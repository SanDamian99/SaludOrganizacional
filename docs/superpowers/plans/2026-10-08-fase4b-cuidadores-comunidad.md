# Fase 4b · Cuidadores 360: vista de comunidad, informes y publicación — plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** colegios, familias y el municipio ven, con los mismos roles, colores y estructura que Estudiantes 360, cómo están los cuidadores que respondieron «Cuidando al Cuidador»: hasta cinco tarjetas (estrés, apoyo, crianza y castigo físico, barrio y cómo ve el cuidador al hijo), el panel «Señales para cuidar a quienes cuidan» («Ánimo» por grupo; «Autolesión» solo para el municipio y solo en el total), la ruta para adultos, los informes del colegio y de la Secretaría y el resumen de una página en PDF. Los agregados de todas las olas se publican en Supabase con `modulo = "cuidadores"`, auditados antes de subir y sin tocar la lectura de estudiantes. En el despliegue público la página solo aparece con dos llaves: la bandera del equipo (`navegacion.CUIDADORES_PUBLICO`) y el catálogo de textos aprobado.

**Fuera de alcance:** cambiar los textos provisionales (los aprueba el equipo, spec §8), subescalas del APQ y total del estrés parental (libro de códigos), publicar por ola, la capa por colegio de la triangulación en el despliegue del equipo (fase 5, que podrá leer esta corrida), poner `CUIDADORES_PUBLICO = True` (commit del equipo tras aprobar y publicar) y publicar de verdad en Supabase (lo hace el usuario).

**Arquitectura.** Todo lo nuevo vive en **módulos nuevos**, que Streamlit Cloud siempre importa frescos:

| Módulo nuevo | Qué contiene |
|---|---|
| `src/cuidadores/comunidad_catalogo.py` | Textos provisionales de la comunidad (`TEXTOS_APROBADOS = False`, `RUTAS_VALIDADAS = False`): tarjetas, señales del adulto, estado general del colegio, autocuidado de familia, ruta para adultos (`catalog.ruta_adulto`) y avisos. Sin «suicidio» ni teléfonos inventados |
| `src/cuidadores/alertas.py` | Tabla de señales desde los cortes YA suprimidos: «Ánimo» (fila «probable, EPDS ≥ 13») en el total, colegios, grados y celdas; «Autolesión» solo en el total. Estado con `estudiantes.alertas.estado` (solo cifras publicadas). Nunca casos |
| `src/cuidadores/comunidad.py` | `preparar(ac)`: copia del análisis de todas las olas para la comunidad y la publicación: sin autolesión por grupo, sin reparto por ola, con la tabla de señales |
| `src/cuidadores/auditoria.py` | Restas de un paso que dejen 1 a 9 **cuidadores distintos**; cifras que no delatan recalculadas con la puntuación de cuidadores (`supresion.fugas`, con la regla de 3 cuidadores distintos en el marco de niños); autolesión por grupo |
| `src/cuidadores/publicar.py` | Lote agregado (`nivel = "cuidadores"`, marco en `detalle.marco`), guardas de estudiantes + propias, `--ensayo` (sale con 2 si hay hallazgos) y `--publicar-ya` (oculta → resultados → abrir → cerrar solo las de cuidadores; sin señales hasta la aprobación) |
| `src/cuidadores/lectura.py` | Rearma la última corrida publicada de cuidadores (`CuidadoresPublicados`, con la forma de `AnalisisCuidadores`) |
| `src/ui/views/cuidadores_comunidad.py` | Vista de comunidad (funciones puras + Streamlit) y `render_publico` (lo único de cuidadores que carga el despliegue público) |
| `src/ui/views/cuidadores_informe.py` | Informes HTML del colegio y de la Secretaría y resumen de una página (PDF con WeasyPrint o HTML) |
| `scripts/generar_informes_cuidadores.py` | Informes en disco, con la misma auditoría que la publicación (aborta ante un hallazgo) |
| `tests/supabase_falso.py`, `tests/cuidadores_comunidad_datos.py` | Base `obs360` en memoria con los CHECK y la RLS por módulo; datos sintéticos preparados y publicados |

**Reutilización sin tocar estudiantes.** Las tablas de los dos marcos ya pasaron por `estudiantes.supresion.aplicar` en la 4a; la 4b solo **lee** esas tablas (y quita cifras, nunca añade). Se reutilizan `estudiantes.publicar` (`_fila`, `verificar`, `_enmascarar_conteos`, `_cliente`), `estudiantes.alertas.estado`, los colores y el CSS de `estudiantes_alertas` y el formato de `estudiantes_informe`. **Ningún archivo de `src/estudiantes/`, `src/ui/estudiantes.py` ni `src/ui/views/estudiantes_*.py` cambia** (la Task 11 lo comprueba con `git diff` y con el lote real del ensayo de estudiantes, byte a byte).

**Módulos rancios.** Cambian cinco archivos existentes: `src/core/navegacion.py` (función nueva `cuidadores_publico`, que solo usa el propio `menu()`), `main.py` (rama pública de Cuidadores, que usa `nav.PAGINA_CUIDADORES`, que ya existía), `src/ui/cuidadores.py`, `src/ui/views/cuidadores_investigador.py` (conteos enmascarados) y tres pruebas. Con un `navegacion` viejo en memoria la página pública simplemente no aparece hasta el «Reboot app»; nada se cae.

**Tech stack:** Python 3.13 local / 3.14 en Streamlit Cloud, pandas (2.x local, 3.x en 3.14), numpy, scipy, Streamlit (`AppTest`), WeasyPrint (solo en 3.14), pytest y Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-10-06-cuidadores-alertas-triangulacion-design.md`: §5.5 (parte 4b), §4, §5.1, §5.4 (reglas de cifras y estados), §6, §7 y §8.

**Restricciones que no se negocian:**
- **Nada individual.**
  - Nada de ingesta, pipeline ni vista de investigadores en el despliegue público: solo `views/cuidadores_comunidad` y lo que importa (catálogos, `alertas`, `lectura`, `views/cuidadores_informe`).
  - Ningún grupo con menos de 10 **cuidadores distintos**; ninguna proporción con menos de 3 casos o no casos, ni deducible por resta; nunca el número de casos.
  - «Autolesión»: solo para el rol municipio, solo la cifra del total, con la regla de 3 a n − 3. Nunca por colegio, grado ni celda; en el rol colegio queda dentro de un estado general fijo, sin cifra.
  - Familia: un mensaje de autocuidado y la ruta para adultos, sin cifras de las señales y sin nada sobre hacerse daño o la muerte.
  - Nada se publica por ola (ni resultados, ni conteos por ola).
- **Textos fijos y provisionales** (`comunidad_catalogo.TEXTOS_APROBADOS = False`, `RUTAS_VALIDADAS = False`). Nunca los redacta la IA. Nunca «suicidio». Color máximo: naranja. El código no inventa teléfonos.
- **Datos reales.**
  - `../datos_fuente_360` tiene nombres y teléfonos de menores y adultos: solo se leen encabezados y se imprimen conteos y booleanos agregados. Nunca filas ni valores. `Datos_Cuidador_corregido.csv` no se abre.
  - Las pruebas reales se omiten si falta el archivo y solo comparan agregados (`assert n == 0`, nunca una lista).
  - Ningún comando de este plan imprime filas, nombres, teléfonos, seudónimos ni la clave `OBS360_CLAVE_HMAC`. Nunca `cat` de `.streamlit/secrets.toml`.
- **Supabase.** Esta fase no necesita migración (ver «Decisiones»). Nadie publica de verdad en este plan: solo `--ensayo`. La publicación real y `CUIDADORES_PUBLICO = True` son del usuario y del equipo.
- **Git.**
  - La rama `feature/fase4b-cuidadores-comunidad` ya existe (sale de `origin/feature/fase4a-cuidadores` = `main` + fase 4a + fase 5) y ya trae este plan: no se crea ni se cambia de rama.
  - Nunca `git add -A`: siempre los archivos por nombre. Los dos `.docx` sin seguimiento de la raíz no se tocan.
  - No se hace `push` hasta la Task 13 y no se fusiona sin permiso del usuario.
- Cada commit termina con una línea en blanco y `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

**Comandos de prueba** (desde la raíz del repo):
- Python 3.13: `.venv/bin/python -m pytest -q`. Línea base al empezar: **956 passed, 4 skipped**.
- Python 3.14 con WeasyPrint (producción): `"$VENV314/bin/python" -m pytest -q`. Línea base: **960 passed**. Con

  ```bash
  SCRATCH=/private/tmp/claude-501/-Users-joseamorocho-Documents-app-360-observatorio-SaludOrganizacional/73d67104-c128-41eb-b044-923af344a71f/scratchpad
  VENV314="$SCRATCH/venv314"
  ```

  Si ese directorio ya no existe (el scratchpad es de la sesión), se recrea como en la Task 11, Step 1.

---

## Decisiones de diseño (tomadas en este plan; las que necesitan al equipo están en «Preguntas abiertas»)

| Tema | Decisión |
|---|---|
| Qué se publica | El análisis de **todas las olas** preparado (`comunidad.preparar`): la vista de una ola nunca sale de la máquina (`preparar` y `aplanar` la rechazan) |
| Nivel y marco en Supabase | `nivel = "cuidadores"` en todas las filas (el CHECK ya lo admite) y el marco en `detalle.marco` (`"cuidador"` / `"nino"`). Las claves de los dos marcos no se repiten salvo «muestra», y el lector separa por `detalle.marco`. **No hace falta migración**: tablas, CHECK (n ≥ 10, nivel, ^[ECN][0-9a-f]{8}$, sin conteos, estado con cifra) y RLS de la última corrida **por módulo** ya cubren cuidadores |
| Migración | Ninguna nueva. Requisitos: 2026-10-07 y 2026-10-07b aplicadas (última publicada por módulo); 2026-10-07c recomendada antes de la primera corrida (última barrera contra conteos). Se documenta en `supabase/README.md` |
| Señales del adulto | No son una columna nueva: «Ánimo» es la fila «probable (EPDS ≥ 13)» de la familia `EPDS_Total` (cortes anidados con «posible ≥ 10», ya suprimidos en tres partes) y «Autolesión» la familia `EPDS_Autolesion`. `alertas.tabla` solo las lee y les pone el estado de `estudiantes.alertas.estado` (con % y n publicados del grupo y del total); sin % → «Sin estado: cifras pequeñas» |
| Autolesión | `preparar` la quita de toda tabla de colegio, grado y celda (queda solo en el total del marco). Quitar cifras no abre restas nuevas. `auditoria.auditar_solo_total` y el lector la rechazan por grupo |
| Auditoría exacta con solo el total | Con solo el total publicado, `supresion.fugas` no enumera componentes de más de 16 átomos y falla cerrado (el formulario real tiene 17 átomos en el marco de cuidadores): `auditoria.fugas` lo resuelve exacto (lo único deducible es el propio total). Sin esto el ensayo real daba un falso hallazgo en la autolesión |
| Auditoría de restas | `auditoria.auditar_restas` es la de estudiantes contando `nunique(ID_cuidador)`: en el marco de niños un resto de 12 filas puede ser de 3 cuidadores (hermanos). Hay prueba de que la de estudiantes no lo vería |
| Qué no se publica | Comparación por sexo del niño, ítems del APQ y del estrés parental (solo locales), reparto por ola (`muestra["ola"]`, `por_ola`, repetidos entre olas) y los `avisos` de la carga (repiten conteos exactos que en el lote van como «<10») |
| Tarjetas por rol (techo de 5) | Orden `estres, animo, apoyo, crianza, barrio, hijo`. **Colegio y municipio:** estrés, apoyo, crianza, barrio, hijo; «Ánimo» va en el panel y la tarjeta solo vuelve si el panel no se dibujó (como la de muerte en estudiantes). **Familia:** las mismas cinco; nunca «Ánimo» |
| Cifras de las tarjetas | Estrés (PSS) y barrio: media del total, del colegio o del grado (las medias por celda no se publican: la tarjeta no sale en una celda). Ánimo, apoyo (MSPSS familia < 3, con amigos y persona especial en el detalle), crianza (castigo físico, con el grito en el detalle) e hijo (SDQ de padres alto o muy alto): «1 de cada N» con IC; suprimida → «—» y el texto fijo |
| Panel por rol | **Colegio:** «Ánimo» del grupo elegido, grados en «Prioridad» dentro del colegio y el estado general fijo (`ESTADO_GENERAL_COLEGIO`), sin cifra ni nombre de la autolesión. **Municipio:** «Ánimo» con colegios y grados en «Prioridad» y «Autolesión» siempre con la cifra del total y la nota «solo para todo el municipio». **Familia:** «Cuidarse para cuidar» sin cifras |
| Comparar entre grupos | Castigo físico, poco apoyo de la familia, hijo con dificultades altas y, solo para colegio y municipio, ánimo. Nunca autolesión. Familia compara solo por grado |
| Grupos | Unión de los grupos publicables de los dos marcos (base local o subgrupos publicados); «OTRO» y «SIN_DATO» nunca. El grado es el del hijo por quien respondió el cuidador (se dice en pantalla) |
| Estado compartido | Mismas claves que Estudiantes (`estado.ROL`, `estado.COLEGIO`); `?colegio=` se aplica también en Cuidadores con `colegio_de_la_url`, que solo acepta colegios con cifras de cuidadores |
| Navegación pública | Dos llaves y ninguna consulta a la red al arrancar: `navegacion.cuidadores_publico()` = `CUIDADORES_PUBLICO is True` **y** `comunidad_catalogo.TEXTOS_APROBADOS` **y** `RUTAS_VALIDADAS`. El equipo pone `CUIDADORES_PUBLICO = True` en un commit propio **después** de publicar con `--publicar-ya`. Si aun así no hubiera corrida, `render_publico` dice «todavía no tiene resultados publicados» |
| Corte público de `main.py` | Rama `PAGINA_CUIDADORES` antes del `st.stop()` que solo importa `views.cuidadores_comunidad.render_publico`. Se amplía `PROHIBIDOS_EN_COMUNIDAD` (scoring, privacidad, publicar, auditoria, comunidad, seudonimo) |
| Modos completo e investigador | Selector «Vista» como en Estudiantes (`audiencia_por_defecto`: completo → comunidad, investigador → investigador). Fuente: archivo local con clave, o la corrida publicada (despliegue del equipo); `OBS360_FUENTE=supabase` la fuerza. El filtro de ola solo existe en la vista de investigadores con archivo |
| Investigadores desde lo publicado | La vista de la 4a lee un `CuidadoresPublicados` (mismas propiedades) y muestra «<10» tal cual (`conteo_legible`, flujo de la muestra con «—» donde no se puede restar) |
| Informes | Colegio: panel de colegio, tarjetas comparadas con el municipio y tabla por grado dentro del colegio; nunca otro colegio. Secretaría: panel de municipio (con la autolesión del total), tarjetas, «Ánimo» por colegio (estado y %) y tablas por colegio y por grado. Resumen de una página: recuadro compacto + 4 tarjetas + ruta, y cabe en una hoja en el peor caso (14 colegios y 7 grados en «Prioridad») |
| Generador de informes | `scripts/generar_informes_cuidadores.py`, igual que el de estudiantes: con archivo local, `publicar.verificar_restas` antes de escribir; con un hallazgo, código 2 y nada escrito |
| Aviso interno | En el modo completo: «textos pendientes de aprobación» y «ruta pendiente de validación» bajo la ruta. Nunca en público ni en informes |
| Pruebas sin red | `tests/supabase_falso.py` imita las tablas, los CHECK y la RLS (el anónimo no escribe y solo ve la última publicada de cada módulo). Las pruebas que arrancan la página parchean `lectura.disponible` para no tocar el Supabase real |

### Lo que la 4b deja para después

- La capa por colegio de la triangulación en el despliegue del equipo (fase 5) puede leer `cuidadores.lectura.cargar_desde_supabase()`; no se toca aquí.
- Si el equipo cambia los textos, solo cambia `comunidad_catalogo.py` (y las pruebas de redacción siguen valiendo).

---

## Mapa de archivos

| Archivo | Qué cambia |
|---|---|
| `src/cuidadores/comunidad_catalogo.py` (nuevo) | Banderas, `ROLES`, `Mensaje`/`MENSAJES`, `ORDEN_TARJETAS`, `SenalAdulto`/`ALERTAS`, textos del panel, `ruta`, avisos |
| `src/cuidadores/alertas.py` (nuevo) | `INDICADOR_PROBABLE`, `FUENTES`, `SOLO_TOTAL`, `fila_corte`, `ordenar`, `tabla`, `vacia` |
| `src/cuidadores/comunidad.py` (nuevo) | `preparar` |
| `src/cuidadores/auditoria.py` (nuevo) | `auditar_restas`, `fugas`, `auditar_cifras`, `auditar_solo_total`, `auditar` |
| `src/cuidadores/publicar.py` (nuevo) | `aplanar`, `aplanar_ingesta`, `verificar`, `verificar_restas`, `publicar`, `main` |
| `src/cuidadores/lectura.py` (nuevo) | `CuidadoresPublicados`, `id_corrida_vigente`, `reconstruir`, `cargar_desde_supabase` |
| `src/ui/views/cuidadores_comunidad.py` (nuevo) | Tarjetas, panel, comparación, `render_comunidad`, `render_publico` |
| `src/ui/views/cuidadores_informe.py` (nuevo) | `informe_colegio_html`, `informe_secretaria_html`, `informe_una_pagina_html`, `a_pdf` |
| `scripts/generar_informes_cuidadores.py` (nuevo) | Informes con auditoría previa |
| `src/ui/cuidadores.py` | Selector «Vista», corrida publicada sin archivo, `OBS360_FUENTE` |
| `src/ui/views/cuidadores_investigador.py` | `conteo_legible` y flujo de la muestra con conteos «<10» |
| `src/core/navegacion.py` | `cuidadores_publico()`; `menu()` la usa |
| `main.py` | Rama pública `PAGINA_CUIDADORES` → `render_publico` |
| `src/cuidadores/__init__.py` | Docstring con los módulos de la 4b |
| `tests/supabase_falso.py`, `tests/cuidadores_comunidad_datos.py` (nuevos) | Ayudas de prueba |
| `tests/test_cuidadores_{comunidad_catalogo,alertas,auditoria,publicar,lectura,comunidad,informe,publicar_reales}.py` (nuevos) | Pruebas |
| `tests/test_cuidadores_pagina.py`, `tests/test_navegacion.py`, `tests/test_modo_despliegue.py` | Vista, fuente publicada, doble llave y corte público |
| `DESPLIEGUE.md`, `ARCHITECTURE.md`, `supabase/README.md` | Documentación |

**Lo que no cambia:** todo `src/estudiantes/`, `src/ui/estudiantes.py`, `src/ui/views/estudiantes_*.py`, `src/core/{colegios,modo,rutas,texto,seudonimo}.py`, `src/cuidadores/{catalog,ingest,scoring,privacidad,pipeline}.py`, `src/triangulacion/`, `supabase/*.sql`.

---

### Task 0: Línea base y foto del ensayo de estudiantes

**Files:** ninguno del repositorio.

- [ ] **Step 1: Comprobar la rama (ya existe; no se crea)**

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
git branch --show-current          # → feature/fase4b-cuidadores-comunidad
git log --oneline -2               # → «docs(plan): fase 4b · cuidadores para la comunidad» sobre cd0dedb
git status --short                 # solo los dos .docx sin seguimiento; no se tocan
grep -c "^OBS360_CLAVE_HMAC" .streamlit/secrets.toml   # → 1 (la clave local de la 4a; nunca se muestra)
```

Si la rama no es la indicada, el árbol tiene cambios propios o falta la clave, parar y avisar al usuario.

- [ ] **Step 2: Línea base**

Run: `.venv/bin/python -m pytest -q`
Expected: `956 passed, 4 skipped`.

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: `960 passed`. Anotar los totales para el PR.

- [ ] **Step 3: Foto del ensayo de estudiantes, fuera del repositorio**

Sirve para probar en la Task 11 que estudiantes no cambia. Solo agregados.

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$SCRATCH/obs360_lote_antes_4b.json" > /dev/null
echo "código de salida: $?"
```
Expected: `código de salida: 0`. (La versión del lote lleva la fecha: la Task 11 debe correr el mismo día; si no, se repite este paso antes de empezar las tareas.)

Sin commit.

---

### Task 1: Textos de la comunidad (catálogo provisional)

**Files:**
- Create: `src/cuidadores/comunidad_catalogo.py`
- Create: `tests/test_cuidadores_comunidad_catalogo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_comunidad_catalogo.py`:

```python
"""Cuidadores 360 · textos de la comunidad (fase 4b, spec §5.5, §6 y §8)."""
import re
from dataclasses import fields, is_dataclass

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.estudiantes import catalog as cat_est


def _textos(objeto) -> list[str]:
    """Todas las cadenas de un valor del catálogo (dataclasses, dicts, tuplas)."""
    if isinstance(objeto, str):
        return [objeto]
    if is_dataclass(objeto) and not isinstance(objeto, type):
        return [t for f in fields(objeto) for t in _textos(getattr(objeto, f.name))]
    if isinstance(objeto, dict):
        return [t for v in objeto.values() for t in _textos(v)]
    if isinstance(objeto, (list, tuple)):
        return [t for v in objeto for t in _textos(v)]
    return []


def _todo() -> list[str]:
    return [t for nombre in dir(cc) if not nombre.startswith("_")
            for t in _textos(getattr(cc, nombre))]


def test_provisional_hasta_la_aprobacion():
    assert cc.TEXTOS_APROBADOS is False and cc.RUTAS_VALIDADAS is False


def test_mismos_roles_que_estudiantes():
    assert cc.ROLES == cat_est.ROLES


def test_una_tarjeta_por_cada_una_de_la_spec_en_su_orden():
    assert cc.ORDEN_TARJETAS == tuple(k for k, _ in cat.TARJETAS_4B)
    assert set(cc.MENSAJES) == set(cc.ORDEN_TARJETAS)
    assert cc.MAX_TARJETAS == 5
    for clave, titulo in cat.TARJETAS_4B:
        assert cc.MENSAJES[clave].titulo == titulo


def test_cada_rol_tiene_accion_en_las_tarjetas_que_ve():
    for clave, m in cc.MENSAJES.items():
        for rol in m.solo_roles:
            assert m.accion.get(rol), (clave, rol)


def test_familia_no_ve_la_tarjeta_de_animo():
    assert "familia" not in cc.MENSAJES["animo"].solo_roles
    assert set(cc.MENSAJES["animo"].solo_roles) == {"colegio", "municipio"}


def test_autolesion_solo_para_el_municipio_y_animo_nunca_para_familia():
    assert cc.ALERTAS[cat.AUTOLESION].roles == ("municipio",)
    assert set(cc.ALERTAS[cat.ANIMO].roles) == {"colegio", "municipio"}
    assert set(cc.ALERTAS) == {cat.ANIMO, cat.AUTOLESION}


def test_nunca_suicidio_en_ningun_texto():
    textos = _todo()
    assert len(textos) > 40
    for texto in textos:
        assert "suicid" not in texto.lower()


def test_lo_que_lee_familia_no_habla_de_hacerse_dano_ni_de_la_muerte():
    familia = [cc.AUTOCUIDADO_FAMILIA, cc.TITULO_AUTOCUIDADO,
               *[m.accion.get("familia", "") for m in cc.MENSAJES.values()],
               *[m.significa for m in cc.MENSAJES.values() if "familia" in m.solo_roles],
               *[m.etiqueta for m in cc.MENSAJES.values() if "familia" in m.solo_roles]]
    for texto in familia:
        for palabra in ("daño", "autoles", "muerte", "morir", "suicid"):
            assert palabra not in texto.lower(), (palabra, texto[:40])


def test_la_ruta_es_la_de_adultos_y_no_inventa_telefonos():
    for rol in cc.ROLES:
        assert cc.ruta(rol) == cat.ruta_adulto(rol)
        for nombre, detalle in cc.ruta(rol):
            assert not re.search(r"\d{3,}", nombre + detalle)


def test_ningun_texto_trae_numeros_de_telefono():
    for texto in _todo():
        assert not re.search(r"\b\d{7,}\b", texto)


def test_el_catalogo_no_importa_ingesta_ni_pipeline():
    import inspect
    fuente = inspect.getsource(cc)
    for prohibido in ("ingest", "pipeline", "scoring", "privacidad", "streamlit"):
        assert f"import {prohibido}" not in fuente and f"cuidadores.{prohibido}" not in fuente
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_comunidad_catalogo.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.cuidadores.comunidad_catalogo'`.

- [ ] **Step 3: Implementar**

`src/cuidadores/comunidad_catalogo.py`:

```python
"""
Textos de la vista de comunidad de Cuidadores 360 — Observatorio 360 (fase 4b).

Todo lo que leen colegios, familias y el municipio en la página de Cuidadores,
en sus informes y en el resumen de una página: las seis tarjetas, las señales
del adulto («Ánimo» y «Autolesión»), el mensaje de autocuidado para familias,
la ruta para adultos y los avisos (spec del 6-oct-2026, §5.5, §6 y §8).

PROVISIONAL. Los textos y las rutas los aprueba el equipo investigador (spec
§8, puntos 1, 4 y 5). Mientras `TEXTOS_APROBADOS` o `RUTAS_VALIDADAS` sean
False:
  · la página de Cuidadores no aparece en el despliegue público
    (`navegacion.cuidadores_publico`);
  · `publicar --publicar-ya` no sube las filas de las señales del adulto;
  · en el modo completo la vista muestra el aviso interno `TEXTOS_PENDIENTES`.

Reglas:
  · Textos fijos. Nunca los redacta la IA en tiempo de ejecución.
  · Nunca «suicidio»: «señales», «no es un diagnóstico», «dónde mirar primero».
  · El código no inventa teléfonos: la ruta es `catalog.ruta_adulto` (la de
    adultos de la fase 3) hasta que el equipo confirme las líneas de Chía.
  · Familia no lee nada sobre hacerse daño ni cifras de las señales del adulto.
  · Color máximo: naranja (lo fija la vista, con los colores de estudiantes).
  · Este módulo no importa nada de ingesta, pipeline ni vistas: lo lee también
    el despliegue público y `core.navegacion`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.cuidadores import catalog as cat

TEXTOS_APROBADOS = False
RUTAS_VALIDADAS = False

ROLES = {
    "colegio": "Rector, docente u orientación escolar",
    "familia": "Madre, padre o cuidador",
    "municipio": "Funcionario del municipio",
}
TODOS_LOS_ROLES = ("colegio", "familia", "municipio")


# ── Tarjetas (spec §5.5) ────────────────────────────────────────────────────
@dataclass(frozen=True)
class Mensaje:
    titulo: str
    etiqueta: str                 # completa la cifra («1 de cada 4 …», «17 de 40 …»)
    significa: str
    accion: dict = field(default_factory=dict)          # rol → qué hacer
    solo_roles: tuple[str, ...] = TODOS_LOS_ROLES


MENSAJES: dict[str, Mensaje] = {
    "estres": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["estres"],
        etiqueta="puntos de 40 en estrés percibido, en promedio",
        significa=("Mide cuánto sienten los cuidadores que la vida diaria se les sale de "
                   "las manos en el último mes (PSS-10). No mide solo el estrés de criar "
                   "y no tiene un punto de corte clínico: se lee comparado con el municipio."),
        accion={
            "colegio": ("Programar los encuentros con familias en horarios posibles para "
                        "quienes trabajan y ofrecer espacios cortos de pausa y apoyo entre "
                        "cuidadores."),
            "familia": ("Buscar momentos de descanso y repartir las tareas de la casa y del "
                        "cuidado. El estrés se lleva mejor acompañado."),
            "municipio": ("Articular programas de apoyo a cuidadores (respiro, escuelas de "
                          "familia) con la oferta de bienestar del municipio."),
        }),
    "animo": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["animo"],
        etiqueta="cuidadores muestran señales de ánimo bajo",
        significa=("Es un tamizaje con la escala de Edimburgo (EPDS), no un diagnóstico: "
                   "indica cuántos cuidadores podrían beneficiarse de una conversación con un "
                   "profesional."),
        accion={
            "colegio": ("Incluir en las reuniones con familias un momento sobre el cuidado de "
                        "quien cuida y dar a conocer la ruta para adultos."),
            "municipio": ("Acercar la oferta de salud mental para adultos a las comunidades "
                          "educativas."),
        },
        solo_roles=("colegio", "municipio")),
    "apoyo": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["apoyo"],
        etiqueta="cuidadores sienten poco apoyo de su familia",
        significa=("Apoyo que el cuidador siente de su familia, de sus amigos y de una "
                   "persona especial (media por debajo de 3 de 5 en cada fuente)."),
        accion={
            "colegio": ("Crear redes entre familias del mismo curso y espacios donde los "
                        "cuidadores se conozcan y se apoyen."),
            "familia": ("Pedir y aceptar ayuda: un familiar, un vecino o las familias del curso "
                        "pueden compartir tareas del cuidado."),
            "municipio": ("Fortalecer las redes comunitarias de apoyo a familias y los "
                          "programas de cuidado de cuidadores."),
        }),
    "crianza": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["crianza"],
        etiqueta=("cuidadores usan alguna forma de castigo físico a veces o más "
                  "(nalgadas, cachetadas o correa)"),
        significa=("Mientras llega el libro de códigos del cuestionario de crianza no se mide "
                   "la crianza positiva: esta tarjeta solo describe el castigo físico y el "
                   "grito. La Ley 2089 de 2021 prohíbe el castigo físico; aquí se lee como una "
                   "invitación a acompañar a las familias, no a señalarlas."),
        accion={
            "colegio": ("Ofrecer a las familias talleres de crianza con alternativas al "
                        "castigo (acuerdos, consecuencias, reconocimiento), sin señalar a "
                        "nadie."),
            "familia": ("Cuando la paciencia se acaba, tomar una pausa antes de corregir. Hay "
                        "formas de poner límites sin golpes ni gritos; la orientación del "
                        "colegio puede acompañar."),
            "municipio": ("Fortalecer y difundir en los colegios los programas de crianza sin "
                          "violencia (Ley 2089 de 2021)."),
        }),
    "barrio": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["barrio"],
        etiqueta="puntos de 10 en el índice de riesgo del barrio, en promedio",
        significa=("Suma de cinco preguntas sobre drogas, delincuencia, riñas, violencia grave "
                   "y pandillas cerca de casa. Más alto quiere decir más riesgo."),
        accion={
            "colegio": ("Revisar con las familias los trayectos entre la casa y el colegio y "
                        "los espacios seguros después de clase."),
            "familia": ("Acordar con los hijos rutas y horarios seguros y saber dónde y con "
                        "quién están."),
            "municipio": ("Llevar la oferta de convivencia, seguridad y uso del tiempo libre a "
                          "los barrios con el índice más alto."),
        }),
    "hijo": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["hijo"],
        etiqueta="niños con dificultades altas o muy altas según su cuidador",
        significa=("Cuestionario SDQ en su versión para padres: es lo que el cuidador observa "
                   "en casa y puede ser distinto de lo que dice el propio niño."),
        accion={
            "colegio": ("Conversar con las familias sobre lo que ven en casa y lo que se ve en "
                        "el aula, para acompañar al niño entre las dos partes."),
            "familia": ("Si nota tristeza, miedos, peleas o inquietud que no pasan, hablar con "
                        "la orientación del colegio."),
            "municipio": ("Orientar la oferta de salud mental infantil hacia los grupos donde "
                          "más cuidadores reportan dificultades."),
        }),
}
# Orden en que se intentan; se muestran las cinco primeras con cifra que el rol puede ver.
ORDEN_TARJETAS = tuple(k for k, _ in cat.TARJETAS_4B)
MAX_TARJETAS = 5

# ── Señales del adulto (spec §5.5) ──────────────────────────────────────────
TITULO_PANEL = "Señales para cuidar a quienes cuidan"


@dataclass(frozen=True)
class SenalAdulto:
    clave: str
    nombre: str
    nombre_corto: str
    senal: str                          # para la frase de la cifra
    que_es: str
    que_hacer: dict = field(default_factory=dict)   # rol → texto
    roles: tuple[str, ...] = ()


ALERTAS: dict[str, SenalAdulto] = {
    cat.ANIMO: SenalAdulto(
        clave=cat.ANIMO,
        nombre="Señales de ánimo bajo en los cuidadores",
        nombre_corto="Ánimo",
        senal="señales de ánimo bajo",
        que_es=(f"Cuidadores con {cat.EPDS_PROBABLE} puntos o más en la escala de Edimburgo "
                "(EPDS), que indica un ánimo bajo probable. Es una señal de grupo para mirar "
                "con atención, no un diagnóstico."),
        que_hacer={
            "colegio": ("Incluir en las reuniones con familias un momento sobre el cuidado de "
                        "quien cuida y dar a conocer la ruta para adultos. No abordar a ningún "
                        "cuidador a partir de este dato."),
            "municipio": ("Llevar la oferta de salud mental para adultos (atención primaria, "
                          "grupos de apoyo) a las comunidades de los colegios en «Prioridad» y "
                          "verificar que tenga capacidad."),
        },
        roles=("colegio", "municipio")),
    cat.AUTOLESION: SenalAdulto(
        clave=cat.AUTOLESION,
        nombre="Pensamientos de hacerse daño",
        nombre_corto="Hacerse daño",
        senal="pensamientos de hacerse daño",
        que_es=("Cuidadores que respondieron haber pensado alguna vez en hacerse daño en los "
                "últimos días (pregunta 10 de la EPDS). Es una señal para garantizar la ruta, "
                "no un diagnóstico."),
        que_hacer={
            "municipio": ("Garantizar que la ruta de salud mental para adultos tenga capacidad "
                          "de respuesta y que los colegios sepan cómo orientar a un cuidador."),
        },
        roles=("municipio",)),
}
PLANTILLA_CIFRA = "{fraccion} cuidadores {verbo} {senal}."
NOTA_SOLO_MUNICIPIO = ("Esta señal se muestra solo para todo el municipio, nunca por colegio "
                       "ni por grado.")
# Rol colegio: la autolesión no tiene cifra ni estado propio; queda dentro de este
# estado general, fijo, sin cifras (spec §5.5).
ESTADO_GENERAL_COLEGIO = (
    "Cuidar a quien cuida también es parte de la ruta. Si un cuidador cuenta que ha pensado en "
    "hacerse daño, escucharlo sin juzgar y orientarlo ese mismo día a la ruta para adultos.")
# Rol familia: sin cifras y sin nada sobre hacerse daño (spec §5.5 y §6).
TITULO_AUTOCUIDADO = "Cuidarse para cuidar"
AUTOCUIDADO_FAMILIA = (
    "Criar cansa. Sentirse triste, agotado o sin ganas durante varios días seguidos no es una "
    "falla: es una señal para pedir apoyo. Hablar con alguien de confianza, descansar y buscar "
    "a un profesional ayuda. Si el malestar no pasa o pesa demasiado, la ruta para adultos "
    "está abajo.")
CIFRAS_PEQUENAS = ("En este grupo las cifras son muy pequeñas para mostrarse sin riesgo de "
                   "identificar a alguien; la ruta sigue aplicando.")
NOTA_TABLA = ("Porcentaje del colegio con señales y su margen de error. El número de "
              "cuidadores con señales no se publica nunca.")

# ── Ruta, avisos y textos de la página ──────────────────────────────────────
TITULO_RUTA = "Si un cuidador necesita ayuda"


def ruta(rol: str) -> list[tuple[str, str]]:
    """Ruta para adultos del rol: la de `catalog.ruta_adulto` (sin teléfonos inventados)."""
    return list(cat.ruta_adulto(rol))


AVISO_TAMIZAJE = ("Estos resultados son un tamizaje de grupo sobre los cuidadores que "
                  "respondieron, no un diagnóstico de nadie.")
AVISO_EPDS = ("La escala de ánimo (EPDS) se creó para el periodo después del parto; aquí se "
              "usa como tamizaje del ánimo de madres, padres y otros cuidadores.")
AVISO_APOYO = ("El apoyo se pregunta por fuente (familia, amigos, una persona especial) con "
               "preguntas distintas de las de los estudiantes: no se comparan directamente.")
AVISO_MINIMO = (f"Ningún grupo con menos de {cat.MIN_GROUP_N} cuidadores distintos se muestra. "
                "El grado es el del hijo o la hija por quien respondió el cuidador.")
AVISO_SIN_OLAS = ("Las cifras reúnen todas las olas de la encuesta (2025 y 2026); no se "
                  "publican por ola.")
TEXTOS_PENDIENTES = ("Aviso interno: los textos y la ruta de esta página están pendientes de "
                     "aprobación del equipo. Solo se ve en el modo completo.")
NO_PUBLICADO = ("Cuidadores 360 todavía no tiene resultados publicados. La página mostrará las "
                "cifras de los cuidadores cuando el equipo apruebe y publique una corrida.")
SIN_SUBGRUPO = (f"Este grupo no tiene cifras publicadas: no llega a {cat.MIN_GROUP_N} "
                "cuidadores distintos.")
```

