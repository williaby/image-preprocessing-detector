# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for Phase 7 continuous label data modules.

Tests:
- DocCreator XML loader
- Augraphy continuous pipeline
- ContinuousQualityLabel schema
- ContinuousIQADataset
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_doccreator_xml() -> str:
    """Sample DocCreator XML ground truth."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<document>
  <degradation type="adaptive_blur" severity="0.45" method="spatial_varying">
    <params>
      <kernel_size>7</kernel_size>
      <sigma>2.1</sigma>
    </params>
  </degradation>
  <degradation type="paper_noise" severity="0.30" method="gaussian">
    <params>
      <intensity>0.30</intensity>
      <distribution>gaussian</distribution>
    </params>
  </degradation>
  <degradation type="ink_bleeding" severity="0.25" method="diffusion">
    <params>
      <spread>3</spread>
    </params>
  </degradation>
</document>"""


@pytest.fixture
def sample_continuous_label() -> dict[str, Any]:
    """Sample continuous label in Phase 7 format."""
    return {
        "blur_severity": 0.35,
        "noise_severity": 0.20,
        "skew_severity": 0.10,
        "contrast_severity": 0.15,
        "compression_severity": 0.25,
        "ink_degradation": 0.05,
        "paper_degradation": 0.10,
        "bleed_through": 0.00,
        "overall_quality": 0.65,
        "label_source": "augraphy",
        "label_confidence": 1.0,
        "label_variance": 0.0,
    }


@pytest.fixture
def sample_weak_supervision_label() -> dict[str, Any]:
    """Sample weak supervision label (binary with severity metadata)."""
    return {
        "image_path": "test_image.png",
        "labels": {
            "blur": {
                "value": 1,
                "confidence": 0.85,
                "source": "laplacian",
                "severity": 0.45,
            },
            "noise": {
                "value": 0,
                "confidence": 0.90,
                "source": "brisque",
                "severity": 0.15,
            },
            "skew": {
                "value": 0,
                "confidence": 0.88,
                "source": "hough_transform",
                "severity": 0.05,
            },
            "illumination": {
                "value": 1,
                "confidence": 0.75,
                "source": "rms_contrast",
                "severity": 0.40,
            },
            "artifacts": {
                "value": 0,
                "confidence": 0.85,
                "source": "blockiness",
                "severity": 0.10,
            },
        },
        "quality_scores": {
            "laplacian_variance": 85.5,
            "brisque": 35.2,
            "rms_contrast": 0.28,
            "blockiness": 2.1,
        },
    }


