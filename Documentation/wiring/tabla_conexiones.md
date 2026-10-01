# Tabla de conexiones punto a punto

Complementa al [esquema completo](esquema_conexiones.svg) (generado por `generar_esquema.py`, que lee los GPIO
de `config.h`) y al [cableado de la placa perforada](placa_control.md) (34 cables numerados, generado y
verificado por `generar_placa_control.py`). Si cambia un pin en `config.h`, vuelva a ejecutar ambos scripts:
fallan si la placa no coincide con el firmware.

> Los colores de cable son una **recomendación** para no confundirse; lo obligatorio es respetar el destino
> de cada conductor. Antes de energizar, haga las comprobaciones de la sección 7.

## 1. Pines del ESP32 DevKit V1

| GPIO | Función | Dirección | Llega por | Componente | Notas de la auditoría |
|---|---|---|---|---|---|
| 26 | TRIG presencia | salida | J2 | HC-SR04 n.º 1 (cápsula 03) | 3,3 V es un ALTO válido para el HC-SR04 |
| 34 | ECHO presencia | entrada | J2 → R1 1k / R2 2k | HC-SR04 n.º 1 | solo entrada; el divisor deja ≈3,4 V |
| 19 | TRIG nivel de tolva | salida | J5 | HC-SR04 n.º 2 (cápsula 13b) | sin función de arranque |
| 21 | ECHO nivel de tolva | entrada | J5 → R5 1k / R6 2k | HC-SR04 n.º 2 | el divisor deja ≈3,4 V |
| 25 | PWM servo 50 Hz | salida | R3 330 Ω → J3 | MG995 (señal naranja) | R4 10k a GND: el servo no se mueve al arrancar |
| 35 | VBAT | ADC1 | J4 | divisor 100k/33k del cajón | 8,4 V → 2,08 V |
| 32 | V6 (riel del servo) | ADC1 | J4 | divisor 100k/33k del cajón | 6,0 V → 1,49 V |
| 33 | VPAN (panel solar) | ADC1 | J4 | divisor 100k/100k del cajón | se mide ANTES de D1; 4,0 V → 2,0 V |
| 2 | LED de estado | salida | — | LED azul de la placa | también es pin de arranque: solo el LED interno |
| 0 | Botón BOOT | entrada | — | botón de la placa | pulsación larga (2 s) = borrar error |
| VIN | 5,0 V | — | J1 | Buck B | ver nota 7 del esquema (USB + VIN) |
| GND | tierra | — | J1 y bus GND | punto estrella | |

No se usan: GPIO6–11 (flash), 1/3 (USB-serie), 0/2/5/12/15 para periféricos (arranque), 36/39 para pulsos
(falsas lecturas con el Wi-Fi), ADC2 (no funciona con el Wi-Fi activo) ni la salida 3V3 para cargas externas.

## 2. Estación solar remota (piezas 12a + 12b)

| Desde | Hasta | Cable | Notas |
|---|---|---|---|
| Panel + | GX12 macho, pin 1 | rojo AWG 20–22, bipolar de exterior, 3–5 m | soldar y aislar con termorretráctil en el panel |
| Panel − | GX12 macho, pin 2 | negro (mismo cable bipolar) | |
| Cable bipolar | base 12a | 2 ranuras + túnel para brida | alivio de tensión: el tirón no llega a las soldaduras |
| GX12 macho | GX12 hembra en la tapa trasera del cajón 16 | — | enchufar y desenchufar con S1 apagado |

## 3. Cajón de energía (pieza 16)

| Desde | Hasta | Sección | Notas |
|---|---|---|---|
| GX12 hembra pin 1 (+ panel) | D1 1N5817 ánodo | AWG 22 | |
| GX12 hembra pin 1 (+ panel) | divisor VPAN: 100k superior | AWG 26 | tomada ANTES del diodo |
| GX12 hembra pin 2 (− panel) | MT3608 IN− (= GND) | AWG 22 | |
| D1 cátodo (franja) | MT3608 IN+ | AWG 22 | |
| MT3608 OUT+ / OUT− (5,0 V) | Cargador 2S: entrada 5 V (+ / −) | AWG 22 | ajustar el MT3608 a 5,0 V ANTES de conectarlo |
| USB-C del cargador | cargador de pared 5 V | — | carga principal |
| Celda 1 − | BMS B− | AWG 20 | portapilas 2S |
| Unión celda 1 + / celda 2 − | BMS BM | AWG 22 | balanceo |
| Celda 2 + | BMS B+ | AWG 20 | |
| Cargador salida + / − (8,4 V) | BMS P+ / P− | AWG 20 | el BMS protege la carga |
| BMS P+ | F1 4 A lento | AWG 20 | fusible lo más cerca posible del BMS |
| F1 | S1 interruptor | AWG 20 | |
| S1 | bus VBAT (6,0–8,4 V) | AWG 20 | |
| bus VBAT | Buck A IN+, Buck B IN+ | AWG 20 | |
| bus VBAT | divisor VBAT: 100k superior | AWG 26 | |
| BMS P− | punto estrella GND | AWG 20 | |
| Buck A IN−, Buck B IN−, MT3608 OUT− | punto estrella GND | AWG 20–22 | |
| Buck A OUT+ (6,0 V) | conector de potencia del servo (XT30 o JST-VH) | AWG 20 | NO pasa por la placa de control |
| Buck A OUT+ (6,0 V) | divisor V6: 100k superior | AWG 26 | |
| Buck A OUT− | conector de potencia del servo (−) | AWG 20 | |
| Buck B OUT+ / OUT− (5,0 V) | C 470 µF (+ / −) y bus 5 V | AWG 22 | |
| bus 5 V / GND | cable J1 → placa de control | AWG 22, 25 cm | |
| bus 5 V / GND | cable de la ESP32-CAM | AWG 22, 45 cm | |
| nodos de los divisores (VBAT, V6, VPAN) + GND | cable J4 → placa de control | AWG 24–26, 25 cm | divisores: 33k / 33k / 100k inferiores a GND |

