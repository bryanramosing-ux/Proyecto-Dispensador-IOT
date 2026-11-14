// =============================================================================
//  config.h  -  Configuración del ESP32 DevKit V1 (controlador del dispensador)
// =============================================================================
//  Montaje vigente: alimentación por USB-C (5 V), SIN panel solar, SIN batería
//  y SIN fusible. Esquema y tablas: docs/conexiones_usbc.md
//
//  Los datos de TU red (Wi-Fi, token, IP) NO van aquí: van en secrets.h
//  (copiar secrets_ejemplo.h -> secrets.h; ese archivo no se sube a GitHub).
//
//  Los valores marcados PROVISIONAL NO son datos de fábrica: son puntos de
//  partida seguros que DEBEN reemplazarse con los obtenidos en la calibración
//  (docs/pruebas.md).
// =============================================================================
#pragma once

#define VERSION_FIRMWARE "2.0.0"

// -----------------------------------------------------------------------------
// 1. PINES  (auditados: ver docs/conexiones_usbc.md)
// -----------------------------------------------------------------------------
#define PIN_TRIG_NIVEL 19 // Salida -> TRIG del HC-SR04 de la TOLVA (3,3 V es nivel alto válido)
#define PIN_ECHO_NIVEL 21 // ECHO (5 V) del HC-SR04 por divisor 1k/2k (~3,3 V)
#define PIN_SERVO      25 // PWM 50 Hz (LEDC) -> señal MG995 (330 ohm en serie + 10k a GND)
#define PIN_LED         2 // LED azul de la placa (indicador de estado)
#define PIN_BOTON       0 // Botón BOOT: pulsación corta = 1 porción; larga (2 s) = borrar error
// Opcionales (solo si se activan más abajo):
#define PIN_TRIG       26 // TRIG del HC-SR04 de PRESENCIA (USAR_DETECCION_AUTOMATICA)
#define PIN_ECHO       34 // ECHO de presencia por divisor 1k/2k. GPIO34 es solo entrada
#define PIN_VSERVO     32 // ADC1_CH4: riel de 5 V del servo por divisor 100k/33k (USAR_MONITOR_SERVO)
#define PIN_VBAT       35 // ADC1_CH7: batería por divisor 100k/33k (USAR_MONITOR_BATERIA; no se usa con USB-C)
// Se usan solo canales ADC1 porque ADC2 no funciona mientras el Wi-Fi está activo.

// Factores de los divisores de medición: (R_superior + R_inferior) / R_inferior
#define FACTOR_VBAT    ((100.0f + 33.0f) / 33.0f)
#define FACTOR_VSERVO  ((100.0f + 33.0f) / 33.0f)

// -----------------------------------------------------------------------------
// 2. RED  (los datos propios de la red van en secrets.h)
// -----------------------------------------------------------------------------
#define NOMBRE_MDNS            "dispensador"   // http://dispensador.local/status
#define PUERTO_DESCUBRIMIENTO  41234           // UDP: el ESP32 busca al backend en la LAN
#define DESCUBRIMIENTO_MS       3000UL         // cada cuánto pregunta mientras no lo encuentra
#define TELEMETRIA_MS           2000UL         // envío periódico del estado al backend
#define TELEMETRIA_MAX_MS      30000UL         // espera máxima entre reintentos si el backend no responde
#define TIMEOUT_BACKEND_CONEXION_MS  800       // conexión TCP con el backend (corto: no frena el control)
#define TIMEOUT_BACKEND_MS          1500       // respuesta del backend
#define MAX_INTENTOS_TOKEN             5       // tokens incorrectos seguidos antes de bloquear
#define BLOQUEO_TOKEN_MS           60000UL     // bloqueo de comandos remotos tras esos intentos

#define TIMEOUT_CONEXION_MS     2000UL   // (modo automático) conexión con el servidor de visión
#define TIMEOUT_CLASIFICAR_MS  10000UL   // (modo automático) respuesta completa de /classify
#define TIMEOUT_ESTADO_MS       2000UL   // (modo automático) /status de cámara o PC
#define WIFI_REINTENTO_MS       5000UL   // cada cuánto reintentar Wi-Fi
#define WIFI_REINICIO_MS      300000UL   // (modo automático) sin Wi-Fi 5 min -> reiniciar ESP32
#define ERROR_REINTENTO_MS     30000UL   // reintento en ERROR_CAMARA / ERROR_CLASIFICACION

