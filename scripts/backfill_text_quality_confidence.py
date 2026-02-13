"""Backfill text quality confidence into Layer 2 metadata from Docling OCR output.

Computes per-sample text_quality_confidence from Docling OCR JSONL files using
heuristic proxy signals (since Docling's native confidence is always 1.0 for
successful extractions). For datasets with ground truth text, assigns
confidence=1.0 directly.

Heuristic confidence tiers:
  - Hard failure (success=false):           0.0   tier_0_exact
  - Silent failure (success but no text):   0.1   tier_3_heuristic
  - Image-only (<!-- image --> marker):     0.2   tier_3_heuristic
  - Very short text (<50 chars):            0.5   tier_3_heuristic
  - Formula-not-decoded (scaled by ratio):  0.7*  tier_2_model
  - Normal extraction (50+ chars):          0.8   tier_2_model
  - Ground truth text:                      1.0   tier_0_exact

Dataset-level quality cap: If >DATASET_CAP_TRIGGER_PCT% of samples score below
SAMPLE_LOW_QUALITY_THRESHOLD, ALL samples in that dataset have their confidence
capped proportionally to the failure rate.

Usage:
    python scripts/backfill_text_quality_confidence.py --datasets rvl-cdip nist-sd6 --dry-run
    python scripts/backfill_text_quality_confidence.py --datasets funsd --ground-truth
    python scripts/backfill_text_quality_confidence.py --all --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- Confidence heuristic thresholds ---
CONFIDENCE_HARD_FAILURE = 0.0
CONFIDENCE_SILENT_FAILURE = 0.1
CONFIDENCE_IMAGE_ONLY = 0.2
CONFIDENCE_SHORT_TEXT = 0.5
CONFIDENCE_FORMULA_PARTIAL = 0.7
CONFIDENCE_NORMAL_EXTRACTION = 0.8
CONFIDENCE_GROUND_TRUTH = 1.0

SHORT_TEXT_THRESHOLD = 50  # chars
IMAGE_ONLY_MARKER = "<!-- image -->"
FORMULA_MARKER = "<!-- formula-not-decoded -->"

# --- Dataset-level quality cap ---
SAMPLE_LOW_QUALITY_THRESHOLD = 0.5  # samples below this are "low quality"
DATASET_CAP_TRIGGER_PCT = 0.05  # 5% — if >5% of samples are below threshold, apply cap
DATASET_CAP_MINIMUM = 0.5  # floor for the cap value


# --- Datasets with known ground truth text ---
# Migration dict: used to stamp text_source_type into metadata files that
# don't have it yet.  Once stamped, the backfill reads from the metadata
# root directly — so this dict only needs to cover the initial population.
# Source: docs/datasets/DATASET_QUICK_REFERENCE.md "Text" column (GT entries).
_GT_TEXT_MIGRATION: dict[str, str] = {
    # Forms & structured documents
    "funsd": "form_annotations",
    "funsd_plus": "form_annotations",
    "sroie": "receipt_text",
    "nist_sd2": "form_text",
    "nist_sd6": "form_handprint_text",
    "invoices_kg": "invoice_text",
    # Table datasets (cell-level GT)
    "pubtabnet": "cell_text_consolidated",
    "fintabnet": "cell_text_consolidated",
    # Layout datasets (page-level GT)
    "doclaynet": "page_text",
    "financebench": "financial_pdf_text",
    "multimodal_textbook": "textbook_text",
    # Scene text / word-level annotations
    "hiertext": "word_annotations",
    "mlt19": "word_annotations",
    "mle2e": "scene_text",
    "midv500": "id_document_text",
    # Handwriting datasets (iam has no Layer 2 metadata yet, coco-text has no metadata yet)
    "muharaf": "line_transcriptions",
    "pucit_ohul": "line_text",
    # OCR reference / quality datasets
    "ohr_bench": "ocr_reference_text",
    "cc_ocr": "ocr_annotations",
    "ocr_quality": "quality_reference_text",
    "omnidocbench": "multi_task_text",
    "smartdoc_qa": "qa_text",
    # Synthetic / generated (known text content)
    "hindi_ocr_synthetic": "synthetic_text",
    "im2latex": "latex_formulas",
    "mathverse": "math_problem_text",
    # Partial GT (titles/OCR-derived)
    "arabic_docs_ocr": "title_annotations",
    "yarmouk_ocr": "ocr_derived_text",
}


def _lookup_gt_migration(metadata_name: str) -> str | None:
    """Look up GT source from migration dict, trying both naming forms."""
    underscore_name = metadata_name.replace("-", "_")
    return _GT_TEXT_MIGRATION.get(metadata_name) or _GT_TEXT_MIGRATION.get(
        underscore_name
    )


# --- Docling OCR annotation directory mapping ---
# Maps metadata name (underscore) to annotation directory name (hyphen)
DOCLING_ANNOTATION_DIRS: dict[str, str] = {
    "rvl_cdip": "rvl-cdip",
    "nist_sd6": "nist-sd6",
    "nist_sd2": "nist-sd2",
    "diqa_5000": "diqa-5000",
    "smartdoc_qa": "smartdoc-qa",
    "funsd": "funsd",
    "invoices_kg": "invoices-kaggle",
    "mobile_receipts_voxel51": "mobile-receipts-voxel51",
}


def compute_sample_confidence(record: dict[str, Any]) -> tuple[float, str, str]:
    """Compute text quality confidence for a single Docling OCR record.

    Args:
        record: A single parsed JSONL record from Docling OCR output.

    Returns:
        Tuple of (confidence, detection_method, provenance_tier).
    """
    success = record.get("success", False)
    text = record.get("text", "") or ""
    text_stripped = text.strip()

    # Hard failure: Docling reported failure
    if not success:
        return (
            CONFIDENCE_HARD_FAILURE,
            "docling_ocr_failed",
            "tier_0_exact",
        )

    # Silent failure: success=true but empty text
    if len(text_stripped) == 0:
        return (
            CONFIDENCE_SILENT_FAILURE,
            "docling_ocr_empty",
            "tier_3_heuristic",
        )

    # Image-only: Docling could only identify image markers
    if text_stripped == IMAGE_ONLY_MARKER:
        return (
            CONFIDENCE_IMAGE_ONLY,
            "docling_ocr_image_only",
            "tier_3_heuristic",
        )

    # Very short text: likely minimal or degraded extraction
    if len(text_stripped) < SHORT_TEXT_THRESHOLD:
        return (
            CONFIDENCE_SHORT_TEXT,
            "docling_ocr_short",
            "tier_3_heuristic",
        )

    # Check for formula-not-decoded markers
    formula_count = text.count(FORMULA_MARKER)
    if formula_count > 0:
        # Scale confidence by how much content is actual text vs markers
        marker_chars = formula_count * len(FORMULA_MARKER)
        text_ratio = max(0.0, 1.0 - (marker_chars / len(text)))
        # Blend: base formula confidence * text_ratio
        confidence = round(CONFIDENCE_FORMULA_PARTIAL * (0.5 + 0.5 * text_ratio), 3)
        return (
            confidence,
            "docling_ocr_partial_formula",
            "tier_2_model",
        )

    # Normal extraction: reasonable text length, no markers
    return (
        CONFIDENCE_NORMAL_EXTRACTION,
        "docling_ocr",
        "tier_2_model",
    )


def build_docling_index(
    annotation_dir: Path,
) -> dict[str, tuple[float, str, str]]:
    """Build per-sample text quality index from Docling OCR JSONL files.

    Args:
        annotation_dir: Path to the dataset's ocr/ directory containing JSONL files.

    Returns:
        Dict mapping filename_stem to (confidence, method, tier).
    """
    ocr_dir = annotation_dir / "ocr"
    if not ocr_dir.exists():
        return {}

    index: dict[str, tuple[float, str, str]] = {}
    for jsonl_file in sorted(ocr_dir.glob("*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                source = record.get("source", "")
                stem = Path(source).stem
                if stem:
                    index[stem] = compute_sample_confidence(record)

    return index


def compute_dataset_quality_cap(
    confidences: list[float],
    cap_trigger_pct: float = DATASET_CAP_TRIGGER_PCT,
) -> float | None:
    """Compute dataset-level quality cap based on failure rate.

    If the percentage of samples with confidence below SAMPLE_LOW_QUALITY_THRESHOLD
    exceeds cap_trigger_pct, returns a cap value that limits all samples.
    The cap is proportional to the failure rate: higher failure = lower cap.

    Args:
        confidences: List of all per-sample confidence values.
        cap_trigger_pct: Failure rate threshold to trigger cap.

    Returns:
        Cap value (0.5-1.0) if triggered, None if dataset is healthy.
    """
    if not confidences:
        return None

    low_quality_count = sum(1 for c in confidences if c < SAMPLE_LOW_QUALITY_THRESHOLD)
    low_quality_rate = low_quality_count / len(confidences)

    if low_quality_rate <= cap_trigger_pct:
        return None

    # Cap is proportional to failure rate, scaled against the normal extraction
    # confidence. A high failure rate means even "successful" extractions are
    # less trustworthy than they appear.
    # 8.6% failure → 0.8*0.914=0.731, 20% → 0.8*0.8=0.64, 50% → 0.8*0.5=0.4
    multiplier = 1.0 - low_quality_rate
    cap = max(DATASET_CAP_MINIMUM, CONFIDENCE_NORMAL_EXTRACTION * multiplier)
    return round(cap, 3)


def extract_image_id(sample: dict[str, Any]) -> str | None:
    """Extract a matchable image_id from a metadata sample.

    Args:
        sample: A sample dict from the metadata JSON.

    Returns:
        Cleaned image_id string (filename stem), or None.
    """
    source = sample.get("source", {})
    original_filename = source.get("original_filename")
    if original_filename:
        return Path(str(original_filename)).stem

    original_path = source.get("original_path")
    if original_path:
        return Path(str(original_path)).stem

    for key in ("image_id", "filename"):
        value = sample.get(key)
        if value:
            return Path(str(value)).stem

    immutable = sample.get("immutable", {})
    for key in ("original_filename", "image_id"):
        value = immutable.get(key)
        if value:
            return Path(str(value)).stem

    return None


def process_ground_truth_dataset(
    dataset_name: str,
    metadata_path: Path,
    gt_source: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Process a ground truth text dataset: assign confidence=1.0.

    Args:
        dataset_name: Canonical dataset name.
        metadata_path: Path to the metadata JSON file.
        gt_source: Description of the ground truth source.
        dry_run: If True, report without writing.

    Returns:
        Stats dict.
    """
    stats: dict[str, int] = {
        "total": 0,
        "ground_truth": 0,
        "already_has_confidence": 0,
        "no_enrichment": 0,
    }

    with open(metadata_path) as f:
        metadata = json.load(f)

    samples = metadata.get("samples", [])
    stats["total"] = len(samples)

    for sample in samples:
        enrichments = sample.get("enrichments", {})
        versions = enrichments.get("versions", [])
        if not versions:
            stats["no_enrichment"] += 1
            continue

        data = versions[0].get("data", {})

        if data.get("text_quality_confidence") is not None:
            stats["already_has_confidence"] += 1
            continue

        data["text_quality_confidence"] = CONFIDENCE_GROUND_TRUTH
        data["text_quality_method"] = f"ground_truth_{gt_source}"
        data["text_quality_provenance_tier"] = "tier_0_exact"
        data["text_quality_is_soft_label"] = False
        stats["ground_truth"] += 1

    if not dry_run:
        metadata.setdefault("backfill_history", [])
        metadata["backfill_history"].append(
            {
                "operation": "text_quality_confidence_backfill",
                "timestamp": datetime.now(UTC).isoformat(),
                "source": f"ground_truth_{gt_source}",
                "stats": stats,
            }
        )
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"  Written: {metadata_path}")
    else:
        logger.info(f"  DRY RUN: would write {metadata_path}")

    return stats


