#pragma once
#include <functional>
#include "WiFi.h"
enum HTTPMethod { HTTP_GET = 1 };
class WebServer {
 public:
  explicit WebServer(int) {}
  void on(const char*, HTTPMethod, std::function<void()>) {}
  void onNotFound(std::function<void()>) {}
  void begin() {}
  void handleClient() {}
  void send(int, const char*, const String&) {}
  void send(int, const char*, const char*) {}
  void sendHeader(const char*, const char*) {}
  void setContentLength(size_t) {}
  WiFiClient& client() { return c_; }
 private:
  WiFiClient c_;
};
