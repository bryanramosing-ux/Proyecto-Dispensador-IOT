# Dispensador inteligente de comida para mascotas — prototipo IoT local

Proyecto universitario de prototipado de un dispensador de alimento con control local, sensores, servomotor, cámara y dashboard web en una red Wi-Fi local.

> **Estado del repositorio:** esta rama contiene firmware ESP32, firmware ESP32-CAM, backend Python y dashboard web. Las pruebas automatizadas y de simulación no sustituyen la validación del circuito físico. No se debe afirmar que el montaje está listo para uso con mascotas hasta completar las pruebas eléctricas, mecánicas y de dosificación descritas en este repositorio.

## 1. Configuración vigente del prototipo

| Elemento | Cantidad | Función | Estado |
|---|---:|---|---|
| ESP32 DevKit V1 | 1 | Control del sensor, servo, Wi-Fi y telemetría | Parte del diseño |
| ESP32-CAM AI-Thinker + OV2640 + PSRAM | 1 | Capturas y stream MJPEG en la LAN | Parte del diseño; confirmar módulo físico |
| HC-SR04 | 2 | Uno mide nivel de alimento en tolva y otro detecta presencia de mascota | Nivel activo; automatización de presencia pendiente de validación |
| MG995 posicional 180° | 1 | Accionamiento del disco dosificador | Parte del diseño; calibración pendiente |
| Fuente regulada de 5 V | 1 | Alimentación del conjunto | Requiere verificar capacidad y distribución |
| PC/notebook | 1 | Backend, almacenamiento y dashboard | Necesario para el servidor local |
| Router/AP Wi-Fi 2,4 GHz | 1 | Red local entre placas y PC | Necesario para comunicación |

Lista detallada, cantidades de pasivos y elementos de montaje: [Documentation/components/lista_materiales.csv](Documentation/components/lista_materiales.csv).

### Elementos excluidos de esta versión

No comprar ni instalar para el prototipo actual: panel solar, baterías 18650, BMS 2S, cargador 2S, MT3608, convertidores del sistema solar, estación solar remota, fusible del esquema anterior, RC522, etiquetas NFC, PIR.

La cámara marcada por el usuario como “5110V0” aún no está identificada. No conectarla ni asumir que reemplaza a la ESP32-CAM AI-Thinker.

## 2. Alcance funcional real

- **ESP32 DevKit:** lee el HC-SR04 de nivel; el segundo sensor de presencia está previsto en GPIO26/34, pero el modo automático requiere validación. Controla el MG995, mantiene una máquina de estados y envía telemetría al backend. La dispensación manual se puede solicitar desde el dashboard con confirmación y token.
- **ESP32-CAM:** implementa `GET /status`, `GET /capture` y `GET /stream` (MJPEG de duración limitada por petición).
- **Backend:** recibe telemetría, guarda historial y fotografías, expone API local, reenvía comandos autorizados y sirve eventos SSE.
- **Dashboard:** muestra estado, nivel, cámara, galería, historial y control manual confirmado.

**Funciones no activas en esta rama:** detección automática de presencia (`USAR_DETECCION_AUTOMATICA=0`) y clasificación automática perro/gato con OpenCV. Aunque existe código de OpenCV y configuración histórica en `OpenCV/`, no forma parte del flujo de ejecución activo del dashboard/firmware de esta rama. No presentar el prototipo como identificador automático de mascotas ni como dispensador autónomo por visión.

## 3. Arquitectura

```text
ESP32 DevKit ── Wi-Fi ──┐
                        ├── Router/AP local ── PC: backend + dashboard ── navegador
ESP32-CAM ───── Wi-Fi ──┘

ESP32 DevKit GPIO:
  HC-SR04 de nivel (GPIO19/21) + HC-SR04 de presencia (GPIO26/34) + señal PWM MG995
```

El funcionamiento de supervisión es local, sin depender de servicios cloud. El PC debe permanecer encendido para alojar el dashboard, guardar fotos e historial y recibir telemetría. La dispensación local por botón/firmware tiene un comportamiento independiente que debe comprobarse en las pruebas.

Detalles: [docs/arquitectura_local.md](docs/arquitectura_local.md).

## 4. Alimentación y seguridad eléctrica

La versión actual elimina el subsistema solar y de batería. **Decisión de alcance:** se instalan DOS HC-SR04: nivel de tolva y presencia de mascota. El firmware mantiene deshabilitada la automatización hasta completar las pruebas de presencia, clasificación y dosificación; instalar el sensor no significa que la detección automática esté activa. La arquitectura eléctrica de referencia para las pruebas de laboratorio es [docs/manual_instrucciones_conexiones.md](docs/manual_instrucciones_conexiones.md). Los documentos [docs/conexiones_usbc.md](docs/conexiones_usbc.md) y [Documentation/manual_armado/Manual_de_Armado.md](Documentation/manual_armado/Manual_de_Armado.md) deben leerse conforme a esa arquitectura y no como permiso para unir fuentes de 5 V.

Puntos obligatorios:

1. El USB del PC alimenta únicamente el ESP32 DevKit y, si se verifica su capacidad, los dos HC-SR04. El MG995 y la ESP32-CAM utilizan la fuente externa de 5 V; jamás alimentar el servo desde el puerto USB del PC.
2. Usar una fuente regulada de 5 V con capacidad suficiente y protección contra sobrecorriente. La recomendación inicial de 5 A debe cotejarse con la fuente y las corrientes reales del servo/cámara.
3. Alimentar el MG995 por una rama de potencia adecuada; nunca desde GPIO ni desde el regulador de la placa ESP32.
4. Mantener GND común entre servo, ESP32, cámara y ambos sensores.
5. Cada ECHO de 5 V requiere su propio divisor 1 kΩ/2 kΩ: nivel a GPIO21 y presencia a GPIO34. Los TRIG van a GPIO19 y GPIO26 respectivamente.
6. No conectar simultáneamente USB del PC y alimentación externa a la placa sin verificar el aislamiento de alimentación.
7. La exclusión del fusible no elimina el riesgo. No energizar hasta revisar polaridad, continuidad y tensiones con multímetro.

