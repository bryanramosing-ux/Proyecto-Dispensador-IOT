# Plan de impresión · Elegoo Neptune 4 Plus

Generado por `plan_impresion.py` (no editar a mano). Volumen de la impresora: 320 × 320 × 385 mm; todas las piezas se verificaron con un margen de 5 mm por lado (`generar_stl.py`).

![Placas](render/placas_impresion.png)

Importe en el laminador (Elegoo Cura u OrcaSlicer con el perfil «Elegoo Neptune 4 Plus») los STL de cada placa **sin rotarlos** (ya vienen orientados) y use *Organizar*. Si prefiere menos riesgo, imprima las piezas altas (02, 07) solas: un fallo no arruina las demás.

## Placa 1 · PLA · ≈368 g · ≈15 h 55 min

| Pieza | Huella × altura (mm) | Relleno | Filamento | Tiempo (orientativo) |
|---|---|---|---|---|
| 01_Base_Torre | 190 × 190 × 45 | 20% | 219 g (73.4 m) | 9 h 25 min |
| 14_Tapa_Lateral_Servicio | 109 × 186 × 6 | 20% | 57 g (19.1 m) | 2 h 17 min |
| 05_Modulo_ESP32 | 100 × 74 × 29 | 20% | 44 g (14.7 m) | 1 h 46 min |
| 03_Modulo_HC_SR04 | 52 × 58 × 28 | 20% | 22 g (7.5 m) | 0 h 59 min |
| 04_Modulo_ESP32_CAM | 42 × 60 × 34 | 20% | 23 g (7.7 m) | 1 h 14 min |
| 15_Separadores | 67 × 19 × 10 | 20% | 3 g (1.0 m) | 0 h 16 min |

## Placa 2 · PLA · ≈615 g · ≈22 h 53 min

| Pieza | Huella × altura (mm) | Relleno | Filamento | Tiempo (orientativo) |
|---|---|---|---|---|
| 02_Cuerpo_Principal | 150 × 150 × 226 | 20% | 532 g (178.2 m) | 20 h 04 min |
| 08a_Carcasa_Dosificador | 150 × 150 × 44 | 20% | 83 g (27.8 m) | 2 h 49 min |

## Placa 3 · PETG · ≈794 g · ≈27 h 08 min

| Pieza | Huella × altura (mm) | Relleno | Filamento | Tiempo (orientativo) |
|---|---|---|---|---|
| 07_Tolva | 150 × 150 × 180 | 20% | 533 g (174.5 m) | 17 h 26 min |
| 11_Comedero | 150 × 146 × 44 | 20% | 116 g (37.9 m) | 4 h 06 min |
| 13a_Tapa_Superior_Tolva | 146 × 145 × 13 | 20% | 56 g (18.4 m) | 2 h 10 min |
| 08d_Placa_Base_Dosificador | 143 × 143 × 32 | 20% | 89 g (29.2 m) | 3 h 26 min |

## Placa 4 · PETG · ≈384 g · ≈17 h 13 min

| Pieza | Huella × altura (mm) | Relleno | Filamento | Tiempo (orientativo) |
|---|---|---|---|---|
| 08c_Placa_Superior_Dosificador | 124 × 124 × 14 | 20% | 44 g (14.3 m) | 1 h 44 min |
| 12a_Estacion_Solar_Base | 130 × 110 × 70 | 40% | 82 g (26.8 m) | 3 h 56 min |
| 16_Soporte_Estructural_Cajon_Energia | 110 × 123 × 31 | 40% | 47 g (15.2 m) | 2 h 26 min |
| 08b_Disco_Dosificador | 116 × 116 × 14 | 40% | 87 g (28.6 m) | 4 h 52 min |
| 09_Conducto_Alimento | 41 × 221 × 50 | 20% | 94 g (30.9 m) | 2 h 55 min |
| 06_Soporte_MG995 | 143 × 35 × 5 | 40% | 18 g (5.9 m) | 0 h 53 min |
| 13c_Tapa_Capsula_Sensor | 58 × 78 × 2 | 20% | 12 g (3.8 m) | 0 h 26 min |

## Placa 5 · PETG · ≈77 g · ≈3 h 08 min

| Pieza | Huella × altura (mm) | Relleno | Filamento | Tiempo (orientativo) |
|---|---|---|---|---|
| 12b_Estacion_Solar_Bandeja | 104 × 88 × 14 | 40% | 21 g (6.9 m) | 0 h 56 min |
| 10_Salida_Alimento | 64 × 106 × 52 | 20% | 33 g (10.7 m) | 1 h 19 min |
| 13b_Capsula_Sensor_Nivel | 54 × 64 × 31 | 20% | 23 g (7.5 m) | 0 h 53 min |

## Totales

| Material | Filamento | Bobinas de 1 kg |
|---|---|---|
| PLA | ≈983 g | 2 (con 15 % de reserva para pruebas y fallos) |
| PETG | ≈1255 g | 2 (con 15 % de reserva para pruebas y fallos) |

Tiempo total orientativo: **≈86 h 17 min** de impresión (suma de las piezas).

## Perfil usado para estimar (equivalente a la Neptune 4 Plus)

| Ajuste | PLA | PETG |
|---|---|---|
| Boquilla / capa / primera capa | 0,4 / 0,2 / 0,2 mm | 0,4 / 0,2 / 0,2 mm |
| Temperatura boquilla / cama | 210 / 60 °C | 240 / 75 °C |
| Perímetros / capas sup. / inf. | 3 / 5 / 4 | 3 / 5 / 4 |
| Relleno | giroide 20 % (40 % en 06, 08b, 12a, 12b, 16) | ídem |
| Flujo volumétrico máx. | 18 mm³/s | 12 mm³/s |
| Velocidades (perímetro ext. / int. / relleno) | 80 / 120 / 200 mm/s | ídem (las limita el flujo) |
| Soportes | **ninguno** (diseño sin voladizos > 45°) | ídem |
| Adherencia | falda; borde (brim) de 5 mm solo en 02 y 07 si la cama no agarra bien | ídem; en PETG use pegamento en barra o la cara texturizada de la placa PEI |

Los tiempos los calcula PrusaSlicer con estas velocidades; su laminador puede dar otros valores. Los gramos dependen poco del laminador.
