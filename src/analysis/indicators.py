"""
Detección y resumen de indicadores para datasets genéricos (no de bienestar laboral).

Cuando un dataset no usa el esquema (BM) del Observatorio (p. ej. baterías con totales
de subescala precalculados: PSS_T, IRI_*_Total, ERS_*_T…), se tratan esas columnas como
"indicadores" y se resumen de forma neutral (media, DE, rango, N). No se asume dirección
de riesgo/bienestar sin codebook: la interpretación se deja al usuario / a la IA.
"""
import re
import pandas as pd

from src.data.processor import is_protected_column

_TOTAL_RE = re.compile(r"(_T$|_Total$|_TOTAL$|_total$)")

# ── Catálogo de indicadores (etiqueta, tema y dirección) ─────────
# higher_is_better: True (mayor = mejor), False (mayor = peor/riesgo), None (sin definir).
# Basado en convenciones de los instrumentos; editable para ajustarse a tu codebook.
# Ver docs/GUIA_DATASETS.md.
THEMES_ORDER = [
    "🧠 Salud mental y estrés",
    "😊 Bienestar laboral",
    "🛠️ Recursos del trabajo",
    "💗 Empatía y regulación emocional",
    "📊 Otros indicadores",
]

INDICATOR_CATALOG = {
    # Salud mental y estrés
    "PSS":         ("Estrés percibido (PSS)", "🧠 Salud mental y estrés", False),
    "BTA":         ("Burnout / Agotamiento", "🧠 Salud mental y estrés", False),
    "BLG_Som":     ("Somatización", "🧠 Salud mental y estrés", False),
    "BLG_Desg":    ("Desgaste", "🧠 Salud mental y estrés", False),
    "BLG_Alie":    ("Alienación", "🧠 Salud mental y estrés", False),
    "BLG_Psicoso": ("Bienestar psicosocial", "🧠 Salud mental y estrés", True),
    # Bienestar laboral
    "Sat":         ("Satisfacción laboral", "😊 Bienestar laboral", True),
    "Comp":        ("Compromiso (engagement)", "😊 Bienestar laboral", True),
    "DefO":        ("Defensa de la organización", "😊 Bienestar laboral", True),
    "IR":          ("Intención de retiro", "😊 Bienestar laboral", False),
    # Recursos psicosociales del trabajo
    "MT":          ("Manejo/control del tiempo", "🛠️ Recursos del trabajo", True),
    "CL":          ("Compromiso del líder", "🛠️ Recursos del trabajo", True),
    "AP":          ("Apoyo de compañeros", "🛠️ Recursos del trabajo", True),
    "CR":          ("Claridad de rol", "🛠️ Recursos del trabajo", True),
    "CO":          ("Cambio organizacional", "🛠️ Recursos del trabajo", True),
    "RO":          ("Responsabilidad organizacional", "🛠️ Recursos del trabajo", True),
    # Empatía y regulación emocional
    "IRI_PT":      ("Empatía: toma de perspectiva", "💗 Empatía y regulación emocional", True),
    "IRI_EC":      ("Empatía: preocupación empática", "💗 Empatía y regulación emocional", True),
    "ERS_CLA":     ("Regulación emocional: claridad", "💗 Empatía y regulación emocional", None),
    "ERS_CON":     ("Regulación emocional (CON)", "💗 Empatía y regulación emocional", None),
    "ERS_ACP":     ("Regulación emocional (ACP)", "💗 Empatía y regulación emocional", None),
    "ERS_MET":     ("Regulación emocional (MET)", "💗 Empatía y regulación emocional", None),
    # Otros
    "PRPS_CE":     ("PRPS — Conflicto/estrés", "📊 Otros indicadores", None),
    "PRPS_Fam":    ("PRPS — Familiar", "📊 Otros indicadores", None),
    "Descon":      ("Desconexión", "📊 Otros indicadores", None),
}


def _base_key(col: str) -> str:
    return _TOTAL_RE.sub("", str(col)).strip()


def catalog_entry(col: str):
    """(label, theme, higher_is_better) para un indicador; genérico si no está catalogado."""
    key = _base_key(col)
    if key in INDICATOR_CATALOG:
        return INDICATOR_CATALOG[key]
    return (key.replace("_", " "), "📊 Otros indicadores", None)


def is_wellbeing_dataset(df: pd.DataFrame) -> bool:
    """True si el dataset usa el esquema de dimensiones (BM) del Observatorio."""
    return any("(BM),(" in str(c) for c in df.columns)


def detect_indicators(df: pd.DataFrame) -> list:
    """Devuelve las columnas-indicador de un dataset genérico.

    Prioriza los totales precalculados (*_T / *_Total). Si no hay, cae a columnas
    numéricas de tipo escala (rango acotado), excluyendo identificadores.
    """
    if df is None or df.empty:
        return []

    totals = [c for c in df.columns
              if _TOTAL_RE.search(str(c)) and pd.api.types.is_numeric_dtype(df[c])]
    if totals:
        return totals

    out = []
    for c in df.columns:
        if is_protected_column(c) or not pd.api.types.is_numeric_dtype(df[c]):
            continue
        s = df[c].dropna()
        if s.empty:
            continue
        rng = float(s.max() - s.min())
        if 1 <= rng <= 80 and s.nunique() <= 60:
            out.append(c)
    return out


def indicator_stats(df: pd.DataFrame, cols: list) -> dict:
    """Estadísticos descriptivos por indicador."""
    rows = {}
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if s.empty:
            continue
        n = int(s.shape[0])
        rows[c] = {
            "mean": float(s.mean()),
            "std": float(s.std(ddof=1)) if n > 1 else 0.0,
            "min": float(s.min()),
            "max": float(s.max()),
            "n": n,
        }
    return rows


def enrich_indicators(df: pd.DataFrame, cols: list) -> dict:
    """Indicadores con etiqueta, tema, dirección y posición relativa (0-100) en la muestra.

    La posición relativa se calcula sobre el rango observado y, cuando se conoce la
    dirección, se orienta a "mayor = mejor". El 'nivel' (Favorable/Intermedio/Atención)
    es RELATIVO a esta muestra, no un punto de corte clínico.
    """
    base = indicator_stats(df, cols)
    out = {}
    for c, v in base.items():
        label, theme, hib = catalog_entry(c)
        mn, mx = v["min"], v["max"]
        pct = (v["mean"] - mn) / (mx - mn) * 100 if mx > mn else 50.0
        oriented = (100 - pct) if hib is False else pct
        if hib is None:
            level, color = "—", "#5F6368"
        elif oriented >= 66:
            level, color = "Favorable", "#1A7F4B"
        elif oriented <= 33:
            level, color = "Atención", "#C0392B"
        else:
            level, color = "Intermedio", "#B07D0D"
        out[c] = {**v, "label": label, "theme": theme, "higher_is_better": hib,
                  "pct": pct, "oriented": oriented, "level": level, "color": color}
    return out


def by_theme(enriched: dict) -> dict:
    """Agrupa indicadores enriquecidos por tema, en el orden de THEMES_ORDER."""
    groups = {t: [] for t in THEMES_ORDER}
    for col, info in enriched.items():
        groups.setdefault(info["theme"], []).append((col, info))
    return {t: v for t, v in groups.items() if v}
