---
title: Project A to Project B Handoff Specification
schema_type: planning
status: draft
owner: ml-team
tags:
  - ocr_preprocessing
  - iqa
  - pipeline
  - integration
purpose: Complete specification of what Project A delivers to Project B (OCR Orchestration).
component: Context
source: CLAUDE.md
---

**Date**: 2026-01-12

> **Related reference**: [docs/reference/DOCLING_CONFIGURATION_REFERENCE.md](../reference/DOCLING_CONFIGURATION_REFERENCE.md)
> — complete docling adjustment levers, CLI flags, and `DoclingRoutingParams` coverage matrix.

---

## Executive Summary

Project A (Preprocessing, IQA & Coarse Layout Gateway) produces:

1. **Corrected images** - Quality-enhanced page images ready for OCR
2. **DocumentMetadata.json** - Structured metadata with quality scores and routing recommendations

Project B (OCR Orchestration) receives this output and applies appropriate OCR strategy based on the routing recommendations.

---

## 1. Project A Outputs

### 1.1 Corrected Images

**Format**: PNG/JPEG images at standardized 300 DPI (or 1600x1600 for ML IQA)

**Corrections Applied** (8 types):

| Correction | Trigger Condition | Algorithm | Guardrails |
|------------|-------------------|-----------|------------|
| **Deskew** | Skew angle 0.5°-45° | Rotation via affine transform | Skip if angle <0.5° or >45° |
| **Contrast Enhancement** | Low contrast score (<0.4) | CLAHE on LAB L-channel | Skip if already good |
| **Sharpening** | Blur score < 200 (Laplacian variance) | Unsharp mask | Cap at 2.0 strength |
| **Denoising** | Noise score < 0.7 | NLMeans | Prevent over-smoothing |
| **Binarization** | Poor binarization quality | Adaptive threshold + morphology | Preserve color info |
| **Illumination Normalization** | Uneven lighting score <0.7 | Morphological background estimation | Blend with original |
| **Bleed-through Suppression** | Bleed-through detected | Cross-channel filtering | Preserve legitimate content |
| **Orientation Correction** | 90°/180°/270° rotation detected | cv2.rotate | Confidence threshold 0.7 |

### 1.2 DocumentMetadata.json Schema

```json
{
  "document_id": "uuid",
  "file_name": "original.pdf",
  "source_mime": "application/pdf",
  "document_type": "pdf",
  "num_pages": 10,

  "pdf_type": "image_only | born_digital | hybrid",
  "languages": ["en", "es"],
  "has_non_latin": false,

  "dqs": {
    "degradation_score": 0.85,
    "structural_complexity_score": 0.30
  },

  "pre_ocr_risk": 0.25,
  "ocr_routing_recommendation": "ocr_fast | ocr_advanced | vision_simple | vision_structured",

  "upscaling": {
    "performed": true,
    "original_dpi": 150,
    "target_dpi": 300
  },

  "page_layout_summary": [
    {
      "page_number": 1,
      "layout_type": "single_column | multi_column | three_column | complex",
      "has_tables": false,
      "has_figures": true,
      "has_dense_math": false,
      "has_handwriting": false,
      "has_list_items": true,
      "has_headers_footers": true,
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.35
    }
  ],

  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 150,
      "dpi_effective": 300,

      "ml_iqa": {
        "source": "student",
        "blur_score": 0.82,
        "noise_score": 0.78,
        "contrast_score": 0.85,
        "skew_score": 0.91,
        "compression_score": 0.87,
        "overall_quality": 0.85
      },

      "teacher_iqa": null,

      "orientation": {
        "detected_angle": 0,
        "confidence": 0.95,
        "auto_corrected": false
      },

      "detected_issues": [...],
      "planned_actions": [...],
      "elements": [...],
      "transform_history": [...]
    }
  ]
}
```

---

## 2. OCR Routing Decision Tree

Project B uses these rules (in order):

| Priority | Condition | Routing Strategy |
|----------|-----------|------------------|
| 1 | `has_tables` OR `has_figures` | `vision_structured` |
| 2 | `pre_ocr_risk > 0.6` OR `has_handwriting` | `ocr_advanced` |
| 3 | `pdf_type == born_digital` AND `degradation_score > 0.8` AND simple layout | `ocr_fast` |
| 4 | `pdf_type == image_only` AND simple layout | `vision_simple` |
| 5 | Default fallback | `ocr_advanced` |

**Simple Layout** = `layout_type` is `single_column` or `multi_column`

