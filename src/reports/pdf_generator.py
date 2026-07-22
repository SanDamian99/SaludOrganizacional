"""
Sistema de generación de PDF profesional — Observatorio de Salud Organizacional.
Librería: ReportLab (Platypus)

Design system: paleta institucional azul, tipografía Helvetica,
portada profesional, callouts, KPI tables, integración texto-gráfica.
"""
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    HRFlowable, Table as RLTable, TableStyle, PageBreak,
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.platypus.doctemplate import LayoutError
from PIL import Image as PILImage
import io
import os
import re
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# PALETA DE COLORES
# ═══════════════════════════════════════════════════════════════

COLORS = {
    # Principales
    "brand_blue":       "#1B3A6B",
    "brand_blue_mid":   "#2E5FAC",
    "brand_blue_light": "#EBF1FB",
    # Semáforo
    "strength":         "#1A7F4B",
    "strength_light":   "#D6F0E4",
    "medium":           "#B07D0D",
    "medium_light":     "#FFF3CD",
    "risk":             "#C0392B",
    "risk_light":       "#FDECEA",
    # Neutros
    "text_primary":     "#1A1A2E",
    "text_secondary":   "#4A4A6A",
    "divider":          "#CBD5E1",
    "background_alt":   "#F8FAFC",
    "white":            "#FFFFFF",
}

# ═══════════════════════════════════════════════════════════════
# TIPOGRAFÍA Y SPACING
# ═══════════════════════════════════════════════════════════════

FONTS = {
    "title":      ("Helvetica-Bold",       22),
    "h1":         ("Helvetica-Bold",       16),
    "h2":         ("Helvetica-Bold",       13),
    "h3":         ("Helvetica-BoldOblique", 11),
    "body":       ("Helvetica",            10),
    "body_small": ("Helvetica",             9),
    "caption":    ("Helvetica-Oblique",     8),
    "label":      ("Helvetica-Bold",        9),
    "footer":     ("Helvetica",             8),
}

SPACING = {
    "page_margin":    2.0 * cm,
    "section_before": 0.6 * cm,
    "para_spacing":   0.3 * cm,
    "chart_margin":   0.4 * cm,
}

# ═══════════════════════════════════════════════════════════════
# ESTILOS PARAGRAPH (Platypus)
# ═══════════════════════════════════════════════════════════════

def build_styles() -> dict:
    """Retorna diccionario con todos los estilos del reporte."""
    return {
        "h1": ParagraphStyle(
            "H1Report",
            fontName="Helvetica-Bold", fontSize=15,
            textColor=HexColor(COLORS["brand_blue"]),
            spaceBefore=18, spaceAfter=6, leading=20,
        ),
        "h2": ParagraphStyle(
            "H2Report",
            fontName="Helvetica-Bold", fontSize=12,
            textColor=HexColor(COLORS["brand_blue_mid"]),
            spaceBefore=14, spaceAfter=4, leading=16,
        ),
        "h3": ParagraphStyle(
            "H3Report",
            fontName="Helvetica-BoldOblique", fontSize=10,
            textColor=HexColor(COLORS["text_secondary"]),
            spaceBefore=10, spaceAfter=3, leading=14,
        ),
        "body": ParagraphStyle(
            "BodyReport",
            fontName="Helvetica", fontSize=10,
            textColor=HexColor(COLORS["text_primary"]),
            spaceAfter=6, leading=15, alignment=TA_JUSTIFY,
        ),
        "caption": ParagraphStyle(
            "CaptionReport",
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=HexColor(COLORS["text_secondary"]),
            spaceAfter=10, leading=11, alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "CalloutReport",
            fontName="Helvetica", fontSize=10,
            textColor=HexColor(COLORS["text_primary"]),
            backColor=HexColor(COLORS["brand_blue_light"]),
            borderColor=HexColor(COLORS["brand_blue_mid"]),
            borderWidth=1, borderPadding=(8, 10, 8, 10),
            spaceAfter=10, leading=15, alignment=TA_JUSTIFY,
        ),
        "bullet": ParagraphStyle(
            "BulletReport",
            fontName="Helvetica", fontSize=10,
            textColor=HexColor(COLORS["text_primary"]),
            spaceAfter=4, leading=14, leftIndent=16, bulletIndent=6,
        ),
    }


