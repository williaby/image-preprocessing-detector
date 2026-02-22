#!/usr/bin/env python3
"""Generate shadow-augmented view of synth-multiscript-v3 images.

Creates ~8K shadow images from v3 pristine base images using OpenCV-based
shadow augmentation with controllable severity. Output is a flat JSON manifest
consumed by ``prepare_multitask_datasets.py shadow`` sub-command.

Each output record contains:

- ``image_path``: relative path within output-dir (``images/{uuid}_shadow.jpg``)
- ``severity``: float [0–1], exact augmentation parameter
- ``provenance``: ``"synthetic_v3"``
- ``script``: ISO 15924 folder name from v3 (e.g. ``"Arab"``)
- ``split``: ``"train"`` / ``"val"`` / ``"test"`` from v3 splits registry

Shadow types (``--shadow-types``):

- ``edge``: gradient shadow from one edge (scanner lid not fully closed)
- ``cast``: rectangular opaque shadow block cast from an object
- ``spotlight``: dark vignette with a bright centre
- ``scanner_lid``: smooth gradient from corner (lid partially open)

Usage::

    python scripts/generate_v3_shadow_view.py \\
        --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \\
        --output-dir /mnt/e/03_training_datasets/shadow_synthetic \\
        --count 8000 \\
        --severity-range 0.1 1.0 \\
        --shadow-types edge cast spotlight scanner_lid

    # Dry run (no images written)
    python scripts/generate_v3_shadow_view.py \\
        --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \\
        --output-dir /tmp/shadow_test \\
        --count 100 --dry-run

Requires: google-cloud-storage, opencv-python, numpy, tqdm
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import cv2
import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Supported shadow type names
VALID_SHADOW_TYPES = ("edge", "cast", "spotlight", "scanner_lid")
DEFAULT_SHADOW_TYPES = list(VALID_SHADOW_TYPES)
DEFAULT_COUNT = 8_000
DEFAULT_SEVERITY_MIN = 0.1
DEFAULT_SEVERITY_MAX = 1.0
JPEG_QUALITY = 92


class _ImageRecord(NamedTuple):
    """Candidate image record from v3 pool."""

    script: str
    uuid: str
    split: str
    gcs_image_key: str  # GCS object key (no gs:// prefix)


class _ShadowResult(NamedTuple):
    """Output record written to metadata manifest."""

    image_path: str  # relative to output-dir
    severity: float
    provenance: str
    script: str
    split: str


# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------


def _get_gcs_bucket(bucket_name: str) -> Any:
    """Return a GCS Bucket client."""
    from google.cloud import storage  # type: ignore[import-untyped]

    client = storage.Client()
    return client.bucket(bucket_name)


def _parse_gcs_prefix(gcs_prefix: str) -> tuple[str, str]:
    """Split ``gs://bucket/prefix`` → ``(bucket_name, prefix)``."""
    if not gcs_prefix.startswith("gs://"):
        msg = f"Expected gs:// path, got: {gcs_prefix!r}"
        raise ValueError(msg)
    rest = gcs_prefix[5:]
    parts = rest.split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix


def _download_blob_bytes(bucket: Any, key: str) -> bytes:
    """Download a GCS blob as bytes."""
    blob = bucket.blob(key)
    return blob.download_as_bytes()


# ---------------------------------------------------------------------------
# Pool building from splits.jsonl
# ---------------------------------------------------------------------------


def _load_splits_pool(
    bucket: Any,
    v3_prefix: str,
) -> dict[str, list[_ImageRecord]]:
    """Download splits.jsonl and build per-script candidate pool.

    Builds the pool from ``source_path`` fields without listing GCS blobs
    (avoids 190K individual object LIST requests).

    Args:
        bucket: GCS Bucket client.
        v3_prefix: GCS prefix for v3 dataset (without bucket, without trailing /).

    Returns:
        Mapping from script folder name to list of ``_ImageRecord``.
    """
    splits_key = f"{v3_prefix}/splits.jsonl"
    logger.info(
        "Downloading splits registry from gs://%s/%s …", bucket.name, splits_key
    )
    content = bucket.blob(splits_key).download_as_text()

    pool: dict[str, list[_ImageRecord]] = {}
    skipped = 0

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue

        source_path = record.get("source_path", "")
        split = record.get("split", "train")

        # Extract SCRIPT and UUID from source_path:
        # /mnt/unraid/appdata/synthetic_multiscript_v3/Arab/UUID.jpg
        parts = Path(source_path).parts
        try:
            v3_idx = next(
                i for i, p in enumerate(parts) if p == "synthetic_multiscript_v3"
            )
            script = parts[v3_idx + 1]
            uuid = Path(parts[v3_idx + 2]).stem
        except (StopIteration, IndexError):
            skipped += 1
            logger.debug("Cannot parse source_path: %s", source_path)
            continue

        gcs_key = f"{v3_prefix}/{script}/{uuid}.jpg"
        rec = _ImageRecord(script=script, uuid=uuid, split=split, gcs_image_key=gcs_key)
        pool.setdefault(script, []).append(rec)

    total = sum(len(v) for v in pool.values())
    logger.info(
        "Pool built: %d scripts, %d images total (%d skipped)",
        len(pool),
        total,
        skipped,
    )
    return pool


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------


