# Fase 4a · Cuidadores 360: carga, puntuación y vista de investigadores — plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** el equipo investigador ve, en local y solo en los modos completo e investigador, el formulario «Cuidando al Cuidador» cargado sin nombres ni teléfonos, puntuado desde el texto crudo (PSS-10, EPDS-10, MSPSS del cuidador, riesgo del barrio, castigo físico, SDQ y ARI de padres) y analizado en dos marcos (**cuidadores** y **niños**) con la misma base publicable y la misma supresión de cifras pequeñas que estudiantes. La página tiene las pestañas de la vista de investigadores de estudiantes, un filtro de ola que solo existe en local y un paquete ZIP agregado y anónimo. El despliegue público no ve ni importa nada de cuidadores.

**Fuera de alcance (fase 4b):** vista de comunidad, tarjetas y sus textos (`MENSAJES`), informes, publicación en Supabase (`publicar.py`, `lectura.py` con `modulo = "cuidadores"`) y habilitación pública. Esta fase deja las interfaces para que 4b se enchufe sin tocar lo de aquí (ver «Interfaces para la 4b»).

**Arquitectura.** Todo lo nuevo vive en **módulos nuevos**, que Streamlit Cloud siempre importa frescos:

| Módulo nuevo | Qué contiene |
|---|---|
| `src/core/seudonimo.py` | HMAC-SHA256 con la clave local `OBS360_CLAVE_HMAC`: `C` + 8 hex (cuidador), `N` + 8 hex (niño), `E` (estudiante, para la fase 5). Sin clave: `ClaveAusente` con un mensaje claro. No hay clave en el código |
| `src/cuidadores/catalog.py` | Columnas por posición con verificación de encabezado, mapas texto → número explícitos (la EPDS, uno por ítem), puntuaciones, señales del adulto, avisos fijos y las claves de las tarjetas de la 4b |
| `src/cuidadores/ingest.py` | Lectura como texto, verificación del formato, consentimiento, seudónimos, colegio vía `core.colegios`, edad, curso libre → grado, ola, hijo 2 y deduplicación |
| `src/cuidadores/scoring.py` | Puntuaciones y tablas con la **misma forma** que las de estudiantes (`sobre_cortes`, `distribucion_bandas`, `descriptivos`, `terciles`, `fiabilidad`) |
| `src/cuidadores/privacidad.py` | Base publicable y todo o nada que cuentan **cuidadores distintos**; devuelve un `estudiantes.privacidad.Base` |
| `src/cuidadores/pipeline.py` | `AnalisisCuidadores` con `cuidador` y `nino`, cada uno un `estudiantes.pipeline.Analisis` pasado por `estudiantes.supresion.aplicar` |
| `src/ui/cuidadores.py`, `src/ui/views/cuidadores_investigador.py` | Página (archivo local, clave, filtro de ola) y vista de investigadores |

**Reutilización sin tocar estudiantes.** Cada marco es un `estudiantes.pipeline.Analisis` con `cortes`, `bandas` y `subgrupos` en el formato de estudiantes. Así `estudiantes.supresion.aplicar` (supresión primaria `3 ≤ casos ≤ n − 3`, complementaria y auditoría exacta de sumas y restas) se aplica tal cual, y la 4b podrá reutilizar el aplanado de `publicar`. **Ningún archivo de `src/estudiantes/` cambia** (la Task 12 lo comprueba con `git diff` y con el lote real del ensayo de estudiantes, byte a byte).

**Módulos rancios.** Solo cambian dos archivos existentes: `src/core/navegacion.py` (un símbolo nuevo, `CUIDADORES_PUBLICO`, que solo lee el propio módulo) y `main.py` (usa `nav.PAGINA_CUIDADORES`, que ya existía). Con un `navegacion` viejo en memoria la página simplemente no aparece hasta el «Reboot app»; nada se cae.

**Tech stack:** Python 3.13 local / 3.14 en Streamlit Cloud, pandas (2.x local, 3.x en 3.14), numpy, scipy, Streamlit (`AppTest`), pytest, openpyxl y Playwright MCP.

**Spec:** `docs/superpowers/specs/2026-10-06-cuidadores-alertas-triangulacion-design.md`: §3.2, §4, §5.1, §5.2 y §5.5 (solo la 4a), con §7 y §8.

**Restricciones que no se negocian:**
- **Nada individual.**
  - Los nombres (posiciones 3, 4 y 147) solo se leen para el seudónimo y nunca se copian. El teléfono (179) y el nombre de un tercer hijo (208) no se leen.
  - Ningún grupo con menos de 10 **cuidadores distintos**, también en el marco de niños.
  - Ninguna proporción con menos de 3 casos o no casos, ni deducible por resta.
  - Ninguna tabla mostrada o exportada lleva `casos`, conteos por banda, seudónimos ni filas.
- **Clave local.** `OBS360_CLAVE_HMAC` vive en el entorno o en `.streamlit/secrets.toml` (ignorado por git). Las pruebas usan su propia clave de prueba. Nunca se imprime, nunca se escribe en el repositorio y nunca va en los secretos de un despliegue.
- **Datos reales.**
  - Nunca se abren a mano los archivos de `../datos_fuente_360` (datos de adultos y de menores). `Datos_Cuidador_corregido.csv` no se abre (codificación heredada defectuosa).
  - Las pruebas reales se omiten si falta el archivo y solo comparan agregados. Sus mensajes de fallo nunca muestran valores (`assert n == 0`, nunca una lista).
  - Ningún comando de este plan imprime filas, nombres, teléfonos ni texto libre.
- **Solo local en 4a.** Nada sube a Supabase. En los despliegues la página dice «Cuidadores aún no está publicado». En comunidad no aparece en el menú (`CUIDADORES_PUBLICO = False`) y `main.py` no importa nada de cuidadores antes del corte público.
- **Textos fijos y provisionales** (`catalog.TEXTOS_APROBADOS = False`). Nunca los redacta la IA.
- **Git.**
  - La rama `feature/fase4a-cuidadores` ya existe (sale de `main` con las fases 1 a 3 y la supresión) y ya trae este plan: no se crea ni se cambia de rama.
  - Nunca `git add -A`: siempre los archivos por nombre. Los dos `.docx` sin seguimiento de la raíz no se tocan.
  - No se hace `push` hasta la Task 14 y no se fusiona sin permiso del usuario.
- Cada commit termina con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

**Comandos de prueba** (desde la raíz del repo):
- Python 3.13: `.venv/bin/python -m pytest -q`. Línea base al empezar: **674 passed, 4 skipped**.
- Python 3.14 con WeasyPrint (producción): `"$VENV314/bin/python" -m pytest -q`. Línea base: **678 passed**. Con

  ```bash
  VENV314=/private/tmp/claude-501/-Users-joseamorocho-Documents-app-360-observatorio-SaludOrganizacional/73d67104-c128-41eb-b044-923af344a71f/scratchpad/venv314
  ```

  Si ese directorio ya no existe (el scratchpad es de la sesión), se recrea como en la Task 12, Step 1.

---

## Decisiones de diseño (tomadas en este plan; las que necesitan al equipo están en «Preguntas abiertas»)

| Tema | Decisión |
|---|---|
| Lectura | Por **posición** (spec §3.2), con `VERIFICAR`: un fragmento normalizado del encabezado por posición clave. Si Google Forms reordena, la carga falla con «En la columna N se esperaba…», nunca puntúa la columna equivocada. Todo se lee como texto (`dtype=str`) y se convierte en el catálogo |
| Seudónimos | `HMAC-SHA256(clave, f"{letra}|{norm_txt(nombre)}")`, primeros 8 hex. La letra va dentro del mensaje: el mismo nombre da seudónimos distintos como cuidador y como niño, y la fase 5 enlazará niño y estudiante calculando los dos con `N`. Sin nombre: `sin-nombre-…` (no se deduplica; hoy no hay ninguno) |
| Clave | `OBS360_CLAVE_HMAC` en el entorno o en `st.secrets`, al menos 16 caracteres. Si falta: `ClaveAusente`, que la página muestra como un error explicado. Como los seudónimos no se guardan ni se publican, perder la clave solo obliga a crear otra |
| Colegio | `core.colegios.normalizar`. «OTRO» se guarda como «Otro colegio» (el texto libre no viaja). «OTRO» y «SIN_DATO» **nunca forman grupo**: solo cuentan en el total |
| Colegio y grado del cuidador | Los de su **hijo 1** (el primero que reporta) |
| Ola | Año calendario de la marca temporal: «2025» (sep-2025) y «2026» (mar–sep 2026). La marca se lee en ISO (xlsx) o día/mes/año (csv) |
| Edad del niño | Un entero de 1 o 2 cifras, con «años» opcional («10 años» → 10). Lo demás («diez», «10 años 5 meses») es «no numérica» → faltante. Una edad numérica fuera de 4–17 → faltante y **su SDQ queda faltante**; con edad no numérica el SDQ se puntúa (casi todos están en grados del estudio) y se declara aparte |
| Curso → grado | En orden: (1) palabra de grado en cualquier parte («Sexto 602» → Sexto); (2) número de 1 o 2 cifras con o sin sufijo («5A», «4to», «8vo», «5°», «5-2» → su primer número); (3) código de 3–4 cifras grado + grupo 01–20 («501» → Quinto, «1002» → Décimo). Grados del estudio: cuarto a décimo, con los nombres de estudiantes. Transición/jardín, primero a tercero y once: «fuera del rango del estudio» (`Grado` vacío, `Grado_detalle` con el nombre). Lo demás: «Sin dato» |
| Quién responde | Mamá, Papá u Otro cuidador (otro cuidador principal, tío o tía, abuelo o abuela) |
| Deduplicación | **Cuidadores:** la respuesta más reciente por `ID_cuidador` (si empatan, el último envío). **Niños:** ola más reciente → mamá, papá, otro → primer envío → hijo 1 antes que hijo 2 (cubre el caso real del mismo niño como hijo 1 y 2 en un envío). El filtro de ola se aplica **antes** de deduplicar |
| Marcos | `cuidador`: una fila por cuidador distinto (PSS, EPDS, MSPSS, barrio, APQ, estrés parental). `nino`: una fila por niño distinto (SDQ y ARI de padres) con el `ID_cuidador` de quien quedó. Ambos son `estudiantes.pipeline.Analisis` (`nivel` = «cuidador» / «nino») |
| Mínimo de 10 | `cuidadores.privacidad` cuenta `nunique(ID_cuidador)` en celdas, colegios, grados, resto y todo o nada. Con una fila por cuidador da exactamente la base de estudiantes (hay prueba) |
| Proporciones | `estudiantes.supresion.aplicar` sobre cada marco. Los dos cortes de la EPDS (≥ 10, ≥ 13) comparten la clave `EPDS_Total` y se suprimen como cortes anidados (tres partes). Las bandas del SDQ de padres y su corte «alto o muy alto» van juntos, como en estudiantes |
| PSS-10 | 0–4 («Nunca» … «Casi siempre», el mapa de docentes), inversos 3, 4, 5, 7 y 9, suma 0–40 prorrateada con 9 de 10 ítems. «Columna 6» = faltante declarado (se cuenta aparte, no como etiqueta desconocida). Sin corte: terciles |
| EPDS-10 | Por texto, un mapa por ítem (ítems 3 y 5–10 al revés del orden de las opciones; se aceptan las erratas del formulario y su forma corregida). Total con los 10 ítems, sin prorrateo. Ánimo posible ≥ 10, probable ≥ 13. Autolesión: ítem 10 ≥ 1 («Casi nunca» o más), calculada aunque falte otro ítem |
| MSPSS | Media 1–5 por fuente con todos sus ítems: persona especial 1–5, familia 6–9, amigos 10–12; total con los 12. Corte descriptivo «media < 3» como en estudiantes |
| APQ | Ítems 1–5 («Nunca» … «Siempre»). `APQ_Fisico` = alguno de 22–24 (columnas 78–80) ≥ 3 («A veces»), con los tres respondidos. `APQ_Grito` (25, columna 81) ≥ 3, descriptivo. Sin subescalas |
| Estrés parental | Ítems 1–5 («Muy en desacuerdo» … «Muy de acuerdo»). **Sin total ni subescalas.** Solo, en la vista local, n, media y % «de acuerdo o más» por ítem, con las notas «elección forzada partida» (22–26 = columnas 103–107) y «redactado en positivo» (36 = columna 117) |
| SDQ de padres | Subescalas, compuestas y prorrateo de estudiantes (`estudiantes.scoring.items_orientados`), bandas `BANDS_PARENT` |
| ARI de padres | «No es cierto» 0, «A veces cierto» 1, «Cierto» 2. Total ítems 1–6 (0–12, completos) y deterioro (ítem 7). **Sin corte** (el de > 2 es de autoinforme); cobertura parcial declarada |
| Barrio | 5 ítems 0–2 («No», «Sí, pero con baja frecuencia», «Sí, es muy frecuente»), índice 0–10 con los 5. Terciles |
| Ítems locales | `items_apq` e `items_estres` solo en la vista local; el % se borra donde hay menos de 3 casos o no casos y la columna `casos` nunca sale. No van al ZIP |
| Pestañas | Las de estudiantes donde tienen sentido: Muestra y exclusiones · Tabla 1 · Cortes y bandas · Correlaciones · Por grupo · **Señales del adulto** (en lugar de Alertas) · **Ítems sin puntaje** (en lugar de Modelos, que se dejan para la triangulación) · Calidad de datos · Exportar. Un selector de marco (cuidadores / niños) hace de selector de nivel |
| Conteos en pantalla | Los conteos por grupo de la pestaña de muestra se muestran como «<10» por debajo del mínimo, en local también |
| ZIP | `tabla1_descriptivos.csv`, `cortes_y_bandas.csv`, `cortes_por_grupo.csv`, `correlaciones_bh.csv`, `comparaciones_grupo.csv`, `flujo_exclusiones.md`, `metodologia.md`, `version_analisis.txt`. Sin `casos`, `n_b*`, seudónimos ni filas |
| Navegación | `PAGINA_CUIDADORES` entra en `DISPONIBLES`; `menu()` lo quita del modo público mientras `CUIDADORES_PUBLICO = False`. `main.py` lo enruta solo en la rama no pública |
| Sin archivo | La página dice «Cuidadores aún no está publicado…» y no falla (despliegue del equipo) |

### Interfaces para la 4b

- `pipeline.AnalisisCuidadores.marcos` → `{"cuidador": Analisis, "nino": Analisis}`, ya con supresión: el aplanado de `estudiantes.publicar` puede recorrerlos con `modulo = "cuidadores"` y `nivel` = marco.
- `catalog.TARJETAS_4B` (las 6 tarjetas de la spec, en orden), `catalog.ALERTAS` (ánimo y autolesión con su columna 0/1 por cuidador) y `catalog.ruta_adulto(rol)` (hoy delega en `estudiantes.alertas_catalogo.ruta(rol, "adulto")`).
- `navegacion.CUIDADORES_PUBLICO`: la 4b lo pone en `True` cuando el equipo apruebe textos y rutas y haya una corrida publicada, y añade la rama pública en `main.py`.
- `cuidadores.privacidad.base_publicable` devuelve un `estudiantes.privacidad.Base`: `filas`, `relaciones`, `auditar` y `supresion` lo aceptan.

---

## Mapa de archivos

| Archivo | Qué cambia |
|---|---|
| `src/core/seudonimo.py` (nuevo) | `VARIABLE`, `ClaveAusente`, `clave()`, `seudonimo(texto, letra, k=None)` |
| `src/cuidadores/__init__.py` (nuevo) | Docstring del paquete |
| `src/cuidadores/catalog.py` (nuevo) | Posiciones, `VERIFICAR`, mapas, `Bloque`, bloques, grados, puntuaciones, `ALERTAS`, `ruta_adulto`, `TARJETAS_4B`, avisos |
| `src/cuidadores/ingest.py` (nuevo) | `FormatoInesperado`, `InformeCuidadores`, `Carga`, `leer`, `verificar_formato`, `enunciado`, `mapear_bloque`, `edad`, `numero_de_grado`, `grado_desde_curso`, `quien`, `fecha`, `cargar`, `deduplicar` |
| `src/cuidadores/scoring.py` (nuevo) | `puntuar_cuidadores`, `puntuar_ninos`, `descriptivos`, `fiabilidad`, `sobre_cortes_cuidador`, `sobre_cortes_nino`, `bandas_nino`, `terciles`, `distribucion_items` |
| `src/cuidadores/privacidad.py` (nuevo) | `base_publicable`, `aplicar_todo_o_nada`, `columnas_de_analisis`, `distintos_por_grupo` |
| `src/cuidadores/pipeline.py` (nuevo) | `AnalisisCuidadores`, `localizar_formulario`, `analizar_marco`, `analizar`, `cargar_y_analizar` |
| `src/ui/views/cuidadores_investigador.py` (nuevo) | Tablas puras, paquete ZIP, pestañas y `render_investigador` |
| `src/ui/cuidadores.py` (nuevo) | `render_cuidadores`: archivo, clave, caché y filtro de ola |
| `src/core/navegacion.py` | `DISPONIBLES` con Cuidadores; `CUIDADORES_PUBLICO = False`; `menu()` lo respeta |
| `main.py` | Rama `PAGINA_CUIDADORES` después del corte público |
| `tests/cuidadores_sinteticos.py` (nuevo) | Formulario sintético con centinelas |
| `tests/test_seudonimo.py`, `tests/test_cuidadores_{catalogo,ingest,dedup,scoring,privacidad,pipeline,vista,pagina,reales}.py` (nuevos) | Pruebas |
| `tests/test_navegacion.py`, `tests/test_modo_despliegue.py` | Cuidadores en el menú de investigadores, nunca en comunidad; nada de cuidadores antes del corte |
| `DESPLIEGUE.md`, `ARCHITECTURE.md`, `secrets.toml.example` | Documentación |

**Lo que no cambia:** todo `src/estudiantes/`, `src/ui/estudiantes.py`, `src/ui/views/estudiantes_*.py`, `src/core/{colegios,modo,rutas,texto}.py`, Supabase.

---

### Task 0: Línea base y clave local

**Files:** ninguno del repositorio (la clave va a `.streamlit/secrets.toml`, ignorado por git).

- [ ] **Step 1: Comprobar la rama (ya existe; no se crea)**

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
git branch --show-current          # → feature/fase4a-cuidadores
git log --oneline -2               # → «docs(plan): fase 4a · cuidadores» sobre 4ecdd9a
git status --short                 # solo los dos .docx sin seguimiento; no se tocan
```

Si la rama no es `feature/fase4a-cuidadores` o el árbol tiene cambios propios, parar y avisar al usuario.

- [ ] **Step 2: Línea base**

Run: `.venv/bin/python -m pytest -q`
Expected: `674 passed, 4 skipped`.

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: `678 passed`. Anotar los totales para el PR.

- [ ] **Step 3: Foto del ensayo de estudiantes, fuera del repositorio**

Sirve para probar en la Task 12 que estudiantes no cambia. Solo agregados; si faltan los formularios, el comando falla y este paso se omite.

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_antes_4a.json" > /dev/null
echo "código de salida: $?"
```
Expected: `código de salida: 0`.

- [ ] **Step 4: Clave local para los seudónimos (sin imprimirla)**

`.streamlit/secrets.toml` está en `.gitignore`. Se inserta **al principio** del archivo (en TOML, una clave suelta después de una tabla `[…]` quedaría dentro de esa tabla). Si ya existe, no se toca.

```bash
git check-ignore -q .streamlit/secrets.toml && echo "ignorado por git"
.venv/bin/python - <<'EOF'
import pathlib, secrets
p = pathlib.Path(".streamlit/secrets.toml")
p.parent.mkdir(exist_ok=True)
texto = p.read_text(encoding="utf-8") if p.exists() else ""
if "OBS360_CLAVE_HMAC" in texto:
    print("la clave ya existía; no se toca")
else:
    p.write_text(f'OBS360_CLAVE_HMAC = "{secrets.token_hex(32)}"\n' + texto, encoding="utf-8")
    print("clave creada (no se muestra)")
EOF
grep -c "^OBS360_CLAVE_HMAC" .streamlit/secrets.toml
```
Expected: `ignorado por git`, uno de los dos mensajes y `1`. Nunca hacer `cat` de ese archivo.

Sin commit.

---

### Task 1: Seudónimos con clave local

**Files:**
- Create: `src/core/seudonimo.py`
- Create: `tests/test_seudonimo.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_seudonimo.py`:

```python
"""Seudónimos HMAC con clave local (core/seudonimo.py)."""
import re

import pytest

from src.core import seudonimo as seud

CLAVE = "clave-de-prueba-solo-para-tests-0001"


@pytest.fixture
def con_clave(monkeypatch):
    monkeypatch.setenv(seud.VARIABLE, CLAVE)


def test_formato_del_check_de_supabase(con_clave):
    for letra in ("C", "N", "E"):
        s = seud.seudonimo("María Pérez", letra)
        assert re.fullmatch(r"^[ECN][0-9a-f]{8}$", s) and s[0] == letra


def test_normaliza_antes_de_firmar(con_clave):
    assert seud.seudonimo("  MARÍA   pérez ", "N") == seud.seudonimo("maria perez", "N")


def test_la_letra_separa_dominios(con_clave):
    assert seud.seudonimo("Ana", "C")[1:] != seud.seudonimo("Ana", "N")[1:]


def test_depende_de_la_clave():
    a = seud.seudonimo("Ana Ruiz", "C", b"una-clave-de-prueba-larga-0001")
    b = seud.seudonimo("Ana Ruiz", "C", b"otra-clave-de-prueba-larga-002")
    assert a != b


def test_vacio_no_tiene_seudonimo(con_clave):
    assert seud.seudonimo("", "C") is None and seud.seudonimo(None, "N") is None


def test_sin_clave_hay_un_error_claro(monkeypatch):
    monkeypatch.delenv(seud.VARIABLE, raising=False)
    monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    with pytest.raises(seud.ClaveAusente, match="OBS360_CLAVE_HMAC"):
        seud.seudonimo("Ana", "C")


def test_una_clave_corta_no_sirve(monkeypatch):
    monkeypatch.setenv(seud.VARIABLE, "corta")
    with pytest.raises(seud.ClaveAusente):
        seud.clave()


def test_letra_desconocida(con_clave):
    with pytest.raises(ValueError):
        seud.seudonimo("Ana", "X")


def test_no_hay_clave_escrita_en_el_codigo():
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parents[1]
    for f in (raiz / "src").rglob("*.py"):
        texto = f.read_text(encoding="utf-8")
        assert "clave-de-prueba" not in texto, f
```

Run: `.venv/bin/python -m pytest tests/test_seudonimo.py -q`
Expected: FAIL con `ImportError: cannot import name 'seudonimo' from 'src.core'`.

- [ ] **Step 2: Implementar**

`src/core/seudonimo.py`:

```python
"""
Seudónimos con clave local — Observatorio 360.

Un nombre propio se convierte en un identificador corto e irreversible con
HMAC-SHA256 y una clave que **solo existe en la máquina que procesa**:

    seudonimo("María Pérez", "C")  →  "C3fa91b07"

  · La letra dice qué es: «C» cuidador, «N» niño, «E» estudiante. Coincide con
    el `CHECK` de Supabase `^[ECN][0-9a-f]{8}$`.
  · El mensaje firmado lleva la letra («N|maria perez»): el mismo nombre da
    seudónimos distintos como cuidador y como niño, y la triangulación (fase 5)
    enlaza niño y estudiante calculando los dos con la letra «N».
  · Sin la clave no se puede recalcular ni comprobar un nombre, a diferencia
    del SHA-1 sin clave que usa hoy `estudiantes.ingest`.

La clave se lee de `OBS360_CLAVE_HMAC` (entorno o `.streamlit/secrets.toml`).
**No hay clave por defecto en el código.** Si falta, `ClaveAusente` explica qué
hacer. El despliegue público no la necesita: nunca procesa archivos crudos.

Este módulo es nuevo, así que tras un despliegue siempre se importa fresco.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from src.core.texto import norm_txt

VARIABLE = "OBS360_CLAVE_HMAC"
LARGO_MINIMO = 16
LETRAS = ("C", "N", "E")
LARGO_HEX = 8


class ClaveAusente(RuntimeError):
    """Falta la clave local para seudonimizar, o es demasiado corta."""


MENSAJE_CLAVE = (
    f"Falta la clave local `{VARIABLE}`, con la que los nombres se convierten en "
    "identificadores anónimos. Defínela en el entorno o en `.streamlit/secrets.toml` "
    f"(al menos {LARGO_MINIMO} caracteres, por ejemplo la salida de "
    "`python -c \"import secrets; print(secrets.token_hex(32))\"`). Guárdala fuera del "
    "repositorio y usa siempre la misma: si cambia, cambian todos los identificadores.")


def clave() -> bytes:
    """La clave local. Lanza `ClaveAusente` si no está o es corta."""
    valor = os.environ.get(VARIABLE, "").strip()
    if not valor:
        try:
            import streamlit as st
            valor = str(st.secrets.get(VARIABLE, "")).strip()
        except Exception:                                  # noqa: BLE001
            valor = ""
    if len(valor) < LARGO_MINIMO:
        raise ClaveAusente(MENSAJE_CLAVE)
    return valor.encode("utf-8")


def seudonimo(texto, letra: str, k: bytes | None = None) -> str | None:
    """Letra + 8 hexadecimales del HMAC-SHA256 del texto normalizado. None si vacío."""
    if letra not in LETRAS:
        raise ValueError(f"Letra de seudónimo desconocida: {letra!r}")
    normalizado = norm_txt(texto)
    if not normalizado:
        return None
    k = clave() if k is None else k
    firma = hmac.new(k, f"{letra}|{normalizado}".encode("utf-8"), hashlib.sha256)
    return letra + firma.hexdigest()[:LARGO_HEX]
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_seudonimo.py -q`
Expected: `9 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/core/seudonimo.py tests/test_seudonimo.py
git commit -m "feat(core): seudónimos HMAC con clave local" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Catálogo de cuidadores y formulario sintético

**Files:**
- Create: `src/cuidadores/__init__.py`, `src/cuidadores/catalog.py`
- Create: `tests/cuidadores_sinteticos.py` (no es un archivo de pruebas: lo importan las demás)
- Create: `tests/test_cuidadores_catalogo.py`

