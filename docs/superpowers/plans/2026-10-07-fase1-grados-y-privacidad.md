# Fase 1 · Grados visibles y privacidad por resta — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Los grados con 10 o más estudiantes se ven también dentro de un colegio (local y despliegue), sin que ningún grupo de 1 a 9 pueda deducirse restando cifras publicadas.

**Architecture:** Un módulo puro `src/estudiantes/privacidad.py` define la *base publicable* (celdas colegio × grado con n ≥ 10; colegio, grado y nivel se calculan sobre la unión de celdas) y una auditoría de restas sobre conjuntos de estudiantes. El pipeline, el publicador, el lector y la vista comunidad pasan a usarla. Una tabla única de colegios (`src/core/colegios.py`) sustituye al mapa de `ingest`. Supabase filtra por módulo y expone solo la última corrida publicada.

**Tech Stack:** Python 3.13, pandas, Streamlit 1.51, pytest, Supabase (PostgREST), Playwright (Node) para la revisión final.

**Spec:** `docs/superpowers/specs/2026-10-06-cuidadores-alertas-triangulacion-design.md` §5.1–§5.2.

**Convenciones del repo:** código y comentarios en español; funciones puras probadas sin Streamlit; `./venv/bin/python -m pytest`; nunca imprimir nombres de estudiantes; commits terminan con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. Fallas preexistentes conocidas: 2 en `tests/test_knowledge_base.py`.

---

## Mapa de archivos

| Archivo | Cambio |
|---|---|
| `src/core/texto.py` | **Nuevo.** `norm_txt` (movido desde `ingest`). |
| `src/core/colegios.py` | **Nuevo.** Tabla única: `normalizar`, `nombre`, `codigo_desde_nombre`. |
| `src/estudiantes/privacidad.py` | **Nuevo.** `Base`, `base_publicable`, `filas`, `relaciones`, `auditar`, `columnas_publicadas`. |
| `src/estudiantes/ingest.py` | Usa `core.texto` y `core.colegios`; `InformeIngesta.crudo_colegio_grado` e `items_marcados`. |
| `src/estudiantes/pipeline.py` | `localizar_formularios` deduplica; `analizar` y `subanalizar` usan la base; `Analisis.base`. |
| `src/estudiantes/publicar.py` | Auditoría antes de subir; despublica la corrida anterior del módulo; enmascara los conteos nuevos. |
| `src/estudiantes/lectura.py` | Filtra por módulo; textos de aviso actualizados. |
| `supabase/migraciones/2026-10-07-modulo-y-ultima-corrida.sql` | **Nuevo.** Módulo, última corrida por módulo, CHECK de niveles e identificadores. |
| `src/ui/views/estudiantes_comunidad.py` | Filtros y comparaciones sobre la base; cruce publicado; selector de grado desbloqueado. |
| `src/ui/views/estudiantes_informe.py` | «Por grado en el colegio» también en el despliegue; nota de base. |
| `src/ui/views/estudiantes_investigador.py` | Tabla colegio × grado con válidas y respuestas. |
| `tests/test_colegios.py`, `tests/test_privacidad.py`, `tests/test_lectura_modulo.py` | **Nuevos.** |
| `tests/fixtures/colegios_estudiantes_2026-09-18.json` | **Nuevo.** Mapa texto → código antes del cambio (nombres de colegio, sin personas). |
| `tests/test_estudiantes.py`, `tests/test_estudiantes_subgrupos.py`, `tests/test_estudiantes_comunidad.py` | Ajustes a la nueva semántica. |

---

### Task 0: Datos: instantánea de referencia y primaria nueva

No es código; deja los datos en su sitio antes de tocar nada.

- [ ] **Step 1: Copiar la instantánea del 18-sep que usa la regresión**

```bash
D=/Users/joseamorocho/Documents/app_360_observatorio/datos_fuente_360
mkdir -p "$D/otros/archivo/estudiantes_2026-09-18"
cp "$D/estudiantes/"*.csv "$D/otros/archivo/estudiantes_2026-09-18/"
ls "$D/otros/archivo/estudiantes_2026-09-18"
```
Expected: los dos CSV (secundaria y primaria).

- [ ] **Step 2: Generar el fixture del mapa de colegios con el código ACTUAL (antes de la Task 2)**

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
./venv/bin/python - <<'EOF'
import glob, json, sys
sys.path.insert(0, ".")
import pandas as pd
from src.estudiantes import ingest
D = "../datos_fuente_360/otros/archivo/estudiantes_2026-09-18"
textos = set()
for f in glob.glob(D + "/*.csv"):
    raw = pd.read_csv(f)
    col = [c for c in raw.columns if "mi colegio es" in ingest.norm_txt(c)][0]
    textos |= set(raw[col].dropna().astype(str))
mapa = {t: list(ingest.normalizar_colegio(t)) for t in sorted(textos)}
json.dump(mapa, open("tests/fixtures/colegios_estudiantes_2026-09-18.json", "w"),
          ensure_ascii=False, indent=1)
print(len(mapa), "textos de colegio")
EOF
```
Expected: `N textos de colegio` (decenas). El archivo solo trae nombres de colegio.

- [ ] **Step 3: Commit del fixture**

```bash
git add tests/fixtures/colegios_estudiantes_2026-09-18.json
git commit -m "test(colegios): mapa texto → código de los formularios del 18-sep, antes de unificar

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

> El reemplazo del CSV de primaria por el xlsx se hace en la Task 3, cuando `localizar_formularios` ya deduplica.

---

### Task 1: La regresión apunta a la instantánea archivada

**Files:** Modify `tests/test_estudiantes.py` (fixture `analisis_real`, ~línea 314)

- [ ] **Step 1: Cambiar la fuente del fixture**

```python
@pytest.fixture(scope="module")
def analisis_real():
    # La referencia se calculó sobre los formularios del 18-sep-2026. Los datos
    # vigentes cambian con cada exportación; la regresión no debe moverse con ellos.
    base = os.path.join(carpeta_datos("otros"), "archivo", "estudiantes_2026-09-18")
    rutas = pipeline.localizar_formularios(base)
    if len(rutas) < 2:
        pytest.skip("Falta la instantánea de referencia del 18-sep")
    res, informes = pipeline.cargar_y_analizar(rutas, n_boot=60)
    return res, informes
```

- [ ] **Step 2: Correr la regresión**

Run: `./venv/bin/python -m pytest tests/test_estudiantes.py -q`
Expected: PASS (mismas cifras que antes).

- [ ] **Step 3: Commit**

```bash
git add tests/test_estudiantes.py
git commit -m "test(estudiantes): la regresión lee la instantánea archivada del 18-sep

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Tabla única de colegios

**Files:**
- Create: `src/core/texto.py`, `src/core/colegios.py`, `tests/test_colegios.py`
- Modify: `src/estudiantes/ingest.py:32-92` (norm_txt, `_COLEGIOS`, `_SEDES`, `nombre_colegio`, `normalizar_colegio`)

- [ ] **Step 1: Escribir las pruebas**

```python
# tests/test_colegios.py
"""Tabla única de colegios: misma salida que antes salvo correcciones documentadas."""
import json
import os

import pytest

from src.core import colegios

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "colegios_estudiantes_2026-09-18.json")
CONOCIDOS = {"LauV", "JJC", "LaBalsa", "SJMEB", "CdP", "DiosCh", "Bojacá", "Fagua",
             "Fonquetá", "Fusca", "Tiquiza", "CND", "SMR"}


def test_no_regresion_con_los_formularios_del_18_sep():
    if not os.path.exists(FIXTURE):
        pytest.skip("falta el fixture")
    antes = json.load(open(FIXTURE, encoding="utf-8"))
    for texto, (cod_antes, _, sede_antes) in antes.items():
        cod, _, sede = colegios.normalizar(texto)
        # un código conocido nunca cambia a otro código conocido; un «OTRO» puede
        # pasar a reconocerse (es una corrección)
        if cod_antes in CONOCIDOS:
            assert cod == cod_antes, f"«{texto}»: {cod_antes} → {cod}"
        assert sede == sede_antes or sede_antes == ""


@pytest.mark.parametrize("texto,codigo", [
    ("I.E.O Laura Vicuña", "LauV"),
    ("San José María Escrivá", "SJMEB"),
    ("Colegio San José María sede Samaria", "SJMEB"),
    ("Conaldi", "CND"),
    ("Conadi ", "CND"),
    ("Institución educativa diversificado Conaldi", "CND"),
    ("Jj casas", "JJC"),
    ("Balaguer ", "SJMEB"),
    ("Santa María del rio", "SMR"),
    ("IE Bojacá - IE José Joaquín Casas", "Bojacá"),
    ("Cerca de Piedra", "CdP"),
])
def test_variantes_de_texto_libre(texto, codigo):
    assert colegios.normalizar(texto)[0] == codigo


def test_sedes_como_detalle():
    assert colegios.normalizar("Diversificado sede Santa Lucía") == (
        "CND", "Colegio Nacional Diversificado", "Santa Lucía")
    assert colegios.normalizar("Josemaría Escrivá - sede Samaria")[2] == "Samaria"


def test_vacio_y_desconocido():
    assert colegios.normalizar(None) == ("SIN_DATO", "Sin dato", "")
    assert colegios.normalizar("Colegio Inventado")[0] == "OTRO"


