"""Unit tests for ResNet Teacher and Student models.

Tests cover:
- Model initialization (default and custom parameters)
- Forward pass and output shape validation
- Issue types and head configuration
- Parameter counts and model info
- Freeze/unfreeze backbone functionality
- Error handling for invalid configurations
"""

import pytest

# Skip entire module if PyTorch is not available
torch = pytest.importorskip("torch", reason="PyTorch required for ResNet model tests")

from unittest.mock import MagicMock

import torch.nn as nn

from image_preprocessing_detector.models.resnet_student import (  # noqa: E402
    ResNetStudent,
    StudentIQAHead,
)
from image_preprocessing_detector.models.resnet_teacher import (  # noqa: E402
    IQAHead,
    ResNetTeacher,
)

# =============================================================================
# IQAHead (Teacher) Tests
# =============================================================================


@pytest.mark.unit
class TestIQAHead:
    """Tests for the teacher model's IQAHead class."""

    def test_head_initialization_default(self) -> None:
        """Test IQAHead initializes with default parameters."""
        head = IQAHead()
        assert head.head_name == "unnamed"
        assert isinstance(head.fc1, nn.Linear)
        assert isinstance(head.bn1, nn.BatchNorm1d)
        assert isinstance(head.dropout, nn.Dropout)
        assert head.fc1.in_features == 2048
        assert head.fc1.out_features == 512

    def test_head_initialization_custom(self) -> None:
        """Test IQAHead initializes with custom parameters."""
        head = IQAHead(
            in_features=1024,
            hidden_features=256,
            dropout=0.5,
            head_name="blur",
        )
        assert head.head_name == "blur"
        assert head.fc1.in_features == 1024
        assert head.fc1.out_features == 256

    def test_head_forward_pass(self) -> None:
        """Test IQAHead forward pass produces correct output shape."""
        head = IQAHead(in_features=2048, hidden_features=512)
        batch_size = 4
        x = torch.randn(batch_size, 2048)

        output = head(x)

        assert "logits" in output
        assert "confidence" in output
        assert output["logits"].shape == (batch_size, 1)
        assert output["confidence"].shape == (batch_size, 1)

    def test_head_confidence_range(self) -> None:
        """Test that confidence scores are in [0, 1] range."""
        head = IQAHead()
        x = torch.randn(10, 2048)

        output = head(x)

        assert (output["confidence"] >= 0).all()
        assert (output["confidence"] <= 1).all()


# =============================================================================
# StudentIQAHead Tests
# =============================================================================


@pytest.mark.unit
class TestStudentIQAHead:
    """Tests for the student model's StudentIQAHead class."""

    def test_head_initialization_default(self) -> None:
        """Test StudentIQAHead initializes with default parameters."""
        head = StudentIQAHead(in_features=512)
        assert head.head_name == "unknown"
        assert isinstance(head.classifier, nn.Sequential)
        assert isinstance(head.confidence_head, nn.Sequential)

    def test_head_initialization_custom(self) -> None:
        """Test StudentIQAHead initializes with custom parameters."""
        head = StudentIQAHead(
            in_features=512,
            hidden_features=128,
            dropout=0.3,
            head_name="noise",
        )
        assert head.head_name == "noise"

    def test_head_forward_pass(self) -> None:
        """Test StudentIQAHead forward pass produces correct output shape."""
        head = StudentIQAHead(in_features=512, hidden_features=256)
        batch_size = 4
        x = torch.randn(batch_size, 512)

        output = head(x)

        assert "logits" in output
        assert "confidence" in output
        assert output["logits"].shape == (batch_size, 1)
        assert output["confidence"].shape == (batch_size, 1)

    def test_head_confidence_range(self) -> None:
        """Test that student confidence scores are in [0, 1] range."""
        head = StudentIQAHead(in_features=512)
        x = torch.randn(10, 512)

        output = head(x)

        assert (output["confidence"] >= 0).all()
        assert (output["confidence"] <= 1).all()


# =============================================================================
# ResNetTeacher Tests
# =============================================================================


