"""
Una base `obs360` en memoria para las pruebas de publicar → leer (sin red).

Imita lo que importa del esquema real (supabase/estudiantes_schema.sql):
  · `corridas` con `id` y `creada_en` crecientes y `publicada = false` al entrar;
  · los CHECK de `resultados`: n ≥ 10, nivel en ('secundaria', 'primaria',
    'cuidadores'), ningún identificador ^[ECN][0-9a-f]{8}$ en `clave` ni en
    `grupo`, ningún conteo de casos en `detalle` y alertas con estado solo
    donde hay cifra;
  · RLS: el cliente anónimo no escribe y solo ve la ÚLTIMA corrida publicada
    de cada módulo (`es_ultima_publicada`) y sus resultados;
  · el usuario de carga (`cargador`, migración 2026-10-10) tampoco escribe en
    `corridas` ni en `resultados`, pero lee todas las corridas, publicadas o no.
    `cliente_sin_sesion()` empieza como anónimo y pasa a cargador al iniciar
    sesión con `CREDENCIALES_CARGADOR` (imita `auth.sign_in_with_password`).
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


class _Sesion:
    """Rol con el que consulta un cliente: «servicio», «anon» o «cargador»."""

    def __init__(self, rol: str):
        self.rol = rol


class _Consulta:
    def __init__(self, base: "BaseFalsa", tabla: str, sesion: _Sesion):
        self.b, self.t, self.sesion = base, tabla, sesion
        self.filtros, self.orden, self.tope, self.rango = [], None, None, None
        self.accion, self.valores = "select", None

    @property
    def anon(self) -> bool:
        return self.sesion.rol == "anon"

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
        if self.accion != "select" and self.sesion.rol != "servicio":
            raise PermissionError(f"RLS: el rol {self.sesion.rol} no escribe")
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


CREDENCIALES_CARGADOR = {"email": "cargador@prueba.invalid", "password": "clave-secreta-de-prueba"}


class CredencialesInvalidas(Exception):
    """Lo que lanza gotrue cuando el usuario o la clave no son válidos."""


class BaseFalsa:
    def __init__(self):
        self.tablas: dict[str, list[dict]] = {"corridas": [], "resultados": []}
        self._id = 0
        self.inicios_de_sesion = 0

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

    def cliente(self, anonimo: bool = False, cargador: bool = False):
        """Cliente de servicio (por defecto), anónimo o del usuario de carga."""
        rol = "anon" if anonimo else "cargador" if cargador else "servicio"
        return self._cliente(_Sesion(rol))

    def cliente_sin_sesion(self):
        """Cliente con la clave anon: es cargador solo tras iniciar sesión bien."""
        return self._cliente(_Sesion("anon"))

    def _cliente(self, sesion: _Sesion):
        base = self

        class _Esquema:
            def table(self, nombre):
                return _Consulta(base, nombre, sesion)

        class _Postgrest:
            def schema(self, _):
                return _Esquema()

        class _Auth:
            def sign_in_with_password(self, credenciales):
                base.inicios_de_sesion += 1
                if dict(credenciales) != CREDENCIALES_CARGADOR:
                    raise CredencialesInvalidas(
                        f"Invalid login credentials for {credenciales.get('email')} "
                        f"with {credenciales.get('password')}")
                sesion.rol = "cargador"

        class _Cliente:
            postgrest = _Postgrest()
            auth = _Auth()
        return _Cliente()
