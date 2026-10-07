"""
Publicación de resultados de estudiantes en Supabase — Observatorio 360.

Convierte los objetos `Analisis` en filas agregadas y las sube al esquema
`obs360` (ver supabase/estudiantes_schema.sql).

QUÉ SUBE
Solo agregados: una fila por nivel, grupo, tipo e indicador. Ni una respuesta
individual, ni un identificador, ni un nombre. Las alertas de grupo (`alerta` y
`alerta_grupo`, spec §5.4) llevan n, % e IC donde la supresión los deja, y el
estado solo donde hay %; nunca casos. La sensibilidad y la distribución de los
ítems de las alertas no se publican: son de la vista local de investigadores.

GUARDAS, EN ESTE ORDEN
  1. `aplanar` construye las filas únicamente desde tablas ya agregadas del
     objeto `Analisis` (calculadas sobre la base publicable y la copia
     enmascarada todo o nada por columna); nunca toca `Analisis.datos`.
  2. `verificar` rechaza el lote completo si aparece un grupo con n < MIN_GROUP_N,
     una columna de identificación o algo con forma de identificador (E/C/N +
     8 hexadecimales, la misma regla que la base) en `grupo` o en `clave`.
     Falla el lote entero, no la fila: si una guarda salta, hay un error de
     programación y publicar «lo que se pueda» lo esconde.
  3. `verificar_restas` audita las restas entre nivel, colegios, grados y
     celdas colegio×grado (privacidad.auditar): si alguna diferencia deja un
     grupo de 1 a MIN_GROUP_N − 1, no se publica nada. También audita las
     cifras que no delatan (supresion.auditar): toda proporción publicada
     tiene de MIN_CASOS a n − MIN_CASOS casos, también tras restar. El número
     de casos no se publica nunca (`verificar` lo rechaza).
  4. El esquema tiene un CHECK de n >= 10 y de identificadores, y RLS sin
     política de escritura para el rol anónimo: la base rechazaría el error
     aunque las guardas anteriores fallaran.
  5. La corrida entra oculta (`publicada = false`) y solo se abre con todos sus
     resultados dentro; al abrirla con `--publicar-ya` se despublican las demás
     corridas del módulo (y la política de lectura solo deja ver la última).
  6. Mientras el equipo no apruebe textos y rutas de las alertas
     (`alertas_catalogo.TEXTOS_APROBADOS` y `RUTAS_VALIDADAS`), `--publicar-ya`
     no sube las filas `alerta` ni `alerta_grupo`: avisa y publica el resto (el
     panel simplemente no aparece en público). `--ensayo` las deja en el JSON
     y avisa.

USO
    # ensayo: no toca la red, deja el lote en un JSON para revisarlo
    python -m src.estudiantes.publicar --ensayo --salida /tmp/lote.json

    # publicación real (exige SUPABASE_URL y SUPABASE_SERVICE_KEY)
    python -m src.estudiantes.publicar --notas "primera carga"

La corrida se crea con `publicada = false`: nadie la ve hasta que el equipo la
aprueba, con `--publicar-ya` o cambiando la bandera en el panel de Supabase.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date

import numpy as np
import pandas as pd

from src.estudiantes import catalog as cat
from src.estudiantes import pipeline, privacidad, supresion

# Columnas que no pueden aparecer en nada que se publique
COLUMNAS_PROHIBIDAS = {"id", "nombre", "nombre_completo", "ts", "sede",
                       "colegio_nombre", "id_estudiante", "id_cuidador"}
TABLA_CORRIDAS = "corridas"
TABLA_RESULTADOS = "resultados"
ESQUEMA = "obs360"
MODULO = "estudiantes"
# Identificador de estudiante (E), cuidador (C) o niño (N): la misma regla que el
# CHECK `resultados_sin_id_estudiante` de la base (^[ECN][0-9a-f]{8}$, sin
# distinguir mayúsculas).
PATRON_ID = re.compile(r"[ECN][0-9a-f]{8}", re.IGNORECASE)
# Conteos de casos: nunca se publican (spec §5.4); con el % y el n son redundantes
# y, en grupos pequeños, delatan. Ver supresion.py.
CAMPOS_CONTEO_PROHIBIDOS = ("casos", "k_bajo", "k_alto")
# Filas de las alertas de grupo (spec §5.4): solo salen al público con textos y
# rutas aprobados por el equipo (alertas_catalogo).
TIPOS_ALERTA = ("alerta", "alerta_grupo")
AVISO_ALERTAS_NO_APROBADAS = (
    "AVISO: las alertas de grupo no están aprobadas (alertas_catalogo.TEXTOS_APROBADOS y "
    "RUTAS_VALIDADAS en False)")


def alertas_aprobadas() -> bool:
    """¿El equipo aprobó los textos y validó las rutas de las alertas? (spec §8)."""
    try:
        from src.estudiantes import alertas_catalogo as ac
    except Exception:                                      # noqa: BLE001
        return False
    return (getattr(ac, "TEXTOS_APROBADOS", False) is True
            and getattr(ac, "RUTAS_VALIDADAS", False) is True)


def es_alerta(fila: dict) -> bool:
    return str(fila.get("tipo", "")) in TIPOS_ALERTA


def _num(v):
    """Número JSON-serializable, o None."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float, int)):
        f = float(v)
        return None if not np.isfinite(f) else f
    return None


