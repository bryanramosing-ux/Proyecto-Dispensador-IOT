"""
Configuración del servidor de visión (PC / notebook).

TODOS los umbrales marcados como PROVISIONAL deben ajustarse con imágenes
reales tomadas por la ESP32-CAM instalada en la torre (ver
Documentation/calibration/calibracion.md y probar_imagenes.py).

Cualquier valor puede sobrescribirse con variables de entorno del mismo nombre
precedidas de DISPENSADOR_ (por ejemplo DISPENSADOR_CAMARA_URL) o con los
argumentos de línea de comandos de servidor_vision.py.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _env(nombre, defecto, tipo=str):
    valor = os.environ.get("DISPENSADOR_" + nombre)
    return defecto if valor is None else tipo(valor)


# --- Red ----------------------------------------------------------------------
# IP fija de la ESP32-CAM (debe coincidir con ESP32_CAM/Camara_ESP32CAM/config.h)
CAMARA_URL = _env("CAMARA_URL", "http://192.168.1.51")
# Dirección y puerto donde escucha este servidor (el ESP32 llama a PC_IP:PUERTO)
HOST = _env("HOST", "0.0.0.0")
PUERTO = _env("PUERTO", 8000, int)
TIMEOUT_CAMARA_S = _env("TIMEOUT_CAMARA_S", 3.0, float)

# --- Modelo -------------------------------------------------------------------
# MobileNetV2 entrenado en ImageNet (ONNX Model Zoo, licencia Apache-2.0).
# Se descarga con: python descargar_modelo.py
MODELO_ONNX = _env("MODELO_ONNX", str(BASE_DIR / "model" / "mobilenetv2-12.onnx"))
ETIQUETAS = _env("ETIQUETAS", str(BASE_DIR / "model" / "imagenet_classes.txt"))

# --- Decisión (PROVISIONAL: calibrar con probar_imagenes.py) -------------------
# Probabilidad mínima agregada de la clase ganadora (perro o gato).
UMBRAL_CONFIANZA = _env("UMBRAL_CONFIANZA", 0.60, float)
# Diferencia mínima entre P(perro) y P(gato) para no considerar el caso ambiguo.
MARGEN_MINIMO = _env("MARGEN_MINIMO", 0.30, float)
# Si P(perro)+P(gato) es menor que esto, en la imagen no hay perro ni gato.
MIN_PROB_ANIMAL = _env("MIN_PROB_ANIMAL", 0.50, float)

# --- Calidad de imagen (PROVISIONAL: calibrar con la cámara instalada) ---------
BRILLO_MIN = _env("BRILLO_MIN", 35.0, float)      # media de gris 0-255
BRILLO_MAX = _env("BRILLO_MAX", 225.0, float)
NITIDEZ_MIN = _env("NITIDEZ_MIN", 40.0, float)    # varianza del Laplaciano
ANCHO_MIN = 160
ALTO_MIN = 120

# Número de fotos por clasificación. Se promedian las probabilidades de las
# fotos válidas: reduce errores por una foto movida o mal encuadrada.
FOTOS_POR_CLASIFICACION = _env("FOTOS_POR_CLASIFICACION", 2, int)

# --- Registro -----------------------------------------------------------------
GUARDAR_CAPTURAS = _env("GUARDAR_CAPTURAS", 1, int) == 1
DIR_CAPTURAS = _env("DIR_CAPTURAS", str(BASE_DIR / "capturas"))

# --- ESP32 y alertas ------------------------------------------------------------
# IP del ESP32 controlador (el panel web del PC consulta su /status)
ESP32_URL = _env("ESP32_URL", "http://192.168.1.52")
# Notificación al celular con ntfy (opcional, requiere Internet en el PC):
# instale la app "ntfy" en el celular, suscríbase a un tema con nombre difícil de
# adivinar (p. ej. "dispensador-ana-7f3k9") y escriba ese nombre aquí.
NTFY_TOPICO = _env("NTFY_TOPICO", "")
NTFY_SERVIDOR = _env("NTFY_SERVIDOR", "https://ntfy.sh")
