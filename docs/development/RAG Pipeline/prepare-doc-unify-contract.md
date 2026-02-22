---
schema_type: common
title: "Prepare-Doc → Unify Interface Contract"
description: "Comprehensive contract defining all handoffs between Prepare-Doc and Unify (OCR Orchestration)"
tags:
  - pipeline
  - integration
status: published
owner: core-maintainer
purpose: "Define the complete interface contract between Prepare-Doc and Unify, including data formats, model registry, and processing recommendations."
---

Version 2.0.0 | Last Updated: 2025-11

## Executive Summary

This document defines the complete interface contract between:

- **Prepare-Doc**: Document ingestion, quality assessment, corrections, layout detection, and element classification
- **Unify (OCR Orchestration)**: Docling-based document parsing with tiered VLM validation and hierarchical chunking

The contract covers three handoff types:

1. **Data Handoff**: DocumentMetadata JSON + corrected images per document
2. **Model Handoff**: Pre-trained ONNX models for element classification
3. **Configuration Handoff**: Thresholds and routing parameters

---

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           PREPARE-DOC                                     │
│                    (Preprocessing & IQA)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Ingestion → IQA → Corrections → DocLayout-YOLO → Element Classification │
│                                                                         │
│  OUTPUTS:                                                               │
│  ├── DocumentMetadata.json (per document)                              │
│  ├── Corrected page images (300 DPI PNG)                               │
│  └── Model Registry (ONNX models for Unify)                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           UNIFY                                     │
│                    (OCR Orchestration)                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUTS:                                                                │
│  ├── DocumentMetadata.json (routing decisions)                         │
│  ├── Corrected page images                                             │
│  └── Model Registry (element classifiers)                              │
│                                                                         │
│  Processing: Docling → Element Routing → Specialists → VLM Validation  │
│                                                                         │
│  OUTPUT: OCRDocument.json → Chunk                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Handoff: DocumentMetadata.json

### 2.1 Output Directory Structure

```text
output/
├── {document_id}/
│   ├── metadata.json           # DocumentMetadata JSON (schema v2.0)
│   ├── page_0000.png           # Corrected page image (300 DPI)
│   ├── page_0001.png
│   ├── ...
│   └── elements/               # Optional: cropped element images
│       ├── page_0000_elem_001.png
│       └── ...
```

