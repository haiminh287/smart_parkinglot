# Bộ prompt thực thi Banknote Retrain + Chatbot RAG

> 2 work stream độc lập. Có thể chạy song song (training banknote background, RAG foreground). Copy block trong code fence.

---

## 🟢 PROMPT A1 — START BANKNOTE RETRAIN (gửi đầu tiên cho stream A)

```
You are a senior ML engineer. A previous training attempt failed — model trained only 1 epoch (smoke test committed) and eval has only 8 classes (missing 200000). Your job: properly retrain banknote v2 model.

## Plan
docs/superpowers/plans/2026-04-22-banknote-v2-retrain-fix.md

## Context
- Dataset ready: 9 classes (train ~1800/class except 200k=457)
- Training script train_banknote_v2.py has DENOMINATIONS = 9 classes including "200000"
- Current banknote_effv2s.pth is from 1-epoch smoke test (useless)
- evaluation_results_v2.json has only 8 classes (old file from v1 era)

## Environment
- Windows 11, Git Bash shell
- GPU GTX 1650 4GB
- Repo root: C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/
- Python venv: backend-microservices/ai-service-fastapi/venv/

## Execute plan

Follow the plan file step by step:
- Task A: Verify + clean old artifacts
- Task B: Full 50-epoch training
- Task C: Eval with 9 classes
- Task D: Update inference thresholds from eval results
- Task E: Sanity test
- Task F: Deploy + commit

## Rules
1. Task B is 4-6 hour training — DO NOT run blocking in this chat. Instead:
   - Complete Task A (cleanup)
   - Output Task B command for user to run in separate terminal
   - STOP, wait for user to reply "training done, best val_loss=X, val_acc=Y"
   - Then continue Task C

2. After Task C (eval), STOP and show:
   - Verification that 9 classes are present (including "200000")
   - Precision-at-accept table
   - Your recommendation for (conf, margin) threshold
   
   Wait for user approval before Task D.

3. Task E (sanity test) must cover ALL 9 classes, especially 200000.

4. Do not commit .pth weights.

Begin with Task A.
```

---

## 🟡 PROMPT A2 — TRAINING DONE (gửi sau khi training 5h xong)

```
Training completed.

best val_loss=<điền>, best val_acc=<điền>, total epochs=<điền>

Log file: backend-microservices/ai-service-fastapi/ml/models/train_v2.log
Weights: backend-microservices/ai-service-fastapi/ml/models/banknote_effv2s.pth

Continue with Task C (eval). After eval, paste:
1. Output of verify 9 classes assertion
2. Full precision-at-accept table
3. Your recommendation for (conf, margin) — precision ≥ 99.5% + accept ≥ 85%
4. Any confusion pair > 2% (especially 200000 row)

Then wait for my approval before Task D (update thresholds).
```

---

## 🔵 PROMPT A3 — APPROVE THRESHOLD (sau khi thấy eval table)

```
Approved threshold:
ACCEPT_HIGH_CONF=<điền, e.g. 0.92>
ACCEPT_HIGH_MARGIN=<điền, e.g. 0.25>

Continue Tasks D, E, F sequentially.
After Task E sanity test, paste results per class (especially 200000).
After Task F deploy, paste the 200k API test response to verify recognition works.
```

---

## 🟢 PROMPT B1 — START CHATBOT RAG (stream B, có thể song song stream A)