- [ ] **Step 4: Correr las pruebas**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_comunidad_catalogo.py -q`
Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/cuidadores/comunidad_catalogo.py tests/test_cuidadores_comunidad_catalogo.py
git commit -m "feat(cuidadores): textos provisionales de la vista de comunidad

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Señales del adulto por grupo y copia para la comunidad

**Files:**
- Create: `src/cuidadores/alertas.py`
- Create: `src/cuidadores/comunidad.py`
- Create: `tests/cuidadores_comunidad_datos.py`
- Create: `tests/test_cuidadores_alertas.py`

- [ ] **Step 1: La ayuda de datos de prueba**

`tests/cuidadores_comunidad_datos.py` (la usan las Tasks 2 a 9; `publicado()` importa `publicar`, `lectura` y `supabase_falso` solo al llamarse, en las Tasks 4 y 5):

```python
"""
Datos de prueba de la fase 4b: el análisis sintético preparado para la comunidad,
su corrida publicada en una base falsa y una tabla de señales con todos los estados.

Todo sale de `cuidadores_sinteticos` (con sus centinelas de nombres y teléfono).
Las funciones devuelven objetos NUEVOS en cada llamada (copias): una prueba que
los modifique no afecta a otra.
"""
from __future__ import annotations

import copy
import functools

import pandas as pd

from src.cuidadores import alertas, comunidad, ingest, pipeline
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()
P, R, S, T = alertas.PRIORIDAD, alertas.REFERENCIA, alertas.SIN_ESTADO, alertas.PRESENTE


@functools.lru_cache(maxsize=1)
def _analisis():
    return pipeline.analizar(ingest.cargar(cs.formulario(), k=K), n_boot=20)


def analisis():
    """El `AnalisisCuidadores` del pipeline (todas las olas), sin preparar."""
    return copy.deepcopy(_analisis())


@functools.lru_cache(maxsize=1)
def _preparado():
    return comunidad.preparar(_analisis())


def preparado():
    return copy.deepcopy(_preparado())


def publicado(aprobado: bool = True):
    """(cuidadores publicados y leídos con el rol anónimo, base falsa).

    `aprobado=True` simula textos y ruta aprobados (si no, `--publicar-ya`
    omite las filas de señales). Se restablecen al salir.
    """
    from src.cuidadores import comunidad_catalogo as cc
    from src.cuidadores import lectura, publicar
    from tests.supabase_falso import BaseFalsa
    base = BaseFalsa()
    antes = (cc.TEXTOS_APROBADOS, cc.RUTAS_VALIDADAS)
    cc.TEXTOS_APROBADOS = cc.RUTAS_VALIDADAS = aprobado
    try:
        publicar.publicar(preparado(), publicar_ya=True, cliente=base.cliente())
    finally:
        cc.TEXTOS_APROBADOS, cc.RUTAS_VALIDADAS = antes
    leido, _ = lectura.cargar_desde_supabase(base.cliente(anonimo=True))
    return leido, base


def _r(alerta, agrupacion, grupo, pct, estado, n=30):
    con = pct is not None
    return dict(alerta=alerta, agrupacion=agrupacion, grupo=grupo, n=n, pct=pct,
                ic_inf=pct - 8 if con else None, ic_sup=pct + 8 if con else None, estado=estado)


def tabla_senales() -> pd.DataFrame:
    """Señales con todos los estados: prioridad, presente, sin estado y referencia."""
    filas = [
        _r("animo", "total", "Todos", 25.0, R, n=90),
        _r("animo", "Colegio", "LauV", 40.0, P), _r("animo", "Colegio", "JJC", 20.0, T),
        _r("animo", "Colegio", "SJMEB", None, S, n=14),
        _r("animo", "Grado", "Quinto", 38.0, P, n=13), _r("animo", "Grado", "Sexto", 22.0, T),
        _r("animo", "Colegio×Grado", "LauV|Quinto", 45.0, P, n=13),
        _r("animo", "Colegio×Grado", "LauV|Sexto", None, S, n=12),
        _r("autolesion", "total", "Todos", 11.0, R, n=90),
    ]
    return alertas.ordenar(pd.DataFrame(filas, columns=alertas.COLUMNAS_TABLA))


def con_senales(ac, tabla: pd.DataFrame | None = None):
    """Copia de `ac` cuyo marco de cuidadores trae `tabla` (por defecto, `tabla_senales`)."""
    out = copy.copy(ac)
    out.cuidador = copy.copy(ac.cuidador)
    out.cuidador.alertas = tabla_senales() if tabla is None else tabla
    return out
```

- [ ] **Step 2: Escribir las pruebas que fallan**

`tests/test_cuidadores_alertas.py`:

```python
"""Cuidadores 360 · señales del adulto por grupo y preparación para la comunidad (fase 4b)."""
import pandas as pd
import pytest

from src.cuidadores import alertas, comunidad, scoring
from src.cuidadores import catalog as cat
from src.estudiantes import alertas as al_est
from src.estudiantes import supresion
from tests import cuidadores_comunidad_datos as datos


@pytest.fixture(scope="module")
def ac():
    return datos.preparado()


def test_el_indicador_de_animo_es_la_fila_probable_de_la_epds():
    d = pd.DataFrame({"EPDS_Total": [5, 12, 14, 20], "EPDS_Autolesion": [0, 1, 0, 1]})
    t = scoring.sobre_cortes_cuidador(d)
    assert alertas.INDICADOR_PROBABLE in set(t["indicador"])
    assert alertas.fila_corte(t, cat.ANIMO)["n"] == 4


def test_la_autolesion_solo_tiene_fila_del_total(ac):
    t = ac.cuidador.alertas
    auto = t[t["alerta"] == cat.AUTOLESION]
    assert len(auto) == 1 and auto.iloc[0]["agrupacion"] == alertas.TOTAL


def test_animo_por_colegio_grado_y_celda(ac):
    t = ac.cuidador.alertas
    animo = t[t["alerta"] == cat.ANIMO]
    assert set(animo["agrupacion"]) == {alertas.TOTAL, "Colegio", "Grado", "Colegio×Grado"}
    assert set(animo.loc[animo["agrupacion"] == "Colegio", "grupo"]) == \
        set(ac.cuidador.subgrupos["Colegio"])


def test_sin_casos_nunca(ac):
    assert "casos" not in ac.cuidador.alertas.columns
    assert list(ac.cuidador.alertas.columns) == alertas.COLUMNAS_TABLA


def test_el_porcentaje_es_el_de_los_cortes_ya_suprimidos(ac):
    t = ac.cuidador.alertas
    for _, f in t.iterrows():
        if f["agrupacion"] == alertas.TOTAL:
            fuente = ac.cuidador
        else:
            fuente = ac.cuidador.subgrupos[f["agrupacion"]][f["grupo"]]
        esperado = alertas.fila_corte(fuente.cortes, f["alerta"])
        assert esperado["n"] == f["n"]
        assert (esperado["pct"] is None) == pd.isna(f["pct"])


def test_el_estado_solo_donde_hay_porcentaje(ac):
    t = ac.cuidador.alertas
    sin = t[t["pct"].isna()]
    assert (sin["estado"] == alertas.SIN_ESTADO).all()
    con = t[t["pct"].notna() & (t["agrupacion"] != alertas.TOTAL)]
    total = t[(t["agrupacion"] == alertas.TOTAL) & (t["alerta"] == cat.ANIMO)].iloc[0]
    for _, f in con.iterrows():
        assert f["estado"] == al_est.estado(f["pct"], f["n"], total["pct"], total["n"])


def test_toda_cifra_publicada_cumple_la_regla_de_tres():
    """Recalculado desde los datos: cada % de ánimo publicado tiene de 3 a n − 3 casos."""
    a = datos.analisis().cuidador
    prep = comunidad.preparar(datos.analisis()).cuidador
    for _, f in prep.alertas.dropna(subset=["pct"]).iterrows():
        if f["agrupacion"] == alertas.TOTAL:
            filas = a.datos.loc[a.base.nivel]
        elif f["agrupacion"] == "Colegio×Grado":
            filas = a.datos.loc[a.base.celdas[f["grupo"]]]
        else:
            filas = a.datos.loc[getattr(a.base, {"Colegio": "colegios",
                                                 "Grado": "grados"}[f["agrupacion"]])[f["grupo"]]]
        col = cat.ALERTAS[f["alerta"]].columna
        v = filas[col].dropna()
        assert supresion.proporcion_publicable(int(v.sum()), len(v))


def test_preparar_no_toca_el_analisis_original():
    original = datos.analisis()
    claves = {g: set(s.cortes["clave"]) for g, s in original.cuidador.subgrupos["Colegio"].items()}
    comunidad.preparar(original)
    for g, s in original.cuidador.subgrupos["Colegio"].items():
        assert set(s.cortes["clave"]) == claves[g]
    assert any("EPDS_Autolesion" in c for c in claves.values())


def test_preparar_quita_la_autolesion_de_todo_grupo_y_la_ola_de_la_muestra(ac):
    for a in ac.marcos.values():
        assert "ola" not in a.muestra
        for grupos in a.subgrupos.values():
            for s in grupos.values():
                assert "EPDS_Autolesion" not in set(s.cortes["clave"])
    assert "EPDS_Autolesion" in set(ac.cuidador.cortes["clave"])
    assert ac.items_apq.empty and ac.items_estres.empty


def test_preparar_rechaza_la_vista_de_una_ola():
    a = datos.analisis()
    a.ola = "2026"
    with pytest.raises(ValueError):
        comunidad.preparar(a)


def test_el_orden_es_canonico():
    t = datos.tabla_senales()
    assert list(t["alerta"]).index(cat.AUTOLESION) == len(t) - 1
    grados = list(t.loc[(t["alerta"] == cat.ANIMO) & (t["agrupacion"] == "Grado"), "grupo"])
    assert grados == ["Quinto", "Sexto"]
```

- [ ] **Step 3: Correrlas y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_alertas.py -q`
Expected: FAIL con `ImportError` (`cannot import name 'alertas' from 'src.cuidadores'`).

- [ ] **Step 4: Implementar las señales**

`src/cuidadores/alertas.py`:

```python
"""
Señales del adulto de Cuidadores 360 — funciones puras (spec 6-oct-2026, §5.4 y §5.5).

Las dos señales ya existen como proporciones del marco de cuidadores, calculadas
y SUPRIMIDAS por el pipeline (`estudiantes.supresion.aplicar`, contando
cuidadores distintos):
  · «Ánimo»: la fila «probable (EPDS ≥ 13)» de la familia `EPDS_Total` de
    `scoring.sobre_cortes_cuidador` (cortes anidados con «posible ≥ 10»).
  · «Autolesión»: la familia `EPDS_Autolesion` (ítem 10 distinto de «No, nunca»).

Este módulo no calcula nada nuevo: `tabla(a)` lee esas filas ya suprimidas del
nivel y de los subgrupos y les pone el estado con `estudiantes.alertas.estado`,
que solo mira cifras publicadas (% y n del grupo y del total). Así:
  · nunca hay conteo de casos;
  · el porcentaje solo existe donde la supresión lo dejó (3 ≤ casos ≤ n − 3,
    también por resta) y, si no, el estado es «sin estado»;
  · la autolesión solo tiene la fila del total: nunca por colegio, grado ni
    celda (spec §5.5).

Es puro y liviano (no importa ingesta ni pipeline): lo usan la vista de
comunidad, los informes, la publicación y la lectura.
"""
from __future__ import annotations

import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import alertas as al_est
from src.estudiantes import alertas_catalogo as ac_est
from src.estudiantes import privacidad

TOTAL = al_est.TOTAL
TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
AGRUPACIONES = ("Colegio", "Grado", CRUCE)
COLUMNAS_TABLA = list(al_est.COLUMNAS_TABLA)

# Fila de `cortes` de la que sale cada señal: (clave, indicador o None si es la única).
INDICADOR_PROBABLE = f"Ánimo: probable (EPDS ≥ {cat.EPDS_PROBABLE})"
FUENTES = {cat.ANIMO: ("EPDS_Total", INDICADOR_PROBABLE),
           cat.AUTOLESION: ("EPDS_Autolesion", None)}
# Señales y claves de `cortes` que solo existen en el total del marco.
SOLO_TOTAL = (cat.AUTOLESION,)
CLAVES_SOLO_TOTAL = ("EPDS_Autolesion",)

# Estados: los mismos de estudiantes (mismos colores y textos de estado).
PRIORIDAD, PRESENTE = ac_est.PRIORIDAD, ac_est.PRESENTE
REFERENCIA, SIN_ESTADO = ac_est.REFERENCIA, ac_est.SIN_ESTADO


def _vacio(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or pd.isna(v)


def _num(v):
    return None if _vacio(v) else float(v)


def fila_corte(t, alerta: str) -> dict | None:
    """{n, pct, ic_inf, ic_sup} de la señal en una tabla `cortes`; None si no está."""
    if not isinstance(t, pd.DataFrame) or t.empty or "clave" not in t.columns:
        return None
    clave, indicador = FUENTES[alerta]
    sel = t[t["clave"].astype(str) == clave]
    if indicador is not None and "indicador" in sel.columns:
        sel = sel[sel["indicador"].astype(str) == indicador]
    if sel.empty or _vacio(sel.iloc[0]["n"]):
        return None
    f = sel.iloc[0]
    return dict(n=int(f["n"]), pct=_num(f["pct"]), ic_inf=_num(f.get("ic_inf")),
                ic_sup=_num(f.get("ic_sup")))


def _orden(alerta: str, agrupacion: str, grupo: str) -> tuple:
    grados = list(cat.GRADOS_ESTUDIO)

    def pos(g):
        return (grados.index(g) if g in grados else 99, str(g))
    orden_alerta = list(FUENTES).index(alerta) if alerta in FUENTES else 99
    if agrupacion == TOTAL:
        return (orden_alerta, 0, (0, ""), (0, ""))
    if agrupacion == "Colegio":
        return (orden_alerta, 1, (0, str(grupo)), (0, ""))
    if agrupacion == "Grado":
        return (orden_alerta, 2, pos(grupo), (0, ""))
    colegio, grado = privacidad.partir_celda(grupo)
    return (orden_alerta, 3, (0, colegio), pos(grado))


def ordenar(t: pd.DataFrame) -> pd.DataFrame:
    if t is None or len(t) == 0:
        return pd.DataFrame(columns=COLUMNAS_TABLA)
    claves = [_orden(a, g, str(x)) for a, g, x in zip(t["alerta"], t["agrupacion"], t["grupo"])]
    posiciones = sorted(range(len(t)), key=lambda i: claves[i])
    return t.iloc[posiciones].reset_index(drop=True)[COLUMNAS_TABLA]


def tabla(a) -> pd.DataFrame:
    """Una fila por señal y grupo del marco de cuidadores, sin casos, nunca.

    `a` es el `Analisis` del marco de cuidadores YA suprimido. La autolesión
    solo lleva la fila del total. El estado sale de `estudiantes.alertas.estado`
    con el % y el n publicados del grupo y del total.
    """
    filas: list[dict] = []
    ref: dict[str, tuple] = {}
    for alerta in FUENTES:
        f = fila_corte(getattr(a, "cortes", None), alerta)
        if f is None or f["n"] < cat.MIN_GROUP_N:
            continue
        ref[alerta] = (f["pct"], f["n"])
        filas.append(dict(alerta=alerta, agrupacion=TOTAL, grupo=TODOS, n=f["n"],
                          pct=f["pct"] if f["pct"] is not None else None,
                          ic_inf=f["ic_inf"] if f["pct"] is not None else None,
                          ic_sup=f["ic_sup"] if f["pct"] is not None else None,
                          estado=al_est.estado_total(f["pct"])))
    subgrupos = getattr(a, "subgrupos", None) or {}
    for agrupacion in AGRUPACIONES:
        for grupo, s in (subgrupos.get(agrupacion) or {}).items():
            for alerta in ref:
                if alerta in SOLO_TOTAL:
                    continue
                f = fila_corte(getattr(s, "cortes", None), alerta)
                if f is None or f["n"] < cat.MIN_GROUP_N:
                    continue
                pct_total, n_total = ref[alerta]
                con_cifra = f["pct"] is not None
                filas.append(dict(alerta=alerta, agrupacion=agrupacion, grupo=str(grupo),
                                  n=f["n"], pct=f["pct"] if con_cifra else None,
                                  ic_inf=f["ic_inf"] if con_cifra else None,
                                  ic_sup=f["ic_sup"] if con_cifra else None,
                                  estado=al_est.estado(f["pct"], f["n"], pct_total, n_total)))
    return ordenar(pd.DataFrame(filas, columns=COLUMNAS_TABLA))


def vacia() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS_TABLA)
```

- [ ] **Step 5: Implementar la copia para la comunidad**

`src/cuidadores/comunidad.py`:

```python
"""
Lo que la comunidad ve y lo que se publica de Cuidadores 360 (fase 4b).

`preparar(ac)` toma el `AnalisisCuidadores` del pipeline (todas las olas) y
devuelve una COPIA lista para la vista de comunidad, los informes y la
publicación. El análisis original (el de la vista de investigadores) no cambia.

Qué cambia en la copia:
  · La autolesión (`EPDS_Autolesion`) sale de las tablas de cada colegio,
    grado y celda: solo queda en el total del marco (spec §5.5).
  · La muestra pierde el reparto por ola: nada se publica por ola.
  · El marco de cuidadores lleva `alertas`, la tabla de las señales del adulto
    (`cuidadores.alertas.tabla`), sin casos.
  · Los ítems del APQ y del estrés parental, que son solo de la vista local de
    investigadores, quedan vacíos.

Quitar cifras nunca abre una resta nueva: lo que queda publicado es un
subconjunto de lo que ya pasó por la supresión. La auditoría
(`cuidadores.auditoria`) se corre sobre esta copia, que es lo que se publica.

No importa ingesta ni pipeline: recibe el objeto ya calculado.
"""
from __future__ import annotations

import copy

import pandas as pd

from src.cuidadores import alertas

CLAVES_MUESTRA_LOCALES = ("ola",)


def _sin_solo_total(s) -> None:
    t = getattr(s, "cortes", None)
    if isinstance(t, pd.DataFrame) and not t.empty and "clave" in t.columns:
        s.cortes = t[~t["clave"].astype(str).isin(alertas.CLAVES_SOLO_TOTAL)].reset_index(
            drop=True)


def preparar(ac):
    """Copia del análisis para la comunidad y la publicación (ver el docstring del módulo)."""
    if getattr(ac, "ola", None):
        raise ValueError("La vista de comunidad y la publicación usan todas las olas: "
                         "la vista de una ola es solo local.")
    out = copy.copy(ac)
    marcos = {}
    for nombre in ("cuidador", "nino"):
        a = copy.deepcopy(getattr(ac, nombre))
        for grupos in (getattr(a, "subgrupos", None) or {}).values():
            for s in grupos.values():
                _sin_solo_total(s)
        a.muestra = {k: v for k, v in (a.muestra or {}).items()
                     if k not in CLAVES_MUESTRA_LOCALES}
        a.alertas = alertas.vacia()
        marcos[nombre] = a
    marcos["cuidador"].alertas = alertas.tabla(marcos["cuidador"])
    out.cuidador, out.nino = marcos["cuidador"], marcos["nino"]
    out.items_apq, out.items_estres = pd.DataFrame(), pd.DataFrame()
    out.flujo_ola = {}
    out.origen = "archivos"
    return out
```

- [ ] **Step 6: Correr las pruebas**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_alertas.py tests/test_cuidadores_pipeline.py -q`
Expected: `32 passed` (las de la 4a siguen igual: `preparar` no toca el análisis original).

- [ ] **Step 7: Commit**

```bash
git add src/cuidadores/alertas.py src/cuidadores/comunidad.py tests/cuidadores_comunidad_datos.py tests/test_cuidadores_alertas.py
git commit -m "feat(cuidadores): señales del adulto por grupo y copia para la comunidad

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Auditoría de lo que se publica

**Files:**
- Create: `src/cuidadores/auditoria.py`
- Create: `tests/test_cuidadores_auditoria.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_auditoria.py`:

```python
"""Cuidadores 360 · auditoría de lo que se publica (fase 4b, spec §4, §5.1 y §5.4)."""
import numpy as np
import pandas as pd

from src.cuidadores import auditoria
from src.cuidadores import catalog as cat
from src.estudiantes import privacidad as priv
from src.estudiantes import supresion
from tests import cuidadores_comunidad_datos as datos


def test_lo_preparado_pasa_la_auditoria():
    assert auditoria.auditar(datos.preparado().marcos) == []


def test_la_resta_cuenta_cuidadores_distintos_no_filas():
    """Un resto de 12 filas de solo 3 cuidadores (hermanos) es un hallazgo."""
    filas = []
    for i in range(20):
        filas.append(dict(ID_cuidador=f"A{i}", Colegio="A", Grado="Quinto", SDQ_Total=10.0))
    for i in range(12):
        filas.append(dict(ID_cuidador=f"R{i % 3}", Colegio="B", Grado="Quinto", SDQ_Total=10.0))
    d = pd.DataFrame(filas)
    base = priv.Base(n_total=len(d))
    base.celdas = {"A|Quinto": d.index[d["Colegio"] == "A"]}
    base.colegios = {"A": base.celdas["A|Quinto"]}
    base.grados = {"Quinto": d.index}                # el grado incluye el resto de B
    base.nivel = d.index
    problemas = auditoria.auditar_restas(d, base, ["SDQ_Total"])
    assert problemas and all("cuidadores distintos" in p for p in problemas)
    # contando filas (como estudiantes) no se vería
    assert priv.auditar(d, base, ["SDQ_Total"]) == []


def test_una_proporcion_destapada_es_un_hallazgo():
    ac = datos.preparado()
    a = ac.cuidador
    suprimidas = [(g, s) for g, s in a.subgrupos["Colegio"].items()
                  if s.cortes["pct"].isna().any()]
    assert suprimidas
    _, s = suprimidas[0]
    fila = s.cortes.index[s.cortes["pct"].isna()][0]
    s.cortes.loc[fila, "pct"] = 50.0                    # alguien la «destapa»
    assert auditoria.auditar_cifras(a)


def test_la_autolesion_por_grupo_es_un_hallazgo():
    ac = datos.preparado()
    s = next(iter(ac.cuidador.subgrupos["Colegio"].values()))
    s.cortes = pd.concat([s.cortes, ac.cuidador.cortes[
        ac.cuidador.cortes["clave"] == "EPDS_Autolesion"]], ignore_index=True)
    problemas = auditoria.auditar(ac.marcos)
    assert any("autolesión" in p for p in problemas)


def test_la_autolesion_en_la_tabla_de_senales_por_grupo_es_un_hallazgo():
    ac = datos.preparado()
    t = ac.cuidador.alertas.copy()
    t.loc[len(t)] = dict(alerta=cat.AUTOLESION, agrupacion="Colegio", grupo="LauV", n=30,
                         pct=12.0, ic_inf=5.0, ic_sup=20.0, estado="presente")
    ac.cuidador.alertas = t
    assert any("autolesión" in p for p in auditoria.auditar_solo_total(ac.cuidador))


def test_solo_el_total_publicado_se_audita_exacto_con_muchos_atomos():
    """Con más de MAX_ENUMERAR átomos y solo el total publicado no hay falso hallazgo."""
    n_atomos = supresion.MAX_ENUMERAR + 3
    celdas = [f"C{i}|Quinto" for i in range(n_atomos)]
    jer = supresion.jerarquia(celdas, [c.split("|")[0] for c in celdas], ["Quinto"],
                              con_resto=False)
    partes = {supresion.atomo_celda(k): (8, 2) for k in celdas}
    assert supresion.fugas(jer, partes, {supresion.NIVEL}, 3)          # falla cerrado
    assert auditoria.fugas(jer, partes, {supresion.NIVEL}, 3) == []
    pocos = {supresion.atomo_celda(k): ((10, 0) if i else (8, 2)) for i, k in enumerate(celdas)}
    assert auditoria.fugas(jer, pocos, {supresion.NIVEL}, 3)            # 2 casos en total


def _ninos_hermanos() -> pd.DataFrame:
    """30 cuidadores, 32 niños de un solo colegio y grado. La banda «muy alta» del SDQ
    tiene 4 niños, pero de solo 2 cuidadores (dos pares de hermanos)."""
    filas = []
    puntajes = [5] * 20 + [15] * 5 + [18] * 3
    for i, sdq in enumerate(puntajes):
        filas.append((f"c{i}", f"n{i}", sdq))
    for i in (28, 29):
        filas += [(f"c{i}", f"n{i}a", 25), (f"c{i}", f"n{i}b", 25)]
    return pd.DataFrame([dict(ID_cuidador=c, ID_nino=n, Colegio="A", Grado="Quinto",
                              Grado_detalle="Quinto", Ola="2026", Quien="Mamá",
                              Sexo="Niña" if k % 2 else "Niño", Edad=10.0, SDQ_Total=float(s))
                         for k, (c, n, s) in enumerate(filas)])


def test_el_marco_de_ninos_exige_tres_cuidadores_distintos():
    from src.cuidadores import pipeline
    a = pipeline.analizar_marco(_ninos_hermanos(), cat.MARCO_NINO, n_boot=5)
    banda = a.bandas[a.bandas["clave"] == "SDQ_Total"].iloc[0]
    assert pd.isna(banda["pct_b3"])                 # el pipeline la suprimió
    assert auditoria.auditar_cifras(a) == []
    # alguien la destapa con los porcentajes reales: 4 niños en la banda muy alta
    fila = a.bandas.index[a.bandas["clave"] == "SDQ_Total"][0]
    for i, pct in enumerate((62.5, 15.6, 9.4, 12.5)):
        a.bandas.loc[fila, f"pct_b{i}"] = pct
    problemas = auditoria.auditar_cifras(a)
    assert any("cuidadores" in p for p in problemas)


def test_los_mensajes_no_muestran_identificadores():
    ac = datos.preparado()
    s = next(iter(ac.cuidador.subgrupos["Colegio"].values()))
    s.cortes["pct"] = np.where(s.cortes["pct"].isna(), 50.0, s.cortes["pct"])
    for p in auditoria.auditar(ac.marcos):
        assert not any(t in p for t in ("Centinela", "3000000000"))
        assert not any(len(x) == 9 and x[0] in "CN" and all(c in "0123456789abcdef" for c in x[1:])
                       for x in p.split())
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_auditoria.py -q`
Expected: FAIL con `ImportError` (`cannot import name 'auditoria'`).

- [ ] **Step 3: Implementar**

`src/cuidadores/auditoria.py`:

```python
"""
Auditoría de lo que se publica de Cuidadores 360 (fase 4b, spec §4, §5.1 y §5.4).

Es la misma auditoría que corre estudiantes antes de publicar o de escribir un
informe (`estudiantes.publicar.verificar_restas`), adaptada a cuidadores:

  1. `auditar_restas`: ninguna resta de un paso entre un agregado y sus
     subgrupos publicados (nivel − colegios, nivel − grados, colegio − celdas,
     grado − celdas) deja de 1 a 9 CUIDADORES DISTINTOS, por indicador. En el
     marco de niños cuenta cuidadores, no filas (spec §4).
  2. `auditar_cifras`: recalcula desde los datos enmascarados, con la
     puntuación de cuidadores, el reparto de cada indicador en cada átomo de la
     base y comprueba que cada proporción publicada (también la de cada
     colegio, grado y celda) tiene de 3 a n − 3 casos, que ninguna suma o resta
     de lo publicado deja un conjunto que no cumpla (`supresion.fugas`) y, en
     el marco de niños, que los casos y los no casos vienen de 3 o más
     cuidadores distintos (`pipeline.regla_cuidadores_distintos`).
  3. `auditar_solo_total`: la autolesión no aparece en ningún grupo, ni en las
     tablas ni en las señales del adulto.

Se corre sobre lo que de verdad se publica: la copia de `comunidad.preparar`.
Los mensajes nombran marco, grupo e indicador; nunca cifras de personas.
"""
from __future__ import annotations

import pandas as pd

from src.cuidadores import alertas
from src.cuidadores import catalog as cat
from src.cuidadores import pipeline, privacidad, scoring
from src.estudiantes import privacidad as priv
from src.estudiantes import supresion

UNIDAD = privacidad.UNIDAD


def _distintos(d: pd.DataFrame, idx) -> int:
    return int(d.loc[idx, UNIDAD].nunique()) if len(idx) else 0


def auditar_restas(d: pd.DataFrame, base, columnas: list[str],
                   minimo: int = cat.MIN_GROUP_N) -> list[str]:
    """Restas de un paso que dejarían de 1 a minimo − 1 cuidadores distintos."""
    priv._exigir_indice_unico(d)
    problemas: list[str] = []
    for col in [None, *columnas]:
        if col is not None and col not in d.columns:
            continue
        validos = d.index if col is None else d.index[d[col].notna()]
        etiqueta = "respuestas" if col is None else col
        for nombre, idx_padre, hijos in priv.relaciones(base):
            padre = idx_padre.intersection(validos)
            if _distintos(d, padre) < minimo:
                continue
            publicados = [h.intersection(validos) for h in hijos]
            publicados = [h for h in publicados if _distintos(d, h) >= minimo]
            if not publicados:
                continue
            resto = padre.difference(priv.union(publicados))
            n = _distintos(d, resto)
            if 0 < n < minimo:
                problemas.append(f"{etiqueta}: {nombre} menos sus subgrupos publicados "
                                 f"deja menos de {minimo} cuidadores distintos")
    return problemas


def _familias(sub: pd.DataFrame, marco: str) -> dict:
    if sub.empty:
        return {}
    if marco == cat.MARCO_NINO:
        return supresion.partes_por_familia(scoring.sobre_cortes_nino(sub),
                                            scoring.bandas_nino(sub))
    return supresion.partes_por_familia(scoring.sobre_cortes_cuidador(sub), None)


def fugas(jer, partes: dict, pub: set, minimo: int, extra=None) -> list[frozenset]:
    """`supresion.fugas`, exacta también cuando solo se publica el total.

    Con un único agregado publicado (el total, como la autolesión) lo único que
    se deduce es ese mismo total: el espacio generado es una sola recta y un
    conjunto de átomos con indicador 0/1 en ella es vacío o el total entero.
    `supresion.fugas` no lo enumera cuando el total tiene más de MAX_ENUMERAR
    átomos y lo da por hallazgo (falla cerrado); aquí se comprueba directamente.
    """
    if pub and pub <= {supresion.NIVEL}:
        atomos = jer.grupos[supresion.NIVEL]
        largo = max((len(p) for p in partes.values()), default=2)
        return [] if supresion._seguro(atomos, partes, largo, minimo, extra) else [atomos]
    return supresion.fugas(jer, partes, pub, minimo, extra=extra)


def auditar_cifras(a, minimo: int = supresion.MIN_CASOS) -> list[str]:
    """Proporciones publicadas que delatan, recalculadas desde `a.datos` y `a.base`."""
    base, d = getattr(a, "base", None), getattr(a, "datos", None)
    if base is None or d is None or d.empty:
        return []
    jer = supresion.jerarquia(list(base.celdas), list(base.colegios), list(base.grados),
                              con_resto=base.incluye_resto)
    indices = supresion.indices_atomos(base)
    fam = {at: _familias(d.loc[d.index.intersection(idx)], a.nivel)
           for at, idx in indices.items()}
    objs = supresion._objetos(a)
    claves = sorted({c for f in fam.values() for c in f})
    reglas = (pipeline.regla_cuidadores_distintos(d, base, claves, minimo)
              if a.nivel == cat.MARCO_NINO else {})
    problemas: list[str] = []
    for clave in claves:
        largo = max(len(f[clave]) for f in fam.values() if clave in f)
        partes = {at: f.get(clave, (0,) * largo) for at, f in fam.items()}
        extra = reglas.get(clave)
        pub = {g for g, o in objs.items() if supresion._publicado(o, clave)}
        for g in sorted(pub, key=str):
            if g not in jer.grupos:
                problemas.append(f"{clave}: {g[0]} {g[1]} publicado fuera de la base")
                continue
            atomos = jer.grupos[g]
            if not supresion.partes_publicables(supresion._suma(atomos, partes, largo), minimo):
                problemas.append(f"{clave}: {g[0]} {g[1] or ''} publica una proporción con "
                                 f"menos de {minimo} casos o no casos")
            elif extra is not None and not extra(frozenset(atomos)):
                problemas.append(f"{clave}: {g[0]} {g[1] or ''} publica una proporción cuyos "
                                 f"casos o no casos vienen de menos de {minimo} cuidadores")
        for s in fugas(jer, partes, pub & set(jer.grupos), minimo, extra=extra):
            problemas.append(f"{clave}: una resta entre cifras publicadas deja un conjunto de "
                             f"{len(s)} grupo(s) con menos de {minimo} casos o no casos")
    return problemas


def auditar_solo_total(a) -> list[str]:
    """La autolesión solo en el total: ni en subgrupos ni en las señales por grupo."""
    problemas: list[str] = []
    for agrupacion, grupos in (getattr(a, "subgrupos", None) or {}).items():
        for grupo, s in grupos.items():
            t = getattr(s, "cortes", None)
            if (isinstance(t, pd.DataFrame) and not t.empty and "clave" in t.columns
                    and t["clave"].astype(str).isin(alertas.CLAVES_SOLO_TOTAL).any()):
                problemas.append(f"autolesión: {agrupacion} {grupo} la publica por grupo")
    t = getattr(a, "alertas", None)
    if isinstance(t, pd.DataFrame) and not t.empty:
        malas = t[t["alerta"].isin(alertas.SOLO_TOTAL) & (t["agrupacion"] != alertas.TOTAL)]
        if len(malas):
            problemas.append("autolesión: la tabla de señales la trae por grupo")
    return problemas


def auditar(marcos: dict) -> list[str]:
    """Todas las auditorías de cada marco con datos. Lista vacía = se puede publicar."""
    problemas: list[str] = []
    for marco, a in (marcos or {}).items():
        if a is None:
            continue
        problemas += [f"{marco} · {p}" for p in auditar_solo_total(a)]
        if getattr(a, "base", None) is None or a.datos is None or a.datos.empty:
            continue
        problemas += [f"{marco} · {p}" for p in
                      auditar_restas(a.datos, a.base, privacidad.columnas_de_analisis(a.datos))]
        problemas += [f"{marco} · {p}" for p in auditar_cifras(a)]
    return problemas
```

- [ ] **Step 4: Correr las pruebas**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_auditoria.py -q`
Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/cuidadores/auditoria.py tests/test_cuidadores_auditoria.py
git commit -m "feat(cuidadores): auditoría de lo publicado contando cuidadores distintos

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Publicador de agregados por módulo

**Files:**
- Create: `tests/supabase_falso.py`
- Create: `src/cuidadores/publicar.py`
- Create: `tests/test_cuidadores_publicar.py`

- [ ] **Step 1: La base falsa (sin red)**

`tests/supabase_falso.py`:

```python
"""
Una base `obs360` en memoria para las pruebas de publicar → leer (sin red).

Imita lo que importa del esquema real (supabase/estudiantes_schema.sql):
  · `corridas` con `id` y `creada_en` crecientes y `publicada = false` al entrar;
  · los CHECK de `resultados`: n ≥ 10, nivel en ('secundaria', 'primaria',
    'cuidadores'), ningún identificador ^[ECN][0-9a-f]{8}$ en `clave` ni en
    `grupo`, ningún conteo de casos en `detalle` y alertas con estado solo
    donde hay cifra;
  · RLS: el cliente anónimo no escribe y solo ve la ÚLTIMA corrida publicada
    de cada módulo (`es_ultima_publicada`) y sus resultados.
Y la cadena de PostgREST que usan los publicadores y los lectores: select, eq,
neq, order, limit, range, insert, update, delete y execute.
"""
from __future__ import annotations

import copy
import re

PATRON_ID = re.compile(r"^[ECN][0-9a-f]{8}$", re.IGNORECASE)
NIVELES = ("secundaria", "primaria", "cuidadores")


class ViolacionCheck(ValueError):
    """La fila no cumple un CHECK del esquema."""


def _check_resultado(f: dict) -> None:
    if int(f["n"]) < 10:
        raise ViolacionCheck("resultados_min_grupo")
    if f["nivel"] not in NIVELES:
        raise ViolacionCheck("resultados_nivel_valido")
    if PATRON_ID.match(str(f["clave"])) or (f.get("grupo") is not None
                                            and PATRON_ID.match(str(f["grupo"]))):
        raise ViolacionCheck("resultados_sin_id_estudiante")
    if set(f.get("detalle") or {}) & {"casos", "k_bajo", "k_alto"}:
        raise ViolacionCheck("resultados_sin_conteos")
    if (str(f["tipo"]).startswith("alerta") and f.get("valor") is None
            and (f.get("detalle") or {}).get("estado", "sin_estado") != "sin_estado"):
        raise ViolacionCheck("resultados_alerta_estado_con_cifra")


class _Respuesta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, base: "BaseFalsa", tabla: str, anonimo: bool):
        self.b, self.t, self.anon = base, tabla, anonimo
        self.filtros, self.orden, self.tope, self.rango = [], None, None, None
        self.accion, self.valores = "select", None

    # lectura
    def select(self, *_):
        self.accion = "select"
        return self

    def eq(self, k, v):
        self.filtros.append(lambda f, k=k, v=v: f.get(k) == v)
        return self

    def neq(self, k, v):
        self.filtros.append(lambda f, k=k, v=v: f.get(k) != v)
        return self

    def order(self, col, desc=False):
        self.orden = (col, desc)
        return self

    def limit(self, n):
        self.tope = n
        return self

    def range(self, desde, hasta):
        self.rango = (desde, hasta)
        return self

    # escritura
    def insert(self, filas):
        self.accion, self.valores = "insert", filas
        return self

    def update(self, valores):
        self.accion, self.valores = "update", valores
        return self

    def delete(self):
        self.accion = "delete"
        return self

    def _visibles(self) -> list[dict]:
        filas = self.b.tablas[self.t]
        if self.anon:
            if self.t == "corridas":
                filas = [f for f in filas if self.b.es_ultima_publicada(f["id"])]
            elif self.t == "resultados":
                filas = [f for f in filas if self.b.es_ultima_publicada(f["corrida_id"])]
        return [f for f in filas if all(c(f) for c in self.filtros)]

    def execute(self):
        if self.accion != "select" and self.anon:
            raise PermissionError("RLS: el rol anónimo no escribe")
        if self.accion == "insert":
            filas = self.valores if isinstance(self.valores, list) else [self.valores]
            nuevas = []
            for f in filas:
                f = copy.deepcopy(f)
                if self.t == "resultados":
                    _check_resultado(f)
                f["id"] = self.b.siguiente()
                if self.t == "corridas":
                    f.setdefault("publicada", False)
                    f["creada_en"] = f["id"]
                nuevas.append(f)
            self.b.tablas[self.t].extend(nuevas)
            return _Respuesta(copy.deepcopy(nuevas))
        if self.accion == "update":
            tocadas = self._visibles()
            for f in tocadas:
                f.update(self.valores)
            return _Respuesta(copy.deepcopy(tocadas))
        if self.accion == "delete":
            quitar = {id(f) for f in self._visibles()}
            self.b.tablas[self.t] = [f for f in self.b.tablas[self.t] if id(f) not in quitar]
            return _Respuesta([])
        filas = self._visibles()
        if self.orden:
            col, desc = self.orden
            filas = sorted(filas, key=lambda f: f.get(col), reverse=desc)
        if self.rango:
            filas = filas[self.rango[0]:self.rango[1] + 1]
        if self.tope is not None:
            filas = filas[:self.tope]
        return _Respuesta(copy.deepcopy(filas))


class BaseFalsa:
    def __init__(self):
        self.tablas: dict[str, list[dict]] = {"corridas": [], "resultados": []}
        self._id = 0

    def siguiente(self) -> int:
        self._id += 1
        return self._id

    def es_ultima_publicada(self, corrida_id) -> bool:
        propia = next((c for c in self.tablas["corridas"] if c["id"] == corrida_id), None)
        if propia is None:
            return False
        publicadas = [c for c in self.tablas["corridas"]
                      if c["publicada"] and c["modulo"] == propia["modulo"]]
        if not publicadas:
            return False
        return max(publicadas, key=lambda c: (c["creada_en"], c["id"]))["id"] == corrida_id

    def corrida(self, corrida_id) -> dict:
        return next(c for c in self.tablas["corridas"] if c["id"] == corrida_id)

    def cliente(self, anonimo: bool = False):
        base = self

        class _Esquema:
            def table(self, nombre):
                return _Consulta(base, nombre, anonimo)

        class _Postgrest:
            def schema(self, _):
                return _Esquema()

        class _Cliente:
            postgrest = _Postgrest()
        return _Cliente()
```

- [ ] **Step 2: Escribir las pruebas que fallan**

`tests/test_cuidadores_publicar.py`:

```python
"""Cuidadores 360 · publicación en Supabase (fase 4b): solo agregados, auditados."""
import json
import re

import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.cuidadores import publicar
from src.estudiantes import publicar as pub_est
from tests import cuidadores_comunidad_datos as datos
from tests import cuidadores_sinteticos as cs
from tests.supabase_falso import BaseFalsa, _check_resultado


@pytest.fixture(scope="module")
def ac():
    return datos.preparado()


@pytest.fixture(scope="module")
def filas(ac):
    return publicar.aplanar(ac)


def test_todo_es_del_nivel_cuidadores_con_su_marco(filas):
    assert filas
    assert {f["nivel"] for f in filas} == {"cuidadores"}
    assert {f["detalle"]["marco"] for f in filas} == set(cat.NOMBRES_MARCO)


def test_pasa_las_guardas_de_estudiantes_y_las_propias(filas):
    pub_est.verificar(filas)
    publicar.verificar(filas)


def test_cumple_los_check_de_la_base(filas):
    for f in filas:
        _check_resultado(f)


def test_sin_nombres_telefonos_identificadores_ni_casos(filas):
    texto = json.dumps(filas, ensure_ascii=False, default=str)
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in texto
    assert not re.search(r'"[ECN][0-9a-f]{8}"', texto)
    for f in filas:
        assert not set(f["detalle"]) & {"casos", "k_bajo", "k_alto"}


def test_nada_por_ola(filas):
    for f in filas:
        assert "ola" not in (f["detalle"].get("muestra") or {})
        assert "por_ola" not in (f["detalle"].get("ingesta") or {})
        assert f["agrupacion"] not in ("Ola",)


def test_la_autolesion_solo_en_el_total(filas):
    propias = [f for f in filas if f["clave"] in ("EPDS_Autolesion", cat.AUTOLESION)]
    assert propias and all(f["agrupacion"] == "total" for f in propias)


def test_sin_comparacion_por_sexo_ni_items_locales(filas):
    assert not [f for f in filas if f["agrupacion"] == "Sexo"]
    assert not [f for f in filas if f["tipo"] in ("item", "item_grupo")]


def test_cada_grupo_publicado_es_de_la_base(ac, filas):
    for f in filas:
        if f["tipo"] in ("corte_grupo", "banda_grupo"):
            marco = ac.marcos[f["detalle"]["marco"]]
            assert f["grupo"] in marco.subgrupos[f["agrupacion"]]


def test_la_auditoria_pasa(ac):
    assert publicar.verificar_restas(ac) == []


def test_no_se_publica_la_vista_de_una_ola(ac):
    import copy
    otra = copy.copy(ac)
    otra.ola = "2026"
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.aplanar(otra)


def test_publicar_ya_abre_la_corrida_y_cierra_solo_las_de_cuidadores(ac):
    base = BaseFalsa()
    vieja_est = base.cliente().postgrest.schema("obs360").table("corridas").insert(
        dict(modulo="estudiantes", version_analisis="x", publicada=True)).execute().data[0]
    primera = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    segunda = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert base.corrida(segunda["corrida_id"])["publicada"] is True
    assert base.corrida(primera["corrida_id"])["publicada"] is False
    assert base.corrida(vieja_est["id"])["publicada"] is True       # estudiantes intacto
    assert base.corrida(segunda["corrida_id"])["modulo"] == "cuidadores"


def test_sin_publicar_ya_queda_oculta(ac):
    base = BaseFalsa()
    r = publicar.publicar(ac, publicar_ya=False, cliente=base.cliente())
    assert base.corrida(r["corrida_id"])["publicada"] is False


def test_sin_aprobacion_publicar_ya_omite_las_senales(ac, monkeypatch):
    monkeypatch.setattr(cc, "TEXTOS_APROBADOS", False)
    base = BaseFalsa()
    r = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert r["alertas_omitidas"] > 0
    assert not [f for f in base.tablas["resultados"] if f["tipo"].startswith("alerta")]


def test_con_aprobacion_las_senales_se_publican(ac, monkeypatch):
    monkeypatch.setattr(cc, "TEXTOS_APROBADOS", True)
    monkeypatch.setattr(cc, "RUTAS_VALIDADAS", True)
    base = BaseFalsa()
    r = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert r["alertas_omitidas"] == 0
    assert [f for f in base.tablas["resultados"] if f["tipo"] == "alerta_grupo"]


def test_una_auditoria_fallida_no_toca_la_base(ac, monkeypatch):
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["cuidador · algo delata"])
    base = BaseFalsa()
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert base.tablas == {"corridas": [], "resultados": []}


def test_si_falla_el_insert_la_corrida_no_se_abre(ac):
    base = BaseFalsa()
    original = base.tablas

    class Rota(dict):
        def __getitem__(self, k):
            if k == "resultados":
                raise RuntimeError("red caída")
            return dict.__getitem__(self, k)
    base.tablas = Rota(original)
    with pytest.raises(RuntimeError):
        publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert not any(c["publicada"] for c in base.tablas["corridas"])


def _main(monkeypatch, tmp_path, *args):
    archivo = cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    monkeypatch.setenv("OBS360_CLAVE_HMAC", cs.CLAVE_PRUEBA)
    salida = tmp_path / "lote.json"
    codigo = publicar.main(["--ensayo", "--archivo", archivo, "--salida", str(salida), *args])
    return codigo, salida


def test_ensayo_sin_hallazgos_sale_con_0_y_solo_agregados(monkeypatch, tmp_path, capsys):
    codigo, salida = _main(monkeypatch, tmp_path)
    assert codigo == 0
    texto = salida.read_text(encoding="utf-8") + capsys.readouterr().out
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in texto
    assert not re.search(r"\b[CN][0-9a-f]{8}\b", texto)
    assert json.loads(salida.read_text(encoding="utf-8"))["modulo"] == "cuidadores"


def test_ensayo_con_hallazgos_escribe_el_json_y_sale_con_2(monkeypatch, tmp_path):
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["cuidador · algo delata"])
    codigo, salida = _main(monkeypatch, tmp_path)
    assert codigo == 2 and salida.exists()


def test_sin_clave_no_publica(monkeypatch, tmp_path):
    archivo = cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    monkeypatch.delenv("OBS360_CLAVE_HMAC", raising=False)
    monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    assert publicar.main(["--ensayo", "--archivo", archivo,
                          "--salida", str(tmp_path / "x.json")]) == 1
    assert not (tmp_path / "x.json").exists()
```

- [ ] **Step 3: Correrlas y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_publicar.py -q`
Expected: FAIL con `ImportError` (`cannot import name 'publicar' from 'src.cuidadores'`).

- [ ] **Step 4: Implementar**

`src/cuidadores/publicar.py`:

```python
"""
Publicación de Cuidadores 360 en Supabase — Observatorio 360 (fase 4b).

Es la otra mitad de `cuidadores.lectura` y sigue a `estudiantes.publicar`:
mismas tablas (`obs360.corridas`, `obs360.resultados`), mismas guardas y el
mismo orden, con `modulo = "cuidadores"`.

QUÉ SUBE
Solo agregados del análisis de TODAS las olas, ya preparado para la comunidad
(`comunidad.preparar`): descriptivos, cortes, bandas del SDQ de padres,
terciles, correlaciones, medias por colegio y por grado, CCI, las tablas de
cada colegio, grado y celda y las señales del adulto sin casos. Nada por ola,
ningún identificador, ningún conteo de casos. No se publican la comparación por
sexo del niño, los ítems del APQ ni los del estrés parental (solo locales).

CÓMO SE GUARDA
  · `nivel = "cuidadores"` en todas las filas (el CHECK de la base admite
    'secundaria', 'primaria' y 'cuidadores').
  · El marco va en `detalle.marco` ("cuidador" o "nino"): las claves de los
    dos marcos no se repiten, salvo «muestra», y el lector separa por ese campo.
  · La autolesión solo lleva la fila del total (spec §5.5).

GUARDAS, EN ESTE ORDEN (las de estudiantes, más las de cuidadores)
  1. `aplanar` solo lee tablas agregadas de la copia preparada.
  2. `estudiantes.publicar.verificar`: n ≥ 10, sin columnas de identificación,
     sin identificadores E/C/N y sin conteos de casos. Falla el lote entero.
  3. `verificar_restas` (`cuidadores.auditoria.auditar`): restas que dejen de 1
     a 9 cuidadores distintos, proporciones con menos de 3 casos o no casos
     (también por resta y, en el marco de niños, contando cuidadores) y
     autolesión por grupo. Con un hallazgo no se publica nada.
  4. El esquema rechaza n < 10, identificadores y conteos aunque todo lo
     anterior fallara; RLS: el rol anónimo no escribe.
  5. La corrida entra oculta y solo se abre con todos sus resultados dentro; al
     abrirla con `--publicar-ya` se despublican las demás corridas DE
     CUIDADORES (las de estudiantes no se tocan).
  6. Mientras `comunidad_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` no sean
     True, `--publicar-ya` no sube las filas de las señales del adulto
     (`alerta`, `alerta_grupo`). `--ensayo` las deja en el JSON y avisa.

USO (en la máquina que procesa, con OBS360_CLAVE_HMAC)
    python -m src.cuidadores.publicar --ensayo --salida /tmp/lote_cuidadores.json
    python -m src.cuidadores.publicar --notas "primera corrida" --publicar-ya
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import publicar as pub_est

MODULO = cat.MODULO
NIVEL = "cuidadores"
ESQUEMA = pub_est.ESQUEMA
TABLA_CORRIDAS = pub_est.TABLA_CORRIDAS
TABLA_RESULTADOS = pub_est.TABLA_RESULTADOS
PublicacionInsegura = pub_est.PublicacionInsegura
TIPOS_ALERTA = pub_est.TIPOS_ALERTA
AVISO_ALERTAS_NO_APROBADAS = (
    "AVISO: las señales del adulto no están aprobadas (comunidad_catalogo.TEXTOS_APROBADOS y "
    "RUTAS_VALIDADAS en False)")
FUENTE_BANDAS = "Scoring the SDQ for age 4-17, versión para padres, sdqinfo.org"


def alertas_aprobadas() -> bool:
    """¿El equipo aprobó los textos y validó la ruta para adultos? (spec §8)."""
    try:
        from src.cuidadores import comunidad_catalogo as cc
    except Exception:                                      # noqa: BLE001
        return False
    return (getattr(cc, "TEXTOS_APROBADOS", False) is True
            and getattr(cc, "RUTAS_VALIDADAS", False) is True)


def es_alerta(fila: dict) -> bool:
    return str(fila.get("tipo", "")) in TIPOS_ALERTA


def _fila(marco: str, tipo: str, clave, n, valor, **kw) -> dict:
    kw.setdefault("escala", cat.label(str(clave)))
    fila = pub_est._fila(NIVEL, tipo, clave, n, valor, **kw)
    fila["detalle"]["marco"] = marco
    return fila


def _filas_marco(marco: str, a) -> list[dict]:
    filas: list[dict] = []
    fiab = ({f["clave"]: f for _, f in a.fiabilidad.iterrows()}
            if a.fiabilidad is not None and not a.fiabilidad.empty else {})
    if a.descriptivos is not None and not a.descriptivos.empty:
        for _, f in a.descriptivos.iterrows():
            alfa = fiab.get(f["clave"], {})
            filas.append(_fila(marco, "descriptivo", f["clave"], f["n"], f["M"],
                               escala=f["escala"], DE=f["DE"], Mdn=f["Mdn"], rango=f["rango"],
                               P25=f["P25"], P75=f["P75"], pct_faltante=f["pct_faltante"],
                               direccion=f["direccion"], fuente=f["fuente"],
                               alpha=alfa.get("alpha"), alpha_ic_inf=alfa.get("ic_inf"),
                               alpha_ic_sup=alfa.get("ic_sup"),
                               n_items=alfa.get("n_items")))
    if a.bandas is not None and not a.bandas.empty:
        for _, f in a.bandas.iterrows():
            filas.append(_fila(marco, "banda", f["clave"], f["n"], f["pct_alto_o_muy_alto"],
                               escala=f["escala"], pct_b0=f["pct_b0"], pct_b1=f["pct_b1"],
                               pct_b2=f["pct_b2"], pct_b3=f["pct_b3"],
                               etiquetas=list(f["etiquetas"]), fuente=FUENTE_BANDAS))
    if a.cortes is not None and not a.cortes.empty:
        for _, f in a.cortes.iterrows():
            filas.append(_fila(marco, "corte", f["clave"], f["n"], f["pct"],
                               ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                               indicador=f["indicador"], fuente=f["fuente"]))
    if a.terciles is not None and not a.terciles.empty:
        for _, f in a.terciles.iterrows():
            filas.append(_fila(marco, "tercil", f["clave"], f["n"], None, escala=f["escala"],
                               corte_bajo=f["corte_bajo"], corte_alto=f["corte_alto"],
                               nota=f["nota"]))
    if a.correlaciones is not None and not a.correlaciones.empty:
        for _, f in a.correlaciones.iterrows():
            filas.append(_fila(marco, "correlacion", f["a"], f["n"], f["rho"],
                               ic_inf=f["ic_inf"], ic_sup=f["ic_sup"], variable_b=f["b"],
                               etiqueta_b=f["etiqueta_b"], p=f["p"], q_bh=f["q_bh"],
                               significativa=bool(f["significativa"])))
    for tabla, agrupacion in ((a.por_grado, "Grado"), (a.por_colegio, "Colegio")):
        if tabla is None or tabla.empty:
            continue
        for _, f in tabla.iterrows():
            for col in [c for c in tabla.columns if c.startswith("M·")]:
                grupo = col[2:]
                n_col = f"n·{grupo}"
                if n_col not in tabla.columns or pd.isna(f[col]) or pd.isna(f[n_col]):
                    continue
                filas.append(_fila(marco, "grupo", f["clave"], f[n_col], f[col],
                                   escala=f["escala"], agrupacion=agrupacion, grupo=grupo,
                                   p=f["p"], eta2=f.get("eta2"), q_bh=f.get("q_bh")))
    n_nivel = ((a.muestra or {}).get("base") or {}).get("n_nivel", a.n)
    for clave, valor in (a.icc or {}).items():
        if valor is not None and valor == valor:
            filas.append(_fila(marco, "icc", clave, n_nivel, valor,
                               nota="Proporción de varianza entre colegios"))
    for columna, grupos in (getattr(a, "subgrupos", None) or {}).items():
        for grupo, s in grupos.items():
            filas.extend(_filas_subgrupo(marco, columna, grupo, s))
    filas.extend(_filas_alertas(marco, a))
    if a.muestra:
        filas.append(_fila(
            marco, "muestra", "muestra", a.n, a.n, escala="Descripción de la muestra",
            muestra={k: (pub_est._enmascarar_conteos(v) if isinstance(v, dict) else v)
                     for k, v in a.muestra.items()},
            enmascarados=a.enmascarados or {}, escalas=list(a.escalas or []),
            avisos=list(a.avisos or [])))
    return filas


def _filas_subgrupo(marco: str, columna: str, grupo: str, s) -> list[dict]:
    if s is None or s.n < cat.MIN_GROUP_N:
        return []
    comun = dict(agrupacion=columna, grupo=str(grupo), n_grupo=s.n)
    filas: list[dict] = []
    if s.bandas is not None and not s.bandas.empty:
        for _, f in s.bandas.iterrows():
            if f["n"] < cat.MIN_GROUP_N:
                continue
            filas.append(_fila(marco, "banda_grupo", f["clave"], f["n"],
                               f["pct_alto_o_muy_alto"], escala=f["escala"],
                               pct_b0=f["pct_b0"], pct_b1=f["pct_b1"], pct_b2=f["pct_b2"],
                               pct_b3=f["pct_b3"], etiquetas=list(f["etiquetas"]),
                               fuente=FUENTE_BANDAS, **comun))
    if s.cortes is not None and not s.cortes.empty:
        for _, f in s.cortes.iterrows():
            if f["n"] < cat.MIN_GROUP_N:
                continue
            filas.append(_fila(marco, "corte_grupo", f["clave"], f["n"], f["pct"],
                               ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                               indicador=f["indicador"], fuente=f["fuente"], **comun))
    return filas


def _filas_alertas(marco: str, a) -> list[dict]:
    """Filas `alerta` (total) y `alerta_grupo` de las señales del adulto. Nunca casos."""
    from src.cuidadores import alertas
    from src.cuidadores import comunidad_catalogo as cc
    t = getattr(a, "alertas", None)
    if not isinstance(t, pd.DataFrame) or t.empty:
        return []
    filas: list[dict] = []
    for f in t.to_dict("records"):
        if int(f["n"]) < cat.MIN_GROUP_N or f["alerta"] not in cc.ALERTAS:
            continue
        nombre = cc.ALERTAS[f["alerta"]].nombre
        comun = dict(escala=nombre, ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                     indicador=nombre, estado=str(f["estado"]))
        if f["agrupacion"] == alertas.TOTAL:
            filas.append(_fila(marco, "alerta", f["alerta"], f["n"], f["pct"], **comun))
        elif f["alerta"] not in alertas.SOLO_TOTAL:
            filas.append(_fila(marco, "alerta_grupo", f["alerta"], f["n"], f["pct"],
                               agrupacion=f["agrupacion"], grupo=str(f["grupo"]), **comun))
    return filas


# Campos del informe de la carga que se publican (para la vista de investigadores
# del despliegue). Nada por ola: ni `por_ola`, ni los repetidos entre olas. Los
# `avisos` no van: repiten conteos exactos que aquí salen enmascarados.
CAMPOS_INGESTA = ("filas_archivo", "sin_consentimiento", "respuestas_validas", "por_quien",
                  "cuidadores_distintos", "respuestas_repetidas_cuidador", "filas_nino",
                  "hijo2", "mismo_nino_misma_respuesta", "mismo_nino_otro_cuidador",
                  "ninos_unicos", "edad_no_numerica", "edad_fuera_de_rango",
                  "curso_sin_resolver", "grados", "colegios_cuidador", "colegios_nino",
                  "colegio_no_reconocido", "respuestas_columna6_pss",
                  "etiquetas_no_mapeadas", "cobertura_ari", "faltantes_por_bloque")
# Porcentajes, no conteos: no se enmascaran.
CAMPOS_SIN_ENMASCARAR = ("faltantes_por_bloque",)


def aplanar_ingesta(informe) -> list[dict]:
    """Una fila con el flujo de la muestra; todo conteo de 1 a 9 sale como «<10»."""
    if informe is None:
        return []
    detalle = {}
    for campo in CAMPOS_INGESTA:
        valor = getattr(informe, campo, None)
        if valor in (None, [], {}):
            continue
        if campo not in CAMPOS_SIN_ENMASCARAR:
            valor = (pub_est._enmascarar_conteos(valor) if isinstance(valor, dict)
                     else pub_est._enmascarar_conteos({campo: valor})[campo])
        detalle[campo] = valor
    validas = getattr(informe, "respuestas_validas", 0) or 0
    return [_fila(cat.MARCO_CUIDADOR, "ingesta", "flujo_exclusiones",
                  max(int(validas), cat.MIN_GROUP_N), validas,
                  escala="Flujo de exclusiones", ingesta=detalle)]


def aplanar(ac) -> list[dict]:
    """Filas agregadas de un análisis YA preparado (`comunidad.preparar`)."""
    if getattr(ac, "ola", None):
        raise PublicacionInsegura("No se publica por ola: use el análisis de todas las olas.")
    filas: list[dict] = []
    for marco, a in ac.marcos.items():
        if a is not None:
            filas.extend(_filas_marco(marco, a))
    return filas + aplanar_ingesta(getattr(ac, "informe", None))


def verificar(filas: list[dict]) -> None:
    """Las guardas de estudiantes y, además, que todo sea del nivel «cuidadores»."""
    pub_est.verificar(filas)
    otros = [i for i, f in enumerate(filas) if f.get("nivel") != NIVEL
             or (f.get("detalle") or {}).get("marco") not in cat.NOMBRES_MARCO]
    if otros:
        raise PublicacionInsegura(f"No se publicó nada: {len(otros)} fila(s) sin nivel "
                                  "«cuidadores» o sin marco.")


def verificar_restas(ac) -> list[str]:
    """`cuidadores.auditoria.auditar` sobre los marcos que se publican."""
    from src.cuidadores import auditoria
    return auditoria.auditar(ac.marcos)


def version_analisis(ac) -> str:
    return pub_est.version_analisis(dict(ac.marcos))


def publicar(ac, notas: str = "", publicar_ya: bool = False, cliente=None) -> dict:
    """Sube el lote del análisis preparado. Devuelve el resumen de lo insertado."""
    filas = aplanar(ac)
    verificar(filas)
    restas = verificar_restas(ac)
    if restas:
        raise PublicacionInsegura(
            "No se publicó nada: la auditoría de cuidadores encontró cifras que delatan:\n  - "
            + "\n  - ".join(restas[:20]) + ("\n  … y más" if len(restas) > 20 else ""))
    alertas_omitidas = 0
    if publicar_ya and not alertas_aprobadas():
        alertas_omitidas = sum(1 for f in filas if es_alerta(f))
        filas = [f for f in filas if not es_alerta(f)]
        if alertas_omitidas:
            print(f"{AVISO_ALERTAS_NO_APROBADAS}: con --publicar-ya no se suben sus "
                  f"{alertas_omitidas} filas.", file=sys.stderr)
    elif not alertas_aprobadas() and any(es_alerta(f) for f in filas):
        print(f"{AVISO_ALERTAS_NO_APROBADAS}: la corrida queda oculta con sus filas de señales. "
              "No la abra a mano; publíquela de nuevo con --publicar-ya, que las omite.",
              file=sys.stderr)
    cli = cliente or pub_est._cliente()
    tabla = lambda t: cli.postgrest.schema(ESQUEMA).table(t)  # noqa: E731
    corrida = dict(modulo=MODULO, version_analisis=version_analisis(ac),
                   n_secundaria=None, n_primaria=None, notas=notas or None,
                   publicada=False)
    res = tabla(TABLA_CORRIDAS).insert(corrida).execute()
    corrida_id = res.data[0]["id"]
    try:
        for i in range(0, len(filas), 500):
            lote = [dict(f, corrida_id=corrida_id) for f in filas[i:i + 500]]
            tabla(TABLA_RESULTADOS).insert(lote).execute()
    except Exception:
        try:
            tabla(TABLA_RESULTADOS).delete().eq("corrida_id", corrida_id).execute()
            tabla(TABLA_CORRIDAS).delete().eq("id", corrida_id).execute()
        except Exception:                                  # noqa: BLE001
            pass
        raise
    publicada, otras_despublicadas = False, False
    if publicar_ya:
        tabla(TABLA_CORRIDAS).update({"publicada": True}).eq("id", corrida_id).execute()
        publicada = True
        try:
            (tabla(TABLA_CORRIDAS).update({"publicada": False})
             .eq("modulo", MODULO).neq("id", corrida_id).execute())
            otras_despublicadas = True
        except Exception as exc:                           # noqa: BLE001
            print(f"AVISO: la corrida {corrida_id} quedó publicada, pero no se pudieron "
                  f"despublicar las demás corridas de «{MODULO}» ({exc}). Despublique a mano: "
                  f"UPDATE obs360.corridas SET publicada = false WHERE modulo = '{MODULO}' "
                  f"AND id <> {corrida_id};", file=sys.stderr)
    return dict(corrida_id=corrida_id, version=corrida["version_analisis"], filas=len(filas),
                publicada=publicada, otras_corridas_despublicadas=otras_despublicadas,
                alertas_omitidas=alertas_omitidas)


def _resumen(filas: list[dict]) -> None:
    print(f"Lote: {len(filas)} filas agregadas")
    for tipo, cuenta in pd.Series([f["tipo"] for f in filas]).value_counts().items():
        print(f"  {tipo}: {cuenta}")
    print(f"  n mínimo en el lote: {min(f['n'] for f in filas)} "
          f"(el umbral es {cat.MIN_GROUP_N})")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Publica los agregados de Cuidadores 360.")
    p.add_argument("--ensayo", action="store_true",
                   help="no toca la red; deja el lote en un JSON (sale con 2 si la "
                        "auditoría encuentra algo)")
    p.add_argument("--salida", default="lote_cuidadores.json", help="JSON del ensayo")
    p.add_argument("--notas", default="", help="nota para la corrida")
    p.add_argument("--publicar-ya", action="store_true",
                   help="abre la corrida y cierra las demás de cuidadores")
    p.add_argument("--archivo", default=None,
                   help="exportación de «Cuidando al Cuidador» (por defecto, la de la "
                        "carpeta de datos fuente)")
    args = p.parse_args(argv)

    from src.core.seudonimo import ClaveAusente
    from src.cuidadores import comunidad, pipeline
    try:
        ac = comunidad.preparar(pipeline.cargar_y_analizar(args.archivo))
    except (ClaveAusente, FileNotFoundError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    filas = aplanar(ac)
    try:
        verificar(filas)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    _resumen(filas)
    print(f"  versión: {version_analisis(ac)}")
    if args.ensayo:
        n_alertas = sum(1 for f in filas if es_alerta(f))
        if n_alertas and not alertas_aprobadas():
            print(f"{AVISO_ALERTAS_NO_APROBADAS}: el JSON trae sus {n_alertas} filas para "
                  "revisarlas, pero --publicar-ya no las subiría hasta la aprobación.")
        restas = verificar_restas(ac)
        if restas:
            print("AVISO: la auditoría encontró problemas:\n  - " + "\n  - ".join(restas))
        with open(args.salida, "w", encoding="utf-8") as fh:
            json.dump(dict(modulo=MODULO, version=version_analisis(ac), filas=filas), fh,
                      ensure_ascii=False, indent=1, default=str)
        print(f"✓ Ensayo. Nada se subió. Lote escrito en {args.salida}")
        return 2 if restas else 0
    try:
        resumen = publicar(ac, notas=args.notas, publicar_ya=args.publicar_ya)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    print(f"✓ Corrida {resumen['corrida_id']} con {resumen['filas']} filas. "
          f"Publicada: {resumen['publicada']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Correr las pruebas**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_publicar.py -q`
