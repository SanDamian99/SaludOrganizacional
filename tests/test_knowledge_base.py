import pytest
from src.ai.knowledge_base import KnowledgeBase

def test_kb_initialization():
    kb = KnowledgeBase(test_mode=True)
    assert kb.is_empty() == True
    
def test_seed_population():
    kb = KnowledgeBase(test_mode=True)
    kb.populate_seed_data()
    # Debería tener las n sentencias semillas (al menos 3)
    assert kb.count() >= 3

def test_rag_query():
    kb = KnowledgeBase(test_mode=True)
    kb.add_documents(
        ["El salario emocional es un tipo de retribución no económica."], 
        [{"source": "Paper de prueba"}],
        ["doc_salario"]
    )
    result = kb.query_knowledge("Qué es el salario emocional?")
    assert "salario emocional" in result.lower()
    assert "Paper de prueba" in result
