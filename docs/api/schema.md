---
schema_type: common
title: "Schema API"
description: "Pydantic schema models for document metadata and quality assessment"
tags: [api_reference, documentation]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document the Pydantic schema models for JSON I/O and validation."
---

The schema module provides Pydantic v2 models for representing document metadata, quality issues, and processing results. All models include comprehensive validation and support JSON serialization.

## Overview

The schema uses a hierarchical structure with COCO-aligned bounding boxes for compatibility with LayoutParser and other document analysis tools:

```
DocumentMetadata
  └── PageMetadata (one per page)
      ├── DetectedIssue (quality issues)
      └── DocumentElement (layout elements)
          └── DetectedIssue (per-element quality)
```

## Module Reference

::: image_preprocessing_detector.schema
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      heading_level: 2

## Usage Examples

### Creating Metadata

```python
from image_preprocessing_detector.schema import (
    DocumentMetadata,
    PageMetadata,
    DetectedIssue,
)

# Create document metadata
metadata = DocumentMetadata(
    source_file="document.pdf",
    num_pages=5,
    processing_version="0.1.0",
)

# Add page metadata
page = PageMetadata(
    page_number=1,
    dpi=300,
    dimensions=(2550, 3300),
)
metadata.pages.append(page)

# Add quality issue
issue = DetectedIssue(
    issue_type="blur",
    severity="high",
    confidence=0.92,
    location=[100, 200, 500, 600],  # COCO format: [x, y, width, height]
    metadata={"laplacian_variance": 45.2},
)
page.detected_issues.append(issue)
```

### JSON Serialization

```python
# Serialize to JSON
json_str = metadata.model_dump_json(indent=2)

# Write to file
metadata.to_json_file("output.json")

# Load from file
loaded = DocumentMetadata.from_json_file("output.json")

# Validate JSON
metadata_dict = metadata.model_dump()
```

### Bounding Box Format

All bounding boxes use **COCO format** `[x, y, width, height]`:

```python
from image_preprocessing_detector.schema import DocumentElement

element = DocumentElement(
    element_type="table",
    bbox=[100, 200, 800, 600],  # x=100, y=200, w=800, h=600
    confidence=0.95,
)

# Extract coordinates
x, y, width, height = element.bbox
```

## Key Features

- **Pydantic v2**: Modern validation with discriminated unions
- **COCO Alignment**: Compatible with LayoutParser, Detectron2
- **JSON I/O**: Built-in serialization methods
- **Type Safety**: Comprehensive type hints
- **Hybrid IQA**: Per-element quality assessment for embedded images
- **Transform History**: Audit trail for all preprocessing operations

## See Also

- [Ingestion API](ingestion.md) - Loading and preprocessing
- [Detection API](detection.md) - Quality issue detection
- [Output API](output.md) - JSON generation
