"""Diagnóstico sin movimiento del motor: modelo, dependencias y /status opcionales."""
import argparse
import importlib
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from iniciar import cargar_entorno


def comprobar(red=False):
    cargar_entorno(Path(__file__).with_name("dispensador.env"))
    import config
    from descargar_modelo import ARCHIVOS, sha256

    errores = []
    cv = None
    for nombre in ("numpy", "cv2"):
        try:
            modulo = importlib.import_module(nombre)
            print(f"[OK] {nombre} {modulo.__version__}")
            if nombre == "cv2":
                cv = modulo
        except ImportError:
            errores.append(f"Falta {nombre}: pip install -r requirements.txt")
    modelo = Path(config.MODELO_ONNX)
    if not modelo.is_file():
        errores.append("Falta modelo: python descargar_modelo.py")
    elif modelo.name == ARCHIVOS[0][0] and sha256(modelo) != ARCHIVOS[0][2]:
        errores.append("Modelo dañado: vuelva a ejecutar descargar_modelo.py")
    elif cv:
        try:
            cv.dnn.readNetFromONNX(str(modelo))
            print("[OK] Modelo ONNX cargable")
        except cv.error as e:
            errores.append(f"Modelo incompatible: {e}")
    for nombre, url in (("CAMARA_URL", config.CAMARA_URL), ("ESP32_URL", config.ESP32_URL)):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            errores.append(f"{nombre} inválida: {url}")
            continue
        if red:
            try:
                with urllib.request.urlopen(url.rstrip("/") + "/status", timeout=3) as respuesta:
                    datos = json.load(respuesta)
                if not isinstance(datos, dict):
                    raise ValueError("/status no devuelve un objeto JSON")
                if nombre == "CAMARA_URL" and datos.get("camara") is not True:
                    raise ValueError("la cámara no indica camara=true")
                if nombre == "ESP32_URL" and "estado" not in datos:
                    raise ValueError("falta estado del controlador")
                print(f"[OK] {nombre}: {datos}")
                if str(datos.get("estado", "")).startswith("ERROR_"):
                    errores.append(f"El controlador requiere atención: {datos['estado']}")
            except Exception as e:
                errores.append(f"{nombre}: {e}")
    for error in errores:
        print(f"[FALTA] {error}")
    print("La calibración física y las URL del firmware se verifican en el montaje.")
    return not errores


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--red", action="store_true", help="consultar solo /status de las placas")
    args = ap.parse_args()
    try:
        ok = comprobar(args.red)
    except (ValueError, OSError) as e:
        sys.exit(str(e))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
