---
title: Prepare-Doc to Unify Handoff Specification v2
schema_type: planning
status: active
owner: ml-team
component: Strategy
source: Internal specification derived from SigLIP 2 multitask requirements and docling integration audit (v1 superseded 2026-01-12)
tags:
  - ocr_preprocessing
  - iqa
  - pipeline
  - integration
purpose: Complete specification of what Prepare-Doc delivers to Unify (Unify), including signal-to-docling-parameter coverage matrix and architectural boundary definition.
---

**Date**: 2026-02-22 | **Version**: 2.0

> **Key Change from v1**: v1 described a 5-head ResNet architecture and Prepare-Doc/B naming.
> v2 reflects the 16-head SigLIP 2 teacher model, MobileNetV4 Stage 1 gate, service names,
> and the canonical architectural boundary decision.
>
> **Related documents**:
>
> - [docs/reference/DOCLING_CONFIGURATION_REFERENCE.md](../reference/DOCLING_CONFIGURATION_REFERENCE.md) — complete docling CLI flags and `DoclingRoutingParams` coverage matrix
> - [docs/planning/DOCLING_INTEGRATION_GAP_REPORT.md](DOCLING_INTEGRATION_GAP_REPORT.md) — 3 P0 bugs and signal coverage audit
> - [docs/planning/MASTER_PROJECT_PLAN.md](MASTER_PROJECT_PLAN.md) — current status and tier structure

---

## 0. Architectural Boundary (CRITICAL)

**Prepare-Doc is an analysis oracle. Unify is the docling configuration authority.**

```text
PREPARE-DOC (image_detection)          UNIFY (Unify)
────────────────────────────────          ───────────────────────
Detects, scores, measures → signals        Reads signals → configures docling
Applies physical corrections               Does NOT apply corrections
Writes DocumentMetadata.json               Reads DocumentMetadata.json
Runs DoclingRoutingEngine (advisory)  →→→  Uses DoclingRoutingParams from metadata
                                           Makes final docling configuration decisions
                                           Can override any Prepare-Doc recommendation
```

`DoclingRoutingEngine` in Prepare-Doc generates **advisory parameters** only. Unify reads
`docling_params` from `DocumentMetadata.json` and applies its own policy — it may accept,
reject, or modify any recommendation.

> **Migration note**: `DoclingRoutingEngine` is currently resident in Prepare-Doc for development
> convenience. It is scheduled for migration to Unify in Stream 5 (after Unify integration begins).

---

## 1. What Prepare-Doc Delivers

Prepare-Doc produces two outputs per document page:

### 1.1 Corrected Page Images (Function 1: Physical Corrections)

Stage 1 (MobileNetV4) detects orientation, skew, and resolution issues, then applies corrections
before any analysis occurs. Corrections are applied to the image before Stage 2 runs.

| Correction | Trigger | Algorithm | Guardrails |
|---|---|---|---|
| **Orientation correction** | 90°/180°/270° detected (conf ≥ 0.70) | `cv2.rotate()` | Skip if confidence < 0.70 |
| **Deskew** | Fine skew > 0.5° | Affine transform (Hough-derived angle) | Skip if < 0.5° or > 45° |
| **CLAHE contrast** | Contrast score < 0.4 | CLAHE on LAB L-channel | Skip if already adequate |
| **Sharpening** | Blur score < 0.5 | Unsharp mask | Cap strength at 2.0 |
| **Denoising** | Noise score < 0.7 | NLMeans | Prevent over-smoothing |
| **Binarization fix** | Poor binarization quality | Adaptive threshold + morphology | Preserve color information |
| **Illumination normalization** | Illumination uniformity < 0.7 | Morphological background estimation | Blend with original |
| **Bleed-through suppression** | Bleed-through detected | Cross-channel filtering | Preserve legitimate content |
| **Border removal** | Scanner/camera frame artifacts | Contour detection + crop | Safety margin 5px |
| **Perspective correction** | Trapezoid distortion (camera docs) | Homography transform | Skip if distortion < threshold |
| **Resolution upscaling** | Char height < 28px effective | OpenCV (5 algorithm options) | Only when below viable threshold |

