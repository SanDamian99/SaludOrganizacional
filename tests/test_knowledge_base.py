import pytest

from src.ai.knowledge_base import KnowledgeBase


@pytest.fixture
def kb():
    kb = KnowledgeBase(test_mode=True)
    if not kb.enabled:
        pytest.skip("RAG deshabilitado (chromadb o el modelo de embeddings no disponibles sin red)")
    return kb


def test_seed_population(kb):
    kb.populate_seed_data()
    # Debería tener las n sentencias semillas (al menos 3)
    assert kb.count() >= 3

def test_rag_query(kb):
    kb.add_documents(
        ["El salario emocional es un tipo de retribución no económica."], 
        [{"source": "Paper de prueba"}],
        ["doc_salario"]
    )
    result = kb.query_knowledge("Qué es el salario emocional?")
    assert "salario emocional" in result.lower()
    assert "Paper de prueba" in result
