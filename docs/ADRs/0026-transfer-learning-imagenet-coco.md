---
schema_type: dev
title: "ADR-026: Transfer Learning from ImageNet/COCO"
description: "Use ImageNet pre-training for IQA, COCO pre-training for YOLOv8 layout detection"
tags: [adr, transfer-learning, imagenet, coco, pre-training]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the decision to use pre-trained models for faster convergence and better accuracy"
---

# ADR-026: Transfer Learning from ImageNet/COCO

**Status**: Accepted
**Date**: 2025-01-15
**Deciders**: Byron Williams
**Related**:
- [ADR-025: MobileNetV3 vs EfficientNet](0025-mobilenetv3-vs-efficientnet.md)
- [ADR-015: YOLOv8 for Layout Detection](0015-yolov8-layout-detection.md)

## Context

Training deep learning models from scratch requires large datasets (100k+ images) and long training time (weeks). Transfer learning from pre-trained models reduces training time by 5-10× and improves accuracy by 5-10%.

## Decision

**Use ImageNet pre-training for IQA classifier, COCO pre-training for YOLOv8 layout detector.**

### Transfer Learning Strategy

**IQA Classifier** (MobileNetV3):
- Pre-trained: ImageNet-1K (1.28M images, 1000 classes)
- Fine-tune: All layers with low learning rate
- Freeze: None (full fine-tuning)
- Training time: 2-3 days (vs 10-14 days from scratch)

**Layout Detector** (YOLOv8):
- Pre-trained: COCO dataset (330k images, 80 classes)
- Fine-tune: DocLayNet (81k pages, 11 classes)
- Freeze: Backbone first 10 epochs, then full fine-tuning
- Training time: 3-4 days (vs 14-21 days from scratch)

## Consequences

### Positive

1. **Faster Convergence**: 5-10× faster training
2. **Better Accuracy**: +5-10% mAP vs from-scratch
3. **Data Efficiency**: Requires 50k vs 500k images
4. **Lower Cost**: 2-3 days GPU vs 10-14 days ($100 vs $500)

### Negative

1. **Domain Shift**: ImageNet/COCO differ from documents
2. **Fine-Tuning Required**: Cannot use pre-trained weights directly

## Implementation

**IQA Fine-Tuning**:
```python
model = models.mobilenet_v3_small(weights="IMAGENET1K_V1")
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
# Fine-tune all layers
```

**YOLOv8 Fine-Tuning**:
```bash
yolo train model=yolov8n.pt data=doclaynet.yaml epochs=150 imgsz=640
```

## References

- [ImageNet-1K Dataset](https://www.image-net.org/)
- [COCO Dataset](https://cocodataset.org/)
- [ADR-025: MobileNetV3](0025-mobilenetv3-vs-efficientnet.md)
