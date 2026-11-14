// =============================================================================
//  DISPENSADOR INTELIGENTE DE ALIMENTO PARA MASCOTAS  -  IoT local
//  Firmware del ESP32 DevKit V1 (controlador y actuador)
// =============================================================================
//  Montaje vigente: USB-C 5 V, un HC-SR04 (nivel de la tolva) y un MG995.
//
//  Responsabilidades del ESP32:
//    * Medir el nivel de alimento de la tolva (HC-SR04) y avisar cuando se acaba.
//    * Dispensar a pedido: panel web (comando HTTP con token), botón BOOT de la
//      placa (control local, funciona sin Wi-Fi) o comando serie DISPENSAR.
//    * VALIDAR cada pedido (porciones, cooldown, límite diario, tolva vacía,
//      errores, dosis en curso) antes de mover el servo.
//    * Generar la señal PWM del MG995 (solo señal: el servo se alimenta aparte).
//    * Enviar su estado al backend (JSON) y responder GET /status.
//    * Seguir funcionando aunque no haya Wi-Fi ni backend.
//    * (Opcional, USAR_DETECCION_AUTOMATICA) detectar a la mascota con un segundo
//      HC-SR04 y pedir la clasificación al servidor de visión del PC.
//
//  Entorno: Arduino IDE (núcleo esp32 2.x o 3.x) o PlatformIO.
//  Biblioteca externa: ArduinoJson 7 (Benoît Blanchon).
// =============================================================================
#include <Arduino.h>
#include <WiFi.h>

#include "Controlador.h"
#include "Dosificador.h"
#include "Energia.h"
#include "NivelGeometria.h"
#include "NivelTolva.h"
#include "Red.h"
#include "Ultrasonico.h"
#include "config.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#warning "Falta secrets.h: se usa secrets_ejemplo.h (copie y complete sus datos de Wi-Fi)"
#include "secrets_ejemplo.h"
#endif

// ----------------------------------------------------------------------------
// Módulos de hardware
// ----------------------------------------------------------------------------
Energia energia;
Ultrasonico ultrasonico(PIN_TRIG, PIN_ECHO, N_MUESTRAS_DIST, TIMEOUT_ECO_US);  // presencia (opcional)
NivelTolva nivel(PIN_TRIG_NIVEL, PIN_ECHO_NIVEL);
Dosificador dosificador(PIN_SERVO, energia, USAR_MONITOR_SERVO);
Red red;

// ----------------------------------------------------------------------------
// Botón BOOT: una pulsación corta = 1 porción (control local); mantenerlo 2 s =
// borrar error. Cada pulsación produce UN solo evento: hay que soltarlo para el
// siguiente (un botón trabado o GPIO0 a nivel bajo no repite acciones).
// ----------------------------------------------------------------------------
class Boton {
 public:
  void leer() {
    bool pulsado = digitalRead(PIN_BOTON) == LOW;
    uint32_t ahora = millis();
    if (pulsado) {
      if (!antes_) tInicio_ = ahora;
      if (!largoEmitido_ && ahora - tInicio_ >= T_BOTON_RESET_MS) {
        largoEmitido_ = true;
        largo_ = true;
      }
    } else if (antes_) {
      uint32_t duracion = ahora - tInicio_;
      if (!largoEmitido_ && duracion >= T_BOTON_CORTO_MIN_MS && duracion <= T_BOTON_CORTO_MAX_MS) corto_ = true;
      largoEmitido_ = false;
    }
    antes_ = pulsado;
  }
  bool tomarCorto() {
    bool v = corto_;
    corto_ = false;
    return v;
  }
  bool tomarLargo() {
    bool v = largo_;
    largo_ = false;
    return v;
  }

 private:
  bool antes_ = false, largoEmitido_ = false, corto_ = false, largo_ = false;
  uint32_t tInicio_ = 0;
};
Boton boton;

void atenderRedDuranteDosis() { red.atender(); }

