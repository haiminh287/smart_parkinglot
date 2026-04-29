# Prompt RESUME cho Copilot/Cursor Agent — tiếp từ Task 4

> Copy block dưới vào chat Agent. Đã adapt cho trạng thái hiện tại: Tasks 1-3 done, Task 4 dở dang.

---

```
You are a senior ML engineer resuming an in-progress implementation. Previous agent completed Tasks 1-3 and started Task 4 but didn't commit. Your job: commit Task 4, then execute Tasks 5-11 per the plan.

## Plan
`docs/superpowers/plans/2026-04-20-banknote-recognition-v2.md`

## Current state (đã verify)

### Committed tasks ✅
- **Task 1** (commit 5672c22): albumentations/sklearn/matplotlib installed
- **Task 2** (commit 316164d): 200k re-extracted → 572 frames
- **Task 3** (commit eed0f2d): dataset split 80/20, counts:
  - train: 1000=1931, 2000=1931, 5000=1916, 10000=1792, 20000=1888, 50000=1596, 100000=1880, 200000=457, 500000=1861
  - val: ~20% tương ứng
  - 200k vẫn imbalance (~1/4 các class khác) — cần WeightedRandomSampler (plan đã có)

### In-progress
- **Task 4**: `backend-microservices/ai-service-fastapi/app/ml/augmentations.py` ĐÃ TẠO (61 lines, syntax OK) nhưng **CHƯA COMMIT** (git status `??`).

### Remaining (8 tasks)
- Task 5: training script
- Task 6: training 50 epochs (~5h, LONG-RUNNING)
- Task 7: eval + confusion matrix
- Task 8: update inference (TTA + rejection)
- Task 9: update pipeline
- Task 10: deploy via env var
- Task 11: sanity test + rollback docs

## Environment
- OS: Windows 11, shell Git Bash (Unix syntax, forward slashes)
- Repo root: `C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/`
- Python venv: `backend-microservices/ai-service-fastapi/venv/`
- GPU: NVIDIA GTX 1650 4GB

## Start sequence

**Step 0 — Verify current state:**

```bash
cd C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main
git log --oneline -5
git status --short backend-microservices/ai-service-fastapi/app/ml/augmentations.py
```

Expected:
- git log: 3 commits đầu là `eed0f2d`, `316164d`, `5672c22`
- git status: `??  backend-microservices/.../augmentations.py`

Nếu mismatch → STOP và báo user.

**Step 1 — Commit Task 4:**

```bash
cd backend-microservices/ai-service-fastapi
# Smoke test augmentations first
venv/Scripts/python.exe -c "
from app.ml.augmentations import build_train_transform, build_val_transform, build_tta_transforms
import cv2, os
t = build_train_transform()
sample = 'ml/models/split/train/1000'
img = cv2.imread(os.path.join(sample, os.listdir(sample)[0]))
out = t(image=img)['image']
print(f'OK — output shape {out.shape}')
"
# Expect: OK — output shape torch.Size([3, 224, 224])

