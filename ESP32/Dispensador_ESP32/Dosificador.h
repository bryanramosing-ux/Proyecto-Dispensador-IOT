// Dosificador.h - MG995 (180°) moviendo un disco volumétrico de un bolsillo.
// El ESP32 SOLO entrega la señal PWM; el servo se alimenta del convertidor de 6 V.
#pragma once
#include <Arduino.h>
#include "Controlador.h"
#include "Energia.h"

class Dosificador {
 public:
  Dosificador(uint8_t pin, Energia& energia, bool vigilarRiel);
  bool iniciar();                       // configura LEDC y lleva el disco a CERRADO
  ResultadoDosis dosificar(uint8_t ciclos);
  // Para calibración: mueve a un pulso (limitado a PULSO_MIN_US..PULSO_MAX_US)
  bool moverA(uint16_t pulsoUs);
  void liberar();                       // deja de enviar pulsos: el servo no hace fuerza
  uint16_t pulsoActual() const { return pulso_; }
  bool atascoDetectado() const { return atasco_; }

 private:
  void escribirPulso(uint16_t us);
  bool rampa(uint16_t destino);         // false si se detecta caída sostenida del riel
  bool esperar(uint32_t ms);
  bool agitar(uint16_t centro);
  bool moverConReintentos(uint16_t destino, uint16_t anterior);
  bool vigilar();

  uint8_t pin_;
  Energia& energia_;
  bool vigilarRiel_;
  uint16_t pulso_ = 0;
  bool activo_ = false;
  bool atasco_ = false;
  bool sinRiel_ = false;
  uint32_t tInicioCaida_ = 0;
  bool enCaida_ = false;
};
