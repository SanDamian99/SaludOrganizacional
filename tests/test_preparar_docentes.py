"""
Preparación del archivo de docentes desde la exportación cruda del formulario.

Lo que se protege aquí: que nadie sin consentimiento entre al archivo, que el
nombre no salga, que las dos versiones del formulario (2025 y 2026) se
codifiquen sobre la misma recta, y que un cambio de orden en las preguntas
detenga el script en vez de codificar mal.
"""
import numpy as np
import pandas as pd
import pytest

from scripts import preparar_docentes as prep

CONSENT = ("Consentimiento: Acepto participar en la caracterización para generar "
           "intervenciones basadas en nuestras necesidades.")


def _crudo(n=6, version=2026) -> pd.DataFrame:
    """Exportación sintética con las 174 columnas en el orden real del formulario."""
    cols = ["Marca temporal", CONSENT, "Indique su nombre completo ", "¿Cuál es su edad?", "Sexo",
            "Estado Civil", "Indique su número de hijos",
            "¿Cuál es el nivel educativo más alto que ha completado?",
            "¿Cuál es su estrato socioeconómico?", "Su vivienda esta ubicada en una zona: ",
            "Nombre del colegio en el que trabaja ", "Este es un colegio: ",
            "¿En que jornada dicta clase? ", "Tipo de Contratación",
            "Número de horas de trabajo semanal ", "Ingreso salarial mensual ", "Nivel de Cargo ",
            "¿Tiene personas a cargo en el trabajo? (**)",
            "¿Con cuántos años de experiencia laboral tiene cómo docente?"]
    cols += [f" [{i}. compasión item]" if i == 2 else f" [{i}. IRI item]" for i in range(2, 17)]   # 19-33
    cols += [" [1 ¿Se sintió que no podía controlar]"] + [f" [{i}. PSS]" for i in range(2, 11)]  # 34-43
    cols += [" [1. Tengo total claridad]"] + [f" [{i}. ERS]" for i in range(2, 17)]              # 44-59
    cols += [" [1) ¿Tienes que trabajar muy rápido?]"] + [f" [{i}) PRPS]" for i in range(2, 17)]  # 60-75
    cols += ["¿Qué parte del trabajo familiar y doméstico haces tú?"]                             # 76
    cols += ["Manejo del Tiempo [Tengo la opción de decidir]"] + [f"MT [{i}]" for i in range(2, 8)]  # 77-83
    cols += [f"bloque{i}" for i in range(84, 120)]                                                # 84-119
    cols += [" [En mi trabajo, me siento agotado/a]"] + [f"BTA{i}" for i in range(2, 13)]         # 120-131
    cols += [f"Compromiso [{i}]" for i in range(3)] + [f"DefO [{i}]" for i in range(3)]           # 132-137
    cols += [f"Sat [{i}]" for i in range(3)] + [f"IR [{i}]" for i in range(4)]                    # 138-144
    cols += ["Bienestar psicosocial  [Mi motivación por el trabajo]"] + [f"BLG_P{i}" for i in range(2, 11)]  # 145-154
    cols += [f"Som{i}" for i in range(5)] + [f"Desg{i}" for i in range(4)] + [f"Alie{i}" for i in range(4)]  # 155-167
    cols += [' [Después del trabajo soy capaz de "desconectarme"]', "Descon2", "Descon3"]         # 168-170
    cols += ["¿Cuántas horas extras trabaja a la semana? ", "Nivel de Cargo  2", "¿En que nivel dicta clase? "]
    assert len(cols) == 174
    rng = np.random.default_rng(3)
    filas = []
    for i in range(n):
        f = dict.fromkeys(cols, np.nan)
        f["Marca temporal"] = pd.Timestamp(f"{version}-04-01 10:00") + pd.Timedelta(days=i)
        f[CONSENT] = "Sí" if i != 1 else "No"
        f["Indique su nombre completo "] = f"Persona {i}"
        f["¿Cuál es su edad?"] = 30 + i
        f["Sexo"] = "Femenino"
        f["Nombre del colegio en el que trabaja "] = ["I.E.O Santa María del Rio", "IE Bojacá ",
                                                       "I.EO Diversificado - Sede Campincito",
                                                       "IE BOJACA - IE JOSÉ JOAQUÍN CASAS",
                                                       "Fusca sede el Cerri", "Institución educativa cerca de piedra "][i]
        if i == 1:      # sin consentimiento: no respondió nada más
            filas.append(f); continue
        for c in cols[19:34]:
            f[c] = "Me describe bastante"
        for c in cols[34:44]:
            f[c] = "Casi nunca"
        acuerdo = "De acuerdo" if version == 2026 else "Moderadamente de acuerdo"
        for c in cols[132:145]:
            f[c] = acuerdo
        for c in cols[145:168]:
            f[c] = float(rng.integers(1, 8)) if version == 2026 else "A menudo"
        filas.append(f)
    return pd.DataFrame(filas)


