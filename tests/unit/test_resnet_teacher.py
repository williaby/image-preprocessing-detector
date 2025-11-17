"""Unit tests for ResNet-50 Teacher Model.

Tests cover:
- Model initialization with different configurations
- Forward pass with various batch sizes
- Output shape validation
- Multi-head architecture
- Pretrained weight loading
- Backbone freezing/unfreezing
- Prediction methods
"""

import pytest
import torch

from image_preprocessing_detector.models import IQAHead, ResNetTeacher


class TestIQAHead:
    """Test individual IQA head."""

    def test_head_initialization(self) -> None:
        """Test head initialization with default parameters."""
        head = IQAHead(in_features=2048, hidden_features=512, dropout=0.2)
        assert head.fc1.in_features == 2048
        assert head.fc1.out_features == 512
        assert head.fc2.in_features == 512
        assert head.fc2.out_features == 2  # Binary classification + confidence

    def test_head_forward_pass(self) -> None:
        """Test forward pass through a single head."""
        head = IQAHead(in_features=2048, hidden_features=512)
        batch_size = 8
        input_tensor = torch.randn(batch_size, 2048)

        output = head(input_tensor)

        # Check output structure
        assert "logits" in output
        assert "confidence" in output

        # Check shapes
        assert output["logits"].shape == (batch_size, 1)
        assert output["confidence"].shape == (batch_size, 1)

        # Check confidence is in [0, 1] range
        assert torch.all(output["confidence"] >= 0.0)
        assert torch.all(output["confidence"] <= 1.0)

    def test_head_different_batch_sizes(self) -> None:
        """Test head with different batch sizes."""
        head = IQAHead(in_features=2048)
        head.eval()  # BatchNorm requires eval mode for batch_size=1

        for batch_size in [1, 4, 16, 32]:
            input_tensor = torch.randn(batch_size, 2048)
            output = head(input_tensor)

            assert output["logits"].shape == (batch_size, 1)
            assert output["confidence"].shape == (batch_size, 1)