def _stratified_sample(
    pool: dict[str, list[_ImageRecord]],
    count: int,
    rng: random.Random,
) -> list[_ImageRecord]:
    """Sample ``count`` records stratified across scripts.

    Distributes quota evenly across scripts; remainder given to largest scripts.
    Each script is sampled without replacement (capped at pool size).

    Args:
        pool: Per-script candidate lists.
        count: Total samples to return.
        rng: Seeded random instance for reproducibility.

    Returns:
        Flat list of sampled ``_ImageRecord`` items.
    """
    scripts = sorted(pool.keys())
    n_scripts = len(scripts)
    if n_scripts == 0:
        return []

    base_quota = count // n_scripts
    remainder = count % n_scripts

    # Give extra 1 to the scripts with the most data
    scripts_by_size = sorted(scripts, key=lambda s: len(pool[s]), reverse=True)
    extra_scripts = set(scripts_by_size[:remainder])

    sampled: list[_ImageRecord] = []
    for script in scripts:
        quota = base_quota + (1 if script in extra_scripts else 0)
        available = pool[script]
        take = min(quota, len(available))
        sampled.extend(rng.sample(available, take))

    rng.shuffle(sampled)
    return sampled


# ---------------------------------------------------------------------------
# Shadow augmentation
# ---------------------------------------------------------------------------


def _apply_edge_shadow(
    image: np.ndarray,
    severity: float,
    rng: random.Random,
) -> np.ndarray:
    """Gradient shadow from one edge (scanner lid effect)."""
    h, w = image.shape[:2]
    side = rng.choice(("left", "right", "top", "bottom"))
    coverage = max(
        1, int((0.25 + severity * 0.55) * (w if side in ("left", "right") else h))
    )
    opacity = 0.15 + severity * 0.75

    mask = np.zeros((h, w), dtype=np.float32)
    grad = np.linspace(opacity, 0.0, coverage, dtype=np.float32)

    if side == "left":
        mask[:, :coverage] = grad[np.newaxis, :]
    elif side == "right":
        mask[:, -coverage:] = grad[np.newaxis, ::-1]
    elif side == "top":
        mask[:coverage, :] = grad[:, np.newaxis]
    else:  # bottom
        mask[-coverage:, :] = grad[::-1, np.newaxis]

    return _apply_mask(image, mask)


def _apply_cast_shadow(
    image: np.ndarray,
    severity: float,
    rng: random.Random,
) -> np.ndarray:
    """Opaque rectangular shadow block (object casting a shadow)."""
    h, w = image.shape[:2]
    opacity = 0.2 + severity * 0.65

    # Random shadow rectangle anchored to one edge
    side = rng.choice(("left", "right", "top", "bottom"))
    coverage_frac = 0.15 + severity * 0.45
    height_frac = 0.3 + rng.random() * 0.5

    mask = np.zeros((h, w), dtype=np.float32)
    if side in ("left", "right"):
        cov_px = int(coverage_frac * w)
        h_start = int((1 - height_frac) / 2 * h)
        h_end = h_start + int(height_frac * h)
        if side == "left":
            mask[h_start:h_end, :cov_px] = opacity
        else:
            mask[h_start:h_end, -cov_px:] = opacity
    else:
        cov_px = int(coverage_frac * h)
        w_start = int((1 - height_frac) / 2 * w)
        w_end = w_start + int(height_frac * w)
        if side == "top":
            mask[:cov_px, w_start:w_end] = opacity
        else:
            mask[-cov_px:, w_start:w_end] = opacity

    # Soft edge
    mask = cv2.GaussianBlur(mask, (31, 31), 0)
    return _apply_mask(image, mask)


