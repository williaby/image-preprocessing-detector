"""Soft Label Reliability Analysis for Layer 2 Enrichment v2 Schema.

Reads existing Layer 2 metadata JSON files and applies the v2 soft label
reliability tagging system to classify each enrichment field as hard label,
soft label, or unassessed. Produces a per-dataset report showing confidence
distributions, provenance tier breakdowns, and training readiness.

Usage:
    python scripts/analyze_soft_labels.py --datasets funsd sroie
    python scripts/analyze_soft_labels.py --all --metadata-dir /mnt/e/image_detection/metadata_registry/json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# --- Threshold configuration (pipeline config, NOT schema-enforced) ---
HARD_LABEL_THRESHOLD = 0.9
SOFT_LABEL_THRESHOLD = 0.7
ACTIVE_LEARNING_THRESHOLD = 0.5

# --- Provenance tier mapping from v1 flat fields to v2 ProvenanceTier ---
TIER_MAP: dict[str, str] = {
    "tier_0_exact": "tier_0_exact",
    "tier_0_exact_by_construction": "tier_0_exact",
    "tier_1_annotation": "tier_1_annotation",
    "tier_2_model": "tier_2_model",
    "tier_3_heuristic": "tier_3_heuristic",
}

# Source strings that indicate ground truth (not soft labels)
GROUND_TRUTH_SOURCES: set[str] = {
    "coco_annotation",
    "dataset_config",
    "dataset_metadata",
    "manual",
    "ground_truth",
    "pdf_metadata",
}

# Source strings that indicate model-derived (soft labels)
MODEL_SOURCES: set[str] = {
    "doclayout_yolo",
    "docling",
    "ml_classifier",
    "artifact_analysis",
    "openlid_v2",
    "fasttext",
    "tesseract",
}


@dataclass(frozen=True)
class FieldReliability:
    """Reliability assessment for a single enrichment field."""

    field_name: str
    confidence: float | None
    provenance_tier: str
    is_soft_label: bool
    detection_method: str
    label_category: (
        str  # hard_label, soft_label, active_learning, unreliable, unassessed
    )


TIER_RANK: dict[str, int] = {
    "tier_0_exact": 3,
    "tier_1_annotation": 2,
    "tier_2_model": 1,
    "tier_3_heuristic": 0,
}


@dataclass
class SampleReliabilitySummary:
    """Computed composite: worst-case reliability across all fields."""

    min_confidence: float | None
    min_confidence_field: str | None
    min_confidence_category: str
    min_provenance_tier: str
    assessed_field_count: int
    unassessed_field_count: int
    hard_field_count: int
    soft_field_count: int
    active_learning_count: int
    unreliable_count: int

    @staticmethod
    def from_assessments(
        assessments: list[FieldReliability],
    ) -> SampleReliabilitySummary:
        """Compute composite from per-field assessments."""
        assessed = [a for a in assessments if a.confidence is not None]
        unassessed = [a for a in assessments if a.confidence is None]

        if not assessed:
            return SampleReliabilitySummary(
                min_confidence=None,
                min_confidence_field=None,
                min_confidence_category="unassessed",
                min_provenance_tier="tier_3_heuristic",
                assessed_field_count=0,
                unassessed_field_count=len(unassessed),
                hard_field_count=0,
                soft_field_count=0,
                active_learning_count=0,
                unreliable_count=0,
            )

        min_field = min(assessed, key=lambda a: a.confidence)  # type: ignore[arg-type]
        min_tier_field = min(
            assessments,
            key=lambda a: TIER_RANK.get(a.provenance_tier, 0),
        )

        hard = sum(1 for a in assessed if a.label_category == "hard_label")
        soft = sum(1 for a in assessed if a.label_category == "soft_label")
        active = sum(1 for a in assessed if a.label_category == "active_learning")
        unreliable = sum(1 for a in assessed if a.label_category == "unreliable")

        return SampleReliabilitySummary(
            min_confidence=min_field.confidence,
            min_confidence_field=min_field.field_name,
            min_confidence_category=classify_confidence(min_field.confidence),
            min_provenance_tier=min_tier_field.provenance_tier,
            assessed_field_count=len(assessed),
            unassessed_field_count=len(unassessed),
            hard_field_count=hard,
            soft_field_count=soft,
            active_learning_count=active,
            unreliable_count=unreliable,
        )


@dataclass
class SampleAnalysis:
    """Analysis result for a single sample's enrichment data."""

    sample_id: str
    field_assessments: list[FieldReliability] = field(default_factory=list)
    layout_detection_count: int = 0
    layout_avg_confidence: float | None = None
    reliability_summary: SampleReliabilitySummary | None = None