**Output format**: PNG or JPEG at effective 300 DPI minimum (or original DPI if already adequate).

### 1.2 DocumentMetadata.json (Function 2: Analysis Signals)

Stage 2 (SigLIP 2, 19 heads) generates all analysis signals. The full schema is defined in
[src/image_preprocessing_detector/schema.py](../../src/image_preprocessing_detector/schema.py).

---

## 2. DocumentMetadata.json Schema

```json
{
  "document_id": "uuid-v4",
  "file_name": "original.pdf",
  "source_mime": "application/pdf",
  "document_type": "pdf",
  "num_pages": 10,
  "schema_version": "2.0",

  "pdf_type": "image_only | born_digital | hybrid",

  "dqs": {
    "degradation_score": 0.85,
    "structural_complexity_score": 0.30
  },

  "pre_ocr_risk": 0.25,
  "ocr_routing_recommendation": "ocr_fast | ocr_advanced | vision_simple | vision_structured",

  "docling_params": {
    "pipeline": "standard | vlm",
    "vlm_model": null,
    "ocr_enabled": true,
    "ocr_force": false,
    "ocr_engine": "auto | rapidocr | tesseract",
    "ocr_lang": "ch",
    "psm": null,
    "tables_enabled": true,
    "table_mode": "fast | accurate",
    "enrich_code": false,
    "enrich_formula": false,
    "page_batch_size": 4
  },

  "upscaling": {
    "performed": true,
    "original_dpi": 150,
    "target_dpi": 300,
    "algorithm": "lanczos"
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
      "complexity_score": 0.35,
      "orientation_angle": 0,
      "orientation_confidence": 0.96
    }
  ],

  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 150,
      "dpi_effective": 300,

      "stage1_gate": {
        "orientation_class": 0,
        "orientation_confidence": 0.97,
        "skew_angle_deg": -0.4,
        "resolution_quality": 0.72,
        "char_height_px": 34
      },

      "ml_iqa": {
        "source": "siglip2",
        "blur_score": 0.82,
        "noise_score": 0.78,
        "contrast_score": 0.85,
        "skew_severity": 0.05,
        "compression_score": 0.87,
        "shadow_severity": 0.10,
        "warping_severity": 0.08,
        "overall_quality": 0.83
      },

      "script_detection": {
        "dominant_script": "Latn",
        "dominant_confidence": 0.94,
        "ml_class": "LATN",
        "secondary_scripts": []
      },

      "handwriting": {
        "presence": "none | partial | dominant",
        "presence_confidence": 0.92,
        "legibility": "unreadable | poor | fair | good | excellent",
        "content_type": "printed | cursive | mixed | annotation | diagram_label",
        "density_score": 0.05,
        "script_family": "latin | arabic | cjk | other"
      },

      "page_attributes": {
        "capture_method": "born_digital | flatbed_scanner | adf_scanner | smartphone_camera | dedicated_camera | synthetic | unknown",
        "capture_confidence": 0.88,
        "shadow_severity": 0.10,
        "warping_severity": 0.08,
        "code_content_ratio": 0.00,
        "effective_resolution_score": 0.91
      },

      "orientation": {
        "detected_angle": 0,
        "confidence": 0.97,
        "auto_corrected": false,
        "stage2_validation": "consistent | escalated"
      },

      "skew": {
        "angle_deg": -0.4,
        "confidence": 0.85,
        "auto_corrected": false
      },

      "detected_issues": [],
      "planned_actions": [],
      "elements": [],
      "transform_history": []
    }
  ]
}
```

---

## 3. Signal-to-Docling-Parameter Coverage Matrix

This is the canonical mapping from Prepare-Doc signals to Unify/docling configuration decisions.
Every `docling_params` field must trace back to a Prepare-Doc signal.

