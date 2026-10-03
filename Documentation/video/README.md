# Video: funcionamiento y armado

**[Dispensador_IoT_funcionamiento_y_armado.mp4](Dispensador_IoT_funcionamiento_y_armado.mp4)** · 1280 × 720 · ≈ 7 min ·
narración en español con subtítulos incrustados ([subtítulos aparte en .srt](Dispensador_IoT_funcionamiento_y_armado.srt)).

| Parte | Contenido |
|---|---|
| Qué es | Torre girando; qué hace; componentes |
| Funcionamiento | Los 5 pasos (detecta → pregunta → foto y análisis → responde → decide y entrega); fotos cada 2 s en vez de video; red local sin Internet |
| Dosificador | Animación en corte: el disco lleva una croqueta de la tolva al conducto y de ahí al comedero |
| Seguridad del alimento | Recorrido cerrado separado de la electrónica |
| Sensor de nivel | Porcentaje por volumen, alertas al computador y al celular, panel web |
| Energía | Batería 2S, convertidores de 6 V y 5 V, estación solar remota (animada) |
| Electrónica | Recorrido por el esquema completo; placa de control |
| Impresión | 5 placas para la Elegoo Neptune 4 Plus |
| Armado | Los 11 pasos animados (las piezas nuevas entran a su lugar) |
| Cierre | Calibración, pruebas automáticas y repositorio |

El texto completo de la narración está en [guion.md](guion.md): sirve para leerlo en la presentación o para grabar el
video con su propia voz.

## Cómo se generó (y cómo volver a generarlo)

Todo sale del mismo modelo y la misma documentación del repositorio; si se cambia una pieza o un texto, el video se
vuelve a armar con los mismos pasos. Fuentes en [`fuente/`](fuente):

| Archivo | Qué hace |
|---|---|
| `guion.py` | Escenas, textos en pantalla y narración (con la pronunciación de las siglas para la voz) |
| `hacer_audio.py` | Narración con voz neuronal sin conexión (Piper, voz `es_MX-claude-high`, vía `sherpa-onnx`) y tiempos de cada frase |
| `exportar_mallas.py` | Piezas en posición de ensamblaje (desde `Mechanical/generar_stl.py`) |
| `web/escena3d.html` + `render3d.mjs` | Animaciones 3D (three.js) renderizadas cuadro a cuadro con Chromium |
| `web/laminas.html` + `laminas.py` + `render_laminas.mjs` | Láminas explicativas |
| `hacer_video.py` | Une todo con ffmpeg: zoom suave en las láminas, paneo por el esquema, subtítulos y audio normalizado |

```bash
cd Documentation/video/fuente
pip install sherpa-onnx numpy trimesh manifold3d pillow
npm install three playwright              # o enlazar un node_modules que los tenga
# voz: https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_MX-claude-high.tar.bz2
VOZ_DIR=ruta/vits-piper-es_MX-claude-high python hacer_audio.py salida
python exportar_mallas.py web/mallas
python escenas3d.py salida/tiempos.json salida/escenas3d.json
python -m http.server 8099 -d web &       # las páginas se sirven por HTTP
node render3d.mjs salida/escenas3d.json salida/cuadros 25
python laminas.py && node render_laminas.mjs salida/laminas
python hacer_video.py salida ../Dispensador_IoT_funcionamiento_y_armado.mp4
python guion_md.py salida/tiempos.json
```

La captura del panel web (`web/img/panel_web.png`) se tomó del servidor real con datos de demostración; la foto de
prueba que muestra el panel se reemplazó por un recuadro, porque era una imagen de terceros.
