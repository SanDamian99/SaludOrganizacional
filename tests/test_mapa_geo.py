"""Carga de coordenadas: solo puntos verificados y dentro del contorno."""
import json

from src.core import colegios
from src.geo import colegios_geo as cg

CUADRADO = {"type": "FeatureCollection", "features": [{
    "type": "Feature", "properties": {},
    "geometry": {"type": "Polygon",
                 "coordinates": [[[-74.1, 4.8], [-74.0, 4.8], [-74.0, 4.9],
                                  [-74.1, 4.9], [-74.1, 4.8]]]}}]}

CABECERA = "codigo,nombre_oficial,lat,lon,fuente,verificado,verificado_por,fecha,nota\n"


def _archivos(tmp_path, filas: str):
    csv_ = tmp_path / "geo.csv"
    csv_.write_text(CABECERA + filas, encoding="utf-8")
    lim = tmp_path / "limite.geojson"
    lim.write_text(json.dumps(CUADRADO), encoding="utf-8")
    return str(csv_), str(lim)


def test_punto_verificado_y_dentro_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,4.85,-74.05,f,true,p,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert [p.codigo for p in puntos] == ["LauV"]
    assert puntos[0].nombre == colegios.nombre("LauV")
    assert avisos == []


def test_punto_sin_verificar_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,4.85,-74.05,f,false,,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert puntos == []
    assert any("sin verificar" in a for a in avisos)


def test_punto_fuera_del_contorno_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,4.5,-74.05,f,true,p,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert puntos == []
    assert any("fuera del contorno" in a for a in avisos)


def test_codigo_desconocido_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "Sede9,x,4.85,-74.05,f,true,p,2026-10-10,\n")
    puntos, avisos = cg.cargar_puntos(csv_, lim)
    assert puntos == []
    assert any("desconocido" in a for a in avisos)


def test_coordenada_ilegible_no_se_dibuja(tmp_path):
    csv_, lim = _archivos(tmp_path, "LauV,x,,-74.05,f,true,p,2026-10-10,\n")
    puntos, _ = cg.cargar_puntos(csv_, lim)
    assert puntos == []


def test_sin_contorno_se_dibuja_lo_verificado(tmp_path):
    csv_, _ = _archivos(tmp_path, "LauV,x,4.5,-74.05,f,true,p,2026-10-10,\n")
    puntos, _ = cg.cargar_puntos(csv_, str(tmp_path / "no_existe.geojson"))
    assert [p.codigo for p in puntos] == ["LauV"]


def test_archivo_de_coordenadas_ausente_devuelve_aviso(tmp_path):
    puntos, avisos = cg.cargar_puntos(str(tmp_path / "no.csv"), None)
    assert puntos == [] and avisos


def test_limite_devuelve_anillos_exteriores(tmp_path):
    _, lim = _archivos(tmp_path, "")
    anillos = cg.cargar_limite(lim)
    assert len(anillos) == 1 and anillos[0][0] == [-74.1, 4.8]


def test_limite_ilegible_devuelve_vacio(tmp_path):
    malo = tmp_path / "malo.geojson"
    malo.write_text("{no es json", encoding="utf-8")
    assert cg.cargar_limite(str(malo)) == []


def test_datos_reales_son_coherentes():
    """Cada fila del CSV real tiene un código del repo, fuente y quién la aceptó."""
    import csv
    conocidos = {c for _, c, _ in colegios.COLEGIOS}
    with open(cg.RUTA_CSV, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    assert {r["codigo"] for r in filas} <= conocidos
    assert all(r["fuente"] and r["verificado_por"] for r in filas)
    puntos, _ = cg.cargar_puntos()
    assert len(puntos) >= 10
    assert cg.cargar_limite(), "el contorno del municipio debe cargarse"