@pytest.mark.parametrize("nombre_docentes,codigo", [
    ("José Joaquín Casas", "JJC"),
    ("Diversificado · sede Santa Lucía", "CND"),
    ("Diversificado · sede Campincito", "CND"),
    ("Colegio Nacional Diversificado", "CND"),
    ("Fusca · sede El Cerro", "Fusca"),
    ("San Josemaría Escrivá de Balaguer", "SJMEB"),
    ("Santa María del Río", "SMR"),
])
def test_codigo_desde_nombre_de_docentes(nombre_docentes, codigo):
    assert colegios.codigo_desde_nombre(nombre_docentes) == codigo


def test_nombre_legible():
    assert colegios.nombre("JJC") == "José Joaquín Casas"
    assert colegios.nombre("XYZ") == "XYZ"
```

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_colegios.py -q`
Expected: FAIL (`ModuleNotFoundError: src.core.colegios`).

- [ ] **Step 3: Implementar `src/core/texto.py`**

```python
"""Normalización de texto compartida por todos los módulos."""
from __future__ import annotations

import re
import unicodedata

import numpy as np


def norm_txt(s) -> str:
    """Minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.replace("\xa0", " ").lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())
```

- [ ] **Step 4: Implementar `src/core/colegios.py`**

```python
"""
Tabla única de colegios — Observatorio 360.

Estudiantes, cuidadores y la triangulación reconocen el colegio con estas
reglas. La unidad es el colegio; la sede es un detalle. Docentes conserva los
nombres que ya muestra (scripts/preparar_docentes.py) y usa
`codigo_desde_nombre` solo para unirse con los demás actores.
"""
from __future__ import annotations

from src.core.texto import norm_txt

# (fragmentos normalizados, código, nombre). El orden importa: lo más específico
# primero. «IE Bojacá - IE José Joaquín Casas» es Bojacá.
COLEGIOS = [
    (("bojac",), "Bojacá", "Bojacá"),
    (("laura", "vicuna"), "LauV", "Laura Vicuña"),
    (("joaquin", "jj casas"), "JJC", "José Joaquín Casas"),
    (("balsa",), "LaBalsa", "La Balsa"),
    (("josemaria", "jose maria", "escriva", "escriba", "balaguer"), "SJMEB",
     "San Josemaría Escrivá de Balaguer"),
    (("cerca",), "CdP", "Cerca de Piedra"),
    (("diosa",), "DiosCh", "Diosa Chía"),
    (("fagua",), "Fagua", "Fagua"),
    (("fonquet",), "Fonquetá", "Fonquetá"),
    (("fusca",), "Fusca", "Fusca"),
    (("tiquiza",), "Tiquiza", "Tiquiza"),
    (("diversificado", "conaldi", "conadi", "santa luc", "campincito"), "CND",
     "Colegio Nacional Diversificado"),
    (("santa maria", "stmr"), "SMR", "Santa María del Río"),
]

SEDES = [
    ("samaria", "Samaria"), ("principal", "Principal"), ("preescolar", "Preescolar"),
    ("calahorra", "Mercedes de Calahorra"), ("polideportivo", "Polideportivo"),
    ("tiquiza", "Tiquiza"), ("mercedes", "Mercedes de Calahorra"),
    ("santa luc", "Santa Lucía"), ("campincito", "Campincito"), ("cerro", "El Cerro"),
]


def normalizar(texto) -> tuple[str, str, str]:
    """(código, nombre legible, sede). ('OTRO', texto, sede) si no se reconoce."""
    s = norm_txt(texto)
    if not s:
        return "SIN_DATO", "Sin dato", ""
    sede = next((nombre for frag, nombre in SEDES if frag in s), "")
    for fragmentos, codigo, nombre in COLEGIOS:
        if any(f in s for f in fragmentos):
            return codigo, nombre, sede
    return "OTRO", str(texto).strip(), sede


def nombre(codigo: str) -> str:
    """Nombre legible de un código; el propio código si no se conoce."""
    return next((n for _, c, n in COLEGIOS if c == codigo), str(codigo))


def codigo_desde_nombre(nombre_legible: str) -> str:
    """Código de colegio para un nombre como los que guarda docentes."""
    return normalizar(nombre_legible)[0]
```

- [ ] **Step 5: `ingest` delega en la tabla única**

En `src/estudiantes/ingest.py`: borrar `def norm_txt` (líneas ~32-38), `_COLEGIOS`, `_SEDES`, `nombre_colegio` y `normalizar_colegio` (líneas ~45-92) y añadir arriba, junto a los imports:

```python
from src.core.colegios import nombre as nombre_colegio          # noqa: F401
from src.core.colegios import normalizar as normalizar_colegio  # noqa: F401
from src.core.texto import norm_txt                              # noqa: F401
```

(Los nombres se reexportan porque otros módulos y pruebas los importan desde `ingest`.)

- [ ] **Step 6: Correr pruebas**

Run: `./venv/bin/python -m pytest tests/test_colegios.py tests/test_estudiantes.py tests/test_estudiantes_comunidad.py tests/test_estudiantes_informe.py -q`
Expected: PASS. Si la no regresión falla en un texto concreto, el orden de `COLEGIOS` está mal para ese texto: corregir el orden, no la prueba.

- [ ] **Step 7: Commit**

```bash
git add src/core/texto.py src/core/colegios.py src/estudiantes/ingest.py tests/test_colegios.py
git commit -m "refactor(colegios): tabla única de colegios con sede como detalle

Reconoce «San José María», Conaldi/Diversificado y otras variantes de texto libre.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Carga: un archivo por formulario, conteos crudos e ítems marcados

**Files:**
- Modify: `src/estudiantes/pipeline.py:26-41` (`localizar_formularios`)
- Modify: `src/estudiantes/ingest.py` (`InformeIngesta`, `cargar`)
- Test: `tests/test_estudiantes.py` (añadir al final)

- [ ] **Step 1: Pruebas**

```python
# al final de tests/test_estudiantes.py
def test_localizar_se_queda_con_el_archivo_mas_reciente(tmp_path):
    import time
    viejo = tmp_path / "¡Cuéntanos sobre tus emociones! (respuestas) - Respuestas de formulario 1.csv"
    nuevo = tmp_path / "¡Cuéntanos sobre tus emociones! (respuestas).xlsx"
    viejo.write_text("x")
    time.sleep(0.01)
    nuevo.write_text("x")
    rutas = pipeline.localizar_formularios(str(tmp_path))
    assert rutas == [str(nuevo)]


def test_la_ingesta_guarda_conteos_crudos_e_items_marcados():
    raw = _formulario_sintetico(30)
    col = next(c for c in raw.columns if c.startswith("SDQ"))
    raw = raw.rename(columns={col: "*" + col})
    d, inf = ingest.cargar(raw)
    assert sum(inf.crudo_colegio_grado.values()) == len(raw)
    assert all("|" in k for k in inf.crudo_colegio_grado)
    assert len(inf.items_marcados) == 1 and inf.items_marcados[0].startswith("sdq")
```

> El generador sintético está en `tests/test_estudiantes.py:177`; si su firma no acepta `n`, llamarlo sin argumentos.

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_estudiantes.py -q -k "localizar or crudos"`
Expected: FAIL (devuelve dos rutas; `InformeIngesta` sin `crudo_colegio_grado`).

- [ ] **Step 3: Implementar `localizar_formularios`**

```python
def localizar_formularios(base: str | None = None) -> list[str]:
    """Un archivo por formulario: si hay varios (CSV viejo y xlsx nuevo), el más reciente."""
    from src.estudiantes.ingest import norm_txt
    from src.core.rutas import carpeta_datos
    base = base or carpeta_datos("estudiantes")
    if not os.path.isdir(base):
        return []
    archivos = [f for f in os.listdir(base) if f.lower().endswith(EXTENSIONES)]
    rutas: list[str] = []
    for p in PATRONES:
        candidatos = [os.path.join(base, f) for f in archivos if p in norm_txt(f)]
        if candidatos:
            rutas.append(max(candidatos, key=os.path.getmtime))
    return rutas
```

- [ ] **Step 4: Implementar los campos de ingesta**

En `InformeIngesta` añadir:

```python
    crudo_colegio_grado: dict = field(default_factory=dict)  # «LauV|Sexto» → filas del archivo
    items_marcados: list[str] = field(default_factory=list)  # encabezados con «*», normalizados
```

En `cargar`, justo después de `d["Sede"] = ...`:

```python
    # Conteos ANTES de limpiar: son los que cuentan los investigadores en la hoja
    from src.estudiantes.privacidad import clave_celda
    inf.crudo_colegio_grado = {clave_celda(c, g): int(n) for (c, g), n in
                               d.groupby(["Colegio", "Grado"]).size().items()}
    inf.items_marcados = [norm_txt(c) for c in raw.columns if str(c).strip().startswith("*")]
```

(`clave_celda` se crea en la Task 4; si se ejecuta esta task antes, definir temporalmente `f"{c}|{g}"` y reemplazarlo en la Task 4.)

- [ ] **Step 5: Correr pruebas**

Run: `./venv/bin/python -m pytest tests/test_estudiantes.py -q`
Expected: PASS.

- [ ] **Step 6: Reemplazar el CSV de primaria por el xlsx**

```bash
D=/Users/joseamorocho/Documents/app_360_observatorio/datos_fuente_360
mv "$D/estudiantes/entrantes/¡Cuéntanos sobre tus emociones! (respuestas).xlsx" "$D/estudiantes/"
mv "$D/estudiantes/¡Cuéntanos sobre tus emociones! (respuestas) - Respuestas de formulario 1.csv" "$D/otros/archivo/"
rmdir "$D/estudiantes/entrantes"
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
./venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from src.estudiantes import pipeline; from src.core.rutas import carpeta_datos
print([r.rsplit('/',1)[1] for r in pipeline.localizar_formularios(carpeta_datos('estudiantes'))])"
```
Expected: el CSV de secundaria y el xlsx de primaria.

