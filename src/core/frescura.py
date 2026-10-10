"""
Módulos rancios tras un despliegue en caliente — Observatorio 360.

Streamlit Community Cloud actualiza los archivos del repositorio sin reiniciar
el proceso. Streamlit saca de `sys.modules` lo que cambió solo a través del
vigilante de archivos de cada sesión abierta: si en el momento del despliegue
no había ninguna, los módulos ya importados (y el código compilado de main.py)
siguen siendo los viejos hasta que alguien reinicie la aplicación.

Así pasó con la vista previa del equipo (oct 2026): `src.ui.estudiantes` ya
estaba importado (la aplicación abre en Estudiantes) y siguió sin interruptor,
mientras que `src.ui.cuidadores`, importado por primera vez después del
despliegue, sí lo mostraba.

`refrescar()` se llama al principio de cada ejecución de main.py, antes de
cualquier otro import de `src`. Compara la fecha de cada archivo con el momento
en que se cargó su módulo y, si alguno cambió, desaloja TODOS los módulos de los
paquetes vigilados (como hace Streamlit: un módulo nuevo que importe uno viejo
seguiría viendo el viejo). Los imports que siguen en main.py ya los cargan del
disco. Si cambió main.py, además vacía la caché de código de Streamlit y pide
otra ejecución.

Límite: este módulo no se desaloja a sí mismo (guarda el registro). Si cambia
él, o en el despliegue que lo introduce, hace falta un reinicio.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time

logger = logging.getLogger(__name__)

PAQUETES = ("src",)
_PROPIO = __name__
_CERROJO = threading.Lock()
# nombre del módulo -> momento (time.time) a partir del cual se sabe que está cargado
_CARGADO: dict[str, float] = {}
# Toda carga anterior a la primera revisión ocurrió antes de importar este módulo.
_ULTIMA_REVISION = time.time()


def _raiz_por_defecto() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _archivo(modulo) -> str | None:
    ruta = getattr(modulo, "__file__", None)
    return os.path.realpath(ruta) if isinstance(ruta, str) else None


def _vigilados(raiz: str, paquetes: tuple[str, ...]) -> dict[str, str]:
    """{nombre: archivo} de los módulos de `paquetes` cuyo archivo está bajo `raiz`."""
    raiz = os.path.realpath(raiz) + os.sep
    salida = {}
    for nombre, modulo in list(sys.modules.items()):
        if nombre == _PROPIO or modulo is None:
            continue
        if not any(nombre == p or nombre.startswith(p + ".") for p in paquetes):
            continue
        ruta = _archivo(modulo)
        if ruta and ruta.startswith(raiz) and "site-packages" not in ruta:
            salida[nombre] = ruta
    return salida


def _mtime(ruta: str) -> float | None:
    try:
        return os.path.getmtime(ruta)
    except OSError:
        return None


def _desalojar(nombres: list[str]) -> None:
    protegidos = {_PROPIO}
    partes = _PROPIO.split(".")
    protegidos.update(".".join(partes[:i]) for i in range(1, len(partes)))
    for nombre in sorted(nombres, key=len, reverse=True):
        if nombre in protegidos:
            continue
        modulo = sys.modules.pop(nombre, None)
        _CARGADO.pop(nombre, None)
        padre_nombre, _, hijo = nombre.rpartition(".")
        padre = sys.modules.get(padre_nombre) if padre_nombre else None
        # `from paquete import modulo` lee el atributo del padre antes que sys.modules.
        if padre is not None and modulo is not None and getattr(padre, hijo, None) is modulo:
            try:
                delattr(padre, hijo)
            except AttributeError:
                pass


def _vaciar_cache_de_codigo() -> None:
    """Olvida el código compilado de main.py (API interna de Streamlit; si no, nada)."""
    try:
        from streamlit.runtime import Runtime
        if Runtime.exists():
            Runtime.instance()._script_cache.clear()
    except Exception as exc:                               # noqa: BLE001
        logger.warning("Frescura: no se pudo vaciar la caché de código (%s).",
                       type(exc).__name__)


def refrescar(script: str | None = None, *, raiz: str | None = None,
              paquetes: tuple[str, ...] = PAQUETES) -> list[str]:
    """Desaloja los módulos de `paquetes` si alguno cambió en disco desde que se cargó.

    `script` es la ruta de main.py: si cambió, también se vacía la caché de código
    de Streamlit y se pide otra ejecución (fuera de Streamlit, solo lo primero).
    Devuelve los nombres desalojados. Nunca lanza.
    """
    global _ULTIMA_REVISION
    try:
        raiz = raiz or _raiz_por_defecto()
        with _CERROJO:
            ahora = time.time()
            # Un módulo que aún no estaba anotado se cargó después de la revisión
            # anterior: esa es una cota inferior segura de su momento de carga.
            desde_antes = _ULTIMA_REVISION
            _ULTIMA_REVISION = ahora
            vigilados = _vigilados(raiz, paquetes)
            cambiados = []
            for nombre, ruta in vigilados.items():
                cargado = _CARGADO.setdefault(nombre, desde_antes)
                mtime = _mtime(ruta)
                if mtime is not None and mtime > cargado:
                    cambiados.append(nombre)
            script_cambiado = False
            if script:
                clave = "__script__:" + os.path.realpath(script)
                cargado = _CARGADO.setdefault(clave, desde_antes)
                mtime = _mtime(script)
                if mtime is not None and mtime > cargado:
                    script_cambiado = True
                    _CARGADO[clave] = ahora
            desalojados: list[str] = []
            if cambiados:
                _desalojar(sorted(vigilados))
                desalojados = [n for n in sorted(vigilados) if n not in sys.modules]
                # Los que no se pueden desalojar (este módulo y sus paquetes padre)
                # se dan por vistos: si no, se recargaría todo en cada ejecución.
                for nombre in vigilados:
                    if nombre in sys.modules:
                        _CARGADO[nombre] = ahora
                logger.warning("Frescura: %d archivo(s) cambiaron desde que se cargaron (%s); "
                               "se recargan %d módulos.", len(cambiados),
                               ", ".join(sorted(cambiados)[:10]), len(desalojados))
        if script_cambiado:
            logger.warning("Frescura: main.py cambió; se vacía la caché de código.")
            _vaciar_cache_de_codigo()
            _pedir_otra_ejecucion()
        return desalojados
    except Exception as exc:                               # noqa: BLE001
        logger.warning("Frescura: no se pudo revisar los módulos (%s).", type(exc).__name__)
        return []


def _pedir_otra_ejecucion() -> None:
    """`st.rerun()` dentro de una ejecución de Streamlit; fuera, nada."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is None:
            return
    except Exception:                                      # noqa: BLE001
        return
    import streamlit as st
    st.rerun()
