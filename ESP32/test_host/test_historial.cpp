#include "../Dispensador_ESP32/HistorialNVS.h"
#include <cassert>
#include <cstdio>
int main() {
  uint8_t cuentas[4] = {};
  uint32_t totales[4] = {};
  assert(HistorialNVS::cargar(cuentas, totales, 3)); // primera instalación: prueba de escritura
  cuentas[1] = 2; totales[1] = 10;
  assert(HistorialNVS::guardar(cuentas, totales, 3));
  cuentas[1] = 0; totales[1] = 0;
  assert(HistorialNVS::cargar(cuentas, totales, 3) && cuentas[1] == 2 && totales[1] == 10);
  // Migrar a firmware con clase manual no pierde el historial anterior.
  assert(HistorialNVS::cargar(cuentas, totales, 4) && cuentas[3] == 0);
  cuentas[3] = 1;
  assert(HistorialNVS::guardar(cuentas, totales, 4));
  assert(!HistorialNVS::cargar(cuentas, totales, 3));
  cuentas[3] = 0;
  assert(HistorialNVS::guardar(cuentas, totales, 4));
  auto correcto = NvsPrueba::blob;
  NvsPrueba::blob[15] ^= 0x80;
  assert(!HistorialNVS::cargar(cuentas, totales, 4)); // corrupción nunca se convierte en cero
  NvsPrueba::blob = correcto; NvsPrueba::blob.pop_back();
  assert(!HistorialNVS::cargar(cuentas, totales, 4));
  NvsPrueba::blob = correcto; NvsPrueba::escribirOk = false;
  assert(!HistorialNVS::guardar(cuentas, totales, 4));
  NvsPrueba::existe = false;
  assert(!HistorialNVS::cargar(cuentas, totales, 4)); // no permite arrancar sin poder persistir
  NvsPrueba::abrirOk = false;
  assert(!HistorialNVS::cargar(cuentas, totales, 4));
  puts("Historial NVS: instalación, reinicio, migración, corrupción y fallos de escritura OK");
}
