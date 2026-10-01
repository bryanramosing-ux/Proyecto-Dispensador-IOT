// Pruebas de la máquina de estados en el PC (sin ESP32).
//   make -C ESP32/test_host
// Simula el tiempo, el HC-SR04, la red, el PC, la batería y el servo.
#include <cassert>
#include <cstdio>
#include <cstring>
#include <deque>
#include <string>

#include "../Dispensador_ESP32/Controlador.h"

struct FakeHW : Hardware {
  uint32_t t = 0;
  float dist = -1;
  bool wifi = true, cam = true, pc = true, boton = false;
  float vbat = 7.6f, vservo = 6.0f;
  std::deque<RespuestaClasificacion> respuestas;
  ResultadoDosis resultadoDosis = ResultadoDosis::OK;
  int dosis = 0, ciclosTotales = 0, reinicios = 0, clasificaciones = 0;
  bool verbose = false;

  uint32_t ahoraMs() override { return t; }
  float distanciaCm() override { return dist; }
  bool wifiConectado() override { return wifi; }
  void reconectarWifi() override {}
  bool camaraDisponible() override { return cam; }
  bool servidorDisponible() override { return pc; }
  RespuestaClasificacion clasificar(int) override {
    clasificaciones++;
    if (respuestas.empty()) return RespuestaClasificacion{};  // ERROR_SERVIDOR
    RespuestaClasificacion r = respuestas.front();
    respuestas.pop_front();
    return r;
  }
  float voltajeBateria() override { return vbat; }
  float voltajeServo() override { return vservo; }
  ResultadoDosis dosificar(uint8_t c) override {
    dosis++;
    ciclosTotales += c;
    return resultadoDosis;
  }
  bool botonResetPulsado() override { return boton; }
  void reiniciar() override { reinicios++; }
  void log(const char* m) override {
    if (verbose) printf("  %8u ms  %s\n", (unsigned)t, m);
  }
};

static RespuestaClasificacion resp(int clase, float conf = 0.9f, const char* motivo = "OK") {
  RespuestaClasificacion r;
  r.tipo = TipoRespuesta::OK;
  r.clase = clase;
  r.confianza = conf;
  strncpy(r.motivo, motivo, sizeof(r.motivo) - 1);
  return r;
}

static Parametros params() {
  Parametros p{};
  p.distMinCm = 3;
  p.distDeteccionCm = 35;
  p.distLibreCm = 50;
  p.lecturasConfirmacion = 3;
  p.zonaLibreMs = 3000;
  p.maxIntentosClasificacion = 3;
  p.reintentoClasificacionMs = 4000;
  p.ciclos[1] = 3;
  p.ciclos[2] = 1;
  p.habilitada[1] = p.habilitada[2] = true;
  p.cooldownClaseMs[1] = p.cooldownClaseMs[2] = 60000;
  p.maxRacionesDia[1] = p.maxRacionesDia[2] = 4;
  p.maxCiclosPorRacion = 10;
  p.cooldownGlobalMs = 30000;
  p.usarMonitorBateria = true;
  p.vbatMin = 6.8f;
  p.vbatHisteresis = 0.2f;
  p.usarMonitorServo = true;
  p.vservoMin = 4.6f;
  p.wifiReintentoMs = 5000;
  p.wifiReinicioMs = 300000;
  p.errorReintentoMs = 30000;
  return p;
}

static void correr(Controlador& c, FakeHW& hw, uint32_t ms) {
  for (uint32_t i = 0; i < ms; i += 50) {
    c.actualizar();
    hw.t += 50;
  }
}

