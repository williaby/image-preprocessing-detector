---
schema_type: dev
title: "ADR-025: MobileNetV3 vs EfficientNet for IQA Model Selection"
description: "Select MobileNetV3-Small over EfficientNet-Lite0 for IQA multi-label classification"
tags: [adr, mobilenetv3, efficientnet, iqa, model-selection]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the model architecture selection for Phase 2 IQA classifier"
---

# ADR-025: MobileNetV3 vs EfficientNet for IQA Model Selection

**Status**: Accepted
**Date**: 2025-01-15
**Deciders**: Byron Williams
**Related**:
- [ADR-014: Classical CV + ML Hybrid for IQA](0014-classical-ml-hybrid-iqa.md)
- [PROJECT_PLAN.md Phase 2](../../PROJECT_PLAN.md#phase-2-ml-for-image-quality-assessment-3-4-weeks)

## Context

Phase 2 requires a lightweight CNN for multi-label IQA classification (noise, blur, perspective, orientation). Model must balance accuracy, latency, and model size.

**Requirements**:
- Latency: < 50ms (GPU), < 200ms (CPU)
- Model size: < 10MB (quantized)
- mAP: > 0.88
- Multi-label output: 6 quality issues

## Decision

**Use MobileNetV3-Small as primary model, EfficientNet-Lite0 as fallback.**

### Model Comparison

| Model | Params | Size (FP32) | Size (INT8) | GPU Latency | CPU Latency | mAP (Est.) |
|-------|--------|-------------|-------------|-------------|-------------|------------|
| **MobileNetV3-Small** | **2.9M** | **11MB** | **3MB** | **~30ms** | **~150ms** | **0.88** |
| EfficientNet-Lite0 | 4.7M | 18MB | 5MB | ~50ms | ~250ms | 0.90 |
| MobileNetV2 | 3.5M | 14MB | 4MB | ~35ms | ~180ms | 0.86 |
| ResNet18 | 11.7M | 46MB | 12MB | ~45ms | ~300ms | 0.89 |

**MobileNetV3-Small wins**: Best latency, smallest size, meets mAP target.

## Consequences

### Positive

1. **Fast Inference**: 30ms GPU meets < 50ms target
2. **Small Model**: 3MB quantized fits deployment constraints
3. **Efficient Training**: 2.9M params = faster training (2-3 days vs 5-7 days)
4. **Mobile-Ready**: Designed for mobile deployment
5. **Active Development**: TorchVision actively maintains MobileNet

### Negative

1. **Lower Accuracy**: 0.88 mAP vs 0.90 for EfficientNet
2. **ImageNet Bias**: Pre-trained on natural images, not documents

### Neutral

1. **Transfer Learning**: ImageNet weights require domain adaptation

## Alternatives Considered

**EfficientNet-Lite0**: Higher accuracy but slower (rejected for latency)
**MobileNetV2**: Older architecture, lower accuracy (rejected)
**ResNet18**: Larger model, slower (rejected for size)

## Implementation

```python
import torchvision.models as models

# Load MobileNetV3-Small with ImageNet weights
model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")

# Replace classifier for multi-label IQA
model.classifier[-1] = nn.Linear(1024, 6)  # 6 quality issues

# Training
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
criterion = nn.BCEWithLogitsLoss()  # Multi-label
```

## References

- [MobileNetV3 Paper](https://arxiv.org/abs/1905.02244)
- [ADR-014: Hybrid IQA](0014-classical-ml-hybrid-iqa.md)
- [ADR-026: Transfer Learning](0026-transfer-learning-imagenet-coco.md)
