# Dataset Acquisition Priorities for Validation Coverage

**Analysis Date**: 2025-11-04
**Purpose**: Identify highest-impact datasets to acquire for comprehensive Stage 3A/3B validation

---

## Executive Summary

Based on your current validation gaps and available datasets:

**Current Coverage**:
- Stage 3A (IQA): **0/6 elements** (0%) - DocLayNet provides no IQA ground truth
- Stage 3B (Elements): **4/6 elements** (67%) - DocLayNet covers tables, figures, formulas, footnotes

**Recommended Dataset Acquisition**:
1. **Priority 1 (Critical)**: 3 datasets to cover Stage 3A IQA gaps
2. **Priority 2 (High)**: 2 datasets to cover Stage 3B missing elements
3. **Priority 3 (Optional)**: Enhancement datasets for robustness

**Total Recommended**: 5 critical datasets + DocLayNet (already have)

---

## Current Validation Gaps

### Stage 3A: Image Quality Assessment (NO-TEXT BRANCH)

| Issue | Current Validation | Gap |
|-------|-------------------|-----|
| Noise | ✅ Synthetic only | ❌ No real-world ground truth |
| Blur | ✅ Synthetic only | ❌ No real-world ground truth |
| Skew/Rotation | ✅ Synthetic only | ❌ No real-world ground truth |
| Perspective Distortion | ❌ None | ❌ No validation at all |
| Low Contrast | ✅ Synthetic only | ❌ No real-world ground truth |
| Image Orientation | ❌ None | ❌ No validation at all |

**Gap**: All 6 IQA issues lack real-world validation

### Stage 3B: Document Element Detection (TEXT BRANCH)

| Element | DocLayNet | Gap |
|---------|-----------|-----|
| Tables | ✅ ~25,000 samples | None |
| Images/Figures | ✅ ~30,000 samples | None |
| Mathematical Formulas | ✅ ~15,000 samples | None |
| Footnotes | ✅ ~20,000 samples | None |
| Handwriting | ❌ 0 samples | ❌ Missing entirely |
| Non-Latin Scripts | ⚠️ Unknown | ❌ No script labels |

**Gap**: Handwriting and Non-Latin scripts not covered

---

## Priority 1: CRITICAL - Stage 3A Real-World IQA Validation

### Dataset 1: SOC (Sharpness-OCR-Correlation) ⭐ HIGHEST PRIORITY

**What it provides**:
- **175 images** with controlled focal blur
- **Ground truth**: Tesseract OCR accuracy (functional metric, not perceptual)
- **Perfect for**: Validating blur detector against actual OCR failure

**Why critical**:
- Your RAG pipeline uses OCR → this directly tests "will blur break Tesseract?"
- Bypasses subjective metrics (MOS) for functional metrics (accuracy)
- **Validation strategy**: Measure detector's ability to predict `acc_t < 90%` threshold

**From image_reference_sets.txt**:
> "The SOC dataset provides the exact Tesseract accuracy (acc_t) for its 175 images. A validation framework can thus bypass proxies like 'blur level' and test the model on its ability to predict the actual outcome of interest."

**Acquisition**:
- Source: https://github.com/rjchern/DIQA_CNN
- Size: 175 images + Excel ground truth
- License: Research use
- Download effort: Low (small dataset)

**Coverage gain**: Blur (real-world functional validation)

---

### Dataset 2: DISEC'13 + Kaggle Noisy/Rotated ⭐ HIGH PRIORITY

**What it provides**:
- **DISEC'13**: 1,550 samples (155 unique, rotated 10x) with precise angles (-15° to +15°)
- **Kaggle Noisy/Rotated**: 600 images with both noise and rotation (-5° to +5°)

**Why critical**:
- **DISEC'13**: "Unit test" for skew detector correctness (clean environment)
- **Kaggle**: "Integration test" for robustness (noisy environment)
- Two-part validation reveals algorithm correctness vs. robustness issues

