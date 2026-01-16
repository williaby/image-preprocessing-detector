# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Additional tests to boost coverage for HyperIQA++ modules."""

from __future__ import annotations

from pathlib import Path

import torch

from image_preprocessing_detector.labeling.hyperiqa_plus_plus.model import (
    HyperIQAPlusPlus,
)
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.pcgrad import PCGrad
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.utils import (
    apply_safe_augmentations,
    create_soft_labels,
)


class TestModelEdgeCases:
    """Test edge cases in model.py for coverage."""

    def test_model_basic_forward(self) -> None:
        """Test basic model forward pass."""
        model = HyperIQAPlusPlus(num_bins=10, use_pretrained=False)
        model.eval()

        x = torch.randn(1, 3, 224, 224)
        with torch.no_grad():
            outputs = model(x)

        assert "overall" in outputs
        assert outputs["overall"]["score"].shape == (1,)

    def test_model_parameter_statistics(self) -> None:
        """Test get_num_parameters with details."""
        model = HyperIQAPlusPlus(use_pretrained=False)

        params = model.get_num_parameters()

        assert "total" in params
        assert "backbone" in params
        assert "hypernet" in params
        assert params["total"] > 0

    def test_model_state_saving(self, tmp_path: Path) -> None:
        """Test model state dict saving."""
        model = HyperIQAPlusPlus(use_pretrained=False)

        checkpoint_path = tmp_path / "model.pt"
        torch.save(model.state_dict(), checkpoint_path)

        assert checkpoint_path.exists()
        assert checkpoint_path.stat().st_size > 0


class TestPCGradCoverage:
    """Test PCGrad for coverage."""

    def test_pcgrad_initialization(self) -> None:
        """Test PCGrad wrapper initialization."""
        base_optimizer = torch.optim.SGD(
            [torch.randn(10, requires_grad=True)],
            lr=0.1,
            momentum=0.9,
            weight_decay=1e-4,
        )
        optimizer = PCGrad(base_optimizer)

        assert optimizer._optimizer is base_optimizer

    def test_pcgrad_zero_grad(self) -> None:
        """Test PCGrad zero_grad pass-through."""
        param = torch.randn(10, requires_grad=True)
        base_optimizer = torch.optim.SGD(
            [param], lr=0.1, momentum=0.9, weight_decay=1e-4
        )
        optimizer = PCGrad(base_optimizer)

        # Create gradient
        loss = param.sum()
        loss.backward()

        assert param.grad is not None

        # Zero out
        optimizer.zero_grad()

        assert param.grad is None or torch.allclose(param.grad, torch.zeros_like(param))

    def test_pcgrad_step(self) -> None:
        """Test PCGrad step pass-through."""
        param = torch.randn(10, requires_grad=True)
        initial_value = param.clone()

        base_optimizer = torch.optim.SGD(
            [param], lr=0.1, momentum=0.9, weight_decay=1e-4
        )
        optimizer = PCGrad(base_optimizer)

        # Create gradient
        loss = param.sum()
        loss.backward()

        # Step
        optimizer.step()

        # Parameter should have changed
        assert not torch.allclose(param, initial_value)

    def test_pcgrad_with_single_loss(self) -> None:
        """Test PCGrad with single loss (no conflict)."""
        param = torch.randn(10, requires_grad=True)
        base_optimizer = torch.optim.SGD(
            [param], lr=0.1, momentum=0.9, weight_decay=1e-4
        )
        optimizer = PCGrad(base_optimizer)

        loss = param.sum()

        optimizer.zero_grad()
        optimizer.pc_backward([loss])
        optimizer.step()

        # Should work without errors
        assert param.grad is not None


class TestUtilsCoverage:
    """Test utils.py for coverage."""

    def test_safe_augmentations_comprehensive(self) -> None:
        """Test safe augmentations with multiple runs."""
        from PIL import Image

        # Create test image
        img = Image.new("RGB", (100, 100), color="red")

        # Run augmentation multiple times (triggers random paths)
        for _ in range(20):
            augmented = apply_safe_augmentations(img)
            assert augmented.size == img.size
            assert augmented.mode == "RGB"

    def test_soft_labels_boundary_conditions(self) -> None:
        """Test soft labels at boundaries."""
        # Test with different bin counts
        for num_bins in [5, 10, 15, 20]:
            labels = create_soft_labels(3.0, num_bins=num_bins)
            assert labels.shape == (num_bins,)
            assert torch.isclose(labels.sum(), torch.tensor(1.0))

    def test_soft_labels_extreme_fractional(self) -> None:
        """Test soft labels with extreme fractional values."""
        test_cases = [1.01, 1.99, 4.99, 2.33, 3.67]

        for mos in test_cases:
            labels = create_soft_labels(mos)
            assert torch.isclose(labels.sum(), torch.tensor(1.0))
            assert labels.min() >= 0.0
            assert labels.max() <= 1.0


