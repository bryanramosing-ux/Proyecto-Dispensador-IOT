# Manual de instrucciones de conexiones

**Proyecto:** Dispensador inteligente de comida para mascotas — prototipo IoT  
**Formato:** documentación Markdown  
**Estado:** guía preliminar; confirmar modelos y fuente reales antes de energizar.

> Este manual describe el montaje de laboratorio previsto para probar primero la electrónica sobre una mesa y adaptar después el conjunto a las piezas impresas en 3D. No reemplaza la revisión de las etiquetas de las placas, el esquema del fabricante ni las mediciones con multímetro. No conectar la alimentación hasta completar las verificaciones de la sección 10.

## 1. Arquitectura de alimentación

Se contemplan dos alimentaciones separadas:

1. **Computador → cable USB → ESP32 DevKit V1.** Alimenta y permite programar el DevKit.
2. **Fuente regulada de laboratorio de 5 V → dos ramas de potencia:** una para la ESP32-CAM y otra para el servo MG995.

El HC-SR04 se alimenta desde el pin de 5 V del DevKit, si la placa y su alimentación USB lo permiten. Todos los módulos deben compartir una referencia GND común.

**Importante:** el MG995 no se alimenta desde el pin 3V3, el regulador del ESP32, el puerto USB del computador ni las pistas de alimentación de la protoboard. Su corriente debe circular por cables adecuados y una bornera o distribución de potencia. La protoboard se reserva para señales y conexiones de baja corriente.

La fuente de laboratorio debe tener capacidad suficiente para los picos de corriente del MG995 y el consumo de la cámara. No asumir que una fuente de 5 V es adecuada solo por su voltaje nominal: verificar su corriente máxima, protección, cables y caída de tensión durante las pruebas.

## 2. Componentes previstos

- ESP32 DevKit V1 (confirmar variante y etiquetas de pines).
- ESP32-CAM compatible con el firmware; la configuración prevista es AI-Thinker con OV2640 y PSRAM. Confirmar el módulo físico antes de conectarlo.
- Sensor ultrasónico HC-SR04.
- Servomotor MG995.
- Fuente regulada de laboratorio con salida de 5 V.
- Protoboard para señales y distribución de GND de baja corriente.
- Cable USB del tipo que corresponda al conector real del DevKit (USB-C o micro-USB).
- Resistencias de 1 kΩ y 2 kΩ para el divisor ECHO.
- Resistencia serie de 220–330 Ω para la señal del servo.
- Resistencia de 10 kΩ entre señal del servo y GND como pull-down opcional, si el circuito/firmware lo requiere.
- Condensador electrolítico de 1000–2200 µF cerca de la alimentación del servo, con tensión nominal adecuada y polaridad correcta.
- Multímetro, cables de potencia adecuados y bornera/conector de distribución.

## 3. Distribución general

```text
COMPUTADOR
   │ USB
   ▼
ESP32 DevKit V1
   ├── 5V ─────────────── HC-SR04 VCC
   ├── GND ────────────── HC-SR04 GND
   ├── GPIO19 ─────────── HC-SR04 TRIG
   ├── GPIO21 ◄────────── HC-SR04 ECHO (divisor 1kΩ/2kΩ)
   └── GPIO25 ─────────── señal MG995 (resistencia serie)

FUENTE REGULABLE (ajustada y medida a 5,0 V)
   ├── +5V ────────────── ESP32-CAM pin 5V (si el modelo lo admite)
   ├── GND ────────────── ESP32-CAM GND
   ├── +5V ────────────── MG995 alimentación positiva
   └── GND ────────────── MG995 GND

GND de la fuente ──────── GND del ESP32 DevKit (tierra común)
ESP32 DevKit ⇄ ESP32-CAM: comunicación por Wi-Fi; no unir GPIO entre placas.
```

El positivo de la fuente externa **no** se conecta al pin 5V/VIN del DevKit mientras el DevKit está alimentado por USB. En esta arquitectura, el DevKit se alimenta únicamente por el cable USB.

## 4. ESP32 DevKit V1 y conexión al computador

Conecta el cable USB al conector real de la placa y al computador. El USB alimenta el DevKit y permite cargar el firmware y usar el monitor serial.

