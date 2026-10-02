// =============================================================================
//  DISPENSADOR INTELIGENTE - Firmware de la ESP32-CAM (AI-Thinker, OV2640)
// =============================================================================
//  Responsabilidad ÚNICA: capturar una foto cuando se la piden y entregarla.
//  NO clasifica (eso lo hace el PC con OpenCV) y NO controla el servo.
//
//  Endpoints HTTP (puerto 80):
//    GET /capture -> image/jpeg  (foto nueva)         | 503 si la cámara falla
//    GET /status  -> application/json (diagnóstico)
//
//  Programación: adaptador USB-TTL de 3,3 V (TX->U0R, RX->U0T, GND, 5V) o placa
//  ESP32-CAM-MB. Unir GPIO0 a GND durante el arranque para entrar en modo carga.
//  Placa en Arduino IDE: "AI Thinker ESP32-CAM".
// =============================================================================
#include <Arduino.h>
#include <WebServer.h>
#include <WiFi.h>

#include "esp_camera.h"
#include "config.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#warning "Falta secrets.h: se usa secrets_ejemplo.h (copie y complete sus datos de Wi-Fi)"
#include "secrets_ejemplo.h"
#endif

// --- Pines fijos del módulo AI-Thinker (ocupados por la cámara) ---------------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define FLASH_GPIO_NUM     4   // LED de flash (alto = encendido)
#define LED_ROJO_GPIO_NUM 33   // LED rojo de la placa (activo en BAJO)

WebServer servidor(80);
bool camaraOk = false;
uint32_t fotosOk = 0, fotosFallidas = 0, tSinWifi = 0, tReintento = 0, tReintentoCam = 0;

bool iniciarCamara() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM;
  c.pin_d1 = Y3_GPIO_NUM;
  c.pin_d2 = Y4_GPIO_NUM;
  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;
  c.pin_d5 = Y7_GPIO_NUM;
  c.pin_d6 = Y8_GPIO_NUM;
  c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM;
  c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM;
  c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM;
  c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM;
  c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = TAMANO_FOTO;
  c.jpeg_quality = CALIDAD_JPEG;
  // MODO FOTO (idea del profesor: no grabar, solo sacar fotos): con un solo búfer el
  // controlador NO captura cuadros de forma continua; toma uno cuando se lo pide /capture.
  // El sensor sigue encendido, así la exposición automática ya está ajustada.
  if (psramFound()) {
    c.fb_count = 1;
    c.fb_location = CAMERA_FB_IN_PSRAM;
    c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  } else {
    c.fb_count = 1;
    c.fb_location = CAMERA_FB_IN_DRAM;
    c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    if (c.frame_size > FRAMESIZE_SVGA) c.frame_size = FRAMESIZE_SVGA;
  }
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("ERROR camara 0x%x (revise cinta FPC y alimentacion 5 V)\n", err);
    return false;
  }
  sensor_t* s = esp_camera_sensor_get();
  s->set_whitebal(s, 1);
  s->set_exposure_ctrl(s, 1);
  s->set_gain_ctrl(s, 1);
  return true;
}

// Devuelve un cuadro "fresco": el que quedó en el búfer puede ser de la foto anterior
// (segundos o minutos atrás), así que se descarta y se toma uno nuevo.
camera_fb_t* capturarFresca() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (fb) esp_camera_fb_return(fb);
  return esp_camera_fb_get();
}

void manejarCaptura() {
  if (!camaraOk) {
    fotosFallidas++;
    servidor.send(503, "application/json", "{\"error\":\"camara no inicializada\"}");
    return;
  }
#if USAR_FLASH
  digitalWrite(FLASH_GPIO_NUM, HIGH);
  delay(T_FLASH_MS);
#endif
  camera_fb_t* fb = capturarFresca();
#if USAR_FLASH
  digitalWrite(FLASH_GPIO_NUM, LOW);
#endif
  if (!fb || fb->format != PIXFORMAT_JPEG || fb->len == 0) {
    if (fb) esp_camera_fb_return(fb);
    fotosFallidas++;
    servidor.send(503, "application/json", "{\"error\":\"fallo de captura\"}");
    return;
  }
  servidor.sendHeader("Cache-Control", "no-store");
  servidor.setContentLength(fb->len);
  servidor.send(200, "image/jpeg", "");
  servidor.client().write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
  fotosOk++;
}

void manejarEstado() {
  char buf[256];
  snprintf(buf, sizeof(buf),
           "{\"camara\":%s,\"psram\":%s,\"fotos_ok\":%lu,\"fotos_fallidas\":%lu,"
           "\"rssi\":%d,\"heap\":%u,\"uptime_s\":%lu}",
           camaraOk ? "true" : "false", psramFound() ? "true" : "false",
           (unsigned long)fotosOk, (unsigned long)fotosFallidas, WiFi.RSSI(),
           (unsigned)ESP.getFreeHeap(), (unsigned long)(millis() / 1000));
  servidor.send(camaraOk ? 200 : 503, "application/json", buf);
}

void conectarWifi() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);   // menor latencia al responder /capture
  WiFi.setAutoReconnect(true);
  IPAddress ip, gw, mascara;
  if (strlen(IP_CAMARA) > 0 && ip.fromString(IP_CAMARA) && gw.fromString(IP_GATEWAY) &&
      mascara.fromString(IP_MASCARA)) {
    WiFi.config(ip, gw, mascara, gw);
  }
  WiFi.begin(WIFI_SSID, WIFI_CLAVE);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(250);
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Wi-Fi OK  http://%s/capture  RSSI=%d dBm\n", WiFi.localIP().toString().c_str(),
                  WiFi.RSSI());
  } else {
    Serial.println("Wi-Fi: sin conexion (se reintentara)");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== Dispensador IoT - ESP32-CAM ===");
  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW);
  pinMode(LED_ROJO_GPIO_NUM, OUTPUT);
  digitalWrite(LED_ROJO_GPIO_NUM, HIGH);  // apagado

  camaraOk = iniciarCamara();
  conectarWifi();
  servidor.on("/capture", HTTP_GET, manejarCaptura);
  servidor.on("/status", HTTP_GET, manejarEstado);
  servidor.onNotFound([]() { servidor.send(404, "application/json", "{\"error\":\"ruta desconocida\"}"); });
  servidor.begin();
}

void loop() {
  servidor.handleClient();

  // LED rojo encendido = sin Wi-Fi o cámara con fallo
  bool problema = !camaraOk || WiFi.status() != WL_CONNECTED;
  digitalWrite(LED_ROJO_GPIO_NUM, problema ? LOW : HIGH);

  if (WiFi.status() != WL_CONNECTED) {
    if (tSinWifi == 0) tSinWifi = millis();
    if (millis() - tReintento > WIFI_REINTENTO_MS) {
      tReintento = millis();
      WiFi.reconnect();
    }
    if (millis() - tSinWifi > WIFI_REINICIO_MS) ESP.restart();
  } else {
    tSinWifi = 0;
  }

  if (!camaraOk && millis() - tReintentoCam > 10000) {  // reintento de inicialización
    tReintentoCam = millis();
    esp_camera_deinit();
    camaraOk = iniciarCamara();
  }
  delay(2);
}
