"""Materialize sample_reliability_summary into Layer 2 metadata JSON files.

Computes a per-sample composite reliability summary from all enrichment fields
and writes it directly into each sample's enrichment data. Also computes
dataset-level bottleneck statistics and optionally updates the per-dataset
documentation in docs/datasets/source/.

Key semantic difference from analyze_soft_labels.py:
  - Missing/unpopulated fields get confidence=0.0 (not null). This ensures the
    composite reflects the true usability of each sample for training. A sample
    missing language data is penalized, not ignored.

Usage:
    python scripts/materialize_reliability_summary.py --all --dry-run
    python scripts/materialize_reliability_summary.py --datasets funsd sroie
    python scripts/materialize_reliability_summary.py --all --update-docs
    python scripts/materialize_reliability_summary.py --all
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- Threshold configuration (mirrors analyze_soft_labels.py) ---
HARD_LABEL_THRESHOLD = 0.9
SOFT_LABEL_THRESHOLD = 0.7
ACTIVE_LEARNING_THRESHOLD = 0.5

# --- Provenance tier ranking (higher = more reliable) ---
TIER_RANK: dict[str, int] = {
    "tier_0_exact": 3,
    "tier_1_annotation": 2,
    "tier_2_model": 1,
    "tier_3_heuristic": 0,
}

# All enrichment fields that contribute to the composite
ALL_FIELDS = [
    "capture_method",
    "resolution",
    "domain",
    "language",
    "text_quality",
    "has_table",
    "has_formula",
    "has_handwriting",
    "has_figure",
    "layout_detections",
]

# Source strings indicating ground truth
GROUND_TRUTH_SOURCES: set[str] = {
    "coco_annotation",
    "dataset_config",
    "dataset_metadata",
    "manual",
    "ground_truth",
    "pdf_metadata",
}


def classify_confidence(confidence: float | None) -> str:
    """Classify a confidence value into a training label category."""
    if confidence is None:
        return "unassessed"
    if confidence >= HARD_LABEL_THRESHOLD:
        return "hard_label"
    if confidence >= SOFT_LABEL_THRESHOLD:
        return "soft_label"
    if confidence >= ACTIVE_LEARNING_THRESHOLD:
        return "active_learning"
    return "unreliable"


@dataclass(frozen=True)
class FieldAssessment:
    """Reliability assessment for a single enrichment field."""

    field_name: str
    confidence: float  # 0.0 for missing fields, never None in materialization
    provenance_tier: str
    is_soft_label: bool
    category: str  # hard_label, soft_label, active_learning, unreliable
    populated: bool  # True if field had data, False if defaulted to 0.0


@dataclass(frozen=True)
class DatasetBottleneck:
    """A field that is the primary bottleneck across samples in a dataset."""

    field_name: str
    bottleneck_count: int
    bottleneck_pct: float
    avg_confidence: float


def assess_capture_method(data: dict[str, Any]) -> FieldAssessment:
    """Assess capture_method field reliability."""
    confidence = data.get("capture_confidence")
    method = data.get("capture_method")
    source = data.get("capture_detection_method", "")

    if method is None and confidence is None:
        return FieldAssessment(
            field_name="capture_method",
            confidence=0.0,
            provenance_tier="tier_3_heuristic",
            is_soft_label=True,
            category="unreliable",
            populated=False,
        )

    conf = confidence if confidence is not None else 0.0
    tier = _infer_tier(source)
    is_soft = tier not in ("tier_0_exact", "tier_1_annotation")

    return FieldAssessment(
        field_name="capture_method",
        confidence=conf,
        provenance_tier=tier,
        is_soft_label=is_soft,
        category=classify_confidence(conf),
        populated=True,
    )


def assess_resolution(data: dict[str, Any]) -> FieldAssessment:
    """Assess resolution field reliability."""
    has_dpi = data.get("resolution_dpi") is not None
    has_pixels = data.get("resolution_pixels") is not None

    if has_dpi:
        return FieldAssessment(
            field_name="resolution",
            confidence=1.0,
            provenance_tier="tier_0_exact",
            is_soft_label=False,
            category="hard_label",
            populated=True,
        )
    if has_pixels:
        return FieldAssessment(
            field_name="resolution",
            confidence=0.95,
            provenance_tier="tier_0_exact",
            is_soft_label=False,
            category="hard_label",
            populated=True,
        )
    return FieldAssessment(
        field_name="resolution",
        confidence=0.0,
        provenance_tier="tier_3_heuristic",
        is_soft_label=True,
        category="unreliable",
        populated=False,
    )


def assess_domain(data: dict[str, Any]) -> FieldAssessment:
    """Assess domain classification reliability."""
    confidence = data.get("domain_confidence")
    domain = data.get("domain")

    if domain is None and confidence is None:
        return FieldAssessment(
            field_name="domain",
            confidence=0.0,
            provenance_tier="tier_3_heuristic",
            is_soft_label=True,
            category="unreliable",
            populated=False,
        )

    conf = confidence if confidence is not None else 0.0
    return FieldAssessment(
        field_name="domain",
        confidence=conf,
        provenance_tier="tier_1_annotation",
        is_soft_label=False,
        category=classify_confidence(conf),
        populated=True,
    )


def assess_language(data: dict[str, Any]) -> FieldAssessment:
    """Assess language detection reliability."""
    lang = data.get("iso639_language")

    if lang is None:
        return FieldAssessment(
            field_name="language",
            confidence=0.0,
            provenance_tier="tier_3_heuristic",
            is_soft_label=True,
            category="unreliable",
            populated=False,
        )

    # Prefer backfilled confidence (from backfill_language_confidence.py)
    backfilled_conf = data.get("language_confidence")
    backfilled_method = data.get("language_detection_method")
    backfilled_tier = data.get("language_provenance_tier")
    backfilled_soft = data.get("language_is_soft_label")

    if backfilled_conf is not None and backfilled_method is not None:
        tier = backfilled_tier or _infer_tier(backfilled_method)
        is_soft = (
            backfilled_soft
            if backfilled_soft is not None
            else (tier not in ("tier_0_exact", "tier_1_annotation"))
        )
        return FieldAssessment(
            field_name="language",
            confidence=backfilled_conf,
            provenance_tier=tier,
            is_soft_label=is_soft,
            category=classify_confidence(backfilled_conf),
            populated=True,
        )

    # Fallback: infer from v1 flat fields
    source = data.get("language_detection_method", "dataset_metadata")
    conf = 0.95 if source in GROUND_TRUTH_SOURCES else 0.8
    tier = _infer_tier(source)

    return FieldAssessment(
        field_name="language",
        confidence=conf,
        provenance_tier=tier,
        is_soft_label=tier not in ("tier_0_exact", "tier_1_annotation"),
        category=classify_confidence(conf),
        populated=True,
    )


def assess_text_quality(data: dict[str, Any]) -> FieldAssessment:
    """Assess text quality confidence from backfilled fields."""
    confidence = data.get("text_quality_confidence")
    method = data.get("text_quality_method")
    tier = data.get("text_quality_provenance_tier")

    if confidence is None and method is None:
        return FieldAssessment(
            field_name="text_quality",
            confidence=0.0,
            provenance_tier="tier_3_heuristic",
            is_soft_label=True,
            category="unreliable",
            populated=False,
        )

    conf = confidence if confidence is not None else 0.0
    tier_val = tier or _infer_tier(method)
    is_soft = tier_val not in ("tier_0_exact", "tier_1_annotation")

    return FieldAssessment(
        field_name="text_quality",
        confidence=conf,
        provenance_tier=tier_val,
        is_soft_label=is_soft,
        category=classify_confidence(conf),
        populated=True,
    )


def assess_content_flag(data: dict[str, Any], flag_name: str) -> FieldAssessment:
    """Assess a single content flag reliability."""
    value = data.get(flag_name)
    flags_tier = data.get("content_flags_tier")
    flags_source = data.get("content_flags_source", "")

    if value is None:
        return FieldAssessment(
            field_name=flag_name,
            confidence=0.0,
            provenance_tier="tier_3_heuristic",
            is_soft_label=True,
            category="unreliable",
            populated=False,
        )

    tier = flags_tier or _infer_tier(flags_source)
    if tier in ("tier_0_exact", "tier_1_annotation"):
        conf = 1.0
    elif tier == "tier_2_model":
        conf = 0.8
    else:
        conf = 0.6

    return FieldAssessment(
        field_name=flag_name,
        confidence=conf,
        provenance_tier=tier,
        is_soft_label=tier not in ("tier_0_exact", "tier_1_annotation"),
        category=classify_confidence(conf),
        populated=True,
    )


def assess_layout_detections(data: dict[str, Any]) -> FieldAssessment:
    """Assess layout detection reliability (summary over all detections)."""
    detections = data.get("layout_detections", [])

    if not detections:
        return FieldAssessment(
            field_name="layout_detections",
            confidence=0.0,
            provenance_tier="tier_3_heuristic",
            is_soft_label=True,
            category="unreliable",
            populated=False,
        )

    confidences = [
        d.get("confidence") for d in detections if d.get("confidence") is not None
    ]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    det_source = detections[0].get("source", "unknown")
    tier = _infer_tier(det_source)

    return FieldAssessment(
        field_name="layout_detections",
        confidence=avg_conf,
        provenance_tier=tier,
        is_soft_label=True,
        category=classify_confidence(avg_conf),
        populated=True,
    )


def _infer_tier(source: str | None) -> str:
    """Infer provenance tier from a source/method string."""
    if not source:
        return "tier_3_heuristic"

    if source in GROUND_TRUTH_SOURCES:
        return "tier_1_annotation"

    model_sources = {
        "doclayout_yolo",
        "docling",
        "ml_classifier",
        "artifact_analysis",
        "openlid_v2",
        "fasttext",
        "tesseract",
    }
    if source in model_sources:
        return "tier_2_model"

    if "heuristic" in source or "default" in source:
        return "tier_3_heuristic"

    # Known backfill methods
    if source in ("dataset_known_language", "folder_label"):
        return "tier_1_annotation"
    if source.startswith("openlid"):
        return "tier_2_model"
    if source in ("ground_truth_text", "docling_heuristic"):
        return "tier_1_annotation"

    return "tier_3_heuristic"


def compute_sample_summary(
    data: dict[str, Any],
) -> tuple[dict[str, Any], list[FieldAssessment]]:
    """Compute the sample_reliability_summary for a single sample.

    Args:
        data: The enrichment data dict for this sample.

    Returns:
        Tuple of (summary dict for JSON serialization, list of assessments).
    """
    assessments: list[FieldAssessment] = []

    assessments.append(assess_capture_method(data))
    assessments.append(assess_resolution(data))
    assessments.append(assess_domain(data))
    assessments.append(assess_language(data))
    assessments.append(assess_text_quality(data))

    for flag in ("has_table", "has_formula", "has_handwriting", "has_figure"):
        assessments.append(assess_content_flag(data, flag))

    assessments.append(assess_layout_detections(data))

    # Compute composite (all assessments have numeric confidence, never None)
    populated = [a for a in assessments if a.populated]
    unpopulated = [a for a in assessments if not a.populated]

    # min_confidence is across ALL fields (including unpopulated=0.0)
    min_assessment = min(assessments, key=lambda a: a.confidence)

    # min provenance tier
    min_tier_assessment = min(
        assessments, key=lambda a: TIER_RANK.get(a.provenance_tier, 0)
    )

    hard_count = sum(1 for a in assessments if a.category == "hard_label")
    soft_count = sum(1 for a in assessments if a.category == "soft_label")

    field_summary = [
        {
            "field": a.field_name,
            "confidence": a.confidence,
            "category": a.category,
            "is_soft_label": a.is_soft_label,
        }
        for a in assessments
    ]

    summary = {
        "min_confidence": round(min_assessment.confidence, 4),
        "min_confidence_field": min_assessment.field_name,
        "min_confidence_category": classify_confidence(min_assessment.confidence),
        "min_provenance_tier": min_tier_assessment.provenance_tier,
        "assessed_field_count": len(populated),
        "unassessed_field_count": 0,  # We no longer have null = unassessed
        "unpopulated_field_count": len(unpopulated),
        "hard_field_count": hard_count,
        "soft_field_count": soft_count,
        "field_summary": field_summary,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    return summary, assessments


def compute_dataset_bottlenecks(
    all_assessments: list[list[FieldAssessment]],
    sample_count: int,
) -> list[DatasetBottleneck]:
    """Compute the top bottleneck fields across all samples in a dataset.

    A bottleneck field is the field that is most frequently the min_confidence
    field (the weakest link) across samples.

    Args:
        all_assessments: List of per-sample assessment lists.
        sample_count: Total samples in the dataset.

    Returns:
        Top 3 bottleneck fields sorted by frequency.
    """
    bottleneck_counts: Counter[str] = Counter()
    field_confidences: dict[str, list[float]] = {}

    for assessments in all_assessments:
        if not assessments:
            continue

        min_assessment = min(assessments, key=lambda a: a.confidence)
        bottleneck_counts[min_assessment.field_name] += 1

        for a in assessments:
            if a.field_name not in field_confidences:
                field_confidences[a.field_name] = []
            field_confidences[a.field_name].append(a.confidence)

    result = []
    for field_name, count in bottleneck_counts.most_common(3):
        confs = field_confidences.get(field_name, [])
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        result.append(
            DatasetBottleneck(
                field_name=field_name,
                bottleneck_count=count,
                bottleneck_pct=round(count / sample_count * 100, 1)
                if sample_count > 0
                else 0.0,
                avg_confidence=round(avg_conf, 4),
            )
        )

    return result


def _get_current_enrichment_data(sample: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the current enrichment data dict from a sample.

    Returns:
        The data dict, or None if no enrichment versions exist.
    """
    enrichments = sample.get("enrichments", {})
    versions = enrichments.get("versions", [])
    if not versions:
        return None

    current_ver = enrichments.get("current_version", 1)
    data = versions[-1].get("data", {})
    for v in versions:
        if v.get("version") == current_ver:
            data = v.get("data", {})
            break
    return data


