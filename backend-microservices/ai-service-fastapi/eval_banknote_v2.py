#!/usr/bin/env python3
"""Evaluate banknote EfficientNetV2-S: accuracy + confusion matrix + precision-at-accept analysis."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")  # headless — no display server needed
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
import torch.nn as nn
from app.ml.augmentations import build_val_transform
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from torchvision.models import efficientnet_v2_s
from train_banknote_v2 import DENOMINATIONS, NUM_CLASSES, BanknoteDataset

BASE_DIR = Path(__file__).resolve().parent
VAL_DIR = BASE_DIR / "ml" / "models" / "split" / "val"
WEIGHTS = BASE_DIR / "ml" / "models" / "banknote_effv2s.pth"
CM_PNG = BASE_DIR / "ml" / "models" / "confusion_matrix_v2.png"
REPORT_JSON = BASE_DIR / "ml" / "models" / "eval_report_v2.json"


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = efficientnet_v2_s(weights=None)
    in_feats = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_feats, NUM_CLASSES)
    model.load_state_dict(torch.load(WEIGHTS, map_location=device))
    model = model.to(device).eval()

    ds = BanknoteDataset(VAL_DIR, build_val_transform())
    # num_workers=0 cho Windows stability
    loader = DataLoader(
        ds, batch_size=24, shuffle=False, num_workers=0, pin_memory=False
    )
    print(f"Val samples: {len(ds)}")

    all_preds: list[int] = []
    all_labels: list[int] = []
    all_probs: list[np.ndarray] = []

    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            all_preds.extend(probs.argmax(axis=1).tolist())
            all_labels.extend(labels.tolist())
            all_probs.extend(probs.tolist())

    acc = sum(p == l for p, l in zip(all_preds, all_labels)) / len(all_labels)
    print(f"\n== Overall top-1 accuracy: {acc*100:.2f}% ==")

    report = classification_report(
        all_labels,
        all_preds,
        labels=list(range(NUM_CLASSES)),
        target_names=DENOMINATIONS,
        output_dict=True,
        zero_division=0,
    )
    print("\n== Per-class metrics ==")
    print(
        classification_report(
            all_labels,
            all_preds,
            labels=list(range(NUM_CLASSES)),
            target_names=DENOMINATIONS,
            zero_division=0,
        )
    )

    cm = confusion_matrix(all_labels, all_preds, labels=list(range(NUM_CLASSES)))
    plt.figure(figsize=(9, 7))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=DENOMINATIONS,
        yticklabels=DENOMINATIONS,
    )
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Banknote v2 — Confusion Matrix")
    plt.tight_layout()
    plt.savefig(CM_PNG, dpi=120)
    print(f"\n✓ Confusion matrix saved: {CM_PNG}")

    # Precision-at-accept với các (conf, margin) threshold pairs
    print("\n== Precision-at-accept với (conf, margin) thresholds ==")
    print(f"  {'conf':>6}  {'margin':>8}  {'accept_rate':>12}  {'precision':>10}")
    print("  " + "-" * 44)
    probs_arr = np.array(all_probs)
    labels_arr = np.array(all_labels)
    preds_arr = probs_arr.argmax(axis=1)

    threshold_results: list[dict] = []
    for conf_t, margin_t in [
        (0.70, 0.20),
        (0.80, 0.20),
        (0.80, 0.25),
        (0.85, 0.25),
        (0.90, 0.25),
        (0.92, 0.25),
        (0.92, 0.30),
        (0.95, 0.25),
        (0.95, 0.30),
        (0.97, 0.30),
    ]:
        top1 = probs_arr.max(axis=1)
        sorted_probs = np.sort(probs_arr, axis=1)
        top2 = sorted_probs[:, -2]
        margin = top1 - top2
        accept_mask = (top1 >= conf_t) & (margin >= margin_t)
        n_accept = int(accept_mask.sum())
        if n_accept == 0:
            print(f"  {conf_t:.2f}    {margin_t:.2f}       0 accepts")
            continue
        correct = int((preds_arr[accept_mask] == labels_arr[accept_mask]).sum())
        precision = correct / n_accept
        accept_rate = n_accept / len(labels_arr)
        marker = (
            " ← ≥99.5% + ≥80%" if precision >= 0.995 and accept_rate >= 0.80 else ""
        )
        print(
            f"  {conf_t:.2f}    {margin_t:.2f}    {accept_rate*100:8.1f}%    {precision*100:7.3f}%{marker}"
        )
        threshold_results.append(
            {
                "conf": conf_t,
                "margin": margin_t,
                "accept_rate": accept_rate,
                "precision": precision,
                "n_accept": n_accept,
            }
        )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "overall_accuracy": acc,
                "per_class": report,
                "confusion_matrix": cm.tolist(),
                "threshold_analysis": threshold_results,
            },
            indent=2,
        )
    )
    print(f"\n✓ Report saved: {REPORT_JSON}")


if __name__ == "__main__":
    main()
