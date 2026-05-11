#!/usr/bin/env python3
"""
Video → Training Frames Extractor — ParkSmart AI.

Extract frames from banknote videos into training dataset.
Each video ~10-15 seconds → 150-450 frames → diverse training data.

Supports FRONT & BACK videos per denomination:

    input_banknotes_video/
    ├── 1000_front.mp4        ← mặt trước tờ 1.000đ
    ├── 1000_back.mp4         ← mặt sau tờ 1.000đ
    ├── 2000_front.mp4
    ├── 2000_back.mp4
    ├── 5000_front.mp4
    ├── 5000_back.mp4
    ├── 10000_front.mp4
    ├── 10000_back.mp4
    ├── 20000_front.mp4
    ├── 20000_back.mp4
    ├── 50000_front.mp4
    ├── 50000_back.mp4
    ├── 100000_front.mp4
    ├── 100000_back.mp4
    └── 500000_front.mp4
    └── 500000_back.mp4
    # 200000 → thêm sau, chạy lại script

    → Tất cả frames sẽ gộp vào cùng folder denomination:
      ml/datasets/banknote_v1/real/1000/
        1000_real_front_20250301_120000_000001_orig.jpg
        1000_real_back_20250301_120001_000001_orig.jpg

Usage:
    python extract_banknote_frames.py
    python extract_banknote_frames.py --input ./my_videos

Author: ParkSmart AI Team
"""

import argparse
import csv
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# ── Vietnamese Denominations ─────────────────────────────────────────────
DENOMINATIONS: list[str] = [
    "1000",
    "2000",
    "5000",
    "10000",
    "20000",
    "50000",
    "100000",
    "200000",
    "500000",
]

VIDEO_EXTENSIONS: set[str] = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".flv"}
IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def detect_denomination_from_filename(filename: str) -> Optional[str]:
    """Detect denomination from video filename.

    Checks longest matches first to avoid matching '1000' in '100000'.
    """
    name_lower = filename.lower()
    for denom in sorted(DENOMINATIONS, key=len, reverse=True):
        if denom in name_lower:
            return denom
    return None


def detect_side_from_filename(filename: str) -> str:
    """Detect front/back side from filename.

    Returns 'front', 'back', or 'mix' if not specified.
    """
    name_lower = filename.lower()
    if "front" in name_lower or "truoc" in name_lower or "mat_truoc" in name_lower:
        return "front"
    if "back" in name_lower or "sau" in name_lower or "mat_sau" in name_lower:
        return "back"
    return "mix"