# ═══════════════════════════════════════════════════════════════
# PORTADA
# ═══════════════════════════════════════════════════════════════

def build_cover_page(canvas, doc, report_title="Informe de Diagnóstico",
                     org_name="Organización", date_str=None, n_participants=None):
    """Portada profesional con banda azul superior e inferior."""
    width, height = letter
    if date_str is None:
        date_str = datetime.now().strftime("%d de %B de %Y")

    canvas.saveState()

    # === BANDA SUPERIOR (30%) ===
    canvas.setFillColor(HexColor(COLORS["brand_blue"]))
    canvas.rect(0, height * 0.70, width, height * 0.30, fill=1, stroke=0)

    canvas.setFillColor(HexColor(COLORS["white"]))
    canvas.setFont(*FONTS["h2"])
    canvas.drawCentredString(width / 2, height * 0.88,
                             "OBSERVATORIO DE SALUD ORGANIZACIONAL")
    canvas.setFont(*FONTS["body"])
    canvas.drawCentredString(width / 2, height * 0.83,
                             "Facultad de Ciencias del Comportamiento")

    # === TÍTULO PRINCIPAL ===
    canvas.setFillColor(HexColor(COLORS["brand_blue"]))
    canvas.setFont("Helvetica-Bold", 20)
    # Wrap title if too long
    if len(report_title) > 50:
        mid = len(report_title) // 2
        space = report_title.rfind(' ', 0, mid)
        if space > 0:
            canvas.drawCentredString(width / 2, height * 0.60, report_title[:space])
            canvas.drawCentredString(width / 2, height * 0.56, report_title[space+1:])
        else:
            canvas.drawCentredString(width / 2, height * 0.58, report_title)
    else:
        canvas.drawCentredString(width / 2, height * 0.58, report_title)

    # Línea decorativa
    canvas.setStrokeColor(HexColor(COLORS["brand_blue_mid"]))
    canvas.setLineWidth(2)
    canvas.line(SPACING["page_margin"], height * 0.53,
                width - SPACING["page_margin"], height * 0.53)

    # Metadatos
    canvas.setFillColor(HexColor(COLORS["text_secondary"]))
    y = height * 0.46
    for label, value in [
        ("Organización:", org_name),
        ("Fecha del informe:", date_str),
    ]:
        canvas.setFont(*FONTS["label"])
        canvas.drawString(SPACING["page_margin"] * 2, y, label)
        canvas.setFont(*FONTS["body"])
        canvas.drawString(SPACING["page_margin"] * 2 + 4 * cm, y, value)
        y -= 0.6 * cm

    if n_participants:
        canvas.setFont(*FONTS["label"])
        canvas.drawString(SPACING["page_margin"] * 2, y, "Participantes:")
        canvas.setFont(*FONTS["body"])
        canvas.drawString(SPACING["page_margin"] * 2 + 4 * cm, y,
                          f"{n_participants:,}")

    # === BANDA INFERIOR ===
    canvas.setFillColor(HexColor(COLORS["brand_blue"]))
    canvas.rect(0, 0, width, 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(HexColor(COLORS["white"]))
    canvas.setFont(*FONTS["footer"])
    canvas.drawCentredString(width / 2, 0.4 * cm,
                             "Documento confidencial · Generado automáticamente")

    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════
# HEADER / FOOTER (páginas internas)
# ═══════════════════════════════════════════════════════════════

def build_header_footer(canvas, doc):
    """Header y footer para todas las páginas excepto portada."""
    canvas.saveState()
    width, height = letter
    margin = SPACING["page_margin"]

    # Header: línea + texto
    canvas.setStrokeColor(HexColor(COLORS["brand_blue_mid"]))
    canvas.setLineWidth(1)
    canvas.line(margin, height - margin * 0.7,
                width - margin, height - margin * 0.7)

    canvas.setFillColor(HexColor(COLORS["text_secondary"]))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(margin, height - margin * 0.55,
                      "Observatorio de Salud Organizacional")
    canvas.drawRightString(width - margin, height - margin * 0.55,
                           f"Página {doc.page}")

    # Footer: línea + texto
    canvas.setStrokeColor(HexColor(COLORS["brand_blue"]))
    canvas.setLineWidth(1.5)
    canvas.line(margin, margin * 0.7, width - margin, margin * 0.7)

    canvas.setFillColor(HexColor(COLORS["text_secondary"]))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(margin, margin * 0.4, "Documento confidencial")
    canvas.drawRightString(width - margin, margin * 0.4,
                           f"Generado: {datetime.now().strftime('%d/%m/%Y')}")

    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════
# COMPONENTES VISUALES
# ═══════════════════════════════════════════════════════════════

def add_section_divider(story: list):
    """Línea decorativa entre secciones."""
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(
        width="100%", thickness=1.5,
        color=HexColor(COLORS["brand_blue_mid"]),
        spaceAfter=0.4 * cm,
    ))


