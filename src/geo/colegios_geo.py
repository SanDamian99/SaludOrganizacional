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
