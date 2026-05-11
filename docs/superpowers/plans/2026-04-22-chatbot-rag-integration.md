# Chatbot RAG Integration Plan

> **Mục tiêu:** Thêm Retrieval-Augmented Generation (RAG) cho chatbot để trả câu về **FAQ / policy / terms** mà hiện tại chỉ trả câu số liệu.

## Context

**Hiện tại chatbot có thể trả:**
- "Còn chỗ ô tô không?" ✓ (query parking-service)
- "Xe tôi ở đâu?" ✓ (query booking-service)

**Không trả được:**
- "Chính sách hủy booking có phí không?"
- "Bãi có hỗ trợ xe container không?"
- "Hóa đơn thuế bãi thế nào?"
- "Giờ mở cửa bãi Vincom?"
- "Quy định về xe máy điện?"

→ Cần RAG để chatbot đọc tài liệu policy + trả lời.

## Architecture

```
User: "Chính sách hủy booking có phí không?"
      ↓
[Intent classification LLM]
  → "faq" hoặc "unknown"
      ↓
[RAG retrieval]
  Query embedding (sentence-transformers)
      ↓
  Search Chroma vector DB → top 3 docs
      ↓
[Augmented prompt to LLM]
  "Dựa vào context sau đây, trả lời user:
   [doc1: chính sách hủy booking]
   [doc2: phí phạt]
   [doc3: điều khoản]
   User: ..."
      ↓
LLM sinh câu trả lời có citation
      ↓
Response: "Bạn có thể hủy miễn phí trước 30 phút so với start_time.
          Hủy sau → phạt 10% package fee. (Nguồn: Điều khoản sử dụng §4.2)"
```

## Tech stack

| Component | Tool | Lý do |
|---|---|---|
| Vector DB | **Chroma** | Nhẹ, in-memory + auto persist, Python native, không cần server riêng |
| Embedding model | `paraphrase-multilingual-MiniLM-L12-v2` | Support tiếng Việt, 384-dim, 120MB |
| Document format | Markdown files | Dễ viết, version control trong git |
| Chunking strategy | Recursive character splitter, 500 chars + 50 overlap | Balance context vs precision |
| Retrieval | Top-3 similarity with score threshold 0.5 | Đủ context, loại irrelevant |
| Generation | Existing Gemini client | Re-use hạ tầng có sẵn |

## Knowledge base scope

Documents phải có:

### `docs/chatbot-knowledge/policies/`
- `cancellation-policy.md` — hủy booking, refund rules
- `booking-rules.md` — quy định đặt chỗ, thời gian, grace period
- `payment-methods.md` — MoMo, VNPay, cash, thẻ, hoàn tiền
- `terms-of-service.md` — điều khoản chung
- `privacy-policy.md` — bảo mật dữ liệu

### `docs/chatbot-knowledge/lots/`
- `vincom-center-parking.md` — giờ mở, address, số slot, xe được phép
- `aeon-mall-binh-tan.md`
- `saigon-centre.md`
- `lotte-mart-go-vap.md`
- `parksmart-tower.md`

### `docs/chatbot-knowledge/vehicles/`
- `supported-vehicles.md` — ô tô, xe máy, xe điện, xe container?
- `plate-format-vietnam.md` — định dạng biển số VN

### `docs/chatbot-knowledge/faq/`
- `common-questions.md` — 30-50 câu hỏi thường gặp
- `troubleshooting.md` — xử lý lỗi thường gặp

Khoảng **15-20 markdown files, ~50 chunks** sau splitting.

## Tasks

### Task 1: Install dependencies

- [ ] **Step 1.1: Add to requirements.txt**

Thêm vào `backend-microservices/chatbot-service-fastapi/requirements.txt`:
```
chromadb==0.4.22
sentence-transformers==2.2.2
langchain-text-splitters==0.0.1
```

- [ ] **Step 1.2: Install**
```bash
cd backend-microservices/chatbot-service-fastapi
docker compose exec chatbot-service-fastapi pip install chromadb sentence-transformers langchain-text-splitters
```

Hoặc rebuild container:
```bash
cd backend-microservices
docker compose build chatbot-service-fastapi
```

- [ ] **Step 1.3: Verify**
```bash
docker compose exec chatbot-service-fastapi python -c "
import chromadb
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
print('OK - all imports')
"
```

