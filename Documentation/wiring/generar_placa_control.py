"""
Placa de control (placa perforada 90x70 mm, paso 2,54 mm) con el ESP32 DevKit V1.

    python generar_placa_control.py

Genera:
  * placa_control.svg  – vista desde el lado de los componentes, con cada cable numerado
  * placa_control.md   – lista de cables (de dónde a dónde) para soldar uno por uno

Verificaciones automáticas (el script falla si algo no cuadra):
  * cada red (net) queda conectada en un solo trozo y ningún agujero pertenece a dos redes;
  * los GPIO de la placa coinciden con ESP32/Dispensador_ESP32/config.h;
  * no se usa ningún pin prohibido (flash, UART, arranque, 3V3);
  * los divisores de los dos ECHO dejan <= 3,4 V en el GPIO con 5,1 V de alimentación.

Coordenadas: (columna 1..35, fila 1..27) contando desde la esquina superior izquierda.
El ESP32 va sobre tiras de pines HEMBRA (se puede retirar). Se asume la DOIT DevKit V1
de 30 pines (filas separadas 25,4 mm = 10 agujeros): VERIFICAR con la placa real.
"""
import math
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).resolve().parent
COLS, FILAS = 35, 27
PASO = 26                      # px por agujero en el dibujo
MARGEN = 60

# --- ESP32 DevKit V1 (30 pines), USB hacia la DERECHA, vista desde arriba -------
FILA_A = ["EN", "VP", "VN", "D34", "D35", "D32", "D33", "D25", "D26", "D27", "D14", "D12", "D13", "GND", "VIN"]
FILA_B = ["D23", "D22", "TX0", "RX0", "D21", "D19", "D18", "D5", "TX2", "RX2", "D4", "D2", "D15", "GND", "3V3"]
PROHIBIDOS = {"EN", "TX0", "RX0", "D12", "D15", "D2", "D5", "3V3", "D0"}

COMP = {
    "ESP32": {"tipo": "esp32",
              "pines": {**{f"A.{n}": (3 + i, 18) for i, n in enumerate(FILA_A)},
                        **{f"B.{n}": (3 + i, 8) for i, n in enumerate(FILA_B)}}},
    "J1": {"tipo": "conector", "texto": "J1 5 V", "pines": {"GND": (33, 2), "5V": (33, 3)}},
    "J2": {"tipo": "conector", "texto": "J2 HC-SR04", "pines": {"VCC": (33, 4), "TRIG": (33, 5), "ECHO": (33, 6), "GND": (33, 7)}},
    "J3": {"tipo": "conector", "texto": "J3 SERVO señal", "pines": {"SIG": (33, 9), "GND": (33, 10)}},
    "J4": {"tipo": "conector", "texto": "J4 MEDICIÓN", "pines": {"VBAT": (33, 12), "V6": (33, 13), "VPAN": (33, 14), "GND": (33, 15)}},
    # J5: HC-SR04 de la TOLVA (sensor de nivel). Horizontal en el borde superior; de izquierda a
    # derecha GND-ECHO-TRIG-VCC: el mismo cable de 4 hilos, girado (sin cruzar hilos).
    "J5": {"tipo": "conector", "texto": "J5 NIVEL TOLVA", "pines": {"GND": (6, 2), "ECHO": (7, 2), "TRIG": (8, 2), "VCC": (9, 2)}},
    "R5": {"tipo": "res", "texto": "R5 1k", "rotulo": "izquierda", "pines": {"1": (7, 3), "2": (7, 7)}},
    "R6": {"tipo": "res", "texto": "R6 2k", "pines": {"1": (6, 7), "2": (2, 7)}},
    "R1": {"tipo": "res", "texto": "R1 1k", "pines": {"1": (31, 6), "2": (27, 6)}},
    "R2": {"tipo": "res", "texto": "R2 2k", "pines": {"1": (24, 6), "2": (24, 10)}},
    "R3": {"tipo": "res", "texto": "R3 330", "pines": {"1": (31, 9), "2": (27, 9)}},
    "R4": {"tipo": "res", "texto": "R4 10k", "pines": {"1": (27, 11), "2": (27, 15)}},
    "C1": {"tipo": "cap", "texto": "C1 100n", "pines": {"1": (25, 23), "2": (25, 25)}},
    "C2": {"tipo": "cap", "texto": "C2 100n", "pines": {"1": (29, 22), "2": (29, 24)}},
    "C3": {"tipo": "cap", "texto": "C3 100n", "pines": {"1": (31, 21), "2": (31, 23)}},
    "C4": {"tipo": "elec", "texto": "C4 470µF", "pines": {"+": (21, 3), "-": (21, 5)}},
}