// Une los módulos reales con la interfaz que usa la máquina de estados.
class HardwareReal : public Hardware {
 public:
  uint32_t ahoraMs() override { return millis(); }
  float distanciaCm() override { return ultrasonico.medirCm(); }
  bool wifiConectado() override { return red.conectado(); }
  void reconectarWifi() override { red.reconectar(); }
  bool camaraDisponible() override { return red.camaraDisponible(); }
  bool servidorDisponible() override { return red.servidorDisponible(); }
  RespuestaClasificacion clasificar(int d) override { return red.clasificar(d); }
  float voltajeBateria() override { return energia.bateria(); }
  float voltajeServo() override { return energia.servo(); }
  float nivelTolvaPct() override { return USAR_SENSOR_NIVEL ? nivel.porcentaje() : -1.0f; }
  bool notificar(Alerta a, float n) override { return red.notificar(nombreAlerta(a), n); }
  ResultadoDosis dosificar(uint8_t ciclos) override {
    digitalWrite(PIN_LED, HIGH);
    ResultadoDosis r = dosificador.dosificar(ciclos);
    digitalWrite(PIN_LED, LOW);
    return r;
  }
  bool botonResetPulsado() override { return boton.tomarLargo(); }
  bool botonDispensarPulsado() override { return boton.tomarCorto(); }
  void reiniciar() override {
    delay(200);
    ESP.restart();
  }
  void log(const char* m) override {
    Serial.printf("[%10lu] %s\n", (unsigned long)millis(), m);
  }
};

HardwareReal hardware;

Parametros crearParametros() {
  Parametros p = {};
  p.usarDeteccionAutomatica = USAR_DETECCION_AUTOMATICA;
  p.distMinCm = DIST_MIN_CM;
  p.distDeteccionCm = DIST_DETECCION_CM;
  p.distLibreCm = DIST_LIBRE_CM;
  p.lecturasConfirmacion = LECTURAS_CONFIRMACION;
  p.zonaLibreMs = ZONA_LIBRE_MS;
  p.maxIntentosClasificacion = MAX_INTENTOS_CLASIFICACION;
  p.reintentoClasificacionMs = REINTENTO_CLASIFICACION_MS;
  p.ciclos[CLASE_PERRO] = CICLOS_PERRO;          p.habilitada[CLASE_PERRO] = HABILITAR_PERRO;
  p.ciclos[CLASE_GATO] = CICLOS_GATO;            p.habilitada[CLASE_GATO] = HABILITAR_GATO;
  p.ciclos[CLASE_MANUAL] = CICLOS_POR_PORCION;   p.habilitada[CLASE_MANUAL] = HABILITAR_MANUAL;
  p.cooldownClaseMs[CLASE_PERRO] = COOLDOWN_PERRO_MS;
  p.cooldownClaseMs[CLASE_GATO] = COOLDOWN_GATO_MS;
  p.cooldownClaseMs[CLASE_MANUAL] = COOLDOWN_MANUAL_MS;
  p.maxRacionesDia[CLASE_PERRO] = MAX_RACIONES_DIA_PERRO;
  p.maxRacionesDia[CLASE_GATO] = MAX_RACIONES_DIA_GATO;
  p.maxRacionesDia[CLASE_MANUAL] = MAX_RACIONES_DIA_MANUAL;
  p.maxPorcionesManual = MAX_PORCIONES_MANUAL;
  p.botonDispensa = BOTON_DISPENSA_LOCAL;
  p.maxCiclosPorRacion = MAX_CICLOS_POR_RACION;
  p.cooldownGlobalMs = COOLDOWN_GLOBAL_MS;
  p.usarMonitorBateria = USAR_MONITOR_BATERIA;
  p.vbatMin = VBAT_MIN;
  p.vbatHisteresis = VBAT_HISTERESIS;
  p.usarMonitorServo = USAR_MONITOR_SERVO;
  p.vservoMin = VSERVO_MIN;
  p.wifiReintentoMs = WIFI_REINTENTO_MS;
  p.wifiReinicioMs = WIFI_REINICIO_MS;
  p.errorReintentoMs = ERROR_REINTENTO_MS;
  p.usarSensorNivel = USAR_SENSOR_NIVEL;
  p.intervaloNivelMs = INTERVALO_NIVEL_MS;
  p.nivelAlertaPct = NIVEL_ALERTA_PCT;
  p.nivelRearmePct = NIVEL_REARME_PCT;
  p.nivelVacioPct = NIVEL_VACIO_PCT;
  p.lecturasNivel = LECTURAS_NIVEL;
  p.reintentoAlertaMs = REINTENTO_ALERTA_MS;
  return p;
}

