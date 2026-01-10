# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for MUSIQ wrapper module."""

from __future__ import annotations

import pytest
import torch
import torch.nn as nn

from image_preprocessing_detector.labeling.finetuning.musiq_wrapper import (
    MultiTaskHead,
    MultiTaskHeadConfig,
)


class TestMultiTaskHeadConfig:
    """Test MultiTaskHeadConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = MultiTaskHeadConfig()
        assert config.in_features == 384
        assert config.hidden_dim == 256
        assert config.dropout == 0.1
        assert config.num_outputs == 3

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = MultiTaskHeadConfig(
            in_features=512,
            hidden_dim=128,
            dropout=0.2,
            num_outputs=5,
        )
        assert config.in_features == 512
        assert config.hidden_dim == 128
        assert config.dropout == 0.2
        assert config.num_outputs == 5


class TestMultiTaskHead:
    """Test MultiTaskHead module."""

    @pytest.fixture
    def config(self) -> MultiTaskHeadConfig:
        """Create test configuration."""
        return MultiTaskHeadConfig(
            in_features=384,
            hidden_dim=256,
            dropout=0.1,
        )

    @pytest.fixture
    def head(self, config: MultiTaskHeadConfig) -> MultiTaskHead:
        """Create test head."""
        return MultiTaskHead(config)

    def test_initialization(self, head: MultiTaskHead) -> None:
        """Test head initialization."""
        assert isinstance(head.shared, nn.Sequential)
        assert isinstance(head.heads, nn.ModuleDict)
        assert "overall" in head.heads
        assert "sharpness" in head.heads
        assert "color" in head.heads

    def test_forward_output_shape(self, head: MultiTaskHead) -> None:
        """Test forward pass output shapes."""
        batch_size = 4
        features = torch.randn(batch_size, 384)

        outputs = head(features)

        assert "overall" in outputs
        assert "sharpness" in outputs
        assert "color" in outputs
        assert outputs["overall"].shape == (batch_size,)
        assert outputs["sharpness"].shape == (batch_size,)
        assert outputs["color"].shape == (batch_size,)

    def test_forward_output_range(self, head: MultiTaskHead) -> None:
        """Test forward pass outputs are in [0, 1]."""
        features = torch.randn(8, 384)

        outputs = head(features)

        for dim, scores in outputs.items():
            assert scores.min() >= 0.0, f"{dim} has value below 0"
            assert scores.max() <= 1.0, f"{dim} has value above 1"

    def test_forward_differentiable(self, head: MultiTaskHead) -> None:
        """Test forward pass is differentiable."""
        features = torch.randn(4, 384, requires_grad=True)

        outputs = head(features)
        loss = sum(out.sum() for out in outputs.values())
        loss.backward()

        assert features.grad is not None
        assert not torch.all(features.grad == 0)

    def test_custom_config(self) -> None:
        """Test head with custom config."""
        config = MultiTaskHeadConfig(
            in_features=512,
            hidden_dim=128,
            dropout=0.3,
        )
        head = MultiTaskHead(config)

        features = torch.randn(4, 512)
        outputs = head(features)

        assert outputs["overall"].shape == (4,)

    def test_weight_initialization(self, head: MultiTaskHead) -> None:
        """Test weights are initialized (not all zeros)."""
        for name, param in head.named_parameters():
            if "weight" in name:
                # Weights should not be all zeros after Xavier init
                assert not torch.all(param == 0), f"{name} is all zeros"


class TestMultiTaskHeadEdgeCases:
    """Test edge cases for MultiTaskHead."""

    def test_single_batch(self) -> None:
        """Test with batch size 1."""
        config = MultiTaskHeadConfig()
        head = MultiTaskHead(config)

        features = torch.randn(1, 384)
        outputs = head(features)

        assert outputs["overall"].shape == (1,)

    def test_large_batch(self) -> None:
        """Test with large batch size."""
        config = MultiTaskHeadConfig()
        head = MultiTaskHead(config)

        features = torch.randn(256, 384)
        outputs = head(features)

        assert outputs["overall"].shape == (256,)

    def test_eval_mode(self) -> None:
        """Test in eval mode (dropout disabled)."""
        config = MultiTaskHeadConfig(dropout=0.5)
        head = MultiTaskHead(config)
        head.eval()

        features = torch.randn(4, 384)

        # Run multiple times - in eval mode, outputs should be deterministic
        outputs1 = head(features)
        outputs2 = head(features)

        torch.testing.assert_close(outputs1["overall"], outputs2["overall"])

    def test_train_mode_dropout(self) -> None:
        """Test dropout affects training mode but not in a breaking way."""
        config = MultiTaskHeadConfig(dropout=0.9)  # High dropout
        head = MultiTaskHead(config)
        head.train()

        features = torch.randn(4, 384)
        outputs = head(features)

        # Should still produce valid outputs
        assert outputs["overall"].shape == (4,)
        assert not torch.any(torch.isnan(outputs["overall"]))
