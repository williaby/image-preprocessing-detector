# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for Phase 7 pseudo-label generation.

Tests the ContinuousQualityLabel class and JSON parsing logic
from modal/generate_pseudo_labels.py.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Try to import from modal scripts - skip all tests if import fails
# The Modal SDK package shadows our local modal/ directory, so we need to
# actually test if the import works, not just check if the file exists
MODAL_IMPORT_AVAILABLE = False
try:
    from modal.generate_pseudo_labels import ContinuousQualityLabel  # noqa: F401

    MODAL_IMPORT_AVAILABLE = True
except (ImportError, ModuleNotFoundError, AttributeError):
    # Modal SDK is installed and shadows our local modal/ directory
    # or the module doesn't exist
    MODAL_IMPORT_AVAILABLE = False

# Skip marker for tests that require modal imports
requires_modal = pytest.mark.skipif(
    not MODAL_IMPORT_AVAILABLE,
    reason="Modal pseudo-label scripts not importable (Modal SDK shadows local modal/ directory)",
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def valid_json_response() -> dict[str, Any]:
    """Valid JSON response from model."""
    return {
        "blur_severity": 0.25,
        "noise_severity": 0.15,
        "skew_severity": 0.05,
        "contrast_severity": 0.10,
        "compression_severity": 0.20,
        "ink_degradation": 0.00,
        "paper_degradation": 0.05,
        "overall_quality": 0.85,
    }


@pytest.fixture
def json_with_code_block() -> str:
    """JSON response wrapped in code block."""
    return """Here is my assessment:

```json
{
    "blur_severity": 0.30,
    "noise_severity": 0.20,
    "skew_severity": 0.10,
    "contrast_severity": 0.15,
    "compression_severity": 0.25,
    "overall_quality": 0.75
}
```

This document shows moderate blur and compression artifacts."""


@pytest.fixture
def json_without_markers() -> str:
    """JSON response without code block markers."""
    return """{
    "blur_severity": 0.40,
    "noise_severity": 0.35,
    "skew_severity": 0.20,
    "contrast_severity": 0.25,
    "compression_severity": 0.30,
    "overall_quality": 0.65
}"""


@pytest.fixture
def malformed_json_response() -> str:
    """Malformed JSON that should trigger default values."""
    return "This is not valid JSON at all. The image looks blurry."


# ============================================================================
# ContinuousQualityLabel Tests
# ============================================================================


@requires_modal
class TestContinuousQualityLabel:
    """Tests for the ContinuousQualityLabel dataclass."""

    def test_default_values(self):
        """Test default initialization values."""
        # Import here to avoid Modal dependency issues in CI
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel()

        assert label.blur_severity == 0.0
        assert label.noise_severity == 0.0
        assert label.skew_severity == 0.0
        assert label.contrast_severity == 0.0
        assert label.compression_severity == 0.0
        assert label.overall_quality == 1.0
        assert label.label_source == "mllm_pseudo"
        assert label.model_name == "qwen3-vl-8b-instruct"
        assert label.label_confidence == 0.85

    def test_from_model_response_valid(self, valid_json_response):
        """Test creating label from valid model response."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel.from_model_response(
            valid_json_response,
            model_name="test-model",
            raw_response="test response",
        )

        assert label.blur_severity == 0.25
        assert label.noise_severity == 0.15
        assert label.skew_severity == 0.05
        assert label.contrast_severity == 0.10
        assert label.compression_severity == 0.20
        assert label.overall_quality == 0.85
        assert label.model_name == "test-model"
        assert label.raw_response == "test response"

    def test_from_model_response_clamping(self):
        """Test that values are clamped to [0, 1] range."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        response = {
            "blur_severity": 1.5,  # Above 1.0
            "noise_severity": -0.2,  # Below 0.0
            "contrast_severity": 0.5,  # Valid
            "overall_quality": 2.0,  # Above 1.0
        }

        label = ContinuousQualityLabel.from_model_response(response)

        assert label.blur_severity == 1.0  # Clamped to max
        assert label.noise_severity == 0.0  # Clamped to min
        assert label.contrast_severity == 0.5  # Unchanged
        assert label.overall_quality == 1.0  # Clamped to max

    def test_from_model_response_invalid_types(self):
        """Test handling of invalid types in response."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        response = {
            "blur_severity": "not a number",
            "noise_severity": None,
            "contrast_severity": [0.5],  # List instead of float
        }

        label = ContinuousQualityLabel.from_model_response(response)

        # Should use defaults for invalid values
        assert label.blur_severity == 0.0
        assert label.noise_severity == 0.0
        assert label.contrast_severity == 0.0

    def test_to_dict_structure(self, valid_json_response):
        """Test that to_dict produces expected structure."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel.from_model_response(valid_json_response)
        result = label.to_dict()

        # Check continuous values
        assert "blur_severity" in result
        assert "noise_severity" in result
        assert "overall_quality" in result

        # Check backward-compatible quality_scores
        assert "quality_scores" in result
        assert result["quality_scores"]["blur"] == 0.25
        assert result["quality_scores"]["overall"] == 0.85

        # Check backward-compatible binary labels
        assert "labels" in result
        assert "blur" in result["labels"]
        assert result["labels"]["blur"]["value"] in [0, 1]
        assert "severity" in result["labels"]["blur"]

    def test_binary_threshold_conversion(self):
        """Test binary label conversion with threshold."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        # Below threshold (0.3)
        label_low = ContinuousQualityLabel(blur_severity=0.2)
        result_low = label_low.to_dict()
        assert result_low["labels"]["blur"]["value"] == 0

        # At threshold
        label_at = ContinuousQualityLabel(blur_severity=0.3)
        result_at = label_at.to_dict()
        assert result_at["labels"]["blur"]["value"] == 1

        # Above threshold
        label_high = ContinuousQualityLabel(blur_severity=0.7)
        result_high = label_high.to_dict()
        assert result_high["labels"]["blur"]["value"] == 1

    def test_timestamp_generation(self):
        """Test that timestamp is auto-generated."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel()

        # Should be a valid ISO timestamp
        assert label.generation_timestamp is not None
        datetime.fromisoformat(label.generation_timestamp)


