# Project B Integration Guide

Complete guide for integrating Project A (Preprocessing & IQA) with Project B (OCR Orchestration).

## Overview

Project A delivers:

1. **DocumentMetadata.json**: Quality scores, routing recommendations, page attributes
2. **Corrected Images**: 300 DPI page images with corrections applied

Project B consumes these to:

1. Select appropriate OCR engine based on routing recommendation
2. Apply layout-aware processing based on page attributes
3. Track quality metrics for downstream fusion

---

## Contract Specification

### Output Directory Structure

```
output/
├── {document_id}/
│   ├── metadata.json       # DocumentMetadata JSON
│   ├── page_0000.png       # Corrected page (300 DPI)
│   ├── page_0001.png
│   └── ...
```

### DocumentMetadata.json Schema

```json
{
  "document_id": "doc_abc123",
  "file_name": "contract.pdf",
  "source_mime": "application/pdf",
  "num_pages": 5,
  "pdf_type": "image_only",
  "dqs": {
    "degradation_score": 0.25,
    "structural_complexity_score": 0.40
  },
  "pre_ocr_risk": 0.32,
  "ocr_routing_recommendation": "ocr_advanced",
  "page_layout_summary": [
    {
      "page_index": 0,
      "layout_type": "dense_text",
      "has_tables": false,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": false,
      "structural_complexity": 0.2
    }
  ],
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi": 300,
      "iqa_scores": {
        "blur_score": 0.85,
        "noise_score": 0.92,
        "contrast_score": 0.78,
        "overall_quality": 0.85
      },
      "detected_issues": [
        {
          "issue_type": "skew",
          "severity": 0.3,
          "corrected": true
        }
      ],
      "corrected_image_path": "page_0000.png"
    }
  ],
  "processing_version": {
    "pipeline": "0.1.0",
    "iqa_model": "resnet18-iqa-v1.0.0",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

---

## Required Fields

### Document Level (MUST be present)

| Field | Type | Validation |
|-------|------|------------|
| `document_id` | string | Non-empty, alphanumeric with underscores |
| `file_name` | string | Non-empty |
| `source_mime` | string | Valid MIME type |
| `num_pages` | integer | >= 1 |
| `pdf_type` | enum | `image_only`, `born_digital`, `hybrid` |
| `dqs.degradation_score` | float | 0.0 - 1.0 |
| `dqs.structural_complexity_score` | float | 0.0 - 1.0 |
| `pre_ocr_risk` | float | 0.0 - 1.0 |
| `ocr_routing_recommendation` | enum | See routing values |
| `pages` | array | Length == num_pages |

### Page Level (MUST be present per page)

| Field | Type | Validation |
|-------|------|------------|
| `page_index` | integer | 0 to num_pages-1 |
| `width_px` | integer | > 0 |
| `height_px` | integer | > 0 |
| `dpi` | integer | Typically 300 |
| `corrected_image_path` | string | Relative path to PNG |

---

## Routing Recommendations

### OCR Strategy Selection

| Recommendation | Trigger Conditions | Project B Action |
|----------------|-------------------|------------------|
| `ocr_fast` | DQS < 0.3, simple layout | Use Tesseract/EasyOCR |
| `ocr_advanced` | 0.3 <= DQS < 0.6, or handwriting | Use Textract/Google Vision |
| `vision_simple` | DQS >= 0.6, no tables | Use GPT-4V/Claude Vision |
| `vision_structured` | Tables/forms/math detected | Use vision with structure prompts |

### Page Layout Types

| Layout Type | Description | OCR Considerations |
|-------------|-------------|-------------------|
| `dense_text` | Text-heavy, simple columns | Standard flow |
| `multi_column` | Multiple columns | Column detection needed |
| `table_heavy` | Contains data tables | Table structure extraction |
| `image_heavy` | Contains figures/diagrams | Figure extraction, captions |
| `form_like` | Form/key-value structure | Key-value extraction |
| `mixed` | Complex mixed content | Full analysis |

---

## Example Payloads

### High-Quality Born-Digital PDF

```json
{
  "document_id": "doc_20250115_001",
  "file_name": "annual_report.pdf",
  "source_mime": "application/pdf",
  "num_pages": 25,
  "pdf_type": "born_digital",
  "dqs": {
    "degradation_score": 0.05,
    "structural_complexity_score": 0.35
  },
  "pre_ocr_risk": 0.12,
  "ocr_routing_recommendation": "ocr_fast",
  "page_layout_summary": [
    {
      "page_index": 0,
      "layout_type": "dense_text",
      "has_tables": false,
      "has_figures": true,
      "has_dense_math": false,
      "has_handwriting": false,
      "structural_complexity": 0.25
    }
  ],
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi": 300,
      "iqa_scores": {
        "blur_score": 0.98,
        "noise_score": 0.99,
        "contrast_score": 0.95,
        "overall_quality": 0.97
      },
      "detected_issues": [],
      "corrected_image_path": "page_0000.png"
    }
  ],
  "processing_version": {
    "pipeline": "0.1.0",
    "iqa_model": "resnet18-iqa-v1.0.0",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Low-Quality Scanned Document

```json
{
  "document_id": "doc_20250115_002",
  "file_name": "old_contract_scan.pdf",
  "source_mime": "application/pdf",
  "num_pages": 3,
  "pdf_type": "image_only",
  "dqs": {
    "degradation_score": 0.65,
    "structural_complexity_score": 0.20
  },
  "pre_ocr_risk": 0.72,
  "ocr_routing_recommendation": "vision_simple",
  "page_layout_summary": [
    {
      "page_index": 0,
      "layout_type": "dense_text",
      "has_tables": false,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": true,
      "structural_complexity": 0.30
    }
  ],
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi": 300,
      "iqa_scores": {
        "blur_score": 0.45,
        "noise_score": 0.55,
        "contrast_score": 0.40,
        "overall_quality": 0.35
      },
      "detected_issues": [
        {
          "issue_type": "blur",
          "severity": 0.55,
          "corrected": false
        },
        {
          "issue_type": "low_contrast",
          "severity": 0.60,
          "corrected": true
        },
        {
          "issue_type": "skew",
          "severity": 0.25,
          "corrected": true
        }
      ],
      "corrected_image_path": "page_0000.png"
    }
  ],
  "processing_version": {
    "pipeline": "0.1.0",
    "iqa_model": "resnet18-iqa-v1.0.0",
    "timestamp": "2025-01-15T10:32:00Z"
  }
}
```

### Form with Tables

```json
{
  "document_id": "doc_20250115_003",
  "file_name": "tax_form.pdf",
  "source_mime": "application/pdf",
  "num_pages": 2,
  "pdf_type": "hybrid",
  "dqs": {
    "degradation_score": 0.20,
    "structural_complexity_score": 0.75
  },
  "pre_ocr_risk": 0.55,
  "ocr_routing_recommendation": "vision_structured",
  "page_layout_summary": [
    {
      "page_index": 0,
      "layout_type": "form_like",
      "has_tables": true,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": true,
      "structural_complexity": 0.80
    }
  ],
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi": 300,
      "iqa_scores": {
        "blur_score": 0.88,
        "noise_score": 0.85,
        "contrast_score": 0.82,
        "overall_quality": 0.80
      },
      "detected_issues": [],
      "corrected_image_path": "page_0000.png"
    }
  ],
  "processing_version": {
    "pipeline": "0.1.0",
    "iqa_model": "resnet18-iqa-v1.0.0",
    "timestamp": "2025-01-15T10:35:00Z"
  }
}
```

---

## Schema Validation

### Python Validation

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from pathlib import Path

class IQAScores(BaseModel):
    blur_score: float = Field(ge=0.0, le=1.0)
    noise_score: float = Field(ge=0.0, le=1.0)
    contrast_score: float = Field(ge=0.0, le=1.0)
    overall_quality: float = Field(ge=0.0, le=1.0)

class DQS(BaseModel):
    degradation_score: float = Field(ge=0.0, le=1.0)
    structural_complexity_score: float = Field(ge=0.0, le=1.0)

class PageMetadata(BaseModel):
    page_index: int = Field(ge=0)
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    dpi: int = Field(gt=0)
    iqa_scores: IQAScores
    corrected_image_path: str

    @field_validator('corrected_image_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.endswith('.png'):
            raise ValueError('Corrected image must be PNG')
        return v

class DocumentMetadata(BaseModel):
    document_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    source_mime: str
    num_pages: int = Field(ge=1)
    pdf_type: Literal["image_only", "born_digital", "hybrid"]
    dqs: DQS
    pre_ocr_risk: float = Field(ge=0.0, le=1.0)
    ocr_routing_recommendation: Literal[
        "ocr_fast", "ocr_advanced", "vision_simple", "vision_structured"
    ]
    pages: list[PageMetadata]

    @field_validator('pages')
    @classmethod
    def validate_page_count(cls, v, info):
        if 'num_pages' in info.data and len(v) != info.data['num_pages']:
            raise ValueError(f'pages length must equal num_pages')
        return v

# Validation usage
def validate_handoff(json_path: Path) -> DocumentMetadata:
    """Validate Project A handoff JSON."""
    import json
    with open(json_path) as f:
        data = json.load(f)
    return DocumentMetadata(**data)
```

### JSON Schema (for external validators)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DocumentMetadata",
  "type": "object",
  "required": [
    "document_id", "file_name", "source_mime", "num_pages",
    "pdf_type", "dqs", "pre_ocr_risk", "ocr_routing_recommendation", "pages"
  ],
  "properties": {
    "document_id": {"type": "string", "minLength": 1},
    "file_name": {"type": "string", "minLength": 1},
    "source_mime": {"type": "string"},
    "num_pages": {"type": "integer", "minimum": 1},
    "pdf_type": {"enum": ["image_only", "born_digital", "hybrid"]},
    "dqs": {
      "type": "object",
      "required": ["degradation_score", "structural_complexity_score"],
      "properties": {
        "degradation_score": {"type": "number", "minimum": 0, "maximum": 1},
        "structural_complexity_score": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "pre_ocr_risk": {"type": "number", "minimum": 0, "maximum": 1},
    "ocr_routing_recommendation": {
      "enum": ["ocr_fast", "ocr_advanced", "vision_simple", "vision_structured"]
    },
    "pages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["page_index", "width_px", "height_px", "dpi", "corrected_image_path"],
        "properties": {
          "page_index": {"type": "integer", "minimum": 0},
          "width_px": {"type": "integer", "minimum": 1},
          "height_px": {"type": "integer", "minimum": 1},
          "dpi": {"type": "integer", "minimum": 1},
          "corrected_image_path": {"type": "string", "pattern": ".*\\.png$"}
        }
      }
    }
  }
}
```

---

## Integration Testing Checklist

### Pre-Integration

- [ ] Project A outputs validated against schema
- [ ] All corrected images at 300 DPI
- [ ] Routing recommendations match expected distribution
- [ ] DQS scores correlate with visual quality

### Contract Validation

- [ ] `document_id` format consistent
- [ ] `pages` array length matches `num_pages`
- [ ] All `corrected_image_path` files exist
- [ ] `page_index` values are sequential (0 to n-1)
- [ ] All float scores in valid 0-1 range

### Routing Verification

- [ ] `ocr_fast` documents are indeed high-quality
- [ ] `vision_structured` documents contain tables/forms
- [ ] Handwriting flag correlates with `ocr_advanced`+

### Performance Validation

- [ ] Processing time < 2 seconds per page
- [ ] Memory usage < 2GB per document
- [ ] No memory leaks in batch processing

### Error Handling

- [ ] Corrupt files produce valid error metadata
- [ ] Partial processing produces partial output
- [ ] Errors include correlation IDs for debugging

---

## API Integration

### Using REST API

```bash
# Process document via API
curl -X POST http://project-a:8000/process \
  -F "file=@document.pdf" \
  -o response.json

# Extract document_id from response
DOCUMENT_ID=$(jq -r '.result.document_id' response.json)

# Fetch full metadata (if stored)
curl "http://project-a:8000/documents/${DOCUMENT_ID}/metadata" \
  -o metadata.json
```

### Direct File Processing

```python
from image_preprocessing_detector import process_document

# Process and get metadata
result = process_document("input.pdf", output_dir="output/")

# Result contains DocumentMetadata
print(f"Routing: {result.ocr_routing_recommendation}")
print(f"DQS: {result.dqs.degradation_score}")

# Files written to output/{document_id}/
```

---

## Troubleshooting

### Common Issues

| Issue | Symptom | Resolution |
|-------|---------|------------|
| Missing pages | `pages` shorter than `num_pages` | Check for processing errors |
| Invalid DQS | Scores outside 0-1 | Update to latest pipeline version |
| Missing images | `corrected_image_path` file not found | Check output directory permissions |
| Wrong routing | Fast OCR fails on complex doc | Validate DQS threshold tuning |

### Debugging

```python
# Enable verbose logging
import logging
logging.getLogger("image_preprocessing_detector").setLevel(logging.DEBUG)

# Validate output manually
from image_preprocessing_detector.validation import validate_output
issues = validate_output("output/doc_123/")
for issue in issues:
    print(f"Validation issue: {issue}")
```

---

## Version Compatibility

| Project A Version | Supported Project B Versions | Breaking Changes |
|-------------------|------------------------------|------------------|
| 0.1.x | 0.1.x, 0.2.x | None |
| 0.2.x (planned) | 0.2.x+ | New layout fields |

### Migration Notes

When upgrading Project A, verify:

1. New optional fields don't break Project B parsing
2. Routing recommendation values unchanged
3. DQS calculation methodology consistent
