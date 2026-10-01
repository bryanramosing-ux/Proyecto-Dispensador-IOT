"""
Servidor de visión artificial (se ejecuta en el PC / notebook).

Flujo de una clasificación:
    ESP32  --GET /classify-->  PC (este programa)
    PC     --GET /capture -->  ESP32-CAM   (se repite FOTOS_POR_CLASIFICACION veces)
    PC     OpenCV + MobileNetV2  ->  1 = PERRO / 2 = GATO / 0 = INDETERMINADO
    PC     --JSON-->  ESP32   (en la misma respuesta HTTP)

Endpoints:
    GET  /classify   -> clasifica
    GET  /status     -> estado del servidor y de la cámara
    POST /alerta     -> el ESP32 avisa del nivel de la tolva (comida baja, vacía...)
    GET  /           -> panel web para la demostración (nivel, alertas, clasificaciones)
    GET  /panel.json -> datos del panel web

Solo usa la biblioteca estándar de Python + OpenCV + NumPy (sin frameworks web).

Uso:
    python servidor_vision.py
    python servidor_vision.py --camara http://192.168.1.51 --puerto 8000
"""
import argparse
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cv2

import config
from alertas import GestorAlertas
from clasificador import (CLASE_INDETERMINADA, ClasificadorMascotas, Resultado,
                          clasificar_imagenes, decodificar_jpeg)

log = logging.getLogger("vision")


class CamaraNoResponde(Exception):
    pass


def descargar_foto(url_base, timeout_s):
    """Pide una foto a la ESP32-CAM. Devuelve bytes JPEG o lanza CamaraNoResponde."""
    try:
        with urllib.request.urlopen(url_base.rstrip("/") + "/capture", timeout=timeout_s) as r:
            if r.status != 200:
                raise CamaraNoResponde(f"HTTP {r.status}")
            return r.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise CamaraNoResponde(str(e)) from e


def estado_camara(url_base, timeout_s):
    try:
        with urllib.request.urlopen(url_base.rstrip("/") + "/status", timeout=timeout_s) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 - solo informativo
        return {"error": str(e)}


class ServicioVision:
    def __init__(self, cfg):
        self.cfg = cfg
        self.clasificador = ClasificadorMascotas(cfg.MODELO_ONNX, cfg.ETIQUETAS)
        # Una sola cámara: las clasificaciones se atienden de a una.
        self.candado = threading.Lock()
        self.total = 0
        self.ultimo = None
        self.historial = []
        self.alertas = GestorAlertas(cfg)

    def clasificar(self, distancia_cm=None):
        """Devuelve (codigo_http, dict_respuesta)."""
        t0 = time.monotonic()
        with self.candado:
            jpegs, imagenes = [], []
            try:
                for _ in range(max(1, self.cfg.FOTOS_POR_CLASIFICACION)):
                    datos = descargar_foto(self.cfg.CAMARA_URL, self.cfg.TIMEOUT_CAMARA_S)
                    jpegs.append(datos)
                    imagenes.append(decodificar_jpeg(datos))
            except CamaraNoResponde as e:
                log.warning("ESP32-CAM no responde: %s", e)
                res = Resultado(CLASE_INDETERMINADA, "CAMARA_NO_RESPONDE")
                return 502, self._respuesta(res, t0)

            res = clasificar_imagenes(self.clasificador, imagenes, self.cfg)
            self.total += 1
            respuesta = self._respuesta(res, t0)
            self.ultimo = dict(respuesta, hora=datetime.now().isoformat(timespec="seconds"),
                               distancia_cm=distancia_cm)
            self.historial = ([self.ultimo] + self.historial)[:10]
            log.info("Clasificacion #%d -> %s (%s) conf=%.2f perro=%.2f gato=%.2f dist=%s cm %s",
                     self.total, res.etiqueta, res.motivo, res.confianza, res.p_perro,
                     res.p_gato, distancia_cm, res.detalles)
            if self.cfg.GUARDAR_CAPTURAS and jpegs:
                self._guardar(jpegs, res)
            return 200, respuesta

    def _respuesta(self, res, t0):
        d = res.a_dict()
        d["ms"] = int((time.monotonic() - t0) * 1000)
        return d

    def _guardar(self, jpegs, res):
        carpeta = Path(self.cfg.DIR_CAPTURAS) / datetime.now().strftime("%Y-%m-%d")
        carpeta.mkdir(parents=True, exist_ok=True)
        base = datetime.now().strftime("%H%M%S")
        for i, datos in enumerate(jpegs):
            (carpeta / f"{base}_{i}_{res.etiqueta}_{res.motivo}.jpg").write_bytes(datos)

    def panel(self):
        """Datos del panel web: estado del ESP32 (consultado aquí, sin CORS), alertas y fotos."""
        try:
            with urllib.request.urlopen(self.cfg.ESP32_URL.rstrip("/") + "/status", timeout=1.0) as r:
                esp32 = json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - solo informativo
            esp32 = {"error": str(e)}
        return {"esp32": esp32, "alertas": self.alertas.recientes(), "clasificaciones": self.historial,
                "hora": datetime.now().isoformat(timespec="seconds")}

    def estado(self):
        return {
            "servidor": "OK",
            "opencv": cv2.__version__,
            "modelo": Path(self.cfg.MODELO_ONNX).name,
            "camara_url": self.cfg.CAMARA_URL,
            # timeout corto: el ESP32 espera /status 2 s y debe poder distinguir
            # "PC caído" de "cámara caída"
            "camara": estado_camara(self.cfg.CAMARA_URL, 0.8),
            "clasificaciones": self.total,
            "ultima": self.ultimo,
            "alertas": self.alertas.recientes(5),
            "umbrales": {
                "confianza": self.cfg.UMBRAL_CONFIANZA,
                "margen": self.cfg.MARGEN_MINIMO,
                "min_animal": self.cfg.MIN_PROB_ANIMAL,
                "brillo": [self.cfg.BRILLO_MIN, self.cfg.BRILLO_MAX],
                "nitidez_min": self.cfg.NITIDEZ_MIN,
            },
        }