def _write_reliability_metadata(
    metadata: dict[str, Any],
    metadata_path: Path,
    stats: dict[str, Any],
) -> None:
    """Write reliability summary metadata back to the JSON file."""
    metadata.setdefault("backfill_history", [])
    metadata["backfill_history"].append(
        {
            "operation": "reliability_summary_materialization",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "materialized": stats["materialized"],
                "already_had_summary": stats["already_has_summary"],
                "bottlenecks": stats["bottlenecks"],
            },
        }
    )
    metadata["reliability_bottlenecks"] = stats["bottlenecks"]
    metadata["reliability_avg_min_confidence"] = stats["avg_min_confidence"]
    metadata["reliability_category_distribution"] = stats["category_distribution"]

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info(f"  Written: {metadata_path}")


def process_dataset(
    dataset_name: str,
    metadata_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Process a single dataset: compute and write reliability summaries.

    Args:
        dataset_name: Canonical dataset name (underscored form).
        metadata_dir: Directory containing *_metadata.json files.
        dry_run: If True, report changes without writing.
        force: If True, re-compute even for samples that already have summaries.

    Returns:
        Stats dict with processing results and bottleneck info.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "materialized": 0,
        "already_has_summary": 0,
        "skipped_no_enrichment": 0,
        "bottlenecks": [],
        "avg_min_confidence": 0.0,
        "category_distribution": {},
    }

    metadata_path = metadata_dir / f"{dataset_name}_metadata.json"
    if not metadata_path.exists():
        logger.warning(f"No metadata file for {dataset_name}: {metadata_path}")
        return stats

    with open(metadata_path) as f:
        metadata = json.load(f)

    samples = metadata.get("samples", [])
    stats["total"] = len(samples)

    if not samples:
        logger.warning(f"{dataset_name}: no samples found")
        return stats

    all_assessments: list[list[FieldAssessment]] = []
    category_dist: Counter[str] = Counter()
    min_confidences: list[float] = []

    for sample in samples:
        data = _get_current_enrichment_data(sample)
        if data is None:
            stats["skipped_no_enrichment"] += 1
            continue

        existing = data.get("sample_reliability_summary")
        if existing is not None and not force:
            stats["already_has_summary"] += 1
            continue

        summary, assessments = compute_sample_summary(data)
        all_assessments.append(assessments)
        data["sample_reliability_summary"] = summary
        stats["materialized"] += 1
        category_dist[summary["min_confidence_category"]] += 1
        min_confidences.append(summary["min_confidence"])

    bottlenecks = compute_dataset_bottlenecks(all_assessments, stats["materialized"])
    stats["bottlenecks"] = [asdict(b) for b in bottlenecks]
    stats["category_distribution"] = dict(category_dist)

    if min_confidences:
        stats["avg_min_confidence"] = round(
            sum(min_confidences) / len(min_confidences), 4
        )

    if not dry_run and stats["materialized"] > 0:
        _write_reliability_metadata(metadata, metadata_path, stats)
    elif dry_run:
        logger.info(f"  DRY RUN: would write {metadata_path}")

    return stats


