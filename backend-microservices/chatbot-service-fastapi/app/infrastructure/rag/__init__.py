"""RAG (Retrieval-Augmented Generation) infrastructure.

Chroma vector DB + sentence-transformers embeddings cho chatbot
trả lời FAQ / policy / lot info từ knowledge base markdown.
"""
from app.infrastructure.rag.rag_store import (
    RAGStore,
    RetrievedDoc,
    get_rag_store,
    init_rag_store,
)

__all__ = ["RAGStore", "RetrievedDoc", "get_rag_store", "init_rag_store"]
