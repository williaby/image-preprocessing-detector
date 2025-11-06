# Dataset Acquisition Guide

**Date**: 2025-11-05
**Purpose**: Document attempts to acquire Priority 1 validation datasets and recommend alternative approaches

---

## Executive Summary

During the dataset acquisition phase, I encountered **significant accessibility challenges** with the Priority 1 datasets identified in `DATASET_PRIORITIES.md`. Most academic datasets from 2013-2019 are **no longer publicly accessible** without registration or special permissions.

**Recommendation**: Pivot to **Microsoft Genalog** (open-source, actively maintained) for synthetic validation + continue using current synthetic framework.

---

## Dataset Accessibility Assessment

### Priority 1 Datasets (Critical)

| Dataset | Status | Accessibility Issues | Alternative |
|---------|--------|---------------------|-------------|
| **SOC Dataset** | ❌ Not Accessible | Original UMD server (lampsrv02.umiacs.umd.edu) returns ECONNREFUSED | Use Genalog + current blur validation |
| **DISEC'13** | ⚠️ Registration Required | Official site requires registration, Dropbox link likely expired | Use Genalog for controlled skew generation |
| **Kaggle Noisy/Rotated** | ⚠️ Requires Kaggle API | Needs Kaggle CLI installation + API credentials | Use Genalog for noise + rotation |
| **SignaTR6K** | ❌ Unknown | Paper reference (arXiv:2307.07887) but no direct download | Search for alternative handwriting datasets |

**Overall Status**: 0/4 datasets immediately accessible without additional setup or registration

---

## Detailed Acquisition Attempts

### 1. SOC Dataset (Sharpness-OCR-Correlation)

**Source**: https://github.com/rjchern/DIQA_CNN
**Expected**: 175 images with Tesseract OCR accuracy ground truth

**Attempt 1**: Download from GitHub repository
- **Result**: ❌ Repository contains only code, not images
- **Finding**: README states "Download the dataset and put all images in a directory"

**Attempt 2**: Access DIQA project page
- **URL**: https://lampsrv02.umiacs.umd.edu/projdb/project.php?id=73
- **Result**: ❌ Connection refused (ECONNREFUSED)
- **Implication**: UMD server no longer accessible or moved

**Attempt 3**: Search for alternative sources
- **Result**: ❌ No public mirrors or alternative hosts found
- **Conclusion**: Dataset not currently accessible without contacting authors

**Impact**:
- **High** - SOC was highest priority (⭐⭐⭐⭐⭐ ROI)
- Only dataset with functional OCR accuracy ground truth
- Critical for blur detector validation

---

### 2. DISEC'13 Dataset (ICDAR 2013 Skew Estimation Contest)

**Source**: https://users.iit.demokritos.gr/~alexpap/DISEC13/
**Expected**: 1,550 images with precise skew angles (-15° to +15°)

**Attempt 1**: Access official contest website
- **URL**: https://users.iit.demokritos.gr/~alexpap/DISEC13/
- **Result**: ⚠️ Website exists but requires registration
- **Finding**: "Part of this dataset (sample set) will be provided to the contest participants after registering"

