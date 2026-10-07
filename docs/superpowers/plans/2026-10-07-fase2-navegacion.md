# Fase 2 · Navegación — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** «Dashboard» pasa a llamarse «Docentes», el menú queda listo para Cuidadores 360 y Triangulación 360, y el colegio y el rol elegidos sobreviven al cambio de página.

**Architecture:** La lista de páginas, su orden y la página inicial viven en un módulo **nuevo**, `src/core/navegacion.py`. Que sea nuevo es deliberado: tras un despliegue, Streamlit puede conservar en memoria la versión vieja de un módulo ya importado (pasó con `src.core.modo`), pero un módulo nuevo siempre se importa fresco. Las páginas que todavía no existen (Cuidadores, Triangulación) están en el orden del menú pero no en `DISPONIBLES`, así que no aparecen hasta sus fases. El estado compartido entre páginas vive en `src/ui/estado.py`: claves de sesión fuera de los widgets, porque Streamlit borra el estado de un widget que deja de dibujarse (comprobado con AppTest en 1.51 y 1.65).

**Tech Stack:** Python 3.13 (local) / 3.14 (Streamlit Cloud), Streamlit 1.51 local → 1.65 en producción, pytest, `streamlit.testing.v1.AppTest`, Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-10-06-cuidadores-alertas-triangulacion-design.md` §5.3.

**Restricciones que no se negocian:**
- Nada cambia en lo que se ve salvo los nombres. Las cifras, informes y vistas de estudiantes quedan iguales.
- En modo comunidad, `main.py` corta (`st.stop()`) antes de importar el cargador, el chat, los informes, el dashboard, la vista de investigador y, a futuro, triangulación.
- No se fusiona a `main` sin permiso del usuario. Tras fusionar, siempre «Reboot app».
- Suite verde. Línea base en `main` (42ff220): 433 passed, 2 skipped.
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

**Comando de pruebas:** `.venv/bin/python -m pytest -q` (desde la raíz del repo).

---

## Mapa de archivos

| Archivo | Qué cambia |
|---|---|
| `src/core/navegacion.py` (nuevo) | Constantes de página, `MENU`, `DISPONIBLES`, `PUBLICAS`, `menu(modo)`, `pagina_inicial(modo)` |
| `src/core/modo.py` | `paginas_permitidas()` y `pagina_por_defecto()` delegan en `navegacion`; `PAGINA_ESTUDIANTES` se reexporta |
| `main.py` | Menú desde `navegacion.menu`, ruteo por constantes, rama comunidad con selector si hay más de una página, `page_title` público |
| `src/ui/estado.py` (nuevo) | `COLEGIO`, `ROL`, `sembrar()`, `guardar()`, `aplicar_colegio_de_url()` |
| `src/ui/estudiantes.py` | `?colegio=` se guarda en el estado compartido |
| `src/ui/views/estudiantes_comunidad.py` | Rol y colegio se siembran y se guardan en el estado compartido; vista previa con `st.iframe` si existe |
| `src/core/state.py`, `src/ui/reports.py`, `src/ui/dashboard.py` | Renombrar «Dashboard» → «Docentes» |
| `tests/test_navegacion.py` (nuevo), `tests/test_estado_compartido.py` (nuevo), `tests/test_modo_despliegue.py` | Pruebas |
| `ARCHITECTURE.md`, `README.md`, `DESPLIEGUE.md` | Nombres y menú |

---

### Task 1: Módulo de navegación

**Files:**
- Create: `src/core/navegacion.py`
- Create: `tests/test_navegacion.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_navegacion.py`:

```python
"""
Pruebas del menú: nombres, orden, qué páginas existen y cuáles ve cada modo.
"""
from src.core import navegacion as nav
from src.core.modo import COMPLETO, COMUNIDAD, INVESTIGADOR


def test_nombres_de_las_paginas():
    assert nav.PAGINA_DOCENTES == "Docentes"
    assert nav.PAGINA_ESTUDIANTES == "Estudiantes 360"
    assert nav.PAGINA_CUIDADORES == "Cuidadores 360"
    assert nav.PAGINA_TRIANGULACION == "Triangulación 360"


def test_orden_del_menu_es_el_de_la_spec():
    assert nav.MENU == (
        "Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360",
        "Chat con IA", "Cargar Datos", "Análisis de tendencias", "Reportes")


def test_ya_no_existe_la_pagina_dashboard():
    assert "Dashboard" not in nav.MENU


def test_las_paginas_sin_construir_no_salen_en_el_menu():
    """Cuidadores y Triangulación llegan en las fases 4 y 5."""
    for m in (COMPLETO, INVESTIGADOR, COMUNIDAD):
        assert nav.PAGINA_CUIDADORES not in nav.menu(m)
        assert nav.PAGINA_TRIANGULACION not in nav.menu(m)


