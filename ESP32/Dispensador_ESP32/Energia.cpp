#include "Energia.h"
#include "config.h"

void Energia::iniciar() {
  // Atenuación 11 dB: rango útil aprox. 0,15-2,45 V con buena linealidad.
  // Los divisores están dimensionados para no superar ~2,1 V en el pin.
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);
  analogSetPinAttenuation(PIN_VSERVO, ADC_11db);
  analogSetPinAttenuation(PIN_VPANEL, ADC_11db);
}

float Energia::leer(uint8_t pin, float factor, uint8_t muestras) {
  uint32_t suma = 0;
  for (uint8_t i = 0; i < muestras; i++) suma += analogReadMilliVolts(pin);  // usa calibración eFuse
  return (suma / (float)muestras) / 1000.0f * factor;
}

float Energia::bateria() { return leer(PIN_VBAT, FACTOR_VBAT); }
float Energia::servo() { return leer(PIN_VSERVO, FACTOR_VSERVO, 4); }
float Energia::panel() { return leer(PIN_VPANEL, FACTOR_VPANEL); }
