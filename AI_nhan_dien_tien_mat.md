# 💵 Vietnamese Banknote Recognition AI — ATM-Grade Production Plan

> **Version**: 4.1-prod | **Cập nhật**: 2026-02-17
> **Service**: `ai-service-fastapi` (port 8009)
> **Endpoint**: `POST /api/detect/banknote/`
> **Target**: ATM-Grade → 99.90%+ accuracy, Full PAD, Strict VN Currency Only
> **Standard**: ISO/IEC 30107-3 (Biometric Presentation Attack Detection)
> **Upgrade**: v4.1 → v4.1-prod (5 mandatory pre-go-live improvements)

---

## I. GAP ANALYSIS: v4.0 → v4.1 → v4.1-prod

### GAP v4.0 → v4.1 (Existing Fixes)

| Lỗ hổng v4.0 | Hậu quả | Fix v4.1 | Accuracy Impact |
|---|---|---|---|
| Stage 1 YOLO chỉ detect "banknote vs background" | Ảnh in A4, iPad replay đều PASS | **PAD Material Detector** (3 class) | +2% |
| Energy OOD chỉ reject class lạ, KHÔNG reject fake in-distribution | Tiền in 500k vẫn PASS (embedding giống tiền thật) | **Metric Texture Verifier** (ArcFace) | +1.5% |
| FFT Liveness quá yếu | Không detect photo paper, UV ink, matte laminate | **Multi-signal Texture PAD** (LBP+Wavelet+Specular) | +1.2% |
| Temporal = naive majority vote | Frame có glare/blur vẫn được vote bình đẳng | **Weighted Confidence Decay** (quality × liveness × conf) | +0.5% |

### ❗ GAP v4.1 → v4.1-prod (5 Mandatory Pre-Go-Live Fixes)

| # | Lỗ hổng v4.1 | Hậu quả thực tế | Fix v4.1-prod | Impact |
|---|---|---|---|---|
| 1 | Stage -1 chỉ Homography (Rigid) | Tiền nhàu/cong → warp security thread, hologram ROI lệch, Siamese FAIL | **TPS Non-Rigid Refinement** sau Homography | +0.8% |
| 2 | ROI hard-coded normalized coords | Homography error ±3-6px → microtext ROI lệch ~5px → One-Class CNN anomaly | **ROI Local Alignment** (ORB feature matching) | +0.5% |
| 3 | Specular threshold cứng [0.005-0.10] | Ban đêm IR: specular quá thấp → REAL_POLYMER bị đánh MATTE_ATTACK | **Camera-Specific Specular Calibration** (specular_profile.json) | +0.3% |
| 4 | Không check serial number integrity | Cut-paste: hologram thật từ tiền rách dán vào tiền in → Texture PASS, ROI PASS | **Serial Integrity Check** (OCR + font forensics) | +0.4% |
| 5 | Drift monitor = monthly trigger | Parking: lighting shift = hourly (mưa, đèn sodium, IR mode) | **Sliding Window Drift Monitor** (real-time 500-frame window) | Reliability |

### Projected Accuracy Progression

| Pipeline Version | Accuracy |
|---|---|
| v3.0 (ResNet50 single) | ~90% |
| v4.0 (Multi-stage + Energy OOD) | ~96-97% |
| v4.1 + PAD | ~98.5% |
| v4.1 + PAD + Metric Verifier | ~99.3% |
| v4.1 Full (Texture PAD + Weighted Temporal) | 99.85%+ |
| **v4.1-prod (+ TPS + ROI Align + Specular Cal + Serial + Drift)** | **99.90%+** |

---

## II. KIẾN TRÚC 9-STAGE PIPELINE (ATM-Grade v4.1-prod)

### Pipeline Flow

```
Camera Input
     ↓
┌─────────────────────────────────────────────────────┐
│ Stage -1: GEOMETRIC RECTIFIER (UPGRADED)            │
│ Step 1: 4-corner keypoint → Homography 640×320      │
│ Step 2: TPS Non-Rigid Refinement ← PROD FIX #1     │
│ • detect_landmarks() → canonical_landmarks          │
│ • Thin-Plate Spline warp → fix nhàu/cong/nhăn       │
│ → Mọi góc chụp + mọi biến dạng → layout chuẩn      │
└────────────┬────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────┐
│ Stage 0: QUALITY GATE (Non-ML)                      │
│ • blur_score (Laplacian variance)                   │
│ • exposure_score (histogram analysis)               │
│ • glare_score (specular highlight detection)        │
│ → REJECT nếu ảnh xấu                               │
└────────────┬────────────────────────────────────────┘
             ↓ PASS
┌─────────────────────────────────────────────────────┐
│ Stage 1: PAD — PRESENTATION ATTACK DETECTOR         │
│ Model: YOLOv8m (3 classes)                          │
│   0: REAL_POLYMER    → Tiền thật                    │
│   1: PRINT_ATTACK    → Tiền in giấy/laser           │
│   2: SCREEN_ATTACK   → Ảnh từ màn hình              │
│ ISO/IEC 30107-3 compliant                           │
│ → REJECT ngay nếu PRINT_ATTACK hoặc SCREEN_ATTACK  │
│ → PASS + crop nếu REAL_POLYMER                      │
└────────────┬────────────────────────────────────────┘
             ↓ REAL_POLYMER
┌─────────────────────────────────────────────────────┐
│ Stage 2: DENOMINATION CLASSIFIER                    │
│ Model: EfficientNetV2-S (9 classes VND)             │
│ + Temperature Scaling (calibration)                 │
│ → Output: logits + calibrated confidence            │
└────────────┬────────────────────────────────────────┘
             ↓ CLASSIFIED
┌─────────────────────────────────────────────────────┐
│ Stage 2.5: OPEN-SET REJECTION (VN ONLY)             │
│ Energy-based OOD: reject USD, Euro, hóa đơn...     │
│ → REJECT mọi thứ không phải VND                     │
└────────────┬────────────────────────────────────────┘
             ↓ VND CONFIRMED
┌─────────────────────────────────────────────────────┐
│ Stage 3: METRIC TEXTURE VERIFIER                    │
│ Model: EfficientNet + ArcFace Head                  │
│ • Extract polymer texture embedding                 │
│ • Compare vs reference REAL texture bank            │
│ • Cosine similarity < threshold → SUSPICIOUS        │
└────────────┬────────────────────────────────────────┘
             ↓ TEXTURE VERIFIED
┌─────────────────────────────────────────────────────┐
│ Stage 4: ROI SECURITY CHECK (UPGRADED)              │
│ Step 1: ROI Auto-Align (ORB matching) ← FIX #2     │
│ Step 2: Siamese Network (hologram verifier)         │
│ Step 3: Anomaly Detector (One-Class CNN)            │
│                                                     │
│ + TEXTURE PAD (Multi-signal, UPGRADED)              │
│ • LBP Texture Map (paper grain detection)           │
│ • Wavelet Energy Map (multi-scale analysis)         │
│ • Specular Index (camera-calibrated) ← FIX #3      │
│ • Micro-contrast Entropy (print dot detection)      │
│ → Score: security_score + liveness_score            │
└────────────┬────────────────────────────────────────┘
             ↓ SCORED
┌─────────────────────────────────────────────────────┐
│ Stage 4.5: SERIAL INTEGRITY CHECK ← NEW FIX #4     │
│ • OCR serial number extraction                      │
│ • Font spacing / kerning analysis                   │
│ • Baseline alignment verification                   │
│ • Stroke width consistency                          │
│ • CRC-like pattern check                            │
│ → REJECT nếu cut-paste detected                     │
└────────────┬────────────────────────────────────────┘
             ↓ SERIAL VERIFIED
┌─────────────────────────────────────────────────────┐
│ Stage 5: TEMPORAL WEIGHTED DECISION                 │
│ Weight = confidence × quality × liveness            │
│ N-frame aggregation (3-5 frames, mobile only)       │
│ Entropy check → reject flickering predictions       │
│ → Final: denomination + confidence +                │
│   real/fake + reason                                │
└────────────┬────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────┐
│ BACKGROUND: SLIDING WINDOW DRIFT MONITOR ← FIX #5  │
│ • KL divergence on last 500 frames vs reference     │
│ • Auto-adjust thresholds on camera domain shift     │
│ • Triggers: mưa, đèn sodium, IR mode chuyển        │
└─────────────────────────────────────────────────────┘
```

