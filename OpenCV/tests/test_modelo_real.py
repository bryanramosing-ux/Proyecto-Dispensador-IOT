"""
Prueba con el MODELO REAL sobre fotos de ejemplo (se omite si no están disponibles).

Requiere:
  * python descargar_modelo.py
  * DISPENSADOR_IMAGENES_PRUEBA=<carpeta> con subcarpetas perro/ gato/ otros/

    DISPENSADOR_IMAGENES_PRUEBA=dataset python -m unittest tests.test_modelo_real -v

Criterio de seguridad: ninguna decisión peligrosa (perro clasificado como gato o al
revés, o "otros" clasificado como mascota).
"""
import os
import sys
import unittest
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from clasificador import ClasificadorMascotas, clasificar_imagenes  # noqa: E402

CARPETA = os.environ.get("DISPENSADOR_IMAGENES_PRUEBA")
ESPERADO = {"perro": 1, "gato": 2, "otros": 0}
EXT = {".jpg", ".jpeg", ".png", ".bmp"}


@unittest.skipUnless(CARPETA and Path(config.MODELO_ONNX).is_file(),
                     "falta el modelo o DISPENSADOR_IMAGENES_PRUEBA")
class TestModeloReal(unittest.TestCase):
    def test_sin_decisiones_peligrosas(self):
        clf = ClasificadorMascotas(config.MODELO_ONNX, config.ETIQUETAS)
        total, peligrosas, aciertos = 0, [], 0
        for sub, esperado in ESPERADO.items():
            for f in sorted((Path(CARPETA) / sub).glob("*")):
                if f.suffix.lower() not in EXT:
                    continue
                r = clasificar_imagenes(clf, [cv2.imread(str(f))], config)
                total += 1
                aciertos += r.clase == esperado
                if r.clase != 0 and r.clase != esperado:
                    peligrosas.append((f.name, esperado, r.clase))
                print(f"{sub:6s} {f.name:40s} -> {r.etiqueta:13s} {r.motivo:15s} "
                      f"perro={r.p_perro:.2f} gato={r.p_gato:.2f}")
        self.assertGreater(total, 0, "no se encontraron imágenes")
        self.assertEqual(peligrosas, [], "decisiones peligrosas")
        self.assertGreaterEqual(aciertos / total, 0.8)


if __name__ == "__main__":
    unittest.main()
