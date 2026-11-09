"""Genera los ficheros del mapa a partir de calculo_prioridades.run().

Salida (out/data/):
  meta.json         catálogo, umbrales, etiquetas
  sscc/{cpro}.json  una provincia por fichero (lo que sirve el Worker por rol)
  municipios.json   índice municipal
  territorios.json  provincias (nivel del comité/modelo) y CCAA
"""
import json, math, os
import numpy as np
import pandas as pd
from calculo_prioridades import IN, HERE, run, PRIOS, CUTS, levels_by_share, cut_values, wavg, ccaa_level, NIVEL_PROV, TAM_REF

OUT = os.path.join(HERE, "..", "public", "data")
os.makedirs(f"{OUT}/sscc", exist_ok=True)
R = run(IN("prioridades_sscc.xlsx"), IN("Prioridad_provincias_FA_29N_Ateneo.xlsx"), IN("cod_pos_sscc.csv"))
prov, d, mun = R["prov"], R["secc"], R["mun"]

d = d.rename(columns={
    "Vencedor Generales": "v23", "% Participación": "part23", "% Sumar": "sumar23", "% Psoe": "psoe23",
    "% Izq nacionalista": "izqnac23", "% Izq minoritaria": "izqmin23", "% Derechas": "dcha23", "% Otros": "otros23",
    "Vencedor Generales.1": "v19", "Censo.1": "censo19", "Participación.1": "votos19",
    "% Participación.1": "part19", "% Sumar.1": "sumar19", "% Psoe.1": "psoe19",
    "% Izq nacionalista.1": "izqnac19", "% Izq minoritaria.1": "izqmin19",
    "% Derechas.1": "dcha19", "% Otros.1": "otros19"})

prov_geo = json.load(open(os.path.join(HERE, "..", "public", "geo", "provincias.json")))
cpro2cca = {f["properties"]["CPRO"]: f["properties"]["CCA"] for f in prov_geo["features"]}
d["cca"] = d["cpro"].map(cpro2cca)

def r(x, n=2):
    if x is None or (isinstance(x, float) and math.isnan(x)): return None
    return round(float(x), n)
