// Energia.h - Medición de tensiones con el ADC1 (divisores resistivos)
#pragma once
#include <Arduino.h>

class Energia {
 public:
  void iniciar();
  float bateria();   // V en bornes de la batería 2S
  float servo();     // V del riel de 6 V del MG995
  float panel();     // V del panel solar (indicador, no mide corriente)
  static float leer(uint8_t pin, float factor, uint8_t muestras = 16);
};
