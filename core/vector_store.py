# core/vector_store.py
import chromadb
from langchain_chroma import Chroma
from .constants import VECTOR_STORE_DIR, CHROMA_COLLECTION_NAME, POLICY_SEARCH_K
from .llm_provider import get_embedding_model

_vector_store_instance = None

def get_vector_store() -> Chroma:
    """Initializes and returns a singleton Chroma vector store instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        if not VECTOR_STORE_DIR.exists():
            raise FileNotFoundError(
                f"Chroma vector store directory not found at {VECTOR_STORE_DIR}. "
                "Run the scripts/document_embedder.py script first."
            )
        try:
            _vector_store_instance = Chroma(
                collection_name=CHROMA_COLLECTION_NAME,
                persist_directory=str(VECTOR_STORE_DIR),
                embedding_function=get_embedding_model() # Use embedding model from provider
            )
            print(f"Connected to Chroma vector store at {VECTOR_STORE_DIR}")
        except Exception as e:
            print(f"Error connecting to Chroma DB: {e}")
            raise RuntimeError(f"Could not connect to vector store: {e}")
    return _vector_store_instance

def get_retriever(k: int = POLICY_SEARCH_K):
    """Gets a retriever from the vector store."""
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": k})