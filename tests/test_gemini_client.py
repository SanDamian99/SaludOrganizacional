"""Tests del cliente Gemini — usan mocks para no consumir API real."""
import pytest
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@patch('src.ai.gemini_client.get_gemini_api_key', return_value=None)
def test_no_api_key_returns_fallback(mock_key):
    from src.ai.gemini_client import GeminiClient
    client = GeminiClient()
    response = client.generate_response("¿Cómo está el burnout?")
    assert "no fue posible" in response.lower() or "api key" in response.lower()


@patch('src.ai.gemini_client.get_gemini_api_key', return_value="fake-key")
@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
def test_successful_response(mock_configure, mock_model_class, mock_key):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="El burnout está en nivel medio.")
    mock_model_class.return_value = mock_model

    from src.ai.gemini_client import GeminiClient
    client = GeminiClient()
    response = client.generate_response("¿Cómo está el burnout?")
    assert "burnout" in response.lower() or "nivel" in response.lower()


@patch('src.ai.gemini_client.get_gemini_api_key', return_value="fake-key")
@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
def test_api_failure_uses_fallback(mock_configure, mock_model_class, mock_key):
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API unavailable")
    mock_model_class.return_value = mock_model

    from src.ai.gemini_client import GeminiClient
    client = GeminiClient()
    response = client.generate_response("¿Cuál es el nivel de estrés?")
    # No debe lanzar excepción, debe retornar mensaje de fallback
    assert isinstance(response, str)
    assert len(response) > 0


@patch('src.ai.gemini_client.get_gemini_api_key', return_value="fake-key")
@patch('google.generativeai.GenerativeModel')
@patch('google.generativeai.configure')
def test_same_prompt_uses_cache(mock_configure, mock_model_class, mock_key):
    """El mismo prompt dos veces solo debe llamar a la API una vez."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="respuesta cacheada")
    mock_model_class.return_value = mock_model

    from src.ai.gemini_client import GeminiClient
    client = GeminiClient()

    client.generate_response("pregunta repetida")
    client.generate_response("pregunta repetida")

    # Segunda llamada debe venir del caché
    assert mock_model.generate_content.call_count == 1
