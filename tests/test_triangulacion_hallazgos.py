"""Triangulación · los hallazgos fijos del Resumen: aparecen solo cuando la corrida los sustenta."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import hallazgos as hz
from src.triangulacion import hallazgos_catalogo as hc

PAR_FAM = next(p for p in cat.PARES if p.a == "est_mspss_fam").titulo


def _t(**cambios):
    """Una corrida mínima (solo agregados) que sustenta los 8 hallazgos."""
    acuerdo = pd.DataFrame([
        dict(subescala="SDQ_Total", escala="Dificultades", n=206, familias=192, media_nino=12.5,
             media_cuidador=9.0, cci=0.2, cci_ic_inf=0.1, cci_ic_sup=0.3, dif_media=3.6,
             dif_ic_inf=2.6, dif_ic_sup=4.5, motivo=""),
        dict(subescala="SDQ_Emo", escala="Emocional", n=206, familias=192, media_nino=3.6,
             media_cuidador=2.0, cci=0.07, cci_ic_inf=-0.04, cci_ic_sup=0.18, dif_media=1.6,
             dif_ic_inf=1.1, dif_ic_sup=2.0, motivo="")])
    informante = pd.DataFrame([
        dict(predictor="EPDS_Total", etiqueta="Ánimo", n=206, familias=192, rho_cuidador=0.45,
             rho_cuidador_ic_inf=0.33, rho_cuidador_ic_sup=0.55, rho_nino=0.11,
             rho_nino_ic_inf=-0.03, rho_nino_ic_sup=0.24, motivo=""),
        dict(predictor="PSS_Total", etiqueta="Estrés", n=206, familias=192, rho_cuidador=0.40,
             rho_cuidador_ic_inf=0.28, rho_cuidador_ic_sup=0.52, rho_nino=0.10,
             rho_nino_ic_inf=-0.04, rho_nino_ic_sup=0.23, motivo="")])
    municipal = pd.DataFrame([
        dict(bloque="senales", clave="item18_frecuente", grupo=None, n=900, valor=25.1,
             ic_inf=22.4, ic_sup=28.0, motivo=""),
        dict(bloque="senales", clave="malestar", grupo=None, n=900, valor=8.8, ic_inf=7.1,
             ic_sup=10.8, motivo=""),
        dict(bloque="senales", clave="malestar_entre_item18", grupo=None, n=900, valor=20.0,
             ic_inf=15.0, ic_sup=25.0, motivo=""),
        dict(bloque="apoyo_animo", clave="epds_probable", grupo="bajo", n=240, valor=43.0,
             ic_inf=37.0, ic_sup=49.0, motivo=""),
        dict(bloque="apoyo_animo", clave="epds_probable", grupo="medio", n=240, valor=20.0,
             ic_inf=15.0, ic_sup=25.0, motivo=""),
        dict(bloque="apoyo_animo", clave="epds_probable", grupo="alto", n=240, valor=8.0,
             ic_inf=5.0, ic_sup=12.0, motivo=""),
        dict(bloque="pss", clave="cuidadores", grupo=None, n=700, valor=14.4, ic_inf=13.9,
             ic_sup=14.8, motivo=""),
        dict(bloque="pss", clave="docentes", grupo=None, n=470, valor=14.3, ic_inf=13.7,
             ic_sup=14.8, motivo=""),
        dict(bloque="pss", clave="diferencia", grupo=None, n=1170, valor=0.02, ic_inf=-0.10,
             ic_sup=0.13, motivo=""),
        dict(bloque="desgaste_docente", clave="demandas", grupo=None, n=470, valor=0.30,
             ic_inf=0.18, ic_sup=0.42, motivo=""),
        dict(bloque="desgaste_docente", clave="conflicto_rol", grupo=None, n=470, valor=0.25,
             ic_inf=0.12, ic_sup=0.38, motivo=""),
        dict(bloque="desgaste_docente", clave="lider", grupo=None, n=470, valor=-0.12,
             ic_inf=-0.22, ic_sup=-0.02, motivo=""),
        dict(bloque="desgaste_docente", clave="r2", grupo=None, n=470, valor=0.50,
             ic_inf=np.nan, ic_sup=np.nan, motivo="")])
    por_grado = pd.DataFrame([
        dict(agrupacion="Grado", grupo=g, clave="est_sin_adulto", actor="Estudiantes",
             constructo="Sin adulto", n_grupo=100, n_resto=800, media_grupo=p, media_resto=40.0,
             d=d, ic_inf=d - 0.2, ic_sup=d + 0.2, d_orientada=-d, ajuste="", motivo="")
        for g, p, d in (("Cuarto", 24.0, -0.4), ("Sexto", 37.0, -0.05), ("Noveno", 51.0, 0.35),
                        ("Décimo", 29.0, -0.1))])
    diferencias = pd.DataFrame([
        dict(agrupacion="Colegio", grupo="LauV", clave="doc_lider", actor="Docentes",
             constructo="Líder", n_grupo=54, n_resto=400, media_grupo=2.0, media_resto=2.9,
             d=-0.68, ic_inf=-0.93, ic_sup=-0.44, d_orientada=-0.68, ajuste="", motivo=""),
        dict(agrupacion="Colegio", grupo="LauV", clave="doc_demandas", actor="Docentes",
             constructo="Demandas", n_grupo=54, n_resto=400, media_grupo=1.9, media_resto=1.3,
             d=0.62, ic_inf=0.32, ic_sup=0.92, d_orientada=-0.62, ajuste="", motivo=""),
        dict(agrupacion="Colegio", grupo="JJC", clave="doc_lider", actor="Docentes",
             constructo="Líder", n_grupo=60, n_resto=400, media_grupo=3.4, media_resto=2.7,
             d=0.48, ic_inf=0.23, ic_sup=0.74, d_orientada=0.48, ajuste="", motivo="")])
    clasificacion = pd.DataFrame([
        dict(agrupacion="Colegio", grupo="LauV", par=PAR_FAM, tipo=cat.MISMO_OBJETO,
             a="Apoyo niño", d_a=0.14, ic_a="[0.03; 0.25]", b="Apoyo cuidador", d_b=0.29,
             ic_b="[0.14; 0.44]", clasificacion=cat.COINCIDENCIA),
        dict(agrupacion="Colegio", grupo="JJC", par=PAR_FAM, tipo=cat.MISMO_OBJETO,
             a="Apoyo niño", d_a=-0.16, ic_a="[-0.29; -0.03]", b="Apoyo cuidador", d_b=-0.2,
             ic_b="[-0.4; 0.0]", clasificacion=cat.SIN_DIFERENCIA)])
    base = dict(acuerdo=acuerdo, informante=informante, municipal=municipal, por_grado=por_grado,
                diferencias=diferencias, clasificacion=clasificacion)
    base.update(cambios)
    capa1 = SimpleNamespace(colegios=["JJC", "LauV"], grados=["Cuarto", "Sexto", "Noveno", "Décimo"],
                            diferencias=base["diferencias"], clasificacion=base["clasificacion"],
                            por_grado=base["por_grado"], municipal=base["municipal"])
    diadas = SimpleNamespace(n=206, familias=192, acuerdo=base["acuerdo"],
                             informante=base["informante"])
    return SimpleNamespace(capa1=capa1, diadas=diadas, n_colegios=2)


def test_las_hipotesis_solo_se_apoyan_en_los_hallazgos_fuertes():
    assert set(hc.HIPOTESIS_POR_ID) == {"H1", "H4", "H8", "H10", "H11", "H12"}
    todo = " ".join(h.texto + h.patron + h.alternativas + h.prueba for h in hc.HIPOTESIS)
    for ajeno in ("no visto", "no lo ven", "niñas", "brecha emocional"):
        assert ajeno not in todo.lower()
    assert "mitad del peso" in hc.HIPOTESIS_POR_ID["H8"].texto


def test_el_hallazgo_8_exige_el_doble_del_lider_con_los_dos_ic():
    t = _t()
    m = t.capa1.municipal
    lid = m["clave"] == "lider"
    t.capa1.municipal = m.assign(ic_sup=np.where(lid, 0.02, m["ic_sup"]))   # líder cruza 0
    assert 8 not in {v.hallazgo.numero for v in hz.evaluar(t)}
    t.capa1.municipal = m[m["clave"] != "r2"]                                # sin R²: igual sale
    assert 8 in {v.hallazgo.numero for v in hz.evaluar(t)}


def test_el_hallazgo_4_acepta_dos_grupos_de_apoyo():
    t = _t()
    m = t.capa1.municipal
    t.capa1.municipal = m[m["grupo"] != "medio"]
    v = next(v for v in hz.evaluar(t) if v.hallazgo.numero == 4)
    assert "bajo" in v.cifra and "alto" in v.cifra and "medio" not in v.cifra


def test_el_catalogo_son_los_ocho_hallazgos_fuertes_sin_aprobar():
    assert [h.numero for h in hc.HALLAZGOS] == list(range(1, 9))
    assert hc.TEXTOS_APROBADOS is False
    assert {h.bloque for h in hc.HALLAZGOS} == {hc.PATRON, hc.TENSION}
    assert [h.numero for h in hc.HALLAZGOS if h.bloque == hc.TENSION] == [7]
    for h in hc.HALLAZGOS:
        assert h.actores and set(h.actores) <= set(hc.ACTORES)
        assert h.texto and h.titulo and h.sustento
        assert set(h.hipotesis) <= set(hc.HIPOTESIS_POR_ID)
    assert {i for h in hc.HALLAZGOS for i in h.hipotesis} == set(hc.HIPOTESIS_POR_ID)


def test_una_corrida_que_sustenta_todo_muestra_los_ocho():
    vis = hz.evaluar(_t())
    assert [v.hallazgo.numero for v in vis] == list(range(1, 9))
    assert all(v.cifra for v in vis)
    siete = next(v for v in vis if v.hallazgo.numero == 7)
    assert siete.grupo == "LauV"                           # JJC no cumple
    assert "0.14" in siete.cifra and "-0.68" in siete.cifra and "0.62" in siete.cifra
    assert [h.id for h in hz.hipotesis_de(vis)] == ["H1", "H4", "H8", "H10", "H11", "H12"]


def test_las_cifras_salen_de_las_tablas_y_no_de_texto_libre():
    vis = {v.hallazgo.numero: v.cifra for v in hz.evaluar(_t())}
    assert "12.5" in vis[1] and "9.0" in vis[1] and "0.07" in vis[1]
    assert "0.45" in vis[2] and "0.11" in vis[2]
    assert "20.0 %" in vis[3]
    assert "43.0 %" in vis[4] and "8.0 %" in vis[4]
    assert "14.4" in vis[5] and "14.3" in vis[5]
    assert "Cuarto" in vis[6] and "Noveno" in vis[6] and "Décimo" not in vis[6]
    assert "0.30" in vis[8] and "-0.12" in vis[8] and "R² 0.50" in vis[8]


@pytest.mark.parametrize("numero, cambio", [
    (1, lambda b: b["acuerdo"].assign(dif_ic_inf=[-0.5, 1.1])),
    (2, lambda b: b["informante"].assign(rho_nino_ic_sup=[0.4, 0.5])),
    (3, lambda b: b["municipal"].assign(ic_sup=np.where(
        b["municipal"]["clave"] == "malestar_entre_item18", 55.0, b["municipal"]["ic_sup"]))),
    (4, lambda b: b["municipal"].assign(ic_inf=np.where(
        b["municipal"]["grupo"] == "bajo", 10.0, b["municipal"]["ic_inf"]))),
    (5, lambda b: b["municipal"].assign(ic_sup=np.where(
        b["municipal"]["clave"] == "diferencia", 0.3, b["municipal"]["ic_sup"]))),
    (6, lambda b: b["por_grado"].assign(ic_inf=[-0.6, -0.25, -0.05, -0.3])),
    (7, lambda b: b["diferencias"].assign(ic_inf=[-0.93, -0.1, 0.23])),
    (8, lambda b: b["municipal"].assign(valor=np.where(
        b["municipal"]["clave"] == "lider", -0.16, b["municipal"]["valor"]))),   # < 2×
])
def test_cada_hallazgo_desaparece_cuando_su_condicion_no_se_cumple(numero, cambio):
    base = {k: getattr(_t().capa1 if hasattr(_t().capa1, k) else _t().diadas, k)
            for k in ("acuerdo", "informante", "municipal", "por_grado", "diferencias",
                      "clasificacion")}
    tabla_cambiada = {("acuerdo" if numero == 1 else "informante" if numero == 2
                       else "por_grado" if numero == 6 else "diferencias" if numero == 7
                       else "municipal"): cambio(base)}
    vis = [v.hallazgo.numero for v in hz.evaluar(_t(**tabla_cambiada))]
    assert numero not in vis
    assert len(vis) == 7


def test_sin_tablas_no_hay_hallazgos_ni_errores():
    vacio = SimpleNamespace(capa1=SimpleNamespace(colegios=[], grados=[]),
                            diadas=SimpleNamespace(), n_colegios=0)
    assert hz.evaluar(vacio) == []
    assert hz.evaluar(SimpleNamespace()) == []
    t = _t(municipal=pd.DataFrame(), informante=pd.DataFrame(columns=["predictor"]))
    assert [v.hallazgo.numero for v in hz.evaluar(t)] == [1, 6, 7]


def test_con_filas_sin_cifra_se_oculta_sin_error():
    t = _t()
    t.capa1.municipal = t.capa1.municipal.assign(valor=np.nan, ic_inf=np.nan, ic_sup=np.nan,
                                                  motivo=c1.MOTIVO_CELDAS)
    assert {v.hallazgo.numero for v in hz.evaluar(t)} == {1, 2, 6, 7}


def test_la_tabla_del_resumen_lleva_los_textos_fijos_y_su_estado():
    tb = hz.tabla(hz.evaluar(_t()))
    assert list(tb.columns) == hz.COLUMNAS_TABLA
    assert len(tb) == 8 and (tb["estado"] == hc.ESTADO_TEXTOS).all()
    assert tb.loc[tb["numero"] == 7, "colegio"].iloc[0] == "LauV"
    assert tb.loc[tb["numero"] == 1, "texto"].iloc[0] == hc.POR_NUMERO[1].texto
    assert hz.tabla([]).empty and list(hz.tabla([]).columns) == hz.COLUMNAS_TABLA


def test_con_la_corrida_publicada_y_la_local_se_ven_los_mismos_hallazgos():
    from tests import triangulacion_publicada_datos as datos
    from src.triangulacion import lectura
    local = datos.analisis()
    _, base = datos.publicado()
    leida = lectura.reconstruir(base.tablas["resultados"], base.tablas["corridas"][0])
    assert hz.tabla(hz.evaluar(leida)).equals(hz.tabla(hz.evaluar(local)))


def test_perfil_por_colegio_usa_las_etiquetas_cortas_y_solo_ic_que_excluye_0():
    t = _t()
    perfil = hz.perfil_colegios(t).set_index("Colegio")
    assert list(perfil.columns) == hz.COLUMNAS_PERFIL[1:]
    assert perfil.loc["LauV", "Docentes"] == ("▼ apoyo del líder (menos); "
                                             "▼ demandas / presión de tiempo (más)")
    assert perfil.loc["JJC", "Docentes"] == "▲ apoyo del líder (más)"
    assert perfil.loc["JJC", "Estudiantes"] == "sin diferencias claras"
    assert hz.perfil_colegios(SimpleNamespace()).empty