def test_completo_e_investigador_ven_todas_las_disponibles_en_orden():
    esperado = ["Docentes", "Estudiantes 360", "Chat con IA", "Cargar Datos",
                "Análisis de tendencias", "Reportes"]
    assert nav.menu(COMPLETO) == esperado
    assert nav.menu(INVESTIGADOR) == esperado


def test_comunidad_solo_ve_paginas_publicas():
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    assert set(nav.PUBLICAS) == {nav.PAGINA_ESTUDIANTES, nav.PAGINA_CUIDADORES}


def test_triangulacion_nunca_es_publica():
    assert nav.PAGINA_TRIANGULACION not in nav.PUBLICAS


def test_cuando_cuidadores_este_disponible_comunidad_lo_ve(monkeypatch):
    monkeypatch.setattr(nav, "DISPONIBLES",
                        nav.DISPONIBLES | {nav.PAGINA_CUIDADORES, nav.PAGINA_TRIANGULACION})
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360", "Cuidadores 360"]
    assert nav.menu(INVESTIGADOR)[:4] == [
        "Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360"]


def test_pagina_inicial_por_modo():
    assert nav.pagina_inicial(COMPLETO) == "Docentes"
    assert nav.pagina_inicial(INVESTIGADOR) == "Estudiantes 360"
    assert nav.pagina_inicial(COMUNIDAD) == "Estudiantes 360"


def test_un_modo_desconocido_se_trata_como_comunidad():
    assert nav.menu("cualquier-cosa") == nav.menu(COMUNIDAD)
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_navegacion.py -q`
Expected: FAIL con `ImportError: cannot import name 'navegacion'`.

- [ ] **Step 3: Implementar**

`src/core/navegacion.py`:

```python
"""
Navegación — Observatorio 360.

Nombres de página, orden del menú y página inicial por modo de despliegue.

Vive en un módulo propio, y no en `modo.py`, por una razón práctica: al
desplegar, Streamlit vuelve a ejecutar `main.py` pero puede conservar en memoria
la versión vieja de los módulos ya importados. Un módulo que no existía antes se
importa siempre fresco, así que el menú nuevo nunca convive con un `modo` viejo.

Las páginas que aún no están construidas figuran en `MENU`, para fijar el orden,
pero no en `DISPONIBLES`: no aparecen hasta que su fase las añada.
"""
from __future__ import annotations

PAGINA_DOCENTES = "Docentes"
PAGINA_ESTUDIANTES = "Estudiantes 360"
PAGINA_CUIDADORES = "Cuidadores 360"
PAGINA_TRIANGULACION = "Triangulación 360"
PAGINA_CHAT = "Chat con IA"
PAGINA_CARGA = "Cargar Datos"
PAGINA_TENDENCIAS = "Análisis de tendencias"
PAGINA_REPORTES = "Reportes"

MENU = (PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CUIDADORES, PAGINA_TRIANGULACION,
        PAGINA_CHAT, PAGINA_CARGA, PAGINA_TENDENCIAS, PAGINA_REPORTES)

# Las que ya tienen vista. Cuidadores entra en la fase 4 y Triangulación en la 5.
DISPONIBLES = frozenset({PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CHAT,
                         PAGINA_CARGA, PAGINA_TENDENCIAS, PAGINA_REPORTES})

# Lo único que puede ver el público. Triangulación es solo para investigadores.
PUBLICAS = (PAGINA_ESTUDIANTES, PAGINA_CUIDADORES)

_COMPLETO = "completo"
_INVESTIGADOR = "investigador"


def _es_publico(modo: str) -> bool:
    # Igual que `modo.modo()`: lo que no sea completo o investigador es comunidad.
    return modo not in (_COMPLETO, _INVESTIGADOR)


def menu(modo: str) -> list[str]:
    """Páginas del menú en este modo, en orden."""
    visibles = PUBLICAS if _es_publico(modo) else MENU
    return [p for p in MENU if p in visibles and p in DISPONIBLES]


def pagina_inicial(modo: str) -> str:
    """Con qué página abre la aplicación.

    Los dos modos pensados para estudiantes aterrizan en su módulo; el modo de
    trabajo local abre en Docentes, como siempre.
    """
    return PAGINA_DOCENTES if modo == _COMPLETO else PAGINA_ESTUDIANTES
```

- [ ] **Step 4: Correr y ver que pasan**

Run: `.venv/bin/python -m pytest tests/test_navegacion.py -q`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/core/navegacion.py tests/test_navegacion.py
git commit -m "feat(navegacion): menú con Docentes y páginas por modo"
```

---

### Task 2: `modo.py` delega en navegación

**Files:**
- Modify: `src/core/modo.py:62-90`
- Modify: `tests/test_modo_despliegue.py:189-195, 223-237`

- [ ] **Step 1: Actualizar las pruebas**

En `tests/test_modo_despliegue.py`, `test_la_pagina_inicial_depende_del_modo` termina con:

```python
    m = con_modo(None)
    assert m.pagina_por_defecto() == "Docentes"
```

Y `test_la_alternativa_devuelve_una_pagina_valida` usa `"Docentes"` en lugar de `"Dashboard"`:

```python
    opciones = ["Docentes", "Estudiantes 360", "Chat con IA"]
    pagina_inicial = getattr(ModuloRancio, "pagina_por_defecto", None)
    inicial = pagina_inicial() if callable(pagina_inicial) else opciones[0]
    assert inicial == "Docentes"
    assert opciones.index(inicial) == 0
```

Añadir al final del archivo:

```python
def test_modo_y_navegacion_coinciden(con_modo):
    from src.core import navegacion as nav
    for valor in (None, "investigador", "comunidad"):
        m = con_modo(valor)
        assert m.pagina_por_defecto() == nav.pagina_inicial(m.modo())
    m = con_modo("comunidad")
    assert m.paginas_permitidas() == nav.menu(m.COMUNIDAD)
```

- [ ] **Step 2: Correr y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_modo_despliegue.py -q`
Expected: FAIL en `test_la_pagina_inicial_depende_del_modo` (`'Dashboard' == 'Docentes'`).

- [ ] **Step 3: Implementar**

En `src/core/modo.py`, reemplazar desde `def paginas_permitidas` hasta el final del archivo, conservando `audiencias_permitidas` y `audiencia_por_defecto` tal como están:

```python
def paginas_permitidas() -> list[str] | None:
    """Páginas visibles en este modo. None = todas.

    Solo el modo comunidad restringe. En investigador se ve toda la plataforma:
    quien revisa también la va a enseñar, y conviene que la conozca entera.
    """
    from src.core import navegacion
    return navegacion.menu(COMUNIDAD) if modo() == COMUNIDAD else None


def audiencias_permitidas() -> list[str] | None:
    """Vistas del módulo de estudiantes disponibles. None = las dos."""
    return ["comunidad"] if modo() == COMUNIDAD else None


def audiencia_por_defecto() -> str:
    """Vista con la que abre el módulo de estudiantes en este modo."""
    return "investigador" if modo() == INVESTIGADOR else "comunidad"


PAGINA_ESTUDIANTES = "Estudiantes 360"


def pagina_por_defecto() -> str:
    """Página con la que abre la aplicación. La decide `navegacion`."""
    from src.core import navegacion
    return navegacion.pagina_inicial(modo())
```

Y en el docstring del módulo, la línea `OBS360_MODO = "comunidad"     SOLO la vista de estudiantes para colegios,` y las tres que la siguen pasan a:

```
    OBS360_MODO = "comunidad"     SOLO las páginas públicas (Estudiantes 360 y,
                                  cuando se habilite, Cuidadores 360) en su vista
                                  para colegios, familias y municipio. Es el único
                                  modo que restringe, y es lo que se despliega en
                                  público.
```

- [ ] **Step 4: Correr y ver que pasan**

Run: `.venv/bin/python -m pytest tests/test_modo_despliegue.py tests/test_navegacion.py -q`
Expected: todos pasan.

- [ ] **Step 5: Commit**

```bash
git add src/core/modo.py tests/test_modo_despliegue.py
git commit -m "refactor(modo): la página inicial y las públicas salen de navegacion"
```

---

### Task 3: `main.py` con el menú nuevo y la rama comunidad con selector

**Files:**
- Modify: `main.py:1-33, 93-134`
- Modify: `tests/test_modo_despliegue.py:85-115, 198-221`

- [ ] **Step 1: Actualizar las pruebas estructurales**

En `tests/test_modo_despliegue.py`:

1. `test_el_punto_de_entrada_corta_antes_de_importar_lo_demas`: añadir, después del bucle existente,

```python
    # lo que llega en fases futuras tampoco puede importarse antes del corte
    for modulo in ("triangulacion", "cuidadores_investigador"):
        assert modulo not in antes, f"{modulo} se importa antes del corte público"
```

2. Reemplazar `test_la_navegacion_se_filtra_por_modo` por:

```python
def test_la_navegacion_se_filtra_por_modo():
    fuente = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    assert "nav.menu(_MODO)" in fuente
    # ningún nombre de página escrito a mano: todos salen de navegacion
    for nombre in ('"Dashboard"', '"Docentes"', '"Estudiantes 360"', '"Chat con IA"',
                   '"Cargar Datos"', '"Reportes"'):
        assert nombre not in fuente, f"{nombre} está escrito a mano en main.py"


def test_el_titulo_publico_es_de_comunidad():
    fuente = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    assert "Observatorio 360 · Comunidad" in fuente
```

3. Reemplazar `test_el_punto_de_entrada_usa_la_pagina_inicial_del_modo` por:

```python
def test_el_punto_de_entrada_usa_la_pagina_inicial_del_modo():
    fuente = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    assert "nav.pagina_inicial(_MODO)" in fuente
    assert "index=_indice" in fuente
