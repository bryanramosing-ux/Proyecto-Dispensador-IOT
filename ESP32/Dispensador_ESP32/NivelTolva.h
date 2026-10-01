// NivelTolva.h - Segundo HC-SR04 (en la tapa de la tolva): nivel de alimento en %.
// La calibración (distancia con tolva vacía y llena) se guarda en la flash (NVS).
// porcentaje() devuelve el % de VOLUMEN restante (ver NivelGeometria.h).
#pragma once
#include <Arduino.h>
#include "Ultrasonico.h"

class NivelTolva {
 public:
  NivelTolva(uint8_t pinTrig, uint8_t pinEcho);
  void iniciar();
  float distanciaCm();               // < 0 si no hay eco
  float alturaPct(float distCm) const;  // 0-100 % de altura entre vacía y llena, < 0 sin lectura
  float porcentaje();                // 0-100 % del VOLUMEN, < 0 si no hay lectura válida
  bool calibrarVacia();              // guarda la distancia actual como "vacía"
  bool calibrarLlena();              // guarda la distancia actual como "llena"
  float distVacia() const { return vacia_; }
  float distLlena() const { return llena_; }

 private:
  void guardar();
  Ultrasonico sensor_;
  float vacia_, llena_;
};
