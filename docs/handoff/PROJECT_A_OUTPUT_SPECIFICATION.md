---
schema_type: common
title: "Project A Output Specification"
description: "Output specification for Project A to Project B handoff"
tags:
  - documentation
  - integration
  - reference
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document the output format and contract between Project A and Project B."
---

> **Status**: Production Ready
> **Version**: 2.0.0-draft
> **Last Updated**: 2026-02-10
> **Audience**: Project B (OCR Orchestration) Team
> **Schema Version**: v1.0 (current) + v2.0 (planned - SigLIP 2 integration)

## Executive Summary

Project A (Preprocessing, IQA & Coarse Layout Gateway) produces two primary outputs for each processed document:

1. **`metadata.json`** - Complete quality assessment, routing recommendations, and page attributes
2. **Corrected Page Images** - 300 DPI PNG images with corrections applied (deskew, denoising, contrast enhancement)

These outputs enable Project B to make intelligent OCR engine selection and processing decisions
without re-analyzing image quality.

---

## Output Directory Structure

```text
output/
└── {document_id}/
    ├── metadata.json           # DocumentMetadata JSON (required)
    ├── page_0000.png           # Corrected page 1 (300 DPI PNG)
    ├── page_0001.png           # Corrected page 2
    ├── page_0002.png           # ...
    └── page_NNNN.png           # Last page
```

### Naming Conventions

| Item | Pattern | Example |
|------|---------|---------|
| Document ID | `doc_{timestamp}_{sequence}` | `doc_20251125_001` |
| Page images | `page_{NNNN}.png` (4-digit zero-padded) | `page_0000.png`, `page_0012.png` |
| Metadata file | `metadata.json` | `metadata.json` |

---

## DocumentMetadata Schema

### Required Fields (Project B MUST consume)

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | Unique document identifier |
| `file_name` | string | Original input filename |
| `source_mime` | string | MIME type (e.g., `application/pdf`, `image/png`) |
| `num_pages` | integer | Total page count (≥1) |
| `pdf_type` | enum | Document classification for routing |
| `dqs` | object | Document Quality Score (degradation + complexity) |
| `pre_ocr_risk` | float | Combined risk score 0-1 for OCR difficulty |
| `ocr_routing_recommendation` | enum | Recommended OCR strategy |
| `page_layout_summary` | array | Per-page coarse layout attributes |
| `pages` | array | Per-page detailed metadata |
| `processing_version` | object | Pipeline version and configuration |

### Optional Fields (Present when applicable)

| Field | Type | Description |
|-------|------|-------------|
| `languages` | array[string] | ISO 639-1 codes detected (e.g., `["en", "es"]`) |
| `has_non_latin` | boolean | Document contains non-Latin scripts |
| `upscaling` | object | DPI upscaling metadata (if performed) |
| `teacher_usage` | object | Teacher model escalation details |

### v2.0 Planned Fields (SigLIP 2 Integration)

> **Status**: Planned - Available after SigLIP 2 multi-task model deployment
> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
> **Timeline**: Post Stream 1 schema foundation

These fields will be added to `DocumentMetadata` and `pages` once the SigLIP 2 multi-task model is deployed.
They are **optional** in v2.0 (absent if SigLIP 2 not available) and will become **recommended** in v3.0.

#### Document-Level New Fields

| Field | Type | Description | Routing Impact |
|-------|------|-------------|----------------|
| `script_detection` | object | Primary script detected across document | OCR engine selection (Tier 3 routing) |
| `capture_method` | object | Predicted physical origin of document | Degradation prediction, correction selection |

#### Per-Page New Fields (in `pages[]`)

| Field | Type | Description | Routing Impact |
|-------|------|-------------|----------------|
| `script_detection` | object | Per-page script analysis | Per-page OCR engine routing |
| `handwriting_assessment` | object | Handwriting presence and characteristics | OCR strategy escalation |
| `page_attributes` | object | Physical page characteristics | Quality assessment, correction |
| `resolution_quality` | object | Character-height-aware quality assessment | DPI adjustment decisions |

#### script_detection (Per-Page)

```json
{
  "script_detection": {
    "primary_script": "Latn",
    "primary_confidence": 0.92,
    "script_family": "LATIN",
    "has_non_latin": false,
    "has_rtl": false,
    "detection_method": "siglip2_multitask",
    "script_probabilities": {
      "Latn": 0.92,
      "Cyrl": 0.05,
      "Grek": 0.02,
      "Zzzz": 0.01
    }
  }
}
```