- [ ] **Step 7: Commit**

```bash
git add src/estudiantes/pipeline.py src/estudiantes/ingest.py tests/test_estudiantes.py
git commit -m "feat(estudiantes): un archivo por formulario, conteos crudos colegio×grado e ítems marcados

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Base publicable

**Files:** Create `src/estudiantes/privacidad.py`, `tests/test_privacidad.py`

- [ ] **Step 1: Pruebas con las tres configuraciones reales de resta**

```python
# tests/test_privacidad.py
"""Base publicable y auditoría de restas (spec 6-oct-2026 §5.1)."""
import pandas as pd
import pytest

from src.estudiantes import privacidad as pv


def _d(conteos: dict[tuple[str, str], int], **cols) -> pd.DataFrame:
    filas = [dict(Colegio=c, Grado=g) for (c, g), n in conteos.items() for _ in range(n)]
    d = pd.DataFrame(filas)
    for k, v in cols.items():
        d[k] = v(d) if callable(v) else v
    return d


# Secundaria del 18-sep: Décimo = LaBalsa 32 + LauV 90 + CdP 6
DECIMO = {("LaBalsa", "Décimo"): 32, ("LauV", "Décimo"): 90, ("CdP", "Décimo"): 6,
          ("CdP", "Sexto"): 2, ("DiosCh", "Sexto"): 3, ("LauV", "Sexto"): 95}
# Primaria nueva: SJMEB 6 + 8, sin celdas publicables
PRIMARIA = {("CdP", "Cuarto"): 11, ("CdP", "Quinto"): 30, ("LauV", "Quinto"): 97,
            ("SJMEB", "Cuarto"): 6, ("SJMEB", "Quinto"): 8, ("DiosCh", "Cuarto"): 2}
# Primaria del 18-sep: CdP total 15 = cuarto 5 + quinto 10
CDP15 = {("CdP", "Cuarto"): 5, ("CdP", "Quinto"): 10, ("LauV", "Cuarto"): 86}


def test_las_celdas_publicables_son_las_de_diez_o_mas():
    b = pv.base_publicable(_d(DECIMO))
    assert set(b.celdas) == {"LaBalsa|Décimo", "LauV|Décimo", "LauV|Sexto"}


def test_el_grado_excluye_los_colegios_pequenos():
    b = pv.base_publicable(_d(DECIMO))
    assert len(b.grados["Décimo"]) == 122          # sin los 6 de CdP


def test_el_colegio_es_la_union_de_sus_celdas():
    b = pv.base_publicable(_d(CDP15))
    assert len(b.colegios["CdP"]) == 10            # el cuarto de 5 queda fuera


def test_colegio_sin_celdas_pero_grande_se_publica_entero():
    b = pv.base_publicable(_d(PRIMARIA))
    assert len(b.colegios["SJMEB"]) == 14
    assert "SJMEB|Cuarto" not in b.celdas


def test_el_nivel_incluye_el_resto_solo_si_es_grande_y_de_dos_colegios():
    grande = pv.base_publicable(_d({**DECIMO, ("DiosCh", "Octavo"): 5}))
    assert grande.incluye_resto                    # 6 + 2 + 3 + 5 = 16, 2 colegios
    chico = pv.base_publicable(_d(PRIMARIA))
    assert not chico.incluye_resto                 # 2, un colegio
    assert len(chico.nivel) == len(_d(PRIMARIA)) - 2


@pytest.mark.parametrize("conteos", [DECIMO, PRIMARIA, CDP15])
def test_ninguna_resta_deja_un_grupo_pequeno(conteos):
    d = _d(conteos)
    b = pv.base_publicable(d)
    assert pv.auditar(d, b, []) == []


def test_la_auditoria_detecta_una_resta_peligrosa():
    """Si se publicara el grado completo, Décimo − celdas = CdP décimo (6)."""
    d = _d(DECIMO)
    b = pv.base_publicable(d)
    b.grados["Décimo"] = d.index[d["Grado"] == "Décimo"]   # el error que evitamos
    problemas = pv.auditar(d, b, [])
    assert any("Grado Décimo" in p and "6" in p for p in problemas)


def test_la_auditoria_mira_cada_indicador_por_separado():
    """Con faltantes, el resto válido de un indicador puede quedar pequeño."""
    conteos = {("A", "X"): 12, ("A", "Y"): 12, ("B", "X"): 12}
    d = _d(conteos)
    d["SDQ_Total"] = 1.0
    # 3 respuestas válidas de A|Y y el resto faltante: la celda no publica el
    # indicador, pero el colegio A sí (15 válidas) → A − A|X = 3
    idx = d.index[(d.Colegio == "A") & (d.Grado == "Y")]
    d.loc[idx[3:], "SDQ_Total"] = None
    b = pv.base_publicable(d)
    assert any(p.startswith("SDQ_Total") for p in pv.auditar(d, b, ["SDQ_Total"]))


def test_filas_respeta_la_base():
    d = _d(DECIMO)
    b = pv.base_publicable(d)
    assert len(pv.filas(d, b, colegio="CdP")) == 0
    assert len(pv.filas(d, b, grado="Décimo")) == 122
    assert len(pv.filas(d, b, colegio="LauV", grado="Décimo")) == 90
    assert len(pv.filas(d, b, colegio="CdP", grado="Décimo")) == 0
```

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_privacidad.py -q`
Expected: FAIL (`No module named src.estudiantes.privacidad`).

- [ ] **Step 3: Implementar `src/estudiantes/privacidad.py`**

```python
"""
Base publicable y auditoría de restas — Estudiantes 360.

La unidad mínima que se publica es la celda colegio × grado con al menos
MIN_GROUP_N estudiantes. Todo agregado publicado (colegio, grado, nivel) se
calcula sobre la unión de esas celdas, para que ningún grupo pequeño pueda
obtenerse restando cifras publicadas (spec del 6-oct-2026, §5.1):

  · colegio = unión de sus celdas; si no tiene ninguna y llega al mínimo, el
    colegio completo;
  · grado   = unión de sus celdas (los colegios pequeños quedan fuera);
  · nivel   = todos, si el resto que no cae en ningún colegio publicado es 0 o
    reúne ≥ MIN_GROUP_N respuestas de ≥ 2 colegios; si no, la unión publicada.

`auditar` comprueba, por indicador, que ninguna resta de un paso entre un
agregado y sus subgrupos publicados deje entre 1 y MIN_GROUP_N − 1 respuestas.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.estudiantes import catalog as cat

SEP = "|"
TODOS = "Todos"
AGRUPACION_CRUCE = "Colegio×Grado"


def clave_celda(colegio, grado) -> str:
    return f"{colegio}{SEP}{grado}"


def partir_celda(clave: str) -> tuple[str, str]:
    colegio, grado = str(clave).split(SEP, 1)
    return colegio, grado


def _union(indices) -> pd.Index:
    salida = pd.Index([])
    for i in indices:
        salida = salida.union(i)
    return salida


def _activo(valor) -> bool:
    return valor not in (TODOS, None, "")


@dataclass
class Base:
    celdas: dict = field(default_factory=dict)     # «LauV|Sexto» → índices
    colegios: dict = field(default_factory=dict)   # «LauV» → índices
    grados: dict = field(default_factory=dict)     # «Sexto» → índices
    nivel: pd.Index = field(default_factory=lambda: pd.Index([]))
    n_total: int = 0
    incluye_resto: bool = True

    @property
    def n_fuera_de_celdas(self) -> int:
        return self.n_total - len(_union(self.celdas.values()))

    def resumen(self) -> dict:
        return dict(n_total=self.n_total, n_nivel=len(self.nivel),
                    n_fuera_de_celdas=self.n_fuera_de_celdas,
                    incluye_resto=self.incluye_resto)


def base_publicable(d: pd.DataFrame, minimo: int = cat.MIN_GROUP_N) -> Base:
    b = Base(n_total=len(d))
    if d.empty or not {"Colegio", "Grado"} <= set(d.columns):
        b.nivel = d.index
        return b
    for (colegio, grado), sub in d.groupby(["Colegio", "Grado"]):
        if len(sub) >= minimo:
            b.celdas[clave_celda(colegio, grado)] = sub.index
    for colegio, sub in d.groupby("Colegio"):
        propias = [i for k, i in b.celdas.items() if partir_celda(k)[0] == str(colegio)]
        if propias:
            b.colegios[str(colegio)] = _union(propias)
        elif len(sub) >= minimo:
            b.colegios[str(colegio)] = sub.index
    for grado in d["Grado"].dropna().unique():
        propias = [i for k, i in b.celdas.items() if partir_celda(k)[1] == str(grado)]
        if propias:
            b.grados[str(grado)] = _union(propias)
    publicado = _union(b.colegios.values())
    resto = d.index.difference(publicado)
    colegios_resto = d.loc[resto, "Colegio"].nunique() if len(resto) else 0
    b.incluye_resto = len(resto) == 0 or (len(resto) >= minimo and colegios_resto >= 2)
    b.nivel = d.index if b.incluye_resto else publicado
    return b


def filas(d: pd.DataFrame, base: Base, colegio=TODOS, grado=TODOS) -> pd.DataFrame:
    """Filas sobre las que se calcula el grupo pedido; vacío si no es publicable."""
    if _activo(colegio) and _activo(grado):
        idx = base.celdas.get(clave_celda(colegio, grado))
    elif _activo(colegio):
        idx = base.colegios.get(str(colegio))
    elif _activo(grado):
        idx = base.grados.get(str(grado))
    else:
        idx = base.nivel
    if idx is None:
        return d.iloc[0:0]
    return d.loc[d.index.intersection(idx)]


def relaciones(base: Base) -> list[tuple[str, pd.Index, list[pd.Index]]]:
    """(nombre del padre, índices del padre, índices de cada hijo publicado)."""
    rel = [("Nivel", base.nivel, list(base.colegios.values())),
           ("Nivel", base.nivel, list(base.grados.values()))]
    for c, idx in base.colegios.items():
        hijos = [i for k, i in base.celdas.items() if partir_celda(k)[0] == c]
        if hijos:
            rel.append((f"Colegio {c}", idx, hijos))
    for g, idx in base.grados.items():
        hijos = [i for k, i in base.celdas.items() if partir_celda(k)[1] == g]
        rel.append((f"Grado {g}", idx, hijos))
    return rel


def auditar(d: pd.DataFrame, base: Base, columnas: list[str],
            minimo: int = cat.MIN_GROUP_N) -> list[str]:
    """Restas que dejarían un grupo de 1 a minimo − 1. Lista vacía = se puede publicar."""
    problemas: list[str] = []
    for col in [None, *columnas]:
        if col is not None and col not in d.columns:
            continue
        validos = d.index if col is None else d.index[d[col].notna()]
        etiqueta = "respuestas" if col is None else col
        for nombre, idx_padre, hijos in relaciones(base):
            padre = idx_padre.intersection(validos)
            if len(padre) < minimo:
                continue
            publicados = [h.intersection(validos) for h in hijos]
            publicados = [h for h in publicados if len(h) >= minimo]
            if not publicados:
                continue
            resto = padre.difference(_union(publicados))
            if 0 < len(resto) < minimo:
                problemas.append(f"{etiqueta}: {nombre} menos sus subgrupos publicados "
                                 f"deja {len(resto)} respuestas")
    return problemas


def columnas_publicadas(a) -> list[str]:
    """Columnas de `a.datos` cuyas cifras salen publicadas por grupo o por nivel."""
    cols = set(a.escalas or [])
    for tabla in (a.cortes, a.bandas, a.items_pssm):
        if tabla is not None and not tabla.empty:
            col = "item" if "item" in tabla.columns else "clave"
            cols.update(str(v) for v in tabla[col])
    for c in a.contrastes or []:
        cols.update([c["resultado"], c["protector"]])
    return sorted(cols)
```

