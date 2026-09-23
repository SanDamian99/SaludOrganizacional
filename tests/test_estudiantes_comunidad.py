"""
Pruebas de la vista comunidad de Estudiantes 360.

Todo se prueba sin arrancar Streamlit: la vista está partida en funciones puras
(selección de mensajes por rol, formateo de cifras, enmascarado por N y el
informe en Markdown) y solo `render_comunidad` toca la interfaz.
"""
import inspect

import numpy as np
import pandas as pd
import pytest

from src.core.rutas import carpeta_datos

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, scoring
from src.ui.views import estudiantes_comunidad as vc

# Colegio y grado con menos de MIN_GROUP_N casos: nunca deben aparecer.
COLEGIO_PEQUENO = "I.E.O Diosa Chía"
GRADO_PEQUENO = "Noveno"
NOMBRE_SENTINELA = "Estudiante Apellido"


def _formulario(n: int = 70) -> pd.DataFrame:
    """Formulario sintético de secundaria con un grupo grande y dos pequeños."""
    rng = np.random.default_rng(11)
    filas = []
    for i in range(n):
        if i < 4:
            colegio, grado = COLEGIO_PEQUENO, "Séptimo"
        elif i < 8:
            colegio, grado = "I.E.O Laura Vicuña", GRADO_PEQUENO
        else:
            colegio, grado = "I.E.O Laura Vicuña", ("Séptimo" if i % 2 else "Octavo")
        f = {"Marca temporal": f"{1 + i % 27}/07/2026 10:00:00",
             "¿Quieres aportar al bienestar de todos con tus respuestas?": "Sí, quiero aportar",
             "Mi nombre completo es:": f"{NOMBRE_SENTINELA} {i}",
             "Tengo:": f"{12 + i % 4} años",
             "Mi sexo es:": "Mujer" if i % 2 else "Hombre",
             "Estoy en grado": grado,
             "Mi colegio es:": colegio}
        for j in range(1, 26):
            f[f"SDQ [enunciado {j}]"] = rng.choice(
                ["No es cierto", "Algo cierto", "Muy cierto"])
        for j in range(1, 8):
            f[f"ARI [enunciado {j}]"] = rng.choice(
                ["No es cierto", "Algo cierto", "Muy cierto"])
        for j in range(1, 26):
            f[f"RCADS [enunciado {j}]"] = rng.choice(
                ["Nunca", "Algunas veces", "Con frecuencia", "Siempre"])
        for j in range(1, 11):
            f[f"ERQ-CA [enunciado {j}]"] = rng.choice(
                ["Nada parecido a mi", "Poco parecido a mi", "Se parece a mi",
                 "Bastante parecido a mi", "Exactamente igual a mi"])
        for j in range(1, 13):
            f[f"MSPSS [enunciado {j}]"] = rng.choice(
                ["Nunca", "Casi nunca", "Algunas veces", "Casi siempre", "Siempre"])
        f["Siento que soy parte de mi colegio"] = int(rng.integers(1, 6))
        for j in range(2, 19):
            f[f"PSSM enunciado {j}"] = int(rng.integers(1, 6))
        for j in range(1, 11):
            f[f"Toma de decisiones  [enunciado {j}]"] = rng.choice(
                ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"])
        filas.append(f)
    return pd.DataFrame(filas)


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)


# ══ Formateo de cifras ══════════════════════════════════════════════════════
@pytest.mark.parametrize("pct,esperado", [
    (20, "1 de cada 5"),
    (25, "1 de cada 4"),
    (50, "1 de cada 2"),
    (11.1, "1 de cada 9"),
    (40, "4 de cada 10"),
    (27, "3 de cada 10"),
    (4, "4 de cada 100"),
    (0, "—"),
    (None, "—"),
    (float("nan"), "—"),
    (100, "todos"),
])
def test_uno_de_cada(pct, esperado):
    assert vc.uno_de_cada(pct) == esperado


