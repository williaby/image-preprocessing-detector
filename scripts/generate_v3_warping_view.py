#!/usr/bin/env python3
"""Generate warping-augmented view of synth-multiscript-v3 images.

Creates ~5K warped images from v3 pristine base images using OpenCV-based
geometric distortion with controllable severity. Output is a flat JSON manifest
consumed by ``prepare_multitask_datasets.py warping`` sub-command.

Each output record contains:

- ``image_path``: relative path within output-dir (``images/{uuid}_warp.jpg``)
- ``severity``: float [0–1], exact augmentation parameter
- ``provenance``: ``"synthetic_v3"``
- ``script``: ISO 15924 folder name from v3 (e.g. ``"Arab"``)
- ``split``: ``"train"`` / ``"val"`` / ``"test"`` from v3 splits registry
- ``warping_type``: one of ``"perspective"``, ``"page_curl"``, ``"fold"``

Warping types (``--warp-types``):

- ``perspective``: 4-corner homography displacement (most common real-world warp)
- ``page_curl``: cylindrical warp simulating a page being curled at a corner
- ``fold``: reflection fold across a diagonal line

Severity maps linearly to geometric displacement: severity=0.0 → flat,
severity=1.0 → maximum distortion (still recoverable by correction).

Usage::

    python scripts/generate_v3_warping_view.py \\
        --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \\
        --output-dir /mnt/e/03_training_datasets/warping_synthetic \\
        --count 5000 \\
        --severity-range 0.05 0.95 \\
        --warp-types perspective page_curl fold

    # Dry run
    python scripts/generate_v3_warping_view.py \\
        --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \\
        --output-dir /tmp/warp_test --count 50 --dry-run

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

VALID_WARP_TYPES = ("perspective", "page_curl", "fold")
DEFAULT_WARP_TYPES = list(VALID_WARP_TYPES)
DEFAULT_COUNT = 5_000
DEFAULT_SEVERITY_MIN = 0.05
DEFAULT_SEVERITY_MAX = 0.95
JPEG_QUALITY = 92


class _ImageRecord(NamedTuple):
    """Candidate image record from v3 pool."""

    script: str
    uuid: str
    split: str
    gcs_image_key: str  # GCS object key (no gs:// prefix)


class _WarpResult(NamedTuple):
    """Output record written to metadata manifest."""

    image_path: str  # relative to output-dir
    severity: float
    warping_type: str
    provenance: str
    script: str
    split: str


# ---------------------------------------------------------------------------
# GCS helpers (same pattern as generate_v3_shadow_view.py)
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
    return parts[0], parts[1] if len(parts) > 1 else ""


def _download_blob_bytes(bucket: Any, key: str) -> bytes:
    """Download a GCS blob as bytes."""
    return bucket.blob(key).download_as_bytes()


# ---------------------------------------------------------------------------
# Pool building (shared logic with shadow script)
# ---------------------------------------------------------------------------


def _load_splits_pool(
    bucket: Any,
    v3_prefix: str,
) -> dict[str, list[_ImageRecord]]:
    """Download splits.jsonl and build per-script candidate pool.

    Args:
        bucket: GCS Bucket client.
        v3_prefix: GCS prefix for v3 dataset (without bucket, no trailing /).

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
        parts = Path(source_path).parts

        try:
            v3_idx = next(
                i for i, p in enumerate(parts) if p == "synthetic_multiscript_v3"
            )
            script = parts[v3_idx + 1]
            uuid = Path(parts[v3_idx + 2]).stem
        except (StopIteration, IndexError):
            skipped += 1
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

    Args:
        pool: Per-script candidate lists.
        count: Total samples desired.
        rng: Seeded random instance.

    Returns:
        Flat list of sampled ``_ImageRecord`` items.
    """
    scripts = sorted(pool.keys())
    n_scripts = len(scripts)
    if n_scripts == 0:
        return []

    base_quota = count // n_scripts
    remainder = count % n_scripts
    extra_scripts = set(
        sorted(scripts, key=lambda s: len(pool[s]), reverse=True)[:remainder]
    )

    sampled: list[_ImageRecord] = []
    for script in scripts:
        quota = base_quota + (1 if script in extra_scripts else 0)
        take = min(quota, len(pool[script]))
        sampled.extend(rng.sample(pool[script], take))

    rng.shuffle(sampled)
    return sampled


# ---------------------------------------------------------------------------
# Warping augmentation
# ---------------------------------------------------------------------------


def _apply_perspective_warp(
    image: np.ndarray,
    severity: float,
    rng: random.Random,
) -> np.ndarray:
    """Random 4-corner perspective warp.

    Each corner is displaced by up to ``severity * max_displacement`` pixels.
    The distortion is asymmetric to simulate real page photographing angles.

    Args:
        image: BGR image array.
        severity: Warp strength in [0, 1].
        rng: Random instance.

    Returns:
        Warped BGR image array.
    """
    h, w = image.shape[:2]
    max_shift = severity * min(h, w) * 0.25

    # Source corners: TL, TR, BR, BL
    src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])

    # Randomise corner displacements; bias toward one side for realism
    bias_corner = rng.randint(0, 3)
    shifts = np.zeros((4, 2), dtype=np.float32)
    for i in range(4):
        bias = 1.5 if i == bias_corner else 0.5
        shifts[i, 0] = rng.uniform(-max_shift * bias, max_shift * bias)
        shifts[i, 1] = rng.uniform(-max_shift * bias, max_shift * bias)

    dst = src + shifts
    # Clamp to image bounds
    dst[:, 0] = np.clip(dst[:, 0], 0, w - 1)
    dst[:, 1] = np.clip(dst[:, 1], 0, h - 1)

    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )


def _apply_page_curl(
    image: np.ndarray,
    severity: float,
    rng: random.Random,
) -> np.ndarray:
    """Cylindrical page curl from one corner.

    Simulates a page being lifted from a scanner bed: the corner curls up,
    causing a crescent-shaped warping region.

    Args:
        image: BGR image array.
        severity: Curl strength in [0, 1].
        rng: Random instance.

    Returns:
        Curled BGR image array (same size, black fill on exposed region).
    """
    h, w = image.shape[:2]
    # Curl originates from one corner
    corner = rng.choice(((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)))
    cy, cx = corner

    # Curl radius: small = tight curl (high severity), large = gentle
    curl_radius = max(50.0, min(h, w) * (1.2 - severity * 0.9))
    # Affected region radius (grows with severity)
    region_radius = min(h, w) * (0.2 + severity * 0.55)

    map_x = np.zeros((h, w), dtype=np.float32)
    map_y = np.zeros((h, w), dtype=np.float32)

    for y in range(h):
        for x in range(w):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < region_radius:
                # Cylindrical distortion toward corner
                t = 1.0 - dist / region_radius
                angle = t * (math.pi / 2.0) * severity
                stretch = curl_radius * math.sin(angle)
                dx = stretch * (cx - x) / (dist + 1e-6)
                dy = stretch * (cy - y) / (dist + 1e-6)
                map_x[y, x] = min(max(x + dx, 0), w - 1)
                map_y[y, x] = min(max(y + dy, 0), h - 1)
            else:
                map_x[y, x] = float(x)
                map_y[y, x] = float(y)

    return cv2.remap(
        image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT
    )


def _apply_fold_warp(
    image: np.ndarray,
    severity: float,
    rng: random.Random,
) -> np.ndarray:
    """Fold along a diagonal or horizontal line with displacement.

    Simulates a page folded at a crease; one region is shifted/reflected
    slightly to create a visible fold boundary.

    Args:
        image: BGR image array.
        severity: Fold strength in [0, 1].
        rng: Random instance.

    Returns:
        Folded BGR image array.
    """
    h, w = image.shape[:2]
    result = image.copy()

    fold_type = rng.choice(("horizontal", "vertical", "diagonal"))
    max_shift = int(severity * min(h, w) * 0.12)
    shift = rng.randint(1, max(1, max_shift))

    if fold_type == "horizontal":
        fold_y = int(h * rng.uniform(0.3, 0.7))
        # Shift lower half
        if fold_y + shift < h:
            result[fold_y + shift :, :] = image[fold_y : h - shift, :]
            result[fold_y : fold_y + shift, :] = image[fold_y : fold_y + 1, :]

    elif fold_type == "vertical":
        fold_x = int(w * rng.uniform(0.3, 0.7))
        if fold_x + shift < w:
            result[:, fold_x + shift :] = image[:, fold_x : w - shift]
            result[:, fold_x : fold_x + shift] = image[:, fold_x : fold_x + 1]

    else:  # diagonal
        # Simple shear distortion along diagonal
        angle = rng.uniform(-severity * 5.0, severity * 5.0)
        M_shear = np.float32([[1, math.tan(math.radians(angle)), 0], [0, 1, 0]])
        result = cv2.warpAffine(image, M_shear, (w, h), borderMode=cv2.BORDER_REPLICATE)

    return result


_WARP_FNS = {
    "perspective": _apply_perspective_warp,
    "page_curl": _apply_page_curl,
    "fold": _apply_fold_warp,
}


def _augment_image(
    image_bytes: bytes,
    severity: float,
    warp_type: str,
    rng: random.Random,
) -> bytes:
    """Load image bytes, apply warp, return JPEG bytes.

    Args:
        image_bytes: Raw JPEG/PNG bytes from GCS.
        severity: Warp severity in [0, 1].
        warp_type: One of ``VALID_WARP_TYPES``.
        rng: Seeded random instance.

    Returns:
        JPEG-encoded bytes of the augmented image.
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        msg = "cv2.imdecode returned None — corrupt image bytes?"
        raise ValueError(msg)

    # page_curl uses a pixel loop so we pre-shrink for performance
    if warp_type == "page_curl":
        max_side = 384
        h, w = image.shape[:2]
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            image = cv2.resize(
                image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )

    warp_fn = _WARP_FNS.get(warp_type, _apply_perspective_warp)
    warped = warp_fn(image, severity, rng)

    ok, buf = cv2.imencode(".jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
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
    warp_type: str,
    images_dir: Path,
    rng: random.Random,
    dry_run: bool,
) -> _WarpResult:
    """Download, warp, and save one image.

    Args:
        record: Candidate image metadata from v3 pool.
        bucket: GCS Bucket client.
        severity: Exact severity value to apply.
        warp_type: Which warp function to use.
        images_dir: Local directory for output images.
        rng: Seeded random instance.
        dry_run: Skip GCS download and disk write if True.

    Returns:
        ``_WarpResult`` with relative path and metadata.
    """
    out_name = f"{record.uuid}_warp.jpg"
    rel_path = f"images/{out_name}"
    out_path = images_dir / out_name

    if not dry_run:
        raw = _download_blob_bytes(bucket, record.gcs_image_key)
        aug_bytes = _augment_image(raw, severity, warp_type, rng)
        out_path.write_bytes(aug_bytes)

    return _WarpResult(
        image_path=rel_path,
        severity=round(severity, 4),
        warping_type=warp_type,
        provenance="synthetic_v3",
        script=record.script,
        split=record.split,
    )