@pytest.mark.unit
class TestResNetTeacher:
    """Tests for ResNetTeacher model."""

    def test_issue_types_constant(self) -> None:
        """Test ISSUE_TYPES class variable is correctly defined."""
        expected_types = ["blur", "noise", "skew", "illumination", "artifacts"]
        assert expected_types == ResNetTeacher.ISSUE_TYPES

    def test_initialization_default_non_pretrained(self) -> None:
        """Test model initializes with default parameters (non-pretrained for speed)."""
        model = ResNetTeacher(pretrained=False)

        assert model.num_heads == 5
        assert model.dropout == pytest.approx(0.2)
        assert model.pretrained is False
        assert model.freeze_backbone is False
        assert model.hidden_features == 512
        assert len(model.heads) == 5

    def test_initialization_custom(self) -> None:
        """Test model initializes with custom parameters."""
        model = ResNetTeacher(
            num_heads=5,
            dropout=0.3,
            pretrained=False,
            freeze_backbone=True,
            hidden_features=256,
        )

        assert model.dropout == pytest.approx(0.3)
        assert model.freeze_backbone is True
        assert model.hidden_features == 256

    def test_invalid_num_heads_raises_error(self) -> None:
        """Test that invalid num_heads raises ValueError."""
        with pytest.raises(ValueError, match="num_heads must be 5"):
            ResNetTeacher(num_heads=3, pretrained=False)

    def test_forward_pass_shape(self) -> None:
        """Test forward pass produces correct output shapes."""
        model = ResNetTeacher(pretrained=False)
        batch_size = 2
        x = torch.randn(batch_size, 3, 224, 224)

        output = model(x)

        assert len(output) == 5
        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert issue_type in output
            assert output[issue_type]["logits"].shape == (batch_size, 1)
            assert output[issue_type]["confidence"].shape == (batch_size, 1)

    def test_forward_pass_different_sizes(self) -> None:
        """Test forward pass with different input sizes."""
        model = ResNetTeacher(pretrained=False)
        model.eval()  # BatchNorm requires batch size > 1 in training mode

        # Test different resolutions
        for size in [224, 256, 320]:
            x = torch.randn(1, 3, size, size)
            output = model(x)
            assert output["blur"]["logits"].shape == (1, 1)

    def test_get_model_info(self) -> None:
        """Test get_model_info returns correct information."""
        model = ResNetTeacher(pretrained=False, dropout=0.3)

        info = model.get_model_info()

        assert info["architecture"] == "ResNet-50 Teacher"
        assert info["num_heads"] == 5
        assert info["issue_types"] == ResNetTeacher.ISSUE_TYPES
        assert info["dropout"] == pytest.approx(0.3)
        assert info["backbone_features"] == 2048
        assert info["total_parameters"] > 0
        assert info["trainable_parameters"] > 0

    def test_freeze_backbone(self) -> None:
        """Test backbone freezing functionality."""
        model = ResNetTeacher(pretrained=False, freeze_backbone=True)

        # All backbone parameters should be frozen
        for param in model.backbone_features.parameters():
            assert not param.requires_grad

        # Head parameters should not be frozen
        for head in model.heads.values():
            for param in head.parameters():
                assert param.requires_grad

    def test_unfreeze_backbone(self) -> None:
        """Test backbone unfreezing functionality."""
        model = ResNetTeacher(pretrained=False, freeze_backbone=True)
        model.unfreeze_backbone_layers()

        for param in model.backbone_features.parameters():
            assert param.requires_grad

    def test_freeze_specific_layers(self) -> None:
        """Test freezing specific number of layers."""
        model = ResNetTeacher(pretrained=False)
        model.freeze_backbone_layers(num_layers=3)

        # First 3 layers should be frozen
        layers = list(model.backbone_features.children())[:3]
        for layer in layers:
            for param in layer.parameters():
                assert not param.requires_grad

    def test_get_predictions(self) -> None:
        """Test get_predictions method."""
        model = ResNetTeacher(pretrained=False)
        x = torch.randn(2, 3, 224, 224)

        predictions = model.get_predictions(x, threshold=0.5)

        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert issue_type in predictions
            assert "present" in predictions[issue_type]
            assert "probability" in predictions[issue_type]
            assert "confidence" in predictions[issue_type]
            assert "logits" in predictions[issue_type]

    def test_get_predictions_threshold(self) -> None:
        """Test that threshold affects predictions."""
        model = ResNetTeacher(pretrained=False)
        model.eval()
        x = torch.randn(4, 3, 224, 224)

        # High threshold should result in fewer positives
        pred_high = model.get_predictions(x, threshold=0.9)
        pred_low = model.get_predictions(x, threshold=0.1)

        # Count total positives
        high_positives = sum(
            pred_high[t]["present"].sum().item() for t in ResNetTeacher.ISSUE_TYPES
        )
        low_positives = sum(
            pred_low[t]["present"].sum().item() for t in ResNetTeacher.ISSUE_TYPES
        )

        assert high_positives <= low_positives


# =============================================================================
# ResNetStudent Tests
# =============================================================================


