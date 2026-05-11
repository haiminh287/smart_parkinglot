# Banknote v2 — Retrain Fix Plan

> **Issue phát hiện:** Training chỉ 1 epoch (early stop quá sớm), eval không có class 200k, val_acc=98.22% (chưa đạt target ≥99%).

**Goal:** Retrain đúng 50 epoch, test đủ 9 class, đạt accuracy ≥ 99% + precision at accept ≥ 99.5%.

## Root cause analysis

1. `training_history_v2.json` chỉ 1 epoch → training dừng sớm
2. `evaluation_results_v2.json` chỉ 8 class → eval script chạy khi file train v1 chưa có 200k
3. `color_accuracy: 13.25%` → color classifier tầng 1 fail, model deep đang cover mọi thứ

## Tasks

### Task A: Clean old artifacts + verify setup

- [ ] **Step A.1: Verify script correct**
```bash
cd C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/backend-microservices/ai-service-fastapi
grep "DENOMINATIONS" train_banknote_v2.py | head -3
# Expected: 9 classes including 200000
```

- [ ] **Step A.2: Check early-stop config**
```bash
grep "EARLY_STOP_PATIENCE\|EPOCHS" train_banknote_v2.py | head -3
# Expected: EPOCHS = 50, EARLY_STOP_PATIENCE = 8
```

Nếu `EPOCHS < 50` hoặc `EARLY_STOP_PATIENCE` không set → fix về 50/8.

- [ ] **Step A.3: Delete old weights + history**
```bash
rm -f ml/models/banknote_effv2s.pth
rm -f ml/models/training_history_v2.json
rm -f ml/models/train_v2.log
rm -f ml/models/evaluation_results_v2.json
rm -f ml/models/confusion_matrix_v2.png
```

### Task B: Full retrain 50 epoch

- [ ] **Step B.1: Train với real 50 epoch**
```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe train_banknote_v2.py 2>&1 | tee ml/models/train_v2.log
```

Expected: ~4-6 giờ GTX 1650, sẽ có "Saved best model" nhiều lần, cuối cùng hoàn thành 50 epoch hoặc early stop sau epoch 20+.

- [ ] **Step B.2: Monitor**
```bash
tail -f ml/models/train_v2.log | grep -E "Epoch|Saved|Early"
```

Healthy signal:
- Epoch 1: val_acc > 0.3
- Epoch 10: val_acc > 0.9
- Epoch 20+: val_acc > 0.97
- Best val_loss cuối < 0.10

- [ ] **Step B.3: Verify final**
```bash
grep "best val_loss" ml/models/train_v2.log | tail -1
ls -la ml/models/banknote_effv2s.pth
```

### Task C: Eval đủ 9 class với stratified test set

- [ ] **Step C.1: Run eval script**
```bash
venv/Scripts/python.exe eval_banknote_v2.py 2>&1 | tee ml/models/eval_v2.log
```

- [ ] **Step C.2: Verify 9 class**
```bash
cat ml/models/evaluation_results_v2.json | python -c "
import json,sys
d=json.load(sys.stdin)
print('classes:', d['class_order'])
assert len(d['class_order']) == 9, 'MUST have 9 classes'
assert '200000' in d['class_order'], 'MUST include 200000'
print('Overall:', d['overall_accuracy']*100, '%')
print('Per class f1:')
for i, item in enumerate(d['per_class']):
    if isinstance(item, dict):
        print(' ', d['class_order'][i], 'p=', item.get('precision',0)*100, '% r=', item.get('recall',0)*100)
"
```

Expected: 9 classes listed, 200000 present, overall ≥ 98%.

- [ ] **Step C.3: Review confusion matrix**

Mở `ml/models/confusion_matrix_v2.png`. Verify:
- Diagonal đậm
- 200k row không có cell > 2% off-diagonal
- Không có pair class nào confuse > 2%

### Task D: Update inference threshold theo eval

- [ ] **Step D.1: Đọc precision-at-accept table từ eval log**

```bash
grep -A 10 "Precision-at-accept" ml/models/eval_v2.log
```

Chọn `(conf, margin)` đạt precision ≥ 99.5% và accept_rate ≥ 85%.

- [ ] **Step D.2: Update threshold trong inference**