Controlador controlador(hardware, crearParametros());

// ----------------------------------------------------------------------------
// Estado en JSON: es el mismo documento para GET /status y para la telemetría
// que se envía al backend. Cada campo está explicado en docs/arquitectura.md.
// ----------------------------------------------------------------------------
const char* estadoServo() {
  Estado e = controlador.estado();
  if (e == Estado::DOSIFICANDO) return "DISPENSANDO";
  if (e == Estado::ERROR_SERVO || e == Estado::ERROR_MECANISMO) return "ERROR";
  return "REPOSO";
}

String estadoJson() {
  const Estado e = controlador.estado();
  const bool enError = e >= Estado::ERROR_WIFI;
  const bool dispensando = e == Estado::DOSIFICANDO || controlador.dosisPendiente();
  const float nivelPct = controlador.nivelTolva();
  const long haceS = controlador.huboDosis() ? (long)(controlador.msDesdeUltimaDosis() / 1000) : -1L;
  char buf[1024];
  snprintf(buf, sizeof(buf),
           "{\"dispositivo\":\"ESP32\",\"fw\":\"%s\",\"modo\":\"%s\",\"estado\":\"%s\",\"error\":\"%s\","
           "\"wifi_conectado\":%s,\"ip\":\"%s\",\"rssi\":%d,\"backend\":%s,"
           "\"sensor_nivel_ok\":%s,\"distancia_nivel_cm\":%.1f,\"nivel_tolva\":%.0f,"
           "\"alerta_tolva\":\"%s\",\"alerta_pendiente\":%s,"
           "\"servo\":\"%s\",\"dispensando\":%s,\"pulso_servo_us\":%u,"
           "\"dispensaciones_total\":%lu,\"dispensaciones_24h\":%u,"
           "\"ultima_dispensacion_hace_s\":%ld,\"ultimo_origen\":\"%s\",\"ultimas_porciones\":%u,"
           "\"ultimo_resultado\":\"%s\",\"cooldown_s\":%lu,\"max_porciones\":%d,"
           "\"distancia_cm\":%.1f,\"ultima_clase\":%d,\"ultima_confianza\":%.2f,\"ultimo_motivo\":\"%s\","
           "\"raciones_perro\":%lu,\"raciones_gato\":%lu,\"raciones_manual\":%lu,"
           "\"v_servo\":%.2f,\"v_bateria\":%.2f,\"uptime_s\":%lu,\"heap\":%u}",
           VERSION_FIRMWARE, controlador.modoAutomatico() ? "AUTOMATICO" : "MANUAL", nombreEstado(e),
           enError ? nombreEstado(e) : "",
           red.conectado() ? "true" : "false", red.ip().c_str(), red.rssi(),
           red.backendConocido() ? "true" : "false",
           nivelPct >= 0 ? "true" : "false", nivel.ultimaDistanciaCm(), nivelPct,
           nombreAlerta(controlador.alertaNivel()), controlador.alertaPendiente() ? "true" : "false",
           estadoServo(), dispensando ? "true" : "false", (unsigned)dosificador.pulsoActual(),
           (unsigned long)controlador.intentosDosis(), (unsigned)controlador.racionesUltimas24hTotal(),
           haceS, nombreOrigen(controlador.ultimoOrigen()), (unsigned)controlador.ultimasPorciones(),
           nombreResultado(controlador.ultimoResultado()),
           (unsigned long)((controlador.cooldownRestanteMs() + 999) / 1000), MAX_PORCIONES_MANUAL,
           controlador.ultimaDistancia(), controlador.ultimaClase(), controlador.ultimaConfianza(),
           controlador.ultimoMotivo(),
           (unsigned long)controlador.racionesTotales(CLASE_PERRO),
           (unsigned long)controlador.racionesTotales(CLASE_GATO),
           (unsigned long)controlador.racionesTotales(CLASE_MANUAL),
           energia.servo(), energia.bateria(), (unsigned long)(millis() / 1000),
           (unsigned)ESP.getFreeHeap());
  return String(buf);
}

