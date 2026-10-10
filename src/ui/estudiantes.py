"""
Página «Estudiantes 360» — despachador de audiencia.

Un selector arriba decide qué vista se arma. Las dos vistas consumen el mismo
objeto `Analisis`, así que no pueden divergir: lo que ve un rector y lo que
exporta el equipo investigador salen del mismo cálculo.

La carga y el análisis se cachean con `st.cache_resource` porque el resultado no
es un DataFrame serializable sino un grafo de objetos; la clave incluye la ruta y
la fecha de modificación de cada archivo, así que basta con volver a guardar un
formulario para que se recalcule.

Vista previa del equipo (`src.core.vista_previa`): en el despliegue privado, sin
formularios en disco, un interruptor de la barra lateral muestra la última
corrida OCULTA en lugar de la publicada, con una franja que lo advierte. En el
modo comunidad ese módulo ni se importa.
"""
from __future__ import annotations

import logging
import os

import streamlit as st

from src.core import modo as modo_app
from src.estudiantes import catalog as cat
from src.estudiantes import lectura, pipeline

logger = logging.getLogger(__name__)

AUDIENCIAS = {
    "comunidad": "Colegios, familias y municipio",
    "investigador": "Equipo investigador",
}


def _raiz_proyecto() -> str:
    """Carpeta donde se buscan los formularios: la de datos fuente, no el repositorio."""
    from src.core.rutas import carpeta_datos
    return carpeta_datos("estudiantes")


@st.cache_resource(show_spinner="Puntuando y analizando las respuestas…")
def _analizar(firma: tuple) -> tuple:
    """`firma` es (ruta, mtime) por archivo: cambia si cambia algún formulario."""
    rutas = [f[0] for f in firma]
    return pipeline.cargar_y_analizar(rutas)


@st.cache_data(ttl=300, show_spinner=False)
def _corrida_vigente() -> int | None:
    """Id de la corrida publicada más reciente, refrescado cada cinco minutos.

    Es la clave de la caché de abajo. Con una clave fija, la aplicación
    desplegada seguía mostrando la corrida anterior después de aprobar una
    nueva, hasta que alguien reiniciara el proceso.
    """
    try:
        return lectura.id_corrida_vigente()
    except Exception:                                      # noqa: BLE001
        return None


@st.cache_resource(show_spinner="Leyendo los resultados publicados…")
def _leer_publicado(_clave: str) -> tuple:
    return lectura.cargar_desde_supabase()


# ── Vista previa del equipo ─────────────────────────────────────────────────
def _vista_previa():
    """Módulo `vista_previa`, o None.

    Nunca en el modo comunidad: ahí no se importa. Y como Streamlit puede
    conservar módulos viejos tras un despliegue, se importa dentro de un `try` y
    se comprueba que traiga lo que se usa: un módulo rancio no tumba la página.
    """
    if modo_app.modo() == modo_app.COMUNIDAD:
        return None
    try:
        from src.core import vista_previa as vp
    except Exception as exc:                               # noqa: BLE001
        logger.warning("Vista previa [estudiantes: import vista_previa]: %s.",
                       type(exc).__name__)
        return None
    necesarias = ("interruptor", "banner", "cliente_autenticado", "marcar_en_uso")
    faltan = [n for n in necesarias if not callable(getattr(vp, n, None))]
    if faltan:
        logger.warning("Vista previa [estudiantes]: módulo vista_previa rancio, sin %s.",
                       ", ".join(faltan))
        return None
    return vp


def _fuente_supabase(base: str) -> bool:
    """True si la página va a leer de Supabase (no hay formularios o se fuerza)."""
    if os.environ.get("OBS360_FUENTE", "").strip().lower() == "supabase":
        return True
    return not pipeline.localizar_formularios(base)


