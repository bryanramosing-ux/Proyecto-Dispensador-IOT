"""Prepara web/laminas.json (y copia las imágenes a web/img) para render_laminas.mjs."""
import json
import shutil
from pathlib import Path

import guion

RAIZ = Path(__file__).resolve().parents[3]
WEB = Path(__file__).resolve().parent / "web"


def img(ruta):
    origen = RAIZ / ruta
    destino = WEB / "img" / Path(ruta).name
    if origen.exists():
        shutil.copy(origen, destino)
    elif not destino.exists():
        raise SystemExit(f"falta la imagen {ruta}")
    return "img/" + Path(ruta).name


def main():
    (WEB / "img").mkdir(exist_ok=True)
    salida = []
    for e in guion.ESCENAS:
        if e["tipo"] == "lamina":
            d = {k: v for k, v in e.items() if k != "frases"}
            if "imagen" in d:
                d["imagen"] = img(d["imagen"])
            if "imagenes" in d:
                d["imagenes"] = [img(x) for x in d["imagenes"]]
            salida.append(d)
        elif e["tipo"] == "paneo":
            img(e["imagen"])
            salida.append({"id": e["id"], "titulo": e["titulo"], "transparente": True})
    (WEB / "laminas.json").write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    print(len(salida), "láminas")


if __name__ == "__main__":
    main()
