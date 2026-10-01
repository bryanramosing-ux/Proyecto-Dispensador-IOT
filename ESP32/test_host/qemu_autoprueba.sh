#!/usr/bin/env bash
# Arranca el firmware REAL del ESP32 (compilado con -DSIMULACION_QEMU) en el emulador
# QEMU de Espressif y verifica la autoprueba que ejecuta setup().
#
#   qemu_autoprueba.sh <carpeta_build> <boot_app0.bin> <qemu-system-xtensa> [timeout_s]
#
# <carpeta_build> debe contener Dispensador_ESP32.ino.{bootloader.bin,partitions.bin,bin}
# (arduino-cli compile --build-path ... --build-property "compiler.cpp.extra_flags=-DSIMULACION_QEMU").
# QEMU no emula la radio Wi-Fi ni el ADC: la variante de simulación los sustituye y el
# resto del código (arranque, PWM del servo, HC-SR04, máquina de estados, comandos) es el real.
set -euo pipefail
BUILD="$1"; BOOT_APP0="$2"; QEMU="$3"; TIEMPO="${4:-240}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

esptool.py --chip esp32 merge_bin --fill-flash-size 4MB -o "$TMP/flash.bin" \
  0x1000 "$BUILD/Dispensador_ESP32.ino.bootloader.bin" \
  0x8000 "$BUILD/Dispensador_ESP32.ino.partitions.bin" \
  0xe000 "$BOOT_APP0" \
  0x10000 "$BUILD/Dispensador_ESP32.ino.bin" >/dev/null

LOG="$TMP/serie.log"
: > "$LOG"
if ! "$QEMU" --version >/dev/null 2>&1; then
  echo "ERROR: no se puede ejecutar $QEMU (¿faltan bibliotecas? ldd lo indica):"
  ldd "$QEMU" | grep "not found" || true
  exit 2
fi
"$QEMU" -machine esp32 -display none -serial "file:$LOG" -drive "file=$TMP/flash.bin,if=mtd,format=raw" &
PID=$!
for _ in $(seq "$TIEMPO"); do
  if grep -aq "AUTOPRUEBA_FIN" "$LOG" 2>/dev/null; then break; fi
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
  sleep 1
done
sleep 1
kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true

tr -d '\000' < "$LOG" | sed -n '/=== Dispensador/,$p'

fallos=0
esperar() {
  if grep -aqF -- "$1" "$LOG"; then echo "[OK]    $1"; else echo "[FALTA] $1"; fallos=$((fallos + 1)); fi
}
prohibir() {
  if grep -aqF -- "$1" "$LOG"; then echo "[ERROR] aparece: $1"; fallos=$((fallos + 1)); fi
}
echo "---------------- verificación ----------------"
esperar "=== Dispensador IoT - ESP32 controlador ==="
esperar "[ESPERANDO] -> [ERROR_WIFI] : sin Wi-Fi al iniciar"
esperar "DIST | SERVO <us> | CICLO <n>"
esperar '"estado":"ERROR_WIFI"'
esperar "Distancia: -1.0 cm"
esperar "Bateria 7.60 V | Servo 6.00 V"
esperar "Servo -> 1200 us OK"
esperar "Rango permitido 500..2500 us"
esperar "CICLO x1 -> OK"
esperar "motivo=SIN_WIFI (NO se dispensa)"
esperar "[ERROR_WIFI] -> [ESPERANDO] : errores borrados manualmente"
esperar "AUTOPRUEBA_FIN"
prohibir "Guru Meditation"
prohibir "assert failed"
prohibir "Rebooting..."
prohibir "Brownout"
if [ "$fallos" -eq 0 ]; then echo "AUTOPRUEBA QEMU: OK"; else echo "AUTOPRUEBA QEMU: $fallos FALLO(S)"; exit 1; fi