```

4. En `test_el_arranque_sobrevive_a_un_modulo_rancio`, reemplazar las dos aserciones sobre `main.py` (las de `pagina_por_defecto`) por:

```python
    assert "from src.core import navegacion as nav" in fuente, \
        "el menú debe venir de un módulo nuevo, que nunca está rancio"
    assert "modo_app.pagina_por_defecto" not in fuente
```

Las dos aserciones sobre `src/ui/estudiantes.py` se quedan igual.

- [ ] **Step 2: Correr y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_modo_despliegue.py -q`
Expected: FAIL en `test_la_navegacion_se_filtra_por_modo`, `test_el_titulo_publico_es_de_comunidad`, `test_el_punto_de_entrada_usa_la_pagina_inicial_del_modo` y `test_el_arranque_sobrevive_a_un_modulo_rancio`.

- [ ] **Step 3: Implementar**

En `main.py`, reemplazar las líneas 1-33 (hasta el primer `st.stop()` incluido) por:

```python
"""
Observatorio de Salud Organizacional — Main Entry Point
"""
import streamlit as st
from src.core import modo as modo_app
from src.core import navegacion as nav
from src.core.state import init_session_state

_MODO = modo_app.modo()
_PUBLICO = _MODO == modo_app.COMUNIDAD

# Page Config
st.set_page_config(
    page_title=("Observatorio 360 · Comunidad" if _PUBLICO
                else "Observatorio de Salud Organizacional"),
    page_icon=("🎒" if _PUBLICO else "📊"),
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize State
init_session_state()

# ─────────────────────────────────────────────────────────────────────────────
# Despliegue público: solo las vistas de comunidad.
# Se corta aquí, antes de importar el cargador de archivos, el chat, los
# informes o la vista de investigación. En esta ejecución esos módulos no
# existen, así que no hay URL ni clic que lleve a ellos.
# ─────────────────────────────────────────────────────────────────────────────
if _PUBLICO:
    _publicas = nav.menu(_MODO)
    if len(_publicas) > 1:
        with st.sidebar:
            _pagina_publica = st.radio("Ir a:", _publicas, key="nav_pagina")
    else:
        _pagina_publica = _publicas[0]
    if _pagina_publica == nav.PAGINA_ESTUDIANTES:
        from src.ui.estudiantes import render_estudiantes
        render_estudiantes()
    st.stop()
```

Y reemplazar desde `# --- Sidebar Navigation ---` hasta `render_reports_page()` (líneas 93-134) por:

```python
# --- Sidebar Navigation ---
with st.sidebar:
    st.title("Navegación")
    _opciones = nav.menu(_MODO)
    # El modo decide con qué página abre; después manda lo que elija la persona.
    # El menú sale de `navegacion`, un módulo nuevo: tras un despliegue nunca
    # queda en memoria una versión vieja que no tenga estas funciones.
    _inicial = nav.pagina_inicial(_MODO)
    _indice = _opciones.index(_inicial) if _inicial in _opciones else 0
    page = st.radio("Ir a:", _opciones, index=_indice, key="nav_pagina")

# --- Main Routing ---
if page == nav.PAGINA_DOCENTES:
    from src.ui.dashboard import render_dashboard
    render_dashboard()

elif page == nav.PAGINA_ESTUDIANTES:
    from src.ui.estudiantes import render_estudiantes
    render_estudiantes()

elif page == nav.PAGINA_CHAT:
    from src.ui.chat import render_chat
    render_chat()

elif page == nav.PAGINA_CARGA:
    from src.ui.upload import render_upload
    render_upload()

elif page == nav.PAGINA_TENDENCIAS:
    from src.ui.trends import render_trends
    render_trends()

elif page == nav.PAGINA_REPORTES:
    render_reports_page()
```

- [ ] **Step 4: Correr y ver que pasan**

Run: `.venv/bin/python -m pytest tests/test_modo_despliegue.py tests/test_navegacion.py -q`
Expected: todos pasan.

- [ ] **Step 5: Prueba de humo con AppTest en modo comunidad**

Añadir a `tests/test_navegacion.py`:

```python
def test_main_en_comunidad_no_importa_modulos_internos(monkeypatch):
    """Arranca main.py de verdad en modo comunidad, sin datos ni Supabase."""
    import sys
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    monkeypatch.setenv("OBS360_DATOS_DIR", "/ruta/que/no/existe")
    for m in ("src.ui.dashboard", "src.ui.chat", "src.ui.upload", "src.ui.reports",
              "src.ui.views.estudiantes_investigador"):
        sys.modules.pop(m, None)
    at = AppTest.from_file("main.py", default_timeout=60).run()
    assert not at.exception
    for m in ("src.ui.dashboard", "src.ui.chat", "src.ui.upload", "src.ui.reports",
              "src.ui.views.estudiantes_investigador"):
        assert m not in sys.modules, f"{m} se importó en modo comunidad"
```

