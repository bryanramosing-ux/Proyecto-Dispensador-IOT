> En el montaje USB-C manual el proceso principal es `backend/dashboard_server.py`.
> Para iniciarlo automáticamente, sustituir ExecStart por ese archivo y usar el
> directorio raíz del repositorio. OpenCV es opcional y usa puerto 8000; el backend
> manual usa 8001. Su configuración se lee de `backend/.env`.

# Arranque continuo del servidor de visión

Primero completar la [puesta en marcha](../calibration/calibracion.md). El servidor
Python debe ejecutarse en un PC conectado a la misma LAN que las placas. Desactivar
la suspensión automática de ese PC mientras esté alimentando animales. Reservar su
IP en el router y mantener el puerto 8000 permitido para la red local.

`OpenCV/iniciar.py` carga `OpenCV/dispensador.env` y acepta todos los argumentos de
`servidor_vision.py`; las variables ya presentes en el entorno tienen prioridad.

## Linux (systemd)

Crear la venv en `OpenCV/.venv`, instalar dependencias y modelo. Copiar
`dispensador-vision.service.example` a una unidad de usuario en
`~/.config/systemd/user/dispensador-vision.service`, sustituyendo ambas rutas
`/RUTA/AL/REPOSITORIO` por la ruta absoluta real. Después:

```sh
systemctl --user daemon-reload
systemctl --user enable --now dispensador-vision
journalctl --user -u dispensador-vision -f
```

Esto arranca con la sesión del usuario y reinicia el proceso si falla. Para arrancar
sin inicio de sesión, el administrador debe habilitar la permanencia de ese usuario
(`loginctl enable-linger USUARIO`). Las credenciales y la instalación de la unidad
son propias de cada equipo; no se incluyen credenciales en el repositorio.

## Windows (Programador de tareas)

Crear una tarea con desencadenador «Al iniciar sesión» para el usuario del PC.
Programa: ruta absoluta a `OpenCV\.venv\Scripts\python.exe`.
Argumentos: ruta absoluta entre comillas a `OpenCV\iniciar.py`.
Directorio «Iniciar en»: carpeta absoluta `OpenCV`.
Activar reinicio ante fallo, una sola instancia y desactivar el límite de duración.
Si se necesita funcionar sin sesión, configurar la tarea con el usuario adecuado y
comprobar que puede acceder a la red y a los archivos.

## Datos y mantenimiento

Se conservan como máximo `DISPENSADOR_MAX_CAPTURAS` JPEG (1000 por defecto).
Los errores de disco se registran y no cambian una clasificación ya calculada.
Las alertas y el panel tienen historial limitado en memoria; no son un registro
persistente de gramos entregados. El límite de alimentación se conserva en la NVS
del ESP32, no en el PC. Verificar espacio libre, registros y funcionamiento tras
reiniciar el PC y las placas. `comprobar_instalacion.py --red` consulta salud sin
alimentar ni pedir una clasificación.
