"""
Vista previa para el equipo — Observatorio 360.

Una corrida se sube OCULTA (`publicada = false`) y el equipo la aprueba después.
Hasta ahora, para revisarla había que tener los datos en la máquina: el
despliegue privado leía, como el público, solo la última corrida publicada.

Este módulo deja que el despliegue PRIVADO (`OBS360_MODO = "investigador"`, o
`"completo"` en local) muestre la última corrida oculta de cada módulo
(estudiantes con sus alertas, la vista de comunidad de Cuidadores) antes de la
aprobación:

  · Lee con el usuario de carga (`OBS360_CARGA_EMAIL` / `OBS360_CARGA_CLAVE`,
    los mismos secretos del almacén de versiones, `src.data.almacen`). Supabase
    le deja leer cualquier corrida solo con la migración
    `supabase/migraciones/2026-10-10-vista-previa-cargador.sql`; sin ella, no
    ve ninguna oculta y la vista previa simplemente no aparece.
  · Un interruptor en la barra lateral, «Vista previa: corrida en revisión (N)»,
    encendido por defecto en el modo investigador; mientras está encendido, una
    franja arriba de la página dice que esa corrida no es pública.
  · Lo público no cambia: la clave anon sigue viendo solo la última corrida
    publicada de cada módulo (`obs360_interno.es_ultima_publicada`).

En el modo «comunidad» este módulo no se importa nunca (`tests/test_navegacion`
lo comprueba) y, aun si se importara, `disponible()` devuelve False.

Nunca registra ni muestra secretos: los fallos se anotan (`registrar_fallo`)
con el paso y el tipo de la excepción, nunca con el mensaje, que puede traer el
correo.

Es un módulo nuevo a propósito: tras un despliegue, Streamlit puede conservar
módulos viejos en memoria; quien lo usa lo importa dentro de un `try` y consulta
cada función con `getattr`, así que un módulo rancio nunca tumba una página.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

ESQUEMA = "obs360"
MODULOS = ("estudiantes", "cuidadores", "triangulacion")   # triangulación: solo el equipo
CLAVE_ACTIVA = "obs360_vista_previa"            # preferencia de la persona (sesión)
_CLAVE_CLIENTE = "_obs360_vista_previa_cliente"
_CLAVE_REVISION = "_obs360_vista_previa_revision"
_CLAVE_EN_USO = "_obs360_vista_previa_en_uso"
TTL_CLIENTE = 45 * 60          # el JWT de Supabase dura una hora: se renueva antes
TTL_FALLO = 5 * 60             # tras un inicio de sesión fallido, no reintentar enseguida
TTL_REVISION = 2 * 60          # cada cuánto se vuelve a mirar si hay corrida nueva

# Sesión fuera de Streamlit (pruebas, scripts): un diccionario del módulo.
_RESPALDO: dict = {}
_AVISADO_SIN_CREDENCIALES = False


def registrar_fallo(donde: str, exc: BaseException) -> None:
    """Anota un fallo tragado: dónde y el tipo de la excepción, nunca el mensaje.

    El mensaje de supabase/gotrue puede traer el correo del usuario de carga o
    partes de la petición; el tipo y el paso bastan para diagnosticar en los
    registros de Streamlit Cloud.
    """
    logger.warning("Vista previa [%s]: %s. Se sigue con lo publicado.",
                   donde, type(exc).__name__)


# ── Utilidades ──────────────────────────────────────────────────────────────
def _ahora() -> float:
    """Separado para que las pruebas muevan el reloj."""
    return time.monotonic()


def _sesion():
    """`st.session_state` dentro de una ejecución de Streamlit; si no, `_RESPALDO`."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        try:
            ctx = get_script_run_ctx(suppress_warning=True)
        except TypeError:                                  # Streamlit sin ese parámetro
            ctx = get_script_run_ctx()
        if ctx is not None:
            import streamlit as st
            return st.session_state
    except Exception:                                      # noqa: BLE001
        pass
    return _RESPALDO


def _modo() -> str:
    try:
        from src.core import modo as modo_app
        return modo_app.modo()
    except Exception:                                      # noqa: BLE001
        return "comunidad"


def modo_privado() -> bool:
    """True en los modos donde la vista previa puede existir."""
    return _modo() in ("investigador", "completo")


