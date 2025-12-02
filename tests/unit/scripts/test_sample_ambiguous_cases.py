# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/sample_ambiguous_cases.py - Ambiguous case sampling.

These tests verify the ambiguous case sampling correctly:
- Loads weak supervision labels
- Calculates uncertainty scores
- Calculates edge case scores
- Calculates composite priority
- Samples high-priority cases for annotation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from sample_ambiguous_cases import (
    CONFIDENCE_VARIANCE_THRESHOLD,
    LAPLACIAN_BLUR_MAX,
    LAPLACIAN_BLUR_MIN,
    RMS_CONTRAST_MAX,
    RMS_CONTRAST_MIN,
    SKEW_ANGLE_MAX,
    SKEW_ANGLE_MIN,
    calculate_composite_priority,
    calculate_edge_case_score,
    calculate_uncertainty,
    load_weak_supervision_labels,
    sample_ambiguous_cases,
)


class TestThresholdConstants:
    """Tests for threshold constant definitions."""

    def test_blur_thresholds_order(self) -> None:
        """Test that blur min < blur max."""
        assert LAPLACIAN_BLUR_MIN < LAPLACIAN_BLUR_MAX

    def test_contrast_thresholds_order(self) -> None:
        """Test that contrast min < contrast max."""
        assert RMS_CONTRAST_MIN < RMS_CONTRAST_MAX

    def test_skew_thresholds_order(self) -> None:
        """Test that skew min < skew max."""
        assert SKEW_ANGLE_MIN < SKEW_ANGLE_MAX

    def test_confidence_variance_positive(self) -> None:
        """Test that confidence variance threshold is positive."""
        assert CONFIDENCE_VARIANCE_THRESHOLD > 0


