"""
Shared texture/pattern feature extractors for banknote recognition.

Features:
  - Gabor: Orientation-sensitive pattern detection (guilloche, watermarks)
  - LBP: Local micro-texture encoding (paper grain, print quality)
  - Edge: Structural landmark differences (denomination-specific layout)

Used by both training (train_and_evaluate.py) and production inference (ai_classifier.py).
"""

import cv2
import numpy as np

GABOR_DIM = 24  # 4 orient × 3 freq × 2 stats
LBP_DIM = 10  # n_points + 2
EDGE_DIM = 36  # 16 density + 16 magnitude + 4 orientation
TOTAL_FEATURE_DIM = GABOR_DIM + LBP_DIM + EDGE_DIM  # 70

_IMG_SIZE = (128, 128)


def extract_gabor_features(
    img_bgr: np.ndarray, n_orient: int = 4, n_freq: int = 3
) -> np.ndarray:
    """Extract Gabor filter bank features for texture/pattern recognition."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gray = cv2.resize(gray, _IMG_SIZE)
    features = []
    freqs = [0.1, 0.3, 0.5][:n_freq]
    thetas = [i * np.pi / n_orient for i in range(n_orient)]
    for freq in freqs:
        for theta in thetas:
            kernel = cv2.getGaborKernel(
                (21, 21), sigma=4.0, theta=theta,
                lambd=1.0 / freq, gamma=0.5, psi=0,
            )
            resp = cv2.filter2D(gray, cv2.CV_32F, kernel)
            features.extend([float(resp.mean()), float(resp.std())])
    return np.array(features, dtype=np.float32)


def extract_lbp_features(
    img_bgr: np.ndarray, n_points: int = 8, radius: int = 1
) -> np.ndarray:
    """Extract vectorized Local Binary Pattern features for micro-texture."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
    gray = cv2.resize(gray, _IMG_SIZE)
    H, W = gray.shape
    m = radius + 1
    center = gray[m : H - m, m : W - m]
    lbp_code = np.zeros_like(center, dtype=np.uint32)

    for k in range(n_points):
        angle = 2 * np.pi * k / n_points
        dy = -radius * np.cos(angle)
        dx = radius * np.sin(angle)
        iy, ix = int(np.floor(dy)), int(np.floor(dx))
        fy, fx = dy - iy, dx - ix

        y0, y1 = m + iy, H - m + iy
        x0, x1 = m + ix, W - m + ix
        neighbor = (
            (1 - fy) * (1 - fx) * gray[y0:y1, x0:x1]
            + (1 - fy) * fx * gray[y0:y1, x0 + 1 : x1 + 1]
            + fy * (1 - fx) * gray[y0 + 1 : y1 + 1, x0:x1]
            + fy * fx * gray[y0 + 1 : y1 + 1, x0 + 1 : x1 + 1]
        )
        lbp_code |= ((neighbor >= center).astype(np.uint32) << k)

    n_bins = n_points + 2
    lbp_code = lbp_code % n_bins
    hist, _ = np.histogram(lbp_code.ravel(), bins=n_bins, range=(0, n_bins))
    hist = hist.astype(np.float32) / (hist.sum() + 1e-8)
    return hist


def extract_edge_features(img_bgr: np.ndarray) -> np.ndarray:
    """Extract structural edge/gradient features over a 4x4 grid."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, _IMG_SIZE)

    edges = cv2.Canny(gray, 50, 150)
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    orientation = np.arctan2(sobel_y, sobel_x)

    H, W = gray.shape
    cell_h, cell_w = H // 4, W // 4
    densities = np.empty(16, dtype=np.float32)
    magnitudes = np.empty(16, dtype=np.float32)
    orient_hist = np.zeros(4, dtype=np.float32)

    ori_bins = np.array([0, np.pi / 4, np.pi / 2, 3 * np.pi / 4])

    for row in range(4):
        for col in range(4):
            idx = row * 4 + col
            y0, y1 = row * cell_h, (row + 1) * cell_h
            x0, x1 = col * cell_w, (col + 1) * cell_w

            cell_edges = edges[y0:y1, x0:x1]
            densities[idx] = float(np.count_nonzero(cell_edges)) / cell_edges.size

            magnitudes[idx] = float(magnitude[y0:y1, x0:x1].mean())

            cell_ori = orientation[y0:y1, x0:x1].ravel()
            cell_ori_abs = np.abs(cell_ori)
            bin_idx = np.argmin(
                np.abs(cell_ori_abs[:, None] - ori_bins[None, :]), axis=1
            )
            for b in range(4):
                orient_hist[b] += float(np.sum(bin_idx == b))

    orient_hist = orient_hist / (orient_hist.sum() + 1e-8)
    return np.concatenate([densities, magnitudes, orient_hist]).astype(np.float32)


def extract_all_features(img_bgr: np.ndarray) -> dict[str, np.ndarray]:
    """Extract all feature sets from a single image."""
    return {
        "gabor": extract_gabor_features(img_bgr),
        "lbp": extract_lbp_features(img_bgr),
        "edge": extract_edge_features(img_bgr),
    }