def _apply_spotlight_shadow(
    image: np.ndarray,
    severity: float,
    rng: random.Random,
) -> np.ndarray:
    """Vignette with off-centre bright spotlight (camera shadow effect)."""
    h, w = image.shape[:2]
    opacity = 0.15 + severity * 0.75

    # Off-centre spotlight position
    cx = w * (0.3 + rng.random() * 0.4)
    cy = h * (0.3 + rng.random() * 0.4)

    max_dist = math.sqrt(max(cx, w - cx) ** 2 + max(cy, h - cy) ** 2)
    # Smaller bright radius for higher severity
    spotlight_r = max_dist * (0.6 - severity * 0.45)

    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(np.float32)
    mask = np.clip((dist - spotlight_r) / max(max_dist - spotlight_r, 1.0), 0.0, 1.0)
    mask = (mask * opacity).astype(np.float32)
    return _apply_mask(image, mask)


def _apply_scanner_lid_shadow(
    image: np.ndarray,
    severity: float,
    rng: random.Random,
) -> np.ndarray:
    """Diagonal gradient shadow from corner (scanner lid partially open)."""
    h, w = image.shape[:2]
    opacity = 0.2 + severity * 0.70

    # Corner choice
    corner_y = rng.choice((0, h - 1))
    corner_x = rng.choice((0, w - 1))

    Y, X = np.ogrid[:h, :w]
    # Distance from chosen corner, normalised
    max_d = math.sqrt(h * h + w * w)
    dist = np.sqrt((X - corner_x) ** 2 + (Y - corner_y) ** 2).astype(np.float32)
    coverage_d = max_d * (0.35 + severity * 0.45)
    mask = np.clip(1.0 - dist / coverage_d, 0.0, 1.0) * opacity
    return _apply_mask(image, mask.astype(np.float32))


