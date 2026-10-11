"""
Video del municipio — Observatorio 360.

Para la Secretaría de Educación y los rectores: 60 a 90 s, sin audio y con
rótulos grandes. Tres ideas, para decidir y no para diagnosticar: dónde hemos
escuchado, qué protege y qué puede hacer cada quién.

Reglas:
  · Los mapas son los del producto: pasan por la misma tabla y la misma auditoría
    (`mapa_datos`, `auditoria_mapa`); si la auditoría falla, no hay video.
  · Solo cobertura y factores protectores. Nunca alertas, malestar, SDQ, RCADS ni
    cifras de grupos ocultos.
  · Las acciones y las lecturas salen de `catalog.MENSAJES`: texto fijo revisado
    por personas, no escrito aquí ni generado por IA. Los títulos de las escenas
    son texto nuevo: por eso el video lleva el sello BORRADOR hasta que el equipo
    apruebe el guion (`opciones.VIDEO_APROBADO`, a mano).
  · Las rutas de atención solo salen con `VIDEO_RUTAS` y `RUTAS_VALIDADAS`.
  · Nada de Streamlit aquí; el script que lo genera es `scripts/generar_video_municipio.py`.
"""
from __future__ import annotations

import io
import os
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from PIL import Image, ImageChops

from src.estudiantes import alertas_catalogo as alertas_cat
from src.estudiantes import catalog as cat
from src.geo import auditoria_mapa, colegios_geo, mapa_datos, mapa_figura, opciones

FORMATOS = {"horizontal": (1920, 1080), "cuadrado": (1080, 1080)}
T_CRUCE = 0.6
FPS = 30
NAVY = "#16365F"
TINTA = "#1D2733"
GRIS = "#5B6776"
SELLO_TEXTO = "BORRADOR · para revisión del equipo"

# (tamaños en puntos con 100 ppp, ancho de línea en caracteres, alto de la franja)
_DISENO = {
    "horizontal": dict(titulo=40, sub=24, cuerpo=26, ancho=80, franja=0.15, pie=0.22),
    "cuadrado": dict(titulo=30, sub=19, cuerpo=22, ancho=48, franja=0.16, pie=0.30),
}

# De qué mensaje del catálogo sale cada acción (solo las que se entienden solas)
ACCION_COLEGIO = ("adulto_confianza", "accion_colegio")
ACCIONES_SECRETARIA = (("pertenencia", "accion_municipio"),
                       ("apoyo_familia", "accion_municipio"))


@dataclass(frozen=True)
class Escena:
    duracion: float
    png: bytes
    textos: list
    sello: bool


def es_borrador() -> bool:
    """Sin la llave de aprobación el video es un borrador, siempre."""
    return not opciones.VIDEO_APROBADO


def formatos() -> list[str]:
    return ["horizontal"] + (["cuadrado"] if opciones.VIDEO_VARIANTE_CELULAR else [])


def nombre_archivo(formato: str) -> str:
    return f"observatorio360_municipio_{formato}{'_BORRADOR' if es_borrador() else ''}.mp4"


# ── Textos ───────────────────────────────────────────────────────────────────
def _primera_oracion(texto: str) -> str:
    return texto.split(". ")[0].rstrip(".") + "."


def _mensaje(clave: str, campo: str) -> str:
    return getattr(cat.MENSAJES[clave], campo)


def _rutas() -> list[str]:
    """Las rutas, solo con las dos llaves (la del video y la validación del equipo)."""
    if not (opciones.VIDEO_RUTAS and alertas_cat.RUTAS_VALIDADAS):
        return []
    return [f"{nombre}: {detalle}" for nombre, detalle in cat.RUTA_ATENCION]


# ── Dibujo ───────────────────────────────────────────────────────────────────
def _rgba(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def _recortar(arr: np.ndarray, margen: int = 14) -> np.ndarray:
    """Quita el margen blanco alrededor del mapa para que ocupe más pantalla."""
    img = Image.fromarray(arr).convert("RGB")
    caja = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255))).getbbox()
    if caja is None:
        return np.asarray(img)
    x0, y0, x1, y1 = caja
    return np.asarray(img.crop((max(0, x0 - margen), max(0, y0 - margen),
                                min(img.width, x1 + margen), min(img.height, y1 + margen))))