# ── Credenciales y cliente ──────────────────────────────────────────────────
def credenciales() -> tuple[str | None, str | None]:
    """(email, clave) del usuario de carga, o (None, None). Los del almacén."""
    try:
        from src.data import almacen
        return almacen.credenciales_carga()
    except Exception:                                      # noqa: BLE001
        return None, None


def _conexion() -> tuple[str | None, str | None]:
    """(url, clave anon): las mismas con las que lee la aplicación."""
    try:
        from src.estudiantes import lectura
        return lectura.credenciales()
    except Exception:                                      # noqa: BLE001
        return None, None


def disponible() -> bool:
    """True solo en modo investigador o completo y con las credenciales de carga."""
    if not modo_privado():
        return False
    email, clave = credenciales()
    url, key = _conexion()
    listo = bool(email and clave and url and key)
    if not listo:
        _avisar_sin_credenciales(email=email, clave=clave, url=url, key=key)
    return listo


def _avisar_sin_credenciales(**valores) -> None:
    """Una vez por proceso: qué falta (solo los nombres, nunca los valores)."""
    global _AVISADO_SIN_CREDENCIALES
    if _AVISADO_SIN_CREDENCIALES:
        return
    _AVISADO_SIN_CREDENCIALES = True
    nombres = {"email": "OBS360_CARGA_EMAIL", "clave": "OBS360_CARGA_CLAVE",
               "url": "SUPABASE_URL", "key": "SUPABASE_KEY"}
    faltan = [nombres[k] for k, v in valores.items() if not v]
    logger.warning("Vista previa desactivada en el modo %s: faltan %s.",
                   _modo(), ", ".join(faltan))


def _crear_cliente(url: str, key: str):
    """Cliente de Supabase sin sesión. Separado para inyectar uno falso en las pruebas."""
    from supabase import create_client
    return create_client(url, key)


def cliente_autenticado():
    """Cliente de Supabase con sesión del usuario de carga, o None.

    Uno por sesión de Streamlit, renovado cada `TTL_CLIENTE`. Si el inicio de
    sesión falla, se anota (sin el mensaje, que puede traer el correo) y no se
    reintenta durante `TTL_FALLO`.
    """
    if not disponible():
        return None
    sesion = _sesion()
    guardado = sesion.get(_CLAVE_CLIENTE)
    ahora = _ahora()
    if guardado:
        cliente, desde = guardado
        if ahora - desde < (TTL_CLIENTE if cliente is not None else TTL_FALLO):
            return cliente
    email, clave = credenciales()
    url, key = _conexion()
    cliente = None
    paso = "crear cliente"
    try:
        cliente = _crear_cliente(url, key)
        paso = "iniciar sesión del usuario de carga"
        cliente.auth.sign_in_with_password({"email": email, "password": clave})
    except Exception as exc:                               # noqa: BLE001
        registrar_fallo(f"cliente_autenticado: {paso}; sin reintento en "
                        f"{TTL_FALLO // 60} min", exc)
        cliente = None
    sesion[_CLAVE_CLIENTE] = (cliente, ahora)
    return cliente


# ── Corridas ────────────────────────────────────────────────────────────────
def _corridas(cli):
    return cli.postgrest.schema(ESQUEMA).table("corridas")


def corrida_en_revision(modulo: str, cli=None) -> int | None:
    """Id de la última corrida del módulo si está oculta (más nueva que la publicada).

    Con un cliente que no es cargador (o sin la migración 2026-10-10) solo se ve
    la publicada, así que no hay nada en revisión: None.
    """
    cli = cli if cli is not None else cliente_autenticado()
    if cli is None:
        return None
    filas = (_corridas(cli).select("id,publicada,creada_en").eq("modulo", modulo)
             .order("creada_en", desc=True).limit(1).execute().data)
    if not filas or filas[0].get("publicada"):
        return None
    return int(filas[0]["id"])


def corrida_publicada(modulo: str, cli=None) -> int | None:
    """Id de la última corrida publicada del módulo: la que ve el público."""
    cli = cli if cli is not None else cliente_autenticado()
    if cli is None:
        return None
    filas = (_corridas(cli).select("id").eq("modulo", modulo).eq("publicada", True)
             .order("creada_en", desc=True).limit(1).execute().data)
    return int(filas[0]["id"]) if filas else None


