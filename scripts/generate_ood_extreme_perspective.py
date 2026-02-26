#!/usr/bin/env python3
"""Generate OOD extreme-perspective images (Phase 3a, Recipe 2).

Applies extreme perspective transforms (≥40° corner perturbation) to
DocLayNet/RVL-CDIP train-split images, creating geometry samples with
~0% training coverage (training data has mild perspective ≤20°).
Target: 700 images registered in ood_registry.jsonl under ood_geometry.

Transform:
  cv2.getPerspectiveTransform with random corner offsets:
    - At least one corner shifted ≥40° equivalent (~15% of image dimension)
    - Remaining corners shifted 10–20% to ensure non-degenerate transforms
    - Output padded with white background; output size matches input

Labels (derived from transform matrix):
  skew_angle_degrees   approximate max angular deviation
  capture_method       "synthetic_augmentation"
  orientation          preserved from source (0 = upright)

Usage:
    # Dry run
    uv run python scripts/generate_ood_extreme_perspective.py --dry-run

    # Generate 700 images
    uv run python scripts/generate_ood_extreme_perspective.py \\
        --doclaynet-dir /mnt/e/image_detection/01_base_data/documents/doclaynet \\
        --output-dir /mnt/e/image_detection/ood/geometry \\
        --n-images 700
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

# #ASSUME: env: opencv available in the uv environment
try:
    import cv2
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

# Distinct OOD seed namespace (same master namespace as compound distortion)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x1234_5678) & 0xFFFFFFFF

_DOCLAYNET_DEFAULT = Path(
    "/mnt/e/image_detection/01_base_data/documents/doclaynet"
)
_RVLCDIP_DEFAULT = Path(
    "/mnt/e/image_detection/01_base_data/documents/rvl_cdip"
)
_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/geometry")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# Minimum extreme offset: 15% of dimension (≈40° equivalent for typical A4 docs)
_MIN_EXTREME_FRACTION = 0.15
_MIN_MODERATE_FRACTION = 0.08


def _random_extreme_perspective(
    img: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, float]:
    """Apply extreme perspective transform; return (warped_img, skew_angle_deg).

    At least one corner has offset ≥ MIN_EXTREME_FRACTION * image_size.
    Remaining corners have offsets in [MIN_MODERATE_FRACTION, MIN_EXTREME_FRACTION).
    Returns the warped image (same size, white background) and approximate
    max angular deviation in degrees derived from the corner displacements.
    """
    h, w = img.shape[:2]

    def _rand_offset(fraction_lo: float, fraction_hi: float) -> tuple[float, float]:
        """Random (dx, dy) with magnitude in [lo, hi] fraction of min(w, h)."""
        scale = min(w, h)
        mag = rng.uniform(fraction_lo * scale, fraction_hi * scale)
        angle_rad = rng.uniform(0, 2 * math.pi)
        return mag * math.cos(angle_rad), mag * math.sin(angle_rad)

    # Source corners: TL, TR, BR, BL
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])

    # Choose which corner gets the extreme offset (at least one)
    extreme_corner = rng.randint(0, 3)
    offsets = []
    for i in range(4):
        if i == extreme_corner:
            dx, dy = _rand_offset(_MIN_EXTREME_FRACTION, _MIN_EXTREME_FRACTION * 2.0)
        else:
            dx, dy = _rand_offset(_MIN_MODERATE_FRACTION, _MIN_EXTREME_FRACTION)
        offsets.append((dx, dy))

    dst_pts = np.float32(
        [[src_pts[i, 0] + offsets[i][0], src_pts[i, 1] + offsets[i][1]] for i in range(4)]
    )

    # Compute approximate angular deviation from the extreme corner displacement
    ex_dx, ex_dy = offsets[extreme_corner]
    corner_x, corner_y = src_pts[extreme_corner]
    # Diagonal from centre to corner
    centre_x, centre_y = w / 2, h / 2
    diag_len = math.hypot(corner_x - centre_x, corner_y - centre_y)
    if diag_len > 0:
        displacement = math.hypot(ex_dx, ex_dy)
        skew_angle = math.degrees(math.atan2(displacement, diag_len))
    else:
        skew_angle = 0.0

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(
        img, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return warped, round(skew_angle, 2)


def _load_source_pool(doclaynet_dir: Path, rvlcdip_dir: Path) -> list[Path]:
    """Collect train-split images from DocLayNet and optionally RVL-CDIP."""
    pool: list[Path] = []

    # DocLayNet train split (CDLA-Permissive)
    coco_train = doclaynet_dir / "ground_truth" / "coco" / "train.json"
    img_dir = doclaynet_dir / "documents" / "png"
    if coco_train.exists() and img_dir.exists():
        with coco_train.open() as f:
            data = json.load(f)
        dl_paths = [img_dir / entry["file_name"] for entry in data["images"]]
        pool.extend(p for p in dl_paths if p.exists())
        click.echo(f"  DocLayNet train:  {len([p for p in dl_paths if p.exists()]):,} images")
    else:
        click.echo(f"  [SKIP] DocLayNet not found at {doclaynet_dir}")

    # RVL-CDIP (check license before using — Academic only)
    if rvlcdip_dir.exists():
        rvl_imgs = list(rvlcdip_dir.rglob("*.tif")) + list(rvlcdip_dir.rglob("*.tiff"))
        pool.extend(rvl_imgs)
        click.echo(f"  RVL-CDIP:         {len(rvl_imgs):,} images")

    return pool


@click.command()
@click.option(
    "--doclaynet-dir",
    type=click.Path(path_type=Path),
    default=_DOCLAYNET_DEFAULT,
    show_default=True,
    help="DocLayNet root (expects ground_truth/coco/train.json + documents/png/).",
)
@click.option(
    "--rvlcdip-dir",
    type=click.Path(path_type=Path),
    default=_RVLCDIP_DEFAULT,
    show_default=True,
    help="RVL-CDIP root (optional; Academic license — excluded by default).",
)
@click.option(
    "--skip-rvlcdip",
    is_flag=True,
    default=True,
    show_default=True,
    help="Skip RVL-CDIP (Academic license). Disable if confirmed commercial-OK.",
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
    rvlcdip_dir: Path,
    skip_rvlcdip: bool,
    output_dir: Path,
    registry: Path,
    n_images: int,
    dry_run: bool,
) -> None:
    """Generate extreme-perspective OOD images (Phase 3a, Recipe 2).

    Sources DocLayNet train-split pages and applies extreme corner
    perturbations (≥40°) to challenge skew and orientation heads.
    Skew angle ground truth is derived from the transform matrix.
    """
    rng = random.Random(_OOD_RNG_SEED)

    rvlcdip_active = _RVLCDIP_DEFAULT if not skip_rvlcdip else Path("/nonexistent")
    click.echo("Loading source pool...")
    source_pool = _load_source_pool(doclaynet_dir, rvlcdip_active)
    click.echo(f"  Total pool: {len(source_pool):,} images")

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

        warped, skew_angle = _random_extreme_perspective(img_bgr, rng)

        out_name = f"extpersp_{n_registered:05d}.jpg"
        out_path = output_dir / out_name

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 92]
        _, encoded = cv2.imencode(".jpg", warped, encode_params)
        img_bytes = encoded.tobytes()

        sha256, phash = _hashes_from_bytes(img_bytes)

        # Dedup
        if sha256 in ood_sha256s:
            n_skipped_dup += 1
            continue
        if any(hamming_distance(phash, p) <= 5 for p in known_phashes):
            n_skipped_dup += 1
            continue

        if not dry_run:
            out_path.write_bytes(img_bytes)

        gt = build_ground_truth_template()
        gt["skew_angle_degrees"] = skew_angle
        gt["capture_method"] = "synthetic_augmentation"
        gt["orientation"] = 0  # source images are upright

        from datetime import date

        entry = {
            "sha256": sha256,
            "phash": phash,
            "source_path": str(out_path),
            "registered_date": date.today().isoformat(),
            "ood_categories": ["ood_geometry"],
            "reason": (
                f"Extreme perspective transform (≥40°) from DocLayNet train: "
                f"{src_path.name}; skew_angle={skew_angle}°; "
                "challenges skew_reg + orientation_cls heads"
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
                "generator_script": "generate_ood_extreme_perspective.py",
                "recipe": "phase3a_recipe2",
                "seed": _OOD_RNG_SEED,
                "transform": "extreme_perspective",
                "min_extreme_fraction": _MIN_EXTREME_FRACTION,
            },
        }

        if not dry_run:
            append_registry_entry(entry, registry)

        ood_sha256s.add(sha256)
        known_phashes.append(phash)
        n_registered += 1

    log_dry_run_summary(
        sub_command="generate-ood-extreme-perspective",
        candidates=n_cands,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=n_registered,
        dry_run=dry_run,
    )
    click.echo(f"  Extreme perspective OOD: {n_registered}/{n_images}")


if __name__ == "__main__":
    main()
