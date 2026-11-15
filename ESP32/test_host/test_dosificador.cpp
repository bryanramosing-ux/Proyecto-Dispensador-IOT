// Se ejecuta el Dosificador real, con reloj, PWM y ADC inyectados.
#include "../Dispensador_ESP32/Dosificador.h"
#include <cassert>
#include <cstdio>
static unsigned long tiempo = 0, sinRielDesde = ~0UL;
static bool pwmOk = true;
static unsigned escrituras = 0;
static uint32_t ultimoDuty = 999;
static float riel = 6.0f, rielEnCaida = 0;
unsigned long millis() { return tiempo; }
void delay(uint32_t ms) { tiempo += ms; }
bool ledcAttach(uint8_t, uint32_t, uint8_t) { return pwmOk; }
uint32_t ledcSetup(uint8_t, uint32_t freq, uint8_t) { return pwmOk ? freq : 0; }
void ledcAttachPin(uint8_t, uint8_t) {}
void ledcWrite(uint8_t, uint32_t duty) { escrituras++; ultimoDuty = duty; }
float Energia::servo() { return tiempo >= sinRielDesde ? rielEnCaida : riel; }
int main() {
  Energia e;
  pwmOk = false;
  Dosificador fallo(25, e, true);
  assert(!fallo.iniciar() && !fallo.preparado());
  assert(fallo.dosificar(1) != ResultadoDosis::OK && !fallo.moverA(1500) && escrituras == 0);
  pwmOk = true;
  Dosificador d(25, e, true);
  assert(d.iniciar() && d.preparado());
  assert(d.dosificar(1) == ResultadoDosis::OK && ultimoDuty == 0);
  unsigned antes = escrituras;
  assert(d.dosificar(0) != ResultadoDosis::OK && d.dosificar(255) != ResultadoDosis::OK);
  assert(escrituras == antes);
  riel = 0;
  assert(d.dosificar(1) == ResultadoDosis::SIN_ALIMENTACION_SERVO && escrituras == antes);
  riel = 6; sinRielDesde = tiempo + 1000;
  assert(d.dosificar(3) == ResultadoDosis::SIN_ALIMENTACION_SERVO && ultimoDuty == 0);
  riel = 6; rielEnCaida = 3; sinRielDesde = tiempo + 300;
  assert(d.dosificar(1) == ResultadoDosis::ATASCO && ultimoDuty == 0);
  printf("Dosificador API %d.x: PWM, dosis valida, limites, perdida de riel y atasco OK\n", ESP_ARDUINO_VERSION_MAJOR);
}
