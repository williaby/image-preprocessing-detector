---
schema_type: common
title: Project A to Project B Handoff Specification
tags:
  - rag_pipeline
  - integration
  - specifications
status: published
owner: docs-team
purpose: Define the handoff format between Project A (Preprocessing/IQA) and Project B (OCR).
---

This document defines the handoff format between Project A (Preprocessing & IQA) and Project B (OCR Orchestration).

## Overview

Project A produces a `DocumentMetadata.json` file for each processed document, which contains:

1. Document identification and basic info
2. Per-page quality assessment (IQA scores)
3. Document-level quality score (DQS)
4. OCR routing recommendation
5. Corrected page images (separate files)

## Handoff Files

For each document processed, Project A outputs:

```text
output/
├── {document_id}/
│   ├── metadata.json          # DocumentMetadata JSON
│   ├── page_0000.png          # Corrected page image (300 DPI)
│   ├── page_0001.png
│   ├── ...
│   └── page_NNNN.png
```text

## DocumentMetadata Schema (Required Fields for MVP)

### Root Level (Required for Project B)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | string | YES | Unique document identifier |
| `file_name` | string | YES | Original filename |
| `source_mime` | string | YES | Source MIME type (e.g., "application/pdf") |
| `num_pages` | integer | YES | Total number of pages |
| `pdf_type` | enum | YES | Document classification |
| `dqs` | object | YES | Document Quality Score |
| `pre_ocr_risk` | float | YES | Risk score 0-1 |
| `ocr_routing_recommendation` | enum | YES | Recommended OCR strategy |
| `page_layout_summary` | array | YES | Per-page layout attributes |
| `pages` | array | YES | Per-page metadata |
| `processing_version` | object | YES | Pipeline version info |

### pdf_type Values

```json
{
  "pdf_type": "image_only" | "born_digital" | "hybrid"
}
```text

- `image_only`: Scanned document, all pages are images
- `born_digital`: Digital-native PDF with embedded text
- `hybrid`: Mix of scanned and digital pages

### dqs (Document Quality Score)

```json
{
  "dqs": {
    "degradation_score": 0.75,
    "structural_complexity_score": 0.40
  }
}
```text

- `degradation_score`: 0-1 where 0=worst quality, 1=pristine
- `structural_complexity_score`: 0-1 where 0=simple, 1=very complex

### ocr_routing_recommendation Values

```json
{
  "ocr_routing_recommendation": "ocr_fast" | "ocr_advanced" | "vision_simple" | "vision_structured"
}
```text

| Strategy | When Used | Expected by Project B |
|----------|-----------|----------------------|
| `ocr_fast` | High quality, simple layout | Tesseract/EasyOCR |
| `ocr_advanced` | Medium quality or handwriting | AWS Textract/Google Vision |
| `vision_simple` | Complex layout, no tables | GPT-4V/Claude Vision |
| `vision_structured` | Tables, forms, dense math | GPT-4V with structure prompts |

### page_layout_summary (Per-Page)

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
```text

### pages (Per-Page Metadata)

```json
{
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 300,
      "dpi_effective": 300,
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.82,
        "noise_score": 0.78,
        "contrast_score": 0.85,
        "overall_quality": 0.82,
        "device": "cpu",
        "inference_time_ms": 45.2
      },
      "teacher_iqa": null,
      "detected_issues": [
        {
          "type": "blur",
          "confidence": 0.85,
          "severity": "low",
          "metrics": {"laplacian_variance": 250.5}
        }
      ],
      "planned_actions": [],
      "transform_history": []
    }
  ]
}
```text

### processing_version

```json
{
  "processing_version": {
    "pipeline_version": "0.1.0",
    "iqa_model_hash": "abc123...",
    "layout_model_hash": null,
    "thresholds": {
      "blur_threshold": 100.0,
      "noise_threshold": 15.0
    },
    "timestamp": "2025-11-23T12:00:00Z"
  }
}
```text

## Complete Example

```json
{
  "document_id": "doc_20251123_001",
  "file_name": "contract_scan.pdf",
  "source_mime": "application/pdf",
  "num_pages": 3,
  "pdf_type": "image_only",
  "languages": ["en"],
  "has_non_latin": false,
  "pre_ocr_risk": 0.35,
  "dqs": {
    "degradation_score": 0.72,
    "structural_complexity_score": 0.45
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
  "upscaling": null,
  "teacher_usage": null,
  "processing_version": {
    "pipeline_version": "0.1.0",
    "iqa_model_hash": null,
    "layout_model_hash": null,
    "thresholds": {
      "blur_threshold_critical": 50.0,
      "blur_threshold_high": 100.0,
      "noise_threshold_critical": 20.0,
      "contrast_threshold_low": 0.18
    },
    "timestamp": "2025-11-23T12:00:00Z"
  },
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 300,
      "dpi_effective": 300,
      "ml_iqa": null,
      "teacher_iqa": null,
      "detected_issues": [
        {
          "type": "blur",
          "confidence": 0.75,
          "severity": "low",
          "metrics": {
            "laplacian_variance": 285.3,
            "blur_score": 0.78
          }
        }
      ],
      "planned_actions": [],
      "elements": [],
      "languages": [],
      "transform_history": []
    }
  ]
}
```text

## Project B Consumption Guidelines

### Routing Decision Tree

```text
IF pdf_type == "born_digital":
    # Skip IQA pipeline, use text extraction
    USE text_extraction_path

ELSE:
    IF pre_ocr_risk < 0.3:
        IF ocr_routing_recommendation == "ocr_fast":
            USE tesseract_path
        ELSE:
            USE cloud_ocr_path
    ELSE IF pre_ocr_risk < 0.6:
        IF any(page.has_tables for page in page_layout_summary):
            USE vision_structured_path
        ELSE:
            USE cloud_ocr_path
    ELSE:
        # High risk document
        USE vision_structured_path WITH retry_strategy
```text

### Quality Thresholds

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| `degradation_score` | > 0.7 | 0.4-0.7 | < 0.4 |
| `pre_ocr_risk` | < 0.3 | 0.3-0.6 | > 0.6 |
| `complexity_score` | < 0.3 | 0.3-0.6 | > 0.6 |

### Per-Page Processing

Project B should process pages individually when:

1. `page.teacher_iqa` is present (indicates challenging page)
2. Page has `severity: "high"` or `severity: "critical"` issues
3. Page `complexity_score > 0.6`

## Validation

Project B should validate incoming metadata:

```python
from pydantic import ValidationError
from image_preprocessing_detector.schema import DocumentMetadata

try:
    metadata = DocumentMetadata.model_validate_json(json_content)
except ValidationError as e:
    # Handle invalid metadata
    log_error(f"Invalid metadata: {e}")
```text

## Versioning

The handoff format follows semantic versioning. Breaking changes require major version bump.

- **Current Version**: 0.1.0 (MVP)
- **Schema Location**: `src/image_preprocessing_detector/schema.py`

---

*Last updated: 2025-11-23*
