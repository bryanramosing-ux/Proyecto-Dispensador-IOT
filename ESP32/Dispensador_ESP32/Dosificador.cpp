#include "Dosificador.h"
#include "config.h"

// PWM de servo: 50 Hz (periodo 20 000 us) con 16 bits de resolución.
static const uint32_t FREQ_HZ = 50;
static const uint8_t RES_BITS = 16;
static const uint32_t PERIODO_US = 1000000UL / FREQ_HZ;
#if !(defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3)
static const uint8_t CANAL_LEDC = 0;  // API del núcleo Arduino-ESP32 2.x
#endif

Dosificador::Dosificador(uint8_t pin, Energia& energia, bool vigilarRiel)
    : pin_(pin), energia_(energia), vigilarRiel_(vigilarRiel) {}

void Dosificador::escribirPulso(uint16_t us) {
  uint32_t duty = (uint32_t)us * ((1UL << RES_BITS) - 1) / PERIODO_US;
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(pin_, duty);
#else
  ledcWrite(CANAL_LEDC, duty);
#endif
  if (us > 0) pulso_ = us;
}

bool Dosificador::iniciar() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  if (!ledcAttach(pin_, FREQ_HZ, RES_BITS)) return false;
#else
  ledcSetup(CANAL_LEDC, FREQ_HZ, RES_BITS);
  ledcAttachPin(pin_, CANAL_LEDC);
#endif
  // Posición inicial desconocida: se envía CERRADO directamente (sin rampa).
  escribirPulso(PULSO_CERRADO_US);
  delay(800);
  liberar();
  return true;
}

void Dosificador::liberar() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(pin_, 0);
#else
  ledcWrite(CANAL_LEDC, 0);
#endif
  activo_ = false;
}

// Devuelve false si el riel del servo cae por debajo de VSERVO_CAIDA durante
// más de T_CAIDA_MS (indicio indirecto de bloqueo: corriente de bloqueo alta),
// o si directamente no hay tensión (VSERVO_MIN).
bool Dosificador::vigilar() {
  if (!vigilarRiel_) return true;
  float v = energia_.servo();
  if (v < 1.0f) {  // sin riel: convertidor apagado o cable suelto
    sinRiel_ = true;
    return false;
  }
  if (v < VSERVO_CAIDA) {
    if (!enCaida_) {
      enCaida_ = true;
      tInicioCaida_ = millis();
    } else if (millis() - tInicioCaida_ >= T_CAIDA_MS) {
      return false;
    }
  } else {
    enCaida_ = false;
  }
  return true;
}

bool Dosificador::esperar(uint32_t ms) {
  uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    if (!vigilar()) return false;
    delay(PASO_MS);
  }
  return true;
}

bool Dosificador::rampa(uint16_t destino) {
  if (destino < PULSO_MIN_US) destino = PULSO_MIN_US;
  if (destino > PULSO_MAX_US) destino = PULSO_MAX_US;
  enCaida_ = false;
  if (!activo_ || pulso_ == 0) {  // venía liberado: reanudar en la última posición
    escribirPulso(pulso_ ? pulso_ : PULSO_CERRADO_US);
    activo_ = true;
  }
  while (pulso_ != destino) {
    int32_t delta = (int32_t)destino - (int32_t)pulso_;
    int32_t paso = delta;
    if (paso > PASO_US) paso = PASO_US;
    if (paso < -PASO_US) paso = -PASO_US;
    escribirPulso(pulso_ + paso);
    delay(PASO_MS);
    if (!vigilar()) return false;
  }
  return true;
}

bool Dosificador::agitar(uint16_t centro) {
  for (uint8_t i = 0; i < AGITACIONES; i++) {
    if (!rampa(centro + AGITACION_US) || !rampa(centro - AGITACION_US)) return false;
  }
  return rampa(centro);
}

// Si el disco se traba, retrocede a la posición anterior (suelta el grano
// pellizcado) y lo vuelve a intentar REINTENTOS_ATASCO veces.
bool Dosificador::moverConReintentos(uint16_t destino, uint16_t anterior) {
  for (uint8_t intento = 0; intento <= REINTENTOS_ATASCO; intento++) {
    if (rampa(destino)) return true;
    if (sinRiel_) return false;
    rampa(anterior);
    delay(300);
  }
  return false;
}

ResultadoDosis Dosificador::dosificar(uint8_t ciclos) {
  atasco_ = false;
  sinRiel_ = false;
  if (vigilarRiel_ && energia_.servo() < VSERVO_MIN) {
    return ResultadoDosis::SIN_ALIMENTACION_SERVO;
  }
  ResultadoDosis resultado = ResultadoDosis::OK;
  for (uint8_t c = 0; c < ciclos && resultado == ResultadoDosis::OK; c++) {
    // 1) Llenar: bolsillo bajo la salida de la tolva
    if (!moverConReintentos(PULSO_LLENADO_US, PULSO_CERRADO_US) || !agitar(PULSO_LLENADO_US) ||
        !esperar(T_LLENADO_MS)) {
      resultado = ResultadoDosis::ATASCO;
      break;
    }
    // 2) Descargar: bolsillo sobre el conducto (el alimento cae por gravedad)
    if (!moverConReintentos(PULSO_DESCARGA_US, PULSO_LLENADO_US) || !esperar(T_DESCARGA_MS) ||
        !agitar(PULSO_DESCARGA_US)) {
      resultado = ResultadoDosis::ATASCO;
      break;
    }
  }
  // 3) Volver a CERRADO (ninguna abertura conectada) y dejar de hacer fuerza
  if (resultado == ResultadoDosis::OK && !moverConReintentos(PULSO_CERRADO_US, PULSO_DESCARGA_US)) {
    resultado = ResultadoDosis::ATASCO;
  }
  if (sinRiel_) resultado = ResultadoDosis::SIN_ALIMENTACION_SERVO;
  atasco_ = (resultado == ResultadoDosis::ATASCO);
  liberar();  // un servo trabado y energizado se calienta: siempre se libera
  return resultado;
}

bool Dosificador::moverA(uint16_t pulsoUs) {
  bool ok = rampa(pulsoUs);
  delay(300);
  liberar();
  return ok;
}
