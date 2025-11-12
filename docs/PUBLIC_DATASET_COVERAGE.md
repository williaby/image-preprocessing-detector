# Publicly Accessible Dataset Coverage Analysis

**Analysis Date**: 2025-01-15
**Purpose**: Evaluate dataset coverage when excluding datasets that require author contact or have restricted access

---

## Dataset Accessibility Classification

### ✅ Fully Public & Accessible (14 datasets)

| Dataset | Access Method | Notes |
|---------|---------------|-------|
| **DIQA-5000 (VQualA)** | CodaLab Competition | Direct download via competition platform |
| **DocIQ** | arXiv + Paper | Paper available, dataset details in publication |
| **SOC Dataset** | GitHub Repository | Included in DIQA_CNN repository |
| **PubLayNet** | GitHub Repository | Large-scale, freely available |
| **DocLayNet** | GitHub + Hugging Face | Multiple access points, well-documented |
| **TableBank** | Official Website + GitHub | Direct download links provided |
| **PubTabNet** | GitHub + Direct Download | CDN-hosted with direct links |
| **TFD-ICDAR 2019** | GitHub Repository | Available with PDF links |
| **Kaggle Noisy/Rotated** | Kaggle Platform | Free with Kaggle account |
| **DocCreator** | GitHub + Website | Open-source software with binaries |
| **Genalog** | GitHub + PyPI | `pip install genalog` |
| **RVL-CDIP** | Website + Hugging Face | Multiple access methods |
| **Tobacco800** | Kaggle | Free with Kaggle account |
| **DocBank** | Official Website + GitHub | Publicly accessible |

### ⚠️ Unclear/Possibly Restricted (1 dataset)

| Dataset | Access Status | Notes |
|---------|---------------|-------|
| **SignaTR6K** | Unclear | arXiv paper + GitHub "related implementation" - full dataset availability unclear |

### ❌ Restricted Access (2 datasets)

| Dataset | Access Method | Restriction |
|---------|---------------|-------------|
| **Marmot** | Contact Authors | Peking University - requires contacting dataset creators |
| **DISEC'13** | Contact Authors | Academic dataset - may require formal request |

---

## Phase 2 Week 1 Coverage (IQA Training Data)

### With All Datasets

| Requirement | Datasets Available | Status |
|-------------|-------------------|--------|
| **IQA Validation** | DIQA-5000 (x2), SOC, DocIQ | ✅ 10k+ images |
| **Synthetic Tools** | Genalog, DocCreator | ✅ Both available |
| **Skew Detection** | DISEC'13, Kaggle Noisy/Rotated | ✅ 2 datasets (2,150 samples) |
| **Base Clean Documents** | RVL-CDIP, Tobacco800, DocBank | ✅ 900k+ images |

### Excluding Restricted Datasets

| Requirement | Datasets Available | Status | Impact |
|-------------|-------------------|--------|--------|
| **IQA Validation** | DIQA-5000 (x2), SOC, DocIQ | ✅ 10k+ images | **No impact** |
| **Synthetic Tools** | Genalog, DocCreator | ✅ Both available | **No impact** |
| **Skew Detection** | ~~DISEC'13~~, Kaggle Noisy/Rotated | ⚠️ 1 dataset (600 samples) | **Loses "unit test" validation** |
| **Base Clean Documents** | RVL-CDIP, Tobacco800, DocBank | ✅ 900k+ images | **No impact** |

**Phase 2 Week 1 Impact**: ⚠️ **MINOR**
- Still have 600 skew images from Kaggle (real-world "integration test")
- Lose DISEC'13's 1,550 "clean room" synthetic samples for algorithm correctness
- **Workaround**: Can generate synthetic skew validation using DocCreator/Genalog

---

## Phase 3 Coverage (Layout Detection)

### With All Datasets

| Element | Datasets Available | Total Samples | Status |
|---------|-------------------|---------------|--------|
| **Tables** | DocLayNet, TableBank, PubTabNet | ~90,000+ | ✅ Excellent |
| **Figures** | DocLayNet, PubLayNet | ~60,000+ | ✅ Excellent |
| **Formulas** | Marmot, TFD-ICDAR 2019 | ~50,000 | ✅ Good |
| **Handwriting** | SignaTR6K | 6,000+ | ⚠️ Unclear access |
| **Footnotes** | DocLayNet | ~20,000 | ✅ Good |