| `docling_params` field | Prepare-Doc signal(s) | Coverage | Notes |
|---|---|---|---|
| `pipeline` | `has_handwriting`, `script_detection.ml_class`, `has_dense_math`, page_attributes | ✅ Full | VLM escalation for poor OCR coverage scripts |
| `vlm_model` | — | ⚠️ Partial | Default behavior undocumented; Unify must decide which VLM to request |
| `ocr_enabled` | `pdf_type`, `ml_iqa.overall_quality` | ✅ Full | Disable for born-digital if quality high |
| `ocr_force` | `pdf_type`, detected born-digital with bad text layer | ✅ Full | Force re-OCR when text layer unreliable |
| `ocr_engine` | `script_detection.dominant_script` (via ScriptRouter) | ✅ Full | `rapidocr` for CJK/Indic; `tesseract` for RTL; `auto` for Latin |
| `ocr_lang` | `script_detection.dominant_script` (via ScriptRouter) | ✅ Full | ISO 639 hint emitted per script class |
| `psm` | `layout_type` (coarse) | ⚠️ Partial | Column structure → PSM hint; not fine-grained enough |
| `tables_enabled` | `has_tables` | ✅ Full | Disable if no tables detected (skips expensive table pipeline) |
| `table_mode` | `has_tables` + `complexity_score` | ✅ Full | `accurate` if complex, `fast` if simple |
| `enrich_code` | `code_content_ratio` | ✅ Full | Enable if > 0.15 code detected |
| `enrich_formula` | `has_dense_math` | ✅ Full | Enable if math detected |
| `page_batch_size` | `script_detection.ml_class`, `dpi_effective` | ✅ Full | Reduce for CJK (memory), increase for Latin |

**Coverage summary**: 10/12 fields fully covered, 2/12 partially covered.

**Known gaps** (see [DOCLING_INTEGRATION_GAP_REPORT.md](DOCLING_INTEGRATION_GAP_REPORT.md)):

- `vlm_model`: When VLM pipeline triggers, Prepare-Doc does not specify which model. Unify must define a default VLM model selection policy. (Bug 1.3)
- `psm`: Only coarse layout types available (single/multi/complex column). Fine-grained PSM selection requires per-region layout analysis (not in Prepare-Doc scope).
- Domain hints for chart/diagram decisions: domain classification not yet in Prepare-Doc signals.

---

## 4. Two-Model Pipeline Summary

### Stage 1 — MobileNetV4-Conv-S (~3ms GPU)

Runs on uncorrected raw image. Produces:

- Orientation: 4-class (0/90/180/270°) with confidence
- Fine skew: sub-degree regression (±45° range)
- Resolution quality: character-height-aware score (0–1)

Physical corrections applied immediately after Stage 1.

**Training status**: ✅ Complete — val MAE=0.837, orient_acc=99.5%. Pipeline integration pending (Stream 4D).

### Stage 2 — SigLIP 2 NAFlex, 88M params (~50ms GPU)

Runs on corrected image. 19 heads across 5 task groups:

| Group | Heads | Count |
|---|---|---|
| IQA | blur, noise, contrast, skew severity, compression artifacts, overall | 6 |
| Script | dominant script 10-class | 1 |
| Orientation + Skew | 4-class rotation validation, fine skew regression | 2 |
| Handwriting | presence, legibility, content type, density, script family | 5 |
| Page Attributes | capture method, shadow severity, warping severity, code content ratio, effective resolution | 5 |

**Training status**: ❌ Not started — dataset assembly 70% complete.

### Classical IQA Baseline (~25ms CPU)

8 detectors running in parallel as interpretable anchors:
skew (Hough), blur (Laplacian), contrast (histogram), noise (sigma estimation),
illumination (block variance), JPEG blockiness, binarization quality, bleed-through.

**Status**: ✅ Complete.

---

## 5. OCR Routing Decision

Prepare-Doc computes an advisory `ocr_routing_recommendation`. Unify is free to override.

