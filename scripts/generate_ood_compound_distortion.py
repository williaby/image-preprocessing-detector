#!/usr/bin/env python3
"""Generate OOD compound-distortion images (Phase 3b, Recipe 5).

Applies ≥5 simultaneous distortions to clean DocLayNet train-split images,
creating "multiply-distorted" samples with ~0% training coverage.
Target: 700 images registered in ood_registry.jsonl under ood_degradation.

Distortion stack (ALL applied together):
  1. Gaussian blur (sigma 1.5–3.0)
  2. Gaussian noise (std 15–30)
  3. Low contrast (factor 0.4–0.7, with mean shift)
  4. JPEG compression (quality 20–35)
  5. Illumination gradient (one bright corner, darkens opposite)
  6. Ink bleed (morphological dilation on binarised text layer)

IQA label ranges:
  blur_score       0.10–0.30  (heavy blur)
  noise_score      0.15–0.35  (visible noise)
  contrast_score   0.10–0.30  (low contrast)
  compression_score 0.05–0.25 (heavy JPEG artefacts)
  overall_quality  0.10–0.30  (all degradations active)

Usage:
    # Dry run
    uv run python scripts/generate_ood_compound_distortion.py --dry-run

    # Generate 700 images
    uv run python scripts/generate_ood_compound_distortion.py \\
        --doclaynet-dir /mnt/e/image_detection/01_base_data/documents/doclaynet \\
        --output-dir /mnt/e/image_detection/ood/degradation \\
        --n-images 700
"""
from __future__ import annotations

import io
import json
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


def _hashes_from_bytes(data: bytes) -> tuple[str, str]:
    """Compute (sha256_hex, phash_hex) directly from image bytes."""
    import hashlib

    import imagehash
    from PIL import Image

    sha256 = hashlib.sha256(data).hexdigest()
    img = Image.open(io.BytesIO(data))
    ph = imagehash.phash(img)
    bits = ph.hash.flatten()
    byte_vals = [int("".join(str(int(b)) for b in bits[i : i + 8]), 2) for i in range(0, 64, 8)]
    phash_hex = bytes(byte_vals).hex()
    return sha256, phash_hex

# Distinct from training generator seeds (plan: OOD_SEED_NAMESPACE = 0xDEADBEEF_0DD5AFEC)
_OOD_RNG_SEED = 0xDEAD_BEEF_0DD5_AFEC & 0xFFFFFFFF  # 32-bit slice for Python RNG

_DOCLAYNET_DEFAULT = Path(
    "/mnt/e/image_detection/01_base_data/documents/doclaynet"
)
_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/degradation")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")


