# Mapa del municipio · Fase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar en Estudiantes 360 (vista comunidad, roles municipio y colegio) un mapa de Chía con los colegios: respuestas recibidas por tramo y dos factores protectores (sentirse parte, apoyo social).

**Architecture:** Paquete nuevo `src/geo/` (datos geográficos, tabla del mapa, auditoría, figuras) y una vista `src/ui/views/estudiantes_mapa.py`. El mapa no calcula estadística: lee `Analisis.muestra`, `Analisis.por_colegio` y `Analisis.descriptivos`, y respeta `grupos_visibles()`. Los módulos nuevos no importan `estudiantes_comunidad` (evita ciclos): la vista de comunidad les pasa `visibles` y `pequenos`.

**Tech Stack:** Python 3.14, Streamlit 1.51, Plotly 6.5 (`go.Scattermap`), matplotlib (figura estática sin red), pytest.

**Alcance:** solo la fase A del diseño `docs/superpowers/specs/2026-10-10-mapa-municipio-design.md`. Las fases B (informes y capa de cuidadores), C (avance de datos), D (video) y E (Supabase) tendrán planes propios.

**Coordinación (diseño §10b):** trabajar en el worktree `SaludOrganizacional-mapa`, rama `feature/mapa-municipio`. Archivos nuevos salvo UNA llamada en `src/ui/views/estudiantes_comunidad.py` (Task 6). No tocar `lectura.py`, `vista_previa.py` ni `supabase/`.

**Cómo correr las pruebas** (el worktree no tiene venv propio):

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional-mapa
../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_<x>.py -q
```

**Ajustes al diseño que este plan fija:**
- La comparación con el municipio (§3.5) se muestra como el valor del municipio junto al del colegio, no como «por encima / por debajo»: el IC por colegio no existe en `por_colegio` y calcularlo aquí rompería la regla «las vistas no calculan».
- `MAPA_CAPAS` por defecto ofrece las tres capas, y `MAPA_CAPA_INICIAL = "respuestas"` es la que se ve al abrir.
- El mapa muestra las respuestas por **tramo** (10–29, 30–99, 100 o más), nunca el número exacto.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `src/geo/__init__.py` | Marca el paquete |
| `src/geo/opciones.py` | Parámetros de presentación y reglas fijas (rol familia nunca; solo capas permitidas) |
| `src/geo/colegios_geo.py` | Carga el CSV de coordenadas y el contorno; devuelve solo puntos verificados y dentro del contorno |
| `src/geo/colegios_geo.csv`, `src/geo/chia_limite.geojson` | Datos (ya existen, sin commitear) |
| `src/geo/mapa_datos.py` | `FilaMapa` y `tabla_mapa()`: una fila por colegio desde un `Analisis` |
| `src/geo/auditoria_mapa.py` | `auditar()`: rechaza capas no permitidas y cifras de grupos no visibles |
| `src/geo/mapa_figura.py` | `figura_interactiva()` (Plotly) y `figura_estatica()` (matplotlib) |
| `src/ui/views/estudiantes_mapa.py` | `render_mapa()`: la sección de Streamlit |
| `tests/mapa_datos_sinteticos.py` | `analisis_sintetico()` para las pruebas |
| `tests/test_mapa_opciones.py`, `test_mapa_geo.py`, `test_mapa_datos.py`, `test_mapa_auditoria.py`, `test_mapa_figura.py`, `test_mapa_vista.py` | Pruebas |
| `requirements.txt` | `plotly>=5.24.0` |

---

### Task 1: Paquete y parámetros

**Files:**
- Create: `src/geo/__init__.py`
- Create: `src/geo/opciones.py`
- Test: `tests/test_mapa_opciones.py`

- [ ] **Step 1: Escribir las pruebas**

```python
"""Parámetros del mapa: lo que el equipo decide y lo que no."""
from src.geo import opciones


def test_por_defecto_ofrece_tres_capas_y_abre_en_respuestas():
    assert opciones.capas_activas() == ["respuestas", "sentirse_parte", "apoyo_social"]
    assert opciones.capa_inicial() == "respuestas"


