#!/usr/bin/env python3
"""Lamina SVG y lista CSV del montaje de laboratorio con dos HC-SR04.

Biblioteca estandar. Ejecutar desde cualquier carpeta. La comprobacion de redes
detecta cortos logicos del modelo; NO certifica el montaje fisico ni las fuentes.
PNG opcional: inkscape docs/imagenes/protoboard_conexiones.svg \
  --export-type=png --export-filename=docs/imagenes/protoboard_conexiones.png
"""
from __future__ import annotations
import csv
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'imagenes'
WIDTH, HEIGHT = 3600, 3100
COL = dict(usb='#d62839', ext='#b32378', gnd='#202b3b', trig='#168345',
           raw='#b68b00', echo='#007e9a', pwm='#df7610', paper='#f4f7fb',
           ink='#162b45', muted='#52657c', blue='#165dba')
X = {'L+': 1300, 'L-': 1334,
     **dict(zip('abcde', [1390, 1422, 1454, 1486, 1518])),
     **dict(zip('fghij', [1610, 1642, 1674, 1706, 1738])),
     'R-': 1795, 'R+': 1829}

def hole(name):
    m = re.fullmatch(r'(L\+|L-|R\+|R-|[a-j])(\d+)', name)
    if not m or not 1 <= int(m[2]) <= 63:
        raise ValueError(f'Coordenada invalida: {name}')
    return X[m[1]], 510 + 22 * (int(m[2])-1)

P = {
    'DEV.5V': (800,520), 'DEV.GND': (800,600),
    'DEV.GPIO19': (800,680), 'DEV.GPIO21': (800,760),
    'DEV.GPIO26': (800,840), 'DEV.GPIO34': (800,920),
    'DEV.GPIO25': (800,1000),
    'NIV.VCC': (800,1340), 'NIV.TRIG': (800,1410),
    'NIV.ECHO': (800,1480), 'NIV.GND': (800,1550),
    'PRE.VCC': (800,1810), 'PRE.TRIG': (800,1880),
    'PRE.ECHO': (800,1950), 'PRE.GND': (800,2020),
    'F.+': (2880,540), 'F.-': (3250,540),
    'TB+.IN': (2260,650), 'TB+.SERVO': (2180,760), 'TB+.CAM': (2400,760),
    'TB-.IN': (3250,650), 'TB-.SERVO': (3030,760),
    'TB-.CAM': (2940,760), 'TB-.REF': (2700,650),
    'CAM.5V': (2630,1140), 'CAM.GND': (2630,1230),
    'SERVO.V+': (2630,1820), 'SERVO.GND': (2630,1880),
    'SERVO.SIG': (2630,1940),
}

def pt(name):
    return P[name] if name in P else hole(name)