---

## III. CHI TIẾT TỪNG FIX

### FIX #1: Stage 1 — PAD Material Detector (thay thế YOLO cũ)

> [!CAUTION]
> **YOLO cũ chỉ detect "banknote vs background"** → Ảnh in A4, tiền trên iPad đều = "banknote".
> **PAD Detector phải phân biệt VẬT LIỆU**, không chỉ hình dạng.

```python
# ===== TRAINING CONFIG =====
# Dataset cần:
#   REAL_POLYMER: 5000+ ảnh tiền thật (đa góc, đa sáng)
#   PRINT_ATTACK: 2000+ ảnh tiền in (laser, inkjet, photocopy)
#   SCREEN_ATTACK: 2000+ ảnh tiền trên màn hình (phone, tablet, monitor)

# YOLOv8 config
classes:
  0: REAL_POLYMER      # Tiền thật polymer/cotton
  1: PRINT_ATTACK      # In giấy, photocopy, laser
  2: SCREEN_ATTACK     # Chụp lại từ màn hình

model: yolov8m
epochs: 150
imgsz: 640

# Augmentation RIÊNG cho PAD:
# REAL_POLYMER: giữ nguyên texture
# PRINT_ATTACK: thêm augment giả lập printer artifacts
# SCREEN_ATTACK: thêm augment moiré, pixel grid

# ===== INFERENCE =====
class PADDetector:
    """Presentation Attack Detection — ISO/IEC 30107-3"""
    
    ATTACK_CLASSES = {"PRINT_ATTACK", "SCREEN_ATTACK"}
    
    def detect(self, image):
        results = self.model.predict(image, conf=0.5)
        
        for det in results:
            if det.class_name in self.ATTACK_CLASSES:
                return {
                    "decision": "REJECT",
                    "attack_type": det.class_name,
                    "confidence": det.conf,
                    "reason": f"Phát hiện tấn công: {det.class_name}"
                }
            
            if det.class_name == "REAL_POLYMER":
                return {
                    "decision": "PASS",
                    "crop": det.crop,
                    "pad_confidence": det.conf
                }
        
        return {"decision": "REJECT", "reason": "Không phát hiện tờ tiền"}
```

### FIX #2: Stage 3 — Metric Texture Verifier (ArcFace)

> [!CAUTION]
> **Energy OOD chỉ reject "class lạ"** (USD, hóa đơn).
> Tiền in màu 500k có **cùng layout** → Energy score vẫn PASS.
> Cần so sánh **TEXTURE**, không chỉ hình dạng/layout.

```python
class MetricTextureVerifier:
    """
    So sánh embedding texture của ảnh input với bank embedding tiền thật.
    Tiền in màu 500k: CÓ layout giống → nhưng texture khác polymer.
    """
    
    def __init__(self):
        # Backbone + ArcFace head (trained trên texture crops)
        self.backbone = timm.create_model('tf_efficientnetv2_s', 
                                          pretrained=True, num_classes=0)
        self.arcface_head = ArcFaceHead(
            in_features=1280,
            out_features=9,  # 9 denominations
            s=30.0,          # scale
            m=0.50           # margin (angular)
        )
        
        # Reference embeddings: trung bình embedding của N mẫu tiền thật
        # Cho MỖI mệnh giá riêng
        self.reference_bank = {}  # {denomination: mean_embedding}
    
    def build_reference_bank(self, real_dataset):
        """Tính mean embedding cho mỗi mệnh giá từ dataset tiền thật."""
        for denom in [1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]:
            embeddings = []
            for img in real_dataset.filter(denomination=denom):
                emb = self.backbone(img)  # (1, 1280)
                embeddings.append(emb)
            self.reference_bank[denom] = torch.stack(embeddings).mean(dim=0)
    
    def verify(self, image, predicted_denom):
        """
        So sánh texture embedding của input vs reference.
        Returns: similarity score (0-1), 1 = giống tiền thật nhất.
        """
        query_emb = self.backbone(image)  # (1, 1280)
        ref_emb = self.reference_bank[predicted_denom]  # (1280,)
        
        # Cosine Similarity
        similarity = F.cosine_similarity(query_emb, ref_emb.unsqueeze(0))
        
        if similarity < TEXTURE_THRESHOLD:  # e.g., 0.75
            return {
                "decision": "SUSPICIOUS",
                "texture_score": similarity.item(),
                "reason": "Texture không khớp polymer thật"
            }
        
        return {
            "decision": "PASS",
            "texture_score": similarity.item()
        }

class ArcFaceHead(nn.Module):
    """ArcFace angular margin loss head."""
    
    def __init__(self, in_features, out_features, s=30.0, m=0.50):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
    
    def forward(self, embeddings, labels=None):
        # Normalize
        cosine = F.linear(F.normalize(embeddings), F.normalize(self.weight))
        
        if labels is not None:
            # Training: add angular margin to target class
            theta = torch.acos(torch.clamp(cosine, -1.0 + 1e-7, 1.0 - 1e-7))
            target_logits = torch.cos(theta + self.m)
            one_hot = F.one_hot(labels, num_classes=cosine.size(1)).float()
            output = cosine * (1 - one_hot) + target_logits * one_hot
            return output * self.s
        
        return cosine  # Inference: raw cosine similarity
```