- [ ] **Step 4: Correr pruebas**

Run: `./venv/bin/python -m pytest tests/test_privacidad.py -q`
Expected: PASS (10 pruebas).

- [ ] **Step 5: Commit**

```bash
git add src/estudiantes/privacidad.py tests/test_privacidad.py
git commit -m "feat(privacidad): base publicable sobre celdas colegio×grado y auditoría de restas

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: El pipeline calcula sobre la base y publica el cruce

**Files:**
- Modify: `src/estudiantes/pipeline.py` (`Analisis`, `analizar`, `COLUMNAS_SUBGRUPO`, `subanalizar`)
- Modify: `tests/test_estudiantes_subgrupos.py`

- [ ] **Step 1: Pruebas nuevas y ajustadas en `tests/test_estudiantes_subgrupos.py`**

Reemplazar `test_las_filas_de_subgrupo_respetan_el_minimo`, `test_la_comparacion_entre_grupos_sale_de_los_subgrupos` y `test_sin_subgrupo_publicado_no_hay_cifra_y_el_informe_lo_explica` por:

```python
def test_las_filas_de_subgrupo_respetan_el_minimo(analisis):
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
             if f["tipo"].endswith("_grupo")]
    assert filas
    assert all(f["n"] >= cat.MIN_GROUP_N for f in filas)
    assert all(f["detalle"]["n_grupo"] >= cat.MIN_GROUP_N for f in filas)
    assert {f["agrupacion"] for f in filas} <= {"Colegio", "Grado", "Colegio×Grado"}


def test_el_pipeline_publica_el_cruce_colegio_grado(analisis):
    cruce = analisis.subgrupos["Colegio×Grado"]
    assert set(cruce) == {"LauV|Séptimo", "LauV|Octavo"}
    assert all(s.n >= cat.MIN_GROUP_N for s in cruce.values())


def test_el_colegio_excluye_su_grado_pequeno(analisis):
    # LauV tiene 4 respuestas en Noveno: el colegio publicado son sus dos celdas
    assert analisis.subgrupos["Colegio"]["LauV"].n == 62


def test_la_comparacion_entre_grupos_sale_de_los_subgrupos(analisis, publicado):
    indicador = next(k for k in vc.INDICADORES if vc.prevalencia(analisis, k, {}))
    for filtros in ({}, {"colegio": "LauV"}):
        crudo = vc.prevalencia_por(analisis, indicador, "Grado", filtros)
        desp = vc.prevalencia_por(publicado, indicador, "Grado", filtros)
        assert list(desp.columns) == ["grupo", "n", "casos", "pct", "ic_inf", "ic_sup"]
        assert set(desp["grupo"]) == set(crudo["grupo"]) and not desp.empty
        fusion = crudo.merge(desp, on="grupo", suffixes=("_c", "_d"))
        assert (fusion["pct_c"] - fusion["pct_d"]).abs().max() < 0.01


def test_el_cruce_publicado_da_las_mismas_cifras_que_el_recalculo(analisis, publicado):
    f = {"colegio": "LauV", "grado": "Octavo"}
    assert vc.bandas_sdq_total(publicado, f)["n"] == vc.bandas_sdq_total(analisis, f)["n"] == 31
    for indicador in vc.INDICADORES:
        assert vc.prevalencia(publicado, indicador, f) == pytest.approx(
            vc.prevalencia(analisis, indicador, f), abs=0.01)


def test_un_cruce_pequeno_no_da_cifras_y_el_informe_lo_explica(analisis, publicado):
    cruce = {"colegio": "LauV", "grado": GRADO_PEQUENO}
    for a in (analisis, publicado):
        assert vc.bandas_sdq_total(a, cruce) == {}
        assert vc.items_pertenencia_bajos(a, 4, cruce) == []
        assert vc.tarjetas(a, "colegio", cruce) == []
    assert vc.subanalisis(publicado, cruce) is None
    informe = vc.informe_markdown(publicado, "colegio", cruce)
    assert "por colegio y por grado" in informe
    assert vc.bandas_sdq_total(publicado, {"grado": GRADO_PEQUENO}) == {}
```

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_subgrupos.py -q`
Expected: FAIL (`KeyError: 'Colegio×Grado'`, LauV n = 66).

- [ ] **Step 3: Implementar en `src/estudiantes/pipeline.py`**

Import:

```python
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, privacidad, scoring, stats
```

En `Analisis`, tras `subgrupos`:

```python
    # Base publicable (privacidad.Base). Solo existe con datos crudos; no se publica.
    base: object = None
```

En `analizar`, sustituir el bloque desde `a = Analisis(...)` hasta `a.subgrupos = ...` por:

```python
    a = Analisis(nivel=nivel, n=len(d), datos=d, escalas=claves,
                 avisos=list(avisos or []))
    base = privacidad.base_publicable(d)
    a.base = base
    dn = d.loc[base.nivel]           # lo que se publica a nivel de todo el nivel
    a.muestra = dict(
        n=len(d),
        sexo=d["Sexo"].value_counts().to_dict(),
        edad_M=round(float(d["Edad"].mean()), 2), edad_DE=round(float(d["Edad"].std()), 2),
        edad={int(k): int(v) for k, v in
              d["Edad"].dropna().value_counts().sort_index().items()},
        grado=d["Grado"].value_counts().to_dict(),
        colegio=d["Colegio"].value_counts().to_dict(),
        colegio_grado={privacidad.clave_celda(c, g): int(n) for (c, g), n in
                       d.groupby(["Colegio", "Grado"]).size().items()},
        base=base.resumen(),
        fechas=([str(d["ts"].min().date()), str(d["ts"].max().date())]
                if "ts" in d.columns and d["ts"].notna().any() else []),
    )
    a.descriptivos = scoring.descriptivos(dn)
    a.fiabilidad = scoring.fiabilidad(dn, n_boot=n_boot)
    a.bandas = scoring.distribucion_bandas(dn, "self")
    a.cortes = scoring.sobre_cortes(dn)
    a.terciles = scoring.terciles(dn)
    if "RCADS_Dep" in claves:
        a.percentiles = scoring.percentiles_por_sexo(
            dn, ["RCADS_Dep", "RCADS_Anx", "RCADS_Total"])

    corr_vars = (cat.CORR_VARS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.CORR_VARS_PRI)
    a.correlaciones = stats.correlaciones(dn, corr_vars)
    a.matriz = stats.matriz_correlaciones(dn, corr_vars)

    a.por_sexo = stats.comparar_por_sexo(dn, claves)
    en_grados = d.loc[privacidad._union(base.grados.values())]
    en_colegios = d.loc[privacidad._union(base.colegios.values())]
    a.por_grado, enm_g = stats.comparar_por_grupo(en_grados, claves, "Grado", orden_grados)
    a.por_colegio, enm_c = stats.comparar_por_grupo(en_colegios, claves, "Colegio")
    a.enmascarados = {"Grado": enm_g, "Colegio": enm_c}
    a.por_edad = stats.correlacion_con_edad(dn, claves)

    objetivos = [k for k in ("RCADS_Dep", "RCADS_Anx", "SDQ_Total", "ARI_Total") if k in claves]
    for y in objetivos:
        m = stats.modelo(dn, y, [p for p in PROTECTORES if p in claves])
        if m:
            a.modelos.append(m)
    if "SDQ_Con" in claves and "TD_Total" in claves:
        m = stats.modelo(dn, "SDQ_Con", ["TD_Total", "ERQ_Sup", "ERQ_Reap", "PSSM_Total"])
        if m:
            a.modelos.append(m)

    a.icc = {k: stats.icc_entre_grupos(dn, k) for k in claves}
    a.solapamiento = stats.solapamiento(dn)
    a.contrastes = _contrastes(dn, claves)
    a.items_pssm = stats.medias_items(dn, "PSSM")
    a.subgrupos = subanalizar(d, nivel, claves, base)
```