Los encabezados sintéticos se arman con los fragmentos de `VERIFICAR` y las respuestas con las etiquetas de opción del formulario (fijas, no datos personales). Las etiquetas de la EPDS y de las demás escalas se comprobaron contra el archivo real **solo como conjuntos de opciones** (conteos agregados por etiqueta, ver «Observaciones de los datos»): todas se mapean, ninguna queda sin convertir.

- [ ] **Step 1: Escribir el formulario sintético y las pruebas que fallan**

`tests/cuidadores_sinteticos.py`:

```python
"""
Formulario sintético de «Cuidando al Cuidador» para las pruebas (spec §7).

Nada sale de los datos reales: los encabezados se arman con los fragmentos de
`catalog.VERIFICAR` y las respuestas con las etiquetas de opción del
formulario (que son fijas, no datos personales). Lleva centinelas de
privacidad que nunca deben aparecer en ninguna salida:

  · nombres «Centinela …» de cuidadores y niños, y un tercer hijo en la 208;
  · el teléfono 3000000000 en la columna 179.

Configuración (después de consentimiento y deduplicación):
  · LauV: celdas de quinto (12), sexto (12) y octavo (10) → 34 cuidadores.
  · JJC: décimo (12) y cuarto (12), con el curso escrito de muchas formas.
  · SJMEB: 7 de séptimo y 7 de noveno → ninguna celda; el colegio entero (14).
  · La Balsa: 12 con once, transición, tercero o jardín → sin grado del estudio.
  · CdP (4) y un colegio que no se reconoce (3): el resto, que no llega a 10.
  · Repetidos: el cuidador 0 también respondió en 2025; el niño del cuidador 1
    lo reporta también su papá; el cuidador 2 repite al hijo 1 como hijo 2.
  · Una fila sin consentimiento, dos «Columna 6» en la PSS, una edad «diez» y
    una edad 19.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.cuidadores import catalog as cat

CLAVE_PRUEBA = "clave-de-prueba-solo-para-tests-0001"
TELEFONO = "3000000000"
PREFIJO_NOMBRE = "Centinela"

ETIQUETAS = {
    "BARRIO": ["No", "Sí, pero con baja frecuencia", "Sí, es muy frecuente"],
    "PSS": ["Nunca", "Casi nunca", "De vez en cuando", "Frecuentemente", "Casi siempre"],
    "MSPSS": ["Nunca", "Casi nunca", "Algunas veces", "Casi siempre", "Siempre"],
    "APQ": ["Nunca", "Casi nunca", "A veces", "Muy seguido", "Siempre"],
    "EP": ["Muy en desacuerdo", "En desacuerdo", "No estoy seguro", "De acuerdo",
           "Muy de acuerdo"],
    "SDQ": ["No es cierto", "Un tanto cierto", "Absolutamente cierto"],
    "ARI": ["No es cierto", "A veces cierto", "Cierto"],
}
# Las cuatro opciones de cada ítem de la EPDS, en el orden en que aparecen.
EPDS_OPCIONES = [
    ["Tanto como siempre he podido hacerlo", "No tanto ahora", "Sin duda, mucho menos ahora",
     "No, en absoluto"],
    ["Tanto como siempre", "Algo menos de lo que solía hacerlo",
     "Definitivamente menos de lo que solía hacerlo", "Prácticamente nunca"],
    ["Sí, casi siempre", "Sí, algunas veces", "No muy a menudo", "No, nunca"],
    ["No, en absoluto", "Casi nada", "Sí, a veces", "Sí, muy amenudo"],
    ["Sí, bastante", "Sí, a veces", "No, no mucho", "No, en absoluto"],
    ["Sí, la mayor parte del tiempo no he podido sobrellevarllas",
     "Sí, a veces no he podido sobrellevarlas de la mejor manera",
     "No, la mayoría de las veces he podido sobrellevarlas bastante bien",
     "No, he podido sobrellevarlas tan bien como lo he hecho simpre"],
    ["Sí, casi siempre", "Sí, a veces", "No muy a menudo", "No, en absoluto"],
    ["Sí, casi siempre", "Sí, a veces", "No muy a menudo", "No, en absoluto"],
    ["Sí, casi siempre", "Sí, a veces", "No muy a menudo", "No, nunca"],
    ["Sí, bastante a menudo", "A veces", "Casi nunca", "No, nunca"],
]

# Curso tal como lo escriben los cuidadores → grado esperado.
CURSOS = {
    "Quinto": ["Quinto", "501", "5A", "quinto B", "5°"],
    "Sexto": ["Sexto 602", "601", "6", "sexto"],
    "Octavo": ["Octavo", "803", "8vo"],
    "Décimo": ["1002", "Décimo", "10", "decimo A"],
    "Cuarto": ["Cuarto", "402", "4to", "4 - 1"],
    "Séptimo": ["Séptimo", "703"],
    "Noveno": ["Noveno", "901"],
    "fuera": ["Once", "1101", "Transición", "Tercero", "Jardín", "11"],
}

# (texto del colegio, [(grado, cuántos)])
PLAN = [
    ("Colegio Laura Vicuña", [("Quinto", 12), ("Sexto", 12), ("Octavo", 10)]),
    ("IE José Joaquín Casas", [("Décimo", 12), ("Cuarto", 12)]),
    ("San José María Escrivá de Balaguer", [("Séptimo", 7), ("Noveno", 7)]),
    ("Colegio La Balsa", [("fuera", 12)]),
    ("Cerca de Piedra", [("Quinto", 4)]),
    ("Colegio Inventado del Norte", [("Sexto", 3)]),
]


def encabezados() -> list[str]:
    return [f"{cat.VERIFICAR[p]} ({p})" if p in cat.VERIFICAR else f"Columna {p}"
            for p in range(cat.N_COLUMNAS)]


def nombre_cuidador(i: int) -> str:
    return f"{PREFIJO_NOMBRE} Cuidador {i:03d}"


def nombre_nino(i: int, hijo: int = 1) -> str:
    return f"{PREFIJO_NOMBRE} Nino {i:03d}-{hijo}"


def _fila_base(rng, i: int, colegio: str, curso: str, ts: str, quien: str = "Mamá") -> dict:
    f = {p: None for p in range(cat.N_COLUMNAS)}
    f[0] = ts
    f[1] = "Sí autorizo"
    f[2] = quien
    f[3] = nombre_cuidador(i)
    f[4] = nombre_nino(i, 1)
    f[5] = str(7 + i % 9) if i % 5 else f"{7 + i % 9} años"
    f[6] = "Niña" if i % 2 else "Niño"
    f[7] = colegio
    f[8] = "Oficial o púbico"
    f[9] = curso
    f[10], f[12], f[13], f[15] = "Sí", "Bachiller", "Sí", "Técnico o tecnólogo"
    f[17], f[18], f[19] = "Muy bueno", "Urbana (en la cuidad o pueblo)", str(1 + i % 4)
    for b in cat.BLOQUES_CUIDADOR:
        for j, p in enumerate(b.posiciones):
            if b.key == "EPDS":
                f[p] = EPDS_OPCIONES[j][int(rng.integers(0, 4))]
            else:
                opciones = ETIQUETAS[b.key]
                f[p] = opciones[int(rng.integers(0, len(opciones)))]
    for p in cat.bloque_sdq(1).posiciones:
        f[p] = ETIQUETAS["SDQ"][int(rng.integers(0, 3))]
    if ts.startswith("2026"):                     # el ARI solo existe en 2026
        for p in cat.bloque_ari(1).posiciones:
            f[p] = ETIQUETAS["ARI"][int(rng.integers(0, 3))]
    f[146] = "No"
    f[178] = "Sí"
    f[179] = TELEFONO
    f[208] = f"{PREFIJO_NOMBRE} Tercero {i:03d}"
    return f


def _hijo2(rng, f: dict, i: int, colegio: str, curso: str, nombre: str | None = None) -> None:
    f[146] = "Sí"
    f[147] = nombre or nombre_nino(i, 2)
    f[148] = str(8 + i % 7)
    f[149] = "Niño" if i % 2 else "Niña"
    f[150] = colegio
    f[151] = "Oficial o público"
    f[152] = curso
    for p in cat.bloque_sdq(2).posiciones:
        f[p] = ETIQUETAS["SDQ"][int(rng.integers(0, 3))]
    if str(f[0]).startswith("2026"):
        for p in cat.bloque_ari(2).posiciones:
            f[p] = ETIQUETAS["ARI"][int(rng.integers(0, 3))]


def formulario(semilla: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    filas: list[dict] = []
    i = 0
    for colegio, grupos in PLAN:
        for grado, cuantos in grupos:
            variantes = CURSOS[grado]
            for j in range(cuantos):
                ts = "2026-03-10 08:00:00" if i % 4 else "2025-09-15 09:00:00"
                ts = ts.replace(":00:00", f":{i % 60:02d}:00")
                f = _fila_base(rng, i, colegio, variantes[j % len(variantes)], ts,
                               quien="Abuelo o abuela" if i % 11 == 10 else "Mamá")
                if i % 3 == 0 and i > 2:
                    _hijo2(rng, f, i, colegio, variantes[(j + 1) % len(variantes)])
                filas.append(f)
                i += 1
    # Calidad: dos «Columna 6» en la PSS, una edad no numérica y una de 19.
    filas[5][cat.PSS.inicio + 6] = "Columna 6"
    filas[6][cat.PSS.inicio + 8] = "Columna 6"
    filas[7][5] = "diez"
    filas[8][5] = "19"
    # El cuidador 2 repite a su hijo 1 como hijo 2 en el mismo envío.
    _hijo2(rng, filas[2], 2, filas[2][7], filas[2][9], nombre=nombre_nino(2, 1))
    # El cuidador 0 también respondió en 2025, antes (se queda la de 2026).
    filas[0][0] = "2026-03-10 08:00:00"
    viejo = _fila_base(rng, 0, filas[0][7], filas[0][9], "2025-09-01 10:00:00")
    filas.append(viejo)
    # El papá del niño del cuidador 1 también lo reporta (se queda la mamá).
    papa = _fila_base(rng, 900, filas[1][7], filas[1][9], filas[1][0], quien="Papá")
    papa[4] = nombre_nino(1, 1)
    filas.append(papa)
    # Sin consentimiento: no entra a nada.
    no = _fila_base(rng, 901, "Colegio Laura Vicuña", "Quinto", "2026-03-11 10:00:00")
    no[1] = "No autorizo"
    filas.append(no)
    return pd.DataFrame([[f[p] for p in range(cat.N_COLUMNAS)] for f in filas],
                        columns=encabezados())


def escribir(ruta, semilla: int = 7) -> str:
    """Escribe el formulario como xlsx con el nombre que busca la aplicación."""
    import os
    os.makedirs(os.path.dirname(str(ruta)) or ".", exist_ok=True)
    formulario(semilla).to_excel(ruta, index=False)
    return str(ruta)


def textos_prohibidos() -> list[str]:
    """Lo que nunca puede aparecer en ninguna salida."""
    return [PREFIJO_NOMBRE, TELEFONO]
```

`tests/test_cuidadores_catalogo.py`:

```python
"""Cuidadores 360 · catálogo del formulario «Cuidando al Cuidador» (spec §3.2, §5.5)."""
from src.core.texto import norm_txt
from src.cuidadores import catalog as cat
from tests import cuidadores_sinteticos as cs


def test_bloques_por_posicion_de_la_spec():
    assert (cat.BARRIO.inicio, cat.PSS.inicio, cat.EPDS.inicio, cat.MSPSS.inicio,
            cat.APQ.inicio, cat.EP.inicio) == (20, 25, 35, 45, 57, 82)
    assert (cat.BARRIO.n_items, cat.PSS.n_items, cat.EPDS.n_items, cat.MSPSS.n_items,
            cat.APQ.n_items, cat.EP.n_items) == (5, 10, 10, 12, 25, 39)
    assert cat.SDQ_INICIO == {1: 121, 2: 153} and cat.ARI_INICIO == {1: 186, 2: 193}
    assert [cat.APQ.inicio + i - 1 for i in cat.APQ_FISICO] == [78, 79, 80]
    assert cat.APQ.inicio + cat.APQ_GRITO - 1 == 81
    assert [cat.EP.inicio + i - 1 for i in cat.EP_ELECCION_FORZADA] == [103, 104, 105, 106, 107]
    assert cat.EP.inicio + cat.EP_POSITIVO[0] - 1 == 117


def test_mspss_reparte_5_4_3():
    assert [len(v) for v in cat.MSPSS_FUENTES.values()] == [5, 4, 3]
    assert sorted(i for v in cat.MSPSS_FUENTES.values() for i in v) == list(range(1, 13))


def test_pss_igual_que_docentes():
    from scripts.preparar_docentes import INVERTIDOS, MAPAS
    assert tuple(int(x[3:]) for x in INVERTIDOS[4] if x.startswith("PSS")) == cat.PSS_INVERSOS
    assert {k: MAPAS["PSS"][k] for k in cat.MAP_PSS} == cat.MAP_PSS


def test_epds_tiene_un_mapa_por_item_y_cubre_todas_las_opciones():
    assert len(cat.EPDS_MAPAS) == 10
    for i, opciones in enumerate(cs.EPDS_OPCIONES):
        valores = [cat.EPDS_MAPAS[i][norm_txt(o)] for o in opciones]
        assert sorted(valores) == [0, 1, 2, 3], i + 1
    # ítems invertidos: la primera opción del formulario vale 3
    for item in (3, 5, 6, 7, 8, 9, 10):
        assert cat.EPDS_MAPAS[item - 1][norm_txt(cs.EPDS_OPCIONES[item - 1][0])] == 3
    for item in (1, 2, 4):
        assert cat.EPDS_MAPAS[item - 1][norm_txt(cs.EPDS_OPCIONES[item - 1][0])] == 0


def test_los_nombres_y_el_telefono_estan_declarados():
    assert set(cat.COLUMNAS_NOMBRE) == {3, 4, 147, 208}
    assert 179 in cat.NUNCA_SE_LEEN and 208 in cat.NUNCA_SE_LEEN


def test_el_formulario_sintetico_pasa_la_verificacion_de_encabezados():
    cols = cs.encabezados()
    assert len(cols) == cat.N_COLUMNAS
    for pos, fragmento in cat.VERIFICAR.items():
        assert fragmento in norm_txt(cols[pos])
```

Run: `.venv/bin/python -m pytest tests/test_cuidadores_catalogo.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.cuidadores'`.

- [ ] **Step 2: Implementar**

`src/cuidadores/__init__.py`:

```python
"""
Cuidadores 360 — formulario «Cuidando al Cuidador» (spec del 6-oct-2026, §5.5).

Fase 4a: carga, puntuación y vista de investigadores, solo en local.
Fase 4b: vista de comunidad, informes y publicación en Supabase.

Módulos: `catalog` (escalas y mapas por posición), `ingest` (consentimiento,
seudónimos, colegio, grado, ola, hijo 2 y deduplicación), `scoring`
(puntuaciones desde el texto crudo), `privacidad` (base publicable contando
cuidadores distintos) y `pipeline` (`AnalisisCuidadores`).
"""
```

`src/cuidadores/catalog.py`:

```python
"""
Catálogo del formulario «Cuidando al Cuidador» — Observatorio 360.

ÚNICA FUENTE DE VERDAD del módulo de cuidadores: qué hay en cada columna (por
posición, spec §3.2), cómo se convierte cada respuesta en número (mapas de
texto explícitos), qué puntuaciones existen, sus rangos y sus cortes.

Reglas que este catálogo fija:
  · El formulario se lee **por posición** y cada posición clave se verifica con
    un fragmento de su encabezado (`VERIFICAR`). Si Google Forms cambia el
    orden, la carga falla con un mensaje, nunca puntúa la columna equivocada.
  · Las respuestas se convierten **por su texto**, nunca por su posición en la
    lista de opciones. La EPDS tiene un mapa por ítem: cada ítem tiene sus
    cuatro etiquetas propias y varios están invertidos.
  · Columnas que nunca se copian: nombres (3, 4, 147, 208) y teléfono (179).
    Los tres nombres de las posiciones 3, 4 y 147 solo se leen para calcular el
    seudónimo; el teléfono y la 208 no se leen.
  · Estrés parental: no hay total ni subescalas hasta el libro de códigos
    (spec §5.5). APQ: solo castigo físico (78–80) y grito (81), descriptivos.

Los textos de este módulo son provisionales (`TEXTOS_APROBADOS = False`) y los
aprueba el equipo (spec §8). Nunca los redacta la IA.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.estudiantes import catalog as cat_est

TEXTOS_APROBADOS = False

MIN_GROUP_N = cat_est.MIN_GROUP_N
MODULO = "cuidadores"

# ── Marcos de análisis ──────────────────────────────────────────────────────
MARCO_CUIDADOR = "cuidador"     # una fila por cuidador distinto
MARCO_NINO = "nino"             # una fila por niño distinto (hijo 1 y hijo 2)
NOMBRES_MARCO = {MARCO_CUIDADOR: "Cuidadores (lo que dice el adulto de sí mismo)",
                 MARCO_NINO: "Niños (lo que dice el cuidador del niño)"}

# Fragmento normalizado con el que se reconoce el archivo en disco.
PATRON_ARCHIVO = "cuidando al cuidador"
N_COLUMNAS = 209

# ── Columnas de identificación y contexto (posición) ───────────────────────
COL = dict(
    ts=0, consentimiento=1, quien=2,
    nombre_cuidador=3, nombre_nino=4,           # solo para el seudónimo
    edad=5, sexo=6, colegio=7, tipo_colegio=8, curso=9,
    vive_mama=10, educ_madre=12, vive_papa=13, educ_padre=15,
    desempeno=17, zona=18, estrato=19,
    hijo2=146, nombre_nino2=147,                # solo para el seudónimo
    edad2=148, sexo2=149, colegio2=150, tipo_colegio2=151, curso2=152,
)
# Nunca se leen: teléfono y el nombre de un tercer hijo (bloque vacío).
NUNCA_SE_LEEN = (179, 208)
COLUMNAS_NOMBRE = (COL["nombre_cuidador"], COL["nombre_nino"], COL["nombre_nino2"], 208)

# Contexto que entra al marco de cuidadores, tal como se respondió (categórico).
CONTEXTO = dict(Vive_mama="vive_mama", Educ_madre="educ_madre", Vive_papa="vive_papa",
                Educ_padre="educ_padre", Desempeno="desempeno", Zona="zona",
                Estrato="estrato")


# ── Mapas de etiquetas (claves ya normalizadas con core.texto.norm_txt) ────
MAP_BARRIO = {"no": 0, "si pero con baja frecuencia": 1, "si es muy frecuente": 2}
# Igual que docentes (scripts/preparar_docentes.py, MAPAS["PSS"]).
MAP_PSS = {"nunca": 0, "casi nunca": 1, "de vez en cuando": 2, "frecuentemente": 3,
           "casi siempre": 4}
MAP_MSPSS = {"nunca": 1, "casi nunca": 2, "algunas veces": 3, "casi siempre": 4,
             "siempre": 5}
MAP_APQ = {"nunca": 1, "casi nunca": 2, "a veces": 3, "muy seguido": 4, "siempre": 5}
MAP_ACUERDO = {"muy en desacuerdo": 1, "en desacuerdo": 2, "no estoy seguro": 3,
               "de acuerdo": 4, "muy de acuerdo": 5}
MAP_SDQ_PADRES = {"no es cierto": 0, "un tanto cierto": 1, "absolutamente cierto": 2}
MAP_ARI_PADRES = {"no es cierto": 0, "a veces cierto": 1, "cierto": 2}

# EPDS-10: un mapa por ítem, por el TEXTO de la respuesta (Cox, Holden y Sagovsky,
# 1987; versión en español). Los ítems 3 y 5 a 10 puntúan al revés del orden en
# que aparecen las opciones. Se incluyen las erratas tal como llegaron en el
# formulario («simpre», «sobrellevarllas», «amenudo») y su forma corregida.
EPDS_MAPAS: tuple[dict, ...] = (
    {"tanto como siempre he podido hacerlo": 0, "no tanto ahora": 1,
     "sin duda mucho menos ahora": 2, "no en absoluto": 3},
    {"tanto como siempre": 0, "algo menos de lo que solia hacerlo": 1,
     "definitivamente menos de lo que solia hacerlo": 2, "practicamente nunca": 3},
    {"no nunca": 0, "no muy a menudo": 1, "si algunas veces": 2, "si casi siempre": 3},
    {"no en absoluto": 0, "casi nada": 1, "si a veces": 2, "si muy amenudo": 3,
     "si muy a menudo": 3},
    {"no en absoluto": 0, "no no mucho": 1, "si a veces": 2, "si bastante": 3},
    {"no he podido sobrellevarlas tan bien como lo he hecho simpre": 0,
     "no he podido sobrellevarlas tan bien como lo he hecho siempre": 0,
     "no la mayoria de las veces he podido sobrellevarlas bastante bien": 1,
     "si a veces no he podido sobrellevarlas de la mejor manera": 2,
     "si la mayor parte del tiempo no he podido sobrellevarllas": 3,
     "si la mayor parte del tiempo no he podido sobrellevarlas": 3},
    {"no en absoluto": 0, "no muy a menudo": 1, "si a veces": 2, "si casi siempre": 3},
    {"no en absoluto": 0, "no muy a menudo": 1, "si a veces": 2, "si casi siempre": 3},
    {"no nunca": 0, "no muy a menudo": 1, "si a veces": 2, "si casi siempre": 3},
    {"no nunca": 0, "casi nunca": 1, "a veces": 2, "si bastante a menudo": 3},
)


@dataclass(frozen=True)
class Bloque:
    """Un bloque de ítems contiguos del formulario."""
    key: str
    nombre: str
    prefijo: str                 # columnas PREFIJO1..N
    inicio: int                  # posición de la primera columna
    n_items: int
    mapas: tuple                 # un dict por ítem (mismo dict repetido si es uno solo)
    valor_min: int
    valor_max: int
    marco: str
    fuente: str
    faltantes: frozenset = frozenset()   # etiquetas que cuentan como faltante declarado

    @property
    def columnas(self) -> list[str]:
        return [f"{self.prefijo}{i}" for i in range(1, self.n_items + 1)]

    @property
    def posiciones(self) -> list[int]:
        return list(range(self.inicio, self.inicio + self.n_items))


def _repetir(mapa: dict, n: int) -> tuple:
    return tuple(mapa for _ in range(n))


BARRIO = Bloque("BARRIO", "Riesgo del barrio", "BARRIO", 20, 5, _repetir(MAP_BARRIO, 5),
                0, 2, MARCO_CUIDADOR,
                "Cinco preguntas del formulario: drogas, delincuencia, riñas, "
                "violencia grave y pandillas (0 = no, 1 = baja frecuencia, 2 = muy frecuente)")
PSS = Bloque("PSS", "PSS-10 — Estrés percibido", "PSS", 25, 10, _repetir(MAP_PSS, 10),
             0, 4, MARCO_CUIDADOR,
             "Cohen, Kamarck y Mermelstein (1983); mismos ítems, orden e inversos que "
             "la PSS de docentes", faltantes=frozenset({"columna 6"}))
EPDS = Bloque("EPDS", "EPDS-10 — Escala de Edimburgo", "EPDS", 35, 10, EPDS_MAPAS,
              0, 3, MARCO_CUIDADOR, "Cox, Holden y Sagovsky (1987); versión en español")
MSPSS = Bloque("MSPSS", "MSPSS — Apoyo social percibido del cuidador", "MSPSS", 45, 12,
               _repetir(MAP_MSPSS, 12), 1, 5, MARCO_CUIDADOR,
               "Zimet et al. (1988), escala de 5 puntos; en este formulario el reparto "
               "es 5 / 4 / 3 ítems (persona especial, familia, amigos)")
APQ = Bloque("APQ", "APQ — Prácticas de crianza", "APQ", 57, 25, _repetir(MAP_APQ, 25),
             1, 5, MARCO_CUIDADOR,
             "Alabama Parenting Questionnaire (Frick, 1991); subescalas pendientes del "
             "libro de códigos")
EP = Bloque("EP", "Estrés parental (39 ítems)", "EP", 82, 39, _repetir(MAP_ACUERDO, 39),
            1, 5, MARCO_CUIDADOR,
            "Formato tipo PSI con 39 ítems; no es el PSI-SF estándar. Sin total ni "
            "subescalas hasta el libro de códigos")
BLOQUES_CUIDADOR = (BARRIO, PSS, EPDS, MSPSS, APQ, EP)

# Bloques del niño: el mismo instrumento en dos lugares (hijo 1 y hijo 2).
SDQ_INICIO = {1: 121, 2: 153}
ARI_INICIO = {1: 186, 2: 193}


def bloque_sdq(hijo: int) -> Bloque:
    return Bloque("SDQ", "SDQ — versión para padres", "SDQ", SDQ_INICIO[hijo], 25,
                  _repetir(MAP_SDQ_PADRES, 25), 0, 2, MARCO_NINO,
                  "Goodman (1997); bandas de la versión para padres 4-17, sdqinfo.org")


def bloque_ari(hijo: int) -> Bloque:
    return Bloque("ARI", "ARI — versión para padres", "ARI", ARI_INICIO[hijo], 7,
                  _repetir(MAP_ARI_PADRES, 7), 0, 2, MARCO_NINO,
                  "Stringaris et al. (2012), versión para padres")


# ── Verificación de encabezados (fragmento normalizado por posición) ────────
VERIFICAR = {
    0: "marca temporal", 1: "consentimiento informado", 2: "quien esta respondiendo",
    3: "indique su nombre completo", 4: "nombre completo de su hijo",
    5: "que edad tiene el nino", 6: "sexo del nino", 7: "en que colegio estudia su hijo",
    9: "en que curso esta", 10: "vive con la mama", 12: "nivel educativo de la madre",
    13: "vive con el papa", 15: "nivel educativo del padre", 17: "desempeno academico",
    18: "en que zona", 19: "estrato socioeconomico",
    20: "relacionados con drogas", 24: "pandillas",
    25: "no podia controlar las cosas importantes",
    34: "tantas dificultades que no podia solucionarlas",
    35: "he podido reir", 44: "he pensado en hacerme dano",
    45: "compartir mis tristezas", 50: "mi familia trata de ayudarme",
    54: "contar con mis amigos", 56: "mis amigos tratan de ayudarme",
    57: "conversaciones amigables", 78: "nalgadas", 79: "cachetadas", 80: "correa",
    81: "grita a su hijo", 82: "no puedo controlar muy bien las situaciones",
    103: "soy muy bueno a como padre", 117: "lograr que mi hijo a haga algo es muy facil",
    120: "me exige mas de lo que exigen",
    121: "tiene en cuenta los sentimientos", 145: "termina lo que empieza",
    146: "otro de sus hijos", 147: "nombre completo de su hijo a 2",
    148: "edad de su hijo", 149: "sexo del nino a 2",
    150: "nombre completo del colegio 2", 152: "en que curso este su hijo",
    153: "tiene en cuenta los sentimientos", 177: "termina lo que empieza",
    179: "telefonico",
    186: "irritan facilmente", 192: "irritabilidad le causa problemas",
    193: "irritan facilmente", 199: "irritabilidad le causa problemas",
}

# ── Quién responde ──────────────────────────────────────────────────────────
MAMA, PAPA, OTRO = "Mamá", "Papá", "Otro cuidador"
PRIORIDAD_QUIEN = {MAMA: 0, PAPA: 1, OTRO: 2}

# ── Grados ──────────────────────────────────────────────────────────────────
GRADOS = ("Transición", "Primero", "Segundo", "Tercero", "Cuarto", "Quinto", "Sexto",
          "Séptimo", "Octavo", "Noveno", "Décimo", "Once")
# Los del estudio, con los mismos nombres que estudiantes (para la triangulación).
GRADOS_ESTUDIO = tuple(cat_est.ORDEN_GRADOS_PRI + cat_est.ORDEN_GRADOS_SEC)
FUERA_DE_RANGO = "Fuera del rango del estudio"
SIN_DATO = "Sin dato"
ESTADO_ESTUDIO, ESTADO_FUERA, ESTADO_SIN_DATO = "estudio", "fuera_de_rango", "sin_dato"
PALABRAS_GRADO = {
    "transicion": 0, "preescolar": 0, "jardin": 0, "prejardin": 0, "kinder": 0,
    "prekinder": 0, "primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "setimo": 7, "octavo": 8, "noveno": 9, "decimo": 10,
    "once": 11, "undecimo": 11,
}

# Edad del niño válida para el SDQ de padres.
EDAD_SDQ = (4, 17)

# ── Puntuaciones ────────────────────────────────────────────────────────────
PSS_INVERSOS = (3, 4, 5, 7, 9)          # = preparar_docentes.INVERTIDOS (PSS3…PSS9)
PSS_MIN_ITEMS = 9                        # se prorratea con 9 de 10
MSPSS_FUENTES = {"MSPSS_Otro": tuple(range(1, 6)), "MSPSS_Fam": tuple(range(6, 10)),
                 "MSPSS_Amigos": tuple(range(10, 13))}
EPDS_POSIBLE, EPDS_PROBABLE = 10, 13
EPDS_ITEM_AUTOLESION = 10
APQ_FISICO = {22: "Nalgadas con la mano", 23: "Cachetadas", 24: "Golpes con correa u objeto"}
APQ_GRITO = 25
APQ_UMBRAL = MAP_APQ["a veces"]          # «a veces o más»
EP_ELECCION_FORZADA = (22, 23, 24, 25, 26)   # columnas 103–107: una sola pregunta partida
EP_POSITIVO = (36,)                          # columna 117, redactada en positivo
ARI_ITEMS_TOTAL = (1, 2, 3, 4, 5, 6)
ARI_ITEM_DETERIORO = 7


@dataclass(frozen=True)
class Puntuacion:
    clave: str
    label: str
    label_llano: str
    rango: tuple
    direccion: str          # "riesgo" | "protector"
    marco: str
    fuente: str


PUNTUACIONES: tuple[Puntuacion, ...] = (
    Puntuacion("PSS_Total", "Estrés percibido (PSS-10)", "Estrés de la vida diaria",
               (0, 40), "riesgo", MARCO_CUIDADOR, PSS.fuente),
    Puntuacion("EPDS_Total", "Ánimo (EPDS-10)", "Ánimo del cuidador", (0, 30), "riesgo",
               MARCO_CUIDADOR, EPDS.fuente),
    Puntuacion("MSPSS_Total", "Apoyo social total (12 ítems)", "Apoyo que tiene en general",
               (1, 5), "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("MSPSS_Otro", "Apoyo de una persona especial (5 ítems)",
               "Una persona especial", (1, 5), "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("MSPSS_Fam", "Apoyo de la familia (4 ítems)", "Su familia", (1, 5),
               "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("MSPSS_Amigos", "Apoyo de los amigos (3 ítems)", "Sus amigos", (1, 5),
               "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("BARRIO_Indice", "Riesgo del barrio (0–10)", "Seguridad del barrio",
               (0, 10), "riesgo", MARCO_CUIDADOR, BARRIO.fuente),
    Puntuacion("SDQ_Total", "SDQ padres: total de dificultades", "Dificultades en total",
               (0, 40), "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Emo", "SDQ padres: síntomas emocionales", "Tristeza, preocupación y miedos",
               (0, 10), "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Con", "SDQ padres: problemas de conducta", "Peleas, desobediencia y mentiras",
               (0, 10), "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Hip", "SDQ padres: hiperactividad e inatención",
               "Inquietud y dificultad para concentrarse", (0, 10), "riesgo", MARCO_NINO,
               "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Pares", "SDQ padres: problemas con pares",
               "Sentirse solo o molestado por otros", (0, 10), "riesgo", MARCO_NINO,
               "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Pro", "SDQ padres: conducta prosocial", "Ayudar y compartir con otros",
               (0, 10), "protector", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Int", "SDQ padres: internalizante", "Malestar hacia adentro", (0, 20),
               "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Ext", "SDQ padres: externalizante", "Malestar hacia afuera", (0, 20),
               "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("ARI_Total", "Irritabilidad según el cuidador (ARI-P, ítems 1–6)",
               "Enojo frecuente e intenso", (0, 12), "riesgo", MARCO_NINO,
               "Stringaris et al. (2012), versión para padres; cobertura parcial"),
)
PUNTUACIONES_POR_CLAVE = {p.clave: p for p in PUNTUACIONES}
CLAVES_CUIDADOR = [p.clave for p in PUNTUACIONES if p.marco == MARCO_CUIDADOR]
CLAVES_NINO = [p.clave for p in PUNTUACIONES if p.marco == MARCO_NINO]
# Sin corte clínico: terciles de la muestra.
CLAVES_TERCILES = ("PSS_Total", "MSPSS_Total", "MSPSS_Otro", "MSPSS_Fam", "MSPSS_Amigos",
                   "BARRIO_Indice")


def label(clave: str) -> str:
    p = PUNTUACIONES_POR_CLAVE.get(clave)
    return p.label if p else clave


# ── Señales del adulto (spec §5.5) ─────────────────────────────────────────
# Solo las definiciones. Mensajes, textos por rol y tarjetas de comunidad: 4b.
@dataclass(frozen=True)
class AlertaAdulto:
    clave: str
    nombre: str
    regla: str
    columna: str           # indicador 0/1 por cuidador


ANIMO, AUTOLESION = "animo", "autolesion"
ALERTAS = {
    ANIMO: AlertaAdulto(ANIMO, "Ánimo", f"EPDS-10 ≥ {EPDS_PROBABLE} (probable)",
                        "EPDS_Probable"),
    AUTOLESION: AlertaAdulto(AUTOLESION, "Autolesión",
                             "EPDS ítem 10 («He pensado en hacerme daño») con cualquier "
                             "respuesta distinta de «No, nunca»", "EPDS_Autolesion"),
}


def ruta_adulto(rol: str) -> list[tuple[str, str]]:
    """Ruta de atención para adultos; la vigente de estudiantes hasta que el equipo apruebe."""
    from src.estudiantes import alertas_catalogo
    return alertas_catalogo.ruta(rol, "adulto")


# Tarjetas de la vista de comunidad (spec §5.5). Las arma la fase 4b.
TARJETAS_4B = (
    ("estres", "Estrés de crianza"),
    ("animo", "Ánimo del cuidador"),
    ("apoyo", "Apoyo que tiene"),
    ("crianza", "Crianza positiva y castigo físico"),
    ("barrio", "Seguridad del barrio"),
    ("hijo", "Cómo ve el cuidador al hijo"),
)

# ── Avisos fijos de la vista de investigadores ──────────────────────────────
AVISO_EPDS = ("La EPDS se validó en el periodo perinatal. Aquí se lee como tamizaje del "
              "ánimo del cuidador, no como diagnóstico ni como medida de depresión posparto.")
AVISO_ARI = ("El ARI de padres se añadió al formulario en 2026: no hay respuestas de la ola "
             "2025 y la cobertura es parcial. Sus cifras describen solo a quienes lo "
             "respondieron.")
AVISO_ESTRES_PARENTAL = ("Estrés parental: no se calcula total ni subescalas hasta confirmar "
                         "con el libro de códigos la dirección de los ítems. Las columnas "
                         "103–107 son las cinco opciones de una sola pregunta de elección "
                         "forzada y la 117 está redactada en positivo. Aquí solo se describen "
                         "los ítems.")
AVISO_APQ = ("APQ: mientras no llegue el libro de códigos solo se reportan el castigo físico "
             "(nalgadas, cachetadas, correa u objeto) como «usa alguna forma, a veces o más» "
             "y el grito, de forma descriptiva. La Ley 2089 de 2021 prohíbe el castigo "
             "físico; el texto para la comunidad lo planteará como acompañamiento.")
AVISO_MSPSS = ("El MSPSS del cuidador reparte los ítems 5 / 4 / 3 (persona especial, familia, "
               "amigos) y su redacción no es la de estudiantes: solo se compara por fuente, "
               "sobre todo familia, y con este aviso.")
AVISO_SDQ_EDAD = (f"SDQ de padres: se puntúa a los niños de {EDAD_SDQ[0]} a {EDAD_SDQ[1]} años "
                  "y a los que no tienen una edad numérica (se declaran aparte). Con una edad "
                  "numérica fuera de ese rango, el SDQ queda como faltante.")
AVISO_OLA = ("El filtro de ola solo existe en esta vista local: nada se publica por ola.")
AVISO_MINIMO = (f"Ningún grupo con menos de {MIN_GROUP_N} cuidadores distintos se muestra "
                "desagregado; en el marco de niños el mínimo también cuenta cuidadores, no "
                "niños.")
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_catalogo.py -q`
Expected: `6 passed`. Los fragmentos de `VERIFICAR` se comprueban contra el encabezado real en la Task 7, Step 4.

