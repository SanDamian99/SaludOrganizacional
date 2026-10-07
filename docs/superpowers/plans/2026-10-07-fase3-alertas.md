# Fase 3 · Alertas de estudiantes («Señales para actuar a tiempo»): plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

> **⚠️ Estado: borrador NO ejecutable tal cual (revisión independiente del 7-oct-2026).** Antes de ejecutar hay que rehacer las Tasks 4, 5 y 7 sobre la supresión general de `fix/cortes-casos-pequenos` (ver «Revisión independiente» al final).

**Objetivo:** el colegio, el municipio y la familia ven, arriba de las tarjetas, un panel de alertas **por grupo**. Hay dos alertas: «Señales de malestar» y «Señales de desesperanza y pensamientos de muerte». El panel tiene dos estados, «Para tener presente» y «Prioridad»; nunca muestra conteos de casos y su color máximo es naranja. Lleva qué hacer y la ruta. Las alertas también llegan a los informes, al PDF de una página, a la vista de investigadores y a Supabase.

**Arquitectura.** Todo lo nuevo vive en **módulos nuevos**, que siempre se importan frescos aunque Streamlit Cloud conserve módulos viejos en memoria:

| Módulo nuevo | Qué contiene |
|---|---|
| `src/estudiantes/alertas_catalogo.py` | Ítems, umbrales, textos fijos y `RUTAS`; `catalog` los reexporta como `catalog.ALERTAS` y `catalog.RUTAS` |
| `src/estudiantes/alertas.py` | Funciones puras: señal por estudiante, tabla por grupo, sensibilidad, distribución de ítems y auditoría |
| `src/ui/views/estudiantes_alertas.py` | Panel: funciones puras, HTML y `render_panel` |

**Cómo viaja la señal.** La señal de cada estudiante (1 / 0 / NaN) es una columna más de los datos (`ALERTA_*`):
- pasa por la base publicable y por el todo o nada de la fase 1;
- por eso la auditoría de restas sobre `n` ya la cubre.

**Restas con porcentajes.** Con porcentaje y `n` se recuperan los casos. Si se publicaran porcentajes de colegios **y** de grados, una cadena de restas aislaría los casos de una celda pequeña. La prueba sintética lo muestra: con B = una sola celda de sexto, «Sexto − (Nivel − A) = A|Sexto».

Por eso solo llevan porcentaje los grupos de un **árbol**: el nivel y los colegios, que son disjuntos.
- Lo deducible restando son uniones de «átomos»: cada colegio visible y el resto R = nivel − Σ colegios visibles.
- `alertas.colegios_visibles` garantiza que cada átomo cumple **3 ≤ casos ≤ n − 3**.
- Los grados y los grados dentro de un colegio solo publican el **estado** («Prioridad» / «Para tener presente»), sin porcentaje. Basta para lo que pide la spec: «grados en Prioridad» para el colegio y «por grado» para el municipio.
- `publicar.verificar_restas` vuelve a auditar los porcentajes antes de subir. Además, dos `CHECK` nuevos en Supabase rechazan casos y porcentajes por grado.

**Despliegue con módulos o corridas viejas.**
- Las vistas leen `Analisis.alertas` con `getattr` e importan el panel dentro de `try/except`.
- Una corrida publicada sin filas de alerta (la vigente hoy) se sigue leyendo: el panel no aparece y la tarjeta de muerte se queda como está.
- El público verá alertas solo cuando se publique una corrida nueva. Esa es la compuerta de aprobación de los textos.

**Tech stack:** Python 3.13 local / 3.14 en Streamlit Cloud, pandas, numpy, scipy (Wilson ya existe en `stats.wilson`), Streamlit, WeasyPrint (PDF), pytest, Supabase (PostgREST) y Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-10-06-cuidadores-alertas-triangulacion-design.md`: §5.4, con §4, §6, §7 y §8.

**Restricciones que no se negocian:**
- **Nada individual.**
  - Nunca se publica ni se muestra el número de casos de una alerta.
  - El % y el «1 de cada N» se muestran solo si 3 ≤ casos ≤ n − 3. Si no, va el texto fijo de §5.4.
  - En los grados, solo el estado.
- **Ninguna resta delata.** Ni por `n` (fase 1) ni por casos (esta fase).
- **Textos fijos** en `alertas_catalogo`, marcados como provisionales (`TEXTOS_APROBADOS = False`). Nunca los redacta la IA.
  - Nunca «riesgo de suicidio».
  - Siempre «señales», «no es un diagnóstico» y «dónde mirar primero».
- **Rutas sin teléfonos inventados.** El aviso «ruta pendiente de validación» se ve solo en el modo completo, nunca en los informes.
- **Familia** no ve desesperanza ni listas por colegio. Para colegio y municipio, el panel reemplaza la tarjeta de muerte.
- **Lo existente no cambia** salvo donde lo pide la spec. Hay prueba de no regresión sobre el lote sintético publicado y comparación del lote real antes y después.
- **Datos reales:**
  - Las pruebas se omiten si faltan los archivos.
  - Nunca se abren a mano los archivos de `datos_fuente_360`.
  - Ninguna salida imprime casos.
- **Git y migración:**
  - No se fusiona a `main` sin permiso del usuario.
  - La migración la corre el usuario.
  - Después de fusionar, siempre «Reboot app».
- Cada commit termina con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

**Comando de pruebas:** `.venv/bin/python -m pytest -q` (desde la raíz del repo). Línea base al cerrar la fase 2: 460 passed, 2 skipped (Python 3.13) y 462 passed (Python 3.14 / pandas 3, venv del scratchpad).

---

## Mapa de archivos

| Archivo | Qué cambia |
|---|---|
| `src/estudiantes/alertas_catalogo.py` (nuevo) | `ALERTAS`, umbrales, textos del panel, `RUTAS[rol][tipo]`, `ruta()` e `items_marcados_esperados()` |
| `src/estudiantes/catalog.py:415-420` | Reexporta `ALERTAS` y `RUTAS`. `RUTA_ATENCION` queda como alias de la ruta vigente |
| `src/estudiantes/alertas.py` (nuevo) | Señales, `marcar`, `colegios_visibles`, `por_grupo`, `sensibilidad`, `distribucion_items`, `auditar_cifras`, `ordenar` e `items_marcados_por_escala` |
| `src/estudiantes/pipeline.py` | `Analisis.alertas`, `alertas_sensibilidad` y `alertas_items`. `analizar` marca las señales antes de la base |
| `src/estudiantes/publicar.py` | Filas `alerta`, `alerta_grupo`, `alerta_sensibilidad` y `alerta_item` sin casos. Nuevas guardas en `verificar` y `verificar_restas`. `mensajes_alertas_para_subir` |
| `src/estudiantes/lectura.py` | `_tablas_alertas`: rearma las tres tablas. Una corrida vieja deja tablas vacías |
| `supabase/migraciones/2026-10-07c-alertas-sin-casos.sql` (nuevo), `supabase/estudiantes_schema.sql` | Dos `CHECK` nuevos |
| `src/ui/views/estudiantes_alertas.py` (nuevo) | `senales`, `listas_prioridad`, `panel_html`, `tabla_secretaria_html`, `render_panel` y los CSS |
| `src/ui/views/estudiantes_comunidad.py` | Panel arriba de las tarjetas; tarjeta de muerte reemplazada; selector «Comparar» sin muerte para familia; ruta por rol; aviso solo en el modo completo |
| `src/ui/views/estudiantes_informe.py` | Panel en el informe del colegio, tabla por colegio en el de la Secretaría y recuadro compacto en el PDF. Sin la columna de muerte cuando hay panel |
| `src/ui/views/estudiantes_investigador.py` | Pestaña «Alertas», `alertas.csv` en el ZIP y sección en la metodología |
| `tests/test_alertas.py`, `tests/test_alertas_publicar.py`, `tests/test_alertas_vista.py`, `tests/test_alertas_reales.py`, `tests/test_alertas_regresion.py` (nuevos) | Pruebas |
| `tests/fixtures/lote_sintetico_antes_de_alertas.json` (nuevo) | Foto del lote sintético antes de la fase |
| `tests/test_estudiantes_publicar.py`, `tests/test_restas_publicadas.py`, `tests/test_estudiantes_investigador.py` | Ajustes explícitos: tipos nuevos, tope de filas por grupo y 9 archivos en el ZIP |
| `docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md`, `supabase/README.md`, `DESPLIEGUE.md` | Documentación |

**Datos que no cambian.** El SDQ y el RCADS se leen tal como los codifica `ingest` desde el **texto crudo** del formulario (`catalog.MAP_3`: No es cierto = 0, Algo cierto = 1, Muy cierto = 2; `MAP_4_FREQ`: Nunca = 0 … Siempre = 3).
- La codificación defectuosa de la memoria (`Datos_Cuidador_AUDIT.xlsx`) es del dataset de **cuidadores**, no de este.
- Ninguno de los 6 ítems del malestar es inverso (los inversos son 7, 11, 14, 21 y 25): se usan las columnas `SDQ5…SDQ24` sin recodificar.
- La Task 2 lo prueba desde el texto crudo.

---

### Task 0: Rama, línea base y foto de lo que ya se publica

**Files:**
- Create: `tests/test_alertas_regresion.py`
- Create: `tests/fixtures/lote_sintetico_antes_de_alertas.json` (generado)

- [ ] **Step 1: Crear la rama**

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
git fetch origin
# Si la fase 2 ya está en main, partir de main; si no, de la rama de la fase 2.
git switch feature/fase2-navegacion && git pull --ff-only || true
git switch -c feature/fase3-alertas
```

- [ ] **Step 2: Línea base**

Run: `.venv/bin/python -m pytest -q`
Expected: todo pasa salvo las 2 fallas conocidas de `test_knowledge_base`. Anotar los totales («N passed, M skipped») para el PR.

- [ ] **Step 3: Escribir la prueba de no regresión (caracterización)**

`tests/test_alertas_regresion.py`:

```python
"""
Lo que ya se publicaba no cambia con las alertas (spec §7, «No regresión de pantallas»).

`tests/fixtures/lote_sintetico_antes_de_alertas.json` se generó con el código
anterior a la fase 3 (Task 0 del plan) sobre formularios sintéticos de los dos
niveles. Después de la fase 3, el lote sin las filas nuevas («alerta…») debe ser
idéntico. Única excepción admitida: los valores suprimidos de las columnas
nuevas de señal (`ALERTA_*`) dentro de `muestra.suprimidos`.
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


def normalizar(filas: list[dict]) -> list[dict]:
    """Quita lo nuevo de la fase 3 y ordena, para comparar lotes."""
    salida = []
    for f in filas:
        if str(f["tipo"]).startswith("alerta"):
            continue
        f = json.loads(json.dumps(f, ensure_ascii=False, default=str))
        if f["tipo"] == "muestra":
            m = f["detalle"].get("muestra") or {}
            m["suprimidos"] = {k: v for k, v in (m.get("suprimidos") or {}).items()
                               if not str(k).startswith("ALERTA_")}
        salida.append(f)
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
Expected: «filas: N», con N en los cientos.

- [ ] **Step 5: Foto del lote real, fuera del repositorio**

Solo agregados. No se abre ningún archivo fuente a mano; si faltan los formularios, este paso se omite.

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_antes.json" || true
ls -l "$TMPDIR/obs360_lote_antes.json"
```

- [ ] **Step 6: Correr y commit**

Run: `.venv/bin/python -m pytest tests/test_alertas_regresion.py -q`
Expected: 1 passed.

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

`tests/test_alertas.py`:

```python
"""Alertas de grupo de Estudiantes 360 (spec 6-oct-2026, §5.4): catálogo, señales y cifras."""
import re

import numpy as np
import pandas as pd
import pytest

from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat


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
    assert ac.ESTADOS == {"prioridad": "Prioridad", "presente": "Para tener presente"}
    assert ac.CIFRAS_PEQUENAS == ("En este grupo las cifras son muy pequeñas para mostrarse "
                                  "sin riesgo de identificar a alguien; la ruta sigue aplicando.")
    assert ac.NO_ES_DIAGNOSTICO.startswith("No es un diagnóstico")
    assert "dónde mirar primero" in ac.NO_ES_DIAGNOSTICO


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
  · No importa `catalog` (catalog importa este módulo): niveles y roles van
    como texto, y una prueba comprueba que coinciden.
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

# Cifras que no delatan: % y «1 de cada N» solo si MIN_CASOS ≤ casos ≤ n − MIN_CASOS
MIN_CASOS = 3


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
ESTADOS = {"prioridad": "Prioridad", "presente": "Para tener presente"}
NO_ES_DIAGNOSTICO = "No es un diagnóstico: indica dónde mirar primero."
PLANTILLA_CIFRA = "{fraccion} estudiantes {verbo} {senal}."
CIFRAS_PEQUENAS = ("En este grupo las cifras son muy pequeñas para mostrarse sin riesgo de "
                   "identificar a alguien; la ruta sigue aplicando.")
CIFRAS_PEQUENAS_CORTO = "Cifras muy pequeñas para mostrarse"
SOLO_ESTADO = ("Por grado se muestra el estado y no el porcentaje: así ninguna resta entre "
               "cifras publicadas permite identificar a alguien. La ruta sigue aplicando.")
NOTA_AZAR = ("Con muchas comparaciones, alguna «Prioridad» puede deberse al azar; sirve para "
             "orientar, no para concluir.")
QUE_ES_PRIORIDAD = ("«Prioridad»: en este grupo las señales son más frecuentes que en el resto "
                    "del municipio, aun contando el margen de error.")
QUE_ES_PRESENTE = ("«Para tener presente»: las señales aparecen, como en casi todos los grupos, "
                   "sin diferenciarse del resto del municipio.")
TITULO_GRADOS_PRIORIDAD = "Grados en «Prioridad»:"
TITULO_COLEGIOS_PRIORIDAD = "Colegios en «Prioridad»:"
NOTA_TABLA = ("Porcentaje del colegio con señales y su margen de error. El número de "
              "estudiantes con señales no se publica nunca.")
REGLA_CIFRAS = ("El porcentaje y el «1 de cada N» se muestran solo si en el grupo hay al menos "
                f"{MIN_CASOS} estudiantes con señales y al menos {MIN_CASOS} sin ellas, y si "
                "ninguna resta entre los grupos con porcentaje deja un resto que no lo cumpla.")
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

En `src/estudiantes/catalog.py`, reemplazar el bloque `RUTA_ATENCION = [ … ]` (líneas 415-420) por:

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

En `tests/test_alertas.py`, añadir al bloque de imports:

```python
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

`src/estudiantes/alertas.py`:

```python
"""
Alertas de grupo de Estudiantes 360 — funciones puras (spec 6-oct-2026, §5.4).

Por estudiante se calcula una señal (1, 0 o faltante) con las reglas de
`alertas_catalogo`. Lo que sale de aquí es siempre por grupo de la base
publicable (privacidad.base_publicable) y nunca lleva el número de casos.

Qué se publica de cada grupo
  · Nivel y colegios: porcentaje con IC de Wilson, si 3 ≤ casos ≤ n − 3, y
    estado («Prioridad» o «Para tener presente»).
  · Grados y grados dentro de un colegio: solo el estado, nunca el porcentaje.

Por qué los grados no llevan porcentaje. Con porcentaje y n se recuperan los
casos (casos = % × n). Si se publicaran colegios y grados a la vez, una cadena
de restas (p. ej. grado − (nivel − colegio A)) puede aislar los casos de una
celda pequeña aunque cada cifra cumpla la regla por sí sola. Con porcentajes
solo en un árbol (nivel ⊃ colegios, disjuntos) lo que se deduce restando son
uniones de «átomos»: cada colegio visible y el resto R = nivel − Σ colegios
visibles. `colegios_visibles` garantiza que cada átomo cumple 3 ≤ casos ≤ n − 3,
así que cualquier resta también (una unión de átomos que cumplen, cumple).

El n de cada grupo ya está protegido: la señal es una columna más de los datos
y pasa por el todo o nada de `privacidad.aplicar_todo_o_nada`, que la
auditoría de restas de `publicar.verificar_restas` revisa.

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
from src.estudiantes import privacidad
from src.estudiantes.stats import wilson

TOTAL = "total"
TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
NUMERICAS = (TOTAL, "Colegio")          # agrupaciones con porcentaje
SOLO_ESTADO = ("Grado", CRUCE)          # agrupaciones con estado, sin porcentaje

COLUMNAS = {ac.MALESTAR: "ALERTA_malestar", ac.DESESPERANZA: "ALERTA_desesperanza"}
COLUMNA_AMPLIA = "ALERTA_desesperanza_amplia"


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

COLUMNAS_TABLA = ["alerta", "agrupacion", "grupo", "n", "pct", "ic_inf", "ic_sup",
                  "visible", "prioridad"]
COLUMNAS_SENSIBILIDAD = ["alerta", "variante", "etiqueta", "vigente", "n", "pct",
                         "ic_inf", "ic_sup", "visible"]
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
    if (nivel in ac.ALERTAS[ac.DESESPERANZA].niveles
            and set(_columnas("RCADS", ac.ITEMS_REGLA_AMPLIA)) <= set(d.columns)):
        nuevas[COLUMNAS[ac.DESESPERANZA]] = senal_desesperanza(d)
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

### Task 3: Ítems con asterisco

`ingest.InformeIngesta.items_marcados` guarda los encabezados normalizados, sin número de ítem. Aquí se obtienen los números dentro de cada bloque. Se acepta el `*` al principio o al final del encabezado.

**Files:**
- Modify: `src/estudiantes/alertas.py`
- Modify: `tests/test_alertas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Al final de `tests/test_alertas.py`:

```python
# ══ Ítems con «*» ═══════════════════════════════════════════════════════════
def test_items_marcados_al_principio_o_al_final():
    raw = _formulario_sintetico(n=12)
    cols = [c for c in raw.columns if c.startswith("SDQ")]
    raw = raw.rename(columns={cols[4]: "*" + cols[4], cols[5]: cols[5] + " *"})
    assert al.items_marcados_por_escala(raw.columns) == {"SDQ": {5, 6}}


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

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q -k marcad`
Expected: FAIL con `AttributeError: ... 'items_marcados_por_escala'`.

- [ ] **Step 2: Implementar**

Al final de `src/estudiantes/alertas.py`:

```python
# ── Ítems con «*» en el formulario ───────────────────────────────────────────
def items_marcados_por_escala(columnas) -> dict[str, set[int]]:
    """{escala: números de ítem} de los encabezados con «*» (spec §5.4).

    Localiza cada bloque igual que `ingest` (por el prefijo normalizado) y
    numera dentro del bloque. Acepta el «*» en cualquier posición.
    """
    from src.core.texto import norm_txt
    from src.estudiantes.ingest import _PREFIJOS, _bloque
    crudas = [str(c) for c in columnas]
    normalizadas = [norm_txt(c) for c in crudas]
    salida: dict[str, set[int]] = {}
    for escala, prefijo in _PREFIJOS.items():
        indices = _bloque(normalizadas, prefijo)
        marcados = {i for i, col in enumerate(indices, start=1) if "*" in crudas[col]}
        if marcados:
            salida[escala] = marcados
    return salida
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/alertas.py tests/test_alertas.py
git commit -m "feat(alertas): ítems marcados con asterisco por escala" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Qué porcentajes se pueden mostrar

**Files:**
- Modify: `src/estudiantes/alertas.py`
- Modify: `tests/test_alertas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
# ══ Regla de cifras: 3 ≤ casos ≤ n − 3, también en el resto ═════════════════
@pytest.mark.parametrize("k,n,esperado", [
    (3, 10, False),     # n − 3 = 7 ≥ 3 pero… 3 ≤ 3 ≤ 7: sí cumple
])
def _sin_uso(k, n, esperado):
    pass


@pytest.mark.parametrize("k,n,esperado", [
    (2, 30, False), (3, 30, True), (27, 30, True), (28, 30, False),
    (3, 9, False),          # por debajo del mínimo de grupo
    (5, 10, True), (0, 50, False), (50, 50, False)])
def test_cumple(k, n, esperado):
    assert al.cumple(k, n) is esperado


def test_colegios_visibles_sin_resto():
    ver, cols = al.colegios_visibles((30, 100), {"A": (12, 40), "B": (15, 30), "C": (3, 30)})
    assert ver and cols == {"A", "B", "C"}


def test_un_resto_pequeno_obliga_a_ocultar_el_colegio_mas_chico():
    # resto = 100 − 90 = 10 estudiantes con 1 caso: restando se delataría
    ver, cols = al.colegios_visibles((30, 100), {"A": (12, 40), "B": (9, 30), "C": (8, 20)})
    assert ver and cols == {"A", "B"}             # C pasa al resto: 30 con 9 casos


def test_un_colegio_pequeno_tambien_protege_por_resta():
    # C no cumple (2 casos); si A y B se mostraran, nivel − A − B = C
    ver, cols = al.colegios_visibles((29, 100), {"A": (12, 40), "B": (15, 30), "C": (2, 30)})
    assert ver and cols == {"A"}                  # se oculta B (el menor): resto B ∪ C


def test_si_el_nivel_no_cumple_no_se_muestra_nada():
    assert al.colegios_visibles((2, 25), {"A": (1, 12), "B": (1, 13)}) == (False, set())
```

Borrar la función auxiliar `_sin_uso` antes de correr. Era solo un borrador: no debe quedar en el archivo.

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q -k "cumple or visibles or resto or nivel_no"`
Expected: FAIL con `AttributeError: ... 'cumple'`.

- [ ] **Step 2: Implementar**

Añadir a `src/estudiantes/alertas.py`, antes de la sección de ítems con «*»:

```python
# ── Regla de cifras ──────────────────────────────────────────────────────────
def cumple(k: int, n: int) -> bool:
    """¿Se puede mostrar el porcentaje? n ≥ MIN_GROUP_N y 3 ≤ casos ≤ n − 3."""
    return bool(n >= cat.MIN_GROUP_N and ac.MIN_CASOS <= k <= n - ac.MIN_CASOS)


def _resto_cumple(k: int, n: int) -> bool:
    """Un resto vacío no delata a nadie; uno con gente, solo si 3 ≤ casos ≤ n − 3."""
    return n == 0 or ac.MIN_CASOS <= k <= n - ac.MIN_CASOS


def colegios_visibles(nivel: tuple[int, int], colegios: dict[str, tuple[int, int]]
                      ) -> tuple[bool, set[str]]:
    """(¿se muestra el nivel?, colegios que muestran porcentaje).

    `nivel` y cada colegio son (casos, n) de respuestas válidas; los colegios
    son disjuntos y están dentro del nivel. Se parte de los que cumplen la
    regla. Si el resto R = nivel − Σ colegios visibles no la cumple, se oculta
    el colegio visible más pequeño (pasa a formar parte de R) y se vuelve a
    mirar. Con eso todo átomo (cada colegio visible y R) cumple.
    """
    k_niv, n_niv = nivel
    if not cumple(k_niv, n_niv):
        return False, set()
    visibles = {c for c, (k, n) in colegios.items() if cumple(k, n)}
    while visibles:
        k_r = k_niv - sum(colegios[c][0] for c in visibles)
        n_r = n_niv - sum(colegios[c][1] for c in visibles)
        if _resto_cumple(k_r, n_r):
            break
        visibles.discard(min(visibles, key=lambda c: (colegios[c][1], c)))
    return True, visibles
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/alertas.py tests/test_alertas.py
git commit -m "feat(alertas): regla 3 ≤ casos ≤ n − 3 con el resto del nivel" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Tabla por grupo, sensibilidad, ítems y auditoría

**Files:**
- Modify: `src/estudiantes/alertas.py`
- Modify: `tests/test_alertas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
# ══ Tabla por grupo ═════════════════════════════════════════════════════════
def _d_senal(conteos: dict, columna="ALERTA_malestar") -> pd.DataFrame:
    """(colegio, grado) → (n, casos)."""
    filas = [dict(Colegio=c, Grado=g, **{columna: 1.0 if i < k else 0.0})
             for (c, g), (n, k) in conteos.items() for i in range(n)]
    return pd.DataFrame(filas)


def _tabla(conteos):
    d = _d_senal(conteos)
    b = privacidad.base_publicable(d)
    return d, b, al.por_grupo(d, b, cat.NIVEL_SECUNDARIA)


def _f(t, agrupacion, grupo="Todos", alerta="malestar"):
    sel = t[(t["alerta"] == alerta) & (t["agrupacion"] == agrupacion)
            & (t["grupo"].astype(str) == grupo)]
    return sel.iloc[0] if len(sel) else None


# B tiene 2 casos: mostrar A dejaría nivel − A = B
CONTEOS_B = {("A", "Sexto"): (30, 6), ("A", "Séptimo"): (30, 9),
             ("B", "Sexto"): (20, 2), ("C", "Sexto"): (4, 1)}
CONTEOS_D = {**CONTEOS_B, ("D", "Sexto"): (20, 4), ("D", "Séptimo"): (20, 4)}
CONTEOS_P = {("A", "Sexto"): (40, 30), ("A", "Séptimo"): (40, 4),
             ("B", "Sexto"): (40, 4), ("B", "Séptimo"): (40, 4)}


def test_la_tabla_nunca_trae_casos():
    _, _, t = _tabla(CONTEOS_P)
    assert list(t.columns) == al.COLUMNAS_TABLA
    assert "casos" not in t.columns


def test_un_colegio_se_oculta_si_al_restarlo_queda_un_colegio_pequeno():
    _, _, t = _tabla(CONTEOS_B)
    total = _f(t, "total")
    assert total["visible"] and total["pct"] == al.wilson(17, 80)[0]
    assert not _f(t, "Colegio", "A")["visible"] and pd.isna(_f(t, "Colegio", "A")["pct"])
    assert not _f(t, "Colegio", "B")["visible"]


