// =============================================================================
//  Controlador.cpp  -  Máquina de estados (ver Documentation/architecture)
// =============================================================================
#include "Controlador.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static const uint32_t MS_24H = 86400000UL;

const char* nombreEstado(Estado e) {
  switch (e) {
    case Estado::ESPERANDO:           return "ESPERANDO";
    case Estado::DETECTADO:           return "DETECTADO";
    case Estado::CAPTURANDO:          return "CAPTURANDO";
    case Estado::PROCESANDO:          return "PROCESANDO";
    case Estado::CLASIFICADO:         return "CLASIFICADO";
    case Estado::DOSIFICANDO:         return "DOSIFICANDO";
    case Estado::FINALIZADO:          return "FINALIZADO";
    case Estado::ERROR_WIFI:          return "ERROR_WIFI";
    case Estado::ERROR_CAMARA:        return "ERROR_CAMARA";
    case Estado::ERROR_CLASIFICACION: return "ERROR_CLASIFICACION";
    case Estado::ERROR_SERVO:         return "ERROR_SERVO";
    case Estado::ERROR_ALIMENTACION:  return "ERROR_ALIMENTACION";
    case Estado::ERROR_MECANISMO:     return "ERROR_MECANISMO";
  }
  return "?";
}

Controlador::Controlador(Hardware& hw, const Parametros& p) : hw_(hw), p_(p) {}

void Controlador::logf(const char* fmt, ...) {
  char buf[160];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buf, sizeof(buf), fmt, args);
  va_end(args);
  hw_.log(buf);
}

void Controlador::iniciar() {
  tEstado_ = hw_.ahoraMs();
  zonaArmada_ = true;
  if (!hw_.wifiConectado()) {
    cambiarA(Estado::ERROR_WIFI, "sin Wi-Fi al iniciar");
  } else {
    cambiarA(Estado::ESPERANDO, "sistema iniciado");
  }
}

void Controlador::cambiarA(Estado nuevo, const char* motivo) {
  logf("[%s] -> [%s]%s%s", nombreEstado(estado_), nombreEstado(nuevo),
       motivo ? " : " : "", motivo ? motivo : "");
  estado_ = nuevo;
  tEstado_ = hw_.ahoraMs();
  tUltimoReintento_ = tEstado_;
}

bool Controlador::esErrorBloqueante() const {
  // Requieren intervención humana (revisar mecánica / cableado del servo)
  return estado_ == Estado::ERROR_SERVO || estado_ == Estado::ERROR_MECANISMO;
}

bool Controlador::mascotaPresente(float d) const {
  return d >= p_.distMinCm && d <= p_.distDeteccionCm;
}

void Controlador::volverAEsperar(const char* motivo) {
  // La detección queda desarmada hasta que la zona esté libre ZONA_LIBRE_MS:
  // evita que una mascota que se queda delante dispare ciclos en bucle.
  zonaArmada_ = false;
  contandoZonaLibre_ = false;
  lecturasPresente_ = 0;
  cambiarA(Estado::ESPERANDO, motivo);
}

void Controlador::borrarErrores() {
  if (estado_ >= Estado::ERROR_WIFI) {
    volverAEsperar("errores borrados manualmente");
  }
}

// ----------------------------------------------------------------------------
// Registro de raciones (ventana móvil de 24 h, sin reloj de tiempo real)
// ----------------------------------------------------------------------------
void Controlador::registrarRacion(int clase) {
  uint32_t ahora = hw_.ahoraMs();
  registro_[clase][posRegistro_[clase]] = ahora;
  posRegistro_[clase] = (posRegistro_[clase] + 1) % REGISTRO;
  if (nRegistro_[clase] < REGISTRO) nRegistro_[clase]++;
  totales_[clase]++;
  huboRacion_ = true;
  tUltimaRacion_ = ahora;
}

uint8_t Controlador::racionesUltimas24h(int clase) const {
  if (clase < 1 || clase > 2) return 0;
  uint32_t ahora = hw_.ahoraMs();
  uint8_t n = 0;
  for (uint8_t i = 0; i < nRegistro_[clase]; i++) {
    if (ahora - registro_[clase][i] < MS_24H) n++;  // resta sin signo: tolera desborde de millis()
  }
  return n;
}

uint32_t Controlador::cooldownRestanteMs() const {
  if (!huboRacion_) return 0;
  uint32_t trans = hw_.ahoraMs() - tUltimaRacion_;
  return trans >= p_.cooldownGlobalMs ? 0 : p_.cooldownGlobalMs - trans;
}