def process_docling_dataset(
    dataset_name: str,
    metadata_path: Path,
    annotation_dir: Path,
    dry_run: bool = False,
    cap_trigger_pct: float = DATASET_CAP_TRIGGER_PCT,
) -> dict[str, int]:
    """Process a dataset with Docling OCR: compute heuristic text quality.

    Two-pass approach:
      1. Compute per-sample confidence from Docling JSONL signals
      2. Apply dataset-level quality cap if failure rate exceeds threshold

    Args:
        dataset_name: Canonical dataset name.
        metadata_path: Path to the metadata JSON file.
        annotation_dir: Path to annotations/{dataset}/ directory.
        dry_run: If True, report without writing.

    Returns:
        Stats dict.
    """
    stats: dict[str, int] = {
        "total": 0,
        "matched": 0,
        "unmatched": 0,
        "already_has_confidence": 0,
        "no_enrichment": 0,
        "hard_failure": 0,
        "silent_failure": 0,
        "image_only": 0,
        "short_text": 0,
        "formula_partial": 0,
        "normal": 0,
        "cap_applied": 0,
    }

    # Build Docling index
    docling_index = build_docling_index(annotation_dir)
    logger.info(f"  Docling index: {len(docling_index)} records")
    if not docling_index:
        logger.warning(f"  No Docling OCR data found in {annotation_dir}/ocr/")
        return stats

    # Load metadata
    with open(metadata_path) as f:
        metadata = json.load(f)

    samples = metadata.get("samples", [])
    stats["total"] = len(samples)

    # --- Pass 1: Compute per-sample confidence ---
    sample_confidences: list[tuple[int, float]] = []  # (sample_idx, confidence)

    for idx, sample in enumerate(samples):
        enrichments = sample.get("enrichments", {})
        versions = enrichments.get("versions", [])
        if not versions:
            stats["no_enrichment"] += 1
            continue

        data = versions[0].get("data", {})

        if data.get("text_quality_confidence") is not None:
            stats["already_has_confidence"] += 1
            continue

        image_id = extract_image_id(sample)
        docling_result = docling_index.get(image_id) if image_id else None

        if docling_result is None:
            stats["unmatched"] += 1
            continue

        confidence, method, tier = docling_result
        stats["matched"] += 1

        # Count by category
        if confidence <= CONFIDENCE_HARD_FAILURE:
            stats["hard_failure"] += 1
        elif confidence <= CONFIDENCE_SILENT_FAILURE:
            stats["silent_failure"] += 1
        elif confidence <= CONFIDENCE_IMAGE_ONLY:
            stats["image_only"] += 1
        elif confidence <= CONFIDENCE_SHORT_TEXT:
            stats["short_text"] += 1
        elif method == "docling_ocr_partial_formula":
            stats["formula_partial"] += 1
        else:
            stats["normal"] += 1

        # Store pre-cap confidence for cap computation
        sample_confidences.append((idx, confidence))

        # Write initial values (may be capped in pass 2)
        data["text_quality_confidence"] = confidence
        data["text_quality_method"] = method
        data["text_quality_provenance_tier"] = tier
        data["text_quality_is_soft_label"] = tier != "tier_0_exact"

    # --- Pass 2: Dataset-level quality cap ---
    all_confidences = [c for _, c in sample_confidences]
    cap = compute_dataset_quality_cap(all_confidences, cap_trigger_pct)

    if cap is not None:
        low_count = sum(1 for c in all_confidences if c < SAMPLE_LOW_QUALITY_THRESHOLD)
        low_rate = low_count / len(all_confidences) if all_confidences else 0
        logger.info(
            f"  Dataset quality cap triggered: {low_count}/{len(all_confidences)} "
            f"({low_rate:.1%}) samples below {SAMPLE_LOW_QUALITY_THRESHOLD} → "
            f"capping all at {cap}"
        )

        for idx, original_confidence in sample_confidences:
            data = samples[idx]["enrichments"]["versions"][0]["data"]
            current = data.get("text_quality_confidence")
            if current is not None and current > cap:
                data["text_quality_confidence"] = cap
                data["text_quality_dataset_cap"] = cap
                data["text_quality_dataset_cap_reason"] = (
                    f"{low_rate:.1%} samples below {SAMPLE_LOW_QUALITY_THRESHOLD}"
                )
                stats["cap_applied"] += 1
    else:
        logger.info("  No dataset quality cap needed")

    # Write updated metadata
    if not dry_run:
        metadata.setdefault("backfill_history", [])
        metadata["backfill_history"].append(
            {
                "operation": "text_quality_confidence_backfill",
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "docling_ocr_heuristic",
                "dataset_quality_cap": cap,
                "stats": stats,
            }
        )
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"  Written: {metadata_path}")
    else:
        logger.info(f"  DRY RUN: would write {metadata_path}")

    return stats