def run_generation(args: argparse.Namespace) -> int:
    """Run the warping view generation pipeline.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 = success).
    """
    _setup_logging(args.verbose)
    rng = random.Random(args.seed)
    start = time.time()

    warp_types: list[str] = args.warp_types or DEFAULT_WARP_TYPES
    for wt in warp_types:
        if wt not in VALID_WARP_TYPES:
            logger.error("Unknown warp type %r. Valid: %s", wt, VALID_WARP_TYPES)
            return 1

    severity_min, severity_max = args.severity_range
    if severity_min < 0.0 or severity_max > 1.0 or severity_min >= severity_max:
        logger.error("severity-range must satisfy 0 ≤ min < max ≤ 1")
        return 1

    bucket_name, v3_prefix = _parse_gcs_prefix(args.v3_gcs_prefix)
    bucket = _get_gcs_bucket(bucket_name)
    pool = _load_splits_pool(bucket, v3_prefix)
    if not pool:
        logger.error("No images found in splits registry")
        return 1

    candidates = _stratified_sample(pool, args.count, rng)
    if not candidates:
        logger.error("No candidates after sampling")
        return 1

    logger.info("Sampled %d candidates from %d scripts", len(candidates), len(pool))

    output_dir: Path = args.output_dir
    images_dir = output_dir / "images"
    if not args.dry_run:
        images_dir.mkdir(parents=True, exist_ok=True)

    try:
        from tqdm import tqdm  # type: ignore[import-untyped]

        progress: Any = tqdm(candidates, desc="Warp view", unit="img")
    except ImportError:
        progress = candidates

    results: list[_WarpResult] = []
    errors = 0

    for record in progress:
        severity = rng.uniform(severity_min, severity_max)
        warp_type = rng.choice(warp_types)
        try:
            result = _process_record(
                record, bucket, severity, warp_type, images_dir, rng, args.dry_run
            )
            results.append(result)
        except Exception:
            logger.exception("Failed on %s/%s", record.script, record.uuid)
            errors += 1

    elapsed = time.time() - start
    throughput = len(results) / elapsed if elapsed > 0 else 0.0

    manifest_path = output_dir / "warping_metadata.json"
    manifest_records = [
        {
            "image_path": r.image_path,
            "severity": r.severity,
            "warping_type": r.warping_type,
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

    warp_type_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    for r in results:
        warp_type_counts[r.warping_type] = warp_type_counts.get(r.warping_type, 0) + 1
        split_counts[r.split] = split_counts.get(r.split, 0) + 1

    logger.info(
        "Done: %d images, %d errors | %.1fs | %.1f img/s",
        len(results),
        errors,
        elapsed,
        throughput,
    )
    logger.info("Warp type distribution: %s", warp_type_counts)
    logger.info("Split distribution: %s", split_counts)
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
        description="Generate warping-augmented view from synth-multiscript-v3.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--v3-gcs-prefix",
        type=str,
        default="gs://image_detection_b/synth_multiscript_v3",
        help="GCS prefix for v3 dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Local directory for output images and warping_metadata.json.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Number of warped images to generate (default: {DEFAULT_COUNT}).",
    )
    parser.add_argument(
        "--severity-range",
        type=float,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=[DEFAULT_SEVERITY_MIN, DEFAULT_SEVERITY_MAX],
        help=f"Severity range (default: {DEFAULT_SEVERITY_MIN} {DEFAULT_SEVERITY_MAX}).",
    )
    parser.add_argument(
        "--warp-types",
        type=str,
        nargs="+",
        choices=VALID_WARP_TYPES,
        default=list(DEFAULT_WARP_TYPES),
        help=f"Warp types to include. Choices: {VALID_WARP_TYPES}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without downloading or writing output.",
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