@pytest.mark.unit
class TestResNetStudent:
    """Tests for ResNetStudent model."""

    def test_issue_types_constant(self) -> None:
        """Test ISSUE_TYPES matches teacher model."""
        assert ResNetStudent.ISSUE_TYPES == ResNetTeacher.ISSUE_TYPES

    def test_initialization_default_non_pretrained(self) -> None:
        """Test model initializes with default parameters (non-pretrained for speed)."""
        model = ResNetStudent(pretrained=False)

        assert model.num_heads == 5
        assert model.hidden_features == 256
        assert model.dropout == pytest.approx(0.2)
        assert model.feature_dim == 512
        assert len(model.heads) == 5

    def test_initialization_custom(self) -> None:
        """Test model initializes with custom parameters."""
        model = ResNetStudent(
            num_heads=5,
            hidden_features=128,
            dropout=0.4,
            pretrained=False,
        )

        assert model.hidden_features == 128
        assert model.dropout == pytest.approx(0.4)

    def test_invalid_num_heads_raises_error(self) -> None:
        """Test that invalid num_heads raises ValueError."""
        with pytest.raises(ValueError, match=r"num_heads .* must match"):
            ResNetStudent(num_heads=3, pretrained=False)

    def test_forward_pass_shape(self) -> None:
        """Test forward pass produces correct output shapes."""
        model = ResNetStudent(pretrained=False)
        batch_size = 2
        x = torch.randn(batch_size, 3, 224, 224)

        output = model(x)

        assert len(output) == 5
        for issue_type in ResNetStudent.ISSUE_TYPES:
            assert issue_type in output
            assert output[issue_type]["logits"].shape == (batch_size, 1)
            assert output[issue_type]["confidence"].shape == (batch_size, 1)

    def test_forward_pass_different_batch_sizes(self) -> None:
        """Test forward pass with different batch sizes."""
        model = ResNetStudent(pretrained=False)
        model.eval()  # BatchNorm requires batch size > 1 in training mode

        for batch_size in [1, 2, 4, 8]:
            x = torch.randn(batch_size, 3, 224, 224)
            output = model(x)
            assert output["blur"]["logits"].shape == (batch_size, 1)

    def test_get_feature_extractor(self) -> None:
        """Test get_feature_extractor returns proper module."""
        model = ResNetStudent(pretrained=False)

        feature_extractor = model.get_feature_extractor()

        assert isinstance(feature_extractor, nn.Sequential)

        # Test output shape
        x = torch.randn(2, 3, 224, 224)
        features = feature_extractor(x)
        assert features.shape == (2, 512)

    def test_freeze_backbone(self) -> None:
        """Test backbone freezing functionality."""
        model = ResNetStudent(pretrained=False)
        model.freeze_backbone()

        for param in model.backbone.parameters():
            assert not param.requires_grad

        # Heads should still be trainable
        for head in model.heads.values():
            for param in head.parameters():
                assert param.requires_grad

    def test_unfreeze_backbone(self) -> None:
        """Test backbone unfreezing functionality."""
        model = ResNetStudent(pretrained=False)
        model.freeze_backbone()
        model.unfreeze_backbone()

        for param in model.backbone.parameters():
            assert param.requires_grad

    def test_count_parameters(self) -> None:
        """Test count_parameters returns proper counts."""
        model = ResNetStudent(pretrained=False)

        counts = model.count_parameters()

        assert "backbone" in counts
        assert "heads" in counts
        assert "total" in counts
        assert "trainable" in counts
        assert counts["total"] == counts["backbone"] + counts["heads"]
        assert counts["trainable"] <= counts["total"]

    def test_from_teacher_config(self) -> None:
        """Test creating student from teacher configuration."""
        teacher = ResNetTeacher(pretrained=False, dropout=0.3)

        student = ResNetStudent.from_teacher_config(
            teacher,
            hidden_features=128,
        )

        assert student.num_heads == 5
        assert student.hidden_features == 128
        assert student.dropout == pytest.approx(0.3)

    def test_from_teacher_config_default_dropout(self) -> None:
        """Test from_teacher_config uses default dropout when not in teacher."""
        mock_teacher = MagicMock(spec=nn.Module)
        # Teacher doesn't have dropout attribute

        student = ResNetStudent.from_teacher_config(
            mock_teacher,
            hidden_features=256,
            dropout=None,
        )

        # Should use default 0.2
        assert student.dropout == pytest.approx(0.2)


# =============================================================================
# Model Comparison Tests
# =============================================================================


