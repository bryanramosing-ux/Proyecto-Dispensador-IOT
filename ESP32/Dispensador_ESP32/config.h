// =============================================================================
//  config.h  -  Configuración del ESP32 DevKit V1 (controlador del dispensador)
// =============================================================================
//  Los valores marcados PROVISIONAL NO son datos de fábrica: son puntos de
//  partida seguros que DEBEN reemplazarse con los obtenidos en la calibración
//  (Documentation/calibration/calibracion.md).
// =============================================================================
#pragma once

// -----------------------------------------------------------------------------
// 1. PINES  (auditados: ver Documentation/wiring/tabla_conexiones.md)
// -----------------------------------------------------------------------------
#define PIN_TRIG      26  // Salida -> TRIG HC-SR04 (3,3 V es nivel TTL alto válido)
#define PIN_ECHO      34  // SOLO ENTRADA. ECHO (5 V) llega por divisor 1k/2k (~3,3 V)
#define PIN_SERVO     25  // PWM 50 Hz (LEDC) -> señal MG995 (con 330 ohm en serie)
#define PIN_VBAT      35  // ADC1_CH7: batería 2S por divisor 100k/33k
#define PIN_VSERVO    32  // ADC1_CH4: riel de 6 V del servo por divisor 100k/33k
#define PIN_VPANEL    33  // ADC1_CH5: tensión del panel solar por divisor 100k/100k
#define PIN_LED        2  // LED azul de la placa (indicador de estado)
#define PIN_BOTON      0  // Botón BOOT de la placa: pulsación larga = borrar error
#define PIN_TRIG_NIVEL 19 // Salida -> TRIG del HC-SR04 de la TOLVA (sin función de arranque)
#define PIN_ECHO_NIVEL 21 // ECHO del HC-SR04 de la tolva por divisor 1k/2k (~3,3 V)
// (19 y 21 están en la otra fila de pines del DevKit, junto al conector J5: cableado corto)
// Se usan solo canales ADC1 porque ADC2 no funciona mientras el Wi-Fi está activo.

// Factores de los divisores: (R_superior + R_inferior) / R_inferior
#define FACTOR_VBAT    ((100.0f + 33.0f) / 33.0f)
#define FACTOR_VSERVO  ((100.0f + 33.0f) / 33.0f)
#define FACTOR_VPANEL  ((100.0f + 100.0f) / 100.0f)

// -----------------------------------------------------------------------------
// 2. RED  (ajustar a la red real; Wi-Fi 2,4 GHz WPA2-Personal)
// -----------------------------------------------------------------------------
// SSID y contraseña van en secrets.h (copiar secrets_ejemplo.h -> secrets.h)
#define IP_ESP32        "192.168.1.52"   // "" = usar DHCP
#define IP_GATEWAY      "192.168.1.1"
#define IP_MASCARA      "255.255.255.0"
#define URL_PC          "http://192.168.1.50:8000"   // servidor_vision.py
#define URL_CAMARA      "http://192.168.1.51"        // ESP32-CAM

#define TIMEOUT_CONEXION_MS     2000UL   // conexión TCP
#define TIMEOUT_CLASIFICAR_MS  10000UL   // respuesta completa de /classify
#define TIMEOUT_ESTADO_MS       2000UL   // /status de cámara o PC
#define WIFI_REINTENTO_MS       5000UL   // cada cuánto reintentar Wi-Fi
#define WIFI_REINICIO_MS      300000UL   // sin Wi-Fi 5 min -> reiniciar ESP32
#define ERROR_REINTENTO_MS     30000UL   // reintento en ERROR_CAMARA / ERROR_CLASIFICACION

// -----------------------------------------------------------------------------
// 3. DETECCIÓN CON HC-SR04  (PROVISIONAL: calibrar en el lugar de uso)
// -----------------------------------------------------------------------------
#define DIST_MIN_CM            3.0f   // < 3 cm: sensor tapado o lectura inválida
#define DIST_DETECCION_CM     35.0f   // mascota "presente" si está más cerca que esto
#define DIST_LIBRE_CM         50.0f   // zona "libre" si está más lejos (histéresis)
#define LECTURAS_CONFIRMACION     3   // lecturas seguidas para confirmar presencia
#define ZONA_LIBRE_MS         3000UL  // tiempo de zona libre para rearmar la detección
#define N_MUESTRAS_DIST           3   // mediana de N disparos (>=60 ms entre disparos)
#define TIMEOUT_ECO_US        30000UL // ~5 m: sin eco = nada delante

// -----------------------------------------------------------------------------
// 4. CLASIFICACIÓN
// -----------------------------------------------------------------------------
#define MAX_INTENTOS_CLASIFICACION   3   // resultados 0 seguidos antes de desistir
#define REINTENTO_CLASIFICACION_MS 4000UL

// -----------------------------------------------------------------------------
// 5. DOSIFICADOR (disco volumétrico + MG995 de 180°)
//    Posiciones en microsegundos de pulso. PROVISIONAL: se calibran con el
//    comando serie "SERVO <us>" alineando las marcas del disco (ver calibración).
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