@pytest.fixture
def temp_xml_file(sample_doccreator_xml: str) -> Path:
    """Create a temporary XML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix="_gt.xml", delete=False) as f:
        f.write(sample_doccreator_xml)
        return Path(f.name)


# ============================================================================
# DocCreator Loader Tests
# ============================================================================


class TestDocCreatorLoader:
    """Tests for DocCreator XML loader."""

    def test_parse_xml_basic(self, temp_xml_file: Path):
        """Test basic XML parsing."""
        from data.doccreator_loader import parse_doccreator_xml

        label = parse_doccreator_xml(temp_xml_file)

        assert label.blur_severity == pytest.approx(0.45)
        assert label.noise_severity == pytest.approx(0.30)
        assert label.ink_degradation == pytest.approx(0.25)
        # Overall quality should be 1 - max(severities)
        assert label.overall_quality == pytest.approx(0.55, rel=0.01)

    def test_to_dict_format(self, temp_xml_file: Path):
        """Test conversion to dictionary format."""
        from data.doccreator_loader import parse_doccreator_xml

        label = parse_doccreator_xml(temp_xml_file)
        result = label.to_dict()

        # Check continuous values
        assert "blur_severity" in result
        assert "noise_severity" in result
        assert "overall_quality" in result

        # Check backward-compatible fields
        assert "quality_scores" in result
        assert "labels" in result
        assert result["label_source"] == "doccreator"
        assert result["label_confidence"] == pytest.approx(1.0)

    def test_binary_labels_threshold(self, temp_xml_file: Path):
        """Test binary label conversion with threshold."""
        from data.doccreator_loader import parse_doccreator_xml

        label = parse_doccreator_xml(temp_xml_file)
        result = label.to_dict()

        # Blur = 0.45 > 0.3 threshold -> binary = 1
        assert result["labels"]["blur"]["value"] == 1
        # Noise = 0.30 >= 0.3 threshold -> binary = 1
        assert result["labels"]["noise"]["value"] == 1

    def test_missing_xml_raises_error(self):
        """Test that missing XML raises FileNotFoundError."""
        from data.doccreator_loader import parse_doccreator_xml

        with pytest.raises(FileNotFoundError):
            parse_doccreator_xml("/nonexistent/path.xml")

    def test_degradation_type_mapping(self):
        """Test that degradation types are correctly mapped."""
        from data.doccreator_loader import DEGRADATION_TYPE_MAPPING

        assert DEGRADATION_TYPE_MAPPING["adaptive_blur"] == "blur"
        assert DEGRADATION_TYPE_MAPPING["paper_noise"] == "noise"
        assert DEGRADATION_TYPE_MAPPING["ink_bleeding"] == "ink"


# ============================================================================
# Continuous Labels Schema Tests
# ============================================================================


class TestContinuousQualityLabel:
    """Tests for ContinuousQualityLabel Pydantic model."""

    def test_default_values(self):
        """Test default initialization."""
        from data.continuous_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel()

        assert label.blur_severity == pytest.approx(0.0)
        assert label.noise_severity == pytest.approx(0.0)
        assert label.overall_quality == pytest.approx(1.0)
        assert label.label_source == "augraphy"

    def test_severity_validation(self):
        """Test that severity values are validated to [0, 1]."""
        from pydantic import ValidationError

        from data.continuous_labels import ContinuousQualityLabel

        # Values > 1.0 should fail
        with pytest.raises(ValidationError):
            ContinuousQualityLabel(blur_severity=1.5)

        # Values < 0.0 should fail
        with pytest.raises(ValidationError):
            ContinuousQualityLabel(blur_severity=-0.1)

    def test_binary_conversion(self, sample_continuous_label: dict[str, Any]):
        """Test conversion to binary labels."""
        from data.continuous_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel(**sample_continuous_label)
        binary = label.get_binary_labels(threshold=0.3)

        # blur = 0.35 >= 0.3 -> 1
        assert binary["blur"] == 1
        # noise = 0.20 < 0.3 -> 0
        assert binary["noise"] == 0
        # skew = 0.10 < 0.3 -> 0
        assert binary["skew"] == 0

    def test_severity_vector(self, sample_continuous_label: dict[str, Any]):
        """Test severity vector extraction."""
        from data.continuous_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel(**sample_continuous_label)
        vector = label.get_severity_vector()

        assert len(vector) == 5
        assert vector[0] == pytest.approx(0.35)  # blur
        assert vector[1] == pytest.approx(0.20)  # noise
        assert vector[2] == pytest.approx(0.10)  # skew

    def test_training_dict_format(self, sample_continuous_label: dict[str, Any]):
        """Test training dictionary format."""
        from data.continuous_labels import ContinuousQualityLabel

        label = ContinuousQualityLabel(**sample_continuous_label)
        result = label.to_training_dict()

        # Check all required fields
        assert "continuous_labels" in result
        assert "quality_scores" in result
        assert "labels" in result
        assert "label_source" in result

        # Check continuous_labels structure
        assert result["continuous_labels"]["blur_severity"] == pytest.approx(0.35)


class TestLabelConversions:
    """Tests for label conversion functions."""

    def test_binary_to_continuous(self):
        """Test converting binary labels to continuous."""
        from data.continuous_labels import binary_to_continuous

        binary = {
            "blur": 1,
            "noise": 0,
            "skew": 1,
            "illumination": 0,
            "artifacts": 1,
        }

        label = binary_to_continuous(binary, confidence=0.7)

        assert label.blur_severity == pytest.approx(0.7)
        assert label.noise_severity == pytest.approx(0.0)
        assert label.skew_severity == pytest.approx(0.7)
        assert label.label_source == "weak_supervision"

    def test_aggregate_labels_mean(self):
        """Test label aggregation with mean method."""
        from data.continuous_labels import ContinuousQualityLabel, aggregate_labels

        labels = [
            ContinuousQualityLabel(blur_severity=0.2, noise_severity=0.3),
            ContinuousQualityLabel(blur_severity=0.4, noise_severity=0.5),
            ContinuousQualityLabel(blur_severity=0.6, noise_severity=0.7),
        ]

        result = aggregate_labels(labels, method="mean")

        assert result.blur_severity == pytest.approx(0.4, rel=0.01)
        assert result.noise_severity == pytest.approx(0.5, rel=0.01)

    def test_aggregate_labels_max(self):
        """Test label aggregation with max method (conservative)."""
        from data.continuous_labels import ContinuousQualityLabel, aggregate_labels

        labels = [
            ContinuousQualityLabel(blur_severity=0.2),
            ContinuousQualityLabel(blur_severity=0.8),
        ]

        result = aggregate_labels(labels, method="max")

        assert result.blur_severity == pytest.approx(0.8)

    def test_load_label_file_continuous(self, sample_continuous_label: dict[str, Any]):
        """Test loading continuous label file."""
        from data.continuous_labels import load_label_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_continuous_label, f)
            temp_path = Path(f.name)

        label = load_label_file(temp_path)

        assert label.blur_severity == pytest.approx(0.35)
        assert label.label_source == "augraphy"

    def test_load_label_file_weak_supervision(
        self, sample_weak_supervision_label: dict[str, Any]
    ):
        """Test loading weak supervision format label file."""
        from data.continuous_labels import load_label_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_weak_supervision_label, f)
            temp_path = Path(f.name)

        label = load_label_file(temp_path)

        # Should extract severity from nested labels
        assert label.blur_severity == pytest.approx(0.45)
        assert label.contrast_severity == pytest.approx(0.40)
        assert label.label_source == "weak_supervision"


# ============================================================================
# Dataset Tests
# ============================================================================


class TestContinuousIQADataset:
    """Tests for ContinuousIQADataset."""

    @pytest.fixture
    def temp_dataset_dir(self, sample_continuous_label: dict[str, Any]) -> Path:
        """Create a temporary dataset directory with split files."""
        import cv2

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create images directory
            images_dir = tmpdir / "images"
            images_dir.mkdir()

            # Create labels directory
            labels_dir = tmpdir / "labels"
            labels_dir.mkdir()

            # Create sample images and labels
            samples = []
            for i in range(5):
                # Create dummy image
                image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
                image_path = images_dir / f"image_{i:03d}.png"
                cv2.imwrite(str(image_path), image)

                # Create label with varying severities
                label = sample_continuous_label.copy()
                label["blur_severity"] = 0.1 * i
                label["noise_severity"] = 0.15 * i

                label_path = labels_dir / f"image_{i:03d}_labels.json"
                with open(label_path, "w") as f:
                    json.dump(label, f)

                samples.append(
                    {
                        "image_path": str(image_path),
                        "label_path": str(label_path),
                    }
                )

            # Create split files
            for split_name, indices in [
                ("train", [0, 1, 2]),
                ("val", [3]),
                ("test", [4]),
            ]:
                split_file = tmpdir / f"{split_name}_split.json"
                with open(split_file, "w") as f:
                    json.dump(
                        {
                            "samples": [samples[i] for i in indices],
                            "split": split_name,
                        },
                        f,
                    )

            yield tmpdir

    def test_dataset_loading(self, temp_dataset_dir: Path):
        """Test basic dataset loading."""
        from data.dataset import ContinuousIQADataset

        dataset = ContinuousIQADataset(temp_dataset_dir, split="train")

        assert len(dataset) == 3

    def test_dataset_getitem(self, temp_dataset_dir: Path):
        """Test getting items from dataset."""
        from data.dataset import ContinuousIQADataset

        dataset = ContinuousIQADataset(temp_dataset_dir, split="train")
        image, labels = dataset[0]

        # Check image shape
        assert image.shape == (3, 224, 224)
        # Check labels shape (5 continuous dimensions)
        assert labels.shape == (5,)
        # Labels should be continuous values
        assert labels.dtype == np.float32

    def test_dataset_with_variance(self, temp_dataset_dir: Path):
        """Test dataset with variance return."""
        from data.dataset import ContinuousIQADataset

        dataset = ContinuousIQADataset(
            temp_dataset_dir,
            split="train",
            return_variance=True,
        )
        image, labels, variances = dataset[0]

        assert variances.shape == (5,)

    def test_dataset_binary_mode(self, temp_dataset_dir: Path):
        """Test dataset in binary label mode."""
        from data.dataset import ContinuousIQADataset

        dataset = ContinuousIQADataset(
            temp_dataset_dir,
            split="train",
            label_type="binary",
        )
        image, labels = dataset[0]

        # Labels should be 0 or 1
        assert all(l in [0.0, 1.0] for l in labels.tolist())

    def test_dataset_statistics(self, temp_dataset_dir: Path):
        """Test label statistics calculation."""
        from data.dataset import ContinuousIQADataset

        dataset = ContinuousIQADataset(temp_dataset_dir, split="train")
        stats = dataset.get_label_statistics()

        assert stats["total_samples"] == 3
        assert "blur_severity" in stats
        assert "mean" in stats["blur_severity"]
        assert "std" in stats["blur_severity"]


# ============================================================================
# Augraphy Pipeline Tests (requires augraphy)
# ============================================================================


@pytest.mark.skipif(
    not pytest.importorskip("augraphy", reason="augraphy not installed"),
    reason="augraphy not installed",
)
class TestAugraphyPipeline:
    """Tests for Augraphy continuous pipeline."""

    def test_pipeline_creation(self):
        """Test pipeline creation with presets."""
        from data.augraphy_pipeline import create_augraphy_pipeline

        pipeline = create_augraphy_pipeline("medium")
        assert pipeline is not None
        assert pipeline.severity_preset == "medium"

    def test_augment_returns_labels(self):
        """Test that augmentation returns labels."""
        from data.augraphy_pipeline import AugraphyContinuousLabeler

        pipeline = AugraphyContinuousLabeler(severity_preset="light")

        # Create dummy image
        image = np.random.randint(0, 255, (400, 300, 3), dtype=np.uint8)

        augmented, labels = pipeline.augment(image)

        # Check output
        assert augmented.shape == image.shape
        assert labels.overall_quality >= 0.0
        assert labels.overall_quality <= 1.0

    def test_label_to_dict(self):
        """Test AugraphyLabel to_dict conversion."""
        from data.augraphy_pipeline import AugraphyLabel

        label = AugraphyLabel(
            blur_severity=0.3,
            noise_severity=0.2,
            overall_quality=0.7,
        )

        result = label.to_dict()

        assert result["blur_severity"] == pytest.approx(0.3)
        assert result["label_source"] == "augraphy"
        assert "labels" in result  # Backward-compatible binary labels