class TestResNetTeacher:
    """Test ResNet-50 Teacher Model."""

    def test_model_initialization_pretrained(self) -> None:
        """Test model initialization with pretrained weights."""
        model = ResNetTeacher(num_heads=5, dropout=0.2, pretrained=True)

        assert model.num_heads == 5
        assert model.dropout == 0.2
        assert model.pretrained is True
        assert len(model.heads) == 5

        # Check all issue types are present
        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert issue_type in model.heads

    def test_model_initialization_no_pretrained(self) -> None:
        """Test model initialization without pretrained weights."""
        model = ResNetTeacher(num_heads=5, pretrained=False)

        assert model.pretrained is False
        assert len(model.heads) == 5

    def test_invalid_num_heads(self) -> None:
        """Test that invalid number of heads raises error."""
        with pytest.raises(ValueError, match="num_heads must be"):
            ResNetTeacher(num_heads=3)  # Should be 5

    def test_forward_pass_shape(self) -> None:
        """Test forward pass output shapes."""
        model = ResNetTeacher(num_heads=5, pretrained=False)
        batch_size = 4
        # RGB images, 224x224
        images = torch.randn(batch_size, 3, 224, 224)

        outputs = model(images)

        # Check all heads present in output
        assert len(outputs) == 5
        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert issue_type in outputs

            # Check each head output structure
            head_output = outputs[issue_type]
            assert "logits" in head_output
            assert "confidence" in head_output

            # Check shapes
            assert head_output["logits"].shape == (batch_size, 1)
            assert head_output["confidence"].shape == (batch_size, 1)

            # Check confidence range
            assert torch.all(head_output["confidence"] >= 0.0)
            assert torch.all(head_output["confidence"] <= 1.0)

    def test_forward_pass_different_batch_sizes(self) -> None:
        """Test forward pass with different batch sizes."""
        model = ResNetTeacher(num_heads=5, pretrained=False)
        model.eval()  # BatchNorm requires eval mode for batch_size=1

        for batch_size in [1, 2, 8, 16]:
            images = torch.randn(batch_size, 3, 224, 224)
            outputs = model(images)

            for issue_type in ResNetTeacher.ISSUE_TYPES:
                assert outputs[issue_type]["logits"].shape == (batch_size, 1)
                assert outputs[issue_type]["confidence"].shape == (batch_size, 1)

    def test_get_model_info(self) -> None:
        """Test model info retrieval."""
        model = ResNetTeacher(num_heads=5, dropout=0.3, pretrained=False)
        info = model.get_model_info()

        assert info["architecture"] == "ResNet-50 Teacher"
        assert info["num_heads"] == 5
        assert info["dropout"] == 0.3
        assert info["pretrained"] is False
        assert info["backbone_features"] == 2048
        assert "total_parameters" in info
        assert "trainable_parameters" in info
        assert info["total_parameters"] > 0

    def test_freeze_backbone(self) -> None:
        """Test freezing backbone layers."""
        model = ResNetTeacher(num_heads=5, freeze_backbone=True)

        # Check that backbone parameters are frozen
        for param in model.backbone_features.parameters():
            assert param.requires_grad is False

        # Check that head parameters are still trainable
        for head in model.heads.values():
            for param in head.parameters():
                assert param.requires_grad is True

    def test_unfreeze_backbone(self) -> None:
        """Test unfreezing backbone layers."""
        model = ResNetTeacher(num_heads=5, freeze_backbone=True)

        # Initially frozen
        for param in model.backbone_features.parameters():
            assert param.requires_grad is False

        # Unfreeze
        model.unfreeze_backbone_layers()

        # Now unfrozen
        for param in model.backbone_features.parameters():
            assert param.requires_grad is True

    def test_freeze_specific_layers(self) -> None:
        """Test freezing specific number of backbone layers."""
        model = ResNetTeacher(num_heads=5, freeze_backbone=False)

        # Freeze first 2 layers
        model.freeze_backbone_layers(num_layers=2)

        layers = list(model.backbone_features.children())

        # First 2 layers should be frozen
        for layer in layers[:2]:
            for param in layer.parameters():
                assert param.requires_grad is False

        # Remaining layers should be trainable (if they have parameters)
        for layer in layers[2:]:
            if list(layer.parameters()):  # Only check if layer has parameters
                has_trainable = any(p.requires_grad for p in layer.parameters())
                # At least some parameters should be trainable
                assert has_trainable

    def test_get_predictions(self) -> None:
        """Test prediction method with threshold."""
        model = ResNetTeacher(num_heads=5, pretrained=False)
        batch_size = 4
        images = torch.randn(batch_size, 3, 224, 224)

        predictions = model.get_predictions(images, threshold=0.5)

        # Check structure
        assert len(predictions) == 5
        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert issue_type in predictions

            pred = predictions[issue_type]
            assert "present" in pred
            assert "probability" in pred
            assert "confidence" in pred
            assert "logits" in pred

            # Check shapes
            assert pred["present"].shape == (batch_size, 1)
            assert pred["probability"].shape == (batch_size, 1)
            assert pred["confidence"].shape == (batch_size, 1)
            assert pred["logits"].shape == (batch_size, 1)

            # Check types
            assert pred["present"].dtype == torch.bool
            assert torch.all(pred["probability"] >= 0.0)
            assert torch.all(pred["probability"] <= 1.0)

    def test_model_eval_mode(self) -> None:
        """Test model in evaluation mode."""
        model = ResNetTeacher(num_heads=5, pretrained=False)
        model.eval()

        batch_size = 4
        images = torch.randn(batch_size, 3, 224, 224)

        with torch.no_grad():
            outputs = model(images)

        # Should still produce valid outputs
        assert len(outputs) == 5
        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert outputs[issue_type]["logits"].shape == (batch_size, 1)

    def test_model_train_mode(self) -> None:
        """Test model in training mode."""
        model = ResNetTeacher(num_heads=5, pretrained=False)
        model.train()

        batch_size = 4
        images = torch.randn(batch_size, 3, 224, 224)

        outputs = model(images)

        # Should produce valid outputs
        assert len(outputs) == 5

        # Gradients should be tracked
        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert outputs[issue_type]["logits"].requires_grad

    def test_different_image_sizes(self) -> None:
        """Test model with different input image sizes."""
        model = ResNetTeacher(num_heads=5, pretrained=False)

        # ResNet can handle different input sizes
        for size in [224, 256, 320]:
            images = torch.randn(2, 3, size, size)
            outputs = model(images)

            # Should still produce valid outputs
            assert len(outputs) == 5
            for issue_type in ResNetTeacher.ISSUE_TYPES:
                assert outputs[issue_type]["logits"].shape == (2, 1)

    def test_custom_hidden_features(self) -> None:
        """Test model with custom hidden layer size."""
        model = ResNetTeacher(num_heads=5, hidden_features=256, pretrained=False)

        # Check head configuration
        for head in model.heads.values():
            assert head.fc1.out_features == 256
            assert head.fc2.in_features == 256

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_model_on_cuda(self) -> None:
        """Test model on CUDA device."""
        model = ResNetTeacher(num_heads=5, pretrained=False)
        model = model.cuda()

        batch_size = 4
        images = torch.randn(batch_size, 3, 224, 224).cuda()

        outputs = model(images)

        # Check outputs are on CUDA
        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert outputs[issue_type]["logits"].is_cuda
            assert outputs[issue_type]["confidence"].is_cuda

    def test_model_parameters_count(self) -> None:
        """Test that model has expected number of parameters."""
        model = ResNetTeacher(num_heads=5, pretrained=False)
        info = model.get_model_info()

        # ResNet-50 has ~25M parameters + our heads
        # Should be > 25M
        assert info["total_parameters"] > 25_000_000

        # When not frozen, all should be trainable
        assert info["trainable_parameters"] == info["total_parameters"]

    def test_model_with_frozen_backbone_parameters_count(self) -> None:
        """Test parameter count with frozen backbone."""
        model = ResNetTeacher(num_heads=5, freeze_backbone=True)
        info = model.get_model_info()

        # Trainable should be much less than total (only heads)
        assert info["trainable_parameters"] < info["total_parameters"]

        # Trainable should be small (only 5 heads)
        # Each head has ~1M parameters, so ~5M total for heads
        assert info["trainable_parameters"] < 10_000_000