def _apply_compound_distortion(
    img_bgr: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, dict[str, float]]:
    """Apply all 6 distortions and return (distorted_bgr, iqa_labels).

    Returns the distorted image as BGR uint8 and a dict with approximate
    IQA label values for registration metadata.
    """
    out = img_bgr.astype(np.float32)
    h, w = out.shape[:2]

    # 1. Gaussian blur
    sigma = rng.uniform(1.5, 3.0)
    k = int(2 * round(3 * sigma) + 1) | 1  # ensure odd kernel
    blurred = cv2.GaussianBlur(out, (k, k), sigma)
    blur_score = max(0.10, min(0.30, 0.30 - (sigma - 1.5) / 1.5 * 0.15))

    # 2. Gaussian noise
    noise_std = rng.uniform(15.0, 30.0)
    noise = np.random.default_rng(int(sigma * 1e6)).normal(0, noise_std, out.shape).astype(np.float32)
    noisy = np.clip(blurred + noise, 0, 255)
    noise_score = max(0.15, min(0.35, noise_std / 30.0 * 0.35))

    # 3. Low contrast (reduce dynamic range, shift toward mid-gray)
    factor = rng.uniform(0.4, 0.7)
    mid = 128.0
    low_contrast = np.clip((noisy - mid) * factor + mid, 0, 255)
    contrast_score = max(0.10, min(0.30, factor * 0.30))

    # 4. Illumination gradient (brighten one corner, darken opposite)
    corner = rng.randint(0, 3)
    xs = np.linspace(0, 1, w, dtype=np.float32)
    ys = np.linspace(0, 1, h, dtype=np.float32)
    xg, yg = np.meshgrid(xs, ys)
    if corner == 0:
        grad = xg * yg  # bright at (0,0)
    elif corner == 1:
        grad = (1 - xg) * yg  # bright at (w,0)
    elif corner == 2:
        grad = xg * (1 - yg)  # bright at (0,h)
    else:
        grad = (1 - xg) * (1 - yg)  # bright at (w,h)
    grad_strength = rng.uniform(40.0, 80.0)
    illum = np.clip(low_contrast + (grad[..., None] - 0.5) * grad_strength, 0, 255)

    # 5. Ink bleed (dilate dark pixels, simulating ink spread)
    gray = cv2.cvtColor(illum.astype(np.uint8), cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    bleed_mask = cv2.dilate(binary, kernel, iterations=1)
    bleed_mask_3ch = (bleed_mask > 0)[..., None].astype(np.float32)
    ink_bled = np.clip(illum - bleed_mask_3ch * 40.0, 0, 255)

    out_uint8 = ink_bled.astype(np.uint8)

    # 6. JPEG compression
    jpeg_quality = rng.randint(20, 35)
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
    _, encoded = cv2.imencode(".jpg", out_uint8, encode_params)
    out_final = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    compression_score = max(0.05, min(0.25, (35 - jpeg_quality) / 15.0 * 0.20))

    # Approximate overall_quality as mean of all degradation scores
    overall = (blur_score + noise_score + contrast_score + compression_score) / 4.0

    iqa = {
        "blur_score": round(blur_score, 3),
        "noise_score": round(noise_score, 3),
        "contrast_score": round(contrast_score, 3),
        "compression_score": round(compression_score, 3),
        "overall_quality": round(overall, 3),
    }
    return out_final, iqa


def _load_doclaynet_train_pool(doclaynet_dir: Path) -> list[Path]:
    """Return list of image paths from DocLayNet train split only."""
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
@click.option("--n-images", default=700, show_default=True, help="Target image count.")
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    doclaynet_dir: Path,
    output_dir: Path,
    registry: Path,
    n_images: int,
    dry_run: bool,
) -> None:
    """Generate compound-distortion OOD images (Phase 3b, Recipe 5).

    Sources clean DocLayNet train-split pages and applies 6 simultaneous
    distortions to create samples with ~0% training coverage for the
    multiply-distorted wild condition.
    """
    rng = random.Random(_OOD_RNG_SEED)
    np.random.seed(_OOD_RNG_SEED & 0xFFFFFFFF)

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

        distorted, iqa_labels = _apply_compound_distortion(img_bgr, rng)

        out_name = f"cmpd_{n_registered:05d}.jpg"
        out_path = output_dir / out_name

        # Encode to bytes for hashing
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 92]
        _, encoded = cv2.imencode(".jpg", distorted, encode_params)
        img_bytes = encoded.tobytes()

        sha256, phash = _hashes_from_bytes(img_bytes)

        # Dedup check
        if sha256 in ood_sha256s:
            n_skipped_dup += 1
            continue
        if any(hamming_distance(phash, p) <= 5 for p in known_phashes):
            n_skipped_dup += 1
            continue

        if not dry_run:
            out_path.write_bytes(img_bytes)

        gt = build_ground_truth_template()
        gt.update(iqa_labels)
        gt["capture_method"] = "synthetic_augmentation"

        from datetime import date

        entry = {
            "sha256": sha256,
            "phash": phash,
            "source_path": str(out_path),
            "registered_date": date.today().isoformat(),
            "ood_categories": ["ood_degradation"],
            "reason": (
                f"Compound distortion (blur+noise+contrast+JPEG+illumination+inkbleed) "
                f"from DocLayNet train: {src_path.name}; "
                "wild condition 'multiply_distorted' — ~0% training coverage"
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
                "generator_script": "generate_ood_compound_distortion.py",
                "recipe": "phase3b_recipe5",
                "seed": _OOD_RNG_SEED,
                "n_distortions": 6,
                "wild_condition": "multiply_distorted",
            },
        }

        if not dry_run:
            append_registry_entry(entry, registry)

        ood_sha256s.add(sha256)
        known_phashes.append(phash)
        n_registered += 1

    log_dry_run_summary(
        sub_command="generate-ood-compound-distortion",
        candidates=n_cands,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=n_registered,
        dry_run=dry_run,
    )
    click.echo(f"  Compound distortion OOD: {n_registered}/{n_images}")


if __name__ == "__main__":
    main()
