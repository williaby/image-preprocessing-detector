"""Tests for MarkushGrapher parser."""

from __future__ import annotations

from pathlib import Path

from image_preprocessing_detector.annotation.parsers.document.markushgrapher import (
    MarkushgrapherParser,
)


class TestMarkushgrapherParser:
    """Tests for MarkushgrapherParser."""

    def test_dataset_names(self) -> None:
        """Parser reports correct dataset names."""
        parser = MarkushgrapherParser()
        assert "markushgrapher" in parser.dataset_names

    def test_parse_returns_original_labels(self, tmp_path: Path) -> None:
        """Parse returns OriginalLabels instance."""
        parser = MarkushgrapherParser()
        # Create minimal test structure
        image = tmp_path / "test.png"
        image.write_bytes(b"fake png")
        labels = parser.parse(tmp_path, image, {})
        assert labels is not None

    def test_parse_sets_source(self, tmp_path: Path) -> None:
        """Parse sets source in raw_labels."""
        parser = MarkushgrapherParser()
        image = tmp_path / "test.png"
        image.write_bytes(b"fake png")
        labels = parser.parse(tmp_path, image, {})
        assert labels.raw_labels is not None
        assert labels.raw_labels.get("source") == "markushgrapher"
