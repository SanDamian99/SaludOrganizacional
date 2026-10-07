"""El lector solo mira las corridas de estudiantes."""
from src.estudiantes import lectura


class _Consulta:
    """Imita la cadena de PostgREST que usan `id_corrida_vigente` y `_traer_filas`."""

    def __init__(self, registro, tabla):
        self.r, self.t = registro, tabla

    def select(self, *_): return self
    def order(self, *a, **k): return self
    def limit(self, *_): return self
    def range(self, *_): return self

    def eq(self, k, v):
        self.r.append((self.t, k, v))
        return self

    def execute(self):
        class R:
            data = []
        return R()


class _Cliente:
    def __init__(self):
        self.registro = []
        cli = self

        class _S:
            def table(self, t):
                return _Consulta(cli.registro, t)

        class _P:
            def schema(self, _):
                return _S()

        self.postgrest = _P()


def test_el_lector_filtra_por_modulo(monkeypatch):
    cli = _Cliente()
    monkeypatch.setattr(lectura, "_cliente", lambda: cli)
    assert lectura.id_corrida_vigente() is None
    assert lectura._traer_filas(cli) == (None, [])
    assert cli.registro.count(("corridas", "modulo", "estudiantes")) == 2


def test_el_aviso_ya_no_dice_que_no_se_puede_filtrar():
    assert "no se puede filtrar" not in lectura.AVISO_SIN_DATOS_CRUDOS
