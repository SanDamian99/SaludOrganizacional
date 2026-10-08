"""
En local, las descargas de la vista de comunidad pasan por la auditoría.

`ui.cuidadores` corre una vez la auditoría de la publicación
(`publicar.verificar_restas`) al preparar el análisis. Con un hallazgo, la
vista no ofrece ninguna descarga y lo dice con un texto fijo del catálogo.
"""
import pickle

from streamlit.testing.v1 import AppTest

from src.cuidadores import comunidad_catalogo as cc
from src.ui.views import cuidadores_comunidad as vc
from tests import cuidadores_comunidad_datos as datos


def test_preparar_con_auditoria_guarda_los_hallazgos(monkeypatch):
    from src.cuidadores import publicar
    from src.ui import cuidadores as pagina
    monkeypatch.setattr(publicar, "verificar_restas", lambda ac: ["cuidador · algo delata"])
    p = pagina.preparar_con_auditoria(datos.analisis())
    assert p.hallazgos_auditoria == ["cuidador · algo delata"]
    assert vc.descargas_bloqueadas(p)


def test_si_la_auditoria_falla_se_bloquea(monkeypatch):
    from src.cuidadores import publicar
    from src.ui import cuidadores as pagina

    def rota(ac):
        raise RuntimeError("x")
    monkeypatch.setattr(publicar, "verificar_restas", rota)
    assert vc.descargas_bloqueadas(pagina.preparar_con_auditoria(datos.analisis()))


def test_sin_hallazgos_no_se_bloquea():
    from src.ui import cuidadores as pagina
    p = pagina.preparar_con_auditoria(datos.analisis())
    assert p.hallazgos_auditoria == []
    assert not vc.descargas_bloqueadas(p)
    assert not vc.descargas_bloqueadas(datos.publicado()[0])     # lo publicado ya se auditó


def _app(tmp_path, hallazgos):
    p = datos.preparado()
    p.hallazgos_auditoria = hallazgos
    ruta = tmp_path / "p.pkl"
    with open(ruta, "wb") as fh:
        pickle.dump(p, fh)
    at = AppTest.from_string(
        f"import pickle\nac = pickle.load(open({str(ruta)!r}, 'rb'))\n"
        "from src.ui.views.cuidadores_comunidad import render_comunidad\nrender_comunidad(ac)\n",
        default_timeout=120)
    at.session_state["cuid_com_rol"] = "municipio"
    return at.run()


def _descargas(at):
    return [e for e in at.get("download_button")]


def test_con_hallazgos_las_descargas_estan_desactivadas(tmp_path):
    at = _app(tmp_path, ["algo"])
    assert not at.exception
    botones = _descargas(at)
    assert botones and all(b.proto.disabled for b in botones)
    assert any(cc.DESCARGAS_BLOQUEADAS in c.value for c in at.caption)


def test_sin_hallazgos_las_descargas_funcionan(tmp_path):
    at = _app(tmp_path, [])
    assert not at.exception
    botones = _descargas(at)
    assert botones and not any(b.proto.disabled for b in botones)
    assert not any(cc.DESCARGAS_BLOQUEADAS in c.value for c in at.caption)
