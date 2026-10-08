"""
Genera todos los informes imprimibles de Estudiantes 360 — Observatorio 360.

Un HTML por colegio con base suficiente y uno para la Secretaría, con las mismas
funciones que usa el dashboard. Lee los formularios de la carpeta de datos
fuente; si no están, la corrida publicada en Supabase.

Los informes solo llevan cifras agregadas de grupos con al menos
`catalog.MIN_GROUP_N` estudiantes, así que la carpeta de salida puede
compartirse. Aun así, por defecto se escribe junto a los datos fuente y no en
el repositorio.

Uso:
    python -m scripts.generar_informes_estudiantes [carpeta_salida]
"""
from __future__ import annotations

import os
import sys

from src.core.rutas import carpeta_datos
from src.estudiantes import lectura, pipeline, publicar
from src.estudiantes.ingest import nombre_colegio
from src.ui.views import estudiantes_informe as inf


def cargar() -> dict:
    rutas = pipeline.localizar_formularios(carpeta_datos("estudiantes"))
    if rutas:
        analisis, _ = pipeline.cargar_y_analizar(rutas)
        print(f"Fuente: {len(rutas)} formularios en disco")
        return analisis
    analisis, _, corrida = lectura.cargar_desde_supabase()
    print(f"Fuente: corrida publicada {corrida}")
    return analisis


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    salida = argv[0] if argv else os.path.join(carpeta_datos(), "informes_estudiantes")
    analisis = cargar()
    if not analisis:
        print("No hay resultados de estudiantes.")
        return 1
    # La misma auditoría que antes de publicar (restas de N y cifras que no
    # delatan): si algo falla, no se escribe ningún informe.
    problemas = publicar.verificar_restas(analisis)
    if problemas:
        print(f"✗ No se escribió ningún informe: la auditoría encontró "
              f"{len(problemas)} problema(s) de privacidad:\n  - "
              + "\n  - ".join(problemas[:20]), file=sys.stderr)
        return 2
    os.makedirs(salida, exist_ok=True)
    for codigo in inf.colegios_con_informe(analisis):
        ruta = os.path.join(salida, f"informe_estudiantes_{codigo}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(inf.informe_colegio_html(analisis, codigo))
        print(f"  {nombre_colegio(codigo)} → {ruta}")
    ruta = os.path.join(salida, "informe_estudiantes_secretaria.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(inf.informe_secretaria_html(analisis))
    print(f"  Secretaría → {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
