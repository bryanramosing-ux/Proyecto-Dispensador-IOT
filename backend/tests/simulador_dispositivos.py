"""SIMULADOR para probar el dashboard SIN hardware. No es el hardware real.

Levanta una ESP32-CAM falsa (GET /status, /capture, /stream) y un ESP32 falso
(POST /dispensar) que además envía telemetría al backend. Las imágenes llevan la
leyenda "SIMULADO" para no confundirlas nunca con fotos reales del dispositivo.

Uso:  TOKEN_DISPOSITIVO=demo ESP32_CAM_URL=http://127.0.0.1:8003 python backend/dashboard_server.py   (otra terminal)
      python backend/tests/simulador_dispositivos.py [--backend http://127.0.0.1:8001]
"""
import argparse, io, json, random, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = "demo"
estado = {"nivel": 72.0, "dispensando_hasta": 0.0, "total": 0, "t0": time.time(), "ultima": -1.0, "porc": 0}


def jpeg(texto):
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (640, 480), (30 + random.randint(0, 40), 50, 70)); d = ImageDraw.Draw(im)
        d.text((20, 20), "SIMULADO - no es la camara real", fill=(255, 255, 255)); d.text((20, 50), texto, fill=(255, 220, 120))
        b = io.BytesIO(); im.save(b, "JPEG", quality=70); return b.getvalue()
    except ImportError:  # JPEG mínimo válido (1x1) si no hay Pillow
        import base64
        return base64.b64decode("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=")


class Cam(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            b = json.dumps({"camara": True, "psram": True, "fotos_ok": 0, "fotos_fallidas": 0, "rssi": -55, "uptime_s": int(time.time() - estado["t0"]), "resolucion": "VGA 640x480", "stream": True}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        elif self.path == "/capture":
            b = jpeg(time.strftime("%H:%M:%S")); self.send_response(200); self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        elif self.path == "/stream":
            self.send_response(200); self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=esp32cam"); self.end_headers()
            try:
                for _ in range(20):
                    b = jpeg(time.strftime("%H:%M:%S"))
                    self.wfile.write(b"--esp32cam\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(b) + b + b"\r\n"); time.sleep(0.1)
            except OSError:
                pass
        else:
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()
    def log_message(self, *a): pass


class Esp(BaseHTTPRequestHandler):
    def do_POST(self):
        f = urllib.parse.parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
        if f.get("token", [""])[0] != TOKEN: code, r = 401, {"ok": False, "resultado": "TOKEN_INVALIDO"}
        elif self.path == "/dispensar":
            n = f.get("porciones", ["0"])[0]
            if not n.isdigit() or not 1 <= int(n) <= 3: code, r = 400, {"ok": False, "resultado": "PORCIONES_INVALIDAS"}
            elif time.time() < estado["dispensando_hasta"]: code, r = 409, {"ok": False, "resultado": "OCUPADO"}
            else:
                estado["dispensando_hasta"] = time.time() + 3 * int(n); estado["total"] += 1; estado["porc"] = int(n); estado["ultima"] = time.time()
                estado["nivel"] = max(0.0, estado["nivel"] - 2 * int(n)); code, r = 202, {"ok": True, "resultado": "ACEPTADA", "cooldown_s": 0}
        else: code, r = 404, {"ok": False}
        b = json.dumps(r).encode(); self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass


def telemetria(backend):
    while True:
        d = time.time() < estado["dispensando_hasta"]
        body = {"dispositivo": "ESP32", "fw": "SIM", "modo": "MANUAL", "estado": "DOSIFICANDO" if d else "ESPERANDO", "error": "",
                "wifi_conectado": True, "ip": "127.0.0.1:8002", "rssi": -48, "backend": True, "sensor_nivel_ok": True,
                "distancia_nivel_cm": round(15 + (100 - estado["nivel"]) * 0.2 + random.uniform(-.3, .3), 1), "nivel_tolva": round(estado["nivel"]),
                "alerta_tolva": "NINGUNA", "servo": "DISPENSANDO" if d else "REPOSO", "dispensando": d, "pulso_servo_us": 1500,
                "dispensaciones_total": estado["total"], "dispensaciones_24h": estado["total"],
                "ultima_dispensacion_hace_s": int(time.time() - estado["ultima"]) if estado["ultima"] > 0 else -1, "ultimo_origen": "PANEL",
                "ultimas_porciones": estado["porc"], "ultimo_resultado": "OK", "cooldown_s": 0, "uptime_s": int(time.time() - estado["t0"])}
        try:
            urllib.request.urlopen(urllib.request.Request(backend + "/api/device/telemetry", json.dumps(body).encode(), {"Content-Type": "application/json", "X-Device-Token": TOKEN}), timeout=2).read()
        except Exception as e:
            print("telemetría:", e)
        time.sleep(2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--backend", default="http://127.0.0.1:8001"); a = ap.parse_args()
    cam = ThreadingHTTPServer(("127.0.0.1", 8003), Cam); esp = ThreadingHTTPServer(("127.0.0.1", 8002), Esp)
    threading.Thread(target=cam.serve_forever, daemon=True).start(); threading.Thread(target=esp.serve_forever, daemon=True).start()
    print("Simulador activo: ESP32-CAM http://127.0.0.1:8003  ESP32 http://127.0.0.1:8002  (token 'demo'; backend con ESP32_CAM_URL=http://127.0.0.1:8003)")
    telemetria(a.backend)