# ID, origen, destino, dominio, codos del recorrido, texto de etiqueta, etiqueta XY.
WIRES = [
 ('W01','DEV.5V','L+5','usb',[(1020,520),(1020,598)],'W01 · +5V_USB',(890,505)),
 ('W02','DEV.GND','L-6','gnd',[(1040,600),(1040,620)],'W02 · GND',(890,590)),
 ('W03','DEV.GPIO19','a8','trig',[(1080,680),(1080,664)],'W03',(1100,642)),
 ('W04','DEV.GPIO21','a12','echo',[(1100,760),(1100,752)],'W04 · ECHO N',(1090,738)),
 ('W05','DEV.GPIO26','a26','trig',[(1120,840),(1120,1060)],'W05',(1105,1024)),
 ('W06','DEV.GPIO34','a30','echo',[(1080,920),(1080,1148)],'W06 · ECHO P',(1100,1133)),
 ('W07','DEV.GPIO25','a48','pwm',[(1160,1000),(1160,1544)],'W07 · PWM',(1180,1526)),
 ('W08','NIV.VCC','L+10','usb',[(880,1340),(880,708)],'W08',(1210,696)),
 ('W09','NIV.TRIG','b8','trig',[(930,1410),(930,664)],'W09',(1205,648)),
 ('W10','NIV.ECHO','a10','raw',[(980,1480),(980,708)],'W10 · ECHO 5 V',(1015,697)),
 ('W11','NIV.GND','L-14','gnd',[(1030,1550),(1030,796)],'W11',(1210,784)),
 ('W12','PRE.VCC','L+28','usb',[(880,1810),(880,1104)],'W12',(1205,1092)),
 ('W13','PRE.TRIG','b26','trig',[(930,1880),(930,1060)],'W13',(1205,1048)),
 ('W14','PRE.ECHO','a28','raw',[(980,1950),(980,1104)],'W14 · ECHO 5 V',(1010,1092)),
 ('W15','PRE.GND','L-36','gnd',[(1030,2020),(1030,1280)],'W15',(1205,1268)),
 ('W16','d16','L-16','gnd',[(1486,860),(1350,860),(1350,840)],'W16',(1380,885)),
 ('W17','d34','L-34','gnd',[(1486,1256),(1350,1256),(1350,1236)],'W17',(1380,1281)),
 ('W18','d56','L-56','gnd',[(1486,1740),(1350,1740),(1350,1720)],'W18',(1380,1765)),
 ('W19','e52','SERVO.SIG','pwm',[(1940,1632),(1940,1940)],'W19 · solo senal',(2050,1927)),
 ('W20','L+31','L+32','usb',[(1280,1170),(1280,1192)],'W20',(1190,1222)),
 ('W21','L-31','L-32','gnd',[(1320,1170),(1320,1192)],'W21',(1240,1255)),
 ('W22','F.+','TB+.IN','ext',[(2880,595),(2260,595)],'W22 · +5V_EXT',(2360,583)),
 ('W23','F.-','TB-.IN','gnd',[],'W23',(3270,610)),
 ('W24','TB+.SERVO','SERVO.V+','ext',[(2180,1820)],'W24 · potencia directa',(2000,1788)),
 ('W25','TB-.SERVO','SERVO.GND','gnd',[(3030,820),(2220,820),(2220,1880)],'W25 · retorno propio',(2235,2070)),
 ('W26','TB+.CAM','CAM.5V','ext',[(2400,1140)],'W26',(2405,1105)),
 ('W27','TB-.CAM','CAM.GND','gnd',[(2940,870),(2440,870),(2440,1230)],'W27',(2445,1270)),
 ('W28','DEV.GND','TB-.REF','gnd',[(850,600),(850,350),(2700,350)],'W28 · GND de referencia: DevKit → estrella',(1420,335)),
]
RESISTORS = [
 ('R1','1 kΩ','b10','b12'), ('R2','2 kΩ','c12','c16'),
 ('R3','1 kΩ','b28','b30'), ('R4','2 kΩ','c30','c34'),
 ('R5','330 Ω','b48','b52'), ('R6','10 kΩ','c52','c56'),
]
CAPS = [
 ('C1','1000–2200 µF / ≥10 V','SERVO.V+','SERVO.GND'),
 ('C2','100 nF','SERVO.V+','SERVO.GND'),
 ('C3','470 µF / ≥10 V','CAM.5V','CAM.GND'),
 ('C4','100 nF','CAM.5V','CAM.GND'),
 ('C5','100 nF','NIV.VCC','NIV.GND'),
 ('C6','100 nF','PRE.VCC','PRE.GND'),
]