## 4. Placa de control (bandeja 05)

El cableado interno está en [placa_control.md](placa_control.md) (34 cables, de dónde a dónde, con el recorrido de
cada uno). Conectores:

| Conector | Pines (orden en la placa) | Cable hacia |
|---|---|---|
| J1 | GND · 5V | bus de 5 V del cajón |
| J2 | VCC · TRIG · ECHO · GND | HC-SR04 de presencia (cápsula 03) |
| J3 | SIG · GND | MG995: naranja (señal) y marrón (GND) |
| J4 | VBAT · V6 · VPAN · GND | divisores del cajón |
| J5 | GND · ECHO · TRIG · VCC (de izquierda a derecha, borde superior) | HC-SR04 de nivel (tapa de la tolva) |

## 5. Periféricos

| Componente | Pin | Va a | Notas |
|---|---|---|---|
| HC-SR04 n.º 1 (presencia) | VCC / TRIG / ECHO / GND | J2 (mismo orden) | cable de 4 hilos ~30 cm por el paso izquierdo del tabique |
| HC-SR04 n.º 2 (nivel) | VCC / TRIG / ECHO / GND | J5 (el cable llega girado: GND-ECHO-TRIG-VCC) | ~120 cm: ranura de la tapa 13a → conducto de la esquina trasera izquierda (07 → 08d) → bahía trasera de 02. Dejar ~20 cm flojos bajo la tapa |
| MG995 | naranja (señal) | J3 SIG | |
| MG995 | marrón (GND) | J3 GND **y** GND del Buck A (empalme en Y) | la corriente del motor vuelve por el Buck A, no por la placa |
| MG995 | rojo (V+) | Buck A OUT+ (6,0 V) | condensador 1000–2200 µF ≥10 V entre rojo y marrón, junto al servo |
| ESP32-CAM | 5V / GND | bus 5 V del cajón | 470 µF + 100 nF soldados junto a la cámara; sin cables de datos (solo Wi-Fi) |

## 6. Recorridos de cables por la torre

| Cable | Recorrido |
|---|---|
| Panel (exterior) | estación 12a → suelo → GX12 de la tapa trasera del cajón 16 |
| J1, J4, ESP32-CAM 5 V | cajón 16 → agujero del piso de 02 → bahía trasera |
| J2 | cápsula 03 → agujero del frente (fuera del canal) → paso izquierdo del tabique → bahía trasera |
| ESP32-CAM | cápsula 04 → agujero del frente → paso derecho del tabique → bahía trasera |
| J3 + 6 V del servo | soporte 06 → bahía trasera (el 6 V baja por el agujero del piso hasta el cajón) |
| J5 (nivel) | cápsula 13b → ranura sobre la tapa 13a → conducto Ø8 de la esquina trasera izquierda (07 y 08d) → bahía trasera |

Ningún cable pasa por el canal de alimento (09) ni por la tolva (el conducto de la esquina es un tubo cerrado,
fuera del embudo).

## 7. Comprobaciones antes de energizar

1. Con todo desconectado, ajustar Buck A = 6,0 V, Buck B = 5,0 V y MT3608 = 5,0 V (multímetro, sin carga).
2. Continuidad: ninguna entre 5 V y GND, 6 V y GND, VBAT y GND (placa y cajón).
3. Placa de control SIN el ESP32: alimentar J1 con 5 V y medir 5 V en VIN, en J2.VCC y en J5.VCC.
4. Con los HC-SR04 conectados y sin el ESP32, medir con el multímetro en los agujeros de D34 y D21: nunca más
   de 3,4 V (los divisores trabajan bien).
5. Colocar el ESP32, cargar el firmware y usar los comandos serie `DIST`, `NIVEL`, `ENERGIA` y `SERVO 1500`
   (ver `ESP32/README.md`) antes de montar la torre completa.
