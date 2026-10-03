"""Escribe la lista de escenas 3D con su duración (de tiempos.json) para render3d.mjs."""
import json, sys
import guion
t = json.load(open(sys.argv[1], encoding="utf-8"))
out = [dict({k: v for k, v in e.items() if k != "frases"}, duracion=t[e["id"]]["duracion"])
       for e in guion.ESCENAS if e["tipo"] == "3d"]
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
print(len(out), "escenas 3D,", round(sum(e["duracion"] for e in out), 1), "s")
