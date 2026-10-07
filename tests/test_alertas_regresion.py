"""
Lo que ya se publicaba no cambia con las alertas (spec §7, «No regresión de pantallas»).

`tests/fixtures/lote_sintetico_antes_de_alertas.json` se generó con el código
anterior a la fase 3 (Task 0 del plan) sobre formularios sintéticos de los dos
niveles. Después de la fase 3, el lote sin las filas nuevas («alerta…») debe ser
idéntico. Únicas diferencias admitidas: los valores suprimidos de las columnas
nuevas de señal (`ALERTA_*`) dentro de `muestra.suprimidos`, y el último dígito
de los flotantes (se redondean a 9 cifras significativas: pandas 3 y numpy
pueden cambiarlo entre versiones).
"""
import json
import os

from src.estudiantes import ingest, pipeline, publicar, scoring

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "lote_sintetico_antes_de_alertas.json")


def _formularios():
    from tests.test_estudiantes_comunidad import _formulario
    sec = _formulario()
    pri = _formulario().drop(columns=[c for c in sec.columns if c.startswith("RCADS")])
    pri["Estoy en grado"] = ["Cuarto" if i % 2 else "Quinto" for i in range(len(pri))]
    pri["Tengo:"] = [f"{9 + i % 3} años" for i in range(len(pri))]
    pri["Mi nombre completo es:"] = [f"Menor Apellido {i}" for i in range(len(pri))]
    return sec, pri


def lote_actual() -> list[dict]:
    sec, pri = _formularios()
    bruto, informes = ingest.cargar_varios([sec, pri])
    puntuado = scoring.puntuar(bruto)
    analisis = {inf.nivel: pipeline.analizar(puntuado, inf.nivel, n_boot=20,
                                             avisos=list(inf.avisos))
                for inf in informes}
    return publicar.aplanar(analisis) + publicar.aplanar_ingesta(informes)


def _redondear(v):
    """Flotantes a 9 cifras significativas, en cualquier nivel de anidación."""
    if isinstance(v, float):
        return float(f"{v:.9g}")
    if isinstance(v, dict):
        return {k: _redondear(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_redondear(x) for x in v]
    return v


def normalizar(filas: list[dict]) -> list[dict]:
    """Quita lo nuevo de la fase 3, redondea y ordena, para comparar lotes."""
    salida = []
    for f in filas:
        if str(f["tipo"]).startswith("alerta"):
            continue
        f = json.loads(json.dumps(f, ensure_ascii=False, default=str))
        if f["tipo"] == "muestra":
            m = f["detalle"].get("muestra") or {}
            m["suprimidos"] = {k: v for k, v in (m.get("suprimidos") or {}).items()
                               if not str(k).startswith("ALERTA_")}
        salida.append(_redondear(f))
    return sorted(salida, key=lambda f: json.dumps(f, sort_keys=True, ensure_ascii=False))


def _texto(filas) -> str:
    return json.dumps(filas, sort_keys=True, ensure_ascii=False)


def test_lo_que_ya_se_publicaba_no_cambia():
    with open(FIXTURE, encoding="utf-8") as fh:
        antes = json.load(fh)
    assert _texto(normalizar(lote_actual())) == _texto(antes)
