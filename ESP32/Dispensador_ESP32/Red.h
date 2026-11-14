// Red.h - Wi-Fi, descubrimiento del backend, telemetría (cliente HTTP) y servidor
// HTTP local del ESP32 (estado + comandos autorizados).
#pragma once
#include <Arduino.h>
#include <WebServer.h>
#include <WiFiUdp.h>
#include "Controlador.h"

// Funciones que el servidor HTTP llama para leer el estado o ejecutar un comando.
struct ManejadoresRed {
  String (*estadoJson)() = nullptr;
  Solicitud (*dispensar)(uint8_t porciones) = nullptr;
  bool (*borrarErrores)() = nullptr;
  uint32_t (*cooldownS)() = nullptr;
};

class Red {
 public:
  void iniciar(const char* ssid, const char* clave);
  bool conectado();
  void reconectar();
  String ip();
  int rssi();

  // --- Backend (dashboard) ---
  bool backendConocido() const { return urlBackend_.length() > 0; }
  const String& urlBackend() const { return urlBackend_; }
  bool enviarTelemetria(const String& json);          // POST /api/device/telemetry
  bool notificar(const char* tipo, float nivelPct);   // POST /api/device/alert

  // --- Modo automático opcional (servidor de visión + cámara) ---
  bool camaraDisponible();
  bool servidorDisponible();
  RespuestaClasificacion clasificar(int distanciaCm);

  // --- Servidor HTTP local ---
  //   GET  /status          estado en JSON (sin token: solo lectura)
  //   POST /dispensar       porciones=N&token=...   (cuerpo de formulario)
  //   POST /reset-errores   token=...
  void iniciarServidor(const ManejadoresRed& manejadores, const char* token);
  void atender();   // llamar en cada vuelta del loop: HTTP + descubrimiento

 private:
  bool getSimple(const String& url, uint32_t timeoutMs);
  bool postBackend(const char* ruta, const String& cuerpo);
  void descubrir();
  bool tokenValido();
  void responder(int codigo, const String& json);
  void manejarDispensar();
  void manejarReset();

  WebServer servidor_{80};
  WiFiUDP udp_;
  bool udpAbierto_ = false;
  bool mdnsIniciado_ = false;
  ManejadoresRed m_;
  const char* token_ = "";
  String urlBackend_;
  uint8_t fallosBackend_ = 0;
  uint32_t tDescubrir_ = 0;
  uint8_t intentosToken_ = 0;
  uint32_t tBloqueoToken_ = 0;
};
