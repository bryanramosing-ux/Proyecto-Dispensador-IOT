// Copie este archivo como "secrets.h" (no se sube a GitHub) y complete los datos
// de SU red. Nunca escriba datos reales en este archivo de ejemplo.
#pragma once

// --- Wi-Fi (2,4 GHz, WPA2-Personal) -------------------------------------------
#define WIFI_SSID  "NOMBRE_DE_SU_RED_2.4GHz"
#define WIFI_CLAVE "CONTRASENA"

// --- Token compartido con el backend (backend/.env -> TOKEN_DISPOSITIVO) -------
// Vacío = el ESP32 RECHAZA los comandos remotos (dispensar / borrar errores).
// Genere uno propio, por ejemplo:  python -c "import secrets; print(secrets.token_hex(8))"
#define TOKEN_DISPOSITIVO ""

// --- Backend (PC con el dashboard) ---------------------------------------------
// "" = descubrimiento automático en la LAN (recomendado: no hay que saber la IP del PC).
// Si su red bloquea el broadcast UDP, escriba la dirección: "http://192.168.1.50:8001"
#define URL_BACKEND ""

// --- IP del ESP32 ----------------------------------------------------------------
// "" = DHCP (recomendado). El backend aprende la IP sola cuando el ESP32 se anuncia.
// IP fija: complete los tres valores según SU red (deben coincidir con el router).
#define IP_ESP32    ""
#define IP_GATEWAY  "192.168.1.1"
#define IP_MASCARA  "255.255.255.0"

// --- Solo para el modo automático opcional (USAR_DETECCION_AUTOMATICA 1) --------
#define URL_VISION  "http://192.168.1.50:8000"   // OpenCV/servidor_vision.py
#define URL_CAMARA  "http://192.168.1.51"        // ESP32-CAM