def revision(modulo: str) -> dict | None:
    """{modulo, en_revision, publicada} si hay corrida en revisión; si no, None.

    Se memoriza en la sesión `TTL_REVISION` segundos. Nunca lanza.
    """
    if modulo not in MODULOS or not disponible():
        return None
    memo = _sesion().setdefault(_CLAVE_REVISION, {})
    ahora = _ahora()
    if modulo in memo and ahora - memo[modulo][1] < TTL_REVISION:
        return memo[modulo][0]
    info = None
    paso = "cliente"
    try:
        cli = cliente_autenticado()
        if cli is not None:
            paso = "corrida_en_revision"
            en_revision = corrida_en_revision(modulo, cli)
            if en_revision is not None:
                paso = "corrida_publicada"
                info = dict(modulo=modulo, en_revision=en_revision,
                            publicada=corrida_publicada(modulo, cli))
    except Exception as exc:                               # noqa: BLE001
        registrar_fallo(f"revision({modulo}): {paso}", exc)
        info = None
    memo[modulo] = (info, ahora)
    return info


# ── Preferencia y estado de la página ───────────────────────────────────────
def por_defecto() -> bool:
    """Encendida por defecto en el despliegue del equipo; apagada en el local."""
    return _modo() == "investigador"


def activa() -> bool:
    """¿La persona quiere ver la corrida en revisión? (interruptor de la barra lateral)."""
    if not disponible():
        return False
    return bool(_sesion().get(CLAVE_ACTIVA, por_defecto()))


def marcar_en_uso(modulo: str, en_uso: bool) -> None:
    """Anota si la página del módulo está mostrando ahora la corrida en revisión."""
    sesion = _sesion()
    actuales = set(sesion.get(_CLAVE_EN_USO, ()) or ())
    (actuales.add if en_uso else actuales.discard)(modulo)
    sesion[_CLAVE_EN_USO] = tuple(sorted(actuales))


def en_uso(modulo: str) -> bool:
    """True si la página del módulo muestra la corrida en revisión (avisos internos)."""
    if not modo_privado():
        return False
    return modulo in (_sesion().get(_CLAVE_EN_USO, ()) or ())


# ── Textos ──────────────────────────────────────────────────────────────────
def etiqueta_interruptor(info: dict) -> str:
    return f"Vista previa: corrida en revisión ({info['en_revision']})"


def texto_banner(info: dict) -> str:
    publica = info.get("publicada")
    cola = (f"Lo público sigue mostrando la corrida {publica}." if publica is not None
            else "Lo público todavía no muestra ninguna corrida de este módulo.")
    return ("Vista previa para el equipo: esta corrida no está publicada; los textos de "
            "alertas y de Cuidadores son provisionales y están pendientes de aprobación. "
            + cola)


# ── Streamlit ───────────────────────────────────────────────────────────────
def interruptor(modulo: str) -> dict | None:
    """Dibuja el interruptor en la barra lateral si hay corrida en revisión.

    Devuelve la información de `revision` si la vista previa está encendida, o
    None (sin corrida en revisión, sin credenciales, apagada o si algo falla).
    """
    info = revision(modulo)
    if info is None:
        return None
    try:
        import streamlit as st
        sesion = _sesion()
        with st.sidebar:
            valor = st.toggle(etiqueta_interruptor(info),
                              value=bool(sesion.get(CLAVE_ACTIVA, por_defecto())),
                              key=f"vista_previa_{modulo}",
                              help="Muestra la última corrida subida y aún no aprobada. "
                                   "Solo existe en el despliegue del equipo.")
        sesion[CLAVE_ACTIVA] = bool(valor)
    except Exception as exc:                               # noqa: BLE001
        registrar_fallo(f"interruptor({modulo}): st.toggle", exc)
        return None
    return info if valor else None


def banner(info: dict) -> None:
    """Franja fija arriba de la página: esta corrida no es la pública."""
    import streamlit as st
    from html import escape
    st.markdown(
        '<div class="obs360-vista-previa" role="alert" style="position:sticky;top:3.25rem;'
        "z-index:999;background:#fff4d6;color:#4a3500;border:2px solid #e0a800;"
        'border-radius:8px;padding:0.75rem 1rem;margin-bottom:1rem;font-weight:600">'
        f"🔍 {escape(texto_banner(info))}</div>",
        unsafe_allow_html=True)
