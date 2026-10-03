# Guion del video · Dispensador inteligente

Texto de la narración, escena por escena (el mismo de los subtítulos). Sirve para leerlo en voz alta en la
presentación o para grabar la narración con su propia voz.

### Dispensador inteligente de alimento para mascotas · 0:00

Este es el dispensador inteligente de alimento para mascotas. Funciona con IoT, visión artificial y energía solar. En este video vemos cómo funciona y cómo se arma, paso a paso.

### ¿Qué hace? · 0:14

Cuando un perro o un gato se acerca, el dispensador lo detecta y le saca una foto. Reconoce si es perro o gato, y le entrega la ración que le corresponde. Si no está seguro, no entrega nada.

### Componentes · 0:28

Los componentes principales son: el ESP32, que es el cerebro; la ESP32-CAM, que saca las fotos; dos sensores ultrasónicos HC-SR04, uno para detectar a la mascota y otro para medir la comida; el servomotor MG995, que mueve el dosificador; y un panel solar. Además lleva una batería de litio con su protección, y convertidores de 6 V para el servo y de 5 V para la electrónica.

### Cómo funciona · 0:59

El funcionamiento es así. Uno: el sensor ultrasónico detecta que algo se acercó a menos de 35 cm. Dos: el ESP32 le pide al computador que identifique a la mascota. Tres: el computador le pide una foto a la cámara y la analiza con OpenCV y una red neuronal, MobileNetV2. Cuatro: responde 1 si es perro, 2 si es gato, o 0 si no está seguro. Cinco: el ESP32 revisa las reglas, como el tiempo mínimo entre raciones y el límite diario, y recién ahí mueve el servo.

### Fotos, no video · 1:35

La cámara no graba video. Saca una foto solo cuando llega la mascota. Si con esa foto no alcanza, saca otra cada 2 s, hasta cinco fotos. El computador combina las fotos de la misma visita: así una foto movida no provoca un error.

### Todo en una red local · 1:53

Todo funciona en una red local. Los tres equipos se comunican por wifi dentro de la misma sala, y no se usa Internet. Por eso es rápido: el análisis de cada foto tarda unos 20 ms en el computador. Para la feria se puede usar el punto de acceso del celular, con los datos móviles apagados.

### El dosificador · 2:13

El alimento se dosifica con un disco que tiene un hueco. El servo lleva el hueco debajo de la tolva, se llena, gira 100° y lo vacía sobre el conducto. Nunca conecta la tolva con el conducto al mismo tiempo, así que no cae comida de más. Cada vuelta entrega siempre el mismo volumen, y los gramos se calibran con una balanza.

### Recorrido del alimento · 2:36

El alimento baja por un conducto cerrado, al frente de la torre. La electrónica queda atrás, separada por un tabique: ningún cable pasa por donde pasa la comida.

### Sensor de nivel en la tolva · 2:47

En la tapa hay un segundo sensor ultrasónico, que mide cuánta comida queda. Como la tolva es un embudo, el porcentaje se calcula por volumen y no por altura. Cuando queda menos del 20 %, el ESP32 envía una alerta al computador y al celular, con la aplicación ntfy. Si la tolva se vacía, deja de dar raciones hasta que se recargue.

### Panel web en el computador · 3:11

En el computador hay un panel web, que se abre desde el navegador o desde el celular. Muestra el nivel de la tolva, el estado del ESP32, las alertas y la última foto analizada.

### Energía · 3:24

La energía viene de dos baterías de litio en serie, protegidas por un BMS y un fusible. Un convertidor da 6 V solo para el servo, y otro da 5 V para la electrónica. El panel aporta 0,3 W, y el sistema consume en promedio 1,75 W: por eso la carga principal es por USB-C, y el panel es demostrativo.

### Estación solar remota · 3:49

El panel va aparte, en una estación que se ubica donde haya sol, y se conecta a la torre con un cable y un conector GX12. La bandeja se inclina según el lugar, y se fija con dos tornillos.

### Esquema eléctrico completo · 4:03

Este es el esquema eléctrico completo. El servo recibe sus 6 V directo del convertidor; del ESP32 solo recibe la señal. Las señales de eco de los dos sensores pasan por divisores de resistencias, para no dañar el ESP32.

### Placa de control · 4:20

La placa de control se suelda siguiendo una lista de 34 cables numerados, y un programa verifica que coincida con el código.

### Impresión 3D · Elegoo Neptune 4 Plus · 4:29

Todas las piezas se imprimen en la Elegoo Neptune 4 Plus, sin soportes, en cinco placas. Las que tocan el alimento van en PETG, y el resto en PLA: son unos 2,2 kg de filamento.

### Armado paso a paso · 4:43

Ahora, el armado paso a paso.

### Paso 1 de 11 · Base y cajón de energía · 4:46

Paso uno. Se arma el cajón de energía y se desliza dentro de la base, desde atrás.

### Paso 2 de 11 · Cuerpo, bandeja y cápsulas · 4:53

Paso dos. En el cuerpo se atornillan la bandeja del ESP32 y las cápsulas del sensor y de la cámara. Después el cuerpo se atornilla sobre la base.

### Paso 3 de 11 · Conducto y pico · 5:04

Paso tres. El conducto de alimento se baja desde arriba, y el pico de salida se coloca desde afuera.

### Paso 4 de 11 · Servo y viga · 5:11

Paso cuatro. Con el servo centrado en 1500 µs, se atornilla a su viga, que se apoya dentro del cuerpo.

### Paso 5 de 11 · Carcasa y placa base · 5:19

Paso cinco. Se colocan la carcasa del dosificador y la placa base, con la salida hacia el frente.

### Paso 6 de 11 · Disco dosificador · 5:27

Paso seis. El disco se atornilla al servo en la marca de cerrado, y se calibran las posiciones.

### Paso 7 de 11 · Placa superior · 5:33

Paso siete. La placa superior se asienta con su chaveta, sin tornillos.

### Paso 8 de 11 · Tolva · 5:39

Paso ocho. La tolva va encima, con la boca del embudo en su lugar.

### Paso 9 de 11 · Tapa con el sensor de nivel · 5:45

Paso nueve. En la tapa va la cápsula con el sensor de nivel. Su cable baja por un conducto oculto en una esquina.

### Paso 10 de 11 · Tapa trasera y comedero · 5:53

Paso diez. Se cierra la tapa trasera de la electrónica y se encaja el comedero.

### Paso 11 de 11 · Estación solar · 6:00

Paso once. La estación solar se arma aparte: el panel va en la bandeja, que se inclina y se fija con dos tornillos.

### Calibración y pruebas · 6:08

Antes de usarlo se calibran las posiciones del disco, los gramos por ciclo, la distancia de detección, los umbrales de la cámara y el sensor de nivel. Y todo el proyecto se prueba automáticamente en cada cambio: la lógica, la visión, la compilación del firmware y la geometría de las piezas.

### Dispensador inteligente · 6:27

Así, el dispensador reconoce a cada mascota, le da su ración, avisa cuando falta comida y funciona de manera local. El código, los archivos para imprimir y el manual de armado están en el repositorio del proyecto.
