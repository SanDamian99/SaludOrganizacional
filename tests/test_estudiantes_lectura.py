"""
Pruebas del lector de resultados publicados.

Lo que importa aquí es que la aplicación desplegada muestre exactamente las
mismas cifras que la corrida local, y que **no** pueda reconstruir nada sobre
individuos: `Analisis.datos` llega vacío a propósito.
"""
import os

import pandas as pd
import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import lectura, publicar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ══ Reconstrucción sin red, desde un lote construido con el publicador ══════
@pytest.fixture(scope="module")
def analisis_local():
    from src.estudiantes import pipeline
    rutas = pipeline.localizar_formularios(RAIZ)
    if len(rutas) < 2:
        pytest.skip("Los formularios originales no están en el directorio de trabajo")
    return pipeline.cargar_y_analizar(rutas, n_boot=20)


@pytest.fixture(scope="module")
def reconstruido(analisis_local):
    """Pasa el análisis por el publicador y lo vuelve a armar con el lector.

    Es el viaje completo sin tocar la red: si el lector y el publicador se
    desincronizan, esto falla.
    """
    analisis, informes = analisis_local
    filas = publicar.aplanar(analisis) + publicar.aplanar_ingesta(informes)
    por_nivel = {}
    for f in filas:
        por_nivel.setdefault(f["nivel"], []).append(f)
    salida = {n: lectura._reconstruir(n, fs) for n, fs in por_nivel.items()}
    leidos = [lectura.InformeLeido(f["nivel"], (f["detalle"] or {}).get("ingesta", {}))
              for f in filas if f["tipo"] == "ingesta"]
    return salida, leidos


TABLAS = ["descriptivos", "fiabilidad", "bandas", "cortes", "terciles",
          "percentiles", "correlaciones", "por_sexo", "por_grado", "por_colegio",
          "por_edad", "items_pssm"]


@pytest.mark.parametrize("tabla", TABLAS)
def test_cada_tabla_se_reconstruye_con_las_mismas_filas(analisis_local, reconstruido, tabla):
    local, _ = analisis_local
    remoto, _ = reconstruido
    for nivel in local:
        dl, dr = getattr(local[nivel], tabla), getattr(remoto[nivel], tabla)
        assert len(dl) == len(dr), f"{nivel}/{tabla}: {len(dl)} vs {len(dr)}"


def test_los_valores_coinciden(analisis_local, reconstruido):
    local, _ = analisis_local
    remoto, _ = reconstruido
    dl = local["secundaria"].descriptivos.set_index("clave")
    dr = remoto["secundaria"].descriptivos.set_index("clave")
    for clave in ("SDQ_Total", "RCADS_Dep", "MSPSS_Fam", "PSSM_Total", "ARI_Total"):
        assert dr.loc[clave, "M"] == pytest.approx(dl.loc[clave, "M"], abs=0.001)
        assert dr.loc[clave, "DE"] == pytest.approx(dl.loc[clave, "DE"], abs=0.001)
        assert dr.loc[clave, "n"] == dl.loc[clave, "n"]

    bl = local["secundaria"].bandas.set_index("clave")
    br = remoto["secundaria"].bandas.set_index("clave")
    for i in range(4):
        assert br.loc["SDQ_Total", f"pct_b{i}"] == pytest.approx(
            bl.loc["SDQ_Total", f"pct_b{i}"], abs=0.001)


def test_los_modelos_se_reconstruyen_con_sus_coeficientes(analisis_local, reconstruido):
    local, _ = analisis_local
    remoto, _ = reconstruido
    ml = {m["y"]: m for m in local["secundaria"].modelos}
    mr = {m["y"]: m for m in remoto["secundaria"].modelos}
    assert set(ml) == set(mr)
    for y in ml:
        assert mr[y]["n"] == ml[y]["n"]
        assert mr[y]["R2"] == pytest.approx(ml[y]["R2"], abs=0.001)
        bl = {c["predictor"]: c["beta"] for c in ml[y]["coeficientes"]
              if c["predictor"] != "(constante)"}
        br = {c["predictor"]: c["beta"] for c in mr[y]["coeficientes"]}
        assert set(bl) == set(br)
        for pred in bl:
            assert br[pred] == pytest.approx(bl[pred], abs=0.001)