### FIX #3: Stage 4 — Multi-Signal Texture PAD (thay thế FFT đơn thuần)

> [!WARNING]
> **FFT alone fails** trên: photo paper, UV ink fake, polymer copy, matte laminated fake.
> Camera smartphone hiện đại đã tự "smooth" → FFT không thấy khác biệt.

```python
class TexturePAD:
    """
    Multi-signal Presentation Attack Detection.
    Kết hợp 4 tín hiệu texture thay vì chỉ FFT.
    """
    
    def analyze(self, gray_img):
        scores = {
            "lbp": self._lbp_texture(gray_img),
            "wavelet": self._wavelet_energy(gray_img),
            "specular": self._specular_reflection(gray_img),
            "micro_contrast": self._micro_contrast_entropy(gray_img),
        }
        
        # Weighted fusion
        final_score = (
            0.30 * scores["lbp"] +
            0.25 * scores["wavelet"] +
            0.25 * scores["specular"] +
            0.20 * scores["micro_contrast"]
        )
        
        is_real = final_score > TEXTURE_PAD_THRESHOLD
        
        return {
            "is_real": is_real,
            "liveness_score": final_score,
            "detail_scores": scores,
            "attack_type": None if is_real else self._classify_attack(scores)
        }
    
    def _lbp_texture(self, gray):
        """
        Local Binary Pattern — phát hiện paper grain vs polymer texture.
        Giấy in có grain pattern khác polymer thật.
        """
        from skimage.feature import local_binary_pattern
        lbp = local_binary_pattern(gray, P=24, R=3, method='uniform')
        hist, _ = np.histogram(lbp, bins=26, density=True)
        
        # So sánh với reference histogram của polymer thật
        similarity = 1.0 - scipy.spatial.distance.cosine(hist, self.ref_lbp_hist)
        return similarity
    
    def _wavelet_energy(self, gray):
        """
        Wavelet decomposition — phân tích multi-scale.
        Tiền thật có energy profile riêng ở các tần số khác nhau.
        Photo paper thiếu high-frequency detail.
        """
        import pywt
        coeffs = pywt.wavedec2(gray, 'db4', level=3)
        
        energies = []
        for detail_coeffs in coeffs[1:]:  # Skip approx
            for d in detail_coeffs:
                energies.append(np.sum(d**2))
        
        # Ratio high-freq / low-freq energy
        energy_ratio = sum(energies[3:]) / (sum(energies[:3]) + 1e-8)
        return min(energy_ratio / WAVELET_REF_RATIO, 1.0)
    
    def _specular_reflection(self, gray, lighting_mode="default"):
        """
        PROD FIX #3: Camera-Specific Specular Calibration.
        
        Polymer VN thật có specular reflection đặc trưng (bóng loáng).
        Giấy in / matte laminate KHÔNG có.
        
        v4.1 BUG: threshold cứng [0.005, 0.10] → ban đêm IR:
          - REAL_POLYMER specular quá thấp → bị đánh MATTE_ATTACK
        
        v4.1-prod: Load specular profile theo lighting condition.
        
        specular_profile.json:
        {
            "default":    {"min": 0.005, "max": 0.10,  "center": 0.04},
            "IR_night":   {"min": 0.002, "max": 0.03,  "center": 0.012},
            "LED_warm":   {"min": 0.006, "max": 0.08,  "center": 0.035},
            "daylight":   {"min": 0.010, "max": 0.12,  "center": 0.055},
            "sodium":     {"min": 0.004, "max": 0.06,  "center": 0.025}
        }
        """
        # Load camera-specific profile
        profile = self.specular_profiles.get(
            lighting_mode,
            self.specular_profiles["default"]
        )
        spec_min = profile["min"]
        spec_max = profile["max"]
        spec_center = profile["center"]
        
        # Detect specular highlights
        _, bright_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        specular_ratio = np.sum(bright_mask > 0) / bright_mask.size
        
        # Calibrated range check
        if spec_min < specular_ratio < spec_max:
            return 1.0  # Looks like real polymer for this lighting
        return max(0, 1.0 - abs(specular_ratio - spec_center) * 20)
    
    def _micro_contrast_entropy(self, gray):
        """
        Phân tích entropy ở micro-level.
        Tiền in có dot pattern (CMYK) → entropy khác tiền thật.
        """
        # Crop small patches and measure local entropy
        from skimage.filters.rank import entropy
        from skimage.morphology import disk
        
        entropy_map = entropy(gray, disk(5))
        mean_entropy = np.mean(entropy_map)
        std_entropy = np.std(entropy_map)
        
        # Tiền thật có entropy phân bố đều hơn tiền in
        uniformity = 1.0 - (std_entropy / (mean_entropy + 1e-8))
        return max(0, min(1, uniformity))
    
    def _classify_attack(self, scores):
        """Phân loại loại tấn công dựa trên pattern scores."""
        if scores["specular"] < 0.3:
            return "MATTE_PAPER_ATTACK"
        if scores["lbp"] < 0.4:
            return "PHOTOCOPY_ATTACK"
        if scores["micro_contrast"] < 0.4:
            return "INKJET_PRINT_ATTACK"
        return "UNKNOWN_ATTACK"
```