def test_se_oculta_el_colegio_mas_chico_para_cubrir_el_resto():
    _, _, t = _tabla(CONTEOS_D)
    assert _f(t, "Colegio", "A")["visible"]
    assert not _f(t, "Colegio", "D")["visible"] and not _f(t, "Colegio", "B")["visible"]


def test_por_grado_solo_va_el_estado():
    _, _, t = _tabla(CONTEOS_P)
    por_grado = t[t["agrupacion"].isin(al.SOLO_ESTADO)]
    assert len(por_grado) and por_grado["pct"].isna().all()
    assert not por_grado["visible"].any()


def test_prioridad_contra_el_resto_del_municipio():
    _, _, t = _tabla(CONTEOS_P)
    assert _f(t, "Colegio", "A")["prioridad"] and not _f(t, "Colegio", "B")["prioridad"]
    assert _f(t, "Grado", "Sexto")["prioridad"] and not _f(t, "Grado", "Séptimo")["prioridad"]
    assert _f(t, "Colegio×Grado", "A|Sexto")["prioridad"]
    assert not _f(t, "total")["prioridad"]


def test_los_grupos_fuera_de_la_base_no_aparecen():
    _, _, t = _tabla(CONTEOS_B)
    assert not t["grupo"].astype(str).str.contains("C").any()


def test_las_senales_faltantes_no_cuentan():
    d = _d_senal(CONTEOS_P)
    d.loc[d.index[:5], "ALERTA_malestar"] = np.nan
    t = al.por_grupo(d, privacidad.base_publicable(d), cat.NIVEL_SECUNDARIA)
    assert _f(t, "total")["n"] == 155


# ══ Auditoría de cifras ═════════════════════════════════════════════════════
@pytest.mark.parametrize("conteos", [CONTEOS_B, CONTEOS_D, CONTEOS_P])
def test_la_auditoria_pasa_con_la_tabla_que_produce_por_grupo(conteos):
    d, b, t = _tabla(conteos)
    assert al.auditar_cifras(d, b, t) == []


def test_la_auditoria_detecta_un_colegio_que_delata_al_resto():
    d, b, t = _tabla(CONTEOS_B)
    t = t.copy()
    i = t.index[(t["agrupacion"] == "Colegio") & (t["grupo"] == "A")][0]
    t.loc[i, ["pct", "ic_inf", "ic_sup", "visible"]] = [25.0, 15.0, 37.0, True]
    assert any("resto" in p for p in al.auditar_cifras(d, b, t))


def test_la_auditoria_detecta_un_porcentaje_por_grado():
    d, b, t = _tabla(CONTEOS_P)
    t = t.copy()
    i = t.index[t["agrupacion"] == "Grado"][0]
    t.loc[i, ["pct", "visible"]] = [40.0, True]
    assert any("solo va el estado" in p for p in al.auditar_cifras(d, b, t))


def test_la_auditoria_detecta_una_columna_de_casos():
    d, b, t = _tabla(CONTEOS_P)
    assert any("casos" in p for p in al.auditar_cifras(d, b, t.assign(casos=1)))


# ══ Sensibilidad e ítems (solo el nivel) ════════════════════════════════════
def test_sensibilidad_oculta_una_variante_que_difiere_en_menos_de_tres():
    d = pd.DataFrame({"Colegio": "A", "Grado": "Sexto",
                      "ALERTA_malestar_2": [1.0] * 20 + [0.0] * 80,
                      "ALERTA_malestar": [1.0] * 10 + [0.0] * 90,
                      "ALERTA_malestar_4": [1.0] * 9 + [0.0] * 91})
    s = al.sensibilidad(d, privacidad.base_publicable(d), cat.NIVEL_SECUNDARIA)
    s = s.set_index("variante")
    assert s.loc["malestar_3", "visible"] and s.loc["malestar_2", "visible"]
    assert not s.loc["malestar_4", "visible"] and pd.isna(s.loc["malestar_4", "pct"])
    assert (s["n"] == 100).all() and "casos" not in s.columns


def test_sensibilidad_oculta_la_regla_amplia_si_le_faltan_filas():
    d = pd.DataFrame({"Colegio": "A", "Grado": "Sexto",
                      "ALERTA_desesperanza": [1.0] * 20 + [0.0] * 80,
                      "ALERTA_desesperanza_amplia": [1.0] * 30 + [0.0] * 69 + [np.nan]})
    s = al.sensibilidad(d, privacidad.base_publicable(d), cat.NIVEL_SECUNDARIA)
    s = s.set_index("variante")
    assert s.loc["desesperanza_estricta", "visible"]
    assert not s.loc["desesperanza_amplia", "visible"]


def test_distribucion_de_items_oculta_el_item_con_una_respuesta_rara():
    d = pd.DataFrame({"Colegio": "A", "Grado": "Sexto", "ALERTA_malestar": 0.0,
                      "SDQ5": [0] * 90 + [1] * 8 + [2] * 2,
                      "SDQ6": [0] * 60 + [1] * 30 + [2] * 10})
    t = al.distribucion_items(d, privacidad.base_publicable(d), cat.NIVEL_SECUNDARIA)
    assert t[t["item"] == "SDQ5"]["pct"].isna().all()
    sdq6 = t[t["item"] == "SDQ6"]
    assert sdq6["pct"].tolist() == [60.0, 30.0, 10.0]
    assert sdq6["respuesta"].tolist() == ["No es cierto", "Algo cierto", "Muy cierto"]
    assert list(t.columns) == al.COLUMNAS_ITEMS


def test_ordenar_es_estable_ante_filas_barajadas():
    _, _, t = _tabla(CONTEOS_P)
    barajada = t.sample(frac=1, random_state=3)
    pd.testing.assert_frame_equal(al.ordenar(barajada, cat.NIVEL_SECUNDARIA), t)
```

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: FAIL con `AttributeError: ... 'por_grupo'`.

- [ ] **Step 2: Implementar**

Añadir a `src/estudiantes/alertas.py`, después de `colegios_visibles`:

```python
# ── Tabla por grupo ──────────────────────────────────────────────────────────
def _kn(d: pd.DataFrame, columna: str, idx) -> tuple[int, int]:
    """(casos, n) de señales válidas en las filas `idx`. Nunca sale de este módulo."""
    v = d.loc[d.index.intersection(idx), columna].dropna()
    return int(v.sum()), int(len(v))


def _prioridad(k: int, n: int, k_nivel: int, n_nivel: int) -> bool:
    """«Prioridad»: el IC del grupo queda por encima del IC del resto del municipio.

    El resto es el nivel sin el grupo, no el total (Laura Vicuña es casi la
    mitad de secundaria). Solo se evalúa si el grupo cumple 3 ≤ casos ≤ n − 3:
    un estado no debe delatar lo que la cifra oculta.
    """
    k_r, n_r = k_nivel - k, n_nivel - n
    if not cumple(k, n) or n_r < cat.MIN_GROUP_N:
        return False
    _, inferior, _ = wilson(k, n)
    _, _, superior_resto = wilson(k_r, n_r)
    return bool(inferior > superior_resto)


def _fila_tabla(alerta, agrupacion, grupo, k, n, visible, prioridad) -> dict:
    pct = ic_inf = ic_sup = None
    if visible:
        pct, ic_inf, ic_sup = wilson(k, n)
    return dict(alerta=alerta, agrupacion=agrupacion, grupo=str(grupo), n=int(n),
                pct=pct, ic_inf=ic_inf, ic_sup=ic_sup,
                visible=bool(visible), prioridad=bool(prioridad))


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


def por_grupo(d: pd.DataFrame, base, nivel: str) -> pd.DataFrame:
    """Una fila por alerta y grupo de la base publicable. Sin casos, nunca.

    `d` son los datos ya enmascarados (todo o nada) con las columnas de señal.
    """
    if d is None or d.empty or base is None:
        return pd.DataFrame(columns=COLUMNAS_TABLA)
    filas: list[dict] = []
    en_nivel = d.loc[d.index.intersection(base.nivel)]
    for clave in claves_del_nivel(en_nivel, nivel):
        col = COLUMNAS[clave]
        k_niv, n_niv = _kn(d, col, base.nivel)
        if n_niv < cat.MIN_GROUP_N:
            continue
        cuentas = {c: _kn(d, col, idx) for c, idx in base.colegios.items()}
        ver_nivel, ver_colegios = colegios_visibles((k_niv, n_niv), cuentas)
        filas.append(_fila_tabla(clave, TOTAL, TODOS, k_niv, n_niv, ver_nivel, False))
        for c, (k, n) in cuentas.items():
            if n < cat.MIN_GROUP_N:
                continue
            ver = c in ver_colegios
            filas.append(_fila_tabla(clave, "Colegio", c, k, n, ver,
                                     ver and _prioridad(k, n, k_niv, n_niv)))
        for agrupacion, grupos in (("Grado", base.grados), (CRUCE, base.celdas)):
            for g, idx in grupos.items():
                k, n = _kn(d, col, idx)
                if n < cat.MIN_GROUP_N:
                    continue
                filas.append(_fila_tabla(clave, agrupacion, g, k, n, False,
                                         _prioridad(k, n, k_niv, n_niv)))
    return ordenar(pd.DataFrame(filas, columns=COLUMNAS_TABLA), nivel)


# ── Sensibilidad y distribución de ítems (solo el nivel publicado) ──────────
def sensibilidad(d: pd.DataFrame, base, nivel: str) -> pd.DataFrame:
    """Prevalencia del nivel con cada variante de umbral o de regla.

    Todas las variantes de una alerta usan las mismas filas: las válidas para
    la regla vigente. Una variante que no está completa en esas filas, o que
    difiere de la vigente en 1 o 2 estudiantes, sale sin cifra (restar dos
    porcentajes del mismo n daría ese puñado).
    """
    if d is None or d.empty:
        return pd.DataFrame(columns=COLUMNAS_SENSIBILIDAD)
    dn = d.loc[d.index.intersection(base.nivel)] if base is not None else d
    filas: list[dict] = []
    for alerta in claves_del_nivel(dn, nivel):
        variantes = [(v, col, etq, vig) for v, (a, col, etq, vig) in VARIANTES.items()
                     if a == alerta and col in dn.columns]
        X = dn.loc[dn[COLUMNAS[alerta]].notna(), [col for _, col, _, _ in variantes]]
        n = len(X)
        if n < cat.MIN_GROUP_N:
            continue
        ks = {v: int(X[col].sum()) for v, col, _, _ in variantes}
        completas = {v: bool(X[col].notna().all()) for v, col, _, _ in variantes}
        vigente = next(v for v, _, _, vig in variantes if vig)
        visibles = {v for v in ks if completas[v] and cumple(ks[v], n)}
        if vigente not in visibles:
            visibles = set()
        for v in list(visibles):
            diferencia = abs(ks[v] - ks[vigente])
            if v != vigente and 0 < diferencia < ac.MIN_CASOS:
                visibles.discard(v)
        for v, _, etiqueta, vig in variantes:
            ver = v in visibles
            pct, ic_inf, ic_sup = wilson(ks[v], n) if ver else (None, None, None)
            filas.append(dict(alerta=alerta, variante=v, etiqueta=etiqueta, vigente=vig,
                              n=n, pct=pct, ic_inf=ic_inf, ic_sup=ic_sup, visible=ver))
    return pd.DataFrame(filas, columns=COLUMNAS_SENSIBILIDAD)


def distribucion_items(d: pd.DataFrame, base, nivel: str) -> pd.DataFrame:
    """% de cada respuesta en los ítems de las alertas, en el nivel publicado.

    Si alguna respuesta de un ítem queda fuera de [3, n − 3], el ítem entero
    sale sin cifras: con una sola respuesta oculta, se deduciría restando las
    demás de n.
    """
    if d is None or d.empty:
        return pd.DataFrame(columns=COLUMNAS_ITEMS)
    dn = d.loc[d.index.intersection(base.nivel)] if base is not None else d
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
            ver = all(cumple(c, n) for c in conteos)
            for etiqueta, c in zip(etiquetas, conteos):
                filas.append(dict(alerta=alerta, item=col,
                                  enunciado=ac.ENUNCIADOS_ITEMS.get(col, col),
                                  respuesta=etiqueta, n=n,
                                  pct=round(100 * c / n, 1) if ver else None))
    return pd.DataFrame(filas, columns=COLUMNAS_ITEMS)


# ── Auditoría (la usa publicar.verificar_restas) ────────────────────────────
def _indices(base, agrupacion: str, grupo: str):
    if agrupacion == TOTAL:
        return base.nivel
    return {"Colegio": base.colegios, "Grado": base.grados,
            CRUCE: base.celdas}.get(agrupacion, {}).get(str(grupo))


