"""
Pruebas del almacén de versiones en Supabase Storage.

Todo corre contra un cliente falso: lo que importa es que el archivo que se
guarda no lleve identificadores, que la ruta y el hash sean los prometidos, que
solo quede una versión activa por conjunto y que, sin credenciales, la app
arranque igual que antes.
"""
import hashlib
from datetime import datetime

import pandas as pd
import pytest

from src.data import almacen


# ─────────────────────────────────────────────────────────────────────────────
# Cliente falso
# ─────────────────────────────────────────────────────────────────────────────

class _Resultado:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """Encadenable como el builder de PostgREST; evalúa en `execute`."""

    def __init__(self, tabla):
        self._tabla = tabla
        self._op = "select"
        self._payload = None
        self._filtros = []
        self._orden = None

    def select(self, *_):
        self._op = "select"; return self

    def insert(self, fila):
        self._op = "insert"; self._payload = fila; return self

    def update(self, cambios):
        self._op = "update"; self._payload = cambios; return self

    def eq(self, col, val):
        self._filtros.append((col, val)); return self

    def order(self, col, desc=False):
        self._orden = (col, desc); return self

    def limit(self, *_):
        return self

    def _coincide(self, fila):
        return all(fila.get(c) == v for c, v in self._filtros)

    def execute(self):
        filas = self._tabla.filas
        if self._op == "insert":
            nueva = {**self._payload, "id": len(filas) + 1,
                     "creada_en": "2026-09-23T10:00:00+00:00"}
            filas.append(nueva)
            return _Resultado([dict(nueva)])
        if self._op == "update":
            tocadas = []
            for f in filas:
                if self._coincide(f):
                    f.update(self._payload); tocadas.append(dict(f))
            return _Resultado(tocadas)
        out = [dict(f) for f in filas if self._coincide(f)]
        if self._orden:
            col, desc = self._orden
            out.sort(key=lambda f: f.get(col) or "", reverse=desc)
        return _Resultado(out)


class _Tabla:
    def __init__(self):
        self.filas = []


class _Bucket:
    def __init__(self):
        self.objetos = {}
        self.subidas = []

    def upload(self, path, file, file_options=None):
        if path in self.objetos:
            raise RuntimeError("Duplicate")
        self.objetos[path] = file
        self.subidas.append((path, file_options))
        return {"Key": path}

    def download(self, path):
        return self.objetos[path]


class _Storage:
    def __init__(self):
        self.buckets = {}

    def from_(self, nombre):
        return self.buckets.setdefault(nombre, _Bucket())


class _Auth:
    def __init__(self):
        self.ingresos = []

    def sign_in_with_password(self, cred):
        self.ingresos.append(cred)
        return {"user": {"email": cred["email"]}}


class ClienteFalso:
    def __init__(self):
        self.auth = _Auth()
        self.storage = _Storage()
        self.tablas = {}
        self.esquemas = []

    def schema(self, nombre):
        self.esquemas.append(nombre)
        return self

    def table(self, nombre):
        return _Consulta(self.tablas.setdefault(nombre, _Tabla()))


@pytest.fixture
def cliente():
    return ClienteFalso()


@pytest.fixture
def alm(cliente, monkeypatch):
    monkeypatch.setattr(almacen, "_ahora", lambda: datetime(2026, 9, 23, 10, 30, 0))
    return almacen.Almacen(url="https://x.supabase.co", key="anon",
                           email="carga@obs360.test", clave="s3cr3t", cliente=cliente)


