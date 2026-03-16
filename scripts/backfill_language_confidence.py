"""Backfill language/script confidence into Layer 2 metadata from enrichment files.

Merges per-sample language detection confidence from *_language_enrichment.json
files into the main *_metadata.json registry files. Applies the revised confidence
tier system:

  - Per-sample ground truth:     confidence=1.0,  tier_0_exact
  - known_language (dataset-level): confidence=0.95, tier_1_annotation
  - folder_based label:           confidence=0.95, tier_1_annotation
  - OpenLID detection:            per-sample,      tier_2_model

When the primary source is known_language or folder_based AND OpenLID data
exists, the OpenLID result is stored as a secondary validation signal
(openlid_language, openlid_script, openlid_confidence).

Usage:
    python scripts/backfill_language_confidence.py --datasets funsd sroie
    python scripts/backfill_language_confidence.py --all --dry-run
    python scripts/backfill_language_confidence.py --all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- Confidence tier configuration ---
KNOWN_LANGUAGE_CONFIDENCE = 0.95
FOLDER_BASED_CONFIDENCE = 0.95
GROUND_TRUTH_CONFIDENCE = 1.0


def load_enrichment(enrichment_path: Path) -> dict[str, Any] | None:
    """Load a language enrichment JSON file.

    Args:
        enrichment_path: Path to the *_language_enrichment.json file.

    Returns:
        Parsed JSON dict, or None if file missing/invalid.
    """
    if not enrichment_path.exists():
        return None
    with open(enrichment_path) as f:
        return json.load(f)


def build_openlid_index(
    enrichment: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build a lookup from image_id to OpenLID per-sample results.

    Args:
        enrichment: Parsed language enrichment dict.

    Returns:
        Dict mapping image_id to {language, script, confidence, method}.
    """
    samples = enrichment.get("samples", [])
    index: dict[str, dict[str, Any]] = {}
    for sample in samples:
        image_id = sample.get("image_id")
        if image_id:
            index[image_id] = {
                "language": sample.get("language"),
                "script": sample.get("script"),
                "confidence": sample.get("confidence"),
                "method": sample.get("method", "openlid_v2"),
            }
    return index


def extract_image_id(sample: dict[str, Any]) -> str | None:
    """Extract a matchable image_id from a metadata sample.

    Checks source.original_filename first (primary metadata format),
    then falls back to other id fields. Strips path/extension to get bare id.

    Args:
        sample: A sample dict from the metadata JSON.

    Returns:
        Cleaned image_id string, or None.
    """
    # Primary: source.original_filename (used by annotate_base_metadata.py)
    source = sample.get("source", {})
    original_filename = source.get("original_filename")
    if original_filename:
        return Path(str(original_filename)).stem

    # Also try source.original_path (strip directory)
    original_path = source.get("original_path")
    if original_path:
        return Path(str(original_path)).stem

    # Try top-level id fields
    for key in ("image_id", "filename"):
        value = sample.get(key)
        if value:
            return Path(str(value)).stem

    # Try nested immutable layer
    immutable = sample.get("immutable", {})
    for key in ("original_filename", "image_id"):
        value = immutable.get(key)
        if value:
            return Path(str(value)).stem

    return None


def backfill_known_language(
    sample_data: dict[str, Any],
    enrichment: dict[str, Any],
    openlid_result: dict[str, Any] | None,
) -> dict[str, str | float | bool | None]:
    """Apply known_language confidence to a sample's enrichment data.

    Args:
        sample_data: The sample's enrichment data dict (mutated in place).
        enrichment: The dataset-level enrichment file.
        openlid_result: Per-sample OpenLID result if available.

    Returns:
        Dict of fields that were set (for logging).
    """
    changes: dict[str, str | float | bool | None] = {}

    sample_data["language_confidence"] = KNOWN_LANGUAGE_CONFIDENCE
    sample_data["language_detection_method"] = "dataset_known_language"
    sample_data["language_provenance_tier"] = "tier_1_annotation"
    sample_data["language_is_soft_label"] = False

    changes["language_confidence"] = KNOWN_LANGUAGE_CONFIDENCE
    changes["language_detection_method"] = "dataset_known_language"

    # Store OpenLID as secondary signal if available
    if openlid_result:
        sample_data["openlid_language"] = openlid_result["language"]
        sample_data["openlid_script"] = openlid_result["script"]
        sample_data["openlid_confidence"] = openlid_result["confidence"]
        changes["openlid_confidence"] = openlid_result["confidence"]
        changes["openlid_agrees"] = openlid_result["language"] == enrichment.get(
            "language"
        ) or openlid_result["script"] == enrichment.get("script")

    return changes