def auditar_cifras(d: pd.DataFrame, base, tabla: pd.DataFrame) -> list[str]:
    """Problemas de la tabla de alertas frente a los datos. Lista vacía = se puede publicar.

    Comprueba que no hay casos, que solo nivel y colegios llevan porcentaje,
    que cada porcentaje cumple 3 ≤ casos ≤ n − 3, que el resto del nivel sin
    los colegios con porcentaje también cumple y que ninguna «Prioridad» está
    en un grupo que no cumple. Los mensajes no dicen cuántos casos hay.
    """
    problemas: list[str] = []
    if tabla is None or len(tabla) == 0 or base is None or d is None or d.empty:
        return problemas
    if "casos" in tabla.columns:
        problemas.append("la tabla de alertas trae una columna de casos")
    for clave, t in tabla.groupby("alerta", sort=False):
        col = COLUMNAS.get(clave)
        if col is None or col not in d.columns:
            continue
        con_cifra = t[t["pct"].notna()]
        for f in con_cifra[~con_cifra["agrupacion"].isin(NUMERICAS)].itertuples():
            problemas.append(f"{clave}: {f.agrupacion} {f.grupo} trae porcentaje; "
                             "por grado solo va el estado")
        k_niv, n_niv = _kn(d, col, base.nivel)
        colegios = []
        for f in con_cifra[con_cifra["agrupacion"].isin(NUMERICAS)].itertuples():
            idx = _indices(base, f.agrupacion, f.grupo)
            if idx is None:
                problemas.append(f"{clave}: {f.agrupacion} {f.grupo} no está en la base")
                continue
            k, n = _kn(d, col, idx)
            if not cumple(k, n):
                problemas.append(f"{clave}: {f.agrupacion} {f.grupo} muestra un porcentaje "
                                 "con casos fuera de [3, n − 3]")
            if f.agrupacion == "Colegio":
                colegios.append((k, n))
        if colegios:
            k_r = k_niv - sum(k for k, _ in colegios)
            n_r = n_niv - sum(n for _, n in colegios)
            if not _resto_cumple(k_r, n_r):
                problemas.append(f"{clave}: el nivel menos los colegios con porcentaje deja "
                                 "un resto con casos fuera de [3, n − 3]")
        for f in t[t["prioridad"].astype(bool)].itertuples():
            idx = _indices(base, f.agrupacion, f.grupo)
            if idx is not None and not cumple(*_kn(d, col, idx)):
                problemas.append(f"{clave}: {f.agrupacion} {f.grupo} está en «Prioridad» "
                                 "sin cumplir 3 ≤ casos ≤ n − 3")
    return problemas
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/alertas.py tests/test_alertas.py
git commit -m "feat(alertas): tabla por grupo sin casos, sensibilidad, ítems y auditoría" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: El pipeline calcula las alertas

**Files:**
- Modify: `src/estudiantes/pipeline.py`
- Create: `tests/test_alertas_publicar.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_alertas_publicar.py`:

```python
"""Alertas de punta a punta sin red: pipeline → publicar → leer (spec §5.4 y §7)."""
import copy
import os
import random

import pandas as pd
import pytest

from src.estudiantes import alertas as al
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring
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


# ══ Pipeline ════════════════════════════════════════════════════════════════
def test_el_analisis_trae_las_alertas_por_grupo(analisis):
    t = analisis.alertas
    assert list(t.columns) == al.COLUMNAS_TABLA and "casos" not in t.columns
    assert set(t["alerta"]) == {"malestar", "desesperanza"}
    assert t[t["agrupacion"] == al.TOTAL]["visible"].all()
    assert t[t["agrupacion"].isin(al.SOLO_ESTADO)]["pct"].isna().all()
    assert not t["grupo"].astype(str).str.contains("DiosCh").any()
    assert GRADO_PEQUENO not in set(t["grupo"].astype(str))


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

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q`
Expected: FAIL con `AttributeError: 'Analisis' object has no attribute 'alertas'`.

- [ ] **Step 2: Implementar**

En `src/estudiantes/pipeline.py`:

1. Import: `from src.estudiantes import alertas, ingest, privacidad, scoring, stats`.
2. En `class Analisis`, después de `subgrupos`, antes de `base`:

```python
    # Alertas de grupo (spec §5.4, alertas.py): por grupo de la base publicable,
    # sin casos. Vacías en una corrida anterior a la fase 3.
    alertas: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas_sensibilidad: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas_items: pd.DataFrame = field(default_factory=pd.DataFrame)
```

3. En `analizar`, justo después de `d = datos_puntuados[...]` (línea 93-94):

```python
    # Señal de alerta por estudiante (1 / 0 / NaN). Entra en la base publicable y
    # en el todo o nada como cualquier otra columna, así que la auditoría de
    # restas de n la cubre. Nunca se publica fila a fila.
    d = alertas.marcar(d, nivel)
```

4. Después de `a.subgrupos = subanalizar(dm, nivel, claves, base)`:

```python
    a.alertas = alertas.por_grupo(dm, base, nivel)
    a.alertas_sensibilidad = alertas.sensibilidad(dm, base, nivel)
    a.alertas_items = alertas.distribucion_items(dm, base, nivel)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py tests/test_alertas_regresion.py tests/test_estudiantes.py tests/test_estudiantes_subgrupos.py tests/test_privacidad.py -q`
Expected: todo pasa. La no regresión sigue idéntica: las columnas nuevas se enmascaran por separado.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/pipeline.py tests/test_alertas_publicar.py
git commit -m "feat(alertas): el análisis trae alertas por grupo, sensibilidad e ítems" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Publicar sin casos

**Files:**
- Modify: `src/estudiantes/publicar.py`
- Modify: `tests/test_alertas_publicar.py`, `tests/test_estudiantes_publicar.py:135-145,163`, `tests/test_restas_publicadas.py:27`

- [ ] **Step 1: Escribir las pruebas que fallan**

Al final de `tests/test_alertas_publicar.py`:

```python
# ══ Publicar ════════════════════════════════════════════════════════════════
def _filas(analisis):
    return publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})


def test_las_alertas_se_publican_sin_casos(analisis):
    filas = _filas(analisis)
    alertas = [f for f in filas if f["tipo"].startswith("alerta")]
    assert {f["tipo"] for f in alertas} == {"alerta", "alerta_grupo",
                                            "alerta_sensibilidad", "alerta_item"}
    for f in alertas:
        assert "casos" not in f["detalle"]
        if f["agrupacion"] in al.SOLO_ESTADO:
            assert f["valor"] is None and f["ic_inf"] is None and f["ic_sup"] is None
        if not f["detalle"].get("visible", True):
            assert f["valor"] is None
    publicar.verificar(filas)


def test_verificar_rechaza_una_alerta_con_casos(analisis):
    fila = next(f for f in _filas(analisis) if f["tipo"] == "alerta")
    mala = dict(fila, detalle=dict(fila["detalle"], casos=5))
    with pytest.raises(publicar.PublicacionInsegura, match="casos"):
        publicar.verificar([mala])


def test_verificar_rechaza_un_porcentaje_por_grado(analisis):
    fila = next(f for f in _filas(analisis)
                if f["tipo"] == "alerta_grupo" and f["agrupacion"] == "Grado")
    with pytest.raises(publicar.PublicacionInsegura, match="solo lleva el estado"):
        publicar.verificar([dict(fila, valor=30.0)])


def test_verificar_restas_bloquea_una_tabla_de_alertas_manipulada(analisis):
    a = copy.copy(analisis)
    t = a.alertas.copy()
    i = t.index[t["agrupacion"] == "Grado"][0]
    t.loc[i, ["pct", "visible"]] = [40.0, True]
    a.alertas = t
    assert any("alertas" in p for p in publicar.verificar_restas({cat.NIVEL_SECUNDARIA: a}))


def test_mensajes_de_alertas_por_rol():
    ms = publicar.mensajes_alertas_para_subir()
    claves = {(m["clave"], m["accion_rol"]) for m in ms}
    assert ("alerta_desesperanza", "familia") not in claves
    assert ("alerta_malestar", "familia") in claves
    assert all(m["accion"].strip() and m["significa"].strip() for m in ms)
```

En `tests/test_estudiantes_publicar.py`:
- En `test_el_lote_real_solo_tiene_tipos_y_agrupaciones_previstas`, añadir al conjunto de tipos: `# alertas de grupo (fase 3), sin casos` y `"alerta", "alerta_grupo", "alerta_sensibilidad", "alerta_item"`.
- En `test_ninguna_fila_viene_de_datos_individuales`, cambiar `tope = 6 + 16 + 4 + 18` por `tope = 6 + 16 + 4 + 18 + 2   # … + las dos alertas`.

En `tests/test_restas_publicadas.py:27`: `TIPOS = ("corte", "banda", "item", "alerta")`. La resta de `n` cubre también las alertas.

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q`
Expected: FAIL (no hay filas `alerta…`).

- [ ] **Step 2: Implementar**

En `src/estudiantes/publicar.py`:

1. Docstring, sección QUÉ SUBE: añadir «Las alertas de grupo (`alerta…`) nunca llevan casos; por grado, solo el estado».

2. En `aplanar`, justo antes de `# descripción de la muestra`:

```python
        # alertas de grupo (spec §5.4): sin casos, nunca; por grado, solo el estado
        filas.extend(_aplanar_alertas(nivel, a))
```

3. Después de `_aplanar_subgrupo`:

```python
def _aplanar_alertas(nivel: str, a) -> list[dict]:
    """Filas de alertas: n, % e IC donde se pueden mostrar, y el estado. Nunca casos."""
    from src.estudiantes import alertas as al
    from src.estudiantes import alertas_catalogo as ac
    filas: list[dict] = []
    tabla = getattr(a, "alertas", None)
    if tabla is not None and len(tabla):
        for f in tabla.to_dict("records"):
            if int(f["n"]) < cat.MIN_GROUP_N or f["alerta"] not in ac.ALERTAS:
                continue
            total = f["agrupacion"] == al.TOTAL
            visible = (bool(f["visible"]) and f["agrupacion"] in al.NUMERICAS
                       and pd.notna(f["pct"]))
            filas.append(_fila(
                nivel, "alerta" if total else "alerta_grupo", f["alerta"], f["n"],
                f["pct"] if visible else None,
                escala=ac.ALERTAS[f["alerta"]].nombre,
                agrupacion="total" if total else f["agrupacion"],
                grupo=None if total else str(f["grupo"]),
                ic_inf=f["ic_inf"] if visible else None,
                ic_sup=f["ic_sup"] if visible else None,
                visible=visible, prioridad=bool(f["prioridad"])))
    sens = getattr(a, "alertas_sensibilidad", None)
    if sens is not None and len(sens):
        for i, f in enumerate(sens.to_dict("records")):
            visible = bool(f["visible"]) and pd.notna(f["pct"])
            filas.append(_fila(
                nivel, "alerta_sensibilidad", f["variante"], f["n"],
                f["pct"] if visible else None, escala=ac.ALERTAS[f["alerta"]].nombre,
                ic_inf=f["ic_inf"] if visible else None,
                ic_sup=f["ic_sup"] if visible else None,
                alerta=f["alerta"], etiqueta=f["etiqueta"], vigente=bool(f["vigente"]),
                visible=visible, orden=i))
    items = getattr(a, "alertas_items", None)
    if items is not None and len(items):
        for i, ((alerta, item), g) in enumerate(items.groupby(["alerta", "item"], sort=False)):
            pcts = [None if pd.isna(p) else float(p) for p in g["pct"]]
            filas.append(_fila(
                nivel, "alerta_item", item, int(g["n"].iloc[0]), None,
                escala=ac.ALERTAS[alerta].nombre, alerta=alerta,
                enunciado=str(g["enunciado"].iloc[0]), respuestas=list(g["respuesta"]),
                pct=pcts, visible=all(p is not None for p in pcts), orden=i))
    return filas
```

4. En `verificar`, dentro del bucle, después de la comprobación de identificadores:

```python
        if str(f.get("tipo", "")).startswith("alerta"):
            if "casos" in (f.get("detalle") or {}):
                problemas.append(f"fila {i} ({f['tipo']}/{f['clave']}/{f['grupo']}): "
                                 "una alerta no puede llevar casos")
            if (f.get("agrupacion") in ("Grado", privacidad.AGRUPACION_CRUCE)
                    and any(f.get(c) is not None for c in ("valor", "ic_inf", "ic_sup"))):
                problemas.append(f"fila {i} ({f['tipo']}/{f['clave']}/{f['grupo']}): "
                                 "por grado una alerta solo lleva el estado")
```

5. En `verificar_restas`, dentro del bucle y después de `problemas += …`:

```python
        tabla = getattr(a, "alertas", None)
        if tabla is not None and len(tabla):
            from src.estudiantes import alertas
            problemas += [f"{nivel} · alertas · {p}"
                          for p in alertas.auditar_cifras(a.datos, a.base, tabla)]
```

Actualizar su docstring: «… y los porcentajes de las alertas (alertas.auditar_cifras)».

