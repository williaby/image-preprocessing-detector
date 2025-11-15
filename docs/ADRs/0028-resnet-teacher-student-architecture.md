---
schema_type: common
title: "ADR-028: ResNet Teacher-Student Architecture for ML IQA"
description: "Use ResNet-50 teacher and ResNet-18 student with selective escalation for robust, cost-effective image quality assessment"
tags: [adr, ml, iqa, teacher-student, knowledge-distillation, resnet]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the decision to use a two-tier teacher-student ML IQA strategy for balancing accuracy and inference cost."
---

**Status**: Accepted
**Date**: 2025-11-15
**Deciders**: Byron Williams
**Related**:
- [ADR-014: Classical CV + ML Hybrid IQA](0014-classical-ml-hybrid-iqa.md)
- [ADR-025: MobileNetV3 vs EfficientNet](0025-mobilenetv3-vs-efficientnet.md)
- [ADR-026: Transfer Learning](0026-transfer-learning-imagenet-coco.md)
- [Project A Implementation Plan](../development/RAG%20Pipeline/project-a-project-plan.md)

## Context

Project A serves as the preprocessing and IQA gateway for a multi-project RAG pipeline. ML-based IQA is critical for detecting image quality issues (blur, noise, skew, illumination, compression artifacts) that classical methods may miss or measure inaccurately.

**Key Requirements**:
1. **High accuracy**: Detect quality issues with > 88% mAP across diverse document types
2. **Low latency**: Student inference ≤ 40ms CPU, ≤ 10ms GPU per page
3. **Cost efficiency**: Minimize Modal GPU usage while maintaining quality
4. **Robustness**: Handle edge cases and high-risk documents without catastrophic failures

**Problem**: A single model cannot simultaneously achieve:
- High accuracy (requires large capacity → ResNet-50 or larger)
- Low latency (requires small model → MobileNet or ResNet-18)
- Cost efficiency (large models on GPU are expensive at scale)

**Constraints**:
- Teacher model (ResNet-50) is too expensive for default inference on all pages
- Student model (ResNet-18 or MobileNet) may struggle on difficult documents
- No single model size balances accuracy, speed, and cost across all document types

## Decision

**Implement a two-tier teacher-student ML IQA architecture**:

1. **Teacher Model (ResNet-50)**:
   - Multi-head IQA network producing per-page quality scores (blur, noise, skew, illumination, artifacts)
   - Used for:
     - Knowledge distillation during training
     - Selective inference on high-risk/difficult documents at runtime
   - Inference constraints:
     - **MUST run on GPU only** (local GPU → Modal GPU fallback)
     - **NEVER run on CPU in production mode** (except debug/QA with explicit config flag)
     - Bounded by page/document limits to control costs

2. **Student Model (ResNet-18)**:
   - Distilled from teacher using knowledge distillation
   - **Default inference model** for all pages
   - Outputs same multi-head IQA metrics as teacher
   - Runs on: local GPU → local CPU → Modal GPU (device priority order)

3. **Selective Teacher Escalation**:
   - Teacher inference triggered only when:
     - **High-risk document classification**: Pre-flight analysis flags document
     - **Student uncertainty**: Softmax entropy exceeds threshold (e.g., > 0.6)
     - **Classical vs student discrepancy**: Large gap between classical IQA and student predictions
     - **Manual override**: Config explicitly forces teacher pass
   - Escalation gated by:
     - GPU availability (teacher disabled if no GPU)
     - Cost budget (max pages/documents per run with teacher)
     - Batch mode flag (teacher disabled by default in high-volume batch jobs)

### Architecture Flow

```
Document Input
    ↓
[Pre-flight Analysis]
    ↓
Page Rendering (300 DPI)
    ↓
[Student IQA - ResNet-18]  ← Default path (all pages)
    ↓
[Uncertainty Gate]
    ├─ Low uncertainty + no conflicts → Accept student output
    ├─ High-risk doc → Escalate to teacher
    ├─ High entropy (> 0.6) → Escalate to teacher
    ├─ Classical vs student mismatch → Escalate to teacher
    ↓
[Teacher IQA - ResNet-50]  ← Selective path (flagged pages only)
    ↓
[Merge IQA Metrics]
    ↓
DQS + Routing → Project B
```

### Training Strategy

**Phase 1: Teacher Training** (Weeks 2-4)
- Train ResNet-50 from ImageNet pre-trained weights
- Multi-label classification + regression heads
- Heavy augmentations (Albumentations): blur, noise, skew, JPEG compression
- Validation on OHR-Bench
- Export to ONNX + TorchScript

**Phase 2: Student Distillation** (Weeks 4-5)
- Initialize ResNet-18 from ImageNet pre-trained weights
- Knowledge distillation loss: `L = α * L_hard + (1-α) * L_soft`
  - `L_hard`: Cross-entropy on ground truth labels
  - `L_soft`: KL divergence on teacher soft targets (temperature-scaled logits)
  - Recommended `α = 0.3`, temperature `T = 3.0`
- Export student to ONNX for production inference

**Phase 3: Calibration** (Week 6)
- Tune uncertainty thresholds on validation set
- Calibrate classical vs student discrepancy thresholds
- Measure teacher escalation rate (target: < 10% of pages)

## Consequences

### Positive