def update_dataset_doc(
    dataset_name: str,
    stats: dict[str, Any],
    docs_dir: Path,
) -> bool:
    """Update a dataset's documentation file with reliability bottleneck info.

    Appends or replaces a 'Reliability & Bottlenecks' section at the end of
    the dataset's source documentation.

    Args:
        dataset_name: Canonical dataset name (hyphenated for docs).
        stats: Processing stats including bottleneck info.
        docs_dir: Path to docs/datasets/source/ directory.

    Returns:
        True if the doc was updated, False otherwise.
    """
    # Convert underscored metadata name to hyphenated doc name
    doc_name = dataset_name.replace("_", "-")
    doc_path = docs_dir / f"{doc_name}.md"

    if not doc_path.exists():
        logger.debug(f"  No doc file for {dataset_name}: {doc_path}")
        return False

    bottlenecks = stats.get("bottlenecks", [])
    if not bottlenecks:
        return False

    avg_min = stats.get("avg_min_confidence", 0.0)
    category_dist = stats.get("category_distribution", {})
    total = stats.get("materialized", 0) + stats.get("already_has_summary", 0)

    # Build the reliability section
    lines = [
        "",
        "##### Reliability & Bottlenecks",
        "",
        f"> **Computed**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} "
        f"| **Samples**: {total:,} | **Avg Min Confidence**: {avg_min:.3f}",
        "",
    ]

    # Category distribution
    if category_dist:
        lines.append("**Composite Category Distribution**:")
        lines.append("")
        lines.append("| Category | Count | Pct |")
        lines.append("|----------|------:|----:|")
        for cat in [
            "hard_label",
            "soft_label",
            "active_learning",
            "unreliable",
        ]:
            count = category_dist.get(cat, 0)
            pct = round(count / total * 100, 1) if total > 0 else 0.0
            lines.append(f"| {cat} | {count:,} | {pct}% |")
        lines.append("")

    # Bottleneck table
    lines.append("**Top Bottleneck Fields** (most frequently the weakest):")
    lines.append("")
    lines.append("| Rank | Field | Bottleneck % | Avg Confidence |")
    lines.append("|-----:|-------|-------------:|---------------:|")
    for i, b in enumerate(bottlenecks, 1):
        lines.append(
            f"| {i} | `{b['field_name']}` | "
            f"{b['bottleneck_pct']}% | {b['avg_confidence']:.3f} |"
        )
    lines.append("")

    section_text = "\n".join(lines)

    # Read existing doc
    content = doc_path.read_text(encoding="utf-8")

    # Replace existing section or append
    section_marker = "##### Reliability & Bottlenecks"
    if section_marker in content:
        # Find the section and replace up to next section or EOF
        pattern = (
            r"##### Reliability & Bottlenecks.*?"
            r"(?=\n#{1,5} [^\n]|\Z)"
        )
        content = re.sub(pattern, section_text.lstrip("\n"), content, flags=re.DOTALL)
    else:
        # Append before final blank lines
        content = content.rstrip() + "\n" + section_text

    doc_path.write_text(content, encoding="utf-8")
    logger.info(f"  Updated doc: {doc_path}")
    return True


