"""Escribe ../guion.md (texto de la narración por escena) a partir de guion.py."""
import json
import sys
from pathlib import Path

import guion

tiempos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if len(sys.argv) > 1 else {}
L = ["# Guion del video · Dispensador inteligente", "",
     "Texto de la narración, escena por escena (el mismo de los subtítulos). Sirve para leerlo en voz alta en la",
     "presentación o para grabar la narración con su propia voz.", ""]
t = 0.0
for e in guion.ESCENAS:
    d = tiempos.get(e["id"], {}).get("duracion")
    marca = f" · {int(t // 60)}:{int(t % 60):02d}" if d else ""
    L.append(f"### {e.get('titulo', e['id'])}{marca}")
    L.append("")
    L.append(" ".join(e["frases"]))
    L.append("")
    t += d or 0
(Path(__file__).resolve().parent.parent / "guion.md").write_text("\n".join(L), encoding="utf-8")
print("guion.md:", len(guion.ESCENAS), "escenas")
