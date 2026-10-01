#pragma once
#include "Arduino.h"
enum wl_status_t { WL_IDLE_STATUS = 0, WL_CONNECTED = 3, WL_DISCONNECTED = 6 };
enum wifi_mode_t { WIFI_STA = 1 };
class IPAddress {
 public:
  bool fromString(const char*) { return true; }
  String toString() const { return String("0.0.0.0"); }
};
class WiFiClass {
 public:
  void persistent(bool) {}
  void mode(wifi_mode_t) {}
  void setAutoReconnect(bool) {}
  void setSleep(bool) {}
  bool config(IPAddress, IPAddress, IPAddress, IPAddress) { return true; }
  void begin(const char*, const char*) {}
  wl_status_t status() { return WL_CONNECTED; }
  bool disconnect() { return true; }
  bool reconnect() { return true; }
  IPAddress localIP() { return IPAddress(); }
  int RSSI() { return -60; }
};
extern WiFiClass WiFi;
class WiFiClient : public Stream {};