Sustituir `COLUMNAS_SUBGRUPO` y `subanalizar`:

```python
COLUMNAS_SUBGRUPO = ("Colegio", "Grado", privacidad.AGRUPACION_CRUCE)


def subanalizar(d: pd.DataFrame, nivel: str, claves: list[str], base=None) -> dict:
    """Resultados de la vista comunidad por colegio, por grado y por celda colegio×grado.

    Cada grupo se calcula sobre la base publicable (privacidad.base_publicable):
    así ninguna resta entre un colegio, un grado y sus celdas deja un grupo pequeño.
    """
    base = base or privacidad.base_publicable(d)
    salida: dict = {}
    for columna, grupos in (("Colegio", base.colegios), ("Grado", base.grados),
                            (privacidad.AGRUPACION_CRUCE, base.celdas)):
        for grupo, idx in grupos.items():
            sub = d.loc[idx]
            if len(sub) < cat.MIN_GROUP_N:
                continue
            s = Analisis(nivel=nivel, n=len(sub), datos=pd.DataFrame(),
                         escalas=list(claves), muestra=dict(n=len(sub)))
            s.bandas = scoring.distribucion_bandas(sub, "self")
            s.cortes = scoring.sobre_cortes(sub)
            s.items_pssm = stats.medias_items(sub, "PSSM")
            s.contrastes = _contrastes(sub, claves)
            salida.setdefault(columna, {})[str(grupo)] = s
    return salida
```

- [ ] **Step 4: Correr pruebas del pipeline (la vista se ajusta en la Task 8)**

Run: `./venv/bin/python -m pytest tests/test_privacidad.py tests/test_estudiantes.py tests/test_estudiantes_subgrupos.py -q -k "not comparacion and not cruce and not informe"`
Expected: PASS. Las pruebas de vista (`comparacion`, `cruce`) pasan al terminar la Task 8.

- [ ] **Step 5: Commit**

```bash
git add src/estudiantes/pipeline.py tests/test_estudiantes_subgrupos.py
git commit -m "feat(estudiantes): el pipeline calcula sobre la base publicable y añade el cruce colegio×grado

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: El publicador audita, enmascara y despublica la corrida anterior

**Files:** Modify `src/estudiantes/publicar.py`; Test `tests/test_estudiantes_publicar.py` (añadir)

- [ ] **Step 1: Pruebas**

```python
# al final de tests/test_estudiantes_publicar.py
from tests.test_estudiantes_comunidad import _formulario


@pytest.fixture(scope="module")
def analisis_sintetico():
    from src.estudiantes import ingest, scoring
    bruto, _ = ingest.cargar(_formulario())
    return {cat.NIVEL_SECUNDARIA: pipeline.analizar(scoring.puntuar(bruto),
                                                    cat.NIVEL_SECUNDARIA, n_boot=20)}


def test_la_auditoria_de_restas_pasa_con_la_base(analisis_sintetico):
    assert publicar.verificar_restas(analisis_sintetico) == []


def test_la_auditoria_bloquea_una_base_manipulada(analisis_sintetico):
    import copy
    a = copy.copy(analisis_sintetico[cat.NIVEL_SECUNDARIA])
    b = copy.copy(a.base)
    b.colegios = dict(b.colegios)
    b.colegios["LauV"] = a.datos.index[a.datos["Colegio"] == "LauV"]   # incluye Noveno (4)
    a.base = b
    assert publicar.verificar_restas({cat.NIVEL_SECUNDARIA: a})


class _Tabla:
    def __init__(self, registro, nombre):
        self.r, self.n = registro, nombre
    def insert(self, filas):
        self.r.append(("insert", self.n, filas)); return self
    def update(self, valores):
        self.r.append(("update", self.n, valores)); return self
    def eq(self, k, v):
        self.r.append(("eq", self.n, (k, v))); return self
    def neq(self, k, v):
        self.r.append(("neq", self.n, (k, v))); return self
    def execute(self):
        class R: data = [{"id": 7}]
        return R()


class _Cliente:
    def __init__(self):
        self.registro = []
        cliente = self
        class _Schema:
            def table(self, nombre): return _Tabla(cliente.registro, nombre)
        class _Postgrest:
            def schema(self, _): return _Schema()
        self.postgrest = _Postgrest()


def test_publicar_ya_despublica_la_corrida_anterior_del_modulo(analisis_sintetico):
    cli = _Cliente()
    publicar.publicar(analisis_sintetico, publicar_ya=True, cliente=cli)
    pasos = cli.registro
    assert ("update", "corridas", {"publicada": False}) in pasos
    assert ("eq", "corridas", ("modulo", "estudiantes")) in pasos
    assert ("neq", "corridas", ("id", 7)) in pasos


def test_sin_publicar_ya_no_toca_otras_corridas(analisis_sintetico):
    cli = _Cliente()
    publicar.publicar(analisis_sintetico, publicar_ya=False, cliente=cli)
    assert not any(p[0] == "update" for p in cli.registro)


def test_los_conteos_crudos_se_enmascaran_al_publicar():
    class Inf:
        nivel = "secundaria"
        crudo_colegio_grado = {"LauV|Sexto": 95, "CdP|Décimo": 6}
    filas = publicar.aplanar_ingesta([Inf()])
    crudo = filas[0]["detalle"]["ingesta"]["crudo_colegio_grado"]
    assert crudo["LauV|Sexto"] == 95 and crudo["CdP|Décimo"] == "<10"
```

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_publicar.py -q`
Expected: FAIL (`verificar_restas` no existe).

- [ ] **Step 3: Implementar**

Imports y constante:

```python
from src.estudiantes import catalog as cat
from src.estudiantes import pipeline, privacidad

MODULO = "estudiantes"
```

Nueva función, tras `verificar`:

```python
def verificar_restas(analisis: dict) -> list[str]:
    """Problemas de resta en cualquier nivel con datos crudos (ver privacidad.auditar)."""
    problemas: list[str] = []
    for nivel, a in (analisis or {}).items():
        if a is None or getattr(a, "base", None) is None or a.datos is None or a.datos.empty:
            continue
        problemas += [f"{nivel} · {p}" for p in
                      privacidad.auditar(a.datos, a.base, privacidad.columnas_publicadas(a))]
    return problemas
```

En `publicar`, tras `verificar(filas)`:

```python
    restas = verificar_restas(analisis)
    if restas:
        raise PublicacionInsegura(
            "No se publicó nada: alguna resta entre cifras publicadas dejaría un grupo "
            f"de menos de {cat.MIN_GROUP_N}:\n  - " + "\n  - ".join(restas[:20]))
```

En el dict `corrida`, `modulo=MODULO`. Tras insertar los resultados:

```python
    if corrida["publicada"]:
        # Dos corridas legibles a la vez permitirían restar una de otra y aislar
        # las respuestas nuevas: solo queda publicada la última de este módulo.
        (tabla(TABLA_CORRIDAS).update({"publicada": False})
         .eq("modulo", MODULO).neq("id", corrida_id).execute())
```

En `CAMPOS_INGESTA` añadir `"crudo_colegio_grado"`, y en `aplanar_ingesta` enmascararlo igual que `colegios`:

```python
            detalle[campo] = (_enmascarar_conteos(valor)
                              if campo in ("colegios", "crudo_colegio_grado") else valor)
```

En `main`, en la rama `--ensayo`, antes de escribir el JSON:

```python
        restas = verificar_restas(analisis)
        if restas:
            print("AVISO: la auditoría de restas encontró problemas:\n  - " + "\n  - ".join(restas))
```

- [ ] **Step 4: Correr pruebas**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_publicar.py tests/test_privacidad.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/estudiantes/publicar.py tests/test_estudiantes_publicar.py
git commit -m "feat(publicar): auditoría de restas, conteos crudos enmascarados y solo una corrida publicada por módulo

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Supabase por módulo y lector filtrado

**Files:**
- Create: `supabase/migraciones/2026-10-07-modulo-y-ultima-corrida.sql`, `tests/test_lectura_modulo.py`
- Modify: `src/estudiantes/lectura.py` (`id_corrida_vigente`, `_traer_filas`, `AVISO_SIN_DATOS_CRUDOS`)

- [ ] **Step 1: Prueba del lector**

