# Dispensador inteligente de comida para mascotas — IoT local

Proyecto universitario para controlar y supervisar un dispensador de alimento mediante un ESP32 DevKit V1, sensores HC-SR04, un servo MG995, una ESP32-CAM AI-Thinker y un dashboard accesible en la red local.

> **Estado:** firmware, backend y dashboard implementados y probados **por software** (pruebas de lógica en PC, 24 pruebas del backend con dispositivos simulados y verificación manual del dashboard contra un simulador). **No se ha probado el hardware físico** (ambos firmwares sí compilan con `arduino-cli`): siga la lista de verificación de [`docs/conexiones_usbc.md`](docs/conexiones_usbc.md) antes de energizar. La dispensación desde la web está habilitada solo si define `TOKEN_DISPOSITIVO`.

## Funciones implementadas

- **ESP32:** control local de HC-SR04 y MG995 con máquina de estados; sigue funcionando sin Wi‑Fi (botón BOOT). Envía telemetría al backend, descubre al backend por UDP y acepta comandos con token.
- **ESP32-CAM:** `GET /status`, `GET /capture` (foto puntual) y `GET /stream` (MJPEG), independientes entre sí.
- **Backend (Python, solo biblioteca estándar):** telemetría, descubrimiento UDP, proxy de video, galería en disco, historial en SQLite, dispensación con validación y actualización en vivo por SSE.
- **Dashboard:** panel, cámara (video + captura manual/automática), galería (ver, descargar, eliminar con confirmación), control con confirmación e historial. Muestra *desconectado* en lugar de datos viejos.
- Credenciales y token se configuran en archivos locales que no se suben a GitHub.

> **Alcance funcional de esta rama:** el dashboard permite supervisar la telemetría, ver el flujo/capturar fotos y solicitar una dispensación manual confirmada. Esta rama **no integra el clasificador OpenCV perro/gato** del diseño anterior; tampoco activa la detección automática de presencia (`USAR_DETECCION_AUTOMATICA=0`). El sensor de nivel sí está contemplado. Por tanto, no debe presentarse como identificación automática de mascotas ni como dispensación autónoma por visión hasta integrar y probar ese flujo.

## Arquitectura

```text
ESP32 DevKit ── Wi‑Fi/LAN ──┐
                            ├── PC local: backend + dashboard ── navegador (PC/móvil/tablet)
ESP32-CAM ─── Wi‑Fi/LAN ───┘
ESP32: HC-SR04 + MG995 por GPIO
```

Sin Internet ni cloud. El dashboard se abre en `http://<IP-LAN-del-PC>:8001` (`localhost` solo sirve en el propio PC). Detalle y decisiones (SSE en lugar de WebSocket, descubrimiento UDP): [`docs/arquitectura_local.md`](docs/arquitectura_local.md).

## Componentes y exclusiones

ESP32 DevKit V1, ESP32-CAM AI-Thinker, servo MG995, HC-SR04 (nivel de tolva; segundo HC-SR04 para presencia solo si se habilita el modo automático), adaptador USB-C de 5 V ≥ 3 A, cable USB-C, protoboard/Dupont. **No forman parte del diseño:** panel solar, fusible, RC522, NFC.

### Advertencia eléctrica

El esquema en `Documentation/wiring/` y el manual de armado describen el montaje **anterior** (solar + batería 2S + fusible); no lo use para el montaje USB-C. El diseño vigente, con divisores calculados y distribución de 5 V, está en [`docs/conexiones_usbc.md`](docs/conexiones_usbc.md). Puntos críticos: el MG995 nunca se alimenta desde un GPIO ni desde la placa ESP32; el ECHO de 5 V pasa por divisor 1 kΩ/2 kΩ (3,33 V); GND común; la cámara exige 5 V estables. Sin fusible, la protección depende del adaptador. Si al mover el servo algo se reinicia, hace falta una segunda fuente de 5 V para el servo (solo GND compartido).

## Requisitos de software

- Python 3.10+ (solo biblioteca estándar para el servidor).
- Arduino IDE o PlatformIO; para las instrucciones y versiones probadas consulte [`ESP32/README.md`](ESP32/README.md).
- Red Wi-Fi de 2.4 GHz compatible con las placas.
- No se requiere Internet durante el funcionamiento, aunque la instalación inicial de herramientas puede necesitarlo.

## Instalación y configuración

1. Clonar y entrar al repositorio:

   ```bash
   git clone https://github.com/bryanramosing-ux/Proyecto-Dispensador-IOT.git
   cd Proyecto-Dispensador-IOT
   ```