`OBS360_DATOS_DIR` es la variable que lee `src/core/rutas.py`. Si Supabase está configurado en `.streamlit/secrets.toml`, la página puede leer la corrida publicada: está bien, la prueba solo exige que no haya excepción ni importaciones prohibidas.

Run: `.venv/bin/python -m pytest tests/test_navegacion.py -q`
Expected: pasa.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_modo_despliegue.py tests/test_navegacion.py
git commit -m "feat(navegacion): Dashboard pasa a Docentes y el menú sale de navegacion"
```

---

### Task 4: Renombrar «Dashboard» en el resto del código

**Files:**
- Modify: `src/core/state.py:62-63`
- Modify: `src/ui/reports.py:19,24`
- Modify: `src/ui/dashboard.py:2,559`
- Test: `tests/test_navegacion.py`

- [ ] **Step 1: Prueba que falla**

Añadir a `tests/test_navegacion.py`:

```python
def test_no_queda_dashboard_visible_en_la_interfaz():
    """Lo que ve la persona dice «Docentes». Los comentarios técnicos no cuentan."""
    import pathlib
    import re
    raiz = pathlib.Path(__file__).resolve().parents[1]
    culpables = []
    for f in [raiz / "main.py", *(raiz / "src" / "ui").rglob("*.py"),
              raiz / "src" / "core" / "state.py"]:
        texto = f.read_text(encoding="utf-8")
        # cadenas entre comillas que contienen la palabra
        for m in re.finditer(r'"[^"\n]*Dashboard[^"\n]*"', texto):
            culpables.append(f"{f.relative_to(raiz)}: {m.group(0)}")
    assert not culpables, culpables
```

Run: `.venv/bin/python -m pytest tests/test_navegacion.py::test_no_queda_dashboard_visible_en_la_interfaz -q`
Expected: FAIL listando `state.py`, `reports.py` y `dashboard.py`.

- [ ] **Step 2: Implementar**

- `src/core/state.py:63`: `st.session_state.current_page = "Docentes"`.
- `src/ui/reports.py:19`: `["Datos cargados (Docentes)", "Archivo Nuevo"]` y `:24`: `if data_source == "Datos cargados (Docentes)":`.
- `src/ui/dashboard.py:2`: `Docentes — dashboard dual del Observatorio de Salud Organizacional.`
- `src/ui/dashboard.py:559`: `st.markdown("## 📊 Docentes · Salud Organizacional")`.

No tocar `src/analysis/scoring.py` (comentario técnico) ni `tests/test_dashboard_fix.py` / `tests/test_deep_dashboard.py` (nombres de pruebas).

- [ ] **Step 3: Correr la suite completa**

Run: `.venv/bin/python -m pytest -q`
Expected: todo pasa (línea base: 433 passed, 2 skipped, más las pruebas nuevas).

- [ ] **Step 4: Commit**

```bash
git add src/core/state.py src/ui/reports.py src/ui/dashboard.py tests/test_navegacion.py
git commit -m "feat(docentes): renombrar Dashboard a Docentes en la interfaz"
```

---

### Task 5: Estado compartido entre páginas (colegio y rol)

**Files:**
- Create: `src/ui/estado.py`
- Create: `tests/test_estado_compartido.py`
- Modify: `src/ui/views/estudiantes_comunidad.py:920-938, 955-957`
- Modify: `src/ui/estudiantes.py:209-214`

Contexto: Streamlit borra el valor de un widget cuando deja de dibujarse en una ejecución. Al pasar a otra página (Cuidadores, en la fase 4) y volver, el colegio y el rol volvían a su valor inicial. La solución, comprobada con AppTest en 1.51 y 1.65: una clave de sesión que no pertenece a ningún widget guarda el valor; antes de dibujar el widget, si su clave no existe, se siembra desde ella; después de dibujarlo, se guarda.

- [ ] **Step 1: Pruebas que fallan**

`tests/test_estado_compartido.py`:

```python
"""
El colegio y el rol elegidos sobreviven al cambio de página.
"""
from streamlit.testing.v1 import AppTest


def _app():
    import streamlit as st
    from src.ui import estado
    pagina = st.radio("pagina", ["A", "B"], key="pagina")
    opciones = ["Todos", "LauV", "CND"] if pagina == "A" else ["Todos", "CND"]
    clave = "a_colegio" if pagina == "A" else "b_colegio"
    estado.sembrar(clave, estado.COLEGIO, opciones)
    valor = st.selectbox("colegio", opciones, key=clave)
    estado.guardar(estado.COLEGIO, valor)


