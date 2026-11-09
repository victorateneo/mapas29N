"""Territorios sin sección censal (facerías, comunidades de pastos, Bardenas Reales…).

El seccionado del INE no cubre algunos territorios comuneros que no pertenecen a ningún
municipio (Bardenas Reales, sierras de Urbasa y Andía, Sierra de la Demanda…). Sin ellos,
las provincias tienen agujeros y el velo del foco los trata como si estuvieran fuera.

Este script los detecta (huecos de la unión de todas las secciones, de más de 0,05 km²) y
asigna cada uno a la provincia con la que comparte más frontera. Escribe las provincias
completas (secciones + esos territorios), que build_geo.sh usa para provincias y
comunidades; en municipios y secciones siguen vacíos (no tienen datos).

Uso:  python pipeline/huecos_2025.py ruta/al/SECC_CE_20250101.shp provincias_completas.geojson
"""
import sys
import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import Polygon

shp, out = sys.argv[1], sys.argv[2]
g = gpd.read_file(shp, encoding="latin1", columns=["CPRO", "NPRO", "CCA", "NCA"])
prov = g.dissolve("CPRO", as_index=False, aggfunc="first")
u = shapely.union_all(g.geometry.values)
holes = [Polygon(r) for p in getattr(u, "geoms", [u]) for r in p.interiors]
holes = [h for h in holes if h.area > 5e4]
rows = []
for h in holes:
    borde = prov.geometry.intersection(h.boundary.buffer(5)).length
    p = prov.loc[borde.idxmax()]
    rows.append({"CPRO": p["CPRO"], "NPRO": p["NPRO"], "CCA": p["CCA"], "NCA": p["NCA"], "geometry": h})
hu = gpd.GeoDataFrame(rows, crs=g.crs)
print(f"{len(hu)} territorios sin sección, {hu.area.sum() / 1e6:,.0f} km² en total")

# Provincias completas: secciones + territorios sin sección, unidas en la proyección original
# (los huecos comparten vértices exactos con las secciones, así que la unión queda limpia).
full = pd.concat([g[["CPRO", "NPRO", "CCA", "NCA", "geometry"]], hu], ignore_index=True)
prov_full = full.dissolve("CPRO", as_index=False, aggfunc="first")
prov_full["geometry"] = prov_full.geometry.buffer(0)
prov_full.to_crs(4326).to_file(out, driver="GeoJSON")
