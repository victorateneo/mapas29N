"""Base de prioridades FA 29N en Excel, con fórmulas vivas (pesos y repartos editables en «Método»)."""
import math
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from calculo_prioridades import IN, HERE, run, NIVEL_PROV, ABSOLUTAS, UMBRAL_MEDIA, UMBRAL_BAJA

R = run(IN("prioridades_sscc.xlsx"), IN("Prioridad_provincias_FA_29N_Ateneo.xlsx"), IN("cod_pos_sscc.csv"))
prov, d, mun, cpd = R["prov"], R["secc"], R["mun"], R["cp"]
d = d.sort_values(["cpro", "cumun", "cusec"]).reset_index(drop=True)

F = "Arial"
NAVY, BLUE = "00192C", "0033FF"
H_FILL = PatternFill("solid", fgColor=NAVY)
IN_FILL = PatternFill("solid", fgColor="FFF2CC")
f_base = Font(name=F, size=10)
f_head = Font(name=F, size=10, bold=True, color="FFFFFF")
f_in = Font(name=F, size=10, color="0000FF")
f_title = Font(name=F, size=16, bold=True, color=NAVY)
f_sub = Font(name=F, size=10, color="6C6D6D")
f_bold = Font(name=F, size=10, bold=True, color=NAVY)
thin = Side(style="thin", color="D3D4CF")

wb = Workbook()
wb._named_styles["Normal"].font = Font(name=F, size=10)

def header(ws, row, cols, widths=None):
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=j, value=c)
        cell.font, cell.fill = f_head, H_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[row].height = 30
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w

