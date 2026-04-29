# Banknote Model History

## v2 (current) — EfficientNetV2-S

- Weights: `banknote_effv2s.pth`
- Architecture: EfficientNetV2-S (22M params)
- Inference: TTA x5 + rejection
- Current thresholds:
  - ACCEPT_HIGH_CONF = 0.85
  - ACCEPT_HIGH_MARGIN = 0.25
  - ACCEPT_LOW_CONF = 0.80
  - ACCEPT_LOW_MARGIN = 0.40

## v1 (backup) — Legacy classifier

- Inference code backup: `app/ml/inference/cash_recognition_v1_backup.py`
- Legacy model file (if available): `banknote_mobilenetv3.pth`

## Rollback to v1

1. Revert inference code:
   - `Copy-Item app/ml/inference/cash_recognition_v1_backup.py app/ml/inference/cash_recognition.py -Force`
2. Update env for legacy weight path:
   - Set `BANKNOTE_MODEL_PATH` to legacy model file (for example `.../banknote_mobilenetv3.pth`).
3. Restart local AI service (uvicorn).
4. Verify:
   - `curl -sS http://localhost:8009/health/`
   - Run one `/ai/detect/banknote/?mode=full` request and confirm non-500 response.
