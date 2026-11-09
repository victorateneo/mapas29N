"""Prioridad por par código postal y municipio (14.622 pares) con la lógica del mapa 29N.

Base: los pares de Prioridad_codigos_postales_Espana.xlsx, con la lógica del mapa:
  - Pares con secciones: scoring final medio de las secciones de ese CP en ese municipio
    (ponderado por censo) × factor de tamaño. Mismos cortes que las secciones.
  - Pares sin secciones o cuyas secciones no tienen censo ni scoring: heredan el índice
    de su municipio.
  - Prioridad en su provincia: reparto 10/10/20/30/30 % de los pares de cada provincia.
Salida: salida/Prioridad_codigos_postales_Espana_29N.xlsx
"""
import os, re, unicodedata
import numpy as np
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from calculo_prioridades import HERE, IN, run, size_index, level_of, levels_by_share, PRIOS, TAM_REF

P = PRIOS + ["Sin datos"]
R = run(IN("prioridades_sscc.xlsx"), IN("Prioridad_provincias_FA_29N_Ateneo.xlsx"), IN("cod_pos_sscc.csv"))
d, mun, t = R["secc"], R["mun"], R["t_sec"]
norm = lambda s: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode())

# ── Pares y código INE del municipio ─────────────────────────────────
o = pd.read_excel(IN("Prioridad_codigos_postales_Espana.xlsx"), sheet_name="Códigos postales", dtype=str)
cm = pd.read_excel(IN("codigos_postales_municipios_espana.xlsx"), sheet_name="CP por municipio", dtype=str)
rs = pd.read_excel(IN("codigos_postales_municipios_espana.xlsx"), sheet_name="Resumen por municipio", dtype=str)
o["kn"], cm["kn"], rs["kn"] = o["Municipio"].map(norm), cm["Municipio"].map(norm), rs["Municipio"].map(norm)
m = o.merge(cm[["Código postal", "kn", "Código INE municipio", "CP de otra provincia"]], on=["Código postal", "kn"], how="left")
alt = dict(zip(zip(rs["kn"], rs["Provincia"]), rs["Código INE municipio"]))
pn = d.groupby("cpro")["prov_n"].first().to_dict()
alt2 = {(norm(r.mun_n), pn.get(k[:2])): k for k, r in mun.iterrows()}   # nombres del INE (p. ej. bilingües)
falta = m["Código INE municipio"].isna()
m.loc[falta, "Código INE municipio"] = [alt.get((r.kn, r.Provincia)) or alt2.get((r.kn, r.Provincia)) for r in m[falta].itertuples()]
assert m["Código INE municipio"].notna().all(), m[m["Código INE municipio"].isna()]

# ── Cálculo ─────────────────────────────────────────────────────────
g = d[d["cp"].notna()].groupby(["cp", "cumun"]).apply(size_index, include_groups=False)
ccaa_n = d.groupby("cpro")["ccaa_n"].first().to_dict()
rows = []
for r in m.itertuples(index=False):
    cp, ine = r[0], r[7]
    x = g.loc[(cp, ine)] if (cp, ine) in g.index else None
    if x is not None and pd.notna(x["indice"]):
        idx, src = x["indice"], "Secciones del código postal en el municipio"
        sm, fac, ns, cen = x["score_medio"], x["factor"], int(x["n_secc"]), int(x["censo"])
    else:
        idx, src = mun.loc[ine, "indice"], "Hereda la prioridad de su municipio"
        sm = fac = cen = np.nan; ns = 0 if x is None else int(x["n_secc"])
    nota = []
    if isinstance(r[8], str) and r[8].strip(): nota.append("Código postal de otra provincia (enclave o municipio limítrofe).")
    rows.append({"Código postal": cp, "Municipio": r.Municipio, "Cód. INE municipio": ine, "Provincia": r.Provincia,
                 "Comunidad": ccaa_n[ine[:2]], "cpro": ine[:2], "Índice (0-10)": idx, "Cálculo": src,
                 "Scoring final medio": sm, "Factor tamaño": fac, "Nº secciones": ns, "Censo 2023": cen, "Notas": " ".join(nota)})
