# Fase 5 · Triangulación 360 (solo investigadores) — plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** el equipo investigador ve, en local y solo en los modos completo e investigador, la página «Triangulación 360» con dos capas. **Capa 1, por colegio** (y por grado con estudiantes y cuidadores): cada actor frente al resto del municipio del mismo actor, en unidades de su DE individual con IC, y la clasificación coincidencia / tensión / co-ocurrencia. **Capa 2, díadas niño–cuidador:** enlace exacto por seudónimo HMAC del nombre del niño, verificado con el colegio, con su informe de calidad y los análisis de acuerdo del SDQ, «malestar que el cuidador no ve», apoyo familiar por fuente y asociaciones con errores agrupados por familia. Todo lo que se muestra o exporta es agregado (≥ 10, cuidadores distintos donde corresponde; proporciones con la regla 3 ≤ k ≤ n − 3) y se descarga en un ZIP local con tablas, figuras y una metodología de plantilla fija. Nada sube a Supabase. El despliegue público no ve ni importa nada de la triangulación.

**Arquitectura.** Todo lo nuevo vive en **módulos nuevos**, que Streamlit Cloud siempre importa frescos:

| Módulo nuevo | Qué contiene |
|---|---|
| `src/triangulacion/catalogo.py` | Constructos (marco, columna, objeto, dirección, binario), pares del mismo objeto y de co-ocurrencia, variables de las díadas y avisos fijos |
| `src/triangulacion/estadistica.py` | CCI(A,1), kappa ponderado lineal, Bland–Altman, media con errores agrupados, correlación con IC de Fisher, bootstrap por familias, MCO con efectos fijos y errores agrupados, reglas de cifras pequeñas. Solo numpy/scipy y `estudiantes.stats.ols_cluster` |
| `src/triangulacion/fuentes.py` | Localiza y carga los tres actores en local: estudiantes con el seudónimo del niño, cuidadores (fase 4a) y docentes (archivo codificado o crudo vía `scripts/preparar_docentes.py`) |
| `src/triangulacion/capa1.py` | Átomos de la base publicable de cada módulo, diferencias estandarizadas por colegio y por grado, clasificación |
| `src/triangulacion/enlace.py` | Enlace exacto verificado con el colegio e informe de calidad agregado |
| `src/triangulacion/diadas.py` | Acuerdo SDQ, Bland–Altman agrupado, malestar no visto, apoyo familiar y asociaciones |
| `src/triangulacion/pipeline.py` | `Triangulacion`: solo agregados (la tabla de díadas nunca sale de `analizar`) |
| `src/triangulacion/exportar.py` | Tablas CSV, figuras PNG, `metodologia.md` fija y ZIP |
| `src/ui/triangulacion.py`, `src/ui/views/triangulacion_investigador.py` | Página (archivos locales, clave, módulo viejo) y vista en capas |

**El único cambio a estudiantes.** `estudiantes.ingest.cargar` y `cargar_varios` aceptan un argumento nuevo, `clave_nino`. Solo si quien llama lo pasa (la triangulación local) se añade la columna `N_hmac` = `core.seudonimo.seudonimo(nombre, "N", clave)`, el mismo seudónimo que Cuidadores 360 calcula para el hijo. El pipeline, la vista y la publicación de estudiantes nunca lo pasan, así que su salida no cambia ni en una columna (Task 1 lo prueba y compara byte a byte el lote del ensayo de publicación).

**Módulos rancios.** Cambian tres archivos existentes: `src/estudiantes/ingest.py` (argumento nuevo; la triangulación comprueba con `inspect.signature` que existe y, si no, pide reiniciar con `ModuloRancio`), `src/core/navegacion.py` (Triangulación entra en `DISPONIBLES`; con un `navegacion` viejo la página no aparece hasta el «Reboot app») y `main.py` (usa `nav.PAGINA_TRIANGULACION`, que existe desde la fase 2).

**Tech stack:** Python 3.13 local / 3.14 en Streamlit Cloud, pandas (2.x local, 3.x en 3.14), numpy, scipy, matplotlib, Streamlit (`AppTest`), pytest, openpyxl y Playwright MCP. **No se añade `statsmodels`** (no está en `requirements.txt`): lo que hace falta se implementa con numpy/scipy y con `estudiantes.stats.ols_cluster`.

**Spec:** `docs/superpowers/specs/2026-10-06-cuidadores-alertas-triangulacion-design.md`: §5.6, con §4, §5.1, §5.2, §6, §7 y §10.

**Restricciones que no se negocian:**
- **Nada individual.**
  - Ningún nombre, teléfono, seudónimo (`C…`, `N…`, `E…`), fila ni díada en pantallas, figuras, tablas o el ZIP. `pipeline.Triangulacion` solo guarda agregados; la tabla de díadas vive y muere dentro de `pipeline.analizar`.
  - Toda media exige ≥ 10 unidades (cuidadores distintos en los marcos de cuidadores; familias distintas en las díadas). Toda proporción cumple 3 ≤ k ≤ n − 3, en filas y en unidades distintas, también por resta dentro de la triangulación.
  - Los conteos por debajo de 10 se muestran como «<10».
- **Clave local.** `OBS360_CLAVE_HMAC` (entorno o `.streamlit/secrets.toml`, ignorado por git) ya existe desde la fase 4a. Las pruebas usan su propia clave de prueba. Nunca se imprime, nunca se escribe en el repositorio y nunca va en los secretos de un despliegue.
- **Datos reales.**
  - Nunca se abren a mano los archivos de `../datos_fuente_360` (estudiantes, cuidadores y docentes traen nombres y teléfonos de menores y adultos). `Datos_Cuidador_corregido.csv` no se abre.
  - Las pruebas reales se omiten si falta algún archivo y solo comparan agregados. Sus mensajes de fallo nunca muestran valores (`assert n == 0`, nunca una lista).
  - Ningún comando de este plan imprime filas, nombres, teléfonos ni texto libre.