def test_el_colegio_sobrevive_al_ir_y_volver():
    at = AppTest.from_function(_app).run()
    at.selectbox(key="a_colegio").set_value("CND").run()
    at.radio(key="pagina").set_value("B").run()
    assert at.selectbox(key="b_colegio").value == "CND"
    at.radio(key="pagina").set_value("A").run()
    assert at.selectbox(key="a_colegio").value == "CND"


def test_un_valor_que_no_esta_en_las_opciones_no_se_siembra():
    at = AppTest.from_function(_app).run()
    at.selectbox(key="a_colegio").set_value("LauV").run()
    at.radio(key="pagina").set_value("B").run()
    assert at.selectbox(key="b_colegio").value == "Todos"


def test_sembrar_no_pisa_lo_que_eligio_la_persona():
    from src.ui import estado
    sesion = {"w": "CND", estado.COLEGIO: "LauV"}
    estado.sembrar("w", estado.COLEGIO, ["LauV", "CND"], sesion=sesion)
    assert sesion["w"] == "CND"


def test_el_colegio_de_la_url_se_aplica_una_sola_vez():
    from src.ui import estado
    sesion = {}
    estado.aplicar_colegio_de_url("LauV", sesion=sesion)
    assert sesion[estado.COLEGIO] == "LauV"
    sesion[estado.COLEGIO] = "CND"            # la persona cambió de colegio
    estado.aplicar_colegio_de_url("LauV", sesion=sesion)
    assert sesion[estado.COLEGIO] == "CND"


def test_sin_colegio_en_la_url_no_hace_nada():
    from src.ui import estado
    sesion = {}
    estado.aplicar_colegio_de_url(None, sesion=sesion)
    assert estado.COLEGIO not in sesion
```

Run: `.venv/bin/python -m pytest tests/test_estado_compartido.py -q`
Expected: FAIL con `ImportError: cannot import name 'estado'`.

- [ ] **Step 2: Implementar `src/ui/estado.py`**

```python
"""
Estado compartido entre páginas — Observatorio 360.

El colegio y el rol que elige la persona deben seguir elegidos al pasar de
Estudiantes a Cuidadores y volver. Streamlit no lo garantiza: borra el valor de
un widget en cuanto una ejecución no lo dibuja. Por eso el valor se guarda
también en una clave de sesión que no pertenece a ningún widget, y cada página
siembra su widget desde ella.
"""
from __future__ import annotations

from typing import Any, MutableMapping, Sequence

import streamlit as st

COLEGIO = "obs360_colegio"
ROL = "obs360_rol"
_URL_APLICADA = "obs360_colegio_url_aplicada"


def _sesion(sesion: MutableMapping | None) -> MutableMapping:
    return st.session_state if sesion is None else sesion


def sembrar(clave_widget: str, clave_compartida: str, opciones: Sequence[Any],
            sesion: MutableMapping | None = None) -> None:
    """Antes de dibujar el widget: si no tiene valor, toma el compartido.

    Solo si ese valor es una de las opciones; si no, el widget usa su valor
    inicial. Nunca pisa lo que la persona ya eligió en este widget.
    """
    s = _sesion(sesion)
    if clave_widget not in s and s.get(clave_compartida) in list(opciones):
        s[clave_widget] = s[clave_compartida]


def guardar(clave_compartida: str, valor: Any,
            sesion: MutableMapping | None = None) -> None:
    """Después de dibujar el widget: el valor elegido pasa a ser el compartido."""
    _sesion(sesion)[clave_compartida] = valor


def aplicar_colegio_de_url(codigo: str | None,
                           sesion: MutableMapping | None = None) -> None:
    """`?colegio=` preselecciona el colegio una sola vez por sesión.

    Después manda lo que la persona elija. `codigo` ya debe venir validado
    (`estudiantes.colegio_de_la_url`).
    """
    s = _sesion(sesion)
    if codigo and not s.get(_URL_APLICADA):
        s[COLEGIO] = codigo
        s[_URL_APLICADA] = True
```

- [ ] **Step 3: Correr las pruebas del módulo**

Run: `.venv/bin/python -m pytest tests/test_estado_compartido.py -q`
Expected: 5 passed.

- [ ] **Step 4: Usar el estado compartido en la vista comunidad**

En `src/ui/views/estudiantes_comunidad.py`, dentro de `_selector_grupo`, sustituir

```python
    if st.session_state.get(clave, TODOS) not in [TODOS] + opciones:
        st.session_state[clave] = TODOS     # el grado elegido no existe en este colegio
    valor = st.sidebar.selectbox(etiqueta, [TODOS] + opciones, key=clave)
    return valor, pequenos
```

por

```python
    if columna == "Colegio":
        estado.sembrar(clave, estado.COLEGIO, [TODOS] + opciones)
    if st.session_state.get(clave, TODOS) not in [TODOS] + opciones:
        st.session_state[clave] = TODOS     # el grado elegido no existe en este colegio
    valor = st.sidebar.selectbox(etiqueta, [TODOS] + opciones, key=clave)
    if columna == "Colegio":
        estado.guardar(estado.COLEGIO, valor)
    return valor, pequenos
