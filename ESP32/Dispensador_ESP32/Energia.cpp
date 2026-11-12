#include "Energia.h"
#include "config.h"

void Energia::iniciar() {
#ifdef SIMULACION_QEMU
  return;
#endif
  // Atenuación 11 dB: rango útil aprox. 0,15-2,45 V con buena linealidad.
  // Divisor 100k/33k: 5,0 V -> 1,24 V en el pin.
#if USAR_MONITOR_BATERIA
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);
#endif
#if USAR_MONITOR_SERVO
  analogSetPinAttenuation(PIN_VSERVO, ADC_11db);
#endif
}

#ifdef SIMULACION_QEMU
// El emulador QEMU no tiene ADC: se devuelven tensiones nominales (solo pruebas).
float Energia::leer(uint8_t pin, float factor, uint8_t muestras) {
  (void)factor;
  (void)muestras;
  return pin == PIN_VBAT ? 7.6f : 5.0f;
}
#else
float Energia::leer(uint8_t pin, float factor, uint8_t muestras) {
  uint32_t suma = 0;
  for (uint8_t i = 0; i < muestras; i++) suma += analogReadMilliVolts(pin);  // usa calibración eFuse
  return (suma / (float)muestras) / 1000.0f * factor;
}
#endif

// Un pin sin divisor montado queda flotante: no se lee si el monitor está apagado.
float Energia::bateria() { return USAR_MONITOR_BATERIA ? leer(PIN_VBAT, FACTOR_VBAT) : 0.0f; }
float Energia::servo() { return USAR_MONITOR_SERVO ? leer(PIN_VSERVO, FACTOR_VSERVO, 4) : 0.0f; }
