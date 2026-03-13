#!/usr/bin/env python3
"""
Banknote Image Organizer — ParkSmart AI.

Organize existing banknote images into the training directory structure.
NO CAMERA NEEDED — just put your images into the input folder.

Usage:
    # Step 1: Put images into input folder (see below)
    # Step 2: Run this script
    python organize_banknote_images.py

    # Or specify custom paths:
    python organize_banknote_images.py --input ./my_photos --output ./ml/datasets/banknote_v1

Input folder structure (SIMPLE — just put images in denomination folders):
    input_banknotes/
    ├── 1000/
    │   ├── photo1.jpg
    │   └── photo2.png
    ├── 2000/
    │   └── ...
    ├── 5000/
    ├── 10000/
    ├── 20000/
    ├── 50000/
    ├── 100000/
    ├── 200000/
    └── 500000/

OR flat structure with denomination in filename:
    input_banknotes/
    ├── 1000_001.jpg
    ├── 1000_002.jpg
    ├── 50000_front.jpg
    ├── 100000_back.png
    └── ...

Output (ready for training):
    ml/datasets/banknote_v1/real/
    ├── 1000/
    │   ├── 1000_real_20250201_120000_000001.jpg
    │   └── ...
    ├── 2000/
    └── ...

Author: ParkSmart AI Team
"""

import argparse
import csv
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# ── Vietnamese Denominations ─────────────────────────────────────────────
DENOMINATIONS: list[str] = [
    "1000", "2000", "5000", "10000", "20000",
    "50000", "100000", "200000", "500000",
]

IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


def detect_denomination_from_filename(filename: str) -> Optional[str]:
    """Try to detect denomination from filename.

    Looks for denomination numbers in the filename.
    Checks longest matches first to avoid matching "1000" in "100000".

    Args:
        filename: Image filename (without path).

    Returns:
        Denomination string if found, None otherwise.
    """
    name_lower = filename.lower()
    # Sort by length descending to match "500000" before "5000"
    for denom in sorted(DENOMINATIONS, key=len, reverse=True):
        if denom in name_lower:
            return denom
    return None


