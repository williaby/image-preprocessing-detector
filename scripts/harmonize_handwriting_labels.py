"""Assemble a handwriting-presence training manifest from heterogeneous source datasets.

Reads L2 metadata files and native annotations (where available) to produce a
JSONL manifest suitable for training the SigLIP 2 handwriting detection heads.

Label schema
------------
Each output record has::

    {
        "image_path": str,           # relative to --base-data-root
        "source_dataset": str,       # canonical dataset name
        "handwriting_presence": bool, # True = page contains handwriting
        "handwriting_score": float,   # 0.0–1.0 confidence / ratio
        "split": str,                 # "train", "val", or "test"
        "label_method": str,          # how the label was derived
    }

Labeling strategies per dataset
---------------------------------
``all_handwritten``   (IAM, Muharaf, PUCIT-OHUL, Nepali):
    All images in the dataset contain handwriting.
    ``handwriting_presence=True``, ``handwriting_score=1.0``.
    Label method: ``"dataset_class"``.

``model_derived``     (HierText, COCO-Text, FUNSD, NIST-SD2/SD6):
    Use the ``has_handwriting`` flag from the L2 DocLayout-YOLO inference stored
    in ``enrichments.versions[-1].data.has_handwriting``.
    Score set to 0.8 (True) or 0.0 (False) reflecting model uncertainty.
    Label method: ``"l2_model_doclayout"``.

``all_printed``       (DocLayNet, PubTabNet negatives):
    All images are born-digital with no handwriting.
    ``handwriting_presence=False``, ``handwriting_score=0.0``.
    Label method: ``"dataset_class"``.

Target distribution
-------------------
≥40K presence=True and ≥15K presence=False (negative class).
CJK handwriting is intentionally skipped for v1 — synth-multiscript-v3 CJK
printed pages serve as strong negative examples.

Usage
-----
::

    # Dry-run: count records without writing
    uv run python scripts/harmonize_handwriting_labels.py \\
        --l2-dir /mnt/e/image_detection/metadata_registry/json/ \\
        --base-data-root /mnt/e/image_detection/01_base_data/ \\
        --dry-run

    # Full run
    uv run python scripts/harmonize_handwriting_labels.py \\
        --l2-dir /mnt/e/image_detection/metadata_registry/json/ \\
        --base-data-root /mnt/e/image_detection/01_base_data/ \\
        --output handwriting_manifest.jsonl

    # Include negative class from DocLayNet subset (sampled)
    uv run python scripts/harmonize_handwriting_labels.py \\
        --l2-dir /mnt/e/image_detection/metadata_registry/json/ \\
        --base-data-root /mnt/e/image_detection/01_base_data/ \\
        --negatives-from doclaynet --negatives-count 15000 \\
        --output handwriting_manifest.jsonl
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from tqdm import tqdm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataset configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasetConfig:
    """Configuration for a single handwriting source dataset.

    Attributes:
        name: Canonical dataset name (matches L2 metadata filename prefix).
        strategy: Label derivation strategy.
            ``"all_handwritten"`` — all images contain handwriting.
            ``"model_derived"`` — use L2 ``has_handwriting`` field.
            ``"all_printed"`` — no images contain handwriting.
        base_subdir: Path relative to ``--base-data-root`` where images live.
        max_samples: Optional cap on how many records to include (random sample).
    """

    name: str
    strategy: str
    base_subdir: str
    max_samples: int | None = None


# Positive-class datasets (handwriting present)
_POSITIVE_DATASETS: list[DatasetConfig] = [
    DatasetConfig(
        name="iam",
        strategy="all_handwritten",
        base_subdir="handwriting/iam_handwriting",
        max_samples=None,
    ),
    DatasetConfig(
        name="muharaf",
        strategy="all_handwritten",
        base_subdir="handwriting/muharaf",
        max_samples=5000,  # cap: 25K total, take representative subset
    ),
    # Mixed-class datasets (model-derived labels)
    DatasetConfig(
        name="hiertext",
        strategy="model_derived",
        base_subdir="text_detection/hiertext",
        max_samples=None,
    ),
    DatasetConfig(
        name="cocotext",
        strategy="model_derived",
        base_subdir="text_detection/cocotext",
        max_samples=20000,  # cap: 123K total, sample for balance
    ),
    DatasetConfig(
        name="funsd",
        strategy="model_derived",
        base_subdir="forms/funsd",
        max_samples=None,
    ),
    # NIST SD-2/SD-6 are fully handwritten (tax forms, handprint).  The L2
    # has_handwriting field may be unpopulated, so use all_handwritten strategy.
    DatasetConfig(
        name="nist-sd2",
        strategy="all_handwritten",
        base_subdir="forms/nist-sd2",
        max_samples=None,
    ),
    DatasetConfig(
        name="nist-sd6",
        strategy="all_handwritten",
        base_subdir="forms/nist_sd6",
        max_samples=None,
    ),
]

# Negative-class datasets (no handwriting)
_NEGATIVE_DATASETS: list[DatasetConfig] = [
    DatasetConfig(
        name="doclaynet",
        strategy="all_printed",
        base_subdir="layout/doclaynet",
        max_samples=None,  # set by --negatives-count at runtime
    ),
    DatasetConfig(
        name="pubtabnet",
        strategy="all_printed",
        base_subdir="tables/pubtabnet",
        max_samples=None,
    ),
]

# All dataset name → config lookup
_ALL_CONFIGS: dict[str, DatasetConfig] = {
    cfg.name: cfg for cfg in _POSITIVE_DATASETS + _NEGATIVE_DATASETS
}


# ---------------------------------------------------------------------------
# L2 metadata helpers
# ---------------------------------------------------------------------------


def _load_l2_metadata(l2_dir: Path, dataset_name: str) -> list[dict[str, Any]]:
    """Load L2 metadata samples for a dataset.

    Args:
        l2_dir: Directory containing ``{name}_metadata.json`` files.
        dataset_name: Canonical dataset name (without ``_metadata.json`` suffix).

    Returns:
        List of sample dicts.  Empty list if the file does not exist.
    """
    meta_path = l2_dir / f"{dataset_name}_metadata.json"
    if not meta_path.exists():
        logger.warning("L2 metadata not found: %s", meta_path)
        return []
    with open(meta_path) as fh:
        data = json.load(fh)
    return data.get("samples", [])


_SPLIT_NORMALIZER: dict[str, str] = {
    "train": "train",
    "training": "train",
    "val": "val",
    "valid": "val",
    "validation": "val",
    "test": "test",
    "testing": "test",
    "unknown": "train",  # treat unknown as train rather than exclude
}


def _normalize_split(raw: str) -> str:
    """Normalize dataset-specific split names to ``train``/``val``/``test``.

    Args:
        raw: Raw split string from L2 metadata.

    Returns:
        Normalized split name.  Defaults to ``"train"`` for unrecognised values.
    """
    return _SPLIT_NORMALIZER.get(raw.lower(), "train")


def _get_latest_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Extract the latest enrichment data dict from a sample.

    Args:
        sample: L2 metadata sample dict.

    Returns:
        Data dict from the latest enrichment version.  Empty dict if none.
    """
    versions = sample.get("enrichments", {}).get("versions", [])
    if not versions:
        return {}
    return versions[-1].get("data", {})


