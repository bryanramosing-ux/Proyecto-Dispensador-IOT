#include "Energia.h"
#include "config.h"

void Energia::iniciar() {
#ifdef SIMULACION_QEMU
  return;
#endif
  // Atenuación 11 dB: rango útil aprox. 0,15-2,45 V con buena linealidad.
  // Los divisores están dimensionados para no superar ~2,1 V en el pin.
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);
  analogSetPinAttenuation(PIN_VSERVO, ADC_11db);
  analogSetPinAttenuation(PIN_VPANEL, ADC_11db);
}

#ifdef SIMULACION_QEMU
// El emulador QEMU no tiene ADC: se devuelven tensiones nominales (solo pruebas).
float Energia::leer(uint8_t pin, float factor, uint8_t muestras) {
  (void)factor;
  (void)muestras;
  return pin == PIN_VBAT ? 7.6f : (pin == PIN_VSERVO ? 6.0f : 2.0f);
}
#else
float Energia::leer(uint8_t pin, float factor, uint8_t muestras) {
  uint32_t suma = 0;
  for (uint8_t i = 0; i < muestras; i++) suma += analogReadMilliVolts(pin);  // usa calibración eFuse
  return (suma / (float)muestras) / 1000.0f * factor;
}
#endif

float Energia::bateria() { return leer(PIN_VBAT, FACTOR_VBAT); }
float Energia::servo() { return leer(PIN_VSERVO, FACTOR_VSERVO, 4); }
float Energia::panel() { return leer(PIN_VPANEL, FACTOR_VPANEL); }
