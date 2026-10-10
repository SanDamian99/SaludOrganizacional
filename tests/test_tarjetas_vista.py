"""Rejilla de tarjetas alineadas (src/ui/views/tarjetas.py): solo presentación."""
from __future__ import annotations

import re

from src.estudiantes import catalog as cat
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import estudiantes_comunidad as ve
from src.ui.views import tarjetas as vt

FICHAS = [
    vt.Ficha("Estrés de crianza", "14.4 de 40", "promedio del grupo",
             "IC 95 % 13.1–15.7; base de 120", "Significa uno.", "Hacer uno."),
    vt.Ficha("Apoyo que tiene", "1 de cada 5", "sienten poco apoyo",
             "20 % (IC 95 % 15–26)", "Significa dos.", "Hacer dos."),
    vt.Ficha("Seguridad del barrio", vc.CIFRA_SUPRIMIDA, "índice del barrio",
             cat.CIFRAS_PEQUENAS, "Significa tres.", "Hacer tres.", suprimida=True),
]


def _sin_etiquetas(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "", html)


def test_incluye_titulo_cifra_etiqueta_y_nota_de_cada_tarjeta():
    html = vt.rejilla_html(FICHAS)
    for f in FICHAS:
        for texto in (f.titulo, f.cifra, f.etiqueta, f.detalle):
            assert vt._e(texto) in html


def test_explicaciones_fuera_de_la_rejilla():
    rejilla = vt.rejilla_html(FICHAS)
    assert "Significa uno." not in rejilla and "Hacer uno." not in rejilla
    exp = vt.explicaciones_html(FICHAS)
    for f in FICHAS:
        assert f.significa in exp and f.accion in exp and f.titulo in exp
    assert exp.count("Qué significa</span>") == len(FICHAS)
    assert exp.count("Qué hacer</span>") == len(FICHAS)


def test_escapa_html():
    malo = vt.Ficha('<script>alert("x")</script>', "<b>1</b>", "a & b", "<i>n</i>",
                    "<img src=x>", "<a href=y>")
    html = vt.rejilla_html([malo]) + vt.explicaciones_html([malo])
    cuerpo = _sin_etiquetas(html)
    assert "<script>" not in cuerpo and "<b>1</b>" not in cuerpo
    assert "<img" not in cuerpo and "<a href" not in cuerpo and "<i>n" not in cuerpo
    assert "&lt;script&gt;" in cuerpo and "a &amp; b" in cuerpo


def test_estructura_de_alineacion():
    html = vt.rejilla_html(FICHAS)
    assert "grid-template-rows:subgrid" in html and "grid-row:span 4" in html
    assert "tabular-nums" in html
    # Cada tarjeta tiene las mismas cuatro filas, en el mismo orden.
    filas = re.findall(r'class="(t360-(?:titulo|cifra|etiqueta|nota))"', html)
    assert filas == ["t360-titulo", "t360-cifra", "t360-etiqueta", "t360-nota"] * len(FICHAS)
    assert html.count('role="listitem"') == len(FICHAS)
    assert 'data-n="3"' in html
    # Nunca rojo: el acento es naranja.
    assert not re.search(r"#(?:C0392B|FF0000|E74C3C)\b", html, re.I)


def test_hasta_cinco_columnas():
    seis = FICHAS * 2
    assert 'data-n="5"' in vt.rejilla_html(seis)
    assert vt.rejilla_html([]) == ""


def test_tarjeta_suprimida_conserva_las_filas():
    html = vt.rejilla_html([FICHAS[2]])
    assert "t360-card t360-suprimida" in html
    assert f'<div class="t360-cifra">{vc.CIFRA_SUPRIMIDA}</div>' in html
    assert vt._e(cat.CIFRAS_PEQUENAS) in html
    assert html.count('class="t360-nota"') == 1


def test_sin_texto_nuevo():
    """Fuera del CSS, todo texto visible sale de las fichas o de los encabezados fijos."""
    html = vt.rejilla_html(FICHAS) + vt.explicaciones_html(FICHAS)
    visibles = [t for t in re.findall(r">([^<>]+)<", _sin_etiquetas(html)) if t.strip()]
    permitidos = {vt._e(x) for f in FICHAS for x in
                  (f.titulo, f.cifra, f.etiqueta, f.detalle, f.significa, f.accion)}
    permitidos |= {"Qué significa", "Qué hacer"}
    assert set(visibles) <= permitidos


def test_adapta_las_tarjetas_de_las_dos_vistas():
    tc = vc.Tarjeta("estres", "Estrés de crianza", "14.4 de 40", "etq", "sig", "acc", "det")
    f = vt.ficha(tc)
    assert (f.titulo, f.cifra, f.etiqueta, f.detalle, f.significa, f.accion, f.suprimida) == \
        ("Estrés de crianza", "14.4 de 40", "etq", "det", "sig", "acc", False)
    te = ve.Tarjeta(clave="sdq", cifra="—", etiqueta="e", significa="s", accion="a",
                    detalle=cat.CIFRAS_PEQUENAS, suprimida=True)
    f = vt.ficha(te, "Título")
    assert f.titulo == "Título" and f.suprimida and f.detalle == cat.CIFRAS_PEQUENAS
