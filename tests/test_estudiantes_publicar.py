"""
Pruebas del publicador de resultados de estudiantes.

Lo que se prueba aquí es la frontera de privacidad: qué sale de la máquina hacia
una base de datos en la nube. Si estas pruebas fallan, no se publica.
"""
import json
import os

import pytest

from src.core.rutas import carpeta_datos

from src.estudiantes import catalog as cat
from src.estudiantes import pipeline, publicar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ══ Guardas, con lotes construidos a mano ═══════════════════════════════════
def _fila_valida(**cambios):
    base = dict(nivel="secundaria", tipo="descriptivo", clave="SDQ_Total",
                escala="Total de dificultades", agrupacion="total", grupo=None,
                n=943, valor=12.6, ic_inf=None, ic_sup=None, detalle={"DE": 5.6})
    base.update(cambios)
    return base


def test_lote_valido_pasa():
    publicar.verificar([_fila_valida()])


def test_rechaza_grupo_por_debajo_del_minimo():
    fila = _fila_valida(n=cat.MIN_GROUP_N - 1, agrupacion="Colegio", grupo="CdP")
    with pytest.raises(publicar.PublicacionInsegura) as e:
        publicar.verificar([fila])
    assert "n = 9" in str(e.value)


def test_rechaza_identificador_de_estudiante_como_grupo():
    with pytest.raises(publicar.PublicacionInsegura) as e:
        publicar.verificar([_fila_valida(agrupacion="ID", grupo="E1a2b3c4d")])
    assert "identificador de estudiante" in str(e.value)


@pytest.mark.parametrize("ident", ["E1a2b3c4d", "C1a2b3c4d", "N1a2b3c4d",
                                   "c00ff00aa", "nABCDEF12"])
def test_rechaza_identificadores_e_c_n_como_en_la_base(ident):
    """Misma regla que el CHECK de la base: ^[ECN][0-9a-f]{8}$, sin distinguir mayúsculas."""
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila_valida(agrupacion="ID", grupo=ident)])
    with pytest.raises(publicar.PublicacionInsegura) as e:
        publicar.verificar([_fila_valida(clave=ident)])
    assert "clave" in str(e.value)


@pytest.mark.parametrize("valor", ["LauV", "Sexto", "E1a2b3c4", "E1a2b3c4d5",
                                   "X1a2b3c4d", "E1a2b3c4z", "LauV|Sexto"])
def test_no_confunde_grupos_normales_con_identificadores(valor):
    publicar.verificar([_fila_valida(agrupacion="Colegio", grupo=valor)])


@pytest.mark.parametrize("prohibida", ["nombre", "id", "ts", "sede"])
def test_rechaza_columnas_de_identificacion_en_el_detalle(prohibida):
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila_valida(detalle={prohibida: "algo"})])


def test_falla_el_lote_entero_no_solo_la_fila_mala():
    """Publicar «lo que se pueda» esconde el error que hay que arreglar."""
    lote = [_fila_valida() for _ in range(5)] + [_fila_valida(n=3)]
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar(lote)


def test_version_depende_de_la_estructura_no_de_los_datos():
    class Falso:
        n = 100
        escalas = ["SDQ_Total", "ARI_Total"]
    v1 = publicar.version_analisis({"secundaria": Falso()})
    v2 = publicar.version_analisis({"secundaria": Falso()})
    assert v1 == v2 and len(v1.split("-")) == 4      # fecha ISO + huella

    class Otro(Falso):
        n = 101
    assert publicar.version_analisis({"secundaria": Otro()}) != v1


def test_mensajes_para_subir_respetan_los_roles_del_catalogo():
    ms = publicar.mensajes_para_subir()
    claves_roles = {(m["clave"], m["accion_rol"]) for m in ms}
    assert ("ideacion", "familia") not in claves_roles
    assert ("ideacion", "colegio") in claves_roles
    for m in ms:
        assert m["accion"].strip(), f"{m['clave']}/{m['accion_rol']} sin acción"
        assert m["significa"] == cat.MENSAJES[m["clave"]].significa


