"""
Colocación de etiquetas del mapa interactivo — Observatorio 360.

Plotly no puede medir el texto, así que aquí se estima en píxeles: cada etiqueta
ocupa `len(nombre) * PX_POR_LETRA` de ancho y `ALTO` de alto. Los puntos se
procesan en el orden recibido (ese orden es la prioridad) y cada uno toma la
primera posición que no choca con una etiqueta ya colocada ni con ningún
círculo. Si ninguna sirve, queda sin etiqueta (`None`): el nombre sigue en el
hover. El mapa estático no usa esto; mide el texto real (ver `mapa_figura`).
"""
from __future__ import annotations

from dataclasses import dataclass

PX_POR_LETRA = 6.6
ALTO = 16.0
HOLGURA = 2.0

# (posición de Plotly, sentido horizontal, sentido vertical); y crece hacia arriba
POSICIONES = (("top right", 1, 1), ("top left", -1, 1),
              ("bottom right", 1, -1), ("bottom left", -1, -1),
              ("middle right", 1, 0), ("middle left", -1, 0),
              ("top center", 0, 1), ("bottom center", 0, -1))
_SENTIDOS = {nombre: (sx, sy) for nombre, sx, sy in POSICIONES}


@dataclass(frozen=True)
class Item:
    codigo: str
    x: float          # píxeles; y crece hacia arriba
    y: float
    nombre: str
    radio: float      # radio del círculo, en píxeles


def caja_circulo(item: Item) -> tuple[float, float, float, float]:
    r = item.radio
    return (item.x - r, item.y - r, item.x + r, item.y + r)


def caja(item: Item, posicion: str) -> tuple[float, float, float, float]:
    """Rectángulo (x0, y0, x1, y1) de la etiqueta en esa posición."""
    sx, sy = _SENTIDOS[posicion]
    d = item.radio + HOLGURA
    ancho = len(item.nombre) * PX_POR_LETRA
    x0 = item.x + d if sx > 0 else item.x - d - ancho if sx < 0 else item.x - ancho / 2
    y0 = item.y + d if sy > 0 else item.y - d - ALTO if sy < 0 else item.y - ALTO / 2
    return (x0, y0, x0 + ancho, y0 + ALTO)


def se_cruzan(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def colocar(items: list[Item]) -> dict[str, str | None]:
    """codigo → posición de Plotly, o None si la etiqueta no cabe sin chocar."""
    circulos = {i.codigo: caja_circulo(i) for i in items}
    ocupado: list[tuple[float, float, float, float]] = list(circulos.values())
    salida: dict[str, str | None] = {}
    for item in items:
        salida[item.codigo] = None
        for nombre, _, _ in POSICIONES:
            c = caja(item, nombre)
            if not any(se_cruzan(c, o) for o in ocupado):
                ocupado.append(c)
                salida[item.codigo] = nombre
                break
    return salida
