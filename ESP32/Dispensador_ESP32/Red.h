// Red.h - Wi-Fi, cliente HTTP (PC y cámara) y servidor HTTP de estado.
#pragma once
#include <Arduino.h>
#include <WebServer.h>
#include "Controlador.h"

class Red {
 public:
  typedef String (*GeneradorEstado)();
  void iniciar(const char* ssid, const char* clave);
  bool conectado();
  void reconectar();
  bool camaraDisponible();
  bool servidorDisponible();
  RespuestaClasificacion clasificar(int distanciaCm);
  bool notificar(const char* tipo, float nivelPct);   // POST PC /alerta
  void iniciarServidorEstado(GeneradorEstado generador);
  void atender();

 private:
  bool getSimple(const String& url, uint32_t timeoutMs);
  WebServer servidor_{80};
  GeneradorEstado generador_ = nullptr;
};
