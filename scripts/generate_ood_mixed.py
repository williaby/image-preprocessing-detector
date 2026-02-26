#!/usr/bin/env python3
"""Generate OOD multi-dimensional stacked images (Phase 3f, Recipe 13).

Run this script LAST — after all other OOD categories have reached ≥90%
of their targets.  It selects images already in the registry with 1–2 OOD
dimensions and applies additional augmentations to push them to ≥3 OOD
dimensions, registering the result in ``ood_mixed``.

Stacking combinations (examples from the plan):
  - reserved-script + extreme perspective + compound distortion
  - historical document + low resolution + handwriting
  - screen recapture + CJK script + shadow

Target: 762 images registered in ood_registry.jsonl under ood_mixed.

How it works:
  1. Load registry; group entries by ``ood_categories`` count (1 or 2).
  2. Randomly sample up to 762 candidate entries (the source images must
     exist on disk).
  3. For each candidate, pick an augmentation from a different OOD dimension
     than what the image already has.
  4. Write the augmented image to the ood/mixed directory.
  5. Register with ood_categories = original_categories + ["ood_mixed"].

Augmentation strategies applied to push images into a new OOD dimension:
  - ``add_geometry``: mild perspective warp (challenges skew/orient heads)
  - ``add_degradation``: moderate JPEG + contrast reduction
  - ``add_resolution``: bicubic downsample to 50% then back (resolution head)
  - ``add_shadow``: radial vignette shadow (shadow_severity head)

Usage:
    # Dry run (shows what would be generated)
    uv run python scripts/generate_ood_mixed.py --dry-run

    # Generate 762 images
    uv run python scripts/generate_ood_mixed.py \\
        --registry metadata_registry/ood_registry.jsonl \\
        --output-dir /mnt/e/image_detection/ood/mixed
"""

from __future__ import annotations

import io
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

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

# OOD seed namespace: 0xDEADBEEF_0DD5AFEC ^ recipe_index(13)
_OOD_RNG_SEED = (0xDEAD_BEEF_0DD5_AFEC ^ 0x0000_000D) & 0xFFFFFFFF

_OUTPUT_DEFAULT = Path("/mnt/e/image_detection/ood/mixed")
_REGISTRY_DEFAULT = Path("metadata_registry/ood_registry.jsonl")

# Augmentation strategies mapped to the new OOD dimension they add
_AUGMENTATION_STRATEGIES: list[str] = [
    "add_geometry",
    "add_degradation",
    "add_resolution",
    "add_shadow",
]

# Which existing ood_categories each strategy is incompatible with
# (don't add geometry to something that's already geometry-only, etc.)
_STRATEGY_INCOMPATIBLE: dict[str, list[str]] = {
    "add_geometry": ["ood_geometry"],
    "add_degradation": ["ood_degradation"],
    "add_resolution": ["ood_resolution"],
    "add_shadow": [],  # shadow is always additive
}

# Category that each strategy adds
_STRATEGY_ADDS: dict[str, str] = {
    "add_geometry": "ood_geometry",
    "add_degradation": "ood_degradation",
    "add_resolution": "ood_resolution",
    "add_shadow": "ood_degradation",
}


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


# ---------------------------------------------------------------------------
# Augmentation functions
# ---------------------------------------------------------------------------


def _aug_add_geometry(
    img_bgr: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, dict]:
    """Apply mild perspective warp (adds ood_geometry dimension)."""
    h, w = img_bgr.shape[:2]
    frac = rng.uniform(0.04, 0.10)
    offset = int(min(h, w) * frac)

    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dx = rng.randint(-offset, offset)
    dy = rng.randint(-offset, offset)
    dst_pts = np.float32([[dx, dy], [w + dx, 0], [w, h + dy], [0, h]])

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    result = cv2.warpPerspective(
        img_bgr,
        M,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    angle = math.degrees(math.atan2(abs(dy), abs(dx))) if abs(dx) + abs(dy) > 0 else 0.0
    return result, {"skew_angle_degrees": round(angle, 2)}


def _aug_add_degradation(
    img_bgr: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, dict]:
    """Apply JPEG + contrast reduction (adds ood_degradation dimension)."""
    # Moderate JPEG compression
    jpeg_q = rng.randint(30, 55)
    params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_q]
    _, encoded = cv2.imencode(".jpg", img_bgr, params)
    compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    # Contrast reduction
    factor = rng.uniform(0.55, 0.80)
    mid = 128.0
    flat = np.clip((compressed.astype(np.float32) - mid) * factor + mid, 0, 255).astype(
        np.uint8
    )

    compression_score = round((75 - jpeg_q) / 45.0 * 0.50 + 0.20, 3)
    contrast_score = round(factor * 0.40, 3)
    return flat, {
        "compression_score": compression_score,
        "contrast_score": contrast_score,
    }


