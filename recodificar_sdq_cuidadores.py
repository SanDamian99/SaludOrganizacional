"""
Recodifica el SDQ del dataset procesado de cuidadores (Datos_Cuidador_AUDIT.xlsx) usando el crudo
como referencia, y genera un dataset analítico limpio para el Observatorio 360.

Por qué: el archivo procesado usa mapas ítem-específicos heredados del archivo legado que
permutan las categorías (valores 0-3 en un instrumento 0-2) y su TOTAL suma los 25 ítems.
Cómo: para cada ítem se infiere la permutación categoría->código que reproduce las frecuencias
del crudo (bloque hijo 1 + bloque hijo 2), se aplica el algoritmo estándar del SDQ y se recalculan
subescalas. Ver docs/METODOLOGIA_PUNTAJES.md (sección Familias) cuando exista.
"""
import itertools, unicodedata, sys
import numpy as np, pandas as pd

BASE = "/Users/joseamorocho/Downloads/Preprocesamiento 360"
RAW = f"{BASE}/data/Cuidando al Cuidador - Parentalidad y bienestar (respuestas).xlsx"
PROC = f"{BASE}/output/Datos_Cuidador_AUDIT.xlsx"
OUT = sys.argv[1] if len(sys.argv) > 1 else "Datos_Cuidador_corregido.csv"

SDQ_MAP = {"no es cierto": 0, "un tanto cierto": 1, "absolutamente cierto": 2}
REVERSE = {7, 11, 14, 21, 25}
SUB = {"Emo": [3, 8, 13, 16, 24], "Con": [5, 7, 12, 18, 22], "Hip": [2, 10, 15, 21, 25],
       "Pares": [6, 11, 14, 19, 23], "Pro": [1, 4, 9, 17, 20]}

def norm(s):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(ch)).lower().strip()

raw = pd.read_excel(RAW)
c = pd.read_excel(PROC)
cols = list(raw.columns)
i_end = cols.index("¿Desea usted responder estas últimas preguntas sobre otro de sus hijos?")
sdq1 = cols[i_end - 25:i_end]
sdq2 = [x for x in cols if x.startswith("De las siguientes afirmaciones")]
mask2 = raw[cols[i_end]].astype(str).str.strip().str.lower().eq("sí")
proc_sdq = [x for x in c.columns if x.startswith("[")]
assert len(sdq1) == len(sdq2) == len(proc_sdq) == 25

fixed = pd.DataFrame(index=c.index)
log = []
for k in range(25):
    r1 = raw[sdq1[k]].map(lambda v: SDQ_MAP.get(norm(v), np.nan))
    r2 = raw.loc[mask2, sdq2[k]].map(lambda v: SDQ_MAP.get(norm(v), np.nan))
    raw_counts = pd.concat([r1, r2]).value_counts().reindex([0, 1, 2], fill_value=0).values
    p = c[proc_sdq[k]]
    best = None
    for perm in itertools.permutations(sorted(p.unique()), 3):
        cnt = np.array([(p == perm[j]).sum() for j in range(3)])
        err = int(np.abs(cnt - raw_counts).sum())
        if best is None or err < best[0]:
            best = (err, perm)
    err, perm = best
    inv = {perm[j]: j for j in range(3)}
    fixed[f"SDQ{k+1}"] = p.map(inv).astype("Int64")
    log.append((k + 1, err, dict(inv)))
    assert err <= 2, f"Ítem {k+1}: la permutación no reproduce el crudo (err={err})"

# Puntuación estándar
S = fixed.copy()
for r in REVERSE:
    S[f"SDQ{r}"] = 2 - S[f"SDQ{r}"]
for name, items in SUB.items():
    fixed[f"SDQ_{name}_T"] = S[[f"SDQ{i}" for i in items]].sum(axis=1)
fixed["SDQ_Dif_T"] = fixed[["SDQ_Emo_T", "SDQ_Con_T", "SDQ_Hip_T", "SDQ_Pares_T"]].sum(axis=1)
fixed["SDQ_Int_T"] = fixed["SDQ_Emo_T"] + fixed["SDQ_Pares_T"]
fixed["SDQ_Ext_T"] = fixed["SDQ_Con_T"] + fixed["SDQ_Hip_T"]
fixed["SDQ_Dif_Banda"] = pd.cut(fixed["SDQ_Dif_T"], [-1, 13, 16, 19, 40],
                                labels=["Promedio", "Ligeramente elevado", "Alto", "Muy alto"]).astype(str)

# Dataset analítico
out = c.drop(columns=["diferente_si_o_no", "detalle_discrepancia", "TOTAL"] + proc_sdq)
out = out.rename(columns={"Indique su nombre completo": "ID_Cuidador",
                          "Nombre completo de su hijo(a)": "ID_Niño",
                          "Sexo del niÃ±o(a)": "Sexo del niño",
                          "Edad del padre en nÃºmeros (ej. 40)": "Edad del padre",
                          "Barro_Riñas": "Barrio_Riñas"})
out["Barrio_Riesgo_T"] = out[["Barrio_Drogas", "Barrio_Delicuencia", "Barrio_Riñas",
                              "Barrio_Asesinatos", "Barrio_Pandillas"]].sum(axis=1)
out["Barrio_Riesgo_Alto"] = (out[["Barrio_Drogas", "Barrio_Delicuencia", "Barrio_Riñas",
                                  "Barrio_Asesinatos", "Barrio_Pandillas"]] == 2).any(axis=1).astype(int)
out["Edad_4_17"] = out["Edad del niño"].between(4, 17).astype(int)
out = pd.concat([out, fixed], axis=1)
out.to_csv(OUT, index=False, encoding="utf-8")
print(f"OK -> {OUT}  filas={len(out)} columnas={out.shape[1]}")
print("errores de emparejamiento por ítem (2 = las dos filas que el pipeline descartó):", [e for _, e, _ in log])
print("SDQ_Dif_T media", round(out["SDQ_Dif_T"].mean(), 2), "| % >=17:", round((out["SDQ_Dif_T"] >= 17).mean() * 100, 1))
