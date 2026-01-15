# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for HyperIQA++ components."""

from __future__ import annotations

from pathlib import Path

import pytest
import torch
import torch.nn as nn
from torchvision.models import ResNet50_Weights, resnet50

from image_preprocessing_detector.labeling.hyperiqa_plus_plus.loss import (
    MultiTaskIQALoss,
    NormInNormLoss,
)
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.model import (
    HyperIQAPlusPlus,
)
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.modules import (
    MultiScaleFeatureFusion,
    SoftLabelHead,
    SpatialAttentionModule,
)
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.utils import (
    compute_vquala_score,
    create_soft_labels,
    denormalize_score_to_mos,
    normalize_mos_to_01,
)


class TestSoftLabelUtils:
    """Test soft label creation utilities."""

    def test_create_soft_labels_integer_mos(self) -> None:
        """Test soft labels for integer MOS values."""
        # MOS = 3.0 should put all mass on bin corresponding to 3
        labels = create_soft_labels(3.0, num_bins=10)

        assert labels.shape == (10,)
        assert torch.isclose(labels.sum(), torch.tensor(1.0))  # Valid distribution
        assert labels.max() >= 0.9  # Most mass on single bin

    def test_create_soft_labels_fractional_mos(self) -> None:
        """Test soft labels for fractional MOS values."""
        # MOS = 3.7 should split mass between bins for 3 and 4
        labels = create_soft_labels(3.7, num_bins=10)

        assert labels.shape == (10,)
        assert torch.isclose(labels.sum(), torch.tensor(1.0), atol=0.01)
        # Should have two non-zero bins
        assert (labels > 0).sum() == 2

    def test_create_soft_labels_edge_cases(self) -> None:
        """Test soft labels for edge MOS values."""
        # MOS = 1.0 (minimum)
        labels_min = create_soft_labels(1.0, num_bins=10)
        assert labels_min[0] >= 0.9  # Mass on first bin

        # MOS = 5.0 (maximum)
        labels_max = create_soft_labels(5.0, num_bins=10)
        assert labels_max[-1] >= 0.9  # Mass on last bin

    def test_normalize_mos_to_01(self) -> None:
        """Test MOS normalization to [0, 1] range."""
        assert normalize_mos_to_01(1.0) == 0.0
        assert normalize_mos_to_01(5.0) == 1.0
        assert normalize_mos_to_01(3.0) == 0.5

    def test_denormalize_score_to_mos(self) -> None:
        """Test denormalization from [0, 1] to MOS [1, 5]."""
        assert denormalize_score_to_mos(0.0) == 1.0
        assert denormalize_score_to_mos(1.0) == 5.0
        assert denormalize_score_to_mos(0.5) == 3.0

    def test_compute_vquala_score(self) -> None:
        """Test VQualA score computation."""
        # VQualA = 0.5xoverall + 0.25xsharpness + 0.25xcolor
        score = compute_vquala_score(0.8, 0.7, 0.6)
        expected = 0.5 * 0.8 + 0.25 * 0.7 + 0.25 * 0.6
        assert abs(score - expected) < 1e-6


class TestMultiScaleFeatureFusion:
    """Test multi-scale feature fusion module."""

    @pytest.fixture
    def backbone(self) -> nn.Module:
        """Create ResNet-50 backbone."""
        return resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)

    @pytest.fixture
    def fusion_module(self, backbone: nn.Module) -> MultiScaleFeatureFusion:
        """Create feature fusion module."""
        return MultiScaleFeatureFusion(backbone)

    def test_feature_fusion_output_shape(
        self, fusion_module: MultiScaleFeatureFusion
    ) -> None:
        """Test feature fusion produces correct output shape."""
        x = torch.randn(2, 3, 224, 224)  # Small input for testing

        output = fusion_module(x)

        # Should output 2048-channel features
        assert output.shape[0] == 2  # Batch size
        assert output.shape[1] == 2048  # Channels

    def test_feature_fusion_gradient_flow(
        self, fusion_module: MultiScaleFeatureFusion
    ) -> None:
        """Test gradients flow through all fusion stages."""
        x = torch.randn(2, 3, 224, 224, requires_grad=True)

        output = fusion_module(x)
        loss = output.sum()
        loss.backward()

        # All projection layers should have gradients
        assert fusion_module.proj1.weight.grad is not None
        assert fusion_module.proj2.weight.grad is not None
        assert fusion_module.proj3.weight.grad is not None
        assert fusion_module.proj4.weight.grad is not None