def _lienzo(formato: str, fondo: str = "white"):
    ancho, alto = FORMATOS[formato]
    fig = Figure(figsize=(ancho / 100, alto / 100), dpi=100, facecolor=fondo)
    FigureCanvasAgg(fig)
    return fig, ancho, alto


def _png(fig, sello: bool) -> bytes:
    if sello:
        fig.text(0.5, 0.5, SELLO_TEXTO, rotation=22, fontsize=48, color="#7F8C9B",
                 alpha=0.22, ha="center", va="center", weight="bold", zorder=50)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor=fig.get_facecolor())
    return buf.getvalue()


def _franja(fig, d: dict, titulo: str) -> None:
    fig.add_artist(Rectangle((0, 1 - d["franja"]), 1, d["franja"],
                             transform=fig.transFigure, facecolor=NAVY, edgecolor="none"))
    fig.text(0.04, 1 - d["franja"] / 2, titulo, color="white", fontsize=d["titulo"],
             weight="bold", va="center", ha="left")


def _envolver(texto: str, d: dict) -> str:
    return textwrap.fill(texto, width=d["ancho"])


def _escena_titulo(formato: str, titulo: str, subtitulo: str, sello: bool) -> Escena:
    d = _DISENO[formato]
    fig, _, _ = _lienzo(formato, NAVY)
    fig.text(0.5, 0.56, textwrap.fill(titulo, d["ancho"] // 2 + 4), color="white",
             fontsize=d["titulo"] + 14, weight="bold", ha="center", va="center")
    fig.text(0.5, 0.36, _envolver(subtitulo, d), color="#C9D6E8", fontsize=d["sub"],
             ha="center", va="center", linespacing=1.4)
    return Escena(0, _png(fig, sello), [titulo, subtitulo], sello)


def _escena_columnas(formato: str, titulo: str, columnas: list[tuple[str, list[str]]],
                     sello: bool) -> Escena:
    """Texto en columnas (16:9) o apilado (cuadrado): (encabezado, [párrafos])."""
    d = _DISENO[formato]
    fig, _, _ = _lienzo(formato)
    _franja(fig, d, titulo)
    apilado = formato == "cuadrado" or len(columnas) == 1
    una = len(columnas) == 1
    cuerpo = d["cuerpo"] + (8 if una else 0)
    ancho_linea = int(d["ancho"] * (0.78 if una else 1.0)) if apilado else d["ancho"] // 2 - 6
    ancho_col = 0.92 if apilado else 0.92 / len(columnas)
    paso = 0.0245 * cuerpo / d["cuerpo"]       # alto de una línea, como fracción del lienzo
    textos = [titulo]
    y_ini = 1 - d["franja"] - (0.20 if una else 0.07)
    y = y_ini
    for i, (encabezado, parrafos) in enumerate(columnas):
        x = 0.04 + (0 if apilado else i * ancho_col)
        if not apilado:
            y = y_ini
        if encabezado:
            fig.text(x, y, encabezado, color=NAVY, fontsize=cuerpo + 4, weight="bold", va="top")
            y -= 0.08
            textos.append(encabezado)
        for p in parrafos:
            bloque = textwrap.fill(p, ancho_linea)
            fig.text(x, y, bloque, color=TINTA, fontsize=cuerpo, va="top", linespacing=1.35)
            y -= paso * (bloque.count("\n") + 1) * 1.35 + 0.045
            textos.append(p)
        if apilado:
            y -= 0.03
    return Escena(0, _png(fig, sello), textos, sello)


def _escena_mapas(formato: str, titulo: str, mapas: list[tuple[str, np.ndarray]],
                  pie: list[str], sello: bool) -> Escena:
    """Uno o dos mapas lado a lado con su rótulo y el texto debajo.

    Con dos mapas lo que limita es el ancho, no el alto: poner el texto a un lado los
    hace más chicos, así que va siempre debajo.
    """
    d = _DISENO[formato]
    fig, ancho, alto = _lienzo(formato)
    _franja(fig, d, titulo)
    techo = alto * d["franja"] + 14
    area_x, area_w = 0.04 * ancho, 0.92 * ancho
    area_h = alto * (1 - d["franja"] - d["pie"]) - 20
    rotulo_alto, hueco, n = 54, 40, len(mapas)
    proporcion = mapas[0][1].shape[1] / mapas[0][1].shape[0]
    img_ancho = min(int((area_w - hueco * (n - 1)) / n), int((area_h - rotulo_alto) * proporcion))
    img_alto = int(img_ancho / proporcion)
    total = n * img_ancho + (n - 1) * hueco
    x0 = area_x + (area_w - total) / 2
    textos = [titulo]
    for i, (rotulo, arr) in enumerate(mapas):
        x = int(x0 + i * (img_ancho + hueco))
        fig.text((x + img_ancho / 2) / ancho, 1 - (techo + rotulo_alto / 2) / alto, rotulo,
                 color=NAVY, fontsize=d["sub"] + 2, weight="bold", ha="center", va="center")
        miniatura = Image.fromarray(arr).convert("RGB").resize((img_ancho, img_alto),
                                                               Image.LANCZOS)
        fig.figimage(np.asarray(miniatura), xo=x,
                     yo=int(alto - techo - rotulo_alto - img_alto), zorder=2)
        textos.append(rotulo)
    x, y, linea, letra = 0.04, d["pie"] - 0.035, d["ancho"] + 14, d["cuerpo"] - 2
    for texto in pie:
        bloque = textwrap.fill(texto, linea)
        fig.text(x, y, bloque, color=TINTA, fontsize=letra, va="top", linespacing=1.35)
        y -= 0.0245 * letra / d["cuerpo"] * (bloque.count("\n") + 1) * 1.35 + 0.04
        textos.append(texto)
    return Escena(0, _png(fig, sello), textos, sello)


# ── Mapas auditados ──────────────────────────────────────────────────────────
def _niveles(analisis: dict) -> list[str]:
    return [n for n in (cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA)
            if n in analisis and getattr(analisis[n], "n", 0) >= cat.MIN_GROUP_N]


def _mapas(analisis: dict, niveles: list[str], capa: str):
    """[(rótulo, imagen)] y los colegios con cifras por nivel, todo auditado."""
    puntos, avisos = colegios_geo.cargar_puntos()
    if not puntos:
        raise ValueError("No hay coordenadas verificadas de colegios: " + "; ".join(avisos))
    from src.ui.views import estudiantes_comunidad as vc
    nombres = {cat.NIVEL_SECUNDARIA: "Secundaria", cat.NIVEL_PRIMARIA: "Primaria"}
    mapas, con_cifra = [], {}
    for nivel in niveles:
        a = analisis[nivel]
        visibles, pequenos = vc.grupos_visibles(a, "Colegio")
        filas = mapa_datos.tabla_mapa(a, capa, [p.codigo for p in puntos], visibles, pequenos)
        auditoria_mapa.auditar(filas, capa, visibles, pequenos)
        fig = mapa_figura.figura_estatica(filas, capa, puntos,
                                          nombres=opciones.VIDEO_NOMBRES_COLEGIOS)
        mapas.append((nombres.get(nivel, nivel), _recortar(_rgba(fig))))
        con_cifra[nivel] = sum(1 for f in filas if f.estado == mapa_datos.CON_CIFRA)
    return mapas, con_cifra


def _frase_cobertura(con_cifra: dict) -> str:
    nombres = {cat.NIVEL_SECUNDARIA: "Secundaria", cat.NIVEL_PRIMARIA: "Primaria"}
    partes = [f"{nombres.get(n, n)}: {c} colegios con cifras" for n, c in con_cifra.items()]
    return " · ".join(partes) + "."


# ── El guion ─────────────────────────────────────────────────────────────────
def construir_escenas(analisis: dict, formato: str) -> list[Escena]:
    """Las escenas del video, con su duración. Levanta si no hay nada seguro que mostrar."""
    niveles = _niveles(analisis)
    if not niveles:
        raise ValueError("No hay resultados de estudiantes con base suficiente.")
    sello = es_borrador()
    mapas_resp, con_cifra = _mapas(analisis, niveles, "respuestas")
    mapas_parte, _ = _mapas(analisis, niveles, "sentirse_parte")
    escenas = [
        (5, _escena_titulo(formato, "Chía escucha a sus estudiantes",
                           "Observatorio 360 · Estudiantes · lo que hemos escuchado y lo "
                           "que podemos hacer", sello)),
        (7, _escena_columnas(formato, "Cómo leer los mapas",
                             [("", ["Cada círculo es un colegio de Chía.",
                                    mapa_datos.NOTA_LECTURA])], sello)),
        (12, _escena_mapas(formato, "Dónde hemos escuchado", mapas_resp,
                           [mapa_datos.LEYENDAS["respuestas"], _frase_cobertura(con_cifra)],
                           sello)),
        (14, _escena_mapas(formato, "Qué protege: sentirse parte del colegio", mapas_parte,
                           [mapa_datos.LEYENDAS["sentirse_parte"],
                            "El tono se compara dentro de cada mapa, no entre niveles.",
                            _mensaje("pertenencia", "significa")], sello)),
    ]
    if opciones.VIDEO_ACCIONES:
        colegio = _primera_oracion(_mensaje(*ACCION_COLEGIO))
        secretaria = [_mensaje(*m) for m in ACCIONES_SECRETARIA]
        escenas.append((18, _escena_columnas(
            formato, "Qué podemos hacer",
            [("Los colegios", [colegio]), ("La Secretaría de Educación", secretaria)],
            sello)))
    cierre = [cat.AVISO_TAMIZAJE]
    rutas = _rutas()
    if rutas:
        cierre.append("Si necesitas ayuda: " + " · ".join(rutas))
    escenas.append((9, _escena_columnas(formato, "Cifras de grupo, nunca de una persona",
                                        [("", cierre)], sello)))
    return [Escena(dur, e.png, e.textos, e.sello) for dur, e in escenas]


# ── MP4 ──────────────────────────────────────────────────────────────────────
def escribir_video(escenas: list[Escena], ruta: str, t_cruce: float = T_CRUCE,
                   fps: int = FPS) -> None:
    """Une las escenas con un cruce suave y escribe un MP4 H.264 compatible con todo."""
    if not escenas:
        raise ValueError("No hay escenas que escribir.")
    ancho, alto = Image.open(io.BytesIO(escenas[0].png)).size
    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for i, e in enumerate(escenas):
            p = os.path.join(tmp, f"escena_{i:02d}.png")
            with open(p, "wb") as f:
                f.write(e.png)
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{e.duracion:.3f}", "-i", p]
        filtros = [f"[{i}:v]scale={ancho}:{alto},setsar=1,fps={fps},format=yuv420p[v{i}]"
                   for i in range(len(escenas))]
        salida, acumulado = "v0", escenas[0].duracion
        for i in range(1, len(escenas)):
            filtros.append(f"[{salida}][v{i}]xfade=transition=fade:duration={t_cruce}:"
                           f"offset={acumulado - t_cruce:.3f}[x{i}]")
            salida = f"x{i}"
            acumulado += escenas[i].duracion - t_cruce
        cmd += ["-filter_complex", ";".join(filtros), "-map", f"[{salida}]",
                "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", ruta]
        resultado = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603 (ffmpeg con lista de argumentos, sin shell)
        if resultado.returncode != 0:
            raise RuntimeError("ffmpeg falló: " + resultado.stderr[-800:])
