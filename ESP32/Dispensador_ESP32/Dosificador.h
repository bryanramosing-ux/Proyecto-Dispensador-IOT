// Dosificador.h - MG995 (180°) moviendo un disco volumétrico de un bolsillo.
// El ESP32 SOLO entrega la señal PWM; el servo se alimenta del riel de 5 V (USB-C),
// por un cable propio desde el punto de reparto: nunca desde el ESP32.
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
  bool enMovimiento() const { return activo_; }
  // Tarea que se ejecuta durante las esperas de la dosis (p. ej. atender el servidor
  // HTTP), para que el equipo siga respondiendo mientras gira el servo.
  typedef void (*TareaFondo)();
  void alEsperar(TareaFondo tarea) { tareaFondo_ = tarea; }
  bool atascoDetectado() const { return atasco_; }

 private:
  void escribirPulso(uint16_t us);
  bool rampa(uint16_t destino);         // false si se detecta caída sostenida del riel
  bool esperar(uint32_t ms);
  void pausa(uint32_t ms);              // delay() que no deja de atender la tarea de fondo
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
  TareaFondo tareaFondo_ = nullptr;
};