| Pin del DevKit | Conexión prevista |
|---|---|
| GPIO19 | TRIG del HC-SR04 |
| GPIO21 | ECHO del HC-SR04, después del divisor resistivo |
| GPIO25 | Señal PWM del MG995, mediante resistencia serie de 220–330 Ω |
| GND | GND común |
| 5V/VIN (según serigrafía) | Alimentación de VCC del HC-SR04, si la placa entrega 5 V desde USB |

Los pines anteriores corresponden a la asignación prevista por el firmware de esta rama. Confirma la serigrafía y el modelo de tu DevKit: no todas las placas tienen el mismo formato ni el mismo pinout. No apliques 5 V a ningún GPIO.

## 5. Sensor ultrasónico HC-SR04

| HC-SR04 | Conectar a |
|---|---|
| VCC | 5 V del DevKit |
| GND | GND del DevKit |
| TRIG | GPIO19 |
| ECHO | GPIO21 mediante divisor resistivo |

### Divisor de tensión obligatorio para ECHO

El ECHO del HC-SR04 puede entregar una señal de 5 V; el ESP32 utiliza lógica de 3,3 V. No conectes ECHO directamente al GPIO.

Cableado del divisor:

1. ECHO del HC-SR04 → resistencia de **1 kΩ**.
2. El otro extremo de 1 kΩ → nodo de señal que va a **GPIO21**.
3. Desde ese mismo nodo → resistencia de **2 kΩ**.
4. El otro extremo de 2 kΩ → GND.

Con 5 V de entrada, el nodo entrega aproximadamente 3,3 V. Mantén GND del sensor unido a GND del DevKit.

## 6. Servomotor MG995

Los colores habituales son rojo (positivo), marrón/negro (GND) y naranja/amarillo/blanco (señal), pero verifica el cableado de tu unidad.

| Cable del MG995 | Conexión |
|---|---|
| Positivo (habitualmente rojo) | +5 V de la fuente externa, por cable de potencia |
| GND (habitualmente marrón/negro) | GND de la fuente externa |
| Señal (habitualmente naranja/amarillo/blanco) | GPIO25 a través de resistencia serie de 220–330 Ω |

Requisitos:

- Unir el GND de la fuente externa con el GND del DevKit para que la señal PWM tenga referencia común.
- Llevar el positivo y GND del servo directamente desde la distribución de potencia mediante cables adecuados. No pasar la corriente del servo por la protoboard.
- Colocar, si corresponde, un condensador de 1000–2200 µF cerca del servo, respetando polaridad y tensión nominal.
- Una resistencia de 10 kΩ entre señal y GND puede utilizarse como pull-down para evitar activaciones espurias durante el arranque, siempre que sea compatible con el circuito.
- Probar inicialmente sin carga mecánica y con movimientos pequeños. No bloquear el eje ni forzar el mecanismo.

No se fija aquí un límite de corriente universal para la fuente: debe definirse según las especificaciones de la fuente y el consumo real del servo. Vigila caídas de tensión, calentamiento y reinicios del microcontrolador.

## 7. ESP32-CAM

La configuración de software prevista para esta rama es ESP32-CAM AI-Thinker con OV2640 y PSRAM. No conectar una placa identificada únicamente como “5110V0” hasta confirmar su modelo, pinout y compatibilidad.

| ESP32-CAM | Conexión prevista |
|---|---|
| 5V | +5 V regulados de la fuente externa, solo si la placa confirma que ese pin es entrada de 5 V |
| GND | GND de la fuente y GND común |

- Comprueba la polaridad y mide 5,0 V antes de conectar la placa.
- Usa cables cortos y adecuados; evita caídas de tensión.
- No conectes periféricos a los GPIO utilizados internamente por la cámara.
- La comunicación con el DevKit es por Wi-Fi; no se conectan entre sí sus GPIO para intercambiar datos.
- Para programar la ESP32-CAM puede requerirse un adaptador ESP32-CAM-MB o un USB-TTL. En este último caso, TX del adaptador va a U0R/RX de la cámara y RX del adaptador a U0T/TX de la cámara; GND común. El modo de programación suele requerir GPIO0 conectado a GND durante el arranque de carga, según el módulo.
- No conectes simultáneamente el 5 V del USB-TTL y la fuente externa a la misma placa, salvo que el adaptador esté diseñado para ello y se haya verificado el aislamiento.

