# Arquitectura local

```
ESP32-CAM ──Wi‑Fi──┐                        ┌── navegador PC / móvil / tablet
                   ├── Router ── LAN ── PC con backend + dashboard
ESP32 DevKit ─Wi‑Fi┘      (sin Internet)        (HTTP + SSE)
   └─ GPIO: HC-SR04 (tolva) + MG995
```

Todo funciona dentro de la LAN: no se usan servicios cloud. Cada componente funciona aunque los demás fallen.

| Componente | Rol |
|---|---|
| ESP32 DevKit V1 | Control local del servo y sensor (máquina de estados en `Controlador`). Sigue operando sin Wi‑Fi ni backend (botón BOOT). Envía telemetría cada 2 s con backoff y expone `GET /status`, `POST /dispensar`, `POST /reset-errores`. |
| ESP32-CAM | `GET /status`, `GET /capture` (JPEG puntual), `GET /stream` (MJPEG, sesiones de ~2 s). Una petición a la vez. |
| Backend (`backend/dashboard_server.py`) | Recibe telemetría/alertas, responde al descubrimiento UDP, consulta la cámara, guarda fotos y eventos (SQLite), valida y reenvía comandos, empuja estado por SSE. Solo biblioteca estándar de Python. |
| Dashboard (`frontend/`) | HTML/CSS/JS sin framework: panel, cámara, galería, control, historial. |

## Decisiones técnicas

- **SSE en vez de WebSocket:** el flujo de actualización es solo servidor → navegador; SSE no requiere dependencias, se reconecta solo y es suficiente. Los comandos usan HTTP REST. No se usa MQTT.
- **Descubrimiento UDP:** el ESP32 pregunta `DISPENSADOR?` por broadcast (puerto 41234) y el backend responde `DISPENSADOR!<puerto>`; no hay que escribir la IP del PC en el firmware (si el router bloquea broadcast, defina `URL_BACKEND`).
- **Datos desactualizados:** si el ESP32 no envía telemetría durante 15 s se marca *desconectado* y el dashboard no muestra sus últimos valores como actuales.
- **Cámara compartida:** el backend serializa el acceso (stream, captura, sondeo) con un candado porque el `WebServer` de la cámara atiende un cliente a la vez. Con el video abierto, una captura espera hasta ~8 s a que termine la sesión de stream en curso.

## API del backend

| Ruta | Uso |
|---|---|
| `POST /api/device/telemetry`, `/api/device/alert` | ESP32 → backend (cabecera `X-Device-Token`) |
| `GET /api/status` | Estado agregado (ESP32, cámara, última foto) |
| `GET /api/events` | SSE: eventos `status` y `evento` |
| `GET /api/camera/stream` | Proxy MJPEG de la cámara |
| `POST /api/capture`, `POST /api/camera/refresh`, `POST /api/auto-capture {interval_s}` | Cámara (0 = apagado, 10–3600 s) |
| `GET /api/gallery`, `GET /api/gallery/<foto>[?download=1]`, `DELETE /api/gallery/<foto>` | Galería (borrado exige `X-Confirm: delete`) |
| `POST /api/dispense {porciones, confirm:true}`, `POST /api/reset-errors` | Control (requiere `TOKEN_DISPOSITIVO`) |
| `GET /api/history?tipo=&limit=` | Historial persistente |

Las acciones del navegador exigen `X-Requested-With: dashboard` y mismo origen.

## Campos de la telemetría del ESP32

`estado`, `error`, `wifi_conectado`, `ip`, `rssi`, `backend` (enlazado), `sensor_nivel_ok`, `distancia_nivel_cm`,
`nivel_tolva` (%), `alerta_tolva`, `servo` (`REPOSO|DISPENSANDO|ERROR`), `dispensando`, `pulso_servo_us`,
`dispensaciones_total`, `dispensaciones_24h`, `ultima_dispensacion_hace_s` (-1 = ninguna), `ultimo_origen`,
`ultimas_porciones`, `ultimo_resultado`, `cooldown_s`, `max_porciones`, `uptime_s`, `heap`, entre otros (ver `estadoJson()` en el `.ino`).

## Seguridad y límites

- Red local sin TLS ni login de usuario: **cualquier equipo de la LAN puede abrir el dashboard**. No abra puertos en el router.
- Dispensar exige: token compartido (backend → ESP32), `confirm:true` explícito, 1–`MAX_PORCIONES` porciones, ESP32 conectado, sin dispensación en curso y separación mínima entre comandos. El ESP32 vuelve a validar (cooldown, límite diario, nivel de tolva, errores) y bloquea 60 s tras 5 tokens erróneos.
- Fotos: nombres generados por el servidor (`foto_AAAAMMDD_HHMMSS_xxxxxx.jpg`), validados con expresión regular (sin *path traversal*), máx. 5 MB, escritura atómica.
- El token viaja en claro por la LAN: protege contra errores y curiosos, no contra un atacante que espíe la red.
