"""
Toma fotos desde la ESP32-CAM instalada para armar el conjunto de calibración.

    python capturar_dataset.py --clase perro --cantidad 30 --intervalo 2
Las fotos quedan en dataset/<clase>/. Use clases: perro, gato, otros.
"""
import argparse
import time
from datetime import datetime
from pathlib import Path

import config
from servidor_vision import CamaraNoResponde, descargar_foto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clase", required=True, choices=["perro", "gato", "otros"])
    ap.add_argument("--cantidad", type=int, default=20)
    ap.add_argument("--intervalo", type=float, default=2.0)
    ap.add_argument("--camara", default=config.CAMARA_URL)
    args = ap.parse_args()

    carpeta = Path(__file__).resolve().parent / "dataset" / args.clase
    carpeta.mkdir(parents=True, exist_ok=True)
    for i in range(args.cantidad):
        try:
            datos = descargar_foto(args.camara, config.TIMEOUT_CAMARA_S)
        except CamaraNoResponde as e:
            print("Camara no responde:", e)
            time.sleep(args.intervalo)
            continue
        nombre = carpeta / f"{datetime.now():%Y%m%d_%H%M%S}_{i:03d}.jpg"
        nombre.write_bytes(datos)
        print(f"[{i + 1}/{args.cantidad}] {nombre.name} ({len(datos)} bytes)")
        time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
