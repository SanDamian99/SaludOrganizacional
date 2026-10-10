"""Módulos rancios tras un despliegue en caliente (`src.core.frescura`).

El fallo de producción (oct 2026): Streamlit Cloud actualiza los archivos sin
reiniciar el proceso. Streamlit solo saca de `sys.modules` lo que cambió si
alguna sesión estaba abierta en ese momento (su vigilante de archivos lo ve); si
no había nadie, los módulos ya importados siguen siendo los viejos para siempre.
`src.ui.estudiantes` se había importado antes (la aplicación abre en
Estudiantes), así que esa página seguía sin vista previa, mientras que
`src.ui.cuidadores`, importado por primera vez después del despliegue, sí la
mostraba.
"""
import ast
import os
import sys
import textwrap
import time
import uuid

import pytest

RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _escribir(ruta, texto, mtime=None):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(texto))
    if mtime is not None:
        os.utime(ruta, (mtime, mtime))


@pytest.fixture
def app_con_paquete(tmp_path):
    """Una aplicación mínima: main.py llama a la guarda y luego importa su página."""
    paquete = f"paq_frescura_{uuid.uuid4().hex[:8]}"
    (tmp_path / paquete).mkdir()
    _escribir(tmp_path / paquete / "__init__.py", "")
    pagina = tmp_path / paquete / "pagina.py"
    _escribir(pagina, """
        import streamlit as st
        def render():
            st.markdown("VIEJO")
    """)
    principal = tmp_path / "main.py"
    _escribir(principal, f"""
        import sys
        sys.path.insert(0, {str(RAIZ_REPO)!r})
        sys.path.insert(0, {str(tmp_path)!r})
        from src.core import frescura
        frescura.refrescar(__file__, raiz={str(tmp_path)!r}, paquetes=({paquete!r},))
        from {paquete} import pagina
        pagina.render()
    """)
    yield principal, pagina, paquete
    for nombre in [m for m in sys.modules if m == paquete or m.startswith(paquete + ".")]:
        sys.modules.pop(nombre, None)


def _despues():
    """Un instante claramente posterior a la última revisión (no en el futuro)."""
    time.sleep(0.05)
    return time.time()


def _textos(at):
    return [m.value for m in at.markdown]


def test_sesion_nueva_tras_despliegue_ve_el_codigo_nuevo(app_con_paquete):
    """Regresión: la página importada antes del despliegue no se queda vieja."""
    from streamlit.testing.v1 import AppTest
    principal, pagina, _ = app_con_paquete

    antes = AppTest.from_file(str(principal), default_timeout=60)
    antes.run()
    assert not antes.exception and _textos(antes) == ["VIEJO"]

    # Despliegue en caliente, sin ninguna sesión abierta: solo cambian los archivos.
    _escribir(pagina, """
        import streamlit as st
        def render():
            st.markdown("NUEVO, otro tamaño")
    """, mtime=_despues())

    despues = AppTest.from_file(str(principal), default_timeout=60)   # sesión nueva
    despues.run()
    assert not despues.exception, [e.value for e in despues.exception]
    assert _textos(despues) == ["NUEVO, otro tamaño"]

    # Y no se vuelve a desalojar sin motivo: la siguiente ejecución no recarga.
    from src.core import frescura
    assert frescura.refrescar(str(principal), raiz=str(principal.parent),
                              paquetes=(app_con_paquete[2],)) == []