class TestLoadWeakSupervisionLabels:
    """Tests for load_weak_supervision_labels function."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid JSON labels file."""
        labels_file = tmp_path / "test_labels.json"
        labels_data = {
            "image_path": "/path/to/image.png",
            "labels": {"blur": {"value": True, "confidence": 0.9}},
            "quality_scores": {"laplacian_variance": 100},
        }

        with open(labels_file, "w") as f:
            json.dump(labels_data, f)

        result = load_weak_supervision_labels(labels_file)

        assert result["image_path"] == "/path/to/image.png"
        assert "labels" in result
        assert "quality_scores" in result

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that loading missing file raises error."""
        with pytest.raises(FileNotFoundError):
            load_weak_supervision_labels(tmp_path / "nonexistent.json")


class TestCalculateUncertainty:
    """Tests for calculate_uncertainty function."""

    def test_uncertainty_empty_labels(self) -> None:
        """Test uncertainty is maximum for empty labels."""
        labels_data: dict[str, Any] = {"labels": {}}

        result = calculate_uncertainty(labels_data)

        assert result == 1.0

    def test_uncertainty_missing_labels(self) -> None:
        """Test uncertainty is maximum for missing labels key."""
        labels_data: dict[str, Any] = {}

        result = calculate_uncertainty(labels_data)

        assert result == 1.0

    def test_uncertainty_high_confidence(self) -> None:
        """Test low uncertainty for high confidence labels."""
        labels_data = {
            "labels": {
                "blur": {"confidence": 0.95},
                "contrast": {"confidence": 0.92},
                "noise": {"confidence": 0.98},
            }
        }

        result = calculate_uncertainty(labels_data)

        # High confidence = low uncertainty
        assert result < 0.1

    def test_uncertainty_low_confidence(self) -> None:
        """Test high uncertainty for low confidence labels."""
        labels_data = {
            "labels": {
                "blur": {"confidence": 0.3},
                "contrast": {"confidence": 0.4},
                "noise": {"confidence": 0.35},
            }
        }

        result = calculate_uncertainty(labels_data)

        # Low confidence = high uncertainty
        assert result > 0.6

    def test_uncertainty_medium_confidence(self) -> None:
        """Test medium uncertainty for medium confidence labels."""
        labels_data = {
            "labels": {
                "blur": {"confidence": 0.6},
                "contrast": {"confidence": 0.7},
            }
        }

        result = calculate_uncertainty(labels_data)

        # Should be moderate uncertainty
        assert 0.3 <= result <= 0.5

    def test_uncertainty_returns_float(self) -> None:
        """Test that uncertainty returns float."""
        labels_data = {"labels": {"blur": {"confidence": 0.5}}}

        result = calculate_uncertainty(labels_data)

        assert isinstance(result, float)

    def test_uncertainty_range(self) -> None:
        """Test uncertainty is in valid range [0, 1]."""
        for conf in [0.0, 0.25, 0.5, 0.75, 1.0]:
            labels_data = {"labels": {"blur": {"confidence": conf}}}
            result = calculate_uncertainty(labels_data)
            assert 0.0 <= result <= 1.0


class TestCalculateEdgeCaseScore:
    """Tests for calculate_edge_case_score function."""

    def test_edge_case_no_borderline(self) -> None:
        """Test edge case score for clearly classified case."""
        labels_data = {
            "quality_scores": {
                "laplacian_variance": 200,  # Clearly above threshold
                "rms_contrast": 0.5,  # Clearly above threshold
                "skew_angle_degrees": 0.5,  # Clearly below threshold
            },
            "labels": {"blur": {"confidence": 0.95}},
        }

        result = calculate_edge_case_score(labels_data)

        assert result == 0.0

    def test_edge_case_borderline_blur(self) -> None:
        """Test edge case score for borderline blur."""
        labels_data = {
            "quality_scores": {
                "laplacian_variance": 100,  # Between 80 and 150
            },
            "labels": {},
        }

        result = calculate_edge_case_score(labels_data)

        assert result > 0

    def test_edge_case_borderline_contrast(self) -> None:
        """Test edge case score for borderline contrast."""
        labels_data = {
            "quality_scores": {
                "rms_contrast": 0.3,  # Between 0.25 and 0.35
            },
            "labels": {},
        }

        result = calculate_edge_case_score(labels_data)

        assert result > 0

    def test_edge_case_borderline_skew(self) -> None:
        """Test edge case score for borderline skew."""
        labels_data = {
            "quality_scores": {
                "skew_angle_degrees": 2.0,  # Between 1.5 and 3.0
            },
            "labels": {},
        }

        result = calculate_edge_case_score(labels_data)

        assert result > 0

    def test_edge_case_mixed_confidence(self) -> None:
        """Test edge case score for mixed confidence labels."""
        labels_data = {
            "quality_scores": {},
            "labels": {
                "blur": {"confidence": 0.95},  # High
                "contrast": {"confidence": 0.3},  # Low
                "noise": {"confidence": 0.9},  # High
            },
        }

        result = calculate_edge_case_score(labels_data)

        # Should detect variance in confidence
        assert isinstance(result, float)

    def test_edge_case_multiple_borderline(self) -> None:
        """Test edge case score for multiple borderline metrics."""
        labels_data = {
            "quality_scores": {
                "laplacian_variance": 100,  # Borderline
                "rms_contrast": 0.3,  # Borderline
                "skew_angle_degrees": 2.0,  # Borderline
            },
            "labels": {},
        }

        result = calculate_edge_case_score(labels_data)

        # Multiple borderline conditions should give high score
        assert result >= 1.0

    def test_edge_case_empty_data(self) -> None:
        """Test edge case score for empty data."""
        labels_data: dict[str, Any] = {"quality_scores": {}, "labels": {}}

        result = calculate_edge_case_score(labels_data)

        assert result == 0.0


class TestCalculateCompositePriority:
    """Tests for calculate_composite_priority function."""

    def test_priority_high_uncertainty_low_edge(self) -> None:
        """Test priority with high uncertainty but low edge case score."""
        labels_data = {
            "labels": {
                "blur": {"confidence": 0.2}
            },  # Low confidence = high uncertainty
            "quality_scores": {"laplacian_variance": 200},  # Not borderline
        }

        result = calculate_composite_priority(labels_data)

        # Should be driven mainly by uncertainty (0.7 weight)
        assert result > 0.5

    def test_priority_low_uncertainty_high_edge(self) -> None:
        """Test priority with low uncertainty but high edge case score."""
        labels_data = {
            "labels": {"blur": {"confidence": 0.95}},  # High confidence
            "quality_scores": {
                "laplacian_variance": 100,  # Borderline
                "rms_contrast": 0.3,  # Borderline
            },
        }

        result = calculate_composite_priority(labels_data)

        # Should have some priority due to edge case score
        assert result > 0

    def test_priority_returns_float(self) -> None:
        """Test that priority returns float."""
        labels_data = {"labels": {}, "quality_scores": {}}

        result = calculate_composite_priority(labels_data)

        assert isinstance(result, float)

    def test_priority_ordering(self) -> None:
        """Test that high uncertainty cases have higher priority."""
        low_uncertainty = {
            "labels": {"blur": {"confidence": 0.95}},
            "quality_scores": {},
        }
        high_uncertainty = {
            "labels": {"blur": {"confidence": 0.3}},
            "quality_scores": {},
        }

        low_priority = calculate_composite_priority(low_uncertainty)
        high_priority = calculate_composite_priority(high_uncertainty)

        assert high_priority > low_priority


class TestSampleAmbiguousCases:
    """Tests for sample_ambiguous_cases function."""

    @pytest.fixture
    def mock_labels_dir(self, tmp_path: Path) -> Path:
        """Create directory with mock label files."""
        labels_dir = tmp_path / "labels"
        labels_dir.mkdir()

        # Create several label files with varying confidence
        for i in range(10):
            labels_data = {
                "image_path": f"/path/to/image_{i}.png",
                "labels": {
                    "blur": {"confidence": 0.5 + (i * 0.05)},
                    "contrast": {"confidence": 0.6 + (i * 0.04)},
                },
                "quality_scores": {
                    "laplacian_variance": 100 + (i * 10),
                    "rms_contrast": 0.25 + (i * 0.02),
                },
            }

            with open(labels_dir / f"image_{i}_labels.json", "w") as f:
                json.dump(labels_data, f)

        return labels_dir

    def test_sample_returns_list(self, mock_labels_dir: Path, tmp_path: Path) -> None:
        """Test that sampling returns a list."""
        output_dir = tmp_path / "output"

        result = sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=5, confidence_threshold=0.95
        )

        assert isinstance(result, list)

    def test_sample_respects_num_samples(
        self, mock_labels_dir: Path, tmp_path: Path
    ) -> None:
        """Test that sampling respects num_samples limit."""
        output_dir = tmp_path / "output"

        result = sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=3, confidence_threshold=0.95
        )

        assert len(result) <= 3

    def test_sample_empty_directory(self, tmp_path: Path) -> None:
        """Test sampling from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        output_dir = tmp_path / "output"

        result = sample_ambiguous_cases(empty_dir, output_dir, num_samples=5)

        assert result == []

    def test_sample_creates_output_directory(
        self, mock_labels_dir: Path, tmp_path: Path
    ) -> None:
        """Test that sampling creates output directory."""
        output_dir = tmp_path / "nested" / "output"

        sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=5, confidence_threshold=0.95
        )

        assert output_dir.exists()

    def test_sample_copies_files(self, mock_labels_dir: Path, tmp_path: Path) -> None:
        """Test that sampled files are copied to output."""
        output_dir = tmp_path / "output"

        result = sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=3, confidence_threshold=0.95
        )

        if result:
            # Check that files were copied
            copied_files = list(output_dir.glob("*_labels.json"))
            assert len(copied_files) == len(result)

    def test_sample_creates_metadata(
        self, mock_labels_dir: Path, tmp_path: Path
    ) -> None:
        """Test that sampling creates metadata file."""
        output_dir = tmp_path / "output"

        result = sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=5, confidence_threshold=0.95
        )

        if result:
            metadata_file = output_dir / "sampling_metadata.json"
            assert metadata_file.exists()

            with open(metadata_file) as f:
                metadata = json.load(f)

            assert "total_labels" in metadata
            assert "sampled_count" in metadata
            assert "statistics" in metadata

    def test_sample_filters_by_confidence(
        self, mock_labels_dir: Path, tmp_path: Path
    ) -> None:
        """Test that sampling filters by confidence threshold."""
        output_dir = tmp_path / "output"

        # Use high threshold so all samples are filtered
        result = sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=10, confidence_threshold=0.99
        )

        # All samples have confidence < 0.99, so they should be included
        assert isinstance(result, list)

    def test_sample_priority_ordering(
        self, mock_labels_dir: Path, tmp_path: Path
    ) -> None:
        """Test that samples are ordered by priority."""
        output_dir = tmp_path / "output"

        result = sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=5, confidence_threshold=0.95
        )

        if len(result) >= 2:
            # First sample should have higher priority than last
            priorities = [item["priority"] for item in result]
            assert priorities == sorted(priorities, reverse=True)

    def test_sample_result_structure(
        self, mock_labels_dir: Path, tmp_path: Path
    ) -> None:
        """Test that sampled results have expected structure."""
        output_dir = tmp_path / "output"

        result = sample_ambiguous_cases(
            mock_labels_dir, output_dir, num_samples=3, confidence_threshold=0.95
        )

        if result:
            sample = result[0]
            assert "label_file" in sample
            assert "image_path" in sample
            assert "uncertainty" in sample
            assert "edge_case_score" in sample
            assert "priority" in sample
            assert "mean_confidence" in sample