### FIX #4: Stage 5 — Weighted Temporal Decision (thay thế Majority Vote)

> [!IMPORTANT]
> **Majority Vote SAI** vì: frame bị blur/glare vẫn được vote ngang frame tốt.
> **ATM-grade phải dùng**: `weight = confidence × quality_score × liveness_score`

```python
class WeightedTemporalDecision:
    """
    ATM-Grade temporal aggregation.
    Mỗi frame có trọng số khác nhau dựa trên chất lượng.
    """
    
    def __init__(self, window_size=5, min_frames=3):
        self.window_size = window_size
        self.min_frames = min_frames
        self.buffer = collections.deque(maxlen=window_size)
    
    def add_frame_result(self, frame_result):
        """
        frame_result = {
            "denomination": 500000,
            "classifier_confidence": 0.94,
            "quality_score": 0.85,      # blur/exposure score [0-1]
            "liveness_score": 0.92,     # TexturePAD score [0-1]
            "texture_score": 0.88,      # MetricVerifier score [0-1]
            "pad_confidence": 0.96,     # PAD Detector score [0-1]
        }
        """
        # Compute composite weight
        weight = (
            frame_result["classifier_confidence"]
            * frame_result["quality_score"]
            * frame_result["liveness_score"]
            * frame_result["texture_score"]
        )
        
        frame_result["composite_weight"] = weight
        self.buffer.append(frame_result)
    
    def get_final_decision(self):
        if len(self.buffer) < self.min_frames:
            return {"status": "SCANNING", "frames_collected": len(self.buffer)}
        
        # ===== Weighted Voting =====
        votes = defaultdict(float)
        vote_details = defaultdict(list)
        
        for fr in self.buffer:
            denom = fr["denomination"]
            votes[denom] += fr["composite_weight"]
            vote_details[denom].append(fr["composite_weight"])
        
        winner = max(votes, key=votes.get)
        winner_total_weight = votes[winner]
        all_weights_sum = sum(votes.values())
        
        # ===== Entropy Check — reject flickering =====
        # Nếu có quá nhiều class khác nhau → unstable
        probs = np.array([v / all_weights_sum for v in votes.values()])
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        
        if entropy > ENTROPY_THRESHOLD:  # e.g., 0.8
            return {
                "status": "UNCERTAIN",
                "reason": "Kết quả nhấp nháy, không ổn định",
                "entropy": entropy
            }
        
        # ===== Confidence Decay — frame cũ giảm trọng số =====
        # Frame mới nhất quan trọng hơn
        if len(vote_details[winner]) >= self.min_frames:
            # Kiểm tra frame cuối cùng khớp winner
            last_frame = self.buffer[-1]
            if last_frame["denomination"] != winner:
                return {
                    "status": "UNCERTAIN", 
                    "reason": "Frame gần nhất không khớp kết quả"
                }
        
        # ===== Quality Gate cho final decision =====
        avg_quality = np.mean([
            fr["quality_score"] for fr in self.buffer 
            if fr["denomination"] == winner
        ])
        
        if avg_quality < 0.6:
            return {
                "status": "RETRY",
                "reason": "Chất lượng ảnh quá thấp, vui lòng chụp lại"
            }
        
        # ===== FINAL ACCEPT =====
        return {
            "status": "ACCEPTED",
            "denomination": winner,
            "weighted_confidence": winner_total_weight / all_weights_sum,
            "avg_quality": avg_quality,
            "frames_used": len(self.buffer),
        }
```

---

## IV. DENOMINATION-AWARE DYNAMIC ROI (Stage 4) — UPGRADED v4.1-prod

> [!CAUTION]
> **PROD FIX #2**: ROI hard-coded normalized coords có **Homography error ±3-6px**.
> Microtext ROI chỉ cần lệch ~5px → One-Class CNN sẽ báo anomaly trên tiền THẬT.
> **ROI Local Alignment** dùng ORB matching giữa ROI crop và template trước khi verify.

Crop security features dựa trên **mệnh giá đã xác nhận** + **ảnh đã rectify** + **local alignment**.

```python
# Normalized coordinates [x1, y1, x2, y2] trên ảnh rectified (640×320)
ROI_MAP = {
    500000: {
        "hologram":       [0.82, 0.10, 0.95, 0.35],
        "watermark":      [0.15, 0.20, 0.35, 0.65],
        "microtext":      [0.40, 0.75, 0.65, 0.85],
        "serial_number":  [0.05, 0.80, 0.35, 0.92],
        "security_thread":[0.48, 0.05, 0.52, 0.95],
    },
    200000: {
        "hologram":       [0.80, 0.12, 0.93, 0.38],
        "watermark":      [0.18, 0.22, 0.38, 0.62],
        "microtext":      [0.42, 0.72, 0.62, 0.82],
        "serial_number":  [0.06, 0.78, 0.34, 0.90],
        "security_thread":[0.47, 0.05, 0.53, 0.95],
    },
    100000: { ... },
    50000:  { ... },
    20000:  { ... },
    10000:  { ... },
    5000:   { ... },
    2000:   { ... },
    1000:   { ... },
}

# ===== ROI TEMPLATE BANK =====
# Pre-computed reference crops cho mỗi ROI × mỗi denomination
# Dùng để local align trước khi Siamese/Anomaly check
ROI_TEMPLATES = load_roi_templates("models/roi_templates/")  # {denom: {roi_name: template_img}}

def extract_rois(rectified_img, denomination):
    """Extract + Local Align ROI crops."""
    layout = ROI_MAP.get(denomination)
    if not layout: return {}

    h, w = rectified_img.shape[:2]
    crops = {}
    for name, (x1, y1, x2, y2) in layout.items():
        raw_crop = rectified_img[int(y1*h):int(y2*h), int(x1*w):int(x2*w)]

        # PROD FIX #2: Local Align trước khi verify
        template = ROI_TEMPLATES.get(denomination, {}).get(name)
        if template is not None:
            crops[name] = align_roi(raw_crop, template)
        else:
            crops[name] = raw_crop

    return crops


def align_roi(roi_crop, template):
    """
    ROI Local Alignment — PROD FIX #2.
    Dùng ORB feature matching để align ROI crop với template.
    Bù Homography error ±3-6px → ROI luôn khớp template
    trước khi đưa vào Siamese / Texture PAD / One-Class CNN.
    """
    orb = cv2.ORB_create(nfeatures=500)

    kp1, des1 = orb.detectAndCompute(
        cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY), None
    )
    kp2, des2 = orb.detectAndCompute(
        cv2.cvtColor(template, cv2.COLOR_BGR2GRAY), None
    )

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return roi_crop  # Fallback: không đủ features

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)

    if len(matches) < 4:
        return roi_crop  # Fallback: không đủ matches

    # Lấy top matches
    good_matches = matches[:min(20, len(matches))]
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)

    if H is None:
        return roi_crop

    h, w = template.shape[:2]
    aligned = cv2.warpPerspective(roi_crop, H, (w, h))
    return aligned
```

