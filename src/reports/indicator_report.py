"""
Informe PDF para datasets de indicadores (p. ej. Salud Mental y Bienestar Docente).

Pensado para datasets que NO usan el esquema (BM) del Observatorio: agrupa los
indicadores por tema (salud mental primero), los explica en lenguaje sencillo y añade
recomendaciones con IA. Complementa a ReportBuilder (esquema de bienestar).
"""
import os
import re
import tempfile

import pandas as pd

from src.core import perezoso
from src.analysis import indicators
from src.docentes import catalogo as cat_doc
from src.docentes import scoring as doc_scoring

plt = perezoso.modulo("matplotlib.pyplot")   # solo al generar el PDF
from src.analysis import grupo_minimo as gm
from src.reports.analytics import apply_report_theme, save_figure_to_bytes, COLORS
from src.reports.pdf_generator import PDFReport
from src.core.ai import generate_analysis


def _theme_name(theme: str) -> str:
    """Nombre del tema sin emoji (para títulos del PDF / latin-1)."""
    return re.sub(r"^[^0-9A-Za-zÁÉÍÓÚÑáéíóúñ]+", "", theme).strip()


def _direction_txt(hib):
    if hib is True:
        return "un valor más alto es mejor"
    if hib is False:
        return "un valor más alto indica más riesgo"
    return "sin dirección definida"


def _theme_bar_chart(items, anclado: bool = False) -> bytes:
    """Barra horizontal 0-100 (orientada a mejor) por indicador.

    Con `anclado` es el % de la escala teórica y el color la zona anclada, igual que el
    dashboard; si no, la posición relativa en la muestra (datasets genéricos)."""
    apply_report_theme()
    items = sorted(items, key=lambda kv: kv[1]["oriented"])
    labels = [i["label"] for _, i in items]
    vals = [i["oriented"] for _, i in items]
    colors = [i["color"] for _, i in items]

    fig, ax = plt.subplots(figsize=(8, max(2.4, len(labels) * 0.5)))
    bars = ax.barh(labels, vals, color=colors, height=0.6, edgecolor="white", linewidth=0.5)
    for b, v in zip(bars, vals):
        ax.text(v + 1.5, b.get_y() + b.get_height() / 2, f"{v:.0f}",
                va="center", ha="left", fontsize=8, fontweight="bold",
                color=COLORS["text_primary"])
    ax.axvline(50, color=COLORS["divider"], lw=1, ls="--", alpha=0.8)
    ax.set_xlim(0, 108)
    ax.set_xlabel("% de la escala teórica (0 = mínimo posible, 100 = máximo; mayor = mejor)"
                  if anclado else "Posición relativa en la muestra (0-100, mayor = mejor)",
                  fontsize=9)
    return save_figure_to_bytes(fig)