- [ ] **Step 4: Commit**

```bash
git add src/cuidadores/__init__.py src/cuidadores/catalog.py \
        tests/cuidadores_sinteticos.py tests/test_cuidadores_catalogo.py
git commit -m "feat(cuidadores): catálogo por posición y formulario sintético" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Ingesta (sin deduplicar)

**Files:**
- Create: `src/cuidadores/ingest.py`
- Create: `tests/test_cuidadores_ingest.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_ingest.py`:

```python
"""Cuidadores 360 · ingesta (spec §3.2, §5.5): formato, privacidad, edad, grado, ola e hijo 2."""
import numpy as np
import pandas as pd
import pytest

from src.core.texto import norm_txt
from src.cuidadores import catalog as cat
from src.cuidadores import ingest
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(cs.formulario(), k=K)


# ══ Formato ═════════════════════════════════════════════════════════════════
def test_un_archivo_con_otro_orden_no_se_carga():
    df = cs.formulario()
    cols = list(df.columns)
    cols[35], cols[36] = cols[36], cols[35]
    with pytest.raises(ingest.FormatoInesperado, match="columna 35"):
        ingest.cargar(df.set_axis(cols, axis=1), k=K)


def test_sin_clave_no_se_carga(monkeypatch):
    from src.core import seudonimo as seud
    monkeypatch.delenv(seud.VARIABLE, raising=False)
    monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    with pytest.raises(seud.ClaveAusente):
        ingest.cargar(cs.formulario())


# ══ Privacidad ══════════════════════════════════════════════════════════════
def _texto_de(df: pd.DataFrame) -> str:
    return df.astype(str).to_csv(index=False) + " ".join(map(str, df.columns))


def test_ni_nombres_ni_telefono_en_ninguna_salida(carga):
    textos = [_texto_de(carga.respuestas), _texto_de(carga.ninos),
              str(carga.informe.como_dict())]
    for t in textos:
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in t
    for df in (carga.respuestas, carga.ninos):
        assert not [c for c in df.columns if "nombre" in c.lower() and c != "Colegio_nombre"]
        assert not [c for c in df.columns if "telef" in norm_txt(c)]


def test_los_seudonimos_tienen_el_formato_de_supabase(carga):
    assert carga.respuestas["ID_cuidador"].str.fullmatch(r"C[0-9a-f]{8}").all()
    assert carga.ninos["ID_nino"].str.fullmatch(r"N[0-9a-f]{8}").all()


def test_el_colegio_no_reconocido_no_lleva_su_texto(carga):
    otros = carga.ninos[carga.ninos["Colegio"] == "OTRO"]
    assert len(otros) and (otros["Colegio_nombre"] == "Otro colegio").all()
    assert "Inventado" not in _texto_de(carga.ninos)


# ══ Consentimiento, ola y quién responde ═══════════════════════════════════
def test_consentimiento(carga):
    assert carga.informe.sin_consentimiento == 1
    assert carga.informe.respuestas_validas == carga.informe.filas_archivo - 1


def test_ola_por_ano_de_la_marca_temporal(carga):
    assert set(carga.respuestas["Ola"]) == {"2025", "2026"}
    s = pd.Series(["2025-09-15 09:05:00", "15/09/2025 9:05:00", "2026-03-10 08:00:00"])
    assert ingest._ola(ingest.fecha(s)).tolist() == ["2025", "2025", "2026"]


@pytest.mark.parametrize("texto,esperado", [
    ("Mamá", cat.MAMA), ("mama", cat.MAMA), ("Papá", cat.PAPA),
    ("Abuelo o abuela", cat.OTRO), ("Tío o tía", cat.OTRO), ("Otro cuidador principal", cat.OTRO),
])
def test_quien_responde(texto, esperado):
    assert ingest.quien(texto) == esperado


# ══ Edad y grado ════════════════════════════════════════════════════════════
@pytest.mark.parametrize("texto,valor,estado", [
    ("7", 7.0, "ok"), ("10 años", 10.0, "ok"), ("12 anos", 12.0, "ok"), ("9años", 9.0, "ok"),
    ("diez", np.nan, "no_numerica"), ("10 años 5 meses", np.nan, "no_numerica"),
    ("19", np.nan, "fuera_de_rango"), ("3", np.nan, "fuera_de_rango"), ("", np.nan, "vacia"),
])
def test_edad_del_nino(texto, valor, estado):
    v, e = ingest.edad(texto)
    assert e == estado and (np.isnan(valor) and np.isnan(v) or v == valor)


VARIANTES_CURSO = [(t, g) for g, ts in cs.CURSOS.items() if g != "fuera" for t in ts] + [
    ("Sexto 602", "Sexto"), ("501", "Quinto"), ("1002", "Décimo"), ("5-2", "Quinto"),
    ("10.1", "Décimo"), ("Grado quinto", "Quinto"), ("4D", "Cuarto"), ("7mo", "Séptimo"),
    ("9no", "Noveno"), ("1ero", None), ("6to B", "Sexto"), ("Octavo jornada tarde", "Octavo"),
]


@pytest.mark.parametrize("texto,grado", VARIANTES_CURSO)
def test_curso_libre_a_grado_del_estudio(texto, grado):
    g, detalle, estado = ingest.grado_desde_curso(texto)
    if grado is None:
        assert estado == cat.ESTADO_FUERA and pd.isna(g)
    else:
        assert g == grado and detalle == grado and estado == cat.ESTADO_ESTUDIO


@pytest.mark.parametrize("texto,detalle", [
    ("Once", "Once"), ("1101", "Once"), ("11", "Once"), ("Transición", "Transición"),
    ("Jardín", "Transición"), ("Tercero", "Tercero"), ("Primero", "Primero"), ("201", "Segundo"),
])
def test_grados_fuera_del_rango_del_estudio(texto, detalle):
    g, d, estado = ingest.grado_desde_curso(texto)
    assert pd.isna(g) and d == detalle and estado == cat.ESTADO_FUERA


@pytest.mark.parametrize("texto", ["", "???", "grupo azul", "25", "A1"])
def test_curso_sin_resolver(texto):
    g, d, estado = ingest.grado_desde_curso(texto)
    assert pd.isna(g) and d == cat.SIN_DATO and estado == cat.ESTADO_SIN_DATO


# ══ Hijo 2 ══════════════════════════════════════════════════════════════════
def test_el_hijo_2_es_otra_fila_de_nino(carga):
    inf = carga.informe
    assert inf.hijo2 > 0
    assert inf.filas_nino == inf.respuestas_validas + inf.hijo2
    assert set(carga.ninos["Orden_hijo"]) == {1, 2}


# ══ Conversión de respuestas ════════════════════════════════════════════════
def test_columna_6_es_faltante_declarado(carga):
    assert carga.informe.respuestas_columna6_pss == 2
    assert "PSS" not in carga.informe.etiquetas_no_mapeadas
    assert carga.respuestas[cat.PSS.columnas].isna().sum().sum() == 2


def test_una_etiqueta_desconocida_se_cuenta_sin_mostrarla():
    df = cs.formulario()
    df.iloc[3, cat.APQ.inicio] = "Respuesta rara de prueba"
    c = ingest.cargar(df, k=K)
    assert c.informe.etiquetas_no_mapeadas == {"APQ": 1}
    assert "Respuesta rara" not in str(c.informe.como_dict())


def test_rangos_de_los_items(carga):
    r = carga.respuestas
    for b in cat.BLOQUES_CUIDADOR:
        v = r[b.columnas].stack().dropna()
        assert v.between(b.valor_min, b.valor_max).all(), b.key
    n = carga.ninos
    assert n[cat.bloque_sdq(1).columnas].stack().dropna().between(0, 2).all()
    assert n[cat.bloque_ari(1).columnas].stack().dropna().between(0, 2).all()


def test_el_ari_no_existe_en_la_ola_2025(carga):
    n = carga.ninos
    assert n.loc[n["Ola"] == "2025", cat.bloque_ari(1).columnas].isna().all().all()
    assert carga.informe.cobertura_ari["hijo 1"] > 0


def test_enunciados_de_los_items(carga):
    assert len(carga.informe.enunciados["APQ"]) == 25
    assert ingest.enunciado(" [Grita a su hijo(a) cuando se ha portado mal]") == \
        "Grita a su hijo(a) cuando se ha portado mal"