def add_insight_box(story: list, text: str, styles: dict, tipo: str = "info"):
    """Caja de texto destacado (callout)."""
    color_map = {
        "info":     (COLORS["brand_blue_light"], COLORS["brand_blue_mid"]),
        "strength": (COLORS["strength_light"],   COLORS["strength"]),
        "risk":     (COLORS["risk_light"],        COLORS["risk"]),
        "warning":  (COLORS["medium_light"],      COLORS["medium"]),
    }
    bg, border = color_map.get(tipo, color_map["info"])
    icon_map = {"info": "&#128161;", "strength": "&#9989;", "risk": "&#9888;", "warning": "&#128204;"}
    icon = icon_map.get(tipo, "")

    style = ParagraphStyle(
        f"Callout_{tipo}_{id(text)}",
        parent=styles["body"],
        backColor=HexColor(bg),
        borderColor=HexColor(border),
        borderWidth=1.5,
        borderPadding=(10, 12, 10, 12),
        leftIndent=0,
    )
    story.append(Paragraph(f"{icon} {clean_text(text)}", style))
    story.append(Spacer(1, SPACING["para_spacing"]))


def add_kpi_table(story: list, metrics: list, styles: dict):
    """
    Tabla visual de métricas clave.
    metrics: list of (label, value, unit, color_key)
    """
    page_width = letter[0] - 2 * SPACING["page_margin"]
    n = len(metrics)
    if n == 0:
        return
    col_width = page_width / n

    header_row = []
    value_row = []
    unit_row = []

    for label, value, unit, color_key in metrics:
        color = COLORS.get(color_key, COLORS["brand_blue"])
        header_row.append(Paragraph(
            f'<font size="8" color="{COLORS["text_secondary"]}">{clean_text(label)}</font>',
            styles["caption"]
        ))
        value_row.append(Paragraph(
            f'<font size="20" color="{color}"><b>{clean_text(str(value))}</b></font>',
            ParagraphStyle("KPIVal", alignment=TA_CENTER, leading=28)
        ))
        unit_row.append(Paragraph(
            f'<font size="8" color="{COLORS["text_secondary"]}">{clean_text(unit)}</font>',
            styles["caption"]
        ))

    t = RLTable(
        [header_row, value_row, unit_row],
        colWidths=[col_width] * n,
        rowHeights=[0.5 * cm, 1.2 * cm, 0.4 * cm]
    )
    t.setStyle(TableStyle([
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",  (0, 0), (-1, 0), HexColor(COLORS["background_alt"])),
        ("BACKGROUND",  (0, 1), (-1, 1), HexColor(COLORS["white"])),
        ("BACKGROUND",  (0, 2), (-1, 2), HexColor(COLORS["background_alt"])),
        ("GRID",        (0, 0), (-1, -1), 0.5, HexColor(COLORS["divider"])),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, SPACING["section_before"]))


def add_data_table(story: list, headers: list, rows: list, styles: dict):
    """Tabla de datos con encabezado azul y filas alternadas (para anexos técnicos)."""
    if not rows:
        return
    page_width = letter[0] - 2 * SPACING["page_margin"]
    ncols = len(headers)
    first = page_width * 0.34
    rest = (page_width - first) / max(1, ncols - 1)
    col_widths = [first] + [rest] * (ncols - 1)

    head_style = ParagraphStyle(
        "THead", fontName="Helvetica-Bold", fontSize=8,
        textColor=HexColor(COLORS["white"]), alignment=TA_CENTER, leading=10)
    cell_c = ParagraphStyle(
        "TCellC", fontName="Helvetica", fontSize=8,
        textColor=HexColor(COLORS["text_primary"]), alignment=TA_CENTER, leading=10)
    cell_l = ParagraphStyle(
        "TCellL", fontName="Helvetica", fontSize=8,
        textColor=HexColor(COLORS["text_primary"]), alignment=TA_LEFT, leading=10)

    data = [[Paragraph(clean_text(str(h)), head_style) for h in headers]]
    for r in rows:
        data.append([
            Paragraph(clean_text(str(v)), cell_l if i == 0 else cell_c)
            for i, v in enumerate(r)
        ])

    t = RLTable(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HexColor(COLORS["brand_blue"])),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [HexColor(COLORS["white"]), HexColor(COLORS["background_alt"])]),
        ("GRID",          (0, 0), (-1, -1), 0.4, HexColor(COLORS["divider"])),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, SPACING["section_before"]))


