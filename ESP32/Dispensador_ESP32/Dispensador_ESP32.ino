// =============================================================================
//  DISPENSADOR INTELIGENTE DE ALIMENTO PARA MASCOTAS
//  IoT + Visión artificial + Energía solar
//  Firmware del ESP32 DevKit V1 (controlador y actuador)
// =============================================================================
//  Responsabilidades del ESP32:
//    * Leer el HC-SR04 y confirmar la presencia de una mascota.
//    * Pedir la clasificación al PC (que a su vez pide la foto a la ESP32-CAM).
//    * DECIDIR si corresponde dispensar (clase válida, cooldown, límite diario,
//      batería y riel del servo correctos, mascota todavía presente).
//    * Generar la señal PWM del MG995 (solo señal: el servo se alimenta aparte).
//    * Gestionar errores con una máquina de estados.
//
//  Entorno: Arduino IDE (núcleo esp32 2.x o 3.x) o PlatformIO.
//  Biblioteca externa: ArduinoJson 7 (Benoît Blanchon).
// =============================================================================
#include <Arduino.h>
#include <WiFi.h>

#include "Controlador.h"
#include "Dosificador.h"
#include "Energia.h"
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
Ultrasonico ultrasonico(PIN_TRIG, PIN_ECHO, N_MUESTRAS_DIST, TIMEOUT_ECO_US);
Dosificador dosificador(PIN_SERVO, energia, USAR_MONITOR_SERVO);
Red red;

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
  ResultadoDosis dosificar(uint8_t ciclos) override {
    digitalWrite(PIN_LED, HIGH);
    ResultadoDosis r = dosificador.dosificar(ciclos);
    digitalWrite(PIN_LED, LOW);
    return r;
  }
  bool botonResetPulsado() override {
    if (digitalRead(PIN_BOTON) == HIGH) {
      tBoton_ = 0;
      return false;
    }
    if (tBoton_ == 0) tBoton_ = millis();
    return millis() - tBoton_ >= T_BOTON_RESET_MS;
  }
  void reiniciar() override {
    delay(200);
    ESP.restart();
  }
  void log(const char* m) override {
    Serial.printf("[%10lu] %s\n", (unsigned long)millis(), m);
  }

 private:
  uint32_t tBoton_ = 0;
};

HardwareReal hardware;

Parametros crearParametros() {
  Parametros p;
  p.distMinCm = DIST_MIN_CM;
  p.distDeteccionCm = DIST_DETECCION_CM;
  p.distLibreCm = DIST_LIBRE_CM;
  p.lecturasConfirmacion = LECTURAS_CONFIRMACION;
  p.zonaLibreMs = ZONA_LIBRE_MS;
  p.maxIntentosClasificacion = MAX_INTENTOS_CLASIFICACION;
  p.reintentoClasificacionMs = REINTENTO_CLASIFICACION_MS;
  p.ciclos[0] = 0;               p.habilitada[0] = false;
  p.ciclos[CLASE_PERRO] = CICLOS_PERRO;  p.habilitada[CLASE_PERRO] = HABILITAR_PERRO;
  p.ciclos[CLASE_GATO] = CICLOS_GATO;    p.habilitada[CLASE_GATO] = HABILITAR_GATO;
  p.cooldownClaseMs[0] = 0;
  p.cooldownClaseMs[CLASE_PERRO] = COOLDOWN_PERRO_MS;
  p.cooldownClaseMs[CLASE_GATO] = COOLDOWN_GATO_MS;
  p.maxRacionesDia[0] = 0;
  p.maxRacionesDia[CLASE_PERRO] = MAX_RACIONES_DIA_PERRO;
  p.maxRacionesDia[CLASE_GATO] = MAX_RACIONES_DIA_GATO;
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
  return p;
}

Controlador controlador(hardware, crearParametros());

