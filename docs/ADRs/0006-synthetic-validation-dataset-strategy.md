---
schema_type: common
title: "ADR-006: Synthetic Validation Dataset Strategy"
description: "Decision to use Microsoft Genalog for synthetic validation data instead
  of inaccessible academic datasets"
tags:
- adr
- validation
- testing
- datasets
- synthetic_data
- quality_assurance
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to pivot from academic datasets to synthetic data
  generation for validation of image quality assessment."
---


**Status**: ✅ **Accepted**
**Date**: 2025-11-05
**Deciders**: Byron Williams
**Related**: Phase 1 Validation, Quality Assurance Strategy

## Context

The project requires comprehensive validation datasets to verify Image Quality Assessment (IQA) detectors for:

- Blur detection
- Skew/rotation detection
- Noise detection
- Perspective distortion
- Contrast assessment
- Orientation detection

### Initial Plan

Priority 1 academic datasets identified in [DATASET_PRIORITIES.md](../../validation/DATASET_PRIORITIES.md):

| Dataset | Purpose | Ground Truth | Status |
|---------|---------|--------------|--------|
| SOC Dataset | Blur/OCR correlation | 175 images with Tesseract accuracy | ❌ Inaccessible |
| DISEC'13 | Skew estimation | 1,550 images with precise angles | ⚠️ Registration required |
| Kaggle Noisy/Rotated | Noise + rotation | 1,000+ images | ⚠️ API credentials required |
| SignaTR6K | Handwriting | 6,000+ samples | ❌ Unknown availability |

### Accessibility Challenges

**Documented in [DATASET_ACQUISITION_GUIDE.md](../../validation/DATASET_ACQUISITION_GUIDE.md)**:

1. **SOC Dataset**: UMD server (lampsrv02.umiacs.umd.edu) returns ECONNREFUSED
   - Original highest priority (⭐⭐⭐⭐⭐ ROI)
   - Only dataset with functional OCR accuracy ground truth
   - No public mirrors found

2. **DISEC'13**: Website requires registration
   - Dropbox links likely expired
   - Would require contacting organizers

3. **Kaggle Datasets**: Require API setup and credentials
   - Additional authentication complexity
   - Privacy/licensing considerations

4. **SignaTR6K**: No accessible download found
   - Paper reference exists but no dataset access

### Requirements

1. **Immediate Availability**: No registration or special permissions
2. **Controllable Parameters**: Precise ground truth for threshold tuning
3. **Reproducibility**: Deterministic generation for regression testing
4. **Coverage**: All IQA dimensions (blur, skew, noise, etc.)
5. **Scale**: Generate thousands of validation samples
6. **Maintenance**: Actively maintained tooling

## Decision

**Adopt Microsoft Genalog for synthetic validation data generation instead of academic datasets.**

### Solution Architecture

1. **Microsoft Genalog** (Primary)
   - Open-source, actively maintained by Microsoft
   - Synthetic document degradation engine
   - Controllable parameters for all IQA dimensions
   - Supports:
     - Blur (Gaussian, motion, defocus)
     - Skew/rotation (precise angle control)
     - Noise (Gaussian, salt-and-pepper, speckle)
     - Contrast (gamma correction, histogram adjustment)
     - Perspective distortion
     - Morphological transformations

2. **Custom Synthetic Framework** (Complementary)
   - Existing blur/noise/skew generation
   - Integration with Genalog for comprehensive coverage
   - Fine-grained control for edge case testing

3. **DocLayNet** (Real-World Baseline)
   - 80,000+ document element annotations
   - Covers Stage 3B (layout detection)
   - No IQA ground truth, but real-world complexity

### Implementation Strategy

```python
# Genalog synthetic generation example
from genalog.degradation.degrader import Degrader

degrader = Degrader([
    ("blur", {"radius": 3}),
    ("bleed_through", {"alpha": 0.5}),
    ("salt", {"amount": 0.01}),
])

degraded_image = degrader.apply_effects(clean_image)
```

**Validation Coverage**:
- **Blur**: Gaussian blur with controlled radius (1-20px)
- **Skew**: Rotation with precise angles (-15° to +15°, 0.1° increments)
- **Noise**: Multiple types with controlled intensities
- **Perspective**: Simulated camera angles and lens distortion
- **Contrast**: Gamma and histogram manipulations

