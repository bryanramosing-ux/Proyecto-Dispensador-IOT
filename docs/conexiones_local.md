# Conexiones mínimas y medidas de seguridad

## Recomendación actual

El sistema mantiene la topología ya validada en el repositorio: ESP32 y ESP32-CAM enlazados por Wi‑Fi local y un PC con Python actuando como backend/visualizador local.

## Conexión crítica

- ESP32 → GPIO25: señal del MG995 mediante resistencia serie y pull-down.
- ESP32 → GPIO26 / GPIO34: sensor HC-SR04 de presencia con divisor de nivel 1 kΩ / 2 kΩ.
- ESP32 → GPIO19 / GPIO21: sensor HC-SR04 de nivel en la tolva con divisor equivalente.
- ESP32-CAM: alimentado por 5 V estable con 470 µF + 100 nF; sin GPIO compartidos con el ESP32.
- GND común del ESP32, cámara y sensores.

## Recomendación de alimentación

- El MG995 no debe conectarse a un GPIO ni a 3.3 V.
- Se recomienda una línea independiente de 6,0 V regida por un conversor DC-DC y condensador cercano al servo.
- La cámara exige fuente estable y cable corto para evitar reinicios por brownout.

## Seguridad

- No se habilita dispensación desde la red sin confirmación explícita.
- Si se activara una petición remota, debe validarse con el mismo conjunto de comprobaciones del firmware: nivel de tolva, cooldown, alimentación, errores de servo y presencia de mascota.
- El uso de la red local debe limitarse a la LAN; no se expone el dashboard a Internet por defecto.
