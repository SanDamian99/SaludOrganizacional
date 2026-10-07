# Fase 3 · Alertas de estudiantes («Señales para actuar a tiempo»): plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** el colegio, el municipio y la familia ven, arriba de las tarjetas, un panel de alertas **por grupo**. Hay dos alertas: «Señales de malestar» y «Señales de desesperanza y pensamientos de muerte». El panel tiene dos estados, «Para tener presente» y «Prioridad», y un tercero neutro, «Sin estado: cifras pequeñas», cuando el porcentaje del grupo no se puede mostrar. Nunca muestra conteos de casos y su color máximo es naranja. Lleva qué hacer y la ruta. Las alertas también llegan a los informes, al PDF de una página, a la vista de investigadores y a Supabase.

**Arquitectura.** Todo lo nuevo vive en **módulos nuevos**, que siempre se importan frescos aunque Streamlit Cloud conserve módulos viejos en memoria:

| Módulo nuevo | Qué contiene |
|---|---|
| `src/estudiantes/alertas_catalogo.py` | Ítems, umbrales, estados, textos fijos y `RUTAS`; `catalog` los reexporta como `catalog.ALERTAS` y `catalog.RUTAS` |
| `src/estudiantes/alertas.py` | Funciones puras: señal por estudiante, ítems con «*», `cortes_alerta` (tabla por grupo con la forma de `cortes`), `estado`, la tabla plana `tabla`, sensibilidad y distribución de ítems |
| `src/ui/views/estudiantes_alertas.py` | Panel: funciones puras, HTML y `render_panel` |

