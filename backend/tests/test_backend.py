"""Pruebas del backend con ESP32 y ESP32-CAM SIMULADOS (no prueban hardware real)."""
import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dashboard_server as ds  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 200 + b"\xff\xd9"
TOKEN = "tok123"


class FakeCamera(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/capture":
            self.send_response(200); self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(JPEG))); self.end_headers(); self.wfile.write(JPEG)
        elif self.path == "/status":
            b = json.dumps({"camara": True, "uptime_s": 5}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        else:
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()

    def log_message(self, *a): pass


class FakeESP(BaseHTTPRequestHandler):
    received = []


    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        FakeESP.received.append((self.path, body))
        ok = f"token={TOKEN}" in body
        b = json.dumps({"ok": ok, "resultado": "ACEPTADA" if ok else "TOKEN_INVALIDO"}).encode()
        self.send_response(202 if ok else 401); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a): pass


def serve(handler):
    s = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Base(unittest.TestCase):
    token = TOKEN

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cam = serve(FakeCamera)
        cls.esp = serve(FakeESP)
        cls.cfg = ds.Config(host="127.0.0.1", port=free_port(), storage=cls.tmp.name,
                            camera_url=f"http://127.0.0.1:{cls.cam.server_port}", token=cls.token,
                            start_threads=False, min_dispense_gap_s=0, discovery_port=free_port())
        cls.srv, cls.app = ds.create_server(cls.cfg)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.cfg.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.cam.shutdown(); cls.esp.shutdown(); cls.app.db.close(); cls.tmp.cleanup()

    def req(self, method, path, body=None, headers=None, dash=True):
        h = {"Content-Type": "application/json"}
        if dash: h["X-Requested-With"] = "dashboard"
        h.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                raw = resp.read(); return resp.status, raw
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def j(self, *a, **k):
        c, raw = self.req(*a, **k); return c, json.loads(raw)

    def telemetry(self, **over):
        d = {"dispositivo": "ESP32", "estado": "ESPERANDO", "ip": "127.0.0.1", "dispensando": False,
             "dispensaciones_total": 0, "nivel_tolva": 65, "distancia_nivel_cm": 9.5}
        d.update(over)
        return self.j("POST", "/api/device/telemetry", d, headers={"X-Device-Token": self.token}, dash=False)


class TestDispositivo(Base):
    def test_telemetria_requiere_token(self):
        c, _ = self.j("POST", "/api/device/telemetry", {"dispositivo": "ESP32"}, dash=False)
        self.assertEqual(c, 401)

    def test_telemetria_valida_y_estado(self):
        c, _ = self.telemetry(); self.assertEqual(c, 200)
        _, st = self.j("GET", "/api/status")
        self.assertTrue(st["esp32"]["online"]); self.assertEqual(st["esp32"]["data"]["nivel_tolva"], 65)

    def test_telemetria_invalida(self):
        for body in ({"dispositivo": "OTRO"}, [1, 2]):
            c, _ = self.j("POST", "/api/device/telemetry", body, headers={"X-Device-Token": TOKEN}, dash=False)
            self.assertEqual(c, 400)
        r = urllib.request.Request(self.base + "/api/device/telemetry", data=b"{no json", method="POST",
                                   headers={"X-Device-Token": TOKEN, "Content-Length": "8"})
        with self.assertRaises(urllib.error.HTTPError) as cm: urllib.request.urlopen(r)
        self.assertEqual(cm.exception.code, 400)

    def test_cuerpo_enorme_rechazado(self):
        c, _ = self.j("POST", "/api/device/telemetry", {"dispositivo": "ESP32", "x": "a" * 20000},
                      headers={"X-Device-Token": TOKEN}, dash=False)
        self.assertEqual(c, 413)

    def test_alerta(self):
        c, _ = self.j("POST", "/api/device/alert", {"dispositivo": "ESP32", "tipo": "COMIDA_BAJA", "nivel": 18},
                      headers={"X-Device-Token": TOKEN}, dash=False)
        self.assertEqual(c, 200)
        c, _ = self.j("POST", "/api/device/alert", {"tipo": "drop table"}, headers={"X-Device-Token": TOKEN}, dash=False)
        self.assertEqual(c, 400)

    def test_desconexion_no_muestra_datos_viejos(self):
        self.telemetry()
        self.app.set_esp32_online(False)
        _, st = self.j("GET", "/api/status")
        self.assertFalse(st["esp32"]["online"]); self.assertIsNone(st["esp32"]["data"])
        self.assertIsNotNone(st["esp32"]["last_data"])
        self.telemetry()  # se recupera
        self.assertTrue(self.j("GET", "/api/status")[1]["esp32"]["online"])
        kinds = [e["tipo"] for e in self.j("GET", "/api/history")[1]["items"]]
        self.assertIn("conexion", kinds)