**Project B Impact**: Use `primary_script` to select OCR engine via script routing config.
RTL scripts (`has_rtl: true`) require Tesseract with RTL mode. CJK scripts route to PaddleOCR.
See `config/script_routing.yaml` for engine mapping.

#### handwriting_assessment (Per-Page)

```json
{
  "handwriting_assessment": {
    "has_handwriting": true,
    "presence_score": 0.75,
    "handwriting_ratio": 0.30,
    "legibility": "partially_legible",
    "legibility_score": 0.55,
    "content_type": "annotations",
    "mixed_content": true
  }
}
```

| Field | Type | Values |
|-------|------|--------|
| `has_handwriting` | bool | Handwriting detected on page |
| `presence_score` | float 0-1 | Confidence of handwriting presence |
| `handwriting_ratio` | float 0-1 | Proportion of page area with handwriting |
| `legibility` | enum | `legible`, `partially_legible`, `illegible`, `not_applicable` |
| `legibility_score` | float 0-1 | Continuous legibility score |
| `content_type` | enum | `annotations`, `form_fill`, `full_page`, `signatures`, `mixed`, `none`, `unknown` |
| `mixed_content` | bool | Page has both printed and handwritten content |

**Project B Impact**: `has_handwriting: true` with `legibility: "partially_legible"` should escalate to
advanced OCR (Textract, Vision). `content_type: "form_fill"` suggests structured extraction.

#### page_attributes (Per-Page)

