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

## Verificación sin hardware

Todo esto corre automáticamente en GitHub Actions (`.github/workflows/verificacion.yml`) en cada `push`.

### 1. Lógica en el PC (segundos)

```bash
cd ESP32/test_host
make                       # 19 escenarios de la máquina de estados
git clone --depth 1 https://github.com/bblanchon/ArduinoJson
make sintaxis              # compila todo el firmware (ESP32 y ESP32-CAM) contra stubs de Arduino, API núcleo 2.x y 3.x
```

### 2. Compilación real con la cadena de Espressif

```bash
URL=https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.0.7 --additional-urls $URL     # o 2.0.17
arduino-cli lib install "ArduinoJson@7.4.2"
arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 --warnings all ESP32/Dispensador_ESP32
arduino-cli compile --fqbn "esp32:esp32:esp32cam:PartitionScheme=huge_app" --warnings all ESP32_CAM/Camara_ESP32CAM
```

| Núcleo | ESP32 (flash / RAM estática) | ESP32-CAM (flash / RAM estática) |
|---|---|---|
| 2.0.17 | 955 kB (72 %) / 48 kB | 847 kB (26 %) / 50 kB |
| 3.0.7 | 1 092 kB (83 %) / 48 kB | 1 023 kB (32 %) / 50 kB |

La única advertencia es la intencional de `secrets.h` cuando todavía no se creó.

### 3. Firmware real en el emulador QEMU de Espressif

QEMU emula el ESP32 (CPU, memoria flash, temporizadores, GPIO, PWM) pero **no la radio Wi-Fi ni el ADC**. La
variante `-DSIMULACION_QEMU` reemplaza solo esas dos partes (Wi-Fi "desconectado", tensiones nominales); todo lo
demás es el código real. En `setup()` ejecuta una autoprueba (AYUDA, ESTADO, DIST, ENERGIA, SERVO, CICLO,
CLASIFICAR, RESET) que `qemu_autoprueba.sh` verifica:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 --build-path build/qemu \
  --build-property "compiler.cpp.extra_flags=-DSIMULACION_QEMU" ESP32/Dispensador_ESP32
# QEMU: https://github.com/espressif/qemu/releases (paquete qemu-xtensa-softmmu, Linux; requiere libslirp0)
ESP32/test_host/qemu_autoprueba.sh build/qemu \
  ~/.arduino15/packages/esp32/hardware/esp32/2.0.17/tools/partitions/boot_app0.bin qemu/bin/qemu-system-xtensa
```

Resultado: `AUTOPRUEBA QEMU: OK` (12 comprobaciones; un ciclo de dosis completo tarda 3,8 s). Esta prueba
detectó y permitió corregir un error real: con el botón BOOT mantenido (o GPIO0 a nivel bajo) los errores se
borraban cada 50 ms; ahora cada pulsación larga produce un solo borrado.

**Nunca** compilar con `SIMULACION_QEMU` para la placa real: desactiva el Wi-Fi y las mediciones.

Lo que ninguna de estas pruebas sustituye: Wi-Fi, cámara, HC-SR04, servo y tensiones reales (plan de pruebas del
README principal, §38).
