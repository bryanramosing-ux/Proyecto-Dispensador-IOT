# Manual de montaje — versión USB-C simplificada

**Versión vigente de trabajo.** Reemplaza las instrucciones anteriores que incluían panel solar, baterías 18650, BMS, convertidores de carga y fusible del diseño solar.

> **Seguridad:** este montaje requiere validación física. No conecte la fuente hasta revisar polaridad, continuidad y tensiones con multímetro. No alimente el MG995 desde un GPIO, desde 3,3 V ni desde el regulador de la placa ESP32. No use el puerto USB de un computador para alimentar el conjunto con el servo conectado.

## 1. Arquitectura vigente

- ESP32 DevKit V1: controlador principal.
- ESP32-CAM AI-Thinker con OV2640 y PSRAM: captura y transmisión MJPEG por Wi-Fi.
- Un HC-SR04: medición del nivel de alimento en la tolva.
- Un servomotor MG995 posicional de 180°: mecanismo dosificador.
- PC/notebook en la misma red Wi-Fi: backend local y dashboard.
- Fuente regulada de 5 V; recomendación inicial de 5 A continuos y distribución separada para servo y lógica.

La detección automática de presencia y la clasificación OpenCV perro/gato **no están activadas en esta rama**. El control del dashboard es manual y requiere confirmación. El sensor de presencia opcional permanece desactivado (USAR_DETECCION_AUTOMATICA=0).

## 2. Componentes

Consulte la [lista de materiales vigente](../components/lista_materiales.csv). No compre componentes marcados como excluidos. La cámara 5110V0 mostrada por el usuario no está identificada y no debe conectarse ni sustituir la ESP32-CAM.

## 3. Alimentación y distribución

1. Use una fuente regulada y certificada de 5 V, recomendación inicial 5 A continuos. Verifique etiqueta, polaridad, conector y capacidad real.
2. Lleve la alimentación a una distribución en estrella:
   - Rama lógica: ESP32 DevKit y ESP32-CAM con 5 V estables.
   - Rama servo: alimentación de potencia con cable corto y calibre apropiado (AWG 20 recomendado para tramo corto).
3. Una las tierras (GND) de ambas ramas en un punto común. La señal PWM necesita esa referencia.
4. Coloque un condensador electrolítico de 1000–2200 µF (tensión nominal mínima 10 V) cerca del conector del MG995, respetando polaridad.
5. Cerca de la ESP32-CAM coloque 470 µF y 100 nF entre 5 V y GND.
6. No conecte simultáneamente fuentes de 5 V distintas a VIN y al USB de la placa. Para programar por USB, desconecte primero la alimentación externa salvo que se haya verificado el aislamiento de alimentación de esa placa.
7. La exclusión del fusible no elimina el riesgo eléctrico. Use una fuente con protección contra sobrecorriente, cableado aislado y pruebas supervisadas. Ante calentamiento, olor, ruido eléctrico o reinicios, desconecte inmediatamente.

**Importante sobre el MG995:** la tensión admitida depende de la variante y suele estar alrededor de 4,8–7,2 V. Este documento contempla un riel de 5 V; a 5 V puede entregar menos par que a 6 V. Si el mecanismo no funciona con carga, no aumente la tensión sin verificar la ficha del servo y rediseñar la fuente.

## 4. Conexiones de señales

### HC-SR04 de nivel

| HC-SR04 | ESP32 DevKit V1 | Observación |
|---|---|---|
| VCC | 5 V de la rama lógica | No usar 3,3 V salvo que el modelo lo permita |
| GND | GND común | Tierra compartida |
| TRIG | GPIO19 | Según config.h |
| ECHO | GPIO21 mediante divisor 1 kΩ/2 kΩ | Nunca conectar ECHO de 5 V directamente al ESP32 |

Divisor: ECHO del sensor → resistencia 1 kΩ → nodo GPIO21; desde ese nodo resistencia 2 kΩ → GND. Mida la tensión del nodo antes de conectarlo al GPIO.

