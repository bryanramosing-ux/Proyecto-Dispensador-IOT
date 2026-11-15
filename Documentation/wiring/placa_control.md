# Placa de control — lista de cables

Generada por `generar_placa_control.py` (no editar a mano). Coordenadas (columna, fila) desde la
esquina superior izquierda, vista desde el lado de los componentes. Ver `placa_control.svg`.

## Componentes

| Ref. | Valor / función | Agujeros |
|---|---|---|
| ESP32 | DevKit V1 30 pines sobre 2 tiras hembra de 15 | fila A (EN…VIN): (3,18)…(17,18); fila B (D23…3V3): (3,8)…(17,8) |
| J1 | J1 5 V | GND (33, 2), 5V (33, 3) |
| J3 | J3 SERVO señal | SIG (33, 9), GND (33, 10) |
| J5 | J5 NIVEL TOLVA | GND (6, 2), ECHO (7, 2), TRIG (8, 2), VCC (9, 2) |
| R5 | R5 1k | 1 (7, 3), 2 (7, 7) |
| R6 | R6 2k | 1 (6, 7), 2 (2, 7) |
| R3 | R3 330 | 1 (31, 9), 2 (27, 9) |
| R4 | R4 10k | 1 (27, 11), 2 (27, 15) |
| C4 | C4 470µF | + (21, 3), - (21, 5) |

Bus GND en U: agujeros (1,1) a (35,1), (35,1) a (35,26) y (3,26) a (35,26) unidos con estaño o alambre desnudo.

## Cables (soldar uno por uno y tachar)

| N.º | Red | Desde | Hasta | Recorrido (dobleces) |
|---|---|---|---|---|
| 1 | 5V | J1.5V (33, 3) | C4.+ (21, 3) | (recto) |
| 2 | 5V | C4.+ (21, 3) | J5.VCC (9, 2) | (21, 2) |
| 3 | 5V | J5.VCC (9, 2) | ESP32.A.VIN (17, 18) | (9, 7) → (18, 7) → (18, 18) |
| 4 | GND | J1.GND (33, 2) | bus GND (33, 1) | (recto) |
| 5 | GND | J3.GND (33, 10) | bus GND (35, 10) | (recto) |
| 6 | GND | J5.GND (6, 2) | bus GND (6, 1) | (recto) |
| 7 | GND | ESP32.A.GND (16, 18) | bus GND (16, 26) | (recto) |
| 8 | GND | R4.2 (27, 15) | bus GND (35, 15) | (recto) |
| 9 | GND | R6.2 (2, 7) | bus GND (2, 1) | (recto) |
| 10 | GND | C4.- (21, 5) | bus GND (35, 5) | (recto) |
| 11 | SERVO_GPIO | R3.2 (27, 9) | R4.1 (27, 11) | (recto) |
| 12 | SERVO_GPIO | R4.1 (27, 11) | ESP32.A.D25 (10, 18) | (26, 11) → (26, 20) → (10, 20) |
| 13 | SERVO_SIG | J3.SIG (33, 9) | R3.1 (31, 9) | (recto) |
| 14 | TRIG2 | J5.TRIG (8, 2) | ESP32.B.D19 (8, 8) | (recto) |
| 15 | ECHO2_5V | J5.ECHO (7, 2) | R5.1 (7, 3) | (recto) |
| 16 | ECHO2_3V3 | R5.2 (7, 7) | ESP32.B.D21 (7, 8) | (recto) |
| 17 | ECHO2_3V3 | R5.2 (7, 7) | R6.1 (6, 7) | (recto) |

## Montaje USB-C / 5 V

J1: 5 V y GND de la rama lógica. J3: SIG/GND del servo, no su potencia.
J5: GND-ECHO-TRIG-VCC del sensor de nivel; R5/R6 forman el divisor del ECHO.
El servo recibe 5 V por su rama de potencia con condensador 1000–2200 µF.
La cámara recibe 5 V/GND y condensadores 470 µF + 100 nF fuera de esta placa.
Los conectores/pasivos opcionales aparecen solo si config.h los activa.
V6_S, si está presente, mide el riel de 5 V mediante divisor 100k/33k.
No hay J4 de batería/panel; no conectar tensiones del diseño solar.
Antes de insertar ESP32: medir continuidad, polaridad y ECHO ≤3,4 V.
Detalle: docs/conexiones_usbc.md. Medir la separación real de las tiras del DevKit.