// Comandos remotos (ya autenticados por Red con el token)
Solicitud dispensarRemoto(uint8_t porciones) { return controlador.solicitarDispensacion(porciones, Origen::PANEL); }
bool borrarErroresRemoto() { return controlador.borrarErrores(); }
uint32_t cooldownSegundos() { return (controlador.cooldownRestanteMs() + 999) / 1000; }

// ----------------------------------------------------------------------------
// Telemetría hacia el backend: cada TELEMETRIA_MS y de inmediato cuando cambia
// algo importante. Si el backend no responde, los intentos se espacian hasta
// TELEMETRIA_MAX_MS para no frenar el lazo de control con conexiones fallidas.
// ----------------------------------------------------------------------------
void gestionarTelemetria() {
  static uint32_t tUltimo = 0, espera = TELEMETRIA_MS;
  static Estado estadoPrevio = Estado::ESPERANDO;
  static Alerta alertaPrevia = Alerta::NINGUNA;
  static uint32_t dosisPrevias = 0;
  static bool pendientePrevio = false;
  if (!red.conectado() || !red.backendConocido()) return;

  const bool cambio = controlador.estado() != estadoPrevio || controlador.alertaNivel() != alertaPrevia ||
                      controlador.intentosDosis() != dosisPrevias ||
                      controlador.dosisPendiente() != pendientePrevio;
  const uint32_t ahora = millis();
  const bool sano = espera == TELEMETRIA_MS;   // sin fallos recientes: se puede enviar al instante
  if (!(ahora - tUltimo >= espera || (cambio && sano))) return;

  tUltimo = ahora;
  estadoPrevio = controlador.estado();
  alertaPrevia = controlador.alertaNivel();
  dosisPrevias = controlador.intentosDosis();
  pendientePrevio = controlador.dosisPendiente();
  if (red.enviarTelemetria(estadoJson())) {
    espera = TELEMETRIA_MS;
  } else {
    espera = espera * 2 > TELEMETRIA_MAX_MS ? TELEMETRIA_MAX_MS : espera * 2;
  }
}

// ----------------------------------------------------------------------------
// Comandos por monitor serie (115200 baudios) para pruebas y CALIBRACIÓN.
// ----------------------------------------------------------------------------
bool estadoPermiteManual() {
  Estado e = controlador.estado();
  return e == Estado::ESPERANDO || e >= Estado::ERROR_WIFI;
}