```

Run: `.venv/bin/python -m pytest tests/test_cuidadores_ingest.py -q`
Expected: FAIL con `ImportError: cannot import name 'ingest' from 'src.cuidadores'`.

- [ ] **Step 2: Implementar**

`src/cuidadores/ingest.py` (la deduplicación se añade al final en la Task 4):

```python
"""
Ingesta del formulario «Cuidando al Cuidador» — Observatorio 360.

Entrada: la exportación de Google Forms (xlsx o csv), 209 columnas, leída por
posición (catalog.COL y los bloques) y verificada con `catalog.VERIFICAR`.

Salida (`Carga`):
  · `respuestas`: una fila por respuesta con consentimiento, con el seudónimo
    del cuidador (`ID_cuidador`), la ola, quién responde, el colegio y el grado
    de su primer hijo, el contexto y los ítems del adulto ya en número.
  · `ninos`: una fila por niño reportado (hijo 1 y, si lo hay, hijo 2), con su
    seudónimo (`ID_nino`), el del cuidador, edad, sexo, colegio, grado y los
    ítems del SDQ y del ARI de padres en número.
  · `informe`: conteos trazables de la carga, nunca valores individuales.

`deduplicar(carga, ola)` deja un cuidador por `ID_cuidador` (la respuesta más
reciente) y un niño por `ID_nino` (la ola más reciente; luego mamá, papá,
otro; luego el primer envío; dentro de un envío, el hijo 1 antes que el 2).

PRIVACIDAD — reglas que este módulo garantiza:
  · Los nombres (posiciones 3, 4 y 147) se leen solo para el seudónimo HMAC con
    clave local (`core.seudonimo`) y nunca se copian a ninguna salida.
  · El teléfono (179) y el nombre de un tercer hijo (208) no se leen.
  · Un colegio escrito a mano que no se reconoce queda como «OTRO» / «Otro
    colegio»: su texto libre no viaja.
  · Ninguna función devuelve, registra ni imprime nombres o filas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.core import seudonimo as seud
from src.core.colegios import normalizar as normalizar_colegio
from src.core.texto import norm_txt
from src.cuidadores import catalog as cat

OLA_COLUMNA = "Ola"


class FormatoInesperado(ValueError):
    """La exportación no tiene las preguntas donde el catálogo las espera."""


@dataclass
class InformeCuidadores:
    filas_archivo: int = 0
    sin_consentimiento: int = 0
    respuestas_validas: int = 0
    por_ola: dict = field(default_factory=dict)
    por_quien: dict = field(default_factory=dict)
    # cuidadores
    cuidadores_distintos: int = 0
    respuestas_repetidas_cuidador: int = 0     # quitadas: el mismo cuidador más de una vez
    cuidadores_en_dos_olas: int = 0
    # niños
    filas_nino: int = 0
    hijo2: int = 0
    ninos_sin_nombre: int = 0
    mismo_nino_misma_respuesta: int = 0        # hijo 2 = hijo 1 en el mismo envío
    mismo_nino_otro_cuidador: int = 0
    mismo_nino_entre_olas: int = 0
    ninos_unicos: int = 0
    # calidad
    edad_no_numerica: int = 0
    edad_fuera_de_rango: int = 0
    curso_sin_resolver: int = 0
    grados: dict = field(default_factory=dict)          # «Cuarto»/«Fuera…»/«Sin dato» → n
    colegios_cuidador: dict = field(default_factory=dict)
    colegios_nino: dict = field(default_factory=dict)
    colegio_no_reconocido: int = 0
    respuestas_columna6_pss: int = 0
    etiquetas_no_mapeadas: dict = field(default_factory=dict)   # bloque → nº de respuestas
    cobertura_ari: dict = field(default_factory=dict)            # «hijo 1»/«hijo 2» → n
    faltantes_por_bloque: dict = field(default_factory=dict)
    enunciados: dict = field(default_factory=dict)   # bloque → textos de los ítems (encabezados)
    avisos: list = field(default_factory=list)

    def como_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Carga:
    respuestas: pd.DataFrame
    ninos: pd.DataFrame
    informe: InformeCuidadores


# ── lectura ─────────────────────────────────────────────────────────────────
def leer(ruta) -> pd.DataFrame:
    """Lee la exportación como texto (las etiquetas se convierten aquí, no en pandas)."""
    ruta = str(ruta)
    if ruta.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(ruta, dtype=str)
    return pd.read_csv(ruta, dtype=str)


def verificar_formato(columnas) -> None:
    """Comprueba que cada posición clave tiene la pregunta esperada."""
    columnas = list(columnas)
    if len(columnas) < cat.N_COLUMNAS - 9:
        raise FormatoInesperado(
            f"Se esperaban {cat.N_COLUMNAS} columnas y llegaron {len(columnas)}. "
            "¿Es la exportación de «Cuidando al Cuidador»?")
    for pos, fragmento in cat.VERIFICAR.items():
        texto = norm_txt(columnas[pos]) if pos < len(columnas) else ""
        if fragmento not in texto:
            raise FormatoInesperado(
                f"En la columna {pos} se esperaba «{fragmento}». Revise que la "
                "exportación no haya cambiado de orden.")


def enunciado(columna) -> str:
    """Texto del ítem en el encabezado: lo que va entre corchetes, o el encabezado entero."""
    texto = str(columna).strip()
    m = re.search(r"\[(.+?)\]", texto)
    return (m.group(1) if m else texto).strip()


def es_formulario_cuidadores(df: pd.DataFrame) -> bool:
    try:
        verificar_formato(df.columns)
        return True
    except FormatoInesperado:
        return False


# ── conversiones ────────────────────────────────────────────────────────────
def mapear_bloque(raw: pd.DataFrame, bloque: cat.Bloque, informe: InformeCuidadores,
                  etiqueta: str | None = None) -> pd.DataFrame:
    """Columnas PREFIJO1..N en número, por el texto de cada respuesta."""
    etiqueta = etiqueta or bloque.key
    out, no_mapeadas, declaradas = {}, 0, 0
    for i, (pos, mapa) in enumerate(zip(bloque.posiciones, bloque.mapas), start=1):
        texto = raw.iloc[:, pos].map(norm_txt)
        valor = texto.map(lambda t: mapa.get(t, np.nan) if t else np.nan).astype(float)
        sin = (texto != "") & valor.isna()
        declaradas += int((sin & texto.isin(bloque.faltantes)).sum())
        no_mapeadas += int((sin & ~texto.isin(bloque.faltantes)).sum())
        out[f"{bloque.prefijo}{i}"] = valor
    if no_mapeadas:
        informe.etiquetas_no_mapeadas[etiqueta] = \
            informe.etiquetas_no_mapeadas.get(etiqueta, 0) + no_mapeadas
    if bloque.key == "PSS":
        informe.respuestas_columna6_pss += declaradas
    return pd.DataFrame(out, index=raw.index)


_EDAD = re.compile(r"(\d{1,2})(?: ?anos?)?")
_ORDINAL = re.compile(r"(\d{1,2})(?:ro|do|er|ero|to|mo|vo|no|o|[a-h])?")
_CODIGO = re.compile(r"(\d{1,2})(\d{2})[a-h]?")


def edad(texto) -> tuple[float, str]:
    """(edad, estado): estado «ok», «no_numerica» o «fuera_de_rango» (fuera de 4–17)."""
    t = norm_txt(texto)
    if not t:
        return np.nan, "vacia"
    m = _EDAD.fullmatch(t)
    if not m:
        return np.nan, "no_numerica"
    n = int(m.group(1))
    lo, hi = cat.EDAD_SDQ
    if not lo <= n <= hi:
        return np.nan, "fuera_de_rango"
    return float(n), "ok"


def numero_de_grado(texto) -> int | None:
    """Grado 0 (transición) a 11 (once) desde el curso escrito a mano; None si no se sabe.

    Reglas, en orden y sobre el texto normalizado:
      1. Una palabra de grado en cualquier parte: «Sexto 602» → 6.
      2. Un número de 1 o 2 cifras, con o sin sufijo («5», «5A», «4to»): «10» → 10.
      3. Un código de curso de 3 o 4 cifras, grado y grupo: «501» → 5, «1002» → 10.
    """
    tokens = norm_txt(texto).split()
    for t in tokens:
        if t in cat.PALABRAS_GRADO:
            return cat.PALABRAS_GRADO[t]
    for t in tokens:
        m = _ORDINAL.fullmatch(t)
        if m and 0 <= int(m.group(1)) <= 11:
            return int(m.group(1))
        m = _CODIGO.fullmatch(t)
        if m and 0 <= int(m.group(1)) <= 11 and 1 <= int(m.group(2)) <= 20:
            return int(m.group(1))
    return None


def grado_desde_curso(texto) -> tuple[object, str, str]:
    """(Grado del estudio o NaN, detalle legible, estado)."""
    n = numero_de_grado(texto)
    if n is None:
        return np.nan, cat.SIN_DATO, cat.ESTADO_SIN_DATO
    nombre = cat.GRADOS[n]
    if nombre in cat.GRADOS_ESTUDIO:
        return nombre, nombre, cat.ESTADO_ESTUDIO
    return np.nan, nombre, cat.ESTADO_FUERA


def quien(texto) -> str:
    t = norm_txt(texto)
    if t.startswith("mama"):
        return cat.MAMA
    if t.startswith("papa"):
        return cat.PAPA
    return cat.OTRO


def _colegio(serie: pd.Series) -> pd.DataFrame:
    """Código, nombre legible y sede. El texto libre no reconocido no viaja."""
    filas = []
    for x in serie:
        codigo, nombre, sede = normalizar_colegio(x)
        if codigo == "OTRO":
            nombre = "Otro colegio"
        filas.append((codigo, nombre, sede))
    return pd.DataFrame(filas, index=serie.index, columns=["Colegio", "Colegio_nombre", "Sede"])


def fecha(serie: pd.Series) -> pd.Series:
    """Marca temporal: ISO (xlsx leído como texto) o día/mes/año (csv de Google Forms)."""
    iso = pd.to_datetime(serie, errors="coerce", format="ISO8601")
    faltan = iso.isna() & serie.notna()
    if faltan.any():
        iso.loc[faltan] = pd.to_datetime(serie[faltan], errors="coerce", dayfirst=True,
                                         format="mixed")
    return iso


def _ola(ts: pd.Series) -> pd.Series:
    """Ola = año calendario de la marca temporal («2025», «2026»)."""
    return ts.dt.year.map(lambda a: str(int(a)) if pd.notna(a) else cat.SIN_DATO)


def _si(serie: pd.Series) -> pd.Series:
    return serie.map(norm_txt).str.startswith("si")


# ── carga ───────────────────────────────────────────────────────────────────
def _nino(raw: pd.DataFrame, filas: pd.Index, hijo: int, base: pd.DataFrame,
          k: bytes, informe: InformeCuidadores) -> pd.DataFrame:
    """Filas de niño (hijo 1 o 2) para las respuestas `filas`."""
    sub = raw.loc[filas]
    pos = (dict(nombre=cat.COL["nombre_nino"], edad=cat.COL["edad"], sexo=cat.COL["sexo"],
                colegio=cat.COL["colegio"], curso=cat.COL["curso"]) if hijo == 1 else
           dict(nombre=cat.COL["nombre_nino2"], edad=cat.COL["edad2"], sexo=cat.COL["sexo2"],
                colegio=cat.COL["colegio2"], curso=cat.COL["curso2"]))
    d = base.loc[filas, ["ID_cuidador", "ts", OLA_COLUMNA, "Quien", "_fila"]].copy()
    d["Orden_hijo"] = hijo
    ids = sub.iloc[:, pos["nombre"]].map(lambda x: seud.seudonimo(x, "N", k))
    informe.ninos_sin_nombre += int(ids.isna().sum())
    # Sin nombre no se puede deduplicar: cada fila es un niño distinto.
    d["ID_nino"] = [i if i is not None else f"sin-nombre-{hijo}-{f}"
                    for i, f in zip(ids, d["_fila"])]
    edades = sub.iloc[:, pos["edad"]].map(edad)
    d["Edad"] = [e for e, _ in edades]
    d["_edad_estado"] = [s for _, s in edades]
    d["Sexo"] = sub.iloc[:, pos["sexo"]].map(
        lambda x: str(x).strip() if norm_txt(x) in ("nino", "nina") else np.nan)
    d = pd.concat([d, _colegio(sub.iloc[:, pos["colegio"]])], axis=1)
    grados = sub.iloc[:, pos["curso"]].map(grado_desde_curso)
    d["Grado"] = [g for g, _, _ in grados]
    d["Grado_detalle"] = [x for _, x, _ in grados]
    d["Grado_estado"] = [s for _, _, s in grados]
    sdq = mapear_bloque(sub, cat.bloque_sdq(hijo), informe, "SDQ")
    ari = mapear_bloque(sub, cat.bloque_ari(hijo), informe, "ARI")
    informe.cobertura_ari[f"hijo {hijo}"] = int(ari.notna().all(axis=1).sum())
    return pd.concat([d, sdq, ari], axis=1)


def cargar(fuente, k: bytes | None = None) -> Carga:
    """Lee, verifica, filtra por consentimiento y seudonimiza. No deduplica."""
    raw = fuente.copy() if isinstance(fuente, pd.DataFrame) else leer(fuente)
    raw = raw.reset_index(drop=True)
    verificar_formato(raw.columns)
    k = seud.clave() if k is None else k      # sin clave, aquí se detiene

    inf = InformeCuidadores(filas_archivo=len(raw))
    for b in cat.BLOQUES_CUIDADOR:
        inf.enunciados[b.key] = [enunciado(raw.columns[p]) for p in b.posiciones]
    consiente = _si(raw.iloc[:, cat.COL["consentimiento"]])
    inf.sin_consentimiento = int((~consiente).sum())
    raw = raw[consiente]
    inf.respuestas_validas = len(raw)

    r = pd.DataFrame(index=raw.index)
    r["_fila"] = np.arange(len(raw))
    r["ID_cuidador"] = raw.iloc[:, cat.COL["nombre_cuidador"]].map(
        lambda x: seud.seudonimo(x, "C", k))
    sin_nombre = r["ID_cuidador"].isna()
    r.loc[sin_nombre, "ID_cuidador"] = [f"sin-nombre-{f}" for f in r.loc[sin_nombre, "_fila"]]
    r["ts"] = fecha(raw.iloc[:, cat.COL["ts"]])
    r[OLA_COLUMNA] = _ola(r["ts"])
    r["Quien"] = raw.iloc[:, cat.COL["quien"]].map(quien)
    # El colegio y el grado del cuidador son los de su primer hijo.
    r = pd.concat([r, _colegio(raw.iloc[:, cat.COL["colegio"]])], axis=1)
    g1 = raw.iloc[:, cat.COL["curso"]].map(grado_desde_curso)
    r["Grado"] = [g for g, _, _ in g1]
    r["Grado_detalle"] = [x for _, x, _ in g1]
    for nombre, clave in cat.CONTEXTO.items():
        r[nombre] = raw.iloc[:, cat.COL[clave]].map(
            lambda x: str(x).strip() if norm_txt(x) else np.nan)
    bloques = [mapear_bloque(raw, b, inf) for b in cat.BLOQUES_CUIDADOR]
    respuestas = pd.concat([r] + bloques, axis=1)

    con_hijo2 = raw.index[_si(raw.iloc[:, cat.COL["hijo2"]])]
    inf.hijo2 = len(con_hijo2)
    ninos = pd.concat([_nino(raw, raw.index, 1, r, k, inf),
                       _nino(raw, con_hijo2, 2, r, k, inf)], ignore_index=True)
    inf.filas_nino = len(ninos)

    inf.por_ola = respuestas[OLA_COLUMNA].value_counts().sort_index().to_dict()
    inf.por_quien = respuestas["Quien"].value_counts().to_dict()
    inf.edad_no_numerica = int((ninos["_edad_estado"] == "no_numerica").sum())
    inf.edad_fuera_de_rango = int((ninos["_edad_estado"] == "fuera_de_rango").sum())
    inf.curso_sin_resolver = int((ninos["Grado_estado"] == cat.ESTADO_SIN_DATO).sum())
    inf.colegio_no_reconocido = int((ninos["Colegio"] == "OTRO").sum())
    for b in cat.BLOQUES_CUIDADOR:
        inf.faltantes_por_bloque[b.key] = round(
            float(respuestas[b.columnas].isna().mean().mean() * 100), 2)
    for clave, cols in (("SDQ", cat.bloque_sdq(1).columnas), ("ARI", cat.bloque_ari(1).columnas)):
        inf.faltantes_por_bloque[clave] = round(float(ninos[cols].isna().mean().mean() * 100), 2)
    if inf.respuestas_columna6_pss:
        inf.avisos.append(f"PSS-10: {inf.respuestas_columna6_pss} respuestas sueltas "
                          "«Columna 6» cuentan como faltantes.")
    if inf.etiquetas_no_mapeadas:
        inf.avisos.append("Hay respuestas con etiquetas que el catálogo no reconoce: "
                          + ", ".join(f"{k_} ({n})" for k_, n in
                                      sorted(inf.etiquetas_no_mapeadas.items()))
                          + ". Quedan como faltantes.")
    return Carga(respuestas=respuestas.reset_index(drop=True), ninos=ninos, informe=inf)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_ingest.py -q`
Expected: `77 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/cuidadores/ingest.py tests/test_cuidadores_ingest.py
git commit -m "feat(cuidadores): ingesta con consentimiento, seudónimos, grado, ola e hijo 2" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Deduplicación de cuidadores y de niños

**Files:**
- Modify: `src/cuidadores/ingest.py` (añadir al final)
- Create: `tests/test_cuidadores_dedup.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_dedup.py`:

```python
"""Cuidadores 360 · deduplicación de cuidadores y de niños (spec §5.5)."""
import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import ingest
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(cs.formulario(), k=K)


@pytest.fixture(scope="module")
def dedup(carga):
    return ingest.deduplicar(carga)


def test_deduplicacion(carga, dedup):
    cuid, ninos, inf = dedup
    assert cuid["ID_cuidador"].is_unique and ninos["ID_nino"].is_unique
    assert inf.respuestas_repetidas_cuidador == 1 and inf.cuidadores_en_dos_olas == 1
    assert inf.mismo_nino_misma_respuesta == 1
    assert inf.mismo_nino_otro_cuidador == 1 and inf.mismo_nino_entre_olas == 1
    assert inf.ninos_unicos == len(ninos) == inf.filas_nino - 3
    assert inf.cuidadores_distintos == len(cuid) == inf.respuestas_validas - 1


def test_el_cuidador_repetido_se_queda_con_la_respuesta_mas_reciente(carga, dedup):
    cuid, _, _ = dedup
    resp = carga.respuestas
    repetido = resp["ID_cuidador"][resp["ID_cuidador"].duplicated()].iloc[0]
    assert cuid.loc[cuid["ID_cuidador"] == repetido, "Ola"].item() == "2026"


def test_el_nino_de_dos_cuidadores_se_queda_con_la_mama(carga, dedup):
    _, ninos, _ = dedup
    n = carga.ninos
    compartido = n.groupby("ID_nino")["ID_cuidador"].nunique()
    nino = compartido[compartido > 1].index[0]
    assert ninos.loc[ninos["ID_nino"] == nino, "Quien"].item() == cat.MAMA


def test_prioridad_ola_luego_quien_luego_primer_envio():
    base = dict(ID_cuidador="C00000001", Quien=cat.MAMA, Colegio="LauV", Grado="Quinto",
                Orden_hijo=1)
    filas = [
        dict(base, ID_nino="N00000001", Ola="2025", ts=pd.Timestamp("2025-09-01"), _fila=0,
             Quien=cat.MAMA, ID_cuidador="C00000001"),
        dict(base, ID_nino="N00000001", Ola="2026", ts=pd.Timestamp("2026-03-02"), _fila=1,
             Quien=cat.OTRO, ID_cuidador="C00000002"),
        dict(base, ID_nino="N00000002", Ola="2026", ts=pd.Timestamp("2026-03-01"), _fila=2,
             Quien=cat.PAPA, ID_cuidador="C00000003"),
        dict(base, ID_nino="N00000002", Ola="2026", ts=pd.Timestamp("2026-03-05"), _fila=3,
             Quien=cat.MAMA, ID_cuidador="C00000004"),
        dict(base, ID_nino="N00000003", Ola="2026", ts=pd.Timestamp("2026-03-01"), _fila=4,
             Quien=cat.PAPA, ID_cuidador="C00000005"),
        dict(base, ID_nino="N00000003", Ola="2026", ts=pd.Timestamp("2026-03-09"), _fila=5,
             Quien=cat.PAPA, ID_cuidador="C00000006"),
    ]
    ninos = pd.DataFrame(filas).assign(Grado_detalle="Quinto")
    resp = ninos.drop(columns=["ID_nino", "Orden_hijo", "Grado_detalle"]).drop_duplicates(
        "ID_cuidador")
    _, u, _ = ingest.deduplicar(ingest.Carga(resp, ninos, ingest.InformeCuidadores()))
    elegido = u.set_index("ID_nino")["ID_cuidador"].to_dict()
    assert elegido == {"N00000001": "C00000002",     # la ola más reciente gana a mamá
                       "N00000002": "C00000004",     # mamá antes que papá
                       "N00000003": "C00000005"}     # el primer envío


def test_filtrar_por_ola_antes_de_deduplicar(carga):
    c25, n25, _ = ingest.deduplicar(carga, "2025")
    assert set(c25["Ola"]) == {"2025"} and set(n25["Ola"]) == {"2025"}
    c26, _, _ = ingest.deduplicar(carga, "2026")
    assert len(c25) + len(c26) >= len(ingest.deduplicar(carga)[0])


def test_tras_deduplicar_sigue_sin_nombres_ni_telefono(dedup):
    cuid, ninos, informe = dedup
    for t in (cuid.astype(str).to_csv(), ninos.astype(str).to_csv(), str(informe.como_dict())):
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in t
    assert cuid["ID_cuidador"].str.fullmatch(r"C[0-9a-f]{8}").all()
    assert ninos["ID_nino"].str.fullmatch(r"N[0-9a-f]{8}").all()


def test_conteos_tras_deduplicar(dedup):
    cuid, ninos, inf = dedup
    assert inf.grados == {"Quinto": 21, "Sexto": 20, cat.FUERA_DE_RANGO: 16, "Décimo": 16,
                          "Cuarto": 16, "Octavo": 14, "Séptimo": 9, "Noveno": 9}
    assert inf.colegios_cuidador == {"LauV": 35, "JJC": 24, "SJMEB": 14, "LaBalsa": 12,
                                     "CdP": 4, "OTRO": 3}
```

Run: `.venv/bin/python -m pytest tests/test_cuidadores_dedup.py -q`
Expected: FAIL con `AttributeError: module 'src.cuidadores.ingest' has no attribute 'deduplicar'`.

- [ ] **Step 2: Implementar: añadir al final de `src/cuidadores/ingest.py`**

```python
# ── deduplicación ───────────────────────────────────────────────────────────
def deduplicar(carga: Carga, ola: str | None = None
               ) -> tuple[pd.DataFrame, pd.DataFrame, InformeCuidadores]:
    """(cuidadores, niños, informe) sin repetidos; `ola` filtra antes de deduplicar."""
    import copy
    inf = copy.deepcopy(carga.informe)
    resp, ninos = carga.respuestas, carga.ninos
    if ola:
        resp = resp[resp[OLA_COLUMNA] == ola]
        ninos = ninos[ninos[OLA_COLUMNA] == ola]

    # Cuidadores: la respuesta más reciente (el último envío si empatan).
    orden = resp.sort_values(["ts", "_fila"], na_position="first")
    cuid = orden.drop_duplicates("ID_cuidador", keep="last")
    inf.cuidadores_distintos = len(cuid)
    inf.respuestas_repetidas_cuidador = len(resp) - len(cuid)
    inf.cuidadores_en_dos_olas = int(
        (resp.groupby("ID_cuidador")[OLA_COLUMNA].nunique() > 1).sum())

    # Niños: ola más reciente → mamá, papá, otro → primer envío → hijo 1 antes que 2.
    n = ninos.assign(_prio=ninos["Quien"].map(cat.PRIORIDAD_QUIEN).fillna(9),
                     _ola_orden=pd.to_numeric(ninos[OLA_COLUMNA], errors="coerce").fillna(-1))
    n = n.sort_values(["_ola_orden", "_prio", "ts", "_fila", "Orden_hijo"],
                      ascending=[False, True, True, True, True], na_position="last")
    grupos = n.groupby("ID_nino")
    inf.mismo_nino_misma_respuesta = int(
        (grupos["_fila"].count() - grupos["_fila"].nunique()).sum())
    inf.mismo_nino_otro_cuidador = int((grupos["ID_cuidador"].nunique() > 1).sum())
    inf.mismo_nino_entre_olas = int((grupos[OLA_COLUMNA].nunique() > 1).sum())
    ninos_u = n.drop_duplicates("ID_nino", keep="first").drop(columns=["_prio", "_ola_orden"])
    inf.ninos_unicos = len(ninos_u)

    inf.grados = ninos_u["Grado_detalle"].map(
        lambda g: g if g in cat.GRADOS_ESTUDIO or g == cat.SIN_DATO else cat.FUERA_DE_RANGO
    ).value_counts().to_dict()
    inf.colegios_cuidador = cuid["Colegio"].value_counts().to_dict()
    inf.colegios_nino = ninos_u["Colegio"].value_counts().to_dict()
    return (cuid.drop(columns=["_fila"]).reset_index(drop=True),
            ninos_u.drop(columns=["_fila"]).reset_index(drop=True), inf)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_dedup.py tests/test_cuidadores_ingest.py -q`
Expected: `84 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/cuidadores/ingest.py tests/test_cuidadores_dedup.py
git commit -m "feat(cuidadores): deduplicación (ola, mamá > papá > otro, primer envío)" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Puntuación desde el texto crudo

**Files:**
- Create: `src/cuidadores/scoring.py`
- Create: `tests/test_cuidadores_scoring.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_scoring.py`:

```python
"""Cuidadores 360 · puntuación desde el texto crudo (spec §5.5)."""
import numpy as np
import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import scoring
from src.estudiantes import catalog as cat_est


def _cuidador(**items) -> pd.DataFrame:
    """Un cuidador con todos los ítems en un valor neutro, salvo los indicados."""
    fila = {}
    for b in cat.BLOQUES_CUIDADOR:
        for c in b.columnas:
            fila[c] = b.valor_min
    fila.update(items)
    return pd.DataFrame([fila])


def test_pss_invierte_3_4_5_7_y_9():
    # todo «Nunca» (0): los 5 directos suman 0 y los 5 inversos 4 cada uno → 20
    assert scoring.puntuar_cuidadores(_cuidador())["PSS_Total"].item() == 20
    todo4 = {f"PSS{i}": 4 for i in range(1, 11)}
    assert scoring.puntuar_cuidadores(_cuidador(**todo4))["PSS_Total"].item() == 20
    peor = {f"PSS{i}": (0 if i in cat.PSS_INVERSOS else 4) for i in range(1, 11)}
    assert scoring.puntuar_cuidadores(_cuidador(**peor))["PSS_Total"].item() == 40


def test_pss_prorratea_con_9_y_falta_con_8():
    nueve = _cuidador(PSS7=np.nan)
    assert scoring.puntuar_cuidadores(nueve)["PSS_Total"].item() == pytest.approx(
        (20 - 4) * 10 / 9, abs=0.05)
    ocho = _cuidador(PSS7=np.nan, PSS9=np.nan)
    assert np.isnan(scoring.puntuar_cuidadores(ocho)["PSS_Total"].item())


@pytest.mark.parametrize("total,posible,probable", [(9, 0, 0), (10, 1, 0), (12, 1, 0),
                                                    (13, 1, 1), (30, 1, 1)])
def test_epds_cortes(total, posible, probable):
    items = {f"EPDS{i}": 0 for i in range(1, 11)}
    resto = total
    for i in range(1, 11):
        items[f"EPDS{i}"] = min(3, resto)
        resto -= items[f"EPDS{i}"]
    p = scoring.puntuar_cuidadores(_cuidador(**items))
    assert p["EPDS_Total"].item() == total
    assert (p["EPDS_Posible"].item(), p["EPDS_Probable"].item()) == (posible, probable)


@pytest.mark.parametrize("item10,senal", [(0, 0), (1, 1), (2, 1), (3, 1)])
def test_autolesion_es_cualquier_respuesta_distinta_de_nunca(item10, senal):
    p = scoring.puntuar_cuidadores(_cuidador(EPDS10=item10))
    assert p["EPDS_Autolesion"].item() == senal


def test_epds_incompleta_es_faltante_pero_el_item_10_cuenta():
    p = scoring.puntuar_cuidadores(_cuidador(EPDS3=np.nan, EPDS10=2))
    assert np.isnan(p["EPDS_Total"].item()) and np.isnan(p["EPDS_Probable"].item())
    assert p["EPDS_Autolesion"].item() == 1


def test_mspss_por_fuente_5_4_3():
    items = {f"MSPSS{i}": 5 for i in range(1, 6)}
    items.update({f"MSPSS{i}": 2 for i in range(6, 10)})
    items.update({f"MSPSS{i}": 3 for i in range(10, 13)})
    p = scoring.puntuar_cuidadores(_cuidador(**items))
    assert (p["MSPSS_Otro"].item(), p["MSPSS_Fam"].item(), p["MSPSS_Amigos"].item()) == (5, 2, 3)
    assert p["MSPSS_Total"].item() == pytest.approx((25 + 8 + 9) / 12)


def test_barrio_de_0_a_10():
    p = scoring.puntuar_cuidadores(_cuidador(**{f"BARRIO{i}": 2 for i in range(1, 6)}))
    assert p["BARRIO_Indice"].item() == 10
    assert scoring.puntuar_cuidadores(_cuidador())["BARRIO_Indice"].item() == 0


@pytest.mark.parametrize("nalgadas,cachetadas,correa,senal", [
    (1, 1, 1, 0), (2, 2, 2, 0), (3, 1, 1, 1), (1, 1, 5, 1)])
def test_castigo_fisico_a_veces_o_mas(nalgadas, cachetadas, correa, senal):
    p = scoring.puntuar_cuidadores(_cuidador(APQ22=nalgadas, APQ23=cachetadas, APQ24=correa))
    assert p["APQ_Fisico"].item() == senal


def test_grito_descriptivo():
    assert scoring.puntuar_cuidadores(_cuidador(APQ25=3))["APQ_Grito"].item() == 1
    assert scoring.puntuar_cuidadores(_cuidador(APQ25=2))["APQ_Grito"].item() == 0


def test_estres_parental_no_tiene_total():
    p = scoring.puntuar_cuidadores(_cuidador())
    assert not [c for c in p.columns if c.startswith("EP_") or c in ("EP_Total", "PSI_Total")]


# ══ Niño ════════════════════════════════════════════════════════════════════
def _nino(edad_estado="ok", **items) -> pd.DataFrame:
    fila = {f"SDQ{i}": 0 for i in range(1, 26)}
    fila.update({f"ARI{i}": 0 for i in range(1, 8)})
    fila["_edad_estado"] = edad_estado
    fila.update(items)
    return pd.DataFrame([fila])


def test_sdq_de_padres_con_bandas_de_padres():
    # emocional 5 (ítems 3, 8, 13: 2 + 2 + 1): banda de padres 5–6 = «Alto»; en autoinforme sería «Ligeramente elevado»
    p = scoring.puntuar_ninos(_nino(SDQ3=2, SDQ8=2, SDQ13=1))
    assert p["SDQ_Emo"].item() == 5
    assert p["banda_SDQ_Emo"].item() == 2
    assert cat_est.banda_de(5, "SDQ_Emo", "self") == 1


def test_sdq_inversos_estandar():
    # ítems 7, 11, 14, 21 y 25 invertidos: con todo en 0 suman 2 cada uno
    p = scoring.puntuar_ninos(_nino())
    assert p["SDQ_Con"].item() == 2 and p["SDQ_Pares"].item() == 4 and p["SDQ_Hip"].item() == 4
    assert p["SDQ_Total"].item() == 10


def test_sdq_faltante_si_la_edad_numerica_esta_fuera_de_4_a_17():
    assert np.isnan(scoring.puntuar_ninos(_nino("fuera_de_rango"))["SDQ_Total"].item())
    assert scoring.puntuar_ninos(_nino("no_numerica"))["SDQ_Total"].notna().item()


def test_ari_de_padres_items_1_a_6():
    p = scoring.puntuar_ninos(_nino(ARI1=2, ARI6=2, ARI7=2))
    assert p["ARI_Total"].item() == 4 and p["ARI_Deterioro"].item() == 2
    assert np.isnan(scoring.puntuar_ninos(_nino(ARI3=np.nan))["ARI_Total"].item())


# ══ Tablas ══════════════════════════════════════════════════════════════════
def test_cortes_de_la_epds_anidados_en_una_clave():
    d = pd.DataFrame({"EPDS_Total": [5, 10, 11, 13, 20, np.nan],
                      "EPDS_Autolesion": [0, 0, 1, 0, 1, np.nan]})
    t = scoring.sobre_cortes_cuidador(d)
    epds = t[t["clave"] == "EPDS_Total"]
    assert list(epds["casos"]) == [4, 2] and set(epds["n"]) == {5}
    assert t.loc[t["clave"] == "EPDS_Autolesion", "casos"].item() == 2


def test_las_tablas_tienen_la_forma_de_estudiantes():
    from src.estudiantes import supresion
    d = pd.DataFrame({"EPDS_Total": [5, 10, 11, 13, 20], "SDQ_Total": [1, 15, 18, 22, 30]})
    t = scoring.sobre_cortes_cuidador(d)
    assert {"clave", "indicador", "n", "casos", "pct", "ic_inf", "ic_sup", "fuente"} <= set(t.columns)
    assert supresion.partes_por_familia(t, None)["EPDS_Total"] == (1, 2, 2)


def test_distribucion_de_items():
    d = pd.DataFrame({f"APQ{i}": [1, 3, 5, 4, 2] * 4 for i in range(1, 26)})
    t = scoring.distribucion_items(d, cat.APQ, umbral=3)
    assert len(t) == 25 and set(t["n"]) == {20} and set(t["pct"]) == {60.0}
    assert list(t["columna"][:2]) == [57, 58]
```

Run: `.venv/bin/python -m pytest tests/test_cuidadores_scoring.py -q`
Expected: FAIL con `ImportError: cannot import name 'scoring' from 'src.cuidadores'`.

- [ ] **Step 2: Implementar**

`src/cuidadores/scoring.py`:

```python
"""
Puntuación del formulario «Cuidando al Cuidador» — Observatorio 360.

