---
schema_type: common
title: "ADR-009: COCO Bounding Box Format Standardization"
description: "Decision to use COCO format [x, y, width, height] for bounding boxes
  instead of corner format"
tags:
- adr
- architecture
- bounding_boxes
- coco_format
- interoperability
- layout_detection
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to standardize on COCO bounding box format for downstream
  compatibility."
---


**Status**: ✅ **Accepted**
**Date**: 2025-01-15 (Phase 0 Schema Design)
**Deciders**: Byron Williams
**Related**: schema.py, LayoutParser Integration, Phase 0 Foundation

## Context

### Problem Statement

Bounding boxes for detected document elements can be represented in multiple formats:

1. **COCO Format**: `[x, y, width, height]`
   - x, y: Top-left corner coordinates
   - width, height: Box dimensions

2. **Corner Format**: `[x1, y1, x2, y2]`
   - x1, y1: Top-left corner
   - x2, y2: Bottom-right corner

3. **Center Format**: `[cx, cy, width, height]`
   - cx, cy: Center coordinates
   - width, height: Box dimensions

### Requirements

1. **Downstream Integration**: System feeds into LayoutParser → Tesseract/Marker/Docling
2. **Interoperability**: Common format across object detection frameworks
3. **Validation**: Easy to validate (positive width/height)
4. **Compatibility**: Must work with YOLOv8, Detectron2, LayoutParser

### Downstream Tools

**LayoutParser**:
- Accepts: COCO format `[x, y, width, height]`
- Used for: Document layout analysis, reading order detection
- Integration: Critical for Phase 3

**YOLOv8**:
- Outputs: COCO format (can convert to others)
- Industry standard: MS COCO dataset

**Detectron2** (potential future use):
- Native: COCO format
- Widely used: Facebook AI research framework

## Decision

**Standardize on COCO format `[x, y, width, height]` for all bounding boxes.**

### Implementation

**Schema Definition**:

```python
class DocumentElement(BaseModel):
    """Detected document element with COCO-aligned bounding box."""
    category: ElementCategory
    bbox: list[float]  # COCO format: [x, y, width, height]
    confidence: float

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: list[float]) -> list[float]:
        """Validate COCO bounding box format."""
        if len(v) != 4:
            raise ValueError("Bounding box must have exactly 4 values")

        x, y, width, height = v

        if x < 0 or y < 0:
            raise ValueError("Coordinates must be non-negative")

        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive")

        return v
```

**Documentation Standard**:

```python
# Example bounding box (COCO format)
bbox = [100.0, 150.0, 250.0, 180.0]
# x=100, y=150, width=250, height=180

# NOT corner format!
# bbox = [100.0, 150.0, 350.0, 330.0]  # WRONG
```

### Conversion Utilities

For interoperability with corner-format systems:

```python
def coco_to_corner(bbox: list[float]) -> list[float]:
    """Convert COCO [x, y, w, h] to corner [x1, y1, x2, y2]."""
    x, y, w, h = bbox
    return [x, y, x + w, y + h]

def corner_to_coco(bbox: list[float]) -> list[float]:
    """Convert corner [x1, y1, x2, y2] to COCO [x, y, w, h]."""
    x1, y1, x2, y2 = bbox
    return [x1, y1, x2 - x1, y2 - y1]
```

## Consequences

### Positive

1. **LayoutParser Compatibility**: Direct integration without conversion
   - LayoutParser expects COCO format
   - Zero-copy integration in Phase 3

2. **Industry Standard**: Aligns with MS COCO dataset
   - Most object detection models output COCO format
   - YOLOv8, Detectron2, Mask R-CNN all use COCO

3. **Easy Validation**: Positive width/height constraints
   - Negative values invalid (unlike corner format)
   - Clear semantic meaning (position + size)

4. **JSON Schema Clarity**: Self-documenting format
   ```json
   {
     "bbox": [100, 150, 250, 180],
     "description": "x=100, y=150, width=250, height=180"
   }
   ```

5. **Pydantic Validation**: Strong typing and validation
   - Rejects malformed bounding boxes at API boundary
   - Prevents downstream errors

### Negative

1. **Conversion Overhead**: Some libraries use corner format
   - OpenCV: Uses corner format for rectangles
   - Mitigation: Conversion functions provided, ~1μs overhead
   - Acceptable: One-time conversion vs. throughout pipeline

2. **Developer Confusion**: Must remember format
   - Common mistake: Using corner format instead
   - Mitigation: Clear documentation, validation errors, property-based tests
   - Examples in schema.py docstrings