def _revision_activa(base: str) -> dict | None:
    """Interruptor de la vista previa; la corrida en revisión si está encendido."""
    vp = _vista_previa()
    if vp is None:
        return None
    paso = "lectura.disponible"
    try:
        if not lectura.disponible():
            return None
        paso = "_fuente_supabase"
        if not _fuente_supabase(base):
            return None
        paso = "vp.interruptor"
        return vp.interruptor(lectura.MODULO)
    except Exception as exc:                               # noqa: BLE001
        logger.warning("Vista previa [estudiantes: _revision_activa: %s]: %s. "
                       "Se sigue con lo publicado.", paso, type(exc).__name__)
        return None


@st.cache_resource(show_spinner="Leyendo la corrida en revisión…")
def _leer_revision(_clave: str, corrida_id: int) -> tuple:
    """La corrida oculta `corrida_id`, con el usuario de carga.

    `_clave` es (módulo, corrida, vista previa): nunca coincide con la de la
    corrida publicada. Si no hay sesión, lanza y no se guarda en caché.
    """
    vp = _vista_previa()
    cli = vp.cliente_autenticado() if vp is not None else None
    if cli is None:
        raise RuntimeError("Sin sesión del usuario de carga.")
    return lectura.cargar_desde_supabase(cli, corrida_id=corrida_id)


def cargar_analisis(base: str | None = None, revision: int | None = None):
    """(analisis, informes, origen).

    Dos fuentes, en este orden:
      1. **Los formularios en disco.** Es lo que se usa en la máquina de quien
         procesa: puntúa desde los ítems y permite filtrar por colegio y grado.
      2. **La corrida publicada en Supabase.** Es lo que usa la aplicación
         desplegada. Solo trae agregados, así que no hay filtros por grupo, y
         eso es deliberado: un despliegue no debería poder recalcular nada sobre
         individuos.

    `origen` es "archivos", "supabase" o None si no hay ninguna de las dos; y
    "revision" si se pidió la corrida oculta `revision` (vista previa del
    equipo) y se pudo leer. Si no se puede, se sigue con la publicada.
    """
    base = base or _raiz_proyecto()
    # `OBS360_FUENTE=supabase` fuerza la segunda fuente aunque los archivos estén
    # en disco. Sirve para ver exactamente lo que mostrará el despliegue.
    forzada = os.environ.get("OBS360_FUENTE", "").strip().lower()
    rutas = [] if forzada == "supabase" else pipeline.localizar_formularios(base)
    if rutas:
        firma = tuple((r, os.path.getmtime(r)) for r in rutas)
        analisis, informes = _analizar(firma)
        return analisis, informes, "archivos"

    if revision is not None:
        try:
            analisis, informes, _ = _leer_revision(
                f"{lectura.MODULO}-corrida-{revision}-vista-previa", revision)
        except Exception as exc:                           # noqa: BLE001
            logger.warning("Vista previa [estudiantes: _leer_revision(%s)]: %s. "
                           "Se muestra la publicada.", revision, type(exc).__name__)
            analisis = None
        if analisis:
            return analisis, informes, "revision"

    if lectura.disponible():
        analisis, informes, corrida = _leer_publicado(f"corrida-{_corrida_vigente()}")
        if analisis:
            return analisis, informes, "supabase"
    return None, None, None


def _sin_datos(base: str) -> None:
    st.title("🎒 Estudiantes 360")
    if lectura.disponible():
        st.warning(
            "Hay conexión con la base de datos, pero **ninguna corrida está "
            "aprobada** todavía, así que no hay resultados que mostrar.\n\n"
            "Quien administre el proyecto debe marcar la corrida como publicada.",
            icon="⏳")
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
        if a is None:
            continue
        datos = getattr(a, "datos", None)
        if getattr(a, "base", None) is not None or \
                (getattr(a, "subgrupos", None) or {}).get("Colegio"):
            # Los mismos colegios que ofrece el selector: los de la base
            # publicable (datos crudos) o los subgrupos publicados.
            from src.ui.views.estudiantes_comunidad import grupos_publicables
            cuenta = {c: cat.MIN_GROUP_N for c in grupos_publicables(a, "Colegio")}
        elif datos is not None and "Colegio" in datos.columns and not datos.empty:
            cuenta = datos["Colegio"].value_counts().to_dict()
        else:
            # La corrida publicada no trae filas: los conteos vienen en `muestra`,
            # con los grupos pequeños enmascarados como «<10».
            cuenta = (getattr(a, "muestra", None) or {}).get("colegio") or {}
        for codigo, n in cuenta.items():
            try:
                suficiente = float(n) >= cat.MIN_GROUP_N
            except (TypeError, ValueError):
                suficiente = False
            if str(codigo).lower() == pedido.lower() and suficiente:
                return str(codigo)
    return None


