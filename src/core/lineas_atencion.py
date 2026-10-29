"""
Líneas de atención en salud mental — fuente única.

Datos transcritos de «Líneas de atención en salud mental», documento de la
Secretaría de Salud (recibido el 29-oct-2026) y confirmado por el equipo. Lo que
el documento pide confirmar antes de ir (sedes, horarios, urgencias psiquiátricas)
conserva su nota en `nota` y la pantalla la muestra.

Sin Streamlit: lo usan las rutas de `alertas_catalogo`, el cuadro de ayuda, el
panel de señales y la página «Dónde pedir ayuda».

Reglas de texto: `resumen` es la frase corta de la ruta y del cuadro de ayuda, y
no nombra riesgos; `descripcion` es el texto del documento y solo sale en la
página del directorio.
"""
from __future__ import annotations

from dataclasses import dataclass

FUENTE = "Secretaría de Salud (documento recibido el 29-oct-2026)"
FECHA = "2026-10-29"

# Orden de aparición en la página.
MUNICIPIOS = {
    "nacional": "Líneas nacionales",
    "chia": "Chía",
    "cajica": "Cajicá",
    "sopo": "Sopó",
    "zipaquira": "Zipaquirá",
    "cota": "Cota",
    "tenjo": "Tenjo",
    "tabio": "Tabio",
    "tocancipa": "Tocancipá",
    "bogota": "Bogotá",
}
TIPOS = {"linea": "Línea telefónica", "escucha": "Escucha y orientación",
         "urgencias": "Urgencias", "orientacion": "Orientación"}
NIVELES = ("ahora", "hoy", "semana")
NIVELES_TITULO = {"ahora": "Ahora mismo", "hoy": "Hoy", "semana": "Esta semana"}
PARA = {"estudiante": "Estudiante", "familia": "Familia", "docente": "Docente"}
TEMAS = {
    "crisis": "Una crisis o apoyo emocional",
    "violencia": "Violencia",
    "menores": "Niños, niñas y adolescentes",
    "consumo": "Consumo de sustancias",
    "orientacion": "Orientación y rutas",
    "victimas": "Víctimas del conflicto armado",
}
_TODOS = ("estudiante", "familia", "docente")


@dataclass(frozen=True)
class Linea:
    clave: str
    nombre: str
    telefono: str                  # para mostrar; vacío si no hay número
    resumen: str                   # frase corta, sin nombrar riesgos
    municipio: str
    tipo: str
    nivel: str                     # ahora | hoy | semana (para la ruta)
    para: tuple[str, ...] = _TODOS
    temas: tuple[str, ...] = ("orientacion",)
    marcado: str = ""              # dígitos para `tel:`; vacío si no se marca directo
    whatsapp: str = ""
    horario: str = ""
    descripcion: str = ""
    direccion: str = ""
    correo: str = ""
    nota: str = ""
    en_directorio: bool = True
    fuente: str = FUENTE
    fecha: str = FECHA


def _l(**kw) -> Linea:
    return Linea(**kw)