```python
# tests/test_lectura_modulo.py
"""El lector solo mira las corridas de estudiantes."""
from src.estudiantes import lectura


class _Consulta:
    def __init__(self, registro, tabla):
        self.r, self.t = registro, tabla
    def select(self, *_): return self
    def order(self, *a, **k): return self
    def limit(self, *_): return self
    def range(self, *_): return self
    def eq(self, k, v):
        self.r.append((self.t, k, v)); return self
    def execute(self):
        class R: data = []
        return R()


class _Cliente:
    def __init__(self):
        self.registro = []
        cli = self
        class _S:
            def table(self, t): return _Consulta(cli.registro, t)
        class _P:
            def schema(self, _): return _S()
        self.postgrest = _P()


def test_el_lector_filtra_por_modulo(monkeypatch):
    cli = _Cliente()
    monkeypatch.setattr(lectura, "_cliente", lambda: cli)
    assert lectura.id_corrida_vigente() is None
    lectura._traer_filas(cli)
    assert ("corridas", "modulo", "estudiantes") in cli.registro
    assert cli.registro.count(("corridas", "modulo", "estudiantes")) == 2


def test_el_aviso_ya_no_dice_que_no_se_puede_filtrar():
    assert "no se puede filtrar" not in lectura.AVISO_SIN_DATOS_CRUDOS
```

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_lectura_modulo.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar en `lectura.py`**

```python
MODULO = "estudiantes"


def id_corrida_vigente() -> int | None:
    """Id de la corrida publicada más reciente de estudiantes, o None."""
    cli = _cliente()
    filas = (cli.postgrest.schema(ESQUEMA).table("corridas").select("id")
             .eq("modulo", MODULO)
             .order("creada_en", desc=True).limit(1).execute().data)
    return int(filas[0]["id"]) if filas else None
```

En `_traer_filas`, la consulta de corridas pasa a:

```python
    corridas = (tabla.table("corridas").select("*").eq("modulo", MODULO)
                .order("creada_en", desc=True).limit(1).execute().data)
```

Y el aviso:

```python
AVISO_SIN_DATOS_CRUDOS = (
    "Los resultados vienen de la corrida publicada en la base de datos: se puede "
    "filtrar por colegio, por grado y por grado dentro de un colegio cuando el grupo "
    "tiene 10 o más estudiantes. Las respuestas individuales nunca salen del equipo "
    "que procesa los datos.")
```

- [ ] **Step 4: Escribir la migración**

```sql
-- supabase/migraciones/2026-10-07-modulo-y-ultima-corrida.sql
-- Observatorio 360 · corridas por módulo y solo la última publicada por módulo.
-- Ejecutar en Supabase → SQL Editor. Aditiva e idempotente.

-- 1. Niveles: se admite el módulo de cuidadores (fase 4)
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_nivel_valido;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_nivel_valido
    CHECK (nivel IN ('secundaria', 'primaria', 'cuidadores'));

-- 2. Ningún identificador de estudiante (E), cuidador (C) ni niño (N)
ALTER TABLE obs360.resultados DROP CONSTRAINT IF EXISTS resultados_sin_id_estudiante;
ALTER TABLE obs360.resultados ADD CONSTRAINT resultados_sin_id_estudiante CHECK (
    (grupo IS NULL OR grupo !~* '^[ECN][0-9a-f]{8}$') AND clave !~* '^[ECN][0-9a-f]{8}$');

-- 3. ¿Es esta la última corrida publicada de su módulo?
CREATE OR REPLACE FUNCTION obs360.es_ultima_publicada(p_id bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = obs360 AS $$
  SELECT EXISTS (
    SELECT 1 FROM obs360.corridas c
    WHERE c.id = p_id AND c.publicada
      AND c.creada_en = (SELECT max(c2.creada_en) FROM obs360.corridas c2
                         WHERE c2.modulo = c.modulo AND c2.publicada));
$$;
REVOKE ALL ON FUNCTION obs360.es_ultima_publicada(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION obs360.es_ultima_publicada(bigint) TO anon, authenticated, service_role;

-- 4. El público solo lee la última corrida publicada de cada módulo
DROP POLICY IF EXISTS "lectura publica de corridas publicadas" ON obs360.corridas;
CREATE POLICY "lectura publica de corridas publicadas" ON obs360.corridas
    FOR SELECT TO anon, authenticated USING (obs360.es_ultima_publicada(id));

DROP POLICY IF EXISTS "lectura publica de resultados publicados" ON obs360.resultados;
CREATE POLICY "lectura publica de resultados publicados" ON obs360.resultados
    FOR SELECT TO anon, authenticated USING (obs360.es_ultima_publicada(corrida_id));

-- 5. Vistas por módulo
CREATE OR REPLACE VIEW obs360.ultima_corrida WITH (security_invoker = true) AS
SELECT DISTINCT ON (modulo) * FROM obs360.corridas
WHERE publicada = true ORDER BY modulo, creada_en DESC;

-- 6. Mensajes por módulo
ALTER TABLE obs360.mensajes ADD COLUMN IF NOT EXISTS modulo TEXT NOT NULL DEFAULT 'estudiantes';
ALTER TABLE obs360.mensajes DROP CONSTRAINT IF EXISTS mensajes_unicos;
ALTER TABLE obs360.mensajes ADD CONSTRAINT mensajes_unicos UNIQUE (modulo, clave, accion_rol);

-- 7. Comprobación: debe devolver una fila por módulo con publicada = true
-- SELECT modulo, id, creada_en FROM obs360.ultima_corrida;
```

- [ ] **Step 5: Correr pruebas**

Run: `./venv/bin/python -m pytest tests/test_lectura_modulo.py tests/test_estudiantes_lectura.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add supabase/migraciones/2026-10-07-modulo-y-ultima-corrida.sql src/estudiantes/lectura.py tests/test_lectura_modulo.py
git commit -m "feat(supabase): corridas por módulo; el público solo lee la última publicada de cada módulo

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

> **Despliegue:** la migración la corre el usuario en el SQL Editor **antes** de fusionar el PR. El código nuevo funciona también sin ella (el filtro por módulo usa una columna que ya existe).

---

### Task 8: Vista comunidad: grupos, filtros y comparaciones sobre la base

**Files:** Modify `src/ui/views/estudiantes_comunidad.py`; Test `tests/test_estudiantes_comunidad.py` (añadir)

- [ ] **Step 1: Pruebas**

```python
# al final de tests/test_estudiantes_comunidad.py
def test_grupos_publicables_por_colegio(analisis):
    assert vc.grupos_publicables(analisis, "Grado", "LauV") == ["Séptimo", "Octavo"]
    assert vc.grupos_publicables(analisis, "Colegio") == ["LauV"]
    assert vc.grupos_publicables(analisis, "Grado", COLEGIO_PEQUENO) == []


def test_la_comparacion_por_grado_dentro_de_un_colegio(analisis):
    tabla = vc.prevalencia_por(analisis, "sdq_alto", "Grado", {"colegio": "LauV"})
    assert list(tabla["grupo"]) == ["Séptimo", "Octavo"]
    assert (tabla["n"] == 31).all()


def test_el_colegio_no_incluye_su_grado_pequeno(analisis):
    assert vc.bandas_sdq_total(analisis, {"colegio": "LauV"})["n"] == 62


def test_la_nota_de_base_cuenta_lo_que_queda_fuera(analisis):
    assert vc.nota_base(analisis) and "8" in vc.nota_base(analisis)
```

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_comunidad.py -q -k "publicables or dentro or pequeno or nota_base"`
Expected: FAIL.

- [ ] **Step 3: Implementar**

Import: `from src.estudiantes import privacidad`.

Nuevas funciones, tras `grupos_visibles`:

```python
def _ordenar(analisis, columna: str, grupos: list[str]) -> list[str]:
    if columna == "Grado":
        orden = (cat.ORDEN_GRADOS_SEC if analisis.nivel == cat.NIVEL_SECUNDARIA
                 else cat.ORDEN_GRADOS_PRI)
        return [g for g in orden if g in grupos] + sorted(g for g in grupos if g not in orden)
    return sorted(grupos)


def grupos_publicables(analisis, columna: str, otra=TODOS) -> list[str]:
    """Grupos de `columna` con cifras publicables, dentro del filtro de la otra dimensión.

    Con datos crudos se leen de la base publicable; con la corrida publicada, de
    los subgrupos que llegaron. Es la misma lista en los dos casos.
    """
    if analisis is None:
        return []
    pos = 0 if columna == "Colegio" else 1
    base = getattr(analisis, "base", None)
    if base is not None and hay_datos_crudos(analisis):
        if not privacidad._activo(otra):
            grupos = list((base.colegios if columna == "Colegio" else base.grados).keys())
        else:
            grupos = [privacidad.partir_celda(k)[pos] for k in base.celdas
                      if privacidad.partir_celda(k)[1 - pos] == str(otra)]
    else:
        sub = getattr(analisis, "subgrupos", None) or {}
        if not privacidad._activo(otra):
            grupos = list((sub.get(columna) or {}).keys())
        else:
            grupos = [privacidad.partir_celda(k)[pos]
                      for k in (sub.get(privacidad.AGRUPACION_CRUCE) or {})
                      if privacidad.partir_celda(k)[1 - pos] == str(otra)]
    return _ordenar(analisis, columna, grupos)


NOTA_BASE = ("Las cifras por colegio y por grado se calculan sobre los grupos de "
             f"{cat.MIN_GROUP_N} o más estudiantes; {{n}} respuestas de grupos más "
             "pequeños cuentan solo en el total del nivel.")


def nota_base(analisis) -> str:
    fuera = (((getattr(analisis, "muestra", None) or {}).get("base") or {})
             .get("n_fuera_de_celdas"))
    if fuera in (None, 0, "0"):
        return ""
    return NOTA_BASE.format(n=fuera)
```

