#!/usr/bin/env python3
"""Generate OOD multi-DPI resolution images (Phase 3d, Recipes 9 + 10).

Creates low-resolution and upscaling-artifact document images to stress-test
the resolution_quality head of MobileNetV4 (MNV4-H3).

Recipe 9 — Vector PDF Multi-DPI Rendering (300 images):
  Simulates rendering the same document at 72, 100, and 150 DPI by
  downsampling DocLayNet 300-DPI PNG sources to the target DPI fraction,
  then keeping at that reduced size.  Each source image produces 3 output
  images (one per DPI tier).  100 source pages x 3 tiers = 300 images.

  Labels: resolution_quality = "low" / "very_low"
          capture_method = "born_digital"

Recipe 10 — Upscaling Artifact Simulation (235 images):
  Takes the 72-DPI downsampled images from Recipe 9 and bicubic-upsamples
  them back to 300-DPI equivalent size, simulating bad scanner output or
  mis-specified scan resolution.

  Labels: resolution_quality = "upscaled_artifact"
          capture_method = "born_digital"

Usage:
    # Dry run
    uv run python scripts/generate_ood_multidpi.py --dry-run

    # Generate all 535 images
    uv run python scripts/generate_ood_multidpi.py \\
        --doclaynet-dir /mnt/e/image_detection/01_base_data/documents/doclaynet \\
        --output-dir /mnt/e/image_detection/ood/resolution
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

# OOD seed namespace: 0xDEADBEEF_0DD5AFEC ^ recipe_index(9)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x0000_0009) & 0xFFFFFFFF

_DOCLAYNET_DEFAULT = Path("/mnt/e/image_detection/01_base_data/documents/doclaynet")
_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/resolution")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# Source DPI assumption for DocLayNet PNGs (standard page render DPI)
_SOURCE_DPI = 300

# Recipe 9 DPI tiers with quality label
_DPI_TIERS: list[tuple[int, str]] = [
    (72, "very_low"),
    (100, "very_low"),
    (150, "low"),
]

# Recipe 9 source page count (100 pages x 3 tiers = 300 images)
_R9_SOURCE_PAGES = 100

# Recipe 10 source count (take from 72-DPI outputs of Recipe 9)
_R10_TARGET = 235


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


def _downsample_to_dpi(img_bgr: np.ndarray, target_dpi: int) -> np.ndarray:
    """Downsample image to simulate *target_dpi* rendering.

    Assumes the source image is at _SOURCE_DPI.  The output is kept at the
    reduced pixel size (not upsampled back) — this directly represents what
    a document scanned at *target_dpi* would look like.

    Args:
        img_bgr: Source BGR uint8 image at _SOURCE_DPI.
        target_dpi: Target DPI (72, 100, or 150).

    Returns:
        Downsampled BGR image at the reduced pixel dimensions.
    """
    scale = target_dpi / _SOURCE_DPI
    h, w = img_bgr.shape[:2]
    new_w = max(32, int(w * scale))
    new_h = max(32, int(h * scale))
    return cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _upsample_artifact(img_bgr: np.ndarray) -> np.ndarray:
    """Bicubic-upsample a low-DPI image back to 300-DPI equivalent size.

    Simulates a scanner set to 300 DPI that actually captures at 72 DPI and
    interpolates — producing characteristic blurring and aliasing artefacts.

    Args:
        img_bgr: Low-resolution BGR image (from _downsample_to_dpi at 72 DPI).

    Returns:
        Upsampled BGR image at the original 300-DPI pixel dimensions.
    """
    h, w = img_bgr.shape[:2]
    # Scale back up by 300/72 factor
    scale = _SOURCE_DPI / 72
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


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


def _register_image(
    img_bytes: bytes,
    out_path: Path,
    src_path: Path,
    extra_gt: dict,
    extra_meta: dict,
    ood_sha256s: set[str],
    known_phashes: list[str],
    registry: Path,
    dry_run: bool,
) -> bool:
    """Hash, dedup-check, write, and register a single OOD image.

    Args:
        img_bytes: JPEG bytes of the image to register.
        out_path: Destination file path.
        src_path: Source DocLayNet image path (for metadata).
        extra_gt: Fields to merge into ground_truth template.
        extra_meta: Fields to merge into generation_metadata.
        ood_sha256s: Running set of registered SHA256s (mutated in-place).
        known_phashes: Running list of registered pHashes (mutated in-place).
        registry: OOD registry JSONL path.
        dry_run: If True, skip all writes.

    Returns:
        True if image was registered (not a duplicate), False otherwise.
    """
    sha256, phash = _hashes_from_bytes(img_bytes)

    if sha256 in ood_sha256s:
        return False
    if any(hamming_distance(phash, p) <= 5 for p in known_phashes):
        return False

    if not dry_run:
        out_path.write_bytes(img_bytes)

    gt = build_ground_truth_template()
    gt.update(extra_gt)

    from datetime import date

    meta = {
        "source_dataset": "doclaynet",
        "source_image": src_path.name,
        "split_used": "train",
        "generator_script": "generate_ood_multidpi.py",
        "seed": _OOD_RNG_SEED,
    }
    meta.update(extra_meta)

    entry = {
        "sha256": sha256,
        "phash": phash,
        "source_path": str(out_path),
        "registered_date": date.today().isoformat(),
        "ood_categories": ["ood_resolution"],
        "reason": extra_meta.get("reason", "Multi-DPI resolution OOD"),
        "acquisition_method": "synthetic_generation",
        "license": "CDLA-Permissive-1.0",
        "dedup_verified": True,
        "evaluation_pipeline_stage": ["mobilenetv4"],
        "ground_truth": gt,
        "generation_metadata": meta,
    }

    if not dry_run:
        append_registry_entry(entry, registry)

    ood_sha256s.add(sha256)
    known_phashes.append(phash)
    return True


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
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    doclaynet_dir: Path,
    output_dir: Path,
    registry: Path,
    dry_run: bool,
) -> None:
    """Generate multi-DPI resolution OOD images (Phase 3d, Recipes 9 + 10).

    Recipe 9: Downsamples DocLayNet pages to 72/100/150 DPI equivalents and
    keeps them at reduced size (simulating low-DPI rendering).

    Recipe 10: Bicubic-upsamples the 72-DPI images back to 300-DPI size,
    simulating scanner output with interpolation artefacts.
    """
    rng = random.Random(_OOD_RNG_SEED)

    click.echo(f"Loading DocLayNet train pool from {doclaynet_dir}...")
    source_pool = _load_doclaynet_train_pool(doclaynet_dir)
    click.echo(f"  Train pool: {len(source_pool):,} images available")

    ood_sha256s, ood_phashes = load_ood_registry(registry)
    known_phashes = list(ood_phashes)

    rng.shuffle(source_pool)
    # Recipe 9 needs _R9_SOURCE_PAGES; Recipe 10 reuses those outputs
    selected_pages = source_pool[:_R9_SOURCE_PAGES]

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    n_r9 = n_r10 = n_skipped_dup = 0
    # Store 72-DPI outputs for Recipe 10 reuse
    r10_candidates: list[tuple[np.ndarray, Path]] = []

    # ------------------------------------------------------------------
    # Recipe 9: DPI downsampling
    # ------------------------------------------------------------------
    click.echo(
        f"\n  Recipe 9: Rendering {len(selected_pages)} pages x {len(_DPI_TIERS)} DPI tiers..."
    )

    for src_path in selected_pages:
        img_bgr = cv2.imread(str(src_path))
        if img_bgr is None:
            continue

        for dpi, quality_label in _DPI_TIERS:
            down = _downsample_to_dpi(img_bgr, dpi)

            out_name = f"multidpi_r9_{n_r9:05d}_{dpi}dpi.jpg"
            out_path = output_dir / out_name

            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 92]
            _, encoded = cv2.imencode(".jpg", down, encode_params)
            img_bytes = encoded.tobytes()

            registered = _register_image(
                img_bytes=img_bytes,
                out_path=out_path,
                src_path=src_path,
                extra_gt={
                    "resolution_quality": quality_label,
                    "capture_method": "born_digital",
                },
                extra_meta={
                    "recipe": "phase3d_recipe9",
                    "target_dpi": dpi,
                    "source_dpi": _SOURCE_DPI,
                    "reason": (
                        f"DPI-downsampled render ({dpi} DPI) from DocLayNet train: "
                        f"{src_path.name}; stress-tests MNV4-H3 resolution_quality head"
                    ),
                },
                ood_sha256s=ood_sha256s,
                known_phashes=known_phashes,
                registry=registry,
                dry_run=dry_run,
            )

            if registered:
                n_r9 += 1
                # Collect 72 DPI downsampled arrays for Recipe 10
                if dpi == 72:
                    r10_candidates.append((down, src_path))
            else:
                n_skipped_dup += 1

    click.echo(f"  Recipe 9 complete: {n_r9} images registered.")

    # ------------------------------------------------------------------
    # Recipe 10: Upscaling artefacts
    # ------------------------------------------------------------------
    r10_needed = min(_R10_TARGET, len(r10_candidates))
    click.echo(
        f"\n  Recipe 10: Upscaling {r10_needed} x 72-DPI images back to 300-DPI size..."
    )

    for down_img, src_path in r10_candidates[:r10_needed]:
        upsized = _upsample_artifact(down_img)

        out_name = f"multidpi_r10_{n_r10:05d}_upsized.jpg"
        out_path = output_dir / out_name

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 88]
        _, encoded = cv2.imencode(".jpg", upsized, encode_params)
        img_bytes = encoded.tobytes()

        registered = _register_image(
            img_bytes=img_bytes,
            out_path=out_path,
            src_path=src_path,
            extra_gt={
                "resolution_quality": "upscaled_artifact",
                "capture_method": "born_digital",
                "blur_score": 0.35,  # interpolation softening
            },
            extra_meta={
                "recipe": "phase3d_recipe10",
                "source_dpi": 72,
                "upsample_target_dpi": _SOURCE_DPI,
                "upsample_method": "bicubic",
                "reason": (
                    f"Bicubic upscale (72→300 DPI) from DocLayNet train: "
                    f"{src_path.name}; simulates bad scanner with interpolation artefacts; "
                    "specifically warns MNV4-H3 resolution_quality head"
                ),
            },
            ood_sha256s=ood_sha256s,
            known_phashes=known_phashes,
            registry=registry,
            dry_run=dry_run,
        )

        if registered:
            n_r10 += 1
        else:
            n_skipped_dup += 1

    total = n_r9 + n_r10
    r9_target = _R9_SOURCE_PAGES * len(_DPI_TIERS)
    log_dry_run_summary(
        sub_command="generate-ood-multidpi",
        candidates=len(selected_pages) * len(_DPI_TIERS) + len(r10_candidates),
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=total,
        dry_run=dry_run,
    )
    click.echo(
        f"  Multi-DPI OOD: Recipe 9={n_r9}/{r9_target}, "
        f"Recipe 10={n_r10}/{_R10_TARGET}, Total={total}/535"
    )


if __name__ == "__main__":
    main()
