// =============================================================================
//  Controlador.h  -  Máquina de estados del dispensador
// =============================================================================
//  Esta clase NO toca hardware: todo lo físico pasa por la interfaz Hardware.
//  Así la lógica se puede compilar y probar en un PC (ver ESP32/test_host).
// =============================================================================
#pragma once
#include <stdint.h>

enum class Estado : uint8_t {
  ESPERANDO,
  DETECTADO,
  CAPTURANDO,
  PROCESANDO,
  CLASIFICADO,
  DOSIFICANDO,
  FINALIZADO,
  ERROR_WIFI,
  ERROR_CAMARA,
  ERROR_CLASIFICACION,
  ERROR_SERVO,
  ERROR_ALIMENTACION,
  ERROR_MECANISMO,
};

const char* nombreEstado(Estado e);

// Clases que devuelve el PC
enum : int { CLASE_INDETERMINADA = 0, CLASE_PERRO = 1, CLASE_GATO = 2 };

enum class TipoRespuesta : uint8_t { OK, ERROR_CAMARA, ERROR_SERVIDOR };

struct RespuestaClasificacion {
  TipoRespuesta tipo = TipoRespuesta::ERROR_SERVIDOR;
  int clase = CLASE_INDETERMINADA;
  float confianza = 0.0f;
  char motivo[28] = "";
};

enum class ResultadoDosis : uint8_t { OK, SIN_ALIMENTACION_SERVO, ATASCO };

// Todo lo que el controlador necesita del mundo físico / la red.
class Hardware {
 public:
  virtual ~Hardware() {}
  virtual uint32_t ahoraMs() = 0;
  virtual float distanciaCm() = 0;            // < 0 si no hay eco
  virtual bool wifiConectado() = 0;
  virtual void reconectarWifi() = 0;
  virtual bool camaraDisponible() = 0;        // GET cámara /status
  virtual bool servidorDisponible() = 0;      // GET PC /status
  virtual RespuestaClasificacion clasificar(int distanciaCm) = 0;  // GET PC /classify
  virtual float voltajeBateria() = 0;
  virtual float voltajeServo() = 0;
  virtual ResultadoDosis dosificar(uint8_t ciclos) = 0;
  virtual bool botonResetPulsado() = 0;       // pulsación larga ya filtrada
  virtual void reiniciar() = 0;
  virtual void log(const char* mensaje) = 0;
};

struct Parametros {
  float distMinCm, distDeteccionCm, distLibreCm;
  uint8_t lecturasConfirmacion;
  uint32_t zonaLibreMs;
  uint8_t maxIntentosClasificacion;
  uint32_t reintentoClasificacionMs;
  uint8_t ciclos[3];          // índice = clase (0 sin uso)
  bool habilitada[3];
  uint32_t cooldownClaseMs[3];
  uint8_t maxRacionesDia[3];
  uint8_t maxCiclosPorRacion;
  uint32_t cooldownGlobalMs;
  bool usarMonitorBateria;
  float vbatMin, vbatHisteresis;
  bool usarMonitorServo;
  float vservoMin;
  uint32_t wifiReintentoMs, wifiReinicioMs, errorReintentoMs;
};

class Controlador {
 public:
  static const uint8_t REGISTRO = 48;   // raciones recordadas por clase (ventana 24 h)

  Controlador(Hardware& hw, const Parametros& p);
  void iniciar();
  void actualizar();               // llamar periódicamente desde loop()
  void borrarErrores();            // comando serie RESET o botón BOOT

  Estado estado() const { return estado_; }
  int ultimaClase() const { return ultimaClase_; }
  float ultimaConfianza() const { return ultimaConfianza_; }
  const char* ultimoMotivo() const { return ultimoMotivo_; }
  float ultimaDistancia() const { return ultimaDistancia_; }
  uint32_t racionesTotales(int clase) const { return clase >= 1 && clase <= 2 ? totales_[clase] : 0; }
  uint8_t racionesUltimas24h(int clase) const;
  uint32_t cooldownRestanteMs() const;

 private:
  void cambiarA(Estado nuevo, const char* motivo = nullptr);
  bool esErrorBloqueante() const;
  bool mascotaPresente(float d) const;
  void registrarRacion(int clase);
  bool racionPermitida(int clase, char* porque, int n);
  void volverAEsperar(const char* motivo);
  void logf(const char* fmt, ...);

  Hardware& hw_;
  Parametros p_;
  Estado estado_ = Estado::ESPERANDO;
  uint32_t tEstado_ = 0;
  uint32_t tUltimoReintento_ = 0;

  // Detección
  uint8_t lecturasPresente_ = 0;
  bool zonaArmada_ = true;
  bool contandoZonaLibre_ = false;
  uint32_t tZonaLibre_ = 0;
  float ultimaDistancia_ = -1.0f;

  // Clasificación
  uint8_t intentos_ = 0;
  uint8_t fallosCamara_ = 0;
  int ultimaClase_ = CLASE_INDETERMINADA;
  float ultimaConfianza_ = 0.0f;
  char ultimoMotivo_[28] = "";

  // Raciones
  bool huboRacion_ = false;
  uint32_t tUltimaRacion_ = 0;
  uint32_t registro_[3][REGISTRO] = {};
  uint8_t nRegistro_[3] = {0, 0, 0};
  uint8_t posRegistro_[3] = {0, 0, 0};
  uint32_t totales_[3] = {0, 0, 0};
};
