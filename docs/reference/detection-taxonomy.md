---
schema_type: common
title: "Detection Taxonomy - Complete Classification of Document Quality Issues"
tags:
  - reference
  - taxonomy
status: published
owner: docs-team
purpose: Reference documentation for detection taxonomy - complete classification of document quality issues.
---

> **Review Needed (2026-02-09)**: This taxonomy may need alignment with `config/layout_taxonomy.yaml` and the SigLIP 2 multi-task architecture. Has 15+ inbound references across docs -- update content in place, do not move.

**Version**: 3.0 (Research-Aligned)
**Date**: 2025-11-13
**Status**: 🚧 **In Progress** - Migration from v2 functional requirements

## Purpose

This document provides a comprehensive taxonomy of all document quality issues, layout elements, and specialized content that the Image Preprocessing Detector must identify. Issues are classified by:

1. **Priority**: P0 (Critical), P1 (High), P2 (Medium), P3 (Low)
2. **Action Type**: Detect-only vs Detect-and-Correct
3. **Detection Method**: Classical CV, ML, or Hybrid
4. **Phase**: When the capability will be implemented

## Overview

**Total Issues**: 30+ detection categories across 3 domains
**Coverage Status**:

- ✅ **Implemented**: 12 (Phase 0-1 complete)
- 🚧 **In Progress**: 6 (Phase 2 ML IQA)
- ⏳ **Planned**: 12+ (Phase 3-5)

## 1. Image Quality Issues (IQA)

### P0 - Critical (Must-Have for Production)

| Issue | Detection | Correction | Method | Phase | Status |
|-------|-----------|------------|--------|-------|--------|
| **Blur** | Laplacian variance, frequency domain | Sharpening (unsharp mask, deconvolution) | Classical + ML | 1, 2 | ✅ Classical done, 🚧 ML in progress |
| **Skew** | Hough transform (lines), projection profile | Rotation (affine transform) | Classical + ML | 1, 2 | ✅ Classical done, 🚧 ML in progress |
| **Low Contrast** | Histogram analysis, RMS contrast | CLAHE, histogram equalization | Classical + ML | 1, 2 | ✅ Classical done, 🚧 ML in progress |
| **Low Resolution** | DPI metadata, pixel density | Upscaling to 300 DPI (OpenCV algorithms) | Classical | 1B | ✅ Complete |
| **Binarization Quality** | Threshold analysis, bimodal histogram | Adaptive thresholding (Otsu, Sauvola, Niblack) | Classical + ML | 1, 2 | ⏳ Planned Phase 2 |
| **Uneven Illumination** | Local variance, shadow detection | Illumination normalization, adaptive histogram | Classical + ML | 2 | ⏳ Planned Phase 2 |

**Research Citations**:

- Blur: "No-Reference Image Blur Assessment Using Multiscale Gradient" (IEEE 2017)
- Skew: "A robust skew detection algorithm for grayscale document images" (Pattern Recognition 2018)
- Binarization: "Degraded Historical Document Binarization: A Review" (PMC 2021)
- Illumination: "Robust Document Image Binarization Technique for Degraded Document Images" (IEEE 2013)

**Key Requirements**:

- **Multi-label classification**: Document can have multiple defects simultaneously
- **Confidence scores**: All detections include confidence [0-1]
- **Spatial localization**: Where possible, identify affected regions (bounding boxes)

### P1 - High (Important for Quality)

| Issue | Detection | Correction | Method | Phase | Status |
|-------|-----------|------------|--------|-------|--------|
| **Noise** | Connected components, SNR estimation | Denoising (bilateral filter, NLM, BM3D) | Classical + ML | 1, 2 | ✅ Classical done, 🚧 ML in progress |
| **Bleed-Through** | Dual-side comparison, frequency analysis | Bleed-through suppression algorithms | ML | 3 | ⏳ Planned |
| **Warping/Curvature** | Line straightness, curve fitting | Dewarping (polynomial regression, DocUNet) | ML | 3 | ⏳ Planned |
| **Watermarks** | Frequency domain, repeated patterns | Detect-only (flag for VLM processing) | Classical + ML | 3 | ⏳ Planned |

**Research Citations**:

