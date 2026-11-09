# Documento técnico breve para la arquitectura local del dispensador.

## Objetivo

Este repositorio ya incluye un firmware funcional de ESP32 y ESP32-CAM y un servidor de visión de Python. El ajuste adicional que se incorpora aquí es una capa local de control y dashboard web para monitorizar el sistema sin depender de Internet.

## Arquitectura local

- ESP32 DevKit V1: controla HC-SR04, servo MG995, estado del dispensador y comunica JSON por HTTP.
- ESP32-CAM AI-Thinker: toma capturas JPEG y expone `/capture` y `/stream`.
- Backend local: `backend/dashboard_server.py` agrega API HTTP para consultar el estado, capturar fotos, listar galería y registrar eventos.
- Frontend: `frontend/index.html` + `frontend/app.js` muestra tarjetas, estado del sistema y galería.

## API local

- `GET /api/health` → estado del backend.
- `GET /api/status` → consulta el estado de la cámara y del ESP32.
- `POST /api/capture` → captura la foto actual y la guarda en `backend/storage/gallery`.
- `GET /api/gallery` → lista las fotos guardadas.
- `DELETE /api/gallery/<nombre>` → elimina una foto.
- `POST /api/dispense` → devuelve `501` por defecto, para no activar la dispensación desde la red sin validación física.

## Ejecución

```bash
cd Proyecto-Dispensador-IOT
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/dashboard_server.py
```

Luego abra `http://localhost:8001` desde un navegador conectado a la misma red local.

## Limitaciones

- Las rutinas de dispensación remota quedan deshabilitadas por defecto para respetar la seguridad del proyecto.
- El sistema real debe validarse con el hardware físico, puesto que la cámara, el Wi‑Fi y los sensores no se pueden verificar sin el montaje real.
