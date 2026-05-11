# Bộ prompt tuần tự cho AI Agent — Banknote v2

> **Cách dùng:** Gửi lần lượt 7 prompt dưới đây khi agent tới checkpoint tương ứng. Copy cả khối trong code fence (không lấy tiêu đề). Không skip, không đảo thứ tự.

---

## 🟢 Prompt #1 — KHỞI ĐỘNG / RESUME (gửi đầu tiên)

> Gửi khi mở chat agent mới. Agent sẽ verify state → commit Task 4 → làm Task 5.

```
You are a senior ML engineer resuming an in-progress implementation plan. Previous agent completed Tasks 1-3 and started Task 4 but didn't commit. Your job: commit Task 4, then execute Tasks 5-11 per the plan.

## Plan file (đọc đầu tiên)
docs/superpowers/plans/2026-04-20-banknote-recognition-v2.md

## Current state (already verified)

Committed:
- Task 1 (5672c22): albumentations/sklearn/matplotlib installed
- Task 2 (316164d): 200k re-extracted → 572 frames
- Task 3 (eed0f2d): dataset split 80/20 — 200k has 457 train / 115 val (imbalanced — handled by WeightedRandomSampler in plan)

Uncommitted:
- Task 4: backend-microservices/ai-service-fastapi/app/ml/augmentations.py CREATED but NOT COMMITTED (git status shows `??`)

## Environment
- Windows 11, Git Bash shell (Unix syntax, forward slashes)
- Repo root: C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/
- Python venv: backend-microservices/ai-service-fastapi/venv/
- GPU: NVIDIA GTX 1650 4GB

## Rules
1. Execute tasks sequentially, one at a time. No skip.
2. Each task = 1 commit. Use exact commit messages from the plan. No `git add .` or `-A`.
3. Verify "Expected: ..." output from plan — mismatch = STOP and report.
4. Task 6 (training 5h) is LONG-RUNNING — do NOT run blocking in this chat. Just prepare the command for the user to run in terminal, then STOP and wait.
5. Task 7 precision-at-accept table — STOP, paste table, wait for user to choose threshold before Task 8.
6. Task 10 deploy — verify curl response before claim done. If fail, paste full log.
7. Do NOT modify the plan file. Report issues to user first.
8. Do NOT commit `.pth` weights (gitignored).

## Start sequence

**Step 0 — Verify state:**
```bash
cd C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main
git log --oneline -5
git status --short backend-microservices/ai-service-fastapi/app/ml/augmentations.py
```

Expected: 3 recent commits `eed0f2d`, `316164d`, `5672c22` + `??  .../augmentations.py`

**Step 1 — Smoke test + commit Task 4:**
```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe -c "
from app.ml.augmentations import build_train_transform
import cv2, os
t = build_train_transform()
sample = 'ml/models/split/train/1000'
img = cv2.imread(os.path.join(sample, sorted(os.listdir(sample))[0]))
out = t(image=img)['image']
print(f'OK - output shape {out.shape}')
"
cd ../..
git add backend-microservices/ai-service-fastapi/app/ml/augmentations.py
git commit -m "feat(ai): add albumentations pipelines (train/val/tta) cho banknote v2"
```

**Step 2 — Task 5 (viết training script):** Follow plan Task 5 Steps 5.1 → 5.4.
- Step 5.2 smoke test: set EPOCHS=1, run 1 epoch, verify val_acc > 0.30, file banknote_effv2s.pth created (~80MB).
- Step 5.3: restore EPOCHS=50.

**Step 3 — Stop before Task 6:** After Task 5 commit, STOP and output exactly this message:
```
✅ Task 5 done. Smoke test passed: val_acc=<X.XX> after 1 epoch, time <Y>s.

⚠️ Task 6 is 5-hour training — cannot run in this chat session.

Please open a separate terminal and run:

cd C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/backend-microservices/ai-service-fastapi
venv/Scripts/python.exe train_banknote_v2.py 2>&1 | tee ml/models/train_v2.log

Monitor in another terminal:
tail -f backend-microservices/ai-service-fastapi/ml/models/train_v2.log | grep Epoch

When training finishes (early stop or epoch 50), reply with:
"Training done. best val_loss=X.XX, last val_acc=Y.YY"