## Consequences

### Positive

1. **Immediate Availability**: No registration, API credentials, or special permissions
2. **Perfect Ground Truth**: Exact parameters known (blur radius, rotation angle, etc.)
3. **Reproducibility**: Deterministic generation enables regression testing
4. **Scale**: Generate unlimited samples for comprehensive coverage
5. **Threshold Tuning**: Controlled parameters ideal for calibrating detectors
6. **Maintenance**: Microsoft-backed, actively maintained
7. **Cost**: Free, no licensing or access fees
8. **Automation**: Easily integrated into CI/CD pipeline

### Negative

1. **Synthetic Bias**: May not capture all real-world degradation patterns
   - Mitigation: Use DocLayNet for real-world baseline validation
   - Mitigation: Generate diverse parameter combinations
2. **Domain Gap**: Synthetic ≠ real-world scanned documents
   - Mitigation: Document and monitor false positives/negatives
   - Mitigation: Incremental real-world testing in production
3. **OCR Correlation**: No OCR accuracy ground truth like SOC dataset
   - Mitigation: Synthetic OCR validation using Tesseract on generated images
   - Acceptable: Can measure OCR degradation on synthetic samples

### Neutral

1. **Hybrid Approach**: Synthetic + DocLayNet provides comprehensive coverage
2. **Flexibility**: Easy to pivot to real datasets if they become accessible

## Alternatives Considered

### Alternative 1: Wait for Dataset Access
**Rejected**:
- Blocks project progress indefinitely
- No guarantee of eventual access
- Registration/permissions may require institutional affiliation

### Alternative 2: Contact Dataset Authors
**Rejected**:
- Time-consuming (weeks to months)
- No guarantee of response or access
- May require academic collaboration agreements

### Alternative 3: Use Only DocLayNet
**Rejected**:
- DocLayNet has no IQA ground truth
- Missing validation for blur, noise, skew, etc.
- Stage 3A would be untested

### Alternative 4: Build Custom Validation Dataset
**Rejected**:
- Expensive (manual annotation)
- Time-consuming (would delay Phase 1)
- Genalog provides superior ground truth

### Alternative 5: Use Albumentations Library
**Partially Accepted**:
- Albumentations provides augmentations, not degradations
- Can complement Genalog for additional variations
- Not a complete replacement

## Implementation

- **Tool**: [Microsoft Genalog](https://github.com/microsoft/genalog)
- **Documentation**: [DATASET_ACQUISITION_GUIDE.md](../../validation/DATASET_ACQUISITION_GUIDE.md)
- **Priorities**: [DATASET_PRIORITIES.md](../../validation/DATASET_PRIORITIES.md)
- **Status**: Implementation ongoing (Phase 1)

### Validation Framework

```python
# Example validation test structure
def test_blur_detector_with_genalog():
    """Validate blur detector using Genalog synthetic data."""
    for blur_radius in [1, 3, 5, 10, 15, 20]:
        degraded = genalog_blur(clean_image, radius=blur_radius)
        confidence, metrics = blur_detector.detect(degraded)

        # Ground truth: blur_radius > threshold should be detected
        expected_detection = blur_radius > BLUR_THRESHOLD
        assert (confidence > 0.7) == expected_detection
```

## Success Metrics

- Generate 1,000+ validation samples per IQA dimension
- Achieve 95%+ detection accuracy on synthetic data
- Document any real-world gaps discovered
- Establish threshold calibration baselines

## Future Considerations

If Priority 1 academic datasets become accessible:
1. Acquire and integrate for comparison
2. Measure synthetic vs. real-world performance gap
3. Calibrate thresholds based on real-world data
4. Document findings in validation/REAL_WORLD_VALIDATION_COMPLETE.md

## References

- [Microsoft Genalog](https://github.com/microsoft/genalog)
- [DATASET_ACQUISITION_GUIDE.md](../../validation/DATASET_ACQUISITION_GUIDE.md)
- [DATASET_PRIORITIES.md](../../validation/DATASET_PRIORITIES.md)
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet)
- [Albumentations](https://albumentations.ai/)
- [VALIDATION_RESULTS.md](../../validation/VALIDATION_RESULTS.md)
