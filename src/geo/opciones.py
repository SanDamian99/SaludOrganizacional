"""
Parámetros de presentación del mapa — Observatorio 360.

Lo que el equipo decide vive aquí; cambiar un valor es un commit de una línea.
Lo que puede delatar a alguien NO es parámetro: la lista de capas permitidas
(`PERMITIDAS`), que familia no vea el mapa y la auditoría previa están en el
código y en sus pruebas.
"""
from __future__ import annotations

# Capas que se ofrecen. Solo cuentan las de PERMITIDAS; lo demás se ignora.
MAPA_CAPAS = ("respuestas", "sentirse_parte", "apoyo_social")
MAPA_CAPA_INICIAL = "respuestas"
MAPA_MOSTRAR_NOMBRES = True            # rótulo con el nombre junto al punto
MAPA_MOSTRAR_SIN_CIFRA = True          # círculos grises de colegios sin cifra
MAPA_MOSTRAR_CAUSA_SIN_CIFRA = True    # decir por qué no hay cifra
MAPA_MOSTRAR_COMPARACION = True        # valor del municipio junto al del colegio
MAPA_ROLES = ("municipio", "colegio")
MAPA_EN_INFORMES = True                # mapa en el informe de la Secretaría
MAPA_CAPAS_INFORME = ("respuestas", "sentirse_parte")

# Video del municipio (src/geo/video_municipio.py). Para la Secretaría y los rectores.
VIDEO_NOMBRES_COLEGIOS = False         # nombrar los colegios en los mapas del video
VIDEO_ACCIONES = True                  # escena «qué podemos hacer» (de catalog.MENSAJES)
VIDEO_RUTAS = False                    # rutas en el cierre; además exige RUTAS_VALIDADAS
VIDEO_VARIANTE_CELULAR = True          # además del 16:9, una versión cuadrada
VIDEO_APROBADO = False                 # llave de publicación del guion (a mano, en un commit)

# No es un parámetro: las únicas capas que el mapa sabe dibujar. Ninguna es de
# malestar, alertas, SDQ ni RCADS.
PERMITIDAS = ("respuestas", "sentirse_parte", "apoyo_social")


def capas_activas() -> list[str]:
    """Capas ofrecidas, en el orden de PERMITIDAS; «respuestas» si no queda ninguna."""
    pedidas = tuple(MAPA_CAPAS)
    activas = [c for c in PERMITIDAS if c in pedidas]
    return activas or ["respuestas"]


def capa_inicial() -> str:
    activas = capas_activas()
    return MAPA_CAPA_INICIAL if MAPA_CAPA_INICIAL in activas else activas[0]


def rol_ve_mapa(rol: str) -> bool:
    """Familia nunca: no ve desagregación por colegio y el mapa lo es."""
    return rol != "familia" and rol in tuple(MAPA_ROLES)


def capas_informe() -> list[str]:
    """Capas del informe: las pedidas, permitidas y también activas en pantalla."""
    pedidas = tuple(MAPA_CAPAS_INFORME)
    return [c for c in capas_activas() if c in pedidas]