### Task 2: Tạo knowledge base documents

- [ ] **Step 2.1: Tạo folder + skeleton docs**

```bash
mkdir -p docs/chatbot-knowledge/{policies,lots,vehicles,faq}
```

Tạo mỗi file với format:

```markdown
---
title: Chính sách hủy booking
category: policies
keywords: hủy, cancel, refund, phí phạt
---

# Chính sách hủy booking

## Hủy trước 30 phút
Miễn phí hoàn toàn, hoàn 100% tiền đã trả.

## Hủy sau 30 phút nhưng trước start_time
Phí hủy 10% package fee. Hoàn 90%.

## Hủy sau start_time (no-show)
Mất 100% package fee, không hoàn tiền.

## Cancel rate limit
Nếu no-show > 3 lần trong 30 ngày → tài khoản bị force online payment.

## Liên hệ
Chi tiết: support@parksmart.com
```

Tạo đủ 15-20 files theo scope trên.

### Task 3: Tạo RAG module

- [ ] **Step 3.1: Tạo `app/infrastructure/rag/` folder**

```bash
mkdir -p backend-microservices/chatbot-service-fastapi/app/infrastructure/rag
touch backend-microservices/chatbot-service-fastapi/app/infrastructure/rag/__init__.py
```

- [ ] **Step 3.2: Tạo `rag_store.py` — Chroma wrapper**

File: `backend-microservices/chatbot-service-fastapi/app/infrastructure/rag/rag_store.py`

```python
"""RAG knowledge base using Chroma + sentence-transformers."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
SCORE_THRESHOLD = 0.5


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

        logger.info("Loading embedding model %s...", EMBEDDING_MODEL)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="parksmart_kb",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("RAG store ready — %d docs", self.collection.count())

    def ingest_all(self) -> int:
        """Scan knowledge_dir, chunk + embed all markdown files."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " "],
        )

        # Clear existing
        all_ids = self.collection.get()["ids"]
        if all_ids:
            self.collection.delete(ids=all_ids)

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        for md_file in self.knowledge_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            chunks = splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                doc_id = f"{md_file.stem}#{i}"
                ids.append(doc_id)
                texts.append(chunk)
                metadatas.append({
                    "source": str(md_file.relative_to(self.knowledge_dir)),
                    "category": md_file.parent.name,
                    "chunk_idx": i,
                })

        if not texts:
            logger.warning("No markdown files found in %s", self.knowledge_dir)
            return 0

        embeddings = self.embedder.encode(texts, batch_size=32, show_progress_bar=False)
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )
        logger.info("Ingested %d chunks from %d files", len(texts), len(set(m["source"] for m in metadatas)))
        return len(texts)

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[RetrievedDoc]:
        """Retrieve top-K most relevant docs for query."""
        query_emb = self.embedder.encode([query])[0].tolist()
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
        )
        docs: list[RetrievedDoc] = []
        if not results["ids"] or not results["ids"][0]:
            return docs
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            score = 1.0 - distance  # cosine distance → similarity
            if score < SCORE_THRESHOLD:
                continue
            docs.append(RetrievedDoc(
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                score=score,
            ))
        return docs


_rag_store: RAGStore | None = None


def get_rag_store() -> RAGStore | None:
    global _rag_store
    return _rag_store


def init_rag_store(knowledge_dir: Path, persist_dir: Path, re_ingest: bool = False) -> RAGStore:
    global _rag_store
    if _rag_store is None:
        _rag_store = RAGStore(knowledge_dir, persist_dir)
        if re_ingest or _rag_store.collection.count() == 0:
            _rag_store.ingest_all()
    return _rag_store
```

### Task 4: Tích hợp RAG vào chatbot pipeline

- [ ] **Step 4.1: Init RAG ở lifespan**

Sửa `app/main.py`, thêm trong `lifespan()`:

```python
from pathlib import Path
from app.infrastructure.rag.rag_store import init_rag_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting chatbot...")

    # Init RAG
    kb_dir = Path("/app/knowledge")  # mount trong docker-compose
    persist_dir = Path("/app/chroma_db")
    try:
        init_rag_store(kb_dir, persist_dir)
    except Exception as e:
        logger.warning("RAG init failed: %s — chatbot runs without RAG", e)

    yield
    logger.info("Shutting down...")
```

