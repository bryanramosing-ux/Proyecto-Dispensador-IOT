"""Lectura y validación de los GPIO ACTIVOS del montaje USB-C."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CONFIG = RAIZ / 'ESP32/Dispensador_ESP32/config.h'


def leer(ruta=CONFIG):
    texto = Path(ruta).read_text(encoding='utf-8')
    pines = {k: int(v) for k, v in re.findall(r'#define\s+(PIN_\w+)\s+(\d+)', texto)}
    flags = {k: int(v) for k, v in re.findall(r'#define\s+((?:USAR_|ALIMENTACION_)\w+)\s+([01])\b', texto)}
    return pines, flags


def validar(p, flags):
    if flags.get('USAR_MONITOR_BATERIA', 0):
        raise ValueError('Montaje USB-C sin batería: USAR_MONITOR_BATERIA debe ser 0')
    activos = ['PIN_SERVO']
    if flags.get('USAR_SENSOR_NIVEL', 0):
        activos += ['PIN_TRIG_NIVEL', 'PIN_ECHO_NIVEL']
    if flags.get('USAR_DETECCION_AUTOMATICA', 0):
        activos += ['PIN_TRIG', 'PIN_ECHO']
    if flags.get('USAR_MONITOR_SERVO', 0):
        activos += ['PIN_VSERVO']
    faltan = set(activos) - p.keys()
    if faltan:
        raise ValueError(f'Faltan GPIO activos: {sorted(faltan)}')
    if len({p[k] for k in activos}) != len(activos):
        raise ValueError('Dos funciones activas comparten GPIO')
    prohibidos = {0, 2, 5, 6, 7, 8, 9, 10, 11, 12, 15, 20, 24, 28, 29, 30, 31}
    for k in activos:
        if p[k] in prohibidos or not 0 <= p[k] <= 39:
            raise ValueError(f'{k}: GPIO{p[k]} no permitido para este cableado')
        if ('TRIG' in k or k == 'PIN_SERVO') and p[k] >= 34:
            raise ValueError(f'{k}: GPIO{p[k]} es solo entrada')
    if flags.get('USAR_MONITOR_SERVO') and p['PIN_VSERVO'] not in {32, 33, 34, 35, 36, 39}:
        raise ValueError('El monitor de riel debe usar ADC1 (compatible con Wi-Fi)')
    return activos
