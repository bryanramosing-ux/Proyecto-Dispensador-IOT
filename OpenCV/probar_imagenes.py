"""
Prueba y CALIBRACIÓN del clasificador con imágenes guardadas.

1) Una imagen o carpeta suelta: muestra la decisión de cada imagen.
       python probar_imagenes.py foto.jpg
2) Conjunto de validación con subcarpetas  perro/  gato/  otros/
   (fotos REALES tomadas por la ESP32-CAM instalada, ver capturar_dataset.py):
       python probar_imagenes.py dataset/ --barrido
   Calcula la exactitud, la matriz de confusión y (con --barrido) prueba varios
   umbrales para elegir UMBRAL_CONFIANZA y MARGEN_MINIMO en config.py.

Regla de seguridad del barrido: se prefiere el umbral que NO produce errores
perro<->gato ni falsos positivos en "otros", aunque deje más casos en 0.
"""
import argparse
import itertools
from pathlib import Path

import cv2

import config
from clasificador import (ETIQUETAS_CLASE, ClasificadorMascotas, decidir,
                          evaluar_calidad, mejorar_contraste)

EXT = {".jpg", ".jpeg", ".png", ".bmp"}
ESPERADO = {"perro": 1, "gato": 2, "otros": 0}


def listar(ruta):
    ruta = Path(ruta)
    if ruta.is_file():
        return [(ruta, None)]
    pares = []
    for sub in sorted(p for p in ruta.iterdir() if p.is_dir()):
        esperado = ESPERADO.get(sub.name.lower())
        pares += [(f, esperado) for f in sorted(sub.rglob("*")) if f.suffix.lower() in EXT]
    pares += [(f, None) for f in sorted(ruta.glob("*")) if f.suffix.lower() in EXT]
    return pares


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ruta")
    ap.add_argument("--barrido", action="store_true", help="probar varios umbrales")
    args = ap.parse_args()

    clf = ClasificadorMascotas(config.MODELO_ONNX, config.ETIQUETAS)
    filas = []
    for archivo, esperado in listar(args.ruta):
        img = cv2.imread(str(archivo))
        cal = evaluar_calidad(img, config.BRILLO_MIN, config.BRILLO_MAX, config.NITIDEZ_MIN)
        if not cal.valida:
            print(f"{archivo.name:40s} {cal.motivo:22s} brillo={cal.brillo:6.1f} nitidez={cal.nitidez:7.1f}")
            filas.append((esperado, None, None))
            continue
        p = clf.predecir(mejorar_contraste(img))
        clase, motivo = decidir(p.p_perro, p.p_gato, config.UMBRAL_CONFIANZA,
                                config.MARGEN_MINIMO, config.MIN_PROB_ANIMAL)
        print(f"{archivo.name:40s} {ETIQUETAS_CLASE[clase]:13s} {motivo:15s} "
              f"perro={p.p_perro:.3f} gato={p.p_gato:.3f} top={p.top_etiqueta} ({p.top_prob:.2f}) "
              f"brillo={cal.brillo:.0f} nitidez={cal.nitidez:.0f}")
        filas.append((esperado, p.p_perro, p.p_gato))

    con_etiqueta = [f for f in filas if f[0] is not None]
    if not con_etiqueta:
        return

    def evaluar(umbral, margen, min_animal):
        matriz = {(e, o): 0 for e in (0, 1, 2) for o in (0, 1, 2)}
        for esperado, pp, pg in con_etiqueta:
            obtenido = 0 if pp is None else decidir(pp, pg, umbral, margen, min_animal)[0]
            matriz[(esperado, obtenido)] += 1
        peligrosos = matriz[(1, 2)] + matriz[(2, 1)] + matriz[(0, 1)] + matriz[(0, 2)]
        aciertos = sum(matriz[(c, c)] for c in (0, 1, 2))
        return matriz, peligrosos, aciertos / len(con_etiqueta)

    matriz, peligrosos, exactitud = evaluar(config.UMBRAL_CONFIANZA, config.MARGEN_MINIMO,
                                            config.MIN_PROB_ANIMAL)
    print("\nMatriz de confusión (filas = real, columnas = obtenido 0/1/2):")
    for e in (0, 1, 2):
        print(f"  real {ETIQUETAS_CLASE[e]:13s}", [matriz[(e, o)] for o in (0, 1, 2)])
    print(f"Exactitud: {exactitud:.1%}   Decisiones peligrosas (dispensar mal): {peligrosos}")

    if args.barrido:
        print("\numbral margen  exactitud  peligrosos")
        mejores = []
        for u, m in itertools.product([0.5, 0.6, 0.7, 0.8, 0.9], [0.1, 0.2, 0.3, 0.4, 0.5]):
            _, pel, ex = evaluar(u, m, config.MIN_PROB_ANIMAL)
            mejores.append((pel, -ex, -u, -m))
            print(f"  {u:.2f}  {m:.2f}    {ex:6.1%}     {pel}")
        pel, ex, u, m = min(mejores)
        u, m = -u, -m  # a igualdad de resultados se prefiere el umbral más estricto
        print(f"\nSugerencia: UMBRAL_CONFIANZA={u}  MARGEN_MINIMO={m}  "
              f"(exactitud {-ex:.1%}, peligrosos {pel}). Verifique con más fotos.")


if __name__ == "__main__":
    main()
