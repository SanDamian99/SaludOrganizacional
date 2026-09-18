"""
Pruebas de la vista investigador (P6) — Observatorio 360.

Todo se prueba sin arrancar Streamlit: solo las funciones puras del módulo
(`tabla1`, `metodologia_md`, `flujo_exclusiones_md`, `paquete_zip`) sobre un
`Analisis` construido con `pipeline.analizar` a partir del formulario sintético
de `tests/test_estudiantes.py`.
"""
import io
import re
import zipfile

import pandas as pd
import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, scoring
from src.ui.views import estudiantes_investigador as vista

from tests.test_estudiantes import _formulario_sintetico

# Columnas que nunca pueden salir en un exportable: identifican a una persona
COLUMNAS_PROHIBIDAS = {"id", "nombre", "nombre_completo", "sede", "ts",
                       "marca temporal", "colegio_nombre"}


@pytest.fixture(scope="module")
def corrida():
    """({nivel: Analisis}, [InformeIngesta]) de secundaria y primaria sintéticas."""
    df_sec = _formulario_sintetico(n=90)
    # dos colegios con N suficiente y uno enmascarado, para probar el filtrado
    colegios = (["I.E.O Laura Vicuña"] * 45 + ["I.E.O La Balsa"] * 40
                + ["I.E.O Cerca de Piedra"] * 5)
    df_sec["Mi colegio es:"] = colegios
    df_sec["Estoy en grado"] = ["Séptimo" if i % 2 else "Noveno" for i in range(len(df_sec))]

    df_pri = _formulario_sintetico(n=60)
    df_pri = df_pri.drop(columns=[c for c in df_pri.columns if c.startswith("RCADS")])
    df_pri["Estoy en grado"] = ["Cuarto" if i % 2 else "Quinto" for i in range(len(df_pri))]
    df_pri["Tengo:"] = [f"{9 + i % 3} años" for i in range(len(df_pri))]
    df_pri["Mi colegio es:"] = (["I.E.O Laura Vicuña"] * 30 + ["I.E.O La Balsa"] * 30)
    df_pri["Mi nombre completo es:"] = [f"Menor Apellido {i}" for i in range(len(df_pri))]

    filas, informes = [], []
    for df in (df_sec, df_pri):
        d, inf = ingest.cargar(df)
        filas.append(d)
        informes.append(inf)
    bruto = pd.concat(filas, ignore_index=True)
    puntuado = scoring.puntuar(bruto)
    analisis = {inf.nivel: pipeline.analizar(puntuado, inf.nivel, n_boot=20,
                                             avisos=list(inf.avisos))
                for inf in informes}
    return analisis, informes


# ══ (a) Tabla 1 ═════════════════════════════════════════════════════════════
def test_tabla1_una_fila_por_escala_del_catalogo_presente(corrida):
    analisis, _ = corrida
    t = vista.tabla1(analisis)
    assert not t.empty
    for nivel, a in analisis.items():
        presentes = scoring.puntuaciones_disponibles(a.datos)
        claves = t.loc[t["nivel"] == nivel, "clave"].tolist()
        assert claves == [k for k in cat.ORDEN_TABLA1 if k in presentes]
        assert len(claves) == len(set(claves))


def test_tabla1_columnas_esperadas_y_contenido(corrida):
    analisis, _ = corrida
    t = vista.tabla1(analisis)
    assert list(t.columns) == vista.COLUMNAS_TABLA1
    assert (t["n"] > 0).all()
    # el corte del SDQ llega con su fuente desde el catálogo
    sdq = t[t["clave"] == "SDQ_Total"].iloc[0]
    assert "sdqinfo.org" in sdq["fuente_corte"]
    assert sdq["pct_sobre_corte"].endswith("%")
    # la toma de decisiones queda rotulada como no validada
    td = t[t["clave"] == "TD_Total"]
    assert not td.empty and not bool(td.iloc[0]["validada"])


def test_tabla1_acepta_un_unico_analisis(corrida):
    analisis, _ = corrida
    a = analisis[cat.NIVEL_SECUNDARIA]
    t = vista.tabla1(a)
    assert list(t.columns) == vista.COLUMNAS_TABLA1
    assert set(t["nivel"]) == {cat.NIVEL_SECUNDARIA}


