# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Dataset validation and stratified splitting for synthetic document generation.

This module provides:
- Stratified train/val/test splitting by primary script
- Dataset validation checks per script_dataset_structure.md specification
- Distribution analysis and reporting

Example:
    >>> from image_preprocessing_detector.synthetic.validation import (
    ...     create_stratified_splits,
    ...     validate_dataset,
    ... )
    >>> train, val, test = create_stratified_splits(samples)
    >>> report = validate_dataset(samples)
    >>> if not report.is_valid:
    ...     print(report.issues)
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from image_preprocessing_detector.synthetic.schema_adapter import GeneratedSample

logger = logging.getLogger(__name__)


# =============================================================================
# Stratified Splitting
# =============================================================================


def create_stratified_splits(
    samples: list[GeneratedSample],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    seed: int = 42,
    in_place: bool = True,
) -> tuple[list[GeneratedSample], list[GeneratedSample], list[GeneratedSample]]:
    """Create stratified train/val/test splits by primary script.

    Ensures each split has proportional representation from all scripts,
    which is critical for balanced model training and evaluation.

    Args:
        samples: List of GeneratedSample objects to split
        train_ratio: Proportion for training set (default 0.80)
        val_ratio: Proportion for validation set (default 0.10)
        test_ratio: Proportion for test set (default 0.10)
        seed: Random seed for reproducibility
        in_place: If True, sets the `split` attribute on each sample

    Returns:
        Tuple of (train_samples, val_samples, test_samples)

    Raises:
        ValueError: If ratios don't sum to 1.0 or samples is empty
    """
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.001:
        raise ValueError(
            f"Split ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"
        )

    if not samples:
        raise ValueError("Cannot split empty sample list")

    import random

    rng = random.Random(seed)

    # Group samples by primary script
    by_script: dict[str, list[GeneratedSample]] = defaultdict(list)
    for sample in samples:
        # Use first (primary) script for stratification
        primary_script = sorted(sample.scripts)[0] if sample.scripts else "unknown"
        by_script[primary_script].append(sample)

    train: list[GeneratedSample] = []
    val: list[GeneratedSample] = []
    test: list[GeneratedSample] = []

    # Split each script group proportionally
    for script_code, script_samples in by_script.items():
        # Shuffle within script
        rng.shuffle(script_samples)

        n_total = len(script_samples)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        # Test gets the remainder to ensure all samples are assigned

        s_train = script_samples[:n_train]
        s_val = script_samples[n_train : n_train + n_val]
        s_test = script_samples[n_train + n_val :]

        # Set split attribute if requested
        if in_place:
            for s in s_train:
                s.split = "train"
            for s in s_val:
                s.split = "val"
            for s in s_test:
                s.split = "test"

        train.extend(s_train)
        val.extend(s_val)
        test.extend(s_test)

        logger.debug(
            "Script %s: %d train, %d val, %d test",
            script_code,
            len(s_train),
            len(s_val),
            len(s_test),
        )

    # Final shuffle to mix scripts
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    logger.info(
        "Split complete: %d train (%.1f%%), %d val (%.1f%%), %d test (%.1f%%)",
        len(train),
        100 * len(train) / len(samples),
        len(val),
        100 * len(val) / len(samples),
        len(test),
        100 * len(test) / len(samples),
    )

    return train, val, test


# =============================================================================
# Dataset Validation
# =============================================================================


