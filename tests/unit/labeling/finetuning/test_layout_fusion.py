# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for Layout Fusion Downsampler module.

Tests the LayoutFusionDownsampler, LayoutMaskGenerator, and DocIQReplica
components used for IQA training with 1600x1600 document images.

Reference: docs/planning/DIQA-5000_Pseudo_Labels_v2.md Section 4.4A3
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from image_preprocessing_detector.labeling.finetuning.layout_fusion import (
    DOCLAYNET_CLASSES,
    N_LAYOUT_CLASSES,
    DocIQReplica,
    LayoutFusionConfig,
    LayoutFusionDownsampler,
    LayoutMaskGenerator,
    LayoutMaskGeneratorConfig,
    create_dociq_replica,
)


class TestLayoutFusionConfig:
    """Tests for LayoutFusionConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values match DocIQ paper."""
        config = LayoutFusionConfig()

        assert config.n_layout_classes == 11
        assert config.input_size == 1600
        assert config.output_size == 400
        assert config.layout_channels == 64
        assert config.rgb_channels == 64
        assert config.fusion_channels == 64

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = LayoutFusionConfig(
            n_layout_classes=10,
            input_size=1024,
            output_size=256,
            layout_channels=32,
        )

        assert config.n_layout_classes == 10
        assert config.input_size == 1024
        assert config.output_size == 256
        assert config.layout_channels == 32


class TestLayoutFusionDownsampler:
    """Tests for LayoutFusionDownsampler module."""

    def test_initialization_default(self) -> None:
        """Test default initialization."""
        downsampler = LayoutFusionDownsampler()

        assert downsampler.config.n_layout_classes == 11
        assert isinstance(downsampler.layout_encoder, torch.nn.Sequential)
        assert isinstance(downsampler.rgb_encoder, torch.nn.Sequential)
        assert isinstance(downsampler.fusion, torch.nn.Sequential)

    def test_initialization_with_config(self) -> None:
        """Test initialization with custom config."""
        config = LayoutFusionConfig(n_layout_classes=10)
        downsampler = LayoutFusionDownsampler(config=config)

        assert downsampler.config.n_layout_classes == 10

    def test_initialization_with_n_classes(self) -> None:
        """Test initialization with n_layout_classes parameter."""
        downsampler = LayoutFusionDownsampler(n_layout_classes=8)

        assert downsampler.config.n_layout_classes == 8

    def test_forward_shape_standard(self) -> None:
        """Test forward pass produces correct output shape.

        Uses 400x400 input for faster testing - the 4x downsampling math
        is identical regardless of input size.
        """
        downsampler = LayoutFusionDownsampler()
        batch_size = 2

        # Use smaller tensors for faster testing (same code path as 1600x1600)
        rgb = torch.randn(batch_size, 3, 400, 400)
        layout = torch.randn(batch_size, 11, 400, 400)

        output = downsampler(rgb, layout)

        # Expected output: 400px input with 4x downsampling produces 100px output
        assert output.shape == (batch_size, 3, 100, 100)

    def test_forward_shape_smaller_input(self) -> None:
        """Test forward pass with smaller input sizes."""
        downsampler = LayoutFusionDownsampler()
        batch_size = 2

        # Smaller input should still work
        rgb = torch.randn(batch_size, 3, 800, 800)
        layout = torch.randn(batch_size, 11, 800, 800)

        output = downsampler(rgb, layout)

        # (800 + 6 - 7) / 4 + 1 = 200
        assert output.shape == (batch_size, 3, 200, 200)

    def test_forward_invalid_rgb_shape(self) -> None:
        """Test forward raises error for invalid RGB shape."""
        downsampler = LayoutFusionDownsampler()

        rgb = torch.randn(2, 4, 1600, 1600)  # Wrong channel count
        layout = torch.randn(2, 11, 1600, 1600)

        with pytest.raises(ValueError, match="Expected RGB shape"):
            downsampler(rgb, layout)

    def test_forward_invalid_layout_shape(self) -> None:
        """Test forward raises error for invalid layout shape."""
        downsampler = LayoutFusionDownsampler()

        rgb = torch.randn(2, 3, 1600, 1600)
        layout = torch.randn(2, 10, 1600, 1600)  # Wrong channel count

        with pytest.raises(ValueError, match="Expected layout shape"):
            downsampler(rgb, layout)

    def test_forward_size_mismatch_handling(self) -> None:
        """Test forward handles RGB/layout size mismatch gracefully."""
        downsampler = LayoutFusionDownsampler()

        # Slightly different sizes should be interpolated
        # Use smaller tensors for faster testing
        rgb = torch.randn(2, 3, 400, 400)
        layout = torch.randn(2, 11, 396, 396)  # Slightly smaller

        output = downsampler(rgb, layout)

        assert output.shape[0] == 2
        assert output.shape[1] == 3

    def test_get_output_size(self) -> None:
        """Test output size calculation."""
        downsampler = LayoutFusionDownsampler()

        assert downsampler.get_output_size(1600) == 400
        assert downsampler.get_output_size(800) == 200
        assert downsampler.get_output_size(400) == 100

    def test_gradient_flow(self) -> None:
        """Test gradients flow through the module."""
        downsampler = LayoutFusionDownsampler()

        rgb = torch.randn(1, 3, 400, 400, requires_grad=True)
        layout = torch.randn(1, 11, 400, 400, requires_grad=True)

        output = downsampler(rgb, layout)
        loss = output.sum()
        loss.backward()

        assert rgb.grad is not None
        assert layout.grad is not None


