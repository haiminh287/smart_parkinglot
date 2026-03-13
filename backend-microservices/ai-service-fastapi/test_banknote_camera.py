#!/usr/bin/env python3
"""
ParkSmart AI — Live Camera Banknote Recognition Test.

Uses the trained MultiBranch EfficientNet-B3 model (with Color + Gabor branches)
to recognize Vietnamese banknotes in real-time from webcam.

Usage:
    # Webcam mặc định (index 0):
    python test_banknote_camera.py

    # Webcam USB (index 1):
    python test_banknote_camera.py --camera 1

    # IP camera (DroidCam):
    python test_banknote_camera.py --camera "http://192.168.100.130:4747/video"

Controls:
    SPACE  — Classify current frame
    C      — Toggle continuous mode (auto-classify every frame)
    S      — Save current frame to disk
    Q/ESC  — Quit

Author: ParkSmart AI Team
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms

# ── Import model building + feature extraction from training script ──────
# We reuse the exact same functions from train_and_evaluate.py to guarantee
# that preprocessing matches training exactly.

BASE_DIR = Path(__file__).parent

MODEL_PATH = str(BASE_DIR / "ml" / "models" / "cash_recognition_best.pth")
CLASS_MAPPING_PATH = str(BASE_DIR / "ml" / "models" / "class_mapping.json")
IMG_SIZE = 300  # Must match training (EfficientNet-B3 @ 300x300)

# ── Feature extraction (copy from train_and_evaluate.py) ─────────────────

def extract_gabor_features(image_bgr: np.ndarray, n_orient: int = 4, n_freq: int = 3) -> np.ndarray:
    """Extract Gabor filter bank features for texture/pattern recognition."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gray = cv2.resize(gray, (128, 128))
    features = []
    freqs = [0.1, 0.3, 0.5][:n_freq]
    thetas = [i * np.pi / n_orient for i in range(n_orient)]
    for freq in freqs:
        for theta in thetas:
            kernel = cv2.getGaborKernel((21, 21), sigma=4.0, theta=theta,
                                        lambd=1.0/freq, gamma=0.5, psi=0)
            resp = cv2.filter2D(gray, cv2.CV_32F, kernel)
            features.extend([float(resp.mean()), float(resp.std())])
    return np.array(features, dtype=np.float32)