// -----------------------------------------------------------------------------
// 3. DISPENSACIÓN MANUAL (panel web, botón BOOT y comando serie DISPENSAR)
// -----------------------------------------------------------------------------
#define HABILITAR_MANUAL         true
#define CICLOS_POR_PORCION          1    // PROVISIONAL: ciclos del disco por porción (pesar con balanza)
#define MAX_PORCIONES_MANUAL        3    // máximo por pedido: un pedido inválido NO mueve el servo
#define BOTON_DISPENSA_LOCAL        1    // 1 = pulsación corta de BOOT entrega 1 porción (control local sin Wi-Fi)

// -----------------------------------------------------------------------------
// 4. MODO AUTOMÁTICO OPCIONAL (segundo HC-SR04 de presencia + visión en el PC)
//    Con el montaje USB-C de un solo HC-SR04 debe quedar en 0.
// -----------------------------------------------------------------------------
#define USAR_DETECCION_AUTOMATICA   0
#define DIST_MIN_CM            3.0f   // < 3 cm: sensor tapado o lectura inválida
#define DIST_DETECCION_CM     35.0f   // mascota "presente" si está más cerca que esto
#define DIST_LIBRE_CM         50.0f   // zona "libre" si está más lejos (histéresis)
#define LECTURAS_CONFIRMACION     3   // lecturas seguidas para confirmar presencia
#define ZONA_LIBRE_MS         3000UL  // tiempo de zona libre para rearmar la detección
#define N_MUESTRAS_DIST           3   // mediana de N disparos (>=60 ms entre disparos)
#define TIMEOUT_ECO_US        30000UL // ~5 m: sin eco = nada delante
#define MAX_INTENTOS_CLASIFICACION   5   // fotos con resultado 0 seguidas antes de desistir
#define REINTENTO_CLASIFICACION_MS 2000UL // espera entre fotos de una misma visita
#define CICLOS_PERRO            3
#define CICLOS_GATO             1
#define HABILITAR_PERRO      true
#define HABILITAR_GATO       true

// -----------------------------------------------------------------------------
// 5. DOSIFICADOR (disco volumétrico + MG995 de 180°)
//    Posiciones en microsegundos de pulso. PROVISIONAL: se calibran con el
//    comando serie "SERVO <us>" alineando las marcas del disco.
// -----------------------------------------------------------------------------
#define PULSO_MIN_US          500    // límites absolutos de seguridad del software
#define PULSO_MAX_US         2500
#define PULSO_CERRADO_US     1500    // PROVISIONAL: bolsillo entre entrada y salida
#define PULSO_LLENADO_US     1000    // PROVISIONAL: bolsillo bajo la entrada de la tolva
#define PULSO_DESCARGA_US    2000    // PROVISIONAL: bolsillo sobre la salida al conducto
#define PASO_US                10    // rampa: incremento por paso
#define PASO_MS                10    // rampa: tiempo por paso (~1 s por 1000 us)
#define T_LLENADO_MS          700    // PROVISIONAL: espera para que caiga el alimento
#define T_DESCARGA_MS         600    // PROVISIONAL: espera para vaciar el bolsillo
#define AGITACIONES             2    // pequeñas oscilaciones para asentar/vaciar
#define AGITACION_US           40    // amplitud de la oscilación (~4°)
#define MAX_CICLOS_POR_RACION  10    // límite duro anti-sobrealimentación

// -----------------------------------------------------------------------------
// 6. CONTROL DE REPETICIONES (política de uso, no dato físico)
// -----------------------------------------------------------------------------
#define MODO_FERIA 1   // 1 = tiempos cortos para demostración; 0 = uso doméstico
#if MODO_FERIA
  #define COOLDOWN_GLOBAL_MS      15000UL   // 15 s entre raciones (cualquier origen)
  #define COOLDOWN_PERRO_MS       60000UL
  #define COOLDOWN_GATO_MS        60000UL
  #define COOLDOWN_MANUAL_MS          0UL   // la manual solo respeta el global
  #define MAX_RACIONES_DIA_PERRO     40
  #define MAX_RACIONES_DIA_GATO      40
  #define MAX_RACIONES_DIA_MANUAL    40
