import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from perfil_electrico import leer, validar


class TestPerfil(unittest.TestCase):
    def test_montaje_usbc_no_requiere_pin_de_panel(self):
        p, f = leer()
        self.assertNotIn('PIN_VPANEL', p)
        self.assertEqual(set(validar(p, f)), {'PIN_SERVO', 'PIN_TRIG_NIVEL', 'PIN_ECHO_NIVEL'})

    def test_conflicto_gpio_activo_se_rechaza(self):
        p, f = leer(); p['PIN_SERVO'] = p['PIN_TRIG_NIVEL']
        with self.assertRaisesRegex(ValueError, 'comparten'):
            validar(p, f)

    def test_salida_no_puede_usar_gpio_solo_entrada(self):
        p, f = leer(); p['PIN_TRIG_NIVEL'] = 34
        with self.assertRaisesRegex(ValueError, 'solo entrada'):
            validar(p, f)

    def test_pin_activo_ausente_se_rechaza(self):
        p, f = leer(); del p['PIN_ECHO_NIVEL']
        with self.assertRaisesRegex(ValueError, 'Faltan'):
            validar(p, f)

    def test_adc2_no_sirve_con_wifi(self):
        p, f = leer(); f['USAR_MONITOR_SERVO'] = 1; p['PIN_VSERVO'] = 27
        with self.assertRaisesRegex(ValueError, 'ADC1'):
            validar(p, f)

    def test_presencia_opcional_se_incluye_si_se_activa(self):
        p, f = leer(); f['USAR_DETECCION_AUTOMATICA'] = 1
        self.assertIn('PIN_ECHO', validar(p, f))