class TestGaleria(Base):
    def test_captura_listado_descarga_borrado(self):
        c, r = self.j("POST", "/api/capture"); self.assertEqual(c, 200)
        name = r["name"]
        self.assertRegex(name, ds.FOTO_RE)
        _, g = self.j("GET", "/api/gallery"); self.assertIn(name, [i["name"] for i in g["items"]])
        c, raw = self.req("GET", f"/api/gallery/{name}"); self.assertEqual((c, raw), (200, JPEG))
        # sin confirmación no borra
        self.assertEqual(self.req("DELETE", f"/api/gallery/{name}")[0], 400)
        self.assertEqual(self.req("DELETE", f"/api/gallery/{name}", headers={"X-Confirm": "delete"})[0], 200)
        self.assertEqual(self.req("GET", f"/api/gallery/{name}")[0], 404)

    def test_frame_sin_guardar(self):
        n0 = len(self.j("GET", "/api/gallery")[1]["items"])
        c, raw = self.req("GET", "/api/camera/frame"); self.assertEqual((c, raw), (200, JPEG))
        self.assertEqual(len(self.j("GET", "/api/gallery")[1]["items"]), n0)

    def test_nombres_unicos(self):
        a = self.j("POST", "/api/capture")[1]["name"]; b = self.j("POST", "/api/capture")[1]["name"]
        self.assertNotEqual(a, b)

    def test_path_traversal(self):
        for bad in ("..%2f..%2fetc%2fpasswd", "../x.jpg", "%2e%2e/dashboard_server.py", "foto_x.jpg", "db"):
            self.assertEqual(self.req("GET", f"/api/gallery/{bad}")[0], 404, bad)
            self.assertEqual(self.req("DELETE", f"/api/gallery/{bad}", headers={"X-Confirm": "delete"})[0], 404, bad)

    def test_persistencia_tras_reinicio(self):
        name = self.j("POST", "/api/capture")[1]["name"]
        app2 = ds.App(ds.Config(storage=self.tmp.name, start_threads=False))
        self.assertIn(name, [p["name"] for p in app2.list_photos()])
        self.assertTrue(any(e["tipo"] == "foto" for e in app2.history()))
        app2.db.close()

    def test_csrf(self):
        self.assertEqual(self.req("POST", "/api/capture", dash=False)[0], 403)
        self.assertEqual(self.req("POST", "/api/capture", headers={"Origin": "http://evil.example"})[0], 403)

    def test_camara_caida(self):
        cfg = ds.Config(storage=self.tmp.name, camera_url="http://127.0.0.1:1", start_threads=False)
        app = ds.App(cfg)
        with self.assertRaises(Exception): app.capture()
        app.poll_camera(); self.assertFalse(app.camera_online); app.db.close()


