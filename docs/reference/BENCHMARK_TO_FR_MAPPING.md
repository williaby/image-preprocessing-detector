# Benchmark-to-Functional Requirement Mapping

**Version**: 1.0
**Date**: 2025-11-14
**Purpose**: Ensure every benchmark validates specific FRs, and every FR has appropriate benchmark coverage

## Purpose

This document provides bidirectional traceability between:
1. **Functional Requirements** → Which benchmarks validate them
2. **Benchmarks** → Which FRs they measure effectiveness against
3. **Coverage Gaps** → FRs without benchmarks, benchmarks without FR justification

**Key Principle**:
- ❌ **If a benchmark doesn't cover an FR** → Question why we're using it
- ❌ **If an FR doesn't have benchmark coverage** → Identify gap and determine if one is needed

---

## Benchmark Registry Overview

| Benchmark | Primary FRs | Secondary FRs | Purpose | Status |
|-----------|-------------|---------------|---------|--------|
| **Synthetic IQA (Blur)** | FR-3.1 | FR-2.2, FR-6.1 | Validate blur detection + correction effectiveness | ✅ Active |
| **Synthetic IQA (Skew)** | FR-3.2 | FR-2.2, FR-6.2 | Validate skew detection + correction effectiveness | ✅ Active |
| **Synthetic IQA (Noise)** | FR-3.3 | FR-2.2, FR-6.3 | Validate noise detection + correction effectiveness | ✅ Active |
| **Synthetic IQA (Contrast)** | FR-3.7 | FR-2.2, FR-6.4 | Validate contrast assessment + enhancement | ✅ Active |
| **LIVE IQA** | FR-3.1, FR-3.3, FR-3.7 | FR-2.3 | External validation against natural image quality (fallback until DIQA-5000) | ✅ Active |
| **CSIQ IQA** | FR-3.1, FR-3.3, FR-3.7 | FR-2.3 | External validation against natural image quality (fallback until DIQA-5000) | ✅ Active |
| **LIVE Challenge** | FR-3.1, FR-3.3 | FR-2.3 | Real-world mobile capture validation (authentic defects) | ✅ Active |
| **DocLayNet Layout** | FR-4.2 | FR-4.1, FR-4.3 | Layout element detection (11 classes), COCO format validation | ✅ Active |
| **TableBank** | FR-4.2 (Table class) | FR-4.11 | Table detection accuracy (part of layout pipeline) | ⏳ Planned |
| **PubTabNet** | FR-4.11 | FR-4.2 | Table structure extraction (cells, rows, columns) | ⏳ Planned |
| **FinTabNet** | FR-4.11 | — | Financial table structure (domain-specific validation) | ⏳ Planned |
| **OmniDocBench** | FR-4.2, FR-4.11, FR-5.1 | FR-2.3, FR-3.14, FR-4.6 | **PRIMARY** comprehensive end-to-end validation (layout + text + tables + formulas) | ⏳ Planned |
| **OHR-Bench** | FR-4.4 | FR-3.14, FR-4.12 | **CRITICAL** RAG-specific validation (OCR quality impact on retrieval/generation) | ⏳ Planned |
| **SignaTR6K** | FR-5.2, FR-4.8 | — | Handwriting vs printed text classification | ⏳ Planned |
| **WiLI-2018** | FR-5.3 | — | Language detection (235 languages) | ⏳ Planned |
| **COCO-Text** | FR-4.8 (text detection) | FR-5.3 | Text detection in natural scenes (edge case validation) | ⏳ Planned |

---

## Phase 1-2: Image Quality Assessment (IQA)

### FR-3.1: Blur Detection

