---
schema_type: common
title: "ADR-012: Defer Handwriting Detection to Phase 2"
description: "Decision to defer specialized handwriting detection in favor of Phase
  1 MVP with general text detection"
tags:
- adr
- handwriting
- phase_planning
- mvp
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to defer handwriting-specific detection to Phase 2
  while validating Phase 1 detectors work on handwritten content."
---


**Status**: Accepted
**Date**: 2025-11-05
**Deciders**: Byron Williams
**Related**:

- [validation/HANDWRITING_ANALYSIS_COMPLETE.md](../../validation/HANDWRITING_ANALYSIS_COMPLETE.md)
- [validation/handwriting_samples_analysis.json](../../validation/handwriting_samples_analysis.json)
- [PROJECT_PLAN.md](../../PROJECT_PLAN.md)
- [ADR-008: Multi-Stage Pipeline Architecture](0008-multi-stage-pipeline-architecture.md)

## Context

During Phase 1 development, we needed to decide whether to include specialized handwriting detection or defer it to later phases.

### Handwriting Validation Results

**Test Coverage**:

- **Manual Samples**: 6 web-sourced handwriting images
- **SignaTR6K Dataset**: 50 random samples from 6,257 legal document crops

**Phase 1 Detector Performance on Handwriting**:

| Detector | Manual Samples | SignaTR6K Samples | Status |
|----------|----------------|-------------------|--------|
| **Text Gate** | 6/6 detected (100%) | 50/50 detected (100%) | ✅ Works |
| **Blur Detector** | 1/6 flagged (17%) | 0/50 flagged (0%) | ✅ Accurate |
| **Contrast Detector** | 6/6 flagged (100%) | 0/50 flagged (0%) | ⚠️ Needs tuning |
| **Skew Detector** | 0/6 flagged (0%) | 19/50 flagged (38%) | ✅ Excellent |

### Key Findings

1. **Phase 1 Detectors Work**: All classical IQA detectors functional on handwriting (100% text detection rate)
2. **Contrast Calibration**: Manual samples have lower contrast (0.136 mean) than business documents (0.18 threshold)
3. **Skew is Common**: 38% skew rate in legal handwriting vs. 4% in printed documents
4. **Dataset Available**: SignaTR6K provides 6,257 high-quality handwriting samples for future work

### Handwriting-Specific Challenges

1. **Lower Contrast**: Handwritten scans have systematically lower contrast than printed documents
2. **Higher Skew Rate**: 38% vs. 4% for printed documents
3. **Segmentation Needs**: Overlapping printed and handwritten text requires pixel-wise segmentation
4. **Content-Aware Thresholds**: May need different thresholds for handwriting vs. printed text

## Decision

**Defer specialized handwriting detection to Phase 2, while ensuring Phase 1 detectors work on handwritten content.**

### Phase 1 (Complete)

- Text gate detects handwriting as text (100% accuracy)
- Classical IQA detectors work on handwriting (validated on 56 samples)
- No handwriting-specific logic or thresholds

### Phase 2 (Planned)

**Option A: Noteshrink-Based Detector** (Classical CV)

- K-means clustering for background/foreground separation
- HSV colorspace analysis for ink detection
- 5% pixel sampling for efficiency
- No ML required

**Option B: SignaTR6K-Based Segmentation** (ML)

- Train U-Net or DeepLabV3 on SignaTR6K masks
- Pixel-wise handwriting vs. printed text classification
- 6,257 training samples available
- Requires GPU training infrastructure

**Option C: Hybrid Approach** (Recommended)

- Use noteshrink for fast binary handwriting detection (Phase 2)
- Use SignaTR6K for precise segmentation if needed (Phase 3+)
- Progressive enhancement strategy

### Content-Aware Thresholds (Phase 2)

```python
# Proposed handwriting-specific thresholds
if document_type == "handwriting":
    contrast_threshold = 0.13  # mean - 1σ from manual samples
    blur_threshold = 150       # allow slightly softer scans
    skew_threshold = 1.0       # tolerate minor rotation
else:
    contrast_threshold = 0.18  # business documents
    blur_threshold = 200       # standard sharpness
    skew_threshold = 0.5       # strict alignment
```

## Consequences

### Positive

1. **Phase 1 MVP Delivered**: No delay to core functionality for handwriting support
2. **Validated Foundation**: Phase 1 detectors confirmed to work on handwriting (no blockers)
3. **Progressive Enhancement**: Can add handwriting-specific features incrementally
4. **Resource Efficiency**: Defer GPU training infrastructure to Phase 2 when ML models needed
5. **Dataset Ready**: SignaTR6K (6,257 samples) available for Phase 2 implementation
6. **Lower Risk**: Focus Phase 1 on stable classical CV methods, add ML complexity later

### Negative

1. **Contrast Over-Flagging**: Manual handwriting scans may be flagged unnecessarily (100% vs. 53% business docs)
2. **No Segmentation**: Cannot distinguish handwritten from printed text within mixed documents
3. **Threshold Mismatch**: Single threshold set for business documents may not optimize for handwriting
4. **Missed Opportunity**: Could have content-aware processing in Phase 1