`grupos_visibles` usa la base cuando la hay. Al inicio de la función, tras calcular `conteo` y `claves` (antes de `def suficiente`):

```python
    if getattr(analisis, "base", None) is not None or \
            (getattr(analisis, "subgrupos", None) or {}).get(columna):
        visibles = grupos_publicables(analisis, columna)
        return visibles, [g for g in claves if g not in visibles]
```

`subconjunto`:

```python
def subconjunto(analisis, filtros: dict) -> pd.DataFrame:
    """Filas del grupo elegido, sobre la base publicable si existe."""
    d = analisis.datos
    base = getattr(analisis, "base", None)
    if base is not None:
        return privacidad.filas(d, base, (filtros or {}).get("colegio", TODOS),
                                (filtros or {}).get("grado", TODOS))
    for columna in ("Colegio", "Grado"):
        valor = (filtros or {}).get(columna.lower(), TODOS)
        if valor and valor != TODOS and columna in d.columns:
            d = d[d[columna] == valor]
    return d
```

`subanalisis`:

```python
def subanalisis(analisis, filtros: dict | None):
    """El `Analisis` publicado del colegio, del grado o de la celda colegio×grado, o None."""
    activos = _filtros_activos(filtros or {})
    if not activos or analisis is None:
        return None
    sub = getattr(analisis, "subgrupos", None) or {}
    if len(activos) == 2:
        clave = privacidad.clave_celda(activos["Colegio"], activos["Grado"])
        return (sub.get(privacidad.AGRUPACION_CRUCE) or {}).get(clave)
    (columna, grupo), = activos.items()
    return (sub.get(columna) or {}).get(str(grupo))
```

`prevalencia_por` (rama con datos crudos) y `_prevalencia_por_publicada`:

```python
def prevalencia_por(analisis, indicador: str, columna: str,
                    filtros: dict | None = None) -> pd.DataFrame:
    """Prevalencia del indicador por nivel de `columna`, sobre la base publicable."""
    cfg = INDICADORES.get(indicador)
    if cfg is None or analisis is None:
        return pd.DataFrame()
    if not hay_datos_crudos(analisis):
        return _prevalencia_por_publicada(analisis, indicador, columna, filtros or {})
    filtros = filtros or {}
    base = getattr(analisis, "base", None)
    if base is not None and columna in ("Colegio", "Grado"):
        otra = "grado" if columna == "Colegio" else "colegio"
        valor_otra = filtros.get(otra, TODOS)
        grupos = grupos_publicables(analisis, columna, valor_otra)
        propio = filtros.get(columna.lower(), TODOS)
        if privacidad._activo(propio):
            grupos = [g for g in grupos if g == str(propio)]
        partes = []
        for g in grupos:
            pedido = {columna.lower(): g, otra: valor_otra}
            partes.append(privacidad.filas(analisis.datos, base, pedido.get("colegio", TODOS),
                                           pedido.get("grado", TODOS)).assign(_grupo=g))
        if not partes:
            return pd.DataFrame()
        d = pd.concat(partes)
        mask = _mascara(d, cfg)
        return pd.DataFrame() if mask is None else \
            stats.prevalencia_por_grupo(d, mask, "_grupo", grupos)
    d = subconjunto(analisis, filtros)
    if columna not in d.columns:
        return pd.DataFrame()
    mask = _mascara(d, cfg)
    if mask is None:
        return pd.DataFrame()
    return stats.prevalencia_por_grupo(d, mask, columna)


def _prevalencia_por_publicada(analisis, indicador: str, columna: str,
                               filtros: dict) -> pd.DataFrame:
    """La comparación entre grupos leída de los subgrupos publicados (también el cruce)."""
    activos = _filtros_activos(filtros)
    otra = "Grado" if columna == "Colegio" else "Colegio"
    sub = getattr(analisis, "subgrupos", None) or {}
    if otra in activos:
        cruce = sub.get(privacidad.AGRUPACION_CRUCE) or {}
        def clave(g):
            return privacidad.clave_celda(*((g, activos[otra]) if columna == "Colegio"
                                            else (activos[otra], g)))
        pares = [(g, cruce.get(clave(g)))
                 for g in grupos_publicables(analisis, columna, activos[otra])]
    else:
        propios = sub.get(columna) or {}
        pares = [(g, propios.get(g)) for g in grupos_publicables(analisis, columna)]
    if columna in activos:
        pares = [(g, s) for g, s in pares if g == str(activos[columna])]
    filas = []
    for g, s in pares:
        p = prevalencia(s, indicador, {}) if s is not None else {}
        if p:
            filas.append(dict(grupo=g, n=p["n"], casos=round(p["n"] * p["pct"] / 100),
                              pct=p["pct"], ic_inf=p["ic_inf"], ic_sup=p["ic_sup"]))
    return pd.DataFrame(filas, columns=["grupo", "n", "casos", "pct", "ic_inf", "ic_sup"])
```

Selector y render. Sustituir `_selector_grupo`:

```python
def _selector_grupo(analisis, columna: str, etiqueta: str,
                    colegio: str = TODOS) -> tuple[str, list[str]]:
    """Selectbox con los grupos publicables; el de grado depende del colegio elegido."""
    _, pequenos = grupos_visibles(analisis, columna)
    opciones = grupos_publicables(analisis, columna,
                                  colegio if columna == "Grado" else TODOS)
    if not opciones:
        return TODOS, pequenos
    clave = f"est_com_{columna.lower()}"
    if st.session_state.get(clave, TODOS) not in [TODOS] + opciones:
        st.session_state[clave] = TODOS     # el grado elegido no existe en este colegio
    valor = st.sidebar.selectbox(etiqueta, [TODOS] + opciones, key=clave)
    return valor, pequenos
```

En `render_comunidad`, la llamada al selector de grado:

```python
    grado, peq_grado = _selector_grupo(a, "Grado", "Grado", colegio=colegio)
```

Y tras el gráfico de bandas (dentro de `if b:`):

```python
        if hay_filtro(filtros) and nota_base(a):
            st.caption(nota_base(a))
```

Texto del aviso de subgrupo:

```python
SIN_SUBGRUPO_PUBLICADO = (
    "Estas cifras vienen de la corrida publicada, que trae resultados por colegio y por "
    "grado, y por grado dentro de cada colegio, solo para grupos de "
    f"{cat.MIN_GROUP_N} o más estudiantes. Este grupo no llega a ese mínimo, o la "
    "corrida es anterior y no traía el cruce.")
```

- [ ] **Step 4: Correr la suite de estudiantes**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_comunidad.py tests/test_estudiantes_subgrupos.py tests/test_estudiantes_lectura.py tests/test_estudiantes_informe.py -q`
Expected: PASS. Si `test_sin_datos_crudos_solo_se_filtra_por_lo_publicado` (lectura) falla, comprobar que el cruce que usa (`grado "8"`) no existe: debe seguir devolviendo `{}`.

- [ ] **Step 5: Commit**

```bash
git add src/ui/views/estudiantes_comunidad.py tests/test_estudiantes_comunidad.py
git commit -m "feat(comunidad): grado dentro de un colegio en local y en el despliegue, sobre la base publicable

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Informes con el grado dentro del colegio en el despliegue

**Files:** Modify `src/ui/views/estudiantes_informe.py` (`colegios_del_nivel`, `informe_colegio_html`, `_avisos`); Test `tests/test_estudiantes_informe.py`

- [ ] **Step 1: Prueba**

```python
# al final de tests/test_estudiantes_informe.py
def test_el_informe_del_colegio_trae_sus_grados_tambien_publicado(fuente):
    html = inf.informe_colegio_html(fuente, COLEGIO)
    assert "Por grado en el colegio" in html
    assert "Séptimo" in html and "Octavo" in html
    assert GRADO_PEQUENO not in html
```

- [ ] **Step 2: Verificar que falla (rama `publicado`)**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_informe.py -q -k sus_grados`
Expected: FAIL en `[publicado]`.

- [ ] **Step 3: Implementar**

`colegios_del_nivel`:

```python
def colegios_del_nivel(analisis) -> list[str]:
    """Colegios del nivel con cifras publicables (base o subgrupos publicados)."""
    if analisis is None:
        return []
    return [g for g in vc.grupos_publicables(analisis, "Colegio") if g not in EXCLUIDOS]
```

En `informe_colegio_html`, quitar la condición `if vc.hay_datos_crudos(a):` y dejar siempre:

```python
        grados = _tabla_comparativa(
            a, "Grado", COLUMNAS_GRADO_COLEGIO, filtros, "Por grado en el colegio",
            lambda g: g, nota="Los grados con menos de "
            f"{cat.MIN_GROUP_N} estudiantes no se muestran.")
```

En `_avisos(niveles)`, añadir parámetro opcional y la nota de base:

```python
def _avisos(niveles: list[str], notas: list[str] | None = None) -> str:
    textos = [cat.AVISO_TAMIZAJE, NOTA_COMPARACION, *[n for n in (notas or []) if n]]
    if cat.NIVEL_PRIMARIA in niveles:
        textos.append(cat.AVISO_PRIMARIA)
    textos.append(cat.AVISO_NORMAS)
    return '<footer class="avisos">' + "".join(f"<p>{_e(t)}</p>" for t in textos) + "</footer>"
