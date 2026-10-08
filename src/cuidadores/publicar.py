"""
Publicación de Cuidadores 360 en Supabase — Observatorio 360 (fase 4b).

Es la otra mitad de `cuidadores.lectura` y sigue a `estudiantes.publicar`:
mismas tablas (`obs360.corridas`, `obs360.resultados`), mismas guardas y el
mismo orden, con `modulo = "cuidadores"`.

QUÉ SUBE
Solo agregados del análisis de TODAS las olas, ya preparado para la comunidad
(`comunidad.preparar`): descriptivos, cortes, bandas del SDQ de padres,
terciles, correlaciones, medias por colegio y por grado, CCI, las tablas de
cada colegio, grado y celda y las señales del adulto sin casos. Nada por ola,
ningún identificador, ningún conteo de casos. No se publican la comparación por
sexo del niño, los ítems del APQ ni los del estrés parental (solo locales).

CÓMO SE GUARDA
  · `nivel = "cuidadores"` en todas las filas (el CHECK de la base admite
    'secundaria', 'primaria' y 'cuidadores').
  · El marco va en `detalle.marco` ("cuidador" o "nino"): las claves de los
    dos marcos no se repiten, salvo «muestra», y el lector separa por ese campo.
  · La autolesión solo lleva la fila del total (spec §5.5).

GUARDAS, EN ESTE ORDEN (las de estudiantes, más las de cuidadores)
  1. `aplanar` solo lee tablas agregadas de la copia preparada.
  2. `estudiantes.publicar.verificar`: n ≥ 10, sin columnas de identificación,
     sin identificadores E/C/N y sin conteos de casos. Falla el lote entero.
  3. `verificar_restas` (`cuidadores.auditoria.auditar`): restas que dejen de 1
     a 9 cuidadores distintos, proporciones con menos de 3 casos o no casos
     (también por resta y, en el marco de niños, contando cuidadores) y
     autolesión por grupo. Con un hallazgo no se publica nada.
  4. El esquema rechaza n < 10, identificadores y conteos aunque todo lo
     anterior fallara; RLS: el rol anónimo no escribe.
  5. La corrida entra oculta y solo se abre con todos sus resultados dentro; al
     abrirla con `--publicar-ya` se despublican las demás corridas DE
     CUIDADORES (las de estudiantes no se tocan).
  6. Mientras `comunidad_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` no sean
     True, `--publicar-ya` no sube las filas de las señales del adulto
     (`alerta`, `alerta_grupo`). `--ensayo` las deja en el JSON y avisa.

USO (en la máquina que procesa, con OBS360_CLAVE_HMAC)
    python -m src.cuidadores.publicar --ensayo --salida /tmp/lote_cuidadores.json
    python -m src.cuidadores.publicar --notas "primera corrida" --publicar-ya
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import publicar as pub_est

MODULO = cat.MODULO
NIVEL = "cuidadores"
ESQUEMA = pub_est.ESQUEMA
TABLA_CORRIDAS = pub_est.TABLA_CORRIDAS
TABLA_RESULTADOS = pub_est.TABLA_RESULTADOS
PublicacionInsegura = pub_est.PublicacionInsegura
TIPOS_ALERTA = pub_est.TIPOS_ALERTA
AVISO_ALERTAS_NO_APROBADAS = (
    "AVISO: las señales del adulto no están aprobadas (comunidad_catalogo.TEXTOS_APROBADOS y "
    "RUTAS_VALIDADAS en False)")
FUENTE_BANDAS = "Scoring the SDQ for age 4-17, versión para padres, sdqinfo.org"


def alertas_aprobadas() -> bool:
    """¿El equipo aprobó los textos y validó la ruta para adultos? (spec §8)."""
    try:
        from src.cuidadores import comunidad_catalogo as cc
    except Exception:                                      # noqa: BLE001
        return False
    return (getattr(cc, "TEXTOS_APROBADOS", False) is True
            and getattr(cc, "RUTAS_VALIDADAS", False) is True)


def es_alerta(fila: dict) -> bool:
    return str(fila.get("tipo", "")) in TIPOS_ALERTA


def _fila(marco: str, tipo: str, clave, n, valor, **kw) -> dict:
    kw.setdefault("escala", cat.label(str(clave)))
    fila = pub_est._fila(NIVEL, tipo, clave, n, valor, **kw)
    fila["detalle"]["marco"] = marco
    return fila


def _filas_marco(marco: str, a) -> list[dict]:
    filas: list[dict] = []
    fiab = ({f["clave"]: f for _, f in a.fiabilidad.iterrows()}
            if a.fiabilidad is not None and not a.fiabilidad.empty else {})
    if a.descriptivos is not None and not a.descriptivos.empty:
        for _, f in a.descriptivos.iterrows():
            alfa = fiab.get(f["clave"], {})
            filas.append(_fila(marco, "descriptivo", f["clave"], f["n"], f["M"],
                               escala=f["escala"], DE=f["DE"], Mdn=f["Mdn"], rango=f["rango"],
                               P25=f["P25"], P75=f["P75"], pct_faltante=f["pct_faltante"],
                               direccion=f["direccion"], fuente=f["fuente"],
                               alpha=alfa.get("alpha"), alpha_ic_inf=alfa.get("ic_inf"),
                               alpha_ic_sup=alfa.get("ic_sup"),
                               n_items=alfa.get("n_items")))
    if a.bandas is not None and not a.bandas.empty:
        for _, f in a.bandas.iterrows():
            filas.append(_fila(marco, "banda", f["clave"], f["n"], f["pct_alto_o_muy_alto"],
                               escala=f["escala"], pct_b0=f["pct_b0"], pct_b1=f["pct_b1"],
                               pct_b2=f["pct_b2"], pct_b3=f["pct_b3"],
                               etiquetas=list(f["etiquetas"]), fuente=FUENTE_BANDAS))
    if a.cortes is not None and not a.cortes.empty:
        for _, f in a.cortes.iterrows():
            filas.append(_fila(marco, "corte", f["clave"], f["n"], f["pct"],
                               ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                               indicador=f["indicador"], fuente=f["fuente"]))
    if a.terciles is not None and not a.terciles.empty:
        for _, f in a.terciles.iterrows():
            filas.append(_fila(marco, "tercil", f["clave"], f["n"], None, escala=f["escala"],
                               corte_bajo=f["corte_bajo"], corte_alto=f["corte_alto"],
                               nota=f["nota"]))
    if a.correlaciones is not None and not a.correlaciones.empty:
        for _, f in a.correlaciones.iterrows():
            filas.append(_fila(marco, "correlacion", f["a"], f["n"], f["rho"],
                               ic_inf=f["ic_inf"], ic_sup=f["ic_sup"], variable_b=f["b"],
                               etiqueta_b=f["etiqueta_b"], p=f["p"], q_bh=f["q_bh"],
                               significativa=bool(f["significativa"])))
    for tabla, agrupacion in ((a.por_grado, "Grado"), (a.por_colegio, "Colegio")):
        if tabla is None or tabla.empty:
            continue
        for _, f in tabla.iterrows():
            for col in [c for c in tabla.columns if c.startswith("M·")]:
                grupo = col[2:]
                n_col = f"n·{grupo}"
                if n_col not in tabla.columns or pd.isna(f[col]) or pd.isna(f[n_col]):
                    continue
                from src.cuidadores.pipeline import media_acota_corte
                if media_acota_corte(f["clave"], f[col], f[n_col]):
                    continue                    # la media acotaría un corte suprimido
                filas.append(_fila(marco, "grupo", f["clave"], f[n_col], f[col],
                                   escala=f["escala"], agrupacion=agrupacion, grupo=grupo,
                                   p=f["p"], eta2=f.get("eta2"), q_bh=f.get("q_bh")))
    n_nivel = ((a.muestra or {}).get("base") or {}).get("n_nivel", a.n)
    for clave, valor in (a.icc or {}).items():
        if valor is not None and valor == valor:
            filas.append(_fila(marco, "icc", clave, n_nivel, valor,
                               nota="Proporción de varianza entre colegios"))
    for columna, grupos in (getattr(a, "subgrupos", None) or {}).items():
        for grupo, s in grupos.items():
            filas.extend(_filas_subgrupo(marco, columna, grupo, s))
    filas.extend(_filas_alertas(marco, a))
    if a.muestra:
        filas.append(_fila(
            marco, "muestra", "muestra", a.n, a.n, escala="Descripción de la muestra",
            muestra={k: (pub_est._enmascarar_conteos(v) if isinstance(v, dict) else v)
                     for k, v in a.muestra.items()},
            enmascarados=a.enmascarados or {}, escalas=list(a.escalas or []),
            avisos=list(a.avisos or [])))
    return filas


def _filas_subgrupo(marco: str, columna: str, grupo: str, s) -> list[dict]:
    if s is None or s.n < cat.MIN_GROUP_N:
        return []
    comun = dict(agrupacion=columna, grupo=str(grupo), n_grupo=s.n)
    filas: list[dict] = []
    if s.bandas is not None and not s.bandas.empty:
        for _, f in s.bandas.iterrows():
            if f["n"] < cat.MIN_GROUP_N:
                continue
            filas.append(_fila(marco, "banda_grupo", f["clave"], f["n"],
                               f["pct_alto_o_muy_alto"], escala=f["escala"],
                               pct_b0=f["pct_b0"], pct_b1=f["pct_b1"], pct_b2=f["pct_b2"],
                               pct_b3=f["pct_b3"], etiquetas=list(f["etiquetas"]),
                               fuente=FUENTE_BANDAS, **comun))
    if s.cortes is not None and not s.cortes.empty:
        for _, f in s.cortes.iterrows():
            if f["n"] < cat.MIN_GROUP_N:
                continue
            filas.append(_fila(marco, "corte_grupo", f["clave"], f["n"], f["pct"],
                               ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                               indicador=f["indicador"], fuente=f["fuente"], **comun))
    return filas


def _filas_alertas(marco: str, a) -> list[dict]:
    """Filas `alerta` (total) y `alerta_grupo` de las señales del adulto. Nunca casos."""
    from src.cuidadores import alertas
    from src.cuidadores import comunidad_catalogo as cc
    t = getattr(a, "alertas", None)
    if not isinstance(t, pd.DataFrame) or t.empty:
        return []
    filas: list[dict] = []
    for f in t.to_dict("records"):
        if int(f["n"]) < cat.MIN_GROUP_N or f["alerta"] not in cc.ALERTAS:
            continue
        nombre = cc.ALERTAS[f["alerta"]].nombre
        comun = dict(escala=nombre, ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                     indicador=nombre, estado=str(f["estado"]))
        if f["agrupacion"] == alertas.TOTAL:
            filas.append(_fila(marco, "alerta", f["alerta"], f["n"], f["pct"], **comun))
        elif f["alerta"] not in alertas.SOLO_TOTAL:
            filas.append(_fila(marco, "alerta_grupo", f["alerta"], f["n"], f["pct"],
                               agrupacion=f["agrupacion"], grupo=str(f["grupo"]), **comun))
    return filas


# Campos del informe de la carga que se publican (para la vista de investigadores
# del despliegue). Nada por ola: ni `por_ola`, ni los repetidos entre olas. Los
# `avisos` no van: repiten conteos exactos que aquí salen enmascarados.
CAMPOS_INGESTA = ("filas_archivo", "sin_consentimiento", "respuestas_validas", "por_quien",
                  "cuidadores_distintos", "respuestas_repetidas_cuidador", "filas_nino",
                  "hijo2", "mismo_nino_misma_respuesta", "mismo_nino_otro_cuidador",
                  "ninos_unicos", "edad_no_numerica", "edad_fuera_de_rango",
                  "curso_sin_resolver", "grados", "colegios_cuidador", "colegios_nino",
                  "colegio_no_reconocido", "respuestas_columna6_pss",
                  "etiquetas_no_mapeadas", "cobertura_ari", "faltantes_por_bloque")
# Porcentajes, no conteos: no se enmascaran.
CAMPOS_SIN_ENMASCARAR = ("faltantes_por_bloque",)


def aplanar_ingesta(informe) -> list[dict]:
    """Una fila con el flujo de la muestra; todo conteo de 1 a 9 sale como «<10»."""
    if informe is None:
        return []
    detalle = {}
    for campo in CAMPOS_INGESTA:
        valor = getattr(informe, campo, None)
        if valor in (None, [], {}):
            continue
        if campo not in CAMPOS_SIN_ENMASCARAR:
            valor = (pub_est._enmascarar_conteos(valor) if isinstance(valor, dict)
                     else pub_est._enmascarar_conteos({campo: valor})[campo])
        detalle[campo] = valor
    validas = getattr(informe, "respuestas_validas", 0) or 0
    return [_fila(cat.MARCO_CUIDADOR, "ingesta", "flujo_exclusiones",
                  max(int(validas), cat.MIN_GROUP_N), validas,
                  escala="Flujo de exclusiones", ingesta=detalle)]


def aplanar(ac) -> list[dict]:
    """Filas agregadas de un análisis YA preparado (`comunidad.preparar`)."""
    if getattr(ac, "ola", None):
        raise PublicacionInsegura("No se publica por ola: use el análisis de todas las olas.")
    filas: list[dict] = []
    for marco, a in ac.marcos.items():
        if a is not None:
            filas.extend(_filas_marco(marco, a))
    return filas + aplanar_ingesta(getattr(ac, "informe", None))


def verificar(filas: list[dict]) -> None:
    """Las guardas de estudiantes y, además, que todo sea del nivel «cuidadores»."""
    pub_est.verificar(filas)
    otros = [i for i, f in enumerate(filas) if f.get("nivel") != NIVEL
             or (f.get("detalle") or {}).get("marco") not in cat.NOMBRES_MARCO]
    if otros:
        raise PublicacionInsegura(f"No se publicó nada: {len(otros)} fila(s) sin nivel "
                                  "«cuidadores» o sin marco.")


def verificar_restas(ac) -> list[str]:
    """`cuidadores.auditoria.auditar` sobre los marcos que se publican."""
    from src.cuidadores import auditoria
    return auditoria.auditar(ac.marcos)


def version_analisis(ac) -> str:
    return pub_est.version_analisis(dict(ac.marcos))


def publicar(ac, notas: str = "", publicar_ya: bool = False, cliente=None) -> dict:
    """Sube el lote del análisis preparado. Devuelve el resumen de lo insertado."""
    filas = aplanar(ac)
    verificar(filas)
    restas = verificar_restas(ac)
    if restas:
        raise PublicacionInsegura(
            "No se publicó nada: la auditoría de cuidadores encontró cifras que delatan:\n  - "
            + "\n  - ".join(restas[:20]) + ("\n  … y más" if len(restas) > 20 else ""))
    alertas_omitidas = 0
    if publicar_ya and not alertas_aprobadas():
        alertas_omitidas = sum(1 for f in filas if es_alerta(f))
        filas = [f for f in filas if not es_alerta(f)]
        if alertas_omitidas:
            print(f"{AVISO_ALERTAS_NO_APROBADAS}: con --publicar-ya no se suben sus "
                  f"{alertas_omitidas} filas.", file=sys.stderr)
    elif not alertas_aprobadas() and any(es_alerta(f) for f in filas):
        print(f"{AVISO_ALERTAS_NO_APROBADAS}: la corrida queda oculta con sus filas de señales. "
              "No la abra a mano; publíquela de nuevo con --publicar-ya, que las omite.",
              file=sys.stderr)
    cli = cliente or pub_est._cliente()
    tabla = lambda t: cli.postgrest.schema(ESQUEMA).table(t)  # noqa: E731
    corrida = dict(modulo=MODULO, version_analisis=version_analisis(ac),
                   n_secundaria=None, n_primaria=None, notas=notas or None,
                   publicada=False)
    res = tabla(TABLA_CORRIDAS).insert(corrida).execute()
    corrida_id = res.data[0]["id"]
    try:
        for i in range(0, len(filas), 500):
            lote = [dict(f, corrida_id=corrida_id) for f in filas[i:i + 500]]
            tabla(TABLA_RESULTADOS).insert(lote).execute()
    except Exception:
        try:
            tabla(TABLA_RESULTADOS).delete().eq("corrida_id", corrida_id).execute()
            tabla(TABLA_CORRIDAS).delete().eq("id", corrida_id).execute()
        except Exception:                                  # noqa: BLE001
            pass
        raise
    publicada, otras_despublicadas = False, False
    if publicar_ya:
        tabla(TABLA_CORRIDAS).update({"publicada": True}).eq("id", corrida_id).execute()
        publicada = True
        try:
            (tabla(TABLA_CORRIDAS).update({"publicada": False})
             .eq("modulo", MODULO).neq("id", corrida_id).execute())
            otras_despublicadas = True
        except Exception as exc:                           # noqa: BLE001
            print(f"AVISO: la corrida {corrida_id} quedó publicada, pero no se pudieron "
                  f"despublicar las demás corridas de «{MODULO}» ({exc}). Despublique a mano: "
                  f"UPDATE obs360.corridas SET publicada = false WHERE modulo = '{MODULO}' "
                  f"AND id <> {corrida_id};", file=sys.stderr)
    return dict(corrida_id=corrida_id, version=corrida["version_analisis"], filas=len(filas),
                publicada=publicada, otras_corridas_despublicadas=otras_despublicadas,
                alertas_omitidas=alertas_omitidas)


def _resumen(filas: list[dict]) -> None:
    print(f"Lote: {len(filas)} filas agregadas")
    for tipo, cuenta in pd.Series([f["tipo"] for f in filas]).value_counts().items():
        print(f"  {tipo}: {cuenta}")
    print(f"  n mínimo en el lote: {min(f['n'] for f in filas)} "
          f"(el umbral es {cat.MIN_GROUP_N})")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Publica los agregados de Cuidadores 360.")
    p.add_argument("--ensayo", action="store_true",
                   help="no toca la red; deja el lote en un JSON (sale con 2 si la "
                        "auditoría encuentra algo)")
    p.add_argument("--salida", default="lote_cuidadores.json", help="JSON del ensayo")
    p.add_argument("--notas", default="", help="nota para la corrida")
    p.add_argument("--publicar-ya", action="store_true",
                   help="abre la corrida y cierra las demás de cuidadores")
    p.add_argument("--archivo", default=None,
                   help="exportación de «Cuidando al Cuidador» (por defecto, la de la "
                        "carpeta de datos fuente)")
    args = p.parse_args(argv)

    from src.core.seudonimo import ClaveAusente
    from src.cuidadores import comunidad, pipeline
    try:
        ac = comunidad.preparar(pipeline.cargar_y_analizar(args.archivo))
    except (ClaveAusente, FileNotFoundError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    filas = aplanar(ac)
    try:
        verificar(filas)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    _resumen(filas)
    print(f"  versión: {version_analisis(ac)}")
    if args.ensayo:
        n_alertas = sum(1 for f in filas if es_alerta(f))
        if n_alertas and not alertas_aprobadas():
            print(f"{AVISO_ALERTAS_NO_APROBADAS}: el JSON trae sus {n_alertas} filas para "
                  "revisarlas, pero --publicar-ya no las subiría hasta la aprobación.")
        restas = verificar_restas(ac)
        if restas:
            print("AVISO: la auditoría encontró problemas:\n  - " + "\n  - ".join(restas))
        with open(args.salida, "w", encoding="utf-8") as fh:
            json.dump(dict(modulo=MODULO, version=version_analisis(ac), filas=filas), fh,
                      ensure_ascii=False, indent=1, default=str)
        print(f"✓ Ensayo. Nada se subió. Lote escrito en {args.salida}")
        return 2 if restas else 0
    try:
        resumen = publicar(ac, notas=args.notas, publicar_ya=args.publicar_ya)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    print(f"✓ Corrida {resumen['corrida_id']} con {resumen['filas']} filas. "
          f"Publicada: {resumen['publicada']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