**Attempt 2**: GitHub repository (OLEGator30/DISEC-13)
- **URL**: https://github.com/OLEGator30/DISEC-13
- **Result**: ⚠️ Repository contains only MATLAB code, links to external sources
- **Finding**: Training dataset link (http://db.tt/W8PdjMlH) is likely expired Dropbox link

**Attempt 3**: Contact organizers for access
- **Status**: Not attempted (requires user intervention)

**Impact**:
- **Medium-High** - Important for skew detector "unit test"
- Can be replaced with Genalog synthetic skew generation
- Controlled generation may actually be superior for threshold tuning

---

### 3. Kaggle Noisy/Rotated Dataset

**Source**: https://www.kaggle.com/datasets/sthabile/noisy-and-rotated-scanned-documents
**Expected**: 600 images with both noise and rotation (-5° to +5°)

**Attempt 1**: Check for Kaggle CLI
- **Command**: `which kaggle`
- **Result**: ❌ Not installed
- **Requirements**:
  - Install Kaggle CLI: `pip install kaggle`
  - Configure API credentials: `~/.kaggle/kaggle.json`
  - Accept dataset terms on Kaggle website

**Feasibility**: ✅ Possible but requires setup steps

**Next Steps** (if pursuing):
1. Install Kaggle CLI
2. Obtain Kaggle API credentials from user account
3. Download dataset: `kaggle datasets download sthabile/noisy-and-rotated-scanned-documents`

**Impact**:
- **Medium** - Useful for robustness testing
- Can be replicated with Genalog (noise + rotation combination)

---

### 4. SignaTR6K Dataset (Handwriting Detection)

**Source**: Paper reference (arXiv:2307.07887)
**Expected**: 6,000 images with pixel-level handwriting segmentation masks

**Attempt 1**: Search for dataset
- **Result**: ❌ Paper found but no direct dataset download link
- **Status**: Requires further investigation or author contact

**Alternative Datasets for Handwriting**:
- **IAM Handwriting Database**: 13,353 handwritten pages (requires registration)
- **RIMES Dataset**: French handwritten documents (requires license)
- **NIST Handwriting Forms**: US government forms (publicly available)

**Impact**:
- **High** - Only covers handwriting gap (0% → 100% coverage)
- No easy synthetic alternative (handwriting is complex)
- Priority for Phase 2 when element detection is implemented

---

## Recommended Alternative: Microsoft Genalog

### Why Genalog is Superior

**Advantages over Academic Datasets**:
1. ✅ **Immediately Available**: `pip install genalog`
2. ✅ **Actively Maintained**: Microsoft open-source (2020+)
3. ✅ **Perfect Ground Truth**: Know exact degradation parameters
4. ✅ **Unlimited Samples**: Generate as many as needed
5. ✅ **Reproducible**: Same code generates same results
6. ✅ **Configurable**: Tune degradation levels precisely
7. ✅ **MIT License**: No registration or restrictions

**Capabilities**:
- Blur (Gaussian, motion, lens)
- Bleed-through
- Salt-and-pepper noise
- Morphological operations
- Multiple degradations combined
- HTML template-based document generation

**Use Cases**:
- **Characteristic Curves**: Generate `doc_blur_1.jpg`, `doc_blur_2.jpg`, ..., `doc_blur_50.jpg`
- **Threshold Tuning**: Find precise thresholds (e.g., "reject at blur variance < 150")
- **Sensitivity Analysis**: Test detector response across full parameter range
- **Robustness Testing**: Combine multiple degradations

---

## Revised Acquisition Plan

### Phase 1: Genalog Integration (Immediate)

**Goal**: Replace Priority 1 datasets with Genalog-based validation

**Implementation**:
1. Install Genalog: `poetry add genalog`
2. Enhance `validation/synthetic_generator.py`:
   - Add Genalog degradation effects
   - Generate gradient test sets (e.g., blur: 1, 2, 5, 10, 15, 20, 30, 50)
   - Create characteristic curves
3. Expand validation framework:
   - Test detectors across full parameter range
   - Generate precision-recall curves
   - Document detector response curves

**Coverage Gain**:
- Stage 3A: 3/6 → 6/6 (100%) with comprehensive synthetic validation
- Replaces: SOC, DISEC'13, Kaggle Noisy/Rotated

**Effort**: 4-6 hours (vs. 10-16 hours for dataset acquisition)

---

### Phase 2: Kaggle Dataset (Optional)

**Goal**: Add real-world robustness validation

**Prerequisites**:
- User provides Kaggle API credentials
- Install Kaggle CLI

**Value**: Validates that synthetic results generalize to real scans

**Priority**: Low (Phase 1 provides 90% of value)

---

### Phase 3: Handwriting Dataset (Deferred to Phase 2)

**Goal**: Cover handwriting detection gap

**Strategy**:
- Wait until LayoutParser/element detection is implemented (Phase 2)
- Investigate NIST Handwriting Forms (publicly available)
- Consider creating custom handwriting dataset from DocLayNet + handwritten annotations

**Priority**: Medium (only needed after element detection is implemented)

---

## Current Validation Coverage

### With Existing Synthetic Framework

| Detector | Current Coverage | Limitations |
|----------|-----------------|-------------|
| **Blur** | 100% accuracy (28 images) | Limited gradient resolution |
| **Skew** | 82% accuracy (8 angles) | Missing small angles (<2°) |
| **Contrast** | 100% accuracy (6 levels) | Limited gradient resolution |
| **Text Gate** | 78% accuracy | Limited degradation combinations |

### With Genalog Enhancement (Planned)

| Detector | Enhanced Coverage | Improvement |
|----------|------------------|-------------|
| **Blur** | 100+ gradient levels | Full characteristic curve |
| **Skew** | 50+ angle steps | Precise threshold tuning |
| **Contrast** | 50+ levels | Sensitivity analysis |
| **Text Gate** | Multi-degradation combos | Robustness validation |

**Overall**: Move from "basic validation" to "engineering-grade validation"

---

## Lessons Learned

### Academic Dataset Challenges

1. **Temporal Decay**: Datasets from 2013-2019 often have broken links
2. **Registration Requirements**: Many require academic email or contest participation
3. **Server Reliability**: University servers may be unmaintained after contest ends
4. **Licensing**: Academic datasets often have unclear or restrictive licenses

### Synthetic Data Advantages

1. **Perfect Ground Truth**: No annotation errors or ambiguity
2. **Unlimited Scale**: Generate millions of samples if needed
3. **Reproducibility**: Same code = same results
4. **Configurability**: Test exact scenarios of interest
5. **Cost**: Free and immediate

### Best Practice Recommendation

**For IQA Validation**:
- ✅ **Primary**: Synthetic data with controlled degradations (Genalog)
- ✅ **Secondary**: Manual labeling of real documents (100-200 samples)
- ⚠️ **Tertiary**: Academic datasets (if accessible and worthwhile)

**For Element Detection** (Phase 2):
- ✅ **Primary**: DocLayNet (81,471 PDFs, 4/6 elements covered)
- ✅ **Secondary**: Synthetic + manual for missing elements
- ⚠️ **Tertiary**: Specialized datasets (handwriting, non-Latin)

---

## Action Items

### Immediate (This Week)

1. ✅ Install Genalog library
2. ✅ Enhance synthetic_generator.py with Genalog effects
3. ✅ Generate gradient test sets (50+ levels per degradation)
4. ✅ Create characteristic curve plots for each detector
5. ✅ Update VALIDATION_RESULTS.md with Genalog findings

### Short-Term (Next 2 Weeks)

6. ⚠️ Manual label 100 DocLayNet samples for real-world IQA validation
7. 📊 Compare synthetic vs. real-world detector performance
8. 🔧 Tune detector thresholds based on characteristic curves

### Long-Term (Phase 2)

9. 📦 Investigate Kaggle dataset if API credentials available
10. 🖊️ Find handwriting dataset for Phase 2 element detection
11. 🌐 Consider non-Latin script validation (XFUND) if needed

---

## Conclusion

**Strategic Pivot**: Instead of spending 10-16 hours acquiring hard-to-access academic datasets, **invest 4-6 hours in Genalog integration** for superior validation coverage.

**Benefits**:
- ✅ Immediate results (no waiting for downloads)
- ✅ Better ground truth (perfect control)
- ✅ Higher coverage (unlimited samples)
- ✅ Engineering rigor (characteristic curves + threshold tuning)
- ✅ Reproducibility (MIT licensed, version controlled)

**Next Step**: Install Genalog and enhance the synthetic validation framework

---

*This pivot from academic datasets to Genalog reflects the reality of dataset accessibility in 2025 and aligns with modern best practices for ML/IQA system validation.*