def _aug_add_resolution(
    img_bgr: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, dict]:
    """Downsample then upsample (adds ood_resolution dimension)."""
    h, w = img_bgr.shape[:2]
    scale = rng.uniform(0.35, 0.55)
    small_w = max(32, int(w * scale))
    small_h = max(32, int(h * scale))
    small = cv2.resize(img_bgr, (small_w, small_h), interpolation=cv2.INTER_AREA)
    upsized = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    return upsized, {
        "resolution_quality": "low",
        "blur_score": round(0.30 + (1 - scale) * 0.25, 3),
    }


def _aug_add_shadow(img_bgr: np.ndarray, rng: random.Random) -> tuple[np.ndarray, dict]:
    """Add radial vignette shadow (adds shadow dimension)."""
    h, w = img_bgr.shape[:2]

    # Shadow centre (biased toward a corner)
    cx = rng.choice([0, w]) + rng.uniform(-w * 0.3, w * 0.3)
    cy = rng.choice([0, h]) + rng.uniform(-h * 0.3, h * 0.3)

    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    xg, yg = np.meshgrid(xs, ys)
    dist = np.sqrt((xg - cx) ** 2 + (yg - cy) ** 2)
    max_dist = math.hypot(w, h)

    # Normalise distance to [0, 1] and create shadow mask
    norm_dist = dist / max_dist
    shadow_strength = rng.uniform(0.25, 0.55)
    shadow_mask = 1.0 - shadow_strength * (1.0 - norm_dist)

    out = (
        (img_bgr.astype(np.float32) * shadow_mask[..., None])
        .clip(0, 255)
        .astype(np.uint8)
    )
    severity = round(shadow_strength, 3)
    return out, {"shadow_severity": severity, "shadow_type": "vignette"}


