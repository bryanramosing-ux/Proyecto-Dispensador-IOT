"""Carga dispensador.env y arranca el servidor. Acepta sus mismos argumentos."""
import os
import sys
from pathlib import Path


def cargar_entorno(ruta):
    if not ruta.is_file():
        return
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        clave, sep, valor = linea.partition("=")
        clave = clave.strip()
        if not sep or not clave.startswith("DISPENSADOR_") or not clave.replace("_", "").isalnum():
            raise ValueError(f"{ruta}:{numero}: use DISPENSADOR_NOMBRE=valor")
        os.environ.setdefault(clave, valor.strip().strip("\"'"))


def main():
    try:
        cargar_entorno(Path(__file__).with_name("dispensador.env"))
        from servidor_vision import main as servidor
        servidor()
    except (ImportError, FileNotFoundError, ValueError) as e:
        sys.exit(f"No se puede iniciar: {e}\nEjecute comprobar_instalacion.py y siga la guía de calibración.")


if __name__ == "__main__":
    main()
