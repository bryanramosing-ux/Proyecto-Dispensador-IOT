"""
Pruebas automáticas del servicio de visión (no requieren cámara ni modelo).

    cd OpenCV
    python -m unittest discover -s tests -v
"""
import json
import sys
import threading
import types
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import servidor_vision  # noqa: E402
from clasificador import (Prediccion, clasificar_imagenes, combinar_visita,  # noqa: E402
                          decidir, decodificar_jpeg, evaluar_calidad)


def imagen_textura(brillo=128, tam=(480, 640)):
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, size=(*tam, 3), dtype=np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    return cv2.convertScaleAbs(img, alpha=0.5, beta=brillo - 64)


class ClasificadorFalso:
    def __init__(self, p_perro, p_gato):
        self.p = (p_perro, p_gato)

    def predecir(self, img):
        return Prediccion(self.p[0], self.p[1], 0, max(self.p), "falso")


class TestDecision(unittest.TestCase):
    def test_perro(self):
        self.assertEqual(decidir(0.9, 0.02, 0.6, 0.3, 0.5), (1, "OK"))

    def test_gato(self):
        self.assertEqual(decidir(0.05, 0.85, 0.6, 0.3, 0.5), (2, "OK"))

    def test_sin_mascota(self):
        self.assertEqual(decidir(0.1, 0.1, 0.6, 0.3, 0.5), (0, "SIN_MASCOTA"))

    def test_baja_confianza(self):
        self.assertEqual(decidir(0.55, 0.0, 0.6, 0.3, 0.5), (0, "BAJA_CONFIANZA"))

    def test_ambiguo(self):
        self.assertEqual(decidir(0.62, 0.38, 0.6, 0.3, 0.5), (0, "AMBIGUO"))

    def test_resultado_solo_0_1_2(self):
        rng = np.random.default_rng(1)
        for _ in range(2000):
            a, b = rng.random(2)
            s = a + b + rng.random()
            clase, _ = decidir(a / s, b / s, 0.6, 0.3, 0.5)
            self.assertIn(clase, (0, 1, 2))


class TestCalidad(unittest.TestCase):
    def test_invalida(self):
        self.assertIsNone(decodificar_jpeg(b"esto no es un jpeg"))
        self.assertEqual(evaluar_calidad(None, 35, 225, 40).motivo, "IMAGEN_INVALIDA")

    def test_oscura(self):
        img = np.full((480, 640, 3), 5, np.uint8)
        self.assertEqual(evaluar_calidad(img, 35, 225, 40).motivo, "IMAGEN_OSCURA")

    def test_sobreexpuesta(self):
        img = np.full((480, 640, 3), 250, np.uint8)
        self.assertEqual(evaluar_calidad(img, 35, 225, 40).motivo, "IMAGEN_SOBREEXPUESTA")

    def test_borrosa(self):
        img = cv2.GaussianBlur(imagen_textura(), (51, 51), 20)
        self.assertEqual(evaluar_calidad(img, 35, 225, 40).motivo, "IMAGEN_BORROSA")

    def test_valida(self):
        self.assertTrue(evaluar_calidad(imagen_textura(), 35, 225, 40).valida)

    def test_pequena(self):
        self.assertEqual(evaluar_calidad(imagen_textura(tam=(60, 80)), 35, 225, 40).motivo,
                         "IMAGEN_INVALIDA")


class TestClasificarImagenes(unittest.TestCase):
    def test_promedio_y_fotos_invalidas(self):
        imgs = [imagen_textura(), None, np.zeros((480, 640, 3), np.uint8)]
        r = clasificar_imagenes(ClasificadorFalso(0.9, 0.01), imgs, config)
        self.assertEqual((r.clase, r.fotos_validas), (1, 1))

    def test_ninguna_valida(self):
        r = clasificar_imagenes(ClasificadorFalso(0.9, 0.01), [None, None], config)
        self.assertEqual((r.clase, r.motivo), (0, "IMAGEN_INVALIDA"))