def test_tabla1_sin_datos_devuelve_tabla_vacia_con_columnas():
    t = vista.tabla1({})
    assert t.empty and list(t.columns) == vista.COLUMNAS_TABLA1


# ══ (b) Paquete ZIP ═════════════════════════════════════════════════════════
def test_paquete_zip_devuelve_bytes_con_los_ocho_archivos(corrida):
    analisis, informes = corrida
    blob = vista.paquete_zip(analisis, informes)
    assert isinstance(blob, bytes) and len(blob) > 0
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        nombres = z.namelist()
        assert len(vista.ARCHIVOS_PAQUETE) == 8
        assert sorted(nombres) == sorted(vista.ARCHIVOS_PAQUETE)
        for nombre in nombres:
            assert z.read(nombre).decode("utf-8").strip(), f"{nombre} salió vacío"


def test_paquete_zip_funciona_sin_informes(corrida):
    analisis, _ = corrida
    blob = vista.paquete_zip(analisis)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert sorted(z.namelist()) == sorted(vista.ARCHIVOS_PAQUETE)
        flujo = z.read("flujo_exclusiones.md").decode("utf-8")
    assert "no se puede reconstruir" in flujo


# ══ (c) Metodología y flujo ═════════════════════════════════════════════════
def test_metodologia_menciona_las_fuentes_de_los_cortes(corrida):
    analisis, informes = corrida
    md = vista.metodologia_md(analisis, informes)
    assert cat.FUENTE_BANDS_SELF in md
    assert cat.ARI.fuente in md
    assert cat.RCADS.fuente in md
    assert cat.PSSM.fuente in md
    for e in cat.ESCALAS:
        assert e.nombre in md, e.key
    assert "percentiles propios" in md.lower()
    assert "terciles" in md.lower()


def test_metodologia_menciona_las_reglas_de_exclusion(corrida):
    analisis, informes = corrida
    md = vista.metodologia_md(analisis, informes)
    for regla in ("Consentimiento", "Filas de prueba",
                  "Colegios con una sola respuesta", "Duplicados",
                  "Invalidación del bloque ERQ-CA", "fuera del rango"):
        assert regla in md, regla
    assert "Reglas de exclusión" in md
    assert cat.AVISO_NORMAS in md and cat.AVISO_TAMIZAJE in md


def test_flujo_de_exclusiones_cuadra_con_el_informe(corrida):
    _, informes = corrida
    md = vista.flujo_exclusiones_md(informes)
    for inf in informes:
        assert str(inf.filas_archivo) in md
        assert str(inf.filas_validas) in md
    assert "Respuestas válidas analizadas" in md
    assert md.startswith("# Flujo de la muestra")


def test_version_analisis_trae_fecha_n_y_hash(corrida):
    analisis, informes = corrida
    txt = vista.version_analisis_txt(analisis, informes)
    import datetime
    assert datetime.date.today().isoformat() in txt
    for nivel, a in analisis.items():
        assert f"[{nivel}]" in txt
        assert str(a.n) in txt
        assert vista._hash_estructura(a) in txt
    # el hash depende de la estructura, no de los datos
    a = analisis[cat.NIVEL_SECUNDARIA]
    h1 = vista._hash_estructura(a)
    otro = type(a)(nivel=a.nivel, n=a.n, datos=a.datos.copy())
    otro.datos.iloc[0, 0] = otro.datos.iloc[1, 0]
    assert vista._hash_estructura(otro) == h1
    assert vista._hash_estructura(
        type(a)(nivel=a.nivel, n=a.n, datos=a.datos.iloc[:, :3])) != h1


# ══ (d) Ningún dato individual en los exportables ═══════════════════════════
def test_ningun_exportable_trae_columnas_de_identificacion(corrida):
    analisis, informes = corrida
    archivos = vista.archivos_paquete(analisis, informes)
    for nombre, contenido in archivos.items():
        if not nombre.endswith(".csv") or not contenido:
            continue
        df = pd.read_csv(io.StringIO(contenido))
        for col in df.columns:
            assert col.strip().lower() not in COLUMNAS_PROHIBIDAS, f"{nombre}: {col}"