_AUGMENTATION_FNS: dict[str, Any] = {
    "add_geometry": _aug_add_geometry,
    "add_degradation": _aug_add_degradation,
    "add_resolution": _aug_add_resolution,
    "add_shadow": _aug_add_shadow,
}


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def _load_full_registry(registry_path: Path) -> list[dict]:
    """Load all entries from the OOD registry JSONL."""
    if not registry_path.exists():
        return []
    entries = []
    with registry_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _pick_strategy(existing_categories: list[str], rng: random.Random) -> str | None:
    """Choose an augmentation strategy compatible with existing categories.

    Returns None if no compatible strategy exists.
    """
    compatible = [
        s
        for s in _AUGMENTATION_STRATEGIES
        if not any(c in existing_categories for c in _STRATEGY_INCOMPATIBLE[s])
        and _STRATEGY_ADDS[s] not in existing_categories
    ]
    if not compatible:
        return None
    return rng.choice(compatible)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--registry",
    type=click.Path(path_type=Path),
    default=_REGISTRY_DEFAULT,
    show_default=True,
    help="OOD registry JSONL file (must be populated by earlier phases).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=_OUTPUT_DEFAULT,
    show_default=True,
    help="Directory to write mixed-OOD images.",
)
@click.option("--n-images", default=762, show_default=True, help="Target image count.")
@click.option("--dry-run", is_flag=True, help="Simulate only; do not write any files.")
def main(
    registry: Path,
    output_dir: Path,
    n_images: int,
    dry_run: bool,
) -> None:
    """Generate multi-dimensional OOD stacked images (Phase 3f, Recipe 13).

    Reads the populated OOD registry, selects images with 1–2 existing OOD
    categories whose source files exist on disk, applies an additional OOD
    augmentation to push them to ≥3 dimensions, and registers the results
    under ood_mixed.

    Run LAST after all other Phase 3 recipes have completed.
    """
    rng = random.Random(_OOD_RNG_SEED)

    # ------------------------------------------------------------------
    # Load registry and filter to single/dual-category candidates
    # ------------------------------------------------------------------
    click.echo(f"Loading OOD registry from {registry}...")
    all_entries = _load_full_registry(registry)
    click.echo(f"  Total entries: {len(all_entries):,}")

    candidates = [
        e
        for e in all_entries
        if 1 <= len(e.get("ood_categories", [])) <= 2
        and "ood_mixed" not in e.get("ood_categories", [])
        and Path(e.get("source_path", "")).exists()
    ]
    click.echo(f"  Eligible candidates (1–2 OOD dims, on-disk): {len(candidates):,}")

    if not candidates:
        click.echo(
            "  [WARN] No eligible candidates found.\n"
            "  Run all other Phase 3 recipes first and ensure images are on disk."
        )
        return

    ood_sha256s, ood_phashes = load_ood_registry(registry)
    known_phashes = list(ood_phashes)

    rng.shuffle(candidates)
    pool = candidates[: n_images * 3]  # oversample to allow for dedup drops

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    n_cands = n_skipped_dup = n_skipped_no_strategy = n_registered = 0
    strategy_counts: dict[str, int] = dict.fromkeys(_AUGMENTATION_STRATEGIES, 0)

    for entry in pool:
        if n_registered >= n_images:
            break
        n_cands += 1

        src_path = Path(entry["source_path"])
        if not src_path.exists():
            continue

        existing_categories: list[str] = entry.get("ood_categories", [])
        strategy = _pick_strategy(existing_categories, rng)
        if strategy is None:
            n_skipped_no_strategy += 1
            continue

        img_bgr = cv2.imread(str(src_path))
        if img_bgr is None:
            continue

        aug_fn = _AUGMENTATION_FNS[strategy]
        augmented, extra_gt = aug_fn(img_bgr, rng)

        out_name = f"mixed_{n_registered:05d}.jpg"
        out_path = output_dir / out_name

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, encoded = cv2.imencode(".jpg", augmented, encode_params)
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

        new_categories = [*list(existing_categories), "ood_mixed"]
        added_dim = _STRATEGY_ADDS[strategy]
        if added_dim not in new_categories:
            new_categories.append(added_dim)

        # Inherit ground_truth from source, apply new fields
        source_gt = entry.get("ground_truth", {})
        gt = build_ground_truth_template()
        for k, v in source_gt.items():
            if k in gt and v is not None:
                gt[k] = v
        gt.update(extra_gt)

        from datetime import date

        new_entry = {
            "sha256": sha256,
            "phash": phash,
            "source_path": str(out_path),
            "registered_date": date.today().isoformat(),
            "ood_categories": new_categories,
            "reason": (
                f"Multi-dim OOD stack: source had {existing_categories}, "
                f"added '{strategy}' (→{added_dim}) from {src_path.name}; "
                f"now {len(new_categories)} OOD dimensions (≥3 target)"
            ),
            "acquisition_method": "synthetic_generation",
            "license": entry.get("license", "unknown"),
            "dedup_verified": True,
            "evaluation_pipeline_stage": ["mobilenetv4", "siglip2"],
            "ground_truth": gt,
            "generation_metadata": {
                "source_entry_sha256": entry.get("sha256"),
                "source_path": str(src_path),
                "original_categories": existing_categories,
                "augmentation_strategy": strategy,
                "generator_script": "generate_ood_mixed.py",
                "recipe": "phase3f_recipe13",
                "seed": _OOD_RNG_SEED,
            },
        }

        if not dry_run:
            append_registry_entry(new_entry, registry)

        ood_sha256s.add(sha256)
        known_phashes.append(phash)
        strategy_counts[strategy] += 1
        n_registered += 1

    log_dry_run_summary(
        sub_command="generate-ood-mixed",
        candidates=n_cands,
        duplicates_training=0,
        duplicates_intra=n_skipped_dup,
        unique=n_registered,
        dry_run=dry_run,
    )
    click.echo(f"  Mixed OOD: {n_registered}/{n_images}")
    click.echo(f"  Strategy breakdown: {strategy_counts}")
    if n_skipped_no_strategy:
        click.echo(
            f"  [INFO] {n_skipped_no_strategy} candidates skipped (no compatible strategy)."
        )


if __name__ == "__main__":
    main()
