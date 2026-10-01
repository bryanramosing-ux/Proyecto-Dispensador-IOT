"""
Genera los planos 2D de referencia (requiere matplotlib):
    python render.py
Crea render/corte_recorrido_alimento.png y render/planta_dosificador.png.
(Las vistas 3D render/vista_*.png se generaron con three.js a partir de los mismos STL.)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

import generar_stl as g  # noqa: E402

DIR = Path(__file__).resolve().parent / "render"

ALIMENTO = "#e8a33d"
ELECTRONICA = "#3d7fe8"
ESTRUCTURA = "#b8bec6"
ENERGIA = "#57b36a"
COLORES = {
    "01": ENERGIA, "16": ENERGIA, "02": ESTRUCTURA, "14": ESTRUCTURA, "13": ESTRUCTURA,
    "15": ESTRUCTURA, "03": ELECTRONICA, "04": ELECTRONICA, "05": ELECTRONICA,
    "06": "#7b5cd6", "07": ALIMENTO, "08": ALIMENTO, "09": ALIMENTO, "10": ALIMENTO,
    "11": "#d9534f", "12": "#2c3e50",
}


def parche(poligonos, transf, **kw):
    """Une todos los contornos en un solo trazado para que los agujeros se vean vacíos."""
    verts, codes = [], []
    for poly in poligonos:
        p = transf(np.asarray(poly))
        verts += list(p) + [p[0]]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(p) - 1) + [MPath.CLOSEPOLY]
    return PathPatch(MPath(verts, codes), **kw)


def corte_x0(piezas, ruta, x=0.0):
    fig, ax = plt.subplots(figsize=(8, 12), dpi=120)
    extra = {"MG995 (envolvente)": g.envolvente_mg995()}
    todos = dict(piezas, **extra)
    for nombre, m in todos.items():
        k = nombre[:2]
        sec = m.translate([-x, 0, 0]).rotate([0, -90, 0]).slice(0.0)
        color = "#444444" if nombre.startswith("MG995") else COLORES.get(k, ESTRUCTURA)
        polys = sec.to_polygons()
        if polys:
            ax.add_patch(parche(polys, lambda p: np.c_[p[:, 1], -p[:, 0]], facecolor=color,
                                edgecolor="black", linewidth=0.3, alpha=0.95))
    # recorrido del alimento (flechas)
    ix, iy = g.polar(g.C_DISCO, g.R_BOLSILLO, g.ANG_ENTRADA)
    camino = [(0, 430), (iy, g.Z_PLACA_SUP + 6), (g.CANAL_Y, g.Z_DISCO + 2), (g.CANAL_Y, 175),
              (-g.R_INT, g.Z_SALIDA_PARED), (-g.W / 2 - g.LARGO_PICO, g.Z_SALIDA_PARED - g.LARGO_PICO),
              (g.BOWL_C[1] + 30, 15)]
    cy, cz = zip(*camino)
    ax.plot(cy, cz, "--", color="#c0392b", linewidth=2)
    for (y0, z0), (y1, z1) in zip(camino[:-1], camino[1:]):
        ax.annotate("", xy=(y1, z1), xytext=(y0, z0),
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=2))
    notas = [((-10, 450), "07 Tolva"), ((10, 318), f"entrada en X = +{ix:.0f} mm\n(fuera de este corte)"),
             ((-10, 300), "08 Disco dosificador (MG995)"),
             ((-95, 230), "09 Conducto\n(tubo cerrado)"), ((-205, 120), "10 Salida"),
             ((-240, 55), "11 Comedero"), ((15, 160), "Bahía electrónica\n(seca, tras el tabique)"),
             ((15, 25), "01 Base: energía")]
    for (yy, zz), txt in notas:
        ax.text(yy, zz, txt, fontsize=9)
    ax.set_xlim(-260, 180)
    ax.set_ylim(-10, 560)
    ax.set_aspect("equal")
    ax.set_xlabel("Y [mm]  (frente <-   -> atrás)")
    ax.set_ylabel("Z [mm]")
    ax.set_title(f"Corte por X = {x:.0f} mm: recorrido del alimento (flechas)")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def planta_dosificador(piezas, ruta):
    fig, ax = plt.subplots(figsize=(7, 7), dpi=120)
    z = g.Z_DISCO + g.E_DISCO / 2
    for nombre in ("08a_Carcasa_Dosificador", "08b_Disco_Dosificador"):
        polys = piezas[nombre].slice(z).to_polygons()
        ax.add_patch(parche(polys, lambda p: p, facecolor=COLORES["08"] if nombre[:3] == "08b" else ESTRUCTURA,
                            edgecolor="black", linewidth=0.4))
    for ang, txt, col in ((g.ANG_ENTRADA, "ENTRADA (tolva)", "#27ae60"),
                          (g.ANG_CERRADO, "CERRADO (reposo)", "#7f8c8d"),
                          (g.ANG_SALIDA, "SALIDA (conducto)", "#c0392b")):
        x, y = g.polar(g.C_DISCO, g.R_BOLSILLO, ang)
        r = (g.D_ENTRADA if "ENTRADA" in txt else g.D_SALIDA if "SALIDA" in txt else g.D_BOLSILLO) / 2
        ax.add_patch(plt.Circle((x, y), r, fill=False, ls="--", color=col, lw=2))
        ax.text(x + 4, y + r + 3, txt, color=col, fontsize=9, ha="center")
    ax.set_xlim(-80, 80)
    ax.set_ylim(-80, 80)
    ax.set_aspect("equal")
    ax.set_title("Dosificador visto desde arriba (corte a media altura del disco)\n"
                 "Bolsillo dibujado en posición CERRADO; entrada y salida separadas 100°")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def main():
    DIR.mkdir(exist_ok=True)
    piezas = g.construir()
    corte_x0(piezas, DIR / "corte_recorrido_alimento.png")
    planta_dosificador(piezas, DIR / "planta_dosificador.png")
    print("Imagenes en", DIR)


if __name__ == "__main__":
    main()