def test_una_capa_no_permitida_se_ignora(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS", ("respuestas", "sdq_total", "rcads"))
    assert opciones.capas_activas() == ["respuestas"]


def test_sin_capas_validas_queda_respuestas(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS", ("sdq_total",))
    assert opciones.capas_activas() == ["respuestas"]


def test_capa_inicial_invalida_cae_a_la_primera_activa(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS", ("apoyo_social",))
    monkeypatch.setattr(opciones, "MAPA_CAPA_INICIAL", "respuestas")
    assert opciones.capa_inicial() == "apoyo_social"


def test_familia_nunca_ve_el_mapa_aunque_se_configure(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_ROLES", ("familia", "colegio", "municipio"))
    assert opciones.rol_ve_mapa("familia") is False
    assert opciones.rol_ve_mapa("colegio") is True


def test_municipio_y_colegio_ven_el_mapa_por_defecto():
    assert opciones.rol_ve_mapa("municipio") is True
    assert opciones.rol_ve_mapa("colegio") is True
    assert opciones.rol_ve_mapa("otro") is False
```

- [ ] **Step 2: Verificar que falla**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_opciones.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.geo'`

- [ ] **Step 3: Implementar**

`src/geo/__init__.py` (vacío).

`src/geo/opciones.py`:

```python
"""
Parámetros de presentación del mapa — Observatorio 360.

Lo que el equipo decide vive aquí; cambiar un valor es un commit de una línea.
Lo que puede delatar a alguien NO es parámetro: la lista de capas permitidas
(`PERMITIDAS`), que familia no vea el mapa y la auditoría previa están en el
código y en sus pruebas.
"""
from __future__ import annotations

# Capas que se ofrecen. Solo cuentan las de PERMITIDAS; lo demás se ignora.
MAPA_CAPAS = ("respuestas", "sentirse_parte", "apoyo_social")
MAPA_CAPA_INICIAL = "respuestas"
MAPA_MOSTRAR_NOMBRES = True            # rótulo con el nombre junto al punto
MAPA_MOSTRAR_SIN_CIFRA = True          # círculos grises de colegios sin cifra
MAPA_MOSTRAR_CAUSA_SIN_CIFRA = True    # decir por qué no hay cifra
MAPA_MOSTRAR_COMPARACION = True        # valor del municipio junto al del colegio
MAPA_ROLES = ("municipio", "colegio")

# No es un parámetro: las únicas capas que el mapa sabe dibujar. Ninguna es de
# malestar, alertas, SDQ ni RCADS.
PERMITIDAS = ("respuestas", "sentirse_parte", "apoyo_social")


def capas_activas() -> list[str]:
    """Capas ofrecidas, en el orden de PERMITIDAS; «respuestas» si no queda ninguna."""
    pedidas = tuple(MAPA_CAPAS)
    activas = [c for c in PERMITIDAS if c in pedidas]
    return activas or ["respuestas"]


def capa_inicial() -> str:
    activas = capas_activas()
    return MAPA_CAPA_INICIAL if MAPA_CAPA_INICIAL in activas else activas[0]


def rol_ve_mapa(rol: str) -> bool:
    """Familia nunca: no ve desagregación por colegio y el mapa lo es."""
    return rol != "familia" and rol in tuple(MAPA_ROLES)
```

- [ ] **Step 4: Verificar que pasa**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_opciones.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/geo/__init__.py src/geo/opciones.py tests/test_mapa_opciones.py
git commit -m "feat(mapa): parámetros de presentación y reglas fijas" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Carga de coordenadas y contorno

**Files:**
- Create: `src/geo/colegios_geo.py`
- Test: `tests/test_mapa_geo.py`
- Data (ya existen): `src/geo/colegios_geo.csv`, `src/geo/chia_limite.geojson`

- [ ] **Step 1: Escribir las pruebas**

```python
"""Carga de coordenadas: solo puntos verificados y dentro del contorno."""
import json

from src.core import colegios
from src.geo import colegios_geo as cg

CUADRADO = {"type": "FeatureCollection", "features": [{
    "type": "Feature", "properties": {},
    "geometry": {"type": "Polygon",
                 "coordinates": [[[-74.1, 4.8], [-74.0, 4.8], [-74.0, 4.9],
                                  [-74.1, 4.9], [-74.1, 4.8]]]}}]}

CABECERA = "codigo,nombre_oficial,lat,lon,fuente,verificado,verificado_por,fecha,nota\n"


def _archivos(tmp_path, filas: str):
    csv_ = tmp_path / "geo.csv"
    csv_.write_text(CABECERA + filas, encoding="utf-8")
    lim = tmp_path / "limite.geojson"
    lim.write_text(json.dumps(CUADRADO), encoding="utf-8")
    return str(csv_), str(lim)


def test_punto_verificado_y_dentro_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,4.85,-74.05,f,true,p,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert [p.codigo for p in puntos] == ["LauV"]
    assert puntos[0].nombre == colegios.nombre("LauV")
    assert avisos == []


def test_punto_sin_verificar_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,4.85,-74.05,f,false,,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert puntos == []
    assert any("sin verificar" in a for a in avisos)


def test_punto_fuera_del_contorno_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,4.5,-74.05,f,true,p,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert puntos == []
    assert any("fuera del contorno" in a for a in avisos)


def test_codigo_desconocido_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "Sede9,x,4.85,-74.05,f,true,p,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert puntos == []
    assert any("desconocido" in a for a in avisos)


def test_coordenada_ilegible_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,,-74.05,f,true,p,2026-10-10,\n")
    puntos, _ = cg.cargar_puntos(csv_, lim)
    assert puntos == []


def test_sin_contorno_se_dibuja_lo_verificado(tmp_path):
    csv_, _ = _archivos(tmp_path, "LauV,x,4.5,-74.05,f,true,p,2026-10-10,\n")
    puntos, _ = cg.cargar_puntos(csv_, str(tmp_path / "no_existe.geojson"))
    assert [p.codigo for p in puntos] == ["LauV"]


def test_archivo_de_coordenadas_ausente_devuelve_aviso(tmp_path):
    puntos, avisos = cg.cargar_puntos(str(tmp_path / "no.csv"), None)
    assert puntos == [] and avisos


def test_limite_devuelve_anillos_exteriores(tmp_path):
    _, lim = _archivos(tmp_path, "")
    anillos = cg.cargar_limite(lim)
    assert len(anillos) == 1 and anillos[0][0] == [-74.1, 4.8]


def test_limite_ilegible_devuelve_vacio(tmp_path):
    malo = tmp_path / "malo.geojson"
    malo.write_text("{no es json", encoding="utf-8")
    assert cg.cargar_limite(str(malo)) == []


def test_datos_reales_son_coherentes():
    """Cada fila del CSV real tiene un código del repo, fuente y quién la aceptó."""
    import csv
    conocidos = {c for _, c, _ in colegios.COLEGIOS}
    with open(cg.RUTA_CSV, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    assert {r["codigo"] for r in filas} <= conocidos
    assert all(r["fuente"] and r["verificado_por"] for r in filas)
    puntos, _ = cg.cargar_puntos()
    assert len(puntos) >= 10
    assert cg.cargar_limite(), "el contorno del municipio debe cargarse"
```

- [ ] **Step 2: Verificar que falla**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_geo.py -q`
Expected: FAIL con `ImportError: cannot import name 'colegios_geo'`

- [ ] **Step 3: Implementar `src/geo/colegios_geo.py`**

```python
"""
Coordenadas de los colegios y contorno de Chía — Observatorio 360.

Una fila por colegio (código de `core/colegios.py`), nunca por sede. Solo se
dibuja un punto si está marcado `verificado = true`, el código existe y cae
dentro del contorno del municipio (cuando el contorno carga). Lo que no se
dibuja deja un aviso en la lista que devuelve `cargar_puntos`; la vista lo
registra en el log, no lo muestra al público.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass

from src.core import colegios

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_CSV = os.path.join(AQUI, "colegios_geo.csv")
RUTA_LIMITE = os.path.join(AQUI, "chia_limite.geojson")


@dataclass(frozen=True)
class Punto:
    codigo: str
    nombre: str
    lat: float
    lon: float


def cargar_limite(ruta: str | None = None) -> list[list[list[float]]]:
    """Anillos exteriores del municipio, cada uno [[lon, lat], ...]. [] si falla."""
    try:
        with open(ruta or RUTA_LIMITE, encoding="utf-8") as f:
            datos = json.load(f)
        if datos.get("type") == "FeatureCollection":
            geom = datos["features"][0]["geometry"]
        else:
            geom = datos.get("geometry", datos)
        poligonos = ([geom["coordinates"]] if geom["type"] == "Polygon"
                     else geom["coordinates"])
        return [p[0] for p in poligonos]
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return []


def _dentro(lon: float, lat: float, anillos: list) -> bool:
    """Punto en polígono por trazado de rayo, en cualquiera de los anillos."""
    for anillo in anillos:
        dentro = False
        for (x1, y1), (x2, y2) in zip(anillo, anillo[1:]):
            if (y1 > lat) != (y2 > lat) and \
                    lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                dentro = not dentro
        if dentro:
            return True
    return False


def cargar_puntos(ruta_csv: str | None = None,
                  ruta_limite: str | None = None) -> tuple[list[Punto], list[str]]:
    """(puntos que se pueden dibujar, avisos de lo que no)."""
    anillos = cargar_limite(ruta_limite)
    conocidos = {c for _, c, _ in colegios.COLEGIOS}
    puntos: list[Punto] = []
    avisos: list[str] = []
    try:
        with open(ruta_csv or RUTA_CSV, encoding="utf-8", newline="") as f:
            filas = list(csv.DictReader(f))
    except OSError:
        return [], ["No se encontró la tabla de coordenadas de los colegios."]
    for fila in filas:
        codigo = (fila.get("codigo") or "").strip()
        if codigo not in conocidos:
            avisos.append(f"{codigo or '(vacío)'}: código desconocido, no se dibuja.")
            continue
        if (fila.get("verificado") or "").strip().lower() != "true":
            avisos.append(f"{codigo}: sin verificar, no se dibuja.")
            continue
        try:
            lat, lon = float(fila["lat"]), float(fila["lon"])
        except (KeyError, TypeError, ValueError):
            avisos.append(f"{codigo}: coordenada ilegible, no se dibuja.")
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            avisos.append(f"{codigo}: coordenada fuera de rango, no se dibuja.")
            continue
        if anillos and not _dentro(lon, lat, anillos):
            avisos.append(f"{codigo}: cae fuera del contorno del municipio, no se dibuja.")
            continue
        puntos.append(Punto(codigo, colegios.nombre(codigo), lat, lon))
    return puntos, avisos
```

- [ ] **Step 4: Verificar que pasa**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_geo.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add src/geo/colegios_geo.py src/geo/colegios_geo.csv src/geo/chia_limite.geojson tests/test_mapa_geo.py
git commit -m "feat(mapa): coordenadas de colegios y contorno de Chía" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Tabla del mapa

**Files:**
- Create: `tests/mapa_datos_sinteticos.py`
- Create: `src/geo/mapa_datos.py`
- Test: `tests/test_mapa_datos.py`

- [ ] **Step 1: Escribir el Analisis sintético y las pruebas**

`tests/mapa_datos_sinteticos.py`:

```python
"""Un Analisis de secundaria con cuatro colegios para las pruebas del mapa."""
import pandas as pd

from src.estudiantes.pipeline import Analisis


def analisis_sintetico() -> Analisis:
    """LauV 435, JJC 297, SJMEB 63 son visibles; LaBalsa 7 es pequeño."""
    a = Analisis(nivel="secundaria", n=800, datos=pd.DataFrame())
    a.muestra = {"colegio": {"LauV": 435, "JJC": 297, "SJMEB": 63, "LaBalsa": 7}}
    a.por_colegio = pd.DataFrame([
        {"clave": "PSSM_Total", "escala": "Pertenencia", "p": 0.01, "eta2": 0.02,
         "q_bh": 0.02, "n": 795,
         "M·LauV": 3.4, "n·LauV": 435, "M·JJC": 3.1, "n·JJC": 297,
         "M·SJMEB": 3.6, "n·SJMEB": 63},
        {"clave": "MSPSS_Total", "escala": "Apoyo social", "p": 0.02, "eta2": 0.01,
         "q_bh": 0.03, "n": 795,
         "M·LauV": 5.1, "n·LauV": 435, "M·JJC": 4.8, "n·JJC": 297,
         "M·SJMEB": 5.4, "n·SJMEB": 63},
    ])
    a.descriptivos = pd.DataFrame([
        {"clave": "PSSM_Total", "escala": "Pertenencia", "n": 795, "M": 3.3},
        {"clave": "MSPSS_Total", "escala": "Apoyo social", "n": 795, "M": 5.0},
    ])
    return a
```

`tests/test_mapa_datos.py`:

```python
"""La tabla del mapa: una fila por colegio, sin cifras de grupos ocultos."""
import pytest

from src.geo import mapa_datos as md
from src.ui.views.estudiantes_comunidad import grupos_visibles
from tests.mapa_datos_sinteticos import analisis_sintetico

CODIGOS = ["LauV", "JJC", "SJMEB", "LaBalsa", "Bojacá"]


def _filas(capa):
    a = analisis_sintetico()
    visibles, pequenos = grupos_visibles(a, "Colegio")
    return {f.codigo: f for f in md.tabla_mapa(a, capa, CODIGOS, visibles, pequenos)}


def test_el_analisis_sintetico_separa_visibles_y_pequenos():
    visibles, pequenos = grupos_visibles(analisis_sintetico(), "Colegio")
    assert visibles == ["JJC", "LauV", "SJMEB"]
    assert pequenos == ["LaBalsa"]


@pytest.mark.parametrize("n, tramo", [(9, None), (10, "10 a 29"), (29, "10 a 29"),
                                      (30, "30 a 99"), (99, "30 a 99"),
                                      (100, "100 o más"), ("<10", None), (None, None)])
def test_tramos(n, tramo):
    assert md.tramo_de(n) == tramo


def test_capa_respuestas_da_tramo_y_nunca_valor():
    f = _filas("respuestas")
    assert f["LauV"].estado == md.CON_CIFRA and f["LauV"].tramo == "100 o más"
    assert f["SJMEB"].tramo == "30 a 99"
    assert all(x.valor is None for x in f.values())


def test_colegio_pequeno_sale_sin_cifra_ni_tramo():
    for capa in md.CAPAS:
        f = _filas(capa)["LaBalsa"]
        assert f.estado == md.PEQUENA
        assert f.tramo is None and f.valor is None


def test_colegio_sin_formulario_se_distingue_del_pequeno():
    assert _filas("respuestas")["Bojacá"].estado == md.SIN_FORMULARIO


def test_capa_sentirse_parte_da_media_y_referencia_del_municipio():
    f = _filas("sentirse_parte")["LauV"]
    assert f.estado == md.CON_CIFRA
    assert f.valor == pytest.approx(3.4) and f.referencia == pytest.approx(3.3)


def test_capa_apoyo_social_usa_mspss():
    assert _filas("apoyo_social")["JJC"].valor == pytest.approx(4.8)


def test_colegio_visible_sin_valor_en_el_indicador_queda_sin_indicador():
    a = analisis_sintetico()
    a.por_colegio = a.por_colegio.drop(columns=["M·JJC"])
    visibles, pequenos = grupos_visibles(a, "Colegio")
    filas = {f.codigo: f for f in md.tabla_mapa(a, "sentirse_parte", CODIGOS,
                                                visibles, pequenos)}
    assert filas["JJC"].estado == md.SIN_INDICADOR and filas["JJC"].valor is None
    assert filas["JJC"].referencia is None


def test_sin_tabla_por_colegio_no_falla():
    a = analisis_sintetico()
    a.por_colegio = a.por_colegio.iloc[0:0]
    visibles, pequenos = grupos_visibles(a, "Colegio")
    filas = md.tabla_mapa(a, "apoyo_social", CODIGOS, visibles, pequenos)
    assert all(f.valor is None for f in filas)


def test_capa_de_malestar_no_existe():
    a = analisis_sintetico()
    for capa in ("sdq_total", "rcads", "alertas", "muerte"):
        with pytest.raises(ValueError):
            md.tabla_mapa(a, capa, CODIGOS, [], [])
```

- [ ] **Step 2: Verificar que falla**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_datos.py -q`
Expected: FAIL con `ImportError: cannot import name 'mapa_datos'`

- [ ] **Step 3: Implementar `src/geo/mapa_datos.py`**

```python
"""
Tabla del mapa — Observatorio 360.

Una fila por colegio con lo que el mapa dibuja. No calcula estadística: lee de
`Analisis` lo que la plataforma ya muestra (conteo por colegio, medias por
colegio y media del nivel) y respeta los grupos visibles que decide la vista de
comunidad. Nunca lleva el número exacto de respuestas: solo el tramo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.core import colegios

# capa → indicador del catálogo de estudiantes (None: es de cobertura)
CAPAS = {"respuestas": None, "sentirse_parte": "PSSM_Total",
         "apoyo_social": "MSPSS_Total"}
ETIQUETAS_CAPA = {"respuestas": "Respuestas recibidas",
                  "sentirse_parte": "Sentirse parte del colegio",
                  "apoyo_social": "Apoyo social"}
TRAMOS = ((100, "100 o más"), (30, "30 a 99"), (10, "10 a 29"))

CON_CIFRA = "con_cifra"
PEQUENA = "pequena"                  # grupo bajo el mínimo: sin cifra
SIN_FORMULARIO = "sin_formulario"    # el colegio no aparece en la corrida
SIN_INDICADOR = "sin_indicador"      # visible, pero sin cifra de este indicador
ESTADOS = (CON_CIFRA, PEQUENA, SIN_FORMULARIO, SIN_INDICADOR)


@dataclass(frozen=True)
class FilaMapa:
    codigo: str
    nombre: str
    estado: str
    tramo: str | None = None
    valor: float | None = None
    referencia: float | None = None


def _numero(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def tramo_de(n) -> str | None:
    """Tramo de respuestas; None si no es un número o está bajo el mínimo."""
    v = _numero(n)
    if v is None:
        return None
    return next((nombre for corte, nombre in TRAMOS if v >= corte), None)


def _valor_colegio(tabla, clave: str, codigo: str) -> float | None:
    if tabla is None or tabla.empty or "clave" not in tabla.columns:
        return None
    fila = tabla[tabla["clave"] == clave]
    columna = f"M·{codigo}"
    if fila.empty or columna not in fila.columns:
        return None
    return _numero(fila.iloc[0][columna])


def _referencia(analisis, clave: str | None) -> float | None:
    d = getattr(analisis, "descriptivos", None)
    if clave is None or d is None or d.empty or "clave" not in d.columns:
        return None
    fila = d[d["clave"] == clave]
    return None if fila.empty or "M" not in fila.columns else _numero(fila.iloc[0]["M"])


def tabla_mapa(analisis, capa: str, codigos, visibles, pequenos) -> list[FilaMapa]:
    """Una fila por código de `codigos`, en ese orden."""
    if capa not in CAPAS:
        raise ValueError(f"Capa no permitida en el mapa: {capa!r}")
    clave = CAPAS[capa]
    conteos = (getattr(analisis, "muestra", None) or {}).get("colegio") or {}
    tabla = getattr(analisis, "por_colegio", None)
    referencia = _referencia(analisis, clave)
    filas: list[FilaMapa] = []
    for codigo in codigos:
        nombre = colegios.nombre(codigo)
        if codigo in pequenos:
            filas.append(FilaMapa(codigo, nombre, PEQUENA))
        elif codigo not in visibles:
            filas.append(FilaMapa(codigo, nombre, SIN_FORMULARIO))
        elif clave is None:
            filas.append(FilaMapa(codigo, nombre, CON_CIFRA,
                                  tramo=tramo_de(conteos.get(codigo))))
        else:
            valor = _valor_colegio(tabla, clave, codigo)
            if valor is None:
                filas.append(FilaMapa(codigo, nombre, SIN_INDICADOR))
            else:
                filas.append(FilaMapa(codigo, nombre, CON_CIFRA, valor=valor,
                                      referencia=referencia))
    return filas
```

- [ ] **Step 4: Verificar que pasa**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_datos.py -q`
Expected: `17 passed` (8 casos de tramos + 9 pruebas)

- [ ] **Step 5: Commit**

```bash
git add src/geo/mapa_datos.py tests/mapa_datos_sinteticos.py tests/test_mapa_datos.py
git commit -m "feat(mapa): tabla del mapa desde el Analisis, con tramos y sin cifras ocultas" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Auditoría del mapa

**Files:**
- Create: `src/geo/auditoria_mapa.py`
- Test: `tests/test_mapa_auditoria.py`

- [ ] **Step 1: Escribir las pruebas**

```python
"""La auditoría rechaza lo que el mapa nunca debe dibujar."""
import pytest

from src.geo import mapa_datos as md
from src.geo.auditoria_mapa import AuditoriaMapa, auditar

VISIBLES = ["LauV", "JJC"]
PEQUENOS = ["LaBalsa"]


def _f(codigo="LauV", estado=md.CON_CIFRA, **kw):
    return md.FilaMapa(codigo, codigo, estado, **kw)


def test_tabla_correcta_pasa():
    filas = [_f("LauV", tramo="100 o más"), _f("JJC", tramo="30 a 99"),
             _f("LaBalsa", md.PEQUENA), _f("Bojacá", md.SIN_FORMULARIO)]
    auditar(filas, "respuestas", VISIBLES, PEQUENOS)


@pytest.mark.parametrize("capa", ["sdq_total", "rcads", "alertas", "muerte", ""])
def test_capa_de_malestar_se_rechaza(capa):
    with pytest.raises(AuditoriaMapa):
        auditar([], capa, VISIBLES, PEQUENOS)


def test_cifra_de_un_colegio_pequeno_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LaBalsa", md.PEQUENA, valor=3.2)], "sentirse_parte",
                VISIBLES, PEQUENOS)


def test_colegio_pequeno_con_estado_con_cifra_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LaBalsa", md.CON_CIFRA, tramo="10 a 29")], "respuestas",
                VISIBLES, PEQUENOS)


def test_cifra_de_un_colegio_no_visible_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("Fusca", md.CON_CIFRA, tramo="10 a 29")], "respuestas",
                VISIBLES, PEQUENOS)


def test_sin_formulario_con_valor_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("Bojacá", md.SIN_FORMULARIO, tramo="10 a 29")], "respuestas",
                VISIBLES, PEQUENOS)


