"""
Evaluación de los hallazgos fijos del «Resumen» contra una corrida.

`evaluar(t)` recorre `hallazgos_catalogo.HALLAZGOS` y, para cada uno, aplica
una regla fija sobre las tablas AGREGADAS de la corrida (`t.capa1.*`,
`t.diadas.*`): si la corrida lo sustenta, devuelve el hallazgo con la cifra
que lo sustenta (texto armado solo con números de esas tablas); si falta la
tabla, la fila o la condición no se cumple, el hallazgo no sale y no hay
error. Funciona igual con `pipeline.Triangulacion` (local) y con
`lectura.TriangulacionPublicada` (equipo y público), que solo tienen
agregados: aquí no se calcula nada sobre personas.

Reglas (una por hallazgo; «IC» = intervalo del 95 %):
  1. Acuerdo SDQ: la diferencia niño − cuidador excluye 0 por arriba en el
     total y en lo emocional.
  2. Informante: para EPDS o PSS, el IC de ρ con el reporte del cuidador
     excluye 0 y no se solapa con el IC de ρ con el reporte del niño (menor).
  3. Señales: el IC del % con señal de malestar entre quienes marcan el ítem
     18 con frecuencia queda por debajo del 50 %.
  4. Apoyo y ánimo: % EPDS ≥ 13 decreciente del tercil bajo al alto y los IC
     de bajo y alto no se solapan.
  5. PSS: el IC de d (cuidadores − docentes) cae dentro de ± `MARGEN_PSS`.
  6. Sin adulto por grado: el grado más bajo con cifra mejor que el resto y
     el grado con el % más alto, posterior, peor que el resto (IC excluyen 0).
  7. Por colegio: apoyo familiar niño–cuidador en coincidencia positiva y, en
     los docentes, apoyo del líder peor y demandas peores (IC excluyen 0).
  8. Desgaste docente: β de demandas y de conflicto de rol excluyen 0 por
     arriba y |β del líder| es menor que ambos.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import hallazgos_catalogo as hc

MARGEN_PSS = 0.2
_VACIA = pd.DataFrame()
_ERRORES = (KeyError, IndexError, TypeError, ValueError, AttributeError)


@dataclass(frozen=True)
class Visible:
    hallazgo: hc.Hallazgo
    cifra: str
    grupo: str | None = None        # el colegio, en los hallazgos por colegio


# ── utilidades ──────────────────────────────────────────────────────────────
def _tabla(t, parte: str, nombre: str) -> pd.DataFrame:
    df = getattr(getattr(t, parte, None), nombre, None)
    return df if isinstance(df, pd.DataFrame) else _VACIA


def _f(v, dec: int = 2) -> str:
    return "—" if v is None or pd.isna(v) else f"{float(v):.{dec}f}"


def _ic(lo, hi, dec: int = 2) -> str:
    return f"[{_f(lo, dec)}; {_f(hi, dec)}]"


def _n(v) -> str:
    try:
        return str(int(v))
    except (TypeError, ValueError):
        return "—"


def _fila(df: pd.DataFrame, **cond):
    """La primera fila que cumple todas las condiciones de igualdad, o None."""
    if df.empty or any(k not in df.columns for k in cond):
        return None
    m = pd.Series(True, index=df.index)
    for k, v in cond.items():
        m &= df[k] == v
    sub = df[m]
    return sub.iloc[0] if len(sub) else None


def _con_cifra(fila, *campos) -> bool:
    return fila is not None and all(pd.notna(fila.get(c)) for c in campos)


# ── reglas ──────────────────────────────────────────────────────────────────
def _h1(t):
    ac = _tabla(t, "diadas", "acuerdo")
    tot = _fila(ac, subescala="SDQ_Total")
    emo = _fila(ac, subescala="SDQ_Emo")
    if not (_con_cifra(tot, "dif_ic_inf", "media_nino", "media_cuidador")
            and _con_cifra(emo, "dif_ic_inf", "cci")):
        return None
    if not (tot["dif_ic_inf"] > 0 and emo["dif_ic_inf"] > 0):
        return None
    return (f"SDQ total: niño {_f(tot['media_nino'], 1)} frente a cuidador "
            f"{_f(tot['media_cuidador'], 1)} (diferencia {_f(tot['dif_media'], 1)} "
            f"{_ic(tot['dif_ic_inf'], tot['dif_ic_sup'], 1)}); síntomas emocionales: diferencia "
            f"{_f(emo['dif_media'], 1)} {_ic(emo['dif_ic_inf'], emo['dif_ic_sup'], 1)}, CCI "
            f"{_f(emo['cci'])} {_ic(emo['cci_ic_inf'], emo['cci_ic_sup'])}; "
            f"{_n(tot['n'])} díadas de {_n(tot['familias'])} familias.")


def _h2(t):
    inf = _tabla(t, "diadas", "informante")
    partes = []
    for clave, etiqueta in cat.PREDICTORES_INFORMANTE:
        f = _fila(inf, predictor=clave)
        if not _con_cifra(f, "rho_cuidador_ic_inf", "rho_nino_ic_sup"):
            continue
        if f["rho_cuidador_ic_inf"] > 0 and f["rho_nino_ic_sup"] < f["rho_cuidador_ic_inf"]:
            partes.append(f"{etiqueta}: ρ {_f(f['rho_cuidador'])} "
                          f"{_ic(f['rho_cuidador_ic_inf'], f['rho_cuidador_ic_sup'])} con el SDQ "
                          f"que da el cuidador y {_f(f['rho_nino'])} "
                          f"{_ic(f['rho_nino_ic_inf'], f['rho_nino_ic_sup'])} con el que da el "
                          f"niño ({_n(f['n'])} díadas de {_n(f['familias'])} familias)")
    return "; ".join(partes) + "." if partes else None


def _h3(t):
    m = _tabla(t, "capa1", "municipal")
    entre = _fila(m, bloque=c1.BLOQUE_SENALES, clave="malestar_entre_item18")
    i18 = _fila(m, bloque=c1.BLOQUE_SENALES, clave="item18_frecuente")
    mal = _fila(m, bloque=c1.BLOQUE_SENALES, clave="malestar")
    if not (_con_cifra(entre, "valor", "ic_sup") and _con_cifra(i18, "valor")
            and _con_cifra(mal, "valor")):
        return None
    if not entre["ic_sup"] < 50:
        return None
    return (f"Solo el {_f(entre['valor'], 1)} % {_ic(entre['ic_inf'], entre['ic_sup'], 1)} de "
            f"quienes marcan el ítem 18 «con frecuencia» o más tiene además la señal de "
            f"malestar (ítem 18 frecuente: {_f(i18['valor'], 1)} %; señal de malestar: "
            f"{_f(mal['valor'], 1)} %; {_n(entre['n'])} estudiantes de secundaria).")


def _h4(t):
    m = _tabla(t, "capa1", "municipal")
    filas = [_fila(m, bloque=c1.BLOQUE_APOYO_ANIMO, grupo=g) for g in c1.TERCILES]
    if not all(_con_cifra(f, "valor", "ic_inf", "ic_sup") for f in filas):
        return None
    bajo, medio, alto = filas
    if not (bajo["valor"] > medio["valor"] > alto["valor"] and bajo["ic_inf"] > alto["ic_sup"]):
        return None
    return (f"EPDS ≥ 13: {_f(bajo['valor'], 1)} % {_ic(bajo['ic_inf'], bajo['ic_sup'], 1)} en el "
            f"tercil bajo de apoyo familiar, {_f(medio['valor'], 1)} % en el medio y "
            f"{_f(alto['valor'], 1)} % {_ic(alto['ic_inf'], alto['ic_sup'], 1)} en el alto "
            f"({_n(bajo['n'])}, {_n(medio['n'])} y {_n(alto['n'])} cuidadores).")


def _h5(t):
    m = _tabla(t, "capa1", "municipal")
    cu = _fila(m, bloque=c1.BLOQUE_PSS, clave="cuidadores")
    do = _fila(m, bloque=c1.BLOQUE_PSS, clave="docentes")
    dif = _fila(m, bloque=c1.BLOQUE_PSS, clave="diferencia")
    if not all(_con_cifra(f, "valor", "ic_inf", "ic_sup") for f in (cu, do, dif)):
        return None
    if not (dif["ic_inf"] > -MARGEN_PSS and dif["ic_sup"] < MARGEN_PSS):
        return None
    return (f"PSS-10: cuidadores {_f(cu['valor'], 1)} {_ic(cu['ic_inf'], cu['ic_sup'], 1)} "
            f"(n = {_n(cu['n'])}) frente a docentes {_f(do['valor'], 1)} "
            f"{_ic(do['ic_inf'], do['ic_sup'], 1)} (n = {_n(do['n'])}); d = {_f(dif['valor'])} "
            f"{_ic(dif['ic_inf'], dif['ic_sup'])}.")


def _h6(t):
    g = _tabla(t, "capa1", "por_grado")
    if g.empty or "clave" not in g.columns:
        return None
    sub = g[(g["clave"] == "est_sin_adulto") & g["d"].notna()]
    orden = list(getattr(getattr(t, "capa1", None), "grados", None) or [])
    sub = sub[sub["grupo"].isin(orden)] if orden else sub
    if len(sub) < 2:
        return None
    sub = sub.assign(_pos=sub["grupo"].map({x: i for i, x in enumerate(orden)}) if orden
                     else range(len(sub))).sort_values("_pos")
    primero = sub.iloc[0]
    peor = sub.loc[sub["media_grupo"].idxmax()]
    if not (peor["_pos"] > primero["_pos"] and primero["ic_sup"] < 0 and peor["ic_inf"] > 0):
        return None
    return (f"Sin adulto de confianza: {_f(primero['media_grupo'], 0)} % en {primero['grupo']} "
            f"y {_f(peor['media_grupo'], 0)} % en {peor['grupo']} (cada grado frente al resto: "
            f"d {_f(primero['d'])} {_ic(primero['ic_inf'], primero['ic_sup'])} y "
            f"{_f(peor['d'])} {_ic(peor['ic_inf'], peor['ic_sup'])}).")


def _h7(t) -> list[tuple[str, str]]:
    cl = _tabla(t, "capa1", "clasificacion")
    dif = _tabla(t, "capa1", "diferencias")
    par = next((p for p in cat.PARES if p.a == "est_mspss_fam" and p.b == "cui_mspss_fam"), None)
    if par is None or cl.empty or dif.empty:
        return []
    salida = []
    for colegio in list(getattr(getattr(t, "capa1", None), "colegios", None) or []):
        fam = _fila(cl, agrupacion="Colegio", grupo=colegio, par=par.titulo)
        lider = _fila(dif, agrupacion="Colegio", grupo=colegio, clave="doc_lider")
        dem = _fila(dif, agrupacion="Colegio", grupo=colegio, clave="doc_demandas")
        if not (_con_cifra(fam, "d_a", "d_b") and _con_cifra(lider, "ic_sup")
                and _con_cifra(dem, "ic_inf")):
            continue
        if not (fam["clasificacion"] == cat.COINCIDENCIA and fam["d_a"] > 0 and fam["d_b"] > 0
                and lider["ic_sup"] < 0 and dem["ic_inf"] > 0):
            continue
        salida.append((colegio, (
            f"Apoyo familiar: estudiantes d {_f(fam['d_a'])} {fam['ic_a']}, cuidadores d "
            f"{_f(fam['d_b'])} {fam['ic_b']}; docentes: apoyo del líder d {_f(lider['d'])} "
            f"{_ic(lider['ic_inf'], lider['ic_sup'])}, demandas d {_f(dem['d'])} "
            f"{_ic(dem['ic_inf'], dem['ic_sup'])}.")))
    return salida


def _h8(t):
    m = _tabla(t, "capa1", "municipal")
    filas = {k: _fila(m, bloque=c1.BLOQUE_DESGASTE, clave=k) for k, _ in c1.PREDICTORES_DESGASTE}
    if not all(_con_cifra(f, "valor", "ic_inf", "ic_sup") for f in filas.values()):
        return None
    dem, conf, lid = filas["demandas"], filas["conflicto_rol"], filas["lider"]
    if not (dem["ic_inf"] > 0 and conf["ic_inf"] > 0
            and abs(lid["valor"]) < min(dem["valor"], conf["valor"])):
        return None
    return (f"β estandarizado del desgaste: demandas {_f(dem['valor'])} "
            f"{_ic(dem['ic_inf'], dem['ic_sup'])}, conflicto de rol {_f(conf['valor'])} "
            f"{_ic(conf['ic_inf'], conf['ic_sup'])}, apoyo del líder {_f(lid['valor'])} "
            f"{_ic(lid['ic_inf'], lid['ic_sup'])} ({_n(dem['n'])} docentes).")


REGLAS = {1: _h1, 2: _h2, 3: _h3, 4: _h4, 5: _h5, 6: _h6, 8: _h8}
REGLAS_POR_COLEGIO = {7: _h7}


# ── API ─────────────────────────────────────────────────────────────────────
def evaluar(t) -> list[Visible]:
    """Los hallazgos que esta corrida sustenta, en el orden del catálogo."""
    salida: list[Visible] = []
    for h in hc.HALLAZGOS:
        try:
            if h.numero in REGLAS:
                cifra = REGLAS[h.numero](t)
                if cifra:
                    salida.append(Visible(h, cifra))
            elif h.numero in REGLAS_POR_COLEGIO:
                for colegio, cifra in REGLAS_POR_COLEGIO[h.numero](t):
                    salida.append(Visible(h, cifra, colegio))
        except _ERRORES:
            continue
    return salida


def por_bloque(visibles: list[Visible], bloque: str) -> list[Visible]:
    return [v for v in visibles if v.hallazgo.bloque == bloque]


def hipotesis_de(visibles: list[Visible]) -> list[hc.Hipotesis]:
    ids: list[str] = []
    for v in visibles:
        for i in v.hallazgo.hipotesis:
            if i not in ids:
                ids.append(i)
    return [hc.HIPOTESIS_POR_ID[i] for i in sorted(ids, key=lambda x: int(x[1:]))
            if i in hc.HIPOTESIS_POR_ID]


COLUMNAS_TABLA = ["numero", "bloque", "colegio", "actores", "titulo", "texto", "cifra",
                  "hipotesis", "estado"]


def tabla(visibles: list[Visible]) -> pd.DataFrame:
    filas = [dict(numero=v.hallazgo.numero, bloque=v.hallazgo.bloque, colegio=v.grupo or "",
                  actores=", ".join(v.hallazgo.actores), titulo=v.hallazgo.titulo,
                  texto=v.hallazgo.texto, cifra=v.cifra,
                  hipotesis=", ".join(v.hallazgo.hipotesis), estado=hc.ESTADO_TEXTOS)
             for v in visibles]
    return pd.DataFrame(filas, columns=COLUMNAS_TABLA)


# ── Perfil por colegio (bloque 1 del Resumen) ───────────────────────────────
MEJOR, PEOR = "▲", "▼"
COLUMNAS_PERFIL = ["Colegio", "Estudiantes", "Cuidadores", "Docentes"]


def perfil_colegios(t) -> pd.DataFrame:
    """Por colegio y actor, los constructos con IC que excluye 0 (▲ mejor / ▼ peor),
    con la etiqueta corta del catálogo. Solo cifras ya publicadas; sin conteos."""
    dif = _tabla(t, "capa1", "diferencias")
    colegios = list(getattr(getattr(t, "capa1", None), "colegios", None) or [])
    if dif.empty or not colegios or "d_orientada" not in dif.columns:
        return pd.DataFrame(columns=COLUMNAS_PERFIL)
    filas = []
    for colegio in colegios:
        fila = {"Colegio": colegio}
        sub = dif[(dif["agrupacion"] == "Colegio") & (dif["grupo"] == colegio) & dif["d"].notna()]
        for actor in COLUMNAS_PERFIL[1:]:
            partes = []
            for _, f in sub[sub["actor"] == actor].iterrows():
                c = cat.POR_CLAVE.get(f["clave"])
                lo, hi = c1._orientado(f) if c is not None else (float("nan"), float("nan"))
                signo = c1._signo(lo, hi)
                if signo == 0:
                    continue
                corta = c.corta or c.etiqueta
                partes.append(f"{MEJOR if signo > 0 else PEOR} {corta}")
            fila[actor] = "; ".join(partes) if partes else "sin diferencias claras"
        filas.append(fila)
    return pd.DataFrame(filas, columns=COLUMNAS_PERFIL)