def backfill_folder_based(
    sample_data: dict[str, Any],
    openlid_result: dict[str, Any] | None,
) -> dict[str, str | float | bool | None]:
    """Apply folder_based confidence to a sample's enrichment data.

    Args:
        sample_data: The sample's enrichment data dict (mutated in place).
        openlid_result: Per-sample OpenLID result if available.

    Returns:
        Dict of fields that were set (for logging).
    """
    changes: dict[str, str | float | bool | None] = {}

    sample_data["language_confidence"] = FOLDER_BASED_CONFIDENCE
    sample_data["language_detection_method"] = "folder_label"
    sample_data["language_provenance_tier"] = "tier_1_annotation"
    sample_data["language_is_soft_label"] = False

    changes["language_confidence"] = FOLDER_BASED_CONFIDENCE
    changes["language_detection_method"] = "folder_label"

    if openlid_result:
        sample_data["openlid_language"] = openlid_result["language"]
        sample_data["openlid_script"] = openlid_result["script"]
        sample_data["openlid_confidence"] = openlid_result["confidence"]
        changes["openlid_confidence"] = openlid_result["confidence"]

    return changes


def backfill_openlid_detection(
    sample_data: dict[str, Any],
    openlid_result: dict[str, Any],
) -> dict[str, str | float | bool | None]:
    """Apply OpenLID per-sample confidence as the primary signal.

    Args:
        sample_data: The sample's enrichment data dict (mutated in place).
        openlid_result: Per-sample OpenLID detection result.

    Returns:
        Dict of fields that were set (for logging).
    """
    changes: dict[str, str | float | bool | None] = {}

    confidence = openlid_result["confidence"]
    sample_data["language_confidence"] = confidence
    sample_data["language_detection_method"] = "openlid_v2"
    sample_data["language_provenance_tier"] = "tier_2_model"
    sample_data["language_is_soft_label"] = True

    # Also update the language/script if OpenLID is the primary source
    sample_data["iso639_language"] = openlid_result["language"]
    sample_data["iso15924_script"] = openlid_result["script"]

    changes["language_confidence"] = confidence
    changes["language_detection_method"] = "openlid_v2"
    changes["iso639_language"] = openlid_result["language"]

    return changes


def backfill_no_enrichment(
    sample_data: dict[str, Any],
) -> dict[str, str | float | bool | None]:
    """Mark a sample as having no language confidence data.

    Args:
        sample_data: The sample's enrichment data dict (mutated in place).

    Returns:
        Dict of fields that were set (for logging).
    """
    sample_data["language_confidence"] = None
    sample_data["language_detection_method"] = "none"
    sample_data["language_provenance_tier"] = "tier_3_heuristic"
    sample_data["language_is_soft_label"] = True

    return {"language_confidence": None, "language_detection_method": "none"}


