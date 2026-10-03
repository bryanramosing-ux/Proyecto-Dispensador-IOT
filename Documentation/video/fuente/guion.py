"""
Guion del video "Dispensador inteligente: funcionamiento y armado".

Cada escena tiene:
  * id, tipo ('lamina', 'paneo', '3d') y los datos visuales;
  * frases: lo que dice la narración. El texto se muestra tal cual en los subtítulos y
    se pasa a la voz con PRONUNCIACION aplicada (siglas deletreadas, unidades en palabras).
"""

PRONUNCIACION = [
    ("ESP32-CAM", "E ese pe treinta y dos cam"),
    ("ESP32", "E ese pe treinta y dos"),
    ("HC-SR04", "hache ce ese erre cero cuatro"),
    ("MG995", "eme ge novecientos noventa y cinco"),
    ("MobileNetV2", "mobail net ve dos"),
    ("OpenCV", "open ce ve"),
    ("Elegoo Neptune 4 Plus", "Elegú Néptun cuatro plus"),
    ("PETG", "pe e te ge"),
    ("PLA", "pe ele a"),
    ("BMS", "be eme ese"),
    ("USB-C", "u ese be ce"),
    ("GX12", "ge equis doce"),
    ("ntfy", "notifái"),
    ("wifi", "uaifai"),
    ("IoT", "Internet de las cosas"),
    ("0,3 W", "cero coma tres watts"),
    ("1,75 W", "uno coma setenta y cinco watts"),
    ("1500 µs", "mil quinientos microsegundos"),
    ("35 cm", "treinta y cinco centímetros"),
    ("20 ms", "veinte milisegundos"),
    ("6 V", "seis volts"),
    ("5 V", "cinco volts"),
    ("100°", "cien grados"),
    ("20 %", "veinte por ciento"),
    ("%", " por ciento"),
    ("2 s", "dos segundos"),
    (" kg", " kilos"),
    (" h ", " horas "),
    ("1 =", "uno igual"),
    ("2 =", "dos igual"),
    ("0 =", "cero igual"),
]


def a_voz(texto):
    for a, b in PRONUNCIACION:
        texto = texto.replace(a, b)
    return texto


# Imágenes: rutas desde la raíz del repositorio (laminas.py las copia a web/img). Las que no
# existen ahí (panel_web.png, esquema_energia.png) se generan directamente en web/img.
R = "Mechanical/render/"
M = "Documentation/manual_armado/img/"
W = "Documentation/wiring/"

