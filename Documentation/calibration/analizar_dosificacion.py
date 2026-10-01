"""
Analiza la planilla de dosificación (plantilla_dosificacion.csv ya completada).

    python analizar_dosificacion.py plantilla_dosificacion.csv --objetivo-g 30

Calcula media, desviación estándar, coeficiente de variación (CV) y el número
de ciclos necesario para una ración objetivo. No inventa datos: si la planilla
está vacía, lo indica.
"""
import argparse
import csv
import math
import statistics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--objetivo-g", type=float, help="gramos deseados por ración")
    a = ap.parse_args()
    masas = []
    with open(a.csv, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            try:
                ciclos = int(fila["ciclos"])
                masas.append(float(fila["masa_g"]) / ciclos)
            except (ValueError, KeyError, ZeroDivisionError):
                continue
    if len(masas) < 3:
        raise SystemExit("Faltan mediciones: complete al menos 3 filas con masa_g (idealmente 10 o más).")
    media = statistics.mean(masas)
    desv = statistics.stdev(masas)
    cv = 100 * desv / media
    print(f"Mediciones: {len(masas)}")
    print(f"Gramos por ciclo: media {media:.2f} g | desv. estándar {desv:.2f} g | CV {cv:.1f} %")
    print(f"Rango observado: {min(masas):.2f} - {max(masas):.2f} g")
    if cv > 10:
        print("AVISO: CV > 10 %: revisar llenado del bolsillo (aumentar T_LLENADO_MS o AGITACIONES).")
    if a.objetivo_g:
        n = max(1, round(a.objetivo_g / media))
        error = 100 * (n * media - a.objetivo_g) / a.objetivo_g
        incert = math.sqrt(n) * desv
        print(f"Para {a.objetivo_g:.0f} g: CICLOS = {n} -> {n * media:.1f} g esperados "
              f"(error de redondeo {error:+.1f} %, +/- {incert:.1f} g por variación)")


if __name__ == "__main__":
    main()
