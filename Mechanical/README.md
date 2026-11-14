# Mecánica — torre modular imprimible en 3D

Este repositorio conserva un modelo mecánico que fue diseñado originalmente con piezas para el sistema solar y dos sensores. La **configuración electrónica vigente** es más simple: sin panel solar, sin batería, sin fusible y con un solo HC-SR04 activo (nivel de tolva).

> **Advertencia de compatibilidad:** los STL, imágenes de ensamblaje, renders y plan de impresión todavía contienen piezas heredadas (estación solar, cápsula frontal para HC-SR04 de presencia y cajón de energía con geometría anterior). No imprimir todas las piezas ni seguir el manual PDF antiguo sin revisar esta guía y medir los componentes reales.

## Piezas que corresponden a la mecánica funcional

- Base y cuerpo de la torre: 01 y 02.
- Soporte de ESP32: 05.
- Cápsula de ESP32-CAM: 04.
- Soporte MG995: 06.
- Tolva: 07.
- Carcasa/disco/placas del dosificador: 08a, 08b, 08c, 08d.
- Conducto y salida: 09 y 10.
- Comedero: 11.
- Tapa de tolva: 13a.
- Cápsula y tapa del sensor de nivel: 13b y 13c.
- Tapa de servicio y separadores: 14 y 15.
- Pieza 16 puede requerir rediseño o adaptación para alojar solo distribución USB-C; no asumir que sus soportes internos de batería/BMS/convertidores sirven para la fuente actual.

## Piezas heredadas que no se requieren

- 12a_Estacion_Solar_Base y 12b_Estacion_Solar_Bandeja: no imprimir para esta versión.
- 03_Modulo_HC_SR04: cápsula de sensor de presencia; no imprimir para la configuración actual con detección automática desactivada.
- La geometría interna de 16 puede corresponder al antiguo cajón de batería y convertidores; revisar antes de imprimir.

## Herramientas de generación

El modelo paramétrico se conserva en `generar_stl.py`. Las verificaciones geométricas que pasan no garantizan que el diseño se ajuste a las piezas físicas disponibles. Medir MG995, ESP32, ESP32-CAM, HC-SR04 y conectores con calibre antes de fabricar.

```bash
pip install numpy trimesh manifold3d matplotlib
python generar_stl.py
python plan_impresion.py
python render.py
```

El plan de impresión generado puede incluir las piezas heredadas. Excluir manualmente las piezas solares y el soporte de presencia; no asumir que los totales de filamento/tiempo reflejan la versión simplificada.

## Impresión y materiales

- Neptune 4 Plus: volumen nominal 320 × 320 × 385 mm; verificar cada STL en el laminador.
- Probar encajes con piezas pequeñas antes de imprimir la torre completa.
- Evitar afirmar aptitud alimentaria por el solo hecho de usar PETG: FDM deja poros y depende del filamento, boquilla y proceso. Para alimento, preferir un recipiente removible apto para alimentos.
- Revisar rebabas, grietas, holguras, limpieza y que ningún cable/electrónica pueda entrar en el canal de alimento.

## Calibración mecánica

1. Centrar MG995 sin carga.
2. Verificar que el disco gire libremente y no alcance topes.
3. Calibrar posiciones de llenado, cerrado y descarga con el firmware.
4. Probar con pequeñas cantidades de alimento y pesar cada porción.
5. Repetir varias veces y observar atascos, caída de alimento y calentamiento.

Los renders, manual PDF y video existentes corresponden a una iteración anterior y deben actualizarse antes de presentarlos como documentación vigente.
