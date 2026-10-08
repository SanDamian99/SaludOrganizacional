"""
Paquete local de la Triangulación 360: tablas, figuras y metodología.

Todo sale de un `pipeline.Triangulacion`, que solo tiene agregados. Nada de
esto sube a Supabase ni se publica: el ZIP se descarga en la máquina local.

Figuras (matplotlib, sin estado global: `matplotlib.figure.Figure`):
  · `capa1_<colegio>.png`: d con su IC por constructo, coloreado por actor.
  · `bland_altman_<subescala>.png`: Bland–Altman AGRUPADO (cada punto es un
    grupo de ≥ 10 díadas de ≥ 10 familias), con la diferencia media y los
    límites de acuerdo. Ninguna díada se dibuja.

`metodologia.md` es una plantilla fija: solo se rellenan conteos agregados.
"""
from __future__ import annotations

import datetime as _dt
import io
import zipfile

import pandas as pd

from src.triangulacion import catalogo as cat
from src.triangulacion import enlace as en

TABLAS = ("capa1_diferencias.csv", "capa1_clasificacion.csv", "capa1_por_grado.csv",
          "capa1_clasificacion_grado.csv", "enlace_calidad.csv", "diadas_acuerdo_sdq.csv",
          "diadas_bland_altman_agrupado.csv", "diadas_malestar_no_visto.csv",
          "diadas_apoyo_familiar.csv", "diadas_asociaciones.csv",
          "diadas_acuerdo_sdq_concordantes.csv")
COLORES = {"Estudiantes": "#3b6ea8", "Cuidadores": "#b5651d", "Docentes": "#4d8b55"}
# Columnas que nunca salen, aunque una tabla las trajera.
PROHIBIDAS = ("familia", "ID_cuidador", "ID_nino", "N_hmac", "ID", "casos")


