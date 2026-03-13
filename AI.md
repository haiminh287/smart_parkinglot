# 💵 Vietnamese Banknote Recognition AI — Hybrid MVP Plan (FastAPI)

> **Version**: 1.0 (MVP Production-Ready)
> **Date**: 2026-02-17
> **Framework**: FastAPI
> **Strategy**: Color-First + AI Fallback
> **Goal**: Realtime Denomination Detection for Smart Parking
> **Upgrade Path**: MVP → ATM-Grade

---

## 🎯 OBJECTIVE

Build a lightweight, production-ready AI system that:

- Detects Vietnamese banknote denomination in realtime
- Runs efficiently on CPU / Edge devices
- Prioritizes color-based detection for speed
- Uses AI fallback for difficult cases
- Supports gradual dataset-based training for future upgrades

---

## 🚀 PIPELINE ARCHITECTURE

```
Camera Input
↓
Stage 0: Preprocessing (Quality + White Balance)
↓
Stage 1: Banknote Detection (YOLOv8n)
↓
Stage 2A: Color-Based Denomination (HSV)
↓
Dynamic Confidence Check
    ├── PASS → Final Output
    └── FAIL → AI Fallback
↓
Stage 2B: AI Classifier (MobileNetV3 / EfficientNet-B0)
↓
Final Decision
```

---

## 🔵 STAGE 0 — PREPROCESSING

### Tasks:

- Blur detection
- Exposure check
- White Balance Correction (IMPORTANT)

### Reason:

HSV color detection is highly sensitive to ambient lighting.

Example:

- 500k (cyan-blue) under yellow light
  → appears green
  → may be misclassified as 100k.

### White Balance:

```python
img = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
img[:,:,0] = cv2.equalizeHist(img[:,:,0])
img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
```

---

## 🟢 STAGE 1 — BANKNOTE DETECTION (YOLOv8n)

### Model:

YOLOv8n (lightweight)

Classes:

```
0: banknote
1: background
```

### Output:

Bounding box of detected banknote.

### IMPORTANT:

CROP the detected banknote before color detection.

```python
banknote = img[y1:y2, x1:x2]
```

Reason:

Avoid background color noise affecting HSV histogram.

---

## 🎨 STAGE 2A — COLOR-BASED DENOMINATION

Convert cropped banknote to HSV:

```python
hsv = cv2.cvtColor(banknote, cv2.COLOR_BGR2HSV)
h = hsv[:,:,0]
```

Compute dominant hue:

```python
hist = cv2.calcHist([h],[0],None,[180],[0,180])
dominant_hue = np.argmax(hist)
```

---

## ⚠️ DYNAMIC THRESHOLDING

### SAFE GROUP:

- 100k (Green)
- 200k (Red-Brown)

Distinctive colors.

```
Threshold = 0.75
```

---

### DANGER GROUP:

- 20k (Blue)
- 500k (Cyan)
- 10k (Yellow-Brown)
- 50k (Pink-Purple)

Color overlap under poor lighting.

```
Threshold = 0.90
```

---

### Decision Logic:

```python
if denom in SAFE_GROUP and confidence > 0.75:
    return result

elif denom in DANGER_GROUP and confidence > 0.90:
    return result

else:
    go_to_AI_fallback()
```

---

## 🧠 STAGE 2B — AI FALLBACK

Triggered when:

- Color confidence is low
- Lighting conditions are poor
- Banknote is old, wrinkled, or reflective

### Model Options:

| Model             | Latency (CPU) | Accuracy |
| ----------------- | ------------- | -------- |
| MobileNetV3-Large | ~15ms         | High     |
| EfficientNet-B0   | ~20ms         | Higher   |

Recommended:

```
MobileNetV3-Large
```

Classes:

```
9 denominations
```

---

## 📦 DATASET REQUIREMENTS

Structure:

```
dataset/
├── 1000/
├── 2000/
├── 5000/
...
```

Minimum:

```
1000 images / denomination
```

---

### MUST INCLUDE:

| Case               | Required |
| ------------------ | -------- |
| New banknotes      | ✔        |
| Old banknotes      | ✔        |
| Wrinkled           | ✔        |
| Bent               | ✔        |
| Night lighting     | ✔        |
| LED lighting       | ✔        |
| IR camera          | ✔        |
| Glare / Reflection | ✔        |
| Flash photos       | ✔        |
| Finger occlusion   | ✔        |

Polymer banknotes are reflective.

Glare must be included in training data.

---

## 📡 FASTAPI ENDPOINT

```
POST /api/detect/banknote
```

---

### Logic:

```python
# Stage 0
preprocess(img)

# Stage 1
banknote = detect_and_crop(img)

# Stage 2A
color_result = detect_color(banknote)

if safe_group and conf > 0.75:
    return color_result

elif danger_group and conf > 0.90:
    return color_result

# Stage 2B
ai_result = classifier.predict(banknote)

return ai_result
```

---

## ⚡ PERFORMANCE

| Method      | Latency  |
| ----------- | -------- |
| Color Only  | ~3ms     |
| AI Fallback | ~15-20ms |
| Hybrid Avg  | ~20-40ms |

---

## 📈 FUTURE UPGRADE PATH

| Phase   | Feature              |
| ------- | -------------------- |
| Phase 1 | Color + AI fallback  |
| Phase 2 | Fake Detection (PAD) |
| Phase 3 | Texture Verification |
| Phase 4 | ROI Security         |
| Phase 5 | ATM-Grade Pipeline   |

---

## ✅ MVP BENEFITS

- Runs on CPU
- No GPU required
- Realtime barrier response
- Dataset-based AI learning
- Supports gradual upgrade

---

## ⚠️ LIMITATION (ACCEPTED FOR MVP)

- No fake detection
- No screen replay detection
- No texture validation

To be added in future phases.

---

## 🎯 CONCLUSION

Hybrid approach:

```
Color-first for speed
AI fallback for robustness
Dataset-based training for future upgrades
```

Ensures:

- Fast deployment
- Realtime operation
- Scalable AI evolution

```

```
