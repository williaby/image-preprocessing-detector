#!/usr/bin/env python3
"""Prepare multi-task training datasets for the SigLIP 2 teacher model.

Five sub-commands prepare individual task datasets; the ``merge`` sub-command
combines them into the unified ``train_manifest.json`` and ``val_manifest.json``
consumed by ``modal/train_siglip2_multitask.py``.

**Training contract** (from ``modal/train_siglip2_multitask.py``):

- Flat JSON list (NOT ``{"samples": [...]}``).
- ``image_path`` is relative to ``/data/`` (Modal Volume mount point).
- ``script``: str in the 19-class set (e.g. ``"LATN"``, ``"ARAB"``).
- ``source``: str in ``{"scanned", "camera", "born_digital", "synthetic"}``.
- ``orientation``: int in ``{0, 90, 180, 270}``.
- ``shadow``: float ``[0, 1]``.
- ``warping``: float ``[0, 1]``.
- Samples may have any subset of labels; missing tasks are masked.

**Real/Synthetic Mixing Caps**:

| Task        | Real minimum | Synthetic cap |
|-------------|-------------|---------------|
| Script      | ≥ 40 %      | ≤ 60 % (v3)  |
| Orientation | ≥ 60 %      | ≤ 40 % (v3)  |
| Source      | ≥ 95 %      | Augmentation only |
| Shadow      | ≥ 50 %      | ≤ 50 % (v3)  |
| Warping     | ≥ 70 %      | ≤ 30 % (v3)  |

Usage::

    # Script (dry-run first)
    python scripts/prepare_multitask_datasets.py script \\
        --mdiw13-dir /mnt/e/image_detection/mdiw13 \\
        --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \\
        --output-dir /mnt/e/03_training_datasets/script_training \\
        --dry-run

    # Shadow
    python scripts/prepare_multitask_datasets.py shadow \\
        --synthetic-metadata /mnt/e/03_training_datasets/shadow_synthetic/shadow_metadata.json \\
        --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json \\
        --output-dir /mnt/e/03_training_datasets/shadow_training --dry-run

    # Merge all task dirs + upload to GCS
    python scripts/prepare_multitask_datasets.py merge \\
        --script-dir /mnt/e/03_training_datasets/script_training \\
        --orientation-dir /mnt/e/03_training_datasets/orientation_training \\
        --source-dir /mnt/e/03_training_datasets/source_training \\
        --shadow-dir /mnt/e/03_training_datasets/shadow_training \\
        --warping-dir /mnt/e/03_training_datasets/warping_training \\
        --gcs-output-prefix gs://image_detection_b/datasets/multitask_training

Requires: click, google-cloud-storage, tqdm
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import time
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Training contract constants (mirrors modal/train_siglip2_multitask.py)
# ---------------------------------------------------------------------------

SCRIPT_ML_CLASSES = (
    "LATN",
    "CYRL",
    "GREK",
    "ARAB",
    "HEBR",
    "DEVA",
    "BENG",
    "TAML",
    "TELU",
    "HANS",
    "HANT",
    "JPAN",
    "KORE",
    "THAI",
    "TIBT",
    "INDIC_OTHER",
    "SE_ASIAN_OTHER",
    "OTHER",
    "UNKNOWN",
)
VALID_SCRIPTS: frozenset[str] = frozenset(SCRIPT_ML_CLASSES)
VALID_SOURCES: frozenset[str] = frozenset(
    ("scanned", "camera", "born_digital", "synthetic")
)
# ISO 15924 codes reserved exclusively for OOD evaluation across ALL data sources.
# Must stay in sync with OOD_ONLY_SCRIPTS in scripts/generate_base_dataset_v3.py.
# Armn/Goth: only 5 SALAMI samples each — too few for training, reserved for OOD.
# Goth is not in v3 synthetic data but exists in SALAMI real data.
OOD_RESERVED_SCRIPTS: frozenset[str] = frozenset(
    {"Armn", "Geor", "Goth", "Mong", "Syrc"}
)
VALID_ORIENTATIONS: frozenset[int] = frozenset((0, 90, 180, 270))

# L2 capture_method → training source class (4-class: born_digital/scanned/camera/synthetic)
# ADF and FAX are merged into "scanned" for v1; they will be separated in v2
# once ≥2K examples per sub-class are available.
L2_TO_SOURCE_CLASS: dict[str, str | None] = {
    "born_digital": "born_digital",
    "scanner": "scanned",  # bare value used by rvl_cdip L2 enrichment
    "scanner_flatbed": "scanned",
    "scanner_adf": "scanned",  # merged into scanned for v1
    "camera": "camera",  # bare value for generic camera captures
    "camera_smartphone": "camera",
    "camera_professional": "camera",
    "fax": "scanned",  # merged into scanned for v1
    "synthetic": "synthetic",  # DocSynth300K, synth-multiscript-v3
    "unknown": None,
}

# Mixing caps per task (max fraction from synthetic sources)
SYNTHETIC_CAPS: dict[str, float] = {
    "script": 0.60,
    "orientation": 0.40,
    "source": 0.05,
    "shadow": 0.50,
    "warping": 0.30,
}


# ---------------------------------------------------------------------------
# OOD leakage detection helpers
# ---------------------------------------------------------------------------


def _compute_sha256(image_path: Path) -> str:
    """Compute SHA256 hash of image file bytes.

    Args:
        image_path: Path to the image file.

    Returns:
        Hex-encoded SHA256 digest string.
    """
    hasher = hashlib.sha256()
    with image_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_ood_registry(ood_registry_path: Path) -> set[str]:
    """Load OOD registry SHA256 hashes from a JSONL file.

    Returns an empty set if the registry file is missing or empty.
    Each line must be a JSON object with a ``sha256`` key.

    Args:
        ood_registry_path: Path to ``metadata_registry/ood_registry.jsonl``.

    Returns:
        Set of SHA256 hex strings for OOD-reserved images.
    """
    if not ood_registry_path.exists():
        return set()
    ood_hashes: set[str] = set()
    with ood_registry_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if sha256 := entry.get("sha256"):
                    ood_hashes.add(sha256)
            except json.JSONDecodeError:
                continue
    return ood_hashes


def _check_ood_leakage(
    samples: list[dict[str, Any]],
    ood_registry_path: Path,
    image_root: Path | None = None,
) -> None:
    """Halt build if any sample SHA256 matches the OOD registry.

    OOD images are exclusively reserved for final hold-out evaluation and
    must never appear in training or validation manifests.  This function
    hashes each sample's image file and compares against the registry;
    it exits with code 2 if any match is detected.

    When the registry is empty or missing the check is skipped with a warning
    so that the guard is a no-op until OOD images are registered.

    Args:
        samples: List of manifest sample dicts (must have ``image_path`` key).
        ood_registry_path: Path to ``metadata_registry/ood_registry.jsonl``.
        image_root: Optional root prepended to relative ``image_path`` values.

    Raises:
        SystemExit: With code 2 if OOD leakage is detected.
    """
    ood_hashes = _load_ood_registry(ood_registry_path)
    if not ood_hashes:
        click.echo(
            f"WARNING: OOD registry empty or missing — leakage check skipped. "
            f"Create {ood_registry_path} with entries to enable enforcement.",
            err=True,
        )
        return

    leakage: list[str] = []
    for sample in samples:
        img_path_str = sample.get("image_path", "")
        img_path = Path(img_path_str)
        if image_root and not img_path.is_absolute():
            img_path = image_root / img_path
        if not img_path.exists():
            continue
        sha256 = _compute_sha256(img_path)
        if sha256 in ood_hashes:
            leakage.append(img_path_str)

    if leakage:
        click.echo(
            f"ERROR: OOD LEAKAGE DETECTED: {len(leakage)} OOD images found in training manifest.\n"
            f"  First 5 offenders: {leakage[:5]}\n"
            f"  These images are registered in {ood_registry_path} as OOD holdout.\n"
            f"  Remove them from the source dataset or mark split_type='ood' and exclude.",
            err=True,
        )
        raise SystemExit(2)

    click.echo(
        f"OOD leakage check passed ({len(samples)} samples, {len(ood_hashes)} OOD hashes checked)"
    )


# ---------------------------------------------------------------------------
# Deterministic SHA256 split assignment
# ---------------------------------------------------------------------------


def _deterministic_split(document_id: str) -> str:
    """Assign a train/val/test split based on SHA256 of document_id.

    Uses first two hex chars of SHA256 digest:
    - ``00``–``cc``: train (~80 %)
    - ``cd``–``e5``: val   (~10 %)
    - ``e6``–``ff``: test  (~10 %)

    Args:
        document_id: Stable identifier for the source document.

    Returns:
        ``"train"``, ``"val"``, or ``"test"``.
    """
    digest = hashlib.sha256(document_id.encode()).hexdigest()
    prefix = int(digest[:2], 16)  # 0-255
    if prefix <= 0xCC:
        return "train"
    if prefix <= 0xE5:
        return "val"
    return "test"


# ---------------------------------------------------------------------------
# Mixing ratio validation
# ---------------------------------------------------------------------------


def _check_mixing_ratio(
    samples: list[dict[str, Any]],
    max_synthetic_pct: float,
    task_label: str,
) -> None:
    """Log a warning if synthetic fraction exceeds the configured cap.

    Args:
        samples: All samples for this task.
        max_synthetic_pct: Maximum allowed synthetic fraction (0–1).
        task_label: Task name for log messages.
    """
    total = len(samples)
    if total == 0:
        return
    n_synthetic = sum(1 for s in samples if s.get("provenance") == "synthetic_v3")
    synth_frac = n_synthetic / total
    real_frac = 1.0 - synth_frac

    logger.info(
        "[%s] Real/synthetic split: %.1f%% real / %.1f%% synthetic (%d / %d)",
        task_label,
        real_frac * 100,
        synth_frac * 100,
        total - n_synthetic,
        n_synthetic,
    )

    if synth_frac > max_synthetic_pct:
        logger.warning(
            "[%s] MIXING CAP EXCEEDED: %.1f%% synthetic > %.0f%% cap. "
            "Reduce synthetic samples or add more real data.",
            task_label,
            synth_frac * 100,
            max_synthetic_pct * 100,
        )


# ---------------------------------------------------------------------------
# Script class weight computation
# ---------------------------------------------------------------------------


def _compute_class_weights(
    samples: list[dict[str, Any]],
    label_field: str,
    all_classes: tuple[str, ...],
) -> list[float]:
    """Compute inverse-frequency class weights for balanced training.

    Args:
        samples: Training split samples with ``label_field`` key.
        label_field: Dict key for the class label string.
        all_classes: Ordered tuple of all valid class names.

    Returns:
        List of weights, one per class, in class order. Rare classes get
        higher weight; weights are normalised so the mean is 1.0.
    """
    counts = dict.fromkeys(all_classes, 0)
    for s in samples:
        cls = s.get(label_field)
        if cls and cls in counts:
            counts[cls] += 1

    total = sum(counts.values())
    if total == 0:
        return [1.0] * len(all_classes)

    weights = []
    for cls in all_classes:
        count = counts[cls]
        # Inverse frequency; floor at 1 to avoid division by zero
        weight = total / max(count, 1)
        weights.append(weight)

    # Normalise so mean weight = 1.0
    mean_w = sum(weights) / len(weights)
    weights = [w / mean_w for w in weights]
    return weights


# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------


def _parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    """Split ``gs://bucket/prefix`` → ``(bucket_name, prefix)``."""
    if not gcs_path.startswith("gs://"):
        msg = f"Expected gs:// path, got {gcs_path!r}"
        raise ValueError(msg)
    rest = gcs_path[5:]
    parts = rest.split("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _get_gcs_bucket(bucket_name: str) -> Any:
    """Return an authenticated GCS Bucket client."""
    from google.cloud import storage  # type: ignore[import-untyped]

    return storage.Client().bucket(bucket_name)


def _upload_manifest(
    records: list[dict[str, Any]],
    bucket: Any,
    gcs_key: str,
    dry_run: bool = False,
) -> None:
    """Upload a JSON manifest (flat list) to GCS.

    Args:
        records: Flat list of sample dicts.
        bucket: GCS Bucket client.
        gcs_key: Destination object key.
        dry_run: Skip actual upload if True.
    """
    if dry_run:
        logger.info(
            "[DRY-RUN] Would upload %d records to gs://%s/%s",
            len(records),
            bucket.name,
            gcs_key,
        )
        return
    blob = bucket.blob(gcs_key)
    blob.upload_from_string(
        json.dumps(records, indent=2), content_type="application/json"
    )
    logger.info(
        "Uploaded manifest (%d records) → gs://%s/%s",
        len(records),
        bucket.name,
        gcs_key,
    )


def _upload_images(
    image_records: list[dict[str, Any]],
    local_images_dir: Path,
    bucket: Any,
    gcs_prefix: str,
    image_path_field: str = "image_path",
    dry_run: bool = False,
) -> None:
    """Upload local images to GCS.

    Args:
        image_records: List of manifest records with ``image_path`` field.
        local_images_dir: Root directory where images live locally.
        bucket: GCS Bucket client.
        gcs_prefix: GCS prefix to upload images under.
        image_path_field: Key name for the image path in each record.
        dry_run: Skip actual upload if True.
    """
    try:
        from tqdm import tqdm  # type: ignore[import-untyped]

        progress: Any = tqdm(image_records, desc="Uploading images", unit="img")
    except ImportError:
        progress = image_records

    uploaded = 0
    errors = 0
    for record in progress:
        rel_path = record.get(image_path_field, "")
        local_path = local_images_dir / rel_path
        if not local_path.exists():
            errors += 1
            logger.debug("Image not found: %s", local_path)
            continue
        if not dry_run:
            gcs_key = f"{gcs_prefix}/{rel_path}"
            bucket.blob(gcs_key).upload_from_filename(str(local_path))
        uploaded += 1

    logger.info(
        "Image upload: %d uploaded, %d not found%s",
        uploaded,
        errors,
        " [DRY-RUN]" if dry_run else "",
    )


# ---------------------------------------------------------------------------
# L2 metadata helpers
# ---------------------------------------------------------------------------


def _read_l2_records(
    l2_dir: Path,
    dataset_names: list[str],
    field: str,
) -> list[dict[str, Any]]:
    """Read L2 metadata records with a specific field from dataset JSON files.

    Searches for ``{l2_dir}/{dataset_name}.json`` (single-file per dataset)
    or ``{l2_dir}/{dataset_name}/`` directory of per-image JSONs.
    Skips records where ``field`` is missing or confidence < 0.5.

    Args:
        l2_dir: Root L2 metadata directory.
        dataset_names: Dataset names to scan.
        field: L2 field name to filter for (e.g. ``"shadow_severity"``).

    Returns:
        List of record dicts with at least ``field``, ``image_path``, ``provenance``.
    """
    records: list[dict[str, Any]] = []

    for dataset in dataset_names:
        paths = _resolve_l2_paths(l2_dir, dataset)
        if not paths:
            logger.warning(
                "L2 metadata not found for dataset %r at %s", dataset, l2_dir
            )
            continue
        for jf in paths:
            records.extend(_parse_l2_file(jf, field, dataset))

    logger.info(
        "L2 metadata: loaded %d records with '%s' from %s",
        len(records),
        field,
        dataset_names,
    )
    return records


def _expand_l2_samples(data: Any) -> list[dict[str, Any]]:
    """Normalize L2 JSON data to a flat list of per-sample record dicts.

    Handles three L2 format variants:

    * Flat list: ``[{...}, {...}]``
    * Aggregated dataset: ``{"samples": [{...}, ...], ...}``
    * Single flat record: ``{...}``

    Args:
        data: Parsed JSON value (list, dict, or other).

    Returns:
        List of per-sample dicts.
    """
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        # Aggregated format: top-level dict whose samples live under "samples"
        if "samples" in data and isinstance(data["samples"], list):
            return [s for s in data["samples"] if isinstance(s, dict)]
        return [data]
    return []


def _get_field_from_l2_sample(sample: dict[str, Any], field: str) -> Any:
    """Extract a named field from an L2 sample, checking multiple schema locations.

    Search order:
    1. Top-level key (flat/legacy records).
    2. ``metadata.data.{field}`` (some intermediate flat formats).
    3. ``enrichments.versions[-1].data.{field}`` (aggregated dataset format).
    4. ``original_labels.{field}`` (raw labels — fallback for known fields).

    Args:
        sample: Per-sample record dict.
        field: Field name to look up.

    Returns:
        The field value, or ``None`` if not found.
    """
    # 1. Direct top-level key
    value = sample.get(field)
    if value is not None:
        return value
    # 2. Nested under metadata.data
    value = (sample.get("metadata") or {}).get("data", {}).get(field)
    if value is not None:
        return value
    # 3. Latest enrichment version data dict
    versions: list[dict[str, Any]] = (sample.get("enrichments") or {}).get(
        "versions", []
    )
    if versions:
        latest_data = versions[-1].get("data", {})
        value = latest_data.get(field)
        if value is not None:
            return value
    # 4. original_labels (raw dataset labels — covers fields like capture_method)
    value = (sample.get("original_labels") or {}).get(field)
    return value


def _get_image_path_from_l2_sample(sample: dict[str, Any]) -> str:
    """Extract the image path from an L2 sample record.

    Args:
        sample: Per-sample record dict.

    Returns:
        Image path string, or empty string if not found.
    """
    for key in ("image_path", "file_path", "filename"):
        val = sample.get(key)
        if val:
            return str(val)
    # Aggregated format stores the path at source.original_path
    src = sample.get("source") or {}
    if src.get("original_path"):
        return str(src["original_path"])
    return ""


def _parse_l2_file(
    json_path: Path,
    field: str,
    dataset_name: str,
) -> list[dict[str, Any]]:
    """Parse one L2 JSON file and return records containing ``field``.

    Supports flat lists, single-record dicts, and aggregated dataset format
    (``{"samples": [...], ...}``) with enrichments nested under
    ``enrichments.versions[-1].data``.

    Args:
        json_path: Path to L2 JSON.
        field: Field name to extract (e.g. ``"shadow_severity"``).
        dataset_name: Dataset name for provenance annotation.

    Returns:
        List of extracted record dicts.
    """
    try:
        with open(json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.debug("Cannot parse L2 JSON: %s", json_path)
        return []

    results: list[dict[str, Any]] = []
    for sample in _expand_l2_samples(data):
        value = _get_field_from_l2_sample(sample, field)
        if value is None:
            continue

        # Low-confidence exclusion for shadow/warping severity fields
        conf_field = field.replace("_severity", "_confidence")
        confidence = float(_get_field_from_l2_sample(sample, conf_field) or 1.0)
        if confidence < 0.5:
            continue

        image_path = _get_image_path_from_l2_sample(sample)
        results.append(
            {
                "image_path": image_path,
                field: float(value),
                "provenance": "real_paired",
                "source_dataset": dataset_name,
                "split_type": "train",
                "ood_categories": [],
            }
        )

    return results


def _resolve_l2_paths(l2_dir: Path, dataset_name: str) -> list[Path]:
    """Resolve all L2 JSON paths for a dataset name.

    Tries the following candidates in order:

    1. ``{l2_dir}/{dataset_name}.json``
    2. ``{l2_dir}/{dataset_name}_metadata.json`` (project-standard naming)
    3. ``{l2_dir}/{dataset_name}/`` directory (all ``*.json`` files)

    Args:
        l2_dir: Root L2 metadata directory.
        dataset_name: Dataset identifier (e.g. ``"doclaynet"``, ``"sd7k"``).

    Returns:
        List of existing JSON Paths to parse. Empty list if none found.
    """
    for candidate in (
        l2_dir / f"{dataset_name}.json",
        l2_dir / f"{dataset_name}_metadata.json",
    ):
        if candidate.is_file():
            return [candidate]

    dataset_dir = l2_dir / dataset_name
    if dataset_dir.is_dir():
        return list(dataset_dir.glob("*.json"))

    return []


def _read_l2_capture_method_records(
    l2_dir: Path,
    dataset_names: list[str],
) -> list[dict[str, Any]]:
    """Read L2 records with capture_method for document source classification.

    Args:
        l2_dir: Root L2 metadata directory.
        dataset_names: Dataset names to scan.

    Returns:
        List of records with ``capture_method``, ``image_path``, ``provenance``.
    """
    records: list[dict[str, Any]] = []

    for dataset in dataset_names:
        paths = _resolve_l2_paths(l2_dir, dataset)
        if not paths:
            logger.warning("No L2 metadata found for %r", dataset)
            continue
        for jf in paths:
            records.extend(_parse_capture_method_file(jf, dataset))

    return records


def _parse_capture_method_file(
    json_path: Path,
    dataset_name: str,
) -> list[dict[str, Any]]:
    """Parse one L2 JSON for capture_method records.

    Supports flat lists, single-record dicts, and aggregated dataset format
    (``{"samples": [...], ...}``) with enrichments nested under
    ``enrichments.versions[-1].data``.

    Args:
        json_path: Path to L2 JSON.
        dataset_name: Dataset name for provenance annotation.

    Returns:
        List of records with ``source``, ``image_path``, ``provenance``.
    """
    try:
        with open(json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    results: list[dict[str, Any]] = []
    for sample in _expand_l2_samples(data):
        method = _get_field_from_l2_sample(sample, "capture_method")
        if method is None:
            continue

        source_class = L2_TO_SOURCE_CLASS.get(str(method))
        if source_class is None:
            continue  # Exclude synthetic and unknown

        image_path = _get_image_path_from_l2_sample(sample)
        results.append(
            {
                "image_path": image_path,
                "source": source_class,
                "provenance": "real_scan"
                if source_class == "scanned"
                else (
                    "real_camera" if source_class == "camera" else "real_born_digital"
                ),
                "source_dataset": dataset_name,
                "split_type": "train",
                "ood_categories": [],
            }
        )

    return results


# ---------------------------------------------------------------------------
# Manifest write helpers
# ---------------------------------------------------------------------------


def _write_task_manifest(
    records: list[dict[str, Any]],
    output_dir: Path,
    task_name: str,
    dry_run: bool,
) -> Path:
    """Write intermediate per-task manifest JSON to output_dir.

    Args:
        records: All task records (train + val + test combined).
        output_dir: Directory to write into.
        task_name: Task identifier used in filename.
        dry_run: Skip write if True.

    Returns:
        Path to the written manifest file (or would-be path in dry-run).
    """
    manifest_path = output_dir / f"{task_name}_manifest.json"
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(records, f, indent=2)
        logger.info("Wrote %d records → %s", len(records), manifest_path)
    else:
        logger.info(
            "[DRY-RUN] Would write %d %s records → %s",
            len(records),
            task_name,
            manifest_path,
        )
    return manifest_path


def _print_task_report(
    records: list[dict[str, Any]],
    task_name: str,
    label_field: str,
) -> None:
    """Print per-class counts and provenance breakdown for a task.

    Args:
        records: All samples for this task.
        task_name: Human-readable task label.
        label_field: Dict key for the class/value label.
    """
    click.echo(f"\n{'=' * 60}")
    click.echo(f"  {task_name.upper()} DATASET REPORT")
    click.echo(f"{'=' * 60}")
    click.echo(f"  Total samples: {len(records)}")

    # Provenance breakdown
    provenance: dict[str, int] = {}
    for r in records:
        p = r.get("provenance", "unknown")
        provenance[p] = provenance.get(p, 0) + 1
    click.echo("  Provenance:")
    for p, n in sorted(provenance.items()):
        click.echo(f"    {p}: {n} ({n / len(records) * 100:.1f}%)")

    # Split breakdown
    splits: dict[str, int] = {}
    for r in records:
        sp = r.get("split", "unset")
        splits[sp] = splits.get(sp, 0) + 1
    click.echo(f"  Splits: {splits}")

    # Label distribution (top 10)
    if label_field in ("script", "source", "orientation"):
        label_counts: dict[Any, int] = {}
        for r in records:
            lv = r.get(label_field)
            if lv is not None:
                label_counts[lv] = label_counts.get(lv, 0) + 1
        click.echo(f"  {label_field} distribution:")
        for lv, n in sorted(label_counts.items(), key=lambda x: -x[1])[:15]:
            click.echo(f"    {lv}: {n}")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.option("--verbose", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Prepare multi-task training datasets for the SigLIP 2 teacher model."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# ---------------------------------------------------------------------------
# Sub-command: script
# ---------------------------------------------------------------------------


_MDIW13_NAME_TO_ISO: dict[str, str] = {
    # English folder names used in the SIW_MultiscriptDatabase layout
    "Arabic": "Arab",
    "Roman": "Latn",
    "Hindi": "Deva",
    "Bangla": "Beng",
    "Japanese": "Jpan",
    "Thai": "Thai",
    "Tamil": "Taml",
    "Telugu": "Telu",
    "Kannada": "Knda",
    "Malayalam": "Mlym",
    "Gujrati": "Gujr",
    "Gurmukhi": "Guru",
    "Oriya": "Orya",
    # ISO 15924 codes are also accepted directly
}


def _load_mdiw13_records(
    mdiw13_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Walk MDIW13 directory and build per-ML-class record pools.

    Supports two MDIW13 directory layouts:

    * ISO 15924 folder names: ``{mdiw13_dir}/Arab/*.jpg``
    * English folder names (SIW_MultiscriptDatabase): ``{mdiw13_dir}/Arabic/*.jpg``

    Recursively collects images so that sub-split directories (``train/``,
    ``test/``) are also traversed.

    Args:
        mdiw13_dir: Root MDIW13 directory.

    Returns:
        Mapping from ML class name to list of image record dicts.
    """
    from image_preprocessing_detector.schema_utils.script_ml_mapping import (
        ScriptMLMapping,
    )

    mapper = ScriptMLMapping()
    pool: dict[str, list[dict[str, Any]]] = {}
    image_exts = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}

    for script_folder in mdiw13_dir.iterdir():
        if not script_folder.is_dir():
            continue
        # Translate English name → ISO 15924 code if needed
        folder_name = script_folder.name
        iso_name = _MDIW13_NAME_TO_ISO.get(folder_name, folder_name)
        ml_class = mapper.to_ml_class(iso_name)
        if ml_class not in VALID_SCRIPTS:
            logger.debug("Unmapped MDIW13 folder %r → %r", script_folder.name, ml_class)
            continue

        # Collect images recursively (handles train/test sub-split dirs)
        images = [
            p
            for p in script_folder.rglob("*")
            if p.is_file() and p.suffix.lower() in image_exts
        ]
        for img_path in images:
            doc_id = hashlib.sha256(
                str(img_path.relative_to(mdiw13_dir)).encode()
            ).hexdigest()[:24]
            pool.setdefault(ml_class, []).append(
                {
                    "image_path": str(img_path),  # absolute local path
                    "script": ml_class,
                    "provenance": "real_scan",
                    "source_dataset": "mdiw13",
                    "document_id": doc_id,
                    "split_type": "train",
                    "ood_categories": [],
                }
            )

    total = sum(len(v) for v in pool.values())
    logger.info("MDIW13: %d images across %d ML classes", total, len(pool))
    return pool


def _load_v3_script_records(
    v3_gcs_prefix: str,
    exclude_scripts: set[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build per-ML-class record pool from v3 splits.jsonl.

    Args:
        v3_gcs_prefix: GCS prefix for v3 dataset.
        exclude_scripts: ISO folder names to exclude (e.g. already well-covered).

    Returns:
        Mapping from ML class name to list of record dicts.
    """
    from image_preprocessing_detector.schema_utils.script_ml_mapping import (
        ScriptMLMapping,
    )

    mapper = ScriptMLMapping()
    bucket_name, prefix = _parse_gcs_path(v3_gcs_prefix)
    bucket = _get_gcs_bucket(bucket_name)

    splits_key = f"{prefix}/splits.jsonl"
    logger.info("Loading v3 script pool from gs://%s/%s …", bucket_name, splits_key)
    content = bucket.blob(splits_key).download_as_text()

    pool: dict[str, list[dict[str, Any]]] = {}
    skipped = 0

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue

        source_path = rec.get("source_path", "")
        split = rec.get("split", "train")
        parts = Path(source_path).parts

        try:
            v3_idx = next(
                i for i, p in enumerate(parts) if p == "synthetic_multiscript_v3"
            )
            iso_folder = parts[v3_idx + 1]
            uuid = Path(parts[v3_idx + 2]).stem
        except (StopIteration, IndexError):
            skipped += 1
            continue

        if exclude_scripts and iso_folder in exclude_scripts:
            continue

        ml_class = mapper.to_ml_class(iso_folder)
        if ml_class not in VALID_SCRIPTS:
            skipped += 1
            continue

        gcs_key = f"{prefix}/{iso_folder}/{uuid}.jpg"
        pool.setdefault(ml_class, []).append(
            {
                "gcs_image_key": gcs_key,
                "script": ml_class,
                "provenance": "synthetic_v3",
                "source_dataset": "synth_multiscript_v3",
                "document_id": uuid,
                "split": split,
                "split_type": "train",
                "ood_categories": [],
            }
        )

    total = sum(len(v) for v in pool.values())
    logger.info(
        "v3 script pool: %d images across %d ML classes (%d skipped)",
        total,
        len(pool),
        skipped,
    )
    return pool


def _merge_script_pools(
    real_pool: dict[str, list[dict[str, Any]]],
    synth_pool: dict[str, list[dict[str, Any]]],
    max_synth_frac: float,
    min_per_class: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Merge real + synthetic script pools, enforcing the synthetic cap.

    Args:
        real_pool: Per-ML-class real image records.
        synth_pool: Per-ML-class synthetic image records.
        max_synth_frac: Maximum synthetic fraction per class (0–1).
        min_per_class: Minimum samples per class (augmented from synthetic if needed).
        rng: Random instance for sampling.

    Returns:
        Combined flat list of records.
    """
    all_classes = set(real_pool.keys()) | set(synth_pool.keys())
    merged: list[dict[str, Any]] = []

    for cls in sorted(all_classes):
        real_records = real_pool.get(cls, [])
        synth_records = synth_pool.get(cls, [])

        n_real = len(real_records)

        # Compute synthetic quota: at most max_synth_frac of (real + synth)
        # Solve: synth / (real + synth) ≤ max_synth_frac
        # → synth ≤ max_synth_frac * real / (1 - max_synth_frac)
        if n_real > 0:
            max_synth = math.ceil(max_synth_frac * n_real / (1.0 - max_synth_frac))
        else:
            # No real data: allow up to min_per_class synthetic but flag it
            max_synth = min_per_class
            if synth_records:
                logger.warning(
                    "[script] Class %r has no real data — using synthetic only (%d samples)",
                    cls,
                    min(max_synth, len(synth_records)),
                )

        n_synth = min(max_synth, len(synth_records))
        chosen_synth = rng.sample(synth_records, n_synth) if n_synth > 0 else []

        # Top up to min_per_class if below minimum
        total_cls = n_real + n_synth
        if total_cls < min_per_class and synth_records:
            extra_needed = min_per_class - total_cls
            extra_pool = [r for r in synth_records if r not in chosen_synth]
            extra = rng.sample(extra_pool, min(extra_needed, len(extra_pool)))
            chosen_synth.extend(extra)
            n_synth = len(chosen_synth)

        merged.extend(real_records)
        merged.extend(chosen_synth)

        logger.debug(
            "[script] %s: %d real + %d synthetic = %d total",
            cls,
            n_real,
            len(chosen_synth),
            n_real + len(chosen_synth),
        )

    return merged


@cli.command()
@click.option(
    "--mdiw13-dir",
    type=Path,
    default=None,
    help="Local MDIW13 root directory (ISO script sub-folders).",
)
@click.option(
    "--v3-gcs-prefix",
    type=str,
    default="gs://image_detection_b/synth_multiscript_v3",
    help="GCS prefix for v3 synthetic dataset.",
)
@click.option(
    "--output-dir",
    type=Path,
    required=True,
    help="Output directory for script_manifest.json.",
)
@click.option(
    "--min-per-class",
    type=int,
    default=5_800,
    help="Minimum samples per class (padded with synthetic). Default: 5800.",
)
@click.option("--seed", type=int, default=42, help="Random seed.")
@click.option("--dry-run", is_flag=True, help="Report counts without writing output.")
@click.pass_context
def script(
    ctx: click.Context,
    mdiw13_dir: Path | None,
    v3_gcs_prefix: str,
    output_dir: Path,
    min_per_class: int,
    seed: int,
    dry_run: bool,
) -> None:
    """Prepare script detection dataset (≥40% real MDIW13, ≤60% v3 synthetic)."""
    rng = random.Random(seed)
    start = time.time()

    # Load real data (MDIW13)
    real_pool: dict[str, list[dict[str, Any]]] = {}
    if mdiw13_dir and mdiw13_dir.is_dir():
        real_pool = _load_mdiw13_records(mdiw13_dir)
    else:
        logger.warning(
            "MDIW13 dir not provided or not found — using synthetic only for all classes."
        )

    # Load synthetic data (v3) — skip GCS in dry-run mode (no credentials needed)
    synth_pool: dict[str, list[dict[str, Any]]] = {}
    if not dry_run:
        synth_pool = _load_v3_script_records(
            v3_gcs_prefix, exclude_scripts=set(OOD_RESERVED_SCRIPTS)
        )
    else:
        logger.info(
            "[dry-run] Skipping v3 GCS download — real pool only for count check."
        )

    # Merge with mixing cap
    records = _merge_script_pools(
        real_pool=real_pool,
        synth_pool=synth_pool,
        max_synth_frac=SYNTHETIC_CAPS["script"],
        min_per_class=min_per_class,
        rng=rng,
    )

    # Assign splits using document_id (respects v3 registry for v3 images)
    for rec in records:
        if "split" not in rec:
            rec["split"] = _deterministic_split(
                rec.get("document_id", rec["image_path"])
            )

    _check_mixing_ratio(records, SYNTHETIC_CAPS["script"], "script")

    # Compute class weights from training split
    train_records = [r for r in records if r.get("split") == "train"]
    class_weights = _compute_class_weights(train_records, "script", SCRIPT_ML_CLASSES)
    weight_map = dict(zip(SCRIPT_ML_CLASSES, class_weights))

    _print_task_report(records, "script", "script")
    click.echo("\n  Class weights (top 5 by weight):")
    for cls, w in sorted(weight_map.items(), key=lambda x: -x[1])[:5]:
        click.echo(f"    {cls}: {w:.3f}")

    # Write manifest (includes class_weights as metadata entry)
    manifest_data: dict[str, Any] = {
        "samples": records,
        "class_weights": class_weights,
        "class_names": list(SCRIPT_ML_CLASSES),
    }
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "script_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)
        logger.info("Wrote %d script records → %s", len(records), manifest_path)
    else:
        logger.info(
            "[DRY-RUN] Would write %d script records → %s/script_manifest.json",
            len(records),
            output_dir,
        )

    if not dry_run:
        ood_registry_path = Path("metadata_registry/ood_registry.jsonl")
        _check_ood_leakage(records, ood_registry_path)

    elapsed = time.time() - start
    click.echo(f"\n  Elapsed: {elapsed:.1f}s")


# ---------------------------------------------------------------------------
# Sub-command: orientation
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--real-metadata",
    type=Path,
    required=True,
    help="Path to orientation_real_metadata.json from build_orientation_real_component.py.",
)
@click.option(
    "--synthetic-metadata",
    type=Path,
    default=None,
    help="Path to orientation_synthetic_metadata.json from derive_v3_orientation_view.py.",
)
@click.option(
    "--output-dir",
    type=Path,
    required=True,
    help="Output directory for orientation_manifest.json.",
)
@click.option("--seed", type=int, default=42, help="Random seed.")
@click.option("--dry-run", is_flag=True, help="Report counts without writing output.")
@click.pass_context
def orientation(
    ctx: click.Context,
    real_metadata: Path,
    synthetic_metadata: Path | None,
    output_dir: Path,
    seed: int,
    dry_run: bool,
) -> None:
    """Prepare orientation dataset (≥60% real rotated docs, ≤40% v3 synthetic)."""
    rng = random.Random(seed)

    records: list[dict[str, Any]] = []

    # Load real component
    if not real_metadata.exists():
        click.echo(f"ERROR: Real metadata file not found: {real_metadata}", err=True)
        raise SystemExit(1)

    with open(real_metadata) as f:
        real_records = json.load(f)

    for rec in real_records:
        deg = rec.get("orientation")
        if deg not in VALID_ORIENTATIONS:
            continue
        rec["split"] = _deterministic_split(
            rec.get("document_id", rec.get("image_path", ""))
        )
        records.append(rec)

    logger.info("Loaded %d real orientation records", len(records))

    # Load synthetic component (optional)
    if synthetic_metadata and synthetic_metadata.exists():
        with open(synthetic_metadata) as f:
            synth_records = json.load(f)

        for rec in synth_records:
            deg = rec.get("orientation")
            if deg not in VALID_ORIENTATIONS:
                continue
            if "split" not in rec:
                rec["split"] = _deterministic_split(
                    rec.get("document_id", rec.get("image_path", ""))
                )
            records.append(rec)

        logger.info("Loaded %d synthetic orientation records", len(synth_records))

    _check_mixing_ratio(records, SYNTHETIC_CAPS["orientation"], "orientation")
    _print_task_report(records, "orientation", "orientation")

    _write_task_manifest(records, output_dir, "orientation", dry_run)
    click.echo(f"\n  Total orientation samples: {len(records)}")

    if not dry_run:
        ood_registry_path = Path("metadata_registry/ood_registry.jsonl")
        _check_ood_leakage(records, ood_registry_path)


# ---------------------------------------------------------------------------
# Sub-command: source
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--l2-metadata-dir",
    type=Path,
    default=Path("/mnt/e/image_detection/metadata_registry/json"),
    help="Root L2 metadata registry directory.",
)
@click.option(
    "--l2-datasets",
    type=str,
    multiple=True,
    default=("doclaynet", "rvlcdip", "smartdoc-qa", "realdae", "midv500"),
    help="Datasets to query for capture_method.",
)
@click.option(
    "--max-scanned", type=int, default=10_000, help="Cap on scanned class samples."
)
@click.option(
    "--max-born-digital",
    type=int,
    default=10_000,
    help="Cap on born_digital class samples.",
)
@click.option(
    "--output-dir",
    type=Path,
    required=True,
    help="Output directory for source_manifest.json.",
)
@click.option("--seed", type=int, default=42)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def source(
    ctx: click.Context,
    l2_metadata_dir: Path,
    l2_datasets: tuple[str, ...],
    max_scanned: int,
    max_born_digital: int,
    output_dir: Path,
    seed: int,
    dry_run: bool,
) -> None:
    """Prepare document source dataset (≥95% real: scanned/camera/born_digital)."""
    rng = random.Random(seed)

    if not l2_metadata_dir.exists():
        logger.warning(
            "L2 metadata dir not found: %s — source sub-command may produce empty results.",
            l2_metadata_dir,
        )

    all_records = _read_l2_capture_method_records(l2_metadata_dir, list(l2_datasets))

    # Validate born_digital spelling (hard assertion)
    for rec in all_records:
        src = rec.get("source", "")
        assert src != "born-digital", (
            "born_digital must use underscore, not hyphen — check L2 schema"
        )

    # Separate by class (4-class: born_digital / scanned / camera / synthetic)
    scanned = [r for r in all_records if r["source"] == "scanned"]
    camera = [r for r in all_records if r["source"] == "camera"]
    born_digital = [r for r in all_records if r["source"] == "born_digital"]
    synthetic = [r for r in all_records if r["source"] == "synthetic"]

    click.echo(
        f"  Source class counts: scanned={len(scanned)}, camera={len(camera)}, "
        f"born_digital={len(born_digital)}, synthetic={len(synthetic)}"
    )

    if len(camera) < 12_000:
        logger.warning(
            "Camera class has only %d samples (target ≥12K). "
            "Consider augmentation via Augraphy camera simulation.",
            len(camera),
        )
    if len(synthetic) == 0:
        logger.info(
            "Synthetic class is empty — add synth-multiscript-v3 or DocSynth300K "
            "to --l2-datasets to include synthetic capture-method samples."
        )

    # Apply per-class caps
    scanned_sample = rng.sample(scanned, min(max_scanned, len(scanned)))
    born_d_sample = rng.sample(born_digital, min(max_born_digital, len(born_digital)))

    records: list[dict[str, Any]] = [
        *scanned_sample,
        *camera,
        *born_d_sample,
        *synthetic,
    ]
    for rec in records:
        rec["split"] = _deterministic_split(rec.get("image_path", ""))

    _check_mixing_ratio(records, SYNTHETIC_CAPS["source"], "source")
    _print_task_report(records, "source", "source")
    _write_task_manifest(records, output_dir, "source", dry_run)
    click.echo(f"\n  Total source samples: {len(records)}")

    if not dry_run:
        ood_registry_path = Path("metadata_registry/ood_registry.jsonl")
        _check_ood_leakage(records, ood_registry_path)


# ---------------------------------------------------------------------------
# Sub-command: shadow
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--synthetic-metadata",
    type=Path,
    required=True,
    help="shadow_metadata.json from generate_v3_shadow_view.py.",
)
@click.option(
    "--l2-metadata-dir",
    type=Path,
    default=Path("/mnt/e/image_detection/metadata_registry/json"),
    help="Root L2 metadata registry directory.",
)
@click.option(
    "--l2-datasets",
    type=str,
    multiple=True,
    default=("sd7k", "wsrd"),
    help="Real shadow datasets to query for shadow_severity.",
)
@click.option(
    "--output-dir",
    type=Path,
    required=True,
    help="Output directory for shadow_manifest.json.",
)
@click.option("--seed", type=int, default=42)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def shadow(
    ctx: click.Context,
    synthetic_metadata: Path,
    l2_metadata_dir: Path,
    l2_datasets: tuple[str, ...],
    output_dir: Path,
    seed: int,
    dry_run: bool,
) -> None:
    """Prepare shadow severity dataset (≥50% real sd7k/wsrd, ≤50% v3 synthetic)."""
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []

    # Synthetic component (from Phase 1.1)
    if not synthetic_metadata.exists():
        logger.warning("Synthetic shadow metadata not found: %s", synthetic_metadata)
    else:
        with open(synthetic_metadata) as f:
            synth_records = json.load(f)
        for rec in synth_records:
            # Map 'severity' → 'shadow' for training contract
            if "severity" in rec and "shadow" not in rec:
                rec["shadow"] = rec["severity"]
            if "split" not in rec:
                rec["split"] = _deterministic_split(rec.get("image_path", ""))
            records.append(rec)
        logger.info("Loaded %d synthetic shadow records", len(synth_records))

    # Real component (from L2 metadata)
    if l2_metadata_dir.exists():
        real_records = _read_l2_records(
            l2_metadata_dir, list(l2_datasets), "shadow_severity"
        )
        for rec in real_records:
            # Map 'shadow_severity' → 'shadow' for training contract
            if "shadow_severity" in rec and "shadow" not in rec:
                rec["shadow"] = rec["shadow_severity"]
            if "split" not in rec:
                rec["split"] = _deterministic_split(rec.get("image_path", ""))
            records.append(rec)
        logger.info("Loaded %d real shadow records from L2", len(real_records))
    else:
        logger.warning(
            "L2 metadata dir not found: %s — no real shadow data loaded.",
            l2_metadata_dir,
        )

    if not records:
        click.echo(
            "ERROR: No shadow records found. Run Phase 1.1 first and ensure L2 metadata exists.",
            err=True,
        )
        raise SystemExit(1)

    _check_mixing_ratio(records, SYNTHETIC_CAPS["shadow"], "shadow")
    _print_task_report(records, "shadow", "shadow")
    _write_task_manifest(records, output_dir, "shadow", dry_run)
    click.echo(f"\n  Total shadow samples: {len(records)}")

    if not dry_run:
        ood_registry_path = Path("metadata_registry/ood_registry.jsonl")
        _check_ood_leakage(records, ood_registry_path)


# ---------------------------------------------------------------------------
# Sub-command: warping
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--synthetic-metadata",
    type=Path,
    required=True,
    help="warping_metadata.json from generate_v3_warping_view.py.",
)
@click.option(
    "--l2-metadata-dir",
    type=Path,
    default=Path("/mnt/e/image_detection/metadata_registry/json"),
    help="Root L2 metadata registry directory.",
)
@click.option(
    "--l2-datasets",
    type=str,
    multiple=True,
    default=("warpdoc", "anyphotodoc6300", "docalign12k", "docreal"),
    help="Real warping datasets to query for warping_severity.",
)
@click.option(
    "--output-dir",
    type=Path,
    required=True,
    help="Output directory for warping_manifest.json.",
)
@click.option("--seed", type=int, default=42)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def warping(
    ctx: click.Context,
    synthetic_metadata: Path,
    l2_metadata_dir: Path,
    l2_datasets: tuple[str, ...],
    output_dir: Path,
    seed: int,
    dry_run: bool,
) -> None:
    """Prepare warping severity dataset (≥70% real pairs, ≤30% v3 synthetic)."""
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []

    # Synthetic component (from Phase 1.2)
    if not synthetic_metadata.exists():
        logger.warning("Synthetic warping metadata not found: %s", synthetic_metadata)
    else:
        with open(synthetic_metadata) as f:
            synth_records = json.load(f)
        for rec in synth_records:
            if "severity" in rec and "warping" not in rec:
                rec["warping"] = rec["severity"]
            if "split" not in rec:
                rec["split"] = _deterministic_split(rec.get("image_path", ""))
            records.append(rec)
        logger.info("Loaded %d synthetic warping records", len(synth_records))

    # Real component (from L2 metadata)
    if l2_metadata_dir.exists():
        real_records = _read_l2_records(
            l2_metadata_dir, list(l2_datasets), "warping_severity"
        )
        for rec in real_records:
            if "warping_severity" in rec and "warping" not in rec:
                rec["warping"] = rec["warping_severity"]
            if "split" not in rec:
                rec["split"] = _deterministic_split(rec.get("image_path", ""))
            records.append(rec)
        logger.info("Loaded %d real warping records from L2", len(real_records))
    else:
        logger.warning(
            "L2 metadata dir not found: %s — no real warping data loaded.",
            l2_metadata_dir,
        )

    if not records:
        click.echo(
            "ERROR: No warping records found. Run Phase 1.2 first and ensure L2 metadata exists.",
            err=True,
        )
        raise SystemExit(1)

    _check_mixing_ratio(records, SYNTHETIC_CAPS["warping"], "warping")
    _print_task_report(records, "warping", "warping")
    _write_task_manifest(records, output_dir, "warping", dry_run)
    click.echo(f"\n  Total warping samples: {len(records)}")

    if not dry_run:
        ood_registry_path = Path("metadata_registry/ood_registry.jsonl")
        _check_ood_leakage(records, ood_registry_path)


# ---------------------------------------------------------------------------
# Sub-command: merge
# ---------------------------------------------------------------------------


def _load_task_manifest(task_dir: Path, task_name: str) -> list[dict[str, Any]]:
    """Load a task-specific manifest JSON.

    For the script manifest (which wraps samples in a dict), unwraps
    the ``samples`` key automatically.

    Args:
        task_dir: Directory containing ``{task_name}_manifest.json``.
        task_name: Task identifier.

    Returns:
        Flat list of record dicts, or empty list if file not found.
    """
    manifest_path = task_dir / f"{task_name}_manifest.json"
    if not manifest_path.exists():
        logger.warning("Task manifest not found: %s", manifest_path)
        return []
    with open(manifest_path) as f:
        data = json.load(f)
    # Script manifest has {"samples": [...], "class_weights": [...]}
    if isinstance(data, dict) and "samples" in data:
        return data["samples"]
    return data


def _remap_image_paths(
    records: list[dict[str, Any]],
    task_prefix: str,
) -> list[dict[str, Any]]:
    """Prepend ``task_prefix/`` to all image_path fields.

    Ensures images from different tasks live in separate subdirectories
    under the Modal Volume /data root.

    Args:
        records: Task records with relative ``image_path``.
        task_prefix: Sub-directory prefix (e.g. ``"shadow"``).

    Returns:
        New list with updated ``image_path`` fields.
    """
    result = []
    for rec in records:
        new_rec = dict(rec)
        img_path = new_rec.get("image_path", "")
        if not img_path.startswith(f"{task_prefix}/"):
            new_rec["image_path"] = f"{task_prefix}/{img_path}"
        result.append(new_rec)
    return result


@cli.command()
@click.option("--script-dir", type=Path, default=None)
@click.option("--orientation-dir", type=Path, default=None)
@click.option("--source-dir", type=Path, default=None)
@click.option("--shadow-dir", type=Path, default=None)
@click.option("--warping-dir", type=Path, default=None)
@click.option(
    "--gcs-output-prefix",
    type=str,
    required=True,
    help="GCS prefix for upload (e.g. gs://image_detection_b/datasets/multitask_training).",
)
@click.option(
    "--output-dir",
    type=Path,
    default=Path("/tmp/multitask_merged"),
    help="Local dir to write merged manifests before GCS upload.",
)
@click.option("--seed", type=int, default=42)
@click.option("--dry-run", is_flag=True)
@click.option(
    "--skip-image-upload",
    is_flag=True,
    help="Skip image upload; only upload manifests.",
)
@click.pass_context
def merge(
    ctx: click.Context,
    script_dir: Path | None,
    orientation_dir: Path | None,
    source_dir: Path | None,
    shadow_dir: Path | None,
    warping_dir: Path | None,
    gcs_output_prefix: str,
    output_dir: Path,
    seed: int,
    dry_run: bool,
    skip_image_upload: bool,
) -> None:
    """Merge all task manifests into unified train/val manifests and upload to GCS.

    Images from each task are prefixed with the task name under /data:
    - script images  → /data/script/images/
    - shadow images  → /data/shadow/images/
    - etc.

    The merged manifests (train_manifest.json, val_manifest.json) are uploaded
    to the specified GCS prefix alongside the task image directories.
    """
    rng = random.Random(seed)

    task_dirs: dict[str, Path | None] = {
        "script": script_dir,
        "orientation": orientation_dir,
        "source": source_dir,
        "shadow": shadow_dir,
        "warping": warping_dir,
    }

    all_records: list[dict[str, Any]] = []

    for task_name, task_dir in task_dirs.items():
        if task_dir is None:
            logger.info("Skipping task %r (no directory provided)", task_name)
            continue
        task_records = _load_task_manifest(task_dir, task_name)
        remapped = _remap_image_paths(task_records, task_name)
        all_records.extend(remapped)
        logger.info("Loaded %d %s records", len(task_records), task_name)

    if not all_records:
        click.echo("ERROR: No records found across all tasks.", err=True)
        raise SystemExit(1)

    # Assign splits for any records without one
    for rec in all_records:
        if "split" not in rec:
            rec["split"] = _deterministic_split(
                rec.get("document_id", rec.get("image_path", ""))
            )

    train_records = [r for r in all_records if r.get("split") == "train"]
    val_records = [r for r in all_records if r.get("split") == "val"]

    rng.shuffle(train_records)
    rng.shuffle(val_records)

    click.echo(f"\n{'=' * 60}")
    click.echo("  MERGE SUMMARY")
    click.echo(f"{'=' * 60}")
    click.echo(f"  Total: {len(all_records)}")
    click.echo(f"  Train: {len(train_records)}")
    click.echo(f"  Val:   {len(val_records)}")

    # Task distribution in training set
    task_counts: dict[str, int] = {}
    for rec in train_records:
        for task_key in ("script", "orientation", "source", "shadow", "warping"):
            if task_key in rec:
                task_counts[task_key] = task_counts.get(task_key, 0) + 1
    click.echo(f"  Per-task train counts: {task_counts}")

    # Write local manifests
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train_manifest.json"
    val_path = output_dir / "val_manifest.json"

    if not dry_run:
        with open(train_path, "w") as f:
            json.dump(train_records, f, indent=2)
        with open(val_path, "w") as f:
            json.dump(val_records, f, indent=2)
        logger.info("Wrote local manifests: %s, %s", train_path, val_path)

    # Upload to GCS
    bucket_name, gcs_prefix = _parse_gcs_path(gcs_output_prefix)
    bucket = _get_gcs_bucket(bucket_name)

    _upload_manifest(
        train_records,
        bucket,
        f"{gcs_prefix}/train_manifest.json",
        dry_run=dry_run,
    )
    _upload_manifest(
        val_records,
        bucket,
        f"{gcs_prefix}/val_manifest.json",
        dry_run=dry_run,
    )

    click.echo("\nMerge complete. Next steps:")
    click.echo("  1. Upload task images to GCS (use --skip-image-upload to skip).")
    click.echo(
        "  2. Copy GCS data to Modal Volume: modal volume put multitask-datasets ..."
    )
    click.echo("  3. Run: uv run modal run modal/train_siglip2_multitask.py --test")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
