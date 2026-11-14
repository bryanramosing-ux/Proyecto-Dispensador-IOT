# ESP32-CAM AI-Thinker — Cámara de red local

## Responsabilidad

La ESP32-CAM captura imágenes JPEG y ofrece un endpoint de stream MJPEG. No clasifica mascotas ni controla el servomotor. En la versión actual el dashboard consume el stream a través del backend local.

## Endpoints

| Ruta | Respuesta |
|---|---|
| `GET /status` | Estado de cámara, PSRAM, resolución, RSSI y contadores |
| `GET /capture` | Una fotografía JPEG nueva |
| `GET /stream` | Stream MJPEG multipart de duración limitada por petición |

El stream implementado envía un número finito de cuadros por conexión y luego termina; el backend/dashboard puede volver a conectarse. No equivale a un servicio de video ilimitado ni garantiza una tasa de cuadros fija. La captura y el stream comparten el recurso de cámara y deben probarse con un solo cliente inicialmente.

## Hardware

- Módulo ESP32-CAM AI-Thinker con sensor OV2640 y PSRAM habilitada.
- Alimentación estable de 5 V al pin 5V y GND.
- Desacoplo recomendado: 470 µF y 100 nF cerca del módulo.
- No conectar GPIO de la ESP32-CAM al ESP32 DevKit: se comunican por Wi-Fi.
- No usar la cámara 5110V0 del inventario como sustituta sin identificar sensor, interfaz, pinout y tensión.

La cámara puede reiniciarse si la alimentación cae. No desactive el detector brownout: corrija fuente, cable y distribución.

## Programación

1. Usar ESP32-CAM-MB o adaptador USB-TTL con UART a niveles lógicos de 3,3 V.
2. Con USB-TTL: 5V a 5V, GND a GND, TX/RX cruzados a U0R/U0T.
3. GPIO0 a GND solo durante la carga; retirar el puente y reiniciar para ejecución normal.
4. Seleccionar AI Thinker ESP32-CAM, habilitar PSRAM y elegir partición compatible con el tamaño de firmware.
5. Copiar `secrets_ejemplo.h` a `secrets.h` y completar la red.
6. Configurar IP estática/reservada en `config.h` o usar DHCP de forma coherente con el backend.

## Prueba

Con la placa conectada a una fuente estable y a la misma Wi-Fi que el PC, comprobar primero `/status`, después `/capture` y finalmente `/stream`. No considerar verificado el stream solo porque la página del dashboard cargue: probarlo con la cámara física.
