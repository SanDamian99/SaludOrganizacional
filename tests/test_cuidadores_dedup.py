"""Cuidadores 360 · deduplicación de cuidadores y de niños (spec §5.5)."""
import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import ingest
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(cs.formulario(), k=K)


@pytest.fixture(scope="module")
def dedup(carga):
    return ingest.deduplicar(carga)


def test_deduplicacion(carga, dedup):
    cuid, ninos, inf = dedup
    assert cuid["ID_cuidador"].is_unique and ninos["ID_nino"].is_unique
    assert inf.respuestas_repetidas_cuidador == 1 and inf.cuidadores_en_dos_olas == 1
    assert inf.mismo_nino_misma_respuesta == 1
    assert inf.mismo_nino_otro_cuidador == 1 and inf.mismo_nino_entre_olas == 1
    assert inf.ninos_unicos == len(ninos) == inf.filas_nino - 3
    assert inf.cuidadores_distintos == len(cuid) == inf.respuestas_validas - 1


def test_el_cuidador_repetido_se_queda_con_la_respuesta_mas_reciente(carga, dedup):
    cuid, _, _ = dedup
    resp = carga.respuestas
    repetido = resp["ID_cuidador"][resp["ID_cuidador"].duplicated()].iloc[0]
    assert cuid.loc[cuid["ID_cuidador"] == repetido, "Ola"].item() == "2026"


def test_el_nino_de_dos_cuidadores_se_queda_con_la_mama(carga, dedup):
    _, ninos, _ = dedup
    n = carga.ninos
    compartido = n.groupby("ID_nino")["ID_cuidador"].nunique()
    nino = compartido[compartido > 1].index[0]
    assert ninos.loc[ninos["ID_nino"] == nino, "Quien"].item() == cat.MAMA


def test_prioridad_ola_luego_quien_luego_primer_envio():
    base = dict(ID_cuidador="C00000001", Quien=cat.MAMA, Colegio="LauV", Grado="Quinto",
                Orden_hijo=1)
    filas = [
        dict(base, ID_nino="N00000001", Ola="2025", ts=pd.Timestamp("2025-09-01"), _fila=0,
             Quien=cat.MAMA, ID_cuidador="C00000001"),
        dict(base, ID_nino="N00000001", Ola="2026", ts=pd.Timestamp("2026-03-02"), _fila=1,
             Quien=cat.OTRO, ID_cuidador="C00000002"),
        dict(base, ID_nino="N00000002", Ola="2026", ts=pd.Timestamp("2026-03-01"), _fila=2,
             Quien=cat.PAPA, ID_cuidador="C00000003"),
        dict(base, ID_nino="N00000002", Ola="2026", ts=pd.Timestamp("2026-03-05"), _fila=3,
             Quien=cat.MAMA, ID_cuidador="C00000004"),
        dict(base, ID_nino="N00000003", Ola="2026", ts=pd.Timestamp("2026-03-01"), _fila=4,
             Quien=cat.PAPA, ID_cuidador="C00000005"),
        dict(base, ID_nino="N00000003", Ola="2026", ts=pd.Timestamp("2026-03-09"), _fila=5,
             Quien=cat.PAPA, ID_cuidador="C00000006"),
    ]
    ninos = pd.DataFrame(filas).assign(Grado_detalle="Quinto")
    resp = ninos.drop(columns=["ID_nino", "Orden_hijo", "Grado_detalle"]).drop_duplicates(
        "ID_cuidador")
    _, u, _ = ingest.deduplicar(ingest.Carga(resp, ninos, ingest.InformeCuidadores()))
    elegido = u.set_index("ID_nino")["ID_cuidador"].to_dict()
    assert elegido == {"N00000001": "C00000002",     # la ola más reciente gana a mamá
                       "N00000002": "C00000004",     # mamá antes que papá
                       "N00000003": "C00000005"}     # el primer envío


def test_filtrar_por_ola_antes_de_deduplicar(carga):
    c25, n25, _ = ingest.deduplicar(carga, "2025")
    assert set(c25["Ola"]) == {"2025"} and set(n25["Ola"]) == {"2025"}
    c26, _, _ = ingest.deduplicar(carga, "2026")
    assert len(c25) + len(c26) >= len(ingest.deduplicar(carga)[0])


def test_tras_deduplicar_sigue_sin_nombres_ni_telefono(dedup):
    cuid, ninos, informe = dedup
    for t in (cuid.astype(str).to_csv(), ninos.astype(str).to_csv(), str(informe.como_dict())):
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in t
    assert cuid["ID_cuidador"].str.fullmatch(r"C[0-9a-f]{8}").all()
    assert ninos["ID_nino"].str.fullmatch(r"N[0-9a-f]{8}").all()


def test_conteos_tras_deduplicar(dedup):
    cuid, ninos, inf = dedup
    assert inf.grados == {"Quinto": 21, "Sexto": 20, cat.FUERA_DE_RANGO: 16, "Décimo": 16,
                          "Cuarto": 16, "Octavo": 14, "Séptimo": 9, "Noveno": 9}
    assert inf.colegios_cuidador == {"LauV": 35, "JJC": 24, "SJMEB": 14, "LaBalsa": 12,
                                     "CdP": 4, "OTRO": 3}