ESCENAS = [
    dict(id="01_portada", tipo="3d", anim="giro", titulo="Dispensador inteligente de alimento para mascotas",
         sub="IoT · visión artificial · energía solar", frases=[
             "Este es el dispensador inteligente de alimento para mascotas.",
             "Funciona con IoT, visión artificial y energía solar.",
             "En este video vemos cómo funciona y cómo se arma, paso a paso.",
         ]),
    dict(id="02_que_hace", tipo="lamina", plantilla="imagen_lista", titulo="¿Qué hace?",
         imagen=R + "vista_frente.png", puntos=[
             ("Detecta", "a la mascota con un sensor ultrasónico"),
             ("Identifica", "con una foto: 1 = PERRO, 2 = GATO"),
             ("Entrega", "la ración que le corresponde"),
             ("Si duda", "no entrega nada (0 = no dispensar)"),
         ], frases=[
             "Cuando un perro o un gato se acerca, el dispensador lo detecta y le saca una foto.",
             "Reconoce si es perro o gato, y le entrega la ración que le corresponde.",
             "Si no está seguro, no entrega nada.",
         ]),
    dict(id="03_componentes", tipo="lamina", plantilla="tarjetas", titulo="Componentes", tarjetas=[
        ("ESP32 DevKit V1", "El cerebro: decide y controla todo", "#1f4e79"),
        ("ESP32-CAM", "Saca las fotos y las envía por wifi", "#2f6fd6"),
        ("2 × HC-SR04", "Presencia de la mascota y nivel de comida", "#17becf"),
        ("Servo MG995", "Mueve el disco dosificador", "#7b5cd6"),
        ("Panel solar 3 V", "En una estación aparte, donde hay sol", "#b9770e"),
        ("Batería 2S + BMS", "Convertidores de 6 V (servo) y 5 V (electrónica)", "#2e8b57"),
    ], frases=[
        "Los componentes principales son: el ESP32, que es el cerebro; la ESP32-CAM, que saca las fotos;",
        "dos sensores ultrasónicos HC-SR04, uno para detectar a la mascota y otro para medir la comida;",
        "el servomotor MG995, que mueve el dosificador; y un panel solar.",
        "Además lleva una batería de litio con su protección, y convertidores de 6 V para el servo y de 5 V para la electrónica.",
    ]),
    dict(id="04_funcionamiento", tipo="lamina", plantilla="flujo", titulo="Cómo funciona", pasos=[
        ("1", "Detecta", "HC-SR04: algo a menos de 35 cm"),
        ("2", "Pregunta", "El ESP32 le pide al PC que identifique"),
        ("3", "Foto y análisis", "ESP32-CAM → OpenCV + red neuronal"),
        ("4", "Responde", "1 = perro · 2 = gato · 0 = duda"),
        ("5", "Decide y entrega", "Reglas de seguridad → servo MG995"),
    ], frases=[
        "El funcionamiento es así.",
        "Uno: el sensor ultrasónico detecta que algo se acercó a menos de 35 cm.",
        "Dos: el ESP32 le pide al computador que identifique a la mascota.",
        "Tres: el computador le pide una foto a la cámara y la analiza con OpenCV y una red neuronal, MobileNetV2.",
        "Cuatro: responde 1 si es perro, 2 si es gato, o 0 si no está seguro.",
        "Cinco: el ESP32 revisa las reglas, como el tiempo mínimo entre raciones y el límite diario, y recién ahí mueve el servo.",
    ]),
    dict(id="05_fotos", tipo="lamina", plantilla="linea_tiempo", titulo="Fotos, no video",
         eventos=[("0 s", "Llega la mascota", "detecta"), ("Foto 1", "entrando al cuadro", "0"),
                  ("+2 s", "Foto 2", "duda"), ("+2 s", "Foto 3", "GATO ✓")],
         notas=["Sin nadie delante: ninguna foto", "Máximo 5 fotos por visita",
                "Las fotos de la misma visita se combinan"], frases=[
             "La cámara no graba video. Saca una foto solo cuando llega la mascota.",
             "Si con esa foto no alcanza, saca otra cada 2 s, hasta cinco fotos.",
             "El computador combina las fotos de la misma visita: así una foto movida no provoca un error.",
         ]),
    dict(id="06_red_local", tipo="lamina", plantilla="red", titulo="Todo en una red local", frases=[
        "Todo funciona en una red local.",
        "Los tres equipos se comunican por wifi dentro de la misma sala, y no se usa Internet.",
        "Por eso es rápido: el análisis de cada foto tarda unos 20 ms en el computador.",
        "Para la feria se puede usar el punto de acceso del celular, con los datos móviles apagados.",
    ]),
    dict(id="07_dosificador", tipo="3d", anim="dosificador", titulo="El dosificador",
         sub="Disco con un bolsillo · nunca conecta la tolva con el conducto", frases=[
             "El alimento se dosifica con un disco que tiene un hueco.",
             "El servo lleva el hueco debajo de la tolva, se llena, gira 100° y lo vacía sobre el conducto.",
             "Nunca conecta la tolva con el conducto al mismo tiempo, así que no cae comida de más.",
             "Cada vuelta entrega siempre el mismo volumen, y los gramos se calibran con una balanza.",
         ]),
    dict(id="08_recorrido", tipo="lamina", plantilla="dos_imagenes", titulo="Recorrido del alimento",
         imagenes=[R + "corte_recorrido_alimento.png", R + "vista_corte.png"], frases=[
             "El alimento baja por un conducto cerrado, al frente de la torre.",
             "La electrónica queda atrás, separada por un tabique: ningún cable pasa por donde pasa la comida.",
         ]),
    dict(id="09_nivel", tipo="lamina", plantilla="nivel", titulo="Sensor de nivel en la tolva",
         imagen=M + "detalle_tapa_sensor.png", frases=[
             "En la tapa hay un segundo sensor ultrasónico, que mide cuánta comida queda.",
             "Como la tolva es un embudo, el porcentaje se calcula por volumen y no por altura.",
             "Cuando queda menos del 20 %, el ESP32 envía una alerta al computador y al celular, con la aplicación ntfy.",
             "Si la tolva se vacía, deja de dar raciones hasta que se recargue.",
         ]),
    dict(id="10_panel", tipo="lamina", plantilla="imagen_lista", titulo="Panel web en el computador",
         imagen="panel_web.png", ancho=600, puntos=[
             ("Nivel", "de la tolva en vivo"),
             ("Estado", "del ESP32 y de la energía"),
             ("Alertas", "de comida baja o agotada"),
             ("Última foto", "analizada, con su resultado"),
         ], frases=[
             "En el computador hay un panel web, que se abre desde el navegador o desde el celular.",
             "Muestra el nivel de la tolva, el estado del ESP32, las alertas y la última foto analizada.",
         ]),
    dict(id="11_energia", tipo="lamina", plantilla="energia", titulo="Energía",
         imagen="esquema_energia.png", frases=[
             "La energía viene de dos baterías de litio en serie, protegidas por un BMS y un fusible.",
             "Un convertidor da 6 V solo para el servo, y otro da 5 V para la electrónica.",
             "El panel aporta 0,3 W, y el sistema consume en promedio 1,75 W: por eso la carga principal es por USB-C, y el panel es demostrativo.",
         ]),
    dict(id="12_estacion", tipo="3d", anim="estacion", titulo="Estación solar remota",
         sub="Se ubica donde hay sol · se inclina de 0° a 75°", frases=[
             "El panel va aparte, en una estación que se ubica donde haya sol, y se conecta a la torre con un cable y un conector GX12.",
             "La bandeja se inclina según el lugar, y se fija con dos tornillos.",
         ]),
    dict(id="13_esquema", tipo="paneo", imagen=W + "esquema_conexiones.png", titulo="Esquema eléctrico completo",
         frases=[
             "Este es el esquema eléctrico completo.",
             "El servo recibe sus 6 V directo del convertidor; del ESP32 solo recibe la señal.",
             "Las señales de eco de los dos sensores pasan por divisores de resistencias, para no dañar el ESP32.",
         ]),
    dict(id="14_placa", tipo="lamina", plantilla="imagen_grande", titulo="Placa de control",
         imagen=W + "placa_control.png", frases=[
             "La placa de control se suelda siguiendo una lista de 34 cables numerados, y un programa verifica que coincida con el código.",
         ]),
    dict(id="15_impresion", tipo="lamina", plantilla="impresion", titulo="Impresión 3D · Elegoo Neptune 4 Plus",
         imagen=R + "placas_impresion.png", frases=[
             "Todas las piezas se imprimen en la Elegoo Neptune 4 Plus, sin soportes, en cinco placas.",
             "Las que tocan el alimento van en PETG, y el resto en PLA: son unos 2,2 kg de filamento.",
         ]),
    dict(id="16_armado", tipo="lamina", plantilla="titulo", titulo="Armado paso a paso",
         sub="11 pasos · manual completo en Documentation/manual_armado", frases=[
             "Ahora, el armado paso a paso.",
         ]),
]

