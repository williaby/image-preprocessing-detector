# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for HyperIQA++ to improve coverage."""

from __future__ import annotations

import torch

from image_preprocessing_detector.labeling.hyperiqa_plus_plus import (
    HyperIQAPlusPlus,
    MultiTaskIQALoss,
    PCGrad,
    create_soft_labels,
)


def test_end_to_end_inference_cpu() -> None:
    """Test full inference pipeline on CPU."""
    model = HyperIQAPlusPlus(num_bins=10, use_pretrained=False)
    model.eval()

    # Test with small input for speed
    x = torch.randn(2, 3, 224, 224)

    with torch.no_grad():
        outputs = model(x)

    # Validate output structure
    assert "overall" in outputs
    assert "sharpness" in outputs
    assert "color" in outputs

    # Validate score ranges
    for dim in ["overall", "sharpness", "color"]:
        score = outputs[dim]["score"]
        assert score.min() >= 1.0
        assert score.max() <= 5.0


def test_soft_labels_all_mos_values() -> None:
    """Test soft labels for comprehensive MOS range."""
    test_values = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    for mos in test_values:
        labels = create_soft_labels(mos, num_bins=10)

        # All should sum to 1.0
        assert torch.isclose(labels.sum(), torch.tensor(1.0), atol=1e-6)

        # Should have at least one non-zero bin
        assert (labels > 0).sum() >= 1

        # Max value should be reasonable
        assert labels.max() <= 1.0


def test_training_with_pcgrad() -> None:
    """Test training step with PCGrad optimizer."""
    model = HyperIQAPlusPlus(use_pretrained=False)
    model.train()

    base_optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
    optimizer = PCGrad(base_optimizer)

    criterion = MultiTaskIQALoss(use_norm_in_norm=True)

    # Create batch
    batch = {
        "pixel_values": torch.randn(2, 3, 224, 224),
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

    # Forward
    outputs = model(batch["pixel_values"])
    losses = criterion(outputs, batch["targets"], return_per_dim=True)

    # PCGrad step
    optimizer.zero_grad()
    optimizer.pc_backward(losses)
    optimizer.step()

    # Verify gradients were computed
    for param in model.parameters():
        if param.requires_grad:
            assert param.grad is not None


def test_model_freezing_workflow() -> None:
    """Test complete freeze/train/unfreeze workflow."""
    model = HyperIQAPlusPlus(use_pretrained=False, freeze_backbone_epochs=5)

    # Initially should be unfrozen
    assert not model._frozen

    # Freeze backbone
    model.freeze_backbone()
    assert model._frozen
    assert not any(p.requires_grad for p in model.backbone.parameters())

    # Heads should still be trainable
    assert all(p.requires_grad for p in model.head_overall.parameters())
    assert all(p.requires_grad for p in model.head_sharpness.parameters())
    assert all(p.requires_grad for p in model.head_color.parameters())

    # Unfreeze
    model.unfreeze_backbone()
    assert not model._frozen
    assert any(p.requires_grad for p in model.backbone.parameters())


def test_model_with_different_num_bins() -> None:
    """Test model with different number of bins."""
    model = HyperIQAPlusPlus(use_pretrained=False, num_bins=5)
    model.eval()

    x = torch.randn(1, 3, 224, 224)

    with torch.no_grad():
        outputs = model(x)

    assert "overall" in outputs
    assert outputs["overall"]["score"].shape == (1,)
    # Probs (probability distribution) should have 5 bins
    assert outputs["overall"]["probs"].shape == (1, 5)
