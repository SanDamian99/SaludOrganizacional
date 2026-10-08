"""
Genera los informes imprimibles de Cuidadores 360 — Observatorio 360.

Un HTML por colegio con cifras de cuidadores y uno para la Secretaría, con las
mismas funciones que la vista de comunidad. Lee la exportación de «Cuidando al
Cuidador» de la carpeta de datos fuente (con la clave local OBS360_CLAVE_HMAC);
si no está, la corrida publicada en Supabase.

Antes de escribir nada corre la misma auditoría que la publicación
(`cuidadores.publicar.verificar_restas`): con un solo hallazgo no se escribe
ningún informe. Por defecto se escribe junto a los datos fuente, no en el
repositorio.

Uso:
    python -m scripts.generar_informes_cuidadores [carpeta_salida]
"""
from __future__ import annotations

import os
import sys

from src.core.rutas import carpeta_datos
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import cuidadores_informe as inf


def cargar():
    """(análisis preparado o corrida publicada, origen)."""
    from src.cuidadores import comunidad, lectura, pipeline
    ruta = pipeline.localizar_formulario()
    if ruta:
        print("Fuente: formulario en disco")
        return comunidad.preparar(pipeline.cargar_y_analizar(ruta)), "archivos"
    publicado, corrida = lectura.cargar_desde_supabase()
    print(f"Fuente: corrida publicada {corrida.get('id') if corrida else None}")
    return publicado, "supabase"


def main(argv: list[str] | None = None) -> int:
    from src.cuidadores import publicar
    argv = sys.argv[1:] if argv is None else argv
    salida = argv[0] if argv else os.path.join(carpeta_datos(), "informes_cuidadores")
    ac, origen = cargar()
    if ac is None:
        print("No hay resultados de cuidadores.")
        return 1
    if origen == "archivos":
        problemas = publicar.verificar_restas(ac)
        if problemas:
            print(f"✗ No se escribió ningún informe: la auditoría encontró {len(problemas)} "
                  "problema(s) de privacidad:\n  - " + "\n  - ".join(problemas[:20]),
                  file=sys.stderr)
            return 2
    os.makedirs(salida, exist_ok=True)
    for codigo in vc.grupos(ac, "Colegio"):
        ruta = os.path.join(salida, f"informe_cuidadores_{codigo}.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(inf.informe_colegio_html(ac, codigo))
        print(f"  {codigo} → {ruta}")
    ruta = os.path.join(salida, "informe_cuidadores_secretaria.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(inf.informe_secretaria_html(ac))
    print(f"  Secretaría → {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
