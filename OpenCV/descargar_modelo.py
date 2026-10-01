"""
Descarga el modelo MobileNetV2 (ONNX Model Zoo, Apache-2.0) y las etiquetas de
ImageNet, y verifica su SHA-256. Solo hace falta ejecutarlo una vez (requiere
Internet); después el sistema funciona sin conexión a Internet.

    python descargar_modelo.py
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

DESTINO = Path(__file__).resolve().parent / "model"
ARCHIVOS = [
    ("mobilenetv2-12.onnx",
     "https://media.githubusercontent.com/media/onnx/models/main/validated/vision/"
     "classification/mobilenet/model/mobilenetv2-12.onnx",
     "c0c3f76d93fa3fd6580652a45618618a220fced18babf65774ed169de0432ad5"),
    ("imagenet_classes.txt",
     "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt",
     "1f386e0d1cb6e28b9c2dac651c3dea6801e98ad1b41a14ce6bb1a093d72069f5"),
]


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    DESTINO.mkdir(exist_ok=True)
    ok = True
    for nombre, url, suma in ARCHIVOS:
        ruta = DESTINO / nombre
        if ruta.is_file() and sha256(ruta) == suma:
            print(f"[OK] {nombre} ya existe y es correcto")
            continue
        print(f"Descargando {nombre} ...")
        urllib.request.urlretrieve(url, ruta)
        if sha256(ruta) != suma:
            print(f"[ERROR] SHA-256 de {nombre} no coincide. Archivo dañado o cambiado.")
            ok = False
        else:
            print(f"[OK] {nombre} ({ruta.stat().st_size} bytes)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
