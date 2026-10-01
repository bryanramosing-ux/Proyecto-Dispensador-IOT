#pragma once
#include "WiFi.h"
class HTTPClient {
 public:
  void setConnectTimeout(int32_t) {}
  void setTimeout(uint16_t) {}
  bool begin(const String&) { return true; }
  int GET() { return 200; }
  String getString() { return String("{}"); }
  void end() {}
};