def _backfill_sample_by_type(
    enrichment_type: str,
    data: dict[str, Any],
    enrichment: dict[str, Any],
    openlid_result: dict[str, Any] | None,
    openlid_index: dict[str, dict[str, Any]],
    stats: dict[str, int],
) -> None:
    """Apply the correct backfill strategy for a single sample based on enrichment type.

    Mutates ``data`` and ``stats`` in place.

    Args:
        enrichment_type: Enrichment type string from the dataset enrichment file.
        data: Sample enrichment data to mutate in place.
        enrichment: Dataset-level enrichment metadata.
        openlid_result: Per-sample OpenLID result, if available.
        openlid_index: Lookup table for OpenLID per-sample results.
        stats: Stats accumulator to update in place.
    """
    if enrichment_type == "known_language":
        backfill_known_language(data, enrichment, openlid_result)
        stats["known_language"] += 1
        if openlid_result:
            stats["openlid_secondary"] += 1
            stats["openlid_matched"] += 1
        elif openlid_index:
            stats["openlid_unmatched"] += 1
        return

    if enrichment_type in ("folder_based_labels", "manifest_labels"):
        backfill_folder_based(data, openlid_result)
        stats["folder_based"] += 1
        if openlid_result:
            stats["openlid_secondary"] += 1
            stats["openlid_matched"] += 1
        elif openlid_index:
            stats["openlid_unmatched"] += 1
        return

    if enrichment_type == "openlid_detection":
        _backfill_openlid_sample(data, enrichment, openlid_result, stats)
        return

    backfill_no_enrichment(data)
    stats["no_enrichment"] += 1


def _backfill_openlid_sample(
    data: dict[str, Any],
    enrichment: dict[str, Any],
    openlid_result: dict[str, Any] | None,
    stats: dict[str, int],
) -> None:
    """Handle openlid_detection enrichment type for a single sample.

    Args:
        data: Sample enrichment data to mutate in place.
        enrichment: Dataset-level enrichment metadata.
        openlid_result: Per-sample OpenLID result, if available.
        stats: Stats accumulator to update in place.
    """
    if openlid_result:
        backfill_openlid_detection(data, openlid_result)
        stats["openlid_primary"] += 1
        stats["openlid_matched"] += 1
        return

    avg_conf = enrichment.get("avg_confidence")
    if avg_conf is not None:
        data["language_confidence"] = round(avg_conf, 3)
        data["language_detection_method"] = "openlid_v2_dataset_avg"
        data["language_provenance_tier"] = "tier_2_model"
        data["language_is_soft_label"] = True
        stats["openlid_primary"] += 1
    else:
        backfill_no_enrichment(data)
        stats["no_enrichment"] += 1
    stats["openlid_unmatched"] += 1


def process_dataset(
    dataset_name: str,
    metadata_dir: Path,
    dry_run: bool = False,
) -> dict[str, int]:
    """Process a single dataset: merge language enrichment into metadata.

    Args:
        dataset_name: Canonical dataset name.
        metadata_dir: Directory containing both *_metadata.json and
            *_language_enrichment.json files.
        dry_run: If True, report changes without writing.

    Returns:
        Stats dict with counts of samples processed by category.
    """
    stats: dict[str, int] = {
        "total": 0,
        "known_language": 0,
        "folder_based": 0,
        "openlid_primary": 0,
        "openlid_secondary": 0,
        "no_enrichment": 0,
        "openlid_matched": 0,
        "openlid_unmatched": 0,
        "already_has_confidence": 0,
    }

    metadata_name = dataset_name.replace("-", "_")
    metadata_path = metadata_dir / f"{metadata_name}_metadata.json"
    if not metadata_path.exists():
        logger.warning(f"No metadata file for {dataset_name}: {metadata_path}")
        return stats

    enrichment_path = metadata_dir / f"{metadata_name}_language_enrichment.json"
    enrichment = load_enrichment(enrichment_path)
    if enrichment is None:
        logger.warning(f"No language enrichment for {dataset_name}: {enrichment_path}")
        return stats

    enrichment_type = enrichment.get("enrichment_type", "unknown")
    logger.info(
        f"{dataset_name}: enrichment_type={enrichment_type}, "
        f"total_samples={enrichment.get('total_samples', 'N/A')}"
    )

    openlid_index = build_openlid_index(enrichment)
    logger.info(f"  OpenLID per-sample index: {len(openlid_index)} entries")

    with open(metadata_path) as f:
        metadata = json.load(f)

    samples = metadata.get("samples", [])
    stats["total"] = len(samples)

    for sample in samples:
        versions = sample.get("enrichments", {}).get("versions", [])
        if not versions:
            stats["no_enrichment"] += 1
            continue

        data = versions[0].get("data", {})
        if data.get("language_confidence") is not None:
            stats["already_has_confidence"] += 1
            continue

        image_id = extract_image_id(sample)
        openlid_result = openlid_index.get(image_id) if image_id else None

        _backfill_sample_by_type(
            enrichment_type,
            data,
            enrichment,
            openlid_result,
            openlid_index,
            stats,
        )

    if not dry_run:
        metadata.setdefault("backfill_history", [])
        metadata["backfill_history"].append(
            {
                "operation": "language_confidence_backfill",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "enrichment_type": enrichment_type,
                "stats": stats,
            }
        )
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"  Written: {metadata_path}")
    else:
        logger.info(f"  DRY RUN: would write {metadata_path}")

    return stats