```

y en `render_comunidad`, sustituir

```python
    rol = st.radio("Estoy viendo esto como", list(cat.ROLES),
                   format_func=lambda r: cat.ROLES[r], horizontal=True,
                   key="est_com_rol")
```

por

```python
    estado.sembrar("est_com_rol", estado.ROL, list(cat.ROLES))
    rol = st.radio("Estoy viendo esto como", list(cat.ROLES),
                   format_func=lambda r: cat.ROLES[r], horizontal=True,
                   key="est_com_rol")
    estado.guardar(estado.ROL, rol)
```

Añadir `from src.ui import estado` junto a los demás imports de `src.` al principio del archivo.

- [ ] **Step 5: El enlace `?colegio=` escribe en el estado compartido**

En `src/ui/estudiantes.py`, sustituir

```python
        preseleccion = colegio_de_la_url(analisis)
        if preseleccion and "est_com_colegio" not in st.session_state:
            st.session_state["est_com_colegio"] = preseleccion
```

por

```python
        from src.ui import estado
        estado.aplicar_colegio_de_url(colegio_de_la_url(analisis))
```

y actualizar el comentario de encima: «Enlace por colegio: ?colegio=LauV deja su colegio preseleccionado la primera vez, en Estudiantes y en Cuidadores. Después manda lo que la persona elija.»

- [ ] **Step 6: Suite completa**

Run: `.venv/bin/python -m pytest -q`
Expected: todo pasa (línea base: 433 passed, 2 skipped, más las pruebas nuevas).

- [ ] **Step 7: Commit**

```bash
git add src/ui/estado.py tests/test_estado_compartido.py src/ui/views/estudiantes_comunidad.py src/ui/estudiantes.py
git commit -m "feat(navegacion): el colegio y el rol sobreviven al cambio de página"
```

---

### Task 6: Vista previa con `st.iframe` cuando existe

**Files:**
- Modify: `src/ui/views/estudiantes_comunidad.py:1108, 1150`
- Test: `tests/test_estudiantes_comunidad.py`

Streamlit 1.65 (producción) avisa que `st.components.v1.html` se retira y recomienda `st.iframe(src, height=...)`. Local usa 1.51, que no lo tiene: se usa `st.iframe` si existe y si no, el componente viejo.

- [ ] **Step 1: Prueba que falla**

Añadir a `tests/test_estudiantes_comunidad.py`:

```python
def test_la_vista_previa_usa_iframe_si_existe(monkeypatch):
    import streamlit as st
    from src.ui.views import estudiantes_comunidad as vista
    llamadas = []
    monkeypatch.setattr(st, "iframe",
                        lambda src, **kw: llamadas.append((src, kw)), raising=False)
    vista._vista_previa("<html>hola</html>")
    assert llamadas == [("<html>hola</html>", {"height": 900})]


def test_la_vista_previa_cae_al_componente_viejo(monkeypatch):
    import streamlit as st
    import streamlit.components.v1 as components
    from src.ui.views import estudiantes_comunidad as vista
    monkeypatch.delattr(st, "iframe", raising=False)
    llamadas = []
    monkeypatch.setattr(components, "html",
                        lambda html, **kw: llamadas.append((html, kw)))
    vista._vista_previa("<html>hola</html>")
    assert llamadas == [("<html>hola</html>", {"height": 900, "scrolling": True})]
```

Run: `.venv/bin/python -m pytest tests/test_estudiantes_comunidad.py -q -k vista_previa`
Expected: FAIL con `AttributeError: ... has no attribute '_vista_previa'`.

- [ ] **Step 2: Implementar**

Antes de `def _seccion_informes`, añadir:

```python
def _vista_previa(html: str) -> None:
    """Muestra un informe HTML embebido.

    `st.iframe` reemplaza a `components.html`, que Streamlit retira; las
    versiones anteriores a `st.iframe` siguen usando el componente.
    """
    iframe = getattr(st, "iframe", None)
    if callable(iframe):
        iframe(html, height=900)
        return
    import streamlit.components.v1 as components
    components.html(html, height=900, scrolling=True)
```

En `_seccion_informes`, borrar `import streamlit.components.v1 as components` y sustituir `components.html(previa, height=900, scrolling=True)` por `_vista_previa(previa)`.

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_estudiantes_comunidad.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_comunidad.py tests/test_estudiantes_comunidad.py
git commit -m "fix(estudiantes): vista previa con st.iframe donde exista"
```

---

### Task 7: Probar con las versiones de producción

**Files:**
- Ninguno en el repositorio salvo que aparezcan fallos.

Producción corre Python 3.14 y Streamlit 1.65; la suite local corre en 3.13 y 1.51.