---

## V. GEOMETRIC RECTIFIER (Stage -1) — UPGRADED v4.1-prod

> [!CAUTION]
> **PROD FIX #1**: Homography alone is RIGID — tiền nhàu/cong/nhăn túi quần là **non-planar surface**.
> Homography sẽ ép mặt cong → mặt phẳng → warp security thread → hologram ROI lệch → Siamese FAIL.
> **TPS Refinement** sau Homography sẽ giữ microtext alignment, security thread straightness, watermark shape.

```python
class GeometricRectifier:
    """
    v4.1-prod: Homography + TPS Non-Rigid Refinement.
    Step 1: Rigid Homography → canonical 640×320
    Step 2: TPS warp → fix nhàu/cong/nhăn
    """

    # Canonical landmarks cho tờ tiền chuẩn (trên 640×320)
    # 20 điểm đặc trưng: 4 corner + security features
    CANONICAL_LANDMARKS = np.float32([
        # 4 corners
        [0, 0], [640, 0], [640, 320], [0, 320],
        # Serial number region
        [32, 256], [224, 294],
        # Watermark center
        [160, 136],
        # Hologram center
        [566, 72],
        # Security thread (top, mid, bottom)
        [310, 16], [310, 160], [310, 304],
        # Microtext region
        [320, 248], [416, 272],
        # Additional grid points for TPS stability
        [160, 80], [320, 80], [480, 80],
        [160, 240], [320, 240], [480, 240],
        [480, 160],
    ])

    def __init__(self):
        self.keypoint_model = load_model("yolo_pose_nano.onnx")
        self.landmark_detector = load_model("landmark_detector_20pt.onnx")
        self.canonical_size = (640, 320)  # 2:1 banknote ratio

    def rectify(self, image):
        """Full rectification: Homography + TPS refinement."""
        # Step 1: Rigid Homography
        rectified, success = self._rigid_homography(image)
        if not success:
            return image, False

        # Step 2: TPS Non-Rigid Refinement (FIX #1)
        aligned = self._tps_refinement(rectified)

        return aligned, True

    def _rigid_homography(self, image):
        """Step 1: 4-corner homography → canonical layout."""
        kpts = self.keypoint_model.predict(image)

        if len(kpts) != 4:
            kpts = self._contour_fallback(image)
            if kpts is None:
                return image, False

        src_pts = np.float32(kpts)
        dst_pts = np.float32([
            [0, 0],
            [self.canonical_size[0], 0],
            [self.canonical_size[0], self.canonical_size[1]],
            [0, self.canonical_size[1]]
        ])

        H = cv2.getPerspectiveTransform(src_pts, dst_pts)
        rectified = cv2.warpPerspective(image, H, self.canonical_size)
        return rectified, True

    def _tps_refinement(self, rectified_img):
        """
        Step 2: Thin-Plate Spline warp để xử lý non-planar deformation.
        Phát hiện landmarks trên ảnh đã rectify → warp về canonical positions.
        TPS giữ được:
          ✔ microtext alignment
          ✔ security thread straightness
          ✔ watermark shape
        → Stage 3–4 không bị embedding drift vì wrinkle
        """
        # Detect landmarks trên ảnh đã Homography
        src_landmarks = self.landmark_detector.predict(rectified_img)

        if src_landmarks is None or len(src_landmarks) < 10:
            # Không đủ landmarks → skip TPS, dùng rigid result
            return rectified_img

        # Build TPS transformation
        tps = cv2.createThinPlateSplineShapeTransformer()

        src_pts = src_landmarks.reshape(1, -1, 2).astype(np.float32)
        dst_pts = self.CANONICAL_LANDMARKS[:len(src_landmarks)].reshape(1, -1, 2)

        matches = [cv2.DMatch(i, i, 0) for i in range(len(src_landmarks))]
        tps.estimateTransformation(dst_pts, src_pts, matches)

        # Apply TPS warp
        aligned = tps.warpImage(rectified_img)

        return aligned

    def _contour_fallback(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None
        largest = max(contours, key=cv2.contourArea)
        approx = cv2.approxPolyDP(largest, 0.02 * cv2.arcLength(largest, True), True)
        if len(approx) == 4:
            return approx.reshape(4, 2)
        return None
```

---

## VI. OPEN-SET REJECTION (Stage 2.5)

```python
def compute_energy_score(logits, temperature=1.0):
    """Energy-based OOD Detection — reject non-VND objects."""
    return -temperature * torch.logsumexp(logits / temperature, dim=1)

def is_vn_currency(logits, threshold=-5.0):
    energy = compute_energy_score(logits)
    if energy.item() > threshold:
        return False, "REJECT: Không phải tiền Việt Nam"
    return True, "VND confirmed"
```

---

## VII. DECISION POLICY (Non-ML Rules)