def validate():
    """Continudad metalica solamente: NO unir extremos de R ni de C."""
    parent = {}
    def find(v):
        parent.setdefault(v,v)
        if parent[v]!=v: parent[v]=find(parent[v])
        return parent[v]
    def union(a,b): parent[find(a)]=find(b)
    for row in range(1,64):
        for group in ['abcde','fghij']:
            for c in group[1:]: union(f'{group[0]}{row}',f'{c}{row}')
    for rail in ['L+','L-','R+','R-']:
        for start,end in [(1,31),(32,63)]:
            for row in range(start+1,end+1): union(f'{rail}{start}',f'{rail}{row}')
    for ports in [('TB+.IN','TB+.SERVO','TB+.CAM'),
                  ('TB-.IN','TB-.SERVO','TB-.CAM','TB-.REF')]:
        for p in ports[1:]: union(ports[0],p)
    used_holes = {}
    for ident,a,b,domain,*_ in WIRES:
        assert domain in COL
        union(a,b)
        for endpoint in (a,b):
            pt(endpoint)
            if endpoint not in P:
                assert endpoint not in used_holes, (endpoint,ident,used_holes.get(endpoint))
                used_holes[endpoint]=ident
    for ident,value,a,b in RESISTORS:
        assert find(a)!=find(b), f'Resistencia puenteada: {ident}'
        for endpoint in (a,b):
            assert endpoint not in used_holes, (endpoint,ident,used_holes.get(endpoint))
            used_holes[endpoint]=ident
    gnd=['DEV.GND','F.-','NIV.GND','PRE.GND','CAM.GND','SERVO.GND','c16','c34','c56']
    assert len({find(x) for x in gnd})==1, 'GND incompleto'
    positives=['DEV.5V','F.+']
    assert len({find(x) for x in positives+['DEV.GND']})==3, 'Positivos unidos o corto a GND'
    for x in ['NIV.VCC','PRE.VCC']: assert find(x)==find('DEV.5V')
    for x in ['CAM.5V','SERVO.V+']: assert find(x)==find('F.+')
    for source,node in [('NIV.ECHO','DEV.GPIO21'),('PRE.ECHO','DEV.GPIO34')]:
        assert find(source)!=find(node), 'ECHO sin divisor'
        assert find(node) not in {find('DEV.5V'),find('F.+'),find('DEV.GND')}
    by_id={ident:(value,a,b) for ident,value,a,b in RESISTORS}
    for top,bottom,source,node in [('R1','R2','NIV.ECHO','DEV.GPIO21'),
                                   ('R3','R4','PRE.ECHO','DEV.GPIO34')]:
        v1,a,b=by_id[top];v2,c,d=by_id[bottom]
        assert v1=='1 kΩ' and v2=='2 kΩ'
        assert find(a)==find(source) and find(b)==find(node)
        assert find(c)==find(node) and find(d)==find('DEV.GND')
    assert find('DEV.GPIO19')==find('NIV.TRIG')
    assert find('DEV.GPIO26')==find('PRE.TRIG')
    _,a,b=by_id['R5'];_,c,d=by_id['R6']
    assert find(a)==find('DEV.GPIO25') and find(b)==find('SERVO.SIG')
    assert find(c)==find('SERVO.SIG') and find(d)==find('DEV.GND')
    expected={'PIN_TRIG_NIVEL':19,'PIN_ECHO_NIVEL':21,'PIN_TRIG':26,'PIN_ECHO':34,'PIN_SERVO':25}
    config=(ROOT/'ESP32/Dispensador_ESP32/config.h').read_text()
    for macro,pin in expected.items():
        match=re.search(r'^#define\s+'+macro+r'\s+(\d+)',config,re.M)
        assert match and int(match[1])==pin, f'Pinout cambio: revisar {macro}'
    return len(used_holes)

