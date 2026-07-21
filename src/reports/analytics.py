"""
Módulo de análisis y generación de gráficas para reportes PDF.
Tema visual institucional azul + semáforo de bienestar.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import Patch
import seaborn as sns
import io
from src.core.config import DATA_DICTIONARY, get_scale_range as _config_scale_range
from src.core.ai import generate_analysis, build_report_prompt
from src.analysis import scoring

# Variables candidatas para comparaciones por grupo (se usan las presentes)
GROUP_CANDIDATES = [
    ("(SD)Sexo", "Sexo"),
    ("(SD)Nivel Educativo", "Nivel Educativo"),
    ("(SD)Zona de vivienda", "Zona de vivienda"),
    ("(LB)Sector empresa", "Sector empresa"),
    ("(LB)Tipo de modalidad de trabajo", "Modalidad de trabajo"),
    ("(LB)Cargo", "Cargo"),
]

# ═══════════════════════════════════════════════════════════════
# PALETA Y TEMA MATPLOTLIB
# ═══════════════════════════════════════════════════════════════

COLORS = {
    "brand_blue":       "#1B3A6B",
    "brand_blue_mid":   "#2E5FAC",
    "brand_blue_light": "#EBF1FB",
    "strength":         "#1A7F4B",
    "strength_light":   "#D6F0E4",
    "medium":           "#B07D0D",
    "medium_light":     "#FFF3CD",
    "risk":             "#C0392B",
    "risk_light":       "#FDECEA",
    "text_primary":     "#1A1A2E",
    "text_secondary":   "#4A4A6A",
    "divider":          "#CBD5E1",
    "background_alt":   "#F8FAFC",
    "white":            "#FFFFFF",
}

CHART_PALETTE = [
    "#2E5FAC", "#1A7F4B", "#C0392B",
    "#B07D0D", "#6C3483", "#117A8B",
]


def apply_report_theme():
    """Aplica el tema visual institucional a matplotlib."""
    mpl.rcParams.update({
        "font.family":          "sans-serif",
        "font.sans-serif":      ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size":            9,
        "axes.titlesize":       11,
        "axes.titleweight":     "bold",
        "axes.titlecolor":      COLORS["brand_blue"],
        "axes.labelsize":       9,
        "axes.labelcolor":      COLORS["text_secondary"],
        "axes.facecolor":       COLORS["background_alt"],
        "figure.facecolor":     COLORS["white"],
        "axes.edgecolor":       COLORS["divider"],
        "axes.linewidth":       0.8,
        "axes.grid":            True,
        "grid.color":           "#E2E8F0",
        "grid.linewidth":       0.6,
        "grid.linestyle":       "--",
        "grid.alpha":           0.7,
        "xtick.color":          COLORS["text_secondary"],
        "ytick.color":          COLORS["text_secondary"],
        "xtick.labelsize":      8,
        "ytick.labelsize":      8,
        "xtick.direction":      "out",
        "ytick.direction":      "out",
        "axes.spines.top":      False,
        "axes.spines.right":    False,
        "legend.fontsize":      8,
        "legend.framealpha":    0.9,
        "legend.edgecolor":     COLORS["divider"],
    })


def save_figure_to_bytes(fig, dpi=130) -> bytes:
    """Guarda figura matplotlib a bytes PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                pad_inches=0.25, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf.read()


# ═══════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

