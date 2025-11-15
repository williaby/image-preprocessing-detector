---
schema_type: common
title: "ADR-011: Hybrid Validation Strategy for Threshold Calibration"
description: "Combined synthetic and real-world validation for production-ready detector
  thresholds"
tags:
- adr
- validation
- testing
- quality_assurance
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to use both synthetic and real-world validation datasets
  for detector threshold calibration."
---


**Status**: Accepted
**Date**: 2025-11-05 (Updated: 2025-01-13 for DGQA)
**Deciders**: Byron Williams
**Related**:
- [ADR-006: Synthetic Validation Dataset Strategy](0006-synthetic-validation-dataset-strategy.md)
- [ADR-029: Three-Tier Dataset Strategy](0029-phase2-dataset-selection-strategy.md)
- [FR-2.3: Learned Quality Assessment](../requirements/functional_requirements_v2.md#fr-23-learned-quality-assessment-phase-2)
- [Phase 1 Validation: Stage 3A/3B Coverage Update](../project/phases/phase-1-validation/STAGE_3A_3B_COVERAGE_UPDATE.md)
- [Phase 1 Completion Summary](../../PHASE_1_COMPLETE.md)

## Context

During Phase 1 validation, we discovered a critical issue with detector threshold calibration:

1. **Initial Approach**: Calibrated thresholds using synthetic data from Microsoft Genalog
2. **Problem Discovered**: Real-world PDFs have systematically lower contrast than synthetic images due to:
   - Scanning artifacts
   - PDF compression and optimization
   - Paper texture
   - Printing imperfections
3. **Impact**: Original thresholds would have caused 100% false positive rate for contrast detection on real-world documents

### Validation Coverage

**Datasets**:
- **Synthetic**: 228 images from Microsoft Genalog (perfect ground truth)
- **Real-World**: 100 PDFs from DocLayNet benchmark (production documents)
- **Total**: 328 images for comprehensive validation

### Critical Discovery

Real-world validation caught contrast threshold miscalibration:
- **Synthetic calibration**: 0.18 threshold worked well
- **Real-world detection**: 100% of documents flagged (incorrect)
- **Adjusted threshold**: Reduced detection rate to 53% (appropriate)

**Quote from validation report**:
> "Real-world PDFs have systematically lower contrast than synthetic images due to: Scanning artifacts, Compression (PDF optimization), Paper texture, Printing imperfections"

## Decision

**Use hybrid validation strategy combining synthetic and real-world datasets for detector threshold calibration.**

### Validation Workflow

1. **Synthetic Dataset (Genalog)**:
   - Purpose: Ground truth generation and initial threshold tuning
   - Samples: 228 images with known quality issues
   - Advantage: Perfect ground truth for precision/recall metrics

2. **Real-World Dataset (DocLayNet)**:
   - Purpose: Threshold calibration and production readiness
   - Samples: 100 PDFs from business documents
   - Advantage: Captures real-world artifacts and edge cases

3. **Calibration Process**:
   - Train on synthetic data (perfect labels)
   - Calibrate thresholds on real-world data (production distribution)
   - Validate final thresholds on both datasets

### Validation Status (Stage 3A)

| Detector | Synthetic | Real-World | Status |
|----------|-----------|------------|--------|
| Blur | ✅ Validated (228 images) | ✅ Validated (100 PDFs) | ✅ Complete |
| Contrast | ✅ Validated (228 images) | ✅ Calibrated (100 PDFs) | ✅ Complete |
| Skew | ✅ Validated (228 images) | ✅ Validated (100 PDFs) | ✅ Complete |

**Detection Rates (Real-World)**:
- Blur: 6% (appropriate for business documents)
- Skew: 4% (appropriate for scanned documents)
- Contrast: 53% (calibrated from 100% false positive rate)

## Consequences

### Positive

1. **Production Readiness**: Real-world validation prevents false positive disasters before deployment
2. **Ground Truth Accuracy**: Synthetic data provides perfect labels for initial training
3. **Calibration Quality**: Dual validation catches distribution shift between synthetic and real-world
4. **Risk Mitigation**: Prevents deploying detectors that work on synthetic but fail on production data
5. **Continuous Improvement**: Framework supports ongoing calibration as new datasets emerge

### Negative

1. **Additional Work**: Requires maintaining both synthetic and real-world validation pipelines
2. **Dataset Costs**: Real-world validation requires manual quality assessment for some edge cases
3. **Complexity**: Two-stage validation (synthetic → calibration) vs single-stage approach
4. **Time Investment**: ~40 hours for initial hybrid validation vs ~20 hours for synthetic-only

### Neutral

1. **Dataset Balance**: 228 synthetic + 100 real-world = 328 total (sufficient for Phase 1)
2. **Validation Coverage**: 100% of implemented detectors validated on both datasets
3. **Future Work**: Phase 2 ML models will benefit from existing hybrid validation infrastructure

## Alternatives Considered

### Alternative 1: Synthetic-Only Validation

**Approach**: Use only Microsoft Genalog synthetic data for validation

**Advantages**:
- Perfect ground truth
- Faster validation (no manual annotation)
- Easier to scale (generate more samples)

**Disadvantages**:
- Missed distribution shift (contrast miscalibration)
- No production readiness guarantee
- High risk of false positives on real-world documents

**Why Rejected**: Would have deployed detectors with 100% false positive rate for contrast

### Alternative 2: Real-World-Only Validation

**Approach**: Use only DocLayNet PDFs for validation

**Advantages**:
- Direct production validation
- Captures all real-world artifacts
- Single validation pipeline

**Disadvantages**:
- No perfect ground truth
- Manual annotation required (expensive)
- Harder to generate edge cases

**Why Rejected**: Lacks perfect ground truth for precision/recall metrics

### Alternative 3: Sequential Dataset Strategy

**Approach**: Start with synthetic, migrate to real-world later

**Advantages**:
- Gradual complexity increase
- Can defer real-world work

**Disadvantages**:
- Delays discovery of calibration issues
- Risk of shipping miscalibrated detectors
- Re-work required when migration happens

**Why Rejected**: Discovered calibration issue late would have caused production incidents

## Implementation

### Validation Pipeline

```python
# Stage 1: Synthetic validation (ground truth)
synthetic_results = validate_detector(
    detector=blur_detector,
    dataset=genalog_synthetic,
    ground_truth=perfect_labels,
    metrics=["precision", "recall", "f1"]
)

# Stage 2: Real-world calibration (production distribution)
real_world_results = validate_detector(
    detector=blur_detector,
    dataset=doclaynet_pdfs,
    ground_truth=manual_annotations,
    calibrate_thresholds=True
)

# Stage 3: Cross-validation (both datasets)
final_validation = {
    "synthetic": validate_detector(blur_detector, genalog_synthetic),
    "real_world": validate_detector(blur_detector, doclaynet_pdfs)
}
```

### Threshold Calibration Example (Contrast)

**Original Threshold (Synthetic)**:
- Threshold: 0.18 (RMS contrast)
- Synthetic detection rate: 25% (appropriate)
- Real-world detection rate: 100% (miscalibrated)

**Calibrated Threshold (Real-World)**:
- Threshold: 0.15 (adjusted based on real-world distribution)
- Synthetic detection rate: 30% (slightly higher, acceptable)
- Real-world detection rate: 53% (appropriate)

### Validation Results

**Stage 3A (IQA) - 100% Validated**:
- 3/3 implemented detectors (blur, skew, contrast) validated on both datasets
- All thresholds calibrated for production readiness
- Detection rates established for real-world documents

**Stage 3B (Element Detection) - 67% Ready for Phase 2**:
- 4/6 elements available in DocLayNet COCO annotations
- Text, Title, List, Figure/Table supported
- Handwriting and Formulas deferred to Phase 2+

## References

- [Synthetic Validation Dataset Strategy (ADR-006)](0006-synthetic-validation-dataset-strategy.md)
- [Phase 1 Validation: Stage 3A/3B Coverage Update](../project/phases/phase-1-validation/STAGE_3A_3B_COVERAGE_UPDATE.md)
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet)
- [Microsoft Genalog](https://github.com/microsoft/genalog)
- [Phase 1 Completion Summary](../../PHASE_1_COMPLETE.md)

## Lessons Learned (Phase 1)

1. **Distribution Shift is Real**: Synthetic and real-world data have different quality distributions
2. **Calibrate on Target Distribution**: Always calibrate thresholds on production-like data
3. **Ground Truth + Real-World**: Best of both worlds - perfect labels for training, real artifacts for calibration
4. **Catch Issues Early**: Hybrid validation caught critical miscalibration before production deployment
5. **Validation Framework**: Investment in hybrid validation infrastructure pays off for all future detectors

---

## Phase 2+ Extension: Domain-Generalized Quality Assessment (DGQA)

**Update Date**: 2025-01-13
**Context**: Phase 1 hybrid validation proved critical for classical detectors. Phase 2+ introduces **learned (ML-based) quality assessment** (FR-2.3) which faces the same synthetic-to-real domain gap, but at a deeper level requiring specialized calibration methodology.

### Problem: Synthetic-to-Real Domain Gap for Learned Models

**Phase 1 Finding**: Real-world PDFs differ from synthetic images (contrast miscalibration: 100% false positive rate without calibration)

**Phase 2+ Challenge**: ML models trained on synthetic data face **domain generalization** problem:
- **Training**: 50k synthetic samples from TableBank with weak supervision (BRISQUE/NIQE labels)
- **Target**: Real-world documents with scanning artifacts, compression, paper texture
- **Risk**: Models overfit to synthetic distribution → poor performance on production documents

**Evidence from Research** (Q4 2024 - Q4 2025 Literature):
- DGQA framework (Domain-Generalized Quality Assessment) specifically designed to address synthetic-to-real gap for document IQA
- Standard approach (train on synthetic, test on real) shows **15-25% performance degradation**
- DGQA calibration reduces degradation to **<5%** through domain adaptation techniques

### Decision: Adopt DGQA Framework for Phase 2 Learned Quality Assessment

**DGQA Framework Components:**

1. **Multi-Domain Training** (Prevent Overfitting to Synthetic)
2. **Domain-Invariant Feature Learning** (Extract Features Common to Both Domains)
3. **Adversarial Domain Adaptation** (Align Synthetic and Real Feature Distributions)
4. **Calibration on Real-World Holdout** (Fine-Tune on Small Real-World Sample)

### DGQA Calibration Methodology

#### Stage 1: Synthetic Training (Weeks 1-2)

**Dataset**: 50k synthetic samples from TableBank + Albumentations augmentation
**Weak Supervision**: BRISQUE/NIQE labels as pseudo-ground-truth
**Augmentation Pipeline**:
- Blur: Gaussian blur (σ=0.5-3.0), motion blur (5-15 pixels)
- Noise: Gaussian noise (σ=5-25), salt-and-pepper noise (density=0.01-0.05)
- Contrast: Random brightness/contrast adjustment (±30%)
- Compression: JPEG compression (quality=50-95)

**Model Architecture** (FR-2.3):
- **Backbone**: MobileNetV3-Small or EfficientNet-B0
- **Output**: 3-dimension scores (overall, sharpness, color fidelity)
- **Loss**: Multi-task loss (MSE for each dimension + ranking loss)

```python
# Synthetic training phase
model = MobileNetV3QualityAssessment(
    num_outputs=3,  # overall, sharpness, color_fidelity
    pretrained=True  # ImageNet initialization
)

# Weak supervision labels from BRISQUE/NIQE
synthetic_labels = {
    "overall": brisque_score_normalized,
    "sharpness": laplacian_variance_normalized,
    "color_fidelity": contrast_rms_normalized
}

# Train on 50k synthetic samples
for epoch in range(50):
    for batch in synthetic_dataloader:
        # Standard supervised learning
        predictions = model(batch.images)
        loss = multi_task_loss(predictions, synthetic_labels)
        loss.backward()
```

**Expected Result**: Model learns quality patterns but overfits to synthetic distribution

#### Stage 2: Domain-Invariant Feature Learning (Week 3)

**Approach**: Train feature extractor to produce similar features for synthetic and real samples with same quality

**Technique**: Adversarial domain adaptation with gradient reversal layer
- **Domain Discriminator**: Classifier that tries to distinguish synthetic vs. real features
- **Gradient Reversal**: Feature extractor learns features that fool the discriminator
- **Result**: Features invariant to domain (synthetic vs. real) but discriminative for quality

```python
# Domain-invariant feature learning
class DomainInvariantQA(nn.Module):
    def __init__(self):
        self.feature_extractor = MobileNetV3Features()
        self.quality_head = QualityRegressionHead(num_outputs=3)
        self.domain_discriminator = DomainClassifier()  # Synthetic vs. Real

    def forward(self, x, domain_label, alpha):
        # Extract features
        features = self.feature_extractor(x)

        # Quality prediction (main task)
        quality_scores = self.quality_head(features)

        # Domain classification with gradient reversal
        reversed_features = GradientReversalLayer(alpha)(features)
        domain_prediction = self.domain_discriminator(reversed_features)

        return quality_scores, domain_prediction

# Training loop (adversarial domain adaptation)
for epoch in range(20):
    for batch_synthetic, batch_real in zip(synthetic_loader, real_loader):
        # Synthetic batch: quality supervision + domain label
        quality_pred_syn, domain_pred_syn = model(
            batch_synthetic.images,
            domain_label=0,  # Synthetic
            alpha=epoch / 20.0  # Gradually increase reversal strength
        )

        # Real batch: no quality labels, only domain label
        _, domain_pred_real = model(
            batch_real.images,
            domain_label=1,  # Real
            alpha=epoch / 20.0
        )

        # Multi-objective loss
        loss_quality = mse_loss(quality_pred_syn, batch_synthetic.labels)
        loss_domain = bce_loss(domain_pred_syn, 0) + bce_loss(domain_pred_real, 1)
        loss_total = loss_quality + lambda_domain * loss_domain

        loss_total.backward()
```

**Expected Result**: Features capture quality (not domain-specific artifacts)

#### Stage 3: Real-World Calibration (Week 4)

**Dataset**: Small real-world holdout set (500-1000 samples) with manual quality annotations
- **Source**: DocLayNet PDFs (100 samples from Phase 1) + new annotated samples (400-900)
- **Annotation**: Manual 3-dimension quality scores (overall, sharpness, color fidelity)
- **Cost**: ~20 hours annotation effort (5-10 annotators, 2-3 hours each)

**Calibration Approach**: Fine-tune on real-world samples with domain-invariant features frozen

```python
# Freeze feature extractor (domain-invariant features)
for param in model.feature_extractor.parameters():
    param.requires_grad = False

# Fine-tune quality head only on real-world data
for epoch in range(10):
    for batch in real_world_calibration_loader:
        # Use real-world manual annotations (ground truth)
        quality_pred = model.quality_head(
            model.feature_extractor(batch.images)
        )
        loss = mse_loss(quality_pred, batch.manual_annotations)
        loss.backward()  # Only updates quality_head parameters
```

**Expected Result**: Model calibrated to real-world distribution while preserving domain-invariant features

#### Stage 4: Validation (Week 4)

**Validation Datasets:**
1. **Synthetic Test Set** (10k samples): Ensure no performance degradation on synthetic
2. **Real-World Test Set** (200 samples): Validate production readiness
3. **DIQA-5000** (when released): Document-specific IQA benchmark with ground-truth 3-dimension scores

**Metrics** (FR-2.3 Targets):
- **Phase 2**: Pearson/Spearman correlation > 0.75 with LIVE/CSIQ ground-truth scores
- **Phase 3**: Pearson/Spearman correlation > 0.80 with DIQA-5000 ground-truth scores

**Validation Results Expected:**
```python
# Synthetic test set (should maintain performance)
synthetic_correlation = evaluate_correlation(
    model, synthetic_test_set, ground_truth=weak_labels
)
assert synthetic_correlation > 0.75  # No degradation

# Real-world test set (should generalize)
real_world_correlation = evaluate_correlation(
    model, real_world_test_set, ground_truth=manual_annotations
)
assert real_world_correlation > 0.75  # FR-2.3 target

# Performance gap (should be <5% with DGQA)
domain_gap = abs(synthetic_correlation - real_world_correlation)
assert domain_gap < 0.05  # DGQA success criterion
```

### Implementation Timeline (Phase 2 Extension)

**Original Phase 2 Timeline**: 4 weeks (Weeks 8-11)

**DGQA Extension**: +1 week (Weeks 8-12)

**Breakdown:**
- **Week 1-2**: Synthetic training with weak supervision (already planned)
- **Week 3**: Domain-invariant feature learning with adversarial adaptation (**NEW**)
- **Week 4**: Real-world calibration + validation (**EXTENDED**)

**Total Phase 2 Duration**: 5 weeks (previously 4 weeks)

**Justification**: DGQA calibration critical to prevent 15-25% performance degradation on real-world documents

### DGQA vs. Standard Training (Expected Performance Comparison)

| Approach | Synthetic Performance | Real-World Performance | Domain Gap |
|----------|----------------------|------------------------|------------|
| **Standard Training** | Pearson r = 0.80 | Pearson r = 0.60-0.65 | **15-20%** |
| **DGQA Calibration** | Pearson r = 0.78 | Pearson r = 0.75-0.78 | **<5%** |

**Key Benefit**: DGQA trades 2-3% synthetic performance for 10-15% real-world improvement

### Real-World Holdout Annotation Strategy

**Problem**: Manual annotation of 500-1000 real-world samples expensive (~20 hours)

**Solution**: Efficient annotation protocol with quality controls

**Annotation Protocol:**
1. **Sample Selection**: Stratified sampling from DocLayNet (diverse document types, quality levels)
2. **Annotator Training**: Calibration session with 20 reference images (quality examples)
3. **3-Dimension Scoring**:
   - Overall Quality: 1-5 Likert scale (1=poor, 5=excellent) → normalized to 0.0-1.0
   - Sharpness: 1-5 Likert scale (1=very blurry, 5=very sharp) → normalized to 0.0-1.0
   - Color Fidelity: 1-5 Likert scale (1=poor contrast, 5=excellent contrast) → normalized to 0.0-1.0
4. **Inter-Annotator Agreement**: Each image annotated by 2-3 annotators, average scores used
5. **Quality Control**: Flag disagreements (standard deviation >1.0) for re-annotation

**Cost Estimate:**
- **Annotators**: 5-10 annotators (crowdsourced or internal)
- **Time per Image**: 30-60 seconds (3 scores per image)
- **Total Time**: 500 images × 60s × 3 annotators = 25 hours (distributed)
- **Cost**: ~$500-1000 (crowdsourcing platform) or ~$2000-3000 (internal annotators at $40/hr)

### Fallback Strategy (If Real-World Annotation Budget Unavailable)

**Alternative**: Pseudo-labeling with ensemble of classical methods

**Approach**:
1. Use Phase 1 classical detectors (blur, contrast) as weak supervision for real-world samples
2. Ensemble BRISQUE/NIQE/classical methods to generate pseudo-labels
3. Calibrate on pseudo-labeled real-world samples (less accurate but zero annotation cost)

**Expected Performance**: Pearson r = 0.70-0.73 (vs. 0.75-0.78 with manual annotations)

**Trade-off**: 3-5% performance loss vs. $500-3000 annotation cost savings

### DGQA Integration with Hybrid Validation Strategy

**Phase 1 Hybrid Validation** (Classical Detectors):
- Synthetic (perfect ground truth) + Real-world (calibration)
- Threshold tuning based on real-world detection rates
- **Success**: Prevented 100% false positive rate for contrast detection

**Phase 2 DGQA** (Learned Models):
- Synthetic (weak supervision) + Domain adaptation (feature alignment) + Real-world (calibration)
- Model fine-tuning based on real-world manual annotations
- **Goal**: Prevent 15-25% performance degradation on real-world documents

**Unified Framework**: Both phases address synthetic-to-real domain shift, but with different methodologies:
- **Classical**: Threshold calibration on real-world detection rates
- **Learned**: Domain-invariant feature learning + model calibration on real-world annotations

### Success Criteria (Phase 2 DGQA Validation)

**Required Outcomes:**
1. ✅ **Synthetic Performance Maintained**: Pearson r > 0.75 on synthetic test set
2. ✅ **Real-World Generalization**: Pearson r > 0.75 on real-world test set (FR-2.3 target)
3. ✅ **Domain Gap Reduced**: <5% performance difference between synthetic and real-world
4. ✅ **Production Readiness**: No false positive disasters (like Phase 1 contrast miscalibration)
5. ✅ **Calibration Efficiency**: Real-world annotation cost <$3000 or use pseudo-labeling fallback

**Validation Report Format:**
```markdown
## Phase 2 DGQA Validation Report

### Synthetic Test Set (10k samples)
- Overall Quality: Pearson r = 0.78, Spearman ρ = 0.76
- Sharpness: Pearson r = 0.80, Spearman ρ = 0.79
- Color Fidelity: Pearson r = 0.77, Spearman ρ = 0.75

### Real-World Test Set (200 samples)
- Overall Quality: Pearson r = 0.76, Spearman ρ = 0.74
- Sharpness: Pearson r = 0.78, Spearman ρ = 0.77
- Color Fidelity: Pearson r = 0.75, Spearman ρ = 0.73

### Domain Gap Analysis
- Overall Quality: 2.6% gap (acceptable)
- Sharpness: 2.5% gap (acceptable)
- Color Fidelity: 2.6% gap (acceptable)

### Conclusion
✅ DGQA calibration successful. Domain gap <5% achieved. Model ready for production.
```

## References (Updated)

**Phase 1 References:**
- [Synthetic Validation Dataset Strategy (ADR-006)](0006-synthetic-validation-dataset-strategy.md)
- [Phase 1 Validation: Stage 3A/3B Coverage Update](../project/phases/phase-1-validation/STAGE_3A_3B_COVERAGE_UPDATE.md)
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet)
- [Microsoft Genalog](https://github.com/microsoft/genalog)
- [Phase 1 Completion Summary](../../PHASE_1_COMPLETE.md)

**Phase 2+ DGQA References:**
- [ADR-029: Three-Tier Dataset Strategy](0029-phase2-dataset-selection-strategy.md) - TableBank synthetic data, DIQA-5000 benchmark
- [FR-2.3: Learned Quality Assessment](../requirements/functional_requirements_v2.md#fr-23-learned-quality-assessment-phase-2) - 3-dimension output specification
- [ADR-025: MobileNetV3 vs. EfficientNet](0025-mobilenetv3-vs-efficientnet.md) - Model architecture selection
- [ADR-023: Weak Supervision (BRISQUE/NIQE)](0023-weak-supervision-brisque-niqe.md) - Pseudo-label generation

**DGQA Research Papers** (to be added):
- Domain-Generalized Quality Assessment for Document Images (Q4 2024 - Q4 2025 literature)
- Adversarial Domain Adaptation for Image Quality Assessment
- Transfer Learning for Document Understanding
