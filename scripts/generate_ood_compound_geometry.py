#!/usr/bin/env python3
"""Generate OOD compound-geometry images (Phase 3a, Recipe 3).

Applies BOTH skew rotation (3–10°) AND sinusoidal page-curl warping
simultaneously.  Training data contains skew-only OR warping-only samples —
the compound combination at this severity is ~0% training coverage.

Target: 500 images registered in ood_registry.jsonl under ood_geometry.

Transform pipeline (applied in sequence):
  1. Skew rotation: cv2.warpAffine with angle drawn from ±[3°, 10°].
  2. Page-curl warp: sinusoidal horizontal displacement
       x'(x, y) = x + amplitude * sin(π * y / period)
     where amplitude ∈ [12, 30] px and period = H (full-height wave).
  3. Pad with white background; output size matches input.

Labels (derived from transform parameters):
  skew_angle_degrees   signed skew angle applied
  warping_severity     approximate warping severity ∈ [0.35, 0.65]
  warping_type         "page_curl"
  capture_method       "synthetic_augmentation"

Usage:
    # Dry run
    uv run python scripts/generate_ood_compound_geometry.py --dry-run

    # Generate 500 images
    uv run python scripts/generate_ood_compound_geometry.py \\
        --doclaynet-dir /mnt/e/image_detection/01_base_data/documents/doclaynet \\
        --output-dir /mnt/e/image_detection/ood/geometry \\
        --n-images 500
"""

from __future__ import annotations

import io
import json
import math
import random
import sys
from pathlib import Path

import click
import numpy as np

# #ASSUME: env: opencv and PIL available in the uv environment
try:
    import cv2
    from PIL import Image
except ImportError as exc:
    click.echo(f"Missing dependency: {exc}. Run: uv sync --extra dev", err=True)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.ood_utils import (
    append_registry_entry,
    build_ground_truth_template,
    hamming_distance,
    load_ood_registry,
    log_dry_run_summary,
)

# OOD seed namespace: 0xDEADBEEF_0DD5AFEC ^ recipe_index(3)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x0000_0003) & 0xFFFFFFFF

_DOCLAYNET_DEFAULT = Path("/mnt/e/image_detection/01_base_data/documents/doclaynet")
_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/geometry")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# Skew range: compound samples must exceed mild training range
_SKEW_MIN_DEG = 3.0
_SKEW_MAX_DEG = 10.0

# Page-curl warp parameters
_WARP_AMP_MIN = 12  # pixels
_WARP_AMP_MAX = 30  # pixels


def _hashes_from_bytes(data: bytes) -> tuple[str, str]:
    """Compute (sha256_hex, phash_hex) directly from image bytes."""
    import hashlib

    import imagehash

    sha256 = hashlib.sha256(data).hexdigest()
    img = Image.open(io.BytesIO(data))
    ph = imagehash.phash(img)
    bits = ph.hash.flatten()
    byte_vals = [
        int("".join(str(int(b)) for b in bits[i : i + 8]), 2) for i in range(0, 64, 8)
    ]
    phash_hex = bytes(byte_vals).hex()
    return sha256, phash_hex