# ══ Elección de textos por rol ══════════════════════════════════════════════
def test_familia_nunca_ve_el_mensaje_de_ideacion():
    assert "ideacion" not in vc.mensajes_para_rol("familia")
    assert "ideacion" in vc.mensajes_para_rol("colegio")
    assert "ideacion" in vc.mensajes_para_rol("municipio")
    assert vc.accion_para_rol(cat.MENSAJES["ideacion"], "familia") == ""


def test_todos_los_roles_del_catalogo_tienen_mensajes():
    for rol in cat.ROLES:
        assert vc.mensajes_para_rol(rol), rol


@pytest.mark.parametrize("rol,atributo", [
    ("colegio", "accion_colegio"),
    ("familia", "accion_familia"),
    ("municipio", "accion_municipio"),
])
def test_accion_para_rol_devuelve_el_texto_del_catalogo(rol, atributo):
    mensaje = cat.MENSAJES["pertenencia"]
    assert vc.accion_para_rol(mensaje, rol) == getattr(mensaje, atributo)


def test_familia_no_ve_desagregacion_por_colegio():
    assert vc.ve_colegios("familia") is False
    assert vc.ve_colegios("colegio") is True
    assert vc.ve_colegios("municipio") is True


def test_enunciados_pssm_completos_y_en_espanol():
    assert len(vc.ENUNCIADOS_PSSM) == cat.PSSM.n_items
    assert vc.enunciado_pssm(f"PSSM{cat.PSSM_ITEM_ADULTO}").startswith("Hay al menos un profesor")
    assert vc.enunciado_pssm("PSSM99") == "PSSM99"


def test_los_enunciados_negativos_se_leen_en_positivo_cuando_la_media_esta_invertida():
    inversos = {f"PSSM{i}" for i in cat.PSSM_REVERSE_ITEMS}
    assert set(vc.ENUNCIADOS_PSSM_ORIENTADOS) == inversos
    for item in inversos:
        assert vc.enunciado_pssm(item, orientado=True) != vc.enunciado_pssm(item)
    # un ítem positivo no cambia
    assert vc.enunciado_pssm("PSSM1", orientado=True) == vc.enunciado_pssm("PSSM1")


def test_items_de_pertenencia_traen_enunciado_y_media(analisis):
    items = vc.items_pertenencia_bajos(analisis, 4)
    assert len(items) == 4
    assert [it["media"] for it in items] == sorted(it["media"] for it in items)
    for it in items:
        assert it["enunciado"] and not it["enunciado"].startswith("PSSM")
        assert 1 <= it["media"] <= 5
        assert it["n"] >= cat.MIN_GROUP_N


# ══ Tarjetas ════════════════════════════════════════════════════════════════
def test_tarjetas_respetan_el_techo_y_el_rol(analisis):
    for rol in cat.ROLES:
        fichas = vc.tarjetas(analisis, rol)
        assert fichas, rol
        assert len(fichas) <= vc.MAX_TARJETAS
        assert all(t.accion for t in fichas)
        assert all(t.significa for t in fichas)
    claves_familia = {t.clave for t in vc.tarjetas(analisis, "familia")}
    assert "ideacion" not in claves_familia


def test_los_textos_de_las_tarjetas_salen_del_catalogo(analisis):
    for t in vc.tarjetas(analisis, "colegio"):
        mensaje = cat.MENSAJES[t.clave]
        assert t.significa == mensaje.significa
        assert t.accion == mensaje.accion_colegio


# ══ Enmascarado por N ═══════════════════════════════════════════════════════
def test_grupos_pequenos_no_entran_en_los_selectores(analisis):
    visibles_c, pequenos_c = vc.grupos_visibles(analisis, "Colegio")
    visibles_g, pequenos_g = vc.grupos_visibles(analisis, "Grado")
    conteo_c = analisis.datos["Colegio"].value_counts().to_dict()
    conteo_g = analisis.datos["Grado"].value_counts().to_dict()
    assert all(conteo_c[g] >= cat.MIN_GROUP_N for g in visibles_c)
    assert all(conteo_g[g] >= cat.MIN_GROUP_N for g in visibles_g)
    assert GRADO_PEQUENO in pequenos_g and GRADO_PEQUENO not in visibles_g
    assert pequenos_c and all(conteo_c[g] < cat.MIN_GROUP_N for g in pequenos_c)