6. Después de `mensajes_para_subir`:

```python
def mensajes_alertas_para_subir() -> list[dict]:
    """Textos de las alertas por rol, con el formato de obs360.mensajes (clave «alerta_…»)."""
    from src.estudiantes import alertas_catalogo as ac
    salida = []
    for clave, alerta in ac.ALERTAS.items():
        for rol in alerta.roles:
            accion = alerta.que_hacer.get(rol, "")
            if accion:
                salida.append(dict(clave=f"alerta_{clave}", titulo=alerta.nombre,
                                   significa=alerta.que_es, accion_rol=rol,
                                   accion=accion, vigente=True))
    return salida
```

7. En `main`, en el JSON del ensayo: `mensajes=mensajes_para_subir() + mensajes_alertas_para_subir(),`.

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py tests/test_estudiantes_publicar.py tests/test_restas_publicadas.py tests/test_alertas_regresion.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/publicar.py tests/test_alertas_publicar.py tests/test_estudiantes_publicar.py tests/test_restas_publicadas.py
git commit -m "feat(publicar): alertas sin casos y auditoría de sus porcentajes" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Migración de Supabase (la corre el usuario)

La columna `tipo` no tiene `CHECK`, así que publicar funciona sin migración. Esto añade la última barrera en la base.

**Files:**
- Create: `supabase/migraciones/2026-10-07c-alertas-sin-casos.sql`
- Modify: `supabase/estudiantes_schema.sql`
- Modify: `tests/test_alertas_publicar.py`

- [ ] **Step 1: Prueba que falla**

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
        assert "resultados_alerta_sin_casos" in texto
        assert "tipo NOT LIKE 'alerta%'" in texto and "detalle ? 'casos'" in texto
        assert "resultados_alerta_grado_sin_cifra" in texto
```

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q -k migracion`
Expected: FAIL con `FileNotFoundError`.

- [ ] **Step 2: Crear la migración**

`supabase/migraciones/2026-10-07c-alertas-sin-casos.sql`:

```sql
-- ════════════════════════════════════════════════════════════════════════════
-- Observatorio 360 · alertas de grupo sin casos (fase 3, spec §5.4)
--
-- Ejecutar en Supabase → SQL Editor → Run, ANTES de publicar una corrida con
-- alertas. Aditiva e idempotente.
-- Publicar funciona sin ella (la columna `tipo` no tiene CHECK); es la última
-- barrera: aunque el código fallara, la base rechaza una fila de alerta con el
-- número de casos o con un porcentaje por grado.
-- Las filas actuales no son de tipo «alerta…»: los ADD CONSTRAINT no fallan.
-- ════════════════════════════════════════════════════════════════════════════

ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_alerta_sin_casos;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_alerta_sin_casos CHECK (
    tipo NOT LIKE 'alerta%' OR NOT (detalle ? 'casos'));

ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_alerta_grado_sin_cifra;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_alerta_grado_sin_cifra CHECK (
    tipo <> 'alerta_grupo'
    OR agrupacion NOT IN ('Grado', 'Colegio×Grado')
    OR (valor IS NULL AND ic_inf IS NULL AND ic_sup IS NULL));

COMMENT ON COLUMN obs360.resultados.tipo IS
  'descriptivo | banda | corte | correlacion | grupo | modelo | tercil | percentil | '
  'item | icc | contraste | muestra | solapamiento | ingesta | *_grupo | '
  'alerta | alerta_grupo | alerta_sensibilidad | alerta_item (las alertas, sin casos)';

-- Comprobación: dos filas
-- SELECT conname FROM pg_constraint
--  WHERE conname IN ('resultados_alerta_sin_casos', 'resultados_alerta_grado_sin_cifra');
```

- [ ] **Step 3: Copiar al esquema vigente**

En `supabase/estudiantes_schema.sql`:
- Pegar el mismo bloque (los dos `DROP/ADD CONSTRAINT` y el `COMMENT`) justo después del `ALTER … resultados_sin_id_estudiante` de la sección 2.
- En la cabecera, sección «ESTADO ACTUAL Y MIGRACIONES», añadir: «Incluye también la migración 2026-10-07c (alertas sin casos y sin porcentaje por grado)».

- [ ] **Step 4: Correr y commit**

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q`
Expected: todo pasa.

```bash
git add supabase/migraciones/2026-10-07c-alertas-sin-casos.sql supabase/estudiantes_schema.sql tests/test_alertas_publicar.py
git commit -m "feat(supabase): la base rechaza alertas con casos o con porcentaje por grado" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Leer las alertas publicadas

**Files:**
- Modify: `src/estudiantes/lectura.py`
- Modify: `tests/test_alertas_publicar.py`

- [ ] **Step 1: Pruebas que fallan**

```python
# ══ Lectura ═════════════════════════════════════════════════════════════════
def test_las_alertas_se_leen_igual_que_se_publicaron(analisis):
    filas = _filas(analisis)
    random.Random(5).shuffle(filas)                 # Supabase no garantiza orden
    leido = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    pd.testing.assert_frame_equal(leido.alertas, analisis.alertas, check_dtype=False)
    pd.testing.assert_frame_equal(leido.alertas_sensibilidad,
                                  analisis.alertas_sensibilidad, check_dtype=False)
    pd.testing.assert_frame_equal(leido.alertas_items, analisis.alertas_items,
                                  check_dtype=False)


def test_una_corrida_anterior_sin_alertas_se_sigue_leyendo(analisis):
    filas = [f for f in _filas(analisis) if not f["tipo"].startswith("alerta")]
    viejo = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert viejo.alertas.empty and list(viejo.alertas.columns) == al.COLUMNAS_TABLA
    assert viejo.alertas_sensibilidad.empty and viejo.alertas_items.empty
```

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py -q -k "leen or anterior"`
Expected: FAIL (las tablas leídas están vacías).

- [ ] **Step 2: Implementar**

En `src/estudiantes/lectura.py`:

1. Docstring, «QUÉ RECONSTRUYE»: añadir «y las alertas de grupo (vacías en una corrida anterior a la fase 3; la vista vuelve entonces a la tarjeta de siempre)».
2. En `_reconstruir`, antes de `return a`:

```python
    a.alertas, a.alertas_sensibilidad, a.alertas_items = _tablas_alertas(nivel, filas)
```

3. Después de `_tabla_items`:

```python
def _tablas_alertas(nivel: str, filas: list[dict]):
    """(alertas por grupo, sensibilidad, distribución de ítems) desde las filas «alerta…»."""
    from src.estudiantes import alertas as al
    grupos, sens, items = [], [], []
    for f in filas:
        tipo = f["tipo"]
        visible = bool(_det(f, "visible", False)) and f.get("valor") is not None
        if tipo in ("alerta", "alerta_grupo"):
            total = tipo == "alerta"
            grupos.append(dict(
                alerta=f["clave"], agrupacion=al.TOTAL if total else f["agrupacion"],
                grupo=al.TODOS if total else str(f["grupo"]), n=int(f["n"]),
                pct=f["valor"] if visible else None,
                ic_inf=f["ic_inf"] if visible else None,
                ic_sup=f["ic_sup"] if visible else None,
                visible=visible, prioridad=bool(_det(f, "prioridad", False))))
        elif tipo == "alerta_sensibilidad":
            sens.append((_det(f, "orden", 0), dict(
                alerta=_det(f, "alerta"), variante=f["clave"], etiqueta=_det(f, "etiqueta"),
                vigente=bool(_det(f, "vigente", False)), n=int(f["n"]),
                pct=f["valor"] if visible else None,
                ic_inf=f["ic_inf"] if visible else None,
                ic_sup=f["ic_sup"] if visible else None, visible=visible)))
        elif tipo == "alerta_item":
            pcts = _det(f, "pct") or []
            for respuesta, pct in zip(_det(f, "respuestas") or [], pcts):
                items.append((_det(f, "orden", 0), dict(
                    alerta=_det(f, "alerta"), item=f["clave"],
                    enunciado=_det(f, "enunciado"), respuesta=respuesta,
                    n=int(f["n"]), pct=pct)))
    tabla = al.ordenar(_df(grupos, al.COLUMNAS_TABLA), nivel)
    sens = _df([d for _, d in sorted(sens, key=lambda x: x[0])], al.COLUMNAS_SENSIBILIDAD)
    items = _df([d for _, d in sorted(items, key=lambda x: x[0])], al.COLUMNAS_ITEMS)
    return tabla, sens, items
```

El `sorted` es estable: las respuestas de un mismo ítem conservan su orden.

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_publicar.py tests/test_estudiantes_lectura.py tests/test_estudiantes_subgrupos.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/estudiantes/lectura.py tests/test_alertas_publicar.py
git commit -m "feat(lectura): las alertas publicadas se leen; una corrida vieja sigue igual" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Panel de alertas (funciones puras y HTML)

**Files:**
- Create: `src/ui/views/estudiantes_alertas.py`
- Create: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

`tests/test_alertas_vista.py`:

```python
"""Panel «Señales para actuar a tiempo» en la vista, los informes y el PDF (spec §5.4, §6)."""
import colorsys
import dataclasses
import inspect
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.core.colegios import COLEGIOS
from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.ui.views import estudiantes_alertas as va


def _r(alerta, agrupacion, grupo, pct=None, visible=False, prioridad=False, n=60):
    return dict(alerta=alerta, agrupacion=agrupacion, grupo=grupo, n=n, pct=pct,
                ic_inf=None if pct is None else pct - 5,
                ic_sup=None if pct is None else pct + 5,
                visible=visible, prioridad=prioridad)


TABLA = [
    _r("malestar", "total", "Todos", 16.7, True, n=900),
    _r("malestar", "Colegio", "LauV", 25.0, True, True, n=400),
    _r("malestar", "Colegio", "JJC"),
    _r("malestar", "Grado", "Octavo", prioridad=True, n=150),
    _r("malestar", "Grado", "Sexto", n=150),
    _r("malestar", "Colegio×Grado", "LauV|Octavo", prioridad=True, n=90),
    _r("malestar", "Colegio×Grado", "LauV|Sexto", prioridad=True, n=95),
    _r("desesperanza", "total", "Todos", 17.0, True, n=900),
    _r("desesperanza", "Colegio", "LauV", 20.0, True, n=400),
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
    assert m.estado == va.PRESENTE and m.visible
    assert m.frase == "1 de cada 6 estudiantes muestra señales de malestar."
    assert m.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)),)


def test_dentro_de_un_colegio_los_grados_van_en_orden_canonico():
    s = va.senales(_ns(), "colegio", {"colegio": "LauV"})[0]
    assert s.estado == va.PRIORIDAD
    assert s.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Sexto", "Octavo")),)


def test_el_municipio_ve_colegios_y_grados_en_prioridad():
    s = va.senales(_ns(), "municipio", {})[0]
    assert s.listas == ((ac.TITULO_COLEGIOS_PRIORIDAD, ("Laura Vicuña",)),
                        (ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)))


def test_un_colegio_sin_cifra_lo_dice_con_el_texto_fijo():
    s = va.senales(_ns(), "colegio", {"colegio": "JJC"})[0]
    assert not s.visible and s.frase == ac.CIFRAS_PEQUENAS and s.estado == va.PRESENTE


def test_por_grado_solo_el_estado_con_la_cifra_de_referencia():
    s = va.senales(_ns(), "familia", {"grado": "Octavo"})[0]
    assert s.estado == va.PRIORIDAD and s.frase == ac.SOLO_ESTADO and s.pct is None
    assert s.referencia == "En el municipio: 1 de cada 6 estudiantes muestra señales de malestar."
    c = va.senales(_ns(), "colegio", {"colegio": "LauV", "grado": "Octavo"})[0]
    assert c.referencia.startswith("En el colegio: 1 de cada 4")


def test_un_grupo_sin_fila_no_oculta_el_panel():
    s = va.senales(_ns(), "colegio", {"grado": "Noveno"})
    assert s and s[0].frase == ac.CIFRAS_PEQUENAS


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
    filas = [_r("malestar", "total", "Todos", 16.7, True, n=900)]
    filas += [_r("malestar", "Colegio", c, 30.0, True, True) for _, c, _ in COLEGIOS]
    html = va.panel_html(_ns(filas), "municipio", {}, compacto=True)
    assert f"y {len(COLEGIOS) - va.MAX_NOMBRES_PAGINA} más" in html


def test_tabla_de_la_secretaria_sin_conteos():
    html = va.tabla_secretaria_html(_ns())
    assert "Laura Vicuña" in html and "José Joaquín Casas" in html
    assert ac.CIFRAS_PEQUENAS_CORTO in html and "Total del municipio" in html
    assert "casos" not in html.lower()


def _hls(color):
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def test_el_color_maximo_es_naranja_nunca_rojo():
    tono, _, saturacion = _hls(va.COLOR_PRIORIDAD)
    assert 25 <= tono * 360 <= 45 and saturacion > 0.5
    assert _hls(va.COLOR_PRESENTE)[2] < 0.2          # gris sereno
    for css in (va.CSS_INFORME, va.CSS_PAGINA):
        assert "#C0392B" not in css.upper() and va.COLOR_PRIORIDAD in css
