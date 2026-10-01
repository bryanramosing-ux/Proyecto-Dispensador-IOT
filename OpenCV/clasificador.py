"""
Clasificador PERRO / GATO con Python + OpenCV.

Reparto de responsabilidades (no se mezclan):
  * ESP32-CAM ........ solo captura y entrega un JPEG.
  * Python ........... ejecuta este programa en el PC.
  * OpenCV ........... decodifica, evalúa la calidad, mejora el contraste y
                       prepara el tensor (blob); además ejecuta la red con su
                       módulo cv2.dnn.
  * Modelo ........... MobileNetV2 (ImageNet, 1000 clases). Es quien
                       "interpreta" la imagen. OpenCV por sí solo NO sabe qué es
                       un perro o un gato.

Cómo se obtienen P(perro) y P(gato):
  ImageNet no tiene una clase "perro" genérica sino 118 razas (índices 151-268)
  y 5 gatos domésticos (índices 281-285: tabby, tiger cat, Persian, Siamese,
  Egyptian cat). Se aplica softmax a las 1000 salidas y se SUMAN las
  probabilidades de cada grupo.

Resultado:  1 = PERRO, 2 = GATO, 0 = INDETERMINADO (no dispensar).
"""
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

CLASE_INDETERMINADA = 0
CLASE_PERRO = 1
CLASE_GATO = 2
ETIQUETAS_CLASE = {0: "INDETERMINADO", 1: "PERRO", 2: "GATO"}

# Índices ImageNet-1k (0-based)
INDICES_PERRO = np.arange(151, 269)
INDICES_GATO = np.arange(281, 286)

# Normalización con la que fue entrenado MobileNetV2 (ONNX Model Zoo)
_MEDIA = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
_DESV = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)
_TAM_ENTRADA = (224, 224)


@dataclass
class Calidad:
    valida: bool
    motivo: str
    brillo: float = 0.0
    nitidez: float = 0.0


@dataclass
class Prediccion:
    p_perro: float
    p_gato: float
    top_indice: int
    top_prob: float
    top_etiqueta: str = ""


@dataclass
class Resultado:
    clase: int
    motivo: str
    confianza: float = 0.0
    p_perro: float = 0.0
    p_gato: float = 0.0
    fotos_validas: int = 0
    detalles: list = field(default_factory=list)

    @property
    def etiqueta(self):
        return ETIQUETAS_CLASE[self.clase]

    def a_dict(self):
        return {
            "clase": self.clase,
            "etiqueta": self.etiqueta,
            "confianza": round(self.confianza, 3),
            "motivo": self.motivo,
            "p_perro": round(self.p_perro, 3),
            "p_gato": round(self.p_gato, 3),
            "fotos_validas": self.fotos_validas,
        }


# --------------------------------------------------------------------------
# Calidad de imagen (OpenCV)
# --------------------------------------------------------------------------
def decodificar_jpeg(datos: bytes):
    """Devuelve la imagen BGR o None si los bytes no son una imagen válida."""
    if not datos:
        return None
    buffer = np.frombuffer(datos, dtype=np.uint8)
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def evaluar_calidad(img, brillo_min, brillo_max, nitidez_min, ancho_min=160, alto_min=120):
    if img is None or img.size == 0:
        return Calidad(False, "IMAGEN_INVALIDA")
    alto, ancho = img.shape[:2]
    if ancho < ancho_min or alto < alto_min:
        return Calidad(False, "IMAGEN_INVALIDA")
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brillo = float(gris.mean())
    # Varianza del Laplaciano: medida clásica de enfoque (bordes nítidos => alta)
    nitidez = float(cv2.Laplacian(gris, cv2.CV_64F).var())
    if brillo < brillo_min:
        return Calidad(False, "IMAGEN_OSCURA", brillo, nitidez)
    if brillo > brillo_max:
        return Calidad(False, "IMAGEN_SOBREEXPUESTA", brillo, nitidez)
    if nitidez < nitidez_min:
        return Calidad(False, "IMAGEN_BORROSA", brillo, nitidez)
    return Calidad(True, "OK", brillo, nitidez)