- Bleed-through: "Reduction of bleed-through in scanned manuscript documents" (Pattern Recognition 2011)
- Warping: "Straightening warped text lines using polynomial regression" (DAS 2016)
- Warping (DL): "DocUNet: Document Image Unwarping via A Stacked U-Net" (CVPR 2018)

**Key Requirements**:

- **Bleed-through**: Requires dual-side scanning (if available) or single-side frequency analysis
- **Warping**: Critical for book scans (spine curvature), mobile captures
- **Watermarks**: Detect-only - flag regions for VLM to interpret semantics

### P2 - Medium (Nice-to-Have)

| Issue | Detection | Correction | Method | Phase | Status |
|-------|-----------|------------|--------|-------|--------|
| **Perspective Distortion** | Corner detection, parallel line analysis | Perspective correction (homography transform) | Classical + ML | 2 | 🚧 ML in progress |
| **Background Patterns** | Frequency domain, texture analysis | Background subtraction | Classical | 3 | ⏳ Planned |
| **Stamps/Seals** | Circle detection (Hough), color analysis | Detect-only (flag region) | Classical | 3 | ⏳ Planned |
| **Signatures** | Continuous stroke detection, ink analysis | Detect-only (flag region) | ML | 3 | ⏳ Planned |
| **Margin Annotations** | Edge detection, spatial isolation | Detect-only (separate from main text) | Classical + ML | 4 | ⏳ Planned |

**Research Citations**:

- Perspective: "Automatic Document Image Rectification Using Geometric Features" (ICDAR 2017)
- Stamps: "Automatic Detection and Recognition of Official Seals in Document Images" (ICDAR 2019)

### P3 - Low (Future Enhancements)

| Issue | Detection | Correction | Method | Phase | Status |
|-------|-----------|------------|--------|-------|--------|
| **Color Bleeding** | Color channel separation, ICC profile analysis | Color normalization | Classical | 4+ | ⏳ Planned |
| **Highlighted Text** | Color analysis, saturation detection | Detect-only (flag importance) | Classical | 4+ | ⏳ Planned |
| **Strikethrough/Redactions** | Line detection over text | Detect-only (mark as deleted) | Classical | 4+ | ⏳ Planned |
| **Fading** | Local intensity variance | Contrast enhancement (adaptive) | Classical | 4+ | ⏳ Planned |

---

## 2. Layout Elements (Object Detection)

### P0 - Critical (RAG Quality)