class TestSpatialAttentionModule:
    """Test spatial attention module."""

    def test_attention_output_shape(self) -> None:
        """Test attention produces correct output shapes."""
        module = SpatialAttentionModule(in_channels=2048)
        features = torch.randn(2, 2048, 7, 7)

        attended, attn_map = module(features)

        assert attended.shape == features.shape  # Same as input
        assert attn_map.shape == (2, 1, 7, 7)  # [B, 1, H, W]

    def test_attention_range(self) -> None:
        """Test attention map values in [0, 1] range."""
        module = SpatialAttentionModule(in_channels=2048)
        features = torch.randn(2, 2048, 7, 7)

        _, attn_map = module(features)

        assert attn_map.min() >= 0.0
        assert attn_map.max() <= 1.0


class TestSoftLabelHead:
    """Test soft label distribution head."""

    def test_head_output_shapes(self) -> None:
        """Test head produces correct output shapes."""
        head = SoftLabelHead(embed_dim=2048, num_bins=10)
        features = torch.randn(4, 2048)

        score, probs, logits = head(features)

        assert score.shape == (4,)  # [B]
        assert probs.shape == (4, 10)  # [B, num_bins]
        assert logits.shape == (4, 10)  # [B, num_bins]

    def test_head_probability_distribution(self) -> None:
        """Test probabilities sum to 1."""
        head = SoftLabelHead(embed_dim=2048, num_bins=10)
        features = torch.randn(4, 2048)

        _, probs, _ = head(features)

        # Each sample's probabilities should sum to 1
        prob_sums = probs.sum(dim=1)
        assert torch.allclose(prob_sums, torch.ones(4), atol=1e-5)

    def test_head_score_in_range(self) -> None:
        """Test predicted scores are in valid MOS range [1, 5]."""
        head = SoftLabelHead(embed_dim=2048, num_bins=10)
        features = torch.randn(4, 2048)

        score, _, _ = head(features)

        # Scores should be in [1, 5] range (MOS scale)
        assert score.min() >= 1.0
        assert score.max() <= 5.0


class TestNormInNormLoss:
    """Test NormInNorm loss function."""

    def test_loss_perfect_prediction(self) -> None:
        """Test loss is zero for perfect predictions."""
        criterion = NormInNormLoss()
        pred = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        target = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])

        loss = criterion(pred, target)

        assert loss.item() < 1e-6  # Should be near zero

    def test_loss_worst_prediction(self) -> None:
        """Test loss is high for completely wrong predictions."""
        criterion = NormInNormLoss()
        pred = torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0])
        target = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])

        loss = criterion(pred, target)

        assert loss.item() > 0.5  # Should be substantial

    def test_loss_gradient_flow(self) -> None:
        """Test gradients flow through loss."""
        criterion = NormInNormLoss()
        pred = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
        target = torch.tensor([1.5, 2.5, 3.5])

        loss = criterion(pred, target)
        loss.backward()

        assert pred.grad is not None
        assert not torch.isnan(pred.grad).any()