def find_all_datasets(metadata_dir: Path) -> list[str]:
    """Find all datasets with metadata files.

    Args:
        metadata_dir: Directory containing metadata JSON files.

    Returns:
        List of dataset names (underscored form).
    """
    datasets = []
    for path in sorted(metadata_dir.glob("*_metadata.json")):
        name = path.stem.replace("_metadata", "")
        datasets.append(name)
    return datasets


def _accumulate_dataset_stats(
    total_stats: dict[str, int],
    stats: dict[str, Any],
) -> None:
    """Add per-dataset stats into the running total."""
    for key in (
        "total",
        "materialized",
        "already_has_summary",
        "skipped_no_enrichment",
    ):
        total_stats[key] += stats[key]


def _log_dataset_progress(
    dataset_name: str,
    stats: dict[str, Any],
) -> None:
    """Log per-dataset processing summary."""
    bottleneck_str = ""
    if stats["bottlenecks"]:
        top = stats["bottlenecks"][0]
        bottleneck_str = (
            f" top_bottleneck={top['field_name']}({top['bottleneck_pct']}%)"
        )
    logger.info(
        f"  {dataset_name}: total={stats['total']} "
        f"materialized={stats['materialized']} "
        f"already={stats['already_has_summary']} "
        f"avg_min_conf={stats['avg_min_confidence']:.3f}"
        f"{bottleneck_str}"
    )