# ═══════════════════════════════════════════════════════════════
# INTEGRACIÓN TEXTO → GRÁFICA → INTERPRETACIÓN
# ═══════════════════════════════════════════════════════════════

def insert_chart_with_context(
    story: list, fig_bytes, intro_text: str, caption: str,
    interpretation: str, styles: dict, width_pct: float = 0.85,
):
    """Inserta gráfica con contexto textual: intro → imagen → caption → interpretación."""
    page_width = letter[0] - 2 * SPACING["page_margin"]
    img_width = page_width * width_pct

    if intro_text:
        story.append(Paragraph(clean_text(intro_text), styles["body"]))
        story.append(Spacer(1, SPACING["chart_margin"]))

    # Insert image
    if isinstance(fig_bytes, bytes):
        buf = io.BytesIO(fig_bytes)
    elif isinstance(fig_bytes, io.BytesIO):
        fig_bytes.seek(0)
        buf = fig_bytes
    else:
        # Matplotlib figure
        buf = io.BytesIO()
        fig_bytes.savefig(buf, format='png', dpi=130, bbox_inches='tight', pad_inches=0.25)
        buf.seek(0)
        import matplotlib.pyplot as plt
        plt.close(fig_bytes)

    with PILImage.open(buf) as pil_img:
        orig_w, orig_h = pil_img.size
    buf.seek(0)

    if orig_w > 0 and orig_h > 0:
        aspect = orig_h / orig_w
        draw_w = min(img_width, orig_w * 0.75)
        draw_h = draw_w * aspect
        max_h = 14 * cm
        if draw_h > max_h:
            draw_h = max_h
            draw_w = draw_h / aspect

        img = RLImage(buf, width=draw_w, height=draw_h)
        img.hAlign = 'CENTER'
        story.append(img)

    if caption:
        story.append(Paragraph(f"<i>{clean_text(caption)}</i>", styles["caption"]))

    story.append(Spacer(1, SPACING["chart_margin"]))

    if interpretation:
        story.append(Paragraph(clean_text(interpretation), styles["body"]))

    story.append(Spacer(1, SPACING["section_before"]))


