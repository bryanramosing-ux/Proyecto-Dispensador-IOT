# Dispensador inteligente de comida para mascotas — IoT local

Proyecto universitario para controlar y supervisar un dispensador de alimento mediante un ESP32 DevKit V1, sensores HC-SR04, un servo MG995, una ESP32-CAM AI-Thinker y un dashboard accesible en la red local.

> **Estado importante:** la rama incluye firmware, una API local y un dashboard en desarrollo. No se puede prometer ausencia total de errores ni afirmar que el hardware está validado sin probarlo físicamente. El último CI conocido falló en el stub de pruebas de la ESP32-CAM; vuelva a ejecutar las Actions después de estos cambios. La dispensación desde la red permanece deshabilitada deliberadamente hasta validar el circuito, la calibración mecánica y los interbloqueos.

## Funciones implementadas

- El ESP32 controla el proceso local, HC-SR04 y MG995 con firmware modular; el control local no depende del dashboard.
- La ESP32-CAM expone endpoints HTTP de estado, captura JPEG y flujo MJPEG de duración limitada por conexión.
- El backend Python sirve el dashboard y agrega el estado de ambos dispositivos, captura y almacenamiento persistente local de fotos, galería, borrado validado e historial JSONL.
- El frontend muestra estados, nivel/distancia cuando están disponibles, cámara, capturas, galería, historial y operación manual (bloqueada de forma segura por defecto).
- Credenciales y direcciones de red se configuran localmente; no se deben subir credenciales reales.

## Arquitectura

```text
ESP32 DevKit ── Wi‑Fi/LAN ──┐
                            ├── PC local: backend + dashboard ── navegador
ESP32-CAM ─── Wi‑Fi/LAN ───┘
     └── /status, /capture, /stream
ESP32: HC-SR04 + MG995 conectados localmente
```

La comunicación básica no requiere cloud ni Internet. El PC, ESP32 y cámara deben estar en la misma red LAN. La dirección del dashboard debe ser la IP LAN del PC, por ejemplo `http://192.168.1.20:8001`; `localhost` solo funciona en el propio PC.

## Componentes y exclusiones

Componentes previstos: ESP32 DevKit V1, ESP32-CAM AI-Thinker (confirmar variante), servo MG995, uno o más HC-SR04, fuente(s) regulada(s) y cable USB-C según el montaje confirmado. No forman parte del diseño objetivo: panel solar, fusible, RC522 ni NFC.

### Advertencia eléctrica: no construir a partir de una suposición

La documentación eléctrica heredada del repositorio describe una instalación solar/batería/fusible y **no es el diseño final solicitado**. No conecte el montaje heredado como si fuera el esquema USB-C actualizado. Antes de reemplazarlo hacen falta el modelo y especificaciones de las fuentes disponibles, el montaje físico, el consumo/arranque del servo y la distribución de 5 V/6 V confirmada con mediciones. No se debe alimentar el MG995 desde un GPIO o desde el regulador de la placa; use una fuente regulada adecuada para el servo y GND común con el ESP32. El HC-SR04 tradicional puede emitir ECHO de 5 V: use divisor/adaptación de nivel y mida que el GPIO no supere su límite. La cámara requiere alimentación estable. Consulte [conexiones y restricciones](docs/conexiones_local.md) y no energice si no puede verificar el cableado con multímetro.

## Requisitos de software

- Python 3.10+ (solo biblioteca estándar para el servidor).
- Arduino IDE o PlatformIO; para las instrucciones y versiones probadas consulte [`ESP32/README.md`](ESP32/README.md).
- Red Wi-Fi de 2.4 GHz compatible con las placas.
- No se requiere Internet durante el funcionamiento, aunque la instalación inicial de herramientas puede necesitarlo.

## Instalación y configuración

1. Clonar el repositorio y cambiar a la rama que contiene esta implementación:

   ```bash
   git clone https://github.com/bryanramosing-ux/Proyecto-Dispensador-IOT.git
   cd Proyecto-Dispensador-IOT
   git checkout copilot/trabajo-asistente
   ```

2. Crear los archivos locales de credenciales, sin versionarlos:

   ```bash
   cp ESP32/Dispensador_ESP32/secrets_ejemplo.h ESP32/Dispensador_ESP32/secrets.h
   cp ESP32_CAM/Camara_ESP32CAM/secrets_ejemplo.h ESP32_CAM/Camara_ESP32CAM/secrets.h
   ```

   Editar los dos `secrets.h` con el SSID/clave Wi-Fi real. No publicar esos datos. Asegúrese de que ambas placas y el PC usan la misma LAN de 2.4 GHz.

3. Configurar IP reservada o estática en el router y actualizar las direcciones correspondientes en `ESP32/Dispensador_ESP32/config.h`, `ESP32_CAM/Camara_ESP32CAM/config.h` y `backend/.env` (copiar `.env.example`). Evite conflictos de IP; gateway y máscara deben coincidir con la red local.

4. Compilar/cargar los firmwares siguiendo [`ESP32/README.md`](ESP32/README.md) y [`ESP32_CAM/README.md`](ESP32_CAM/README.md). Cargue primero con el hardware de potencia desconectado cuando sea necesario; verifique el circuito antes de conectar servo o sensores.