def test_ningun_exportable_trae_filas_individuales(corrida):
    """Cada fila exportada describe una escala, un par o un grupo, nunca una persona."""
    analisis, informes = corrida
    claves_agregadas = {"clave", "escala", "a", "b", "indicador", "predictor", "grupo",
                        "seccion", "y", "comparacion"}
    for nombre, contenido in vista.archivos_paquete(analisis, informes).items():
        if not nombre.endswith(".csv") or not contenido:
            continue
        df = pd.read_csv(io.StringIO(contenido))
        assert "ID" not in df.columns
        # la fila se identifica por una clave agregada, no por un respondiente
        assert claves_agregadas & set(df.columns), f"{nombre} no tiene clave agregada"
        # toda base N de un grupo cubre al menos el mínimo (las casillas de banda,
        # n_b0..n_b3, son reparto interno de una base que ya cumple el mínimo)
        for col in df.columns:
            if col == "n" or re.fullmatch(r"n[·_](?!b\d)\w+", str(col)):
                valores = pd.to_numeric(df[col], errors="coerce").dropna()
                assert (valores >= cat.MIN_GROUP_N).all(), f"{nombre}: {col}"


def test_ningun_exportable_contiene_identificadores_ni_nombres(corrida):
    analisis, informes = corrida
    ids = set()
    for a in analisis.values():
        if "ID" in a.datos.columns:
            ids.update(a.datos["ID"].astype(str).tolist())
    assert ids, "la fixture debería traer identificadores que no deben filtrarse"
    for nombre, contenido in vista.archivos_paquete(analisis, informes).items():
        for un_id in list(ids)[:25]:
            assert un_id not in contenido, f"{nombre} filtró un identificador"
        assert "Estudiante Apellido" not in contenido
        assert "Menor Apellido" not in contenido


def test_grupos_menores_al_minimo_no_reaparecen_en_los_exportables(corrida):
    analisis, informes = corrida
    comparaciones = vista.comparaciones_grupo(analisis)
    for col in comparaciones.columns:
        if str(col).startswith("n·"):
            valores = comparaciones[col].dropna()
            assert (valores >= cat.MIN_GROUP_N).all(), col
    for col in ("n_mujer", "n_hombre", "n"):
        if col in comparaciones.columns:
            valores = comparaciones[col].dropna()
            assert (valores >= cat.MIN_GROUP_N).all(), col


# ══ Tablas auxiliares que alimentan las pestañas ════════════════════════════
def test_bandas_y_cortes_cubre_las_cuatro_secciones(corrida):
    analisis, _ = corrida
    t = vista.bandas_y_cortes(analisis)
    assert not t.empty
    secciones = set(t["seccion"])
    assert "Bandas del SDQ (autoinforme)" in secciones
    assert "Prevalencia sobre corte (IC de Wilson)" in secciones
    assert "Terciles de la muestra" in secciones
    # ninguna celda queda como lista: el CSV tiene que poder escribirse
    assert not t.map(lambda v: isinstance(v, (list, tuple, set))).any().any()


def test_modelos_y_correlaciones_conservan_las_columnas_clave(corrida):
    analisis, _ = corrida
    corr = vista.correlaciones_bh(analisis)
    assert {"nivel", "rho", "ic_inf", "ic_sup", "p", "q_bh", "n"} <= set(corr.columns)
    modelos = vista.modelos_tabla(analisis)
    if not modelos.empty:
        assert {"nivel", "y", "n", "conglomerados", "R2", "predictor", "beta", "se", "p",
                "significativo"} <= set(modelos.columns)
    icc = vista.icc_tabla(analisis)
    assert {"nivel", "clave", "escala", "CCI"} <= set(icc.columns)


def test_render_con_analisis_vacio_no_lanza(monkeypatch):
    """El contrato dice: si no hay datos, un st.info y nunca una excepción."""
    mensajes = []
    monkeypatch.setattr(vista.st, "title", lambda *a, **k: None)
    monkeypatch.setattr(vista.st, "info", lambda msg, *a, **k: mensajes.append(msg))
    vista.render_investigador({})
    assert len(mensajes) == 1 and "cargar" in mensajes[0].lower()