---

## 3. What Production Models Must Accomplish

### 3.1 Current Model Output (5 Heads)

The ML IQA model currently outputs 5 aggregate quality scores:

| Head | Range | Interpretation |
|------|-------|----------------|
| `blur_score` | 0-1 | 1 = sharp, 0 = blurry |
| `noise_score` | 0-1 | 1 = clean, 0 = noisy |
| `contrast_score` | 0-1 | 1 = good contrast, 0 = poor |
| `skew_score` | 0-1 | 1 = straight, 0 = skewed |
| `compression_score` | 0-1 | 1 = no artifacts, 0 = severe compression |

### 3.2 What Corrections Need

For each correction to activate, specific detection must occur:

| Correction | Required Detection | Trigger |
|------------|-------------------|---------|
| Deskew | Skew angle (degrees) | Classical: Hough transform |
| Sharpen | Blur score (Laplacian variance) | Classical + ML |
| Denoise | Noise score (0-1) | Classical + ML |
| CLAHE | Contrast score (0-1) | Classical + ML |
| Illumination | Illumination uniformity (0-1) | Classical only |
| Binarization | Binarization quality (0-1) | Classical only |
| Bleed-through | Bleed-through score (0-1) | Classical only |
| Orientation | Rotation angle (0/90/180/270) | Ensemble detector |

### 3.3 What Routing Needs

| Routing Input | Source | Used For |
|---------------|--------|----------|
| `pdf_type` | PDF classifier | Born-digital fast path |
| `has_tables` | Layout-lite (YOLO) | Vision-structured routing |
| `has_figures` | Layout-lite (YOLO) | Vision-structured routing |
| `has_handwriting` | Layout-lite (YOLO) | Advanced OCR routing |
| `layout_type` | Column detector | Simple/complex classification |
| `degradation_score` | DQS calculator | Quality threshold |
| `pre_ocr_risk` | Risk aggregator | Risk threshold (>0.6) |
| `structural_complexity_score` | Layout aggregator | Complexity assessment |

---

## 4. Gap Analysis: What's Missing

### 4.1 Classical IQA (✅ Complete)

8 detectors fully implemented:

- Skew, Blur, Contrast, Noise
- Illumination, JPEG Blockiness, Binarization, Bleed-through

### 4.2 Layout-Lite (✅ Complete)

- DocLayout-YOLO detecting 11 DocLayNet classes
- Page attributes: tables, figures, handwriting, math, headers/footers
- Fuzzy scan, watermark, colorful background detection
- Column layout classification

### 4.3 ML IQA (⚠️ Architecture Gap)

**Current**: 5-head model (blur, noise, contrast/illumination, skew, compression/artifacts)

**Training Labels**: 45-dimensional degradation taxonomy

| Gap | Issue | Impact |
|-----|-------|--------|
| **45→5 mapping** | 45 degradation types compressed to 5 heads | Loss of fine-grained detection |
| **15 unmapped types** | Physical, text-specific, scanner artifacts | No model coverage |
| **Head naming** | Inconsistent names across codebase | Confusion |

### 4.4 Pseudo-Labels (❌ Not Started)

Production ML IQA requires training on corpus with quality labels:

| Status | Description |
|--------|-------------|
| Human labels | Only DIQA-5000 (5,500 images, 0.2%) |
| Pseudo-labels | Not generated (requires DocIQ-Replica inference) |
| Anchor labels | 13K strategic images identified |

---

## 5. Production Model Requirements Summary

### 5.1 Minimum Viable Product

For corrections and routing to work, models must predict:

| Prediction | Purpose | Current Status |
|------------|---------|----------------|
| Overall quality score | DQS calculation | ✅ Student model |
| Blur severity (0-1) | Sharpening decision | ✅ Classical + ML |
| Noise severity (0-1) | Denoising decision | ✅ Classical + ML |
| Contrast score (0-1) | CLAHE decision | ✅ Classical + ML |
| Compression artifacts (0-1) | Quality flag | ⚠️ ML only |

### 5.2 Enhanced Detection (Future)

For fine-grained correction and diagnostics:

| Prediction | Purpose | Current Status |
|------------|---------|----------------|
| 45-dim degradation vector | Detailed diagnosis | ❌ Need 45-head model |
| Physical damage detection | Stain, water damage | ❌ Not covered |
| Text-specific issues | Faded text, broken chars | ❌ Not covered |
| Scanner artifacts | Moiré pattern, halftone, dust | ❌ Not covered |

