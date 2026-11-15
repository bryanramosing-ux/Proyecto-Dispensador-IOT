import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from clasificador import Resultado
from iniciar import cargar_entorno
from servidor_vision import ServicioVision


class TestOperacion(unittest.TestCase):
    def cfg(self, carpeta):
        cfg = types.SimpleNamespace(**{n: getattr(config, n) for n in dir(config) if n.isupper()})
        cfg.DIR_CAPTURAS = carpeta
        cfg.MAX_CAPTURAS = 2
        return cfg

    def test_retencion_acotada_y_nombres_unicos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            servicio = ServicioVision(self.cfg(carpeta), clasificador=object())
            for i in range(5):
                servicio._guardar([str(i).encode()], Resultado(1, "OK"))
            archivos = sorted(Path(carpeta).glob("*/*.jpg"))
            self.assertEqual(len(archivos), 2)
            self.assertEqual([p.read_bytes() for p in archivos], [b"3", b"4"])

    def test_fallo_de_disco_no_anula_clasificacion(self):
        with tempfile.TemporaryDirectory() as carpeta:
            servicio = ServicioVision(self.cfg(carpeta), clasificador=object())
            with patch("servidor_vision.descargar_foto", return_value=b""), \
                 patch("servidor_vision.clasificar_imagenes",
                       return_value=Resultado(1, "OK", .9, .9, .01, 1)), \
                 patch.object(servicio, "_guardar", side_effect=OSError("disco lleno")), \
                 self.assertLogs("vision", level="ERROR"):
                codigo, datos = servicio.clasificar()
            self.assertEqual((codigo, datos["clase"]), (200, 1))

    def test_entorno_no_ejecuta_codigo_y_respeta_variables_existentes(self):
        with tempfile.TemporaryDirectory() as carpeta, patch.dict(os.environ, {"DISPENSADOR_PUERTO": "9000"}):
            archivo = Path(carpeta) / "dispensador.env"
            archivo.write_text("# configuración\nDISPENSADOR_PUERTO=8000\nDISPENSADOR_NTFY_TOPICO='tema'\n")
            cargar_entorno(archivo)
            self.assertEqual(os.environ["DISPENSADOR_PUERTO"], "9000")
            self.assertEqual(os.environ["DISPENSADOR_NTFY_TOPICO"], "tema")
            archivo.write_text("export DISPENSADOR_PUERTO=8000\n")
            with self.assertRaises(ValueError):
                cargar_entorno(archivo)


if __name__ == "__main__":
    unittest.main()
