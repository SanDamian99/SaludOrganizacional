"""
Módulo legacy de IA — usa GeminiClient como backend principal.
Mantiene funciones auxiliares para compatibilidad con report_builder.
"""
import logging
from src.ai.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


def generate_analysis(prompt: str) -> str:
    """
    Genera texto usando Gemini basado en el prompt proporcionado.
    Delega al GeminiClient centralizado.
    """
    try:
        client = get_gemini_client()
        if not client:
            return "Error: No se encontró la API Key de Gemini."
        return client.generate_response(prompt)
    except Exception as e:
        logger.error(f"Error al generar análisis con IA: {e}")
        return f"Error al generar análisis con IA: {str(e)}"


def build_report_prompt(promedios, fortalezas, riesgos) -> str:
    """
    Construye un prompt detallado para el informe de salud organizacional.
    """
    prompt = f"""
    Actúa como un experto consultor en Psicología Organizacional y Salud Ocupacional con 20 años de experiencia.
    Tu tarea es analizar los resultados de una evaluación de riesgo psicosocial y bienestar.
    
    **Datos del Análisis:**
    
    *   **Promedios por Dimensión (Escala típica 1-7 o 1-5):**
        {promedios}
        
    *   **Fortalezas Identificadas (Puntajes altos/positivos):**
        {fortalezas}
        
    *   **Riesgos Identificados (Puntajes bajos/negativos):**
        {riesgos}
        
    **Instrucciones para el Reporte:**
    
    1.  **Resumen Ejecutivo:** Provee una visión general del estado de la organización. Sé directo y objetivo.
    2.  **Análisis de Fortalezas:** Explica qué significan estos resultados positivos para la empresa y cómo pueden potenciarlos.
    3.  **Análisis de Riesgos:** Profundiza en las áreas de riesgo. ¿Qué implicaciones tienen para la salud de los empleados y la productividad? Usa literatura científica para respaldar tus afirmaciones (cita autores clásicos como Maslach, Karasek, o modelos de la OMS si aplica, pero mantén el tono profesional, no académico denso). Incluye referencias en formato APA.
    4.  **Recomendaciones Estratégicas:** Propón 3-5 acciones concretas, viables y de alto impacto para mitigar los riesgos y mantener las fortalezas.
    
    **Formato de Salida:**
    Usa Markdown limpio. Usa negritas para resaltar puntos clave. Estructura con títulos claros (##).
    El tono debe ser formal, empático pero firme en la evidencia.
    """
    return prompt