Expected: `19 passed`. Por stderr salen los avisos de señales no aprobadas: es lo esperado.

- [ ] **Step 6: Commit**

```bash
git add tests/supabase_falso.py src/cuidadores/publicar.py tests/test_cuidadores_publicar.py
git commit -m "feat(cuidadores): publicador de agregados por módulo, auditado antes de subir

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Lectura de la corrida publicada

**Files:**
- Create: `src/cuidadores/lectura.py`
- Create: `tests/test_cuidadores_lectura.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_lectura.py`:

```python
"""Cuidadores 360 · publicar → leer por módulo, sin tocar la lectura de estudiantes."""
import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import lectura, publicar
from src.estudiantes import catalog as cat_est
from src.estudiantes import lectura as lec_est
from src.estudiantes import pipeline as pipe_est
from src.estudiantes import publicar as pub_est
from tests import cuidadores_comunidad_datos as datos
from tests.supabase_falso import BaseFalsa


@pytest.fixture(scope="module")
def ida_y_vuelta():
    leido, base = datos.publicado()
    return datos.preparado(), leido, base


@pytest.fixture(scope="module")
def estudiantes():
    from src.estudiantes import ingest, scoring
    from tests.test_estudiantes_comunidad import _formulario
    bruto, _ = ingest.cargar(_formulario())
    return {cat_est.NIVEL_SECUNDARIA: pipe_est.analizar(scoring.puntuar(bruto),
                                                         cat_est.NIVEL_SECUNDARIA, n_boot=20)}


def _sin_vacios(t: pd.DataFrame) -> pd.DataFrame:
    return t.reset_index(drop=True).astype(object).where(t.notna().reset_index(drop=True), None)


def test_la_lectura_reconstruye_las_mismas_cifras(ida_y_vuelta):
    local, leido, _ = ida_y_vuelta
    for marco in cat.NOMBRES_MARCO:
        a, b = local.marcos[marco], leido.marcos[marco]
        columnas = ["clave", "indicador", "n", "pct", "ic_inf", "ic_sup"]
        assert _sin_vacios(a.cortes[columnas]).equals(_sin_vacios(b.cortes[columnas]))
        for agrupacion, grupos in a.subgrupos.items():
            assert set(grupos) == set(b.subgrupos.get(agrupacion, {}))
            for g, s in grupos.items():
                assert _sin_vacios(s.cortes[columnas]).equals(
                    _sin_vacios(b.subgrupos[agrupacion][g].cortes[columnas]))
        assert list(a.descriptivos["M"]) == list(b.descriptivos["M"])
        assert a.n == b.n


def test_la_tabla_de_senales_es_la_misma(ida_y_vuelta):
    local, leido, _ = ida_y_vuelta
    assert _sin_vacios(local.cuidador.alertas).equals(_sin_vacios(leido.cuidador.alertas))
    assert leido.nino.alertas.empty


def test_lo_leido_no_trae_filas_ni_olas(ida_y_vuelta):
    _, leido, _ = ida_y_vuelta
    for a in leido.marcos.values():
        assert a.datos.empty and a.base is None
        assert "ola" not in a.muestra
    assert leido.ola is None and leido.origen == "supabase"
    assert leido.informe.por_ola == {}


def test_los_conteos_pequenos_del_informe_llegan_enmascarados(ida_y_vuelta):
    _, leido, _ = ida_y_vuelta
    inf = leido.informe
    assert inf.sin_consentimiento == "<10"           # una sola fila sin consentimiento
    assert isinstance(inf.filas_archivo, int) and inf.filas_archivo >= cat.MIN_GROUP_N


def test_sin_aprobacion_la_corrida_se_lee_sin_senales():
    leido, _ = datos.publicado(aprobado=False)
    assert leido.cuidador.alertas.empty
    assert not leido.cuidador.cortes.empty


def test_la_autolesion_por_grupo_se_ignora_aunque_llegara():
    filas = [dict(nivel="cuidadores", tipo="alerta_grupo", clave=cat.AUTOLESION,
                  agrupacion="Colegio", grupo="LauV", n=30, valor=10.0, ic_inf=5.0,
                  ic_sup=15.0, detalle={"marco": "cuidador", "estado": "presente"})]
    assert lectura._alertas(filas).empty


def test_solo_lee_la_ultima_corrida_publicada_de_cuidadores(ida_y_vuelta):
    _, _, base = ida_y_vuelta
    cli = base.cliente(anonimo=True)
    vigente = lectura.id_corrida_vigente(cli)
    assert base.corrida(vigente)["modulo"] == "cuidadores"
    publicar.publicar(datos.preparado(), publicar_ya=False, cliente=base.cliente())
    assert lectura.id_corrida_vigente(cli) == vigente       # la oculta no se ve


def test_publicar_cuidadores_no_cambia_la_lectura_de_estudiantes(estudiantes, monkeypatch):
    base = BaseFalsa()
    pub_est.publicar(estudiantes, publicar_ya=True, cliente=base.cliente())
    monkeypatch.setattr(lec_est, "_cliente", lambda: base.cliente(anonimo=True))
    antes_id = lec_est.id_corrida_vigente()
    antes, _, corrida_antes = lec_est.cargar_desde_supabase()
    publicar.publicar(datos.preparado(), publicar_ya=True, cliente=base.cliente())
    publicar.publicar(datos.preparado(), publicar_ya=True, cliente=base.cliente())
    despues, _, corrida_despues = lec_est.cargar_desde_supabase()
    assert lec_est.id_corrida_vigente() == antes_id
    assert corrida_antes == corrida_despues
    assert set(antes) == set(despues) == {cat_est.NIVEL_SECUNDARIA}
    a, b = antes[cat_est.NIVEL_SECUNDARIA], despues[cat_est.NIVEL_SECUNDARIA]
    assert _sin_vacios(a.cortes).equals(_sin_vacios(b.cortes))
    # y la de cuidadores lee la suya, no la de estudiantes
    leido, corrida = lectura.cargar_desde_supabase(base.cliente(anonimo=True))
    assert corrida["modulo"] == "cuidadores" and leido is not None


def test_sin_corrida_no_hay_nada_que_leer():
    base = BaseFalsa()
    assert lectura.cargar_desde_supabase(base.cliente(anonimo=True)) == (None, None)
    assert lectura.id_corrida_vigente(base.cliente(anonimo=True)) is None


def test_el_lector_no_importa_ingesta_ni_pipeline_de_cuidadores():
    import inspect
    fuente = inspect.getsource(lectura)
    for prohibido in ("cuidadores import ingest", "cuidadores import pipeline",
                      "cuidadores.ingest", "cuidadores.pipeline", "cuidadores import scoring"):
        assert prohibido not in fuente
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_lectura.py -q`
Expected: FAIL con `ImportError` (`cannot import name 'lectura' from 'src.cuidadores'`).

- [ ] **Step 3: Implementar**

`src/cuidadores/lectura.py`:

```python
"""
Lectura de la corrida publicada de Cuidadores 360 — Observatorio 360 (fase 4b).

Es la otra mitad de `cuidadores.publicar`. La usan el despliegue público
(vista de comunidad) y el despliegue del equipo (vista de investigadores sin
archivos): rearma, desde las filas agregadas, un objeto con la forma de
`AnalisisCuidadores` (`cuidador`, `nino`, `informe`, `marcos`), con `datos`
vacío y sin nada por ola. No puede recalcular nada sobre individuos: no hay
filas de personas.

Solo lee la ÚLTIMA corrida publicada del módulo «cuidadores» (filtro por
`modulo`, y la política RLS solo deja ver la última publicada de cada módulo),
con la clave `anon`, que no escribe. Nunca toca la de estudiantes.

Es un módulo nuevo y liviano: no importa ingesta, pipeline ni puntuación, así
que puede cargarse en el despliegue público.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pandas as pd

from src.cuidadores import alertas
from src.cuidadores import catalog as cat
from src.estudiantes.pipeline import Analisis

ESQUEMA = "obs360"
MODULO = cat.MODULO
NIVEL = "cuidadores"
TIPOS_SUBGRUPO = ("banda_grupo", "corte_grupo")

# Campos del informe de la carga con su valor si la corrida no los trae.
INFORME_POR_DEFECTO = dict(
    filas_archivo=0, sin_consentimiento=0, respuestas_validas=0, por_ola={}, por_quien={},
    cuidadores_distintos=0, respuestas_repetidas_cuidador=0, cuidadores_en_dos_olas=0,
    filas_nino=0, hijo2=0, ninos_sin_nombre=0, mismo_nino_misma_respuesta=0,
    mismo_nino_otro_cuidador=0, mismo_nino_entre_olas=0, ninos_unicos=0,
    edad_no_numerica=0, edad_fuera_de_rango=0, curso_sin_resolver=0, grados={},
    colegios_cuidador={}, colegios_nino={}, colegio_no_reconocido=0,
    respuestas_columna6_pss=0, etiquetas_no_mapeadas={}, cobertura_ari={},
    faltantes_por_bloque={}, enunciados={}, avisos=[])


@dataclass
class CuidadoresPublicados:
    """Lo mismo que `pipeline.AnalisisCuidadores`, rearmado desde la corrida publicada."""
    cuidador: Analisis
    nino: Analisis
    informe: object
    corrida: dict = field(default_factory=dict)
    ola: str | None = None
    olas: list = field(default_factory=list)
    items_apq: pd.DataFrame = field(default_factory=pd.DataFrame)
    items_estres: pd.DataFrame = field(default_factory=pd.DataFrame)
    flujo_ola: dict = field(default_factory=dict)
    origen: str = "supabase"

    @property
    def marcos(self) -> dict:
        return {cat.MARCO_CUIDADOR: self.cuidador, cat.MARCO_NINO: self.nino}


# ── Conexión (la misma de estudiantes: clave anon de lectura) ───────────────
def credenciales() -> tuple[str | None, str | None]:
    from src.estudiantes import lectura as lec_est
    return lec_est.credenciales()


def disponible() -> bool:
    url, key = credenciales()
    return bool(url and key)


def _cliente():
    from supabase import create_client
    url, key = credenciales()
    if not (url and key):
        raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_KEY.")
    return create_client(url, key)


def id_corrida_vigente(cli=None) -> int | None:
    """Id de la corrida de cuidadores publicada más reciente, o None."""
    cli = cli or _cliente()
    filas = (cli.postgrest.schema(ESQUEMA).table("corridas").select("id")
             .eq("modulo", MODULO).order("creada_en", desc=True).limit(1).execute().data)
    return int(filas[0]["id"]) if filas else None


def _traer_filas(cli) -> tuple[dict | None, list[dict]]:
    tabla = cli.postgrest.schema(ESQUEMA)
    corridas = (tabla.table("corridas").select("*").eq("modulo", MODULO)
                .order("creada_en", desc=True).limit(1).execute().data)
    if not corridas:
        return None, []
    corrida = corridas[0]
    filas, desde, paso = [], 0, 1000
    while True:
        lote = (tabla.table("resultados").select("*").eq("corrida_id", corrida["id"])
                .range(desde, desde + paso - 1).execute().data)
        filas.extend(lote)
        if len(lote) < paso:
            break
        desde += paso
    return corrida, filas


# ── Reconstrucción ──────────────────────────────────────────────────────────
def _det(f: dict, clave: str, defecto=None):
    return (f.get("detalle") or {}).get(clave, defecto)


def _df(filas: list[dict], columnas: list[str]) -> pd.DataFrame:
    return pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame(columns=columnas)


def _bandas(filas: list[dict]) -> pd.DataFrame:
    return _df([dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                     **{f"pct_b{i}": _det(f, f"pct_b{i}") for i in range(4)},
                     pct_alto_o_muy_alto=f["valor"], etiquetas=_det(f, "etiquetas", []))
                for f in filas],
               ["clave", "escala", "n", "pct_b0", "pct_b1", "pct_b2", "pct_b3",
                "pct_alto_o_muy_alto", "etiquetas"])


def _cortes(filas: list[dict]) -> pd.DataFrame:
    # Sin `casos`: nunca se publican. Un `pct` vacío es una cifra suprimida.
    return _df([dict(clave=f["clave"], indicador=_det(f, "indicador"), n=f["n"],
                     pct=f["valor"], ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                     fuente=_det(f, "fuente")) for f in filas],
               ["clave", "indicador", "n", "pct", "ic_inf", "ic_sup", "fuente"])


def _subgrupos(marco: str, filas: list[dict]) -> dict:
    por_grupo: dict[tuple[str, str], dict[str, list[dict]]] = {}
    for f in filas:
        if f["tipo"] in TIPOS_SUBGRUPO:
            cubo = por_grupo.setdefault((f["agrupacion"], str(f["grupo"])), {})
            cubo.setdefault(f["tipo"], []).append(f)
    salida: dict = {}
    for (columna, grupo), tipos in por_grupo.items():
        primera = next(iter(next(iter(tipos.values()))))
        n = int(_det(primera, "n_grupo") or primera["n"])
        s = Analisis(nivel=marco, n=n, datos=pd.DataFrame(), muestra=dict(n=n))
        s.bandas = _bandas(tipos.get("banda_grupo", []))
        s.cortes = _cortes(tipos.get("corte_grupo", []))
        salida.setdefault(columna, {})[grupo] = s
    return salida


def _alertas(filas: list[dict]) -> pd.DataFrame:
    salida = []
    for f in filas:
        if f["tipo"] not in ("alerta", "alerta_grupo"):
            continue
        total = f["tipo"] == "alerta"
        if not total and f["clave"] in alertas.SOLO_TOTAL:
            continue                      # nunca por grupo, aunque llegara
        salida.append(dict(alerta=f["clave"],
                           agrupacion=alertas.TOTAL if total else f["agrupacion"],
                           grupo=alertas.TODOS if total else str(f["grupo"]),
                           n=int(f["n"]), pct=f["valor"], ic_inf=f["ic_inf"],
                           ic_sup=f["ic_sup"],
                           estado=_det(f, "estado", alertas.SIN_ESTADO) or alertas.SIN_ESTADO))
    return alertas.ordenar(_df(salida, alertas.COLUMNAS_TABLA))


def _marco(marco: str, filas: list[dict]) -> Analisis:
    por_tipo: dict[str, list[dict]] = {}
    for f in filas:
        por_tipo.setdefault(f["tipo"], []).append(f)
    muestra, enmascarados, escalas, avisos = {}, {}, [], []
    for f in por_tipo.get("muestra", []):
        muestra = _det(f, "muestra", {}) or {}
        enmascarados = _det(f, "enmascarados", {}) or {}
        escalas = list(_det(f, "escalas", []) or [])
        avisos = list(_det(f, "avisos", []) or [])
    a = Analisis(nivel=marco, n=int(muestra.get("n") or 0), datos=pd.DataFrame(),
                 muestra=muestra, enmascarados=enmascarados, escalas=escalas, avisos=avisos)
    desc, fiab = [], []
    for f in por_tipo.get("descriptivo", []):
        desc.append(dict(clave=f["clave"], escala=f["escala"], n=f["n"], M=f["valor"],
                         DE=_det(f, "DE"), Mdn=_det(f, "Mdn"), rango=_det(f, "rango"),
                         pct_faltante=_det(f, "pct_faltante"), P25=_det(f, "P25"),
                         P75=_det(f, "P75"), direccion=_det(f, "direccion"),
                         fuente=_det(f, "fuente")))
        if _det(f, "alpha") is not None:
            fiab.append(dict(clave=f["clave"], escala=f["escala"],
                             n_items=_det(f, "n_items"), n=f["n"], alpha=_det(f, "alpha"),
                             ic_inf=_det(f, "alpha_ic_inf"), ic_sup=_det(f, "alpha_ic_sup")))
    orden = {p.clave: i for i, p in enumerate(cat.PUNTUACIONES)}
    a.descriptivos = _df(sorted(desc, key=lambda d: orden.get(d["clave"], 99)),
                         ["clave", "escala", "n", "M", "DE", "Mdn", "rango", "pct_faltante",
                          "P25", "P75", "direccion", "fuente"])
    a.fiabilidad = _df(fiab, ["clave", "escala", "n_items", "n", "alpha", "ic_inf", "ic_sup"])
    a.bandas = _bandas(por_tipo.get("banda", []))
    a.cortes = _cortes(por_tipo.get("corte", []))
    a.terciles = _df([dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                           corte_bajo=_det(f, "corte_bajo"), corte_alto=_det(f, "corte_alto"),
                           nota=_det(f, "nota")) for f in por_tipo.get("tercil", [])],
                     ["clave", "escala", "n", "corte_bajo", "corte_alto", "nota"])
    a.correlaciones = _df([dict(a=f["clave"], b=_det(f, "variable_b"), etiqueta_a=f["escala"],
                                etiqueta_b=_det(f, "etiqueta_b"), rho=f["valor"],
                                ic_inf=f["ic_inf"], ic_sup=f["ic_sup"], p=_det(f, "p"),
                                n=f["n"], q_bh=_det(f, "q_bh"),
                                significativa=bool(_det(f, "significativa", False)))
                           for f in por_tipo.get("correlacion", [])],
                          ["a", "b", "etiqueta_a", "etiqueta_b", "rho", "ic_inf", "ic_sup",
                           "p", "n", "q_bh", "significativa"])
    grupos = por_tipo.get("grupo", [])
    for agrupacion, destino in (("Grado", "por_grado"), ("Colegio", "por_colegio")):
        acumulado: dict[str, dict] = {}
        for f in [g for g in grupos if g["agrupacion"] == agrupacion]:
            fila = acumulado.setdefault(f["clave"], dict(
                clave=f["clave"], escala=f["escala"], p=_det(f, "p"), eta2=_det(f, "eta2"),
                q_bh=_det(f, "q_bh"), n=0))
            fila[f"M·{f['grupo']}"] = f["valor"]
            fila[f"n·{f['grupo']}"] = f["n"]
            fila["n"] += int(f["n"] or 0)
        setattr(a, destino, pd.DataFrame(list(acumulado.values())))
    a.icc = {f["clave"]: f["valor"] for f in por_tipo.get("icc", [])}
    a.subgrupos = _subgrupos(marco, filas)
    a.alertas = _alertas(filas) if marco == cat.MARCO_CUIDADOR else alertas.vacia()
    return a


def informe_desde(filas: list[dict]) -> SimpleNamespace:
    """El informe de la carga, con todos los campos (los conteos pequeños llegan «<10»)."""
    datos = dict(INFORME_POR_DEFECTO)
    for f in filas:
        if f["tipo"] == "ingesta":
            datos.update(_det(f, "ingesta", {}) or {})
    datos["origen"] = "supabase"
    return SimpleNamespace(**datos)


def reconstruir(filas: list[dict], corrida: dict | None = None) -> CuidadoresPublicados | None:
    """Objeto con la forma de `AnalisisCuidadores`; None si no hay filas de cuidadores."""
    propias = [f for f in filas if f.get("nivel") == NIVEL]
    por_marco: dict[str, list[dict]] = {m: [] for m in cat.NOMBRES_MARCO}
    for f in propias:
        marco = _det(f, "marco")
        if marco in por_marco:
            por_marco[marco].append(f)
    if not any(por_marco.values()):
        return None
    return CuidadoresPublicados(
        cuidador=_marco(cat.MARCO_CUIDADOR, por_marco[cat.MARCO_CUIDADOR]),
        nino=_marco(cat.MARCO_NINO, por_marco[cat.MARCO_NINO]),
        informe=informe_desde(propias), corrida=dict(corrida or {}))


def cargar_desde_supabase(cli=None) -> tuple[CuidadoresPublicados | None, dict | None]:
    """(cuidadores publicados, corrida). (None, corrida o None) si no hay nada que leer."""
    cli = cli or _cliente()
    corrida, filas = _traer_filas(cli)
    if not corrida or not filas:
        return None, corrida
    return reconstruir(filas, corrida), corrida


AVISO_PUBLICADO = ("Las cifras vienen de la corrida publicada de cuidadores: solo agregados de "
                   "grupos con 10 o más cuidadores distintos y de todas las olas.")
```

- [ ] **Step 4: Correr las pruebas (y las de lectura de estudiantes)**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_lectura.py tests/test_lectura_modulo.py tests/test_estudiantes_lectura.py -q`
Expected: todas pasan (`10` nuevas).

- [ ] **Step 5: Commit**

```bash
git add src/cuidadores/lectura.py tests/test_cuidadores_lectura.py
git commit -m "feat(cuidadores): lectura de la última corrida publicada del módulo

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Vista de comunidad, panel de señales e informes

**Files:**
- Create: `src/ui/views/cuidadores_comunidad.py`
- Create: `src/ui/views/cuidadores_informe.py`
- Create: `tests/test_cuidadores_comunidad.py`

La vista y los informes se crean juntos: el botón del resumen de una página de la vista importa `cuidadores_informe`, y este usa las funciones de la vista.

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_comunidad.py`:

```python
"""Cuidadores 360 · vista de comunidad (fase 4b, spec §5.5 y §6)."""
import pickle

import pytest
from streamlit.testing.v1 import AppTest

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.estudiantes import alertas_catalogo as ac_est
from src.ui.views import cuidadores_comunidad as vc
from tests import cuidadores_comunidad_datos as datos
from tests import cuidadores_sinteticos as cs

ROLES = ("colegio", "familia", "municipio")
PALABRAS_DANO = ("daño", "autoles", "muerte", "suicid")


@pytest.fixture(scope="module")
def ac():
    return datos.preparado()


@pytest.fixture(scope="module")
def senales(ac):
    return datos.con_senales(ac)


@pytest.fixture(scope="module")
def leido():
    return datos.publicado()[0]


# ══ Tarjetas ═══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("rol", ROLES)
def test_tarjetas_por_rol(ac, rol):
    claves = [t.clave for t in vc.tarjetas(ac, rol, {})]
    assert claves == ["estres", "apoyo", "crianza", "barrio", "hijo"]
    assert len(claves) <= cc.MAX_TARJETAS


def test_animo_solo_vuelve_si_el_panel_no_salio_y_nunca_para_familia(ac):
    assert "animo" in [t.clave for t in vc.tarjetas(ac, "colegio", {}, panel_dibujado=False)]
    assert "animo" in [t.clave for t in vc.tarjetas(ac, "municipio", {}, panel_dibujado=False)]
    assert "animo" not in [t.clave for t in vc.tarjetas(ac, "familia", {},
                                                         panel_dibujado=False)]
    assert len(vc.tarjetas(ac, "colegio", {}, panel_dibujado=False)) == cc.MAX_TARJETAS


def test_las_tarjetas_traen_cifra_texto_del_catalogo_y_accion_del_rol(ac):
    for t in vc.tarjetas(ac, "colegio", {}):
        m = cc.MENSAJES[t.clave]
        assert t.titulo == m.titulo and t.significa == m.significa
        assert t.accion == m.accion["colegio"]
        assert t.cifra


def test_una_cifra_suprimida_lleva_el_texto_fijo(ac):
    grupo = next(g for g in vc.grupos(ac, "Colegio")
                 if vc.suprimida(ac, "castigo", {"colegio": g}))
    t = next(t for t in vc.tarjetas(ac, "colegio", {"colegio": grupo}) if t.clave == "crianza")
    assert t.suprimida and t.cifra == vc.CIFRA_SUPRIMIDA and t.detalle == cc.CIFRAS_PEQUENAS
    assert "%" not in t.detalle


def test_las_medias_no_existen_por_celda(ac):
    assert vc.media(ac, "PSS_Total", {}) and vc.media(ac, "PSS_Total", {"colegio": "LauV"})
    assert vc.media(ac, "PSS_Total", {"colegio": "LauV", "grado": "Quinto"}) == {}


@pytest.mark.parametrize("rol", ROLES)
@pytest.mark.parametrize("filtros", [{}, {"colegio": "LauV"}, {"grado": "Quinto"},
                                     {"colegio": "LauV", "grado": "Quinto"},
                                     {"colegio": "SJMEB"}])
def test_local_y_publicado_muestran_lo_mismo(ac, leido, rol, filtros):
    assert vc.tarjetas(ac, rol, filtros) == vc.tarjetas(leido, rol, filtros)
    assert vc.bandas_hijo(ac, filtros) == vc.bandas_hijo(leido, filtros)
    assert vc.panel_html(ac, rol, filtros) == vc.panel_html(leido, rol, filtros)


def test_los_grupos_son_los_de_la_base_en_los_dos_marcos(ac, leido):
    assert vc.grupos(ac, "Colegio") == vc.grupos(leido, "Colegio") == \
        ["JJC", "LaBalsa", "LauV", "SJMEB"]
    assert vc.grupos(ac, "Grado", "LauV") == ["Quinto", "Sexto", "Octavo"]
    assert "OTRO" not in vc.grupos(ac, "Colegio") and "CdP" not in vc.grupos(ac, "Colegio")


# ══ Señales del adulto ═════════════════════════════════════════════════════
def test_familia_no_ve_cifras_ni_nada_sobre_hacerse_dano(senales):
    assert vc.senales(senales, "familia", {}) == []
    html = vc.panel_html(senales, "familia", {})
    assert cc.AUTOCUIDADO_FAMILIA in html and "%" not in html
    for palabra in PALABRAS_DANO:
        assert palabra not in html.lower()


def test_colegio_ve_animo_con_estado_general_y_nunca_la_autolesion(senales):
    for filtros in ({}, {"colegio": "LauV"}, {"colegio": "LauV", "grado": "Quinto"}):
        lista = vc.senales(senales, "colegio", filtros)
        assert [s.alerta for s in lista] == [cat.ANIMO]
        html = vc.panel_html(senales, "colegio", filtros)
        assert cc.ESTADO_GENERAL_COLEGIO in html
        assert cc.ALERTAS[cat.AUTOLESION].nombre not in html


def test_dentro_del_colegio_los_grados_en_prioridad(senales):
    s = vc.senales(senales, "colegio", {"colegio": "LauV"})[0]
    assert s.estado == ac_est.PRIORIDAD and s.pct == 40.0
    assert s.listas == ((ac_est.TITULO_GRADOS_PRIORIDAD, ("Quinto",)),)


def test_municipio_ve_la_autolesion_solo_del_total(senales):
    for filtros in ({}, {"colegio": "LauV"}, {"grado": "Quinto"}):
        auto = [s for s in vc.senales(senales, "municipio", filtros)
                if s.alerta == cat.AUTOLESION]
        assert len(auto) == 1 and auto[0].pct == 11.0 and auto[0].listas == ()
    assert vc.fila_alerta(senales, cat.AUTOLESION, {"colegio": "LauV"})["grupo"] == "Todos"


def test_municipio_ve_colegios_y_grados_en_prioridad(senales):
    s = next(s for s in vc.senales(senales, "municipio", {}) if s.alerta == cat.ANIMO)
    assert dict(s.listas) == {ac_est.TITULO_COLEGIOS_PRIORIDAD: ("LauV",),
                              ac_est.TITULO_GRADOS_PRIORIDAD: ("Quinto",)}


def test_sin_porcentaje_no_hay_estado_ni_cifra(senales):
    s = vc.senales(senales, "colegio", {"colegio": "SJMEB"})[0]
    assert s.estado == ac_est.SIN_ESTADO and s.pct is None
    assert s.frase == cc.CIFRAS_PEQUENAS


def test_la_frase_no_cuenta_casos(senales):
    s = vc.senales(senales, "municipio", {})[0]
    assert s.frase == "1 de cada 4 cuidadores muestra señales de ánimo bajo."


def test_la_tabla_de_la_secretaria_no_trae_la_autolesion(senales):
    html = vc.tabla_secretaria_html(senales)
    assert "LauV" in html and "Prioridad" in html
    assert cc.ALERTAS[cat.AUTOLESION].nombre_corto not in html


def test_sin_tabla_de_senales_no_hay_panel_y_vuelve_la_tarjeta(ac):
    vacio = datos.con_senales(ac, vc.al.vacia())
    assert vc.senales(vacio, "municipio", {}) == []
    assert vc.panel_html(vacio, "municipio", {}) == ""


def test_el_color_maximo_es_el_naranja_de_estudiantes():
    from src.ui.views import estudiantes_alertas as va
    assert vc.va is va
    assert "#C0392B" not in va.CSS_INFORME.upper() and "#C0392B" not in va.CSS_PAGINA.upper()


# ══ Comparar entre grupos ══════════════════════════════════════════════════
def test_comparables_por_rol():
    assert "animo" not in vc.comparables("familia")
    assert "animo" in vc.comparables("colegio") and "animo" in vc.comparables("municipio")
    for rol in ROLES:
        assert not [k for k in vc.comparables(rol) if "auto" in k]


def test_la_comparacion_sin_casos_y_solo_con_porcentaje(ac):
    t = vc.prevalencia_por(ac, "castigo", "Colegio")
    assert list(t.columns) == ["grupo", "n", "pct", "ic_inf", "ic_sup"]
    assert t["pct"].notna().all()
    sin = vc.grupos_sin_cifra(ac, "castigo", "Colegio")
    assert not set(sin) & set(t["grupo"])


# ══ Página (AppTest) ═══════════════════════════════════════════════════════
def _app(tmp_path, objeto: str, pre: str = "") -> AppTest:
    ruta = tmp_path / "objetos.pkl"
    if not ruta.exists():
        with open(ruta, "wb") as fh:
            pickle.dump((datos.preparado(), datos.publicado()[0]), fh)
    codigo = (f"import pickle\nac, leido = pickle.load(open({str(ruta)!r}, 'rb'))\n{pre}\n"
              "from src.ui.views.cuidadores_comunidad import render_comunidad\n"
              f"render_comunidad({objeto})\n")
    return AppTest.from_string(codigo, default_timeout=120)


def _pantalla(at) -> str:
    partes = [str(getattr(e, "value", "")) for grupo in (at.markdown, at.caption, at.info,
                                                         at.warning, at.subheader)
              for e in grupo]
    return " ".join(partes)


@pytest.mark.parametrize("objeto", ["ac", "leido"])
@pytest.mark.parametrize("rol", ROLES)
def test_la_vista_se_dibuja_para_cada_rol(tmp_path, objeto, rol):
    at = _app(tmp_path, objeto)
    at.session_state["cuid_com_rol"] = rol
    at.run()
    assert not at.exception
    pantalla = _pantalla(at)
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in pantalla
    assert cc.TITULO_RUTA in pantalla
    if rol == "familia":
        assert cc.AUTOCUIDADO_FAMILIA in pantalla
        for palabra in PALABRAS_DANO:
            assert palabra not in pantalla.lower()
        assert "cuid_com_colegio" not in [s.key for s in at.sidebar.selectbox]


def test_familia_no_tiene_selector_de_colegio_ni_informes(tmp_path):
    at = _app(tmp_path, "ac")
    at.session_state["cuid_com_rol"] = "familia"
    at.run()
    claves = [s.key for s in at.selectbox]
    assert "cuid_com_colegio" not in claves and "cuid_inf_colegio" not in claves


def test_cambiar_de_colegio_y_grado_no_falla(tmp_path):
    at = _app(tmp_path, "leido")
    at.session_state["cuid_com_rol"] = "municipio"
    at.run()
    at.selectbox(key="cuid_com_colegio").set_value("LauV").run()
    assert not at.exception
    assert list(at.selectbox(key="cuid_com_grado").options) == ["Todos", "Quinto", "Sexto",
                                                                "Octavo"]
    at.selectbox(key="cuid_com_grado").set_value("Quinto").run()
    assert not at.exception


def test_el_colegio_y_el_rol_se_comparten_con_estudiantes(tmp_path):
    from src.ui import estado
    at = _app(tmp_path, "ac")
    at.session_state[estado.COLEGIO] = "JJC"
    at.session_state[estado.ROL] = "municipio"
    at.run()
    assert at.selectbox(key="cuid_com_colegio").value == "JJC"
    assert at.radio(key="cuid_com_rol").value == "municipio"
    at.selectbox(key="cuid_com_colegio").set_value("LauV").run()
    assert at.session_state[estado.COLEGIO] == "LauV"


def test_el_colegio_de_la_url_aplica_a_cuidadores(tmp_path):
    from src.ui import estado
    pre = ("from src.ui import estado\nfrom src.ui.views import cuidadores_comunidad as vc\n"
           "estado.aplicar_colegio_de_url(vc.colegio_de_la_url(ac))")
    at = _app(tmp_path, "ac", pre)
    at.query_params["colegio"] = "lauv"
    at.run()
    assert not at.exception
    assert at.session_state[estado.COLEGIO] == "LauV"
    assert at.selectbox(key="cuid_com_colegio").value == "LauV"


def test_un_colegio_de_la_url_sin_cifras_se_ignora(tmp_path):
    from src.ui import estado
    pre = ("from src.ui import estado\nfrom src.ui.views import cuidadores_comunidad as vc\n"
           "estado.aplicar_colegio_de_url(vc.colegio_de_la_url(ac))")
    at = _app(tmp_path, "ac", pre)
    at.query_params["colegio"] = "CdP"
    at.run()
    assert not at.exception
    assert at.selectbox(key="cuid_com_colegio").value == "Todos"
    assert at.session_state[estado.COLEGIO] == "Todos"


def test_el_aviso_interno_solo_en_el_modo_completo(monkeypatch):
    monkeypatch.setenv("OBS360_MODO", "completo")
    assert cc.TEXTOS_PENDIENTES in vc.avisos_internos()
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    assert vc.avisos_internos() == []


def test_render_publico_sin_corrida_dice_que_no_hay(monkeypatch):
    from src.cuidadores import lectura
    monkeypatch.setattr(lectura, "disponible", lambda: False)
    at = AppTest.from_string("from src.ui.views.cuidadores_comunidad import render_publico\n"
                             "render_publico()\n", default_timeout=60).run()
    assert not at.exception
    assert any(cc.NO_PUBLICADO in i.value for i in at.info)


def test_la_vista_no_importa_lo_de_investigacion():
    import inspect
    fuente = inspect.getsource(vc)
    for prohibido in ("cuidadores import ingest", "cuidadores import pipeline",
                      "cuidadores_investigador", "src.ui.cuidadores", "cuidadores import scoring",
                      "cuidadores import privacidad", "cuidadores import comunidad\n"):
        assert prohibido not in fuente
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_comunidad.py -q`
Expected: FAIL con `ImportError` (`cannot import name 'cuidadores_comunidad' from 'src.ui.views'`).

- [ ] **Step 3: Implementar la vista**

`src/ui/views/cuidadores_comunidad.py`:

```python
"""
Vista comunidad de Cuidadores 360 — para colegios, familias y el municipio (fase 4b).

