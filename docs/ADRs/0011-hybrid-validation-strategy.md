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
**Date**: 2025-11-05
**Deciders**: Byron Williams
**Related**:
- [ADR-006: Synthetic Validation Dataset Strategy](0006-synthetic-validation-dataset-strategy.md)
- [validation/STAGE_3A_3B_COVERAGE_UPDATE.md](../../validation/STAGE_3A_3B_COVERAGE_UPDATE.md)
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
- [Stage 3A/3B Coverage Update](../../validation/STAGE_3A_3B_COVERAGE_UPDATE.md)
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet)
- [Microsoft Genalog](https://github.com/microsoft/genalog)
- [Phase 1 Completion Summary](../../PHASE_1_COMPLETE.md)

## Lessons Learned

1. **Distribution Shift is Real**: Synthetic and real-world data have different quality distributions
2. **Calibrate on Target Distribution**: Always calibrate thresholds on production-like data
3. **Ground Truth + Real-World**: Best of both worlds - perfect labels for training, real artifacts for calibration
4. **Catch Issues Early**: Hybrid validation caught critical miscalibration before production deployment
5. **Validation Framework**: Investment in hybrid validation infrastructure pays off for all future detectors
