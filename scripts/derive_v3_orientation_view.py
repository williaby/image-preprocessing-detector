#!/usr/bin/env python3
"""Sample non-Latin v3 images for the orientation dataset's synthetic component.

Reads v3 splits.jsonl to build a candidate pool of images whose script is NOT
Latin (``Latn``). For each sampled image, reads its sidecar JSON to get the
ground-truth orientation class (0 / 90 / 180 / 270°), which was assigned at
generation time, then downloads and resizes the image to 224px.

Output is a flat JSON manifest consumed by
``prepare_multitask_datasets.py orientation`` sub-command.

Each output record contains:

- ``image_path``: relative path within output-dir (``images/{uuid}_orient.jpg``)
- ``orientation``: int in {0, 90, 180, 270} from v3 sidecar
- ``provenance``: ``"synthetic_v3"``
- ``script``: ISO 15924 folder name (e.g. ``"Arab"``)
- ``split``: from v3 split registry
- ``document_id``: uuid used as document_id for deterministic split validation

The orientation dataset mixing cap is ≤40% synthetic.  For a 50K dataset this
means ≤20K synthetic images.  Default ``--target-per-class 5000`` gives 20K
(4 classes × 5K).

Usage::

    python scripts/derive_v3_orientation_view.py \\
        --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \\
        --output-dir /mnt/e/03_training_datasets/orientation_v2/synthetic \\
        --target-per-class 5000 \\
        --target-size 224

    # Dry run (no downloads)
    python scripts/derive_v3_orientation_view.py \\
        --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \\
        --output-dir /tmp/orient_synth --target-per-class 100 --dry-run

Requires: google-cloud-storage, opencv-python, numpy, tqdm
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any, NamedTuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Orientation classes supported by the training contract
VALID_ORIENTATIONS = {0, 90, 180, 270}
# Latin script folder name in v3 GCS structure
LATIN_SCRIPT_FOLDER = "Latn"
DEFAULT_TARGET_PER_CLASS = 5_000
DEFAULT_TARGET_SIZE = 224
JPEG_QUALITY = 92


class _ImageRecord(NamedTuple):
    """Candidate image record from v3 pool."""

    script: str
    uuid: str
    split: str
    orientation: int  # from v3 sidecar (0/90/180/270)
    gcs_image_key: str
    gcs_sidecar_key: str


class _OrientResult(NamedTuple):
    """Output record written to metadata manifest."""

    image_path: str
    orientation: int
    provenance: str
    script: str
    split: str
    document_id: str


# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------


def _get_gcs_bucket(bucket_name: str) -> Any:
    """Return a GCS Bucket client."""
    from google.cloud import storage  # type: ignore[import-untyped]

    return storage.Client().bucket(bucket_name)


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
# Pool building
# ---------------------------------------------------------------------------


def _parse_orientation_from_sidecar(sidecar_json: dict[str, Any]) -> int | None:
    """Extract orientation class from v3 sidecar JSON.

    v3 sidecar stores orientation under ``data.geometric.orientation_class``.
    Valid values: 0, 90, 180, 270.

    Args:
        sidecar_json: Parsed sidecar JSON dict.

    Returns:
        Orientation in degrees, or None if missing/invalid.
    """
    try:
        orient = sidecar_json["data"]["geometric"]["orientation_class"]
        if int(orient) in VALID_ORIENTATIONS:
            return int(orient)
    except (KeyError, TypeError, ValueError):
        pass
    return None


def _load_splits_pool_with_orientation(
    bucket: Any,
    v3_prefix: str,
    exclude_scripts: set[str],
    batch_sidecar_limit: int = 5_000,
) -> dict[int, list[_ImageRecord]]:
    """Download splits.jsonl and fetch sidecar orientation for each candidate.

    Builds a per-orientation candidate pool, excluding specified scripts.
    Sidecar JSONs are fetched in a limited batch to avoid excessive GCS requests.

    Strategy: download splits.jsonl to get {uuid, split, script}, then batch-
    download sidecar JSONs for orientation. If ``batch_sidecar_limit`` is
    reached per orientation class, stop (we have enough candidates).

    Args:
        bucket: GCS Bucket client.
        v3_prefix: GCS prefix without trailing slash.
        exclude_scripts: Script folder names to exclude (e.g. {``"Latn"``}).
        batch_sidecar_limit: Maximum sidecars to fetch per orientation class.

    Returns:
        Mapping from orientation degrees to list of ``_ImageRecord``.
    """
    splits_key = f"{v3_prefix}/splits.jsonl"
    logger.info("Downloading splits registry …")
    content = bucket.blob(splits_key).download_as_text()

    # First pass: collect non-excluded candidates grouped by script
    candidates_by_script: dict[
        str, list[tuple[str, str]]
    ] = {}  # script → [(uuid, split)]
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
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
            continue

        if script in exclude_scripts:
            continue
        candidates_by_script.setdefault(script, []).append((uuid, split))

    total_candidates = sum(len(v) for v in candidates_by_script.values())
    logger.info(
        "Non-excluded candidates: %d across %d scripts",
        total_candidates,
        len(candidates_by_script),
    )

    # Second pass: fetch sidecars to get orientation
    # Flatten and shuffle for even script distribution
    all_candidates: list[tuple[str, str, str]] = []  # [(script, uuid, split)]
    for script, items in candidates_by_script.items():
        for uuid, split in items:
            all_candidates.append((script, uuid, split))

    rng_shuffle = random.Random(42)
    rng_shuffle.shuffle(all_candidates)

    pool: dict[int, list[_ImageRecord]] = {o: [] for o in VALID_ORIENTATIONS}
    fetched = 0
    skipped = 0

    logger.info(
        "Fetching sidecar JSONs for orientation labels (limit %d/class) …",
        batch_sidecar_limit,
    )

    for script, uuid, split in all_candidates:
        # Stop early if all orientation classes are saturated
        if all(len(pool[o]) >= batch_sidecar_limit for o in VALID_ORIENTATIONS):
            break

        sidecar_key = f"{v3_prefix}/{script}/{uuid}.json"
        try:
            sidecar_bytes = _download_blob_bytes(bucket, sidecar_key)
            sidecar = json.loads(sidecar_bytes)
            orientation = _parse_orientation_from_sidecar(sidecar)
        except Exception:
            skipped += 1
            continue

        if orientation is None:
            skipped += 1
            continue

        if len(pool[orientation]) >= batch_sidecar_limit:
            continue

        gcs_img_key = f"{v3_prefix}/{script}/{uuid}.jpg"
        gcs_sidecar_key = f"{v3_prefix}/{script}/{uuid}.json"
        rec = _ImageRecord(
            script=script,
            uuid=uuid,
            split=split,
            orientation=orientation,
            gcs_image_key=gcs_img_key,
            gcs_sidecar_key=gcs_sidecar_key,
        )
        pool[orientation].append(rec)
        fetched += 1

    logger.info(
        "Sidecar fetch: %d fetched, %d skipped | Per-class counts: %s",
        fetched,
        skipped,
        {o: len(pool[o]) for o in VALID_ORIENTATIONS},
    )
    return pool


# ---------------------------------------------------------------------------
# Stratified sampling (balanced across orientations)
# ---------------------------------------------------------------------------


def _balanced_sample(
    pool: dict[int, list[_ImageRecord]],
    target_per_class: int,
    rng: random.Random,
) -> list[_ImageRecord]:
    """Sample up to ``target_per_class`` records per orientation class.

    Args:
        pool: Per-orientation candidate lists.
        target_per_class: Maximum samples per orientation.
        rng: Seeded random instance.

    Returns:
        Flat shuffled list of sampled records.
    """
    sampled: list[_ImageRecord] = []
    for orientation, records in pool.items():
        take = min(target_per_class, len(records))
        chosen = rng.sample(records, take)
        sampled.extend(chosen)
        logger.info(
            "Orientation %d°: taking %d / %d available", orientation, take, len(records)
        )

    rng.shuffle(sampled)
    return sampled


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------


def _resize_image(image: np.ndarray, target_size: int) -> np.ndarray:
    """Resize image so its longer side equals ``target_size``.

    Args:
        image: BGR numpy array.
        target_size: Target size in pixels for the longer dimension.

    Returns:
        Resized image.
    """
    h, w = image.shape[:2]
    if max(h, w) == target_size:
        return image
    scale = target_size / max(h, w)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _process_record(
    record: _ImageRecord,
    bucket: Any,
    target_size: int,
    images_dir: Path,
    dry_run: bool,
) -> _OrientResult:
    """Download, resize, and save one orientation image.

    Args:
        record: Candidate image from v3 pool.
        bucket: GCS Bucket client.
        target_size: Resize target (pixels on longer side).
        images_dir: Output image directory.
        dry_run: If True, skip download and write.

    Returns:
        ``_OrientResult`` metadata record.
    """
    out_name = f"{record.uuid}_orient.jpg"
    rel_path = f"images/{out_name}"
    out_path = images_dir / out_name

    if not dry_run:
        raw = _download_blob_bytes(bucket, record.gcs_image_key)
        arr = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            msg = f"Failed to decode image for uuid={record.uuid}"
            raise ValueError(msg)
        image = _resize_image(image, target_size)
        ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not ok:
            msg = "cv2.imencode failed"
            raise RuntimeError(msg)
        out_path.write_bytes(buf.tobytes())

    return _OrientResult(
        image_path=rel_path,
        orientation=record.orientation,
        provenance="synthetic_v3",
        script=record.script,
        split=record.split,
        document_id=record.uuid,
    )


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def run_derivation(args: argparse.Namespace) -> int:
    """Run the v3 orientation view derivation pipeline.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 = success).
    """
    _setup_logging(args.verbose)
    rng = random.Random(args.seed)
    start = time.time()

    bucket_name, v3_prefix = _parse_gcs_prefix(args.v3_gcs_prefix)
    bucket = _get_gcs_bucket(bucket_name)

    exclude_scripts: set[str] = (
        set(args.exclude_scripts) if args.exclude_scripts else {LATIN_SCRIPT_FOLDER}
    )
    logger.info("Excluding scripts: %s", sorted(exclude_scripts))

    # Sidecar limit: fetch enough candidates per class to cover target + headroom
    sidecar_limit = args.target_per_class * 3
    pool = _load_splits_pool_with_orientation(
        bucket, v3_prefix, exclude_scripts, sidecar_limit
    )

    candidates = _balanced_sample(pool, args.target_per_class, rng)
    if not candidates:
        logger.error("No candidates after sampling")
        return 1

    logger.info("Total candidates sampled: %d", len(candidates))

    output_dir: Path = args.output_dir
    images_dir = output_dir / "images"
    if not args.dry_run:
        images_dir.mkdir(parents=True, exist_ok=True)

    try:
        from tqdm import tqdm  # type: ignore[import-untyped]

        progress: Any = tqdm(candidates, desc="Orientation (v3)", unit="img")
    except ImportError:
        progress = candidates

    results: list[_OrientResult] = []
    errors = 0

    for record in progress:
        try:
            result = _process_record(
                record, bucket, args.target_size, images_dir, args.dry_run
            )
            results.append(result)
        except Exception:
            logger.exception("Failed on %s/%s", record.script, record.uuid)
            errors += 1

    elapsed = time.time() - start
    throughput = len(results) / elapsed if elapsed > 0 else 0.0

    manifest_path = output_dir / "orientation_synthetic_metadata.json"
    manifest_records = [
        {
            "image_path": r.image_path,
            "orientation": r.orientation,
            "provenance": r.provenance,
            "script": r.script,
            "split": r.split,
            "document_id": r.document_id,
        }
        for r in results
    ]

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest_records, f, indent=2)

    orient_counts: dict[int, int] = {}
    for r in results:
        orient_counts[r.orientation] = orient_counts.get(r.orientation, 0) + 1

    logger.info(
        "Done: %d images, %d errors | %.1fs | %.1f img/s",
        len(results),
        errors,
        elapsed,
        throughput,
    )
    logger.info("Orientation distribution: %s", orient_counts)
    if not args.dry_run:
        logger.info("Manifest: %s", manifest_path)

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
        description="Derive orientation synthetic component from synth-multiscript-v3 (non-Latin).",
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
        help="Output directory for images and orientation_synthetic_metadata.json.",
    )
    parser.add_argument(
        "--target-per-class",
        type=int,
        default=DEFAULT_TARGET_PER_CLASS,
        help=f"Maximum images per orientation class (default: {DEFAULT_TARGET_PER_CLASS}).",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=DEFAULT_TARGET_SIZE,
        help=f"Resize longer side to this many pixels (default: {DEFAULT_TARGET_SIZE}).",
    )
    parser.add_argument(
        "--exclude-scripts",
        type=str,
        nargs="+",
        default=[LATIN_SCRIPT_FOLDER],
        help=f"Script folder names to exclude (default: [{LATIN_SCRIPT_FOLDER}]).",
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
        help="Sample and report counts without downloading images.",
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
    return run_derivation(args)


if __name__ == "__main__":
    sys.exit(main())