PASOS = [
    (1, "Base y cajón de energía", ["01", "16"], "2 × M3×10",
     "Paso uno. Se arma el cajón de energía y se desliza dentro de la base, desde atrás."),
    (2, "Cuerpo, bandeja y cápsulas", ["02", "05", "03", "04"], "8 × M3×10 + tuercas · 4 × M3×12",
     "Paso dos. En el cuerpo se atornillan la bandeja del ESP32 y las cápsulas del sensor y de la cámara. Después el cuerpo se atornilla sobre la base."),
    (3, "Conducto y pico", ["09", "10"], "4 × M3×10",
     "Paso tres. El conducto de alimento se baja desde arriba, y el pico de salida se coloca desde afuera."),
    (4, "Servo y viga", ["06", "MG"], "2 × M3×10",
     "Paso cuatro. Con el servo centrado en 1500 µs, se atornilla a su viga, que se apoya dentro del cuerpo."),
    (5, "Carcasa y placa base", ["08a", "08d"], "3 × M3×10",
     "Paso cinco. Se colocan la carcasa del dosificador y la placa base, con la salida hacia el frente."),
    (6, "Disco dosificador", ["08b"], "tornillos del servo",
     "Paso seis. El disco se atornilla al servo en la marca de cerrado, y se calibran las posiciones."),
    (7, "Placa superior", ["08c"], "sin tornillos",
     "Paso siete. La placa superior se asienta con su chaveta, sin tornillos."),
    (8, "Tolva", ["07"], "3 × M3×10",
     "Paso ocho. La tolva va encima, con la boca del embudo en su lugar."),
    (9, "Tapa con el sensor de nivel", ["13b", "HC", "13a", "13c"], "2 × M3×12",
     "Paso nueve. En la tapa va la cápsula con el sensor de nivel. Su cable baja por un conducto oculto en una esquina."),
    (10, "Tapa trasera y comedero", ["14", "11"], "4 × M3×10",
     "Paso diez. Se cierra la tapa trasera de la electrónica y se encaja el comedero."),
]