5. Iniciar el dashboard:

   ```bash
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   cp backend/.env.example backend/.env
   python backend/dashboard_server.py
   ```

   El servidor carga variables desde el entorno y, si existe, desde `backend/.env`. Abra `http://localhost:8001` en el PC o `http://<IP-LAN-del-PC>:8001` desde otro dispositivo de la misma red.

## Configuración del backend

Variables en `backend/.env`:

| Variable | Predeterminado | Descripción |
|---|---|---|
| `ESP32_CAM_URL` | `http://192.168.1.51` | URL base de la cámara |
| `ESP32_URL` | `http://192.168.1.52` | URL base del ESP32 |
| `HOST` | `0.0.0.0` | Interfaz de escucha; para uso solo local, usar `127.0.0.1` |
| `PORT` | `8001` | Puerto HTTP del dashboard |

No exponga el puerto a Internet ni configure redirección de puertos en el router. El servidor HTTP local no proporciona autenticación ni TLS y debe usarse únicamente en una LAN confiable.

## API local

| Método y ruta | Función |
|---|---|
| `GET /api/health` | Health check y URL configuradas |
| `GET /api/status` | Consulta estados de cámara y ESP32; los errores indican que un dispositivo no respondió |
| `POST /api/capture` | Pide una nueva foto JPEG y la guarda localmente |
| `GET /api/gallery` | Lista capturas locales |
| `GET /api/gallery/<nombre>` | Muestra/descarga una captura JPEG validada |
| `DELETE /api/gallery/<nombre>` | Borra únicamente capturas generadas por el sistema |
| `GET /api/history` | Historial persistente de eventos recientes |
| `GET /api/camera/stream` | Proxy del flujo MJPEG de la cámara |
| `POST /api/dispense` | Rechazado (HTTP 501) hasta validación y autorización de seguridad |

Las capturas e historial se guardan bajo `backend/storage/` y sobreviven al reinicio del proceso. No elimine esa carpeta si desea conservarlos.

## Uso y límites funcionales

- El dashboard actualiza periódicamente el estado; no se debe interpretar un dato con error o desconectado como estado actual válido.
- La transmisión de cámara está implementada como sesiones MJPEG de duración limitada que el dashboard vuelve a solicitar. No equivale a un servicio de streaming probado con múltiples clientes y el servidor integrado `WebServer` de la cámara puede atender una petición a la vez.
- Captura manual guarda una foto nueva; la galería permite visualizar, descargar y eliminar después de confirmación.
- La dispensación remota no está habilitada. Solo se debe habilitar en una futura revisión después de incorporar controles en el firmware y verificar sensor, nivel, cooldown, fallos del servo y presencia/seguridad de la mascota. No se active por cambiar solo el frontend.
- La captura automática configurable desde dashboard y WebSockets no están implementados en esta entrega.

## Pruebas y validación

Pruebas que se pueden ejecutar sin hardware:

```bash
make -C ESP32/test_host
# Requiere clonar ArduinoJson a ESP32/test_host/ArduinoJson (ver ESP32/README.md)
make -C ESP32/test_host sintaxis
python -m unittest discover -s backend/tests -v
```

La CI también compila firmware para Arduino-ESP32 2.x/3.x, ejecuta lógica, verifica geometría/documentación y otras pruebas. Consulte la pestaña **Actions**; una ejecución correcta no valida la electrónica física ni Wi-Fi.

Antes de la demostración real, validar bajo supervisión y registrar resultados: tensión de alimentación en reposo y durante movimiento del servo, corriente y temperatura, ECHO tras divisor, reinicios/brownout, distancia y calibración del nivel, recorrido mecánico, cámara/MJPEG, pérdida y recuperación de Wi-Fi, reinicio de backend y funcionamiento desde un teléfono. No declarar hardware aprobado hasta completar estas comprobaciones.

## Documentación

- [Arquitectura local](docs/arquitectura_local.md)
- [Conexiones, riesgos y datos pendientes para el esquema USB-C](docs/conexiones_local.md)
- [Firmware ESP32](ESP32/README.md)
- [Firmware ESP32-CAM](ESP32_CAM/README.md)
- [Auditoría de integración](Documentation/auditoria_integracion_local.md)

## Solución de problemas

- **Dashboard inaccesible en móvil:** usar IP LAN del PC, confirmar misma red y permitir el puerto TCP configurado en el firewall local.
- **Dispositivo offline:** verificar SSID 2.4 GHz, clave local, IP/gateway/máscara y que no haya conflicto de direcciones.
- **ESP32-CAM reinicia:** comprobar fuente estable, cableado corto y caída de tensión; no desactivar el detector de brownout.
- **Captura/stream falla:** consultar `GET /status`, verificar la IP y volver a cargar la cámara; no asumir que la página prueba la cámara física.
- **Servo reinicia el ESP32:** desconectar la alimentación y revisar fuente independiente/regulada, GND común y caída de tensión; no seguir probando hasta corregirlo.
- **Fotos no persisten:** revisar permisos de escritura en `backend/storage/` y espacio disponible.

## Alcance no verificado

No se ha podido probar desde este entorno el hardware conectado, la estabilidad RF, la medición real de energía, la precisión de nivel, el movimiento bajo carga, la calidad de vídeo ni la seguridad del montaje final. El objetivo “cero errores” no puede garantizarse; se requiere ejecutar CI y las pruebas físicas descritas, corregir cualquier fallo observado y documentar el resultado.