def s(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else x

# ── Secciones (seccionado 2025) ───────────────────────────────────────
# Datos electorales de 2023 por código; el scoring viene de secc25 (real o media de vecinas).
SSCC_COLS = ["score", "pidx", "cumun", "score_orig", "v23", "censo23", "part23", "sumar23", "psoe23",
             "izqnac23", "izqmin23", "dcha23", "otros23",
             "v19", "censo19", "part19", "sumar19", "psoe19", "izqnac19", "izqmin19", "dcha19", "otros19", "pprov"]
ELEC = SSCC_COLS[4:-1]
d23 = d.set_index("cusec")
s25 = R["secc25"]
# Prioridad dentro de su provincia: mismo reparto 10/10/20/30/30 %, comparando solo con las de la provincia
s25["nivel_prov_rel"] = s25.groupby("cpro")["score_final"].transform(levels_by_share).astype(int)
for cpro, g in s25.groupby("cpro"):
    peso = float(prov.loc[cpro, "peso"])
    rows = {}
    for t in g.itertuples(index=False):
        e = d23.loc[t.cusec] if t.cusec in d23.index else None
        elec = []
        for c in ELEC:
            x = None if e is None else e[c]
            if c in ("v23", "v19"): elec.append(s(x))
            elif c in ("censo23", "censo19"): elec.append(None if x is None or pd.isna(x) else int(x))
            else: elec.append(r(x))
        rows[t.cusec] = [r(t.score_final), int(t.nivel), t.cumun, r(t.score_final / peso)] + elec + [int(t.nivel_prov_rel)]
    json.dump({"cols": SSCC_COLS, "peso": peso, "rows": rows},
              open(f"{OUT}/sscc/{cpro}.json", "w"), ensure_ascii=False, separators=(",", ":"))

# ── Agregados electorales (para popups) ───────────────────────────────
PCT = ["sumar", "psoe", "izqnac", "izqmin", "dcha", "otros"]
def votos(g):
    out = {}
    for y in ("23", "19"):
        censo, vot = g[f"censo{y}"].sum(), g[f"votos{y}"].sum()
        out[f"censo{y}"] = int(censo) if censo else None
        out[f"part{y}"] = r(100 * vot / censo) if censo else None
        for p in PCT: out[f"{p}{y}"] = r(wavg(g[f"{p}{y}"], g[f"votos{y}"]))
        vv = g.groupby(f"v{y}")[f"votos{y}"].sum()
        out[f"v{y}"] = vv.idxmax() if len(vv) else None
    out["n"] = int(len(g))
    out["dist"] = [int((g["nivel"] == i).sum()) for i in range(6)]
    tot = g["censo23"].sum()
    out["pct_prior"] = r(100 * g.loc[g["nivel"] <= 1, "censo23"].sum() / tot, 1) if tot else None
    out["score_medio"] = r(wavg(g["score_final"], g["censo23"]))
    return out
VOTE_COLS = ["n", "dist", "pct_prior", "score_medio", "v23", "censo23", "part23"] + [f"{p}23" for p in PCT] + \
            ["v19", "censo19", "part19"] + [f"{p}19" for p in PCT]

# ── Municipios ────────────────────────────────────────────────────────
MUN_COLS = ["name", "cpro", "score", "pidx", "factor"] + VOTE_COLS + ["pprov"]
mun["cpro"] = [k[:2] for k in mun.index]
mun["nivel_prov_rel"] = mun.groupby("cpro")["indice"].transform(levels_by_share).astype(int)
mun_rows = {}
for cumun, m in mun.iterrows():
    g = d[d["cumun"] == cumun]
    v = votos(g) if len(g) else {c: None for c in VOTE_COLS}   # municipios nuevos de 2025: sin datos de 2023
    mun_rows[cumun] = [m["mun_n"], cumun[:2], r(m["indice"]), int(m["nivel"]), r(m.get("factor"))] + [v[c] for c in VOTE_COLS] + [int(m["nivel_prov_rel"])]
json.dump({"cols": MUN_COLS, "rows": mun_rows}, open(f"{OUT}/municipios.json", "w"), ensure_ascii=False, separators=(",", ":"))

# ── Provincias (nivel del comité/modelo) y CCAA ──────────────────────
P_EXTRA = ["nivel_txt", "peso", "categoria_modelo", "escanos", "esc23", "esc_fa", "esc_seguros", "fa_est", "p_mas", "p_menos", "p_filo", "rival", "fa_nac_sig"]
T_COLS = ["name", "score", "pidx"] + VOTE_COLS
provincias = {}
for cpro, g in d.groupby("cpro"):
    v = votos(g); p = prov.loc[cpro]
    extra = {k: (r(p[k], 4) if isinstance(p[k], (float, np.floating)) else (int(p[k]) if isinstance(p[k], (int, np.integer)) else s(p[k]))) for k in P_EXTRA}
    provincias[cpro] = [g["prov_n"].iloc[0], v["score_medio"], int(p["nivel"])] + [v[c] for c in VOTE_COLS] + [cpro2cca[cpro], extra]
# Comunidad: media de los pesos de sus provincias ponderada por censo -> nivel provincial más cercano
ccaa_score = d.groupby("cca").apply(lambda g: wavg(g["score_final"], g["censo23"]), include_groups=False)
ccaa_peso = d.groupby("cca").apply(lambda g: wavg(g["peso_prov"], g["censo23"]), include_groups=False)
ccaa_lv = ccaa_peso.apply(ccaa_level)
ccaa = {}
for cca, g in d.groupby("cca"):
    v = votos(g)
    ccaa[cca] = [g["ccaa_n"].iloc[0], r(ccaa_score[cca]), int(ccaa_lv[cca])] + [v[c] for c in VOTE_COLS] + [r(ccaa_peso[cca], 3)]
json.dump({"cols": T_COLS, "provincias": provincias, "ccaa": ccaa}, open(f"{OUT}/territorios.json", "w"), ensure_ascii=False, separators=(",", ":"))

# ── Meta ──────────────────────────────────────────────────────────────
meta = {
    "prioridades": PRIOS,
    "niveles_provincia": PRIOS,
    "pesos_provincia": [1.00, 0.90, 0.80, 0.70, 0.55],
    "umbrales_seccion": R["thr"]["seccion"],
    "cortes": [round(x, 2) for x in R["t_sec"]],          # escala común: Máxima, Alta, Media, Baja (≥)
    "tam_ref": TAM_REF,
    "ccaa": sorted([{"cca": k, "name": v[0], "provincias": sorted([p for p, c in cpro2cca.items() if c == k])} for k, v in ccaa.items()], key=lambda x: x["name"]),
    "provincias": {k: v[0] for k, v in provincias.items()},
    "n_secciones": int(len(s25)),
    "seccionado": "INE 1/1/2025",
    "fuente": "prioridades_sscc.xlsx y Prioridad_provincias_FA_29N_Ateneo.xlsx (18/10/2026)",
}
json.dump(meta, open(f"{OUT}/meta.json", "w"), ensure_ascii=False, indent=1)
print("ok", len(d), len(mun_rows), len(provincias), len(ccaa))
