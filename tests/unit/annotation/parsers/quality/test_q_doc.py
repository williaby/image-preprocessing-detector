"""Tests for Q-Doc parser."""

from __future__ import annotations

from pathlib import Path

from image_preprocessing_detector.annotation.parsers.quality.q_doc import (
    QDocParser,
)


class TestQDocParser:
    """Tests for QDocParser."""

    def test_dataset_names(self) -> None:
        """Parser reports correct dataset names."""
        parser = QDocParser()
        assert "q-doc" in parser.dataset_names

    def test_parse_returns_original_labels(self, tmp_path: Path) -> None:
        """Parse returns OriginalLabels instance."""
        parser = QDocParser()
        # Create minimal test structure
        image = tmp_path / "test.png"
        image.write_bytes(b"fake png")
        labels = parser.parse(tmp_path, image, {})
        assert labels is not None

    def test_parse_sets_source(self, tmp_path: Path) -> None:
        """Parse sets source in raw_labels."""
        parser = QDocParser()
        image = tmp_path / "test.png"
        image.write_bytes(b"fake png")
        labels = parser.parse(tmp_path, image, {})
        assert labels.raw_labels is not None
        assert labels.raw_labels.get("source") == "q-doc"
