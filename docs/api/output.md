---
schema_type: common
title: "Output API"
description: "JSON generation with COCO-aligned metadata"
tags: [api_reference, documentation]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document the output module for JSON metadata generation."
---

The output module provides utilities for generating JSON metadata with COCO-aligned bounding boxes for integration with downstream processors.

## Overview

The output pipeline serializes processing results to JSON format:

- **DocumentMetadata**: Complete document processing results
- **COCO Alignment**: Bounding boxes compatible with LayoutParser, Detectron2
- **Transform History**: Audit trail for all preprocessing operations
- **Validation**: Pydantic-based schema validation

## Module Reference

::: image_preprocessing_detector.output.json_generator
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      heading_level: 2

## Usage Examples

### Generate JSON Output

```python
from image_preprocessing_detector.schema import (
    DocumentMetadata,
    PageMetadata,
    DetectedIssue,
)
from image_preprocessing_detector.output import generate_json_output

# Create metadata
metadata = DocumentMetadata(
    source_file="document.pdf",
    num_pages=5,
    processing_version="0.1.0",
)

# Add page data
page = PageMetadata(
    page_number=1,
    dpi=300,
    dimensions=(2550, 3300),
)

# Add detected issues
page.detected_issues.append(DetectedIssue(
    issue_type="blur",
    severity="high",
    confidence=0.92,
    location=[100, 200, 500, 600],  # COCO format
))

metadata.pages.append(page)

# Generate JSON
json_output = generate_json_output(metadata)
print(json_output)
```

### Save to File

```python
# Save JSON to file
metadata.to_json_file("output.json")

# Load from file
loaded_metadata = DocumentMetadata.from_json_file("output.json")
```

### Validate JSON Structure

```python
from pydantic import ValidationError

try:
    # Validate JSON structure
    metadata_dict = metadata.model_dump()
    DocumentMetadata.model_validate(metadata_dict)
    print("JSON structure valid")
except ValidationError as e:
    print(f"Validation errors: {e}")
```

## JSON Schema Structure

### Complete Example

```json
{
  "source_file": "document.pdf",
  "num_pages": 5,
  "processing_version": "0.1.0",
  "pages": [
    {
      "page_number": 1,
      "dpi": 300,
      "dimensions": [2550, 3300],
      "detected_issues": [
        {
          "issue_type": "blur",
          "severity": "high",
          "confidence": 0.92,
          "location": [100, 200, 500, 600],
          "metadata": {
            "laplacian_variance": 45.2,
            "threshold": 100.0
          }
        }
      ],
      "elements": [
        {
          "element_type": "table",
          "bbox": [100, 200, 800, 600],
          "confidence": 0.95,
          "quality_issues": [],
          "metadata": {
            "num_rows": 10,
            "num_cols": 5
          }
        }
      ],
      "transform_history": [
        {
          "transform_type": "deskew",
          "parameters": {"angle": -2.5},
          "timestamp": "2025-11-08T12:00:00Z"
        }
      ]
    }
  ],
  "created_at": "2025-11-08T12:00:00Z",
  "transform_history": []
}
```

## COCO Bounding Box Format

All bounding boxes use **COCO format** `[x, y, width, height]`:

```python
# COCO format
bbox = [100, 200, 800, 600]  # x=100, y=200, width=800, height=600

# Extract coordinates
x, y, width, height = bbox

# Convert to corner format if needed
x1, y1 = x, y
x2, y2 = x + width, y + height
```

**Why COCO?**
- Industry standard for object detection
- Compatible with LayoutParser, Detectron2, YOLO
- Simplifies integration with downstream tools

## Integration with Downstream Tools

### LayoutParser Integration

```python
import layoutparser as lp

# Load results
metadata = DocumentMetadata.from_json_file("output.json")

# Convert to LayoutParser format
for page in metadata.pages:
    for element in page.elements:
        block = lp.TextBlock(
            block=lp.Rectangle(
                x_1=element.bbox[0],
                y_1=element.bbox[1],
                x_2=element.bbox[0] + element.bbox[2],
                y_2=element.bbox[1] + element.bbox[3],
            ),
            type=element.element_type,
            score=element.confidence,
        )
```

### Tesseract OCR Integration

```python
from PIL import Image
import pytesseract

# Load image and metadata
image = Image.open("page1.jpg")
metadata = DocumentMetadata.from_json_file("output.json")

# OCR detected text regions
for element in metadata.pages[0].elements:
    if element.element_type == "text":
        x, y, w, h = element.bbox
        crop = image.crop((x, y, x + w, y + h))
        text = pytesseract.image_to_string(crop)
        print(f"Text: {text}")
```

## Schema Validation

The output module enforces strict schema validation:

```python
# Valid JSON passes
valid_metadata = DocumentMetadata(
    source_file="doc.pdf",
    num_pages=1,
    processing_version="0.1.0",
)
json_output = generate_json_output(valid_metadata)  # Success

# Invalid JSON fails
try:
    invalid_metadata = DocumentMetadata(
        source_file="",  # Empty string not allowed
        num_pages=-1,     # Negative not allowed
        processing_version="0.1.0",
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| **JSON Generation** | < 1ms | Fast serialization |
| **File Write** | ~10ms | I/O dependent |
| **Validation** | < 1ms | Pydantic validation |

## Best Practices

1. **Validate Before Export**: Ensure metadata is valid before generating JSON
2. **Use COCO Format**: Always use `[x, y, width, height]` for bounding boxes
3. **Track Transforms**: Maintain complete transform history for audit trails
4. **Version Consistently**: Use semantic versioning for `processing_version`
5. **Test Integration**: Validate compatibility with downstream tools

## See Also

- [Schema API](schema.md) - Pydantic models
- [Detection API](detection.md) - Quality assessment
- [Correction API](correction.md) - Preprocessing operations
