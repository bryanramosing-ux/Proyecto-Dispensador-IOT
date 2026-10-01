"""
Alertas del dispensador (nivel de alimento en la tolva).

El ESP32 envía  POST /alerta  {"tipo": "COMIDA_BAJA", "nivel": 18}  y este módulo:
  * guarda las últimas alertas (se ven en el panel web http://PC:8000/),
  * las escribe en el registro de la consola,
  * y, si se configuró NTFY_TOPICO, las reenvía al celular por ntfy.sh
    (en segundo plano: si no hay Internet el dispensador sigue funcionando).
"""
import collections
import logging
import threading
import unicodedata
import urllib.request
from datetime import datetime

log = logging.getLogger("alertas")

MENSAJES = {
    "COMIDA_BAJA": ("Comida baja", "high",
                    "La comida del dispensador se está acabando (nivel ~{nivel:.0f} %). Recargue la tolva."),
    "COMIDA_AGOTADA": ("Tolva vacía", "urgent",
                       "La tolva está vacía: el dispensador no entregará raciones hasta recargarla."),
    "COMIDA_REPUESTA": ("Tolva recargada", "default",
                        "Tolva recargada (nivel ~{nivel:.0f} %)."),
    "SENSOR_NIVEL_SIN_LECTURA": ("Sensor de nivel", "high",
                                 "El sensor de nivel de la tolva no responde: revise el cable de la tapa."),
}


def sin_acentos(texto):
    """Las cabeceras HTTP son ASCII/latin-1: el título viaja sin tildes (el cuerpo va en UTF-8)."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


class GestorAlertas:
    def __init__(self, cfg, enviar=None):
        self.cfg = cfg
        self.historial = collections.deque(maxlen=50)
        self.candado = threading.Lock()
        self._enviar = enviar or self._enviar_ntfy

    def registrar(self, tipo, nivel):
        """Devuelve el dict de la alerta o lanza ValueError si el tipo no existe."""
        if tipo not in MENSAJES:
            raise ValueError(f"tipo de alerta desconocido: {tipo}")
        titulo, prioridad, plantilla = MENSAJES[tipo]
        nivel = float(nivel) if nivel is not None else -1.0
        alerta = {"hora": datetime.now().isoformat(timespec="seconds"), "tipo": tipo, "nivel": nivel,
                  "titulo": titulo, "mensaje": plantilla.format(nivel=max(nivel, 0))}
        with self.candado:
            self.historial.appendleft(alerta)
        log.warning("ALERTA %s: %s", tipo, alerta["mensaje"])
        if self.cfg.NTFY_TOPICO:
            threading.Thread(target=self._enviar, args=(alerta, prioridad), daemon=True).start()
        return alerta

    def recientes(self, n=10):
        with self.candado:
            return list(self.historial)[:n]

    def _enviar_ntfy(self, alerta, prioridad):
        url = self.cfg.NTFY_SERVIDOR.rstrip("/") + "/" + self.cfg.NTFY_TOPICO
        pedido = urllib.request.Request(url, data=alerta["mensaje"].encode("utf-8"), method="POST",
                                        headers={"Title": sin_acentos(alerta["titulo"]),
                                                 "Priority": prioridad, "Tags": "dog,cat"})
        try:
            with urllib.request.urlopen(pedido, timeout=5):
                log.info("Alerta enviada al celular (ntfy)")
        except Exception as e:  # noqa: BLE001 - sin Internet no debe caerse nada
            log.warning("No se pudo enviar la alerta a ntfy: %s", e)