### Neutral

1. **Format Choice**: COCO vs corner both have pros/cons
2. **Conversion Needed**: Some upstream/downstream tools may differ

## Alternatives Considered

### Alternative 1: Corner Format `[x1, y1, x2, y2]`
**Rejected**:
- Incompatible with LayoutParser (requires conversion)
- Harder to validate (x2 > x1 and y2 > y1)
- Less intuitive for size-based operations
- Not COCO standard

### Alternative 2: Center Format `[cx, cy, width, height]`
**Rejected**:
- Not compatible with LayoutParser
- Requires conversion to COCO for YOLOv8 output
- Less common in document analysis

### Alternative 3: Support Multiple Formats
**Rejected**:
- Adds complexity (format detection/conversion)
- Inconsistent across codebase
- Error-prone (which format is this?)
- Violates "one way to do it" principle

### Alternative 4: Normalized Coordinates [0-1]
**Rejected**:
- Loses pixel precision
- Requires denormalization for cropping
- Less intuitive for debugging

## Validation

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@composite
def bounding_boxes(draw):
    """Generate valid COCO-format bounding boxes."""
    x = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False))
    y = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False))
    width = draw(st.floats(min_value=1.0, max_value=500.0, allow_nan=False))
    height = draw(st.floats(min_value=1.0, max_value=500.0, allow_nan=False))
    return [x, y, width, height]

@given(bounding_boxes())
def test_bbox_format_invariant(bbox: list[float]):
    """Property: COCO bounding boxes must be [x, y, width, height]."""
    assert len(bbox) == 4
    x, y, width, height = bbox
    assert x >= 0
    assert y >= 0
    assert width > 0
    assert height > 0
```

### Schema Validation

```python
# Valid COCO bounding box
element = DocumentElement(
    category=ElementCategory.TABLE,
    bbox=[100.0, 150.0, 250.0, 180.0],
    confidence=0.92,
)

# Invalid: negative coordinates (raises ValidationError)
element = DocumentElement(
    category=ElementCategory.TABLE,
    bbox=[-10.0, 150.0, 250.0, 180.0],  # ❌
    confidence=0.92,
)

# Invalid: zero width (raises ValidationError)
element = DocumentElement(
    category=ElementCategory.TABLE,
    bbox=[100.0, 150.0, 0.0, 180.0],  # ❌
    confidence=0.92,
)
```

## Integration Examples

### LayoutParser Integration

```python
import layoutparser as lp

# Direct compatibility - no conversion needed!
elements = detect_layout(page_image)

for element in elements:
    # element.bbox is already in COCO format
    lp_bbox = lp.Rectangle(
        x_1=element.bbox[0],
        y_1=element.bbox[1],
        x_2=element.bbox[0] + element.bbox[2],  # x + width
        y_2=element.bbox[1] + element.bbox[3],  # y + height
    )
    # Process with LayoutParser...
```

### YOLOv8 Output Mapping

```python
# YOLOv8 outputs COCO format natively
results = yolo_model(page_image)

for detection in results[0].boxes:
    bbox_coco = detection.xyxy.tolist()  # Get bbox in corner format
    bbox_coco = corner_to_coco(bbox_coco)  # Convert to COCO

    element = DocumentElement(
        category=map_yolo_class(detection.cls),
        bbox=bbox_coco,  # Direct assignment
        confidence=float(detection.conf),
    )
```

## Documentation

**Schema Documentation**:
- `schema.py`: Inline comments for COCO format
- `api/schema.md`: MkDocs API reference with examples
- `guides/layout.md`: Layout detection guide with bbox examples

**Code Comments**:
```python
# COCO format: [x, y, width, height]
# x, y: Top-left corner coordinates
# width, height: Box dimensions (must be positive)
bbox: list[float]
```

## References

- [MS COCO Dataset](https://cocodataset.org/#format-data) - Original COCO format specification
- [LayoutParser Documentation](https://layout-parser.github.io/) - LayoutParser bbox expectations
- [YOLOv8 Documentation](https://docs.ultralytics.com/) - YOLO output formats
- [schema.py](../../src/image_preprocessing_detector/schema.py#L50-L75) - DocumentElement implementation
- [test_property_based.py](../../tests/unit/test_property_based.py#L35-L50) - Property-based bbox tests
- [ADR-003: Property-Based Testing](0003-adopt-property-based-testing.md) - Related testing decision