El montaje no ha sido validado físicamente. No se afirma que una fuente o cable concreto del inventario del usuario sea adecuado hasta leer sus etiquetas y comprobar su capacidad.

## 5. Software necesario

- Python 3.10 o superior para backend (biblioteca estándar).
- Arduino IDE o PlatformIO para firmware.
- Núcleo Arduino-ESP32 y librerías según [ESP32/README.md](ESP32/README.md) y [ESP32_CAM/README.md](ESP32_CAM/README.md).
- Wi-Fi de 2,4 GHz.
- Navegador moderno en PC/móvil conectado a la misma LAN.

## 6. Instalación

Clonar:

```bash
git clone https://github.com/bryanramosing-ux/Proyecto-Dispensador-IOT.git
cd Proyecto-Dispensador-IOT
```

Crear los archivos locales de credenciales (no subirlos a GitHub):

```bash
cp ESP32/Dispensador_ESP32/secrets_ejemplo.h ESP32/Dispensador_ESP32/secrets.h
cp ESP32_CAM/Camara_ESP32CAM/secrets_ejemplo.h ESP32_CAM/Camara_ESP32CAM/secrets.h
cp backend/.env.example backend/.env
```

Completar SSID, contraseña, IP de cámara y token compartido según los comentarios de cada archivo. Mantener secretos fuera del control de versiones.

Compilar y cargar los firmwares siguiendo sus respectivos README. Al hacer la primera puesta en marcha, mantener desconectada la potencia del servo.

Iniciar el backend desde la raíz:

```bash
python3 backend/dashboard_server.py
```

Abrir `http://localhost:8001` en el PC o `http://IP-LAN-DEL-PC:8001` desde otro equipo de la misma red. No exponer el servidor directamente a Internet; no implementa TLS ni autenticación de usuario completa.

## 7. Funciones del dashboard

- Estado y telemetría del ESP32.
- Nivel de alimento calculado a partir del HC-SR04.
- Stream MJPEG y captura puntual de la ESP32-CAM.
- Galería local de fotografías.
- Historial de eventos.
- Solicitud de dispensación manual con confirmación y validación del dispositivo.

El stream y la captura comparten el recurso de cámara; una captura puede esperar mientras se atiende el stream. La disponibilidad real depende de la alimentación, Wi-Fi y hardware físico.

## 8. Pruebas

Backend:

```bash
python3 -I -m unittest discover -s backend/tests -v
```

Lógica de firmware en host:

```bash
make -C ESP32/test_host
```

Revisar [docs/pruebas.md](docs/pruebas.md). Antes de conectar alimento o permitir uso real, completar pruebas físicas de:
- tensión en vacío y durante movimiento del servo;
- corriente y temperatura de fuente, cables y servo;
- niveles lógicos del divisor ECHO;
- captura y stream con ESP32-CAM real;
- medición del nivel en tolva vacía/llena y detección de presencia con el segundo HC-SR04;
- calibración del MG995 y masa real por porción;
- respuesta ante desconexión Wi-Fi y reinicios.

## 9. Documentación vigente y heredada

- [Lista de materiales vigente](Documentation/components/lista_materiales.csv)
- [Manual de montaje con USB del PC y fuente externa](Documentation/manual_armado/Manual_de_Armado.md)
- [Conexiones eléctricas de laboratorio](docs/conexiones_usbc.md)
- [Manual de instrucciones de conexiones (Markdown)](docs/manual_instrucciones_conexiones.md)
- [Arquitectura local y API](docs/arquitectura_local.md)
- [Pruebas y validación](docs/pruebas.md)
- [Firmware ESP32](ESP32/README.md)
- [Firmware ESP32-CAM](ESP32_CAM/README.md)
- [Mecánica e impresión 3D](Mechanical/README.md)

Los esquemas, manual PDF, video, piezas STL y plan de impresión originales pueden contener el diseño solar/batería de una versión anterior. Se conservan como antecedentes, no como instrucciones vigentes. No usar un PDF o video antiguo para cablear o comprar componentes sin revisar primero la documentación USB-C actualizada.

## 10. Limitaciones y estado de validación

No se ha demostrado en esta revisión el funcionamiento del hardware físico, el rendimiento de la fuente concreta, la estabilidad de la cámara en stream continuo, la precisión de la medición de tolva, la cantidad de alimento dispensada ni la seguridad del mecanismo con mascotas. Las pruebas de software/simulación no prueban esos aspectos. La clasificación OpenCV automática queda pendiente de integración y pruebas antes de poder declararla función implementada.

## Correcciones de funcionamiento y comprobaciones

El firmware guarda cada intento de alimentación antes de mover el motor y conserva
los límites tras reiniciar. Un fallo PWM o de almacenamiento bloquea la entrega.
El modo predeterminado es doméstico. Los diagramas SVG y la lista de cables se
generan para el montaje USB-C real desde los GPIO activos; las pruebas del dashboard
HTTP, del dosificador y del historial se ejecutan en GitHub Actions.

La [guía de calibración](Documentation/calibration/calibracion.md) incluye el acta
para las medidas físicas pendientes. Las pruebas automáticas no certifican gramos,
consumo, exactitud del nivel ni movimiento físico del MG995.