#else
  #define COOLDOWN_GLOBAL_MS     600000UL   // 10 min
  #define COOLDOWN_PERRO_MS    14400000UL   // 4 h (definir con el veterinario/dueño)
  #define COOLDOWN_GATO_MS     10800000UL   // 3 h
  #define COOLDOWN_MANUAL_MS    1800000UL   // 30 min
  #define MAX_RACIONES_DIA_PERRO      3
  #define MAX_RACIONES_DIA_GATO       4
  #define MAX_RACIONES_DIA_MANUAL     6
#endif

// -----------------------------------------------------------------------------
// 7. ENERGÍA (USB-C 5 V)
// -----------------------------------------------------------------------------
// No hay batería: el monitor de batería queda apagado.
#define USAR_MONITOR_BATERIA  0
#define VBAT_MIN            6.8f
#define VBAT_HISTERESIS     0.2f
// Monitor OPCIONAL del riel de 5 V del servo (divisor 100k/33k en GPIO32).
// Dejar en 0 si el divisor no está montado: sin él la lectura es ~0 V y toda
// dosis daría ERROR_SERVO. Con 1 se gana la detección INDIRECTA de atascos
// (un bloqueo eleva la corriente y hace caer el riel). Umbrales PROVISIONALES
// para un riel de 5 V: medir la caída real con el servo cargado antes de fiarse.
#define USAR_MONITOR_SERVO    0
#define VSERVO_MIN          4.3f   // PROVISIONAL: riel ausente/bajo -> ERROR_SERVO
#define VSERVO_CAIDA        4.0f   // PROVISIONAL: caída sostenida durante el giro -> posible atasco
#define T_CAIDA_MS          250    // PROVISIONAL: duración mínima de la caída
#define REINTENTOS_ATASCO     2    // retrocesos antes de declarar ERROR_MECANISMO

// -----------------------------------------------------------------------------
// 8. NIVEL DE ALIMENTO EN LA TOLVA (HC-SR04 montado en la tapa, mirando hacia abajo)
// -----------------------------------------------------------------------------
#define USAR_SENSOR_NIVEL        1
#define INTERVALO_NIVEL_MS    5000UL   // una medición cada 5 s (y tras cada ración)
// Los porcentajes son de VOLUMEN restante (no de altura): ver NivelGeometria.h.
#define NIVEL_ALERTA_PCT      20.0f    // PROVISIONAL: por debajo -> alerta COMIDA_BAJA
#define NIVEL_REARME_PCT      30.0f    // por encima -> COMIDA_REPUESTA (histéresis)
#define NIVEL_VACIO_PCT        3.0f    // PROVISIONAL: por debajo -> COMIDA_AGOTADA, no dispensa
#define LECTURAS_NIVEL            3    // lecturas seguidas para confirmar un cambio
#define REINTENTO_ALERTA_MS  30000UL   // si el backend no recibió la alerta, se reenvía
#define N_MUESTRAS_NIVEL          3    // mediana de 3 disparos (~0,2 s de medición)
#define TIMEOUT_ECO_NIVEL_US  12000UL  // ~2 m: de sobra para una tolva; acorta la espera sin eco
// Distancias por defecto (sensor -> superficie). Se CALIBRAN con los comandos serie
// "NIVEL VACIO" y "NIVEL LLENO" y quedan guardadas en la memoria flash (NVS).
#define DIST_TOLVA_VACIA_CM   15.0f    // PROVISIONAL: transductores -> boca del embudo en el modelo 3D
#define DIST_TOLVA_LLENA_CM    3.0f    // PROVISIONAL: transductores -> surco MAX (modelo 3D)

#define T_BOTON_RESET_MS   2000UL  // pulsación larga del botón BOOT = borrar error
#define T_BOTON_CORTO_MIN_MS 50UL  // antirrebote de la pulsación corta
#define T_BOTON_CORTO_MAX_MS 1000UL
#define INTERVALO_CICLO_MS   50UL  // periodo del lazo principal
