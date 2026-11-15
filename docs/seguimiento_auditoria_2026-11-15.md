# Seguimiento de correcciones de auditoría — 2026-11-15

## Cambios aplicados
- Se establece una arquitectura eléctrica documental única para laboratorio: DevKit por USB del PC; ESP32-CAM y MG995 por fuente externa de 5 V; GND común y positivos separados.
- Se corrigen README, manual de montaje, guía eléctrica y lista de materiales para esta distribución.
- Se excluyen expresamente los archivos locales de credenciales en .gitignore.
- Se corrige un error de formato en README.

## Bloqueos antes de considerar el proyecto terminado
1. **Cantidad de HC-SR04 sin resolver:** los requisitos anteriores pedían uno para nivel y excluían el sensor de presencia, pero una auditoría posterior plantea dos. Se mantiene el firmware con `USAR_DETECCION_AUTOMATICA=0` y un solo sensor hasta confirmación expresa. No activar alimentación automática sin pruebas.
2. **Diagramas/generadores:** revisar `Documentation/wiring/generar_esquema.py`, `generar_placa_control.py` y salidas SVG/PNG con la arquitectura de dos alimentaciones. No usar diagramas sin esa comprobación.
3. **Hardware:** identificar exactamente placa DevKit, cámara, fuente, versión de MG995 y sensores; comprobar con multímetro tensión, polaridad, protección y consumo.
4. **Pruebas físicas:** completar `Documentation/calibration/acta_pruebas.csv`, incluyendo pulsos servo, gramos por porción, caídas de tensión, lecturas de nivel, stream y recuperación.
5. **Seguridad:** comprobar que nunca se hayan versionado secretos reales. .gitignore evita nuevas incorporaciones accidentales, pero no elimina secretos ya comprometidos ni sustituye una revisión del historial.
6. **OpenCV:** el reconocimiento perro/gato no forma parte del flujo activo; requiere integración y pruebas de extremo a extremo antes de habilitar acciones automáticas.
7. **Mecánica:** revisar STL heredados de solar/batería y soporte de presencia según la cantidad final de sensores.
8. **CI:** verificar GitHub Actions para esta rama después de cada modificación. CI aprobada no certifica montaje físico.
9. **Red local:** no exponer el backend a Internet; no hay autenticación de usuario completa ni TLS. Usar LAN de confianza y revisar controles antes de un despliegue mayor.

## Criterio de cierre
No declarar “sin errores” ni “listo para mascotas” hasta completar todas las comprobaciones, resolver requisitos y registrar evidencia reproducible. Mantener la rama como propuesta revisable y no fusionar a main sin CI y revisión.