def test_capa_de_respuestas_no_lleva_valor():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LauV", valor=3.0)], "respuestas", VISIBLES, PEQUENOS)


def test_codigo_que_no_es_un_colegio_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("Samaria", md.SIN_FORMULARIO)], "respuestas", VISIBLES, PEQUENOS)


def test_codigo_repetido_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LauV", tramo="100 o más"), _f("LauV", tramo="100 o más")],
                "respuestas", VISIBLES, PEQUENOS)


def test_estado_desconocido_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LauV", "raro")], "respuestas", VISIBLES, PEQUENOS)
```

- [ ] **Step 2: Verificar que falla**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_auditoria.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.geo.auditoria_mapa'`

- [ ] **Step 3: Implementar `src/geo/auditoria_mapa.py`**

```python
"""
Auditoría del mapa — Observatorio 360.

Última barrera antes de dibujar: si la tabla del mapa trae algo que el mapa
nunca debe mostrar, se levanta `AuditoriaMapa` y la vista no dibuja nada. No
depende de que `mapa_datos` esté bien: lo revisa desde afuera.
"""
from __future__ import annotations

from src.core import colegios
from src.geo import mapa_datos as md


class AuditoriaMapa(ValueError):
    """La tabla del mapa trae algo que no se puede mostrar."""


def auditar(filas, capa: str, visibles, pequenos) -> None:
    if capa not in md.CAPAS:
        raise AuditoriaMapa(f"Capa no permitida en el mapa: {capa!r}")
    conocidos = {c for _, c, _ in colegios.COLEGIOS}
    vistos: set[str] = set()
    for f in filas:
        if f.codigo not in conocidos:
            raise AuditoriaMapa(f"{f.codigo!r} no es un colegio (¿una sede?).")
        if f.codigo in vistos:
            raise AuditoriaMapa(f"{f.codigo}: aparece dos veces.")
        vistos.add(f.codigo)
        if f.estado not in md.ESTADOS:
            raise AuditoriaMapa(f"{f.codigo}: estado desconocido {f.estado!r}.")
        con_dato = f.tramo is not None or f.valor is not None
        if f.codigo in pequenos and (f.estado != md.PEQUENA or con_dato):
            raise AuditoriaMapa(f"{f.codigo}: grupo pequeño con cifra.")
        if f.estado == md.CON_CIFRA and f.codigo not in visibles:
            raise AuditoriaMapa(f"{f.codigo}: cifra de un grupo que no es visible.")
        if f.estado in (md.PEQUENA, md.SIN_FORMULARIO, md.SIN_INDICADOR) and \
                (con_dato or f.referencia is not None):
            raise AuditoriaMapa(f"{f.codigo}: estado sin cifra pero con dato.")
        if capa == "respuestas" and f.valor is not None:
            raise AuditoriaMapa(f"{f.codigo}: la capa de respuestas no lleva valor.")
```