def _fila(nivel, tipo, clave, n, valor, *, escala=None, agrupacion="total",
          grupo=None, ic_inf=None, ic_sup=None, **detalle) -> dict:
    def limpiar(v):
        # Los booleanos van antes que los números: `bool` hereda de `int`, y
        # convertirlos a 1.0 rompe al leerlos (filtrar un DataFrame por una
        # columna de números se interpreta como selección de columnas).
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if isinstance(v, (int, float, np.number)):
            return _num(v)
        return v

    limpio = {k: limpiar(v) for k, v in detalle.items()
              if v is not None and (isinstance(v, (bool, np.bool_)) or v == v)}
    return dict(nivel=nivel, tipo=tipo, clave=str(clave),
                escala=escala or cat.meta(str(clave))["label"],
                agrupacion=agrupacion, grupo=grupo, n=int(n),
                valor=_num(valor), ic_inf=_num(ic_inf), ic_sup=_num(ic_sup),
                detalle=limpio)


def aplanar(analisis: dict) -> list[dict]:
    """Convierte {nivel: Analisis} en filas agregadas listas para insertar."""
    filas: list[dict] = []
    for nivel, a in analisis.items():
        if a is None:
            continue

        # descriptivos y fiabilidad
        fiab = ({f["clave"]: f for _, f in a.fiabilidad.iterrows()}
                if a.fiabilidad is not None and not a.fiabilidad.empty else {})
        if a.descriptivos is not None and not a.descriptivos.empty:
            for _, f in a.descriptivos.iterrows():
                alfa = fiab.get(f["clave"], {})
                filas.append(_fila(
                    nivel, "descriptivo", f["clave"], f["n"], f["M"],
                    escala=f["escala"], DE=f["DE"], Mdn=f["Mdn"],
                    minimo=f["min"], maximo=f["max"], rango=f["rango"],
                    P25=f["P25"], P75=f["P75"], P90=f["P90"], P95=f["P95"],
                    pct_faltante=f["pct_faltante"], direccion=f["direccion"],
                    validada=bool(f["validada"]),
                    alpha=alfa.get("alpha"), alpha_ic_inf=alfa.get("ic_inf"),
                    alpha_ic_sup=alfa.get("ic_sup")))

        # bandas del SDQ
        if a.bandas is not None and not a.bandas.empty:
            for _, f in a.bandas.iterrows():
                filas.append(_fila(
                    nivel, "banda", f["clave"], f["n"], f["pct_alto_o_muy_alto"],
                    escala=f["escala"],
                    pct_b0=f["pct_b0"], pct_b1=f["pct_b1"],
                    pct_b2=f["pct_b2"], pct_b3=f["pct_b3"],
                    etiquetas=list(f["etiquetas"]),
                    fuente=cat.FUENTE_BANDS_SELF))

        # prevalencias sobre corte
        if a.cortes is not None and not a.cortes.empty:
            for _, f in a.cortes.iterrows():
                filas.append(_fila(
                    nivel, "corte", f["clave"], f["n"], f["pct"],
                    ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                    indicador=f["indicador"], fuente=f["fuente"]))

        # terciles y percentiles
        if a.terciles is not None and not a.terciles.empty:
            for _, f in a.terciles.iterrows():
                filas.append(_fila(nivel, "tercil", f["clave"], f["n"], None,
                                   escala=f["escala"], corte_bajo=f["corte_bajo"],
                                   corte_alto=f["corte_alto"], nota=f["nota"]))
        if a.percentiles is not None and not a.percentiles.empty:
            for _, f in a.percentiles.iterrows():
                filas.append(_fila(nivel, "percentil", f["clave"], f["n"], f["P50"],
                                   escala=f["escala"], agrupacion="Sexo",
                                   grupo=f["sexo"], P75=f["P75"], P85=f["P85"],
                                   P90=f["P90"], P95=f["P95"]))

        # correlaciones
        if a.correlaciones is not None and not a.correlaciones.empty:
            for _, f in a.correlaciones.iterrows():
                filas.append(_fila(nivel, "correlacion", f["a"], f["n"], f["rho"],
                                   ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                                   variable_b=f["b"], etiqueta_b=f["etiqueta_b"],
                                   p=f["p"], q_bh=f["q_bh"],
                                   significativa=bool(f["significativa"])))

        # comparaciones por grupo
        if a.por_sexo is not None and not a.por_sexo.empty:
            for _, f in a.por_sexo.iterrows():
                for sexo, m, de, n in (("Mujer", f["M_mujer"], f["DE_mujer"], f["n_mujer"]),
                                       ("Hombre", f["M_hombre"], f["DE_hombre"], f["n_hombre"])):
                    filas.append(_fila(nivel, "grupo", f["clave"], n, m,
                                       escala=f["escala"], agrupacion="Sexo",
                                       grupo=sexo, DE=de, d=f["d"],
                                       magnitud=f["magnitud"], p=f["p"],
                                       q_bh=f["q_bh"]))
        for tabla, agrupacion in ((a.por_grado, "Grado"), (a.por_colegio, "Colegio")):
            if tabla is None or tabla.empty:
                continue
            for _, f in tabla.iterrows():
                for col in [c for c in tabla.columns if c.startswith("M·")]:
                    grupo = col[2:]
                    n_col = f"n·{grupo}"
                    if n_col not in tabla.columns or pd.isna(f[col]):
                        continue
                    filas.append(_fila(nivel, "grupo", f["clave"], f[n_col], f[col],
                                       escala=f["escala"], agrupacion=agrupacion,
                                       grupo=grupo, p=f["p"], eta2=f.get("eta2"),
                                       q_bh=f.get("q_bh")))

        # correlación con la edad
        if a.por_edad is not None and not a.por_edad.empty:
            for _, f in a.por_edad.iterrows():
                filas.append(_fila(nivel, "grupo", f["clave"], f["n"], f["rho"],
                                   escala=f["escala"], agrupacion="Edad",
                                   grupo="correlación", p=f["p"], q_bh=f["q_bh"]))

        # modelos
        for m in (a.modelos or []):
            for c in m["coeficientes"]:
                if c["predictor"] == "(constante)":
                    continue
                filas.append(_fila(nivel, "modelo", m["y"], m["n"], c["beta"],
                                   escala=m["y_etiqueta"], predictor=c["predictor"],
                                   etiqueta=c["etiqueta"], se=c["se"], p=c["p"],
                                   significativo=c["significativo"],
                                   R2=m["R2"], clusters=m["clusters"],
                                   aviso=m.get("aviso") or None))

        # CCI: se calcula sobre el nivel publicado, que puede ser menor que a.n
        n_nivel = ((a.muestra or {}).get("base") or {}).get("n_nivel", a.n)
        for clave, valor in (a.icc or {}).items():
            if valor is not None and valor == valor:
                filas.append(_fila(nivel, "icc", clave, n_nivel, valor,
                                   nota="Proporción de varianza entre colegios"))

        # contrastes por tercil (los suprimidos por pocos casos no se suben)
        for c in (a.contrastes or []):
            if c.get("suprimido"):
                continue
            filas.append(_fila(nivel, "contraste", c["resultado"],
                               c["n_bajo"] + c["n_alto"], c["pct_tercil_bajo"],
                               escala=c["resultado_etiqueta"],
                               agrupacion=c["protector"], grupo="tercil bajo",
                               pct_tercil_alto=c["pct_tercil_alto"],
                               n_bajo=c["n_bajo"], n_alto=c["n_alto"],
                               umbral=c["umbral"], razon=c.get("razon"),
                               protector_etiqueta=c["protector_etiqueta"]))

        # medias por ítem del PSSM (lo más accionable para los colegios)
        if a.items_pssm is not None and not a.items_pssm.empty:
            for _, f in a.items_pssm.iterrows():
                filas.append(_fila(nivel, "item", f["item"], f["n"], f["M"],
                                   escala=cat.PSSM.nombre, DE=f["DE"],
                                   orientado=True))

        # resultados por colegio, por grado y por celda colegio×grado para la
        # vista comunidad desplegada. Tipos propios («banda_grupo»…) para que el
        # lector no los confunda con los del nivel completo. Descartar las filas
        # que no llegan al mínimo es solo un respaldo: el enmascaramiento todo o
        # nada ya garantiza que cada columna tiene ≥ MIN_GROUP_N o 0 respuestas
        # válidas en cada grupo de la base.
        for columna, grupos in (getattr(a, "subgrupos", None) or {}).items():
            for grupo, s in grupos.items():
                filas.extend(_aplanar_subgrupo(nivel, columna, grupo, s))

        # alertas de grupo (spec §5.4): sin casos; estado solo donde hay %
        filas.extend(_aplanar_alertas(nivel, a))

        # descripción de la muestra, en una sola fila cuyo N es el del nivel
        if a.muestra:
            # La muestra va anidada en un solo campo: sus claves (n, sexo, edad…)
            # chocarían con las columnas de la fila. Los tamaños de grupo
            # (colegio_grado, base) no se tratan como sensibles (spec §5.1: dicen
            # cuántos respondieron, no qué respondieron); solo se enmascaran los
            # conteos por debajo del mínimo.
            filas.append(_fila(
                nivel, "muestra", "muestra", a.n, a.n,
                escala="Descripción de la muestra",
                muestra={k: (_enmascarar_conteos(v) if isinstance(v, dict) else v)
                         for k, v in a.muestra.items()},
                enmascarados=a.enmascarados or {}, escalas=list(a.escalas or []),
                avisos=list(a.avisos or [])))

        # comorbilidad entre indicadores con corte
        if a.solapamiento:
            filas.append(_fila(nivel, "solapamiento", "SDQ_y_ARI",
                               a.solapamiento.get("n", a.n),
                               a.solapamiento.get("pct_ambos"),
                               escala="Solapamiento entre indicadores",
                               solapamiento={k: v for k, v in a.solapamiento.items()
                                             if k != "n"}))
    return filas


