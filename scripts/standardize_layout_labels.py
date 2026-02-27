#!/usr/bin/env python3
"""Standardize layout labels in metadata registry using the layout taxonomy.

Reads existing Layer 1/2 metadata JSON files from the registry, converts
class_name fields in layout_detections to canonical form via LayoutTaxonomy,
and writes canonical_class, source_schema, is_lossy back to each record.

Three-layer metadata architecture:
1. IMMUTABLE LAYER: Original labels preserved exactly as provided
2. ENRICHMENT LAYER: Our derived annotations with full provenance (versioned)
3. TRAINING LAYER: Computed on-demand from original + enrichments

This script modifies the enrichment layer to add canonical layout labels.

Usage:
    # Standardize a single dataset (explicit source schema)
    python scripts/standardize_layout_labels.py \\
        --dataset doclaynet \\
        --source-schema doclaynet \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json \\
        --dry-run

    # Standardize a single dataset (auto-detect source schema)
    python scripts/standardize_layout_labels.py \\
        --dataset doclaynet \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json

    # Standardize all datasets (auto-detect source schemas)
    python scripts/standardize_layout_labels.py \\
        --all \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json

    # Dry-run mode (shows what would change without modifying files)
    python scripts/standardize_layout_labels.py \\
        --all \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json \\
        --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Parser-name to source-schema mapping
# ---------------------------------------------------------------------------
# Maps dataset parser names (from annotation/config/datasets.py) to the
# layout schema they produce.  Only datasets whose parsers emit layout
# annotations are listed here; all others are implicitly "no layout".

PARSER_TO_SCHEMA: dict[str, str] = {
    # DocLayNet native (COCO annotations with DocLayNet classes)
    "doclaynet": "doclaynet",
    # DocStructBench / DocLayout-YOLO output
    "docstructbench": "docstructbench",
    "docsynth300k": "docsynth300k",
    # PubLayNet family (COCO annotations with PubLayNet classes)
    "pubtabnet": "publaynet",
    "fintabnet": "publaynet",
    "tablebank": "doclaynet",
    # FUNSD entity-type annotations
    "funsd": "funsd",
}

# Enrichment tier-to-schema mapping for YOLO-inferred layouts
YOLO_ENRICHMENT_METHODS = {"tier_2_yolo", "tier_2_doclayout_yolo"}
YOLO_DETECTION_SOURCES = {"doclayout_yolo", "DocLayout-YOLO"}

# Detection source -> schema mapping for enrichment-based detection
DETECTION_SOURCE_SCHEMA: dict[str, str] = {
    "doclayout_yolo": "docstructbench",
    "DocLayout-YOLO": "docstructbench",
    "docling": "docling",
    "Docling": "docling",
}


def _auto_detect_source_schema(dataset_name: str) -> str | None:
    """Auto-detect source schema from dataset parser configuration.

    Looks up the dataset in the annotation config registry and maps
    its parser_name to a layout schema.

    Args:
        dataset_name: Canonical dataset name.

    Returns:
        Source schema name or None if not determinable.
    """
    try:
        from image_preprocessing_detector.annotation.config.datasets import (
            DATASET_CONFIGS,
        )

        config = DATASET_CONFIGS.get(dataset_name)
        if config is None:
            log.warning(
                "dataset_not_in_config",
                dataset=dataset_name,
            )
            return None

        parser_name = config.parser_name
        if parser_name is None:
            return None

        schema = PARSER_TO_SCHEMA.get(parser_name)
        if schema is not None:
            log.info(
                "auto_detected_schema",
                dataset=dataset_name,
                parser=parser_name,
                schema=schema,
            )
        return schema

    except ImportError:
        log.warning("annotation_config_not_available")
        return None


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class StandardizationReport:
    """Report for a single dataset standardization run.

    Attributes:
        dataset: Dataset name processed.
        source_schema: Source schema used for conversion.
        total_files: Total metadata JSON files found.
        files_with_layout: Files containing layout_detections.
        total_detections: Total layout detection elements found.
        conversions_lossless: Number of lossless conversions performed.
        conversions_lossy: Number of lossy conversions performed.
        already_canonical: Detections already had canonical_class set.
        unknown_labels: Labels that could not be mapped.
        errors: List of error descriptions.
        files_modified: Number of files actually written.
    """

    dataset: str
    source_schema: str
    total_files: int = 0
    files_with_layout: int = 0
    total_detections: int = 0
    conversions_lossless: int = 0
    conversions_lossy: int = 0
    already_canonical: int = 0
    unknown_labels: int = 0
    errors: list[str] = field(default_factory=list)
    files_modified: int = 0

    def summary(self) -> str:
        """Format a human-readable summary of the report."""
        lines = [
            f"  Dataset:            {self.dataset}",
            f"  Source schema:      {self.source_schema}",
            f"  Files scanned:      {self.total_files}",
            f"  Files with layout:  {self.files_with_layout}",
            f"  Total detections:   {self.total_detections}",
            f"  Lossless:           {self.conversions_lossless}",
            f"  Lossy:              {self.conversions_lossy}",
            f"  Already canonical:  {self.already_canonical}",
            f"  Unknown labels:     {self.unknown_labels}",
            f"  Files modified:     {self.files_modified}",
        ]
        if self.errors:
            lines.append(f"  Errors:             {len(self.errors)}")
            for err in self.errors[:10]:
                lines.append(f"    - {err}")
            if len(self.errors) > 10:
                lines.append(f"    ... and {len(self.errors) - 10} more")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core standardization logic
# ---------------------------------------------------------------------------


def _get_latest_enrichment(
    record: dict[str, Any],
) -> dict[str, Any] | None:
    """Get the latest enrichment version data from a metadata record.

    Handles two metadata formats:
    1. Per-image format: ``enrichment_versions[].data``
    2. Annotate script format: ``enrichments.versions[].data``

    Args:
        record: Full metadata JSON record.

    Returns:
        The enrichment data dict from the latest version, or None.
    """
    # Format 1: per-image JSON files (enrichment_versions at top level)
    versions = record.get("enrichment_versions", [])

    # Format 2: annotate_base_metadata.py output (enrichments.versions)
    if not versions:
        enrichments = record.get("enrichments", {})
        if isinstance(enrichments, dict):
            versions = enrichments.get("versions", [])

    if not versions:
        return None

    # Find the version matching current_version, or fall back to last
    current_ver = record.get("current_version")
    if current_ver is None:
        enrichments = record.get("enrichments", {})
        current_ver = enrichments.get("current_version", len(versions))

    for ver in versions:
        if ver.get("version") == current_ver:
            return ver.get("data")

    # Fallback: last version
    return versions[-1].get("data") if versions else None


def _detect_schema_from_enrichment(record: dict[str, Any]) -> str | None:
    """Detect source schema from enrichment metadata.

    Checks the enrichment method and detection source fields to determine
    the layout schema (e.g. docstructbench for YOLO, docling for Docling).

    Args:
        record: Full metadata JSON record.

    Returns:
        Detected source schema or None if not determinable.
    """
    enrichment_data = _get_latest_enrichment(record)
    if enrichment_data is None:
        return None

    # Check enrichment version metadata for method field
    versions = record.get("enrichment_versions", [])
    if not versions:
        enrichments = record.get("enrichments", {})
        if isinstance(enrichments, dict):
            versions = enrichments.get("versions", [])

    for ver in versions:
        method = ver.get("method", "")
        if method in YOLO_ENRICHMENT_METHODS:
            return "docstructbench"

    # Check detection source fields against known source->schema mapping
    detections = enrichment_data.get("layout_detections", [])
    for det in detections[:3]:  # Check first few detections
        source = det.get("source", "")
        schema = DETECTION_SOURCE_SCHEMA.get(source)
        if schema is not None:
            return schema

    return None


def standardize_record(
    record: dict[str, Any],
    taxonomy: Any,
    source_schema: str,
    dry_run: bool = False,
) -> tuple[bool, int, int, int, int, int, list[str]]:
    """Standardize layout detections in a single metadata record.

    For each detection with a class_name, converts to canonical form
    and writes canonical_class, source_schema, source_label, is_lossy,
    conversion_confidence back. Also converts class_name to DocLayNet
    PascalCase (e.g. ``text`` -> ``Text``, ``list_item`` -> ``List-Item``).

    Args:
        record: Full metadata JSON record (modified in-place if not dry_run).
        taxonomy: LayoutTaxonomy instance.
        source_schema: Source schema name for conversion.
        dry_run: If True, do not modify the record.

    Returns:
        Tuple of (modified, lossless, lossy, already, unknown, total, errors).
    """
    enrichment_data = _get_latest_enrichment(record)
    if enrichment_data is None:
        return False, 0, 0, 0, 0, 0, []

    detections = enrichment_data.get("layout_detections")
    if not detections:
        return False, 0, 0, 0, 0, 0, []

    modified = False
    lossless = 0
    lossy = 0
    already = 0
    unknown = 0
    total = len(detections)
    errors: list[str] = []

    for detection in detections:
        class_name = detection.get("class_name")
        if not class_name:
            continue

        # Skip if already standardized
        if detection.get("canonical_class") is not None:
            already += 1
            continue

        try:
            canonical = taxonomy.to_canonical(class_name, source_schema)

            # Determine lossiness: if canonical has a parent and the label
            # maps to a child class, the conversion to DocLayNet would be lossy
            doclaynet_label = taxonomy.to_doclaynet(canonical)
            # Check if the original class maps directly to a top-level class
            canonical_info = taxonomy._canonical.get(canonical, {})
            is_lossy = canonical_info.get("parent") is not None

            if canonical == "UNKNOWN":
                unknown += 1
                is_lossy = True

            if not dry_run:
                detection["canonical_class"] = canonical
                detection["source_schema"] = source_schema
                detection["source_label"] = class_name
                detection["is_lossy"] = is_lossy
                detection["class_name"] = doclaynet_label
                detection["conversion_confidence"] = 0.0 if is_lossy else 1.0
                modified = True

            if is_lossy:
                lossy += 1
            else:
                lossless += 1

        except Exception as exc:
            err_msg = f"Failed to convert '{class_name}': {exc}"
            errors.append(err_msg)
            log.warning(
                "conversion_error",
                class_name=class_name,
                schema=source_schema,
                error=str(exc),
            )

    return modified, lossless, lossy, already, unknown, total, errors


def standardize_dataset(
    metadata_dir: Path,
    dataset_name: str,
    taxonomy: Any,
    source_schema: str,
    dry_run: bool = False,
) -> StandardizationReport:
    """Standardize all layout labels for a single dataset.

    Handles two metadata formats:
    1. Per-image directory: ``metadata_dir/{dataset}/`` with individual JSON files
    2. Single-file format: ``metadata_dir/{dataset}_metadata.json`` with samples array

    Args:
        metadata_dir: Root metadata registry directory.
        dataset_name: Dataset name.
        taxonomy: LayoutTaxonomy instance.
        source_schema: Source schema for label conversion.
        dry_run: If True, report changes without writing.

    Returns:
        StandardizationReport with statistics.
    """
    report = StandardizationReport(
        dataset=dataset_name,
        source_schema=source_schema,
    )

    # Try format 1: per-image directory
    dataset_dir = metadata_dir / dataset_name
    if dataset_dir.is_dir():
        return _standardize_per_image_dir(
            dataset_dir,
            report,
            taxonomy,
            source_schema,
            dry_run,
        )

    # Try format 2: single-file with samples array
    single_file = metadata_dir / f"{dataset_name}_metadata.json"
    if single_file.exists():
        return _standardize_single_file(
            single_file,
            report,
            taxonomy,
            source_schema,
            dry_run,
        )

    report.errors.append(f"No metadata found: neither {dataset_dir} nor {single_file}")
    log.error(
        "dataset_metadata_not_found",
        dataset=dataset_name,
        tried_dir=str(dataset_dir),
        tried_file=str(single_file),
    )
    return report


def _standardize_per_image_dir(
    dataset_dir: Path,
    report: StandardizationReport,
    taxonomy: Any,
    source_schema: str,
    dry_run: bool,
) -> StandardizationReport:
    """Standardize layout labels from per-image JSON files in a directory."""
    json_files = sorted(dataset_dir.glob("*.json"))
    report.total_files = len(json_files)

    if not json_files:
        log.info(
            "no_json_files",
            dataset=report.dataset,
            dir=str(dataset_dir),
        )
        return report

    for json_path in json_files:
        try:
            with open(json_path, encoding="utf-8") as fh:
                record = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            report.errors.append(f"Failed to read {json_path.name}: {exc}")
            continue

        _apply_standardize_record(record, report, taxonomy, source_schema, dry_run)

        if not dry_run and report.files_modified >= 0:
            try:
                with open(json_path, "w", encoding="utf-8") as fh:
                    json.dump(record, fh, indent=2, ensure_ascii=False)
                    fh.write("\n")
                report.files_modified += 1
            except OSError as exc:
                report.errors.append(f"Failed to write {json_path.name}: {exc}")

    return report


def _standardize_single_file(
    file_path: Path,
    report: StandardizationReport,
    taxonomy: Any,
    source_schema: str,
    dry_run: bool,
) -> StandardizationReport:
    """Standardize layout labels from annotate_base_metadata single-file format.

    Reads ``{dataset}_metadata.json`` which contains a ``samples`` array,
    iterates over each sample record, and applies taxonomy conversions.
    Auto-detects DocLayout-YOLO enrichments and overrides source schema
    when appropriate.
    """
    try:
        with open(file_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        report.errors.append(f"Failed to read {file_path.name}: {exc}")
        return report

    samples = data.get("samples", [])
    report.total_files = 1  # Single file containing all samples
    any_modified = False

    # Auto-detect schema from first sample with layout detections
    # Scan up to 500 samples for sparse-detection datasets (e.g. cvsi)
    effective_schema = source_schema
    for sample in samples[:500]:
        detected = _detect_schema_from_enrichment(sample)
        if detected is not None:
            if detected != source_schema:
                log.info(
                    "schema_override_from_enrichment",
                    configured=source_schema,
                    detected=detected,
                    file=file_path.name,
                )
            effective_schema = detected
            report.source_schema = effective_schema
            break

    for record in samples:
        modified = _apply_standardize_record(
            record,
            report,
            taxonomy,
            effective_schema,
            dry_run,
        )
        if modified:
            any_modified = True

    if any_modified and not dry_run:
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            report.files_modified = 1
        except OSError as exc:
            report.errors.append(f"Failed to write {file_path.name}: {exc}")

    return report


def _apply_standardize_record(
    record: dict[str, Any],
    report: StandardizationReport,
    taxonomy: Any,
    source_schema: str,
    dry_run: bool,
) -> bool:
    """Apply standardization to a single record and update report counters.

    Returns:
        True if the record was modified.
    """
    (
        modified,
        lossless,
        lossy,
        already_count,
        unknown_count,
        total_det,
        errors,
    ) = standardize_record(record, taxonomy, source_schema, dry_run)

    if total_det > 0:
        report.files_with_layout += 1
    report.total_detections += total_det
    report.conversions_lossless += lossless
    report.conversions_lossy += lossy
    report.already_canonical += already_count
    report.unknown_labels += unknown_count
    report.errors.extend(errors)

    return modified


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Standardize layout labels in metadata registry using "
            "the layout taxonomy. Converts class_name fields in "
            "layout_detections to canonical form."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Single dataset with explicit schema\n"
            "  python scripts/standardize_layout_labels.py \\\n"
            "      --dataset doclaynet --source-schema doclaynet \\\n"
            "      --metadata-dir /mnt/e/image_detection/"
            "metadata_registry/json\n\n"
            "  # All datasets with auto-detection\n"
            "  python scripts/standardize_layout_labels.py \\\n"
            "      --all \\\n"
            "      --metadata-dir /mnt/e/image_detection/"
            "metadata_registry/json\n\n"
            "  # Dry-run mode\n"
            "  python scripts/standardize_layout_labels.py \\\n"
            "      --all --dry-run \\\n"
            "      --metadata-dir /mnt/e/image_detection/"
            "metadata_registry/json"
        ),
    )

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--dataset",
        type=str,
        help="Single dataset name to standardize.",
    )
    target_group.add_argument(
        "--all",
        action="store_true",
        dest="process_all",
        help="Process all datasets found in metadata-dir.",
    )

    parser.add_argument(
        "--source-schema",
        type=str,
        default=None,
        help=(
            "Source layout schema (e.g. doclaynet, docstructbench). "
            "Auto-detected from parser config if not specified."
        ),
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/metadata_registry/json"),
        help="Root metadata registry directory (default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output.",
    )

    return parser


def _detect_schema_from_metadata_file(
    metadata_dir: Path,
    dataset_name: str,
) -> str | None:
    """Try to detect source schema by sampling enrichment data from the metadata file.

    Reads the first few records from the dataset's metadata and checks
    enrichment metadata for YOLO-based layout detections.

    Args:
        metadata_dir: Root metadata directory.
        dataset_name: Dataset name.

    Returns:
        Detected source schema or None.
    """
    # Try single-file format first (most common for annotate_base_metadata output)
    single_file = metadata_dir / f"{dataset_name}_metadata.json"
    if single_file.exists():
        try:
            with open(single_file, encoding="utf-8") as fh:
                data = json.load(fh)
            samples = data.get("samples", [])
            # Scan up to 500 samples to handle sparse-detection datasets
            # (e.g. cvsi has tiny character crops where YOLO only detects
            # layout elements in ~12% of images, first hit at index ~260)
            for sample in samples[:500]:
                detected = _detect_schema_from_enrichment(sample)
                if detected is not None:
                    log.info(
                        "schema_detected_from_enrichment",
                        dataset=dataset_name,
                        schema=detected,
                    )
                    return detected
        except (json.JSONDecodeError, OSError):
            pass

    # Try per-image directory format
    dataset_dir = metadata_dir / dataset_name
    if dataset_dir.is_dir():
        json_files = sorted(dataset_dir.glob("*.json"))[:10]
        for json_path in json_files:
            try:
                with open(json_path, encoding="utf-8") as fh:
                    record = json.load(fh)
                detected = _detect_schema_from_enrichment(record)
                if detected is not None:
                    log.info(
                        "schema_detected_from_enrichment",
                        dataset=dataset_name,
                        schema=detected,
                    )
                    return detected
            except (json.JSONDecodeError, OSError):
                continue

    return None


def _discover_datasets(metadata_dir: Path) -> list[str]:
    """Discover all datasets in the metadata registry.

    Finds both per-image directories and single-file metadata JSON files.

    Args:
        metadata_dir: Root metadata directory.

    Returns:
        Sorted list of unique dataset names.
    """
    if not metadata_dir.is_dir():
        return []

    names: set[str] = set()
    for entry in metadata_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            names.add(entry.name)
        elif entry.is_file() and entry.name.endswith("_metadata.json"):
            # Extract dataset name from "{name}_metadata.json"
            ds_name = entry.name.removesuffix("_metadata.json")
            names.add(ds_name)

    return sorted(names)


def _resolve_source_schema(
    ds_name: str,
    explicit_schema: str | None,
    metadata_dir: Path,
) -> str | None:
    """Resolve the source schema for a dataset (explicit > auto-detect > metadata)."""
    schema = explicit_schema or _auto_detect_source_schema(ds_name)
    if schema is None:
        schema = _detect_schema_from_metadata_file(metadata_dir, ds_name)
    return schema


def _build_targets(
    args: argparse.Namespace,
    metadata_dir: Path,
) -> list[tuple[str, str | None]]:
    """Build list of (dataset_name, source_schema) targets to process."""
    if args.process_all:
        datasets = _discover_datasets(metadata_dir)
        log.info("discovered_datasets", count=len(datasets))
        return [
            (ds_name, _resolve_source_schema(ds_name, args.source_schema, metadata_dir))
            for ds_name in datasets
        ]
    return [
        (
            args.dataset,
            _resolve_source_schema(args.dataset, args.source_schema, metadata_dir),
        )
    ]


def _print_standardization_summary(
    reports: list[StandardizationReport],
    skipped: list[str],
    dry_run: bool,
) -> int:
    """Print summary report and return the total error count."""
    print("\n" + "=" * 60)
    print("Layout Label Standardization Report")
    if dry_run:
        print("(DRY RUN - no files were modified)")
    print("=" * 60)

    total_detections = 0
    total_lossless = 0
    total_lossy = 0
    total_errors = 0

    for report in reports:
        if report.total_detections > 0 or report.files_with_layout > 0 or report.errors:
            print(f"\n{report.dataset}:")
            print(report.summary())
            total_detections += report.total_detections
            total_lossless += report.conversions_lossless
            total_lossy += report.conversions_lossy
            total_errors += len(report.errors)

    if skipped:
        print(f"\nSkipped ({len(skipped)} datasets, no source schema):")
        for ds_name in skipped:
            print(f"  - {ds_name}")

    print(f"\n{'─' * 60}")
    print(f"Total detections processed:  {total_detections}")
    print(f"Total lossless conversions:  {total_lossless}")
    print(f"Total lossy conversions:     {total_lossy}")
    print(f"Total errors:                {total_errors}")
    print(f"Datasets processed:          {len(reports)}")
    print(f"Datasets skipped:            {len(skipped)}")

    return total_errors


def main() -> int:
    """Run the standardization pipeline.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args()

    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10),
        )

    try:
        from image_preprocessing_detector.schema_utils.layout_taxonomy import (
            LayoutTaxonomy,
        )
    except ImportError as exc:
        log.error(
            "taxonomy_import_failed",
            error=str(exc),
            hint=(
                "The layout_taxonomy module is not yet available. "
                "Ensure taxonomy-agent has completed building "
                "src/.../schema_utils/layout_taxonomy.py"
            ),
        )
        print(
            "ERROR: Cannot import LayoutTaxonomy. "
            "Has the taxonomy module been created yet?",
            file=sys.stderr,
        )
        return 1

    taxonomy = LayoutTaxonomy()

    metadata_dir: Path = args.metadata_dir
    if not metadata_dir.is_dir():
        print(f"ERROR: Metadata directory not found: {metadata_dir}", file=sys.stderr)
        return 1

    dry_run: bool = args.dry_run
    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    targets = _build_targets(args, metadata_dir)

    reports: list[StandardizationReport] = []
    skipped: list[str] = []

    for ds_name, source_schema in targets:
        if source_schema is None:
            log.info(
                "skipping_no_schema",
                dataset=ds_name,
                reason="No source schema could be determined",
            )
            skipped.append(ds_name)
            continue

        log.info(
            "standardizing_dataset",
            dataset=ds_name,
            schema=source_schema,
            dry_run=dry_run,
        )

        report = standardize_dataset(
            metadata_dir=metadata_dir,
            dataset_name=ds_name,
            taxonomy=taxonomy,
            source_schema=source_schema,
            dry_run=dry_run,
        )
        reports.append(report)

    total_errors = _print_standardization_summary(reports, skipped, dry_run)
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
