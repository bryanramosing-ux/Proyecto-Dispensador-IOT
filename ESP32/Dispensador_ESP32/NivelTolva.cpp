#include "NivelTolva.h"

#include <Preferences.h>

#include "NivelGeometria.h"
#include "config.h"

NivelTolva::NivelTolva(uint8_t pinTrig, uint8_t pinEcho)
    : sensor_(pinTrig, pinEcho, N_MUESTRAS_NIVEL, TIMEOUT_ECO_US),
      vacia_(DIST_TOLVA_VACIA_CM), llena_(DIST_TOLVA_LLENA_CM) {}

void NivelTolva::iniciar() {
  sensor_.iniciar();
  Preferences pref;
  if (pref.begin("tolva", true)) {        // solo lectura
    vacia_ = pref.getFloat("vacia", DIST_TOLVA_VACIA_CM);
    llena_ = pref.getFloat("llena", DIST_TOLVA_LLENA_CM);
    pref.end();
  }
}

float NivelTolva::distanciaCm() { return sensor_.medirCm(); }

float NivelTolva::alturaPct(float d) const {
  if (d < 0 || vacia_ - llena_ < 2.0f) return -1.0f;   // sin eco o calibración inválida
  float pct = (vacia_ - d) / (vacia_ - llena_) * 100.0f;
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

float NivelTolva::porcentaje() {
  float h = alturaPct(distanciaCm());
  return h < 0 ? -1.0f : alturaAVolumenPct(h);
}

void NivelTolva::guardar() {
  Preferences pref;
  if (pref.begin("tolva", false)) {
    pref.putFloat("vacia", vacia_);
    pref.putFloat("llena", llena_);
    pref.end();
  }
}

bool NivelTolva::calibrarVacia() {
  float d = distanciaCm();
  if (d < 0) return false;
  vacia_ = d;
  guardar();
  return true;
}

bool NivelTolva::calibrarLlena() {
  float d = distanciaCm();
  if (d < 0) return false;
  llena_ = d;
  guardar();
  return true;
}
