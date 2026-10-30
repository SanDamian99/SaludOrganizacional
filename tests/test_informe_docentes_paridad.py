"""El PDF de Docentes y el dashboard dicen lo mismo (informe de inconsistencias, 30-oct-2026).

Antes el PDF leía los totales `*_T` y daba una «posición relativa en la muestra»; el
dashboard puntúa desde los ítems y ancla la zona a la escala. Ahora los dos parten de
`doc_scoring.para_vistas`.
"""
import pandas as pd

from src.docentes import catalogo as cat
from src.docentes import scoring as ds
from src.reports.indicator_report import IndicatorReportBuilder
from src.ui import dashboard as d
from tests import docentes_sinteticos as sint


def test_el_pdf_usa_los_mismos_indicadores_y_zonas_que_el_dashboard():
    df = sint.docentes()
    enr_dash, _ = d._resumen_docentes.__wrapped__(df)
    b = IndicatorReportBuilder(df)
    assert b.anclado
    assert list(b.enr) == list(enr_dash)
    for k, i in enr_dash.items():
        assert b.enr[k]["mean"] == i["mean"] and b.enr[k]["n"] == i["n"]
        assert b.enr[k]["level"] == i["level"] and b.enr[k]["oriented"] == i["oriented"]


def test_el_pdf_ignora_los_totales_precalculados_del_archivo():
    """Un `*_T` en sumas (archivos antiguos) no cambia lo que dice el PDF."""
    df = sint.docentes()
    sucio = df.copy()
    for c in [c for c in sucio.columns if str(c).endswith("_T")]:
        sucio[c] = pd.to_numeric(sucio[c], errors="coerce") * 7
    assert IndicatorReportBuilder(sucio).enr == IndicatorReportBuilder(df).enr


def test_el_foco_del_pdf_es_la_zona_a_vigilar_del_dashboard():
    df = sint.docentes()
    pss = [f"PSS{i}" for i in range(1, 11)]
    df[pss] = 3.0                      # PSS = 30 de 40: zona a vigilar
    b = IndicatorReportBuilder(df)
    assert b._nivel(b.enr["PSS"]) == "Atención"
    assert b.enr["PSS"]["zona"] == cat.ZONA_VIGILAR
    assert ds.resumen(df, solo_tablero=True)["PSS"]["zona"] == cat.ZONA_VIGILAR