class ClasificadorSecuencia:
    """Devuelve una predicción distinta en cada foto (una visita que evoluciona)."""

    def __init__(self, secuencia):
        self.secuencia = list(secuencia)

    def predecir(self, img):
        pp, pg = self.secuencia.pop(0) if len(self.secuencia) > 1 else self.secuencia[0]
        return Prediccion(pp, pg, 0, max(pp, pg), "falso")


class TestVisita(unittest.TestCase):
    """Fotos cada ~2 s de una misma visita (idea del profesor): se promedian las que muestran un animal."""

    def test_dos_fotos_de_perro_se_promedian(self):
        pp, pg, n, mem = combinar_visita([(0.0, 0.70, 0.05)], 2.1, 0.90, 0.02, config)
        self.assertEqual(n, 2)
        self.assertAlmostEqual(pp, 0.80)
        self.assertEqual(decidir(pp, pg, 0.6, 0.3, 0.5), (1, "OK"))

    def test_perro_y_gato_en_la_misma_visita_no_dispensa(self):
        pp, pg, n, _ = combinar_visita([(0.0, 0.92, 0.02)], 2.0, 0.03, 0.90, config)
        self.assertEqual(n, 2)
        self.assertEqual(decidir(pp, pg, 0.6, 0.3, 0.5)[0], 0)

    def test_foto_vieja_es_otra_visita(self):
        _, _, n, mem = combinar_visita([(0.0, 0.03, 0.90)], 6.0, 0.92, 0.02, config)
        self.assertEqual((n, len(mem)), (1, 1))

    def test_foto_sin_animal_no_se_guarda(self):
        pp, pg, n, mem = combinar_visita([(0.0, 0.9, 0.0)], 2.0, 0.05, 0.05, config)
        self.assertEqual((n, len(mem), round(pp, 2)), (1, 1, 0.05))

    def test_maximo_de_fotos(self):
        mem = []
        for i in range(6):
            _, _, n, mem = combinar_visita(mem, i * 0.5, 0.8, 0.1, config)
        self.assertEqual((n, len(mem)), (config.MAX_FOTOS_VISITA, config.MAX_FOTOS_VISITA))