# Rutas de los cables de señal (lista de agujeros por los que pasa cada cable).
# Cada señal baja a su "carril" bajo el ESP32 y sube a su pin: así nunca pasa sobre otro pin.
RUTAS = {
    "5V": [[(33, 3), (33, 4)], [(33, 3), (21, 3)], [(21, 3), (21, 2), (9, 2)],
           [(9, 2), (9, 7), (18, 7), (18, 18), (17, 18)]],
    "TRIG2": [[(8, 2), (8, 8)]],
    "ECHO2_5V": [[(7, 2), (7, 3)]],
    "ECHO2_3V3": [[(7, 7), (7, 8)], [(7, 7), (6, 7)]],
    "TRIG": [[(33, 5), (25, 5), (25, 19), (11, 19), (11, 18)]],
    "ECHO_5V": [[(33, 6), (31, 6)]],
    "ECHO_3V3": [[(27, 6), (24, 6)], [(24, 6), (23, 6), (23, 24), (6, 24), (6, 18)]],
    "SERVO_SIG": [[(33, 9), (31, 9)]],
    "SERVO_GPIO": [[(27, 9), (27, 11)], [(27, 11), (26, 11), (26, 20), (10, 20), (10, 18)]],
    "VPAN_S": [[(33, 14), (32, 14), (32, 21), (31, 21)], [(31, 21), (9, 21), (9, 18)]],
    "V6_S": [[(33, 13), (30, 13), (30, 22), (29, 22)], [(29, 22), (8, 22), (8, 18)]],
    "VBAT_S": [[(33, 12), (28, 12), (28, 23), (25, 23)], [(25, 23), (7, 23), (7, 18)]],
}

# Bus de GND en "U": fila 1 (columnas 1-35), columna 35 (filas 1-26) y fila 26 (columnas 3-35),
# agujeros unidos con estaño o alambre desnudo
BUS_GND = [(c, 1) for c in range(1, 35)] + [(35, r) for r in range(1, 27)] + [(c, 26) for c in range(34, 2, -1)]
ESQUINAS_BUS = [(1, 1), (35, 1), (35, 26), (3, 26)]

REDES = {
    # nombre: (color, [pines])
    "5V": ("#e67e22", ["J1.5V", "ESP32.A.VIN", "J2.VCC", "C4.+", "J5.VCC"]),
    "GND": ("#111111", ["J1.GND", "J2.GND", "J3.GND", "J4.GND", "J5.GND", "ESP32.A.GND", "R2.2", "R4.2",
                        "R6.2", "C1.2", "C2.2", "C3.2", "C4.-"]),
    "TRIG": ("#1f77b4", ["J2.TRIG", "ESP32.A.D26"]),
    "ECHO_5V": ("#8c564b", ["J2.ECHO", "R1.1"]),
    "ECHO_3V3": ("#17becf", ["R1.2", "R2.1", "ESP32.A.D34"]),
    "SERVO_GPIO": ("#9467bd", ["ESP32.A.D25", "R3.2", "R4.1"]),
    "SERVO_SIG": ("#d62728", ["R3.1", "J3.SIG"]),
    "VBAT_S": ("#2ca02c", ["J4.VBAT", "C1.1", "ESP32.A.D35"]),
    "V6_S": ("#7f7f00", ["J4.V6", "C2.1", "ESP32.A.D32"]),
    "VPAN_S": ("#bcbd22", ["J4.VPAN", "C3.1", "ESP32.A.D33"]),
    "TRIG2": ("#3949ab", ["J5.TRIG", "ESP32.B.D19"]),
    "ECHO2_5V": ("#a0522d", ["J5.ECHO", "R5.1"]),
    "ECHO2_3V3": ("#00897b", ["R5.2", "R6.1", "ESP32.B.D21"]),
}