def test_la_matriz_de_correlaciones_es_simetrica_y_con_diagonal_uno(reconstruido):
    remoto, _ = reconstruido
    m = remoto["secundaria"].matriz
    assert not m.empty
    assert all(m.loc[v, v] == 1.0 for v in m.index)
    for a in m.index[:5]:
        for b in m.columns[:5]:
            assert m.loc[a, b] == pytest.approx(m.loc[b, a], abs=1e-9)


def test_el_flujo_de_exclusiones_sobrevive(analisis_local, reconstruido):
    _, informes_l = analisis_local
    _, informes_r = reconstruido
    por_nivel_l = {i.nivel: i for i in informes_l}
    por_nivel_r = {i.nivel: i for i in informes_r}
    assert set(por_nivel_l) == set(por_nivel_r)
    for nivel, il in por_nivel_l.items():
        ir = por_nivel_r[nivel]
        for campo in ("filas_archivo", "sin_consentimiento", "excluidas_prueba",
                      "duplicados_eliminados", "filas_validas", "erq_invalidado"):
            assert getattr(ir, campo, None) == getattr(il, campo, None), campo


# ══ Lo que NO se reconstruye, y es lo importante ════════════════════════════
def test_no_hay_datos_individuales_en_lo_reconstruido(reconstruido):
    remoto, _ = reconstruido
    for a in remoto.values():
        assert a.datos is not None and a.datos.empty, \
            "lo publicado no debe permitir reconstruir filas por estudiante"


def test_sin_datos_crudos_solo_se_filtra_por_lo_publicado(reconstruido, analisis_local):
    """Sin fila por estudiante, un filtro solo puede devolver lo que viene calculado.

    Un colegio publicado da exactamente las cifras que recalcula la máquina que
    procesa; un cruce colegio × grado, que no se publica, no devuelve nada
    inventado.
    """
    from src.ui.views import estudiantes_comunidad as vc
    remoto, _ = reconstruido
    local, _ = analisis_local
    a = remoto["secundaria"]
    assert not vc.hay_datos_crudos(a)
    # las cifras del nivel completo sí están
    assert vc.bandas_sdq_total(a)
    assert len(vc.tarjetas(a, "colegio", {})) > 0
    # un colegio publicado: las mismas cifras que el recálculo local
    f = {"colegio": "LauV"}
    assert vc.bandas_sdq_total(a, f)["n"] == vc.bandas_sdq_total(local["secundaria"], f)["n"]
    assert vc.prevalencia(a, "sdq_alto", f) == vc.prevalencia(local["secundaria"], "sdq_alto", f)
    # un cruce no publicado no devuelve nada inventado
    cruce = {"colegio": "LauV", "grado": "8"}
    assert vc.bandas_sdq_total(a, cruce) == {}
    assert vc.prevalencia(a, "sdq_alto", cruce) == {}


def test_el_informe_filtrado_explica_la_causa_correcta(reconstruido):
    """No puede decir «grupo pequeño» de un colegio de cientos de estudiantes."""
    from src.ui.views import estudiantes_comunidad as vc
    remoto, _ = reconstruido
    informe = vc.informe_markdown(remoto["secundaria"], "colegio",
                                  {"colegio": "LauV", "grado": "8"})
    assert "corrida publicada" in informe
    # la explicación va antes del pie de «grupos que se muestran», donde sí es
    # correcto mencionar el mínimo; lo que no puede es atribuirle la causa
    explicacion = informe.split("## Grupos que se muestran")[0]
    assert f"menos de {cat.MIN_GROUP_N} estudiantes. Con grupos" not in explicacion
    assert "podría reconocer a un estudiante" not in explicacion


def test_los_conteos_enmascarados_se_leen_como_grupo_pequeno(reconstruido):
    """En lo publicado, una celda pequeña llega como «<10», no como número."""
    from src.ui.views import estudiantes_comunidad as vc
    remoto, _ = reconstruido
    visibles, pequenos = vc.grupos_visibles(remoto["secundaria"], "Colegio")
    colegios = (remoto["secundaria"].muestra or {}).get("colegio", {})
    assert any(isinstance(v, str) for v in colegios.values()), \
        "el enmascarado debería haber producido algún «<10»"
    for g in pequenos:
        assert isinstance(colegios.get(g), str) or colegios.get(g, 0) < cat.MIN_GROUP_N
    for g in visibles:
        assert float(colegios[g]) >= cat.MIN_GROUP_N