**Requirement**: Detect and classify blur defects (Gaussian, motion, defocus) with >85% F1

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **Synthetic IQA (Blur)** | Internal | Validate classical detection accuracy | Blur F1 > 0.85, Correlation r > 0.85 | ✅ Active |
| **LIVE IQA** | External | Cross-validate against ground-truth DMOS (Gaussian blur subset) | Pearson r > 0.75 | ✅ Active |
| **DIQA-5000** | External | **PRIMARY** document-specific blur validation (replaces LIVE when released) | Document blur F1 > 0.85 | ⚠️ Pending Release |

**Gap Analysis**:
- ✅ **Classical detection**: Covered by Synthetic IQA
- ✅ **External validation**: LIVE (fallback), DIQA-5000 (future primary)
- ⚠️ **ML detection (Phase 2)**: No specific benchmark for MobileNetV3 multi-label classification → **Use Synthetic IQA test split**

---

### FR-3.2: Skew Detection

**Requirement**: Detect document rotation (>2°) with >90% precision

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **Synthetic IQA (Skew)** | Internal | Validate Hough transform + ML detection | Skew F1 > 0.87, Angle MAE < 0.5° | ✅ Active |
| **DocLayNet PDFs** | External | Real-world skew validation (scanned documents) | Skew F1 > 0.85 | ⏳ Planned |
| **DIQA-5000** | External | Document-specific skew validation (when released) | Skew F1 > 0.85 | ⚠️ Pending Release |

**Gap Analysis**:
- ✅ **Synthetic validation**: Covered
- ⚠️ **Real-world validation**: DocLayNet not yet used for skew-specific benchmark → **Add skew benchmark suite**

---

### FR-3.3: Noise Detection

**Requirement**: Detect noise artifacts (Gaussian, salt-and-pepper, compression) with >80% F1

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **Synthetic IQA (Noise)** | Internal | Validate noise detection accuracy | Noise F1 > 0.77 | ✅ Active |
| **LIVE IQA** | External | Cross-validate against white noise DMOS | Pearson r > 0.75 | ✅ Active |
| **CSIQ** | External | Cross-validate against pink noise DMOS | Pearson r > 0.75 | ✅ Active |

**Gap Analysis**:
- ✅ **Covered** - but LIVE/CSIQ are natural images, not documents
- ⚠️ **Document-specific**: Need DIQA-5000 for document noise validation

---

### FR-3.7: Contrast Assessment

**Requirement**: Assess contrast quality with >80% F1

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **Synthetic IQA (Contrast)** | Internal | Validate contrast detection | Contrast F1 > 0.77 | ✅ Active |
| **CSIQ** | External | Cross-validate against contrast degradation DMOS | Pearson r > 0.75 | ✅ Active |
| **DIQA-5000** | External | Document-specific contrast/color fidelity validation | Contrast F1 > 0.80 | ⚠️ Pending Release |

**Gap Analysis**:
- ✅ **Covered** - but CSIQ is natural images
- ⚠️ **Document-specific**: DIQA-5000 needed

---

## Phase 3: Layout Detection

### FR-4.1: Layout Detection Model

**Requirement**: YOLOv8-based layout detection with mAP@.50 > 0.82

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **DocLayNet (val_docwise)** | External | Primary layout detection validation (11 classes) | mAP@.50 > 0.82, mAP@[.5:.95] > 0.80 | ⏳ Planned |
| **OmniDocBench** | External | **COMPREHENSIVE** multi-domain layout validation | Layout mAP > 0.82 | ⏳ Planned |

**Gap Analysis**:
- ✅ **Covered** - DocLayNet is gold standard, OmniDocBench adds multi-domain validation

---

### FR-4.2: Layout Element Detection (11 Classes)

**Requirement**: Detect 11 DocLayNet element types (Text, Title, List, Table, Picture, Caption, Formula, Footnote, Page-Header, Page-Footer, Section-Header)

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **DocLayNet (val_docwise)** | External | Per-class AP validation | AP > 0.75 for all 11 classes | ⏳ Planned |
| **OmniDocBench** | External | Cross-domain per-class validation | Per-class AP > 0.70 | ⏳ Planned |