def test_la_comparacion_por_grupo_no_muestra_grupos_pequenos(analisis):
    for columna in ("Grado", "Colegio"):
        tabla = vc.prevalencia_por(analisis, "sdq_alto", columna)
        if tabla.empty:
            continue
        assert (tabla["n"] >= cat.MIN_GROUP_N).all()
        assert GRADO_PEQUENO not in set(tabla["grupo"]) or columna != "Grado"


def test_un_filtro_a_un_grupo_pequeno_no_devuelve_cifra(analisis):
    filtros = {"colegio": vc.TODOS, "grado": GRADO_PEQUENO}
    assert vc.prevalencia(analisis, "sdq_alto", filtros) == {}


# ══ Informe descargable ═════════════════════════════════════════════════════
def test_informe_no_filtra_nombres_ni_grupos_pequenos(analisis):
    for rol in cat.ROLES:
        md = vc.informe_markdown(analisis, rol)
        assert NOMBRE_SENTINELA not in md
        assert "Apellido" not in md
        assert GRADO_PEQUENO not in md
        # ni el código ni el nombre largo del colegio pequeño
        for etiqueta in (COLEGIO_PEQUENO, "Diosa", "DiosCh"):
            assert etiqueta not in md


def test_informe_trae_ruta_de_atencion_y_avisos(analisis):
    md = vc.informe_markdown(analisis, "colegio")
    for nombre, _ in cat.RUTA_ATENCION:
        assert nombre in md
    assert cat.AVISO_TAMIZAJE in md
    assert cat.AVISO_NORMAS in md
    assert cat.AVISO_PRIMARIA not in md


def test_informe_de_familia_sin_ideacion_ni_colegios(analisis):
    md = vc.informe_markdown(analisis, "familia")
    assert cat.MENSAJES["ideacion"].titulo not in md
    assert "Colegios comparados" not in md
    md_colegio = vc.informe_markdown(analisis, "colegio")
    assert "Colegios comparados" in md_colegio


def test_informe_sin_analisis_no_lanza():
    md = vc.informe_markdown(None, "colegio")
    assert "No hay datos" in md


def test_el_informe_no_etiqueta_resultados_con_lenguaje_clinico(analisis):
    """Las palabras vetadas solo pueden venir de textos ya revisados del catálogo."""
    md = vc.informe_markdown(analisis, "colegio")
    revisados = [m.significa for m in cat.MENSAJES.values()]
    revisados += [m.accion_colegio for m in cat.MENSAJES.values()]
    revisados += [m.titulo for m in cat.MENSAJES.values()]
    revisados += [cat.AVISO_TAMIZAJE, cat.AVISO_PRIMARIA, cat.AVISO_NORMAS]
    revisados += [d for _, d in cat.RUTA_ATENCION]
    propio = md
    for texto in revisados:
        propio = propio.replace(texto, " ")
    bajo = propio.lower()
    for palabra in ("depresión", "trastorno", "diagnóstico"):
        assert palabra not in bajo, palabra


def test_el_informe_no_contiene_filas_individuales(analisis):
    md = vc.informe_markdown(analisis, "municipio")
    # ninguna columna de ítem crudo se imprime
    for columna in ("SDQ1", "RCADS1", "PSSM1 ", "MSPSS1"):
        assert columna not in md
    assert len(md.splitlines()) < 120


# ══ Contrato de la vista ════════════════════════════════════════════════════
def test_render_comunidad_existe_con_la_firma_acordada():
    firma = inspect.signature(vc.render_comunidad)
    assert list(firma.parameters) == ["analisis", "informes"]
    assert firma.parameters["informes"].default is None


@pytest.mark.parametrize("entrada", [None, {}, {"secundaria": None}])
def test_render_sin_datos_no_lanza(entrada):
    """Sin datos (o sin el nivel pedido) se explica cómo cargarlos, no se revienta."""
    vc.render_comunidad(entrada)


