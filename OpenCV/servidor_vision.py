"""
Servidor de visión artificial (se ejecuta en el PC / notebook).

Flujo de una clasificación:
    ESP32  --GET /classify-->  PC (este programa)
    PC     --GET /capture -->  ESP32-CAM   (se repite FOTOS_POR_CLASIFICACION veces)
    PC     OpenCV + MobileNetV2  ->  1 = PERRO / 2 = GATO / 0 = INDETERMINADO
    PC     --JSON-->  ESP32   (en la misma respuesta HTTP)

Endpoints:
    GET /classify   -> clasifica (ver Documentation/api/api.md)
    GET /status     -> estado del servidor y de la cámara

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
            "umbrales": {
                "confianza": self.cfg.UMBRAL_CONFIANZA,
                "margen": self.cfg.MARGEN_MINIMO,
                "min_animal": self.cfg.MIN_PROB_ANIMAL,
                "brillo": [self.cfg.BRILLO_MIN, self.cfg.BRILLO_MAX],
                "nitidez_min": self.cfg.NITIDEZ_MIN,
            },
        }


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

        def do_GET(self):  # noqa: N802 (nombre impuesto por http.server)
            url = urlparse(self.path)
            try:
                if url.path == "/classify":
                    dist = parse_qs(url.query).get("dist", [None])[0]
                    codigo, datos = servicio.clasificar(dist)
                    self._json(codigo, datos)
                elif url.path == "/status":
                    self._json(200, servicio.estado())
                else:
                    self._json(404, {"error": "ruta desconocida", "rutas": ["/classify", "/status"]})
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
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    config.CAMARA_URL = args.camara
    servicio = ServicioVision(config)
    servidor = ThreadingHTTPServer((args.host, args.puerto), crear_manejador(servicio))
    log.info("Servidor de vision en http://%s:%d  (camara: %s, OpenCV %s)",
             args.host, args.puerto, config.CAMARA_URL, cv2.__version__)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        log.info("Detenido por el usuario")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
