"""Tests for document quality assessment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.doc_quality_assessment import (
    DocQualityReport,
    assess_all_datasets,
    assess_document,
    write_quality_report,
)


@pytest.fixture
def good_doc(tmp_path: Path) -> Path:
    """Create a well-structured dataset doc."""
    doc = tmp_path / "good-dataset.md"
    doc.write_text(
        """# good-dataset

## 1. Overview

This is a comprehensive dataset for document image analysis.
It contains high-quality scanned documents from various sources
with carefully annotated ground truth labels for training and evaluation.

## 2. Dataset Statistics

- Total images: 10,000
- Format: JPEG
- Resolution: 300 DPI average
- Size: 5.2 GB
- Categories: 15 document types

## 3. Ground Truth

All images have manually annotated bounding boxes using COCO format.
Inter-annotator agreement (IAA) measured at kappa=0.92.
Two-pass annotation with expert adjudication for disagreements.

## 4. License

Apache 2.0. Free for research and commercial use.
Original paper must be cited per license terms.

## 5. Training Task Suitability

Primary: Layout detection and document classification.
Supplementary: Table structure recognition.
Well-suited for transfer learning with DocLayNet pretraining.
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def bad_doc(tmp_path: Path) -> Path:
    """Create a poorly-structured dataset doc with issues."""
    doc = tmp_path / "bad-dataset.md"
    doc.write_text(
        """# bad-dataset

## 1. Overview

TODO: Write overview.

## 2. Dataset Statistics

TBD

## Notes

TODO(audit): Need to add license info.
""",
        encoding="utf-8",
    )
    return tmp_path


class TestAssessDocument:
    """Tests for assess_document."""

    def test_good_document(self, good_doc: Path) -> None:
        report = assess_document("good-dataset", source_dir=good_doc)
        assert report.score >= 80.0
        assert report.total_words > 50

    def test_bad_document(self, bad_doc: Path) -> None:
        report = assess_document("bad-dataset", source_dir=bad_doc)
        assert report.score < 80.0
        assert len(report.issues) > 0

    def test_missing_document(self, tmp_path: Path) -> None:
        report = assess_document("nonexistent", source_dir=tmp_path)
        assert report.score == 0.0
        assert any(i.severity == "critical" for i in report.issues)

    def test_detects_placeholders(self, bad_doc: Path) -> None:
        report = assess_document("bad-dataset", source_dir=bad_doc)
        placeholder_issues = [
            i
            for i in report.issues
            if "Placeholder" in i.description or "placeholder" in i.description.lower()
        ]
        assert len(placeholder_issues) > 0

    def test_detects_missing_sections(self, bad_doc: Path) -> None:
        report = assess_document("bad-dataset", source_dir=bad_doc)
        missing = [i for i in report.issues if "not found" in i.description]
        # Should flag missing License and Ground Truth
        assert len(missing) >= 2

    def test_detects_short_sections(self, bad_doc: Path) -> None:
        report = assess_document("bad-dataset", source_dir=bad_doc)
        short = [
            i
            for i in report.issues
            if "words" in i.description and "only" in i.description
        ]
        assert len(short) > 0

    def test_reports_total_sections(self, good_doc: Path) -> None:
        report = assess_document("good-dataset", source_dir=good_doc)
        assert report.total_sections >= 5


class TestAssessAllDatasets:
    """Tests for assess_all_datasets."""

    def test_assesses_multiple(self, tmp_path: Path) -> None:
        for name in ["alpha", "beta", "gamma"]:
            (tmp_path / f"{name}.md").write_text(
                f"# {name}\n\n## 1. Overview\n\nA dataset.\n",
                encoding="utf-8",
            )
        reports = assess_all_datasets(source_dir=tmp_path)
        assert len(reports) == 3

    def test_sorted_by_score(self, tmp_path: Path) -> None:
        # Good doc
        (tmp_path / "good.md").write_text(
            "# good\n\n## 1. Overview\n\n"
            + "This is a detailed overview of a good dataset. " * 10
            + "\n## 2. Dataset Statistics\n\n"
            + "Contains 10000 images across 15 categories. " * 3
            + "\n## 3. Ground Truth\n\n"
            + "Manually annotated with bounding boxes and labels. " * 3
            + "\n## 4. License\n\n"
            + "Apache 2.0. Free for research and commercial use. " * 2
            + "\n## 5. Training Task\n\n"
            + "Primary task is layout detection and classification. " * 3,
            encoding="utf-8",
        )
        # Bad doc
        (tmp_path / "bad.md").write_text(
            "# bad\n\nTODO\n",
            encoding="utf-8",
        )
        reports = assess_all_datasets(source_dir=tmp_path)
        # Sorted ascending by score
        assert reports[0].dataset == "bad"
        assert reports[-1].dataset == "good"

    def test_empty_dir(self, tmp_path: Path) -> None:
        reports = assess_all_datasets(source_dir=tmp_path)
        assert reports == []


class TestWriteQualityReport:
    """Tests for write_quality_report."""

    def test_writes_json(self, tmp_path: Path) -> None:
        reports = [
            DocQualityReport(
                dataset="test",
                doc_path="/tmp/test.md",
                total_sections=5,
                total_words=200,
                score=85.0,
            )
        ]
        path = write_quality_report(reports, output_path=tmp_path / "report.json")
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["total_documents"] == 1
        assert data["good"] == 1
        assert data["mean_score"] == 85.0

    def test_categorizes_scores(self, tmp_path: Path) -> None:
        reports = [
            DocQualityReport(dataset="a", doc_path="", score=90.0),
            DocQualityReport(dataset="b", doc_path="", score=65.0),
            DocQualityReport(dataset="c", doc_path="", score=30.0),
        ]
        path = write_quality_report(reports, output_path=tmp_path / "report.json")
        with path.open() as f:
            data = json.load(f)
        assert data["good"] == 1
        assert data["needs_work"] == 1
        assert data["poor"] == 1
