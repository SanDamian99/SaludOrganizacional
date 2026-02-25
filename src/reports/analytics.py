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
from src.core.config import DATA_DICTIONARY
from src.core.ai import generate_analysis, build_report_prompt

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
        self.inverse_dims = {
            "Conflicto Familia-Trabajo": True,
            "Síntomas de Burnout": True,
            "Factores de Efectos Colaterales (Escala de Desgaste)": True,
            "Factores de Efectos Colaterales (Escala de Alienación)": True,
            "Intención de Retiro": True,
            "Factores de Efectos Colaterales (Escala de Somatización)": True,
        }

    def get_scale_range(self, dim_name):
        details = DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {}).get(dim_name, {})
        escala = details.get("Escala", {})
        if escala and isinstance(escala, dict):
            vals = [k for k in escala.keys() if isinstance(k, (int, float))]
            if vals:
                return min(vals), max(vals)
        if "Burnout" in dim_name:
            return 1, 5
        if any(s in dim_name for s in ["Compromiso", "Defensa", "Satisfacción", "Retiro"]):
            return 1, 6
        return 1, 7

    def estado_dimension(self, valor, dim_name):
        if pd.isna(valor):
            return ('Sin Datos', 'grey')
        min_esc, max_esc = self.get_scale_range(dim_name)
        rango = max_esc - min_esc
        if rango <= 0:
            return ('Rango Inválido', 'grey')

        umbral_riesgo = min_esc + rango / 3.0
        umbral_fortaleza = max_esc - rango / 3.0
        val_int = (max_esc + min_esc) - valor if self.inverse_dims.get(dim_name, False) else valor

        if val_int >= umbral_fortaleza:
            return ('Fortaleza', 'green')
        elif val_int <= umbral_riesgo:
            return ('Riesgo', 'red')
        else:
            return ('Intermedio', 'yellow')

    def calculate_averages(self):
        """Calcula promedios de todas las dimensiones."""
        resultados = {}
        bm_dims = DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {})
        for dim_name, dim_details in bm_dims.items():
            acronym = dim_details.get("Acronimo")
            if not acronym:
                continue
            target = f"(BM),({acronym})"
            cols = [c for c in self.df.columns
                    if target in c and pd.api.types.is_numeric_dtype(self.df[c])]
            if cols:
                prom = self.df[cols].mean(axis=0, skipna=True).mean(skipna=True)
                if pd.notna(prom):
                    resultados[dim_name] = prom
        return resultados

    def classify_dimensions(self, promedios):
        """Clasifica dimensiones en Fortalezas, Riesgos, Intermedios."""
        fortalezas, riesgos, intermedios, sin_datos = [], [], [], []
        for dim, val in promedios.items():
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

        # Buscar columnas de agrupación
        grupos = {}
        col_sexo = '(SD)Sexo'
        if col_sexo in self.df.columns and self.df[col_sexo].nunique() > 1:
            grupos['Sexo'] = col_sexo

        if not grupos:
            return []

        for dim_name, prom_general in promedios.items():
            details = DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {}).get(dim_name, {})
            acronym = details.get("Acronimo")
            if not acronym:
                continue
            target = f"(BM),({acronym})"
            cols_validas = [c for c in self.df.columns
                           if target in c and pd.api.types.is_numeric_dtype(self.df[c])]
            if not cols_validas:
                continue

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
                    grouped = self.df.groupby(grupo_col, observed=False)[cols_validas].mean(numeric_only=True)
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
        """Genera heatmap de correlación."""
        apply_report_theme()

        target_subs = ["(BM)", "(SD)"]
        cols = [c for c in self.df.columns
                if any(s in c for s in target_subs) and pd.api.types.is_numeric_dtype(self.df[c])]
        if len(cols) < 2:
            return None

        corr_df = self.df[cols].corr()
        short_labels = []
        for c in corr_df.columns:
            label = c.split(')')[-1]
            short_labels.append(label[:18] + '..' if len(label) > 18 else label)

        n = len(corr_df.columns)
        fig_size = max(8, n * 0.45)
        fig, ax = plt.subplots(figsize=(fig_size, fig_size))

        sns.heatmap(corr_df, annot=False, cmap='coolwarm', center=0,
                    xticklabels=short_labels, yticklabels=short_labels,
                    square=True, linewidths=.5, cbar_kws={"shrink": .5}, ax=ax)

        ax.set_title("Matriz de Correlación", fontsize=14, color=COLORS["brand_blue"], pad=12)
        plt.xticks(rotation=45, ha='right', fontsize=8)
        plt.yticks(rotation=0, fontsize=8)
        return save_figure_to_bytes(fig, dpi=110)

    def generate_ai_analysis(self, promedios, fortalezas, riesgos) -> str:
        """Genera análisis IA usando ai.py."""
        prompt = build_report_prompt(promedios, fortalezas, riesgos)
        return generate_analysis(prompt)