# ══ Con los datos reales, si están ══════════════════════════════════════════
@pytest.fixture(scope="module")
def lote_real():
    rutas = pipeline.localizar_formularios(carpeta_datos('estudiantes'))
    if len(rutas) < 2:
        pytest.skip("Los formularios originales no están en el directorio de trabajo")
    analisis, _ = pipeline.cargar_y_analizar(rutas, n_boot=20)
    return analisis, publicar.aplanar(analisis)


def test_el_lote_real_pasa_las_guardas(lote_real):
    _, filas = lote_real
    publicar.verificar(filas)
    assert len(filas) > 200
    assert min(f["n"] for f in filas) >= cat.MIN_GROUP_N


def test_el_lote_real_no_trae_ni_un_nombre_ni_un_identificador(lote_real):
    import re
    import pandas as pd
    analisis, filas = lote_real
    texto = json.dumps(filas, ensure_ascii=False, default=str)
    assert not re.findall(r"\bE[0-9a-f]{8}\b", texto)
    # ningún identificador derivado del nombre sobrevive
    ids = set()
    for a in analisis.values():
        if a is not None and "ID" in a.datos.columns:
            ids.update(a.datos["ID"].astype(str).head(200))
    assert not [i for i in ids if i in texto]
    # y los nombres crudos tampoco
    ruta = pipeline.localizar_formularios(carpeta_datos('estudiantes'))[0]
    nombres = pd.read_csv(ruta)["Mi nombre completo es:"].dropna().astype(str).head(200)
    bajo = texto.lower()
    assert not [n for n in nombres if n.strip() and n.strip().lower() in bajo]


def test_el_lote_real_solo_tiene_tipos_y_agrupaciones_previstas(lote_real):
    _, filas = lote_real
    tipos = {f["tipo"] for f in filas}
    assert tipos <= {"descriptivo", "banda", "corte", "correlacion", "grupo",
                     "modelo", "tercil", "percentil", "icc", "contraste", "item",
                     "muestra", "solapamiento", "ingesta",
                     # resultados por colegio y por grado para el despliegue
                     "banda_grupo", "corte_grupo", "contraste_grupo", "item_grupo",
                       # alertas de grupo (fase 3), sin casos
                       "alerta", "alerta_grupo"}
    for f in filas:
        assert f["nivel"] in ("secundaria", "primaria")
        assert isinstance(f["detalle"], dict)


def test_ninguna_fila_viene_de_datos_individuales(lote_real):
    """El aplanado solo debe leer tablas agregadas, nunca `Analisis.datos`."""
    analisis, filas = lote_real
    n_estudiantes = sum(a.n for a in analisis.values() if a is not None)
    # una fila por estudiante sería la señal de fuga; hay muchas menos filas
    del_nivel = [f for f in filas if not f["tipo"].endswith("_grupo")]
    assert len(del_nivel) < n_estudiantes
    # y cada colegio o grado publicado lleva un número fijo y pequeño de filas
    # (bandas, cortes, contrastes e ítems), independiente de cuántos estudiantes
    # tenga: si dependiera del N, algo estaría saliendo fila a fila
    por_grupo: dict = {}
    for f in filas:
        if f["tipo"].endswith("_grupo"):
            por_grupo.setdefault((f["nivel"], f["agrupacion"], f["grupo"]), []).append(f)
    assert por_grupo
    tope = 6 + 16 + 4 + 18 + 2   # bandas + cortes + contrastes + ítems del PSSM + alertas
    for clave, propias in por_grupo.items():
        assert len(propias) <= tope, clave
    # y toda fila declara un N de grupo, no de individuo
    assert all(f["n"] >= cat.MIN_GROUP_N for f in filas)


