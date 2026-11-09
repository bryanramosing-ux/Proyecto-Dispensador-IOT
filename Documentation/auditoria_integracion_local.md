# Auditoría inicial y plan de integración local

## Alcance

Esta auditoría revisa la estructura existente de firmware, servidor de visión y documentación eléctrica. No afirma que el hardware haya sido probado físicamente. Se conserva la arquitectura y el código existentes; este documento identifica las diferencias que deben resolverse antes de ampliar el sistema.

## Lo que ya existe

- **ESP32 DevKit V1:** firmware modular en `ESP32/Dispensador_ESP32/`; usa HC-SR04, MG995, máquina de estados, medición de nivel de tolva, Wi-Fi y un endpoint HTTP `/status`. La dispensación automática depende de detección/clasificación y controles locales.
- **ESP32-CAM AI-Thinker:** firmware en `ESP32_CAM/Camara_ESP32CAM/`; ofrece `GET /capture` (JPEG) y `GET /status`. No ofrece streaming MJPEG.
- **Servidor local:** `OpenCV/servidor_vision.py` recibe `/classify` y `/alerta`, consulta la cámara y el ESP32, y sirve una página de estado en `/`. El frontend consulta datos mediante polling; no usa WebSockets.
- **Configuración y pruebas:** hay plantillas de credenciales, configuraciones de PlatformIO, pruebas host y documentación detallada de pines y alimentación.

## Diferencias frente a los requisitos nuevos

| Requisito | Situación encontrada | Consecuencia |
|---|---|---|
| Video MJPEG en vivo | La cámara implementa captura puntual, deliberadamente descrita como “modo foto”. | El stream debe añadirse sin bloquear `/capture`, `/status` ni el ciclo de reconexión. |
| Galería con descarga y borrado | El servidor guarda capturas de clasificación opcionalmente; la página solo muestra la última imagen analizada. | Falta una API y una interfaz para listar, descargar y borrar capturas con persistencia. |
| Dispensación manual desde web | El firmware documenta que no existe comando remoto de dispensación; el control manual de calibración es serie/USB. | Hace falta decidir expresamente si se habilita control remoto y definir autenticación, límites y prevención de doble activación. No se debe inferir ni activar una ruta de alimentación sin esa decisión. |
| USB-C, sin panel solar ni fusible | La documentación eléctrica y firmware actuales describen panel solar, batería 2S, convertidores, medición de panel y fusible. | La documentación y el circuito actuales no representan el montaje solicitado. No se debe conectar el nuevo montaje basándose en el esquema antiguo. |
| Registro persistente de eventos | Las alertas/clasificaciones tienen historial en memoria; las imágenes pueden guardarse en archivos. | El historial del proceso se pierde al reiniciar; no existe una galería respaldada por una base de datos en esta arquitectura. |
| Actualización en tiempo real | La página consulta `/panel.json` cada 5 segundos. | Es una actualización periódica, no una conexión push/WebSocket. |

## Riesgos y decisiones de ingeniería

1. **No retirar ni reutilizar conexiones del diseño solar a ciegas.** `Documentation/wiring/tabla_conexiones.md` describe una distribución de energía distinta a USB-C. Antes de reemplazarla se debe confirmar el modelo de fuente, sus salidas y la alimentación disponible para cada placa y el MG995.
2. **El MG995 requiere una línea de potencia adecuada separada de la salida GPIO.** Mantener tierra común entre la señal del ESP32 y la fuente del servo; verificar corriente de arranque/bloqueo y caída de tensión con los componentes reales. No alimentar el servo desde el GPIO ni asumir que el USB de la placa basta.
3. **Las entradas ECHO de HC-SR04 deben limitarse a nivel compatible con ESP32.** El firmware actual contempla divisores para GPIO34 y GPIO21; confirmar valores, conexiones y tensión medida antes de energizar.
4. **No se confirma compatibilidad de una fuente exclusivamente por tener conector USB-C.** El conector no determina por sí solo la tensión, corriente ni distribución segura requeridas por el conjunto.
5. **La eliminación del fusible solicitada difiere del esquema actual.** No se ha modificado la documentación eléctrica para presentar un circuito distinto como validado. La fuente y el cableado deben contar con protección contra sobrecorriente apropiada; consultar al responsable del montaje antes de eliminar una protección existente.
6. **El firmware tiene valores provisionales** para umbrales, calibración y dosis. Deben calibrarse físicamente antes de operar con una mascota.

## Plan recomendado

1. Confirmar inventario y modelo exacto de fuente USB-C, placa ESP32-CAM y servomotor; decidir qué partes del esquema anterior siguen en uso.
2. Actualizar conjuntamente `config.h`, esquemas, tabla de conexiones y README para eliminar referencias solares únicamente después de verificar el nuevo circuito y las mediciones de alimentación.
3. Implementar streaming en una tarea/servidor que no bloquee las capturas puntuales ni el manejo de errores; probar concurrencia y estabilidad antes de exponerlo al dashboard.
4. Añadir una API local de galería con nombres no predecibles, validación de rutas, límites de tamaño y almacenamiento persistente; confirmar borrado en la interfaz.
5. Mantener el control de dispensación deshabilitado desde la red hasta acordar el modelo de seguridad. Si se autoriza, exigir confirmación explícita, validación estricta, límite de frecuencia, exclusión mutua, y conservar los interbloqueos de firmware.
6. Agregar pruebas automatizadas para API, almacenamiento, estados desconectados y controles; después ejecutar compilación real para ambas placas.
7. Realizar pruebas físicas supervisadas de voltajes, consumo, reinicios, sensor, servo, cámara, Wi-Fi y recuperación. Documentar cuáles pruebas fueron físicas y cuáles simuladas.

## Validación de esta auditoría

La revisión se hizo a partir de los archivos existentes en la rama de trabajo, incluidos `ESP32/README.md`, `ESP32/Dispensador_ESP32/config.h`, `ESP32/Dispensador_ESP32/Red.cpp`, `ESP32_CAM/README.md`, `ESP32_CAM/Camara_ESP32CAM/Camara_ESP32CAM.ino`, `OpenCV/servidor_vision.py`, `OpenCV/config.py` y `Documentation/wiring/tabla_conexiones.md`. No se ejecutó compilación ni prueba de hardware en esta etapa.