@dataclass
class ValidationIssue:
    """Single validation issue.

    Attributes:
        category: Issue category (coverage, distribution, etc.)
        severity: Issue severity (error, warning, info)
        message: Human-readable description
        details: Additional context
    """

    category: str
    severity: str  # error, warning, info
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report for a dataset.

    Attributes:
        is_valid: True if dataset passes all required checks
        issues: List of validation issues found
        statistics: Computed statistics about the dataset
    """

    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)

    def add_error(
        self, category: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        """Add an error issue (fails validation)."""
        self.issues.append(
            ValidationIssue(
                category=category,
                severity="error",
                message=message,
                details=details or {},
            )
        )
        self.is_valid = False

    def add_warning(
        self, category: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        """Add a warning issue (passes but needs attention)."""
        self.issues.append(
            ValidationIssue(
                category=category,
                severity="warning",
                message=message,
                details=details or {},
            )
        )

    def add_info(
        self, category: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        """Add an informational note."""
        self.issues.append(
            ValidationIssue(
                category=category,
                severity="info",
                message=message,
                details=details or {},
            )
        )

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Validation {'PASSED' if self.is_valid else 'FAILED'}",
            f"Total issues: {len(self.issues)}",
        ]

        by_severity = Counter(i.severity for i in self.issues)
        if by_severity:
            lines.append(
                f"  Errors: {by_severity.get('error', 0)}, "
                f"Warnings: {by_severity.get('warning', 0)}, "
                f"Info: {by_severity.get('info', 0)}"
            )

        if self.statistics:
            lines.append("\nStatistics:")
            for key, value in self.statistics.items():
                if isinstance(value, dict):
                    lines.append(f"  {key}:")
                    for k, v in value.items():
                        lines.append(f"    {k}: {v}")
                else:
                    lines.append(f"  {key}: {value}")

        return "\n".join(lines)


# Validation thresholds from script_dataset_structure.md
VALIDATION_THRESHOLDS = {
    # Minimum samples per script per split
    "min_train_per_script": 1000,
    "min_val_per_script": 125,
    "min_test_per_script": 125,
    # Distribution tolerances
    "quality_tolerance": 0.05,  # 5% deviation allowed
    "split_tolerance": 0.02,  # 2% deviation from 80/10/10
    # Coverage requirements
    "min_layout_samples_per_script": 50,  # Per (script, layout) combination
    "min_latn_languages": 20,  # Latin script should have 20+ languages
    "min_arab_languages": 10,  # Arabic script should have 10+ languages
    # IQA independence
    "max_kl_divergence": 0.05,  # IQA should be independent of script
}


def validate_dataset(
    samples: list[GeneratedSample],
    thresholds: dict[str, Any] | None = None,
) -> ValidationReport:
    """Validate a dataset against script_dataset_structure.md requirements.

    Checks:
    - Script coverage: All 27 scripts in all splits
    - Minimum samples per script per split
    - Layout coverage: ≥50 samples per (script, layout)
    - Quality tier distribution within tolerance
    - Split ratios within tolerance
    - Language diversity for major scripts

    Args:
        samples: List of GeneratedSample objects
        thresholds: Override default thresholds

    Returns:
        ValidationReport with issues and statistics
    """
    report = ValidationReport()
    thresh = {**VALIDATION_THRESHOLDS, **(thresholds or {})}

    if not samples:
        report.add_error("dataset", "Empty dataset provided")
        return report

    # Compute statistics
    stats = compute_dataset_statistics(samples)
    report.statistics = stats

    # Check 1: Script coverage in all splits
    _validate_script_coverage(samples, stats, report, thresh)

    # Check 2: Minimum samples per script
    _validate_sample_counts(stats, report, thresh)

    # Check 3: Layout coverage per script
    _validate_layout_coverage(samples, report, thresh)

    # Check 4: Quality tier distribution
    _validate_quality_distribution(stats, report, thresh)

    # Check 5: Split ratios
    _validate_split_ratios(stats, report, thresh)

    # Check 6: Language diversity
    _validate_language_diversity(samples, report, thresh)

    return report


def compute_dataset_statistics(
    samples: list[GeneratedSample],
) -> dict[str, Any]:
    """Compute comprehensive statistics for a dataset.

    Args:
        samples: List of GeneratedSample objects

    Returns:
        Dictionary of statistics
    """
    stats: dict[str, Any] = {
        "total_samples": len(samples),
        "scripts": Counter(),
        "scripts_per_split": {"train": Counter(), "val": Counter(), "test": Counter()},
        "quality_tiers": Counter(),
        "resolution_tiers": Counter(),
        "layouts": Counter(),
        "densities": Counter(),
        "splits": Counter(),
        "languages_per_script": defaultdict(set),
        "multi_script_count": 0,
    }

    for sample in samples:
        # Scripts
        for script in sample.scripts:
            stats["scripts"][script] += 1

        # Multi-script tracking
        if len(sample.scripts) > 1:
            stats["multi_script_count"] += 1

        # Split tracking
        split = sample.split or "unassigned"
        stats["splits"][split] += 1

        # Scripts per split
        if sample.split in ("train", "val", "test"):
            for script in sample.scripts:
                stats["scripts_per_split"][sample.split][script] += 1

        # Quality/resolution tiers
        stats["quality_tiers"][sample.quality_tier] += 1
        stats["resolution_tiers"][sample.resolution_tier] += 1

        # Layout and density
        stats["layouts"][sample.layout_type.value] += 1
        stats["densities"][sample.text_density.value] += 1

        # Languages per script
        primary_script = sorted(sample.scripts)[0] if sample.scripts else "unknown"
        for lang in sample.language_codes:
            stats["languages_per_script"][primary_script].add(lang)

    # Convert sets to counts
    stats["language_counts_per_script"] = {
        script: len(langs) for script, langs in stats["languages_per_script"].items()
    }

    return stats


def _validate_script_coverage(
    samples: list[GeneratedSample],
    stats: dict[str, Any],
    report: ValidationReport,
    thresh: dict[str, Any],
) -> None:
    """Validate all required scripts are present in all splits."""
    from image_preprocessing_detector.synthetic.config import SCRIPT_CONFIGS

    # Use all 27 configured scripts, not just MVP_SCRIPTS (10)
    required_scripts = set(SCRIPT_CONFIGS.keys())
    found_scripts = set(stats["scripts"].keys())

    missing = required_scripts - found_scripts
    if missing:
        report.add_error(
            "coverage",
            f"Missing {len(missing)} required scripts",
            {"missing_scripts": sorted(missing)},
        )

    # Check per-split coverage
    for split_name in ("train", "val", "test"):
        split_scripts = set(stats["scripts_per_split"][split_name].keys())
        split_missing = required_scripts - split_scripts
        if split_missing:
            report.add_warning(
                "coverage",
                f"{split_name} split missing {len(split_missing)} scripts",
                {"split": split_name, "missing": sorted(split_missing)},
            )


def _validate_sample_counts(
    stats: dict[str, Any],
    report: ValidationReport,
    thresh: dict[str, Any],
) -> None:
    """Validate minimum sample counts per script per split."""
    for split_name, min_key in [
        ("train", "min_train_per_script"),
        ("val", "min_val_per_script"),
        ("test", "min_test_per_script"),
    ]:
        min_required = thresh[min_key]
        script_counts = stats["scripts_per_split"][split_name]

        below_min = {
            script: count
            for script, count in script_counts.items()
            if count < min_required
        }

        if below_min:
            report.add_warning(
                "sample_count",
                f"{len(below_min)} scripts below {min_required} samples in {split_name}",
                {"split": split_name, "scripts_below_min": below_min},
            )


def _validate_layout_coverage(
    samples: list[GeneratedSample],
    report: ValidationReport,
    thresh: dict[str, Any],
) -> None:
    """Validate layout coverage per script."""
    min_per_combo = thresh["min_layout_samples_per_script"]

    script_layout_counts: dict[tuple[str, str], int] = Counter()
    for sample in samples:
        primary_script = sorted(sample.scripts)[0] if sample.scripts else "unknown"
        layout = sample.layout_type.value
        script_layout_counts[(primary_script, layout)] += 1

    # Find combinations below threshold
    below_min = {
        combo: count
        for combo, count in script_layout_counts.items()
        if count < min_per_combo
    }

    if below_min:
        # Group by script for cleaner reporting
        by_script: dict[str, list[str]] = defaultdict(list)
        for (script, layout), count in below_min.items():
            by_script[script].append(f"{layout}:{count}")

        report.add_warning(
            "layout_coverage",
            f"{len(below_min)} (script, layout) combinations below {min_per_combo}",
            {"combinations_below_min": dict(by_script)},
        )


def _validate_quality_distribution(
    stats: dict[str, Any],
    report: ValidationReport,
    thresh: dict[str, Any],
) -> None:
    """Validate quality tier distribution matches targets."""
    from image_preprocessing_detector.synthetic.config import QUALITY_TIER_WEIGHTS

    tolerance = thresh["quality_tolerance"]
    total = stats["total_samples"]

    if total == 0:
        return

    for tier, target_ratio in QUALITY_TIER_WEIGHTS.items():
        actual_count = stats["quality_tiers"].get(tier, 0)
        actual_ratio = actual_count / total

        deviation = abs(actual_ratio - target_ratio)
        if deviation > tolerance:
            report.add_warning(
                "distribution",
                f"Quality tier '{tier}' deviates {deviation:.1%} from target",
                {
                    "tier": tier,
                    "target": target_ratio,
                    "actual": actual_ratio,
                    "deviation": deviation,
                },
            )


def _validate_split_ratios(
    stats: dict[str, Any],
    report: ValidationReport,
    thresh: dict[str, Any],
) -> None:
    """Validate train/val/test split ratios."""
    tolerance = thresh["split_tolerance"]
    total = stats["total_samples"]

    if total == 0:
        return

    expected = {"train": 0.80, "val": 0.10, "test": 0.10}

    for split_name, target in expected.items():
        actual_count = stats["splits"].get(split_name, 0)
        actual_ratio = actual_count / total

        deviation = abs(actual_ratio - target)
        if deviation > tolerance:
            report.add_warning(
                "split_ratio",
                f"Split '{split_name}' deviates {deviation:.1%} from target {target:.0%}",
                {
                    "split": split_name,
                    "target": target,
                    "actual": actual_ratio,
                    "deviation": deviation,
                },
            )


def _validate_language_diversity(
    samples: list[GeneratedSample],
    report: ValidationReport,
    thresh: dict[str, Any],
) -> None:
    """Validate language diversity for major scripts."""
    # Count unique languages per script
    languages_per_script: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        primary_script = sorted(sample.scripts)[0] if sample.scripts else "unknown"
        for lang in sample.language_codes:
            languages_per_script[primary_script].add(lang)

    # Check Latin
    latn_languages = len(languages_per_script.get("Latn", set()))
    min_latn = thresh["min_latn_languages"]
    if latn_languages < min_latn:
        report.add_warning(
            "language_diversity",
            f"Latin script has only {latn_languages} languages (min: {min_latn})",
            {"script": "Latn", "actual": latn_languages, "required": min_latn},
        )

    # Check Arabic
    arab_languages = len(languages_per_script.get("Arab", set()))
    min_arab = thresh["min_arab_languages"]
    if arab_languages < min_arab:
        report.add_warning(
            "language_diversity",
            f"Arabic script has only {arab_languages} languages (min: {min_arab})",
            {"script": "Arab", "actual": arab_languages, "required": min_arab},
        )


def generate_dataset_report(
    samples: list[GeneratedSample],
    output_path: str | None = None,
) -> str:
    """Generate a comprehensive human-readable dataset report.

    Args:
        samples: List of samples to analyze
        output_path: Optional path to write report

    Returns:
        Formatted report string
    """
    stats = compute_dataset_statistics(samples)
    validation = validate_dataset(samples)

    lines = [
        "=" * 60,
        "SYNTHETIC DATASET REPORT",
        "=" * 60,
        "",
        f"Total Samples: {stats['total_samples']:,}",
        f"Multi-script Documents: {stats['multi_script_count']:,}",
        "",
        "SCRIPT DISTRIBUTION:",
        "-" * 40,
    ]

    for script, count in sorted(
        stats["scripts"].items(), key=lambda x: x[1], reverse=True
    ):
        pct = 100 * count / stats["total_samples"]
        lines.append(f"  {script}: {count:,} ({pct:.1f}%)")

    lines.extend(
        [
            "",
            "SPLIT DISTRIBUTION:",
            "-" * 40,
        ]
    )
    for split, count in stats["splits"].items():
        pct = 100 * count / stats["total_samples"]
        lines.append(f"  {split}: {count:,} ({pct:.1f}%)")

    lines.extend(
        [
            "",
            "QUALITY TIER DISTRIBUTION:",
            "-" * 40,
        ]
    )
    for tier, count in sorted(stats["quality_tiers"].items()):
        pct = 100 * count / stats["total_samples"]
        lines.append(f"  {tier}: {count:,} ({pct:.1f}%)")

    lines.extend(
        [
            "",
            "RESOLUTION TIER DISTRIBUTION:",
            "-" * 40,
        ]
    )
    for tier, count in sorted(stats["resolution_tiers"].items()):
        pct = 100 * count / stats["total_samples"]
        lines.append(f"  {tier}: {count:,} ({pct:.1f}%)")

    lines.extend(
        [
            "",
            "LAYOUT DISTRIBUTION:",
            "-" * 40,
        ]
    )
    for layout, count in sorted(
        stats["layouts"].items(), key=lambda x: x[1], reverse=True
    ):
        pct = 100 * count / stats["total_samples"]
        lines.append(f"  {layout}: {count:,} ({pct:.1f}%)")

    lines.extend(
        [
            "",
            "LANGUAGE DIVERSITY:",
            "-" * 40,
        ]
    )
    for script, count in sorted(
        stats["language_counts_per_script"].items(), key=lambda x: x[1], reverse=True
    )[:10]:
        lines.append(f"  {script}: {count} unique languages")

    lines.extend(
        [
            "",
            "=" * 60,
            "VALIDATION RESULTS",
            "=" * 60,
            "",
            validation.summary(),
        ]
    )

    if validation.issues:
        lines.extend(["", "ISSUES:"])
        for issue in validation.issues:
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(issue.severity, "•")
            lines.append(f"  {icon} [{issue.category}] {issue.message}")

    report = "\n".join(lines)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        logger.info("Report written to %s", output_path)

    return report


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "compute_dataset_statistics",
    "create_stratified_splits",
    "generate_dataset_report",
    "validate_dataset",
]