# ============================================================================
# JSON Parsing Tests
# ============================================================================


@requires_modal
class TestJsonParsing:
    """Tests for JSON response parsing logic."""

    def test_parse_direct_json(self, json_without_markers):
        """Test parsing direct JSON without code blocks."""
        from modal.generate_pseudo_labels import Qwen3VLLabeler

        # Create mock labeler to access parsing method
        labeler = MagicMock(spec=Qwen3VLLabeler)
        labeler._parse_json_response = Qwen3VLLabeler._parse_json_response

        result = labeler._parse_json_response(labeler, json_without_markers)

        assert result["blur_severity"] == 0.40
        assert result["noise_severity"] == 0.35
        assert result["overall_quality"] == 0.65

    def test_parse_json_with_code_block(self, json_with_code_block):
        """Test parsing JSON wrapped in markdown code block."""
        from modal.generate_pseudo_labels import Qwen3VLLabeler

        labeler = MagicMock(spec=Qwen3VLLabeler)
        labeler._parse_json_response = Qwen3VLLabeler._parse_json_response

        result = labeler._parse_json_response(labeler, json_with_code_block)

        assert result["blur_severity"] == 0.30
        assert result["noise_severity"] == 0.20
        assert result["overall_quality"] == 0.75

    def test_parse_malformed_json_returns_defaults(self, malformed_json_response):
        """Test that malformed JSON returns default values."""
        from modal.generate_pseudo_labels import Qwen3VLLabeler

        labeler = MagicMock(spec=Qwen3VLLabeler)
        labeler._parse_json_response = Qwen3VLLabeler._parse_json_response

        result = labeler._parse_json_response(labeler, malformed_json_response)

        # Should return defaults with parse_error flag
        assert result.get("parse_error", False) is True
        assert result["blur_severity"] == 0.5
        assert result["overall_quality"] == 0.5

    def test_parse_json_with_surrounding_text(self):
        """Test parsing JSON embedded in surrounding text."""
        from modal.generate_pseudo_labels import Qwen3VLLabeler

        response = """Based on my analysis, here are the quality scores:

        {"blur_severity": 0.5, "noise_severity": 0.3, "overall_quality": 0.7}

        The document shows moderate degradation."""

        labeler = MagicMock(spec=Qwen3VLLabeler)
        labeler._parse_json_response = Qwen3VLLabeler._parse_json_response

        result = labeler._parse_json_response(labeler, response)

        assert result["blur_severity"] == 0.5
        assert result["noise_severity"] == 0.3

    def test_parse_nested_json_block(self):
        """Test parsing with nested json code block marker."""
        from modal.generate_pseudo_labels import Qwen3VLLabeler

        response = """```json
{"blur_severity": 0.6, "overall_quality": 0.4}
```"""

        labeler = MagicMock(spec=Qwen3VLLabeler)
        labeler._parse_json_response = Qwen3VLLabeler._parse_json_response

        result = labeler._parse_json_response(labeler, response)

        assert result["blur_severity"] == 0.6
        assert result["overall_quality"] == 0.4