def extract_color_features(image_bgr: np.ndarray, bins: int = 12) -> np.ndarray:
    """Extract HSV color histogram features."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    feats = []
    ranges = [(0, 180), (0, 256), (0, 256)]
    for ch, (lo, hi) in enumerate(ranges):
        hist = cv2.calcHist([hsv], [ch], None, [bins], [lo, hi]).flatten()
        hist = hist / (hist.sum() + 1e-8)
        feats.extend(hist.tolist())
    return np.array(feats, dtype=np.float32)


# ── Model architecture (must match training exactly) ─────────────────────

def build_model(n_classes: int, color_feat_dim: int, gabor_feat_dim: int):
    """Build MultiBranch EfficientNet-B3 model (identical to training)."""
    import timm

    class MultiBranchBanknoteNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = timm.create_model(
                "efficientnet_b3", pretrained=False, num_classes=0,
                global_pool="avg",
            )
            vis_dim = self.backbone.num_features  # 1536

            self.color_branch = nn.Sequential(
                nn.Linear(color_feat_dim, 128),
                nn.BatchNorm1d(128),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.GELU(),
            )

            self.texture_branch = nn.Sequential(
                nn.Linear(gabor_feat_dim, 128),
                nn.BatchNorm1d(128),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.GELU(),
            )

            fused_dim = vis_dim + 64 + 64  # 1664
            self.classifier = nn.Sequential(
                nn.Dropout(0.40),
                nn.Linear(fused_dim, 512),
                nn.BatchNorm1d(512),
                nn.GELU(),
                nn.Dropout(0.25),
                nn.Linear(512, n_classes),
            )

        def forward(self, image, color_feat, gabor_feat):
            vis = self.backbone(image)
            color = self.color_branch(color_feat)
            texture = self.texture_branch(gabor_feat)
            fused = torch.cat([vis, color, texture], dim=1)
            return self.classifier(fused)

    return MultiBranchBanknoteNet()


# ── Denomination display config ──────────────────────────────────────────

DENOM_INFO = {
    "1000":   {"label": "1.000 VND",   "color": (54, 140, 171)},     # brown
    "2000":   {"label": "2.000 VND",   "color": (180, 120, 60)},     # blue-gray
    "5000":   {"label": "5.000 VND",   "color": (150, 50, 150)},     # purple
    "10000":  {"label": "10.000 VND",  "color": (40, 80, 180)},      # red-brown
    "20000":  {"label": "20.000 VND",  "color": (160, 80, 20)},      # deep blue
    "50000":  {"label": "50.000 VND",  "color": (120, 100, 200)},    # pink/rose
    "100000": {"label": "100.000 VND", "color": (50, 150, 50)},      # green
    "200000": {"label": "200.000 VND", "color": (100, 50, 180)},     # brown-orange
    "500000": {"label": "500.000 VND", "color": (180, 120, 40)},     # blue-teal
}

HIGH_CONFIDENCE = 0.80
LOW_CONFIDENCE = 0.50


# ── Model Loading ────────────────────────────────────────────────────────

def load_model(model_path: str):
    """Load trained MultiBranch model from checkpoint."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    checkpoint = torch.load(model_path, map_location=device, weights_only=False)

    idx_to_class = checkpoint.get("idx_to_class", {})
    if not idx_to_class:
        # Fallback: build from class_to_idx
        c2i = checkpoint.get("class_to_idx", {})
        idx_to_class = {str(v): k for k, v in c2i.items()}
    else:
        # Normalize keys to strings (checkpoint may store int keys)
        idx_to_class = {str(k): v for k, v in idx_to_class.items()}

    num_classes = checkpoint.get("num_classes", len(idx_to_class))
    color_dim = checkpoint.get("color_feat_dim", 36)
    gabor_dim = checkpoint.get("gabor_feat_dim", 24)
    img_size = checkpoint.get("img_size", 300)

    print(f"📋 Architecture: {checkpoint.get('arch', 'MultiBranch EfficientNet-B3')}")
    print(f"📋 Classes ({num_classes}): {list(idx_to_class.values())}")
    print(f"📋 Feature dims: color={color_dim}, gabor={gabor_dim}, img={img_size}x{img_size}")

    model = build_model(num_classes, color_dim, gabor_dim)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    epoch = checkpoint.get("epoch", "?")
    val_acc = checkpoint.get("val_acc", 0)
    print(f"✅ Model loaded (epoch {epoch}, val_acc={val_acc:.4f})")
    print(f"🖥️  Device: {device}")

    return model, idx_to_class, device, color_dim, gabor_dim, img_size


# ── Inference ────────────────────────────────────────────────────────────

def classify_frame(
    frame: np.ndarray,
    model: nn.Module,
    idx_to_class: dict,
    device: torch.device,
    img_size: int,
) -> tuple[str, float, dict[str, float]]:
    """Classify a single frame using MultiBranch model.

    Process:
      1. Resize to img_size x img_size → tensor (visual branch)
      2. Extract HSV color histogram features (color branch)
      3. Extract Gabor texture features (texture branch)
      4. Forward pass → softmax → prediction
    """
    # Prepare BGR image for feature extraction
    bgr_resized = cv2.resize(frame, (img_size, img_size))

    # Extract hand-crafted features
    color_feat = torch.tensor(
        extract_color_features(bgr_resized), dtype=torch.float32
    ).unsqueeze(0).to(device)

    gabor_feat = torch.tensor(
        extract_gabor_features(bgr_resized), dtype=torch.float32
    ).unsqueeze(0).to(device)

    # Prepare image tensor (RGB, normalized)
    rgb = cv2.cvtColor(bgr_resized, cv2.COLOR_BGR2RGB)
    val_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    img_tensor = val_transform(rgb).unsqueeze(0).to(device)

    # Inference
    with torch.no_grad():
        outputs = model(img_tensor, color_feat, gabor_feat)
        probabilities = torch.softmax(outputs, dim=1)[0]

    top_prob, top_idx = probabilities.max(0)
    predicted_class = idx_to_class[str(top_idx.item())]
    confidence = top_prob.item()

    all_probs = {}
    for idx, prob in enumerate(probabilities):
        cls_name = idx_to_class.get(str(idx), str(idx))
        all_probs[cls_name] = prob.item()

    return predicted_class, confidence, all_probs