def render_estudiantes() -> None:
    base = _raiz_proyecto()
    revision = _revision_activa(base)
    try:
        analisis, informes, origen = cargar_analisis(
            base, revision=revision["en_revision"] if revision else None)
    except Exception as exc:                                   # noqa: BLE001
        st.title("🎒 Estudiantes 360")
        texto = str(exc)
        if "Invalid API key" in texto or "'code': 401" in texto or "JWT" in texto:
            # El fallo más probable en un despliegue: la clave de Supabase que
            # se pegó en los secretos no es la del proyecto, o está caducada.
            st.error("La clave de Supabase de este despliegue no es válida, así que "
                     "no se pueden leer los resultados publicados.", icon="🔑")
            st.markdown(
                "Quien administre la aplicación debe revisar, en "
                "*Settings → Secrets*, que `SUPABASE_URL` y `SUPABASE_KEY` sean los "
                "del proyecto. `SUPABASE_KEY` es la clave **anon**, que se copia de "
                "*Supabase → Settings → API*. La clave `service_role` no se pone "
                "aquí: sirve para escribir y no debe salir del equipo que publica.")
        else:
            st.error(f"No se pudieron procesar los formularios: {texto}")
            st.caption("Revisa que las columnas de identificación y los bloques de "
                       "ítems estén completos. El detalle queda en los registros "
                       "de la aplicación.")
        return

    vp = _vista_previa()
    if vp is not None:
        vp.marcar_en_uso(lectura.MODULO, origen == "revision")
        if origen == "revision":
            vp.banner(revision)

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
            # El modo decide con cuál abre; después manda lo que elija la persona.
            # Misma precaución que en main.py: un módulo rancio tras un
            # despliegue no debe impedir que se vea la página.
            _defecto = getattr(modo_app, "audiencia_por_defecto", None)
            inicial = _defecto() if callable(_defecto) else permitidas[0]
            indice = permitidas.index(inicial) if inicial in permitidas else 0
            clave = st.radio("Vista", permitidas, index=indice,
                             format_func=lambda k: AUDIENCIAS[k],
                             key="estudiantes_audiencia")
        else:
            clave = permitidas[0]
        total = sum(a.n for a in analisis.values())
        st.caption(f"{total:,}".replace(",", " ") + " respuestas válidas")
        if origen == "supabase":
            st.caption("Fuente: corrida publicada")
        elif origen == "revision":
            st.caption(f"Fuente: corrida en revisión ({revision['en_revision']}), "
                       "no publicada")

    if origen == "supabase":
        st.info(lectura.AVISO_SIN_DATOS_CRUDOS, icon="🗄️")

    if clave == "comunidad":
        # Enlace por colegio: ?colegio=LauV deja su colegio preseleccionado la
        # primera vez, en Estudiantes y en Cuidadores. Después manda lo que la
        # persona elija.
        from src.ui import estado
        estado.aplicar_colegio_de_url(colegio_de_la_url(analisis))
        from src.ui.views.estudiantes_comunidad import render_comunidad
        render_comunidad(analisis, informes)
    else:
        from src.ui.views.estudiantes_investigador import render_investigador
        render_investigador(analisis, informes)
