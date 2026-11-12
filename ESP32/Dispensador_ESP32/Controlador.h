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
enum : int { CLASE_INDETERMINADA = 0, CLASE_PERRO = 1, CLASE_GATO = 2, CLASE_MANUAL = 3, N_CLASES = 4 };

enum class TipoRespuesta : uint8_t { OK, ERROR_CAMARA, ERROR_SERVIDOR };

struct RespuestaClasificacion {
  TipoRespuesta tipo = TipoRespuesta::ERROR_SERVIDOR;
  int clase = CLASE_INDETERMINADA;
  float confianza = 0.0f;
  char motivo[28] = "";
};

enum class ResultadoDosis : uint8_t { OK, SIN_ALIMENTACION_SERVO, ATASCO, NINGUNA };
const char* nombreResultado(ResultadoDosis r);

// Respuesta a un pedido de dispensación manual. Solo ACEPTADA mueve el servo.
enum class Solicitud : uint8_t {
  ACEPTADA,
  OCUPADO,                  // ya hay una dosis en curso o pendiente
  ERROR_ACTIVO,             // el equipo está en un estado de error
  PORCIONES_INVALIDAS,      // fuera de 1..maxPorcionesManual
  DESHABILITADA,            // dispensación manual desactivada en config.h
  COOLDOWN,                 // todavía no pasó el tiempo mínimo entre raciones
  LIMITE_DIARIO,
  TOLVA_VACIA,
  SIN_ALIMENTACION_SERVO,
};
const char* nombreSolicitud(Solicitud s);

// Quién pidió la última dosis
enum class Origen : uint8_t { NINGUNO, PANEL, BOTON, SERIE, AUTOMATICO };
const char* nombreOrigen(Origen o);

// Alertas que el ESP32 envía al PC (POST /alerta) sobre el nivel de la tolva
enum class Alerta : uint8_t { NINGUNA, COMIDA_BAJA, COMIDA_AGOTADA, COMIDA_REPUESTA, SENSOR_NIVEL_SIN_LECTURA };
const char* nombreAlerta(Alerta a);

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
  virtual float nivelTolvaPct() = 0;          // 0-100 %; < 0 si no hay lectura válida
  virtual bool notificar(Alerta a, float nivelPct) = 0;  // true si el PC la recibió
  virtual bool botonResetPulsado() = 0;       // pulsación larga ya filtrada
  virtual bool botonDispensarPulsado() = 0;   // pulsación corta ya filtrada (un evento por pulsación)
  virtual void reiniciar() = 0;
  virtual void log(const char* mensaje) = 0;
};

struct Parametros {
  float distMinCm, distDeteccionCm, distLibreCm;
  uint8_t lecturasConfirmacion;
  uint32_t zonaLibreMs;
  uint8_t maxIntentosClasificacion;
  uint32_t reintentoClasificacionMs;
  // Índice = clase (0 sin uso, 1 perro, 2 gato, 3 manual).
  // ciclos[CLASE_MANUAL] = ciclos del disco por cada porción pedida.
  uint8_t ciclos[N_CLASES];
  bool habilitada[N_CLASES];
  uint32_t cooldownClaseMs[N_CLASES];
  uint8_t maxRacionesDia[N_CLASES];
  uint8_t maxPorcionesManual;       // porciones máximas por pedido manual
  bool botonDispensa;               // pulsación corta del botón = 1 porción
  // false = solo nivel + dispensación manual (un HC-SR04, sin visión). En ese modo
  // la falta de Wi-Fi NO es un error: el control local sigue funcionando.
  bool usarDeteccionAutomatica;
  uint8_t maxCiclosPorRacion;
  uint32_t cooldownGlobalMs;
  bool usarMonitorBateria;
  float vbatMin, vbatHisteresis;
  bool usarMonitorServo;
  float vservoMin;
  uint32_t wifiReintentoMs, wifiReinicioMs, errorReintentoMs;
  // Nivel de la tolva (HC-SR04 en la tapa)
  bool usarSensorNivel;
  uint32_t intervaloNivelMs;
  float nivelAlertaPct, nivelRearmePct, nivelVacioPct;
  uint8_t lecturasNivel;          // lecturas seguidas para confirmar un cambio
  uint32_t reintentoAlertaMs;     // reenvío si el PC no recibió la alerta
};

