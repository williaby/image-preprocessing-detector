#!/usr/bin/env python3
"""Generate OOD orientation-ambiguous (symmetric) images (Phase 3a, Recipe 1).

Crops documents to their center 60% of height, removing headers and footers
that are the primary cues an orientation classifier uses.  The resulting images
are inherently ambiguous — the correct orientation cannot be determined from
image content alone — so ``orientation_cls`` must learn to predict abstention
or near-uniform class entropy on these samples.

Target: 500 images registered in ood_registry.jsonl under ood_geometry.

Transform:
  1. Load upright DocLayNet train-split PNG.
  2. Crop y: [0.20 * H, 0.80 * H], x: [0.10 * W, 0.90 * W].
  3. Optionally rotate by a random multiple of 90° (equal probability for each
     of the four rotations) so that the test distribution is balanced across
     all orientations.  Ground-truth orientation is recorded as the rotation
     applied (0/90/180/270) but the evaluator must treat confidence < 0.4 as
     abstention.

Labels:
  orientation        int in {0, 90, 180, 270} — the applied rotation
  capture_method     "born_digital" (DocLayNet source)

Usage:
    # Dry run
    uv run python scripts/generate_ood_symmetric.py --dry-run

    # Generate 500 images
    uv run python scripts/generate_ood_symmetric.py \\
        --doclaynet-dir /mnt/e/image_detection/01_base_data/documents/doclaynet \\
        --output-dir /mnt/e/image_detection/ood/geometry \\
        --n-images 500
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

# OOD seed namespace: 0xDEADBEEF_0DD5AFEC ^ recipe_index(1)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x0000_0001) & 0xFFFFFFFF

_DOCLAYNET_DEFAULT = Path(
    "/mnt/e/image_detection/01_base_data/documents/doclaynet"
)
_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/geometry")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# Fraction of image kept (from center)
_Y_LO = 0.20
_Y_HI = 0.80
_X_LO = 0.10
_X_HI = 0.90

_ROTATIONS = [0, 90, 180, 270]


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


def _center_crop_and_rotate(
    img_bgr: np.ndarray, rotation_deg: int
) -> np.ndarray:
    """Crop to center fraction and apply 90°-step rotation.

    Args:
        img_bgr: Source image in BGR uint8 format.
        rotation_deg: One of {0, 90, 180, 270}.

    Returns:
        Cropped + rotated BGR image as uint8.
    """
    h, w = img_bgr.shape[:2]
    y0 = int(_Y_LO * h)
    y1 = int(_Y_HI * h)
    x0 = int(_X_LO * w)
    x1 = int(_X_HI * w)
    cropped = img_bgr[y0:y1, x0:x1]

    if rotation_deg == 0:
        return cropped
    elif rotation_deg == 90:
        return cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_deg == 180:
        return cv2.rotate(cropped, cv2.ROTATE_180)
    else:  # 270
        return cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)


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
@click.option("--n-images", default=500, show_default=True, help="Target image count.")
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    doclaynet_dir: Path,
    output_dir: Path,
    registry: Path,
    n_images: int,
    dry_run: bool,
) -> None:
    """Generate orientation-ambiguous OOD images (Phase 3a, Recipe 1).

    Crops DocLayNet train-split pages to their center 60% (removing headers
    and footers) and applies a random 90°-step rotation.  Challenges the
    orientation_cls head by removing the structural cues it relies on.
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
    rot_counts = {0: 0, 90: 0, 180: 0, 270: 0}

    for src_path in candidate_pool:
        if n_registered >= n_images:
            break
        n_cands += 1

        img_bgr = cv2.imread(str(src_path))
        if img_bgr is None:
            continue

        rotation = rng.choice(_ROTATIONS)
        cropped = _center_crop_and_rotate(img_bgr, rotation)

        out_name = f"sym_{n_registered:05d}.jpg"
        out_path = output_dir / out_name

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 92]
        _, encoded = cv2.imencode(".jpg", cropped, encode_params)
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
        gt["orientation"] = rotation
        gt["capture_method"] = "born_digital"

        from datetime import date

        entry = {
            "sha256": sha256,
            "phash": phash,
            "source_path": str(out_path),
            "registered_date": date.today().isoformat(),
            "ood_categories": ["ood_geometry"],
            "reason": (
                f"Center-crop (y 20%–80%, x 10%–90%) from DocLayNet train: "
                f"{src_path.name}; rotation={rotation}°; "
                "removes orientation cues (headers/footers) — challenges orientation_cls"
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
                "generator_script": "generate_ood_symmetric.py",
                "recipe": "phase3a_recipe1",
                "seed": _OOD_RNG_SEED,
                "crop_y": [_Y_LO, _Y_HI],
                "crop_x": [_X_LO, _X_HI],
                "rotation_deg": rotation,
            },
        }

        if not dry_run:
            append_registry_entry(entry, registry)

        ood_sha256s.add(sha256)
        known_phashes.append(phash)
        rot_counts[rotation] += 1
        n_registered += 1

    log_dry_run_summary(
        sub_command="generate-ood-symmetric",
        candidates=n_cands,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=n_registered,
        dry_run=dry_run,
    )
    click.echo(f"  Symmetric OOD: {n_registered}/{n_images}")
    click.echo(f"  Rotation distribution: {rot_counts}")


if __name__ == "__main__":
    main()