def _aplanar_subgrupo(nivel: str, columna: str, grupo: str, s) -> list[dict]:
    """Filas de un colegio o un grado: solo lo que la vista comunidad muestra."""
    if s is None or s.n < cat.MIN_GROUP_N:
        return []
    filas: list[dict] = []
    comun = dict(agrupacion=columna, grupo=str(grupo), n_grupo=s.n)
    if s.bandas is not None and not s.bandas.empty:
        for _, f in s.bandas.iterrows():
            if f["n"] < cat.MIN_GROUP_N:
                continue
            filas.append(_fila(nivel, "banda_grupo", f["clave"], f["n"],
                               f["pct_alto_o_muy_alto"], escala=f["escala"],
                               pct_b0=f["pct_b0"], pct_b1=f["pct_b1"],
                               pct_b2=f["pct_b2"], pct_b3=f["pct_b3"],
                               etiquetas=list(f["etiquetas"]),
                               fuente=cat.FUENTE_BANDS_SELF, **comun))
    if s.cortes is not None and not s.cortes.empty:
        for _, f in s.cortes.iterrows():
            if f["n"] < cat.MIN_GROUP_N:
                continue
            filas.append(_fila(nivel, "corte_grupo", f["clave"], f["n"], f["pct"],
                               ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                               indicador=f["indicador"], fuente=f["fuente"], **comun))
    for c in (s.contrastes or []):
        if c.get("suprimido"):
            continue
        if c["n_bajo"] < cat.MIN_GROUP_N or c["n_alto"] < cat.MIN_GROUP_N:
            continue
        filas.append(_fila(nivel, "contraste_grupo", c["resultado"],
                           c["n_bajo"] + c["n_alto"], c["pct_tercil_bajo"],
                           escala=c["resultado_etiqueta"],
                           protector=c["protector"],
                           pct_tercil_alto=c["pct_tercil_alto"],
                           n_bajo=c["n_bajo"], n_alto=c["n_alto"],
                           umbral=c["umbral"], razon=c.get("razon"),
                           protector_etiqueta=c["protector_etiqueta"], **comun))
    if s.items_pssm is not None and not s.items_pssm.empty:
        for _, f in s.items_pssm.iterrows():
            if f["n"] < cat.MIN_GROUP_N:
                continue
            filas.append(_fila(nivel, "item_grupo", f["item"], f["n"], f["M"],
                               escala=cat.PSSM.nombre, DE=f["DE"], orientado=True,
                               **comun))
    return filas