def compute_frame_quality(frame: np.ndarray) -> dict:
    """Compute quality metrics for a frame.

    Returns:
        Dict with blur_score (higher = sharper), brightness, contrast.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Laplacian variance = sharpness (higher = less blur)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Brightness (mean of grayscale)
    brightness = float(np.mean(gray))

    # Contrast (std of grayscale)
    contrast = float(np.std(gray))

    return {
        "blur_score": blur_score,
        "brightness": brightness,
        "contrast": contrast,
    }


def is_frame_usable(quality: dict, min_blur: float = 30.0) -> bool:
    """Check if a frame meets minimum quality requirements.

    Args:
        quality: Quality metrics from compute_frame_quality().
        min_blur: Minimum Laplacian variance (below = too blurry).

    Returns:
        True if frame is usable for training.
    """
    # Skip very blurry frames (camera moving, out of focus)
    if quality["blur_score"] < min_blur:
        return False

    # Skip too dark or too bright frames
    if quality["brightness"] < 30 or quality["brightness"] > 240:
        return False

    # Skip very low contrast frames
    if quality["contrast"] < 15:
        return False

    return True


def augment_frame(frame: np.ndarray, seed: int) -> list[tuple[np.ndarray, str]]:
    """Create augmented versions of a frame.

    Returns list of (augmented_frame, suffix) tuples.
    """
    results = [(frame, "orig")]
    rng = random.Random(seed)

    # Random horizontal flip
    if rng.random() > 0.5:
        results.append((cv2.flip(frame, 1), "hflip"))

    # Random brightness adjustment
    if rng.random() > 0.6:
        factor = rng.uniform(0.7, 1.3)
        bright = cv2.convertScaleAbs(frame, alpha=factor, beta=0)
        results.append((bright, "bright"))

    # Random slight rotation
    if rng.random() > 0.7:
        angle = rng.uniform(-15, 15)
        h, w = frame.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        rotated = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        results.append((rotated, f"rot{int(angle)}"))

    return results


def extract_frames_from_video(
    video_path: str,
    denomination: str,
    output_dir: str,
    target_size: tuple[int, int] = (640, 480),
    frame_interval: int = 3,
    max_frames: int = 300,
    quality: int = 95,
    augment: bool = True,
    min_blur: float = 30.0,
) -> dict:
    """Extract and organize frames from a banknote video.

    Args:
        video_path: Path to input video file.
        denomination: Denomination string (e.g., "50000").
        output_dir: Root output dir (e.g., ml/datasets/banknote_v1).
        target_size: Resize frames to (width, height).
        frame_interval: Extract every N-th frame (skip similar frames).
        max_frames: Maximum frames to extract before augmentation.
        quality: JPEG quality.
        augment: Whether to create augmented copies.
        min_blur: Minimum blur score for frame to be usable.

    Returns:
        Stats dict with counts.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ❌ Cannot open video: {video_path}")
        return {"total": 0, "skipped_blur": 0, "skipped_brightness": 0}

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    side = detect_side_from_filename(Path(video_path).stem)
    side_label = {"front": "mặt trước", "back": "mặt sau", "mix": ""}.get(side, "")

    print(
        f"  📹 Video: {Path(video_path).name} {'(' + side_label + ')' if side_label else ''}"
    )
    print(
        f"     FPS: {fps:.1f}, Duration: {duration:.1f}s, Total frames: {total_frames}"
    )

    real_dir = Path(output_dir) / "real" / denomination
    real_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "total": 0,
        "saved": 0,
        "augmented": 0,
        "skipped_blur": 0,
        "skipped_brightness": 0,
    }

    timestamp_base = datetime.now().strftime("%Y%m%d_%H%M%S")
    side_tag = side  # front / back / mix
    frame_idx = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        stats["total"] += 1
        frame_idx += 1

        # Skip frames based on interval
        if frame_idx % frame_interval != 0:
            continue

        # Stop if we've extracted enough
        if saved_count >= max_frames:
            break

        # Check frame quality
        q = compute_frame_quality(frame)

        if q["blur_score"] < min_blur:
            stats["skipped_blur"] += 1
            continue

        if q["brightness"] < 30 or q["brightness"] > 240:
            stats["skipped_brightness"] += 1
            continue

        if q["contrast"] < 15:
            stats["skipped_brightness"] += 1
            continue

        # Resize frame
        h, w = frame.shape[:2]
        if w > target_size[0] or h > target_size[1]:
            scale = min(target_size[0] / w, target_size[1] / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Save original + augmented versions
        if augment:
            versions = augment_frame(frame, seed=frame_idx)
        else:
            versions = [(frame, "orig")]

        for aug_frame, suffix in versions:
            saved_count += 1
            out_name = f"{denomination}_real_{side_tag}_{timestamp_base}_{saved_count:06d}_{suffix}.jpg"
            out_path = real_dir / out_name
            cv2.imwrite(str(out_path), aug_frame, [cv2.IMWRITE_JPEG_QUALITY, quality])

        stats["saved"] = saved_count
        if augment:
            stats["augmented"] += len(versions) - 1

    cap.release()

    print(
        f"     ✅ Extracted: {stats['saved']} images (incl. {stats['augmented']} augmented)"
    )
    print(
        f"     ⏩ Skipped: {stats['skipped_blur']} blur, {stats['skipped_brightness']} brightness"
    )

    return stats


def extract_all_videos(
    input_dir: str,
    output_dir: str,
    frame_interval: int = 3,
    max_frames: int = 300,
    augment: bool = True,
    target_size: tuple[int, int] = (640, 480),
    min_blur: float = 30.0,
) -> dict[str, int]:
    """Process all banknote videos in input directory.

    Supports:
    - Videos in root folder: input_dir/50000.mp4
    - Videos in subfolders: input_dir/50000/video1.mp4

    Args:
        input_dir: Directory containing banknote videos.
        output_dir: Output dataset directory.
        frame_interval: Extract every N-th frame.
        max_frames: Max frames per video.
        augment: Create augmented versions.
        target_size: Frame resize dimensions.
        min_blur: Minimum blur score.

    Returns:
        Dictionary of denomination → total image count.
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"❌ Input directory not found: {input_path}")
        print(f"💡 Create it and put your banknote videos inside:")
        print(f"   mkdir {input_path}")
        print(f"   # Put 1000.mp4, 2000.mp4, ... 500000.mp4")
        sys.exit(1)

    # Collect all videos with their denomination
    video_tasks: list[tuple[str, str]] = []  # (video_path, denomination)

    # Mode 1: Videos in subfolders (input_dir/50000/video.mp4)
    for denom in DENOMINATIONS:
        denom_dir = input_path / denom
        if denom_dir.is_dir():
            for f in sorted(denom_dir.iterdir()):
                if f.suffix.lower() in VIDEO_EXTENSIONS:
                    video_tasks.append((str(f), denom))

    # Mode 2: Videos in root folder (input_dir/50000.mp4)
    for f in sorted(input_path.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            denom = detect_denomination_from_filename(f.stem)
            if denom:
                # Don't add if already found via subfolder
                if not any(str(f) == vp for vp, _ in video_tasks):
                    video_tasks.append((str(f), denom))
            else:
                print(f"  ⚠️  Cannot detect denomination from: {f.name} → skipped")

    # Also handle images directly (bonus)
    for f in sorted(input_path.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
            denom = detect_denomination_from_filename(f.stem)
            if denom:
                # Copy image directly to output
                real_dir = Path(output_dir) / "real" / denom
                real_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_name = f"{denom}_real_{ts}_{f.name}"
                import shutil

                shutil.copy2(str(f), str(real_dir / out_name))

    if not video_tasks:
        print(f"❌ No banknote videos found in: {input_path}")
        print(f"💡 Put videos named like: 1000.mp4, 50000.mp4, etc.")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"🎬 BANKNOTE VIDEO → TRAINING FRAMES EXTRACTOR")
    print(f"{'=' * 60}")
    print(f"  Input:   {input_path.resolve()}")
    print(f"  Output:  {Path(output_dir).resolve()}")
    print(f"  Videos:  {len(video_tasks)}")
    print(f"  Frame interval: every {frame_interval}th frame")
    print(f"  Max frames/video: {max_frames}")
    print(f"  Augmentation: {'ON' if augment else 'OFF'}")
    print(f"{'=' * 60}\n")

    # Check which denominations already have images
    existing_counts: dict[str, int] = {}
    for denom in DENOMINATIONS:
        real_dir = Path(output_dir) / "real" / denom
        if real_dir.exists():
            existing_counts[denom] = len(list(real_dir.glob("*.jpg")))
        else:
            existing_counts[denom] = 0

    if any(c > 0 for c in existing_counts.values()):
        print("📊 Existing images in dataset:")
        for denom in DENOMINATIONS:
            if existing_counts[denom] > 0:
                print(
                    f"   {denom:>7s} VND: {existing_counts[denom]} images (will ADD more)"
                )
        print()

    # Process each video
    total_stats: dict[str, int] = {d: existing_counts.get(d, 0) for d in DENOMINATIONS}
    new_images: dict[str, int] = {d: 0 for d in DENOMINATIONS}

    for video_path, denom in video_tasks:
        side = detect_side_from_filename(Path(video_path).stem)
        side_label = {"front": "mặt trước", "back": "mặt sau", "mix": ""}.get(side, "")
        print(f"\n{'─' * 50}")
        print(f"  💵 {denom} VND {'— ' + side_label if side_label else ''}")
        stats = extract_frames_from_video(
            video_path=video_path,
            denomination=denom,
            output_dir=output_dir,
            target_size=target_size,
            frame_interval=frame_interval,
            max_frames=max_frames,
            augment=augment,
            min_blur=min_blur,
        )
        new_images[denom] += stats["saved"]
        total_stats[denom] += stats["saved"]

    # Final summary
    print(f"\n\n{'=' * 60}")
    print(f"📊 EXTRACTION SUMMARY")
    print(f"{'=' * 60}")

    total_new = sum(new_images.values())
    total_all = sum(total_stats.values())

    for denom in DENOMINATIONS:
        count = total_stats[denom]
        new = new_images[denom]
        status = "✅" if count >= 50 else "⚠️" if count >= 10 else "❌"
        bar = "█" * min(count // 10, 40)
        new_str = f" (+{new} new)" if new > 0 else ""
        print(f"  {status} {denom:>7s} VND: {count:4d} images{new_str}  {bar}")

    print(f"\n  Total images: {total_all} (new: {total_new})")
    print(f"\n💡 Minimum recommended: 50 images/denomination")
    print(f"💡 Production quality:  200+ images/denomination")

    # Check missing denominations
    missing = [d for d in DENOMINATIONS if total_stats[d] == 0]
    low = [d for d in DENOMINATIONS if 0 < total_stats[d] < 50]

    if missing:
        print(f"\n⚠️  MISSING denominations ({len(missing)}):")
        for d in missing:
            print(f"   ❌ {d} VND — add video '{d}.mp4' and run again")

    if low:
        print(f"\n⚠️  LOW image count:")
        for d in low:
            print(f"   ⚠️  {d} VND: only {total_stats[d]} images (need 50+)")

    ready = [d for d in DENOMINATIONS if total_stats[d] >= 50]
    if len(ready) == len(DENOMINATIONS):
        print(f"\n🎉 ALL {len(DENOMINATIONS)} denominations ready for training!")
    elif len(ready) > 0:
        print(f"\n✅ {len(ready)}/{len(DENOMINATIONS)} denominations ready")
        print(f"   You can train now and add missing denominations later!")

    print(f"\n🚀 Next step — train the model:")
    print(f"   python -m app.ml.training.train_cash_recognition \\")
    print(f"     --data-dir {Path(output_dir).resolve()}/real")
    print(f"{'=' * 60}")

    return total_stats


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ParkSmart AI — Extract Frames from Banknote Videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract frames from videos (default folder):
  python extract_banknote_frames.py

  # Custom input/output:
  python extract_banknote_frames.py --input ./my_videos --output ./ml/datasets/banknote_v1

  # Extract more frames per video:
  python extract_banknote_frames.py --max-frames 500 --interval 2

  # No augmentation (fewer but cleaner images):
  python extract_banknote_frames.py --no-augment

  # Add 200k later:
  # 1. Put 200000.mp4 into input_banknotes_video/
  # 2. Run again — it will add only the new denomination
  python extract_banknote_frames.py
        """,
    )
    parser.add_argument(
        "--input",
        "-i",
        default="./input_banknotes_video",
        help="Input directory with banknote videos (default: ./input_banknotes_video)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./ml/datasets/banknote_v1",
        help="Output dataset directory (default: ./ml/datasets/banknote_v1)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3,
        help="Extract every N-th frame (default: 3, higher = fewer frames)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=300,
        help="Max frames to extract per video before augmentation (default: 300)",
    )
    parser.add_argument(
        "--no-augment",
        action="store_true",
        help="Disable data augmentation (no flip/rotate/brightness variants)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=640,
        help="Target frame width (default: 640)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=480,
        help="Target frame height (default: 480)",
    )
    parser.add_argument(
        "--min-blur",
        type=float,
        default=30.0,
        help="Minimum blur score — frames below this are skipped (default: 30.0)",
    )

    args = parser.parse_args()

    # Create input folder if not exists
    input_path = Path(args.input)
    if not input_path.exists():
        input_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created input folder: {input_path.resolve()}")
        print(f"📁 Put your banknote videos here (front & back riêng):")
        print(f"   {input_path}/1000_front.mp4")
        print(f"   {input_path}/1000_back.mp4")
        print(f"   {input_path}/2000_front.mp4")
        print(f"   {input_path}/2000_back.mp4")
        print(f"   ... (tương tự cho các mệnh giá khác)")
        print(f"   {input_path}/500000_front.mp4")
        print(f"   {input_path}/500000_back.mp4")
        print(f"")
        print(f"   200000 → có thể thêm sau, chạy lại script")
        print(f"\n💡 Then run: python extract_banknote_frames.py")
        return

    extract_all_videos(
        input_dir=args.input,
        output_dir=args.output,
        frame_interval=args.interval,
        max_frames=args.max_frames,
        augment=not args.no_augment,
        target_size=(args.width, args.height),
        min_blur=args.min_blur,
    )


if __name__ == "__main__":
    main()