def _apply_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Darken ``image`` by ``mask`` (values 0–1, 1 = fully darkened)."""
    img_f = image.astype(np.float32) / 255.0
    if img_f.ndim == 3:
        mask = mask[:, :, np.newaxis]
    result = img_f * (1.0 - mask)
    return np.clip(result * 255.0, 0, 255).astype(np.uint8)


_SHADOW_FNS = {
    "edge": _apply_edge_shadow,
    "cast": _apply_cast_shadow,
    "spotlight": _apply_spotlight_shadow,
    "scanner_lid": _apply_scanner_lid_shadow,
}


def _augment_image(
    image_bytes: bytes,
    severity: float,
    shadow_type: str,
    rng: random.Random,
) -> bytes:
    """Load image bytes, apply shadow, return JPEG bytes.

    Args:
        image_bytes: Raw JPEG/PNG bytes from GCS.
        severity: Shadow severity in [0, 1].
        shadow_type: One of VALID_SHADOW_TYPES.
        rng: Seeded random instance.

    Returns:
        JPEG-encoded bytes of the augmented image.
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        msg = "cv2.imdecode returned None — corrupt image bytes?"
        raise ValueError(msg)

    aug_fn = _SHADOW_FNS.get(shadow_type, _apply_edge_shadow)
    augmented = aug_fn(image, severity, rng)

    ok, buf = cv2.imencode(".jpg", augmented, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        msg = "cv2.imencode failed"
        raise RuntimeError(msg)
    return buf.tobytes()


# ---------------------------------------------------------------------------
# Main generation loop
# ---------------------------------------------------------------------------


def _process_record(
    record: _ImageRecord,
    bucket: Any,
    severity: float,
    shadow_type: str,
    images_dir: Path,
    rng: random.Random,
    dry_run: bool,
) -> _ShadowResult:
    """Download, augment, and save one shadow image.

    Args:
        record: Candidate image metadata from v3 pool.
        bucket: GCS Bucket client.
        severity: Exact severity value to use.
        shadow_type: Which shadow function to apply.
        images_dir: Local directory where output images are written.
        rng: Seeded random instance.
        dry_run: If True, skip GCS download and write; return dummy result.

    Returns:
        ``_ShadowResult`` with relative path and metadata.
    """
    out_name = f"{record.uuid}_{shadow_type}.jpg"
    rel_path = f"images/{out_name}"
    out_path = images_dir / out_name

    if not dry_run:
        raw = _download_blob_bytes(bucket, record.gcs_image_key)
        aug_bytes = _augment_image(raw, severity, shadow_type, rng)
        out_path.write_bytes(aug_bytes)

    return _ShadowResult(
        image_path=rel_path,
        severity=round(severity, 4),
        provenance="synthetic_v3",
        script=record.script,
        split=record.split,
    )


def run_generation(args: argparse.Namespace) -> int:
    """Run the shadow view generation pipeline.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 = success).
    """
    _setup_logging(args.verbose)
    rng = random.Random(args.seed)
    start = time.time()

    # Validate shadow types
    shadow_types: list[str] = args.shadow_types or DEFAULT_SHADOW_TYPES
    for st in shadow_types:
        if st not in VALID_SHADOW_TYPES:
            logger.error("Unknown shadow type %r. Valid: %s", st, VALID_SHADOW_TYPES)
            return 1

    severity_min, severity_max = args.severity_range
    if severity_min < 0.0 or severity_max > 1.0 or severity_min >= severity_max:
        logger.error("severity-range must satisfy 0 ≤ min < max ≤ 1")
        return 1

    # GCS setup
    bucket_name, v3_prefix = _parse_gcs_prefix(args.v3_gcs_prefix)
    bucket = _get_gcs_bucket(bucket_name)

    # Build candidate pool from splits.jsonl
    pool = _load_splits_pool(bucket, v3_prefix)
    if not pool:
        logger.error("No images found in splits registry")
        return 1

    # Stratified sample
    candidates = _stratified_sample(pool, args.count, rng)
    if not candidates:
        logger.error("No candidates after sampling")
        return 1

    logger.info("Sampled %d candidates from %d scripts", len(candidates), len(pool))

    # Output directory setup
    output_dir: Path = args.output_dir
    images_dir = output_dir / "images"
    if not args.dry_run:
        images_dir.mkdir(parents=True, exist_ok=True)

    # Progress bar
    try:
        from tqdm import tqdm  # type: ignore[import-untyped]

        progress: Any = tqdm(candidates, desc="Shadow view", unit="img")
    except ImportError:
        progress = candidates

    results: list[_ShadowResult] = []
    errors = 0

    for record in progress:
        severity = rng.uniform(severity_min, severity_max)
        shadow_type = rng.choice(shadow_types)
        try:
            result = _process_record(
                record, bucket, severity, shadow_type, images_dir, rng, args.dry_run
            )
            results.append(result)
        except Exception:
            logger.exception("Failed on %s/%s", record.script, record.uuid)
            errors += 1

    elapsed = time.time() - start
    throughput = len(results) / elapsed if elapsed > 0 else 0.0

    # Write manifest
    manifest_path = output_dir / "shadow_metadata.json"
    manifest_records = [
        {
            "image_path": r.image_path,
            "severity": r.severity,
            "provenance": r.provenance,
            "script": r.script,
            "split": r.split,
        }
        for r in results
    ]

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest_records, f, indent=2)

    # Script distribution report
    script_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    for r in results:
        script_counts[r.script] = script_counts.get(r.script, 0) + 1
        split_counts[r.split] = split_counts.get(r.split, 0) + 1

    logger.info(
        "Done: %d images, %d errors | %.1fs | %.1f img/s",
        len(results),
        errors,
        elapsed,
        throughput,
    )
    logger.info("Split distribution: %s", split_counts)
    logger.info(
        "Script distribution (top 5): %s",
        sorted(script_counts.items(), key=lambda x: -x[1])[:5],
    )
    if not args.dry_run:
        logger.info("Manifest written to: %s", manifest_path)

    return 0 if errors == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate shadow-augmented view from synth-multiscript-v3.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--v3-gcs-prefix",
        type=str,
        default="gs://image_detection_b/synth_multiscript_v3",
        help="GCS prefix for v3 dataset (default: gs://image_detection_b/synth_multiscript_v3)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Local directory for output images and shadow_metadata.json.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Number of shadow images to generate (default: {DEFAULT_COUNT}).",
    )
    parser.add_argument(
        "--severity-range",
        type=float,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=[DEFAULT_SEVERITY_MIN, DEFAULT_SEVERITY_MAX],
        help=f"Severity range [0,1] (default: {DEFAULT_SEVERITY_MIN} {DEFAULT_SEVERITY_MAX}).",
    )
    parser.add_argument(
        "--shadow-types",
        type=str,
        nargs="+",
        choices=VALID_SHADOW_TYPES,
        default=list(DEFAULT_SHADOW_TYPES),
        help=f"Shadow types to include (default: all). Choices: {VALID_SHADOW_TYPES}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and count without downloading images or writing output.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()
    return run_generation(args)


if __name__ == "__main__":
    sys.exit(main())
