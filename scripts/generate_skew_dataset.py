#!/usr/bin/env python3
"""Derive skew training dataset from synth-multiscript-250K pristine images.

Takes existing 250K pristine synthetic document images (27 scripts, 198 languages)
and derives a skew training dataset by applying:
  1. Orientation rotation (0/90/180/270) — Head 1 ground truth
  2. Skew rotation (±45 deg, non-uniform distribution) — Head 2+3 ground truth
  3. Document degradation (Albumentations) — realistic noise

Geometric transforms are applied BEFORE degradation to match real scanner physics:
  pristine image → orientation → skew → degradation → output

Output format matches Modal training script expectations:
  output_dir/
    train/
      images/
      labels.json  # {filename: {angle, orientation, ...metadata}}
    val/
      images/
      labels.json
    test/
      images/
      labels.json

Held-back scripts (Georgian, Armenian, Korean) go exclusively into the test split
for generalization testing — never seen during training.

Sources:
  - Local filesystem (--source-dir)
  - GCS bucket (--gcs-bucket, requires GOOGLE_APPLICATION_CREDENTIALS)

Usage:
    # Dry run (show statistics, no processing)
    python scripts/generate_skew_dataset.py \\
        --source-dir /path/to/synth_multiscript \\
        --output-dir /path/to/skew \\
        --dry-run

    # Generate from local source (70K default)
    python scripts/generate_skew_dataset.py \\
        --source-dir /path/to/synth_multiscript \\
        --output-dir /path/to/skew \\
        --total-images 70000

    # Generate from GCS (for Modal)
    python scripts/generate_skew_dataset.py \\
        --gcs-bucket image_detection_b \\
        --gcs-prefix synthetic_multiscript/ \\
        --output-dir /data/skew_training \\
        --total-images 70000
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Non-uniform bin configuration (mirrors config/skew_estimation.yaml)
# ---------------------------------------------------------------------------

SKEW_ZONES: list[tuple[str, float, float, float, int]] = [
    # (name, start, end, width, count)
    ("extreme_neg", -45.0, -15.0, 5.0, 6),
    ("moderate_neg", -15.0, -5.0, 2.0, 5),
    ("critical", -5.0, 5.0, 0.5, 20),
    ("moderate_pos", 5.0, 15.0, 2.0, 5),
    ("extreme_pos", 15.0, 45.0, 5.0, 6),
]

ORIENTATION_CLASSES = [0, 90, 180, 270]

# Scripts reserved exclusively for test split (never seen during training)
DEFAULT_HELD_BACK_SCRIPTS = ["Geor", "Armn", "Kore"]

# Images to generate per held-back script in test split
HELD_BACK_IMAGES_PER_SCRIPT = 500


def compute_bin_centers() -> list[float]:
    """Compute 42 non-uniform bin centers matching skew_estimation.yaml."""
    centers: list[float] = []
    for _name, start, _end, width, count in SKEW_ZONES:
        for i in range(count):
            centers.append(round(start + (i + 0.5) * width, 4))
    return centers


BIN_CENTERS = compute_bin_centers()
assert len(BIN_CENTERS) == 42, f"Expected 42 bins, got {len(BIN_CENTERS)}"


def angle_to_bin(angle: float) -> int:
    """Map an angle to its nearest bin index."""
    min_dist = float("inf")
    best_idx = 0
    for i, center in enumerate(BIN_CENTERS):
        dist = abs(angle - center)
        if dist < min_dist:
            min_dist = dist
            best_idx = i
    return best_idx


# ---------------------------------------------------------------------------
# Angle distribution (non-uniform, matching training plan)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AngleAllocation:
    """Angle distribution spec for one range."""

    low: float
    high: float
    fraction: float
    name: str


# Distribution from project plan — focuses on critical zone (±2 deg)
ANGLE_DISTRIBUTION: list[AngleAllocation] = [
    AngleAllocation(-45.0, -15.0, 0.05, "extreme_neg"),
    AngleAllocation(-15.0, -5.0, 0.08, "large_neg"),
    AngleAllocation(-5.0, -2.0, 0.12, "moderate_neg"),
    AngleAllocation(-2.0, -0.5, 0.15, "mild_neg"),
    AngleAllocation(-0.5, 0.5, 0.10, "near_zero"),
    AngleAllocation(0.5, 2.0, 0.15, "mild_pos"),
    AngleAllocation(2.0, 5.0, 0.12, "moderate_pos"),
    AngleAllocation(5.0, 15.0, 0.08, "large_pos"),
    AngleAllocation(15.0, 45.0, 0.05, "extreme_pos"),
    # Uniform tail coverage across all bins
    AngleAllocation(-45.0, 45.0, 0.10, "stratified_uniform"),
]


def sample_skew_angle(rng: random.Random) -> float:
    """Sample a skew angle from the non-uniform distribution.

    Args:
        rng: Seeded random generator.

    Returns:
        Skew angle in degrees (±45).
    """
    ranges = ANGLE_DISTRIBUTION
    fractions = [r.fraction for r in ranges]
    selected = rng.choices(ranges, weights=fractions, k=1)[0]
    return rng.uniform(selected.low, selected.high)


# ---------------------------------------------------------------------------
# Degradation profile distribution
# ---------------------------------------------------------------------------

DEGRADATION_WEIGHTS: dict[str, float] = {
    "pristine": 0.10,
    "light": 0.25,
    "moderate": 0.35,
    "heavy": 0.20,
    "aged": 0.07,
    "historical": 0.03,
}


def sample_degradation_profile(rng: random.Random) -> str:
    """Sample a degradation profile from weighted distribution."""
    profiles = list(DEGRADATION_WEIGHTS.keys())
    weights = list(DEGRADATION_WEIGHTS.values())
    return rng.choices(profiles, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Script stratification (proportional to synth-multiscript distribution)
# ---------------------------------------------------------------------------

# Tier-based sampling weights (higher-resource scripts get more samples)
SCRIPT_TIER_WEIGHTS: dict[str, float] = {
    # Tier 1 — High resource (48% of original dataset)
    "Latn": 0.14,
    "Arab": 0.08,
    "Hans": 0.06,
    "Cyrl": 0.06,
    "Deva": 0.08,
    "Hant": 0.06,
    # Tier 2 — Medium resource (29%)
    "Jpan": 0.04,
    "Kore": 0.04,
    "Beng": 0.03,
    "Thai": 0.03,
    "Taml": 0.03,
    "Hebr": 0.02,
    "Telu": 0.02,
    "Grek": 0.02,
    "Gujr": 0.02,
    "Knda": 0.02,
    # Tier 3 — Lower resource (23%)
    "Mlym": 0.02,
    "Guru": 0.015,
    "Mymr": 0.015,
    "Tibt": 0.015,
    "Sinh": 0.015,
    "Khmr": 0.015,
    "Laoo": 0.01,
    "Ethi": 0.01,
    "Orya": 0.01,
}


# ---------------------------------------------------------------------------
# Source image discovery — local filesystem
# ---------------------------------------------------------------------------


SKIP_DIRS = {"train", "val", "test", "augmented", "metadata", "__pycache__"}
_PNG_GLOB = "*.png"


def _is_valid_script_dir(script_dir: Path) -> bool:
    """Check if a directory is a valid script directory (not a skip/hidden dir).

    Args:
        script_dir: Directory path to check.

    Returns:
        True if the directory should be scanned for images.
    """
    if not script_dir.is_dir():
        return False
    name = script_dir.name
    return name not in SKIP_DIRS and not name.startswith((".", "_"))


def _collect_images_from_dir(script_dir: Path) -> list[Path]:
    """Collect PNG and JPG images from a single directory.

    Args:
        script_dir: Directory to scan for images.

    Returns:
        List of image paths found.
    """
    return list(script_dir.glob(_PNG_GLOB)) + list(script_dir.glob("*.jpg"))


def _discover_worker_layout(source_dir: Path) -> dict[str, list[Path]]:
    """Discover images from worker-based layout: source_dir/worker_*/ScriptCode/*.

    Args:
        source_dir: Root of synth-multiscript dataset.

    Returns:
        Dict mapping script code to sorted list of image paths.
    """
    images_by_script: dict[str, list[Path]] = {}
    worker_dirs = sorted(
        d for d in source_dir.iterdir() if d.is_dir() and d.name.startswith("worker_")
    )

    if not worker_dirs:
        return images_by_script

    logger.info("Detected worker-based layout (%d workers)", len(worker_dirs))
    for worker_dir in worker_dirs:
        for script_dir in sorted(worker_dir.iterdir()):
            if not _is_valid_script_dir(script_dir):
                continue
            imgs = _collect_images_from_dir(script_dir)
            if imgs:
                images_by_script.setdefault(script_dir.name, []).extend(imgs)

    for code in images_by_script:
        images_by_script[code].sort()
    return images_by_script


def _discover_flat_layout(source_dir: Path) -> dict[str, list[Path]]:
    """Discover images from flat layout: source_dir/ScriptCode/*.

    Args:
        source_dir: Root of synth-multiscript dataset.

    Returns:
        Dict mapping script code to sorted list of image paths.
    """
    images_by_script: dict[str, list[Path]] = {}
    for script_dir in sorted(source_dir.iterdir()):
        if not _is_valid_script_dir(script_dir):
            continue
        imgs = _collect_images_from_dir(script_dir)
        if imgs:
            images_by_script[script_dir.name] = sorted(imgs)
    return images_by_script


def _discover_split_layout(source_dir: Path) -> dict[str, list[Path]]:
    """Discover images from split-based layout: source_dir/{train,val,test}/images/ScriptCode/*.

    Args:
        source_dir: Root of synth-multiscript dataset.

    Returns:
        Dict mapping script code to list of image paths.
    """
    images_by_script: dict[str, list[Path]] = {}
    for sub in ["train", "val", "test"]:
        img_dir = source_dir / sub / "images"
        if not img_dir.exists():
            continue
        for script_dir in sorted(img_dir.iterdir()):
            if script_dir.is_dir():
                imgs = list(script_dir.glob(_PNG_GLOB))
                if imgs:
                    images_by_script.setdefault(script_dir.name, []).extend(imgs)
    return images_by_script


def discover_source_images(
    source_dir: Path,
) -> dict[str, list[Path]]:
    """Discover pristine images organized by script directory.

    Supports multiple directory layouts:
      1. Flat: source_dir/ScriptCode/*.png
      2. Worker-based: source_dir/worker_*/ScriptCode/*.png (NAS generation layout)
      3. Split-based: source_dir/{train,val,test}/images/ScriptCode/*.png

    Args:
        source_dir: Root of synth-multiscript dataset.

    Returns:
        Dict mapping script code to list of image paths.
    """
    # Check for worker-based layout first (worker_0, worker_1, ...)
    images_by_script = _discover_worker_layout(source_dir)
    if images_by_script:
        return images_by_script

    # Flat layout: source_dir/ScriptCode/*.png
    images_by_script = _discover_flat_layout(source_dir)
    if images_by_script:
        return images_by_script

    # Fallback: split-based layout
    return _discover_split_layout(source_dir)


# ---------------------------------------------------------------------------
# Source image discovery — GCS
# ---------------------------------------------------------------------------


def discover_gcs_images(
    bucket_name: str,
    prefix: str,
) -> dict[str, list[str]]:
    """Discover images in GCS bucket organized by script directory.

    Args:
        bucket_name: GCS bucket name.
        prefix: Prefix path within bucket (e.g. "synthetic_multiscript/").

    Returns:
        Dict mapping script code to list of GCS blob names.
    """
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    images_by_script: dict[str, list[str]] = {}

    # List all blobs under prefix
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        if not blob.name.endswith((".png", ".jpg")):
            continue
        # Extract script code from path: prefix/ScriptCode/image.png
        relative = blob.name[len(prefix) :]
        parts = relative.split("/")
        if len(parts) >= 2:
            script_code = parts[0]
            if script_code.startswith((".", "_")):
                continue
            if script_code in {"train", "val", "test", "augmented", "metadata"}:
                continue
            images_by_script.setdefault(script_code, []).append(blob.name)

    # Sort for deterministic ordering
    for code in images_by_script:
        images_by_script[code].sort()

    return images_by_script


def download_gcs_image(bucket_name: str, blob_name: str, dest_path: Path) -> Path:
    """Download a single image from GCS.

    Args:
        bucket_name: GCS bucket name.
        blob_name: Full blob name in bucket.
        dest_path: Local path to write image to.

    Returns:
        Path to downloaded file.
    """
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(dest_path))
    return dest_path


# ---------------------------------------------------------------------------
# Image processing (single image)
# ---------------------------------------------------------------------------


@dataclass
class ProcessedImage:
    """Result of processing a single source image."""

    output_filename: str
    source_path: str
    script_code: str
    skew_angle: float
    orientation_class: int
    skew_bin: int
    degradation_profile: str
    success: bool
    error: str | None = None


def process_single_image(
    source_path: Path,
    output_dir: Path,
    script_code: str,
    skew_angle: float,
    orientation_class: int,
    degradation_profile: str,
    output_idx: int,
) -> ProcessedImage:
    """Process a single image: apply orientation + skew + degradation.

    Args:
        source_path: Path to pristine source image.
        output_dir: Directory to write processed image.
        script_code: ISO 15924 script code.
        skew_angle: Skew angle in degrees (±45).
        orientation_class: Orientation rotation (0/90/180/270).
        degradation_profile: Degradation profile name.
        output_idx: Output filename index.

    Returns:
        ProcessedImage result.
    """
    try:
        from PIL import Image

        img = Image.open(source_path).convert("RGB")

        # Step 1: Apply orientation rotation (0/90/180/270)
        if orientation_class == 90:
            img = img.transpose(Image.Transpose.ROTATE_270)
        elif orientation_class == 180:
            img = img.transpose(Image.Transpose.ROTATE_180)
        elif orientation_class == 270:
            img = img.transpose(Image.Transpose.ROTATE_90)

        # Step 2: Apply fine skew rotation (±45 degrees)
        if abs(skew_angle) > 0.01:
            import cv2

            img_np = np.array(img)
            h, w = img_np.shape[:2]
            center = (w / 2, h / 2)

            rot_matrix = cv2.getRotationMatrix2D(center, -skew_angle, 1.0)

            cos_a = abs(rot_matrix[0, 0])
            sin_a = abs(rot_matrix[0, 1])
            new_w = int(h * sin_a + w * cos_a)
            new_h = int(h * cos_a + w * sin_a)

            rot_matrix[0, 2] += (new_w - w) / 2
            rot_matrix[1, 2] += (new_h - h) / 2

            rotated = cv2.warpAffine(
                img_np,
                rot_matrix,
                (new_w, new_h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255),
            )
            img = Image.fromarray(rotated)

        # Step 3: Apply degradation (after geometric transforms)
        img = _apply_degradation(img, degradation_profile)

        # Step 4: Resize to training resolution (384x384) to save storage
        # Full-res PNGs would require ~350GB; resized JPEGs need ~5GB
        img = img.resize((384, 384), Image.Resampling.LANCZOS)

        output_filename = f"skew_{output_idx:07d}.jpg"
        output_path = output_dir / output_filename
        img.save(output_path, "JPEG", quality=90)

        return ProcessedImage(
            output_filename=output_filename,
            source_path=str(source_path),
            script_code=script_code,
            skew_angle=skew_angle,
            orientation_class=orientation_class,
            skew_bin=angle_to_bin(skew_angle),
            degradation_profile=degradation_profile,
            success=True,
        )

    except Exception as exc:
        return ProcessedImage(
            output_filename=f"skew_{output_idx:07d}.jpg",
            source_path=str(source_path),
            script_code=script_code,
            skew_angle=skew_angle,
            orientation_class=orientation_class,
            skew_bin=angle_to_bin(skew_angle),
            degradation_profile=degradation_profile,
            success=False,
            error=str(exc),
        )


def _apply_degradation(img: Any, profile: str) -> Any:
    """Apply degradation effects based on profile.

    Uses Albumentations for fast, reproducible augmentation.
    Falls back to no-op if library unavailable.
    """
    if profile == "pristine":
        return img

    try:
        import albumentations as A  # noqa: N812

        img_np = np.array(img)
        params = _get_albumentations_params(profile)
        transforms_list = []

        if params["blur_limit"] > 0:
            transforms_list.extend(
                [
                    A.GaussianBlur(blur_limit=(3, params["blur_limit"]), p=0.5),
                    A.MotionBlur(blur_limit=(3, params["blur_limit"]), p=0.3),
                ]
            )

        if params["noise_var"][1] > 0:
            low_std = math.sqrt(params["noise_var"][0]) / 255.0
            high_std = math.sqrt(params["noise_var"][1]) / 255.0
            transforms_list.append(A.GaussNoise(std_range=(low_std, high_std), p=0.5))

        if params["jpeg_quality"][0] < 95:
            transforms_list.append(
                A.ImageCompression(
                    quality_range=(
                        params["jpeg_quality"][0],
                        params["jpeg_quality"][1],
                    ),
                    p=0.4,
                )
            )

        if params.get("perspective", 0) > 0:
            transforms_list.append(
                A.Perspective(scale=(0.01, params["perspective"]), p=0.2)
            )

        if profile in ("aged", "historical"):
            transforms_list.append(
                A.ColorJitter(
                    brightness=0.1,
                    contrast=0.15 if profile == "historical" else 0.1,
                    saturation=0.1,
                    hue=0.03,
                    p=0.7,
                )
            )

        if not transforms_list:
            return img

        pipeline = A.Compose(transforms_list)
        result = pipeline(image=img_np)
        from PIL import Image as PILImage

        return PILImage.fromarray(result["image"])

    except ImportError:
        logger.warning("Albumentations not available, skipping degradation")
        return img


def _get_albumentations_params(profile: str) -> dict[str, Any]:
    """Get Albumentations parameters for a degradation profile."""
    params: dict[str, dict[str, Any]] = {
        "pristine": {
            "blur_limit": 0,
            "noise_var": (0, 0),
            "jpeg_quality": (95, 100),
            "perspective": 0.0,
        },
        "light": {
            "blur_limit": 3,
            "noise_var": (5, 15),
            "jpeg_quality": (75, 95),
            "perspective": 0.02,
        },
        "moderate": {
            "blur_limit": 5,
            "noise_var": (10, 30),
            "jpeg_quality": (50, 85),
            "perspective": 0.05,
        },
        "heavy": {
            "blur_limit": 7,
            "noise_var": (20, 50),
            "jpeg_quality": (30, 70),
            "perspective": 0.1,
        },
        "aged": {
            "blur_limit": 3,
            "noise_var": (5, 20),
            "jpeg_quality": (60, 90),
            "perspective": 0.02,
        },
        "historical": {
            "blur_limit": 5,
            "noise_var": (15, 40),
            "jpeg_quality": (40, 75),
            "perspective": 0.05,
        },
    }
    return params.get(profile, params["moderate"])


# ---------------------------------------------------------------------------
# Dataset generation orchestrator
# ---------------------------------------------------------------------------


@dataclass
class GenerationPlan:
    """Plan for which images to process with what transforms."""

    items: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def _assign_split(
    rng: random.Random,
    test_fraction: float,
    val_fraction: float,
) -> str:
    """Randomly assign a sample to train/val/test split.

    Args:
        rng: Seeded random generator.
        test_fraction: Fraction for test split.
        val_fraction: Fraction for validation split.

    Returns:
        Split name: "train", "val", or "test".
    """
    roll = rng.random()
    if roll < test_fraction:
        return "test"
    if roll < test_fraction + val_fraction:
        return "val"
    return "train"


def _generate_plan_item(
    rng: random.Random,
    source_images: list[Any],
    script_code: str,
    split: str,
    output_idx: int,
) -> dict[str, Any]:
    """Generate a single plan item with sampled transforms.

    Args:
        rng: Seeded random generator.
        source_images: List of source image paths for this script.
        script_code: ISO 15924 script code.
        split: Target split name.
        output_idx: Output filename index.

    Returns:
        Plan item dict with source_path, transforms, split, and output_idx.
    """
    return {
        "source_path": str(rng.choice(source_images)),
        "script_code": script_code,
        "skew_angle": round(sample_skew_angle(rng), 4),
        "orientation_class": rng.choice(ORIENTATION_CLASSES),
        "degradation_profile": sample_degradation_profile(rng),
        "split": split,
        "output_idx": output_idx,
    }


def _update_plan_counts(
    item: dict[str, Any],
    orient_counts: dict[str, int],
    degrad_counts: dict[str, int],
    script_counts: dict[str, int],
    split_counts: dict[str, int],
) -> None:
    """Update counter dicts from a single plan item.

    Args:
        item: Plan item dict.
        orient_counts: Orientation distribution counter.
        degrad_counts: Degradation distribution counter.
        script_counts: Per-script count.
        split_counts: Per-split count.
    """
    orient_counts[str(item["orientation_class"])] += 1
    degrad_counts[item["degradation_profile"]] += 1
    script_counts[item["script_code"]] = script_counts.get(item["script_code"], 0) + 1
    split_counts[item["split"]] += 1


def _compute_angle_distribution(
    items: list[dict[str, Any]],
) -> dict[str, int]:
    """Compute angle distribution stats across all plan items.

    Args:
        items: List of plan items with skew_angle field.

    Returns:
        Dict mapping angle allocation name to count.
    """
    angle_counts = {alloc.name: 0 for alloc in ANGLE_DISTRIBUTION}
    for item in items:
        angle = item["skew_angle"]
        for alloc in ANGLE_DISTRIBUTION:
            if alloc.low <= angle < alloc.high or (
                alloc.name == "extreme_pos" and angle == alloc.high
            ):
                angle_counts[alloc.name] += 1
                break
    return angle_counts


def build_generation_plan(
    images_by_script: dict[str, list[Any]],
    total_images: int,
    val_fraction: float,
    test_fraction: float,
    seed: int,
    held_back_scripts: list[str] | None = None,
    held_back_per_script: int = HELD_BACK_IMAGES_PER_SCRIPT,
) -> GenerationPlan:
    """Build a generation plan with stratified sampling and 3-way split.

    Train/val splits are drawn from non-held-back scripts.
    Test split includes:
      - A portion of non-held-back scripts (test_fraction of total_images)
      - ALL held-back scripts (exclusive to test, for generalization testing)

    Args:
        images_by_script: Available source images by script code (Path or str).
        total_images: Total images for train+val+test (excluding held-back extras).
        val_fraction: Fraction of total_images for validation.
        test_fraction: Fraction of total_images for test (from seen scripts).
        seed: Random seed.
        held_back_scripts: Scripts reserved exclusively for test.
        held_back_per_script: Images to generate per held-back script.

    Returns:
        GenerationPlan with items and statistics.
    """
    rng = random.Random(seed)  # nosec B311
    held_back = set(held_back_scripts or [])

    train_val_scripts = {
        code: imgs
        for code, imgs in images_by_script.items()
        if code not in held_back and code in SCRIPT_TIER_WEIGHTS
    }
    test_only_scripts = {
        code: imgs for code, imgs in images_by_script.items() if code in held_back
    }

    if not train_val_scripts:
        logger.error("No matching scripts found in source directory")
        return GenerationPlan(stats={"error": "no matching scripts"})

    # Compute per-script allocation for train+val+test(seen)
    available_weight_sum = sum(SCRIPT_TIER_WEIGHTS[code] for code in train_val_scripts)
    per_script_count: dict[str, int] = {}
    for code in train_val_scripts:
        weight = SCRIPT_TIER_WEIGHTS[code] / available_weight_sum
        per_script_count[code] = max(1, round(total_images * weight))

    # Adjust to match total exactly
    current_total = sum(per_script_count.values())
    if current_total != total_images:
        diff = total_images - current_total
        largest = max(per_script_count, key=lambda c: per_script_count[c])
        per_script_count[largest] += diff

    items: list[dict[str, Any]] = []
    output_idx = 0
    orient_counts = dict.fromkeys((str(o) for o in ORIENTATION_CLASSES), 0)
    degrad_counts = dict.fromkeys(DEGRADATION_WEIGHTS, 0)
    script_counts: dict[str, int] = {}
    split_counts = {"train": 0, "val": 0, "test": 0}

    # Build items for train/val/test (seen scripts)
    for script_code, count in sorted(per_script_count.items()):
        source_images = train_val_scripts[script_code]
        if not source_images:
            continue
        for _i in range(count):
            split = _assign_split(rng, test_fraction, val_fraction)
            item = _generate_plan_item(
                rng, source_images, script_code, split, output_idx
            )
            items.append(item)
            _update_plan_counts(
                item, orient_counts, degrad_counts, script_counts, split_counts
            )
            output_idx += 1

    # Add held-back scripts exclusively to test split
    held_back_total = 0
    for script_code in sorted(held_back):
        source_images = test_only_scripts.get(script_code, [])
        if not source_images:
            logger.warning("Held-back script %s has no source images", script_code)
            continue
        for _i in range(held_back_per_script):
            item = _generate_plan_item(
                rng, source_images, script_code, "test", output_idx
            )
            items.append(item)
            _update_plan_counts(
                item, orient_counts, degrad_counts, script_counts, split_counts
            )
            held_back_total += 1
            output_idx += 1

    angle_counts = _compute_angle_distribution(items)

    stats = {
        "total_images": len(items),
        "train_count": split_counts["train"],
        "val_count": split_counts["val"],
        "test_count": split_counts["test"],
        "held_back_test_images": held_back_total,
        "scripts": len(script_counts),
        "per_script": dict(sorted(script_counts.items())),
        "orientation_distribution": orient_counts,
        "degradation_distribution": degrad_counts,
        "angle_distribution": angle_counts,
        "held_back_scripts": list(held_back),
        "seed": seed,
    }

    return GenerationPlan(items=items, stats=stats)


def _process_item_wrapper(args: tuple[Any, ...]) -> ProcessedImage:
    """Wrapper for process_single_image to work with ProcessPoolExecutor.

    Args:
        args: Tuple of (source_path, output_dir, script_code, skew_angle,
              orientation_class, degradation_profile, output_idx).

    Returns:
        ProcessedImage result.
    """
    return process_single_image(
        source_path=Path(args[0]),
        output_dir=Path(args[1]),
        script_code=args[2],
        skew_angle=args[3],
        orientation_class=args[4],
        degradation_profile=args[5],
        output_idx=args[6],
    )


def _build_work_items_for_split(
    split_items: list[dict[str, Any]],
    split_img_dir: Path,
    gcs_bucket: str | None,
    gcs_cache_dir: Path | None,
) -> tuple[list[tuple[Any, ...]], int]:
    """Build work item tuples for a single split, handling GCS downloads if needed.

    Args:
        split_items: Plan items for this split.
        split_img_dir: Output directory for this split's images.
        gcs_bucket: Optional GCS bucket name for source downloads.
        gcs_cache_dir: Optional local cache directory for GCS images.

    Returns:
        Tuple of (work_items list, error_count from GCS downloads).
    """
    work_items: list[tuple[Any, ...]] = []
    download_errors = 0

    for item in split_items:
        source_path = item["source_path"]

        if gcs_bucket and gcs_cache_dir:
            cache_path = gcs_cache_dir / Path(source_path).name
            if not cache_path.exists():
                try:
                    download_gcs_image(gcs_bucket, source_path, cache_path)
                except Exception as exc:
                    download_errors += 1
                    logger.warning("GCS download failed: %s — %s", source_path, exc)
                    continue
            source_path = str(cache_path)

        work_items.append(
            (
                source_path,
                str(split_img_dir),
                item["script_code"],
                item["skew_angle"],
                item["orientation_class"],
                item["degradation_profile"],
                item["output_idx"],
            )
        )

    return work_items, download_errors


def _process_split_items(
    split: str,
    work_items: list[tuple[Any, ...]],
    workers: int,
    labels: dict[str, dict[str, Any]],
    start_time: float,
    total: int,
    success_count: int,
    error_count: int,
) -> tuple[int, int]:
    """Process all work items for a single split in parallel.

    Args:
        split: Split name ("train", "val", or "test").
        work_items: Work item tuples for parallel processing.
        workers: Number of parallel workers.
        labels: Labels dict to update in-place.
        start_time: Overall start time for rate calculation.
        total: Total items across all splits for progress reporting.
        success_count: Running success count.
        error_count: Running error count.

    Returns:
        Tuple of (updated success_count, updated error_count).
    """
    split_start = time.monotonic()
    completed = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        for result in executor.map(_process_item_wrapper, work_items, chunksize=50):
            if result.success:
                labels[split][result.output_filename] = {
                    "angle": result.skew_angle,
                    "orientation": result.orientation_class,
                    "skew_bin": result.skew_bin,
                    "script": result.script_code,
                    "degradation": result.degradation_profile,
                    "source": Path(result.source_path).name,
                }
                success_count += 1
            else:
                error_count += 1
                logger.warning("Failed: %s — %s", result.source_path, result.error)

            completed += 1
            if completed % 2000 == 0:
                elapsed = time.monotonic() - start_time
                rate = (success_count + error_count) / max(elapsed, 0.01)
                logger.info(
                    "[%s] Progress: %d/%d total (%.1f img/s, %d errors)",
                    split,
                    success_count + error_count,
                    total,
                    rate,
                    error_count,
                )

    split_elapsed = time.monotonic() - split_start
    logger.info(
        "[%s] Complete: %d images in %.1fs (%.1f img/s)",
        split,
        completed,
        split_elapsed,
        completed / max(split_elapsed, 0.01),
    )

    return success_count, error_count


def execute_generation(
    plan: GenerationPlan,
    output_dir: Path,
    workers: int = 4,
    gcs_bucket: str | None = None,
    gcs_cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute the generation plan, writing images and labels.

    Args:
        plan: Generation plan from build_generation_plan.
        output_dir: Root output directory.
        workers: Number of parallel workers.
        gcs_bucket: If set, download source images from this GCS bucket.
        gcs_cache_dir: Local cache directory for GCS downloads.

    Returns:
        Summary statistics dict.
    """
    splits = ["train", "val", "test"]
    for split in splits:
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)

    if gcs_bucket and gcs_cache_dir:
        gcs_cache_dir.mkdir(parents=True, exist_ok=True)

    labels: dict[str, dict[str, Any]] = {s: {} for s in splits}
    success_count = 0
    error_count = 0
    start_time = time.monotonic()

    total = len(plan.items)
    items_by_split = {s: [it for it in plan.items if it["split"] == s] for s in splits}

    logger.info(
        "Processing %d images (train=%d, val=%d, test=%d) with %d workers",
        total,
        len(items_by_split["train"]),
        len(items_by_split["val"]),
        len(items_by_split["test"]),
        workers,
    )

    for split in splits:
        split_items = items_by_split[split]
        if not split_items:
            continue

        split_img_dir = output_dir / split / "images"
        work_items, dl_errors = _build_work_items_for_split(
            split_items,
            split_img_dir,
            gcs_bucket,
            gcs_cache_dir,
        )
        error_count += dl_errors

        success_count, error_count = _process_split_items(
            split,
            work_items,
            workers,
            labels,
            start_time,
            total,
            success_count,
            error_count,
        )

    # Write labels.json for each split
    for split in splits:
        if labels[split]:
            labels_path = output_dir / split / "labels.json"
            with labels_path.open("w") as f:
                json.dump(labels[split], f, indent=2)
            logger.info("Wrote %d labels to %s", len(labels[split]), labels_path)

    # Write generation manifest
    elapsed = time.monotonic() - start_time
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_images": success_count,
        "errors": error_count,
        "elapsed_seconds": round(elapsed, 1),
        "images_per_second": round(success_count / max(elapsed, 0.01), 1),
        "plan_stats": plan.stats,
        "train_labels_count": len(labels["train"]),
        "val_labels_count": len(labels["val"]),
        "test_labels_count": len(labels["test"]),
    }
    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Wrote manifest to %s", manifest_path)

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _discover_images(args: argparse.Namespace) -> dict[str, list[Any]]:
    """Discover source images from local filesystem or GCS.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Dict mapping script code to list of image paths/blob names.
    """
    if args.gcs_bucket:
        logger.info(
            "Discovering source images in gs://%s/%s", args.gcs_bucket, args.gcs_prefix
        )
        gcs_images = discover_gcs_images(args.gcs_bucket, args.gcs_prefix)
        return dict(gcs_images)

    logger.info("Discovering source images in %s", args.source_dir)
    return dict(discover_source_images(args.source_dir))


def _print_plan_statistics(
    stats: dict[str, Any],
    plan: GenerationPlan,
    held_back_scripts: list[str],
) -> None:
    """Print generation plan statistics to stdout.

    Args:
        stats: Plan statistics dict.
        plan: Generation plan with items.
        held_back_scripts: Scripts reserved for test only.
    """
    print("\n=== Generation Plan ===")
    print(f"Total images: {stats['total_images']:,}")
    print(
        f"Train: {stats['train_count']:,} | Val: {stats['val_count']:,} | Test: {stats['test_count']:,}"
    )
    print(
        f"  (includes {stats['held_back_test_images']:,} held-back script images in test)"
    )
    print(f"Scripts: {stats['scripts']}")
    print(f"Held-back (test only): {stats['held_back_scripts']}")
    print(f"Seed: {stats['seed']}")

    print("\n--- Script Allocation ---")
    held_set = set(held_back_scripts)
    for code, count in sorted(stats["per_script"].items(), key=lambda x: -x[1]):
        pct = 100 * count / stats["total_images"]
        held = " [TEST ONLY]" if code in held_set else ""
        print(f"  {code:5s}: {count:6,d} ({pct:5.1f}%){held}")

    print("\n--- Orientation Distribution ---")
    for orient, count in sorted(stats["orientation_distribution"].items()):
        pct = 100 * count / stats["total_images"]
        print(f"  {orient:4s} deg: {count:6,d} ({pct:5.1f}%)")

    print("\n--- Degradation Distribution ---")
    for prof, count in sorted(
        stats["degradation_distribution"].items(), key=lambda x: -x[1]
    ):
        pct = 100 * count / stats["total_images"]
        print(f"  {prof:12s}: {count:6,d} ({pct:5.1f}%)")

    print("\n--- Angle Distribution ---")
    for name, count in stats["angle_distribution"].items():
        pct = 100 * count / stats["total_images"]
        print(f"  {name:20s}: {count:6,d} ({pct:5.1f}%)")

    # Bin coverage check
    bin_counts = [0] * 42
    for item in plan.items:
        bin_idx = angle_to_bin(item["skew_angle"])
        bin_counts[bin_idx] += 1
    empty_bins = sum(1 for c in bin_counts if c == 0)
    min_bin = min(bin_counts)
    max_bin = max(bin_counts)
    print("\n--- Bin Coverage ---")
    print(f"  42 bins: min={min_bin}, max={max_bin}, empty={empty_bins}")


def main() -> None:
    """CLI entry point for skew dataset generation."""
    parser = argparse.ArgumentParser(
        description="Derive skew training dataset from synth-multiscript-250K",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    source_group = parser.add_argument_group("source (choose one)")
    source_group.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Local directory of synth-multiscript dataset (with script subdirs)",
    )
    source_group.add_argument(
        "--gcs-bucket",
        type=str,
        default=None,
        help="GCS bucket name (e.g. image_detection_b)",
    )
    source_group.add_argument(
        "--gcs-prefix",
        type=str,
        default="synthetic_multiscript/",
        help="GCS prefix within bucket (default: synthetic_multiscript/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for skew training dataset",
    )
    parser.add_argument(
        "--total-images",
        type=int,
        default=70000,
        help="Total images for train+val+test splits (default: 70000)",
    )
    parser.add_argument(
        "--val-fraction",
        type=float,
        default=0.10,
        help="Fraction for validation split (default: 0.10)",
    )
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=0.10,
        help="Fraction for test split from seen scripts (default: 0.10)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "--held-back-scripts",
        nargs="*",
        default=DEFAULT_HELD_BACK_SCRIPTS,
        help="Scripts reserved for test only (default: Geor Armn Hang)",
    )
    parser.add_argument(
        "--held-back-per-script",
        type=int,
        default=HELD_BACK_IMAGES_PER_SCRIPT,
        help="Images per held-back script in test (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show plan statistics without processing images",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if not args.source_dir and not args.gcs_bucket:
        parser.error("Either --source-dir or --gcs-bucket is required")

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Step 1: Discover source images
    images_by_script = _discover_images(args)
    if not images_by_script:
        logger.error("No images found in source")
        sys.exit(1)

    total_source = sum(len(imgs) for imgs in images_by_script.values())
    logger.info(
        "Found %d source images across %d scripts: %s",
        total_source,
        len(images_by_script),
        ", ".join(f"{k}({len(v)})" for k, v in sorted(images_by_script.items())),
    )

    # Step 2: Build generation plan
    logger.info("Building generation plan for %d images...", args.total_images)
    plan = build_generation_plan(
        images_by_script=images_by_script,
        total_images=args.total_images,
        val_fraction=args.val_fraction,
        test_fraction=args.test_fraction,
        seed=args.seed,
        held_back_scripts=args.held_back_scripts,
        held_back_per_script=args.held_back_per_script,
    )

    if not plan.items:
        logger.error("Generation plan is empty. Check source directory structure.")
        sys.exit(1)

    _print_plan_statistics(plan.stats, plan, args.held_back_scripts)

    if args.dry_run:
        print("\n[DRY RUN] No images processed. Use without --dry-run to generate.")
        return

    # Step 3: Execute generation
    print(f"\nGenerating {plan.stats['total_images']:,} images to {args.output_dir}")
    gcs_cache = args.output_dir / ".gcs_cache" if args.gcs_bucket else None
    result = execute_generation(
        plan=plan,
        output_dir=args.output_dir,
        workers=args.workers,
        gcs_bucket=args.gcs_bucket,
        gcs_cache_dir=gcs_cache,
    )

    print("\n=== Generation Complete ===")
    print(f"Total: {result['total_images']:,} images")
    print(f"Errors: {result['errors']}")
    print(
        f"Time: {result['elapsed_seconds']:.1f}s ({result['images_per_second']:.1f} img/s)"
    )
    print(
        f"Train: {result['train_labels_count']:,} | Val: {result['val_labels_count']:,} | Test: {result['test_labels_count']:,}"
    )
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
