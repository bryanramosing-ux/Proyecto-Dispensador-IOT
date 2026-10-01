"""
Simulador de la ESP32-CAM para probar el PC sin hardware.

Sirve /capture (JPEG) y /status igual que el firmware real. Las imágenes se
toman de una carpeta (rotando) o de un archivo.

    python simulador_camara.py --imagenes ruta/a/fotos --puerto 8081
    python servidor_vision.py --camara http://127.0.0.1:8081
"""
import argparse
import itertools
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imagenes", required=True, help="archivo o carpeta de imágenes")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--puerto", type=int, default=8081)
    args = ap.parse_args()

    import cv2  # solo para convertir PNG/BMP a JPEG como la cámara real
    origen = Path(args.imagenes)
    rutas = sorted(p for p in origen.iterdir() if p.suffix.lower() in EXT) if origen.is_dir() else [origen]
    if not rutas:
        raise SystemExit("No hay imágenes en " + str(origen))
    ciclo = itertools.cycle(rutas)
    servidas = {"n": 0}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.startswith("/capture"):
                ruta = next(ciclo)
                ok, jpg = cv2.imencode(".jpg", cv2.imread(str(ruta)), [cv2.IMWRITE_JPEG_QUALITY, 85])
                cuerpo, tipo = jpg.tobytes(), "image/jpeg"
                servidas["n"] += 1
            elif self.path.startswith("/status"):
                cuerpo = json.dumps({"camara": "SIMULADA", "fotos": servidas["n"]}).encode()
                tipo = "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *a):
            pass

    print(f"Camara simulada en http://{args.host}:{args.puerto} con {len(rutas)} imagen(es)")
    ThreadingHTTPServer((args.host, args.puerto), H).serve_forever()


if __name__ == "__main__":
    main()
