# ESP32-CAM (AI-Thinker) — Captura de imágenes

Responsabilidad única: **capturar y entregar un JPEG** cuando el PC lo pide. No
clasifica y no controla el servo.

| Endpoint | Respuesta |
|---|---|
| `GET /capture` | `200 image/jpeg` (foto nueva, VGA 640×480) · `503` si la cámara falla |

**Modo foto, no video (idea del profesor):** la cámara se configura con un solo búfer y `CAMERA_GRAB_WHEN_EMPTY`, así
el controlador no captura cuadros de forma continua: toma uno cada vez que el PC pide `/capture` (solo cuando el
HC-SR04 detectó a una mascota, una foto cada ~2 s mientras siga delante). El sensor queda encendido para que la
exposición automática esté siempre ajustada, y el cuadro viejo que pudo quedar en el búfer se descarta: cada respuesta
es una foto **actual**.
| `GET /status` | `200 application/json` `{"camara":true,"psram":true,"fotos_ok":..,"rssi":..}` |

## Programación (no tiene USB propio)

* Opción A: placa **ESP32-CAM-MB** (USB) — conectar y cargar.
* Opción B: adaptador **USB-TTL a 3,3 V lógicos**:

| USB-TTL | ESP32-CAM |
|---|---|
| 5V | 5V |
| GND | GND |
| TX | U0R (GPIO3) |
| RX | U0T (GPIO1) |
| — | **GPIO0 → GND** solo mientras se carga; luego quitar el puente y pulsar RST |

Arduino IDE: placa **AI Thinker ESP32-CAM**, *PSRAM: Enabled*, *Partition: Huge APP*.
Copiar `Camara_ESP32CAM/secrets_ejemplo.h` como `secrets.h` y revisar `config.h` (IP fija `192.168.1.51`).

## Avisos

* Los GPIO 0, 5, 18, 19, 21–23, 25–27, 32, 34–36, 39 están ocupados por la cámara; 4 = flash; 33 = LED rojo; 16 = PSRAM. **No se cablea ningún GPIO** al ESP32: la comunicación es por Wi-Fi.
* Alimentar por el pin **5V** con una fuente estable (≥1 A disponible) y 470 µF + 100 nF junto al módulo. Con fuentes débiles aparecen reinicios por *brownout*: **no desactivar** el detector de brownout, corregir la alimentación.
* El flash (GPIO4) viene desactivado (`USAR_FLASH 0`): es muy brillante y puede asustar a la mascota.