_LINEAS: tuple[Linea, ...] = (
    # ── Nacionales ───────────────────────────────────────────────────────────
    _l(clave="l106", nombre="Línea 106", telefono="106", marcado="106",
       resumen="Escucha y apoyo emocional, gratuita y confidencial, 24 horas.",
       municipio="nacional", tipo="linea", nivel="ahora", temas=("crisis", "orientacion"),
       horario="24 horas, todos los días",
       descripcion=("Línea nacional de salud mental, gratuita y confidencial. Escucha "
                    "profesional, apoyo emocional, primeros auxilios psicológicos, intervención "
                    "en crisis y orientación hacia servicios especializados. Puede utilizarse "
                    "ante ansiedad, malestar emocional o riesgo suicida.")),
    _l(clave="l123", nombre="Línea 123", telefono="123", marcado="123",
       resumen="Emergencias y apoyo psicosocial en Chía; informe el municipio y la ubicación.",
       municipio="chia", tipo="linea", nivel="ahora", temas=("crisis", "violencia"),
       horario="24 horas, gratuito",
       descripcion=("Emergencias, apoyo emocional y activación de la ruta de atención. Chía "
                    "publica expresamente la teleorientación psicosocial a través de este "
                    "número. Solicitar atención por una crisis de salud mental e informar el "
                    "municipio y la ubicación.")),
    _l(clave="l155", nombre="Línea 155", telefono="155", marcado="155",
       resumen="Orientación a mujeres ante violencias, 24 horas.",
       municipio="nacional", tipo="linea", nivel="hoy", para=("familia", "docente"),
       temas=("violencia",), horario="24 horas, gratuita",
       descripcion=("Orientación a mujeres víctimas de violencia física, psicológica, sexual, "
                    "económica o intrafamiliar y acceso a rutas de protección. Ante peligro "
                    "inmediato, llamar al 123.")),
    _l(clave="icbf_141", nombre="ICBF: Línea 141", telefono="141", marcado="141",
       resumen="Protección de niños, niñas y adolescentes, 24 horas.",
       municipio="nacional", tipo="linea", nivel="hoy", temas=("menores", "violencia"),
       horario="24 horas, gratuita",
       descripcion=("Emergencias, maltrato, violencia y vulneración de derechos de menores de "
                    "edad; orientación y activación de protección.")),
    _l(clave="icbf_info", nombre="ICBF: información y orientación", telefono="01 8000 91 80 80",
       marcado="018000918080",
       resumen="Información sobre programas y rutas del ICBF.",
       municipio="nacional", tipo="linea", nivel="semana", temas=("menores", "orientacion"),
       horario="Lunes a viernes, 8:00 a. m.–5:00 p. m.",
       descripcion=("Información sobre programas, servicios y rutas del ICBF. Para una "
                    "emergencia con un menor, utilizar 141.")),
    # ── Chía ─────────────────────────────────────────────────────────────────
    _l(clave="chia_escucha", nombre="Chía: Centros de Escucha", telefono="601 884 4444",
       marcado="6018844444",
       resumen="Orientación y acompañamiento psicosocial; pida el equipo de salud mental.",
       municipio="chia", tipo="escucha", nivel="hoy",
       temas=("crisis", "consumo", "violencia", "orientacion"),
       descripcion=("Solicitar información pidiendo el equipo de salud mental de la Secretaría "
                    "de Salud. Orientación y acompañamiento psicosocial, prevención del "
                    "suicidio, consumo de sustancias y violencias."),
       direccion="Casa de la Mujer, Palacio Municipal y Parque Paraíso (vereda Bojacá)",
       nota=("Confirmar sede y horario antes de asistir: otra publicación municipal menciona "
             "puntos distintos.")),
    _l(clave="chia_papsivi", nombre="Chía: PAPSIVI", telefono="601 884 4444",
       marcado="6018844444",
       resumen="Acompañamiento a víctimas del conflicto armado.",
       municipio="chia", tipo="escucha", nivel="semana", temas=("victimas",),
       descripcion=("Acceso mediante la Secretaría de Salud. Acompañamiento a víctimas del "
                    "conflicto armado y articulación de las rutas de salud física y mental."),
       nota="Es una oferta dirigida a víctimas del conflicto armado."),
    _l(clave="orientacion_escolar", nombre="Orientación escolar del colegio", telefono="",
       resumen="Primer contacto, siempre.", municipio="chia", tipo="orientacion",
       nivel="hoy", temas=("orientacion",), en_directorio=False),
    _l(clave="comisaria_familia", nombre="Comisaría de Familia", telefono="",
       resumen="Si hay riesgo en el hogar.", municipio="chia", tipo="orientacion",
       nivel="semana", temas=("violencia", "menores"), en_directorio=False),
    _l(clave="chia_clinica_sabana", nombre="Clínica Universidad de La Sabana — Chía",
       telefono="601 861 7777", marcado="6018617777",
       resumen="Urgencias generales de adultos y pediatría, 24 horas.",
       municipio="chia", tipo="urgencias", nivel="semana", temas=("crisis",),
       horario="24 horas, todos los días",
       descripcion="Urgencias generales de adultos y pediatría 24/7.",
       direccion="Km 21, Autopista Norte, La Caro",
       nota="Confirmar disponibilidad de valoración por psiquiatría."),
    _l(clave="chia_clinica_chia", nombre="Clínica Chía", telefono="601 593 8080",
       marcado="6015938080",
       resumen="Urgencias generales, 24 horas.", municipio="chia", tipo="urgencias",
       nivel="semana", temas=("crisis",), horario="24 horas",
       descripcion="Urgencias generales 24 horas.", direccion="Calle 6 # 10-125",
       nota="No hay confirmación de urgencias psiquiátricas especializadas permanentes."),
    _l(clave="chia_hospital_san_antonio", nombre="Hospital San Antonio de Chía",
       telefono="317 849 0101", marcado="3178490101",
       resumen="Urgencias, 24 horas.", municipio="chia", tipo="urgencias", nivel="semana",
       temas=("crisis",), horario="24 horas",
       descripcion="Celular institucional publicado como atención 24 horas.",
       direccion="Entrada de urgencias anunciada en carrera 1 # 5-67, variante Chía–Cota",
       nota=("Confirmar la ubicación por teléfono: el sitio del hospital conserva otra "
             "dirección y existe un anuncio de traslado. No se verificó psiquiatría presencial "
             "24/7.")),
    # ── Cajicá ───────────────────────────────────────────────────────────────
    _l(clave="cajica_ruta", nombre="Cajicá: ruta de salud mental", telefono="601 866 5021",
       marcado="6018665021", correo="secsalud@cajica.gov.co",
       resumen="Orientación, seguimiento y canalización a la EPS; también 106 y 123.",
       municipio="cajica", tipo="escucha", nivel="semana", temas=("crisis", "orientacion"),
       descripcion=("Orientación, seguimiento y canalización a la EPS frente a ideación o "
                    "amenaza suicida. El municipio también reporta un Centro de Escucha."),
       nota="Solicitar ubicación, cupo y horario del Centro de Escucha por este canal."),
    _l(clave="cajica_hospital", nombre="Hospital Profesor Jorge Cavelier — Cajicá",
       telefono="310 669 7196", marcado="3106697196",
       resumen="Urgencias generales, 24 horas.", municipio="cajica", tipo="urgencias",
       nivel="semana", temas=("crisis",), horario="24 horas",
       descripcion=("Urgencias generales 24 horas. Incluido en la ruta municipal para atención "
                    "tras intento de suicidio. También 601 866 4949."),
       direccion="Carrera 4 # 1-10"),
    _l(clave="cajica_san_luis", nombre="Clínica San Luis — Cajicá", telefono="601 879 3699",
       marcado="6018793699",
       resumen="Urgencias generales, 24 horas.", municipio="cajica", tipo="urgencias",
       nivel="semana", temas=("crisis",), horario="24 horas",
       descripcion=("Urgencias generales 24 horas; incluida en la ruta local de atención. "
                    "También 315 318 8474."),
       direccion="Carrera 4 # 0-90"),
    # ── Sopó, Zipaquirá, Cota, Tenjo, Tabio, Tocancipá ──────────────────────
    _l(clave="sopo_codigo_dorado", nombre="Sopó: Código Dorado", telefono="318 820 6780",
       marcado="3188206780",
       resumen="Apoyo emocional y orientación; activa la atención cuando hace falta.",
       municipio="sopo", tipo="linea", nivel="semana", temas=("crisis", "orientacion"),
       horario="Todos los días, 7:00 a. m.–7:00 p. m.",
       descripcion=("Escucha psicológica. Apoyo emocional, orientación, seguimiento y "
                    "activación de atención ante riesgo suicida o problemas de salud mental.")),
    _l(clave="zipaquira_esperanza", nombre="Zipaquirá: Línea de la Esperanza",
       telefono="322 814 2684", marcado="3228142684", whatsapp="3228142684",
       resumen="Apoyo emocional y contención; llamadas y WhatsApp, 24 horas.",
       municipio="zipaquira", tipo="linea", nivel="semana", temas=("crisis", "orientacion"),
       horario="24 horas",
       descripcion=("Apoyo emocional, contención y orientación ante ansiedad, depresión, "
                    "estrés o dificultades personales. Llamadas y WhatsApp.")),
    _l(clave="zipaquira_escucha", nombre="Zipaquirá: Centros de Escucha",
       telefono="320 979 4213", marcado="3209794213",
       resumen="Orientación psicológica y primeros auxilios psicológicos.",
       municipio="zipaquira", tipo="escucha", nivel="semana",
       temas=("crisis", "orientacion"),
       descripcion=("Secretaría de Salud. Orientación psicológica, primeros auxilios "
                    "psicológicos, acompañamiento y activación de rutas."),
       direccion="Calle 8 # 8-23, Centro; CAMI de Barandillas, carrera 3 # 2F-35",
       nota="Confirmar horarios y requisitos de acceso."),
    _l(clave="cota_escucha", nombre="Cota: Centro de Escucha", telefono="601 745 1453",
       marcado="6017451453",
       resumen="Pida Salud Pública / Centro de Escucha en el conmutador municipal.",
       municipio="cota", tipo="escucha", nivel="semana", temas=("orientacion",),
       descripcion="Conmutador municipal; solicitar Salud Pública / Centro de Escucha.",
       nota=("La Alcaldía confirma el servicio, pero no hay un teléfono directo ni un horario "
             "actual verificable.")),
    _l(clave="tenjo_proteccion", nombre="Tenjo: Protección Social", telefono="601 580 7997",
       marcado="6015807997", correo="proteccionsocial@tenjo-cundinamarca.gov.co",
       resumen="Consulta de la oferta de orientación y salud mental (extensión 208).",
       municipio="tenjo", tipo="orientacion", nivel="semana", temas=("orientacion",),
       descripcion=("Extensión 208. Canal para consultar la oferta de orientación y salud "
                    "mental."),
       nota=("Hay antecedentes de Centros de Escucha comunitarios, pero no se confirmó un "
             "servicio permanente con horario vigente.")),
    _l(clave="tabio_oferta", nombre="Tabio: consulta de oferta municipal",
       telefono="01 8000 93 78 80", marcado="018000937880",
       resumen="Línea de la Alcaldía; pida la Secretaría de Salud.",
       municipio="tabio", tipo="orientacion", nivel="semana", temas=("orientacion",),
       descripcion=("Línea gratuita de la Alcaldía. Canal administrativo para averiguar la "
                    "oferta local."),
       nota=("No se confirmó una línea exclusiva de salud mental vigente. Para apoyo "
             "inmediato, usar 106 o 123.")),
    _l(clave="tocancipa_linea", nombre="Tocancipá: Línea Amiga", telefono="322 846 7222",
       marcado="3228467222",
       resumen="Línea de salud mental de la Secretaría de Salud.",
       municipio="tocancipa", tipo="linea", nivel="semana", temas=("crisis", "orientacion"),
       descripcion=("Línea de salud mental. Conmutador: 57 (60) 1 516 9017, extensión 102."),
       direccion="Calle 11, carrera 6 - 12, Tocancipá"),
    # ── Bogotá ───────────────────────────────────────────────────────────────
    _l(clave="bogota_106", nombre="Línea 106 de Bogotá", telefono="106", marcado="106",
       whatsapp="3007548933",
       resumen="Escucha, apoyo emocional e intervención en crisis; WhatsApp 300 754 8933.",
       municipio="bogota", tipo="linea", nivel="semana", temas=("crisis",),
       horario="24 horas",
       descripcion=("Escucha, apoyo emocional e intervención en crisis para personas de todas "
                    "las edades. El WhatsApp corresponde al servicio de Bogotá.")),
    _l(clave="bogota_purpura", nombre="Línea Púrpura Distrital", telefono="01 8000 112 137",
       marcado="018000112137", whatsapp="3007551846", para=("familia", "docente"),
       resumen="Orientación psicológica, social y jurídica a mujeres mayores de 18 años.",
       municipio="bogota", tipo="linea", nivel="semana", temas=("violencia",),
       horario="24 horas; WhatsApp 300 755 1846",
       descripcion=("Orientación psicológica, social y jurídica a mujeres mayores de 18 años "
                    "ante violencias.")),
    _l(clave="bogota_calma", nombre="Línea Calma", telefono="01 8000 423 614",
       marcado="018000423614", para=("familia", "docente"),
       resumen="Escucha y orientación emocional para hombres mayores de 18 años de Bogotá.",
       municipio="bogota", tipo="linea", nivel="semana", temas=("crisis", "violencia"),
       horario=("Lunes a viernes 7:00 a. m.–10:30 p. m.; sábados 8:00 a. m.–10:30 p. m.; "
                "domingos 2:00 p. m.–10:30 p. m."),
       descripcion=("Escucha y orientación emocional para hombres mayores de 18 años "
                    "residentes en Bogotá, manejo de conflictos y prevención de violencias.")),
    _l(clave="bogota_montserrat", nombre="Clínica Montserrat — norte de Bogotá",
       telefono="601 259 6000", marcado="6012596000",
       resumen="Consulta psiquiátrica prioritaria sin cita, 24 horas (de pago).",
       municipio="bogota", tipo="urgencias", nivel="semana", temas=("crisis",),
       horario="24 horas, todos los días",
       descripcion=("Consulta psiquiátrica prioritaria sin cita, con evaluación y definición "
                    "de manejo ambulatorio u hospitalario."),
       direccion="Calle 134 # 17-71",
       nota=("Servicio de pago particular o mediante aseguradoras con convenio; no tiene "
             "convenio con EPS.")),
    _l(clave="bogota_la_paz", nombre="Clínica Nuestra Señora de La Paz — Bogotá",
       telefono="601 292 1277", marcado="6012921277",
       resumen="Servicio de urgencias en salud mental.", municipio="bogota",
       tipo="urgencias", nivel="semana", temas=("crisis",),
       descripcion="Servicio de urgencias en salud mental.", direccion="Carrera 69 # 12-75",
       nota=("Confirmar con la institución cobertura, acceso y disponibilidad. Está más "
             "alejada de Chía que Montserrat.")),
)