Misma estructura, mismos roles y mismos colores que la de estudiantes: cómo
están quienes cuidan, qué significa y qué se puede hacer. Cinco tarjetas como
techo, el panel «Señales para cuidar a quienes cuidan» arriba de las tarjetas y
la ruta para adultos siempre visible.

Tarjetas por rol (orden de `comunidad_catalogo.ORDEN_TARJETAS`, techo de 5):
  · colegio y municipio: estrés, apoyo, crianza y castigo físico, barrio y cómo
    ve el cuidador al hijo. «Ánimo» está en el panel de señales; la tarjeta solo
    vuelve si el panel no se pudo dibujar (como la de muerte en estudiantes).
  · familia: las mismas cinco. Nunca «Ánimo»: familia no ve cifras de las
    señales del adulto, solo el mensaje de autocuidado y la ruta (spec §5.5).

Reglas que este archivo respeta:
  · Solo lee tablas agregadas YA suprimidas: las del análisis preparado
    (`cuidadores.comunidad.preparar`) o las de la corrida publicada
    (`cuidadores.lectura`). Las dos tienen la misma forma, así que la máquina
    que procesa y el despliegue muestran lo mismo. No recalcula nada.
  · Ningún grupo con menos de 10 cuidadores distintos: solo se ofrecen los
    grupos de la base publicable (o los subgrupos publicados).
  · «Autolesión» solo para el rol municipio y solo con la cifra de todo el
    municipio; nunca por colegio ni por grado. En el rol colegio queda dentro
    de un estado general fijo, sin cifra.
  · Ningún conteo de casos; un porcentaje solo donde la supresión lo dejó.
  · Todos los textos vienen de `comunidad_catalogo`; aquí no se redacta.
  · No importa ingesta, pipeline ni la vista de investigadores: es la única
    vista de cuidadores que carga el despliegue público.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st

from src.cuidadores import alertas as al
from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.estudiantes import alertas_catalogo as ac_est
from src.estudiantes import privacidad
from src.ui import estado
from src.ui.views import estudiantes_alertas as va
from src.ui.views.estudiantes_comunidad import COLORES_BANDAS, figura_comparativa, uno_de_cada

TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
GRADOS = list(cat.GRADOS_ESTUDIO)
EXCLUIDOS = ("OTRO", "SIN_DATO")
CUIDADOR, NINO = cat.MARCO_CUIDADOR, cat.MARCO_NINO

# Proporciones que usan las tarjetas y «Comparar entre grupos» (filas de `cortes`).
INDICADORES: dict[str, dict] = {
    "animo": dict(marco=CUIDADOR, clave="EPDS_Total", indicador=al.INDICADOR_PROBABLE,
                  etiqueta="cuidadores con señales de ánimo bajo"),
    "apoyo_familia": dict(marco=CUIDADOR, clave="MSPSS_Fam",
                          etiqueta="cuidadores que sienten poco apoyo de su familia"),
    "apoyo_amigos": dict(marco=CUIDADOR, clave="MSPSS_Amigos",
                         etiqueta="sienten poco apoyo de sus amigos"),
    "apoyo_otro": dict(marco=CUIDADOR, clave="MSPSS_Otro",
                       etiqueta="sienten poco apoyo de una persona especial"),
    "castigo": dict(marco=CUIDADOR, clave="APQ_Fisico",
                    etiqueta="cuidadores que usan castigo físico a veces o más"),
    "grito": dict(marco=CUIDADOR, clave="APQ_Grito", etiqueta="gritan al hijo a veces o más"),
    "hijo_alto": dict(marco=NINO, clave="SDQ_Total",
                      etiqueta="niños con dificultades altas según su cuidador"),
}
# Tarjeta → indicador principal; las de media → (clave, máximo de la escala).
INDICADOR_TARJETA = {"animo": "animo", "apoyo": "apoyo_familia", "crianza": "castigo",
                     "hijo": "hijo_alto"}
EXTRAS_TARJETA = {"apoyo": ("apoyo_amigos", "apoyo_otro"), "crianza": ("grito",)}
MEDIAS = {"estres": ("PSS_Total", 40), "barrio": ("BARRIO_Indice", 10)}
COMPARABLES = ("castigo", "apoyo_familia", "hijo_alto", "animo")
CIFRA_SUPRIMIDA = "—"


@dataclass(frozen=True)
class Tarjeta:
    clave: str
    titulo: str
    cifra: str
    etiqueta: str
    significa: str
    accion: str
    detalle: str = ""
    suprimida: bool = False


# ══ Grupos y objetos ═══════════════════════════════════════════════════════
def ve_colegios(rol: str) -> bool:
    """Familia no ve desagregación por colegio (spec §6)."""
    return rol != "familia"


def hay_datos_crudos(a) -> bool:
    datos = getattr(a, "datos", None)
    return datos is not None and not datos.empty


def _ordenar(columna: str, grupos) -> list[str]:
    grupos = [str(g) for g in grupos if str(g) not in EXCLUIDOS]
    if columna == "Grado":
        return [g for g in GRADOS if g in grupos] + sorted(g for g in grupos if g not in GRADOS)
    return sorted(set(grupos))


def _grupos_marco(a, columna: str, otra=TODOS) -> list[str]:
    pos = 0 if columna == "Colegio" else 1
    base = getattr(a, "base", None)
    if base is not None and hay_datos_crudos(a):
        if not privacidad.activo(otra):
            return list((base.colegios if columna == "Colegio" else base.grados).keys())
        return [privacidad.partir_celda(k)[pos] for k in base.celdas
                if privacidad.partir_celda(k)[1 - pos] == str(otra)]
    sub = getattr(a, "subgrupos", None) or {}
    if not privacidad.activo(otra):
        return list((sub.get(columna) or {}).keys())
    return [privacidad.partir_celda(k)[pos] for k in (sub.get(CRUCE) or {})
            if privacidad.partir_celda(k)[1 - pos] == str(otra)]


def grupos(ac, columna: str, otra=TODOS) -> list[str]:
    """Grupos publicables de `columna` en alguno de los dos marcos, dentro de `otra`."""
    if ac is None:
        return []
    todos: list[str] = []
    for a in ac.marcos.values():
        if a is not None:
            todos += _grupos_marco(a, columna, otra)
    return _ordenar(columna, set(todos))


def objeto(a, filtros: dict | None):
    """El nivel, o el subgrupo del colegio, del grado o de la celda; None si no existe."""
    if a is None:
        return None
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    sub = getattr(a, "subgrupos", None) or {}
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return (sub.get(CRUCE) or {}).get(privacidad.clave_celda(colegio, grado))
    if privacidad.activo(colegio):
        return (sub.get("Colegio") or {}).get(str(colegio))
    if privacidad.activo(grado):
        return (sub.get("Grado") or {}).get(str(grado))
    return a


def hay_filtro(filtros: dict | None) -> bool:
    return any(privacidad.activo((filtros or {}).get(c, TODOS)) for c in ("colegio", "grado"))


def etiqueta_filtro(filtros: dict | None) -> str:
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    partes = ["Todos los colegios" if not privacidad.activo(colegio) else f"Colegio {colegio}"]
    if privacidad.activo(grado):
        partes.append(f"grado {grado}")
    return " · ".join(partes)


def n_grupo(ac, filtros: dict | None) -> int | None:
    """Cuidadores del grupo (marco de cuidadores), o None si el grupo no tiene cifras."""
    o = objeto(ac.cuidador, filtros)
    if o is None:
        return None
    if o is ac.cuidador:
        base = (getattr(o, "muestra", None) or {}).get("base") or {}
        try:
            return int(base.get("n_nivel", o.n))
        except (TypeError, ValueError):
            return int(o.n)
    return int(o.n)


# ══ Cifras ═════════════════════════════════════════════════════════════════
def _fila_corte(a, indicador: str, filtros: dict | None):
    cfg = INDICADORES[indicador]
    o = objeto(a, filtros)
    t = getattr(o, "cortes", None) if o is not None else None
    if not isinstance(t, pd.DataFrame) or t.empty or "clave" not in t.columns:
        return None
    sel = t[t["clave"].astype(str) == cfg["clave"]]
    if cfg.get("indicador") and "indicador" in sel.columns:
        sel = sel[sel["indicador"].astype(str) == cfg["indicador"]]
    if sel.empty or pd.isna(sel.iloc[0]["n"]) or int(sel.iloc[0]["n"]) < cat.MIN_GROUP_N:
        return None
    return sel.iloc[0]


def proporcion(ac, indicador: str, filtros: dict | None = None) -> dict:
    """{pct, ic_inf, ic_sup, n} del grupo; {} si no hay o si la supresión la ocultó."""
    a = ac.marcos[INDICADORES[indicador]["marco"]]
    f = _fila_corte(a, indicador, filtros)
    if f is None or pd.isna(f["pct"]):
        return {}
    return dict(pct=float(f["pct"]), ic_inf=float(f["ic_inf"]), ic_sup=float(f["ic_sup"]),
                n=int(f["n"]))


def suprimida(ac, indicador: str, filtros: dict | None = None) -> bool:
    """El grupo tiene el indicador (n ≥ 10) pero su porcentaje se ocultó por pocos casos."""
    f = _fila_corte(ac.marcos[INDICADORES[indicador]["marco"]], indicador, filtros)
    return f is not None and pd.isna(f["pct"])


def media(ac, clave: str, filtros: dict | None = None) -> dict:
    """{M, n} de una escala sin corte: del total, de un colegio o de un grado.

    Las medias por celda colegio × grado no se publican: {}.
    """
    a = ac.cuidador
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return {}
    if not hay_filtro(filtros):
        t = getattr(a, "descriptivos", None)
        if not isinstance(t, pd.DataFrame) or t.empty:
            return {}
        sel = t[t["clave"] == clave]
        if sel.empty or pd.isna(sel.iloc[0]["M"]):
            return {}
        return dict(M=float(sel.iloc[0]["M"]), n=int(sel.iloc[0]["n"]))
    columna, grupo = (("Colegio", colegio) if privacidad.activo(colegio) else ("Grado", grado))
    t = getattr(a, "por_colegio" if columna == "Colegio" else "por_grado", None)
    if not isinstance(t, pd.DataFrame) or t.empty or f"M·{grupo}" not in t.columns:
        return {}
    sel = t[t["clave"] == clave]
    if sel.empty or pd.isna(sel.iloc[0][f"M·{grupo}"]):
        return {}
    return dict(M=float(sel.iloc[0][f"M·{grupo}"]), n=int(sel.iloc[0][f"n·{grupo}"]))


def _pct(p: dict) -> str:
    return f"{p['pct']:.0f} %"


def tarjetas(ac, rol: str, filtros: dict | None = None,
             panel_dibujado: bool = True) -> list[Tarjeta]:
    """Hasta `cc.MAX_TARJETAS` tarjetas con cifra, textos del catálogo y acción del rol."""
    filtros = filtros or {}
    salida: list[Tarjeta] = []
    for clave in cc.ORDEN_TARJETAS:
        m = cc.MENSAJES[clave]
        accion = m.accion.get(rol, "")
        if rol not in m.solo_roles or not accion:
            continue
        if clave == "animo" and panel_dibujado:
            continue
        if clave in MEDIAS:
            escala, maximo = MEDIAS[clave]
            x = media(ac, escala, filtros)
            if not x:
                continue
            detalle = f"Base de {x['n']} cuidadores"
            if hay_filtro(filtros):
                ref = media(ac, escala, {})
                if ref:
                    detalle += f" · municipio: {ref['M']:.1f} de {maximo}"
            salida.append(Tarjeta(clave, m.titulo, f"{x['M']:.1f} de {maximo}", m.etiqueta,
                                  m.significa, accion, detalle))
        else:
            indicador = INDICADOR_TARJETA[clave]
            p = proporcion(ac, indicador, filtros)
            if not p:
                if suprimida(ac, indicador, filtros):
                    salida.append(Tarjeta(clave, m.titulo, CIFRA_SUPRIMIDA, m.etiqueta,
                                          m.significa, accion, cc.CIFRAS_PEQUENAS, True))
                    if len(salida) == cc.MAX_TARJETAS:
                        break
                continue
            unidad = "niños" if INDICADORES[indicador]["marco"] == NINO else "cuidadores"
            detalle = (f"{_pct(p)} (IC 95 % {p['ic_inf']:.0f}–{p['ic_sup']:.0f}); base de "
                       f"{p['n']} {unidad}")
            extras = []
            for otro in EXTRAS_TARJETA.get(clave, ()):
                q = proporcion(ac, otro, filtros)
                if q:
                    extras.append(f"{_pct(q)} {INDICADORES[otro]['etiqueta']}")
            if extras:
                detalle += ". " + "; ".join(extras)
            salida.append(Tarjeta(clave, m.titulo, uno_de_cada(p["pct"]), m.etiqueta,
                                  m.significa, accion, detalle))
        if len(salida) == cc.MAX_TARJETAS:
            break
    return salida


def bandas_hijo(ac, filtros: dict | None = None) -> dict:
    """Las cuatro bandas del SDQ total según el cuidador, o {} si no hay o se ocultaron."""
    o = objeto(ac.nino, filtros)
    t = getattr(o, "bandas", None) if o is not None else None
    if not isinstance(t, pd.DataFrame) or t.empty or "clave" not in t.columns:
        return {}
    sel = t[t["clave"] == "SDQ_Total"]
    if sel.empty:
        return {}
    f = sel.iloc[0]
    if int(f["n"]) < cat.MIN_GROUP_N or any(pd.isna(f[f"pct_b{i}"]) for i in range(4)):
        return {}
    etiquetas = list(f["etiquetas"]) if isinstance(f.get("etiquetas"), (list, tuple)) and \
        len(f["etiquetas"]) == 4 else ["Cercano al promedio", "Ligeramente elevado", "Alto",
                                       "Muy alto"]
    return dict(n=int(f["n"]), pct=[float(f[f"pct_b{i}"]) for i in range(4)],
                etiquetas=etiquetas)


def comparables(rol: str) -> list[str]:
    """Indicadores de «Comparar entre grupos». «Ánimo» nunca para familia."""
    return [k for k in COMPARABLES if k != "animo" or rol in ("colegio", "municipio")]


def prevalencia_por(ac, indicador: str, columna: str, filtros: dict | None = None
                    ) -> pd.DataFrame:
    """El indicador por colegio o por grado, desde las tablas de cada grupo (sin casos)."""
    filtros = filtros or {}
    otra = "grado" if columna == "Colegio" else "colegio"
    valor_otra = filtros.get(otra, TODOS)
    filas = []
    for g in grupos(ac, columna, valor_otra):
        propio = filtros.get(columna.lower(), TODOS)
        if privacidad.activo(propio) and g != str(propio):
            continue
        p = proporcion(ac, indicador, {columna.lower(): g, otra: valor_otra})
        if p:
            filas.append(dict(grupo=g, n=p["n"], pct=p["pct"], ic_inf=p["ic_inf"],
                              ic_sup=p["ic_sup"]))
    return pd.DataFrame(filas, columns=["grupo", "n", "pct", "ic_inf", "ic_sup"])


def grupos_sin_cifra(ac, indicador: str, columna: str, filtros: dict | None = None) -> list[str]:
    filtros = filtros or {}
    otra = "grado" if columna == "Colegio" else "colegio"
    return [g for g in grupos(ac, columna, filtros.get(otra, TODOS))
            if suprimida(ac, indicador, {columna.lower(): g, otra: filtros.get(otra, TODOS)})]


# ══ Señales del adulto ═════════════════════════════════════════════════════
def tabla_alertas(ac) -> pd.DataFrame:
    t = getattr(ac.cuidador, "alertas", None) if ac is not None else None
    if isinstance(t, pd.DataFrame) and len(t) and set(al.COLUMNAS_TABLA) <= set(t.columns):
        return t
    return al.vacia()


def _clave_grupo(filtros: dict | None) -> tuple[str, str]:
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return CRUCE, privacidad.clave_celda(colegio, grado)
    if privacidad.activo(colegio):
        return "Colegio", str(colegio)
    if privacidad.activo(grado):
        return "Grado", str(grado)
    return al.TOTAL, TODOS


def fila_alerta(ac, alerta: str, filtros: dict | None = None) -> dict | None:
    """La fila del grupo elegido; la autolesión siempre es la del total del municipio."""
    t = tabla_alertas(ac)
    if not len(t):
        return None
    agrupacion, grupo = ((al.TOTAL, TODOS) if alerta in al.SOLO_TOTAL
                         else _clave_grupo(filtros))
    sel = t[(t["alerta"] == alerta) & (t["agrupacion"] == agrupacion)
            & (t["grupo"].astype(str) == str(grupo))]
    return None if sel.empty else sel.iloc[0].to_dict()


def _con_cifra(f) -> bool:
    return bool(f) and f.get("pct") is not None and not pd.isna(f.get("pct"))


def frase(alerta: str, pct: float) -> str:
    fraccion = uno_de_cada(pct)
    verbo = "muestra" if fraccion.startswith("1 de cada") else "muestran"
    return cc.PLANTILLA_CIFRA.format(fraccion=fraccion, verbo=verbo,
                                     senal=cc.ALERTAS[alerta].senal)


def listas_prioridad(ac, alerta: str, rol: str, filtros: dict | None = None
                     ) -> list[tuple[str, list[str]]]:
    """Grupos en «Prioridad» que el rol puede ver. Solo «Ánimo»; nunca para familia."""
    if rol == "familia" or alerta in al.SOLO_TOTAL:
        return []
    t = tabla_alertas(ac)
    if not len(t):
        return []
    t = t[(t["alerta"] == alerta) & (t["estado"] == al.PRIORIDAD)]
    agrupacion, grupo = _clave_grupo(filtros)
    salida: list[tuple[str, list[str]]] = []
    if agrupacion == "Colegio":
        prefijo = grupo + privacidad.SEP
        grados = [privacidad.partir_celda(g)[1]
                  for g in t.loc[t["agrupacion"] == CRUCE, "grupo"].astype(str)
                  if g.startswith(prefijo)]
        salida.append((ac_est.TITULO_GRADOS_PRIORIDAD, _ordenar("Grado", grados)))
    elif agrupacion == al.TOTAL:
        if rol == "municipio":
            colegios = _ordenar("Colegio", t.loc[t["agrupacion"] == "Colegio", "grupo"])
            salida.append((ac_est.TITULO_COLEGIOS_PRIORIDAD, colegios))
        salida.append((ac_est.TITULO_GRADOS_PRIORIDAD,
                       _ordenar("Grado", t.loc[t["agrupacion"] == "Grado", "grupo"])))
    return [(titulo, nombres) for titulo, nombres in salida if nombres]


def senales(ac, rol: str, filtros: dict | None = None) -> list[va.Senal]:
    """Una señal por cada una que el rol puede ver. Familia: ninguna (sin cifras)."""
    if rol == "familia" or ac is None:
        return []
    t = tabla_alertas(ac)
    salida: list[va.Senal] = []
    for alerta, definicion in cc.ALERTAS.items():
        if rol not in definicion.roles or not len(t) or not (t["alerta"] == alerta).any():
            continue
        f = fila_alerta(ac, alerta, filtros)
        listas = tuple((ti, tuple(ns)) for ti, ns in listas_prioridad(ac, alerta, rol, filtros))
        que_hacer = definicion.que_hacer.get(rol, "")
        if not _con_cifra(f):
            salida.append(va.Senal(alerta=alerta, nombre=definicion.nombre,
                                   estado=al.SIN_ESTADO, frase=cc.CIFRAS_PEQUENAS,
                                   que_hacer=que_hacer, listas=listas))
            continue
        salida.append(va.Senal(alerta=alerta, nombre=definicion.nombre,
                               estado=va.estado_valido(f["estado"]),
                               frase=frase(alerta, float(f["pct"])), que_hacer=que_hacer,
                               pct=float(f["pct"]), ic_inf=float(f["ic_inf"]),
                               ic_sup=float(f["ic_sup"]), n=int(f["n"]), listas=listas))
    return salida


def _e(texto) -> str:
    return escape(str(texto), quote=True)


def _unir(nombres, tope: int | None = None) -> str:
    nombres = list(nombres)
    if tope and len(nombres) > tope:
        return ", ".join(nombres[:tope]) + f" y {len(nombres) - tope} más"
    return ", ".join(nombres)