**From image_reference_sets.txt**:
> "This two-part validation is essential. A skew-detection algorithm relies on finding text lines; image noise can break these lines, causing the algorithm to fail even on a correct image."

**Acquisition**:
- **DISEC'13**: https://arxiv.org/pdf/1912.02504 (find dataset link)
- **Kaggle**: https://www.kaggle.com/datasets/sthabile/noisy-and-rotated-scanned-documents
- Size: DISEC (1,550) + Kaggle (600) = 2,150 images
- License: Research use
- Download effort: Medium

**Coverage gain**: Skew (correctness + robustness), Noise (integration testing)

---

### Dataset 3: Genalog (Synthetic Generator) ⭐ MEDIUM-HIGH PRIORITY

**What it provides**:
- **Python library** for programmatic synthetic generation
- **Degradations**: Blur, bleed-through, salt-and-pepper noise, morphological ops
- **Controlled ground truth** for sensitivity analysis

**Why critical**:
- Create "characteristic curves" for each detector
- Tune thresholds precisely (e.g., "reject at skew > 2.0°")
- Generate gradients: `doc_skew_0.5.jpg`, `doc_skew_1.0.jpg`, ..., `doc_skew_10.0.jpg`

**From image_reference_sets.txt**:
> "This allows for the precise tuning of the model's internal thresholds to match a specific business requirement, transforming validation from a pass/fail check into a robust engineering practice."

**Acquisition**:
- Source: https://github.com/microsoft/genalog (Microsoft open-source)
- Size: Unlimited (generator)
- License: MIT
- Installation effort: Low (pip install)

**Coverage gain**: All Stage 3A issues (sensitivity analysis + threshold tuning)

**Implementation priority**: Defer to Phase 2 (nice-to-have, not blocking)

---

## Priority 2: HIGH - Stage 3B Missing Elements

### Dataset 4: SignaTR6K ⭐ HIGH PRIORITY

**What it provides**:
- **6,000+ images** from real legal documents
- **Pixel-level segmentation masks**: Printed Text (PT), Handwritten Text (HT), Background (BG)
- **Focus**: Overlapping/coexisting printed and handwritten text

**Why critical**:
- Only dataset that addresses "mixed-modality" handwriting detection
- DocLayNet has **zero** handwriting samples
- Real legal document source → matches RAG use case

**From image_reference_sets.txt**:
> "The real-world problem, common in forms and annotated legal or financial documents, is the 'mixed-modality' case where handwritten text and printed text 'coexist' or 'overlap' on the same page."

**Acquisition**:
- Source: https://arxiv.org/abs/2307.07887 (find dataset link)
- Size: 6,000 images
- License: Research use
- Download effort: Medium

**Coverage gain**: Handwriting detection (0% → 100% coverage)

**Validation metric**: IoU (Intersection over Union) against pixel masks

---

### Dataset 5: XFUND (Multilingual Forms) ⚠️ OPTIONAL

**What it provides**:
- **1,393 forms** across 7 languages
- **Languages**: Chinese, Japanese, Spanish, French, Italian, German, Portuguese
- **Annotations**: Key-value extraction with entity/relation labels

**Why consider**:
- Addresses "Non-Latin characters" gap
- Tests multilingual document handling
- Form understanding validation

**From datasets.md**:
> "Useful for non-English pipelines. Use only if multilingual support is required."

**Acquisition**:
- Source: https://github.com/doc-analysis/XFUND
- Size: 1,393 forms
- License: Research use
- Download effort: Medium

**Coverage gain**: Non-Latin scripts (unknown → validated)

**Decision**: Only acquire if RAG pipeline needs multilingual support

---

## Priority 3: OPTIONAL - Enhancement Datasets

### Additional Datasets (Lower Priority)

#### For Stage 3A Enhancement:

| Dataset | Purpose | Size | Priority |
|---------|---------|------|----------|
| **DIQA-5000** | Perceptual quality (MOS) | 5,000 | Low |
| **DocIQ** | Layout-aware quality | 5,000 | Low |

**Rationale**: Subjective metrics (MOS) are less relevant than functional metrics (OCR accuracy) for RAG

#### For Stage 3B Enhancement:

| Dataset | Purpose | Size | Priority |
|---------|---------|------|----------|
| **Marmot** | Formula detection (inline formulas) | 7,907 embedded | Medium |
| **TFD-ICDAR 2019** | Formula detection (char-level) | ~38,000 | Medium |
| **PubTables-1M** | Table structure validation | 1M+ | Medium |

**Rationale**: DocLayNet already covers formulas and tables; these add depth but not coverage

---

## Recommended Acquisition Plan

### Phase 1: Fill Critical Gaps (Weeks 1-2)

**Must-Have** (3 datasets):
1. ✅ **SOC Dataset** (175 images) - Blur + OCR functional validation
2. ✅ **DISEC'13 + Kaggle** (2,150 images) - Skew correctness + robustness
3. ✅ **SignaTR6K** (6,000 images) - Handwriting detection

**Deliverable**: Real-world validation for 3/6 Stage 3A issues + 1/2 Stage 3B gaps

---

### Phase 2: Sensitivity Analysis (Week 3)

**Should-Have** (1 tool):
4. ✅ **Genalog** (Python library) - Threshold tuning + characteristic curves

**Deliverable**: Precision-tuned detectors with documented performance curves

---

### Phase 3: Multilingual Support (Week 4, Optional)

**Nice-to-Have** (1 dataset):
5. ⚠️ **XFUND** (1,393 forms) - Only if multilingual RAG needed

**Deliverable**: Non-Latin script validation

---

## Coverage Before vs. After

### Before Dataset Acquisition

| Category | Coverage | Gap |
|----------|----------|-----|
| **Stage 3A (IQA)** | 0/6 (0%) | Synthetic only |
| **Stage 3B (Elements)** | 4/6 (67%) | Missing handwriting, non-Latin |
| **Overall** | 4/12 (33%) | Major gaps |

### After Phase 1 Acquisition

| Category | Coverage | Gap |
|----------|----------|-----|
| **Stage 3A (IQA)** | 3/6 (50%) | Blur, skew, noise validated |
| **Stage 3B (Elements)** | 5/6 (83%) | Only non-Latin optional |
| **Overall** | 8/12 (67%) | Acceptable coverage |

### After Phase 2 (with Genalog)

| Category | Coverage | Gap |
|----------|----------|-----|
| **Stage 3A (IQA)** | 6/6 (100%) | All issues + tuning |
| **Stage 3B (Elements)** | 5/6 (83%) | Only non-Latin optional |
| **Overall** | 11/12 (92%) | Excellent coverage |

---

## Acquisition Effort Summary

| Dataset | Size | Download | Setup | Total Effort |
|---------|------|----------|-------|--------------|
| SOC | 175 images | Low | Low | 1-2 hours |
| DISEC'13 | 1,550 images | Medium | Low | 2-4 hours |
| Kaggle Noisy | 600 images | Low | Low | 1-2 hours |
| SignaTR6K | 6,000 images | Medium | Medium | 4-6 hours |
| Genalog | Library | Low | Low | 2-3 hours |
| XFUND | 1,393 forms | Medium | Medium | 3-4 hours |

**Total for Phase 1**: ~10-16 hours
**Total for Phase 1+2**: ~12-19 hours
**Total for all**: ~15-23 hours

---

## Cost-Benefit Analysis

### Highest ROI (Return on Investment)

1. **SOC Dataset** ⭐⭐⭐⭐⭐
   - **ROI**: Extremely High
   - **Effort**: 1-2 hours
   - **Gain**: Functional blur validation (OCR-based)
   - **Unique**: Only dataset with Tesseract ground truth