R_ECHO = (1000.0, 2000.0)      # R1 serie, R2 a GND  (y R5 serie, R6 a GND en el ECHO de la tolva)


def agujero(ref):
    comp, pin = ref.split(".", 1)
    return COMP[comp]["pines"][pin]


def ocupados_ajenos(red=None):
    """Todos los agujeros con pin o bus (un cable solo puede tocarlos en sus extremos)."""
    return {h for c in COMP.values() for h in c["pines"].values()} | set(BUS_GND)


def distancia_segmento(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx - p[0], ay + t * dy - p[1])


def despejado(ruta, ocupados, minimo=0.4):
    """La ruta no pasa sobre agujeros ocupados salvo en sus dos extremos."""
    extremos = {ruta[0], ruta[-1]}
    for a, b in zip(ruta, ruta[1:]):
        for h in ocupados - extremos:
            if distancia_segmento(h, a, b) < minimo:
                return False
    return True


def cables_de_red(nombre, refs):
    """Señales: rutas fijas de RUTAS. GND: cada pin al agujero libre más cercano del bus
    con un cable recto despejado."""
    if nombre != "GND":
        return [list(r) for r in RUTAS[nombre]]
    ocupados = ocupados_ajenos()
    cables, usados = [], set()
    for p in (agujero(r) for r in refs):
        # primero cables rectos horizontales o verticales; si no hay, en diagonal
        orden = sorted(BUS_GND, key=lambda q: (q[0] != p[0] and q[1] != p[1], math.dist(q, p), q))
        for b in orden:
            if b not in usados and despejado([p, b], ocupados):
                usados.add(b)
                cables.append([p, b])
                break
        else:
            raise SystemExit(f"GND: no hay camino despejado al bus desde {p}")
    return cables


def leer_config():
    txt = (RAIZ / "ESP32/Dispensador_ESP32/config.h").read_text(encoding="utf-8")
    return {k: int(v) for k, v in re.findall(r"#define\s+(PIN_\w+)\s+(\d+)", txt)}


def verificar(cables):
    errores = []
    # 1) un agujero = una sola red
    duenio = {}
    for red, (_, refs) in REDES.items():
        for r in refs:
            h = agujero(r)
            if duenio.get(h, red) != red:
                errores.append(f"agujero {h} compartido por {duenio[h]} y {red}")
            duenio[h] = red
    for h in BUS_GND:
        if duenio.get(h, "GND") != "GND":
            errores.append(f"el bus GND pisa {h} de {duenio[h]}")
    todos = [h for c in COMP.values() for h in c["pines"].values()]
    if len(todos) != len(set(todos)):
        errores.append("dos pines de componentes en el mismo agujero")
    # 2) conectividad de cada red con los cables generados (unión-búsqueda)
    padre = {}

    def raiz(x):
        while padre.setdefault(x, x) != x:
            x = padre[x]
        return x

    pines_red = {red: {agujero(r) for r in refs} for red, (_, refs) in REDES.items()}
    for red, lista in cables.items():
        for ruta in lista:
            padre[raiz((red, ruta[0]))] = raiz((red, ruta[-1]))
            for extremo in (ruta[0], ruta[-1]):
                if extremo not in pines_red[red] and not (red == "GND" and extremo in BUS_GND):
                    errores.append(f"{red}: el cable termina en {extremo}, que no es un pin de la red")
    for i in range(len(BUS_GND) - 1):
        padre[raiz(("GND", BUS_GND[i]))] = raiz(("GND", BUS_GND[i + 1]))
    for red, (_, refs) in REDES.items():
        grupos = {raiz((red, agujero(r))) for r in refs}
        if len(grupos) != 1:
            errores.append(f"la red {red} no queda unida ({len(grupos)} trozos)")
    # 3) coherencia con config.h
    pines = leer_config()
    esperado = {"TRIG": pines["PIN_TRIG"], "ECHO_3V3": pines["PIN_ECHO"], "SERVO_GPIO": pines["PIN_SERVO"],
                "VBAT_S": pines["PIN_VBAT"], "V6_S": pines["PIN_VSERVO"], "VPAN_S": pines["PIN_VPANEL"],
                "TRIG2": pines["PIN_TRIG_NIVEL"], "ECHO2_3V3": pines["PIN_ECHO_NIVEL"]}
    for red, gpio in esperado.items():
        if not {f"ESP32.A.D{gpio}", f"ESP32.B.D{gpio}"} & set(REDES[red][1]):
            errores.append(f"{red}: config.h usa GPIO{gpio} pero la placa no lo conecta")
    # 4) pines prohibidos
    for red, (_, refs) in REDES.items():
        for r in refs:
            if r.startswith("ESP32.") and r.split(".")[-1] in PROHIBIDOS:
                errores.append(f"{red} usa el pin prohibido {r}")
    # 5) ningún cable pasa por encima de agujeros de otra red
    ocupados = ocupados_ajenos()
    for red, lista in cables.items():
        for ruta in lista:
            if not despejado(ruta, ocupados):
                errores.append(f"el cable {ruta} de {red} pasa sobre otro agujero ocupado")
    # 6) divisor del ECHO
    v = 5.1 * R_ECHO[1] / sum(R_ECHO)
    if v > 3.4:
        errores.append(f"divisor ECHO deja {v:.2f} V (> 3,4 V)")
    return errores


