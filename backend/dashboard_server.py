"""Backend local del dispensador IoT (solo biblioteca estándar, sin Internet).

Responsabilidades:
  * Recibir telemetría y alertas del ESP32 (POST /api/device/telemetry, /alert).
  * Responder al descubrimiento UDP del ESP32 ("DISPENSADOR?" -> "DISPENSADOR!<puerto>").
  * Consultar la ESP32-CAM, hacer de proxy del flujo MJPEG y guardar fotos en disco.
  * Registrar eventos en SQLite (sobreviven a reinicios).
  * Reenviar comandos de dispensación al ESP32 con validación, confirmación y límite de frecuencia.
  * Empujar el estado al dashboard en tiempo real mediante Server-Sent Events (SSE).

Se usa SSE y no WebSocket porque el flujo es solo servidor -> navegador y SSE no
necesita dependencias externas; los comandos viajan por HTTP REST.
"""
from __future__ import annotations

import json
import os
import queue
import re
import secrets
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"

# Nombres de fotos generados por el sistema: es lo único que se sirve o borra.
FOTO_RE = re.compile(r"^foto_\d{8}_\d{6}_[0-9a-f]{6}\.jpg$")
MAX_FOTO_BYTES = 5 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024
MSG_PREGUNTA = b"DISPENSADOR?"
MSG_RESPUESTA = b"DISPENSADOR!"


def cargar_env(ruta: Path) -> None:
    """Carga backend/.env sin sobrescribir variables ya definidas en el entorno."""
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Config:
    def __init__(self, **kw):
        env = os.environ.get
        self.host = kw.get("host", env("HOST", "0.0.0.0"))
        self.port = int(kw.get("port", env("PORT", "8001")))
        self.camera_url = kw.get("camera_url", env("ESP32_CAM_URL", "http://192.168.1.51")).rstrip("/")
        self.esp32_url = kw.get("esp32_url", env("ESP32_URL", "")).rstrip("/")  # opcional: se aprende de la telemetría
        self.token = kw.get("token", env("TOKEN_DISPOSITIVO", ""))
        self.storage = Path(kw.get("storage", env("STORAGE_DIR", str(ROOT / "backend" / "storage"))))
        self.discovery_port = int(kw.get("discovery_port", env("PUERTO_DESCUBRIMIENTO", "41234")))
        self.esp32_timeout_s = float(kw.get("esp32_timeout_s", env("ESP32_OFFLINE_S", "15")))
        self.camera_poll_s = float(kw.get("camera_poll_s", env("CAMERA_POLL_S", "5")))
        self.min_dispense_gap_s = float(kw.get("min_dispense_gap_s", env("MIN_DISPENSE_GAP_S", "3")))
        self.max_portions = int(kw.get("max_portions", env("MAX_PORCIONES", "3")))
        self.start_threads = kw.get("start_threads", True)


class Hub:
    """Difusión de eventos SSE a los navegadores conectados."""

    def __init__(self):
        self._clients: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=50)
        with self._lock:
            self._clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def publish(self, event: str, data) -> None:
        msg = (event, data)
        with self._lock:
            for q in list(self._clients):
                try:
                    q.put_nowait(msg)
                except queue.Full:  # cliente lento: se descarta el mensaje, no se bloquea nada
                    pass