// Ración = número de ciclos completos (llenar->descargar). Los GRAMOS por ciclo
// se miden con balanza (calibración). PROVISIONAL.
#define CICLOS_PERRO            3
#define CICLOS_GATO             1
#define HABILITAR_PERRO      true
#define HABILITAR_GATO       true
#define MAX_CICLOS_POR_RACION  10    // límite duro anti-sobrealimentación

// -----------------------------------------------------------------------------
// 6. CONTROL DE REPETICIONES (política de uso, no dato físico)
// -----------------------------------------------------------------------------
#define MODO_FERIA 1   // 1 = tiempos cortos para demostración; 0 = uso doméstico
#if MODO_FERIA
  #define COOLDOWN_GLOBAL_MS      30000UL   // 30 s entre raciones (cualquier mascota)
  #define COOLDOWN_PERRO_MS       60000UL
  #define COOLDOWN_GATO_MS        60000UL
  #define MAX_RACIONES_DIA_PERRO     40
  #define MAX_RACIONES_DIA_GATO      40
#else
  #define COOLDOWN_GLOBAL_MS     600000UL   // 10 min
  #define COOLDOWN_PERRO_MS    14400000UL   // 4 h (definir con el veterinario/dueño)
  #define COOLDOWN_GATO_MS     10800000UL   // 3 h
  #define MAX_RACIONES_DIA_PERRO      3
  #define MAX_RACIONES_DIA_GATO       4
#endif

// -----------------------------------------------------------------------------
// 7. ENERGÍA
// -----------------------------------------------------------------------------
// Poner en 0 durante pruebas de banco alimentadas por USB sin batería.
#define USAR_MONITOR_BATERIA  1
#define VBAT_MIN            6.8f   // 2S Li-ion: 3,4 V/celda -> se deja de dispensar
#define VBAT_HISTERESIS     0.2f   // vuelve a funcionar por encima de 7,0 V
// Poner USAR_MONITOR_SERVO en 0 si el divisor del riel de 6 V (GPIO32) no está
// montado (pruebas de banco): sin él la lectura es ~0 V y toda dosis daría ERROR_SERVO.
// Detección INDIRECTA: el MG995 no informa su posición. Un bloqueo eleva la
// corriente y hace caer el riel de 6 V; cuánto cae depende del convertidor y
// del cableado -> umbrales PROVISIONALES, se ajustan en la Prueba 7.
#define USAR_MONITOR_SERVO    1
#define VSERVO_MIN          4.6f   // PROVISIONAL: riel ausente/bajo -> ERROR_SERVO
#define VSERVO_CAIDA        4.2f   // PROVISIONAL: caída sostenida durante el giro -> posible atasco
#define T_CAIDA_MS          250    // PROVISIONAL: duración mínima de la caída
#define REINTENTOS_ATASCO     2    // retrocesos antes de declarar ERROR_MECANISMO

// -----------------------------------------------------------------------------
// 8. NIVEL DE ALIMENTO EN LA TOLVA (segundo HC-SR04, montado en la tapa)
//    Recomendación del profesor: avisar cuando la comida se está acabando.
// -----------------------------------------------------------------------------
#define USAR_SENSOR_NIVEL        1
#define INTERVALO_NIVEL_MS   60000UL   // una medición por minuto (y tras cada ración)
// Los porcentajes son de VOLUMEN restante (no de altura): ver NivelGeometria.h.
// Con la tolva del modelo 3D (≈ 630 cm3 hasta la línea MAX): 20 % ≈ 125 cm3.
#define NIVEL_ALERTA_PCT      20.0f    // PROVISIONAL: por debajo -> alerta COMIDA_BAJA
#define NIVEL_REARME_PCT      30.0f    // por encima -> COMIDA_REPUESTA (histéresis)
#define NIVEL_VACIO_PCT        3.0f    // PROVISIONAL: por debajo -> COMIDA_AGOTADA, no dispensa
#define LECTURAS_NIVEL            3    // lecturas seguidas para confirmar un cambio
#define REINTENTO_ALERTA_MS  30000UL   // si el PC no recibió la alerta, se reenvía
#define N_MUESTRAS_NIVEL          5    // mediana de 5 disparos
// Distancias por defecto (sensor -> superficie). Se CALIBRAN con los comandos serie
// "NIVEL VACIO" y "NIVEL LLENO" y quedan guardadas en la memoria flash (NVS).
#define DIST_TOLVA_VACIA_CM   16.0f    // PROVISIONAL: tolva vacía (medida en el modelo 3D)
#define DIST_TOLVA_LLENA_CM    3.0f    // PROVISIONAL: alimento en la marca MAX

#define T_BOTON_RESET_MS   2000UL  // pulsación larga del botón BOOT
#define INTERVALO_CICLO_MS   50UL  // periodo del lazo principal
