# Puesta en marcha y calibración — montaje USB-C / modo manual

La configuración vigente usa una fuente regulada 5 V (5 A recomendados, confirmar
con la corriente real), un HC-SR04 de nivel, un MG995 posicional de 180° y cámara.
No conectar batería 2S, panel solar, BMS ni el circuito de convertidores del diseño
anterior. Ver [conexiones USB-C](../../docs/conexiones_usbc.md).

1. Medir polaridad y salida de la fuente sin módulos. Conectar por ramas de potencia
   separadas a lógica y servo, con GND común. El servo no se alimenta desde la placa.
   Medir tensión y corriente mientras gira; no aceptar reinicios ni tensión fuera
   del rango de la unidad MG995. Usar los condensadores del esquema.
2. Copiar los `secrets_ejemplo.h` a `secrets.h`; completar Wi-Fi y el mismo
   `TOKEN_DISPOSITIVO` en el controlador y `backend/.env`. El archivo de backend se
   obtiene de `.env.example`; no publicar los secretos. Un token vacío deshabilita
   la alimentación desde el panel.
3. Compilar y subir ambas placas. Mantener `USAR_DETECCION_AUTOMATICA 0` para el
   montaje de un solo sensor. En el PC ejecutar `python backend/dashboard_server.py`
   y permitir TCP 8001/UDP 41234 en la LAN. Confirmar telemetría, cámara y `/status`
   antes de enviar pedidos. Las instrucciones principales están en `docs/`.
4. Sin mascotas, activar temporalmente `MODO_FERIA 1` para usar `CICLO` y posicionar
   el disco con `SERVO <us>`. Medir pulsos LLENADO/DESCARGA/CERRADO y guardarlos en
   `config.h`. Pesar 10 ciclos con tolva llena, 10 con nivel medio y 10 con nivel bajo.
   Completar `plantilla_dosificacion.csv` y analizar por nivel con
   `python analizar_dosificacion.py MEDIDAS.csv --objetivo-g GRAMOS_DEFINIDOS`.
   Aceptar CV ≤10 %; ajustar mecánica/tiempos si no se cumple.
5. Con tolva vacía ejecutar `NIVEL VACIO`; con alimento hasta MAX, `NIVEL LLENO`.
   Verificar extremos, aviso al bajar de 20 %, bloqueo al confirmar ≤3 % y recarga.
6. Definir gramos por porción y límites con el responsable de la alimentación.
   Volver a `MODO_FERIA 0` y cargar la configuración de uso doméstico.
7. Probar pedido manual válido, cantidad inválida, pedido simultáneo, cooldown,
   reinicio tras entrega, cámara caída y pérdida de Wi-Fi. El botón local sigue
   disponible sin red y respeta las mismas reglas de alimentación.
8. Registrar resultados en `acta_pruebas.csv`, con firmware, medidas y evidencias.
   Completar una hora integrada sin reinicios; ampliar a 24 h para uso continuo.

Cada intento se reserva en NVS antes de mover el motor. Los contadores indican
intentos, no gramos confirmados. Sin RTC, al reiniciar se conservan las cuentas y
se renuevan conservadoramente los plazos de cooldown y 24 h. Un fallo de memoria
produce `ERROR_REGISTRO`, que RESET no borra. No borrar la flash para eludir límites.

En este montaje el monitor de riel está desactivado: no hay realimentación para
confirmar movimiento o gramos. No afirmar detección física fiable de atasco; una
confirmación exige sensores adicionales y validar su circuito. El modo automático
con visión sigue siendo opcional: necesita otro HC-SR04 y calibrar OpenCV con fotos
propias, separando las usadas para ajuste de las reservadas para evaluación final.

Para arranque automático del backend, usar la plantilla systemd de `../operacion/`
con `ExecStart=/RUTA/AL/REPO/.venv/bin/python -u /RUTA/AL/REPO/backend/dashboard_server.py`
y `WorkingDirectory=/RUTA/AL/REPO`. En Windows, configurar esas rutas en el
Programador de tareas. Mantener el PC sin suspensión durante la operación.