class TestDatasetCoverage:
    """Test dataset.py for coverage."""

    def test_dataset_init_missing_csv(self, tmp_path: Path) -> None:
        """Test dataset initialization with missing CSV file."""
        import pytest

        from image_preprocessing_detector.labeling.hyperiqa_plus_plus.dataset import (
            DIQA5000HighResDataset,
        )

        with pytest.raises(FileNotFoundError, match="Annotations not found"):
            DIQA5000HighResDataset(root_dir=tmp_path, split="train")

    def test_dataset_load_and_getitem(self, tmp_path: Path) -> None:
        """Test dataset loading and item retrieval."""
        from PIL import Image

        from image_preprocessing_detector.labeling.hyperiqa_plus_plus.dataset import (
            DIQA5000HighResDataset,
        )

        # Create mock dataset structure
        train_dir = tmp_path / "train"
        train_dir.mkdir()
        res_dir = train_dir / "res"
        res_dir.mkdir()

        # Create test image
        test_img = Image.new("RGB", (100, 100), color="red")
        test_img.save(res_dir / "test.png")

        # Create CSV
        csv_path = train_dir / "train.csv"
        csv_path.write_text(
            "res,ori,overall,sharpness,color_fidelity\ntest.png,orig.png,3.5,4.0,3.0\n"
        )

        # Create dataset
        dataset = DIQA5000HighResDataset(
            root_dir=tmp_path,
            split="train",
            image_size=(224, 224),
            augment=False,
        )

        assert len(dataset) == 1

        # Get item
        item = dataset[0]
        assert "pixel_values" in item
        assert "targets" in item
        assert item["pixel_values"].shape[0] == 3  # RGB channels

    def test_dataset_path_traversal_prevention(self, tmp_path: Path) -> None:
        """Test that path traversal is prevented."""
        import pytest

        from image_preprocessing_detector.labeling.hyperiqa_plus_plus.dataset import (
            DIQA5000HighResDataset,
        )

        # Create mock dataset structure
        train_dir = tmp_path / "train"
        train_dir.mkdir()
        res_dir = train_dir / "res"
        res_dir.mkdir()

        # Create CSV with path traversal attempt
        csv_path = train_dir / "train.csv"
        csv_path.write_text(
            "res,ori,overall,sharpness,color_fidelity\n"
            "../../../etc/passwd,orig.png,3.5,4.0,3.0\n"
        )

        dataset = DIQA5000HighResDataset(
            root_dir=tmp_path,
            split="train",
            image_size=(224, 224),
            augment=False,
        )

        with pytest.raises(ValueError, match="Path traversal detected"):
            _ = dataset[0]

    def test_dataset_with_augmentation(self, tmp_path: Path) -> None:
        """Test dataset with augmentation enabled."""
        from PIL import Image

        from image_preprocessing_detector.labeling.hyperiqa_plus_plus.dataset import (
            DIQA5000HighResDataset,
        )

        # Create mock dataset structure
        train_dir = tmp_path / "train"
        train_dir.mkdir()
        res_dir = train_dir / "res"
        res_dir.mkdir()

        # Create test image
        test_img = Image.new("RGB", (100, 100), color="blue")
        test_img.save(res_dir / "aug_test.png")

        # Create CSV
        csv_path = train_dir / "train.csv"
        csv_path.write_text(
            "res,ori,overall,sharpness,color_fidelity\n"
            "aug_test.png,orig.png,2.5,3.0,4.0\n"
        )

        # Create dataset with augmentation
        dataset = DIQA5000HighResDataset(
            root_dir=tmp_path,
            split="train",
            image_size=(224, 224),
            augment=True,
        )

        # Get item multiple times to trigger augmentation paths
        for _ in range(5):
            item = dataset[0]
            assert item["pixel_values"].shape == (3, 224, 224)
