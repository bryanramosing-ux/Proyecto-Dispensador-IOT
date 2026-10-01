# Mecánica — Torre modular imprimible en 3D

![Vista frontal](render/vista_frente.png)

Todo el modelo es **paramétrico** y se genera con Python:

```bash
pip install numpy trimesh manifold3d matplotlib
python generar_stl.py    # crea STL/ y ejecuta las verificaciones automáticas
python render.py         # planos 2D: corte del recorrido del alimento y planta del dosificador
```

`generar_stl.py` comprueba en cada ejecución:

* que **ninguna pieza interfiera con otra** (153 pares) ni con la envolvente del MG995;
* que el bolsillo del disco **nunca conecte** la tolva con el conducto a la vez (margen angular);
* que el interior del canal de alimento **no contenga electrónica** (ESP32, ESP32-CAM, HC-SR04, MG995, soporte);
* que la punta del pico caiga dentro del comedero y por encima de su borde;
* que las paredes de la tolva tengan **≥ 55°** (las croquetas no forman bóveda con paredes tendidas);
* que cada pieza **quepa en 220 × 220 × 250 mm** y tenga una cara plana de apoyo en la orientación de impresión.

> Las cotas de los componentes comprados (MG995, HC-SR04, ESP32-CAM, placa perforada, panel) son las
> **nominales** y están al principio de `generar_stl.py` (sección COMPONENTES). **Mida sus unidades con un
> calibre** y corrija esos parámetros antes de imprimir: los clones varían. El panel solar debe medirse sí o sí
> (`PANEL_W`, `PANEL_H`).

## Piezas

`STL/` contiene cada pieza **ya orientada para imprimir** y `00_Ensamblaje_Referencia_NO_IMPRIMIR.stl`
(GitHub lo muestra en 3D).

| Pieza | Función / ubicación | Tamaño de impresión (mm) | Unión y tornillería | Orientación | Mantenimiento |
|---|---|---|---|---|---|
| 01_Base_Torre | Módulo de energía; plinto de 190 mm para estabilidad; 4 pilares de unión | 190×190×45 | 4 × M3×12 desde arriba (a través del piso de 02) | Como está | Se separa de 02 quitando 4 tornillos |
| 16_Soporte_Estructural_Cajon_Energia | Cajón deslizante: batería, BMS, convertidores, cargador; tapa trasera con interruptor y USB-C | 110×123×31 | 2 × M3×10 a tetones de 01; componentes con M3 + separadores (rejilla 10 mm) | Piso abajo | Sale por detrás sin desarmar la torre |
| 02_Cuerpo_Principal | Canal de alimento (frente), tabique, bahía electrónica (atrás), frente de sensores | 150×150×226 | Labio superior + 3 × M3×10 radiales hacia 08a | Como está | Tapa de servicio trasera |
| 03_Modulo_HC_SR04 | Cápsula del HC-SR04 (horizontal, pines abajo) | 52×58×28 | 2 × M3×10 + tuerca por dentro de la pared | Cara frontal abajo | Se desatornilla desde el frente |
| 04_Modulo_ESP32_CAM | Cápsula de la ESP32-CAM, inclinada 12° hacia abajo, con ventilación | 42×60×34 | 2 × M3×10 + tuerca | Cara frontal abajo | Se desatornilla desde el frente |
| 05_Modulo_ESP32 | Bandeja con guías para una placa perforada 90×70 mm con el ESP32 | 100×74×29 | 4 × M3×10 + tuerca bajo el piso | Como está | La placa sale deslizando por la tapa trasera |
| 06_Soporte_MG995 | Viga que sostiene el servo, apoyada en dos ménsulas de 02 | 143×35×5 | 2 × M3×10 a las ménsulas; servo con 4 tornillos en ranuras | Plana | Calces (15) para ajustar la altura |
| 07_Tolva | Depósito con embudo cónico oblicuo (≥55°), conducto oculto para el cable del panel | 150×150×180 | Sobre el labio de 08a + 3 × M3×10 | Como está | Se retira para limpiar; sin electrónica |
| 08a_Carcasa_Dosificador | Anillo exterior del módulo dosificador | 150×150×44 | Labio de 02 + 3 × M3×10; labio para 07 | Como está | — |
| 08b_Disco_Dosificador | Disco de 116 mm con un bolsillo de Ø28×14 mm (8,6 cm³ geométricos) | 116×116×14 | Atornillado al horn redondo del MG995 | Boca abajo | Se saca levantando 08c |
| 08c_Placa_Superior_Dosificador | Tapa del disco con la entrada (Ø28) y zócalo para la boca de la tolva | 124×124×14 | Asiento cónico + chaveta (sin tornillos) | Como está | Sale a mano para limpiar |
| 08d_Placa_Base_Dosificador | Placa con la salida (Ø32), cámara del disco, laberinto del eje y marcas de calibración | 143×143×32 | Apoya sobre el labio de 02, encajada en 08a | Como está | Superficie lisa, lavable |
| 09_Conducto_Alimento | Tubo cerrado 36×36 mm: vertical + codo a 45° hacia el frente | 185×185×50 (en diagonal) | Apoya en el piso de 02; se baja desde arriba | Acostado sobre su cara trasera | Se lava; se cepilla por dentro |
| 10_Salida_Alimento | Pico a 45° que deja caer el alimento en el comedero | 64×106×52 | 4 × M3×10 a tetones del frente de 02 | Sobre la cara inferior del tubo | Se desmonta desde fuera |
| 11_Comedero | Plato con cuenco Ø118 interior; 2 lengüetas que entran bajo el plinto | 150×146×44 | Encastre (sin tornillos) | Como está | Se saca para lavar (ver nota de higiene) |
| 12_Soporte_Panel_Solar | Bandeja inclinada 30° para el panel (alojamiento paramétrico) | 57×82×90 | 4 × M3×10 a tetones de 07 | De costado (perfil sobre la cama) | — |
| 13_Tapa_Superior | Tapa de la tolva con muescas para los dedos | 146×145×12 | Encaje a presión en el cilindro | Boca abajo | — |
| 14_Tapa_Lateral_Servicio | Tapa trasera de la bahía electrónica (ventilada) | 109×186×6 | 4 × M3×10 | Cara exterior abajo | Acceso al ESP32, servo y cableado |
| 15_Separadores | Tubos para M3 (3, 6 y 10 mm) | 67×19×10 | — | Como está | — |