def _resolve_metadata_path(
    dataset_name: str,
    metadata_dir: Path,
) -> Path | None:
    """Resolve metadata file path trying both naming conventions.

    Tries original name, then hyphen-to-underscore, then underscore-to-hyphen.

    Args:
        dataset_name: Dataset name (hyphen or underscore form).
        metadata_dir: Directory containing metadata JSON files.

    Returns:
        Path to the metadata file, or None if not found.
    """
    candidates = [
        dataset_name,
        dataset_name.replace("-", "_"),
        dataset_name.replace("_", "-"),
    ]
    for name in candidates:
        metadata_path = metadata_dir / f"{name}_metadata.json"
        if metadata_path.exists():
            return metadata_path
    return None


def stamp_text_source_type(
    metadata_path: Path,
    dry_run: bool = False,
) -> tuple[str | None, str | None]:
    """Read text_source_type from metadata root, stamping from migration dict if absent.

    Checks the metadata JSON root for ``text_source_type`` (enum:
    ``ground_truth``, ``model_extracted``, ``synthetic``, ``partial_ground_truth``,
    ``none``) and ``ground_truth_text_source`` (descriptive string).  If the
    fields are missing, looks up the migration dict and writes them into the
    metadata file so future runs auto-detect without the dict.

    Args:
        metadata_path: Path to the dataset metadata JSON.
        dry_run: If True, don't write.

    Returns:
        (text_source_type, ground_truth_text_source) or (None, None).
    """
    metadata_name = metadata_path.stem.replace("_metadata", "")

    with open(metadata_path) as f:
        metadata = json.load(f)

    existing_type = metadata.get("text_source_type")
    existing_source = metadata.get("ground_truth_text_source")

    if existing_type is not None:
        return (existing_type, existing_source)

    # Not stamped yet — check the migration dict
    gt_source = _lookup_gt_migration(metadata_name)
    if gt_source is None:
        return (None, None)

    # Determine type: most are ground_truth, a couple are partial
    partial_datasets = {"arabic_docs_ocr", "yarmouk_ocr"}
    underscore_name = metadata_name.replace("-", "_")
    if underscore_name in partial_datasets:
        source_type = "partial_ground_truth"
    elif "synthetic" in gt_source:
        source_type = "synthetic"
    else:
        source_type = "ground_truth"

    metadata["text_source_type"] = source_type
    metadata["ground_truth_text_source"] = gt_source
    logger.info(f"  Stamping text_source_type={source_type}, gt_source={gt_source}")

    if not dry_run:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    return (source_type, gt_source)


