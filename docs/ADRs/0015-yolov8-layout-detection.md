---
schema_type: common
title: "ADR-015: YOLOv8 for Layout Detection (DEPRECATED)"
description: "Select YOLOv8 over Vision Transformers for document layout detection.
  DEPRECATED: Full layout moved to Project B, only layout-lite in Project A."
tags:
- adr
- layout_detection
- yolo
- object_detection
- deprecated
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to use YOLOv8 for document layout detection in Phase
  3. DEPRECATED 2025-11-15."
---

> **DEPRECATED (2025-11-15)**: Full semantic layout detection moved out of Project A scope.
> **New Approach**: Layout-Lite (Phase 6) - Coarse page-level attributes only (layout_type, has_tables, has_figures, etc.)
> **Full Layout Detection**: Moved to Project B (OCR Orchestration) in RAG Pipeline
> **YOLOv8 Usage**: Repurposed for layout-lite coarse region detection (text_block, table_block, figure_block)
> **Phase Renumbering**: Phase 3 → Phase 6 (Layout-Lite)
> **Reference**: [docs/development/RAG Pipeline/project-a-project-plan.md](../development/RAG Pipeline/project-a-project-plan.md)

---

**Status**: ~~Accepted~~ **DEPRECATED**
**Date**: 2025-01-15
**Deciders**: Byron Williams
**Related**:
- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md)
- [PROJECT_PLAN.md Phase 3](../../PROJECT_PLAN.md#phase-3-ml-for-document-layout-weeks-12-16)
- [ADR-007: Hybrid IQA Approach](0007-hybrid-iqa-approach.md)

## Context

Phase 3 requires document layout detection to identify elements (text, titles, lists, tables, figures, formulas, handwriting) for per-element IQA assessment. We needed to choose between YOLOv8 and Vision Transformers (ViT).

### Requirements

**Performance Targets**:
- Latency: < 50ms per page (GPU)
- mAP@.50: > 0.82 (object detection)
- Elements: Text, Title, List, Table, Figure, Formula, Handwriting (7 classes)

**Integration Needs**:
- COCO bounding box format compatibility
- Element extraction for per-element IQA
- Production deployment (ONNX Runtime)

## Decision

**Use YOLOv8n/s for document layout detection.**

### Model Selection

**YOLOv8-Nano (Primary)**:
- Latency: ~20ms (GPU T4)
- Parameters: 3.2M
- Model Size: ~6MB (FP16)
- mAP: ~0.82 (on DocLayNet validation)

**YOLOv8-Small (Fallback)**:
- Latency: ~30ms (GPU T4)
- Parameters: 11.2M
- Model Size: ~22MB (FP16)
- mAP: ~0.85 (higher accuracy if needed)

### Training Strategy

**Transfer Learning**:
- Pre-trained: COCO dataset (general objects)
- Fine-tuned: DocLayNet (document elements)
- Epochs: 100-150 with early stopping
- Data augmentation: Rotation, brightness, contrast (Albumentations)

**DocLayNet Dataset**:
- Training: 80,863 pages
- Validation: 6,489 pages
- Test: 4,138 pages
- Classes: 11 (we use 7: Text, Title, List, Table, Figure, Formula, Handwriting)

## Consequences

### Positive

1. **Fast Inference**: 20-30ms meets < 50ms latency target
2. **COCO Compatibility**: Direct integration with existing bbox format (ADR-009)
3. **Proven Architecture**: YOLOv8 is production-ready and widely deployed
4. **Small Model Size**: 6-22MB fits deployment constraints
5. **Active Development**: Ultralytics actively maintains YOLOv8
6. **DocLayNet Ready**: Pre-existing fine-tuned models available

### Negative

1. **Lower Accuracy than ViT**: ~82% mAP vs ~87% for larger transformers
2. **Anchor-Based Limitations**: May struggle with very small text elements
3. **Fine-Tuning Required**: COCO pre-training needs DocLayNet adaptation

### Neutral

1. **GPU Required**: Inference requires T4 or better for target latency
2. **ONNX Export**: Standard conversion path available

## Alternatives Considered

### Alternative 1: Vision Transformers (LayoutLMv3, DiT)

**Approach**: Use transformer-based document understanding models

**Advantages**:
- Higher accuracy (~87-90% mAP)
- Better handling of document structure
- State-of-the-art on DocLayNet leaderboard

**Disadvantages**:
- Slower inference (200-700ms)
- Larger models (100-300MB)
- More complex deployment
- Higher GPU memory requirements

**Why Rejected**: Latency exceeds 50ms target by 4-14×

### Alternative 2: Faster R-CNN

**Approach**: Use two-stage object detector

**Advantages**:
- Higher accuracy than YOLO (~85% mAP)
- Better bounding box quality

**Disadvantages**:
- Slower inference (80-150ms)
- More complex architecture
- Harder to optimize

**Why Rejected**: Latency exceeds 50ms target

### Alternative 3: LayoutParser

**Approach**: Use LayoutParser library (built on Detectron2)

**Advantages**:
- Pre-built document layout models
- High accuracy (~85% mAP)
- Easy integration

**Disadvantages**:
- Slower inference (50-100ms)
- Larger dependency footprint
- Based on older Detectron2 architecture

**Why Rejected**: Marginal latency performance, prefer direct YOLOv8 control

## Implementation

### Phase 3 Plan (Weeks 12-16)

**Week 12-13: Model Training**
- Fine-tune YOLOv8n on DocLayNet
- Hyperparameter tuning (learning rate, batch size, augmentation)
- Validation on DocLayNet test set

**Week 14: ONNX Optimization**
- Export to ONNX format
- INT8 quantization (FP32 → INT8 for 1.5-3× speedup)
- Benchmark latency and accuracy trade-offs

**Week 15: Integration**
- Integrate with hybrid IQA pipeline (ADR-007)
- Per-element extraction and quality assessment
- JSON output with element-level metadata

**Week 16: Validation**
- End-to-end testing on DocLayNet
- Performance benchmarking (latency, accuracy, throughput)
- Production deployment preparation

### Integration with Hybrid IQA

```python
def process_text_document(page_image):
    # 1. Layout Detection (YOLOv8)
    layout_results = yolov8_detector.detect(page_image)

    # 2. Extract Elements
    elements = []
    for detection in layout_results:
        element_crop = crop_bbox(page_image, detection.bbox)

        # 3. Per-Element IQA (Hybrid Detector)
        if detection.category in [ElementCategory.IMAGE, ElementCategory.FIGURE]:
            quality_issues = hybrid_iqa_detector.detect(element_crop)
        else:
            quality_issues = []  # Text elements use OCR quality metrics

        elements.append(DocumentElement(
            category=detection.category,
            bbox=detection.bbox,
            confidence=detection.confidence,
            quality_issues=quality_issues
        ))

    return elements
```

## Performance Projections

### YOLOv8-Nano (Primary)

| Metric | Value | Notes |
|--------|-------|-------|
| Latency (GPU T4) | ~20ms | Meets < 50ms target |
| Latency (CPU) | ~200ms | Fallback mode |
| mAP@.50 | 0.82 | Meets > 0.82 target |
| Model Size (FP16) | 6MB | Deployment-friendly |
| Model Size (INT8) | 3MB | Quantized |

### YOLOv8-Small (Fallback)

| Metric | Value | Notes |
|--------|-------|-------|
| Latency (GPU T4) | ~30ms | Still meets target |
| mAP@.50 | 0.85 | Higher accuracy |
| Model Size (FP16) | 22MB | Acceptable |

### Element Detection Coverage (DocLayNet)

| Element | Samples | F1-Score | Notes |
|---------|---------|----------|-------|
| Text | 500k+ | 0.92 | Most common |
| Title | 80k+ | 0.88 | High confidence |
| List | 70k+ | 0.85 | Structured |
| Table | 35k+ | 0.80 | Complex |
| Figure | 30k+ | 0.83 | Images |
| Formula | 15k+ | 0.78 | Challenging |
| Handwriting | 3k+ | 0.70 | Limited data |

## References

- [YOLOv8 Documentation](https://docs.ultralytics.com/models/yolov8/)
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet)
- [ADR-007: Hybrid IQA Approach](0007-hybrid-iqa-approach.md)
- [ADR-009: COCO Bounding Box Format](0009-coco-bounding-box-format.md)
- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md)

## Deployment Strategy

**ONNX Runtime with INT8 Quantization**:
- FP16 → INT8: 1.5-3× speedup
- Accuracy drop: < 2% (acceptable)
- Model size: 6MB → 3MB

**Hardware Requirements**:
- GPU: NVIDIA T4 or better
- VRAM: 4GB minimum
- Driver: CUDA 11.8+