```json
{
  "page_attributes": {
    "shadow_detected": true,
    "shadow_score": 0.45,
    "warping_detected": false,
    "warping_score": 0.12,
    "code_detected": false,
    "code_confidence": 0.05,
    "capture_method": "SCANNER_FLATBED",
    "capture_method_confidence": 0.88
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `shadow_detected` | bool | Page has visible shadows (camera capture artifact) |
| `shadow_score` | float 0-1 | Shadow severity (0=none, 1=severe) |
| `warping_detected` | bool | Page has geometric warping/curl |
| `warping_score` | float 0-1 | Warping severity |
| `code_detected` | bool | Page contains source code / programming content |
| `code_confidence` | float 0-1 | Code detection confidence |
| `capture_method` | enum | `BORN_DIGITAL`, `SCANNER_FLATBED`, `SCANNER_ADF`, `CAMERA_PROFESSIONAL`, `CAMERA_SMARTPHONE`, `FAX`, `UNKNOWN` |
| `capture_method_confidence` | float 0-1 | Capture method prediction confidence |

**Project B Impact**: `shadow_detected` and `warping_detected` indicate camera-captured documents
that may benefit from DocTr/DocRes pre-processing. `code_detected` suggests monospace font handling.

#### resolution_quality (Per-Page)

```json
{
  "resolution_quality": {
    "estimated_char_height_px": 28,
    "quality_score": 0.45,
    "assessment": "borderline",
    "recommended_action": "upscale_light"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `estimated_char_height_px` | int | Estimated character height in pixels |
| `quality_score` | float 0-1 | Resolution adequacy (0=too small, 0.7=optimal, 1.0=oversized) |
| `assessment` | enum | `too_small`, `borderline`, `adequate`, `optimal`, `oversized` |
| `recommended_action` | enum | `upscale_heavy`, `upscale_light`, `no_change`, `downscale` |

**Project B Impact**: If Project A correction was applied, this reflects post-correction state.
If `assessment: "too_small"` persists after correction, Project B should expect lower OCR accuracy.

#### Updated Routing Decision Logic (v2.0)

The routing decision tree gains script-awareness:

```text
START
  |
  +-> Use existing v1.0 routing logic (pdf_type, pre_ocr_risk, layout)
  |
  +-> ADDITIONALLY (v2.0):
        |
        +-> IF script_detection.has_rtl == true
        |     -> Override engine to Tesseract RTL mode
        |
        +-> IF script_detection.script_family == "CJK"
        |     -> Override engine to PaddleOCR
        |
        +-> IF handwriting_assessment.has_handwriting == true
        |     AND handwriting_assessment.legibility_score < 0.5
        |     -> Escalate to vision_simple or vision_structured
        |
        +-> IF page_attributes.shadow_score > 0.5
        |     OR page_attributes.warping_score > 0.5
        |     -> Consider DocTr/DocRes pre-processing
        |
        +-> IF page_attributes.code_detected == true
              -> Use monospace-aware OCR settings
```

#### Updated pre_ocr_risk Formula (v2.0)

```text
pre_ocr_risk = 0.30 * degradation_score
             + 0.20 * complexity_score
             + 0.15 * (1 if pdf_type == "image_only" else 0)
             + 0.10 * (1 - script_detection.primary_confidence)
             + 0.10 * handwriting_assessment.presence_score
             + 0.05 * page_attributes.shadow_score
             + 0.05 * page_attributes.warping_score
             + 0.05 * (1 - resolution_quality.quality_score)
```

---

## Schema Version Migration (v1.0 -> v2.0)

| Aspect | v1.0 (Current) | v2.0 (Planned) |
|--------|----------------|----------------|
| Script detection | `has_non_latin: bool` only | Full `script_detection` object with ISO 15924 |
| Handwriting | `has_handwriting: bool` in page_layout_summary | Full `handwriting_assessment` object per page |
| Capture method | Not present | `capture_method` at document and page level |
| Page attributes | Not present | `page_attributes` object per page |
| Resolution quality | `dpi_input`/`dpi_effective` only | `resolution_quality` with char-height analysis |
| Routing | 4 strategies | 4 strategies + script-aware engine overrides |
| pre_ocr_risk | 4-factor formula | 8-factor formula with new signals |

**Backward Compatibility**: All v2.0 fields are optional. v1.0 consumers can ignore new fields.
v2.0 consumers should check field presence before using (`if "script_detection" in page:`).

---

## Field Specifications

### pdf_type (Document Classification)

```json
{
  "pdf_type": "image_only" | "born_digital" | "hybrid"
}
```

| Value | Description | Project B Implication |
|-------|-------------|----------------------|
| `image_only` | Scanned document, all pages are raster images | Full OCR required |
| `born_digital` | Digital-native PDF with embedded text layer | Text extraction possible, OCR optional |
| `hybrid` | Mix of scanned and digital pages | Per-page strategy needed |

### dqs (Document Quality Score)

```json
{
  "dqs": {
    "degradation_score": 0.25,
    "structural_complexity_score": 0.40
  }
}
```

| Field | Range | Description |
|-------|-------|-------------|
| `degradation_score` | 0.0-1.0 | Image degradation level (0=pristine, 1=severely degraded) |
| `structural_complexity_score` | 0.0-1.0 | Layout complexity (0=simple single column, 1=very complex) |

**Quality Interpretation:**

| Score Range | Degradation Meaning | Complexity Meaning |
|-------------|--------------------|--------------------|
| 0.0-0.3 | High quality, minimal issues | Simple layout |
| 0.3-0.6 | Moderate issues, correctable | Moderate complexity |
| 0.6-1.0 | Significant issues | Complex/challenging layout |

### ocr_routing_recommendation

```json
{
  "ocr_routing_recommendation": "ocr_fast" | "ocr_advanced" | "vision_simple" | "vision_structured"
}
```

| Strategy | Trigger Conditions | Recommended OCR Approach |
|----------|-------------------|--------------------------|
| `ocr_fast` | High quality (DQS<0.3), simple layout | Tesseract, EasyOCR |
| `ocr_advanced` | Medium quality or handwriting detected | AWS Textract, Google Vision |
| `vision_simple` | Low quality, complex layout without tables | GPT-4V, Claude Vision |
| `vision_structured` | Tables, forms, dense math detected | Vision models with structure prompts |

### page_layout_summary (Per-Page Attributes)

```json
{
  "page_layout_summary": [
    {
      "page_number": 1,
      "layout_type": "single_column",
      "has_tables": false,
      "has_figures": true,
      "has_dense_math": false,
      "has_handwriting": false,
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.25
    }
  ]
}
```

**Layout Types:**

| Type | Description |
|------|-------------|
| `single_column` | Standard single-column text layout |
| `multi_column` | Two-column layout (newspaper, academic) |
| `three_column` | Three or more columns |
| `complex` | Mixed regions, irregular layout |
| `unknown` | Unable to determine (fallback) |

**Boolean Flags:**

| Flag | When True |
|------|-----------|
| `has_tables` | Page contains tabular data |
| `has_figures` | Page contains images/diagrams |
| `has_dense_math` | Mathematical notation detected |
| `has_handwriting` | Handwritten content present |
| `fuzzy_scan` | Low-quality/blurry scan |
| `watermark` | Watermark overlay detected |
| `colorful_background` | Non-white background affects OCR |

### pages (Per-Page Detailed Metadata)

```json
{
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
        "overall_quality": 0.85,
        "device": "cuda",
        "inference_time_ms": 15.3
      },
      "teacher_iqa": null,
      "detected_issues": [...],
      "planned_actions": [...],
      "elements": [...],
      "languages": [...],
      "transform_history": [...]
    }
  ]
}
```

**Core Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `page_index` | integer | Zero-based page index |
| `width_px` | integer | Page width in pixels |
| `height_px` | integer | Page height in pixels |
| `dpi_input` | integer | Original DPI of input |
| `dpi_effective` | integer | DPI after processing (typically 300) |

**IQA Scores (ml_iqa):**

All scores are 0-1 where higher = better quality:

| Score | Description |
|-------|-------------|
| `blur_score` | Sharpness (0=very blurry, 1=sharp) |
| `noise_score` | Noise level (0=very noisy, 1=clean) |
| `contrast_score` | Contrast quality (0=poor, 1=good) |
| `skew_score` | Alignment (0=severely skewed, 1=straight) |
| `compression_score` | Compression artifacts (0=heavy artifacts, 1=clean) |
| `overall_quality` | Weighted aggregate score |

### detected_issues (Quality Issues Found)

```json
{
  "detected_issues": [
    {
      "type": "blur",
      "confidence": 0.85,
      "severity": "medium",
      "metrics": {
        "laplacian_variance": 85.3,
        "blur_score": 0.45
      }
    }
  ]
}
```

**Issue Types:** `noise`, `blur`, `skew`, `perspective`, `low_contrast`, `orientation`, `low_dpi`

**Severity Levels:** `low`, `medium`, `high`, `critical`

### transform_history (Corrections Applied)

```json
{
  "transform_history": [
    {
      "action": "deskew",
      "params": {"angle": -2.3},
      "started_at": "2025-11-25T10:30:00Z",
      "finished_at": "2025-11-25T10:30:00.150Z",
      "status": "success",
      "error_message": null
    }
  ]
}
```

**Action Types:** `deskew`, `perspective_correction`, `sharpen`, `denoise`, `clahe`,
`background_normalization`, `upsample`, `rotate`

---

## Complete Example: Multi-Page Scanned Document

```json
{
  "document_id": "doc_20251125_001",
  "file_name": "contract_scan.pdf",
  "source_mime": "application/pdf",
  "num_pages": 3,
  "pdf_type": "image_only",
  "languages": ["en"],
  "has_non_latin": false,
  "pre_ocr_risk": 0.42,
  "dqs": {
    "degradation_score": 0.35,
    "structural_complexity_score": 0.48
  },
  "ocr_routing_recommendation": "ocr_advanced",
  "page_layout_summary": [
    {
      "page_number": 1,
      "layout_type": "single_column",
      "has_tables": false,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": false,
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.15
    },
    {
      "page_number": 2,
      "layout_type": "multi_column",
      "has_tables": true,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": false,
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.65
    },
    {
      "page_number": 3,
      "layout_type": "single_column",
      "has_tables": false,
      "has_figures": true,
      "has_dense_math": false,
      "has_handwriting": true,
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.55
    }
  ],
  "upscaling": {
    "performed": true,
    "original_dpi": 150,
    "target_dpi": 300,
    "algorithm": "lanczos",
    "processing_time_ms": 345
  },
  "teacher_usage": null,
  "processing_version": {
    "pipeline_version": "1.0.0",
    "iqa_model_hash": "sha256:abc123def456...",
    "layout_model_hash": null,
    "thresholds": {
      "blur_threshold_critical": 50.0,
      "blur_threshold_high": 100.0,
      "noise_threshold_critical": 20.0,
      "contrast_threshold_low": 0.18
    },
    "timestamp": "2025-11-25T10:30:00Z"
  },
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 150,
      "dpi_effective": 300,
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.78,
        "noise_score": 0.82,
        "contrast_score": 0.75,
        "skew_score": 0.95,
        "compression_score": 0.88,
        "overall_quality": 0.80,
        "device": "cpu",
        "inference_time_ms": 42.5
      },
      "teacher_iqa": null,
      "detected_issues": [
        {
          "type": "blur",
          "confidence": 0.72,
          "severity": "low",
          "metrics": {
            "laplacian_variance": 185.3,
            "blur_score": 0.78
          }
        }
      ],
      "planned_actions": [],
      "elements": [],
      "languages": [
        {
          "script": "Latin",
          "confidence": 0.98
        }
      ],
      "transform_history": [
        {
          "action": "upsample",
          "params": {"scale_factor": 2.0, "algorithm": "lanczos"},
          "started_at": "2025-11-25T10:30:00Z",
          "finished_at": "2025-11-25T10:30:00.120Z",
          "status": "success",
          "error_message": null
        }
      ]
    },
    {
      "page_index": 1,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 150,
      "dpi_effective": 300,
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.65,
        "noise_score": 0.70,
        "contrast_score": 0.68,
        "skew_score": 0.88,
        "compression_score": 0.85,
        "overall_quality": 0.72,
        "device": "cpu",
        "inference_time_ms": 45.2
      },
      "teacher_iqa": null,
      "detected_issues": [
        {
          "type": "blur",
          "confidence": 0.85,
          "severity": "medium",
          "metrics": {
            "laplacian_variance": 95.7,
            "blur_score": 0.65
          }
        },
        {
          "type": "skew",
          "confidence": 0.78,
          "severity": "low",
          "metrics": {
            "angle_degrees": -1.8
          }
        }
      ],
      "planned_actions": [],
      "elements": [],
      "languages": [
        {
          "script": "Latin",
          "confidence": 0.97
        }
      ],
      "transform_history": [
        {
          "action": "upsample",
          "params": {"scale_factor": 2.0, "algorithm": "lanczos"},
          "started_at": "2025-11-25T10:30:00.150Z",
          "finished_at": "2025-11-25T10:30:00.280Z",
          "status": "success",
          "error_message": null
        },
        {
          "action": "deskew",
          "params": {"angle": 1.8},
          "started_at": "2025-11-25T10:30:00.280Z",
          "finished_at": "2025-11-25T10:30:00.350Z",
          "status": "success",
          "error_message": null
        }
      ]
    },
    {
      "page_index": 2,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 150,
      "dpi_effective": 300,
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.72,
        "noise_score": 0.75,
        "contrast_score": 0.70,
        "skew_score": 0.92,
        "compression_score": 0.86,
        "overall_quality": 0.75,
        "device": "cpu",
        "inference_time_ms": 44.8
      },
      "teacher_iqa": null,
      "detected_issues": [],
      "planned_actions": [],
      "elements": [],
      "languages": [
        {
          "script": "Latin",
          "confidence": 0.95
        }
      ],
      "transform_history": [
        {
          "action": "upsample",
          "params": {"scale_factor": 2.0, "algorithm": "lanczos"},
          "started_at": "2025-11-25T10:30:00.380Z",
          "finished_at": "2025-11-25T10:30:00.510Z",
          "status": "success",
          "error_message": null
        }
      ]
    }
  ]
}
```

---

## Routing Decision Logic for Project B

### Primary Decision Tree

```text
START
  │
  ├─▶ IF pdf_type == "born_digital"
  │     └─▶ Extract embedded text (skip heavy OCR)
  │         └─▶ Use OCR only for non-text regions
  │
  ├─▶ ELSE (image_only or hybrid)
  │     │
  │     ├─▶ IF pre_ocr_risk < 0.3
  │     │     └─▶ Use ocr_routing_recommendation directly
  │     │
  │     ├─▶ ELSE IF pre_ocr_risk < 0.6
  │     │     ├─▶ IF any page has_tables == true
  │     │     │     └─▶ Use vision_structured
  │     │     └─▶ ELSE
  │     │           └─▶ Use ocr_advanced
  │     │
  │     └─▶ ELSE (pre_ocr_risk >= 0.6)
  │           └─▶ Use vision_structured with retry strategy
  │
  └─▶ Per-page overrides:
        ├─▶ IF page.teacher_iqa is present → Flag as challenging
        ├─▶ IF page has severity="critical" issues → Special handling
        └─▶ IF page complexity_score > 0.6 → Per-page vision analysis
```

### Per-Page Strategy Selection

```python
def get_page_strategy(page_metadata, page_layout):
    """Determine OCR strategy for a single page."""

    # Teacher escalation indicates challenging content
    if page_metadata.teacher_iqa is not None:
        return "vision_structured"

    # Critical issues require vision models
    critical_issues = [i for i in page_metadata.detected_issues
                       if i.severity == "critical"]
    if critical_issues:
        return "vision_simple"

    # Tables/forms need structured extraction
    if page_layout.has_tables:
        return "vision_structured"

    # Handwriting needs advanced OCR
    if page_layout.has_handwriting:
        return "ocr_advanced"

    # Dense math needs vision
    if page_layout.has_dense_math:
        return "vision_structured"

    # High complexity pages
    if page_layout.complexity_score > 0.6:
        return "vision_simple"

    # Default to document-level recommendation
    return None  # Use document's ocr_routing_recommendation
```

---

## Validation

### Python Validation (Using Project A Schema)

```python
from pathlib import Path
import json

# Option 1: Import Project A's schema directly
from image_preprocessing_detector.schema import DocumentMetadata

def validate_handoff(metadata_path: Path) -> DocumentMetadata:
    """Validate Project A output metadata."""
    content = metadata_path.read_text()
    return DocumentMetadata.model_validate_json(content)

# Option 2: Standalone validation
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime

class DQSMetadata(BaseModel):
    degradation_score: float = Field(ge=0.0, le=1.0)
    structural_complexity_score: float = Field(ge=0.0, le=1.0)

class PageLayoutSummary(BaseModel):
    page_number: int = Field(ge=1)
    layout_type: Literal["single_column", "multi_column", "three_column", "complex", "unknown"]
    has_tables: bool = False
    has_figures: bool = False
    has_dense_math: bool = False
    has_handwriting: bool = False
    fuzzy_scan: bool = False
    watermark: bool = False
    colorful_background: bool = False
    complexity_score: float = Field(ge=0.0, le=1.0)

class DocumentMetadataMinimal(BaseModel):
    """Minimal validation for Project B consumption."""
    document_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    source_mime: str
    num_pages: int = Field(ge=1)
    pdf_type: Literal["image_only", "born_digital", "hybrid"]
    dqs: DQSMetadata
    pre_ocr_risk: float = Field(ge=0.0, le=1.0)
    ocr_routing_recommendation: Literal["ocr_fast", "ocr_advanced", "vision_simple", "vision_structured"]
    page_layout_summary: list[PageLayoutSummary]
```

### Filesystem Validation

```python
def validate_handoff_directory(doc_dir: Path) -> list[str]:
    """Validate Project A output directory structure."""
    errors = []

    # Check metadata.json exists
    metadata_path = doc_dir / "metadata.json"
    if not metadata_path.exists():
        errors.append(f"Missing metadata.json in {doc_dir}")
        return errors

    # Load and validate metadata
    try:
        metadata = validate_handoff(metadata_path)
    except Exception as e:
        errors.append(f"Invalid metadata.json: {e}")
        return errors

    # Check all page images exist
    for i in range(metadata.num_pages):
        page_path = doc_dir / f"page_{i:04d}.png"
        if not page_path.exists():
            errors.append(f"Missing page image: {page_path}")

    # Verify page count matches
    if len(metadata.pages) != metadata.num_pages:
        errors.append(f"Page count mismatch: {len(metadata.pages)} vs {metadata.num_pages}")

    return errors
```

---

## Integration Checklist for Project B

### Pre-Integration Validation

- [ ] Can parse `metadata.json` without errors
- [ ] All `page_NNNN.png` files exist and are valid PNGs
- [ ] Page images are 300 DPI (verify dimensions match metadata)
- [ ] All required fields present (see Required Fields table)
- [ ] All float scores in valid 0-1 range

### Routing Logic Implementation

- [ ] Handle all 4 `ocr_routing_recommendation` values
- [ ] Implement per-page strategy override logic
- [ ] Handle `pdf_type="born_digital"` text extraction path
- [ ] Implement `teacher_iqa` presence detection

### Error Handling

- [ ] Graceful handling of missing optional fields
- [ ] Fallback strategy when routing recommendation unclear
- [ ] Logging of quality metrics for monitoring

### Performance Expectations

| Metric | Project A Guarantee |
|--------|---------------------|
| Processing time | <2 seconds/page average |
| Output image DPI | 300 (standardized) |
| Output image format | PNG (lossless) |
| Metadata size | <100KB per document |

---

## Performance Guarantees

### Processing Time by Stage

| Stage | GPU | CPU | Notes |
|-------|-----|-----|-------|
| Pre-flight (DPI analysis) | <100ms | <100ms | Per document |
| DPI Upscaling | 310-360ms | 310-360ms | Per page (if needed) |
| Text Gate | <10ms | <10ms | Per page |
| Classical IQA | <25ms | <25ms | Per page (7 detectors) |
| Student ML IQA | <10ms | <40ms | Per page |
| Teacher ML IQA | <30ms | N/A | Per page (if escalated) |
| Layout-Lite | <30ms | <100ms | Per page |
| Corrections | <100ms | <100ms | Per page |
| **Total Pipeline** | **<150ms/page** | **<500ms/page** | End-to-end |

### Quality Targets

| Metric | Target | Description |
|--------|--------|-------------|
| IQA mAP | >0.88 | Multi-label classification accuracy |
| Routing Accuracy | >90% | Correct OCR strategy selection |
| Teacher Escalation | <10% | Pages requiring teacher model |
| Test Coverage | >80% | Code coverage |

### Resource Limits

| Resource | Limit |
|----------|-------|
| Memory per page | <2GB |
| Output image DPI | 300 (standardized) |
| Output format | PNG (lossless) |
| Metadata size | <100KB per document |

---

## Pre-OCR Risk Calculation

Project A calculates `pre_ocr_risk` using the following formula:

```text
pre_ocr_risk = 0.40 * degradation_score
             + 0.30 * complexity_score
             + 0.20 * (1 if pdf_type == "image_only" else 0)
             + 0.10 * (1 if has_handwriting else 0)
```

**Risk Interpretation:**

| Range | Level | Recommended Handling |
|-------|-------|---------------------|
| 0.0-0.3 | Low | Fast OCR engines (Tesseract) |
| 0.3-0.6 | Medium | Cloud OCR (Textract, Vision) |
| 0.6-1.0 | High | Vision models with retry |

---

## Additional Examples

### High-Quality Born-Digital PDF

```json
{
  "document_id": "doc_20251125_002",
  "file_name": "annual_report_2024.pdf",
  "source_mime": "application/pdf",
  "num_pages": 25,
  "pdf_type": "born_digital",
  "languages": ["en"],
  "has_non_latin": false,
  "pre_ocr_risk": 0.12,
  "dqs": {
    "degradation_score": 0.05,
    "structural_complexity_score": 0.35
  },
  "ocr_routing_recommendation": "ocr_fast",
  "page_layout_summary": [
    {
      "page_number": 1,
      "layout_type": "single_column",
      "has_tables": false,
      "has_figures": true,
      "has_dense_math": false,
      "has_handwriting": false,
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.25
    }
  ],
  "upscaling": null,
  "teacher_usage": null,
  "processing_version": {
    "pipeline_version": "1.0.0",
    "iqa_model_hash": "sha256:abc123...",
    "layout_model_hash": null,
    "thresholds": {},
    "timestamp": "2025-11-25T11:00:00Z"
  },
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 300,
      "dpi_effective": 300,
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.98,
        "noise_score": 0.99,
        "contrast_score": 0.95,
        "skew_score": 0.99,
        "compression_score": 0.97,
        "overall_quality": 0.97,
        "device": "cpu",
        "inference_time_ms": 38.2
      },
      "teacher_iqa": null,
      "detected_issues": [],
      "planned_actions": [],
      "elements": [],
      "languages": [],
      "transform_history": []
    }
  ]
}
```

**Project B Action:** Extract embedded text layer directly, skip heavy OCR.

### Low-Quality Scanned Form with Tables

```json
{
  "document_id": "doc_20251125_003",
  "file_name": "tax_form_1040_scan.pdf",
  "source_mime": "application/pdf",
  "num_pages": 2,
  "pdf_type": "image_only",
  "languages": ["en"],
  "has_non_latin": false,
  "pre_ocr_risk": 0.68,
  "dqs": {
    "degradation_score": 0.55,
    "structural_complexity_score": 0.75
  },
  "ocr_routing_recommendation": "vision_structured",
  "page_layout_summary": [
    {
      "page_number": 1,
      "layout_type": "complex",
      "has_tables": true,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": true,
      "fuzzy_scan": true,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.85
    },
    {
      "page_number": 2,
      "layout_type": "complex",
      "has_tables": true,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": true,
      "fuzzy_scan": true,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.80
    }
  ],
  "upscaling": {
    "performed": true,
    "original_dpi": 150,
    "target_dpi": 300,
    "algorithm": "lanczos",
    "processing_time_ms": 680
  },
  "teacher_usage": {
    "pages_with_teacher": [0, 1],
    "escalation_reasons": {
      "0": "high_entropy (0.850 >= 0.800); fuzzy_scan detected",
      "1": "high_entropy (0.820 >= 0.800); fuzzy_scan detected"
    },
    "teacher_device": "cuda",
    "total_teacher_time_ms": 58
  },
  "processing_version": {
    "pipeline_version": "1.0.0",
    "iqa_model_hash": "sha256:abc123...",
    "layout_model_hash": "sha256:def456...",
    "thresholds": {
      "entropy_threshold": 0.8,
      "discrepancy_threshold": 0.3
    },
    "timestamp": "2025-11-25T11:15:00Z"
  },
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 150,
      "dpi_effective": 300,
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.45,
        "noise_score": 0.52,
        "contrast_score": 0.48,
        "skew_score": 0.85,
        "compression_score": 0.78,
        "overall_quality": 0.52,
        "device": "cpu",
        "inference_time_ms": 42.1
      },
      "teacher_iqa": {
        "source": "teacher",
        "blur_score": 0.42,
        "noise_score": 0.48,
        "contrast_score": 0.45,
        "skew_score": 0.88,
        "compression_score": 0.75,
        "overall_quality": 0.48,
        "escalation_reason": "high_entropy (0.850 >= 0.800); fuzzy_scan detected",
        "device": "cuda",
        "inference_time_ms": 28.5
      },
      "detected_issues": [
        {
          "type": "blur",
          "confidence": 0.88,
          "severity": "high",
          "metrics": {"laplacian_variance": 45.2, "blur_score": 0.42}
        },
        {
          "type": "noise",
          "confidence": 0.82,
          "severity": "medium",
          "metrics": {"noise_level": 0.52}
        },
        {
          "type": "low_contrast",
          "confidence": 0.75,
          "severity": "medium",
          "metrics": {"contrast_ratio": 0.45}
        }
      ],
      "planned_actions": [],
      "elements": [],
      "languages": [{"script": "Latin", "confidence": 0.92}],
      "transform_history": [
        {
          "action": "upsample",
          "params": {"scale_factor": 2.0, "algorithm": "lanczos"},
          "started_at": "2025-11-25T11:15:00Z",
          "finished_at": "2025-11-25T11:15:00.340Z",
          "status": "success",
          "error_message": null
        },
        {
          "action": "clahe",
          "params": {"clip_limit": 2.0, "tile_grid_size": [8, 8]},
          "started_at": "2025-11-25T11:15:00.340Z",
          "finished_at": "2025-11-25T11:15:00.380Z",
          "status": "success",
          "error_message": null
        }
      ]
    }
  ]
}
```

**Project B Action:** Use vision_structured with structure prompts, expect handwriting, plan retry strategy.

### Document with Dense Math

```json
{
  "document_id": "doc_20251125_004",
  "file_name": "physics_textbook_ch3.pdf",
  "source_mime": "application/pdf",
  "num_pages": 1,
  "pdf_type": "hybrid",
  "languages": ["en"],
  "has_non_latin": false,
  "pre_ocr_risk": 0.52,
  "dqs": {
    "degradation_score": 0.18,
    "structural_complexity_score": 0.72
  },
  "ocr_routing_recommendation": "vision_structured",
  "page_layout_summary": [
    {
      "page_number": 1,
      "layout_type": "multi_column",
      "has_tables": false,
      "has_figures": true,
      "has_dense_math": true,
      "has_handwriting": false,
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false,
      "complexity_score": 0.72
    }
  ],
  "upscaling": null,
  "teacher_usage": null,
  "processing_version": {
    "pipeline_version": "1.0.0",
    "iqa_model_hash": "sha256:abc123...",
    "layout_model_hash": "sha256:def456...",
    "thresholds": {},
    "timestamp": "2025-11-25T11:30:00Z"
  },
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 300,
      "dpi_effective": 300,
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.92,
        "noise_score": 0.88,
        "contrast_score": 0.85,
        "skew_score": 0.95,
        "compression_score": 0.90,
        "overall_quality": 0.88,
        "device": "cpu",
        "inference_time_ms": 40.5
      },
      "teacher_iqa": null,
      "detected_issues": [],
      "planned_actions": [],
      "elements": [],
      "languages": [{"script": "Latin", "confidence": 0.95}],
      "transform_history": []
    }
  ]
}
```

**Project B Action:** Use vision_structured with math-aware prompting, extract LaTeX notation.

---

## JSON Schema

A complete JSON Schema for external validation is available at:

- **Location:** `docs/schema/document_metadata.schema.json`
- **Draft:** JSON Schema draft-07
- **Usage:**

```bash
# Validate with ajv-cli
npm install -g ajv-cli ajv-formats
ajv validate -s docs/schema/document_metadata.schema.json -d output/doc_123/metadata.json

# Validate with Python jsonschema
pip install jsonschema
python -c "
import json
from jsonschema import validate
schema = json.load(open('docs/schema/document_metadata.schema.json'))
data = json.load(open('output/doc_123/metadata.json'))
validate(data, schema)
print('Valid!')
"
```

---

## Workflow Reference

For detailed pipeline flow visualization, see:

- **PlantUML Diagram:** `docs/_archived/planning/workflows-opus/unified_primary_workflow.puml` (archived 2026-02-09)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0-draft | 2026-02-10 | Added v2.0 planned fields (script detection, handwriting, capture method, page attributes, resolution quality), schema migration guide, updated routing logic |
| 1.0.0 | 2025-11-25 | Initial production specification |

---

## Contact

For questions about Project A output:

- **Schema Issues**: See `src/image_preprocessing_detector/schema.py`
- **JSON Schema**: See `docs/schema/document_metadata.schema.json`
- **Integration Issues**: Create issue in Project A repository
- **Architecture Questions**: See `docs/development/RAG Pipeline/RAG-pipeline-project-overview.md`
- **Pipeline Workflow**: See `docs/_archived/planning/workflows-opus/unified_primary_workflow.puml` (archived 2026-02-09)
