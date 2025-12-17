# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Tests for DIQA regression head architecture."""

from __future__ import annotations

import pytest
import torch

from image_preprocessing_detector.labeling.finetuning.regression_head import (
    DIQAOutput,
    DIQARegressionHead,
    RegressionHeadConfig,
)


class TestRegressionHeadConfig:
    """Tests for RegressionHeadConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RegressionHeadConfig()

        assert config.hidden_size == 768
        assert config.intermediate_size == 256
        assert config.num_outputs == 3
        assert config.dropout == 0.1
        assert config.activation == "gelu"
        assert config.use_layer_norm is True
        assert config.pooling_strategy == "mean"

    def test_custom_config(self):
        """Test custom configuration."""
        config = RegressionHeadConfig(
            hidden_size=1024,
            intermediate_size=512,
            dropout=0.2,
            pooling_strategy="cls",
        )

        assert config.hidden_size == 1024
        assert config.intermediate_size == 512
        assert config.dropout == 0.2
        assert config.pooling_strategy == "cls"

    def test_to_dict(self):
        """Test dictionary conversion."""
        config = RegressionHeadConfig(hidden_size=512)
        config_dict = config.to_dict()

        assert config_dict["hidden_size"] == 512
        assert "intermediate_size" in config_dict
        assert "activation" in config_dict


class TestDIQARegressionHead:
    """Tests for DIQARegressionHead module."""

    @pytest.fixture
    def head(self):
        """Create a regression head for testing."""
        config = RegressionHeadConfig(hidden_size=768)
        return DIQARegressionHead(config)

    def test_forward_3d_input(self, head):
        """Test forward pass with 3D input (batch, seq, hidden)."""
        batch_size = 4
        seq_len = 197
        hidden_size = 768

        hidden_states = torch.randn(batch_size, seq_len, hidden_size)
        output = head(hidden_states)

        assert output.shape == (batch_size, 3)
        assert output.min() >= 0.0
        assert output.max() <= 1.0

    def test_forward_2d_input(self, head):
        """Test forward pass with 2D input (batch, hidden)."""
        batch_size = 4
        hidden_size = 768

        hidden_states = torch.randn(batch_size, hidden_size)
        output = head(hidden_states)

        assert output.shape == (batch_size, 3)
        assert output.min() >= 0.0
        assert output.max() <= 1.0

    def test_output_in_valid_range(self, head):
        """Test that outputs are always in [0, 1] range."""
        # Test with various input magnitudes
        for scale in [0.1, 1.0, 10.0, 100.0]:
            hidden_states = torch.randn(8, 197, 768) * scale
            output = head(hidden_states)

            assert output.min() >= 0.0, f"Output below 0 with scale {scale}"
            assert output.max() <= 1.0, f"Output above 1 with scale {scale}"

    def test_pooling_strategies(self):
        """Test different pooling strategies."""
        for strategy in ["mean", "cls", "max"]:
            config = RegressionHeadConfig(
                hidden_size=768,
                pooling_strategy=strategy,
            )
            head = DIQARegressionHead(config)

            hidden_states = torch.randn(4, 197, 768)
            output = head(hidden_states)

            assert output.shape == (4, 3)

    def test_activation_functions(self):
        """Test different activation functions."""
        for activation in ["gelu", "relu", "silu"]:
            config = RegressionHeadConfig(
                hidden_size=768,
                activation=activation,
            )
            head = DIQARegressionHead(config)

            hidden_states = torch.randn(4, 197, 768)
            output = head(hidden_states)

            assert output.shape == (4, 3)

    def test_without_layer_norm(self):
        """Test head without layer normalization."""
        config = RegressionHeadConfig(
            hidden_size=768,
            use_layer_norm=False,
        )
        head = DIQARegressionHead(config)

        hidden_states = torch.randn(4, 197, 768)
        output = head(hidden_states)

        assert output.shape == (4, 3)

    def test_gradient_flow(self, head):
        """Test that gradients flow through the head."""
        hidden_states = torch.randn(4, 197, 768, requires_grad=True)
        output = head(hidden_states)
        loss = output.sum()
        loss.backward()

        assert hidden_states.grad is not None
        assert hidden_states.grad.shape == hidden_states.shape


class TestDIQAOutput:
    """Tests for DIQAOutput dataclass."""

    def test_from_tensor_1d(self):
        """Test creating output from 1D tensor."""
        scores = torch.tensor([0.8, 0.7, 0.9])
        output = DIQAOutput.from_tensor(scores)

        assert output.overall == pytest.approx(0.8, abs=0.01)
        assert output.sharpness == pytest.approx(0.7, abs=0.01)
        assert output.color == pytest.approx(0.9, abs=0.01)

    def test_from_tensor_2d(self):
        """Test creating output from 2D tensor."""
        scores = torch.tensor([[0.8, 0.7, 0.9]])
        output = DIQAOutput.from_tensor(scores)

        assert output.overall == pytest.approx(0.8, abs=0.01)
        assert output.sharpness == pytest.approx(0.7, abs=0.01)
        assert output.color == pytest.approx(0.9, abs=0.01)

    def test_scores_tensor_preserved(self):
        """Test that scores tensor is preserved in output."""
        scores = torch.tensor([0.5, 0.6, 0.7])
        output = DIQAOutput.from_tensor(scores)

        assert output.scores is not None
        assert torch.allclose(output.scores, scores)

    def test_manual_creation(self):
        """Test manual output creation."""
        output = DIQAOutput(
            overall=0.8,
            sharpness=0.7,
            color=0.9,
        )

        assert output.overall == 0.8
        assert output.sharpness == 0.7
        assert output.color == 0.9
        assert output.scores is None
        assert output.hidden_states is None