- [ ] **Step 4.2: Thêm FAQ intent**

Sửa `app/domain/value_objects/intent.py`, thêm class `Intent.FAQ`:

```python
class Intent(str, Enum):
    # ... existing intents
    FAQ = "faq"

    @property
    def required_entities(self) -> list[str]:
        mapping = {
            # ...existing mapping
            "faq": [],  # FAQ không cần entity
        }
        return mapping.get(self.value, [])
```

Update intent classification prompt (`intent_service.py`) thêm ví dụ:
- "Chính sách hủy booking?" → faq
- "Xe container có được vào bãi không?" → faq
- "Giờ mở cửa Vincom?" → faq
- "Làm sao đăng ký tài khoản?" → faq

- [ ] **Step 4.3: Add RAG action handler**

Sửa `app/application/services/action_service.py`, thêm:

```python
async def _handle_faq(self, user_id: str, entities: dict, message: str) -> dict:
    """FAQ action — retrieve docs + LLM answer với context."""
    from app.infrastructure.rag.rag_store import get_rag_store

    rag = get_rag_store()
    if not rag:
        return {
            "status": "error",
            "error": "Tôi chưa có đủ thông tin về câu hỏi đó. Vui lòng liên hệ hotline.",
        }

    docs = rag.retrieve(message, top_k=3)
    if not docs:
        return {
            "status": "no_match",
            "message": "Tôi chưa tìm thấy thông tin phù hợp. Bạn mô tả rõ hơn được không?",
        }

    # Build context for LLM
    context_blocks = []
    for i, doc in enumerate(docs, 1):
        context_blocks.append(
            f"[Nguồn {i}: {doc.metadata['source']}]\n{doc.content}"
        )
    context = "\n\n".join(context_blocks)

    system_prompt = (
        "Bạn là trợ lý ParkSmart. Trả lời câu hỏi user CHỈ dựa vào "
        "context dưới đây. Nếu không có thông tin, nói thành thật rằng bạn "
        "chưa biết. Trích dẫn nguồn [Nguồn N] khi trả lời."
    )
    user_prompt = f"Context:\n{context}\n\nCâu hỏi user: {message}\n\nTrả lời ngắn gọn:"

    if not self.llm_client:
        return {
            "status": "ok",
            "answer": docs[0].content,  # fallback raw chunk
            "sources": [d.metadata["source"] for d in docs],
        }

    answer = await self.llm_client.generate(system_prompt, user_prompt)
    return {
        "status": "ok",
        "answer": answer,
        "sources": [d.metadata["source"] for d in docs],
        "num_docs_retrieved": len(docs),
    }
```

Đăng ký handler vào dispatch map:
```python
Intent.FAQ: self._handle_faq,
```

Khi call `self._handle_faq`, cần pass `message` — update `ActionService.dispatch` signature:
```python
async def dispatch(self, intent: Intent, entities: dict, user_id: str, message: str = "") -> dict:
    ...
    if intent == Intent.FAQ:
        return await self._handle_faq(user_id, entities, message)
    # ...
```

- [ ] **Step 4.4: Update response formatter cho FAQ**

`app/application/services/response_formatters.py`, thêm branch:

```python
def format_faq(entities: dict, result: dict) -> str:
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    if not answer:
        return result.get("message", "Xin lỗi, tôi chưa có thông tin đó.")
    # Answer đã có citation từ LLM; optionally append source list
    return answer
```

Đăng ký trong dispatch formatter:
```python
if intent == Intent.FAQ:
    return format_faq(entities, result)
```

### Task 5: Mount knowledge vào Docker

- [ ] **Step 5.1: Update docker-compose.yml**

Sửa `backend-microservices/docker-compose.yml` section `chatbot-service-fastapi`:

```yaml
chatbot-service-fastapi:
  build: ./chatbot-service-fastapi
  # ...existing config
  volumes:
    - ../docs/chatbot-knowledge:/app/knowledge:ro
    - chatbot-chroma-data:/app/chroma_db

volumes:
  chatbot-chroma-data:
```

Note: Chroma cần mount volume để persist embeddings (tránh re-ingest mỗi restart).

