"""
Report Builder — Estructura narrativa del informe PDF.
Orquesta ReportAnalytics + PDFReport para generar un documento coherente
con contexto texto → gráfica → interpretación.
"""
import io
import os
import tempfile
from datetime import datetime
from src.reports.analytics import ReportAnalytics
from src.reports.pdf_generator import PDFReport, clean_text


class ReportBuilder:
    """
    Construye el informe completo siguiendo esta narrativa:

    PORTADA → RESUMEN EJECUTIVO → SOCIODEMOGRÁFICO → DIAGNÓSTICO →
    ANÁLISIS POR GRUPOS → RECOMENDACIONES → REFERENCIAS
    """

    def __init__(self, df, title="Informe de Diagnóstico de Bienestar",
                 org_name="Organización"):
        self.df = df
        self.title = title
        self.org_name = org_name
        self.analytics = ReportAnalytics(df)

    def build_report(self, title=None, org_name=None) -> bytes:
        """
        Genera el reporte completo y retorna los bytes del PDF.
        """
        if title:
            self.title = title
        if org_name:
            self.org_name = org_name

        # Crear archivo temporal
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()

        try:
            pdf = PDFReport(
                filename=tmp_path,
                report_title=self.title,
                org_name=self.org_name,
                n_participants=len(self.df),
            )

            # Calcular datos
            promedios = self.analytics.calculate_averages()
            fortalezas, riesgos, intermedios, sin_datos = (
                self.analytics.classify_dimensions(promedios)
            )

            # Construir secciones
            self._build_executive_summary(pdf, promedios, fortalezas, riesgos, intermedios)
            self._build_sociodemographic(pdf)
            self._build_bienestar_diagnosis(pdf, promedios, fortalezas, riesgos)
            self._build_group_analysis(pdf, promedios)
            self._build_recommendations(pdf, promedios, fortalezas, riesgos)
            self._build_references(pdf)

            # Generar PDF
            pdf.build_pdf()

            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # ───────────────────────────────────────────────────────
    # SECCIÓN 1: RESUMEN EJECUTIVO
    # ───────────────────────────────────────────────────────

    def _build_executive_summary(self, pdf, promedios, fortalezas, riesgos, intermedios):
        pdf.add_title("RESUMEN EJECUTIVO", level=1)

        # KPI Table
        n_dims = len(promedios)
        n_fort = len(fortalezas)
        n_risk = len(riesgos)

        pdf.add_kpi_table([
            ("Participantes", f"{len(self.df):,}", "personas", "brand_blue"),
            ("Dimensiones evaluadas", str(n_dims), "areas", "brand_blue"),
            ("Fortalezas", str(n_fort), "dimensiones", "strength"),
            ("Areas de atencion", str(n_risk), "dimensiones", "risk"),
        ])

        # Contexto
        pdf.add_paragraph(
            f"El presente informe sintetiza los resultados del estudio de bienestar y "
            f"salud organizacional realizado con {len(self.df):,} participantes. "
            f"Se evaluaron {n_dims} dimensiones clave del bienestar laboral, "
            f"identificando {n_fort} fortalezas y {n_risk} areas que requieren atencion."
        )

        # Callout: principal fortaleza
        if fortalezas:
            best = fortalezas[0]
            pdf.add_insight_box(
                f"Principal fortaleza: {best[0]} con un puntaje promedio de {best[1]:.2f}. "
                f"Este resultado indica un desempeno positivo en esta dimension.",
                tipo="strength"
            )

        # Callout: principal riesgo
        if riesgos:
            worst = riesgos[0]
            pdf.add_insight_box(
                f"Principal area de atencion: {worst[0]} con un puntaje promedio de {worst[1]:.2f}. "
                f"Se recomienda una intervencion prioritaria en esta dimension.",
                tipo="risk"
            )

        pdf.add_divider()
        pdf.add_page_break()

    # ───────────────────────────────────────────────────────
    # SECCIÓN 2: CARACTERIZACIÓN SOCIODEMOGRÁFICA
    # ───────────────────────────────────────────────────────

    def _build_sociodemographic(self, pdf):
        pdf.add_title("1. CARACTERIZACION SOCIODEMOGRAFICA", level=1)
        pdf.add_paragraph(
            "A continuacion se presenta la distribucion de los participantes "
            "segun sus principales caracteristicas demograficas y laborales."
        )

        # Buscar columnas SD disponibles
        sd_vars = [
            ("(SD)Sexo",      "Distribucion por Sexo"),
            ("(SD)Edad",      "Distribucion por Edad"),
        ]

        # Gráficas en pares lado a lado
        pair = []
        for col, label in sd_vars:
            chart_bytes = self.analytics.generate_sociodemographic_chart(col, label)
            if chart_bytes:
                pair.append((chart_bytes, label))

            if len(pair) == 2:
                pdf.insert_two_charts(
                    pair[0][0], pair[1][0],
                    caption_left=pair[0][1],
                    caption_right=pair[1][1],
                )
                pair = []

        # Si queda un impar
        if pair:
            pdf.insert_chart(
                pair[0][0],
                caption=pair[0][1],
                width_pct=0.6,
            )

        # Buscar variables laborales
        lab_vars = []
        for col in self.df.columns:
            if col.startswith("(SD)") and col not in ["(SD)Sexo", "(SD)Edad"]:
                lab_vars.append((col, col.replace("(SD)", "").strip()))

        if lab_vars:
            pdf.add_title("Caracteristicas Laborales", level=2)
            pair = []
            for col, label in lab_vars[:4]:  # Máximo 4 variables
                chart_bytes = self.analytics.generate_sociodemographic_chart(col, label)
                if chart_bytes:
                    pair.append((chart_bytes, label))
                if len(pair) == 2:
                    pdf.insert_two_charts(
                        pair[0][0], pair[1][0],
                        caption_left=pair[0][1],
                        caption_right=pair[1][1],
                    )
                    pair = []
            if pair:
                pdf.insert_chart(pair[0][0], caption=pair[0][1], width_pct=0.6)

        pdf.add_divider()
        pdf.add_page_break()

    # ───────────────────────────────────────────────────────
    # SECCIÓN 3: DIAGNÓSTICO DE BIENESTAR
    # ───────────────────────────────────────────────────────

    def _build_bienestar_diagnosis(self, pdf, promedios, fortalezas, riesgos):
        pdf.add_title("2. DIAGNOSTICO DE BIENESTAR", level=1)

        # Intro con escala
        pdf.add_paragraph(
            "Las dimensiones de bienestar fueron evaluadas en escalas tipo Likert "
            "(tipicamente de 1 a 7, donde 1 = muy bajo y 7 = muy alto). "
            "A continuacion se presenta el diagnostico visual (semaforo) que clasifica "
            "cada dimension como Fortaleza (verde), Intermedio (amarillo) o Riesgo (rojo)."
        )

        # Gráfica semáforo
        semaforo_bytes = self.analytics.generate_traffic_light_chart(promedios)
        if semaforo_bytes:
            pdf.insert_chart(
                semaforo_bytes,
                intro="La siguiente grafica muestra el puntaje promedio de cada dimension "
                      "y su clasificacion segun el semaforo de bienestar:",
                caption="Figura 1: Semaforo de dimensiones de bienestar organizacional.",
                interpretation="Los colores indican: verde = fortaleza del equipo, "
                               "amarillo = zona intermedia que merece monitoreo, "
                               "rojo = area critica que requiere intervencion.",
                width_pct=0.9,
            )

        # 2.1 Fortalezas
        if fortalezas:
            pdf.add_title("2.1 Fortalezas Identificadas", level=2)
            pdf.add_paragraph(
                "Las siguientes dimensiones obtuvieron puntajes elevados, "
                "indicando areas de buen desempeno en la organizacion:"
            )
            for dim, val in fortalezas:
                pdf.add_insight_box(
                    f"{dim}: puntaje promedio de {val:.2f}. "
                    f"Esta dimension se encuentra en zona positiva.",
                    tipo="strength"
                )
            pdf.add_paragraph(
                "Recomendacion: mantener las practicas actuales que sostienen "
                "estos resultados positivos e identificar los factores que contribuyen "
                "a estos logros para replicarlos en otras areas."
            )

        # 2.2 Riesgos
        if riesgos:
            pdf.add_title("2.2 Areas de Atencion", level=2)
            pdf.add_paragraph(
                "Las siguientes dimensiones mostraron puntajes preocupantes "
                "y requieren atencion prioritaria:"
            )
            for dim, val in riesgos:
                pdf.add_insight_box(
                    f"{dim}: puntaje promedio de {val:.2f}. "
                    f"Esta dimension se encuentra en zona de riesgo.",
                    tipo="risk"
                )
            pdf.add_paragraph(
                "Se sugiere disenar intervenciones focalizadas en estas dimensiones, "
                "involucrando a los equipos de gestion humana y salud ocupacional."
            )

        pdf.add_divider()
        pdf.add_page_break()

    # ───────────────────────────────────────────────────────
    # SECCIÓN 4: ANÁLISIS POR GRUPOS
    # ───────────────────────────────────────────────────────

    def _build_group_analysis(self, pdf, promedios):
        pdf.add_title("3. ANALISIS COMPARATIVO POR GRUPOS", level=1)
        pdf.add_paragraph(
            "Esta seccion presenta las comparaciones entre subgrupos demograficos, "
            "permitiendo identificar diferencias significativas en los niveles de bienestar."
        )

        comparative_results = self.analytics.generate_comparative_charts(promedios)

        if comparative_results:
            for chart_bytes, title in comparative_results[:5]:  # Limitar a 5
                pdf.insert_chart(
                    chart_bytes,
                    caption=title,
                    width_pct=0.85,
                )
        else:
            pdf.add_insight_box(
                "No se encontraron variables de agrupacion suficientes para "
                "generar comparaciones entre subgrupos.",
                tipo="warning"
            )

        # Correlación
        corr_bytes = self.analytics.generate_correlation_matrix()
        if corr_bytes:
            pdf.add_title("Matriz de Correlaciones", level=2)
            pdf.insert_chart(
                corr_bytes,
                intro="La siguiente matriz muestra la correlacion entre las variables medidas:",
                caption="Figura: Matriz de correlacion entre dimensiones.",
                interpretation="Los tonos rojos indican correlacion negativa y los azules positiva. "
                               "Correlaciones fuertes (>0.5 o <-0.5) sugieren variables interdependientes.",
                width_pct=0.85,
            )

        pdf.add_divider()
        pdf.add_page_break()

    # ───────────────────────────────────────────────────────
    # SECCIÓN 5: RECOMENDACIONES (IA)
    # ───────────────────────────────────────────────────────

    def _build_recommendations(self, pdf, promedios, fortalezas, riesgos):
        pdf.add_title("4. RECOMENDACIONES ESTRATEGICAS", level=1)
        pdf.add_paragraph(
            "Las siguientes recomendaciones fueron generadas por inteligencia artificial "
            "con base en los resultados del estudio, integrando conocimiento de psicologia "
            "organizacional y modelos de bienestar laboral."
        )

        try:
            ai_text = self.analytics.generate_ai_analysis(promedios, fortalezas, riesgos)
            if ai_text and "Error" not in ai_text[:10]:
                pdf.add_markdown(ai_text)
            else:
                pdf.add_insight_box(
                    "No fue posible generar el analisis automatizado. "
                    "Esto puede deberse a que la API key de Gemini no esta configurada.",
                    tipo="warning"
                )
        except Exception as e:
            pdf.add_insight_box(
                f"Error al generar recomendaciones IA: {str(e)[:100]}",
                tipo="warning"
            )

        pdf.add_divider()

    # ───────────────────────────────────────────────────────
    # SECCIÓN 6: REFERENCIAS
    # ───────────────────────────────────────────────────────

    def _build_references(self, pdf):
        pdf.add_title("5. REFERENCIAS BIBLIOGRAFICAS", level=1)

        refs = [
            "Maslach, C., & Jackson, S. E. (1981). The measurement of experienced burnout. "
            "Journal of Organizational Behavior, 2(2), 99-113.",

            "Karasek, R. A. (1979). Job demands, job decision latitude, and mental strain: "
            "Implications for job redesign. Administrative Science Quarterly, 24(2), 285-308.",

            "Organizacion Mundial de la Salud (2022). Directrices de la OMS sobre salud mental "
            "en el trabajo. Ginebra: OMS.",

            "Schaufeli, W. B., & Bakker, A. B. (2004). Job demands, job resources, and their "
            "relationship with burnout and engagement. Journal of Organizational Behavior, 25(3), 293-315.",

            "Siegrist, J. (1996). Adverse health effects of high-effort/low-reward conditions. "
            "Journal of Occupational Health Psychology, 1(1), 27-41.",
        ]

        for ref in refs:
            pdf.add_paragraph(ref, style="body")
