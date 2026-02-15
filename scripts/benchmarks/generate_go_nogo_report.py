#!/usr/bin/env python3
"""Generate Go/No-Go decision report from Stream 3 benchmark results.

Reads all JSON result files from results/stream3_benchmarks/ and produces
a comprehensive Markdown decision document.

Usage:
    python scripts/benchmarks/generate_go_nogo_report.py \
        --results-dir results/stream3_benchmarks \
        --output results/stream3_benchmarks/GO_NOGO_DECISION.md
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from scripts.benchmarks.classification_metrics import format_confusion_matrix
from scripts.benchmarks.stream3_config import THRESHOLDS

logger = logging.getLogger(__name__)

# Map detector result file prefixes to threshold keys
_PREFIX_TO_THRESHOLD: dict[str, str] = {
    "script_detection": "script_detection",
    "document_source": "document_source",
    "orientation": "orientation",
    "shadow": "shadow",
    "warping": "warping",
    "handwriting": "handwriting",
}


def find_latest_results(results_dir: Path) -> dict[str, dict[str, Any]]:
    """Find the most recent result file for each benchmark type.

    Args:
        results_dir: Directory containing benchmark result JSON files.

    Returns:
        Dict mapping benchmark name to loaded result dict.
    """
    results: dict[str, dict[str, Any]] = {}

    if not results_dir.exists():
        logger.warning("Results directory not found: %s", results_dir)
        return results

    # Group files by prefix, take latest by timestamp in filename
    for prefix in _PREFIX_TO_THRESHOLD:
        matching = sorted(results_dir.glob(f"{prefix}_*.json"), reverse=True)
        if matching:
            latest = matching[0]
            try:
                with open(latest) as fh:
                    results[prefix] = json.load(fh)
                logger.info("Loaded %s from %s", prefix, latest.name)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load %s: %s", latest, exc)

    # Also look for descriptive stats
    descriptive = sorted(results_dir.glob("descriptive_*.json"), reverse=True)
    if descriptive:
        try:
            with open(descriptive[0]) as fh:
                results["descriptive"] = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass

    return results


def generate_executive_summary(results: dict[str, dict[str, Any]]) -> list[str]:
    """Generate the executive summary table.

    Args:
        results: Loaded benchmark results.

    Returns:
        List of Markdown lines.
    """
    lines: list[str] = [
        "## Executive Summary",
        "",
        "| Detector | Metric | Dataset | Score | Target | Status | Decision |",
        "|----------|--------|---------|-------|--------|--------|----------|",
    ]

    for prefix, threshold_key in _PREFIX_TO_THRESHOLD.items():
        if prefix not in results:
            threshold = THRESHOLDS.get(threshold_key)
            if threshold:
                lines.append(
                    f"| {threshold.detector_name} | {threshold.metric} | "
                    f"{threshold.dataset} | - | {threshold.target:.0%} | NOT RUN | - |"
                )
            continue

        result = results[prefix]
        threshold = THRESHOLDS.get(threshold_key)
        if not threshold:
            continue

        # Extract metric value
        threshold_info = result.get("threshold", {})
        met = threshold_info.get("met", False)

        # Find the metric value
        metric_value = _extract_metric(result, threshold.metric)
        score_str = f"{metric_value:.1%}" if metric_value is not None else "-"
        status = "PASS" if met else "FAIL"
        decision = "Ship heuristic" if met else threshold.ml_action

        # Check reliability
        reliable = threshold_info.get("reliable", True)
        if not reliable:
            status += "*"

        lines.append(
            f"| {threshold.detector_name} | {threshold.metric} | "
            f"{threshold.dataset} | {score_str} | {threshold.target:.0%} | "
            f"{status} | {decision} |"
        )

    # Count results
    total_run = sum(1 for p in _PREFIX_TO_THRESHOLD if p in results)
    total_pass = sum(
        1
        for p in _PREFIX_TO_THRESHOLD
        if p in results and results[p].get("threshold", {}).get("met", False)
    )
    total_fail = total_run - total_pass

    lines.append("")
    lines.append(
        f"**Summary**: {total_run} benchmarks run, {total_pass} PASS, {total_fail} FAIL"
    )
    if any(
        not results.get(p, {}).get("threshold", {}).get("reliable", True)
        for p in _PREFIX_TO_THRESHOLD
        if p in results
    ):
        lines.append("\\* Result marked unreliable (insufficient positive samples)")
    lines.append("")

    return lines


def _extract_metric(result: dict[str, Any], metric_name: str) -> float | None:
    """Extract the primary metric value from a result dict.

    Handles different result structures across benchmark types.

    Args:
        result: Loaded benchmark result.
        metric_name: Metric name (e.g., "accuracy", "f1").

    Returns:
        Metric value, or None if not found.
    """
    # Direct metrics dict
    metrics = result.get("metrics", {})
    if metric_name in metrics:
        return metrics[metric_name]

    # Family-level (script detection)
    family = metrics.get("family_level", {})
    if metric_name in family:
        return family[metric_name]

    # Overall (orientation)
    overall = metrics.get("overall", {})
    if metric_name in overall:
        return overall[metric_name]

    # Primary (shadow/warping)
    primary = result.get("primary", {})
    if primary:
        primary_metrics = primary.get("metrics", {})
        if metric_name in primary_metrics:
            return primary_metrics[metric_name]

    return None


def generate_detector_section(
    name: str,
    result: dict[str, Any],
    threshold_key: str,
) -> list[str]:
    """Generate detailed section for a single detector.

    Args:
        name: Detector display name.
        result: Loaded benchmark result.
        threshold_key: Key into THRESHOLDS dict.

    Returns:
        List of Markdown lines.
    """
    lines = [f"### {name}", ""]

    threshold = THRESHOLDS.get(threshold_key)

    # Dataset info
    dataset = result.get("dataset", "unknown")
    num_samples = result.get("num_samples", 0)
    lines.append(f"**Dataset**: {dataset} | **Samples**: {num_samples:,}")
    lines.append("")

    # Metrics
    metrics = result.get("metrics", {})

    # Handle different structures
    if "family_level" in metrics:
        # Script detection - family level
        family = metrics["family_level"]
        lines.extend(_format_classification_metrics(family, "Family-Level"))

        if "iso_level" in metrics:
            lines.extend(
                _format_classification_metrics(metrics["iso_level"], "ISO-Level")
            )

        # IndicDLP supplementary (script detection only)
        indicdlp = result.get("supplementary_indicdlp")
        if indicdlp:
            lines.extend(_format_indicdlp_section(indicdlp))

    elif "overall" in metrics:
        # Orientation - overall + breakdowns
        lines.extend(_format_classification_metrics(metrics["overall"], "Overall"))

        # Per-script breakdown
        per_script = metrics.get("per_script", {})
        if per_script:
            lines.extend(["", "**Per-Script Accuracy**:", ""])
            lines.append("| Script | Accuracy | Samples |")
            lines.append("|--------|----------|---------|")
            for script, data in sorted(per_script.items()):
                lines.append(
                    f"| {script} | {data['accuracy']:.1%} | {data['num_samples']} |"
                )

        # Per-DPI breakdown
        per_dpi = metrics.get("per_dpi", {})
        if per_dpi:
            lines.extend(["", "**Per-DPI Accuracy**:", ""])
            lines.append("| DPI | Accuracy | Samples |")
            lines.append("|-----|----------|---------|")
            for dpi, data in sorted(per_dpi.items(), key=lambda x: int(x[0])):
                lines.append(
                    f"| {dpi} | {data['accuracy']:.1%} | {data['num_samples']} |"
                )

        # Vertical text
        vt = metrics.get("vertical_text")
        if vt:
            lines.extend(
                [
                    "",
                    f"**CJK Vertical Text**: {vt['accuracy']:.1%} ({vt['num_samples']} samples)",
                ]
            )

    elif "primary" in result or "accuracy" in metrics:
        # Binary metrics (shadow, warping, document source)
        if result.get("primary"):
            primary = result["primary"]
            lines.extend(
                _format_binary_metrics(
                    primary.get("metrics", {}), primary.get("dataset", "Primary")
                )
            )

            score_dist = primary.get("score_distribution", {})
            if score_dist.get("shadow_mean") is not None:
                lines.extend(
                    [
                        "",
                        "**Score Distribution**:",
                        f"- Shadow images: mean={score_dist['shadow_mean']:.4f}, std={score_dist.get('shadow_std', 0):.4f}",
                        f"- Clean images: mean={score_dist.get('clean_mean', 0):.4f}, std={score_dist.get('clean_std', 0):.4f}",
                    ]
                )
        else:
            lines.extend(_format_binary_metrics(metrics, dataset))

        # WarpDoc per-type (warping)
        warpdoc_per_type = result.get("warpdoc_per_type", {})
        if warpdoc_per_type:
            lines.extend(["", "**WarpDoc Per-Type Results**:", ""])
            lines.append("| Type | F1 | Accuracy | Samples |")
            lines.append("|------|-----|----------|---------|")
            for dtype, dtype_result in sorted(warpdoc_per_type.items()):
                dm = dtype_result.get("metrics", {})
                lines.append(
                    f"| {dtype} | {dm.get('f1', 0):.4f} | {dm.get('accuracy', 0):.1%} | {dm.get('num_samples', 0)} |"
                )

        # Validation dataset (shadow/warping)
        validation = result.get("validation")
        if validation:
            lines.extend(["", "**Validation Dataset**:"])
            val_m = validation.get("metrics", {})
            lines.append(f"- Dataset: {validation.get('dataset', 'validation')}")
            lines.append(
                f"- F1: {val_m.get('f1', 0):.4f}, Accuracy: {val_m.get('accuracy', 0):.1%}"
            )

    # Latency
    latency = result.get("latency", {})
    if not latency and "primary" in result and result.get("primary"):
        latency = result["primary"].get("latency", {})
    if latency and latency.get("mean_ms", 0) > 0:
        lines.extend(
            [
                "",
                f"**Latency**: mean={latency.get('mean_ms', 0):.1f}ms, "
                f"p95={latency.get('p95_ms', 0):.1f}ms",
            ]
        )

    # Caveats
    caveat = result.get("caveat")
    if caveat:
        lines.extend(["", f"> **Caveat**: {caveat}"])

    # Go/No-Go
    if threshold:
        met = result.get("threshold", {}).get("met", False)
        metric_value = _extract_metric(result, threshold.metric)
        score_str = f"{metric_value:.1%}" if metric_value is not None else "N/A"

        lines.extend(
            [
                "",
                f"**Go/No-Go**: {'PASS' if met else 'FAIL'} "
                f"({score_str} vs {threshold.target:.0%} target)",
            ]
        )
        if not met:
            lines.append(f"**Recommended Action**: {threshold.ml_action}")

    lines.append("")
    return lines


def _format_classification_metrics(metrics: dict[str, Any], label: str) -> list[str]:
    """Format classification metrics as Markdown.

    Args:
        metrics: Classification report dict.
        label: Section label.

    Returns:
        Markdown lines.
    """
    lines = [
        f"**{label} Metrics**:",
        "",
        f"- Accuracy: {metrics.get('accuracy', 0):.1%}",
        f"- Macro F1: {metrics.get('macro_f1', 0):.4f}",
        f"- Weighted F1: {metrics.get('weighted_f1', 0):.4f}",
        f"- Cohen's Kappa: {metrics.get('cohens_kappa', 0):.4f}",
    ]

    # Confusion matrix
    cm = metrics.get("confusion_matrix")
    class_names = metrics.get("class_names")
    if cm and class_names:
        lines.extend(
            [
                "",
                "**Confusion Matrix**:",
                "```text",
                format_confusion_matrix(cm, class_names),
                "```",
            ]
        )

    # Per-class
    per_class = metrics.get("per_class", {})
    if per_class:
        lines.extend(["", "| Class | Precision | Recall | F1 | Support |"])
        lines.append("|-------|-----------|--------|-----|---------|")
        for cls, cls_metrics in per_class.items():
            lines.append(
                f"| {cls} | {cls_metrics.get('precision', 0):.4f} | "
                f"{cls_metrics.get('recall', 0):.4f} | {cls_metrics.get('f1', 0):.4f} | "
                f"{cls_metrics.get('support', 0)} |"
            )
        lines.append("")

    return lines


def _format_indicdlp_section(indicdlp: dict[str, Any]) -> list[str]:
    """Format the IndicDLP supplementary evaluation section.

    Args:
        indicdlp: IndicDLP result sub-dict from script detection benchmark.

    Returns:
        Markdown lines.
    """
    lines: list[str] = [
        "",
        "**Supplementary: IndicDLP (12 Indic Languages)**:",
        "",
        f"> {indicdlp.get('note', '')}",
        "",
        f"**Samples**: {indicdlp.get('num_samples', 0):,}",
        "",
    ]

    indic_metrics = indicdlp.get("metrics", {})
    family = indic_metrics.get("family_level", {})
    if family:
        lines.extend(
            [
                f"- Family-level accuracy: {family.get('accuracy', 0):.1%}",
                f"- Macro F1: {family.get('macro_f1', 0):.4f}",
                f"- Cohen's Kappa: {family.get('cohens_kappa', 0):.4f}",
            ]
        )

    iso = indic_metrics.get("iso_level", {})
    if iso:
        lines.extend(
            [
                f"- ISO-level accuracy: {iso.get('accuracy', 0):.1%}",
            ]
        )

    # Per-language breakdown
    per_lang = indicdlp.get("per_language", {})
    if per_lang:
        lines.extend(["", "| Script (ISO) | Family Accuracy | Samples |"])
        lines.append("|--------------|-----------------|---------|")
        for lang_iso, stats in sorted(per_lang.items()):
            lines.append(
                f"| {lang_iso} | {stats.get('accuracy', 0):.1%} | {stats.get('total', 0)} |"
            )

    lines.append("")
    return lines


def _format_binary_metrics(metrics: dict[str, Any], label: str) -> list[str]:
    """Format binary metrics as Markdown.

    Args:
        metrics: Binary report dict.
        label: Section label.

    Returns:
        Markdown lines.
    """
    return [
        f"**{label} Metrics**:",
        "",
        f"- Accuracy: {metrics.get('accuracy', 0):.1%}",
        f"- Precision: {metrics.get('precision', 0):.4f}",
        f"- Recall: {metrics.get('recall', 0):.4f}",
        f"- F1: {metrics.get('f1', 0):.4f}",
        f"- ROC-AUC: {metrics.get('roc_auc', 'N/A')}",
        f"- TP={metrics.get('tp', 0)}, FP={metrics.get('fp', 0)}, "
        f"TN={metrics.get('tn', 0)}, FN={metrics.get('fn', 0)}",
    ]


def generate_descriptive_section(result: dict[str, Any]) -> list[str]:
    """Generate section for Tier 3 descriptive stats.

    Args:
        result: Descriptive benchmark result dict.

    Returns:
        Markdown lines.
    """
    lines = ["### Tier 3: Descriptive Statistics (No GT)", ""]

    # Blank page
    blank = result.get("blank_page", {})
    if blank:
        synth = blank.get("synthetic_metrics", {})
        lines.extend(
            [
                "#### BlankPageDetector",
                "",
                f"- Synthetic accuracy: {synth.get('accuracy', 0):.1%}",
                f"- Real docs false-blank rate: {blank.get('real_false_positive_rate', 0):.1%} "
                f"({blank.get('real_false_blank_count', 0)}/{blank.get('real_docs_tested', 0)})",
                "",
            ]
        )

    # Code detector
    code = result.get("code_detector", {})
    if code:
        score_dist = code.get("score_distribution", {})
        lines.extend(
            [
                "#### CodeDetector",
                "",
                f"- Detection rate: {code.get('detection_rate', 0):.1%} ({code.get('positive_count', 0)}/{code.get('num_images', 0)})",
                f"- Score distribution: mean={score_dist.get('mean', 0):.4f}, p95={score_dist.get('p95', 0):.4f}",
                "",
            ]
        )

    # Table complexity
    table = result.get("table_complexity", {})
    if table:
        complexity = table.get("complexity_distribution", {})
        lines.extend(
            [
                "#### TableComplexityAnalyzer",
                "",
                f"- Mean complexity: {complexity.get('mean', 0):.4f}",
                f"- P95 complexity: {complexity.get('p95', 0):.4f}",
                "",
            ]
        )

    return lines


def generate_ml_recommendations(results: dict[str, dict[str, Any]]) -> list[str]:
    """Generate ML upgrade recommendations for failing detectors.

    Args:
        results: All loaded benchmark results.

    Returns:
        Markdown lines.
    """
    lines = ["## ML Upgrade Recommendations", ""]

    failures = []
    for prefix, threshold_key in _PREFIX_TO_THRESHOLD.items():
        if prefix not in results:
            continue
        result = results[prefix]
        if not result.get("threshold", {}).get("met", False):
            threshold = THRESHOLDS.get(threshold_key)
            if threshold:
                failures.append((prefix, threshold, result))

    if not failures:
        lines.append(
            "All detectors met their Go/No-Go thresholds. No ML upgrades required."
        )
        lines.append("")
        return lines

    for prefix, threshold, result in failures:
        metric_value = _extract_metric(result, threshold.metric)
        score_str = f"{metric_value:.1%}" if metric_value is not None else "N/A"
        gap = threshold.target - (metric_value or 0)

        lines.extend(
            [
                f"### {threshold.detector_name}",
                "",
                f"- **Current**: {score_str} | **Target**: {threshold.target:.0%} | **Gap**: {gap:.1%}",
                f"- **Action**: {threshold.ml_action}",
                f"- **Dataset**: {threshold.dataset}",
                "",
            ]
        )

    return lines


def generate_report(results_dir: Path, output_path: Path) -> None:
    """Generate the full Go/No-Go decision report.

    Args:
        results_dir: Directory with benchmark JSON results.
        output_path: Path to write the Markdown report.
    """
    results = find_latest_results(results_dir)

    if not results:
        print(f"No benchmark results found in {results_dir}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# Stream 3: Go/No-Go Decision Report",
        "",
        f"> Generated: {timestamp}",
        ">",
        "> Phase 10 Stream 3 benchmarks heuristic detectors (Stream 2) against",
        "> real labeled datasets to determine if ML upgrades (Stream 4) are needed.",
        "",
    ]

    # Executive summary
    lines.extend(generate_executive_summary(results))

    # Per-detector sections
    lines.append("## Detailed Results")
    lines.append("")

    detector_display_names = {
        "script_detection": "Script Detection (MLT-2019 + IndicDLP)",
        "document_source": "Document Source (SmartDoc-QA + Tobacco800 + DocReal)",
        "orientation": "Orientation Detection (synth_multiscript_v3)",
        "shadow": "Shadow Detection (SD7K + WSRD)",
        "warping": "Warping Detection (AnyPhotoDoc6300 + WarpDoc)",
        "handwriting": "Handwriting Detection (COCO-Text)",
    }

    for prefix, threshold_key in _PREFIX_TO_THRESHOLD.items():
        if prefix in results:
            display_name = detector_display_names.get(prefix, prefix)
            lines.extend(
                generate_detector_section(display_name, results[prefix], threshold_key)
            )

    # Descriptive stats
    if "descriptive" in results:
        lines.extend(generate_descriptive_section(results["descriptive"]))

    # ML recommendations
    lines.extend(generate_ml_recommendations(results))

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Go/No-Go report written to {output_path}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Go/No-Go decision report from benchmark results"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/stream3_benchmarks"),
        help="Directory containing benchmark JSON results",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/stream3_benchmarks/GO_NOGO_DECISION.md"),
        help="Output Markdown report path",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    generate_report(args.results_dir, args.output)


if __name__ == "__main__":
    main()
