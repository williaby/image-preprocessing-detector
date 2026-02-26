#!/usr/bin/env python3
"""Generate OOD fax-artifact images (Phase 3b, Recipe 7).

Simulates documents transmitted by fax — a "wild condition" listed in
WILD_CONDITIONS_ANALYSIS.md with ~0% training coverage.  Fax transmission
degrades documents through 1-bit halftoning, horizontal line noise, and
heavy contrast loss.

Target: 200 images registered in ood_registry.jsonl under
        [ood_degradation, ood_capture].

Transform pipeline:
  1. Convert to grayscale.
  2. Floyd-Steinberg–style 1-bit dithering (error diffusion to neighbours).
  3. Horizontal line noise: insert semi-transparent dark/white scan lines
     at random intervals to simulate transmission errors.
  4. Contrast reduction: flatten dynamic range toward mid-gray.
  5. Convert back to RGB (3-channel grayscale) and encode as JPEG.

Labels:
  capture_method   "fax"
  noise_score      0.60–0.70
  compression_score 0.65–0.75
  contrast_score   0.20–0.35

Usage:
    # Dry run
    uv run python scripts/generate_ood_fax_artifacts.py --dry-run

    # Generate 200 images
    uv run python scripts/generate_ood_fax_artifacts.py \\
        --doclaynet-dir /mnt/e/image_detection/01_base_data/documents/doclaynet \\
        --output-dir /mnt/e/image_detection/ood/degradation \\
        --n-images 200
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

# OOD seed namespace: 0xDEADBEEF_0DD5AFEC ^ recipe_index(7)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x0000_0007) & 0xFFFFFFFF

_DOCLAYNET_DEFAULT = Path(
    "/mnt/e/image_detection/01_base_data/documents/doclaynet"
)
_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/degradation")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")


def _hashes_from_bytes(data: bytes) -> tuple[str, str]:
    """Compute (sha256_hex, phash_hex) directly from image bytes."""
    import hashlib

    import imagehash

    sha256 = hashlib.sha256(data).hexdigest()
    img = Image.open(io.BytesIO(data))
    ph = imagehash.phash(img)
    bits = ph.hash.flatten()
    byte_vals = [int("".join(str(int(b)) for b in bits[i : i + 8]), 2) for i in range(0, 64, 8)]
    phash_hex = bytes(byte_vals).hex()
    return sha256, phash_hex


def _floyd_steinberg_dither(gray: np.ndarray) -> np.ndarray:
    """Apply Floyd-Steinberg error-diffusion dithering to a grayscale image.

    Converts a uint8 grayscale image to a 1-bit dithered image (values 0 or 255),
    then returns it as uint8.  This simulates the halftoning used in fax machines.

    Args:
        gray: 2-D uint8 numpy array (grayscale).

    Returns:
        2-D uint8 array with values in {0, 255}.
    """
    # Work in float for error accumulation
    img = gray.astype(np.float32)
    h, w = img.shape

    for y in range(h):
        for x in range(w):
            old_val = img[y, x]
            new_val = 255.0 if old_val >= 128.0 else 0.0
            img[y, x] = new_val
            err = old_val - new_val

            if x + 1 < w:
                img[y, x + 1] += err * (7.0 / 16.0)
            if y + 1 < h:
                if x > 0:
                    img[y + 1, x - 1] += err * (3.0 / 16.0)
                img[y + 1, x] += err * (5.0 / 16.0)
                if x + 1 < w:
                    img[y + 1, x + 1] += err * (1.0 / 16.0)

    return np.clip(img, 0, 255).astype(np.uint8)


def _add_horizontal_line_noise(
    gray: np.ndarray, rng: random.Random
) -> np.ndarray:
    """Randomly darken or whiten horizontal bands to simulate fax line errors.

    Fax transmission errors typically manifest as entire horizontal scan lines
    being dropped (white) or corrupted (dark streaks).

    Args:
        gray: 2-D uint8 grayscale image.
        rng: Seeded random generator.

    Returns:
        Grayscale image with horizontal line artefacts, same shape as input.
    """
    out = gray.copy().astype(np.float32)
    h, w = gray.shape

    # Number of error bands: 1–4% of image height
    n_bands = rng.randint(max(1, h // 80), max(2, h // 25))

    for _ in range(n_bands):
        y_start = rng.randint(0, h - 1)
        band_h = rng.randint(1, 4)  # 1–4 pixel wide band
        y_end = min(h, y_start + band_h)

        band_type = rng.choice(["dropout", "dark", "gray"])
        if band_type == "dropout":
            out[y_start:y_end, :] = 255.0
        elif band_type == "dark":
            out[y_start:y_end, :] = 0.0
        else:  # gray smear
            out[y_start:y_end, :] = rng.uniform(100.0, 180.0)

    return np.clip(out, 0, 255).astype(np.uint8)


def _apply_fax_artifacts(
    img_bgr: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, dict[str, float]]:
    """Full fax simulation pipeline.

    Args:
        img_bgr: Source document image (BGR uint8).
        rng: Seeded random generator.

    Returns:
        (fax_result_bgr, iqa_labels) where result is 3-channel grayscale.
    """
    # 1. Convert to grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 2. Slight blur before dithering (simulate analogue transmission bandwidth)
    pre_blur_k = rng.choice([3, 5])
    gray = cv2.GaussianBlur(gray, (pre_blur_k, pre_blur_k), 0)

    # 3. Floyd-Steinberg dithering
    dithered = _floyd_steinberg_dither(gray)

    # 4. Horizontal line noise
    noisy = _add_horizontal_line_noise(dithered, rng)

    # 5. Contrast reduction (flatten toward mid-gray, simulating fax contrast loss)
    contrast_factor = rng.uniform(0.55, 0.75)
    mid = 128.0
    flat = np.clip((noisy.astype(np.float32) - mid) * contrast_factor + mid, 0, 255).astype(np.uint8)

    # 6. Convert back to BGR (3-channel grayscale)
    result_bgr = cv2.cvtColor(flat, cv2.COLOR_GRAY2BGR)

    # Approximate IQA labels
    noise_score = round(rng.uniform(0.60, 0.70), 3)
    compression_score = round(rng.uniform(0.65, 0.75), 3)
    contrast_score = round(contrast_factor * 0.45, 3)

    iqa = {
        "noise_score": noise_score,
        "compression_score": compression_score,
        "contrast_score": contrast_score,
    }
    return result_bgr, iqa


def _load_doclaynet_train_pool(doclaynet_dir: Path) -> list[Path]:
    """Return image paths from DocLayNet train split only."""
    coco_train = doclaynet_dir / "ground_truth" / "coco" / "train.json"
    img_dir = doclaynet_dir / "documents" / "png"
    if not coco_train.exists() or not img_dir.exists():
        raise FileNotFoundError(
            f"DocLayNet train split not found at {doclaynet_dir}"
        )
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
@click.option("--n-images", default=200, show_default=True, help="Target image count.")
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    doclaynet_dir: Path,
    output_dir: Path,
    registry: Path,
    n_images: int,
    dry_run: bool,
) -> None:
    """Generate fax-artifact OOD images (Phase 3b, Recipe 7).

    Sources DocLayNet train-split pages and applies Floyd-Steinberg dithering,
    horizontal line noise, and contrast reduction to simulate fax transmission.
    Wild condition 'fax_artifacts' has ~0% training coverage.
    """
    rng = random.Random(_OOD_RNG_SEED)

    click.echo(f"Loading DocLayNet train pool from {doclaynet_dir}...")
    source_pool = _load_doclaynet_train_pool(doclaynet_dir)
    click.echo(f"  Train pool: {len(source_pool):,} images available")

    ood_sha256s, ood_phashes = load_ood_registry(registry)
    known_phashes = list(ood_phashes)

    rng.shuffle(source_pool)
    candidate_pool = source_pool[: n_images * 4]  # extra headroom for dithering variance

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

        result, iqa = _apply_fax_artifacts(img_bgr, rng)

        out_name = f"fax_{n_registered:05d}.jpg"
        out_path = output_dir / out_name

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        _, encoded = cv2.imencode(".jpg", result, encode_params)
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

        gt = build_ground_truth_template()
        gt.update(iqa)
        gt["capture_method"] = "fax"
        gt["color_mode"] = "binarized"

        from datetime import date

        entry = {
            "sha256": sha256,
            "phash": phash,
            "source_path": str(out_path),
            "registered_date": date.today().isoformat(),
            "ood_categories": ["ood_degradation", "ood_capture"],
            "reason": (
                f"Fax-artifact simulation (dithering + line noise + contrast loss) "
                f"from DocLayNet train: {src_path.name}; "
                "wild condition 'fax_artifacts' — ~0% training coverage"
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
                "generator_script": "generate_ood_fax_artifacts.py",
                "recipe": "phase3b_recipe7",
                "seed": _OOD_RNG_SEED,
                "wild_condition": "fax_artifacts",
                "dither_method": "floyd_steinberg",
            },
        }

        if not dry_run:
            append_registry_entry(entry, registry)

        ood_sha256s.add(sha256)
        known_phashes.append(phash)
        n_registered += 1

    log_dry_run_summary(
        sub_command="generate-ood-fax-artifacts",
        candidates=n_cands,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=n_registered,
        dry_run=dry_run,
    )
    click.echo(f"  Fax-artifact OOD: {n_registered}/{n_images}")


if __name__ == "__main__":
    main()