for n, titulo, piezas, tornillos, texto in PASOS:
    ESCENAS.append(dict(id=f"17_paso_{n:02d}", tipo="3d", anim="paso", paso=n, piezas=piezas,
                        titulo=f"Paso {n} de 11 · {titulo}", sub=f"Tornillería: {tornillos}", frases=[texto]))

ESCENAS += [
    dict(id="18_paso_11", tipo="3d", anim="estacion", titulo="Paso 11 de 11 · Estación solar",
         sub="Tornillería: 2 × M4×12 + tuercas", frases=[
             "Paso once. La estación solar se arma aparte: el panel va en la bandeja, que se inclina y se fija con dos tornillos.",
         ]),
    dict(id="19_pruebas", tipo="lamina", plantilla="dos_listas", titulo="Calibración y pruebas",
         listas=[("Se calibra", ["Posiciones del disco", "Gramos por ciclo (balanza)", "Distancia de detección",
                                 "Umbrales de la cámara", "Sensor de nivel: vacío y lleno"]),
                 ("Se prueba solo, en cada cambio", ["Lógica del ESP32 (26 casos)", "Visión por computador (29 pruebas)",
                                                     "Compilación real del firmware", "Firmware en un emulador",
                                                     "Geometría de las 22 piezas"])],
         frases=[
             "Antes de usarlo se calibran las posiciones del disco, los gramos por ciclo, la distancia de detección, los umbrales de la cámara y el sensor de nivel.",
             "Y todo el proyecto se prueba automáticamente en cada cambio: la lógica, la visión, la compilación del firmware y la geometría de las piezas.",
         ]),
    dict(id="20_cierre", tipo="3d", anim="giro", titulo="Dispensador inteligente",
         sub="github.com/bryanramosing-ux/Proyecto-Dispensador-IOT", frases=[
             "Así, el dispensador reconoce a cada mascota, le da su ración, avisa cuando falta comida y funciona de manera local.",
             "El código, los archivos para imprimir y el manual de armado están en el repositorio del proyecto.",
         ]),
]