def test_desaloja_tambien_el_atributo_del_paquete_padre(app_con_paquete):
    """`from paquete import pagina` lee el atributo del padre: también hay que quitarlo."""
    from src.core import frescura
    principal, pagina, paquete = app_con_paquete
    sys.path.insert(0, str(principal.parent))
    try:
        import importlib
        raiz = str(principal.parent)
        frescura.refrescar(None, raiz=raiz, paquetes=(paquete,))      # revisión previa
        modulo = importlib.import_module(f"{paquete}.pagina")
        assert frescura.refrescar(None, raiz=raiz, paquetes=(paquete,)) == []  # lo anota
        _escribir(pagina, "VALOR = 2  # otro tamaño\n", mtime=_despues())
        desalojados = frescura.refrescar(None, raiz=raiz, paquetes=(paquete,))
        assert f"{paquete}.pagina" in desalojados
        padre = sys.modules.get(paquete)
        assert padre is None or getattr(padre, "pagina", None) is not modulo
        exec(f"from {paquete} import pagina as nueva", globals())
        assert globals()["nueva"].VALOR == 2
    finally:
        sys.path.remove(str(principal.parent))


def test_main_llama_a_la_guarda_antes_de_importar_paginas():
    """main.py desaloja lo rancio antes de cualquier otro import de `src`."""
    with open(os.path.join(RAIZ_REPO, "main.py"), encoding="utf-8") as f:
        arbol = ast.parse(f.read())
    imports_src = []
    for nodo in arbol.body:
        if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("src"):
            imports_src.append((nodo.lineno, nodo.module, [a.name for a in nodo.names]))
    assert imports_src, "main.py no importa nada de src"
    primero = imports_src[0]
    assert primero[1] == "src.core" and primero[2] == ["frescura"], primero
    llamadas = [n.lineno for n in ast.walk(arbol)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "refrescar"
                and getattr(n.func.value, "id", None) == "frescura"]
    assert llamadas and llamadas[0] < imports_src[1][0]


def test_sin_la_guarda_la_sesion_nueva_sigue_viendo_lo_viejo(app_con_paquete):
    """Control: así fallaba producción. Confirma que la prueba de arriba mide algo."""
    from streamlit.testing.v1 import AppTest
    principal, pagina, paquete = app_con_paquete
    _escribir(principal, principal.read_text(encoding="utf-8").replace(
        "frescura.refrescar(", "(lambda *a, **k: None)("))
    AppTest.from_file(str(principal), default_timeout=60).run()
    _escribir(pagina, """
        import streamlit as st
        def render():
            st.markdown("NUEVO, otro tamaño")
    """, mtime=_despues())
    despues = AppTest.from_file(str(principal), default_timeout=60)
    despues.run()
    assert _textos(despues) == ["VIEJO"]


def test_solo_vigila_los_paquetes_bajo_la_raiz_y_nunca_a_si_misma():
    from src.core import frescura
    vigilados = frescura._vigilados(RAIZ_REPO, ("src", "streamlit", "pandas"))
    assert "src.core.vista_previa" in vigilados or "src.core.modo" in vigilados
    assert "src.core.frescura" not in vigilados
    assert not any(n.startswith(("streamlit", "pandas")) for n in vigilados)


def test_un_paquete_que_no_se_puede_desalojar_no_recarga_en_cada_ejecucion(
        app_con_paquete, monkeypatch):
    """Si cambia un padre de la guarda (no desalojable), se recarga una vez, no siempre."""
    import importlib
    from src.core import frescura
    principal, pagina, paquete = app_con_paquete
    raiz = str(principal.parent)
    monkeypatch.setattr(frescura, "_PROPIO", f"{paquete}.guarda")   # protege `paquete`
    sys.path.insert(0, raiz)
    try:
        frescura.refrescar(None, raiz=raiz, paquetes=(paquete,))
        importlib.import_module(f"{paquete}.pagina")
        assert frescura.refrescar(None, raiz=raiz, paquetes=(paquete,)) == []
        _escribir(principal.parent / paquete / "__init__.py", "# cambiado\n",
                  mtime=_despues())
        assert frescura.refrescar(None, raiz=raiz, paquetes=(paquete,)) == [f"{paquete}.pagina"]
        assert paquete in sys.modules
        importlib.import_module(f"{paquete}.pagina")
        assert frescura.refrescar(None, raiz=raiz, paquetes=(paquete,)) == []
    finally:
        sys.path.remove(raiz)