void procesarComando(String linea) {
  linea.trim();
  String cmd = linea;
  String resto = "";
  long arg = 0;
  int esp = linea.indexOf(' ');
  if (esp > 0) {
    cmd = linea.substring(0, esp);
    resto = linea.substring(esp + 1);
    arg = resto.toInt();
  }
  cmd.toUpperCase();
  resto.toUpperCase();

  if (cmd == "AYUDA" || cmd == "?") {
    Serial.println(F("NIVEL [VACIO|LLENO] | DISPENSAR <n> | SERVO <us> | CICLO <n> | RED | ENERGIA | ESTADO | RESET | DIST | CLASIFICAR"));
  } else if (cmd == "DIST") {
    if (USAR_DETECCION_AUTOMATICA) {
      Serial.printf("Distancia: %.1f cm\n", ultrasonico.medirCm());
    } else {
      Serial.println(F("Sensor de presencia desactivado (USAR_DETECCION_AUTOMATICA 0). Use NIVEL"));
    }
  } else if (cmd == "NIVEL") {
    if (resto == "VACIO" || resto == "LLENO") {
      bool ok = resto == "VACIO" ? nivel.calibrarVacia() : nivel.calibrarLlena();
      Serial.printf("Calibracion %s: %s (vacia %.1f cm, llena %.1f cm)\n", resto.c_str(),
                    ok ? "guardada" : "SIN ECO, no se guardo", nivel.distVacia(), nivel.distLlena());
    } else {
      float d = nivel.distanciaCm();
      float h = nivel.alturaPct(d);
      if (h < 0) {
        Serial.printf("Nivel tolva: sin lectura (distancia %.1f cm)\n", d);
      } else {
        Serial.printf("Nivel tolva: %.0f %% del volumen (altura %.0f %%, distancia %.1f cm; vacia %.1f, llena %.1f)\n",
                      alturaAVolumenPct(h), h, d, nivel.distVacia(), nivel.distLlena());
      }
    }
  } else if (cmd == "ENERGIA") {
    if (USAR_MONITOR_SERVO) {
      Serial.printf("Riel del servo: %.2f V\n", energia.servo());
    } else {
      Serial.println(F("Monitor del riel del servo desactivado (USAR_MONITOR_SERVO 0): medir con multimetro"));
    }
  } else if (cmd == "RED") {
    Serial.printf("Wi-Fi %s | IP %s | RSSI %d dBm | backend %s\n", red.conectado() ? "conectado" : "SIN CONEXION",
                  red.ip().c_str(), red.rssi(),
                  red.backendConocido() ? red.urlBackend().c_str() : "no encontrado (buscando)");
  } else if (cmd == "ESTADO") {
    Serial.println(estadoJson());
  } else if (cmd == "RESET") {
    controlador.borrarErrores();
  } else if (cmd == "DISPENSAR") {
    // Mismo camino y mismas validaciones que el panel web y el botón.
    Solicitud r = (arg >= 0 && arg <= 255) ? controlador.solicitarDispensacion((uint8_t)arg, Origen::SERIE)
                                           : Solicitud::PORCIONES_INVALIDAS;
    Serial.printf("DISPENSAR %ld -> %s\n", arg, nombreSolicitud(r));
  } else if (!estadoPermiteManual()) {
    Serial.println(F("Ocupado: espere a que el estado sea ESPERANDO"));
  } else if (cmd == "SERVO") {
    if (arg < PULSO_MIN_US || arg > PULSO_MAX_US) {
      Serial.printf("Rango permitido %d..%d us\n", PULSO_MIN_US, PULSO_MAX_US);
    } else {
      bool ok = dosificador.moverA((uint16_t)arg);
      Serial.printf("Servo -> %ld us %s\n", arg, ok ? "OK" : "(caida de tension detectada)");
    }
  } else if (cmd == "CICLO") {
    // Calibración: gira sin pasar por cooldown ni límites (solo por cable USB).
    if (arg < 1 || arg > MAX_CICLOS_POR_RACION) arg = 1;
    uint32_t t0 = millis();
    ResultadoDosis r = dosificador.dosificar((uint8_t)arg);
    Serial.printf("CICLO x%ld -> %s en %lu ms (pesar el alimento entregado)\n", arg, nombreResultado(r),
                  (unsigned long)(millis() - t0));
  } else if (cmd == "CLASIFICAR") {
    if (USAR_DETECCION_AUTOMATICA) {
      RespuestaClasificacion r = red.clasificar(0);
      Serial.printf("tipo=%d clase=%d conf=%.2f motivo=%s (NO se dispensa)\n", (int)r.tipo, r.clase,
                    r.confianza, r.motivo);
    } else {
      Serial.println(F("Modo automatico desactivado (USAR_DETECCION_AUTOMATICA 0)"));
    }
  } else {
    Serial.println(F("Comando desconocido. Escriba AYUDA"));
  }
}