---

## 6. Correction → Detection Mapping

Complete mapping from correction to required detection:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    CORRECTION PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DETECTION                    CORRECTION                                 │
│  ─────────                    ──────────                                 │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │ SkewDetector  │───angle───►│ DeskewCorrector│                        │
│  │ (Hough/Proj)  │            │ (Affine warp)  │                        │
│  └───────────────┘            └───────────────┘                         │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │ BlurDetector  │───score───►│ Sharpener     │                        │
│  │ (Laplacian)   │            │ (Unsharp mask)│                        │
│  │ + ML IQA blur │            └───────────────┘                         │
│  └───────────────┘                                                       │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │ContrastDetect │───score───►│ContrastEnhance│                        │
│  │ (Histogram)   │            │ (CLAHE LAB)   │                        │
│  │ + ML IQA      │            └───────────────┘                         │
│  └───────────────┘                                                       │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │ NoiseDetector │───score───►│ Denoiser      │                        │
│  │ (Sigma est)   │            │ (NLMeans)     │                        │
│  │ + ML IQA      │            └───────────────┘                         │
│  └───────────────┘                                                       │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │IlluminDetect  │───score───►│IllumNormalizer│                        │
│  │ (Block var)   │            │ (Morphological)│                        │
│  └───────────────┘            └───────────────┘                         │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │BinarizDetect  │───score───►│BinarizCorrect │                        │
│  │ (Otsu bimod)  │            │ (Adaptive thr)│                        │
│  └───────────────┘            └───────────────┘                         │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │BleedThruDetect│───score───►│BleedThruSuppr │                        │
│  │ (Channel diff)│            │ (Morph filter)│                        │
│  └───────────────┘            └───────────────┘                         │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │OrientDetector │───angle───►│OrientCorrector│                        │
│  │ (Ensemble)    │            │ (cv2.rotate)  │                        │
│  └───────────────┘            └───────────────┘                         │
│                                                                          │
│  ┌───────────────┐            ┌───────────────┐                         │
│  │ ML IQA 5-head │            │ DQS Calculator│                        │
│  │ (ResNet-18)   │───scores──►│ + Routing     │───►DocumentMetadata    │
│  └───────────────┘            └───────────────┘                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Key Decisions Required

### 7.1 Architecture Decision: 45 vs 5 Heads

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A: Keep 5** | Simple, fast | Lose detail | If routing is sufficient |
| **B: Expand to 8** | Better coverage | Retraining | **Recommended** |
| **C: Full 45** | Complete taxonomy | Complex, slow | Overkill for corrections |
| **D: Two-stage** | Best of both | Complexity | For diagnostics only |

### 7.2 Missing Detections

These 15 degradation types have no model coverage:

**Physical Damage** (5): stain, ink_bleed, bleed_through*, water_damage, yellowing
**Text-specific** (5): faded_text, broken_characters, touching_characters, overlapping_text, stamp_interference
**Scanner** (5): moiré pattern (`moire_pattern`), halftone, scanner_noise, dust_specks, scratches

*bleed_through has classical detector but no ML model

**Question**: Are these needed for corrections or just diagnostics?

---

## 8. Summary: What Must Work for Production

### 8.1 Critical Path (Must Have)

| Component | Status | Action |
|-----------|--------|--------|
| Classical IQA (8 detectors) | ✅ Complete | None |
| Corrections (8 correctors) | ✅ Complete | None |
| Layout-Lite (YOLO + attributes) | ✅ Complete | None |
| PDF Type Classification | ✅ Complete | None |
| Routing Engine | ✅ Complete | None |
| ML IQA Student (5-head) | ✅ Trained | Generate pseudo-labels |
| DQS Calculator | ✅ Complete | Calibrate with OCR feedback |

### 8.2 Quality Enhancement (Should Have)

| Component | Status | Action |
|-----------|--------|--------|
| Pseudo-labels (2.5M images) | ❌ Not started | Run DocIQ-Replica |
| ML model retraining | ❌ Not started | After pseudo-labels |
| DQS calibration | ⚠️ Partial | Integrate OCR feedback |

### 8.3 Future (Nice to Have)

| Component | Status | Action |
|-----------|--------|--------|
| 8-head or 45-head model | ❌ Not started | Architecture decision |
| Physical damage detection | ❌ Not started | Needs training data |
| Scanner artifact detection | ❌ Not started | Needs training data |

---

*This specification defines the complete interface between Project A and Project B.*
