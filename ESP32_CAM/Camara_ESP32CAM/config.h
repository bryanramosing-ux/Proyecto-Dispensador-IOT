// config.h - ESP32-CAM (AI-Thinker). Solo captura y entrega imágenes por HTTP.
#pragma once

// Red (IP fija: el PC la usa en OpenCV/config.py -> CAMARA_URL)
#define IP_CAMARA    "192.168.1.51"   // "" = DHCP
#define IP_GATEWAY   "192.168.1.1"
#define IP_MASCARA   "255.255.255.0"

// Imagen. VGA (640x480) es suficiente para el clasificador (entrada 224x224)
// y produce JPEG de pocas decenas de kB: transmisión rápida por Wi-Fi.
#define TAMANO_FOTO      FRAMESIZE_VGA
#define CALIDAD_JPEG     12        // 10-63 (menor = mejor calidad, más bytes)
#define USAR_FLASH       0         // LED GPIO4: muy brillante (puede asustar) y consume más
#define T_FLASH_MS       120

#define WIFI_REINTENTO_MS   5000UL
#define WIFI_REINICIO_MS  120000UL  // sin Wi-Fi 2 min -> reinicio