def resize_and_normalize(
    img_path: str,
    output_path: str,
    target_size: tuple[int, int] = (640, 480),
    quality: int = 95,
) -> bool:
    """Resize image to standard size and save as high-quality JPEG.

    Args:
        img_path: Input image path.
        output_path: Output image path.
        target_size: Target (width, height).
        quality: JPEG quality (0-100).

    Returns:
        True if successful.
    """
    if not HAS_CV2:
        # Fallback: just copy the file
        shutil.copy2(img_path, output_path)
        return True

    img = cv2.imread(img_path)
    if img is None:
        return False

    h, w = img.shape[:2]

    # Only resize if larger than target
    if w > target_size[0] or h > target_size[1]:
        # Maintain aspect ratio
        scale = min(target_size[0] / w, target_size[1] / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return True


def organize_images(
    input_dir: str,
    output_dir: str,
    category: str = "real",
    resize: bool = True,
    target_size: tuple[int, int] = (640, 480),
) -> dict[str, int]:
    """Organize banknote images into training directory structure.

    Supports two input modes:
    1. Subfolder mode: input_dir/1000/, input_dir/2000/, etc.
    2. Flat mode: filenames contain denomination (e.g., 1000_001.jpg)

    Args:
        input_dir: Directory containing input images.
        output_dir: Root output directory (e.g., ml/datasets/banknote_v1).
        category: Category name (real, print_attack, screen_attack).
        resize: Whether to resize images to target_size.
        target_size: Target image dimensions.

    Returns:
        Dictionary of denomination → count of images organized.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) / category

    if not input_path.exists():
        print(f"❌ Input directory not found: {input_path}")
        sys.exit(1)

    # Create output directories
    for denom in DENOMINATIONS:
        (output_path / denom).mkdir(parents=True, exist_ok=True)

    # Initialize metadata CSV
    metadata_file = Path(output_dir) / "metadata.csv"
    write_header = not metadata_file.exists()
    metadata_rows: list[list[str]] = []

    stats: dict[str, int] = {d: 0 for d in DENOMINATIONS}
    skipped: int = 0
    errors: int = 0
    counter: int = 0

    # Check if input has subfolders matching denominations
    has_subfolders = any(
        (input_path / d).is_dir() for d in DENOMINATIONS
    )

    if has_subfolders:
        print("📁 Mode: Subfolder mode (input_dir/denomination/image.jpg)")
        for denom in DENOMINATIONS:
            denom_dir = input_path / denom
            if not denom_dir.exists():
                print(f"  ⚠️  {denom}: folder not found, skipping")
                continue

            images = sorted([
                f for f in denom_dir.iterdir()
                if f.suffix.lower() in IMAGE_EXTENSIONS
            ])

            for img_file in images:
                counter += 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{counter:06d}"
                out_name = f"{denom}_{category}_{timestamp}.jpg"
                out_file = output_path / denom / out_name

                try:
                    if resize and HAS_CV2:
                        success = resize_and_normalize(
                            str(img_file), str(out_file), target_size,
                        )
                        if not success:
                            print(f"  ❌ Cannot read: {img_file.name}")
                            errors += 1
                            continue
                    else:
                        shutil.copy2(str(img_file), str(out_file))

                    stats[denom] += 1
                    metadata_rows.append([
                        out_name, denom, category,
                        timestamp, str(target_size[0]), str(target_size[1]),
                        str(img_file),
                    ])
                except Exception as e:
                    print(f"  ❌ Error processing {img_file.name}: {e}")
                    errors += 1

            print(f"  ✅ {denom}: {stats[denom]} images")

    else:
        print("📄 Mode: Flat mode (denomination detected from filename)")
        images = sorted([
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ])

        for img_file in images:
            denom = detect_denomination_from_filename(img_file.name)
            if denom is None:
                print(f"  ⚠️  Cannot detect denomination: {img_file.name} → skipped")
                skipped += 1
                continue

            counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{counter:06d}"
            out_name = f"{denom}_{category}_{timestamp}.jpg"
            out_file = output_path / denom / out_name

            try:
                if resize and HAS_CV2:
                    success = resize_and_normalize(
                        str(img_file), str(out_file), target_size,
                    )
                    if not success:
                        print(f"  ❌ Cannot read: {img_file.name}")
                        errors += 1
                        continue
                else:
                    shutil.copy2(str(img_file), str(out_file))

                stats[denom] += 1
                metadata_rows.append([
                    out_name, denom, category,
                    timestamp, str(target_size[0]), str(target_size[1]),
                    str(img_file),
                ])
            except Exception as e:
                print(f"  ❌ Error processing {img_file.name}: {e}")
                errors += 1

    # Write metadata
    with open(metadata_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "filename", "denomination", "category", "timestamp",
                "width", "height", "source_file",
            ])
        writer.writerows(metadata_rows)

    # Print summary
    total = sum(stats.values())
    print(f"\n{'=' * 60}")
    print(f"📊 ORGANIZATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Category: {category}")
    print(f"  Output:   {output_path.resolve()}")
    print()

    for denom in DENOMINATIONS:
        count = stats[denom]
        status = "✅" if count >= 50 else "⚠️" if count >= 10 else "❌"
        bar = "█" * min(count // 5, 40)
        print(f"  {status} {denom:>7s} VND: {count:4d} images {bar}")

    print(f"\n  Total organized: {total}")
    if skipped:
        print(f"  Skipped (no denomination): {skipped}")
    if errors:
        print(f"  Errors: {errors}")

    print(f"\n💡 Minimum recommended: 50 images/denomination")
    print(f"💡 Production quality: 200+ images/denomination")

    # Check readiness
    ready_count = sum(1 for d in DENOMINATIONS if stats[d] >= 50)
    if ready_count == len(DENOMINATIONS):
        print(f"\n🎉 ALL {len(DENOMINATIONS)} denominations ready for training!")
        print(f"   Run: python -m app.ml.training.train_cash_recognition --train-dir {output_path}")
    elif ready_count > 0:
        print(f"\n⚠️  {ready_count}/{len(DENOMINATIONS)} denominations have enough images")
        missing = [d for d in DENOMINATIONS if stats[d] < 50]
        print(f"   Need more images for: {', '.join(missing)}")
    else:
        print(f"\n❌ No denomination has enough images yet. Need at least 50 per denomination.")

    print(f"{'=' * 60}")
    return stats


def create_input_folder(input_dir: str) -> None:
    """Create input folder structure for the user to drop images into.

    Args:
        input_dir: Root input directory path.
    """
    input_path = Path(input_dir)
    for denom in DENOMINATIONS:
        (input_path / denom).mkdir(parents=True, exist_ok=True)

    readme_content = """# 📸 Bỏ ảnh tiền vào đây — ParkSmart AI

## Cách sử dụng:

1. Bỏ ảnh tiền vào thư mục tương ứng với mệnh giá:
   - 1000/   → Ảnh tờ 1.000 VND
   - 2000/   → Ảnh tờ 2.000 VND
   - 5000/   → Ảnh tờ 5.000 VND
   - 10000/  → Ảnh tờ 10.000 VND
   - 20000/  → Ảnh tờ 20.000 VND
   - 50000/  → Ảnh tờ 50.000 VND
   - 100000/ → Ảnh tờ 100.000 VND
   - 200000/ → Ảnh tờ 200.000 VND
   - 500000/ → Ảnh tờ 500.000 VND

2. Ảnh chấp nhận: .jpg, .jpeg, .png, .bmp, .webp
3. Nên chụp: nền sạch, đủ sáng, đa dạng góc (0°, 15°, 30°, 90°, mặt trước/sau)
4. Mục tiêu: 50+ ảnh/mệnh giá (tốt nhất: 200+)

5. Sau khi bỏ ảnh xong, chạy:
   cd backend-microservices/ai-service-fastapi
   python organize_banknote_images.py
"""
    readme_path = input_path / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"✅ Created input folder structure at: {input_path.resolve()}")
    print(f"   Put your banknote images into the denomination subfolders.")
    print(f"   Then run: python organize_banknote_images.py")


def main() -> None:
    """Entry point for banknote image organizer."""
    parser = argparse.ArgumentParser(
        description="ParkSmart AI — Organize Banknote Images for Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create input folder structure, then put images there:
  python organize_banknote_images.py --init

  # Organize images from default input folder:
  python organize_banknote_images.py

  # Organize from custom path:
  python organize_banknote_images.py --input ./my_banknote_photos

  # Organize as "print_attack" category:
  python organize_banknote_images.py --input ./fake_printed --category print_attack

  # Skip resize (keep original resolution):
  python organize_banknote_images.py --no-resize
        """,
    )
    parser.add_argument(
        "--init", action="store_true",
        help="Create input folder structure and exit",
    )
    parser.add_argument(
        "--input", "-i",
        default="./input_banknotes",
        help="Input directory with banknote images (default: ./input_banknotes)",
    )
    parser.add_argument(
        "--output", "-o",
        default="./ml/datasets/banknote_v1",
        help="Output dataset directory (default: ./ml/datasets/banknote_v1)",
    )
    parser.add_argument(
        "--category", "-c",
        default="real",
        choices=["real", "print_attack", "screen_attack"],
        help="Category for these images (default: real)",
    )
    parser.add_argument(
        "--no-resize", action="store_true",
        help="Don't resize images (keep original resolution)",
    )
    parser.add_argument(
        "--width", type=int, default=640,
        help="Target image width (default: 640)",
    )
    parser.add_argument(
        "--height", type=int, default=480,
        help="Target image height (default: 480)",
    )

    args = parser.parse_args()

    if args.init:
        create_input_folder(args.input)
        return

    if not os.path.exists(args.input):
        print(f"❌ Input directory not found: {args.input}")
        print(f"💡 Run first: python organize_banknote_images.py --init")
        print(f"   Then put your images in the {args.input}/ folder")
        sys.exit(1)

    organize_images(
        input_dir=args.input,
        output_dir=args.output,
        category=args.category,
        resize=not args.no_resize,
        target_size=(args.width, args.height),
    )


if __name__ == "__main__":
    main()
