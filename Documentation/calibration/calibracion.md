# Instalación, calibración y aceptación del dispensador automático

Esta guía corresponde al firmware automático de la rama predeterminada. El montaje
USB-C y dashboard manual del PR #1 es otra configuración: use sus instrucciones y
no mezcle las dos alimentaciones. El software no puede medir a distancia los gramos,
la corriente o las posiciones de un servo que no está conectado al equipo de revisión.

## 1. Alimentación y montaje

- A: buck-boost regulado a 6,0 V, ≥3 A continuos, entrada garantizada de 6,0 a 8,4 V.
  Un XL4015 requiere al menos 8 V según [su fabricante](https://www.xlsemi.com/datasheet/XL4015-EN.pdf)
  y queda fuera de especificación durante gran parte de la descarga de una batería 2S.
- B: buck de bajo dropout regulado a 5,0–5,1 V, ≥2 A continuos y funcionamiento
  garantizado en ese mismo rango de entrada. Validar el módulo concreto; ajustar
  sin carga no demuestra su funcionamiento bajo carga.
- Medir ambos rieles con batería llena y a 6,8 V, primero sin módulos y luego con
  Wi-Fi, cámara y motor activos. El servo debe conservar ≥5,8 V durante el giro,
  sin reinicios. Registrar corriente máxima y temperatura tras 10 minutos.
- Mantener BMS 2S, fusible, polaridad, divisores de ECHO y GND común según las tablas.
  Confirmar que el MG995 sea de 180°, no de giro continuo.
- El panel de 0,3 W es demostrativo. El cálculo estima ~42 Wh/día del dispensador;
  no sostiene uso continuo. El PC necesita alimentación aparte. Para incluirlo:
  `python Documentation/power/calculo_energia.py --pc-w POTENCIA_MEDIDA`.

## 2. Red y software

1. Copiar `secrets_ejemplo.h` como `secrets.h` en las carpetas de ambos sketches y
   completar la Wi-Fi 2,4 GHz. No subir credenciales a GitHub.
2. En los dos `config.h`, ajustar gateway, máscara e IP. Reservar las IP en el router
   para impedir conflictos. En el controlador, `URL_PC` debe apuntar al PC real;
   `URL_CAMARA` a la ESP32-CAM. No basta con cambiar la URL en Python.
3. Compilar/subir ambos firmwares. Las versiones de PlatformIO y ArduinoJson están
   fijadas para repetir la compilación. Por defecto se usa `MODO_FERIA 0`.
4. En `OpenCV`, crear `.venv`, instalar `requirements.txt` y ejecutar
   `python descargar_modelo.py`. La descarga comprueba SHA-256; no requiere Internet
   después de instalar.
5. Ejecutar `python comprobar_instalacion.py` y, con el montaje encendido,
   `python comprobar_instalacion.py --red`. Este comando solo consulta `/status`;
   no solicita fotos ni acciona el servo.
6. Copiar `OpenCV/dispensador.env.example` a `OpenCV/dispensador.env`, completar las
   URL y arrancar `python iniciar.py`. Abrir el puerto TCP 8000 para la red local.
   El panel queda en `http://IP_DEL_PC:8000/`.

En pruebas de banco por USB, desactivar únicamente los monitores de batería/riel
que no estén conectados; restaurarlos al montar los divisores del diseño 2S.

## 3. Calibración supervisada

Hacer las pruebas sin mascotas. Activar temporalmente `MODO_FERIA 1` para habilitar
`CICLO`. Los comandos de calibración son acceso físico de mantenimiento y no están
sujetos al historial de alimentación; no usarlos para alimentar.

1. Con el mecanismo vacío, ajustar los pulsos CERRADO, LLENADO y DESCARGA usando las
   marcas y `SERVO <us>`. Guardar los valores medidos en `config.h` y volver a compilar.
2. Pesar al menos 10 ciclos con tolva llena, 10 con nivel medio y 10 con nivel bajo,
   con la marca/tamaño de croqueta que se usará. Completar `plantilla_dosificacion.csv`
   (duplicar filas según sea necesario). Analizar con
   `python analizar_dosificacion.py MEDICIONES.csv --objetivo-g GRAMOS_DEFINIDOS`.
   Aceptar CV ≤10 % también en cada nivel; ajustar tiempos/mecánica si no se cumple.
3. Configurar `CICLOS_PERRO` y `CICLOS_GATO` según los gramos medidos y la ración
   indicada para los animales. Los valores de ejemplo no son una pauta nutricional.
4. Ejecutar `NIVEL VACIO` y `NIVEL LLENO` en sus condiciones reales. Comprobar lectura
   cercana a 0/100 %, alerta al bajar del 20 %, bloqueo al confirmar ≤3 % y reposición.
5. Completar `plantilla_distancia.csv` y ajustar distancias con el sensor instalado.
6. Capturar un conjunto propio de perro/gato/otros con `capturar_dataset.py`.
   Separar imágenes para ajuste de umbrales y otras nuevas para evaluación final;
   no medir la precisión con las mismas fotos usadas para elegir umbrales.
   Ejecutar `probar_imagenes.py dataset --barrido` y evaluar las fotos reservadas.
   La cámara clasifica especies, no individuos, y no garantiza rechazar fotos o
   escenas con varios animales. Registrar esas limitaciones en la presentación.
7. Volver a `MODO_FERIA 0`, fijar intervalos/límites y cargar la versión de uso.

## 4. Reinicios, errores y entrega real

Cada intento de alimentación se guarda en NVS ANTES de accionar el motor, aunque
termine por atasco o pérdida del riel. Los contadores indican intentos reservados,
no gramos de alimento confirmados. Sin RTC, después de reiniciar todas las cuentas
recuperadas se consideran recientes: los cooldowns y la ventana de 24 h comienzan
de nuevo. Esto puede retrasar una ración; un responsable debe controlar la comida.

`ERROR_REGISTRO` significa que no se pudo leer/verificar/escribir el historial.
RESET no lo borra. Revisar la memoria; no borrar la flash para eludir los límites.
La primera instalación no conoce las raciones entregadas antes de instalar este
firmware. Un fallo PWM impide entregar raciones hasta corregirlo y reiniciar.

La caída del riel solo es un indicio de atasco. Probar un atasco controlado con el
mecanismo supervisado: si la fuente mantiene el voltaje, este método puede no
advertirlo. Para confirmar físicamente movimiento o gramos, se necesita añadir
retroalimentación de posición/peso y diseñar su circuito; ninguna prueba simulada
sustituye esa medición.

## 5. Criterios de aceptación y operación continua

Registrar fecha, firmware, alimento, medidas y fotos en `acta_pruebas.csv`:

- Rieles estables en batería llena/baja, sin reinicios ni calentamiento anormal.
- CV de dosificación ≤10 % en cada nivel de tolva.
- Cero dispensaciones indebidas y ≥90 % de detecciones correctas en ≥20 visitas.
- Alertas de nivel en ≤3 minutos; tolva vacía bloquea la alimentación.
- Mediana de `/classify` <2 s en la LAN del lugar; probar pérdida y recuperación
  de cámara, servidor y Wi-Fi. Usar `OpenCV/medir_red.py --clasificar`.
- Tras una ración, reiniciar y verificar que se conservan cuentas y bloqueo.
- Al menos una hora integrada sin reinicios. Para uso permanente, ampliar la prueba
  a 24 h y comprobar autonomía real antes de dejar el sistema sin supervisión.

Las celdas sin medidas quedan **pendientes**, no aprobadas. Para iniciar el servidor
al encender el PC, ver [operación continua](../operacion/README.md).