## 8. Uso de la protoboard

La protoboard puede utilizarse para:

- Montar el divisor resistivo del ECHO.
- Distribuir señales de baja corriente.
- Facilitar conexiones GND de referencia.

No la utilices para transportar la corriente de alimentación del MG995. Usa una bornera, distribución de potencia o cables directos apropiados. Comprueba con multímetro la continuidad de los rieles: algunas protoboards tienen rieles partidos en el centro.

## 9. Secuencia de armado y pruebas

1. **Inspección sin alimentación:** identifica los modelos exactos, revisa etiquetas, polaridad, cables y continuidad. Comprueba que no existan cortocircuitos.
2. **DevKit solo:** conecta USB al computador, verifica que encienda y carga un programa básico. Comprueba el puerto serie.
3. **HC-SR04:** desconecta USB, realiza el cableado y revisa el divisor ECHO. Vuelve a conectar USB y valida las lecturas de distancia.
4. **ESP32-CAM:** con la salida de fuente desactivada, conecta 5V y GND tras confirmar el pinout. Ajusta y mide 5,0 V; activa la fuente y prueba el inicio, captura y stream por Wi-Fi.
5. **MG995:** deja el servo sin carga. Verifica el voltaje y la polaridad; conecta su potencia directamente a la rama externa y su señal a GPIO25. Prueba movimientos pequeños y observa el consumo, la tensión y la temperatura.
6. **Integración:** une las tierras (GND), comprueba la comunicación Wi-Fi y prueba sensor, cámara y servo en conjunto.
7. **Dosificación:** calibra el movimiento y mide con una balanza la masa entregada por ciclo. Hazlo sin mascotas cerca del mecanismo.
8. **Registro:** documenta voltajes, corriente observada, reinicios, temperatura, distancia y masa dispensada antes de adaptar el prototipo a las piezas STL.

## 10. Verificaciones obligatorias antes de energizar

- [ ] Confirmar el modelo exacto del ESP32 DevKit y la etiqueta de sus pines.
- [ ] Confirmar el modelo exacto de ESP32-CAM y que su entrada de alimentación admite 5 V.
- [ ] Leer la etiqueta de la fuente: tensión, corriente máxima y protecciones.
- [ ] Ajustar la fuente a 5,0 V y verificarla con multímetro antes de conectar las placas.
- [ ] Confirmar la polaridad de cada cable del MG995.
- [ ] Verificar el divisor de ECHO de 1 kΩ/2 kΩ.
- [ ] Confirmar GND común entre fuente, DevKit, cámara y sensor.
- [ ] Confirmar que el positivo de la fuente externa no está unido al pin 5V/VIN del DevKit alimentado por USB.
- [ ] Confirmar que la corriente del MG995 no circula por la protoboard.
- [ ] Revisar continuidad y ausencia de cortocircuitos.

## 11. Advertencias

- No inviertas la polaridad de la fuente.
- No conectes 5 V directamente a GPIO del ESP32.
- No alimentes el MG995 desde 3V3, el USB del computador ni el regulador de la placa.
- No conectes el positivo de la fuente externa al 5V/VIN del DevKit mientras el USB está conectado.
- No conectes dos fuentes de 5 V en paralelo a una misma placa sin verificar el diseño de alimentación.
- La exclusión de un fusible no elimina el riesgo eléctrico. Utiliza una fuente con protección contra sobrecorriente y supervisa las pruebas.
- No uses el dispensador con mascotas hasta validar seguridad eléctrica, mecánica, control del servo y cantidad de alimento dispensada.

## 12. Relación con el resto del repositorio

Este documento complementa, pero no reemplaza, la documentación específica de firmware y arquitectura:

- [README principal](../README.md)
- [Conexiones eléctricas vigentes](conexiones_usbc.md)
- [Arquitectura local](arquitectura_local.md)
- [Pruebas y validación](pruebas.md)
- [Manual de montaje](../Documentation/manual_armado/Manual_de_Armado.md)
- [Lista de materiales](../Documentation/components/lista_materiales.csv)

**Estado de validación:** esta guía no certifica que el hardware físico ya haya sido probado. La fuente concreta, las placas reales, la caída de tensión, la corriente del servo, el comportamiento de la cámara y la dosificación deben verificarse en laboratorio antes de considerar terminado el prototipo.