class TestMultiTaskIQALoss:
    """Test multi-task IQA loss."""

    @pytest.fixture
    def sample_predictions(self) -> dict:
        """Create sample predictions."""
        return {
            "overall": {
                "score": torch.tensor([0.5, 0.6]),
                "probs": torch.softmax(torch.randn(2, 10), dim=-1),
                "logits": torch.randn(2, 10),
            },
            "sharpness": {
                "score": torch.tensor([0.4, 0.7]),
                "probs": torch.softmax(torch.randn(2, 10), dim=-1),
                "logits": torch.randn(2, 10),
            },
            "color": {
                "score": torch.tensor([0.6, 0.5]),
                "probs": torch.softmax(torch.randn(2, 10), dim=-1),
                "logits": torch.randn(2, 10),
            },
        }

    @pytest.fixture
    def sample_targets(self) -> dict:
        """Create sample targets."""
        return {
            "overall": {
                "mos": torch.tensor([0.5, 0.6]),
                "soft_labels": torch.softmax(torch.randn(2, 10), dim=-1),
            },
            "sharpness": {
                "mos": torch.tensor([0.4, 0.7]),
                "soft_labels": torch.softmax(torch.randn(2, 10), dim=-1),
            },
            "color": {
                "mos": torch.tensor([0.6, 0.5]),
                "soft_labels": torch.softmax(torch.randn(2, 10), dim=-1),
            },
        }

    def test_multitask_loss_dict_output(
        self, sample_predictions: dict, sample_targets: dict
    ) -> None:
        """Test loss returns dictionary by default."""
        criterion = MultiTaskIQALoss()

        loss_dict = criterion(sample_predictions, sample_targets, return_per_dim=False)

        assert isinstance(loss_dict, dict)
        assert "loss_overall" in loss_dict
        assert "loss_sharpness" in loss_dict
        assert "loss_color" in loss_dict
        assert "loss_total" in loss_dict

    def test_multitask_loss_list_output_for_pcgrad(
        self, sample_predictions: dict, sample_targets: dict
    ) -> None:
        """Test loss returns list for PCGrad when requested."""
        criterion = MultiTaskIQALoss()

        losses = criterion(sample_predictions, sample_targets, return_per_dim=True)

        assert isinstance(losses, list)
        assert len(losses) == 3  # One per dimension


@pytest.mark.slow
class TestHyperIQAPlusPlus:
    """Test full HyperIQA++ model."""

    @pytest.mark.skipif(
        not torch.cuda.is_available(), reason="Requires GPU for full model test"
    )
    def test_model_forward_pass_high_res(self) -> None:
        """Test model forward pass with 1600x1600 input."""
        # Note: This test loads pretrained weights, skip in CI if needed
        try:
            model = HyperIQAPlusPlus(
                num_bins=10,
                freeze_backbone_epochs=10,
                use_pretrained=True,
            )
        except Exception:
            pytest.skip("PyIQA not available or HyperIQA weights not accessible")

        model.eval()

        # 1600x1600 input (DocIQ protocol)
        x = torch.randn(2, 3, 1600, 1600)

        with torch.no_grad():
            outputs = model(x)

        # Check outputs
        assert "overall" in outputs
        assert "sharpness" in outputs
        assert "color" in outputs
        assert "attention_map" in outputs

        # Check each dimension has correct keys
        for dim in ["overall", "sharpness", "color"]:
            assert "score" in outputs[dim]
            assert "probs" in outputs[dim]
            assert "logits" in outputs[dim]

            # Check shapes
            assert outputs[dim]["score"].shape == (2,)
            assert outputs[dim]["probs"].shape == (2, 10)
            assert outputs[dim]["logits"].shape == (2, 10)

    def test_model_freeze_unfreeze(self) -> None:
        """Test backbone freezing/unfreezing."""
        model = HyperIQAPlusPlus(use_pretrained=False)  # Don't load weights

        # Initially unfrozen
        assert any(p.requires_grad for p in model.backbone.parameters())

        # Freeze
        model.freeze_backbone()
        assert not any(p.requires_grad for p in model.backbone.parameters())
        assert not any(p.requires_grad for p in model.feature_fusion.parameters())
        assert model._frozen is True

        # Heads should still be trainable
        assert all(p.requires_grad for p in model.head_overall.parameters())

        # Unfreeze
        model.unfreeze_backbone()
        assert any(p.requires_grad for p in model.backbone.parameters())
        assert model._frozen is False

    def test_model_parameter_counts(self) -> None:
        """Test parameter counting."""
        model = HyperIQAPlusPlus(use_pretrained=False)

        param_counts = model.get_num_parameters()

        assert "total" in param_counts
        assert "backbone" in param_counts
        assert "hypernet" in param_counts
        assert param_counts["total"] > 0
        # ResNet-50 should be ~25M params
        assert param_counts["backbone"] > 20_000_000


