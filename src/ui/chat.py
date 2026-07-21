"""
Chat con IA — Asistente experto en Psicología Organizacional.

Ancla las respuestas a datos reales (puntajes de dimensión calculados) y a fuentes
académicas recuperadas del RAG, reduciendo alucinaciones. Usa el enrutador de
respuestas para manejar temas sensibles, solicitudes individuales y ambigüedad.
"""
import streamlit as st

from src.core.state import get_processed_data
from src.ai.gemini_client import get_cached_client
from src.ai.knowledge_base import get_cached_kb
from src.ai.response_router import ResponseRouter
from src.ai.prompt_builder import PromptBuilder
from src.analysis import scoring, indicators


def _data_context(df) -> str:
    """Resumen compacto de los datos (dimensiones de bienestar o indicadores) para la IA."""
    if df is None or df.empty:
        return "No hay datos cargados."

    # Datasets genéricos (no de bienestar): resumir indicadores detectados
    if not indicators.is_wellbeing_dataset(df):
        inds = indicators.detect_indicators(df)
        stats = indicators.indicator_stats(df, inds)
        if not stats:
            return f"Dataset con {len(df):,} participantes. Sin indicadores numéricos claros."
        lines = [f"Dataset activo: {len(df):,} participantes, {len(stats)} indicadores.",
                 "Indicadores (media [mín-máx], N) — la dirección depende de cada instrumento:"]
        for c, v in stats.items():
            lines.append(f"  - {c}: {v['mean']:.2f} [{v['min']:.0f}-{v['max']:.0f}], N={v['n']}")
        return "\n".join(lines)

    try:
        scores = scoring.compute_dimension_scores(df)
    except Exception:
        scores = {}
    if not scores:
        return f"Dataset con {len(df):,} participantes. Sin dimensiones puntuables detectadas."

    fort, riesgo, inter = scoring.classify_dimensions(scores)
    lines = [f"Dataset activo: {len(df):,} participantes, {len(scores)} dimensiones evaluadas.",
             "Puntajes orientados a bienestar (mayor = mejor):"]
    for dim, info in sorted(scores.items(), key=lambda kv: kv[1]["score"]):
        alpha = info.get("alpha")
        a = f", α={alpha:.2f}" if isinstance(alpha, float) else ""
        lines.append(f"  - {dim}: {info['score']:.2f}/{info['scale_max']:.0f} "
                     f"({info['estado']}, N={info['n']}{a})")
    if riesgo:
        lines.append("Principales riesgos: " + ", ".join(d for d, _ in riesgo[:3]))
    if fort:
        lines.append("Principales fortalezas: " + ", ".join(d for d, _ in fort[:3]))
    return "\n".join(lines)


def render_chat():
    st.markdown("## 🤖 Asistente Virtual Especializado")
    st.caption("Experto en Psicología Organizacional · respuestas ancladas en tus datos y en literatura científica")

    client = get_cached_client()
    if not client.is_configured():
        st.error(
            "⚠️ API Key de Gemini no encontrada. Configúrala en "
            "`.streamlit/secrets.toml` (`YOUR_API_KEY`) o como variable de entorno "
            "`GEMINI_API_KEY`."
        )
        return

    df = get_processed_data()
    client.current_df = df  # habilita las herramientas analíticas
    kb = get_cached_kb()
    router = ResponseRouter()

    if kb.enabled and not kb.is_empty():
        st.caption(f"📚 Base de conocimiento: {kb.count()} referencias disponibles para citar.")

    if df is None:
        st.warning(
            "📊 No hay datos cargados. Responderé con conocimiento general de "
            "psicometría, pero sin calcular sobre tu organización. Ve a 'Cargar Datos'."
        )

    # Empty state con preguntas sugeridas
    if not st.session_state.get("messages"):
        st.info("👋 Soy tu asistente. Te ayudo a interpretar las encuestas de bienestar.")
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

    # Historial
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prefill = st.session_state.pop("prefill_question", None)
    user_input = st.chat_input("Haz una pregunta sobre los datos de bienestar...")
    prompt = prefill or user_input

    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    available = {"columns": list(df.columns)} if df is not None else {}
    pathway = router.route(prompt, available)

    with st.chat_message("assistant"):
        if pathway == "sensitive_topic":
            response = (
                "Este tema requiere atención especializada. Si alguien del equipo está "
                "en una situación difícil, recomiendo contactar a un profesional de salud "
                "mental o a la línea de crisis local.\n\nSobre los datos del estudio, puedo "
                "mostrarte indicadores de bienestar **agregados** del grupo si lo deseas."
            )
            st.markdown(response)

        elif pathway == "out_of_scope":
            response = (
                "Por confidencialidad no puedo identificar a personas específicas. "
                "Puedo darte promedios por grupo, área o cualquier segmentación agregada. "
                "¿Qué grupo te interesa analizar?"
            )
            st.markdown(response)

        elif pathway == "needs_clarification":
            response = (
                "¿Podrías precisar tu pregunta? Por ejemplo, indícame la dimensión "
                "(burnout, satisfacción, apoyo del líder…) o el grupo que te interesa."
            )
            st.markdown(response)

        else:
            with st.spinner("Analizando con la IA..."):
                data_ctx = _data_context(df)
                rag_ctx = kb.query_knowledge(prompt) if kb.enabled else ""

                system_prompt = PromptBuilder().build_system_prompt(
                    {"n_rows": len(df) if df is not None else 0,
                     "columns": list(scoring.compute_dimension_scores(df).keys()) if df is not None else []},
                    stats_context=data_ctx,
                )

                references_block = (
                    f"\n\nREFERENCIAS CIENTÍFICAS DISPONIBLES (cita SOLO estas en APA):\n{rag_ctx}"
                    if rag_ctx else
                    "\n\n(No hay referencias del RAG disponibles; evita inventar citas.)"
                )

                full_prompt = (
                    f"INSTRUCCIONES DEL SISTEMA:\n{system_prompt}"
                    f"{references_block}\n\n"
                    f"DATOS DEL ESTUDIO:\n{data_ctx}\n\n"
                    f"PREGUNTA DEL USUARIO:\n{prompt}"
                )
                response = client.generate_response(full_prompt, df_context=df)
                st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
