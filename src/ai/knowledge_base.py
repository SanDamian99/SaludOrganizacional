"""
Base de conocimiento (RAG) sobre psicología organizacional.

Usa ChromaDB con embeddings locales ONNX (all-MiniLM-L6-v2) → funciona sin costo de
API y offline tras la primera descarga del modelo. Degrada con gracia: si Chroma o el
modelo de embeddings no están disponibles, la app sigue funcionando sin RAG.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class KnowledgeBase:
    COLLECTION = "organizational_psychology"

    def __init__(self, persist_directory=".chroma", test_mode=False):
        self.enabled = False
        self.collection = None
        try:
            import chromadb
            from chromadb.config import Settings
            from chromadb.utils import embedding_functions

            if test_mode:
                self.chroma_client = chromadb.EphemeralClient()
            else:
                self.chroma_client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(anonymized_telemetry=False),
                )

            # Embeddings locales ONNX (sin API key, sin torch)
            self.ef = embedding_functions.DefaultEmbeddingFunction()

            self.collection = self.chroma_client.get_or_create_collection(
                name=self.COLLECTION,
                embedding_function=self.ef,
                metadata={"hnsw:space": "cosine"},
            )
            self.enabled = True
        except Exception as e:  # chromadb/onnx ausente o sin red la primera vez
            logger.warning(f"KnowledgeBase deshabilitada (RAG no disponible): {e}")

    def is_empty(self) -> bool:
        if not self.enabled or self.collection is None:
            return True
        try:
            return self.collection.count() == 0
        except Exception:
            return True

    def count(self) -> int:
        if not self.enabled or self.collection is None:
            return 0
        try:
            return self.collection.count()
        except Exception:
            return 0

    def add_documents(self, documents: List[str],
                      metadatas: List[Dict[str, Any]] = None,
                      ids: List[str] = None):
        if not self.enabled or not documents:
            return
        if ids is None:
            ids = [f"doc_{abs(hash(doc))}" for doc in documents]
        if metadatas is None:
            metadatas = [{"source": "desconocido"} for _ in documents]
        try:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        except Exception as e:
            logger.warning(f"No se pudieron agregar documentos al RAG: {e}")

    def query_knowledge(self, query: str, n_results: int = 3) -> str:
        """Recupera contexto relevante formateado. Cadena vacía si no hay RAG/datos."""
        if self.is_empty():
            return ""
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
        except Exception as e:
            logger.warning(f"Fallo la consulta RAG: {e}")
            return ""

        docs = results.get("documents") or [[]]
        if not docs or not docs[0]:
            return ""

        metas = (results.get("metadatas") or [[]])[0]
        parts = []
        for i, doc in enumerate(docs[0]):
            meta = metas[i] if i < len(metas) and metas else {}
            source = meta.get("source", "Literatura científica de salud ocupacional")
            parts.append(f"Referencia [{i+1}] ({source}):\n{doc}")
        return "\n\n".join(parts)

    def populate_seed_data(self):
        """Siembra conocimiento fundacional de psicología organizacional si está vacía."""
        if not self.enabled or not self.is_empty():
            return

        seed_docs = [
            "El Síndrome de Burnout (Agotamiento) se caracteriza por tres dimensiones: "
            "agotamiento emocional, despersonalización y baja realización personal. "
            "Según Maslach y Jackson, es una respuesta al estrés crónico laboral.",
            "El modelo Demandas-Recursos Laborales (JD-R) postula que las demandas "
            "laborales (carga de trabajo, presión de tiempo) agotan la energía, mientras "
            "que los recursos laborales (autonomía, apoyo social) fomentan el engagement "
            "y amortiguan el impacto de las demandas.",
            "El Engagement laboral, definido por Schaufeli y Bakker, es un estado mental "
            "positivo relacionado con el trabajo, caracterizado por el Vigor, la Dedicación "
            "y la Absorción.",
            "El apoyo del líder (Liderazgo transformacional) es un recurso clave que reduce "
            "el estrés laboral y aumenta la satisfacción, promoviendo un clima de seguridad "
            "psicológica (Edmondson).",
            "La claridad de rol reduce la ambigüedad y el conflicto de rol, siendo "
            "fundamental para disminuir la tensión psicológica en el trabajo (Kahn et al.).",
            "El conflicto trabajo-familia se asocia con mayor agotamiento, menor "
            "satisfacción laboral y mayor intención de rotación; las prácticas de "
            "flexibilidad y el apoyo organizacional lo mitigan (Greenhaus & Beutell, 1985).",
            "El salario emocional agrupa retribuciones no económicas (reconocimiento, "
            "desarrollo, conciliación, autonomía) que incrementan el compromiso y la "
            "retención del talento.",
        ]
        seed_metas = [
            {"source": "Maslach, C., & Jackson, S. E. (1981)"},
            {"source": "Bakker, A. B., & Demerouti, E. (2007)"},
            {"source": "Schaufeli, W. B., & Bakker, A. B. (2004)"},
            {"source": "Edmondson, A. (1999); Bass, B. M. (1990)"},
            {"source": "Kahn, R. L. et al. (1964)"},
            {"source": "Greenhaus, J. H., & Beutell, N. J. (1985)"},
            {"source": "Gómez-Rada (2020), salario emocional"},
        ]
        self.add_documents(seed_docs, metadatas=seed_metas)


def get_cached_kb() -> "KnowledgeBase":
    """Instancia única de KnowledgeBase (sembrada) por sesión de Streamlit."""
    try:
        import streamlit as st

        @st.cache_resource(show_spinner=False)
        def _make():
            kb = KnowledgeBase()
            kb.populate_seed_data()
            return kb

        return _make()
    except Exception:
        kb = KnowledgeBase()
        kb.populate_seed_data()
        return kb