def _aplanar_alertas(nivel: str, a) -> list[dict]:
    """Filas `alerta` (nivel) y `alerta_grupo` desde `Analisis.alertas`. Nunca casos.

    La tabla ya viene suprimida (supresion.aplicar) y con el estado calculado
    solo con cifras publicadas (alertas.estado).
    """
    from src.estudiantes import alertas as al
    from src.estudiantes import alertas_catalogo as ac
    tabla = getattr(a, "alertas", None)
    if not isinstance(tabla, pd.DataFrame) or tabla.empty:
        return []
    subgrupos = getattr(a, "subgrupos", None) or {}
    filas: list[dict] = []
    for f in tabla.to_dict("records"):
        if int(f["n"]) < cat.MIN_GROUP_N or f["alerta"] not in ac.ALERTAS:
            continue
        nombre = ac.ALERTAS[f["alerta"]].nombre
        comun = dict(escala=nombre, ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                     indicador=nombre, estado=str(f["estado"]))
        if f["agrupacion"] == al.TOTAL:
            filas.append(_fila(nivel, "alerta", f["alerta"], f["n"], f["pct"], **comun))
            continue
        s = (subgrupos.get(f["agrupacion"]) or {}).get(str(f["grupo"]))
        if s is None or s.n < cat.MIN_GROUP_N:
            continue
        filas.append(_fila(nivel, "alerta_grupo", f["alerta"], f["n"], f["pct"],
                           agrupacion=f["agrupacion"], grupo=str(f["grupo"]),
                           n_grupo=s.n, **comun))
    return filas