**Las alertas son proporciones binarias como cualquier corte.** No tienen regla de privacidad propia: pasan por la supresión general de `src/estudiantes/supresion.py` (PR #8, ya fusionado en esta rama).
- La señal de cada estudiante (1 / 0 / NaN) es una columna más de los datos (`ALERTA_*`): pasa por la base publicable y por el todo o nada de la fase 1, así que la auditoría de restas de `n` (`privacidad.auditar`) ya la cubre.
- El nivel y cada subgrupo (colegio, grado, celda colegio×grado) llevan una tabla `cortes_alerta` con la forma de `scoring.sobre_cortes`. `supresion.aplicar` la trata como una familia más, con la misma jerarquía (celdas, colegios, grados, nivel y el resto R): supresión primaria `3 ≤ casos ≤ n − 3`, supresión complementaria y auditoría exacta de sumas y restas (`fugas`). Así los **grados y las celdas llevan porcentaje** cuando la supresión lo permite.
- **La desesperanza está anidada en el corte del ítem 18.** La regla estricta implica RCADS 18 ≥ «Con frecuencia», que es justo el corte que publica la tarjeta «Pensamientos sobre la muerte». Publicar las dos deja ver la diferencia (ítem 18 alto sin desesperanza). Por eso la supresión reparte la base del ítem 18 en tres partes `(n − k₁₈, k₁₈ − k, k)`, como los dos cortes anidados de irritabilidad, y suprime la desesperanza **después** del ítem 18, partiendo de lo que este ya ocultó (`suprimir(previos=…)`): nunca se publica donde el ítem 18 está suprimido. Si en algún grupo las bases no coinciden (alguien respondió el 18 y no el 16), la desesperanza no se publica en ninguno (falla cerrado).
- `supresion.auditar` (que ya llama `publicar.verificar_restas`) recalcula las alertas desde los datos enmascarados y audita lo publicado. No hay una auditoría paralela.

**El estado no añade información.**
- Se calcula y se muestra **solo para grupos con porcentaje publicado**, y solo con cifras publicadas: `alertas.estado(pct, n, pct_nivel, n_nivel)`. Compara el IC de Wilson del grupo con el del resto del nivel (nivel − grupo), cuyo porcentaje se deduce de esas mismas cifras.
- Si el porcentaje del grupo está suprimido: «Sin estado: cifras pequeñas», el texto fijo de §5.4 y la ruta.
- Si el grupo tiene cifra pero no hay resto con qué compararlo (el total del nivel, o un grupo que es casi todo el nivel): estado `referencia`, que se lee «Para tener presente» sin la explicación de la comparación.

**Lo que no se publica.** La sensibilidad (umbrales 2/3/4, regla amplia) y la distribución de los ítems son **solo de la vista local de investigadores**: no van a Supabase ni al ZIP. Aun así cumplen la regla: cada reparto anidado se muestra entero o no se muestra (`supresion.partes_publicables`). Los mensajes por rol de las alertas **no** se suben a `obs360.mensajes` en esta fase: se suben cuando el equipo apruebe los textos (spec §8.1).

**Despliegue con módulos o corridas viejas.**
- Las vistas leen `Analisis.alertas` con `getattr`, importan el panel dentro de `try/except` y envuelven `render_panel`, `panel_html` y `tabla_secretaria_html` en `try/except`. Los informes usan `getattr(vc, "ruta_para_rol", None)` con `cat.RUTA_ATENCION` como alternativa.
- Una corrida publicada sin filas de alerta (la vigente hoy) se sigue leyendo: el panel no aparece y la tarjeta de muerte se queda como está.
- El público verá alertas solo cuando se publique una corrida nueva. Esa es la compuerta de aprobación de los textos.

**Tech stack:** Python 3.13 local / 3.14 en Streamlit Cloud, pandas, numpy, scipy (Wilson ya existe en `stats.wilson`), Streamlit, WeasyPrint (PDF), pytest, Supabase (PostgREST) y Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-10-06-cuidadores-alertas-triangulacion-design.md`: §5.4, con §4, §6, §7 y §8.

**Restricciones que no se negocian:**
- **Nada individual.**
  - Nunca se publica, se exporta ni se muestra el número de casos de una alerta.
  - El % y el «1 de cada N» solo donde la supresión general los deja. Si no, va el texto fijo de §5.4.
  - El estado, solo donde hay %.
- **Ninguna resta delata.** Ni por `n` (fase 1) ni por proporciones (PR #8, y ahora las alertas).
- **Textos fijos** en `alertas_catalogo`, marcados como provisionales (`TEXTOS_APROBADOS = False`). Nunca los redacta la IA en tiempo de ejecución.
  - Nunca «riesgo de suicidio».
  - Siempre «señales», «no es un diagnóstico» y «dónde mirar primero».
- **Rutas sin teléfonos inventados.** El aviso «ruta pendiente de validación» se ve solo en el modo completo, nunca en los informes.
- **Familia** no ve desesperanza ni listas por colegio. Para colegio y municipio, el panel reemplaza la tarjeta de muerte.
- **Lo existente no cambia** salvo donde lo pide la spec. Hay prueba de no regresión sobre el lote sintético publicado y comparación del lote real antes y después.
- **Datos reales:**
  - Las pruebas se omiten si faltan los archivos.
  - Nunca se abren a mano los archivos de `../datos_fuente_360` (datos de menores).
  - Ninguna salida imprime casos.
  - El ensayo real (`python -m src.estudiantes.publicar --ensayo`) tiene que seguir saliendo con código 0.
- **Git y migración:**
  - La rama `feature/fase3-alertas` ya existe y ya trae la fase 2 y el PR #8: no se crea ni se cambia de rama.
  - Nunca `git add -A`: siempre los archivos por nombre.
  - No se fusiona a `main` sin permiso del usuario. No se hace `push` hasta la Task 18.
  - La migración la escribe el plan y la corre el usuario.
  - Después de fusionar, siempre «Reboot app».
- Cada commit termina con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

**Comandos de prueba** (desde la raíz del repo):
- Python 3.13: `.venv/bin/python -m pytest -q`. Línea base al empezar: **529 passed, 2 skipped**.
- Python 3.14 con WeasyPrint (producción): `"$VENV314/bin/python" -m pytest -q`, con

  ```bash
  VENV314=/private/tmp/claude-501/-Users-joseamorocho-Documents-app-360-observatorio-SaludOrganizacional/73d67104-c128-41eb-b044-923af344a71f/scratchpad/venv314
  ```

  Si ese directorio ya no existe (el scratchpad es de la sesión), se recrea como en la Task 16, Step 1.

---

## Mapa de archivos

| Archivo | Qué cambia |
|---|---|
| `src/estudiantes/alertas_catalogo.py` (nuevo) | `ALERTAS`, umbrales, estados, textos del panel, `RUTAS[rol][tipo]`, `ruta()` e `items_marcados_esperados()` |
| `src/estudiantes/catalog.py:415-420` | Reexporta `ALERTAS` y `RUTAS`. `RUTA_ATENCION` queda como alias de la ruta vigente |
| `src/estudiantes/ingest.py` | `tiene_asterisco(col)`: la única regla del «*», que usan `items_marcados` y `alertas` |
| `src/estudiantes/alertas.py` (nuevo) | Señales, `marcar`, `items_marcados_por_escala`, `cortes_alerta`, `ANIDADA`, `estado`, `tabla`, `ordenar`, `sensibilidad`, `distribucion_items` |
| `src/estudiantes/supresion.py` | `suprimir(previos=…)`, `indices_atomos`, `partes_alerta`, `_aplicar_alertas` dentro de `aplicar` y `_auditar_alertas` dentro de `auditar` |
| `src/estudiantes/pipeline.py` | `Analisis.cortes_alerta`, `alertas`, `alertas_sensibilidad` y `alertas_items`. `analizar` marca las señales antes de la base y arma la tabla plana después de la supresión |
| `src/estudiantes/publicar.py` | Filas `alerta` y `alerta_grupo` (con `n_grupo` y `estado`), sin casos. `verificar` rechaza un estado sin porcentaje |
| `src/estudiantes/lectura.py` | `_tabla_alertas`: rearma `Analisis.alertas`. Una corrida vieja deja la tabla vacía |
| `supabase/migraciones/2026-10-07c-alertas-sin-casos.sql` (nuevo), `supabase/estudiantes_schema.sql` | `CHECK` sin conteos (`casos`, `k_bajo`, `k_alto`) y estado solo con cifra, `NOT VALID` |
| `src/ui/views/estudiantes_alertas.py` (nuevo) | `senales`, `listas_prioridad`, `explicaciones`, `panel_html`, `tabla_secretaria_html`, `render_panel` y los CSS |
| `src/ui/views/estudiantes_comunidad.py` | Panel arriba de las tarjetas; tarjeta de muerte reemplazada; selector «Comparar» sin muerte para familia; ruta por rol; aviso solo en el modo completo |
| `src/ui/views/estudiantes_informe.py` | Panel en el informe del colegio, tabla por colegio en el de la Secretaría y recuadro compacto en el PDF; sin la columna de muerte cuando hay panel; todo a prueba de módulos viejos |
| `src/ui/views/estudiantes_investigador.py` | `PESTANAS` con «Alertas», `alertas.csv` en el ZIP (columna `alerta_nombre`) y sección en la metodología |
| `tests/test_alertas.py`, `tests/test_alertas_publicar.py`, `tests/test_alertas_vista.py`, `tests/test_alertas_reales.py`, `tests/test_alertas_regresion.py` (nuevos) | Pruebas |
| `tests/fixtures/lote_sintetico_antes_de_alertas.json` (nuevo) | Foto del lote sintético antes de la fase |
| `tests/test_estudiantes_publicar.py`, `tests/test_restas_publicadas.py`, `tests/test_estudiantes_investigador.py` | Ajustes explícitos: tipos nuevos, tope de filas por grupo y 9 archivos en el ZIP |
| `docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md`, `supabase/README.md`, `DESPLIEGUE.md` | Documentación |

**Datos que no cambian.** El SDQ y el RCADS se leen tal como los codifica `ingest` desde el **texto crudo** del formulario (`catalog.MAP_3`: No es cierto = 0, Algo cierto = 1, Muy cierto = 2; `MAP_4_FREQ`: Nunca = 0 … Siempre = 3).
- La codificación defectuosa de la memoria (`Datos_Cuidador_AUDIT.xlsx`) es del dataset de **cuidadores**, no de este.
- Ninguno de los 6 ítems del malestar es inverso (los inversos son 7, 11, 14, 21 y 25): se usan las columnas `SDQ5…SDQ24` sin recodificar.
- La Task 2 lo prueba desde el texto crudo.

---

### Task 0: Línea base y foto de lo que ya se publica

**Files:**
- Create: `tests/test_alertas_regresion.py`
- Create: `tests/fixtures/lote_sintetico_antes_de_alertas.json` (generado)

- [ ] **Step 1: Comprobar la rama (ya existe; no se crea)**

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
git branch --show-current          # → feature/fase3-alertas
git log --oneline -1               # → c86f930 merge: supresión de cifras pequeñas (PR #8) en la fase 3
git status --short                 # solo los dos .docx sin seguimiento; no se tocan
```

Si la rama no es `feature/fase3-alertas` o el árbol tiene cambios propios, parar y avisar al usuario.

- [ ] **Step 2: Línea base**

Run: `.venv/bin/python -m pytest -q`
Expected: `529 passed, 2 skipped`.

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: todo pasa (las pruebas de PDF corren en vez de saltarse). Anotar los totales para el PR.

- [ ] **Step 3: Escribir la prueba de no regresión (caracterización)**

`tests/test_alertas_regresion.py`:

```python
"""
Lo que ya se publicaba no cambia con las alertas (spec §7, «No regresión de pantallas»).

`tests/fixtures/lote_sintetico_antes_de_alertas.json` se generó con el código
anterior a la fase 3 (Task 0 del plan) sobre formularios sintéticos de los dos
niveles. Después de la fase 3, el lote sin las filas nuevas («alerta…») debe ser
idéntico. Únicas diferencias admitidas: los valores suprimidos de las columnas
nuevas de señal (`ALERTA_*`) dentro de `muestra.suprimidos`, y el último dígito
de los flotantes (se redondean a 9 cifras significativas: pandas 3 y numpy
pueden cambiarlo entre versiones).
"""
import json
import os

from src.estudiantes import ingest, pipeline, publicar, scoring

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "lote_sintetico_antes_de_alertas.json")


def _formularios():
    from tests.test_estudiantes_comunidad import _formulario
    sec = _formulario()
    pri = _formulario().drop(columns=[c for c in sec.columns if c.startswith("RCADS")])
    pri["Estoy en grado"] = ["Cuarto" if i % 2 else "Quinto" for i in range(len(pri))]
    pri["Tengo:"] = [f"{9 + i % 3} años" for i in range(len(pri))]
    pri["Mi nombre completo es:"] = [f"Menor Apellido {i}" for i in range(len(pri))]
    return sec, pri


def lote_actual() -> list[dict]:
    sec, pri = _formularios()
    bruto, informes = ingest.cargar_varios([sec, pri])
    puntuado = scoring.puntuar(bruto)
    analisis = {inf.nivel: pipeline.analizar(puntuado, inf.nivel, n_boot=20,
                                             avisos=list(inf.avisos))
                for inf in informes}
    return publicar.aplanar(analisis) + publicar.aplanar_ingesta(informes)


def _redondear(v):
    """Flotantes a 9 cifras significativas, en cualquier nivel de anidación."""
    if isinstance(v, float):
        return float(f"{v:.9g}")
    if isinstance(v, dict):
        return {k: _redondear(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_redondear(x) for x in v]
    return v


def normalizar(filas: list[dict]) -> list[dict]:
    """Quita lo nuevo de la fase 3, redondea y ordena, para comparar lotes."""
    salida = []
    for f in filas:
        if str(f["tipo"]).startswith("alerta"):
            continue
        f = json.loads(json.dumps(f, ensure_ascii=False, default=str))
        if f["tipo"] == "muestra":
            m = f["detalle"].get("muestra") or {}
            m["suprimidos"] = {k: v for k, v in (m.get("suprimidos") or {}).items()
                               if not str(k).startswith("ALERTA_")}
        salida.append(_redondear(f))
    return sorted(salida, key=lambda f: json.dumps(f, sort_keys=True, ensure_ascii=False))


def _texto(filas) -> str:
    return json.dumps(filas, sort_keys=True, ensure_ascii=False)


def test_lo_que_ya_se_publicaba_no_cambia():
    with open(FIXTURE, encoding="utf-8") as fh:
        antes = json.load(fh)
    assert _texto(normalizar(lote_actual())) == _texto(antes)
```

- [ ] **Step 4: Generar la foto con el código actual (antes de tocar nada)**

```bash
.venv/bin/python - <<'EOF'
import json, sys
sys.path.insert(0, ".")
from tests.test_alertas_regresion import FIXTURE, lote_actual, normalizar
with open(FIXTURE, "w", encoding="utf-8") as fh:
    json.dump(normalizar(lote_actual()), fh, ensure_ascii=False, indent=1, sort_keys=True)
print("filas:", len(json.load(open(FIXTURE, encoding="utf-8"))))
EOF
```
Expected: `filas: 1000` (aproximadamente; lo importante es que se escriba).

Run: `"$VENV314/bin/python" -m pytest tests/test_alertas_regresion.py -q`
Expected: `1 passed` también en 3.14: el redondeo a 9 cifras significativas absorbe el último dígito que cambia pandas 3.

- [ ] **Step 5: Foto del lote real, fuera del repositorio**

Solo agregados. No se abre ningún archivo fuente a mano; si faltan los formularios, este paso se omite (el comando falla con `FileNotFoundError`).

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_antes.json"
echo "código de salida: $?"
```
Expected: `código de salida: 0` (la auditoría no encuentra nada). Si sale 2, parar: el punto de partida ya tiene un problema y no es de esta fase.

- [ ] **Step 6: Correr y commit**

Run: `.venv/bin/python -m pytest tests/test_alertas_regresion.py -q`
Expected: `1 passed`.

```bash
git add tests/test_alertas_regresion.py tests/fixtures/lote_sintetico_antes_de_alertas.json
git commit -m "test(alertas): foto del lote publicado antes de la fase 3" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 1: Catálogo de alertas y rutas

**Files:**
- Create: `src/estudiantes/alertas_catalogo.py`
- Modify: `src/estudiantes/catalog.py:415-420`
- Create: `tests/test_alertas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_alertas.py` (los imports de las tareas siguientes se añaden en cada una):

```python
"""Alertas de grupo de Estudiantes 360 (spec 6-oct-2026, §5.4): catálogo, señales y cifras."""
import re

import pytest

from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import supresion


# ══ Catálogo ════════════════════════════════════════════════════════════════
def test_catalog_reexporta_alertas_y_rutas():
    assert cat.ALERTAS is ac.ALERTAS and cat.RUTAS is ac.RUTAS


def test_definiciones_de_la_spec():
    m, d = ac.ALERTAS[ac.MALESTAR], ac.ALERTAS[ac.DESESPERANZA]
    assert m.escala == "SDQ" and m.items == (5, 6, 8, 13, 19, 24)
    assert ac.UMBRAL_MALESTAR == 3 and ac.UMBRALES_SENSIBILIDAD == (2, 3, 4)
    assert set(m.niveles) == {cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA}
    assert d.escala == "RCADS" and d.niveles == (cat.NIVEL_SECUNDARIA,)
    assert ac.ITEM_MUERTE == cat.RCADS_ITEM_MUERTE == 18 and ac.ITEM_VALIA == 16
    assert set(ac.ITEMS_AMPLIA) == {1, 4}


def test_la_codificacion_es_la_de_ingest():
    assert ac.MUY_CIERTO == cat.MAP_3["muy cierto"]
    assert ac.CON_FRECUENCIA == cat.MAP_4_FREQ["con frecuencia"]
    assert ac.SIEMPRE == cat.MAP_4_FREQ["siempre"]
    # ninguno de los 6 ítems del malestar es inverso: se leen como se respondieron
    assert not set(ac.ALERTAS[ac.MALESTAR].items) & set(cat.SDQ_REVERSE_ITEMS)
    assert set(ac.ITEMS_REGLA_AMPLIA) <= set(cat.RCADS_DEP_ITEMS)


def test_roles_y_niveles_coinciden_con_catalog():
    assert set(ac.ROLES) == set(cat.ROLES)
    assert set(ac.NIVELES) == {cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA}
    for a in ac.ALERTAS.values():
        assert set(a.roles) <= set(cat.ROLES) and set(a.niveles) <= set(ac.NIVELES)
        for rol in a.roles:
            assert a.que_hacer.get(rol, "").strip(), (a.clave, rol)


def test_familia_no_ve_desesperanza():
    assert "familia" not in ac.ALERTAS[ac.DESESPERANZA].roles
    assert "familia" in ac.ALERTAS[ac.MALESTAR].roles


def _textos() -> list[str]:
    textos = [v for k, v in vars(ac).items() if k.isupper() and isinstance(v, str)]
    textos += list(ac.ESTADOS.values())
    for a in ac.ALERTAS.values():
        textos += [a.nombre, a.nombre_corto, a.senal, a.regla, a.que_es, a.limite,
                   *a.que_hacer.values()]
    textos += [d for por_tipo in ac.RUTAS.values() for ruta in por_tipo.values()
               for _, d in ruta]
    return textos


def test_los_textos_no_alarman():
    for t in _textos():
        bajo = t.lower()
        assert "suicid" not in bajo, t
        assert "alarma" not in bajo, t
    assert ac.ESTADOS[ac.PRIORIDAD] == "Prioridad"
    assert ac.ESTADOS[ac.PRESENTE] == ac.ESTADOS[ac.REFERENCIA] == "Para tener presente"
    assert ac.ESTADOS[ac.SIN_ESTADO] == "Sin estado: cifras pequeñas"
    assert ac.CIFRAS_PEQUENAS == cat.CIFRAS_PEQUENAS
    assert ac.NO_ES_DIAGNOSTICO.startswith("No es un diagnóstico")
    assert "dónde mirar primero" in ac.NO_ES_DIAGNOSTICO
    assert f"al menos {supresion.MIN_CASOS} estudiantes" in ac.REGLA_CIFRAS


def test_las_rutas_no_inventan_telefonos():
    numeros = {m for por_tipo in ac.RUTAS.values() for ruta in por_tipo.values()
               for n, d in ruta for m in re.findall(r"\d{3,}", f"{n} {d}")}
    assert numeros <= {"106"}          # la línea vigente; las de Chía las confirma el equipo
    assert set(ac.RUTAS) == set(cat.ROLES)
    for rol in cat.ROLES:
        assert ac.ruta(rol, "estudiante") == list(cat.RUTA_ATENCION)
        assert ac.ruta(rol, "adulto")


def test_la_ruta_vigente_no_cambia():
    assert cat.RUTA_ATENCION == [
        ("Orientación escolar del colegio", "Primer contacto, siempre."),
        ("Línea 106", "Atención psicológica gratuita, 24 horas."),
        ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
        ("Comisaría de Familia", "Si hay riesgo en el hogar."),
    ]


def test_quedan_marcadas_como_provisionales():
    assert ac.TEXTOS_APROBADOS is False and ac.RUTAS_VALIDADAS is False
    assert "pendiente de validación" in ac.RUTA_PENDIENTE
```

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.estudiantes.alertas_catalogo'`.

- [ ] **Step 2: Crear el catálogo**

`src/estudiantes/alertas_catalogo.py`:

```python
"""
Alertas de grupo de Estudiantes 360 — «Señales para actuar a tiempo».

Qué ítems activan cada alerta, con qué umbral, qué lee cada rol y a dónde se
deriva (spec del 6-oct-2026, §5.4). `catalog` reexporta `ALERTAS` y `RUTAS`.

PROVISIONAL. Textos, umbrales y rutas los aprueba el equipo investigador
(spec §8, puntos 1 a 3). Mientras `TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` sean
False se muestran tal cual y, solo en el modo completo, la vista añade el aviso
interno `RUTA_PENDIENTE`.

Reglas:
  · Textos fijos. Nunca los redacta la IA en tiempo de ejecución.
  · Nunca «riesgo de suicidio»: «señales», «no es un diagnóstico», «dónde
    mirar primero».
  · El código no inventa teléfonos. La «Línea 106» es de Bogotá y se queda
    hasta que el equipo confirme las líneas de Chía (p. ej. 192 opción 4 o
    ICBF 141).
  · No importa `catalog` (catalog importa este módulo): niveles, roles y el
    texto de cifras pequeñas van como texto, y una prueba comprueba que
    coinciden.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TEXTOS_APROBADOS = False
RUTAS_VALIDADAS = False

MALESTAR = "malestar"
DESESPERANZA = "desesperanza"

ROLES = ("colegio", "familia", "municipio")
NIVELES = ("secundaria", "primaria")

# Codificación de ingest (catalog.MAP_3 y catalog.MAP_4_FREQ)
MUY_CIERTO = 2
CON_FRECUENCIA = 2
SIEMPRE = 3

# Malestar: «Muy cierto» en al menos UMBRAL_MALESTAR de los 6 ítems
UMBRAL_MALESTAR = 3
UMBRALES_SENSIBILIDAD = (2, 3, 4)

# Desesperanza (solo secundaria): ítems del RCADS-25
ITEM_MUERTE = 18          # «Pienso acerca de la muerte»
ITEM_VALIA = 16           # «Me siento que no valgo nada»
ITEMS_AMPLIA = (4, 1)     # la regla amplia (sensibilidad) suma RCADS 4 o RCADS 1
ITEMS_REGLA_ESTRICTA = (ITEM_VALIA, ITEM_MUERTE)
ITEMS_REGLA_AMPLIA = (1, 4, ITEM_VALIA, ITEM_MUERTE)


@dataclass(frozen=True)
class Alerta:
    clave: str
    nombre: str                 # lo que lee la comunidad
    nombre_corto: str           # tablas e informes
    senal: str                  # «señales de malestar», para la frase de la cifra
    escala: str                 # prefijo de columna de ingest: «SDQ», «RCADS»
    items: tuple[int, ...]      # ítems que la activan (1-indexados)
    regla: str                  # la regla en palabras, para la metodología
    niveles: tuple[str, ...]
    roles: tuple[str, ...]
    marcados_en: tuple[str, ...] = ()   # formularios cuyos encabezados llevan «*» en estos ítems
    que_es: str = ""
    que_hacer: dict = field(default_factory=dict)   # rol → texto
    limite: str = ""


ALERTAS: dict[str, Alerta] = {
    MALESTAR: Alerta(
        clave=MALESTAR,
        nombre="Señales de malestar",
        nombre_corto="Malestar",
        senal="señales de malestar",
        escala="SDQ",
        items=(5, 6, 8, 13, 19, 24),
        regla=("«Muy cierto» en 3 o más de estos 6 ítems del SDQ: 5 (me enojo y pierdo el "
               "control), 6 (solitario), 8 (preocupado), 13 (triste o con ganas de llorar), "
               "19 (se burlan de mí) y 24 (muchos miedos). Se calcula con los 6 ítems "
               "respondidos."),
        niveles=("secundaria", "primaria"),
        roles=("colegio", "familia", "municipio"),
        marcados_en=("primaria",),     # hoy solo primaria trae el «*» (spec §5.4)
        que_es=("Estudiantes que marcan «muy cierto» en al menos 3 de 6 preguntas sobre "
                "enojo, soledad, preocupación, tristeza, burlas y miedos."),
        que_hacer={
            "colegio": ("Revisar con orientación escolar cómo se acompaña a este grupo: "
                        "convivencia, burlas entre compañeros y espacios para hablar de lo que "
                        "sienten. Formar a los docentes para reconocer señales y derivar por la "
                        "ruta, sin señalar a ningún estudiante."),
            "familia": ("Preguntar con calma cómo se siente y cómo le va con sus compañeros, y "
                        "escuchar sin juzgar. Si nota tristeza, miedo o enojo que no pasan, "
                        "buscar a la orientación del colegio o al servicio de salud."),
            "municipio": ("Orientar la oferta psicosocial y de convivencia escolar hacia los "
                          "grupos en «Prioridad» y verificar que la ruta de salud mental tenga "
                          "capacidad para recibir a quienes se deriven."),
        },
        limite=("Los seis ítems mezclan emociones, enojo y relación con los compañeros: por eso "
                "se nombra «malestar» y no «malestar emocional». No forman una escala validada "
                "por sí solos."),
    ),
    DESESPERANZA: Alerta(
        clave=DESESPERANZA,
        nombre="Señales de desesperanza y pensamientos de muerte",
        nombre_corto="Desesperanza",
        senal="señales de desesperanza o pensamientos de muerte",
        escala="RCADS",
        items=(ITEM_VALIA, ITEM_MUERTE),
        regla=("RCADS 18 («Pienso acerca de la muerte») en «Siempre», o RCADS 18 en «Con "
               "frecuencia» o más junto con RCADS 16 («Me siento que no valgo nada») en «Con "
               "frecuencia» o más. Se calcula con los ítems 16 y 18 respondidos."),
        niveles=("secundaria",),
        roles=("colegio", "municipio"),
        que_es=("Estudiantes que dicen pensar en la muerte siempre, o con frecuencia junto con "
                "sentir que no valen nada. Es una señal para mirar con atención y activar la "
                "ruta, no un diagnóstico."),
        que_hacer={
            "colegio": ("Verificar que la ruta de atención esté activa y que los docentes sepan "
                        "cómo derivar. Fortalecer los espacios de escucha y la formación en "
                        "primeros auxilios psicológicos. No abordar a estudiantes individuales a "
                        "partir de este dato."),
            "municipio": ("Garantizar que la ruta de salud mental adolescente tenga capacidad de "
                          "respuesta y articularla con los colegios en «Prioridad»."),
        },
        limite=("El instrumento no tiene una escala de desesperanza: son dos ítems del RCADS-25 "
                "y se leen como señal de grupo."),
    ),
}

# Enunciados resumidos de los ítems que usan las alertas (pestaña de investigadores).
# RCADS 1 y 4: pendientes de copiar del formulario aplicado.
ENUNCIADOS_ITEMS = {
    "SDQ5": "Me enojo y pierdo el control",
    "SDQ6": "Solitario",
    "SDQ8": "Preocupado",
    "SDQ13": "Triste o con ganas de llorar",
    "SDQ19": "Se burlan de mí",
    "SDQ24": "Muchos miedos",
    "RCADS1": "RCADS 1 (subescala de depresión)",
    "RCADS4": "RCADS 4 (subescala de depresión)",
    "RCADS16": "Me siento que no valgo nada",
    "RCADS18": "Pienso acerca de la muerte",
}

# ── Textos del panel ─────────────────────────────────────────────────────────
TITULO_PANEL = "Señales para actuar a tiempo"
# Estados. «referencia» se lee igual que «presente», pero no hubo comparación
# (el total del nivel, o un grupo sin resto suficiente con qué compararlo).
PRIORIDAD = "prioridad"
PRESENTE = "presente"
REFERENCIA = "referencia"
SIN_ESTADO = "sin_estado"
ESTADOS = {PRIORIDAD: "Prioridad", PRESENTE: "Para tener presente",
           REFERENCIA: "Para tener presente", SIN_ESTADO: "Sin estado: cifras pequeñas"}
NO_ES_DIAGNOSTICO = "No es un diagnóstico: indica dónde mirar primero."
PLANTILLA_CIFRA = "{fraccion} estudiantes {verbo} {senal}."
# Igual a catalog.CIFRAS_PEQUENAS (una prueba lo comprueba).
CIFRAS_PEQUENAS = ("En este grupo las cifras son muy pequeñas para mostrarse sin riesgo de "
                   "identificar a alguien; la ruta sigue aplicando.")
CIFRAS_PEQUENAS_CORTO = "Cifras muy pequeñas para mostrarse"
NOTA_AZAR = ("Con muchas comparaciones, alguna «Prioridad» puede deberse al azar; sirve para "
             "orientar, no para concluir.")
QUE_ES_PRIORIDAD = ("«Prioridad»: en este grupo las señales son más frecuentes que en el resto "
                    "del municipio, aun contando el margen de error.")
QUE_ES_PRESENTE = ("«Para tener presente»: las señales aparecen, como en casi todos los grupos, "
                   "sin diferenciarse del resto del municipio.")
QUE_ES_SIN_ESTADO = ("«Sin estado»: con cifras tan pequeñas no se muestra ni el porcentaje ni la "
                     "comparación, para no identificar a nadie. La ruta sigue aplicando.")
QUE_ES_REFERENCIA = ("«Para tener presente», sin comparación: es el total del nivel, o un "
                     "grupo que es casi todo el nivel y no deja un resto con qué compararlo.")
TITULO_GRADOS_PRIORIDAD = "Grados en «Prioridad»:"
TITULO_COLEGIOS_PRIORIDAD = "Colegios en «Prioridad»:"
NOTA_TABLA = ("Porcentaje del colegio con señales y su margen de error. El número de "
              "estudiantes con señales no se publica nunca.")
REGLA_CIFRAS = ("El porcentaje y el «1 de cada N» se muestran solo si en el grupo hay al menos "
                "3 estudiantes con señales y al menos 3 sin ellas, también después de sumar o "
                "restar cualquier par de cifras publicadas (la misma supresión de todas las "
                "proporciones). El estado se muestra solo donde se muestra el porcentaje.")
RUTA_PENDIENTE = ("Aviso interno: la ruta de atención está pendiente de validación por el "
                  "equipo (las líneas de Chía no están confirmadas). Solo se ve en el modo "
                  "completo.")

# ── Rutas por rol y por tipo de persona ──────────────────────────────────────
# Mientras el equipo no apruebe las de Chía, las tres usan la ruta vigente.
_RUTA_ESTUDIANTE = (
    ("Orientación escolar del colegio", "Primer contacto, siempre."),
    ("Línea 106", "Atención psicológica gratuita, 24 horas."),
    ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
    ("Comisaría de Familia", "Si hay riesgo en el hogar."),
)
# Para adultos (cuidadores, fase 4). Sin teléfonos hasta que el equipo los confirme.
_RUTA_ADULTO = (
    ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
    ("Comisaría de Familia", "Si hay riesgo en el hogar."),
)
RUTAS: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {
    "colegio": {"estudiante": _RUTA_ESTUDIANTE, "adulto": _RUTA_ADULTO},
    "familia": {"estudiante": _RUTA_ESTUDIANTE, "adulto": _RUTA_ADULTO},
    "municipio": {"estudiante": _RUTA_ESTUDIANTE, "adulto": _RUTA_ADULTO},
}


def ruta(rol: str, tipo: str = "estudiante") -> list[tuple[str, str]]:
    """La ruta de un rol para estudiantes o adultos; la del colegio si el rol no existe."""
    por_tipo = RUTAS.get(rol) or RUTAS["colegio"]
    return list(por_tipo.get(tipo) or por_tipo["estudiante"])


def items_marcados_esperados(nivel: str) -> dict[str, set[int]]:
    """{escala: ítems} que el formulario de `nivel` debe traer marcados con «*»."""
    salida: dict[str, set[int]] = {}
    for a in ALERTAS.values():
        if nivel in a.marcados_en:
            salida.setdefault(a.escala, set()).update(a.items)
    return salida
```

- [ ] **Step 3: Reexportar desde `catalog`**

En `src/estudiantes/catalog.py`, reemplazar el bloque

```python
RUTA_ATENCION = [
    ("Orientación escolar del colegio", "Primer contacto, siempre."),
    ("Línea 106", "Atención psicológica gratuita, 24 horas."),
    ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
    ("Comisaría de Familia", "Si hay riesgo en el hogar."),
]
```

por:

```python
# Alertas de grupo y rutas por rol (spec §5.4). Viven en un módulo propio:
# tras un despliegue, un módulo nuevo se importa fresco aunque `catalog` siga
# viejo en memoria, y la aplicación nunca lee `catalog.ALERTAS` directamente.
from src.estudiantes.alertas_catalogo import ALERTAS, RUTAS  # noqa: E402,F401

# Compatibilidad: la ruta vigente, igual para los tres roles mientras el equipo
# no apruebe las de Chía. Lo nuevo usa `alertas_catalogo.ruta(rol, tipo)`.
RUTA_ATENCION = list(RUTAS["colegio"]["estudiante"])
```

- [ ] **Step 4: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py tests/test_alertas_regresion.py tests/test_estudiantes.py -q`
Expected: todo pasa.

- [ ] **Step 5: Commit**

```bash
git add src/estudiantes/alertas_catalogo.py src/estudiantes/catalog.py tests/test_alertas.py
git commit -m "feat(alertas): catálogo de alertas y rutas por rol (provisional)" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Señal por estudiante

**Files:**
- Create: `src/estudiantes/alertas.py`
- Modify: `tests/test_alertas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_alertas.py`, añadir a los imports:

```python
import numpy as np
import pandas as pd

from src.estudiantes import alertas as al
from src.estudiantes import ingest, privacidad
from tests.test_estudiantes import _formulario_sintetico
```

y al final:

```python
# ══ Señales por estudiante, desde el texto crudo del formulario ═════════════
def _poner(raw, prefijo, fila, valores: dict):
    cols = [c for c in raw.columns if c.startswith(prefijo)]
    for item, texto in valores.items():
        raw.loc[fila, cols[item - 1]] = texto


def _crudo_malestar():
    raw = _formulario_sintetico(n=12)
    for f in range(12):
        _poner(raw, "SDQ", f, {i: "No es cierto" for i in ac.ALERTAS[ac.MALESTAR].items})
    _poner(raw, "SDQ", 0, {5: "Muy cierto", 6: "Muy cierto", 8: "Muy cierto"})
    _poner(raw, "SDQ", 1, {5: "Muy cierto", 24: "Muy cierto"})
    _poner(raw, "SDQ", 2, {6: "Muy cierto", 13: "Muy cierto", 19: "Muy cierto", 24: "Muy cierto"})
    _poner(raw, "SDQ", 3, {5: "Muy cierto", 6: "Muy cierto", 8: "Muy cierto", 24: None})
    _poner(raw, "SDQ", 4, {i: "Algo cierto" for i in ac.ALERTAS[ac.MALESTAR].items})
    return raw


def _crudo_desesperanza():
    raw = _formulario_sintetico(n=12)
    for f in range(12):
        _poner(raw, "RCADS", f, {i: "Nunca" for i in ac.ITEMS_REGLA_AMPLIA})
    _poner(raw, "RCADS", 0, {18: "Siempre"})
    _poner(raw, "RCADS", 1, {18: "Con frecuencia", 16: "Con frecuencia"})
    _poner(raw, "RCADS", 2, {18: "Con frecuencia", 16: "Algunas veces"})
    _poner(raw, "RCADS", 3, {18: "Algunas veces", 16: "Siempre", 4: "Con frecuencia"})
    _poner(raw, "RCADS", 4, {18: "Nunca", 16: "Siempre"})
    return raw


def test_malestar_se_puntua_desde_el_texto_crudo():
    d, _ = ingest.cargar(_crudo_malestar())          # filas en el orden del formulario
    s = al.senal_malestar(d)
    assert s.iloc[0] == 1.0                          # 3 «Muy cierto»
    assert s.iloc[1] == 0.0                          # 2
    assert s.iloc[2] == 1.0                          # 4
    assert np.isnan(s.iloc[3])                       # falta un ítem: no se adivina
    assert s.iloc[4] == 0.0                          # «Algo cierto» no cuenta
    assert al.senal_malestar(d, 2).iloc[1] == 1.0
    assert al.senal_malestar(d, 4).iloc[0] == 0.0


def test_desesperanza_estricta_y_amplia():
    d, _ = ingest.cargar(_crudo_desesperanza())
    estricta = al.senal_desesperanza(d)
    amplia = al.senal_desesperanza(d, amplia=True)
    assert estricta.iloc[:5].tolist() == [1.0, 1.0, 0.0, 0.0, 0.0]
    assert amplia.iloc[:5].tolist() == [1.0, 1.0, 1.0, 1.0, 0.0]
    assert (amplia.dropna() >= estricta.dropna()).all()   # la amplia contiene a la estricta


def test_la_desesperanza_esta_anidada_en_el_corte_del_item_18():
    """Estricta ⊆ RCADS18 ≥ «Con frecuencia»: por eso la supresión la trata como anidada."""
    rng = np.random.default_rng(3)
    d = pd.DataFrame({f"RCADS{i}": rng.integers(0, 4, 500) for i in ac.ITEMS_REGLA_AMPLIA})
    s = al.senal_desesperanza(d)
    assert ((s == 1) <= (d["RCADS18"] >= ac.CON_FRECUENCIA)).all()
    assert al.ANIDADA == {ac.DESESPERANZA: f"RCADS{cat.RCADS_ITEM_MUERTE}"}


def test_sin_las_columnas_no_hay_senal():
    d = pd.DataFrame({"SDQ1": [0, 1]})
    assert al.senal_malestar(d).isna().all()
    assert al.senal_desesperanza(d).isna().all()


def test_marcar_agrega_las_columnas_del_nivel_y_no_toca_nada_mas():
    d, _ = ingest.cargar(_crudo_desesperanza())
    m = al.marcar(d, cat.NIVEL_SECUNDARIA)
    assert set(m.columns) - set(d.columns) == {
        "ALERTA_malestar", "ALERTA_malestar_2", "ALERTA_malestar_4",
        "ALERTA_desesperanza", "ALERTA_desesperanza_amplia"}
    pd.testing.assert_frame_equal(m[d.columns], d)
    p = al.marcar(d, cat.NIVEL_PRIMARIA)             # primaria nunca lleva desesperanza
    assert "ALERTA_malestar" in p.columns
    assert not [c for c in p.columns if c.startswith("ALERTA_desesperanza")]
    pd.testing.assert_frame_equal(al.marcar(m, cat.NIVEL_SECUNDARIA), m)   # idempotente


def test_las_columnas_de_senal_pasan_por_el_todo_o_nada():
    d = pd.DataFrame(columns=["Colegio", "Grado", "ALERTA_malestar"])
    assert "ALERTA_malestar" in privacidad.columnas_de_analisis(d)
```

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.estudiantes.alertas'`.

- [ ] **Step 2: Implementar**

`src/estudiantes/alertas.py` (el resto del módulo se añade en las Tasks 3 y 4; el docstring y las constantes ya van completos):

```python
"""
Alertas de grupo de Estudiantes 360 — funciones puras (spec 6-oct-2026, §5.4).

Por estudiante se calcula una señal (1, 0 o faltante) con las reglas de
`alertas_catalogo`. Lo que sale de aquí es siempre por grupo de la base
publicable (privacidad.base_publicable) y nunca lleva el número de casos.

CÓMO SE PROTEGEN LAS CIFRAS
Cada alerta es una proporción binaria más, igual que un corte:
  · La señal es una columna de los datos (`ALERTA_*`): pasa por el todo o nada
    de la fase 1, así que la auditoría de restas de n ya la cubre.
  · `cortes_alerta` arma, para el nivel y para cada subgrupo (colegio, grado,
    celda), una tabla con la forma de `scoring.sobre_cortes`. `supresion.aplicar`
    la trata como una familia más (celdas, colegios, grados, nivel y el resto R):
    supresión primaria 3 ≤ casos ≤ n − 3, complementaria y auditoría exacta de
    sumas y restas. Los grados y las celdas llevan porcentaje cuando la
    supresión lo permite.
  · La desesperanza (regla estricta) implica RCADS 18 ≥ «Con frecuencia», que es
    el corte de la tarjeta de muerte: es un corte ANIDADO en esa familia
    (`ANIDADA`). La supresión la reparte en (n − k₁₈, k₁₈ − k, k) y nunca la
    publica donde el corte del ítem 18 está suprimido.

ESTADO («Prioridad» / «Para tener presente»)
Solo para grupos con porcentaje publicado, y solo con cifras publicadas
(`estado`): el % y el n del grupo y del nivel. El resto del nivel (nivel −
grupo) se deduce de esas cifras, así que el estado no añade información. Si el
porcentaje está suprimido, el estado es neutro («sin estado»).

LO QUE NO SE PUBLICA
La sensibilidad (umbrales 2/3/4 y regla amplia) y la distribución de los ítems
son solo para la vista local de investigadores: no van a Supabase ni al ZIP.
Aun así cumplen la regla: cada reparto anidado se muestra entero o no se
muestra (`supresion.partes_publicables`).

Faltantes: el malestar exige los 6 ítems respondidos; la desesperanza, los de
su regla (16 y 18 la estricta; 1, 4, 16 y 18 la amplia).

Los ítems se leen tal como los codifica `ingest` desde el texto crudo del
formulario (No es cierto = 0 … Muy cierto = 2; Nunca = 0 … Siempre = 3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import privacidad, supresion
from src.estudiantes.stats import wilson

TOTAL = "total"
TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
AGRUPACIONES = ("Colegio", "Grado", CRUCE)

COLUMNAS = {ac.MALESTAR: "ALERTA_malestar", ac.DESESPERANZA: "ALERTA_desesperanza"}
COLUMNA_AMPLIA = "ALERTA_desesperanza_amplia"

# Alerta → familia de `scoring.sobre_cortes` en la que está anidada (alerta ⊆ corte).
ANIDADA = {ac.DESESPERANZA: f"RCADS{ac.ITEM_MUERTE}"}


def columna_malestar(umbral: int) -> str:
    return (COLUMNAS[ac.MALESTAR] if umbral == ac.UMBRAL_MALESTAR
            else f"ALERTA_malestar_{umbral}")


# variante → (alerta, columna, etiqueta, ¿es la vigente?)
VARIANTES: dict[str, tuple[str, str, str, bool]] = {
    **{f"malestar_{u}": (ac.MALESTAR, columna_malestar(u),
                         f"«Muy cierto» en {u} o más de 6", u == ac.UMBRAL_MALESTAR)
       for u in ac.UMBRALES_SENSIBILIDAD},
    "desesperanza_estricta": (ac.DESESPERANZA, COLUMNAS[ac.DESESPERANZA],
                              "Regla estricta", True),
    "desesperanza_amplia": (ac.DESESPERANZA, COLUMNA_AMPLIA, "Regla amplia", False),
}

# Tabla por grupo de cada objeto (nivel y subgrupos), con la forma de sobre_cortes.
# `casos` es interno: lo usa la supresión y nunca se publica.
COLUMNAS_CORTES = ["clave", "indicador", "anidada_en", "n", "casos", "pct", "ic_inf",
                   "ic_sup"]
# Tabla plana que leen las vistas y que se publica. Sin casos, nunca.
COLUMNAS_TABLA = ["alerta", "agrupacion", "grupo", "n", "pct", "ic_inf", "ic_sup", "estado"]
COLUMNAS_SENSIBILIDAD = ["alerta", "variante", "etiqueta", "vigente", "n", "pct",
                         "ic_inf", "ic_sup"]
COLUMNAS_ITEMS = ["alerta", "item", "enunciado", "respuesta", "n", "pct"]

ETIQUETAS_RESPUESTA = {
    "SDQ": ("No es cierto", "Algo cierto", "Muy cierto"),
    "RCADS": ("Nunca", "Algunas veces", "Con frecuencia", "Siempre"),
}


# ── Señal por estudiante ─────────────────────────────────────────────────────
def _columnas(escala: str, items) -> list[str]:
    return [f"{escala}{i}" for i in items]


def senal_malestar(d: pd.DataFrame, umbral: int = ac.UMBRAL_MALESTAR) -> pd.Series:
    """1.0 si «Muy cierto» en ≥ `umbral` de los 6 ítems; 0.0 si no; NaN si falta alguno."""
    cols = _columnas("SDQ", ac.ALERTAS[ac.MALESTAR].items)
    if not set(cols) <= set(d.columns):
        return pd.Series(np.nan, index=d.index, dtype=float)
    X = d[cols]
    completos = X.notna().all(axis=1)
    return ((X == ac.MUY_CIERTO).sum(axis=1) >= umbral).astype(float).where(completos)


def senal_desesperanza(d: pd.DataFrame, amplia: bool = False) -> pd.Series:
    """Regla estricta (vigente) o amplia (sensibilidad); NaN si falta un ítem de la regla."""
    cols = _columnas("RCADS", ac.ITEMS_REGLA_AMPLIA if amplia else ac.ITEMS_REGLA_ESTRICTA)
    if not set(cols) <= set(d.columns):
        return pd.Series(np.nan, index=d.index, dtype=float)
    completos = d[cols].notna().all(axis=1)
    muerte = d[f"RCADS{ac.ITEM_MUERTE}"]
    valia = d[f"RCADS{ac.ITEM_VALIA}"]
    if amplia:
        otros = pd.concat([d[f"RCADS{i}"] >= ac.CON_FRECUENCIA for i in ac.ITEMS_AMPLIA],
                          axis=1).any(axis=1)
        si = (muerte >= ac.CON_FRECUENCIA) | ((valia >= ac.CON_FRECUENCIA) & otros)
    else:
        si = (muerte == ac.SIEMPRE) | ((muerte >= ac.CON_FRECUENCIA)
                                       & (valia >= ac.CON_FRECUENCIA))
    return si.astype(float).where(completos)


def marcar(d: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Copia de `d` con una columna por señal y variante (1 / 0 / NaN). No toca nada más.

    Estas columnas son individuales: viven solo en `Analisis.datos`, que nunca
    se publica ni se exporta.
    """
    nuevas: dict[str, pd.Series] = {}
    malestar = ac.ALERTAS[ac.MALESTAR]
    if nivel in malestar.niveles and set(_columnas("SDQ", malestar.items)) <= set(d.columns):
        for u in ac.UMBRALES_SENSIBILIDAD:
            nuevas[columna_malestar(u)] = senal_malestar(d, u)
    if nivel in ac.ALERTAS[ac.DESESPERANZA].niveles:
        if set(_columnas("RCADS", ac.ITEMS_REGLA_ESTRICTA)) <= set(d.columns):
            nuevas[COLUMNAS[ac.DESESPERANZA]] = senal_desesperanza(d)
        if set(_columnas("RCADS", ac.ITEMS_REGLA_AMPLIA)) <= set(d.columns):
            nuevas[COLUMNA_AMPLIA] = senal_desesperanza(d, amplia=True)
    base = d.drop(columns=[c for c in nuevas if c in d.columns])
    if not nuevas:
        return base.copy()
    return pd.concat([base, pd.DataFrame(nuevas, index=d.index)], axis=1)


def claves_del_nivel(d: pd.DataFrame, nivel: str) -> list[str]:
    """Alertas que aplican al nivel y tienen alguna señal válida en `d`."""
    return [k for k, x in ac.ALERTAS.items()
            if nivel in x.niveles and COLUMNAS[k] in d.columns and d[COLUMNAS[k]].notna().any()]
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/alertas.py tests/test_alertas.py
git commit -m "feat(alertas): señal de malestar y de desesperanza por estudiante" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Ítems con asterisco, con una sola regla

Hoy `ingest.cargar` solo reconoce el «*» al principio del encabezado (`str(c).strip().startswith("*")`). La spec admite el «*» al principio o al final. Se crea `ingest.tiene_asterisco` y la usan `InformeIngesta.items_marcados` y `alertas.items_marcados_por_escala`: una sola regla.

**Files:**
- Modify: `src/estudiantes/ingest.py`
- Modify: `src/estudiantes/alertas.py`
- Modify: `tests/test_alertas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Al final de `tests/test_alertas.py`:

```python
# ══ Ítems con «*»: una sola regla, la de ingest ═════════════════════════════
@pytest.mark.parametrize("encabezado,marcado", [
    ("*SDQ [x]", True), ("SDQ [x] *", True), (" *SDQ [x]", True),
    ("SDQ [x]", False), ("SDQ [x*y]", False)])
def test_tiene_asterisco(encabezado, marcado):
    assert ingest.tiene_asterisco(encabezado) is marcado


def test_items_marcados_al_principio_o_al_final():
    raw = _formulario_sintetico(n=12)
    cols = [c for c in raw.columns if c.startswith("SDQ")]
    raw = raw.rename(columns={cols[4]: "*" + cols[4], cols[5]: cols[5] + " *"})
    assert al.items_marcados_por_escala(raw.columns) == {"SDQ": {5, 6}}
    _, inf = ingest.cargar(raw)                     # ingest usa la misma regla
    assert len(inf.items_marcados) == 2


def test_los_items_esperados_salen_del_catalogo():
    assert ac.items_marcados_esperados(cat.NIVEL_PRIMARIA) == {"SDQ": {5, 6, 8, 13, 19, 24}}
    assert ac.items_marcados_esperados(cat.NIVEL_SECUNDARIA) == {}   # hoy sin marcar


def test_un_formulario_marcado_como_el_catalogo_coincide_y_se_carga():
    raw = _formulario_sintetico(n=12)
    cols = [c for c in raw.columns if c.startswith("SDQ")]
    raw = raw.rename(columns={cols[i - 1]: "*" + cols[i - 1]
                              for i in ac.ALERTAS[ac.MALESTAR].items})
    assert al.items_marcados_por_escala(raw.columns) == \
        ac.items_marcados_esperados(cat.NIVEL_PRIMARIA)
    d, inf = ingest.cargar(raw)                     # el «*» no rompe la carga
    assert len(inf.items_marcados) == 6 and "SDQ5" in d.columns
```

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q -k "asterisco or marcad"`
Expected: FAIL con `AttributeError: module 'src.estudiantes.ingest' has no attribute 'tiene_asterisco'`.

- [ ] **Step 2: Implementar en `ingest`**

En `src/estudiantes/ingest.py`, justo antes de `def _bloque(`:

```python
def tiene_asterisco(columna) -> bool:
    """¿El encabezado crudo marca el ítem con «*», al principio o al final? (spec §5.4)"""
    texto = str(columna).strip()
    return texto.startswith("*") or texto.endswith("*")
```

y en `cargar`, reemplazar

```python
    inf.items_marcados = [norm_txt(c) for c in raw.columns if str(c).strip().startswith("*")]
```

por

```python
    inf.items_marcados = [norm_txt(c) for c in raw.columns if tiene_asterisco(c)]
```

- [ ] **Step 3: Implementar en `alertas`**

Al final de `src/estudiantes/alertas.py`:

```python
# ── Ítems con «*» en el formulario ───────────────────────────────────────────
def items_marcados_por_escala(columnas) -> dict[str, set[int]]:
    """{escala: números de ítem} de los encabezados con «*» (spec §5.4).

    Localiza cada bloque igual que `ingest` (por el prefijo normalizado), numera
    dentro del bloque y reconoce el «*» con `ingest.tiene_asterisco`, la misma
    regla que llena `InformeIngesta.items_marcados`.
    """
    from src.estudiantes.ingest import _PREFIJOS, _bloque, norm_txt, tiene_asterisco
    crudas = list(columnas)
    normalizadas = [norm_txt(c) for c in crudas]
    salida: dict[str, set[int]] = {}
    for escala, prefijo in _PREFIJOS.items():
        indices = _bloque(normalizadas, prefijo)
        marcados = {i for i, col in enumerate(indices, start=1) if tiene_asterisco(crudas[col])}
        if marcados:
            salida[escala] = marcados
    return salida
```

- [ ] **Step 4: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py tests/test_estudiantes.py -q`
Expected: todo pasa (incluida `test_la_ingesta_guarda_conteos_crudos_e_items_marcados`, que sigue con el «*» al principio).

- [ ] **Step 5: Commit**

```bash
git add src/estudiantes/ingest.py src/estudiantes/alertas.py tests/test_alertas.py
git commit -m "feat(alertas): ítems con asterisco con una sola regla, la de ingest" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Tabla de cada grupo, estado y tablas locales

Funciones puras, sin pipeline todavía:
- `cortes_alerta(d, nivel)`: la tabla de un grupo, con la forma de `scoring.sobre_cortes` (lleva `casos` para la supresión; nunca se publica).
- `estado(pct, n, pct_nivel, n_nivel)` y `estado_total(pct)`: solo cifras publicadas.
- `tabla(a)`: la tabla plana que leen las vistas y que se publica, armada desde las tablas **ya suprimidas** del nivel y de los subgrupos. Sin casos.
- `sensibilidad` y `distribucion_items`: solo el nivel, solo local, enteras o nada.

**Files:**
- Modify: `src/estudiantes/alertas.py`
- Modify: `tests/test_alertas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_alertas.py`, añadir a los imports:

```python
import inspect
from types import SimpleNamespace
```

y al final:

```python
# ══ Tabla de cada grupo, estado y tablas locales ═══════════════════════════
def test_estado_prioridad_contra_el_resto():
    assert al.estado(75.0, 40, 30.6, 160) == ac.PRIORIDAD      # 30/40 frente a 19/120
    assert al.estado(10.0, 40, 30.6, 160) == ac.PRESENTE


def test_sin_porcentaje_no_hay_estado():
    assert al.estado(None, 40, 30.0, 160) == ac.SIN_ESTADO
    assert al.estado(float("nan"), 40, 30.0, 160) == ac.SIN_ESTADO
    assert al.estado_total(None) == ac.SIN_ESTADO


def test_sin_resto_con_que_comparar_es_referencia():
    assert al.estado(30.0, 155, 30.0, 160) == ac.REFERENCIA      # resto de 5
    assert al.estado(30.0, 40, None, 160) == ac.REFERENCIA       # nivel suprimido
    assert al.estado_total(17.0) == ac.REFERENCIA


def test_el_estado_solo_recibe_cifras_publicadas():
    """El estado es función del % y el n publicados del grupo y del nivel: nada más."""
    assert list(inspect.signature(al.estado).parameters) == ["pct", "n", "pct_nivel", "n_nivel"]
    assert list(inspect.signature(al.estado_total).parameters) == ["pct"]


def test_cortes_alerta_tiene_la_forma_de_los_cortes():
    d = pd.DataFrame({"ALERTA_malestar": [1.0] * 6 + [0.0] * 14 + [np.nan] * 2,
                      "ALERTA_desesperanza": [1.0] * 4 + [0.0] * 18})
    t = al.cortes_alerta(d, cat.NIVEL_SECUNDARIA).set_index("clave")
    assert list(al.cortes_alerta(d, cat.NIVEL_SECUNDARIA).columns) == al.COLUMNAS_CORTES
    assert (t.loc["malestar", "n"], t.loc["malestar", "casos"]) == (20, 6)
    assert t.loc["malestar", "pct"] == 30.0 and t.loc["malestar", "anidada_en"] == ""
    assert t.loc["desesperanza", "anidada_en"] == "RCADS18"
    assert list(al.cortes_alerta(d, cat.NIVEL_PRIMARIA)["clave"]) == ["malestar"]


def _objeto(filas):
    return SimpleNamespace(cortes_alerta=pd.DataFrame(filas, columns=al.COLUMNAS_CORTES))


def _c(clave, n, k, pct):
    nulo = pct is None
    return dict(clave=clave, indicador="", anidada_en="", n=n, casos=None if nulo else k,
                pct=pct, ic_inf=None if nulo else pct - 5, ic_sup=None if nulo else pct + 5)


def test_la_tabla_plana_sale_de_las_tablas_suprimidas():
    a = _objeto([_c("malestar", 160, 49, 30.6)])
    a.nivel = cat.NIVEL_SECUNDARIA
    a.subgrupos = {
        "Colegio": {"A": _objeto([_c("malestar", 40, 30, 75.0)]),
                    "B": _objeto([_c("malestar", 40, None, None)])},     # suprimida
        "Grado": {"Sexto": _objeto([_c("malestar", 8, 2, 25.0)])},        # n < 10: fuera
        al.CRUCE: {}}
    t = al.tabla(a)
    assert list(t.columns) == al.COLUMNAS_TABLA and "casos" not in t.columns
    assert list(zip(t["agrupacion"], t["grupo"], t["estado"])) == [
        (al.TOTAL, al.TODOS, ac.REFERENCIA), ("Colegio", "A", ac.PRIORIDAD),
        ("Colegio", "B", ac.SIN_ESTADO)]
    assert t["pct"].isna().tolist() == [False, False, True]


def test_sin_tabla_de_alertas_la_tabla_plana_queda_vacia():
    t = al.tabla(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA))
    assert t.empty and list(t.columns) == al.COLUMNAS_TABLA


def test_ordenar_es_estable_ante_filas_barajadas():
    filas = [dict(alerta=a, agrupacion=ag, grupo=g, n=40, pct=None, ic_inf=None, ic_sup=None,
                  estado=ac.SIN_ESTADO)
             for a in ("desesperanza", "malestar")
             for ag, g in ((al.CRUCE, "A|Octavo"), ("Grado", "Octavo"), (al.CRUCE, "A|Sexto"),
                           ("Colegio", "B"), ("Grado", "Sexto"), (al.TOTAL, al.TODOS),
                           ("Colegio", "A"))]
    t = al.ordenar(pd.DataFrame(filas), cat.NIVEL_SECUNDARIA)
    assert list(t["alerta"][:7]) == ["malestar"] * 7
    assert list(zip(t["agrupacion"], t["grupo"]))[:7] == [
        (al.TOTAL, al.TODOS), ("Colegio", "A"), ("Colegio", "B"), ("Grado", "Sexto"),
        ("Grado", "Octavo"), (al.CRUCE, "A|Sexto"), (al.CRUCE, "A|Octavo")]
    barajada = t.sample(frac=1, random_state=3)
    pd.testing.assert_frame_equal(al.ordenar(barajada, cat.NIVEL_SECUNDARIA), t)


# ── sensibilidad e ítems: solo el nivel, solo local ───────────────────────
def test_sensibilidad_se_muestra_entera_o_no_se_muestra():
    d = pd.DataFrame({"ALERTA_malestar_2": [1.0] * 20 + [0.0] * 80,
                      "ALERTA_malestar": [1.0] * 10 + [0.0] * 90,
                      "ALERTA_malestar_4": [1.0] * 9 + [0.0] * 91})
    s = al.sensibilidad(d, cat.NIVEL_SECUNDARIA).set_index("variante")
    assert s["pct"].isna().all()                  # 3 − 4 deja 1 estudiante: nada
    d["ALERTA_malestar_4"] = [1.0] * 5 + [0.0] * 95
    s = al.sensibilidad(d, cat.NIVEL_SECUNDARIA).set_index("variante")
    assert s.loc["malestar_3", "pct"] == 10.0 and s.loc["malestar_4", "pct"] == 5.0
    assert (s["n"] == 100).all() and "casos" not in s.columns


def test_distribucion_de_items_oculta_el_item_con_una_respuesta_rara():
    d = pd.DataFrame({"ALERTA_malestar": 0.0,
                      "SDQ5": [0] * 90 + [1] * 8 + [2] * 2,
                      "SDQ6": [0] * 60 + [1] * 30 + [2] * 10})
    t = al.distribucion_items(d, cat.NIVEL_SECUNDARIA)
    assert t[t["item"] == "SDQ5"]["pct"].isna().all()
    sdq6 = t[t["item"] == "SDQ6"]
    assert sdq6["pct"].tolist() == [60.0, 30.0, 10.0]
    assert sdq6["respuesta"].tolist() == ["No es cierto", "Algo cierto", "Muy cierto"]
    assert list(t.columns) == al.COLUMNAS_ITEMS
```

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: FAIL con `AttributeError: module 'src.estudiantes.alertas' has no attribute 'estado'`.

- [ ] **Step 2: Implementar**

Al final de `src/estudiantes/alertas.py`:

```python
# ── Tabla por grupo de cada objeto (entra en la supresión) ──────────────────
def cortes_alerta(d: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Prevalencia de cada alerta en las filas `d`, con IC de Wilson.

    Misma forma que `scoring.sobre_cortes`; la supresión deja en blanco pct, IC
    y casos donde la cifra delataría. `casos` no sale nunca de `Analisis`.
    """
    filas = []
    for clave in claves_del_nivel(d, nivel):
        v = d[COLUMNAS[clave]].dropna()
        k, n = int(v.sum()), int(len(v))
        pct, ic_inf, ic_sup = wilson(k, n)
        filas.append(dict(clave=clave, indicador=ac.ALERTAS[clave].nombre,
                          anidada_en=ANIDADA.get(clave, ""), n=n, casos=k,
                          pct=pct, ic_inf=ic_inf, ic_sup=ic_sup))
    return pd.DataFrame(filas, columns=COLUMNAS_CORTES)


# ── Estado, solo con cifras publicadas ───────────────────────────────────────
def _vacio(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v)) or pd.isna(v)


def estado(pct, n, pct_nivel, n_nivel) -> str:
    """Estado de un grupo a partir de cifras PUBLICADAS: (%, n) del grupo y del nivel.

    · Sin porcentaje del grupo: «sin estado» (cifras pequeñas).
    · Sin porcentaje del nivel, o con un resto (nivel − grupo) de menos de
      MIN_GROUP_N respuestas: «referencia» (se lee «Para tener presente», sin
      comparación).
    · Si no, «Prioridad» cuando el límite inferior del IC de Wilson del grupo
      queda por encima del límite superior del resto, que se deduce de esas
      mismas cifras; si no, «Para tener presente».
    """
    if _vacio(pct) or _vacio(n):
        return ac.SIN_ESTADO
    if _vacio(pct_nivel) or _vacio(n_nivel):
        return ac.REFERENCIA
    n, n_nivel = int(n), int(n_nivel)
    n_resto = n_nivel - n
    if n <= 0 or n_resto < cat.MIN_GROUP_N:
        return ac.REFERENCIA
    k = float(pct) * n / 100
    k_resto = min(max(float(pct_nivel) * n_nivel / 100 - k, 0.0), float(n_resto))
    _, inferior, _ = wilson(k, n)
    _, _, superior_resto = wilson(k_resto, n_resto)
    return ac.PRIORIDAD if inferior > superior_resto else ac.PRESENTE


def estado_total(pct) -> str:
    """El nivel es la referencia de las comparaciones."""
    return ac.SIN_ESTADO if _vacio(pct) else ac.REFERENCIA


# ── Tabla plana: lo que leen las vistas y lo que se publica ─────────────────
def _orden_grupo(agrupacion: str, grupo: str, nivel: str) -> tuple:
    grados = cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.ORDEN_GRADOS_PRI

    def pos(g):
        return (grados.index(g) if g in grados else 99, str(g))
    if agrupacion == TOTAL:
        return (0, (0, ""), (0, ""))
    if agrupacion == "Colegio":
        return (1, (0, str(grupo)), (0, ""))
    if agrupacion == "Grado":
        return (2, pos(grupo), (0, ""))
    colegio, grado = privacidad.partir_celda(grupo)
    return (3, (0, colegio), pos(grado))


def ordenar(tabla: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Orden canónico: alerta del catálogo, nivel, colegios, grados y celdas."""
    if tabla is None or len(tabla) == 0:
        return pd.DataFrame(columns=COLUMNAS_TABLA)
    orden_alerta = {k: i for i, k in enumerate(ac.ALERTAS)}
    claves = [(orden_alerta.get(a, 99), _orden_grupo(ag, str(g), nivel))
              for a, ag, g in zip(tabla["alerta"], tabla["agrupacion"], tabla["grupo"])]
    posiciones = sorted(range(len(tabla)), key=lambda i: claves[i])
    return tabla.iloc[posiciones].reset_index(drop=True)[COLUMNAS_TABLA]


def _num(v):
    return None if _vacio(v) else float(v)


def tabla(a) -> pd.DataFrame:
    """Una fila por alerta y grupo, desde las tablas YA suprimidas. Sin casos, nunca.

    Se llama después de `supresion.aplicar`. El estado sale de `estado`, que
    solo mira cifras publicadas.
    """
    propia = getattr(a, "cortes_alerta", None)
    if not isinstance(propia, pd.DataFrame) or propia.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA)
    nivel = getattr(a, "nivel", None)
    ref: dict[str, tuple] = {}
    filas: list[dict] = []
    for f in propia.to_dict("records"):
        if int(f["n"]) < cat.MIN_GROUP_N:
            continue
        ref[f["clave"]] = (_num(f["pct"]), int(f["n"]))
        filas.append(dict(alerta=f["clave"], agrupacion=TOTAL, grupo=TODOS, n=int(f["n"]),
                          pct=_num(f["pct"]), ic_inf=_num(f["ic_inf"]),
                          ic_sup=_num(f["ic_sup"]), estado=estado_total(f["pct"])))
    for agrupacion in AGRUPACIONES:
        for grupo, s in ((getattr(a, "subgrupos", None) or {}).get(agrupacion) or {}).items():
            t = getattr(s, "cortes_alerta", None)
            if not isinstance(t, pd.DataFrame) or t.empty:
                continue
            for f in t.to_dict("records"):
                if int(f["n"]) < cat.MIN_GROUP_N or f["clave"] not in ref:
                    continue
                pct_nivel, n_nivel = ref[f["clave"]]
                filas.append(dict(alerta=f["clave"], agrupacion=agrupacion, grupo=str(grupo),
                                  n=int(f["n"]), pct=_num(f["pct"]),
                                  ic_inf=_num(f["ic_inf"]), ic_sup=_num(f["ic_sup"]),
                                  estado=estado(f["pct"], f["n"], pct_nivel, n_nivel)))
    return ordenar(pd.DataFrame(filas, columns=COLUMNAS_TABLA), nivel)


# ── Sensibilidad y distribución de ítems (solo el nivel, solo local) ────────
def sensibilidad(dn: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Prevalencia del nivel con cada variante de umbral o de regla. Solo local.

    Todas las variantes de una alerta usan las mismas filas (las que tienen
    todas sus variantes). Las variantes están anidadas (2 ⊇ 3 ⊇ 4; amplia ⊇
    estricta), así que se muestran todas o ninguna: el reparto anidado
    (n − k_a, k_a − k_b, …) tiene que cumplir `supresion.partes_publicables`.
    """
    if dn is None or dn.empty:
        return pd.DataFrame(columns=COLUMNAS_SENSIBILIDAD)
    filas: list[dict] = []
    for alerta in claves_del_nivel(dn, nivel):
        variantes = [(v, col, etq, vig) for v, (a, col, etq, vig) in VARIANTES.items()
                     if a == alerta and col in dn.columns]
        X = dn[[col for _, col, _, _ in variantes]].dropna()
        n = len(X)
        if n < cat.MIN_GROUP_N:
            continue
        ks = {v: int(X[col].sum()) for v, col, _, _ in variantes}
        anidados = sorted(ks.values(), reverse=True)
        partes = ([n - anidados[0]] + [anidados[i] - anidados[i + 1]
                                       for i in range(len(anidados) - 1)] + [anidados[-1]])
        ver = supresion.partes_publicables(partes)
        for v, _, etiqueta, vig in variantes:
            pct, ic_inf, ic_sup = wilson(ks[v], n) if ver else (None, None, None)
            filas.append(dict(alerta=alerta, variante=v, etiqueta=etiqueta, vigente=vig,
                              n=n, pct=pct, ic_inf=ic_inf, ic_sup=ic_sup))
    return pd.DataFrame(filas, columns=COLUMNAS_SENSIBILIDAD)


def distribucion_items(dn: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """% de cada respuesta en los ítems de las alertas, en el nivel. Solo local.

    El reparto de respuestas de un ítem se muestra entero o no se muestra
    (`supresion.partes_publicables`): con una respuesta oculta, se deduciría
    restando las demás de n.
    """
    if dn is None or dn.empty:
        return pd.DataFrame(columns=COLUMNAS_ITEMS)
    filas: list[dict] = []
    for alerta in claves_del_nivel(dn, nivel):
        a = ac.ALERTAS[alerta]
        items = a.items if alerta == ac.MALESTAR else ac.ITEMS_REGLA_AMPLIA
        etiquetas = ETIQUETAS_RESPUESTA[a.escala]
        for i in items:
            col = f"{a.escala}{i}"
            if col not in dn.columns:
                continue
            v = dn[col].dropna()
            n = len(v)
            if n < cat.MIN_GROUP_N:
                continue
            conteos = [int((v == codigo).sum()) for codigo in range(len(etiquetas))]
            ver = supresion.partes_publicables(conteos)
            for etiqueta, c in zip(etiquetas, conteos):
                filas.append(dict(alerta=alerta, item=col,
                                  enunciado=ac.ENUNCIADOS_ITEMS.get(col, col),
                                  respuesta=etiqueta, n=n,
                                  pct=round(100 * c / n, 1) if ver else None))
    return pd.DataFrame(filas, columns=COLUMNAS_ITEMS)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/alertas.py tests/test_alertas.py
git commit -m "feat(alertas): tabla por grupo, estado con cifras publicadas y tablas locales" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Las alertas pasan por la supresión general y el pipeline las calcula

**Files:**
- Modify: `src/estudiantes/supresion.py`
- Modify: `src/estudiantes/pipeline.py`
- Modify: `tests/test_alertas.py`
- Create: `tests/test_alertas_publicar.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

En `tests/test_alertas.py`, añadir a los imports:

```python
import random

from src.estudiantes import pipeline
from tests.test_estudiantes_comunidad import CON_RESTO, PRIMARIA
from tests.test_supresion_propiedades import _fuerza_bruta
```

y al final (las tres configuraciones reales de resta reutilizan `PRIMARIA` y `CON_RESTO` de `tests/test_estudiantes_comunidad.py`; la prueba de fuerza bruta reutiliza `_fuerza_bruta` de `tests/test_supresion_propiedades.py`):

```python
# ══ Cifras de las alertas: la supresión general ═════════════════════════════
# Las tres configuraciones reales de resta: todo en celdas; colegio publicado
# entero sin celdas y respuestas fuera del nivel (primaria, oct-2026); resto R
# dentro del nivel (CON_RESTO).
TODO_EN_CELDAS = {("A", "Sexto"): 20, ("B", "Sexto"): 30, ("C", "Sexto"): 15,
                  ("A", "Séptimo"): 20}
CONFIGURACIONES = [(cat.NIVEL_SECUNDARIA, TODO_EN_CELDAS), (cat.NIVEL_PRIMARIA, PRIMARIA),
                   (cat.NIVEL_SECUNDARIA, CON_RESTO)]
ITEMS_MALESTAR = ac.ALERTAS[ac.MALESTAR].items


def _datos_config(nivel, conteos: dict, semilla: int) -> pd.DataFrame:
    """Filas con ítems ya codificados. Probabilidades bajas: muchas celdas con 0 a 2 casos."""
    rng = random.Random(semilla)
    p_mal, p_des, p_18 = rng.choice([.03, .08, .2]), rng.choice([.03, .1]), rng.choice([.05, .2])
    filas = []
    for (c, g), n in conteos.items():
        for i in range(n):
            f = dict(Colegio=c, Grado=g, Sexo="Mujer" if i % 2 else "Hombre", Edad=13,
                     nivel=nivel)
            malestar = rng.random() < p_mal
            for item in ITEMS_MALESTAR:
                f[f"SDQ{item}"] = ac.MUY_CIERTO if malestar and item in (5, 6, 8) else 0
            if nivel == cat.NIVEL_SECUNDARIA:
                u = rng.random()
                muerte = (ac.SIEMPRE if u < p_des else ac.CON_FRECUENCIA if u < p_des + p_18
                          else 0)
                f.update(RCADS1=0, RCADS4=0, RCADS16=0, RCADS18=muerte)
            filas.append(f)
    return pd.DataFrame(filas)


def _nombre(agrupacion: str, grupo: str):
    return supresion.NIVEL if agrupacion == al.TOTAL else (agrupacion, str(grupo))


def _partes_reales(a, alerta: str):
    """{átomo: partes} desde los datos enmascarados, sin pasar por la supresión."""
    familia = al.ANIDADA.get(alerta, "")
    partes = {}
    for at, idx in supresion.indices_atomos(a.base).items():
        sub = a.datos.loc[a.datos.index.intersection(idx)]
        s = sub[al.COLUMNAS[alerta]].dropna() if al.COLUMNAS[alerta] in sub else pd.Series(dtype=float)
        k, n = int(s.sum()), len(s)
        if familia:
            k18 = int((sub[familia].dropna() >= ac.CON_FRECUENCIA).sum())
            partes[at] = (n - k18, k18 - k, k)
        else:
            partes[at] = (n - k, k)
    return partes


@pytest.mark.parametrize("nivel,conteos", CONFIGURACIONES)
def test_lo_publicado_de_las_alertas_resiste_restas(nivel, conteos):
    """Fuerza bruta: ningún conjunto de átomos deducible de lo publicado incumple la regla."""
    for semilla in range(12):
        a = pipeline.analizar(_datos_config(nivel, conteos, semilla), nivel, n_boot=5)
        assert supresion.auditar(a) == [], semilla
        jer = supresion.jerarquia(list(a.base.celdas), list(a.base.colegios),
                                  list(a.base.grados), con_resto=a.base.incluye_resto)
        for alerta in al.claves_del_nivel(a.datos, nivel):
            t = a.alertas[a.alertas["alerta"] == alerta]
            pub = {_nombre(f["agrupacion"], f["grupo"]) for f in t.to_dict("records")
                   if f["pct"] is not None and not pd.isna(f["pct"])}
            partes = _partes_reales(a, alerta)
            assert _fuerza_bruta(jer, partes, pub) == set(), (semilla, alerta)
            for f in t.to_dict("records"):
                if pd.isna(f["pct"]):
                    assert f["estado"] == ac.SIN_ESTADO and pd.isna(f["ic_inf"])


def test_los_grados_y_las_celdas_llevan_porcentaje_cuando_se_puede():
    conteos = {("A", "Sexto"): 40, ("A", "Séptimo"): 40, ("B", "Sexto"): 40,
               ("B", "Séptimo"): 40}
    filas = []
    for (c, g), n in conteos.items():
        k = 30 if (c, g) == ("A", "Sexto") else 6
        for i in range(n):
            f = dict(Colegio=c, Grado=g, Sexo="Mujer", Edad=13, nivel=cat.NIVEL_SECUNDARIA)
            f.update({f"SDQ{j}": ac.MUY_CIERTO if i < k and j in (5, 6, 8) else 0
                      for j in ITEMS_MALESTAR})
            filas.append(f)
    a = pipeline.analizar(pd.DataFrame(filas), cat.NIVEL_SECUNDARIA, n_boot=5)
    t = a.alertas.set_index(["agrupacion", "grupo"])
    for clave in (("Grado", "Sexto"), ("Grado", "Séptimo"), (al.CRUCE, "A|Sexto"),
                  ("Colegio", "A")):
        assert not pd.isna(t.loc[clave, "pct"]), clave
    assert t.loc[(al.CRUCE, "A|Sexto"), "estado"] == ac.PRIORIDAD
    assert t.loc[("Grado", "Séptimo"), "estado"] == ac.PRESENTE
    assert t.loc[(al.TOTAL, al.TODOS), "estado"] == ac.REFERENCIA
    assert list(a.alertas.columns) == al.COLUMNAS_TABLA and "casos" not in a.alertas


def test_la_desesperanza_nunca_se_publica_donde_el_item_18_esta_suprimido():
    for semilla in range(12):
        a = pipeline.analizar(_datos_config(cat.NIVEL_SECUNDARIA, CON_RESTO, semilla),
                              cat.NIVEL_SECUNDARIA, n_boot=5)
        for g, o in supresion._objetos(a).items():
            if supresion._publicado_alerta(o, ac.DESESPERANZA):
                assert supresion._publicado(o, al.ANIDADA[ac.DESESPERANZA]), (semilla, g)


def test_si_las_bases_no_coinciden_la_desesperanza_no_se_publica():
    d = _datos_config(cat.NIVEL_SECUNDARIA, TODO_EN_CELDAS, 1)
    d.loc[d.index[:3], "RCADS16"] = np.nan       # 18 respondido, 16 no: bases distintas
    a = pipeline.analizar(d, cat.NIVEL_SECUNDARIA, n_boot=5)
    des = a.alertas[a.alertas["alerta"] == ac.DESESPERANZA]
    assert len(des) and des["pct"].isna().all()
    assert (des["estado"] == ac.SIN_ESTADO).all()
    assert supresion.auditar(a) == []


def test_la_auditoria_detecta_una_alerta_destapada():
    import copy
    for semilla in range(12):
        a = pipeline.analizar(_datos_config(cat.NIVEL_SECUNDARIA, TODO_EN_CELDAS, semilla),
                              cat.NIVEL_SECUNDARIA, n_boot=5)
        celda = a.subgrupos[al.CRUCE]["A|Sexto"]
        t = celda.cortes_alerta
        fila = t["clave"] == ac.MALESTAR
        if fila.any() and t.loc[fila, "pct"].isna().all():
            b = copy.deepcopy(a)
            b.subgrupos[al.CRUCE]["A|Sexto"].cortes_alerta.loc[fila, "pct"] = 5.0
            assert any(p.startswith("alerta malestar") for p in supresion.auditar(b))
            return
    pytest.fail("ninguna semilla dejó la celda suprimida")


def test_suprimir_nunca_destapa_lo_que_ya_venia_oculto():
    jer = supresion.jerarquia(["A|Sexto", "B|Sexto"], ["A", "B"], ["Sexto"], con_resto=False)
    partes = {supresion.atomo_celda("A|Sexto"): (20, 10), supresion.atomo_celda("B|Sexto"): (20, 10)}
    assert supresion.suprimir(jer, partes) == set()
    sup = supresion.suprimir(jer, partes, previos={supresion.COLEGIO("A")})
    assert supresion.COLEGIO("A") in sup


@pytest.mark.parametrize("semilla", range(6))
def test_el_estado_de_la_tabla_se_reproduce_con_lo_publicado(semilla):
    """Con las cifras publicadas de la tabla (sin datos) sale el mismo estado."""
    a = pipeline.analizar(_datos_config(*CONFIGURACIONES[0], semilla=semilla), CONFIGURACIONES[0][0],
                          n_boot=5)
    t = a.alertas
    for f in t[t["agrupacion"] != al.TOTAL].to_dict("records"):
        nivel = t[(t["alerta"] == f["alerta"]) & (t["agrupacion"] == al.TOTAL)].iloc[0]
        assert f["estado"] == al.estado(f["pct"], f["n"], nivel["pct"], nivel["n"])
```

`tests/test_alertas_publicar.py` (las secciones de publicar, Supabase y lectura se añaden en las Tasks 6 a 8):

```python
"""Alertas de punta a punta sin red: pipeline → publicar → leer (spec §5.4 y §7)."""
import os
import random

import pandas as pd
import pytest

from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring, supresion
from tests.test_alertas import CONFIGURACIONES, _datos_config
from tests.test_estudiantes_comunidad import GRADO_PEQUENO, _formulario


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)


@pytest.fixture(scope="module")
def primaria():
    raw = _formulario()
    raw = raw.drop(columns=[c for c in raw.columns if c.startswith("RCADS")])
    bruto, _ = ingest.cargar(raw)
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_PRIMARIA, n_boot=20)


@pytest.fixture(scope="module", params=range(len(CONFIGURACIONES)))
def config(request):
    nivel, conteos = CONFIGURACIONES[request.param]
    return nivel, pipeline.analizar(_datos_config(nivel, conteos, 5), nivel, n_boot=5)


# ══ Pipeline ════════════════════════════════════════════════════════════════
def test_el_analisis_trae_las_alertas_por_grupo(analisis):
    t = analisis.alertas
    assert list(t.columns) == al.COLUMNAS_TABLA and "casos" not in t.columns
    assert set(t["alerta"]) == {"malestar", "desesperanza"}
    assert t[t["agrupacion"] == al.TOTAL]["pct"].notna().all()
    assert not t["grupo"].astype(str).str.contains("DiosCh").any()
    assert GRADO_PEQUENO not in set(t["grupo"].astype(str))
    # cada subgrupo trae su tabla, que es la que pasa por la supresión
    celda = analisis.subgrupos[al.CRUCE]["LauV|Octavo"]
    assert list(celda.cortes_alerta.columns) == al.COLUMNAS_CORTES


def test_las_senales_individuales_quedan_solo_en_los_datos_locales(analisis):
    assert {"ALERTA_malestar", "ALERTA_desesperanza"} <= set(analisis.datos.columns)


def test_la_auditoria_de_restas_cubre_las_senales(analisis):
    assert publicar.verificar_restas({cat.NIVEL_SECUNDARIA: analisis}) == []


def test_primaria_solo_tiene_malestar(primaria):
    assert set(primaria.alertas["alerta"]) == {"malestar"}
    assert set(primaria.alertas_sensibilidad["alerta"]) == {"malestar"}


def test_sensibilidad_e_items_del_nivel(analisis):
    assert set(analisis.alertas_sensibilidad["variante"]) == set(al.VARIANTES)
    assert set(analisis.alertas_items["item"]) == {
        "SDQ5", "SDQ6", "SDQ8", "SDQ13", "SDQ19", "SDQ24",
        "RCADS1", "RCADS4", "RCADS16", "RCADS18"}
```

Run: `.venv/bin/python -m pytest tests/test_alertas.py tests/test_alertas_publicar.py -q`
Expected: FAIL (`AttributeError: module 'src.estudiantes.supresion' has no attribute 'indices_atomos'` y `'Analisis' object has no attribute 'alertas'`).

- [ ] **Step 2: `supresion.py`**

1. Docstring del módulo: justo antes de la sección `CONTRASTES`, añadir:

```text
ALERTAS DE GRUPO (fase 3, alertas.py)
Cada objeto (nivel y subgrupos) trae `cortes_alerta`, con la forma de `cortes`.
Una alerta es una familia más con la misma jerarquía: binaria (n − k, k) o, si
está anidada en un corte (desesperanza ⊆ RCADS18 ≥ «Con frecuencia»), repartida
en (n − k_F, k_F − k, k) sobre la base de ese corte. La anidada se suprime
después de su corte y parte de lo que este ocultó (`suprimir(previos=…)`): así
nunca se publica donde el corte no se publica, y lo deducible de las dos juntas
queda dentro de lo que audita `fugas` sobre el reparto de tres partes. Si las
bases no coinciden en algún grupo, la alerta no se publica en ninguno (falla
cerrado).

```

2. `suprimir`: reemplazar la firma, el docstring y la primera línea del cuerpo

```python
def suprimir(jer: Jerarquia, partes: dict, minimo: int = MIN_CASOS) -> set:
    """Agregados que no se publican para un indicador (primaria + complementaria).

    `partes` = {átomo: (conteo de cada parte)}. Incluye los agregados sin
    respuestas válidas (n = 0) y los que nunca se publican (R).
    """
    largo = _largo(partes)
    sup = set(jer.nunca)
```

por

```python
def suprimir(jer: Jerarquia, partes: dict, minimo: int = MIN_CASOS,
             previos=frozenset()) -> set:
    """Agregados que no se publican para un indicador (primaria + complementaria).

    `partes` = {átomo: (conteo de cada parte)}. Incluye los agregados sin
    respuestas válidas (n = 0) y los que nunca se publican (R). `previos` son
    agregados que ya vienen ocultos (p. ej. los de la familia en la que una
    alerta está anidada): se parte de ellos y nunca se destapan.
    """
    largo = _largo(partes)
    sup = set(jer.nunca) | set(previos)
```

3. `_anular`: reemplazar

```python
def _anular(obj, clave: str) -> int:
    """Deja en blanco las proporciones de `clave` en las tablas de `obj`. Filas tocadas."""
    tocadas = 0
    for nombre, columnas in (("cortes", COLUMNAS_CORTE_NULAS), ("bandas", COLUMNAS_BANDA_NULAS)):
```

por

```python
TABLAS_FAMILIA = (("cortes", COLUMNAS_CORTE_NULAS), ("bandas", COLUMNAS_BANDA_NULAS))
TABLAS_ALERTA = (("cortes_alerta", COLUMNAS_CORTE_NULAS),)


def _anular(obj, clave: str, tablas=TABLAS_FAMILIA) -> int:
    """Deja en blanco las proporciones de `clave` en las tablas de `obj`. Filas tocadas."""
    tocadas = 0
    for nombre, columnas in tablas:
```

4. Justo antes de `def aplicar(`:

```python
def indices_atomos(base) -> dict:
    """{átomo: índices de filas} de la base publicable (privacidad.Base)."""
    from src.estudiantes import privacidad
    con_celdas = {k.split(SEP, 1)[0] for k in base.celdas}
    indices = {atomo_celda(k): idx for k, idx in base.celdas.items()}
    indices.update({atomo_colegio(c): idx for c, idx in base.colegios.items()
                    if c not in con_celdas})
    if base.incluye_resto:
        indices[RESTO] = base.nivel.difference(privacidad.union(base.colegios.values()))
    return indices


# ── alertas de grupo (fase 3): una familia binaria más, o anidada en un corte ──
def _fila_alerta(t, clave: str):
    if _vacia(t):
        return None
    filas = t[t["clave"].astype(str) == clave]
    return None if filas.empty else filas.iloc[0]


def _anidada_en(tablas, clave: str) -> str:
    """Familia de cortes en la que está anidada la alerta («» si es binaria)."""
    for t in tablas:
        f = _fila_alerta(t, clave)
        if f is not None and "anidada_en" in f.index and str(f["anidada_en"] or ""):
            return str(f["anidada_en"])
    return ""


def partes_alerta(t_alerta, fam: dict, clave: str, familia: str) -> tuple | None:
    """Partes de una alerta en un grupo, desde su tabla `cortes_alerta` (con conteos).

    Binaria: (n − k, k). Anidada en la familia `familia` de los cortes (la
    alerta implica el corte; p. ej. desesperanza ⊆ RCADS18 ≥ 2): la base del
    corte se reparte en (n − k_F, k_F − k, k). None si no se puede repartir
    así (bases distintas o alerta fuera del corte): la alerta no se publica.
    """
    f = _fila_alerta(t_alerta, clave)
    n_a = 0 if f is None or pd.isna(f["n"]) else int(f["n"])
    if f is not None and n_a and pd.isna(f["casos"]):
        return None                       # ya suprimida: sin conteos
    k_a = 0 if not n_a else int(f["casos"])
    if not familia:
        return (n_a - k_a, k_a)
    fp = fam.get(familia, (0, 0))
    if len(fp) != 2:
        return None
    n_f, k_f = int(sum(fp)), int(fp[1])
    if n_f != n_a or k_a > k_f:
        return None
    return (n_f - k_f, k_f - k_a, k_a)


def _publicado_alerta(obj, clave: str) -> bool:
    f = _fila_alerta(getattr(obj, "cortes_alerta", None), clave)
    return f is not None and not pd.isna(f["pct"])


def _aplicar_alertas(jer, objs: dict, atomos: dict, fam: dict, sup_familias: dict,
                     minimo: int, resumen: dict) -> None:
    """Supresión de las alertas de grupo con la misma jerarquía que los cortes."""
    tablas = {g: getattr(o, "cortes_alerta", None) for g, o in objs.items()}
    claves = sorted({str(c) for t in tablas.values() if not _vacia(t) for c in t["clave"]})
    for clave in claves:
        familia = _anidada_en(tablas.values(), clave)
        por_grupo = {g: partes_alerta(t, fam[g], clave, familia) for g, t in tablas.items()}
        sup: set
        if any(p is None for p in por_grupo.values()):
            sup = set(objs)                       # falla cerrado: nada de esta alerta
        else:
            largo = 3 if familia else 2
            cero = np.zeros(largo, dtype=np.int64)
            partes = {a_: np.asarray(por_grupo[g]) for a_, g in atomos.items()}
            resto = np.asarray(por_grupo[NIVEL]) - sum(partes.values(), cero)
            if (resto < 0).any():
                raise ValueError(f"{clave}: los subgrupos suman más que el nivel")
            partes[RESTO] = resto
            previos = sup_familias.get(familia, set()) if familia else set()
            sup = suprimir(jer, {k: tuple(v) for k, v in partes.items()}, minimo,
                           previos=previos)
        for g in sup:
            if g in objs and _anular(objs[g], clave, TABLAS_ALERTA):
                clave_res = (g[0], f"alerta:{clave}")
                resumen[clave_res] = resumen.get(clave_res, 0) + 1
```

5. En `aplicar`:
   - Después de `resumen: dict = {}`, añadir `sup_familias: dict[str, set] = {}`.
   - Reemplazar

     ```python
             for g in suprimir(jer, {k: tuple(v) for k, v in partes.items()}, minimo):
                 if g in objs:
     ```

     por

     ```python
             sup_familias[clave] = suprimir(jer, {k: tuple(v) for k, v in partes.items()}, minimo)
             for g in sup_familias[clave]:
                 if g in objs:
     ```

   - Justo antes de `for g, o in objs.items():` (el bucle de contrastes e ítems), añadir:

     ```python
         # Alertas de grupo (fase 3): después de los cortes, porque una alerta anidada
         # en un corte nunca se publica donde ese corte está suprimido.
         _aplicar_alertas(jer, objs, atomos, fam, sup_familias, minimo, resumen)
     ```

6. En `auditar`, reemplazar

```python
    con_celdas = {k.split(SEP, 1)[0] for k in base.celdas}
    indices = {atomo_celda(k): idx for k, idx in base.celdas.items()}
    indices.update({atomo_colegio(c): idx for c, idx in base.colegios.items()
                    if c not in con_celdas})
    if base.incluye_resto:
        indices[RESTO] = base.nivel.difference(privacidad.union(base.colegios.values()))
```

por `    indices = indices_atomos(base)`, y justo antes de `problemas += auditar_solapamiento(` añadir:

```python
    problemas += _auditar_alertas(a, jer, indices, fam, objs, minimo)
```

7. Al final del archivo:

```python
def _auditar_alertas(a, jer, indices: dict, fam: dict, objs: dict,
                     minimo: int = MIN_CASOS) -> list[str]:
    """Las alertas publicadas, recalculadas desde `a.datos` (alertas.cortes_alerta)."""
    from src.estudiantes import alertas
    d = a.datos
    tablas_atomo = {}
    for at, idx in indices.items():
        sub = d.loc[d.index.intersection(idx)]
        tablas_atomo[at] = alertas.cortes_alerta(sub, a.nivel) if len(sub) else None
    claves = sorted({str(c) for o in objs.values()
                     if not _vacia(getattr(o, "cortes_alerta", None))
                     for c in o.cortes_alerta["clave"]})
    problemas: list[str] = []
    for clave in claves:
        familia = alertas.ANIDADA.get(clave, "")
        pub = {g for g, o in objs.items() if _publicado_alerta(o, clave)}
        if not pub:
            continue
        por_atomo = {at: partes_alerta(t, fam.get(at, {}), clave, familia)
                     for at, t in tablas_atomo.items()}
        if any(p is None for p in por_atomo.values()):
            problemas.append(f"alerta {clave}: se publica aunque su base no coincide con la "
                             f"del corte {familia} en algún grupo")
            continue
        largo = 3 if familia else 2
        for g in sorted(pub, key=str):
            if g not in jer.grupos:
                problemas.append(f"alerta {clave}: {g[0]} {g[1]} publicado fuera de la base")
                continue
            if familia and not _publicado(objs[g], familia):
                problemas.append(f"alerta {clave}: {g[0]} {g[1] or ''} publica la alerta con "
                                 f"el corte {familia} suprimido")
            if not partes_publicables(_suma(jer.grupos[g], por_atomo, largo), minimo):
                problemas.append(f"alerta {clave}: {g[0]} {g[1] or ''} publica una proporción "
                                 f"con menos de {minimo} casos o no casos")
        for s_ in fugas(jer, por_atomo, pub & set(jer.grupos), minimo):
            problemas.append(f"alerta {clave}: una resta entre cifras publicadas deja un "
                             f"conjunto de {len(s_)} grupo(s) con menos de {minimo} casos o "
                             "no casos")
    return problemas
```

- [ ] **Step 3: `pipeline.py`**

1. Import: `from src.estudiantes import alertas, ingest, privacidad, scoring, stats, supresion`.
2. En `class Analisis`, después de `subgrupos: dict = field(default_factory=dict)` y antes del comentario de `base`:

```python
    # Alertas de grupo (spec §5.4, alertas.py). `cortes_alerta`: una fila por
    # alerta con la forma de `cortes` (con casos, que nunca se publican); la
    # tienen el nivel y cada subgrupo, y la supresión la trata como una familia
    # más. `alertas`: la tabla plana por grupo que leen las vistas y que se
    # publica, sin casos. Sensibilidad e ítems: solo locales, del nivel. Todas
    # vacías en una corrida anterior a la fase 3.
    cortes_alerta: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas_sensibilidad: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas_items: pd.DataFrame = field(default_factory=pd.DataFrame)
```

3. En `analizar`, justo después de `d = datos_puntuados[...]` (antes de `claves = …`):

```python
    # Señal de alerta por estudiante (1 / 0 / NaN). Entra en la base publicable y
    # en el todo o nada como cualquier otra columna, así que la auditoría de
    # restas de n la cubre. Nunca se publica fila a fila.
    d = alertas.marcar(d, nivel)
```

4. Después de `a.cortes = scoring.sobre_cortes(dn)`: `a.cortes_alerta = alertas.cortes_alerta(dn, nivel)`.
5. Reemplazar `    supresion.aplicar(a)` por:

```python
    supresion.aplicar(a)
    # Después de la supresión: la tabla plana solo lleva lo que quedó publicable
    # y el estado se calcula con esas cifras.
    a.alertas = alertas.tabla(a)
    a.alertas_sensibilidad = alertas.sensibilidad(dn, nivel)
    a.alertas_items = alertas.distribucion_items(dn, nivel)
```

6. En `subanalizar`, después de `s.cortes = scoring.sobre_cortes(sub)`: `            s.cortes_alerta = alertas.cortes_alerta(sub, nivel)`.

- [ ] **Step 4: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py tests/test_alertas_publicar.py tests/test_alertas_regresion.py tests/test_supresion.py tests/test_supresion_pipeline.py tests/test_supresion_propiedades.py tests/test_supresion_vistas.py tests/test_estudiantes.py tests/test_estudiantes_subgrupos.py tests/test_privacidad.py -q`
Expected: todo pasa. La no regresión sigue idéntica: las columnas `ALERTA_*` se enmascaran por separado y la supresión de las alertas corre después de la de los cortes, sin tocarlos.

- [ ] **Step 5: Commit**

```bash
git add src/estudiantes/supresion.py src/estudiantes/pipeline.py tests/test_alertas.py tests/test_alertas_publicar.py
git commit -m "feat(alertas): las alertas pasan por la supresión general; el análisis las trae" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Publicar sin casos

**Files:**
- Modify: `src/estudiantes/publicar.py`
- Modify: `tests/test_alertas_publicar.py`, `tests/test_estudiantes_publicar.py` (`test_el_lote_real_solo_tiene_tipos_y_agrupaciones_previstas` y `test_ninguna_fila_viene_de_datos_individuales`), `tests/test_restas_publicadas.py:27`

- [ ] **Step 1: Escribir las pruebas que fallan**

Al final de `tests/test_alertas_publicar.py`:

```python
# ══ Publicar ════════════════════════════════════════════════════════════════
def _filas(a, nivel=cat.NIVEL_SECUNDARIA):
    return publicar.aplanar({nivel: a})


def test_las_alertas_se_publican_sin_casos(config):
    nivel, a = config
    filas = _filas(a, nivel)
    alertas = [f for f in filas if f["tipo"].startswith("alerta")]
    assert {f["tipo"] for f in alertas} == {"alerta", "alerta_grupo"}
    for f in alertas:
        assert not set(f["detalle"]) & set(publicar.CAMPOS_CONTEO_PROHIBIDOS)
        if f["valor"] is None:
            assert f["ic_inf"] is None and f["detalle"]["estado"] == ac.SIN_ESTADO
        else:
            # la regla, fila por fila: k = % × n queda en [3, n − 3]
            k = round(f["valor"] * f["n"] / 100)
            assert supresion.MIN_CASOS <= k <= f["n"] - supresion.MIN_CASOS
        if f["tipo"] == "alerta_grupo":
            assert f["detalle"]["n_grupo"] >= cat.MIN_GROUP_N
    publicar.verificar(filas)
    assert publicar.verificar_restas({nivel: a}) == []


def test_no_se_publican_sensibilidad_ni_items(analisis):
    tipos = {f["tipo"] for f in _filas(analisis)}
    assert not {"alerta_sensibilidad", "alerta_item"} & tipos


def test_verificar_rechaza_una_alerta_con_casos(analisis):
    fila = next(f for f in _filas(analisis) if f["tipo"] == "alerta")
    mala = dict(fila, detalle=dict(fila["detalle"], casos=5))
    with pytest.raises(publicar.PublicacionInsegura, match="casos"):
        publicar.verificar([mala])


def test_verificar_rechaza_un_estado_sin_porcentaje(analisis):
    fila = next(f for f in _filas(analisis) if f["tipo"] == "alerta_grupo")
    mala = dict(fila, valor=None, ic_inf=None, ic_sup=None,
                detalle=dict(fila["detalle"], estado=ac.PRIORIDAD))
    with pytest.raises(publicar.PublicacionInsegura, match="estado"):
        publicar.verificar([mala])


def test_verificar_restas_bloquea_una_alerta_destapada(config):
    import copy
    nivel, a = config
    for agrupacion, grupos in a.subgrupos.items():
        for grupo, s in grupos.items():
            t = s.cortes_alerta
            if len(t) and t["pct"].isna().any():
                b = copy.deepcopy(a)
                tb = b.subgrupos[agrupacion][grupo].cortes_alerta
                tb.loc[tb["pct"].isna(), "pct"] = 5.0
                assert any("alerta" in p for p in publicar.verificar_restas({nivel: b}))
                return
    pytest.skip("esta configuración no suprime ninguna alerta de subgrupo")
```

`test_las_alertas_se_publican_sin_casos` es la prueba fila por fila que sustituye a la vieja búsqueda de textos «k de n» en el HTML: ninguna fila de alerta trae un campo de conteo, y donde hay porcentaje, `k = % × n` queda en `[3, n − 3]`.

En `tests/test_estudiantes_publicar.py`:
- En `test_el_lote_real_solo_tiene_tipos_y_agrupaciones_previstas`, reemplazar `"banda_grupo", "corte_grupo", "contraste_grupo", "item_grupo"}` por:

  ```python
                       "banda_grupo", "corte_grupo", "contraste_grupo", "item_grupo",
                       # alertas de grupo (fase 3), sin casos
                       "alerta", "alerta_grupo"}
  ```

- En `test_ninguna_fila_viene_de_datos_individuales`, reemplazar `tope = 6 + 16 + 4 + 18   # bandas + cortes + contrastes + ítems del PSSM` por `tope = 6 + 16 + 4 + 18 + 2   # bandas + cortes + contrastes + ítems del PSSM + alertas`.

En `tests/test_restas_publicadas.py:27`: `TIPOS = ("corte", "banda", "item", "alerta")   # «alerta»: alertas de grupo (fase 3)`. La resta de `n` cubre también las alertas (`alerta_grupo` lleva el mismo `indicador` que `alerta`).

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q`
Expected: FAIL (no hay filas `alerta…`).

- [ ] **Step 2: Implementar**

En `src/estudiantes/publicar.py`:

1. Docstring, sección QUÉ SUBE: reemplazar

```text
Solo agregados: una fila por nivel, grupo, tipo e indicador. Ni una respuesta
individual, ni un identificador, ni un nombre.
```

por

```text
Solo agregados: una fila por nivel, grupo, tipo e indicador. Ni una respuesta
individual, ni un identificador, ni un nombre. Las alertas de grupo (`alerta` y
`alerta_grupo`, spec §5.4) llevan n, % e IC donde la supresión los deja, y el
estado solo donde hay %; nunca casos. La sensibilidad y la distribución de los
ítems de las alertas no se publican: son de la vista local de investigadores.
```

2. En `aplanar`, justo antes de `        # descripción de la muestra, en una sola fila cuyo N es el del nivel`:

```python
        # alertas de grupo (spec §5.4): sin casos; estado solo donde hay %
        filas.extend(_aplanar_alertas(nivel, a))

```

3. Justo antes de `def _enmascarar_conteos(`:

```python
def _aplanar_alertas(nivel: str, a) -> list[dict]:
    """Filas `alerta` (nivel) y `alerta_grupo` desde `Analisis.alertas`. Nunca casos.

    La tabla ya viene suprimida (supresion.aplicar) y con el estado calculado
    solo con cifras publicadas (alertas.estado).
    """
    from src.estudiantes import alertas as al
    from src.estudiantes import alertas_catalogo as ac
    tabla = getattr(a, "alertas", None)
    if not isinstance(tabla, pd.DataFrame) or tabla.empty:
        return []
    subgrupos = getattr(a, "subgrupos", None) or {}
    filas: list[dict] = []
    for f in tabla.to_dict("records"):
        if int(f["n"]) < cat.MIN_GROUP_N or f["alerta"] not in ac.ALERTAS:
            continue
        nombre = ac.ALERTAS[f["alerta"]].nombre
        comun = dict(escala=nombre, ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                     indicador=nombre, estado=str(f["estado"]))
        if f["agrupacion"] == al.TOTAL:
            filas.append(_fila(nivel, "alerta", f["alerta"], f["n"], f["pct"], **comun))
            continue
        s = (subgrupos.get(f["agrupacion"]) or {}).get(str(f["grupo"]))
        if s is None or s.n < cat.MIN_GROUP_N:
            continue
        filas.append(_fila(nivel, "alerta_grupo", f["alerta"], f["n"], f["pct"],
                           agrupacion=f["agrupacion"], grupo=str(f["grupo"]),
                           n_grupo=s.n, **comun))
    return filas
```

4. En `verificar`, dentro del bucle y justo antes de `        for campo in ("grupo", "clave"):`:

```python
        if (str(f.get("tipo", "")).startswith("alerta") and f.get("valor") is None
                and (f.get("detalle") or {}).get("estado", "sin_estado") != "sin_estado"):
            problemas.append(f"fila {i} ({f['tipo']}/{f['clave']}/{f['grupo']}): una alerta "
                             "sin porcentaje publicado no puede llevar estado")
```

   El campo `casos` ya lo rechaza `CAMPOS_CONTEO_PROHIBIDOS` para toda fila, también las de alerta.

5. Docstring de `verificar_restas`: reemplazar `suma o resta de proporciones publicadas deja un conjunto que no cumpla).` por `suma o resta de proporciones publicadas deja un conjunto que no cumpla; también las alertas de grupo, como una familia más).`

6. `main` y `mensajes_para_subir` **no cambian**: los mensajes por rol de las alertas se suben a `obs360.mensajes` cuando el equipo apruebe los textos (ver «Preguntas abiertas», 6).

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py tests/test_estudiantes_publicar.py tests/test_restas_publicadas.py tests/test_estudiantes_subgrupos.py tests/test_supresion_pipeline.py tests/test_alertas_regresion.py -q`
Expected: todo pasa. `test_estudiantes_subgrupos.py::test_las_filas_de_subgrupo_respetan_el_minimo` exige `n_grupo` en toda fila «…_grupo»: `alerta_grupo` lo lleva.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/publicar.py tests/test_alertas_publicar.py tests/test_estudiantes_publicar.py tests/test_restas_publicadas.py
git commit -m "feat(publicar): alertas por grupo sin casos y estado solo donde hay porcentaje" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Migración de Supabase (la escribe el plan, la corre el usuario)

La columna `tipo` no tiene `CHECK`, así que publicar funciona sin migración. Esto añade la última barrera en la base. Las corridas viejas (anteriores al PR #8) todavía guardan `casos` en las filas «corte»: por eso las restricciones van `NOT VALID` (no se revisan las filas existentes; sí toda fila nueva).

**Files:**
- Create: `supabase/migraciones/2026-10-07c-alertas-sin-casos.sql`
- Modify: `supabase/estudiantes_schema.sql`
- Modify: `tests/test_alertas_publicar.py`

- [ ] **Step 1: Prueba que falla**

Al final de `tests/test_alertas_publicar.py`:

```python
# ══ Supabase ════════════════════════════════════════════════════════════════
def test_la_migracion_de_alertas_y_el_esquema_dicen_lo_mismo():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "supabase", "migraciones",
                           "2026-10-07c-alertas-sin-casos.sql"), encoding="utf-8") as fh:
        migracion = fh.read()
    with open(os.path.join(raiz, "supabase", "estudiantes_schema.sql"), encoding="utf-8") as fh:
        esquema = fh.read()
    for texto in (migracion, esquema):
        assert "resultados_sin_conteos" in texto
        assert "detalle ?| ARRAY['casos', 'k_bajo', 'k_alto']" in texto
        assert "resultados_alerta_estado_con_cifra" in texto
        assert "NOT VALID" in texto
    # la misma lista de campos que rechaza `verificar`
    assert publicar.CAMPOS_CONTEO_PROHIBIDOS == ("casos", "k_bajo", "k_alto")
    assert ac.SIN_ESTADO == "sin_estado"          # el literal del CHECK y de verificar
```

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q -k migracion`
Expected: FAIL con `FileNotFoundError`.

- [ ] **Step 2: Crear la migración**

`supabase/migraciones/2026-10-07c-alertas-sin-casos.sql`:

```sql
-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · ningún conteo de casos y alertas con estado solo donde hay
-- cifra (fase 3, spec §5.4)
--
-- Ejecutar en Supabase → SQL Editor → Run, ANTES de publicar una corrida con
-- alertas. Aditiva e idempotente.
-- Publicar funciona sin ella: `publicar.verificar` ya rechaza en Python los
-- campos de conteo y el estado sin porcentaje. Esta es la última barrera: aunque
-- el código fallara, la base rechaza la fila.
--
-- NOT VALID: las corridas viejas (anteriores a la supresión de cifras pequeñas)
-- todavía guardan `casos` en las filas «corte». No se validan ni se tocan; la
-- restricción vale para toda fila nueva.
-- ════════════════════════════════════════════════════════════════════════════

-- Ninguna fila publica el número de casos (ni los de un contraste por tercil).
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_sin_conteos;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_sin_conteos CHECK (
    NOT (detalle ?| ARRAY['casos', 'k_bajo', 'k_alto'])) NOT VALID;

-- Una alerta sin porcentaje publicado no lleva estado («Prioridad» / «Para
-- tener presente»): el estado solo se muestra donde se muestra la cifra.
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_alerta_estado_con_cifra;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_alerta_estado_con_cifra CHECK (
    tipo NOT LIKE 'alerta%'
    OR valor IS NOT NULL
    OR coalesce(detalle->>'estado', 'sin_estado') = 'sin_estado') NOT VALID;

COMMENT ON COLUMN obs360.resultados.tipo IS
  'descriptivo | banda | corte | correlacion | grupo | modelo | tercil | percentil | '
  'item | icc | contraste | muestra | solapamiento | ingesta | *_grupo | '
  'alerta | alerta_grupo (alertas de grupo: n, % e IC donde se pueden mostrar y '
  'estado en detalle; nunca casos)';

-- Comprobación: dos filas
-- SELECT conname FROM pg_constraint
--  WHERE conname IN ('resultados_sin_conteos', 'resultados_alerta_estado_con_cifra');
```

- [ ] **Step 3: Copiar al esquema vigente**

En `supabase/estudiantes_schema.sql`:
- Justo después del `ALTER … ADD CONSTRAINT resultados_sin_id_estudiante CHECK (…);` de la sección 2, pegar:

```sql
-- Migración 2026-10-07c: ningún conteo de casos y alertas con estado solo donde
-- hay cifra. NOT VALID: no revisa las filas de corridas viejas, sí las nuevas.
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_sin_conteos;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_sin_conteos CHECK (
    NOT (detalle ?| ARRAY['casos', 'k_bajo', 'k_alto'])) NOT VALID;
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_alerta_estado_con_cifra;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_alerta_estado_con_cifra CHECK (
    tipo NOT LIKE 'alerta%'
    OR valor IS NOT NULL
    OR coalesce(detalle->>'estado', 'sin_estado') = 'sin_estado') NOT VALID;
```

- En la cabecera, sección «ESTADO ACTUAL Y MIGRACIONES», reemplazar

```text
-- identificador E/C/N; mensajes por módulo). Volver a ejecutarlo NO reabre las
-- corridas viejas.
```

por

```text
-- identificador E/C/N; mensajes por módulo) y la 2026-10-07c (ningún conteo de
-- casos; alertas con estado solo donde hay cifra). Volver a ejecutarlo NO reabre
-- las corridas viejas.
```

- [ ] **Step 4: Correr y commit**

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q`
Expected: todo pasa.

```bash
git add supabase/migraciones/2026-10-07c-alertas-sin-casos.sql supabase/estudiantes_schema.sql tests/test_alertas_publicar.py
git commit -m "feat(supabase): la base rechaza conteos de casos y estados sin porcentaje" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

No se aplica a Supabase desde aquí: la corre el usuario (Task 18, pasos del usuario).

---

### Task 8: Leer las alertas publicadas

**Files:**
- Modify: `src/estudiantes/lectura.py`
- Modify: `tests/test_alertas_publicar.py`

- [ ] **Step 1: Pruebas que fallan**

Al final de `tests/test_alertas_publicar.py`:

```python
# ══ Lectura ═════════════════════════════════════════════════════════════════
def test_las_alertas_se_leen_igual_que_se_publicaron(config):
    nivel, a = config
    filas = _filas(a, nivel)
    random.Random(5).shuffle(filas)                 # Supabase no garantiza orden
    leido = lectura._reconstruir(nivel, filas)
    pd.testing.assert_frame_equal(leido.alertas, a.alertas, check_dtype=False)
    assert leido.alertas_sensibilidad.empty and leido.alertas_items.empty


def test_el_estado_leido_se_reproduce_con_las_cifras_publicadas(config):
    nivel, a = config
    t = lectura._reconstruir(nivel, _filas(a, nivel)).alertas
    for f in t[t["agrupacion"] != al.TOTAL].to_dict("records"):
        ref = t[(t["alerta"] == f["alerta"]) & (t["agrupacion"] == al.TOTAL)].iloc[0]
        assert f["estado"] == al.estado(f["pct"], f["n"], ref["pct"], ref["n"])


def test_una_corrida_anterior_sin_alertas_se_sigue_leyendo(analisis):
    filas = [f for f in _filas(analisis) if not f["tipo"].startswith("alerta")]
    viejo = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert viejo.alertas.empty and list(viejo.alertas.columns) == al.COLUMNAS_TABLA
```

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q -k "leen or leido or anterior"`
Expected: FAIL (la tabla leída está vacía).

- [ ] **Step 2: Implementar**

En `src/estudiantes/lectura.py`:

1. Docstring, justo antes del párrafo «Esa limitación es el diseño…»:

```text
También rearma la tabla de alertas de grupo (`Analisis.alertas`, filas
`alerta` y `alerta_grupo`). Una corrida anterior a la fase 3 no las trae: la
tabla queda vacía y la vista vuelve a la tarjeta de siempre. La sensibilidad y
la distribución de ítems de las alertas no se publican: quedan vacías.

```

2. En `_reconstruir`, reemplazar

```python
    a.subgrupos = _subgrupos(nivel, filas)
    return a
```

por

```python
    a.subgrupos = _subgrupos(nivel, filas)
    a.alertas = _tabla_alertas(nivel, filas)
    return a
```

3. Justo antes de `TIPOS_SUBGRUPO = (`:

```python
def _tabla_alertas(nivel: str, filas: list[dict]) -> pd.DataFrame:
    """`Analisis.alertas` desde las filas «alerta» y «alerta_grupo» (sin casos)."""
    from src.estudiantes import alertas as al
    from src.estudiantes import alertas_catalogo as ac
    salida = []
    for f in filas:
        if f["tipo"] not in ("alerta", "alerta_grupo"):
            continue
        total = f["tipo"] == "alerta"
        salida.append(dict(alerta=f["clave"],
                           agrupacion=al.TOTAL if total else f["agrupacion"],
                           grupo=al.TODOS if total else str(f["grupo"]),
                           n=int(f["n"]), pct=f["valor"], ic_inf=f["ic_inf"],
                           ic_sup=f["ic_sup"],
                           estado=_det(f, "estado", ac.SIN_ESTADO) or ac.SIN_ESTADO))
    return al.ordenar(_df(salida, al.COLUMNAS_TABLA), nivel)
```

`TIPOS_SUBGRUPO` no cambia: `alerta_grupo` no crea objetos de subgrupo.

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py tests/test_estudiantes_lectura.py tests/test_estudiantes_subgrupos.py tests/test_supresion_vistas.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/lectura.py tests/test_alertas_publicar.py
git commit -m "feat(lectura): las alertas publicadas se leen; una corrida vieja sigue igual" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Panel de alertas (funciones puras y HTML)

**Files:**
- Create: `src/ui/views/estudiantes_alertas.py`
- Create: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

`tests/test_alertas_vista.py` (las secciones de la vista comunidad, los informes, el PDF y los investigadores se añaden en las Tasks 10 a 13):

```python
"""Panel «Señales para actuar a tiempo» en la vista, los informes y el PDF (spec §5.4, §6)."""
import colorsys
import dataclasses
import io
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.core.colegios import COLEGIOS
from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.ui.views import estudiantes_alertas as va

P, T, R, S = ac.PRIORIDAD, ac.PRESENTE, ac.REFERENCIA, ac.SIN_ESTADO


def _r(alerta, agrupacion, grupo, pct=None, estado=S, n=60):
    return dict(alerta=alerta, agrupacion=agrupacion, grupo=grupo, n=n, pct=pct,
                ic_inf=None if pct is None else pct - 5,
                ic_sup=None if pct is None else pct + 5, estado=estado)


TABLA = [
    _r("malestar", "total", "Todos", 16.7, R, n=900),
    _r("malestar", "Colegio", "LauV", 25.0, P, n=400),
    _r("malestar", "Colegio", "JJC"),
    _r("malestar", "Grado", "Octavo", 30.0, P, n=150),
    _r("malestar", "Grado", "Sexto", 12.0, T, n=150),
    _r("malestar", "Colegio×Grado", "LauV|Octavo", 35.0, P, n=90),
    _r("malestar", "Colegio×Grado", "LauV|Sexto", 33.0, P, n=95),
    _r("malestar", "Colegio×Grado", "LauV|Noveno"),
    _r("desesperanza", "total", "Todos", 17.0, R, n=900),
    _r("desesperanza", "Colegio", "LauV", 20.0, T, n=400),
]


def _ns(filas=TABLA, nivel=cat.NIVEL_SECUNDARIA):
    return SimpleNamespace(nivel=nivel, alertas=pd.DataFrame(filas, columns=al.COLUMNAS_TABLA))


def test_frase_de_la_cifra():
    assert va.frase("malestar", 16.7) == "1 de cada 6 estudiantes muestra señales de malestar."
    assert va.frase("malestar", 40) == "4 de cada 10 estudiantes muestran señales de malestar."


def test_familia_solo_ve_malestar_y_sin_listas():
    s = va.senales(_ns(), "familia", {})
    assert [x.alerta for x in s] == ["malestar"]
    assert s[0].listas == ()
    assert s[0].que_hacer == ac.ALERTAS["malestar"].que_hacer["familia"]


def test_colegio_ve_las_dos_y_los_grados_en_prioridad():
    s = {x.alerta: x for x in va.senales(_ns(), "colegio", {})}
    assert set(s) == {"malestar", "desesperanza"}
    m = s["malestar"]
    assert m.estado == R and m.etiqueta_estado == "Para tener presente" and m.visible
    assert m.frase == "1 de cada 6 estudiantes muestra señales de malestar."
    assert m.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)),)


def test_dentro_de_un_colegio_los_grados_van_en_orden_canonico():
    s = va.senales(_ns(), "colegio", {"colegio": "LauV"})[0]
    assert s.estado == P
    assert s.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Sexto", "Octavo")),)


def test_el_municipio_ve_colegios_y_grados_en_prioridad():
    s = va.senales(_ns(), "municipio", {})[0]
    assert s.listas == ((ac.TITULO_COLEGIOS_PRIORIDAD, ("Laura Vicuña",)),
                        (ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)))


def test_un_grado_con_cifra_lleva_porcentaje_y_estado():
    s = va.senales(_ns(), "familia", {"grado": "Octavo"})[0]
    assert s.estado == P and s.pct == 30.0
    c = va.senales(_ns(), "colegio", {"colegio": "LauV", "grado": "Octavo"})[0]
    assert c.estado == P and c.frase.startswith("4 de cada 10")


@pytest.mark.parametrize("filtros", [{"colegio": "JJC"}, {"colegio": "LauV", "grado": "Noveno"},
                                     {"grado": "Noveno"}])
def test_sin_cifra_el_estado_es_neutro_y_va_el_texto_fijo(filtros):
    s = va.senales(_ns(), "colegio", filtros)[0]
    assert s.estado == S and s.etiqueta_estado == "Sin estado: cifras pequeñas"
    assert s.frase == ac.CIFRAS_PEQUENAS and s.pct is None and s.n is None


def test_el_panel_solo_usa_cifras_de_la_tabla():
    """Cada cifra de una señal es la de su fila; nada se calcula ni se cuenta aparte."""
    for filtros in ({}, {"colegio": "LauV"}, {"grado": "Octavo"}, {"colegio": "JJC"},
                    {"colegio": "LauV", "grado": "Sexto"}):
        for s in va.senales(_ns(), "municipio", filtros):
            f = va.fila(_ns(), s.alerta, filtros)
            if s.visible:
                assert (s.pct, s.ic_inf, s.ic_sup, s.n, s.estado) == \
                    (f["pct"], f["ic_inf"], f["ic_sup"], f["n"], f["estado"])
            else:
                assert f is None or pd.isna(f["pct"])
    assert {x.name for x in dataclasses.fields(va.Senal)} == {
        "alerta", "nombre", "estado", "frase", "que_hacer", "pct", "ic_inf", "ic_sup", "n",
        "listas"}


def test_las_explicaciones_son_solo_de_los_estados_que_aparecen():
    lista = va.senales(_ns(), "colegio", {})            # dos «referencia»
    assert va.explicaciones(lista) == [ac.QUE_ES_REFERENCIA]
    assert ac.QUE_ES_PRESENTE in va.explicaciones(va.senales(_ns(), "colegio", {"grado": "Sexto"}))
    assert va.explicaciones(va.senales(_ns(), "colegio", {"colegio": "JJC"})) == \
        [ac.QUE_ES_SIN_ESTADO]


def test_primaria_no_trae_desesperanza():
    assert [x.alerta for x in va.senales(_ns(nivel=cat.NIVEL_PRIMARIA), "colegio", {})] \
        == ["malestar"]


def test_sin_tabla_no_hay_panel():
    assert va.senales(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA), "colegio", {}) == []
    assert va.panel_html(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA), "colegio", {}) == ""


def _seccion(html):
    return html.split('<section class="senales')[1].split("</section>")[0]


def test_el_panel_html_no_alarma_ni_cuenta_casos():
    html = va.panel_html(_ns(), "colegio", {"colegio": "LauV"})
    sec = _seccion(html)
    assert ac.TITULO_PANEL in sec and ac.NO_ES_DIAGNOSTICO in sec and ac.NOTA_AZAR in sec
    assert "Prioridad" in sec and "casos" not in sec.lower()
    assert "#C0392B" not in sec.upper()


def test_el_recuadro_compacto_recorta_las_listas():
    filas = [_r("malestar", "total", "Todos", 16.7, R, n=900)]
    filas += [_r("malestar", "Colegio", c, 30.0, P) for _, c, _ in COLEGIOS]
    html = va.panel_html(_ns(filas), "municipio", {}, compacto=True)
    assert f"y {len(COLEGIOS) - va.MAX_NOMBRES_PAGINA} más" in html


def test_tabla_de_la_secretaria():
    html = va.tabla_secretaria_html(_ns())
    assert "Laura Vicuña" in html and "José Joaquín Casas" in html
    assert ac.CIFRAS_PEQUENAS_CORTO in html and "Total del municipio" in html
    assert ac.ESTADOS[S] in html and "casos" not in html.lower()


def _hls(color):
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def test_el_color_maximo_es_naranja_nunca_rojo():
    tono, _, saturacion = _hls(va.COLOR_PRIORIDAD)
    assert 25 <= tono * 360 <= 45 and saturacion > 0.5
    assert _hls(va.COLOR_PRESENTE)[2] < 0.2 and _hls(va.COLOR_SIN_ESTADO)[2] < 0.2
    for css in (va.CSS_INFORME, va.CSS_PAGINA):
        assert "#C0392B" not in css.upper() and va.COLOR_PRIORIDAD in css
```

`test_el_panel_solo_usa_cifras_de_la_tabla` sustituye a la vieja búsqueda de conteos en el HTML: cada cifra de una señal es la de su fila publicada y `Senal` no tiene ningún campo de casos.

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py -q`
Expected: FAIL con `ImportError: cannot import name 'estudiantes_alertas'`.

- [ ] **Step 2: Implementar**

`src/ui/views/estudiantes_alertas.py`:

```python
"""
Panel «Señales para actuar a tiempo» — alertas de grupo de Estudiantes 360.

Funciones puras que leen `Analisis.alertas` (alertas.py) y los textos fijos de
`alertas_catalogo`; `render_panel` es lo único que dibuja con Streamlit. Lo
usan la vista comunidad, el informe del colegio, el de la Secretaría y el
resumen de una página: todos dicen lo mismo.

Reglas (spec §5.4 y §6):
  · Nunca un conteo de casos. Porcentaje, «1 de cada N», margen de error y
    estado solo si la tabla trae el porcentaje (la supresión ya decidió).
  · Sin porcentaje, estado neutro «Sin estado: cifras pequeñas», el texto fijo
    y la ruta. El panel nunca se oculta.
  · Naranja como máximo; nunca rojo.
  · Familia no ve desesperanza ni listas por colegio.
  · Es un módulo nuevo: se importa fresco aunque el despliegue conserve
    módulos viejos en memoria. Lee `Analisis.alertas` con getattr.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

import pandas as pd

from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import privacidad

TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE

# Gris sereno, gris claro (sin estado) y naranja. Nunca rojo (#C0392B es el de
# las bandas del SDQ).
COLOR_PRESENTE = "#5B6776"
FONDO_PRESENTE = "#F2F4F7"
COLOR_SIN_ESTADO = "#7A8594"
FONDO_SIN_ESTADO = "#FAFBFC"
COLOR_PRIORIDAD = "#B86E00"
FONDO_PRIORIDAD = "#FFF3E0"
MAX_NOMBRES_PAGINA = 6

# Clase CSS por estado: «referencia» se pinta como «presente».
CLASE = {ac.PRIORIDAD: "prioridad", ac.PRESENTE: "presente", ac.REFERENCIA: "presente",
         ac.SIN_ESTADO: "sin-estado"}


@dataclass(frozen=True)
class Senal:
    alerta: str
    nombre: str
    estado: str
    frase: str
    que_hacer: str
    pct: float | None = None
    ic_inf: float | None = None
    ic_sup: float | None = None
    n: int | None = None
    listas: tuple = ()

    @property
    def visible(self) -> bool:
        return self.pct is not None

    @property
    def etiqueta_estado(self) -> str:
        return ac.ESTADOS[self.estado]

    @property
    def clase(self) -> str:
        return CLASE[self.estado]


# ══ Datos ═══════════════════════════════════════════════════════════════════
def tabla(analisis) -> pd.DataFrame:
    t = getattr(analisis, "alertas", None)
    if isinstance(t, pd.DataFrame) and len(t) and set(al.COLUMNAS_TABLA) <= set(t.columns):
        return t
    return pd.DataFrame(columns=al.COLUMNAS_TABLA)


def hay_alerta(analisis, alerta: str) -> bool:
    t = tabla(analisis)
    return bool(len(t)) and bool((t["alerta"] == alerta).any())


def alertas_para_rol(analisis, rol: str) -> list[str]:
    nivel = getattr(analisis, "nivel", None)
    return [k for k, x in ac.ALERTAS.items()
            if rol in x.roles and nivel in x.niveles and hay_alerta(analisis, k)]


def clave_grupo(filtros: dict | None) -> tuple[str, str]:
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return CRUCE, privacidad.clave_celda(colegio, grado)
    if privacidad.activo(colegio):
        return "Colegio", str(colegio)
    if privacidad.activo(grado):
        return "Grado", str(grado)
    return al.TOTAL, TODOS


def fila(analisis, alerta: str, filtros: dict | None = None) -> dict | None:
    t = tabla(analisis)
    if not len(t):
        return None
    agrupacion, grupo = clave_grupo(filtros)
    sel = t[(t["alerta"] == alerta) & (t["agrupacion"] == agrupacion)
            & (t["grupo"].astype(str) == str(grupo))]
    return None if sel.empty else sel.iloc[0].to_dict()


def _con_cifra(f) -> bool:
    return bool(f) and f.get("pct") is not None and not pd.isna(f.get("pct"))


def frase(alerta: str, pct: float) -> str:
    from src.ui.views.estudiantes_comunidad import uno_de_cada
    fraccion = uno_de_cada(pct)
    verbo = "muestra" if fraccion.startswith("1 de cada") else "muestran"
    return ac.PLANTILLA_CIFRA.format(fraccion=fraccion, verbo=verbo,
                                     senal=ac.ALERTAS[alerta].senal)


def _ordenar_grados(grados, nivel) -> list[str]:
    orden = cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.ORDEN_GRADOS_PRI
    return sorted(grados, key=lambda g: (orden.index(g) if g in orden else 99, g))


def listas_prioridad(analisis, alerta: str, rol: str,
                     filtros: dict | None = None) -> list[tuple[str, list[str]]]:
    """(título, nombres) de los grupos en «Prioridad» que este rol puede ver."""
    if rol == "familia":
        return []
    t = tabla(analisis)
    if not len(t):
        return []
    t = t[(t["alerta"] == alerta) & (t["estado"] == ac.PRIORIDAD)]
    agrupacion, grupo = clave_grupo(filtros)
    nivel = getattr(analisis, "nivel", None)
    salida: list[tuple[str, list[str]]] = []
    if agrupacion == "Colegio":
        prefijo = grupo + privacidad.SEP
        grados = [privacidad.partir_celda(g)[1]
                  for g in t.loc[t["agrupacion"] == CRUCE, "grupo"].astype(str)
                  if g.startswith(prefijo)]
        salida.append((ac.TITULO_GRADOS_PRIORIDAD, _ordenar_grados(grados, nivel)))
    elif agrupacion == al.TOTAL:
        if rol == "municipio":
            from src.estudiantes.ingest import nombre_colegio
            colegios = sorted((nombre_colegio(g) for g in
                               t.loc[t["agrupacion"] == "Colegio", "grupo"].astype(str)),
                              key=str.lower)
            salida.append((ac.TITULO_COLEGIOS_PRIORIDAD, colegios))
        grados = list(t.loc[t["agrupacion"] == "Grado", "grupo"].astype(str))
        salida.append((ac.TITULO_GRADOS_PRIORIDAD, _ordenar_grados(grados, nivel)))
    return [(titulo, nombres) for titulo, nombres in salida if nombres]


def senales(analisis, rol: str, filtros: dict | None = None) -> list[Senal]:
    """Una señal por alerta que el rol puede ver, para el grupo elegido."""
    salida: list[Senal] = []
    for alerta in alertas_para_rol(analisis, rol):
        definicion = ac.ALERTAS[alerta]
        f = fila(analisis, alerta, filtros)
        listas = tuple((t, tuple(ns)) for t, ns in
                       listas_prioridad(analisis, alerta, rol, filtros))
        if not _con_cifra(f):
            salida.append(Senal(alerta=alerta, nombre=definicion.nombre,
                                estado=ac.SIN_ESTADO, frase=ac.CIFRAS_PEQUENAS,
                                que_hacer=definicion.que_hacer.get(rol, ""), listas=listas))
            continue
        salida.append(Senal(
            alerta=alerta, nombre=definicion.nombre, estado=str(f["estado"]),
            frase=frase(alerta, float(f["pct"])), que_hacer=definicion.que_hacer.get(rol, ""),
            pct=float(f["pct"]), ic_inf=float(f["ic_inf"]), ic_sup=float(f["ic_sup"]),
            n=int(f["n"]), listas=listas))
    return salida


def explicaciones(lista: list[Senal]) -> list[str]:
    """Qué quiere decir cada estado que aparece en `lista` (y nada más)."""
    textos = {ac.PRIORIDAD: ac.QUE_ES_PRIORIDAD, ac.PRESENTE: ac.QUE_ES_PRESENTE,
              ac.REFERENCIA: ac.QUE_ES_REFERENCIA, ac.SIN_ESTADO: ac.QUE_ES_SIN_ESTADO}
    vistos: list[str] = []
    for s in lista:
        if textos[s.estado] not in vistos:
            vistos.append(textos[s.estado])
    return vistos


# ══ HTML (informes y PDF) ═══════════════════════════════════════════════════
def _e(texto) -> str:
    return escape(str(texto), quote=True)


def _unir(nombres, tope: int | None = None) -> str:
    nombres = list(nombres)
    if tope and len(nombres) > tope:
        return ", ".join(nombres[:tope]) + f" y {len(nombres) - tope} más"
    return ", ".join(nombres)


def panel_html(analisis, rol: str, filtros: dict | None = None,
               compacto: bool = False) -> str:
    """Panel para el informe del colegio o, `compacto`, recuadro del PDF de una página."""
    lista = senales(analisis, rol, filtros)
    if not lista:
        return ""
    tope = MAX_NOMBRES_PAGINA if compacto else None
    bloques = []
    for s in lista:
        estado = f'<span class="estado">{_e(s.etiqueta_estado)}</span>'
        listas = "".join(f' <span class="lista">{_e(t)} {_e(_unir(ns, tope))}</span>'
                         for t, ns in s.listas)
        if compacto:
            bloques.append(f'<p class="senal senal-{s.clase}">{estado} <b>{_e(s.nombre)}.</b> '
                           f'{_e(s.frase)}{listas}</p>')
            continue
        margen = (f'<p class="margen">Margen de error {s.ic_inf:.0f}–{s.ic_sup:.0f} % · base '
                  f'de {s.n} estudiantes</p>' if s.visible else "")
        hacer = (f'<p class="accion"><b>Qué hacer.</b> {_e(s.que_hacer)}</p>'
                 if s.que_hacer else "")
        bloques.append(f'<div class="senal senal-{s.clase}"><p>{estado} <b>{_e(s.nombre)}</b></p>'
                       f'<p>{_e(s.frase)}</p>'
                       + (f"<p>{listas.strip()}</p>" if listas else "") + margen + hacer
                       + "</div>")
    notas = [ac.NO_ES_DIAGNOSTICO, ac.NOTA_AZAR]
    if not compacto and getattr(analisis, "nivel", None) == cat.NIVEL_PRIMARIA:
        notas.append(cat.AVISO_PRIMARIA)
    return (f'<section class="senales"><h2>{_e(ac.TITULO_PANEL)}</h2>' + "".join(bloques)
            + f'<p class="nota-senal">{_e(" ".join(notas))}</p></section>')


def _celda_html(f) -> str:
    if not _con_cifra(f):
        return (f'<td class="senal-sin-estado"><span class="estado">'
                f'{_e(ac.ESTADOS[ac.SIN_ESTADO])}</span>'
                f'<small>{_e(ac.CIFRAS_PEQUENAS_CORTO)}</small></td>')
    clase = CLASE[str(f["estado"])]
    return (f'<td class="senal-{clase}"><span class="estado">{_e(ac.ESTADOS[f["estado"]])}'
            f'</span> {float(f["pct"]):.0f} %<small>{float(f["ic_inf"]):.0f}–'
            f'{float(f["ic_sup"]):.0f}</small></td>')


def tabla_secretaria_html(analisis) -> str:
    """Tabla por colegio para el informe de la Secretaría: estado y %, sin conteos."""
    from src.estudiantes.ingest import nombre_colegio
    claves = alertas_para_rol(analisis, "municipio")
    if not claves:
        return ""
    t = tabla(analisis)
    colegios = sorted({str(g) for g in t.loc[(t["agrupacion"] == "Colegio")
                                             & t["alerta"].isin(claves), "grupo"]},
                      key=lambda c: nombre_colegio(c).lower())
    cabecera = "".join(f"<th>{_e(ac.ALERTAS[k].nombre_corto)}</th>" for k in claves)
    cuerpo = "".join(
        f'<tr><th scope="row">{_e(nombre_colegio(c))}</th>'
        + "".join(_celda_html(fila(analisis, k, {"colegio": c})) for k in claves) + "</tr>"
        for c in colegios)
    total = ('<tr><th scope="row">Total del municipio</th>'
             + "".join(_celda_html(fila(analisis, k, {})) for k in claves) + "</tr>")
    grados = []
    for k in claves:
        for titulo, nombres in listas_prioridad(analisis, k, "municipio", {}):
            if titulo == ac.TITULO_GRADOS_PRIORIDAD:
                grados.append(f'<p class="nota"><b>{_e(ac.ALERTAS[k].nombre_corto)}.</b> '
                              f"{_e(titulo)} {_e(_unir(nombres))}</p>")
    return (f'<section class="bloque senales"><h2>{_e(ac.TITULO_PANEL)} · por colegio</h2>'
            '<div class="desliza"><table class="senales-tabla"><thead><tr><th></th>'
            + cabecera + f"</tr></thead><tbody>{cuerpo}</tbody><tfoot>{total}</tfoot>"
            "</table></div>" + "".join(grados)
            + f'<p class="nota">{_e(ac.NOTA_TABLA)} {_e(ac.NOTA_AZAR)}</p></section>')


CSS_INFORME = (
    ".senales{border:1px solid #dde3ea;border-radius:6px;padding:12px 16px;margin:0 0 22px;"
    "break-inside:avoid}"
    ".senal{border-left:4px solid " + COLOR_PRESENTE + ";background:" + FONDO_PRESENTE + ";"
    "border-radius:4px;padding:8px 12px;margin:0 0 10px}"
    ".senal p{margin:3px 0;font-size:13.5px}"
    ".senal-prioridad{border-left-color:" + COLOR_PRIORIDAD + ";background:" + FONDO_PRIORIDAD + "}"
    ".senal-sin-estado{border-left-color:" + COLOR_SIN_ESTADO + ";background:"
    + FONDO_SIN_ESTADO + "}"
    ".senales .estado{display:inline-block;padding:1px 9px;border-radius:10px;font-size:12px;"
    "font-weight:700;background:#fff;color:" + COLOR_PRESENTE + ";margin-right:6px}"
    ".senal-prioridad .estado{color:" + COLOR_PRIORIDAD + "}"
    ".senal-sin-estado .estado{color:" + COLOR_SIN_ESTADO + ";font-weight:600}"
    ".senales .lista{color:#5b6776}"
    ".nota-senal{font-size:11.5px;color:#5b6776;margin:6px 0 0}"
    ".senales-tabla{width:100%;border-collapse:collapse;font-size:13px}"
    ".senales-tabla th,.senales-tabla td{border-bottom:1px solid #dde3ea;padding:6px 8px;"
    "text-align:center;vertical-align:top}"
    ".senales-tabla tbody th,.senales-tabla tfoot th{text-align:left}"
    ".senales-tabla small{display:block;font-size:10.5px;color:#5b6776}"
    ".senales-tabla td.senal-prioridad{background:" + FONDO_PRIORIDAD + "}"
    "@media print{.senales{padding:6px 12px;margin-bottom:12px}.senal{padding:5px 9px}"
    ".senal p{font-size:10.5px}.senales-tabla{font-size:10.5px}"
    ".senales-tabla th,.senales-tabla td{padding:3px 6px}}"
)

CSS_PAGINA = (
    ".senales{border:1px solid #dde3ea;border-radius:6px;padding:5px 9px 6px;margin-bottom:8px}"
    ".senales h2{margin-bottom:3px}"
    ".senal{margin:2px 0;font-size:8.3pt;line-height:1.3}"
    ".senal .estado{display:inline-block;padding:0 6px;border-radius:7px;font-size:7.4pt;"
    "font-weight:bold;margin-right:4px;background:" + FONDO_PRESENTE + ";color:"
    + COLOR_PRESENTE + "}"
    ".senal-prioridad .estado{background:" + FONDO_PRIORIDAD + ";color:" + COLOR_PRIORIDAD + "}"
    ".senal-sin-estado .estado{background:" + FONDO_SIN_ESTADO + ";color:"
    + COLOR_SIN_ESTADO + "}"
    ".senal .lista{color:#5b6776}"
    ".nota-senal{font-size:7pt;color:#5b6776;margin:2px 0 0}"
)


# ══ Streamlit ═══════════════════════════════════════════════════════════════
def _chip_html(s: Senal) -> str:
    color, fondo = {"prioridad": (COLOR_PRIORIDAD, FONDO_PRIORIDAD),
                    "presente": (COLOR_PRESENTE, FONDO_PRESENTE),
                    "sin-estado": (COLOR_SIN_ESTADO, FONDO_SIN_ESTADO)}[s.clase]
    return (f'<span style="background:{fondo};color:{color};border-radius:10px;'
            f'padding:1px 9px;font-size:0.85em;font-weight:600">{_e(s.etiqueta_estado)}</span>')


def render_panel(analisis, rol: str, filtros: dict | None = None) -> bool:
    """Dibuja el panel arriba de las tarjetas. False si la corrida no trae alertas."""
    import streamlit as st
    lista = senales(analisis, rol, filtros)
    if not lista:
        return False
    with st.container(border=True):
        st.markdown(f"#### {ac.TITULO_PANEL}")
        for s in lista:
            st.markdown(f"{_chip_html(s)} **{_e(s.nombre)}**", unsafe_allow_html=True)
            st.markdown(f"{s.frase} {ac.NO_ES_DIAGNOSTICO}")
            for titulo, nombres in s.listas:
                st.markdown(f"{titulo} {_unir(nombres)}")
            if s.que_hacer:
                st.markdown(f"**Qué hacer:** {s.que_hacer}")
        if getattr(analisis, "nivel", None) == cat.NIVEL_PRIMARIA:
            st.caption(cat.AVISO_PRIMARIA)
        with st.expander("Qué quiere decir cada estado"):
            for s in lista:
                st.markdown(f"**{s.nombre}.** {ac.ALERTAS[s.alerta].que_es}")
                if s.visible:
                    st.caption(f"{s.pct:.0f} % · margen de error {s.ic_inf:.0f}–"
                               f"{s.ic_sup:.0f} % · base de {s.n} estudiantes")
            for texto in explicaciones(lista):
                st.caption(texto)
            st.caption(ac.NOTA_AZAR)
    return True
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_alertas.py tests/test_alertas_vista.py
git commit -m "feat(alertas): panel «Señales para actuar a tiempo» (puro, HTML y Streamlit)" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Vista comunidad

**Files:**
- Modify: `src/ui/views/estudiantes_comunidad.py`
- Modify: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

Al final de `tests/test_alertas_vista.py`:

```python
# ══ Vista comunidad ═════════════════════════════════════════════════════════
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring  # noqa: E402
from src.ui.views import estudiantes_comunidad as vc  # noqa: E402
from tests.test_estudiantes_comunidad import _formulario  # noqa: E402


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)


def test_el_panel_reemplaza_la_tarjeta_de_muerte_para_colegio_y_municipio(analisis):
    for rol in ("colegio", "municipio"):
        assert vc.panel_reemplaza_muerte(analisis, rol)
        assert "ideacion" not in {t.clave for t in vc.tarjetas(analisis, rol)}
    assert not vc.panel_reemplaza_muerte(analisis, "familia")


def test_sin_alertas_la_tarjeta_de_muerte_vuelve(analisis):
    viejo = dataclasses.replace(analisis, alertas=pd.DataFrame())
    assert "ideacion" in {t.clave for t in vc.tarjetas(viejo, "colegio")}
    assert va.senales(viejo, "colegio", {}) == []


def test_una_corrida_publicada_sin_alertas_vuelve_a_la_tarjeta(analisis):
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
             if not f["tipo"].startswith("alerta")]
    viejo = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert va.senales(viejo, "colegio", {}) == []
    assert "ideacion" in {t.clave for t in vc.tarjetas(viejo, "colegio")}


def test_comparar_entre_grupos_sin_muerte_para_familia_ni_con_panel(analisis):
    assert "ideacion" not in vc.indicadores_comparables(analisis, "familia")
    assert "ideacion" not in vc.indicadores_comparables(analisis, "colegio")
    viejo = dataclasses.replace(analisis, alertas=pd.DataFrame())
    assert "ideacion" in vc.indicadores_comparables(viejo, "colegio")
    assert "ideacion" not in vc.indicadores_comparables(viejo, "familia")


def test_la_ruta_por_rol_es_la_vigente():
    for rol in cat.ROLES:
        assert vc.ruta_para_rol(rol) == list(cat.RUTA_ATENCION)


@pytest.mark.parametrize("modo,ve", [("completo", True), ("comunidad", False),
                                     ("investigador", False)])
def test_el_aviso_de_ruta_pendiente_solo_en_el_modo_completo(monkeypatch, modo, ve):
    monkeypatch.setenv("OBS360_MODO", modo)
    assert (vc.aviso_ruta_pendiente() == ac.RUTA_PENDIENTE) is ve


def test_si_el_panel_falla_la_pagina_sigue(monkeypatch, analisis):
    def falla(*a, **k):
        raise RuntimeError("módulo viejo")
    monkeypatch.setattr(va, "render_panel", falla)
    vc._panel_alertas(analisis, "colegio", {})          # no lanza
```

El orden del panel en la página (entre las bandas y las tarjetas) no se prueba leyendo el código fuente: lo comprueba Playwright en la Task 17.

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py -q -k "muerte or comparar or ruta or falla"`
Expected: FAIL con `AttributeError: module 'src.ui.views.estudiantes_comunidad' has no attribute 'panel_reemplaza_muerte'`.

- [ ] **Step 2: Implementar**

En `src/ui/views/estudiantes_comunidad.py`:

1. Docstring: reemplazar

```text
  · Todos los textos que lee el usuario vienen de `catalog` (MENSAJES, ROLES,
    RUTA_ATENCION, avisos). Esta vista elige y formatea; no redacta.
```

por

```text
  · Todos los textos que lee el usuario vienen de `catalog` (MENSAJES, ROLES,
    avisos) y de `alertas_catalogo` (alertas y la ruta por rol, `ruta`). Esta
    vista elige y formatea; no redacta.
  · El panel de alertas (estudiantes_alertas) va arriba de las tarjetas y, para
    colegio y municipio, reemplaza la tarjeta de muerte (spec §5.4).
```

2. Justo después de `def ve_colegios(…)` (antes de `def enunciado_pssm(`):

```python
def _alertas_vista():
    """Módulo del panel de alertas, o None.

    Si faltara o fallara al importarse (un despliegue a medias), la página sigue
    como antes de la fase 3.
    """
    try:
        from src.ui.views import estudiantes_alertas as va
        return va
    except Exception:                                      # noqa: BLE001
        return None


def panel_reemplaza_muerte(analisis, rol: str) -> bool:
    """¿El panel de alertas sustituye la tarjeta «Pensamientos sobre la muerte»?

    Solo para colegio y municipio, y solo si la corrida trae la alerta de
    desesperanza (spec §5.4, «Unificación»): si no, serían dos cifras sobre el
    mismo ítem. Con una corrida anterior a la fase 3 la tarjeta sigue igual.
    """
    if rol not in ("colegio", "municipio"):
        return False
    va = _alertas_vista()
    try:
        return bool(va and va.hay_alerta(analisis, "desesperanza"))
    except Exception:                                      # noqa: BLE001
        return False


def indicadores_comparables(analisis, rol: str) -> list[str]:
    """Indicadores del selector «Comparar entre grupos» para este rol.

    Familia nunca ve el de la muerte (spec §6). Colegio y municipio tampoco
    cuando el panel de alertas la reemplaza.
    """
    opciones = [k for k in INDICADORES if prevalencia(analisis, k, {})]
    if rol == "familia" or panel_reemplaza_muerte(analisis, rol):
        opciones = [k for k in opciones if k != "ideacion"]
    return opciones or ["sdq_alto"]


def ruta_para_rol(rol: str) -> list[tuple[str, str]]:
    """Ruta de atención para estudiantes del rol (alertas_catalogo.RUTAS)."""
    try:
        from src.estudiantes import alertas_catalogo as ac
        return ac.ruta(rol, "estudiante")
    except Exception:                                      # noqa: BLE001
        return list(cat.RUTA_ATENCION)


def aviso_ruta_pendiente() -> str:
    """Aviso interno «ruta pendiente de validación»: solo en el modo completo.

    Nunca sale en el despliegue público ni en los informes, que se comparten.
    """
    try:
        from src.core import modo as modo_app
        from src.estudiantes import alertas_catalogo as ac
    except Exception:                                      # noqa: BLE001
        return ""
    if ac.RUTAS_VALIDADAS:
        return ""
    return ac.RUTA_PENDIENTE if modo_app.modo() == modo_app.COMPLETO else ""


def _panel_alertas(a, rol: str, filtros: dict) -> None:
    """Dibuja el panel; si algo falla, la página sigue sin él."""
    va = _alertas_vista()
    if va is None:
        return
    try:
        va.render_panel(a, rol, filtros)
    except Exception:                                      # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("No se pudo dibujar el panel de alertas")
```

3. En `tarjetas`, reemplazar

```python
        accion = accion_para_rol(mensaje, rol)
        if not accion:
            continue
        cifra, detalle = "", ""
```

por

```python
        accion = accion_para_rol(mensaje, rol)
        if not accion:
            continue
        if clave == "ideacion" and panel_reemplaza_muerte(analisis, rol):
            continue
        cifra, detalle = "", ""
```

4. En `informe_markdown`, reemplazar `    for nombre, detalle in cat.RUTA_ATENCION:` por `    for nombre, detalle in ruta_para_rol(rol):`.

5. En `render_comunidad`:
   - Después del bloque «1. bandas» (tras el último `st.info("Este grupo no tiene suficientes respuestas para mostrar la " "distribución por niveles.", icon="ℹ️")`), insertar:

     ```python

         # ── 1b. señales para actuar a tiempo (alertas de grupo, spec §5.4)
         _panel_alertas(a, rol, filtros)
     ```

   - En «3. comparación», reemplazar

     ```python
             opciones = [k for k in INDICADORES if prevalencia(a, k, {})]
             if not opciones:
                 opciones = ["sdq_alto"]
     ```

     por `        opciones = indicadores_comparables(a, rol)`.

   - En «5. ruta de atención», reemplazar

     ```python
             for nombre, detalle in cat.RUTA_ATENCION:
                 st.markdown(f"- **{nombre}** — {detalle}")
     ```

     por

     ```python
             for nombre, detalle in ruta_para_rol(rol):
                 st.markdown(f"- **{nombre}** — {detalle}")
             aviso = aviso_ruta_pendiente()
             if aviso:
                 st.caption(f"⚠️ {aviso}")
     ```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_comunidad.py tests/test_estudiantes_subgrupos.py tests/test_supresion_vistas.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_comunidad.py tests/test_alertas_vista.py
git commit -m "feat(comunidad): panel de alertas arriba de las tarjetas y ruta por rol" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Informes del colegio y de la Secretaría

**Files:**
- Modify: `src/ui/views/estudiantes_informe.py`
- Modify: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

Al final de `tests/test_alertas_vista.py`:

```python
# ══ Informes ════════════════════════════════════════════════════════════════
from src.ui.views import estudiantes_informe as inf  # noqa: E402

COLEGIO = "LauV"


@pytest.fixture(scope="module", params=["archivos", "publicado"])
def fuente(request, analisis):
    if request.param == "archivos":
        return {cat.NIVEL_SECUNDARIA: analisis}
    filas = publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
    publicar.verificar(filas)
    return {cat.NIVEL_SECUNDARIA: lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)}


def test_el_informe_del_colegio_trae_el_panel(fuente):
    html = inf.informe_colegio_html(fuente, COLEGIO, fecha=date(2026, 10, 8))
    assert ac.TITULO_PANEL in html and ac.NO_ES_DIAGNOSTICO in html
    assert html.index(ac.TITULO_PANEL) < html.index("Resultados y qué hacer")
    assert "casos" not in _seccion(html).lower()
    assert "Piensa en la muerte con frecuencia" not in html     # el panel la reemplaza
    assert ac.RUTA_PENDIENTE not in html


def test_la_secretaria_trae_la_tabla_por_colegio(fuente):
    html = inf.informe_secretaria_html(fuente, fecha=date(2026, 10, 8))
    assert '<table class="senales-tabla">' in html and "Laura Vicuña" in html
    assert "Piensa en la muerte con frecuencia" not in html
    assert ac.RUTA_PENDIENTE not in html


def test_la_tabla_de_alertas_es_la_misma_desde_archivos_y_publicado(analisis):
    filas = publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
    pub = {cat.NIVEL_SECUNDARIA: lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)}

    def tabla(x):
        return inf.informe_secretaria_html(x, fecha=date(2026, 10, 8)).split(
            '<table class="senales-tabla">')[1].split("</table>")[0]
    assert tabla({cat.NIVEL_SECUNDARIA: analisis}) == tabla(pub)


def test_sin_alertas_los_informes_quedan_como_antes(analisis):
    viejo = {cat.NIVEL_SECUNDARIA: dataclasses.replace(analisis, alertas=pd.DataFrame())}
    html = inf.informe_secretaria_html(viejo, fecha=date(2026, 10, 8))
    assert ac.TITULO_PANEL not in html
    assert "Piensa en la muerte con frecuencia" in html


def test_con_modulos_viejos_los_informes_no_se_caen(monkeypatch, analisis):
    """Streamlit Cloud puede conservar un `estudiantes_comunidad` sin `ruta_para_rol`
    o un panel que falla: el informe sale igual, con la ruta vigente."""
    monkeypatch.delattr(vc, "ruta_para_rol")

    def falla(*a, **k):
        raise RuntimeError("módulo viejo")
    monkeypatch.setattr(va, "panel_html", falla)
    monkeypatch.setattr(va, "tabla_secretaria_html", falla)
    fuente = {cat.NIVEL_SECUNDARIA: analisis}
    for html in (inf.informe_colegio_html(fuente, COLEGIO, fecha=date(2026, 10, 8)),
                 inf.informe_secretaria_html(fuente, fecha=date(2026, 10, 8)),
                 inf.informe_una_pagina_html(analisis, "colegio", {})):
        assert ac.TITULO_PANEL not in html
        assert cat.RUTA_ATENCION[0][0] in html
```

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py -q -k "informe or secretaria or tabla_de_alertas or sin_alertas_los or viejos"`
Expected: FAIL (no hay panel en el HTML).

- [ ] **Step 2: Implementar**

En `src/ui/views/estudiantes_informe.py`:

1. Docstring: reemplazar

```text
  · Todos los textos sobre salud mental salen de `catalog` (MENSAJES,
    RUTA_ATENCION, avisos). Aquí solo se añaden títulos, etiquetas y la
    instrucción de impresión.
```

por

```text
  · Todos los textos sobre salud mental salen de `catalog` (MENSAJES, avisos)
    y de `alertas_catalogo` (alertas y la ruta por rol). Aquí solo se añaden
    títulos, etiquetas y la instrucción de impresión.
  · Panel de alertas (estudiantes_alertas): en el informe del colegio, tabla
    por colegio en el de la Secretaría y recuadro compacto en el resumen de una
    página. Con alertas, la columna de muerte sale de las tablas. Todo va en
    try/except: si el panel falla o el módulo de la vista es viejo, el informe
    sale como antes de la fase 3.
```

2. Justo antes de `def _e(texto) -> str:`:

```python
def _va():
    """Módulo del panel de alertas, o None (despliegue con módulos a medias)."""
    try:
        from src.ui.views import estudiantes_alertas as va
        return va
    except Exception:                                      # noqa: BLE001
        return None


def _seguro(funcion, *args, **kwargs) -> str:
    """HTML del panel de alertas, o «» si algo falla: el informe nunca se cae por él."""
    try:
        return funcion(*args, **kwargs)
    except Exception:                                      # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo armar el panel de alertas")
        return ""


def _sin_muerte(a, columnas) -> list[str]:
    """Sin la columna de muerte si el panel de alertas la reemplaza (spec §5.4)."""
    va = _va()
    try:
        reemplaza = va is not None and va.hay_alerta(a, "desesperanza")
    except Exception:                                      # noqa: BLE001
        reemplaza = False
    return [k for k in columnas if not (reemplaza and k == "ideacion")]


def _panel(a, rol: str, filtros: dict, compacto: bool = False) -> str:
    va = _va()
    return "" if va is None else _seguro(va.panel_html, a, rol, filtros, compacto=compacto)


def _senales_secretaria(a) -> str:
    va = _va()
    return "" if va is None else _seguro(va.tabla_secretaria_html, a)


def _css_senales(tipo: str) -> str:
    va = _va()
    if va is None:
        return ""
    return getattr(va, "CSS_PAGINA" if tipo == "pagina" else "CSS_INFORME", "")


def _ruta(rol: str) -> list[tuple[str, str]]:
    """La ruta por rol; si `estudiantes_comunidad` es un módulo viejo, la vigente."""
    funcion = getattr(vc, "ruta_para_rol", None)
    if funcion is None:
        return list(cat.RUTA_ATENCION)
    try:
        return funcion(rol)
    except Exception:                                      # noqa: BLE001
        return list(cat.RUTA_ATENCION)
```

3. `_bloque_ruta`: reemplazar

```python
def _bloque_ruta() -> str:
    filas = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in cat.RUTA_ATENCION)
```

por

```python
def _bloque_ruta(rol: str = "colegio") -> str:
    filas = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in _ruta(rol))
```

4. `_documento`: firma `def _documento(titulo: str, cuerpo: str, css_extra: str = "") -> str:` y `<style>{_CSS}{css_extra}</style>` en lugar de `<style>{_CSS}</style>`.

5. `informe_colegio_html`:
   - Reemplazar

     ```python
             grados = _tabla_comparativa(
                 a, "Grado", COLUMNAS_GRADO_COLEGIO, filtros, "Por grado en el colegio",
     ```

     por

     ```python
             grados = _tabla_comparativa(
                 a, "Grado", _sin_muerte(a, COLUMNAS_GRADO_COLEGIO), filtros,
                 "Por grado en el colegio",
     ```

   - Después de `+ _bloque_bandas([("Colegio", b), ("Municipio", vc.bandas_sdq_total(a, {}))])` y antes de `+ '<h2>Resultados y qué hacer</h2><div class="tarjetas">'`, insertar `            + _panel(a, "colegio", filtros)`.
   - `_bloque_ruta()` → `_bloque_ruta("colegio")`.
   - `return _documento(f"Informe Estudiantes 360 · {nombre}", cuerpo, _css_senales("informe"))`.

6. `informe_secretaria_html`:
   - Reemplazar

     ```python
                 + "".join(tarjetas_html) + "</div>"
                 + _tabla_comparativa(a, "Colegio", list(COLUMNAS_TABLA), {}, "Por colegio",
                                      nombre_colegio, nota=nota_peq)
                 + _tabla_comparativa(a, "Grado", list(COLUMNAS_TABLA), {}, "Por grado",
                                      lambda g: g)
     ```

     por

     ```python
                 + "".join(tarjetas_html) + "</div>"
                 + _senales_secretaria(a)
                 + _tabla_comparativa(a, "Colegio", _sin_muerte(a, list(COLUMNAS_TABLA)), {},
                                      "Por colegio", nombre_colegio, nota=nota_peq)
                 + _tabla_comparativa(a, "Grado", _sin_muerte(a, list(COLUMNAS_TABLA)), {},
                                      "Por grado", lambda g: g)
     ```

   - `_bloque_ruta()` → `_bloque_ruta("municipio")`.
   - `return _documento("Informe Estudiantes 360 · Secretaría", cuerpo, _css_senales("informe"))`.

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_informe.py tests/test_supresion_vistas.py -q`
Expected: todo pasa (las pruebas de PDF se saltan sin WeasyPrint).

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_informe.py tests/test_alertas_vista.py
git commit -m "feat(informes): panel de alertas para el colegio y tabla para la Secretaría" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Recuadro en el resumen de una página y el peor caso

La prueba existente (`tests/test_estudiantes_informe.py::test_el_resumen_cabe_en_una_pagina_de_pdf`) mide con `HTML(string=…).render()` y `len(doc.pages) == 1`. Aquí se hace lo mismo con el peor caso: rol municipio, todos los colegios y grados en «Prioridad», y los dos niveles.

**Files:**
- Modify: `src/ui/views/estudiantes_informe.py`
- Modify: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

Al final de `tests/test_alertas_vista.py`:

```python
# ══ Resumen de una página ═══════════════════════════════════════════════════
def _f(colegio="Todos", grado="Todos"):
    return {"nivel": cat.NIVEL_SECUNDARIA, "colegio": colegio, "grado": grado}


def test_el_recuadro_va_antes_de_las_tarjetas(analisis):
    html = inf.informe_una_pagina_html(analisis, "colegio", _f(colegio=COLEGIO))
    assert html.index(ac.TITULO_PANEL) < html.index("Lo más importante y qué hacer")
    assert ac.RUTA_PENDIENTE not in html


def test_el_resumen_de_familia_no_trae_desesperanza(analisis):
    html = inf.informe_una_pagina_html(analisis, "familia", _f())
    assert ac.ALERTAS["malestar"].nombre in html
    assert ac.ALERTAS["desesperanza"].nombre not in html


def test_un_grupo_pequeno_tambien_lleva_el_recuadro(analisis):
    html = inf.informe_una_pagina_html(analisis, "colegio", _f(grado="Noveno"))
    assert ac.CIFRAS_PEQUENAS in html and ac.ESTADOS[S] in html


def _peor_caso(a, nivel):
    grados = cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.ORDEN_GRADOS_PRI
    filas = []
    for k, x in ac.ALERTAS.items():
        if nivel not in x.niveles:
            continue
        filas.append(_r(k, "total", "Todos", 17.0, R, n=900))
        filas += [_r(k, "Colegio", c, 40.0, P) for _, c, _ in COLEGIOS]
        filas += [_r(k, "Grado", g, 40.0, P, n=150) for g in grados]
    return dataclasses.replace(a, nivel=nivel,
                               alertas=pd.DataFrame(filas, columns=al.COLUMNAS_TABLA))


@pytest.mark.parametrize("nivel", [cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA])
def test_el_peor_caso_cabe_en_una_pagina(analisis, nivel):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML
    html = inf.informe_una_pagina_html(_peor_caso(analisis, nivel), "municipio", _f())
    assert f"y {len(COLEGIOS) - va.MAX_NOMBRES_PAGINA} más" in html
    assert len(HTML(string=html).render().pages) == 1
```

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py -q -k "recuadro or resumen_de_familia or grupo_pequeno or peor"`
Expected: FAIL (no hay recuadro). La del peor caso se salta sin WeasyPrint.

- [ ] **Step 2: Implementar**

En `informe_una_pagina_html`:

1. Reemplazar

```python
    if b or fichas:
        filas_bandas = [("Este grupo" if con_municipio else "Municipio", b)]
```

por

```python
    caja = _panel(analisis, rol, filtros, compacto=True)
    if b or fichas:
        filas_bandas = [("Este grupo" if con_municipio else "Municipio", b)]
```

2. `contenido = (bandas + '<h2>Lo más importante y qué hacer</h2><div class="tiles">'` → `contenido = (bandas + caja + '<h2>Lo más importante y qué hacer</h2><div class="tiles">'`.
3. `contenido = f"<p>{_e(vc.SIN_SUBGRUPO_PUBLICADO)}</p>"` → `contenido = caja + f"<p>{_e(vc.SIN_SUBGRUPO_PUBLICADO)}</p>"`.
4. `contenido = (f"<p>Este grupo tiene menos de {cat.MIN_GROUP_N} estudiantes, así que "` → `contenido = caja + (f"<p>Este grupo tiene menos de {cat.MIN_GROUP_N} estudiantes, así que "` (el resto de la expresión no cambia).
5. `ruta = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in cat.RUTA_ATENCION)` → `… for n, d in _ruta(rol))`.
6. En el `return`, reemplazar `f"<style>{_CSS_PAGINA}</style></head><body>{cuerpo}</body></html>")` por:

```python
            f"<style>{_CSS_PAGINA}{_css_senales('pagina')}</style></head><body>{cuerpo}"
            "</body></html>")
```

- [ ] **Step 3: Correr, también con WeasyPrint**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_informe.py tests/test_supresion_vistas.py -q`
Expected: todo pasa.

El `.venv` local no trae WeasyPrint, así que el PDF se prueba con el entorno de producción.

Run: `"$VENV314/bin/python" -m pytest tests/test_alertas_vista.py tests/test_estudiantes_informe.py -q -rA -k "pagina or peor"`
Expected: `test_el_peor_caso_cabe_en_una_pagina[secundaria]` y `[primaria]` **PASSED**, no saltadas.

Si el peor caso da 2 páginas, compactar en este orden:
1. `CSS_PAGINA`: bajar `.senal` a `font-size:8pt` y `.senales` a `padding:4px 8px`.
2. `MAX_NOMBRES_PAGINA = 4` (la prueba lo lee de la constante).

Nunca se quitan la ruta, los avisos ni la nota «no es un diagnóstico».

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_informe.py tests/test_alertas_vista.py
git commit -m "feat(pdf): recuadro compacto de alertas antes de las tarjetas, cabe en una página" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

Si hubo que compactar, añadir también `src/ui/views/estudiantes_alertas.py` al `git add`.

---

### Task 13: Vista de investigadores

**Files:**
- Modify: `src/ui/views/estudiantes_investigador.py`
- Modify: `tests/test_estudiantes_investigador.py:97-106`
- Modify: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

En `tests/test_estudiantes_investigador.py`:
- Renombrar `test_paquete_zip_devuelve_bytes_con_los_ocho_archivos` → `test_paquete_zip_devuelve_bytes_con_los_nueve_archivos`.
- `assert len(vista.ARCHIVOS_PAQUETE) == 8` → `== 9`. Es un cambio explícito: la spec pide `alertas.csv` en el ZIP.

Al final de `tests/test_alertas_vista.py`:

```python
# ══ Investigadores ══════════════════════════════════════════════════════════
from src.ui.views import estudiantes_investigador as vi  # noqa: E402


def test_alertas_csv_en_el_zip_y_sin_casos(analisis):
    assert "alertas.csv" in vi.ARCHIVOS_PAQUETE
    t = pd.read_csv(io.StringIO(vi.archivos_paquete({cat.NIVEL_SECUNDARIA: analisis})
                                ["alertas.csv"]))
    assert list(t.columns) == vi.COLUMNAS_ALERTAS_CSV
    assert "casos" not in t.columns and "nombre" not in t.columns
    assert (t["n"] >= cat.MIN_GROUP_N).all()
    assert (t.loc[t["pct"].isna(), "estado"] == ac.ESTADOS[S]).all()


def test_sensibilidad_e_items_no_van_al_zip(analisis):
    assert not [n for n in vi.ARCHIVOS_PAQUETE if "sensibilidad" in n or "items" in n]


def test_las_tablas_de_alertas_son_convertibles_a_arrow(analisis):
    import pyarrow as pa
    for t in (vi.alertas_tabla(analisis), vi.sensibilidad_tabla(analisis),
              vi.items_alertas_tabla(analisis)):
        assert len(t)
        pa.Table.from_pandas(t)


def test_la_metodologia_define_las_alertas(analisis):
    md = vi.metodologia_md({cat.NIVEL_SECUNDARIA: analisis})
    assert "Alertas de grupo" in md
    assert ac.ALERTAS["malestar"].regla in md and ac.REGLA_CIFRAS in md


def test_la_pestana_de_alertas_existe():
    assert vi.PESTANAS.index("Alertas") == 5 and len(vi.PESTANAS) == 9
```

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_investigador.py -q`
Expected: FAIL.

- [ ] **Step 2: Implementar**

En `src/ui/views/estudiantes_investigador.py`:

1. Reemplazar `ARCHIVOS_PAQUETE = [ … ]` por:

```python
ARCHIVOS_PAQUETE = ["tabla1_descriptivos.csv", "bandas_y_cortes.csv", "correlaciones_bh.csv",
                    "comparaciones_grupo.csv", "modelos.csv", "alertas.csv",
                    "flujo_exclusiones.md", "metodologia.md", "version_analisis.txt"]

PESTANAS = ["Muestra y exclusiones", "Tabla 1 · descriptivos", "Cortes y bandas",
            "Correlaciones", "Por grupo", "Alertas", "Modelos", "Calidad de datos", "Exportar"]
```

2. Justo antes de `def flujo_exclusiones_md(`:

```python
def _tabla_de(analisis, campo: str, columnas: list[str]) -> pd.DataFrame:
    partes = []
    niveles = _como_dict(analisis)
    for nivel in _niveles(niveles):
        t = getattr(niveles[nivel], campo, None)
        if isinstance(t, pd.DataFrame) and len(t):
            partes.append(_con_nivel(t, nivel))
    return (pd.concat(partes, ignore_index=True)[["nivel"] + columnas] if partes
            else pd.DataFrame(columns=["nivel"] + columnas))


COLUMNAS_ALERTAS_CSV = ["nivel", "alerta", "alerta_nombre", "agrupacion", "grupo", "n", "pct",
                        "ic_inf", "ic_sup", "estado"]


def alertas_tabla(analisis) -> pd.DataFrame:
    """Alertas por grupo para `alertas.csv`: % con IC y estado, nunca casos (spec §5.4).

    La columna se llama `alerta_nombre` y no `nombre`: ningún exportable lleva
    una columna «nombre» (tests/test_estudiantes_investigador.py).
    """
    from src.estudiantes import alertas as al
    from src.estudiantes import alertas_catalogo as ac
    t = _tabla_de(analisis, "alertas", al.COLUMNAS_TABLA)
    if t.empty:
        return pd.DataFrame(columns=COLUMNAS_ALERTAS_CSV)
    t["alerta_nombre"] = [ac.ALERTAS[k].nombre if k in ac.ALERTAS else k for k in t["alerta"]]
    t["estado"] = [ac.ESTADOS.get(e, e) for e in t["estado"]]
    return t[COLUMNAS_ALERTAS_CSV]


def sensibilidad_tabla(analisis) -> pd.DataFrame:
    """Solo local: no se publica ni va al ZIP."""
    from src.estudiantes import alertas as al
    return _tabla_de(analisis, "alertas_sensibilidad", al.COLUMNAS_SENSIBILIDAD)


def items_alertas_tabla(analisis) -> pd.DataFrame:
    """Solo local: no se publica ni va al ZIP."""
    from src.estudiantes import alertas as al
    return _tabla_de(analisis, "alertas_items", al.COLUMNAS_ITEMS)


def _metodologia_alertas() -> list[str]:
    from src.estudiantes import alertas_catalogo as ac
    lineas = ["## Alertas de grupo («Señales para actuar a tiempo»)", ""]
    for alerta in ac.ALERTAS.values():
        lineas.append(f"- **{alerta.nombre}** ({' y '.join(alerta.niveles)}): {alerta.regla}"
                      + (f" Límite: {alerta.limite}" if alerta.limite else ""))
    lineas += ["", f"- {ac.REGLA_CIFRAS}",
               "- La desesperanza implica RCADS 18 ≥ «Con frecuencia» (la tarjeta de muerte): "
               "se suprime como un corte anidado en ese ítem y nunca se publica donde ese "
               "corte está suprimido.",
               "- «Prioridad»: el límite inferior del IC de Wilson del grupo queda por encima "
               "del límite superior del resto del nivel (el nivel sin el grupo), calculado solo "
               "con el % y el n publicados del grupo y del nivel. " + ac.NOTA_AZAR,
               "- Nunca se publica ni se exporta el número de casos de una alerta.",
               "- Sensibilidad (2, 3 y 4 ítems para el malestar; regla estricta frente a amplia "
               "para la desesperanza) y distribución de los ítems: solo en la vista local de "
               "investigadores, del nivel, y enteras o nada. No van a Supabase ni al ZIP.",
               "- Textos y umbrales provisionales hasta la aprobación del equipo.", ""]
    return lineas
```

3. En `metodologia_md`, justo antes de `    lineas += ["## 6. Análisis estadístico", "",`: `    lineas += _metodologia_alertas()`.

4. En `archivos_paquete`, después de `"modelos.csv": _csv(modelos_tabla(analisis)),`: `        "alertas.csv": _csv(alertas_tabla(analisis)),`. Docstring de `paquete_zip`: «ocho» → «nueve».

5. En `_tab_exportar`, en `descripciones`, después de la de `modelos.csv`: `        "alertas.csv": "Alertas por grupo: % con IC y estado donde se pueden mostrar; sin casos.",`.

6. Pestaña nueva, justo antes de `def _tab_modelos(`:

```python
def _tab_alertas(a) -> None:
    from src.estudiantes import alertas_catalogo as ac
    st.subheader("Señales para actuar a tiempo · definiciones")
    for alerta in ac.ALERTAS.values():
        if getattr(a, "nivel", None) not in alerta.niveles:
            continue
        st.markdown(f"**{alerta.nombre}.** {alerta.regla}")
        if alerta.limite:
            st.caption(alerta.limite)
    st.caption(ac.REGLA_CIFRAS)
    if not ac.TEXTOS_APROBADOS:
        st.warning("Textos y umbrales provisionales, pendientes de aprobación del equipo "
                   "(spec §8).")
    st.divider()
    st.subheader("Prevalencia por grupo")
    t = alertas_tabla(a)
    if t.empty:
        st.info("Esta corrida no trae alertas (es anterior a la fase 3).")
    else:
        st.dataframe(t.drop(columns=["nivel", "alerta"]), hide_index=True, width="stretch")
        st.caption("Sin número de casos, nunca. " + ac.NOTA_AZAR)
    st.divider()
    st.subheader("Distribución de cada ítem · nivel (solo local)")
    it = items_alertas_tabla(a)
    if it.empty:
        st.info("Solo con los datos locales: la corrida publicada no la trae.")
    else:
        st.dataframe(it.drop(columns=["nivel"]), hide_index=True, width="stretch")
        st.caption("Un ítem sin cifras tiene alguna respuesta con menos de 3 estudiantes o con "
                   "todos menos 2.")
    st.divider()
    st.subheader("Sensibilidad · umbrales y reglas (solo local)")
    s = sensibilidad_tabla(a)
    if s.empty:
        st.info("Solo con los datos locales: la corrida publicada no la trae.")
    else:
        st.dataframe(s.drop(columns=["nivel"]), hide_index=True, width="stretch")
        st.caption("Mismas filas para todas las variantes. Como están anidadas, se muestran "
                   "todas o ninguna.")
```

7. En `render_investigador`, reemplazar la lista literal de `st.tabs([...])` por `tabs = st.tabs(PESTANAS)` y reindexar: `tabs[5]` → `_tab_alertas(a)`, `tabs[6]` → `_tab_modelos(a)`, `tabs[7]` → `_tab_calidad(a, informe)`, `tabs[8]` → `_tab_exportar(analisis, informes)`. La prevalencia del ítem 18 sigue en «Cortes y bandas», sin cambios.

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_investigador.py tests/test_estudiantes_lectura.py -q`
Expected: todo pasa. `test_ningun_exportable_trae_columnas_de_identificacion` también pasa con `alertas.csv`: la columna se llama `alerta_nombre`, no `nombre`.

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_investigador.py tests/test_estudiantes_investigador.py tests/test_alertas_vista.py
git commit -m "feat(investigador): pestaña de alertas y alertas.csv en el ZIP" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Datos reales (se omite si faltan los archivos)

**Files:**
- Create: `tests/test_alertas_reales.py`

- [ ] **Step 1: Escribir las pruebas**

```python
"""
Alertas con los datos reales (spec §5.4 y §7). Se omiten si faltan los archivos.

Las calibraciones son las de la spec, con los formularios vigentes el 6-oct-2026
(secundaria del 18-sep; primaria xlsx hasta el 6-oct). Cuando llegue la
exportación nueva de secundaria (spec §9) cambian: se actualizan con la cifra
nueva; nunca se ensancha la tolerancia. Ninguna prueba imprime casos: solo
porcentajes de todo el nivel.
"""
import pandas as pd
import pytest

from src.core.rutas import carpeta_datos
from src.core.texto import norm_txt
from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, publicar, scoring, supresion


@pytest.fixture(scope="module")
def rutas():
    r = pipeline.localizar_formularios(carpeta_datos("estudiantes"))
    if len(r) < 2:
        pytest.skip("faltan los formularios")
    return r


@pytest.fixture(scope="module")
def puntuado(rutas):
    bruto, _ = ingest.cargar_varios(rutas)
    return scoring.puntuar(bruto)


@pytest.fixture(scope="module")
def analisis(rutas):
    a, _ = pipeline.cargar_y_analizar(rutas, n_boot=20)
    return a


def _pct(serie) -> float:
    return round(100 * float(serie.dropna().mean()), 1)


@pytest.mark.parametrize("nivel,umbral,esperado", [
    (cat.NIVEL_SECUNDARIA, 3, 8.8), (cat.NIVEL_PRIMARIA, 3, 15.1),
    (cat.NIVEL_SECUNDARIA, 2, 22.0), (cat.NIVEL_PRIMARIA, 2, 32.4)])
def test_calibracion_del_malestar(puntuado, nivel, umbral, esperado):
    d = puntuado[puntuado["nivel"] == nivel]
    assert _pct(al.senal_malestar(d, umbral)) == pytest.approx(esperado, abs=0.6)


def test_calibracion_de_la_desesperanza(puntuado):
    d = puntuado[puntuado["nivel"] == cat.NIVEL_SECUNDARIA]
    assert _pct(al.senal_desesperanza(d)) == pytest.approx(17.0, abs=0.6)
    por_grado = [_pct(al.senal_desesperanza(g)) for grado, g in d.groupby("Grado")
                 if grado in cat.ORDEN_GRADOS_SEC]
    assert min(por_grado) == pytest.approx(10.8, abs=0.6)
    assert max(por_grado) == pytest.approx(21.5, abs=0.6)


def test_la_cifra_de_la_tarjeta_de_muerte_no_cambia(puntuado):
    d = puntuado[puntuado["nivel"] == cat.NIVEL_SECUNDARIA]
    item = d[f"RCADS{cat.RCADS_ITEM_MUERTE}"]
    assert _pct((item >= 2).astype(float).where(item.notna())) == pytest.approx(24.9, abs=0.2)


def _encabezados(ruta) -> list:
    lector = pd.read_excel if str(ruta).lower().endswith((".xlsx", ".xls")) else pd.read_csv
    return list(lector(ruta, nrows=0).columns)     # solo encabezados, ninguna respuesta


def test_los_items_con_asterisco_coinciden_con_el_catalogo(rutas):
    for ruta in rutas:
        cols = _encabezados(ruta)
        nivel = (cat.NIVEL_SECUNDARIA if any(norm_txt(c).startswith("rcads") for c in cols)
                 else cat.NIVEL_PRIMARIA)
        assert al.items_marcados_por_escala(cols) == ac.items_marcados_esperados(nivel), nivel


def test_la_auditoria_cubre_las_alertas_reales(analisis):
    assert publicar.verificar_restas(analisis) == []
    for nivel, a in analisis.items():
        assert not [p for p in supresion.auditar(a) if p.startswith("alerta")], nivel


def test_el_total_de_cada_nivel_muestra_su_cifra(analisis):
    """Si falla para la desesperanza, sus bases no coinciden con las del ítem 18 en
    algún grupo (falla cerrado): informar al usuario, no relajar la regla."""
    for nivel, a in analisis.items():
        total = a.alertas[a.alertas["agrupacion"] == al.TOTAL]
        assert set(total["alerta"]) == set(al.claves_del_nivel(a.datos, nivel)), nivel
        assert total["pct"].notna().all(), nivel


def test_ninguna_fila_de_alerta_publicada_trae_casos(analisis):
    filas = publicar.aplanar(analisis)
    publicar.verificar(filas)
    assert not [f for f in filas if f["tipo"].startswith("alerta")
                and set(f["detalle"]) & set(publicar.CAMPOS_CONTEO_PROHIBIDOS)]
```

- [ ] **Step 2: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_reales.py -q`
Expected:
- Con los archivos: todo pasa.
- Sin ellos: todo se salta.

Si falla una calibración: **no** se ensancha la tolerancia. Se revisa la definición contra la spec, la regla de faltantes y que la columna sea la del texto crudo, y se informa al usuario con el porcentaje obtenido (de todo el nivel; nunca casos).

Si falla la prueba del asterisco, se informa qué ítems trae marcados cada formulario. Decide el equipo (spec §8.3).

- [ ] **Step 3: Diagnóstico para el equipo (sin casos)**

```bash
.venv/bin/python - <<'EOF'
from src.estudiantes import pipeline
analisis, _ = pipeline.cargar_y_analizar(n_boot=20)
for nivel, a in analisis.items():
    for alerta, g in a.alertas.groupby("alerta"):
        for agrupacion, h in g.groupby("agrupacion"):
            print(nivel, alerta, agrupacion,
                  f"grupos con porcentaje: {int(h['pct'].notna().sum())} de {len(h)}",
                  f"· en Prioridad: {int((h['estado'] == 'prioridad').sum())}")
EOF
```

Guardar la salida para el PR. Son conteos de **grupos**, no de estudiantes.

- [ ] **Step 4: Ensayo real y comparación del lote antes y después**

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_despues.json"
echo "código de salida: $?"
```
Expected: `código de salida: 0`. Si sale 2, la auditoría encontró algo: listar los mensajes (nombran grupo e indicador, nunca cifras) y parar.

```bash
.venv/bin/python - <<'EOF'
import json, os, sys
sys.path.insert(0, ".")
from tests.test_alertas_regresion import normalizar
t = os.environ["TMPDIR"]
antes = json.load(open(f"{t}/obs360_lote_antes.json", encoding="utf-8"))["filas"]
despues = json.load(open(f"{t}/obs360_lote_despues.json", encoding="utf-8"))["filas"]
a, d = (json.dumps(normalizar(x), sort_keys=True, ensure_ascii=False) for x in (antes, despues))
print("idéntico" if a == d else "DIFERENTE")
print("filas de alerta nuevas:", sum(f["tipo"].startswith("alerta") for f in despues))
EOF
```

Expected: «idéntico». Si dice DIFERENTE, listar qué filas cambian (tipo, clave y grupo; nunca casos) y presentarlas al usuario para aprobación explícita (spec §7) antes de seguir.

- [ ] **Step 5: Commit**

```bash
git add tests/test_alertas_reales.py
git commit -m "test(alertas): calibración, asteriscos y auditoría con los datos reales" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: Documentación

**Files:**
- Modify: `docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md` (sección nueva al final)
- Modify: `supabase/README.md` (lista de migraciones)
- Modify: `DESPLIEGUE.md` (pasos antes de publicar alertas)

- [ ] **Step 1: Editar**

**`INSTRUMENTO_ESTUDIANTES.md`**: sección «Alertas de grupo («Señales para actuar a tiempo»)» con:
- las dos reglas (copiadas de `alertas_catalogo.ALERTAS[*].regla`) y la regla de faltantes;
- que son proporciones como cualquier corte y pasan por la misma supresión (3 ≤ casos ≤ n − 3, complementaria y auditoría de restas), con porcentaje también por grado y por celda cuando la supresión lo permite;
- que la desesperanza está anidada en el corte del ítem 18 y por qué;
- el estado: «Prioridad» contra el resto del nivel, solo donde hay porcentaje y solo con cifras publicadas; «Sin estado» donde no;
- sensibilidad y distribución de ítems: solo en la vista local de investigadores;
- textos provisionales.

**`supabase/README.md`**: añadir `2026-10-07c-alertas-sin-casos.sql`: qué hace (ningún conteo de casos en ninguna fila nueva; estado de alerta solo con porcentaje; `NOT VALID` porque las corridas viejas guardan `casos`), y que es opcional para publicar pero recomendada.

**`DESPLIEGUE.md`**, sección «Publicar alertas»:
1. El equipo aprueba textos, umbrales y rutas: `alertas_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS`.
2. Correr la migración `2026-10-07c` (SQL Editor → Run).
3. `python -m src.estudiantes.publicar --ensayo` y revisar (tiene que salir con código 0).
4. Publicar con `--publicar-ya`.
5. «Reboot app».
6. Los mensajes por rol de las alertas se suben a `obs360.mensajes` en un paso aparte, cuando el equipo apruebe los textos.

Mientras no se publique una corrida nueva, el despliegue sigue con la tarjeta de muerte y sin panel.

- [ ] **Step 2: Commit**

```bash
git add docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md supabase/README.md DESPLIEGUE.md
git commit -m "docs(alertas): definiciones, migración y pasos para publicarlas" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 16: Probar con las versiones de producción

**Files:** ninguno, salvo que aparezcan fallos.

- [ ] **Step 1: Entorno con Python 3.14 y WeasyPrint**

Si `$VENV314` ya existe (lo normal), solo actualizarlo:

```bash
[ -x "$VENV314/bin/python" ] || /opt/homebrew/bin/python3.14 -m venv "$VENV314"
"$VENV314/bin/pip" install -q -r requirements.txt pytest pyarrow
"$VENV314/bin/python" -c "import streamlit, weasyprint, sys; print(sys.version, streamlit.__version__, weasyprint.__version__)"
```

Si WeasyPrint no encuentra pango: `brew install pango`.

- [ ] **Step 2: Correr la suite**

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: lo mismo que en 3.13 más las pruebas de PDF, que pasan en lugar de saltarse (entre ellas `test_el_peor_caso_cabe_en_una_pagina` y `test_lo_que_ya_se_publicaba_no_cambia`).

- Si hay un error real: corregirlo con prueba y commit propio.
- Si es del entorno: anotarlo en el PR.

- [ ] **Step 3: Commit (solo si hubo correcciones)**

---

### Task 17: Verificación con Playwright (local)

**Files:** ninguno.

- [ ] **Step 1: Levantar los modos**

```bash
OBS360_MODO=completo     .venv/bin/streamlit run main.py --server.port 8601 --server.headless true &
OBS360_MODO=investigador .venv/bin/streamlit run main.py --server.port 8602 --server.headless true &
OBS360_MODO=comunidad OBS360_FUENTE=supabase .venv/bin/streamlit run main.py --server.port 8603 --server.headless true &
```

- [ ] **Step 2: Comprobar con Playwright MCP**

| Modo | Comprobación |
|---|---|
| completo (8601), Estudiantes, rol colegio | Panel «Señales para actuar a tiempo» entre las bandas y las tarjetas, con las dos alertas, «No es un diagnóstico» y «Qué hacer». Sin tarjeta «Pensamientos sobre la muerte». Ninguna cifra roja en el panel |
| completo, colegio LauV | Estado y lista «Grados en «Prioridad»» en orden canónico, si los hay. Al desplegar «Qué quiere decir cada estado» aparecen el margen de error, la base y solo las explicaciones de los estados que se ven; nunca un conteo de casos |
| completo, colegio + grado con cifra | Porcentaje, «1 de cada N» y estado del grado |
| completo, grupo con cifra suprimida o sin fila | Chip «Sin estado: cifras pequeñas», «En este grupo las cifras son muy pequeñas…» y la ruta |
| completo, rol municipio | Listas de colegios y grados en «Prioridad»; sin tarjeta de muerte; el selector «Comparar» no ofrece «piensa en la muerte» |
| completo, rol familia | Solo «Señales de malestar»; nada de muerte ni desesperanza ni listas de colegios; «piensa en la muerte» no está en «Comparar» |
| completo | Bajo la ruta, el aviso interno «ruta pendiente de validación» |
| completo, primaria | Solo malestar y el aviso de validez de edad |
| completo, PDF | Descargar el resumen de una página (colegio y municipio): una sola página, con el recuadro antes de las tarjetas. El informe del colegio y el de la Secretaría muestran el panel o la tabla, sin casos |
| investigador (8602) | Pestaña «Alertas» con definiciones, prevalencias por grupo, ítems y sensibilidad (estas dos, con los datos locales). El ZIP trae `alertas.csv` y no trae sensibilidad ni ítems |
| comunidad (8603, corrida publicada sin alertas) | Sin panel; la tarjeta de muerte sigue como antes; sin errores; sin aviso interno de ruta |
| comunidad | A 390 px de ancho, el panel sin desborde horizontal |
| todos | Sin excepciones en pantalla |

- [ ] **Step 3: Apagar los servidores y borrar `.playwright-mcp/` si se creó**

---

### Task 18: PR (sin fusionar)

- [ ] **Step 1:** `git push -u origin feature/fase3-alertas`

- [ ] **Step 2:** `gh pr create --base main`. Si el PR #8 (`fix/cortes-casos-pequenos`) aún no está fusionado en `main`, el PR se abre como borrador (`--draft`) y el cuerpo lo dice: su diff incluye los commits del #8 hasta que se fusione. El cuerpo lleva:

  1. **Resumen.**
     - Qué ve cada rol.
     - Las alertas son proporciones como cualquier corte: misma supresión, misma auditoría; porcentaje también por grado y por celda cuando se puede.
     - La desesperanza va anidada en el corte del ítem 18.
     - El estado, solo donde hay porcentaje y solo con cifras publicadas.
  2. **Pruebas.**
     - Totales antes (529 passed, 2 skipped en 3.13) y después, en 3.13 y 3.14.
     - PDF en 3.14 (peor caso en una página).
     - Diagnóstico de grupos con porcentaje y en «Prioridad» (Task 14, Step 3).
     - Ensayo real con código 0 y comparación del lote real: «idéntico».
  3. **Pasos del usuario, en orden.**
     - Aprobación de textos, umbrales y rutas por el equipo.
     - Migración `2026-10-07c` en el SQL Editor.
     - Ensayo.
     - `--publicar-ya`.
     - **«Reboot app» después de fusionar.**
     - Mensajes por rol a `obs360.mensajes`, tras la aprobación.
  4. **Preguntas abiertas** (lista de abajo).
  5. Cerrar con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 3:** No fusionar. Lo decide el usuario.

---

## Preguntas abiertas y valores provisionales que debe confirmar el equipo

Ninguna bloquea la ejecución: todas tienen un valor provisional en el código.

1. **Textos (spec §8.1).** Están en `src/estudiantes/alertas_catalogo.py`, con `TEXTOS_APROBADOS = False`: `que_es`, `que_hacer` por rol, las frases del panel, los nombres de los estados («Sin estado: cifras pequeñas» incluido) y `QUE_ES_PRIORIDAD`, `QUE_ES_PRESENTE`, `QUE_ES_REFERENCIA` y `QUE_ES_SIN_ESTADO`.
2. **Rutas (spec §8.1).** Hoy los tres roles usan la ruta vigente, que incluye la «Línea 106» (es de Bogotá); `RUTAS_VALIDADAS = False`.
   - El equipo debe confirmar las líneas de Chía (p. ej. 192 opción 4 o ICBF 141) y la ruta de adultos de la fase 4. Hoy la de adultos lleva solo la Secretaría de Salud y la Comisaría, sin teléfonos.
3. **Umbrales (spec §8.2).** Malestar con 3 de 6 «Muy cierto»; desesperanza con la regla estricta. Se les entrega la sensibilidad: 2, 3 y 4 ítems, y regla estricta frente a amplia.
4. **Ítems con `*` de secundaria (spec §8.3).** Hoy `marcados_en=("primaria",)`. Cuando el equipo marque secundaria, se añade `"secundaria"`.
5. **Regla de faltantes.** Malestar: los 6 ítems respondidos. Desesperanza: ítems 16 y 18 (la amplia: 1, 4, 16 y 18). Si en algún grupo alguien respondió el 18 y no el 16, la desesperanza no se publica en ningún grupo del nivel (falla cerrado; la Task 14 lo detectaría con los datos reales).
6. **Mensajes por rol en `obs360.mensajes`.** No se suben en esta fase. Se suben, con un paso aparte, cuando el equipo apruebe los textos (spec §5.4 los pide en Supabase; se difieren hasta la aprobación).
7. **Sensibilidad y distribución de ítems.** Solo en la vista local de investigadores; no van a Supabase ni al ZIP (el ZIP lleva `alertas.csv`, como pide la spec). ¿Se exportan también, con la misma regla?
8. **Tarjeta y columna de muerte.**
   - La spec pide reemplazar la **tarjeta** para colegio y municipio. El plan también quita, cuando hay alertas, la columna «Piensa en la muerte con frecuencia» de las tablas de los informes y la opción del selector «Comparar».
   - Para familia, la opción se quita siempre: hoy la ve, contra la spec §6.
   - La fila `corte` del ítem 18 se sigue publicando (la usa la vista de investigadores y la familia no la ve).
9. **Estado sin comparación.** El total del nivel y un grupo que es casi todo el nivel (resto < 10) tienen cifra pero no resto con qué compararse: salen como «Para tener presente» con la explicación `QUE_ES_REFERENCIA`. ¿De acuerdo?
10. **Recuadro del PDF de una página.** Omite el «qué hacer» de cada alerta para caber en una página (la ruta sí va). ¿Basta?
11. **Enunciados de RCADS 1 y 4** en la pestaña de investigadores: hay que copiarlos del formulario aplicado.
12. **Calibraciones de la prueba real** (8,8 / 15,1 / 22,0 / 32,4 / 17,0 / 10,8–21,5 / 24,9). Son de la spec con los archivos actuales. Con la exportación nueva de secundaria hay que actualizarlas.

---

## Cambios tras la revisión

Revisión independiente del 7-oct-2026. Todo lo pedido está aplicado en las tareas de arriba; el plan se rehízo sobre la supresión general del PR #8, ya fusionada en esta rama.

- **Supresión general en vez de la regla de árbol.** Se quitaron `cumple`, `colegios_visibles`, `_resto_cumple`, `por_grupo` y `auditar_cifras`. Cada alerta es una familia de `supresion` (celdas, colegios, grados, nivel y resto R) con supresión complementaria y auditoría exacta; `supresion.auditar` la cubre y `publicar.verificar_restas` no cambia. Los grados y las celdas llevan porcentaje cuando la supresión lo permite (cierra las antiguas preguntas 5 y 6).
- **Hallazgo nuevo, resuelto:** la desesperanza está anidada en el corte del ítem 18 que ya se publica. Se suprime como corte anidado `(n − k₁₈, k₁₈ − k, k)`, después del ítem 18 y sin destaparlo nunca (`suprimir(previos=…)`), con falla cerrada si las bases no coinciden. La regresión de lo ya publicado no cambia.
- **Estado.** Solo donde hay porcentaje y solo con cifras publicadas (`alertas.estado(pct, n, pct_nivel, n_nivel)`; el resto del nivel se deduce de ellas). Sin porcentaje: «Sin estado: cifras pequeñas». Pruebas: la firma de `estado`, y que el estado de la tabla y el leído de Supabase se reproducen con las cifras publicadas.
- **Supabase.** Ningún conteo (`casos`, `k_bajo`, `k_alto`) en ninguna fila nueva y estado de alerta solo con porcentaje, como `CHECK … NOT VALID`. Ya no hay `CHECK` de «sin porcentaje por grado» (los grados lo llevan).
- **Importantes:** `alerta_grupo` lleva `n_grupo` y `tests/test_estudiantes_subgrupos.py` está en la lista de la tarea de publicar (ahora Task 6); `alertas.csv` usa `alerta_nombre`; la foto de la Task 0 redondea los flotantes a 9 cifras significativas (probado en 3.14); módulos rancios con `getattr(vc, "ruta_para_rol", None)` → `cat.RUTA_ATENCION` y `try/except` alrededor de `render_panel`, `panel_html` y `tabla_secretaria_html`, con prueba; sensibilidad e ítems solo locales; pruebas con las tres configuraciones reales de resta (`PRIMARIA`, `CON_RESTO` y todo en celdas) contra la fuerza bruta de `test_supresion_propiedades`; mensajes por rol diferidos hasta la aprobación.
- **Menores:** la Task 0 no crea la rama; la ruta del venv de 3.14 es la del scratchpad (`$VENV314`); sin `_sin_uso`; la búsqueda de «k de n» en el HTML se cambió por pruebas sobre las filas publicadas y sobre `Senal`; sin pruebas que lean el código fuente (`PESTANAS` en el investigador; el orden del panel lo ve Playwright); el «*» se detecta con una sola regla, `ingest.tiene_asterisco`.
- **Numeración.** Las antiguas Tasks 4 y 5 son ahora la 4 (funciones puras) y la 5 (supresión y pipeline); publicar pasa de la 7 a la 6 y lo demás corre un número (19 → 18).
- **Verificación del plan.** El código de las Tasks 1 a 13 se probó en una copia del repositorio sin datos reales: 3.13 con 578 passed, 66 skipped (las 64 de datos reales se saltan en la copia) y 3.14 con 582 passed, 62 skipped, incluidas las del PDF y la foto de regresión.
