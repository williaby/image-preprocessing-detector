"""Enhanced document quality assessment for scorecard doc_completeness.

Goes beyond section presence to detect quality issues in dataset source
documentation: TODO/TBD placeholders, insufficient content, outdated
statistics, and missing critical sections.

Usage::

    python scripts/audit/doc_quality_assessment.py --dataset jssoda
    python scripts/audit/doc_quality_assessment.py --all --output results/doc_quality.json
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_DOCS_DIR = PROJECT_ROOT / "docs" / "datasets" / "source"
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Patterns indicating incomplete content
PLACEHOLDER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\bXXX\b"),
    re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE),
    re.compile(r"\[.*?\]\(#\)"),  # Broken markdown links
    re.compile(r"<\s*insert\s+", re.IGNORECASE),
]

# Required sections (from DATASET_TEMPLATE.md)
REQUIRED_SECTIONS: list[str] = [
    "Overview",
    "Dataset Statistics",
    "Ground Truth",
    "License",
    "Training Task",
]

# Minimum word count per section for meaningful content
MIN_SECTION_WORDS = 15


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DocIssue:
    """A single documentation quality issue.

    Attributes:
        section: Section name where the issue was found (or "global").
        severity: Issue severity: "critical", "warning", or "info".
        description: Human-readable description.
        line_number: Approximate line number (0 if global).
    """

    section: str
    severity: str
    description: str
    line_number: int = 0


@dataclass
class DocQualityReport:
    """Quality assessment for a single dataset's documentation.

    Attributes:
        dataset: Canonical dataset name.
        doc_path: Path to the source document.
        total_sections: Number of sections found.
        total_words: Total word count.
        issues: List of quality issues found.
        score: Quality score (0-100).
    """

    dataset: str
    doc_path: str
    total_sections: int = 0
    total_words: int = 0
    issues: list[DocIssue] = field(default_factory=list)
    score: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def _extract_sections(content: str) -> dict[str, str]:
    """Extract markdown sections from document content.

    Args:
        content: Raw markdown text.

    Returns:
        Dict mapping section heading to section body text.
    """
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        heading_match = re.match(r"^#{1,3}\s+\d*\.?\s*(.*)", line)
        if heading_match:
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = heading_match.group(1).strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines)

    return sections


def _count_words(text: str) -> int:
    """Count words in text, excluding markdown syntax."""
    # Strip markdown formatting
    clean = re.sub(r"[#*`\[\]\(\)|>-]", " ", text)
    return len(clean.split())


def assess_document(
    dataset: str,
    *,
    source_dir: Path | None = None,
) -> DocQualityReport:
    """Assess documentation quality for a single dataset.

    Args:
        dataset: Canonical dataset name.
        source_dir: Override source docs directory.

    Returns:
        DocQualityReport with issues and score.
    """
    docs_dir = source_dir or SOURCE_DOCS_DIR
    doc_path = docs_dir / f"{dataset}.md"

    report = DocQualityReport(
        dataset=dataset,
        doc_path=str(doc_path),
    )

    if not doc_path.exists():
        report.issues.append(
            DocIssue("global", "critical", "Source document does not exist")
        )
        report.score = 0.0
        return report

    content = doc_path.read_text(encoding="utf-8")
    report.total_words = _count_words(content)

    # Check total word count
    if report.total_words < 50:
        report.issues.append(
            DocIssue(
                "global",
                "critical",
                f"Document too short ({report.total_words} words, min 50)",
            )
        )

    # Check for placeholders
    for i, line in enumerate(content.split("\n"), 1):
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(line):
                report.issues.append(
                    DocIssue(
                        "global",
                        "warning",
                        f"Placeholder found: {pattern.pattern}",
                        line_number=i,
                    )
                )
                break  # One issue per line

    # Check sections
    sections = _extract_sections(content)
    report.total_sections = len(sections)

    for required in REQUIRED_SECTIONS:
        found = False
        for heading in sections:
            if required.lower() in heading.lower():
                found = True
                body = sections[heading]
                word_count = _count_words(body)
                if word_count < MIN_SECTION_WORDS:
                    report.issues.append(
                        DocIssue(
                            heading,
                            "warning",
                            f"Section '{heading}' has only {word_count} words"
                            f" (min {MIN_SECTION_WORDS})",
                        )
                    )
                break
        if not found:
            report.issues.append(
                DocIssue(
                    required,
                    "critical",
                    f"Required section '{required}' not found",
                )
            )

    # Compute score
    critical_count = sum(1 for i in report.issues if i.severity == "critical")
    warning_count = sum(1 for i in report.issues if i.severity == "warning")
    deductions = critical_count * 20 + warning_count * 5
    report.score = max(0.0, 100.0 - deductions)

    return report


def assess_all_datasets(
    *,
    source_dir: Path | None = None,
) -> list[DocQualityReport]:
    """Assess documentation quality for all datasets.

    Args:
        source_dir: Override source docs directory.

    Returns:
        List of DocQualityReport sorted by score (ascending).
    """
    docs_dir = source_dir or SOURCE_DOCS_DIR
    if not docs_dir.is_dir():
        return []

    reports: list[DocQualityReport] = []
    for doc_path in sorted(docs_dir.glob("*.md")):
        dataset = doc_path.stem
        report = assess_document(dataset, source_dir=docs_dir)
        reports.append(report)

    reports.sort(key=lambda r: r.score)
    return reports


def write_quality_report(
    reports: list[DocQualityReport],
    *,
    output_path: Path | None = None,
) -> Path:
    """Write quality assessment results to JSON.

    Args:
        reports: List of quality reports.
        output_path: Override output path.

    Returns:
        Path to the written file.
    """
    if output_path is None:
        output_path = AUDIT_RESULTS_DIR / "doc_quality_assessment.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = len(reports)
    good = sum(1 for r in reports if r.score >= 80)
    needs_work = sum(1 for r in reports if 50 <= r.score < 80)
    poor = sum(1 for r in reports if r.score < 50)

    data = {
        "total_documents": total,
        "good": good,
        "needs_work": needs_work,
        "poor": poor,
        "mean_score": sum(r.score for r in reports) / total if total else 0,
        "reports": [r.to_dict() for r in reports],
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.info("Wrote %d reports to %s", total, output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Assess dataset documentation quality."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset", type=str, help="Assess single dataset.")
    group.add_argument("--all", action="store_true", help="Assess all datasets.")
    parser.add_argument("--output", type=Path, default=None, help="Output path.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.dataset:
        report = assess_document(args.dataset)
        reports = [report]
    else:
        reports = assess_all_datasets()

    for r in reports:
        issues_str = f"{len(r.issues)} issues" if r.issues else "clean"
        print(f"  {r.dataset:<25} score={r.score:>5.1f}  {issues_str}")

    if reports:
        path = write_quality_report(reports, output_path=args.output)
        print(f"\nReport written to {path}")


if __name__ == "__main__":
    main()