| Priority | Condition | Recommendation |
|---|---|---|
| 1 | `has_tables` OR `has_figures` with complex layout | `vision_structured` |
| 2 | `pre_ocr_risk > 0.6` OR `has_handwriting=dominant` | `ocr_advanced` |
| 3 | `pdf_type=born_digital` AND `degradation_score > 0.8` AND simple layout | `ocr_fast` |
| 4 | `pdf_type=image_only` AND simple layout AND low risk | `vision_simple` |
| 5 | Default fallback | `ocr_advanced` |

---

## 6. Current Status vs v1 Spec

| Component | v1 Status (Jan 2026) | v2 Status (Feb 2026) |
|---|---|---|
| Classical IQA (8 detectors) | ✅ Complete | ✅ Complete |
| Corrections (8 correctors) | ✅ Complete | ✅ Complete — border removal + perspective added |
| Layout-Lite (docling-layout) | ✅ Complete | ✅ Complete |
| PDF type classification | ✅ Complete | ✅ Complete |
| Routing engine | ✅ Complete | ✅ Complete — 3 P0 bugs fixed (see below) |
| DQS calculator | ✅ Complete | ✅ Complete |
| ML IQA (5-head ResNet) | ✅ Trained | Replaced by SigLIP 2 (16-head) — ❌ training pending |
| MobileNetV4 Stage 1 | ❌ Not in spec | ✅ Trained (val MAE=0.837) — pipeline integration pending |
| SigLIP 2 16-head teacher | ❌ Not in spec | ❌ Training pending (dataset assembly ~70%) |
| Pseudo-labels (2.5M) | ❌ Not started | ❌ Not started (Stream 7, requires SigLIP 2) |

**P0 bugs fixed in this cycle** (see [DOCLING_INTEGRATION_GAP_REPORT.md](DOCLING_INTEGRATION_GAP_REPORT.md)):

1. `paddleocr` invalid engine key → replaced with `rapidocr` in `script_routing.yaml` (12 entries)
2. `--no-tables` never emitted in `to_cli_args()` when `tables_enabled=False` → fixed in `schema.py`
3. VLM model stays `None` with undocumented default → behavior documented with inline comment in `docling_router.py`

---

## 7. Integration Testing Prerequisites

Before Prepare-Doc → Unify integration testing can begin:

| Prerequisite | Status | Owner |
|---|---|---|
| 3 P0 Docling bugs fixed | ✅ Done (this cycle) | Prepare-Doc |
| SigLIP 2 training complete | ❌ Pending | Prepare-Doc (Tier 3) |
| MobileNetV4 pipeline integration | ❌ Pending (Stream 4D) | Prepare-Doc (Tier 3) |
| Unify reads `docling_params` from schema | ❓ Unknown | Unify team |
| VLM model selection policy defined | ❓ Unknown | Unify team |
| Contract schema version agreement | ❓ Unknown | Both teams |

---

## 8. Boundary Compliance Checklist

Before Prepare-Doc delivers any batch to Unify, verify:

- [ ] All corrected images are at ≥ 300 DPI effective (or original if higher)
- [ ] `document_id` is stable UUID (same across all retries)
- [ ] `schema_version` field is present in output JSON
- [ ] `docling_params.ocr_engine` contains only `"auto"`, `"rapidocr"`, or `"tesseract"` — never `"paddleocr"`
- [ ] `docling_params.tables_enabled=False` only when `has_tables=False` across all pages
- [ ] `docling_params.vlm_model=null` is acceptable (Unify will apply VLM model selection policy)
- [ ] `transform_history` is populated for all pages with corrections applied
- [ ] `stage1_gate` fields present for every page (char_height_px, skew_angle_deg, resolution_quality)

---

*This specification supersedes the v1 document (2026-01-12). The v1 document described a 5-head
ResNet model, "Prepare-Doc/B" naming, and did not include the architectural boundary definition,
signal-to-docling-parameter coverage matrix, or Stage 1/Stage 2 two-model pipeline split.*