### Neutral

1. **Skew Detection**: Already handles handwriting well (38% detection rate, -22.5° to +22.5° range)
2. **Text Gate**: 100% detection rate on handwriting, no changes needed
3. **Blur Detection**: Works accurately on both clean and degraded handwriting samples

## Alternatives Considered

### Alternative 1: Implement Handwriting Detection in Phase 1

**Approach**: Add noteshrink-based detector and content-aware thresholds to Phase 1

**Advantages**:

- Better handling of handwritten documents immediately
- Content-aware thresholds from the start
- No over-flagging of handwriting contrast

**Disadvantages**:

- Delays Phase 1 MVP delivery (additional 2-3 weeks)
- Increases Phase 1 complexity and risk
- Limited handwriting validation data available
- Requires additional testing and threshold tuning

**Why Rejected**: Phase 1 priority is stable MVP with classical methods; handwriting enhancement is Phase 2 work

### Alternative 2: Train ML Segmentation Model in Phase 1

**Approach**: Use SignaTR6K to train handwriting segmentation model

**Advantages**:

- Pixel-wise handwriting detection
- State-of-the-art accuracy
- Leverages existing 6,257 training samples

**Disadvantages**:

- Requires GPU training infrastructure (not available in Phase 1)
- Adds ML complexity to classical CV phase
- Training time: ~1-2 weeks
- Delays Phase 1 delivery by 3-4 weeks

**Why Rejected**: Phase 1 is CPU-only classical methods; GPU and ML infrastructure deferred to Phase 2

### Alternative 3: Ignore Handwriting Entirely

**Approach**: No handwriting consideration, assume printed text only

**Advantages**:

- Simplest approach
- Focus solely on business documents
- No additional work

**Disadvantages**:

- Unknown performance on handwriting
- Risk of failures on handwritten content
- No validation data for handwriting

**Why Rejected**: Validation showed handwriting is common in real-world documents; need to ensure detectors work

## Implementation

### Phase 1 Status (Complete)

**Validation**:

- ✅ Text gate: 100% detection on handwriting (56/56 samples)
- ✅ Blur detector: Accurate on clean and degraded samples
- ✅ Contrast detector: Works but may over-flag amateur scans
- ✅ Skew detector: Excellent performance (38% detection rate, ±22.5° range)

**No Code Changes Required**: Phase 1 detectors work on handwriting as-is

### Phase 2 Implementation Plan

**Step 1: Noteshrink Integration** (Week 8-9)

- Integrate noteshrink algorithm for binary handwriting detection
- K-means clustering for ink/background separation
- HSV colorspace analysis

**Step 2: Content-Aware Thresholds** (Week 9-10)

- Implement document_type classification (handwriting vs. printed)
- Adjust thresholds based on content type
- Validate on SignaTR6K and manual samples

**Step 3: Validation** (Week 10-11)

- Test on full SignaTR6K dataset (6,257 samples)
- Measure precision/recall for handwriting detection
- Calibrate thresholds for optimal F1 score

### Phase 3+ (Optional Enhancement)

**SignaTR6K Segmentation Model**:

- Train U-Net or DeepLabV3 on pixel-wise masks
- Distinguish handwritten from printed text in mixed documents
- Use for precise element-level handwriting detection

## References

- [Handwriting Analysis Complete Report](../../validation/HANDWRITING_ANALYSIS_COMPLETE.md)
- [Handwriting Samples Analysis (JSON)](../../validation/handwriting_samples_analysis.json)
- [SignaTR6K Dataset](https://github.com/thomasrockhu/signatr6k)
- [Noteshrink Algorithm](https://mzucker.github.io/2016/09/20/noteshrink.html)
- [ADR-008: Multi-Stage Pipeline Architecture](0008-multi-stage-pipeline-architecture.md)
- [PROJECT_PLAN.md Phase 2 Details](../../PROJECT_PLAN.md#phase-2-ml-for-image-quality-weeks-8-11)

## Comparative Analysis: Manual vs. SignaTR6K

| Metric | Manual Samples | SignaTR6K Samples | Difference |
|--------|----------------|-------------------|------------|
| **Blur (mean)** | 1,253.9 | 10,637.2 | **8.5× sharper** |
| **Contrast (mean)** | 0.136 | 0.364 | **2.7× higher** |
| **Skew rate** | 0% | 38% | **+38%** |
| **Low contrast rate** | 100% | 0% | **-100%** |

**Insights**:

1. SignaTR6K legal documents are professionally scanned (higher quality)
2. Manual web samples represent amateur handwriting scans (lower quality)
3. Both extremes validated - detectors work across quality spectrum
4. Real-world handwriting has significant skew variance (38% detection rate)

## Production Readiness

**Phase 1 Conclusion**:
> ✅ IQA detectors successfully validated on handwriting content. Current Phase 1 detectors work on handwriting; no blockers for deployment.

**Phase 2 Enhancements**:

- Noteshrink-based handwriting detection
- Content-aware threshold selection
- Optional SignaTR6K segmentation model for precise localization