```

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
  · Nunca un conteo de casos. Porcentaje, «1 de cada N» y margen de error solo
    si la fila viene marcada como visible; por grado, solo el estado.
  · El panel nunca se oculta: sin cifra, lo dice con el texto fijo y la ruta
    sigue a la vista.
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
PRIORIDAD = "prioridad"
PRESENTE = "presente"

# Gris sereno y naranja. Nunca rojo (#C0392B es el de las bandas y la ruta).
COLOR_PRESENTE = "#5B6776"
FONDO_PRESENTE = "#F2F4F7"
COLOR_PRIORIDAD = "#B86E00"
FONDO_PRIORIDAD = "#FFF3E0"
MAX_NOMBRES_PAGINA = 6


@dataclass(frozen=True)
class Senal:
    alerta: str
    nombre: str
    estado: str
    visible: bool
    frase: str
    que_hacer: str
    pct: float | None = None
    ic_inf: float | None = None
    ic_sup: float | None = None
    n: int | None = None
    referencia: str = ""
    listas: tuple = ()

    @property
    def etiqueta_estado(self) -> str:
        return ac.ESTADOS[self.estado]


# ══ Datos ═══════════════════════════════════════════════════════════════════
def tabla(analisis) -> pd.DataFrame:
    t = getattr(analisis, "alertas", None)
    if isinstance(t, pd.DataFrame) and len(t):
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


def _visible(f) -> bool:
    return (bool(f) and bool(f.get("visible")) and f.get("pct") is not None
            and not pd.isna(f.get("pct")))


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
    t = t[(t["alerta"] == alerta) & t["prioridad"].astype(bool)]
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
    filtros = filtros or {}
    agrupacion, _ = clave_grupo(filtros)
    salida: list[Senal] = []
    for alerta in alertas_para_rol(analisis, rol):
        definicion = ac.ALERTAS[alerta]
        f = fila(analisis, alerta, filtros)
        ver = _visible(f)
        if ver:
            texto = frase(alerta, float(f["pct"]))
        elif f is not None and agrupacion in al.SOLO_ESTADO:
            texto = ac.SOLO_ESTADO
        else:
            texto = ac.CIFRAS_PEQUENAS
        referencia = ""
        if not ver and f is not None and agrupacion in al.SOLO_ESTADO:
            ref = fila(analisis, alerta,
                       {"colegio": filtros.get("colegio")} if agrupacion == CRUCE else {})
            if _visible(ref):
                donde = "En el colegio" if agrupacion == CRUCE else "En el municipio"
                referencia = f"{donde}: {frase(alerta, float(ref['pct']))}"
        salida.append(Senal(
            alerta=alerta, nombre=definicion.nombre,
            estado=PRIORIDAD if f is not None and bool(f.get("prioridad")) else PRESENTE,
            visible=ver, frase=texto, que_hacer=definicion.que_hacer.get(rol, ""),
            pct=float(f["pct"]) if ver else None,
            ic_inf=float(f["ic_inf"]) if ver else None,
            ic_sup=float(f["ic_sup"]) if ver else None,
            n=int(f["n"]) if ver else None, referencia=referencia,
            listas=tuple((titulo, tuple(nombres)) for titulo, nombres
                         in listas_prioridad(analisis, alerta, rol, filtros))))
    return salida


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
        referencia = f' <span class="lista">{_e(s.referencia)}</span>' if s.referencia else ""
        listas = "".join(f' <span class="lista">{_e(t)} {_e(_unir(ns, tope))}</span>'
                         for t, ns in s.listas)
        if compacto:
            bloques.append(f'<p class="senal senal-{s.estado}">{estado} <b>{_e(s.nombre)}.</b> '
                           f'{_e(s.frase)}{referencia}{listas}</p>')
            continue
        margen = (f'<p class="margen">Margen de error {s.ic_inf:.0f}–{s.ic_sup:.0f} % · base '
                  f'de {s.n} estudiantes</p>' if s.visible else "")
        hacer = (f'<p class="accion"><b>Qué hacer.</b> {_e(s.que_hacer)}</p>'
                 if s.que_hacer else "")
        bloques.append(f'<div class="senal senal-{s.estado}"><p>{estado} <b>{_e(s.nombre)}</b></p>'
                       f'<p>{_e(s.frase)}{referencia}</p>'
                       + (f"<p>{listas.strip()}</p>" if listas else "") + margen + hacer
                       + "</div>")
    notas = [ac.NO_ES_DIAGNOSTICO, ac.NOTA_AZAR]
    if not compacto and getattr(analisis, "nivel", None) == cat.NIVEL_PRIMARIA:
        notas.append(cat.AVISO_PRIMARIA)
    return (f'<section class="senales"><h2>{_e(ac.TITULO_PANEL)}</h2>' + "".join(bloques)
            + f'<p class="nota-senal">{_e(" ".join(notas))}</p></section>')


def _celda_html(f) -> str:
    if not _visible(f):
        return (f'<td class="senal-presente"><span class="estado">{_e(ac.ESTADOS[PRESENTE])}'
                f'</span><small>{_e(ac.CIFRAS_PEQUENAS_CORTO)}</small></td>')
    estado = PRIORIDAD if f.get("prioridad") else PRESENTE
    return (f'<td class="senal-{estado}"><span class="estado">{_e(ac.ESTADOS[estado])}</span> '
            f'{float(f["pct"]):.0f} %<small>{float(f["ic_inf"]):.0f}–'
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
    ".senales .estado{display:inline-block;padding:1px 9px;border-radius:10px;font-size:12px;"
    "font-weight:700;background:#fff;color:" + COLOR_PRESENTE + ";margin-right:6px}"
    ".senal-prioridad .estado{color:" + COLOR_PRIORIDAD + "}"
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
    ".senal .lista{color:#5b6776}"
    ".nota-senal{font-size:7pt;color:#5b6776;margin:2px 0 0}"
)


# ══ Streamlit ═══════════════════════════════════════════════════════════════
def _chip_html(s: Senal) -> str:
    color, fondo = ((COLOR_PRIORIDAD, FONDO_PRIORIDAD) if s.estado == PRIORIDAD
                    else (COLOR_PRESENTE, FONDO_PRESENTE))
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
            if s.referencia:
                st.caption(s.referencia)
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
            st.caption(ac.QUE_ES_PRIORIDAD)
            st.caption(ac.QUE_ES_PRESENTE)
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

### Task 11: Vista comunidad

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


def test_el_panel_va_arriba_de_las_tarjetas():
    fuente = inspect.getsource(vc.render_comunidad)
    assert fuente.index("_panel_alertas(") < fuente.index("tarjetas(a, rol, filtros)")
    assert "indicadores_comparables(a, rol)" in fuente
    assert "ruta_para_rol(rol)" in fuente and "aviso_ruta_pendiente()" in fuente
```

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py -q -k "muerte or comparar or ruta or panel_va"`
Expected: FAIL con `AttributeError: ... 'panel_reemplaza_muerte'`.

- [ ] **Step 2: Implementar**

En `src/ui/views/estudiantes_comunidad.py`:

1. Docstring:
   - Añadir: «· El panel de alertas (estudiantes_alertas) va arriba de las tarjetas y, para colegio y municipio, reemplaza la tarjeta de muerte».
   - Cambiar «RUTA_ATENCION» por «la ruta por rol (alertas_catalogo.ruta)».

2. Después de `ve_colegios`:

```python
def _alertas_vista():
    """Módulo del panel de alertas, o None.

    Si faltara (un despliegue a medias), la página sigue como antes de la fase 3.
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
    return bool(va and va.hay_alerta(analisis, "desesperanza"))


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
    va = _alertas_vista()
    if va is not None:
        va.render_panel(a, rol, filtros)
```

3. En `tarjetas`, después de `if not accion: continue`:

```python
        if clave == "ideacion" and panel_reemplaza_muerte(analisis, rol):
            continue
```

4. En `render_comunidad`:
   - Después del bloque «1. bandas» (tras el `else: st.info(...)` de la línea ~994), insertar:

     ```python
         # ── 1b. señales para actuar a tiempo (alertas de grupo, spec §5.4)
         _panel_alertas(a, rol, filtros)
     ```

   - En «3. comparación», sustituir las cuatro líneas `opciones = [k for k in INDICADORES if prevalencia(a, k, {})]` … `opciones = ["sdq_alto"]` por:

     ```python
             opciones = indicadores_comparables(a, rol)
     ```

   - En «5. ruta de atención», sustituir el bucle por:

     ```python
             for nombre, detalle in ruta_para_rol(rol):
                 st.markdown(f"- **{nombre}** — {detalle}")
             aviso = aviso_ruta_pendiente()
             if aviso:
                 st.caption(f"⚠️ {aviso}")
     ```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_comunidad.py tests/test_estudiantes_subgrupos.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_comunidad.py tests/test_alertas_vista.py
git commit -m "feat(comunidad): panel de alertas arriba de las tarjetas y ruta por rol" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Informes del colegio y de la Secretaría

**Files:**
- Modify: `src/ui/views/estudiantes_informe.py`
- Modify: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

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


def _sin_conteos(html, a):
    """Ningún «k de n» ni «k estudiantes con señal» de las alertas reales del fixture."""
    d = a.datos.loc[a.base.nivel]
    for col in ("ALERTA_malestar", "ALERTA_desesperanza"):
        k, n = int(d[col].sum()), int(d[col].notna().sum())
        assert f"{k} de {n}" not in html and f"{k} estudiantes" not in html


def test_el_informe_del_colegio_trae_el_panel(fuente, analisis):
    html = inf.informe_colegio_html(fuente, COLEGIO, fecha=date(2026, 10, 8))
    assert ac.TITULO_PANEL in html and ac.NO_ES_DIAGNOSTICO in html
    assert html.index(ac.TITULO_PANEL) < html.index("Resultados y qué hacer")
    assert "casos" not in _seccion(html).lower()
    assert "Piensa en la muerte con frecuencia" not in html     # el panel la reemplaza
    assert ac.RUTA_PENDIENTE not in html
    _sin_conteos(html, analisis)


def test_la_secretaria_trae_la_tabla_por_colegio_sin_conteos(fuente, analisis):
    html = inf.informe_secretaria_html(fuente, fecha=date(2026, 10, 8))
    assert '<table class="senales-tabla">' in html and "Laura Vicuña" in html
    assert "Piensa en la muerte con frecuencia" not in html
    assert ac.RUTA_PENDIENTE not in html
    _sin_conteos(html, analisis)


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
```

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py -q -k "informe or secretaria or tabla_de_alertas or sin_alertas_los"`
Expected: FAIL (no hay panel en el HTML).

- [ ] **Step 2: Implementar**

En `src/ui/views/estudiantes_informe.py`:

1. Docstring:
   - Cambiar «RUTA_ATENCION» por «la ruta por rol».
   - Añadir «· Panel de alertas (estudiantes_alertas): en el informe del colegio, tabla por colegio en el de la Secretaría y recuadro compacto en el resumen de una página. Con alertas, la columna de muerte sale de las tablas».

2. Después de `_nivel_valido`:

```python
def _va():
    """Módulo del panel de alertas, o None (despliegue con módulos a medias)."""
    try:
        from src.ui.views import estudiantes_alertas as va
        return va
    except Exception:                                      # noqa: BLE001
        return None


def _sin_muerte(a, columnas) -> list[str]:
    """Sin la columna de muerte si el panel de alertas la reemplaza (spec §5.4)."""
    va = _va()
    if va is not None and va.hay_alerta(a, "desesperanza"):
        return [k for k in columnas if k != "ideacion"]
    return list(columnas)


def _panel(a, rol: str, filtros: dict, compacto: bool = False) -> str:
    va = _va()
    return va.panel_html(a, rol, filtros, compacto=compacto) if va is not None else ""


def _css_senales(tipo: str) -> str:
    va = _va()
    if va is None:
        return ""
    return va.CSS_PAGINA if tipo == "pagina" else va.CSS_INFORME
```

3. `_bloque_ruta`:

```python
def _bloque_ruta(rol: str = "colegio") -> str:
    filas = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in vc.ruta_para_rol(rol))
    return f'<section class="ruta"><h2>Si un estudiante necesita ayuda</h2><ul>{filas}</ul></section>'
```

4. `_documento(titulo, cuerpo, css_extra: str = "")`: usar `<style>{_CSS}{css_extra}</style>`.

5. `informe_colegio_html`:
   - `grados = _tabla_comparativa(a, "Grado", _sin_muerte(a, COLUMNAS_GRADO_COLEGIO), filtros, …)`.
   - En `secciones.append(...)`, después de `_bloque_bandas([...])` y antes de `'<h2>Resultados y qué hacer</h2>'`, insertar `+ _panel(a, "colegio", filtros)`.
   - `_bloque_ruta()` → `_bloque_ruta("colegio")`.
   - `return _documento(f"Informe Estudiantes 360 · {nombre}", cuerpo, _css_senales("informe"))`.

6. `informe_secretaria_html`:
   - Después del `"</div>"` de las tarjetas, insertar `+ _senales_secretaria(a)`.
   - Las dos llamadas a `_tabla_comparativa` usan `_sin_muerte(a, list(COLUMNAS_TABLA))`.
   - `_bloque_ruta("municipio")`.
   - `_documento("Informe Estudiantes 360 · Secretaría", cuerpo, _css_senales("informe"))`.

   Con:

```python
def _senales_secretaria(a) -> str:
    va = _va()
    return va.tabla_secretaria_html(a) if va is not None else ""
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_informe.py -q`
Expected: todo pasa (las pruebas de PDF se saltan sin WeasyPrint).

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_informe.py tests/test_alertas_vista.py
git commit -m "feat(informes): panel de alertas para el colegio y tabla para la Secretaría" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Recuadro en el resumen de una página y el peor caso

La prueba existente (`tests/test_estudiantes_informe.py::test_el_resumen_cabe_en_una_pagina_de_pdf`) mide con `HTML(string=…).render()` y `len(doc.pages) == 1`. Aquí se hace lo mismo con el peor caso: rol municipio, todos los colegios y grados en «Prioridad», y los dos niveles.

**Files:**
- Modify: `src/ui/views/estudiantes_informe.py`
- Modify: `tests/test_alertas_vista.py`

- [ ] **Step 1: Pruebas que fallan**

```python
# ══ Resumen de una página ═══════════════════════════════════════════════════
def _f(colegio="Todos", grado="Todos"):
    return {"nivel": cat.NIVEL_SECUNDARIA, "colegio": colegio, "grado": grado}


def test_el_recuadro_va_antes_de_las_tarjetas(analisis):
    html = inf.informe_una_pagina_html(analisis, "colegio", _f(colegio=COLEGIO))
    assert html.index(ac.TITULO_PANEL) < html.index("Lo más importante y qué hacer")
    assert ac.RUTA_PENDIENTE not in html
    _sin_conteos(html, analisis)


def test_el_resumen_de_familia_no_trae_desesperanza(analisis):
    html = inf.informe_una_pagina_html(analisis, "familia", _f())
    assert ac.ALERTAS["malestar"].nombre in html
    assert ac.ALERTAS["desesperanza"].nombre not in html


def test_un_grupo_pequeno_tambien_lleva_el_recuadro(analisis):
    html = inf.informe_una_pagina_html(analisis, "colegio", _f(grado="Noveno"))
    assert ac.CIFRAS_PEQUENAS in html


def _peor_caso(a, nivel):
    grados = cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.ORDEN_GRADOS_PRI
    filas = []
    for k, x in ac.ALERTAS.items():
        if nivel not in x.niveles:
            continue
        filas.append(_r(k, "total", "Todos", 17.0, True, n=900))
        filas += [_r(k, "Colegio", c, 40.0, True, True) for _, c, _ in COLEGIOS]
        filas += [_r(k, "Grado", g, prioridad=True, n=150) for g in grados]
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

```python
    caja = _panel(analisis, rol, filtros, compacto=True)
    if b or fichas:
        ...                                   # igual hasta `bandas`
        contenido = (bandas + caja + '<h2>Lo más importante y qué hacer</h2><div class="tiles">'
                     + "".join(_tile_pagina(analisis, t, filtros, con_municipio)
                               for t in fichas) + "</div>")
    elif con_municipio and not vc.hay_datos_crudos(analisis):
        contenido = caja + f"<p>{_e(vc.SIN_SUBGRUPO_PUBLICADO)}</p>"
    else:
        contenido = caja + (f"<p>Este grupo tiene menos de {cat.MIN_GROUP_N} estudiantes, así "
                            "que no se muestran sus resultados: con grupos tan pequeños se podría "
                            "reconocer a un estudiante. Sus respuestas sí cuentan en los "
                            "totales.</p>")

    ruta = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in vc.ruta_para_rol(rol))
```

En el `return`, cambiar `f"<style>{_CSS_PAGINA}</style></head>"` por `f"<style>{_CSS_PAGINA}{_css_senales('pagina')}</style></head>"`.

- [ ] **Step 3: Correr, también con WeasyPrint**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_informe.py -q`
Expected: todo pasa.

El `.venv` local no trae WeasyPrint, así que el PDF se prueba con el entorno de producción de la fase 2. Si no existe, se crea como en la Task 17, Step 1.

Run: `"$TMPDIR/venv314/bin/python" -m pytest tests/test_alertas_vista.py tests/test_estudiantes_informe.py -q -k "pagina"`
Expected: las pruebas de una página **pasan**, no se saltan.

Si el peor caso da 2 páginas, compactar en este orden:
1. `CSS_PAGINA`: bajar `.senal` a `font-size:8pt` y `.senales` a `padding:4px 8px`.
2. `MAX_NOMBRES_PAGINA = 4` (y ajustar la prueba que lo usa).

Nunca se quitan la ruta, los avisos ni la nota «no es un diagnóstico».

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_informe.py src/ui/views/estudiantes_alertas.py tests/test_alertas_vista.py
git commit -m "feat(pdf): recuadro compacto de alertas antes de las tarjetas, cabe en una página" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Vista de investigadores

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
    import io
    t = pd.read_csv(io.StringIO(vi.archivos_paquete({cat.NIVEL_SECUNDARIA: analisis})["alertas.csv"]))
    assert {"nivel", "alerta", "agrupacion", "grupo", "n", "pct", "estado"} <= set(t.columns)
    assert "casos" not in t.columns and (t["n"] >= cat.MIN_GROUP_N).all()
    assert t[t["agrupacion"].isin(al.SOLO_ESTADO)]["pct"].isna().all()


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
    fuente = inspect.getsource(vi.render_investigador)
    assert '"Alertas"' in fuente and "_tab_alertas(a)" in fuente
```

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_investigador.py -q`
Expected: FAIL.

- [ ] **Step 2: Implementar**

En `src/ui/views/estudiantes_investigador.py`:

1. `ARCHIVOS_PAQUETE`: añadir `"alertas.csv"` después de `"modelos.csv"`.

2. Después de `icc_tabla`:

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


def alertas_tabla(analisis) -> pd.DataFrame:
    """Alertas por grupo para `alertas.csv`: estado y %, nunca casos (spec §5.4)."""
    from src.estudiantes import alertas as al
    from src.estudiantes import alertas_catalogo as ac
    t = _tabla_de(analisis, "alertas", al.COLUMNAS_TABLA)
    if t.empty:
        return pd.DataFrame(columns=["nivel", "alerta", "nombre", "agrupacion", "grupo", "n",
                                     "pct", "ic_inf", "ic_sup", "estado", "cifra"])
    t["nombre"] = [ac.ALERTAS[k].nombre if k in ac.ALERTAS else k for k in t["alerta"]]
    t["estado"] = [ac.ESTADOS["prioridad"] if p else ac.ESTADOS["presente"]
                   for p in t["prioridad"].astype(bool)]
    t["cifra"] = ["porcentaje" if v else ("solo estado" if g in al.SOLO_ESTADO
                                          else "muy pequeña")
                  for v, g in zip(t["visible"].astype(bool), t["agrupacion"])]
    return t[["nivel", "alerta", "nombre", "agrupacion", "grupo", "n", "pct", "ic_inf",
              "ic_sup", "estado", "cifra"]]


def sensibilidad_tabla(analisis) -> pd.DataFrame:
    from src.estudiantes import alertas as al
    return _tabla_de(analisis, "alertas_sensibilidad", al.COLUMNAS_SENSIBILIDAD)


def items_alertas_tabla(analisis) -> pd.DataFrame:
    from src.estudiantes import alertas as al
    return _tabla_de(analisis, "alertas_items", al.COLUMNAS_ITEMS)


def _metodologia_alertas() -> list[str]:
    from src.estudiantes import alertas_catalogo as ac
    lineas = ["## Alertas de grupo («Señales para actuar a tiempo»)", ""]
    for alerta in ac.ALERTAS.values():
        lineas.append(f"- **{alerta.nombre}** ({' y '.join(alerta.niveles)}): {alerta.regla}"
                      + (f" Límite: {alerta.limite}" if alerta.limite else ""))
    lineas += ["", f"- {ac.REGLA_CIFRAS} Por grado solo se publica el estado.",
               "- «Prioridad»: el límite inferior del IC de Wilson del grupo queda por encima "
               "del límite superior del resto del municipio (el nivel sin el grupo). "
               + ac.NOTA_AZAR,
               "- Nunca se publica ni se exporta el número de casos de una alerta.",
               "- Sensibilidad: 2, 3 y 4 ítems para el malestar y regla estricta frente a "
               "amplia para la desesperanza, sobre las mismas filas.",
               "- Textos y umbrales provisionales hasta la aprobación del equipo.", ""]
    return lineas
```

3. En `metodologia_md`, justo antes de `lineas += ["## 6. Análisis estadístico", …`, añadir `lineas += _metodologia_alertas()`.

4. En `archivos_paquete`, después de `"modelos.csv"`: `"alertas.csv": _csv(alertas_tabla(analisis)),`.

5. En `_tab_exportar`, en `descripciones`: `"alertas.csv": "Alertas por grupo: estado y porcentaje con IC, sin casos.",`.

6. Pestaña nueva (antes de `_tab_modelos`):

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
    st.caption(ac.REGLA_CIFRAS + " Por grado solo se publica el estado.")
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
    st.subheader("Distribución de cada ítem · nivel publicado")
    it = items_alertas_tabla(a)
    if not it.empty:
        st.dataframe(it.drop(columns=["nivel"]), hide_index=True, width="stretch")
        st.caption("Un ítem sin cifras tiene alguna respuesta con menos de 3 estudiantes o con "
                   "todos menos 2.")
    st.divider()
    st.subheader("Sensibilidad · umbrales y reglas")
    s = sensibilidad_tabla(a)
    if not s.empty:
        st.dataframe(s.drop(columns=["nivel"]), hide_index=True, width="stretch")
        st.caption("Mismas filas para todas las variantes. Una variante sin cifra difiere de "
                   "la vigente en 1 o 2 estudiantes, o le faltan respuestas.")
```

7. En `render_investigador`:

```python
    tabs = st.tabs(["Muestra y exclusiones", "Tabla 1 · descriptivos", "Cortes y bandas",
                    "Correlaciones", "Por grupo", "Alertas", "Modelos", "Calidad de datos",
                    "Exportar"])
```

Reindexar: `tabs[5]` → `_tab_alertas(a)`, `tabs[6]` → modelos, `tabs[7]` → calidad, `tabs[8]` → exportar. La prevalencia del ítem 18 sigue en «Cortes y bandas», sin cambios.

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_vista.py tests/test_estudiantes_investigador.py tests/test_estudiantes_lectura.py -q`
Expected: todo pasa.

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/estudiantes_investigador.py tests/test_estudiantes_investigador.py tests/test_alertas_vista.py
git commit -m "feat(investigador): pestaña de alertas, sensibilidad y alertas.csv en el ZIP" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: Datos reales (se omite si faltan los archivos)

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
from src.estudiantes import ingest, pipeline, publicar, scoring


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
        assert al.auditar_cifras(a.datos, a.base, a.alertas) == [], nivel


def test_el_municipio_siempre_muestra_su_cifra(analisis):
    for nivel, a in analisis.items():
        total = a.alertas[a.alertas["agrupacion"] == al.TOTAL]
        assert set(total["alerta"]) == set(al.claves_del_nivel(a.datos, nivel)), nivel
        assert total["visible"].all(), nivel


def test_ninguna_fila_de_alerta_publicada_trae_casos(analisis):
    filas = publicar.aplanar(analisis)
    publicar.verificar(filas)
    assert not [f for f in filas if f["tipo"].startswith("alerta") and "casos" in f["detalle"]]
```

- [ ] **Step 2: Correr**

Run: `.venv/bin/python -m pytest tests/test_alertas_reales.py -q`
Expected:
- Con los archivos: todo pasa.
- Sin ellos: todo se salta.

Si falla una calibración: **no** se ensancha la tolerancia. Se revisa la definición contra la spec, la regla de faltantes y que la columna sea la del texto crudo, y se informa al usuario con el porcentaje obtenido.

Si falla la prueba del asterisco, se informa qué ítems trae marcados cada formulario. Decide el equipo (spec §8.3).

- [ ] **Step 3: Diagnóstico para el equipo (sin casos)**

```bash
.venv/bin/python - <<'EOF'
from src.estudiantes import pipeline
analisis, _ = pipeline.cargar_y_analizar(n_boot=20)
for nivel, a in analisis.items():
    for alerta, g in a.alertas.groupby("alerta"):
        col = g[g["agrupacion"] == "Colegio"]
        print(nivel, alerta, f"colegios con porcentaje: {int(col['visible'].sum())} de {len(col)}",
              f"· grupos en Prioridad: {int(g['prioridad'].sum())}")
EOF
```

Guardar la salida para el PR. Son conteos de **grupos**, no de estudiantes.

- [ ] **Step 4: Comparar el lote real antes y después**

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_despues.json" || true
.venv/bin/python - <<'EOF'
import json, os, sys
sys.path.insert(0, ".")
from tests.test_alertas_regresion import normalizar
t = os.environ["TMPDIR"]
antes = json.load(open(f"{t}/obs360_lote_antes.json", encoding="utf-8"))["filas"]
despues = json.load(open(f"{t}/obs360_lote_despues.json", encoding="utf-8"))["filas"]
a, d = (json.dumps(normalizar(x), sort_keys=True, ensure_ascii=False) for x in (antes, despues))
print("idéntico" if a == d else "DIFERENTE")
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

### Task 16: Documentación

**Files:**
- Modify: `docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md` (sección nueva al final)
- Modify: `supabase/README.md` (lista de migraciones)
- Modify: `DESPLIEGUE.md` (pasos antes de publicar alertas)

- [ ] **Step 1: Editar**

**`INSTRUMENTO_ESTUDIANTES.md`**: sección «Alertas de grupo («Señales para actuar a tiempo»)» con:
- las dos reglas (copiadas de `alertas_catalogo.ALERTAS[*].regla`);
- la regla de faltantes;
- «3 ≤ casos ≤ n − 3», con el resto del nivel;
- por qué los grados solo llevan estado;
- «Prioridad» contra el resto del municipio;
- sensibilidad;
- textos provisionales.

**`supabase/README.md`**: añadir `2026-10-07c-alertas-sin-casos.sql`, qué hace y que es opcional para publicar pero recomendada.

**`DESPLIEGUE.md`**, sección «Publicar alertas»:
1. El equipo aprueba textos, umbrales y rutas: `alertas_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS`.
2. Correr la migración `2026-10-07c`.
3. `python -m src.estudiantes.publicar --ensayo` y revisar.
4. Publicar con `--publicar-ya`.
5. «Reboot app».

Mientras no se publique una corrida nueva, el despliegue sigue con la tarjeta de muerte y sin panel.

- [ ] **Step 2: Commit**

```bash
git add docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md supabase/README.md DESPLIEGUE.md
git commit -m "docs(alertas): definiciones, migración y pasos para publicarlas" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: Probar con las versiones de producción

**Files:** ninguno, salvo que aparezcan fallos.

- [ ] **Step 1: Entorno con Python 3.14 y WeasyPrint**

Si ya existe el de la fase 2, solo actualizarlo:

```bash
[ -x "$TMPDIR/venv314/bin/python" ] || /opt/homebrew/bin/python3.14 -m venv "$TMPDIR/venv314"
"$TMPDIR/venv314/bin/pip" install -q -r requirements.txt pytest pyarrow
"$TMPDIR/venv314/bin/python" -c "import streamlit, weasyprint, sys; print(sys.version, streamlit.__version__, weasyprint.__version__)"
```

Si WeasyPrint no encuentra pango: `brew install pango`.

- [ ] **Step 2: Correr la suite**

Run: `"$TMPDIR/venv314/bin/python" -m pytest -q`
Expected: lo mismo que en 3.13, **y** las pruebas de PDF pasan en lugar de saltarse.

- Si hay un error real: corregirlo con prueba y commit propio.
- Si es del entorno: anotarlo en el PR.

- [ ] **Step 3: Commit (solo si hubo correcciones)**

---

### Task 18: Verificación con Playwright (local)

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
| completo, colegio LauV | El estado y la lista «Grados en «Prioridad»» en orden canónico, si los hay. Al desplegar «Qué quiere decir cada estado» aparecen el margen de error y la base, nunca un conteo de casos |
| completo, colegio + grado | Texto «Por grado se muestra el estado…» y «En el colegio: …» |
| completo, colegio pequeño o grado sin fila | «En este grupo las cifras son muy pequeñas…» y la ruta |
| completo, rol municipio | Listas de colegios y grados en «Prioridad»; sin tarjeta de muerte; el selector «Comparar» no ofrece «piensa en la muerte» |
| completo, rol familia | Solo «Señales de malestar»; nada de muerte ni desesperanza ni listas de colegios; «piensa en la muerte» no está en «Comparar» |
| completo | Bajo la ruta, el aviso interno «ruta pendiente de validación» |
| completo, primaria | Solo malestar y el aviso de validez de edad |
| completo, PDF | Descargar el resumen de una página (colegio y municipio): una sola página, con el recuadro antes de las tarjetas. El informe del colegio y el de la Secretaría muestran el panel o la tabla, sin casos |
| investigador (8602) | Pestaña «Alertas» con definiciones, prevalencias por grupo, ítems y sensibilidad. El ZIP trae `alertas.csv` |
| comunidad (8603, corrida publicada sin alertas) | Sin panel; la tarjeta de muerte sigue como antes; sin errores; sin aviso interno de ruta |
| comunidad | A 390 px de ancho, el panel sin desborde horizontal |
| todos | Sin excepciones en pantalla |

- [ ] **Step 3: Apagar los servidores y borrar `.playwright-mcp/` si se creó**

---

### Task 19: PR (sin fusionar)

- [ ] **Step 1:** `git push -u origin feature/fase3-alertas`

- [ ] **Step 2:** `gh pr create`. Base: `main` si la fase 2 ya se fusionó; si no, `feature/fase2-navegacion`. El cuerpo lleva:

  1. **Resumen.**
     - Qué ve cada rol.
     - La regla de cifras: 3..n−3; porcentaje solo para el nivel y los colegios; estado por grado.
     - Por qué los grados no llevan porcentaje.
  2. **Pruebas.**
     - Totales antes y después.
     - PDF en 3.14.
     - Diagnóstico de grupos visibles (Task 15, Step 3).
     - Comparación del lote real: «idéntico».
  3. **Pasos del usuario, en orden.**
     - Aprobación de textos, umbrales y rutas por el equipo.
     - Migración `2026-10-07c`.
     - Ensayo.
     - `--publicar-ya`.
     - **«Reboot app» después de fusionar.**
  4. **Preguntas abiertas** (lista de abajo).
  5. Cerrar con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 3:** No fusionar. Lo decide el usuario.

---

## Preguntas abiertas y valores provisionales que debe confirmar el equipo

1. **Textos (spec §8.1).** Están en `src/estudiantes/alertas_catalogo.py`, con `TEXTOS_APROBADOS = False`: `que_es`, `que_hacer` por rol, las frases del panel, `SOLO_ESTADO`, `QUE_ES_PRIORIDAD` y `QUE_ES_PRESENTE`.
2. **Rutas (spec §8.1).** Hoy los tres roles usan la ruta vigente, que incluye la «Línea 106» (es de Bogotá); `RUTAS_VALIDADAS = False`.
   - El equipo debe confirmar las líneas de Chía (p. ej. 192 opción 4 o ICBF 141) y la ruta de adultos de la fase 4. Hoy la de adultos lleva solo la Secretaría de Salud y la Comisaría, sin teléfonos.
3. **Umbrales (spec §8.2).** Malestar con 3 de 6 «Muy cierto»; desesperanza con la regla estricta. Se les entrega la sensibilidad: 2, 3 y 4 ítems, y regla estricta frente a amplia.
4. **Ítems con `*` de secundaria (spec §8.3).** Hoy `marcados_en=("primaria",)`. Cuando el equipo marque secundaria, se añade `"secundaria"`.
5. **Decisión de privacidad nueva: los grados llevan solo el estado, sin porcentaje.**
   - Así se cierran las restas de varios pasos entre colegios y grados.
   - La alternativa sería porcentaje por grado con supresión secundaria: más cifras ocultas y una garantía más débil.
   - ¿Lo aprueban? Aplica también a la vista de investigadores y a `alertas.csv`.
6. **Cuando el resto del nivel delata, se oculta el colegio visible más pequeño.** ¿De acuerdo, frente a ocultar el nivel?
7. **Regla de faltantes.**
   - Malestar: los 6 ítems respondidos.
   - Desesperanza: ítems 16 y 18 (la amplia: 1, 4, 16 y 18).
8. **Tarjeta y columna de muerte.**
   - La spec pide reemplazar la **tarjeta** para colegio y municipio. El plan también quita, cuando hay alertas:
     - la columna «Piensa en la muerte con frecuencia» de las tablas de los informes;
     - la opción del selector «Comparar».
   - Para familia, la opción se quita siempre: hoy la ve, contra la spec §6.
   - ¿Confirman?
9. **`casos` en las filas existentes.** Las filas `corte` y `corte_grupo` ya publican `casos`, también del RCADS 18 ≥ «Con frecuencia» por grupo. Es anterior a esta fase y queda fuera de alcance, pero contradice el espíritu de §5.4. ¿Se quitan en una fase posterior?
10. **Recuadro del PDF de una página.** Omite el «qué hacer» de cada alerta para caber en una página (la ruta sí va). ¿Basta?
11. **Enunciados de RCADS 1 y 4** en la pestaña de investigadores: hay que copiarlos del formulario aplicado.
12. **Estados «Prioridad» de grados y celdas.** Se publican como booleanos, solo si el grupo cumple 3..n−3. ¿Aceptan publicar ese estado?
13. **Calibraciones de la prueba real** (8,8 / 15,1 / 22,0 / 32,4 / 17,0 / 10,8–21,5 / 24,9). Son de la spec con los archivos actuales. Con la exportación nueva de secundaria hay que actualizarlas.
14. **Sensibilidad y distribución de ítems.** Hoy no entran en el ZIP; solo `alertas.csv`. ¿Se exportan también?
15. **Mensajes por rol en Supabase.** `mensajes_alertas_para_subir` los deja en el JSON del ensayo; el publicador actual no inserta mensajes. ¿Se suben a `obs360.mensajes` (y cuándo, tras la aprobación)?



---

## Revisión independiente (7-oct-2026) y cambios obligatorios antes de ejecutar

**Críticos**

1. **El estado «Prioridad» de grados y celdas delata cotas de casos.** Un booleano «Prioridad» equivale a «k ≥ t», con t calculable desde cifras públicas (n del grupo, % y n del nivel). Combinado con los colegios, puede revelar que un grado hermano tiene ≤ 2 casos. «Para tener presente» delata la cota contraria.
   **Decisión:** el estado se publica y se muestra **solo donde el porcentaje del grupo es publicable** bajo la supresión general (3 ≤ k ≤ n − 3 más supresión secundaria jerárquica). Así el estado no añade información. Donde el porcentaje se suprime, el estado es neutro: «Sin estado: cifras pequeñas», nunca «Para tener presente».
2. **Reusar la supresión general** (`src/estudiantes/supresion.py`, rama `fix/cortes-casos-pequenos`) en vez de `colegios_visibles` / `_resto_cumple` y de la regla de árbol. Las alertas son una proporción más: pasan por el mismo mecanismo, y los grados pueden llevar porcentaje cuando la supresión lo permita (cumple la spec §5.4, «para cada grupo publicable»). La fase 3 se rebasa sobre ese arreglo antes de las Tasks 4, 5 y 7. Se cierra así la pregunta abierta 5. La 9 la resuelve el arreglo: `casos` deja de publicarse.

**Importantes**

1. `alerta_grupo` lleva `n_grupo` en `detalle`. `tests/test_estudiantes_subgrupos.py` va en la lista de pruebas de la Task 7.
2. En `alertas.csv`, la columna `nombre` pasa a `alerta_nombre` (la prueba de exportables prohíbe `nombre`).
3. La foto de regresión de la Task 0 redondea los flotantes (9 cifras significativas): pandas 3 cambia el último dígito.
4. Tercer estado neutro (ver crítico 1). `QUE_ES_PRESENTE` solo se usa cuando la comparación se hizo.
5. Módulos rancios:
   - `getattr(vc, "ruta_para_rol", None)`, con alternativa `cat.RUTA_ATENCION`.
   - `try/except` alrededor de `render_panel`, `panel_html` y `tabla_secretaria_html`.
6. La auditoría cubre también `alertas_sensibilidad` y `alertas_items`. Si van a Supabase, se publican solo a nivel y con la regla 3..n − 3; si no, se quedan en local (para investigadores).
7. Pruebas de alertas con las tres configuraciones reales de resta (diccionarios `PRIMARIA` y `CON_RESTO` de `test_estudiantes_comunidad.py`).
8. Mensajes por rol en `obs360.mensajes`: se suben cuando el equipo apruebe los textos.

**Menores:**
- La Task 0 no crea la rama, que ya existe.
- El venv de 3.14 está en el scratchpad (`venv314`).
- Quitar `_sin_uso`.
- Cambiar `_sin_conteos` por una prueba sobre las filas.
- Quitar la prueba que inspecciona el código fuente del panel.
- Unificar la detección del `*`.
