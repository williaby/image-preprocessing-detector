---
schema_type: common
title: "API Reference Overview"
description: "Complete API documentation for Image Preprocessing Detector"
tags: [api_reference, reference, documentation]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Provide comprehensive API reference documentation for developers."
---

> **Note**: These documents describe the planned REST API for Phase 5. The API is not yet fully implemented. See [Project Plan](../planning/PROJECT_PLAN.md) for current Phase 5 status.

Welcome to the Image Preprocessing Detector API reference documentation. This section provides detailed documentation for all public modules, classes, and functions.

## Core Modules

### [Schema](schema.md)

Pydantic v2 models for JSON input/output, including:

- `DetectedIssue` - Representation of detected quality issues
- `DocumentElement` - Per-element metadata for hybrid IQA
- `PageMetadata` - Page-level metadata and quality metrics
- `DocumentMetadata` - Complete document analysis results

**Key Feature**: COCO-aligned bounding boxes `[x, y, width, height]` for LayoutParser integration.

### [Ingestion](ingestion.md)

Document ingestion and normalization:

- PDF extraction and DPI standardization (300 DPI)
- Multi-format support (PDF, PNG, JPEG, TIFF)
- Image validation and preprocessing
- DPI upscaling for low-resolution inputs (Phase 4)

### [Detection](detection.md)

Quality assessment and layout analysis:

- **Text Gate**: Fast text presence detection for routing
- **Classical IQA**: Skew, blur, contrast, noise, JPEG blockiness
- **ML IQA**: Teacher-student ResNet architecture (Phase 2)
- **Layout-Lite**: Coarse page attribute classification (Phase 6)

### [Correction](correction.md)

OpenCV-based image corrections:

- Deskew correction with Hough transform
- CLAHE contrast enhancement
- Unsharp masking for sharpening
- Non-local means denoising
- Transform history tracking

### [Output](output.md)

Results serialization and export:

- DocumentMetadata JSON generation
- Corrected image output
- COCO-format bounding boxes
- Routing recommendations for Unify

## Architecture Patterns

### Multi-Stage Pipeline

The API follows a pipeline architecture with text detection gate:

```python
from image_preprocessing_detector import DocumentProcessor

# Initialize processor
processor = DocumentProcessor()

# Process document
result = processor.process_document("input.pdf")

# Access results
print(f"Quality score: {result.document_quality_score}")
for page in result.pages:
    print(f"Page {page.page_number}: {len(page.detected_issues)} issues")
```

### Teacher-Student ML IQA (Phase 2)

The system uses selective inference for optimal performance:

- **Student Model** (ResNet-18): Default production inference
- **Teacher Model** (ResNet-50): High-capacity fallback for difficult cases
- **Device Priority**: Local GPU → Local CPU → Modal GPU

### Hybrid IQA

Per-element quality assessment for embedded images in documents:

- Classical IQA for pure images
- Layout-aware processing for text documents
- Element-level `quality_issues` in `DocumentElement`

## Usage Examples

### Basic Document Processing

```python
from image_preprocessing_detector import DocumentProcessor
from image_preprocessing_detector.schema import DocumentMetadata

# Process a PDF
processor = DocumentProcessor(config_path="config.yaml")
metadata: DocumentMetadata = processor.process_document("document.pdf")

# Check for quality issues
for page in metadata.pages:
    if page.detected_issues:
        print(f"Page {page.page_number} issues:")
        for issue in page.detected_issues:
            print(f"  - {issue.issue_type}: {issue.severity}")
```

### Configuration

```python
from image_preprocessing_detector import DocumentProcessor

# Custom configuration
config = {
    "ingestion": {
        "target_dpi": 300,
        "enable_upscaling": True
    },
    "detection": {
        "use_ml_iqa": True,
        "ml_device": "cuda"
    },
    "correction": {
        "auto_correct": True,
        "confidence_threshold": 0.7
    }
}

processor = DocumentProcessor(config=config)
```

### Accessing Specific Modules

```python
from image_preprocessing_detector.detection.text_gate import TextGate
from image_preprocessing_detector.detection.iqa_classical import ClassicalIQA

# Use text gate directly
text_gate = TextGate()
has_text = text_gate.detect(image_array)

# Use classical IQA
iqa = ClassicalIQA()
issues = iqa.detect_issues(image_array)
```

## API Stability

- **Stable**: Schema, core pipeline, detection modules
- **Beta**: ML IQA teacher-student (Phase 2)
- **Alpha**: Layout-lite detection (Phase 6)
- **Experimental**: DQS and routing (Phase 8)

## Related Documentation

- [Architecture](../architecture/) - System architecture
- [Project Plan](../planning/PROJECT_PLAN.md) - Implementation roadmap
- [Contributing](../development/contributing.md) - Development guidelines

## Module Reference

For detailed API documentation of each module, see:

::: image_preprocessing_detector
