# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for MUSIQ dataset module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

# Check if albumentations is available
try:
    import albumentations as alb  # noqa: F401

    HAS_ALBUMENTATIONS = True
except ImportError:
    HAS_ALBUMENTATIONS = False

from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
    collate_diqa_batch,
)

# Conditionally import transform functions
if HAS_ALBUMENTATIONS:
    from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
        get_phase1_transforms,
        get_phase2_transforms,
        get_validation_transforms,
    )


requires_albumentations = pytest.mark.skipif(
    not HAS_ALBUMENTATIONS,
    reason="albumentations not installed",
)


@requires_albumentations
class TestGetPhase1Transforms:
    """Test Phase 1 transforms."""

    def test_returns_compose(self) -> None:
        """Test returns an Albumentations Compose."""
        # Import fresh to avoid any module caching issues
        import albumentations as albumentations_fresh

        transforms = get_phase1_transforms()
        assert isinstance(transforms, albumentations_fresh.Compose)

    def test_applies_normalization(self) -> None:
        """Test normalization is applied."""
        transforms = get_phase1_transforms()

        # Create test image [H, W, C] in uint8
        rng = np.random.default_rng(42)
        image = rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
        result = transforms(image=image)

        # Should be a tensor after ToTensorV2
        assert isinstance(result["image"], torch.Tensor)
        # Shape should be [C, H, W]
        assert result["image"].shape == (3, 224, 224)

    def test_minimal_augmentation(self) -> None:
        """Test Phase 1 has no geometric augmentation."""
        transforms = get_phase1_transforms()

        # Check there's no flip/rotate transforms
        transform_names = [t.__class__.__name__ for t in transforms.transforms]
        assert "HorizontalFlip" not in transform_names
        assert "Rotate" not in transform_names


@requires_albumentations
class TestGetPhase2Transforms:
    """Test Phase 2 transforms."""

    def test_returns_compose(self) -> None:
        """Test returns an Albumentations Compose."""
        import albumentations as albumentations_fresh

        transforms = get_phase2_transforms()
        assert isinstance(transforms, albumentations_fresh.Compose)

    def test_includes_augmentation(self) -> None:
        """Test Phase 2 has augmentation transforms."""
        transforms = get_phase2_transforms()

        transform_names = [t.__class__.__name__ for t in transforms.transforms]
        assert "HorizontalFlip" in transform_names

    def test_output_shape(self) -> None:
        """Test output shape is correct."""
        # Use default target_size=224 matching the function default
        transforms = get_phase2_transforms()

        rng = np.random.default_rng(42)
        image = rng.integers(0, 255, (384, 384, 3), dtype=np.uint8)
        result = transforms(image=image)

        # Default target size is 224
        assert result["image"].shape == (3, 224, 224)


@requires_albumentations
class TestGetValidationTransforms:
    """Test validation transforms."""

    def test_returns_compose(self) -> None:
        """Test returns an Albumentations Compose."""
        import albumentations as albumentations_fresh

        transforms = get_validation_transforms()
        assert isinstance(transforms, albumentations_fresh.Compose)

    def test_no_augmentation(self) -> None:
        """Test validation has no augmentation."""
        transforms = get_validation_transforms()

        transform_names = [t.__class__.__name__ for t in transforms.transforms]
        assert "HorizontalFlip" not in transform_names
        assert "Rotate" not in transform_names
        assert "ColorJitter" not in transform_names

    def test_deterministic(self) -> None:
        """Test validation transforms are deterministic."""
        transforms = get_validation_transforms()

        rng = np.random.default_rng(42)
        image = rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
        result1 = transforms(image=image)
        result2 = transforms(image=image)

        torch.testing.assert_close(result1["image"], result2["image"])