def xy(h):
    return MARGEN + (h[0] - 1) * PASO, MARGEN + (h[1] - 1) * PASO


def svg(cables):
    W = MARGEN * 2 + (COLS - 1) * PASO + 330
    H = MARGEN * 2 + (FILAS - 1) * PASO + 40
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         'font-family="Arial, Helvetica, sans-serif" font-size="11">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{MARGEN}" y="28" font-size="18" font-weight="bold">Placa de control · placa perforada 90×70 mm '
         '(vista desde el lado de los componentes)</text>']
    x0, y0 = xy((1, 1))
    x1, y1 = xy((COLS, FILAS))
    o.append(f'<rect x="{x0 - 14}" y="{y0 - 14}" width="{x1 - x0 + 28}" height="{y1 - y0 + 28}" rx="8" '
             'fill="#e8f3e6" stroke="#5d8a58" stroke-width="2"/>')
    for c in range(1, COLS + 1):
        for r in range(1, FILAS + 1):
            x, y = xy((c, r))
            o.append(f'<circle cx="{x}" cy="{y}" r="2.6" fill="#b9c7b4"/>')
    for c in range(1, COLS + 1, 2):
        x, _ = xy((c, 1))
        o.append(f'<text x="{x}" y="{y0 - 20}" text-anchor="middle" font-size="9" fill="#666">{c}</text>')
    for r in range(1, FILAS + 1, 2):
        _, y = xy((1, r))
        o.append(f'<text x="{x0 - 22}" y="{y + 3}" text-anchor="end" font-size="9" fill="#666">{r}</text>')
    # bus GND
    pts = " ".join("{},{}".format(*xy(h)) for h in ESQUINAS_BUS)
    o.append(f'<polyline points="{pts}" fill="none" stroke="#111" stroke-width="6" stroke-linecap="round" '
             'stroke-linejoin="round"/>')
    bx0, by = xy(BUS_GND[-1])
    o.append(f'<text x="{bx0}" y="{by + 22}" font-size="11">BUS GND en U: fila 1, columna 35 y fila 26 unidas con '
             'estaño o alambre desnudo</text>')
    # ESP32
    ex0, ey0 = xy((2, 7))
    ex1, ey1 = xy((19, 19))
    o.append(f'<rect x="{ex0}" y="{ey0}" width="{ex1 - ex0}" height="{ey1 - ey0}" rx="6" fill="#2c3e50" opacity="0.12" '
             'stroke="#2c3e50" stroke-width="2" stroke-dasharray="6 3"/>')
    o.append(f'<text x="{(ex0 + ex1) / 2}" y="{(ey0 + ey1) / 2 - 6}" text-anchor="middle" font-size="15" '
             'font-weight="bold" fill="#2c3e50">ESP32 DevKit V1 (30 pines)</text>')
    o.append(f'<text x="{(ex0 + ex1) / 2}" y="{(ey0 + ey1) / 2 + 12}" text-anchor="middle" fill="#2c3e50">'
             'sobre tiras de pines hembra · USB hacia la derecha →</text>')
    for pin, h in COMP["ESP32"]["pines"].items():
        x, y = xy(h)
        usado = any(f"ESP32.{pin}" in refs for _, refs in REDES.values())
        o.append(f'<rect x="{x - 5}" y="{y - 5}" width="10" height="10" fill="{"#f1c40f" if usado else "#d5d8dc"}" '
                 'stroke="#7d6608"/>')
        dy = 18 if pin.startswith("A.") else -10
        o.append(f'<text x="{x}" y="{y + dy}" text-anchor="middle" font-size="8.5" '
                 f'transform="rotate(-60 {x} {y + dy})">{pin[2:]}</text>')
    # componentes
    for nombre, c in COMP.items():
        if nombre == "ESP32":
            continue
        hs = list(c["pines"].values())
        xs = [xy(h)[0] for h in hs]
        ys = [xy(h)[1] for h in hs]
        if c["tipo"] == "conector" and len(set(ys)) == 1:          # horizontal (J5)
            o.append(f'<rect x="{min(xs) - 10}" y="{ys[0] - 9}" width="{max(xs) - min(xs) + 20}" height="18" '
                     'fill="#fdebd0" stroke="#7e5109" stroke-width="1.5"/>')
            for pin, h in c["pines"].items():
                x, y = xy(h)
                o.append(f'<text x="{x}" y="{y - 11}" text-anchor="middle" font-size="8" font-weight="bold">{pin}</text>')
            tx, ty = xy((10, 4))
            o.append(f'<text x="{tx}" y="{ty}" font-weight="bold">{c["texto"]}</text>'
                     f'<text x="{tx}" y="{ty + 14}">HC-SR04 de la tapa de la tolva</text>'
                     f'<text x="{tx}" y="{ty + 28}">← GND · ECHO · TRIG · VCC</text>')
        elif c["tipo"] == "conector":
            o.append(f'<rect x="{min(xs) - 9}" y="{min(ys) - 10}" width="18" height="{max(ys) - min(ys) + 20}" '
                     'fill="#fdebd0" stroke="#7e5109" stroke-width="1.5"/>')
            for pin, h in c["pines"].items():
                x, y = xy(h)
                o.append(f'<text x="{x + 14}" y="{y + 4}">{pin}</text>')
            o.append(f'<text x="{xy((35, 1))[0] + 16}" y="{(min(ys) + max(ys)) / 2 + 4}" font-weight="bold">'
                     f'{c["texto"]}</text>')
        else:
            (xa, ya), (xb, yb) = [xy(h) for h in hs]
            ancho = 9 if c["tipo"] != "elec" else 14
            vert = xa == xb
            rx0, rx1 = (min(xa, xb) + 8, max(xa, xb) - 8) if not vert else (xa - ancho / 2, xa + ancho / 2)
            ry0, ry1 = (ya - ancho / 2, ya + ancho / 2) if not vert else (min(ya, yb) + 8, max(ya, yb) - 8)
            relleno = {"res": "#f5cba7", "cap": "#aed6f1", "elec": "#5d6d7e"}[c["tipo"]]
            o.append(f'<rect x="{rx0}" y="{ry0}" width="{rx1 - rx0}" height="{ry1 - ry0}" rx="3" fill="{relleno}" '
                     'stroke="#333"/>')
            tx, ty = ((rx0 + rx1) / 2, ry0 - 4) if not vert else (rx1 + 4, (ry0 + ry1) / 2 + 4)
            ancla = "middle" if not vert else "start"
            if c.get("rotulo") == "izquierda":
                tx, ancla = rx0 - 4, "end"
            o.append(f'<text x="{tx}" y="{ty}" text-anchor="{ancla}" font-weight="bold">{c["texto"]}</text>')
            if c["tipo"] == "elec":
                x, y = xy(c["pines"]["+"])
                o.append(f'<text x="{x - 12}" y="{y + 4}" font-weight="bold">+</text>')
            for h in hs:
                x, y = xy(h)
                o.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#bbb" stroke="#333"/>')
        for h in hs:
            x, y = xy(h)
            o.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#7d6608"/>')
    # cables numerados
    n = 0
    for red, lista in cables.items():
        color = REDES[red][0]
        for ruta in lista:
            n += 1
            pts = " ".join("{},{}".format(*xy(h)) for h in ruta)
            o.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3" '
                     'stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>')
            a, b = max(zip(ruta, ruta[1:]), key=lambda ab: math.dist(*ab))
            (xa, ya), (xb, yb) = xy(a), xy(b)
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            if math.dist(a, b) <= 1:          # cable de un paso: el número va al costado, no encima de los pines
                mx, my = (mx - 18, my) if xa == xb else (mx, my - 13)
            o.append(f'<circle cx="{mx}" cy="{my}" r="8" fill="#fff" stroke="{color}" stroke-width="1.5"/>'
                     f'<text x="{mx}" y="{my + 3.5}" text-anchor="middle" font-size="9" font-weight="bold">{n}</text>')
    # leyenda
    lx = x1 + 140
    ly = y0 + 10
    o.append(f'<text x="{lx}" y="{ly}" font-weight="bold" font-size="13">Redes</text>')
    for i, (red, (color, _)) in enumerate(REDES.items()):
        yy = ly + 22 + i * 20
        o.append(f'<line x1="{lx}" y1="{yy - 4}" x2="{lx + 26}" y2="{yy - 4}" stroke="{color}" stroke-width="4"/>'
                 f'<text x="{lx + 34}" y="{yy}">{red}</text>')
    notas = ["Cables: aislados, por el lado", "de componentes. Un cruce de", "líneas NO es una unión.",
             "", "Los números remiten a la", "lista de cables", "(placa_control.md).", "",
             "El servo se alimenta del", "Buck A (6 V) directamente:", "por esta placa solo pasa", "su SEÑAL."]
    for i, t in enumerate(notas):
        o.append(f'<text x="{lx}" y="{ly + 22 + len(REDES) * 20 + 30 + i * 16}" font-size="11">{t}</text>')
    o.append("</svg>")
    return "\n".join(o)