# ---------------------------------------------------------------------------
# Record builders per strategy
# ---------------------------------------------------------------------------


def _build_all_handwritten_records(
    samples: list[dict[str, Any]],
    config: DatasetConfig,
    base_data_root: Path,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Build records for datasets where ALL images contain handwriting.

    Args:
        samples: L2 metadata samples.
        config: Dataset configuration.
        base_data_root: Root path for resolving image paths.
        rng: Random state for reproducible sampling.

    Returns:
        List of output record dicts.  Empty if dataset not on disk.
    """
    base_dir = base_data_root / config.base_subdir
    if not base_dir.exists():
        logger.warning("Dataset directory not found (GCS-only?): %s", base_dir)
        return []

    # Apply cap before the per-file disk scan to avoid slow O(N) stat calls
    if config.max_samples and len(samples) > config.max_samples * 4:
        samples = rng.sample(samples, config.max_samples * 4)

    records: list[dict[str, Any]] = []
    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        raw_split = sample.get("source", {}).get("split", "train")
        if not original_path:
            continue
        img_path = base_dir / original_path
        if not img_path.exists():
            continue
        records.append(
            {
                "image_path": str(Path(config.base_subdir) / original_path),
                "source_dataset": config.name,
                "handwriting_presence": True,
                "handwriting_score": 1.0,
                "split": _normalize_split(raw_split),
                "label_method": "dataset_class",
            }
        )

    if config.max_samples and len(records) > config.max_samples:
        records = rng.sample(records, config.max_samples)
    return records


def _build_model_derived_records(
    samples: list[dict[str, Any]],
    config: DatasetConfig,
    base_data_root: Path,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Build records using L2 DocLayout-YOLO ``has_handwriting`` labels.

    Args:
        samples: L2 metadata samples.
        config: Dataset configuration.
        base_data_root: Root path for resolving image paths.
        rng: Random state for reproducible sampling.

    Returns:
        List of output record dicts.
    """
    base_dir = base_data_root / config.base_subdir
    if not base_dir.exists():
        logger.warning("Dataset directory not found (GCS-only?): %s", base_dir)
        return []

    # L2 metadata was built from actual files — trust it.  Per-file stat calls
    # are too slow on large datasets (e.g. 123K COCO-Text at ~3ms/call over WSL).
    # Pre-sample to 4× the cap before iterating to keep iteration O(cap) not O(N).
    if config.max_samples and len(samples) > config.max_samples * 4:
        samples = rng.sample(samples, config.max_samples * 4)

    records: list[dict[str, Any]] = []
    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        raw_split = sample.get("source", {}).get("split", "train")
        if not original_path:
            continue

        data = _get_latest_data(sample)
        has_hw = bool(data.get("has_handwriting", False))
        # Model confidence: 0.8 for positive detections (avoid overconfidence on
        # DocLayout-YOLO which has moderate precision for handwriting class)
        score = 0.8 if has_hw else 0.0
        records.append(
            {
                "image_path": str(Path(config.base_subdir) / original_path),
                "source_dataset": config.name,
                "handwriting_presence": has_hw,
                "handwriting_score": score,
                "split": _normalize_split(raw_split),
                "label_method": "l2_model_doclayout",
            }
        )

    if config.max_samples and len(records) > config.max_samples:
        records = rng.sample(records, config.max_samples)
    return records


def _build_all_printed_records(
    samples: list[dict[str, Any]],
    config: DatasetConfig,
    base_data_root: Path,
    rng: random.Random,
    target_count: int | None,
) -> list[dict[str, Any]]:
    """Build negative-class records for fully-printed datasets.

    Args:
        samples: L2 metadata samples.
        config: Dataset configuration.
        base_data_root: Root path for resolving image paths.
        rng: Random state for reproducible sampling.
        target_count: If set, sample down to this many records.

    Returns:
        List of output record dicts.
    """
    base_dir = base_data_root / config.base_subdir
    if not base_dir.exists():
        logger.warning("Dataset directory not found (GCS-only?): %s", base_dir)
        return []

    # L2 metadata was built from actual files — trust it.  Pre-sample to 4× cap
    # before iterating to keep iteration O(cap) not O(N).
    effective_cap = target_count or config.max_samples
    if effective_cap and len(samples) > effective_cap * 4:
        samples = rng.sample(samples, effective_cap * 4)

    records: list[dict[str, Any]] = []
    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        raw_split = sample.get("source", {}).get("split", "train")
        if not original_path:
            continue
        records.append(
            {
                "image_path": str(Path(config.base_subdir) / original_path),
                "source_dataset": config.name,
                "handwriting_presence": False,
                "handwriting_score": 0.0,
                "split": _normalize_split(raw_split),
                "label_method": "dataset_class",
            }
        )

    effective_cap = target_count or config.max_samples
    if effective_cap and len(records) > effective_cap:
        records = rng.sample(records, effective_cap)
    return records


# ---------------------------------------------------------------------------
# Manifest assembly
# ---------------------------------------------------------------------------


def _build_iam_records_from_filesystem(
    base_data_root: Path,
    split_fractions: tuple[float, float, float],
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Build IAM records directly from filesystem (no L2 metadata required).

    IAM is stored as ``{writer_id}/{form_id}.png`` under
    ``handwriting/iam_handwriting/``.  All PNGs are positive-class (form-level
    handwritten pages).

    Args:
        base_data_root: Root path for resolving image paths.
        split_fractions: (train, val, test) fractions summing to 1.0.
        rng: Random state for reproducible splits.

    Returns:
        List of output record dicts with writer-aware splits.
    """
    iam_dir = base_data_root / "handwriting/iam_handwriting"
    if not iam_dir.exists():
        logger.warning("IAM directory not found: %s", iam_dir)
        return []

    # Collect form PNG paths at the top level and one level deep (writer dirs)
    form_paths: list[Path] = []
    for item in iam_dir.iterdir():
        if item.is_dir() and len(item.name) <= 3:
            # Writer directory (e.g., a01, b02) — collect form PNGs inside
            for form_png in item.glob("*.png"):
                form_paths.append(form_png)
        elif item.suffix.lower() == ".png" and item.is_file():
            form_paths.append(item)

    if not form_paths:
        logger.warning("No IAM form PNGs found in %s", iam_dir)
        return []

    rng.shuffle(form_paths)
    n = len(form_paths)
    train_end = int(n * split_fractions[0])
    val_end = train_end + int(n * split_fractions[1])

    records: list[dict[str, Any]] = []
    for idx, form_path in enumerate(form_paths):
        if idx < train_end:
            split = "train"
        elif idx < val_end:
            split = "val"
        else:
            split = "test"
        rel_path = form_path.relative_to(base_data_root)
        records.append(
            {
                "image_path": str(rel_path),
                "source_dataset": "iam",
                "handwriting_presence": True,
                "handwriting_score": 1.0,
                "split": split,
                "label_method": "dataset_class",
            }
        )
    return records


def _print_summary(records: list[dict[str, Any]], verbose: bool) -> None:
    """Print manifest statistics.

    Args:
        records: All assembled records.
        verbose: Whether to print per-dataset breakdown.
    """
    total = len(records)
    positive = sum(1 for r in records if r["handwriting_presence"])
    negative = total - positive
    splits: dict[str, int] = {}
    per_dataset: dict[str, int] = {}
    for r in records:
        splits[r["split"]] = splits.get(r["split"], 0) + 1
        per_dataset[r["source_dataset"]] = per_dataset.get(r["source_dataset"], 0) + 1

    click.echo(f"\nManifest summary:")
    click.echo(f"  Total records  : {total:>8,}")
    click.echo(
        f"  Positive (True): {positive:>8,}  ({100 * positive / max(total, 1):.1f}%)"
    )
    click.echo(
        f"  Negative (False): {negative:>7,}  ({100 * negative / max(total, 1):.1f}%)"
    )
    click.echo(f"  Splits: " + ", ".join(f"{k}={v}" for k, v in sorted(splits.items())))
    if verbose:
        click.echo("\n  Per-dataset counts:")
        for ds, cnt in sorted(per_dataset.items(), key=lambda x: -x[1]):
            click.echo(f"    {ds:<20} {cnt:>7,}")

    # Go/No-Go checks
    if positive < 40_000:
        click.echo(
            f"\n  WARNING: positive class {positive:,} < 40,000 target.\n"
            "  Missing positive sources (likely GCS-only, not mirrored to local disk):\n"
            "    muharaf (~5K pages), pucit-ohul (~7K lines), nepali-handwritten (~1K).\n"
            "  Re-run after syncing GCS datasets to --base-data-root for full count.",
        )
    if negative < 15_000:
        click.echo(
            f"  WARNING: negative class {negative:,} < 15,000 target.\n"
            "  Add --negatives-from pubtabnet or --negatives-from doclaynet after syncing.",
        )
    if positive >= 40_000 and negative >= 15_000:
        click.echo("\n  GO: Handwriting manifest meets 40K+/15K+ class targets.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--l2-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("/mnt/e/image_detection/metadata_registry/json"),
    show_default=True,
    help="Directory containing {dataset}_metadata.json L2 files.",
)
@click.option(
    "--base-data-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("/mnt/e/image_detection/01_base_data"),
    show_default=True,
    help="Root directory containing all dataset image directories.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("handwriting_manifest.jsonl"),
    show_default=True,
    help="Output JSONL manifest path.",
)
@click.option(
    "--negatives-from",
    multiple=True,
    type=click.Choice(list(cfg.name for cfg in _NEGATIVE_DATASETS)),
    default=["doclaynet"],
    show_default=True,
    help="Negative-class dataset(s) to include.",
)
@click.option(
    "--negatives-count",
    default=20000,
    show_default=True,
    help="Total negative records to sample (split evenly across --negatives-from).",
)
@click.option(
    "--seed",
    default=42,
    show_default=True,
    help="Random seed for reproducible sampling.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Count records without writing output file.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Print per-dataset breakdown.",
)
def main(  # noqa: PLR0913
    l2_dir: Path,
    base_data_root: Path,
    output: Path,
    negatives_from: tuple[str, ...],
    negatives_count: int,
    seed: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Assemble a handwriting-presence training manifest.

    Reads L2 metadata for configured source datasets, derives page-level
    handwriting presence labels, and writes a JSONL manifest suitable for
    the SigLIP 2 handwriting detection heads (G1-G4).

    Example::

        uv run python scripts/harmonize_handwriting_labels.py \\
            --negatives-from doclaynet \\
            --negatives-count 20000 \\
            --output handwriting_manifest.jsonl
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rng = random.Random(seed)

    all_records: list[dict[str, Any]] = []

    # --- IAM (filesystem-based, most reliable) ---
    click.echo("Processing IAM (filesystem) …")
    iam_records = _build_iam_records_from_filesystem(
        base_data_root, split_fractions=(0.80, 0.10, 0.10), rng=rng
    )
    click.echo(f"  IAM: {len(iam_records):,} form PNGs")
    all_records.extend(iam_records)

    # --- Positive datasets via L2 metadata ---
    for config in tqdm(_POSITIVE_DATASETS, desc="Positive datasets"):
        if config.name == "iam":
            continue  # already handled above via filesystem
        samples = _load_l2_metadata(l2_dir, config.name)
        if not samples:
            logger.warning("Skipping %s — no L2 metadata", config.name)
            continue

        if config.strategy == "all_handwritten":
            recs = _build_all_handwritten_records(samples, config, base_data_root, rng)
        elif config.strategy == "model_derived":
            recs = _build_model_derived_records(samples, config, base_data_root, rng)
        else:
            logger.error("Unknown strategy '%s' for %s", config.strategy, config.name)
            continue

        click.echo(f"  {config.name}: {len(recs):,} records")
        all_records.extend(recs)

    # --- Negative datasets ---
    neg_per_dataset = negatives_count // max(len(negatives_from), 1)
    for ds_name in tqdm(negatives_from, desc="Negative datasets"):
        config = _ALL_CONFIGS.get(ds_name)
        if config is None:
            logger.error("Unknown dataset '%s' in --negatives-from", ds_name)
            continue
        # Check directory before loading potentially large L2 file
        neg_dir = base_data_root / config.base_subdir
        if not neg_dir.exists():
            logger.warning(
                "Skipping %s (negatives) — directory not found: %s", ds_name, neg_dir
            )
            continue
        samples = _load_l2_metadata(l2_dir, ds_name)
        if not samples:
            logger.warning("Skipping %s — no L2 metadata", ds_name)
            continue
        recs = _build_all_printed_records(
            samples, config, base_data_root, rng, target_count=neg_per_dataset
        )
        click.echo(f"  {ds_name} (negatives): {len(recs):,} records")
        all_records.extend(recs)

    # --- Summary ---
    _print_summary(all_records, verbose=verbose)

    if dry_run:
        click.echo("\nDry-run complete — no output written.")
        return

    # --- Write manifest ---
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as fh:
        for record in all_records:
            fh.write(json.dumps(record) + "\n")
    click.echo(f"\nWrote {len(all_records):,} records → {output}")


if __name__ == "__main__":
    main()
