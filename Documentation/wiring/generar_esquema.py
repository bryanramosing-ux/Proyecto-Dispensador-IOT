"""
Esquema de conexiones COMPLETO del dispensador (todos los componentes).

    python generar_esquema.py      -> esquema_conexiones.svg

Los números de GPIO se leen de ESP32/Dispensador_ESP32/config.h: el dibujo no puede
quedar desactualizado respecto del firmware (el script falla si falta algún pin).

Convenciones: un cruce de líneas SIN punto no es una unión; el "salto" (semicírculo)
marca el único cruce de potencia. Las tierras se dibujan con el símbolo de GND y
todas vuelven al punto estrella del cajón (P− del BMS).
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).resolve().parent / "esquema_conexiones.svg"
ANCHO, ALTO = 2000, 1500

ESTILOS = """
    .blk{fill:#f7f9fc;stroke:#34495e;stroke-width:2}
    .aux{fill:#fff8e6;stroke:#b9770e;stroke-width:2;stroke-dasharray:6 3}
    .per{fill:#eef6ff;stroke:#1f4e79;stroke-width:2}
    .red{fill:#f4f6f6;stroke:#566573;stroke-width:2}
    .zona{fill:none;stroke-width:2;stroke-dasharray:9 5}
    .t{font-weight:bold;font-size:15px}
    .s{font-size:12px;fill:#444}
    .pin{font-size:12px;font-family:monospace}
    .vbat{stroke:#8e44ad;stroke-width:3;fill:none}
    .v6{stroke:#d62728;stroke-width:3;fill:none}
    .v5{stroke:#ff7f0e;stroke-width:3;fill:none}
    .gnd{stroke:#000;stroke-width:2.5;fill:none}
    .sig{stroke:#1f77b4;stroke-width:2;fill:none}
    .echo5{stroke:#8c564b;stroke-width:2;fill:none}
    .echo3{stroke:#17becf;stroke-width:2;fill:none}
    .adc{stroke:#2ca02c;stroke-width:2;fill:none}
    .pv{stroke:#b9770e;stroke-width:3;fill:none}
    .wifi{stroke:#7f8c8d;stroke-width:2;stroke-dasharray:7 5;fill:none}
    .res{fill:#fff;stroke:#000;stroke-width:1.5}
"""


def leer_pines():
    txt = (RAIZ / "ESP32/Dispensador_ESP32/config.h").read_text(encoding="utf-8")
    pines = {k: int(v) for k, v in re.findall(r"#define\s+(PIN_\w+)\s+(\d+)", txt)}
    faltan = {"PIN_TRIG", "PIN_ECHO", "PIN_SERVO", "PIN_VBAT", "PIN_VSERVO", "PIN_VPANEL",
              "PIN_TRIG_NIVEL", "PIN_ECHO_NIVEL", "PIN_LED", "PIN_BOTON"} - set(pines)
    if faltan:
        raise SystemExit(f"config.h no define {sorted(faltan)}")
    return pines


class Dibujo:
    def __init__(self):
        self.o = []

    def add(self, s):
        self.o.append(s)

    def texto(self, x, y, t, cls="s", anchor="start", **kw):
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
        self.add(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}" {extra}>{t}</text>')

    def bloque(self, x, y, w, h, titulo, lineas=(), cls="blk"):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" class="{cls}"/>')
        self.texto(x + w / 2, y + 20, titulo, "t", "middle")
        for i, linea in enumerate(lineas):
            self.texto(x + w / 2, y + 38 + i * 16, linea, "s", "middle")

    def zona(self, x, y, w, h, titulo, color, dx=12):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="zona" stroke="{color}"/>')
        self.texto(x + dx, y + 20, titulo, "t", fill=color)

    def linea(self, pts, cls, flecha=False, saltos=()):
        """Polilínea ortogonal. 'saltos' = puntos (x, y) sobre tramos HORIZONTALES donde la
        línea salta por encima de otra (cruce sin unión)."""
        d = f"M{pts[0][0]},{pts[0][1]}"
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            for sx, sy in sorted(saltos, key=lambda p: p[0] * (1 if x1 >= x0 else -1)):
                if y0 == y1 == sy and min(x0, x1) < sx < max(x0, x1):
                    s = 7 if x1 > x0 else -7
                    d += f" L{sx - s},{sy} A7,7 0 0 {1 if s > 0 else 0} {sx + s},{sy}"
            d += f" L{x1},{y1}"
        m = ' marker-end="url(#flecha)"' if flecha else ""
        self.add(f'<path d="{d}" class="{cls}"{m}/>')

    def punto(self, x, y):
        self.add(f'<circle cx="{x}" cy="{y}" r="4.5" fill="#000"/>')

    def tierra(self, x, y):
        self.add(f'<use href="#gnd" x="{x}" y="{y}"/>')

    def resistencia(self, x0, y0, x1, y1, etiqueta, lado=1):
        """Resistencia centrada entre dos puntos alineados (horizontal o vertical)."""
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if y0 == y1:
            self.add(f'<rect x="{cx - 18}" y="{cy - 6}" width="36" height="12" class="res"/>')
            self.texto(cx, cy - 10 if lado > 0 else cy + 22, etiqueta, "s", "middle")
        else:
            self.add(f'<rect x="{cx - 6}" y="{cy - 18}" width="12" height="36" class="res"/>')
            self.texto(cx + 10 if lado > 0 else cx - 10, cy + 4, etiqueta, "s", "start" if lado > 0 else "end")

    def condensador(self, x, y, etiqueta, polar=False):
        """Condensador vertical: placa superior en y, a GND por debajo."""
        self.add(f'<line x1="{x - 11}" y1="{y}" x2="{x + 11}" y2="{y}" stroke="#000" stroke-width="2.5"/>')
        if polar:
            self.add(f'<path d="M{x - 11},{y + 9} Q{x},{y + 4} {x + 11},{y + 9}" stroke="#000" '
                     'stroke-width="2.5" fill="none"/>')
            self.texto(x - 15, y - 2, "+", "s", "end")
        else:
            self.add(f'<line x1="{x - 11}" y1="{y + 7}" x2="{x + 11}" y2="{y + 7}" stroke="#000" stroke-width="2.5"/>')
        self.add(f'<line x1="{x}" y1="{y + 8}" x2="{x}" y2="{y + 20}" class="gnd"/>')
        self.tierra(x, y + 20)
        self.texto(x + 15, y + 12, etiqueta, "s")

    def svg(self):
        cab = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" width="{ANCHO}" '
               f'height="{ALTO}" font-family="Arial, Helvetica, sans-serif" font-size="13">\n'
               '<title>Esquema de conexiones completo - Dispensador IoT</title>\n<defs>\n'
               '<marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
               'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker>\n'
               '<g id="gnd"><line x1="-10" y1="0" x2="10" y2="0" stroke="#000" stroke-width="2"/>'
               '<line x1="-6" y1="5" x2="6" y2="5" stroke="#000" stroke-width="2"/>'
               '<line x1="-2" y1="10" x2="2" y2="10" stroke="#000" stroke-width="2"/></g>\n'
               f'</defs>\n<style>{ESTILOS}</style>\n<rect width="{ANCHO}" height="{ALTO}" fill="#fff"/>\n')
        return cab + "\n".join(self.o) + "\n</svg>\n"


def dibujar(p):
    d = Dibujo()
    g = lambda n: f"GPIO{p[n]}"  # noqa: E731
    d.texto(ANCHO / 2, 32, "Dispensador IoT · Esquema de conexiones completo (v2)", "t", "middle", font_size="22")
    d.texto(ANCHO / 2, 56, "Líneas: ámbar = panel solar · morado = batería 2S (6,0–8,4 V) · rojo = 6,0 V servo · "
            "naranja = 5,0 V lógica · negro = GND · azul = señal 3,3 V · marrón = ECHO 5 V · celeste = ECHO "
            "dividido (≤3,4 V) · verde = medición ADC · gris punteado = Wi-Fi", "s", "middle")

    # ------------------------------------------------------------------ RED
    d.bloque(760, 85, 230, 80, "Router / hotspot", ["Wi-Fi 2,4 GHz WPA2", "IP fijas 192.168.1.50–52"], "red")
    d.bloque(1080, 78, 430, 112, "PC / notebook · 192.168.1.50:8000",
             ["servidor_vision.py (Python + OpenCV + MobileNetV2)",
              "GET /classify → {\"clase\": 0 | 1 | 2}   (1 = PERRO, 2 = GATO)",
              "POST /alerta ← nivel de la tolva · GET / = panel web"], "red")
    d.bloque(1600, 85, 360, 80, "Celular (opcional)", ["app ntfy: «La comida del dispensador", "se está acabando (nivel ~18 %)»"], "red")
    d.linea([(990, 125), (1080, 125)], "wifi")
    d.linea([(1510, 125), (1600, 125)], "wifi")
    d.texto(1555, 116, "Internet", "s", "middle")
    d.texto(1555, 145, "ntfy.sh", "s", "middle")

    # ------------------------------------------------------- ESTACIÓN SOLAR
    d.zona(20, 75, 600, 175, "ESTACIÓN SOLAR REMOTA (piezas 12a + 12b) · donde haya sol", "#b9770e")
    d.bloque(400, 110, 200, 85, "PANEL SOLAR", ["≈3 V · 100 mA · ≈0,3 W", "(medir Voc e Isc)"], "aux")
    d.bloque(170, 110, 200, 85, "Conector GX12 macho", ["2 pines: 1 = + (rojo)", "2 = − (negro)"], "aux")
    d.linea([(400, 135), (370, 135)], "pv")
    d.linea([(400, 170), (370, 170)], "gnd")
    d.texto(310, 215, "cable bipolar exterior 3–5 m (AWG 20–22) →", "s")
    d.texto(310, 231, "se enchufa en la tapa trasera del cajón", "s")
    d.texto(40, 140, "Inclinación ≈ latitud", "s")
    d.texto(40, 156, "(mín. 10–15°), hacia", "s")
    d.texto(40, 172, "el ecuador; M4 fija", "s")
    d.texto(40, 188, "el ángulo (0–75°)", "s")

    # ------------------------------------------------------- CAJÓN DE ENERGÍA
    d.zona(20, 262, 640, 878, "CAJÓN DE ENERGÍA (pieza 16, en la base 01)", "#27ae60", dx=300)
    d.linea([(250, 195), (250, 290)], "pv", flecha=True)
    d.linea([(290, 195), (290, 290)], "gnd")
    d.bloque(170, 290, 200, 55, "GX12 hembra", ["tapa trasera · 1 = + · 2 = −"], "aux")
    d.linea([(270, 345), (270, 380)], "pv", flecha=True)
    d.bloque(170, 380, 200, 50, "D1 Schottky 1N5817", ["anti-retorno del panel"], "aux")
    d.linea([(270, 430), (270, 465)], "pv", flecha=True)
    d.bloque(170, 465, 200, 55, "Elevador MT3608", ["ajustar 5,0 V sin carga"], "aux")
    d.linea([(270, 520), (270, 555)], "v5", flecha=True)
    d.bloque(170, 555, 200, 65, "Cargador 2S USB-C", ["entrada 5 V → CC/CV 8,4 V", "(configurado 2 celdas)"], "aux")
    d.bloque(35, 555, 110, 65, "USB-C 5 V", ["cargador de", "pared (principal)"], "aux")
    d.linea([(145, 587), (170, 587)], "v5", flecha=True)
    d.linea([(270, 620), (270, 655)], "vbat", flecha=True)
    d.bloque(170, 655, 200, 65, "BMS 2S con balanceo", ["B+ · BM · B− | P+ · P−", "corte sobrecarga/descarga"], "aux")
    d.bloque(35, 655, 110, 65, "2 × 18650", ["Li-ion en serie", "7,4 V nominal"], "aux")
    for yy in (672, 688, 704):
        d.linea([(145, yy), (170, yy)], "vbat")
    d.linea([(270, 720), (270, 755)], "vbat", flecha=True)
    d.bloque(170, 755, 200, 40, "F1 fusible 4 A (lento)", [], "aux")
    d.linea([(270, 795), (270, 830)], "vbat", flecha=True)
    d.bloque(170, 830, 200, 40, "S1 interruptor general", [], "aux")
    # tronco VBAT
    d.linea([(270, 870), (270, 890), (385, 890)], "vbat")
    d.linea([(385, 405), (385, 1010), (400, 1010)], "vbat")
    d.linea([(385, 405), (400, 405)], "vbat", flecha=True)
    d.linea([(385, 910), (400, 910)], "vbat", flecha=True)
    d.punto(385, 890)
    d.punto(385, 910)
    d.texto(380, 960, "VBAT 6,0–8,4 V", "s", "end", fill="#8e44ad")
    # divisores (V_panel ANTES de D1)
    d.bloque(400, 290, 205, 165, "Divisores de medición", [], "aux")
    d.texto(410, 339, "VBAT 100k/33k: 2,08 V@8,4", "pin", font_size="11")
    d.texto(410, 359, "V6   100k/33k: 1,49 V@6,0", "pin", font_size="11")
    d.texto(410, 379, "VPAN 100k/100k: 2,0 V@4,0", "pin", font_size="11")
    d.texto(410, 402, "VPAN: tomada ANTES de D1", "s")
    d.texto(410, 418, "VBAT ← tronco · V6 ← Buck A", "s")
    d.texto(410, 446, "salidas → J4", "s")
    d.linea([(370, 305), (400, 305)], "pv")
    d.punto(370, 305)
    d.tierra(330, 352)
    d.linea([(330, 345), (330, 352)], "gnd")
    # convertidores
    d.bloque(400, 880, 205, 60, "Buck A → 6,0 V servo", ["≥3 A (XL4015) · solo el MG995"], "aux")
    d.bloque(400, 980, 205, 60, "Buck B → 5,0 V lógica", ["2–3 A · 470 µF a la salida"], "aux")
    # 6 V: al divisor (subida) y al servo (riel inferior)
    d.linea([(605, 910), (645, 910)], "v6")
    d.punto(645, 910)
    d.linea([(645, 910), (645, 440), (605, 440)], "v6", flecha=True)
    d.linea([(645, 910), (645, 1065), (1790, 1065), (1790, 785)], "v6")
    d.texto(655, 1058, "6,0 V servo (NO pasa por la placa de control)", "s", fill="#d62728")
    # 5 V: a J1 y a la ESP32-CAM
    d.linea([(605, 1010), (1405, 1010), (1405, 958)], "v5", flecha=True, saltos=[(645, 1010)])
    d.punto(780, 1010)
    d.linea([(780, 1010), (780, 975)], "v5", flecha=True)
    d.texto(655, 1003, "BUS 5,0 V", "s", fill="#e67e22")
    # punto estrella
    d.bloque(170, 1060, 200, 60, "Punto estrella GND", ["P− del BMS = GND común", "(todas las tierras)"], "aux")
    d.tierra(270, 1125)
    d.texto(40, 1100, "D1, Buck A/B y", "s")
    d.texto(40, 1116, "divisores van a GND", "s")

    # ------------------------------------------------------- PLACA DE CONTROL
    d.zona(700, 285, 560, 690, "PLACA DE CONTROL (bandeja 05)", "#1f4e79", dx=90)
    # J4 (izquierda, arriba) y J1 (abajo)
    d.add('<rect x="702" y="322" width="38" height="86" fill="#fdebd0" stroke="#7e5109"/>')
    d.texto(721, 316, "J4", "t", "middle")
    for t, y in [("VBAT", 335), ("V6", 355), ("VPAN", 375), ("GND", 395)]:
        d.texto(721, y + 3, t, "pin", "middle", font_size="9")
        if t != "GND":
            d.linea([(605, y), (702, y)], "adc")
    d.linea([(702, 395), (680, 395), (680, 405)], "gnd")
    d.tierra(680, 405)
    d.add('<rect x="760" y="941" width="60" height="32" fill="#fdebd0" stroke="#7e5109"/>')
    d.texto(754, 963, "J1", "t", "end")
    d.texto(768, 962, "5V", "pin")
    d.texto(796, 962, "GND", "pin")
    # ESP32
    d.bloque(850, 345, 230, 590, "ESP32 DevKit V1", ["30 pines · lógica 3,3 V"])
    izq = [(f"{g('PIN_VBAT')} VBAT", 420), (f"{g('PIN_VSERVO')} V6", 450), (f"{g('PIN_VPANEL')} VPAN", 480),
           ("VIN (5 V)", 860), ("GND", 900)]
    for t, y in izq:
        d.texto(857, y + 4, t, "pin")
    d.linea([(790, 335), (810, 335), (810, 420), (850, 420)], "adc")
    d.linea([(780, 355), (800, 355), (800, 450), (850, 450)], "adc")
    d.linea([(770, 375), (790, 375), (790, 480), (850, 480)], "adc")
    d.linea([(740, 335), (790, 335)], "adc")
    d.linea([(740, 355), (780, 355)], "adc")
    d.linea([(740, 375), (770, 375)], "adc")
    d.texto(770, 512, "C 100 nF de cada", "s", "middle")
    d.texto(770, 527, "GPIO ADC a GND", "s", "middle")
    d.texto(770, 542, "(ADC1: funciona", "s", "middle")
    d.texto(770, 557, "con Wi-Fi activo)", "s", "middle")
    d.linea([(780, 941), (780, 860), (850, 860)], "v5")
    d.condensador(730, 860, "", polar=True)
    d.texto(706, 900, "C 470 µF", "s")
    d.linea([(730, 860), (780, 860)], "v5")
    d.punto(780, 860)
    d.linea([(810, 941), (810, 900), (850, 900)], "gnd")
    d.linea([(810, 973), (810, 985)], "gnd")
    d.tierra(810, 985)
    der = [(f"{g('PIN_TRIG_NIVEL')} TRIG2", 430), (f"{g('PIN_ECHO_NIVEL')} ECHO2", 470),
           (f"{g('PIN_TRIG')} TRIG", 600), (f"{g('PIN_ECHO')} ECHO*", 640), (f"{g('PIN_SERVO')} PWM", 745)]
    for t, y in der:
        d.texto(1073, y + 4, t, "pin", "end")
    d.texto(965, 790, f"{g('PIN_LED')} = LED de la placa", "s", "middle")
    d.texto(965, 806, f"{g('PIN_BOTON')} = botón BOOT (borrar error)", "s", "middle")
    d.texto(965, 822, f"*{g('PIN_ECHO')}: solo entrada", "s", "middle")
    d.texto(965, 838, "3V3 NO alimenta cargas externas", "s", "middle")

    def conector(nombre, x, y0, pines):
        alto = 24 * len(pines) + 2
        d.add(f'<rect x="{x}" y="{y0 - 13}" width="34" height="{alto}" fill="#fdebd0" stroke="#7e5109"/>')
        d.texto(x + 17, y0 - 18, nombre, "t", "middle")
        for i, t in enumerate(pines):
            d.texto(x + 17, y0 + i * 24 + 3, t, "pin", "middle", font_size="9")
        return [y0 + i * 24 for i in range(len(pines))]

    def sensor_ultrasonico(yv, gpio_trig, gpio_echo, rs, rg):
        """Conector de 4 pines (VCC, TRIG, ECHO, GND) con divisor del ECHO."""
        vcc, trig, echo, gnd = yv
        d.linea([(1080, gpio_trig), (1130, gpio_trig), (1130, trig), (1222, trig)], "sig")
        d.linea([(1222, echo), (1205, echo)], "echo5")
        d.resistencia(1205, echo, 1165, echo, rs)
        d.linea([(1165, echo), (1150, echo), (1150, gpio_echo), (1080, gpio_echo)], "echo3")
        d.linea([(1150, gpio_echo), (1150, gpio_echo + 50)], "echo3")
        d.resistencia(1150, gpio_echo + 2, 1150, gpio_echo + 50, rg, -1)
        d.punto(1150, gpio_echo)
        d.tierra(1150, gpio_echo + 50)
        d.linea([(1222, vcc), (1195, vcc)], "v5")
        d.texto(1192, vcc + 4, "5V", "s", "end", fill="#e67e22")
        d.linea([(1222, gnd), (1205, gnd), (1205, gnd + 8)], "gnd")
        d.tierra(1205, gnd + 8)

    yj5 = conector("J5", 1222, 345, ["VCC", "TRIG", "ECHO", "GND"])
    sensor_ultrasonico(yj5, 430, 470, "R5 1k", "R6 2k")
    yj2 = conector("J2", 1222, 520, ["VCC", "TRIG", "ECHO", "GND"])
    sensor_ultrasonico(yj2, 600, 640, "R1 1k", "R2 2k")
    yj3 = conector("J3", 1222, 715, ["SIG", "GND"])
    d.linea([(1080, 745), (1110, 745)], "sig")
    d.punto(1110, 745)
    d.linea([(1110, 745), (1110, 715), (1145, 715)], "sig")
    d.resistencia(1145, 715, 1205, 715, "R3 330")
    d.linea([(1205, 715), (1222, 715)], "sig")
    d.linea([(1110, 745), (1110, 800)], "sig")
    d.resistencia(1110, 752, 1110, 800, "R4 10k", 1)
    d.tierra(1110, 800)
    d.linea([(1222, 739), (1205, 739), (1205, 750)], "gnd")
    d.tierra(1205, 750)

    # ------------------------------------------------------------ PERIFÉRICOS
    def periferico(y0, alto, titulo, sub, pines, ys, cls_lineas):
        d.add(f'<rect x="1330" y="{y0}" width="430" height="{alto}" rx="6" class="per"/>')
        d.texto(1545, y0 + 20, titulo, "t", "middle")
        for i, t in enumerate(sub):
            d.texto(1455, y0 + 44 + i * 16, t, "s")
        for t, y, c in zip(pines, ys, cls_lineas):
            d.linea([(1256, y), (1330, y)], c)
            d.texto(1337, y + 4, t, "pin")

    periferico(298, 135, "HC-SR04 n.º 2 · NIVEL de la TOLVA",
               ["cápsula 13b colgada de la tapa 13a,", "transductores hacia el alimento;",
                "cable 4 hilos ~120 cm por la ranura", "de la tapa y el conducto de la esquina"],
               ["VCC", "TRIG", "ECHO 5V", "GND"], yj5, ["v5", "sig", "echo5", "gnd"])
    periferico(473, 135, "HC-SR04 n.º 1 · PRESENCIA",
               ["cápsula 03 en el frente de la torre", "(detecta a la mascota);",
                "cable 4 hilos ~30 cm"],
               ["VCC", "TRIG", "ECHO 5V", "GND"], yj2, ["v5", "sig", "echo5", "gnd"])
    periferico(668, 135, "MG995 (180°) · dosificador",
               ["soporte 06 · cable original del servo;", "marrón: a J3 y al GND del Buck A (Y)",
                "rojo: 6,0 V del Buck A (AWG 20)"],
               ["SEÑAL", "GND"], yj3, ["sig", "gnd"])
    d.texto(1753, 789, "V+ rojo", "pin", "end")
    d.linea([(1790, 785), (1760, 785)], "v6", flecha=True)
    d.punto(1790, 785)
    d.linea([(1790, 785), (1850, 785)], "v6")
    d.condensador(1850, 785, "", polar=True)
    d.texto(1850, 830, "1000–2200 µF ≥10 V", "s", "middle")
    d.texto(1850, 846, "junto al servo", "s", "middle")
    d.bloque(1330, 840, 430, 115, "ESP32-CAM AI-Thinker · OV2640",
             ["cápsula 04 · IP 192.168.1.51 · solo Wi-Fi (sin cables de datos)",
              "U0R/U0T/IO0 solo para programar (adaptador ESP32-CAM-MB)"], "per")
    d.texto(1412, 948, "5V", "pin")
    d.texto(1688, 948, "GND", "pin")
    d.linea([(1700, 955), (1700, 985)], "gnd")
    d.tierra(1700, 985)
    d.punto(1405, 990)
    d.linea([(1405, 990), (1450, 990)], "v5")
    d.condensador(1450, 990, "", polar=True)
    d.texto(1468, 1004, "470 µF + 100 nF junto a la cámara", "s")

    # ------------------------------------------------------------------ WI-FI
    d.linea([(1060, 345), (1060, 245), (870, 245), (870, 165)], "wifi")
    d.texto(1068, 268, "ESP32 · 192.168.1.52 (GET /classify, POST /alerta; su /status lo lee el panel web)", "s")
    d.linea([(1760, 900), (1975, 900), (1975, 215), (940, 215), (940, 165)], "wifi")
    d.texto(1968, 600, "ESP32-CAM · Wi-Fi", "s", "end")

    # ----------------------------------------------------------------- NOTAS
    d.add('<rect x="20" y="1165" width="1960" height="320" rx="8" fill="#fdecea" stroke="#c0392b" stroke-width="1.5"/>')
    d.texto(36, 1190, "REGLAS DE SEGURIDAD Y DE MONTAJE", "t", fill="#c0392b")
    reglas = [
        "1) Ajustar Buck A a 6,0 V y Buck B a 5,0 V con multímetro ANTES de conectar cargas; el MT3608 a 5,0 V con el panel al sol o con una fuente de 3 V.",
        "2) El MG995 nunca se alimenta desde un GPIO, desde 3V3 ni desde el VIN del ESP32: su 6 V viene directo del Buck A (cable AWG 20) y solo su SEÑAL pasa por la placa.",
        "3) Los dos ECHO (5 V) llegan al ESP32 únicamente a través de sus divisores: R1/R2 (presencia) y R5/R6 (nivel de la tolva). Nunca conectar un ECHO directo a un GPIO.",
        "4) Todas las tierras se unen (GND común, punto estrella en P− del BMS) para que el PWM, los ECHO y las mediciones ADC tengan la misma referencia.",
        "5) La batería 2S (hasta 8,4 V) nunca se conecta directa al MG995 (máx. 7,2 V) ni a los módulos de 5 V. Fusible F1 lo más cerca posible del BMS.",
        "6) Estación solar remota: respetar la polaridad del GX12 (pin 1 = +); el cable exterior se fija con bridas a la base 12a; conectar/desconectar con S1 apagado.",
        "7) Al programar el ESP32 por USB, desconectar J1 si la placa no tiene diodo entre USB y VIN (depende del clon).",
        "8) El cable del sensor de nivel deja ~20 cm flojos bajo la tapa para poder levantarla y cargar alimento sin tirar de las soldaduras (o usar un conector de 4 pines).",
        "9) Bloques con borde punteado = COMPONENTES AUXILIARES DE ALIMENTACIÓN (no están en la lista de componentes principales, pero son necesarios).",
        "Detalle punto a punto: tabla_conexiones.md · Cableado de la placa perforada: placa_control.svg / placa_control.md · Valores de GPIO tomados de config.h al generar este dibujo.",
    ]
    for i, r in enumerate(reglas):
        d.texto(36, 1216 + i * 26, r, "s", font_size="13")
    return d


def main():
    pines = leer_pines()
    usados = [pines[k] for k in ("PIN_TRIG", "PIN_ECHO", "PIN_SERVO", "PIN_VBAT", "PIN_VSERVO", "PIN_VPANEL",
                                 "PIN_TRIG_NIVEL", "PIN_ECHO_NIVEL")]
    if len(set(usados)) != len(usados):
        raise SystemExit("config.h asigna el mismo GPIO a dos funciones")
    SALIDA.write_text(dibujar(pines).svg(), encoding="utf-8")
    print(f"{SALIDA.name}: GPIO de config.h -> " + ", ".join(f"{k[4:]}={v}" for k, v in sorted(pines.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
