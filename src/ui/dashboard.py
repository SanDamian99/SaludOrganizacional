"""
Dashboard dual — Observatorio de Salud Organizacional.

Vista EJECUTIVA (KPIs, semáforo, alertas, fortalezas/riesgos) para directivos y
vista ACADÉMICA (α de Cronbach, tablas, correlación entre dimensiones, comparativas
por grupo con N) para investigación. Todos los puntajes provienen de src.analysis.scoring
(orientados a bienestar: mayor = mejor).
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.core.config import DATA_DICTIONARY, get_scale_range
from src.core.state import get_processed_data
from src.analysis import scoring, indicators
from src.ai.gemini_client import get_cached_client
from src.ui.components.filtering import render_filtering_sidebar

SEM_COLORS = {"green": "#1A7F4B", "yellow": "#B07D0D", "red": "#C0392B", "grey": "#5F6368"}
ESTADO_ICON = {"Fortaleza": "🟢", "Intermedio": "🟡", "Riesgo": "🔴", "Sin Datos": "⚪"}


# ── Cálculos cacheados ──────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _scores(df):
    return scoring.compute_dimension_scores(df)


@st.cache_data(show_spinner=False)
def _dim_score_matrix(df):
    """DataFrame de puntajes orientados por respondiente (columnas = acrónimos)."""
    data = {}
    for dim, info in scoring.compute_dimension_scores(df).items():
        cols = scoring.dimension_columns(df, dim)
        if cols:
            data[info.get("acronimo") or dim[:6]] = scoring.orient_items(df, dim, cols).mean(axis=1)
    return pd.DataFrame(data)


def _norm(info):
    mn, mx = info["scale_min"], info["scale_max"]
    return (info["score"] - mn) / (mx - mn) * 100 if mx > mn else 0.0


# ── Compatibilidad (utilidades usadas por tests y vistas) ───────
def get_dimension_average(df, dim_name):
    """Media CRUDA (sin orientar) de una dimensión y sus columnas. (avg, cols)."""
    dims = DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {})
    cfg = dims.get(dim_name)
    if not cfg:
        return None, []
    questions = cfg.get("Preguntas", [])
    valid = [c for c in df.columns if c in questions and pd.api.types.is_numeric_dtype(df[c])]
    if not valid:
        return None, []
    return df[valid].mean(axis=1).mean(), valid


def render_tank(value, left_label, right_label, min_val=1, max_val=7):
    """Visualización tipo 'tanque' para diferencial semántico."""
    pct = (value - min_val) / (max_val - min_val) * 100 if max_val > min_val else 0
    color = "#C0392B" if pct < 33 else "#B07D0D" if pct < 66 else "#1A7F4B"
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[max_val], y=[""], orientation="h",
                         marker_color="lightgrey", opacity=0.3, hoverinfo="none"))
    fig.add_trace(go.Bar(x=[value], y=[""], orientation="h", marker_color=color,
                         text=f"{value:.2f}", textposition="auto"))
    fig.update_layout(
        title=dict(text=f"{left_label} ↔ {right_label}", x=0.5, xanchor="center"),
        xaxis=dict(range=[0, max_val + 0.5], visible=False),
        yaxis=dict(visible=False), height=90, barmode="overlay",
        margin=dict(l=20, r=20, t=40, b=10), showlegend=False)
    return fig


# ── Componentes visuales ────────────────────────────────────────
def render_gauge(value, title, mn=1, mx=7, color="#2E5FAC"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": f" / {mx:.0f}", "font": {"size": 26}},
        title={"text": title, "font": {"size": 15}},
        gauge={
            "axis": {"range": [mn, mx]},
            "bar": {"color": color, "thickness": 0.7},
            "steps": [
                {"range": [mn, mn + (mx - mn) / 3], "color": "#FDECEA"},
                {"range": [mn + (mx - mn) / 3, mx - (mx - mn) / 3], "color": "#FFF3CD"},
                {"range": [mx - (mx - mn) / 3, mx], "color": "#D6F0E4"},
            ],
        },
    ))
    fig.update_layout(height=260, margin=dict(l=25, r=25, t=55, b=10))
    return fig


def render_semaforo(scores):
    items = sorted(scores.items(), key=lambda kv: _norm(kv[1]))
    dims = [d for d, _ in items]
    vals = [_norm(i) for _, i in items]
    colors = [SEM_COLORS.get(i["color"], "#5F6368") for _, i in items]
    fig = go.Figure(go.Bar(
        x=vals, y=dims, orientation="h", marker_color=colors,
        text=[f"{v:.0f}" for v in vals], textposition="outside",
        hovertemplate="<b>%{y}</b><br>Índice: %{x:.0f}/100<extra></extra>",
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="#CBD5E1")
    fig.update_layout(
        height=max(320, len(dims) * 30),
        margin=dict(l=10, r=40, t=30, b=10),
        xaxis=dict(range=[0, 108], title="Índice de bienestar (0-100, mayor = mejor)"),
        showlegend=False,
    )
    return fig


def render_distribution(df, dim, cols):
    oriented = scoring.orient_items(df, dim, cols)
    vals = oriented.stack().dropna().round().astype(int)
    counts = vals.value_counts().sort_index()
    total = counts.sum()
    pct = (counts / total * 100).round(1)
    fig = go.Figure(go.Bar(
        x=counts.index.astype(str), y=counts.values,
        marker=dict(color=counts.index, colorscale=[[0, "#C0392B"], [0.5, "#FBBC04"], [1, "#1A7F4B"]]),
        text=[f"{p}%" for p in pct.values], textposition="outside",
        hovertemplate="Respuesta %{x}<br>%{y} respuestas<extra></extra>",
    ))
    fig.update_layout(
        title="Distribución de respuestas (orientadas a bienestar)",
        height=320, margin=dict(l=50, r=30, t=50, b=50),
        xaxis_title="Nivel de respuesta (mayor = mejor)", yaxis_title="Frecuencia",
        coloraxis_showscale=False, showlegend=False,
    )
    return fig


def render_item_bars(df, dim, cols):
    """Media por ítem (orientada), útil para dimensiones y diferencial semántico."""
    oriented = scoring.orient_items(df, dim, cols)
    means = oriented.mean().sort_values()
    labels = [c.split(")")[-1][:55] for c in means.index]
    mn, mx = get_scale_range(dim)
    fig = go.Figure(go.Bar(
        x=means.values, y=labels, orientation="h",
        marker_color="#2E5FAC",
        text=[f"{v:.2f}" for v in means.values], textposition="outside",
    ))
    fig.update_layout(
        title="Promedio por ítem (orientado)", height=max(280, len(labels) * 26),
        margin=dict(l=10, r=30, t=50, b=10),
        xaxis=dict(range=[mn, mx + 0.3], title=f"Escala {mn:.0f}-{mx:.0f}"),
    )
    return fig


# ── Vistas ──────────────────────────────────────────────────────
def _view_executive(df, scores):
    if not scores:
        st.warning("No se detectaron dimensiones de bienestar puntuables en los datos.")
        return
    fort, riesgo, inter = scoring.classify_dimensions(scores)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Participantes", f"{len(df):,}")
    c2.metric("📐 Dimensiones", len(scores))
    c3.metric("🟢 Fortalezas", len(fort))
    c4.metric("🔴 Áreas de atención", len(riesgo))

    st.markdown("#### Semáforo de bienestar")
    st.plotly_chart(render_semaforo(scores), width="stretch")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### 🟢 Principales fortalezas")
        if fort:
            for dim, val in fort[:5]:
                st.success(f"**{dim}** — {val:.2f}/{scores[dim]['scale_max']:.0f}")
        else:
            st.caption("Sin fortalezas destacadas.")
    with col_b:
        st.markdown("##### 🔴 Áreas de atención prioritaria")
        if riesgo:
            for dim, val in riesgo[:5]:
                st.error(f"**{dim}** — {val:.2f}/{scores[dim]['scale_max']:.0f}")
        else:
            st.caption("Sin dimensiones en riesgo crítico.")


def _view_dimension(df, scores):
    dims = DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {})
    dim_names = [d for d in dims.keys() if d in scores]
    if not dim_names:
        st.warning("No hay dimensiones puntuables.")
        return
    selected = st.selectbox("Selecciona una dimensión:", dim_names)
    info = scores[selected]
    cols = scoring.dimension_columns(df, selected)

    st.markdown(f"### {ESTADO_ICON.get(info['estado'],'')} {selected}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Puntaje", f"{info['score']:.2f}/{info['scale_max']:.0f}")
    m2.metric("Estado", info["estado"])
    m3.metric("N", info["n"])
    m4.metric("α Cronbach", f"{info['alpha']:.2f}" if isinstance(info["alpha"], float) else "—")

    if info["is_risk"]:
        st.caption("ℹ️ Dimensión de riesgo: el puntaje está orientado a bienestar "
                   "(mayor = mejor); un valor bajo indica mayor nivel de riesgo.")

    g, d = st.columns([1, 1.3])
    with g:
        st.plotly_chart(
            render_gauge(info["score"], selected[:30], info["scale_min"],
                         info["scale_max"], SEM_COLORS.get(info["color"], "#2E5FAC")),
            width="stretch")
    with d:
        st.plotly_chart(render_distribution(df, selected, cols), width="stretch")

    st.plotly_chart(render_item_bars(df, selected, cols), width="stretch")

    if st.button(f"✨ Interpretar «{selected}» con IA"):
        client = get_cached_client()
        client.current_df = df
        if not client.is_configured():
            st.error("⚠️ API Key no configurada.")
        else:
            with st.spinner("Generando análisis experto..."):
                stats = df[cols].describe().to_string()
                prompt = (
                    f"Actúa como experto en Psicología Organizacional. Analiza la dimensión "
                    f"'{selected}' (puntaje orientado a bienestar {info['score']:.2f}/"
                    f"{info['scale_max']:.0f}, estado {info['estado']}, N={info['n']}).\n\n"
                    f"Estadísticos por ítem:\n{stats}\n\n"
                    "1. Describe el estado actual en lenguaje claro.\n"
                    "2. Identifica ítems críticos.\n"
                    "3. Sugiere 2 acciones basadas en evidencia."
                )
                st.markdown(client.generate_response(prompt))


def _view_profile(df):
    tabs = st.tabs(["👥 Sociodemográficas", "🏢 Laborales"])
    specs = [
        (tabs[0], "Variables Sociodemográficas"),
        (tabs[1], "Variables Laborales"),
    ]
    for tab, cat in specs:
        with tab:
            variables = DATA_DICTIONARY.get(cat, {})
            cols = st.columns(2)
            i = 0
            for var_name in variables.keys():
                found = next((c for c in df.columns if var_name.strip() in c), None)
                if not found:
                    continue
                with cols[i % 2]:
                    label = var_name.split(")")[-1].strip()
                    st.markdown(f"**{label}**")
                    if pd.api.types.is_numeric_dtype(df[found]):
                        fig = px.histogram(df, x=found, nbins=20, color_discrete_sequence=["#2E5FAC"])
                    else:
                        vc = df[found].value_counts().reset_index()
                        vc.columns = ["Valor", "Frecuencia"]
                        fig = px.bar(vc, x="Valor", y="Frecuencia",
                                     color="Frecuencia", color_continuous_scale="Blues")
                    fig.update_layout(height=300, margin=dict(l=40, r=20, t=20, b=60),
                                      coloraxis_showscale=False,
                                      xaxis=dict(automargin=True), yaxis=dict(automargin=True))
                    st.plotly_chart(fig, width="stretch")
                i += 1
            if i == 0:
                st.caption("No se encontraron columnas de esta categoría en los datos.")


def _view_academic(df, scores):
    if not scores:
        st.warning("No hay dimensiones puntuables.")
        return

    st.markdown("#### Tabla de fiabilidad y puntajes")
    table = pd.DataFrame([
        {
            "Dimensión": dim,
            "N": info["n"],
            "Puntaje": round(info["score"], 2),
            "Escala": f"{info['scale_min']:.0f}-{info['scale_max']:.0f}",
            "DE": round(info["std"], 2),
            "IC95%": f"±{info['ci95']:.2f}",
            "α": round(info["alpha"], 2) if isinstance(info["alpha"], float) else None,
            "Ítems": info["n_items"],
            "Estado": info["estado"],
        }
        for dim, info in sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    ])
    st.dataframe(table, width="stretch", hide_index=True)
    st.caption("α = alfa de Cronbach (consistencia interna; aceptable ≥ 0.70). "
               "Puntajes orientados a bienestar (mayor = mejor).")

    st.markdown("#### Correlación entre dimensiones (orientadas)")
    mat = _dim_score_matrix(df)
    if mat.shape[1] >= 2:
        corr = mat.corr()
        fig = px.imshow(corr, text_auto=".2f", aspect="auto",
                        color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        fig.update_layout(height=560, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Comparación por grupo")
    cat_cols = [c for c in df.columns
                if (c.startswith("(SD)") or c.startswith("(LB)"))
                and 1 < df[c].nunique(dropna=True) <= 12]
    if cat_cols and mat.shape[1] >= 1:
        c1, c2 = st.columns(2)
        group_col = c1.selectbox("Agrupar por:", cat_cols,
                                 format_func=lambda c: c.split(")")[-1].strip())
        dim_acr = c2.selectbox("Dimensión:", list(mat.columns))
        comp = mat[[dim_acr]].copy()
        comp["_grupo"] = df[group_col].values
        agg = comp.groupby("_grupo")[dim_acr].agg(["mean", "count"]).reset_index()
        agg = agg.sort_values("mean", ascending=False)
        fig = px.bar(agg, x="_grupo", y="mean", text=agg["mean"].round(2),
                     color="mean", color_continuous_scale="Blues",
                     labels={"_grupo": group_col.split(")")[-1].strip(), "mean": "Puntaje medio"})
        fig.update_layout(height=380, margin=dict(l=40, r=20, t=20, b=80),
                          coloraxis_showscale=False, xaxis=dict(tickangle=-30, automargin=True))
        st.plotly_chart(fig, width="stretch")
        st.caption("N por grupo: " + ", ".join(f"{r['_grupo']}={int(r['count'])}" for _, r in agg.iterrows()))
    else:
        st.caption("No hay variables de agrupación adecuadas en los datos.")


# ── Vistas genéricas (datasets que no son de bienestar (BM)) ────
@st.cache_data(show_spinner=False)
def _enriched(df, cols):
    return indicators.enrich_indicators(df, cols)


def _group_columns(df, exclude):
    """Columnas categóricas/de agrupación (baja cardinalidad), excluyendo indicadores."""
    cols = []
    for c in df.columns:
        if c in exclude:
            continue
        from src.data.processor import is_protected_column
        if is_protected_column(c):
            continue
        nun = df[c].nunique(dropna=True)
        if 1 < nun <= 12:
            cols.append(c)
    return cols


def _label(c):
    return str(c).split(")")[-1].strip()


def _theme_bar(items):
    """Barra horizontal de posición relativa (0-100, orientada a mejor) por indicador."""
    items = sorted(items, key=lambda kv: kv[1]["oriented"])
    labels = [i["label"] for _, i in items]
    vals = [i["oriented"] for _, i in items]
    colors = [i["color"] for _, i in items]
    raw = [f"{i['mean']:.1f}  (rango {i['min']:.0f}–{i['max']:.0f}, N={i['n']})" for _, i in items]
    dirn = ["↑ mejor" if i["higher_is_better"] else "↑ riesgo" if i["higher_is_better"] is False
            else "dirección no definida" for _, i in items]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h", marker_color=colors,
        text=[f"{v:.0f}" for v in vals], textposition="outside",
        customdata=list(zip(raw, dirn)),
        hovertemplate="<b>%{y}</b><br>Posición: %{x:.0f}/100<br>Media: %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="#CBD5E1")
    fig.update_layout(height=max(190, len(labels) * 42), margin=dict(l=10, r=40, t=10, b=10),
                      xaxis=dict(range=[0, 108], title="Posición relativa en la muestra (0-100, orientada a mejor)"),
                      showlegend=False)
    return fig


def _view_indicators(df, enr):
    themes = indicators.by_theme(enr)
    n_atencion = sum(1 for _, i in enr.items()
                     if i["theme"].startswith("🧠") and i["level"] == "Atención")

    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Docentes", f"{len(df):,}")
    c2.metric("📐 Indicadores", len(enr))
    c3.metric("🧠 Salud mental en atención", n_atencion)

    st.info("Las barras muestran la **posición relativa dentro de esta muestra** (0-100), "
            "orientada a *mayor = mejor* cuando se conoce la dirección del instrumento. "
            "El nivel (Favorable/Intermedio/Atención) es relativo a la muestra, no un punto "
            "de corte clínico. Ajusta etiquetas y direcciones en `docs/GUIA_DATASETS.md`.")

    for theme in indicators.THEMES_ORDER:
        items = themes.get(theme)
        if not items:
            continue
        st.markdown(f"##### {theme}")
        st.plotly_chart(_theme_bar(items), width="stretch")
        if theme.startswith("🧠"):
            aten = [i["label"] for _, i in items if i["level"] == "Atención"]
            fav = [i["label"] for _, i in items if i["level"] == "Favorable"]
            cols = st.columns(2)
            with cols[0]:
                if aten:
                    st.error("**Requieren atención:** " + ", ".join(aten))
                else:
                    st.success("Sin indicadores de salud mental en zona de atención.")
            with cols[1]:
                if fav:
                    st.success("**Favorables:** " + ", ".join(fav))
            if st.button("✨ Interpretar salud mental con IA"):
                _ai_interpret_mental_health(df, items)

    with st.expander("📋 Tabla completa de indicadores"):
        table = pd.DataFrame([
            {"Indicador": i["label"], "Tema": i["theme"], "Media": round(i["mean"], 2),
             "DE": round(i["std"], 2), "Rango": f"{i['min']:.0f}–{i['max']:.0f}",
             "N": i["n"], "Nivel (muestra)": i["level"]}
            for _, i in enr.items()
        ])
        st.dataframe(table, width="stretch", hide_index=True)

    st.markdown("#### Explorar un indicador")
    keys = list(enr.keys())
    sel = st.selectbox("Indicador:", keys, format_func=lambda c: enr[c]["label"])
    if sel:
        info = enr[sel]
        g, h = st.columns([1, 1.4])
        with g:
            st.metric(info["label"], f"{info['mean']:.2f}")
            st.metric("Rango observado", f"{info['min']:.0f} – {info['max']:.0f}")
            st.metric("N", info["n"])
        with h:
            fig = px.histogram(df, x=sel, nbins=20, color_discrete_sequence=["#2E5FAC"])
            fig.update_layout(height=300, margin=dict(l=40, r=20, t=30, b=40),
                              xaxis_title=info["label"], yaxis_title="Frecuencia")
            st.plotly_chart(fig, width="stretch")

        groups = _group_columns(df, exclude=set(enr.keys()))
        if groups:
            gcol = st.selectbox("Comparar por grupo:", groups, format_func=_label)
            agg = df.groupby(gcol)[sel].agg(["mean", "count"]).reset_index().sort_values("mean", ascending=False)
            fig2 = px.bar(agg, x=gcol, y="mean", text=agg["mean"].round(2),
                          color="mean", color_continuous_scale="Blues",
                          labels={gcol: _label(gcol), "mean": f"{info['label']} (media)"})
            fig2.update_layout(height=340, margin=dict(l=40, r=20, t=20, b=70),
                               coloraxis_showscale=False, xaxis=dict(tickangle=-30, automargin=True))
            st.plotly_chart(fig2, width="stretch")
            st.caption("N por grupo: " + ", ".join(f"{r[gcol]}={int(r['count'])}" for _, r in agg.iterrows()))

        if st.button(f"✨ Interpretar «{info['label']}» con IA"):
            client = get_cached_client()
            client.current_df = df
            if not client.is_configured():
                st.error("⚠️ API Key no configurada.")
            else:
                with st.spinner("Generando análisis..."):
                    desc = df[sel].describe().to_string()
                    d = ("mayor = mejor" if info["higher_is_better"] else "mayor = más riesgo"
                         if info["higher_is_better"] is False else "dirección no definida")
                    prompt = (
                        f"Actúa como psicólogo experto en salud mental laboral docente. El indicador "
                        f"'{info['label']}' ({d}) tiene estos estadísticos:\n{desc}\n\n"
                        "1. Explica en lenguaje claro qué mide.\n"
                        "2. Interpreta el nivel observado en el contexto de docentes.\n"
                        "3. Sugiere 2 acciones basadas en evidencia."
                    )
                    st.markdown(client.generate_response(prompt))


def _ai_interpret_mental_health(df, items):
    client = get_cached_client()
    client.current_df = df
    if not client.is_configured():
        st.error("⚠️ API Key no configurada.")
        return
    with st.spinner("Analizando salud mental con IA..."):
        resumen = "\n".join(
            f"- {i['label']}: media {i['mean']:.1f} (rango {i['min']:.0f}-{i['max']:.0f}), "
            f"posición {i['oriented']:.0f}/100, {i['level']}" for _, i in items)
        prompt = (
            "Actúa como experto en salud mental ocupacional docente. Con base en estos "
            f"indicadores de {len(df)} docentes (posición 0-100 orientada a mejor):\n{resumen}\n\n"
            "1. Da un panorama de la salud mental del profesorado en lenguaje claro.\n"
            "2. Señala los focos de riesgo prioritarios.\n"
            "3. Propón 3 acciones concretas y basadas en evidencia (cita autores clásicos si aplica)."
        )
        st.markdown(client.generate_response(prompt))


def _view_generic_academic(df, enr):
    st.markdown("#### Correlación entre indicadores")
    inds = list(enr.keys())
    num = df[inds].apply(pd.to_numeric, errors="coerce")
    num.columns = [enr[c]["label"] for c in inds]
    if num.shape[1] >= 2:
        corr = num.corr()
        fig = px.imshow(corr, text_auto=False, aspect="auto",
                        color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        fig.update_layout(height=680, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")
        st.caption("Correlaciones de Pearson entre los indicadores detectados. "
                   "Nota: sobre puntajes crudos (sin orientar).")
    else:
        st.caption("Se necesitan al menos 2 indicadores numéricos.")


# ── Sidebar (reporte + filtros + descarga) ──────────────────────
def _sidebar(df_full, wellbeing=True):
    with st.sidebar:
        st.subheader("📄 Informe")
        org = st.text_input("Organización", "Organización", key="dash_org")
        if st.button("Generar Informe PDF", width="stretch"):
            with st.spinner("Generando informe profesional..."):
                try:
                    data = st.session_state.get("_df_view", df_full)
                    if wellbeing:
                        from src.reports.report_builder import ReportBuilder
                        pdf_bytes = ReportBuilder(
                            data, title="Informe de Diagnóstico de Bienestar",
                            org_name=org).build_report()
                        fname = "informe_bienestar.pdf"
                    else:
                        from src.reports.indicator_report import IndicatorReportBuilder
                        pdf_bytes = IndicatorReportBuilder(
                            data, title="Informe de Salud Mental y Bienestar Docente",
                            org_name=org).build_report()
                        fname = "informe_salud_mental_docente.pdf"
                    st.download_button(
                        "⬇️ Descargar Informe PDF", data=pdf_bytes,
                        file_name=fname, mime="application/pdf",
                        width="stretch")
                    st.success("✅ Informe generado.")
                except Exception as e:
                    st.error(f"Error al generar informe: {e}")
        st.divider()

    # Filtros multiselección (añaden controles a la sidebar)
    df_view = render_filtering_sidebar(df_full)
    st.session_state["_df_view"] = df_view

    with st.sidebar:
        csv = df_view.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar datos filtrados (CSV)", data=csv,
                           file_name="datos_filtrados.csv", mime="text/csv",
                           width="stretch")
    return df_view


def render_dashboard():
    df = get_processed_data()
    if df is None:
        st.info("⚠️ No hay datos cargados. Ve a 'Cargar Datos' para comenzar.")
        return

    st.markdown("## 📊 Dashboard de Salud Organizacional")
    label = st.session_state.get("current_dataset")
    if label:
        st.caption(f"Dataset activo: **{label}** · {len(df):,} registros")
    # En el despliegue solo existe el CSV sintético; sin este aviso se lee como datos reales.
    from src.data.loader import es_demo
    if es_demo(label):
        st.warning(
            "Estás viendo datos de demostración generados al azar, no respuestas reales. "
            "Carga el archivo real en «Cargar Datos»."
        )

    wellbeing = indicators.is_wellbeing_dataset(df)
    df_view = _sidebar(df, wellbeing)

    if wellbeing:
        scores = _scores(df_view)
        tab_exec, tab_dim, tab_perfil, tab_acad = st.tabs(
            ["🏢 Resumen ejecutivo", "🧠 Dimensiones", "👥 Perfil", "🎓 Vista académica"]
        )
        with tab_exec:
            _view_executive(df_view, scores)
        with tab_dim:
            _view_dimension(df_view, scores)
        with tab_perfil:
            _view_profile(df_view)
        with tab_acad:
            _view_academic(df_view, scores)
    else:
        inds = indicators.detect_indicators(df_view)
        enr = _enriched(df_view, inds) if inds else {}
        tab_ind, tab_perfil, tab_corr = st.tabs(
            ["🧠 Salud mental e indicadores", "👥 Perfil", "🎓 Correlaciones"]
        )
        with tab_ind:
            if enr:
                _view_indicators(df_view, enr)
            else:
                st.warning("No se detectaron indicadores numéricos en este dataset.")
        with tab_perfil:
            _view_profile(df_view)
        with tab_corr:
            if enr:
                _view_generic_academic(df_view, enr)
            else:
                st.caption("Sin indicadores para correlacionar.")