- [ ] **Step 4: Verificar que pasa**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_auditoria.py -q`
Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add src/geo/auditoria_mapa.py tests/test_mapa_auditoria.py
git commit -m "feat(mapa): auditoría previa a dibujar" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Figuras (interactiva y estática)

**Files:**
- Create: `src/geo/mapa_figura.py`
- Test: `tests/test_mapa_figura.py`

- [ ] **Step 1: Escribir las pruebas**

```python
"""Figuras del mapa: interactiva (Plotly) y estática (matplotlib, sin red)."""
import io

import pytest

from src.estudiantes import catalog as cat
from src.geo import mapa_datos as md
from src.geo import mapa_figura as mf
from src.geo import opciones
from src.geo.colegios_geo import Punto

PUNTOS = [Punto("LauV", "Laura Vicuña", 4.86, -74.05),
          Punto("JJC", "José Joaquín Casas", 4.85, -74.06),
          Punto("LaBalsa", "La Balsa", 4.87, -74.03),
          Punto("Bojacá", "Bojacá", 4.86, -74.04)]


def _filas_respuestas():
    return [md.FilaMapa("LauV", "Laura Vicuña", md.CON_CIFRA, tramo="100 o más"),
            md.FilaMapa("JJC", "José Joaquín Casas", md.CON_CIFRA, tramo="30 a 99"),
            md.FilaMapa("LaBalsa", "La Balsa", md.PEQUENA),
            md.FilaMapa("Bojacá", "Bojacá", md.SIN_FORMULARIO)]


