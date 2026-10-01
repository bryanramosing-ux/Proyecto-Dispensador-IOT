#include "Red.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

// SIMULACION_QEMU: solo para arrancar el firmware en el emulador QEMU de Espressif,
// que no emula la radio Wi-Fi. Nunca definirlo al compilar para la placa real.
#ifdef SIMULACION_QEMU
void Red::iniciar(const char*, const char*) { Serial.println("SIMULACION_QEMU: Wi-Fi desactivado"); }
bool Red::conectado() { return false; }
void Red::reconectar() { Serial.println("Wi-Fi: reintentando conexion... (simulado)"); }
#else
void Red::iniciar(const char* ssid, const char* clave) {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  IPAddress ip, gw, mascara;
  if (strlen(IP_ESP32) > 0 && ip.fromString(IP_ESP32) && gw.fromString(IP_GATEWAY) &&
      mascara.fromString(IP_MASCARA)) {
    WiFi.config(ip, gw, mascara, gw);  // IP fija: el PC y la cámara saben dónde está
  }
  WiFi.begin(ssid, clave);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(250);
  if (conectado()) {
    Serial.printf("Wi-Fi OK  IP=%s  RSSI=%d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    Serial.println("Wi-Fi: sin conexion (se reintentara)");
  }
}

bool Red::conectado() { return WiFi.status() == WL_CONNECTED; }

void Red::reconectar() {
  // Sin WiFi.disconnect(): cortaría un intento de asociación que todavía está en curso.
  Serial.println("Wi-Fi: reintentando conexion...");
  WiFi.reconnect();
}
#endif

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

bool Red::servidorDisponible() { return getSimple(String(URL_PC) + "/status", TIMEOUT_ESTADO_MS); }

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
  String url = String(URL_PC) + "/classify?dist=" + String(distanciaCm);
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

void Red::iniciarServidorEstado(GeneradorEstado generador) {
  generador_ = generador;
#ifdef SIMULACION_QEMU
  return;  // sin Wi-Fi no hay pila TCP/IP en el emulador
#endif
  servidor_.on("/status", HTTP_GET, [this]() {
    servidor_.send(200, "application/json", generador_ ? generador_() : String("{}"));
  });
  servidor_.onNotFound([this]() { servidor_.send(404, "application/json", "{\"error\":\"ruta desconocida\"}"); });
  servidor_.begin();
}

void Red::atender() {
#ifndef SIMULACION_QEMU
  servidor_.handleClient();
#endif
}
