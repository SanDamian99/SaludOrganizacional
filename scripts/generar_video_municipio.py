"""
Genera el video del municipio de Estudiantes 360 — Observatorio 360.

Para la Secretaría de Educación y los rectores. Lee la ÚLTIMA CORRIDA PUBLICADA en
Supabase (lo mismo que ve el público), pasa por la misma auditoría que los
informes y el mapa, y escribe un MP4 horizontal (16:9) y, si el equipo lo deja,
uno cuadrado para el celular. Hasta que `opciones.VIDEO_APROBADO` sea True, el
video lleva el sello BORRADOR y el nombre de archivo lo dice.

Sale a una carpeta fuera del repositorio. El script no publica ni envía nada.

Uso:
    python -m scripts.generar_video_municipio [carpeta_salida] [--local]

`--local` usa los formularios de la carpeta de datos fuente en vez de la corrida
publicada (para ensayar en la máquina que procesa).
"""
from __future__ import annotations

import os
import shutil
import sys

from src.core.rutas import carpeta_datos
from src.estudiantes import lectura, pipeline, publicar
from src.geo import video_municipio as vm


def cargar(local: bool) -> dict:
    if local:
        rutas = pipeline.localizar_formularios(carpeta_datos("estudiantes"))
        if not rutas:
            print("No hay formularios de estudiantes en la carpeta de datos fuente.",
                  file=sys.stderr)
            return {}
        analisis, _ = pipeline.cargar_y_analizar(rutas)
        print(f"Fuente: {len(rutas)} formularios en disco (ensayo local)")
        return analisis
    analisis, _, corrida = lectura.cargar_desde_supabase()
    print(f"Fuente: corrida publicada {corrida['id'] if isinstance(corrida, dict) else corrida}")
    return analisis


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    local = "--local" in argv
    posicionales = [a for a in argv if not a.startswith("--")]
    salida = posicionales[0] if posicionales else os.path.join(carpeta_datos(), "videos")
    if shutil.which("ffmpeg") is None:
        print("Falta ffmpeg en esta máquina.", file=sys.stderr)
        return 3
    analisis = cargar(local)
    if not analisis:
        print("No hay resultados de estudiantes.", file=sys.stderr)
        return 1
    problemas = publicar.verificar_restas(analisis)
    if problemas:
        print(f"✗ No se escribió ningún video: la auditoría encontró {len(problemas)} "
              "problema(s) de privacidad:\n  - " + "\n  - ".join(problemas[:20]),
              file=sys.stderr)
        return 2
    os.makedirs(salida, exist_ok=True)
    if vm.es_borrador():
        print("Aviso: VIDEO_APROBADO está en False: el video sale como BORRADOR.")
    for formato in vm.formatos():
        escenas = vm.construir_escenas(analisis, formato)
        ruta = os.path.join(salida, vm.nombre_archivo(formato))
        vm.escribir_video(escenas, ruta)
        total = sum(e.duracion for e in escenas) - (len(escenas) - 1) * vm.T_CRUCE
        print(f"  {formato}: {total:.0f} s → {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
