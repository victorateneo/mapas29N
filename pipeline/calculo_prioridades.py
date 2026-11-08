"""Cálculo fino de prioridades FA · Generales 29N.

Entradas
  prioridades_sscc.xlsx                      scoring original por sección (0–10)
  Prioridad_provincias_FA_29N_Ateneo.xlsx    modelo de escaños (pestaña Ranking)
  cod_pos_sscc.csv                           sección -> código postal

Pasos
  1. Prioridad provincial (5 niveles) y peso: las 4 absolutas que fija el comité
     (Madrid, Barcelona, Valencia, Alicante) y el resto según la categoría del modelo
     de escaños.
  2. Scoring final de sección = scoring original × peso de su provincia.
  3. Niveles de sección: mismo reparto que el original (10/10/20/30/30 %) sobre el
     scoring final, a escala de España.
  4. Municipios y códigos postales: índice = scoring medio (ponderado por censo)
     × log10(censo). Premia a la vez calidad y tamaño, sin que las ciudades grandes
     se lo lleven todo. Se reescala a 0–10 y se reparte 10/10/20/30/30 %.
"""
import math
import os
HERE = os.path.dirname(os.path.abspath(__file__))
IN = lambda f: os.path.join(HERE, "inputs", f)
import numpy as np
import pandas as pd

PRIOS = ["Máxima", "Alta", "Media", "Baja", "Nula"]
CUTS = [0.10, 0.20, 0.40, 0.70, 1.00]          # reparto acumulado de niveles

# ── 1. Provincias ────────────────────────────────────────────────────
# Nombre en el Excel del modelo -> código INE
XL2INE = {
    "Álava": "01", "Albacete": "02", "Alicante": "03", "Almería": "04", "Ávila": "05", "Badajoz": "06",
    "Illes Balears": "07", "Barcelona": "08", "Burgos": "09", "Cáceres": "10", "Cádiz": "11", "Castellón": "12",
    "Ciudad Real": "13", "Córdoba": "14", "A Coruña": "15", "Cuenca": "16", "Girona": "17", "Granada": "18",
    "Guadalajara": "19", "Gipuzkoa": "20", "Huelva": "21", "Huesca": "22", "Jaén": "23", "León": "24",
    "Lleida": "25", "La Rioja": "26", "Lugo": "27", "Madrid": "28", "Málaga": "29", "Murcia": "30",
    "Navarra": "31", "Ourense": "32", "Asturias": "33", "Palencia": "34", "Las Palmas": "35", "Pontevedra": "36",
    "Salamanca": "37", "Santa Cruz de Tenerife": "38", "Cantabria": "39", "Segovia": "40", "Sevilla": "41",
    "Soria": "42", "Tarragona": "43", "Teruel": "44", "Toledo": "45", "Valencia": "46", "Valladolid": "47",
    "Bizkaia": "48", "Zamora": "49", "Zaragoza": "50", "Ceuta": "51", "Melilla": "52",
}
ABSOLUTAS = {"28", "08", "46", "03"}            # decisión del comité
# Prioridad provincial y peso
#   Máxima: decisión del comité · Alta: «En el filo» / «A por uno más» en el modelo
#   Media / Baja: según el voto nacional de FA con el que entra su siguiente escaño
NIVEL_PROV = [  # (nivel, etiqueta, peso)
    (0, "Máxima", 1.00), (1, "Alta", 0.90), (2, "Media", 0.80), (3, "Baja", 0.70), (4, "Nula", 0.55),
]
CAT_ALTA = {"En el filo", "A por uno más", "Defender"}
UMBRAL_MEDIA = 0.09   # siguiente escaño con FA ≤ 9 % nacional
UMBRAL_BAJA = 0.13    # siguiente escaño con FA ≤ 13 % nacional

def load_provincias(path):
    raw = pd.read_excel(path, sheet_name="Ranking", header=None)
    hdr = raw.index[raw[1].astype(str).eq("#")][0]
    df = raw.iloc[hdr + 1:, 1:].copy()
    df.columns = raw.iloc[hdr, 1:].tolist()
    df = df[pd.to_numeric(df["#"], errors="coerce").notna()].copy()
    df["cpro"] = df["Provincia"].map(XL2INE)
    assert df["cpro"].notna().all(), df.loc[df["cpro"].isna(), "Provincia"].tolist()
    def nivel(r):
        if r["cpro"] in ABSOLUTAS: return 0
        if r["Prioridad"] in CAT_ALTA: return 1
        sig = pd.to_numeric(r["FA nacional para el siguiente escaño"], errors="coerce")
        if pd.notna(sig) and sig <= UMBRAL_MEDIA: return 2
        if pd.notna(sig) and sig <= UMBRAL_BAJA: return 3
        return 4
    df["nivel"] = df.apply(nivel, axis=1)
    df["nivel_txt"] = df["nivel"].map({n: t for n, t, _ in NIVEL_PROV})
    df["peso"] = df["nivel"].map({n: w for n, _, w in NIVEL_PROV})
    keep = {"#": "rank_modelo", "Provincia": "provincia_modelo", "Prioridad": "categoria_modelo",
            "Escaños en juego": "escanos", "Candidatura": "candidatura", "Escaños 23J (Sumar)": "esc23",
            "FA % estimado": "fa_est", "Escaños FA (central)": "esc_fa", "Prob. uno más": "p_mas",
            "Prob. uno menos": "p_menos", "Prob. escaño en el filo": "p_filo",
            "Rival siguiente escaño": "rival", "FA nacional para el siguiente escaño": "fa_nac_sig",
            "Escaños casi seguros": "esc_seguros"}
    out = df[["cpro", "nivel", "nivel_txt", "peso"] + list(keep)].rename(columns=keep)
    return out.set_index("cpro")