class App:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.t0 = time.time()
        self.gallery = cfg.storage / "gallery"
        self.gallery.mkdir(parents=True, exist_ok=True)
        self.hub = Hub()
        self._db_lock = threading.Lock()
        self.db = sqlite3.connect(str(cfg.storage / "dispensador.db"), check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " ts TEXT NOT NULL, tipo TEXT NOT NULL, mensaje TEXT NOT NULL, dato TEXT)"
        )
        self.db.commit()
        # Estado del ESP32 (telemetría) y de la cámara (sondeo)
        self.esp32: dict = {}
        self.esp32_seen = 0.0
        self.esp32_ip = ""
        self.esp32_online = False
        self.camera: dict = {}
        self.camera_seen = 0.0
        self.camera_online = False
        self.cam_lock = threading.Lock()  # la cámara atiende una petición a la vez
        self.cmd_lock = threading.Lock()  # una dispensación a la vez
        self.last_cmd = 0.0
        self.auto_capture_s = self._load_setting("auto_capture_s", 0)
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # ---------------- persistencia -----------------
    def _settings_path(self) -> Path:
        return self.cfg.storage / "settings.json"

    def _load_setting(self, key, default):
        try:
            return json.loads(self._settings_path().read_text("utf-8")).get(key, default)
        except (OSError, ValueError):
            return default

    def set_auto_capture(self, seconds: int) -> None:
        self.auto_capture_s = seconds
        self._settings_path().write_text(json.dumps({"auto_capture_s": seconds}), encoding="utf-8")
        self.log("estado", f"Captura automática: {'desactivada' if seconds == 0 else f'cada {seconds} s'}")

    def log(self, tipo: str, mensaje: str, dato=None) -> None:
        ts = ahora_iso()
        with self._db_lock:
            self.db.execute(
                "INSERT INTO eventos (ts, tipo, mensaje, dato) VALUES (?,?,?,?)",
                (ts, tipo, mensaje, json.dumps(dato) if dato is not None else None),
            )
            self.db.commit()
        self.hub.publish("evento", {"ts": ts, "tipo": tipo, "mensaje": mensaje})

    def history(self, limit=100, tipo=None) -> list[dict]:
        q = "SELECT id, ts, tipo, mensaje FROM eventos"
        args: tuple = ()
        if tipo:
            q += " WHERE tipo=?"
            args = (tipo,)
        q += " ORDER BY id DESC LIMIT ?"
        with self._db_lock:
            rows = self.db.execute(q, args + (limit,)).fetchall()
        return [{"id": r[0], "ts": r[1], "tipo": r[2], "mensaje": r[3]} for r in rows]

    # ---------------- estado -----------------
    def snapshot(self) -> dict:
        now = time.time()
        esp_age = now - self.esp32_seen if self.esp32_seen else None
        cam_age = now - self.camera_seen if self.camera_seen else None
        return {
            "ts": ahora_iso(),
            "backend_uptime_s": int(now - self.t0),
            "esp32": {
                "online": self.esp32_online,
                "age_s": round(esp_age, 1) if esp_age is not None else None,
                "ip": self.esp32_ip,
                # Un ESP32 desconectado NO muestra datos viejos como si fueran actuales.
                "data": self.esp32 if self.esp32_online else None,
                "last_data": None if self.esp32_online else (self.esp32 or None),
            },
            "camera": {
                "online": self.camera_online,
                "age_s": round(cam_age, 1) if cam_age is not None else None,
                "url": self.camera_base(),
                "data": self.camera if self.camera_online else None,
            },
            "auto_capture_s": self.auto_capture_s,
            "max_portions": self.cfg.max_portions,
            "remote_commands": bool(self.cfg.token),
            "last_photo": (self.list_photos(1) or [None])[0],
        }

    def push_status(self) -> None:
        self.hub.publish("status", self.snapshot())

    def set_esp32_online(self, online: bool) -> None:
        if online != self.esp32_online:
            self.esp32_online = online
            self.log("conexion", "ESP32 conectado" if online else "ESP32 sin comunicación")

    def set_camera_online(self, online: bool) -> None:
        if online != self.camera_online:
            self.camera_online = online
            self.log("conexion", "ESP32-CAM conectada" if online else "ESP32-CAM sin comunicación")

    def on_telemetry(self, data: dict, remote_ip: str) -> None:
        prev = self.esp32
        self.esp32 = data
        self.esp32_seen = time.time()
        ip = data.get("ip") if isinstance(data.get("ip"), str) else ""
        self.esp32_ip = ip if ip and ip != "0.0.0.0" else remote_ip
        self.set_esp32_online(True)
        if prev.get("estado") != data.get("estado"):
            self.log("estado", f"ESP32: {prev.get('estado', '—')} → {data.get('estado')}")
        if data.get("error") and prev.get("error") != data.get("error"):
            self.log("error", f"ESP32 error: {data.get('error')}")
        if prev and data.get("dispensaciones_total") != prev.get("dispensaciones_total"):
            self.log(
                "dispensacion",
                f"Dispensación #{data.get('dispensaciones_total')} ({data.get('ultimo_origen', '?')},"
                f" {data.get('ultimas_porciones', '?')} porc.) → {data.get('ultimo_resultado', '?')}",
            )
        self.push_status()

    # ---------------- cámara -----------------
    def camera_base(self) -> str:
        return self.cfg.camera_url or self.esp32_base()

    def camera_get(self, path: str, timeout: float):
        base = self.camera_base()
        if not base:
            raise ConnectionError("IP de la cámara desconocida (el ESP32 aún no envía telemetría)")
        if not self.cam_lock.acquire(timeout=timeout):
            raise TimeoutError("cámara ocupada")
        try:
            req = urllib.request.Request(base + path, headers={"User-Agent": "dispensador-backend/2"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        finally:
            self.cam_lock.release()

    def poll_camera(self) -> None:
        try:
            status, body = self.camera_get("/status", 3)
            data = json.loads(body.decode("utf-8", "replace"))
            self.camera, self.camera_seen = data, time.time()
            self.set_camera_online(status == 200 and bool(data.get("camara")))
        except Exception:
            self.set_camera_online(False)
        self.push_status()

    def capture(self, origin: str = "manual") -> dict:
        status, body = self.camera_get("/capture", 8)
        if status != 200 or not body.startswith(b"\xff\xd8") or len(body) > MAX_FOTO_BYTES:
            raise ValueError("la cámara no devolvió un JPEG válido")
        name = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}.jpg"
        tmp = self.gallery / (name + ".part")
        tmp.write_bytes(body)
        tmp.replace(self.gallery / name)  # escritura atómica: nunca queda una foto a medias
        self.log("foto", f"Foto {name} ({origin}, {len(body) // 1024} kB)")
        self.push_status()
        return {"name": name, "size": len(body)}

    def list_photos(self, limit: int = 500) -> list[dict]:
        names = sorted((p for p in self.gallery.iterdir() if FOTO_RE.match(p.name)), key=lambda p: p.name, reverse=True)
        out = []
        for p in names[:limit]:
            st = p.stat()
            out.append({"name": p.name, "size": st.st_size,
                        "ts": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")})
        return out

    def photo_path(self, name: str) -> Path | None:
        if not FOTO_RE.match(name):  # impide cualquier ruta fuera de la galería
            return None
        p = self.gallery / name
        return p if p.is_file() else None

    # ---------------- comandos al ESP32 -----------------
    def esp32_base(self) -> str:
        if self.esp32_ip:
            return f"http://{self.esp32_ip}"
        return self.cfg.esp32_url

    def send_command(self, path: str, form: dict) -> tuple[int, dict]:
        base = self.esp32_base()
        if not base:
            return 503, {"ok": False, "error": "IP del ESP32 desconocida: aún no ha enviado telemetría"}
        body = urllib.parse.urlencode({**form, "token": self.cfg.token}).encode()
        req = urllib.request.Request(base + path, data=body, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as e:  # el ESP32 respondió con un rechazo (409, 400, 403...)
            try:
                return e.code, json.loads(e.read().decode("utf-8", "replace") or "{}")
            except ValueError:
                return e.code, {"ok": False, "error": f"HTTP {e.code}"}
        except Exception as e:
            return 503, {"ok": False, "error": f"ESP32 no responde: {e}"}

    def dispense(self, portions) -> tuple[int, dict]:
        if not self.cfg.token:
            return 403, {"ok": False, "error": "control remoto deshabilitado: defina TOKEN_DISPOSITIVO en backend/.env y secrets.h"}
        if not isinstance(portions, int) or isinstance(portions, bool) or not 1 <= portions <= self.cfg.max_portions:
            return 400, {"ok": False, "error": f"porciones debe ser un entero entre 1 y {self.cfg.max_portions}"}
        if not self.esp32_online:
            return 503, {"ok": False, "error": "ESP32 desconectado: no se envía el comando"}
        if not self.cmd_lock.acquire(blocking=False):
            return 409, {"ok": False, "error": "ya hay una dispensación en curso"}
        try:
            gap = time.time() - self.last_cmd
            if gap < self.cfg.min_dispense_gap_s:
                return 429, {"ok": False, "error": f"espere {self.cfg.min_dispense_gap_s - gap:.0f} s entre comandos"}
            if self.esp32.get("dispensando"):
                return 409, {"ok": False, "error": "el dispensador está ocupado"}
            self.last_cmd = time.time()
            code, resp = self.send_command("/dispensar", {"porciones": str(portions)})
            self.log("dispensacion", f"Comando desde dashboard: {portions} porc. → HTTP {code} {resp.get('resultado', resp.get('error', ''))}")
            return code, resp
        finally:
            self.cmd_lock.release()

    # ---------------- hilos de fondo -----------------
    def _loop_watchdog(self):
        while not self._stop.wait(2):
            if self.esp32_online and time.time() - self.esp32_seen > self.cfg.esp32_timeout_s:
                self.set_esp32_online(False)
                self.push_status()
            else:
                self.hub.publish("status", self.snapshot())  # latido: refresca edades y uptime

    def _loop_camera(self):
        last_auto = time.time()
        while not self._stop.wait(self.cfg.camera_poll_s):
            self.poll_camera()
            if self.auto_capture_s and self.camera_online and time.time() - last_auto >= self.auto_capture_s:
                last_auto = time.time()
                try:
                    self.capture("automática")
                except Exception as e:
                    self.log("error", f"Captura automática fallida: {e}")

    def _loop_discovery(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.cfg.discovery_port))
        except OSError as e:
            print(f"Aviso: descubrimiento UDP desactivado ({e}); configure URL_BACKEND en secrets.h")
            return
        sock.settimeout(1)
        while not self._stop.is_set():
            try:
                data, addr = sock.recvfrom(64)
            except socket.timeout:
                continue
            except OSError:
                return
            if data.strip() == MSG_PREGUNTA:
                sock.sendto(MSG_RESPUESTA + str(self.cfg.port).encode(), addr)

    def start_background(self):
        for fn in (self._loop_watchdog, self._loop_camera, self._loop_discovery):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self._threads.append(t)

    def stop_background(self):
        self._stop.set()


# ======================================================================
# HTTP
# ======================================================================
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "Dispensador/2"

        # --- utilidades ---
        def _json(self, payload, status=200):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self, required=True):
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                n = -1
            if n < 0 or n > MAX_JSON_BYTES:
                self._json({"ok": False, "error": "cuerpo demasiado grande o inválido"}, 413)
                return None
            raw = self.rfile.read(n) if n else b""
            if not raw and not required:
                return {}
            try:
                data = json.loads(raw.decode("utf-8"))
            except ValueError:
                self._json({"ok": False, "error": "JSON inválido"}, 400)
                return None
            if not isinstance(data, dict):
                self._json({"ok": False, "error": "se esperaba un objeto JSON"}, 400)
                return None
            return data

        def _device_auth(self) -> bool:
            if app.cfg.token and not secrets.compare_digest(self.headers.get("X-Device-Token", ""), app.cfg.token):
                self._json({"ok": False, "error": "token de dispositivo inválido"}, 401)
                return False
            return True

        def _dashboard_guard(self) -> bool:
            """Acciones del navegador: exige cabecera propia y mismo origen (frena CSRF desde otras webs)."""
            if self.headers.get("X-Requested-With") != "dashboard":
                self._json({"ok": False, "error": "falta X-Requested-With"}, 403)
                return False
            origin = self.headers.get("Origin")
            if origin and urllib.parse.urlparse(origin).netloc != self.headers.get("Host"):
                self._json({"ok": False, "error": "origen no permitido"}, 403)
                return False
            return True

        # --- GET ---
        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path in STATIC:
                name, ctype = STATIC[path]
                f = FRONTEND_DIR / name
                if not f.is_file():
                    return self._json({"error": "archivo no encontrado"}, 404)
                data = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/health":
                return self._json({"status": "ok", "uptime_s": int(time.time() - app.t0)})
            if path == "/api/status":
                return self._json(app.snapshot())
            if path == "/api/history":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    limit = max(1, min(500, int(q.get("limit", ["100"])[0])))
                except ValueError:
                    limit = 100
                return self._json({"items": app.history(limit, q.get("tipo", [None])[0])})
            if path == "/api/gallery":
                return self._json({"items": app.list_photos()})
            if path.startswith("/api/gallery/"):
                p = app.photo_path(urllib.parse.unquote(path[len("/api/gallery/"):]))
                if not p:
                    return self._json({"error": "foto no encontrada"}, 404)
                data = p.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                disp = "attachment" if "download=1" in self.path else "inline"
                self.send_header("Content-Disposition", f'{disp}; filename="{p.name}"')
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/events":
                return self._sse()
            if path == "/api/camera/stream":
                return self._stream()
            if path == "/api/camera/frame":
                return self._frame()
            self._json({"error": "ruta no encontrada"}, 404)

        def _sse(self):
            q = app.hub.subscribe()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                self._sse_write("status", app.snapshot())
                while True:
                    try:
                        ev, data = q.get(timeout=15)
                        self._sse_write(ev, data)
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                app.hub.unsubscribe(q)

        def _sse_write(self, ev, data):
            self.wfile.write(f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.flush()

        def _frame(self):
            """Fotograma puntual para la vista 'en vivo' por fotos (no se guarda en la galería)."""
            try:
                status, body = app.camera_get("/capture", 8)
            except urllib.error.HTTPError as e:  # 409 = dispensando; 503 = cámara no detectada
                return self._json({"ok": False, "error": f"cámara: HTTP {e.code}"}, 409 if e.code == 409 else 503)
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 503)
            if status != 200 or not body.startswith(b"\xff\xd8") or len(body) > MAX_FOTO_BYTES:
                return self._json({"ok": False, "error": "JPEG inválido"}, 503)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _stream(self):
            """Proxy MJPEG. La cámara corta cada ~2 s: se reconecta de forma transparente."""
            if not app.camera_online:
                return self._json({"error": "cámara desconectada"}, 503)
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=esp32cam")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            fallos = 0
            try:
                while fallos < 5:
                    if not app.cam_lock.acquire(timeout=5):
                        fallos += 1
                        continue
                    try:
                        req = urllib.request.Request(app.camera_base() + "/stream")
                        with urllib.request.urlopen(req, timeout=5) as r:
                            fallos = 0
                            while True:
                                chunk = r.read(4096)
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    except Exception:
                        fallos += 1
                        time.sleep(0.5)
                    finally:
                        app.cam_lock.release()
            except OSError:
                pass

        # --- POST ---
        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/device/telemetry":
                if not self._device_auth():
                    return
                data = self._read_json()
                if data is None:
                    return
                if data.get("dispositivo") != "ESP32":
                    return self._json({"ok": False, "error": "dispositivo desconocido"}, 400)
                app.on_telemetry(data, self.client_address[0])
                return self._json({"ok": True})
            if path == "/api/device/alert":
                if not self._device_auth():
                    return
                data = self._read_json()
                if data is None:
                    return
                tipo = str(data.get("tipo", ""))[:32]
                if not re.fullmatch(r"[A-Z_]{1,32}", tipo):
                    return self._json({"ok": False, "error": "tipo de alerta inválido"}, 400)
                app.log("alerta", f"Alerta {tipo} (nivel {data.get('nivel', '?')} %)")
                return self._json({"ok": True})
            # --- acciones del dashboard ---
            if not self._dashboard_guard():
                return
            if path == "/api/capture":
                try:
                    return self._json({"ok": True, **app.capture("manual")})
                except Exception as e:
                    app.log("error", f"Captura fallida: {e}")
                    return self._json({"ok": False, "error": f"no se pudo capturar: {e}"}, 503)
            if path == "/api/dispense":
                data = self._read_json()
                if data is None:
                    return
                if data.get("confirm") is not True:  # sin confirmación explícita nunca se mueve el servo
                    return self._json({"ok": False, "error": "falta confirmación explícita (confirm: true)"}, 400)
                code, resp = app.dispense(data.get("porciones"))
                return self._json(resp, code)
            if path == "/api/reset-errors":
                if not app.cfg.token:
                    return self._json({"ok": False, "error": "control remoto deshabilitado"}, 403)
                code, resp = app.send_command("/reset-errores", {})
                app.log("estado", f"Borrar errores desde dashboard → HTTP {code}")
                return self._json(resp, code)
            if path == "/api/auto-capture":
                data = self._read_json()
                if data is None:
                    return
                s = data.get("interval_s")
                if isinstance(s, bool) or not isinstance(s, int) or not (s == 0 or 10 <= s <= 3600):
                    return self._json({"ok": False, "error": "interval_s debe ser 0 (apagado) o 10-3600"}, 400)
                app.set_auto_capture(s)
                app.push_status()
                return self._json({"ok": True, "auto_capture_s": s})
            if path == "/api/camera/refresh":
                app.poll_camera()
                return self._json({"ok": True, "online": app.camera_online})
            self._json({"error": "ruta no encontrada"}, 404)

        def do_DELETE(self):
            path = urllib.parse.urlparse(self.path).path
            if not self._dashboard_guard():
                return
            if path.startswith("/api/gallery/"):
                # El borrado exige confirmación explícita además de un nombre válido.
                if self.headers.get("X-Confirm") != "delete":
                    return self._json({"ok": False, "error": "falta confirmación de borrado"}, 400)
                p = app.photo_path(urllib.parse.unquote(path[len("/api/gallery/"):]))
                if not p:
                    return self._json({"ok": False, "error": "foto no encontrada"}, 404)
                p.unlink()
                app.log("foto", f"Foto {p.name} eliminada")
                app.push_status()
                return self._json({"ok": True, "deleted": p.name})
            self._json({"error": "ruta no encontrada"}, 404)

        def log_message(self, fmt, *args):  # sin ruido en consola
            return

    return Handler


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_server(cfg: Config) -> tuple[Server, App]:
    app = App(cfg)
    srv = Server((cfg.host, cfg.port), make_handler(app))
    if cfg.start_threads:
        app.start_background()
    return srv, app


def main():
    cargar_env(Path(__file__).resolve().parent / ".env")
    cfg = Config()
    srv, _ = create_server(cfg)
    print(f"Dashboard local: http://{cfg.host}:{cfg.port}  (use la IP LAN del PC desde el móvil)")
    if not cfg.token:
        print("Aviso: TOKEN_DISPOSITIVO vacío -> la dispensación remota queda deshabilitada.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
