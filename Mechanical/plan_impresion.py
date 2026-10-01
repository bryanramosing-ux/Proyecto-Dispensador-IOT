"""
Plan de impresión para la Elegoo Neptune 4 Plus (volumen 320 x 320 x 385 mm).

    python generar_stl.py        # primero: crea STL/ (piezas ya orientadas)
    python plan_impresion.py     # placas por material + filamento y tiempo estimados

1. Agrupa las piezas por material y las acomoda en placas de 310 x 310 mm (5 mm de margen
   por lado para la falda), con 8 mm entre piezas. Dibuja render/placas_impresion.png.
2. Si PrusaSlicer está instalado (prusa-slicer en el PATH), lamina CADA pieza con un perfil
   equivalente al de la Neptune 4 Plus (PERFIL, abajo) y anota filamento (g) y tiempo.
   Los gramos son fiables; el tiempo es orientativo (depende de las velocidades que use).
3. Escribe plan_impresion.md.
"""
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

import generar_stl as g  # noqa: E402

BASE = Path(__file__).resolve().parent
CAMA = 310.0                 # útil (320 nominal - 2 x 5 mm)
SEPARACION = 8.0

# Material por pieza. PETG: contacto con el alimento (y la tapa, que está sobre él), la
# estación solar (exterior, sol), la viga del servo (06) y el cajón de energía (16, calor de
# los convertidores). PLA: el resto de la estructura, dentro de la casa.
PETG = {"06", "07", "08b", "08c", "08d", "09", "10", "11", "12a", "12b", "13a", "13b", "13c", "16"}
RELLENO_40 = {"06", "08b", "16", "12a", "12b"}      # piezas que trabajan (servo, disco, cajón, intemperie)

# Perfil de laminado equivalente al de la Neptune 4 Plus (boquilla 0,4; Klipper). Velocidades
# moderadas (la impresora admite más): el resultado importa más que el tiempo.
PERFIL = {
    "printer_model": "", "gcode_flavor": "klipper", "bed_shape": "0x0,320x0,320x320,0x320",
    "max_print_height": 385, "nozzle_diameter": 0.4, "layer_height": 0.2, "first_layer_height": 0.2,
    "perimeters": 3, "top_solid_layers": 5, "bottom_solid_layers": 4, "fill_pattern": "gyroid",
    "fill_density": "20%", "support_material": 0, "skirts": 1, "skirt_distance": 4, "brim_width": 0,
    "perimeter_speed": 120, "external_perimeter_speed": 80, "infill_speed": 200, "solid_infill_speed": 120,
    "top_solid_infill_speed": 80, "first_layer_speed": 40, "travel_speed": 300, "bridge_speed": 40,
    "gap_fill_speed": 60, "small_perimeter_speed": 40, "default_acceleration": 3000,
    "perimeter_acceleration": 2500, "infill_acceleration": 4000, "first_layer_acceleration": 1000,
    "machine_limits_usage": "time_estimate_only", "machine_max_acceleration_x": 10000,
    "machine_max_acceleration_y": 10000, "machine_max_acceleration_extruding": 10000,
    "machine_max_feedrate_x": 500, "machine_max_feedrate_y": 500, "filament_diameter": 1.75,
}
FILAMENTO = {"PLA": {"filament_density": 1.24, "filament_max_volumetric_speed": 18, "temperature": 210,
                     "bed_temperature": 60},
             "PETG": {"filament_density": 1.27, "filament_max_volumetric_speed": 12, "temperature": 240,
                      "bed_temperature": 75}}


def codigo(nombre):
    return nombre.split("_")[0]


def material(nombre):
    return "PETG" if codigo(nombre) in PETG else "PLA"


