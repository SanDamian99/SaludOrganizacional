"""
Una conexión de lectura a Supabase por proceso.

`supabase.create_client` abre un cliente HTTP nuevo cada vez (conexiones,
cabeceras, sesión). Los módulos de lectura lo llamaban en cada consulta: cada
rerun de cada visitante pagaba esa creación. Aquí se guarda una instancia por
(url, clave) y se reutiliza; las credenciales de la vista previa (usuario de
carga, con sesión) siguen gestionándose aparte en `core.vista_previa`.

Las pruebas no pasan por aquí: sustituyen `_cliente()` en cada módulo de
lectura por el cliente falso de `tests/supabase_falso.py`.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=4)
def cliente_lectura(url: str, key: str):
    """Cliente anónimo de Supabase, compartido por todo el proceso."""
    from supabase import create_client
    return create_client(url, key)


def olvidar() -> None:
    """Descarta las conexiones guardadas (cambio de credenciales o pruebas)."""
    cliente_lectura.cache_clear()
