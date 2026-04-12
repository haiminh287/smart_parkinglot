# Implementation Guide — Enhanced Banknote Classifier

## Dependency Order (implement theo thứ tự này)

```
1. feature_extractors.py     — shared feature extraction module  
2. train_and_evaluate.py      — updated training script
3. ai_classifier.py           — updated production classifier
```

**Không cần thay đổi**: `pipeline.py`, `color_classifier.py`, `detector.py`, `preprocessing.py`

---

## File 1: `backend-microservices/ai-service-fastapi/app/engine/feature_extractors.py` (MỚI)

### Purpose
Shared module chứa tất cả handcrafted feature extraction functions. Dùng chung cho cả training và inference.

### Functions Required

#### `extract_gabor_features(img_bgr: np.ndarray, n_orient: int = 4, n_freq: int = 3) → np.ndarray`
- Copy từ `train_and_evaluate.py` hiện tại (đã đúng logic)
- Input: BGR image (bất kỳ size)
- Process: resize to 128×128 gray → apply 12 Gabor kernels → mean + std per response
- Output: float32 array shape (24,)
- **Optimization**: pre-compute Gabor kernels một lần khi module load (module-level constant)

#### `extract_lbp_features(img_bgr: np.ndarray, n_bins: int = 26) → np.ndarray`
- **VIẾT MỚI** — KHÔNG copy pixel loop từ train_and_evaluate.py
- Input: BGR image (bất kỳ size)
- Process: resize to 128×128 gray → vectorized 3×3 LBP → uniform pattern histogram
- Output: float32 array shape (26,)
- **Algorithm (vectorized)**:
  ```
  gray = resize to 128×128
  center = gray[1:-1, 1:-1]
  8 shifted arrays via slicing:
    top_left     = gray[:-2, :-2]
    top          = gray[:-2, 1:-1]
    top_right    = gray[:-2, 2:]
    right        = gray[1:-1, 2:]
    bottom_right = gray[2:, 2:]
    bottom       = gray[2:, 1:-1]
    bottom_left  = gray[2:, :-2]
    left         = gray[1:-1, :-2]
  
  code = (top_left >= center).astype(np.uint8) << 0
       | (top >= center) << 1
       | (top_right >= center) << 2
       | (right >= center) << 3
       | (bottom_right >= center) << 4
       | (bottom >= center) << 5
       | (bottom_left >= center) << 6
       | (left >= center) << 7
  
  # Map 256 values → 26 bins (uniform patterns)
  # Uniform pattern: code có ≤ 2 bit transitions (0→1 hoặc 1→0)
  uniform_table = precompute_uniform_table()  # 256 → 0-25
  mapped = uniform_table[code]
  hist = np.bincount(mapped.ravel(), minlength=26).astype(np.float32)
  hist /= (hist.sum() + 1e-8)
  return hist
  ```

#### `extract_edge_features(img_bgr: np.ndarray) → np.ndarray`
- **MỚI hoàn toàn**
- Input: BGR image (bất kỳ size)
- Process: resize to 128×128 gray → Sobel → 3 feature groups
- Output: float32 array shape (36,)
- **Algorithm**:
  ```
  gray = resize to 128×128, float32
  gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
  gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
  magnitude = sqrt(gx² + gy²)
  angle = arctan2(gy, gx) → map to [0, 180) degrees (unsigned)
  
  # Feature group 1: Orientation histogram (18 bins, 10° each)
  edge_mask = magnitude > threshold(mean + 0.5*std)
  orientation_hist = np.histogram(angle[edge_mask], bins=18, range=(0, 180))
  orientation_hist /= (sum + 1e-8)  # normalize
  → 18 values
  
  # Feature group 2: Spatial edge density (4×4 grid)
  for each of 16 cells (32×32 pixels):
      density[cell] = count(magnitude[cell] > threshold) / cell_size
  → 16 values
  
  # Feature group 3: Global statistics
  mean_magnitude = magnitude.mean()
  edge_coverage = (magnitude > threshold).sum() / total_pixels
  → 2 values
  
  return concat(orientation_hist, density, [mean_magnitude, edge_coverage])
  # Total: 18 + 16 + 2 = 36
  ```

