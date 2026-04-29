# Prompt dùng cho GitHub Copilot / Cursor Agent thực thi Plan

> Copy block dưới vào chat của Copilot/Cursor (dùng Agent mode). Thay `{{YOUR_PATH}}` bằng đường dẫn thực tế nếu khác.

---

```
You are a senior ML engineer executing a pre-written implementation plan. Your job is to implement it precisely, test after each step, and commit often.

## Your task
Thực thi toàn bộ plan tại:
`docs/superpowers/plans/2026-04-20-banknote-recognition-v2.md`

Plan này nâng cấp bộ nhận diện mệnh giá tiền Việt Nam từ MobileNetV3 (89% accuracy) lên EfficientNetV2-S (≥99% precision với rejection logic). Có 11 task tuần tự, mỗi task có code copy-paste ready, lệnh chạy, và acceptance criteria.

## Environment
- OS: Windows 11, shell Git Bash (syntax Unix: `ls`, `cp`, forward slashes)
- Repo root: `C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/`
- Python venv: `backend-microservices/ai-service-fastapi/venv/` (PyTorch 1.13 + CUDA 11.6)
- GPU: NVIDIA GTX 1650 4GB VRAM
- Spec (context): `docs/superpowers/specs/2026-04-20-banknote-recognition-v2-design.md`

## Rules

1. **Đọc toàn bộ plan trước khi bắt đầu.** Hiểu tổng quan 11 task, phụ thuộc giữa các task.

2. **Prerequisites check đầu tiên.** Section "Prerequisites" trong plan có 5 lệnh verify — chạy tất cả. Nếu bất kỳ check nào fail, STOP và báo user, đừng cố workaround.

3. **Thực thi tuần tự 1 task tại 1 thời điểm.** Không skip, không song song. Trong mỗi task, làm từng step (đã đánh số `Step N.M`) theo đúng thứ tự.

4. **Sau mỗi step, verify expected output.** Plan ghi rõ "Expected: ..." cho từng lệnh. So khớp chính xác trước khi qua step tiếp. Nếu output khác expected, báo user và đợi hướng dẫn — đừng đoán.

5. **Commit cuối mỗi task** với đúng commit message đã cho trong plan. Không commit giữa task.

6. **TDD mindset:** Task 5 có smoke test 1 epoch trước khi train thật 50 epoch. Task 8-9 có smoke test inference trước khi wire vào pipeline. Luôn chạy smoke test và verify trước.

7. **Task 6 là long-running (~5h).** Không chạy trong Copilot session. Thay vào đó:
   - Chuẩn bị lệnh + hướng dẫn monitor
   - Báo user: "Task 6 là training 5h. Hãy chạy lệnh sau trong terminal riêng, monitor bằng `tail -f`, xong báo tôi để tôi tiếp tục Task 7."
   - Không block, chuyển sang chờ user.

8. **Risk awareness với live system:**
   - Task 1 (install deps) → có thể break venv. Nếu pip install fail, thử lại với version tolerance (`>=1.3,<1.4` thay vì `==1.3.1`).
   - Task 8 (replace inference code) → live AI service đang dùng. Backup `cash_recognition_v1_backup.py` TRƯỚC khi replace (plan đã có lệnh này).
   - Task 10 (swap model) → kill uvicorn cũ trước khi start mới, tránh port 8009 conflict.

9. **Báo progress rõ ràng** mỗi khi xong 1 task:
   ```
   ✅ Task N complete
   - [danh sách file đã tạo/sửa]
   - [commit SHA]
   - [kết quả verify nào quan trọng]
   
   ▶ Bắt đầu Task N+1...
   ```

10. **Nếu bị stuck** (lệnh fail không khớp expected, tests fail, logic ambiguous):
    - KHÔNG đoán workaround
    - Paste lại output thực tế + lỗi + step đang làm
    - Đề xuất 2-3 hướng fix
    - Đợi user chọn

11. **Troubleshooting section trong plan** có hướng dẫn cho 5 loại lỗi (OOM, NaN loss, slow training, confusion pair, 500 API). Apply trước khi hỏi user.

12. **Acceptance criteria ở Task 11** (accuracy ≥98%, precision at accept ≥99.5%, accept rate 80-95%, latency <200ms) là bắt buộc. Nếu không đạt, rollback theo README.md trong plan — đừng ép deploy.

## Priorities
1. **Correctness** > speed. Chạy chậm mà đúng còn hơn fast-forward sai.
2. **Không break live system.** AI service đang chạy trên port 8009 phục vụ ESP32 + Unity. Task 10 (deploy) phải graceful: kill → start → verify health trước khi claim done.
3. **Commit frequently** theo plan. Mỗi task 1 commit. Nếu crash giữa task, có thể resume từ task trước.

## Output format
- Đầu mỗi session, ghi: "Resuming from Task X. Completed: [list]. Next: [task]."
- Cuối mỗi task, ghi progress như Rule #9.
- Khi all tasks done, ghi summary với metrics thực tế từ eval (accuracy, precision, latency).

## What NOT to do
- ❌ Đừng sửa plan. Plan đã được design + review. Nếu thấy vấn đề, báo user trước khi modify.
- ❌ Đừng skip smoke test (Task 5.2, 8.3, 9.3). Smoke test catches bug sớm, tiết kiệm 5h training sai.
- ❌ Đừng commit weights `.pth` files (gitignored). Chỉ commit code + config + history JSON.
- ❌ Đừng dùng `git add .` hoặc `git add -A`. Plan ghi rõ file nào add mỗi commit.
- ❌ Đừng touch các file khác ngoài plan (không refactor random, không format toàn bộ codebase).

## Start now
Bắt đầu bằng lệnh đọc plan:

```
cat docs/superpowers/plans/2026-04-20-banknote-recognition-v2.md
```

Rồi chạy Prerequisites check, rồi báo user kết quả trước khi bắt đầu Task 1.
```

