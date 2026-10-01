"""
Generador paramétrico de la torre del dispensador (todas las piezas STL).

    pip install numpy trimesh manifold3d
    python generar_stl.py            # genera STL/ y ejecuta las verificaciones

Unidades: mm.  Ejes del ensamblaje: X = derecha, Y = atrás (+) / frente (-),
Z = arriba.  El frente de la torre (comedero, cámara, sensor) mira hacia -Y.

Reglas de diseño para impresión FDM aplicadas en TODAS las piezas:
  * ningún voladizo de más de 45° ni puente largo (los tetones llevan cartela a 45°);
  * cada pieza tiene una cara plana de apoyo en la orientación de impresión indicada;
  * las placas grandes (piso, placa base del dosificador) se imprimen planas como
    piezas independientes en lugar de quedar "colgadas" dentro de un módulo.

IMPORTANTE: las cotas de componentes comprados (MG995, HC-SR04, ESP32-CAM,
placa perforada, panel) son las NOMINALES/HABITUALES y están reunidas en la
sección "COMPONENTES". Mida sus unidades con calibre y ajuste antes de
imprimir: hay clones con cotas distintas.
"""
import math
import re
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType

SALIDA = Path(__file__).resolve().parent / "STL"
SEG = 96

# =============================================================================
# PARÁMETROS GENERALES
# =============================================================================
W, CH = 150.0, 20.0          # torre: cuadrado 150 mm con chaflanes de 20 mm (octógono)
T = 3.0                      # espesor de pared
CLR = 0.3                    # holgura de encaje entre módulos
LIP_H, LIP_T = 6.0, 2.0      # labio de encaje (macho) en la parte superior de cada módulo
PLINTO, PLINTO_CH, PLINTO_H = 190.0, 30.0, 12.0

# Alturas de la pila (z de la junta inferior de cada módulo)
Z_BASE, Z_CUERPO, Z_DOSIF, Z_TOLVA = 0.0, 45.0, 265.0, 303.0
H_TOLVA = 180.0
Z_TAPA = Z_TOLVA + H_TOLVA   # 483
E_PISO = 4.0
Z_PISO = Z_CUERPO + E_PISO   # 49: cara superior del piso del cuerpo

# =============================================================================
# COMPONENTES (cotas nominales -> VERIFICAR con calibre)
# =============================================================================
MG995_L, MG995_A, MG995_ALTO = 40.7, 19.7, 42.9   # cuerpo (hoja de datos Tower Pro)
MG995_EJE_DESDE_EXTREMO = 10.0     # VERIFICAR: distancia eje-extremo del cuerpo
MG995_AGUJEROS_DX = 49.2           # VERIFICAR: separación de agujeros de las orejas
MG995_AGUJEROS_DY = 10.0
MG995_BRIDA_A_ESTRIA = 19.0        # VERIFICAR: de la cara superior de las orejas a la punta del eje
HC_L, HC_A, HC_TRANSD_D, HC_TRANSD_SEP = 45.0, 20.0, 16.0, 26.0  # HC-SR04 (VERIFICAR separación)
CAM_L, CAM_A = 40.5, 27.0          # ESP32-CAM AI-Thinker
PERF_X, PERF_Y, PERF_E = 90.0, 70.0, 1.6   # placa perforada 90x70 mm
PANEL_W, PANEL_H, PANEL_E = 80.0, 80.0, 3.0  # MEDIR el panel real y ajustar

# =============================================================================
# DOSIFICADOR (disco volumétrico)  -- geometría verificada en verificar()
# =============================================================================
C_DISCO = (0.0, -2.0)        # eje del servo / centro del disco
R_BOLSILLO = 40.0            # radio al centro del bolsillo
D_BOLSILLO = 28.0            # diámetro del bolsillo (grano recomendado <= 14 mm)
D_ENTRADA = 28.0             # agujero de entrada (tolva -> disco)
D_SALIDA = 32.0              # agujero de salida (disco -> conducto), mayor que el bolsillo
ANG_SALIDA = -90.0           # salida hacia el frente (canal de alimento)
ANG_ENTRADA = ANG_SALIDA + 100.0   # 100° de separación entre entrada y salida
ANG_CERRADO = (ANG_SALIDA + ANG_ENTRADA) / 2   # posición de reposo (nada conectado)
E_DISCO = 14.0
R_DISCO = R_BOLSILLO + D_BOLSILLO / 2 + 4.0    # 58
R_CAMARA = R_DISCO + 1.0                        # holgura radial 1 mm
Z_PLACA_INF = Z_DOSIF + LIP_H                   # 271: placa base apoyada sobre el labio del cuerpo
E_PLACA_INF = 5.0
Z_DISCO = Z_PLACA_INF + E_PLACA_INF + 0.5       # 276.5
Z_PLACA_SUP = Z_DISCO + E_DISCO + 0.5           # 291
E_PLACA_SUP = 4.0
Z_ASIENTO = Z_PLACA_SUP + E_PLACA_SUP           # 295: asiento cónico de la placa superior

# Canal de alimento (sección interior cuadrada) y salida
CANAL_IN, CANAL_PARED = 36.0, 2.5
CANAL_Y = -42.0                  # = centro del agujero de salida
TABIQUE_Y = (-21.5, -18.5)       # tabique: frente (canal) | atrás (electrónica)
Z_SALIDA_PARED = 128.0           # eje del canal inclinado al cruzar la pared frontal
LARGO_PICO = 40.0                # proyección horizontal del pico fuera de la torre

# Pods frontales, por encima de la brida del pico. Sus cables entran a la torre
# por agujeros situados FUERA del ancho del canal (|x| > 20,5 mm).
HC_X, HC_Z = -29.0, 204.0          # HC-SR04 a la izquierda
CAM_X, CAM_Z0, CAM_Z1 = 31.0, 197.0, 257.0   # ESP32-CAM a la derecha

# Comedero
BOWL_C = (0.0, -160.0)
BOWL_R, BOWL_H = 62.0, 40.0