### 2.2 DocumentMetadata Schema v2.0

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DocumentMetadata",
  "version": "2.0.0",
  "type": "object",
  "required": [
    "schema_version",
    "document_id",
    "file_name",
    "source_mime",
    "num_pages",
    "pdf_type",
    "quality_assessment",
    "processing_recommendation",
    "pages"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "2.0.0"
    },
    "document_id": {
      "type": "string",
      "minLength": 1,
      "description": "Unique identifier for the document"
    },
    "file_name": {
      "type": "string",
      "minLength": 1
    },
    "source_mime": {
      "type": "string",
      "enum": ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
    },
    "num_pages": {
      "type": "integer",
      "minimum": 1
    },
    "pdf_type": {
      "type": "string",
      "enum": ["image_only", "born_digital", "hybrid"],
      "description": "Classification of PDF content type"
    },
    "quality_assessment": {
      "$ref": "#/definitions/QualityAssessment"
    },
    "processing_recommendation": {
      "$ref": "#/definitions/ProcessingRecommendation"
    },
    "pages": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/PageMetadata"
      }
    },
    "processing_version": {
      "$ref": "#/definitions/ProcessingVersion"
    }
  }
}
```

### 2.3 Quality Assessment (Document Level)

```json
{
  "quality_assessment": {
    "degradation_score": 0.25,
    "structural_complexity_score": 0.40,
    "pre_ocr_risk": 0.32,
    "iqa_summary": {
      "blur_score": 0.85,
      "noise_score": 0.92,
      "contrast_score": 0.78,
      "lighting_score": 0.88,
      "compression_score": 0.95,
      "overall_quality": 0.85
    }
  }
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `degradation_score` | float | 0.0-1.0 | Weighted combination of IQA issues (higher = worse) |
| `structural_complexity_score` | float | 0.0-1.0 | Layout complexity indicator |
| `pre_ocr_risk` | float | 0.0-1.0 | Predicted OCR difficulty |
| `iqa_summary` | object | — | Per-metric quality scores |

### 2.4 Processing Recommendation (NEW in v2.0)

Replaces the previous `ocr_routing_recommendation` enum with richer guidance:

```json
{
  "processing_recommendation": {
    "tier": "vlm_assisted",
    "tier_confidence": 0.85,
    "vlm_validation": {
      "recommended": true,
      "reasons": ["has_tables", "moderate_degradation"],
      "estimated_benefit": "medium",
      "priority_elements": ["table", "handwriting"]
    },
    "specialist_routing": {
      "tables": "structeqtable",
      "formulas": "texify",
      "handwriting": "trocr"
    }
  }
}
```

#### Processing Tiers

| Tier | Trigger Conditions | Unify Action |
|------|-------------------|------------------|
| `standard` | DQS < 0.3, born_digital, simple layout | Docling StandardPipeline |
| `vlm_assisted` | 0.3 ≤ DQS < 0.6, tables/math, moderate complexity | Docling + Granite-Docling VLM |
| `vlm_validated` | DQS ≥ 0.6, handwriting, complex layout | Docling ∥ VLM parallel validation |

#### VLM Validation Guidance

| Field | Type | Description |
|-------|------|-------------|
| `recommended` | bool | Whether VLM validation should run |
| `reasons` | array[string] | Factors triggering recommendation |
| `estimated_benefit` | enum | `low`, `medium`, `high` |
| `priority_elements` | array[string] | Element types to prioritize for VLM |

#### Specialist Routing

Maps element types to recommended specialist processors:

| Element Type | Specialist Options | Selection Criteria |
|--------------|-------------------|-------------------|
| `table` | `tableformer`, `structeqtable` | Based on table_type classification |
| `formula` | `texify`, `unimernet`, `granite-docling` | Based on formula complexity |
| `handwriting` | `trocr`, `trocr-domain` | Based on domain match |
| `code` | `docling-standard` | Preserve formatting |

### 2.5 Page Metadata (Enhanced)

```json
{
  "pages": [{
    "page_index": 0,
    "dimensions": {
      "width_px": 2550,
      "height_px": 3300,
      "dpi": 300
    },
    "quality_metrics": {
      "blur_score": 0.85,
      "noise_score": 0.92,
      "contrast_score": 0.78,
      "lighting_score": 0.88,
      "compression_score": 0.95,
      "overall_quality": 0.85
    },
    "layout_attributes": {
      "layout_type": "multi_column",
      "num_columns": 2,
      "has_tables": true,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": true,
      "has_code": false,
      "structural_complexity": 0.45
    },
    "detected_issues": [
      {
        "issue_type": "skew",
        "severity": 0.3,
        "corrected": true
      }
    ],
    "corrections_applied": ["deskew", "clahe"],
    "corrected_image_path": "page_0000.png",
    "detected_elements": [...]
  }]
}
```

### 2.6 Detected Elements (NEW in v2.0)

Per-page array of detected elements with classifications from Phase 9 models:

```json
{
  "detected_elements": [
    {
      "element_id": "page_0_elem_001",
      "element_type": "text",
      "bbox": [100, 200, 400, 50],
      "bbox_normalized": [0.039, 0.061, 0.157, 0.015],
      "detection_confidence": 0.95,
      "classifications": {
        "is_handwritten": false,
        "handwriting_confidence": 0.02,
        "complexity": "clean_print",
        "specialist_needed": false
      }
    },
    {
      "element_id": "page_0_elem_002",
      "element_type": "table",
      "bbox": [50, 300, 500, 200],
      "bbox_normalized": [0.020, 0.091, 0.196, 0.061],
      "detection_confidence": 0.92,
      "classifications": {
        "table_type": "financial",
        "complexity": "merged_cells",
        "has_merged_cells": true,
        "appears_numeric": true,
        "specialist_needed": true,
        "recommended_specialist": "structeqtable",
        "validate_calculations": true
      }
    },
    {
      "element_id": "page_0_elem_003",
      "element_type": "formula",
      "bbox": [100, 550, 300, 80],
      "bbox_normalized": [0.039, 0.167, 0.118, 0.024],
      "detection_confidence": 0.88,
      "classifications": {
        "formula_type": "block_equation",
        "complexity": "multi_line",
        "specialist_needed": true,
        "recommended_specialist": "texify"
      }
    },
    {
      "element_id": "page_0_elem_004",
      "element_type": "handwriting",
      "bbox": [400, 600, 150, 40],
      "bbox_normalized": [0.157, 0.182, 0.059, 0.012],
      "detection_confidence": 0.85,
      "classifications": {
        "is_handwritten": true,
        "handwriting_confidence": 0.92,
        "specialist_needed": true,
        "recommended_specialist": "trocr"
      }
    },
    {
      "element_id": "page_0_elem_005",
      "element_type": "watermark",
      "bbox": [100, 100, 400, 400],
      "bbox_normalized": [0.039, 0.030, 0.157, 0.121],
      "detection_confidence": 0.78,
      "classifications": {
        "is_parasitic": true,
        "parasitic_type": "text_watermark",
        "ocr_action": "skip"
      }
    }
  ]
}
```

#### Element Types

| Type | Source | Description | OCR Action |
|------|--------|-------------|------------|
| `text` | DocLayout-YOLO | Printed text regions | Standard OCR |
| `handwriting` | Extended YOLO | Handwritten text | TrOCR specialist |
| `table` | DocLayout-YOLO | Data tables | TableFormer/StructEqTable |
| `formula` | DocLayout-YOLO | Math equations | Texify/UniMERNet |
| `picture` | DocLayout-YOLO | Images/photos | Caption extraction |
| `chart` | Extended YOLO | Charts/graphs | Chart-to-data extraction |
| `code_block` | Extended YOLO | Code snippets | Preserve formatting |
| `watermark` | Extended YOLO | Watermarks | Skip OCR |
| `stamp` | Extended YOLO | Stamps | Metadata extraction |
| `signature` | Extended YOLO | Signatures | Flag for review |
| `page_header` | DocLayout-YOLO | Page headers | Mark parasitic |
| `page_footer` | DocLayout-YOLO | Page footers | Mark parasitic |

#### Parasitic Content

Elements marked with `is_parasitic: true` should be:

1. **Excluded from RAG chunks** - Not included in semantic chunking
2. **Preserved in metadata** - Available for document identification
3. **Not OCR'd** (watermarks) or **OCR'd for metadata only** (headers/footers)

### 2.7 Parasitic Summary (NEW)

Page-level summary of parasitic content for quick filtering:

```json
{
  "parasitic_summary": {
    "has_watermark": true,
    "has_header": true,
    "has_footer": true,
    "watermark_type": "text_watermark",
    "parasitic_element_ids": ["page_0_elem_005", "page_0_elem_006"]
  }
}
```

---

## 3. Model Handoff: Model Registry

Prepare-Doc trains and exports models that Unify loads for inference. Each model ships in **full** and **light** variants for flexible deployment based on available compute resources.

### 3.1 Registry Location

```text
# Local filesystem - each model has full/ and light/ subdirectories
models/
├── registry.json                           # Master index with variant support
├── doclayout_yolo_extended/
│   ├── full/yolov10_17class.onnx          # ~100MB, 1600px, Modal L4 target
│   ├── light/yolov10n_17class.onnx        # ~20MB, 1024px, CPU target
│   ├── class_mapping.json                  # Shared
│   └── benchmarks.json                     # CPU/GPU/Modal L4 comparison
├── handwriting_classifier/
│   ├── full/resnet18_handwriting.onnx     # ~47MB
│   ├── light/mobilenetv3_handwriting.onnx # ~10MB
│   └── benchmarks.json
├── table_type_classifier/
│   ├── full/resnet18_table.onnx
│   ├── light/mobilenetv3_table.onnx
│   └── benchmarks.json
├── formula_complexity_classifier/
│   ├── full/resnet18_formula.onnx
│   ├── light/mobilenetv3_formula.onnx
│   └── benchmarks.json
└── parasitic_detector/
    ├── full/resnet18_parasitic.onnx
    ├── light/mobilenetv3_parasitic.onnx
    └── benchmarks.json

# GCS backup
gs://image_detection_b/models/phase9/
```

### 3.2 Model Variant Strategy

Based on Phase 4 benchmarks, local GPUs (P2000, RTX A500) provide minimal benefit for small models—CPU is often faster due to transfer overhead. Variants are selected automatically:

| Device Available | Recommended Variant | Rationale |
|-----------------|---------------------|-----------|
| Modal L4 | `full` | True GPU acceleration (7-170x speedup) |
| CPU only | `light` | MobileNetV3 optimized for CPU inference |
| Local GPU (P2000/A500) | `light` | Negative speedup with full models |

### 3.3 Registry Manifest (registry.json)

```json
{
  "registry_version": "2.0.0",
  "created_date": "2025-12-01",
  "default_variant": "light",
  "models": {
    "doclayout_yolo_extended": {
      "classes": 17,
      "class_mapping_path": "doclayout_yolo_extended/class_mapping.json",
      "benchmarks_path": "doclayout_yolo_extended/benchmarks.json",
      "variants": {
        "full": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "doclayout_yolo_extended/full/yolov10_17class.onnx",
          "architecture": "yolov10",
          "input_size": [1600, 1600],
          "size_mb": 100,
          "recommended_device": "modal_l4",
          "training_dataset": "DocLayNet + custom",
          "performance": {
            "mAP_50": 0.85,
            "inference_ms_modal_l4": 15,
            "inference_ms_cpu": 180
          }
        },
        "light": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "doclayout_yolo_extended/light/yolov10n_17class.onnx",
          "architecture": "yolov10n",
          "input_size": [1024, 1024],
          "size_mb": 20,
          "recommended_device": "cpu",
          "performance": {
            "mAP_50": 0.78,
            "inference_ms_cpu": 80
          }
        }
      }
    },
    "handwriting_classifier": {
      "classes": 2,
      "class_names": ["printed", "handwritten"],
      "benchmarks_path": "handwriting_classifier/benchmarks.json",
      "variants": {
        "full": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "handwriting_classifier/full/resnet18_handwriting.onnx",
          "architecture": "resnet18",
          "input_size": [224, 224],
          "size_mb": 47,
          "recommended_device": "modal_l4",
          "performance": {
            "accuracy": 0.96,
            "inference_ms_modal_l4": 1.5,
            "inference_ms_cpu": 10
          }
        },
        "light": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "handwriting_classifier/light/mobilenetv3_handwriting.onnx",
          "architecture": "mobilenetv3_small",
          "input_size": [224, 224],
          "size_mb": 10,
          "recommended_device": "cpu",
          "performance": {
            "accuracy": 0.92,
            "inference_ms_cpu": 4
          }
        }
      }
    },
    "table_type_classifier": {
      "classes": 6,
      "class_names": ["simple_grid", "merged_header", "nested_rows", "financial", "form_like", "scientific"],
      "variants": {
        "full": {
          "path": "table_type_classifier/full/resnet18_table.onnx",
          "architecture": "resnet18",
          "input_size": [384, 384]
        },
        "light": {
          "path": "table_type_classifier/light/mobilenetv3_table.onnx",
          "architecture": "mobilenetv3_small",
          "input_size": [384, 384]
        }
      }
    },
    "formula_complexity_classifier": {
      "classes": 5,
      "class_names": ["simple_inline", "block_equation", "multi_line", "matrix", "handwritten_math"],
      "variants": {
        "full": {
          "path": "formula_complexity_classifier/full/resnet18_formula.onnx",
          "architecture": "resnet18"
        },
        "light": {
          "path": "formula_complexity_classifier/light/mobilenetv3_formula.onnx",
          "architecture": "mobilenetv3_small"
        }
      }
    }
  }
}
```

### 3.4 Model Loading Contract

Unify MUST load models using this interface with variant support:

```python
from pathlib import Path
from typing import Literal
import onnxruntime as ort
import json

VariantType = Literal["full", "light", "auto"]

class ProjectAModelRegistry:
    """Load and manage models trained by Prepare-Doc with variant support."""

    def __init__(self, registry_path: Path, default_variant: VariantType = "auto"):
        with open(registry_path / "registry.json") as f:
            self.manifest = json.load(f)
        self.registry_path = registry_path
        self.default_variant = default_variant
        self._sessions = {}
        self._device = self._detect_device()

    def _detect_device(self) -> str:
        """Detect best available device."""
        try:
            import modal
            # Check if running on Modal
            if hasattr(modal, 'is_local') and not modal.is_local():
                return "modal_l4"
        except ImportError:
            pass
        return "cpu"  # Default to CPU (local GPU not recommended)

    def _select_variant(self, model_name: str, variant: VariantType) -> str:
        """Select appropriate variant based on device and request."""
        if variant != "auto":
            return variant

        # Auto-select based on device
        if self._device == "modal_l4":
            return "full"
        return "light"  # CPU or local GPU -> use light

    def load_model(
        self,
        model_name: str,
        variant: VariantType = "auto"
    ) -> ort.InferenceSession:
        """Load ONNX model by name with variant selection."""
        selected_variant = self._select_variant(model_name, variant)
        cache_key = f"{model_name}:{selected_variant}"

        if cache_key not in self._sessions:
            model_info = self.manifest["models"][model_name]
            variant_info = model_info["variants"][selected_variant]
            model_path = self.registry_path / variant_info["path"]

            # Select providers based on device
            if self._device == "modal_l4":
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                providers = ["CPUExecutionProvider"]

            self._sessions[cache_key] = ort.InferenceSession(
                str(model_path),
                providers=providers
            )
        return self._sessions[cache_key]

    def get_class_mapping(self, model_name: str) -> dict:
        """Get class name to index mapping."""
        model_info = self.manifest["models"][model_name]
        if "class_mapping_path" in model_info:
            with open(self.registry_path / model_info["class_mapping_path"]) as f:
                return json.load(f)
        elif "class_names" in model_info:
            return {name: i for i, name in enumerate(model_info["class_names"])}
        return {}

    def get_input_size(self, model_name: str, variant: VariantType = "auto") -> tuple[int, int]:
        """Get expected input dimensions for variant."""
        selected_variant = self._select_variant(model_name, variant)
        model_info = self.manifest["models"][model_name]
        variant_info = model_info["variants"][selected_variant]
        return tuple(variant_info["input_size"])

    def get_benchmarks(self, model_name: str) -> dict:
        """Load benchmark results for model (all variants)."""
        model_info = self.manifest["models"][model_name]
        if "benchmarks_path" in model_info:
            with open(self.registry_path / model_info["benchmarks_path"]) as f:
                return json.load(f)
        return {}
```

### 3.5 Version Compatibility

| Prepare-Doc Model Version | Compatible Unify Versions |
|------------------------|------------------------------|
| registry v1.0.x | Unify v1.0.x |
| registry v1.1.x | Unify v1.0.x, v1.1.x |

**Breaking Changes Requiring Unify Update:**

- Class additions to DocLayout-YOLO (new element types)
- Input size changes
- Output format changes

---

## 4. Configuration Handoff

### 4.1 Threshold Configuration

Prepare-Doc provides calibrated thresholds that Unify uses for routing:

```yaml
# configs/project_b_thresholds.yaml

# Processing tier thresholds
tier_thresholds:
  standard_max_dqs: 0.3
  vlm_assisted_max_dqs: 0.6
  # Above 0.6 = vlm_validated

# VLM validation triggers
vlm_triggers:
  handwriting_present: true
  table_complexity_threshold: 0.5
  formula_present: true
  degradation_above: 0.4

# Specialist routing
specialist_selection:
  table:
    simple_grid: tableformer
    merged_header: structeqtable
    nested_rows: structeqtable
    financial: tableformer  # with calculation validation
    form_like: docling
    scientific: structeqtable
  formula:
    simple_inline: granite-docling
    block_equation: texify
    multi_line: texify
    matrix: unimernet
    handwritten_math: unimernet
  handwriting:
    default: trocr
    domain_specific: trocr-domain  # if available

# Confidence thresholds for element classification
classification_thresholds:
  handwriting_classifier: 0.7
  table_type_classifier: 0.6
  formula_complexity_classifier: 0.6
  element_detection: 0.5
```

### 4.2 Parasitic Content Rules

```yaml
# configs/parasitic_rules.yaml

# Elements always marked parasitic
always_parasitic:
  - watermark
  - stamp
  - page_header
  - page_footer

# Elements conditionally parasitic
conditionally_parasitic:
  signature:
    action: flag_for_review
    include_in_metadata: true
    include_in_chunks: false

# OCR actions by parasitic type
ocr_actions:
  watermark: skip
  stamp: metadata_only
  page_header: metadata_only
  page_footer: metadata_only
  signature: flag_only
```

---

## 5. Validation Requirements

### 5.1 Prepare-Doc Output Validation

Before handoff, Prepare-Doc MUST validate:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from pathlib import Path

class ElementClassification(BaseModel):
    is_handwritten: Optional[bool] = None
    handwriting_confidence: Optional[float] = Field(None, ge=0, le=1)
    is_parasitic: Optional[bool] = None
    specialist_needed: Optional[bool] = None
    recommended_specialist: Optional[str] = None

class DetectedElement(BaseModel):
    element_id: str
    element_type: str
    bbox: list[int] = Field(..., min_length=4, max_length=4)
    bbox_normalized: list[float] = Field(..., min_length=4, max_length=4)
    detection_confidence: float = Field(..., ge=0, le=1)
    classifications: ElementClassification

class PageMetadata(BaseModel):
    page_index: int = Field(..., ge=0)
    dimensions: dict
    quality_metrics: dict
    layout_attributes: dict
    corrected_image_path: str
    detected_elements: list[DetectedElement]

    @field_validator('corrected_image_path')
    @classmethod
    def validate_image_exists(cls, v: str, info) -> str:
        # Validation logic
        return v

class ProcessingRecommendation(BaseModel):
    tier: Literal["standard", "vlm_assisted", "vlm_validated"]
    tier_confidence: float = Field(..., ge=0, le=1)
    vlm_validation: dict

class DocumentMetadata(BaseModel):
    schema_version: Literal["2.0.0"]
    document_id: str
    file_name: str
    num_pages: int = Field(..., ge=1)
    pdf_type: Literal["image_only", "born_digital", "hybrid"]
    quality_assessment: dict
    processing_recommendation: ProcessingRecommendation
    pages: list[PageMetadata]

    @field_validator('pages')
    @classmethod
    def validate_page_count(cls, v, info):
        if len(v) != info.data.get('num_pages', 0):
            raise ValueError('pages length must equal num_pages')
        return v
```

### 5.2 Unify Input Validation

Unify MUST validate received data:

```python
def validate_handoff(metadata_path: Path, output_dir: Path) -> list[str]:
    """Validate Prepare-Doc handoff package."""
    errors = []

    # Load and validate JSON
    try:
        with open(metadata_path) as f:
            data = json.load(f)
        metadata = DocumentMetadata(**data)
    except Exception as e:
        errors.append(f"Schema validation failed: {e}")
        return errors

    # Validate schema version
    if metadata.schema_version != "2.0.0":
        errors.append(f"Unsupported schema version: {metadata.schema_version}")

    # Validate all images exist
    for page in metadata.pages:
        image_path = output_dir / page.corrected_image_path
        if not image_path.exists():
            errors.append(f"Missing image: {page.corrected_image_path}")

    # Validate element IDs are unique
    all_element_ids = []
    for page in metadata.pages:
        for elem in page.detected_elements:
            if elem.element_id in all_element_ids:
                errors.append(f"Duplicate element_id: {elem.element_id}")
            all_element_ids.append(elem.element_id)

    return errors
```

---

## 6. Error Handling

### 6.1 Processing Errors

When Prepare-Doc encounters errors, it MUST still produce valid output:

```json
{
  "document_id": "doc_error_001",
  "processing_status": "partial_failure",
  "errors": [
    {
      "page_index": 2,
      "error_type": "detection_failure",
      "error_message": "DocLayout-YOLO inference timeout",
      "fallback_applied": "cv_based_detection"
    }
  ],
  "pages": [
    {
      "page_index": 0,
      "status": "success",
      "detected_elements": [...]
    },
    {
      "page_index": 1,
      "status": "success",
      "detected_elements": [...]
    },
    {
      "page_index": 2,
      "status": "fallback",
      "detected_elements": [],
      "fallback_reason": "detection_failure"
    }
  ]
}
```

### 6.2 Unify Error Response

Unify MUST handle:

| Error Type | Response |
|------------|----------|
| Missing metadata.json | Reject document, log error |
| Invalid schema version | Attempt compatibility mode or reject |
| Missing page images | Process available pages, flag missing |
| Unknown element type | Treat as `text`, log warning |
| Missing model in registry | Use fallback model or skip classification |

---

## 7. Performance Requirements

### 7.1 Prepare-Doc Outputs

| Metric | Requirement |
|--------|-------------|
| Processing latency | < 500ms/page (GPU), < 2s/page (CPU) |
| Output JSON size | < 1MB per 100 pages |
| Image format | PNG, 300 DPI, RGB |
| Image compression | lossless (PNG) |

### 7.2 Handoff Timing

| Operation | SLA |
|-----------|-----|
| Metadata JSON write | < 100ms |
| Image write (per page) | < 500ms |
| Model registry load | < 5s (first load) |
| Model inference (per element) | < 50ms |

---

## 8. Versioning and Migration

### 8.1 Schema Versioning

- **Major version** (X.0.0): Breaking changes requiring Unify code updates
- **Minor version** (0.X.0): New optional fields, backward compatible
- **Patch version** (0.0.X): Bug fixes, no schema changes

### 8.2 Migration: v1.0 → v2.0

Key changes from v1.0 (original handoff doc) to v2.0:

| v1.0 Field | v2.0 Field | Change |
|------------|------------|--------|
| `ocr_routing_recommendation` | `processing_recommendation.tier` | Enum changed |
| — | `processing_recommendation.vlm_validation` | New |
| — | `pages[].detected_elements` | New |
| — | `pages[].parasitic_summary` | New |
| `page_layout_summary` | `pages[].layout_attributes` | Moved into page |

**Backward Compatibility:**

Unify v1.x can read v2.0 metadata by ignoring new fields. Unify v2.x requires v2.0 metadata.

---

## 9. Testing Checklist

### 9.1 Integration Tests

- [ ] All JSON outputs validate against schema
- [ ] All page images exist and are valid PNGs
- [ ] Element IDs are unique across document
- [ ] Bounding boxes are within page dimensions
- [ ] Classification confidences are in [0, 1] range
- [ ] Parasitic elements correctly flagged
- [ ] Model registry loads successfully
- [ ] All registered models produce valid outputs

### 9.2 End-to-End Tests

- [ ] Born-digital PDF → `standard` tier recommendation
- [ ] Scanned PDF with tables → `vlm_assisted` tier
- [ ] Handwritten document → `vlm_validated` tier
- [ ] Watermarked document → watermark detected and flagged
- [ ] Multi-page document → all pages processed
- [ ] Corrupt page → graceful degradation

---

## 10. Contact and Support

| Role | Responsibility |
|------|----------------|
| Prepare-Doc Team | Schema changes, model updates, IQA issues |
| Unify Team | Routing logic, OCR integration, chunking |
| Shared | Threshold calibration, performance optimization |

**Change Request Process:**

1. Propose change in GitHub issue
2. Review impact on both projects
3. Update contract document
4. Implement in Prepare-Doc
5. Update Unify
6. Integration testing
7. Deploy

---

## Appendix A: Complete Example Payload

See `docs/examples/handoff_example_v2.json` for a complete example document.

## Appendix B: Class Mapping Reference

See `models/doclayout_yolo_extended/class_mapping.json` for the authoritative class list.
