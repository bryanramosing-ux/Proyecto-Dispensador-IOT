"""
Narración del video con voz neuronal sin conexión (Piper, voz es_MX "claude", vía sherpa-onnx).

    pip install sherpa-onnx numpy
    # voz: https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_MX-claude-high.tar.bz2
    VOZ_DIR=ruta/vits-piper-es_MX-claude-high python hacer_audio.py salida/

Genera salida/audio/<escena>.wav y salida/tiempos.json (duración de cada escena y de cada frase,
que se usan para los subtítulos y para la duración de las animaciones).
"""
import json
import os
import sys
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx

import guion

ENTRADA, ENTRE_FRASES, SALIDA_S = 0.45, 0.35, 0.75     # silencios (s)
VELOCIDAD = 1.04


def motor(voz_dir):
    d = Path(voz_dir)
    onnx = next(d.glob("*.onnx"))
    cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(onnx), tokens=str(d / "tokens.txt"),
                                                   data_dir=str(d / "espeak-ng-data"),
                                                   noise_scale=0.6, noise_scale_w=0.8),
        num_threads=4))
    return sherpa_onnx.OfflineTts(cfg)


def main():
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else "salida")
    (salida / "audio").mkdir(parents=True, exist_ok=True)
    tts = motor(os.environ["VOZ_DIR"])
    tiempos = {}
    for esc in guion.ESCENAS:
        partes, frases, t = [np.zeros(int(ENTRADA * 22050))], [], ENTRADA
        sr = 22050
        for i, f in enumerate(esc["frases"]):
            a = tts.generate(guion.a_voz(f), sid=0, speed=VELOCIDAD)
            sr = a.sample_rate
            x = np.array(a.samples, dtype=np.float32)
            frases.append({"texto": f, "inicio": round(t, 3), "fin": round(t + len(x) / sr, 3)})
            partes.append(x)
            t += len(x) / sr
            pausa = ENTRE_FRASES if i < len(esc["frases"]) - 1 else SALIDA_S
            partes.append(np.zeros(int(pausa * sr), dtype=np.float32))
            t += pausa
        audio = np.clip(np.concatenate(partes), -1, 1)
        with wave.open(str(salida / "audio" / f"{esc['id']}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((audio * 32767).astype(np.int16).tobytes())
        tiempos[esc["id"]] = {"duracion": round(len(audio) / sr, 3), "frases": frases}
        print(f"{esc['id']:22s} {len(audio) / sr:6.1f} s")
    (salida / "tiempos.json").write_text(json.dumps(tiempos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Total: {sum(v['duracion'] for v in tiempos.values()) / 60:.1f} min")


if __name__ == "__main__":
    main()