Todo sale de los ítems que `ingest` convirtió desde el TEXTO crudo de cada
respuesta (spec §5.5). Nada se toma de la codificación heredada
(`Datos_Cuidador_corregido.csv` / `Datos_Cuidador_AUDIT.xlsx`), que es
defectuosa.

Marco cuidador: PSS-10 (0–40, inversos 3, 4, 5, 7 y 9, prorrateo con 9 de 10),
EPDS-10 (0–30, los 10 ítems), señales de ánimo (≥ 10 posible, ≥ 13 probable) y
de autolesión (ítem 10 ≠ «No, nunca»), MSPSS por fuente (media 1–5, 5 / 4 / 3
ítems), índice de riesgo del barrio (0–10), castigo físico (APQ 22–24 «a veces
o más») y grito (APQ 25), descriptivos.

Marco niño: SDQ de padres con las subescalas estándar y las bandas
`BANDS_PARENT`; si la edad es numérica y cae fuera de 4–17, el SDQ es faltante.
ARI de padres: ítems 1–6 (0–12) y deterioro (ítem 7).

Las tablas (`descriptivos`, `sobre_cortes_*`, `terciles`, `fiabilidad`) tienen
la misma forma que las de estudiantes, para que `estudiantes.supresion` y la
vista las traten igual.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import catalog as cat_est
from src.estudiantes import scoring as sc_est
from src.estudiantes.stats import wilson


def _suma_prorrateada(X: pd.DataFrame, minimo: int) -> pd.Series:
    respondidos = X.notna().sum(axis=1)
    s = X.sum(axis=1) * X.shape[1] / respondidos.replace(0, np.nan)
    return s.mask(respondidos < minimo)


def _media_completa(X: pd.DataFrame) -> pd.Series:
    return X.mean(axis=1).mask(X.isna().any(axis=1))


def _indicador(condicion: pd.Series, base: pd.Series) -> pd.Series:
    """1 / 0 donde hay dato; NaN donde no."""
    return condicion.astype(float).where(base)


# ── marco cuidador ─────────────────────────────────────────────────────────
def pss_orientada(d: pd.DataFrame) -> pd.DataFrame:
    X = d[cat.PSS.columnas].copy()
    for i in cat.PSS_INVERSOS:
        X[f"PSS{i}"] = (cat.PSS.valor_min + cat.PSS.valor_max) - X[f"PSS{i}"]
    return X


def puntuar_cuidadores(d: pd.DataFrame) -> pd.DataFrame:
    """Copia con PSS, EPDS, MSPSS, barrio y castigo físico añadidos."""
    out = d.copy()
    nuevas: dict[str, pd.Series] = {}
    nuevas["PSS_Total"] = _suma_prorrateada(pss_orientada(d), cat.PSS_MIN_ITEMS).round(1)
    epds = d[cat.EPDS.columnas]
    total = epds.sum(axis=1).mask(epds.isna().any(axis=1))
    nuevas["EPDS_Total"] = total
    nuevas["EPDS_Posible"] = _indicador(total >= cat.EPDS_POSIBLE, total.notna())
    nuevas["EPDS_Probable"] = _indicador(total >= cat.EPDS_PROBABLE, total.notna())
    item10 = d[f"EPDS{cat.EPDS_ITEM_AUTOLESION}"]
    nuevas["EPDS_Autolesion"] = _indicador(item10 >= 1, item10.notna())
    for clave, items in cat.MSPSS_FUENTES.items():
        nuevas[clave] = _media_completa(d[[f"MSPSS{i}" for i in items]])
    nuevas["MSPSS_Total"] = _media_completa(d[cat.MSPSS.columnas])
    barrio = d[cat.BARRIO.columnas]
    nuevas["BARRIO_Indice"] = barrio.sum(axis=1).mask(barrio.isna().any(axis=1))
    fisico = d[[f"APQ{i}" for i in cat.APQ_FISICO]]
    nuevas["APQ_Fisico"] = _indicador((fisico >= cat.APQ_UMBRAL).any(axis=1),
                                      fisico.notna().all(axis=1))
    grito = d[f"APQ{cat.APQ_GRITO}"]
    nuevas["APQ_Grito"] = _indicador(grito >= cat.APQ_UMBRAL, grito.notna())
    return pd.concat([out, pd.DataFrame(nuevas, index=d.index)], axis=1)


# ── marco niño ─────────────────────────────────────────────────────────────
def puntuar_ninos(d: pd.DataFrame) -> pd.DataFrame:
    """Copia con el SDQ de padres (subescalas, compuestas y bandas) y el ARI-P."""
    out = d.copy()
    sdq_cols = cat_est.SDQ.columnas
    if "_edad_estado" in out.columns:
        fuera = out["_edad_estado"] == "fuera_de_rango"
        out.loc[fuera, sdq_cols] = np.nan
    nuevas: dict[str, pd.Series] = {}
    for sub in cat_est.SDQ.subescalas:
        X = sc_est.items_orientados(out, sub, cat_est.SDQ)
        nuevas[sub.key] = _suma_prorrateada(X, sub.min_items).round(0)
    for clave, c in cat_est.COMPUESTAS.items():
        nuevas[clave] = pd.concat([nuevas[p] for p in c["partes"]], axis=1).sum(
            axis=1, min_count=len(c["partes"]))
    ari = out[[f"ARI{i}" for i in cat.ARI_ITEMS_TOTAL]]
    nuevas["ARI_Total"] = ari.sum(axis=1).mask(ari.isna().any(axis=1))
    nuevas["ARI_Deterioro"] = out[f"ARI{cat.ARI_ITEM_DETERIORO}"]
    out = pd.concat([out, pd.DataFrame(nuevas, index=out.index)], axis=1)
    for key in cat_est.BANDS_PARENT:
        out[f"banda_{key}"] = out[key].map(
            lambda v: cat_est.banda_de(v, key, "parent") if pd.notna(v) else np.nan)
    return out


# ── tablas ─────────────────────────────────────────────────────────────────
def disponibles(d: pd.DataFrame, claves: list[str]) -> list[str]:
    return [k for k in claves if k in d.columns and d[k].notna().any()]