void leerSerie() {
  static String linea;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (linea.length()) procesarComando(linea);
      linea = "";
    } else if (linea.length() < 40) {
      linea += c;
    }
  }
}

// LED: fijo = listo y con Wi-Fi | parpadeo lento = listo SIN Wi-Fi (control local)
//      parpadeo rápido = error  | encendido durante la dosis
void actualizarLed() {
  Estado e = controlador.estado();
  if (e >= Estado::ERROR_WIFI) {
    digitalWrite(PIN_LED, (millis() / 150) % 2);
  } else if (e == Estado::ESPERANDO) {
    digitalWrite(PIN_LED, red.conectado() ? HIGH : (millis() / 1000) % 2);
  } else if (e != Estado::DOSIFICANDO) {
    digitalWrite(PIN_LED, LOW);
  }
}

// ----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println(F("\n=== Dispensador IoT - ESP32 controlador ==="));
  Serial.printf("Firmware %s | modo %s\n", VERSION_FIRMWARE, USAR_DETECCION_AUTOMATICA ? "AUTOMATICO" : "MANUAL");
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BOTON, INPUT_PULLUP);  // GPIO0 ya tiene pull-up en la placa; solo se lee tras el arranque

  energia.iniciar();
  if (USAR_DETECCION_AUTOMATICA) ultrasonico.iniciar();
  nivel.iniciar();
  if (!dosificador.iniciar()) Serial.println(F("ERROR: no se pudo configurar el PWM del servo"));
  dosificador.alEsperar(atenderRedDuranteDosis);  // el servidor HTTP responde también durante la dosis

  red.iniciar(WIFI_SSID, WIFI_CLAVE);
  ManejadoresRed manejadores;
  manejadores.estadoJson = estadoJson;
  manejadores.dispensar = dispensarRemoto;
  manejadores.borrarErrores = borrarErroresRemoto;
  manejadores.cooldownS = cooldownSegundos;
  red.iniciarServidor(manejadores, TOKEN_DISPOSITIVO);
  if (strlen(TOKEN_DISPOSITIVO) == 0) {
    Serial.println(F("AVISO: TOKEN_DISPOSITIVO vacio -> el panel web NO puede dispensar (ver secrets.h)"));
  }
  controlador.iniciar();
  Serial.println(F("Escriba AYUDA en el monitor serie para ver los comandos."));
#ifdef SIMULACION_QEMU
  // Autoprueba para el emulador (ver ESP32/test_host/qemu_autoprueba.sh)
  const char* pruebas[] = {"AYUDA", "ESTADO", "RED", "ENERGIA", "SERVO 1200", "SERVO 3000", "CICLO 1",
                           "NIVEL", "DISPENSAR 9", "DISPENSAR 1"};
  for (const char* p : pruebas) {
    Serial.printf("> %s\n", p);
    procesarComando(String(p));
  }
  // El pedido aceptado se ejecuta en el lazo: ESPERANDO -> DOSIFICANDO -> FINALIZADO -> ESPERANDO
  for (uint8_t i = 0; i < 4; i++) controlador.actualizar();
  Serial.println("> DISPENSAR 1 (repetido: debe rechazarse por cooldown)");
  procesarComando(String("DISPENSAR 1"));
  Serial.println("> ESTADO");
  procesarComando(String("ESTADO"));
  Serial.println(F("AUTOPRUEBA_FIN"));
#endif
}

void loop() {
  static uint32_t tCiclo = 0;
  leerSerie();
  boton.leer();
  red.atender();
  if (millis() - tCiclo >= INTERVALO_CICLO_MS) {
    tCiclo = millis();
    controlador.actualizar();
    actualizarLed();
    gestionarTelemetria();
  }
}