```
You are a senior backend + NLP engineer. Your job: integrate RAG (Retrieval-Augmented Generation) into existing chatbot so it can answer FAQ/policy questions.

## Plan
docs/superpowers/plans/2026-04-22-chatbot-rag-integration.md

## Context
Current chatbot answers structured queries (slot availability, current parking) by calling microservice APIs. It CANNOT answer:
- Cancellation policy
- Supported vehicle types
- Parking lot opening hours
- Payment refund rules
- User registration process

Because there's no knowledge base. Goal: add Chroma vector DB + sentence-transformers embedding + new "faq" intent.

## Environment
- Windows 11, Git Bash shell
- Docker compose on localhost
- Chatbot-service-fastapi runs as Docker container (port 8008 internal, via gateway)
- Existing chatbot architecture: DDD 3-layer (domain/application/infrastructure)

## Execute plan

Follow the plan file step by step:
- Task 1: Install deps (chromadb, sentence-transformers)
- Task 2: Create 15-20 markdown docs in docs/chatbot-knowledge/
- Task 3: Create app/infrastructure/rag/rag_store.py
- Task 4: Wire into pipeline (intent, action_service, response_formatters)
- Task 5: Mount knowledge volume + rebuild container
- Task 6: E2E test 5 FAQ queries
- Task 7: Commit

## Rules
1. Task 2 is content creation. Write substantive policy docs — each file 200-500 words with sections. Do not stub.

2. Task 4 modifies existing chatbot code. Before editing:
   - Read existing code (Intent enum, action_service dispatch map, response_formatters) to understand current structure
   - Keep existing intent handling intact — only ADD faq branch
   - Do not break existing tests

3. After Task 5 (container rebuild), verify log shows "Ingested N chunks from M files" and "RAG store ready"

4. Task 6 (E2E test) — STOP and paste results:
   - For each of 5 FAQ queries, paste intent + response (first 300 chars)
   - Verify ≥ 4/5 classified as intent=faq with substantive response
   
   If < 4/5 pass → paste chatbot logs + ask for guidance.

5. Do NOT commit chatbot-chroma-data volume (gitignored).

6. Knowledge base files must be in Vietnamese (user audience is Vietnamese).

Begin with Task 1.
```

---

## 🟡 PROMPT B2 — E2E RESULT (sau khi agent xong Task 6)

Gửi nếu agent show kết quả E2E < 100% pass:

```
Test results noted. If any query is NOT classified as faq or returns "chưa hiểu":

For each failing query, paste:
1. The exact retrieved docs (call rag.retrieve(query) directly and show top-3)
2. The intent classification confidence

If retrieval returned 0 docs with good score → check if related markdown file exists + has relevant keywords.
If retrieval good but LLM answer wrong → check the prompt template in _handle_faq.
If intent != faq → update intent classification prompt with more faq examples.

Iterate until ≥ 4/5 pass. Then commit per Task 7.
```

---

## ⚫ PROMPT C — FINAL SUMMARY (sau cả A và B xong)

```
Both streams complete. Generate final report:

## Banknote v2
- Training: <N> epochs, best val_loss=<X>
- Eval: <Y>% accuracy, <Z>% precision at accept (with threshold conf=<A> margin=<B>)
- All 9 classes verified including 200000
- Live API test: <pass/fail> with sample 200k → returned <denom> conf=<C>

## Chatbot RAG
- Knowledge base: <N> markdown files, <M> chunks ingested
- E2E: <X>/5 FAQ queries classified correctly
- Example response for "Chính sách hủy booking" (full text)
- Avg latency with RAG: <T>s (vs baseline <T0>s)

## Git log
git log --oneline --since="2 days ago" -20

## Next steps recommended
- Any sprint follow-up needed?
- Any metric not meeting target?

Report should fit in 1 markdown section.
```

---

## Thứ tự gửi

```
[Stream A: Banknote retrain — takes 5h overnight]
  └─ A1 → agent cleanup + prepare training command
        ↓
  [User run training 5h in separate terminal]
        ↓
  └─ A2 → agent run eval → show precision table
        ↓
  └─ A3 → approve threshold → deploy + test

[Stream B: Chatbot RAG — runs independently, ~2-3h]
  └─ B1 → agent creates knowledge + RAG module + E2E test
        ↓
  (optional) B2 → iterate on failing queries
        ↓
  [agent commits]

[After both done]
  └─ C → combined final report
```

## Mẹo

- **Song song được:** Banknote training không share resource với chatbot → mở 2 tab agent riêng, chạy A1 và B1 cùng lúc
- **A1 + B1 cùng tab thì agent có thể chậm** vì switch context giữa 2 task — khuyến nghị tách tab
- **Training background:** Khi đang chạy Task B training, bạn tự do làm Stream B cùng lúc
- **Knowledge base tiếng Việt:** agent có thể dùng template tiếng Việt — bạn review, sửa cho đúng chính sách thật của bãi
