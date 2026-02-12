#!/usr/bin/env python3
"""Compute quality scorecard for Layer 2 metadata audits.

Reads existing JSON audit artifacts and computes a weighted quality grade
per dataset based on the 6-dimension rubric in config/audit_scorecard.yaml.

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
def compute_field_coverage(screening_path: Path) -> float | None:
    """Compute field coverage score from automated_screening.json.

    Score = average pass rate across 13 prescreening fields.

    Args:
        screening_path: Path to automated_screening.json.

    Returns:
        Score 0-100, or None if artifact missing.
    """
    if not screening_path.is_file():
        log.warning("  automated_screening.json not found: %s", screening_path)
        return None

    with screening_path.open() as f:
        data = json.load(f)

    per_field = data.get("per_field_results", {})
    if not per_field:
        log.warning("  No per_field_results in screening data")
        return None

    total_fields = len(per_field)
    pass_rates: list[float] = []
    for field_name, stats in per_field.items():
        total = stats.get("pass", 0) + stats.get("fail", 0)
        if total > 0:
            pass_rate = stats["pass"] / total * 100
        else:
            pass_rate = 0.0
        pass_rates.append(pass_rate)

    score = sum(pass_rates) / max(total_fields, 1)
    log.info(
        "  field_coverage: %.1f/100 (%d fields, avg pass rate %.1f%%)",
        score,
        total_fields,
        score,
    )
    return round(score, 2)


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

    # Handle both summary-level and field-level formats
    field_summary = data.get("field_summary", {})
    if field_summary:
        validity_pcts: list[float] = []
        for _field, info in field_summary.items():
            if isinstance(info, dict) and "validity_pct" in info:
                validity_pcts.append(info["validity_pct"])
        if validity_pcts:
            score = sum(validity_pcts) / len(validity_pcts)
            log.info(
                "  field_validity: %.1f/100 (%d fields)",
                score,
                len(validity_pcts),
            )
            return round(score, 2)

    # Fallback: extract from per_field_results if available
    per_field = data.get("per_field_results", {})
    if per_field:
        validity_pcts = []
        for _field, info in per_field.items():
            if isinstance(info, dict):
                total = info.get("valid", 0) + info.get("invalid", 0)
                if total > 0:
                    validity_pcts.append(info["valid"] / total * 100)
        if validity_pcts:
            score = sum(validity_pcts) / len(validity_pcts)
            log.info(
                "  field_validity: %.1f/100 (%d fields)",
                score,
                len(validity_pcts),
            )
            return round(score, 2)

    log.warning("  Could not extract validity scores from compliance.json")
    return None


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

    # Expected section keywords (case-insensitive partial match)
    expected_sections = [
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

    # Find headings and check for content after them
    populated = 0
    for keyword in expected_sections:
        found_heading = False
        for i, line in enumerate(lines):
            # Match any heading level
            if re.match(r"^#{1,6}\s+", line) and keyword.lower() in line.lower():
                found_heading = True
                # Check if there's content after the heading
                has_content = False
                for j in range(i + 1, min(i + 20, len(lines))):
                    stripped = lines[j].strip()
                    # Stop at next heading
                    if stripped and re.match(r"^#{1,6}\s+", stripped):
                        break
                    # Non-empty, non-heading line = content
                    if stripped and not stripped.startswith("---"):
                        has_content = True
                        break
                if has_content:
                    populated += 1
                break
        if not found_heading:
            pass  # Section not found at all

    total = len(expected_sections)
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
    penalties = dim_config.get("defect_penalties", {
        "critical": 15,
        "high": 10,
        "medium": 5,
        "low": 2,
    })
    status_weights = dim_config.get("status_weights", {
        "RESOLVED": 0.0,
        "PARTIALLY_RESOLVED": 0.5,
        "DEFERRED": 0.3,
        "OPEN": 1.0,
    })

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

    # Compute pairwise agreement from samples
    samples = data.get("samples", [])
    if not samples:
        log.warning("  No samples in comparison report")
        return None

    field_agreements: dict[str, list[bool]] = {}
    for sample in samples:
        fields = sample.get("fields", {})
        for field_name, field_data in fields.items():
            pairwise = field_data.get("pairwise_matches", {})
            for _pair, matches in pairwise.items():
                if field_name not in field_agreements:
                    field_agreements[field_name] = []
                if isinstance(matches, bool):
                    field_agreements[field_name].append(matches)

    if not field_agreements:
        # Fallback: count fields where sources agree
        total_comparisons = 0
        agreements = 0
        for sample in samples:
            fields = sample.get("fields", {})
            for _field_name, field_data in fields.items():
                source_values = field_data.get("sources", {})
                non_null = [
                    v for v in source_values.values() if v is not None
                ]
                if len(non_null) >= 2:
                    total_comparisons += 1
                    if len(set(str(v) for v in non_null)) == 1:
                        agreements += 1

        if total_comparisons == 0:
            log.warning("  No multi-source comparisons available")
            return None
        score = agreements / total_comparisons * 100
    else:
        field_rates: list[float] = []
        for _field, matches in field_agreements.items():
            if matches:
                rate = sum(matches) / len(matches) * 100
                field_rates.append(rate)
        if not field_rates:
            return None
        score = sum(field_rates) / len(field_rates)

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


# -------------------------------------------------------------------
# Overall scorecard computation
# -------------------------------------------------------------------
def compute_overall(
    dimension_scores: dict[str, float | None],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute the overall weighted score and grade.

    Missing dimensions have their weight redistributed proportionally.

    Args:
        dimension_scores: Per-dimension scores (0-100) or None.
        config: Full scorecard config.

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

    # Redistribute excluded weights
    total_available_weight = sum(w for w, _ in available.values())
    effective_weights: dict[str, float] = {}
    for dim_name, (weight, _score) in available.items():
        effective_weights[dim_name] = weight / total_available_weight

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

    # Enforce grade caps for required dimensions
    grade_caps = config.get("grade_caps", {})
    grade_cap_applied: str | None = None

    # Check vlm_accuracy requirement
    vlm_config = dimensions.get("vlm_accuracy", {})
    if vlm_config.get("required", False) and "vlm_accuracy" in excluded:
        cap_rule = grade_caps.get("missing_vlm_accuracy", {})
        max_grade = cap_rule.get("max_grade", "D")
        grade_order = ["A", "B", "C", "D", "F"]
        if grade_order.index(grade) < grade_order.index(max_grade):
            grade_cap_applied = (
                f"Grade capped from {grade} to {max_grade}: "
                f"VLM inspection not performed. "
                f"{cap_rule.get('reason', '').strip()}"
            )
            grade = max_grade
            log.warning("  GRADE CAPPED: %s", grade_cap_applied)

    result: dict[str, Any] = {
        "overall_score": round(overall, 2),
        "grade": grade,
        "dimensions": dim_details,
        "excluded_dimensions": excluded,
        "effective_weights": {
            k: round(v, 4) for k, v in effective_weights.items()
        },
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
    compliance_path = results_dir / "compliance.json"
    catalog_path = results_dir / "defect_catalog.json"
    comparison_path = results_dir / "comparison_report.json"
    vlm_path = results_dir / "vlm_corrections.json"
    source_doc = DATASET_DOCS_DIR / f"{dataset_name}.md"

    dimension_scores: dict[str, float | None] = {
        "field_coverage": compute_field_coverage(screening_path),
        "field_validity": compute_field_validity(compliance_path),
        "doc_completeness": compute_doc_completeness(source_doc),
        "defect_rate": compute_defect_rate(catalog_path, config),
        "cross_source_agreement": compute_cross_source_agreement(
            comparison_path,
        ),
        "vlm_accuracy": compute_vlm_accuracy(vlm_path, catalog_path),
    }

    overall = compute_overall(dimension_scores, config)

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
        "dimension_scores": {
            k: v for k, v in dimension_scores.items()
        },
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
        print(
            f"  {'Dimension':<28s} {'Score':>6s} {'Weight':>7s} "
            f"{'Weighted':>8s}"
        )
        print("  " + "-" * 52)
        for dim_name, detail in dims.items():
            label = dim_name.replace("_", " ").title()
            score = detail.get("score", 0)
            eff_w = detail.get("effective_weight", 0)
            weighted = detail.get("weighted_contribution", 0)
            print(
                f"  {label:<28s} {score:>5.1f} {eff_w:>6.2f}  "
                f"{weighted:>7.2f}"
            )
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
        "| Dataset | Score | Grade | Coverage | Validity "
        "| Doc | Defects | Agreement | VLM | Updated |",
        "|---------|-------|-------|----------|----------"
        "|-----|---------|-----------|-----|---------|",
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
            f"| {fmt(dim_scores.get('vlm_accuracy'))} "
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

    scorecards: list[dict[str, Any]] = []

    if args.dataset:
        datasets = [args.dataset]
    else:
        # Find all datasets with audit results
        datasets = sorted(
            d.name
            for d in AUDIT_RESULTS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        if not datasets:
            log.error("No audit results found in %s", AUDIT_RESULTS_DIR)
            return 1
        log.info("Found audit results for %d datasets", len(datasets))

    for dataset_name in datasets:
        scorecard = score_dataset(dataset_name, config)
        scorecards.append(scorecard)

        # Write individual scorecard
        out_dir = args.output_dir or (AUDIT_RESULTS_DIR / dataset_name)
        write_scorecard(scorecard, out_dir / "scorecard.json")

        if not args.quiet:
            print_scorecard(scorecard)

    # Summary for multi-dataset runs
    if len(scorecards) > 1 and not args.quiet:
        print("=" * 60)
        print("  Summary: All Datasets")
        print("=" * 60)
        print(f"  {'Dataset':<20s} {'Score':>6s} {'Grade':>6s}")
        print("  " + "-" * 34)
        for sc in scorecards:
            ds = sc.get("dataset", "?")
            grade = sc.get("grade", "?")
            overall = sc.get("overall_score", 0.0)
            status = sc.get("status", "")
            if status == "no_audit_data":
                print(f"  {ds:<20s} {'N/A':>6s} {'N/A':>6s}")
            else:
                print(f"  {ds:<20s} {overall:>5.1f} {grade:>6s}")
        print("=" * 60)

    # Update tracking index if requested
    if args.update_index:
        valid = [s for s in scorecards if s.get("status") != "no_audit_data"]
        if valid:
            update_tracking_index(valid)

    return 0


if __name__ == "__main__":
    sys.exit(main())