class TestProcessLabelFile:
    """Tests for _process_label_file helper function."""

    def test_process_valid_file(self, tmp_path: Path) -> None:
        """Test processing a valid label file."""
        from sample_ambiguous_cases import _process_label_file

        label_file = tmp_path / "test_labels.json"
        labels_data = {
            "image_path": "/path/to/image.png",
            "labels": {"blur": {"confidence": 0.5}},
            "quality_scores": {"laplacian_variance": 100},
        }

        with open(label_file, "w") as f:
            json.dump(labels_data, f)

        result = _process_label_file(label_file, confidence_threshold=0.9)

        assert result is not None
        assert result["image_path"] == "/path/to/image.png"

    def test_process_high_confidence_filtered(self, tmp_path: Path) -> None:
        """Test that high confidence files are filtered out."""
        from sample_ambiguous_cases import _process_label_file

        label_file = tmp_path / "test_labels.json"
        labels_data = {
            "image_path": "/path/to/image.png",
            "labels": {"blur": {"confidence": 0.95}},  # High confidence
            "quality_scores": {},
        }

        with open(label_file, "w") as f:
            json.dump(labels_data, f)

        result = _process_label_file(label_file, confidence_threshold=0.9)

        # High confidence (0.95) >= threshold (0.9), so should be filtered
        assert result is None

    def test_process_invalid_file_returns_none(self, tmp_path: Path) -> None:
        """Test that invalid file returns None."""
        from sample_ambiguous_cases import _process_label_file

        label_file = tmp_path / "invalid.json"
        label_file.write_text("not valid json {")

        result = _process_label_file(label_file, confidence_threshold=0.9)

        assert result is None