out = pd.DataFrame(rows)
out["Prioridad en España"] = [P[level_of(x, t)] for x in out["Índice (0-10)"]]
out["Prioridad en su provincia"] = [P[int(v)] for v in out.groupby("cpro")["Índice (0-10)"].transform(levels_by_share)]
out = out[["Código postal", "Municipio", "Cód. INE municipio", "Provincia", "Comunidad", "Índice (0-10)", "Prioridad en España",
           "Prioridad en su provincia", "Cálculo", "Scoring final medio", "Factor tamaño", "Nº secciones", "Censo 2023", "Notas"]]
for c in ["Índice (0-10)", "Scoring final medio", "Factor tamaño"]: out[c] = out[c].round(2)

# ── Excel ───────────────────────────────────────────────────────────
es = lambda v: f"{v:.2f}".replace(".", ",")
ref = f"{TAM_REF:,}".replace(",", ".")
n_sec = int(out["Cálculo"].str.startswith("Secc").sum())
notes = [
    ["PRIORIDAD POR CÓDIGO POSTAL, ESPAÑA (29N)"], ["Ateneo del Dato, 9 de noviembre de 2026"], [],
    ["Base: los 14.622 pares código postal y municipio de Prioridad_codigos_postales_Espana.xlsx, con la misma lógica que el mapa del 29N y los ficheros de secciones y municipios."], [],
    ["Cómo se calcula"],
    ["1. Scoring final de cada sección censal = scoring de la sección (prioridades_sscc.xlsx) × peso de su provincia (1,00 Máxima, 0,90 Alta, 0,80 Media, 0,70 Baja, 0,55 Nula)."],
    ["2. Pares con secciones: scoring final medio de las secciones de ese código postal dentro de ese municipio, ponderado por censo, × factor de tamaño."],
    [f"   Factor de tamaño = log10(censo) / log10({ref}), como mucho 1: a partir de {ref} electores no rebaja; por debajo, cuanto más pequeño, más rebaja."],
    ["3. Pares sin secciones propias heredan el índice de su municipio, calculado igual con todas sus secciones. Cada sección tiene un único código postal, así que muchos códigos pequeños no tienen ninguna."],
    [f"4. Prioridad en España: los mismos cortes que las secciones y los municipios del mapa. Máxima desde {es(t[0])}, Alta desde {es(t[1])}, Media desde {es(t[2])}, Baja desde {es(t[3])}, Nula el resto."],
    ["5. Prioridad en su provincia: los pares de cada provincia se reparten 10 % Máxima, 10 % Alta, 20 % Media, 30 % Baja y 30 % Nula según su índice, comparándolos solo entre ellos."], [],
    ["Cifras"], ["Pares código postal y municipio", len(out)], ["Códigos postales distintos", out["Código postal"].nunique()],
    ["Pares calculados con sus secciones", n_sec], ["Pares que heredan la prioridad de su municipio", len(out) - n_sec], [],
    ["Fuentes: prioridades_sscc.xlsx; Prioridad_provincias_FA_29N_Ateneo.xlsx (pestaña Ranking, 18/10/2026); cod_pos_sscc.csv (sección a código postal); codigos_postales_municipios_espana.xlsx (código INE de cada municipio)."],
]
path = os.path.join(HERE, "..", "salida", "Prioridad_codigos_postales_Espana_29N.xlsx")
with pd.ExcelWriter(path, engine="openpyxl") as w:
    out.to_excel(w, index=False, sheet_name="Códigos postales")
    ws = w.sheets["Códigos postales"]
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="00192C")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 32; ws.freeze_panes = "C2"; ws.auto_filter.ref = ws.dimensions
    W = {"Municipio": 26, "Provincia": 18, "Comunidad": 20, "Cálculo": 34, "Notas": 50}
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = W.get(col[0].value, max(10, min(16, len(str(col[0].value)) + 2)))
    pd.DataFrame(notes).to_excel(w, index=False, header=False, sheet_name="Notas y método")
    wn = w.sheets["Notas y método"]; wn.column_dimensions["A"].width = 120; wn.column_dimensions["B"].width = 12
    for row in wn.iter_rows():
        for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
    wn["A1"].font = Font(name="Arial", bold=True, size=14, color="00192C")
    for c in ("A6", "A14"): wn[c].font = Font(name="Arial", bold=True, color="00192C")
print("ok", len(out), out["Cálculo"].value_counts().to_dict())
print(out["Prioridad en España"].value_counts().to_dict())
print(out["Prioridad en su provincia"].value_counts().to_dict())