def panel_html(ac, rol: str, filtros: dict | None = None, compacto: bool = False) -> str:
    """Panel para los informes; `compacto` para el resumen de una página."""
    if rol == "familia":
        return (f'<section class="senales"><h2>{_e(cc.TITULO_AUTOCUIDADO)}</h2>'
                f'<p class="nota-senal">{_e(cc.AUTOCUIDADO_FAMILIA)}</p></section>')
    lista = senales(ac, rol, filtros)
    if not lista:
        return ""
    tope = va.MAX_NOMBRES_PAGINA if compacto else None
    bloques = []
    for s in lista:
        chip = f'<span class="estado">{_e(s.etiqueta_estado)}</span>'
        listas = "".join(f' <span class="lista">{_e(t)} {_e(_unir(ns, tope))}</span>'
                         for t, ns in s.listas)
        nota = (f' <span class="lista">{_e(cc.NOTA_SOLO_MUNICIPIO)}</span>'
                if s.alerta in al.SOLO_TOTAL and not compacto else "")
        if compacto:
            bloques.append(f'<p class="senal senal-{s.clase}">{chip} <b>{_e(s.nombre)}.</b> '
                           f'{_e(s.frase)}{listas}</p>')
            continue
        margen = (f'<p class="margen">Margen de error {s.ic_inf:.0f}–{s.ic_sup:.0f} % · base '
                  f'de {s.n} cuidadores</p>' if s.visible else "")
        hacer = (f'<p class="accion"><b>Qué hacer.</b> {_e(s.que_hacer)}</p>'
                 if s.que_hacer else "")
        bloques.append(f'<div class="senal senal-{s.clase}"><p>{chip} <b>{_e(s.nombre)}</b></p>'
                       f'<p>{_e(s.frase)}{nota}</p>'
                       + (f"<p>{listas.strip()}</p>" if listas else "") + margen + hacer
                       + "</div>")
    notas = [ac_est.NO_ES_DIAGNOSTICO, ac_est.NOTA_AZAR]
    if rol == "colegio":
        notas.insert(0, cc.ESTADO_GENERAL_COLEGIO)
    return (f'<section class="senales"><h2>{_e(cc.TITULO_PANEL)}</h2>' + "".join(bloques)
            + f'<p class="nota-senal">{_e(" ".join(notas))}</p></section>')


def _celda_html(f) -> str:
    if not _con_cifra(f):
        return (f'<td class="senal-sin-estado"><span class="estado">'
                f'{_e(ac_est.ESTADOS[al.SIN_ESTADO])}</span>'
                f'<small>{_e(ac_est.CIFRAS_PEQUENAS_CORTO)}</small></td>')
    estado_ = va.estado_valido(f["estado"])
    return (f'<td class="senal-{va.CLASE.get(estado_, va.CLASE[al.SIN_ESTADO])}">'
            f'<span class="estado">{_e(ac_est.ESTADOS[estado_])}</span> '
            f'{float(f["pct"]):.0f} %<small>{float(f["ic_inf"]):.0f}–'
            f'{float(f["ic_sup"]):.0f}</small></td>')


def tabla_secretaria_html(ac) -> str:
    """«Ánimo» por colegio para la Secretaría: estado y %, sin conteos. Nunca autolesión."""
    t = tabla_alertas(ac)
    if not len(t) or not (t["alerta"] == cat.ANIMO).any():
        return ""
    colegios = _ordenar("Colegio", t.loc[(t["agrupacion"] == "Colegio")
                                        & (t["alerta"] == cat.ANIMO), "grupo"])
    nombre = cc.ALERTAS[cat.ANIMO].nombre_corto
    cuerpo = "".join(f'<tr><th scope="row">{_e(c)}</th>'
                     f'{_celda_html(fila_alerta(ac, cat.ANIMO, {"colegio": c}))}</tr>'
                     for c in colegios)
    total = (f'<tr><th scope="row">Total del municipio</th>'
             f'{_celda_html(fila_alerta(ac, cat.ANIMO, {}))}</tr>')
    return (f'<section class="bloque senales"><h2>{_e(cc.TITULO_PANEL)} · por colegio</h2>'
            f'<div class="desliza"><table class="senales-tabla"><thead><tr><th></th>'
            f'<th>{_e(nombre)}</th></tr></thead><tbody>{cuerpo}</tbody><tfoot>{total}</tfoot>'
            f'</table></div><p class="nota">{_e(cc.NOTA_TABLA)} {_e(ac_est.NOTA_AZAR)}</p>'
            "</section>")


# ══ Streamlit ══════════════════════════════════════════════════════════════
def render_panel(ac, rol: str, filtros: dict | None = None) -> bool:
    """Dibuja el panel arriba de las tarjetas. True si salió «Ánimo» (colegio, municipio)."""
    if rol == "familia":
        with st.container(border=True):
            st.markdown(f"#### {cc.TITULO_AUTOCUIDADO}")
            st.markdown(cc.AUTOCUIDADO_FAMILIA)
        return True
    lista = senales(ac, rol, filtros)
    if not lista:
        return False
    with st.container(border=True):
        st.markdown(f"#### {cc.TITULO_PANEL}")
        for s in lista:
            st.markdown(f"{va._chip_html(s)} **{_e(s.nombre)}**", unsafe_allow_html=True)
            st.markdown(f"{s.frase} {ac_est.NO_ES_DIAGNOSTICO}")
            if s.alerta in al.SOLO_TOTAL:
                st.caption(cc.NOTA_SOLO_MUNICIPIO)
            for titulo, nombres in s.listas:
                st.markdown(f"{titulo} {_unir(nombres)}")
            if s.que_hacer:
                st.markdown(f"**Qué hacer:** {s.que_hacer}")
        if rol == "colegio":
            st.markdown(cc.ESTADO_GENERAL_COLEGIO)
        with st.expander("Qué quiere decir cada estado"):
            for s in lista:
                st.markdown(f"**{s.nombre}.** {cc.ALERTAS[s.alerta].que_es}")
                if s.visible:
                    st.caption(f"{s.pct:.0f} % · margen de error {s.ic_inf:.0f}–"
                               f"{s.ic_sup:.0f} % · base de {s.n} cuidadores")
            for texto in va.explicaciones(lista):
                st.caption(texto)
            st.caption(ac_est.NOTA_AZAR)
    return any(s.alerta == cat.ANIMO for s in lista)


def _panel(ac, rol: str, filtros: dict) -> bool:
    try:
        return bool(render_panel(ac, rol, filtros))
    except Exception:                                      # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo dibujar el panel de cuidadores")
        return False


def figura_bandas(b: dict):
    import plotly.graph_objects as go
    fig = go.Figure()
    for i, (etiqueta, pct) in enumerate(zip(b["etiquetas"], b["pct"])):
        fig.add_trace(go.Bar(x=[pct], y=[""], orientation="h", name=etiqueta,
                             marker_color=COLORES_BANDAS[i], text=[f"{pct:.0f} %"],
                             textposition="inside", insidetextanchor="middle",
                             hovertemplate=f"<b>{etiqueta}</b><br>%{{x:.0f}} %<extra></extra>"))
    fig.update_layout(barmode="stack", height=150, showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.6, x=0),
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(range=[0, 100], visible=False), yaxis=dict(visible=False))
    return fig


def _selector(ac, columna: str, colegio: str = TODOS) -> str:
    opciones = grupos(ac, columna, colegio if columna == "Grado" else TODOS)
    clave = f"cuid_com_{columna.lower()}"
    if not opciones:
        return TODOS
    if columna == "Colegio":
        estado.sembrar(clave, estado.COLEGIO, [TODOS] + opciones)
    if st.session_state.get(clave, TODOS) not in [TODOS] + opciones:
        st.session_state[clave] = TODOS
    etiqueta = "Colegio" if columna == "Colegio" else "Grado (del hijo o la hija)"
    valor = st.sidebar.selectbox(etiqueta, [TODOS] + opciones, key=clave)
    if columna == "Colegio" and (
            valor != TODOS or st.session_state.get(estado.COLEGIO, TODOS) in [TODOS] + opciones):
        estado.guardar(estado.COLEGIO, valor)
    return valor


def colegio_de_la_url(ac) -> str | None:
    """`?colegio=LauV`, si ese colegio tiene cifras de cuidadores; si no, None."""
    try:
        pedido = str(st.query_params.get("colegio", "")).strip()
    except Exception:                                      # noqa: BLE001
        return None
    if not pedido or ac is None:
        return None
    for codigo in grupos(ac, "Colegio"):
        if codigo.lower() == pedido.lower():
            return codigo
    return None


def avisos_internos() -> list[str]:
    """Avisos de textos y ruta pendientes: solo en el modo completo, nunca en público."""
    try:
        from src.core import modo as modo_app
    except Exception:                                      # noqa: BLE001
        return []
    if modo_app.modo() != modo_app.COMPLETO:
        return []
    salida = []
    if not cc.TEXTOS_APROBADOS:
        salida.append(cc.TEXTOS_PENDIENTES)
    if not cc.RUTAS_VALIDADAS:
        salida.append(ac_est.RUTA_PENDIENTE)
    return salida


def render_comunidad(ac) -> None:
    """Vista comunidad: `ac` es el análisis preparado o la corrida publicada."""
    st.subheader("👪 Cuidadores · para colegios, familias y el municipio")
    st.caption("Cómo están quienes cuidan, qué significa y qué se puede hacer. "
               "Nada individual, nunca.")
    if ac is None or getattr(ac.cuidador, "n", 0) < cat.MIN_GROUP_N:
        st.info(cc.NO_PUBLICADO, icon="⏳")
        return
    estado.sembrar("cuid_com_rol", estado.ROL, list(cc.ROLES))
    rol = st.radio("Estoy viendo esto como", list(cc.ROLES), format_func=lambda r: cc.ROLES[r],
                   horizontal=True, key="cuid_com_rol")
    estado.guardar(estado.ROL, rol)
    st.sidebar.markdown("### Cuidadores · vista comunidad")
    colegio = _selector(ac, "Colegio") if ve_colegios(rol) else TODOS
    grado = _selector(ac, "Grado", colegio)
    filtros = {"colegio": colegio, "grado": grado}

    st.markdown(f"#### Cómo están los cuidadores · {etiqueta_filtro(filtros)}")
    n = n_grupo(ac, filtros)
    if n is None:
        st.info(cc.SIN_SUBGRUPO, icon="ℹ️")
    else:
        st.caption(f"{n} cuidadores en estas cifras. {cc.AVISO_SIN_OLAS}")

    panel_dibujado = _panel(ac, rol, filtros)
    fichas = tarjetas(ac, rol, filtros, panel_dibujado=panel_dibujado)
    if fichas:
        for col, t in zip(st.columns(len(fichas)), fichas):
            with col, st.container(border=True):
                st.markdown(f"**{t.titulo}**")
                st.markdown(f"## {t.cifra}")
                st.caption(t.etiqueta)
                st.markdown(f"**Qué significa:** {t.significa}")
                st.markdown(f"**Qué hacer:** {t.accion}")
                if t.detalle:
                    st.caption(t.detalle)
    else:
        st.info("Aún no hay indicadores con base suficiente para este grupo.", icon="ℹ️")

    st.markdown("#### Comparar entre grupos")
    dimensiones = ["Grado"] + (["Colegio"] if ve_colegios(rol) else [])
    izq, der = st.columns(2)
    with izq:
        dimension = st.radio("Comparar por", dimensiones, horizontal=True,
                             key="cuid_com_dimension")
    with der:
        indicador = st.selectbox("Indicador", comparables(rol),
                                 format_func=lambda k: INDICADORES[k]["etiqueta"].capitalize(),
                                 key="cuid_com_indicador")
    tabla = prevalencia_por(ac, indicador, dimension, filtros)
    if tabla.empty:
        st.info("No hay grupos con suficientes cuidadores para comparar.", icon="ℹ️")
    else:
        st.plotly_chart(figura_comparativa(tabla, INDICADORES[indicador]["etiqueta"].capitalize()),
                        width="stretch", key="cuid_com_comparativa")
        st.caption("Las líneas verticales son el margen de error (intervalo de Wilson al 95 %). "
                   "Se compara, no se ranquea.")
    sin_cifra = grupos_sin_cifra(ac, indicador, dimension, filtros)
    if sin_cifra:
        st.caption(f"Sin cifra: {', '.join(sin_cifra)}. {cc.CIFRAS_PEQUENAS}")

    b = bandas_hijo(ac, filtros)
    if b:
        st.markdown(f"#### {cc.MENSAJES['hijo'].titulo} · {b['n']} niños")
        st.plotly_chart(figura_bandas(b), width="stretch", key="cuid_com_bandas")

    with st.container(border=True):
        st.markdown(f"#### 🆘 {cc.TITULO_RUTA}")
        for nombre, detalle in cc.ruta(rol):
            st.markdown(f"- **{nombre}** — {detalle}")
        for aviso in avisos_internos():
            st.caption(f"⚠️ {aviso}")

    st.warning(cc.AVISO_TAMIZAJE, icon="⚠️")
    with st.expander("Sobre estas cifras"):
        for aviso in (cc.AVISO_EPDS, cc.AVISO_APOYO, cc.AVISO_MINIMO, cc.AVISO_SIN_OLAS):
            st.caption(f"· {aviso}")

    _boton_una_pagina(ac, rol, filtros)
    if ve_colegios(rol):
        _seccion_informes(ac, rol, colegio)


@st.cache_data(show_spinner="Preparando el PDF…", max_entries=64)
def _pdf_de(html: str) -> bytes | None:
    from src.ui.views.cuidadores_informe import a_pdf
    return a_pdf(html)


def _boton_una_pagina(ac, rol: str, filtros: dict) -> None:
    from src.ui.views.cuidadores_informe import informe_una_pagina_html
    html = informe_una_pagina_html(ac, rol, filtros)
    pdf = _pdf_de(html)
    base = f"resumen_cuidadores_{rol}"
    for clave in ("colegio", "grado"):
        if privacidad.activo(filtros.get(clave, TODOS)):
            base += f"_{filtros[clave]}"
    if pdf:
        st.download_button("⬇️ Descargar resumen de una página (PDF)", data=pdf,
                           file_name=f"{base}.pdf", mime="application/pdf", type="primary",
                           key="cuid_com_descarga")
    else:
        st.download_button("⬇️ Descargar resumen de una página", data=html,
                           file_name=f"{base}.html", mime="text/html", type="primary",
                           key="cuid_com_descarga")
        st.caption("Se abre en el navegador; desde ahí se imprime o se guarda como PDF.")


def _seccion_informes(ac, rol: str, colegio: str) -> None:
    from src.ui.views import cuidadores_informe as inf
    st.markdown("#### 🖨️ Informes para imprimir")
    st.caption("Se descargan como página web: al abrirla en el navegador trae el botón "
               "«Imprimir», desde el que también se guarda como PDF.")
    codigos = grupos(ac, "Colegio")
    izq, der = st.columns(2)
    with izq:
        if codigos:
            indice = codigos.index(colegio) if colegio in codigos else 0
            elegido = st.selectbox("Informe del colegio", codigos, index=indice,
                                   key="cuid_inf_colegio")
            st.download_button("⬇️ Descargar informe del colegio",
                               data=inf.informe_colegio_html(ac, elegido),
                               file_name=f"informe_cuidadores_{elegido}.html", mime="text/html",
                               key="cuid_inf_desc_colegio")
        else:
            st.info("Ningún colegio tiene suficientes cuidadores para un informe.", icon="ℹ️")
    with der:
        if rol == "municipio":
            st.markdown("**Informe para la Secretaría**")
            st.download_button("⬇️ Descargar informe para la Secretaría",
                               data=inf.informe_secretaria_html(ac),
                               file_name="informe_cuidadores_secretaria.html", mime="text/html",
                               key="cuid_inf_desc_secretaria")


# ══ Despliegue público ═════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def _corrida_vigente() -> int | None:
    try:
        from src.cuidadores import lectura
        return lectura.id_corrida_vigente()
    except Exception:                                      # noqa: BLE001
        return None


@st.cache_resource(show_spinner="Leyendo los resultados publicados de cuidadores…")
def _leer_publicado(_clave: str):
    from src.cuidadores import lectura
    return lectura.cargar_desde_supabase()[0]


def publicado():
    """La corrida publicada de cuidadores, o None (sin credenciales, sin corrida o sin red)."""
    try:
        from src.cuidadores import lectura
        if not lectura.disponible():
            return None
        return _leer_publicado(f"corrida-{_corrida_vigente()}")
    except Exception:                                      # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo leer la corrida de cuidadores")
        return None


def render_publico() -> None:
    """Página de Cuidadores en el despliegue público: solo la corrida publicada."""
    ac = publicado()
    if ac is None:
        st.title("👪 Cuidadores 360")
        st.info(cc.NO_PUBLICADO, icon="⏳")
        return
    estado.aplicar_colegio_de_url(colegio_de_la_url(ac))
    render_comunidad(ac)
```

- [ ] **Step 4: Implementar los informes**

`src/ui/views/cuidadores_informe.py`:

```python
"""
Informes imprimibles de Cuidadores 360 — colegio, Secretaría y resumen de una página.

Mismo formato que los de estudiantes (`estudiantes_informe`: hoja HTML con
botón «Imprimir», y el resumen de una página en PDF con WeasyPrint o, si
falla, en HTML). Las cifras salen de las funciones de `cuidadores_comunidad`,
así que el informe no puede decir algo distinto de la pantalla.

Reglas:
  · Solo agregados de grupos con 10 o más cuidadores distintos; nunca casos.
  · El informe del colegio se compara con el total del municipio, nunca con
    otro colegio, y no trae la señal de autolesión (solo el estado general).
  · El de la Secretaría trae «Ánimo» por colegio (estado y %) y la autolesión
    solo como cifra de todo el municipio.
  · El resumen de una página cabe en una hoja carta también en el peor caso
    (rol municipio con la lista máxima de grupos en «Prioridad»).
  · Los textos vienen de `comunidad_catalogo`. La IA no redacta nada.
"""
from __future__ import annotations

import logging
from datetime import date
from html import escape

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import estudiantes_alertas as va
from src.ui.views import estudiantes_informe as inf_est

COLUMNAS_TABLA = {"castigo": "Castigo físico", "apoyo_familia": "Poco apoyo de la familia",
                  "hijo_alto": "Hijo con dificultades altas", "animo": "Ánimo bajo"}
MAX_TARJETAS_PAGINA = 4


def _e(texto) -> str:
    return escape(str(texto), quote=True)


def fecha_larga(d: date | None = None) -> str:
    return inf_est.fecha_larga(d)


def a_pdf(html: str) -> bytes | None:
    """PDF con WeasyPrint; None si falta la librería (la vista entrega el HTML)."""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception:                                      # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo generar el PDF de cuidadores")
        return None


def _comparar(p: dict, m: dict) -> str:
    return inf_est.comparar(p, m) if p and m else ""


def _tarjeta_html(ac, t: vc.Tarjeta, filtros: dict, con_municipio: bool) -> str:
    cuerpo = f'<p class="cifra">{_e(t.cifra)}</p><p class="etiqueta">{_e(t.etiqueta)}</p>'
    if t.suprimida:
        cuerpo += f'<p class="margen">{_e(cc.CIFRAS_PEQUENAS)}</p>'
    else:
        indicador = vc.INDICADOR_TARJETA.get(t.clave)
        if indicador and con_municipio:
            comp = _comparar(vc.proporcion(ac, indicador, filtros),
                             vc.proporcion(ac, indicador, {}))
            if comp:
                cuerpo += (f'<span class="chip chip-{comp}">'
                           f'{_e(inf_est.COMPARACION_TEXTO[comp])}</span>')
        if t.detalle:
            cuerpo += f'<p class="margen">{_e(t.detalle)}</p>'
    return (f'<article class="tarjeta"><h3>{_e(t.titulo)}</h3>{cuerpo}'
            f'<p class="significa"><b>Qué significa.</b> {_e(t.significa)}</p>'
            f'<p class="accion"><b>Qué hacer.</b> {_e(t.accion)}</p></article>')


def _tabla(ac, columna: str, indicadores: list[str], filtros: dict, titulo: str,
           nota: str = "") -> str:
    """Grupos × indicadores, cada celda comparada con el total del municipio."""
    indicadores = [k for k in indicadores if vc.proporcion(ac, k, {})]
    tablas = {k: vc.prevalencia_por(ac, k, columna, filtros) for k in indicadores}
    grupos: list[str] = []
    for t in tablas.values():
        for g in t["grupo"].astype(str):
            if g not in grupos:
                grupos.append(g)
    if not grupos:
        return ""
    grupos = vc._ordenar(columna, grupos)
    ref = {k: vc.proporcion(ac, k, {}) for k in indicadores}
    cabecera = "".join(f"<th>{_e(COLUMNAS_TABLA[k])}</th>" for k in indicadores)
    cuerpo = ""
    for g in grupos:
        celdas = ""
        for k in indicadores:
            sel = tablas[k][tablas[k]["grupo"].astype(str) == g]
            p = ({} if sel.empty else dict(pct=float(sel.iloc[0]["pct"]),
                                           ic_inf=float(sel.iloc[0]["ic_inf"]),
                                           ic_sup=float(sel.iloc[0]["ic_sup"]),
                                           n=int(sel.iloc[0]["n"])))
            celdas += inf_est._celda(p, ref[k])
        cuerpo += f'<tr><th scope="row">{_e(g)}</th>{celdas}</tr>'
    total = "".join(f'<td class="total">{ref[k]["pct"]:.0f} %</td>' for k in indicadores)
    return (f'<section class="bloque"><h2>{_e(titulo)}</h2><div class="desliza">'
            f'<table class="comparativa"><thead><tr><th></th>{cabecera}</tr></thead>'
            f'<tbody>{cuerpo}</tbody><tfoot><tr><th scope="row">Total del municipio</th>'
            f'{total}</tr></tfoot></table></div><p class="nota">Porcentaje del grupo y, debajo, '
            "su margen de error. ▲ más alto y ▼ más bajo que el total del municipio. Se "
            "compara, no se ranquea." + (f" {_e(nota)}" if nota else "") + "</p></section>")


def _ruta(rol: str) -> str:
    filas = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in cc.ruta(rol))
    return f'<section class="ruta"><h2>{_e(cc.TITULO_RUTA)}</h2><ul>{filas}</ul></section>'


def _avisos() -> str:
    textos = [cc.AVISO_TAMIZAJE, inf_est.NOTA_COMPARACION, cc.AVISO_EPDS, cc.AVISO_APOYO,
              cc.AVISO_MINIMO, cc.AVISO_SIN_OLAS]
    return '<footer class="avisos">' + "".join(f"<p>{_e(t)}</p>" for t in textos) + "</footer>"


def _documento(titulo: str, cuerpo: str) -> str:
    return inf_est._documento(titulo, cuerpo, va.CSS_INFORME)


def _encabezado(titulo: str, meta: str, marca: str) -> str:
    return inf_est._encabezado(marca, titulo, meta)


def informe_colegio_html(ac, colegio: str, fecha: date | None = None) -> str:
    """Informe de un colegio. ValueError si el colegio no tiene cifras de cuidadores."""
    if colegio not in vc.grupos(ac, "Colegio"):
        raise ValueError(f"El colegio {colegio} no tiene resultados de cuidadores que se puedan "
                         "mostrar.")
    filtros = {"colegio": colegio, "grado": vc.TODOS}
    panel = vc.panel_html(ac, "colegio", filtros)
    fichas = vc.tarjetas(ac, "colegio", filtros, panel_dibujado=bool(panel))
    n = vc.n_grupo(ac, filtros)
    meta = f"{n} cuidadores respondieron · {fecha_larga(fecha)}" if n else fecha_larga(fecha)
    cuerpo = (_encabezado(colegio, meta,
                          "Observatorio 360 · Cuidadores · Informe para el colegio")
              + '<p class="leer">Cada resultado trae la cifra de los cuidadores del colegio, cómo '
                "se compara con el total del municipio y qué puede hacer el colegio. Son cifras "
                "del grupo: ningún dato corresponde a una persona.</p>"
              + panel + '<h2>Resultados y qué hacer</h2><div class="tarjetas">'
              + "".join(_tarjeta_html(ac, t, filtros, True) for t in fichas) + "</div>"
              + _tabla(ac, "Grado", ["castigo", "apoyo_familia", "hijo_alto", "animo"], filtros,
                       "Por grado en el colegio",
                       nota=f"Los grados con menos de {cat.MIN_GROUP_N} cuidadores no se "
                            "muestran.")
              + _ruta("colegio") + _avisos())
    return _documento(f"Informe Cuidadores 360 · {colegio}", cuerpo)


def informe_secretaria_html(ac, fecha: date | None = None) -> str:
    """Informe para la Secretaría: total del municipio, señales y comparación entre grupos."""
    if ac is None or getattr(ac.cuidador, "n", 0) < cat.MIN_GROUP_N:
        raise ValueError("No hay resultados de cuidadores con base suficiente.")
    panel = vc.panel_html(ac, "municipio", {})
    fichas = vc.tarjetas(ac, "municipio", {}, panel_dibujado=bool(panel))
    meta = (f"{vc.n_grupo(ac, {})} cuidadores · {len(vc.grupos(ac, 'Colegio'))} colegios con "
            f"resultados · {fecha_larga(fecha)}")
    indicadores = list(COLUMNAS_TABLA)
    cuerpo = (_encabezado("Chía · total del municipio", meta,
                          "Observatorio 360 · Cuidadores · Informe para la Secretaría")
              + '<p class="leer">Primero el total del municipio y qué hacer desde la política '
                "pública; después, cómo se ubica cada colegio y cada grado frente a ese total. "
                "Son cifras de grupo: ningún dato corresponde a una persona.</p>"
              + panel + '<h2>Resultados y qué hacer</h2><div class="tarjetas">'
              + "".join(_tarjeta_html(ac, t, {}, False) for t in fichas) + "</div>"
              + vc.tabla_secretaria_html(ac)
              + _tabla(ac, "Colegio", indicadores, {}, "Por colegio")
              + _tabla(ac, "Grado", indicadores, {}, "Por grado")
              + _ruta("municipio") + _avisos())
    return _documento("Informe Cuidadores 360 · Secretaría", cuerpo)


def informe_una_pagina_html(ac, rol: str, filtros: dict | None = None,
                            fecha: date | None = None) -> str:
    """Hoja de una página con lo esencial del grupo que está en pantalla."""
    filtros = filtros or {}
    if ac is None:
        raise ValueError("No hay resultados de cuidadores.")
    con_municipio = vc.hay_filtro(filtros)
    caja = vc.panel_html(ac, rol, filtros, compacto=True)
    fichas = vc.tarjetas(ac, rol, filtros,
                         panel_dibujado=bool(caja) and rol != "familia")[:MAX_TARJETAS_PAGINA]
    n = vc.n_grupo(ac, filtros)
    partes_meta = ([f"{n} cuidadores"] if n else []) + [f"Para: {cc.ROLES.get(rol, rol)}",
                                                        fecha_larga(fecha)]
    if fichas:
        tiles = "".join(
            f'<div class="tile"><h3>{_e(t.titulo)}</h3><p class="cifra">{_e(t.cifra)}</p>'
            f'<p class="etiqueta">{_e(t.etiqueta)}</p>'
            + (f'<p class="margen">{_e(cc.CIFRAS_PEQUENAS if t.suprimida else t.detalle)}</p>'
               if (t.suprimida or t.detalle) else "")
            + f'<div class="hacer"><b>Qué hacer:</b> {_e(t.accion)}</div></div>'
            for t in fichas)
        contenido = caja + f'<h2>Lo más importante y qué hacer</h2><div class="tiles">{tiles}</div>'
    else:
        contenido = caja + f"<p>{_e(cc.SIN_SUBGRUPO)}</p>"
    ruta = "".join(f"<li><b>{_e(a)}</b> — {_e(b)}</li>" for a, b in cc.ruta(rol))
    avisos = [cc.AVISO_TAMIZAJE] + ([inf_est.NOTA_COMPARACION] if con_municipio else [])
    cuerpo = ('<div class="banda"><div class="marca">Observatorio 360 · Cuidadores · '
              f'Resumen de una página</div><h1>{_e(vc.etiqueta_filtro(filtros))}</h1>'
              f'<div class="meta">{_e(" · ".join(partes_meta))}</div></div>'
              + contenido
              + f'<div class="ruta"><h2>{_e(cc.TITULO_RUTA)}</h2><ul>{ruta}</ul></div>'
              + '<div class="pie">' + "".join(f"<p>{_e(t)}</p>" for t in avisos) + "</div>")
    return ("<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
            f"<title>Resumen Cuidadores 360 · {_e(vc.etiqueta_filtro(filtros))}</title>"
            f"<style>{inf_est._CSS_PAGINA}{va.CSS_PAGINA}</style></head><body>{cuerpo}"
            "</body></html>")
```

- [ ] **Step 5: Correr las pruebas**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_comunidad.py -q`
Expected: `49 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/ui/views/cuidadores_comunidad.py src/ui/views/cuidadores_informe.py tests/test_cuidadores_comunidad.py
git commit -m "feat(cuidadores): vista de comunidad, señales del adulto por rol e informes

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Pruebas de los informes y generador con auditoría previa

**Files:**
- Create: `tests/test_cuidadores_informe.py`
- Create: `scripts/generar_informes_cuidadores.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_informe.py`:

```python
"""Cuidadores 360 · informes del colegio y de la Secretaría y resumen de una página."""
import pandas as pd
import pytest

from src.cuidadores import alertas
from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.ui.views import cuidadores_informe as inf
from src.ui.views import estudiantes_alertas as va
from tests import cuidadores_comunidad_datos as datos
from tests import cuidadores_sinteticos as cs


@pytest.fixture(scope="module")
def ac():
    return datos.con_senales(datos.preparado())


def _limpio(html: str) -> None:
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in html
    assert "casos" not in html.lower() or "casos o no casos" in html.lower()
    assert "suicid" not in html.lower()


def test_informe_del_colegio(ac):
    html = inf.informe_colegio_html(ac, "LauV")
    _limpio(html)
    assert "LauV" in html and cc.TITULO_RUTA in html
    assert cc.ESTADO_GENERAL_COLEGIO in html
    assert cc.ALERTAS[cat.AUTOLESION].nombre not in html
    assert "Prioridad" in html                          # LauV en «Prioridad» de ánimo
    for otro in ("JJC", "SJMEB"):
        assert otro not in html                         # un rector no ve a los demás


def test_un_colegio_sin_cifras_no_tiene_informe(ac):
    with pytest.raises(ValueError):
        inf.informe_colegio_html(ac, "CdP")


def test_informe_de_la_secretaria(ac):
    html = inf.informe_secretaria_html(ac)
    _limpio(html)
    assert cc.ALERTAS[cat.AUTOLESION].nombre in html            # solo el total
    assert cc.NOTA_SOLO_MUNICIPIO in html
    assert "Por colegio" in html and "Por grado" in html
    tabla = inf.vc.tabla_secretaria_html(ac)
    assert tabla and cc.ALERTAS[cat.AUTOLESION].nombre_corto not in tabla


@pytest.mark.parametrize("rol", ["colegio", "familia", "municipio"])
def test_resumen_de_una_pagina_por_rol(ac, rol):
    html = inf.informe_una_pagina_html(ac, rol, {})
    _limpio(html)
    assert cc.TITULO_RUTA in html
    if rol == "familia":
        caja = html.split("<body>")[1].split("Lo más importante")[0]
        assert cc.AUTOCUIDADO_FAMILIA in caja and "%" not in caja
        for palabra in ("daño", "autoles", "muerte"):
            assert palabra not in html.lower()


def _peor_caso(ac):
    """Municipio sin filtro, con todos los colegios y grados en «Prioridad»."""
    colegios = [f"Colegio número {i:02d}" for i in range(14)]
    filas = [datos._r("animo", "total", "Todos", 25.0, alertas.REFERENCIA, n=700)]
    filas += [datos._r("animo", "Colegio", c, 40.0, alertas.PRIORIDAD) for c in colegios]
    filas += [datos._r("animo", "Grado", g, 40.0, alertas.PRIORIDAD) for g in cat.GRADOS_ESTUDIO]
    filas += [datos._r("autolesion", "total", "Todos", 11.0, alertas.REFERENCIA, n=700)]
    return datos.con_senales(ac, alertas.ordenar(pd.DataFrame(filas,
                                                              columns=alertas.COLUMNAS_TABLA)))


def test_el_peor_caso_recorta_las_listas(ac):
    html = inf.informe_una_pagina_html(_peor_caso(ac), "municipio", {})
    assert f"y {14 - va.MAX_NOMBRES_PAGINA} más" in html


@pytest.mark.parametrize("rol,filtros", [("municipio", {}), ("colegio", {"colegio": "LauV"}),
                                         ("familia", {"grado": "Quinto"})])
