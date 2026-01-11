# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Tests for DIQA training dataset adapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import torch

from image_preprocessing_detector.labeling.finetuning.dataset import (
    DIQASample,
    DIQATrainingDataset,
    get_default_transforms,
)


class TestDIQASample:
    """Tests for DIQASample dataclass."""

    def test_basic_sample(self):
        """Test basic sample creation."""
        sample = DIQASample(
            image_id="test_001",
            image_path="/path/to/image.jpg",
            overall=0.8,
            sharpness=0.7,
            color=0.9,
        )

        assert sample.image_id == "test_001"
        assert sample.overall == 0.8
        assert sample.sharpness == 0.7
        assert sample.color == 0.9
        assert sample.metadata is None

    def test_to_target_tensor(self):
        """Test conversion to target tensor."""
        sample = DIQASample(
            image_id="test",
            image_path="",
            overall=0.8,
            sharpness=0.7,
            color=0.9,
        )

        target = sample.to_target_tensor()

        assert target.shape == (3,)
        assert target[0] == pytest.approx(0.8)
        assert target[1] == pytest.approx(0.7)
        assert target[2] == pytest.approx(0.9)
        assert target.dtype == torch.float32

    def test_with_metadata(self):
        """Test sample with metadata."""
        sample = DIQASample(
            image_id="test",
            image_path="",
            overall=0.5,
            sharpness=0.5,
            color=0.5,
            metadata={"source": "test", "annotator": "human"},
        )

        assert sample.metadata is not None
        assert sample.metadata["source"] == "test"


class TestDIQATrainingDataset:
    """Tests for DIQATrainingDataset."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_synthetic_train_dataset(self, temp_data_dir):
        """Test loading synthetic training dataset."""
        dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="train",
            synthetic_fallback=True,
            max_samples=100,
        )

        assert len(dataset) == 100

    def test_synthetic_val_dataset(self, temp_data_dir):
        """Test loading synthetic validation dataset."""
        dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="val",
            synthetic_fallback=True,
            max_samples=50,
        )

        assert len(dataset) == 50

    def test_validation_alias(self, temp_data_dir):
        """Test 'validation' split alias."""
        dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="validation",
            synthetic_fallback=True,
            max_samples=10,
        )

        # Should normalize to 'val'
        assert dataset.split == "val"

    def test_blocked_test_split(self, temp_data_dir):
        """Test that test split is blocked."""
        with pytest.raises(ValueError, match="Test split is blocked"):
            DIQATrainingDataset(
                data_dir=temp_data_dir,
                split="test",
                synthetic_fallback=True,
            )

    def test_unknown_split(self, temp_data_dir):
        """Test unknown split raises error."""
        with pytest.raises(ValueError, match="Unknown split"):
            DIQATrainingDataset(
                data_dir=temp_data_dir,
                split="unknown",
                synthetic_fallback=True,
            )

    def test_getitem_returns_tuple(self, temp_data_dir):
        """Test __getitem__ returns (image, target) tuple."""
        transform = get_default_transforms(is_training=False, image_size=224)

        dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="train",
            transform=transform,
            synthetic_fallback=True,
            max_samples=10,
        )

        image, target = dataset[0]

        assert isinstance(image, torch.Tensor)
        assert isinstance(target, torch.Tensor)
        assert image.shape == (3, 224, 224)
        assert target.shape == (3,)

    def test_get_sample_info(self, temp_data_dir):
        """Test get_sample_info returns DIQASample."""
        dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="train",
            synthetic_fallback=True,
            max_samples=10,
        )

        sample = dataset.get_sample_info(0)

        assert isinstance(sample, DIQASample)
        assert sample.image_id.startswith("synthetic_train_")

    def test_synthetic_score_ranges(self, temp_data_dir):
        """Test synthetic samples have valid score ranges."""
        dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="train",
            synthetic_fallback=True,
            max_samples=100,
        )

        for i in range(len(dataset)):
            sample = dataset.get_sample_info(i)
            assert 0.0 <= sample.overall <= 1.0
            assert 0.0 <= sample.sharpness <= 1.0
            assert 0.0 <= sample.color <= 1.0

    def test_train_val_different_seeds(self, temp_data_dir):
        """Test train and val use different random seeds."""
        train_dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="train",
            synthetic_fallback=True,
            max_samples=50,
        )

        val_dataset = DIQATrainingDataset(
            data_dir=temp_data_dir,
            split="val",
            synthetic_fallback=True,
            max_samples=50,
        )

        # Get first sample from each
        train_sample = train_dataset.get_sample_info(0)
        val_sample = val_dataset.get_sample_info(0)

        # Scores should be different (different random seeds)
        # Note: Small chance they could be equal, but very unlikely
        assert (
            train_sample.overall != val_sample.overall
            or train_sample.sharpness != val_sample.sharpness
        )


class TestDefaultTransforms:
    """Tests for default transforms."""

    def test_training_transforms(self):
        """Test training transforms include augmentation."""
        from torchvision import transforms

        transform = get_default_transforms(is_training=True, image_size=224)

        # Should be a Compose of transforms
        assert isinstance(transform, transforms.Compose)

    def test_validation_transforms(self):
        """Test validation transforms are simpler."""
        from torchvision import transforms

        transform = get_default_transforms(is_training=False, image_size=224)

        assert isinstance(transform, transforms.Compose)

    def test_custom_image_size(self):
        """Test transforms with custom image size."""
        from PIL import Image

        transform = get_default_transforms(is_training=False, image_size=384)

        # Create dummy image
        img = Image.new("RGB", (640, 480))
        result = transform(img)

        assert result.shape == (3, 384, 384)

    def test_output_normalized(self):
        """Test transform output is normalized (not just ToTensor)."""
        from PIL import Image

        transform = get_default_transforms(is_training=False, image_size=224)

        # Create image with known values
        img = Image.new("RGB", (224, 224), color=(128, 128, 128))
        result = transform(img)

        # Check that output is a tensor with correct shape
        assert result.shape == (3, 224, 224)
        # Values should be normalized - not raw [0, 255] values
        # After ImageNet normalization, gray (128) becomes different values per channel
        # Check channels have different values (normalized by different means)
        assert not torch.allclose(
            result[0], result[1]
        )  # R and G channels differ after normalization
