"""
Cliente para Google Gemini API - gemini-2.5-flash-lite
Usando: google-generativeai >= 0.8.0
"""
import hashlib
import time
import logging
from typing import Optional
import streamlit as st

logger = logging.getLogger(__name__)


def get_gemini_api_key() -> Optional[str]:
    """Obtiene API key desde secrets o variables de entorno."""
    try:
        return st.secrets.get("YOUR_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    except Exception:
        import os
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("YOUR_API_KEY")


class GeminiClient:
    MODEL = "gemini-2.5-flash-lite"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # segundos, se duplica en cada intento
    CALLS_PER_MINUTE = 10

    def __init__(self):
        self.api_key = get_gemini_api_key()
        self.model = None
        self.current_df = None  # contexto de datos para las herramientas analíticas
        self._call_timestamps: list[float] = []
        self._response_cache: dict[str, tuple[float, str]] = {}
        self._cache_ttl = 3600  # 1 hora
        self._session_stats = {"calls": 0, "errors": 0, "cache_hits": 0}

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.MODEL)
                logger.info(f"GeminiClient inicializado con modelo {self.MODEL}")
            except Exception as e:
                logger.error(f"Error inicializando Gemini: {e}")

    def is_configured(self) -> bool:
        return self.model is not None

    # ------ Rate Limiting & Caching ------

    def _rate_limit_check(self) -> bool:
        """Retorna True si se puede hacer una llamada, False si hay que esperar."""
        now = time.time()
        self._call_timestamps = [t for t in self._call_timestamps if t > now - 60]
        return len(self._call_timestamps) < self.CALLS_PER_MINUTE

    def _cache_key(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached(self, prompt: str) -> Optional[str]:
        key = self._cache_key(prompt)
        if key in self._response_cache:
            ts, response = self._response_cache[key]
            if time.time() - ts < self._cache_ttl:
                self._session_stats["cache_hits"] += 1
                return response
            else:
                del self._response_cache[key]
        return None

    # ------ Core API ------

    def generate_response(self, prompt: str, df_context=None) -> str:
        """
        Genera respuesta con retry, rate limiting y caché.

        Args:
            prompt: El prompt a enviar
            df_context: DataFrame opcional para agregar estadísticas como contexto

        Returns:
            Respuesta de texto, o mensaje de fallback si falla
        """
        if not self.is_configured():
            return self._fallback_response("API key no configurada.")

        # Enriquecer prompt con contexto del dataframe
        full_prompt = self._build_prompt(prompt, df_context)

        # Revisar caché
        cached = self._get_cached(full_prompt)
        if cached:
            return cached

        # Rate limiting
        if not self._rate_limit_check():
            return self._fallback_response("Límite de solicitudes alcanzado. Intenta en un momento.")

        # Intentos con backoff exponencial
        delay = self.RETRY_DELAY
        for attempt in range(self.MAX_RETRIES):
            try:
                self._call_timestamps.append(time.time())
                self._session_stats["calls"] += 1

                response = self.model.generate_content(full_prompt)
                result = response.text

                # Guardar en caché
                self._response_cache[self._cache_key(full_prompt)] = (time.time(), result)
                return result

            except Exception as e:
                self._session_stats["errors"] += 1
                logger.warning(f"Intento {attempt + 1}/{self.MAX_RETRIES} fallido: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2

        return self._fallback_response("El servicio de IA no está disponible en este momento.")

    def _build_prompt(self, prompt: str, df_context) -> str:
        """Enriquece el prompt con estadísticas del DataFrame si está disponible."""
        if df_context is None:
            return prompt
        try:
            stats = df_context.describe().to_string()[:2000]  # Limitar tamaño
            return f"{prompt}\n\nCONTEXTO DE DATOS:\n{stats}"
        except Exception:
            return prompt

    def _fallback_response(self, reason: str) -> str:
        return (
            f"⚠️ No fue posible generar un análisis automático en este momento ({reason})\n\n"
            "Puedes revisar los datos directamente en el dashboard o intentarlo de nuevo "
            "en unos minutos."
        )

    def get_stats(self) -> dict:
        """Retorna estadísticas de uso de la sesión actual."""
        return {**self._session_stats, "model": self.MODEL, "configured": self.is_configured()}

    # ------ Herramientas analíticas (anclan las respuestas a datos reales) ------

    def _df(self, df=None):
        return df if df is not None else self.current_df

    def calculate_correlation(self, col1: str, col2: str, df=None) -> str:
        """Correlación de Pearson entre dos columnas numéricas."""
        import pandas as pd
        d = self._df(df)
        if d is None or col1 not in d.columns or col2 not in d.columns:
            return f"Error: no se encontraron las columnas '{col1}' y/o '{col2}'."
        s1 = pd.to_numeric(d[col1], errors="coerce")
        s2 = pd.to_numeric(d[col2], errors="coerce")
        if s1.notna().sum() < 2 or s2.notna().sum() < 2:
            return f"Error: '{col1}' o '{col2}' no son numéricas o no tienen datos suficientes."
        r = s1.corr(s2)
        if pd.isna(r):
            return f"Error: no se pudo calcular la correlación entre '{col1}' y '{col2}'."
        return f"Correlation between '{col1}' and '{col2}': {r:.4f}"

    def compare_groups(self, group_col: str, value_col: str, df=None) -> str:
        """Promedio de una métrica por grupo."""
        import pandas as pd
        d = self._df(df)
        if d is None or group_col not in d.columns or value_col not in d.columns:
            return f"Error: no se encontraron las columnas '{group_col}' y/o '{value_col}'."
        vals = pd.to_numeric(d[value_col], errors="coerce")
        if vals.notna().sum() < 1:
            return f"Error: '{value_col}' no es numérica."
        means = vals.groupby(d[group_col]).mean().sort_values(ascending=False)
        lines = [f"Average '{value_col}' by '{group_col}':"]
        for g, v in means.items():
            lines.append(f"  {g}: {v:.2f}")
        return "\n".join(lines)

    def get_summary_statistics(self, col: str, df=None) -> str:
        """Estadísticos descriptivos de una columna."""
        d = self._df(df)
        if d is None or col not in d.columns:
            return f"Error: no se encontró la columna '{col}'."
        try:
            return f"Statistics for '{col}':\n{d[col].describe().to_string()}"
        except Exception as e:
            return f"Error calculando estadísticas de '{col}': {e}"


def get_gemini_client() -> Optional[GeminiClient]:
    """Helper para obtener una instancia configurada del cliente."""
    client = GeminiClient()
    if client.is_configured():
        return client
    return None


def get_cached_client() -> "GeminiClient":
    """Instancia única de GeminiClient por sesión de Streamlit.

    Preserva caché de respuestas y estado de rate-limit entre reruns.
    """
    try:
        import streamlit as st

        @st.cache_resource(show_spinner=False)
        def _make():
            return GeminiClient()

        return _make()
    except Exception:
        return GeminiClient()