class TestServidorExtremoAExtremo(unittest.TestCase):
    """Cámara simulada + servidor real (con clasificador falso) por HTTP."""

    @classmethod
    def setUpClass(cls):
        ok, jpg = cv2.imencode(".jpg", imagen_textura())
        datos = jpg.tobytes()

        class Cam(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                self.wfile.write(datos)

            def log_message(self, *a):
                pass

        cls.cam = ThreadingHTTPServer(("127.0.0.1", 0), Cam)
        threading.Thread(target=cls.cam.serve_forever, daemon=True).start()

        cfg = types.SimpleNamespace(**{k: getattr(config, k) for k in dir(config) if k.isupper()})
        cfg.CAMARA_URL = f"http://127.0.0.1:{cls.cam.server_port}"
        cfg.GUARDAR_CAPTURAS = False
        cfg.ESP32_URL = "http://127.0.0.1:9"    # ESP32 apagado: el panel debe informarlo
        cfg.NTFY_TOPICO = ""
        cls.cfg = cfg
        servicio = servidor_vision.ServicioVision(cfg, ClasificadorFalso(0.03, 0.91))
        cls.servicio = servicio
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor_vision.crear_manejador(servicio))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.cam.shutdown()
        cls.srv.server_close()
        cls.cam.server_close()

    def get(self, ruta):
        try:
            with urllib.request.urlopen(self.url + ruta, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_classify_gato(self):
        codigo, d = self.get("/classify?dist=25")
        self.assertEqual(codigo, 200)
        self.assertEqual((d["clase"], d["etiqueta"], d["motivo"]), (2, "GATO", "OK"))

    def test_ultima_foto(self):
        self.get("/classify")
        with urllib.request.urlopen(self.url + "/ultima.jpg", timeout=10) as r:
            self.assertEqual(r.headers["Content-Type"], "image/jpeg")
            self.assertIsNotNone(decodificar_jpeg(r.read()))

    def test_visita_que_se_identifica_en_la_tercera_foto(self):
        """Entrando al cuadro -> dudosa -> gato: la tercera foto (promediada con la segunda) decide."""
        original = self.servicio.clasificador
        self.servicio.clasificador = ClasificadorSecuencia([(0.05, 0.10), (0.10, 0.55), (0.02, 0.95)])
        try:
            r1, r2, r3 = (self.get("/classify")[1] for _ in range(3))
        finally:
            self.servicio.clasificador = original
        self.assertEqual((r1["clase"], r1["motivo"], r1["fotos_visita"]), (0, "SIN_MASCOTA", 1))
        self.assertEqual((r2["clase"], r2["motivo"], r2["fotos_visita"]), (0, "BAJA_CONFIANZA", 1))
        self.assertEqual((r3["clase"], r3["fotos_visita"]), (2, 2))
        self.assertEqual(self.servicio.visita, [])       # la visita terminó con una decisión

    def test_camara_caida(self):
        original = self.servicio.cfg.CAMARA_URL
        self.servicio.cfg.CAMARA_URL = "http://127.0.0.1:9"  # puerto cerrado
        try:
            codigo, d = self.get("/classify")
        finally:
            self.servicio.cfg.CAMARA_URL = original
        self.assertEqual((codigo, d["clase"], d["motivo"]), (502, 0, "CAMARA_NO_RESPONDE"))

    def test_ruta_desconocida(self):
        self.assertEqual(self.get("/feed")[0], 404)

    def post(self, ruta, datos):
        pedido = urllib.request.Request(self.url + ruta, data=json.dumps(datos).encode(), method="POST",
                                        headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_alerta_comida_baja(self):
        codigo, d = self.post("/alerta", {"tipo": "COMIDA_BAJA", "nivel": 18})
        self.assertEqual((codigo, d["ok"]), (200, True))
        self.assertIn("18 %", d["alerta"]["mensaje"])
        panel = self.get("/panel.json")[1]
        self.assertEqual(panel["alertas"][0]["tipo"], "COMIDA_BAJA")
        self.assertIn("error", panel["esp32"])          # ESP32 inalcanzable: se informa, no se cae

    def test_alerta_invalida(self):
        self.assertEqual(self.post("/alerta", {"tipo": "OTRA_COSA"})[0], 400)
        self.assertEqual(self.post("/alerta", ["COMIDA_BAJA"])[0], 400)                  # no es un objeto
        self.assertEqual(self.post("/alerta", {"tipo": "COMIDA_BAJA", "nivel": {}})[0], 400)

    def test_panel_html(self):
        with urllib.request.urlopen(self.url + "/", timeout=10) as r:
            html = r.read().decode("utf-8")
        self.assertIn("Nivel de la tolva", html)


class TestNtfy(unittest.TestCase):
    """El reenvío al celular usa un servidor ntfy (aquí, uno falso local)."""

    def test_reenvio(self):
        recibido = {}

        class Ntfy(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                recibido["ruta"] = self.path
                recibido["titulo"] = self.headers.get("Title")
                recibido["cuerpo"] = self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        srv = ThreadingHTTPServer(("127.0.0.1", 0), Ntfy)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        cfg = types.SimpleNamespace(NTFY_TOPICO="dispensador-prueba",
                                    NTFY_SERVIDOR=f"http://127.0.0.1:{srv.server_port}")
        gestor = servidor_vision.GestorAlertas(cfg)
        gestor._enviar(gestor.registrar("COMIDA_AGOTADA", 2), "urgent")
        srv.shutdown()
        srv.server_close()
        self.assertEqual(recibido["ruta"], "/dispensador-prueba")
        self.assertEqual(recibido["titulo"], "Tolva vacia")
        self.assertIn("vacía", recibido["cuerpo"])


if __name__ == "__main__":
    unittest.main()
