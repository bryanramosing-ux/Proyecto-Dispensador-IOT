# ESP32 DevKit V1 — Controlador del dispensador

Controla todo el sistema: lee el HC-SR04, pide la clasificación al PC, **decide**
si dispensa y mueve el MG995. Implementa la máquina de estados con manejo de errores.

## Archivos

| Archivo | Responsabilidad |
|---|---|
| `Dispensador_ESP32/Dispensador_ESP32.ino` | `setup()`/`loop()`, une los módulos, `/status`, comandos serie |
| `Dispensador_ESP32/config.h` | Pines, red, umbrales, tiempos, dosis (valores PROVISIONALES marcados) |
| `Dispensador_ESP32/Controlador.*` | Máquina de estados (sin dependencias de hardware: se prueba en PC) |
| `Dispensador_ESP32/Ultrasonico.*` | HC-SR04 con mediana de N disparos |
| `Dispensador_ESP32/Dosificador.*` | PWM del MG995 con rampa, ciclos llenar/descargar, anti-atasco |
| `Dispensador_ESP32/Energia.*` | Tensiones de batería, riel del servo y panel (ADC1) |
| `Dispensador_ESP32/Red.*` | Wi-Fi, cliente HTTP (PC y cámara), servidor `/status` |
| `Dispensador_ESP32/secrets_ejemplo.h` | Plantilla de credenciales Wi-Fi |
| `test_host/` | Pruebas de la máquina de estados y verificación de compilación en PC |

## Compilar y cargar

1. Copiar `Dispensador_ESP32/secrets_ejemplo.h` como `Dispensador_ESP32/secrets.h` y completar SSID/clave (red **2,4 GHz**).
2. Revisar `config.h`: IP del ESP32, del PC (`URL_PC`) y de la cámara (`URL_CAMARA`).
3. **Arduino IDE**: abrir `Dispensador_ESP32/Dispensador_ESP32.ino`, placa *DOIT ESP32 DEVKIT V1*, instalar la biblioteca **ArduinoJson 7** (Gestor de bibliotecas). Compatible con el núcleo esp32 2.x y 3.x.
   **PlatformIO**: `pio run -t upload && pio device monitor` desde esta carpeta.
4. Si la placa se alimenta desde el bus de 5 V **y** se conecta el USB al PC, verificar que la placa tenga diodo entre VBUS y VIN; si no se sabe, desconectar el 5 V externo mientras se programa.

## Comandos del monitor serie (115200 baudios)

| Comando | Uso |
|---|---|
| `DIST` | Distancia actual del HC-SR04 |
| `SERVO <us>` | Mueve el disco a un pulso (500–2500 µs) — calibración de posiciones |
| `CICLO <n>` | Ejecuta n ciclos de dosis (para pesar con balanza) |
| `CLASIFICAR` | Pide una clasificación al PC **sin dispensar** |
| `ENERGIA` | Tensiones de batería, riel del servo y panel |
| `ESTADO` | JSON de estado |
| `RESET` | Borra ERROR_SERVO / ERROR_MECANISMO (también: botón BOOT 2 s) |

No existe un comando remoto de "dar comida": dispensar manualmente exige acceso físico al USB.

## Verificación en PC (sin hardware)

```bash
cd ESP32/test_host
make                       # 19 escenarios de la máquina de estados
git clone --depth 1 https://github.com/bblanchon/ArduinoJson
make sintaxis              # compila todo el firmware (ESP32 y ESP32-CAM) contra stubs de Arduino, API núcleo 2.x y 3.x
```

`make sintaxis` detecta errores de C++ y de uso de API, pero **no reemplaza** la
compilación real con la cadena de herramientas de Espressif (Arduino IDE / PlatformIO).