**Gap Analysis**:
- ✅ **Covered** - DocLayNet provides ground truth for all 11 classes

---

### FR-4.4: RAG-Specific Document Quality Score

**Requirement**: Predict retrieval-readiness score based on preprocessing quality

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **OHR-Bench** | External | **CRITICAL** RAG-specific validation (OCR quality → retrieval/generation impact) | NDCG@5 > 0.74, ROE < 5% | ⏳ Planned |

**Gap Analysis**:
- ✅ **NEWLY COVERED** - OHR-Bench is the **ONLY** benchmark measuring cascading OCR→RAG impact
- ⚠️ **No other benchmarks available** - OHR-Bench is unique in this domain

**Justification**: Reading order errors cause 5-29% RAG performance loss (per OHR-Bench research). This is **MORE CRITICAL** than individual quality defects.

---

### FR-4.8: Handwriting Detection in Mixed Documents

**Requirement**: Detect handwritten regions in mixed documents with >95% accuracy

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **SignaTR6K** | External | Handwriting vs printed text classification | F1 > 0.95 | ⏳ Planned |
| **OmniDocBench (handwriting subset)** | External | Mixed document handwriting detection | F1 > 0.90 | ⏳ Planned |

**Gap Analysis**:
- ✅ **Covered** - SignaTR6K provides ground truth for 6k signatures

---

### FR-4.11: Table Structure Extraction

**Requirement**: Extract table structure (cells, rows, columns) with F1 > 0.85

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **PubTabNet** | External | Table structure extraction (510k tables) | TEDS > 0.90 | ⏳ Planned |
| **FinTabNet** | External | Financial table structure (domain-specific) | TEDS > 0.85 | ⏳ Planned |
| **OmniDocBench (table subset)** | External | Cross-domain table structure validation | TEDS > 0.90 | ⏳ Planned |

**Gap Analysis**:
- ✅ **Covered** - PubTabNet is gold standard, FinTabNet adds financial domain

---

### FR-4.12: Reading Order Prediction

**Requirement**: Predict correct reading order for multi-column layouts

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **ROOR** | External | Reading order recognition (multi-column, complex layouts) | ROE < 5% | ⏳ Planned (ELEVATED) |
| **OHR-Bench** | External | Reading order error impact on RAG performance | ROE < 5% | ⏳ Planned |

**Gap Analysis**:
- ✅ **NEWLY COVERED** - ROOR elevated from Phase 4-5 to Phase 3 due to OHR-Bench findings
- ⚠️ **CRITICAL**: 5-29% RAG performance loss from reading order errors

---

## Phase 3: Specialized Content Detection

### FR-5.1: Mathematical Content Detection

**Requirement**: Detect mathematical formulas and equations

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **OmniDocBench (formula subset)** | External | Formula detection (CDM metric) | CDM > 0.85 | ⏳ Planned |

**Gap Analysis**:
- ✅ **Covered** - OmniDocBench includes formula annotations

---

### FR-5.2: Handwritten Content Detection

**Requirement**: Detect handwriting regions (signatures, notes, annotations)

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **SignaTR6K** | External | Signature detection (6k samples) | F1 > 0.95 | ⏳ Planned |

**Gap Analysis**:
- ⚠️ **Partial coverage** - SignaTR6K covers signatures, not margin notes/annotations
- ❌ **Missing**: No benchmark for margin annotation detection → **Identify gap**

---

### FR-5.3: Language Detection

**Requirement**: Detect document language (235 languages) with >95% accuracy

**Benchmarks**:

| Benchmark | Type | Purpose | Target Metric | Status |
|-----------|------|---------|---------------|--------|
| **WiLI-2018** | External | Language identification (235 languages) | Accuracy > 0.95 | ⏳ Planned |

**Gap Analysis**:
- ✅ **Covered** - WiLI-2018 is comprehensive

---

## Benchmark Gaps (FRs Without Benchmarks)

