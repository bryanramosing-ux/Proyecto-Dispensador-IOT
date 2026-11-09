# Dispensador inteligente de comida para mascotas - actualización local

## Estado actual de la implementación

Este repositorio ya cuenta con la base funcional en firmware y en captación visual. Se ha agregado una capa local de control y dashboard web para supervisar el sistema desde la red LAN sin depender de Internet.

### Cambios incluidos

- `backend/dashboard_server.py`: backend local con API REST para estado, capturas y galería.
- `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`: dashboard web responsive.
- `ESP32_CAM/Camara_ESP32CAM/Camara_ESP32CAM.ino`: se adiciona soporte de `/stream` sencillo para MJPEG.
- `docs/arquitectura_local.md`: descripción del backend local.
- `docs/conexiones_local.md`: resumen de seguridad y conexiones recomendadas.

## Cómo arrancar

```bash
cd Proyecto-Dispensador-IOT
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/dashboard_server.py
```

Abrir `http://localhost:8001` o la IP del equipo dentro de la LAN.

## Limitaciones de seguridad

La dispensación manual desde remoto queda deshabilitada por defecto. La operación debe autorizarse físicamente, validarse con nivel, batería, cooldown y seguridad del servo antes de activarla.

## Nota de validación

Los cambios estructurales no reemplazan ninguna prueba física del montaje real. Las conexiones de cámara, Wi‑Fi y servo deben verificarse en el hardware antes de considerarse operativos.