### Module-Level Constants
```python
# Pre-computed Gabor kernels (computed once at import time)
_GABOR_KERNELS: list[np.ndarray]  # 12 kernels

# Pre-computed LBP uniform pattern lookup table
_LBP_UNIFORM_TABLE: np.ndarray  # shape (256,), values 0-25

FEATURE_SIZE = 128  # resize target for handcrafted features
GABOR_FEAT_DIM = 24
LBP_FEAT_DIM = 26
EDGE_FEAT_DIM = 36
```

---

## File 2: `backend-microservices/ai-service-fastapi/train_and_evaluate.py` (MODIFY)

### Changes Required

#### 2.1 Replace model architecture

- Remove `build_model()` function (EfficientNet-B3 based)
- Add `build_enhanced_model()`:
  - Backbone: `torchvision.models.mobilenet_v3_large(pretrained=True)` with `classifier = nn.Identity()`
  - 3 FC branches for Gabor(24→48), LBP(26→32), Edge(36→48)
  - Fusion head: concat(960+48+32+48=1088) → FC(256) → FC(8)
- Remove `import timm` dependency

#### 2.2 Replace data split

- Remove current `prepare_split()` function (random split)
- Add `prepare_anti_leakage_split()`:
  - Parse filenames to extract group keys: `{denom}_{face}_{date}_{time}`
  - Split by frame range: first 80% frames → train (all augmentations), last 20% → val (only `_orig`)
  - Verify: assert no shared base frames between train/val
  - Log: expected frame counts, unique source count

#### 2.3 Update dataset class

- Import from `feature_extractors.py` instead of inline functions
- Add `extract_edge_features()` call in `__getitem__`
- Dataset returns: `(image_tensor, gabor_feat, lbp_feat, edge_feat, label)` — 5 items instead of 4
- Update dataloader unpacking in train/eval loops

#### 2.4 Update augmentation

- Replace current `train_tf` with enhanced pipeline (see ADR augmentation section)
- Add `RandomDesaturation` custom transform class
- Remove `RandomVerticalFlip` (banknotes không lật dọc)
- Add `GaussianBlur` with p=0.2

#### 2.5 Update training loop

- Reduce IMAGE_SIZE from 300 to 224 (MobileNetV3 native)
- Update forward call: `model(imgs, gabor_f, lbp_f, edge_f)` — 4 inputs
- Update checkpoint format to include all feature dims + arch marker
- Two-phase training with backbone freeze/unfreeze

#### 2.6 Update evaluation

- Same forward call change
- Update feature importance analysis to include edge features

#### 2.7 Save as new model filename

- Output: `banknote_enhanced_v3.pth` (NOT overwrite `cash_recognition_best.pth`)

---

## File 3: `backend-microservices/ai-service-fastapi/app/engine/ai_classifier.py` (MODIFY)

### Changes Required

#### 3.1 Add imports

```python
from app.engine.feature_extractors import (
    extract_gabor_features, extract_lbp_features, extract_edge_features,
    GABOR_FEAT_DIM, LBP_FEAT_DIM, EDGE_FEAT_DIM,
)
```

#### 3.2 Add MultiBranchMobileNet model class

- Same `nn.Module` class as in training script (matching architecture exactly)
- Backbone: MobileNetV3-Large with `classifier = nn.Identity()` → 960-dim
- 3 FC branches + fusion head (must match training architecture dimensions exactly)

#### 3.3 Modify `_try_load_model()`

- Add model type detection logic:
  ```
  if checkpoint is dict and "arch" contains "multibranch":
      → build MultiBranchMobileNet
      → load state dict from checkpoint["model_state_dict"]
      → set self._model_type = "enhanced"
  else:
      → existing MobileNetV3 loading logic
      → set self._model_type = "legacy"
  ```

#### 3.4 Add `_classify_enhanced()` method

- Extract features: `extract_gabor_features(img_bgr)`, `extract_lbp_features(img_bgr)`, `extract_edge_features(img_bgr)`
- Convert to tensors
- Run model forward: `model(image_tensor, gabor_tensor, lbp_tensor, edge_tensor)`
- Build probability dict, find best denomination
- Return `AIClassification` (same interface)

#### 3.5 Modify `classify()` dispatch

```python
def classify(self, img_bgr):
    if self._model_type == "enhanced":
        return self._classify_enhanced(img_bgr)
    elif self._model_type == "legacy":
        return self._classify_with_model(img_bgr)  # existing
    else:
        return self._stub_classify(img_bgr)  # existing
```

