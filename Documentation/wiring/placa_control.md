# Placa de control — lista de cables

Generada por `generar_placa_control.py` (no editar a mano). Coordenadas (columna, fila) desde la
esquina superior izquierda, vista desde el lado de los componentes. Ver `placa_control.svg`.

## Componentes

| Ref. | Valor / función | Agujeros |
|---|---|---|
| ESP32 | DevKit V1 30 pines sobre 2 tiras hembra de 15 | fila A (EN…VIN): (3,18)…(17,18); fila B (D23…3V3): (3,8)…(17,8) |
| J1 | J1 5 V | GND (33, 2), 5V (33, 3) |
| J2 | J2 HC-SR04 | VCC (33, 4), TRIG (33, 5), ECHO (33, 6), GND (33, 7) |
| J3 | J3 SERVO señal | SIG (33, 9), GND (33, 10) |
| J4 | J4 MEDICIÓN | VBAT (33, 12), V6 (33, 13), VPAN (33, 14), GND (33, 15) |
| R1 | R1 1k | 1 (31, 6), 2 (27, 6) |
| R2 | R2 2k | 1 (24, 6), 2 (24, 10) |
| R3 | R3 330 | 1 (31, 9), 2 (27, 9) |
| R4 | R4 10k | 1 (27, 11), 2 (27, 15) |
| C1 | C1 100n | 1 (25, 23), 2 (25, 25) |
| C2 | C2 100n | 1 (29, 22), 2 (29, 24) |
| C3 | C3 100n | 1 (31, 21), 2 (31, 23) |
| C4 | C4 470µF | + (21, 3), - (21, 5) |

Bus GND en L: agujeros (35,2) a (35,26) y (3,26) a (35,26) unidos con estaño o alambre desnudo.

## Cables (soldar uno por uno y tachar)

| N.º | Red | Desde | Hasta | Recorrido (dobleces) |
|---|---|---|---|---|
| 1 | 5V | J1.5V (33, 3) | J2.VCC (33, 4) | (recto) |
| 2 | 5V | J1.5V (33, 3) | C4.+ (21, 3) | (recto) |
| 3 | 5V | C4.+ (21, 3) | ESP32.A.VIN (17, 18) | (19, 3) → (19, 18) |
| 4 | GND | J1.GND (33, 2) | bus GND (35, 2) | (recto) |
| 5 | GND | J2.GND (33, 7) | bus GND (35, 7) | (recto) |
| 6 | GND | J3.GND (33, 10) | bus GND (35, 10) | (recto) |
| 7 | GND | J4.GND (33, 15) | bus GND (35, 15) | (recto) |
| 8 | GND | ESP32.A.GND (16, 18) | bus GND (16, 26) | (recto) |
| 9 | GND | R2.2 (24, 10) | bus GND (24, 26) | (recto) |
| 10 | GND | R4.2 (27, 15) | bus GND (27, 26) | (recto) |
| 11 | GND | C1.2 (25, 25) | bus GND (25, 26) | (recto) |
| 12 | GND | C2.2 (29, 24) | bus GND (29, 26) | (recto) |
| 13 | GND | C3.2 (31, 23) | bus GND (31, 26) | (recto) |
| 14 | GND | C4.- (21, 5) | bus GND (21, 26) | (recto) |
| 15 | TRIG | J2.TRIG (33, 5) | ESP32.A.D26 (11, 18) | (25, 5) → (25, 19) → (11, 19) |
| 16 | ECHO_5V | J2.ECHO (33, 6) | R1.1 (31, 6) | (recto) |
| 17 | ECHO_3V3 | R1.2 (27, 6) | R2.1 (24, 6) | (recto) |
| 18 | ECHO_3V3 | R2.1 (24, 6) | ESP32.A.D34 (6, 18) | (23, 6) → (23, 24) → (6, 24) |
| 19 | SERVO_GPIO | R3.2 (27, 9) | R4.1 (27, 11) | (recto) |
| 20 | SERVO_GPIO | R4.1 (27, 11) | ESP32.A.D25 (10, 18) | (26, 11) → (26, 20) → (10, 20) |
| 21 | SERVO_SIG | J3.SIG (33, 9) | R3.1 (31, 9) | (recto) |
| 22 | VBAT_S | J4.VBAT (33, 12) | C1.1 (25, 23) | (28, 12) → (28, 23) |
| 23 | VBAT_S | C1.1 (25, 23) | ESP32.A.D35 (7, 18) | (7, 23) |
| 24 | V6_S | J4.V6 (33, 13) | C2.1 (29, 22) | (30, 13) → (30, 22) |
| 25 | V6_S | C2.1 (29, 22) | ESP32.A.D32 (8, 18) | (8, 22) |
| 26 | VPAN_S | J4.VPAN (33, 14) | C3.1 (31, 21) | (32, 14) → (32, 21) |
| 27 | VPAN_S | C3.1 (31, 21) | ESP32.A.D33 (9, 18) | (9, 21) |

## Arnés de cables de la torre

Longitudes estimadas sobre el modelo 3D (recorrido por los pasos del piso y del tabique) con ~30 % de
holgura; cortar un poco más largo y ajustar al montar. Conectores entre módulos recomendados: JST-XH
(señal) y XT30 o JST-VH (potencia), para poder separar los módulos sin desoldar.

| Cable | Desde | Hasta | Conductores | Sección | Longitud aprox. |
|---|---|---|---|---|---|
| J1 | Bus 5 V del cajón (Buck B) | J1 de la placa de control | 5V, GND | AWG 22 | 25 cm |
| J4 | Divisores del cajón | J4 de la placa de control | VBAT, V6, VPAN, GND | AWG 24–26 | 25 cm |
| J2 | J2 de la placa | HC-SR04 (cápsula 03, paso izquierdo del tabique) | VCC, TRIG, ECHO, GND | AWG 24–26 | 30 cm |
| J3 | J3 de la placa | Cables naranja (señal) y marrón (GND) del MG995 | SIG, GND | AWG 24 | 20 cm (el cable del MG995 suele alcanzar) |
| Servo 6 V | Buck A del cajón (+ C1 1000–2200 µF junto al servo) | Cable rojo (+) y marrón (−) del MG995 | 6V, GND | **AWG 20** | 40 cm |
| Cámara | Bus 5 V del cajón | ESP32-CAM (cápsula 04, paso derecho del tabique; 470 µF + 100 nF en la cápsula) | 5V, GND | AWG 22 | 45 cm |
| Panel | Panel solar (soporte 12) | Elevador MT3608 y divisor del panel en el cajón (por el conducto de la esquina) | +, − | AWG 22 | 70 cm (alargar el cable del panel) |

## Conectores de la placa

| Conector | Pin | Va a |
|---|---|---|
| J1 | 5V / GND | Bus de 5 V del cajón de energía (Buck B) |
| J2 | VCC / TRIG / ECHO / GND | HC-SR04 (cápsula 03) |
| J3 | SIG / GND | Cable naranja y marrón del MG995 (el rojo va al Buck A de 6 V, NO a esta placa) |
| J4 | VBAT / V6 / VPAN / GND | Salidas de los divisores 100k/33k, 100k/33k y 100k/100k montados en el cajón |

Antes de colocar el ESP32: con el multímetro, comprobar que no hay continuidad entre 5V y GND
ni entre la red ECHO_5V y el ESP32; con J1 alimentado y el HC-SR04 conectado, medir ≤ 3,4 V en el
agujero del pin D34 al disparar.