# ── UI Drawing ───────────────────────────────────────────────────────────

def draw_result(frame, predicted, confidence, all_probs, inference_ms, continuous_mode):
    """Draw classification result overlay on frame."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    denom_info = DENOM_INFO.get(predicted, {"label": predicted, "color": (128, 128, 128)})

    if confidence >= HIGH_CONFIDENCE:
        banner_color = denom_info["color"]
        status = "OK"
    elif confidence >= LOW_CONFIDENCE:
        banner_color = (0, 180, 255)
        status = "?"
    else:
        banner_color = (0, 0, 180)
        denom_info = {"label": "Khong nhan dien duoc", "color": (128, 128, 128)}
        status = "X"

    # Banner at top
    cv2.rectangle(overlay, (0, 0), (w, 90), banner_color, -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    label = f"[{status}] {denom_info['label']}"
    cv2.putText(frame, label, (15, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

    conf_str = f"Confidence: {confidence * 100:.1f}%  |  {inference_ms:.0f}ms"
    cv2.putText(frame, conf_str, (15, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2)

    # Top-5 sidebar
    sorted_probs = sorted(all_probs.items(), key=lambda x: x[1], reverse=True)[:5]
    sidebar_x = w - 300
    sidebar_y = 110

    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (sidebar_x - 10, sidebar_y - 25),
                  (w - 10, sidebar_y + len(sorted_probs) * 32 + 5),
                  (0, 0, 0), -1)
    cv2.addWeighted(overlay2, 0.6, frame, 0.4, 0, frame)

    cv2.putText(frame, "Top predictions:", (sidebar_x, sidebar_y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    for i, (cls, prob) in enumerate(sorted_probs):
        y = sidebar_y + 22 + i * 32
        cls_info = DENOM_INFO.get(cls, {"label": cls, "color": (128, 128, 128)})
        bar_w = int(prob * 160)
        bar_color = cls_info["color"] if prob > 0.1 else (80, 80, 80)
        cv2.rectangle(frame, (sidebar_x, y - 6), (sidebar_x + bar_w, y + 12), bar_color, -1)
        text = f"{cls_info['label']}: {prob * 100:.1f}%"
        cv2.putText(frame, text, (sidebar_x + 5, y + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

    # Mode indicator
    mode_text = "MODE: CONTINUOUS (auto)" if continuous_mode else "MODE: MANUAL (Space=classify)"
    mode_color = (0, 255, 0) if continuous_mode else (200, 200, 200)
    cv2.putText(frame, mode_text, (15, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, mode_color, 1)

    cv2.putText(frame, "C=Toggle | S=Save | Q=Quit", (w - 280, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

    return frame


def draw_idle_overlay(frame):
    """Draw guide overlay when not classifying."""
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    cv2.line(frame, (cx - 40, cy), (cx + 40, cy), (0, 255, 0), 1)
    cv2.line(frame, (cx, cy - 40), (cx, cy + 40), (0, 255, 0), 1)

    rx, ry = int(w * 0.15), int(h * 0.15)
    rw, rh = int(w * 0.7), int(h * 0.7)
    cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), 2)

    cv2.putText(frame, "Dua to tien vao khung", (rx + 10, ry + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, "SPACE=Nhan dien | C=Lien tuc | Q=Thoat",
                (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    return frame


# ── Main Loop ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ParkSmart AI — Live Banknote Recognition Test",
    )
    parser.add_argument(
        "--camera", default="0",
        help="Camera index (0, 1, ...) or URL (http://...)",
    )
    parser.add_argument(
        "--model", default=MODEL_PATH,
        help=f"Path to model .pth file",
    )
    parser.add_argument(
        "--continuous", action="store_true",
        help="Start in continuous classification mode",
    )
    parser.add_argument(
        "--width", type=int, default=800,
        help="Camera frame width (default: 800)",
    )
    parser.add_argument(
        "--height", type=int, default=600,
        help="Camera frame height (default: 600)",
    )

    args = parser.parse_args()

    # ── Load model ──
    print("\n" + "=" * 60)
    print("  ParkSmart AI — Banknote Recognition Test")
    print("  Model: MultiBranch EfficientNet-B3 + Color + Gabor")
    print("=" * 60)

    if not os.path.exists(args.model):
        print(f"❌ Model not found: {args.model}")
        print(f"💡 Train first: python train_and_evaluate.py")
        sys.exit(1)

    model, idx_to_class, device, color_dim, gabor_dim, img_size = load_model(args.model)

    # ── Open camera ──
    camera_src = int(args.camera) if args.camera.isdigit() else args.camera
    print(f"\n📹 Opening camera: {camera_src}")

    cap = cv2.VideoCapture(camera_src)
    if not cap.isOpened():
        print(f"❌ Cannot open camera: {camera_src}")
        print(f"💡 Try: --camera 0  or  --camera 1  or  --camera http://IP:PORT/video")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"✅ Camera opened: {actual_w}x{actual_h}")

    # ── State ──
    continuous_mode = args.continuous
    last_result = None
    frame_count = 0
    save_count = 0

    print("\n🎮 Controls:")
    print("   SPACE  — Classify current frame")
    print("   C      — Toggle continuous mode")
    print("   S      — Save frame to disk")
    print("   Q/ESC  — Quit\n")

    window_name = "ParkSmart - Banknote Recognition"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, args.width, args.height)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        frame_count += 1
        display = frame.copy()

        # Continuous mode: classify every 3rd frame
        if continuous_mode and frame_count % 3 == 0:
            t0 = time.perf_counter()
            predicted, confidence, all_probs = classify_frame(
                frame, model, idx_to_class, device, img_size,
            )
            inference_ms = (time.perf_counter() - t0) * 1000
            last_result = (predicted, confidence, all_probs, inference_ms)

        # Draw UI
        if last_result:
            display = draw_result(
                display,
                last_result[0], last_result[1],
                last_result[2], last_result[3],
                continuous_mode,
            )
        else:
            display = draw_idle_overlay(display)

        cv2.imshow(window_name, display)

        # Keyboard
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:
            print("\n👋 Exiting...")
            break

        elif key == ord(" "):
            t0 = time.perf_counter()
            predicted, confidence, all_probs = classify_frame(
                frame, model, idx_to_class, device, img_size,
            )
            inference_ms = (time.perf_counter() - t0) * 1000
            last_result = (predicted, confidence, all_probs, inference_ms)
            info = DENOM_INFO.get(predicted, {"label": predicted})
            print(f"💵 {info['label']} — {confidence * 100:.1f}% ({inference_ms:.0f}ms)")

        elif key == ord("c"):
            continuous_mode = not continuous_mode
            if not continuous_mode:
                last_result = None
            print(f"🔄 Mode: {'CONTINUOUS' if continuous_mode else 'MANUAL'}")

        elif key == ord("s"):
            save_count += 1
            save_dir = Path("./test_captures")
            save_dir.mkdir(exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            save_path = save_dir / f"capture_{ts}_{save_count:03d}.jpg"
            cv2.imwrite(str(save_path), frame)
            print(f"💾 Saved: {save_path}")

    cap.release()
    cv2.destroyAllWindows()
    print("✅ Done!")


if __name__ == "__main__":
    main()