def test_el_peor_caso_cabe_en_una_pagina(ac, rol, filtros):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML
    html = inf.informe_una_pagina_html(_peor_caso(ac), rol, filtros)
    assert len(HTML(string=html).render().pages) == 1
    assert inf.a_pdf(html)[:4] == b"%PDF"


def test_sin_weasyprint_el_pdf_es_none(monkeypatch):
    import builtins
    original = builtins.__import__

    def falla(nombre, *a, **k):
        if nombre == "weasyprint":
            raise ImportError("sin weasyprint")
        return original(nombre, *a, **k)
    monkeypatch.setattr(builtins, "__import__", falla)
    assert inf.a_pdf("<p>x</p>") is None


# ── generador de informes: audita antes de escribir ────────────────────────
def test_el_generador_aborta_sin_escribir_si_la_auditoria_falla(tmp_path, monkeypatch):
    from scripts import generar_informes_cuidadores as gen
    from src.cuidadores import publicar
    monkeypatch.setattr(gen, "cargar", lambda: (datos.preparado(), "archivos"))
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["cuidador · algo delata"])
    assert gen.main([str(tmp_path)]) == 2
    assert list(tmp_path.iterdir()) == []


def test_el_generador_escribe_si_la_auditoria_pasa(tmp_path, monkeypatch):
    from scripts import generar_informes_cuidadores as gen
    monkeypatch.setattr(gen, "cargar", lambda: (datos.preparado(), "archivos"))
    assert gen.main([str(tmp_path)]) == 0
    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert "informe_cuidadores_secretaria.html" in nombres
    assert "informe_cuidadores_LauV.html" in nombres
    for p in tmp_path.iterdir():
        _limpio(p.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Correrlas y ver que fallan las del generador**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_informe.py -q`
Expected: FAIL en las dos pruebas del generador (`ModuleNotFoundError: No module named 'scripts.generar_informes_cuidadores'`); las de los informes pasan (los PDF se omiten en 3.13, sin WeasyPrint).

- [ ] **Step 3: Implementar el generador**

`scripts/generar_informes_cuidadores.py`:

```python
"""
Genera los informes imprimibles de Cuidadores 360 — Observatorio 360.

Un HTML por colegio con cifras de cuidadores y uno para la Secretaría, con las
mismas funciones que la vista de comunidad. Lee la exportación de «Cuidando al
Cuidador» de la carpeta de datos fuente (con la clave local OBS360_CLAVE_HMAC);
si no está, la corrida publicada en Supabase.

Antes de escribir nada corre la misma auditoría que la publicación
(`cuidadores.publicar.verificar_restas`): con un solo hallazgo no se escribe
ningún informe. Por defecto se escribe junto a los datos fuente, no en el
repositorio.

Uso:
    python -m scripts.generar_informes_cuidadores [carpeta_salida]
"""
from __future__ import annotations

import os
import sys

from src.core.rutas import carpeta_datos
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import cuidadores_informe as inf


def cargar():
    """(análisis preparado o corrida publicada, origen)."""
    from src.cuidadores import comunidad, lectura, pipeline
    ruta = pipeline.localizar_formulario()
    if ruta:
        print("Fuente: formulario en disco")
        return comunidad.preparar(pipeline.cargar_y_analizar(ruta)), "archivos"
    publicado, corrida = lectura.cargar_desde_supabase()
    print(f"Fuente: corrida publicada {corrida.get('id') if corrida else None}")
    return publicado, "supabase"


def main(argv: list[str] | None = None) -> int:
    from src.cuidadores import publicar
    argv = sys.argv[1:] if argv is None else argv
    salida = argv[0] if argv else os.path.join(carpeta_datos(), "informes_cuidadores")
    ac, origen = cargar()
    if ac is None:
        print("No hay resultados de cuidadores.")
        return 1
    if origen == "archivos":
        problemas = publicar.verificar_restas(ac)
        if problemas:
            print(f"✗ No se escribió ningún informe: la auditoría encontró {len(problemas)} "
                  "problema(s) de privacidad:\n  - " + "\n  - ".join(problemas[:20]),
                  file=sys.stderr)
            return 2
    os.makedirs(salida, exist_ok=True)
    for codigo in vc.grupos(ac, "Colegio"):
        ruta = os.path.join(salida, f"informe_cuidadores_{codigo}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(inf.informe_colegio_html(ac, codigo))
        print(f"  {codigo} → {ruta}")
    ruta = os.path.join(salida, "informe_cuidadores_secretaria.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(inf.informe_secretaria_html(ac))
    print(f"  Secretaría → {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Correr las pruebas en las dos versiones**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_informe.py -q`
Expected: `10 passed, 3 skipped`.

Run: `"$VENV314/bin/python" -m pytest tests/test_cuidadores_informe.py -q`
Expected: `13 passed` (con WeasyPrint: el peor caso cabe en una página para municipio, colegio y familia).

- [ ] **Step 5: Commit**

```bash
git add tests/test_cuidadores_informe.py scripts/generar_informes_cuidadores.py
git commit -m "feat(cuidadores): generador de informes con auditoría previa

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---
### Task 8: Página local con selector de vista, corrida publicada y página pública con doble llave

**Files:**
- Modify: `src/core/navegacion.py`
- Modify: `main.py`
- Modify (se reescribe entero): `src/ui/cuidadores.py`
- Modify: `src/ui/views/cuidadores_investigador.py`
- Modify (se reescribe entero): `tests/test_navegacion.py`, `tests/test_cuidadores_pagina.py`
- Modify: `tests/test_modo_despliegue.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_navegacion.py` (completo; cambia: `cuidadores_publico` en la prueba de la aprobación, la doble llave, la lista de prohibidos ampliada, la página pública sin corrida y con corrida, y la prueba del investigador sin red):

```python
"""
Pruebas del menú: nombres, orden, qué páginas existen y cuáles ve cada modo.
"""
import os

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


def test_triangulacion_solo_para_investigadores():
    """Fase 5: completo e investigador la ven; comunidad nunca (spec §5.3 y §5.6)."""
    assert nav.PAGINA_TRIANGULACION in nav.DISPONIBLES
    assert nav.PAGINA_TRIANGULACION in nav.menu(COMPLETO)
    assert nav.PAGINA_TRIANGULACION in nav.menu(INVESTIGADOR)
    assert nav.PAGINA_TRIANGULACION not in nav.menu(COMUNIDAD)
    assert nav.PAGINA_TRIANGULACION not in nav.menu("cualquier-cosa")


def test_completo_e_investigador_ven_todas_las_disponibles_en_orden():
    esperado = ["Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360",
                "Chat con IA", "Cargar Datos", "Análisis de tendencias", "Reportes"]
    assert nav.menu(COMPLETO) == esperado
    assert nav.menu(INVESTIGADOR) == esperado


def test_comunidad_solo_ve_paginas_publicas():
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    assert set(nav.PUBLICAS) == {nav.PAGINA_ESTUDIANTES, nav.PAGINA_CUIDADORES}


def test_triangulacion_nunca_es_publica():
    assert nav.PAGINA_TRIANGULACION not in nav.PUBLICAS


def test_triangulacion_sigue_fuera_aunque_cuidadores_sea_publica(monkeypatch):
    _aprobar_cuidadores(monkeypatch)
    assert nav.PAGINA_TRIANGULACION not in nav.menu(COMUNIDAD)


def test_cuidadores_no_es_publica_hasta_la_aprobacion():
    """Existe para investigadores; el público no la ve hasta la aprobación (spec §5.5)."""
    assert nav.CUIDADORES_PUBLICO is False
    assert nav.cuidadores_publico() is False
    assert nav.PAGINA_CUIDADORES in nav.DISPONIBLES
    assert nav.PAGINA_CUIDADORES not in nav.menu(COMUNIDAD)
    assert nav.PAGINA_CUIDADORES not in nav.menu("cualquier-cosa")


def _aprobar_cuidadores(monkeypatch, bandera=True, textos=True, rutas=True):
    from src.cuidadores import comunidad_catalogo as cc
    monkeypatch.setattr(nav, "CUIDADORES_PUBLICO", bandera)
    monkeypatch.setattr(cc, "TEXTOS_APROBADOS", textos)
    monkeypatch.setattr(cc, "RUTAS_VALIDADAS", rutas)


def test_cuando_cuidadores_se_apruebe_comunidad_lo_ve(monkeypatch):
    """Fase 4b: la bandera del equipo Y los textos y la ruta aprobados en el catálogo."""
    monkeypatch.setattr(nav, "DISPONIBLES",
                        nav.DISPONIBLES | {nav.PAGINA_CUIDADORES, nav.PAGINA_TRIANGULACION})
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch, bandera=True, textos=False, rutas=False)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch, bandera=True, textos=True, rutas=False)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch, bandera=False, textos=True, rutas=True)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360", "Cuidadores 360"]
    assert nav.menu(INVESTIGADOR)[:4] == [
        "Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360"]


def test_pagina_inicial_por_modo():
    assert nav.pagina_inicial(COMPLETO) == "Docentes"
    assert nav.pagina_inicial(INVESTIGADOR) == "Estudiantes 360"
    assert nav.pagina_inicial(COMUNIDAD) == "Estudiantes 360"


def test_un_modo_desconocido_se_trata_como_comunidad():
    assert nav.menu("cualquier-cosa") == nav.menu(COMUNIDAD)


PROHIBIDOS_EN_COMUNIDAD = (
    "src.ui.dashboard", "src.ui.chat", "src.ui.upload", "src.ui.reports",
    "src.ui.trends", "src.ai.gemini_client",
    "src.ui.views.estudiantes_investigador",
    "src.ui.cuidadores", "src.ui.views.cuidadores_investigador",
    "src.cuidadores.ingest", "src.cuidadores.pipeline", "src.cuidadores.scoring",
    "src.cuidadores.privacidad", "src.cuidadores.publicar", "src.cuidadores.auditoria",
    "src.cuidadores.comunidad", "src.core.seudonimo",
    "src.ui.triangulacion", "src.ui.views.triangulacion_investigador",
    "src.triangulacion.fuentes", "src.triangulacion.enlace", "src.triangulacion.diadas",
    "src.triangulacion.capa1", "src.triangulacion.pipeline")


def _main_en_comunidad(monkeypatch):
    """Ejecuta main.py en modo comunidad con los módulos prohibidos descargados."""
    import sys
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    monkeypatch.setenv("OBS360_DATOS_DIR", "/ruta/que/no/existe")
    for m in PROHIBIDOS_EN_COMUNIDAD:
        monkeypatch.delitem(sys.modules, m, raising=False)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return AppTest.from_file(os.path.join(raiz, "main.py"), default_timeout=60)


def test_main_en_comunidad_no_importa_modulos_internos(monkeypatch):
    """Arranca main.py de verdad en modo comunidad.

    Puede leer la corrida publicada en Supabase si hay secretos configurados;
    solo garantiza que no lanza excepción y que no se importa ningún módulo
    interno.
    """
    import sys
    at = _main_en_comunidad(monkeypatch).run()
    assert not at.exception
    for m in PROHIBIDOS_EN_COMUNIDAD:
        assert m not in sys.modules, f"{m} se importó en modo comunidad"


def test_comunidad_con_dos_paginas_publicas_muestra_el_selector(monkeypatch):
    """Aprobada pero sin corrida publicada: la página lo dice y no se cae."""
    import sys
    from src.cuidadores import comunidad_catalogo as cc
    from src.cuidadores import lectura
    _aprobar_cuidadores(monkeypatch)
    monkeypatch.setattr(lectura, "disponible", lambda: False)
    at = _main_en_comunidad(monkeypatch).run()
    assert not at.exception
    radio = at.radio(key="nav_pagina")
    assert list(radio.options) == ["Estudiantes 360", "Cuidadores 360"]
    radio.set_value("Cuidadores 360").run()
    assert not at.exception
    assert any(cc.NO_PUBLICADO in i.value for i in at.info)
    for m in PROHIBIDOS_EN_COMUNIDAD:
        assert m not in sys.modules, f"{m} se importó en modo comunidad"


def test_comunidad_con_corrida_de_cuidadores_muestra_solo_la_vista_de_comunidad(monkeypatch):
    import sys
    from src.cuidadores import comunidad_catalogo as cc
    from src.cuidadores import lectura
    from tests import cuidadores_comunidad_datos as datos
    from src.ui.views import cuidadores_comunidad as vc
    _, base = datos.publicado()
    vc._corrida_vigente.clear()
    vc._leer_publicado.clear()
    _aprobar_cuidadores(monkeypatch)
    monkeypatch.setattr(lectura, "disponible", lambda: True)
    monkeypatch.setattr(lectura, "_cliente", lambda: base.cliente(anonimo=True))
    at = _main_en_comunidad(monkeypatch).run()
    at.radio(key="nav_pagina").set_value("Cuidadores 360").run()
    assert not at.exception
    assert at.radio(key="cuid_com_rol").value in cc.ROLES
    assert "src.ui.views.cuidadores_comunidad" in sys.modules
    for m in PROHIBIDOS_EN_COMUNIDAD:
        assert m not in sys.modules, f"{m} se importó en modo comunidad"


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


def test_main_en_investigador_ofrece_cuidadores(monkeypatch, tmp_path):
    """Sin archivos y sin corrida publicada, la página dice que no está publicada."""
    from streamlit.testing.v1 import AppTest
    from src.cuidadores import lectura
    monkeypatch.setattr(lectura, "disponible", lambda: False)
    monkeypatch.setenv("OBS360_MODO", "investigador")
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    at = AppTest.from_file(os.path.join(raiz, "main.py"), default_timeout=120).run()
    assert not at.exception
    radio = at.radio(key="nav_pagina")
    assert "Cuidadores 360" in radio.options
    radio.set_value("Cuidadores 360").run()
    assert not at.exception
    assert any("aún no está publicado" in i.value for i in at.info)


def test_main_en_investigador_ofrece_triangulacion(monkeypatch, tmp_path):
    """Sin archivos (como en el despliegue del equipo), la página lo dice y no falla."""
    from streamlit.testing.v1 import AppTest
    from src.triangulacion import catalogo as cat_tri
    monkeypatch.setenv("OBS360_MODO", "investigador")
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    at = AppTest.from_file(os.path.join(raiz, "main.py"), default_timeout=120).run()
    assert not at.exception
    radio = at.radio(key="nav_pagina")
    assert "Triangulación 360" in radio.options
    radio.set_value("Triangulación 360").run()
    assert not at.exception
    assert any(cat_tri.AVISO_DESPLIEGUE in i.value for i in at.info)
```

`tests/test_cuidadores_pagina.py` (completo; `_pagina` fija el modo y nunca toca la red, y se añaden las pruebas de la 4b):

```python
"""Cuidadores 360 · página: sin archivo, sin clave, con datos sintéticos y con la corrida
publicada (fases 4a y 4b)."""

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.cuidadores import lectura
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import cuidadores_investigador as vi
from tests import cuidadores_sinteticos as cs


def _pagina(monkeypatch, datos: str, clave: str | None, modo: str = "investigador"):
    """La página, en el modo pedido y sin red: sin corrida publicada salvo que se simule."""
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_MODO", modo)
    monkeypatch.setattr(lectura, "disponible", lambda: False)
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    if clave:
        monkeypatch.setenv("OBS360_CLAVE_HMAC", clave)
    else:
        monkeypatch.delenv("OBS360_CLAVE_HMAC", raising=False)
        monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    return AppTest.from_string(
        "from src.ui.cuidadores import render_cuidadores\nrender_cuidadores()\n",
        default_timeout=120)


def test_sin_datos_dice_que_no_esta_publicado(monkeypatch, tmp_path):
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any("aún no está publicado" in i.value for i in at.info)


def test_sin_clave_explica_que_falta(monkeypatch, tmp_path):
    cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    at = _pagina(monkeypatch, str(tmp_path), None).run()
    assert not at.exception
    assert any("OBS360_CLAVE_HMAC" in e.value for e in at.error)


def test_con_datos_muestra_las_pestanas_y_el_filtro_de_ola(monkeypatch, tmp_path):
    cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS
    ola = at.selectbox(key="cuid_ola")
    assert list(ola.options) == ["Todas", "2025", "2026"]
    ola.set_value("2026").run()
    assert not at.exception
    assert any(vi.SOLO_TODAS == c.value for c in at.caption)
    at.radio(key="cuid_marco").set_value(cat.MARCO_NINO).run()
    assert not at.exception
    pantalla = " ".join(str(e.value) for e in at.markdown) + \
        " ".join(str(getattr(d, "value", "")) for d in at.dataframe)
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in pantalla


# ══ Fase 4b: selector de vista y corrida publicada ═════════════════════════
def _archivo(tmp_path):
    cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")


def _texto(at) -> str:
    return " ".join(str(getattr(e, "value", "")) for g in (at.markdown, at.caption, at.info)
                    for e in g)


def test_en_completo_abre_la_vista_de_comunidad(monkeypatch, tmp_path):
    _archivo(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA, modo="completo").run()
    assert not at.exception
    vista = at.radio(key="cuid_audiencia")
    from src.ui.cuidadores import AUDIENCIAS
    assert list(vista.options) == list(AUDIENCIAS.values()) and vista.value == "comunidad"
    assert at.radio(key="cuid_com_rol").value in cc.ROLES
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in _texto(at)
    assert cc.TEXTOS_PENDIENTES in _texto(at)          # aviso interno del modo completo
    vista.set_value("investigador").run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS


def test_en_investigador_abre_la_vista_de_investigadores(monkeypatch, tmp_path):
    _archivo(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA).run()
    assert at.radio(key="cuid_audiencia").value == "investigador"
    at.radio(key="cuid_audiencia").set_value("comunidad").run()
    assert not at.exception
    assert not [s for s in at.selectbox if s.key == "cuid_ola"]   # sin filtro de ola


def test_sin_archivo_lee_la_corrida_publicada(monkeypatch, tmp_path):
    from tests import cuidadores_comunidad_datos as datos
    publicado = datos.publicado()[0]
    at = _pagina(monkeypatch, str(tmp_path), None)
    monkeypatch.setattr(vc, "publicado", lambda: publicado)
    at.run()
    assert not at.exception
    assert any(lectura.AVISO_PUBLICADO in i.value for i in at.info)
    assert [t.label for t in at.tabs] == vi.PESTANAS
    assert not [s for s in at.selectbox if s.key == "cuid_ola"]
    at.radio(key="cuid_audiencia").set_value("comunidad").run()
    assert not at.exception
    assert at.radio(key="cuid_com_rol").value in cc.ROLES


def test_la_fuente_supabase_se_puede_forzar(monkeypatch, tmp_path):
    from tests import cuidadores_comunidad_datos as datos
    _archivo(tmp_path)
    publicado = datos.publicado()[0]
    monkeypatch.setenv("OBS360_FUENTE", "supabase")
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA)
    monkeypatch.setattr(vc, "publicado", lambda: publicado)
    at.run()
    assert not at.exception
    assert any(lectura.AVISO_PUBLICADO in i.value for i in at.info)


def test_la_vista_de_investigadores_lee_conteos_enmascarados():
    assert vi.conteo_legible("<10") == "<10"
    assert vi.conteo_legible(12) == "12" and vi.conteo_legible(4) == "<10"
    from types import SimpleNamespace
    inf = SimpleNamespace(**dict(lectura.INFORME_POR_DEFECTO, filas_archivo=779,
                                 sin_consentimiento="<10", respuestas_repetidas_cuidador=22))
    md = vi.flujo_exclusiones_md(inf)
    assert "Sin consentimiento: <10 → quedan —" in md
```

En `tests/test_modo_despliegue.py`, dentro de `test_el_punto_de_entrada_corta_antes_de_importar_lo_demas`, reemplazar:

```python
    # Cuidadores 360 (fase 4a) solo se enruta después del corte, para investigadores
    assert "src.ui.cuidadores" not in antes and "src.cuidadores" not in antes
    assert "from src.ui.cuidadores import render_cuidadores" in despues
```

por:

```python
    # Cuidadores 360: en público solo la vista de comunidad (fase 4b), leída de la
    # corrida publicada; la página local y la de investigadores, después del corte
    assert "from src.ui.views.cuidadores_comunidad import render_publico" in antes
    assert "src.ui.cuidadores" not in antes and "src.cuidadores" not in antes
    assert "from src.ui.cuidadores import render_cuidadores" in despues
```

- [ ] **Step 2: Correrlas y ver que fallan**

Run: `.venv/bin/python -m pytest tests/test_navegacion.py tests/test_cuidadores_pagina.py tests/test_modo_despliegue.py -q`
Expected: FAIL en `cuidadores_publico` (no existe), en la página pública con corrida, en el corte de `main.py` y en las pruebas del selector «Vista» (`cuid_audiencia`).

- [ ] **Step 3: Navegación con doble llave**

En `src/core/navegacion.py`, reemplazar:

```python
# Cuidadores es pública solo cuando el equipo aprueba sus textos y rutas y hay
# una corrida de cuidadores publicada (spec §5.5). Lo cambia la fase 4b.
CUIDADORES_PUBLICO = False
```

por:

```python
# Cuidadores es pública solo cuando el equipo aprueba sus textos y rutas y hay
# una corrida de cuidadores publicada (spec §5.5). Dos llaves, las dos a mano:
#   1. `CUIDADORES_PUBLICO`: la pone en True el equipo, en un commit propio,
#      DESPUÉS de publicar la corrida con `--publicar-ya`.
#   2. `comunidad_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` (ver
#      `cuidadores_publico`).
# La navegación no consulta Supabase: el arranque nunca depende de la red. Si
# aun así no hubiera corrida, la página pública lo dice («todavía no tiene
# resultados publicados») en vez de fallar.
CUIDADORES_PUBLICO = False
```

y reemplazar:

```python
def menu(modo: str) -> list[str]:
    """Páginas del menú en este modo, en orden."""
    if _es_publico(modo):
        visibles = [p for p in PUBLICAS
                    if p != PAGINA_CUIDADORES or CUIDADORES_PUBLICO]
```

por:

```python
def cuidadores_publico() -> bool:
    """¿Cuidadores 360 aparece en el despliegue público?

    Solo si el equipo puso `CUIDADORES_PUBLICO = True` y el catálogo de textos de
    la comunidad está aprobado (textos y ruta). Si el catálogo falta o falla al
    importarse, no: ante la duda, la página no se publica.
    """
    if CUIDADORES_PUBLICO is not True:
        return False
    try:
        from src.cuidadores import comunidad_catalogo as cc
    except Exception:                                      # noqa: BLE001
        return False
    return (getattr(cc, "TEXTOS_APROBADOS", False) is True
            and getattr(cc, "RUTAS_VALIDADAS", False) is True)


def menu(modo: str) -> list[str]:
    """Páginas del menú en este modo, en orden."""
    if _es_publico(modo):
        visibles = [p for p in PUBLICAS
                    if p != PAGINA_CUIDADORES or cuidadores_publico()]
```

- [ ] **Step 4: Rama pública en `main.py`**

Reemplazar:

```python
    if _pagina_publica == nav.PAGINA_ESTUDIANTES:
        from src.ui.estudiantes import render_estudiantes
        render_estudiantes()
    st.stop()
```

por:

```python
    if _pagina_publica == nav.PAGINA_ESTUDIANTES:
        from src.ui.estudiantes import render_estudiantes
        render_estudiantes()
    elif _pagina_publica == nav.PAGINA_CUIDADORES:
        # Solo la vista de comunidad, leída de la corrida publicada: nunca la
        # carga del formulario, la vista de investigadores ni la página local.
        from src.ui.views.cuidadores_comunidad import render_publico
        render_publico()
    st.stop()
```

y reemplazar el comentario de la rama local:

```python
elif page == nav.PAGINA_CUIDADORES:
    # Fase 4a: solo la vista de investigadores, con los archivos en local. Nunca
    # se importa en el despliegue público, que se corta arriba.
```

por:

```python
elif page == nav.PAGINA_CUIDADORES:
    # Vistas de comunidad y de investigadores, con los archivos en local o la
    # corrida publicada. El despliegue público se corta arriba y usa solo
    # `cuidadores_comunidad.render_publico`.
```

- [ ] **Step 5: La página local**

`src/ui/cuidadores.py` (completo):

```python
"""
Página «Cuidadores 360» en los modos completo e investigador.

Un selector «Vista» (como en Estudiantes) decide qué se arma:
  · «Colegios, familias y municipio»: la vista de comunidad
    (`views/cuidadores_comunidad`), con el análisis de todas las olas ya
    preparado (`cuidadores.comunidad.preparar`), igual que lo que se publica.
  · «Equipo investigador»: la vista de investigadores de la fase 4a, con el
    filtro de ola que solo existe aquí.

Dos fuentes, en este orden:
  1. La exportación de «Cuidando al Cuidador» en la carpeta de datos fuente
     (`core.rutas`), con la clave local `OBS360_CLAVE_HMAC`.
  2. La corrida publicada en Supabase (`cuidadores.lectura`): es lo que ve el
     despliegue del equipo, que no tiene archivos. Solo agregados, de todas las
     olas. `OBS360_FUENTE=supabase` la fuerza aunque haya archivos.
Sin ninguna de las dos, dice que Cuidadores aún no está publicado y no falla.

El despliegue público nunca importa este módulo (`main.py` corta antes): allí
la página es `cuidadores_comunidad.render_publico`.
"""
from __future__ import annotations

import os

import streamlit as st

from src.core import modo as modo_app
from src.cuidadores import catalog as cat

TODAS = "Todas"
AUDIENCIAS = {"comunidad": "Colegios, familias y municipio",
              "investigador": "Equipo investigador"}
NO_PUBLICADO = ("Cuidadores aún no está publicado. Esta página muestra los resultados "
                "solo en la máquina que procesa el formulario o cuando hay una corrida de "
                "cuidadores publicada.")


@st.cache_resource(show_spinner="Leyendo el formulario de cuidadores…")
def _carga(firma: tuple):
    from src.cuidadores import ingest
    return ingest.cargar(firma[0])


@st.cache_resource(show_spinner="Puntuando y analizando…")
def _analisis(firma: tuple, ola: str | None):
    from src.cuidadores import pipeline
    return pipeline.analizar(_carga(firma), ola=ola)


@st.cache_resource(show_spinner="Preparando la vista de comunidad…")
def _preparado(firma: tuple):
    from src.cuidadores import comunidad
    return comunidad.preparar(_analisis(firma, None))


def _vista() -> str:
    defecto = getattr(modo_app, "audiencia_por_defecto", None)
    inicial = defecto() if callable(defecto) else "comunidad"
    opciones = list(AUDIENCIAS)
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Cuidadores 360**")
        return st.radio("Vista", opciones,
                        index=opciones.index(inicial) if inicial in opciones else 0,
                        format_func=lambda k: AUDIENCIAS[k], key="cuid_audiencia")


def _sin_datos() -> None:
    st.title("👪 Cuidadores 360")
    st.info(NO_PUBLICADO, icon="⏳")


def _desde_supabase(vista: str) -> None:
    from src.cuidadores import lectura
    from src.ui.views import cuidadores_comunidad as vc
    publicado = vc.publicado()
    if publicado is None:
        _sin_datos()
        return
    st.sidebar.caption("Fuente: corrida publicada")
    st.info(lectura.AVISO_PUBLICADO, icon="🗄️")
    if vista == "comunidad":
        from src.ui import estado
        estado.aplicar_colegio_de_url(vc.colegio_de_la_url(publicado))
        vc.render_comunidad(publicado)
    else:
        from src.ui.views.cuidadores_investigador import render_investigador
        render_investigador(publicado)


def render_cuidadores() -> None:
    from src.core.seudonimo import ClaveAusente
    from src.cuidadores import pipeline

    vista = _vista()
    forzada = os.environ.get("OBS360_FUENTE", "").strip().lower() == "supabase"
    ruta = None if forzada else pipeline.localizar_formulario()
    if not ruta:
        _desde_supabase(vista)
        return
    firma = (ruta, os.path.getmtime(ruta))
    try:
        carga = _carga(firma)
    except ClaveAusente as exc:
        st.title("👪 Cuidadores 360")
        st.error(str(exc), icon="🔑")
        return
    except Exception as exc:                               # noqa: BLE001
        st.title("👪 Cuidadores 360")
        st.error(f"No se pudo leer el formulario de cuidadores: {exc}")
        return

    if vista == "comunidad":
        from src.ui import estado
        from src.ui.views import cuidadores_comunidad as vc
        preparado = _preparado(firma)
        estado.aplicar_colegio_de_url(vc.colegio_de_la_url(preparado))
        vc.render_comunidad(preparado)
        return

    olas = sorted(o for o in carga.respuestas["Ola"].dropna().unique() if o != cat.SIN_DATO)
    with st.sidebar:
        eleccion = st.selectbox("Ola (solo local)", [TODAS, *olas], key="cuid_ola")
        st.caption(cat.AVISO_OLA)
    ola = None if eleccion == TODAS else eleccion
    ac = _analisis(firma, ola)
    st.sidebar.caption(f"{ac.cuidador.n} cuidadores · {ac.nino.n} niños")

    from src.ui.views.cuidadores_investigador import render_investigador
    render_investigador(ac)
```

- [ ] **Step 6: La vista de investigadores lee conteos enmascarados**

En `src/ui/views/cuidadores_investigador.py`, reemplazar:

```python
def conteo_legible(valor) -> str:
    """Conteos de grupo: por debajo del mínimo, «<10»."""
    try:
```

por:

```python
def _entero(valor) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def conteo_legible(valor) -> str:
    """Conteos de grupo: por debajo del mínimo, «<10» (también si ya llega así publicado)."""
    if isinstance(valor, str) and valor.strip().startswith("<"):
        return valor.strip()
    try:
```

y, en `flujo_exclusiones_md`, reemplazar:

```python
    restantes = int(informe.filas_archivo)
    lineas.append(f"- {PASOS_EXCLUSION[0][1]}: {restantes}")
    for campo, etiqueta in PASOS_EXCLUSION[1:]:
        quitadas = int(getattr(informe, campo, 0) or 0)
        restantes -= quitadas
        lineas.append(f"- − {etiqueta}: {quitadas} → quedan {restantes}")
```

por:

```python
    # Desde la corrida publicada, un conteo de 1 a 9 llega como «<10»: se muestra
    # tal cual y lo que se deduciría de él queda «—».
    restantes = _entero(informe.filas_archivo)
    lineas.append(f"- {PASOS_EXCLUSION[0][1]}: {informe.filas_archivo}")
    for campo, etiqueta in PASOS_EXCLUSION[1:]:
        valor = getattr(informe, campo, 0) or 0
        quitadas = _entero(valor)
        restantes = (restantes - quitadas
                     if restantes is not None and quitadas is not None else None)
        lineas.append(f"- − {etiqueta}: {valor} → quedan "
                      f"{restantes if restantes is not None else _SIN_DATO}")
```

Con datos locales (enteros) la salida es idéntica a la de la 4a.

- [ ] **Step 7: Correr las pruebas**

Run: `.venv/bin/python -m pytest tests/test_navegacion.py tests/test_cuidadores_pagina.py tests/test_modo_despliegue.py tests/test_cuidadores_vista.py -q`
Expected: todas pasan (`48` en los tres primeros archivos).

- [ ] **Step 8: Commit**

```bash
git add src/core/navegacion.py main.py src/ui/cuidadores.py src/ui/views/cuidadores_investigador.py tests/test_navegacion.py tests/test_cuidadores_pagina.py tests/test_modo_despliegue.py
git commit -m "feat(cuidadores): selector de vista, corrida publicada y página pública con doble llave

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Datos reales (se omite si falta el archivo) y ensayo real

**Files:**
- Create: `tests/test_cuidadores_publicar_reales.py`

- [ ] **Step 1: Escribir las pruebas**

`tests/test_cuidadores_publicar_reales.py`:

```python
"""
Cuidadores 360 · publicación, vista e informes con el formulario real (se omite sin él).

Solo se comparan agregados. Ningún mensaje de fallo muestra un valor individual:
las comprobaciones cuentan (`assert n == 0`), nunca listan filas.
"""
import json
import re

import pytest

from src.cuidadores import alertas, comunidad, ingest, pipeline, publicar
from src.cuidadores import catalog as cat
from src.estudiantes import supresion

CLAVE = b"clave-de-prueba-solo-para-tests-0001"
RUTA = pipeline.localizar_formulario()
pytestmark = pytest.mark.skipif(RUTA is None, reason="sin el formulario real de cuidadores")


@pytest.fixture(scope="module")
def ac():
    return comunidad.preparar(pipeline.analizar(ingest.cargar(RUTA, k=CLAVE), n_boot=50))


@pytest.fixture(scope="module")
def filas(ac):
    return publicar.aplanar(ac)


def test_el_lote_real_pasa_las_guardas_y_la_auditoria(ac, filas):
    publicar.verificar(filas)
    assert len(publicar.verificar_restas(ac)) == 0


def test_el_lote_real_no_trae_identificadores_ni_conteos(filas):
    texto = json.dumps(filas, ensure_ascii=False, default=str)
    assert len(re.findall(r'"[ECN][0-9a-f]{8}"', texto)) == 0
    assert len(re.findall(r"\b3\d{9}\b", texto)) == 0
    assert sum(1 for f in filas if set(f["detalle"]) & {"casos", "k_bajo", "k_alto"}) == 0
    assert sum(1 for f in filas if f["n"] < cat.MIN_GROUP_N) == 0


def test_el_lote_real_no_publica_nada_por_ola(filas):
    assert sum(1 for f in filas if "ola" in (f["detalle"].get("muestra") or {})) == 0
    assert sum(1 for f in filas if "por_ola" in (f["detalle"].get("ingesta") or {})) == 0


def test_la_autolesion_real_solo_en_el_total(filas):
    propias = [f for f in filas if f["clave"] in ("EPDS_Autolesion", cat.AUTOLESION)]
    assert len(propias) == 2
    assert sum(1 for f in propias if f["agrupacion"] != "total") == 0


def test_cada_grupo_real_tiene_10_o_mas_cuidadores_distintos(ac):
    for a in ac.marcos.values():
        for idx in [*a.base.celdas.values(), *a.base.colegios.values(),
                    *a.base.grados.values()]:
            assert a.datos.loc[idx, "ID_cuidador"].nunique() >= cat.MIN_GROUP_N


def test_cada_animo_real_publicado_cumple_la_regla_de_tres(ac):
    a = ac.cuidador
    malas = 0
    for _, f in a.alertas.dropna(subset=["pct"]).iterrows():
        if f["agrupacion"] == alertas.TOTAL:
            idx = a.base.nivel
        elif f["agrupacion"] == "Colegio×Grado":
            idx = a.base.celdas[f["grupo"]]
        elif f["agrupacion"] == "Colegio":
            idx = a.base.colegios[f["grupo"]]
        else:
            idx = a.base.grados[f["grupo"]]
        v = a.datos.loc[idx, cat.ALERTAS[f["alerta"]].columna].dropna()
        malas += not supresion.proporcion_publicable(int(v.sum()), len(v))
    assert malas == 0


def test_la_vista_y_los_informes_reales_se_arman(ac):
    from src.ui.views import cuidadores_comunidad as vc
    from src.ui.views import cuidadores_informe as inf
    for rol in ("colegio", "familia", "municipio"):
        assert 0 < len(vc.tarjetas(ac, rol, {})) <= 5
    html = inf.informe_secretaria_html(ac)
    for colegio in vc.grupos(ac, "Colegio"):
        html += inf.informe_colegio_html(ac, colegio)
    assert len(re.findall(r"\b[CN][0-9a-f]{8}\b", html)) == 0


def test_el_resumen_real_del_municipio_cabe_en_una_pagina(ac):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML
    from src.ui.views import cuidadores_informe as inf
    html = inf.informe_una_pagina_html(ac, "municipio", {})
    assert len(HTML(string=html).render().pages) == 1
```

- [ ] **Step 2: Correrlas en las dos versiones**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_publicar_reales.py -q`
Expected: `7 passed, 1 skipped` (el PDF se omite en 3.13). Sin el archivo: `8 skipped`.

Run: `"$VENV314/bin/python" -m pytest tests/test_cuidadores_publicar_reales.py -q`
Expected: `8 passed`.

Si alguna falla, **no** imprimir los datos para depurar: usar conteos (`print(len(...))`, `sum(...)`) y avisar al usuario.

- [ ] **Step 3: Ensayo real de cuidadores (solo agregados, con la clave local)**

```bash
.venv/bin/python -m src.cuidadores.publicar --ensayo --salida "$SCRATCH/lote_cuidadores_ensayo.json" > "$SCRATCH/ensayo_cuidadores.log" 2>&1
echo "código de salida: $?"
grep -E "^Lote|^  [a-z_]+: [0-9]+$|n mínimo|^AVISO|^✓" "$SCRATCH/ensayo_cuidadores.log"
```
Expected: `código de salida: 0`; `Lote: 910 filas agregadas` (corte_grupo 390, grupo 219, banda_grupo 174, correlacion 36, alerta_grupo 27, descriptivo 16, icc 16, corte 15, tercil 6, banda 6, alerta 2, muestra 2, ingesta 1); `n mínimo en el lote: 10`; el aviso de señales no aprobadas (29 filas) y **ningún** «AVISO: la auditoría encontró problemas». Si el formulario cambió, los números pueden variar; el código de salida y la ausencia de hallazgos no.

- [ ] **Step 4: Revisar el JSON del ensayo contando, sin mostrar valores**

```bash
.venv/bin/python - "$SCRATCH/lote_cuidadores_ensayo.json" <<'EOF'
import collections, json, re, sys
filas = json.load(open(sys.argv[1], encoding="utf-8"))["filas"]
texto = json.dumps(filas, ensure_ascii=False)
print("identificadores C/N/E:", len(re.findall(r'"[CNE][0-9a-f]{8}"', texto)))
print("teléfonos:", len(re.findall(r"\b3\d{9}\b", texto)))
print("filas con casos:", sum(1 for f in filas if "casos" in (f["detalle"] or {})))
print("filas con ola:", sum(1 for f in filas if "ola" in (f["detalle"].get("muestra") or {})))
print("niveles:", dict(collections.Counter(f["nivel"] for f in filas)))
print("autolesión por grupo:", sum(1 for f in filas if f["clave"] in ("EPDS_Autolesion", "autolesion")
                                   and f["agrupacion"] != "total"))
print("n < 10:", sum(1 for f in filas if f["n"] < 10))
print("estado sin cifra:", sum(1 for f in filas if f["tipo"].startswith("alerta")
                               and f["valor"] is None and f["detalle"].get("estado") != "sin_estado"))
EOF
```
Expected: todos los conteos en `0` y `niveles: {'cuidadores': 910}`. El JSON se queda en el scratchpad: nunca se copia al repositorio.

Sin commit en los Steps 3 y 4; commit de las pruebas:

- [ ] **Step 5: Commit**

```bash
git add tests/test_cuidadores_publicar_reales.py
git commit -m "test(cuidadores): publicación, vista e informes con el formulario real

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Documentación

**Files:**
- Modify: `DESPLIEGUE.md`, `ARCHITECTURE.md`, `supabase/README.md`, `src/cuidadores/__init__.py`

- [ ] **Step 1: `DESPLIEGUE.md`**

Reemplazar el párrafo:

```markdown
**Cuidadores 360 (fase 4a)** solo funciona con el archivo en local
(`cuidadores/Cuidando al Cuidador … .xlsx`) y la clave `OBS360_CLAVE_HMAC`. En
los despliegues la página dice «Cuidadores aún no está publicado»; en el
público ni siquiera aparece en el menú hasta que la fase 4b ponga
`navegacion.CUIDADORES_PUBLICO = True`.
```

por:

````markdown
**Cuidadores 360 (fases 4a y 4b).** En local (archivo
`cuidadores/Cuidando al Cuidador … .xlsx` y clave `OBS360_CLAVE_HMAC`) la
página tiene dos vistas, como Estudiantes: comunidad (colegio, familia,
municipio) e investigadores (con el filtro de ola, que nunca se publica). Sin
archivo, la página lee la corrida publicada de cuidadores (solo agregados de
todas las olas); sin corrida dice «Cuidadores aún no está publicado».

Publicar (en la máquina que procesa, con la clave):

```bash
python -m src.cuidadores.publicar --ensayo --salida /tmp/lote_cuidadores.json   # revisar
python -m src.cuidadores.publicar --notas "cuidadores" --publicar-ya
```

`--ensayo` sale con código 2 si la auditoría encuentra algo. Mientras
`comunidad_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` sean False,
`--publicar-ya` no sube las filas de las señales del adulto. Publicar
cuidadores solo cierra las corridas viejas de cuidadores: la de estudiantes no
se toca. Informes para imprimir: `python -m scripts.generar_informes_cuidadores`
(audita antes de escribir).

En el despliegue público la página **solo aparece** cuando se cumplen las dos
llaves: el equipo aprueba textos y ruta (`comunidad_catalogo.TEXTOS_APROBADOS`
y `RUTAS_VALIDADAS` en True) y, después de publicar la corrida con
`--publicar-ya`, pone `navegacion.CUIDADORES_PUBLICO = True` en un commit
propio. Luego, «Reboot app». Si aun así no hubiera corrida, la página lo dice
y no falla. En público solo se carga la vista de comunidad
(`cuidadores_comunidad.render_publico`); nunca la carga del formulario, el
pipeline ni la vista de investigadores.
````

- [ ] **Step 2: `ARCHITECTURE.md`**

Reemplazar el encabezado y la entrada:

```markdown
## Módulo Cuidadores 360 (fase 4a)

Formulario «Cuidando al Cuidador» (209 columnas, dos olas). Solo local y solo
para investigadores; la vista de comunidad, los informes y la publicación son
de la fase 4b.
```

por:

```markdown
## Módulo Cuidadores 360 (fases 4a y 4b)

Formulario «Cuidando al Cuidador» (209 columnas, dos olas). La fase 4a lo carga,
lo puntúa y lo muestra a investigadores en local; la 4b añade la vista de
comunidad, los informes y la publicación de agregados.
```

Dentro del bloque de código de ese módulo, reemplazar las dos últimas líneas:

```
src/ui/cuidadores.py                    Página: archivo local, clave y filtro de ola.
src/ui/views/cuidadores_investigador.py Pestañas y paquete exportable.
```

por:

```
src/cuidadores/ (fase 4b)
├── comunidad_catalogo.py  Textos de la comunidad (provisionales): tarjetas, señales
│                          del adulto, autocuidado de familia, ruta y avisos.
├── alertas.py             «Ánimo» (EPDS ≥ 13) por grupo y «Autolesión» solo en el
│                          total, desde los cortes ya suprimidos; estado sin casos.
├── comunidad.py           preparar(): copia para la comunidad y la publicación
│                          (sin autolesión por grupo, sin nada por ola).
├── auditoria.py           Restas contando cuidadores distintos, cifras que no
│                          delatan (con la puntuación de cuidadores) y autolesión.
├── publicar.py            Lote agregado (nivel «cuidadores», marco en detalle),
│                          ensayo y publicación por módulo.
└── lectura.py             Rearma la corrida publicada (despliegues).
src/ui/cuidadores.py                    Página local: selector de vista y fuente.
src/ui/views/cuidadores_investigador.py Pestañas y paquete exportable.
src/ui/views/cuidadores_comunidad.py    Vista de comunidad y página pública.
src/ui/views/cuidadores_informe.py      Informes del colegio y de la Secretaría y
                                        resumen de una página (PDF).
scripts/generar_informes_cuidadores.py  Informes HTML, con auditoría previa.
```

y reemplazar la viñeta:

```markdown
- **Sin publicación todavía.** `navegacion.CUIDADORES_PUBLICO = False`: el
  despliegue público no muestra ni importa nada de cuidadores.
```

por:

```markdown
- **Publicación (4b).** Solo agregados de todas las olas, auditados antes de
  subir; la autolesión solo en el total; ningún conteo de casos. El público ve
  la página solo con `navegacion.CUIDADORES_PUBLICO = True` y el catálogo de la
  comunidad aprobado; aun entonces solo importa `views/cuidadores_comunidad`.
```

- [ ] **Step 3: `supabase/README.md`**

Insertar antes de `## Lo que falta`:

```markdown
## Cuidadores 360 (fase 4b): sin migración nueva

Publicar cuidadores no necesita ningún cambio en la base: usa las tablas de
siempre con `modulo = 'cuidadores'` y `nivel = 'cuidadores'` (que el CHECK ya
admite desde la migración 2026-10-07). El marco (cuidador o niño) va en
`detalle.marco`. Requisitos: las migraciones 2026-10-07 y 2026-10-07b aplicadas
(la última corrida publicada **por módulo**); la 2026-10-07c es la última
barrera contra conteos de casos y se recomienda antes de la primera corrida.

- **Verificar después de publicar:** `SELECT modulo, id, creada_en FROM
  obs360.ultima_corrida;` debe dar una fila de `estudiantes` y otra de
  `cuidadores`. La de estudiantes no cambia al publicar cuidadores.
```

- [ ] **Step 4: `src/cuidadores/__init__.py`**

Reemplazar el cierre del docstring:

```python
(puntuaciones desde el texto crudo), `privacidad` (base publicable contando
cuidadores distintos) y `pipeline` (`AnalisisCuidadores`).
"""
```

por:

```python
(puntuaciones desde el texto crudo), `privacidad` (base publicable contando
cuidadores distintos) y `pipeline` (`AnalisisCuidadores`).

Fase 4b: `comunidad_catalogo` (textos provisionales de la comunidad), `alertas`
(señales del adulto por grupo, sin casos), `comunidad` (copia para la comunidad
y la publicación), `auditoria` (lo que se publica, contando cuidadores
distintos), `publicar` y `lectura` (Supabase, `modulo = "cuidadores"`).
"""
```

- [ ] **Step 5: Commit**

```bash
git add DESPLIEGUE.md ARCHITECTURE.md supabase/README.md src/cuidadores/__init__.py
git commit -m "docs(cuidadores): despliegue, arquitectura y publicación de la fase 4b

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Suite completa, producción y no regresión de estudiantes

**Files:** ninguno, salvo que aparezcan fallos.

- [ ] **Step 1: Entorno con Python 3.14 y WeasyPrint**

```bash
[ -x "$VENV314/bin/python" ] || /opt/homebrew/bin/python3.14 -m venv "$VENV314"
"$VENV314/bin/pip" install -q -r requirements.txt pytest pyarrow
"$VENV314/bin/python" -c "import streamlit, pandas, weasyprint, sys; print(sys.version, streamlit.__version__, pandas.__version__)"
```

- [ ] **Step 2: Correr las dos suites**

Run: `.venv/bin/python -m pytest -q`
Expected: `1087 passed, 8 skipped` (956 passed, 4 skipped de antes + 135 nuevas, de las que 4 se omiten sin WeasyPrint). En una máquina sin el archivo real de cuidadores: 8 omitidas más por `test_cuidadores_publicar_reales` (y las de la 4a).

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: `1095 passed`. Ojo con pandas 3: `DataFrame.stack()` ya no quita los NaN.

- Si hay un error real: corregirlo con prueba y commit propio.
- Si es del entorno: anotarlo en el PR.

- [ ] **Step 3: Estudiantes no cambia**

```bash
git diff --stat cd0dedb -- src/estudiantes src/ui/estudiantes.py src/ui/views/estudiantes_comunidad.py \
  src/ui/views/estudiantes_informe.py src/ui/views/estudiantes_investigador.py \
  src/ui/views/estudiantes_alertas.py src/core/colegios.py src/core/modo.py src/core/rutas.py \
  src/core/texto.py src/core/seudonimo.py src/cuidadores/catalog.py src/cuidadores/ingest.py \
  src/cuidadores/scoring.py src/cuidadores/privacidad.py src/cuidadores/pipeline.py supabase/*.sql \
  supabase/migraciones
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$SCRATCH/obs360_lote_despues_4b.json" > /dev/null
cmp "$SCRATCH/obs360_lote_antes_4b.json" "$SCRATCH/obs360_lote_despues_4b.json" && echo "lote de estudiantes idéntico"
```
Expected: el `git diff --stat` no imprime nada y sale `lote de estudiantes idéntico`. Si el `cmp` difiere, parar: algo de esta fase tocó estudiantes.

Además, contra la foto de la 4a (si existe), sin la fecha de la versión:

```bash
[ -f "$SCRATCH/obs360_lote_antes_4a.json" ] && .venv/bin/python - "$SCRATCH/obs360_lote_antes_4a.json" "$SCRATCH/obs360_lote_despues_4b.json" <<'EOF'
import json, sys
a, b = (json.load(open(r, encoding="utf-8")) for r in sys.argv[1:3])
for x in (a, b):
    x["version"] = x["version"].split("-", 3)[-1]      # quita AAAA-MM-DD
print("igual a la foto de la 4a:", a == b)
EOF
```
Expected: `igual a la foto de la 4a: True`.

- [ ] **Step 4: Commit (solo si hubo correcciones)**

---

### Task 12: Verificación con Playwright (local)

**Files:** ninguno del repositorio. El lanzador de la prueba con las dos llaves vive en el scratchpad.

- [ ] **Step 1: Lanzador «aprobado» con una corrida sintética (solo para esta verificación)**

Simula las dos llaves y una corrida publicada de cuidadores con los datos **sintéticos** (centinelas incluidos), sin tocar el código ni Supabase:

```bash
cat > "$SCRATCH/obs360_cuidadores_aprobado.py" <<'EOF'
"""Verificación local: Cuidadores 360 aprobado y con una corrida sintética publicada."""
import os
import sys

RAIZ = os.environ["OBS360_RAIZ"]
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
from src.core import navegacion as nav                       # noqa: E402
from src.cuidadores import comunidad_catalogo as cc, lectura  # noqa: E402

nav.CUIDADORES_PUBLICO = True
cc.TEXTOS_APROBADOS = cc.RUTAS_VALIDADAS = True
if not hasattr(lectura, "_base_de_prueba"):
    from tests import cuidadores_comunidad_datos as datos
    lectura._base_de_prueba = datos.publicado()[1]
lectura.disponible = lambda: True
lectura._cliente = lambda: lectura._base_de_prueba.cliente(anonimo=True)
exec(compile(open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read(), "main.py", "exec"))
EOF
```

- [ ] **Step 2: Levantar los modos**

```bash
RAIZ=/Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
OBS360_MODO=completo     .venv/bin/streamlit run main.py --server.port 8601 --server.headless true &
OBS360_MODO=investigador .venv/bin/streamlit run main.py --server.port 8602 --server.headless true &
OBS360_MODO=comunidad OBS360_FUENTE=supabase .venv/bin/streamlit run main.py --server.port 8603 --server.headless true &
OBS360_MODO=comunidad OBS360_FUENTE=supabase OBS360_RAIZ="$RAIZ" \
  .venv/bin/streamlit run "$SCRATCH/obs360_cuidadores_aprobado.py" --server.port 8604 --server.headless true &
mkdir -p "$SCRATCH/obs360_vacio"
OBS360_MODO=investigador OBS360_DATOS_DIR="$SCRATCH/obs360_vacio" OBS360_RAIZ="$RAIZ" \
  .venv/bin/streamlit run "$SCRATCH/obs360_cuidadores_aprobado.py" --server.port 8605 --server.headless true &
```

- [ ] **Step 3: Comprobar con Playwright MCP**

| Modo | Comprobación |
|---|---|
| completo (8601), Cuidadores 360 | En la barra lateral, «Vista» con «Colegios, familias y municipio» (elegida) y «Equipo investigador». Rol con los tres roles; colegio y «Grado (del hijo o la hija)»; «Cómo están los cuidadores · Todos los colegios»; panel «Señales para cuidar a quienes cuidan»; hasta cinco tarjetas; «Comparar entre grupos»; ruta «Si un cuidador necesita ayuda» con los avisos internos de textos y ruta pendientes |
| completo, rol familia | Sin selector de colegio ni informes; recuadro «Cuidarse para cuidar» sin cifras; ninguna mención de hacerse daño ni de autolesión; sin tarjeta de ánimo |
| completo, rol colegio | Panel con «Ánimo» y el estado general fijo; ninguna mención de «Pensamientos de hacerse daño»; al elegir un colegio, los grados en «Prioridad» de ese colegio (si los hay) |
| completo, rol municipio | «Ánimo» con colegios y grados en «Prioridad» y «Pensamientos de hacerse daño» con la cifra de todo el municipio y la nota «solo para todo el municipio», también con un colegio elegido |
| completo, informes | PDF de una página (o HTML sin WeasyPrint), informe del colegio y, como municipio, el de la Secretaría: se descargan; sin «casos», sin seudónimos |
| completo, Vista → Equipo investigador | Las 9 pestañas y el filtro «Ola (solo local)» de la 4a |
| completo, estado compartido | Elegir un colegio y el rol municipio en Cuidadores, ir a Estudiantes 360: siguen elegidos (y al revés). Con `?colegio=LauV` en la URL, los dos selectores arrancan en LauV |
| investigador (8602) | Abre en «Equipo investigador»; al cambiar a comunidad no hay filtro de ola |
| comunidad (8603), bandera en False | **No hay selector de páginas** (solo Estudiantes 360); ninguna mención de Cuidadores; Estudiantes funciona como antes |
| comunidad «aprobado» (8604) | Selector «Ir a:» con Estudiantes 360 y Cuidadores 360. Cuidadores muestra la vista de comunidad con la corrida sintética (sin selector «Vista», sin filtro de ola, sin pestañas de investigadores); los tres roles como arriba; `?colegio=LauV` preselecciona LauV en las dos páginas |
| investigador sin archivos (8605) | Cuidadores 360 abre en «Equipo investigador» con el aviso de la corrida publicada; la pestaña de muestra muestra «<10» donde corresponde; sin filtro de ola; la vista de comunidad también funciona |
| todos | Sin excepciones en pantalla; ningún «Centinela» ni «3000000000» en pantalla; en el celular (ancho 390) las tarjetas se apilan y nada se corta |

- [ ] **Step 4: Apagar los servidores y borrar `.playwright-mcp/` si se creó**

```bash
pkill -f "streamlit run" ; rm -rf .playwright-mcp
```

---

### Task 13: PR (sin fusionar)

- [ ] **Step 1:** `git push -u origin feature/fase4b-cuidadores-comunidad`

- [ ] **Step 2:** Abrir el PR. Base: `main` si el PR #12 (fase 5 a `main`) ya está fusionado; si no, `feature/fase4a-cuidadores` (y se cambia a `main` cuando se fusione el #12).

  `gh pr create --base <base> --title "Fase 4b · Cuidadores 360: vista de comunidad, informes y publicación"`. El cuerpo lleva:

  1. **Resumen.**
     - Qué ve cada rol (tarjetas, panel, ruta, informes) y qué no ve (familia sin cifras de señales; autolesión solo en el total para el municipio; colegio con estado general).
     - Publicación: agregados de todas las olas, `nivel = "cuidadores"` con el marco en `detalle`, auditoría antes de subir, sin casos, sin IDs, sin olas; señales retenidas hasta la aprobación; publicar cuidadores no toca estudiantes. Sin migración nueva.
     - Navegación pública con doble llave; corte público ampliado.
  2. **Pruebas.**
     - Totales antes (956 passed, 4 skipped en 3.13; 960 passed en 3.14) y después (1087 passed, 8 skipped / 1095 passed).
     - Ensayo real de cuidadores con código 0 (910 filas, solo agregados) y lote de estudiantes idéntico (`cmp`); `git diff` vacío en estudiantes.
     - Verificación con Playwright (Task 12).
  3. **Pasos del usuario y del equipo.**
     - **Antes de la primera corrida:** aplicar `supabase/migraciones/2026-10-07c-alertas-sin-casos.sql` si aún no está.
     - **«Reboot app» después de fusionar.**
     - Para abrir Cuidadores al público, en este orden: (1) el equipo aprueba textos y ruta → `TEXTOS_APROBADOS = True` y `RUTAS_VALIDADAS = True` en `src/cuidadores/comunidad_catalogo.py`; (2) `python -m src.cuidadores.publicar --ensayo` y revisión; (3) `--publicar-ya`; (4) commit con `navegacion.CUIDADORES_PUBLICO = True`; (5) Reboot app; (6) comprobar `SELECT modulo, id FROM obs360.ultima_corrida;`.
  4. **Preguntas abiertas** (la lista de abajo).
  5. Cerrar con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 3:** No fusionar. Lo decide el usuario.

---

## Preguntas abiertas para el equipo (todas tienen un valor provisional en el código)

1. **Textos de las seis tarjetas, del panel y del autocuidado** (`comunidad_catalogo.py`, spec §8.5). En particular, la tarjeta «Estrés de crianza» usa la PSS-10, que mide el estrés percibido de la vida diaria y no el de criar: ¿se mantiene el título de la spec (y el texto lo aclara, como ahora) o se renombra, p. ej. «Estrés del día a día»?
2. **Ruta para adultos con las líneas de Chía** (spec §8.1). Hoy: Secretaría de Salud de Chía y Comisaría de Familia, sin teléfonos. ¿Qué líneas y horarios se añaden (p. ej. la 192 opción 4)?
3. **Uso y redacción de la EPDS fuera del periodo perinatal** (spec §8.4): «señales de ánimo bajo» con EPDS ≥ 13, y la autolesión como «pensamientos de hacerse daño» (cualquier respuesta distinta de «No, nunca»).
4. **Estado general del colegio.** El rol colegio no ve la autolesión; ve un texto fijo («Si un cuidador cuenta que ha pensado en hacerse daño, escucharlo sin juzgar y orientarlo ese mismo día a la ruta para adultos»). ¿Es la lectura correcta de «queda dentro de un estado general» (spec §5.5)?
5. **Familia sin la tarjeta de ánimo.** Para que familia no vea cifras de las señales del adulto, la tarjeta «Ánimo del cuidador» no existe para ese rol y su lugar lo ocupa «Cuidarse para cuidar». ¿De acuerdo?
6. **Cifras en las tarjetas de estrés y barrio:** media del grupo (PSS 0–40, barrio 0–10) con la del municipio en el detalle; sin «más alto / más bajo» (las medias por grupo no traen intervalo). Por celda colegio × grado no hay media publicada y la tarjeta no sale. ¿Prefieren el tercio más alto (requiere publicar un corte nuevo)?
7. **Grado del cuidador = el de su hijo 1** (pregunta 5 de la 4a, sigue abierta): la vista lo dice como «Grado (del hijo o la hija)».
8. **Publicar la comparación por sexo del niño.** No se publica (el sexo no es parte de la base publicable y en el marco de niños los grupos se cuentan en cuidadores). ¿La necesitan en el despliegue del equipo?
9. **Libro de códigos** (spec §9): sin él no hay crianza positiva (subescalas del APQ) y la tarjeta solo describe castigo físico y grito.

## Observaciones de los datos (solo agregados, 8-oct-2026)

Calculadas con este código y una clave de prueba; nada individual se imprimió.

- **Base publicable:** 7 colegios y 7 grados en los dos marcos; 13 celdas en el de cuidadores y 15 en el de niños; el nivel incluye el resto.
- **Señales del adulto (total, 734 cuidadores):** ánimo bajo probable 23,6 %; autolesión 11,2 % (las mismas de la 4a). «Ánimo» por grupo: colegios 5 con cifra (2 en «Prioridad», 3 «Para tener presente») y 2 sin estado; grados 5 con cifra y 2 sin estado; celdas 7 con cifra y 6 sin estado.
- **Tarjetas del municipio:** las cinco tienen cifra para los tres roles. Castigo físico 30,2 % (IC 27,0–33,7); poco apoyo de la familia 18,7 %; hijo con dificultades altas o muy altas según el cuidador 15,7 % (862 niños); PSS media 14,4 de 40; barrio 2,0 de 10.
- **Lote del ensayo:** 910 filas (389 del marco de cuidadores y 521 del de niños), n mínimo 10, ninguna fila con casos, ola ni identificador; la autolesión solo en las 2 filas del total (corte y señal).
- **Auditoría:** sin hallazgos. Sin `auditoria.fugas`, la autolesión daba un falso hallazgo: con solo el total publicado y 17 átomos, `supresion.fugas` no enumera el componente y falla cerrado.

## Autorrevisión contra la spec

| Spec | Dónde queda |
|---|---|
| §5.5 vista de comunidad con los mismos roles y estructura; seis tarjetas con techo de 5 | Task 6 (`cuidadores_comunidad`), roles y orden de `comunidad_catalogo`; pruebas por rol |
| §5.5 «Ánimo» (EPDS ≥ 13) por grupo para colegio y municipio, con las reglas de §5.4 | `alertas.tabla` desde los cortes suprimidos (3 ≤ casos ≤ n − 3, también por resta), estado con `estudiantes.alertas.estado`, «Sin estado: cifras pequeñas» (Tasks 2 y 6) |
| §5.5 «Autolesión» solo municipio, sin conteos, 3..n−3, nunca por colegio; en el colegio, estado general | `preparar` + `SOLO_TOTAL` + `auditar_solo_total` + lector; panel de colegio con texto fijo (Tasks 2, 3, 5 y 6) |
| §5.5 familia: autocuidado y ruta, sin cifras | `panel_html`/`render_panel` de familia y sin tarjeta de ánimo; pruebas de palabras prohibidas |
| §5.5 `publicar.py`, `lectura.py` con `modulo = "cuidadores"` | Tasks 4 y 5; circuito publicar → leer y aislamiento de estudiantes con la base falsa |
| §5.5 despliegue público solo con textos y rutas aprobados y una corrida publicada | Doble llave en `navegacion` + mensaje de `render_publico` sin corrida (Task 8) |
| §4 nada individual; mínimo en cuidadores distintos; nada deducible; solo agregados a Supabase; textos fijos; el público no importa lo de investigación | `auditoria` (Task 3), `verificar` + CHECK emulados (Task 4), catálogo fijo (Task 1), `PROHIBIDOS_EN_COMUNIDAD` ampliado (Task 8) |
| §5.1 base publicable y todo o nada | Heredados de la 4a; la 4b solo lee y quita cifras |
| §5.3 `?colegio=` y estado compartido entre páginas | `estado.ROL`/`estado.COLEGIO` y `colegio_de_la_url` (Task 6) |
| §5.4 informes: panel en el del colegio, tabla por colegio sin conteos en el de la Secretaría, recuadro compacto en el PDF | Tasks 6 y 7; peor caso en una página con WeasyPrint |
| §6 lenguaje (nunca «suicidio», naranja máximo, ruta siempre visible) | Pruebas del catálogo y de colores (Tasks 1 y 6) |
| §7 sintéticas con centinelas, auditoría propia, regresión real, Supabase por módulo, PDF peor caso, Playwright | Tasks 1–9, 11 y 12 |
| §8 lo que decide el equipo | Banderas en False; preguntas abiertas |
| §10 fuera de alcance (publicar por ola) | `preparar` y `aplanar` rechazan la vista de una ola; nada por ola en el lote |

## Verificación del plan

El código de las Tasks 1 a 10 se escribió y se probó en una copia del repositorio (worktree en el scratchpad, sobre `cd0dedb`) antes de escribir este plan, y se insertó aquí sin cambios:

- Python 3.13 (pandas 2): **1087 passed, 8 skipped** con el archivo real presente (956 passed, 4 skipped antes; 135 pruebas nuevas, 4 de ellas de PDF omitidas sin WeasyPrint).
- Python 3.14 (pandas 3.0.6, WeasyPrint): **1095 passed** (960 passed antes).
- Ensayo real de cuidadores: código 0, 910 filas, solo agregados (conteos de la Task 9 en 0).
- Ensayo de estudiantes: el lote es idéntico byte a byte con y sin el código de la fase 4b.
- `AppTest`: vista de comunidad local y publicada en los tres roles, página local en completo e investigador, corrida publicada sin archivo y `main.py` en comunidad con y sin la doble llave, sin excepciones y sin importar módulos prohibidos.
