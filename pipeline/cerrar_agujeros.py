"""Cierra los agujeros de provincias y comunidades que no son territorio de otra.

Tras simplificar quedan huecos pequeños sin sección ni territorio comunero asignado.
Un agujero se conserva solo si lo ocupa otra provincia o comunidad (p. ej. el enclave
de Treviño, de Burgos, dentro de Álava); si no, se rellena.
Uso:  python pipeline/cerrar_agujeros.py public/geo/provincias.json public/geo/ccaa.json
"""
import json, sys
from shapely.geometry import shape, Polygon

for path in sys.argv[1:]:
    fc = json.load(open(path))
    geoms = [shape(f["geometry"]).buffer(0) for f in fc["features"]]
    cerrados = 0
    for i, f in enumerate(fc["features"]):
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for part in parts:
            keep = [part[0]]
            for ring in part[1:]:
                h = Polygon(ring)
                ocupado = max((o.intersection(h).area for j, o in enumerate(geoms) if j != i), default=0)
                if h.area and ocupado / h.area >= 0.5: keep.append(ring)
                else: cerrados += 1
            part[:] = keep
    rnd = lambda c: [round(c[0], 4), round(c[1], 4)] if isinstance(c[0], (int, float)) else [rnd(x) for x in c]
    for f in fc["features"]: f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    json.dump(fc, open(path, "w"), separators=(",", ":"))
    print(f"{path}: {cerrados} agujeros cerrados")