**Recorrido del alimento:** 07 → 08c (entrada) → 08b (bolsillo) → 08d (salida) → 09 → 10 → 11.
Ninguna de esas piezas contiene ni toca electrónica.

![Corte](render/corte_recorrido_alimento.png)

## Recomendaciones de impresión

| Parámetro | Valor recomendado |
|---|---|
| Material piezas en contacto con alimento (07, 08b, 08c, 08d, 09, 10, 11) | **PETG** apto para contacto con alimentos (o PLA de color natural sin aditivos); boquilla de acero inoxidable si se busca aptitud alimentaria |
| Material estructura y electrónica (01, 02, 03, 04, 05, 06, 08a, 12, 13, 14, 15, 16) | PLA o PETG. **Si la torre recibe sol directo** (panel), usar PETG o ASA: el PLA se ablanda a ~55–60 °C |
| Capa | 0,2 mm (0,16 mm en 08b y 08c para mejor acabado de la superficie de deslizamiento) |
| Perímetros | 3–4 (las paredes de 3 mm quedan macizas con boquilla de 0,4 mm) |
| Relleno | 20 % (giroide); 40 % en 06, 08b y 16 |
| Soportes | **No hacen falta.** Puentes presentes: techo de la abertura del pico (42 mm), techo interior del conducto y del pico (36–37 mm), esquinas del anillo superior de la tolva (≤ 17 mm), brida del pico a 45°, orejetas internas de los pods (≤ 8 mm apoyadas en dos paredes) |
| Tolerancias | Encaje entre módulos 0,3 mm por lado; ranuras de placas 1,8–2,0 mm; agujeros pasantes M3 Ø3,4; agujeros para rosca en plástico Ø2,5 |
| Prueba previa | Imprimir primero 06 y 15 (rápidas) y comprobar el MG995 y los tornillos antes de las piezas grandes |
| Filamento total | ≈ 2–2,5 kg (volumen sólido de todas las piezas ≈ 2,3 dm³). El laminador da el valor exacto |

**Higiene:** las superficies impresas tienen microsurcos entre capas. Lavar con agua tibia y jabón (no
lavavajillas: el PLA/PETG se deforma), secar bien antes de volver a cargar alimento. Para uso prolongado se
recomienda apoyar un cuenco de acero inoxidable sobre el comedero 11.

## Orden de montaje

1. **Cajón de energía (16):** fijar portapilas 2S, BMS, fusible, interruptor, cargador, elevador y los dos
   convertidores con separadores (15). **Ajustar Buck A a 6,0 V y Buck B a 5,0 V con multímetro sin carga.**
   Montar la placa de divisores. Deslizar el cajón en la base (01) y atornillar.
2. **Cuerpo (02):** atornillar la bandeja (05) al piso (tuercas por debajo) **antes** de unir con la base.
   Montar los pods 03 y 04 con sus placas (tuercas por dentro) **antes** de colocar el conducto. Pasar los
   cables por los agujeros del frente y los pasos del tabique hacia la bahía trasera.
3. Unir 02 sobre 01 (4 × M3 desde el piso), pasando los cables de 5 V, 6 V, GND y medición por el agujero del piso.
4. **Conducto (09):** bajarlo desde arriba en la zona frontal hasta apoyar en el piso. **Pico (10):** colocarlo
   desde fuera y atornillar la brida.
5. **Servo:** con el servo suelto, enviar `SERVO 1500` (centro). Atornillar el MG995 a la viga (06), apoyar la
   viga en las ménsulas, calzar con separadores de 3 mm si hace falta y atornillar.
6. Colocar 08a (labio de 02) y la placa base 08d. Verificar que la estría asome por el centro de 08d.
7. Colocar el horn redondo con el servo en 1500 µs, apoyar el disco 08b con su marca en la marca **CERRADO** de
   08d y atornillarlo al horn. Comprobar que gira libre (0,5 mm de holgura bajo el disco).
8. Calibrar las posiciones (ver `Documentation/calibration`) **sin** la placa superior: se ven las marcas.
9. Colocar 08c (chaveta en su ranura), la tolva 07, el soporte 12 con el panel (cable por el conducto de la
   esquina trasera izquierda hasta la base), la tapa 13 y el comedero 11.
