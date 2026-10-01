# Servidor de visión (PC / notebook) — Python + OpenCV

| Pieza | Qué hace |
|---|---|
| ESP32-CAM | Solo captura el JPEG |
| `servidor_vision.py` | Servidor HTTP (biblioteca estándar). Recibe `GET /classify` del ESP32, pide fotos a la cámara y responde; recibe las alertas de nivel (`POST /alerta`) y sirve el **panel web** (`GET /`) |
| `alertas.py` | Guarda las alertas de la tolva y, si se configura, las reenvía al celular con **ntfy** |
| OpenCV | Decodifica el JPEG, mide brillo y nitidez (varianza del Laplaciano), aplica CLAHE, prepara el *blob* y **ejecuta la red con `cv2.dnn`** |
| Modelo MobileNetV2 (ImageNet) | Interpreta la imagen. P(perro) = suma de las 118 razas (índices 151–268); P(gato) = suma de 5 gatos domésticos (281–285) |
| Regla de decisión | 1 = PERRO, 2 = GATO, 0 = INDETERMINADO (no dispensar) |

## Instalación y uso

```bash
cd OpenCV
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python descargar_modelo.py                              # una sola vez (14 MB, verifica SHA-256)
python servidor_vision.py --camara http://192.168.1.51 --esp32 http://192.168.1.52 --puerto 8000
```

Permitir el puerto 8000 en el firewall del PC (Windows lo pregunta la primera vez).

## Panel web y alertas de comida (sensor de nivel de la tolva)

* **Panel web:** abra `http://IP-DEL-PC:8000/` en el navegador (también desde el celular, en la misma red). Muestra la
  barra de nivel de la tolva, el estado del ESP32 (lo lee de su `/status`), las últimas alertas y las últimas
  clasificaciones; se actualiza cada 5 s. Los mismos datos en JSON: `GET /panel.json`.
* **Alertas:** el ESP32 envía `POST /alerta` con `{"tipo": ..., "nivel": ...}`:

  | Tipo | Cuándo | Mensaje |
  |---|---|---|
  | `COMIDA_BAJA` | queda < 20 % del volumen | «La comida del dispensador se está acabando (nivel ~18 %). Recargue la tolva.» |
  | `COMIDA_AGOTADA` | ≤ 3 % | «La tolva está vacía: el dispensador no entregará raciones hasta recargarla.» |
  | `COMIDA_REPUESTA` | > 30 % después de una alerta | «Tolva recargada (nivel ~64 %).» |
  | `SENSOR_NIVEL_SIN_LECTURA` | el sensor no da eco | «El sensor de nivel de la tolva no responde: revise el cable de la tapa.» |

* **Al celular (opcional, gratis, sin cuentas):** instale la app **ntfy** (Android/iOS), suscríbase a un tema con un
  nombre difícil de adivinar (por ejemplo `dispensador-ana-7f3k9`) y arranque el servidor con `--ntfy dispensador-ana-7f3k9`
  (o `NTFY_TOPICO` en `config.py`). El PC necesita Internet; si no lo tiene, el panel web sigue funcionando y el
  dispensador no se entera (el envío va en segundo plano). Cualquiera que conozca el nombre del tema puede leer los
  avisos: no ponga datos personales en él.
* Probar sin el ESP32: `curl -X POST http://127.0.0.1:8000/alerta -d '{"tipo":"COMIDA_BAJA","nivel":18}'`.

## Probar sin hardware

```bash
python -m unittest discover -s tests -v                   # 22 pruebas (sin cámara ni modelo; incluye alertas y panel)
python simulador_camara.py --imagenes carpeta_fotos --puerto 8081 &
python servidor_vision.py --camara http://127.0.0.1:8081
curl "http://127.0.0.1:8000/classify?dist=25"
```

## Calibrar umbrales con fotos reales de la cámara instalada

```bash
python capturar_dataset.py --clase perro --cantidad 30
python capturar_dataset.py --clase gato  --cantidad 30
python capturar_dataset.py --clase otros --cantidad 30     # personas, juguetes, fondo vacío
python probar_imagenes.py dataset --barrido               # matriz de confusión y umbral sugerido
```

Ajustar `UMBRAL_CONFIANZA`, `MARGEN_MINIMO`, `BRILLO_*` y `NITIDEZ_MIN` en `config.py`
(o con variables de entorno `DISPENSADOR_*`).

## Limitaciones honestas

* El modelo reconoce **perro o gato en general**, no a una mascota concreta.
* Una foto de un perro en un celular o un peluche realista puede clasificarse como perro.
* Zorros, lobos o felinos grandes pueden dar probabilidades altas en clases cercanas; los umbrales y el margen reducen el riesgo, no lo eliminan.
* Mejora futura: reentrenar (transfer learning) con fotos propias de las mascotas de la casa.
