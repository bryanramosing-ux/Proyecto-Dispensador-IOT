# Conexiones eléctricas — montaje USB-C simplificado

> **Documento de diseño, no certificación eléctrica.** Aún no se ha validado físicamente. Verifique etiqueta de fuente, corrientes reales, polaridad, calibre y caída de tensión antes de conectar el servo.

## 1. Componentes eléctricos vigentes

- ESP32 DevKit V1.
- ESP32-CAM AI-Thinker con OV2640/PSRAM.
- Un HC-SR04 para nivel de tolva.
- MG995 posicional de 180°.
- Fuente regulada de 5 V; recomendación inicial 5 A continuos y protección contra sobrecorriente.
- Cable USB-C y distribución de potencia adecuada.
- Resistencias 1 kΩ y 2 kΩ para ECHO; 330 Ω serie para señal servo; 10 kΩ pull-down.
- 1000–2200 µF junto al servo; 470 µF + 100 nF junto a ESP32-CAM.

Excluidos: panel solar, baterías 18650, BMS, cargador 2S, MT3608, convertidores buck del diseño solar, fusible del esquema anterior, RC522/NFC, PIR y segundo HC-SR04 de presencia.

## 2. Distribución propuesta

**Arquitectura de laboratorio seleccionada:** el PC alimenta por USB únicamente al ESP32 DevKit y, previa comprobación, al HC-SR04. La fuente regulada externa de 5 V alimenta exclusivamente la ESP32-CAM y el MG995 en ramas separadas. Ambas alimentaciones comparten GND, pero sus positivos NO se unen. La corriente del servo no debe circular por pistas de protoboard ni por el regulador de la placa.

```text
PC USB ─── ESP32 DevKit ─── HC-SR04 (5 V, si está verificado)
                │ GPIO25 (señal PWM)
                └── GND común ──────────────────────────┐
                                                       │
Fuente externa 5 V ──┬── ESP32-CAM (5 V)               │
                     └── MG995 (5 V, cables potencia) ──┘

NO conectar el +5 V externo al pin VIN/5V del DevKit alimentado por USB.
```

La recomendación de 5 A es un margen inicial, no una garantía: confirme la corriente de bloqueo del servo específico y el consumo de cámara/ESP32. Si la fuente no mantiene 5 V durante el movimiento, use una fuente separada y adecuada para el servo; una las tierras y no una los positivos de fuentes distintas.

**No alimentar MG995 ni ESP32-CAM desde USB del computador.** El USB se usa para alimentar/programar el DevKit; comprobar que el pin de 5 V del DevKit puede alimentar el HC-SR04. No unir los rieles positivos USB y fuente externa. Verificar con multímetro antes de energizar.

## 3. Tensiones y señales

| Elemento | Conexión | Precaución |
|---|---|---|
| ESP32 DevKit | USB del PC; sin +5 V externo a VIN/5V | Confirmar pinout y tensión USB |
| ESP32-CAM | 5 V y GND | Alimentación estable; no desactivar brownout |
| HC-SR04 | 5 V del DevKit si se verifica, GND común, TRIG GPIO19 | Un sensor de nivel activo |
| HC-SR04 ECHO | GPIO21 mediante divisor 1 kΩ/2 kΩ | No aplicar 5 V directo al GPIO |
| MG995 | Rojo a rama servo 5 V; GND común; señal GPIO25 por 330 Ω | No alimentar desde ESP32 ni protoboard |

Divisor ECHO: Vgpio = Vsensor × 2 kΩ / (1 kΩ + 2 kΩ). Con 5,0 V resulta aproximadamente 3,33 V. Mida el valor real antes de conectar.

## 4. Pines de firmware

| GPIO | Función | Estado |
|---|---|---|
| 19 | TRIG sensor de nivel | Activo |
| 21 | ECHO sensor de nivel con divisor | Activo |
| 25 | Señal PWM MG995 | Activo |
| 2 | LED de estado | Según firmware |
| 0 | Botón BOOT | Activo |
| 26 / 34 | Sensor de presencia | Reservado; detección automática desactivada |
| 32 | Monitor riel servo | Opcional y desactivado por defecto |
| 35 | Monitor batería | Desactivado; no hay batería |

## 5. Reglas de seguridad y prueba

1. No conecte el servo hasta medir salida de fuente y verificar polaridad.
2. Mantenga GND común entre ESP32, cámara, sensor y servo.
3. Use cables de potencia cortos y apropiados; no use Dupont/protoboard como conductores principales del servo.
4. Coloque condensador 1000–2200 µF cerca del servo y respete polaridad.
5. Si el ESP32 se reinicia al mover el servo, desconecte y corrija alimentación antes de seguir.
6. No deje el servo bloqueado contra topes mecánicos.
7. La ausencia del fusible no elimina el riesgo de cortocircuito. Use fuente certificada con protección contra sobrecorriente y supervisión durante pruebas.
8. No conecte USB del PC y fuente externa al mismo tiempo sin confirmar aislamiento eléctrico.

## 6. Diagramas del montaje vigente

Los generadores `Documentation/wiring/generar_placa_control.py` y `generar_esquema.py` leen `ALIMENTACION_USBC` y los GPIO activos de `config.h`, pero **sus salidas no se consideran verificadas contra la distribución de dos fuentes de este manual**. No usarlas para conectar alimentación hasta revisar y actualizar los generadores y diagramas. La lista actual está en `Documentation/components/lista_materiales.csv`. El manual PDF y el video del diseño solar son históricos y no deben utilizarse para cablear esta versión.

## 7. Validación pendiente

No se han confirmado la fuente física disponible, la corriente de bloqueo de tu unidad MG995, la caída de tensión bajo carga, la polaridad del cable USB-C ni la seguridad del montaje completo. Coteja la fuente recomendada con sus especificaciones reales antes de comprar o conectar.