2. Crear los `secrets.h` locales (no se versionan) y editar SSID, clave y token:

   ```bash
   cp ESP32/Dispensador_ESP32/secrets_ejemplo.h ESP32/Dispensador_ESP32/secrets.h
   cp ESP32_CAM/Camara_ESP32CAM/secrets_ejemplo.h ESP32_CAM/Camara_ESP32CAM/secrets.h
   python3 -c "import secrets; print(secrets.token_hex(8))"   # use este valor como token
   ```

   El mismo token va en `TOKEN_DISPOSITIVO` de `ESP32/.../secrets.h` y en `backend/.env`. Red Wi‑Fi de 2,4 GHz.

3. Configurar el backend:

   ```bash
   cp backend/.env.example backend/.env    # edite ESP32_CAM_URL y TOKEN_DISPOSITIVO
   ```

   Reserve en el router una IP para la ESP32-CAM y use la misma en `IP_CAMARA` (`ESP32_CAM/Camara_ESP32CAM/config.h`) y `ESP32_CAM_URL`. El ESP32 usa DHCP y descubre al backend solo; si su router bloquea el broadcast UDP, defina `URL_BACKEND` en su `secrets.h`.

4. Compilar y cargar los firmwares según [`ESP32/README.md`](ESP32/README.md) y [`ESP32_CAM/README.md`](ESP32_CAM/README.md), con la potencia (servo) desconectada la primera vez.

5. Iniciar el backend (Python 3.10+, sin dependencias):

   ```bash
   python3 backend/dashboard_server.py
   ```

   Abra `http://localhost:8001` en el PC o `http://<IP-LAN-del-PC>:8001` desde el móvil (permita el puerto 8001 y el UDP 41234 en el firewall). Para probar el dashboard sin hardware: `python3 backend/tests/simulador_dispositivos.py` (usa token `demo`; todo lo que muestra es **simulado**).

## Configuración del backend

Variables de `backend/.env` (ver `.env.example`): `ESP32_CAM_URL`, `TOKEN_DISPOSITIVO`, `HOST` (`0.0.0.0` LAN / `127.0.0.1` solo este PC), `PORT`, `PUERTO_DESCUBRIMIENTO`, `MAX_PORCIONES`, `MIN_DISPENSE_GAP_S`, `ESP32_URL` (respaldo). No exponga el puerto a Internet: no hay TLS ni inicio de sesión.

## API local

Resumen: telemetría (`/api/device/*`), `GET /api/status`, `GET /api/events` (SSE), `GET /api/camera/stream`, `POST /api/capture`, galería (`/api/gallery`), `POST /api/dispense`, `GET /api/history`, `POST /api/auto-capture`. Tabla completa, campos de la telemetría y medidas de seguridad en [`docs/arquitectura_local.md`](docs/arquitectura_local.md). Fotos e historial persisten en `backend/storage/` (no la borre si quiere conservarlos).

## Uso y límites funcionales

- **Dispensar:** pestaña *Control* → elegir porciones → *Dispensar…* → confirmar. Se rechaza si no hay token, el ESP32 está desconectado, ya hay una dispensación o rige el cooldown. Nunca se dispensa al abrir la página.
- **Foto:** pestaña *Cámara* → *Capturar fotografía* (o captura automática cada 30 s–15 min). Se guarda en la galería, donde puede verse, descargarse o eliminarse con confirmación.
- El video MJPEG de la ESP32-CAM va en sesiones de ~2 s que el backend reconecta sin que se note; la cámara atiende una petición a la vez, por lo que una captura con el video abierto puede tardar unos segundos y se recomienda un solo espectador a la vez.
- Los dispositivos desconectados se marcan tras 15 s sin telemetría; no se muestran sus valores anteriores como actuales.
- Valores de calibración (`PULSO_*_US`, `DIST_TOLVA_VACIA_CM`, dosis) en `config.h` son **provisionales** hasta medirlos en el montaje.

## Pruebas y validación

```bash
make -C ESP32/test_host                          # lógica del ESP32 (26+ escenarios, en PC)
python3 -I -m unittest discover -s backend/tests -v   # backend con ESP32/cámara simulados
```

Resultado de este entorno: lógica ESP32 OK; backend 24/24 OK; dashboard verificado en navegador contra el simulador (panel, video, captura, galería, dispensación con confirmación, caída del ESP32, móvil). Ambos firmwares compilan con la cadena de Espressif (`arduino-cli`, núcleo 3.0.7); la CI repite la compilación. Lista completa y distinción simulado/físico en [`docs/pruebas.md`](docs/pruebas.md).

## Documentación

- [Arquitectura local y API](docs/arquitectura_local.md)
- [Conexiones eléctricas USB-C (vigente)](docs/conexiones_usbc.md) · [notas previas](docs/conexiones_local.md)
- [Pruebas: simuladas vs. físicas](docs/pruebas.md)
- [Firmware ESP32](ESP32/README.md) · [Firmware ESP32-CAM](ESP32_CAM/README.md)
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