def find_all_datasets(metadata_dir: Path) -> list[str]:
    """Find all datasets that have both metadata and language enrichment files.

    Args:
        metadata_dir: Directory containing metadata JSON files.

    Returns:
        List of dataset names.
    """
    datasets = []
    for path in sorted(metadata_dir.glob("*_language_enrichment.json")):
        name = path.stem.replace("_language_enrichment", "")
        metadata_path = metadata_dir / f"{name}_metadata.json"
        if metadata_path.exists():
            datasets.append(name)
    return datasets


def main() -> None:
    """Run the language confidence backfill."""
    parser = argparse.ArgumentParser(
        description="Backfill language/script confidence into Layer 2 metadata"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        help="Dataset names to process (default: auto-detect all)",
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/metadata_registry/json"),
        help="Directory containing metadata JSON files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all datasets with language enrichment",
    )

    args = parser.parse_args()

    if args.all:
        datasets = find_all_datasets(args.metadata_dir)
    elif args.datasets:
        datasets = args.datasets
    else:
        print("Specify --datasets or --all", file=sys.stderr)
        sys.exit(1)

    logger.info(f"Processing {len(datasets)} datasets")
    if args.dry_run:
        logger.info("DRY RUN MODE - no files will be written")

    total_stats: dict[str, int] = {
        "total": 0,
        "known_language": 0,
        "folder_based": 0,
        "openlid_primary": 0,
        "openlid_secondary": 0,
        "no_enrichment": 0,
        "openlid_matched": 0,
        "openlid_unmatched": 0,
        "already_has_confidence": 0,
    }

    for dataset_name in datasets:
        stats = process_dataset(dataset_name, args.metadata_dir, args.dry_run)
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

        # Print per-dataset summary
        logger.info(
            f"  {dataset_name}: total={stats['total']} "
            f"known={stats['known_language']} folder={stats['folder_based']} "
            f"openlid_primary={stats['openlid_primary']} "
            f"openlid_secondary={stats['openlid_secondary']} "
            f"no_enrich={stats['no_enrichment']} "
            f"already={stats['already_has_confidence']}"
        )

    # Final summary
    print("\n" + "=" * 60)
    print("BACKFILL SUMMARY")
    print("=" * 60)
    print(f"Total samples:          {total_stats['total']:>8,}")
    print(f"Known language (0.95):  {total_stats['known_language']:>8,}")
    print(f"Folder-based (0.95):    {total_stats['folder_based']:>8,}")
    print(f"OpenLID primary:        {total_stats['openlid_primary']:>8,}")
    print(f"OpenLID secondary:      {total_stats['openlid_secondary']:>8,}")
    print(f"No enrichment (null):   {total_stats['no_enrichment']:>8,}")
    print(f"Already had confidence: {total_stats['already_has_confidence']:>8,}")
    print(f"OpenLID matched:        {total_stats['openlid_matched']:>8,}")
    print(f"OpenLID unmatched:      {total_stats['openlid_unmatched']:>8,}")


if __name__ == "__main__":
    main()