Then I'll resume from Task 7.
```

Wait for user. Do NOT proceed until user replies with training results.

Begin now with Step 0.
```

---

## 🟡 Prompt #2 — SAU KHI TRAINING XONG (user gửi sau khi train 5h)

> Gửi khi training script chạy xong. Điền số liệu thực tế vào.

```
Training done. Best val_loss=<điền số>, last val_acc=<điền số>, total epochs=<điền số>.

Log file: backend-microservices/ai-service-fastapi/ml/models/train_v2.log
Weights: backend-microservices/ai-service-fastapi/ml/models/banknote_effv2s.pth (verify size ~80MB)

Resume plan at Task 7 (eval + confusion matrix). Execute Task 7 Steps 7.1 → 7.4 per plan.

After Step 7.2 (run eval_banknote_v2.py), STOP and output:
1. Full eval output including the Precision-at-accept table
2. Visual inspection result of confusion_matrix_v2.png — any off-diagonal > 2%?
3. Your recommendation for (conf, margin) threshold that gives precision ≥ 99.5% AND accept_rate ≥ 80%

Then wait for me to approve threshold before Task 8.
```

---

## 🔵 Prompt #3 — CHỌN THRESHOLD (sau khi agent đưa eval table)

> Gửi sau khi agent show precision-at-accept table. Điền threshold bạn chọn.

```
Approved threshold: ACCEPT_HIGH_CONF=<điền, e.g. 0.92>, ACCEPT_HIGH_MARGIN=<điền, e.g. 0.25>.

Reason: <1 câu giải thích why, e.g. "precision 99.7% + accept 87% là tradeoff tốt nhất">

Keep ACCEPT_LOW_CONF=0.80, ACCEPT_LOW_MARGIN=0.40 as secondary rule (per plan).

Continue to Task 8 (update inference). Before replacing cash_recognition.py, first backup to cash_recognition_v1_backup.py as plan specifies.

After Task 8 smoke test (4 samples), paste the results with ✓/✗ marks per class.

Then continue Task 9 (pipeline wire-up). After Task 9 smoke test, paste 3-sample results.

Commit each task separately with messages from plan.
```

---

## 🟣 Prompt #4 — NẾU TASK 8 HOẶC 9 GẶP LỖI SIGNATURE MISMATCH

> Chỉ gửi nếu agent báo PipelineResult/PipelineDecision field names khác plan.

```
Pause Task 9. Show me:
1. Full content of class PipelineResult in backend-microservices/ai-service-fastapi/app/engine/pipeline.py
2. Full content of enum PipelineDecision
3. ClassificationMethod enum
4. The exact line(s) where cash_inference.predict() is called in pipeline.py

I'll give you the correct field mapping. Do NOT guess — wait for my reply.
```

---

## 🟠 Prompt #5 — DEPLOY TASK 10

> Gửi sau khi agent hoàn thành Task 9 commit.

```
Continue Task 10 (deploy via env).

Important safety checks before kill uvicorn:
1. First check if uvicorn is currently running:
   curl -sS -m 2 http://localhost:8009/health/ 2>&1 | head -2

2. If service is running, note PIDs first:
   powershell -Command "Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*uvicorn*app.main*' } | Select-Object ProcessId, CommandLine | Format-List"

3. Kill old + start new (Task 10 Step 10.4).

4. Wait 30 seconds for model pre-warm (AI service lifespan loads YOLO + plate + banknote).

5. Verify health:
   curl -sS http://localhost:8009/health/

6. Check log confirmation (Task 10 Step 10.5):
   grep -i "Loaded banknote v2\|EfficientNetV2-S" /tmp/ai.log

7. Run end-to-end test (Task 10 Step 10.6) — paste the full response.

STOP after Step 10.6. If response does NOT show `decision=accept denom=<correct> conf>0.90`, paste:
- Full /tmp/ai.log tail 50
- Content of .env BANKNOTE_MODEL_PATH line
- Content of detection.py _get_cash_inference function

Then wait for my diagnosis.

If response looks correct, commit per Step 10.7 and continue Task 11.
```

---

## 🔴 Prompt #6 — TASK 11 SANITY TEST + FINAL ACCEPTANCE

