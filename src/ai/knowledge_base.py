import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
import streamlit as st
from typing import List, Dict, Any
import os
import re

class KnowledgeBase:
    def __init__(self, persist_directory=".chroma", test_mode=False):
        # We use Gemini's embedding model if API Key is available
        self.api_key = os.environ.get("GEMINI_API_KEY")
        
        # Configure ChromaDB to store data locally or in memory for tests
        if test_mode:
            self.chroma_client = chromadb.EphemeralClient()
        else:
            self.chroma_client = chromadb.PersistentClient(path=persist_directory, settings=Settings(anonymized_telemetry=False))
        
        if self.api_key:
             # Default to Gemini embedding model
             self.ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=self.api_key, model_name="models/text-embedding-004")
        else:
             # Fallback to local sentence-transformers if no API key
             self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
             
        # Get or create the main collection for psychology knowledge
        self.collection = self.chroma_client.get_or_create_collection(
            name="organizational_psychology",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )

    def is_empty(self) -> bool:
        """Check if the knowledge base has documents."""
        try:
             return self.collection.count() == 0
        except:
             return True

    def count(self) -> int:
        return self.collection.count()

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]] = None, ids: List[str] = None):
        """Adds documents to the vector store."""
        if not documents:
            return
            
        if ids is None:
            # Generate deterministic IDs if none provided
            ids = [f"doc_{hash(doc)}" for doc in documents]
            
        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in documents]
            
        # Add to Chroma (handles batching implicitly for small/medium sizes)
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query_knowledge(self, query: str, n_results: int = 3) -> str:
        """Queries the vector store and returns formatted context string."""
        if self.is_empty():
            return ""
            
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if not results['documents'] or len(results['documents'][0]) == 0:
            return ""
            
        context_parts = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'][0] else {}
            source = metadata.get("source", "Literatura científica de salud ocupacional")
            context_parts.append(f"Referencia [{i+1}] ({source}):\n{doc}")
            
        return "\n\n".join(context_parts)
        
    def populate_seed_data(self):
        """Adds foundational organizational psychology knowledge if empty."""
        if not self.is_empty():
            return
            
        # Seed Knowledge
        seed_docs = [
            "El Síndrome de Burnout (Agotamiento) se caracteriza por tres dimensiones: agotamiento emocional, despersonalización y baja realización personal. Según Maslach y Jackson, es una respuesta al estrés crónico laboral.",
            "El modelo Demandas-Recursos Laborales (JD-R) postula que las demandas laborales (carga de trabajo, presión de tiempo) agotan la energía, mientras que los recursos laborales (autonomía, apoyo social) fomentan el engagement y amortiguan el impacto de las demandas.",
            "El Engagement laboral, definido por Schaufeli y Bakker, es un estado mental positivo relacionado con el trabajo, caracterizado por el Vigor, la Dedicación y la Absorción.",
            "El apoyo del líder (Liderazgo transformacional) es un recurso clave que reduce el estrés laboral y aumenta la satisfacción, promoviendo un clima de seguridad psicológica (Edmondson).",
            "La claridad de rol reduce la ambigüedad y el conflicto de rol, siendo fundamental para disminuir la tensión psicológica en el trabajo (Kahn et al.)."
        ]
        
        seed_metas = [
            {"source": "Maslach, C., & Jackson, S. E. (1981)"},
            {"source": "Bakker, A. B., & Demerouti, E. (2007)"},
            {"source": "Schaufeli, W. B., & Bakker, A. B. (2004)"},
            {"source": "Edmondson, A. (1999); Bass, B. M. (1990)"},
            {"source": "Kahn, R. L. et al. (1964)"}
        ]
        
        self.add_documents(seed_docs, metadatas=seed_metas)
