"""Lista de secciones 2025 y sus vecinas, para rellenar las que no tienen scoring.

Uso:  python pipeline/vecinas_2025.py ruta/al/SECC_CE_20250101.shp
Sale: pipeline/inputs/secciones_2025.json   {cusec: [cumun, nombre_municipio, [vecinas…]]}

Dos secciones son vecinas si comparten borde o punto (se tolera 1 m por las
imprecisiones de la cartografía). Se ejecuta solo cuando cambia el seccionado.
"""
import json, os, sys
import geopandas as gpd

HERE = os.path.dirname(os.path.abspath(__file__))
shp = sys.argv[1]
g = gpd.read_file(shp, encoding="latin1", columns=["CUSEC", "CUMUN", "NMUN"])
g = g.to_crs(25830).reset_index(drop=True)
buf = g.geometry.buffer(1)
izq, der = g.sindex.query(buf, predicate="intersects")
vec = {c: [] for c in g["CUSEC"]}
for i, j in zip(izq, der):
    if i != j:
        vec[g.at[i, "CUSEC"]].append(g.at[j, "CUSEC"])
out = {r.CUSEC: [r.CUMUN, r.NMUN, sorted(set(vec[r.CUSEC]))] for r in g.itertuples()}
json.dump(out, open(os.path.join(HERE, "inputs", "secciones_2025.json"), "w"),
          ensure_ascii=False, separators=(",", ":"))
sin = sum(1 for v in out.values() if not v[2])
print(f"{len(out)} secciones, {sin} sin vecinas (islas)")