#### 3.6 Update model loading path in pipeline

- In `pipeline.py`, the AI classifier path logic:
  ```python
  # Try enhanced model first, fall back to legacy
  enhanced_path = os.path.join(model_dir, "banknote_enhanced_v3.pth")
  legacy_path = os.path.join(model_dir, "banknote_mobilenetv3.pth")
  ai_path = enhanced_path if os.path.exists(enhanced_path) else legacy_path
  ```
  **NOTE**: Đây là thay đổi DUY NHẤT trong pipeline.py — chỉ thay đổi đường dẫn model file preference.

---

## Interfaces to Implement

| File | Class/Function | Signature |
|------|----------------|-----------|
| feature_extractors.py | `extract_gabor_features` | `(img_bgr: np.ndarray, n_orient=4, n_freq=3) → np.ndarray[24]` |
| feature_extractors.py | `extract_lbp_features` | `(img_bgr: np.ndarray, n_bins=26) → np.ndarray[26]` |
| feature_extractors.py | `extract_edge_features` | `(img_bgr: np.ndarray) → np.ndarray[36]` |
| train_and_evaluate.py | `MultiBranchMobileNet` | `nn.Module(image, gabor_feat, lbp_feat, edge_feat) → logits[8]` |
| train_and_evaluate.py | `prepare_anti_leakage_split` | `(source_dir, split_dir, val_ratio) → stats_dict` |
| ai_classifier.py | `MultiBranchMobileNet` | same as training (duplicate class or import) |
| ai_classifier.py | `_classify_enhanced` | `(img_bgr: np.ndarray) → AIClassification` |

---

## Business Rules (implement exactly as specified)

1. **Model preference**: enhanced (`banknote_enhanced_v3.pth`) → legacy (`banknote_mobilenetv3.pth`) → stub fallback
2. **Feature extraction always uses 128×128**: regardless of input image size
3. **CNN branch always uses 224×224**: standard MobileNetV3 input
4. **Val set ONLY contains `_orig` images**: no pre-augmented variants in validation
5. **No frame group split across train/val**: all augmentations of a source frame stay in the same set
6. **Checkpoint must contain `"arch"` key**: for backward-compatible model loading detection

---

## Error Scenarios (phải handle đủ)

| Scenario | Error Type | Handling |
|----------|-----------|---------|
| Enhanced model file missing | N/A | Auto-fallback to legacy model |
| Legacy model file also missing | N/A | Auto-fallback to stub classifier |
| Feature extraction fails | Caught exception | Log warning, return zero vector for that branch |
| Image too small (< 32×32) | N/A | Pad to 128×128 before feature extraction |
| Grayscale image input | N/A | Convert to 3-channel before processing |
| torch not installed | ImportError | Stub fallback (existing behavior) |
| CUDA not available | N/A | Default to CPU (existing behavior) |

---

## Pattern Reference

- Pipeline integration pattern: see current `ai_classifier.py` `_classify_with_model()` for tensor preparation flow
- Feature extraction pattern: see current `train_and_evaluate.py` `extract_gabor_features()` and `extract_color_features()`
- Multi-branch model pattern: see current `train_and_evaluate.py` `build_model()` for EfficientNet version — MobileNetV3 version follows same structure but with 4 branches instead of 3

---

## Verification Checklist (cho Implementer)

```
[ ] feature_extractors.py: extract_gabor_features returns shape (24,)
[ ] feature_extractors.py: extract_lbp_features returns shape (26,) — VECTORIZED, < 5ms
[ ] feature_extractors.py: extract_edge_features returns shape (36,)
[ ] train_and_evaluate.py: model forward accepts (image, gabor, lbp, edge)
[ ] train_and_evaluate.py: data split has NO leakage (val only _orig, split by group)
[ ] train_and_evaluate.py: saves checkpoint with arch="mobilenetv3_multibranch_v3"
[ ] train_and_evaluate.py: no import timm (uses torchvision only)
[ ] ai_classifier.py: loads enhanced model and dispatches to _classify_enhanced
[ ] ai_classifier.py: loads legacy model (backward compatible)
[ ] ai_classifier.py: falls back to stub when no model available
[ ] pipeline.py: prefers banknote_enhanced_v3.pth, falls back to banknote_mobilenetv3.pth
[ ] Total inference time < 100ms on CPU
[ ] Model file < 30MB
```