// ----------------------------------------------------------------------------
// GET /status  (JSON para pruebas y monitoreo)
// ----------------------------------------------------------------------------
String estadoJson() {
  char buf[512];
  snprintf(buf, sizeof(buf),
           "{\"estado\":\"%s\",\"distancia_cm\":%.1f,\"ultima_clase\":%d,"
           "\"ultima_confianza\":%.2f,\"ultimo_motivo\":\"%s\","
           "\"raciones_perro\":%lu,\"raciones_gato\":%lu,"
           "\"raciones_24h_perro\":%u,\"raciones_24h_gato\":%u,"
           "\"cooldown_s\":%lu,\"v_bateria\":%.2f,\"v_servo\":%.2f,\"v_panel\":%.2f,"
           "\"rssi\":%d,\"uptime_s\":%lu,\"heap\":%u}",
           nombreEstado(controlador.estado()), controlador.ultimaDistancia(),
           controlador.ultimaClase(), controlador.ultimaConfianza(), controlador.ultimoMotivo(),
           (unsigned long)controlador.racionesTotales(CLASE_PERRO),
           (unsigned long)controlador.racionesTotales(CLASE_GATO),
           controlador.racionesUltimas24h(CLASE_PERRO), controlador.racionesUltimas24h(CLASE_GATO),
           (unsigned long)(controlador.cooldownRestanteMs() / 1000), energia.bateria(),
           energia.servo(), energia.panel(), WiFi.RSSI(), (unsigned long)(millis() / 1000),
           (unsigned)ESP.getFreeHeap());
  return String(buf);
}

// ----------------------------------------------------------------------------
// Comandos por monitor serie (115200 baudios) para pruebas y CALIBRACIÓN.
// Solo por cable USB (acceso físico): no existe un endpoint remoto de "dar comida".
// ----------------------------------------------------------------------------
bool estadoPermiteManual() {
  Estado e = controlador.estado();
  return e == Estado::ESPERANDO || e >= Estado::ERROR_WIFI;
}

void procesarComando(String linea) {
  linea.trim();
  String cmd = linea;
  long arg = 0;
  int esp = linea.indexOf(' ');
  if (esp > 0) {
    cmd = linea.substring(0, esp);
    arg = linea.substring(esp + 1).toInt();
  }
  cmd.toUpperCase();

  if (cmd == "AYUDA" || cmd == "?") {
    Serial.println(F("DIST | SERVO <us> | CICLO <n> | CLASIFICAR | ENERGIA | ESTADO | RESET"));
  } else if (cmd == "DIST") {
    Serial.printf("Distancia: %.1f cm\n", ultrasonico.medirCm());
  } else if (cmd == "ENERGIA") {
    Serial.printf("Bateria %.2f V | Servo %.2f V | Panel %.2f V\n", energia.bateria(),
                  energia.servo(), energia.panel());
  } else if (cmd == "ESTADO") {
    Serial.println(estadoJson());
  } else if (cmd == "RESET") {
    controlador.borrarErrores();
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
    if (arg < 1 || arg > MAX_CICLOS_POR_RACION) arg = 1;
    uint32_t t0 = millis();
    ResultadoDosis r = dosificador.dosificar((uint8_t)arg);
    Serial.printf("CICLO x%ld -> %s en %lu ms (pesar el alimento entregado)\n", arg,
                  r == ResultadoDosis::OK ? "OK" : (r == ResultadoDosis::ATASCO ? "ATASCO" : "SIN RIEL"),
                  (unsigned long)(millis() - t0));
  } else if (cmd == "CLASIFICAR") {
    RespuestaClasificacion r = red.clasificar(0);
    Serial.printf("tipo=%d clase=%d conf=%.2f motivo=%s (NO se dispensa)\n", (int)r.tipo, r.clase,
                  r.confianza, r.motivo);
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

// LED: fijo = esperando, parpadeo rápido = error, apagado = procesando
void actualizarLed() {
  Estado e = controlador.estado();
  if (e >= Estado::ERROR_WIFI) {
    digitalWrite(PIN_LED, (millis() / 150) % 2);
  } else if (e == Estado::ESPERANDO) {
    digitalWrite(PIN_LED, HIGH);
  } else if (e != Estado::DOSIFICANDO) {
    digitalWrite(PIN_LED, LOW);
  }
}

// ----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println(F("\n=== Dispensador IoT - ESP32 controlador ==="));
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BOTON, INPUT_PULLUP);  // GPIO0 ya tiene pull-up en la placa; solo se lee tras el arranque

  energia.iniciar();
  ultrasonico.iniciar();
  if (!dosificador.iniciar()) Serial.println(F("ERROR: no se pudo configurar el PWM del servo"));

  red.iniciar(WIFI_SSID, WIFI_CLAVE);
  red.iniciarServidorEstado(estadoJson);
  controlador.iniciar();
  Serial.println(F("Escriba AYUDA en el monitor serie para ver los comandos."));
}

void loop() {
  static uint32_t tCiclo = 0;
  leerSerie();
  red.atender();
  if (millis() - tCiclo >= INTERVALO_CICLO_MS) {
    tCiclo = millis();
    controlador.actualizar();
    actualizarLed();
  }
}