| Element | Detection | Correction | Method | Phase | Status |
|---------|-----------|------------|--------|-------|--------|
| **Text Blocks** | YOLOv8, LayoutLMv3 | N/A (detect-only) | ML | 3 | ⏳ Planned |
| **Titles/Headings** | YOLOv8, font analysis | N/A (detect-only) | ML | 3 | ⏳ Planned |
| **Paragraphs** | YOLOv8, whitespace analysis | N/A (detect-only) | ML | 3 | ⏳ Planned |
| **Lists** | YOLOv8, bullet/number detection | N/A (detect-only) | ML | 3 | ⏳ Planned |
| **Tables** | YOLOv8, TableTransformer | Structure preservation (JSON) | ML | 3 | ⏳ Planned |
| **Figures/Images** | YOLOv8, embedded image detection | Extract for separate processing | ML | 3 | ⏳ Planned |
| **Captions** | YOLOv8, proximity to figures | Link to parent figure | ML | 3 | ⏳ Planned |
| **Parasitic Content** | Pattern matching across pages (headers/footers) | Remove from output | ML | 3 | ⏳ Planned |
| **Page Boundaries** | Page metadata, PDF structure | Smart chunking (don't split mid-sentence) | Classical | 1B | ✅ Complete |

**Research Citations**:

- Layout: "LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking" (ACM 2022)
- Tables: "TableFormer: Table Structure Understanding with Transformers" (CVPR 2022)
- RAG Issues: "OCR Hinders RAG: Evaluating the Cascading Impact of OCR on RAG" (arXiv 2024)

**Key Requirements**:

- **COCO Format**: Bounding boxes as `[x, y, width, height]` for LayoutParser compatibility
- **Confidence Scores**: All detections include confidence [0-1]
- **Relationship Linking**: Captions linked to figures, footnotes to references

### P1 - High (Semantic Understanding)

| Element | Detection | Correction | Method | Phase | Status |
|---------|-----------|------------|--------|-------|--------|
| **Footnotes** | Superscript numbers, spatial proximity | Link to reference in main text | ML | 3 | ⏳ Planned |
| **Multi-Column Layout** | Column detection, reading order | Output correct reading order | ML | 3 | ⏳ Planned |
| **Section Headers** | Font size, whitespace, formatting | Hierarchical structure (H1, H2, H3) | ML | 3 | ⏳ Planned |
| **Formulas** | DocLayNet Formula class, symbol detection | Detect-only (flag for specialized OCR) | ML | 3 | ⏳ Planned |
| **Diagrams** | Visual complexity analysis | Detect-only (flag for VLM) | ML | 4 | ⏳ Planned |

**Research Citations**:

- Footnotes: "Footnote Detection and Recognition in Historical Documents" (ICDAR 2019)
- Reading Order: "Reading Order Detection in Complex Layouts" (IJDAR 2021)

### P2 - Medium (Advanced Features)

| Element | Detection | Correction | Method | Phase | Status |
|---------|-----------|------------|--------|-------|--------|
| **Cross-References** | Reference pattern matching ("See Figure 3") | Resolve internal references | ML | 4 | ⏳ Planned |
| **Sidebars** | Spatial separation, background shading | Mark as supplementary content | ML | 4 | ⏳ Planned |
| **Pull Quotes** | Large font, indentation, quotation marks | Distinguish from main text | Classical | 4 | ⏳ Planned |
| **Vertical Text** | Text orientation detection (Asian scripts) | Rotate before OCR | Classical | 3 | ⏳ Planned |

---

## 3. Specialized Content Detection

### P0 - Critical (Production Blocking)

| Content Type | Detection | Correction | Method | Phase | Status |
|--------------|-----------|------------|--------|-------|--------|
| **PDF Type** | PyMuPDF text extraction, embedded images | Route to appropriate pipeline | Classical | 1 | ✅ Complete |
| **Text Presence** | Ensemble heuristics (stroke density, edges) | Route to text vs image pipeline | Classical | 1 | ✅ Complete |
| **Language/Script** | fastText, langdetect | Trigger language-specific OCR | Classical | 1 | ✅ Complete |
| **DPI** | PyMuPDF metadata, pixel density | Upscale to 300 DPI if needed | Classical | 1B | ✅ Complete |

**Related ADRs**:

- [ADR-008](ADRs/0008-multi-stage-pipeline-architecture.md): Text detection fork architecture
- [ADR-007](ADRs/0007-hybrid-iqa-approach.md): Embedded image detection

### P1 - High (Quality Impact)

| Content Type | Detection | Correction | Method | Phase | Status |
|--------------|-----------|------------|--------|-------|--------|
| **Handwriting** | CNN classifier (stroke characteristics) | Detect-only (flag for VLM or specialized OCR) | ML | 3 | ⏳ Planned |
| **Mixed Content** | Hybrid detection (text + handwriting) | Separate processing paths | ML | 3 | ⏳ Planned |
| **Embedded Images in Text Docs** | YOLOv8 Figure detection | Extract and run IQA separately | ML | 3 | ⏳ Planned |
| **Code Blocks** | Monospace font, indentation, syntax patterns | Preserve formatting | ML | 4 | ⏳ Planned |

**Research Citations**:

- Handwriting: "A Survey on Handwriting Recognition" (IEEE Access 2019)
- Mixed Content: "Hybrid Text/Handwriting Recognition in Document Images" (ICDAR 2021)

### P2 - Medium (Domain-Specific)

| Content Type | Detection | Correction | Method | Phase | Status |
|--------------|-----------|------------|--------|-------|--------|
| **Music Notation** | Staff line detection, note symbols | Detect-only (flag for OMR) | ML | 5 | ⏳ Planned |
| **Chemical Formulas** | Symbol detection, subscript/superscript | Detect-only (flag for specialized OCR) | ML | 5 | ⏳ Planned |
| **Circuit Diagrams** | Symbol library matching | Detect-only (flag for VLM) | ML | 5 | ⏳ Planned |
| **Maps** | Geographic feature detection | Detect-only (flag for GIS processing) | ML | 5 | ⏳ Planned |

---

## Detection Methods and Technologies

### Classical Computer Vision

**Advantages**:

- ✅ Fast inference (< 50ms per page)
- ✅ No training data required
- ✅ Interpretable (clear thresholds)
- ✅ Low memory footprint

**Disadvantages**:

- ❌ Requires manual threshold tuning
- ❌ Less robust to edge cases
- ❌ Fixed feature extraction

**Used For**:

- Phase 1: Blur, skew, contrast, noise, DPI
- Supplementary: Text presence gate, PDF type classification

### Machine Learning (Deep Learning)

**Advantages**:

- ✅ Learns from data (no manual thresholds)
- ✅ Robust to variations
- ✅ State-of-the-art accuracy

**Disadvantages**:

- ❌ Requires training data (50k+ samples)
- ❌ Slower inference (100-300ms per page)
- ❌ Higher memory usage (model size)

**Architectures**:

- **IQA**: MobileNetV3, EfficientNet-B0 (multi-label classification)
- **Layout**: YOLOv8n, LayoutLMv3 (object detection)
- **Tables**: TableTransformer (structure recognition)
- **Specialized**: Custom CNNs for handwriting, formulas

**Used For**:

- Phase 2: IQA multi-defect classification
- Phase 3: Layout detection, table structure, specialized content

### Hybrid Approaches

**Strategy**: Classical detectors + ML refinement + ensemble fusion

**Example - Blur Detection**:

1. **Classical**: Laplacian variance (fast screening)
2. **ML**: MobileNetV3 multi-label IQA (confidence refinement)
3. **Fusion**: Max confidence or weighted average

**Benefits**:

- ✅ Fast screening with classical methods
- ✅ High accuracy with ML refinement
- ✅ Graceful degradation if ML fails

**Related ADR**: [ADR-014](ADRs/0014-classical-ml-hybrid-iqa.md) - Hybrid IQA ensemble

---

## Correction Methods and Technologies

### Phase 1: Classical Corrections (OpenCV)

| Issue | Correction Method | Library | Status |
|-------|-------------------|---------|--------|
| Blur | Unsharp mask, deconvolution | OpenCV | ✅ Complete |
| Skew | Affine rotation | OpenCV | ✅ Complete |
| Noise | Bilateral filter, Non-Local Means | OpenCV | ✅ Complete |
| Low Contrast | CLAHE, histogram equalization | OpenCV | ✅ Complete |
| Low Resolution | Bicubic upscaling, Lanczos | OpenCV | ✅ Complete (1B) |

### Phase 2: ML-Guided Corrections

| Issue | Correction Method | Library | Status |
|-------|-------------------|---------|--------|
| Binarization | Adaptive thresholding (Otsu, Sauvola, Niblack) | OpenCV | ⏳ Planned |
| Illumination | Illumination normalization, adaptive histogram | Custom | ⏳ Planned |
| Perspective | Homography transform (corner detection) | OpenCV | 🚧 ML detection in progress |

### Phase 3: Deep Learning Corrections

| Issue | Correction Method | Library | Status |
|-------|-------------------|---------|--------|
| Warping | DocUNet (DL-based dewarping) | Custom PyTorch | ⏳ Planned |
| Bleed-through | Bleed-through suppression CNN | Custom PyTorch | ⏳ Planned |
| Super-Resolution | ESRGAN, Real-ESRGAN | PyTorch | ⏳ Planned (Phase 4) |

**Research Citations**:

- DocUNet: "DocUNet: Document Image Unwarping via A Stacked U-Net" (CVPR 2018)
- Super-Resolution: "ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks" (ECCV 2018)

---

## Priority Classification Rationale

### P0 - Critical (Production Blocking)

**Criteria**:

- Causes complete OCR failure (e.g., severe blur, extreme skew)
- Affects majority of documents (> 30% detection rate)
- No workaround possible (must be corrected)
- Required for MVP deployment

**Examples**: Blur, skew, binarization, illumination, text presence, PDF type

### P1 - High (Quality Impact)

**Criteria**:

- Degrades OCR accuracy significantly (> 20% error rate)
- Affects specialized domains (book scans, historical documents)
- Has viable correction method
- Required for production quality

**Examples**: Warping, bleed-through, noise, watermarks, footnotes

### P2 - Medium (Feature Enhancement)

**Criteria**:

- Improves user experience but not critical
- Affects edge cases or specific document types
- Workarounds exist (manual review)
- Nice-to-have for differentiation

**Examples**: Perspective, stamps, cross-references, vertical text

### P3 - Low (Future Nice-to-Have)

**Criteria**:

- Rarely encountered (< 5% of documents)
- Minimal impact on core functionality
- High implementation cost for low benefit
- Can defer to Phase 4+

**Examples**: Color bleeding, highlighted text, music notation

---

## Detect-Only vs Detect-and-Correct

### Detect-Only (Routing Decision)

**Purpose**: Identify content that requires specialized processing or VLM interpretation

**Examples**:

- **Handwriting**: Route to VLM or specialized handwriting OCR
- **Formulas**: Route to MathPix, LaTeX generation
- **Watermarks**: Flag for VLM to extract semantic meaning
- **Stamps/Seals**: Flag region, may contain important metadata

**Output Format**:

```json
{
  "detection_type": "watermark",
  "bounding_box": [100, 200, 300, 150],
  "confidence": 0.92,
  "recommended_action": "route_to_vlm",
  "metadata": {
    "pattern_type": "repeated_text",
    "transparency": 0.3
  }
}
```

### Detect-and-Correct (Quality Enhancement)

**Purpose**: Automatically fix issues to improve OCR accuracy

**Examples**:

- **Blur**: Sharpen image before OCR
- **Skew**: Rotate to correct orientation
- **Low Contrast**: Enhance with CLAHE
- **Warping**: Dewarp curved text lines

**Output Format**:

```json
{
  "detection_type": "blur",
  "severity": 0.78,
  "correction_applied": true,
  "correction_method": "unsharp_mask",
  "confidence_improvement": 0.15,
  "transform_history": [
    {"operation": "sharpen", "params": {"radius": 1.5, "amount": 1.2}}
  ]
}
```

**Key Principle**: Only apply corrections that **improve** OCR confidence. Validate corrections with before/after quality metrics.

---

## Relationship to Functional Requirements

### Current Functional Requirements v2

**Coverage**:

- ✅ FR-1: File Handling (PDF, images)
- ✅ FR-2: PDF Type Classification
- ✅ FR-3: Image Quality Detection (partial - missing binarization, illumination, warping, bleed-through)
- ✅ FR-4: Layout Analysis (partial - missing parasitic content, footnotes, cross-references)
- ✅ FR-5: Specialized Content (partial - missing watermarks, stamps, signatures)

### Recommended Updates

**Add to FR-3 (Image Quality)**:

- FR-3.8: Binarization Quality Assessment (P0)
- FR-3.9: Illumination Uniformity Detection (P0)
- FR-3.10: Bleed-Through Detection (P1)
- FR-3.11: Warping/Curvature Detection (P1)
- FR-3.12: Perspective Distortion Detection (P2)

**Add to FR-4 (Layout)**:

- FR-4.4: Parasitic Content Detection (headers/footers) (P0)
- FR-4.5: Footnote Linking (superscript to footnote) (P1)
- FR-4.6: Figure-Caption Linking (P1)
- FR-4.7: Vertical Text Orientation Detection (P2)

**Add to FR-5 (Specialized Content)**:

- FR-5.4: Watermark Detection (P1)
- FR-5.5: Stamp/Seal Detection (P2)
- FR-5.6: Signature Detection (P2)
- FR-5.7: Margin Annotation Detection (P2)

**Add corrections** (FR-6):

- FR-6.8: Binarization Correction (adaptive thresholding)
- FR-6.9: Illumination Normalization
- FR-6.10: Dewarping (polynomial regression, DocUNet)
- FR-6.11: Perspective Correction (homography)
- FR-6.12: Bleed-through Suppression

---

## Dataset Requirements by Issue

### Training Data Requirements (Phase 2-3)

| Issue | Training Samples | Source | Annotation Method |
|-------|------------------|--------|-------------------|
| Blur | 10k+ | TableBank + augmentation | Weak supervision (Laplacian) |
| Noise | 10k+ | TableBank + augmentation | Weak supervision (SNR) |
| Skew | 10k+ | TableBank + rotation | Weak supervision (Hough) |
| Perspective | 5k+ | TableBank + affine | Weak supervision (corner detection) |
| Low Contrast | 10k+ | TableBank + brightness | Weak supervision (histogram) |
| Orientation | 5k+ | TableBank + rotation | Deterministic (rotation angles) |
| Layout Elements | 80k+ | DocLayNet COCO annotations | Ground-truth COCO JSON |
| Tables | 40k+ | TableBank, PubTabNet | Ground-truth structure |
| Handwriting | 10k+ | SignaTR6K | Ground-truth labels |

**Related ADR**: [ADR-029](ADRs/0029-phase2-dataset-selection-strategy.md) - Three-tier dataset strategy

### Benchmark Data Requirements

| Issue | Benchmark Dataset | Size | Purpose |
|-------|-------------------|------|---------|
| IQA | LIVE, CSIQ, LIVE Challenge | 2,807 images | Ground-truth MOS/DMOS scores |
| Layout | DocLayNet | 80,863 pages | COCO annotations |
| Tables | TableBank | 417,234 tables | Structure validation |
| Language | Wili-2018 | 235,000 paragraphs | Language ID accuracy |
| Handwriting | SignaTR6K | 6,000 signatures | Classification accuracy |

---

## Performance Targets by Phase

### Phase 1 (Classical Methods)

| Issue | Target Precision | Target Recall | Target F1 | Status |
|-------|------------------|---------------|-----------|--------|
| Blur | > 0.85 | > 0.80 | > 0.82 | ✅ 0.87 achieved |
| Skew | > 0.90 | > 0.85 | > 0.87 | ✅ 0.92 achieved |
| Contrast | > 0.80 | > 0.75 | > 0.77 | ✅ 0.83 achieved (after calibration) |
| Noise | > 0.80 | > 0.75 | > 0.77 | ✅ 0.81 achieved |

**Related ADR**: [ADR-011](ADRs/0011-hybrid-validation-strategy.md) - Real-world calibration critical

### Phase 2 (ML IQA)

| Metric | Target | Notes |
|--------|--------|-------|
| **mAP** (multi-label) | > 0.88 | Average precision across 6 defects |
| **Per-class F1** | > 0.85 | All defects individually |
| **ECE** (calibration) | < 0.1 | Well-calibrated probabilities |
| **Pearson Correlation** | > 0.75 | vs LIVE/CSIQ ground-truth |

### Phase 3 (Layout Detection)

| Metric | Target | Notes |
|--------|--------|-------|
| **mAP@.50** (layout) | > 0.82 | DocLayNet benchmark |
| **mAP@.75** (layout) | > 0.70 | Strict IoU threshold |
| **Table Detection F1** | > 0.90 | TableBank validation |
| **Reading Order Accuracy** | > 0.95 | Multi-column documents |

---

## References

**Research Papers**:

- OCR/RAG: "OCR Hinders RAG: Evaluating the Cascading Impact of OCR on RAG" (arXiv 2024)
- Binarization: "Degraded Historical Document Binarization: A Review" (PMC 2021)
- Dewarping: "DocUNet: Document Image Unwarping via A Stacked U-Net" (CVPR 2018)
- Layout: "LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking" (ACM 2022)

**Internal Documentation**:

- [docs/requirements/functional_requirements_v2.md](requirements/functional_requirements_v2.md): Current FR specification
- [data/README.md](../data/README.md): Three-tier dataset strategy
- [benchmarks/registry.yml](../benchmarks/registry.yml): Benchmark suite definitions

**Architecture Decision Records**:

- [ADR-011](ADRs/0011-hybrid-validation-strategy.md): Hybrid validation (synthetic + real-world)
- [ADR-029](ADRs/0029-phase2-dataset-selection-strategy.md): Three-tier dataset strategy
- [ADR-031](ADRs/0031-comprehensive-benchmarking-framework.md): Registry-based benchmarking
- [ADR-014](ADRs/0014-classical-ml-hybrid-iqa.md): Hybrid IQA ensemble approach

---

**Created**: 2025-11-13 (Phase 2 Week 1 - Documentation Phase)
**Status**: 🚧 **In Progress** - Research-aligned taxonomy complete, FR updates pending
**Next Steps**: Update functional_requirements_v2.md with missing issues (FR-3.8 through FR-5.7)
**Next Review**: Phase 2 Week 3 (after FR updates complete)
