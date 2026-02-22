#!/usr/bin/env python3
"""Compute quality scorecard for Layer 2 metadata audits.

Reads existing JSON audit artifacts and computes a weighted quality grade
per dataset based on the 7-dimension rubric in config/audit_scorecard.yaml.

v2.0 dimensions: field_coverage (15%), field_validity (15%),
doc_completeness (5%), defect_rate (10%), cross_source_agreement (15%),
label_accuracy (20%), confidence_quality (20%).

Usage:
    # Score a single dataset
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/compute_scorecard.py --dataset jssoda

    # Score all datasets with audit results
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/compute_scorecard.py --all-datasets

    # Score and update the tracking index
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/compute_scorecard.py --all-datasets --update-index
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCORECARD_CONFIG_PATH = PROJECT_ROOT / "config" / "audit_scorecard.yaml"
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"
DATASET_DOCS_DIR = PROJECT_ROOT / "docs" / "datasets" / "source"
TRACKING_INDEX_PATH = PROJECT_ROOT / "docs" / "datasets" / "AUDIT_TRACKING_INDEX.md"


# -------------------------------------------------------------------
# Config loader
# -------------------------------------------------------------------
def load_scorecard_config(path: Path | None = None) -> dict[str, Any]:
    """Load the scorecard YAML configuration.

    Args:
        path: Override path to scorecard YAML. Defaults to
            config/audit_scorecard.yaml.

    Returns:
        Parsed YAML config dict.
    """
    config_path = path or SCORECARD_CONFIG_PATH
    if not config_path.is_file():
        log.error("Scorecard config not found: %s", config_path)
        sys.exit(1)
    with config_path.open() as f:
        return yaml.safe_load(f)


# -------------------------------------------------------------------
# Dimension scorers
# -------------------------------------------------------------------
def _load_per_field_pass_rates(screening_path: Path) -> dict[str, float] | None:
    """Load per-field pass rates from automated_screening.json.

    Args:
        screening_path: Path to automated_screening.json.

    Returns:
        Dict mapping field names to pass rates (0-100), or None if missing.
    """
    if not screening_path.is_file():
        return None

    with screening_path.open() as f:
        data = json.load(f)

    per_field = data.get("per_field_results", {})
    if not per_field:
        return None

    rates: dict[str, float] = {}
    for field_name, stats in per_field.items():
        total = stats.get("pass", 0) + stats.get("fail", 0)
        if total > 0:
            rates[field_name] = stats["pass"] / total * 100
        else:
            rates[field_name] = 0.0
    return rates


def compute_field_coverage(
    screening_path: Path,
    config: dict[str, Any] | None = None,
) -> float | None:
    """Compute field coverage score from automated_screening.json.

    v2.0: Weighted average of core (70%) and extended (30%) pass rates
    across 45 prescreening fields. Falls back to simple average if
    core/extended data not available (old screening artifacts).

    Args:
        screening_path: Path to automated_screening.json.
        config: Scorecard config (for field lists).

    Returns:
        Score 0-100, or None if artifact missing.
    """
    if not screening_path.is_file():
        log.warning("  automated_screening.json not found: %s", screening_path)
        return None

    with screening_path.open() as f:
        data = json.load(f)

    # v2.0: Use pre-computed core/extended pass rates if available
    core_rate = data.get("core_pass_rate_pct")
    ext_rate = data.get("extended_pass_rate_pct")

    if core_rate is not None and ext_rate is not None:
        score = core_rate * 0.7 + ext_rate * 0.3
        log.info(
            "  field_coverage: %.1f/100 (core=%.1f%%, ext=%.1f%%)",
            score,
            core_rate,
            ext_rate,
        )
        return round(score, 2)

    # Fallback: simple average across all fields (backward compat)
    rates = _load_per_field_pass_rates(screening_path)
    if rates is None:
        return None

    total_fields = len(rates)
    score = sum(rates.values()) / max(total_fields, 1)
    log.info(
        "  field_coverage: %.1f/100 (%d fields, avg pass rate %.1f%%)",
        score,
        total_fields,
        score,
    )
    return round(score, 2)


def _extract_validity_from_summary(
    field_summary: dict[str, Any],
) -> list[float]:
    """Extract validity percentages from field_summary format."""
    return [
        info["validity_pct"]
        for info in field_summary.values()
        if isinstance(info, dict) and "validity_pct" in info
    ]


def _extract_validity_from_per_field(
    per_field: dict[str, Any],
) -> list[float]:
    """Extract validity percentages from per_field_results format."""
    pcts: list[float] = []
    for info in per_field.values():
        if not isinstance(info, dict):
            continue
        total = info.get("valid", 0) + info.get("invalid", 0)
        if total > 0:
            pcts.append(info["valid"] / total * 100)
    return pcts


def compute_field_validity(compliance_path: Path) -> float | None:
    """Compute field validity score from compliance.json.

    Score = average validity percentage across field groups.

    Args:
        compliance_path: Path to compliance.json.

    Returns:
        Score 0-100, or None if artifact missing.
    """
    if not compliance_path.is_file():
        log.warning("  compliance.json not found: %s", compliance_path)
        return None

    with compliance_path.open() as f:
        data = json.load(f)

    validity_pcts = _extract_validity_from_summary(data.get("field_summary", {}))
    if not validity_pcts:
        validity_pcts = _extract_validity_from_per_field(
            data.get("per_field_results", {})
        )

    if not validity_pcts:
        log.warning("  Could not extract validity scores from compliance.json")
        return None

    score = sum(validity_pcts) / len(validity_pcts)
    log.info("  field_validity: %.1f/100 (%d fields)", score, len(validity_pcts))
    return round(score, 2)


_EXPECTED_SECTIONS: list[str] = [
    "overview",
    "statistics",
    "format",
    "label",
    "iqa",
    "limitation",
    "license",
    "layer 2",
    "reliability",
    "processing",
    "version history",
]


def _heading_level(line: str) -> int:
    """Return the heading level (1-6) of a markdown heading, or 0 if not a heading."""
    match = re.match(r"^(#{1,6})\s+", line.strip())
    return len(match.group(1)) if match else 0


def _section_has_content(lines: list[str], heading_idx: int) -> bool:
    """Check whether the section starting at *heading_idx* has body content.

    Searches the entire sub-tree (including within sub-headings) for any
    non-heading, non-separator body text.  Only stops at a heading of the
    same or higher level as the target section, which marks the start of
    a sibling or parent section.
    """
    section_level = _heading_level(lines[heading_idx])
    if section_level == 0:
        return False

    for j in range(heading_idx + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped or stripped.startswith("---"):
            continue
        current_level = _heading_level(stripped)
        # A same-level or higher-level heading means we've left this section
        if current_level and current_level <= section_level:
            break
        # Sub-headings (deeper level) are part of this section -- skip them
        if current_level:
            continue
        # Non-heading, non-empty, non-separator line = body content
        return True
    return False


def _count_populated_sections(lines: list[str]) -> int:
    """Count how many expected sections have body content."""
    populated = 0
    for keyword in _EXPECTED_SECTIONS:
        for i, line in enumerate(lines):
            if re.match(r"^#{1,6}\s+", line) and keyword.lower() in line.lower():
                if _section_has_content(lines, i):
                    populated += 1
                break
    return populated


def compute_doc_completeness(source_doc_path: Path) -> float | None:
    """Compute documentation completeness score.

    Score = populated sections / total expected sections * 100.
    A section counts as populated if it has content beyond the heading.

    Args:
        source_doc_path: Path to docs/datasets/source/{dataset}.md.

    Returns:
        Score 0-100, or None if doc missing.
    """
    if not source_doc_path.is_file():
        log.warning("  Source doc not found: %s", source_doc_path)
        return None

    content = source_doc_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    populated = _count_populated_sections(lines)
    total = len(_EXPECTED_SECTIONS)
    score = populated / total * 100
    log.info(
        "  doc_completeness: %.1f/100 (%d/%d sections populated)",
        score,
        populated,
        total,
    )
    return round(score, 2)


def compute_defect_rate(
    catalog_path: Path,
    config: dict[str, Any],
) -> float | None:
    """Compute defect rate score from defect_catalog.json.

    Score = max(0, 100 - sum(open_defect_penalties)).
    Resolved defects don't count. Deferred defects count at 0.3 weight.

    Args:
        catalog_path: Path to defect_catalog.json.
        config: Scorecard config with defect_penalties and status_weights.

    Returns:
        Score 0-100, or None if artifact missing.
    """
    if not catalog_path.is_file():
        log.warning("  defect_catalog.json not found: %s", catalog_path)
        return None

    with catalog_path.open() as f:
        data = json.load(f)

    defects = data.get("defects", [])
    if not defects:
        log.info("  defect_rate: 100.0/100 (no defects)")
        return 100.0

    dim_config = config.get("dimensions", {}).get("defect_rate", {})
    penalties = dim_config.get(
        "defect_penalties",
        {
            "critical": 15,
            "high": 10,
            "medium": 5,
            "low": 2,
        },
    )
    status_weights = dim_config.get(
        "status_weights",
        {
            "RESOLVED": 0.0,
            "ACCEPTED": 0.1,
            "DEFERRED": 0.3,
            "PARTIALLY_RESOLVED": 0.5,
            "OPEN": 1.0,
        },
    )

    total_penalty = 0.0
    for defect in defects:
        status = defect.get("status", "OPEN").upper()
        status_weight = status_weights.get(status, 1.0)

        # Determine severity from extrapolation_risk or fix_complexity
        risk = defect.get("extrapolation_risk", "").upper()
        if "CRITICAL" in risk:
            severity = "critical"
        elif "HIGH" in risk:
            severity = "high"
        elif "MEDIUM" in risk:
            severity = "medium"
        else:
            severity = "low"

        penalty = penalties.get(severity, 2) * status_weight
        total_penalty += penalty

    score = max(0.0, 100.0 - total_penalty)
    log.info(
        "  defect_rate: %.1f/100 (%d defects, %.1f penalty)",
        score,
        len(defects),
        total_penalty,
    )
    return round(score, 2)


_EXCLUDED_PAIR_FIELDS: dict[str, frozenset[str]] = {
    # Docling/Egret layout models hardcode has_handwriting=False (no handwriting
    # class), so comparing against L2 metadata is always a false disagreement.
    "has_handwriting": frozenset({"docling_layout", "egret_layout"}),
    # Detection counts from different models are inherently different; comparing
    # raw counts across models is not a meaningful quality signal.
    "layout_class_count": frozenset({"docling_layout", "egret_layout"}),
    # image_id_derived split is a heuristic that only works for datasets with
    # ``{split}_`` prefixed filenames.  Comparing against L2 metadata produces
    # false disagreements when the naming convention doesn't match.
    "split": frozenset({"image_id_derived"}),
}
"""Source names that should be excluded from cross-source agreement scoring
for specific fields because the comparison is methodologically invalid."""


def _pair_excluded(field_name: str, pair_label: str) -> bool:
    """Return True if this (field, pair) should be skipped in scoring.

    ``pair_label`` has the form ``"source_a vs source_b"``.
    """
    excluded_sources = _EXCLUDED_PAIR_FIELDS.get(field_name)
    if not excluded_sources:
        return False
    return any(src in pair_label for src in excluded_sources)


def _collect_pairwise_agreements(
    samples: list[dict[str, Any]],
) -> dict[str, list[bool]]:
    """Collect pairwise match booleans from comparison report samples.

    Pairs listed in ``_EXCLUDED_PAIR_FIELDS`` are skipped because the
    comparison is methodologically invalid (e.g. layout models that lack
    a handwriting class, or detection count comparisons across models).
    """
    field_agreements: dict[str, list[bool]] = {}
    for sample in samples:
        for field_name, field_data in sample.get("fields", {}).items():
            for pair_label, matches in field_data.get("pairwise_matches", {}).items():
                if isinstance(matches, bool) and not _pair_excluded(
                    field_name, pair_label
                ):
                    field_agreements.setdefault(field_name, []).append(matches)
    return field_agreements


def _compute_fallback_agreement(samples: list[dict[str, Any]]) -> float | None:
    """Compute agreement by checking if all non-null source values match.

    Sources listed in ``_EXCLUDED_PAIR_FIELDS`` for the given field are
    removed before comparison.
    """
    total_comparisons = 0
    agreements = 0
    for sample in samples:
        for field_name, field_data in sample.get("fields", {}).items():
            excluded_sources = _EXCLUDED_PAIR_FIELDS.get(field_name, frozenset())
            non_null = [
                v
                for src, v in field_data.get("sources", {}).items()
                if v is not None and src not in excluded_sources
            ]
            if len(non_null) < 2:
                continue
            total_comparisons += 1
            if len({str(v) for v in non_null}) == 1:
                agreements += 1
    if total_comparisons == 0:
        return None
    return agreements / total_comparisons * 100


def _compute_field_agreement_score(
    field_agreements: dict[str, list[bool]],
) -> float | None:
    """Compute mean agreement rate across fields from pairwise matches."""
    field_rates = [
        sum(matches) / len(matches) * 100
        for matches in field_agreements.values()
        if matches
    ]
    if not field_rates:
        return None
    return sum(field_rates) / len(field_rates)


def compute_cross_source_agreement(
    comparison_path: Path,
) -> float | None:
    """Compute cross-source agreement from comparison_report.json.

    Score = mean pairwise agreement rate across compared fields.

    Args:
        comparison_path: Path to comparison_report.json.

    Returns:
        Score 0-100, or None if artifact missing or single-source.
    """
    if not comparison_path.is_file():
        log.warning("  comparison_report.json not found: %s", comparison_path)
        return None

    with comparison_path.open() as f:
        data = json.load(f)

    meta = data.get("report_metadata", {})
    sources = meta.get("sources_discovered", [])
    if len(sources) < 2:
        log.warning("  Only %d sources - cross-source agreement N/A", len(sources))
        return None

    samples = data.get("samples", [])
    if not samples:
        log.warning("  No samples in comparison report")
        return None

    field_agreements = _collect_pairwise_agreements(samples)

    if field_agreements:
        score = _compute_field_agreement_score(field_agreements)
    else:
        score = _compute_fallback_agreement(samples)

    if score is None:
        log.warning("  No multi-source comparisons available")
        return None

    log.info("  cross_source_agreement: %.1f/100", score)
    return round(score, 2)


def compute_vlm_accuracy(
    vlm_path: Path,
    catalog_path: Path,
) -> float | None:
    """Compute VLM accuracy from vlm_corrections.json or defect_catalog.json.

    Score = passing sample accuracy rate * 100.

    Args:
        vlm_path: Path to vlm_corrections.json.
        catalog_path: Path to defect_catalog.json (fallback for VLM data).

    Returns:
        Score 0-100, or None if no VLM data.
    """
    # Try vlm_corrections.json first
    if vlm_path.is_file():
        with vlm_path.open() as f:
            data = json.load(f)
        passing_accuracy = data.get("passing_sample_accuracy")
        if passing_accuracy is not None:
            score = float(passing_accuracy) * 100
            log.info("  vlm_accuracy: %.1f/100 (from vlm_corrections.json)", score)
            return round(score, 2)

    # Fallback: extract from defect_catalog.json vlm_validation section
    if catalog_path.is_file():
        with catalog_path.open() as f:
            data = json.load(f)
        vlm_val = data.get("vlm_validation", {})
        passing_accuracy = vlm_val.get("passing_sample_accuracy")
        if passing_accuracy is not None:
            score = float(passing_accuracy) * 100
            log.info("  vlm_accuracy: %.1f/100 (from defect_catalog)", score)
            return round(score, 2)

    log.warning("  VLM accuracy data not found")
    return None


def _extract_accuracy_pct(rate: Any) -> float:
    """Extract accuracy percentage from various accuracy_by_field formats.

    Handles multiple accuracy_by_field value formats:
    - Dict with 'accuracy_pct' key (0-100): use directly.
    - Dict with 'pct' key (0-100): use directly.
    - Dict with 'correct'/'incorrect' counts: compute percentage.
    - Float (0-1 scale): multiply by 100 to get percentage.
    - Float (>1): treat as already a percentage.

    Args:
        rate: A float, int, or dict with accuracy data.

    Returns:
        Accuracy as percentage (0-100).
    """
    if isinstance(rate, dict):
        # Prefer explicit percentage keys
        if "accuracy_pct" in rate:
            return float(rate["accuracy_pct"])
        if "pct" in rate:
            return float(rate["pct"])
        # Compute from correct/incorrect counts
        correct = rate.get("correct")
        incorrect = rate.get("incorrect")
        if isinstance(correct, (int, float)) and isinstance(incorrect, (int, float)):
            total = correct + incorrect
            return (correct / total * 100) if total > 0 else 0.0
        return 0.0
    val = float(rate)
    # Values 0-1 are fractions; larger values are already percentages
    if 0.0 <= val <= 1.0:
        return val * 100
    return val


def compute_label_accuracy(
    vlm_path: Path,
    catalog_path: Path,
    config: dict[str, Any] | None = None,
) -> float | None:
    """Compute per-field label accuracy from VLM corrections.

    v2.0: Weighted average of per-field accuracy rates.
    Critical fields (60%): iso639_language, script_family, domain_level1, capture_method.
    Structural fields (40%): orientation, handwriting, content flags.

    Falls back to passing_sample_accuracy if per-field data unavailable.

    Args:
        vlm_path: Path to vlm_corrections.json.
        catalog_path: Path to defect_catalog.json (fallback).
        config: Scorecard config.

    Returns:
        Score 0-100, or None if no VLM data.
    """
    dim_config = (config or {}).get("dimensions", {}).get("label_accuracy", {})
    critical_fields = dim_config.get(
        "critical_fields",
        ["iso639_language", "script_family", "domain_level1", "capture_method"],
    )
    structural_fields = dim_config.get(
        "structural_fields",
        [
            "orientation_class",
            "handwriting_present",
            "has_table",
            "has_formula",
            "has_figure",
            "has_handwriting",
        ],
    )
    critical_weight = dim_config.get("critical_weight", 0.60)
    structural_weight = dim_config.get("structural_weight", 0.40)

    vlm_data: dict[str, Any] = {}
    if vlm_path.is_file():
        with vlm_path.open() as f:
            vlm_data = json.load(f)

    # Try per-field accuracy from accuracy_by_field
    accuracy_by_field = vlm_data.get("accuracy_by_field", {})
    if not accuracy_by_field:
        # Also try validation_summary
        val_summary = vlm_data.get("validation_summary", {})
        accuracy_by_field = val_summary.get("accuracy_by_field", {})

    if accuracy_by_field:
        # Compute weighted average
        crit_rates: list[float] = []
        for field in critical_fields:
            rate = accuracy_by_field.get(field)
            if rate is not None:
                crit_rates.append(_extract_accuracy_pct(rate))

        struct_rates: list[float] = []
        for field in structural_fields:
            rate = accuracy_by_field.get(field)
            if rate is not None:
                struct_rates.append(_extract_accuracy_pct(rate))

        if crit_rates or struct_rates:
            crit_avg = sum(crit_rates) / len(crit_rates) if crit_rates else 0.0
            struct_avg = sum(struct_rates) / len(struct_rates) if struct_rates else 0.0

            # Adjust weights if one group has no data
            if crit_rates and struct_rates:
                score = crit_avg * critical_weight + struct_avg * structural_weight
            elif crit_rates:
                score = crit_avg
            else:
                score = struct_avg

            log.info(
                "  label_accuracy: %.1f/100 (critical=%.1f, structural=%.1f)",
                score,
                crit_avg,
                struct_avg,
            )
            return round(score, 2)

    # Fallback: use passing_sample_accuracy
    passing_accuracy = vlm_data.get("passing_sample_accuracy")
    if passing_accuracy is not None:
        score = float(passing_accuracy) * 100
        log.info(
            "  label_accuracy: %.1f/100 (fallback: passing_sample_accuracy)", score
        )
        return round(score, 2)

    # Try defect_catalog fallback
    if catalog_path.is_file():
        with catalog_path.open() as f:
            catalog_data = json.load(f)
        vlm_val = catalog_data.get("vlm_validation", {})
        passing_accuracy = vlm_val.get("passing_sample_accuracy")
        if passing_accuracy is not None:
            score = float(passing_accuracy) * 100
            log.info(
                "  label_accuracy: %.1f/100 (fallback: defect_catalog)",
                score,
            )
            return round(score, 2)

    log.warning("  Label accuracy data not found")
    return None


# Confidence-related field names for the confidence_quality dimension
CONFIDENCE_FIELDS: list[str] = [
    "reliability_summary_present",
    "reliability_min_confidence_category",
    "reliability_assessed_count",
    "reliability_min_confidence",
    "reliability_hard_label_ratio",
    "capture_confidence_valid",
    "domain_confidence_valid",
    "language_confidence_valid",
    "content_flag_confidence_present",
    "handwriting_confidence_valid",
    "structure_confidence_present",
    "orientation_confidence_valid",
    "skew_confidence_valid",
]


def compute_confidence_quality(
    screening_path: Path,
    config: dict[str, Any] | None = None,
) -> float | None:
    """Compute confidence quality score from prescreening pass rates.

    v2.0: Mean pass rate across 13 confidence-related prescreening fields.

    Args:
        screening_path: Path to automated_screening.json.
        config: Scorecard config.

    Returns:
        Score 0-100, or None if no confidence fields available.
    """
    rates = _load_per_field_pass_rates(screening_path)
    if rates is None:
        log.warning("  automated_screening.json not found for confidence quality")
        return None

    dim_config = (config or {}).get("dimensions", {}).get("confidence_quality", {})
    conf_fields = dim_config.get("confidence_fields", CONFIDENCE_FIELDS)

    field_rates: list[float] = []
    for field in conf_fields:
        rate = rates.get(field)
        if rate is not None:
            field_rates.append(rate)

    if not field_rates:
        log.warning("  No confidence fields found in prescreening results")
        return None

    score = sum(field_rates) / len(field_rates)
    log.info(
        "  confidence_quality: %.1f/100 (%d/%d fields)",
        score,
        len(field_rates),
        len(conf_fields),
    )
    return round(score, 2)


def _load_content_flag_fp_rates(
    vlm_path: Path,
) -> dict[str, float] | None:
    """Load per-flag false positive rates from VLM corrections.

    Args:
        vlm_path: Path to vlm_corrections.json.

    Returns:
        Dict mapping flag names to FP rates (0-100), or None.
    """
    if not vlm_path.is_file():
        return None

    with vlm_path.open() as f:
        data = json.load(f)

    # Check for content flag analysis in supported locations
    content_flag_analysis = data.get("content_flag_analysis", {})
    if not content_flag_analysis:
        # Try track_a_analysis
        track_a = data.get("track_a_analysis", {})
        content_flag_analysis = track_a.get("content_flag_analysis", {})
    if not content_flag_analysis:
        # Try v2 schema location under validation_summary
        validation_summary = data.get("validation_summary", {})
        content_flag_analysis = validation_summary.get("content_flag_analysis", {})

    if not content_flag_analysis:
        return None

    fp_rates: dict[str, float] = {}
    for flag_name, flag_data in content_flag_analysis.items():
        if isinstance(flag_data, dict):
            rate_pct: float | None = None

            # Prefer explicit percentage fields (already 0-100)
            if "fp_rate_pct" in flag_data:
                try:
                    rate_pct = float(flag_data["fp_rate_pct"])
                except (TypeError, ValueError):
                    rate_pct = None
            elif "pct" in flag_data:
                try:
                    rate_pct = float(flag_data["pct"])
                except (TypeError, ValueError):
                    rate_pct = None
            else:
                fp_rate = flag_data.get("false_positive_rate")
                if fp_rate is not None:
                    try:
                        fp_rate_f = float(fp_rate)
                    except (TypeError, ValueError):
                        fp_rate_f = None
                    if fp_rate_f is not None:
                        # Values 0-1 are fractions; larger values are percentages
                        if 0.0 <= fp_rate_f <= 1.0:
                            rate_pct = fp_rate_f * 100.0
                        else:
                            rate_pct = fp_rate_f

            if rate_pct is not None:
                fp_rates[flag_name] = rate_pct
    return fp_rates if fp_rates else None


# -------------------------------------------------------------------
# Overall scorecard computation
# -------------------------------------------------------------------
def _apply_grade_cap(
    grade: str,
    max_grade: str,
    reason: str,
    existing_cap: str | None,
) -> tuple[str, str | None]:
    """Apply a grade cap, stacking with existing caps.

    Args:
        grade: Current grade letter.
        max_grade: Maximum allowed grade.
        reason: Reason for the cap.
        existing_cap: Existing cap message or None.

    Returns:
        Tuple of (new_grade, updated_cap_message).
    """
    grade_order = ["A", "B", "C", "D", "F"]
    if grade_order.index(grade) < grade_order.index(max_grade):
        cap_msg = f"Grade capped from {grade} to {max_grade}: {reason}"
        log.warning("  GRADE CAPPED: %s", cap_msg)
        new_cap = f"{existing_cap} | {cap_msg}" if existing_cap else cap_msg
        return max_grade, new_cap
    return grade, existing_cap


def compute_overall(
    dimension_scores: dict[str, float | None],
    config: dict[str, Any],
    *,
    screening_path: Path | None = None,
    vlm_path: Path | None = None,
) -> dict[str, Any]:
    """Compute the overall weighted score and grade.

    Missing dimensions have their weight redistributed proportionally.
    v2.0: Handles 7 dimensions + 8 grade caps.

    Args:
        dimension_scores: Per-dimension scores (0-100) or None.
        config: Full scorecard config.
        screening_path: Path to automated_screening.json for cap checks.
        vlm_path: Path to vlm_corrections.json for content flag FP caps.

    Returns:
        Dict with overall score, grade, per-dimension details,
        and effective weights.
    """
    dimensions = config.get("dimensions", {})
    thresholds = config.get("grade_thresholds", {})

    # Separate available and excluded dimensions
    available: dict[str, tuple[float, float]] = {}  # name -> (weight, score)
    excluded: list[str] = []

    for dim_name, dim_config in dimensions.items():
        weight = dim_config.get("weight", 0.0)
        score = dimension_scores.get(dim_name)
        if score is not None:
            available[dim_name] = (weight, score)
        else:
            excluded.append(dim_name)

    if not available:
        return {
            "overall_score": 0.0,
            "grade": "F",
            "dimensions": {},
            "excluded_dimensions": list(dimensions.keys()),
            "effective_weights": {},
            "note": "No dimensions could be computed",
        }

    # Redistribute excluded weights (only from optional dimensions)
    # Required dimensions (e.g., label_accuracy) are never redistributed;
    # their weight stays in the denominator so missing required data
    # naturally depresses the overall score (scored as 0).
    missing_optional_weight = sum(
        dimensions[d].get("weight", 0.0)
        for d in excluded
        if not dimensions[d].get("required", False)
    )
    missing_required_weight = sum(
        dimensions[d].get("weight", 0.0)
        for d in excluded
        if dimensions[d].get("required", False)
    )
    available_weight_sum = sum(w for w, _ in available.values())
    full_weight_sum = (
        available_weight_sum + missing_optional_weight + missing_required_weight
    )
    effective_weights: dict[str, float] = {}
    for dim_name, (weight, _score) in available.items():
        # Each available dimension gets its original weight plus a
        # proportional share of the redistributable (optional) weight.
        redistribution_share = (
            (weight / available_weight_sum) * missing_optional_weight
            if available_weight_sum > 0
            else 0.0
        )
        effective_weights[dim_name] = (
            (weight + redistribution_share) / full_weight_sum
            if full_weight_sum > 0
            else 0.0
        )
    # Missing required dimensions keep their weight (scored as 0).
    for d in excluded:
        if dimensions[d].get("required", False):
            effective_weights[d] = (
                dimensions[d].get("weight", 0.0) / full_weight_sum
                if full_weight_sum > 0
                else 0.0
            )

    # Compute weighted score
    overall = 0.0
    dim_details: dict[str, dict[str, Any]] = {}
    for dim_name, (original_weight, score) in available.items():
        eff_weight = effective_weights[dim_name]
        weighted = score * eff_weight
        overall += weighted
        dim_details[dim_name] = {
            "score": score,
            "original_weight": original_weight,
            "effective_weight": round(eff_weight, 4),
            "weighted_contribution": round(weighted, 2),
        }

    # Determine grade
    grade = "F"
    for grade_letter in ["A", "B", "C", "D"]:
        threshold = thresholds.get(grade_letter, 0)
        if overall >= threshold:
            grade = grade_letter
            break

    # ---------------------------------------------------------------
    # Enforce grade caps
    # ---------------------------------------------------------------
    grade_caps = config.get("grade_caps", {})
    grade_cap_applied: str | None = None

    # Cap 1: Missing VLM inspection -> max D
    # Check actual VLM file existence rather than dimension exclusion,
    # because defect_catalog fallback can produce a score even without VLM.
    vlm_file_exists = vlm_path is not None and vlm_path.is_file()
    label_acc_config = dimensions.get("label_accuracy", {})
    vlm_acc_config = dimensions.get("vlm_accuracy", {})
    label_required = label_acc_config.get("required", False)
    vlm_required = vlm_acc_config.get("required", False)
    if (label_required or vlm_required) and not vlm_file_exists:
        cap_rule = grade_caps.get("missing_vlm_accuracy", {})
        max_g = cap_rule.get("max_grade", "D")
        reason = cap_rule.get("reason", "").strip()
        grade, grade_cap_applied = _apply_grade_cap(
            grade, max_g, f"VLM inspection not performed. {reason}", grade_cap_applied
        )

    # Cap 2: Low critical field coverage -> max D
    crit_cap = grade_caps.get("low_critical_field_coverage", {})
    crit_fields: list[str] = crit_cap.get("fields", [])
    crit_threshold: float = crit_cap.get("threshold_pct", 75)
    if crit_fields and screening_path is not None:
        per_field_rates = _load_per_field_pass_rates(screening_path)
        if per_field_rates is not None:
            failing_fields: list[str] = []
            for fname in crit_fields:
                rate = per_field_rates.get(fname, 0.0)
                if rate < crit_threshold:
                    failing_fields.append(f"{fname}={rate:.0f}%")
            if failing_fields:
                crit_max = crit_cap.get("max_grade", "D")
                crit_reason = crit_cap.get("reason", "").strip()
                msg = (
                    f"Critical fields below {crit_threshold:.0f}%: "
                    f"{', '.join(failing_fields)}. {crit_reason}"
                )
                grade, grade_cap_applied = _apply_grade_cap(
                    grade, crit_max, msg, grade_cap_applied
                )

    # Cap 3: Low label accuracy -> max C
    label_acc_cap = grade_caps.get("low_label_accuracy", {})
    label_acc_threshold = label_acc_cap.get("threshold_pct", 70)
    label_acc_score = dimension_scores.get("label_accuracy")
    if label_acc_score is not None and label_acc_score < label_acc_threshold:
        max_g = label_acc_cap.get("max_grade", "C")
        reason = label_acc_cap.get("reason", "").strip()
        grade, grade_cap_applied = _apply_grade_cap(
            grade,
            max_g,
            f"label_accuracy={label_acc_score:.1f}% (min {label_acc_threshold}%). {reason}",
            grade_cap_applied,
        )

    # Cap 4/5: Content flag FP rates -> max C or D
    if vlm_path is not None:
        fp_rates = _load_content_flag_fp_rates(vlm_path)
        if fp_rates is not None:
            # Check critical FP cap (>80% -> D)
            fp_crit_cap = grade_caps.get("high_content_flag_fp_rate_critical", {})
            fp_crit_threshold = fp_crit_cap.get("threshold_pct", 80)
            crit_flags = [
                f"{f}={r:.0f}%" for f, r in fp_rates.items() if r > fp_crit_threshold
            ]
            if crit_flags:
                max_g = fp_crit_cap.get("max_grade", "D")
                reason = fp_crit_cap.get("reason", "").strip()
                msg = (
                    f"Content flag FP >{fp_crit_threshold}%: "
                    f"{', '.join(crit_flags)}. {reason}"
                )
                grade, grade_cap_applied = _apply_grade_cap(
                    grade, max_g, msg, grade_cap_applied
                )

            # Check warning FP cap (>50% -> C)
            fp_warn_cap = grade_caps.get("high_content_flag_fp_rate_warning", {})
            fp_warn_threshold = fp_warn_cap.get("threshold_pct", 50)
            warn_flags = [
                f"{f}={r:.0f}%" for f, r in fp_rates.items() if r > fp_warn_threshold
            ]
            if warn_flags:
                max_g = fp_warn_cap.get("max_grade", "C")
                reason = fp_warn_cap.get("reason", "").strip()
                msg = (
                    f"Content flag FP >{fp_warn_threshold}%: "
                    f"{', '.join(warn_flags)}. {reason}"
                )
                grade, grade_cap_applied = _apply_grade_cap(
                    grade, max_g, msg, grade_cap_applied
                )
        elif vlm_file_exists:
            # VLM file exists but no content flag analysis -> cap at C
            missing_cf_cap = grade_caps.get("missing_content_flag_inspection", {})
            max_g = missing_cf_cap.get("max_grade", "C")
            reason = missing_cf_cap.get("reason", "").strip()
            grade, grade_cap_applied = _apply_grade_cap(
                grade,
                max_g,
                f"No content flag inspection data. {reason}",
                grade_cap_applied,
            )

    # Cap 6: Low confidence quality -> max B
    conf_cap = grade_caps.get("low_confidence_quality", {})
    conf_threshold = conf_cap.get("threshold_pct", 60)
    conf_score = dimension_scores.get("confidence_quality")
    if conf_score is not None and conf_score < conf_threshold:
        max_g = conf_cap.get("max_grade", "B")
        reason = conf_cap.get("reason", "").strip()
        grade, grade_cap_applied = _apply_grade_cap(
            grade,
            max_g,
            f"confidence_quality={conf_score:.1f}% (min {conf_threshold}%). {reason}",
            grade_cap_applied,
        )

    # Cap 7: Low core prescreening pass rate -> max C
    core_cap = grade_caps.get("low_core_prescreening_pass_rate", {})
    core_threshold = core_cap.get("threshold_pct", 70)
    if screening_path is not None and screening_path.is_file():
        with screening_path.open() as f:
            screening_data = json.load(f)
        core_rate = screening_data.get("core_pass_rate_pct")
        if core_rate is not None and core_rate < core_threshold:
            max_g = core_cap.get("max_grade", "C")
            reason = core_cap.get("reason", "").strip()
            grade, grade_cap_applied = _apply_grade_cap(
                grade,
                max_g,
                f"core_pass_rate={core_rate:.1f}% (min {core_threshold}%). {reason}",
                grade_cap_applied,
            )

    result: dict[str, Any] = {
        "overall_score": round(overall, 2),
        "grade": grade,
        "dimensions": dim_details,
        "excluded_dimensions": excluded,
        "effective_weights": {k: round(v, 4) for k, v in effective_weights.items()},
    }
    if grade_cap_applied:
        result["grade_cap_applied"] = grade_cap_applied
    return result


# -------------------------------------------------------------------
# Dataset scorer
# -------------------------------------------------------------------
def score_dataset(
    dataset_name: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute the full scorecard for a single dataset.

    Args:
        dataset_name: Canonical dataset name.
        config: Scorecard YAML config.

    Returns:
        Complete scorecard dict suitable for JSON output.
    """
    results_dir = AUDIT_RESULTS_DIR / dataset_name
    if not results_dir.is_dir():
        log.warning("No audit results directory for %s", dataset_name)
        return {
            "dataset": dataset_name,
            "status": "no_audit_data",
            "computed_at": datetime.now(UTC).isoformat(),
        }

    log.info("Scoring dataset: %s", dataset_name)

    # Compute each dimension
    screening_path = results_dir / "automated_screening.json"
    # Accept both "compliance.json" (preferred) and legacy "schema_compliance_v2.json"
    compliance_path = results_dir / "compliance.json"
    if not compliance_path.is_file():
        legacy_compliance = results_dir / "schema_compliance_v2.json"
        if legacy_compliance.is_file():
            compliance_path = legacy_compliance
            log.info("  Using legacy compliance file: %s", legacy_compliance.name)
    catalog_path = results_dir / "defect_catalog.json"
    comparison_path = results_dir / "comparison_report.json"
    vlm_path = results_dir / "vlm_corrections.json"
    # Dataset results dir may use non-hyphenated name (e.g. "cocotext") while
    # the canonical doc uses hyphens (e.g. "coco-text.md").  Try exact match
    # first, then scan for files containing the base name.
    source_doc = DATASET_DOCS_DIR / f"{dataset_name}.md"
    if not source_doc.is_file():
        # Try common variations: add hyphens, remove hyphens
        for candidate in DATASET_DOCS_DIR.glob("*.md"):
            normalized = candidate.stem.replace("-", "")
            if normalized == dataset_name.replace("-", ""):
                source_doc = candidate
                log.info(
                    "  Resolved source doc: %s -> %s",
                    dataset_name,
                    candidate.name,
                )
                break

    dimension_scores: dict[str, float | None] = {
        "field_coverage": compute_field_coverage(screening_path, config),
        "field_validity": compute_field_validity(compliance_path),
        "doc_completeness": compute_doc_completeness(source_doc),
        "defect_rate": compute_defect_rate(catalog_path, config),
        "cross_source_agreement": compute_cross_source_agreement(
            comparison_path,
        ),
        "label_accuracy": compute_label_accuracy(vlm_path, catalog_path, config),
        "confidence_quality": compute_confidence_quality(screening_path, config),
    }

    overall = compute_overall(
        dimension_scores,
        config,
        screening_path=screening_path,
        vlm_path=vlm_path,
    )

    # Build metadata
    artifacts_found: list[str] = []
    for name, path in [
        ("automated_screening", screening_path),
        ("compliance", compliance_path),
        ("defect_catalog", catalog_path),
        ("comparison_report", comparison_path),
        ("vlm_corrections", vlm_path),
        ("source_doc", source_doc),
    ]:
        if path.is_file():
            artifacts_found.append(name)

    scorecard = {
        "dataset": dataset_name,
        "computed_at": datetime.now(UTC).isoformat(),
        "scorecard_config_version": config.get("version", "unknown"),
        "artifacts_found": artifacts_found,
        "dimension_scores": dict(dimension_scores.items()),
        **overall,
    }

    return scorecard


