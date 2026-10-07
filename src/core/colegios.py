"""
Tabla única de colegios — Observatorio 360.

Estudiantes, cuidadores y la triangulación reconocen el colegio con estas
reglas. La unidad es el colegio; la sede es un detalle. Docentes conserva los
nombres que ya muestra (scripts/preparar_docentes.py) y usa
`codigo_desde_nombre` solo para unirse con los demás actores.
"""
from __future__ import annotations

from src.core.texto import norm_txt

# (fragmentos normalizados, código, nombre). El orden importa: lo más específico
# primero. «IE Bojacá - IE José Joaquín Casas» es Bojacá.
COLEGIOS = [
    (("bojac",), "Bojacá", "Bojacá"),
    (("laura", "vicuna"), "LauV", "Laura Vicuña"),
    (("joaquin", "jj casas"), "JJC", "José Joaquín Casas"),
    (("balsa",), "LaBalsa", "La Balsa"),
    (("josemaria", "jose maria", "escriva", "escriba", "balaguer"), "SJMEB",
     "San Josemaría Escrivá de Balaguer"),
    (("cerca",), "CdP", "Cerca de Piedra"),
    (("diosa",), "DiosCh", "Diosa Chía"),
    (("fagua",), "Fagua", "Fagua"),
    (("fonquet",), "Fonquetá", "Fonquetá"),
    (("fusca",), "Fusca", "Fusca"),
    (("tiquiza",), "Tiquiza", "Tiquiza"),
    (("diversificado", "conaldi", "conadi", "santa luc", "campincito"), "CND",
     "Colegio Nacional Diversificado"),
    (("santa maria", "stmr"), "SMR", "Santa María del Río"),
]

SEDES = [
    ("samaria", "Samaria"), ("principal", "Principal"), ("preescolar", "Preescolar"),
    ("calahorra", "Mercedes de Calahorra"), ("polideportivo", "Polideportivo"),
    ("tiquiza", "Tiquiza"), ("mercedes", "Mercedes de Calahorra"),
    ("santa luc", "Santa Lucía"), ("campincito", "Campincito"), ("cerro", "El Cerro"),
]


def normalizar(texto) -> tuple[str, str, str]:
    """(código, nombre legible, sede). ('OTRO', texto, sede) si no se reconoce."""
    s = norm_txt(texto)
    if not s:
        return "SIN_DATO", "Sin dato", ""
    sede = next((nombre for frag, nombre in SEDES if frag in s), "")
    for fragmentos, codigo, nombre in COLEGIOS:
        if any(f in s for f in fragmentos):
            return codigo, nombre, sede
    return "OTRO", str(texto).strip(), sede


def nombre(codigo: str) -> str:
    """Nombre legible de un código; el propio código si no se conoce."""
    return next((n for _, c, n in COLEGIOS if c == codigo), str(codigo))


def codigo_desde_nombre(nombre_legible: str) -> str:
    """Código de colegio para un nombre como los que guarda docentes."""
    return normalizar(nombre_legible)[0]
