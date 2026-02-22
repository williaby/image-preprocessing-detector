#!/usr/bin/env python3
"""Migrate Layer 2 metadata from flat field format to full nested object schema.

This script converts existing Layer 2 metadata files from the legacy flat field
format to the full nested object format matching the Layer 2 enrichment schema.

The migration handles the following conversions:
- capture_method (string) → capture_method (object)
- resolution_* flat fields → resolution (object)
- domain_* flat fields → domain (object)
- text_scope (string) → text_scope (object)
- has_* booleans + content_flags_* → content_flags (object)
- iso639_language/iso15924_script → language (object)
- Creates placeholder objects for: structure, quality, llm_scores

Usage:
    # Migrate all datasets
    python scripts/migrate_layer2_schema_to_full.py \\
        --input-dir /mnt/e/image_detection/metadata_registry/json \\
        --backup-dir /mnt/e/image_detection/metadata_registry/json_backup_20250131 \\
        --output-dir /mnt/e/image_detection/metadata_registry/json \\
        --validate --verbose

    # Dry-run on single dataset
    python scripts/migrate_layer2_schema_to_full.py \\
        --dataset fintabnet \\
        --input-dir /mnt/e/image_detection/metadata_registry/json \\
        --dry-run --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

# Optional JSON schema validation
try:
    from jsonschema import Draft7Validator, ValidationError

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    Draft7Validator = None
    ValidationError = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Script version for provenance tracking
SCRIPT_VERSION = "1.1.0"
MIGRATION_FORMAT_VERSION = "full_nested_v2.3"

# Mapping for script_family normalization
# Some legacy data uses "ltr" which should map to "latin"
SCRIPT_FAMILY_MAPPING = {
    "ltr": "latin",
    "rtl": "arabic",
    "latin": "latin",
    "cjk": "cjk",
    "arabic": "arabic",
    "indic": "indic",
    "cyrillic": "cyrillic",
    "other": "other",
}

# RTL scripts for is_rtl detection
RTL_SCRIPTS = {"Arab", "Hebr", "Syrc", "Thaa", "Nkoo"}


def migrate_capture_method(flat_data: dict[str, Any]) -> dict[str, Any] | None:
    """Migrate capture_method from string to object format.

    Args:
        flat_data: Flat enrichment data

    Returns:
        Nested capture_method object or None if no data
    """
    if "capture_method" not in flat_data:
        return None

    return {
        "method": flat_data["capture_method"],
        "confidence": flat_data.get("capture_confidence", 0.5),
        "detection_method": flat_data.get("capture_detection_method", "unknown"),
    }


def migrate_resolution(flat_data: dict[str, Any]) -> dict[str, Any] | None:
    """Migrate resolution flat fields to object format.

    Args:
        flat_data: Flat enrichment data

    Returns:
        Nested resolution object or None if no data
    """
    has_resolution = any(
        k in flat_data
        for k in ["resolution_dpi", "resolution_category", "resolution_pixels"]
    )
    if not has_resolution:
        return None

    return {
        "dpi": flat_data.get("resolution_dpi"),
        "category": flat_data.get("resolution_category"),
        "pixels": flat_data.get("resolution_pixels"),
    }


def migrate_domain(flat_data: dict[str, Any]) -> dict[str, Any] | None:
    """Migrate domain flat fields to object format.

    Args:
        flat_data: Flat enrichment data

    Returns:
        Nested domain object or None if no data
    """
    if "domain_level1" not in flat_data:
        return None

    level1 = flat_data["domain_level1"]
    # Default confidence: 0.3 for UNK, 0.8 for classified domains
    default_confidence = 0.3 if level1 == "UNK" else 0.8

    return {
        "level1": level1,
        "level2": flat_data.get("domain_level2"),
        "level3": flat_data.get("domain_level3"),
        "confidence": flat_data.get("domain_confidence", default_confidence),
    }


def migrate_structure(flat_data: dict[str, Any]) -> dict[str, Any]:
    """Create structure object (placeholder or from existing data).

    Args:
        flat_data: Flat enrichment data

    Returns:
        Structure object with available data or null placeholders
    """
    result: dict[str, Any] = {
        "text_density": flat_data.get("text_density"),
        "layout_type": flat_data.get("layout_type"),
        "element_types": flat_data.get("element_types", []),
    }
    # v2.3.0: text_directions_present (defaults to null for pre-v2.3 data)
    if "text_directions_present" in flat_data:
        result["text_directions_present"] = flat_data["text_directions_present"]
    return result


def migrate_quality(flat_data: dict[str, Any]) -> dict[str, Any]:
    """Create quality object (placeholder or from existing data).

    Args:
        flat_data: Flat enrichment data

    Returns:
        Quality object with available data or null placeholders
    """
    return {
        "overall_score": flat_data.get("overall_score"),
        "degradations": flat_data.get("degradations", []),
    }


def normalize_script_family(raw_value: str | None) -> str | None:
    """Normalize script_family values.

    Handles legacy values like "ltr" → "latin".

    Args:
        raw_value: Raw script_family value from flat data

    Returns:
        Normalized script_family or None
    """
    if raw_value is None:
        return None
    return SCRIPT_FAMILY_MAPPING.get(raw_value.lower(), raw_value.lower())


def migrate_language(flat_data: dict[str, Any]) -> dict[str, Any]:
    """Create language object from flat fields.

    Handles both naming conventions:
    - iso639_language / iso15924_script (legacy)
    - language_code / script_code (newer)

    Args:
        flat_data: Flat enrichment data

    Returns:
        Language object with available data or null placeholders
    """
    # Try both naming conventions
    language_code = flat_data.get("iso639_language") or flat_data.get("language_code")
    script_code = flat_data.get("iso15924_script") or flat_data.get("script_code")

    # Determine script_family
    raw_script_family = flat_data.get("script_family")
    script_family = normalize_script_family(raw_script_family)

    # Determine is_rtl based on script_code
    is_rtl = script_code in RTL_SCRIPTS if script_code else False

    # Build BCP47 tag if we have the components
    bcp47_tag = flat_data.get("bcp47_tag")
    if bcp47_tag is None and language_code and script_code:
        bcp47_tag = f"{language_code}-{script_code}"

    result = {
        "language_code": language_code,
        "script_code": script_code,
        "bcp47_tag": bcp47_tag,
        "script_family": script_family,
        "confidence": flat_data.get("language_confidence"),
        "detection_method": flat_data.get("language_detection_method"),
        "is_rtl": flat_data.get("is_rtl", is_rtl),
        "is_primary": flat_data.get("is_primary", True),
    }
    # v2.3.0: text_direction (defaults to null for pre-v2.3 data)
    if "text_direction" in flat_data:
        result["text_direction"] = flat_data["text_direction"]
    return result


def migrate_text_scope(flat_data: dict[str, Any]) -> dict[str, Any] | None:
    """Migrate text_scope from string to object format.

    Args:
        flat_data: Flat enrichment data

    Returns:
        Nested text_scope object or None if no data
    """
    if "text_scope" not in flat_data:
        return None

    # Handle case where text_scope might already be an object
    raw_scope = flat_data["text_scope"]
    if isinstance(raw_scope, dict):
        scope = raw_scope.get("scope")
    else:
        scope = raw_scope

    return {
        "scope": scope,
        "content_type": flat_data.get("text_scope_content_type")
        or flat_data.get("content_type"),
        "density": flat_data.get("text_density_scope"),
        "estimated_chars": flat_data.get("estimated_chars"),
        "estimated_words": flat_data.get("estimated_words"),
        "confidence": flat_data.get("text_scope_confidence"),
        "detection_method": flat_data.get("text_scope_detection_method"),
    }


def migrate_content_flags(flat_data: dict[str, Any]) -> dict[str, Any]:
    """Migrate content flag booleans to object format.

    Args:
        flat_data: Flat enrichment data

    Returns:
        Content flags object
    """
    return {
        "has_table": flat_data.get("has_table", False),
        "has_formula": flat_data.get("has_formula", False),
        "has_handwriting": flat_data.get("has_handwriting", False),
        "has_signature": flat_data.get("has_signature", False),
        "has_figure": flat_data.get("has_figure", False),
        "tier": flat_data.get("content_flags_tier"),
        "source": flat_data.get("content_flags_source"),
    }


def migrate_sample_data(flat_data: dict[str, Any]) -> dict[str, Any]:
    """Convert flat field format to full nested schema format.

    Args:
        flat_data: Sample enrichment data in flat format

    Returns:
        Migrated data in full nested object format
    """
    nested_data: dict[str, Any] = {}

    # 1. Migrate capture_method (string → object)
    capture_method = migrate_capture_method(flat_data)
    if capture_method:
        nested_data["capture_method"] = capture_method

    # 2. Migrate resolution (flat → object)
    resolution = migrate_resolution(flat_data)
    if resolution:
        # v2.3.0: character_height_rendered_px and output_size_px
        if "character_height_rendered_px" in flat_data:
            resolution["character_height_rendered_px"] = flat_data[
                "character_height_rendered_px"
            ]
        if "output_size_px" in flat_data:
            resolution["output_size_px"] = flat_data["output_size_px"]
        nested_data["resolution"] = resolution

    # 3. Migrate domain (flat → object)
    domain = migrate_domain(flat_data)
    if domain:
        nested_data["domain"] = domain

    # 4. Create structure placeholder (NEW)
    nested_data["structure"] = migrate_structure(flat_data)

    # 5. Create quality placeholder (NEW)
    nested_data["quality"] = migrate_quality(flat_data)

    # 6. Create language object (NEW)
    nested_data["language"] = migrate_language(flat_data)

    # 7. Migrate text_scope (string → object)
    text_scope = migrate_text_scope(flat_data)
    if text_scope:
        nested_data["text_scope"] = text_scope

    # 8. Migrate content_flags (flat booleans → object)
    nested_data["content_flags"] = migrate_content_flags(flat_data)

    # 9. Create llm_scores placeholder
    nested_data["llm_scores"] = flat_data.get("llm_scores")  # Usually null

    # 10. Preserve layout_detections as-is
    if "layout_detections" in flat_data:
        nested_data["layout_detections"] = flat_data["layout_detections"]

    return nested_data


def is_already_migrated(data: dict[str, Any]) -> bool:
    """Check if enrichment data is already in nested format.

    Args:
        data: Enrichment data dict

    Returns:
        True if already migrated (has nested capture_method object)
    """
    capture_method = data.get("capture_method")
    if isinstance(capture_method, dict) and "method" in capture_method:
        return True
    return False


def load_json_schema(schema_path: Path) -> dict[str, Any] | None:
    """Load JSON schema for validation.

    Args:
        schema_path: Path to JSON schema file

    Returns:
        Schema dict or None if not found/invalid
    """
    if not schema_path.exists():
        logger.warning(f"Schema file not found: {schema_path}")
        return None

    try:
        with open(schema_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON schema: {e}")
        return None


def validate_enrichment_data(
    data: dict[str, Any],
    validator: Draft7Validator | None,
) -> list[str]:
    """Validate enrichment data against schema.

    Args:
        data: Enrichment data to validate
        validator: JSON schema validator instance

    Returns:
        List of validation error messages (empty if valid)
    """
    if validator is None:
        return []

    errors = []
    for error in validator.iter_errors(data):
        errors.append(f"{error.json_path}: {error.message}")
    return errors


def _make_skipped_result(dataset_name: str, reason: str) -> dict[str, Any]:
    """Create a result dict for a skipped/error dataset."""
    return {
        "dataset": dataset_name,
        "status": "skipped",
        "reason": reason,
        "samples_total": 0,
        "samples_migrated": 0,
        "samples_already_migrated": 0,
        "errors": [],
    }


def _load_dataset_metadata(input_file: Path) -> dict[str, Any] | str:
    """Load dataset metadata from JSON file.

    Returns:
        The parsed metadata dict, or an error string on failure.
    """
    try:
        with open(input_file) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return str(e)
    except OSError as e:
        return f"File error: {e}"


def _migrate_sample_versions(
    sample: dict[str, Any],
    idx: int,
    schema_validator: Draft7Validator | None,
    validation_errors: list[str],
) -> int:
    """Migrate all enrichment versions in a single sample.

    Returns:
        Count of already-migrated versions encountered.
    """
    already_migrated = 0
    enrichments = sample.get("enrichments", {})
    versions = enrichments.get("versions", [])

    for version in versions:
        flat_data = version.get("data", {})
        if is_already_migrated(flat_data):
            already_migrated += 1
            continue

        nested_data = migrate_sample_data(flat_data)

        if schema_validator:
            ver_errors = validate_enrichment_data(nested_data, schema_validator)
            if ver_errors:
                validation_errors.extend([f"Sample {idx}: {e}" for e in ver_errors])

        version["data"] = nested_data

    return already_migrated


def _determine_migration_status(
    errors: list[dict[str, Any]],
    total_samples: int,
) -> str:
    """Determine overall migration status from error count."""
    if len(errors) == total_samples and total_samples > 0:
        return "failed"
    if errors:
        return "partial"
    return "success"


def migrate_dataset(
    dataset_name: str,
    input_dir: Path,
    output_dir: Path,
    backup_dir: Path | None = None,
    schema_validator: Draft7Validator | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Migrate a single dataset from flat to nested schema.

    Args:
        dataset_name: Canonical dataset name
        input_dir: Directory with original metadata files
        output_dir: Directory for migrated metadata files
        backup_dir: Optional backup directory
        schema_validator: Optional JSON schema validator
        dry_run: Don't write files, just report
        verbose: Print detailed progress

    Returns:
        Migration statistics dict
    """
    input_file = input_dir / f"{dataset_name}_metadata.json"

    if not input_file.exists():
        return _make_skipped_result(dataset_name, "No metadata file found")

    if verbose:
        logger.info(f"Loading {input_file}...")

    loaded = _load_dataset_metadata(input_file)
    if isinstance(loaded, str):
        result = _make_skipped_result(dataset_name, f"Invalid JSON: {loaded}")
        result["status"] = "error"
        result["errors"] = [loaded]
        return result
    dataset_metadata = loaded

    samples = dataset_metadata.get("samples", [])

    if verbose:
        original_sample_count = dataset_metadata.get("sample_count", 0)
        logger.info(f"Found {len(samples)} samples (declared: {original_sample_count})")

    # Backup if requested
    if backup_dir and not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"{dataset_name}_metadata.json"
        with open(backup_file, "w") as f:
            json.dump(dataset_metadata, f, indent=2)
        if verbose:
            logger.info(f"Backed up to {backup_file}")

    # Migrate each sample
    migrated_samples = []
    already_migrated = 0
    errors: list[dict[str, Any]] = []
    validation_errors: list[str] = []

    for idx, sample in enumerate(samples):
        try:
            already_migrated += _migrate_sample_versions(
                sample,
                idx,
                schema_validator,
                validation_errors,
            )
            migrated_samples.append(sample)

            if verbose and (idx + 1) % 10000 == 0:
                logger.info(f"  Processed {idx + 1}/{len(samples)} samples...")
        except Exception as e:
            errors.append(
                {
                    "sample_index": idx,
                    "sample_id": sample.get("id", "unknown"),
                    "error": str(e),
                }
            )
            if verbose:
                logger.warning(f"Error migrating sample {idx}: {e}")
            migrated_samples.append(sample)

    # Update dataset metadata
    dataset_metadata["samples"] = migrated_samples
    dataset_metadata["migration"] = {
        "migrated_at": datetime.now(UTC).isoformat(),
        "migration_script": f"migrate_layer2_schema_to_full.py_v{SCRIPT_VERSION}",
        "format_version": MIGRATION_FORMAT_VERSION,
        "samples_processed": len(migrated_samples),
        "samples_already_migrated": already_migrated,
        "errors_count": len(errors),
        "validation_errors_count": len(validation_errors),
    }

    if not dry_run:
        output_file = output_dir / f"{dataset_name}_metadata.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(dataset_metadata, f, indent=2)
        if verbose:
            logger.info(f"Wrote migrated data to {output_file}")

    return {
        "dataset": dataset_name,
        "status": _determine_migration_status(errors, len(samples)),
        "samples_total": len(samples),
        "samples_migrated": len(migrated_samples) - already_migrated,
        "samples_already_migrated": already_migrated,
        "errors": errors,
        "validation_errors": validation_errors[:10],
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for migration."""
    parser = argparse.ArgumentParser(
        description="Migrate Layer 2 metadata from flat to full nested schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        help="Migrate single dataset (canonical name, e.g., 'fintabnet')",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Input directory with flat format metadata files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for migrated metadata files",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Backup directory for original files (recommended)",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=Path("docs/schema/layer2_enrichment.schema.json"),
        help="Path to JSON schema for validation",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate migrated data against JSON schema",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write files, just report what would be done",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print detailed progress"
    )
    return parser


def _load_schema_validator(schema_path: Path) -> Draft7Validator | None:
    """Load and return a JSON schema validator, or None on failure."""
    if not HAS_JSONSCHEMA:
        logger.error("jsonschema package required for validation. Install with:")
        logger.error("  uv pip install jsonschema")
        return None

    schema = load_json_schema(schema_path)
    if not schema:
        return None

    enrichment_data_schema = schema.get("$defs", {}).get("EnrichmentData", {})
    if not enrichment_data_schema:
        logger.warning("EnrichmentData schema not found, skipping validation")
        return None

    logger.info(f"Loaded schema from {schema_path}")
    return Draft7Validator(enrichment_data_schema)


def _discover_migration_datasets(args: argparse.Namespace) -> list[str]:
    """Discover datasets to migrate from CLI args or directory listing."""
    if args.dataset:
        return [args.dataset]
    metadata_files = list(args.input_dir.glob("*_metadata.json"))
    return sorted(f.stem.removesuffix("_metadata") for f in metadata_files)


def _build_migration_report(
    results: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    """Aggregate per-dataset results into a migration report."""
    now = datetime.now(UTC)
    return {
        "migration_date": now.strftime("%Y-%m-%d"),
        "migration_timestamp": now.isoformat(),
        "script_version": SCRIPT_VERSION,
        "format_version": MIGRATION_FORMAT_VERSION,
        "dry_run": dry_run,
        "total_datasets": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "partial": sum(1 for r in results if r["status"] == "partial"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "failed": sum(1 for r in results if r["status"] in ("error", "failed")),
        "total_samples_migrated": sum(r.get("samples_migrated", 0) for r in results),
        "total_samples_already_migrated": sum(
            r.get("samples_already_migrated", 0) for r in results
        ),
        "results": results,
    }


def _print_migration_summary(
    report: dict[str, Any],
    report_file: Path,
    backup_dir: Path | None,
    dry_run: bool,
) -> None:
    """Print the final migration summary to stdout."""
    print(f"\n{'=' * 60}")
    print("MIGRATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total datasets:     {report['total_datasets']}")
    print(f"  Successful:       {report['successful']}")
    print(f"  Partial:          {report['partial']}")
    print(f"  Skipped:          {report['skipped']}")
    print(f"  Failed:           {report['failed']}")
    print(f"Total samples migrated:         {report['total_samples_migrated']}")
    print(f"Total samples already migrated: {report['total_samples_already_migrated']}")
    print(f"Report: {report_file}")
    if backup_dir:
        print(f"Backup: {backup_dir}")
    if dry_run:
        print("\n[DRY RUN] No files were modified.")


def main() -> int:
    """Main migration function.

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    args = _build_arg_parser().parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    schema_validator = None
    if args.validate:
        schema_validator = _load_schema_validator(args.schema_path)
        if schema_validator is None:
            logger.error(
                "Schema validation requested but validator could not be loaded. "
                "Ensure jsonschema is installed and schema path is valid."
            )
            return 1

    datasets = _discover_migration_datasets(args)
    if not datasets:
        logger.error(f"No metadata files found in {args.input_dir}")
        return 1

    logger.info(f"Found {len(datasets)} datasets to migrate")
    if args.dry_run:
        logger.info("DRY RUN - no files will be modified")

    _status_labels = {
        "success": "OK",
        "partial": "WARN",
        "skipped": "SKIP",
        "error": "ERR",
        "failed": "FAIL",
    }

    results = []
    for dataset_name in datasets:
        if args.verbose:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Migrating: {dataset_name}")
            logger.info(f"{'=' * 60}")

        result = migrate_dataset(
            dataset_name=dataset_name,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            backup_dir=args.backup_dir,
            schema_validator=schema_validator,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        results.append(result)

        label = _status_labels.get(result["status"], "?")
        logger.info(
            f"[{label}] {dataset_name}: "
            f"{result['samples_migrated']} migrated, "
            f"{result['samples_already_migrated']} already done, "
            f"{len(result.get('errors', []))} errors"
        )

    report = _build_migration_report(results, args.dry_run)

    report_date = datetime.now(UTC).strftime("%Y%m%d")
    report_file = Path("metadata_registry") / f"migration_report_{report_date}.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    if not args.dry_run:
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report written to: {report_file}")

    _print_migration_summary(report, report_file, args.backup_dir, args.dry_run)

    return 1 if report["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
