# Pruebas: qué está verificado y qué no

## Simuladas / de software (ejecutadas)

| Prueba | Comando | Resultado |
|---|---|---|
| Lógica del controlador ESP32 (estados, cooldown, límites, errores, nivel) | `make -C ESP32/test_host` | OK |
| Backend: telemetría, token, validación, galería, *path traversal*, CSRF, persistencia, dispensación, límites, UDP, SSE, fotograma | `python3 -I -m unittest discover -s backend/tests -v` | 24/24 OK |
| **Compilación real** del ESP32 DevKit (`esp32:esp32:esp32`, núcleo 3.0.7) y de la ESP32-CAM (`esp32:esp32:esp32cam`) con `arduino-cli` | `arduino-cli compile` | OK ambas (ESP32: 86 % de flash; CAM: 32 %) |
| Dashboard en navegador contra simulador: carga, SSE, video, captura, galería, dispensación con confirmación, desconexión, móvil 375 px | manual con `simulador_dispositivos.py` | OK, sin errores de consola |

## Pendientes (requieren hardware o la CI)

- [ ] Cargar ambos firmwares en las placas reales (compilan, pero no se han ejecutado en hardware).
- [ ] Descubrimiento UDP y telemetría entre un ESP32 real y el backend (y con el firewall del PC).
- [ ] Video MJPEG real de la ESP32-CAM, estabilidad con 1 y con 2 espectadores.
- [ ] Servo MG995 bajo carga: caída del riel de 5 V, reinicios, calibración de `PULSO_*_US`.
- [ ] HC-SR04: tensión tras el divisor (≤ 3,4 V) y calibración de `DIST_TOLVA_VACIA_CM`.
- [ ] Recuperación: Wi‑Fi caído, reinicio del backend, reinicio del ESP32, apagón.
- [ ] Acceso desde móvil real en la LAN.

No declare el hardware "aprobado" hasta marcar estas casillas con mediciones.
