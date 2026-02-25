import pytest
import pandas as pd
from src.ai.response_router import ResponseRouter
from src.ai.prompt_builder import PromptBuilder

def test_router_sensitive_topic():
    router = ResponseRouter()
    pathway = router.route("Me quiero morir por la presion", {})
    assert pathway == "sensitive_topic"
    
def test_router_out_of_scope():
    router = ResponseRouter()
    pathway = router.route("Cual fue el peor puntaje de pedro?", {})
    assert pathway == "out_of_scope"
    
def test_router_needs_clarification():
    router = ResponseRouter()
    pathway = router.route("Esto es malo", {})
    assert pathway == "needs_clarification"

def test_router_direct_answer():
    router = ResponseRouter()
    available = {"columns": ['ID', 'Agotamiento', 'Liderazgo']}
    pathway = router.route("Cual es la correlacion del agotamiento y el liderazgo?", available)
    assert pathway == "direct_answer"
    
def test_prompt_generation():
    pb = PromptBuilder()
    df_info = {"n_rows": 150, "columns": ["Edad", "Sexo", "Burnout"]}
    prompt = pb.build_system_prompt(df_info, "Avg burnout 5.2")
    
    assert "150" in prompt
    assert "Edad, Sexo, Burnout" in prompt
    assert "Avg burnout 5.2" in prompt
    assert "psicología organizacional" in prompt.lower()