def _enmascarar_conteos(d: dict) -> dict:
    """Sustituye por «<10» cualquier celda de 1 a MIN_GROUP_N − 1.

    Un cero no identifica a nadie y se deja: la vista necesita saber que no
    hay respuestas fuera de la base, no «menos de 10».

    Las distribuciones de la muestra (edad, colegio) pueden tener celdas de
    pocos casos. El recuento exacto de esas celdas solo queda en la corrida
    local; lo que se publica dice «<10».
    """
    salida = {}
    for k, v in d.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v < cat.MIN_GROUP_N:
            salida[str(k)] = f"<{cat.MIN_GROUP_N}"
        else:
            salida[str(k)] = v
    return salida


CAMPOS_INGESTA = ("filas_archivo", "sin_consentimiento", "excluidas_prueba",
                  "excluidas_colegio_unico", "duplicados_eliminados",
                  "filas_validas", "erq_invalidado", "escalas_detectadas",
                  "escalas_ausentes", "etiquetas_no_mapeadas",
                  "faltantes_por_escala", "edades_fuera_de_rango",
                  "colegios_enmascarados", "crudo_colegio_grado", "avisos")


# Conteos por categoría (colegio×grado, escala, bloque) que pueden ser de 1 a
# MIN_GROUP_N − 1 y señalar a pocos estudiantes de un grupo concreto: se publican
# enmascarados («<10»). `erq_invalidado` es un escalar, pero en la práctica es un
# conteo de un colegio (el artefacto apareció en uno solo). Los totales de
# exclusión del flujo (sin consentimiento, prueba, colegio único, duplicados) se
# publican como número: son pasos del diagrama de la muestra de todo el nivel.
CAMPOS_CONTEO_INGESTA = ("crudo_colegio_grado", "edades_fuera_de_rango", "erq_invalidado")


def aplanar_ingesta(informes: list) -> list[dict]:
    """El flujo de exclusiones, que es el diagrama de la muestra del artículo."""
    filas = []
    for inf in (informes or []):
        detalle = {}
        for campo in CAMPOS_INGESTA:
            valor = getattr(inf, campo, None)
            if valor in (None, [], {}):
                continue
            if campo in CAMPOS_CONTEO_INGESTA:
                valor = (_enmascarar_conteos(valor) if isinstance(valor, dict)
                         else _enmascarar_conteos({campo: valor})[campo])
            detalle[campo] = valor
        erq = detalle.get("erq_invalidado")
        if isinstance(erq, str) and detalle.get("avisos"):
            # el aviso del ERQ repite la cifra exacta: se enmascara igual
            detalle["avisos"] = [re.sub(r"^ERQ-CA: \d+", f"ERQ-CA: {erq}", str(av))
                                 for av in detalle["avisos"]]
        colegios = getattr(inf, "colegios", None)
        if colegios:
            detalle["colegios"] = _enmascarar_conteos(colegios)
        filas.append(_fila(inf.nivel, "ingesta", "flujo_exclusiones",
                           max(int(getattr(inf, "filas_validas", 0) or 0),
                               cat.MIN_GROUP_N),
                           getattr(inf, "filas_validas", None),
                           escala="Flujo de exclusiones", ingesta=detalle))
    return filas