# Qué líneas forman la ruta de cada tipo de persona, en orden.
_RUTAS = {
    "estudiante": ("l106", "l123", "orientacion_escolar", "chia_escucha", "icbf_141",
                   "comisaria_familia"),
    "adulto": ("l106", "l123", "chia_escucha", "l155", "comisaria_familia"),
}

# Tema de líneas por alerta de grupo (estudiantes y cuidadores).
TEMAS_POR_ALERTA = {
    "malestar": ("crisis", "orientacion"),
    "desesperanza": ("crisis",),
    "animo": ("crisis", "orientacion"),
    "autolesion": ("crisis",),
}
_TEMAS_URGENTES = ("crisis",)


def todas() -> list[Linea]:
    return list(_LINEAS)


def directorio() -> list[Linea]:
    """Las que tienen teléfono propio y van en la página del directorio."""
    return [x for x in _LINEAS if x.en_directorio]


def por_clave(clave: str) -> Linea:
    for x in _LINEAS:
        if x.clave == clave:
            return x
    raise KeyError(clave)


def filtrar(para: str | None = None, tema: str | None = None,
            municipio: str | None = None, solo_directorio: bool = False) -> list[Linea]:
    base = directorio() if solo_directorio else todas()
    return [x for x in base
            if (para is None or para in x.para)
            and (tema is None or tema in x.temas)
            and (municipio is None or x.municipio == municipio)]