class TestMultiScaleFeatureFusionAdvanced:
    """Test multi-scale feature fusion advanced scenarios."""

    @pytest.fixture
    def backbone(self) -> nn.Module:
        """Create ResNet-50 backbone."""
        return resnet50(weights=None)  # Don't download weights for test

    @pytest.fixture
    def fusion(self, backbone: nn.Module) -> MultiScaleFeatureFusion:
        """Create fusion module."""
        return MultiScaleFeatureFusion(backbone)

    def test_fusion_output_channels(self, fusion: MultiScaleFeatureFusion) -> None:
        """Test fusion outputs 2048 channels."""
        x = torch.randn(1, 3, 224, 224)

        output = fusion(x)

        assert output.shape[1] == 2048  # Output channels

    def test_fusion_handles_different_resolutions(
        self, fusion: MultiScaleFeatureFusion
    ) -> None:
        """Test fusion works with different input resolutions."""
        resolutions = [(224, 224), (384, 384), (512, 512)]

        for h, w in resolutions:
            x = torch.randn(1, 3, h, w)
            output = fusion(x)

            assert output.shape[1] == 2048  # Always 2048 channels
            assert output.shape[2] > 0  # Valid spatial dimensions
            assert output.shape[3] > 0


class TestTrainingIntegration:
    """Integration tests for training components."""

    def test_full_training_step_no_pcgrad(self) -> None:
        """Test training step without PCGrad."""
        model = HyperIQAPlusPlus(use_pretrained=False)
        model.train()

        criterion = MultiTaskIQALoss(use_norm_in_norm=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

        # Create dummy batch
        batch = {
            "pixel_values": torch.randn(2, 3, 384, 384),  # Smaller for test
            "targets": {
                "overall": {
                    "mos": torch.tensor([0.5, 0.6]),
                    "soft_labels": torch.softmax(torch.randn(2, 10), dim=-1),
                },
                "sharpness": {
                    "mos": torch.tensor([0.4, 0.7]),
                    "soft_labels": torch.softmax(torch.randn(2, 10), dim=-1),
                },
                "color": {
                    "mos": torch.tensor([0.6, 0.5]),
                    "soft_labels": torch.softmax(torch.randn(2, 10), dim=-1),
                },
            },
        }

        # Forward pass
        outputs = model(batch["pixel_values"])
        loss_dict = criterion(outputs, batch["targets"], return_per_dim=False)

        # Backward pass
        loss_dict["loss_total"].backward()
        optimizer.step()

        # Check loss is valid
        assert not torch.isnan(loss_dict["loss_total"])
        assert loss_dict["loss_total"].item() > 0

    def test_model_saves_and_loads(self, tmp_path: Path) -> None:
        """Test model checkpoint saving and loading."""
        model = HyperIQAPlusPlus(use_pretrained=False)

        # Save checkpoint
        checkpoint_path = tmp_path / "test_checkpoint.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "epoch": 10,
            },
            checkpoint_path,
        )

        # Load into new model
        model_loaded = HyperIQAPlusPlus(use_pretrained=False)
        checkpoint = torch.load(checkpoint_path, weights_only=False)
        model_loaded.load_state_dict(checkpoint["model_state_dict"])

        # Compare parameters
        for (n1, p1), (n2, p2) in zip(
            model.named_parameters(), model_loaded.named_parameters()
        ):
            assert n1 == n2
            assert torch.allclose(p1, p2)