# ══ Las vistas funcionan con lo reconstruido ════════════════════════════════
def test_la_vista_investigador_produce_su_paquete(reconstruido):
    import io
    import zipfile
    from src.ui.views import estudiantes_investigador as vi
    remoto, informes = reconstruido
    tabla = vi.tabla1(remoto)
    assert not tabla.empty
    contenido = vi.paquete_zip(remoto, informes)
    nombres = zipfile.ZipFile(io.BytesIO(contenido)).namelist()
    assert set(nombres) == set(vi.ARCHIVOS_PAQUETE)
    metodologia = vi.metodologia_md(remoto, informes)
    assert "sdqinfo.org" in metodologia


def test_credenciales_y_disponibilidad(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    # sin secretos de Streamlit en un test plano, no debe reventar
    assert isinstance(lectura.disponible(), bool)
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "clave")
    assert lectura.disponible()
    assert lectura.credenciales() == ("https://ejemplo.supabase.co", "clave")


def test_el_lector_no_usa_la_clave_de_servicio():
    """La aplicación desplegada lee con la clave anónima, que no escribe."""
    fuente = open(os.path.join(RAIZ, "src", "estudiantes", "lectura.py"),
                  encoding="utf-8").read()
    assert "SUPABASE_SERVICE_KEY" not in fuente


def test_ninguna_vista_revienta_con_conteos_enmascarados(reconstruido):
    """Los conteos publicados pueden ser «<10»: nada debe hacer aritmética con ellos.

    Este fallo ya ocurrió una vez: la pestaña de muestra ordenaba los colegios
    con `-kv[1]` y se rompía con el conteo enmascarado.
    """
    from src.ui.views import estudiantes_investigador as vi
    remoto, informes = reconstruido
    m = remoto["secundaria"].muestra
    assert any(isinstance(v, str) for v in (m.get("colegio") or {}).values())
    # el orden tolera el texto y lo pone al final
    ordenado = sorted((m.get("colegio") or {}).items(), key=lambda kv: -vi._conteo(kv[1]))
    numericos = [k for k, v in ordenado if not isinstance(v, str)]
    enmascarados = [k for k, v in ordenado if isinstance(v, str)]
    assert ordenado[0][0] in numericos
    assert all(ordenado.index((k, m["colegio"][k])) >= len(numericos)
               for k in enmascarados)
    # y las funciones puras de las dos vistas corren de punta a punta
    assert not vi.tabla1(remoto).empty
    assert vi.paquete_zip(remoto, informes)


def test_toda_tabla_que_se_muestra_es_convertible_a_arrow(reconstruido):
    """`st.dataframe` serializa a Arrow: una columna con números y texto falla.

    Ocurrió en el despliegue: los conteos enmascarados como «<10» convivían con
    enteros en la columna `n` y cada recarga llenaba el registro de trazas.
    """
    import pyarrow as pa
    from src.ui.views import estudiantes_investigador as vi
    remoto, informes = reconstruido
    a = remoto["secundaria"]
    m = a.muestra

    tablas = {
        "sexo": vi._tabla_conteos(sorted((m.get("sexo") or {}).items()), "Sexo"),
        "edad": vi._tabla_conteos(
            sorted([(vi._edad_legible(k), v) for k, v in (m.get("edad") or {}).items()],
                   key=lambda kv: vi._conteo(kv[0])), "Edad"),
        "grado": vi._tabla_conteos(sorted((m.get("grado") or {}).items()), "Grado"),
        "colegio": vi._tabla_conteos(
            sorted((m.get("colegio") or {}).items(), key=lambda kv: -vi._conteo(kv[1])),
            "Colegio"),
        "tabla1": vi.tabla1(remoto),
        "bandas_y_cortes": vi.bandas_y_cortes(remoto),
        "correlaciones": vi.correlaciones_bh(remoto),
        "comparaciones": vi.comparaciones_grupo(remoto),
        "modelos": vi.modelos_tabla(remoto),
        "icc": vi.icc_tabla(remoto),
    }
    for nombre, t in tablas.items():
        if t is None or t.empty:
            continue
        pa.Table.from_pandas(t)          # lanza si alguna columna mezcla tipos


def test_la_edad_se_muestra_sin_decimales():
    from src.ui.views import estudiantes_investigador as vi
    assert vi._edad_legible("13.0") == "13"
    assert vi._edad_legible(13.0) == "13"
    assert vi._edad_legible(13) == "13"
    assert vi._edad_legible("sin dato") == "sin dato"
