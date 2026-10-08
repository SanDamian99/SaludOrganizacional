"""
Navegación — Observatorio 360.

Nombres de página, orden del menú y página inicial por modo de despliegue.

Vive en un módulo propio, y no en `modo.py`, por una razón práctica: al
desplegar, Streamlit vuelve a ejecutar `main.py` pero puede conservar en memoria
la versión vieja de los módulos ya importados. Un módulo que no existía antes se
importa siempre fresco, así que el menú nuevo nunca convive con un `modo` viejo.

Regla de despliegue: tras el primer despliegue este módulo también puede quedar
rancio en memoria. Todo símbolo nuevo va en un módulo nuevo, o se lee con
`getattr` y un valor de respaldo; y después de fusionar siempre hay que hacer
Reboot app.

Las páginas que aún no están construidas figuran en `MENU`, para fijar el orden,
pero no en `DISPONIBLES`: no aparecen hasta que su fase las añada.
"""
from __future__ import annotations

PAGINA_DOCENTES = "Docentes"
PAGINA_ESTUDIANTES = "Estudiantes 360"
PAGINA_CUIDADORES = "Cuidadores 360"
PAGINA_TRIANGULACION = "Triangulación 360"
PAGINA_CHAT = "Chat con IA"
PAGINA_CARGA = "Cargar Datos"
PAGINA_TENDENCIAS = "Análisis de tendencias"
PAGINA_REPORTES = "Reportes"

MENU = (PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CUIDADORES, PAGINA_TRIANGULACION,
        PAGINA_CHAT, PAGINA_CARGA, PAGINA_TENDENCIAS, PAGINA_REPORTES)

# Las que ya tienen vista. Cuidadores entró en la fase 4a y Triangulación en la
# 5, las dos solo para investigadores: Triangulación nunca está en PUBLICAS.
DISPONIBLES = frozenset({PAGINA_DOCENTES, PAGINA_ESTUDIANTES, PAGINA_CUIDADORES,
                         PAGINA_TRIANGULACION, PAGINA_CHAT, PAGINA_CARGA,
                         PAGINA_TENDENCIAS, PAGINA_REPORTES})

# Lo único que puede ver el público. Triangulación es solo para investigadores.
PUBLICAS = (PAGINA_ESTUDIANTES, PAGINA_CUIDADORES)

# Cuidadores es pública solo cuando el equipo aprueba sus textos y rutas y hay
# una corrida de cuidadores publicada (spec §5.5). Lo cambia la fase 4b.
CUIDADORES_PUBLICO = False

_COMPLETO = "completo"
_INVESTIGADOR = "investigador"


def _es_publico(modo: str) -> bool:
    # Igual que `modo.modo()`: lo que no sea completo o investigador es comunidad.
    return modo not in (_COMPLETO, _INVESTIGADOR)


def menu(modo: str) -> list[str]:
    """Páginas del menú en este modo, en orden."""
    if _es_publico(modo):
        visibles = [p for p in PUBLICAS
                    if p != PAGINA_CUIDADORES or CUIDADORES_PUBLICO]
    else:
        visibles = MENU
    return [p for p in MENU if p in visibles and p in DISPONIBLES]


def pagina_inicial(modo: str) -> str:
    """Con qué página abre la aplicación.

    Los dos modos pensados para estudiantes aterrizan en su módulo; el modo de
    trabajo local abre en Docentes, como siempre.
    """
    return PAGINA_DOCENTES if modo == _COMPLETO else PAGINA_ESTUDIANTES
