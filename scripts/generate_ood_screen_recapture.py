#!/usr/bin/env python3
"""Generate OOD screen-recapture moiré images (Phase 3b, Recipe 6).

Simulates documents photographed off a screen — a "wild condition" with ~0%
training coverage.  The pipeline introduces the characteristic moiré fringe
artefacts produced when a camera's sensor grid and the screen's pixel grid
interfere.

Target: 300 images registered in ood_registry.jsonl under
        [ood_degradation, ood_capture].

Transform pipeline:
  1. Downsample source image to ~screen resolution (scale factor 0.40–0.55).
  2. Add sinusoidal RGB moiré pattern at a frequency slightly different from
     the sampling grid (horizontal + vertical stripes at 5–10° offset).
  3. Apply slight perspective rotation (15–25°) to simulate off-angle capture.
  4. Bicubic upsample back to original size (introduces interpolation blur).

Labels:
  capture_method      "screen_recapture"
  blur_score          0.30–0.40  (interpolation softening)
  compression_score   0.40–0.50  (JPEG + moiré information loss)
  noise_score         0.20–0.30  (moiré as structured noise)

Usage:
    # Dry run
    uv run python scripts/generate_ood_screen_recapture.py --dry-run

    # Generate 300 images
    uv run python scripts/generate_ood_screen_recapture.py \\
        --doclaynet-dir /mnt/e/image_detection/01_base_data/documents/doclaynet \\
        --output-dir /mnt/e/image_detection/ood/degradation \\
        --n-images 300
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

# OOD seed namespace: 0xDEADBEEF_0DD5AFEC ^ recipe_index(6)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x0000_0006) & 0xFFFFFFFF

_DOCLAYNET_DEFAULT = Path(
    "/mnt/e/image_detection/01_base_data/documents/doclaynet"
)
_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/degradation")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# Downsample scale (simulates screen pixel density relative to document)
_SCALE_LO = 0.40
_SCALE_HI = 0.55

# Moiré stripe frequency range (cycles per pixel in downsampled space)
_MOIRE_FREQ_LO = 0.08
_MOIRE_FREQ_HI = 0.18
_MOIRE_AMPLITUDE = 18.0  # intensity oscillation amplitude (0–255 scale)

# Recapture angle range (degrees from vertical)
_ANGLE_LO = 15.0
_ANGLE_HI = 25.0


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


def _add_moire_pattern(
    img_float: np.ndarray, freq: float, angle_deg: float, amplitude: float
) -> np.ndarray:
    """Overlay sinusoidal moiré stripes at *angle_deg* rotation.

    The pattern simulates RGB subpixel interference by shifting the R and B
    channels slightly relative to G, which is characteristic of screen recapture.

    Args:
        img_float: Source image as float32 (0–255 range).
        freq: Stripe frequency in cycles-per-pixel.
        angle_deg: Stripe orientation angle in degrees.
        amplitude: Peak intensity oscillation amplitude.

    Returns:
        Image with moiré overlay, same shape/dtype as input.
    """
    h, w = img_float.shape[:2]
    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    xg, yg = np.meshgrid(xs, ys)

    # Rotate coordinates by angle
    rad = math.radians(angle_deg)
    proj = xg * math.cos(rad) + yg * math.sin(rad)

    # Sinusoidal pattern
    stripe = amplitude * np.sin(2 * math.pi * freq * proj)  # shape (H, W)

    # Apply to each channel with slight phase offset for RGB fringing
    out = img_float.copy()
    out[..., 0] = np.clip(out[..., 0] + stripe * 0.6, 0, 255)   # B
    out[..., 1] = np.clip(out[..., 1] + stripe, 0, 255)          # G
    out[..., 2] = np.clip(out[..., 2] + stripe * 0.7, 0, 255)    # R
    return out


def _apply_slight_perspective(
    img_bgr: np.ndarray, tilt_deg: float, rng: random.Random
) -> np.ndarray:
    """Apply a mild perspective transform simulating off-angle capture.

    One side of the document is shrunk as if viewed from an angle.

    Args:
        img_bgr: Source BGR uint8 image.
        tilt_deg: Apparent tilt angle (15–25°), used to compute shrink ratio.
        rng: Random generator for axis selection.

    Returns:
        Perspective-warped BGR image (same size, white background).
    """
    h, w = img_bgr.shape[:2]
    shrink = math.cos(math.radians(tilt_deg))

    # Randomly tilt left/right or top/bottom
    axis = rng.choice(["horizontal", "vertical"])

    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    if axis == "horizontal":
        offset = int((1 - shrink) * h * 0.5)
        dst_pts = np.float32([[0, offset], [w, 0], [w, h], [0, h - offset]])
    else:
        offset = int((1 - shrink) * w * 0.5)
        dst_pts = np.float32([[offset, 0], [w - offset, 0], [w, h], [0, h]])

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(
        img_bgr, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def _simulate_screen_recapture(
    img_bgr: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, dict[str, float]]:
    """Full screen-recapture pipeline.

    Args:
        img_bgr: Clean source document image (BGR uint8).
        rng: Seeded random generator for reproducibility.

    Returns:
        Tuple of (processed_bgr_uint8, approximate_iqa_labels).
    """
    h, w = img_bgr.shape[:2]

    # 1. Downsample to simulate screen pixel density
    scale = rng.uniform(_SCALE_LO, _SCALE_HI)
    small_w = max(64, int(w * scale))
    small_h = max(64, int(h * scale))
    small = cv2.resize(img_bgr, (small_w, small_h), interpolation=cv2.INTER_AREA)

    # 2. Add moiré pattern in downsampled space
    freq = rng.uniform(_MOIRE_FREQ_LO, _MOIRE_FREQ_HI)
    stripe_angle = rng.uniform(5.0, 15.0)
    small_f = small.astype(np.float32)
    moire_f = _add_moire_pattern(small_f, freq, stripe_angle, _MOIRE_AMPLITUDE)

    # 3. Upsample back to original size (bicubic — introduces blur)
    recaptured = cv2.resize(
        moire_f.astype(np.uint8), (w, h), interpolation=cv2.INTER_CUBIC
    )

    # 4. Apply perspective tilt
    tilt = rng.uniform(_ANGLE_LO, _ANGLE_HI)
    result = _apply_slight_perspective(recaptured, tilt, rng)

    # Approximate IQA labels
    blur = round(0.30 + (1.0 - scale) * 0.20, 3)
    compression = round(0.40 + freq * 0.5, 3)
    noise = round(0.20 + _MOIRE_AMPLITUDE / 255.0 * 0.30, 3)

    iqa = {
        "blur_score": min(blur, 0.45),
        "compression_score": min(compression, 0.55),
        "noise_score": min(noise, 0.35),
    }
    return result, iqa


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
@click.option("--n-images", default=300, show_default=True, help="Target image count.")
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    doclaynet_dir: Path,
    output_dir: Path,
    registry: Path,
    n_images: int,
    dry_run: bool,
) -> None:
    """Generate screen-recapture moiré OOD images (Phase 3b, Recipe 6).

    Sources DocLayNet train-split pages and applies a downsample → moiré
    overlay → perspective warp → bicubic upsample pipeline, simulating
    a document photographed off a screen ('screen_recapture' wild condition).
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

        result, iqa = _simulate_screen_recapture(img_bgr, rng)

        out_name = f"screc_{n_registered:05d}.jpg"
        out_path = output_dir / out_name

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
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
        gt["capture_method"] = "screen_recapture"
        gt["orientation"] = 0

        from datetime import date

        entry = {
            "sha256": sha256,
            "phash": phash,
            "source_path": str(out_path),
            "registered_date": date.today().isoformat(),
            "ood_categories": ["ood_degradation", "ood_capture"],
            "reason": (
                f"Screen-recapture simulation (moiré + perspective) from "
                f"DocLayNet train: {src_path.name}; "
                "wild condition 'screen_recapture_moire' — ~0% training coverage"
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
                "generator_script": "generate_ood_screen_recapture.py",
                "recipe": "phase3b_recipe6",
                "seed": _OOD_RNG_SEED,
                "wild_condition": "screen_recapture_moire",
            },
        }

        if not dry_run:
            append_registry_entry(entry, registry)

        ood_sha256s.add(sha256)
        known_phashes.append(phash)
        n_registered += 1

    log_dry_run_summary(
        sub_command="generate-ood-screen-recapture",
        candidates=n_cands,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=n_registered,
        dry_run=dry_run,
    )
    click.echo(f"  Screen-recapture OOD: {n_registered}/{n_images}")


if __name__ == "__main__":
    main()