def nan(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else x

# ── Método ────────────────────────────────────────────────────────────
ws = wb.active; ws.title = "Método"
ws.column_dimensions["A"].width = 2
for c, w in zip("BCDEF", [30, 26, 12, 16, 70]): ws.column_dimensions[c].width = w
ws["B2"] = "PRIORIDADES FA · GENERALES 29N"; ws["B2"].font = f_title
ws["B3"] = "Ateneo del Dato · base para el mapa · celdas en azul sobre amarillo = editables"; ws["B3"].font = f_sub

ws["B5"] = "1. Prioridad provincial y peso"; ws["B5"].font = f_bold
header(ws, 6, [None, "Prioridad provincial", "Peso", "Nº provincias", "Criterio"])
ws.cell(row=6, column=1).fill = PatternFill(None)
crit = ["Decisión del comité: Madrid, Barcelona, Valencia, Alicante",
        "Modelo de escaños: «En el filo», «A por uno más» o «Defender»",
        "El siguiente escaño entra con FA ≤ umbral Media (tabla 2) en voto nacional",
        "El siguiente escaño entra con FA ≤ umbral Baja (tabla 2) en voto nacional",
        "Resto"]
for i, (n, lab, w) in enumerate(NIVEL_PROV):
    r = 7 + i
    ws.cell(row=r, column=2, value=lab).font = f_base
    c = ws.cell(row=r, column=3, value=w); c.font, c.fill, c.number_format = f_in, IN_FILL, "0.00"
    ws.cell(row=r, column=4, value=f'=COUNTIF(Provincias!$F$2:$F$53,B{r})').font = f_base
    ws.cell(row=r, column=5, value=crit[i]).font = f_base
ws["C7"].comment = Comment("Pesos propuestos por Ateneo del Dato (8/11/2026). Multiplican el scoring de cada sección de la provincia.", "Ateneo")

ws["B13"] = "2. Umbrales para Media y Baja"; ws["B13"].font = f_bold
header(ws, 14, [None, "Parámetro", "Valor"])
ws.cell(row=14, column=1).fill = PatternFill(None)
for i, (lab, v) in enumerate([("Media si el siguiente escaño entra con FA ≤", UMBRAL_MEDIA), ("Baja si el siguiente escaño entra con FA ≤", UMBRAL_BAJA)]):
    ws.cell(row=15 + i, column=2, value=lab).font = f_base
    c = ws.cell(row=15 + i, column=3, value=v); c.font, c.fill, c.number_format = f_in, IN_FILL, "0.0%"
ws.cell(row=17, column=2, value="Dato: columna «FA nacional para el siguiente escaño» del modelo (Provincias, col. N).").font = f_sub

ws["B24"] = "3. Reparto de niveles (secciones, municipios y códigos postales)"; ws["B24"].font = f_bold
header(ws, 25, [None, "Prioridad", "% acumulado", "Corte secciones", "Corte municipios"])
ws.cell(row=25, column=1).fill = PatternFill(None)
ws.column_dimensions["F"].width = 70
for i, (lab, cum) in enumerate([("Máxima", 0.10), ("Alta", 0.20), ("Media", 0.40), ("Baja", 0.70)]):
    r = 26 + i
    ws.cell(row=r, column=2, value=lab).font = f_base
    c = ws.cell(row=r, column=3, value=cum); c.font, c.fill, c.number_format = f_in, IN_FILL, "0%"
    ws.cell(row=r, column=4, value=f"=PERCENTILE(Secciones!$K$2:$K${len(d)+1},1-C{r})").number_format = "0.00"
    ws.cell(row=r, column=5, value=f"=PERCENTILE(Municipios!$I$2:$I${len(mun)+1},1-C{r})").number_format = "0.00"
    ws.cell(row=r, column=6, value=f"=PERCENTILE('Códigos postales'!$I$2:$I${len(cpd)+1},1-C{r})").number_format = "0.00"
ws.cell(row=25, column=6, value="Corte códigos postales").font = f_head
ws.cell(row=25, column=6).fill = H_FILL
ws.cell(row=30, column=2, value="Nula").font = f_base
ws.cell(row=30, column=3, value="resto").font = f_base

notes = [
    "4. Cómo se calcula",
    "Scoring final de la sección = scoring original de la sección (prioridades_sscc.xlsx) × peso de su provincia.",
    "Prioridad de la sección: Máxima si está en el 10 % más alto de España, Alta en el siguiente 10 %, Media 20 %, Baja 30 %, Nula el resto (cortes de la tabla 3).",
    "Municipio y código postal: índice = scoring final medio de sus secciones (ponderado por censo) × log10(censo total). Se reescala a 0–10 dividiendo por el máximo.",
    "El logaritmo premia el tamaño sin que las grandes ciudades se lo lleven todo: un municipio de 1 sección con 8 de scoring (≈ 800 electores) da 8 × 2,9 = 23,2; uno de 10 secciones con 7 (≈ 12.000) da 7 × 4,1 = 28,6, y queda por delante.",
    "Las secciones sin scoring en el original (362) quedan como «Sin datos» y no entran en las medias, pero su censo sí cuenta en el tamaño del municipio.",
    "Fuentes: prioridades_sscc.xlsx (scoring por sección, generales 2023 y 2019) · Prioridad_provincias_FA_29N_Ateneo.xlsx, pestaña Ranking (modelo de escaños, 18/10/2026) · cod_pos_sscc.csv (sección → código postal).",
]
for i, t in enumerate(notes):
    c = ws.cell(row=32 + i, column=2, value=t)
    c.font = f_bold if i == 0 else f_base
    if i: ws.merge_cells(start_row=32 + i, start_column=2, end_row=32 + i, end_column=6); c.alignment = Alignment(wrap_text=True, vertical="top"); ws.row_dimensions[32 + i].height = 28

# Referencias a cortes
CUT_S = ["Método!$D$26", "Método!$D$27", "Método!$D$28", "Método!$D$29"]
CUT_M = ["Método!$E$26", "Método!$E$27", "Método!$E$28", "Método!$E$29"]
CUT_C = ["Método!$F$26", "Método!$F$27", "Método!$F$28", "Método!$F$29"]
def prio_formula(cell, cuts):
    return (f'=IF({cell}="","Sin datos",IF({cell}>={cuts[0]},"Máxima",IF({cell}>={cuts[1]},"Alta",'
            f'IF({cell}>={cuts[2]},"Media",IF({cell}>={cuts[3]},"Baja","Nula")))))')

NS = len(d) + 1
# ── Provincias ────────────────────────────────────────────────────────
wp = wb.create_sheet("Provincias")
cols = ["Cód.", "Provincia", "Comunidad", "Categoría del modelo", "Absoluta (comité)", "Prioridad provincial", "Peso",
        "Escaños en juego", "Escaños Sumar 23J", "Escaños FA (base)", "FA % estimado", "Prob. escaño en el filo",
        "Rival siguiente escaño", "FA nacional para el siguiente escaño", "Secciones", "Censo 2023",
        "Scoring final medio", "Secciones Máxima", "Secciones Alta"]
header(wp, 1, cols, [6, 22, 20, 28, 11, 22, 7, 9, 9, 9, 10, 10, 12, 12, 10, 12, 10, 10, 10])
first = d.groupby("cpro")[["prov_n", "ccaa_n"]].first()
for i, (cpro, p) in enumerate(prov.sort_values("rank_modelo").iterrows()):
    r = 2 + i
    vals = [cpro, first.loc[cpro, "prov_n"], first.loc[cpro, "ccaa_n"], p["categoria_modelo"],
            "Sí" if cpro in ABSOLUTAS else "No"]
    for j, v in enumerate(vals, 1): wp.cell(row=r, column=j, value=v).font = f_base
    c = wp.cell(row=r, column=5); c.font, c.fill = f_in, IN_FILL
    wp.cell(row=r, column=6, value=f'=IF(E{r}="Sí","Máxima",IF(OR(D{r}="En el filo",D{r}="A por uno más",D{r}="Defender"),"Alta",IF(AND(N{r}<>"",N{r}<=Método!$C$15),"Media",IF(AND(N{r}<>"",N{r}<=Método!$C$16),"Baja","Nula"))))')
    wp.cell(row=r, column=7, value=f"=INDEX(Método!$C$7:$C$11,MATCH(F{r},Método!$B$7:$B$11,0))").number_format = "0.00"
    for j, k in enumerate(["escanos", "esc23", "esc_fa", "fa_est", "p_filo", "rival", "fa_nac_sig"], 8):
        c = wp.cell(row=r, column=j, value=nan(p[k]))
        if k in ("fa_est", "p_filo", "fa_nac_sig"): c.number_format = "0.0%"
    wp.cell(row=r, column=15, value=f"=COUNTIF(Secciones!$D$2:$D${NS},A{r})")
    wp.cell(row=r, column=16, value=f"=SUMIF(Secciones!$D$2:$D${NS},A{r},Secciones!$H$2:$H${NS})").number_format = "#,##0"
    wp.cell(row=r, column=17, value=f"=SUMIF(Secciones!$D$2:$D${NS},A{r},Secciones!$M$2:$M${NS})/SUMIF(Secciones!$D$2:$D${NS},A{r},Secciones!$N$2:$N${NS})").number_format = "0.00"
    wp.cell(row=r, column=18, value=f'=COUNTIFS(Secciones!$D$2:$D${NS},A{r},Secciones!$L$2:$L${NS},"Máxima")')
    wp.cell(row=r, column=19, value=f'=COUNTIFS(Secciones!$D$2:$D${NS},A{r},Secciones!$L$2:$L${NS},"Alta")')
    for j in range(6, 20): wp.cell(row=r, column=j).font = f_base
wp.freeze_panes = "C2"; wp.auto_filter.ref = f"A1:S{len(prov)+1}"
wp.cell(row=len(prov) + 3, column=2, value="Fuente: Prioridad_provincias_FA_29N_Ateneo.xlsx (Ranking, escenario base, 18/10/2026). «Absoluta» marcada por el comité (8/11/2026).").font = f_sub

# ── Secciones ─────────────────────────────────────────────────────────
wsec = wb.create_sheet("Secciones")
cols = ["Sección", "Comunidad", "Provincia", "Cód. prov.", "Municipio", "Cód. municipio", "Código postal", "Censo 2023",
        "Scoring sección", "Peso provincial", "Scoring final", "Prioridad", "Scoring × censo", "Censo con scoring",
        "1.º en 2023", "% Sumar 2023", "% PSOE 2023", "% Derechas 2023"]
header(wsec, 1, cols, [12, 18, 18, 7, 22, 10, 9, 9, 9, 9, 9, 10, 11, 10, 10, 9, 9, 9])
for i, t in enumerate(d.itertuples(index=False)):
    r = 2 + i
    row = [t.cusec, t.ccaa_n, t.prov_n, t.cpro, t.mun_n, t.cumun, nan(t.cp), nan(t.censo23), nan(t.score_orig)]
    for j, v in enumerate(row, 1): wsec.cell(row=r, column=j, value=v)
    wsec.cell(row=r, column=10, value=f"=INDEX(Provincias!$G$2:$G$53,MATCH(D{r},Provincias!$A$2:$A$53,0))")
    wsec.cell(row=r, column=11, value=f'=IF(I{r}="","",I{r}*J{r})')
    wsec.cell(row=r, column=12, value=prio_formula(f"K{r}", CUT_S))
    wsec.cell(row=r, column=13, value=f'=IF(K{r}="",0,K{r}*H{r})')
    wsec.cell(row=r, column=14, value=f'=IF(K{r}="",0,H{r})')
vcols = {"Vencedor Generales": 15, "% Sumar": 16, "% Psoe": 17, "% Derechas": 18}
for name, j in vcols.items():
    for i, v in enumerate(d[name].tolist()):
        wsec.cell(row=2 + i, column=j, value=nan(v))
for col, fmt in [(8, "#,##0"), (9, "0.00"), (10, "0.00"), (11, "0.00"), (13, "#,##0"), (14, "#,##0")]:
    for r in range(2, NS + 1): wsec.cell(row=r, column=col).number_format = fmt
wsec.freeze_panes = "B2"; wsec.auto_filter.ref = f"A1:R{NS}"

# ── Municipios y CP (agregados con SUMIF sobre Secciones) ─────────────
def agg_sheet(title, key_col, rows, keys_meta, extra_cols, extra_widths):
    w = wb.create_sheet(title)
    n = len(rows) + 1
    cols = extra_cols + ["Secciones", "Censo 2023", "Scoring final medio", "Índice bruto", "Índice (0–10)", "Prioridad",
                         "Secciones Máxima o Alta"]
    header(w, 1, cols, extra_widths + [9, 11, 10, 10, 10, 10, 10])
    k = len(extra_cols)
    L = lambda off: get_column_letter(k + off)
    for i, vals in enumerate(rows):
        r = 2 + i
        for j, v in enumerate(vals, 1): w.cell(row=r, column=j, value=v)
        rng = f"Secciones!${key_col}$2:${key_col}${NS}"
        w.cell(row=r, column=k + 1, value=f"=COUNTIF({rng},A{r})")
        w.cell(row=r, column=k + 2, value=f"=SUMIF({rng},A{r},Secciones!$H$2:$H${NS})").number_format = "#,##0"
        w.cell(row=r, column=k + 3, value=f'=IFERROR(SUMIF({rng},A{r},Secciones!$M$2:$M${NS})/SUMIF({rng},A{r},Secciones!$N$2:$N${NS}),"")').number_format = "0.00"
        w.cell(row=r, column=k + 4, value=f'=IF(OR({L(3)}{r}="",{L(2)}{r}<=1),"",{L(3)}{r}*LOG10({L(2)}{r}))').number_format = "0.00"
        w.cell(row=r, column=k + 5, value=f'=IF({L(4)}{r}="","",10*{L(4)}{r}/MAX(${L(4)}$2:${L(4)}${n}))').number_format = "0.00"
        w.cell(row=r, column=k + 7, value=f'=COUNTIFS({rng},A{r},Secciones!$L$2:$L${NS},"Máxima")+COUNTIFS({rng},A{r},Secciones!$L$2:$L${NS},"Alta")')
    return w, n, L

mrows = [[k, v["mun_n"], v["prov_n"], v["ccaa_n"]] for k, v in mun.sort_values("indice", ascending=False).iterrows()]
wm, nm, Lm = agg_sheet("Municipios", "F", mrows, None, ["Cód. municipio", "Municipio", "Provincia", "Comunidad"], [10, 26, 18, 18])
for r in range(2, nm + 1): wm.cell(row=r, column=10, value=prio_formula(f"I{r}", CUT_M))
wm.freeze_panes = "C2"; wm.auto_filter.ref = f"A1:K{nm}"

crows = [[k, v["municipio"], v["provincia"], int(v["n_mun"])] for k, v in cpd.sort_values("indice", ascending=False).iterrows()]
wc, nc, Lc = agg_sheet("Códigos postales", "G", crows, None, ["Código postal", "Municipio principal", "Provincia", "Nº municipios"], [10, 26, 18, 9])
for r in range(2, nc + 1): wc.cell(row=r, column=10, value=prio_formula(f"I{r}", CUT_C))
wc.freeze_panes = "B2"; wc.auto_filter.ref = f"A1:K{nc}"

wb.save(os.path.join(HERE, "..", "salida", "Prioridades_FA_29N_base.xlsx"))
print("ok", len(d), len(mun), len(cpd))