class TestLayoutMaskGeneratorConfig:
    """Tests for LayoutMaskGeneratorConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = LayoutMaskGeneratorConfig()

        assert config.target_size == (1600, 1600)
        assert config.n_classes == 11
        assert config.confidence_threshold == 0.25
        assert config.cache_dir is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = LayoutMaskGeneratorConfig(
            target_size=(800, 800),
            confidence_threshold=0.5,
            cache_dir="/tmp/mask_cache",  # nosec B108 - test fixture
        )

        assert config.target_size == (800, 800)
        assert config.confidence_threshold == 0.5
        assert config.cache_dir == "/tmp/mask_cache"  # nosec B108 - test fixture


class TestLayoutMaskGenerator:
    """Tests for LayoutMaskGenerator class."""

    def test_initialization_default(self) -> None:
        """Test default initialization."""
        generator = LayoutMaskGenerator()

        assert generator.config.n_classes == 11
        assert generator._detector is None  # Lazy loaded
        assert generator._cache_path is None

    def test_initialization_with_cache(self, tmp_path) -> None:
        """Test initialization with cache directory."""
        cache_dir = str(tmp_path / "masks")
        config = LayoutMaskGeneratorConfig(cache_dir=cache_dir)
        generator = LayoutMaskGenerator(config=config)

        assert generator._cache_path is not None
        assert generator._cache_path.exists()

    def test_class_mapping_complete(self) -> None:
        """Test all DocLayNet classes have mappings."""
        # Check that all 11 classes are covered
        mapped_indices = set(LayoutMaskGenerator.CLASS_MAPPING.values())
        expected_indices = set(range(11))

        assert mapped_indices == expected_indices

    def test_class_mapping_variants(self) -> None:
        """Test class name variants map correctly."""
        mapping = LayoutMaskGenerator.CLASS_MAPPING

        # Test various formats
        assert mapping["list-item"] == mapping["list_item"] == mapping["listitem"] == 3
        assert mapping["page-footer"] == mapping["page_footer"] == 4
        assert mapping["picture"] == mapping["figure"] == mapping["image"] == 6

    def test_generate_mask_output_shape(self) -> None:
        """Test generate_mask produces correct shape."""
        generator = LayoutMaskGenerator()

        # Mock the detector and the import
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.elements = []

        # Create a mock module to patch the import
        mock_doclayout = MagicMock()
        mock_doclayout.LayoutDetectionResult = type("LayoutDetectionResult", (), {})

        with (
            patch.object(generator, "_load_detector"),
            patch.dict(
                "sys.modules",
                {
                    "image_preprocessing_detector.detection.doclayout_yolo": mock_doclayout
                },
            ),
        ):
            generator._detector = MagicMock()
            generator._detector.detect.return_value = mock_result

            image = np.random.randint(0, 255, (1600, 1600, 3), dtype=np.uint8)
            mask = generator.generate_mask(image)

            assert mask.shape == (11, 1600, 1600)
            assert mask.dtype == np.float32

    def test_generate_mask_with_detections(self) -> None:
        """Test generate_mask with detected elements."""
        generator = LayoutMaskGenerator()

        # Mock detection result with elements
        mock_element = MagicMock()
        mock_element.class_name = "Text"
        mock_element.confidence = 0.9
        mock_element.bbox_xyxy = [100, 100, 500, 500]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.elements = [mock_element]

        mock_doclayout = MagicMock()
        mock_doclayout.LayoutDetectionResult = type("LayoutDetectionResult", (), {})

        with (
            patch.object(generator, "_load_detector"),
            patch.dict(
                "sys.modules",
                {
                    "image_preprocessing_detector.detection.doclayout_yolo": mock_doclayout
                },
            ),
        ):
            generator._detector = MagicMock()
            generator._detector.detect.return_value = mock_result

            image = np.random.randint(0, 255, (1600, 1600, 3), dtype=np.uint8)
            mask = generator.generate_mask(image)

            # Text class (index 9) should have non-zero values
            assert mask[9, 100:500, 100:500].sum() > 0

    def test_generate_mask_custom_target_size(self) -> None:
        """Test generate_mask with custom target size."""
        generator = LayoutMaskGenerator()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.elements = []

        mock_doclayout = MagicMock()
        mock_doclayout.LayoutDetectionResult = type("LayoutDetectionResult", (), {})

        with (
            patch.object(generator, "_load_detector"),
            patch.dict(
                "sys.modules",
                {
                    "image_preprocessing_detector.detection.doclayout_yolo": mock_doclayout
                },
            ),
        ):
            generator._detector = MagicMock()
            generator._detector.detect.return_value = mock_result

            image = np.random.randint(0, 255, (800, 800, 3), dtype=np.uint8)
            mask = generator.generate_mask(image, target_size=(400, 400))

            assert mask.shape == (11, 400, 400)

    def test_generate_mask_tensor(self) -> None:
        """Test generate_mask_tensor returns torch tensor."""
        generator = LayoutMaskGenerator()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.elements = []

        mock_doclayout = MagicMock()
        mock_doclayout.LayoutDetectionResult = type("LayoutDetectionResult", (), {})

        with (
            patch.object(generator, "_load_detector"),
            patch.dict(
                "sys.modules",
                {
                    "image_preprocessing_detector.detection.doclayout_yolo": mock_doclayout
                },
            ),
        ):
            generator._detector = MagicMock()
            generator._detector.detect.return_value = mock_result

            image = np.random.randint(0, 255, (400, 400, 3), dtype=np.uint8)
            tensor = generator.generate_mask_tensor(
                image, target_size=(400, 400), device="cpu"
            )

            assert isinstance(tensor, torch.Tensor)
            assert tensor.shape == (11, 400, 400)
            assert tensor.device.type == "cpu"

    def test_batch_generate(self) -> None:
        """Test batch_generate processes multiple images."""
        generator = LayoutMaskGenerator()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.elements = []

        mock_doclayout = MagicMock()
        mock_doclayout.LayoutDetectionResult = type("LayoutDetectionResult", (), {})

        with (
            patch.object(generator, "_load_detector"),
            patch.dict(
                "sys.modules",
                {
                    "image_preprocessing_detector.detection.doclayout_yolo": mock_doclayout
                },
            ),
        ):
            generator._detector = MagicMock()
            generator._detector.detect.return_value = mock_result

            images = [
                np.random.randint(0, 255, (400, 400, 3), dtype=np.uint8)
                for _ in range(3)
            ]
            masks = generator.batch_generate(images, target_size=(400, 400))

            assert len(masks) == 3
            assert all(m.shape == (11, 400, 400) for m in masks)

    def test_cache_key_generation(self) -> None:
        """Test cache key is deterministic for same image."""
        generator = LayoutMaskGenerator()

        image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        key1 = generator._get_cache_key(image)
        key2 = generator._get_cache_key(image)

        assert key1 == key2
        assert len(key1) == 32  # MD5 hex digest


class TestDocIQReplica:
    """Tests for DocIQReplica model."""

    def test_initialization_default(self) -> None:
        """Test default initialization with frozen backbone."""
        model = DocIQReplica(freeze_backbone=True, pretrained_backbone=False)

        assert model.is_backbone_frozen
        assert isinstance(model.downsampler, LayoutFusionDownsampler)
        assert model.head_config.in_features == 2048

    def test_initialization_unfrozen(self) -> None:
        """Test initialization with unfrozen backbone."""
        model = DocIQReplica(freeze_backbone=False, pretrained_backbone=False)

        assert not model.is_backbone_frozen

    def test_forward_shape(self) -> None:
        """Test forward pass produces correct output shape.

        Uses 400x400 input for faster testing - architecture is size-agnostic.
        """
        model = DocIQReplica(freeze_backbone=True, pretrained_backbone=False)
        batch_size = 2

        # Use smaller tensors for faster testing
        rgb = torch.randn(batch_size, 3, 400, 400)
        layout = torch.randn(batch_size, 11, 400, 400)

        outputs = model(rgb, layout)

        assert "overall" in outputs
        assert "sharpness" in outputs
        assert "color" in outputs
        assert outputs["overall"].shape == (batch_size,)
        assert outputs["sharpness"].shape == (batch_size,)
        assert outputs["color"].shape == (batch_size,)

    def test_forward_output_range(self) -> None:
        """Test forward outputs are in [0, 1] range (sigmoid)."""
        model = DocIQReplica(freeze_backbone=True, pretrained_backbone=False)

        rgb = torch.randn(4, 3, 400, 400)
        layout = torch.randn(4, 11, 400, 400)

        outputs = model(rgb, layout)

        for dim in ["overall", "sharpness", "color"]:
            assert (outputs[dim] >= 0).all()
            assert (outputs[dim] <= 1).all()

    def test_freeze_unfreeze_backbone(self) -> None:
        """Test backbone freezing and unfreezing."""
        model = DocIQReplica(freeze_backbone=True, pretrained_backbone=False)

        assert model.is_backbone_frozen

        # Check backbone params are frozen
        for param in model.backbone.parameters():
            assert not param.requires_grad

        # Unfreeze
        model.unfreeze_backbone()
        assert not model.is_backbone_frozen

        # Check backbone params are trainable
        for param in model.backbone.parameters():
            assert param.requires_grad

    def test_get_backbone_params(self) -> None:
        """Test get_backbone_params returns correct parameters."""
        model = DocIQReplica(freeze_backbone=False, pretrained_backbone=False)

        backbone_params = model.get_backbone_params()

        assert len(backbone_params) > 0
        # Should include both backbone and downsampler params
        total_backbone = sum(p.numel() for p in model.backbone.parameters())
        total_downsampler = sum(p.numel() for p in model.downsampler.parameters())
        param_count = sum(p.numel() for p in backbone_params)
        assert param_count == total_backbone + total_downsampler

    def test_get_head_params(self) -> None:
        """Test get_head_params returns correct parameters."""
        model = DocIQReplica(freeze_backbone=True, pretrained_backbone=False)

        head_params = model.get_head_params()

        assert len(head_params) > 0
        head_count = sum(p.numel() for p in model.head.parameters())
        param_count = sum(p.numel() for p in head_params)
        assert param_count == head_count

    def test_get_trainable_params_frozen(self) -> None:
        """Test trainable param count with frozen backbone."""
        model = DocIQReplica(freeze_backbone=True, pretrained_backbone=False)

        trainable = model.get_trainable_params()
        total = model.get_total_params()

        # Only head should be trainable
        assert trainable < total
        assert trainable == sum(p.numel() for p in model.head.parameters())

    def test_get_trainable_params_unfrozen(self) -> None:
        """Test trainable param count with unfrozen backbone."""
        model = DocIQReplica(freeze_backbone=False, pretrained_backbone=False)

        trainable = model.get_trainable_params()
        total = model.get_total_params()

        # All params should be trainable
        assert trainable == total

    def test_gradient_flow_frozen(self) -> None:
        """Test gradients only flow to head when backbone frozen."""
        model = DocIQReplica(freeze_backbone=True, pretrained_backbone=False)

        rgb = torch.randn(1, 3, 400, 400)
        layout = torch.randn(1, 11, 400, 400)

        outputs = model(rgb, layout)
        # Use all outputs so all head branches get gradients
        loss = (
            outputs["overall"].sum()
            + outputs["sharpness"].sum()
            + outputs["color"].sum()
        )
        loss.backward()

        # Head should have gradients (at least some trainable params)
        head_has_grad = any(
            p.grad is not None for p in model.head.parameters() if p.requires_grad
        )
        assert head_has_grad, "Head should have gradients"

        # Backbone should not have gradients
        for param in model.backbone.parameters():
            assert param.grad is None

    def test_gradient_flow_unfrozen(self) -> None:
        """Test gradients flow everywhere when backbone unfrozen."""
        model = DocIQReplica(freeze_backbone=False, pretrained_backbone=False)

        rgb = torch.randn(1, 3, 400, 400)
        layout = torch.randn(1, 11, 400, 400)

        outputs = model(rgb, layout)
        loss = outputs["overall"].sum()
        loss.backward()

        # Both head and some backbone params should have gradients
        head_has_grad = any(
            p.grad is not None for p in model.head.parameters() if p.requires_grad
        )
        backbone_has_grad = any(
            p.grad is not None for p in model.backbone.parameters() if p.requires_grad
        )

        assert head_has_grad
        assert backbone_has_grad


class TestCreateDocIQReplica:
    """Tests for create_dociq_replica factory function."""

    def test_creates_model(self) -> None:
        """Test factory creates valid model."""
        model = create_dociq_replica(
            device="cpu",
            freeze_backbone=True,
            pretrained_backbone=False,
        )

        assert isinstance(model, DocIQReplica)
        assert model.is_backbone_frozen

    def test_custom_head_config(self) -> None:
        """Test factory with custom head configuration."""
        model = create_dociq_replica(
            device="cpu",
            freeze_backbone=True,
            head_hidden_dim=256,
            head_dropout=0.2,
            pretrained_backbone=False,
        )

        assert model.head_config.hidden_dim == 256
        assert model.head_config.dropout == 0.2


class TestDocLayNetClasses:
    """Tests for DocLayNet class constants."""

    def test_class_count(self) -> None:
        """Test correct number of classes."""
        assert N_LAYOUT_CLASSES == 11
        assert len(DOCLAYNET_CLASSES) == 11

    def test_class_names(self) -> None:
        """Test class names match DocLayNet specification."""
        expected = [
            "Caption",
            "Footnote",
            "Formula",
            "List-Item",
            "Page-Footer",
            "Page-Header",
            "Picture",
            "Section-Header",
            "Table",
            "Text",
            "Title",
        ]

        assert expected == DOCLAYNET_CLASSES