def _limpia(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df.drop(columns=[c for c in PROHIBIDAS if c in df.columns])


def _csv(df: pd.DataFrame | None) -> str:
    df = _limpia(df)
    return "" if df.empty else df.to_csv(index=False)


def tablas(t) -> dict[str, pd.DataFrame]:
    c, d = t.capa1, t.diadas
    return {
        "capa1_diferencias.csv": c.diferencias, "capa1_clasificacion.csv": c.clasificacion,
        "capa1_por_grado.csv": c.por_grado, "capa1_clasificacion_grado.csv": c.clasificacion_grado,
        "enlace_calidad.csv": en.tabla_calidad(t.enlace),
        "diadas_acuerdo_sdq.csv": d.acuerdo, "diadas_bland_altman_agrupado.csv": d.bland_altman,
        "diadas_malestar_no_visto.csv": d.no_visto, "diadas_apoyo_familiar.csv": d.apoyo,
        "diadas_asociaciones.csv": d.asociaciones,
        "diadas_acuerdo_sdq_concordantes.csv": d.acuerdo_concordantes,
    }


# ── figuras ────────────────────────────────────────────────────────────────
def figura_capa1(t, colegio: str):
    from matplotlib.figure import Figure
    dif = t.capa1.diferencias
    sub = dif[(dif["grupo"] == colegio) & dif["d"].notna()] if not dif.empty else dif
    fig = Figure(figsize=(8, max(2.5, 0.42 * len(sub) + 1)))
    ax = fig.add_subplot(111)
    if sub.empty:
        ax.text(0.5, 0.5, "Sin cifras para mostrar", ha="center", va="center")
        ax.set_axis_off()
        return fig
    y = list(range(len(sub)))[::-1]
    for yi, (_, f) in zip(y, sub.iterrows()):
        color = COLORES.get(f["actor"], "#555555")
        ax.errorbar(f["d"], yi, xerr=[[f["d"] - f["ic_inf"]], [f["ic_sup"] - f["d"]]],
                    fmt="o", color=color, capsize=3)
    ax.axvline(0, color="#999999", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{f['actor']}: {f['constructo']}" for _, f in sub.iterrows()],
                       fontsize=7)
    ax.set_xlabel("Diferencia con el resto del municipio (DE del actor), IC 95 %")
    ax.set_title(f"{colegio}: cada actor frente al resto de su actor", fontsize=10)
    fig.tight_layout()
    return fig


def figura_bland_altman(t, subescala: str):
    from matplotlib.figure import Figure
    ba = t.diadas.bland_altman
    sub = ba[ba["subescala"] == subescala] if not ba.empty else ba
    acuerdo = t.diadas.acuerdo
    fila = (acuerdo[acuerdo["subescala"] == subescala].iloc[0]
            if not acuerdo.empty and (acuerdo["subescala"] == subescala).any() else None)
    fig = Figure(figsize=(6.5, 4))
    ax = fig.add_subplot(111)
    if sub.empty or fila is None or pd.isna(fila.get("dif_media")):
        ax.text(0.5, 0.5, "Sin cifras para mostrar", ha="center", va="center")
        ax.set_axis_off()
        return fig
    ax.errorbar(sub["promedio_informantes"], sub["dif_media"],
                yerr=[sub["dif_media"] - sub["ic_inf"], sub["ic_sup"] - sub["dif_media"]],
                fmt="s", color="#3b6ea8", capsize=3, label="Grupo de ≥ 10 díadas (IC 95 %)")
    ax.axhline(fila["dif_media"], color="#333333", linewidth=1.2, label="Diferencia media")
    for lim in ("ba_lim_inf", "ba_lim_sup"):
        ax.axhline(fila[lim], color="#b5651d", linestyle="--", linewidth=1)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_xlabel("Promedio de los dos informantes (grupo)")
    ax.set_ylabel("Niño − cuidador")
    ax.set_title(f"Bland–Altman agrupado · {fila['escala']}", fontsize=10)
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    return fig


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    return buf.getvalue()


# ── textos ─────────────────────────────────────────────────────────────────
def metodologia_md(t) -> str:
    inf = t.enlace or {}
    actores = "; ".join(f"{k}: {en.conteo_legible(v)}" for k, v in (t.actores or {}).items())
    calidad = en.tabla_calidad(inf)
    lineas_calidad = [f"- {r.indicador}: {r.valor}" for r in calidad.itertuples()]
    lineas = [
        "# Metodología · Triangulación 360 (fase 5, solo local)", "",
        "## Alcance", "",
        "Solo para el equipo investigador y solo en la máquina que procesa los formularios. "
        "Nada de este paquete sube a Supabase ni se publica. " + cat.AVISO_TEXTOS, "",
        f"Personas analizadas: {actores or '—'}.", "",
        "## Capa 1 · por colegio y por grado", "",
        cat.AVISO_ECOLOGICO.format(n=t.n_colegios), "",
        f"Colegios: {', '.join(t.capa1.colegios) or '—'} (publicables en estudiantes, "
        "cuidadores y docentes a la vez). Cuidadores: solo los de niños en los grados del "
        "estudio; el mínimo cuenta cuidadores distintos.", "",
        "d = (media del grupo − media del resto) / DE individual del actor; IC del 95 % "
        "= d ± 1,96 · √(s²₁/n₁ + s²₂/n₂) / DE. En los constructos binarios la media es una "
        "proporción y se muestra como %.", "",
        cat.AVISO_RESTO, "",
        "Átomos: exactamente las unidades que publica el módulo de cada actor. "
        "Estudiantes: la base publicable de cada nivel por separado (celdas colegio × grado "
        "con 10 o más, colegios publicados enteros y el resto R de ese nivel solo si el "
        "nivel lo incluye). Cuidadores: la base del marco completo, y el filtro de los "
        "grados del estudio quita átomos enteros (los que tienen alguna fila fuera de esos "
        "grados). Docentes: los colegios con 10 o más y R. Por constructo, un átomo con 1 a "
        "9 unidades con dato, o con menos de 3 casos o no casos, sale: toda suma o resta de "
        "cifras mostradas aquí o publicadas por los módulos es unión de átomos que cumplen "
        "la regla.", "",
        cat.AVISO_CLASIFICACION, "", cat.AVISO_COOCURRENCIA, "", cat.AVISO_GRADO, "",
        "Docentes: archivo codificado por scripts/preparar_docentes.py; colegio unido con "
        "core.colegios.codigo_desde_nombre. Clima laboral = apoyo del líder (7 ítems, 0–5); "
        "apoyo percibido = apoyo de compañeros (3 ítems, 0–5); PSS-10 (0–40, prorrateo con 9 "
        "de 10); desgaste (4 ítems, 1–7).", "",
        "## Capa 2 · díadas niño–cuidador", "",
        cat.AVISO_ENLACE, "", *lineas_calidad, "",
        cat.AVISO_DIADAS, "",
        f"- Acuerdo SDQ por subescala: Spearman y Pearson (IC de Fisher), CCI(A,1) de McGraw "
        f"y Wong y kappa ponderado lineal sobre 4 bandas (IC percentil con {cat.N_BOOT} "
        "remuestreos de familias), diferencia media niño − cuidador (IC por errores "
        "agrupados por familia) y límites de Bland–Altman (± 1,96 DE). " + cat.AVISO_SDQ,
        "- " + cat.AVISO_BLAND_ALTMAN,
        "- «Malestar que el cuidador no ve»: el niño en banda alta o muy alta de su "
        "autoinforme o con la señal de malestar (3 o más de 6 ítems «muy cierto»), y el "
        "cuidador lo ubica en «cercano al promedio» con las bandas de padres. Se publica "
        "solo si las tres partes (sin malestar, visto, no visto) tienen 3 o más díadas y "
        "familias, y no más de n − 3. IC de Wilson.",
        "- MSPSS por fuente: Spearman y diferencia media. " + cat.AVISO_MSPSS,
        "- " + cat.AVISO_ASOCIACIONES + " Resultados estandarizados (z); predictores "
        "continuos en z y castigo físico como 0/1; un predictor binario exige 10 o más "
        "díadas y familias en cada nivel. q de Benjamini–Hochberg por muestra.",
        "- " + cat.AVISO_SENSIBILIDAD_CONCORDANCIA, "",
        "## Límites", "",
        "- Enlace exacto: un nombre escrito distinto en los dos formularios no enlaza; las "
        "díadas no son una muestra aleatoria de los niños.",
        "- Cada cuidador aporta su respuesta más reciente; si respondió en dos olas, la del "
        "niño puede ser de otra ola.",
        "- La protección contra restas cubre la triangulación junto con lo que publican los "
        "módulos de estudiantes y cuidadores (auditoría lineal en las pruebas); no cubre "
        "otras vistas locales.",
    ]
    return "\n".join(lineas) + "\n"


def version_txt(t) -> str:
    return "\n".join([
        "Triangulación 360 · versión del análisis",
        f"Fecha: {_dt.date.today().isoformat()}",
        f"Colegios en la capa 1: {', '.join(t.capa1.colegios) or '—'}",
        f"Grados en la capa 1: {', '.join(t.capa1.grados) or '—'}",
        f"Díadas: {en.conteo_legible(t.diadas.n)} · familias: "
        f"{en.conteo_legible(t.diadas.familias)}",
        f"Remuestreos bootstrap: {cat.N_BOOT}",
    ]) + "\n"


def archivos(t) -> dict[str, object]:
    salida: dict[str, object] = {n: _csv(df) for n, df in tablas(t).items()}
    for colegio in t.capa1.colegios:
        salida[f"figuras/capa1_{colegio}.png"] = _png(figura_capa1(t, colegio))
    ba = t.diadas.bland_altman
    for s in (ba["subescala"].unique() if not ba.empty else []):
        salida[f"figuras/bland_altman_{s}.png"] = _png(figura_bland_altman(t, s))
    salida["metodologia.md"] = metodologia_md(t)
    salida["version_analisis.txt"] = version_txt(t)
    return salida


def paquete_zip(t) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in archivos(t).items():
            if contenido:
                z.writestr(nombre, contenido)
    return buf.getvalue()
