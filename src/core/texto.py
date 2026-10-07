"""Normalización de texto compartida por todos los módulos."""
from __future__ import annotations

import re
import unicodedata

import numpy as np


def norm_txt(s) -> str:
    """Minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.replace("\xa0", " ").lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())
