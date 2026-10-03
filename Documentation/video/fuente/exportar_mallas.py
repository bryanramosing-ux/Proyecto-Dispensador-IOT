"""
Exporta las piezas EN SU POSICIÓN DE ENSAMBLAJE (no orientadas para imprimir) para las
animaciones 3D del video.

    python exportar_mallas.py [carpeta_salida]      # por defecto: ./web/mallas
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Mechanical"))
import generar_stl as g  # noqa: E402

SALIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "web" / "mallas"


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    piezas = g.construir()
    for nombre, m in piezas.items():
        if nombre in ("12a_Estacion_Solar_Base", "12b_Estacion_Solar_Bandeja", "15_Separadores"):
            continue
        g.a_trimesh(m).export(SALIDA / f"{nombre}.stl")
    g.a_trimesh(g.envolvente_mg995()).export(SALIDA / "MG995.stl")
    # estación solar: base, y bandeja + panel a 0° (la animación los gira sobre el eje del pivote)
    g.a_trimesh(g.p12a_estacion_base()).export(SALIDA / "E_12a.stl")
    g.a_trimesh(g.p12b_estacion_bandeja(0)).export(SALIDA / "E_12b0.stl")
    panel = g.caja(-g.PANEL_W / 2, g.PANEL_W / 2, -g.PANEL_H / 2, g.PANEL_H / 2,
                   g.E_BANDEJA - g.PANEL_E + 0.5, g.E_BANDEJA + 0.5)
    g.a_trimesh(panel.translate([0, 0, g.Z_PIVOTE - g.NUDILLO_R])).export(SALIDA / "E_panel0.stl")
    # HC-SR04 simulado dentro de su cápsula (placa + transductores)
    cx, cy = g.CAP_C
    z = g.Z_SENSOR + g.CAP_PARED + g.HC_SOBRE_PISO
    hc = g.caja(cx - g.HC_A / 2, cx + g.HC_A / 2, cy - g.HC_L / 2, cy + g.HC_L / 2, z, z + 1.6)
    for s in (-1, 1):
        hc += g.cil(cx, cy + s * g.HC_TRANSD_SEP / 2, z - 12, z, 8)
    g.a_trimesh(hc).export(SALIDA / "HC_nivel.stl")
    print("Mallas en", SALIDA, "· pivote de la estación z =", g.Z_PIVOTE)


if __name__ == "__main__":
    main()