---

## Hướng dẫn dùng prompt này

### Với GitHub Copilot Chat (VS Code Agent mode)

1. Mở VS Code trong `C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/`
2. Copilot Chat → chọn **Agent** mode (không phải Ask)
3. Paste nguyên block prompt trên
4. Copilot sẽ đọc plan + chạy Prerequisites

### Với Cursor AI Agent

1. Mở Cursor ở root repo
2. `Cmd/Ctrl + L` mở Agent
3. Paste prompt
4. Click **Run**

### Với Claude / ChatGPT (manual mode)

1. Paste prompt vào chat
2. Sau mỗi response agent, tự chạy lệnh trong terminal rồi paste output lại
3. Agent sẽ verify + qua step tiếp

### Tips

- **Task 6 (training 5h):** Agent sẽ dừng và yêu cầu bạn chạy terminal riêng. Copy lệnh từ plan, mở PowerShell/Git Bash khác, chạy qua đêm. Sáng dậy báo agent "Task 6 done, val_acc=0.98" để nó tiếp tục.
- **Nếu agent stuck ở Task 2** (re-extract frames chỉ ra 200 frame): plan có hướng dẫn giảm `frame_step` trong extract script — agent nên tự apply.
- **Nếu agent không có permission chạy Docker/kill process:** chạy lệnh đó thủ công, paste output lại.

### Checkpoint questions bạn nên hỏi agent giữa chừng

- Sau Task 5: *"Smoke test 1 epoch val_acc là bao nhiêu? Có lỗi nào không?"*
- Sau Task 7: *"Confusion matrix có cặp class nào confuse > 2%? Eval precision-at-accept ở các threshold là gì?"* → quyết định threshold cho Task 8.
- Sau Task 10: *"curl end-to-end test trả gì? AI service log có 'Loaded banknote v2'?"*
- Sau Task 11: *"Final metrics: accuracy = ?, precision at accept = ?, inference time = ? Pass acceptance criteria không?"*

Nếu câu trả lời agent mâu thuẫn/lơ mơ → quay lại step trước verify.
