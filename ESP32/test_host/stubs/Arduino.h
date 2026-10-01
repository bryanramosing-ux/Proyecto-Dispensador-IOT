// Stub MÍNIMO de la API Arduino-ESP32 SOLO para verificar la compilación en PC.
// No se usa en el microcontrolador.
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <algorithm>
#include <cctype>
#include <string>

#ifndef ESP_ARDUINO_VERSION_MAJOR
#define ESP_ARDUINO_VERSION_MAJOR 3
#endif
#define HIGH 1
#define LOW 0
#define INPUT 0x01
#define OUTPUT 0x03
#define INPUT_PULLUP 0x05
#define F(x) (x)
typedef const char* PGM_P;
typedef bool boolean;
typedef uint8_t byte;
enum adc_attenuation_t { ADC_0db, ADC_2_5db, ADC_6db, ADC_11db };

class String {
 public:
  String() {}
  String(const char* s) : s_(s ? s : "") {}
  String(const std::string& s) : s_(s) {}
  String(int v) : s_(std::to_string(v)) {}
  String(long v) : s_(std::to_string(v)) {}
  String(unsigned v) : s_(std::to_string(v)) {}
  String(unsigned long v) : s_(std::to_string(v)) {}
  const char* c_str() const { return s_.c_str(); }
  unsigned length() const { return (unsigned)s_.size(); }
  bool concat(const char* s, unsigned n) { s_.append(s, n); return true; }
  bool concat(char c) { s_ += c; return true; }
  bool concat(const char* s) { s_ += s; return true; }
  bool reserve(unsigned n) { s_.reserve(n); return true; }
  char operator[](unsigned i) const { return s_[i]; }
  String& operator+=(char c) { s_ += c; return *this; }
  String& operator+=(const String& o) { s_ += o.s_; return *this; }
  friend String operator+(const String& a, const String& b) { return String(a.s_ + b.s_); }
  friend String operator+(const String& a, const char* b) { return String(a.s_ + b); }
  bool operator==(const char* o) const { return s_ == o; }
  bool operator==(const String& o) const { return s_ == o.s_; }
  int indexOf(char c) const { auto p = s_.find(c); return p == std::string::npos ? -1 : (int)p; }
  String substring(unsigned a) const { return String(s_.substr(a)); }
  String substring(unsigned a, unsigned b) const { return String(s_.substr(a, b - a)); }
  long toInt() const { return atol(s_.c_str()); }
  void trim() {
    while (!s_.empty() && isspace((unsigned char)s_.back())) s_.pop_back();
    while (!s_.empty() && isspace((unsigned char)s_.front())) s_.erase(0, 1);
  }
  void toUpperCase() { for (auto& c : s_) c = (char)toupper((unsigned char)c); }
 private:
  std::string s_;
};

class Print {
 public:
  virtual ~Print() {}
  virtual size_t write(uint8_t) { return 1; }
  virtual size_t write(const uint8_t*, size_t n) { return n; }
  size_t printf(const char*, ...) { return 0; }
  size_t print(const char*) { return 0; }
  size_t println(const char* = "") { return 0; }
  size_t println(const String&) { return 0; }
};
class Stream : public Print {
 public:
  virtual int available() { return 0; }
  virtual int read() { return -1; }
  virtual int peek() { return -1; }
  size_t readBytes(char*, size_t) { return 0; }
};
class HardwareSerial : public Stream {
 public:
  void begin(unsigned long) {}
};
extern HardwareSerial Serial;

class EspClass {
 public:
  void restart() {}
  uint32_t getFreeHeap() { return 0; }
};
extern EspClass ESP;

unsigned long millis();
void delay(uint32_t);
void delayMicroseconds(uint32_t);
void pinMode(uint8_t, uint8_t);
void digitalWrite(uint8_t, uint8_t);
int digitalRead(uint8_t);
unsigned long pulseIn(uint8_t, uint8_t, unsigned long = 1000000L);
uint32_t analogReadMilliVolts(uint8_t);
void analogSetPinAttenuation(uint8_t, adc_attenuation_t);
bool psramFound();
// LEDC: API núcleo 3.x y 2.x
bool ledcAttach(uint8_t pin, uint32_t freq, uint8_t res);
uint32_t ledcSetup(uint8_t ch, uint32_t freq, uint8_t res);
void ledcAttachPin(uint8_t pin, uint8_t ch);
void ledcWrite(uint8_t pinOrCh, uint32_t duty);
