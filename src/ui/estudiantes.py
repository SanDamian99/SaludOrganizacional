"""
Página «Estudiantes 360» — despachador de audiencia.

Un selector arriba decide qué vista se arma. Las dos vistas consumen el mismo
objeto `Analisis`, así que no pueden divergir: lo que ve un rector y lo que
exporta el equipo investigador salen del mismo cálculo.

La carga y el análisis se cachean con `st.cache_resource` porque el resultado no
es un DataFrame serializable sino un grafo de objetos; la clave incluye la ruta y
la fecha de modificación de cada archivo, así que basta con volver a guardar un
formulario para que se recalcule.
"""
from __future__ import annotations

import os

import streamlit as st

from src.core import modo as modo_app
from src.estudiantes import catalog as cat
from src.estudiantes import pipeline

AUDIENCIAS = {
    "comunidad": "Colegios, familias y municipio",
    "investigador": "Equipo investigador",
}


def _raiz_proyecto() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@st.cache_resource(show_spinner="Puntuando y analizando las respuestas…")
def _analizar(firma: tuple) -> tuple:
    """`firma` es (ruta, mtime) por archivo: cambia si cambia algún formulario."""
    rutas = [f[0] for f in firma]
    return pipeline.cargar_y_analizar(rutas)


def cargar_analisis(base: str | None = None):
    """(analisis, informes) o (None, None) si los formularios no están en disco."""
    base = base or _raiz_proyecto()
    rutas = pipeline.localizar_formularios(base)
    if not rutas:
        return None, None
    firma = tuple((r, os.path.getmtime(r)) for r in rutas)
    return _analizar(firma)


def _sin_datos(base: str) -> None:
    st.title("🎒 Estudiantes 360")
    st.info(
        "Todavía no encuentro los formularios de estudiantes.\n\n"
        "Se esperan dos exportaciones de Google Forms, en `.csv` o `.xlsx`, cuyo nombre "
        "contenga **«Cuéntanos sobre tu bienestar emocional»** (secundaria) y "
        "**«Cuéntanos sobre tus emociones»** (primaria), colocadas en la carpeta del "
        f"proyecto:\n\n`{base}`\n\n"
        "Se leen ítem por ítem, con el enunciado completo como encabezado. "
        "El nombre del estudiante se convierte en un identificador anónimo durante la "
        "carga y no se guarda en ningún momento.")
    with st.expander("Qué mide el instrumento"):
        for e in cat.ESCALAS:
            marca = "" if e.validada else "  ·  *escala exploratoria, fuente sin documentar*"
            st.markdown(f"- **{e.nombre}** — {e.n_items} ítems, "
                        f"edad {e.edad_validada[0]}–{e.edad_validada[1]}{marca}")


def colegio_de_la_url(analisis) -> str | None:
    """Colegio pedido en la URL (`?colegio=LauV`), si existe y es mostrable.

    Permite dar a cada colegio su propio enlace sin exponer los de los demás.
    Un código que no existe, o un colegio con menos de MIN_GROUP_N respuestas,
    se ignora: el enlace no sirve para sondear la base.
    """
    try:
        pedido = str(st.query_params.get("colegio", "")).strip()
    except Exception:                                      # noqa: BLE001
        return None
    if not pedido:
        return None
    for a in (analisis or {}).values():
        if a is None or "Colegio" not in a.datos.columns:
            continue
        cuenta = a.datos["Colegio"].value_counts()
        for codigo, n in cuenta.items():
            if str(codigo).lower() == pedido.lower() and n >= cat.MIN_GROUP_N:
                return str(codigo)
    return None


def render_estudiantes() -> None:
    base = _raiz_proyecto()
    try:
        analisis, informes = cargar_analisis(base)
    except Exception as exc:                                   # noqa: BLE001
        st.title("🎒 Estudiantes 360")
        st.error(f"No se pudieron procesar los formularios: {exc}")
        st.caption("Revisa que las columnas de identificación y los bloques de ítems "
                   "estén completos. El detalle queda en los registros de la aplicación.")
        return

    if not analisis:
        _sin_datos(base)
        return

    # El modo de despliegue decide qué vistas existen. En un despliegue público
    # solo hay una, así que no se muestra un selector que no elige nada.
    permitidas = modo_app.audiencias_permitidas() or list(AUDIENCIAS)
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Estudiantes 360**")
        if len(permitidas) > 1:
            clave = st.radio("Vista", permitidas, format_func=lambda k: AUDIENCIAS[k],
                             key="estudiantes_audiencia")
        else:
            clave = permitidas[0]
        total = sum(a.n for a in analisis.values())
        st.caption(f"{total:,}".replace(",", " ") + " respuestas válidas")

    if clave == "comunidad":
        # Enlace por colegio: ?colegio=LauV deja su colegio preseleccionado la
        # primera vez. Después manda lo que la persona elija en el selector.
        preseleccion = colegio_de_la_url(analisis)
        if preseleccion and "est_com_colegio" not in st.session_state:
            st.session_state["est_com_colegio"] = preseleccion
        from src.ui.views.estudiantes_comunidad import render_comunidad
        render_comunidad(analisis, informes)
    else:
        from src.ui.views.estudiantes_investigador import render_investigador
        render_investigador(analisis, informes)