def test_solo_entran_quienes_dijeron_si_y_sin_nombre():
    d, inf = prep.preparar(_crudo())
    assert inf["sin_consentimiento"] == 1 and inf["filas_validas"] == 5
    assert "Nombre" not in d.columns and not any("nombre" in c.lower() for c in d.columns)
    assert list(d["ID"]) == [f"D00{i}" for i in range(1, 6)]
    assert "Persona 1" not in d.to_string()


@pytest.mark.parametrize("texto,codigo,nombre", [
    ("I.E.O Santa María del Rio", "SMR", "Santa María del Río"),
    ("IE BOJACA - IE JOSÉ JOAQUÍN CASAS", "Bojacá", "Bojacá"),
    ("I.EO Diversificado - Sede Campincito", "Dcampin", "Diversificado · sede Campincito"),
    ("Fusca sede el Cerri", "Fcerr", "Fusca · sede El Cerro"),
    ("Institución educativa cerca de piedra ", "CdP", "Cerca de Piedra"),
    ("San José Má. Escrivá de Balaguer", "SJMEB", "San Josemaría Escrivá de Balaguer"),
    ("Colegio inexistente", "", ""),
    (np.nan, "", ""),
])
def test_normalizacion_de_colegios(texto, codigo, nombre):
    assert prep.colegio(texto) == (codigo, nombre)


def test_las_dos_versiones_del_formulario_caen_en_la_misma_recta():
    d26, _ = prep.preparar(_crudo(version=2026))
    d25, _ = prep.preparar(_crudo(version=2025))
    # «De acuerdo» (2026) y «Moderadamente de acuerdo» (2025) valen lo mismo
    assert d26["Comp1"].iloc[0] == d25["Comp1"].iloc[0] == 4
    assert set(d26["Versión del formulario"]) == {"2026 (acuerdo en 5 opciones)"}
    assert set(d25["Versión del formulario"]) == {"2025 (acuerdo en 6 opciones)"}
    # los ítems de bienestar numéricos (2026) se respetan; los de texto (2025) se codifican
    assert d26["BLG_Som1"].between(1, 7).all() and d25["BLG_Som1"].iloc[0] == 5


def test_inversiones_y_totales():
    d, _ = prep.preparar(_crudo())
    # PSS: «Casi nunca» = 1; los ítems 3,4,5,7,9 se invierten (4 - 1 = 3)
    assert d["PSS1"].iloc[0] == 1 and d["PSS3"].iloc[0] == 3
    assert d["PSS_T"].iloc[0] == 5 * 1 + 5 * 3
    assert d["IRI_EC_T"].notna().all() and "Comp_T" in d.columns


def test_un_cambio_de_orden_en_las_preguntas_detiene_el_script():
    crudo = _crudo()
    cols = list(crudo.columns)
    cols[34], cols[44] = cols[44], cols[34]
    with pytest.raises(prep.FormatoInesperado):
        prep.preparar(crudo[cols])


def test_valores_no_reconocidos_quedan_vacios_y_se_informan():
    crudo = _crudo()
    crudo.iloc[0, 34] = "Tal vez"
    d, inf = prep.preparar(crudo)
    assert np.isnan(d["PSS1"].iloc[0])
    assert inf["valores_sin_mapear"]["PSS1"] == ["Tal vez"]
