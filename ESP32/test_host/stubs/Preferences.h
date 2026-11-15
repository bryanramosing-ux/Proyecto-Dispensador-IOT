#pragma once
#include "Arduino.h"
#include <vector>
namespace NvsPrueba {
inline std::vector<uint8_t> blob;
inline bool existe = false, abrirOk = true, escribirOk = true;
}
class Preferences {
 public:
  bool begin(const char*, bool = false) { return NvsPrueba::abrirOk; }
  float getFloat(const char*, float d) { return d; }
  size_t putFloat(const char*, float) { return 4; }
  bool isKey(const char*) { return NvsPrueba::existe; }
  size_t getBytesLength(const char*) { return NvsPrueba::blob.size(); }
  size_t getBytes(const char*, void* destino, size_t n) {
    if (n != NvsPrueba::blob.size()) return 0;
    memcpy(destino, NvsPrueba::blob.data(), n);
    return n;
  }
  size_t putBytes(const char*, const void* datos, size_t n) {
    if (!NvsPrueba::escribirOk) return 0;
    auto p = static_cast<const uint8_t*>(datos);
    NvsPrueba::blob.assign(p, p + n);
    NvsPrueba::existe = true;
    return n;
  }
  void end() {}
};