def ruta_niveles(tipo: str = "estudiante") -> dict[str, list[Linea]]:
    """{nivel: líneas} de la ruta: ahora mismo, hoy y esta semana."""
    claves = _RUTAS.get(tipo) or _RUTAS["estudiante"]
    salida: dict[str, list[Linea]] = {n: [] for n in NIVELES}
    for c in claves:
        x = por_clave(c)
        salida[x.nivel].append(x)
    return salida


def detalle(x: Linea) -> str:
    if x.telefono and x.telefono not in x.nombre:
        return f"{x.telefono} · {x.resumen}"
    return x.resumen


def ruta(tipo: str = "estudiante") -> list[tuple[str, str]]:
    """Ruta como pares (nombre, detalle), de lo más urgente a lo menos."""
    por = ruta_niveles(tipo)
    return [(x.nombre, detalle(x)) for n in NIVELES for x in por[n]]


def para_senal(alerta: str, limite: int = 3) -> list[Linea]:
    """Pocas líneas, las más urgentes, para el tema de una alerta de grupo."""
    temas = TEMAS_POR_ALERTA.get(alerta, _TEMAS_URGENTES)
    candidatas = [x for x in _LINEAS if x.en_directorio and x.municipio in ("nacional", "chia")
                  and x.nivel in ("ahora", "hoy") and set(x.temas) & set(temas)]
    orden = {n: i for i, n in enumerate(NIVELES)}
    candidatas.sort(key=lambda x: (orden[x.nivel], not (set(x.temas) & {"crisis"})))
    return candidatas[:limite]
