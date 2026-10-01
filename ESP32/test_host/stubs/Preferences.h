#pragma once
#include "Arduino.h"
class Preferences {
 public:
  bool begin(const char*, bool = false) { return true; }
  float getFloat(const char*, float d) { return d; }
  size_t putFloat(const char*, float) { return 4; }
  void end() {}
};
