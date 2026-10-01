#include "Ultrasonico.h"

// Hoja de datos HC-SR04: pulso de disparo >= 10 us, ciclo de medida >= 60 ms,
// distancia [cm] = ancho del pulso ECHO [us] / 58.
static const uint32_t CICLO_MIN_MS = 60;

Ultrasonico::Ultrasonico(uint8_t pinTrig, uint8_t pinEcho, uint8_t muestras, uint32_t timeoutUs)
    : trig_(pinTrig), echo_(pinEcho), muestras_(muestras < 1 ? 1 : (muestras > 9 ? 9 : muestras)),
      timeoutUs_(timeoutUs) {}

void Ultrasonico::iniciar() {
  pinMode(trig_, OUTPUT);
  digitalWrite(trig_, LOW);
  pinMode(echo_, INPUT);  // GPIO34: solo entrada, sin pull-up interno (el divisor fija el nivel)
}

float Ultrasonico::disparoCm() {
  uint32_t trans = millis() - tUltimoDisparo_;
  if (trans < CICLO_MIN_MS) delay(CICLO_MIN_MS - trans);
  digitalWrite(trig_, LOW);
  delayMicroseconds(2);
  digitalWrite(trig_, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig_, LOW);
  unsigned long us = pulseIn(echo_, HIGH, timeoutUs_);
  tUltimoDisparo_ = millis();
  if (us == 0) return -1.0f;
  return us / 58.0f;
}

float Ultrasonico::medirCm() {
  float v[9];
  uint8_t n = 0;
  for (uint8_t i = 0; i < muestras_; i++) {
    float d = disparoCm();
    if (d > 0) v[n++] = d;
  }
  if (n == 0) return -1.0f;
  // Ordenación por inserción (n <= 9) y mediana: descarta ecos espurios
  for (uint8_t i = 1; i < n; i++) {
    float x = v[i];
    int8_t j = i - 1;
    while (j >= 0 && v[j] > x) { v[j + 1] = v[j]; j--; }
    v[j + 1] = x;
  }
  return v[n / 2];
}
