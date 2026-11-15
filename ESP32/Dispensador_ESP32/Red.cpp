#include "Red.h"

#include <ArduinoJson.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets_ejemplo.h"
#endif

static const char MSG_PREGUNTA[] = "DISPENSADOR?";    // el ESP32 pregunta por broadcast UDP
static const char MSG_RESPUESTA[] = "DISPENSADOR!";   // el backend responde "DISPENSADOR!<puerto>"

// SIMULACION_QEMU: solo para arrancar el firmware en el emulador QEMU de Espressif,
// que no emula la radio Wi-Fi. Nunca definirlo al compilar para la placa real.
#ifdef SIMULACION_QEMU
void Red::iniciar(const char*, const char*) { Serial.println("SIMULACION_QEMU: Wi-Fi desactivado"); }
bool Red::conectado() { return false; }
void Red::reconectar() { Serial.println("Wi-Fi: reintentando conexion... (simulado)"); }
String Red::ip() { return String("0.0.0.0"); }
int Red::rssi() { return 0; }
#else
void Red::iniciar(const char* ssid, const char* clave) {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  IPAddress ip, gw, mascara;
  if (strlen(IP_ESP32) > 0 && ip.fromString(IP_ESP32) && gw.fromString(IP_GATEWAY) &&
      mascara.fromString(IP_MASCARA)) {
    WiFi.config(ip, gw, mascara, gw);  // IP fija opcional (por defecto DHCP)
  }
  if (strlen(URL_BACKEND) > 0) urlBackend_ = URL_BACKEND;  // dirección manual: no se descubre
  WiFi.begin(ssid, clave);
  // Espera acotada: si no hay Wi-Fi, el equipo arranca igual y sigue con el control local.
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(250);
  if (conectado()) {
    Serial.printf("Wi-Fi OK  IP=%s  RSSI=%d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    Serial.println("Wi-Fi: sin conexion (se reintentara; el control local sigue activo)");
  }
}

bool Red::conectado() { return WiFi.status() == WL_CONNECTED; }

void Red::reconectar() {
  // Sin WiFi.disconnect(): cortaría un intento de asociación que todavía está en curso.
  Serial.println("Wi-Fi: reintentando conexion...");
  WiFi.reconnect();
}

String Red::ip() { return conectado() ? WiFi.localIP().toString() : String("0.0.0.0"); }
int Red::rssi() { return conectado() ? WiFi.RSSI() : 0; }
#endif

// ----------------------------------------------------------------------------
// Descubrimiento del backend: el ESP32 pregunta por broadcast UDP y el PC que
// ejecuta el dashboard contesta con su puerto HTTP. Así no hay que escribir la
// IP del PC en el firmware. Si URL_BACKEND está definida, no se usa.
// ----------------------------------------------------------------------------
void Red::descubrir() {
#ifndef SIMULACION_QEMU
  if (!conectado()) {
    if (udpAbierto_) {
      udp_.stop();
      udpAbierto_ = false;
    }
    return;
  }
  if (!mdnsIniciado_) {
    mdnsIniciado_ = MDNS.begin(NOMBRE_MDNS);  // http://dispensador.local/status
    if (mdnsIniciado_) MDNS.addService("http", "tcp", 80);
  }
  if (strlen(URL_BACKEND) > 0) return;
  // Se busca mientras no se conozca el backend o si dejó de responder (pudo cambiar de IP).
  if (backendConocido() && fallosBackend_ < 3) return;
  if (!udpAbierto_) udpAbierto_ = udp_.begin(PUERTO_DESCUBRIMIENTO) == 1;
  if (!udpAbierto_) return;

  int n = udp_.parsePacket();
  if (n > 0) {
    char buf[32];
    int len = udp_.read((uint8_t*)buf, sizeof(buf) - 1);
    if (len < 0) len = 0;
    buf[len] = '\0';
    const size_t pref = sizeof(MSG_RESPUESTA) - 1;
    if (strncmp(buf, MSG_RESPUESTA, pref) == 0) {
      long puerto = atol(buf + pref);
      if (puerto > 0 && puerto < 65536) {
        urlBackend_ = String("http://") + udp_.remoteIP().toString() + String(":") + String(puerto);
        fallosBackend_ = 0;
        Serial.printf("Backend encontrado en %s\n", urlBackend_.c_str());
      }
    }
  }
  if (millis() - tDescubrir_ >= DESCUBRIMIENTO_MS) {
    tDescubrir_ = millis();
    udp_.beginPacket(IPAddress(255, 255, 255, 255), PUERTO_DESCUBRIMIENTO);
    udp_.write((const uint8_t*)MSG_PREGUNTA, sizeof(MSG_PREGUNTA) - 1);
    udp_.endPacket();
  }
#endif
}

// ----------------------------------------------------------------------------
// Cliente HTTP hacia el backend. Tiempos de espera cortos: si el PC está apagado
// el lazo de control se detiene como mucho TIMEOUT_BACKEND_CONEXION_MS por intento,
// y los intentos se espacian (ver gestionarTelemetria() en el .ino).
// ----------------------------------------------------------------------------
bool Red::postBackend(const char* ruta, const String& cuerpo) {
  if (!conectado() || !backendConocido()) return false;
  HTTPClient http;
  http.setConnectTimeout(TIMEOUT_BACKEND_CONEXION_MS);
  http.setTimeout(TIMEOUT_BACKEND_MS);
  bool ok = false;
  if (http.begin(urlBackend_ + String(ruta))) {
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", token_);
    ok = http.POST(cuerpo) == 200;
    http.end();
  }
  if (ok) {
    fallosBackend_ = 0;
  } else if (fallosBackend_ < 250) {
    fallosBackend_++;
  }
  return ok;
}

bool Red::enviarTelemetria(const String& json) { return postBackend("/api/device/telemetry", json); }

// POST /api/device/alert  {"dispositivo":"ESP32","tipo":"COMIDA_BAJA","nivel":18}
bool Red::notificar(const char* tipo, float nivelPct) {
  char cuerpo[112];
  snprintf(cuerpo, sizeof(cuerpo), "{\"dispositivo\":\"ESP32\",\"tipo\":\"%s\",\"nivel\":%.0f}", tipo, nivelPct);
  return postBackend("/api/device/alert", String(cuerpo));
}

// ----------------------------------------------------------------------------
// Modo automático opcional: servidor de visión (OpenCV) y cámara
// ----------------------------------------------------------------------------
bool Red::getSimple(const String& url, uint32_t timeoutMs) {
  if (!conectado()) return false;
  HTTPClient http;
  http.setConnectTimeout(TIMEOUT_CONEXION_MS);
  http.setTimeout(timeoutMs);
  if (!http.begin(url)) return false;
  int codigo = http.GET();
  http.end();
  return codigo == 200;
}

bool Red::camaraDisponible() { return getSimple(String(URL_CAMARA) + "/status", TIMEOUT_ESTADO_MS); }

bool Red::servidorDisponible() { return getSimple(String(URL_VISION) + "/status", TIMEOUT_ESTADO_MS); }

// GET http://PC:8000/classify?dist=NN  ->  {"clase":1,"confianza":0.93,"motivo":"OK",...}
RespuestaClasificacion Red::clasificar(int distanciaCm) {
  RespuestaClasificacion r;
  if (!conectado()) {
    strncpy(r.motivo, "SIN_WIFI", sizeof(r.motivo) - 1);
    return r;  // tipo = ERROR_SERVIDOR
  }
  HTTPClient http;
  http.setConnectTimeout(TIMEOUT_CONEXION_MS);
  http.setTimeout(TIMEOUT_CLASIFICAR_MS);
  String url = String(URL_VISION) + "/classify?dist=" + String(distanciaCm);
  if (!http.begin(url)) {
    strncpy(r.motivo, "URL_INVALIDA", sizeof(r.motivo) - 1);
    return r;
  }
  int codigo = http.GET();
  if (codigo <= 0) {  // timeout, conexión rechazada, etc.
    snprintf(r.motivo, sizeof(r.motivo), "HTTP_ERR_%d", codigo);
    http.end();
    return r;
  }
  String cuerpo = http.getString();
  http.end();

  JsonDocument doc;
  if (deserializeJson(doc, cuerpo)) {
    strncpy(r.motivo, "JSON_INVALIDO", sizeof(r.motivo) - 1);
    return r;
  }
  const char* motivo = doc["motivo"] | "";
  strncpy(r.motivo, motivo, sizeof(r.motivo) - 1);
  int clase = doc["clase"] | -1;

  if (codigo == 502 && strcmp(motivo, "CAMARA_NO_RESPONDE") == 0) {
    r.tipo = TipoRespuesta::ERROR_CAMARA;
  } else if (codigo == 200 && clase >= CLASE_INDETERMINADA && clase <= CLASE_GATO) {
    r.tipo = TipoRespuesta::OK;
    r.clase = clase;
    r.confianza = doc["confianza"] | 0.0f;
  }  // cualquier otro caso queda como ERROR_SERVIDOR
  return r;
}

// ----------------------------------------------------------------------------
// Servidor HTTP local
// ----------------------------------------------------------------------------
void Red::responder(int codigo, const String& json) {
  servidor_.sendHeader("Cache-Control", "no-store");
  servidor_.send(codigo, "application/json", json);
}

// Los comandos que mueven el servo exigen el token compartido con el backend.
// Sin token configurado NO hay control remoto; tras varios intentos fallidos se
// bloquean los comandos durante BLOQUEO_TOKEN_MS (frena la fuerza bruta).
bool Red::tokenValido() {
  if (strlen(token_) == 0) {
    responder(403, "{\"ok\":false,\"resultado\":\"SIN_TOKEN\",\"error\":\"control remoto deshabilitado: defina TOKEN_DISPOSITIVO en secrets.h\"}");
    return false;
  }
  if (intentosToken_ >= MAX_INTENTOS_TOKEN) {
    if (millis() - tBloqueoToken_ < BLOQUEO_TOKEN_MS) {
      responder(429, "{\"ok\":false,\"resultado\":\"BLOQUEADO\",\"error\":\"demasiados intentos con token incorrecto\"}");
      return false;
    }
    intentosToken_ = 0;
  }
  if (!servidor_.hasArg("token") || !(servidor_.arg("token") == token_)) {
    if (++intentosToken_ >= MAX_INTENTOS_TOKEN) tBloqueoToken_ = millis();
    responder(401, "{\"ok\":false,\"resultado\":\"TOKEN_INVALIDO\",\"error\":\"token incorrecto\"}");
    return false;
  }
  intentosToken_ = 0;
  return true;
}

void Red::manejarDispensar() {
  if (!tokenValido()) return;
  // "porciones" debe ser 1 o 2 dígitos: cualquier otra cosa se rechaza sin mover nada.
  String s = servidor_.arg("porciones");
  bool numerico = s.length() >= 1 && s.length() <= 2;
  for (unsigned i = 0; numerico && i < s.length(); i++) numerico = s[i] >= '0' && s[i] <= '9';
  Solicitud r = Solicitud::PORCIONES_INVALIDAS;
  if (numerico && m_.dispensar) r = m_.dispensar((uint8_t)s.toInt());

  int codigo = 409;  // conflicto con el estado actual (ocupado, cooldown, tolva vacía...)
  if (r == Solicitud::ACEPTADA) codigo = 202;
  else if (r == Solicitud::PORCIONES_INVALIDAS) codigo = 400;
  else if (r == Solicitud::DESHABILITADA) codigo = 403;
  char buf[128];
  snprintf(buf, sizeof(buf), "{\"ok\":%s,\"resultado\":\"%s\",\"cooldown_s\":%lu}",
           r == Solicitud::ACEPTADA ? "true" : "false", nombreSolicitud(r),
           (unsigned long)(m_.cooldownS ? m_.cooldownS() : 0));
  responder(codigo, String(buf));
}

void Red::manejarReset() {
  if (!tokenValido()) return;
  bool habia = m_.borrarErrores ? m_.borrarErrores() : false;
  responder(200, habia ? "{\"ok\":true,\"resultado\":\"ERRORES_BORRADOS\"}" : "{\"ok\":true,\"resultado\":\"SIN_ERRORES\"}");
}

void Red::iniciarServidor(const ManejadoresRed& manejadores, const char* token) {
  m_ = manejadores;
  token_ = token ? token : "";
#ifdef SIMULACION_QEMU
  return;  // sin Wi-Fi no hay pila TCP/IP en el emulador
#endif
  servidor_.on("/status", HTTP_GET, [this]() {
    responder(200, m_.estadoJson ? m_.estadoJson() : String("{}"));
  });
  servidor_.on("/dispensar", HTTP_POST, [this]() { manejarDispensar(); });
  servidor_.on("/reset-errores", HTTP_POST, [this]() { manejarReset(); });
  // Cualquier otra ruta o método (p. ej. GET /dispensar) NO ejecuta nada.
  servidor_.onNotFound([this]() { responder(404, "{\"error\":\"ruta o metodo no permitido\"}"); });
  servidor_.begin();
}

void Red::atender() {
#ifndef SIMULACION_QEMU
  servidor_.handleClient();
  descubrir();
#endif
}
