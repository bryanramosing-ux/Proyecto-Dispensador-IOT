"""
Descarga un conjunto PÚBLICO de imágenes de prueba (muestras de ImageNet del
repositorio EliSchwartz/imagenet-sample-images) en perro/ gato/ otros/.

    python tests/descargar_imagenes_prueba.py imagenes_prueba
    DISPENSADOR_IMAGENES_PRUEBA=imagenes_prueba python -m unittest tests.test_modelo_real -v

"otros" contiene animales parecidos (lobo, coyote, dingo, zorros, hiena, puma, lince,
tigre, guepardo) y un oso de peluche: el sistema NO debe dispensar con ellos.

AVISO: son imágenes de ImageNet, el mismo conjunto con el que se entrenó el modelo,
así que el resultado es optimista. La calibración real se hace con fotos de la
ESP32-CAM instalada (capturar_dataset.py).
"""
import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/EliSchwartz/imagenet-sample-images/master/"
CONJUNTO = {
    "perro": ["n02085620_Chihuahua", "n02088364_beagle", "n02095314_wire-haired_fox_terrier",
              "n02099601_golden_retriever", "n02099712_Labrador_retriever", "n02106662_German_shepherd",
              "n02110185_Siberian_husky", "n02110958_pug", "n02113799_standard_poodle"],
    "gato": ["n02123045_tabby", "n02123159_tiger_cat", "n02123394_Persian_cat",
             "n02123597_Siamese_cat", "n02124075_Egyptian_cat"],
    "otros": ["n02114367_timber_wolf", "n02114855_coyote", "n02115641_dingo", "n02117135_hyena",
              "n02119022_red_fox", "n02120079_Arctic_fox", "n02125311_cougar", "n02127052_lynx",
              "n02129604_tiger", "n02130308_cheetah", "n04399382_teddy"],
}


def main():
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "imagenes_prueba")
    for clase, nombres in CONJUNTO.items():
        (destino / clase).mkdir(parents=True, exist_ok=True)
        for n in nombres:
            ruta = destino / clase / f"{n}.JPEG"
            if not ruta.is_file():
                urllib.request.urlretrieve(BASE + n + ".JPEG", ruta)
    print(f"{sum(len(v) for v in CONJUNTO.values())} imágenes en {destino}")


if __name__ == "__main__":
    main()