def contorno_2d(malla):
    """Envolvente convexa de la proyección en XY (cadena monótona)."""
    p = np.unique(np.round(malla.vertices[:, :2], 2), axis=0)
    p = p[np.lexsort((p[:, 1], p[:, 0]))]

    def cruz(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    inf, sup = [], []
    for q in p:
        while len(inf) >= 2 and cruz(inf[-2], inf[-1], q) <= 0:
            inf.pop()
        inf.append(q)
    for q in p[::-1]:
        while len(sup) >= 2 and cruz(sup[-2], sup[-1], q) <= 0:
            sup.pop()
        sup.append(q)
    return np.array(inf[:-1] + sup[:-1])


class Placa:
    """Empaquetado MaxRects (mejor ajuste por el lado corto) con giro de 90°."""

    def __init__(self, mat):
        self.mat, self.libres, self.piezas = mat, [(0.0, 0.0, CAMA, CAMA)], []

    def colocar(self, nombre, w, h):
        mejor = None
        for x, y, fw, fh in self.libres:
            for ww, hh, giro in ((w, h, False), (h, w, True)):
                if ww + SEPARACION <= fw + SEPARACION + 1e-6 and ww <= fw and hh <= fh:
                    puntaje = (min(fw - ww, fh - hh), max(fw - ww, fh - hh))
                    if mejor is None or puntaje < mejor[0]:
                        mejor = (puntaje, x, y, ww, hh, giro)
        if mejor is None:
            return False
        _, x, y, ww, hh, giro = mejor
        self.piezas.append((nombre, x, y, ww, hh, giro))
        usado = (x, y, ww + SEPARACION, hh + SEPARACION)
        nuevos = []
        for f in self.libres:
            if not (usado[0] < f[0] + f[2] and usado[0] + usado[2] > f[0] and
                    usado[1] < f[1] + f[3] and usado[1] + usado[3] > f[1]):
                nuevos.append(f)
                continue
            fx, fy, fw, fh = f
            if usado[0] > fx:
                nuevos.append((fx, fy, usado[0] - fx, fh))
            if usado[0] + usado[2] < fx + fw:
                nuevos.append((usado[0] + usado[2], fy, fx + fw - usado[0] - usado[2], fh))
            if usado[1] > fy:
                nuevos.append((fx, fy, fw, usado[1] - fy))
            if usado[1] + usado[3] < fy + fh:
                nuevos.append((fx, usado[1] + usado[3], fw, fy + fh - usado[1] - usado[3]))
        self.libres = [a for a in nuevos if a[2] > 1 and a[3] > 1 and not any(
            b is not a and b[0] <= a[0] and b[1] <= a[1] and b[0] + b[2] >= a[0] + a[2] and
            b[1] + b[3] >= a[1] + a[3] for b in nuevos)]
        return True


def laminar(stl, mat, relleno):
    """Devuelve (gramos, metros, minutos) o None si PrusaSlicer no está disponible."""
    exe = None if "--sin-laminar" in sys.argv else shutil.which("prusa-slicer")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        ini = Path(tmp) / "perfil.ini"
        cfg = {**PERFIL, **FILAMENTO[mat], "fill_density": relleno,
               "first_layer_temperature": FILAMENTO[mat]["temperature"],
               "first_layer_bed_temperature": FILAMENTO[mat]["bed_temperature"]}
        ini.write_text("\n".join(f"{k} = {v}" for k, v in cfg.items()) + "\n")
        salida = Path(tmp) / "pieza.gcode"
        r = subprocess.run([exe, "--export-gcode", "--load", str(ini), "--center", "160,160",
                            "-o", str(salida), str(stl)], capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not salida.exists():
            print("  PrusaSlicer falló con", stl.name, r.stderr[-300:])
            return None
        txt = salida.read_text(errors="ignore")[-20000:]
    gramos = float(re.search(r"filament used \[g\] = ([\d.]+)", txt).group(1))
    metros = float(re.search(r"filament used \[mm\] = ([\d.]+)", txt).group(1)) / 1000
    t = re.search(r"estimated printing time \(normal mode\) = (.+)", txt).group(1)
    minutos = sum(int(n) * {"d": 1440, "h": 60, "m": 1, "s": 1 / 60}[u] for n, u in re.findall(r"(\d+)([dhms])", t))
    return gramos, metros, minutos


def hm(minutos):
    return f"{int(minutos // 60)} h {int(round(minutos % 60)):02d} min"


def main():
    stl_dir = BASE / "STL"
    piezas = []
    for nombre, _, _ in g.PIEZAS:
        malla = trimesh.load(stl_dir / f"{nombre}.stl")
        x0, y0, z0 = malla.bounds[0]
        x1, y1, z1 = malla.bounds[1]
        piezas.append({"nombre": nombre, "malla": malla, "w": x1 - x0, "h": y1 - y0, "alto": z1 - z0,
                       "mat": material(nombre), "contorno": contorno_2d(malla) - [x0, y0]})
    # placas: por material; se prueban varios órdenes y se queda el que usa menos placas
    placas = []
    for mat in ("PLA", "PETG"):
        propias = [p for p in piezas if p["mat"] == mat]
        mejor = None
        for clave in (lambda p: -p["w"] * p["h"], lambda p: -max(p["w"], p["h"]),
                      lambda p: -p["h"], lambda p: -p["w"], lambda p: -p["alto"]):
            intento = []
            for p in sorted(propias, key=clave):
                if not any(pl.colocar(p["nombre"], p["w"], p["h"]) for pl in intento):
                    pl = Placa(mat)
                    if not pl.colocar(p["nombre"], p["w"], p["h"]):
                        raise SystemExit(f"{p['nombre']} no cabe en la cama de {CAMA} mm")
                    intento.append(pl)
            if mejor is None or len(intento) < len(mejor):
                mejor = intento
        placas += mejor
    # laminado
    datos = {}
    print(f"Laminando {len(piezas)} piezas con el perfil Neptune 4 Plus (puede tardar unos minutos)...")
    for p in piezas:
        relleno = "40%" if codigo(p["nombre"]) in RELLENO_40 else "20%"
        datos[p["nombre"]] = (relleno, laminar(stl_dir / f"{p['nombre']}.stl", p["mat"], relleno))
        r = datos[p["nombre"]][1]
        print(f"  {p['nombre']:40s} {p['mat']:4s} {relleno:>4s} " +
              (f"{r[0]:7.1f} g {hm(r[2]):>12s}" if r else "(sin PrusaSlicer)"))
    dibujar(placas, piezas)
    escribir_md(placas, piezas, datos)
    return 0


def dibujar(placas, piezas):
    por_nombre = {p["nombre"]: p for p in piezas}
    n = len(placas)
    cols = 3
    filas = math.ceil(n / cols)
    fig, ejes = plt.subplots(filas, cols, figsize=(5.2 * cols, 5.4 * filas))
    ejes = np.atleast_1d(ejes).ravel()
    for i, (ax, pl) in enumerate(zip(ejes, placas)):
        ax.add_patch(plt.Rectangle((-5, -5), 320, 320, fill=True, fc="#f4f4f4", ec="#333", lw=1.5))
        ax.add_patch(plt.Rectangle((0, 0), CAMA, CAMA, fill=False, ec="#999", lw=0.8, ls="--"))
        color = "#e8a33d" if pl.mat == "PETG" else "#5b8fe8"
        for nombre, x, y, w, h, giro in pl.piezas:
            c = por_nombre[nombre]["contorno"]
            if giro:
                c = np.column_stack([c[:, 1], por_nombre[nombre]["w"] - c[:, 0]])
            ax.add_patch(plt.Polygon(c + [x, y], closed=True, fc=color, ec="#222", alpha=0.85))
            ax.text(x + w / 2, y + h / 2, codigo(nombre), ha="center", va="center", fontsize=11, weight="bold")
        alto = max(por_nombre[nm]["alto"] for nm, *_ in pl.piezas)
        ax.set_title(f"Placa {i + 1} · {pl.mat} · altura máx. {alto:.0f} mm", fontsize=11)
        ax.set_xlim(-10, 325)
        ax.set_ylim(-10, 325)
        ax.set_aspect("equal")
        ax.set_xticks([0, 160, 320])
        ax.set_yticks([0, 160, 320])
    for ax in ejes[n:]:
        ax.axis("off")
    fig.suptitle(f"{g.IMPRESORA}: placas de impresión (cama 320 × 320 mm; zona usada 310 × 310)", fontsize=14)
    fig.tight_layout()
    ruta = BASE / "render" / "placas_impresion.png"
    fig.savefig(ruta, dpi=90)
    print("->", ruta.relative_to(BASE))


def escribir_md(placas, piezas, datos):
    por_nombre = {p["nombre"]: p for p in piezas}
    hay = all(r for _, r in datos.values())
    L = ["# Plan de impresión · Elegoo Neptune 4 Plus", "",
         "Generado por `plan_impresion.py` (no editar a mano). Volumen de la impresora: 320 × 320 × 385 mm; "
         "todas las piezas se verificaron con un margen de 5 mm por lado (`generar_stl.py`).", "",
         "![Placas](render/placas_impresion.png)", "",
         "Importe en el laminador (Elegoo Cura u OrcaSlicer con el perfil «Elegoo Neptune 4 Plus») los STL de cada "
         "placa **sin rotarlos** (ya vienen orientados) y use *Organizar*. Si prefiere menos riesgo, imprima las "
         "piezas altas (02, 07) solas: un fallo no arruina las demás.", ""]
    tot_g = {"PLA": 0.0, "PETG": 0.0}
    tot_t = 0.0
    for i, pl in enumerate(placas, 1):
        g_placa = sum(datos[n][1][0] for n, *_ in pl.piezas) if hay else 0
        t_placa = sum(datos[n][1][2] for n, *_ in pl.piezas) if hay else 0
        L += [f"## Placa {i} · {pl.mat}" + (f" · ≈{g_placa:.0f} g · ≈{hm(t_placa)}" if hay else ""), "",
              "| Pieza | Huella × altura (mm) | Relleno | Filamento | Tiempo (orientativo) |", "|---|---|---|---|---|"]
        for nombre, *_ in pl.piezas:
            p = por_nombre[nombre]
            relleno, r = datos[nombre]
            L.append(f"| {nombre} | {p['w']:.0f} × {p['h']:.0f} × {p['alto']:.0f} | {relleno} | "
                     + (f"{r[0]:.0f} g ({r[1]:.1f} m) | {hm(r[2])} |".replace(".", ",") if r else "— | — |"))
            if r:
                tot_g[pl.mat] += r[0]
                tot_t += r[2]
        L.append("")
    if hay:
        L += ["## Totales", "", "| Material | Filamento | Bobinas de 1 kg |", "|---|---|---|"]
        for m, v in tot_g.items():
            L.append(f"| {m} | ≈{v:.0f} g | {math.ceil(v * 1.15 / 1000)} (con 15 % de reserva para pruebas y fallos) |")
        L += ["", f"Tiempo total orientativo: **≈{hm(tot_t)}** de impresión (suma de las piezas).", ""]
    L += ["## Perfil usado para estimar (equivalente a la Neptune 4 Plus)", "",
          "| Ajuste | PLA | PETG |", "|---|---|---|",
          f"| Boquilla / capa / primera capa | 0,4 / 0,2 / 0,2 mm | 0,4 / 0,2 / 0,2 mm |",
          f"| Temperatura boquilla / cama | {FILAMENTO['PLA']['temperature']} / {FILAMENTO['PLA']['bed_temperature']} °C | "
          f"{FILAMENTO['PETG']['temperature']} / {FILAMENTO['PETG']['bed_temperature']} °C |",
          "| Perímetros / capas sup. / inf. | 3 / 5 / 4 | 3 / 5 / 4 |",
          "| Relleno | giroide 20 % (40 % en 06, 08b, 12a, 12b, 16) | ídem |",
          f"| Flujo volumétrico máx. | {FILAMENTO['PLA']['filament_max_volumetric_speed']} mm³/s | "
          f"{FILAMENTO['PETG']['filament_max_volumetric_speed']} mm³/s |",
          "| Velocidades (perímetro ext. / int. / relleno) | 80 / 120 / 200 mm/s | ídem (las limita el flujo) |",
          "| Soportes | **ninguno** (diseño sin voladizos > 45°) | ídem |",
          "| Adherencia | falda; borde (brim) de 5 mm solo en 02 y 07 si la cama no agarra bien | ídem; en PETG use "
          "pegamento en barra o la cara texturizada de la placa PEI |", "",
          "Los tiempos los calcula PrusaSlicer con estas velocidades; su laminador puede dar otros valores. Los gramos "
          "dependen poco del laminador.", ""]
    (BASE / "plan_impresion.md").write_text("\n".join(L), encoding="utf-8")
    print("-> plan_impresion.md")


if __name__ == "__main__":
    sys.exit(main())