| FR | Requirement | Benchmark Status | Recommended Action |
|----|-------------|------------------|-------------------|
| **FR-3.4** | Image Resolution Detection | ❌ No specific benchmark | Use synthetic downsampled images (internal) |
| **FR-3.5** | DPI Detection | ❌ No benchmark | Use mixed-DPI corpus validation (internal) |
| **FR-3.6** | DPI Upscaling | ❌ No benchmark | Use before/after PSNR/SSIM validation (internal) |
| **FR-3.8** | Binarization Quality | ❌ No benchmark | **NEEDED** - Yale historical manuscripts or DIBCO (Phase 2+) |
| **FR-3.9** | Illumination Uniformity | ❌ No benchmark | **NEEDED** - Mobile capture dataset (Phase 2+) |
| **FR-3.10** | Bleed-Through Detection | ❌ No benchmark | **NEEDED** - Historical manuscript dataset (Phase 3+) |
| **FR-3.11** | Warping/Curvature | ✅ **AnyPhotoDoc 6300** | Available (Phase 3) |
| **FR-3.12** | Perspective Distortion | ❌ No benchmark | SmartDoc dataset (optional Phase 2+) |
| **FR-3.14** | Hybrid IQA on Embedded Images | ❌ No specific benchmark | **Use OmniDocBench** (embedded images in documents) |
| **FR-5.4** | Watermark Detection | ❌ No benchmark | **Synthetic watermarks** (internal, Phase 3) |
| **FR-5.5** | Stamp/Seal Detection | ⚠️ Training only (StaVer+DDI-100) | **NEEDED** - No validation benchmark |
| **FR-5.6** | Signature Detection | ✅ **SignaTR6K** | Available |
| **FR-5.7** | Margin Annotation Detection | ❌ No benchmark | **NEEDED** - Historical manuscript corpus |

---

## Benchmark Justification (Why Each Benchmark)

### LIVE/CSIQ/LIVE Challenge

**Purpose**: External IQA validation against human-annotated quality scores
**FRs Covered**: FR-3.1 (Blur), FR-3.3 (Noise), FR-3.7 (Contrast)
**Justification**: Gold standard for IQA research, enables peer comparison
**Limitation**: Natural images, not document-specific → **DIQA-5000 will replace**
**Keep?**: ✅ Yes (until DIQA-5000 releases)

### DIQA-5000 (Pending Release)

**Purpose**: **PRIMARY** document-specific IQA validation
**FRs Covered**: FR-3.1, FR-3.2, FR-3.3, FR-3.7
**Justification**: Only document-specific IQA benchmark with 3-dimension quality scores
**Status**: ⚠️ Pending release (Sept 2025 arXiv paper)
**Keep?**: ✅ Yes - **WILL REPLACE** LIVE/CSIQ when available

### DocLayNet

**Purpose**: Layout detection gold standard
**FRs Covered**: FR-4.1, FR-4.2
**Justification**: 80k+ annotated pages, 11-class COCO format, industry standard
**Keep?**: ✅ Yes - primary layout benchmark

### OmniDocBench

**Purpose**: **COMPREHENSIVE** end-to-end multi-domain validation
**FRs Covered**: FR-4.2 (layout), FR-4.11 (tables), FR-5.1 (formulas), FR-3.14 (composite)
**Justification**: Only benchmark covering ALL document understanding tasks in one dataset
**Keep?**: ✅ Yes - **CRITICAL** for holistic validation

### OHR-Bench

**Purpose**: **CRITICAL** RAG-specific OCR quality validation
**FRs Covered**: FR-4.4 (RAG DQS), FR-4.12 (reading order)
**Justification**: **ONLY** benchmark measuring cascading OCR→RAG impact (5-29% performance loss from reading order errors)
**Keep?**: ✅ Yes - **CRITICAL** (no alternative exists)

### SignaTR6K