class ReportAnalytics:
    def __init__(self, df):
        self.df = df
        # Fuente única de verdad: puntajes orientados a bienestar (mayor = mejor)
        self._scores = scoring.compute_dimension_scores(df)

    def get_scale_range(self, dim_name):
        return _config_scale_range(dim_name)

    def estado_dimension(self, valor, dim_name):
        """Clasifica un puntaje YA orientado (delegado a scoring)."""
        return scoring.estado_from_score(valor, dim_name)

    def scores(self):
        """Métricas completas por dimensión (score, n, std, ci95, alpha, estado...)."""
        return self._scores

    def calculate_averages(self):
        """Promedios ORIENTADOS por dimensión (mayor = mejor bienestar)."""
        return {dim: info["score"] for dim, info in self._scores.items()}

    def classify_dimensions(self, promedios=None):
        """Clasifica en Fortalezas, Riesgos, Intermedios, Sin Datos."""
        fortalezas, riesgos, intermedios, sin_datos = [], [], [], []
        source = promedios if promedios is not None else self.calculate_averages()
        for dim, val in source.items():
            estado, _ = self.estado_dimension(val, dim)
            entry = (dim, val)
            if estado == 'Fortaleza':
                fortalezas.append(entry)
            elif estado == 'Riesgo':
                riesgos.append(entry)
            elif estado == 'Intermedio':
                intermedios.append(entry)
            else:
                sin_datos.append(entry)
        fortalezas.sort(key=lambda x: x[1], reverse=True)
        riesgos.sort(key=lambda x: x[1])
        intermedios.sort(key=lambda x: x[1])
        return fortalezas, riesgos, intermedios, sin_datos

    # ───────────────────────────────────────────────────────
    # GRÁFICAS
    # ───────────────────────────────────────────────────────

    def generate_traffic_light_chart(self, promedios) -> bytes:
        """Gráfica semáforo — barras horizontales con colores de estado."""
        apply_report_theme()

        items = sorted(promedios.items(), key=lambda x: x[1])
        if not items:
            return None

        labels = [k for k, v in items]
        values = [v for k, v in items]

        bar_colors = []
        for name, val in items:
            estado, _ = self.estado_dimension(val, name)
            if estado == 'Fortaleza':
                bar_colors.append(COLORS["strength"])
            elif estado == 'Riesgo':
                bar_colors.append(COLORS["risk"])
            else:
                bar_colors.append(COLORS["medium"])

        fig, ax = plt.subplots(figsize=(8, max(4, len(labels) * 0.45)))

        bars = ax.barh(labels, values, color=bar_colors, height=0.6,
                       edgecolor="white", linewidth=0.5)

        for bar, val in zip(bars, values):
            ax.text(val + 0.08, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", ha="left",
                    fontsize=8, fontweight="bold", color=COLORS["text_primary"])

        # Línea de referencia
        ax.axvline(x=4.0, color=COLORS["divider"], linewidth=1,
                   linestyle="--", alpha=0.8)
        ax.text(4.05, -0.7, "Punto medio\n(4.0)", fontsize=7,
                color=COLORS["text_secondary"], va="top")

        ax.set_xlim(0, 7.8)
        ax.set_xlabel("Puntaje promedio (escala 1-7)", fontsize=9)
        ax.set_title("Diagnóstico de Dimensiones de Bienestar", pad=12)

        legend_elements = [
            Patch(facecolor=COLORS["strength"], label="Fortaleza"),
            Patch(facecolor=COLORS["medium"], label="Intermedio"),
            Patch(facecolor=COLORS["risk"], label="Riesgo"),
        ]
        ax.legend(handles=legend_elements, loc="lower right", fontsize=8)

        return save_figure_to_bytes(fig)

    def generate_sociodemographic_chart(self, col_name: str, var_label: str) -> bytes:
        """Gráfica de barras para una variable sociodemográfica o laboral."""
        apply_report_theme()

        if col_name not in self.df.columns:
            return None

        if pd.api.types.is_numeric_dtype(self.df[col_name]):
            fig, ax = plt.subplots(figsize=(5, 3.5))
            self.df[col_name].hist(ax=ax, bins=15, color=COLORS["brand_blue_mid"],
                                   edgecolor="white", linewidth=0.5)
            ax.set_xlabel(var_label, fontsize=9)
            ax.set_ylabel("Frecuencia", fontsize=9)
        else:
            counts = self.df[col_name].value_counts()
            fig, ax = plt.subplots(figsize=(5, 3.5))
            colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(counts))]
            bars = ax.bar(range(len(counts)), counts.values, color=colors,
                          edgecolor="white", linewidth=0.5)
            ax.set_xticks(range(len(counts)))
            ax.set_xticklabels(counts.index, rotation=45, ha='right', fontsize=8)
            ax.set_ylabel("Frecuencia", fontsize=9)

            for bar, val in zip(bars, counts.values):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                            str(val), ha='center', va='bottom', fontsize=7,
                            color=COLORS["text_secondary"])

        ax.set_title(var_label, pad=10)
        return save_figure_to_bytes(fig)

    def generate_comparative_charts(self, promedios) -> list:
        """Gráficas comparativas por grupos. Retorna lista de (bytes, título)."""
        apply_report_theme()
        charts = []

        # Buscar columnas de agrupación disponibles (cardinalidad razonable)
        grupos = {}
        for col, label in GROUP_CANDIDATES:
            if col in self.df.columns:
                nun = self.df[col].nunique(dropna=True)
                if 1 < nun <= 8:
                    grupos[label] = col
            if len(grupos) >= 3:  # máximo 3 agrupaciones por dimensión
                break

        if not grupos:
            return []

        for dim_name, prom_general in promedios.items():
            cols_validas = scoring.dimension_columns(self.df, dim_name)
            if not cols_validas:
                continue
            # Ítems orientados a bienestar para que la comparación sea coherente
            oriented = scoring.orient_items(self.df, dim_name, cols_validas)

            min_esc, max_esc = self.get_scale_range(dim_name)
            n_grupos = len(grupos)
            fig, axs = plt.subplots(1, n_grupos, figsize=(n_grupos * 4.5, 4.0), sharey=True)
            if n_grupos == 1:
                axs = [axs]

            fig.suptitle(f"Comparación: {dim_name}\n(Promedio general: {prom_general:.2f})",
                         y=1.03, fontsize=11, fontweight='bold', color=COLORS["brand_blue"])

            has_data = False
            for k, (grupo_label, grupo_col) in enumerate(grupos.items()):
                ax = axs[k]
                try:
                    grouped = oriented.groupby(self.df[grupo_col], observed=False).mean(numeric_only=True)
                    final_means = grouped.mean(axis=1, skipna=True).dropna()
                    if not final_means.empty:
                        has_data = True
                        cats = final_means.index.astype(str)
                        vals = final_means.values
                        colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(cats))]
                        bars = ax.bar(cats, vals, color=colors, width=0.7,
                                      edgecolor="white", linewidth=0.5)
                        ax.set_title(f"Por {grupo_label}", fontsize=10)
                        if k == 0:
                            ax.set_ylabel('Promedio', fontsize=9)
                        ax.tick_params(axis='x', rotation=45, labelsize=8)
                        ax.set_ylim(bottom=max(0, min_esc - 0.5), top=max_esc + 0.5)
                        for bar in bars:
                            ax.text(bar.get_x() + bar.get_width() / 2,
                                    bar.get_height() + 0.05,
                                    f'{bar.get_height():.1f}',
                                    ha='center', va='bottom', fontsize=8,
                                    color=COLORS["text_primary"])
                except Exception:
                    ax.text(0.5, 0.5, 'Sin Datos', ha='center', va='center',
                            transform=ax.transAxes)

            if has_data:
                plt.tight_layout(rect=[0, 0.05, 1, 0.92], pad=2.0)
                chart_bytes = save_figure_to_bytes(fig)
                charts.append((chart_bytes, f"Comparación: {dim_name}"))
            else:
                plt.close(fig)

        return charts

    def generate_correlation_matrix(self) -> bytes:
        """Heatmap de correlación ENTRE DIMENSIONES (orientadas): legible e interpretable."""
        apply_report_theme()

        dim_scores = {}
        for dim in self._scores.keys():
            cols = scoring.dimension_columns(self.df, dim)
            if not cols:
                continue
            oriented = scoring.orient_items(self.df, dim, cols)
            acr = self._scores[dim].get("acronimo") or dim[:6]
            dim_scores[acr] = oriented.mean(axis=1, skipna=True)

        if len(dim_scores) < 2:
            return None

        corr_df = pd.DataFrame(dim_scores).corr()
        n = len(corr_df.columns)
        fig_size = max(6, n * 0.55)
        fig, ax = plt.subplots(figsize=(fig_size, fig_size))

        sns.heatmap(corr_df, annot=True, fmt=".2f", annot_kws={"size": 7},
                    cmap='coolwarm', center=0, vmin=-1, vmax=1,
                    xticklabels=corr_df.columns, yticklabels=corr_df.columns,
                    square=True, linewidths=.5, cbar_kws={"shrink": .6}, ax=ax)

        ax.set_title("Matriz de Correlación entre Dimensiones (orientadas a bienestar)",
                     fontsize=12, color=COLORS["brand_blue"], pad=12)
        plt.xticks(rotation=0, fontsize=8)
        plt.yticks(rotation=0, fontsize=8)
        return save_figure_to_bytes(fig, dpi=120)

    def generate_ai_analysis(self, promedios, fortalezas, riesgos) -> str:
        """Genera análisis IA fundamentado con referencias del RAG."""
        prompt = build_report_prompt(promedios, fortalezas, riesgos)
        try:
            from src.ai.knowledge_base import get_cached_kb
            kb = get_cached_kb()
            if kb.enabled:
                focos = " ".join(d for d, _ in (riesgos[:3] if riesgos else []))
                refs = kb.query_knowledge(
                    f"recomendaciones e intervenciones de bienestar laboral {focos}",
                    n_results=4,
                )
                if refs:
                    prompt += (
                        "\n\nUSA Y CITA EN FORMATO APA ÚNICAMENTE ESTAS REFERENCIAS "
                        f"(no inventes otras):\n{refs}"
                    )
        except Exception:
            pass
        return generate_analysis(prompt)