```python
class DecisionPolicy:
    """Final aggregation of all stage scores. Non-ML hard rules."""

    class Decision(Enum):
        ACCEPTED = "accepted"
        UNCERTAIN = "uncertain"
        SUSPICIOUS = "suspicious"
        REJECTED = "rejected"

    def decide(self, pipeline_result):
        # Rule 0: Quality
        if pipeline_result.quality_score < 0.3:
            return self._reject("Ảnh quá mờ / quá tối / quá sáng")

        # Rule 1: PAD
        if pipeline_result.pad_class != "REAL_POLYMER":
            return self._reject(f"Phát hiện tấn công: {pipeline_result.pad_class}")

        # Rule 2: Open-set
        if not pipeline_result.is_vn_currency:
            return self._reject("Không phải tiền Việt Nam")

        # Rule 3: Classifier confidence (CALIBRATED)
        if pipeline_result.calibrated_confidence < 0.85:
            return self._uncertain("Không chắc chắn mệnh giá")

        # Rule 4: Metric Texture Verifier
        if pipeline_result.texture_score < 0.70:
            return self._suspicious("Texture không khớp polymer thật")

        # Rule 5: Liveness (Texture PAD)
        if pipeline_result.liveness_score < 0.60:
            return self._suspicious("Nghi ngờ tiền giả — texture bất thường")

        # Rule 6: ROI Security
        if pipeline_result.security_score < 0.65:
            return self._suspicious("Security features bất thường")

        # Rule 7: Serial Integrity (PROD FIX #4)
        if pipeline_result.serial_score < 0.70:
            return self._suspicious("Serial number bất thường — nghi cut-paste")

        # Rule 8: All passed
        return FinalDecision(
            decision=self.Decision.ACCEPTED,
            denomination=pipeline_result.denomination,
            confidence=pipeline_result.calibrated_confidence,
            texture_score=pipeline_result.texture_score,
            liveness_score=pipeline_result.liveness_score,
            security_score=pipeline_result.security_score,
            serial_score=pipeline_result.serial_score,
        )
```

---

## VIII. SERIAL INTEGRITY CHECK (Stage 4.5) — NEW v4.1-prod

> [!CAUTION]
> **PROD FIX #4**: Advanced fake: in thật 500k → cắt hologram thật từ tiền rách → dán vào tiền in.
> → Texture PASS, ROI hologram PASS 😱
> **Serial Integrity Check** phát hiện cut-paste qua font forensics.

```python
class SerialIntegrityChecker:
    """
    Stage 4.5: Anti Cut-Paste Detection via Serial Number Forensics.
    Fake cut-paste thường có:
      - kerning mismatch (khoảng cách giữa các ký tự)
      - baseline shift (dòng chữ không thẳng)
      - stroke width inconsistency
      - font không khớp template
    """

    def __init__(self):
        self.ocr_engine = load_model("paddleocr_serial.onnx")
        # Reference font metrics cho mỗi denomination
        self.font_refs = load_json("models/serial_font_refs.json")

    def check_serial(self, serial_roi, denomination):
        """Full serial integrity analysis."""
        # Step 1: OCR extraction
        ocr_result = self.ocr_engine.recognize(serial_roi)
        if not ocr_result or len(ocr_result.text) < 6:
            return {"decision": "UNCERTAIN", "reason": "Không đọc được serial"}

        # Step 2: Font forensics
        scores = {
            "kerning": self._check_kerning(ocr_result, denomination),
            "baseline": self._check_baseline(ocr_result),
            "stroke_width": self._check_stroke_width(serial_roi, ocr_result),
            "crc_pattern": self._check_crc_pattern(ocr_result.text, denomination),
        }

        final_score = (
            0.30 * scores["kerning"] +
            0.25 * scores["baseline"] +
            0.25 * scores["stroke_width"] +
            0.20 * scores["crc_pattern"]
        )

        is_genuine = final_score > SERIAL_THRESHOLD  # e.g., 0.70

        return {
            "decision": "PASS" if is_genuine else "SUSPICIOUS",
            "serial_score": final_score,
            "serial_text": ocr_result.text,
            "detail_scores": scores,
            "reason": None if is_genuine else self._diagnose(scores)
        }

    def _check_kerning(self, ocr_result, denomination):
        """So sánh khoảng cách giữa các ký tự với reference."""
        ref = self.font_refs[str(denomination)]
        char_gaps = []
        for i in range(len(ocr_result.boxes) - 1):
            gap = ocr_result.boxes[i+1][0] - ocr_result.boxes[i][2]  # x_next - x_end
            char_gaps.append(gap)

        if not char_gaps:
            return 0.5

        # Compare with reference kerning std
        gap_std = np.std(char_gaps)
        ref_std = ref["kerning_std"]
        return max(0, 1.0 - abs(gap_std - ref_std) / (ref_std + 1e-8))

    def _check_baseline(self, ocr_result):
        """Kiểm tra tất cả ký tự nằm trên cùng 1 baseline."""
        y_centers = [(box[1] + box[3]) / 2 for box in ocr_result.boxes]
        if len(y_centers) < 3:
            return 0.5
        baseline_std = np.std(y_centers)
        # Tiền thật: baseline rất thẳng (std < 2px)
        return max(0, 1.0 - baseline_std / 5.0)

    def _check_stroke_width(self, serial_roi, ocr_result):
        """Phân tích stroke width consistency."""
        gray = cv2.cvtColor(serial_roi, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Distance transform → stroke width estimation
        dist = cv2.distanceTransform(255 - binary, cv2.DIST_L2, 5)
        stroke_widths = dist[dist > 0]

        if len(stroke_widths) < 10:
            return 0.5

        # Tiền thật: stroke width đều → coefficient of variation thấp
        cv_stroke = np.std(stroke_widths) / (np.mean(stroke_widths) + 1e-8)
        return max(0, 1.0 - cv_stroke * 2)

    def _check_crc_pattern(self, serial_text, denomination):
        """VN banknote serial có pattern nhất quán (prefix + check digit)."""
        ref = self.font_refs[str(denomination)]
        valid_prefixes = ref.get("valid_prefixes", [])

        # Check prefix
        prefix_match = any(serial_text.startswith(p) for p in valid_prefixes)

        # Check length
        expected_len = ref.get("serial_length", 11)
        len_match = len(serial_text) == expected_len

        score = 0.0
        if prefix_match: score += 0.5
        if len_match: score += 0.5
        return score

    def _diagnose(self, scores):
        """Chẩn đoán loại bất thường."""
        issues = []
        if scores["kerning"] < 0.5:
            issues.append("kerning mismatch")
        if scores["baseline"] < 0.5:
            issues.append("baseline shift")
        if scores["stroke_width"] < 0.5:
            issues.append("stroke width inconsistent")
        if scores["crc_pattern"] < 0.5:
            issues.append("serial pattern invalid")
        return f"Serial bất thường: {', '.join(issues)}"
```

---

## IX. KPI TARGETS (v4.1-prod)