```

Y en `informe_colegio_html` e `informe_secretaria_html`, la llamada final:

```python
_avisos(niveles, [vc.nota_base(analisis[n]) for n in niveles])
```

- [ ] **Step 4: Correr pruebas**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_informe.py -q`
Expected: PASS (incluido el PDF de una página).

- [ ] **Step 5: Commit**

```bash
git add src/ui/views/estudiantes_informe.py tests/test_estudiantes_informe.py
git commit -m "feat(informes): grados dentro del colegio también con la corrida publicada

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Pestaña de muestra: colegio × grado con válidas y respuestas

**Files:** Modify `src/ui/views/estudiantes_investigador.py` (`_tab_muestra`); Test `tests/test_estudiantes_investigador.py`

- [ ] **Step 1: Prueba**

```python
# al final de tests/test_estudiantes_investigador.py
def test_tabla_colegio_grado_reconcilia_validas_y_respuestas():
    from src.ui.views import estudiantes_investigador as vi
    t = vi.tabla_colegio_grado({"LauV|Octavo": 91, "CdP|Décimo": "<10"},
                               {"LauV|Octavo": 93, "CdP|Décimo": 6},
                               ["Sexto", "Octavo", "Décimo"])
    assert list(t.columns) == ["Colegio", "Grado", "Válidas", "Respuestas"]
    fila = t[(t.Colegio == "Laura Vicuña") & (t.Grado == "Octavo")].iloc[0]
    assert fila["Válidas"] == "91" and fila["Respuestas"] == "93"
    pequena = t[t.Grado == "Décimo"].iloc[0]
    assert pequena["Válidas"] == "<10" and pequena["Respuestas"] == "<10"
```

- [ ] **Step 2: Verificar que falla**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_investigador.py -q -k colegio_grado`
Expected: FAIL.

- [ ] **Step 3: Implementar**

```python
def tabla_colegio_grado(validas: dict, crudas: dict, orden_grados: list[str]) -> pd.DataFrame:
    """Colegio × grado: válidas (entran al análisis) y respuestas (filas del formulario).

    Los conteos por debajo del mínimo se muestran como «<10» en las dos columnas,
    aunque la corrida local tenga la cifra exacta: esta tabla se ve igual en
    local y en el despliegue.
    """
    from src.core.colegios import nombre
    from src.estudiantes.privacidad import partir_celda

    def texto(v):
        try:
            return str(int(v)) if float(v) >= cat.MIN_GROUP_N else f"<{cat.MIN_GROUP_N}"
        except (TypeError, ValueError):
            return f"<{cat.MIN_GROUP_N}"

    claves = sorted(set(validas) | set(crudas),
                    key=lambda k: (nombre(partir_celda(k)[0]),
                                   orden_grados.index(partir_celda(k)[1])
                                   if partir_celda(k)[1] in orden_grados else 99))
    filas = []
    for k in claves:
        colegio, grado = partir_celda(k)
        v = validas.get(k)
        filas.append({"Colegio": nombre(colegio), "Grado": grado,
                      "Válidas": texto(v) if v is not None else "0",
                      "Respuestas": texto(crudas[k]) if k in crudas else "—"})
    return pd.DataFrame(filas, columns=["Colegio", "Grado", "Válidas", "Respuestas"])
```

En `_tab_muestra`, dentro de `with c2:` tras la tabla de Colegio:

```python
        cg = m.get("colegio_grado") or {}
        if cg:
            crudas = (getattr(informe, "crudo_colegio_grado", None)
                      or getattr(informe, "datos", {}).get("crudo_colegio_grado", {})
                      if informe is not None else {})
            st.markdown("**Colegio × grado**")
            st.dataframe(tabla_colegio_grado(cg, crudas or {}, orden),
                         hide_index=True, width="stretch")
            st.caption("«Válidas» entran al análisis; «Respuestas» son las filas del "
                       "formulario antes de limpiar (consentimiento, pruebas y duplicados). "
                       "La sede no separa grupos: San Josemaría suma sus sedes.")
```

> Comprobar cómo `InformeLeido` (lectura.py) expone los campos de ingesta: si es por atributo, el `getattr` basta; si guarda un dict, ajustar a ese nombre. El objetivo es el mismo dict «colegio|grado → n».

- [ ] **Step 4: Correr pruebas**

Run: `./venv/bin/python -m pytest tests/test_estudiantes_investigador.py tests/test_estudiantes_lectura.py -q`
Expected: PASS (incluida la conversión a Arrow de las tablas).

- [ ] **Step 5: Commit**

```bash
git add src/ui/views/estudiantes_investigador.py tests/test_estudiantes_investigador.py
git commit -m "feat(investigador): tabla colegio×grado con válidas y respuestas

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Aceptación con datos reales

**Files:** Create `tests/test_aceptacion_grados.py`

- [ ] **Step 1: Prueba con la lista de los investigadores (conteos crudos)**

```python
# tests/test_aceptacion_grados.py
"""Lista de los investigadores (6-oct-2026), sobre conteos crudos del formulario.

Solo se comprueban los colegios cuyos datos ya llegaron completos; al recibir la
exportación nueva de secundaria se añaden CdP, JJC y SJMEB.
"""
import pytest

from src.core.rutas import carpeta_datos
from src.estudiantes import pipeline, publicar, privacidad
from src.ui.views import estudiantes_comunidad as vc

LISTA = {
    "secundaria": {"LaBalsa": {"Sexto": 24, "Séptimo": 52, "Noveno": 29, "Décimo": 32},
                   "LauV": {"Sexto": 95, "Séptimo": 69, "Octavo": 93, "Noveno": 90,
                            "Décimo": 90}},
    "primaria": {"LauV": {"Cuarto": 86, "Quinto": 98}},
}


@pytest.fixture(scope="module")
def real():
    rutas = pipeline.localizar_formularios(carpeta_datos("estudiantes"))
    if len(rutas) < 2:
        pytest.skip("faltan los formularios")
    return pipeline.cargar_y_analizar(rutas, n_boot=20)


def test_los_conteos_crudos_coinciden_con_la_lista(real):
    _, informes = real
    crudos = {i.nivel: i.crudo_colegio_grado for i in informes}
    for nivel, colegios in LISTA.items():
        for colegio, grados in colegios.items():
            for grado, n in grados.items():
                assert crudos[nivel][privacidad.clave_celda(colegio, grado)] == n, \
                    f"{nivel} {colegio} {grado}"


def test_todos_esos_grados_se_ven_dentro_de_su_colegio(real):
    analisis, _ = real
    for nivel, colegios in LISTA.items():
        for colegio, grados in colegios.items():
            visibles = vc.grupos_publicables(analisis[nivel], "Grado", colegio)
            assert set(grados) <= set(visibles), f"{nivel} {colegio}: {visibles}"


def test_la_auditoria_de_restas_pasa_con_los_datos_reales(real):
    analisis, _ = real
    assert publicar.verificar_restas(analisis) == []
```

- [ ] **Step 2: Correr**

Run: `./venv/bin/python -m pytest tests/test_aceptacion_grados.py -v`
Expected: PASS. Si la auditoría falla, **no tocar la prueba**: el mensaje dice qué indicador y qué grupo; aplicar la regla «todo o nada por celda» (spec §5.1.3) a ese indicador y documentarlo.

- [ ] **Step 3: Ensayo del publicador**

Run: `./venv/bin/python -m src.estudiantes.publicar --ensayo --salida /private/tmp/claude-501/lote_fase1.json`
Expected: sin «AVISO: la auditoría…»; el JSON contiene filas con `"agrupacion": "Colegio×Grado"`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_aceptacion_grados.py
git commit -m "test(aceptacion): la lista de grados de los investigadores se ve y nada es deducible

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Verificación de punta a punta y PR

- [ ] **Step 1: Suite completa**

Run: `./venv/bin/python -m pytest tests/ -q`
Expected: todo en verde salvo las 2 fallas conocidas de `test_knowledge_base`.

- [ ] **Step 2: Playwright (modo comunidad leyendo un lote local)**

Levantar `OBS360_MODO=comunidad streamlit run main.py --server.port 8611` con los formularios en disco y `OBS360_MODO=completo` en 8612. Con el script de revisión (`scratchpad/revision.js`, ampliado) comprobar:
1. Rol colegio, elegir **Laura Vicuña**: el selector de grado ofrece Sexto…Décimo; al elegir **Octavo** aparecen bandas y tarjetas con n = 91.
2. «Comparar entre grupos → Grado» con Laura Vicuña elegido muestra los 5 grados.
3. Cambiar a **La Balsa** con Octavo elegido: el grado vuelve a «Todos» sin error (La Balsa no tiene octavo).
4. El informe del colegio trae «Por grado en el colegio».
5. Investigadores → Muestra: tabla colegio × grado con «Válidas / Respuestas».
6. Sin excepciones de Streamlit en ninguna página.

- [ ] **Step 3: Push y PR (base: `feature/informe-estudiantes-html` hasta que el PR #1 se fusione; luego `main`)**

```bash
git push -u origin feature/360-cuidadores-alertas-triangulacion
gh pr create --base feature/informe-estudiantes-html --title "Fase 1: grados dentro del colegio y privacidad por resta" --body "…resumen de la fase, pruebas, Playwright, y la migración SQL que hay que correr antes de fusionar…

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 4: Avisar al usuario** que corra `supabase/migraciones/2026-10-07-modulo-y-ultima-corrida.sql` y, después, publique una corrida nueva (`python -m src.estudiantes.publicar --notas "fase 1"` y aprobarla) para que el despliegue muestre el cruce.