def process_dataset(
    dataset_name: str,
    metadata_dir: Path,
    annotation_base: Path,
    ground_truth: bool = False,
    dry_run: bool = False,
    cap_trigger_pct: float = DATASET_CAP_TRIGGER_PCT,
) -> dict[str, int]:
    """Process a single dataset for text quality confidence.

    GT detection priority:
      1. ``text_source_type`` field already in metadata root (auto-detect)
      2. ``--ground-truth`` CLI flag (user override)
      3. Migration dict ``_GT_TEXT_MIGRATION`` (stamps metadata for future runs)
      4. Docling OCR heuristic fallback

    Args:
        dataset_name: Canonical dataset name (hyphen or underscore).
        metadata_dir: Directory containing metadata JSON files.
        annotation_base: Base directory for annotations.
        ground_truth: If True, force ground truth assignment.
        dry_run: If True, report without writing.
        cap_trigger_pct: Failure rate threshold for dataset cap.

    Returns:
        Stats dict.
    """
    metadata_path = _resolve_metadata_path(dataset_name, metadata_dir)
    if metadata_path is None:
        logger.warning(f"No metadata file for {dataset_name}")
        return {"total": 0}
    metadata_name = metadata_path.stem.replace("_metadata", "")

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Processing: {dataset_name}")

    # --- GT detection: read from metadata root or migrate from dict ---
    source_type, gt_source = stamp_text_source_type(metadata_path, dry_run)

    if ground_truth or source_type in (
        "ground_truth",
        "synthetic",
        "partial_ground_truth",
    ):
        source = gt_source or "user_specified"
        logger.info(f"  Mode: ground truth ({source}, type={source_type})")
        return process_ground_truth_dataset(
            dataset_name, metadata_path, source, dry_run
        )

    # --- Docling OCR fallback ---
    underscore_name = metadata_name.replace("-", "_")
    anno_dir_name = (
        DOCLING_ANNOTATION_DIRS.get(metadata_name)
        or DOCLING_ANNOTATION_DIRS.get(underscore_name)
        or dataset_name
    )
    annotation_dir = annotation_base / anno_dir_name
    if (annotation_dir / "ocr").exists():
        logger.info(f"  Mode: Docling OCR heuristic ({annotation_dir}/ocr/)")
        return process_docling_dataset(
            dataset_name, metadata_path, annotation_dir, dry_run, cap_trigger_pct
        )

    logger.warning(
        f"  No text source found for {dataset_name} "
        f"(text_source_type={source_type}, no Docling OCR at {annotation_dir}/ocr/)"
    )
    return {"total": 0}


