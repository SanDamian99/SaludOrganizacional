"""Cuidadores 360 · auditoría de lo que se publica (fase 4b, spec §4, §5.1 y §5.4)."""
import numpy as np
import pandas as pd

from src.cuidadores import auditoria
from src.cuidadores import catalog as cat
from src.estudiantes import privacidad as priv
from src.estudiantes import supresion
from tests import cuidadores_comunidad_datos as datos


def test_lo_preparado_pasa_la_auditoria():
    assert auditoria.auditar(datos.preparado().marcos) == []


def test_la_resta_cuenta_cuidadores_distintos_no_filas():
    """Un resto de 12 filas de solo 3 cuidadores (hermanos) es un hallazgo."""
    filas = []
    for i in range(20):
        filas.append(dict(ID_cuidador=f"A{i}", Colegio="A", Grado="Quinto", SDQ_Total=10.0))
    for i in range(12):
        filas.append(dict(ID_cuidador=f"R{i % 3}", Colegio="B", Grado="Quinto", SDQ_Total=10.0))
    d = pd.DataFrame(filas)
    base = priv.Base(n_total=len(d))
    base.celdas = {"A|Quinto": d.index[d["Colegio"] == "A"]}
    base.colegios = {"A": base.celdas["A|Quinto"]}
    base.grados = {"Quinto": d.index}                # el grado incluye el resto de B
    base.nivel = d.index
    problemas = auditoria.auditar_restas(d, base, ["SDQ_Total"])
    assert problemas and all("cuidadores distintos" in p for p in problemas)
    # contando filas (como estudiantes) no se vería
    assert priv.auditar(d, base, ["SDQ_Total"]) == []


def test_una_proporcion_destapada_es_un_hallazgo():
    ac = datos.preparado()
    a = ac.cuidador
    suprimidas = [(g, s) for g, s in a.subgrupos["Colegio"].items()
                  if s.cortes["pct"].isna().any()]
    assert suprimidas
    _, s = suprimidas[0]
    fila = s.cortes.index[s.cortes["pct"].isna()][0]
    s.cortes.loc[fila, "pct"] = 50.0                    # alguien la «destapa»
    assert auditoria.auditar_cifras(a)


def test_la_autolesion_por_grupo_es_un_hallazgo():
    ac = datos.preparado()
    s = next(iter(ac.cuidador.subgrupos["Colegio"].values()))
    s.cortes = pd.concat([s.cortes, ac.cuidador.cortes[
        ac.cuidador.cortes["clave"] == "EPDS_Autolesion"]], ignore_index=True)
    problemas = auditoria.auditar(ac.marcos)
    assert any("autolesión" in p for p in problemas)


def test_la_autolesion_en_la_tabla_de_senales_por_grupo_es_un_hallazgo():
    ac = datos.preparado()
    t = ac.cuidador.alertas.copy()
    t.loc[len(t)] = dict(alerta=cat.AUTOLESION, agrupacion="Colegio", grupo="LauV", n=30,
                         pct=12.0, ic_inf=5.0, ic_sup=20.0, estado="presente")
    ac.cuidador.alertas = t
    assert any("autolesión" in p for p in auditoria.auditar_solo_total(ac.cuidador))


def test_solo_el_total_publicado_se_audita_exacto_con_muchos_atomos():
    """Con más de MAX_ENUMERAR átomos y solo el total publicado no hay falso hallazgo."""
    n_atomos = supresion.MAX_ENUMERAR + 3
    celdas = [f"C{i}|Quinto" for i in range(n_atomos)]
    jer = supresion.jerarquia(celdas, [c.split("|")[0] for c in celdas], ["Quinto"],
                              con_resto=False)
    partes = {supresion.atomo_celda(k): (8, 2) for k in celdas}
    assert supresion.fugas(jer, partes, {supresion.NIVEL}, 3)          # falla cerrado
    assert auditoria.fugas(jer, partes, {supresion.NIVEL}, 3) == []
    pocos = {supresion.atomo_celda(k): ((10, 0) if i else (8, 2)) for i, k in enumerate(celdas)}
    assert auditoria.fugas(jer, pocos, {supresion.NIVEL}, 3)            # 2 casos en total


def _ninos_hermanos() -> pd.DataFrame:
    """30 cuidadores, 32 niños de un solo colegio y grado. La banda «muy alta» del SDQ
    tiene 4 niños, pero de solo 2 cuidadores (dos pares de hermanos)."""
    filas = []
    puntajes = [5] * 20 + [15] * 5 + [18] * 3
    for i, sdq in enumerate(puntajes):
        filas.append((f"c{i}", f"n{i}", sdq))
    for i in (28, 29):
        filas += [(f"c{i}", f"n{i}a", 25), (f"c{i}", f"n{i}b", 25)]
    return pd.DataFrame([dict(ID_cuidador=c, ID_nino=n, Colegio="A", Grado="Quinto",
                              Grado_detalle="Quinto", Ola="2026", Quien="Mamá",
                              Sexo="Niña" if k % 2 else "Niño", Edad=10.0, SDQ_Total=float(s))
                         for k, (c, n, s) in enumerate(filas)])


def test_el_marco_de_ninos_exige_tres_cuidadores_distintos():
    from src.cuidadores import pipeline
    a = pipeline.analizar_marco(_ninos_hermanos(), cat.MARCO_NINO, n_boot=5)
    banda = a.bandas[a.bandas["clave"] == "SDQ_Total"].iloc[0]
    assert pd.isna(banda["pct_b3"])                 # el pipeline la suprimió
    assert auditoria.auditar_cifras(a) == []
    # alguien la destapa con los porcentajes reales: 4 niños en la banda muy alta
    fila = a.bandas.index[a.bandas["clave"] == "SDQ_Total"][0]
    for i, pct in enumerate((62.5, 15.6, 9.4, 12.5)):
        a.bandas.loc[fila, f"pct_b{i}"] = pct
    problemas = auditoria.auditar_cifras(a)
    assert any("cuidadores" in p for p in problemas)


def test_los_mensajes_no_muestran_identificadores():
    ac = datos.preparado()
    s = next(iter(ac.cuidador.subgrupos["Colegio"].values()))
    s.cortes["pct"] = np.where(s.cortes["pct"].isna(), 50.0, s.cortes["pct"])
    for p in auditoria.auditar(ac.marcos):
        assert not any(t in p for t in ("Centinela", "3000000000"))
        assert not any(len(x) == 9 and x[0] in "CN" and all(c in "0123456789abcdef" for c in x[1:])
                       for x in p.split())
