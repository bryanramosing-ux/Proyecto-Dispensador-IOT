// Ultrasonico.h - HC-SR04 (VCC 5 V; ECHO adaptado a 3,3 V con divisor 1k/2k)
#pragma once
#include <Arduino.h>

class Ultrasonico {
 public:
  Ultrasonico(uint8_t pinTrig, uint8_t pinEcho, uint8_t muestras, uint32_t timeoutUs);
  void iniciar();
  // Mediana de N disparos en cm; -1 si no hay eco válido (nada delante / fuera de rango)
  float medirCm();

 private:
  float disparoCm();
  uint8_t trig_, echo_, muestras_;
  uint32_t timeoutUs_;
  uint32_t tUltimoDisparo_ = 0;
};
