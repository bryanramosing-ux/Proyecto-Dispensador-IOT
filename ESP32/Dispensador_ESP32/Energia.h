// Energia.h - Medición OPCIONAL de tensiones con el ADC1 (divisores resistivos).
// Con el montaje USB-C no hay batería ni panel: solo queda, como opción, vigilar
// el riel de 5 V del servo (USAR_MONITOR_SERVO) para detectar atascos.
#pragma once
#include <Arduino.h>

class Energia {
 public:
  void iniciar();
  float bateria();   // V de la batería (solo si USAR_MONITOR_BATERIA; si no, 0)
  float servo();     // V del riel del MG995 (solo si USAR_MONITOR_SERVO; si no, 0)
  static float leer(uint8_t pin, float factor, uint8_t muestras = 16);
};
