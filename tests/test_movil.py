"""Los ajustes de celular no tocan el escritorio y la tabla alternativa pinta bien."""
import re

import pandas as pd
import pytest

from src.docentes import catalogo as cat
from src.ui import docentes_items as di
from src.ui import movil


def _fuera_de_media(css: str) -> str:
    """El CSS sin los bloques @media (con llaves anidadas)."""
    salida, profundidad, i = [], 0, 0
    while i < len(css):
        if css.startswith("@media", i) and profundidad == 0:
            j = css.index("{", i)
            profundidad, i = 1, j + 1
            while profundidad:
                profundidad += {"{": 1, "}": -1}.get(css[i], 0)
                i += 1
            continue
        salida.append(css[i])
        i += 1
    return "".join(salida)


def test_toda_regla_visible_va_dentro_de_media_query():
    fuera = re.sub(r"/\*.*?\*/", "", _fuera_de_media(movil.CSS), flags=re.S).strip()
    # Lo único que vale para todos los anchos es esconder la tabla alternativa.
    assert fuera.replace(" ", "") == ".st-key-doc_items_movil{display:none;}"
    assert f"max-width: {movil.ANCHO_MAXIMO}px" in movil.CSS


def test_la_tabla_alternativa_se_muestra_solo_en_celular():
    dentro = movil.CSS.split("@media", 1)[1]
    assert ".st-key-doc_items_movil { display: block !important; }" in dentro
    assert ".st-key-doc_items_calor" in dentro and ".st-key-doc_items_tabla" in dentro


@pytest.mark.parametrize("pct,esperado", [(0, "#E8964A"), (50, "#F4EFE2"), (100, "#4FAE7E")])
def test_color_de_celda_en_los_extremos(pct, esperado):
    assert di.color_celda(pct) == esperado
    assert di.color_celda(None) == ""
    assert di.color_celda(float("nan")) == ""


def test_tabla_movil_deja_la_pregunta_fija_y_pinta_cada_celda():
    dim = cat.por_clave("Descon")
    medias = pd.DataFrame({"Todos": [3.0, 5.0, 1.0], "A <b>": [4.0, float("nan"), 2.0]},
                          index=list(dim.items))
    ns = pd.DataFrame({"Todos": [30, 30, 30], "A <b>": [12, 4, 12]}, index=list(dim.items))
    html = di.tabla_html_movil(medias, ns, dim)
    assert "position:sticky" in html and "overflow-x:auto" in html
    assert "4.00" in html and "—" in html
    assert "#4FAE7E" in html.upper()                                  # 5 en «mayor = mejor»
    assert "A &lt;b&gt;" in html and "<b>" not in html                # el nombre del grupo se escapa
    assert "n=12" in html
    assert html.count("<tr>") == len(dim.items) + 1