- [ ] **Step 5.2: Rebuild + restart**

```bash
cd backend-microservices
docker compose up -d --build chatbot-service-fastapi
```

- [ ] **Step 5.3: Verify RAG loaded**

```bash
docker logs chatbot-service-fastapi 2>&1 | grep -i "RAG\|ingest\|embedding"
```

Expected: log "Ingested N chunks from M files" + "RAG store ready — N docs"

### Task 6: E2E test RAG

- [ ] **Step 6.1: Test FAQ query**

```bash
docker exec gateway-service-go wget -qO- --timeout=30 \
  --header="X-Gateway-Secret: gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE" \
  --header="X-User-ID: 08fc117f-5a57-48a0-ac99-5b2c44e6ae71" \
  --header="X-User-Email: testdriver@parksmart.com" \
  --header="Content-Type: application/json" \
  --post-data='{"message":"Chính sách hủy booking có phí không?"}' \
  http://chatbot-service-fastapi:8008/chatbot/chat/ 2>&1 | python -c "
import json,sys
d=json.load(sys.stdin)
print(f'Intent: {d.get(\"intent\")}')
print(f'Response: {d.get(\"response\",\"\")[:500]}')
"
```

Expected: Intent = `faq`, response chứa "Hủy trước 30 phút miễn phí, sau → phạt 10%..." với citation.

- [ ] **Step 6.2: Test multiple FAQ queries**

```bash
for q in "Giờ mở cửa bãi Vincom" "Xe container có được không" "Làm sao đăng ký tài khoản" "Phí phạt hủy booking"; do
  echo "=== Q: $q ==="
  docker exec gateway-service-go wget -qO- --timeout=30 \
    --header="X-Gateway-Secret: gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE" \
    --header="X-User-ID: 08fc117f-5a57-48a0-ac99-5b2c44e6ae71" \
    --header="X-User-Email: testdriver@parksmart.com" \
    --header="Content-Type: application/json" \
    --post-data="{\"message\":\"$q\"}" \
    http://chatbot-service-fastapi:8008/chatbot/chat/ 2>&1 | python -c "
import json,sys
d=json.load(sys.stdin)
print(f'  Intent: {d.get(\"intent\")} Conf: {d.get(\"confidence\",0):.2f}')
print(f'  Response (first 200 chars): {d.get(\"response\",\"\")[:200]}')"
done
```

Acceptance:
- ≥ 80% câu FAQ được classify intent=`faq` (thay vì unknown)
- Response có thông tin cụ thể (không phải "tôi chưa hiểu")
- Nếu câu không có trong knowledge base → bot thành thật "chưa biết"

### Task 7: Commit + document

- [ ] **Step 7.1: Commit code**

```bash
cd C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main
git add backend-microservices/chatbot-service-fastapi/app/infrastructure/rag/
git add backend-microservices/chatbot-service-fastapi/app/domain/value_objects/intent.py
git add backend-microservices/chatbot-service-fastapi/app/application/services/action_service.py
git add backend-microservices/chatbot-service-fastapi/app/application/services/response_formatters.py
git add backend-microservices/chatbot-service-fastapi/app/main.py
git add backend-microservices/chatbot-service-fastapi/requirements.txt
git add backend-microservices/docker-compose.yml
git commit -m "feat(chatbot): RAG integration với Chroma + multilingual embeddings"
```

- [ ] **Step 7.2: Commit knowledge base**

```bash
git add docs/chatbot-knowledge/
git commit -m "docs(chatbot): knowledge base FAQ + policies + lot info"
```

## Acceptance criteria

Chatbot RAG được coi là DONE khi:

- [ ] ChromaDB persist + Chroma container không re-embed mỗi restart
- [ ] ≥ 15 markdown files ingested thành chunks
- [ ] ≥ 80% câu FAQ được classify intent=faq
- [ ] Response có citation `[Nguồn: policies/cancellation-policy.md]` hoặc tương đương
- [ ] Câu ngoài knowledge → bot trả lời "chưa biết" thay vì bịa

## Performance expectation

- RAG init: 15-30s tại startup (load embedder + ingest)
- Query latency added: ~150ms (embedding + search)
- Total chatbot response: 2-3s (tăng từ 1.5-2s)
