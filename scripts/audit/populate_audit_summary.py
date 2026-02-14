#!/usr/bin/env python3
"""Populate Section 11 (Layer 2 Audit Summary) in dataset source docs.

Reads scorecard.json, defect_catalog.json, and vlm_corrections.json from
scripts/audit/results/{dataset}/ and writes/updates Section 11 in the
corresponding docs/datasets/source/{dataset}.md file.

Usage:
    # Single dataset
    PYTHONPATH=. uv run python3 scripts/audit/populate_audit_summary.py --dataset ohr-bench

    # All datasets missing Section 11
    PYTHONPATH=. uv run python3 scripts/audit/populate_audit_summary.py --all-missing

    # All datasets (overwrite existing)
    PYTHONPATH=. uv run python3 scripts/audit/populate_audit_summary.py --all --overwrite

    # Dry run (preview without writing)
    PYTHONPATH=. uv run python3 scripts/audit/populate_audit_summary.py --all-missing --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Project root for resolving paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"
SOURCE_DOCS_DIR = PROJECT_ROOT / "docs" / "datasets" / "source"

# Dimension display names (order matches template)
DIMENSION_DISPLAY = {
    "field_coverage": "Field Coverage",
    "field_validity": "Field Validity",
    "doc_completeness": "Doc Completeness",
    "defect_rate": "Defect Rate",
    "cross_source_agreement": "Cross-Source Agreement",
    "vlm_accuracy": "VLM Accuracy",
}

# Standard dimension order for the scorecard table
DIMENSION_ORDER = [
    "field_coverage",
    "field_validity",
    "doc_completeness",
    "defect_rate",
    "cross_source_agreement",
    "vlm_accuracy",
]


@dataclass
class AuditArtifacts:
    """Container for audit JSON artifacts."""

    dataset: str
    scorecard: dict | None = None
    defect_catalog: dict | None = None
    vlm_corrections: dict | None = None
    results_dir: Path = field(default_factory=lambda: Path("."))

    @classmethod
    def load(cls, dataset: str) -> AuditArtifacts:
        """Load all available audit artifacts for a dataset."""
        results = RESULTS_DIR / dataset
        if not results.is_dir():
            msg = f"No audit results directory found: {results}"
            raise FileNotFoundError(msg)

        artifacts = cls(dataset=dataset, results_dir=results)

        scorecard_path = results / "scorecard.json"
        if scorecard_path.exists():
            with open(scorecard_path) as fh:
                artifacts.scorecard = json.load(fh)

        defect_path = results / "defect_catalog.json"
        if defect_path.exists():
            with open(defect_path) as fh:
                artifacts.defect_catalog = json.load(fh)

        vlm_path = results / "vlm_corrections.json"
        if vlm_path.exists():
            with open(vlm_path) as fh:
                artifacts.vlm_corrections = json.load(fh)

        return artifacts


def _resolve_source_doc(dataset: str) -> Path | None:
    """Find the source doc for a dataset, handling hyphen/no-hyphen variants.

    Resolution order:
    1. Exact match: {dataset}.md
    2. Dehyphenated match: remove all hyphens from both sides
    3. Prefix/substring match: source doc stem starts with or is contained in dataset name
       (handles cases like 'arabic-docs-ocr' -> 'arabic-docs.md')
    """
    # Direct match
    direct = SOURCE_DOCS_DIR / f"{dataset}.md"
    if direct.exists():
        return direct

    # Try hyphenated/dehyphenated variants
    normalized = dataset.replace("-", "")
    candidates = [
        c for c in SOURCE_DOCS_DIR.glob("*.md") if c.name != "README.md"
    ]

    for candidate in candidates:
        if candidate.stem.replace("-", "") == normalized:
            return candidate

    # Prefix/substring match: dataset name starts with or contains the stem
    # e.g., 'arabic-docs-ocr' starts with 'arabic-docs'
    best_match: Path | None = None
    best_len = 0
    for candidate in candidates:
        stem = candidate.stem
        if dataset.startswith(stem) and len(stem) > best_len:
            best_match = candidate
            best_len = len(stem)

    return best_match


def _detect_heading_level(doc_content: str) -> str:
    """Detect the heading level used for numbered sections in the doc.

    Returns the prefix to use for Section 11 heading (e.g., '####' or '#####').
    Looks at existing numbered section headings to determine the pattern.
    """
    # Look for patterns like "#### 10." or "##### 10." or "#### 9."
    for pattern in [
        r"^(#{2,5})\s+(?:10|9|8|7)\.",
        r"^(#{2,5})\s+(?:Layer 2|Known|Reliability)",
    ]:
        match = re.search(pattern, doc_content, re.MULTILINE)
        if match:
            return match.group(1)

    # Default to #### (template standard)
    return "####"


def _format_score(score: float | None) -> str:
    """Format a dimension score, handling None."""
    if score is None:
        return "-"
    return f"{score:.1f}"


def _format_weight(weight: float) -> str:
    """Format a weight as percentage string."""
    return f"{weight * 100:.0f}%"


def _build_scorecard_section(
    artifacts: AuditArtifacts,
    h2: str,
    h3: str,
) -> str:
    """Build the 11.1 Quality Scorecard subsection."""
    sc = artifacts.scorecard
    if sc is None:
        return ""

    # Extract audit date from computed_at
    computed_at = sc.get("computed_at", "")
    audit_date = computed_at[:10] if computed_at else datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    grade = sc.get("grade", "?")
    overall = sc.get("overall_score", 0.0)
    grade_cap = sc.get("grade_cap_applied", "")

    lines = [
        f"{h3} 11.1 Quality Scorecard",
        "",
        f"> **Audit Date**: {audit_date} | **Grade**: {grade} ({overall:.1f}/100) | **Auditor**: claude-opus-4-6",
        "",
    ]

    # Grade cap notice
    if grade_cap:
        # Extract the short form: "Grade capped from X to Y: reason"
        cap_match = re.match(r"Grade capped from (\w) to (\w):", grade_cap)
        if cap_match:
            uncapped = cap_match.group(1)
            lines.append(f"> **Grade Cap**: {uncapped} -> {grade} (see notes below)")
            lines.append("")

    # Scorecard table
    lines.extend([
        "| Dimension | Score | Weight | Notes |",
        "|-----------|------:|-------:|-------|",
    ])

    dimensions = sc.get("dimensions", {})
    excluded = sc.get("excluded_dimensions", [])

    for dim_key in DIMENSION_ORDER:
        display_name = DIMENSION_DISPLAY[dim_key]
        dim_data = dimensions.get(dim_key)

        if dim_key in excluded or dim_data is None:
            lines.append(f"| {display_name} | - | - | Excluded (no data) |")
            continue

        score_val = dim_data.get("score")
        weight_val = dim_data.get("effective_weight")
        notes = ""

        if score_val is None or weight_val is None:
            lines.append(f"| {display_name} | - | - | Excluded (no data) |")
            continue

        # Add contextual notes for notable scores
        if score_val == 0.0:
            notes = "No cross-source data"
        elif score_val < 70:
            notes = "Below threshold"

        lines.append(
            f"| {display_name} | {_format_score(score_val)} | {_format_weight(weight_val)} | {notes} |"
        )

    # Overall row
    lines.append(f"| **Overall** | **{overall:.1f}** | | **Grade {grade}** |")
    lines.append("")

    # Grade cap explanation
    if grade_cap:
        lines.extend([
            "**Grade Cap Applied**:",
            f"> {grade_cap}",
            "",
        ])

    return "\n".join(lines)


def _build_defects_section(
    artifacts: AuditArtifacts,
    h3: str,
) -> str:
    """Build the 11.2 Key Defects subsection."""
    lines = [f"{h3} 11.2 Key Defects", ""]

    dc = artifacts.defect_catalog
    if dc is None:
        lines.extend([
            "No defect catalog available for this dataset.",
            "",
        ])
        return "\n".join(lines)

    defects = dc.get("defects", [])
    summary = dc.get("defect_summary", {})

    if not defects:
        lines.extend([
            "No defects identified during audit.",
            "",
        ])
        return "\n".join(lines)

    # Summary line
    total = summary.get("total_defects", len(defects))
    # Count by status
    status_counts: dict[str, int] = {}
    for defect in defects:
        status = defect.get("status", "open").upper()
        # Normalize status names
        if status in ("FIXED", "RESOLVED"):
            status = "RESOLVED"
        elif status == "PARTIALLY_RESOLVED":
            status = "PARTIAL"
        status_counts[status] = status_counts.get(status, 0) + 1

    status_parts = []
    for status_name in ["RESOLVED", "ACCEPTED", "DEFERRED", "PARTIAL", "OPEN"]:
        count = status_counts.get(status_name, 0)
        if count > 0:
            status_parts.append(f"{count} {status_name.lower()}")

    lines.append(f"> **Total**: {total} defects ({', '.join(status_parts)})")
    lines.append("")

    # Defect table
    lines.extend([
        "| ID | Field | Severity | Status | Description |",
        "|----|-------|----------|--------|-------------|",
    ])

    for defect in defects:
        did = defect.get("id", "?")
        d_field = defect.get("field", "?")
        severity = defect.get("severity", "?")
        status = defect.get("status", "open").upper()
        if status in ("FIXED",):
            status = "RESOLVED"
        title = defect.get("title", defect.get("description", "")[:80])
        # Escape pipe characters in title
        title = title.replace("|", "\\|")

        lines.append(f"| {did} | {d_field} | {severity} | {status} | {title} |")

    lines.append("")
    return "\n".join(lines)


def _build_vlm_section(
    artifacts: AuditArtifacts,
    h3: str,
) -> str:
    """Build the 11.3 VLM Inspection Summary subsection."""
    lines = [f"{h3} 11.3 VLM Inspection Summary", ""]

    vlm = artifacts.vlm_corrections
    if vlm is None:
        lines.extend([
            "No VLM inspection data available.",
            "",
        ])
        return "\n".join(lines)

    # Check if VLM was deferred
    vlm_status = vlm.get("vlm_inspection_status", "")
    if vlm_status == "deferred":
        reason = vlm.get("reason", "Deferred to manual review")
        lines.extend([
            f"> **Status**: Deferred -- {reason}",
            "",
        ])
        return "\n".join(lines)

    total_inspected = vlm.get("total_samples_inspected", 0)
    total_corrections = vlm.get("total_corrections", 0)
    accuracy = vlm.get("passing_sample_accuracy")

    accuracy_str = f"{accuracy * 100:.1f}%" if accuracy is not None else "N/A"

    lines.append(
        f"> **Samples Inspected**: {total_inspected} | "
        f"**Corrections**: {total_corrections} | "
        f"**Passing Accuracy**: {accuracy_str}"
    )
    lines.append("")

    # Accuracy by field (if available)
    validation = vlm.get("validation_summary", {})
    accuracy_by_field = validation.get("accuracy_by_field", {})

    if accuracy_by_field:
        lines.extend([
            "| Field | Correct | Incorrect | Accuracy | Notes |",
            "|-------|--------:|----------:|---------:|-------|",
        ])

        for field_name, field_data in accuracy_by_field.items():
            correct = field_data.get("correct", 0)
            incorrect = field_data.get("incorrect", 0)
            flagged = field_data.get("flagged", 0)
            # Some fields use "flagged" instead of "incorrect"
            wrong = incorrect or flagged
            pct = field_data.get("pct", 0.0)
            note = field_data.get("note", "")
            note = note.replace("|", "\\|")

            lines.append(
                f"| {field_name} | {correct} | {wrong} | {pct:.1f}% | {note} |"
            )
        lines.append("")

    # Content flag distribution (if available)
    content_flags = validation.get("content_flag_distribution", {})
    if content_flags:
        lines.extend([
            "**Content Flag Distribution** (in inspected samples):",
            "",
            "| Flag | Count | Percentage |",
            "|------|------:|-----------:|",
        ])

        for flag_name, flag_data in content_flags.items():
            count = flag_data.get("count", 0)
            pct = flag_data.get("pct", 0.0)
            lines.append(f"| {flag_name} | {count} | {pct:.1f}% |")

        lines.append("")

    # Grade cap removal info
    cap_info = vlm.get("grade_cap_removal", {})
    if cap_info:
        vlm_complete = cap_info.get("vlm_inspection_complete", False)
        threshold_met = cap_info.get("vlm_accuracy_threshold_met", False)
        if vlm_complete and threshold_met:
            achieved = cap_info.get("achieved", 0.0)
            threshold = cap_info.get("threshold", 90.0)
            lines.append(
                f"**VLM Grade Cap**: Removed (accuracy {achieved:.1f}% >= {threshold:.0f}% threshold)"
            )
            lines.append("")

    return "\n".join(lines)


def _build_cross_dataset_section(
    artifacts: AuditArtifacts,
    h3: str,
) -> str:
    """Build the 11.4 Cross-Dataset Findings subsection."""
    lines = [f"{h3} 11.4 Cross-Dataset Findings", ""]

    # Extract KI references from defect catalog
    ki_refs: list[str] = []
    dc = artifacts.defect_catalog
    if dc is not None:
        for defect in dc.get("defects", []):
            ki = defect.get("known_issue")
            if ki:
                status = defect.get("status", "open").upper()
                if status in ("FIXED", "RESOLVED"):
                    status = "RESOLVED"
                title = defect.get("title", "")
                ki_refs.append(f"- **{ki}**: {status} -- {title}")

    if ki_refs:
        lines.extend(ki_refs)
    else:
        lines.append("- No cross-dataset known issues identified for this dataset.")

    lines.extend([
        "",
        f"**Audit Artifacts**: [scripts/audit/results/{artifacts.dataset}/](../../scripts/audit/results/{artifacts.dataset}/)",
        "",
    ])

    return "\n".join(lines)


def generate_section_11(artifacts: AuditArtifacts) -> str:
    """Generate the full Section 11 markdown content."""
    if artifacts.scorecard is None:
        msg = f"No scorecard.json found for {artifacts.dataset}"
        raise FileNotFoundError(msg)

    # We'll use #### for the main heading and ##### for subsections (template standard)
    # The actual heading level will be adjusted when inserting into the doc
    h2 = "####"
    h3 = "#####"

    parts = [
        f"{h2} 11. Layer 2 Audit Summary",
        "",
        "> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated",
        "> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and",
        "> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).",
        "",
        _build_scorecard_section(artifacts, h2, h3),
        _build_defects_section(artifacts, h3),
        _build_vlm_section(artifacts, h3),
        _build_cross_dataset_section(artifacts, h3),
    ]

    return "\n".join(parts)


def _find_section_11_bounds(content: str) -> tuple[int, int] | None:
    """Find the start and end character positions of Section 11 in the doc.

    Returns (start, end) tuple or None if not found.
    End position is the start of the next section at the same or higher heading level.
    """
    # Match "#### 11." or "##### 11." or similar
    pattern = r"^(#{2,5})\s+(?:11\.?\s+)?Layer 2 Audit Summary"
    match = re.search(pattern, content, re.MULTILINE)
    if match is None:
        return None

    start = match.start()
    heading_level = len(match.group(1))

    # Find the next heading at same or higher level
    rest = content[match.end():]
    next_heading = re.search(
        rf"^#{{2,{heading_level}}}\s+",
        rest,
        re.MULTILINE,
    )

    if next_heading:
        end = match.end() + next_heading.start()
    else:
        end = len(content)

    return (start, end)


def _find_insertion_point(content: str) -> tuple[int, str]:
    """Find where to insert Section 11 and the heading level to use.

    Looks for Section 12 (Reliability) or Version History as the anchor,
    then inserts before it. Falls back to end of file.

    Returns (position, heading_prefix).
    """
    # Detect heading level from existing numbered sections
    heading_prefix = _detect_heading_level(content)

    # Try to find Section 12 or Reliability section
    for pattern in [
        r"^(#{2,5})\s+(?:12\.?\s+)?Reliability",
        r"^(#{2,5})\s+(?:Version History|Changelog)",
        r"^(#{2,5})\s+(?:Processing Notes|Version)",
    ]:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            heading_prefix = match.group(1)
            return (match.start(), heading_prefix)

    # If no anchor found, insert before the last "---" separator or at end
    last_separator = content.rfind("\n---\n")
    if last_separator > 0:
        return (last_separator, heading_prefix)

    return (len(content), heading_prefix)


def _adjust_heading_levels(section_content: str, target_prefix: str) -> str:
    """Adjust heading levels in the generated section to match the target doc."""
    # Default generation uses #### for h2 and ##### for h3
    default_h2 = "####"
    default_h3 = "#####"

    if target_prefix == default_h2:
        return section_content

    # Calculate the offset
    target_len = len(target_prefix)
    default_len = len(default_h2)
    offset = target_len - default_len

    if offset == 0:
        return section_content

    # Adjust all heading levels
    def adjust_heading(m: re.Match[str]) -> str:
        hashes = m.group(1)
        rest = m.group(2)
        new_len = len(hashes) + offset
        # Clamp to 2-6
        new_len = max(2, min(6, new_len))
        return "#" * new_len + rest

    return re.sub(r"^(#{2,6})([ \t])", adjust_heading, section_content, flags=re.MULTILINE)


def update_source_doc(
    dataset: str,
    artifacts: AuditArtifacts,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> bool:
    """Update a dataset source doc with Section 11 content.

    Returns True if the file was modified (or would be in dry_run mode).
    """
    doc_path = _resolve_source_doc(dataset)
    if doc_path is None:
        print(f"  SKIP: No source doc found for '{dataset}'")
        return False

    content = doc_path.read_text(encoding="utf-8")

    # Check if Section 11 already exists
    existing_bounds = _find_section_11_bounds(content)

    if existing_bounds is not None and not overwrite:
        print(f"  SKIP: Section 11 already exists in {doc_path.name} (use --overwrite to replace)")
        return False

    # Generate the new Section 11
    section_content = generate_section_11(artifacts)

    if existing_bounds is not None:
        # Replace existing section
        start, end = existing_bounds
        # Detect heading level from existing section
        existing_heading = re.match(r"^(#{2,5})", content[start:])
        if existing_heading:
            heading_prefix = existing_heading.group(1)
        else:
            heading_prefix = "####"

        section_content = _adjust_heading_levels(section_content, heading_prefix)

        # Ensure clean boundaries
        before = content[:start].rstrip("\n") + "\n\n"
        after = content[end:].lstrip("\n")
        if not after.startswith("\n"):
            after = "\n" + after

        new_content = before + section_content.rstrip("\n") + "\n\n" + after
        action = "REPLACE"
    else:
        # Insert new section
        insert_pos, heading_prefix = _find_insertion_point(content)
        section_content = _adjust_heading_levels(section_content, heading_prefix)

        before = content[:insert_pos].rstrip("\n") + "\n\n"
        after = content[insert_pos:].lstrip("\n")
        if after and not after.startswith("\n"):
            after = "\n" + after

        # Add separator before section
        new_content = before + section_content.rstrip("\n") + "\n\n---\n" + after
        action = "INSERT"

    if dry_run:
        print(f"  DRY RUN ({action}): Would update {doc_path.name}")
        # Show first 20 lines of generated section
        preview_lines = section_content.split("\n")[:20]
        for line in preview_lines:
            print(f"    | {line}")
        if len(section_content.split("\n")) > 20:
            print(f"    | ... ({len(section_content.split(chr(10)))} total lines)")
        return True

    doc_path.write_text(new_content, encoding="utf-8")
    print(f"  {action}: Updated {doc_path.name}")
    return True


def get_datasets_with_scorecards() -> list[str]:
    """List all datasets that have scorecard.json in results."""
    datasets = []
    for result_dir in sorted(RESULTS_DIR.iterdir()):
        if result_dir.is_dir() and (result_dir / "scorecard.json").exists():
            datasets.append(result_dir.name)
    return datasets


def get_datasets_missing_section_11() -> list[str]:
    """List datasets that have scorecards but are missing Section 11 in source docs."""
    missing = []
    for dataset in get_datasets_with_scorecards():
        doc_path = _resolve_source_doc(dataset)
        if doc_path is None:
            continue
        content = doc_path.read_text(encoding="utf-8")
        if _find_section_11_bounds(content) is None:
            missing.append(dataset)
    return missing


def main() -> None:
    """Entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Populate Section 11 (Layer 2 Audit Summary) in dataset source docs.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset", help="Single dataset to update")
    group.add_argument("--all-missing", action="store_true", help="Update all datasets missing Section 11")
    group.add_argument("--all", action="store_true", help="Update all datasets with scorecards")
    group.add_argument("--list-missing", action="store_true", help="List datasets missing Section 11")

    parser.add_argument("--overwrite", action="store_true", help="Replace existing Section 11 content")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.list_missing:
        missing = get_datasets_missing_section_11()
        print(f"Datasets missing Section 11 ({len(missing)}):")
        for ds in missing:
            print(f"  - {ds}")
        return

    # Determine dataset list
    if args.dataset:
        datasets = [args.dataset]
    elif args.all_missing:
        datasets = get_datasets_missing_section_11()
        print(f"Found {len(datasets)} datasets missing Section 11")
    else:
        datasets = get_datasets_with_scorecards()
        print(f"Found {len(datasets)} datasets with scorecards")

    if not datasets:
        print("No datasets to process.")
        return

    updated = 0
    skipped = 0
    errors = 0

    for dataset in datasets:
        print(f"\nProcessing: {dataset}")
        try:
            artifacts = AuditArtifacts.load(dataset)
            if artifacts.scorecard is None:
                print(f"  SKIP: No scorecard.json for {dataset}")
                skipped += 1
                continue

            result = update_source_doc(
                dataset,
                artifacts,
                overwrite=args.overwrite or args.all,
                dry_run=args.dry_run,
            )
            if result:
                updated += 1
            else:
                skipped += 1
        except FileNotFoundError as exc:
            print(f"  ERROR: {exc}")
            errors += 1
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors += 1

    print(f"\n{'=' * 50}")
    print(f"Summary: {updated} updated, {skipped} skipped, {errors} errors")
    if args.dry_run:
        print("(dry run -- no files were modified)")


if __name__ == "__main__":
    main()