# -------------------------------------------------------------------
# Output
# -------------------------------------------------------------------
def write_scorecard(
    scorecard: dict[str, Any],
    output_path: Path,
) -> None:
    """Write scorecard JSON to disk.

    Args:
        scorecard: Computed scorecard dict.
        output_path: Target file path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(scorecard, f, indent=2, ensure_ascii=False)
    log.info("Scorecard written to %s", output_path)


def print_scorecard(scorecard: dict[str, Any]) -> None:
    """Print a human-readable scorecard summary."""
    dataset = scorecard.get("dataset", "unknown")
    grade = scorecard.get("grade", "?")
    overall = scorecard.get("overall_score", 0.0)

    print()
    print("=" * 60)
    print(f"  Quality Scorecard: {dataset}")
    print("=" * 60)
    print(f"  Overall Score: {overall:.1f}/100")
    print(f"  Grade: {grade}")
    print()

    dims = scorecard.get("dimensions", {})
    if dims:
        print(f"  {'Dimension':<28s} {'Score':>6s} {'Weight':>7s} {'Weighted':>8s}")
        print("  " + "-" * 52)
        for dim_name, detail in dims.items():
            label = dim_name.replace("_", " ").title()
            score = detail.get("score", 0)
            eff_w = detail.get("effective_weight", 0)
            weighted = detail.get("weighted_contribution", 0)
            print(f"  {label:<28s} {score:>5.1f} {eff_w:>6.2f}  {weighted:>7.2f}")
        print("  " + "-" * 52)
        print(f"  {'TOTAL':<28s} {'':>6s} {'1.00':>7s}  {overall:>7.2f}")

    excluded = scorecard.get("excluded_dimensions", [])
    if excluded:
        print()
        labels = [d.replace("_", " ").title() for d in excluded]
        print(f"  Excluded (no data): {', '.join(labels)}")

    grade_cap = scorecard.get("grade_cap_applied")
    if grade_cap:
        print()
        print(f"  !! GRADE CAP: {grade_cap}")

    print("=" * 60)
    print()


def update_tracking_index(
    scorecards: list[dict[str, Any]],
) -> None:
    """Update the AUDIT_TRACKING_INDEX.md scorecard summary table.

    Looks for the `<!-- SCORECARD_TABLE_START -->` and
    `<!-- SCORECARD_TABLE_END -->` markers and replaces the content between
    them.

    Args:
        scorecards: List of computed scorecard dicts.
    """
    if not TRACKING_INDEX_PATH.is_file():
        log.warning(
            "Tracking index not found: %s. Skipping update.",
            TRACKING_INDEX_PATH,
        )
        return

    content = TRACKING_INDEX_PATH.read_text(encoding="utf-8")

    start_marker = "<!-- SCORECARD_TABLE_START -->"
    end_marker = "<!-- SCORECARD_TABLE_END -->"

    if start_marker not in content or end_marker not in content:
        log.warning("Scorecard markers not found in tracking index")
        return

    # Build table
    lines = [
        start_marker,
        "",
        "| Dataset | Score | Grade | Cov | Valid "
        "| Doc | Defect | Agree | Label | Conf | Updated |",
        "|---------|-------|-------|-----|------"
        "|-----|--------|-------|-------|------|---------|",
    ]

    for sc in sorted(scorecards, key=lambda s: s.get("dataset", "")):
        ds = sc.get("dataset", "?")
        grade = sc.get("grade", "?")
        overall = sc.get("overall_score", 0.0)
        dim_scores = sc.get("dimension_scores", {})
        updated = sc.get("computed_at", "")[:10]

        def fmt(val: float | None) -> str:
            return f"{val:.0f}" if val is not None else "-"

        lines.append(
            f"| {ds} | {overall:.1f} | {grade} "
            f"| {fmt(dim_scores.get('field_coverage'))} "
            f"| {fmt(dim_scores.get('field_validity'))} "
            f"| {fmt(dim_scores.get('doc_completeness'))} "
            f"| {fmt(dim_scores.get('defect_rate'))} "
            f"| {fmt(dim_scores.get('cross_source_agreement'))} "
            f"| {fmt(dim_scores.get('label_accuracy'))} "
            f"| {fmt(dim_scores.get('confidence_quality'))} "
            f"| {updated} |"
        )

    lines.append("")
    lines.append(end_marker)

    # Replace content between markers
    before = content[: content.index(start_marker)]
    after = content[content.index(end_marker) + len(end_marker) :]
    new_content = before + "\n".join(lines) + after

    TRACKING_INDEX_PATH.write_text(new_content, encoding="utf-8")
    log.info("Updated tracking index: %s", TRACKING_INDEX_PATH)


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------
def _discover_datasets(dataset_arg: str | None) -> list[str] | None:
    """Return the list of datasets to score, or None if none found."""
    if dataset_arg:
        return [dataset_arg]
    datasets = sorted(
        d.name
        for d in AUDIT_RESULTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    if not datasets:
        log.error("No audit results found in %s", AUDIT_RESULTS_DIR)
        return None
    log.info("Found audit results for %d datasets", len(datasets))
    return datasets


def _print_multi_dataset_summary(scorecards: list[dict[str, Any]]) -> None:
    """Print a summary table for multi-dataset runs."""
    print("=" * 60)
    print("  Summary: All Datasets")
    print("=" * 60)
    print(f"  {'Dataset':<20s} {'Score':>6s} {'Grade':>6s}")
    print("  " + "-" * 34)
    for sc in scorecards:
        ds = sc.get("dataset", "?")
        if sc.get("status") == "no_audit_data":
            print(f"  {ds:<20s} {'N/A':>6s} {'N/A':>6s}")
        else:
            grade = sc.get("grade", "?")
            overall = sc.get("overall_score", 0.0)
            print(f"  {ds:<20s} {overall:>5.1f} {grade:>6s}")
    print("=" * 60)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compute quality scorecard for Layer 2 metadata audits.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dataset",
        type=str,
        help="Score a single dataset by name.",
    )
    group.add_argument(
        "--all-datasets",
        action="store_true",
        help="Score all datasets with audit results.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=SCORECARD_CONFIG_PATH,
        help="Path to scorecard YAML config (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: scripts/audit/results/{dataset}/).",
    )
    parser.add_argument(
        "--update-index",
        action="store_true",
        help="Update AUDIT_TRACKING_INDEX.md with scorecard results.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable output.",
    )

    args = parser.parse_args()
    config = load_scorecard_config(args.config)

    datasets = _discover_datasets(args.dataset)
    if datasets is None:
        return 1

    scorecards: list[dict[str, Any]] = []
    for dataset_name in datasets:
        scorecard = score_dataset(dataset_name, config)
        scorecards.append(scorecard)

        out_dir = args.output_dir or (AUDIT_RESULTS_DIR / dataset_name)
        write_scorecard(scorecard, out_dir / "scorecard.json")

        if not args.quiet:
            print_scorecard(scorecard)

    if len(scorecards) > 1 and not args.quiet:
        _print_multi_dataset_summary(scorecards)

    if args.update_index:
        valid = [s for s in scorecards if s.get("status") != "no_audit_data"]
        if valid:
            update_tracking_index(valid)

    return 0


if __name__ == "__main__":
    sys.exit(main())