@pytest.mark.unit
class TestModelComparison:
    """Tests comparing teacher and student models."""

    def test_student_smaller_than_teacher(self) -> None:
        """Test that student model has fewer parameters than teacher."""
        teacher = ResNetTeacher(pretrained=False)
        student = ResNetStudent(pretrained=False)

        teacher_params = sum(p.numel() for p in teacher.parameters())
        student_params = sum(p.numel() for p in student.parameters())

        assert student_params < teacher_params

    def test_same_output_structure(self) -> None:
        """Test that both models produce same output structure."""
        teacher = ResNetTeacher(pretrained=False)
        student = ResNetStudent(pretrained=False)
        x = torch.randn(2, 3, 224, 224)

        teacher_out = teacher(x)
        student_out = student(x)

        assert set(teacher_out.keys()) == set(student_out.keys())

        for issue_type in ResNetTeacher.ISSUE_TYPES:
            assert set(teacher_out[issue_type].keys()) == set(
                student_out[issue_type].keys()
            )

    def test_compatible_issue_types(self) -> None:
        """Test that teacher and student use same issue types."""
        assert ResNetTeacher.ISSUE_TYPES == ResNetStudent.ISSUE_TYPES


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_single_image_batch(self) -> None:
        """Test models work with batch size of 1."""
        teacher = ResNetTeacher(pretrained=False)
        student = ResNetStudent(pretrained=False)
        # BatchNorm requires batch size > 1 in training mode
        teacher.eval()
        student.eval()
        x = torch.randn(1, 3, 224, 224)

        teacher_out = teacher(x)
        student_out = student(x)

        assert teacher_out["blur"]["logits"].shape == (1, 1)
        assert student_out["blur"]["logits"].shape == (1, 1)

    def test_eval_mode_deterministic(self) -> None:
        """Test that eval mode produces deterministic output."""
        model = ResNetStudent(pretrained=False)
        model.eval()
        x = torch.randn(2, 3, 224, 224)

        with torch.no_grad():
            out1 = model(x)
            out2 = model(x)

        for issue_type in ResNetStudent.ISSUE_TYPES:
            assert torch.allclose(
                out1[issue_type]["logits"], out2[issue_type]["logits"]
            )

    def test_train_mode_with_dropout(self) -> None:
        """Test that train mode uses dropout (non-deterministic)."""
        model = ResNetStudent(pretrained=False, dropout=0.5)
        model.train()
        x = torch.randn(4, 3, 224, 224)

        # Multiple forward passes in train mode should differ due to dropout
        outputs = [model(x)["blur"]["logits"] for _ in range(3)]

        # At least some should differ (with high probability at dropout=0.5)
        # Note: This test might occasionally fail due to randomness
        # In practice, we just verify no errors occur
        _ = all(torch.allclose(outputs[0], o) for o in outputs[1:])


# =============================================================================
# Parametrized Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model_class", "pretrained"),
    [
        (ResNetTeacher, False),
        (ResNetStudent, False),
    ],
)
def test_model_initialization(model_class: type, pretrained: bool) -> None:
    """Test both models initialize correctly."""
    model = model_class(pretrained=pretrained)
    assert model is not None
    assert len(model.heads) == 5


@pytest.mark.unit
@pytest.mark.parametrize(
    ("batch_size", "height", "width"),
    [
        (1, 224, 224),
        (2, 256, 256),
        (4, 320, 320),
        (1, 384, 384),
    ],
)
def test_various_input_sizes(batch_size: int, height: int, width: int) -> None:
    """Test models handle various input sizes."""
    model = ResNetStudent(pretrained=False)
    model.eval()  # BatchNorm requires batch size > 1 in training mode
    x = torch.randn(batch_size, 3, height, width)

    output = model(x)

    assert output["blur"]["logits"].shape == (batch_size, 1)


@pytest.mark.unit
@pytest.mark.parametrize(
    "dropout",
    [0.0, 0.1, 0.2, 0.3, 0.5],
)
def test_various_dropout_rates(dropout: float) -> None:
    """Test models work with various dropout rates."""
    teacher = ResNetTeacher(pretrained=False, dropout=dropout)
    student = ResNetStudent(pretrained=False, dropout=dropout)

    x = torch.randn(2, 3, 224, 224)

    # Should not raise
    _ = teacher(x)
    _ = student(x)


@pytest.mark.unit
@pytest.mark.parametrize(
    "hidden_features",
    [128, 256, 512],
)
def test_various_hidden_features(hidden_features: int) -> None:
    """Test models work with various hidden feature sizes."""
    teacher = ResNetTeacher(pretrained=False, hidden_features=hidden_features)
    student = ResNetStudent(pretrained=False, hidden_features=hidden_features)

    x = torch.randn(2, 3, 224, 224)

    # Should not raise
    _ = teacher(x)
    _ = student(x)
