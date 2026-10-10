"""
Publicación PRIVADA de la Triangulación 360 en Supabase — solo para el equipo.

La triangulación se calcula en la máquina que procesa los formularios (los tres
actores, la clave local y las díadas solo existen allí). Este módulo sube sus
AGREGADOS para que el despliegue privado del equipo (`OBS360_MODO =
"investigador"`) la muestre sin archivos (`triangulacion.lectura`).

QUIÉN LA LEE
Solo el usuario de carga del despliegue privado. La migración
`supabase/migraciones/2026-10-10b-triangulacion-privada.sql` hace que el rol
anónimo (la clave pública) NUNCA lea una corrida ni una fila de triangulación,
aunque esté marcada como publicada (`obs360_interno.es_publica`). Sin esa
migración, la base rechaza el nivel 'triangulacion' y no se sube nada.

QUÉ SUBE (modulo = nivel = "triangulacion")
  · Una fila por fila de cada tabla agregada que tiene cifra: capa 1 por colegio
    (`tri_capa1_diferencias`) y por grado (`tri_capa1_por_grado`), acuerdo SDQ,
    su sensibilidad de concordancia, Bland–Altman AGRUPADO (cada fila es un grupo
    de ≥ 10 díadas de ≥ 10 familias), malestar no visto, apoyo familiar y
    asociaciones. `n` es el n de esa cifra (≥ 10, también lo exige la base) y la
    fila completa va en `detalle.fila`.
  · Una fila `tri_meta` (n = estudiantes analizados): colegios y grados de la
    capa 1, las filas SIN cifra (solo su motivo, sin conteos), la clasificación
    de los pares (derivada de las cifras publicadas), la calidad del enlace y
    las personas por colegio ya legibles (lo pequeño como «<10»), la metodología
    y la versión.
Nunca: filas de personas, díadas, seudónimos, la tabla del enlace, ni un conteo
de 1 a 9 (todo conteo en `detalle` es ≥ 10, o «<10»).

GUARDAS, EN ESTE ORDEN (falla el lote entero)
  1. `estudiantes.publicar.verificar`: n ≥ 10, columnas prohibidas, conteos de
     casos, identificadores en `clave` / `grupo`.
  2. Las de cuidadores (`_problemas_de_contenido`): ninguna clave prohibida ni
     valor con forma de identificador E/C/N o de teléfono en ninguna parte de la
     fila; además, ninguna columna de `exportar.PROHIBIDAS`.
  3. Las propias: nivel y tipo de triangulación, una sola fila `tri_meta`, todo
     conteo del detalle ≥ 10 y a lo sumo `MAX_BINES_BA` grupos de Bland–Altman
     por subescala.
  4. La base: CHECK de n ≥ 10, identificadores y conteos; RLS (anon no escribe
     ni lee triangulación).
  5. La corrida entra OCULTA y solo se abre con todos sus resultados dentro; con
     `--publicar-ya` se despublican las demás corridas DE TRIANGULACIÓN.

USO (en la máquina que procesa, con OBS360_CLAVE_HMAC y la clave service_role)
    python -m src.triangulacion.publicar --ensayo --salida /tmp/lote_tri.json
    python -m src.triangulacion.publicar --notas "primera corrida" --publicar-ya
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import date

import numpy as np
import pandas as pd

from src.estudiantes import publicar as pub_est
from src.triangulacion import catalogo as cat

MODULO = "triangulacion"
NIVEL = "triangulacion"
PREFIJO = "tri_"
TIPO_META = "tri_meta"
FORMATO = 1
ESQUEMA = pub_est.ESQUEMA
TABLA_CORRIDAS = pub_est.TABLA_CORRIDAS
TABLA_RESULTADOS = pub_est.TABLA_RESULTADOS
PublicacionInsegura = pub_est.PublicacionInsegura

# Campos de una fila que son conteos de personas, díadas o familias: ≥ 10 o nada.
CAMPOS_CONTEO = ("n", "n_grupo", "n_resto", "familias")


# Las tablas agregadas que suben fila a fila (las demás van en `tri_meta`).
def _tablas(t) -> dict:
    c, d = t.capa1, t.diadas
    return {
        "capa1_diferencias": c.diferencias, "capa1_por_grado": c.por_grado,
        "diadas_acuerdo": d.acuerdo, "diadas_acuerdo_concordantes": d.acuerdo_concordantes,
        "diadas_bland_altman": d.bland_altman, "diadas_no_visto": d.no_visto,
        "diadas_apoyo": d.apoyo, "diadas_asociaciones": d.asociaciones,
    }


TABLAS = ("capa1_diferencias", "capa1_por_grado", "diadas_acuerdo",
          "diadas_acuerdo_concordantes", "diadas_bland_altman", "diadas_no_visto",
          "diadas_apoyo", "diadas_asociaciones")
COLUMNA_N = {"capa1_diferencias": "n_grupo", "capa1_por_grado": "n_grupo"}
VALOR = {"capa1_diferencias": ("d", "ic_inf", "ic_sup"),
         "capa1_por_grado": ("d", "ic_inf", "ic_sup"),
         "diadas_acuerdo": ("cci", "cci_ic_inf", "cci_ic_sup"),
         "diadas_acuerdo_concordantes": ("cci", "cci_ic_inf", "cci_ic_sup"),
         "diadas_bland_altman": ("dif_media", "ic_inf", "ic_sup"),
         "diadas_no_visto": ("pct_no_visto", "ic_inf", "ic_sup"),
         "diadas_apoyo": ("rho", "rho_ic_inf", "rho_ic_sup"),
         "diadas_asociaciones": ("beta", "ic_inf", "ic_sup")}


# ── valores JSON ────────────────────────────────────────────────────────────
def plano(v):
    """Un valor de una tabla como JSON simple: None, bool, int, float o str."""
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        return f if math.isfinite(f) else None
    if isinstance(v, int):
        return v
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return str(v)


def _registros(df: pd.DataFrame | None) -> list[dict]:
    if df is None or df.empty:
        return []
    return [{str(k): plano(v) for k, v in fila.items()} for fila in df.to_dict("records")]


def _columnas(df: pd.DataFrame | None) -> list[str]:
    return [] if df is None else [str(c) for c in df.columns]


def legible(v):
    """Un conteo para el detalle: el número si es ≥ 10, «<10» si es de 1 a 9, 0 si es 0."""
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    if n >= cat.MIN_GROUP_N:
        return n
    return f"<{cat.MIN_GROUP_N}" if n > 0 else 0


# ── filas ───────────────────────────────────────────────────────────────────
def _limpia(df: pd.DataFrame | None) -> pd.DataFrame | None:
    from src.triangulacion import exportar as ex
    if df is None or df.empty:
        return df
    return df.drop(columns=[c for c in ex.PROHIBIDAS if c in df.columns])


def _clave(tabla: str, fila: dict) -> tuple[str, str, str, str | None]:
    """(clave, escala, agrupación, grupo) legibles para las columnas de la base."""
    if tabla.startswith("capa1_"):
        return (str(fila.get("clave")), str(fila.get("constructo") or fila.get("clave")),
                str(fila.get("agrupacion") or "total"), plano(fila.get("grupo")))
    if tabla in ("diadas_acuerdo", "diadas_acuerdo_concordantes"):
        return str(fila.get("subescala")), str(fila.get("escala")), "total", None
    if tabla == "diadas_bland_altman":
        return (str(fila.get("subescala")), "Bland–Altman agrupado", "grupo_ba",
                str(plano(fila.get("grupo"))))
    if tabla == "diadas_no_visto":
        return str(fila.get("variante")), str(fila.get("variante")), "total", None
    if tabla == "diadas_apoyo":
        return str(fila.get("fuente")), str(fila.get("fuente")), "total", None
    return (f"{fila.get('resultado')} · {fila.get('predictor') or '—'}",
            str(fila.get("resultado")), "muestra", plano(fila.get("muestra")))


def _n_de(tabla: str, fila: dict):
    v = fila.get(COLUMNA_N.get(tabla, "n"))
    return None if v is None else int(v)


def filas_tabla(tabla: str, df: pd.DataFrame | None) -> tuple[list[dict], list[dict]]:
    """(filas para la base, filas sin cifra para `tri_meta`)."""
    con, sin = [], []
    for orden, fila in enumerate(_registros(_limpia(df))):
        n = _n_de(tabla, fila)
        if n is None:
            sin.append(dict(tabla=tabla, orden=orden, fila=fila))
            continue
        clave, escala, agrupacion, grupo = _clave(tabla, fila)
        v, lo, hi = VALOR[tabla]
        con.append(pub_est._fila(NIVEL, PREFIJO + tabla, clave, n, fila.get(v),
                                 escala=escala, agrupacion=agrupacion, grupo=grupo,
                                 ic_inf=fila.get(lo), ic_sup=fila.get(hi),
                                 tabla=tabla, orden=orden, fila=fila))
    return con, sin


def _conteos_tabla(t) -> pd.DataFrame:
    from src.ui.views.triangulacion_investigador import conteos_actores
    return conteos_actores(t)


def fila_meta(t, sin_cifra: list[dict]) -> dict:
    from src.triangulacion import enlace as en
    from src.triangulacion import exportar as ex
    c = t.capa1
    tablas = _tablas(t)
    actores = dict(t.actores or {})
    n = actores.get("Estudiantes", 0)
    detalle = dict(
        formato=FORMATO,
        colegios=[str(x) for x in c.colegios], grados=[str(x) for x in c.grados],
        columnas={k: _columnas(_limpia(df)) for k, df in tablas.items()},
        sin_cifra=sin_cifra,
        clasificacion=_registros(c.clasificacion),
        clasificacion_grado=_registros(c.clasificacion_grado),
        columnas_clasificacion=_columnas(c.clasificacion),
        calidad=_registros(en.tabla_calidad(t.enlace)),
        conteos_actores=_registros(_conteos_tabla(t)),
        actores={str(k): legible(v) for k, v in actores.items()},
        diadas_n=legible(t.diadas.n), diadas_familias=legible(t.diadas.familias),
        metodologia=ex.metodologia_md(t), version=ex.version_txt(t),
    )
    return pub_est._fila(NIVEL, TIPO_META, "triangulacion", int(n or 0), None,
                         escala="Triangulación 360 · metadatos", **detalle)


def aplanar(t) -> list[dict]:
    """Filas agregadas de un `pipeline.Triangulacion` (nunca filas de personas)."""
    if hasattr(t, "fuentes") or hasattr(getattr(t, "diadas", None), "datos"):
        raise PublicacionInsegura("No se publicó nada: el objeto trae datos individuales.")
    filas, sin = [], []
    tablas = _tablas(t)
    for nombre in TABLAS:
        con, sin_t = filas_tabla(nombre, tablas[nombre])
        filas += con
        sin += sin_t
    return [fila_meta(t, sin), *filas]


# ── guardas ─────────────────────────────────────────────────────────────────
def conteos_del_detalle(f: dict):
    """(campo, valor) de cada conteo numérico del detalle de una fila."""
    det = f.get("detalle") or {}
    filas = [det.get("fila") or {}]
    filas += [s.get("fila") or {} for s in det.get("sin_cifra") or []]
    for fila in filas:
        for campo in CAMPOS_CONTEO:
            v = fila.get(campo)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                yield campo, v
    for campo in ("diadas_n", "diadas_familias"):
        v = det.get(campo)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0:
            yield campo, v
    for actor, v in (det.get("actores") or {}).items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0:
            yield f"actores.{actor}", v


def _claves(valor):
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield str(k)
            yield from _claves(v)
    elif isinstance(valor, (list, tuple)):
        for v in valor:
            yield from _claves(v)


def verificar(filas: list[dict]) -> None:
    """Rechaza el lote entero si algo no cumple las reglas de privacidad."""
    from src.cuidadores import publicar as pub_cuid
    from src.triangulacion import exportar as ex
    pub_est.verificar(filas)
    problemas: list[str] = []
    prohibidas = {c.lower() for c in ex.PROHIBIDAS}
    metas = 0
    bines: dict[str, int] = {}
    for i, f in enumerate(filas):
        tipo = str(f.get("tipo", ""))
        if f.get("nivel") != NIVEL or not tipo.startswith(PREFIJO):
            problemas.append(f"fila {i}: no es de triangulación (nivel o tipo)")
        metas += tipo == TIPO_META
        if tipo == PREFIJO + "diadas_bland_altman":
            bines[f["clave"]] = bines.get(f["clave"], 0) + 1
        problemas += pub_cuid._problemas_de_contenido(i, f)
        for k in _claves(f):
            if k.lower() in prohibidas:
                problemas.append(f"fila {i}: contiene la columna prohibida «{k}»")
        for campo, v in conteos_del_detalle(f):
            if v < cat.MIN_GROUP_N:
                problemas.append(f"fila {i} ({tipo}): el conteo «{campo}» es menor que "
                                 f"{cat.MIN_GROUP_N}")
    if metas != 1:
        problemas.append(f"el lote trae {metas} filas {TIPO_META} (debe ser 1)")
    for sub, k in bines.items():
        if k > cat.MAX_BINES_BA:
            problemas.append(f"Bland–Altman {sub}: {k} grupos (máximo {cat.MAX_BINES_BA})")
    if problemas:
        raise PublicacionInsegura(
            f"No se publicó nada. El lote tiene {len(problemas)} problema(s) de "
            "privacidad:\n  - " + "\n  - ".join(problemas[:20])
            + ("\n  … y más" if len(problemas) > 20 else ""))


def version_analisis(t) -> str:
    """Huella de la estructura analizada, no de los datos."""
    partes = [",".join(map(str, t.capa1.colegios)), ",".join(map(str, t.capa1.grados)),
              *(f"{k}:{len(v) if v is not None else 0}" for k, v in _tablas(t).items())]
    huella = hashlib.sha1("|".join(partes).encode()).hexdigest()[:12]
    return f"{date.today().isoformat()}-{huella}"


# ── publicar ────────────────────────────────────────────────────────────────
def publicar(t, notas: str = "", publicar_ya: bool = False, cliente=None) -> dict:
    """Sube el lote: corrida oculta → resultados → (abrir → cerrar las demás)."""
    filas = aplanar(t)
    verificar(filas)
    cli = cliente or pub_est._cliente()
    tabla = lambda nombre: cli.postgrest.schema(ESQUEMA).table(nombre)  # noqa: E731
    corrida = dict(modulo=MODULO, version_analisis=version_analisis(t),
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
                  f"despublicar las demás corridas de «{MODULO}» ({type(exc).__name__}). "
                  f"Despublique a mano: UPDATE obs360.corridas SET publicada = false WHERE "
                  f"modulo = '{MODULO}' AND id <> {corrida_id};", file=sys.stderr)
    return dict(corrida_id=corrida_id, version=corrida["version_analisis"], filas=len(filas),
                publicada=publicada, otras_corridas_despublicadas=otras_despublicadas)


def _resumen(filas: list[dict]) -> None:
    print(f"Lote: {len(filas)} filas agregadas")
    for tipo, cuenta in pd.Series([f["tipo"] for f in filas]).value_counts().items():
        print(f"  {tipo}: {cuenta}")
    print(f"  n mínimo en el lote: {min(f['n'] for f in filas)} "
          f"(el umbral es {cat.MIN_GROUP_N})")
    meta = next((f for f in filas if f["tipo"] == TIPO_META), {})
    print(f"  filas sin cifra (solo motivo, en {TIPO_META}): "
          f"{len((meta.get('detalle') or {}).get('sin_cifra') or [])}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Publica los agregados de la Triangulación 360 (solo para el equipo).")
    p.add_argument("--ensayo", action="store_true",
                   help="no toca la red; deja el lote en un JSON")
    p.add_argument("--salida", default="lote_triangulacion.json", help="JSON del ensayo")
    p.add_argument("--notas", default="", help="nota para la corrida")
    p.add_argument("--publicar-ya", action="store_true",
                   help="abre la corrida (para el equipo) y cierra las demás de triangulación")
    p.add_argument("--desde-storage", action="store_true", help="procesa las versiones activas desidentificadas del almacén de Supabase en vez de los archivos locales (requiere la credencial de carga)")
    args = p.parse_args(argv)

    from src.core.seudonimo import ClaveAusente
    from src.triangulacion import pipeline
    try:
        disp = None
        if args.desde_storage:
            # Solo aquí se habla con el almacén: `fuentes` sigue siendo local puro.
            from src.data.almacen import rutas_desde_storage
            from src.triangulacion import fuentes
            r = rutas_desde_storage(["estudiantes_secundaria", "estudiantes_primaria",
                                     "cuidadores", "docentes"])
            disp = fuentes.Disponibles(
                estudiantes=[x for x in (r["estudiantes_secundaria"], r["estudiantes_primaria"]) if x],
                cuidadores=r["cuidadores"], docentes=r["docentes"])
        t = pipeline.cargar_y_analizar(disp=disp)
    except (ClaveAusente, FileNotFoundError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    filas = aplanar(t)
    try:
        verificar(filas)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    _resumen(filas)
    print(f"  versión: {version_analisis(t)}")
    if args.ensayo:
        with open(args.salida, "w", encoding="utf-8") as fh:
            json.dump(dict(modulo=MODULO, version=version_analisis(t), filas=filas), fh,
                      ensure_ascii=False, indent=1, default=str)
        print(f"✓ Ensayo. Nada se subió. Lote escrito en {args.salida}")
        return 0
    try:
        resumen = publicar(t, notas=args.notas, publicar_ya=args.publicar_ya)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    print(f"✓ Corrida {resumen['corrida_id']} con {resumen['filas']} filas. "
          f"Abierta para el equipo: {resumen['publicada']} (el público nunca la lee).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