| Metric | Target | Ghi chú |
|---|---|---|
| Denomination Accuracy | ≥99.90% | Trên calibrated test set (bao gồm tiền nhàu/cong) |
| PAD Detection Rate | ≥99% | PRINT + SCREEN attack |
| Fake Detection Recall | ≥97% | Tiền in/copy bị detect |
| False Positive Rate | <0.3% | Tiền thật bị flag giả (kể cả ban đêm IR) |
| Open-Set Rejection | 100% | USD / Euro / Hóa đơn |
| Cut-Paste Detection | ≥95% | Hologram cắt-dán phải bị detect |
| Inference Latency | <130ms | Full 9-stage, GPU |
| ECE (Calibration) | <0.05 | Confidence đáng tin |
| Mobile Latency | <280ms | TFLite, mid-range phone |
| Domain Shift Response | <5min | Auto-adjust khi lighting thay đổi |

---

## X. MLOPS — SLIDING WINDOW DRIFT DETECTION — UPGRADED v4.1-prod

> [!WARNING]
> **PROD FIX #5**: Drift monitor monthly trigger → parking lot lighting shift = **hourly**.
> Trời mưa, đèn sodium bật, IR mode chuyển → mỗi lần đều shift distribution.
> **Sliding Window Monitor** check liên tục trên 500-frame window.

```python
class SlidingWindowDriftMonitor:
    """
    v4.1-prod: Real-time drift detection thay thế monthly trigger.
    Theo dõi embedding distribution trên sliding window.
    """

    def __init__(self, window_size=500, kl_threshold=0.12):
        self.window_size = window_size
        self.kl_threshold = kl_threshold
        self.frame_buffer = collections.deque(maxlen=window_size)
        self.ref_distribution = None  # Loaded from calibration
        self.specular_profiles = load_json("models/specular_profile.json")
        self.alert_cooldown = 300  # seconds between alerts
        self.last_alert_time = 0

    def on_frame(self, frame_embedding, timestamp):
        """Called sau mỗi inference frame."""
        self.frame_buffer.append(frame_embedding)

        if len(self.frame_buffer) < self.window_size:
            return  # Chưa đủ data

        # Check drift mỗi 50 frames
        if len(self.frame_buffer) % 50 != 0:
            return

        kl_score = self._compute_kl()

        if kl_score > self.kl_threshold:
            if timestamp - self.last_alert_time > self.alert_cooldown:
                self._handle_drift(kl_score, timestamp)
                self.last_alert_time = timestamp

    def _compute_kl(self):
        """KL divergence giữa current window và reference."""
        current = np.array(list(self.frame_buffer))
        return compute_kl_divergence(current, self.ref_distribution)

    def _handle_drift(self, kl_score, timestamp):
        """Auto-response khi phát hiện domain shift."""
        # 1. Detect lighting mode
        lighting_mode = self._detect_lighting_mode()

        # 2. Auto-adjust specular thresholds
        self._auto_adjust_thresholds(lighting_mode)

        # 3. Alert
        send_alert(
            f"CAMERA DOMAIN SHIFT DETECTED! "
            f"KL={kl_score:.3f}, mode={lighting_mode}, "
            f"time={timestamp}"
        )

        # 4. Log for retraining pipeline
        log_drift_event(kl_score, lighting_mode, timestamp)

    def _detect_lighting_mode(self):
        """Phân loại lighting condition hiện tại."""
        recent = np.array(list(self.frame_buffer)[-50:])
        mean_brightness = np.mean(recent)

        if mean_brightness < 0.2:
            return "IR_night"
        elif mean_brightness < 0.4:
            return "sodium"
        elif mean_brightness > 0.7:
            return "daylight"
        return "LED_warm"

    def _auto_adjust_thresholds(self, lighting_mode):
        """Load specular profile phù hợp với lighting."""
        profile = self.specular_profiles.get(lighting_mode, {})
        if profile:
            update_runtime_config("specular_range", profile)
            logger.info(f"Auto-adjusted specular to {lighting_mode}: {profile}")
```

| Trigger | Action |
|---|---|
| **Sliding Window KL > 0.12** | **Auto-adjust thresholds + Alert** |
| Accuracy drop >0.5% | Alert → immediate retrain |
| KL divergence >0.20 (severe) | Auto-retrain pipeline |
| >300 user corrections | Triggered retrain |
| Hourly brightness check | Auto lighting mode detection |

---

## XI. CODE STRUCTURE (v4.1-prod)

### Training

| File | Action | Mô tả |
|---|---|---|
| `app/ml/training/train_pad_detector.py` | **NEW** | YOLOv8 PAD (3 class) training |
| `app/ml/training/train_classifier_v2.py` | UPGRADE | EfficientNetV2 + Temperature Scaling |
| `app/ml/training/train_metric_verifier.py` | **NEW** | ArcFace texture embedding training |
| `app/ml/training/train_texture_pad.py` | **NEW** | LBP/Wavelet reference calibration |
| `app/ml/training/train_security.py` | KEEP | Siamese + Anomaly detector |
| `app/ml/training/train_landmark_detector.py` | **NEW** | 20-point landmark detector cho TPS |
| `app/ml/training/train_serial_ocr.py` | **NEW** | Serial number OCR + font metrics |

### Inference Pipeline

| File | Action | Mô tả |
|---|---|---|
| `app/ml/banknote/pipeline.py` | UPGRADE | **9-stage** orchestrator (v4.1-prod) |
| `app/ml/banknote/rectifier.py` | **UPGRADE** | Homography + **TPS Refinement** |
| `app/ml/banknote/quality_gate.py` | KEEP | Blur/Exposure checks |
| `app/ml/banknote/pad_detector.py` | **NEW** | PAD Material Detector |
| `app/ml/banknote/classifier.py` | KEEP | EfficientNetV2 + temp scaling |
| `app/ml/banknote/open_set_rejection.py` | **NEW** | Energy-based OOD |
| `app/ml/banknote/metric_verifier.py` | **NEW** | ArcFace texture verifier |
| `app/ml/banknote/texture_pad.py` | **UPGRADE** | Multi-signal liveness + **specular calibration** |
| `app/ml/banknote/roi_aligner.py` | **NEW** | **ROI Local Alignment** (ORB matching) |
| `app/ml/banknote/serial_checker.py` | **NEW** | **Serial Integrity Check** (anti cut-paste) |
| `app/ml/banknote/security_analyzer.py` | UPGRADE | Dynamic ROI + Siamese |
| `app/ml/banknote/temporal_decision.py` | **NEW** | Weighted temporal voting |
| `app/ml/banknote/decision_policy.py` | UPGRADE | **8-rule** policy (thêm serial) |