def markdown(cables):
    filas = ["# Placa de control — lista de cables", "",
             "Generada por `generar_placa_control.py` (no editar a mano). Coordenadas (columna, fila) desde la",
             "esquina superior izquierda, vista desde el lado de los componentes. Ver `placa_control.svg`.", "",
             "## Componentes", "", "| Ref. | Valor / función | Agujeros |", "|---|---|---|"]
    for nombre, c in COMP.items():
        if nombre == "ESP32":
            filas.append("| ESP32 | DevKit V1 30 pines sobre 2 tiras hembra de 15 | fila A (EN…VIN): (3,18)…(17,18); "
                         "fila B (D23…3V3): (3,8)…(17,8) |")
            continue
        pines = ", ".join(f"{p} {h}" for p, h in c["pines"].items())
        filas.append(f"| {nombre} | {c.get('texto', '')} | {pines} |")
    filas += ["", "Bus GND en U: agujeros (1,1) a (35,1), (35,1) a (35,26) y (3,26) a (35,26) unidos con estaño o "
              "alambre desnudo.", "",
              "## Cables (soldar uno por uno y tachar)", "", "| N.º | Red | Desde | Hasta | Recorrido (dobleces) |",
              "|---|---|---|---|---|"]
    inverso = {h: f"{c}.{p}" for c, d in COMP.items() for p, h in d["pines"].items()}
    n = 0
    for red, lista in cables.items():
        for ruta in lista:
            n += 1
            a, b = ruta[0], ruta[-1]
            da = inverso.get(a, "bus GND")
            db = inverso.get(b, "bus GND")
            via = " → ".join(str(h) for h in ruta[1:-1])
            filas.append(f"| {n} | {red} | {da} {a} | {db} {b} | {via or '(recto)'} |")
    filas += ["", "## Arnés de cables de la torre", "",
              "Longitudes estimadas sobre el modelo 3D (recorrido por los pasos del piso y del tabique) con ~30 % de",
              "holgura; cortar un poco más largo y ajustar al montar. Conectores entre módulos recomendados: JST-XH",
              "(señal) y XT30 o JST-VH (potencia), para poder separar los módulos sin desoldar.", "",
              "| Cable | Desde | Hasta | Conductores | Sección | Longitud aprox. |", "|---|---|---|---|---|---|",
              "| J1 | Bus 5 V del cajón (Buck B) | J1 de la placa de control | 5V, GND | AWG 22 | 25 cm |",
              "| J4 | Divisores del cajón | J4 de la placa de control | VBAT, V6, VPAN, GND | AWG 24–26 | 25 cm |",
              "| J2 | J2 de la placa | HC-SR04 de presencia (cápsula 03, paso izquierdo del tabique) | VCC, TRIG, ECHO, GND | AWG 24–26 | 30 cm |",
              "| J5 | J5 de la placa | HC-SR04 de nivel (cápsula 13b en la tapa): ranura de la tapa → conducto de la esquina trasera izquierda (07, 08d) → bahía trasera de 02 | VCC, TRIG, ECHO, GND (cable de 4 hilos, mejor apantallado) | AWG 24–26 | 120 cm (incluye 20 cm flojos para levantar la tapa) |",
              "| J3 | J3 de la placa | Cables naranja (señal) y marrón (GND) del MG995 | SIG, GND | AWG 24 | 20 cm (el cable del MG995 suele alcanzar) |",
              "| Servo 6 V | Buck A del cajón (+ C1 1000–2200 µF junto al servo) | Cable rojo (+) y marrón (−) del MG995 | 6V, GND | **AWG 20** | 40 cm |",
              "| Cámara | Bus 5 V del cajón | ESP32-CAM (cápsula 04, paso derecho del tabique; 470 µF + 100 nF en la cápsula) | 5V, GND | AWG 22 | 45 cm |",
              "| Panel | Panel solar en la estación remota (12a/12b) | Conector GX12 de 2 pines en la tapa del cajón 16 → elevador MT3608 y divisor del panel | +, − | AWG 20–22 (bipolar, exterior) | 3–5 m según dónde haya sol (medir) |",
              "", "## Conectores de la placa", "",
              "| Conector | Pin | Va a |", "|---|---|---|",
              "| J1 | 5V / GND | Bus de 5 V del cajón de energía (Buck B) |",
              "| J2 | VCC / TRIG / ECHO / GND | HC-SR04 (cápsula 03) |",
              "| J3 | SIG / GND | Cable naranja y marrón del MG995 (el rojo va al Buck A de 6 V, NO a esta placa) |",
              "| J4 | VBAT / V6 / VPAN / GND | Salidas de los divisores 100k/33k, 100k/33k y 100k/100k montados en el cajón |",
              "| J5 | GND / ECHO / TRIG / VCC (de izquierda a derecha) | HC-SR04 de nivel en la tapa de la tolva (el mismo cable de 4 hilos, girado 180°) |",
              "", "Antes de colocar el ESP32: con el multímetro, comprobar que no hay continuidad entre 5V y GND",
              "ni entre las redes ECHO_5V / ECHO2_5V y el ESP32; con J1 alimentado y los HC-SR04 conectados, medir",
              "≤ 3,4 V en los agujeros de D34 y D21 al disparar (comandos serie DIST y NIVEL)."]
    return "\n".join(filas) + "\n"


def main():
    cables = {red: cables_de_red(red, refs) for red, (_, refs) in REDES.items()}
    errores = verificar(cables)
    total = sum(len(v) for v in cables.values())
    (SALIDA / "placa_control.svg").write_text(svg(cables), encoding="utf-8")
    (SALIDA / "placa_control.md").write_text(markdown(cables), encoding="utf-8")
    print(f"{len(COMP)} componentes, {len(REDES)} redes, {total} cables")
    for e in errores:
        print("ERROR:", e)
    print("VERIFICACIÓN:", "OK" if not errores else f"{len(errores)} error(es)")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