class TestCollateDIQABatch:
    """Test custom collate function."""

    def test_collates_images(self) -> None:
        """Test images are properly stacked."""
        batch = [
            (
                torch.randn(3, 224, 224),
                {
                    "overall": torch.tensor(0.5),
                    "sharpness": torch.tensor(0.6),
                    "color": torch.tensor(0.7),
                },
            ),
            (
                torch.randn(3, 224, 224),
                {
                    "overall": torch.tensor(0.7),
                    "sharpness": torch.tensor(0.8),
                    "color": torch.tensor(0.9),
                },
            ),
        ]

        images, _ = collate_diqa_batch(batch)

        assert images.shape == (2, 3, 224, 224)

    def test_collates_labels(self) -> None:
        """Test labels are properly stacked."""
        batch = [
            (
                torch.randn(3, 224, 224),
                {
                    "overall": torch.tensor(0.5),
                    "sharpness": torch.tensor(0.6),
                    "color": torch.tensor(0.7),
                },
            ),
            (
                torch.randn(3, 224, 224),
                {
                    "overall": torch.tensor(0.8),
                    "sharpness": torch.tensor(0.9),
                    "color": torch.tensor(0.4),
                },
            ),
        ]

        _, labels = collate_diqa_batch(batch)

        assert labels["overall"].shape == (2,)
        assert labels["sharpness"].shape == (2,)
        assert labels["color"].shape == (2,)

    def test_preserves_label_values(self) -> None:
        """Test label values are preserved."""
        batch = [
            (
                torch.randn(3, 224, 224),
                {
                    "overall": torch.tensor(0.123),
                    "sharpness": torch.tensor(0.456),
                    "color": torch.tensor(0.789),
                },
            ),
        ]

        _, labels = collate_diqa_batch(batch)

        assert labels["overall"][0].item() == pytest.approx(0.123)
        assert labels["sharpness"][0].item() == pytest.approx(0.456)
        assert labels["color"][0].item() == pytest.approx(0.789)


@requires_albumentations
class TestDIQA5000TrainingDataset:
    """Test DIQA5000TrainingDataset class."""

    @pytest.fixture
    def mock_base_dataset(self) -> MagicMock:
        """Create mock base dataset."""
        mock = MagicMock()
        mock.__len__ = MagicMock(return_value=10)

        # Create mock sample
        mock_sample = MagicMock()
        rng = np.random.default_rng(42)
        mock_sample.image = rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)
        mock_sample.ground_truth = {
            "overall": 0.8,
            "sharpness": 0.7,
            "color": 0.9,
        }
        mock.__getitem__ = MagicMock(return_value=mock_sample)

        return mock

    def test_len(self, mock_base_dataset: MagicMock) -> None:
        """Test dataset length."""
        with patch(
            "image_preprocessing_detector.labeling.arena.datasets.base.DIQA5000Dataset",
            return_value=mock_base_dataset,
        ):
            from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
                DIQA5000TrainingDataset,
            )

            dataset = DIQA5000TrainingDataset(
                root_dir="/fake/path",
                split="train",
            )

            assert len(dataset) == 10

    def test_getitem_returns_tuple(self, mock_base_dataset: MagicMock) -> None:
        """Test __getitem__ returns (image, labels) tuple."""
        with patch(
            "image_preprocessing_detector.labeling.arena.datasets.base.DIQA5000Dataset",
            return_value=mock_base_dataset,
        ):
            from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
                DIQA5000TrainingDataset,
            )

            dataset = DIQA5000TrainingDataset(
                root_dir="/fake/path",
                split="train",
            )

            image, labels = dataset[0]

            assert isinstance(image, torch.Tensor)
            assert isinstance(labels, dict)
            assert "overall" in labels
            assert "sharpness" in labels
            assert "color" in labels

    def test_with_transforms(self, mock_base_dataset: MagicMock) -> None:
        """Test dataset with transforms applied."""
        with patch(
            "image_preprocessing_detector.labeling.arena.datasets.base.DIQA5000Dataset",
            return_value=mock_base_dataset,
        ):
            from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
                DIQA5000TrainingDataset,
            )

            transforms = get_phase1_transforms()
            dataset = DIQA5000TrainingDataset(
                root_dir="/fake/path",
                split="train",
                transform=transforms,
            )

            image, _ = dataset[0]

            # With transforms, image should be [C, H, W]
            assert image.dim() == 3
            assert image.shape[0] == 3

    def test_labels_are_tensors(self, mock_base_dataset: MagicMock) -> None:
        """Test labels are converted to tensors."""
        with patch(
            "image_preprocessing_detector.labeling.arena.datasets.base.DIQA5000Dataset",
            return_value=mock_base_dataset,
        ):
            from image_preprocessing_detector.labeling.finetuning.musiq_dataset import (
                DIQA5000TrainingDataset,
            )

            dataset = DIQA5000TrainingDataset(
                root_dir="/fake/path",
                split="train",
            )

            _, labels = dataset[0]

            assert isinstance(labels["overall"], torch.Tensor)
            assert isinstance(labels["sharpness"], torch.Tensor)
            assert isinstance(labels["color"], torch.Tensor)
            assert labels["overall"].dtype == torch.float32