def insert_two_charts_side_by_side(
    story: list, fig_bytes_left, fig_bytes_right,
    caption_left: str, caption_right: str, styles: dict,
):
    """Coloca dos gráficas lado a lado en columnas."""
    page_width = letter[0] - 2 * SPACING["page_margin"]
    col_width = (page_width - 0.5 * cm) / 2

    def make_img(fb, width):
        if isinstance(fb, bytes):
            buf = io.BytesIO(fb)
        elif isinstance(fb, io.BytesIO):
            fb.seek(0)
            buf = fb
        else:
            buf = io.BytesIO()
            fb.savefig(buf, format='png', dpi=130, bbox_inches='tight', pad_inches=0.2)
            buf.seek(0)
            import matplotlib.pyplot as plt
            plt.close(fb)

        with PILImage.open(buf) as pil_img:
            orig_w, orig_h = pil_img.size
        buf.seek(0)

        if orig_w == 0:
            return None
        aspect = orig_h / orig_w
        img = RLImage(buf, width=width, height=width * aspect)
        img.hAlign = 'CENTER'
        return img

    img_l = make_img(fig_bytes_left, col_width)
    img_r = make_img(fig_bytes_right, col_width)

    if img_l and img_r:
        cap_l = Paragraph(f"<i>{clean_text(caption_left)}</i>", styles["caption"])
        cap_r = Paragraph(f"<i>{clean_text(caption_right)}</i>", styles["caption"])

        t = RLTable([[img_l, img_r], [cap_l, cap_r]],
                    colWidths=[col_width, col_width])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, SPACING["section_before"]))


# ═══════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════

