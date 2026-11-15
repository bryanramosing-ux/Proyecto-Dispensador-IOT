# Plan de impresión — revisión para montaje USB-C simplificado

> Este archivo sustituye como guía de selección al plan generado antiguo. Los datos de masa/tiempo del generador original no se han recalculado: el plan antiguo incluye piezas solares y una cápsula para el sensor de presencia. No usar sus totales como estimación exacta del montaje vigente.

## Piezas a considerar para el prototipo actual

| Código STL | Pieza | Decisión |
|---|---|---|
| 01 | Base torre | Revisar cajón y fijaciones; geometría de energía antigua |
| 02 | Cuerpo principal | Usar tras comprobar dimensiones |
| 03 | Módulo HC-SR04 frontal | No imprimir: presencia automática desactivada |
| 04 | Módulo ESP32-CAM | Usar si coincide con módulo físico |
| 05 | Módulo ESP32 | Usar tras verificar placa y dimensiones |
| 06 | Soporte MG995 | Usar tras verificar servo real |
| 07 | Tolva | Usar tras revisar canal y limpieza |
| 08a–08d | Dosificador | Usar tras verificar encajes y calibrar |
| 09–10 | Conducto y salida | Usar tras prueba de caída de alimento |
| 11 | Comedero | Usar con recipiente removible apto para alimentos |
| 12a–12b | Estación solar | **No imprimir** |
| 13a–13c | Tapa y cápsula del sensor de nivel | Usar; corresponde al HC-SR04 activo |
| 14–15 | Tapa de servicio y separadores | Revisar compatibilidad |
| 16 | Cajón energía | No imprimir sin rediseño/revisión: alojaba batería, BMS y convertidores antiguos |

## Recomendaciones de fabricación

1. Medir las placas, cámara, servo y sensor físicos con calibre.
2. Imprimir primero una muestra de encaje del soporte MG995, cápsula de cámara y tapa/cápsula del HC-SR04.
3. Abrir los STL en el laminador y verificar orientación, escala y dimensiones.
4. Excluir piezas 03, 12a y 12b del lote actual.
5. No usar los totales de filamento/tiempo del plan generado anterior para calcular compras; regenerar después de actualizar el modelo CAD.
6. Para las superficies de contacto con alimento, utilizar un recipiente interior removible apto para alimentos; una pieza FDM no es automáticamente higiénica o certificada.

## Limitación pendiente

El modelo CAD aún conserva elementos heredados y no ha sido rediseñado por completo para la fuente USB-C ni para el inventario físico confirmado. La compatibilidad final se debe validar antes de imprimir todas las piezas.