static int fallos = 0;
#define CHECK(cond)                                                   \
  do {                                                                \
    if (!(cond)) {                                                    \
      printf("    FALLO linea %d: %s\n", __LINE__, #cond);            \
      fallos++;                                                       \
    }                                                                 \
  } while (0)

static void prueba(const char* nombre) { printf("- %s\n", nombre); }

int main() {
  {
    prueba("Perro detectado -> clasificado 1 -> dispensa 3 ciclos -> ESPERANDO");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.dist = 20;
    correr(c, hw, 2000);
    CHECK(hw.dosis == 1 && hw.ciclosTotales == 3);
    CHECK(c.estado() == Estado::ESPERANDO);
    CHECK(c.racionesTotales(CLASE_PERRO) == 1);
    CHECK(c.cooldownRestanteMs() > 0);
  }
  {
    prueba("Mascota demasiado lejos: no se activa nada");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.dist = 42;
    correr(c, hw, 10000);
    CHECK(hw.clasificaciones == 0 && hw.dosis == 0);
  }
  {
    prueba("Lectura menor a DIST_MIN (sensor tapado) no dispara");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.dist = 1.5f;
    correr(c, hw, 5000);
    CHECK(hw.clasificaciones == 0);
  }
  {
    prueba("Gato: 1 ciclo; repetición inmediata bloqueada (cooldown + zona libre)");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.respuestas.push_back(resp(CLASE_GATO));
    hw.respuestas.push_back(resp(CLASE_GATO));
    hw.dist = 25;
    correr(c, hw, 2000);
    CHECK(hw.dosis == 1 && hw.ciclosTotales == 1);
    correr(c, hw, 120000);  // el gato se queda delante 2 minutos
    CHECK(hw.dosis == 1);   // no se rearma sin zona libre
    hw.dist = -1;
    correr(c, hw, 4000);    // se va
    hw.dist = 25;
    correr(c, hw, 2000);    // vuelve (cooldown de clase de 60 s ya pasó)
    CHECK(hw.dosis == 2);
  }
  {
    prueba("Cooldown global impide racion aunque la zona se libere");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.respuestas.push_back(resp(CLASE_GATO));
    hw.dist = 20;
    correr(c, hw, 2000);
    hw.dist = -1;
    correr(c, hw, 4000);
    hw.dist = 20;
    correr(c, hw, 5000);  // 11 s después de la primera: cooldown global 30 s
    CHECK(hw.dosis == 1 && hw.clasificaciones == 1);
    correr(c, hw, 25000);
    CHECK(hw.dosis == 2);
  }
  {
    prueba("Clasificacion incierta (0) x3: NO dispensa y desiste");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    for (int i = 0; i < 5; i++) hw.respuestas.push_back(resp(0, 0.4f, "BAJA_CONFIANZA"));
    hw.dist = 20;
    correr(c, hw, 30000);
    CHECK(hw.dosis == 0);
    CHECK(hw.clasificaciones == 3);
    CHECK(c.estado() == Estado::ESPERANDO);
  }
  {
    prueba("Imagen invalida y luego perro: el reintento si dispensa");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.respuestas.push_back(resp(0, 0, "IMAGEN_BORROSA"));
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.dist = 20;
    correr(c, hw, 8000);
    CHECK(hw.clasificaciones == 2 && hw.dosis == 1);
  }
  {
    prueba("La mascota abandona el area antes de dispensar: no dispensa");
    struct HWSeVa : FakeHW {
      RespuestaClasificacion clasificar(int d) override {
        dist = -1;  // se va mientras el PC clasifica
        return FakeHW::clasificar(d);
      }
    } hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.dist = 20;
    correr(c, hw, 3000);
    CHECK(hw.clasificaciones == 1 && hw.dosis == 0);
  }
  {
    prueba("Wi-Fi perdido -> ERROR_WIFI -> recuperado -> ESPERANDO");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.wifi = false;
    correr(c, hw, 1000);
    CHECK(c.estado() == Estado::ERROR_WIFI);
    hw.dist = 20;
    hw.respuestas.push_back(resp(CLASE_PERRO));
    correr(c, hw, 5000);
    CHECK(hw.dosis == 0);
    hw.wifi = true;
    correr(c, hw, 200);
    CHECK(c.estado() == Estado::ESPERANDO);
  }
  {
    prueba("Wi-Fi caido 5 min -> reinicio del ESP32");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.wifi = false;
    correr(c, hw, 301000);
    CHECK(hw.reinicios >= 1);
  }
  {
    prueba("ESP32-CAM no responde -> ERROR_CAMARA -> se recupera");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.cam = false;
    hw.dist = 20;
    correr(c, hw, 1000);
    CHECK(c.estado() == Estado::ERROR_CAMARA);
    hw.cam = true;
    correr(c, hw, 31000);
    CHECK(c.estado() == Estado::ESPERANDO);
    CHECK(hw.dosis == 0);
  }
  {
    prueba("PC informa camara caida (502) -> ERROR_CAMARA");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    RespuestaClasificacion r;
    r.tipo = TipoRespuesta::ERROR_CAMARA;
    hw.respuestas.push_back(r);
    hw.dist = 20;
    correr(c, hw, 1000);
    CHECK(c.estado() == Estado::ERROR_CAMARA);
  }
  {
    prueba("PC no responde -> ERROR_CLASIFICACION -> recuperado");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.dist = 20;  // sin respuestas encoladas = timeout
    hw.pc = false;
    correr(c, hw, 1000);
    CHECK(c.estado() == Estado::ERROR_CLASIFICACION);
    hw.pc = true;
    correr(c, hw, 31000);
    CHECK(c.estado() == Estado::ESPERANDO && hw.dosis == 0);
  }
  {
    prueba("Bateria baja -> ERROR_ALIMENTACION (con histeresis)");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.vbat = 6.6f;
    hw.dist = 20;
    hw.respuestas.push_back(resp(CLASE_PERRO));
    correr(c, hw, 2000);
    CHECK(c.estado() == Estado::ERROR_ALIMENTACION && hw.dosis == 0);
    hw.vbat = 6.9f;  // por encima del mínimo pero dentro de la histéresis
    correr(c, hw, 1000);
    CHECK(c.estado() == Estado::ERROR_ALIMENTACION);
    hw.vbat = 7.2f;
    correr(c, hw, 200);
    CHECK(c.estado() == Estado::ESPERANDO);
  }
  {
    prueba("Riel del servo ausente -> ERROR_SERVO bloqueante; boton lo borra");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.vservo = 0.2f;
    hw.dist = 20;
    hw.respuestas.push_back(resp(CLASE_PERRO));
    correr(c, hw, 2000);
    CHECK(c.estado() == Estado::ERROR_SERVO && hw.dosis == 0);
    hw.vservo = 6.0f;
    correr(c, hw, 60000);
    CHECK(c.estado() == Estado::ERROR_SERVO);  // no se borra solo
    hw.boton = true;
    correr(c, hw, 100);
    hw.boton = false;
    CHECK(c.estado() == Estado::ESPERANDO);
  }
  {
    prueba("Atasco durante la dosis -> ERROR_MECANISMO bloqueante");
    FakeHW hw;
    Controlador c(hw, params());
    c.iniciar();
    hw.resultadoDosis = ResultadoDosis::ATASCO;
    hw.dist = 20;
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.respuestas.push_back(resp(CLASE_PERRO));
    correr(c, hw, 2000);
    CHECK(c.estado() == Estado::ERROR_MECANISMO);
    correr(c, hw, 120000);
    CHECK(hw.dosis == 1);  // no vuelve a intentar sin intervención
  }
  {
    prueba("Limite diario por clase");
    FakeHW hw;
    Parametros p = params();
    p.cooldownGlobalMs = 0;
    p.cooldownClaseMs[1] = 0;
    p.maxRacionesDia[1] = 2;
    Controlador c(hw, p);
    c.iniciar();
    for (int i = 0; i < 4; i++) {
      hw.respuestas.push_back(resp(CLASE_PERRO));
      hw.dist = 20;
      correr(c, hw, 2000);
      hw.dist = -1;
      correr(c, hw, 4000);
    }
    CHECK(hw.dosis == 2);
    CHECK(c.racionesUltimas24h(CLASE_PERRO) == 2);
    hw.t += 86400000UL;  // pasan 24 h
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.dist = 20;
    correr(c, hw, 2000);
    CHECK(hw.dosis == 3);
  }
  {
    prueba("Clase deshabilitada (solo perros): gato no recibe");
    FakeHW hw;
    Parametros p = params();
    p.habilitada[2] = false;
    Controlador c(hw, p);
    c.iniciar();
    hw.respuestas.push_back(resp(CLASE_GATO));
    hw.dist = 20;
    correr(c, hw, 3000);
    CHECK(hw.dosis == 0 && hw.clasificaciones == 1);
  }
  {
    prueba("Desborde de millis() (49,7 dias) no rompe cooldown");
    FakeHW hw;
    hw.t = 0xFFFFFFFFUL - 1000;
    Controlador c(hw, params());
    c.iniciar();
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.dist = 20;
    correr(c, hw, 2000);
    CHECK(hw.dosis == 1);
    hw.dist = -1;
    correr(c, hw, 4000);
    hw.dist = 20;
    correr(c, hw, 3000);
    CHECK(hw.dosis == 1 && hw.clasificaciones == 1);  // cooldown global (30 s) activo pese al desborde
    correr(c, hw, 60000);
    // A los 30 s se clasifica de nuevo, pero el cooldown de CLASE (60 s) lo impide
    // y la detección queda desarmada hasta que la mascota se vaya.
    CHECK(hw.dosis == 1 && hw.clasificaciones == 2);
    hw.respuestas.push_back(resp(CLASE_PERRO));
    hw.dist = -1;
    correr(c, hw, 4000);
    hw.dist = 20;
    correr(c, hw, 2000);
    CHECK(hw.dosis == 2);
  }

  printf(fallos ? "\nRESULTADO: %d FALLO(S)\n" : "\nRESULTADO: todas las pruebas OK\n", fallos);
  return fallos ? 1 : 0;
}
