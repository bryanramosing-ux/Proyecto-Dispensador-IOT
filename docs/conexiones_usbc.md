# Conexiones eléctricas — montaje USB-C (sin panel solar ni fusible)

> **Estado:** diseño de referencia calculado a partir de las hojas de datos y de `ESP32/Dispensador_ESP32/config.h`.
> **No ha sido probado físicamente.** Antes de conectar el MG995 o la cámara, siga la lista de verificación del final
> con multímetro. La documentación heredada (`Documentation/wiring/`, estación solar, batería 2S, fusible F1) describe
> **otro** montaje y no debe usarse para este.

Excluidos del diseño: panel solar, fusible, RFID RC522, NFC. Los pines `PIN_VBAT` (GPIO35) y el monitor de batería
están desactivados (`USAR_MONITOR_BATERIA 0`).

## 1. Distribución de energía

```
Adaptador USB-C 5 V / ≥3 A (salida fija de 5 V)
        │  (breakout USB-C con 2 × 5,1 kΩ entre CC1/CC2 y GND, si se cablea sin conector de datos)
        ▼
   Bus 5 V  ──┬── cable grueso (AWG 20, corto) ── MG995 rojo (V+)   + 1000–2200 µF ≥10 V junto al servo
              ├── ESP32 DevKit V1: pin VIN (o su USB-C/micro-USB, nunca ambos a la vez)
              ├── ESP32-CAM: 5V   + 470 µF + 100 nF junto a la placa, cable ≤ 30 cm
              └── HC-SR04 × 2: VCC
   GND común (punto estrella) ── MG995 marrón, ESP32 GND, ESP32-CAM GND, HC-SR04 GND
```

| Carga | Tensión | Corriente típica / pico (hoja de datos) | Observación |
|---|---|---|---|
| ESP32 DevKit V1 | 5 V (VIN) → LDO 3,3 V | ~100 mA prom., ~240–500 mA en TX Wi-Fi | |
| ESP32-CAM AI-Thinker | 5 V | 180 mA (sin flash), 310 mA (flash) | el flash está desactivado (`USAR_FLASH 0`) |
| HC-SR04 (tolva; el de presencia es opcional) | 5 V | 15 mA c/u midiendo | |
| MG995 | 4,8–7,2 V (admite 5 V) | 500–900 mA en movimiento; **~2,5 A bloqueado** a 6 V | a 5 V entrega menos par; el pico domina el diseño |

Presupuesto: ~0,6 A de lógica + hasta ~1 A de servo en uso normal; con atasco puede llegar a 2,5 A. Por eso se pide un
adaptador de **≥ 3 A** a 5 V y se detecta el atasco por caída de tensión del riel (`USAR_MONITOR_SERVO`).

**Reglas que debe cumplir el montaje**

1. El MG995 **nunca** se alimenta desde un GPIO ni desde el 3,3 V/5 V regulado de la placa ESP32; solo su señal va al GPIO25.
2. Los cables de potencia del servo salen directamente del bus de 5 V (no pasan por la protoboard) y su retorno llega al punto estrella de GND.
3. Si al mover el servo el ESP32 o la cámara se reinician (brownout), la solución es una **segunda fuente de 5 V ≥ 2 A solo para el servo** con **solo GND unido** al resto. No se unen los dos +5 V. Esto es un componente adicional que puede resultar indispensable; solo la medición lo dirá.
4. Sin fusible, la protección contra cortocircuito depende del adaptador. Use un cargador certificado con protección de sobrecorriente y revise que no haya cortos antes de energizar.
5. No alimentar el ESP32 por VIN y por USB al mismo tiempo (alimentación inversa entre fuentes).

## 2. ESP32 DevKit V1 — pines (coinciden con `config.h`)

| GPIO | Función | Conexión |
|---|---|---|
| 25 | PWM servo (LEDC 50 Hz) | 330 Ω en serie → señal MG995 (naranja); 10 kΩ a GND |
| 19 | TRIG HC-SR04 de tolva (nivel) | directo (3,3 V es nivel alto válido para el HC-SR04) |
| 21 | ECHO HC-SR04 de tolva | **divisor** 1 kΩ / 2 kΩ |
| 32 | Monitor del riel del servo (opcional, `USAR_MONITOR_SERVO`) | divisor 100 kΩ / 33 kΩ |
| 0 | Botón BOOT: pulsación corta = 1 porción; larga = borrar error | integrado |
| 2 | LED azul de estado | integrado |

Pines evitados: GPIO6–11 (flash interno), 12/15 (arranque), 1/3 (USB-serie), 35/36/39 para salidas.

### Divisor del ECHO (5 V → 3,3 V)

ECHO ─ R1 = 1 kΩ ─┬─ GPIO ; R2 = 2 kΩ desde el nodo a GND.

`Vgpio = 5 V · R2 / (R1 + R2) = 5 · 2000 / 3000 = 3,33 V` (máximo admitido por el GPIO: 3,6 V). Con HC-SR04 que
entregue 5,25 V resulta 3,5 V, aún dentro del límite. Corriente del divisor: 5 V / 3 kΩ = 1,7 mA.
TRIG se conecta directo: el HC-SR04 reconoce 3,3 V como nivel alto (≥ 2 V según hoja de datos); si su módulo no
dispara con 3,3 V, use un adaptador de nivel en lugar de alimentar TRIG a 5 V.

## 3. ESP32-CAM AI-Thinker

Pines ocupados por la cámara/placa (no reutilizar): GPIO 0, 5, 18, 19, 21, 22, 23, 25, 26, 27, 32, 34, 35, 36, 39
(cámara), 4 (flash), 33 (LED rojo), 12/13/14/15/2 (tarjeta microSD, no usada). Esta placa **no comparte GPIO con el
ESP32 DevKit**; solo comparte 5 V y GND. La cámara se comunica solo por Wi-Fi.

Programación: sin puerto USB propio; use un adaptador USB-serie de 3,3 V (TX↔U0R, RX↔U0T, 5V, GND) y **GPIO0 a GND**
durante la carga, luego retirar el puente y reiniciar. La cámara necesita 5 V estables (≥ 500 mA de pico): si aparece
`Brownout detector was triggered`, mejore la fuente/cable; no desactive el detector.

> Nota: las fotos del material muestran un módulo **OV7670 sin FIFO**, que **no** se usa (no tiene Wi-Fi ni JPEG y el
> DevKit sin PSRAM solo daría fotos pequeñas). Se adquirirá una ESP32-CAM.

## 4. Lista de verificación previa a energizar (con multímetro)

- [ ] Continuidad nula entre 5 V y GND (bus y cada carga).
- [ ] Adaptador sin carga: 4,9–5,2 V.
- [ ] Con ESP32 y cámara conectados, **sin servo**: 5 V estables; ambas placas se unen al Wi-Fi.
- [ ] Abrir `http://<IP-CAMARA>/capture`: debe devolver un JPEG real.
- [ ] Divisor del ECHO: medir ≤ 3,4 V en el nodo con el sensor midiendo.
- [ ] Con el servo: osciloscopio o multímetro en el bus durante el giro; no debe bajar de ~4,5 V ni reiniciar nada.
- [ ] Servo sin carga mecánica primero: calibrar `PULSO_*_US` en `config.h` antes de acoplar el disco.
- [ ] Temperatura de adaptador, cables y reguladores tras 10 min de uso.