def main() -> None:
    """Run the text quality confidence backfill."""
    parser = argparse.ArgumentParser(
        description="Backfill text quality confidence into Layer 2 metadata"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        help="Dataset names to process",
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/metadata_registry/json"),
        help="Directory containing metadata JSON files",
    )
    parser.add_argument(
        "--annotation-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/annotations"),
        help="Base directory for annotation data",
    )
    parser.add_argument(
        "--ground-truth",
        action="store_true",
        help="Force ground truth assignment (confidence=1.0) for specified datasets",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all datasets with metadata files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    parser.add_argument(
        "--cap-trigger-pct",
        type=float,
        default=DATASET_CAP_TRIGGER_PCT,
        help=f"Failure rate threshold to trigger dataset cap (default: {DATASET_CAP_TRIGGER_PCT})",
    )

    args = parser.parse_args()

    cap_trigger_pct = args.cap_trigger_pct

    if args.all:
        # Find all metadata files
        datasets = []
        for mf in sorted(args.metadata_dir.glob("*_metadata.json")):
            name = mf.stem.replace("_metadata", "")
            datasets.append(name)
    elif args.datasets:
        datasets = list(
            args.datasets
        )  # pass as-is; _resolve_metadata_path handles naming
    else:
        print("Specify --datasets or --all", file=sys.stderr)
        sys.exit(1)

    logger.info(f"Processing {len(datasets)} datasets")
    if args.dry_run:
        logger.info("DRY RUN MODE — no files will be written")

    total_stats: dict[str, int] = {}

    for dataset_name in datasets:
        stats = process_dataset(
            dataset_name,
            args.metadata_dir,
            args.annotation_dir,
            ground_truth=args.ground_truth,
            dry_run=args.dry_run,
            cap_trigger_pct=cap_trigger_pct,
        )

        for key, value in stats.items():
            total_stats[key] = total_stats.get(key, 0) + value

        # Per-dataset summary
        logger.info(f"  Stats: {stats}")

    # Final summary
    print(f"\n{'=' * 60}")
    print("TEXT QUALITY CONFIDENCE BACKFILL SUMMARY")
    print("=" * 60)
    for key in sorted(total_stats):
        print(f"  {key:30s} {total_stats[key]:>8,}")


if __name__ == "__main__":
    main()
