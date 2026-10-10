"""
Sube al almacén de Supabase todo lo que usa la plataforma — Observatorio 360.

Cuatro conjuntos, cada uno como nueva versión activa del bucket privado
`datasets` (tabla `obs360.conjuntos_versiones`):

  docentes                 el archivo codificado y sin nombres (lo prepara
                           `scripts/preparar_docentes.py` desde la exportación cruda)
  estudiantes_secundaria   el formulario «¡Cuéntanos sobre tu bienestar emocional!»
  estudiantes_primaria     el formulario «¡Cuéntanos sobre tus emociones!»
  cuidadores               la exportación «Cuidando al Cuidador»

Los tres formularios traen nombres. **No se suben tal cual**: cada nombre se
reemplaza por su seudónimo HMAC con la clave local (`OBS360_CLAVE_HMAC`) y se
vacían teléfono y contacto (`src/data/desidentificar.py`). El almacén vuelve a
verificarlo antes de subir. Procesar la copia da los mismos resultados que el
original, porque la ingesta reconoce los seudónimos.

Uso:
    python -m scripts.subir_datos_fuente            # todo lo que encuentre
    python -m scripts.subir_datos_fuente cuidadores # solo uno
    python -m scripts.subir_datos_fuente --ensayo   # desidentifica y verifica, no sube
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

from src.core.rutas import carpeta_datos
from src.core.texto import norm_txt
from src.data import almacen, desidentificar

EXTENSIONES = (".xlsx", ".xls", ".csv")


def _leer(ruta: str, como_texto: bool = False) -> pd.DataFrame:
    kw = dict(dtype=str) if como_texto else {}
    return (pd.read_excel(ruta, **kw) if ruta.lower().endswith((".xlsx", ".xls"))
            else pd.read_csv(ruta, **kw))


def _mas_reciente(carpeta: str, patron: str) -> str | None:
    if not os.path.isdir(carpeta):
        return None
    candidatos = [os.path.join(carpeta, f) for f in os.listdir(carpeta)
                  if f.lower().endswith(EXTENSIONES) and patron in norm_txt(f)
                  and not f.startswith("~$")]
    return max(candidatos, key=os.path.getmtime) if candidatos else None


def localizar() -> dict[str, str | None]:
    """{conjunto: ruta local} con lo que haya en la carpeta de datos fuente."""
    return {
        "docentes": _mas_reciente(carpeta_datos("docentes"), "codificado"),
        "estudiantes_secundaria": _mas_reciente(
            carpeta_datos("estudiantes"), desidentificar.CONJUNTOS_CRUDOS["estudiantes_secundaria"]),
        "estudiantes_primaria": _mas_reciente(
            carpeta_datos("estudiantes"), desidentificar.CONJUNTOS_CRUDOS["estudiantes_primaria"]),
        "cuidadores": _mas_reciente(
            carpeta_datos("cuidadores"), desidentificar.CONJUNTOS_CRUDOS["cuidadores"]),
    }


def preparar(conjunto: str, ruta: str) -> tuple[pd.DataFrame, str]:
    """(DataFrame listo para subir, resumen de lo que se hizo)."""
    if conjunto == "docentes":
        df = _leer(ruta)
        return df, f"{len(df)} filas codificadas, sin nombres"
    # cuidadores se lee como texto: su ingesta también lo hace así
    df = _leer(ruta, como_texto=(conjunto == "cuidadores"))
    limpio, inf = desidentificar.desidentificar(conjunto, df)
    return limpio, (f"{inf.filas} filas; {inf.nombres_reemplazados} nombres reemplazados por "
                    f"seudónimos en {len(inf.columnas_seudonimizadas)} columna(s); "
                    f"{len(inf.columnas_vaciadas)} columna(s) de contacto vaciadas")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("conjuntos", nargs="*", help="cuáles subir (por defecto, todos)")
    p.add_argument("--ensayo", action="store_true", help="prepara y verifica, no sube")
    p.add_argument("--notas", default="", help="nota para cada versión")
    args = p.parse_args(argv)

    rutas = localizar()
    pedidos = args.conjuntos or list(rutas)
    desconocidos = [c for c in pedidos if c not in rutas]
    if desconocidos:
        print(f"✗ Conjuntos desconocidos: {desconocidos}. Válidos: {list(rutas)}", file=sys.stderr)
        return 2

    a = None
    if not args.ensayo:
        a = almacen.Almacen()
        a.conectar()

    fallos = 0
    for conjunto in pedidos:
        ruta = rutas[conjunto]
        if not ruta:
            print(f"· {conjunto}: no hay archivo en la carpeta de datos fuente, se omite")
            continue
        try:
            df, resumen = preparar(conjunto, ruta)
        except Exception as exc:                            # noqa: BLE001
            fallos += 1
            print(f"✗ {conjunto}: {exc}", file=sys.stderr)
            continue
        print(f"· {conjunto} ← {os.path.basename(ruta)}: {resumen}")
        if args.ensayo:
            continue
        fila = a.subir_version(conjunto, df, os.path.basename(ruta),
                               notas=args.notas or f"Subida con scripts/subir_datos_fuente.py. {resumen}.")
        print(f"  ✓ versión {fila.get('id')} activa → {fila['ruta']} ({fila['filas']} filas)")
    if args.ensayo:
        print("Ensayo: nada se subió.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
