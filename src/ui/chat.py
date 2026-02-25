"""
Chat con IA — Asistente Virtual Especializado en Psicología Organizacional.
Incluye pathways para preguntas sensibles e individuales, y preguntas sugeridas.
"""
import streamlit as st
from src.ai.gemini_client import GeminiClient


SYSTEM_PROMPT = """Eres un experto en psicología organizacional y bienestar laboral, 
parte del equipo de investigación de una universidad. Tu rol es ayudar a personas 
(empleados, directivos, investigadores) a entender los resultados de un estudio 
sobre salud mental en el trabajo.

REGLAS:
- Usa lenguaje claro y simple. Si usas un término técnico, explícalo inmediatamente.
- Contextualiza siempre los números: "un puntaje de 5.2/7 indica que..."
- Cita fuentes académicas en formato APA cuando hagas afirmaciones sobre bienestar laboral.
- Si no tienes datos para responder algo, di exactamente qué SÍ puedes responder.
- NUNCA reveles datos de individuos específicos, solo promedios y tendencias grupales.
- NUNCA inventes cifras. Si no hay datos, dilo claramente.
- Al final de cada respuesta, sugiere 2-3 preguntas de seguimiento relevantes.

SOBRE LOS DATOS DISPONIBLES:
{dataset_context}
"""


def _build_system_prompt(df=None) -> str:
    """Construye el prompt con contexto real del dataset."""
    if df is None or df.empty:
        dataset_context = "No hay datos cargados aún."
    else:
        n_rows = len(df)
        n_dims = len([c for c in df.columns if any(
            p in str(c) for p in ['(BM)', '(CT)', '(CL)', '(AG)']
        )])
        dataset_context = (
            f"Dataset activo: {n_rows:,} participantes, "
            f"aproximadamente {n_dims} dimensiones de bienestar medidas."
        )
    return SYSTEM_PROMPT.format(dataset_context=dataset_context)


def _classify_question(question: str) -> str:
    """
    Clasifica la pregunta antes de enviarla a Gemini.
    Returns: "answerable" | "individual_data" | "sensitive"
    """
    q_lower = question.lower()

    # Solicitud de datos individuales
    individual_kw = ["persona específica", "empleado x", "quién tiene", "nombre",
                     "correo", "quien", "fulano", "pedro", "maria"]
    if any(w in q_lower for w in individual_kw) and any(
        w2 in q_lower for w2 in ["peor", "mejor", "puntaje", "dato"]
    ):
        return "individual_data"

    # Tema sensible de salud mental
    sensitive_kw = ["suicidio", "autolesión", "crisis", "emergencia", "matar",
                    "depresion clinica", "ansiedad severa", "morir", "daño"]
    if any(w in q_lower for w in sensitive_kw):
        return "sensitive"

    return "answerable"


def render_chat():
    st.markdown("## 🤖 Asistente Virtual Especializado")
    st.caption("Impulsado por Gemini 2.5 Flash Lite — Especialista en Psicología Organizacional")

    client = GeminiClient()

    if not client.is_configured():
        st.error(
            "⚠️ API Key de Gemini no encontrada. Por favor, configúrala en "
            "`.streamlit/secrets.toml` o en tus variables de entorno."
        )
        return

    # Warning si no hay datos
    df = st.session_state.get("df")
    if df is None:
        st.warning(
            "📊 No hay datos cargados actualmente. El modelo te responderá basándose "
            "en su conocimiento general de psicometría, pero no realizará cálculos "
            "sobre tu organización. Ve a 'Cargar Datos' para analizar un conjunto específico."
        )

    # Preguntas sugeridas (empty state)
    if not st.session_state.get("messages"):
        st.info("👋 ¡Hola! Soy tu Asistente Virtual. Estoy aquí para ayudarte a interpretar las encuestas de bienestar.")
        st.markdown("**💡 Puedes empezar preguntando:**")
        suggested = [
            "¿Cuál es la dimensión con mayor riesgo en la organización?",
            "¿Cómo están los niveles de burnout?",
            "¿Qué fortalezas tiene el equipo?",
            "¿Hay diferencias entre grupos demográficos?",
        ]
        cols = st.columns(2)
        for i, q in enumerate(suggested):
            if cols[i % 2].button(q, key=f"suggested_{i}"):
                st.session_state["prefill_question"] = q
                st.rerun()

    # Mostrar Historial
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Check for prefilled question
    prefill = st.session_state.pop("prefill_question", None)

    # Input Box
    user_input = st.chat_input("Haz una pregunta sobre los datos de bienestar...")
    prompt = prefill or user_input

    if prompt:
        # Agregar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Pathway classification
        pathway = _classify_question(prompt)

        with st.chat_message("assistant"):
            if pathway == "individual_data":
                response = (
                    "Por razones de confidencialidad, no puedo mostrar datos de personas "
                    "específicas. Puedo mostrarte promedios por grupo, departamento o "
                    "cualquier otra segmentación agregada. ¿Qué grupo te interesa analizar?"
                )
                st.markdown(response)

            elif pathway == "sensitive":
                response = (
                    "Este tema requiere atención especializada. Si alguien del equipo "
                    "está en una situación difícil, te recomiendo contactar a un profesional "
                    "de salud mental.\n\nRespecto a los datos del estudio, puedo mostrarte "
                    "los indicadores de bienestar general del grupo si lo deseas."
                )
                st.markdown(response)

            else:
                with st.spinner("Analizando con Gemini (esto puede tomar varios segundos)..."):
                    # Build enriched prompt with system context
                    system_ctx = _build_system_prompt(df)
                    full_prompt = f"INSTRUCCIONES DEL SISTEMA:\n{system_ctx}\n\nPREGUNTA DEL USUARIO:\n{prompt}"
                    response = client.generate_response(full_prompt, df_context=df)
                    st.markdown(response)

        # Save assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})