> Gửi sau khi Task 10 deploy thành công (đã thấy curl response đúng).

```
Execute Task 11 Steps 11.1 → 11.4.

For Step 11.1 (30-sample random test), paste the full output with the 3 key metrics:
- Total samples
- Accept rate %
- Precision at accept %

For Step 11.2 (benchmark), paste mean inference time.

Then make accept/reject decision per these criteria:
- Val top-1 accuracy ≥ 98% (from Task 7 eval)
- Precision at accept ≥ 99.5% (from Task 11.1)
- Accept rate 80-95% (from Task 11.1)
- Inference time < 200ms (from Task 11.2)
- No confusion pair > 2% (from Task 7 confusion matrix)

If ALL criteria pass → report:
"✅ ALL ACCEPTANCE CRITERIA PASSED. Ready for production use."
Then commit Task 11 per Step 11.4.

If ANY criterion fails → report:
"❌ FAIL on <criterion name>: got <actual>, need <target>. Rollback recommended."
Then follow rollback procedure in Task 11.3 README.md. Paste rollback steps and wait for user approval before executing.
```

---

## ⚫ Prompt #7 — FINAL WRAP-UP

> Gửi sau khi tất cả tasks done.

```
All tasks complete. Final wrap-up:

1. Show git log of all v2 commits:
   git log --oneline --grep="banknote v2\|banknote\|EfficientNet" -20

2. Summary report — fill in actual numbers from training + eval + sanity test:
   ```
   # Banknote v2 Deployment Report

   - Model: EfficientNetV2-S
   - Training: <N> epochs, best val_loss=<X>, val_acc=<Y>%
   - Dataset: <total> train, <total> val, 9 classes
   - Acceptance thresholds: conf ≥ <A>, margin ≥ <B>

   ## Metrics
   - Val top-1 accuracy: <X>%
   - Precision at accept: <Y>%
   - Accept rate: <Z>%
   - Inference latency (TTA ×5): <T>ms
   - Confusion matrix: worst off-diagonal <W>%

   ## Files
   - Training script: train_banknote_v2.py
   - Eval script: eval_banknote_v2.py
   - Weights: ml/models/banknote_effv2s.pth
   - Inference: app/ml/inference/cash_recognition.py
   - Augmentations: app/ml/augmentations.py
   - Rollback: ml/models/README.md
   ```

3. Show deploy verification:
   - curl http://localhost:8009/health/ (healthy?)
   - curl test banknote endpoint with 1 sample (still returns correct?)

4. DO NOT push to remote. Stop here and let user review all commits before pushing.
```

---

## Tóm tắt thứ tự gửi

```
[Agent chưa có context]
  └─ Prompt #1 (khởi động)
        ├─ Agent commit Task 4, làm Task 5, smoke test OK
        └─ Agent STOP, yêu cầu user chạy training
              ↓
[User chạy training 5h trong terminal riêng]
              ↓
  └─ Prompt #2 (báo training xong, điền val_loss/val_acc)
        ├─ Agent làm Task 7 (eval)
        └─ Agent STOP, show precision-at-accept table
              ↓
  └─ Prompt #3 (chọn threshold)
        ├─ Agent làm Task 8 (inference)
        ├─ Agent làm Task 9 (pipeline)
        └─ [Nếu Task 8/9 lỗi signature → Prompt #4]
              ↓
  └─ Prompt #5 (deploy Task 10)
        ├─ Agent kill + start uvicorn
        ├─ Agent verify curl + log
        └─ STOP nếu fail, show log
              ↓
  └─ Prompt #6 (acceptance + Task 11)
        ├─ 30-sample test
        ├─ Benchmark
        └─ Accept/reject decision
              ↓
  └─ Prompt #7 (final report)
        └─ Summary + deploy verification
```

## Lưu ý

- **Mỗi prompt đều tự chứa đủ context.** Nếu chat session bị mất (browser crash), mở session mới gửi lại đúng prompt ở checkpoint hiện tại.
- **Giữ `train_v2.log`** — file này là bằng chứng training cho KLTN report.
- **Giữ `confusion_matrix_v2.png`** — đưa vào slide presentation được.
- **Không push lên remote** cho tới khi bạn review xong tất cả commits.