def _filas_puntaje():
    return [md.FilaMapa("LauV", "Laura Vicuña", md.CON_CIFRA, valor=3.4, referencia=3.3),
            md.FilaMapa("JJC", "José Joaquín Casas", md.CON_CIFRA, valor=3.1, referencia=3.3),
            md.FilaMapa("LaBalsa", "La Balsa", md.PEQUENA),
            md.FilaMapa("Bojacá", "Bojacá", md.SIN_FORMULARIO)]


def _hover_total(fig) -> str:
    return " ".join(str(t) for tr in fig.data if tr.customdata is not None
                    for t in tr.customdata)


def test_hover_de_respuestas_da_tramo_y_no_numero():
    texto = mf.texto_hover(_filas_respuestas()[0], "respuestas")
    assert "100 o más" in texto and "435" not in texto


def test_hover_de_colegio_pequeno_no_lleva_cifras():
    texto = mf.texto_hover(_filas_respuestas()[2], "respuestas")
    assert cat.CIFRAS_PEQUENAS in texto
    assert not any(c.isdigit() for c in texto)


def test_hover_de_puntaje_incluye_el_municipio_si_esta_activo(monkeypatch):
    f = _filas_puntaje()[0]
    assert "Todo el municipio: 3.30" in mf.texto_hover(f, "sentirse_parte")
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_COMPARACION", False)
    assert "municipio" not in mf.texto_hover(f, "sentirse_parte")


