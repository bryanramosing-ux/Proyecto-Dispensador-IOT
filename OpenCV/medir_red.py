"""
Mide los tiempos de la red LOCAL del dispensador, para responder con datos propios a
"¿conectado por Wi-Fi o de manera local?".

    python medir_red.py                           # IP de config.py, 10 repeticiones
    python medir_red.py --veces 20
    python medir_red.py --clasificar              # además mide /classify del servidor de este PC

Todo ocurre dentro de la red local (router o punto de acceso del celular): no usa Internet.
Mide, N veces cada uno:
  * ESP32      GET /status    ida y vuelta por Wi-Fi
  * ESP32-CAM  GET /status    ida y vuelta por Wi-Fi
  * ESP32-CAM  GET /capture   una foto (tiempo y tamaño)
  * PC         OpenCV + MobileNetV2 sobre esa foto (si el modelo está descargado)
  * PC         GET /classify  foto + análisis completo (solo con --clasificar y el servidor en marcha;
                              no dispensa nada: dispensar lo decide el ESP32)
y estima el tiempo desde que el HC-SR04 confirma a la mascota hasta la decisión.
"""
import argparse
import statistics
import time
import urllib.request
from pathlib import Path

import config


def medir(url, veces, timeout):
    """Devuelve (lista_ms, bytes_ultimo, error)."""
    tiempos, tam, error = [], 0, None
    for _ in range(veces):
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                datos = r.read()
            tiempos.append((time.perf_counter() - t0) * 1000)
            tam = len(datos)
        except Exception as e:  # noqa: BLE001 - se informa y se sigue
            error = str(e)
    return tiempos, tam, error


def fila(nombre, tiempos, extra="", error=None):
    if not tiempos:
        print(f"  {nombre:34s} sin respuesta ({error})")
        return None
    med = statistics.median(tiempos)
    print(f"  {nombre:34s} mediana {med:6.0f} ms   mín {min(tiempos):5.0f}   máx {max(tiempos):5.0f}   {extra}")
    return med


def main():
    ap = argparse.ArgumentParser(description="Tiempos de la red local del dispensador")
    ap.add_argument("--veces", type=int, default=10)
    ap.add_argument("--esp32", default=config.ESP32_URL)
    ap.add_argument("--camara", default=config.CAMARA_URL)
    ap.add_argument("--servidor", default=f"http://127.0.0.1:{config.PUERTO}")
    ap.add_argument("--clasificar", action="store_true", help="medir también GET /classify del servidor")
    a = ap.parse_args()

    print(f"Red local · {a.veces} repeticiones · ESP32 {a.esp32} · ESP32-CAM {a.camara}\n")
    t, _, err = medir(a.esp32.rstrip("/") + "/status", a.veces, 2)
    esp = fila("ESP32 /status (ida y vuelta)", t, error=err)
    t, _, err = medir(a.camara.rstrip("/") + "/status", a.veces, 2)
    cam = fila("ESP32-CAM /status (ida y vuelta)", t, error=err)
    t, tam, err = medir(a.camara.rstrip("/") + "/capture", a.veces, 3)
    foto = fila("ESP32-CAM /capture (1 foto)", t, f"{tam / 1024:.0f} kB" if tam else "", err)

    inferencia = None
    if Path(config.MODELO_ONNX).exists():
        import numpy as np
        from clasificador import ClasificadorMascotas, decodificar_jpeg, mejorar_contraste
        modelo = ClasificadorMascotas(config.MODELO_ONNX, config.ETIQUETAS)
        img = None
        if foto is not None:
            with urllib.request.urlopen(a.camara.rstrip("/") + "/capture", timeout=3) as r:
                img = decodificar_jpeg(r.read())
        if img is None:
            img = np.random.default_rng(0).integers(0, 255, (480, 640, 3), dtype=np.uint8)
        modelo.predecir(img)                                    # la primera ejecución calienta caché
        tiempos = []
        for _ in range(a.veces):
            t0 = time.perf_counter()
            modelo.predecir(mejorar_contraste(img))
            tiempos.append((time.perf_counter() - t0) * 1000)
        inferencia = fila("PC: OpenCV + MobileNetV2", tiempos, "(sin red)")
    else:
        print("  PC: OpenCV + MobileNetV2          modelo no descargado (python descargar_modelo.py)")

    if a.clasificar:
        t, _, err = medir(a.servidor.rstrip("/") + "/classify?dist=0", a.veces, 10)
        fila("PC /classify (foto + análisis)", t, error=err)

    print()
    if None not in (cam, foto, inferencia):
        total = cam + foto + inferencia + (esp or 0)
        print(f"Estimación: mascota confirmada -> decisión ≈ {total:.0f} ms "
              f"(consulta a la cámara + foto + análisis + respuesta al ESP32).")
        print(f"Si no se identifica a la primera, el ESP32 pide otra foto cada ~2 s (máx. 5 por visita).")
    print("Ningún paso usó Internet: las fotos no salen de la red local. Las alertas al celular (ntfy) son lo único\n"
          "opcional que necesita Internet; el panel web http://IP-DEL-PC:8000/ funciona sin él.")


if __name__ == "__main__":
    main()
