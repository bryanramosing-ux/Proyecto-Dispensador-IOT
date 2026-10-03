"""
Arma el video final con ffmpeg a partir de:
  salida/tiempos.json + salida/audio/*.wav    (hacer_audio.py)
  salida/laminas/*.png                         (laminas.py + render_laminas.mjs)
  salida/cuadros/<escena>/*.jpg                (escenas3d.py + render3d.mjs)

    python hacer_video.py salida/ Dispensador_IoT.mp4

Cada escena dura lo mismo que su narración. Los subtítulos (salida/subtitulos.ass y .srt)
usan el tiempo real de cada frase y se incrustan en la imagen.
"""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

import guion

FPS, ANCHO, ALTO = 25, 1280, 720
RAIZ = Path(__file__).resolve().parents[3]
FUNDIDO = 0.3


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


def codificar():
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", FPS]


def fundidos(n):
    d = n / FPS
    return (f"fade=t=in:st=0:d={FUNDIDO}:color=white,"
            f"fade=t=out:st={d - FUNDIDO:.3f}:d={FUNDIDO}:color=white")


def clip_lamina(png, n, salida):
    vf = (f"scale={ANCHO * 2}:{ALTO * 2},zoompan=z='1+0.035*on/{n}':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={n}:s={ANCHO}x{ALTO}:fps={FPS},{fundidos(n)}")
    ff("-i", png, "-vf", vf, "-frames:v", n, *codificar(), salida)


def clip_paneo(imagen, rotulo, n, salida):
    # esquema 2000x1500 -> recorte 16:9 sin el cuadro de reglas; recorrido izquierda -> derecha
    z = 1.7
    vf = (f"[0:v]crop=2000:1125:0:40,scale=3840:2160,zoompan=z={z}:"
          f"x='(iw-iw/zoom)*min(1,max(0,(on-{FPS})/({n}-{3 * FPS})))':y='(ih-ih/zoom)*0.42':"
          f"d={n}:s={ANCHO}x{ALTO}:fps={FPS}[p];[p][1:v]overlay=0:0,{fundidos(n)}")
    ff("-i", imagen, "-i", rotulo, "-filter_complex", vf, "-frames:v", n, *codificar(), salida)


def clip_cuadros(carpeta, n, salida):
    ff("-framerate", FPS, "-i", Path(carpeta) / "%05d.jpg", "-vf", fundidos(n), "-frames:v", n,
       *codificar(), salida)


def leer_wav(ruta):
    with wave.open(str(ruta)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16), w.getframerate()


def trozos(texto, inicio, fin, maximo=84):
    """Divide frases largas en partes de <= 2 líneas, con tiempo proporcional al largo."""
    partes = [texto]
    while any(len(p) > maximo for p in partes):
        nuevas = []
        for p in partes:
            if len(p) <= maximo:
                nuevas.append(p)
                continue
            cortes = [m.end() for m in re.finditer(r"[,:;]\s", p)] or [m.end() for m in re.finditer(r"\s", p)]
            c = min(cortes, key=lambda k: abs(k - len(p) / 2))
            nuevas += [p[:c].strip(), p[c:].strip()]
        partes = nuevas
    total = sum(len(p) for p in partes)
    t, salida = inicio, []
    for p in partes:
        d = (fin - inicio) * len(p) / total
        salida.append((t, t + d, p))
        t += d
    return salida


def hms(t, ass=True):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}" if ass else f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def main():
    base = Path(sys.argv[1])
    final = Path(sys.argv[2])
    tiempos = json.loads((base / "tiempos.json").read_text(encoding="utf-8"))
    clips = base / "clips"
    clips.mkdir(exist_ok=True)
    lista, audio, subs, t0, sr = [], [], [], 0.0, 22050
    for e in guion.ESCENAS:
        dur = tiempos[e["id"]]["duracion"]
        n = round(dur * FPS)
        salida = clips / f"{e['id']}.mp4"
        if e["tipo"] == "lamina":
            clip_lamina(base / "laminas" / f"{e['id']}.png", n, salida)
        elif e["tipo"] == "paneo":
            clip_paneo(RAIZ / e["imagen"], base / "laminas" / f"{e['id']}.png", n, salida)
        else:
            clip_cuadros(base / "cuadros" / e["id"], n, salida)
        lista.append(f"file '{salida.resolve()}'")
        x, sr = leer_wav(base / "audio" / f"{e['id']}.wav")
        largo = round(n / FPS * sr)
        audio.append(np.pad(x, (0, max(0, largo - len(x))))[:largo])
        for f in tiempos[e["id"]]["frases"]:
            subs += trozos(f["texto"], t0 + f["inicio"], t0 + f["fin"])
        t0 += n / FPS
        print(f"{e['id']:22s} {n / FPS:6.1f} s")

    (base / "clips.txt").write_text("\n".join(lista) + "\n", encoding="utf-8")
    with wave.open(str(base / "narracion.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.concatenate(audio).astype(np.int16).tobytes())

    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {ANCHO}", f"PlayResY: {ALTO}", "WrapStyle: 0",
           "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
           "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
           "MarginL, MarginR, MarginV, Encoding",
           "Style: Base,Noto Sans,29,&H00FFFFFF,&H000000FF,&H40182430,&H40182430,0,0,0,0,100,100,0,0,3,9,0,2,"
           "90,90,20,1", "", "[Events]",
           "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    srt = []
    for i, (a, b, texto) in enumerate(subs, 1):
        ass.append(f"Dialogue: 0,{hms(a)},{hms(b)},Base,,0,0,0,,{texto}")
        srt += [str(i), f"{hms(a, False)} --> {hms(b, False)}", texto, ""]
    (base / "subtitulos.ass").write_text("\n".join(ass) + "\n", encoding="utf-8")
    (base / "subtitulos.srt").write_text("\n".join(srt), encoding="utf-8")

    ff("-f", "concat", "-safe", "0", "-i", base / "clips.txt", "-i", base / "narracion.wav",
       "-vf", f"ass={base / 'subtitulos.ass'}", "-c:v", "libx264", "-preset", "slow", "-crf", "23",
       "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "128k",
       "-ar", "44100", "-shortest", "-movflags", "+faststart", final)
    print(f"Video: {final}  ({t0 / 60:.1f} min, {final.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
