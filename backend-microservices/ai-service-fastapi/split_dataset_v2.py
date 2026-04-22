"""Split dataset từ ml/datasets/banknote_v1/real/{class}/ → ml/models/split/{train,val}/{class}/.

80/20 random shuffle, seed=42 để reproducible.

Usage:
    python split_dataset_v2.py
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE / "ml" / "datasets" / "banknote_v1" / "real"
DST = BASE / "ml" / "models" / "split"
TRAIN_RATIO = 0.8
SEED = 42

CLASSES = ["1000", "2000", "5000", "10000", "20000", "50000", "100000", "200000", "500000"]


def main() -> None:
    rng = random.Random(SEED)
    for cls in CLASSES:
        src_dir = SRC / cls
        if not src_dir.exists():
            print(f"  SKIP {cls} — source dir missing")
            continue

        images = sorted(src_dir.glob("*.jpg"))
        if not images:
            print(f"  SKIP {cls} — no images")
            continue

        rng.shuffle(images)
        split_idx = int(len(images) * TRAIN_RATIO)

        for subset, imgs in [("train", images[:split_idx]), ("val", images[split_idx:])]:
            dst = DST / subset / cls
            if dst.exists():
                shutil.rmtree(dst)
            dst.mkdir(parents=True, exist_ok=True)
            for img in imgs:
                shutil.copy2(img, dst / img.name)

        print(f"  {cls}: {len(images)} total → train={split_idx} val={len(images)-split_idx}")


if __name__ == "__main__":
    main()