bool Controlador::racionPermitida(int clase, char* porque, int n) {
  if (!p_.habilitada[clase]) {
    snprintf(porque, n, "clase deshabilitada");
    return false;
  }
  if (nRegistro_[clase] > 0) {
    uint8_t ult = (posRegistro_[clase] + REGISTRO - 1) % REGISTRO;
    uint32_t trans = hw_.ahoraMs() - registro_[clase][ult];
    if (trans < p_.cooldownClaseMs[clase]) {
      snprintf(porque, n, "cooldown de clase activo (%lu s restantes)",
               (unsigned long)((p_.cooldownClaseMs[clase] - trans) / 1000));
      return false;
    }
  }
  if (racionesUltimas24h(clase) >= p_.maxRacionesDia[clase]) {
    snprintf(porque, n, "limite diario alcanzado");
    return false;
  }
  return true;
}

// ----------------------------------------------------------------------------
// Lazo principal
// ----------------------------------------------------------------------------
void Controlador::actualizar() {
  const uint32_t ahora = hw_.ahoraMs();

  // --- Botón de reset de errores (cualquier estado de error) ---
  if (estado_ >= Estado::ERROR_WIFI && hw_.botonResetPulsado()) {
    borrarErrores();
    return;
  }

  // --- Supervisión de energía (prioridad sobre todo salvo errores bloqueantes) ---
  if (p_.usarMonitorBateria && !esErrorBloqueante() && estado_ != Estado::ERROR_ALIMENTACION) {
    float vbat = hw_.voltajeBateria();
    if (vbat < p_.vbatMin) {
      logf("Bateria baja: %.2f V < %.2f V", vbat, p_.vbatMin);
      cambiarA(Estado::ERROR_ALIMENTACION, "bateria insuficiente: no se dispensa");
      return;
    }
  }

  // --- Supervisión de Wi-Fi ---
  if (!esErrorBloqueante() && estado_ != Estado::ERROR_ALIMENTACION &&
      estado_ != Estado::ERROR_WIFI && !hw_.wifiConectado()) {
    cambiarA(Estado::ERROR_WIFI, "conexion perdida");
    return;
  }

  switch (estado_) {
    // ------------------------------------------------------------------
    case Estado::ESPERANDO: {
      float d = hw_.distanciaCm();
      ultimaDistancia_ = d;
      bool presente = mascotaPresente(d);
      bool libre = (d < 0) || (d > p_.distLibreCm);

      if (libre) {
        if (!contandoZonaLibre_) {
          contandoZonaLibre_ = true;
          tZonaLibre_ = ahora;
        } else if (!zonaArmada_ && ahora - tZonaLibre_ >= p_.zonaLibreMs) {
          zonaArmada_ = true;
          logf("Zona libre: deteccion rearmada");
        }
      } else {
        contandoZonaLibre_ = false;
      }

      if (presente && zonaArmada_ && cooldownRestanteMs() == 0) {
        if (++lecturasPresente_ >= p_.lecturasConfirmacion) {
          lecturasPresente_ = 0;
          char m[48];
          snprintf(m, sizeof(m), "objeto a %.1f cm", d);
          cambiarA(Estado::DETECTADO, m);
        }
      } else {
        lecturasPresente_ = 0;
      }
      break;
    }

    // ------------------------------------------------------------------
    case Estado::DETECTADO:
      intentos_ = 0;
      fallosCamara_ = 0;
      cambiarA(Estado::CAPTURANDO, "solicitando captura");
      break;

    // ------------------------------------------------------------------
    case Estado::CAPTURANDO:
      if (hw_.camaraDisponible()) {
        fallosCamara_ = 0;
        cambiarA(Estado::PROCESANDO, "camara lista, clasificando en PC");
      } else if (++fallosCamara_ >= 2) {
        cambiarA(Estado::ERROR_CAMARA, "ESP32-CAM no responde");
      }
      break;

    // ------------------------------------------------------------------
    case Estado::PROCESANDO: {
      RespuestaClasificacion r = hw_.clasificar((int)(ultimaDistancia_ + 0.5f));
      strncpy(ultimoMotivo_, r.motivo, sizeof(ultimoMotivo_) - 1);
      ultimoMotivo_[sizeof(ultimoMotivo_) - 1] = '\0';
      if (r.tipo == TipoRespuesta::ERROR_CAMARA) {
        cambiarA(Estado::ERROR_CAMARA, "el PC no pudo obtener la imagen");
      } else if (r.tipo == TipoRespuesta::ERROR_SERVIDOR) {
        cambiarA(Estado::ERROR_CLASIFICACION, "PC sin respuesta o respuesta invalida");
      } else {
        ultimaClase_ = r.clase;
        ultimaConfianza_ = r.confianza;
        char m[64];
        snprintf(m, sizeof(m), "clase=%d conf=%.2f motivo=%s", r.clase, r.confianza, r.motivo);
        cambiarA(Estado::CLASIFICADO, m);
      }
      break;
    }

    // ------------------------------------------------------------------
    case Estado::CLASIFICADO: {
      const int c = ultimaClase_;
      if (c != CLASE_PERRO && c != CLASE_GATO) {
        // Resultado no válido: NUNCA se dispensa. Se reintenta si sigue ahí.
        if (intentos_ + 1 >= p_.maxIntentosClasificacion) {
          volverAEsperar("clasificacion no valida: maximo de intentos");
          break;
        }
        if (ahora - tEstado_ < p_.reintentoClasificacionMs) break;  // esperar
        float d = hw_.distanciaCm();
        ultimaDistancia_ = d;
        if (!mascotaPresente(d)) {
          volverAEsperar("clasificacion no valida y la mascota se fue");
        } else {
          intentos_++;
          cambiarA(Estado::CAPTURANDO, "reintento de clasificacion");
        }
        break;
      }

      char porque[64];
      if (!racionPermitida(c, porque, sizeof(porque))) {
        volverAEsperar(porque);
        break;
      }
      float d = hw_.distanciaCm();
      ultimaDistancia_ = d;
      if (!mascotaPresente(d)) {
        volverAEsperar("la mascota abandono el area: no se dispensa");
        break;
      }
      if (p_.usarMonitorServo && hw_.voltajeServo() < p_.vservoMin) {
        cambiarA(Estado::ERROR_SERVO, "riel de alimentacion del servo ausente o bajo");
        break;
      }
      cambiarA(Estado::DOSIFICANDO, c == CLASE_PERRO ? "racion PERRO" : "racion GATO");
      break;
    }

    // ------------------------------------------------------------------
    case Estado::DOSIFICANDO: {
      uint8_t ciclos = p_.ciclos[ultimaClase_];
      if (ciclos > p_.maxCiclosPorRacion) ciclos = p_.maxCiclosPorRacion;
      ResultadoDosis r = hw_.dosificar(ciclos);
      if (r == ResultadoDosis::OK) {
        registrarRacion(ultimaClase_);
        cambiarA(Estado::FINALIZADO, "racion entregada");
      } else if (r == ResultadoDosis::SIN_ALIMENTACION_SERVO) {
        cambiarA(Estado::ERROR_SERVO, "el servo perdio alimentacion");
      } else {
        // Por seguridad también se cuenta: pudo haber caído alimento.
        registrarRacion(ultimaClase_);
        cambiarA(Estado::ERROR_MECANISMO, "posible atasco del dosificador");
      }
      break;
    }

    // ------------------------------------------------------------------
    case Estado::FINALIZADO:
      volverAEsperar("bloqueo temporal activo");
      break;

    // ------------------------------------------------------------------
    case Estado::ERROR_WIFI:
      if (hw_.wifiConectado()) {
        volverAEsperar("Wi-Fi recuperado");
      } else if (ahora - tEstado_ >= p_.wifiReinicioMs) {
        hw_.log("Sin Wi-Fi demasiado tiempo: reiniciando");
        hw_.reiniciar();
      } else if (ahora - tUltimoReintento_ >= p_.wifiReintentoMs) {
        tUltimoReintento_ = ahora;
        hw_.reconectarWifi();
      }
      break;

    case Estado::ERROR_CAMARA:
      if (ahora - tUltimoReintento_ >= p_.errorReintentoMs) {
        tUltimoReintento_ = ahora;
        if (hw_.camaraDisponible()) volverAEsperar("camara recuperada");
      }
      break;

    case Estado::ERROR_CLASIFICACION:
      if (ahora - tUltimoReintento_ >= p_.errorReintentoMs) {
        tUltimoReintento_ = ahora;
        if (hw_.servidorDisponible()) volverAEsperar("servidor de vision recuperado");
      }
      break;

    case Estado::ERROR_ALIMENTACION:
      if (!p_.usarMonitorBateria || hw_.voltajeBateria() >= p_.vbatMin + p_.vbatHisteresis) {
        volverAEsperar("bateria recuperada");
      }
      break;

    case Estado::ERROR_SERVO:
    case Estado::ERROR_MECANISMO:
      // Bloqueantes: solo salen con borrarErrores() (botón BOOT o comando RESET)
      break;
  }
}