- **Solo local.** Nada sube a Supabase. En el despliegue del equipo (sin archivos) la página muestra un mensaje fijo; en comunidad no aparece en el menú y `main.py` no importa nada de la triangulación antes del corte público.
- **Textos fijos y provisionales** (`catalogo.TEXTOS_APROBADOS = False`). Nunca los redacta la IA.
- **Git.**
  - La rama `feature/fase5-triangulacion` ya existe (sale de `feature/fase4a-cuidadores`, PR #10 sin fusionar) y ya trae este plan: no se crea ni se cambia de rama.
  - Nunca `git add -A`: siempre los archivos por nombre. Los dos `.docx` sin seguimiento de la raíz no se tocan.
  - No se hace `push` hasta la Task 13 y no se fusiona sin permiso del usuario.
- Cada commit termina con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

**Comandos de prueba** (desde la raíz del repo):
- Python 3.13: `.venv/bin/python -m pytest -q`. Línea base al empezar: **852 passed, 4 skipped**.
- Python 3.14 con WeasyPrint (producción): `"$VENV314/bin/python" -m pytest -q`. Línea base: **856 passed**. Con

  ```bash
  VENV314=/private/tmp/claude-501/-Users-joseamorocho-Documents-app-360-observatorio-SaludOrganizacional/73d67104-c128-41eb-b044-923af344a71f/scratchpad/venv314
  ```

  Si ese directorio ya no existe (el scratchpad es de la sesión), se recrea como en la Task 11, Step 1.

---

## Decisiones de diseño (tomadas en este plan; las que necesitan al equipo están en «Preguntas abiertas»)

| Tema | Decisión |
|---|---|
| Seudónimo del niño en estudiantes | Argumento explícito `clave_nino` en `ingest.cargar` / `cargar_varios`, no «cuando la clave esté disponible»: así, aunque la máquina local tenga la clave, el pipeline de estudiantes nunca crea `N_hmac` y sus salidas, su vista y su publicación son idénticas (prueba de columnas y ensayo byte a byte). La triangulación quita además la columna `ID` (SHA-1 sin clave) apenas carga |
| Enlace | Igualdad exacta de `N_hmac` (estudiantes) e `ID_nino` (cuidadores, ya deduplicado), uno a uno, y **mismo código de colegio** reconocido (nunca «OTRO» ni «SIN_DATO»). Sin coincidencias aproximadas: la normalización de `core.texto.norm_txt` (mayúsculas, tildes, puntuación, espacios) es la única tolerancia, la misma de los dos seudónimos |
| Familia | `ID_cuidador` del cuidador que quedó para ese niño en la deduplicación de la 4a. Es el conglomerado de los errores y la unidad que cuenta para el mínimo de 10. Las variables del adulto son las de su respuesta más reciente (marco cuidador de la 4a) |
| Docentes | Se prefiere el archivo ya codificado por `scripts/preparar_docentes.py` (sin nombres; patrón «codificado» en el nombre); si solo está la exportación cruda («profesores»), se codifica en memoria con `preparar`, que descarta el nombre. Colegio con `codigo_desde_nombre`. **Clima laboral = apoyo del líder** (CL, 7 ítems HSE, 0–5, media), **apoyo percibido = apoyo de compañeros** (AP, 3 ítems, 0–5), **PSS-10** con los inversos ya aplicados por `preparar` (0–40, prorrateo con 9 de 10, como cuidadores) y **desgaste** (BLG_Desg, 4 ítems, 1–7) |
| Constructos de estudiantes | SDQ total y emocional (autoinforme), PSSM total, «sin adulto de confianza» (PSSM 7 ≤ 2, binario, el corte de `scoring.sobre_cortes`), señal de malestar (`alertas.marcar`, binaria) y MSPSS familia |
| Constructos de cuidadores | Marco niño: SDQ total y emocional de padres. Marco cuidador: PSS, EPDS, castigo físico (binario), barrio y MSPSS familia. Solo cuidadores con hijo en los grados del estudio (spec: 631 de 756; con la deduplicación de la 4a son 614 cuidadores distintos) |
| Colegios de la capa 1 | Los **publicables (§5.1) en estudiantes, cuidadores y docentes a la vez**: con los datos de octubre de 2026, JJC, La Balsa, LauV y SJMEB, como dice la spec |
| Base y restas en la capa 1 | Cada marco se parte en **átomos** con la base publicable de su módulo (`estudiantes.privacidad` y `cuidadores.privacidad`: celdas colegio × grado con 10 o más, colegios publicados enteros y el resto R si el módulo lo admite; en docentes, colegios con 10 o más y R con la misma regla de resto). Colegio, grado y «resto del municipio» son uniones de átomos, así que una resta entre la tabla por colegio y la tabla por grado nunca aísla una celda pequeña. Por constructo, un átomo con 1 a 9 unidades con dato, o con menos de 3 casos o no casos en un binario, sale del constructo (todo o nada) |
| Medida | d = (media del grupo − media del resto) / DE individual del actor (sobre los átomos que entran); IC = d ± 1,96 · √(s²₁/n₁ + s²₂/n₂) / DE. En los binarios la media es una proporción y se muestra como % |
| Clasificación | Solo en pares del mismo objeto (conducta del niño: SDQ autoinforme frente a SDQ de padres, total y emocional; clima escolar: PSSM y «sin adulto» frente a apoyo del líder y de compañeros). Se orienta con la dirección del constructo (positivo = mejor que el resto). «Tensión»: los dos IC excluyen el cero en direcciones opuestas; «coincidencia»: en la misma; si no, «sin diferencia clara». PSS de cuidadores y docentes, malestar del niño con EPDS y con desgaste, y MSPSS de familia del niño con el del cuidador: «co-ocurrencia» |
| Por grado | Solo marcos de estudiantes, cuidadores (grado del hijo 1) y niños; los grados publicables en los tres. La vista dice que los docentes no tienen grado |
| Despliegue de investigador sin archivos | Mensaje fijo (`catalogo.AVISO_DESPLIEGUE`) y la lista de qué archivos faltan (sí / no). **No se lee Supabase en esta fase:** no hay agregados publicados de cuidadores (llegan con la 4b) y la corrida de estudiantes no publica medias ni DE por colegio (solo bandas y cortes), así que la capa 1 no se puede armar desde lo publicado. Ver «Preguntas abiertas» |
| Estadística | CCI(A,1) de McGraw y Wong (= CCI(2,1) de Shrout y Fleiss); kappa ponderado **lineal** sobre las 4 bandas, cada informante con sus cortes (autoinforme / padres); Spearman y Pearson con IC de Fisher; diferencia media con IC por errores agrupados por familia (CR1, t con G − 1 gl); límites de Bland–Altman ± 1,96 DE; IC de CCI y kappa por bootstrap percentil remuestreando familias (500, semilla 1) |
| Bland–Altman | **Agrupado, sin puntos individuales:** hasta 5 grupos por quintil del promedio de los dos informantes, cada uno con ≥ 10 díadas de ≥ 10 familias (si no caben, menos grupos); la figura dibuja la media de cada grupo con su IC, la diferencia media y los dos límites |
| Malestar que el cuidador no ve | Vigente: el niño en banda alta o muy alta de su SDQ total (autoinforme) **o** con la señal de malestar, y el cuidador lo ubica en «cercano al promedio» (SDQ total de padres). Sensibilidad: lo mismo con el SDQ emocional. Se publican el % sobre todas las díadas, el % con malestar y el % no visto entre ellos (Wilson), y solo si las tres partes (sin malestar / visto / no visto) tienen ≥ 3 díadas y ≥ 3 familias, y su complemento también. Nunca el número de casos |
| Apoyo familiar | MSPSS del niño frente al del cuidador por fuente (familia, amigos, persona especial): Spearman y diferencia media, con el aviso fijo de la 4a (reparto 4/4/4 frente a 5/4/3 y redacción distinta) |
| Asociaciones | MCO con el SDQ del niño (total, internalizante y externalizante, autoinforme, en z) y los cuatro predictores a la vez (EPDS, PSS y barrio en z; castigo físico 0/1), controles de sexo y edad del niño, efecto fijo de colegio, errores agrupados por familia; sensibilidad solo con LauV (sin efecto fijo). ≥ 30 díadas completas y ≥ 10 familias; un predictor binario exige ≥ 10 díadas y familias en cada nivel (si no, se omite y se dice). q de Benjamini–Hochberg por muestra. Si el modelo es singular, no se estima y se dice |
| Calidad del enlace | Coincidencias, verificadas, descartes por colegio distinto y por colegio no reconocido, familias, díadas por colegio y por nivel (conteos legibles, «<10») y concordancia de sexo, edad (± 1 año) y grado. Las tasas siguen la regla: con menos de 3 discordantes se muestra «casi todas» (o «casi ninguna»); con n < 10, «—» |
| Exportación | ZIP local: 10 tablas CSV, `figuras/capa1_<colegio>.png`, `figuras/bland_altman_<subescala>.png`, `metodologia.md` (plantilla fija con conteos agregados) y `version_analisis.txt`. Nada a Supabase |
| Página | `st.cache_resource` por la firma de los archivos (ruta y fecha de modificación). Sin clave: el error de `ClaveAusente`. Con un `estudiantes.ingest` viejo en memoria: aviso para reiniciar. Pestañas: Resumen · Por colegio · Por grado · Enlace de díadas · Acuerdo SDQ · Malestar no visto · Apoyo familiar · Asociaciones · Metodología · Exportar (spec §6: primero el resumen, luego las tablas, luego la metodología) |
| Navegación | `PAGINA_TRIANGULACION` entra en `DISPONIBLES`; nunca en `PUBLICAS`. `main.py` la enruta solo después del corte público |

---

## Mapa de archivos

| Archivo | Qué cambia |
|---|---|
| `src/estudiantes/ingest.py` | `COLUMNA_NINO = "N_hmac"`; `cargar(…, clave_nino=None)` y `cargar_varios(…, clave_nino=None)` |
| `src/triangulacion/__init__.py` (nuevo) | Docstring del paquete |
| `src/triangulacion/catalogo.py` (nuevo) | `Constructo`, `CONSTRUCTOS`, `Par`, `PARES`, variables de díadas, avisos |
| `src/triangulacion/estadistica.py` (nuevo) | `icc_a1`, `kappa_ponderado`, `bland_altman`, `media_agrupada`, `correlacion_ic`, `bootstrap_ic`, `ols_agrupado`, `suficiente`, `partes_seguras` |
| `src/triangulacion/fuentes.py` (nuevo) | `ModuloRancio`, `Disponibles`, `Fuentes`, `localizar`, `localizar_docentes`, `leer_docentes`, `puntuar_docentes`, `preparar_estudiantes`, `cargar_estudiantes`, `cargar_cuidadores`, `cargar` |
| `src/triangulacion/capa1.py` (nuevo) | `Atomo`, `Capa1`, `marcos`, `atomos`, `diferencias_constructo`, `diferencias`, `clasificar`, `clasificacion`, `analizar` |
| `src/triangulacion/enlace.py` (nuevo) | `Enlace`, `enlazar`, `tasa_legible`, `conteo_legible`, `tabla_calidad` |
| `src/triangulacion/diadas.py` (nuevo) | `Diadas`, `acuerdo_sdq`, `bland_altman_agrupado`, `malestar_no_visto`, `apoyo_familiar`, `asociaciones`, `analizar` |
| `src/triangulacion/pipeline.py` (nuevo) | `Triangulacion`, `analizar`, `cargar_y_analizar` |
| `src/triangulacion/exportar.py` (nuevo) | `tablas`, `figura_capa1`, `figura_bland_altman`, `metodologia_md`, `version_txt`, `archivos`, `paquete_zip` |
| `src/ui/triangulacion.py` (nuevo) | `render_triangulacion` |
| `src/ui/views/triangulacion_investigador.py` (nuevo) | `PESTANAS`, `hallazgos`, `conteos_actores`, pestañas y `render_investigador` |
| `src/core/navegacion.py` | `DISPONIBLES` con Triangulación |
| `main.py` | Rama `PAGINA_TRIANGULACION` después del corte público |
| `tests/triangulacion_sinteticos.py` (nuevo) | Estudiantes y docentes sintéticos que comparten niños con el formulario sintético de cuidadores |
| `tests/test_estudiantes_seudonimo_nino.py`, `tests/test_triangulacion_{estadistica,fuentes,capa1,enlace,diadas,privacidad,pagina,reales}.py` (nuevos) | Pruebas |
| `tests/test_navegacion.py`, `tests/test_modo_despliegue.py` | Triangulación para investigadores, nunca en comunidad; nada de la triangulación antes del corte |
| `DESPLIEGUE.md`, `ARCHITECTURE.md` | Documentación |

**Lo que no cambia:** el resto de `src/estudiantes/` (pipeline, scoring, privacidad, supresión, publicar, lectura), `src/cuidadores/`, `src/ui/estudiantes.py`, `src/ui/cuidadores.py`, `src/ui/views/estudiantes_*.py`, `src/ui/views/cuidadores_investigador.py`, `src/core/{colegios,modo,rutas,seudonimo,texto}.py`, `scripts/preparar_docentes.py`, `requirements.txt` y Supabase.

---

### Task 0: Línea base, foto del ensayo y clave local

**Files:** ninguno del repositorio.

- [ ] **Step 1: Comprobar la rama (ya existe; no se crea)**

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional
git branch --show-current          # → feature/fase5-triangulacion
git log --oneline -2               # → «docs(plan): fase 5 · triangulación» sobre 1968b81
git status --short                 # solo los dos .docx sin seguimiento; no se tocan
```

Si la rama no es `feature/fase5-triangulacion` o el árbol tiene cambios propios, parar y avisar al usuario.

- [ ] **Step 2: Línea base**

Run: `.venv/bin/python -m pytest -q`
Expected: `852 passed, 4 skipped`.

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: `856 passed`. Anotar los totales para el PR.

- [ ] **Step 3: Foto del ensayo de estudiantes, fuera del repositorio**

Sirve para probar en las Tasks 1 y 11 que estudiantes no cambia. Solo agregados; si faltan los formularios, el comando falla y este paso se omite.

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_antes_5.json" > /dev/null
echo "código de salida: $?"
```
Expected: `código de salida: 0`.

- [ ] **Step 4: La clave local ya existe (fase 4a; sin imprimirla)**

```bash
git check-ignore -q .streamlit/secrets.toml && echo "ignorado por git"
grep -c "^OBS360_CLAVE_HMAC" .streamlit/secrets.toml
```
Expected: `ignorado por git` y `1`. Si da `0`, crearla como en la Task 0, Step 4 del plan de la fase 4a (`docs/superpowers/plans/2026-10-08-fase4a-cuidadores.md`). Nunca hacer `cat` de ese archivo.

Sin commit.

---

### Task 1: Seudónimo del niño en la carga de estudiantes (sin cambiar estudiantes)

**Files:**
- Modify: `src/estudiantes/ingest.py:34-36, 144-149, 186-192, 308-319`
- Create: `tests/triangulacion_sinteticos.py`
- Create: `tests/test_estudiantes_seudonimo_nino.py`

- [ ] **Step 1: Escribir los actores sintéticos y las pruebas que fallan**

`tests/triangulacion_sinteticos.py` (lo usan todas las pruebas de esta fase):

```python
"""
Los tres actores sintéticos para la triangulación (spec §7).

Nada sale de los datos reales. Cuidadores es el formulario sintético de la
fase 4a (`cuidadores_sinteticos`); estudiantes y docentes se arman aquí, con
niños que comparten nombre con los hijos de ese formulario:

  · Enlazan (mismo nombre y mismo colegio): los hijos 1 de los cuidadores 0 a
    71 (LauV, JJC y SJMEB), salvo el 13 (sin estudiante), el 40 (estudiante en
    otro colegio: se descarta por colegio) y el 41 (estudiante con una letra
    distinta, «Nina»: no hay coincidencias aproximadas). También los hijos 2
    de los cuidadores 3, 6, 9 y 12 (familias con dos díadas).
  · No enlazan: 12 estudiantes de La Balsa, 4 de Cerca de Piedra y 10 más de
    Laura Vicuña.
  · Docentes (archivo codificado, sin nombres): LauV 15, JJC 12, SJMEB 11,
    La Balsa 10, Cerca de Piedra 5 y 2 de la Secretaría (no es colegio).

Centinelas: todos los nombres empiezan por «Centinela» y el teléfono del
formulario de cuidadores es 3000000000. Ninguno puede aparecer en una salida.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from tests import cuidadores_sinteticos as cs

CLAVE_PRUEBA = cs.CLAVE_PRUEBA
ARCHIVO_SEC = "¡Cuéntanos sobre tu bienestar emocional! (respuestas).xlsx"
ARCHIVO_PRI = "¡Cuéntanos sobre tus emociones! (respuestas).xlsx"
ARCHIVO_CUID = "Cuidando al Cuidador (respuestas).xlsx"
ARCHIVO_DOC = "Docentes_codificado.xlsx"
PRIMARIA = ("Cuarto", "Quinto")
SIN_ESTUDIANTE, OTRO_COLEGIO, MAL_ESCRITO = 13, 40, 41
HIJOS2 = (3, 6, 9, 12)
DOCENTES = (("Laura Vicuña", 15), ("José Joaquín Casas", 12),
            ("San Josemaría Escrivá de Balaguer", 11), ("La Balsa", 10),
            ("Cerca de Piedra", 5), ("Secretaría de Educación", 2))
SDQ_OPC = ["No es cierto", "Algo cierto", "Muy cierto"]
RCADS_OPC = ["Nunca", "Algunas veces", "Con frecuencia", "Siempre"]
ERQ_OPC = ["Nada parecido a mi", "Poco parecido a mi", "Se parece a mi",
           "Bastante parecido a mi", "Exactamente igual a mi"]
MSPSS_OPC = ["Nunca", "Casi nunca", "Algunas veces", "Casi siempre", "Siempre"]
TD_OPC = ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]


def ninos_del_plan() -> list[tuple[int, str, str]]:
    """(i, texto del colegio, grado) de cada hijo 1 del formulario sintético de cuidadores."""
    salida, i = [], 0
    for colegio, grupos in cs.PLAN:
        for grado, cuantos in grupos:
            for _ in range(cuantos):
                salida.append((i, colegio, grado))
                i += 1
    return salida


def _estudiante(rng, nombre: str, colegio: str, grado: str, edad: int, sexo: str,
                secundaria: bool) -> dict:
    f = {"Marca temporal": "10/03/2026 10:00:00",
         "¿Quieres aportar al bienestar de todos con tus respuestas?": "Sí, quiero aportar",
         "Mi nombre completo es:": nombre, "Tengo:": f"{edad} años", "Mi sexo es:": sexo,
         "Estoy en grado": grado, "Mi colegio es:": colegio}
    for j in range(1, 26):
        f[f"SDQ [enunciado {j}]"] = SDQ_OPC[int(rng.integers(0, 3))]
    for j in range(1, 8):
        f[f"ARI [enunciado {j}]"] = SDQ_OPC[int(rng.integers(0, 3))]
    if secundaria:
        for j in range(1, 26):
            f[f"RCADS [enunciado {j}]"] = RCADS_OPC[int(rng.integers(0, 4))]
    for j in range(1, 11):
        f[f"ERQ-CA [enunciado {j}]"] = ERQ_OPC[int(rng.integers(0, 5))]
    for j in range(1, 13):
        f[f"MSPSS [enunciado {j}]"] = MSPSS_OPC[int(rng.integers(0, 5))]
    f["Siento que soy parte de mi colegio"] = int(rng.integers(1, 6))
    for j in range(2, 19):
        f[f"PSSM enunciado {j}"] = int(rng.integers(1, 6))
    for j in range(1, 11):
        f[f"Toma de decisiones  [enunciado {j}]"] = TD_OPC[int(rng.integers(0, 5))]
    return f


def estudiantes(semilla: int = 11) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(secundaria, primaria) como exportaciones de Google Forms."""
    rng = np.random.default_rng(semilla)
    filas = []
    plan = ninos_del_plan()
    otro = {"Colegio Laura Vicuña": "IE José Joaquín Casas"}
    for i, colegio, grado in plan:
        if colegio == "Colegio La Balsa" or i >= 72 or i == SIN_ESTUDIANTE:
            continue
        nombre = cs.nombre_nino(i, 1)
        if i == MAL_ESCRITO:
            nombre = nombre.replace("Nino", "Nina")
        if i == OTRO_COLEGIO:
            colegio = otro.get(colegio, "Colegio Laura Vicuña")
        filas.append((nombre, colegio, grado, 10 + i % 6, "Mujer" if i % 2 else "Hombre"))
        if i in HIJOS2:
            filas.append((cs.nombre_nino(i, 2), colegio, grado, 11, "Hombre"))
    for k in range(12):
        filas.append((f"Centinela Estudiante Balsa {k:02d}", "Colegio La Balsa", "Sexto", 12,
                      "Mujer" if k % 2 else "Hombre"))
    for k in range(4):
        filas.append((f"Centinela Estudiante Piedra {k:02d}", "Cerca de Piedra", "Séptimo",
                      13, "Mujer"))
    for k in range(10):
        filas.append((f"Centinela Estudiante Vicuna {k:02d}", "Colegio Laura Vicuña", "Noveno",
                      15, "Hombre" if k % 2 else "Mujer"))
    sec = [_estudiante(rng, n, c, g, e, s, True) for n, c, g, e, s in filas if g not in PRIMARIA]
    pri = [_estudiante(rng, n, c, g, e, s, False) for n, c, g, e, s in filas if g in PRIMARIA]
    return pd.DataFrame(sec), pd.DataFrame(pri)


def docentes(semilla: int = 5) -> pd.DataFrame:
    """Archivo de docentes ya codificado (como el de scripts/preparar_docentes.py)."""
    rng = np.random.default_rng(semilla)
    filas = []
    for colegio, n in DOCENTES:
        for _ in range(n):
            f = {"ID": f"D{len(filas) + 1:03d}", "Colegio": colegio}
            f.update({f"PSS{i}": int(rng.integers(0, 5)) for i in range(1, 11)})
            f.update({f"CL{i}": int(rng.integers(0, 6)) for i in range(1, 8)})
            f.update({f"AP{i}": int(rng.integers(0, 6)) for i in range(1, 4)})
            f.update({f"BLG_Desg{i}": int(rng.integers(1, 8)) for i in range(1, 5)})
            filas.append(f)
    return pd.DataFrame(filas)


def escribir(base) -> str:
    """Los tres actores en `base/{estudiantes,cuidadores,docentes}`, como en datos_fuente_360."""
    base = str(base)
    for sub in ("estudiantes", "cuidadores", "docentes"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    sec, pri = estudiantes()
    sec.to_excel(os.path.join(base, "estudiantes", ARCHIVO_SEC), index=False)
    pri.to_excel(os.path.join(base, "estudiantes", ARCHIVO_PRI), index=False)
    cs.escribir(os.path.join(base, "cuidadores", ARCHIVO_CUID))
    docentes().to_excel(os.path.join(base, "docentes", ARCHIVO_DOC), index=False)
    return base


def textos_prohibidos() -> list[str]:
    """Lo que nunca puede aparecer en ninguna salida."""
    return cs.textos_prohibidos()
```

`tests/test_estudiantes_seudonimo_nino.py`:

```python
"""
Estudiantes · seudónimo del niño con clave (fase 5).

La carga de estudiantes solo añade `N_hmac` si quien llama pasa la clave
(`clave_nino`). Sin ella, la salida es exactamente la de antes: el pipeline,
la vista y la publicación de estudiantes no cambian.
"""
import pandas as pd

from src.core import seudonimo as seud
from src.estudiantes import ingest
from tests import cuidadores_sinteticos as cs
from tests import triangulacion_sinteticos as ts

K = cs.CLAVE_PRUEBA.encode()


def _formularios(tmp_path):
    ts.escribir(tmp_path)
    base = tmp_path / "estudiantes"
    return [str(base / ts.ARCHIVO_SEC), str(base / ts.ARCHIVO_PRI)]


def test_sin_clave_la_salida_no_cambia(tmp_path):
    sec, _ = ts.estudiantes()
    sin, inf_sin = ingest.cargar(sec)
    con, inf_con = ingest.cargar(sec, clave_nino=K)
    assert ingest.COLUMNA_NINO not in sin.columns
    assert [c for c in con.columns if c != ingest.COLUMNA_NINO] == list(sin.columns)
    pd.testing.assert_frame_equal(con.drop(columns=[ingest.COLUMNA_NINO]), sin)
    assert inf_sin.como_dict() == inf_con.como_dict()


def test_el_seudonimo_es_el_del_hijo_en_cuidadores():
    sec, _ = ts.estudiantes()
    con, _ = ingest.cargar(sec, clave_nino=K)
    esperado = seud.seudonimo(cs.nombre_nino(30, 1), "N", K)
    assert esperado in set(con[ingest.COLUMNA_NINO])
    assert con[ingest.COLUMNA_NINO].str.fullmatch(r"N[0-9a-f]{8}").all()


def test_sin_columna_de_nombre_el_seudonimo_queda_vacio():
    sec, _ = ts.estudiantes()
    con, _ = ingest.cargar(sec.drop(columns=["Mi nombre completo es:"]), clave_nino=K)
    assert con[ingest.COLUMNA_NINO].isna().all()


def test_cargar_varios_pasa_la_clave(tmp_path):
    rutas = _formularios(tmp_path)
    sin, _ = ingest.cargar_varios(rutas)
    con, _ = ingest.cargar_varios(rutas, clave_nino=K)
    assert ingest.COLUMNA_NINO not in sin.columns
    assert con[ingest.COLUMNA_NINO].notna().all()
    pd.testing.assert_frame_equal(con.drop(columns=[ingest.COLUMNA_NINO]), sin)


def test_el_pipeline_de_estudiantes_nunca_pide_la_clave(tmp_path):
    from src.estudiantes import pipeline
    resultados, _ = pipeline.cargar_y_analizar(_formularios(tmp_path), n_boot=10)
    for a in resultados.values():
        assert ingest.COLUMNA_NINO not in a.datos.columns
        assert not any(str(c).startswith("N_") for c in a.datos.columns)
```

Run: `.venv/bin/python -m pytest tests/test_estudiantes_seudonimo_nino.py -q`
Expected: FAIL: `TypeError: cargar() got an unexpected keyword argument 'clave_nino'` y `AttributeError: module 'src.estudiantes.ingest' has no attribute 'COLUMNA_NINO'`.

- [ ] **Step 2: Implementar**

En `src/estudiantes/ingest.py`, sustituir:

```python
def _hash_id(nombre_normalizado: str) -> str:
    return "E" + hashlib.sha1(nombre_normalizado.encode()).hexdigest()[:8]
```

por:

```python
def _hash_id(nombre_normalizado: str) -> str:
    return "E" + hashlib.sha1(nombre_normalizado.encode()).hexdigest()[:8]


# Seudónimo del niño con clave local (core.seudonimo, letra «N»), el mismo que
# calcula Cuidadores 360 para el hijo. Solo existe si quien llama pasa la clave
# (`clave_nino`): lo pide la triangulación local (fase 5). El pipeline de
# estudiantes, la vista y la publicación nunca la pasan, así que su salida no
# cambia ni en una columna.
COLUMNA_NINO = "N_hmac"
```

Sustituir:

```python
def cargar(ruta_o_df, nivel: str | None = None) -> tuple[pd.DataFrame, InformeIngesta]:
    """Lee un formulario de estudiantes y devuelve (DataFrame limpio, informe).

    `nivel` fuerza 'secundaria' o 'primaria'; por defecto se infiere de la
    presencia del bloque RCADS (solo lo respondió secundaria).
    """
```

por:

```python
def cargar(ruta_o_df, nivel: str | None = None, clave_nino: bytes | None = None
           ) -> tuple[pd.DataFrame, InformeIngesta]:
    """Lee un formulario de estudiantes y devuelve (DataFrame limpio, informe).

    `nivel` fuerza 'secundaria' o 'primaria'; por defecto se infiere de la
    presencia del bloque RCADS (solo lo respondió secundaria).

    `clave_nino` (solo la triangulación local): añade `COLUMNA_NINO`, el
    seudónimo HMAC «N…» del nombre con esa clave. Sin ella (lo de siempre) la
    salida es idéntica a la de antes de la fase 5.
    """
```

Sustituir:

```python
        d["ID"] = _nombre_norm.map(_hash_id)
        _clave_dedupe = _nombre_norm
    else:
        d["ID"] = [f"E{i:05d}" for i in range(len(raw))]
        _clave_dedupe = pd.Series([f"__{i}" for i in range(len(raw))], index=raw.index)
```

por:

```python
        d["ID"] = _nombre_norm.map(_hash_id)
        _clave_dedupe = _nombre_norm
        if clave_nino is not None:
            from src.core.seudonimo import seudonimo
            d[COLUMNA_NINO] = raw.iloc[:, idx_ident["nombre"]].map(
                lambda x: seudonimo(x, "N", clave_nino))
    else:
        d["ID"] = [f"E{i:05d}" for i in range(len(raw))]
        _clave_dedupe = pd.Series([f"__{i}" for i in range(len(raw))], index=raw.index)
        if clave_nino is not None:
            d[COLUMNA_NINO] = None
```

Sustituir:

```python
def cargar_varios(rutas: list, niveles: list[str] | None = None
                  ) -> tuple[pd.DataFrame, list[InformeIngesta]]:
```

por:

```python
def cargar_varios(rutas: list, niveles: list[str] | None = None,
                  clave_nino: bytes | None = None
                  ) -> tuple[pd.DataFrame, list[InformeIngesta]]:
```

Y dentro de `cargar_varios`, sustituir `        d, inf = cargar(r, nivel=nivel)` por:

```python
        d, inf = cargar(r, nivel=nivel, clave_nino=clave_nino)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_estudiantes_seudonimo_nino.py tests/test_estudiantes.py tests/test_estudiantes_publicar.py -q`
Expected: todo en verde (las 5 nuevas más las existentes, que no cambian).

- [ ] **Step 4: El ensayo de estudiantes sigue idéntico**

```bash
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_tras_task1.json" > /dev/null
cmp "$TMPDIR/obs360_lote_antes_5.json" "$TMPDIR/obs360_lote_tras_task1.json" && echo "lote de estudiantes idéntico"
```
Expected: `lote de estudiantes idéntico`. Si difiere, parar: el cambio tocó la salida de estudiantes.

- [ ] **Step 5: Commit**

```bash
git add src/estudiantes/ingest.py tests/triangulacion_sinteticos.py tests/test_estudiantes_seudonimo_nino.py
git commit -m "feat(estudiantes): seudónimo HMAC del niño solo cuando la triangulación pasa la clave" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Catálogo y estadística

**Files:**
- Create: `src/triangulacion/__init__.py`, `src/triangulacion/catalogo.py`, `src/triangulacion/estadistica.py`
- Create: `tests/test_triangulacion_estadistica.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Los valores conocidos: CCI(2,1) = 0,29 en la tabla de Shrout y Fleiss (1979); kappa de Cohen 0,4 en una tabla 2 × 2 con po = 0,7 y pe = 0,5; kappa ponderado lineal 39/59 en la tabla 3 × 3 de la prueba (calculado con fracciones exactas y pesos de acuerdo 1 − |i − j| / 2).

`tests/test_triangulacion_estadistica.py`:

```python
"""Triangulación · estadística contra valores conocidos."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from src.triangulacion import estadistica as est

# Shrout y Fleiss (1979), tabla 2: 6 sujetos × 4 jueces. CCI(2,1) = 0,29.
SHROUT_FLEISS = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8],
                          [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]])


def _desde_tabla(tabla):
    a, b = [], []
    for i, fila in enumerate(tabla):
        for j, n in enumerate(fila):
            a += [i] * n
            b += [j] * n
    return a, b


def test_cci_a1_de_shrout_y_fleiss():
    assert round(est.icc_a1(SHROUT_FLEISS), 2) == 0.29


def test_cci_es_uno_con_acuerdo_perfecto_y_quita_faltantes():
    Y = np.array([[1, 1], [2, 2], [5, 5], [np.nan, 3], [7, 7]])
    assert est.icc_a1(Y) == pytest.approx(1.0)


def test_cci_baja_con_un_sesgo_sistematico():
    x = np.arange(20, dtype=float)
    assert est.icc_a1(np.column_stack([x, x + 5])) < est.icc_a1(np.column_stack([x, x]))


def test_kappa_sin_ponderar_en_2x2_es_el_de_cohen():
    a, b = _desde_tabla([[20, 10], [5, 15]])        # po = 0,7; pe = 0,5
    assert est.kappa_ponderado(a, b, k=2) == pytest.approx(0.4)


def test_kappa_ponderado_lineal_3x3():
    """Calculado a mano con pesos de acuerdo 1 − |i − j| / 2: κw = 39/59."""
    a, b = _desde_tabla([[10, 2, 0], [3, 8, 1], [0, 2, 4]])
    assert est.kappa_ponderado(a, b, k=3) == pytest.approx(39 / 59)


def test_kappa_perfecto_y_con_faltantes():
    assert est.kappa_ponderado([0, 1, 2, 3, np.nan], [0, 1, 2, 3, 1]) == pytest.approx(1.0)


def test_bland_altman():
    r = est.bland_altman([3, 5, 7, 9], [1, 4, 5, 9])        # diferencias 2, 1, 2, 0
    s = np.std([2, 1, 2, 0], ddof=1)
    assert r["n"] == 4 and r["dif_media"] == pytest.approx(1.25)
    assert r["lim_inf"] == pytest.approx(1.25 - est.Z95 * s)
    assert r["lim_sup"] == pytest.approx(1.25 + est.Z95 * s)


def test_media_agrupada_con_familias_de_uno_es_la_t_clasica():
    y = np.array([1.0, 3, 2, 5, 4, 6, 2, 3])
    r = est.media_agrupada(y, np.arange(len(y)))
    t = sps.t.ppf(0.975, len(y) - 1)
    se = y.std(ddof=1) / np.sqrt(len(y))
    assert r["m"] == pytest.approx(y.mean())
    assert r["ic_inf"] == pytest.approx(y.mean() - t * se)
    assert r["ic_sup"] == pytest.approx(y.mean() + t * se)


def test_media_agrupada_ensancha_con_hermanos_iguales():
    y = np.repeat([1.0, 4, 2, 6, 3, 5], 2)
    solos = est.media_agrupada(y, np.arange(len(y)))
    familias = est.media_agrupada(y, np.repeat(np.arange(6), 2))
    assert familias["se"] > solos["se"] and familias["G"] == 6


def test_correlacion_con_ic_de_fisher():
    a = np.arange(30, dtype=float)
    b = a ** 2
    rho, lo, hi, p = est.correlacion_ic(a, b, "spearman")
    assert rho == pytest.approx(1.0) and hi == pytest.approx(1.0, abs=1e-5)
    rng = np.random.default_rng(3)
    x, y = rng.normal(size=50), rng.normal(size=50)
    r, lo, hi, _ = est.correlacion_ic(x, y, "pearson")
    z, se = np.arctanh(r), 1 / np.sqrt(47)
    assert lo == pytest.approx(np.tanh(z - est.Z95 * se))
    assert hi == pytest.approx(np.tanh(z + est.Z95 * se))


def test_bootstrap_por_familias_es_reproducible():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"x": rng.normal(size=60), "familia": np.repeat(np.arange(30), 2)})
    f = lambda d: d["x"].mean()                                     # noqa: E731
    uno = est.bootstrap_ic(df, f, "familia", n_boot=200, semilla=1)
    dos = est.bootstrap_ic(df, f, "familia", n_boot=200, semilla=1)
    assert uno == dos and uno[0] < df["x"].mean() < uno[1]


def test_mco_con_efecto_fijo_recupera_la_pendiente():
    rng = np.random.default_rng(1)
    colegio = pd.Series(np.repeat(["A", "B", "C"], 20))
    x = pd.Series(rng.normal(size=60))
    y = 2 * x + colegio.map({"A": 0.0, "B": 5.0, "C": -3.0}) + rng.normal(0, 0.01, 60)
    res = est.ols_agrupado(y, pd.DataFrame({"x": x}), pd.Series(np.arange(60)), colegio)
    assert list(res["predictor"]) == ["x"]
    assert res.iloc[0]["beta"] == pytest.approx(2.0, abs=0.01)
    assert res.iloc[0]["ic_inf"] < 2.0 < res.iloc[0]["ic_sup"]


def test_partes_seguras_cuenta_filas_y_familias():
    etiquetas = pd.Series([0] * 10 + [1] * 3)
    assert est.partes_seguras(etiquetas, None, [1])
    assert not est.partes_seguras(pd.Series([0] * 10 + [1] * 2), None, [1])
    assert not est.partes_seguras(pd.Series([0] * 3 + [1] * 10), None, [0, 1, 2])  # 2 vacía
    familias = pd.Series(list(range(10)) + [99, 99, 99])           # 3 casos, 1 familia
    assert not est.partes_seguras(etiquetas, familias, [1])


def test_suficiente_exige_familias_distintas():
    df = pd.DataFrame({"familia": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]})
    assert not est.suficiente(df, "familia")
    assert est.suficiente(df, None)
```

Run: `.venv/bin/python -m pytest tests/test_triangulacion_estadistica.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.triangulacion'`.

- [ ] **Step 2: Implementar**

`src/triangulacion/__init__.py`:

```python
"""
Triangulación 360 — solo investigadores, solo local (spec del 6-oct-2026, §5.6).

Dos capas:
  · Capa 1, por colegio (y por grado con estudiantes y cuidadores): cada actor
    frente al resto del municipio del mismo actor, en unidades de su DE
    individual, y la clasificación coincidencia / tensión / co-ocurrencia.
  · Capa 2, díadas niño–cuidador: enlace exacto por seudónimo HMAC del nombre
    del niño, verificado con el colegio, y análisis de acuerdo y asociación.

Módulos puros: `catalogo` (constructos, pares y avisos fijos), `fuentes`
(carga local de los tres actores), `estadistica`, `capa1`, `enlace`,
`diadas`, `pipeline` (`Triangulacion`, solo agregados) y `exportar` (ZIP).
La página vive en `src/ui/triangulacion.py` y nunca se importa en el
despliegue público. Nada de este paquete sube a Supabase.
"""
```

`src/triangulacion/catalogo.py`:

```python
"""
Catálogo de la Triangulación 360 — constructos, pares y textos fijos.

ÚNICA FUENTE DE VERDAD de la triangulación: qué constructo sale de qué actor y
de qué columna, hacia dónde es «mejor», qué pares hablan del mismo objeto y
los avisos fijos de la vista y de la metodología.

Los textos son provisionales (`TEXTOS_APROBADOS = False`) y los aprueba el
equipo (spec §8). Nunca los redacta la IA.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.cuidadores import catalog as cat_cuid
from src.estudiantes import catalog as cat_est

TEXTOS_APROBADOS = False

MIN_GROUP_N = cat_est.MIN_GROUP_N     # unidades distintas (cuidadores en cuidadores)
MIN_CASOS = 3                          # = estudiantes.supresion.MIN_CASOS
MIN_MODELO = 30                        # díadas completas para un modelo (como stats.modelo)
N_BOOT = 500
SEMILLA = 1
COLEGIOS_SIN_GRUPO = ("OTRO", "SIN_DATO")
COLEGIO_SENSIBILIDAD = "LauV"

# ── Marcos (de qué tabla sale cada constructo) y actores ───────────────────
ESTUDIANTE, CUIDADOR, NINO, DOCENTE = "estudiante", "cuidador", "nino", "docente"
ACTOR = {ESTUDIANTE: "Estudiantes", CUIDADOR: "Cuidadores", NINO: "Cuidadores",
         DOCENTE: "Docentes"}
# Columna que identifica a la unidad que cuenta para el mínimo de 10. En
# estudiantes y docentes cada fila es una persona; en cuidadores (también en
# el marco de niños) cuenta el cuidador distinto (spec §4).
UNIDAD = {ESTUDIANTE: None, CUIDADOR: "ID_cuidador", NINO: "ID_cuidador", DOCENTE: None}
MARCOS_GRADO = (ESTUDIANTE, CUIDADOR, NINO)       # los docentes no tienen grado

# ── Objetos y clasificación ─────────────────────────────────────────────────
MISMO_OBJETO, COOCURRENCIA = "mismo_objeto", "co-ocurrencia"
COINCIDENCIA, TENSION, SIN_DIFERENCIA, SIN_DATO = (
    "coincidencia", "tensión", "sin diferencia clara", "sin dato")


@dataclass(frozen=True)
class Constructo:
    clave: str
    marco: str
    columna: str
    etiqueta: str
    objeto: str
    direccion: int           # +1: más es mejor (protector); −1: más es peor (riesgo)
    binario: bool = False    # 0/1 por persona: se muestra como %


CONSTRUCTOS: tuple[Constructo, ...] = (
    Constructo("est_sdq_total", ESTUDIANTE, "SDQ_Total",
               "Dificultades del niño, según él (SDQ autoinforme)", "conducta_total", -1),
    Constructo("est_sdq_emo", ESTUDIANTE, "SDQ_Emo",
               "Síntomas emocionales, según el niño (SDQ autoinforme)", "conducta_emo", -1),
    Constructo("est_pssm", ESTUDIANTE, "PSSM_Total",
               "Pertenencia al colegio (PSSM)", "clima_escolar", +1),
    Constructo("est_sin_adulto", ESTUDIANTE, "SIN_ADULTO",
               "Sin un adulto de confianza en el colegio (PSSM 7)", "clima_escolar", -1,
               binario=True),
    Constructo("est_malestar", ESTUDIANTE, "ALERTA_malestar",
               "Señal de malestar del niño (6 ítems del SDQ)", "malestar_nino", -1,
               binario=True),
    Constructo("est_mspss_fam", ESTUDIANTE, "MSPSS_Fam",
               "Apoyo de la familia que siente el niño (MSPSS)", "apoyo_familia", +1),
    Constructo("nin_sdq_total", NINO, "SDQ_Total",
               "Dificultades del niño, según su cuidador (SDQ padres)", "conducta_total", -1),
    Constructo("nin_sdq_emo", NINO, "SDQ_Emo",
               "Síntomas emocionales, según su cuidador (SDQ padres)", "conducta_emo", -1),
    Constructo("cui_pss", CUIDADOR, "PSS_Total", "Estrés percibido del cuidador (PSS-10)",
               "estres", -1),
    Constructo("cui_epds", CUIDADOR, "EPDS_Total", "Ánimo del cuidador (EPDS-10)",
               "animo_adulto", -1),
    Constructo("cui_fisico", CUIDADOR, "APQ_Fisico",
               "Usa alguna forma de castigo físico, a veces o más (APQ 22–24)", "crianza", -1,
               binario=True),
    Constructo("cui_barrio", CUIDADOR, "BARRIO_Indice", "Riesgo del barrio (0–10)", "barrio",
               -1),
    Constructo("cui_mspss_fam", CUIDADOR, "MSPSS_Fam",
               "Apoyo de la familia que siente el cuidador (MSPSS)", "apoyo_familia", +1),
    Constructo("doc_pss", DOCENTE, "DOC_PSS", "Estrés percibido del docente (PSS-10)",
               "estres", -1),
    Constructo("doc_lider", DOCENTE, "DOC_LIDER",
               "Clima laboral: apoyo del líder (HSE, 7 ítems)", "clima_escolar", +1),
    Constructo("doc_grupo", DOCENTE, "DOC_GRUPO",
               "Apoyo percibido de los compañeros (HSE, 3 ítems)", "clima_escolar", +1),
    Constructo("doc_desgaste", DOCENTE, "DOC_DESGASTE",
               "Desgaste del docente (4 ítems, 1–7)", "desgaste", -1),
)
POR_CLAVE = {c.clave: c for c in CONSTRUCTOS}


@dataclass(frozen=True)
class Par:
    a: str
    b: str
    tipo: str              # MISMO_OBJETO | COOCURRENCIA
    titulo: str


PARES: tuple[Par, ...] = (
    Par("est_sdq_total", "nin_sdq_total", MISMO_OBJETO,
        "Conducta del niño: dificultades, según él y según su cuidador"),
    Par("est_sdq_emo", "nin_sdq_emo", MISMO_OBJETO,
        "Conducta del niño: síntomas emocionales, según él y según su cuidador"),
    Par("est_pssm", "doc_lider", MISMO_OBJETO,
        "Clima escolar: pertenencia (estudiantes) y apoyo del líder (docentes)"),
    Par("est_pssm", "doc_grupo", MISMO_OBJETO,
        "Clima escolar: pertenencia (estudiantes) y apoyo de compañeros (docentes)"),
    Par("est_sin_adulto", "doc_lider", MISMO_OBJETO,
        "Clima escolar: adulto de confianza (estudiantes) y apoyo del líder (docentes)"),
    Par("est_sin_adulto", "doc_grupo", MISMO_OBJETO,
        "Clima escolar: adulto de confianza (estudiantes) y apoyo de compañeros (docentes)"),
    Par("cui_pss", "doc_pss", COOCURRENCIA,
        "Estrés (PSS-10): cuidadores y docentes, la misma escala en personas distintas"),
    Par("est_malestar", "cui_epds", COOCURRENCIA,
        "Malestar del niño y ánimo del cuidador"),
    Par("est_malestar", "doc_desgaste", COOCURRENCIA,
        "Malestar del niño y desgaste docente"),
    Par("est_mspss_fam", "cui_mspss_fam", COOCURRENCIA,
        "Apoyo de la familia: el que siente el niño y el que siente el cuidador"),
)

# ── Díadas (capa 2) ────────────────────────────────────────────────────────
SUBESCALAS_SDQ = ("SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro")
FUENTES_MSPSS = (("MSPSS_Fam", "Familia"), ("MSPSS_Amigos", "Amigos"),
                 ("MSPSS_Otro", "Una persona especial"))
RESULTADOS = (("SDQ_Total", "Dificultades (SDQ autoinforme)"),
              ("SDQ_Int", "Internalizante (SDQ autoinforme)"),
              ("SDQ_Ext", "Externalizante (SDQ autoinforme)"))
PREDICTORES = (("EPDS_Total", "Ánimo del cuidador (EPDS, z)", False),
               ("PSS_Total", "Estrés del cuidador (PSS, z)", False),
               ("APQ_Fisico", "Castigo físico a veces o más (sí = 1)", True),
               ("BARRIO_Indice", "Riesgo del barrio (z)", False))
# «Malestar que el cuidador no ve»: (variante, subescala, ¿suma la señal de malestar?)
VARIANTES_NO_VISTO = (("Dificultades totales o señal de malestar (vigente)", "SDQ_Total", True),
                      ("Síntomas emocionales o señal de malestar (sensibilidad)", "SDQ_Emo",
                       True))
MAX_BINES_BA = 5

# ── Avisos fijos ────────────────────────────────────────────────────────────
TITULO = "Triangulación 360 · solo investigadores"
AVISO_ECOLOGICO = ("Con {n} colegios esto es descriptivo y ecológico: compara promedios de "
                   "grupo, no personas, y no permite concluir relaciones individuales ni "
                   "causales. Cada actor se compara con el resto del municipio del mismo "
                   "actor, en unidades de su desviación estándar individual.")
AVISO_RESTO = ("«Resto del municipio» = los demás colegios reconocidos de ese actor. Si los "
               "colegios que no entran en la comparación suman entre 1 y 9 personas con dato "
               "en un constructo, se excluyen de ese constructo (no pueden deducirse "
               "restando).")
AVISO_GRADO = ("Por grado solo se comparan estudiantes y cuidadores: los docentes no "
               "tienen grado.")
AVISO_COOCURRENCIA = ("«Co-ocurrencia»: dos cifras que se describen lado a lado sin llamarlas "
                      "acuerdo, porque no miden lo mismo o miden a personas distintas (la PSS "
                      "es la misma escala en cuidadores y docentes, pero son otras personas).")
AVISO_CLASIFICACION = ("«Tensión»: los intervalos de los dos actores excluyen el cero en "
                       "direcciones opuestas. «Coincidencia»: lo excluyen en la misma "
                       "dirección. En otro caso, «sin diferencia clara». Con muchas "
                       "comparaciones, alguna puede deberse al azar.")
AVISO_DESPLIEGUE = ("La triangulación solo funciona en la máquina que procesa los "
                    "formularios (estudiantes, cuidadores y docentes). En el despliegue del "
                    "equipo, la capa por colegio necesitará los agregados publicados de "
                    "cuidadores, que llegan con la fase 4b; las díadas nunca salen de la "
                    "máquina local.")
AVISO_ENLACE = ("Enlace exacto: el seudónimo HMAC del nombre normalizado del niño, calculado "
                "con la misma clave local en los dos formularios, y verificado con el "
                "colegio. No hay coincidencias aproximadas: un nombre escrito distinto no "
                "enlaza. Los seudónimos no se guardan ni se muestran.")
AVISO_DIADAS = ("Las díadas solo existen en esta máquina. Toda cifra exige 10 o más díadas de "
                "10 o más familias distintas; ninguna salida muestra una díada.")
AVISO_SDQ = ("Cada informante se lee con sus propias bandas: autoinforme para el niño y "
             "versión para padres para el cuidador (sdqinfo.org). " + cat_est.AVISO_PRIMARIA)
AVISO_MSPSS = cat_cuid.AVISO_MSPSS
AVISO_ASOCIACIONES = ("Regresión lineal con efecto fijo de colegio, controles de sexo y edad "
                      "del niño y errores agrupados por familia (cuidador). Con 4 colegios no "
                      "se usan errores agrupados por colegio; la sensibilidad repite el "
                      "análisis solo con Laura Vicuña. Son asociaciones, no efectos causales.")
AVISO_BLAND_ALTMAN = ("Bland–Altman agrupado: cada punto es el promedio de un grupo de 10 o "
                      "más díadas (quintiles del promedio de los dos informantes); no se "
                      "dibuja ninguna díada.")
AVISO_TEXTOS = ("Textos provisionales: el equipo los revisa antes de usarlos fuera de esta "
                "vista.")
```

`src/triangulacion/estadistica.py`:

```python
"""
Estadística de la triangulación — funciones puras con numpy y scipy.

No hay `statsmodels` en `requirements.txt` y no se añade: lo que hace falta
cabe en numpy/scipy y en `estudiantes.stats.ols_cluster` (MCO con errores
agrupados CR1 y gl = G − 1), que ya usa estudiantes.

  · `icc_a1`: CCI(A,1) de McGraw y Wong (1996) = CCI(2,1) de Shrout y Fleiss
    (1979): dos vías, efectos aleatorios, acuerdo absoluto, medida única.
  · `kappa_ponderado`: kappa de Cohen (1968) con pesos lineales.
  · `bland_altman`: diferencia media y límites de acuerdo (± 1,96 DE).
  · `media_agrupada`: media con IC por errores agrupados (familia).
  · `correlacion_ic`: Spearman o Pearson con IC de Fisher.
  · `bootstrap_ic`: IC percentil remuestreando conglomerados (familias).
  · `ols_agrupado`: MCO con efectos fijos y errores agrupados.
  · `partes_seguras` y `suficiente`: las reglas de cifras pequeñas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from src.estudiantes import stats as stats_est
from src.triangulacion import catalogo as cat

Z95 = 1.959963984540054


def icc_a1(Y) -> float:
    """CCI(A,1) sobre una matriz n × k (filas con faltantes se quitan)."""
    Y = np.asarray(Y, dtype=float)
    Y = Y[~np.isnan(Y).any(axis=1)]
    n, k = Y.shape if Y.ndim == 2 else (0, 0)
    if n < 2 or k < 2:
        return float("nan")
    g = Y.mean()
    ssr = k * ((Y.mean(axis=1) - g) ** 2).sum()
    ssc = n * ((Y.mean(axis=0) - g) ** 2).sum()
    sse = ((Y - g) ** 2).sum() - ssr - ssc
    msr, msc = ssr / (n - 1), ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    den = msr + (k - 1) * mse + k * (msc - mse) / n
    return float((msr - mse) / den) if den > 0 else float("nan")


def kappa_ponderado(a, b, k: int = 4) -> float:
    """Kappa ponderado lineal entre dos clasificaciones ordinales 0..k−1."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok].astype(int), b[ok].astype(int)
    if len(a) == 0:
        return float("nan")
    O = np.zeros((k, k))
    np.add.at(O, (a, b), 1)
    O /= O.sum()
    E = np.outer(O.sum(axis=1), O.sum(axis=0))
    i, j = np.indices((k, k))
    W = np.abs(i - j) / (k - 1)
    den = (W * E).sum()
    return float(1 - (W * O).sum() / den) if den > 0 else float("nan")


def bland_altman(a, b) -> dict:
    """Diferencia media (a − b), su DE y los límites de acuerdo del 95 %."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    dif = a[ok] - b[ok]
    if len(dif) < 2:
        return dict(n=len(dif), dif_media=float("nan"), de_dif=float("nan"),
                    lim_inf=float("nan"), lim_sup=float("nan"))
    m, s = float(dif.mean()), float(dif.std(ddof=1))
    return dict(n=len(dif), dif_media=m, de_dif=s, lim_inf=m - Z95 * s, lim_sup=m + Z95 * s)


def media_agrupada(y, grupos) -> dict:
    """Media con IC del 95 % por errores agrupados (t con G − 1 gl)."""
    y = np.asarray(y, dtype=float)
    grupos = np.asarray(grupos)
    ok = ~np.isnan(y)
    y, grupos = y[ok], grupos[ok]
    if len(y) < 2:
        return dict(m=float("nan"), se=float("nan"), ic_inf=float("nan"),
                    ic_sup=float("nan"), G=len(set(grupos)))
    b, se, _, _, G = stats_est.ols_cluster(y, np.empty((len(y), 0)), grupos)
    t = sps.t.ppf(0.975, max(G - 1, 1))
    return dict(m=float(b[0]), se=float(se[0]), ic_inf=float(b[0] - t * se[0]),
                ic_sup=float(b[0] + t * se[0]), G=int(G))


def correlacion_ic(a, b, metodo: str = "spearman") -> tuple[float, float, float, float]:
    """(r, IC inferior, IC superior, p) con la transformación de Fisher."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    n = len(a)
    if n < 4 or np.std(a) == 0 or np.std(b) == 0:
        return (float("nan"),) * 4
    res = sps.spearmanr(a, b) if metodo == "spearman" else sps.pearsonr(a, b)
    r = float(res.statistic)
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    se = 1 / np.sqrt(n - 3)
    return r, float(np.tanh(z - Z95 * se)), float(np.tanh(z + Z95 * se)), float(res.pvalue)


def bootstrap_ic(df: pd.DataFrame, estadistico, grupo: str, n_boot: int = cat.N_BOOT,
                 semilla: int = cat.SEMILLA) -> tuple[float, float]:
    """IC percentil del 95 % remuestreando conglomerados enteros (familias)."""
    if df.empty or n_boot <= 0:
        return float("nan"), float("nan")
    posiciones = [np.asarray(v) for v in df.groupby(grupo, sort=True).indices.values()]
    rng = np.random.default_rng(semilla)
    valores = []
    for _ in range(n_boot):
        elegidos = rng.integers(0, len(posiciones), len(posiciones))
        idx = np.concatenate([posiciones[e] for e in elegidos])
        valores.append(estadistico(df.iloc[idx]))
    valores = np.asarray(valores, dtype=float)
    valores = valores[~np.isnan(valores)]
    if len(valores) < max(10, n_boot // 2):
        return float("nan"), float("nan")
    return float(np.percentile(valores, 2.5)), float(np.percentile(valores, 97.5))


def ols_agrupado(y: pd.Series, X: pd.DataFrame, grupos: pd.Series,
                 efectos_fijos: pd.Series | None = None) -> pd.DataFrame:
    """MCO con efectos fijos (variables indicadoras) y errores agrupados.

    Devuelve una fila por columna de `X` (no por las indicadoras ni la
    constante): beta, se, IC del 95 % y p con t de G − 1 gl.
    """
    Xf = X.astype(float)
    if efectos_fijos is not None and efectos_fijos.nunique() > 1:
        ind = pd.get_dummies(efectos_fijos.astype(str), prefix="_ef", drop_first=True,
                             dtype=float)
        Xf = pd.concat([Xf, ind], axis=1)
    b, se, p, r2, G = stats_est.ols_cluster(np.asarray(y, dtype=float), Xf.to_numpy(),
                                            np.asarray(grupos))
    t = sps.t.ppf(0.975, max(G - 1, 1))
    filas = []
    for i, nombre in enumerate(X.columns, start=1):
        filas.append(dict(predictor=nombre, beta=float(b[i]), se=float(se[i]),
                          ic_inf=float(b[i] - t * se[i]), ic_sup=float(b[i] + t * se[i]),
                          p=float(p[i]), R2=float(r2), G=int(G)))
    return pd.DataFrame(filas)


def suficiente(df: pd.DataFrame, unidad: str | None, minimo: int = cat.MIN_GROUP_N) -> bool:
    """≥ `minimo` filas y ≥ `minimo` unidades distintas (familias, cuidadores)."""
    if len(df) < minimo:
        return False
    return unidad is None or df[unidad].nunique() >= minimo


def partes_seguras(etiquetas: pd.Series, unidades: pd.Series | None, categorias,
                   minimo: int = cat.MIN_CASOS) -> bool:
    """Cada categoría y su complemento tienen ≥ `minimo` filas y unidades distintas.

    Es la regla 3 ≤ k ≤ n − 3 de `estudiantes.supresion` sobre un reparto en
    varias partes (todo o nada), contando además unidades distintas: tres
    hermanos de una misma familia no son tres casos.
    """
    etiquetas = pd.Series(etiquetas)
    if etiquetas.empty:
        return False
    for c in categorias:
        dentro = etiquetas == c
        for parte in (dentro, ~dentro):
            if int(parte.sum()) < minimo:
                return False
            if unidades is not None and pd.Series(unidades)[parte.to_numpy()].nunique() < minimo:
                return False
    return True
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_triangulacion_estadistica.py -q`
Expected: `14 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/triangulacion/__init__.py src/triangulacion/catalogo.py \
        src/triangulacion/estadistica.py tests/test_triangulacion_estadistica.py
git commit -m "feat(triangulacion): catálogo de constructos y estadística con numpy/scipy" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Carga local de los tres actores

**Files:**
- Create: `src/triangulacion/fuentes.py`
- Create: `tests/test_triangulacion_fuentes.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_triangulacion_fuentes.py` (usa `_crudo` de `tests/test_preparar_docentes.py`, la exportación cruda sintética de docentes):

```python
"""Triangulación · carga local de los tres actores (sintéticos)."""
import numpy as np
import pandas as pd
import pytest

from src.triangulacion import fuentes as fu
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_fuentes"))
    return base


def test_localizar_encuentra_los_tres(datos, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    disp = fu.localizar()
    assert disp.completo and len(disp.estudiantes) == 2
    assert disp.docentes.endswith(ts.ARCHIVO_DOC)
    assert len(disp.firma()) == 4


def test_sin_archivos_no_esta_completo(tmp_path, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    disp = fu.localizar()
    assert not disp.completo
    assert disp.presentes() == {"Estudiantes": False, "Cuidadores": False, "Docentes": False}
    with pytest.raises(FileNotFoundError):
        fu.cargar(disp, k=K)


def test_docentes_prefiere_el_codificado(tmp_path):
    (tmp_path / "360 - Profesores (respuestas).xlsx").write_bytes(b"x")
    (tmp_path / "Docentes_codificado.xlsx").write_bytes(b"x")
    assert fu.localizar_docentes(str(tmp_path)).endswith("Docentes_codificado.xlsx")


def test_puntuar_docentes():
    d = ts.docentes()
    p = fu.puntuar_docentes(d)
    assert list(p.columns) == ["Colegio", "DOC_PSS", "DOC_LIDER", "DOC_GRUPO", "DOC_DESGASTE"]
    assert p["Colegio"].value_counts().to_dict() == {
        "LauV": 15, "JJC": 12, "SJMEB": 11, "LaBalsa": 10, "CdP": 5, "OTRO": 2}
    pss = d[[f"PSS{i}" for i in range(1, 11)]].sum(axis=1)
    assert np.allclose(p["DOC_PSS"], pss)
    assert p["DOC_LIDER"].between(0, 5).all() and p["DOC_DESGASTE"].between(1, 7).all()


def test_pss_docente_prorratea_con_nueve_items():
    d = ts.docentes().head(2).copy()
    d.loc[0, "PSS1"] = np.nan
    d.loc[1, ["PSS1", "PSS2"]] = np.nan
    p = fu.puntuar_docentes(d)
    nueve = d.loc[0, [f"PSS{i}" for i in range(2, 11)]].sum() * 10 / 9
    assert p.loc[0, "DOC_PSS"] == pytest.approx(nueve)
    assert np.isnan(p.loc[1, "DOC_PSS"])


def test_docentes_crudos_se_codifican_en_memoria_sin_nombres():
    from tests.test_preparar_docentes import _crudo
    crudo = _crudo()
    codificado = fu.leer_docentes(crudo)
    assert fu.es_docentes_codificado(codificado)
    assert "Nombre" not in codificado.columns
    p = fu.puntuar_docentes(codificado)
    assert "SMR" in set(p["Colegio"]) and "CND" in set(p["Colegio"])


def test_estudiantes_puntuados_con_senales_y_sin_id(datos, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    e = fu.cargar_estudiantes(fu.localizar().estudiantes, K)
    assert "ID" not in e.columns and e[fu.COLUMNA_NINO].notna().all()
    for c in ("SDQ_Total", "PSSM_Total", "MSPSS_Fam", "ALERTA_malestar", "SIN_ADULTO"):
        assert c in e.columns
    assert set(e["SIN_ADULTO"].dropna().unique()) <= {0.0, 1.0}
    assert e.loc[e["PSSM7"] <= 2, "SIN_ADULTO"].eq(1).all()


def test_modulo_rancio_pide_reiniciar(monkeypatch):
    from src.estudiantes import ingest

    def viejo(rutas, niveles=None):
        raise AssertionError("no debía llamarse")
    monkeypatch.setattr(ingest, "cargar_varios", viejo)
    with pytest.raises(fu.ModuloRancio, match="Reinicie"):
        fu.cargar_estudiantes(["x.xlsx"], K)


def test_cargar_los_tres(datos, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    f = fu.cargar(k=K)
    assert len(f.docentes) == sum(n for _, n in ts.DOCENTES)
    assert f.cuidadores["ID_cuidador"].is_unique and f.ninos["ID_nino"].is_unique
    assert "EPDS_Total" in f.cuidadores.columns and "SDQ_Total" in f.ninos.columns
    assert isinstance(f.marco("docente"), pd.DataFrame)
```

Run: `.venv/bin/python -m pytest tests/test_triangulacion_fuentes.py -q`
Expected: FAIL con `ImportError: cannot import name 'fuentes' from 'src.triangulacion'`.

- [ ] **Step 2: Implementar**

`src/triangulacion/fuentes.py`:

```python
"""
Carga local de los tres actores para la triangulación — Observatorio 360.

  · Estudiantes: los dos formularios con `estudiantes.ingest.cargar_varios`,
    pidiendo el seudónimo del niño con la clave local (`clave_nino`), y su
    puntuación (`scoring.puntuar`, señales de `alertas.marcar` por nivel y
    «sin adulto de confianza», PSSM 7 ≤ 2). La columna `ID` (SHA-1 sin clave)
    se quita: la triangulación solo usa el seudónimo con clave.
  · Cuidadores: `cuidadores.ingest` (seudónimos «C…» y «N…»), deduplicados y
    puntuados en sus dos marcos (cuidador y niño), igual que la fase 4a.
  · Docentes: el archivo codificado por `scripts/preparar_docentes.py` (sin
    nombres). Si solo está la exportación cruda, se codifica en memoria con
    `preparar`, que descarta el nombre. El colegio se une con
    `core.colegios.codigo_desde_nombre`.

PRIVACIDAD: nada de aquí se escribe en disco ni se muestra. Los seudónimos
viven solo en memoria, para enlazar; `pipeline.Triangulacion` solo guarda
agregados.
"""
from __future__ import annotations

import inspect
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.colegios import codigo_desde_nombre
from src.core.texto import norm_txt
from src.triangulacion import catalogo as cat

EXTENSIONES = (".xlsx", ".xls", ".csv")
# Se prefiere el archivo ya codificado (sin nombres); si no, la exportación cruda.
PATRONES_DOCENTES = ("codificado", "profesores")
COLUMNA_NINO = "N_hmac"          # = estudiantes.ingest.COLUMNA_NINO

ITEMS_DOCENTES = {
    "DOC_PSS": [f"PSS{i}" for i in range(1, 11)],
    "DOC_LIDER": [f"CL{i}" for i in range(1, 8)],
    "DOC_GRUPO": [f"AP{i}" for i in range(1, 4)],
    "DOC_DESGASTE": [f"BLG_Desg{i}" for i in range(1, 5)],
}
PSS_MIN_ITEMS = 9

MENSAJE_RANCIO = ("La aplicación tiene en memoria una versión anterior de la carga de "
                  "estudiantes, sin el seudónimo del niño. Reinicie la aplicación (en "
                  "Streamlit Cloud, «Reboot app») y vuelva a abrir Triangulación 360.")


class ModuloRancio(RuntimeError):
    """Un módulo existente quedó viejo en memoria y no tiene lo que esta fase necesita."""


@dataclass
class Disponibles:
    estudiantes: list
    cuidadores: str | None
    docentes: str | None

    @property
    def completo(self) -> bool:
        return bool(self.estudiantes) and bool(self.cuidadores) and bool(self.docentes)

    def firma(self) -> tuple:
        rutas = list(self.estudiantes) + [self.cuidadores, self.docentes]
        return tuple((r, os.path.getmtime(r)) for r in rutas if r)

    def presentes(self) -> dict:
        return {"Estudiantes": bool(self.estudiantes), "Cuidadores": bool(self.cuidadores),
                "Docentes": bool(self.docentes)}


@dataclass
class Fuentes:
    estudiantes: pd.DataFrame
    cuidadores: pd.DataFrame
    ninos: pd.DataFrame
    docentes: pd.DataFrame
    informe_cuidadores: object = None

    def marco(self, nombre: str) -> pd.DataFrame:
        return {cat.ESTUDIANTE: self.estudiantes, cat.CUIDADOR: self.cuidadores,
                cat.NINO: self.ninos, cat.DOCENTE: self.docentes}[nombre]


# ── localizar ───────────────────────────────────────────────────────────────
def localizar_docentes(base: str | None = None) -> str | None:
    from src.core.rutas import carpeta_datos
    base = base or carpeta_datos("docentes")
    if not os.path.isdir(base):
        return None
    archivos = [f for f in os.listdir(base)
                if f.lower().endswith(EXTENSIONES) and not f.startswith("~$")]
    for patron in PATRONES_DOCENTES:
        candidatos = [os.path.join(base, f) for f in archivos if patron in norm_txt(f)]
        if candidatos:
            return max(candidatos, key=os.path.getmtime)
    return None


def localizar() -> Disponibles:
    from src.cuidadores.pipeline import localizar_formulario
    from src.estudiantes.pipeline import localizar_formularios
    return Disponibles(estudiantes=localizar_formularios(), cuidadores=localizar_formulario(),
                       docentes=localizar_docentes())


# ── docentes ────────────────────────────────────────────────────────────────
def es_docentes_codificado(df: pd.DataFrame) -> bool:
    necesarias = {"Colegio"} | {c for cols in ITEMS_DOCENTES.values() for c in cols}
    return necesarias <= set(df.columns)


def leer_docentes(fuente) -> pd.DataFrame:
    """El archivo codificado de docentes; la exportación cruda se codifica en memoria."""
    if isinstance(fuente, pd.DataFrame):
        raw = fuente
    else:
        ruta = str(fuente)
        raw = (pd.read_excel(ruta) if ruta.lower().endswith((".xlsx", ".xls"))
               else pd.read_csv(ruta))
    if es_docentes_codificado(raw):
        return raw
    from scripts.preparar_docentes import preparar
    codificado, _ = preparar(raw)
    return codificado


def _suma_prorrateada(X: pd.DataFrame, minimo: int) -> pd.Series:
    respondidos = X.notna().sum(axis=1)
    s = X.sum(axis=1) * X.shape[1] / respondidos.replace(0, np.nan)
    return s.mask(respondidos < minimo)


def puntuar_docentes(d: pd.DataFrame) -> pd.DataFrame:
    """Colegio (código) y los cuatro constructos docentes. Nada más sale de aquí.

    PSS-10: los ítems 3, 4, 5, 7 y 9 ya vienen invertidos por `preparar`; suma
    0–40 prorrateada con 9 de 10 (igual que cuidadores). Apoyo del líder (CL,
    0–5), apoyo de compañeros (AP, 0–5) y desgaste (BLG_Desg, 1–7): media con
    todos sus ítems.
    """
    out = pd.DataFrame(index=d.index)
    out["Colegio"] = d["Colegio"].map(codigo_desde_nombre)
    items = {k: d[cols].apply(pd.to_numeric, errors="coerce") for k, cols in ITEMS_DOCENTES.items()}
    out["DOC_PSS"] = _suma_prorrateada(items["DOC_PSS"], PSS_MIN_ITEMS)
    for clave in ("DOC_LIDER", "DOC_GRUPO", "DOC_DESGASTE"):
        X = items[clave]
        out[clave] = X.mean(axis=1).mask(X.isna().any(axis=1))
    return out.reset_index(drop=True)


# ── estudiantes ─────────────────────────────────────────────────────────────
def preparar_estudiantes(bruto: pd.DataFrame) -> pd.DataFrame:
    """Puntuaciones, señales de alerta por nivel y «sin adulto de confianza»."""
    from src.estudiantes import alertas, scoring
    from src.estudiantes import catalog as cat_est
    p = scoring.puntuar(bruto)
    partes = [alertas.marcar(p[p["nivel"] == nivel], nivel)
              for nivel in p["nivel"].dropna().unique()]
    d = pd.concat(partes).sort_index() if partes else p
    col = f"PSSM{cat_est.PSSM_ITEM_ADULTO}"
    if col in d.columns:
        d["SIN_ADULTO"] = (d[col] <= 2).astype(float).where(d[col].notna())
    return d.drop(columns=[c for c in ("ID",) if c in d.columns]).reset_index(drop=True)


def cargar_estudiantes(rutas: list, k: bytes) -> pd.DataFrame:
    from src.estudiantes import ingest
    if "clave_nino" not in inspect.signature(ingest.cargar_varios).parameters:
        raise ModuloRancio(MENSAJE_RANCIO)
    bruto, _ = ingest.cargar_varios(rutas, clave_nino=k)
    return preparar_estudiantes(bruto)


# ── cuidadores ──────────────────────────────────────────────────────────────
def cargar_cuidadores(fuente, k: bytes) -> tuple[pd.DataFrame, pd.DataFrame, object]:
    from src.cuidadores import ingest, scoring
    cuid, ninos, informe = ingest.deduplicar(ingest.cargar(fuente, k=k))
    return scoring.puntuar_cuidadores(cuid), scoring.puntuar_ninos(ninos), informe


def cargar(disp: Disponibles | None = None, k: bytes | None = None) -> Fuentes:
    """Los tres actores desde los archivos locales. Sin la clave, `ClaveAusente`."""
    from src.core import seudonimo
    disp = disp or localizar()
    if not disp.completo:
        raise FileNotFoundError(cat.AVISO_DESPLIEGUE)
    k = seudonimo.clave() if k is None else k
    estudiantes = cargar_estudiantes(disp.estudiantes, k)
    cuidadores, ninos, informe = cargar_cuidadores(disp.cuidadores, k)
    docentes = puntuar_docentes(leer_docentes(disp.docentes))
    return Fuentes(estudiantes=estudiantes, cuidadores=cuidadores, ninos=ninos,
                   docentes=docentes, informe_cuidadores=informe)
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_triangulacion_fuentes.py -q`
Expected: `9 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/triangulacion/fuentes.py tests/test_triangulacion_fuentes.py
git commit -m "feat(triangulacion): carga local de estudiantes, cuidadores y docentes" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Capa 1 por colegio y por grado

**Files:**
- Create: `src/triangulacion/capa1.py`
- Create: `tests/test_triangulacion_capa1.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_triangulacion_capa1.py`:

```python
"""Triangulación · capa 1 por colegio y por grado."""
import numpy as np
import pandas as pd
import pytest

from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import fuentes as fu
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def fuentes_sint(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_capa1"))
    mp = pytest.MonkeyPatch()
    mp.setenv("OBS360_DATOS_DIR", base)
    try:
        yield fu.cargar(k=K)
    finally:
        mp.undo()


@pytest.fixture(scope="module")
def capa(fuentes_sint):
    return c1.analizar(fuentes_sint)


def _fila(clave, d, lo, hi):
    return pd.Series(dict(clave=clave, d=d, ic_inf=lo, ic_sup=hi))


def test_clasificacion_mismo_objeto():
    par = next(p for p in cat.PARES if p.a == "est_pssm" and p.b == "doc_lider")
    # pertenencia (+) más alta y apoyo del líder (+) más alto: coincidencia
    assert c1.clasificar(par, _fila("est_pssm", .4, .1, .7),
                         _fila("doc_lider", .5, .2, .8)) == cat.COINCIDENCIA
    assert c1.clasificar(par, _fila("est_pssm", .4, .1, .7),
                         _fila("doc_lider", -.5, -.8, -.2)) == cat.TENSION
    assert c1.clasificar(par, _fila("est_pssm", .4, -.1, .7),
                         _fila("doc_lider", -.5, -.8, -.2)) == cat.SIN_DIFERENCIA
    assert c1.clasificar(par, None, _fila("doc_lider", .5, .2, .8)) == cat.SIN_DATO


def test_la_orientacion_respeta_la_direccion():
    """«Sin adulto» (riesgo) más alto y apoyo del líder (protector) más bajo: coinciden."""
    par = next(p for p in cat.PARES if p.a == "est_sin_adulto" and p.b == "doc_lider")
    assert c1.clasificar(par, _fila("est_sin_adulto", .4, .1, .7),
                         _fila("doc_lider", -.5, -.8, -.2)) == cat.COINCIDENCIA


def test_coocurrencia_nunca_es_acuerdo():
    par = next(p for p in cat.PARES if p.a == "cui_pss" and p.b == "doc_pss")
    assert par.tipo == cat.COOCURRENCIA
    assert c1.clasificar(par, _fila("cui_pss", .4, .1, .7),
                         _fila("doc_pss", .5, .2, .8)) == cat.COOCURRENCIA


def test_pares_de_mismo_objeto_son_los_de_la_spec():
    mismos = {(p.a, p.b) for p in cat.PARES if p.tipo == cat.MISMO_OBJETO}
    assert mismos == {("est_sdq_total", "nin_sdq_total"), ("est_sdq_emo", "nin_sdq_emo"),
                      ("est_pssm", "doc_lider"), ("est_pssm", "doc_grupo"),
                      ("est_sin_adulto", "doc_lider"), ("est_sin_adulto", "doc_grupo")}


def _docentes(conteos: dict, valor=lambda i: float(i % 5)) -> pd.DataFrame:
    filas = [dict(Colegio=c, DOC_PSS=valor(i)) for c, n in conteos.items() for i in range(n)]
    return pd.DataFrame(filas)


def test_el_resto_con_1_a_9_sale_del_constructo():
    d = _docentes({"A": 12, "B": 15, "C": 4})
    atomos = c1.atomos(d, cat.DOCENTE)
    assert [a.nombre for a in atomos] == ["A", "B"]          # C (4) no es átomo ni resto
    c = cat.POR_CLAVE["doc_pss"]
    filas = c1.diferencias_constructo(d, atomos, c, ["A", "B"], "Colegio")
    assert [f["n_grupo"] for f in filas] == [12, 15]
    assert [f["n_resto"] for f in filas] == [15, 12]          # el resto no incluye a C


def test_el_resto_con_10_o_mas_de_dos_colegios_entra():
    d = _docentes({"A": 12, "B": 15, "C": 6, "D": 6})
    assert [a.nombre for a in c1.atomos(d, cat.DOCENTE)][-1] == c1.RESTO


def test_un_grupo_con_menos_de_10_con_dato_no_se_muestra():
    d = _docentes({"A": 12, "B": 15})
    d.loc[d.index[:5], "DOC_PSS"] = np.nan                     # A queda con 7 con dato
    c = cat.POR_CLAVE["doc_pss"]
    filas = c1.diferencias_constructo(d, c1.atomos(d, cat.DOCENTE), c, ["A", "B"], "Colegio")
    assert np.isnan(filas[0]["d"]) and filas[0]["motivo"] == c1.MOTIVO_POCOS
    assert filas[1]["motivo"] == c1.MOTIVO_RESTO               # su resto sería A (7)


def test_binario_con_menos_de_3_casos_no_se_muestra():
    filas = []
    for colegio, casos in (("A", 2), ("B", 6), ("C", 5)):
        for i in range(12):
            filas.append(dict(Colegio=colegio, Grado="Sexto", SIN_ADULTO=float(i < casos)))
    d = pd.DataFrame(filas)
    c = cat.POR_CLAVE["est_sin_adulto"]
    res = c1.diferencias_constructo(d, c1.atomos(d, cat.ESTUDIANTE), c, ["A", "B", "C"],
                                    "Colegio")
    assert np.isnan(res[0]["d"])
    assert res[1]["media_grupo"] == pytest.approx(50.0)        # % con 1 decimal
    assert res[1]["n_resto"] == 12                             # el resto de B es solo C


def test_diferencia_estandarizada_e_ic():
    d = _docentes({"A": 10, "B": 10}, valor=lambda i: float(i))
    d.loc[d["Colegio"] == "A", "DOC_PSS"] += 5
    c = cat.POR_CLAVE["doc_pss"]
    f = c1.diferencias_constructo(d, c1.atomos(d, cat.DOCENTE), c, ["A"], "Colegio")[0]
    x, y = d.loc[d.Colegio == "A", "DOC_PSS"], d.loc[d.Colegio == "B", "DOC_PSS"]
    de = d["DOC_PSS"].std(ddof=1)
    se = np.sqrt(x.var() / 10 + y.var() / 10) / de
    assert f["d"] == pytest.approx(round(5 / de, 3))
    assert f["ic_inf"] == pytest.approx(round(5 / de - 1.959964 * se, 3), abs=1e-3)
    assert f["d_orientada"] == pytest.approx(-f["d"])          # PSS: más es peor


def test_colegios_y_grados_sinteticos(capa):
    # La Balsa no tiene cuidadores con hijos en los grados del estudio.
    assert capa.colegios == ["JJC", "LauV", "SJMEB"]
    assert capa.grados and set(capa.grados) <= {"Cuarto", "Quinto", "Sexto", "Séptimo",
                                                 "Octavo", "Noveno", "Décimo"}
    assert set(capa.diferencias["grupo"]) == set(capa.colegios)


def test_por_grado_solo_estudiantes_y_cuidadores(capa):
    assert set(capa.por_grado["actor"]) <= {"Estudiantes", "Cuidadores"}
    assert not capa.por_grado["clave"].str.startswith("doc_").any()


def test_toda_cifra_mostrada_tiene_10_o_mas(capa):
    for t in (capa.diferencias, capa.por_grado):
        con = t[t["d"].notna()]
        assert (con["n_grupo"] >= cat.MIN_GROUP_N).all()
        assert (con["n_resto"] >= cat.MIN_GROUP_N).all()
        sin = t[t["d"].isna()]
        assert sin[["media_grupo", "media_resto", "n_grupo"]].isna().all().all()


def test_cuidadores_cuentan_distintos(fuentes_sint):
    tablas = c1.marcos(fuentes_sint)
    assert tablas[cat.CUIDADOR]["Grado"].notna().all()
    for a in c1.atomos(tablas[cat.NINO], cat.NINO):
        if a.nombre != c1.RESTO:
            assert tablas[cat.NINO].loc[a.idx, "ID_cuidador"].nunique() >= cat.MIN_GROUP_N


def test_clasificacion_tiene_todos_los_pares_por_colegio(capa):
    assert len(capa.clasificacion) == len(cat.PARES) * len(capa.colegios)
    assert set(capa.clasificacion["clasificacion"]) <= {
        cat.COINCIDENCIA, cat.TENSION, cat.SIN_DIFERENCIA, cat.COOCURRENCIA, cat.SIN_DATO}
```

Run: `.venv/bin/python -m pytest tests/test_triangulacion_capa1.py -q`
Expected: FAIL con `ImportError: cannot import name 'capa1' from 'src.triangulacion'`.

- [ ] **Step 2: Implementar**

`src/triangulacion/capa1.py`:

```python
"""
Capa 1 de la triangulación — por colegio (y por grado), spec §5.6.

Para cada actor y constructo: la diferencia del grupo (colegio o grado) frente
al resto del municipio del MISMO actor, en unidades de la DE individual del
actor, con su IC del 95 %:

    d = (media del grupo − media del resto) / DE del actor
    IC = d ± 1,96 · √(s²_grupo / n_grupo + s²_resto / n_resto) / DE del actor

Qué entra:
  · Colegios publicables (§5.1) en estudiantes, cuidadores y docentes a la
    vez: con los datos de octubre de 2026, LauV, JJC, SJMEB y La Balsa.
  · Cuidadores: solo los de niños en los grados del estudio (marcos cuidador
    y niño con grado). En los dos, el mínimo cuenta cuidadores distintos.
  · Por grado: solo estudiantes y cuidadores (los docentes no tienen grado).

Cifras que no delatan. Cada marco se parte en ÁTOMOS con la base publicable de
su módulo (§5.1): las celdas colegio × grado con 10 o más, los colegios
publicados enteros (sin celdas) y el resto R, que solo entra si su módulo lo
admite. En docentes, que no tienen grado, los átomos son los colegios con 10
o más y R. Colegios, grados y «resto del municipio» son uniones de átomos, así
que toda suma o resta de cifras mostradas también lo es. Por constructo, un
átomo con 1 a 9 unidades con dato sale (todo o nada), y en un constructo
binario también si tiene menos de 3 casos o no casos (filas o unidades).

Clasificación (solo pares del mismo objeto): «tensión» si los dos IC excluyen
el cero en direcciones opuestas (orientadas: positivo = mejor que el resto),
«coincidencia» si lo excluyen en la misma, y si no «sin diferencia clara».
Los demás pares son «co-ocurrencia».
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.cuidadores import privacidad as priv_cuid
from src.estudiantes import privacidad as priv_est
from src.triangulacion import catalogo as cat
from src.triangulacion.estadistica import Z95, partes_seguras

RESTO = "__resto__"
COLUMNAS_DIFERENCIAS = ["agrupacion", "grupo", "clave", "actor", "constructo", "objeto",
                        "binario", "n_grupo", "n_resto", "media_grupo", "media_resto",
                        "de_actor", "d", "ic_inf", "ic_sup", "d_orientada", "motivo"]
COLUMNAS_CLASIFICACION = ["agrupacion", "grupo", "par", "tipo", "a", "d_a", "ic_a", "b",
                          "d_b", "ic_b", "clasificacion"]
MOTIVO_POCOS = "menos de 10 con dato o cifras pequeñas"
MOTIVO_RESTO = "el resto no llega a 10"


@dataclass(frozen=True)
class Atomo:
    nombre: str
    colegio: str | None
    grado: str | None
    idx: pd.Index


@dataclass
class Capa1:
    colegios: list = field(default_factory=list)
    grados: list = field(default_factory=list)
    conteos: dict = field(default_factory=dict)          # {marco: {colegio: n unidades}}
    diferencias: pd.DataFrame = field(default_factory=pd.DataFrame)
    clasificacion: pd.DataFrame = field(default_factory=pd.DataFrame)
    por_grado: pd.DataFrame = field(default_factory=pd.DataFrame)
    clasificacion_grado: pd.DataFrame = field(default_factory=pd.DataFrame)


def _unidades(d: pd.DataFrame, marco: str) -> pd.Series:
    col = cat.UNIDAD[marco]
    return d[col] if col else pd.Series(d.index, index=d.index)


def n_unidades(d: pd.DataFrame, marco: str) -> int:
    return int(_unidades(d, marco).nunique()) if len(d) else 0


def marcos(fuentes) -> dict:
    """Las tablas de cada marco (cuidadores y niños: solo grados del estudio)."""
    out = {}
    for m in (cat.ESTUDIANTE, cat.CUIDADOR, cat.NINO, cat.DOCENTE):
        d = fuentes.marco(m)
        if m in (cat.CUIDADOR, cat.NINO):
            d = d[d["Grado"].notna()]
        out[m] = d.reset_index(drop=True)
    return out


def conteos_por_colegio(tablas: dict) -> dict:
    return {m: {str(c): n_unidades(g, m) for c, g in d.groupby("Colegio")}
            for m, d in tablas.items()}


def _resto_suficiente(d: pd.DataFrame, idx, marco: str) -> bool:
    if len(idx) == 0:
        return False
    if marco in (cat.CUIDADOR, cat.NINO):
        return priv_cuid._resto_suficiente(d, idx, cat.MIN_GROUP_N)
    return priv_est._resto_suficiente(d.loc[idx, "Colegio"], cat.MIN_GROUP_N)


def atomos(d: pd.DataFrame, marco: str) -> list[Atomo]:
    """Átomos de un marco: unidades de su base publicable y el resto R si entra."""
    salida: list[Atomo] = []
    if marco == cat.DOCENTE:
        for colegio, g in d.groupby("Colegio"):
            if colegio not in cat.COLEGIOS_SIN_GRUPO and len(g) >= cat.MIN_GROUP_N:
                salida.append(Atomo(str(colegio), str(colegio), None, g.index))
        resto = d.index.difference(priv_est.union(a.idx for a in salida))
        if _resto_suficiente(d, resto, marco):
            salida.append(Atomo(RESTO, None, None, resto))
        return salida
    base = (priv_cuid.base_publicable(d) if marco in (cat.CUIDADOR, cat.NINO)
            else priv_est.base_publicable(d))
    for nombre, idx in priv_est.unidades(base):
        if priv_est.SEP in str(nombre):
            colegio, grado = priv_est.partir_celda(nombre)
        else:
            colegio, grado = str(nombre), None
        salida.append(Atomo(str(nombre), colegio, grado, idx))
    if base.incluye_resto:
        resto = base.nivel.difference(priv_est.union(a.idx for a in salida))
        if len(resto):
            salida.append(Atomo(RESTO, None, None, resto))
    return salida


def _atomo_ok(d: pd.DataFrame, a: Atomo, marco: str, c: cat.Constructo) -> bool:
    """Un átomo sin datos no aporta; con 1 a 9 (o < 3 casos o no casos) sale."""
    validas = a.idx[d.loc[a.idx, c.columna].notna().to_numpy()]
    if len(validas) == 0:
        return False
    sub = d.loc[validas]
    if a.nombre == RESTO:
        ok = _resto_suficiente(d, validas, marco)
    else:
        ok = n_unidades(sub, marco) >= cat.MIN_GROUP_N
    if ok and c.binario:
        unidades = _unidades(sub, marco) if cat.UNIDAD[marco] else None
        ok = partes_seguras(sub[c.columna], unidades, [1.0])
    return ok


def _fila(agrupacion, grupo, c: cat.Constructo, **valores) -> dict:
    fila = dict(agrupacion=agrupacion, grupo=grupo, clave=c.clave, actor=cat.ACTOR[c.marco],
                constructo=c.etiqueta, objeto=c.objeto, binario=c.binario)
    for k in COLUMNAS_DIFERENCIAS:
        fila.setdefault(k, valores.get(k, np.nan))
    fila["motivo"] = valores.get("motivo", "")
    return fila


def _del_grupo(a: Atomo, agrupacion: str, grupo: str) -> bool:
    return (a.colegio if agrupacion == "Colegio" else a.grado) == grupo


def diferencias_constructo(d: pd.DataFrame, lista: list[Atomo], c: cat.Constructo,
                           grupos: list, agrupacion: str) -> list[dict]:
    """Filas de `diferencias` de un constructo para cada grupo pedido."""
    if c.columna not in d.columns:
        return [_fila(agrupacion, g, c, motivo=MOTIVO_POCOS) for g in grupos]
    ok = [a for a in lista if _atomo_ok(d, a, c.marco, c)]
    v = d[c.columna].astype(float)

    def valores(atomos_: list[Atomo]) -> pd.Series:
        idx = priv_est.union(a.idx for a in atomos_)
        return v.loc[idx].dropna() if len(idx) else v.iloc[0:0]

    de = float(valores(ok).std(ddof=1)) if ok else float("nan")
    escala, dec = (100.0, 1) if c.binario else (1.0, 2)
    filas = []
    for g in grupos:
        propios = [a for a in ok if _del_grupo(a, agrupacion, g)]
        if not propios:
            filas.append(_fila(agrupacion, g, c, motivo=MOTIVO_POCOS))
            continue
        otros = [a for a in ok if not _del_grupo(a, agrupacion, g)]
        x, y = valores(propios), valores(otros)
        sub_resto = d.loc[y.index]
        if n_unidades(sub_resto, c.marco) < cat.MIN_GROUP_N or not de > 0:
            filas.append(_fila(agrupacion, g, c, motivo=MOTIVO_RESTO))
            continue
        dif = (x.mean() - y.mean()) / de
        se = np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y)) / de
        filas.append(_fila(
            agrupacion, g, c, n_grupo=len(x), n_resto=len(y),
            media_grupo=round(escala * x.mean(), dec), media_resto=round(escala * y.mean(), dec),
            de_actor=round(escala * de, dec), d=round(dif, 3),
            ic_inf=round(dif - Z95 * se, 3), ic_sup=round(dif + Z95 * se, 3),
            d_orientada=round(c.direccion * dif, 3)))
    return filas


def diferencias(tablas: dict, atomos_por_marco: dict, constructos, grupos: list,
                agrupacion: str) -> pd.DataFrame:
    filas = []
    for c in constructos:
        filas += diferencias_constructo(tablas[c.marco], atomos_por_marco[c.marco], c,
                                        grupos, agrupacion)
    return pd.DataFrame(filas, columns=COLUMNAS_DIFERENCIAS)


def _orientado(fila) -> tuple[float, float]:
    c = cat.POR_CLAVE[fila["clave"]]
    lo, hi = c.direccion * fila["ic_inf"], c.direccion * fila["ic_sup"]
    return min(lo, hi), max(lo, hi)


def _signo(lo: float, hi: float) -> int:
    return 1 if lo > 0 else (-1 if hi < 0 else 0)


def clasificar(par: cat.Par, fila_a, fila_b) -> str:
    if par.tipo == cat.COOCURRENCIA:
        return cat.COOCURRENCIA
    if fila_a is None or fila_b is None or pd.isna(fila_a["d"]) or pd.isna(fila_b["d"]):
        return cat.SIN_DATO
    sa, sb = _signo(*_orientado(fila_a)), _signo(*_orientado(fila_b))
    if sa == 0 or sb == 0:
        return cat.SIN_DIFERENCIA
    return cat.COINCIDENCIA if sa == sb else cat.TENSION


def _ic(fila) -> str:
    if fila is None or pd.isna(fila["d"]):
        return "—"
    return f"[{fila['ic_inf']:.2f}; {fila['ic_sup']:.2f}]"


def clasificacion(dif: pd.DataFrame, pares=cat.PARES) -> pd.DataFrame:
    if dif.empty:
        return pd.DataFrame(columns=COLUMNAS_CLASIFICACION)
    filas = []
    for (agrupacion, grupo), sub in dif.groupby(["agrupacion", "grupo"], sort=False):
        por_clave = {r["clave"]: r for _, r in sub.iterrows()}
        for par in pares:
            if par.a not in por_clave or par.b not in por_clave:
                continue
            fa, fb = por_clave[par.a], por_clave[par.b]
            filas.append(dict(
                agrupacion=agrupacion, grupo=grupo, par=par.titulo, tipo=par.tipo,
                a=cat.POR_CLAVE[par.a].etiqueta, d_a=fa["d"], ic_a=_ic(fa),
                b=cat.POR_CLAVE[par.b].etiqueta, d_b=fb["d"], ic_b=_ic(fb),
                clasificacion=clasificar(par, fa, fb)))
    return pd.DataFrame(filas, columns=COLUMNAS_CLASIFICACION)


def _grupos(lista: list[Atomo], agrupacion: str) -> set:
    return {(a.colegio if agrupacion == "Colegio" else a.grado) for a in lista} - {None}


def analizar(fuentes) -> Capa1:
    tablas = marcos(fuentes)
    por_marco = {m: atomos(d, m) for m, d in tablas.items()}
    colegios = sorted(set.intersection(*(_grupos(por_marco[m], "Colegio")
                                          for m in (cat.ESTUDIANTE, cat.CUIDADOR, cat.DOCENTE))))
    from src.cuidadores import catalog as cat_cuid
    en_todos = set.intersection(*(_grupos(por_marco[m], "Grado") for m in cat.MARCOS_GRADO))
    grados = [g for g in cat_cuid.GRADOS_ESTUDIO if g in en_todos]
    dif = diferencias(tablas, por_marco, cat.CONSTRUCTOS, colegios, "Colegio")
    en_grado = [c for c in cat.CONSTRUCTOS if c.marco in cat.MARCOS_GRADO]
    dif_g = diferencias(tablas, por_marco, en_grado, grados, "Grado")
    return Capa1(colegios=colegios, grados=grados, conteos=conteos_por_colegio(tablas),
                 diferencias=dif, clasificacion=clasificacion(dif), por_grado=dif_g,
                 clasificacion_grado=clasificacion(dif_g))
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_triangulacion_capa1.py -q`
Expected: `14 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/triangulacion/capa1.py tests/test_triangulacion_capa1.py
git commit -m "feat(triangulacion): capa 1 por colegio y por grado sobre átomos publicables" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Enlace exacto de díadas

**Files:**
- Create: `src/triangulacion/enlace.py`
- Create: `tests/test_triangulacion_enlace.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_triangulacion_enlace.py`:

```python
"""Triangulación · enlace exacto de díadas, verificado con el colegio."""
import pandas as pd
import pytest

from src.core import seudonimo as seud
from src.triangulacion import enlace as en
from src.triangulacion import fuentes as fu
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def enlace_sint(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_enlace"))
    mp = pytest.MonkeyPatch()
    mp.setenv("OBS360_DATOS_DIR", base)
    try:
        f = fu.cargar(k=K)
    finally:
        mp.undo()
    return en.enlazar(f.estudiantes, f.ninos, f.cuidadores)


def _est(nombre, colegio, **extra):
    return dict(N_hmac=seud.seudonimo(nombre, "N", K), Colegio=colegio, Grado="Sexto",
                Edad=11, Sexo="Mujer", nivel="secundaria", SDQ_Total=10.0, **extra)


def _nino(nombre, colegio, cuidador="C00000001", **extra):
    return dict(ID_nino=seud.seudonimo(nombre, "N", K), ID_cuidador=cuidador,
                Colegio=colegio, Grado="Sexto", Edad=11.0, Sexo="Niña", SDQ_Total=8.0, **extra)


def test_enlaza_solo_con_el_mismo_colegio():
    e = pd.DataFrame([_est("Ana Uno", "LauV"), _est("Ana Dos", "JJC")])
    n = pd.DataFrame([_nino("Ana Uno", "LauV"), _nino("Ana Dos", "LauV", "C00000002")])
    c = pd.DataFrame({"ID_cuidador": ["C00000001", "C00000002"], "EPDS_Total": [5.0, 9.0]})
    r = en.enlazar(e, n, c)
    assert r.informe["coincidencias_nombre"] == 2 and r.informe["verificadas"] == 1
    assert r.informe["descartadas_colegio_distinto"] == 1
    assert len(r.diadas) == 1 and r.diadas.loc[0, "a_EPDS_Total"] == 5.0


def test_no_hay_coincidencias_aproximadas():
    e = pd.DataFrame([_est("María José Pérez", "LauV"), _est("Maria Jose Perez", "JJC")])
    n = pd.DataFrame([_nino("Maria Jose Peres", "LauV"), _nino("MARÍA  JOSÉ PÉREZ", "JJC")])
    c = pd.DataFrame({"ID_cuidador": ["C00000001"], "EPDS_Total": [5.0]})
    r = en.enlazar(e.iloc[[0]], n, c)
    # «Peres» no enlaza con «Pérez»; mayúsculas, tildes y espacios sí (normalización),
    # pero esa coincidencia está en otro colegio y se descarta.
    assert r.informe["coincidencias_nombre"] == 1 and r.informe["verificadas"] == 0


def test_un_colegio_no_reconocido_no_verifica():
    e = pd.DataFrame([_est("Luis", "OTRO")])
    n = pd.DataFrame([_nino("Luis", "OTRO")])
    c = pd.DataFrame({"ID_cuidador": ["C00000001"]})
    r = en.enlazar(e, n, c)
    assert r.informe["verificadas"] == 0 and r.informe["descartadas_colegio_no_reconocido"] == 1


def test_las_diadas_no_llevan_nombres_ni_seudonimos_del_nino():
    e = pd.DataFrame([_est("Ana Uno", "LauV")])
    n = pd.DataFrame([_nino("Ana Uno", "LauV")])
    r = en.enlazar(e, n, pd.DataFrame({"ID_cuidador": ["C00000001"]}))
    columnas = set(r.diadas.columns)
    assert not columnas & {"N_hmac", "ID_nino", "e_N_hmac", "c_ID_nino", "ID", "e_ID"}
    assert {"familia", "Colegio", "e_SDQ_Total", "c_SDQ_Total"} <= columnas


def test_sintetico_enlaza_lo_esperado(enlace_sint):
    inf = enlace_sint.informe
    # 72 hijos 1 de LauV, JJC y SJMEB menos el 13 (sin estudiante) y el 41 (mal escrito)
    # = 70 coincidencias, más 4 hijos 2; el 40 está en otro colegio y se descarta.
    assert inf["coincidencias_nombre"] == 74
    assert inf["verificadas"] == 73 and inf["descartadas_colegio_distinto"] == 1
    assert inf["por_colegio"] == {"LauV": 37, "JJC": 22, "SJMEB": 14}
    assert inf["familias"] < inf["verificadas"]          # familias con dos díadas
    assert inf["grado"]["concordantes"] == inf["grado"]["con_dato"]


def test_tasas_y_conteos_legibles():
    assert en.conteo_legible(9) == "<10" and en.conteo_legible(10) == "10"
    assert en.tasa_legible(97, 100) == "97,0 %"
    assert en.tasa_legible(99, 100) == "casi todas"
    assert en.tasa_legible(2, 100) == "casi ninguna"
    assert en.tasa_legible(5, 9) == "—"


def test_tabla_de_calidad_oculta_los_conteos_pequenos(enlace_sint):
    t = en.tabla_calidad(enlace_sint.informe)
    valores = dict(zip(t["indicador"], t["valor"]))
    assert valores["Descartadas: colegio distinto"] == "<10"
    assert valores["Díadas en LauV"] == "37"
```

Run: `.venv/bin/python -m pytest tests/test_triangulacion_enlace.py -q`
Expected: FAIL con `ImportError: cannot import name 'enlace' from 'src.triangulacion'`.

- [ ] **Step 2: Implementar**

`src/triangulacion/enlace.py`:

```python
"""
Enlace de díadas niño–cuidador — solo local (spec §5.6, capa 2).

Regla única, sin coincidencias aproximadas:

    seudónimo HMAC «N…» del nombre normalizado del niño en el formulario de
    estudiantes  ==  el del hijo en el de cuidadores  (misma clave local)
    Y  mismo código de colegio en los dos (y que sea un colegio reconocido).

Un nombre escrito distinto («Nina» por «Niña» no lo arregla la normalización)
no enlaza. Un mismo nombre en colegios distintos se descarta y se cuenta.

`enlazar` devuelve las díadas (solo en memoria: nunca se guardan, se muestran
ni se exportan) y un informe de calidad que solo tiene conteos y tasas:
coincidencias, descartes por colegio y concordancia de sexo, edad (± 1 año) y
grado. La vista muestra los conteos por colegio como «<10» por debajo del
mínimo y las tasas con la regla 3 ≤ k ≤ n − 3.

Columnas de una díada: `familia` (seudónimo del cuidador, solo para agrupar
errores y contar familias distintas), `Colegio`, las del niño según él con el
prefijo `e_`, las del niño según su cuidador con `c_` y las del cuidador con
`a_`. Ningún nombre ni seudónimo del niño.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.estudiantes.supresion import proporcion_publicable
from src.triangulacion import catalogo as cat

COLUMNA_NINO = "N_hmac"
SEXO_NINO = {"Niña": "Mujer", "Niño": "Hombre"}
# Columnas que nunca pasan a una díada.
FUERA = ("N_hmac", "ID", "ID_nino", "ts", "_fila", "_edad_estado", "Colegio_nombre", "Sede")


@dataclass
class Enlace:
    diadas: pd.DataFrame
    informe: dict = field(default_factory=dict)


def _prefijo(d: pd.DataFrame, prefijo: str, quitar=()) -> pd.DataFrame:
    return d.drop(columns=[c for c in (*FUERA, *quitar) if c in d.columns]).add_prefix(prefijo)


def _concordancia(si: pd.Series, con_dato: pd.Series) -> dict:
    return dict(concordantes=int((si & con_dato).sum()), con_dato=int(con_dato.sum()))


def enlazar(estudiantes: pd.DataFrame, ninos: pd.DataFrame,
            cuidadores: pd.DataFrame) -> Enlace:
    """Díadas verificadas con el colegio e informe agregado de la calidad del enlace."""
    e = estudiantes[estudiantes[COLUMNA_NINO].notna()].drop_duplicates(COLUMNA_NINO)
    n = ninos[ninos["ID_nino"].notna() & ~ninos["ID_nino"].astype(str).str.startswith("sin-")]
    n = n.drop_duplicates("ID_nino")
    m = e.merge(n, left_on=COLUMNA_NINO, right_on="ID_nino", how="inner",
                suffixes=("_e", "_c"), validate="one_to_one")
    reconocido = ~m["Colegio_e"].isin(cat.COLEGIOS_SIN_GRUPO)
    mismo = m["Colegio_e"] == m["Colegio_c"]
    ok = m[mismo & reconocido]
    informe = dict(
        estudiantes_con_nombre=len(e), ninos_con_nombre=len(n),
        coincidencias_nombre=len(m), verificadas=len(ok),
        descartadas_colegio_distinto=int((~mismo).sum()),
        descartadas_colegio_no_reconocido=int((mismo & ~reconocido).sum()),
        familias=int(ok["ID_cuidador"].nunique()) if len(ok) else 0,
        por_colegio={str(k): int(v) for k, v in ok["Colegio_e"].value_counts().items()},
        descartes_por_colegio={str(k): int(v) for k, v in
                               m.loc[~mismo, "Colegio_e"].value_counts().items()},
        por_nivel={str(k): int(v) for k, v in ok["nivel"].value_counts().items()},
    )
    sexo_c = ok["Sexo_c"].map(SEXO_NINO)
    informe["sexo"] = _concordancia(sexo_c == ok["Sexo_e"],
                                    sexo_c.notna() & ok["Sexo_e"].isin(SEXO_NINO.values()))
    edad_ok = ok["Edad_e"].notna() & ok["Edad_c"].notna()
    informe["edad"] = _concordancia((ok["Edad_e"] - ok["Edad_c"]).abs() <= 1, edad_ok)
    informe["grado"] = _concordancia(ok["Grado_e"] == ok["Grado_c"], ok["Grado_c"].notna())

    ids = ok["ID_cuidador"].to_numpy()
    lado_e = e.set_index(COLUMNA_NINO).loc[ok[COLUMNA_NINO]].reset_index()
    lado_c = n.set_index("ID_nino").loc[ok["ID_nino"]].reset_index()
    adulto = cuidadores.drop_duplicates("ID_cuidador").set_index("ID_cuidador")
    lado_a = adulto.reindex(ids).reset_index(drop=True)
    diadas = pd.concat([
        pd.DataFrame({"familia": ids, "Colegio": ok["Colegio_e"].to_numpy()}),
        _prefijo(lado_e, "e_"), _prefijo(lado_c, "c_", quitar=("ID_cuidador",)),
        _prefijo(lado_a, "a_")], axis=1)
    return Enlace(diadas=diadas, informe=informe)


def tasa_legible(k: int, n: int) -> str:
    """Una tasa de concordancia con la regla de cifras pequeñas."""
    if n < cat.MIN_GROUP_N:
        return "—"
    if proporcion_publicable(k, n):
        return f"{100 * k / n:.1f} %".replace(".", ",")
    return "casi todas" if k > n - cat.MIN_CASOS else "casi ninguna"


def conteo_legible(valor) -> str:
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return "—"
    return str(v) if v >= cat.MIN_GROUP_N else f"<{cat.MIN_GROUP_N}"


def tabla_calidad(informe: dict) -> pd.DataFrame:
    """La calidad del enlace para mostrar y exportar: conteos legibles y tasas."""
    if not informe:
        return pd.DataFrame(columns=["indicador", "valor"])
    filas = [
        ("Estudiantes con nombre", conteo_legible(informe["estudiantes_con_nombre"])),
        ("Niños reportados por cuidadores (únicos)", conteo_legible(informe["ninos_con_nombre"])),
        ("Coincidencias exactas del seudónimo", conteo_legible(informe["coincidencias_nombre"])),
        ("Díadas verificadas con el colegio", conteo_legible(informe["verificadas"])),
        ("Familias distintas en las díadas", conteo_legible(informe["familias"])),
        ("Descartadas: colegio distinto", conteo_legible(informe["descartadas_colegio_distinto"])),
        ("Descartadas: colegio no reconocido",
         conteo_legible(informe["descartadas_colegio_no_reconocido"])),
    ]
    for colegio, v in sorted(informe["por_colegio"].items()):
        filas.append((f"Díadas en {colegio}", conteo_legible(v)))
    for nivel, v in sorted(informe["por_nivel"].items()):
        filas.append((f"Díadas en {nivel}", conteo_legible(v)))
    for clave, nombre in (("sexo", "Concordancia de sexo"),
                          ("edad", "Concordancia de edad (± 1 año)"),
                          ("grado", "Concordancia de grado")):
        c = informe[clave]
        filas.append((nombre, tasa_legible(c["concordantes"], c["con_dato"])))
    return pd.DataFrame(filas, columns=["indicador", "valor"])
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_triangulacion_enlace.py -q`
Expected: `7 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/triangulacion/enlace.py tests/test_triangulacion_enlace.py
git commit -m "feat(triangulacion): enlace exacto niño–cuidador verificado con el colegio" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Análisis de díadas

**Files:**
- Create: `src/triangulacion/diadas.py`
- Create: `tests/test_triangulacion_diadas.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

Las tablas de díadas se arman a mano, con cifras conocidas: en `_no_visto_base`, 10 de 40 díadas tienen malestar no visto, 16 tienen malestar y 24 no; el % esperado es exactamente `wilson(10, 40)`.

`tests/test_triangulacion_diadas.py`:

```python
"""Triangulación · análisis de díadas sobre tablas armadas a mano."""
import numpy as np
import pandas as pd
import pytest

from src.estudiantes.stats import wilson
from src.triangulacion import catalogo as cat
from src.triangulacion import diadas as dy


def _diadas(e_total, c_total, familias=None, colegio="LauV", seed=0) -> pd.DataFrame:
    n = len(e_total)
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({
        "familia": familias if familias is not None else [f"C{i:08x}" for i in range(n)],
        "Colegio": colegio,
        "e_SDQ_Total": e_total, "c_SDQ_Total": c_total,
        "e_ALERTA_malestar": 0.0,
        "e_Sexo": np.where(np.arange(n) % 2, "Mujer", "Hombre"),
        "e_Edad": 10 + np.arange(n) % 6,
    })
    for s in ("SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro"):
        d[f"e_{s}"] = rng.integers(0, 11, n).astype(float)
        d[f"c_{s}"] = rng.integers(0, 11, n).astype(float)
    d["e_SDQ_Int"] = rng.normal(size=n)
    d["e_SDQ_Ext"] = rng.normal(size=n)
    for k in ("MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro"):
        d[f"e_{k}"] = rng.uniform(1, 5, n)
        d[f"a_{k}"] = rng.uniform(1, 5, n)
    d["a_EPDS_Total"] = rng.integers(0, 31, n).astype(float)
    d["a_PSS_Total"] = rng.integers(0, 41, n).astype(float)
    d["a_APQ_Fisico"] = ((np.arange(n) // 3) % 2).astype(float)
    d["a_BARRIO_Indice"] = rng.integers(0, 11, n).astype(float)
    return d


def _no_visto_base():
    # 10 con malestar no visto (20 / 5), 6 con malestar visto (20 / 20), 24 sin malestar.
    e = [20.0] * 16 + [5.0] * 24
    c = [5.0] * 10 + [20.0] * 6 + [5.0] * 24
    return _diadas(e, c)


def test_malestar_no_visto_con_cifras_conocidas():
    t = dy.malestar_no_visto(_no_visto_base())
    f = t.iloc[0]
    assert f["n"] == 40 and f["motivo"] == ""
    assert (f["pct_no_visto"], f["ic_inf"], f["ic_sup"]) == wilson(10, 40)
    assert f["pct_malestar"] == wilson(16, 40)[0]
    assert f["pct_no_visto_entre_malestar"] == wilson(10, 16)[0]


def test_la_senal_de_malestar_tambien_cuenta():
    d = _no_visto_base()
    d.loc[d.index[-3:], "e_ALERTA_malestar"] = 1.0           # 3 más con señal, no vistos
    f = dy.malestar_no_visto(d).iloc[0]
    assert f["pct_no_visto"] == wilson(13, 40)[0]


def test_malestar_no_visto_se_suprime_con_menos_de_3():
    e = [20.0] * 12 + [5.0] * 28
    c = [5.0] * 10 + [20.0] * 2 + [5.0] * 28                  # solo 2 «visto»
    f = dy.malestar_no_visto(_diadas(e, c)).iloc[0]
    assert f["motivo"] == dy.MOTIVO_PEQUENAS and pd.isna(f.get("pct_no_visto"))


def test_malestar_no_visto_cuenta_familias():
    d = _no_visto_base()
    d.loc[d.index[:10], "familia"] = ["F1", "F2"] * 5          # 10 no vistos de 2 familias
    f = dy.malestar_no_visto(d).iloc[0]
    assert f["motivo"] == dy.MOTIVO_PEQUENAS


def test_menos_de_10_familias_no_da_cifras():
    d = _diadas([10.0] * 12, [9.0] * 12, familias=[f"F{i % 6}" for i in range(12)])
    a = dy.acuerdo_sdq(d, n_boot=20)
    assert (a["motivo"] == dy.MOTIVO_POCAS).all()
    assert dy.bland_altman_agrupado(d).empty
    assert (dy.malestar_no_visto(d)["motivo"] == dy.MOTIVO_POCAS).all()


def test_acuerdo_perfecto():
    x = np.arange(40, dtype=float) % 25
    a = dy.acuerdo_sdq(_diadas(x, x), n_boot=50)
    f = a[a["subescala"] == "SDQ_Total"].iloc[0]
    assert f["cci"] == pytest.approx(1.0) and f["dif_media"] == 0
    assert f["rho"] == pytest.approx(1.0) and f["ba_lim_inf"] == f["ba_lim_sup"] == 0
    assert f["n"] == 40 and f["familias"] == 40


def test_bland_altman_agrupado_nunca_tiene_menos_de_10():
    x = np.arange(40, dtype=float) % 25
    ba = dy.bland_altman_agrupado(_diadas(x, x[::-1]))
    total = ba[ba["subescala"] == "SDQ_Total"]
    assert len(total) == 4                                      # 5 grupos de 8 no caben
    assert (ba["n"] >= cat.MIN_GROUP_N).all()


def test_asociaciones_con_y_sin_efecto_fijo():
    d = _diadas(np.arange(40.0), np.arange(40.0))
    d.loc[d.index[20:], "Colegio"] = "JJC"
    t = dy.asociaciones(d)
    todas = t[t["muestra"].str.startswith("Todas")]
    assert set(todas["colegios"]) == {2}
    assert len(todas) == len(cat.RESULTADOS) * len(cat.PREDICTORES)
    lauv = t[t["muestra"].str.startswith("Solo")]
    assert (lauv["motivo"] == dy.MOTIVO_MODELO).all()           # 20 díadas < 30
    assert todas["q_bh"].notna().all()


def test_un_predictor_binario_con_pocas_familias_se_omite():
    d = _diadas(np.arange(40.0), np.arange(40.0))
    d["a_APQ_Fisico"] = 0.0
    d.loc[d.index[:5], "a_APQ_Fisico"] = 1.0
    t = dy.asociaciones(d)
    assert not t["predictor"].str.contains("Castigo").any()
    assert t["nota"].str.contains("Castigo").all()


def test_apoyo_familiar_por_fuente():
    t = dy.apoyo_familiar(_diadas(np.arange(40.0), np.arange(40.0)))
    assert list(t["fuente"]) == [n for _, n in cat.FUENTES_MSPSS]
    assert (t["n"] == 40).all()


def test_ninguna_salida_lleva_familias():
    r = dy.analizar(_no_visto_base(), n_boot=20)
    for t in (r.acuerdo, r.bland_altman, r.no_visto, r.apoyo, r.asociaciones):
        assert "familia" not in t.columns
        assert not t.astype(str).apply(lambda s: s.str.fullmatch(r"C[0-9a-f]{8}")).any().any()
```

Run: `.venv/bin/python -m pytest tests/test_triangulacion_diadas.py -q`
Expected: FAIL con `ImportError: cannot import name 'diadas' from 'src.triangulacion'`.

- [ ] **Step 2: Implementar**

`src/triangulacion/diadas.py`:

```python
"""
Capa 2 de la triangulación — análisis de díadas niño–cuidador (solo local).

Entra la tabla de díadas de `enlace.enlazar` (solo en memoria) y sale un
`Diadas` con tablas AGREGADAS:

  · `acuerdo`: SDQ del niño (autoinforme, bandas de autoinforme) frente al de
    su cuidador (versión para padres, bandas de padres), por subescala:
    Spearman y Pearson con IC de Fisher, CCI(A,1) y kappa ponderado lineal
    sobre las 4 bandas (IC por bootstrap de familias), diferencia media
    (niño − cuidador) con IC por errores agrupados y límites de Bland–Altman.
  · `bland_altman`: la figura agrupada, sin díadas: hasta 5 grupos por
    quintil del promedio de los dos informantes, cada uno con ≥ 10 díadas de
    ≥ 10 familias (si no caben, menos grupos).
  · `no_visto`: «malestar que el cuidador no ve» = el niño en banda alta o
    muy alta (o con la señal de malestar) y el cuidador lo ubica en la banda
    «cercano al promedio». % sobre todas las díadas, % de niños con malestar y
    % no visto entre ellos, con IC de Wilson. Las tres partes (sin malestar,
    malestar visto, malestar no visto) cumplen la regla 3 ≤ k ≤ n − 3 en
    díadas y en familias; si no, no se muestra ninguna cifra.
  · `apoyo`: MSPSS del niño frente al del cuidador, por fuente (aviso fijo:
    redacción y reparto de ítems distintos; no es acuerdo sobre lo mismo).
  · `asociaciones`: EPDS, PSS, castigo físico y barrio del cuidador con el
    SDQ del niño (total, internalizante, externalizante): MCO estandarizado,
    controles de sexo y edad del niño, efecto fijo de colegio y errores
    agrupados por familia; sensibilidad solo con Laura Vicuña.

Reglas de cifras pequeñas: toda cifra exige ≥ 10 díadas de ≥ 10 familias
distintas (los modelos, ≥ 30 díadas completas); un predictor binario exige
≥ 10 díadas y familias en cada nivel. Ninguna tabla lleva una díada.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.estudiantes import catalog as cat_est
from src.estudiantes.stats import benjamini_hochberg, wilson
from src.triangulacion import catalogo as cat
from src.triangulacion import estadistica as est

FAMILIA = "familia"
MOTIVO_POCAS = "menos de 10 díadas o de 10 familias"
MOTIVO_PEQUENAS = "cifras pequeñas: alguna parte con menos de 3 díadas o familias"
MOTIVO_MODELO = "menos de 30 díadas completas o de 10 familias"
MOTIVO_SINGULAR = "el modelo no se puede estimar (predictores redundantes)"


@dataclass
class Diadas:
    n: int = 0
    familias: int = 0
    acuerdo: pd.DataFrame = field(default_factory=pd.DataFrame)
    bland_altman: pd.DataFrame = field(default_factory=pd.DataFrame)
    no_visto: pd.DataFrame = field(default_factory=pd.DataFrame)
    apoyo: pd.DataFrame = field(default_factory=pd.DataFrame)
    asociaciones: pd.DataFrame = field(default_factory=pd.DataFrame)


def _r(v, dec: int = 3):
    return None if v is None or pd.isna(v) else round(float(v), dec)


def bandas(serie: pd.Series, clave: str, version: str) -> pd.Series:
    return serie.map(lambda v: cat_est.banda_de(v, clave, version) if pd.notna(v) else np.nan
                     ).astype(float)


def _par(D: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    if a not in D.columns or b not in D.columns:
        return D.iloc[0:0][[FAMILIA]]
    return D[[a, b, FAMILIA]].dropna()


def acuerdo_sdq(D: pd.DataFrame, n_boot: int = cat.N_BOOT) -> pd.DataFrame:
    filas = []
    for s in cat.SUBESCALAS_SDQ:
        e, c = f"e_{s}", f"c_{s}"
        sub = _par(D, e, c)
        fila = dict(subescala=s, escala=cat_est.meta(s)["label"])
        if not est.suficiente(sub, FAMILIA):
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        rho = est.correlacion_ic(sub[e], sub[c], "spearman")
        r = est.correlacion_ic(sub[e], sub[c], "pearson")
        icc = est.icc_a1(sub[[e, c]].to_numpy())
        icc_ic = est.bootstrap_ic(sub, lambda x: est.icc_a1(x[[e, c]].to_numpy()), FAMILIA,
                                  n_boot)
        be, bc = bandas(sub[e], s, "self"), bandas(sub[c], s, "parent")
        kw = est.kappa_ponderado(be, bc)
        kw_ic = est.bootstrap_ic(
            sub.assign(_be=be, _bc=bc),
            lambda x: est.kappa_ponderado(x["_be"], x["_bc"]), FAMILIA, n_boot)
        ba = est.bland_altman(sub[e], sub[c])
        mg = est.media_agrupada(sub[e] - sub[c], sub[FAMILIA])
        filas.append({**fila, "n": len(sub), "familias": int(sub[FAMILIA].nunique()),
                      "media_nino": _r(sub[e].mean(), 2), "media_cuidador": _r(sub[c].mean(), 2),
                      "rho": _r(rho[0]), "rho_ic_inf": _r(rho[1]), "rho_ic_sup": _r(rho[2]),
                      "r": _r(r[0]), "r_ic_inf": _r(r[1]), "r_ic_sup": _r(r[2]),
                      "cci": _r(icc), "cci_ic_inf": _r(icc_ic[0]), "cci_ic_sup": _r(icc_ic[1]),
                      "dif_media": _r(mg["m"], 2), "dif_ic_inf": _r(mg["ic_inf"], 2),
                      "dif_ic_sup": _r(mg["ic_sup"], 2), "ba_lim_inf": _r(ba["lim_inf"], 2),
                      "ba_lim_sup": _r(ba["lim_sup"], 2), "kappa_w": _r(kw),
                      "kappa_ic_inf": _r(kw_ic[0]), "kappa_ic_sup": _r(kw_ic[1]), "motivo": ""})
    return pd.DataFrame(filas)


def bland_altman_agrupado(D: pd.DataFrame) -> pd.DataFrame:
    """Promedio de la diferencia por grupos de ≥ 10 díadas y familias (sin puntos individuales)."""
    filas = []
    for s in cat.SUBESCALAS_SDQ:
        e, c = f"e_{s}", f"c_{s}"
        sub = _par(D, e, c)
        if not est.suficiente(sub, FAMILIA):
            continue
        x = (sub[e] + sub[c]) / 2
        dif = sub[e] - sub[c]
        for nb in range(cat.MAX_BINES_BA, 0, -1):
            grupo = (pd.qcut(x.rank(method="first"), nb, labels=False) if nb > 1
                     else pd.Series(0, index=x.index))
            if all(est.suficiente(sub[grupo == g], FAMILIA) for g in range(nb)):
                break
        for g in range(nb):
            m = grupo == g
            mg = est.media_agrupada(dif[m], sub.loc[m, FAMILIA])
            filas.append(dict(subescala=s, grupo=g + 1, n=int(m.sum()),
                              promedio_informantes=_r(x[m].mean(), 2),
                              dif_media=_r(mg["m"], 2), ic_inf=_r(mg["ic_inf"], 2),
                              ic_sup=_r(mg["ic_sup"], 2)))
    return pd.DataFrame(filas)


def malestar_no_visto(D: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for etiqueta, s, con_senal in cat.VARIANTES_NO_VISTO:
        e, c = f"e_{s}", f"c_{s}"
        fila = dict(variante=etiqueta)
        if e not in D.columns or c not in D.columns:
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        sub = D[D[e].notna() & D[c].notna()]
        if not est.suficiente(sub, FAMILIA):
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        malestar = bandas(sub[e], s, "self") >= 2
        if con_senal and "e_ALERTA_malestar" in sub.columns:
            malestar = malestar | (sub["e_ALERTA_malestar"] == 1)
        no_visto = malestar & (bandas(sub[c], s, "parent") == 0)
        parte = pd.Series(np.where(~malestar, 0, np.where(no_visto, 2, 1)), index=sub.index)
        if not est.partes_seguras(parte, sub[FAMILIA], (0, 1, 2)):
            filas.append({**fila, "n": len(sub), "motivo": MOTIVO_PEQUENAS})
            continue
        n, k_m, k = len(sub), int(malestar.sum()), int(no_visto.sum())
        p, lo, hi = wilson(k, n)
        pm, lom, him = wilson(k_m, n)
        pe, loe, hie = wilson(k, k_m)
        filas.append({**fila, "n": n, "familias": int(sub[FAMILIA].nunique()),
                      "pct_no_visto": p, "ic_inf": lo, "ic_sup": hi,
                      "pct_malestar": pm, "malestar_ic_inf": lom, "malestar_ic_sup": him,
                      "pct_no_visto_entre_malestar": pe, "entre_ic_inf": loe,
                      "entre_ic_sup": hie, "motivo": ""})
    return pd.DataFrame(filas)


def apoyo_familiar(D: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for clave, nombre in cat.FUENTES_MSPSS:
        e, a = f"e_{clave}", f"a_{clave}"
        sub = _par(D, e, a)
        fila = dict(fuente=nombre)
        if not est.suficiente(sub, FAMILIA):
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        rho = est.correlacion_ic(sub[e], sub[a], "spearman")
        mg = est.media_agrupada(sub[e] - sub[a], sub[FAMILIA])
        filas.append({**fila, "n": len(sub), "familias": int(sub[FAMILIA].nunique()),
                      "media_nino": _r(sub[e].mean(), 2), "media_cuidador": _r(sub[a].mean(), 2),
                      "rho": _r(rho[0]), "rho_ic_inf": _r(rho[1]), "rho_ic_sup": _r(rho[2]),
                      "dif_media": _r(mg["m"], 2), "dif_ic_inf": _r(mg["ic_inf"], 2),
                      "dif_ic_sup": _r(mg["ic_sup"], 2), "motivo": ""})
    return pd.DataFrame(filas)


def _z(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=1)


def _modelo(datos: pd.DataFrame, y: str, etiqueta_y: str, muestra: str,
            efecto_fijo: bool) -> list[dict]:
    pred_cols = [f"a_{p}" for p, _, _ in cat.PREDICTORES]
    cols = [f"e_{y}", *pred_cols, "e_Sexo", "e_Edad", FAMILIA, "Colegio"]
    if any(c not in datos.columns for c in cols):
        return [dict(muestra=muestra, resultado=etiqueta_y, motivo=MOTIVO_MODELO)]
    sub = datos[cols].dropna()
    base = dict(muestra=muestra, resultado=etiqueta_y)
    if len(sub) < cat.MIN_MODELO or sub[FAMILIA].nunique() < cat.MIN_GROUP_N:
        return [{**base, "motivo": MOTIVO_MODELO}]
    X, omitidos = pd.DataFrame(index=sub.index), []
    for p, etiqueta, binario in cat.PREDICTORES:
        v = sub[f"a_{p}"].astype(float)
        if binario:
            niveles_ok = all(est.suficiente(sub[v == nivel], FAMILIA) for nivel in (0.0, 1.0))
            if not niveles_ok:
                omitidos.append(etiqueta)
                continue
            X[etiqueta] = v
        elif v.std(ddof=1) > 0:
            X[etiqueta] = _z(v)
    controles = pd.DataFrame({"_mujer": (sub["e_Sexo"] == "Mujer").astype(float),
                              "_edad": sub["e_Edad"].astype(float)}, index=sub.index)
    controles = controles.loc[:, controles.std(ddof=1) > 0]
    if "_edad" in controles:
        controles["_edad"] = _z(controles["_edad"])
    try:
        res = est.ols_agrupado(_z(sub[f"e_{y}"].astype(float)),
                               pd.concat([X, controles], axis=1), sub[FAMILIA],
                               sub["Colegio"] if efecto_fijo else None)
    except np.linalg.LinAlgError:
        return [{**base, "motivo": MOTIVO_SINGULAR}]
    res = res[res["predictor"].isin(X.columns)]
    nota = ("Omitido por cifras pequeñas: " + ", ".join(omitidos)) if omitidos else ""
    return [{**base, "predictor": f["predictor"], "beta": _r(f["beta"]), "ic_inf": _r(f["ic_inf"]),
             "ic_sup": _r(f["ic_sup"]), "p": _r(f["p"], 4), "n": len(sub),
             "familias": int(sub[FAMILIA].nunique()), "colegios": int(sub["Colegio"].nunique()),
             "motivo": "", "nota": nota} for _, f in res.iterrows()]


def asociaciones(D: pd.DataFrame) -> pd.DataFrame:
    muestras = (("Todas las díadas (efecto fijo de colegio)", D, True),
                ("Solo Laura Vicuña (sensibilidad)", D[D["Colegio"] == cat.COLEGIO_SENSIBILIDAD],
                 False))
    filas = []
    for muestra, datos, ef in muestras:
        for y, etiqueta_y in cat.RESULTADOS:
            filas += _modelo(datos, y, etiqueta_y, muestra, ef)
    t = pd.DataFrame(filas)
    if not t.empty and "p" in t.columns:
        t["q_bh"] = np.nan
        for muestra, sub in t[t["p"].notna()].groupby("muestra"):
            t.loc[sub.index, "q_bh"] = np.round(benjamini_hochberg(sub["p"].to_numpy()), 4)
    return t


def analizar(D: pd.DataFrame, n_boot: int = cat.N_BOOT) -> Diadas:
    if D.empty:
        return Diadas()
    return Diadas(n=len(D), familias=int(D[FAMILIA].nunique()),
                  acuerdo=acuerdo_sdq(D, n_boot), bland_altman=bland_altman_agrupado(D),
                  no_visto=malestar_no_visto(D), apoyo=apoyo_familiar(D),
                  asociaciones=asociaciones(D))
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_triangulacion_diadas.py -q`
Expected: `11 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/triangulacion/diadas.py tests/test_triangulacion_diadas.py
git commit -m "feat(triangulacion): acuerdo SDQ, malestar no visto, apoyo y asociaciones por díada" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Orquestación (solo agregados) y paquete exportable

**Files:**
- Create: `src/triangulacion/pipeline.py`, `src/triangulacion/exportar.py`
- Create: `tests/test_triangulacion_privacidad.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_triangulacion_privacidad.py`:

```python
"""
Triangulación · privacidad de punta a punta y paquete exportable (sintéticos).

Nada individual en el objeto que llega a la vista ni en el ZIP: ni nombres, ni
teléfono, ni seudónimos (C… / N… / E…), ni díadas; toda cifra con ≥ 10.
"""
import io
import re
import zipfile

import pytest

from src.triangulacion import catalogo as cat
from src.triangulacion import exportar as ex
from src.triangulacion import pipeline
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()
SEUDONIMO = re.compile(r"\b[CEN][0-9a-f]{8}\b")


@pytest.fixture(scope="module")
def tri(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_priv"))
    mp = pytest.MonkeyPatch()
    mp.setenv("OBS360_DATOS_DIR", base)
    try:
        yield pipeline.cargar_y_analizar(k=K, n_boot=30)
    finally:
        mp.undo()


def _tablas(t) -> dict:
    return ex.tablas(t)


def test_el_resultado_solo_tiene_agregados(tri):
    for nombre, df in _tablas(tri).items():
        assert not {"familia", "ID_cuidador", "ID_nino", "N_hmac", "ID"} & set(df.columns), nombre
        assert len(df) < 200, nombre                  # tablas de grupos, no de personas
    assert not hasattr(tri, "fuentes") and not hasattr(tri.diadas, "datos")


def test_ningun_texto_prohibido_ni_seudonimo_en_el_zip(tri):
    z = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(tri)))
    textos = [z.read(n).decode("utf-8") for n in z.namelist() if not n.endswith(".png")]
    for texto in textos:
        for prohibido in ts.textos_prohibidos():
            assert prohibido not in texto
        assert not SEUDONIMO.search(texto)


def test_el_zip_trae_tablas_figuras_y_metodologia(tri):
    z = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(tri)))
    nombres = set(z.namelist())
    assert {"metodologia.md", "version_analisis.txt", "capa1_diferencias.csv",
            "enlace_calidad.csv", "diadas_acuerdo_sdq.csv"} <= nombres
    for colegio in tri.capa1.colegios:
        assert z.read(f"figuras/capa1_{colegio}.png").startswith(b"\x89PNG")
    assert any(n.startswith("figuras/bland_altman_") for n in nombres)


def test_la_metodologia_es_la_plantilla_fija(tri):
    md = ex.metodologia_md(tri)
    for titulo in ("## Alcance", "## Capa 1 · por colegio y por grado",
                   "## Capa 2 · díadas niño–cuidador", "## Límites"):
        assert titulo in md
    assert cat.AVISO_ENLACE in md and cat.AVISO_COOCURRENCIA in md
    assert cat.AVISO_ECOLOGICO.format(n=tri.n_colegios) in md


def test_bland_altman_no_dibuja_diadas(tri):
    fig = ex.figura_bland_altman(tri, "SDQ_Total")
    ax = fig.axes[0]
    # Los únicos puntos son los cuadrados de los grupos (las barras de error y las
    # líneas horizontales no son datos de personas).
    puntos = sum(len(l.get_xdata()) for l in ax.get_lines() if l.get_marker() == "s")
    assert 0 < puntos <= cat.MAX_BINES_BA
    assert not ax.collections or all(len(c.get_offsets()) <= cat.MAX_BINES_BA
                                     for c in ax.collections if hasattr(c, "get_offsets"))


def test_cada_cifra_de_diadas_tiene_10_familias(tri):
    for t in (tri.diadas.acuerdo, tri.diadas.apoyo):
        con = t[t["motivo"] == ""]
        assert (con["familias"] >= cat.MIN_GROUP_N).all()
    ba = tri.diadas.bland_altman
    assert ba.empty or (ba["n"] >= cat.MIN_GROUP_N).all()
    nv = tri.diadas.no_visto
    pub = nv[nv["motivo"] == ""]
    assert pub.empty or (pub["familias"] >= cat.MIN_GROUP_N).all()


def test_nada_de_triangulacion_sube_a_supabase():
    """Ningún módulo de la triangulación importa el cliente de Supabase ni el publicador."""
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parents[1]
    archivos = [*(raiz / "src" / "triangulacion").glob("*.py"),
                raiz / "src" / "ui" / "triangulacion.py",
                raiz / "src" / "ui" / "views" / "triangulacion_investigador.py"]
    prohibidos = re.compile(r"^\s*(from|import)\s+.*(supabase|publicar|lectura|almacen)",
                            re.MULTILINE)
    for f in archivos:
        assert not prohibidos.search(f.read_text(encoding="utf-8")), f.name
```

Run: `.venv/bin/python -m pytest tests/test_triangulacion_privacidad.py -q`
Expected: FAIL con `ImportError: cannot import name 'exportar' from 'src.triangulacion'`.

- [ ] **Step 2: Implementar**

`src/triangulacion/pipeline.py`:

```python
"""
Orquestación de la Triangulación 360 — solo local, solo agregados.

`analizar(fuentes)` arma la capa 1 (por colegio y por grado), enlaza las
díadas y las analiza. Devuelve un `Triangulacion` que SOLO tiene tablas
agregadas: ni filas, ni seudónimos, ni la tabla de díadas (que vive y muere
dentro de esta función). Lo que ve la página y lo que exporta el ZIP sale de
aquí.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import diadas as dy
from src.triangulacion import enlace as en
from src.triangulacion import fuentes as fu


@dataclass
class Triangulacion:
    capa1: c1.Capa1
    enlace: dict = field(default_factory=dict)        # informe agregado del enlace
    diadas: dy.Diadas = field(default_factory=dy.Diadas)
    actores: dict = field(default_factory=dict)       # {actor: unidades analizadas}

    @property
    def n_colegios(self) -> int:
        return len(self.capa1.colegios)


def analizar(fuentes: fu.Fuentes, n_boot: int = cat.N_BOOT) -> Triangulacion:
    capa = c1.analizar(fuentes)
    enlace = en.enlazar(fuentes.estudiantes, fuentes.ninos, fuentes.cuidadores)
    resultado = dy.analizar(enlace.diadas, n_boot=n_boot)
    actores = {
        "Estudiantes": len(fuentes.estudiantes),
        "Cuidadores (distintos)": int(fuentes.cuidadores["ID_cuidador"].nunique()),
        "Niños reportados por cuidadores": len(fuentes.ninos),
        "Docentes": len(fuentes.docentes),
    }
    return Triangulacion(capa1=capa, enlace=enlace.informe, diadas=resultado, actores=actores)


def cargar_y_analizar(k: bytes | None = None, n_boot: int = cat.N_BOOT) -> Triangulacion:
    return analizar(fu.cargar(k=k), n_boot=n_boot)
```

`src/triangulacion/exportar.py`:

```python
"""
Paquete local de la Triangulación 360: tablas, figuras y metodología.

Todo sale de un `pipeline.Triangulacion`, que solo tiene agregados. Nada de
esto sube a Supabase ni se publica: el ZIP se descarga en la máquina local.

Figuras (matplotlib, sin estado global: `matplotlib.figure.Figure`):
  · `capa1_<colegio>.png`: d con su IC por constructo, coloreado por actor.
  · `bland_altman_<subescala>.png`: Bland–Altman AGRUPADO (cada punto es un
    grupo de ≥ 10 díadas de ≥ 10 familias), con la diferencia media y los
    límites de acuerdo. Ninguna díada se dibuja.

`metodologia.md` es una plantilla fija: solo se rellenan conteos agregados.
"""
from __future__ import annotations

import datetime as _dt
import io
import zipfile

import pandas as pd

from src.triangulacion import catalogo as cat
from src.triangulacion import enlace as en

TABLAS = ("capa1_diferencias.csv", "capa1_clasificacion.csv", "capa1_por_grado.csv",
          "capa1_clasificacion_grado.csv", "enlace_calidad.csv", "diadas_acuerdo_sdq.csv",
          "diadas_bland_altman_agrupado.csv", "diadas_malestar_no_visto.csv",
          "diadas_apoyo_familiar.csv", "diadas_asociaciones.csv")
COLORES = {"Estudiantes": "#3b6ea8", "Cuidadores": "#b5651d", "Docentes": "#4d8b55"}
# Columnas que nunca salen, aunque una tabla las trajera.
PROHIBIDAS = ("familia", "ID_cuidador", "ID_nino", "N_hmac", "ID", "casos")


def _limpia(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df.drop(columns=[c for c in PROHIBIDAS if c in df.columns])


def _csv(df: pd.DataFrame | None) -> str:
    df = _limpia(df)
    return "" if df.empty else df.to_csv(index=False)


def tablas(t) -> dict[str, pd.DataFrame]:
    c, d = t.capa1, t.diadas
    return {
        "capa1_diferencias.csv": c.diferencias, "capa1_clasificacion.csv": c.clasificacion,
        "capa1_por_grado.csv": c.por_grado, "capa1_clasificacion_grado.csv": c.clasificacion_grado,
        "enlace_calidad.csv": en.tabla_calidad(t.enlace),
        "diadas_acuerdo_sdq.csv": d.acuerdo, "diadas_bland_altman_agrupado.csv": d.bland_altman,
        "diadas_malestar_no_visto.csv": d.no_visto, "diadas_apoyo_familiar.csv": d.apoyo,
        "diadas_asociaciones.csv": d.asociaciones,
    }


# ── figuras ────────────────────────────────────────────────────────────────
def figura_capa1(t, colegio: str):
    from matplotlib.figure import Figure
    dif = t.capa1.diferencias
    sub = dif[(dif["grupo"] == colegio) & dif["d"].notna()] if not dif.empty else dif
    fig = Figure(figsize=(8, max(2.5, 0.42 * len(sub) + 1)))
    ax = fig.add_subplot(111)
    if sub.empty:
        ax.text(0.5, 0.5, "Sin cifras para mostrar", ha="center", va="center")
        ax.set_axis_off()
        return fig
    y = list(range(len(sub)))[::-1]
    for yi, (_, f) in zip(y, sub.iterrows()):
        color = COLORES.get(f["actor"], "#555555")
        ax.errorbar(f["d"], yi, xerr=[[f["d"] - f["ic_inf"]], [f["ic_sup"] - f["d"]]],
                    fmt="o", color=color, capsize=3)
    ax.axvline(0, color="#999999", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{f['actor']}: {f['constructo']}" for _, f in sub.iterrows()],
                       fontsize=7)
    ax.set_xlabel("Diferencia con el resto del municipio (DE del actor), IC 95 %")
    ax.set_title(f"{colegio}: cada actor frente al resto de su actor", fontsize=10)
    fig.tight_layout()
    return fig


def figura_bland_altman(t, subescala: str):
    from matplotlib.figure import Figure
    ba = t.diadas.bland_altman
    sub = ba[ba["subescala"] == subescala] if not ba.empty else ba
    acuerdo = t.diadas.acuerdo
    fila = (acuerdo[acuerdo["subescala"] == subescala].iloc[0]
            if not acuerdo.empty and (acuerdo["subescala"] == subescala).any() else None)
    fig = Figure(figsize=(6.5, 4))
    ax = fig.add_subplot(111)
    if sub.empty or fila is None or pd.isna(fila.get("dif_media")):
        ax.text(0.5, 0.5, "Sin cifras para mostrar", ha="center", va="center")
        ax.set_axis_off()
        return fig
    ax.errorbar(sub["promedio_informantes"], sub["dif_media"],
                yerr=[sub["dif_media"] - sub["ic_inf"], sub["ic_sup"] - sub["dif_media"]],
                fmt="s", color="#3b6ea8", capsize=3, label="Grupo de ≥ 10 díadas (IC 95 %)")
    ax.axhline(fila["dif_media"], color="#333333", linewidth=1.2, label="Diferencia media")
    for lim in ("ba_lim_inf", "ba_lim_sup"):
        ax.axhline(fila[lim], color="#b5651d", linestyle="--", linewidth=1)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_xlabel("Promedio de los dos informantes (grupo)")
    ax.set_ylabel("Niño − cuidador")
    ax.set_title(f"Bland–Altman agrupado · {fila['escala']}", fontsize=10)
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    return fig


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    return buf.getvalue()


# ── textos ─────────────────────────────────────────────────────────────────
def metodologia_md(t) -> str:
    inf = t.enlace or {}
    actores = "; ".join(f"{k}: {en.conteo_legible(v)}" for k, v in (t.actores or {}).items())
    calidad = en.tabla_calidad(inf)
    lineas_calidad = [f"- {r.indicador}: {r.valor}" for r in calidad.itertuples()]
    lineas = [
        "# Metodología · Triangulación 360 (fase 5, solo local)", "",
        "## Alcance", "",
        "Solo para el equipo investigador y solo en la máquina que procesa los formularios. "
        "Nada de este paquete sube a Supabase ni se publica. " + cat.AVISO_TEXTOS, "",
        f"Personas analizadas: {actores or '—'}.", "",
        "## Capa 1 · por colegio y por grado", "",
        cat.AVISO_ECOLOGICO.format(n=t.n_colegios), "",
        f"Colegios: {', '.join(t.capa1.colegios) or '—'} (publicables en estudiantes, "
        "cuidadores y docentes a la vez). Cuidadores: solo los de niños en los grados del "
        "estudio; el mínimo cuenta cuidadores distintos.", "",
        "d = (media del grupo − media del resto) / DE individual del actor; IC del 95 % "
        "= d ± 1,96 · √(s²₁/n₁ + s²₂/n₂) / DE. En los constructos binarios la media es una "
        "proporción y se muestra como %.", "",
        cat.AVISO_RESTO, "",
        "Átomos: las unidades de la base publicable de cada módulo (celdas colegio × grado "
        "con 10 o más, colegios publicados enteros y el resto R si su módulo lo admite; en "
        "docentes, los colegios con 10 o más y R). Por constructo, un átomo con 1 a 9 "
        "unidades con dato, o con menos de 3 casos o no casos, sale: toda suma o resta de "
        "cifras mostradas es unión de átomos que cumplen la regla.", "",
        cat.AVISO_CLASIFICACION, "", cat.AVISO_COOCURRENCIA, "", cat.AVISO_GRADO, "",
        "Docentes: archivo codificado por scripts/preparar_docentes.py; colegio unido con "
        "core.colegios.codigo_desde_nombre. Clima laboral = apoyo del líder (7 ítems, 0–5); "
        "apoyo percibido = apoyo de compañeros (3 ítems, 0–5); PSS-10 (0–40, prorrateo con 9 "
        "de 10); desgaste (4 ítems, 1–7).", "",
        "## Capa 2 · díadas niño–cuidador", "",
        cat.AVISO_ENLACE, "", *lineas_calidad, "",
        cat.AVISO_DIADAS, "",
        f"- Acuerdo SDQ por subescala: Spearman y Pearson (IC de Fisher), CCI(A,1) de McGraw "
        f"y Wong y kappa ponderado lineal sobre 4 bandas (IC percentil con {cat.N_BOOT} "
        "remuestreos de familias), diferencia media niño − cuidador (IC por errores "
        "agrupados por familia) y límites de Bland–Altman (± 1,96 DE). " + cat.AVISO_SDQ,
        "- " + cat.AVISO_BLAND_ALTMAN,
        "- «Malestar que el cuidador no ve»: el niño en banda alta o muy alta de su "
        "autoinforme o con la señal de malestar (3 o más de 6 ítems «muy cierto»), y el "
        "cuidador lo ubica en «cercano al promedio» con las bandas de padres. Se publica "
        "solo si las tres partes (sin malestar, visto, no visto) tienen 3 o más díadas y "
        "familias, y no más de n − 3. IC de Wilson.",
        "- MSPSS por fuente: Spearman y diferencia media. " + cat.AVISO_MSPSS,
        "- " + cat.AVISO_ASOCIACIONES + " Resultados estandarizados (z); predictores "
        "continuos en z y castigo físico como 0/1; un predictor binario exige 10 o más "
        "díadas y familias en cada nivel. q de Benjamini–Hochberg por muestra.", "",
        "## Límites", "",
        "- Enlace exacto: un nombre escrito distinto en los dos formularios no enlaza; las "
        "díadas no son una muestra aleatoria de los niños.",
        "- Cada cuidador aporta su respuesta más reciente; si respondió en dos olas, la del "
        "niño puede ser de otra ola.",
        "- La protección contra restas se garantiza dentro de la triangulación; no se "
        "auditan restas contra otras vistas locales.",
    ]
    return "\n".join(lineas) + "\n"


def version_txt(t) -> str:
    return "\n".join([
        "Triangulación 360 · versión del análisis",
        f"Fecha: {_dt.date.today().isoformat()}",
        f"Colegios en la capa 1: {', '.join(t.capa1.colegios) or '—'}",
        f"Grados en la capa 1: {', '.join(t.capa1.grados) or '—'}",
        f"Díadas: {en.conteo_legible(t.diadas.n)} · familias: "
        f"{en.conteo_legible(t.diadas.familias)}",
        f"Remuestreos bootstrap: {cat.N_BOOT}",
    ]) + "\n"


def archivos(t) -> dict[str, object]:
    salida: dict[str, object] = {n: _csv(df) for n, df in tablas(t).items()}
    for colegio in t.capa1.colegios:
        salida[f"figuras/capa1_{colegio}.png"] = _png(figura_capa1(t, colegio))
    ba = t.diadas.bland_altman
    for s in (ba["subescala"].unique() if not ba.empty else []):
        salida[f"figuras/bland_altman_{s}.png"] = _png(figura_bland_altman(t, s))
    salida["metodologia.md"] = metodologia_md(t)
    salida["version_analisis.txt"] = version_txt(t)
    return salida


def paquete_zip(t) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in archivos(t).items():
            if contenido:
                z.writestr(nombre, contenido)
    return buf.getvalue()
```

- [ ] **Step 3: Correr**

Run: `.venv/bin/python -m pytest tests/test_triangulacion_privacidad.py -q`
Expected: `7 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/triangulacion/pipeline.py src/triangulacion/exportar.py \
        tests/test_triangulacion_privacidad.py
git commit -m "feat(triangulacion): resultado solo agregado y ZIP local con figuras y metodología" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Página, vista, navegación y corte público

**Files:**
- Create: `src/ui/triangulacion.py`, `src/ui/views/triangulacion_investigador.py`
- Create: `tests/test_triangulacion_pagina.py`
- Modify: `src/core/navegacion.py:33-37`
- Modify: `main.py:121-125`
- Modify: `tests/test_navegacion.py`, `tests/test_modo_despliegue.py`

- [ ] **Step 1: Escribir las pruebas que fallan**

`tests/test_triangulacion_pagina.py`:

```python
"""Triangulación 360 · página (fase 5): sin archivos, sin clave, módulo viejo y sintéticos."""

from src.triangulacion import catalogo as cat
from src.ui.views import triangulacion_investigador as vi
from tests import triangulacion_sinteticos as ts


def _pagina(monkeypatch, datos: str, clave: str | None):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    if clave:
        monkeypatch.setenv("OBS360_CLAVE_HMAC", clave)
    else:
        monkeypatch.delenv("OBS360_CLAVE_HMAC", raising=False)
        monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    return AppTest.from_string(
        "from src.ui.triangulacion import render_triangulacion\nrender_triangulacion()\n",
        default_timeout=180)


def test_sin_archivos_da_el_mensaje_del_despliegue(monkeypatch, tmp_path):
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any(cat.AVISO_DESPLIEGUE in i.value for i in at.info)
    assert any("Cuidadores: no" in c.value for c in at.caption)


def test_sin_clave_explica_que_falta(monkeypatch, tmp_path):
    ts.escribir(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), None).run()
    assert not at.exception
    assert any("OBS360_CLAVE_HMAC" in e.value for e in at.error)


def test_con_un_modulo_viejo_pide_reiniciar(monkeypatch, tmp_path):
    from src.estudiantes import ingest
    ts.escribir(tmp_path)

    def viejo(rutas, niveles=None):
        raise AssertionError("no debía llamarse")
    monkeypatch.setattr(ingest, "cargar_varios", viejo)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any("Reinicie" in w.value for w in at.warning)


def test_con_datos_muestra_las_pestanas_sin_nada_individual(monkeypatch, tmp_path):
    ts.escribir(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS
    at.selectbox(key="tri_ba").set_value("SDQ_Emo").run()
    assert not at.exception
    pantalla = " ".join(str(e.value) for e in at.markdown) + \
        " ".join(str(getattr(d, "value", "")) for d in at.dataframe)
    for prohibido in ts.textos_prohibidos():
        assert prohibido not in pantalla
```

En `tests/test_navegacion.py`, sustituir:

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

por:

```python
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
```

Sustituir:

```python
def test_triangulacion_nunca_es_publica():
    assert nav.PAGINA_TRIANGULACION not in nav.PUBLICAS
```

por:

```python
def test_triangulacion_nunca_es_publica():
    assert nav.PAGINA_TRIANGULACION not in nav.PUBLICAS


def test_triangulacion_sigue_fuera_aunque_cuidadores_sea_publica(monkeypatch):
    monkeypatch.setattr(nav, "CUIDADORES_PUBLICO", True)
    assert nav.PAGINA_TRIANGULACION not in nav.menu(COMUNIDAD)
```

Ampliar `PROHIBIDOS_EN_COMUNIDAD`, sustituyendo:

```python
    "src.ui.cuidadores", "src.ui.views.cuidadores_investigador",
    "src.cuidadores.ingest", "src.cuidadores.pipeline")
```

por:

```python
    "src.ui.cuidadores", "src.ui.views.cuidadores_investigador",
    "src.cuidadores.ingest", "src.cuidadores.pipeline",
    "src.ui.triangulacion", "src.ui.views.triangulacion_investigador",
    "src.triangulacion.fuentes", "src.triangulacion.enlace", "src.triangulacion.diadas",
    "src.triangulacion.capa1", "src.triangulacion.pipeline")
```

(`test_main_en_comunidad_no_importa_modulos_internos` y `test_comunidad_con_dos_paginas_publicas_muestra_el_selector` comprueban así que el despliegue público no importa ningún módulo de la triangulación.)

Y añadir al final:

```python


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

En `tests/test_modo_despliegue.py`, dentro de `test_el_punto_de_entrada_corta_antes_de_importar_lo_demas`, después de

```python
    # Cuidadores 360 (fase 4a) solo se enruta después del corte, para investigadores
    assert "src.ui.cuidadores" not in antes and "src.cuidadores" not in antes
    assert "from src.ui.cuidadores import render_cuidadores" in despues
```

añadir:

```python

    # Triangulación 360 (fase 5) también: después del corte y solo para investigadores
    assert "src.triangulacion" not in antes and "src.ui.triangulacion" not in antes
    assert "from src.ui.triangulacion import render_triangulacion" in despues
```

Run: `.venv/bin/python -m pytest tests/test_navegacion.py tests/test_modo_despliegue.py tests/test_triangulacion_pagina.py -q`
Expected: FAIL. Entre otras, `test_triangulacion_solo_para_investigadores` (no está en `DISPONIBLES`), `test_el_punto_de_entrada_corta_antes_de_importar_lo_demas` (falta la ruta en `main.py`) y las de la página (`ImportError: cannot import name 'triangulacion_investigador' from 'src.ui.views'`).

- [ ] **Step 2: Implementar la página y la vista**

`src/ui/triangulacion.py`:

```python
"""
Página «Triangulación 360» — fase 5: solo investigadores, solo local.

  · Busca los tres archivos (estudiantes, cuidadores y docentes) en la carpeta
    de datos fuente (`core.rutas`). Si falta alguno (por ejemplo, en el
    despliegue del equipo), lo dice con un mensaje fijo y no falla: la capa por
    colegio en el despliegue necesita los agregados publicados de cuidadores,
    que llegan con la fase 4b.
  · Sin la clave local `OBS360_CLAVE_HMAC` no carga y explica qué hacer.
  · Si `estudiantes.ingest` quedó viejo en memoria (sin `clave_nino`), pide
    reiniciar la aplicación en vez de fallar.

Solo se enruta en los modos completo e investigador (`main.py`): el despliegue
público nunca importa este módulo ni `src.triangulacion`.
"""
from __future__ import annotations

import streamlit as st

from src.triangulacion import catalogo as cat


@st.cache_resource(show_spinner="Cargando los tres actores y enlazando díadas…")
def _analisis(firma: tuple):
    from src.triangulacion import pipeline
    return pipeline.cargar_y_analizar()


def render_triangulacion() -> None:
    from src.core.seudonimo import ClaveAusente
    from src.triangulacion import fuentes

    disponibles = fuentes.localizar()
    if not disponibles.completo:
        st.title(f"🔺 {cat.TITULO}")
        st.info(cat.AVISO_DESPLIEGUE, icon="⏳")
        st.caption("Archivos en esta máquina: " + " · ".join(
            f"{actor}: {'sí' if hay else 'no'}"
            for actor, hay in disponibles.presentes().items()))
        return
    try:
        t = _analisis(disponibles.firma())
    except ClaveAusente as exc:
        st.title(f"🔺 {cat.TITULO}")
        st.error(str(exc), icon="🔑")
        return
    except fuentes.ModuloRancio as exc:
        st.title(f"🔺 {cat.TITULO}")
        st.warning(str(exc), icon="🔄")
        return
    except Exception as exc:                               # noqa: BLE001
        st.title(f"🔺 {cat.TITULO}")
        st.error(f"No se pudo armar la triangulación: {exc}")
        return

    from src.ui.views.triangulacion_investigador import render_investigador
    render_investigador(t)
```

`src/ui/views/triangulacion_investigador.py`:

```python
"""
Vista investigador de la Triangulación 360 — Observatorio 360 (fase 5).

Se lee en capas (spec §6): primero el resumen («dónde coinciden» y «dónde hay
tensión»), luego las tablas de cada capa, luego la metodología y la descarga.

No calcula: consume un `pipeline.Triangulacion`, que solo tiene agregados. Los
conteos por debajo de 10 se muestran como «<10» y ninguna tabla lleva
identificadores, seudónimos ni díadas.
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from src.triangulacion import catalogo as cat
from src.triangulacion import enlace as en
from src.triangulacion import exportar as ex

PESTANAS = ["Resumen", "Por colegio", "Por grado", "Enlace de díadas", "Acuerdo SDQ",
            "Malestar no visto", "Apoyo familiar", "Asociaciones", "Metodología", "Exportar"]


def _df(t: pd.DataFrame | None, columnas: list | None = None) -> None:
    t = ex._limpia(t)
    if t.empty:
        st.caption("Sin datos para mostrar.")
        return
    if columnas:
        t = t[[c for c in columnas if c in t.columns]]
    st.dataframe(t, hide_index=True, width="stretch")


def hallazgos(clasificacion: pd.DataFrame, tipo: str) -> pd.DataFrame:
    if clasificacion is None or clasificacion.empty:
        return pd.DataFrame()
    t = clasificacion[clasificacion["clasificacion"] == tipo]
    return t[["agrupacion", "grupo", "par", "d_a", "ic_a", "d_b", "ic_b"]].reset_index(drop=True)


def conteos_actores(t) -> pd.DataFrame:
    conteos = t.capa1.conteos or {}
    colegios = sorted({c for m in conteos.values() for c in m} - set(cat.COLEGIOS_SIN_GRUPO))
    filas = []
    for c in colegios:
        filas.append(dict(
            Colegio=c, Estudiantes=en.conteo_legible(conteos.get(cat.ESTUDIANTE, {}).get(c)),
            Cuidadores=en.conteo_legible(conteos.get(cat.CUIDADOR, {}).get(c)),
            Docentes=en.conteo_legible(conteos.get(cat.DOCENTE, {}).get(c)),
            **{"En la capa 1": "sí" if c in t.capa1.colegios else "no"}))
    return pd.DataFrame(filas)


def _tab_resumen(t) -> None:
    st.info(cat.AVISO_ECOLOGICO.format(n=t.n_colegios))
    c1, c2, c3 = st.columns(3)
    c1.metric("Colegios en la capa 1", t.n_colegios)
    c2.metric("Díadas niño–cuidador", en.conteo_legible(t.diadas.n))
    c3.metric("Familias en las díadas", en.conteo_legible(t.diadas.familias))
    todo = pd.concat([t.capa1.clasificacion, t.capa1.clasificacion_grado], ignore_index=True)
    st.subheader("Dónde coinciden")
    _df(hallazgos(todo, cat.COINCIDENCIA))
    st.subheader("Dónde hay tensión")
    _df(hallazgos(todo, cat.TENSION))
    st.caption(cat.AVISO_CLASIFICACION)
    st.caption(cat.AVISO_TEXTOS)


def _tab_colegio(t) -> None:
    st.caption(cat.AVISO_RESTO)
    st.markdown("**Personas por colegio y actor**")
    _df(conteos_actores(t))
    st.markdown("**Clasificación de los pares**")
    _df(t.capa1.clasificacion)
    st.caption(cat.AVISO_COOCURRENCIA)
    st.markdown("**Cada actor frente al resto del municipio**")
    _df(t.capa1.diferencias)
    for colegio in t.capa1.colegios:
        with st.expander(f"Figura · {colegio}"):
            st.pyplot(ex.figura_capa1(t, colegio))


def _tab_grado(t) -> None:
    st.caption(cat.AVISO_GRADO)
    _df(t.capa1.clasificacion_grado)
    _df(t.capa1.por_grado)


def _tab_enlace(t) -> None:
    st.caption(cat.AVISO_ENLACE)
    _df(en.tabla_calidad(t.enlace))


def _tab_acuerdo(t) -> None:
    st.caption(cat.AVISO_DIADAS)
    st.caption(cat.AVISO_SDQ)
    _df(t.diadas.acuerdo)
    st.caption(cat.AVISO_BLAND_ALTMAN)
    ba = t.diadas.bland_altman
    if not ba.empty:
        sub = st.selectbox("Subescala", list(ba["subescala"].unique()), key="tri_ba")
        st.pyplot(ex.figura_bland_altman(t, sub))
        _df(ba[ba["subescala"] == sub])


def _tab_no_visto(t) -> None:
    st.caption("El niño en banda alta o muy alta de su autoinforme, o con la señal de "
               "malestar, y su cuidador lo ubica en «cercano al promedio». No es un "
               "diagnóstico: indica dónde conversar primero con las familias.")
    _df(t.diadas.no_visto)


def _tab_apoyo(t) -> None:
    st.warning(cat.AVISO_MSPSS)
    _df(t.diadas.apoyo)


def _tab_asociaciones(t) -> None:
    st.caption(cat.AVISO_ASOCIACIONES)
    _df(t.diadas.asociaciones)


def _tab_metodologia(t) -> None:
    st.markdown(ex.metodologia_md(t))


def _tab_exportar(t) -> None:
    st.caption("Todo es agregado: ni filas, ni seudónimos, ni díadas. Nada sube a Supabase.")
    st.download_button("📦 Descargar el paquete de la triangulación (ZIP)",
                       data=ex.paquete_zip(t),
                       file_name=f"triangulacion360_{_dt.date.today().isoformat()}.zip",
                       mime="application/zip", type="primary", width="stretch",
                       key="tri_dl_zip")


def render_investigador(t) -> None:
    st.title(f"🔺 {cat.TITULO}")
    tabs = st.tabs(PESTANAS)
    for tab, fn in zip(tabs, (_tab_resumen, _tab_colegio, _tab_grado, _tab_enlace,
                              _tab_acuerdo, _tab_no_visto, _tab_apoyo, _tab_asociaciones,
                              _tab_metodologia, _tab_exportar)):
        with tab:
            fn(t)
```

- [ ] **Step 3: Navegación**

En `src/core/navegacion.py`, sustituir:

```python
# Las que ya tienen vista. Cuidadores entra en la fase 4a (solo investigadores)
# y Triangulación en la 5.
DISPONIBLES = frozenset({PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CUIDADORES,
                         PAGINA_CHAT, PAGINA_CARGA, PAGINA_TENDENCIAS, PAGINA_REPORTES})
```

por:

```python
# Las que ya tienen vista. Cuidadores entró en la fase 4a y Triangulación en la
# 5, las dos solo para investigadores: Triangulación nunca está en PUBLICAS.
DISPONIBLES = frozenset({PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CUIDADORES,
                         PAGINA_TRIANGULACION, PAGINA_CHAT, PAGINA_CARGA,
                         PAGINA_TENDENCIAS, PAGINA_REPORTES})
```

`PUBLICAS` y `menu()` **no cambian**: Triangulación no está en `PUBLICAS`, así que en comunidad nunca sale.

- [ ] **Step 4: Enrutar en `main.py`, solo después del corte público**

Entre la rama de Cuidadores y la del chat:

```python
elif page == nav.PAGINA_CUIDADORES:
    # Fase 4a: solo la vista de investigadores, con los archivos en local. Nunca
    # se importa en el despliegue público, que se corta arriba.
    from src.ui.cuidadores import render_cuidadores
    render_cuidadores()

elif page == nav.PAGINA_TRIANGULACION:
    # Fase 5: solo investigadores y solo con los archivos en local. Nunca se
    # importa en el despliegue público, que se corta arriba.
    from src.ui.triangulacion import render_triangulacion
    render_triangulacion()

elif page == nav.PAGINA_CHAT:
```

La rama pública de arriba (`if _PUBLICO: …`) **no se toca**.

- [ ] **Step 5: Correr**

Run: `.venv/bin/python -m pytest tests/test_navegacion.py tests/test_modo_despliegue.py tests/test_triangulacion_pagina.py -q`
Expected: `43 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/ui/triangulacion.py src/ui/views/triangulacion_investigador.py \
        src/core/navegacion.py main.py tests/test_triangulacion_pagina.py \
        tests/test_navegacion.py tests/test_modo_despliegue.py
git commit -m "feat(triangulacion): página para investigadores; nunca en el despliegue público" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Datos reales (se omite si falta algún archivo)

**Files:**
- Create: `tests/test_triangulacion_reales.py`

Las cifras esperadas son **agregados** calculados el 8-oct-2026 sobre los archivos reales con este mismo código y una clave de prueba (ver «Observaciones de los datos»). El enlace no depende de la clave: la misma en los dos formularios da las mismas coincidencias. Las comprobaciones de privacidad leen nombres y teléfonos **solo en memoria** y comparan conteos.

- [ ] **Step 1: Escribir las pruebas**

`tests/test_triangulacion_reales.py`:

```python
"""
Triangulación 360 con los archivos reales (se omite si falta alguno).

Solo se comparan AGREGADOS con el recuento del 8-oct-2026 (spec §5.6 y §7:
«recuento de díadas»). Ningún mensaje de fallo puede mostrar un valor
individual: las comprobaciones de privacidad comparan conteos (`assert n == 0`).
"""
import io
import re
import zipfile

import pandas as pd
import pytest

from src.core.texto import norm_txt
from src.triangulacion import enlace as en
from src.triangulacion import exportar as ex
from src.triangulacion import fuentes as fu
from src.triangulacion import pipeline

CLAVE = b"clave-de-prueba-solo-para-tests-0001"
DISP = fu.localizar()
pytestmark = pytest.mark.skipif(not DISP.completo,
                                reason="sin los archivos reales de los tres actores")


@pytest.fixture(scope="module")
def fuentes_reales():
    return fu.cargar(DISP, k=CLAVE)


@pytest.fixture(scope="module")
def tri(fuentes_reales):
    return pipeline.analizar(fuentes_reales, n_boot=50)


def test_actores(fuentes_reales):
    assert len(fuentes_reales.estudiantes) == 1295
    assert fuentes_reales.cuidadores["ID_cuidador"].nunique() == 734
    assert len(fuentes_reales.ninos) == 886
    assert len(fuentes_reales.docentes) == 479


def test_recuento_de_diadas(tri):
    inf = tri.enlace
    assert inf["coincidencias_nombre"] == 209
    assert inf["verificadas"] == 208 and inf["descartadas_colegio_distinto"] == 1
    assert inf["familias"] == 194
    assert inf["por_colegio"]["LauV"] == 184 and inf["por_colegio"]["JJC"] == 19
    assert inf["por_colegio"]["LaBalsa"] < 10 and inf["por_colegio"]["SJMEB"] < 10


def test_calidad_del_enlace(tri):
    inf = tri.enlace
    assert (inf["sexo"]["concordantes"], inf["sexo"]["con_dato"]) == (204, 208)
    assert (inf["edad"]["concordantes"], inf["edad"]["con_dato"]) == (202, 206)
    assert (inf["grado"]["concordantes"], inf["grado"]["con_dato"]) == (203, 208)


def test_capa1_con_los_cuatro_colegios_de_la_spec(tri):
    assert tri.capa1.colegios == ["JJC", "LaBalsa", "LauV", "SJMEB"]
    assert tri.capa1.grados == ["Cuarto", "Quinto", "Sexto", "Séptimo", "Octavo",
                                "Noveno", "Décimo"]


def test_toda_cifra_con_10_o_mas(tri):
    for t in (tri.capa1.diferencias, tri.capa1.por_grado):
        con = t[t["d"].notna()]
        pequenos = int((con["n_grupo"] < 10).sum() + (con["n_resto"] < 10).sum())
        assert pequenos == 0
    for t in (tri.diadas.acuerdo, tri.diadas.apoyo, tri.diadas.no_visto):
        con = t[t["motivo"] == ""]
        assert int((con["familias"] < 10).sum()) == 0


def _prohibidos() -> set[str]:
    """Nombres de estudiantes y de cuidadores e hijos, y teléfonos (solo en memoria)."""
    from src.cuidadores import catalog as cat_cuid
    from src.cuidadores import ingest as ing_cuid
    valores = set()
    for ruta in DISP.estudiantes:
        raw = (pd.read_excel(ruta, dtype=str) if ruta.lower().endswith((".xlsx", ".xls"))
               else pd.read_csv(ruta, dtype=str))
        col = next(c for c in raw.columns if "mi nombre completo es" in norm_txt(c))
        valores |= {str(v).strip() for v in raw[col].dropna() if len(str(v).split()) >= 2}
    raw = ing_cuid.leer(DISP.cuidadores)
    for pos in cat_cuid.COLUMNAS_NOMBRE:
        valores |= {str(v).strip() for v in raw.iloc[:, pos].dropna()
                    if len(str(v).split()) >= 2}
    valores |= {d for d in (norm_txt(v).replace(" ", "") for v in raw.iloc[:, 179].dropna())
                if d.isdigit() and len(d) >= 7}
    return valores


def test_ningun_nombre_telefono_ni_seudonimo_en_la_salida(tri):
    prohibidos = _prohibidos()
    textos = [df.astype(str).to_csv() for df in ex.tablas(tri).values()]
    z = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(tri)))
    textos += [z.read(n).decode("utf-8") for n in z.namelist() if not n.endswith(".png")]
    hallados = sum(1 for t in textos for v in prohibidos if v in t)
    assert hallados == 0
    seudonimos = sum(len(re.findall(r"\b[CEN][0-9a-f]{8}\b", t)) for t in textos)
    assert seudonimos == 0


def test_tabla_de_calidad_legible(tri):
    t = en.tabla_calidad(tri.enlace)
    valores = dict(zip(t["indicador"], t["valor"]))
    assert valores["Díadas en LaBalsa"] == "<10" and valores["Díadas en SJMEB"] == "<10"
```

- [ ] **Step 2: Correr**

Run: `.venv/bin/python -m pytest tests/test_triangulacion_reales.py -q`
Expected: `7 passed` (o `7 skipped` en una máquina sin los archivos).

Si una cifra no coincide, **no** se imprime nada de los archivos para investigarla: se investiga con conteos agregados y, si los archivos cambiaron (una exportación nueva), se actualizan las cifras esperadas en el mismo commit, explicándolo en el mensaje.

- [ ] **Step 3: Commit**

```bash
git add tests/test_triangulacion_reales.py
git commit -m "test(triangulacion): recuento de díadas y capa 1 con los archivos reales" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Documentación

**Files:**
- Modify: `DESPLIEGUE.md`, `ARCHITECTURE.md`

- [ ] **Step 1: `DESPLIEGUE.md`**

En «Dónde viven los datos fuente», después del párrafo de **Cuidadores 360 (fase 4a)**, añadir:

```markdown
**Triangulación 360 (fase 5)** solo funciona en la máquina que tiene los tres
archivos (estudiantes, cuidadores y docentes, de preferencia el codificado por
`scripts/preparar_docentes.py`) y la clave `OBS360_CLAVE_HMAC`. Las díadas
niño–cuidador nunca salen de esa máquina y nada de la triangulación sube a
Supabase. En el despliegue del equipo la página explica que la capa por
colegio necesitará los agregados publicados de cuidadores (fase 4b); en el
público no aparece en el menú ni se importa.
```

- [ ] **Step 2: `ARCHITECTURE.md`** (al final)

````markdown

---

## Módulo Triangulación 360 (fase 5)

Solo investigadores y solo local. Cruza estudiantes, cuidadores y docentes.

```
src/triangulacion/
├── catalogo.py      Constructos por actor, pares del mismo objeto y de
│                    co-ocurrencia, avisos fijos.
├── fuentes.py       Carga local: estudiantes (con el seudónimo «N…» del niño),
│                    cuidadores (fase 4a) y docentes (archivo codificado).
├── estadistica.py   CCI(A,1), kappa ponderado, Bland–Altman, errores agrupados,
│                    bootstrap por familias (numpy/scipy, sin statsmodels).
├── capa1.py         Cada actor frente al resto del municipio, por colegio y
│                    por grado, sobre átomos de la base publicable (§5.1).
├── enlace.py        Díadas: seudónimo HMAC exacto + mismo colegio.
├── diadas.py        Acuerdo SDQ, malestar no visto, apoyo y asociaciones.
├── pipeline.py      Triangulacion: solo agregados.
└── exportar.py      ZIP local: tablas, figuras y metodología fija.
src/ui/triangulacion.py                    Página: archivos, clave, módulo viejo.
src/ui/views/triangulacion_investigador.py Resumen, capas, metodología, ZIP.
```

- **Nada individual.** La tabla de díadas vive solo dentro de
  `pipeline.analizar`; toda cifra exige 10 o más (familias distintas en las
  díadas) y toda proporción, 3 o más casos y no casos, también por resta.
- **Estudiantes no cambia.** `estudiantes.ingest` solo crea `N_hmac` cuando la
  triangulación pasa `clave_nino`; el pipeline y la publicación no lo hacen.
- **Nunca en público.** `PAGINA_TRIANGULACION` no está en `PUBLICAS` y
  `main.py` la enruta después del corte.
````

- [ ] **Step 3: Commit**

```bash
git add DESPLIEGUE.md ARCHITECTURE.md
git commit -m "docs(triangulacion): despliegue y arquitectura de la fase 5" \
  -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Suite completa, producción y no regresión de estudiantes

**Files:** ninguno, salvo que aparezcan fallos.

- [ ] **Step 1: Entorno con Python 3.14 y WeasyPrint**

```bash
[ -x "$VENV314/bin/python" ] || /opt/homebrew/bin/python3.14 -m venv "$VENV314"
"$VENV314/bin/pip" install -q -r requirements.txt pytest pyarrow
"$VENV314/bin/python" -c "import streamlit, pandas, sys; print(sys.version, streamlit.__version__, pandas.__version__)"
```

- [ ] **Step 2: Correr las dos suites**

Run: `.venv/bin/python -m pytest -q`
Expected: `932 passed, 4 skipped` (852 de antes + 80 nuevas: 78 en los archivos nuevos y 2 en `test_navegacion.py`). En una máquina sin los archivos reales se omiten además los 7 de `test_triangulacion_reales.py`.

Run: `"$VENV314/bin/python" -m pytest -q`
Expected: `936 passed`.

- Si hay un error real: corregirlo con prueba y commit propio.
- Si es del entorno: anotarlo en el PR.

- [ ] **Step 3: Estudiantes no cambia**

```bash
git diff --stat feature/fase4a-cuidadores -- src/estudiantes src/cuidadores src/ui/estudiantes.py \
  src/ui/cuidadores.py src/ui/views/estudiantes_comunidad.py src/ui/views/estudiantes_informe.py \
  src/ui/views/estudiantes_investigador.py src/ui/views/estudiantes_alertas.py \
  src/ui/views/cuidadores_investigador.py src/core/colegios.py src/core/modo.py \
  src/core/rutas.py src/core/seudonimo.py src/core/texto.py scripts supabase requirements.txt
.venv/bin/python -m src.estudiantes.publicar --ensayo --salida "$TMPDIR/obs360_lote_despues_5.json" > /dev/null
cmp "$TMPDIR/obs360_lote_antes_5.json" "$TMPDIR/obs360_lote_despues_5.json" && echo "lote de estudiantes idéntico"
```
Expected: el `git diff --stat` lista **solo** `src/estudiantes/ingest.py` y sale `lote de estudiantes idéntico`. Si el `cmp` difiere, parar: algo de esta fase tocó la salida de estudiantes.

- [ ] **Step 4: Commit (solo si hubo correcciones)**

---

### Task 12: Verificación con Playwright (local)

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
| completo (8601) | El menú lateral muestra «Triangulación 360» entre «Cuidadores 360» y «Chat con IA». Al elegirlo: título «Triangulación 360 · solo investigadores» y las 10 pestañas |
| completo, Resumen | Aviso ecológico «Con 4 colegios…»; métricas de colegios, díadas y familias; tablas «Dónde coinciden» y «Dónde hay tensión» |
| completo, Por colegio | Conteos por colegio y actor con «<10» donde corresponde; clasificación de los 10 pares por colegio; diferencias con IC; figura de cada colegio (sin nombres) |
| completo, Por grado | Aviso «los docentes no tienen grado»; solo estudiantes y cuidadores |
| completo, Enlace de díadas | Coincidencias, verificadas, descartes «<10», díadas por colegio («<10» en La Balsa y SJMEB) y tasas de concordancia |
| completo, Acuerdo SDQ | Tabla por subescala; selector de subescala y figura de Bland–Altman **agrupada** (cuadrados con IC, sin nube de puntos) |
| completo, Malestar no visto / Apoyo familiar / Asociaciones | Tablas sin columnas de familia ni casos; aviso del MSPSS; aviso de errores agrupados y sensibilidad LauV |
| completo, Metodología | El texto fijo con las secciones Alcance, Capa 1, Capa 2 y Límites |
| completo, Exportar | El ZIP descarga 10 CSV, las figuras y `metodologia.md`; abrirlos: sin nombres, teléfonos ni seudónimos `C…`/`N…`/`E…` |
| investigador (8602) | «Triangulación 360» en el menú y misma vista |
| investigador sin archivos (8604) | La página muestra el aviso del despliegue y «Estudiantes: no · Cuidadores: no · Docentes: no»; sin errores |
| comunidad (8603) | Ni selector con Triangulación ni mención alguna; Estudiantes funciona como antes |
| todos | Sin excepciones en pantalla; Estudiantes 360 y Cuidadores 360 se ven igual que en la rama de la 4a |

- [ ] **Step 3: Apagar los servidores y borrar `.playwright-mcp/` si se creó**

---

### Task 13: PR (sin fusionar)

- [ ] **Step 1:** `git push -u origin feature/fase5-triangulacion`

- [ ] **Step 2:** `gh pr create --base feature/fase4a-cuidadores --title "Fase 5 · Triangulación 360 (solo investigadores)"`. El cuerpo lleva:

  1. **Resumen.**
     - Qué ve el equipo investigador (capa 1 por colegio y por grado, capa 2 de díadas, ZIP).
     - Privacidad: enlace exacto por seudónimo HMAC con clave local verificado con el colegio, sin coincidencias aproximadas; díadas solo en memoria; toda cifra con ≥ 10 (familias distintas) y proporciones con 3 ≤ k ≤ n − 3; Bland–Altman agrupado.
     - Lo que no hace: nada sube a Supabase; en el despliegue del equipo la página explica que falta la 4b; en comunidad no existe.
     - **Base del PR:** `feature/fase4a-cuidadores` (PR #10). Cuando #10 se fusione: `gh pr edit <número> --base main`.
  2. **Pruebas.**
     - Totales antes (852 passed, 4 skipped en 3.13; 856 en 3.14) y después (932 / 936).
     - Lote de estudiantes idéntico (`cmp`) y `git diff` limitado a `src/estudiantes/ingest.py`.
     - Verificación con Playwright (Task 12).
  3. **Pasos del usuario.** «Reboot app» después de fusionar. No hace falta ningún secreto nuevo: la clave local es la de la 4a y nunca va en un despliegue.
  4. **Decisiones, preguntas abiertas y observaciones de los datos** (las listas de abajo).
  5. Cerrar con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 3:** No fusionar. Lo decide el usuario.

---

## Preguntas abiertas para el equipo (todas tienen un valor provisional en el código)

1. **Clima escolar de los docentes.** El formulario no tiene una escala llamada «clima laboral». Provisional: clima laboral = **apoyo del líder** (CL, 7 ítems HSE) y apoyo percibido = **apoyo de compañeros** (AP, 3 ítems). ¿Prefieren otra combinación de los indicadores HSE (manejo del tiempo, claridad de rol, cambio organizacional, responsabilidad organizacional)?
2. **Desgaste docente.** Provisional: la escala «Desgaste» de 4 ítems (1–7). La alternativa es el BAT de 12 ítems (agotamiento, distancia mental, deterioro cognitivo y emocional). ¿Cuál quieren junto al malestar del niño?
3. **«Malestar que el cuidador no ve».** Provisional: SDQ total del niño en banda alta o muy alta **o** señal de malestar, y SDQ total de padres en «cercano al promedio»; sensibilidad con el SDQ emocional. ¿Esa definición, o solo la señal de malestar, o «ligeramente elevado» también como «visto»?
4. **Primaria en las díadas.** 41 de las 208 díadas son de primaria, que respondió el SDQ por debajo de la edad validada. ¿Las dejamos con el aviso o añadimos una sensibilidad solo con secundaria?
5. **Pesos del kappa.** Provisional: lineales. ¿Prefieren cuadráticos (equivalen al CCI en el límite)?
6. **Asociaciones.** Provisional: SDQ total, internalizante y externalizante del niño con EPDS, PSS, castigo físico y barrio a la vez, controles de sexo y edad. ¿Añadir la señal de malestar como resultado, o el ARI de padres?
7. **Capa 1 en el despliegue del equipo.** Para armarla sin archivos haría falta publicar, por colegio, **medias y DE** de estudiantes (hoy solo se publican bandas y cortes) y los agregados de cuidadores (4b) y de docentes. ¿Lo quieren en el despliegue o basta con la máquina local?
8. **Resto del municipio.** Hoy incluye a los colegios pequeños y, en cuidadores, a quienes escribieron un colegio no reconocido («OTRO»), si su módulo los admite en el total. ¿Prefieren comparar solo contra los colegios publicables?

## Observaciones de los datos (solo agregados, 8-oct-2026)

Calculadas con este código y una clave de prueba; nada individual se imprimió. De los archivos de docentes solo se leyó la fila de encabezados y conteos agregados.

- **Actores:** 1295 estudiantes (943 de secundaria y 352 de primaria); 734 cuidadores distintos, 614 con el hijo 1 en los grados del estudio; 886 niños únicos, 712 en los grados del estudio; 479 docentes.
- **Docentes:** el archivo `Docentes_2026_codificado.xlsx` tiene las mismas 479 filas y columnas que `preparar` aplicado a la exportación cruda. PSS, apoyo del líder, apoyo de compañeros y desgaste están completos en las 479; el bloque de bienestar psicosocial solo en 189 (ola 2025). Por colegio: CND 73, SMR 72, JJC 60, LauV 54, SJMEB 46, DiosCh 37, CdP 28, Fonquetá 27, Bojacá 27, Fagua 19, La Balsa 18, Fusca 17 y 1 que no es colegio (Secretaría de Educación).
- **Capa 1:** los 4 colegios de la spec (JJC, La Balsa, LauV, SJMEB) y los 7 grados del estudio. Cerca de Piedra no entra (menos de 10 cuidadores con hijo en los grados del estudio). En SJMEB, la señal de malestar del estudiante no se muestra (cifras pequeñas). Con el código actual hay 4 «tensiones», todas de clima escolar (la pertenencia de los estudiantes frente al apoyo del líder o de compañeros que reportan los docentes), y ninguna «coincidencia»; los pares de conducta del niño quedan «sin diferencia clara».
- **Enlace:** 209 coincidencias exactas del seudónimo (lo que dice la spec), **208 verificadas con el colegio** y 1 descartada por colegio distinto. Díadas: LauV 184, JJC 19, La Balsa y SJMEB «<10» (la spec, con un primer recuento, decía unas 204, 20, 4 y 3 filas). 194 familias; 167 díadas de secundaria y 41 de primaria. Concordancia: sexo 98,1 %, edad ± 1 año 98,1 % y grado 97,6 %.
- **Díadas (preliminar, n = 206):** el acuerdo del SDQ entre el niño y su cuidador es bajo (CCI entre 0,07 y 0,29; kappa ponderado entre −0,01 y 0,15) y el niño reporta más dificultades que su cuidador (diferencia media del total + 3,6 puntos). «Malestar que el cuidador no ve»: 17,0 % de las díadas [12,5–22,7]; 7 de cada 10 niños con malestar. Ninguna asociación sobrevive a Benjamini–Hochberg; el castigo físico es la más alta (β = 0,37 [0,05; 0,69] sobre el SDQ total con todas las díadas; 0,33 [−0,00; 0,67] solo con LauV).
- **Rendimiento:** la página carga y analiza los tres actores en unos 7 s (500 remuestreos bootstrap).

## Autorrevisión contra la spec

| Spec | Dónde queda |
|---|---|
| §5.6 código en `src/triangulacion/` (puro) y `src/ui/triangulacion.py` | Tasks 2–8 |
| §5.6 capa 1: colegios con ≥ 10 en cada actor (4: LauV, JJC, SJMEB, La Balsa) | `capa1.analizar` (colegios publicables en los tres actores); prueba real |
| §5.6 cuidadores solo de niños en grados del estudio; docentes con `codigo_desde_nombre` | `capa1.marcos`, `fuentes.puntuar_docentes` |
| §5.6 por grado solo estudiantes y cuidadores; la vista lo dice | `capa1.analizar`, `catalogo.AVISO_GRADO`; prueba |
| §5.6 medida en DE individual del actor con IC | `capa1.diferencias_constructo`; prueba con cifras conocidas |
| §5.6 coincidencia / tensión solo en el mismo objeto; PSS cuidadores–docentes co-ocurrencia; demás cruces co-ocurrencia | `catalogo.PARES`, `capa1.clasificar`; pruebas |
| §5.6 aviso fijo: descriptivo y ecológico con 4 colegios | `catalogo.AVISO_ECOLOGICO` en el resumen y la metodología |
| §5.6 despliegue de investigador sin archivos | Mensaje fijo (`AVISO_DESPLIEGUE`); decisión y pregunta abierta 7 |
| §5.6 capa 2: HMAC con clave local en los dos archivos, verificado con el colegio, sin aproximadas | Task 1 (`clave_nino`) y Task 5; pruebas de colegio y de nombre mal escrito |
| §5.6 calidad del enlace: coincidencias, descartes por colegio, sexo y edad ± 1 | `enlace.tabla_calidad` (más grado); prueba real |
| §5.6 acuerdo SDQ: correlación, CCI, diferencia media con Bland–Altman, kappa ponderado con cortes propios | `diadas.acuerdo_sdq`; estadística con valores conocidos |
| §5.6 malestar que el cuidador no ve, % e IC | `diadas.malestar_no_visto`; prueba con cifras conocidas y regla de 3 |
| §5.6 MSPSS de familia por fuente con aviso | `diadas.apoyo_familiar`, `AVISO_MSPSS` |
| §5.6 asociaciones con errores por familia y efecto fijo de colegio; sensibilidad LauV | `diadas.asociaciones`; pruebas |
| §5.6 ZIP local con tablas, figuras y `metodologia.md` fija; nada a Supabase | `exportar`; pruebas de contenido y de importaciones |
| §4 nada individual; mínimo de 10 en cuidadores distintos; nada deducible | Átomos de la capa 1, `estadistica.suficiente` y `partes_seguras`, `Triangulacion` solo agregada; pruebas sintéticas y reales con centinelas |
| §4 el despliegue público no importa los módulos de investigación | `PROHIBIDOS_EN_COMUNIDAD` ampliado y prueba del corte de `main.py` |
| §5.1 base publicable | Los átomos salen de `estudiantes.privacidad` y `cuidadores.privacidad` |
| §6 la triangulación se lee en capas: resumen, tablas, metodología | Orden de las pestañas |
| §7 sintéticos con centinelas, regresión real (recuento de díadas), Playwright con triangulación invisible en comunidad | Tasks 1–9 y 12 |
| §7 estudiantes no cambia | Tasks 1 y 11 (columnas, `git diff` y ensayo byte a byte) |
| §10 sin coincidencias aproximadas ni inferencia multinivel con 4 colegios | Enlace exacto; sin modelos multinivel ni errores por colegio |

## Verificación del plan

El código de las Tasks 1 a 9 se escribió y se probó en una copia del repositorio (worktree en el scratchpad, sobre `1968b81`) antes de escribir este plan, y se pegó aquí sin cambios:

- Python 3.13 (pandas 2.3): **932 passed, 4 skipped** con los archivos reales presentes (852 + 80 nuevas).
- Python 3.14 (pandas 3.0.6): **936 passed**.
- Ensayo de estudiantes: el lote es idéntico byte a byte con y sin el código de la fase 5.
- `AppTest` de la página con los archivos reales y una clave de prueba: 10 pestañas, 12 tablas, sin excepciones, en unos 7 s.