@dataclass
class OpenLIDSecondaryStats:
    """Statistics about OpenLID secondary validation signals."""

    total_with_secondary: int = 0
    agrees_count: int = 0
    disagrees_count: int = 0
    secondary_confidences: list[float] = field(default_factory=list)


@dataclass
class DatasetReport:
    """Aggregate report for a dataset."""

    dataset_name: str
    sample_count: int
    root_method: str
    samples: list[SampleAnalysis] = field(default_factory=list)

    # Aggregate counters
    label_category_counts: Counter[str] = field(default_factory=Counter)
    provenance_tier_counts: Counter[str] = field(default_factory=Counter)
    field_confidence_sums: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    field_soft_label_counts: dict[str, Counter[bool]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    openlid_stats: OpenLIDSecondaryStats = field(default_factory=OpenLIDSecondaryStats)


def classify_confidence(confidence: float | None) -> str:
    """Classify a confidence value into a training label category.

    Args:
        confidence: Confidence score 0-1, or None if unassessed.

    Returns:
        Label category string.
    """
    if confidence is None:
        return "unassessed"
    if confidence >= HARD_LABEL_THRESHOLD:
        return "hard_label"
    if confidence >= SOFT_LABEL_THRESHOLD:
        return "soft_label"
    if confidence >= ACTIVE_LEARNING_THRESHOLD:
        return "active_learning"
    return "unreliable"


def determine_provenance_tier(
    root_method: str,
    field_tier: str | None = None,
    source: str | None = None,
) -> str:
    """Determine the provenance tier for a field.

    Args:
        root_method: Root-level method tier from the enrichment record.
        field_tier: Field-specific tier override (e.g., content_flags_tier).
        source: Detection source string for additional context.

    Returns:
        ProvenanceTier enum string.
    """
    # Field-specific tier takes priority
    if field_tier and field_tier in TIER_MAP:
        return TIER_MAP[field_tier]

    # Infer from source string
    if source:
        if source in GROUND_TRUTH_SOURCES:
            return "tier_1_annotation"
        if source in MODEL_SOURCES:
            return "tier_2_model"
        if "heuristic" in source or "default" in source:
            return "tier_3_heuristic"

    # Fall back to root method
    return TIER_MAP.get(root_method, "tier_3_heuristic")


def determine_is_soft_label(
    provenance_tier: str,
    confidence: float | None,
    source: str | None = None,
) -> bool:
    """Determine if a field value is a soft label.

    Args:
        provenance_tier: The provenance tier for this field.
        confidence: Confidence score, or None.
        source: Detection source string.

    Returns:
        True if the label is inferred/predicted (soft), False if ground truth.
    """
    # Tier 0 (exact/by-construction) and tier 1 (annotation) are hard labels
    if provenance_tier in ("tier_0_exact", "tier_1_annotation"):
        return False

    # Tier 2 (model) is always soft
    if provenance_tier == "tier_2_model":
        return True

    # Tier 3 (heuristic) is soft unless confidence is very high
    if provenance_tier == "tier_3_heuristic":
        return True

    # Source-based fallback
    if source and source in GROUND_TRUTH_SOURCES:
        return False

    return True


def analyze_capture_method(data: dict[str, Any], root_method: str) -> FieldReliability:
    """Analyze capture_method field reliability."""
    confidence = data.get("capture_confidence")
    source = data.get("capture_detection_method", "")
    tier = determine_provenance_tier(root_method, source=source)
    is_soft = determine_is_soft_label(tier, confidence, source)

    return FieldReliability(
        field_name="capture_method",
        confidence=confidence,
        provenance_tier=tier,
        is_soft_label=is_soft,
        detection_method=source or "unknown",
        label_category=classify_confidence(confidence),
    )


def analyze_resolution(data: dict[str, Any], root_method: str) -> FieldReliability:
    """Analyze resolution field reliability."""
    # Resolution is typically deterministic from image metadata
    has_dpi = data.get("resolution_dpi") is not None
    has_pixels = data.get("resolution_pixels") is not None

    if has_dpi:
        confidence = 1.0
        tier = "tier_0_exact"
    elif has_pixels:
        confidence = 0.95
        tier = "tier_0_exact"
    else:
        confidence = None
        tier = determine_provenance_tier(root_method)

    return FieldReliability(
        field_name="resolution",
        confidence=confidence,
        provenance_tier=tier,
        is_soft_label=False,  # Resolution is always deterministic
        detection_method="image_metadata" if has_pixels else "unknown",
        label_category=classify_confidence(confidence),
    )


def analyze_domain(data: dict[str, Any], root_method: str) -> FieldReliability:
    """Analyze domain classification reliability."""
    confidence = data.get("domain_confidence")
    # Domain is typically from dataset config (hard) or classifier (soft)
    source = "dataset_config"  # Default assumption for v1 data
    tier = determine_provenance_tier(root_method, source=source)
    is_soft = determine_is_soft_label(tier, confidence, source)

    return FieldReliability(
        field_name="domain",
        confidence=confidence,
        provenance_tier=tier,
        is_soft_label=is_soft,
        detection_method=source,
        label_category=classify_confidence(confidence),
    )


def analyze_language(data: dict[str, Any], root_method: str) -> FieldReliability:
    """Analyze language detection reliability.

    Reads backfilled language confidence fields if present, falling back to
    heuristic inference from v1 flat fields.
    """
    lang = data.get("iso639_language")
    if lang is None:
        return FieldReliability(
            field_name="language",
            confidence=None,
            provenance_tier=determine_provenance_tier(root_method),
            is_soft_label=True,
            detection_method="none",
            label_category="unassessed",
        )

    # Prefer backfilled confidence fields (from backfill_language_confidence.py)
    backfilled_confidence = data.get("language_confidence")
    backfilled_method = data.get("language_detection_method")
    backfilled_tier = data.get("language_provenance_tier")
    backfilled_soft = data.get("language_is_soft_label")

    if backfilled_confidence is not None and backfilled_method is not None:
        tier = backfilled_tier or determine_provenance_tier(
            root_method, source=backfilled_method
        )
        is_soft = (
            backfilled_soft
            if backfilled_soft is not None
            else (
                determine_is_soft_label(tier, backfilled_confidence, backfilled_method)
            )
        )
        return FieldReliability(
            field_name="language",
            confidence=backfilled_confidence,
            provenance_tier=tier,
            is_soft_label=is_soft,
            detection_method=backfilled_method,
            label_category=classify_confidence(backfilled_confidence),
        )

    # Fallback: infer from v1 flat fields (pre-backfill data)
    source = data.get("language_detection_method", "dataset_metadata")
    tier = determine_provenance_tier(root_method, source=source)
    confidence = 0.95 if source in GROUND_TRUTH_SOURCES else 0.8
    is_soft = determine_is_soft_label(tier, confidence, source)

    return FieldReliability(
        field_name="language",
        confidence=confidence,
        provenance_tier=tier,
        is_soft_label=is_soft,
        detection_method=source,
        label_category=classify_confidence(confidence),
    )


def analyze_text_quality(data: dict[str, Any], root_method: str) -> FieldReliability:
    """Analyze text quality confidence from backfilled fields.

    Reads text_quality_confidence, text_quality_method, etc. set by
    backfill_text_quality_confidence.py. Returns unassessed if not populated.
    """
    confidence = data.get("text_quality_confidence")
    method = data.get("text_quality_method")
    tier = data.get("text_quality_provenance_tier")
    is_soft = data.get("text_quality_is_soft_label")

    if confidence is None and method is None:
        return FieldReliability(
            field_name="text_quality",
            confidence=None,
            provenance_tier=determine_provenance_tier(root_method),
            is_soft_label=True,
            detection_method="none",
            label_category="unassessed",
        )

    tier = tier or determine_provenance_tier(root_method, source=method)
    if is_soft is None:
        is_soft = tier not in ("tier_0_exact", "tier_1_annotation")

    return FieldReliability(
        field_name="text_quality",
        confidence=confidence,
        provenance_tier=tier,
        is_soft_label=is_soft,
        detection_method=method or "unknown",
        label_category=classify_confidence(confidence),
    )


def analyze_content_flags(
    data: dict[str, Any], root_method: str
) -> list[FieldReliability]:
    """Analyze content flag reliability (per-flag)."""
    flags = ["has_table", "has_formula", "has_handwriting", "has_figure"]
    results = []

    flags_tier = data.get("content_flags_tier")
    flags_source = data.get("content_flags_source", "")
    tier = determine_provenance_tier(root_method, field_tier=flags_tier)

    for flag_name in flags:
        value = data.get(flag_name)
        if value is None:
            results.append(
                FieldReliability(
                    field_name=flag_name,
                    confidence=None,
                    provenance_tier=tier,
                    is_soft_label=True,
                    detection_method=flags_source or "unknown",
                    label_category="unassessed",
                )
            )
            continue

        # Ground truth annotations have high confidence
        if tier in ("tier_0_exact", "tier_1_annotation"):
            confidence = 1.0
        elif tier == "tier_2_model":
            # Model-derived flags: moderate confidence
            confidence = 0.8
        else:
            confidence = 0.6

        is_soft = determine_is_soft_label(tier, confidence, flags_source)

        results.append(
            FieldReliability(
                field_name=flag_name,
                confidence=confidence,
                provenance_tier=tier,
                is_soft_label=is_soft,
                detection_method=flags_source or "unknown",
                label_category=classify_confidence(confidence),
            )
        )

    return results


def analyze_layout_detections(
    data: dict[str, Any], root_method: str
) -> tuple[list[FieldReliability], int, float | None]:
    """Analyze layout detection reliability.

    Returns:
        Tuple of (field assessments, detection count, average confidence).
    """
    detections = data.get("layout_detections", [])
    if not detections:
        return [], 0, None

    confidences = []
    soft_count = 0

    for det in detections:
        conf = det.get("confidence")
        source = det.get("source", "")
        if conf is not None:
            confidences.append(conf)

        tier = determine_provenance_tier(root_method, source=source)
        is_soft = determine_is_soft_label(tier, conf, source)
        if is_soft:
            soft_count += 1

    avg_conf = sum(confidences) / len(confidences) if confidences else None

    # Create a summary field reliability for the array
    det_source = detections[0].get("source", "unknown") if detections else "unknown"
    flags_tier = data.get("content_flags_tier")
    tier = determine_provenance_tier(
        root_method, field_tier=flags_tier, source=det_source
    )

    assessment = FieldReliability(
        field_name="layout_detections",
        confidence=avg_conf,
        provenance_tier=tier,
        is_soft_label=soft_count > 0,
        detection_method=det_source,
        label_category=classify_confidence(avg_conf),
    )

    return [assessment], len(detections), avg_conf


def analyze_sample(sample: dict[str, Any], root_method: str) -> SampleAnalysis:
    """Run full soft label reliability analysis on a single sample.

    Args:
        sample: Sample dict from the metadata JSON.
        root_method: Root enrichment method tier.

    Returns:
        SampleAnalysis with per-field assessments.
    """
    enrichment = sample["enrichments"]["versions"][0]
    data = enrichment["data"]
    sample_id = sample.get("id", "unknown")

    assessments: list[FieldReliability] = []

    # Analyze each enrichment field category
    assessments.append(analyze_capture_method(data, root_method))
    assessments.append(analyze_resolution(data, root_method))
    assessments.append(analyze_domain(data, root_method))
    assessments.append(analyze_language(data, root_method))
    assessments.append(analyze_text_quality(data, root_method))
    assessments.extend(analyze_content_flags(data, root_method))

    layout_assessments, layout_count, layout_avg = analyze_layout_detections(
        data, root_method
    )
    assessments.extend(layout_assessments)

    reliability = SampleReliabilitySummary.from_assessments(assessments)

    return SampleAnalysis(
        sample_id=sample_id,
        field_assessments=assessments,
        layout_detection_count=layout_count,
        layout_avg_confidence=layout_avg,
        reliability_summary=reliability,
    )


def analyze_dataset(metadata_path: Path) -> DatasetReport:
    """Analyze an entire dataset's Layer 2 metadata.

    Args:
        metadata_path: Path to the dataset's metadata JSON file.

    Returns:
        DatasetReport with aggregate statistics.
    """
    with open(metadata_path) as f:
        metadata = json.load(f)

    dataset_name = metadata.get("dataset_name", metadata_path.stem)
    sample_count = metadata.get("sample_count", 0)

    # Get root method from first sample
    samples = metadata.get("samples", [])
    if not samples:
        return DatasetReport(
            dataset_name=dataset_name,
            sample_count=0,
            root_method="unknown",
        )

    root_method = samples[0]["enrichments"]["versions"][0].get("method", "unknown")

    report = DatasetReport(
        dataset_name=dataset_name,
        sample_count=sample_count,
        root_method=root_method,
    )

    for sample in samples:
        analysis = analyze_sample(sample, root_method)
        report.samples.append(analysis)

        for assessment in analysis.field_assessments:
            report.label_category_counts[assessment.label_category] += 1
            report.provenance_tier_counts[assessment.provenance_tier] += 1
            report.field_soft_label_counts[assessment.field_name][
                assessment.is_soft_label
            ] += 1

            if assessment.confidence is not None:
                report.field_confidence_sums[assessment.field_name].append(
                    assessment.confidence
                )

        # Collect OpenLID secondary signal stats from raw data
        data = sample["enrichments"]["versions"][0].get("data", {})
        openlid_conf = data.get("openlid_confidence")
        if openlid_conf is not None:
            report.openlid_stats.total_with_secondary += 1
            report.openlid_stats.secondary_confidences.append(openlid_conf)
            primary_lang = data.get("iso639_language")
            openlid_lang = data.get("openlid_language")
            if primary_lang and openlid_lang:
                if primary_lang == openlid_lang:
                    report.openlid_stats.agrees_count += 1
                else:
                    report.openlid_stats.disagrees_count += 1

    return report


def _print_language_summary(report: DatasetReport) -> None:
    """Print language/script confidence summary including OpenLID secondary signal."""
    methods: Counter[str] = Counter()

    for sample in report.samples:
        for fa in sample.field_assessments:
            if fa.field_name == "language":
                methods[fa.detection_method] += 1
                break

    print(f"  {'LANGUAGE/SCRIPT CONFIDENCE':─<50}")
    print("  Detection methods:")
    for method, count in methods.most_common():
        pct = count / len(report.samples) * 100 if report.samples else 0
        print(f"    {method:30s} {count:6d} ({pct:5.1f}%)")

    # OpenLID secondary validation stats
    stats = report.openlid_stats
    if stats.total_with_secondary > 0:
        avg_conf = sum(stats.secondary_confidences) / len(stats.secondary_confidences)
        agree_pct = stats.agrees_count / stats.total_with_secondary * 100
        print(
            f"\n  OpenLID secondary validation ({stats.total_with_secondary} samples):"
        )
        print(f"    Agrees with primary:   {stats.agrees_count:6d} ({agree_pct:5.1f}%)")
        print(
            f"    Disagrees:             {stats.disagrees_count:6d} ({100 - agree_pct:5.1f}%)"
        )
        print(f"    Avg OpenLID confidence: {avg_conf:.3f}")
        conf_band = format_confidence_band(stats.secondary_confidences)
        print(f"    Confidence band:       {conf_band}")
    print()


def _print_text_quality_summary(report: DatasetReport) -> None:
    """Print text quality confidence summary including dataset cap info."""
    methods: Counter[str] = Counter()

    for sample in report.samples:
        for fa in sample.field_assessments:
            if fa.field_name == "text_quality":
                methods[fa.detection_method] += 1
                break

    # Cap info will show through the method/confidence values

    print(f"  {'TEXT QUALITY CONFIDENCE':─<50}")
    if not methods or (len(methods) == 1 and "none" in methods):
        print(
            "  No text quality data available (run backfill_text_quality_confidence.py)"
        )
        print()
        return

    print("  Detection methods:")
    for method, count in methods.most_common():
        pct = count / len(report.samples) * 100 if report.samples else 0
        print(f"    {method:30s} {count:6d} ({pct:5.1f}%)")

    # Confidence distribution for text quality
    text_confs = report.field_confidence_sums.get("text_quality", [])
    if text_confs:
        conf_band = format_confidence_band(text_confs)
        print(f"  Confidence band:       {conf_band}")
    print()


def format_confidence_band(values: list[float]) -> str:
    """Format confidence values into a distribution summary."""
    if not values:
        return "no data"

    hard = sum(1 for v in values if v >= HARD_LABEL_THRESHOLD)
    soft = sum(1 for v in values if SOFT_LABEL_THRESHOLD <= v < HARD_LABEL_THRESHOLD)
    active = sum(
        1 for v in values if ACTIVE_LEARNING_THRESHOLD <= v < SOFT_LABEL_THRESHOLD
    )
    unreliable = sum(1 for v in values if v < ACTIVE_LEARNING_THRESHOLD)

    avg = sum(values) / len(values)
    return (
        f"avg={avg:.3f} | "
        f"hard({hard}) soft({soft}) active_learn({active}) unreliable({unreliable})"
    )


def _print_category_histogram(
    title: str,
    categories: list[str],
    counts_source: dict | Counter,
    total: int,
) -> None:
    """Print a histogram section for a list of categories.

    Args:
        title: Section title string.
        categories: Ordered list of category keys.
        counts_source: Dict/Counter mapping category to count.
        total: Total for percentage calculation.
    """
    print(f"  {title:─<50}")
    for category in categories:
        count = counts_source.get(category, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {category:20s} {count:6d} ({pct:5.1f}%) {bar}")
    print()


def _get_field_label_tag(report: DatasetReport, field_name: str) -> str:
    """Determine whether a field is HARD, SOFT, or MIXED across the dataset."""
    soft_counts = report.field_soft_label_counts.get(field_name, Counter())
    hard_n = soft_counts.get(False, 0)
    soft_n = soft_counts.get(True, 0)
    if soft_n == 0:
        return "HARD"
    if hard_n == 0:
        return "SOFT"
    return "MIXED"


def _determine_readiness(hard_pct: float, soft_pct: float) -> str:
    """Return a training readiness label based on hard/soft label percentages."""
    if hard_pct >= 70:
        return "HIGH - Majority hard labels, suitable for supervised training"
    if hard_pct + soft_pct >= 70:
        return "MODERATE - Mix of hard/soft labels, suitable for semi-supervised"
    if soft_pct >= 50:
        return "LOW - Predominantly soft labels, use with confidence weighting"
    return "NEEDS ENRICHMENT - Too many unassessed fields"


def _print_training_readiness(report: DatasetReport, total_fields: int) -> None:
    """Print the training readiness and sample-level composite sections."""

    def _safe_pct(key: str) -> float:
        return (
            report.label_category_counts.get(key, 0) / total_fields * 100
            if total_fields > 0
            else 0
        )

    hard_pct = _safe_pct("hard_label")
    soft_pct = _safe_pct("soft_label")
    unassessed_pct = _safe_pct("unassessed")

    print(f"  {'TRAINING READINESS':─<50}")
    print(f"  Readiness: {_determine_readiness(hard_pct, soft_pct)}")
    print(f"  Hard labels:  {hard_pct:.1f}%  (full training weight)")
    print(f"  Soft labels:  {soft_pct:.1f}%  (reduced weight / semi-supervised)")
    print(f"  Unassessed:   {unassessed_pct:.1f}%  (apply default policy)")
    print()

    # Sample-Level Composite
    composite_counts: Counter[str] = Counter()
    bottleneck_counts: Counter[str] = Counter()
    for sample in report.samples:
        if not sample.reliability_summary:
            continue
        composite_counts[sample.reliability_summary.min_confidence_category] += 1
        if sample.reliability_summary.min_confidence_field:
            bottleneck_counts[sample.reliability_summary.min_confidence_field] += 1

    _print_category_histogram(
        "SAMPLE-LEVEL COMPOSITE (min_confidence_category per sample)",
        ["hard_label", "soft_label", "active_learning", "unreliable", "unassessed"],
        composite_counts,
        len(report.samples),
    )

    print(f"  {'BOTTLENECK FIELDS (which field is the weakest most often)':─<50}")
    n_samples = len(report.samples)
    for field_name, count in bottleneck_counts.most_common():
        pct = count / n_samples * 100
        print(f"  {field_name:22s} {count:6d} ({pct:5.1f}%)")

    print(f"\n{'=' * 72}\n")


def print_report(report: DatasetReport) -> None:
    """Print a formatted analysis report for a dataset."""
    total_fields = sum(report.label_category_counts.values())

    print(f"\n{'=' * 72}")
    print(f"  SOFT LABEL RELIABILITY ANALYSIS: {report.dataset_name.upper()}")
    print(f"{'=' * 72}")
    print(f"  Samples: {report.sample_count}")
    print(f"  Root method: {report.root_method}")
    print(f"  Total field assessments: {total_fields}")
    print()

    _label_categories = [
        "hard_label",
        "soft_label",
        "active_learning",
        "unreliable",
        "unassessed",
    ]
    _provenance_tiers = [
        "tier_0_exact",
        "tier_1_annotation",
        "tier_2_model",
        "tier_3_heuristic",
    ]

    _print_category_histogram(
        "LABEL CATEGORY DISTRIBUTION",
        _label_categories,
        report.label_category_counts,
        total_fields,
    )
    _print_category_histogram(
        "PROVENANCE TIER DISTRIBUTION",
        _provenance_tiers,
        report.provenance_tier_counts,
        total_fields,
    )

    # --- Per-Field Breakdown ---
    print(f"  {'PER-FIELD CONFIDENCE & SOFT LABEL BREAKDOWN':─<50}")
    fields = [
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
    for field_name in fields:
        label_tag = _get_field_label_tag(report, field_name)
        conf_values = report.field_confidence_sums.get(field_name, [])
        conf_str = format_confidence_band(conf_values)
        print(f"  {field_name:22s} [{label_tag:5s}] {conf_str}")
    print()

    # --- Layout Detection Statistics ---
    layout_counts = [s.layout_detection_count for s in report.samples]
    layout_confs = [
        s.layout_avg_confidence
        for s in report.samples
        if s.layout_avg_confidence is not None
    ]

    if any(c > 0 for c in layout_counts):
        avg_count = sum(layout_counts) / len(layout_counts)
        avg_conf = sum(layout_confs) / len(layout_confs) if layout_confs else 0

        print(f"  {'LAYOUT DETECTION STATISTICS':─<50}")
        print(f"  Avg detections per sample: {avg_count:.1f}")
        print(f"  Avg detection confidence:  {avg_conf:.3f}")
        print(
            f"  Samples with detections:   {sum(1 for c in layout_counts if c > 0)}/{len(layout_counts)}"
        )
        print()

    _print_language_summary(report)
    _print_text_quality_summary(report)
    _print_training_readiness(report, total_fields)


def print_sample_detail(report: DatasetReport, num_samples: int = 3) -> None:
    """Print detailed per-sample analysis for the first N samples."""
    print(f"\n  {'SAMPLE DETAIL (first ' + str(num_samples) + ' samples)':─<50}")

    for sample in report.samples[:num_samples]:
        rs = sample.reliability_summary
        composite_tag = rs.min_confidence_category if rs else "n/a"
        bottleneck = rs.min_confidence_field if rs else "n/a"
        min_conf = (
            f"{rs.min_confidence:.2f}"
            if rs and rs.min_confidence is not None
            else "null"
        )

        print(f"\n  Sample: {sample.sample_id[:12]}...")
        print(
            f"  COMPOSITE: [{composite_tag}]  min_conf={min_conf}  "
            f"bottleneck={bottleneck}"
        )
        print(f"  Layout detections: {sample.layout_detection_count}")
        for fa in sample.field_assessments:
            soft_tag = "SOFT" if fa.is_soft_label else "HARD"
            conf_str = f"{fa.confidence:.2f}" if fa.confidence is not None else "null"
            marker = " <-- min" if fa.field_name == bottleneck else ""
            print(
                f"    {fa.field_name:22s} conf={conf_str:>5s}  "
                f"tier={fa.provenance_tier:20s}  [{soft_tag:4s}]  "
                f"-> {fa.label_category}{marker}"
            )


def resolve_metadata_path(dataset_name: str, metadata_dir: Path) -> Path | None:
    """Resolve a dataset name to its metadata JSON file path."""
    # Try canonical name patterns
    candidates = [
        metadata_dir / f"{dataset_name}_metadata.json",
        metadata_dir / f"{dataset_name.replace('-', '_')}_metadata.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def main() -> None:
    """Run soft label reliability analysis on specified datasets."""
    parser = argparse.ArgumentParser(
        description="Soft Label Reliability Analysis for Layer 2 Enrichment v2"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["funsd", "sroie"],
        help="Dataset names to analyze (default: funsd sroie)",
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/metadata_registry/json"),
        help="Directory containing Layer 2 metadata JSON files",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        default=True,
        help="Show per-sample detail for first 3 samples (default: True)",
    )
    parser.add_argument(
        "--num-detail-samples",
        type=int,
        default=3,
        help="Number of samples to show in detail view (default: 3)",
    )

    args = parser.parse_args()

    print("\nSoft Label Reliability Analysis v2.0")
    print("Schema: layer2_enrichment_v2.schema.json")
    print(
        f"Thresholds: hard>={HARD_LABEL_THRESHOLD} soft>={SOFT_LABEL_THRESHOLD} "
        f"active>={ACTIVE_LEARNING_THRESHOLD}"
    )
    print(f"Metadata dir: {args.metadata_dir}")

    for dataset_name in args.datasets:
        metadata_path = resolve_metadata_path(dataset_name, args.metadata_dir)
        if metadata_path is None:
            print(f"\nWARNING: No metadata found for '{dataset_name}'")
            continue

        report = analyze_dataset(metadata_path)
        print_report(report)

        if args.detail:
            print_sample_detail(report, args.num_detail_samples)


if __name__ == "__main__":
    main()