cd ../..
git add backend-microservices/ai-service-fastapi/app/ml/augmentations.py
git commit -m "feat(ai): add albumentations pipelines (train/val/tta) cho banknote v2"
```

## Rules (giữ nguyên từ session trước)

1. **Thực thi tuần tự** — 1 task tại 1 thời điểm, không skip.
2. **Smoke test trước khi train thật** — Task 5.2 set EPOCHS=1 chạy ~5 phút trước khi bung 50 epoch.
3. **Task 6 long-running (5h)** — KHÔNG chạy blocking trong session. Thay vào đó:
   - Hoàn thành Task 5 (viết script + smoke test pass)
   - Báo user: "Task 5 done. Task 6 là training 5h. Hãy chạy lệnh sau trong terminal riêng:
     ```bash
     cd backend-microservices/ai-service-fastapi
     venv/Scripts/python.exe train_banknote_v2.py 2>&1 | tee ml/models/train_v2.log
     ```
     Qua đêm xong báo tôi `train done, best val_loss=X.XX` để tôi tiếp Task 7."
   - WAIT cho user confirm rồi mới tiếp Task 7.
4. **Risk awareness**:
   - Task 8 replace inference → backup `cash_recognition_v1_backup.py` TRƯỚC (plan có lệnh).
   - Task 10 deploy → kill uvicorn cũ trước, verify `/health` sau.
5. **Mỗi task 1 commit** — đúng message trong plan. Không `git add .` / `-A`.
6. **Verify expected output** — plan ghi "Expected: ..." cho từng lệnh. Mismatch → STOP.
7. **Báo progress** mỗi khi xong task:
   ```
   ✅ Task N complete
   - Files: [...]
   - Commit: <SHA>
   - Verify: [key metric nào quan trọng]
   ▶ Task N+1 bắt đầu...
   ```

## Task 6 checkpoint (bắt buộc)

Sau Task 5 smoke test pass, trước khi chuyển Task 7:
- Paste lệnh training user cần chạy
- STOP — đợi user báo "training done"
- Khi user reply, hỏi: "val_acc cuối là bao nhiêu? best val_loss?" → log vào progress.

## Task 7 checkpoint (bắt buộc)

Sau eval:
- Paste output `Precision-at-accept` table đầy đủ cho user review
- Đề xuất threshold `(conf, margin)` đạt precision ≥99.5% + accept ≥80%
- STOP — đợi user approve threshold
- Dùng threshold user chọn cho Task 8 (`ACCEPT_HIGH_CONF` + `ACCEPT_HIGH_MARGIN`).

## Task 10 checkpoint (bắt buộc)

Sau deploy:
- Chạy curl test ở Step 10.6 — paste response
- Verify `decision=accept denom=<đúng> conf>0.90`
- Nếu fail → paste log `/tmp/ai.log` full, STOP.

## Acceptance criteria (Task 11 gate)

Báo user accept/reject deploy dựa trên:
- Val top-1 accuracy ≥ 98%
- Precision at accept ≥ 99.5%
- Accept rate 80-95%
- Inference <200ms
- Confusion matrix: no off-diagonal > 2%

Fail → rollback theo README.md (Task 11.3).

## What NOT to do

- ❌ Skip Task 4 commit (sẽ mất track, session sau có thể overwrite)
- ❌ Chạy Task 6 training trong Copilot session (timeout)
- ❌ Dùng threshold khác mà không qua Task 7 eval
- ❌ Deploy Task 10 khi Task 7 criteria không đạt
- ❌ Commit `.pth` weights file (gitignored)
- ❌ Modify plan file. Nếu thấy sai, báo user trước.

## Start now

Chạy Step 0 (verify state), report kết quả, rồi Step 1 (commit Task 4), rồi Task 5.
```

---

## Hướng dẫn dùng

1. **Copy block trong code fence trên** (không lấy phần hướng dẫn này)
2. Paste vào Copilot Chat / Cursor Agent
3. Click Run / Send

### Các điểm cần bạn interact:

- **Sau Task 5:** Agent sẽ đưa lệnh training. Bạn chạy trong terminal riêng, ~5h (qua đêm).
- **Sáng hôm sau:** Paste `"Training done. best val_loss=0.XX, val_acc=0.XX"` → agent tiếp Task 7.
- **Sau Task 7:** Agent đưa table precision-at-accept. Bạn chọn threshold (thường `(0.92, 0.25)` hoặc `(0.95, 0.30)`).
- **Sau Task 10:** Nếu curl test pass → OK tiếp Task 11. Nếu fail → paste log `/tmp/ai.log`.

### Nếu agent bị dừng giữa chừng lần nữa:

Quay lại dùng file prompt này, edit section "Current state" để update committed tasks + running state. Rule "Start sequence" sẽ tự adapt.
