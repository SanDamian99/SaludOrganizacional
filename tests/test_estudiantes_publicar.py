"""
Pruebas del publicador de resultados de estudiantes.

Lo que se prueba aquí es la frontera de privacidad: qué sale de la máquina hacia
una base de datos en la nube. Si estas pruebas fallan, no se publica.
"""
import json
import os

import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import pipeline, publicar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ══ Guardas, con lotes construidos a mano ═══════════════════════════════════
def _fila_valida(**cambios):
    base = dict(nivel="secundaria", tipo="descriptivo", clave="SDQ_Total",
                escala="Total de dificultades", agrupacion="total", grupo=None,
                n=943, valor=12.6, ic_inf=None, ic_sup=None, detalle={"DE": 5.6})
    base.update(cambios)
    return base


def test_lote_valido_pasa():
    publicar.verificar([_fila_valida()])


def test_rechaza_grupo_por_debajo_del_minimo():
    fila = _fila_valida(n=cat.MIN_GROUP_N - 1, agrupacion="Colegio", grupo="CdP")
    with pytest.raises(publicar.PublicacionInsegura) as e:
        publicar.verificar([fila])
    assert "n = 9" in str(e.value)


def test_rechaza_identificador_de_estudiante_como_grupo():
    with pytest.raises(publicar.PublicacionInsegura) as e:
        publicar.verificar([_fila_valida(agrupacion="ID", grupo="E1a2b3c4d")])
    assert "identificador de estudiante" in str(e.value)


@pytest.mark.parametrize("prohibida", ["nombre", "id", "ts", "sede"])
def test_rechaza_columnas_de_identificacion_en_el_detalle(prohibida):
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila_valida(detalle={prohibida: "algo"})])


def test_falla_el_lote_entero_no_solo_la_fila_mala():
    """Publicar «lo que se pueda» esconde el error que hay que arreglar."""
    lote = [_fila_valida() for _ in range(5)] + [_fila_valida(n=3)]
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar(lote)


def test_version_depende_de_la_estructura_no_de_los_datos():
    class Falso:
        n = 100
        escalas = ["SDQ_Total", "ARI_Total"]
    v1 = publicar.version_analisis({"secundaria": Falso()})
    v2 = publicar.version_analisis({"secundaria": Falso()})
    assert v1 == v2 and len(v1.split("-")) == 4      # fecha ISO + huella

    class Otro(Falso):
        n = 101
    assert publicar.version_analisis({"secundaria": Otro()}) != v1


def test_mensajes_para_subir_respetan_los_roles_del_catalogo():
    ms = publicar.mensajes_para_subir()
    claves_roles = {(m["clave"], m["accion_rol"]) for m in ms}
    assert ("ideacion", "familia") not in claves_roles
    assert ("ideacion", "colegio") in claves_roles
    for m in ms:
        assert m["accion"].strip(), f"{m['clave']}/{m['accion_rol']} sin acción"
        assert m["significa"] == cat.MENSAJES[m["clave"]].significa


# ══ Con los datos reales, si están ══════════════════════════════════════════
@pytest.fixture(scope="module")
def lote_real():
    rutas = pipeline.localizar_formularios(RAIZ)
    if len(rutas) < 2:
        pytest.skip("Los formularios originales no están en el directorio de trabajo")
    analisis, _ = pipeline.cargar_y_analizar(rutas, n_boot=20)
    return analisis, publicar.aplanar(analisis)


def test_el_lote_real_pasa_las_guardas(lote_real):
    _, filas = lote_real
    publicar.verificar(filas)
    assert len(filas) > 200
    assert min(f["n"] for f in filas) >= cat.MIN_GROUP_N


def test_el_lote_real_no_trae_ni_un_nombre_ni_un_identificador(lote_real):
    import re
    import pandas as pd
    analisis, filas = lote_real
    texto = json.dumps(filas, ensure_ascii=False, default=str)
    assert not re.findall(r"\bE[0-9a-f]{8}\b", texto)
    # ningún identificador derivado del nombre sobrevive
    ids = set()
    for a in analisis.values():
        if a is not None and "ID" in a.datos.columns:
            ids.update(a.datos["ID"].astype(str).head(200))
    assert not [i for i in ids if i in texto]
    # y los nombres crudos tampoco
    ruta = pipeline.localizar_formularios(RAIZ)[0]
    nombres = pd.read_csv(ruta)["Mi nombre completo es:"].dropna().astype(str).head(200)
    bajo = texto.lower()
    assert not [n for n in nombres if n.strip() and n.strip().lower() in bajo]


def test_el_lote_real_solo_tiene_tipos_y_agrupaciones_previstas(lote_real):
    _, filas = lote_real
    tipos = {f["tipo"] for f in filas}
    assert tipos <= {"descriptivo", "banda", "corte", "correlacion", "grupo",
                     "modelo", "tercil", "percentil", "icc", "contraste", "item",
                     "muestra", "solapamiento", "ingesta"}
    for f in filas:
        assert f["nivel"] in ("secundaria", "primaria")
        assert isinstance(f["detalle"], dict)


def test_ninguna_fila_viene_de_datos_individuales(lote_real):
    """El aplanado solo debe leer tablas agregadas, nunca `Analisis.datos`."""
    analisis, filas = lote_real
    n_estudiantes = sum(a.n for a in analisis.values() if a is not None)
    # una fila por estudiante sería la señal de fuga; hay muchas menos filas
    assert len(filas) < n_estudiantes
    # y toda fila declara un N de grupo, no de individuo
    assert all(f["n"] >= cat.MIN_GROUP_N for f in filas)


def test_las_banderas_se_publican_como_booleanos():
    """`bool` hereda de `int`: convertirlas a 1.0 rompe al leerlas.

    Con una bandera numérica, filtrar un DataFrame por esa columna se
    interpreta como selección de columnas y la vista revienta.
    """
    fila = publicar._fila("secundaria", "correlacion", "SDQ_Total", 943, 0.5,
                          significativa=True, validada=False, p=0.001, casos=12)
    assert fila["detalle"]["significativa"] is True
    assert fila["detalle"]["validada"] is False
    assert isinstance(fila["detalle"]["p"], float)
    assert isinstance(fila["detalle"]["casos"], float)


def test_el_lote_real_no_trae_banderas_numericas(lote_real):
    _, filas = lote_real
    for f in filas:
        for clave in ("significativa", "significativo", "validada", "orientado"):
            if clave in f["detalle"]:
                assert isinstance(f["detalle"][clave], bool), \
                    f"{f['tipo']}/{f['clave']}: {clave} no es booleano"