def clean_text(text: str) -> str:
    """Limpia texto para ReportLab XML."""
    if not isinstance(text, str):
        text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    replacements = {
        '\u2013': '-', '\u2014': '--', '\u2018': "'", '\u2019': "'",
        '\u201C': '"', '\u201D': '"', '\u2022': '* ', '\u00A0': ' ',
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    try:
        text = text.encode('latin-1', 'ignore').decode('latin-1')
    except Exception:
        try:
            text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        except Exception:
            pass
    return text


def add_markdown(story: list, md_text: str, styles: dict):
    """Convierte markdown básico a flowables de ReportLab."""
    if not md_text:
        return

    paragraphs = md_text.split('\n\n')
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue

        if p.startswith('### '):
            story.append(Paragraph(clean_text(p[4:]), styles["h3"]))
        elif p.startswith('## '):
            story.append(Paragraph(clean_text(p[3:]), styles["h2"]))
        elif p.startswith('# '):
            story.append(Paragraph(clean_text(p[2:]), styles["h1"]))
        elif p.startswith('- ') or p.startswith('* '):
            items = p.split('\n')
            for item in items:
                item = item.strip()
                if item.startswith('-') or item.startswith('*'):
                    cleaned = item[2:].strip()
                    # Bold inside lists
                    cleaned = _apply_inline_formatting(cleaned)
                    story.append(Paragraph(f"&bull; {cleaned}", styles["bullet"]))
        else:
            text = _apply_inline_formatting(p)
            story.append(Paragraph(text, styles["body"]))

        story.append(Spacer(1, 4))


def _apply_inline_formatting(text: str) -> str:
    """Aplica negritas e itálicas básicas de markdown."""
    text = clean_text(text)
    # **bold** → <b>bold</b> (must come before single *)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # *italic* → <i>italic</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return text


# ═══════════════════════════════════════════════════════════════
# CLASE PRINCIPAL PDFReport (compatibilidad con report_builder)
# ═══════════════════════════════════════════════════════════════

class PDFReport:
    """Wrapper de alto nivel para construir el PDF."""

    def __init__(self, filename: str, report_title: str = "Informe de Diagnóstico",
                 org_name: str = "Organización", n_participants: int = None):
        self.filename = filename
        self.report_title = report_title
        self.org_name = org_name
        self.n_participants = n_participants
        self.elements = []
        self.styles = build_styles()
        self.doc = SimpleDocTemplate(
            filename, pagesize=letter,
            rightMargin=SPACING["page_margin"],
            leftMargin=SPACING["page_margin"],
            topMargin=SPACING["page_margin"],
            bottomMargin=SPACING["page_margin"],
        )

    def add_title(self, text: str, level: int = 1):
        style_key = {1: "h1", 2: "h2", 3: "h3"}.get(level, "h1")
        self.elements.append(Paragraph(clean_text(text), self.styles[style_key]))

    def add_paragraph(self, text: str, style: str = "body"):
        s = self.styles.get(style, self.styles["body"])
        self.elements.append(Paragraph(clean_text(text), s))
        self.elements.append(Spacer(1, 3))

    def add_markdown(self, md_text: str):
        add_markdown(self.elements, md_text, self.styles)

    def add_spacer(self, height_cm: float = 0.5):
        self.elements.append(Spacer(1, height_cm * cm))

    def add_divider(self):
        add_section_divider(self.elements)

    def add_page_break(self):
        self.elements.append(PageBreak())

    def add_insight_box(self, text: str, tipo: str = "info"):
        add_insight_box(self.elements, text, self.styles, tipo)

    def add_kpi_table(self, metrics: list):
        add_kpi_table(self.elements, metrics, self.styles)

    def add_metrics_table(self, headers: list, rows: list):
        add_data_table(self.elements, headers, rows, self.styles)

    def insert_chart(self, fig_bytes, intro: str = "", caption: str = "",
                     interpretation: str = "", width_pct: float = 0.85):
        insert_chart_with_context(
            self.elements, fig_bytes, intro, caption,
            interpretation, self.styles, width_pct
        )

    def insert_two_charts(self, left, right, caption_left="", caption_right=""):
        insert_two_charts_side_by_side(
            self.elements, left, right,
            caption_left, caption_right, self.styles
        )

    def insert_image(self, image_source, max_width_mm=170, max_height_mm=160):
        """Compatibilidad: inserta imagen desde path, fig matplotlib, o BytesIO."""
        try:
            if isinstance(image_source, str) and os.path.isfile(image_source):
                with PILImage.open(image_source) as pil_img:
                    orig_w, orig_h = pil_img.size
                src = os.path.abspath(image_source)
            elif hasattr(image_source, 'savefig'):
                buf = io.BytesIO()
                image_source.savefig(buf, format='png', dpi=130,
                                     bbox_inches='tight', pad_inches=0.25)
                buf.seek(0)
                with PILImage.open(buf) as pil_img:
                    orig_w, orig_h = pil_img.size
                buf.seek(0)
                src = buf
            elif isinstance(image_source, io.BytesIO):
                image_source.seek(0)
                with PILImage.open(image_source) as pil_img:
                    orig_w, orig_h = pil_img.size
                image_source.seek(0)
                src = image_source
            else:
                self.add_paragraph(f"Error: imagen no válida ({type(image_source)})")
                return

            if orig_w == 0 or orig_h == 0:
                return

            max_w = max_width_mm * mm
            max_h = max_height_mm * mm
            ratio = orig_h / orig_w
            draw_w = min(max_w, orig_w * 0.75)
            draw_h = draw_w * ratio
            if draw_h > max_h:
                draw_h = max_h
                draw_w = draw_h / ratio

            img = RLImage(src, width=draw_w, height=draw_h)
            img.hAlign = 'CENTER'
            self.elements.append(img)
            self.elements.append(Spacer(1, 10))

        except Exception as e:
            self.add_paragraph(f"Error procesando imagen: {e}")

    def _on_first_page(self, canvas, doc):
        build_cover_page(canvas, doc,
                         report_title=self.report_title,
                         org_name=self.org_name,
                         n_participants=self.n_participants)

    def build_pdf(self):
        """Construye el PDF con portada + páginas internas."""
        try:
            # Insert page break after cover
            self.elements.insert(0, PageBreak())

            self.doc.build(
                self.elements,
                onFirstPage=self._on_first_page,
                onLaterPages=build_header_footer,
            )
            return True
        except LayoutError as e:
            print(f"Error PDF Layout: {e}")
            raise e
        except Exception as e:
            print(f"Error PDF Build: {e}")
            raise e