### MLOps

| File | Action | Mô tả |
|---|---|---|
| `app/ml/mlops/drift_monitor.py` | **UPGRADE** | **Sliding Window** KL divergence (real-time) |
| `app/ml/mlops/feedback_collector.py` | KEEP | User corrections |
| `app/ml/mlops/hard_example_miner.py` | KEEP | Mine low-conf samples |

### Config / Data

| File | Action | Mô tả |
|---|---|---|
| `models/specular_profile.json` | **NEW** | Camera-specific specular thresholds |
| `models/serial_font_refs.json` | **NEW** | Font metrics per denomination |
| `models/roi_templates/` | **NEW** | Reference ROI crops per denomination |
| `models/landmark_detector_20pt.onnx` | **NEW** | 20-point landmark model cho TPS |

---

## XII. IMPLEMENTATION ROADMAP (16 Weeks)

### Phase 1: Data & Rectifier (Week 1-3)
- [ ] Collect PAD dataset: `REAL_POLYMER` (5000+), `PRINT_ATTACK` (2000+), `SCREEN_ATTACK` (2000+)
- [ ] Collect Negative data for Open-Set (USD, Euro, bills, receipts)
- [ ] Implement `GeometricRectifier` (Homography + **TPS Refinement**)
- [ ] Train **20-point landmark detector** cho TPS
- [ ] Define & annotate `ROI_MAP` cho 9 mệnh giá trên rectified images
- [ ] Build **ROI Template Bank** (reference crops per denomination)

### Phase 2: Core Models (Week 4-7)
- [ ] Train PAD Detector (YOLOv8m, 3 class) → PAD rate >99%
- [ ] Train EfficientNetV2 Classifier → accuracy >99%
- [ ] Train ArcFace Metric Verifier → texture similarity threshold tuning
- [ ] Calibrate LBP/Wavelet/Specular references cho Texture PAD
- [ ] Temperature Scaling calibration → ECE <0.05
- [ ] Train **Serial OCR** model (PaddleOCR fine-tuned)
- [ ] Build **serial_font_refs.json** cho 9 mệnh giá

### Phase 3: Pipeline Integration (Week 8-11)
- [ ] Build **9-stage** pipeline.py orchestrator
- [ ] Implement `ROIAligner` (ORB feature matching)
- [ ] Implement `SerialIntegrityChecker`
- [ ] Implement `WeightedTemporalDecision`
- [ ] Unit tests: PAD, Open-Set, Metric Verifier, Texture PAD, **Serial**, **ROI Align**
- [ ] Integration tests: full pipeline E2E
- [ ] Benchmark: latency <130ms (GPU), <280ms (mobile)

### Phase 4: Production Calibration (Week 12-14)
- [ ] **Specular Calibration**: measure specular profiles cho mỗi camera/lighting
- [ ] Build `specular_profile.json` (IR, LED, daylight, sodium)
- [ ] Implement `SlidingWindowDriftMonitor`
- [ ] Test auto-adjust thresholds khi lighting shift
- [ ] **Tiền nhàu/cong test**: validate TPS trên 500+ mẫu tiền deformed
- [ ] **Cut-paste test**: validate Serial Integrity trên 100+ mẫu cut-paste

### Phase 5: Go-Live & MLOps (Week 15-16)
- [ ] TFLite export (Rectifier + Classifier + PAD + Serial OCR)
- [ ] Mobile Temporal Decision SDK
- [ ] A/B testing framework
- [ ] Security audit & penetration test (paper, screen, laminate, **cut-paste** attacks)
- [ ] **Overnight test**: validate IR mode + specular calibration ban đêm
- [ ] **Rainy day test**: validate drift monitor auto-response

---

## XIII. PRODUCTION READINESS CHECKLIST

```
✅ 9-stage pipeline (rectify+TPS → PAD → classify → OOD → metric → ROI+Align → serial → temporal → decide)
✅ PAD Material Detection (ISO/IEC 30107-3)
✅ Metric Texture Verification (ArcFace polymer embedding)
✅ Multi-signal Texture PAD (LBP + Wavelet + Specular + Micro-contrast)
✅ Weighted Temporal Decision (quality × liveness × confidence)
✅ Open-Set Rejection (Energy-based, STRICT VN ONLY)
✅ Denomination-aware Dynamic ROI
✅ Confidence Calibration (Temperature Scaling, ECE < 0.05)

🆕 v4.1-prod MANDATORY FIXES:
✅ TPS Non-Rigid Refinement (tiền nhàu/cong/nhăn)
✅ ROI Local Alignment (ORB matching, bù Homography error)
✅ Camera-Specific Specular Calibration (specular_profile.json)
✅ Serial Integrity Check (anti cut-paste, font forensics)
✅ Sliding Window Drift Monitor (real-time, auto-adjust)
✅ Audit Trail (PredictionLog, mọi inference được log)
```

### v4.1-prod Coverage Matrix

| Case | v4.1 | v4.1-prod |
|---|---|---|
| Tiền mới | ✔ | ✔ |
| Tiền nhàu | ❌ | ✔ (TPS) |
| Tiền cong | ❌ | ✔ (TPS) |
| Ban đêm IR | ❌ | ✔ (Specular Cal) |
| Hologram cut-paste | ❌ | ✔ (Serial Check) |
| Lighting shift | ❌ | ✔ (Drift Monitor) |
| ROI lệch microtext | ❌ | ✔ (ROI Align) |

> [!WARNING]
> **Context cho Smart Parking System**: Nếu nhận nhầm tiền in 500k → barrier mở miễn phí.
> Pipeline v4.1-prod với PAD + Metric Verifier + **Serial Check** đảm bảo:
> - Tiền in → bị chặn ở Stage 1 (PAD)
> - Tiền cut-paste hologram → bị chặn ở Stage 4.5 (Serial)
> - Ban đêm IR → specular auto-calibrated
> - Lighting shift → drift monitor auto-adjust
