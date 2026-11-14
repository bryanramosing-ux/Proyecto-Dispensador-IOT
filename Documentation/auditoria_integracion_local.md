# Auditoría de integración — rama USB-C simplificada

## Alcance de esta revisión

Esta rama reúne ESP32 DevKit, ESP32-CAM, backend Python y dashboard local. La configuración de firmware activa un HC-SR04 para nivel de tolva y deja desactivada la detección automática de presencia.

## Estado por subsistema

| Subsistema | Estado documental/código | Validación pendiente |
|---|---|---|
| ESP32 DevKit | Control de servo, sensor de nivel y telemetría | Confirmar variante de placa y probar hardware |
| ESP32-CAM AI-Thinker | Endpoints /status, /capture y /stream MJPEG | Probar estabilidad y stream físico |
| Backend/dashboard | API, almacenamiento, galería, SSE y control manual confirmado | Prueba en LAN real y permisos del firewall |
| HC-SR04 presencia | Pines/rutinas heredadas; modo automático desactivado | No instalar para configuración actual |
| HC-SR04 nivel | Un sensor activo en GPIO19/21 | Medir divisor y calibrar tolva |
| MG995 | PWM en GPIO25; dispensación manual | Verificar alimentación, par, topes y dosis reales |
| OpenCV perro/gato | Código de visión se conserva en carpeta OpenCV | No integrado en flujo activo; requiere integración y prueba end-to-end |
| Alimentación USB-C | Documentación simplificada 5 V | Verificar fuente real, distribución, corriente y caída bajo carga |
| Mecánica STL | Modelo paramétrico contiene piezas heredadas solares y de presencia | Revisar/rediseñar cajón y excluir piezas antiguas |

## Cambios de esta revisión

- Se actualizó el README raíz con lista de componentes y alcance real.
- Se actualizó la lista de materiales, excluyendo panel solar, baterías, BMS, cargador 2S, convertidores del diseño solar, fusible antiguo, RFID/NFC, PIR y segundo sensor de presencia.
- Se reemplazó el manual Markdown solar por guía USB-C simplificada.
- Se actualizó la guía eléctrica y se marcó la tabla de cableado/placa perforada anterior como obsoleta.
- Se actualizaron las guías de firmware y mecánica.
- Se documentó que el PDF y video antiguos aún muestran el diseño solar y no deben usarse como instrucciones vigentes.

## Riesgos y decisiones que requieren confirmación física

1. Confirmar modelo exacto de ESP32 DevKit, ESP32-CAM y fuente disponible.
2. La cámara marcada “5110V0” no está identificada; no conectarla ni tratarla como reemplazo de OV2640.
3. Confirmar corriente de bloqueo del MG995 real y que la fuente de 5 V elegida soporte el conjunto.
4. Mantener rama de potencia del servo separada de la distribución lógica, con GND común y cables dimensionados.
5. Medir ECHO del HC-SR04 tras el divisor 1 kΩ/2 kΩ antes de conectarlo al GPIO21.
6. Calibrar sensor de nivel con tolva real y servo con disco montado.
7. La exclusión del fusible no es una validación de seguridad. Usar fuente con protección contra sobrecorriente y supervisar las pruebas.

## No declarar como terminado

No afirmar que la detección perro/gato está operativa, que el sistema dosifica cantidades exactas, que el stream es continuo ilimitado, que el hardware está probado ni que la alimentación es segura hasta completar pruebas físicas y documentarlas.