PANEL_HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Dispensador IoT</title>
<style>
:root{--fondo:#f4f6f8;--tarjeta:#fff;--texto:#1f2d3a;--suave:#6b7a89;--ok:#2e8b57;--alerta:#d98c00;--mal:#c0392b}
@media (prefers-color-scheme:dark){:root{--fondo:#11161c;--tarjeta:#1b232c;--texto:#e6edf3;--suave:#9aa7b4}}
body{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:var(--fondo);color:var(--texto)}
main{max-width:960px;margin:auto;padding:16px;display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
h1{grid-column:1/-1;margin:8px 0;font-size:1.4rem}.c{background:var(--tarjeta);border-radius:12px;padding:16px}
.c h2{margin:0 0 8px;font-size:1rem;color:var(--suave);font-weight:600}.grande{font-size:2.2rem;font-weight:700}
.barra{height:22px;border-radius:11px;background:#d5dbe1;overflow:hidden}.barra div{height:100%;transition:width .5s}
ul{list-style:none;margin:0;padding:0}li{padding:6px 0;border-bottom:1px solid #8882}small{color:var(--suave)}
</style></head><body><main>
<h1>Dispensador inteligente · panel en vivo</h1>
<section class="c"><h2>Nivel de la tolva</h2><div class="grande" id="nivel">—</div>
<div class="barra"><div id="barra" style="width:0"></div></div><p id="alertaTolva"></p></section>
<section class="c"><h2>Estado del ESP32</h2><div class="grande" id="estado">—</div>
<p id="detalle"></p></section>
<section class="c"><h2>Alertas</h2><ul id="alertas"><li><small>Sin alertas</small></li></ul></section>
<section class="c"><h2>Últimas clasificaciones</h2><ul id="clases"><li><small>Todavía no hay</small></li></ul></section>
</main><script>
const nombre={1:"🐶 PERRO",2:"🐱 GATO",0:"— no dispensar"};
function li(t){const e=document.createElement("li");e.innerHTML=t;return e}
async function actualizar(){try{const d=await (await fetch("panel.json")).json();const e=d.esp32||{};
const n=e.nivel_tolva;const sin=(n===undefined||n<0);
document.getElementById("nivel").textContent=sin?"sin lectura":Math.round(n)+" %";
const b=document.getElementById("barra");b.style.width=(sin?0:n)+"%";
b.style.background=sin?"#999":(n<=5?"var(--mal)":(n<20?"var(--alerta)":"var(--ok)"));
document.getElementById("alertaTolva").textContent=e.alerta_tolva&&e.alerta_tolva!=="NINGUNA"?"⚠ "+e.alerta_tolva:"";
document.getElementById("estado").textContent=e.error?"sin conexión":e.estado;
document.getElementById("detalle").textContent=e.error?e.error:`Batería ${e.v_bateria} V · servo ${e.v_servo} V · panel ${e.v_panel} V · raciones perro ${e.raciones_perro}, gato ${e.raciones_gato}`;
const ua=document.getElementById("alertas");ua.innerHTML="";(d.alertas.length?d.alertas:[]).forEach(a=>ua.appendChild(li(`<b>${a.titulo}</b><br>${a.mensaje}<br><small>${a.hora}</small>`)));
if(!d.alertas.length)ua.appendChild(li("<small>Sin alertas</small>"));
const uc=document.getElementById("clases");uc.innerHTML="";d.clasificaciones.forEach(c=>uc.appendChild(li(`<b>${nombre[c.clase]}</b> ${c.motivo} · conf ${c.confianza}<br><small>${c.hora}</small>`)));
if(!d.clasificaciones.length)uc.appendChild(li("<small>Todavía no hay</small>"));}catch(err){document.getElementById("estado").textContent="PC sin datos"}}
actualizar();setInterval(actualizar,5000);
</script></body></html>"""


def crear_manejador(servicio):
    class Manejador(BaseHTTPRequestHandler):
        server_version = "DispensadorVision/1.0"

        def _json(self, codigo, datos):
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(cuerpo)

        def _html(self, cuerpo):
            datos = cuerpo.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_POST(self):  # noqa: N802
            url = urlparse(self.path)
            if url.path != "/alerta":
                self._json(404, {"error": "ruta desconocida"})
                return
            try:
                largo = min(int(self.headers.get("Content-Length", 0)), 4096)
                datos = json.loads(self.rfile.read(largo).decode("utf-8") or "{}")
                alerta = servicio.alertas.registrar(datos.get("tipo"), datos.get("nivel"))
                self._json(200, {"ok": True, "alerta": alerta})
            except (ValueError, TypeError, AttributeError) as e:     # JSON inválido o con otra forma
                self._json(400, {"ok": False, "error": str(e)})

        def do_GET(self):  # noqa: N802 (nombre impuesto por http.server)
            url = urlparse(self.path)
            try:
                if url.path == "/":
                    self._html(PANEL_HTML)
                elif url.path == "/panel.json":
                    self._json(200, servicio.panel())
                elif url.path == "/classify":
                    dist = parse_qs(url.query).get("dist", [None])[0]
                    codigo, datos = servicio.clasificar(dist)
                    self._json(codigo, datos)
                elif url.path == "/status":
                    self._json(200, servicio.estado())
                else:
                    self._json(404, {"error": "ruta desconocida",
                                     "rutas": ["/", "/classify", "/status", "/panel.json", "POST /alerta"]})
            except Exception as e:  # noqa: BLE001 - nunca dejar al ESP32 sin respuesta
                log.exception("Error interno")
                self._json(500, {"clase": 0, "etiqueta": "INDETERMINADO",
                                 "motivo": "ERROR_INTERNO", "detalle": str(e)})

        def log_message(self, fmt, *args):
            log.debug("%s - %s", self.address_string(), fmt % args)

    return Manejador


def main():
    ap = argparse.ArgumentParser(description="Servidor de visión del dispensador")
    ap.add_argument("--camara", default=config.CAMARA_URL, help="URL base de la ESP32-CAM")
    ap.add_argument("--host", default=config.HOST)
    ap.add_argument("--puerto", type=int, default=config.PUERTO)
    ap.add_argument("--esp32", default=config.ESP32_URL, help="URL base del ESP32 (el panel web lee su /status)")
    ap.add_argument("--ntfy", default=config.NTFY_TOPICO,
                    help="tema de ntfy para recibir las alertas en el celular (vacío = desactivado)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    config.CAMARA_URL, config.ESP32_URL, config.NTFY_TOPICO = args.camara, args.esp32, args.ntfy
    servicio = ServicioVision(config)
    servidor = ThreadingHTTPServer((args.host, args.puerto), crear_manejador(servicio))
    log.info("Servidor de vision en http://%s:%d  (camara: %s, OpenCV %s)",
             args.host, args.puerto, config.CAMARA_URL, cv2.__version__)
    log.info("Panel web: http://<IP-de-este-PC>:%d/   ·   alertas al celular: %s", args.puerto,
             f"ntfy, tema '{config.NTFY_TOPICO}'" if config.NTFY_TOPICO else "desactivadas (--ntfy TEMA)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        log.info("Detenido por el usuario")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
