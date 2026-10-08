"""
Alertas con los datos reales (spec §5.4 y §7). Se omiten si faltan los archivos.

Las calibraciones son las de la spec, con los formularios vigentes el 6-oct-2026
(secundaria del 18-sep; primaria xlsx hasta el 6-oct). Cuando llegue la
exportación nueva de secundaria (spec §9) cambian: se actualizan con la cifra
nueva; nunca se ensancha la tolerancia. Ninguna prueba imprime casos: solo
porcentajes de todo el nivel.
"""
import pandas as pd
import pytest

from src.core.rutas import carpeta_datos
from src.core.texto import norm_txt
from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, publicar, scoring, supresion


@pytest.fixture(scope="module")
def rutas():
    r = pipeline.localizar_formularios(carpeta_datos("estudiantes"))
    if len(r) < 2:
        pytest.skip("faltan los formularios")
    return r


@pytest.fixture(scope="module")
def puntuado(rutas):
    bruto, _ = ingest.cargar_varios(rutas)
    return scoring.puntuar(bruto)


@pytest.fixture(scope="module")
def analisis(rutas):
    a, _ = pipeline.cargar_y_analizar(rutas, n_boot=20)
    return a


def _pct(serie) -> float:
    return round(100 * float(serie.dropna().mean()), 1)


@pytest.mark.parametrize("nivel,umbral,esperado", [
    (cat.NIVEL_SECUNDARIA, 3, 8.8), (cat.NIVEL_PRIMARIA, 3, 15.1),
    (cat.NIVEL_SECUNDARIA, 2, 22.0), (cat.NIVEL_PRIMARIA, 2, 32.4)])
def test_calibracion_del_malestar(puntuado, nivel, umbral, esperado):
    d = puntuado[puntuado["nivel"] == nivel]
    assert _pct(al.senal_malestar(d, umbral)) == pytest.approx(esperado, abs=0.6)


def test_calibracion_de_la_desesperanza(puntuado):
    d = puntuado[puntuado["nivel"] == cat.NIVEL_SECUNDARIA]
    assert _pct(al.senal_desesperanza(d)) == pytest.approx(17.0, abs=0.6)
    por_grado = [_pct(al.senal_desesperanza(g)) for grado, g in d.groupby("Grado")
                 if grado in cat.ORDEN_GRADOS_SEC]
    assert min(por_grado) == pytest.approx(10.8, abs=0.6)
    assert max(por_grado) == pytest.approx(21.5, abs=0.6)


def test_la_cifra_de_la_tarjeta_de_muerte_no_cambia(puntuado):
    d = puntuado[puntuado["nivel"] == cat.NIVEL_SECUNDARIA]
    item = d[f"RCADS{cat.RCADS_ITEM_MUERTE}"]
    assert _pct((item >= 2).astype(float).where(item.notna())) == pytest.approx(24.9, abs=0.2)


def _encabezados(ruta) -> list:
    lector = pd.read_excel if str(ruta).lower().endswith((".xlsx", ".xls")) else pd.read_csv
    return list(lector(ruta, nrows=0).columns)     # solo encabezados, ninguna respuesta


def test_los_items_con_asterisco_coinciden_con_el_catalogo(rutas):
    for ruta in rutas:
        cols = _encabezados(ruta)
        nivel = (cat.NIVEL_SECUNDARIA if any(norm_txt(c).startswith("rcads") for c in cols)
                 else cat.NIVEL_PRIMARIA)
        assert al.items_marcados_por_escala(cols) == ac.items_marcados_esperados(nivel), nivel


def test_la_auditoria_cubre_las_alertas_reales(analisis):
    assert publicar.verificar_restas(analisis) == []
    for nivel, a in analisis.items():
        assert not [p for p in supresion.auditar(a) if p.startswith("alerta")], nivel


def test_el_total_de_cada_nivel_muestra_su_cifra(analisis):
    """Si falla para la desesperanza, sus bases no coinciden con las del ítem 18 en
    algún grupo (falla cerrado): informar al usuario, no relajar la regla."""
    for nivel, a in analisis.items():
        total = a.alertas[a.alertas["agrupacion"] == al.TOTAL]
        assert set(total["alerta"]) == set(al.claves_del_nivel(a.datos, nivel)), nivel
        assert total["pct"].notna().all(), nivel


def test_ninguna_fila_de_alerta_publicada_trae_casos(analisis):
    filas = publicar.aplanar(analisis)
    publicar.verificar(filas)
    assert not [f for f in filas if f["tipo"].startswith("alerta")
                and set(f["detalle"]) & set(publicar.CAMPOS_CONTEO_PROHIBIDOS)]