def descriptivos(d: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    filas = []
    for k in disponibles(d, claves):
        v = d[k].dropna()
        p = cat.PUNTUACIONES_POR_CLAVE[k]
        filas.append(dict(
            clave=k, escala=p.label, n=len(v), M=round(float(v.mean()), 2),
            DE=round(float(v.std(ddof=1)), 2) if len(v) > 1 else np.nan,
            Mdn=round(float(v.median()), 2), min=float(v.min()), max=float(v.max()),
            rango=f"{p.rango[0]:g}–{p.rango[1]:g}",
            pct_faltante=round(100 * (1 - len(v) / len(d)), 1) if len(d) else np.nan,
            P25=round(float(v.quantile(.25)), 2), P75=round(float(v.quantile(.75)), 2),
            direccion=p.direccion, fuente=p.fuente))
    return pd.DataFrame(filas)


def fiabilidad(d: pd.DataFrame, n_boot: int = 300) -> pd.DataFrame:
    """α con IC por bootstrap (casos completos), con los ítems ya orientados."""
    conjuntos: dict[str, pd.DataFrame] = {}
    if set(cat.PSS.columnas) <= set(d.columns):
        conjuntos["PSS_Total"] = pss_orientada(d)
    if set(cat.EPDS.columnas) <= set(d.columns):
        conjuntos["EPDS_Total"] = d[cat.EPDS.columnas]
    if set(cat.MSPSS.columnas) <= set(d.columns):
        conjuntos["MSPSS_Total"] = d[cat.MSPSS.columnas]
        for clave, items in cat.MSPSS_FUENTES.items():
            conjuntos[clave] = d[[f"MSPSS{i}" for i in items]]
    if set(cat.BARRIO.columnas) <= set(d.columns):
        conjuntos["BARRIO_Indice"] = d[cat.BARRIO.columnas]
    if set(cat_est.SDQ.columnas) <= set(d.columns):
        for sub in cat_est.SDQ.subescalas:
            conjuntos[sub.key] = sc_est.items_orientados(d, sub, cat_est.SDQ)
        conjuntos["SDQ_Total"] = pd.concat(
            [sc_est.items_orientados(d, cat_est.subescala(s), cat_est.SDQ)
             for s in cat_est.SDQ_SUBS_DIFICULTADES], axis=1)
    ari_cols = [f"ARI{i}" for i in cat.ARI_ITEMS_TOTAL]
    if set(ari_cols) <= set(d.columns):
        conjuntos["ARI_Total"] = d[ari_cols]
    filas = []
    for clave, X in conjuntos.items():
        a, lo, hi, n = sc_est.alpha_ci(X, n_boot=n_boot)
        filas.append(dict(clave=clave, escala=cat.label(clave), n_items=X.shape[1], n=n,
                          alpha=round(a, 3) if not np.isnan(a) else None,
                          ic_inf=round(lo, 3) if not np.isnan(lo) else None,
                          ic_sup=round(hi, 3) if not np.isnan(hi) else None))
    return pd.DataFrame(filas)


def _agrega(filas: list, clave: str, etiqueta: str, mask: pd.Series, base: pd.Series,
            fuente: str) -> None:
    base_n = int(base.sum())
    if base_n == 0:
        return
    k = int((mask & base).sum())
    p, lo, hi = wilson(k, base_n)
    filas.append(dict(clave=clave, indicador=etiqueta, n=base_n, casos=k, pct=p,
                      ic_inf=lo, ic_sup=hi, fuente=fuente))


def sobre_cortes_cuidador(d: pd.DataFrame) -> pd.DataFrame:
    """Prevalencias del marco cuidador (forma de estudiantes.scoring.sobre_cortes).

    Las dos filas de la EPDS comparten la clave «EPDS_Total»: son cortes
    anidados de la misma escala y la supresión las reparte en tres partes.
    """
    filas: list = []
    if "EPDS_Total" in d.columns:
        t = d["EPDS_Total"]
        _agrega(filas, "EPDS_Total", f"Ánimo: posible (EPDS ≥ {cat.EPDS_POSIBLE})",
                t >= cat.EPDS_POSIBLE, t.notna(), cat.EPDS.fuente)
        _agrega(filas, "EPDS_Total", f"Ánimo: probable (EPDS ≥ {cat.EPDS_PROBABLE})",
                t >= cat.EPDS_PROBABLE, t.notna(), cat.EPDS.fuente)
    if "EPDS_Autolesion" in d.columns:
        a = d["EPDS_Autolesion"]
        _agrega(filas, "EPDS_Autolesion",
                "Autolesión: pensó en hacerse daño (ítem 10 distinto de «No, nunca»)",
                a == 1, a.notna(), "EPDS ítem 10; señal para indagar, no diagnóstico")
    if "APQ_Fisico" in d.columns:
        f = d["APQ_Fisico"]
        _agrega(filas, "APQ_Fisico", "Usa alguna forma de castigo físico, a veces o más",
                f == 1, f.notna(), "APQ ítems 22–24 (columnas 78–80); descriptivo")
    if "APQ_Grito" in d.columns:
        g = d["APQ_Grito"]
        _agrega(filas, "APQ_Grito", "Grita al hijo cuando se porta mal, a veces o más",
                g == 1, g.notna(), "APQ ítem 25 (columna 81); descriptivo")
    for k in ("MSPSS_Total", "MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro"):
        if k in d.columns:
            _agrega(filas, k, f"{cat.label(k)}: media por debajo de 3 (descriptivo)",
                    d[k] < 3, d[k].notna(),
                    "Umbral descriptivo (punto medio de la escala), no clínico")
    return pd.DataFrame(filas)


def sobre_cortes_nino(d: pd.DataFrame) -> pd.DataFrame:
    """SDQ de padres «alto o muy alto» por subescala, con las bandas de padres."""
    filas: list = []
    for key in cat_est.BANDS_PARENT:
        if key not in d.columns:
            continue
        b = d[key].map(lambda x: cat_est.banda_de(x, key, "parent") if pd.notna(x) else np.nan)
        etiqueta = ("Prosocial bajo o muy bajo" if key == "SDQ_Pro"
                    else f"{cat.label(key)}: alto o muy alto")
        _agrega(filas, key, etiqueta, b >= 2, d[key].notna(),
                "Scoring the SDQ for age 4-17, versión para padres, sdqinfo.org")
    return pd.DataFrame(filas)


def bandas_nino(d: pd.DataFrame) -> pd.DataFrame:
    """Bandas del SDQ de padres (misma forma que estudiantes)."""
    t = sc_est.distribucion_bandas(d, "parent")
    if not t.empty:
        t["escala"] = t["clave"].map(cat.label)
    return t


def terciles(d: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for k in cat.CLAVES_TERCILES:
        if k not in d.columns:
            continue
        v = d[k].dropna()
        if len(v) < cat.MIN_GROUP_N:
            continue
        filas.append(dict(clave=k, escala=cat.label(k), n=len(v),
                          corte_bajo=round(float(v.quantile(1 / 3)), 2),
                          corte_alto=round(float(v.quantile(2 / 3)), 2),
                          nota="Relativo a esta muestra, no clínico"))
    return pd.DataFrame(filas)


# ── ítems descriptivos (solo vista local de investigadores) ────────────────
def distribucion_items(d: pd.DataFrame, bloque: cat.Bloque, enunciados: list[str] | None = None,
                       umbral: int | None = None) -> pd.DataFrame:
    """Por ítem: n, media y % con respuesta ≥ umbral (sin conteos de casos)."""
    filas = []
    for i, col in enumerate(bloque.columnas, start=1):
        if col not in d.columns:
            continue
        v = d[col].dropna()
        if v.empty:
            continue
        fila = dict(item=i, columna=bloque.inicio + i - 1,
                    enunciado=(enunciados[i - 1] if enunciados else col),
                    n=len(v), M=round(float(v.mean()), 2))
        if umbral is not None:
            k = int((v >= umbral).sum())
            fila["casos"] = k                     # se quita antes de mostrar
            fila["pct"] = round(100 * k / len(v), 1)
        filas.append(fila)
    return pd.DataFrame(filas)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_scoring.py -q`
Expected: `27 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/cuidadores/scoring.py tests/test_cuidadores_scoring.py
git commit -m "feat(cuidadores): PSS, EPDS, MSPSS 5/4/3, barrio, castigo físico, SDQ y ARI de padres" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Base publicable que cuenta cuidadores distintos

**Files:**
- Create: `src/cuidadores/privacidad.py`
- Create: `tests/test_cuidadores_privacidad.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_privacidad.py`:

```python
"""Cuidadores 360 · base publicable contando cuidadores distintos (spec §4, §5.1)."""
import numpy as np
import pandas as pd

from src.cuidadores import privacidad
from src.estudiantes import privacidad as priv_est


def _marco(filas: list[tuple[str, str, int, int]]) -> pd.DataFrame:
    """[(colegio, grado, cuidadores, niños por cuidador)] → una fila por niño."""
    out, c = [], 0
    for colegio, grado, cuidadores, hijos in filas:
        for _ in range(cuidadores):
            for h in range(hijos):
                out.append(dict(ID_cuidador=f"C{c:08x}", ID_nino=f"N{c:06x}{h:02x}",
                                Colegio=colegio, Grado=grado, X=float(c % 7)))
            c += 1
    return pd.DataFrame(out)


def test_con_un_cuidador_por_fila_es_la_base_de_estudiantes():
    d = _marco([("A", "Quinto", 12, 1), ("A", "Sexto", 6, 1), ("B", "Quinto", 15, 1),
                ("C", "Sexto", 4, 1), ("D", "Quinto", 5, 1)])
    a, b = privacidad.base_publicable(d), priv_est.base_publicable(d)
    assert a.celdas.keys() == b.celdas.keys() and a.colegios.keys() == b.colegios.keys()
    assert a.grados.keys() == b.grados.keys()
    assert a.nivel.equals(b.nivel) and a.incluye_resto == b.incluye_resto


def test_el_minimo_cuenta_cuidadores_no_ninos():
    # 6 cuidadores con 2 hijos cada uno = 12 filas, pero 6 personas: no se publica
    d = _marco([("A", "Quinto", 6, 2), ("A", "Sexto", 10, 1), ("B", "Quinto", 12, 1)])
    base = privacidad.base_publicable(d)
    assert "A|Quinto" not in base.celdas and "A|Sexto" in base.celdas
    assert priv_est.base_publicable(d).celdas.keys() >= {"A|Quinto"}   # la de estudiantes sí


def test_otro_y_sin_dato_nunca_son_grupo():
    d = _marco([("OTRO", "Quinto", 15, 1), ("SIN_DATO", "Sexto", 12, 1), ("A", "Quinto", 11, 1)])
    base = privacidad.base_publicable(d)
    assert set(base.colegios) == {"A"} and set(base.celdas) == {"A|Quinto"}


def test_el_resto_cuenta_cuidadores_distintos():
    # resto: 2 colegios, 5 cuidadores con 2 hijos (10 filas): no llega a 10 personas
    d = _marco([("A", "Quinto", 12, 1), ("B", "Quinto", 3, 2), ("C", "Sexto", 2, 2)])
    base = privacidad.base_publicable(d)
    assert not base.incluye_resto
    assert len(base.nivel) == 12


def test_todo_o_nada_cuenta_cuidadores():
    d = _marco([("A", "Quinto", 12, 1), ("A", "Sexto", 10, 2)])
    # en A|Sexto solo 5 cuidadores tienen dato (10 filas)
    sexto = d.index[(d["Grado"] == "Sexto")]
    con_dato = d.loc[sexto, "ID_cuidador"].drop_duplicates().index[:5]
    quitar = sexto.difference(d.index[d["ID_cuidador"].isin(d.loc[con_dato, "ID_cuidador"])])
    d.loc[quitar, "X"] = np.nan
    base = privacidad.base_publicable(d)
    dm, sup = privacidad.aplicar_todo_o_nada(d, base)
    assert dm.loc[sexto, "X"].isna().all() and sup == {"X": 10}
    assert dm.loc[d["Grado"] == "Quinto", "X"].notna().all()


def test_las_columnas_de_identificacion_no_se_tocan():
    d = _marco([("A", "Quinto", 12, 1)]).assign(Quien="Mamá", Ola="2026", Edad=9.0)
    assert privacidad.columnas_de_analisis(d) == ["X"]


def test_distintos_por_grupo():
    d = _marco([("A", "Quinto", 3, 2), ("B", "Sexto", 4, 1)])
    assert privacidad.distintos_por_grupo(d, "Colegio") == {"A": 3, "B": 4}
```

Run: `.venv/bin/python -m pytest tests/test_cuidadores_privacidad.py -q`
Expected: FAIL con `ImportError: cannot import name 'privacidad' from 'src.cuidadores'`.

- [ ] **Step 2: Implementar**

`src/cuidadores/privacidad.py`:

```python
"""
Base publicable de Cuidadores 360 — el mínimo cuenta CUIDADORES DISTINTOS.

Misma regla que `estudiantes.privacidad` (spec §5.1), con una diferencia
(spec §4): en el marco de niños dos filas pueden ser del mismo cuidador (sus
dos hijos), y lo que identifica a alguien es el adulto que respondió. Por eso
cada umbral de `MIN_GROUP_N` se cuenta con `nunique` de `ID_cuidador`:

  · celda colegio × grado publicable si reúne ≥ 10 cuidadores distintos;
  · colegio = unión de sus celdas; sin celdas, el colegio completo si llega;
  · grado = unión de sus celdas;
  · nivel = todos si el resto R es vacío o reúne ≥ 10 cuidadores de ≥ 2
    colegios con margen `MARGEN_RESTO` sobre su colegio más grande;
  · «OTRO» (colegio escrito a mano que no se reconoce) y «SIN_DATO» no son
    colegios: nunca forman celda ni colegio y solo cuentan en el total;
  · todo o nada por indicador: una unidad con 1 a 9 cuidadores con dato en un
    indicador pierde ese indicador.

Devuelve un `estudiantes.privacidad.Base`, así que `filas`, `relaciones`,
`unidades`, `estudiantes.supresion` y la vista lo usan sin cambios. En el
marco de cuidadores (una fila por cuidador) el resultado es idéntico al de
estudiantes, y hay una prueba que lo comprueba.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import privacidad as priv

UNIDAD = "ID_cuidador"
# Códigos que no son un colegio: nunca forman celda ni colegio publicable.
# Sus respuestas cuentan en el total del marco (como resto), si el resto llega.
COLEGIOS_SIN_GRUPO = ("OTRO", "SIN_DATO")
COLUMNAS_ID = ("ID_cuidador", "ID_nino", "ts", "Ola", "Quien", "Colegio", "Colegio_nombre",
               "Sede", "Grado", "Grado_detalle", "Grado_estado", "Orden_hijo", "Edad",
               "Sexo", *cat.CONTEXTO)


def _distintos(d: pd.DataFrame, idx) -> int:
    if UNIDAD not in d.columns:
        return len(idx)
    return int(d.loc[idx, UNIDAD].nunique())


def columnas_de_analisis(d: pd.DataFrame) -> list[str]:
    """Columnas numéricas con cifras: sin identificación, contexto ni «_…»."""
    return [c for c in d.columns
            if c not in COLUMNAS_ID and not str(c).startswith("_")
            and pd.api.types.is_numeric_dtype(d[c])]


def _resto_suficiente(d: pd.DataFrame, idx, minimo: int) -> bool:
    sub = d.loc[idx]
    if _distintos(d, idx) < minimo:
        return False
    por_colegio = sub.groupby("Colegio")[UNIDAD].nunique() if UNIDAD in sub.columns \
        else sub["Colegio"].value_counts()
    if len(por_colegio) < 2:
        return False
    return _distintos(d, idx) - int(por_colegio.max()) >= priv.MARGEN_RESTO


def base_publicable(d: pd.DataFrame, minimo: int = cat.MIN_GROUP_N) -> priv.Base:
    priv._exigir_indice_unico(d)
    b = priv.Base(n_total=len(d))
    if d.empty or not {"Colegio", "Grado"} <= set(d.columns):
        b.nivel = d.index
        return b
    agrupable = d[~d["Colegio"].isin(COLEGIOS_SIN_GRUPO)]
    for (colegio, grado), sub in agrupable.groupby(["Colegio", "Grado"]):
        if _distintos(d, sub.index) >= minimo:
            b.celdas[priv.clave_celda(colegio, grado)] = sub.index
    for colegio, sub in agrupable.groupby("Colegio"):
        propias = [i for k, i in b.celdas.items() if priv.partir_celda(k)[0] == str(colegio)]
        if propias:
            b.colegios[str(colegio)] = priv.union(propias)
        elif _distintos(d, sub.index) >= minimo:
            b.colegios[str(colegio)] = sub.index
    for grado in d["Grado"].dropna().unique():
        propias = [i for k, i in b.celdas.items() if priv.partir_celda(k)[1] == str(grado)]
        if propias:
            b.grados[str(grado)] = priv.union(propias)
    publicado = priv.union(b.colegios.values())
    resto = d.index.difference(publicado)
    b.incluye_resto = len(resto) == 0 or _resto_suficiente(d, resto, minimo)
    b.nivel = d.index if b.incluye_resto else publicado
    return b


def aplicar_todo_o_nada(d: pd.DataFrame, base: priv.Base, columnas: list[str] | None = None,
                        minimo: int = cat.MIN_GROUP_N) -> tuple[pd.DataFrame, dict]:
    """Como `estudiantes.privacidad.aplicar_todo_o_nada`, contando cuidadores distintos."""
    priv._exigir_indice_unico(d)
    dm = d.copy()
    columnas = columnas_de_analisis(d) if columnas is None else columnas
    lista = priv.unidades(base)
    en_unidades = priv.union(i for _, i in lista)
    resto = (d.index.intersection(base.nivel).difference(en_unidades)
             if base.incluye_resto else d.index[:0])
    grupos = [d.index.intersection(i) for _, i in lista]
    suprimidos: dict = {}
    for col in columnas:
        if col not in d.columns:
            continue
        validos = d[col].notna()
        borrar = []
        for idx in grupos:
            n = _distintos(d, idx[validos.loc[idx].to_numpy()])
            if 0 < n < minimo:
                borrar.append(idx)
        if len(resto):
            v_resto = resto[validos.loc[resto].to_numpy()]
            if len(v_resto) and not _resto_suficiente(d, v_resto, minimo):
                borrar.append(resto)
        if not borrar:
            continue
        idx = priv.union(borrar)
        n = int(validos.loc[idx].sum())
        if n:
            dm.loc[idx, col] = np.nan
            suprimidos[col] = n
    return dm, suprimidos


def distintos_por_grupo(d: pd.DataFrame, columna: str) -> dict:
    """{grupo: cuidadores distintos}."""
    if d.empty or columna not in d.columns:
        return {}
    return {str(k): int(v) for k, v in d.groupby(columna)[UNIDAD].nunique().items()}
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_privacidad.py tests/test_privacidad.py -q`
Expected: todo pasa (`7 passed` de las nuevas; `test_privacidad.py` de estudiantes sigue igual).

- [ ] **Step 4: Commit**

```bash
git add src/cuidadores/privacidad.py tests/test_cuidadores_privacidad.py
git commit -m "feat(cuidadores): base publicable y todo o nada por cuidadores distintos" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Pipeline con dos marcos y supresión

**Files:**
- Create: `src/cuidadores/pipeline.py`
- Create: `tests/test_cuidadores_pipeline.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_pipeline.py`:

```python
"""Cuidadores 360 · pipeline con dos marcos, base publicable y supresión (spec §4, §5.5)."""
import copy

import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import ingest, pipeline
from src.estudiantes import catalog as cat_est
from src.estudiantes import pipeline as pipe_est
from src.estudiantes import supresion
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(cs.formulario(), k=K)


@pytest.fixture(scope="module")
def ac(carga):
    return pipeline.analizar(carga, n_boot=20)


def test_dos_marcos_con_la_clase_de_estudiantes(ac):
    assert isinstance(ac.cuidador, pipe_est.Analisis) and isinstance(ac.nino, pipe_est.Analisis)
    assert ac.cuidador.nivel == cat.MARCO_CUIDADOR and ac.nino.nivel == cat.MARCO_NINO
    assert set(ac.marcos) == {cat.MARCO_CUIDADOR, cat.MARCO_NINO}
    assert ac.cuidador.n == ac.informe.cuidadores_distintos
    assert ac.nino.n == ac.informe.ninos_unicos
    assert ac.olas == ["2025", "2026"]


def test_grupos_publicados_segun_la_configuracion_sintetica(ac):
    for a in ac.marcos.values():
        sub = a.subgrupos
        assert set(sub["Colegio×Grado"]) == {"LauV|Quinto", "LauV|Sexto", "LauV|Octavo",
                                             "JJC|Décimo", "JJC|Cuarto"}
        # SJMEB entero (sin celdas), La Balsa entera (sin grado del estudio)
        assert set(sub["Colegio"]) == {"LauV", "JJC", "SJMEB", "LaBalsa"}
        assert "CdP" not in sub["Colegio"] and "OTRO" not in sub["Colegio"]
        assert not a.base.incluye_resto          # CdP 4 + OTRO 3 no llegan a 10


def test_todo_grupo_publicado_tiene_10_o_mas_cuidadores_distintos(ac):
    for a in ac.marcos.values():
        d = a.datos
        for agrupacion, grupos in a.subgrupos.items():
            for grupo, s in grupos.items():
                assert s.muestra["n_cuidadores"] >= cat.MIN_GROUP_N, (agrupacion, grupo)
        for _, idx in [*a.base.celdas.items(), *a.base.colegios.items(), *a.base.grados.items()]:
            assert d.loc[idx, "ID_cuidador"].nunique() >= cat.MIN_GROUP_N


def test_ninguna_proporcion_publicada_delata(ac):
    for a in ac.marcos.values():
        assert a.supresion_aplicada
        objetos = [a] + [s for g in a.subgrupos.values() for s in g.values()]
        for o in objetos:
            t = o.cortes
            if t is None or t.empty:
                continue
            for _, f in t[t["pct"].notna()].iterrows():
                assert supresion.proporcion_publicable(f["casos"], f["n"]), (o.n, f["clave"])


def test_cortes_y_bandas_por_marco(ac):
    claves_c = set(ac.cuidador.cortes["clave"])
    assert {"EPDS_Total", "EPDS_Autolesion", "APQ_Fisico", "APQ_Grito"} <= claves_c
    assert set(ac.nino.cortes["clave"]) == set(cat_est.BANDS_PARENT)
    assert set(ac.nino.bandas["clave"]) == set(cat_est.BANDS_PARENT)
    assert ac.cuidador.bandas.empty


def test_puntuaciones_disponibles(ac):
    assert set(ac.cuidador.descriptivos["clave"]) == set(cat.CLAVES_CUIDADOR)
    assert set(ac.nino.descriptivos["clave"]) == set(cat.CLAVES_NINO)


def test_los_datos_enmascarados_no_llevan_nombres_ni_telefono(ac):
    for a in ac.marcos.values():
        texto = a.datos.astype(str).to_csv()
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in texto


def test_filtro_de_ola(carga):
    a25 = pipeline.analizar(carga, ola="2025", n_boot=10)
    a26 = pipeline.analizar(carga, ola="2026", n_boot=10)
    assert a25.ola == "2025" and set(a25.cuidador.datos["Ola"]) == {"2025"}
    assert set(a26.nino.datos["Ola"]) == {"2026"}
    assert a25.cuidador.n + a26.cuidador.n == ac_n_sin_dedup(carga)


def ac_n_sin_dedup(carga) -> int:
    r = carga.respuestas
    return int(r.groupby("Ola")["ID_cuidador"].nunique().sum())


def test_items_locales_sin_conteos(ac):
    assert len(ac.items_apq) == 25 and "casos" not in ac.items_apq.columns
    assert len(ac.items_estres) == 39 and "casos" not in ac.items_estres.columns
    notas = ac.items_estres.set_index("item")["nota"]
    assert notas[22] == "elección forzada partida" and notas[36] == "redactado en positivo"


def test_localizar_formulario(tmp_path):
    assert pipeline.localizar_formulario(str(tmp_path)) is None
    ruta = cs.escribir(tmp_path / "Cuidando al Cuidador - Parentalidad (respuestas).xlsx")
    (tmp_path / "otro.xlsx").write_bytes(b"")
    assert pipeline.localizar_formulario(str(tmp_path)) == ruta
    assert pipeline.localizar_formulario(str(tmp_path / "no-existe")) is None


def test_cargar_y_analizar_desde_disco(tmp_path, monkeypatch):
    monkeypatch.setenv("OBS360_CLAVE_HMAC", cs.CLAVE_PRUEBA)
    ruta = cs.escribir(tmp_path / "Cuidando al Cuidador (respuestas).xlsx")
    ac = pipeline.cargar_y_analizar(ruta, n_boot=10)
    assert ac.cuidador.n == ac.informe.cuidadores_distintos


def test_sin_archivo_hay_un_error_claro(monkeypatch, tmp_path):
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Cuidando al Cuidador"):
        pipeline.cargar_y_analizar()


def test_estudiantes_no_cambia_al_correr_cuidadores(carga):
    """Regresión: cuidadores lee el catálogo de estudiantes pero nunca lo modifica."""
    antes = copy.deepcopy((cat_est.BANDS_PARENT, cat_est.BANDS_SELF, cat_est.COMPUESTAS,
                           cat_est.MIN_GROUP_N, cat_est.ORDEN_GRADOS_PRI,
                           cat_est.ORDEN_GRADOS_SEC, [e.key for e in cat_est.ESCALAS]))
    pipeline.analizar(carga, n_boot=5)
    despues = (cat_est.BANDS_PARENT, cat_est.BANDS_SELF, cat_est.COMPUESTAS,
               cat_est.MIN_GROUP_N, cat_est.ORDEN_GRADOS_PRI, cat_est.ORDEN_GRADOS_SEC,
               [e.key for e in cat_est.ESCALAS])
    assert antes == despues


def test_items_publicables_quita_el_conteo_y_los_pct_que_delatan():
    t = pd.DataFrame({"item": [1, 2, 3], "n": [20, 20, 20], "casos": [10, 2, 18],
                      "pct": [50.0, 10.0, 90.0]})
    p = pipeline._items_publicables(t)
    assert "casos" not in p.columns
    assert p["pct"].tolist()[0] == 50.0 and p["pct"].isna().tolist()[1:] == [True, True]
```

Run: `.venv/bin/python -m pytest tests/test_cuidadores_pipeline.py -q`
Expected: FAIL con `ImportError: cannot import name 'pipeline' from 'src.cuidadores'`.

- [ ] **Step 2: Implementar**

`src/cuidadores/pipeline.py`:

```python
"""
Orquestación de Cuidadores 360 — Observatorio 360.

`analizar(carga, ola)` produce un `AnalisisCuidadores` con dos marcos:

  · `cuidador`: una fila por cuidador distinto (lo que el adulto dice de sí
    mismo: estrés, ánimo, apoyo, barrio, castigo físico).
  · `nino`: una fila por niño distinto (lo que el cuidador dice del niño: SDQ
    y ARI de padres).

Cada marco es un `estudiantes.pipeline.Analisis` (misma clase, mismas tablas),
calculado sobre la base publicable que cuenta cuidadores distintos
(`cuidadores.privacidad`) y pasado por la supresión general de cifras pequeñas
(`estudiantes.supresion.aplicar`). Así la vista de investigadores, la de
comunidad (4b) y la publicación (4b) leen lo mismo que en estudiantes.

`ola` filtra antes de deduplicar. Solo existe en local: no se publica por ola.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd

from src.cuidadores import catalog as cat
from src.cuidadores import ingest, privacidad, scoring
from src.estudiantes import pipeline as pipe_est
from src.estudiantes import privacidad as priv_est
from src.estudiantes import stats, supresion

EXTENSIONES = (".xlsx", ".xls", ".csv")
CORR_CUIDADOR = ["PSS_Total", "EPDS_Total", "MSPSS_Otro", "MSPSS_Fam", "MSPSS_Amigos",
                 "BARRIO_Indice"]
SEXO_A_STATS = {"Niña": "Mujer", "Niño": "Hombre"}
CORR_NINO = ["SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro", "ARI_Total"]


@dataclass
class AnalisisCuidadores:
    """Resultado completo del módulo de cuidadores."""
    cuidador: pipe_est.Analisis
    nino: pipe_est.Analisis
    informe: ingest.InformeCuidadores
    ola: str | None = None
    olas: list = field(default_factory=list)
    # Solo locales (vista de investigadores): ítems del APQ y del estrés
    # parental, ya filtrados por la regla de cifras pequeñas.
    items_apq: pd.DataFrame = field(default_factory=pd.DataFrame)
    items_estres: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def marcos(self) -> dict:
        return {cat.MARCO_CUIDADOR: self.cuidador, cat.MARCO_NINO: self.nino}


def localizar_formulario(base: str | None = None) -> str | None:
    """La exportación más reciente de «Cuidando al Cuidador» en la carpeta de datos."""
    from src.core.rutas import carpeta_datos
    from src.core.texto import norm_txt
    base = base or carpeta_datos("cuidadores")
    if not os.path.isdir(base):
        return None
    candidatos = [os.path.join(base, f) for f in os.listdir(base)
                  if f.lower().endswith(EXTENSIONES) and cat.PATRON_ARCHIVO in norm_txt(f)]
    return max(candidatos, key=os.path.getmtime) if candidatos else None


def _muestra(d: pd.DataFrame, base, suprimidos: dict, marco: str) -> dict:
    m = dict(
        n=len(d),
        n_cuidadores=int(d["ID_cuidador"].nunique()) if len(d) else 0,
        ola=d["Ola"].value_counts().sort_index().to_dict(),
        quien=d["Quien"].value_counts().to_dict(),
        colegio=privacidad.distintos_por_grupo(d, "Colegio"),
        grado=privacidad.distintos_por_grupo(d, "Grado"),
        colegio_grado={priv_est.clave_celda(c, g): int(n) for (c, g), n in
                       d.groupby(["Colegio", "Grado"])["ID_cuidador"].nunique().items()},
        base=base.resumen(),
        suprimidos=suprimidos,
        fechas=([str(d["ts"].min().date()), str(d["ts"].max().date())]
                if "ts" in d.columns and d["ts"].notna().any() else []),
    )
    if marco == cat.MARCO_NINO:
        m["sexo"] = d["Sexo"].value_counts().to_dict()
        m["edad_M"] = round(float(d["Edad"].mean()), 2) if d["Edad"].notna().any() else None
        m["grado_detalle"] = d["Grado_detalle"].value_counts().to_dict()
    return m


def _subgrupos(dm: pd.DataFrame, marco: str, claves: list[str], base) -> dict:
    """Las tablas de cada colegio, grado y celda (bandas y cortes), sobre la base."""
    salida: dict = {}
    for columna, grupos in (("Colegio", base.colegios), ("Grado", base.grados),
                            (priv_est.AGRUPACION_CRUCE, base.celdas)):
        for grupo, idx in grupos.items():
            sub = dm.loc[idx]
            s = pipe_est.Analisis(nivel=marco, n=len(sub), datos=pd.DataFrame(),
                                  escalas=list(claves),
                                  muestra=dict(n=len(sub),
                                               n_cuidadores=int(sub["ID_cuidador"].nunique())))
            if marco == cat.MARCO_NINO:
                s.bandas = scoring.bandas_nino(sub)
                s.cortes = scoring.sobre_cortes_nino(sub)
            else:
                s.cortes = scoring.sobre_cortes_cuidador(sub)
            salida.setdefault(columna, {})[str(grupo)] = s
    return salida


def _por_sexo(dn: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """Niñas frente a niños con `stats.comparar_por_sexo`, que espera «Mujer» y «Hombre»."""
    t = stats.comparar_por_sexo(dn.assign(Sexo=dn["Sexo"].map(SEXO_A_STATS)), claves)
    if t.empty:
        return t
    t = t.rename(columns=lambda c: c.replace("_mujer", "_niña").replace("_hombre", "_niño"))
    t["escala"] = t["clave"].map(cat.label)
    return t


def analizar_marco(d: pd.DataFrame, marco: str, n_boot: int = 300,
                   avisos: list | None = None) -> pipe_est.Analisis:
    """Un marco ya puntuado → `Analisis` sobre la base publicable, con supresión."""
    d = d.reset_index(drop=True)
    claves_marco = cat.CLAVES_NINO if marco == cat.MARCO_NINO else cat.CLAVES_CUIDADOR
    claves = scoring.disponibles(d, claves_marco)
    base = privacidad.base_publicable(d)
    dm, suprimidos = privacidad.aplicar_todo_o_nada(d, base)
    dn = dm.loc[base.nivel]
    a = pipe_est.Analisis(nivel=marco, n=len(d), datos=dm, escalas=claves,
                          avisos=list(avisos or []))
    a.base = base
    a.muestra = _muestra(d, base, suprimidos, marco)
    a.descriptivos = scoring.descriptivos(dn, claves)
    a.fiabilidad = scoring.fiabilidad(dn, n_boot=n_boot)
    if marco == cat.MARCO_NINO:
        a.bandas = scoring.bandas_nino(dn)
        a.cortes = scoring.sobre_cortes_nino(dn)
        corr = [c for c in CORR_NINO if c in claves]
    else:
        a.cortes = scoring.sobre_cortes_cuidador(dn)
        corr = [c for c in CORR_CUIDADOR if c in claves]
    a.terciles = scoring.terciles(dn)
    a.correlaciones = stats.correlaciones(dn, corr)
    if not a.correlaciones.empty:
        a.correlaciones["etiqueta_a"] = a.correlaciones["a"].map(cat.label)
        a.correlaciones["etiqueta_b"] = a.correlaciones["b"].map(cat.label)
    a.matriz = stats.matriz_correlaciones(dn, corr)
    en_grados = dm.loc[priv_est.union(base.grados.values())]
    en_colegios = dm.loc[priv_est.union(base.colegios.values())]
    a.por_grado, _ = stats.comparar_por_grupo(en_grados, claves, "Grado",
                                              list(cat.GRADOS_ESTUDIO))
    a.por_colegio, _ = stats.comparar_por_grupo(en_colegios, claves, "Colegio")
    for t in (a.por_grado, a.por_colegio):
        if not t.empty:
            t["escala"] = t["clave"].map(cat.label)
    if marco == cat.MARCO_NINO:
        a.por_sexo = _por_sexo(dn, claves)
    a.enmascarados = {
        "Grado": sorted(set(map(str, d["Grado"].dropna().unique())) - set(base.grados)),
        "Colegio": sorted(set(map(str, d["Colegio"].dropna().unique())) - set(base.colegios)),
    }
    a.icc = {k: stats.icc_entre_grupos(dn, k) for k in claves}
    a.subgrupos = _subgrupos(dm, marco, claves, base)
    supresion.aplicar(a)
    return a


def _items_publicables(t: pd.DataFrame) -> pd.DataFrame:
    """Quita el % de los ítems con menos de MIN_CASOS casos o no casos; nunca deja `casos`."""
    if t.empty:
        return t
    t = t.copy()
    if "casos" in t.columns:
        ok = [supresion.proporcion_publicable(k, n) for k, n in zip(t["casos"], t["n"])]
        t.loc[[not x for x in ok], "pct"] = float("nan")
        t = t.drop(columns=["casos"])
    return t


def analizar(carga: ingest.Carga, ola: str | None = None, n_boot: int = 300
             ) -> AnalisisCuidadores:
    cuid, ninos, informe = ingest.deduplicar(carga, ola)
    cuid_p = scoring.puntuar_cuidadores(cuid)
    ninos_p = scoring.puntuar_ninos(ninos)
    avisos_c = [cat.AVISO_EPDS, cat.AVISO_APQ, cat.AVISO_MSPSS]
    avisos_n = [cat.AVISO_SDQ_EDAD, cat.AVISO_ARI]
    a_c = analizar_marco(cuid_p, cat.MARCO_CUIDADOR, n_boot=n_boot, avisos=avisos_c)
    a_n = analizar_marco(ninos_p, cat.MARCO_NINO, n_boot=n_boot, avisos=avisos_n)
    dn = a_c.datos.loc[a_c.base.nivel]
    items_apq = scoring.distribucion_items(dn, cat.APQ, informe.enunciados.get("APQ"),
                                           umbral=cat.APQ_UMBRAL)
    items_estres = scoring.distribucion_items(dn, cat.EP, informe.enunciados.get("EP"),
                                              umbral=cat.MAP_ACUERDO["de acuerdo"])
    if not items_estres.empty:
        items_estres["nota"] = items_estres["item"].map(
            lambda i: "elección forzada partida" if i in cat.EP_ELECCION_FORZADA
            else ("redactado en positivo" if i in cat.EP_POSITIVO else ""))
    olas = sorted(o for o in carga.respuestas["Ola"].dropna().unique() if o != cat.SIN_DATO)
    return AnalisisCuidadores(cuidador=a_c, nino=a_n, informe=informe, ola=ola, olas=olas,
                              items_apq=_items_publicables(items_apq),
                              items_estres=_items_publicables(items_estres))


def cargar_y_analizar(ruta: str | None = None, ola: str | None = None,
                      n_boot: int = 300) -> AnalisisCuidadores:
    ruta = ruta or localizar_formulario()
    if not ruta:
        raise FileNotFoundError(
            "No se encontró la exportación de «Cuidando al Cuidador» en la carpeta "
            "de datos fuente (ver src/core/rutas.py y OBS360_DATOS_DIR).")
    return analizar(ingest.cargar(ruta), ola=ola, n_boot=n_boot)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_pipeline.py -q`
Expected: `14 passed`.

- [ ] **Step 4: Comprobar los fragmentos de `VERIFICAR` contra el encabezado real**

Solo lee la fila de encabezados (`nrows=0`); imprime un conteo, nunca el contenido del archivo. Se omite si no hay archivo.

```bash
.venv/bin/python - <<'EOF'
import sys; sys.path.insert(0, ".")
import pandas as pd
from src.core.texto import norm_txt
from src.cuidadores import catalog as cat, pipeline
ruta = pipeline.localizar_formulario()
if ruta is None:
    print("sin archivo real: se omite")
else:
    cols = list(pd.read_excel(ruta, nrows=0).columns)
    malos = [p for p, f in cat.VERIFICAR.items() if f not in norm_txt(cols[p])]
    print("columnas:", len(cols), "· fragmentos que no coinciden:", len(malos))
EOF
```
Expected: `columnas: 209 · fragmentos que no coinciden: 0`.

- [ ] **Step 5: Commit**

```bash
git add src/cuidadores/pipeline.py tests/test_cuidadores_pipeline.py
git commit -m "feat(cuidadores): AnalisisCuidadores con marcos cuidador y niño, base y supresión" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Vista de investigadores

**Files:**
- Create: `src/ui/views/cuidadores_investigador.py`
- Create: `tests/test_cuidadores_vista.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_vista.py`:

```python
"""Cuidadores 360 · vista de investigadores: tablas, paquete y anonimato (fase 4a)."""
import io
import re
import zipfile

import pytest

from src.cuidadores import ingest, pipeline
from src.ui.views import cuidadores_investigador as vi
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()
SEUDONIMO = re.compile(r"\b[CN][0-9a-f]{8}\b")


@pytest.fixture(scope="module")
def ac():
    return pipeline.analizar(ingest.cargar(cs.formulario(), k=K), n_boot=10)


def test_pestanas():
    assert vi.PESTANAS == ["Muestra y exclusiones", "Tabla 1 · descriptivos", "Cortes y bandas",
                           "Correlaciones", "Por grupo", "Señales del adulto",
                           "Ítems sin puntaje", "Calidad de datos", "Exportar"]


def test_tablas_sin_casos_ni_identificadores(ac):
    for t in (vi.tabla1(ac), vi.cortes_y_bandas(ac), vi.cortes_por_grupo(ac),
              vi.correlaciones(ac), vi.comparaciones_grupo(ac), vi.senales_adulto(ac)):
        assert not t.empty
        assert not set(vi.COLUMNAS_PROHIBIDAS) & set(t.columns)


def test_cortes_por_grupo_solo_grupos_publicables(ac):
    t = vi.cortes_por_grupo(ac)
    assert set(t["grupo"]) <= {"LauV", "JJC", "SJMEB", "LaBalsa", "Quinto", "Sexto", "Octavo",
                               "Décimo", "Cuarto", "LauV|Quinto", "LauV|Sexto", "LauV|Octavo",
                               "JJC|Décimo", "JJC|Cuarto"}


def test_senales_adulto_solo_epds(ac):
    t = vi.senales_adulto(ac)
    assert set(t["clave"]) == {"EPDS_Total", "EPDS_Autolesion"}
    assert "Total" in set(t["agrupacion"])


def test_conteos_pequenos_se_enmascaran():
    t = vi.tabla_conteos({"LauV": 35, "CdP": 4}, "Colegio")
    assert t.set_index("Colegio")["Cuidadores"].to_dict() == {"LauV": "35", "CdP": "<10"}


def test_el_zip_es_agregado_y_anonimo(ac):
    z = zipfile.ZipFile(io.BytesIO(vi.paquete_zip(ac)))
    assert set(z.namelist()) == set(vi.ARCHIVOS_PAQUETE)
    for nombre in z.namelist():
        texto = z.read(nombre).decode("utf-8")
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in texto, nombre
        assert not SEUDONIMO.search(texto), nombre
        if nombre.endswith(".csv"):
            assert not set(vi.COLUMNAS_PROHIBIDAS) & set(texto.splitlines()[0].split(","))


def test_metodologia_declara_lo_pendiente(ac):
    md = vi.metodologia_md(ac)
    for fragmento in ("Columna 6", "libro de códigos", "5 / 4 / 3", "OBS360_CLAVE_HMAC",
                      "periodo perinatal", "501", "fuera del rango"):
        assert fragmento in md, fragmento
```

Run: `.venv/bin/python -m pytest tests/test_cuidadores_vista.py -q`
Expected: FAIL con `ImportError: cannot import name 'cuidadores_investigador' from 'src.ui.views'`.

- [ ] **Step 2: Implementar**

`src/ui/views/cuidadores_investigador.py`:

```python
"""
Vista investigador de Cuidadores 360 — Observatorio 360 (fase 4a).

Misma estructura que la de estudiantes: un selector de marco (cuidadores o
niños, como el de nivel) y las pestañas de muestra, Tabla 1, cortes y bandas,
correlaciones, por grupo, señales del adulto, ítems, calidad y exportación.

No calcula estadística: consume el `AnalisisCuidadores` de
`src.cuidadores.pipeline`. Todo lo que muestra o exporta es agregado, ya pasó
por la base publicable (cuidadores distintos) y por la supresión de cifras
pequeñas. Ninguna tabla lleva `casos`, identificadores ni filas.

Solo existe en los modos completo e investigador: `main.py` no la importa en el
despliegue público.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import zipfile

import pandas as pd
import streamlit as st

from src.cuidadores import catalog as cat

PESTANAS = ["Muestra y exclusiones", "Tabla 1 · descriptivos", "Cortes y bandas",
            "Correlaciones", "Por grupo", "Señales del adulto", "Ítems sin puntaje",
            "Calidad de datos", "Exportar"]

ARCHIVOS_PAQUETE = ["tabla1_descriptivos.csv", "cortes_y_bandas.csv", "cortes_por_grupo.csv",
                    "correlaciones_bh.csv", "comparaciones_grupo.csv",
                    "flujo_exclusiones.md", "metodologia.md", "version_analisis.txt"]

# Columnas que nunca salen de esta vista, aunque una tabla las traiga.
COLUMNAS_PROHIBIDAS = ("casos", "ID_cuidador", "ID_nino", "n_b0", "n_b1", "n_b2", "n_b3",
                       "k_bajo", "k_alto")

PASOS_EXCLUSION = [
    ("filas_archivo", "Respuestas en el archivo"),
    ("sin_consentimiento", "Sin consentimiento"),
    ("respuestas_repetidas_cuidador", "El mismo cuidador más de una vez (se queda la más reciente)"),
]

_SIN_DATO = "—"


# ══════════════════════════════════════════════════════════════════════════
# Funciones puras
# ══════════════════════════════════════════════════════════════════════════
def _limpia(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    out = df.drop(columns=[c for c in COLUMNAS_PROHIBIDAS if c in df.columns]).copy()
    for c in out.columns:
        if out[c].map(lambda v: isinstance(v, (list, tuple, set))).any():
            out[c] = out[c].map(lambda v: " · ".join(map(str, v))
                                if isinstance(v, (list, tuple, set)) else v)
    return out


def _con_marco(df: pd.DataFrame, marco: str) -> pd.DataFrame:
    df = _limpia(df)
    if df.empty:
        return df
    df.insert(0, "marco", marco)
    return df


def _csv(df: pd.DataFrame) -> str:
    df = _limpia(df)
    return "" if df.empty else df.to_csv(index=False)


def conteo_legible(valor) -> str:
    """Conteos de grupo: por debajo del mínimo, «<10»."""
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return _SIN_DATO
    return str(v) if v >= cat.MIN_GROUP_N else f"<{cat.MIN_GROUP_N}"


def tabla_conteos(conteos: dict, etiqueta: str, orden: list | None = None) -> pd.DataFrame:
    claves = [k for k in (orden or []) if k in conteos] + \
        sorted((k for k in conteos if k not in (orden or [])),
               key=lambda k: -int(conteos[k]) if str(conteos[k]).isdigit() else 0)
    return pd.DataFrame([(k, conteo_legible(conteos[k])) for k in claves],
                        columns=[etiqueta, "Cuidadores"])


def tabla1(ac) -> pd.DataFrame:
    filas = []
    for marco, a in ac.marcos.items():
        desc = getattr(a, "descriptivos", pd.DataFrame())
        if desc is None or desc.empty:
            continue
        fia = getattr(a, "fiabilidad", pd.DataFrame())
        fia = fia.set_index("clave") if fia is not None and not fia.empty else pd.DataFrame()
        for _, f in desc.iterrows():
            alpha = fia.loc[f["clave"]] if f["clave"] in fia.index else None
            filas.append(dict(
                marco=marco, clave=f["clave"], escala=f["escala"], n=f["n"], M=f["M"],
                DE=f["DE"], Mdn=f["Mdn"], min=f["min"], max=f["max"], rango=f["rango"],
                alpha=None if alpha is None else alpha["alpha"],
                alpha_ic=(_SIN_DATO if alpha is None or alpha["ic_inf"] is None
                          or pd.isna(alpha["ic_inf"])
                          else f"[{alpha['ic_inf']:.2f}–{alpha['ic_sup']:.2f}]"),
                pct_faltante=f["pct_faltante"], fuente=f["fuente"]))
    return pd.DataFrame(filas)


def cortes_y_bandas(ac) -> pd.DataFrame:
    partes = []
    for marco, a in ac.marcos.items():
        partes.append(_con_marco(getattr(a, "cortes", None), marco).assign(tabla="corte"))
        b = _limpia(getattr(a, "bandas", None))
        if not b.empty:
            b = b.drop(columns=[c for c in ("etiquetas",) if c in b.columns])
            partes.append(_con_marco(b, marco).assign(tabla="bandas_padres"))
        partes.append(_con_marco(getattr(a, "terciles", None), marco).assign(tabla="terciles"))
    partes = [p for p in partes if not p.empty]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def cortes_por_grupo(ac) -> pd.DataFrame:
    """Cortes de cada colegio, grado y celda que quedaron publicables (sin casos)."""
    filas = []
    for marco, a in ac.marcos.items():
        for agrupacion, grupos in (getattr(a, "subgrupos", None) or {}).items():
            for grupo, s in grupos.items():
                t = _limpia(getattr(s, "cortes", None))
                if t.empty:
                    continue
                t.insert(0, "grupo", grupo)
                t.insert(0, "agrupacion", agrupacion)
                t.insert(0, "marco", marco)
                filas.append(t)
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


def correlaciones(ac) -> pd.DataFrame:
    partes = [_con_marco(getattr(a, "correlaciones", None), m) for m, a in ac.marcos.items()]
    partes = [p for p in partes if not p.empty]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def comparaciones_grupo(ac) -> pd.DataFrame:
    partes = []
    for marco, a in ac.marcos.items():
        for nombre, campo in (("Colegio", "por_colegio"), ("Grado", "por_grado"),
                              ("Sexo del niño", "por_sexo")):
            t = _con_marco(getattr(a, campo, None), marco)
            if not t.empty:
                t.insert(1, "comparacion", nombre)
                partes.append(t)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def senales_adulto(ac) -> pd.DataFrame:
    """Ánimo (EPDS) y autolesión (ítem 10) en el total y en cada grupo con cifra."""
    t = cortes_por_grupo(ac)
    nivel = _con_marco(getattr(ac.cuidador, "cortes", None), cat.MARCO_CUIDADOR)
    if not nivel.empty:
        nivel.insert(1, "agrupacion", "Total")
        nivel.insert(2, "grupo", "Todos")
        t = pd.concat([nivel, t], ignore_index=True)
    if t.empty:
        return t
    return t[t["clave"].isin(["EPDS_Total", "EPDS_Autolesion"])].reset_index(drop=True)


def flujo_exclusiones_md(informe) -> str:
    if informe is None:
        return ""
    lineas = ["# Flujo de la muestra · Cuidadores 360", ""]
    restantes = int(informe.filas_archivo)
    lineas.append(f"- {PASOS_EXCLUSION[0][1]}: {restantes}")
    for campo, etiqueta in PASOS_EXCLUSION[1:]:
        quitadas = int(getattr(informe, campo, 0) or 0)
        restantes -= quitadas
        lineas.append(f"- − {etiqueta}: {quitadas} → quedan {restantes}")
    lineas += [f"- Cuidadores distintos analizados: {informe.cuidadores_distintos}", "",
               "## Niños", "",
               f"- Filas de niño (hijo 1 y hijo 2): {informe.filas_nino}",
               f"- − El mismo niño como hijo 1 y hijo 2 en un envío: "
               f"{informe.mismo_nino_misma_respuesta}",
               f"- Niños reportados por más de un cuidador: {informe.mismo_nino_otro_cuidador}",
               f"- Niños repetidos entre olas: {informe.mismo_nino_entre_olas}",
               f"- Niños únicos analizados: {informe.ninos_unicos}", "",
               "Prioridad al deduplicar niños: la ola más reciente; luego mamá, papá, otro "
               "cuidador; luego el primer envío. Cuidadores: la respuesta más reciente."]
    return "\n".join(lineas) + "\n"


def metodologia_md(ac) -> str:
    inf = ac.informe
    olas = ", ".join(f"{o}: {n}" for o, n in (inf.por_ola or {}).items())
    lineas = [
        "# Metodología · Cuidadores 360 (fase 4a, solo local)", "",
        "## Instrumento", "",
        "Formulario «Cuidando al Cuidador», leído por posición y verificado con el texto de "
        "cada encabezado. Cada respuesta se convierte en número por su texto, con un mapa "
        "explícito por ítem (src/cuidadores/catalog.py).", "",
        f"Olas: {olas or _SIN_DATO}. El filtro de ola existe solo en la vista local.", "",
        "## Identificadores", "",
        "Los nombres se convierten en seudónimos HMAC-SHA256 con una clave local "
        "(OBS360_CLAVE_HMAC) y no se guardan. El teléfono no se lee. Ninguna tabla de este "
        "paquete lleva identificadores ni filas.", "",
        "## Puntuación", "",
        "- PSS-10: 0–40, ítems 3, 4, 5, 7 y 9 invertidos (igual que docentes); se prorratea "
        "con 9 de 10 ítems. «Columna 6» cuenta como faltante. Sin corte: terciles.",
        f"- EPDS-10: 0–30 con los 10 ítems. Ánimo posible ≥ {cat.EPDS_POSIBLE}, probable "
        f"≥ {cat.EPDS_PROBABLE}. Autolesión: ítem 10 distinto de «No, nunca». "
        + cat.AVISO_EPDS,
        "- MSPSS del cuidador: media 1–5 por fuente (5 / 4 / 3 ítems) y total. "
        + cat.AVISO_MSPSS,
        "- Riesgo del barrio: suma de 5 ítems (0–10).",
        "- " + cat.AVISO_APQ,
        "- " + cat.AVISO_ESTRES_PARENTAL,
        "- SDQ de padres: subescalas estándar y bandas de la versión para padres 4-17. "
        + cat.AVISO_SDQ_EDAD,
        "- ARI de padres: ítems 1–6 (0–12) y deterioro (ítem 7). " + cat.AVISO_ARI, "",
        "## Privacidad", "",
        "- " + cat.AVISO_MINIMO,
        "- Base publicable: celdas colegio × grado con 10 o más cuidadores distintos; colegio, "
        "grado y total se calculan sobre la unión de esas celdas (spec §5.1).",
        "- Todo o nada por indicador y supresión de proporciones con menos de 3 casos o no "
        "casos, también por resta (estudiantes/supresion.py).",
        "- «OTRO» (colegio no reconocido) y «SIN_DATO» nunca forman grupo.", "",
        "## Grado", "",
        "El curso se escribe a mano. Reglas: palabra de grado («Sexto 602» → Sexto), número "
        "de una o dos cifras («5A» → Quinto) y código de curso («501» → Quinto, «1002» → "
        "Décimo). Grados del estudio: cuarto a décimo; los demás quedan «fuera del rango "
        "del estudio» y solo cuentan en el total.",
    ]
    return "\n".join(lineas) + "\n"


def _hash_estructura(ac) -> str:
    firma = "|".join(f"{m}:{','.join(map(str, a.datos.columns))}:{a.datos.shape}"
                     for m, a in ac.marcos.items() if getattr(a, "datos", None) is not None)
    return hashlib.sha1(firma.encode("utf-8")).hexdigest()


def version_analisis_txt(ac) -> str:
    return "\n".join([
        "Cuidadores 360 · versión del análisis",
        f"Fecha: {_dt.date.today().isoformat()}",
        f"Ola: {ac.ola or 'todas'}",
        f"Cuidadores analizados: {ac.cuidador.n}",
        f"Niños analizados: {ac.nino.n}",
        f"Hash de estructura: {_hash_estructura(ac)}",
    ]) + "\n"


def archivos_paquete(ac) -> dict[str, str]:
    return {
        "tabla1_descriptivos.csv": _csv(tabla1(ac)),
        "cortes_y_bandas.csv": _csv(cortes_y_bandas(ac)),
        "cortes_por_grupo.csv": _csv(cortes_por_grupo(ac)),
        "correlaciones_bh.csv": _csv(correlaciones(ac)),
        "comparaciones_grupo.csv": _csv(comparaciones_grupo(ac)),
        "flujo_exclusiones.md": flujo_exclusiones_md(ac.informe),
        "metodologia.md": metodologia_md(ac),
        "version_analisis.txt": version_analisis_txt(ac),
    }


def paquete_zip(ac) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in archivos_paquete(ac).items():
            if contenido:
                z.writestr(nombre, contenido)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════
# Pestañas
# ══════════════════════════════════════════════════════════════════════════
def _df(t: pd.DataFrame) -> None:
    t = _limpia(t)
    if t.empty:
        st.caption("Sin datos para mostrar.")
    else:
        st.dataframe(t, hide_index=True, width="stretch")


def _tab_muestra(a, informe, marco: str) -> None:
    m = getattr(a, "muestra", {}) or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas analizadas", m.get("n", a.n))
    c2.metric("Cuidadores distintos", m.get("n_cuidadores", _SIN_DATO))
    c3.metric("Colegios con 10 o más", len(getattr(a, "subgrupos", {}).get("Colegio", {})))
    fechas = m.get("fechas") or []
    c4.metric("Recogida", f"{fechas[0]} → {fechas[1]}" if len(fechas) == 2 else _SIN_DATO)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Ola**")
        st.dataframe(tabla_conteos(m.get("ola") or {}, "Ola"), hide_index=True,
                     width="stretch")
        st.markdown("**Quién responde**")
        st.dataframe(tabla_conteos(m.get("quien") or {}, "Quién"), hide_index=True,
                     width="stretch")
    with c2:
        st.markdown("**Colegio**")
        st.dataframe(tabla_conteos(m.get("colegio") or {}, "Colegio"), hide_index=True,
                     width="stretch")
        st.markdown("**Grado del estudio**")
        st.dataframe(tabla_conteos(m.get("grado") or {}, "Grado", list(cat.GRADOS_ESTUDIO)),
                     hide_index=True, width="stretch")
    st.caption(cat.AVISO_MINIMO)
    st.divider()
    st.subheader("Flujo de la muestra")
    st.markdown(flujo_exclusiones_md(informe))


def _tab_tabla1(ac, marco: str) -> None:
    t = tabla1(ac)
    _df(t[t["marco"] == marco].drop(columns=["marco"]) if not t.empty else t)
    st.caption("α con IC por bootstrap sobre casos completos. Las cifras salen de la base "
               "publicable (cuidadores distintos).")


def _tab_cortes(a, marco: str) -> None:
    st.markdown("**Prevalencias sobre corte**")
    _df(getattr(a, "cortes", None))
    if marco == cat.MARCO_NINO:
        st.markdown("**Bandas del SDQ de padres**")
        b = _limpia(getattr(a, "bandas", None))
        _df(b.drop(columns=[c for c in ("etiquetas",) if c in b.columns]) if not b.empty else b)
    st.markdown("**Terciles (escalas sin corte clínico)**")
    _df(getattr(a, "terciles", None))
    st.caption("Un «—» o una celda vacía es una cifra suprimida: menos de 3 casos o no casos, "
               "directamente o por resta.")


def _tab_correlaciones(a) -> None:
    _df(getattr(a, "correlaciones", None))
    st.caption("Spearman con IC de Fisher; q de Benjamini-Hochberg.")


def _tab_por_grupo(ac, a, marco: str) -> None:
    t = comparaciones_grupo(ac)
    _df(t[t["marco"] == marco].drop(columns=["marco"]) if not t.empty else t)
    st.markdown("**Cortes por colegio, grado y celda**")
    g = cortes_por_grupo(ac)
    _df(g[g["marco"] == marco].drop(columns=["marco"]) if not g.empty else g)
    enm = getattr(a, "enmascarados", {}) or {}
    if enm.get("Colegio") or enm.get("Grado"):
        st.caption("No se desagregan (menos de 10 cuidadores distintos o sin celda "
                   f"publicable): {len(enm.get('Colegio', []))} colegios y "
                   f"{len(enm.get('Grado', []))} grados.")


def _tab_senales(ac) -> None:
    st.info(cat.AVISO_EPDS)
    _df(senales_adulto(ac))
    st.caption("Definiciones provisionales (spec §5.5): ánimo = EPDS ≥ 13; autolesión = "
               "ítem 10 distinto de «No, nunca». En la vista de comunidad (4b) la autolesión "
               "solo se mostrará a nivel municipio.")


def _tab_items(ac) -> None:
    st.markdown("**APQ · prácticas de crianza (% «a veces» o más)**")
    st.caption(cat.AVISO_APQ)
    _df(getattr(ac, "items_apq", None))
    st.markdown("**Estrés parental · ítems (% «de acuerdo» o «muy de acuerdo»)**")
    st.caption(cat.AVISO_ESTRES_PARENTAL)
    _df(getattr(ac, "items_estres", None))


def _tab_calidad(ac, a) -> None:
    inf = ac.informe
    c1, c2, c3 = st.columns(3)
    c1.metric("Edades no numéricas", inf.edad_no_numerica)
    c2.metric("Edades fuera de 4–17", inf.edad_fuera_de_rango)
    c3.metric("Cursos sin resolver", inf.curso_sin_resolver)
    c1, c2, c3 = st.columns(3)
    c1.metric("«Columna 6» en la PSS", inf.respuestas_columna6_pss)
    c2.metric("Colegio no reconocido (filas de niño)", inf.colegio_no_reconocido)
    c3.metric("ARI de padres (hijo 1 / hijo 2)",
              f"{inf.cobertura_ari.get('hijo 1', 0)} / {inf.cobertura_ari.get('hijo 2', 0)}")
    st.markdown("**% de ítems faltantes por bloque**")
    st.dataframe(pd.DataFrame(sorted(inf.faltantes_por_bloque.items()),
                              columns=["Bloque", "% faltante"]),
                 hide_index=True, width="stretch")
    if inf.etiquetas_no_mapeadas:
        st.warning("Respuestas con etiquetas que el catálogo no reconoce (quedan como "
                   "faltantes): " + ", ".join(f"{k} ({n})" for k, n in
                                             sorted(inf.etiquetas_no_mapeadas.items())))
    else:
        st.success("Todas las etiquetas del formulario se mapearon a número.")
    for aviso in list(getattr(a, "avisos", []) or []) + list(inf.avisos or []):
        st.warning(aviso)


def _tab_exportar(ac) -> None:
    st.caption("Todo es agregado: ni filas, ni identificadores, ni conteos de casos.")
    contenidos = archivos_paquete(ac)
    columnas = st.columns(2)
    for i, nombre in enumerate(ARCHIVOS_PAQUETE):
        with columnas[i % 2]:
            contenido = contenidos.get(nombre, "")
            st.download_button(f"⬇️ {nombre}", data=contenido.encode("utf-8-sig"),
                               file_name=nombre,
                               mime="text/csv" if nombre.endswith(".csv") else "text/markdown",
                               disabled=not contenido, width="stretch",
                               key=f"cuid_dl_{nombre}")
    st.download_button("📦 Descargar el paquete completo (ZIP)", data=paquete_zip(ac),
                       file_name=f"cuidadores360_{ac.ola or 'todas'}_"
                                 f"{_dt.date.today().isoformat()}.zip",
                       mime="application/zip", type="primary", width="stretch",
                       key="cuid_dl_zip")


def render_investigador(ac) -> None:
    st.title("Cuidadores 360 · vista investigador")
    marco = st.radio("Marco", list(cat.NOMBRES_MARCO), horizontal=True,
                     format_func=lambda m: cat.NOMBRES_MARCO[m], key="cuid_marco")
    a = ac.marcos[marco]
    if ac.ola:
        st.caption(f"Ola {ac.ola}. {cat.AVISO_OLA}")
    tabs = st.tabs(PESTANAS)
    with tabs[0]:
        _tab_muestra(a, ac.informe, marco)
    with tabs[1]:
        _tab_tabla1(ac, marco)
    with tabs[2]:
        _tab_cortes(a, marco)
    with tabs[3]:
        _tab_correlaciones(a)
    with tabs[4]:
        _tab_por_grupo(ac, a, marco)
    with tabs[5]:
        _tab_senales(ac)
    with tabs[6]:
        _tab_items(ac)
    with tabs[7]:
        _tab_calidad(ac, a)
    with tabs[8]:
        _tab_exportar(ac)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_vista.py tests/test_modo_despliegue.py -q`
Expected: todo pasa (`7 passed` de las nuevas). `test_no_queda_el_parametro_de_ancho_obsoleto` y `test_no_queda_dashboard_visible_en_la_interfaz` revisan también el archivo nuevo.

- [ ] **Step 4: Commit**

```bash
git add src/ui/views/cuidadores_investigador.py tests/test_cuidadores_vista.py
git commit -m "feat(cuidadores): vista de investigadores y paquete agregado" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Página, navegación y corte público

**Files:**
- Create: `src/ui/cuidadores.py`
- Create: `tests/test_cuidadores_pagina.py`
- Modify: `src/core/navegacion.py:33-52`
- Modify: `main.py:116-121`
- Modify: `tests/test_navegacion.py`, `tests/test_modo_despliegue.py:104-106`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_cuidadores_pagina.py`:

```python
"""Cuidadores 360 · página (fase 4a): sin archivo, sin clave y con datos sintéticos."""

from src.cuidadores import catalog as cat
from src.ui.views import cuidadores_investigador as vi
from tests import cuidadores_sinteticos as cs


def _pagina(monkeypatch, datos: str, clave: str | None):
    from streamlit.testing.v1 import AppTest
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
    at.radio(key="cuid_marco").set_value(cat.MARCO_NINO).run()
    assert not at.exception
    pantalla = " ".join(str(e.value) for e in at.markdown) + \
        " ".join(str(getattr(d, "value", "")) for d in at.dataframe)
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in pantalla
```

En `tests/test_navegacion.py`, sustituir las dos pruebas del principio:

```python
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
```

por:

```python
def test_triangulacion_aun_no_sale_en_el_menu():
    """Triangulación llega en la fase 5."""
    for m in (COMPLETO, INVESTIGADOR, COMUNIDAD):
        assert nav.PAGINA_TRIANGULACION not in nav.menu(m)


def test_completo_e_investigador_ven_todas_las_disponibles_en_orden():
    esperado = ["Docentes", "Estudiantes 360", "Cuidadores 360", "Chat con IA",
                "Cargar Datos", "Análisis de tendencias", "Reportes"]
    assert nav.menu(COMPLETO) == esperado
    assert nav.menu(INVESTIGADOR) == esperado
```

Después de `test_comunidad_solo_ve_paginas_publicas` (que **no cambia**: comunidad sigue viendo solo `["Estudiantes 360"]`), añadir:

```python
def test_cuidadores_no_es_publica_hasta_la_aprobacion():
    """Fase 4a: existe para investigadores; el público no la ve hasta la 4b (spec §5.5)."""
    assert nav.CUIDADORES_PUBLICO is False
    assert nav.PAGINA_CUIDADORES in nav.DISPONIBLES
    assert nav.PAGINA_CUIDADORES not in nav.menu(COMUNIDAD)
    assert nav.PAGINA_CUIDADORES not in nav.menu("cualquier-cosa")
```

Sustituir `test_cuando_cuidadores_este_disponible_comunidad_lo_ve` por:

```python
def test_cuando_cuidadores_se_apruebe_comunidad_lo_ve(monkeypatch):
    monkeypatch.setattr(nav, "DISPONIBLES",
                        nav.DISPONIBLES | {nav.PAGINA_CUIDADORES, nav.PAGINA_TRIANGULACION})
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    monkeypatch.setattr(nav, "CUIDADORES_PUBLICO", True)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360", "Cuidadores 360"]
    assert nav.menu(INVESTIGADOR)[:4] == [
        "Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360"]
```

Ampliar `PROHIBIDOS_EN_COMUNIDAD`:

```python
PROHIBIDOS_EN_COMUNIDAD = (
    "src.ui.dashboard", "src.ui.chat", "src.ui.upload", "src.ui.reports",
    "src.ui.trends", "src.ai.gemini_client",
    "src.ui.views.estudiantes_investigador",
    "src.ui.cuidadores", "src.ui.views.cuidadores_investigador",
    "src.cuidadores.ingest", "src.cuidadores.pipeline")
```

En `test_comunidad_con_dos_paginas_publicas_muestra_el_selector`, cambiar

```python
    monkeypatch.setattr(nav, "DISPONIBLES",
                        nav.DISPONIBLES | {nav.PAGINA_CUIDADORES})
```

por

```python
    monkeypatch.setattr(nav, "CUIDADORES_PUBLICO", True)
```

(el resto de la prueba no cambia: con la bandera forzada, el selector ofrece las dos páginas, elegir Cuidadores no lanza nada y ningún módulo prohibido se importa, porque la rama pública de `main.py` todavía no enruta Cuidadores).

Y añadir al final:

```python
def test_main_en_investigador_ofrece_cuidadores(monkeypatch, tmp_path):
    """Sin archivos (como en el despliegue del equipo), la página dice que no está publicada."""
    from streamlit.testing.v1 import AppTest
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
```

En `tests/test_modo_despliegue.py`, dentro de `test_el_punto_de_entrada_corta_antes_de_importar_lo_demas`, después del bucle `for modulo in ("triangulacion", "cuidadores_investigador"):`, añadir:

```python

    # Cuidadores 360 (fase 4a) solo se enruta después del corte, para investigadores
    assert "src.ui.cuidadores" not in antes and "src.cuidadores" not in antes
    assert "from src.ui.cuidadores import render_cuidadores" in despues
```

Run: `.venv/bin/python -m pytest tests/test_navegacion.py tests/test_modo_despliegue.py tests/test_cuidadores_pagina.py -q`
Expected: FAIL. Entre otras, `test_completo_e_investigador_ven_todas_las_disponibles_en_orden` (falta Cuidadores), `test_cuidadores_no_es_publica_hasta_la_aprobacion` (`AttributeError: … CUIDADORES_PUBLICO`) y las de la página (`ModuleNotFoundError: No module named 'src.ui.cuidadores'`).

- [ ] **Step 2: Implementar la página**

`src/ui/cuidadores.py`:

```python
"""
Página «Cuidadores 360» — fase 4a: solo la vista de investigadores, en local.

  · Busca la exportación de «Cuidando al Cuidador» en la carpeta de datos
    fuente (`core.rutas`). Si no está (por ejemplo, en el despliegue), dice
    que Cuidadores aún no está publicado y no falla.
  · Sin la clave local `OBS360_CLAVE_HMAC` no carga y explica qué hacer.
  · El filtro de ola vive en la barra lateral y solo existe aquí.

La vista de comunidad, los informes y la corrida publicada llegan en la 4b.
La página solo se enruta en los modos completo e investigador (`main.py`).
"""
from __future__ import annotations

import os

import streamlit as st

from src.cuidadores import catalog as cat

TODAS = "Todas"
NO_PUBLICADO = ("Cuidadores aún no está publicado. Esta página muestra los resultados "
                "solo en la máquina que procesa el formulario; la vista para colegios, "
                "familias y municipio llegará cuando el equipo apruebe sus textos.")


@st.cache_resource(show_spinner="Leyendo el formulario de cuidadores…")
def _carga(firma: tuple):
    from src.cuidadores import ingest
    return ingest.cargar(firma[0])


@st.cache_resource(show_spinner="Puntuando y analizando…")
def _analisis(firma: tuple, ola: str | None):
    from src.cuidadores import pipeline
    return pipeline.analizar(_carga(firma), ola=ola)


def render_cuidadores() -> None:
    from src.cuidadores import pipeline
    from src.core.seudonimo import ClaveAusente

    ruta = pipeline.localizar_formulario()
    if not ruta:
        st.title("👪 Cuidadores 360")
        st.info(NO_PUBLICADO, icon="⏳")
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

    olas = sorted(o for o in carga.respuestas["Ola"].dropna().unique() if o != cat.SIN_DATO)
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Cuidadores 360**")
        eleccion = st.selectbox("Ola (solo local)", [TODAS, *olas], key="cuid_ola")
        st.caption(cat.AVISO_OLA)
    ola = None if eleccion == TODAS else eleccion
    ac = _analisis(firma, ola)
    st.sidebar.caption(f"{ac.cuidador.n} cuidadores · {ac.nino.n} niños")

    from src.ui.views.cuidadores_investigador import render_investigador
    render_investigador(ac)
```

- [ ] **Step 3: Navegación**

En `src/core/navegacion.py`, sustituir:

```python
# Las que ya tienen vista. Cuidadores entra en la fase 4 y Triangulación en la 5.
DISPONIBLES = frozenset({PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CHAT,
                         PAGINA_CARGA, PAGINA_TENDENCIAS, PAGINA_REPORTES})

# Lo único que puede ver el público. Triangulación es solo para investigadores.
PUBLICAS = (PAGINA_ESTUDIANTES, PAGINA_CUIDADORES)
```

por:

```python
# Las que ya tienen vista. Cuidadores entra en la fase 4a (solo investigadores)
# y Triangulación en la 5.
DISPONIBLES = frozenset({PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CUIDADORES,
                         PAGINA_CHAT, PAGINA_CARGA, PAGINA_TENDENCIAS, PAGINA_REPORTES})

# Lo único que puede ver el público. Triangulación es solo para investigadores.
PUBLICAS = (PAGINA_ESTUDIANTES, PAGINA_CUIDADORES)

# Cuidadores es pública solo cuando el equipo aprueba sus textos y rutas y hay
# una corrida de cuidadores publicada (spec §5.5). Lo cambia la fase 4b.
CUIDADORES_PUBLICO = False
```

Y en `menu()`, sustituir:

```python
    visibles = PUBLICAS if _es_publico(modo) else MENU
    return [p for p in MENU if p in visibles and p in DISPONIBLES]
```

por:

```python
    if _es_publico(modo):
        visibles = [p for p in PUBLICAS
                    if p != PAGINA_CUIDADORES or CUIDADORES_PUBLICO]
    else:
        visibles = MENU
    return [p for p in MENU if p in visibles and p in DISPONIBLES]
```

- [ ] **Step 4: Enrutar en `main.py`, solo después del corte público**

Entre la rama de Estudiantes y la del chat:

```python
elif page == nav.PAGINA_ESTUDIANTES:
    from src.ui.estudiantes import render_estudiantes
    render_estudiantes()

elif page == nav.PAGINA_CUIDADORES:
    # Fase 4a: solo la vista de investigadores, con los archivos en local. Nunca
    # se importa en el despliegue público, que se corta arriba.
    from src.ui.cuidadores import render_cuidadores
    render_cuidadores()

elif page == nav.PAGINA_CHAT:
```

La rama pública de arriba (`if _PUBLICO: …`) **no se toca**: la 4b le añadirá Cuidadores cuando `CUIDADORES_PUBLICO` pase a `True`.

- [ ] **Step 5: Correr**

Run: `.venv/bin/python -m pytest tests/test_navegacion.py tests/test_modo_despliegue.py tests/test_cuidadores_pagina.py -q`
Expected: `40 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/ui/cuidadores.py src/core/navegacion.py main.py \
        tests/test_cuidadores_pagina.py tests/test_navegacion.py tests/test_modo_despliegue.py
git commit -m "feat(cuidadores): página para investigadores; nunca en el despliegue público" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Datos reales (se omite si falta el archivo)

**Files:**
- Create: `tests/test_cuidadores_reales.py`

Las cifras esperadas son **agregados** calculados el 8-oct-2026 sobre el xlsx real con este mismo código (ver «Observaciones de los datos»). Las comprobaciones de privacidad leen nombres y teléfonos del archivo **solo en memoria** y comparan un conteo (`assert hallados == 0`), así que un fallo nunca imprime un valor.

- [ ] **Step 1: Escribir las pruebas**

`tests/test_cuidadores_reales.py`:

```python
"""
Cuidadores 360 con el formulario real (se omite si falta el archivo).

Solo se comparan AGREGADOS con la spec (§3.2, §5.5) y con el recuento del
8-oct-2026. Ningún mensaje de fallo puede mostrar un valor individual: las
comprobaciones de privacidad comparan conteos (`assert n == 0`), nunca listas.
"""
import io
import zipfile

import pytest

from src.core.texto import norm_txt
from src.cuidadores import catalog as cat
from src.cuidadores import ingest, pipeline

CLAVE = b"clave-de-prueba-solo-para-tests-0001"
RUTA = pipeline.localizar_formulario()
pytestmark = pytest.mark.skipif(RUTA is None, reason="sin el formulario real de cuidadores")


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(RUTA, k=CLAVE)


@pytest.fixture(scope="module")
def ac(carga):
    return pipeline.analizar(carga, n_boot=50)


def test_formato_y_consentimiento(carga):
    inf = carga.informe
    assert inf.filas_archivo == 779 and inf.sin_consentimiento == 23
    assert inf.respuestas_validas == 756
    assert inf.por_ola == {"2025": 142, "2026": 614}
    assert inf.etiquetas_no_mapeadas == {}
    assert inf.respuestas_columna6_pss == 4


def test_ninos_y_repetidos(ac):
    inf = ac.informe
    assert inf.filas_nino == 973 and inf.hijo2 == 217
    assert inf.ninos_unicos == 886
    assert inf.mismo_nino_misma_respuesta == 72
    assert inf.mismo_nino_otro_cuidador == 6 and inf.mismo_nino_entre_olas == 5
    assert inf.cuidadores_distintos == 734 and inf.cuidadores_en_dos_olas == 6


def test_calibracion_de_la_epds(carga):
    """Spec §5.5: probable 23,3 % y autolesión 11,0 % sobre las 756 respuestas."""
    from src.cuidadores import scoring
    p = scoring.puntuar_cuidadores(carga.respuestas)
    assert round(100 * p["EPDS_Probable"].mean(), 1) == 23.3
    assert round(100 * p["EPDS_Autolesion"].mean(), 1) == 11.0


def test_colegios_con_el_normalizador_corregido(carga):
    c = carga.respuestas["Colegio"].value_counts().to_dict()
    assert c["LauV"] == 448 and c["SJMEB"] == 39 and c["LaBalsa"] == 24
    assert c["DiosCh"] == 13 and c["Bojacá"] == 12 and c["JJC"] == 121


def test_curso_casi_siempre_resuelto(ac):
    assert ac.informe.curso_sin_resolver <= 20
    assert ac.informe.grados.get(cat.SIN_DATO, 0) <= 20


def test_ari_solo_en_2026(carga):
    n = carga.ninos
    assert n.loc[n["Ola"] == "2025", [f"ARI{i}" for i in range(1, 8)]].isna().all().all()
    assert carga.informe.cobertura_ari == {"hijo 1": 382, "hijo 2": 93}


def test_ningun_grupo_publicado_con_menos_de_10_cuidadores(ac):
    for a in ac.marcos.values():
        for agrupacion, grupos in a.subgrupos.items():
            pequenos = sum(s.muestra["n_cuidadores"] < cat.MIN_GROUP_N for s in grupos.values())
            assert pequenos == 0, agrupacion
        assert "OTRO" not in a.subgrupos.get("Colegio", {})


def _prohibidos() -> set[str]:
    """Nombres completos y teléfonos del archivo real (solo en memoria, nunca se imprimen).

    Nombres: dos o más palabras (un «Ninguno» en la casilla del nombre no es un
    nombre y coincide con una opción de nivel educativo). Teléfonos: 7 o más
    dígitos.
    """
    raw = ingest.leer(RUTA)
    valores = set()
    for pos in cat.COLUMNAS_NOMBRE:
        valores |= {str(v).strip() for v in raw.iloc[:, pos].dropna()
                    if len(str(v).split()) >= 2}
    valores |= {d for d in (norm_txt(v).replace(" ", "") for v in raw.iloc[:, 179].dropna())
                if d.isdigit() and len(d) >= 7}
    return valores


def test_ningun_nombre_ni_telefono_en_marcos_ni_exportacion(ac):
    from src.ui.views import cuidadores_investigador as vi
    prohibidos = _prohibidos()
    textos = [a.datos.astype(str).to_csv() for a in ac.marcos.values()]
    z = zipfile.ZipFile(io.BytesIO(vi.paquete_zip(ac)))
    textos += [z.read(n).decode("utf-8") for n in z.namelist()]
    hallados = sum(1 for t in textos for v in prohibidos if v in t)
    assert hallados == 0
```

- [ ] **Step 2: Correr**

Run: `.venv/bin/python -m pytest tests/test_cuidadores_reales.py -q`
Expected: `8 passed` (o `8 skipped` en una máquina sin el archivo).

Si una cifra no coincide, **no** se imprime nada del archivo para investigarla. Se investiga con conteos agregados (por ejemplo, `value_counts` de códigos o de estados), y si el archivo cambió (una exportación nueva) se actualizan las cifras esperadas en el mismo commit, explicándolo en el mensaje.

- [ ] **Step 3: Commit**

```bash
git add tests/test_cuidadores_reales.py
git commit -m "test(cuidadores): agregados del formulario real y ausencia de nombres y teléfonos" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Documentación

**Files:**
- Modify: `DESPLIEGUE.md`, `ARCHITECTURE.md`, `secrets.toml.example`

- [ ] **Step 1: `DESPLIEGUE.md`**

En «Lo que nunca va en los secretos del despliegue», después del párrafo de `SUPABASE_SERVICE_KEY` y `SUPABASE_ACCESS_TOKEN`, añadir:

```markdown
`OBS360_CLAVE_HMAC` tampoco. Es la clave local con la que Cuidadores 360 (y la
triangulación de la fase 5) convierte nombres en seudónimos HMAC. Solo la
necesita la máquina que procesa los formularios; un despliegue nunca lee
archivos crudos. Si se pierde, basta con crear otra: los seudónimos no se
guardan ni se publican, se recalculan en cada carga.
```

En «Dónde viven los datos fuente», al final, añadir:

```markdown
**Cuidadores 360 (fase 4a)** solo funciona con el archivo en local
(`cuidadores/Cuidando al Cuidador … .xlsx`) y la clave `OBS360_CLAVE_HMAC`. En
los despliegues la página dice «Cuidadores aún no está publicado»; en el
público ni siquiera aparece en el menú hasta que la fase 4b ponga
`navegacion.CUIDADORES_PUBLICO = True`.
```

- [ ] **Step 2: `secrets.toml.example`** (al final)

```toml

# --- Solo en la máquina que procesa formularios (nunca en un despliegue) ---
# Clave para los seudónimos HMAC de Cuidadores 360. Generar una con:
#   python -c "import secrets; print(secrets.token_hex(32))"
# OBS360_CLAVE_HMAC = "…"
```

- [ ] **Step 3: `ARCHITECTURE.md`** (al final)

````markdown

---

## Módulo Cuidadores 360 (fase 4a)

Formulario «Cuidando al Cuidador» (209 columnas, dos olas). Solo local y solo
para investigadores; la vista de comunidad, los informes y la publicación son
de la fase 4b.

```
src/core/seudonimo.py      HMAC-SHA256 con clave local (OBS360_CLAVE_HMAC):
                           «C…» cuidador, «N…» niño, «E…» estudiante.
src/cuidadores/
├── catalog.py             Columnas por posición con verificación de encabezado,
│                          mapas texto → número por ítem (EPDS uno por ítem),
│                          puntuaciones, señales del adulto y avisos fijos.
├── ingest.py              Consentimiento, seudónimos, colegio (core/colegios),
│                          curso libre → grado, ola, hijo 2 y deduplicación.
├── scoring.py             PSS-10, EPDS-10, MSPSS 5/4/3, barrio, castigo físico,
│                          SDQ y ARI de padres. Tablas con la forma de estudiantes.
├── privacidad.py          Base publicable contando cuidadores distintos.
└── pipeline.py            AnalisisCuidadores: marcos «cuidador» y «nino», cada
                           uno un estudiantes.pipeline.Analisis con supresión.
src/ui/cuidadores.py                    Página: archivo local, clave y filtro de ola.
src/ui/views/cuidadores_investigador.py Pestañas y paquete exportable.
```

- **Nada individual.** Los nombres solo se leen para el seudónimo; el teléfono
  no se lee. El mínimo de 10 cuenta cuidadores distintos, también en el marco
  de niños. Toda proporción pasa por `estudiantes/supresion.py`.
- **Sin publicación todavía.** `navegacion.CUIDADORES_PUBLICO = False`: el
  despliegue público no muestra ni importa nada de cuidadores.
````

- [ ] **Step 4: Commit**

```bash
git add DESPLIEGUE.md ARCHITECTURE.md secrets.toml.example
git commit -m "docs(cuidadores): clave local, despliegue y arquitectura de la fase 4a" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Suite completa, producción y no regresión de estudiantes

**Files:** ninguno, salvo que aparezcan fallos.

- [ ] **Step 1: Entorno con Python 3.14 y WeasyPrint**

```bash
[ -x "$VENV314/bin/python" ] || /opt/homebrew/bin/python3.14 -m venv "$VENV314"
"$VENV314/bin/pip" install -q -r requirements.txt pytest pyarrow
"$VENV314/bin/python" -c "import streamlit, pandas, sys; print(sys.version, streamlit.__version__, pandas.__version__)"
```

- [ ] **Step 2: Correr las dos suites**

Run: `.venv/bin/python -m pytest -q`
Expected: `841 passed, 4 skipped` (674 de antes + 167 nuevas). En una máquina sin el archivo real de cuidadores: `833 passed, 12 skipped`.

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: `845 passed`. Ojo con pandas 3: `DataFrame.stack()` ya no quita los NaN; las pruebas usan `.stack().dropna()`.

- Si hay un error real: corregirlo con prueba y commit propio.
- Si es del entorno: anotarlo en el PR.

- [ ] **Step 3: Estudiantes no cambia**

```bash
git diff --stat main -- src/estudiantes src/ui/estudiantes.py src/ui/views/estudiantes_comunidad.py \
  src/ui/views/estudiantes_informe.py src/ui/views/estudiantes_investigador.py \
  src/ui/views/estudiantes_alertas.py src/core/colegios.py src/core/modo.py src/core/rutas.py \
  src/core/texto.py supabase
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_despues_4a.json" > /dev/null
cmp "$TMPDIR/obs360_lote_antes_4a.json" "$TMPDIR/obs360_lote_despues_4a.json" && echo "lote de estudiantes idéntico"
```
Expected: el `git diff --stat` no imprime nada y sale `lote de estudiantes idéntico`. Si el `cmp` difiere, parar: algo de esta fase tocó estudiantes.

- [ ] **Step 4: Commit (solo si hubo correcciones)**

---

### Task 13: Verificación con Playwright (local)

**Files:** ninguno.

- [ ] **Step 1: Levantar los modos**

```bash
OBS360_MODO=completo     .venv/bin/streamlit run main.py --server.port 8601 --server.headless true &
OBS360_MODO=investigador .venv/bin/streamlit run main.py --server.port 8602 --server.headless true &
OBS360_MODO=comunidad OBS360_FUENTE=supabase .venv/bin/streamlit run main.py --server.port 8603 --server.headless true &
mkdir -p "$TMPDIR/obs360_vacio"
OBS360_MODO=investigador OBS360_DATOS_DIR="$TMPDIR/obs360_vacio" .venv/bin/streamlit run main.py --server.port 8604 --server.headless true &
```

- [ ] **Step 2: Comprobar con Playwright MCP**

| Modo | Comprobación |
|---|---|
| completo (8601) | El menú lateral muestra «Cuidadores 360» entre «Estudiantes 360» y «Chat con IA». Al elegirlo: título «Cuidadores 360 · vista investigador», selector «Ola (solo local)» con Todas / 2025 / 2026, selector de marco y las 9 pestañas |
| completo, pestaña Muestra | Métricas de filas y cuidadores distintos; tablas de ola, quién responde, colegio y grado con «<10» donde corresponde; flujo de la muestra |
| completo, Cortes y bandas | EPDS posible y probable, autolesión, castigo físico, grito, MSPSS < 3; en el marco de niños, bandas del SDQ de padres sin columnas `n_b*` |
| completo, Por grupo | Solo colegios con 10 o más cuidadores (nunca «OTRO»); cortes por celda con «—» donde se suprimen |
| completo, Señales del adulto | Aviso de la EPDS perinatal; solo filas de EPDS |
| completo, Ítems sin puntaje | 25 ítems del APQ y 39 de estrés parental con las notas de 22–26 y 36; sin columna de casos |
| completo, Exportar | El ZIP descarga 8 archivos; abrirlos: sin seudónimos `C…`/`N…`, sin nombres, sin teléfonos, sin `casos` |
| completo, Ola 2025 | Se recalcula; el aviso «solo existe en esta vista local» aparece |
| investigador (8602) | «Cuidadores 360» en el menú y misma vista |
| investigador sin archivos (8604) | La página dice «Cuidadores aún no está publicado…»; sin errores |
| comunidad (8603) | **No hay selector de páginas** (solo Estudiantes 360); ninguna mención de Cuidadores; Estudiantes funciona como antes |
| todos | Sin excepciones en pantalla; Estudiantes 360 se ve igual que en `main` |

- [ ] **Step 3: Apagar los servidores y borrar `.playwright-mcp/` si se creó**

---

### Task 14: PR (sin fusionar)

- [ ] **Step 1:** `git push -u origin feature/fase4a-cuidadores`

- [ ] **Step 2:** `gh pr create --base main --title "Fase 4a · Cuidadores 360: carga, puntuación y vista de investigadores"`. El cuerpo lleva:

  1. **Resumen.**
     - Qué ve el equipo investigador (marcos, pestañas, filtro de ola, ZIP).
     - Privacidad: seudónimos HMAC con clave local, nombres y teléfono nunca copiados, mínimo de 10 cuidadores distintos, supresión general de estudiantes.
     - Lo que no hace: ni comunidad, ni informes, ni Supabase (4b); Cuidadores no aparece en el despliegue público.
  2. **Pruebas.**
     - Totales antes (674 passed, 4 skipped en 3.13; 678 en 3.14) y después (841 / 845).
     - Lote de estudiantes idéntico (`cmp`) y `git diff` vacío en `src/estudiantes`.
     - Verificación con Playwright (Task 13).
  3. **Pasos del usuario.**
     - Definir `OBS360_CLAVE_HMAC` en cada máquina que procese (la Task 0 ya la creó en esta). Nunca en los secretos de un despliegue.
     - **«Reboot app» después de fusionar** (los despliegues mostrarán «Cuidadores aún no está publicado» en investigador y nada en comunidad).
  4. **Preguntas abiertas y observaciones de los datos** (las listas de abajo).
  5. Cerrar con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 3:** No fusionar. Lo decide el usuario.

---

## Preguntas abiertas para el equipo (todas tienen un valor provisional en el código)

1. **Libro de códigos (`Códigos.xlsx`, spec §5.0 y §9).** Sin él no hay subescalas del APQ ni total del estrés parental. En particular: ¿cómo se puntúan las columnas 103–107 (una pregunta de elección forzada partida en cinco Likert) y la 117 (en positivo)? ¿Qué ítems del APQ forman cada subescala (implicación, crianza positiva, supervisión, disciplina inconsistente, castigo corporal)?
2. **Hijo 2 igual al hijo 1.** En 72 envíos el hijo 2 tiene el mismo nombre que el hijo 1 (ver observaciones). Hoy se queda el hijo 1 y el 2 se descarta. ¿Es un error de diligenciamiento, o son hermanos con el mismo nombre (improbable)? ¿Conviene conservar el SDQ del hijo 2 como segunda medición?
3. **Corte del ARI de padres.** No se aplica el > 2 del autoinforme; solo media y distribución. ¿Hay un corte de la versión para padres que quieran usar?
4. **Edad y SDQ.** Con una edad numérica fuera de 4–17 (15 filas de niño) el SDQ queda faltante; con edad no numérica (9 filas) se puntúa. ¿De acuerdo?
5. **Colegio y grado del cuidador = los de su hijo 1.** Afecta a 217 cuidadores con dos hijos. ¿Prefieren el hijo de menor grado, o contar al cuidador en los dos grupos (esto último complica la regla de cuidadores distintos)?
6. **Ola por año calendario.** 2025 = septiembre de 2025; 2026 = marzo a septiembre de 2026. ¿Es la definición de ola del estudio?
7. **Señales del adulto** (provisionales, `TEXTOS_APROBADOS = False`): ánimo = EPDS ≥ 13; autolesión = ítem 10 distinto de «No, nunca». Uso y redacción de la EPDS fuera del periodo perinatal (spec §8.4).
8. **Estado de las alertas del adulto.** La 4a solo muestra prevalencias con IC a investigadores; los estados «Para tener presente» / «Prioridad» y los mensajes por rol llegan con la 4b.
9. **Ruta de adultos.** `catalog.ruta_adulto` usa la ruta de adultos de la fase 3, sin teléfonos de Chía hasta que el equipo los confirme.
10. **Columnas 181–185, 200–207 y 208.** 181–185 repiten ítems prosociales del SDQ, 200–206 serían el ARI de un tercer hijo, 207 pregunta por otro hijo y 208 pide su nombre. Se ignoran (la 208 nunca se lee). ¿Hubo una versión del formulario con tercer hijo?

## Observaciones de los datos (solo agregados, 8-oct-2026)

Calculadas con este código y una clave de prueba; nada individual se imprimió. Solo se leyó la fila de encabezados y conteos agregados de etiquetas y patrones.

- **Filas:** 779; 23 sin consentimiento; **756** válidas. Olas: **142** en sep-2025 y **614** en 2026 (448 en marzo, 136 en abril, el resto de mayo a septiembre). Quién responde: mamá 569, papá 135, otro cuidador 52.
- **Cuidadores:** **734** distintos; 22 respuestas repetidas del mismo cuidador (6 entre olas, 16 en la misma ola).
- **Niños:** 973 filas (217 con hijo 2) y **886** únicos, como dice la spec. Pero el origen de los repetidos no es el que dice la spec («casi siempre los dos padres»): **72** son el mismo niño como hijo 1 y hijo 2 en un mismo envío, solo **6** niños los reportan dos cuidadores distintos y **5** se repiten entre olas.
- **Etiquetas:** todas las respuestas se mapean (0 sin mapa), incluidas las 10 de la EPDS por su texto, con sus erratas («simpre», «sobrellevarllas», «amenudo»). PSS: 4 «Columna 6» (en los ítems 7 y 9).
- **EPDS:** sobre las 756 respuestas, probable (≥ 13) **23,3 %** y autolesión **11,0 %**, igual que la spec; tras deduplicar cuidadores, 23,6 % y 11,2 %. Posible (≥ 10): 41,6 %.
- **α (cuidadores, base publicable):** PSS 0,74; EPDS 0,86; MSPSS 0,95 (total y fuentes); barrio 0,79. SDQ de padres: total 0,82, pares 0,44 (baja, como es habitual).
- **Edad del niño:** con la regla del plan, 9 no numéricas y 15 fuera de 4–17 (la spec contaba 89 «no numéricas» porque incluía «10 años»).
- **Curso → grado:** 19 de 973 filas sin resolver. Tras deduplicar: 712 niños en grados del estudio (cuarto 124, quinto 108, sexto 100, séptimo 101, octavo 89, noveno 95, décimo 95), 157 fuera del rango y 17 sin dato.
- **Colegio** (respuestas con consentimiento): LauV 448, JJC 121 (la spec decía 119; la diferencia es «Jj casas»), CND 71, SJMEB 39, La Balsa 24, DiosCh 13, Bojacá 12, OTRO 12, SMR 6, Fagua 4, CdP 3, y 1 cada uno Fusca, Tiquiza y Fonquetá.
- **ARI de padres:** completo en 382 hijos 1 y 93 hijos 2 (la spec decía 94), ninguno en 2025.
- **Base publicable:** 7 colegios publicables en los dos marcos (Bojacá, CND, DiosCh, JJC, La Balsa, LauV, SJMEB), los 7 grados del estudio, 13 celdas en el marco de cuidadores y 15 en el de niños. El resto (158 cuidadores de colegios pequeños, OTRO o fuera de grado) entra en el total.
- **Encabezado:** 209 columnas; la 208 es «Indique el nombre completo de su hijo(a)» (la spec la daba por vacía): se trata como nombre y no se lee.

## Autorrevisión contra la spec

| Spec | Dónde queda |
|---|---|
| §3.2 columnas por posición, PSS con inversos de docentes y «Columna 6», EPDS con etiquetas propias, MSPSS 5/4/3, APQ 78–81, estrés parental 103–107 y 117, hijo 2, teléfono descartado, ARI parcial, columnas vacías | Tasks 2, 3 y 5; prueba de que la PSS coincide con `preparar_docentes` |
| §4 nada individual; mínimo de 10 en cuidadores distintos | Tasks 3, 6, 7 y 10 (centinelas sintéticos y reales; base por `nunique`) |
| §4 nada deducible | `estudiantes.supresion.aplicar` en cada marco (Task 7); prueba de que toda proporción publicada cumple `3 ≤ k ≤ n − 3` |
| §4 a Supabase solo agregados; el público no importa lo de investigación | Nada sube en 4a; pruebas de `main.py` en comunidad (Task 9) |
| §4 textos fijos | `catalog.TEXTOS_APROBADOS = False`; avisos fijos en el catálogo |
| §5.1 base publicable y todo o nada | `cuidadores.privacidad` (igual a la de estudiantes con una fila por cuidador) |
| §5.2 tabla única de colegios | `core.colegios.normalizar`; «OTRO»/«SIN_DATO» nunca forman grupo |
| §5.5 archivos `catalog`, `ingest`, `scoring`, `pipeline`, `ui/cuidadores.py`, `views/cuidadores_investigador.py` | Tasks 2–9. `publicar.py`, `lectura.py`, `cuidadores_comunidad.py` y `cuidadores_informe.py` son de la 4b |
| §5.5 HMAC con clave local, `C…` y `N…` | Task 1 (`core.seudonimo`), sin clave en el código |
| §5.5 deduplicación de niños y de cuidadores | Task 4, con prueba de la prioridad completa |
| §5.5 puntuaciones (SDQ padres 4–17, ARI 1–6, PSS terciles, EPDS ≥ 10 / ≥ 13 e ítem 10, MSPSS por fuente, APQ castigo físico, estrés parental sin total, barrio 0–10) | Task 5 |
| §5.5 curso libre con «501», «1002», «Sexto 602», cuarto a décimo | Task 3, con las variantes sintéticas y la prueba real de cuántos quedan sin resolver |
| §5.5 investigador: pestañas de estudiantes + filtro de ola solo local | Tasks 8 y 9; el filtro no se publica (nada se publica en 4a) |
| §5.5 despliegue público solo tras aprobación | `CUIDADORES_PUBLICO = False`; comunidad sigue con `["Estudiantes 360"]` |
| §5.3 corte de importaciones de `main.py` | Pruebas de `test_navegacion` y `test_modo_despliegue` ampliadas |
| §7 pruebas sintéticas con centinelas, datos reales que se omiten, Playwright | Tasks 2–10 y 13 |
| §7 no regresión de estudiantes | Task 12 (`git diff` vacío y lote del ensayo idéntico byte a byte) |

**Lo que la spec pide y esta fase deja explícitamente para después:** mensajes y tarjetas de comunidad, estados y rutas por rol de las alertas del adulto, informes y Supabase (4b); díadas y triangulación (fase 5).

## Verificación del plan

El código de las Tasks 1 a 11 se escribió y se probó en una copia del repositorio (worktree en el scratchpad) antes de escribir este plan:

- Python 3.13 (pandas 2): **841 passed, 4 skipped** con el archivo real presente (674 + 167 nuevas).
- Python 3.14 (pandas 3.0.6): **845 passed**.
- Ensayo de estudiantes: el lote es idéntico byte a byte con y sin el código de la fase 4a.
- `AppTest` de la página: sin archivo, sin clave y con el formulario sintético (pestañas, filtro de ola y marco de niños) sin excepciones.