### Excluding Restricted Datasets

| Element | Datasets Available | Total Samples | Status | Impact |
|---------|-------------------|---------------|--------|--------|
| **Tables** | DocLayNet, TableBank, PubTabNet | ~90,000+ | ✅ Excellent | **No impact** |
| **Figures** | DocLayNet, PubLayNet | ~60,000+ | ✅ Excellent | **No impact** |
| **Formulas** | ~~Marmot~~, TFD-ICDAR 2019 | ~38,000 | ✅ Good | **Loses embedded formula focus** |
| **Handwriting** | SignaTR6K (unclear) | 0-6,000 | ❌ Uncertain | **Potential gap** |
| **Footnotes** | DocLayNet | ~20,000 | ✅ Good | **No impact** |

**Phase 3 Impact**: ⚠️ **MODERATE**
- **Formulas**: Still have TFD-ICDAR 2019 (~38k expressions)
  - Lose Marmot's explicit "embedded formula" distinction (7,907 critical inline formulas)
  - **Workaround**: TFD-ICDAR 2019 distinguishes single-char vs multi-char expressions
- **Handwriting**: SignaTR6K access unclear
  - May need to identify alternative datasets (IAM, RIMES, etc.)

---

## Overall Coverage Analysis

### Publicly Accessible Coverage Summary

| Category | Fully Accessible | Restricted | Coverage with Public Only |
|----------|------------------|------------|---------------------------|
| **IQA Validation** | 3/3 (100%) | 0/3 | ✅ **100%** - No impact |
| **Synthetic Tools** | 2/2 (100%) | 0/2 | ✅ **100%** - No impact |
| **Skew Detection** | 1/2 (50%) | 1/2 | ⚠️ **50%** - Minor impact |
| **Base Documents** | 3/3 (100%) | 0/3 | ✅ **100%** - No impact |
| **Tables** | 3/3 (100%) | 0/3 | ✅ **100%** - No impact |
| **Figures** | 2/2 (100%) | 0/2 | ✅ **100%** - No impact |
| **Formulas** | 1/2 (50%) | 1/2 | ⚠️ **50%** - Moderate impact |
| **Handwriting** | 0/1 (0%) | 0/1 (unclear) | ❓ **Unknown** |
| **Footnotes** | 1/1 (100%) | 0/1 | ✅ **100%** - No impact |

**Overall**: **87.5% fully accessible** (14/16 datasets, excluding SignaTR6K as "unclear")

---

## Critical Gaps with Public-Only Datasets

### 1. Skew Detection - Minor Gap ⚠️

**What's Lost**: DISEC'13 (1,550 samples, -15° to +15°)
- "Unit test" validation for algorithm correctness
- Clean-room synthetic rotations

**What Remains**: Kaggle Noisy/Rotated (600 samples, -5° to +5°)
- Real-world "integration test"
- Noisy + rotated combination

**Mitigation Strategy**:
```python
# Generate synthetic skew validation using Genalog
from image_preprocessing_detector.augmentation import DegradationConfig

# Create synthetic skew gradient for algorithm validation
skew_angles = range(-15, 16, 1)  # -15° to +15° in 1° steps
# 31 angles × 50 clean documents = 1,550 synthetic samples
# Equivalent to DISEC'13 coverage
```

**Risk Level**: 🟡 **LOW** - Can synthesize equivalent dataset

### 2. Mathematical Formulas - Moderate Gap ⚠️

**What's Lost**: Marmot (9,482 formulas: 1,575 isolated + 7,907 embedded)
- Explicit "embedded/inline" formula distinction
- Critical for RAG (inline formulas are "RAG-killers")

**What Remains**: TFD-ICDAR 2019 (~38,000 expressions)
- Still very large dataset
- Distinguishes single-char vs multi-char expressions
- Character-level bounding boxes

**Mitigation Strategy**:
1. Use TFD-ICDAR 2019's character-level annotations to infer inline vs isolated
2. Filter for small bounding boxes (< 50px height) as proxy for inline formulas
3. Validate separately on inline-like formulas

**Risk Level**: 🟡 **LOW-MEDIUM** - TFD-ICDAR 2019 is robust alternative