class PublicacionInsegura(RuntimeError):
    """El lote no cumple una guarda de privacidad: no se publica nada."""


def verificar(filas: list[dict]) -> None:
    """Rechaza el lote completo si algo no cumple las reglas de privacidad."""
    problemas: list[str] = []
    for i, f in enumerate(filas):
        if int(f["n"]) < cat.MIN_GROUP_N:
            problemas.append(f"fila {i} ({f['tipo']}/{f['clave']}/{f['grupo']}): "
                             f"n = {f['n']} < {cat.MIN_GROUP_N}")
        texto = json.dumps(f, ensure_ascii=False, default=str).lower()
        for prohibida in COLUMNAS_PROHIBIDAS:
            if f'"{prohibida}"' in texto:
                problemas.append(f"fila {i}: contiene la columna prohibida «{prohibida}»")
        for campo in CAMPOS_CONTEO_PROHIBIDOS:
            if campo in (f.get("detalle") or {}):
                problemas.append(f"fila {i} ({f['tipo']}/{f['clave']}): publica el conteo "
                                 f"«{campo}»; solo se publican proporciones y n")
        if (str(f.get("tipo", "")).startswith("alerta") and f.get("valor") is None
                and (f.get("detalle") or {}).get("estado", "sin_estado") != "sin_estado"):
            problemas.append(f"fila {i} ({f['tipo']}/{f['clave']}/{f['grupo']}): una alerta "
                             "sin porcentaje publicado no puede llevar estado")
        for campo in ("grupo", "clave"):
            valor = str(f.get(campo) or "")
            if PATRON_ID.fullmatch(valor):
                problemas.append(f"fila {i}: el campo {campo} «{valor}» tiene forma de "
                                 "identificador de estudiante, cuidador o niño")
    if problemas:
        raise PublicacionInsegura(
            "No se publicó nada. El lote tiene "
            f"{len(problemas)} problema(s) de privacidad:\n  - "
            + "\n  - ".join(problemas[:20])
            + ("\n  … y más" if len(problemas) > 20 else ""))


def verificar_restas(analisis: dict) -> list[str]:
    """Problemas de resta en cualquier nivel con datos.

    Dos auditorías: `privacidad.auditar` (ninguna resta de N deja un grupo de
    1 a MIN_GROUP_N − 1; todas las columnas de los datos enmascarados, no solo
    las publicadas) y `supresion.auditar` (cifras que no delatan: cada
    proporción publicada tiene de MIN_CASOS a n − MIN_CASOS casos, y ninguna
    suma o resta de proporciones publicadas deja un conjunto que no cumpla; también las alertas de grupo, como una familia más).
    """
    problemas: list[str] = []
    for nivel, a in (analisis or {}).items():
        if a is None or getattr(a, "base", None) is None or a.datos is None or a.datos.empty:
            continue
        problemas += [f"{nivel} · {p}" for p in
                      privacidad.auditar(a.datos, a.base, privacidad.columnas_de_analisis(a.datos))]
        problemas += [f"{nivel} · {p}" for p in supresion.auditar(a)]
    return problemas


def version_analisis(analisis: dict) -> str:
    """Huella de la estructura analizada, no de los datos."""
    partes = []
    for nivel in sorted(analisis):
        a = analisis[nivel]
        if a is None:
            continue
        partes.append(f"{nivel}:{a.n}:{','.join(sorted(a.escalas))}")
    huella = hashlib.sha1("|".join(partes).encode()).hexdigest()[:12]
    return f"{date.today().isoformat()}-{huella}"


RUTA_SECRETOS = os.path.join(".streamlit", "secrets.toml")


