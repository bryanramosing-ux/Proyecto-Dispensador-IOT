from __future__ import annotations

import json
import os
import shutil
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
STORAGE_DIR = ROOT / "backend" / "storage"
GALLERY_DIR = STORAGE_DIR / "gallery"
HISTORY_PATH = STORAGE_DIR / "history.jsonl"

ESP32_CAM_URL = os.environ.get("ESP32_CAM_URL", "http://192.168.1.51")
ESP32_URL = os.environ.get("ESP32_URL", "http://192.168.1.52")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8001"))

GALLERY_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
if not HISTORY_PATH.exists():
    HISTORY_PATH.write_text("", encoding="utf-8")


def log_event(message: str) -> None:
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": datetime.utcnow().isoformat() + "Z", "message": message}) + "\n")


def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "local-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except Exception as exc:  # pragma: no cover - runtime only
        return {"error": str(exc), "status": "offline"}


def file_response(path: Path):
    data = path.read_bytes()
    return data, "application/octet-stream"


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._serve_file(FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._serve_file(FRONTEND_DIR / "styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._serve_file(FRONTEND_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/api/health":
            payload = {"status": "ok", "camera_url": ESP32_CAM_URL, "esp32_url": ESP32_URL}
            self._send_json(payload)
            return
        if parsed.path == "/api/status":
            camera = fetch_json(f"{ESP32_CAM_URL}/status")
            esp32 = fetch_json(f"{ESP32_URL}/status")
            payload = {
                "camera": camera,
                "esp32": esp32,
                "ts": datetime.utcnow().isoformat() + "Z",
                "dispense_manual_enabled": False,
                "notes": "La dispensación manual requiere confirmación física y validación de seguridad antes de habilitarse por red.",
            }
            self._send_json(payload)
            return
        if parsed.path == "/api/gallery":
            files = []
            for p in sorted(GALLERY_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if p.is_file():
                    files.append({
                        "name": p.name,
                        "size": p.stat().st_size,
                        "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat() + "Z",
                    })
            self._send_json({"items": files})
            return
        if parsed.path.startswith("/api/gallery/"):
            filename = parsed.path.removeprefix("/api/gallery/")
            target = GALLERY_DIR / filename
            if target.exists() and target.is_file():
                data, mime = file_response(target)
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Disposition", f"inline; filename={filename}")
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404, "foto no encontrada")
            return
        if parsed.path == "/api/capture":
            try:
                req = urllib.request.Request(f"{ESP32_CAM_URL}/capture", headers={"User-Agent": "local-dashboard/1.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    payload = resp.read()
                filename = f"capture_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                target = GALLERY_DIR / filename
                target.write_bytes(payload)
                log_event(f"captured {filename}")
                self._send_json({"ok": True, "filename": filename, "size": len(payload)})
                return
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=503)
                return
        if parsed.path == "/api/dispense":
            self._send_json({
                "ok": False,
                "status": "disabled",
                "message": "La dispensación manual desde red queda deshabilitada por seguridad. Debe confirmarse físicamente y calibrarse antes de activarla.",
            }, status=501)
            return
        if parsed.path == "/api/camera/stream":
            try:
                req = urllib.request.Request(f"{ESP32_CAM_URL}/stream", headers={"User-Agent": "local-dashboard/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    content_type = resp.headers.get_content_type()
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=esp32cam")
                    self.end_headers()
                    while True:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except Exception:
                self.send_error(503, "stream de cámara no disponible")
            return
        self.send_error(404, "ruta no encontrada")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/capture":
            self.do_GET()
            return
        if parsed.path == "/api/dispense":
            self._send_json({
                "ok": False,
                "status": "disabled",
                "message": "La dispensación manual desde red queda deshabilitada por seguridad. Debe confirmarse físicamente y calibrarse antes de activarla.",
            }, status=501)
            return
        self.send_error(404, "ruta no encontrada")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/gallery/"):
            filename = parsed.path.removeprefix("/api/gallery/")
            target = GALLERY_DIR / filename
            if target.exists():
                target.unlink()
                log_event(f"deleted {filename}")
                self._send_json({"ok": True, "deleted": filename})
                return
            self.send_error(404, "foto no encontrada")
            return
        self.send_error(404, "ruta no encontrada")

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404, "archivo no encontrado")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Dashboard local activo en http://{HOST}:{PORT}")
    server.serve_forever()