def test_las_banderas_se_publican_como_booleanos():
    """`bool` hereda de `int`: convertirlas a 1.0 rompe al leerlas.

    Con una bandera numérica, filtrar un DataFrame por esa columna se
    interpreta como selección de columnas y la vista revienta.
    """
    fila = publicar._fila("secundaria", "correlacion", "SDQ_Total", 943, 0.5,
                          significativa=True, validada=False, p=0.001, casos=12)
    assert fila["detalle"]["significativa"] is True
    assert fila["detalle"]["validada"] is False
    assert isinstance(fila["detalle"]["p"], float)
    assert isinstance(fila["detalle"]["casos"], float)


def test_el_lote_real_no_trae_banderas_numericas(lote_real):
    _, filas = lote_real
    for f in filas:
        for clave in ("significativa", "significativo", "validada", "orientado"):
            if clave in f["detalle"]:
                assert isinstance(f["detalle"][clave], bool), \
                    f"{f['tipo']}/{f['clave']}: {clave} no es booleano"


def test_las_credenciales_de_escritura_salen_del_archivo_local_si_no_estan_en_el_entorno(tmp_path, monkeypatch):
    """Quien publica no debería tener que exportar claves a mano antes de cada corrida."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    ruta = tmp_path / "secrets.toml"
    ruta.write_text('SUPABASE_URL = "https://x.supabase.co"\nSUPABASE_SERVICE_KEY = "srv"\n'
                    'SUPABASE_KEY = "anon"\n')
    assert publicar.credenciales_escritura(str(ruta)) == ("https://x.supabase.co", "srv")
    # el entorno manda cuando existe
    monkeypatch.setenv("SUPABASE_URL", "https://y.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "otra")
    assert publicar.credenciales_escritura(str(ruta)) == ("https://y.supabase.co", "otra")
    # sin archivo y sin entorno, nada
    monkeypatch.delenv("SUPABASE_URL"); monkeypatch.delenv("SUPABASE_SERVICE_KEY")
    assert publicar.credenciales_escritura(str(tmp_path / "no_existe.toml")) == (None, None)


# ══ Auditoría de restas, enmascarado y despublicación ═══════════════════════
from tests.test_estudiantes_comunidad import _formulario  # noqa: E402


@pytest.fixture(scope="module")
def analisis_sintetico():
    from src.estudiantes import ingest, scoring
    bruto, _ = ingest.cargar(_formulario())
    return {cat.NIVEL_SECUNDARIA: pipeline.analizar(scoring.puntuar(bruto),
                                                    cat.NIVEL_SECUNDARIA, n_boot=20)}


def test_la_auditoria_de_restas_pasa_con_la_base(analisis_sintetico):
    assert publicar.verificar_restas(analisis_sintetico) == []


def test_la_auditoria_bloquea_una_base_manipulada(analisis_sintetico):
    import copy
    a = copy.copy(analisis_sintetico[cat.NIVEL_SECUNDARIA])
    b = copy.copy(a.base)
    b.colegios = dict(b.colegios)
    b.colegios["LauV"] = a.datos.index[a.datos["Colegio"] == "LauV"]   # incluye Noveno (4)
    a.base = b
    assert publicar.verificar_restas({cat.NIVEL_SECUNDARIA: a})


class _Tabla:
    def __init__(self, registro, nombre):
        self.r, self.n = registro, nombre

    def insert(self, filas):
        self.r.append(("insert", self.n, filas)); return self

    def update(self, valores):
        self.r.append(("update", self.n, valores)); return self

    def eq(self, k, v):
        self.r.append(("eq", self.n, (k, v))); return self

    def neq(self, k, v):
        self.r.append(("neq", self.n, (k, v))); return self

    def execute(self):
        class R:
            data = [{"id": 7}]
        return R()


class _Cliente:
    def __init__(self):
        self.registro = []
        cliente = self

        class _Schema:
            def table(self, nombre): return _Tabla(cliente.registro, nombre)

        class _Postgrest:
            def schema(self, _): return _Schema()
        self.postgrest = _Postgrest()


def test_publicar_ya_inserta_oculta_y_publica_al_final(analisis_sintetico):
    cli = _Cliente()
    publicar.publicar(analisis_sintetico, publicar_ya=True, cliente=cli)
    pasos = cli.registro
    ins = [p for p in pasos if p[0] == "insert"]
    assert ins[0][1] == "corridas" and ins[0][2]["publicada"] is False
    assert all(p[1] == "resultados" for p in ins[1:]) and len(ins) > 1
    ult_insert = max(i for i, p in enumerate(pasos) if p[0] == "insert")
    i_true = pasos.index(("update", "corridas", {"publicada": True}))
    i_false = pasos.index(("update", "corridas", {"publicada": False}))
    assert ult_insert < i_true < i_false
    assert ("eq", "corridas", ("id", 7)) in pasos[i_true:i_false]
    assert ("eq", "corridas", ("modulo", "estudiantes")) in pasos[i_false:]
    assert ("neq", "corridas", ("id", 7)) in pasos[i_false:]


def test_publicar_ya_devuelve_publicada_true(analisis_sintetico):
    r = publicar.publicar(analisis_sintetico, publicar_ya=True, cliente=_Cliente())
    assert r["publicada"] is True


def test_si_falla_el_insert_de_resultados_no_se_publica(analisis_sintetico):
    cli = _Cliente()
    original = _Tabla.execute

    def execute(self):
        if self.n == "resultados":
            raise RuntimeError("red caída")
        return original(self)
    _Tabla.execute = execute
    try:
        with pytest.raises(RuntimeError):
            publicar.publicar(analisis_sintetico, publicar_ya=True, cliente=cli)
    finally:
        _Tabla.execute = original
    assert not any(p[0] == "update" and p[2] == {"publicada": True}
                   for p in cli.registro)


def test_sin_publicar_ya_no_toca_otras_corridas(analisis_sintetico):
    cli = _Cliente()
    publicar.publicar(analisis_sintetico, publicar_ya=False, cliente=cli)
    assert not any(p[0] == "update" for p in cli.registro)


def test_auditoria_fallida_no_llama_al_cliente(analisis_sintetico, monkeypatch):
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["x"])
    cli = _Cliente()
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.publicar(analisis_sintetico, publicar_ya=True, cliente=cli)
    assert cli.registro == []


def test_verificar_restas_vacio_y_sin_base():
    from src.estudiantes.pipeline import Analisis
    import pandas as pd
    assert publicar.verificar_restas({}) == []
    a = Analisis(nivel="secundaria", n=50, datos=pd.DataFrame())
    assert getattr(a, "base", None) is None
    assert publicar.verificar_restas({"secundaria": a, "primaria": None}) == []


def test_main_devuelve_2_si_publicar_es_inseguro(analisis_sintetico, monkeypatch, capsys):
    monkeypatch.setattr(publicar.pipeline, "cargar_y_analizar",
                        lambda base=None: (analisis_sintetico, []))
    def falla(*a, **k):
        raise publicar.PublicacionInsegura("resta")
    monkeypatch.setattr(publicar, "publicar", falla)
    assert publicar.main([]) == 2


def test_ensayo_con_restas_escribe_json_y_devuelve_2(analisis_sintetico, monkeypatch, tmp_path):
    monkeypatch.setattr(publicar.pipeline, "cargar_y_analizar",
                        lambda base=None: (analisis_sintetico, []))
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["x"])
    salida = tmp_path / "l.json"
    assert publicar.main(["--ensayo", "--salida", str(salida)]) == 2
    assert salida.exists()


def test_los_conteos_crudos_se_enmascaran_al_publicar():
    class Inf:
        nivel = "secundaria"
        crudo_colegio_grado = {"LauV|Sexto": 95, "CdP|Décimo": 6}
    filas = publicar.aplanar_ingesta([Inf()])
    crudo = filas[0]["detalle"]["ingesta"]["crudo_colegio_grado"]
    assert crudo["LauV|Sexto"] == 95 and crudo["CdP|Décimo"] == "<10"


def test_la_fila_muestra_enmascara_celdas_y_suprimidos_pequenos(analisis_sintetico):
    import copy
    a = copy.copy(analisis_sintetico[cat.NIVEL_SECUNDARIA])
    m = dict(a.muestra)
    m["colegio_grado"] = {"LauV|Sexto": 95, "LauV|Noveno": 4}
    m["suprimidos"] = {"SDQ_Total": 3, "PSSM": 25}
    a.muestra = m
    fila = next(f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: a})
                if f["tipo"] == "muestra")
    pub = fila["detalle"]["muestra"]
    assert pub["colegio_grado"] == {"LauV|Sexto": 95, "LauV|Noveno": "<10"}
    assert pub["suprimidos"] == {"SDQ_Total": "<10", "PSSM": 25}


def test_un_conteo_cero_no_se_enmascara():
    # un cero no identifica a nadie y la vista necesita distinguirlo de «<10»
    assert publicar._enmascarar_conteos({"a": 0, "b": 3, "c": 12}) == \
        {"a": 0, "b": "<10", "c": 12}


def test_la_ingesta_publicada_enmascara_los_conteos_por_categoria():
    """Edades fuera de rango y ERQ invalidado: de 1 a 9 se publican como «<10».

    Los totales de exclusión (sin consentimiento, prueba, duplicados…) se quedan
    como número: son pasos del diagrama de la muestra de todo el nivel.
    """
    class Inf:
        nivel = "secundaria"
        filas_validas = 300
        sin_consentimiento = 4
        duplicados_eliminados = 2
        edades_fuera_de_rango = {"RCADS": 3, "SDQ": 25}
        erq_invalidado = 7
        avisos = ["ERQ-CA: 7 respuestas con «Nada parecido a mi» en los 10 ítems "
                  "se marcan como faltantes.", "Otro aviso con 7 cosas."]
    ing = publicar.aplanar_ingesta([Inf()])[0]["detalle"]["ingesta"]
    assert ing["edades_fuera_de_rango"] == {"RCADS": "<10", "SDQ": 25}
    assert ing["erq_invalidado"] == "<10"
    assert ing["avisos"][0].startswith("ERQ-CA: <10 respuestas")
    assert ing["avisos"][1] == "Otro aviso con 7 cosas."
    assert ing["sin_consentimiento"] == 4 and ing["duplicados_eliminados"] == 2


def test_un_erq_invalidado_grande_se_publica_tal_cual():
    class Inf:
        nivel = "secundaria"
        filas_validas = 300
        erq_invalidado = 42
        avisos = ["ERQ-CA: 42 respuestas con «x» en los 10 ítems se marcan."]
    ing = publicar.aplanar_ingesta([Inf()])[0]["detalle"]["ingesta"]
    assert ing["erq_invalidado"] == 42
    assert ing["avisos"][0].startswith("ERQ-CA: 42 respuestas")


def test_si_falla_despublicar_las_otras_avisa_y_devuelve_el_resultado(
        analisis_sintetico, capsys):
    """La corrida nueva ya está abierta: no se pierde el resultado, se avisa."""
    original = _Tabla.execute

    def execute(self):
        if ("neq", "corridas", ("id", 7)) in self.r:
            raise RuntimeError("permiso denegado")
        return original(self)
    _Tabla.execute = execute
    try:
        r = publicar.publicar(analisis_sintetico, publicar_ya=True, cliente=_Cliente())
    finally:
        _Tabla.execute = original
    assert r["publicada"] is True and r["corrida_id"] == 7
    assert r["otras_corridas_despublicadas"] is False
    err = capsys.readouterr().err
    assert "migración" in err and "despublic" in err.lower()


def test_publicar_ya_informa_que_despublico_las_otras(analisis_sintetico):
    r = publicar.publicar(analisis_sintetico, publicar_ya=True, cliente=_Cliente())
    assert r["otras_corridas_despublicadas"] is True