def credenciales_escritura(ruta_secretos: str = RUTA_SECRETOS) -> tuple[str | None, str | None]:
    """(url, clave service_role): del entorno o, si falta, del archivo local de secretos.

    El publicador corre en la máquina de quien procesa, donde las claves viven
    en `.streamlit/secrets.toml` (ignorado por git). Leerlo aquí evita tener
    que exportarlas a mano antes de cada corrida. Se lee con `tomllib`, no con
    Streamlit, para no arrancar nada de la aplicación.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if (not url or not key) and os.path.exists(ruta_secretos):
        import tomllib
        with open(ruta_secretos, "rb") as fh:
            secretos = tomllib.load(fh)
        url = url or secretos.get("SUPABASE_URL")
        key = key or secretos.get("SUPABASE_SERVICE_KEY")
    return url, key


def _cliente(url: str | None = None, key: str | None = None):
    """Cliente de Supabase con la clave de servicio. Escribir exige service_role."""
    from supabase import create_client
    url_sec, key_sec = credenciales_escritura()
    url = url or url_sec
    key = key or key_sec
    if not url or not key:
        raise RuntimeError(
            "Faltan credenciales. Se necesita SUPABASE_URL y SUPABASE_SERVICE_KEY "
            "(la clave service_role, no la anon: el esquema no da permiso de "
            f"escritura al rol anónimo a propósito), en el entorno o en {RUTA_SECRETOS}.")
    return create_client(url, key)


def publicar(analisis: dict, notas: str = "", publicar_ya: bool = False,
             cliente=None, informes: list | None = None) -> dict:
    """Sube el lote. Devuelve el resumen de lo insertado."""
    filas = aplanar(analisis) + aplanar_ingesta(informes)
    verificar(filas)
    restas = verificar_restas(analisis)
    if restas:
        raise PublicacionInsegura(
            "No se publicó nada: la auditoría encontró cifras que delatan. Alguna resta "
            f"entre cifras publicadas dejaría un grupo de menos de {cat.MIN_GROUP_N} "
            f"respuestas, o alguna proporción publicada (directa o por resta) tendría "
            f"menos de {supresion.MIN_CASOS} casos o menos de {supresion.MIN_CASOS} no "
            "casos:\n  - " + "\n  - ".join(restas[:20])
            + ("\n  … y más" if len(restas) > 20 else ""))
    alertas_omitidas = 0
    if publicar_ya and not alertas_aprobadas():
        alertas_omitidas = sum(1 for f in filas if es_alerta(f))
        filas = [f for f in filas if not es_alerta(f)]
        if alertas_omitidas:
            print(f"{AVISO_ALERTAS_NO_APROBADAS}: con --publicar-ya no se suben sus "
                  f"{alertas_omitidas} filas. El resto se publica y el panel no aparece en "
                  "público hasta que el equipo apruebe y se vuelva a publicar.",
                  file=sys.stderr)
    elif not alertas_aprobadas() and any(es_alerta(f) for f in filas):
        print(f"{AVISO_ALERTAS_NO_APROBADAS}: la corrida queda oculta con sus filas de "
              "alertas. No la abra a mano (UPDATE … publicada = true) hasta la aprobación: "
              "publíquela de nuevo con --publicar-ya, que las omite.", file=sys.stderr)
    cli = cliente or _cliente()
    tabla = lambda t: cli.postgrest.schema(ESQUEMA).table(t)  # noqa: E731

    corrida = dict(
        modulo=MODULO, version_analisis=version_analisis(analisis),
        n_secundaria=(analisis.get(cat.NIVEL_SECUNDARIA).n
                      if analisis.get(cat.NIVEL_SECUNDARIA) else None),
        n_primaria=(analisis.get(cat.NIVEL_PRIMARIA).n
                    if analisis.get(cat.NIVEL_PRIMARIA) else None),
        notas=notas or None, publicada=False)
    res = tabla(TABLA_CORRIDAS).insert(corrida).execute()
    corrida_id = res.data[0]["id"]

    try:
        for i in range(0, len(filas), 500):
            lote = [dict(f, corrida_id=corrida_id) for f in filas[i:i + 500]]
            tabla(TABLA_RESULTADOS).insert(lote).execute()
    except Exception:
        # La corrida sigue oculta (publicada = false); se intenta borrarla.
        try:
            tabla(TABLA_RESULTADOS).delete().eq("corrida_id", corrida_id).execute()
            tabla(TABLA_CORRIDAS).delete().eq("id", corrida_id).execute()
        except Exception:
            pass
        raise

    publicada = False
    otras_despublicadas = False
    if publicar_ya:
        # Solo con todos los resultados dentro se abre la corrida nueva; y dos
        # corridas legibles a la vez permitirían restar una de otra y aislar
        # las respuestas nuevas, así que se cierran las demás del módulo.
        tabla(TABLA_CORRIDAS).update({"publicada": True}).eq("id", corrida_id).execute()
        publicada = True
        try:
            (tabla(TABLA_CORRIDAS).update({"publicada": False})
             .eq("modulo", MODULO).neq("id", corrida_id).execute())
            otras_despublicadas = True
        except Exception as exc:                                  # noqa: BLE001
            # La corrida nueva ya está abierta y completa: no se deshace. Con la
            # migración 2026-10-07 el público solo lee la última publicada del
            # módulo; sin ella, las viejas siguen legibles hasta cerrarlas a mano.
            print(f"AVISO: la corrida {corrida_id} quedó publicada, pero no se pudieron "
                  f"despublicar las demás corridas de «{MODULO}» ({exc}). Compruebe que "
                  "corrió la migración supabase/migraciones/2026-10-07-modulo-y-ultima-"
                  "corrida.sql y despublique a mano: UPDATE obs360.corridas SET "
                  f"publicada = false WHERE modulo = '{MODULO}' AND id <> {corrida_id};",
                  file=sys.stderr)

    return dict(corrida_id=corrida_id, version=corrida["version_analisis"],
                filas=len(filas), publicada=publicada,
                otras_corridas_despublicadas=otras_despublicadas,
                alertas_omitidas=alertas_omitidas)


def mensajes_para_subir() -> list[dict]:
    """Los textos del catálogo, en el formato de la tabla obs360.mensajes."""
    salida = []
    for clave, m in cat.MENSAJES.items():
        for rol in m.solo_roles:
            accion = {"colegio": m.accion_colegio, "familia": m.accion_familia,
                      "municipio": m.accion_municipio}[rol]
            if not accion:
                continue
            salida.append(dict(clave=clave, titulo=m.titulo, significa=m.significa,
                               accion_rol=rol, accion=accion, vigente=True))
    return salida


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--ensayo", action="store_true",
                   help="no toca la red; deja el lote en un JSON (se escribe aunque la "
                        "auditoría falle, para revisarlo; en ese caso sale con código 2)")
    p.add_argument("--salida", default="lote_estudiantes.json",
                   help="ruta del JSON en modo ensayo")
    p.add_argument("--notas", default="", help="nota para la corrida")
    p.add_argument("--publicar-ya", action="store_true",
                   help="marca la corrida como publicada (por defecto queda oculta "
                        "hasta que el equipo la apruebe)")
    p.add_argument("--base", default=None,
                   help="carpeta donde están los formularios (por defecto, la de datos "
                        "fuente: OBS360_DATOS_DIR o ../datos_fuente_360/estudiantes)")
    args = p.parse_args(argv)

    analisis, informes = pipeline.cargar_y_analizar(base=args.base)
    filas = aplanar(analisis) + aplanar_ingesta(informes)
    try:
        verificar(filas)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2

    print(f"Lote: {len(filas)} filas agregadas")
    for nivel, a in analisis.items():
        print(f"  {nivel}: n = {a.n}")
    por_tipo = pd.Series([f["tipo"] for f in filas]).value_counts()
    for tipo, cuenta in por_tipo.items():
        print(f"  {tipo}: {cuenta}")
    print(f"  versión: {version_analisis(analisis)}")
    print(f"  n mínimo en el lote: {min(f['n'] for f in filas)} "
          f"(el umbral es {cat.MIN_GROUP_N})")

    if args.ensayo:
        n_alertas = sum(1 for f in filas if es_alerta(f))
        if n_alertas and not alertas_aprobadas():
            print(f"{AVISO_ALERTAS_NO_APROBADAS}: el JSON trae sus {n_alertas} filas para "
                  "revisarlas, pero --publicar-ya no las subiría hasta la aprobación.")
        restas = verificar_restas(analisis)
        if restas:
            print("AVISO: la auditoría (restas y cifras que delatan) encontró problemas:\n  - "
                  + "\n  - ".join(restas))
        with open(args.salida, "w", encoding="utf-8") as fh:
            json.dump(dict(version=version_analisis(analisis),
                           mensajes=mensajes_para_subir(), filas=filas),
                      fh, ensure_ascii=False, indent=1, default=str)
        print(f"✓ Ensayo. Nada se subió. Lote escrito en {args.salida}")
        return 2 if restas else 0

    try:
        resumen = publicar(analisis, notas=args.notas, publicar_ya=args.publicar_ya,
                           informes=informes)
    except PublicacionInsegura as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    print(f"✓ Corrida {resumen['corrida_id']} con {resumen['filas']} filas. "
          f"Publicada: {resumen['publicada']}")
    if not resumen["publicada"]:
        print("  Queda oculta al público. Para abrirla, en Supabase: "
              "UPDATE obs360.corridas SET publicada = true WHERE id = "
              f"{resumen['corrida_id']};")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