def _print_final_summary(
    total_stats: dict[str, int],
    all_bottlenecks: list[dict[str, Any]],
    show_docs: bool,
) -> None:
    """Print the final materialization summary."""
    print(f"\n{'=' * 60}")
    print("RELIABILITY MATERIALIZATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total samples:           {total_stats['total']:>8,}")
    print(f"Materialized:            {total_stats['materialized']:>8,}")
    print(f"Already had summary:     {total_stats['already_has_summary']:>8,}")
    print(f"Skipped (no enrichment): {total_stats['skipped_no_enrichment']:>8,}")
    if show_docs:
        print(f"Docs updated:            {total_stats['docs_updated']:>8,}")

    if not all_bottlenecks:
        return

    print(f"\n{'─' * 60}")
    print("CROSS-DATASET BOTTLENECK SUMMARY")
    print(f"{'─' * 60}")

    field_bottleneck_counts: Counter[str] = Counter()
    for entry in all_bottlenecks:
        for b in entry["bottlenecks"]:
            field_bottleneck_counts[b["field_name"]] += b["bottleneck_count"]

    for field_name, count in field_bottleneck_counts.most_common(5):
        print(f"  {field_name:25s} {count:8,} samples")


def main() -> None:
    """Run the reliability summary materialization."""
    parser = argparse.ArgumentParser(
        description=("Materialize sample_reliability_summary into Layer 2 metadata"),
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
        "--docs-dir",
        type=Path,
        default=Path("docs/datasets/source"),
        help="Directory containing per-dataset documentation",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report changes without writing files"
    )
    parser.add_argument(
        "--all", action="store_true", help="Process all datasets with metadata files"
    )
    parser.add_argument(
        "--update-docs",
        action="store_true",
        help="Update docs/datasets/source/ files with bottleneck info",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute even if sample_reliability_summary already exists",
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
        "materialized": 0,
        "already_has_summary": 0,
        "skipped_no_enrichment": 0,
        "docs_updated": 0,
    }
    all_bottlenecks: list[dict[str, Any]] = []

    for dataset_name in datasets:
        logger.info(f"Processing: {dataset_name}")
        stats = process_dataset(
            dataset_name, args.metadata_dir, args.dry_run, args.force
        )

        _accumulate_dataset_stats(total_stats, stats)
        _log_dataset_progress(dataset_name, stats)

        if args.update_docs and not args.dry_run and stats["bottlenecks"]:
            updated = update_dataset_doc(dataset_name, stats, args.docs_dir)
            if updated:
                total_stats["docs_updated"] += 1
                all_bottlenecks.append(
                    {
                        "dataset": dataset_name,
                        "bottlenecks": stats["bottlenecks"],
                    }
                )

    _print_final_summary(total_stats, all_bottlenecks, args.update_docs)


if __name__ == "__main__":
    main()