@pytest.fixture
def df_docentes():
    return pd.DataFrame({
        "Nombre": ["Ana", "Luis"],
        "Correo electrónico": ["a@x.co", "l@x.co"],
        "Documento": [1, 2],
        "Marca temporal": ["2026-01-01", "2026-01-02"],
        "Edad": [34, 41],
        "Sexo": ["Mujer", "Hombre"],
        "Me siento agotado al final del día": ["Siempre", "Nunca"],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Retiro de identificadores
# ─────────────────────────────────────────────────────────────────────────────

def test_sin_identificadores_quita_nombre_y_correo_y_conserva_el_resto(df_docentes):
    limpio = almacen.sin_identificadores(df_docentes)
    assert "Nombre" not in limpio.columns
    assert "Correo electrónico" not in limpio.columns
    assert "Documento" not in limpio.columns
    assert list(limpio.columns) == ["Edad", "Sexo", "Me siento agotado al final del día"]
    assert len(limpio) == 2
    # no modifica el original
    assert "Nombre" in df_docentes.columns


@pytest.mark.parametrize("col", ["nombre", "NOMBRE COMPLETO", "Cédula", "Teléfono",
                                 "celular", "e-mail", "Correo del docente", "id"])
def test_es_identificador_reconoce_variantes(col):
    assert almacen.es_identificador(col)


@pytest.mark.parametrize("col", ["Edad", "Nombre del colegio", "Sexo", "Grado"])
def test_es_identificador_no_se_pasa_de_largo(col):
    # «Nombre del colegio» no identifica a la persona: la regla es exacta.
    assert not almacen.es_identificador(col)


# ─────────────────────────────────────────────────────────────────────────────
# Subida, versiones y activación
# ─────────────────────────────────────────────────────────────────────────────

def test_subir_version_sube_a_la_ruta_esperada_con_hash_correcto(alm, cliente, df_docentes):
    fila = alm.subir_version("docentes", df_docentes, "Datos_Docentes.xlsx", notas="corte sep")

    esperado_csv = almacen.sin_identificadores(df_docentes).to_csv(index=False).encode("utf-8")
    hash_ = hashlib.sha256(esperado_csv).hexdigest()

    assert fila["ruta"] == f"docentes/20260923-103000_{hash_[:8]}.csv"
    assert fila["hash"] == hash_
    assert fila["filas"] == 2 and fila["columnas"] == 3
    assert fila["activa"] is True
    assert fila["subido_por"] == "carga@obs360.test"
    assert fila["notas"] == "corte sep"
    assert set(fila["columnas_retiradas"]) == {"Nombre", "Correo electrónico",
                                                "Documento", "Marca temporal"}

    bucket = cliente.storage.from_("datasets")
    assert bucket.objetos[fila["ruta"]] == esperado_csv
    assert bucket.subidas[0][1]["content-type"] == "text/csv"
    assert bucket.subidas[0][1]["upsert"] == "false"

    assert cliente.auth.ingresos == [{"email": "carga@obs360.test", "password": "s3cr3t"}]
    assert "obs360" in cliente.esquemas
    guardadas = cliente.tablas["conjuntos_versiones"].filas
    assert len(guardadas) == 1 and guardadas[0]["activa"] is True


def test_una_nueva_version_desactiva_la_anterior_del_mismo_conjunto(alm, cliente, df_docentes):
    primera = alm.subir_version("docentes", df_docentes, "v1.xlsx")
    cuidadores = alm.subir_version("cuidadores", df_docentes, "c1.xlsx")
    # segunda versión de docentes con otro contenido
    segunda = alm.subir_version("docentes", df_docentes.assign(Edad=[35, 42]), "v2.xlsx")

    filas = {f["id"]: f for f in cliente.tablas["conjuntos_versiones"].filas}
    assert filas[primera["id"]]["activa"] is False
    assert filas[segunda["id"]]["activa"] is True
    assert filas[cuidadores["id"]]["activa"] is True, "otro conjunto no se toca"

    activa = alm.version_activa("docentes")
    assert activa["id"] == segunda["id"]
    assert len(alm.versiones("docentes")) == 2


def test_activar_vuelve_a_una_version_anterior(alm, cliente, df_docentes):
    primera = alm.subir_version("docentes", df_docentes, "v1.xlsx")
    segunda = alm.subir_version("docentes", df_docentes.assign(Edad=[35, 42]), "v2.xlsx")

    alm.activar(primera["id"])          # sin pasar el conjunto: lo consulta

    filas = {f["id"]: f for f in cliente.tablas["conjuntos_versiones"].filas}
    assert filas[primera["id"]]["activa"] is True
    assert filas[segunda["id"]]["activa"] is False
    assert sum(f["activa"] for f in filas.values()) == 1


def test_descargar_devuelve_dataframe(alm, df_docentes):
    fila = alm.subir_version("docentes", df_docentes, "v1.xlsx")
    df = alm.descargar(fila["ruta"])
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Edad", "Sexo", "Me siento agotado al final del día"]
    assert df["Edad"].tolist() == [34, 41]


def test_conjunto_desconocido_se_rechaza(alm, df_docentes):
    with pytest.raises(ValueError):
        alm.subir_version("estudiantes", df_docentes, "x.csv")


def test_version_activa_none_si_no_hay(alm):
    assert alm.version_activa("docentes") is None
    assert alm.versiones("docentes") == []


# ─────────────────────────────────────────────────────────────────────────────
# Sin credenciales
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sin_credenciales(monkeypatch):
    monkeypatch.setattr(almacen, "_secreto", lambda nombre: None)


def test_sin_credenciales_no_esta_disponible(sin_credenciales):
    assert almacen.credenciales_carga() == (None, None)
    assert almacen.disponible() is False


def test_sin_credenciales_conectar_explica_en_espanol(sin_credenciales):
    with pytest.raises(almacen.AlmacenNoDisponible) as exc:
        almacen.Almacen().conectar()
    assert "OBS360_CARGA_EMAIL" in str(exc.value)
    assert "{" not in str(exc.value), "no debe volcar JSON"


def test_dataset_activo_en_storage_es_none_sin_credenciales(sin_credenciales):
    from src.data import loader
    import streamlit as st
    st.cache_data.clear()
    assert loader.dataset_activo_en_storage("docentes") is None


def test_init_session_state_no_rompe_sin_credenciales(sin_credenciales, monkeypatch):
    """Sin almacén, el arranque cae al disco como siempre y no lanza nada."""
    import streamlit as st
    from src.core import state
    st.cache_data.clear()
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    state.init_session_state()
    assert "df" in st.session_state


def test_etiqueta_storage():
    from src.data.loader import etiqueta_storage
    v = {"creada_en": "2026-09-23T10:00:00+00:00", "filas": 412}
    assert etiqueta_storage(v) == "Docentes · versión 23/09/2026 (412 filas)"