class TestDispensar(Base):
    def setUp(self):
        FakeESP.received.clear()
        self.app.esp32_ip = f"127.0.0.1:{self.esp.server_port}"
        self.app.esp32 = {"dispensando": False}; self.app.esp32_online = True; self.app.esp32_seen = time.time()
        self.app.last_cmd = 0

    def test_ok_con_confirmacion(self):
        c, r = self.j("POST", "/api/dispense", {"porciones": 1, "confirm": True})
        self.assertEqual(c, 202); self.assertTrue(r["ok"])
        path, body = FakeESP.received[0]
        self.assertEqual(path, "/dispensar"); self.assertIn("porciones=1", body); self.assertIn(f"token={TOKEN}", body)

    def test_sin_confirmacion_no_mueve(self):
        self.assertEqual(self.j("POST", "/api/dispense", {"porciones": 1})[0], 400)
        self.assertEqual(self.j("POST", "/api/dispense", {"porciones": 1, "confirm": "true"})[0], 400)
        self.assertEqual(FakeESP.received, [])

    def test_porciones_invalidas(self):
        for p in (0, 4, -1, 1.5, "2", None, True, 999):
            self.assertEqual(self.j("POST", "/api/dispense", {"porciones": p, "confirm": True})[0], 400, p)
        self.assertEqual(FakeESP.received, [])

    def test_ocupado_y_offline(self):
        self.app.esp32["dispensando"] = True
        self.assertEqual(self.j("POST", "/api/dispense", {"porciones": 1, "confirm": True})[0], 409)
        self.app.esp32["dispensando"] = False; self.app.esp32_online = False
        self.assertEqual(self.j("POST", "/api/dispense", {"porciones": 1, "confirm": True})[0], 503)
        self.assertEqual(FakeESP.received, [])

    def test_limite_frecuencia(self):
        self.app.cfg.min_dispense_gap_s = 60
        try:
            self.assertEqual(self.j("POST", "/api/dispense", {"porciones": 1, "confirm": True})[0], 202)
            self.assertEqual(self.j("POST", "/api/dispense", {"porciones": 1, "confirm": True})[0], 429)
            self.assertEqual(len(FakeESP.received), 1)
        finally:
            self.app.cfg.min_dispense_gap_s = 0

    def test_get_no_dispensa(self):
        self.assertEqual(self.req("GET", "/api/dispense")[0], 404)
        self.assertEqual(FakeESP.received, [])


class TestSinToken(Base):
    token = ""

    def test_remoto_deshabilitado(self):
        self.app.esp32_online = True
        self.assertEqual(self.j("POST", "/api/dispense", {"porciones": 1, "confirm": True})[0], 403)


class TestAuto(Base):
    def test_auto_captura_validacion(self):
        for v in (5, -1, 99999, "10", True, None):
            self.assertEqual(self.j("POST", "/api/auto-capture", {"interval_s": v})[0], 400, v)
        self.assertEqual(self.j("POST", "/api/auto-capture", {"interval_s": 30})[0], 200)
        self.assertEqual(self.app._load_setting("auto_capture_s", 0), 30)
        self.j("POST", "/api/auto-capture", {"interval_s": 0})

    def test_descubrimiento_udp(self):
        cfg = ds.Config(storage=self.tmp.name, discovery_port=free_port(), port=8123, start_threads=False)
        app = ds.App(cfg)
        threading.Thread(target=app._loop_discovery, daemon=True).start(); time.sleep(0.3)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2)
        s.sendto(b"DISPENSADOR?", ("127.0.0.1", cfg.discovery_port))
        self.assertEqual(s.recvfrom(64)[0], b"DISPENSADOR!8123")
        app.stop_background(); s.close(); time.sleep(1.2); app.db.close()

    def test_sse_entrega_estado(self):
        r = urllib.request.urlopen(self.base + "/api/events", timeout=5)
        first = b""
        while b"\n\n" not in first: first += r.read(1)
        self.assertIn(b"event: status", first); r.close()

    def test_rutas_estaticas_y_404(self):
        self.assertEqual(self.req("GET", "/")[0], 200)
        self.assertEqual(self.req("GET", "/nada")[0], 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)

