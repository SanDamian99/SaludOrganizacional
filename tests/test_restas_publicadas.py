"""
Restas sobre lo que de verdad se publica — Estudiantes 360.

`privacidad.auditar` revisa las restas sobre los datos enmascarados. Este
archivo las revisa sobre la salida de `publicar.aplanar`, que es lo único que
ve el público: para cada indicador, el N del padre menos la suma de los N de
sus hijos publicados debe ser 0 o ≥ MIN_GROUP_N.

  · nivel   − Σ colegios
  · nivel   − Σ grados
  · colegio − Σ sus celdas colegio×grado
  · grado   − Σ sus celdas colegio×grado

Por construcción los hijos de un padre son disjuntos y están contenidos en él,
así que la diferencia de N es el tamaño del grupo que una resta aislaría. Solo
se compara cuando existen el padre y al menos un hijo para esa clave: un hijo
puede faltar legítimamente (el indicador no llega al mínimo en ese grupo, o el
grupo no está en la base).
"""
from __future__ import annotations

import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import pipeline, privacidad, publicar

CRUCE = privacidad.AGRUPACION_CRUCE
TIPOS = ("corte", "banda", "item")


def _clave(f) -> tuple:
    """(tipo base, clave, indicador): el corte usa `indicador` para distinguir umbrales."""
    tipo = f["tipo"].removesuffix("_grupo")
    return (f["nivel"], tipo, f["clave"], (f["detalle"] or {}).get("indicador"))


def _problemas_por_indicador(filas: list[dict]) -> list[str]:
    padres_nivel: dict = {}
    hijos: dict = {}           # (clave, agrupacion) -> {grupo: n}
    for f in filas:
        tipo = f["tipo"]
        if tipo in TIPOS and f["agrupacion"] == "total":
            padres_nivel[_clave(f)] = int(f["n"])
        elif tipo.removesuffix("_grupo") in TIPOS and tipo.endswith("_grupo"):
            hijos.setdefault((_clave(f), f["agrupacion"]), {})[str(f["grupo"])] = int(f["n"])
    return _comparar(padres_nivel, hijos)


def _problemas_por_grupo(filas: list[dict]) -> list[str]:
    """Filas `grupo` por Colegio y por Grado contra el N del descriptivo del nivel."""
    padres_nivel = {(f["nivel"], "descriptivo", f["clave"], None): int(f["n"])
                    for f in filas if f["tipo"] == "descriptivo"}
    hijos: dict = {}
    for f in filas:
        if f["tipo"] == "grupo" and f["agrupacion"] in ("Colegio", "Grado"):
            k = (f["nivel"], "descriptivo", f["clave"], None)
            hijos.setdefault((k, f["agrupacion"]), {})[str(f["grupo"])] = int(f["n"])
    return _comparar(padres_nivel, hijos)


def _resta_valida(padre: int, suma: int) -> bool:
    resto = padre - suma
    return resto == 0 or resto >= cat.MIN_GROUP_N


def _comparar(padres_nivel: dict, hijos: dict) -> list[str]:
    problemas: list[str] = []
    for clave, n_nivel in padres_nivel.items():
        for agrupacion in ("Colegio", "Grado"):
            propios = hijos.get((clave, agrupacion))
            if propios and not _resta_valida(n_nivel, sum(propios.values())):
                problemas.append(f"{clave}: nivel ({n_nivel}) − Σ {agrupacion} "
                                 f"({sum(propios.values())})")
        celdas = hijos.get((clave, CRUCE)) or {}
        for agrupacion, posicion in (("Colegio", 0), ("Grado", 1)):
            for grupo, n_grupo in (hijos.get((clave, agrupacion)) or {}).items():
                suyas = [n for c, n in celdas.items()
                         if privacidad.partir_celda(c)[posicion] == grupo]
                if suyas and not _resta_valida(n_grupo, sum(suyas)):
                    problemas.append(f"{clave}: {agrupacion} {grupo} ({n_grupo}) − "
                                     f"Σ sus celdas ({sum(suyas)})")
    return problemas


def _comprobar(analisis: dict) -> None:
    filas = publicar.aplanar(analisis)
    assert any(f["tipo"].endswith("_grupo") for f in filas), "no hay subgrupos que comparar"
    problemas = _problemas_por_indicador(filas) + _problemas_por_grupo(filas)
    assert problemas == [], "\n".join(problemas[:20])


# ══ Datos sintéticos ═══════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def analisis_sintetico():
    from src.estudiantes import ingest, scoring
    from tests.test_estudiantes_comunidad import _formulario
    bruto, _ = ingest.cargar(_formulario())
    return {cat.NIVEL_SECUNDARIA: pipeline.analizar(scoring.puntuar(bruto),
                                                    cat.NIVEL_SECUNDARIA, n_boot=20)}


def test_restas_publicadas_sinteticas(analisis_sintetico):
    _comprobar(analisis_sintetico)


def test_el_comprobador_detecta_una_resta_pequena():
    """Si el nivel trae 5 respuestas más que la suma de colegios, es un problema."""
    def fila(tipo, agrupacion, grupo, n):
        return dict(nivel="secundaria", tipo=tipo, clave="SDQ_Total",
                    agrupacion=agrupacion, grupo=grupo, n=n, detalle={})
    filas = [fila("banda", "total", None, 45),
             fila("banda_grupo", "Colegio", "A", 20), fila("banda_grupo", "Colegio", "B", 20),
             fila("banda_grupo", "Grado", "Sexto", 30),
             fila("banda_grupo", CRUCE, "A|Sexto", 20)]
    problemas = _problemas_por_indicador(filas)
    assert any("Σ Colegio" in p for p in problemas)          # 45 − 40 = 5
    assert not any("Σ Grado" in p for p in problemas)        # 45 − 30 = 15
    assert not any("Grado Sexto" in p for p in problemas)    # 30 − 20 = 10
    assert not any("Colegio A" in p for p in problemas)      # 20 − 20 = 0
    filas.append(fila("banda_grupo", CRUCE, "B|Quinto", 15))
    assert any("Colegio B" in p for p in _problemas_por_indicador(filas))  # 20 − 15 = 5



# ══ Datos reales, si están ═════════════════════════════════════════════════
@pytest.fixture(scope="module")
def analisis_real():
    from src.core.rutas import carpeta_datos
    rutas = pipeline.localizar_formularios(carpeta_datos("estudiantes"))
    if len(rutas) < 2:
        pytest.skip("Los formularios originales no están en el directorio de trabajo")
    analisis, _ = pipeline.cargar_y_analizar(rutas, n_boot=20)
    return analisis


def test_restas_publicadas_reales(analisis_real):
    _comprobar(analisis_real)