def test_la_vista_no_dibuja_la_tabla_de_datos():
    fuente = inspect.getsource(vc)
    assert "st.dataframe" not in fuente
    assert "st.table" not in fuente
    assert "st.data_editor" not in fuente


# ══ Los enunciados del PSSM no pueden desviarse del formulario aplicado ═════
def test_enunciados_pssm_fieles_al_formulario():
    """Compara cada enunciado corto con el encabezado real del formulario.

    Se hizo necesario porque una paráfrasis cambió el sentido de dos ítems
    («Se toman mis opiniones en serio» no es lo mismo que «los demás estudiantes
    toman en serio mis opiniones»), y estos enunciados son justamente el
    resultado que los colegios usan para decidir qué hacer.
    """
    import os
    import pandas as pd
    from difflib import SequenceMatcher
    from src.estudiantes import pipeline
    from src.estudiantes.ingest import norm_txt
    from src.ui.views.estudiantes_comunidad import ENUNCIADOS_PSSM

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rutas = pipeline.localizar_formularios(carpeta_datos('estudiantes'))
    if not rutas:
        import pytest
        pytest.skip("Los formularios originales no están en el directorio de trabajo")
    cols = list(pd.read_csv(rutas[0], nrows=1).columns)
    inicio = next(i for i, c in enumerate(cols) if "siento que soy parte" in norm_txt(c))
    reales = {f"PSSM{k}": cols[inicio + k - 1] for k in range(1, 19)}

    for clave, corto in ENUNCIADOS_PSSM.items():
        real = norm_txt(reales[clave])
        breve = norm_txt(corto)
        # cada palabra del enunciado corto debe estar en el original: se permite
        # acortar, nunca añadir un sujeto o un matiz que el ítem no tenía
        añadidas = set(breve.split()) - set(real.split())
        assert not añadidas, f"{clave} añade palabras que no están en el ítem: {añadidas}"
        assert SequenceMatcher(None, real, breve).ratio() > 0.55, \
            f"{clave} se aleja demasiado del original: «{corto}» vs «{reales[clave]}»"


# ══ Con un filtro activo, las cifras deben ser las del grupo filtrado ══════
def test_bandas_e_items_respetan_el_filtro():
    """Un título que nombra un colegio no puede llevar las cifras de todo el nivel.

    Antes de este arreglo, `bandas_sdq_total` e `items_pertenencia_bajos`
    ignoraban los filtros: el informe de un colegio salía encabezado con su
    nombre y relleno con la distribución del municipio.
    """
    import os
    import pytest
    from src.estudiantes import pipeline
    from src.ui.views import estudiantes_comunidad as vc

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rutas = pipeline.localizar_formularios(carpeta_datos('estudiantes'))
    if len(rutas) < 2:
        pytest.skip("Los formularios originales no están en el directorio de trabajo")
    res, _ = pipeline.cargar_y_analizar(rutas, n_boot=20)
    a = res["secundaria"]

    total = vc.bandas_sdq_total(a)
    visibles, pequenos = vc.grupos_visibles(a, "Colegio")
    assert visibles, "hacen falta colegios visibles para la prueba"

    # un colegio concreto tiene su propio N y su propia distribución
    uno = vc.bandas_sdq_total(a, {"colegio": visibles[-1]})
    assert uno and uno["n"] < total["n"]
    assert uno["pct"] != total["pct"]
    items_uno = vc.items_pertenencia_bajos(a, 4, {"colegio": visibles[-1]})
    assert items_uno and all(i["n"] <= uno["n"] for i in items_uno)

    # un grupo por debajo del mínimo no devuelve nada, y el informe lo explica
    if pequenos:
        f = {"colegio": pequenos[0]}
        assert vc.bandas_sdq_total(a, f) == {}
        assert vc.items_pertenencia_bajos(a, 4, f) == []
        informe = vc.informe_markdown(a, "colegio", f)
        assert "%" not in informe.split("Si un estudiante")[0].split("menos de")[0]
        assert f"menos de {cat.MIN_GROUP_N} estudiantes" in informe