### 3. Handwriting - Unclear Gap ❓

**SignaTR6K Status**: Paper on arXiv, GitHub has "related implementation"
- Dataset may or may not be publicly available
- Need to verify access before relying on it

**Alternative Public Datasets**:
- **IAM Handwriting Database**: 13,353 pages (free for research)
  - Access: https://fki.tic.heia-fr.ch/databases/iam-handwriting-database
- **RIMES Dataset**: French handwriting (free for research)
- **NIST Handwriting Forms**: US government forms (public domain)

**Mitigation Strategy**:
1. Attempt to access SignaTR6K directly
2. If unavailable, use IAM Handwriting Database
3. Focus on mixed printed/handwritten detection (not pure handwriting)

**Risk Level**: 🟡 **MEDIUM** - Alternative datasets available

---

## Recommendations

### Immediate Actions (Phase 2 Week 1)

1. **Verify SignaTR6K Access** ⚡ HIGH PRIORITY
   ```bash
   # Check if full dataset is available on GitHub
   git clone https://github.com/Naagar/Handwritten_Printed_Segmentation
   # Or contact paper authors for dataset access
   ```

2. **Use Public Datasets for MVP** ✅ RECOMMENDED
   - 14/16 datasets (87.5%) are fully public
   - Sufficient coverage for Phase 2 IQA training
   - DocLayNet + TFD-ICDAR 2019 sufficient for Phase 3

3. **Synthetic Skew Generation** 🔧 WORKAROUND
   ```python
   # Replace DISEC'13 with Genalog-generated synthetic skew
   # See image_reference_sets.md Section IV.B for methodology
   ```

### Long-Term Strategy (Phase 3+)

1. **Marmot Formula Dataset**:
   - **Option A**: Contact Peking University authors for access
   - **Option B**: Use TFD-ICDAR 2019 exclusively (sufficient for most use cases)
   - **Decision Point**: Phase 3 Week 1 (12 weeks from now)

2. **Handwriting Detection**:
   - **Option A**: Verify SignaTR6K access (check GitHub repository)
   - **Option B**: Use IAM Handwriting Database as fallback
   - **Option C**: Focus on noteshrink-based classical CV (Phase 2 approach)
   - **Decision Point**: Phase 2 Week 2 (2 weeks from now)

---

## Impact Assessment

### Phase 2 Week 1 (Current)

**Impact of Excluding Restricted Datasets**: 🟢 **MINIMAL**

| Requirement | Public Coverage | Assessment |
|-------------|----------------|------------|
| IQA Training | 100% (10k+ images) | ✅ No impact |
| Synthetic Tools | 100% (2 tools) | ✅ No impact |
| Skew Validation | 50% (600 samples) | ⚠️ Workaround available |
| Base Documents | 100% (900k images) | ✅ No impact |

**Conclusion**: ✅ **Can proceed with Phase 2 Week 1 using public datasets only**

### Phase 3 (Weeks 12-16)

**Impact of Excluding Restricted Datasets**: 🟡 **LOW-MODERATE**

| Element | Public Coverage | Assessment |
|---------|----------------|------------|
| Tables | 100% (~90k samples) | ✅ No impact |
| Figures | 100% (~60k samples) | ✅ No impact |
| Formulas | 50% (~38k samples) | ⚠️ Alternative available |
| Handwriting | Unclear | ❓ Need verification |

**Conclusion**: ⚠️ **Verify SignaTR6K + IAM alternatives before Phase 3**

---

## Summary

**Good News**: 🎉
- **87.5% of datasets fully public** (14/16)
- **Phase 2 Week 1 unaffected** - all critical IQA datasets accessible
- **Strong table/figure coverage** - DocLayNet alone provides 80k+ samples
- **Synthetic tools fully available** - Genalog + DocCreator

**Areas of Concern**: ⚠️
- **Skew detection**: Lose DISEC'13 but can synthesize equivalent
- **Formula detection**: Lose Marmot's inline focus but TFD-ICDAR robust
- **Handwriting**: SignaTR6K access unclear - need alternatives

**Recommendation**: ✅ **Proceed with public datasets**, verify handwriting alternatives by Phase 2 Week 2.

---

**Last Updated**: 2025-01-15
**Next Review**: Phase 2 Week 2 (SignaTR6K verification)