def mejorar_contraste(img):
    """CLAHE sobre la luminancia: ayuda con la iluminación pobre de interiores."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return cv2.cvtColor(cv2.merge((clahe.apply(l), a, b)), cv2.COLOR_LAB2BGR)


# --------------------------------------------------------------------------
# Modelo
# --------------------------------------------------------------------------
class ClasificadorMascotas:
    def __init__(self, ruta_modelo, ruta_etiquetas=None):
        ruta_modelo = Path(ruta_modelo)
        if not ruta_modelo.is_file():
            raise FileNotFoundError(
                f"No existe el modelo {ruta_modelo}. Ejecute: python descargar_modelo.py")
        self.red = cv2.dnn.readNetFromONNX(str(ruta_modelo))
        self.etiquetas = []
        if ruta_etiquetas and Path(ruta_etiquetas).is_file():
            self.etiquetas = [l.strip() for l in Path(ruta_etiquetas).read_text().splitlines()]

    def predecir(self, img_bgr) -> Prediccion:
        # blobFromImage: redimensiona a 224x224, BGR->RGB y escala a [0,1]
        blob = cv2.dnn.blobFromImage(img_bgr, 1.0 / 255.0, _TAM_ENTRADA,
                                     (0, 0, 0), swapRB=True, crop=False)
        blob = ((blob - _MEDIA) / _DESV).astype(np.float32)
        self.red.setInput(blob)
        logits = self.red.forward().reshape(-1).astype(np.float64)
        prob = np.exp(logits - logits.max())
        prob /= prob.sum()
        top = int(prob.argmax())
        etiqueta = self.etiquetas[top] if top < len(self.etiquetas) else str(top)
        return Prediccion(float(prob[INDICES_PERRO].sum()), float(prob[INDICES_GATO].sum()),
                          top, float(prob[top]), etiqueta)


# --------------------------------------------------------------------------
# Regla de decisión (función pura: se prueba sin cámara ni modelo)
# --------------------------------------------------------------------------
def decidir(p_perro, p_gato, umbral, margen, min_animal):
    """Devuelve (clase, motivo). Ante cualquier duda: 0 = no dispensar."""
    if p_perro + p_gato < min_animal:
        return CLASE_INDETERMINADA, "SIN_MASCOTA"
    if max(p_perro, p_gato) < umbral:
        return CLASE_INDETERMINADA, "BAJA_CONFIANZA"
    if abs(p_perro - p_gato) < margen:
        return CLASE_INDETERMINADA, "AMBIGUO"
    return (CLASE_PERRO, "OK") if p_perro > p_gato else (CLASE_GATO, "OK")


def clasificar_imagenes(clasificador, imagenes, cfg) -> Resultado:
    """
    imagenes: lista de imágenes BGR (None si la descarga/decodificación falló).
    cfg: objeto/módulo con los umbrales (ver config.py).
    """
    detalles, perros, gatos = [], [], []
    ultimo_motivo = "IMAGEN_INVALIDA"
    for img in imagenes:
        cal = evaluar_calidad(img, cfg.BRILLO_MIN, cfg.BRILLO_MAX, cfg.NITIDEZ_MIN,
                              cfg.ANCHO_MIN, cfg.ALTO_MIN)
        info = {"calidad": cal.motivo, "brillo": round(cal.brillo, 1),
                "nitidez": round(cal.nitidez, 1)}
        if not cal.valida:
            ultimo_motivo = cal.motivo
            detalles.append(info)
            continue
        pred = clasificador.predecir(mejorar_contraste(img))
        info.update(p_perro=round(pred.p_perro, 3), p_gato=round(pred.p_gato, 3),
                    top=pred.top_etiqueta, top_prob=round(pred.top_prob, 3))
        detalles.append(info)
        perros.append(pred.p_perro)
        gatos.append(pred.p_gato)

    if not perros:
        return Resultado(CLASE_INDETERMINADA, ultimo_motivo, detalles=detalles)

    p_perro, p_gato = float(np.mean(perros)), float(np.mean(gatos))
    clase, motivo = decidir(p_perro, p_gato, cfg.UMBRAL_CONFIANZA, cfg.MARGEN_MINIMO,
                            cfg.MIN_PROB_ANIMAL)
    return Resultado(clase, motivo, max(p_perro, p_gato), p_perro, p_gato,
                     len(perros), detalles)