# ── Utilidades ───────────────────────────────────────────────────────
def thresholds(score):
    """Cortes como PERCENTIL.INC de Excel: Máxima ≥ p90, Alta ≥ p80, Media ≥ p60, Baja ≥ p30."""
    v = score.dropna().to_numpy()
    return [float(np.percentile(v, 100 * (1 - c))) for c in CUTS[:4]]

def levels_by_share(score):
    """Nivel 0–4 (5 = sin datos) con reparto 10/10/20/30/30 % por percentiles."""
    t = thresholds(score)
    def lv(x):
        if pd.isna(x): return 5
        for i, c in enumerate(t):
            if x >= c: return i
        return 4
    return score.apply(lv).astype(int)

def cut_values(score, lv):
    return {PRIOS[i]: round(float(score[lv == i].min()), 2) for i in range(5)}

def wavg(v, w):
    m = v.notna() & w.notna() & (w > 0)
    return float(np.average(v[m], weights=w[m])) if m.any() else np.nan

def size_index(g):
    """Índice de municipio / CP: scoring medio ponderado × log10(censo)."""
    censo = g["censo23"].sum()
    s = wavg(g["score_final"], g["censo23"])
    return pd.Series({
        "n_secc": len(g), "censo": censo, "score_medio": s,
        "indice_bruto": s * math.log10(censo) if censo and censo > 1 and not np.isnan(s) else np.nan,
        "secc_max_alta": int((g["nivel"] <= 1).sum()),
        "pct_censo_max_alta": 100 * g.loc[g["nivel"] <= 1, "censo23"].sum() / censo if censo else np.nan,
    })

def run(sscc_xlsx, prov_xlsx, cp_csv):
    prov = load_provincias(prov_xlsx)

    # ── 2. Secciones ────────────────────────────────────────────────
    d = pd.read_excel(sscc_xlsx, header=1)
    d = d.rename(columns={"Seccion": "cusec", "Scoring": "score_orig", "Prioridad": "prio_orig",
                          "Comunidad": "ccaa_n", "Provincia": "prov_n", "Municipio": "mun_n",
                          "Censo": "censo23", "Participación": "votos23"})
    d["cusec"] = d["cusec"].astype(str).str.zfill(10)
    d["cpro"], d["cumun"] = d["cusec"].str[:2], d["cusec"].str[:5]
    d["peso_prov"] = d["cpro"].map(prov["peso"])
    d["nivel_prov"] = d["cpro"].map(prov["nivel"])
    d["score_final"] = d["score_orig"] * d["peso_prov"]
    d["nivel"] = levels_by_share(d["score_final"])
    thr_sec = cut_values(d["score_final"], d["nivel"])

    cp = pd.read_csv(cp_csv, dtype=str)
    d = d.merge(cp.rename(columns={"CUSEC": "cusec", "COD_POSTAL": "cp"}), on="cusec", how="left")

    # ── 3. Municipios ───────────────────────────────────────────────
    mun = d.groupby("cumun").apply(size_index, include_groups=False)
    mun["indice"] = 10 * mun["indice_bruto"] / mun["indice_bruto"].max()
    mun["nivel"] = levels_by_share(mun["indice"])
    first = d.groupby("cumun")[["mun_n", "prov_n", "ccaa_n", "cpro"]].first()
    mun = first.join(mun)
    thr_mun = cut_values(mun["indice"], mun["nivel"])

    # ── 4. Códigos postales ─────────────────────────────────────────
    cpd = d[d["cp"].notna()].groupby("cp").apply(size_index, include_groups=False)
    cpd["indice"] = 10 * cpd["indice_bruto"] / cpd["indice_bruto"].max()
    cpd["nivel"] = levels_by_share(cpd["indice"])
    # municipio principal (más censo) y nº de municipios del CP
    mp = d[d["cp"].notna()].groupby(["cp", "mun_n", "prov_n"])["censo23"].sum().reset_index()
    mp = mp.sort_values("censo23", ascending=False).groupby("cp").agg(
        municipio=("mun_n", "first"), provincia=("prov_n", "first"), n_mun=("mun_n", "nunique"))
    cpd = mp.join(cpd)
    thr_cp = cut_values(cpd["indice"], cpd["nivel"])

    return dict(prov=prov, secc=d, mun=mun, cp=cpd, thr=dict(seccion=thr_sec, municipio=thr_mun, cp=thr_cp))

if __name__ == "__main__":
    r = run(IN("prioridades_sscc.xlsx"), IN("Prioridad_provincias_FA_29N_Ateneo.xlsx"), IN("cod_pos_sscc.csv"))
    p, d, m = r["prov"], r["secc"], r["mun"]
    print(p.groupby(["nivel", "nivel_txt"])["provincia_modelo"].apply(list))
    print("umbrales", r["thr"])
    print("secciones por nivel y nivel provincial\n", pd.crosstab(d["nivel_prov"], d["nivel"]))
    print(m.sort_values("indice", ascending=False).head(15)[["mun_n", "n_secc", "censo", "score_medio", "indice", "nivel"]])
    print(m["nivel"].value_counts().sort_index())