class Controlador {
 public:
  static const uint8_t REGISTRO = 48;   // raciones recordadas por clase (ventana 24 h)

  Controlador(Hardware& hw, const Parametros& p);
  void iniciar();
  void actualizar();               // llamar periódicamente desde loop()
  bool borrarErrores();            // comando serie RESET, botón BOOT o panel. true si había error
  // Pedido de dispensación manual (panel web, botón o serie). Se valida aquí y,
  // si se acepta, la dosis se ejecuta en el siguiente actualizar().
  Solicitud solicitarDispensacion(uint8_t porciones, Origen origen);

  Estado estado() const { return estado_; }
  int ultimaClase() const { return ultimaClase_; }
  float ultimaConfianza() const { return ultimaConfianza_; }
  const char* ultimoMotivo() const { return ultimoMotivo_; }
  float ultimaDistancia() const { return ultimaDistancia_; }
  uint32_t racionesTotales(int clase) const { return clase >= 1 && clase < N_CLASES ? totales_[clase] : 0; }
  uint32_t intentosDosis() const { return intentosDosis_; }       // dosis ejecutadas (con cualquier resultado)
  uint16_t racionesUltimas24hTotal() const;
  bool huboDosis() const { return intentosDosis_ > 0; }
  uint32_t msDesdeUltimaDosis() const { return hw_.ahoraMs() - tUltimaDosis_; }
  ResultadoDosis ultimoResultado() const { return ultimoResultado_; }
  Origen ultimoOrigen() const { return ultimoOrigen_; }
  uint8_t ultimasPorciones() const { return ultimasPorciones_; }
  bool dosisPendiente() const { return porcionesPendientes_ > 0; }
  bool modoAutomatico() const { return p_.usarDeteccionAutomatica; }
  uint8_t racionesUltimas24h(int clase) const;
  uint32_t cooldownRestanteMs() const;
  float nivelTolva() const { return nivelPct_; }
  Alerta alertaNivel() const { return alertaNivel_; }
  bool alertaPendiente() const { return pendiente_ != Alerta::NINGUNA; }

 private:
  void cambiarA(Estado nuevo, const char* motivo = nullptr);
  bool esErrorBloqueante() const;
  bool mascotaPresente(float d) const;
  void registrarRacion(int clase);
  Solicitud verificarRacion(int clase, char* porque, int n) const;
  Solicitud evaluarSolicitud(uint8_t porciones);
  void volverAEsperar(const char* motivo);
  void logf(const char* fmt, ...);
  void vigilarNivel(uint32_t ahora);
  void emitir(Alerta a);

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
  uint32_t registro_[N_CLASES][REGISTRO] = {};
  uint8_t nRegistro_[N_CLASES] = {};
  uint8_t posRegistro_[N_CLASES] = {};
  uint32_t totales_[N_CLASES] = {};

  // Dispensación manual y registro de la última dosis
  uint8_t porcionesPendientes_ = 0;
  Origen origenPendiente_ = Origen::NINGUNO;
  uint8_t ciclosManual_ = 0;
  uint32_t intentosDosis_ = 0;
  uint32_t tUltimaDosis_ = 0;
  ResultadoDosis ultimoResultado_ = ResultadoDosis::NINGUNA;
  Origen ultimoOrigen_ = Origen::NINGUNO;
  uint8_t ultimasPorciones_ = 0;
  uint32_t tReintentoWifi_ = 0;

  // Nivel de la tolva
  float nivelPct_ = -1.0f;
  bool nivelMedido_ = false;
  uint32_t tNivel_ = 0;
  uint8_t bajas_ = 0, altas_ = 0, vacias_ = 0, noVacias_ = 0, invalidas_ = 0;
  Alerta alertaNivel_ = Alerta::NINGUNA;   // COMIDA_BAJA / COMIDA_AGOTADA activas
  bool avisoSinLectura_ = false;
  Alerta pendiente_ = Alerta::NINGUNA;      // última alerta no entregada
  uint32_t tPendiente_ = 0;
};
