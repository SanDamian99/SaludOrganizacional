"""Lista de los investigadores (6-oct-2026), sobre conteos crudos del formulario.

Solo se comprueban los colegios cuyos datos ya llegaron completos; al recibir la
exportación nueva de secundaria se añaden CdP, JJC y SJMEB.
"""
import pytest

from src.core.rutas import carpeta_datos
from src.estudiantes import pipeline, publicar, privacidad
from src.ui.views import estudiantes_comunidad as vc

LISTA = {
    "secundaria": {"LaBalsa": {"Sexto": 24, "Séptimo": 52, "Noveno": 29, "Décimo": 32},
                   "LauV": {"Sexto": 95, "Séptimo": 69, "Octavo": 93, "Noveno": 90,
                            "Décimo": 90}},
    "primaria": {"LauV": {"Cuarto": 86, "Quinto": 98}},
}


@pytest.fixture(scope="module")
def real():
    rutas = pipeline.localizar_formularios(carpeta_datos("estudiantes"))
    if len(rutas) < 2:
        pytest.skip("faltan los formularios")
    return pipeline.cargar_y_analizar(rutas, n_boot=20)


def test_los_conteos_crudos_coinciden_con_la_lista(real):
    _, informes = real
    crudos = {i.nivel: i.crudo_colegio_grado for i in informes}
    for nivel, colegios in LISTA.items():
        for colegio, grados in colegios.items():
            for grado, n in grados.items():
                assert crudos[nivel][privacidad.clave_celda(colegio, grado)] == n, \
                    f"{nivel} {colegio} {grado}"


def test_todos_esos_grados_se_ven_dentro_de_su_colegio(real):
    analisis, _ = real
    for nivel, colegios in LISTA.items():
        for colegio, grados in colegios.items():
            visibles = vc.grupos_publicables(analisis[nivel], "Grado", colegio)
            assert set(grados) <= set(visibles), f"{nivel} {colegio}: {visibles}"


def test_la_auditoria_de_restas_pasa_con_los_datos_reales(real):
    analisis, _ = real
    assert publicar.verificar_restas(analisis) == []