2. **DISEC'13 + Kaggle** ⭐⭐⭐⭐
   - **ROI**: High
   - **Effort**: 3-6 hours
   - **Gain**: Skew correctness + robustness validation
   - **Unique**: Two-part validation strategy

3. **SignaTR6K** ⭐⭐⭐⭐
   - **ROI**: High
   - **Effort**: 4-6 hours
   - **Gain**: Handwriting detection (0% → 100%)
   - **Unique**: Only dataset for mixed-modality handwriting

4. **Genalog** ⭐⭐⭐
   - **ROI**: Medium-High (long-term value)
   - **Effort**: 2-3 hours
   - **Gain**: Threshold tuning + sensitivity analysis
   - **Unique**: Enables engineering rigor

5. **XFUND** ⭐⭐
   - **ROI**: Low (unless multilingual needed)
   - **Effort**: 3-4 hours
   - **Gain**: Non-Latin script validation
   - **Unique**: Multilingual forms

---

## Immediate Action Plan

### This Week: Acquire Critical Datasets

```bash
# 1. SOC Dataset (Blur + OCR)
wget https://github.com/rjchern/DIQA_CNN/raw/main/SOC_gt.xlsx
wget https://github.com/rjchern/DIQA_CNN/archive/refs/heads/main.zip
# Extract images, place in: validation/datasets/soc/

# 2. DISEC'13 (Skew correctness)
# Find dataset link from: https://arxiv.org/pdf/1912.02504
# Place in: validation/datasets/disec13/

# 3. Kaggle Noisy/Rotated (Skew robustness)
kaggle datasets download sthabile/noisy-and-rotated-scanned-documents
# Place in: validation/datasets/kaggle_noisy/

# 4. SignaTR6K (Handwriting)
# Find dataset link from: https://arxiv.org/abs/2307.07887
# Place in: validation/datasets/signatr6k/
```

### Next Week: Create Validation Scripts

```python
# validation/validate_soc.py
# Validates blur detector against SOC Tesseract accuracy

# validation/validate_disec.py
# Validates skew detector correctness

# validation/validate_kaggle_noisy.py
# Validates skew detector robustness to noise

# validation/validate_handwriting.py
# Validates handwriting detection with IoU metric
```

---

## Summary Recommendation

**Acquire These 4 Items Immediately**:
1. ✅ **SOC Dataset** - Functional blur validation
2. ✅ **DISEC'13** - Skew correctness
3. ✅ **Kaggle Noisy/Rotated** - Skew robustness
4. ✅ **SignaTR6K** - Handwriting detection

**Defer These to Phase 2**:
5. **Genalog** - Threshold tuning (install when needed)
6. **XFUND** - Only if multilingual support required

**Total Effort**: 10-16 hours
**Coverage Gain**: 33% → 67% (doubling coverage)
**Cost**: Free (all research datasets)

---

## Validation Framework Integration

Once acquired, integrate into validation pipeline:

```bash
# Run comprehensive validation
poetry run python validation/validate_all.py \
    --synthetic  # Current 28 images \
    --soc        # 175 real-world blur images \
    --disec      # 1,550 clean skew images \
    --kaggle     # 600 noisy skew images \
    --signatr    # 6,000 handwriting images \
    --output validation/comprehensive_report.json
```

**Expected output**:
- Synthetic: Controlled baseline (current: 100% blur, 100% contrast, 82% skew)
- SOC: Functional blur validation (target: >85% @ OCR threshold)
- DISEC: Skew correctness (target: MAE <1.0°)
- Kaggle: Skew robustness (target: MAE <2.0° with noise)
- SignaTR: Handwriting IoU (target: >0.70)

---

*This analysis prioritizes datasets that provide the highest coverage gains with the lowest acquisition effort, following the principle of "biggest gap first, easiest acquisition second."*