- [ ] **Step 1: Crear un entorno con Python 3.14**

```bash
/opt/homebrew/bin/python3.14 -m venv "$TMPDIR/venv314"
"$TMPDIR/venv314/bin/pip" install -q -r requirements.txt pytest
"$TMPDIR/venv314/bin/python" -c "import streamlit, sys; print(sys.version, streamlit.__version__)"
```

Expected: Python 3.14.x y Streamlit 1.65.x. El entorno queda fuera del repo.

- [ ] **Step 2: Correr la suite**

Run: `"$TMPDIR/venv314/bin/python" -m pytest -q`
Expected: lo mismo que en 3.13. Si hay fallas nuevas, registrar cada una: si es un error real del código, corregirlo con prueba y commit propio; si es del entorno (p. ej. un paquete sin rueda para 3.14), anotarlo en el informe sin tocar código.

- [ ] **Step 3: Commit (solo si hubo correcciones)**

```bash
git commit -am "fix: compatibilidad con Python 3.14 / Streamlit 1.65"
```

---

### Task 8: Documentación

**Files:**
- Modify: `ARCHITECTURE.md:77,83,136,146,446`
- Modify: `README.md:16`
- Modify: `DESPLIEGUE.md` (sección de modos, línea ~99, y la de `OBS360_MODO = "comunidad"`)

- [ ] **Step 1: Editar**

- `ARCHITECTURE.md`: en el diagrama, `Nav --> Dashboard[Dashboard]` → `Nav --> Docentes[Docentes]`, `Dashboard --> State` → `Docentes --> State`, y añadir `Nav --> Estudiantes[Estudiantes 360]`. «### 2. Visualización en Dashboard» → «### 2. Visualización en Docentes»; «Navega a Dashboard» → «Navega a Docentes»; «2. **Dashboard**:» → «2. **Docentes**:».
- `README.md:16`: «**Dashboard dual:**» → «**Docentes (dashboard dual):**».
- `DESPLIEGUE.md`: «dashboard» en la línea ~99 → «Docentes». En la descripción del modo comunidad, decir que muestra las páginas públicas (Estudiantes 360 y, cuando se habilite, Cuidadores 360), con un selector de página si hay más de una. Añadir una nota en la sección de despliegue: «Después de fusionar a `main`, haz siempre *Manage app → Reboot app*. Si no, la aplicación puede quedar con módulos viejos en memoria.»
- No tocar las menciones al dashboard de Supabase.

- [ ] **Step 2: Comprobar**

Run: `grep -n "Dashboard" ARCHITECTURE.md README.md DESPLIEGUE.md`
Expected: ninguna mención a la página «Dashboard» (sí pueden quedar las de Supabase).

- [ ] **Step 3: Commit**

```bash
git add ARCHITECTURE.md README.md DESPLIEGUE.md
git commit -m "docs: Docentes, menú por modo y reinicio tras fusionar"
```

---

### Task 9: Verificación de punta a punta con Playwright (local)

**Files:** ninguno.

- [ ] **Step 1: Levantar los tres modos**

```bash
OBS360_MODO=completo     .venv/bin/streamlit run main.py --server.port 8601 --server.headless true &
OBS360_MODO=investigador .venv/bin/streamlit run main.py --server.port 8602 --server.headless true &
OBS360_MODO=comunidad OBS360_FUENTE=supabase .venv/bin/streamlit run main.py --server.port 8603 --server.headless true &
```

- [ ] **Step 2: Comprobar con Playwright MCP**

| Modo | Comprobación |
|---|---|
| completo (8601) | El menú dice Docentes, Estudiantes 360, Chat con IA, Cargar Datos, Análisis de tendencias, Reportes; abre en Docentes; Docentes muestra «📊 Docentes · Salud Organizacional»; ningún «Dashboard» visible |
| investigador (8602) | Abre en Estudiantes 360, vista de investigación; se puede ir a Docentes y volver |
| completo | En Estudiantes (comunidad), elegir rol «Funcionario del municipio» y colegio LauV; ir a Docentes y volver: siguen elegidos |
| comunidad (8603) | Título de pestaña «Observatorio 360 · Comunidad»; sin menú de páginas (solo hay una); `?colegio=LauV` preselecciona LauV; la vista previa del informe se ve |
| comunidad | Ancho 390 px: sin desborde horizontal |
| todos | Sin excepciones en pantalla |

- [ ] **Step 3: Apagar los servidores y borrar `.playwright-mcp/` si se creó**

---

### Task 10: PR (sin fusionar)

- [ ] **Step 1:** `git push -u origin feature/fase2-navegacion`
- [ ] **Step 2:** `gh pr create --base main` con resumen, pruebas y la advertencia: **tras fusionar, Reboot app**.
- [ ] **Step 3:** No fusionar. Lo decide el usuario.