S=[]
def emit(s): S.append(s)
def rect(x,y,w,h,fill,stroke='none',radius=12,sw=2):
    emit(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def text(x,y,s,size=24,fill=None,weight=400,anchor='start'):
    emit(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill or COL["ink"]}">{escape(str(s))}</text>')
def lines(x,y,items,size=24,dy=36,fill=None,weight=400):
    for i,s in enumerate(items): text(x,y+i*dy,s,size,fill,weight)
def path(points,color,width=5,halo=True):
    d=' '.join(('M' if i==0 else 'L')+f'{x},{y}' for i,(x,y) in enumerate(points))
    if halo: emit(f'<path d="{d}" fill="none" stroke="white" stroke-width="{width+5}" stroke-linejoin="round" stroke-linecap="round"/>')
    emit(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')
def dot(x,y,color,r=6): emit(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" stroke="white" stroke-width="1.5"/>')
def circle(x,y,r,fill,stroke='none',sw=2): emit(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def label(x,y,s,color,size=20):
    w=len(s)*size*.56+14
    rect(x-5,y-size,w,size+8,'#ffffff',radius=4)
    text(x,y,s,size,color,600)

def resistor(ident,value,a,b):
    x1,y1=hole(a); x2,y2=hole(b)
    mid=(y1+y2)/2
    path([(x1,y1),(x1,y2)],'#8c806c',4)
    rect(x1-11,mid-17,22,34,'#e7d5a3','#6b6047',4,2)
    bands = {
        '1 kΩ': ['#704020','#111111','#111111','#704020','#704020'],
        '2 kΩ': ['#c22d32','#111111','#111111','#704020','#704020'],
        '330 Ω':['#e77b10','#e77b10','#111111','#111111','#704020'],
        '10 kΩ':['#704020','#111111','#111111','#c22d32','#704020'],
    }
    for yy,color in zip([mid-12,mid-6,mid,mid+6,mid+13],bands[value]):
        path([(x1-9,yy),(x1+9,yy)],color,3,False)
    dot(x1,y1,'#6b6047',5); dot(x2,y2,'#6b6047',5)
    return mid

def capacitor(x,y1,y2,electro=False,positive='ext'):
    color=COL['gnd']; mid=(y1+y2)/2
    path([(x,y1),(x,mid-9)],color,3)
    path([(x,y2),(x,mid+9)],color,3)
    path([(x-13,mid-9),(x+13,mid-9)],color,4)
    path([(x-13,mid+9),(x+13,mid+9)],color,4)
    if electro: text(x-27,mid-13,'+',22,COL['ext'],700)
    dot(x,y1,COL[positive],4); dot(x,y2,COL['gnd'],4)

def sensor(x,y,title,prefix):
    rect(x,y,710,340,'#eaf3fb','#9db6ce',16)
    text(x+24,y+38,title,28,weight=700)
    rect(x+30,y+65,480,165,'#146aa1','#104873',6)
    for cx in [x+150,x+375]:
        circle(cx,y+148,68,'#c1cad2','#eef2f5',5)
        circle(cx,y+148,51,'#647484','#233a51',4)
        circle(cx,y+148,35,'#aab8c3','#dae1e6',3)
        for k in range(-2,3): path([(cx-29,y+148+k*9),(cx+29,y+148+k*9)],'#5c6a78',2,False)
    text(x+202,y+93,'HC-SR04',23,'white',700)
    for p in ['VCC','TRIG','ECHO','GND']:
        px,py=P[prefix+'.'+p]
        text(px-14,py-12,p,24,COL['ink'],600,'end')
        dot(px,py,COL['gnd'],6)
    # Bypass local entre VCC/GND, AVANT les fils traversants.
    vx,vy=P[prefix+'.VCC']; gx,gy=P[prefix+'.GND']
    path([(vx,vy),(x+548,vy)],COL['usb'],3)
    path([(gx,gy),(x+548,gy)],COL['gnd'],3)
    capacitor(x+548,vy,gy,positive='usb')
    text(x+20,y+280,('C5' if prefix=='NIV' else 'C6')+' · 100 nF junto a VCC/GND',21)
    text(x+20,y+312,'Leer VCC / TRIG / ECHO / GND en la placa real',20,COL['muted'])

def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    emit(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">')
    emit('<title>Protoboard detallada: dispensador ESP32 con dos HC-SR04, MG995 y ESP32-CAM</title>')
    emit('<desc>Diagrama de conexiones con coordenadas y dos positivos separados. La corriente del servo circula fuera de la protoboard. Los GND son comunes.</desc>')
    rect(0,0,WIDTH,HEIGHT,COL['paper'],radius=0)
    rect(0,0,WIDTH,170,COL['ink'],radius=0)
    text(65,68,'DISPENSADOR IoT · MONTAJE DETALLADO DE LABORATORIO',46,'white',700)
    text(65,120,'ESP32 DevKit + 2 HC-SR04 + MG995 + ESP32-CAM AI-Thinker  |  vista superior funcional',28,'#cdddeb')
    text(3540,120,'REV. 2026-11-17',23,'#cdddeb',anchor='end')
    lx=65
    for domain,title in [('usb','+5V_USB: solo sensores'),('ext','+5V_EXT: servo + CAM'),('gnd','GND comun'),('trig','TRIG'),('raw','ECHO 5 V'),('echo','ECHO dividido'),('pwm','PWM')]:
        path([(lx,220),(lx+45,220)],COL[domain],7)
        text(lx+60,228,title,23,weight=600)
        lx+=len(title)*14+115
    rect(65,255,3470,60,'#fff0db','#ecbb75')
    text(85,294,'POSITIVOS SEPARADOS · Motor fuera de la protoboard · Cruces sin punto NO conectan · Ubicar GPIO por serigrafia',27,'#8d460e',700)

    # Placas funcionales; no se inventa el orden fisico de las variantes DevKit.
    rect(65,405,750,740,'#e9eff6','#aab8c8',16)
    text(90,447,'ESP32 DevKit V1 · alimentado por USB',29,weight=700)
    rect(95,480,360,550,'#26394b','#101c2c')
    rect(145,560,260,210,'#c9d1d8','#85929e')
    text(275,650,'ESP-WROOM-32',24,anchor='middle',weight=700)
    for i in range(6): path([(160+i*35,520),(160+i*35,550)],'#e0b64a',7,False)
    rect(205,995,130,62,'#a8b3bf','#637381',5)
    path([(270,1057),(270,1120),(110,1120)],'#65788e',12)
    text(110,1090,'USB del PC',23,weight=700)
    for key,title,domain in [('5V','5V / VIN verificado','usb'),('GND','GND','gnd'),
        ('GPIO19','GPIO19 · TRIG nivel','trig'),('GPIO21','GPIO21 · ECHO nivel','echo'),
        ('GPIO26','GPIO26 · TRIG presencia','trig'),('GPIO34','GPIO34 · ECHO presencia','echo'),
        ('GPIO25','GPIO25 · PWM MG995','pwm')]:
        x,y=P['DEV.'+key]
        text(x-15,y+7,title,22,COL[domain],600,'end'); dot(x,y,COL[domain])
    text(90,1185,'Terminales funcionales: NO representan el orden del header.',23,COL['muted'])
    text(90,1220,'No conectar +5V_EXT a VIN / 5V del DevKit.',24,COL['ext'],700)
    sensor(65,1280,'S1 · NIVEL DE TOLVA','NIV')
    sensor(65,1750,'S2 · PRESENCIA','PRE')

    # Matriz 63 filas: a-e comunes por fila; f-j comunes por fila; canal aislante.
    rect(1260,415,615,1580,'#e3e8ee','#aab7c5',15)
    rect(1358,480,194,1435,'#f9fafb','#d2d9e2',4)
    rect(1576,480,194,1435,'#f9fafb','#d2d9e2',4)
    rect(1555,480,19,1435,'#bdc6d0',radius=3)
    text(1568,395,'PROTOBOARD · 63 FILAS',29,weight=700,anchor='middle')
    for name,x in X.items():
        color=COL['usb'] if name=='L+' else COL['gnd'] if name=='L-' else '#a6afb9'
        text(x,463,name.upper(),21,color,700,'middle')
        if len(name)>1:
            for a,b in [(1,31),(32,63)]:
                y1=hole(name+str(a))[1];y2=hole(name+str(b))[1]
                path([(x,y1-9),(x,y2+9)],color,3,False)
    active_rows={8,10,12,16,26,28,30,34,48,52,56}
    for row in range(1,64):
        y=hole('a'+str(row))[1]
        if row in active_rows:
            rect(1366,y-9,180,18,'#dfedf9',radius=3)
        text(1355,y+6,str(row),16,COL['muted'],anchor='end')
        text(1777,y+6,str(row),16,COL['muted'])
        for name,x in X.items(): circle(x,y,4.2,'#6b7785','#9ca8b5',.7)
    text(1390,1950,'a–e: unidos por fila',18,COL['muted'])
    text(1605,1950,'f–j: unidos por fila',18,COL['muted'])
    text(1568,2040,'Rieles L partidos entre 31 / 32: instalar W20 + W21.',22,weight=600,anchor='middle')
    text(1568,2080,'Rieles derechos y matriz f–j: SIN USO.',22,COL['muted'],anchor='middle')
    text(1568,2120,'Confirmar continuidad de TU protoboard antes de copiar.',21,COL['muted'],anchor='middle')

    # Fuente, borneras y dispositivos externos.
    rect(2760,385,700,185,'#e9edf3','#95a6b8')
    text(2790,430,'FUENTE EXTERNA REGULADA',28,weight=700)
    text(2790,472,'5,0 V · 5 A iniciales · verificar consumo real',22)
    text(2880,528,'+',27,COL['ext'],700,'middle'); text(3250,528,'−',27,COL['gnd'],700,'middle')
    rect(2090,650,430,110,'#f8e0ee','#b32378')
    text(2305,695,'TB+  ·  +5V_EXT',25,COL['ext'],700,'middle')
    text(2305,730,'RAMAS INDEPENDIENTES',19,COL['ext'],600,'middle')
    rect(2645,650,735,110,'#e3e9ef','#5e7083')
    text(3012,695,'TB−  ·  ESTRELLA GND',25,weight=700,anchor='middle')
    text(3012,730,'REF DEVKIT  /  CAM  /  SERVO',19,weight=600,anchor='middle')
    rect(2630,1000,810,555,'#e9f0f7','#9eb2c7')
    text(2660,1045,'ESP32-CAM AI-Thinker + OV2640',29,weight=700)
    rect(2830,1090,380,300,'#233246','#0e1d31')
    circle(3020,1215,72,'#0e1724','#9faab4',8)
    circle(3020,1215,48,'#1e4771','#051422',6)
    rect(2890,1330,260,33,'#c28f44','#775b30',2)
    text(2650,1130,'5V',23,COL['ext'],700)
    text(2650,1220,'GND',23,COL['gnd'],700)
    lines(2660,1440,['C3: 470 µF / ≥10 V + C4: 100 nF, junto al modulo.',
                     'Datos por Wi-Fi. Sin GPIO hacia el DevKit.',
                     'UART solo al programar; TX/RX a 3,3 V.'],22,34)
    rect(2630,1720,810,385,'#eef0f4','#a0adbc')
    text(2660,1764,'MG995 · POSICIONAL 180°',30,weight=700)
    rect(2920,1810,330,180,'#343a42','#111924')
    rect(3025,1778,125,45,'#b6bdc6','#727e8d',5)
    text(3085,1915,'MG995',31,'#efce6c',700,'middle')
    for key,title,domain in [('V+','V+ · rojo','ext'),('GND','GND · marron / negro','gnd'),('SIG','SIG · naranja / amarillo','pwm')]:
        x,y=P['SERVO.'+key]; text(x+18,y+7,title,22,COL[domain],600)
    text(2660,2047,'C1: 1000–2200 µF / ≥10 V + C2: 100 nF',23)
    text(2660,2080,'Primera prueba SIN brazo ni disco acoplados.',23,COL['ext'],700)

    # Cableado numerado: color identifica red, punto identifica contacto.
    for ident,a,b,domain,bends,title,xy in WIRES:
        path([pt(a),*bends,pt(b)],COL[domain],7 if ident in {'W22','W23','W24','W25','W26','W27'} else 4)
        dot(*pt(a),COL[domain],5);dot(*pt(b),COL[domain],5)
    # Resistencias encima de cables; patas en agujeros distintos de los jumpers.
    for ident,value,a,b in RESISTORS: resistor(ident,value,a,b)
    # Caps externos sobre los dos conductores de su propia rama.
    for x in [2520,2580]: capacitor(x,1140,1230,x==2520)
    for x in [2520,2580]: capacitor(x,1820,1880,x==2520)
    # Etiquetas en corredores. No cubrir la matriz de agujeros.
    for ident,a,b,domain,bends,title,xy in WIRES:
        if ident not in {'W20','W21','W16','W17','W18'}: label(*xy,title,COL[domain],18)
    for x,y,msg in [(1885,725,'R1 · 1 kΩ · b10 → b12'),
                    (1885,785,'R2 · 2 kΩ · c12 → c16'),
                    (1885,1115,'R3 · 1 kΩ · b28 → b30'),
                    (1885,1175,'R4 · 2 kΩ · c30 → c34'),
                    (1885,1560,'R5 · 330 Ω · b48 → b52'),
                    (1885,1660,'R6 · 10 kΩ · c52 → c56')]:
        label(x,y,msg,COL['ink'],20)
    for xy,s in [((1370,885),'W16 → L−16'),((1370,1285),'W17 → L−34'),((1370,1780),'W18 → L−56')]:
        text(*xy,s,18,COL['gnd'],600)
    text(1284,1218,'W20',15,COL['usb'],700,'end')
    text(1340,1218,'W21',15,COL['gnd'],700)
    for name in ['a12','a30']: dot(*hole(name),COL['echo'],7)
    dot(*hole('e52'),COL['pwm'],7)

    # Explicacion y tablas legibles, vinculadas a CSV y documento.
    rect(65,2200,1100,675,'white','#c7d3df')
    rect(1200,2200,1100,675,'white','#c7d3df')
    rect(2335,2200,1200,675,'white','#c7d3df')
    text(95,2250,'1 · COORDENADAS DE MONTAJE',30,weight=700)
    lines(95,2300,[
        'Cada fila a–e tiene continuidad; no cruza el canal central.',
        'L+ es +5V_USB. L− es GND comun de baja corriente.',
        'Rieles derechos: dejar sin conexion.',
        '',
        'NIVEL: GPIO19 → a8; TRIG → b8; ECHO → a10.',
        'R1 b10–b12; GPIO21 → a12; R2 c12–c16.',
        'GND divisor: d16 → L−16 (W16).',
        '',
        'PRESENCIA: GPIO26 → a26; TRIG → b26;',
        'ECHO → a28; R3 b28–b30; GPIO34 → a30.',
        'R4 c30–c34; GND: d34 → L−34 (W17).',
        '',
        'PWM: GPIO25 → a48; R5 b48–b52;',
        'R6 c52–c56; GND: d56 → L−56 (W18).',
        'Senal servo: e52 → SIG (W19).',
    ],23,36)
    text(1230,2250,'2 · REDES Y PROTECCIONES',30,weight=700)
    lines(1230,2300,[
        'ECHO 5 V → 1 kΩ → nodo GPIO → 2 kΩ → GND.',
        'Dos divisores independientes; nunca ECHO directo.',
        'Vnodo = 5,0 × 2 / (1 + 2) ≈ 3,33 V.',
        '',
        'GPIO25 → 330 Ω → SIG; SIG → 10 kΩ → GND.',
        'El pull-down esta DESPUES de la resistencia serie.',
        'PWM de 50 Hz; confirmar entrada 3,3 V del servo.',
        '',
        'C1 y C3: + al positivo de SU rama; − a GND.',
        'C2/C4/C5/C6: ceramicos de 100 nF sin polaridad.',
        'C5/C6 se montan localmente junto a cada sensor.',
        '',
        'W20: L+31 → L+32; W21: L−31 → L−32.',
        'El diagrama supone rieles partidos: verificar tu placa.',
        'GND comun NO significa aislamiento galvanico.',
    ],23,36)
    text(2365,2250,'3 · ANTES DE ENERGIZAR',30,weight=700)
    lines(2365,2300,[
        '1. Desconectar ambas alimentaciones para cablear.',
        '2. Verificar polaridad y ausencia de cortocircuitos.',
        '3. Medir fuente externa: 5,0 V regulados.',
        '4. Confirmar W28 y todos los retornos GND.',
        '5. No unir +5V_USB con +5V_EXT.',
        '6. Motor por borneras; nunca por la protoboard.',
        '7. Comprobar divisores antes de unirlos al GPIO.',
        '8. Primera carga de firmware sin potencia del servo.',
        '9. Servo sin carga: el arranque envia 1500 µs.',
        '10. Medir tension durante captura y movimiento.',
        '',
        'El monitor de riel y modo automatico estan apagados.',
        'Este dibujo no prueba hardware ni detecta atascos.',
        'No modificar conexiones con fuentes encendidas.',
        'CSV W01–W28 + guia Markdown: fuentes de detalle.',
    ],24,36)
    text(65,2930,'REFERENCIA FUNCIONAL: GPIO segun config.h · positivos separados segun docs/conexiones_usbc.md · validar placas y fuente reales',25,weight=600)
    text(65,2975,'Los terminales de las placas se dibujan por funcion; su posicion fisica depende de la variante. No contar pines en esta ilustracion.',25,COL['muted'])
    text(65,3020,'Archivo vectorial ampliable: protoboard_conexiones.svg  |  Lista: docs/protoboard_conexiones.csv  |  Guia: docs/guia_ensamblaje_protoboard.md',23,COL['muted'])
    emit('</svg>')
    (OUT/'protoboard_conexiones.svg').write_text('\n'.join(S)+'\n',encoding='utf-8')
    with (ROOT/'docs/protoboard_conexiones.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['id','tipo','valor_o_dominio','origen','destino','nota'])
        for ident,a,b,domain,*_ in WIRES:
            note='Potencia fuera de protoboard' if ident in {'W22','W23','W24','W25','W26','W27'} else 'Referencia GND directa a estrella' if ident=='W28' else 'Baja corriente / senal'
            w.writerow([ident,'cable',domain,a,b,note])
        for ident,value,a,b in RESISTORS: w.writerow([ident,'resistencia',value,a,b,'1/4 W; divisores preferiblemente 1 %'])
        for ident,value,a,b in CAPS: w.writerow([ident,'condensador',value,a,b,'Local al modulo; electrolitico: + en origen, - en destino' if ident in {'C1','C3'} else 'Ceramico sin polaridad; local al modulo'])

if __name__=='__main__':
    count=validate()
    generate()
    print(f'OK: {len(WIRES)} cables, {len(RESISTORS)} resistencias, {len(CAPS)} condensadores; {count} agujeros asignados sin duplicar.')
    print('OK: positivos separados; GND comun; ECHO sin puente directo; GPIO contrastados con config.h.')
    print('Generados docs/imagenes/protoboard_conexiones.svg y docs/protoboard_conexiones.csv')