# =============================================================================
# UTILIDADES
# =============================================================================
def caja(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cil(cx, cy, z0, z1, r, r2=None, seg=SEG):
    return Manifold.cylinder(z1 - z0, r, r if r2 is None else r2, seg).translate([cx, cy, z0])


def cil_eje(p, eje, largo, r, seg=48):
    """Cilindro centrado en p, orientado según 'x', 'y' o 'z'."""
    c = Manifold.cylinder(largo, r, r, seg, True)
    if eje == "x":
        c = c.rotate([0, 90, 0])
    elif eje == "y":
        c = c.rotate([90, 0, 0])
    return c.translate(list(p))


def octogono(w, ch):
    h = w / 2
    pts = [(h - ch, -h), (h, -h + ch), (h, h - ch), (h - ch, h),
           (-h + ch, h), (-h, h - ch), (-h, -h + ch), (-h + ch, -h)]
    return CrossSection([pts])


def contorno(inset=0.0):
    cs = octogono(W, CH)
    return cs if inset == 0 else cs.offset(-inset, JoinType.Miter)


def prisma(cs, z0, z1):
    return cs.extrude(z1 - z0).translate([0, 0, z0])


def union(*piezas):
    piezas = [p for p in piezas if p is not None]
    return Manifold.batch_boolean(piezas, OpType.Add)


def polar(c, r, ang):
    return (c[0] + r * math.cos(math.radians(ang)), c[1] + r * math.sin(math.radians(ang)))


def teton(x0, x1, y0, y1, z0, z1, pared):
    """Bloque pegado a una pared con cartela a 45° por debajo (imprimible sin soportes).
    pared: '+x', '-x', '+y' o '-y' = lado del bloque que toca la pared."""
    prof = (x1 - x0) if pared[1] == "x" else (y1 - y0)
    if pared == "+x":
        losa = caja(x1 - 0.01, x1, y0, y1, z0 - prof, z1)
    elif pared == "-x":
        losa = caja(x0, x0 + 0.01, y0, y1, z0 - prof, z1)
    elif pared == "+y":
        losa = caja(x0, x1, y1 - 0.01, y1, z0 - prof, z1)
    else:
        losa = caja(x0, x1, y0, y0 + 0.01, z0 - prof, z1)
    return Manifold.batch_hull([caja(x0, x1, y0, y1, z0, z1), losa])


R_INT = W / 2 - T                       # 72: semiancho interior
PUNTOS_JUNTA = [(-1, 0), (1, 0), (0, 1)]  # mitad de pared izquierda, derecha y trasera


def carcasa(z0, z1):
    return prisma(contorno(), z0, z1) - prisma(contorno(T), z0 - 1, z1 + 1)


def labio(z_sup):
    """Labio macho en la parte superior del módulo inferior + 3 tetones para M3.
    Por debajo lleva una rampa a 45° (escalones de 0,3 mm) para no quedar en voladizo."""
    anillo = contorno(T + CLR) - contorno(T + CLR + LIP_T)
    piezas = [prisma(anillo, z_sup, z_sup + LIP_H)]
    ancho = CLR + LIP_T + 0.1
    n = 10
    for k in range(1, n + 1):
        d = ancho * k / n
        z0 = z_sup - ancho + (k - 1) * ancho / n
        piezas.append(prisma(contorno(T - 0.05) - contorno(T - 0.05 + d), z0, z_sup + 0.01))
    r_lab = W / 2 - T - CLR - LIP_T
    agujeros = []
    for sx, sy in PUNTOS_JUNTA:
        if sx:
            x0, x1 = sorted([sx * (r_lab - 6), sx * (W / 2 - T)])
            piezas.append(teton(x0, x1, -5, 5, z_sup, z_sup + LIP_H, "+x" if sx > 0 else "-x"))
            agujeros.append(cil_eje((sx * (W / 2 - 6), 0, z_sup + LIP_H / 2), "x", 14, 1.25))
        else:
            y0, y1 = sorted([sy * (r_lab - 6), sy * (W / 2 - T)])
            piezas.append(teton(-5, 5, y0, y1, z_sup, z_sup + LIP_H, "+y" if sy > 0 else "-y"))
            agujeros.append(cil_eje((0, sy * (W / 2 - 6), z_sup + LIP_H / 2), "y", 14, 1.25))
    lab = union(*piezas) - union(*agujeros)
    # el labio no debe invadir el espacio exterior de la pared
    return lab - (prisma(contorno(), z_sup - 10, z_sup + LIP_H + 1) - prisma(contorno(T - 0.05), z_sup - 11, z_sup + LIP_H + 2))


def agujeros_junta(z_junta):
    """Pasantes Ø3,4 en el módulo superior, alineados con los tetones del labio."""
    out = []
    for sx, sy in PUNTOS_JUNTA:
        p = (sx * (W / 2 - 1), sy * (W / 2 - 1), z_junta + LIP_H / 2)
        out.append(cil_eje(p, "x" if sx else "y", 8, 1.7))
    return union(*out)


def ranuras(eje_pared, coord_pared, centros, z0, z1, ancho=3.0):
    """Ranuras de ventilación verticales en una pared ('x' = pared lateral)."""
    out = []
    for c in centros:
        if eje_pared == "x":
            out.append(caja(coord_pared - 5, coord_pared + 5, c - ancho / 2, c + ancho / 2, z0, z1))
        else:
            out.append(caja(c - ancho / 2, c + ancho / 2, coord_pared - 5, coord_pared + 5, z0, z1))
    return union(*out)


# =============================================================================
# 01 BASE (módulo de energía, plinto ancho para estabilidad)
# =============================================================================
CAJON_X = 45.0      # semiancho del cajón de energía
Z_CAJON = 13.0      # el cajón apoya a 13 mm: su tapa queda por encima del plinto trasero
PILARES = [(sx * 56.0, sy * 60.0) for sx in (-1, 1) for sy in (-1, 1)]  # unión base-cuerpo (M3 vertical)
LENGUETAS_X = (30.0, 50.0)   # lengüetas del comedero bajo el plinto (|x|)


def p01_base():
    plinto = prisma(octogono(PLINTO, PLINTO_CH), 0, PLINTO_H)
    cuerpo = prisma(contorno(), 0, Z_CUERPO)
    hueco = prisma(contorno(T), 3, Z_CUERPO + 1)
    b = union(plinto, cuerpo) - hueco
    # pilares de unión con el cuerpo (tornillo M3 desde arriba, a través del piso)
    for x, y in PILARES:
        b += cil(x, y, 2.9, Z_CUERPO, 5, seg=32) - cil(x, y, Z_CUERPO - 12, Z_CUERPO + 1, 1.25, seg=24)
    # abertura trasera para el cajón (escotadura abierta arriba: el piso del cuerpo la cierra)
    b -= caja(-CAJON_X - 1, CAJON_X + 1, R_INT - 1, W / 2 + 1, Z_CAJON, Z_CUERPO + 1)
    # repisas de apoyo y guías laterales del cajón
    for s in (-1, 1):
        x0, x1 = sorted([s * (CAJON_X - 4), s * (CAJON_X + 4)])
        b += caja(x0, x1, -50, R_INT, 3, Z_CAJON)
        x0, x1 = sorted([s * (CAJON_X + 0.5), s * (CAJON_X + 4)])
        b += caja(x0, x1, -50, R_INT, Z_CAJON - 0.01, Z_CAJON + 4)
    # tetones (con cartela) para los tornillos de la tapa del cajón
    for s in (-1, 1):
        x0, x1 = sorted([s * 46.5, s * 54.5])
        b += teton(x0, x1, R_INT - 8, R_INT + 0.5, 18, 26, "+y") - cil_eje((s * 50.5, R_INT - 2, 22), "y", 14, 1.25)
    # ventilación lateral (convertidores DC-DC)
    for s in (-1, 1):
        b -= ranuras("x", s * (W / 2 - 1.5), np.arange(5, 60, 8), 16, 38)
    # alojamientos de las lengüetas del comedero (al ras del suelo: imprimible)
    for s in (-1, 1):
        x0, x1 = sorted([s * (LENGUETAS_X[0] - 0.4), s * (LENGUETAS_X[1] + 0.4)])
        b -= caja(x0, x1, -PLINTO / 2 - 1, -PLINTO / 2 + 15.5, -1, 4.4)
    return b


# =============================================================================
# 02 CUERPO PRINCIPAL (canal de alimento + bahía electrónica + frente de sensores)
# =============================================================================
TAPA_SERV = (-52.0, 52.0, 75.0, 245.0)   # abertura trasera (x0, x1, z0, z1); techo en punta a 45°
TAPA_AG = [(sx * 40.0, z) for sx in (-1, 1) for z in (71.0, 249.0)]  # tornillos de la tapa
BANDEJA_AG = [(sx * 30.0, y) for sx in (-1, 1) for y in (2.0, 56.0)]  # (x, y) pernos de la bandeja ESP32
CABLE_PISO = (-60.0, 20.0)         # paso de cables cuerpo -> base
X_MENSULA = 60.0                   # ménsulas que sostienen la viga del servo


def ag_pico():
    """(x, z) de los 4 tornillos de la brida del pico de salida."""
    return [(sx * 26, z) for sx in (-1, 1) for z in (Z_SALIDA_PARED - 22, Z_SALIDA_PARED + 28)]


def ag_pod_hc():
    return [(HC_X - 21, HC_Z - 24), (HC_X + 21, HC_Z - 24)]


def ag_pod_cam():
    return [(CAM_X - 16, CAM_Z0 + 5), (CAM_X + 16, CAM_Z0 + 5)]


CABLE_HC = (HC_X - 11, HC_Z - 18)
CABLE_CAM = (CAM_X + 9, CAM_Z0 + 12)


def abertura_servicio(y0, y1, holgura=0.0):
    """Abertura trasera: rectángulo con techo en punta a 45° (sin puente al imprimir)."""
    x0, x1, z0, z1 = TAPA_SERV
    x0, x1, z0 = x0 + holgura, x1 - holgura, z0 + holgura
    zr = z1 - (x1 - x0) / 2
    cs = CrossSection([[(x0, z0), (x1, z0), (x1, zr), ((x0 + x1) / 2, z1 - holgura), (x0, zr)]])
    return cs.extrude(y1 - y0).rotate([90, 0, 0]).translate([0, y1, 0])


def p02_cuerpo():
    z0, z1 = Z_CUERPO, Z_DOSIF
    c = carcasa(z0, z1)
    piso = prisma(contorno(T - 0.01), z0, Z_PISO)
    tabique = caja(-R_INT, R_INT, TABIQUE_Y[0], TABIQUE_Y[1], Z_PISO - 0.01, z1 + 3)
    tet = []
    for x, zz in TAPA_AG:
        tet.append(teton(x - 4, x + 4, R_INT - 7, R_INT + 0.5, zz - 4, zz + 4, "+y"))
    for x, z in ag_pico():
        tet.append(teton(x - 4, x + 4, -R_INT - 0.5, -R_INT + 6, z - 4, z + 4, "-y"))
    zt = z_soporte() - 5 - 0.1          # apoyo de la viga del servo
    for s in (-1, 1):
        x0, x1 = sorted([s * X_MENSULA, s * (R_INT + 0.5)])
        m = teton(x0, x1, -17.5, 17.5, zt - 6, zt, "+x" if s > 0 else "-x")
        tet.append(m - cil(s * 66, 0, zt - 12, zt + 1, 1.25, seg=24))
    c = union(c, piso, tabique, *tet)

    # piso: unión con la base, paso de cables y pernos de la bandeja
    for x, y in PILARES:
        c -= cil(x, y, z0 - 1, Z_PISO + 1, 1.7, seg=24)
    c -= cil(*CABLE_PISO, z0 - 1, Z_PISO + 1, 8)
    for x, y in BANDEJA_AG:
        c -= cil(x, y, z0 - 1, Z_PISO + 1, 1.7, seg=24)
    # tabique: pasos de cables de los pods (a ambos lados, lejos del canal)
    c -= cil_eje((-58, sum(TABIQUE_Y) / 2, 190), "y", 10, 6)
    c -= cil_eje((58, sum(TABIQUE_Y) / 2, 210), "y", 10, 6)
    # frente: abertura del pico (canal inclinado 45°)
    c -= caja(-21, 21, -W / 2 - 1, -R_INT + 1, Z_SALIDA_PARED - 33, Z_SALIDA_PARED + 31)
    for x, z in ag_pico():
        c -= cil_eje((x, -R_INT + 2, z), "y", 12, 1.25)
    # frente: agujeros de pods (cable + tornillos M3 con tuerca por dentro)
    for x, z in (CABLE_HC, CABLE_CAM):
        c -= cil_eje((x, -R_INT - 1.5, z), "y", 8, 5)
    for x, z in ag_pod_hc() + ag_pod_cam():
        c -= cil_eje((x, -R_INT - 1.5, z), "y", 8, 1.7)
    # atrás: abertura de servicio de la bahía electrónica
    c -= abertura_servicio(R_INT - 1, W / 2 + 1)
    for x, zz in TAPA_AG:
        c -= cil_eje((x, R_INT - 2, zz), "y", 14, 1.25)
    # ventilación de la bahía electrónica (solo zona trasera, lejos del alimento)
    for s in (-1, 1):
        c -= ranuras("x", s * (W / 2 - 1.5), np.arange(26, 66, 8), 200, 240)
    c -= ranuras("x", W / 2 - 1.5, np.arange(8, 66, 8), 90, 180)
    return c + labio(z1)


# =============================================================================
# 09 CONDUCTO DE ALIMENTO (tubo cerrado: vertical + codo a 45° hacia el frente)
# =============================================================================
def tramo_canal(medio, z_ini):
    """Sólido del canal (exterior si medio=semiancho exterior, interior si no)."""
    d = np.array([0.0, -1.0, -1.0]) / math.sqrt(2)          # dirección del tramo inclinado
    dz = (-R_INT + 0.5) - CANAL_Y                            # avance en Y hasta la pared (-29.5)
    p1 = np.array([0.0, CANAL_Y, Z_SALIDA_PARED - dz])       # codo (z = 157.5)
    vert = caja(-medio, medio, CANAL_Y - medio, CANAL_Y + medio, p1[2] - 60, z_ini)
    largo = 200.0
    incl = Manifold.cube([2 * medio, 2 * medio, largo]).translate([-medio, -medio, -largo / 2])
    incl = incl.rotate([-45, 0, 0]).translate(list(p1))
    n = np.array([0.0, 0.0, 1.0]) - d                       # plano bisector del inglete
    n = n / np.linalg.norm(n)
    off = float(n @ p1)
    return union(vert.trim_by_plane(list(n), off), incl.trim_by_plane(list(-n), -off)), p1


def p09_conducto():
    z_top = Z_PLACA_INF - 1.0          # 1 mm bajo la placa base: la salida Ø32 cae dentro (36x36)
    ext, p1 = tramo_canal(CANAL_IN / 2 + CANAL_PARED, z_top)
    inn, _ = tramo_canal(CANAL_IN / 2, z_top + 5)
    tubo = ext - inn
    patas = union(caja(-20.5, -17.5, CANAL_Y - 20.5, CANAL_Y + 20.5, Z_PISO + 0.1, p1[2]),
                  caja(17.5, 20.5, CANAL_Y - 20.5, CANAL_Y + 20.5, Z_PISO + 0.1, p1[2]))
    patas -= inn
    w_abajo = np.array([0.0, 1.0, -1.0]) / math.sqrt(2)     # cara inferior del tramo inclinado
    patas = patas.trim_by_plane(list(w_abajo), float(w_abajo @ p1) + CANAL_IN / 2 + 0.5)
    return union(tubo, patas).trim_by_plane([0, 1, 0], -R_INT + 0.5)


# =============================================================================
# 10 SALIDA (pico a 45° atornillado al frente)
# =============================================================================
def p10_salida():
    d = np.array([0.0, -1.0, -1.0]) / math.sqrt(2)
    p2 = np.array([0.0, -R_INT + 0.5, Z_SALIDA_PARED])
    medio_e, medio_i = (CANAL_IN + 1) / 2 + 2.0, (CANAL_IN + 1) / 2
    largo = (LARGO_PICO + 3.5) * math.sqrt(2) + 2 * medio_e

    def tubo_incl(medio):
        t = Manifold.cube([2 * medio, 2 * medio, largo]).translate([-medio, -medio, 0])
        return t.rotate([135, 0, 0]).translate(list(p2 - d * medio_e))  # +Z -> d

    hueco = tubo_incl(medio_i).translate(list(-d * 5))
    t = tubo_incl(medio_e) - hueco
    t = t.trim_by_plane([0, -1, 0], R_INT - 0.5)                  # empieza a ras de la cara interior
    t = t.trim_by_plane([0, 1, 0], -(W / 2 + LARGO_PICO))         # punta
    brida = caja(-32, 32, -W / 2 - 3.1, -W / 2 - 0.1, Z_SALIDA_PARED - 38, Z_SALIDA_PARED + 38) - hueco
    for x, z in ag_pico():
        brida -= cil_eje((x, -W / 2 - 1.5, z), "y", 8, 1.7)
    # la cara exterior inferior del tubo es la cara de apoyo para imprimir: se recorta
    # la brida por ese plano para que la pieza quede plana sobre la cama
    n = np.array([0.0, -1.0, 1.0]) / math.sqrt(2)
    return union(t, brida).trim_by_plane(list(n), float(n @ p2) - medio_e)


# =============================================================================
# Pods frontales: caja abierta por detrás. La placa se coloca desde atrás antes
# de montar; dos orejetas internas se atornillan a la pared con M3 + tuerca
# (agujeros de acceso para el destornillador en la cara frontal).
# =============================================================================
def caja_pod(xc, z0, z1, ancho, fondo, orejetas):
    y_f = -W / 2 - fondo
    pod = caja(xc - ancho / 2, xc + ancho / 2, y_f, -W / 2 - 0.1, z0, z1)
    pod -= caja(xc - ancho / 2 + 2, xc + ancho / 2 - 2, y_f + 2, -W / 2 + 1, z0 + 2, z1 - 2)
    for x, z in orejetas:
        o = caja(x - 5, x + 5, -W / 2 - 4, -W / 2 - 0.1, z - 5, z + 5)
        pod += o - cil_eje((x, -W / 2 - 2, z), "y", 6, 1.7)
        pod -= cil_eje((x, y_f + 1, z), "y", 4, 3.2)      # acceso al tornillo
    return pod, y_f


def p03_pod_hc():
    """HC-SR04 horizontal; pines y conector hacia abajo."""
    z0, z1 = HC_Z - 29, HC_Z + 29
    pod, y_f = caja_pod(HC_X, z0, z1, 50, 28, ag_pod_hc())
    z_c = HC_Z + 9              # centro de los transductores
    for s in (-1, 1):
        pod -= cil_eje((HC_X + s * HC_TRANSD_SEP / 2, y_f + 1, z_c), "y", 6, HC_TRANSD_D / 2 + 0.4)
    y_pcb = y_f + 2 + 10.0      # guías con ranura de 1,8 mm para los extremos de la placa
    for s in (-1, 1):
        xg0, xg1 = sorted([HC_X + s * 23, HC_X + s * (HC_L / 2 - 2)])
        g = caja(xg0, xg1, y_f + 2, -W / 2 - 4, z_c - 11, z_c + 11)
        xr0, xr1 = sorted([HC_X + s * (HC_L / 2 - 2.5), HC_X + s * (HC_L / 2 + 0.4)])
        pod += g - caja(xr0, xr1, y_pcb, y_pcb + PERF_E + 0.3, z_c - 12, z_c + 12)
    return pod


def p04_pod_cam():
    """ESP32-CAM vertical, inclinada 12° hacia abajo."""
    ancho = 40.0
    pod, y_f = caja_pod(CAM_X, CAM_Z0, CAM_Z1, ancho, 34, ag_pod_cam())
    zc = (CAM_Z0 + CAM_Z1) / 2 + 4
    pod -= caja(CAM_X - 9, CAM_X + 9, y_f - 1, y_f + 3, zc - 6, zc + 20)   # ventana de la lente
    for s in (-1, 1):
        for k in range(4):
            z = CAM_Z0 + 16 + k * 9
            pod -= caja(CAM_X + s * ancho / 2 - 3, CAM_X + s * ancho / 2 + 3, y_f + 8, y_f + 26, z, z + 3)
    cuna = []
    for s in (-1, 1):
        g = caja(-2.5, 2.5, -4, 4, -CAM_L / 2 - 3, CAM_L / 2 + 3)
        g -= caja(-2.6 if s > 0 else -0.5, 0.5 if s > 0 else 2.6, -1.0, 1.0, -CAM_L / 2 - 4, CAM_L / 2 + 4)
        cuna.append(g.translate([s * (CAM_A / 2 + 0.3), 0, 0]))
    cuna = union(*cuna).rotate([-12, 0, 0]).translate([CAM_X, y_f + 14, zc])
    cuna = cuna.trim_by_plane([0, 0, 1], CAM_Z0 + 12).trim_by_plane([0, 0, -1], -(CAM_Z1 - 1))
    return union(pod, cuna)


# =============================================================================
# 05 BANDEJA ESP32 (sobre el piso de la bahía trasera). La placa perforada de
# 90x70 mm con el ESP32 entra/sale deslizando por la tapa de servicio.
# =============================================================================
Z_PCB = 74.0


def p05_bandeja_esp32():
    y0, y1 = -10.0, 64.0
    b = caja(-50, 50, y0, y1, Z_PISO + 0.1, Z_PISO + 3)
    for s in (-1, 1):
        x0, x1 = sorted([s * 41, s * 50])
        riel = caja(x0, x1, y0, y1, Z_PISO + 2.9, Z_PCB + 4)
        rx0, rx1 = sorted([s * 40, s * (PERF_X / 2 + 0.4)])
        b += riel - caja(rx0, rx1, y0 + 2, y1 + 1, Z_PCB - 0.15, Z_PCB + PERF_E + 0.25)
    b += caja(-41, 41, y0, y0 + 2, Z_PISO + 2.9, Z_PCB + 4)   # tope delantero
    b -= caja(-30, 30, y0 - 1, y0 + 3, Z_PISO + 8, Z_PCB - 3)  # paso de cables
    for x, y in BANDEJA_AG:
        b -= cil(x, y, Z_PISO - 1, Z_PISO + 4, 1.7, seg=24)
    return b


# =============================================================================
# 06 SOPORTE MG995: viga apoyada en dos ménsulas del cuerpo
# =============================================================================
def z_soporte():
    """Cara superior de la viga = apoyo de las orejas del servo."""
    return Z_PLACA_INF - MG995_BRIDA_A_ESTRIA + 5   # punta de la estría ~5 mm sobre la placa base


def p06_soporte_servo():
    zt = z_soporte()
    s = caja(-R_INT + 0.5, R_INT - 0.5, -17.5, 17.5, zt - 5, zt)
    cx0 = C_DISCO[0] - MG995_EJE_DESDE_EXTREMO
    s -= caja(cx0 - 0.4, cx0 + MG995_L + 0.4, C_DISCO[1] - MG995_A / 2 - 0.4,
              C_DISCO[1] + MG995_A / 2 + 0.4, zt - 6, zt + 1)
    xc = cx0 + MG995_L / 2
    for sx in (-1, 1):
        for sy in (-1, 1):   # ranuras: absorben diferencias entre clones del MG995
            x, y = xc + sx * MG995_AGUJEROS_DX / 2, C_DISCO[1] + sy * MG995_AGUJEROS_DY / 2
            s -= union(cil(x - 1.5, y, zt - 6, zt + 1, 1.7, seg=24), cil(x + 1.5, y, zt - 6, zt + 1, 1.7, seg=24),
                       caja(x - 1.5, x + 1.5, y - 1.7, y + 1.7, zt - 6, zt + 1))
    for sx in (-1, 1):
        s -= cil(sx * 66, 0, zt - 6, zt + 1, 1.7, seg=24)
    return s


def envolvente_mg995():
    """Volumen aproximado del MG995 + horn (solo para verificar interferencias)."""
    zt = z_soporte()
    cx0 = C_DISCO[0] - MG995_EJE_DESDE_EXTREMO
    cuerpo = caja(cx0, cx0 + MG995_L, C_DISCO[1] - MG995_A / 2, C_DISCO[1] + MG995_A / 2, zt - 30, zt + 13)
    orejas = caja(cx0 - 6.7, cx0 + MG995_L + 6.7, C_DISCO[1] - MG995_A / 2, C_DISCO[1] + MG995_A / 2,
                  zt + 0.05, zt + 2.5)
    eje = cil(*C_DISCO, zt + 13, Z_PLACA_INF + E_PLACA_INF + 3.4, 2.9)
    horn = cil(*C_DISCO, Z_PLACA_INF + E_PLACA_INF + 3.4, Z_PLACA_INF + E_PLACA_INF + 7.2, 12.5)
    return union(cuerpo, orejas, eje, horn)


# =============================================================================
# 08 MÓDULO DOSIFICADOR
#   08a carcasa (anillo exterior)      08b disco (gira con el MG995)
#   08c placa superior (entrada)       08d placa base (salida + cámara del disco)
# =============================================================================
CONDUCTO_CABLES = (-56.0, 56.0)


def p08a_carcasa():
    return carcasa(Z_DOSIF, Z_TOLVA) - agujeros_junta(Z_DOSIF) + labio(Z_TOLVA)


def p08d_placa_base():
    """Se imprime plana. Apoya sobre el labio del cuerpo y queda encajada en la carcasa."""
    z0, z_pl = Z_PLACA_INF, Z_PLACA_INF + E_PLACA_INF
    p = prisma(contorno(T + CLR), z0, z_pl)
    camara = cil(*C_DISCO, z_pl - 0.01, Z_ASIENTO, R_CAMARA + 3) - cil(*C_DISCO, z_pl - 1, Z_ASIENTO + 1, R_CAMARA)
    collar = cil(*C_DISCO, z_pl - 0.01, z_pl + 3, 9)                 # laberinto anti-polvo
    conducto = cil(*CONDUCTO_CABLES, z0, Z_TOLVA - 0.2, 6)
    p = union(p, camara, collar, conducto)
    ox, oy = polar(C_DISCO, R_BOLSILLO, ANG_SALIDA)
    p -= cil(ox, oy, z0 - 1, z_pl + 1, D_SALIDA / 2)                 # salida -> conducto
    p -= cil(*C_DISCO, z0 - 1, z_pl + 4, 7)                          # paso de la estría del servo
    p -= cil(*CONDUCTO_CABLES, z0 - 1, Z_TOLVA + 1, 4)                # cable del sensor de nivel (seco)
    # asiento cónico (45°) de la placa superior: la centra y la sostiene
    p -= cil(*C_DISCO, Z_ASIENTO - 3.2, Z_ASIENTO + 0.01, R_CAMARA, R_CAMARA + 3.2, seg=128)
    for ang in (ANG_ENTRADA, ANG_CERRADO, ANG_SALIDA):               # marcas de calibración
        x, y = polar(C_DISCO, R_CAMARA + 1.8, ang)
        p -= cil(x, y, Z_ASIENTO - 1.5, Z_ASIENTO + 1, 1.0, seg=16)
    kx, ky = polar(C_DISCO, R_CAMARA + 1.5, 90)                      # chavetero anti-giro
    p -= caja(kx - 3, kx + 3, ky - 2, ky + 2, Z_ASIENTO - 2.5, Z_ASIENTO + 1)
    return p


def p08b_disco():
    """Disco en posición de ensamblaje con el bolsillo en ANG_CERRADO."""
    z0, z1 = Z_DISCO, Z_DISCO + E_DISCO
    d = cil(*C_DISCO, z0, z1, R_DISCO, seg=128)
    bx, by = polar(C_DISCO, R_BOLSILLO, ANG_CERRADO)
    d -= cil(bx, by, z0 - 1, z1 + 1, D_BOLSILLO / 2)
    d -= cil(bx, by, z1 - 1.5, z1 + 0.01, D_BOLSILLO / 2, D_BOLSILLO / 2 + 1.5)  # chaflán de entrada
    d -= cil(*C_DISCO, z0 - 1, z0 + 7.5, 13.5)                        # alojamiento del horn + collar
    d -= cil(*C_DISCO, z0, z1 + 1, 3.5)                               # acceso al tornillo central
    for k in range(4):                                                # ranuras para tornillos del horn
        a = ANG_CERRADO + 45 + 90 * k
        for r in np.linspace(6, 10, 5):
            x, y = polar(C_DISCO, r, a)
            d -= cil(x, y, z0 + 7, z1 + 1, 1.1, seg=16)
    mx, my = polar(C_DISCO, R_DISCO, ANG_CERRADO)                     # marca del bolsillo
    return d - cil(mx, my, z1 - 2, z1 + 1, 1.5, seg=16)


Z_ZOCALO = Z_TOLVA + 2.0     # el zócalo de la entrada sube 2 mm dentro de la tolva (laberinto)


def p08c_placa_superior():
    z0 = Z_PLACA_SUP
    p = cil(*C_DISCO, z0, Z_ASIENTO - 3.2 + 0.1, R_CAMARA - 0.2, seg=128)
    p += cil(*C_DISCO, Z_ASIENTO - 3.2 + 0.1, Z_ASIENTO + 0.1, R_CAMARA - 0.2, R_CAMARA + 3.0, seg=128)
    p += cil(*C_DISCO, Z_ASIENTO + 0.1, Z_ASIENTO + 2, R_CAMARA + 3.0, seg=128)
    ix, iy = polar(C_DISCO, R_BOLSILLO, ANG_ENTRADA)
    p += cil(ix, iy, Z_ASIENTO + 2 - 0.01, Z_ZOCALO, 19)              # zócalo de la boca de la tolva
    p -= cil(ix, iy, Z_ASIENTO + 2, Z_ZOCALO + 1, 16.5)
    p -= cil(ix, iy, z0 - 1, Z_ASIENTO + 3, D_ENTRADA / 2)
    p -= cil(ix, iy, z0 - 0.01, z0 + 1.2, D_ENTRADA / 2 + 1.2, D_ENTRADA / 2)  # chaflán anti-cizalla
    kx, ky = polar(C_DISCO, R_CAMARA + 1.5, 90)
    p += caja(kx - 2.7, kx + 2.7, ky - 1.7, ky + 1.7, Z_ASIENTO - 2.2, Z_ASIENTO + 0.5)
    for a in (ANG_ENTRADA + 150, ANG_ENTRADA - 150):                  # agujeros para levantarla
        x, y = polar(C_DISCO, R_CAMARA - 8, a)
        p -= cil(x, y, z0 - 1, z0 + 10, 4)
    return p


# =============================================================================
# 07 TOLVA (embudo cónico oblicuo con paredes >= 55°)
# =============================================================================
Z_CIL = Z_TOLVA + H_TOLVA - 38       # inicio de la parte cilíndrica
R_TOLVA = 70.0
Z_EMBUDO = Z_TOLVA + 4.0             # fondo del embudo (la boca apoya en la cama de impresión)
ANG_LLAVE = 135.0                    # llave de la tapa: misma esquina que el conducto de cables

# Sensor de nivel (HC-SR04 n.º 2) en la tapa, apuntando a la boca de la tolva
E_TAPA = 5.0
CAP_C = (32.0, 4.0)                  # centro de la cápsula (transductores en Y)
Z_SENSOR = Z_TAPA - 26.0             # cara de los transductores (457)
Z_MAX = Z_SENSOR - 30.0              # línea MAX de llenado: >= 2 cm del sensor (mínimo del HC-SR04)


def embudo_interior(holgura=0.0):
    ix, iy = polar(C_DISCO, R_BOLSILLO, ANG_ENTRADA)
    return Manifold.batch_hull([cil(0, 0, Z_CIL, Z_CIL + 0.01, R_TOLVA + holgura),
                                cil(ix, iy, Z_EMBUDO - 0.01, Z_EMBUDO, D_ENTRADA / 2 + holgura)])


def caja_rotada(r0, r1, ancho, z0, z1, ang):
    """Bloque radial (de r0 a r1) centrado en el ángulo 'ang'."""
    return caja(r0, r1, -ancho / 2, ancho / 2, z0, z1).rotate([0, 0, ang])


def p07_tolva():
    z0, z1 = Z_TOLVA, Z_TAPA
    ix, iy = polar(C_DISCO, R_BOLSILLO, ANG_ENTRADA)
    emb_ext = Manifold.batch_hull([cil(0, 0, Z_CIL, Z_CIL + 0.01, R_TOLVA + 2.5),
                                   cil(ix, iy, Z_EMBUDO, Z_EMBUDO + 0.01, D_ENTRADA / 2 + 2.5)])
    cilindro = cil(0, 0, Z_CIL, z1, R_TOLVA + 2.5)
    boca = cil(ix, iy, z0, Z_EMBUDO + 0.5, D_ENTRADA / 2 + 2.0)       # entra en el zócalo de 08c
    anillo_sup = prisma(contorno(T - 0.01), z1 - 4, z1) - cil(0, 0, z1 - 5, z1 + 1, R_TOLVA)
    conducto = cil(*CONDUCTO_CABLES, z0, z1, 6)
    t = union(carcasa(z0, z1), emb_ext, cilindro, boca, anillo_sup, conducto)
    t -= union(embudo_interior(), cil(0, 0, Z_CIL, z1 + 1, R_TOLVA), cil(ix, iy, z0 - 1, Z_EMBUDO + 0.5, D_ENTRADA / 2))
    t -= cil(*CONDUCTO_CABLES, z0 - 1, z1 + 1, 4)
    # ranura de la llave de la tapa (una sola posición posible)
    t -= caja_rotada(R_TOLVA - 0.5, R_TOLVA + 1.8, 6.0, z1 - 8.5, z1 + 1, ANG_LLAVE)
    # línea MAX de llenado: surco de 0,6 mm en la cara interior del embudo
    surco = embudo_interior(0.6) ^ caja(-100, 100, -100, 100, Z_MAX - 0.5, Z_MAX + 0.5)
    t -= surco
    return t - agujeros_junta(z0)


# =============================================================================
# 13a TAPA SUPERIOR  ·  13b CÁPSULA del sensor de nivel  ·  13c tapa de la cápsula
#   La cápsula es una pieza aparte (se imprime con el piso sobre la cama, sin
#   puentes) que cuelga de la tapa por un ala a 45° encajada en un avellanado.
#   El alimento solo "ve" los dos transductores; la placa queda en seco.
# =============================================================================
CAP_IN = (CAP_C[0] - 30, CAP_C[0] + 12, CAP_C[1] - 26, CAP_C[1] + 26)  # interior x0,x1,y0,y1
CAP_PARED, CAP_ALA = 2.0, 4.0          # pared y vuelo del ala (a 45°)
HC_SOBRE_PISO = 10.0                   # nervios: la cara de las cápsulas queda al ras del piso
AG_TAPA_CAPSULA = [(CAP_C[0] - 9, CAP_C[1] + 26 + CAP_PARED + CAP_ALA + 3.5),
                   (CAP_C[0] - 9, CAP_C[1] - 26 - CAP_PARED - CAP_ALA - 3.5)]
SALIDA_CABLE_Y = CAP_C[1] + 20         # muesca del cable en la pared -x de la cápsula


def _rect(lim, d, z0, z1):
    x0, x1, y0, y1 = lim
    return caja(x0 - d, x1 + d, y0 - d, y1 + d, z0, z1)


def capsula_exterior(holgura=0.0):
    """Paredes + ala troncopiramidal a 45° (la misma forma recorta la tapa)."""
    zt = Z_TAPA + E_TAPA
    d = CAP_PARED + holgura
    cuerpo = _rect(CAP_IN, d, Z_SENSOR - holgura, zt)
    ala = Manifold.batch_hull([_rect(CAP_IN, d, zt - CAP_ALA, zt - CAP_ALA + 0.01),
                               _rect(CAP_IN, d + CAP_ALA, zt - 0.01, zt + holgura)])
    return cuerpo + ala


def p13a_tapa():
    z0, zt = Z_TAPA, Z_TAPA + E_TAPA
    t = cil(0, 0, z0, zt, R_TOLVA + 3, seg=128)
    t += cil(0, 0, z0 - 8, z0 + 0.01, R_TOLVA - 0.4, seg=128) - cil(0, 0, z0 - 9, z0, R_TOLVA - 2.4, seg=128)
    t += caja_rotada(R_TOLVA - 0.6, R_TOLVA + 1.4, 5.0, z0 - 7, z0 + 0.01, ANG_LLAVE)     # llave
    for x, y in AG_TAPA_CAPSULA:                                           # tetones de los tornillos de 13c
        t += cil(x, y, z0 - 8, z0 + 0.01, 4.0, seg=32)
    for sy in (-1, 1):                                                     # muescas para los dedos
        t -= cil(0, sy * (R_TOLVA + 3), z0 - 1, zt + 1, 9)
    t -= capsula_exterior(CLR) + _rect(CAP_IN, CAP_PARED + CLR, z0 - 10, zt)   # avellanado + abertura
    for x, y in AG_TAPA_CAPSULA:
        t -= cil(x, y, z0 - 9, zt + 1, 1.25, seg=24)                       # rosca en plástico (M3)
    # ranura del cable sobre la tapa: de la cápsula al borde, hacia el conducto de la esquina
    x_ala = CAP_IN[0] - CAP_PARED - CAP_ALA
    ex, ey = polar((0, 0), R_TOLVA + 4, ANG_LLAVE)
    ranura = Manifold.batch_hull([cil(x_ala, SALIDA_CABLE_Y, zt - 3.5, zt + 1, 2.6, seg=24),
                                  cil(ex, ey, zt - 3.5, zt + 1, 2.6, seg=24)])
    return t - ranura


def p13b_capsula():
    zs, zt = Z_SENSOR, Z_TAPA + E_TAPA
    cx, cy = CAP_C
    c = capsula_exterior() - _rect(CAP_IN, 0, zs + CAP_PARED, zt + 1)
    for s in (-1, 1):
        c -= cil(cx, cy + s * HC_TRANSD_SEP / 2, zs - 1, zs + CAP_PARED + 1, HC_TRANSD_D / 2 + 0.4)
        # nervios bajo los bordes largos de la placa (fuera de los transductores)
        x0, x1 = sorted([cx + s * (HC_A / 2 - 1.2), cx + s * (HC_A / 2 + 0.3)])
        c += caja(x0, x1, cy - HC_L / 2 + 1, cy + HC_L / 2 - 1, zs + CAP_PARED - 0.01, zs + CAP_PARED + HC_SOBRE_PISO)
    # muesca de salida del cable (pared -x, junto a la ranura de la tapa)
    x_ala = CAP_IN[0] - CAP_PARED - CAP_ALA
    c -= caja(x_ala - 1, CAP_IN[0] + 0.5, SALIDA_CABLE_Y - 2.6, SALIDA_CABLE_Y + 2.6, zt - 4.5, zt + 1)
    return c


def p13c_tapa_capsula():
    zt = Z_TAPA + E_TAPA
    x0, x1, y0, y1 = CAP_IN
    m = CAP_PARED + CAP_ALA
    c = caja(x0 - m - 2, x1 + m + 2, y0 - m - 7, y1 + m + 7, zt + 0.1, zt + 2.6)
    for x, y in AG_TAPA_CAPSULA:
        c -= cil(x, y, zt - 1, zt + 4, 1.7, seg=24)
    return c


# =============================================================================
# 12 ESTACIÓN SOLAR REMOTA (recomendación del profesor: el panel va aparte, donde
# haya sol, unido a la torre por un cable con conector GX12). 12a base con
# horquilla, 12b bandeja del panel. La bandeja gira sobre dos tornillos M4 que
# roscan en tuercas alojadas en sus nudillos; al apretarlos queda fija.
# =============================================================================
E_BANDEJA = 5.0
BANDEJA_W, BANDEJA_H = PANEL_W + 8, PANEL_H + 8
NUDILLO_R, NUDILLO_E = 7.0, 8.0      # nudillos de la bandeja: eje a 7 mm de su cara inferior
OREJA_E = 5.0                        # espesor de las orejas de la horquilla
Z_PIVOTE = 60.0                      # altura del eje de giro sobre el suelo
X_OREJA = BANDEJA_W / 2 + NUDILLO_E + 0.5   # cara interior de las orejas
ANGULOS_PANEL = (0, 15, 30, 45, 60, 75)


def p12a_estacion_base():
    b = caja(-65, 65, -55, 55, 0, 6)
    for s in (-1, 1):
        x0, x1 = sorted([s * X_OREJA, s * (X_OREJA + OREJA_E)])
        xm = (x0 + x1) / 2
        oreja = caja(x0, x1, -10, 10, 5.9, Z_PIVOTE) + cil_eje((xm, 0, Z_PIVOTE), "x", OREJA_E, 10)
        cartela = Manifold.batch_hull([caja(x0, x1, -22, 22, 5.9, 6.0), caja(x0, x1, -10, 10, 5.9, 32)])
        b += oreja + cartela
        b -= cil_eje((xm, 0, Z_PIVOTE), "x", OREJA_E + 2, 2.2)              # M4 pasante
    for x in (-55, 55):                                                    # fijación al suelo/muro
        for y in (-45, 45):
            b -= cil(x, y, -1, 7, 2.3, seg=24)
    b -= caja(-30, 30, 22, 42, 2, 7)                                       # alojamiento de lastre
    for x in (-6, 6):                                                      # brida del cable: dos ranuras
        b -= caja(x - 1.6, x + 1.6, -49.5, -44.5, -1, 7)
    b -= caja(-8, 8, -49.5, -44.5, -1, 2.5)                                # túnel inferior de la brida
    return b


def p12b_estacion_bandeja(angulo=0.0):
    t = caja(-BANDEJA_W / 2, BANDEJA_W / 2, -BANDEJA_H / 2, BANDEJA_H / 2, 0, E_BANDEJA)
    t -= caja(-PANEL_W / 2 - 0.5, PANEL_W / 2 + 0.5, -PANEL_H / 2 - 0.5, PANEL_H / 2 + 0.5,
              E_BANDEJA - PANEL_E + 0.5, E_BANDEJA + 1)                    # alojamiento del panel
    t -= caja(-25, 25, -25, 25, -1, E_BANDEJA)                             # ventana: soldaduras y cable
    for s in (-1, 1):
        x0, x1 = sorted([s * (BANDEJA_W / 2 - 0.01), s * (BANDEJA_W / 2 + NUDILLO_E)])
        nudillo = Manifold.batch_hull([cil_eje(((x0 + x1) / 2, 0, NUDILLO_R), "x", x1 - x0, NUDILLO_R),
                                       caja(x0, x1, -NUDILLO_R, NUDILLO_R, 0, 0.01)])
        nudillo -= cil_eje(((x0 + x1) / 2, 0, NUDILLO_R), "x", NUDILLO_E + 2, 2.2)
        # tuerca M4 alojada en la cara exterior (hexágono con vértice arriba: sin puente)
        hexa = Manifold.cylinder(4.4, 7.3 / math.sqrt(3), 7.3 / math.sqrt(3), 6).rotate([0, 90, 0])
        xe = x1 if s > 0 else x0
        hexa = hexa.translate([xe - 3.4, 0, NUDILLO_R]) if s > 0 else hexa.rotate([0, 0, 180]).translate([xe + 3.4, 0, NUDILLO_R])
        t += nudillo - hexa
    # en el ensamblaje (solo para verificar) la bandeja gira 'angulo' alrededor del eje
    return t.translate([0, 0, -NUDILLO_R]).rotate([angulo, 0, 0]).translate([0, 0, Z_PIVOTE])


# =============================================================================
# 14 TAPA LATERAL DE SERVICIO (trasera de la bahía electrónica)
# =============================================================================
def p14_tapa_servicio():
    x0, x1, z0, z1 = TAPA_SERV
    t = caja(x0 - 2.5, x1 + 2.5, W / 2, W / 2 + 3, z0 - 8, z1 + 8)
    t += abertura_servicio(R_INT + 0.5, W / 2 + 0.01, holgura=0.4) - \
        abertura_servicio(R_INT, W / 2 - 0.5, holgura=2.4)
    for x, zz in TAPA_AG:
        t -= cil_eje((x, W / 2 + 1.5, zz), "y", 8, 1.7)
    t -= ranuras("y", W / 2 + 1.5, np.arange(-30, 31, 8), 150, 190)
    return t - ranuras("y", W / 2 + 1.5, np.arange(-30, 31, 8), z0 + 25, z0 + 70)


# =============================================================================
# 16 SOPORTE ESTRUCTURAL: CAJÓN DE ENERGÍA (batería, BMS, convertidores)
# =============================================================================
def p16_cajon_energia():
    z0 = Z_CAJON + 0.2
    piso = caja(-CAJON_X, CAJON_X, -45, W / 2 + 0.01, z0, z0 + 2.5)
    lados = union(caja(-CAJON_X, -CAJON_X + 2, -45, R_INT, z0 + 2.4, z0 + 10),
                  caja(CAJON_X - 2, CAJON_X, -45, R_INT, z0 + 2.4, z0 + 10),
                  caja(-CAJON_X, CAJON_X, -45, -43, z0 + 2.4, z0 + 10))
    frente = caja(-55, 55, W / 2 + 0.2, W / 2 + 3.2, z0, Z_CUERPO - 0.5)
    c = union(piso, lados, frente)
    for x in np.arange(-35, 36, 10):          # rejilla de montaje M3 (paso 10 mm)
        for y in np.arange(-35, 66, 10):
            c -= cil(x, y, z0 - 1, z0 + 3, 1.6, seg=16)
    c -= caja(-9.6, 9.6, W / 2 - 1, W / 2 + 5, 28, 41)        # interruptor basculante (VERIFICAR)
    c -= caja(-35 - 6, -35 + 6, W / 2 - 1, W / 2 + 5, 19, 25)  # USB-C del cargador (ajustar)
    c -= cil_eje((35, W / 2 + 1.7, 38), "y", 8, 4)            # portafusible/LED (opcional)
    c -= cil_eje((-35, W / 2 + 1.7, 36), "y", 8, 6.1)         # conector GX12 del panel solar remoto
    c -= ranuras("y", W / 2 + 1.7, np.arange(15, 46, 6), 17, 31, ancho=2.5)
    for sx in (-1, 1):
        c -= cil_eje((sx * 50.5, W / 2 + 1.7, 22), "y", 8, 1.7)
    return c


# =============================================================================
# 11 COMEDERO (se encastra con dos lengüetas bajo el plinto)
# =============================================================================
def p11_comedero():
    y_borde = -PLINTO / 2
    bx, by = BOWL_C
    placa = caja(-75, 75, by - BOWL_R - 4, y_borde - 0.3, 0, 4)
    cuenco = cil(bx, by, 0, BOWL_H + 4, BOWL_R) - cil(bx, by, 4, BOWL_H + 5, BOWL_R - 3)
    c = union(placa, cuenco)
    for s in (-1, 1):
        x0, x1 = sorted([s * LENGUETAS_X[0], s * LENGUETAS_X[1]])
        c += caja(x0, x1, y_borde - 0.5, y_borde + 15, 0, 4)
    return c


# =============================================================================
# 15 SEPARADORES (tubos para M3: cajón de energía y calces de la viga del servo)
# =============================================================================
def p15_separadores():
    piezas = []
    largos = [3, 3, 3, 3, 6, 6, 10, 10, 10, 10, 10, 10]
    for i, L in enumerate(largos):
        x, y = (i % 6) * 12, (i // 6) * 12
        piezas.append(cil(x, y, 0, L, 3.5, seg=32) - cil(x, y, -1, L + 1, 1.7, seg=24))
    return union(*piezas)


# =============================================================================
# EXPORTACIÓN
# =============================================================================
def a_trimesh(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    return trimesh.Trimesh(vertices=v, faces=f, process=True)


def orientar(m, rot):
    """Aplica la rotación de impresión y apoya la pieza en z = 0 centrada en XY."""
    if rot:
        m = m.rotate(rot)
    (x0, y0, z0, x1, y1, z1) = m.bounding_box()
    return m.translate([-(x0 + x1) / 2, -(y0 + y1) / 2, -z0])


PIEZAS = [
    # nombre, función, rotación de impresión (grados)
    ("01_Base_Torre", p01_base, None),
    ("02_Cuerpo_Principal", p02_cuerpo, None),
    ("03_Modulo_HC_SR04", p03_pod_hc, [90, 0, 0]),
    ("04_Modulo_ESP32_CAM", p04_pod_cam, [90, 0, 0]),
    ("05_Modulo_ESP32", p05_bandeja_esp32, None),
    ("06_Soporte_MG995", p06_soporte_servo, None),
    ("07_Tolva", p07_tolva, None),
    ("08a_Carcasa_Dosificador", p08a_carcasa, None),
    ("08b_Disco_Dosificador", p08b_disco, [180, 0, 0]),
    ("08c_Placa_Superior_Dosificador", p08c_placa_superior, None),
    ("08d_Placa_Base_Dosificador", p08d_placa_base, None),
    ("09_Conducto_Alimento", p09_conducto, [-90, 0, 0]),
    ("10_Salida_Alimento", p10_salida, [-45, 0, 0]),
    ("11_Comedero", p11_comedero, None),
    ("12a_Estacion_Solar_Base", p12a_estacion_base, None),
    ("12b_Estacion_Solar_Bandeja", p12b_estacion_bandeja, None),
    ("13a_Tapa_Superior_Tolva", p13a_tapa, [180, 0, 0]),
    ("13b_Capsula_Sensor_Nivel", p13b_capsula, None),
    ("13c_Tapa_Capsula_Sensor", p13c_tapa_capsula, None),
    ("14_Tapa_Lateral_Servicio", p14_tapa_servicio, [-90, 0, 0]),
    ("15_Separadores", p15_separadores, None),
    ("16_Soporte_Estructural_Cajon_Energia", p16_cajon_energia, None),
]

# Impresora del proyecto: Elegoo Neptune 4 Plus, volumen 320 x 320 x 385 mm (especificación
# del fabricante). Se deja un margen de 5 mm por lado para falda/borde (skirt/brim).
IMPRESORA = "Elegoo Neptune 4 Plus"
VOLUMEN_NOMINAL = (320.0, 320.0, 385.0)
VOLUMEN_IMPRESORA = (310.0, 310.0, 380.0)
# Piezas sin posición en la torre: juego de separadores y la estación solar (va aparte)
SUELTAS = {"15_Separadores", "12a_Estacion_Solar_Base", "12b_Estacion_Solar_Bandeja"}


def construir():
    return {nombre: fn() for nombre, fn, _ in PIEZAS}


def interferencia(a, b):
    return (a ^ b).volume()


def area_apoyo(m):
    """Área de la primera capa (0,2 mm) en la orientación de impresión."""
    return m.slice(0.1).area()


def voladizos(m, limite_grados=45.0):
    """Área (mm2) de caras que miran hacia abajo más de 'limite' respecto de la
    vertical, sin contar la cara apoyada en la cama ni los escalones de las rampas.
    Incluye los puentes (techos de agujeros, ranuras y canales); en el README se
    detalla cada puente y su luz."""
    t = a_trimesh(m)
    n = t.face_normals
    cz = t.triangles_center[:, 2]
    abajo = (n[:, 2] < -math.cos(math.radians(limite_grados))) & (cz > 0.3)
    if not abajo.any():
        return 0.0, 0.0
    caras = t.faces[abajo]
    padre = {}                                   # unión-búsqueda por vértices compartidos

    def raiz(v):
        while padre.setdefault(v, v) != v:
            padre[v] = padre[padre[v]]
            v = padre[v]
        return v

    for f in caras:
        r0 = raiz(f[0])
        for v in f[1:]:
            padre[raiz(v)] = r0
    grupos = {}
    for f in caras:
        grupos.setdefault(raiz(f[0]), set()).update(f)
    area_caras = dict(zip(map(tuple, caras), t.area_faces[abajo]))
    area_total = 0.0
    for vs in grupos.values():
        pts = t.vertices[list(vs)]
        ext = pts.max(axis=0) - pts.min(axis=0)
        a = sum(ar for f, ar in area_caras.items() if f[0] in vs)
        if a / max(ext[0], ext[1], 1e-6) < 1.0:
            continue          # escalón de 0,25 mm de una rampa a 45° (no es voladizo real)
        area_total += a
    return area_total, 0.0


def verificar(piezas):
    """Comprobaciones geométricas automáticas. Devuelve lista de (ok, texto)."""
    r = []

    def chk(ok, txt):
        r.append((bool(ok), txt))

    # 1) Dosificador: el bolsillo nunca conecta entrada y salida a la vez
    r_suma_e = (D_BOLSILLO + D_ENTRADA) / 2
    r_suma_s = (D_BOLSILLO + D_SALIDA) / 2
    ang_e = math.degrees(2 * math.asin(r_suma_e / (2 * R_BOLSILLO)))
    ang_s = math.degrees(2 * math.asin(r_suma_s / (2 * R_BOLSILLO)))
    sep = abs(ANG_ENTRADA - ANG_SALIDA)
    chk(sep > ang_e + ang_s, f"Disco: separación {sep:.0f}° > {ang_e:.1f}°+{ang_s:.1f}° "
        f"(margen {sep - ang_e - ang_s:.1f}°): nunca hay paso directo tolva->canal")
    d_cerr_e = 2 * R_BOLSILLO * math.sin(math.radians(abs(ANG_CERRADO - ANG_ENTRADA) / 2))
    chk(d_cerr_e > r_suma_e, f"Posición CERRADO aislada de la entrada ({d_cerr_e:.1f} > {r_suma_e:.1f} mm)")
    vol = math.pi * (D_BOLSILLO / 2) ** 2 * E_DISCO / 1000
    chk(True, f"Volumen geométrico del bolsillo: {vol:.2f} cm3 por ciclo (gramos: CALIBRAR)")
    chk(R_CAMARA + 3 + math.hypot(*C_DISCO) < R_INT - CLR, "Cámara del disco dentro de la torre")

    # 2) Recorrido del alimento: alineaciones
    ox, oy = polar(C_DISCO, R_BOLSILLO, ANG_SALIDA)
    chk(abs(ox) < 1e-6 and abs(oy - CANAL_Y) < 1e-6, "Salida del disco coaxial con el conducto")
    chk(D_SALIDA < CANAL_IN, "Conducto (36 mm) mayor que la salida (32 mm): sin escalón que retenga")
    chk(CANAL_Y + CANAL_IN / 2 + CANAL_PARED <= TABIQUE_Y[0], "Conducto completamente delante del tabique")

    # 3) Interferencias en el ensamblaje (volumen común ~ 0)
    servo = envolvente_mg995()
    nombres = [n for n, _, _ in PIEZAS if n not in SUELTAS]
    malas = 0
    for i, na in enumerate(nombres):
        for nb in nombres[i + 1:]:
            v = interferencia(piezas[na], piezas[nb])
            if v >= 1.0:
                malas += 1
                chk(False, f"Interferencia {na} <-> {nb} ({v:.1f} mm3)")
    chk(malas == 0, f"Interferencias entre las {len(nombres)} piezas ensambladas: {malas} de "
        f"{len(nombres) * (len(nombres) - 1) // 2} pares")
    for nb in nombres:
        v = interferencia(servo, piezas[nb])
        chk(v < 1.0, f"MG995 no interfiere con {nb} ({v:.2f} mm3)")

    # 4) Separación electrónica / alimento
    canal_int, _ = tramo_canal(CANAL_IN / 2, Z_PLACA_INF - 1)
    canal_int = canal_int.trim_by_plane([0, 1, 0], -R_INT + 0.5)
    for nombre in ("05_Modulo_ESP32", "04_Modulo_ESP32_CAM", "03_Modulo_HC_SR04", "06_Soporte_MG995"):
        chk(interferencia(canal_int, piezas[nombre]) < 1.0, f"El volumen interior del canal no contiene {nombre}")
    chk(interferencia(canal_int, servo) < 1.0, "El volumen interior del canal no contiene el MG995")

    # 5) El pico deja caer el alimento dentro del comedero
    punta_y = -W / 2 - LARGO_PICO
    chk(BOWL_C[1] - BOWL_R + 3 < punta_y - 10 < BOWL_C[1] + BOWL_R - 3,
        f"La punta del pico (y={punta_y:.0f}) cae dentro del comedero")
    z_borde_inf = Z_SALIDA_PARED - (LARGO_PICO + 3.5) - (CANAL_IN / 2 + 2.5) * math.sqrt(2)
    chk(z_borde_inf > BOWL_H + 4 + 5, f"Borde inferior del pico (z~{z_borde_inf:.0f}) sobre el borde del comedero")

    # 6) Ángulo de la tolva
    ix, iy = polar(C_DISCO, R_BOLSILLO, ANG_ENTRADA)
    alcance = R_TOLVA + math.hypot(ix, iy) - D_ENTRADA / 2
    ang = math.degrees(math.atan2(Z_CIL - Z_EMBUDO, alcance))
    chk(ang >= 55 - 0.5, f"Pared más tendida de la tolva: {ang:.1f}° (>= 55° recomendado para croquetas)")

    # 7) Sensor de nivel: alcance mínimo, cápsula fuera del alimento, capacidad y umbrales
    interior = union(embudo_interior(), cil(0, 0, Z_CIL, Z_TAPA, R_TOLVA),
                     cil(ix, iy, Z_TOLVA - 1, Z_EMBUDO + 0.01, D_ENTRADA / 2))

    def vol_hasta(h):
        return (interior ^ caja(-100, 100, -100, 100, Z_TOLVA - 2, h)).volume() / 1000

    v_max = vol_hasta(Z_MAX)
    chk(Z_SENSOR - Z_MAX >= 20, f"Línea MAX a {Z_SENSOR - Z_MAX:.0f} mm de los transductores (mínimo del "
        f"HC-SR04: 20 mm); capacidad hasta MAX ≈ {v_max:.0f} cm3 (gramos = cm3 x densidad aparente: MEDIR)")
    # la tabla altura -> volumen del firmware (NivelGeometria.h) debe coincidir con esta tolva
    v0 = vol_hasta(Z_EMBUDO)
    tabla = [100 * (vol_hasta(Z_EMBUDO + k / 10 * (Z_MAX - Z_EMBUDO)) - v0) / (v_max - v0) for k in range(11)]
    fw_dir = Path(__file__).resolve().parents[1] / "ESP32/Dispensador_ESP32"
    fw = [float(v) for v in re.findall(r"([\d.]+)f", (fw_dir / "NivelGeometria.h").read_text().split("{", 1)[1].split("}", 1)[0])]
    dif = max(abs(a - b) for a, b in zip(tabla, fw)) if len(fw) == 11 else 99
    chk(dif < 0.6, f"NivelGeometria.h coincide con la tolva (dif. máx. {dif:.2f} %)" + ("" if dif < 0.6 else
        " -> copie: {" + ", ".join(f"{v:.1f}f" for v in tabla) + "}"))
    # umbrales del firmware (porcentaje de VOLUMEN): a qué altura y cuánto alimento corresponden
    cfg = (fw_dir / "config.h").read_text()
    bolsillo = math.pi * (D_BOLSILLO / 2) ** 2 * E_DISCO / 1000
    for nombre in ("NIVEL_REARME_PCT", "NIVEL_ALERTA_PCT", "NIVEL_VACIO_PCT"):
        pct = float(re.search(nombre + r"\s+([\d.]+)", cfg).group(1))
        k = next(i for i in range(10) if tabla[i + 1] >= pct)
        h = (k + (pct - tabla[k]) / (tabla[k + 1] - tabla[k])) / 10 * (Z_MAX - Z_EMBUDO)
        v = pct / 100 * (v_max - v0)
        chk(True, f"{nombre} = {pct:.0f} % del volumen ≈ {v:3.0f} cm3 (≈{v / bolsillo:4.1f} bolsillos del disco): "
            f"superficie a {h:3.0f} mm sobre la boca")
    chk(HC_A + 18 <= CAP_IN[1] - CAP_IN[0] and HC_L + 4 <= CAP_IN[3] - CAP_IN[2],
        f"Cápsula {CAP_IN[1] - CAP_IN[0]:.0f}x{CAP_IN[3] - CAP_IN[2]:.0f} mm: HC-SR04 {HC_L:.0f}x{HC_A:.0f} + 18 mm de pines/cable")
    chk(interferencia(piezas["13b_Capsula_Sensor_Nivel"], interior ^ caja(-100, 100, -100, 100, 0, Z_MAX)) < 0.01,
        "La cápsula del sensor queda por encima de la línea MAX (nunca toca el alimento)")

    # 8) Estación solar remota: la bandeja gira de 0° a 75° sin tocar la base
    base = p12a_estacion_base()
    peor = max(interferencia(base, p12b_estacion_bandeja(a)) for a in ANGULOS_PANEL)
    chk(peor < 1.0, f"Bandeja del panel libre en {', '.join(str(a) for a in ANGULOS_PANEL)}° ({peor:.2f} mm3)")
    alto = min(p12b_estacion_bandeja(a).bounding_box()[2] for a in ANGULOS_PANEL)
    chk(alto > 6.5, f"Bandeja siempre sobre la placa base (punto más bajo z = {alto:.1f} mm a 75°)")

    # 9) Impresora
    fuera = []
    for nombre, _, rot in PIEZAS:
        x0, y0, z0, x1, y1, z1 = orientar(piezas[nombre], rot).bounding_box()
        if any(d > lim for d, lim in zip((x1 - x0, y1 - y0, z1 - z0), VOLUMEN_IMPRESORA)):
            fuera.append(nombre)
    chk(not fuera, f"Las {len(PIEZAS)} piezas caben en la {IMPRESORA} "
        f"({VOLUMEN_NOMINAL[0]:.0f}x{VOLUMEN_NOMINAL[1]:.0f}x{VOLUMEN_NOMINAL[2]:.0f} mm; se usa "
        f"{VOLUMEN_IMPRESORA[0]:.0f}x{VOLUMEN_IMPRESORA[1]:.0f}x{VOLUMEN_IMPRESORA[2]:.0f} con margen)"
        + (f" FUERA: {fuera}" if fuera else ""))
    return r


def main():
    SALIDA.mkdir(exist_ok=True)
    piezas = construir()
    print("Pieza                                   estado  vol(cm3)  impresión (mm)          apoyo(cm2)"
          "  puentes/voladizos>45° (cm2)")
    todo_ok = True
    for nombre, _, rot in PIEZAS:
        m = piezas[nombre]
        ok = m.status().name == "NoError" and not m.is_empty() and len(m.decompose()) >= 1
        mo = orientar(m, rot)
        x0, y0, z0, x1, y1, z1 = mo.bounding_box()
        dims = (x1 - x0, y1 - y0, z1 - z0)
        cabe = all(d <= lim for d, lim in zip(dims, VOLUMEN_IMPRESORA))
        apoyo = area_apoyo(mo) / 100
        v_area, _ = voladizos(mo)
        todo_ok &= ok and cabe and apoyo > 1
        print(f"{nombre:40s} {'OK ' if ok else 'ERR'}   {m.volume() / 1000:7.1f}   "
              f"{dims[0]:5.0f} x {dims[1]:5.0f} x {dims[2]:5.0f}   {apoyo:6.1f}      {v_area / 100:6.2f}"
              f"{'' if cabe else '  <-- NO CABE'}")
        a_trimesh(mo).export(SALIDA / f"{nombre}.stl")
    a_trimesh(union(*[m for n, m in piezas.items() if n not in SUELTAS])).export(
        SALIDA / "00_Ensamblaje_Referencia_NO_IMPRIMIR.stl")

    print("\nVERIFICACIONES:")
    for ok, txt in verificar(piezas):
        todo_ok &= ok
        print(f"  [{'OK' if ok else 'FALLA'}] {txt}")
    print("\nRESULTADO:", "todo correcto" if todo_ok else "HAY PROBLEMAS")
    return 0 if todo_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
