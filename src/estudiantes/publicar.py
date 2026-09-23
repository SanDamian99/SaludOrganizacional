"""
Publicación de resultados de estudiantes en Supabase — Observatorio 360.

Convierte los objetos `Analisis` en filas agregadas y las sube al esquema
`obs360` (ver supabase/estudiantes_schema.sql).

QUÉ SUBE
Solo agregados: una fila por nivel, grupo, tipo e indicador. Ni una respuesta
individual, ni un identificador, ni un nombre.

TRES GUARDAS, EN ESTE ORDEN
  1. `aplanar` construye las filas únicamente desde tablas ya agregadas del
     objeto `Analisis`; nunca toca `Analisis.datos`.
  2. `verificar` rechaza el lote completo si aparece un grupo con n < MIN_GROUP_N,
     una columna de identificación o algo con forma de identificador de
     estudiante. Falla el lote entero, no la fila: si una guarda salta, hay un
     error de programación y publicar «lo que se pueda» lo esconde.
  3. El esquema tiene un CHECK de n >= 10 y no da política de escritura al rol
     anónimo, así que la base rechazaría el error aunque las dos guardas
     anteriores fallaran.

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
import sys
from datetime import date

import numpy as np
import pandas as pd

from src.estudiantes import catalog as cat
from src.estudiantes import pipeline

# Columnas que no pueden aparecer en nada que se publique
COLUMNAS_PROHIBIDAS = {"id", "nombre", "nombre_completo", "ts", "sede",
                       "colegio_nombre", "id_estudiante", "id_cuidador"}
TABLA_CORRIDAS = "corridas"
TABLA_RESULTADOS = "resultados"
ESQUEMA = "obs360"


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
                    indicador=f["indicador"], casos=f["casos"], fuente=f["fuente"]))

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

        # CCI
        for clave, valor in (a.icc or {}).items():
            if valor is not None and valor == valor:
                filas.append(_fila(nivel, "icc", clave, a.n, valor,
                                   nota="Proporción de varianza entre colegios"))

        # contrastes por tercil
        for c in (a.contrastes or []):
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

        # resultados por colegio y por grado para la vista comunidad desplegada.
        # Tipos propios («banda_grupo»…) para que el lector no los confunda con
        # los del nivel completo. Se omite cualquier fila que no llegue al
        # mínimo: un indicador con pocas respuestas válidas dentro de un colegio
        # no se publica, aunque el colegio sí llegue.
        for columna, grupos in (getattr(a, "subgrupos", None) or {}).items():
            for grupo, s in grupos.items():
                filas.extend(_aplanar_subgrupo(nivel, columna, grupo, s))

        # descripción de la muestra, en una sola fila cuyo N es el del nivel
        if a.muestra:
            # La muestra va anidada en un solo campo: sus claves (n, sexo, edad…)
            # chocarían con las columnas de la fila.
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
                               indicador=f["indicador"], casos=f["casos"],
                               fuente=f["fuente"], **comun))
    for c in (s.contrastes or []):
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


def _enmascarar_conteos(d: dict) -> dict:
    """Sustituye por «<10» cualquier celda por debajo del mínimo publicable.

    Las distribuciones de la muestra (edad, colegio) pueden tener celdas de
    pocos casos. El recuento exacto de esas celdas se queda en la corrida local,
    que es la que usa el artículo; lo que se publica dice «<10».
    """
    salida = {}
    for k, v in d.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v < cat.MIN_GROUP_N:
            salida[str(k)] = f"<{cat.MIN_GROUP_N}"
        else:
            salida[str(k)] = v
    return salida


CAMPOS_INGESTA = ("filas_archivo", "sin_consentimiento", "excluidas_prueba",
                  "excluidas_colegio_unico", "duplicados_eliminados",
                  "filas_validas", "erq_invalidado", "escalas_detectadas",
                  "escalas_ausentes", "etiquetas_no_mapeadas",
                  "faltantes_por_escala", "edades_fuera_de_rango",
                  "colegios_enmascarados", "avisos")


def aplanar_ingesta(informes: list) -> list[dict]:
    """El flujo de exclusiones, que es el diagrama de la muestra del artículo."""
    filas = []
    for inf in (informes or []):
        detalle = {}
        for campo in CAMPOS_INGESTA:
            valor = getattr(inf, campo, None)
            if valor in (None, [], {}):
                continue
            detalle[campo] = (_enmascarar_conteos(valor)
                              if campo == "colegios" else valor)
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
        grupo = str(f.get("grupo") or "")
        if len(grupo) == 9 and grupo[0].upper() == "E" and \
                all(c in "0123456789abcdef" for c in grupo[1:].lower()):
            problemas.append(f"fila {i}: el grupo «{grupo}» tiene forma de "
                             "identificador de estudiante")
    if problemas:
        raise PublicacionInsegura(
            "No se publicó nada. El lote tiene "
            f"{len(problemas)} problema(s) de privacidad:\n  - "
            + "\n  - ".join(problemas[:20])
            + ("\n  … y más" if len(problemas) > 20 else ""))


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
    cli = cliente or _cliente()
    tabla = lambda t: cli.postgrest.schema(ESQUEMA).table(t)  # noqa: E731

    corrida = dict(
        modulo="estudiantes", version_analisis=version_analisis(analisis),
        n_secundaria=(analisis.get(cat.NIVEL_SECUNDARIA).n
                      if analisis.get(cat.NIVEL_SECUNDARIA) else None),
        n_primaria=(analisis.get(cat.NIVEL_PRIMARIA).n
                    if analisis.get(cat.NIVEL_PRIMARIA) else None),
        notas=notas or None, publicada=bool(publicar_ya))
    res = tabla(TABLA_CORRIDAS).insert(corrida).execute()
    corrida_id = res.data[0]["id"]

    for i in range(0, len(filas), 500):
        lote = [dict(f, corrida_id=corrida_id) for f in filas[i:i + 500]]
        tabla(TABLA_RESULTADOS).insert(lote).execute()

    return dict(corrida_id=corrida_id, version=corrida["version_analisis"],
                filas=len(filas), publicada=corrida["publicada"])


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
                   help="no toca la red; deja el lote en un JSON")
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
        with open(args.salida, "w", encoding="utf-8") as fh:
            json.dump(dict(version=version_analisis(analisis),
                           mensajes=mensajes_para_subir(), filas=filas),
                      fh, ensure_ascii=False, indent=1, default=str)
        print(f"✓ Ensayo. Nada se subió. Lote escrito en {args.salida}")
        return 0

    resumen = publicar(analisis, notas=args.notas, publicar_ya=args.publicar_ya,
                       informes=informes)
    print(f"✓ Corrida {resumen['corrida_id']} con {resumen['filas']} filas. "
          f"Publicada: {resumen['publicada']}")
    if not resumen["publicada"]:
        print("  Queda oculta al público. Para abrirla, en Supabase: "
              "UPDATE obs360.corridas SET publicada = true WHERE id = "
              f"{resumen['corrida_id']};")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