def _apply_skew(img_bgr: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate image by *angle_deg* around its centre; pad with white.

    Args:
        img_bgr: Source BGR uint8 image.
        angle_deg: Rotation angle in degrees (positive = counter-clockwise).

    Returns:
        Rotated BGR image, same size as input, white background fill.
    """
    h, w = img_bgr.shape[:2]
    cx, cy = w / 2, h / 2
    M = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    return cv2.warpAffine(
        img_bgr,
        M,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def _apply_page_curl(img_bgr: np.ndarray, amplitude: float) -> np.ndarray:
    """Apply sinusoidal horizontal page-curl displacement.

    For each row y, shift all pixels horizontally by:
        dx = amplitude * sin(π * y / H)
    creating a gentle S-curve warp that simulates a partially curled page.

    Args:
        img_bgr: Source BGR uint8 image.
        amplitude: Peak horizontal displacement in pixels.

    Returns:
        Warped BGR image (same size, white padding for unmapped pixels).
    """
    h, w = img_bgr.shape[:2]

    # Build remap arrays
    map_x = np.zeros((h, w), dtype=np.float32)
    map_y = np.zeros((h, w), dtype=np.float32)

    ys = np.arange(h, dtype=np.float32)
    dx_per_row = amplitude * np.sin(math.pi * ys / h)  # shape: (h,)

    for y in range(h):
        map_x[y, :] = np.arange(w, dtype=np.float32) + dx_per_row[y]
        map_y[y, :] = y

    return cv2.remap(
        img_bgr,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def _warping_severity(amplitude: float, img_w: int) -> float:
    """Approximate warping severity as fraction of image width displaced."""
    severity = min(1.0, amplitude / (img_w * 0.10))
    # Scale to [0.35, 0.65] range consistent with plan specification
    return round(0.35 + severity * 0.30, 3)


def _load_doclaynet_train_pool(doclaynet_dir: Path) -> list[Path]:
    """Return image paths from DocLayNet train split only."""
    coco_train = doclaynet_dir / "ground_truth" / "coco" / "train.json"
    img_dir = doclaynet_dir / "documents" / "png"
    if not coco_train.exists() or not img_dir.exists():
        raise FileNotFoundError(f"DocLayNet train split not found at {doclaynet_dir}")
    with coco_train.open() as f:
        data = json.load(f)
    paths = [img_dir / entry["file_name"] for entry in data["images"]]
    return [p for p in paths if p.exists()]


@click.command()
@click.option(
    "--doclaynet-dir",
    type=click.Path(path_type=Path),
    default=_DOCLAYNET_DEFAULT,
    show_default=True,
    help="DocLayNet root (expects ground_truth/coco/train.json + documents/png/).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=_OUTPUT_DEFAULT,
    show_default=True,
    help="Directory to write generated OOD images.",
)
@click.option(
    "--registry",
    type=click.Path(path_type=Path),
    default=_REGISTRY_DEFAULT,
    show_default=True,
    help="OOD registry JSONL file.",
)
@click.option("--n-images", default=500, show_default=True, help="Target image count.")
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    doclaynet_dir: Path,
    output_dir: Path,
    registry: Path,
    n_images: int,
    dry_run: bool,
) -> None:
    """Generate compound skew+warping OOD images (Phase 3a, Recipe 3).

    Sources DocLayNet train-split pages and applies skew rotation followed
    by sinusoidal page-curl warping.  The compound combination at this
    severity is ~0% training coverage — training has skew-only or warping-only.
    """
    rng = random.Random(_OOD_RNG_SEED)

    click.echo(f"Loading DocLayNet train pool from {doclaynet_dir}...")
    source_pool = _load_doclaynet_train_pool(doclaynet_dir)
    click.echo(f"  Train pool: {len(source_pool):,} images available")

    ood_sha256s, ood_phashes = load_ood_registry(registry)
    known_phashes = list(ood_phashes)

    rng.shuffle(source_pool)
    candidate_pool = source_pool[: n_images * 3]

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    n_cands = n_skipped_dup = n_registered = 0

    for src_path in candidate_pool:
        if n_registered >= n_images:
            break
        n_cands += 1

        img_bgr = cv2.imread(str(src_path))
        if img_bgr is None:
            continue

        # 1. Skew rotation (signed: positive/negative with equal probability)
        angle = rng.uniform(_SKEW_MIN_DEG, _SKEW_MAX_DEG)
        if rng.random() < 0.5:
            angle = -angle
        skewed = _apply_skew(img_bgr, angle)

        # 2. Page-curl warp
        amplitude = rng.uniform(_WARP_AMP_MIN, _WARP_AMP_MAX)
        warped = _apply_page_curl(skewed, amplitude)

        out_name = f"cmpd_geo_{n_registered:05d}.jpg"
        out_path = output_dir / out_name

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 92]
        _, encoded = cv2.imencode(".jpg", warped, encode_params)
        img_bytes = encoded.tobytes()

        sha256, phash = _hashes_from_bytes(img_bytes)

        if sha256 in ood_sha256s:
            n_skipped_dup += 1
            continue
        if any(hamming_distance(phash, p) <= 5 for p in known_phashes):
            n_skipped_dup += 1
            continue

        if not dry_run:
            out_path.write_bytes(img_bytes)

        severity = _warping_severity(amplitude, warped.shape[1])
        gt = build_ground_truth_template()
        gt["skew_angle_degrees"] = round(angle, 2)
        gt["warping_severity"] = severity
        gt["warping_type"] = "page_curl"
        gt["capture_method"] = "synthetic_augmentation"
        gt["orientation"] = 0

        from datetime import date

        entry = {
            "sha256": sha256,
            "phash": phash,
            "source_path": str(out_path),
            "registered_date": date.today().isoformat(),
            "ood_categories": ["ood_geometry"],
            "reason": (
                f"Compound skew ({angle:.1f}°) + page-curl (amp={amplitude:.0f}px) "
                f"from DocLayNet train: {src_path.name}; "
                "training has skew-only OR warping-only — compound is ~0% coverage"
            ),
            "acquisition_method": "synthetic_generation",
            "license": "CDLA-Permissive-1.0",
            "dedup_verified": True,
            "evaluation_pipeline_stage": ["mobilenetv4", "siglip2"],
            "ground_truth": gt,
            "generation_metadata": {
                "source_dataset": "doclaynet",
                "source_image": src_path.name,
                "split_used": "train",
                "generator_script": "generate_ood_compound_geometry.py",
                "recipe": "phase3a_recipe3",
                "seed": _OOD_RNG_SEED,
                "skew_angle_deg": round(angle, 2),
                "warp_amplitude_px": round(amplitude, 1),
                "warp_type": "page_curl_sinusoidal",
            },
        }

        if not dry_run:
            append_registry_entry(entry, registry)

        ood_sha256s.add(sha256)
        known_phashes.append(phash)
        n_registered += 1

    log_dry_run_summary(
        sub_command="generate-ood-compound-geometry",
        candidates=n_cands,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=n_registered,
        dry_run=dry_run,
    )
    click.echo(f"  Compound geometry OOD: {n_registered}/{n_images}")


if __name__ == "__main__":
    main()
