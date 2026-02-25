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


def get_gemini_client() -> Optional[GeminiClient]:
    """Helper para obtener una instancia configurada del cliente."""
    client = GeminiClient()
    if client.is_configured():
        return client
    return None