Edit `app/ml/inference/cash_recognition.py`:
```python
ACCEPT_HIGH_CONF = <chosen_conf>   # ví dụ 0.92
ACCEPT_HIGH_MARGIN = <chosen_margin>  # ví dụ 0.25
```

### Task E: Integration test 30 samples toàn 9 class

- [ ] **Step E.1: Sanity test**
```bash
venv/Scripts/python.exe -c "
from app.ml.inference.cash_recognition import CashRecognitionInference
import cv2, os, random, collections
random.seed(42)
inf = CashRecognitionInference('ml/models/banknote_effv2s.pth')
val_dir = 'ml/models/split/val'
stats = collections.defaultdict(lambda: {'total': 0, 'accept': 0, 'correct': 0})
for cls in sorted(os.listdir(val_dir)):
    files = os.listdir(os.path.join(val_dir, cls))
    for f in random.sample(files, min(5, len(files))):
        img = cv2.imread(os.path.join(val_dir, cls, f))
        r = inf.predict(img)
        stats[cls]['total'] += 1
        if r.decision == 'accept':
            stats[cls]['accept'] += 1
            if r.denomination == cls:
                stats[cls]['correct'] += 1
total = sum(s['total'] for s in stats.values())
accept = sum(s['accept'] for s in stats.values())
correct = sum(s['correct'] for s in stats.values())
print(f'Overall: {total} tests, accept rate {accept/total*100:.1f}%, precision at accept {correct/max(accept,1)*100:.2f}%')
print('Per class:')
for cls, s in sorted(stats.items()):
    print(f'  {cls}: {s[\"total\"]} tested, {s[\"accept\"]} accepted, {s[\"correct\"]} correct')
"
```

**Success criteria:**
- Overall accept rate 80-95%
- Overall precision at accept ≥ 99%
- Class 200000: accept ≥ 3/5, correct = accept (100% khi accept)

### Task F: Deploy + verify live

- [ ] **Step F.1: Restart AI service**
```bash
powershell -Command "Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*uvicorn*app.main*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }"
sleep 3
cd backend-microservices/ai-service-fastapi
set -a && source ../.env && set +a
venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8009 > /tmp/ai.log 2>&1 &
sleep 30
curl -sS http://localhost:8009/health/
```

- [ ] **Step F.2: Test API banknote với 200k**
```bash
SAMPLE=$(ls ml/models/split/val/200000/*.jpg | head -1)
curl -sS -m 15 -H "X-Gateway-Secret: gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE" -H "X-User-ID: system" \
  -F "image=@$SAMPLE" \
  "http://localhost:8009/ai/detect/banknote/?mode=full" | python -c "
import json,sys
d=json.load(sys.stdin)
print(f'200k test → decision={d[\"decision\"]} denom={d[\"denomination\"]} conf={d[\"confidence\"]:.3f}')
assert d['denomination'] == '200000' and d['decision'] == 'accept', f'FAIL'
print('✓ 200k recognized correctly')
"
```

- [ ] **Step F.3: Commit training artifacts**
```bash
cd C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main
git add backend-microservices/ai-service-fastapi/ml/models/training_history_v2.json
git add backend-microservices/ai-service-fastapi/ml/models/evaluation_results_v2.json
git add backend-microservices/ai-service-fastapi/ml/models/confusion_matrix_v2.png
git add backend-microservices/ai-service-fastapi/ml/models/train_v2.log
git add backend-microservices/ai-service-fastapi/ml/models/eval_v2.log
git add backend-microservices/ai-service-fastapi/app/ml/inference/cash_recognition.py
git commit -m "eval(ai): banknote v2 full 50-epoch retrain — 9 classes, val_acc=<X>%, precision at accept=<Y>%"
```

(Weights `.pth` gitignored, không commit)

## Acceptance criteria

Banknote v2 chỉ được coi là DONE khi:

- [ ] Training log có ≥ 20 epochs (không phải 1)
- [ ] `evaluation_results_v2.json` có 9 classes bao gồm `200000`
- [ ] Overall val accuracy ≥ 98%
- [ ] Per-class precision + recall cho 200000 ≥ 95%
- [ ] Precision at accept ≥ 99%
- [ ] Confusion matrix no off-diagonal > 2%
- [ ] API test thực 200k sample → accept + đúng mệnh giá