class IndicatorReportBuilder:
    LEVEL_WORD = {
        "Favorable": "resultado favorable",
        "Intermedio": "resultado intermedio",
        "Atención": "área que requiere atención",
        "—": "resultado (dirección no definida)",
    }

    def __init__(self, df, title="Informe de Salud Mental y Bienestar Docente",
                 org_name="Institución educativa"):
        self.df = df
        self.title = title
        self.org_name = org_name
        # Archivo de docentes: las MISMAS cifras y zonas que el dashboard
        # (`doc_scoring.para_vistas`). Otros datasets: lectura relativa a la muestra.
        self.anclado = doc_scoring.es_archivo_docentes(df)
        if self.anclado:
            self.enr, _ = doc_scoring.para_vistas(df)
            self.temas_orden = list(cat_doc.TEMAS)
            self.themes = {t: [(c, i) for c, i in self.enr.items() if i["theme"] == t]
                           for t in self.temas_orden}
            self.themes = {t: v for t, v in self.themes.items() if v}
        else:
            self.inds = indicators.detect_indicators(df)
            self.enr = indicators.enrich_indicators(df, self.inds)
            self.temas_orden = indicators.THEMES_ORDER
            self.themes = indicators.by_theme(self.enr)

    def _nivel(self, info) -> str:
        """Favorable / Intermedio / Atención / —, con la zona anclada si es Docentes."""
        if not self.anclado:
            return info["level"]
        return {cat_doc.ZONA_FAVORABLE: "Favorable", cat_doc.ZONA_INTERMEDIA: "Intermedio",
                cat_doc.ZONA_VIGILAR: "Atención"}.get(info["zona"], "—")

    @staticmethod
    def _ic(info) -> str:
        if info.get("ic_inf") is None:
            return ""
        return f" [IC 95 %: {info['ic_inf']:.2f} a {info['ic_sup']:.2f}]"

    def build_report(self, title=None, org_name=None) -> bytes:
        if title:
            self.title = title
        if org_name:
            self.org_name = org_name
        gm.exigir_grupo(len(self.df))      # grupo mínimo de 10

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()
        try:
            pdf = PDFReport(filename=tmp_path, report_title=self.title,
                            org_name=self.org_name, n_participants=len(self.df))
            self._executive(pdf)
            self._demographics(pdf)
            self._themes(pdf)
            self._recommendations(pdf)
            self._methodology(pdf)
            pdf.build_pdf()
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def build(self, title=None, org_name=None) -> bytes:
        return self.build_report(title=title, org_name=org_name)

    # ── Secciones ──────────────────────────────────────────────
    def _mental_health_items(self):
        for theme, items in self.themes.items():
            if theme.startswith("🧠"):
                return items
        return []

    def _executive(self, pdf):
        pdf.add_title("RESUMEN EJECUTIVO", level=1)

        sm = self._mental_health_items()
        aten = [i for _, i in sm if self._nivel(i) == "Atención"]
        fav = [i for _, i in sm if self._nivel(i) == "Favorable"]

        pdf.add_kpi_table([
            ("Docentes evaluados", f"{len(self.df):,}", "personas", "brand_blue"),
            ("Indicadores", str(len(self.enr)), "medidos", "brand_blue"),
            ("Focos de atención", str(len(aten)), "en salud mental", "risk"),
            ("Fortalezas", str(len(fav)), "en salud mental", "strength"),
        ])

        if self.anclado:
            pdf.add_paragraph(
                f"Este informe resume el estado de salud mental y bienestar de "
                f"{len(self.df):,} docentes. Se organizan los resultados por temas, "
                f"comenzando por la salud mental. Cada indicador se ubica en una escala de 0 a "
                f"100 (% de la escala teórica del instrumento, donde un valor más alto siempre "
                f"significa mejor bienestar) y se colorea por zona: favorable, intermedia o a "
                f"vigilar. Son las mismas cifras y zonas que muestra el tablero."
            )
        else:
            pdf.add_paragraph(
                f"Este informe resume el estado de salud mental y bienestar de "
                f"{len(self.df):,} docentes. Se organizan los resultados por temas, "
                f"comenzando por la salud mental. Para cada indicador se muestra su "
                f"posición relativa dentro de este grupo (de 0 a 100, donde un valor más "
                f"alto siempre significa mejor bienestar) y una lectura en lenguaje sencillo."
            )

        if aten:
            worst = min(aten, key=lambda i: i["oriented"])
            pdf.add_insight_box(
                f"Principal foco de atención: {worst['label']}. Es el aspecto de salud "
                f"mental con el resultado menos favorable en este grupo y conviene "
                f"priorizarlo.", tipo="risk")
        elif self.anclado:
            pdf.add_insight_box(
                "Ningún indicador de salud mental está en zona a vigilar.", tipo="strength")
        else:
            pdf.add_insight_box(
                "Ningún indicador de salud mental aparece en zona de atención relativa "
                "dentro de este grupo.", tipo="strength")
        if self.anclado:
            fuera = [i["label"] for i in self.enr.values()
                     if self._nivel(i) == "Atención" and i["theme"] != cat_doc.TEMA_SALUD_MENTAL]
            if fuera:
                pdf.add_insight_box(
                    "También en zona a vigilar: " + ", ".join(fuera) + ".", tipo="risk")
        if fav:
            best = max(fav, key=lambda i: i["oriented"])
            pdf.add_insight_box(
                f"Principal fortaleza: {best['label']}, con el resultado más favorable "
                f"en salud mental.", tipo="strength")

        pdf.add_divider()
        pdf.add_page_break()

    def _demographics(self, pdf):
        pdf.add_title("1. CARACTERIZACIÓN DE LOS PARTICIPANTES", level=1)
        parts = [f"Participaron {len(self.df):,} docentes."]
        edad = next((c for c in self.df.columns if "edad" in c.lower()), None)
        if edad and pd.api.types.is_numeric_dtype(self.df[edad]):
            s = pd.to_numeric(self.df[edad], errors="coerce").dropna()
            if not s.empty:
                parts.append(f"La edad promedio es de {s.mean():.0f} años "
                             f"(rango de {s.min():.0f} a {s.max():.0f}).")
        sexo = next((c for c in self.df.columns if c.lower().endswith("sexo")
                     or c.lower().endswith(")sexo")), None)
        if sexo:
            # Sin conteos menores de 10 ni deducibles por resta (`grupo_minimo`).
            det = gm.texto_conteos(self.df[sexo])
            parts.append(f"Distribución por sexo (según codificación del estudio): {det}.")
            if "<10" in det or "entre " in det:
                parts.append(gm.NOTA_OCULTOS)
        pdf.add_paragraph(" ".join(parts))
        pdf.add_divider()

    def _themes(self, pdf):
        for theme in self.temas_orden:
            items = self.themes.get(theme)
            if not items:
                continue
            name = _theme_name(theme)
            pdf.add_title(name, level=1)

            chart = _theme_bar_chart(items, anclado=self.anclado)
            intro = (f"La siguiente gráfica muestra el % de la escala teórica de cada "
                     f"indicador de «{name}» (0-100; mayor = mejor; verde = zona favorable, "
                     f"ámbar = intermedia, naranja = a vigilar)."
                     if self.anclado else
                     f"La siguiente gráfica muestra la posición relativa de cada "
                     f"indicador de «{name}» dentro de este grupo (0-100; verde = "
                     f"favorable, amarillo = intermedio, rojo = requiere atención).")
            pdf.insert_chart(
                chart,
                intro=intro,
                caption=f"Indicadores de {name}.",
                width_pct=0.9,
            )

            # Lecturas en lenguaje sencillo por indicador
            for _, info in sorted(items, key=lambda kv: kv[1]["oriented"]):
                nivel = self._nivel(info)
                lectura = self.LEVEL_WORD.get(nivel, "resultado")
                tipo = ("risk" if nivel == "Atención"
                        else "strength" if nivel == "Favorable" else "info")
                if self.anclado:
                    extra = "".join(f"; {t}" for t in (
                        f"banda: {info['banda']}" if info.get("banda") else "",
                        "cambió el formulario en 2026" if info.get("aviso_version") else "",
                        info.get("nota") or "") if t)
                    texto = (f"{info['label']}: {lectura} (media {info['mean']:.2f}"
                             f"{self._ic(info)} en una escala de {info['min']:.0f} a "
                             f"{info['max']:.0f}; N={info['n']}; "
                             f"{_direction_txt(info['higher_is_better'])}{extra}).")
                else:
                    texto = (f"{info['label']}: {lectura} (promedio {info['mean']:.1f} en un rango "
                             f"observado de {info['min']:.0f} a {info['max']:.0f}; "
                             f"{_direction_txt(info['higher_is_better'])}).")
                pdf.add_insight_box(texto, tipo=tipo)
            pdf.add_divider()
            pdf.add_page_break()

    def _recommendations(self, pdf):
        pdf.add_title("RECOMENDACIONES", level=1)
        pdf.add_paragraph(
            "Las siguientes recomendaciones se generan con inteligencia artificial a "
            "partir de los resultados, con foco en la salud mental del profesorado.")
        try:
            resumen = "\n".join(
                f"- {i['label']}: promedio {i['mean']:.2f} (escala {i['min']:.0f}-{i['max']:.0f}), "
                f"{i['oriented']:.0f}/100 de la escala, {self._nivel(i)}"
                if self.anclado else
                f"- {i['label']}: promedio {i['mean']:.1f} (rango {i['min']:.0f}-{i['max']:.0f}), "
                f"posición {i['oriented']:.0f}/100, {i['level']}"
                for _, i in sorted(self.enr.items(), key=lambda kv: kv[1]["oriented"]))
            prompt = (
                "Actúa como experto en salud mental ocupacional docente. Con base en estos "
                f"indicadores de {len(self.df)} docentes (posición 0-100 orientada a 'mayor = "
                f"mejor'):\n{resumen}\n\n"
                "Escribe en Markdown, claro y accionable:\n"
                "## Panorama general (2-3 frases sencillas)\n"
                "## Focos prioritarios (los de menor posición)\n"
                "## Recomendaciones (4-5 acciones concretas y viables para la institución)\n"
                "Evita tecnicismos; si citas literatura, hazlo brevemente en formato APA.")
            try:
                from src.ai.knowledge_base import get_cached_kb
                kb = get_cached_kb()
                refs = kb.query_knowledge("salud mental docente estrés burnout intervención", 4) if kb.enabled else ""
                if refs:
                    prompt += f"\n\nCita SOLO estas referencias si aplican:\n{refs}"
            except Exception:                              # noqa: BLE001, S110
                pass                                       # sin base de conocimiento: el informe sale sin citas
            ai_text = generate_analysis(prompt)
            if ai_text and "Error" not in ai_text[:10]:
                pdf.add_markdown(ai_text)
            else:
                pdf.add_insight_box(
                    "No fue posible generar recomendaciones automáticas (verifica la API "
                    "key de Gemini).", tipo="warning")
        except Exception as e:
            pdf.add_insight_box(f"No se pudieron generar recomendaciones: {str(e)[:100]}",
                                tipo="warning")
        pdf.add_divider()

    def _methodology(self, pdf):
        pdf.add_title("NOTA METODOLÓGICA", level=1)
        if self.anclado:
            pdf.add_paragraph(
                "Cada indicador se puntúa desde las respuestas a los ítems, sin imputar datos "
                "faltantes, y se expresa como % de la escala teórica del instrumento (0 = mínimo "
                "posible, 100 = máximo posible), orientado de modo que un valor más alto siempre "
                "sea mejor. La zona (favorable, intermedia o a vigilar) sale del punto de corte "
                "publicado del instrumento o, si no lo hay, del tercio de la escala; no depende "
                "de los demás docentes de la muestra. Son las mismas cifras que muestra el "
                "tablero. Los grupos de menos de 10 docentes no se muestran. No es un "
                "diagnóstico individual.")
            return
        pdf.add_paragraph(
            "La «posición relativa» (0-100) ubica el promedio del grupo dentro del rango "
            "observado en esta misma muestra y se orienta de forma que un valor más alto "
            "siempre indique mejor bienestar. Por lo tanto, los niveles "
            "(Favorable/Intermedio/Atención) son comparaciones internas de este grupo y "
            "NO equivalen a puntos de corte clínicos. La dirección de cada indicador "
            "(si un valor alto es mejor o peor) proviene del catálogo de instrumentos; "
            "los indicadores sin dirección confirmada se muestran de forma neutral.")
