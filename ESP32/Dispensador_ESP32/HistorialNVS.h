#pragma once
#include <Preferences.h>
#include <stdint.h>
#include <string.h>

// Un solo blob NVS: evita combinar cuentas y totales de escrituras diferentes.
// No se guardan millis() entre arranques: no son un reloj persistente.
class HistorialNVS {
  struct Datos {
    uint32_t magic, version, clases;
    uint32_t cuentas[4], totales[4];
    uint32_t suma;
  };

  static uint32_t checksum(const Datos& d) {
    const auto* p = reinterpret_cast<const uint8_t*>(&d);
    uint32_t h = 2166136261UL;
    for (unsigned i = 0; i < sizeof(Datos) - sizeof(d.suma); i++) h = (h ^ p[i]) * 16777619UL;
    return h;
  }

 public:
  static bool guardar(const uint8_t* cuentas, const uint32_t* totales, uint8_t clases) {
    if (clases < 2 || clases > 4) return false;
    Datos d{};
    d.magic = 0x52414331;
    d.version = 1;
    d.clases = clases;
    for (uint8_t c = 0; c < clases; c++) {
      if (cuentas[c] > 48) return false;
      d.cuentas[c] = cuentas[c];
      d.totales[c] = totales[c];
    }
    d.suma = checksum(d);
    Preferences p;
    if (!p.begin("raciones", false)) return false;
    bool ok = p.putBytes("registro", &d, sizeof(d)) == sizeof(d);
    p.end();
    return ok;
  }

  static bool cargar(uint8_t* cuentas, uint32_t* totales, uint8_t clases) {
    if (clases < 2 || clases > 4) return false;
    Preferences p;
    if (!p.begin("raciones", false)) return false;
    if (!p.isKey("registro")) {
      p.end();
      memset(cuentas, 0, clases * sizeof(*cuentas));
      memset(totales, 0, clases * sizeof(*totales));
      return guardar(cuentas, totales, clases);
    }
    Datos d{};
    bool ok = p.getBytesLength("registro") == sizeof(d) &&
              p.getBytes("registro", &d, sizeof(d)) == sizeof(d);
    p.end();
    if (!ok || d.magic != 0x52414331 || d.version != 1 || d.clases < 2 || d.clases > 4 ||
        d.suma != checksum(d)) return false;
    // Nunca descartar una clase con raciones activas al cambiar de firmware.
    for (uint8_t c = clases; c < d.clases; c++) if (d.cuentas[c]) return false;
    for (uint8_t c = 0; c < clases; c++) {
      if (d.cuentas[c] > 48) return false;
      cuentas[c] = d.cuentas[c];
      totales[c] = d.totales[c];
    }
    return true;
  }
};
