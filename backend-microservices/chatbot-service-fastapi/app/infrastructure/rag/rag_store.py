"""RAG knowledge base using Chroma + sentence-transformers.

Ingest markdown files trong docs/chatbot-knowledge/ thành chunks + embeddings,
retrieve top-K liên quan khi user hỏi FAQ.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
SCORE_THRESHOLD = 0.35  # cosine similarity ≥ threshold mới accept


class RetrievedDoc(NamedTuple):
    content: str
    metadata: dict
    score: float


class RAGStore:
    """Vector store cho FAQ/policy documents."""

    def __init__(self, knowledge_dir: Path, persist_dir: Path):
        self.knowledge_dir = Path(knowledge_dir)
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Lazy import — tránh load khi service không dùng RAG
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        logger.info("RAG: loading embedding model %s ...", EMBEDDING_MODEL)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="parksmart_kb",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("RAG: store ready — %d docs indexed", self.collection.count())

    def ingest_all(self) -> int:
        """Scan knowledge_dir, chunk + embed tất cả markdown files.

        Gọi khi: init lần đầu, OR user thêm/sửa doc trong folder.
        """
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
        )

        # Clear existing chunks
        existing_ids = self.collection.get()["ids"]
        if existing_ids:
            self.collection.delete(ids=existing_ids)
            logger.info("RAG: cleared %d old chunks", len(existing_ids))

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        md_files = list(self.knowledge_dir.rglob("*.md"))
        if not md_files:
            logger.warning("RAG: no markdown files found in %s", self.knowledge_dir)
            return 0

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("RAG: skip %s: %s", md_file, e)
                continue

            # Strip frontmatter if present (--- ... ---)
            if content.startswith("---\n"):
                end = content.find("\n---\n", 4)
                if end > 0:
                    content = content[end + 5:]

            chunks = splitter.split_text(content)
            rel_path = md_file.relative_to(self.knowledge_dir).as_posix()

            for i, chunk in enumerate(chunks):
                chunk_stripped = chunk.strip()
                if len(chunk_stripped) < 50:
                    continue  # skip tiny chunks (headers only)
                doc_id = f"{md_file.stem}#{i}"
                ids.append(doc_id)
                texts.append(chunk_stripped)
                metadatas.append({
                    "source": rel_path,
                    "category": md_file.parent.name,
                    "chunk_idx": i,
                    "title": md_file.stem.replace("-", " ").title(),
                })

        if not texts:
            logger.warning("RAG: no valid chunks from %d files", len(md_files))
            return 0

        logger.info("RAG: embedding %d chunks from %d files ...", len(texts), len(md_files))
        embeddings = self.embedder.encode(texts, batch_size=32, show_progress_bar=False)

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )
        logger.info("RAG: ingested %d chunks ✓", len(texts))
        return len(texts)

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[RetrievedDoc]:
        """Retrieve top-K docs relevant to query."""
        if not query or not query.strip():
            return []

        query_emb = self.embedder.encode([query])[0].tolist()
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
        )

        docs: list[RetrievedDoc] = []
        if not results.get("ids") or not results["ids"][0]:
            return docs

        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            # cosine distance in Chroma = 1 - cosine_similarity → convert back
            score = 1.0 - distance
            if score < SCORE_THRESHOLD:
                continue
            docs.append(RetrievedDoc(
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                score=score,
            ))
        return docs


_rag_store: Optional[RAGStore] = None


def get_rag_store() -> Optional[RAGStore]:
    """Get singleton RAG store (None if not initialized)."""
    return _rag_store


def init_rag_store(knowledge_dir: Path, persist_dir: Path, re_ingest: bool = False) -> Optional[RAGStore]:
    """Initialize RAG store. Re-ingest nếu collection rỗng hoặc re_ingest=True."""
    global _rag_store
    try:
        if _rag_store is None:
            _rag_store = RAGStore(knowledge_dir, persist_dir)
            if re_ingest or _rag_store.collection.count() == 0:
                _rag_store.ingest_all()
        return _rag_store
    except Exception as e:
        logger.exception("RAG: init failed — chatbot runs without RAG")
        return None
