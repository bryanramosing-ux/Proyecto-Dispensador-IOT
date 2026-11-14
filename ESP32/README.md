# ESP32 DevKit V1 — Controlador del dispensador

## Responsabilidad en la versión actual

El ESP32 controla el MG995, mide el nivel de alimento de la tolva con **un HC-SR04** y comunica telemetría/comandos con el backend local. La detección automática de presencia y la clasificación de mascotas están desactivadas en la configuración actual.

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| `Dispensador_ESP32.ino` | `setup()`, `loop()`, endpoints y comandos serie |
| `config.h` | Pines, umbrales, tiempos y dosis provisionales |
| `Controlador.*` | Máquina de estados |
| `Ultrasonico.*` | Lectura ultrasónica |
| `Dosificador.*` | PWM del MG995 y ciclos del disco |
| `NivelTolva.*` | Nivel de tolva, calibración VACIO/LLENO y porcentaje de volumen |
| `NivelGeometria.h` | Relación geométrica altura/volumen |
| `Red.*` | Wi-Fi, telemetría y comunicación con backend |
| `Energia.*` | Lecturas de tensión opcionales; monitores de batería y servo desactivados por defecto |
| `secrets_ejemplo.h` | Plantilla de credenciales |

## Hardware de esta versión

- Un HC-SR04 para nivel: TRIG GPIO19, ECHO GPIO21 mediante divisor 1 kΩ/2 kΩ.
- MG995 180°: señal GPIO25; alimentación de potencia externa de 5 V según el diseño actual y la ficha de la unidad.
- ESP32 DevKit V1 con Wi-Fi 2,4 GHz.
- GND común entre lógica y alimentación del servo.

El segundo HC-SR04 de presencia está reservado en el firmware, pero `USAR_DETECCION_AUTOMATICA=0`; no se requiere para la configuración activa.

## Compilar y cargar

1. Copiar `secrets_ejemplo.h` como `secrets.h` y completar credenciales Wi-Fi y token.
2. Revisar los GPIO de `config.h` y confirmar que corresponden a la placa física.
3. Arduino IDE: abrir `Dispensador_ESP32.ino`, seleccionar la placa adecuada (confirmar variante) e instalar ArduinoJson 7 si el entorno lo requiere.
4. PlatformIO: usar el `platformio.ini` de esta carpeta.
5. Mantener desconectada la potencia del MG995 durante la primera carga y verificación.

No conectar a la vez USB del PC y fuente externa sin confirmar el aislamiento entre VBUS y VIN de la placa.

## Comandos serie

| Comando | Uso |
|---|---|
| `NIVEL` | Lee el nivel de tolva |
| `NIVEL VACIO` | Calibra tolva vacía |
| `NIVEL LLENO` | Calibra tolva con alimento hasta marca MAX |
| `SERVO <us>` | Posiciona el servo para calibración |
| `CICLO <n>` | Ejecuta ciclos de dosificación para pruebas controladas |
| `ENERGIA` | Muestra mediciones de energía disponibles |
| `ESTADO` | Estado actual en JSON |
| `RESET` | Borra errores recuperables |

Los comandos exactos pueden depender de la versión compilada; consultar también la salida de AYUDA del firmware.

## Modo automático no habilitado

El código contiene parámetros y rutinas heredadas para un segundo HC-SR04 de presencia y consulta a un servidor de visión. En esta rama la opción está desactivada por configuración. El clasificador OpenCV no debe considerarse parte del ciclo funcional hasta que se active, integre y pruebe extremo a extremo.

## Pruebas

```bash
make -C ESP32/test_host
```

Las pruebas de host comprueban lógica con sustitutos de hardware. No verifican sensores reales, Wi-Fi, tensiones, corriente ni movimiento físico del MG995.
