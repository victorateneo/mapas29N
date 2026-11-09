#!/usr/bin/env bash
# Genera las geometrías del mapa a partir de la cartografía de secciones del INE.
# Uso:  bash pipeline/build_geo.sh ruta/al/SECC_CE_20250101.shp
# (El .shp con su .dbf, .shx y .prj en la misma carpeta. Descarga: INE, «Cartografía
#  digitalizada de secciones censales», fecha de referencia 1/1/2025.)
set -euo pipefail
SHP="${1:?Indica la ruta al .shp de secciones del INE}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GEO="$ROOT/public/geo"
TMP="$(mktemp -d)"
MS="npx --yes mapshaper@0.6"

mkdir -p "$GEO/sscc" "$TMP/split"

# 1. Base común: WGS84, campos mínimos, topología limpia
$MS -i "$SHP" -proj wgs84 -filter-fields CUSEC,CUMUN,CPRO,CCA,NMUN,NPRO,NCA -clean \
    -o "$TMP/base.topojson" format=topojson quantization=1e6

# 2. Secciones: una provincia por fichero, simplificadas
$MS -i "$TMP/base.topojson" -simplify 18% weighted keep-shapes -filter-fields CUSEC \
    -each 'CPRO=CUSEC.slice(0,2)' -split CPRO -o "$TMP/split" format=geojson
rm -f "$GEO"/sscc/*.topo.json
for f in "$TMP"/split/*.json; do
  b="$(basename "$f" .json)"
  $MS -i "$f" name=s -o "$GEO/sscc/$b.topo.json" format=topojson quantization=500000 >/dev/null
done

# 3. Municipios, provincias y comunidades (disolviendo secciones).
#    Provincias y comunidades incluyen los territorios sin sección (huecos_2025.py).
python3 "$ROOT/pipeline/huecos_2025.py" "$SHP" "$TMP/prov_full.json"
$MS -i "$TMP/base.topojson" -dissolve CUMUN copy-fields=NMUN,CPRO,CCA -simplify 6% weighted keep-shapes \
    -o "$GEO/municipios.topo.json" format=topojson quantization=200000
$MS -i "$TMP/prov_full.json" -dissolve CPRO copy-fields=NPRO,CCA -simplify 3% weighted keep-shapes \
    -o "$GEO/provincias.json" format=geojson precision=0.0001
$MS -i "$TMP/prov_full.json" -dissolve CCA copy-fields=NCA -simplify 3% weighted keep-shapes \
    -o "$GEO/ccaa.json" format=geojson precision=0.0001

python3 "$ROOT/pipeline/cerrar_agujeros.py" "$GEO/provincias.json" "$GEO/ccaa.json"

rm -rf "$TMP"
echo "Geometrías listas en $GEO ($(ls "$GEO/sscc" | wc -l) provincias)"