**Purpose**: Handwriting vs printed text classification
**FRs Covered**: FR-5.2 (handwriting), FR-4.8 (mixed documents)
**Justification**: 6k signatures with ground truth
**Keep?**: ✅ Yes

### WiLI-2018

**Purpose**: Language identification (235 languages)
**FRs Covered**: FR-5.3 (language detection)
**Justification**: Comprehensive language coverage, enables multi-lingual routing
**Keep?**: ✅ Yes

### TableBank / PubTabNet / FinTabNet

**Purpose**: Table structure extraction validation
**FRs Covered**: FR-4.11 (table structure)
**Justification**:
- **PubTabNet**: 510k tables with cell-level annotations (primary)
- **FinTabNet**: Financial domain specialization
- **TableBank**: Table detection (part of layout pipeline)
**Keep?**: ✅ Yes - complementary coverage

### COCO-Text

**Purpose**: Text detection in natural scenes
**FRs Covered**: FR-4.8 (text detection edge cases)
**Justification**: Validates text detection robustness in challenging conditions
**Keep?**: ⚠️ **QUESTIONABLE** - Natural scenes, not documents → **Consider removing**

---

## Coverage Summary

| FR Category | Total FRs | Benchmarked | Gaps | Coverage % |
|-------------|-----------|-------------|------|------------|
| **File Handling** | 2 | 0 | 2 | 0% (internal validation only) |
| **PDF Classification** | 2 | 0 | 2 | 0% (internal validation only) |
| **Image Quality (IQA)** | 12 | 6 | 6 | 50% |
| **Layout Analysis** | 13 | 7 | 6 | 54% |
| **Specialized Content** | 7 | 3 | 4 | 43% |
| **Corrections** | 12 | 0 | 12 | 0% (before/after internal validation) |
| **TOTAL** | 48 | 16 | 32 | **33%** |

---

## Recommendations

### High Priority (Add Benchmarks)

1. **FR-3.8 (Binarization)**: Add DIBCO or Yale historical manuscript benchmark (Phase 2)
2. **FR-3.9 (Illumination)**: Add mobile capture dataset with ground truth (Phase 2)
3. **FR-5.5 (Stamps)**: Identify or create validation benchmark (Phase 3)
4. **FR-5.7 (Margin Annotations)**: Historical manuscript corpus (Phase 3)

### Medium Priority (Enhance Existing)

5. **FR-3.2 (Skew)**: Add DocLayNet skew-specific benchmark suite
6. **FR-3.14 (Hybrid IQA)**: Explicitly use OmniDocBench embedded images

### Low Priority (Consider Removing)

7. **COCO-Text**: Natural scenes benchmark - **questionable document relevance** → Consider removing if not actively used

### Correction FRs (Internal Validation)

- All correction FRs (FR-6.x) use **before/after quality metrics** (PSNR, SSIM, OCR accuracy improvement)
- No external benchmarks needed - internal validation sufficient

---

## Related Documentation

- [docs/reference/TRAINING_DATA_GAP_ANALYSIS.md](TRAINING_DATA_GAP_ANALYSIS.md) - Priority document type coverage gaps and COCO-Text evaluation
- [docs/reference/document-type-coverage.md](document-type-coverage.md) - Training dataset to FR mapping
- [docs/ADRs/0031-comprehensive-benchmarking-framework.md](../ADRs/0031-comprehensive-benchmarking-framework.md) - Benchmarking architecture
- [benchmarks/registry.yml](../../benchmarks/registry.yml) - Benchmark suite definitions
- [docs/requirements/functional_requirements_v2.md](../requirements/functional_requirements_v2.md) - Complete FR specification

---

**Created**: 2025-11-14
**Status**: ✅ Complete - All benchmarks mapped to FRs, gaps identified
**Next Steps**: Add missing benchmarks (binarization, illumination, stamps, margin annotations)
**Next Review**: Phase 3 Week 1 (after new benchmark integration)