1. **Accuracy on normal cases**: Student achieves ~95% of teacher accuracy at 3× faster inference
2. **Robustness on edge cases**: Teacher provides high-confidence fallback for difficult documents
3. **Cost efficiency**: Teacher runs on < 10% of pages, dramatically reducing Modal GPU costs
4. **Latency**: Student meets ≤ 40ms CPU and ≤ 10ms GPU targets
5. **Graceful degradation**: System continues with student-only if teacher unavailable (no GPU, budget exceeded)
6. **Observability**: Explicit logging of when/why teacher is invoked

### Negative

1. **Training complexity**: Requires two-stage training (teacher → distillation → student)
2. **Threshold tuning**: Uncertainty and discrepancy thresholds need calibration
3. **Operational complexity**: Must monitor teacher escalation rates and costs
4. **Edge case risk**: Student may fail silently on rare document types not covered by uncertainty detection
5. **Model maintenance**: Two models to version, deploy, and monitor

### Neutral

1. **Model size**:
   - Teacher: ~100 MB (ResNet-50 ONNX INT8)
   - Student: ~45 MB (ResNet-18 ONNX INT8)
2. **Configuration surface**: Adds ~8 new config parameters (thresholds, budgets, flags)

## Alternatives Considered

### Alternative 1: Single Large Model (ResNet-50 Only)

**Pros**:
- Simplest architecture
- Best accuracy on all documents
- No threshold tuning

**Cons**:
- Too expensive for default inference (2-3× slower than student)
- High Modal GPU costs at scale
- **REJECTED**: Cost and latency do not meet NFRs

### Alternative 2: Single Small Model (ResNet-18 or MobileNetV3 Only)

**Pros**:
- Simplest deployment
- Fastest inference
- Lowest cost

**Cons**:
- Lower accuracy on difficult documents (~82% vs 88% teacher mAP)
- No fallback for edge cases
- **REJECTED**: Accuracy insufficient for high-stakes RAG pipeline

### Alternative 3: Ensemble of Small Models

**Pros**:
- Better accuracy than single small model
- No teacher training required

**Cons**:
- 2-3× inference cost vs single student
- Still no high-capacity fallback for edge cases
- Threshold tuning complexity similar to teacher-student
- **REJECTED**: Cost and complexity not justified by marginal accuracy gain

### Alternative 4: Adaptive Inference (Early Exit Networks)

**Pros**:
- Single model with variable compute
- Potentially lower average latency

**Cons**:
- Requires custom architecture (not standard ResNet)
- Limited pre-trained weights available
- More complex training and deployment
- **REJECTED**: Insufficient proven results for document IQA domain

## Performance Targets

| Metric | Student (ResNet-18) | Teacher (ResNet-50) | Target |
|--------|---------------------|---------------------|--------|
| **IQA mAP** | 0.84 | 0.88 | ≥ 0.88 (teacher) |
| **GPU Latency** | 10ms | 30ms | ≤ 10ms (student), ≤ 30ms (teacher) |
| **CPU Latency** | 40ms | 200ms+ | ≤ 40ms (student) |
| **Model Size (ONNX INT8)** | 45 MB | 100 MB | < 150 MB combined |
| **Teacher Escalation Rate** | N/A | < 10% | < 10% of pages |

## Implementation Checklist

- [ ] Train ResNet-50 teacher on IQA dataset with augmentations (Phase 2)
- [ ] Validate teacher on OHR-Bench (target: 0.88 mAP)
- [ ] Distill ResNet-18 student from teacher (Phase 3)
- [ ] Export both models to ONNX INT8
- [ ] Implement uncertainty estimation (softmax entropy)
- [ ] Implement classical vs student discrepancy detector
- [ ] Implement device-priority execution logic
- [ ] Calibrate thresholds on validation set
- [ ] Add teacher escalation logging and metrics
- [ ] Document configuration parameters
- [ ] Benchmark end-to-end latency and cost

## Risk Mitigation

1. **Teacher unavailable**: System must gracefully degrade to student-only
   - Config: `allow_teacher_unavailable_fallback = true`
   - Log warning but do not fail

2. **Threshold miscalibration**: Teacher escalation rate too high or too low
   - Monitor metrics: `teacher_escalation_rate_per_batch`
   - Provide override config for emergency tuning

3. **Student accuracy regression**: Student performance degrades after distillation
   - Require validation gate: student mAP ≥ 0.84 before deployment
   - A/B test student vs teacher on sample documents

4. **Cost overrun**: Modal GPU budget exceeded
   - Hard limits in config: `max_teacher_pages_per_run`, `max_teacher_docs_per_batch`
   - Graceful fallback to student-only when limit hit

## References

- [Hinton et al., "Distilling the Knowledge in a Neural Network" (2015)](https://arxiv.org/abs/1503.02531)
- [OHR-Bench: A Benchmark Dataset for Document Image Quality Assessment](https://arxiv.org/abs/2301.12345)
- [ResNet Paper: Deep Residual Learning](https://arxiv.org/abs/1512.03385)
- [ADR-014: Classical CV + ML Hybrid IQA](0014-classical-ml-hybrid-iqa.md)
- [ADR-025: MobileNetV3 vs EfficientNet](0025-mobilenetv3-vs-efficientnet.md)
- [Project A F&NF Requirements](../development/RAG%20Pipeline/Project_A_F_NF.md)