### MG995

| Cable servo (verificar colores del fabricante) | Conexión |
|---|---|
| Rojo | +5 V de la rama de potencia |
| Marrón/negro | GND de la rama de servo y GND común |
| Naranja/amarillo | GPIO25 mediante resistencia serie de 330 Ω |

Añada una resistencia de 10 kΩ entre señal y GND como pull-down. No haga circular la corriente del motor por la protoboard.

### ESP32-CAM

- Alimentar por el pin 5V y GND con una rama estable.
- No conectar sus GPIO al ESP32 DevKit: la comunicación entre placas es por Wi-Fi.
- No reutilizar pines de cámara para periféricos.
- Para programar, usar ESP32-CAM-MB o adaptador USB-TTL con UART de 3,3 V y procedimiento de arranque correcto.

## 5. Red local y software

1. Conecte ESP32 DevKit, ESP32-CAM y PC a la misma red Wi-Fi de 2,4 GHz.
2. Configure credenciales en los archivos locales secrets.h; no publique contraseñas ni tokens.
3. Reserve/defina una IP estable para ESP32-CAM y configure la misma dirección en firmware y backend.
4. Cargue ambos firmwares siguiendo los README de ESP32/ y ESP32_CAM/.
5. Inicie el backend desde la raíz: python3 backend/dashboard_server.py.
6. Abra http://localhost:8001 en el PC o http://IP-LAN-DEL-PC:8001 desde otro equipo de la misma red.

El dashboard muestra telemetría, cámara MJPEG, capturas, galería, historial y control manual confirmado. No representa clasificación automática perro/gato en esta versión.

## 6. Secuencia de puesta en marcha

1. Con todo desconectado, inspeccione polaridad, terminales y aislamiento.
2. Compruebe continuidad: no debe existir cortocircuito entre 5 V y GND.
3. Energice únicamente la rama lógica, sin servo conectado. Mida 5 V y compruebe que ambas placas arrancan y se conectan a Wi-Fi.
4. Compruebe /status, captura JPEG y stream de ESP32-CAM.
5. Compruebe el HC-SR04: mida el nodo ECHO del divisor y compare distancias conocidas. Calibre tolva vacía y llena.
6. Con la fuente apagada, conecte el MG995. Verifique alimentación directa desde la rama de potencia y GND común.
7. Pruebe el servo sin alimento y sin acoplarlo al mecanismo. Use movimientos pequeños y detenga ante topes, vibración o calentamiento.
8. Calibre las posiciones del disco y pruebe primero con pocas croquetas, pesando cada porción.
9. Observe tensión de 5 V durante el movimiento. Si hay caída, reinicios o comportamiento errático, desconecte y corrija la alimentación.
10. Pruebe dashboard, cámara, galería, desconexión Wi-Fi y recuperación.

## 7. Límites conocidos

- No se ha validado el hardware físico ni la dosificación con alimento.
- Los parámetros de distancia, porcentaje de tolva, pulsos del servo y tamaño de porción son provisionales hasta calibrarlos.
- El firmware actual tiene detección automática desactivada y un único sensor de nivel habilitado.
- OpenCV existe en el repositorio, pero no está integrado en el flujo activo de esta rama.
- El modelo de cámara 5110V0 no está confirmado; no conectarlo.
- Sin fusible, la fuente y la instalación deben proporcionar protección apropiada; no presentar el montaje como seguro hasta revisarlo y medirlo.

## 8. Archivos de referencia

- [Lista de materiales](../components/lista_materiales.csv)
- [Conexiones eléctricas USB-C](../../docs/conexiones_usbc.md)
- [Arquitectura local](../../docs/arquitectura_local.md)
- [Plan de impresión](../../Mechanical/plan_impresion.md)
- [Firmware ESP32](../../ESP32/README.md)
- [Firmware ESP32-CAM](../../ESP32_CAM/README.md)