def test_hover_sin_causa_si_el_equipo_la_apaga(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_CAUSA_SIN_CIFRA", False)
    texto = mf.texto_hover(_filas_respuestas()[2], "respuestas")
    assert cat.CIFRAS_PEQUENAS not in texto and "Sin cifras" in texto


def test_interactiva_dibuja_contorno_cifras_y_grises():
    fig = mf.figura_interactiva(_filas_respuestas(), "respuestas", PUNTOS)
    assert len(fig.data) >= 3          # contorno + con cifra + sin cifra
    assert fig.layout.map.style == "open-street-map"


def test_interactiva_sin_grises_si_el_equipo_los_apaga(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_SIN_CIFRA", False)
    fig = mf.figura_interactiva(_filas_respuestas(), "respuestas", PUNTOS)
    hover = _hover_total(fig)
    assert "Laura Vicuña" in hover
    assert "La Balsa" not in hover and "Bojacá" not in hover


def test_interactiva_sin_nombres_no_rotula(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_NOMBRES", False)
    fig = mf.figura_interactiva(_filas_respuestas(), "respuestas", PUNTOS)
    assert all("text" not in (tr.mode or "") for tr in fig.data)


def test_interactiva_de_puntaje_usa_escala_de_un_solo_tono():
    fig = mf.figura_interactiva(_filas_puntaje(), "sentirse_parte", PUNTOS)
    con = [tr for tr in fig.data if tr.marker is not None and tr.marker.showscale]
    assert len(con) == 1 and con[0].marker.colorscale is not None


def test_interactiva_ignora_filas_sin_punto():
    sin_punto = [md.FilaMapa("Fusca", "Fusca", md.CON_CIFRA, tramo="10 a 29")]
    fig = mf.figura_interactiva(sin_punto, "respuestas", PUNTOS)
    assert "Fusca" not in _hover_total(fig)


def test_estatica_se_genera_sin_red_como_png():
    fig = mf.figura_estatica(_filas_respuestas(), "respuestas", PUNTOS)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert buf.getvalue()[:8] == b"\x89PNG\r\n\x1a\n" and len(buf.getvalue()) > 5000


def test_estatica_de_puntaje_tambien_se_genera():
    fig = mf.figura_estatica(_filas_puntaje(), "apoyo_social", PUNTOS)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert len(buf.getvalue()) > 5000
```

- [ ] **Step 2: Verificar que falla**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_figura.py -q`
Expected: FAIL con `ImportError: cannot import name 'mapa_figura'`

- [ ] **Step 3: Implementar `src/geo/mapa_figura.py`**

```python
"""
Figuras del mapa — Observatorio 360.

`figura_interactiva` (Plotly sobre OpenStreetMap) es la de la pantalla.
`figura_estatica` (matplotlib, sin tiles ni red) es la de los PDF y el video.
Las dos dibujan lo mismo: el contorno de Chía y un punto por colegio, con un
solo tono, sin rojo y sin semáforo.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go
from matplotlib import colormaps
from matplotlib.figure import Figure

from src.estudiantes import catalog as cat
from src.geo import colegios_geo
from src.geo import mapa_datos as md
from src.geo import opciones

COLOR_PUNTO = "#1F5F8B"
COLOR_GRIS = "#9AA0A6"
COLOR_LIMITE = "#5F6368"
TAMANOS = {"100 o más": 24, "30 a 99": 17, "10 a 29": 11}
TAMANO_BASE = 16
TAMANO_GRIS = 10
CENTRO_POR_DEFECTO = (4.86, -74.06)


def texto_hover(fila: md.FilaMapa, capa: str) -> str:
    """Texto al pasar el cursor. Nunca lleva el número exacto de respuestas."""
    cabecera = f"<b>{fila.nombre}</b>"
    if fila.estado == md.PEQUENA:
        causa = (cat.CIFRAS_PEQUENAS if opciones.MAPA_MOSTRAR_CAUSA_SIN_CIFRA
                 else "Sin cifras")
        return f"{cabecera}<br>{causa}"
    if fila.estado == md.SIN_FORMULARIO:
        causa = ("Todavía no hay respuestas de este colegio."
                 if opciones.MAPA_MOSTRAR_CAUSA_SIN_CIFRA else "Sin cifras")
        return f"{cabecera}<br>{causa}"
    if fila.estado == md.SIN_INDICADOR:
        return f"{cabecera}<br>Sin cifra para este indicador."
    if capa == "respuestas":
        return f"{cabecera}<br>Respuestas recibidas: {fila.tramo or '10 o más'}"
    texto = f"{cabecera}<br>{md.ETIQUETAS_CAPA[capa]}: {fila.valor:.2f}"
    if opciones.MAPA_MOSTRAR_COMPARACION and fila.referencia is not None:
        texto += f"<br>Todo el municipio: {fila.referencia:.2f}"
    return texto


def _con_punto(filas, puntos):
    por_codigo = {p.codigo: p for p in puntos}
    return [(f, por_codigo[f.codigo]) for f in filas if f.codigo in por_codigo]


def _centro(puntos) -> tuple[float, float]:
    if not puntos:
        return CENTRO_POR_DEFECTO
    return (sum(p.lat for p in puntos) / len(puntos),
            sum(p.lon for p in puntos) / len(puntos))


def _rango(valores) -> tuple[float, float]:
    lo, hi = min(valores), max(valores)
    return (lo, hi) if hi > lo else (lo - 0.5, hi + 0.5)


def figura_interactiva(filas, capa: str, puntos) -> go.Figure:
    pares = _con_punto(filas, puntos)
    fig = go.Figure()
    for anillo in colegios_geo.cargar_limite():
        fig.add_trace(go.Scattermap(
            lon=[x for x, _ in anillo], lat=[y for _, y in anillo], mode="lines",
            line=dict(width=2, color=COLOR_LIMITE), hoverinfo="skip",
            showlegend=False))
    modo = "markers+text" if opciones.MAPA_MOSTRAR_NOMBRES else "markers"
    con = [(f, p) for f, p in pares if f.estado == md.CON_CIFRA]
    if con:
        marcador = dict(size=[TAMANOS.get(f.tramo, TAMANO_BASE) for f, _ in con],
                        color=COLOR_PUNTO, opacity=0.9)
        if capa != "respuestas":
            lo, hi = _rango([f.valor for f, _ in con])
            marcador = dict(size=TAMANO_BASE, color=[f.valor for f, _ in con],
                            colorscale="Blues", cmin=lo, cmax=hi, showscale=True,
                            colorbar=dict(title=md.ETIQUETAS_CAPA[capa], thickness=12),
                            opacity=0.95)
        fig.add_trace(go.Scattermap(
            lon=[p.lon for _, p in con], lat=[p.lat for _, p in con], mode=modo,
            marker=marcador, text=[p.nombre for _, p in con],
            textposition="top right",
            customdata=[texto_hover(f, capa) for f, _ in con],
            hovertemplate="%{customdata}<extra></extra>", showlegend=False))
    sin = [(f, p) for f, p in pares if f.estado != md.CON_CIFRA]
    if sin and opciones.MAPA_MOSTRAR_SIN_CIFRA:
        fig.add_trace(go.Scattermap(
            lon=[p.lon for _, p in sin], lat=[p.lat for _, p in sin], mode=modo,
            marker=dict(size=TAMANO_GRIS, color=COLOR_GRIS, opacity=0.8),
            text=[p.nombre for _, p in sin], textposition="top right",
            customdata=[texto_hover(f, capa) for f, _ in sin],
            hovertemplate="%{customdata}<extra></extra>", showlegend=False))
    lat, lon = _centro(puntos)
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=11.3),
        margin=dict(l=0, r=0, t=0, b=0), height=460, showlegend=False)
    return fig


def figura_estatica(filas, capa: str, puntos) -> Figure:
    """Misma imagen sin tiles: contorno gris claro y puntos, para PDF y video."""
    pares = _con_punto(filas, puntos)
    fig = Figure(figsize=(6.4, 6.0), dpi=150)
    ax = fig.subplots()
    for anillo in colegios_geo.cargar_limite():
        ax.fill([x for x, _ in anillo], [y for _, y in anillo], facecolor="#F1F3F4",
                edgecolor=COLOR_LIMITE, linewidth=1.2)
    con = [(f, p) for f, p in pares if f.estado == md.CON_CIFRA]
    sin = [(f, p) for f, p in pares if f.estado != md.CON_CIFRA]
    if sin and opciones.MAPA_MOSTRAR_SIN_CIFRA:
        ax.scatter([p.lon for _, p in sin], [p.lat for _, p in sin], s=60,
                   color=COLOR_GRIS, alpha=0.8, zorder=3)
    if con:
        if capa == "respuestas":
            ax.scatter([p.lon for _, p in con], [p.lat for _, p in con],
                       s=[TAMANOS.get(f.tramo, TAMANO_BASE) ** 2 for f, _ in con],
                       color=COLOR_PUNTO, alpha=0.9, zorder=4)
        else:
            lo, hi = _rango([f.valor for f, _ in con])
            mapa = colormaps["Blues"]
            colores = [mapa(0.35 + 0.6 * (f.valor - lo) / (hi - lo)) for f, _ in con]
            ax.scatter([p.lon for _, p in con], [p.lat for _, p in con], s=260,
                       color=colores, edgecolors=COLOR_LIMITE, linewidths=0.6, zorder=4)
    if opciones.MAPA_MOSTRAR_NOMBRES:
        for f, p in pares:
            if f.estado == md.CON_CIFRA or opciones.MAPA_MOSTRAR_SIN_CIFRA:
                ax.annotate(p.nombre, (p.lon, p.lat), xytext=(6, 6),
                            textcoords="offset points", fontsize=7, color="#202124")
    lat, _ = _centro(puntos)
    ax.set_aspect(1 / math.cos(math.radians(lat)))
    ax.axis("off")
    fig.tight_layout()
    return fig
```

- [ ] **Step 4: Verificar que pasa**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_figura.py -q`
Expected: `14 passed` (incluye centrado en el contorno, escala que no arranca en blanco y etiquetas con color propio)

- [ ] **Step 5: Commit**

```bash
git add src/geo/mapa_figura.py tests/test_mapa_figura.py
git commit -m "feat(mapa): figuras interactiva y estática del municipio" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: La sección en la vista

**Files:**
- Create: `src/ui/views/estudiantes_mapa.py`
- Modify: `src/ui/views/estudiantes_comunidad.py` (UNA llamada, después de `panel_dibujado = _panel_alertas(a, rol, filtros)`)
- Modify: `requirements.txt` (`plotly>=5.24.0`)
- Test: `tests/test_mapa_vista.py`

- [ ] **Step 1: Escribir las pruebas**

```python
"""La sección del mapa: preparación pura y enganche en la vista de comunidad."""
import inspect

import pytest

from src.geo import auditoria_mapa, opciones
from src.geo.colegios_geo import Punto
from src.ui.views import estudiantes_comunidad as vc
from src.ui.views import estudiantes_mapa as em
from tests.mapa_datos_sinteticos import analisis_sintetico

VISIBLES, PEQUENOS = ["JJC", "LauV", "SJMEB"], ["LaBalsa"]
PUNTOS = [Punto("LauV", "Laura Vicuña", 4.86, -74.05),
          Punto("LaBalsa", "La Balsa", 4.87, -74.03)]


@pytest.fixture(autouse=True)
def _puntos_fijos(monkeypatch):
    monkeypatch.setattr(em.colegios_geo, "cargar_puntos", lambda *a, **k: (PUNTOS, []))


def test_preparar_devuelve_puntos_y_filas_auditadas():
    puntos, filas = em.preparar(analisis_sintetico(), "respuestas", VISIBLES, PEQUENOS)
    assert [p.codigo for p in puntos] == ["LauV", "LaBalsa"]
    assert {f.codigo: f.estado for f in filas} == {"LauV": "con_cifra", "LaBalsa": "pequena"}


def test_preparar_rechaza_una_capa_de_malestar():
    with pytest.raises(ValueError):
        em.preparar(analisis_sintetico(), "sdq_total", VISIBLES, PEQUENOS)


def test_preparar_no_deja_pasar_una_fila_que_falle_la_auditoria(monkeypatch):
    def mala(*a, **k):
        raise auditoria_mapa.AuditoriaMapa("x")
    monkeypatch.setattr(em.auditoria_mapa, "auditar", mala)
    with pytest.raises(auditoria_mapa.AuditoriaMapa):
        em.preparar(analisis_sintetico(), "respuestas", VISIBLES, PEQUENOS)


def test_render_no_dibuja_para_familia():
    assert em.render_mapa(analisis_sintetico(), "familia", VISIBLES, PEQUENOS) is False


def test_render_no_dibuja_si_no_hay_puntos(monkeypatch):
    monkeypatch.setattr(em.colegios_geo, "cargar_puntos", lambda *a, **k: ([], ["x"]))
    assert em.render_mapa(analisis_sintetico(), "municipio", VISIBLES, PEQUENOS) is False


def test_render_no_dibuja_si_el_equipo_quita_el_rol(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_ROLES", ("municipio",))
    assert em.render_mapa(analisis_sintetico(), "colegio", VISIBLES, PEQUENOS) is False


def test_la_vista_de_comunidad_engancha_el_mapa_y_no_se_rompe_si_falla():
    fuente = inspect.getsource(vc.render_comunidad)
    assert "render_mapa" in fuente
    # El mapa es un complemento: si falla, la página sigue.
    antes = fuente.index("render_mapa")
    assert "except" in fuente[antes:antes + 400]


def test_el_mapa_se_dibuja_despues_del_panel_de_alertas_y_antes_de_las_tarjetas():
    fuente = inspect.getsource(vc.render_comunidad)
    assert (fuente.index("_panel_alertas(a, rol, filtros)")
            < fuente.index("render_mapa")
            < fuente.index("tarjetas(a, rol, filtros"))
```

- [ ] **Step 2: Verificar que falla**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_vista.py -q`
Expected: FAIL con `ImportError: cannot import name 'estudiantes_mapa'`

- [ ] **Step 3: Implementar la vista `src/ui/views/estudiantes_mapa.py`**

```python
"""
Sección «Mapa de Chía» de Estudiantes 360 — vista comunidad.

Solo dibuja; no calcula. Recibe del llamador los colegios visibles y pequeños
(`grupos_visibles`) para no importar la vista de comunidad. Si algo falla, el
llamador sigue sin mapa: es un complemento, no la página.
"""
from __future__ import annotations

import logging

import streamlit as st

from src.estudiantes import catalog as cat
from src.geo import auditoria_mapa, colegios_geo, mapa_datos, mapa_figura, opciones

log = logging.getLogger(__name__)

NOTA_LECTURA = ("Los colegios se muestran para conocer dónde hay respuestas y qué "
                "protege a los estudiantes. No es un ranking ni un diagnóstico.")
LEYENDA = {
    "respuestas": "Tamaño del círculo: respuestas recibidas (10 a 29, 30 a 99, "
                  "100 o más). Gris: todavía sin cifras que mostrar.",
    "sentirse_parte": "Más oscuro: mayor puntaje medio de sentirse parte del "
                      "colegio. Gris: todavía sin cifras que mostrar.",
    "apoyo_social": "Más oscuro: mayor puntaje medio de apoyo social. Gris: "
                    "todavía sin cifras que mostrar.",
}


def preparar(analisis, capa: str, visibles, pequenos):
    """(puntos, filas) listos para dibujar; levanta si la auditoría no pasa."""
    puntos, avisos = colegios_geo.cargar_puntos()
    for aviso in avisos:
        log.warning("Mapa: %s", aviso)
    filas = mapa_datos.tabla_mapa(analisis, capa, [p.codigo for p in puntos],
                                  visibles, pequenos)
    auditoria_mapa.auditar(filas, capa, visibles, pequenos)
    return puntos, filas


def render_mapa(analisis, rol: str, visibles, pequenos) -> bool:
    """Dibuja la sección. False si no corresponde (rol, sin puntos o auditoría)."""
    if not opciones.rol_ve_mapa(rol):
        return False
    puntos, _ = colegios_geo.cargar_puntos()
    if not puntos:
        return False
    capas = opciones.capas_activas()
    st.markdown("#### Mapa de Chía")
    if len(capas) > 1:
        capa = st.radio("Mostrar", capas, index=capas.index(opciones.capa_inicial()),
                        format_func=lambda c: mapa_datos.ETIQUETAS_CAPA[c],
                        horizontal=True, key="est_map_capa")
    else:
        capa = capas[0]
    try:
        puntos, filas = preparar(analisis, capa, visibles, pequenos)
    except Exception:                                      # noqa: BLE001
        log.exception("El mapa no se dibuja: la auditoría o la tabla fallaron")
        st.info("El mapa no está disponible en este momento.", icon="ℹ️")
        return False
    st.plotly_chart(mapa_figura.figura_interactiva(filas, capa, puntos),
                    width="stretch", key="est_map_fig")
    st.caption(LEYENDA[capa])
    if pequenos and opciones.MAPA_MOSTRAR_CAUSA_SIN_CIFRA:
        st.caption(cat.CIFRAS_PEQUENAS)
    st.caption(NOTA_LECTURA)
    return True
```

- [ ] **Step 4: Enganchar en `render_comunidad`**

Con Edit, en `src/ui/views/estudiantes_comunidad.py`, justo después de `panel_dibujado = _panel_alertas(a, rol, filtros)` y antes del comentario `# ── 2. tarjetas`:

```python
    # ── 1c. mapa del municipio (src/geo): cobertura y factores protectores
    try:
        from src.ui.views import estudiantes_mapa
        v_mapa, p_mapa = (grupos_visibles(a, "Colegio") if ve_colegios(rol)
                          else ([], []))
        estudiantes_mapa.render_mapa(a, rol, v_mapa, p_mapa)
    except Exception:                                      # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("El mapa falló; la vista sigue sin él")
```

Y en `requirements.txt` cambiar `plotly>=5.18.0` por `plotly>=5.24.0`.

- [ ] **Step 5: Verificar que pasa**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_vista.py -q`
Expected: `8 passed`

- [ ] **Step 6: Commit**

```bash
git add src/ui/views/estudiantes_mapa.py src/ui/views/estudiantes_comunidad.py requirements.txt tests/test_mapa_vista.py
git commit -m "feat(mapa): sección «Mapa de Chía» en la vista comunidad de estudiantes" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Verificación completa

**Files:** ninguno nuevo.

- [ ] **Step 1: Pruebas del mapa y de la vista comunidad juntas**

Run: `../SaludOrganizacional/venv/bin/python -m pytest tests/test_mapa_opciones.py tests/test_mapa_geo.py tests/test_mapa_datos.py tests/test_mapa_auditoria.py tests/test_mapa_figura.py tests/test_mapa_vista.py tests/test_estudiantes_comunidad.py -q`
Expected: todo en verde.

- [ ] **Step 2: Suite completa**

Run: `../SaludOrganizacional/venv/bin/python -m pytest -q -x`
Expected: sin fallos nuevos (más de 1 100 pruebas; algunas se omiten sin los datos reales).

- [ ] **Step 3: Revisión en el navegador, computador y celular**

Arrancar la app desde el worktree (modo comunidad, o el de trabajo local si hay datos):

```bash
cd /Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional-mapa
../SaludOrganizacional/venv/bin/python -m streamlit run main.py --server.port 8599 --server.headless true
```

Con Playwright, abrir `http://localhost:8599`, ir a Estudiantes 360, elegir rol «municipio», y comprobar: el mapa aparece debajo del panel de alertas; el selector ofrece las tres capas; los colegios sin cifra salen grises; con rol «familia» el mapa no aparece; a 390 px de ancho no hay desbordamiento horizontal. Guardar capturas en el directorio temporal, no en el repo.

- [ ] **Step 4: Parar el servidor y dejar el árbol limpio**

Run: `git status --short` (en el worktree)
Expected: vacío.

---

## Autorrevisión

**Cobertura del diseño (§3, §5, §6, §7, §8b):**
- §3.1 ubicación y roles → Task 1 (`rol_ve_mapa`), Task 6 (enganche).
- §3.2 capas → Task 3 (`CAPAS`), Task 5.
- §3.3 lo que nunca se dibuja → Task 3 (capa inexistente), Task 4 (auditoría).
- §3.4 colegios sin cifra y su causa → Task 3 (`PEQUENA` / `SIN_FORMULARIO`), Task 5 (hover).
- §3.5 comparación → ajustada (ver cabecera): valor del municipio junto al del colegio.
- §5 datos geográficos → Task 2.
- §6 componentes → Tasks 2 a 6.
- §7 pruebas → cada task; la regresión con la corrida real queda en el Step 3 de la Task 7.
- §8b parámetros → Task 1 (los de la fase A; los de video llegan con la fase D).
- Fase B (informes, cuidadores), C, D, E → planes propios.

**Consistencia de nombres:** `FilaMapa`, `tabla_mapa`, `tramo_de`, `CAPAS`, `ETIQUETAS_CAPA`, `CON_CIFRA`, `PEQUENA`, `SIN_FORMULARIO`, `SIN_INDICADOR`, `ESTADOS` (Task 3) se usan igual en Tasks 4, 5 y 6. `Punto` y `cargar_puntos`/`cargar_limite` (Task 2) igual en 5 y 6. `render_mapa(analisis, rol, visibles, pequenos)` es la misma firma en la vista y en el enganche.

**Riesgo conocido:** Fusca cae fuera del contorno de OpenStreetMap; `cargar_puntos` la deja sin punto y registra el aviso. Si el equipo confirma otra coordenada, se corrige el CSV sin tocar código.
