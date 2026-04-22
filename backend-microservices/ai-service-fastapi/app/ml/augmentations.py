"""Albumentations transforms cho banknote classifier v2.

KHONG dung ElasticTransform / MixUp / heavy RGBShift vi lam bien dang
so seri + menh gia in tren to tien -> model hoc sai pattern.
"""
from __future__ import annotations

import albumentations as A
import cv2
from albumentations.pytorch import ToTensorV2

IMG_SIZE = 224

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_train_transform() -> A.Compose:
    """Training augmentation - mo phong dieu kien chup thuc te."""
    return A.Compose([
        A.RandomResizedCrop(IMG_SIZE, IMG_SIZE, scale=(0.8, 1.0), ratio=(0.9, 1.1)),
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=20, border_mode=cv2.BORDER_REFLECT, p=0.7),
        A.Perspective(scale=(0.02, 0.08), p=0.3),
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.7),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=15, p=0.4),
        A.CLAHE(clip_limit=2.0, p=0.2),
        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
            A.MotionBlur(blur_limit=7, p=1.0),
        ], p=0.3),
        A.GaussNoise(var_limit=(10, 40), p=0.3),
        A.CoarseDropout(max_holes=3, max_height=30, max_width=30, p=0.3),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ])


def build_val_transform() -> A.Compose:
    """Val augmentation - deterministic, no random."""
    return A.Compose([
        A.Resize(IMG_SIZE, IMG_SIZE),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ])


def build_tta_transforms() -> list[A.Compose]:
    """TTA - 5 bien the cho inference, average softmax."""
    base_norm = [
        A.Resize(IMG_SIZE, IMG_SIZE),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ]
    return [
        A.Compose(base_norm),
        A.Compose([A.HorizontalFlip(p=1.0), *base_norm]),
        A.Compose([A.Rotate(limit=(10, 10), p=1.0), *base_norm]),
        A.Compose([A.Rotate(limit=(-10, -10), p=1.0), *base_norm]),
        A.Compose([A.RandomBrightnessContrast(brightness_limit=(0.1, 0.1), contrast_limit=0, p=1.0), *base_norm]),
    ]