# ============================================================================
# Integration Tests (without Modal)
# ============================================================================


@requires_modal
class TestLabelSerialization:
    """Tests for label serialization and compatibility."""

    def test_json_round_trip(self, valid_json_response):
        """Test that labels survive JSON serialization round-trip."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel.from_model_response(valid_json_response)
        serialized = json.dumps(label.to_dict())
        deserialized = json.loads(serialized)

        # Verify all fields survived
        assert deserialized["blur_severity"] == 0.25
        assert deserialized["overall_quality"] == 0.85
        assert "quality_scores" in deserialized
        assert "labels" in deserialized

    def test_weak_supervision_compatibility(self, valid_json_response):
        """Test compatibility with weak supervision label format."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel.from_model_response(valid_json_response)
        result = label.to_dict()

        # Check compatibility with data/weak_supervision.py format
        labels = result["labels"]

        for issue_name in ["blur", "noise", "skew", "illumination", "artifacts"]:
            assert issue_name in labels
            assert "value" in labels[issue_name]
            assert "confidence" in labels[issue_name]
            assert "source" in labels[issue_name]
            assert isinstance(labels[issue_name]["value"], int)
            assert labels[issue_name]["value"] in [0, 1]

    def test_quality_scores_backward_compatibility(self, valid_json_response):
        """Test backward compatibility with quality_scores format."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel.from_model_response(valid_json_response)
        result = label.to_dict()

        quality_scores = result["quality_scores"]

        # Check expected keys
        expected_keys = {"blur", "noise", "skew", "contrast", "compression", "overall"}
        assert set(quality_scores.keys()) == expected_keys

        # Check values are floats in [0, 1]
        for key, value in quality_scores.items():
            assert isinstance(value, float)
            assert 0.0 <= value <= 1.0


# ============================================================================
# Edge Cases
# ============================================================================


@requires_modal
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_response(self):
        """Test handling of empty response."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel.from_model_response({})

        # Should use all defaults
        assert label.blur_severity == 0.0
        assert label.overall_quality == 1.0

    def test_extra_fields_ignored(self):
        """Test that extra fields in response are ignored."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        response = {
            "blur_severity": 0.5,
            "unknown_field": "should be ignored",
            "another_extra": 123,
        }

        label = ContinuousQualityLabel.from_model_response(response)

        assert label.blur_severity == 0.5
        # Extra fields should not cause errors

    def test_all_maximum_values(self):
        """Test with all maximum severity values."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        response = {
            "blur_severity": 1.0,
            "noise_severity": 1.0,
            "skew_severity": 1.0,
            "contrast_severity": 1.0,
            "compression_severity": 1.0,
            "overall_quality": 0.0,  # Worst quality
        }

        label = ContinuousQualityLabel.from_model_response(response)
        result = label.to_dict()

        # All binary labels should be 1
        for issue_name in ["blur", "noise", "skew", "illumination", "artifacts"]:
            assert result["labels"][issue_name]["value"] == 1

    def test_all_minimum_values(self):
        """Test with all minimum severity values (perfect quality)."""
        from modal.generate_pseudo_labels import ContinuousQualityLabel

        response = {
            "blur_severity": 0.0,
            "noise_severity": 0.0,
            "skew_severity": 0.0,
            "contrast_severity": 0.0,
            "compression_severity": 0.0,
            "overall_quality": 1.0,  # Best quality
        }

        label = ContinuousQualityLabel.from_model_response(response)
        result = label.to_dict()

        # All binary labels should be 0
        for issue_name in ["blur", "noise", "skew", "illumination", "artifacts"]:
            assert result["labels"][issue_name]["value"] == 0


# ============================================================================
# Skip Modal-dependent tests in CI
# ============================================================================


@pytest.mark.skipif(
    "CI" in str(Path.cwd()) or not Path("/usr/bin/nvidia-smi").exists(),
    reason="Skipping Modal tests in CI or without GPU",
)
class TestModalIntegration:
    """Tests that require Modal runtime (skipped in CI)."""

    def test_labeler_initialization(self):
        """Test that Qwen3VLLabeler can be instantiated."""
        from modal.generate_pseudo_labels import Qwen3VLLabeler

        # This would require Modal runtime
        # Just test that the class exists and has expected methods
        assert hasattr(Qwen3VLLabeler, "generate_label")
        assert hasattr(Qwen3VLLabeler, "generate_labels_batch")
        assert hasattr(Qwen3VLLabeler, "load_model")
