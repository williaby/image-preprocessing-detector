---
schema_type: common
title: "ADR-017: Pydantic v2 for JSON Schema Validation"
description: "Use Pydantic v2 for type-safe JSON schema definition and validation"
tags: [adr, pydantic, schema, validation, json]
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to use Pydantic v2 for JSON schema validation and
  serialization."
---


**Status**: Accepted
**Date**: 2025-01-15
**Deciders**: Byron Williams
**Related**:
- [schema.py](../../src/image_preprocessing_detector/schema.py)
- [PROJECT_PLAN.md](../../PROJECT_PLAN.md)
- [ADR-009: COCO Bounding Box Format](0009-coco-bounding-box-format.md)

## Context

The system needs to generate JSON metadata for document preprocessing results. We required a solution for:
- Type-safe schema definition
- Runtime validation
- JSON serialization/deserialization
- Integration with Python type hints

## Decision

**Use Pydantic v2 for JSON schema definition, validation, and serialization.**

### Key Features Used

**Discriminated Unions**:
```python
class DetectedIssue(BaseModel):
    type: IssueType  # BLUR, SKEW, CONTRAST, etc.
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    severity: IssueSeverity
```

**Field Validation**:
```python
@field_validator("bbox")
@classmethod
def validate_bbox(cls, v: list[float]) -> list[float]:
    if len(v) != 4:
        raise ValueError("Bounding box must have exactly 4 values [x, y, width, height]")
    x, y, width, height = v
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    return v
```

**JSON Serialization**:
```python
metadata = DocumentMetadata(document_id="doc_001", file_name="test.pdf", ...)
json_str = metadata.model_dump_json(indent=2)
loaded = DocumentMetadata.model_validate_json(json_str)
```

## Consequences

### Positive

1. **Type Safety**: Compile-time type checking with MyPy
2. **Runtime Validation**: Automatic validation of inputs
3. **JSON I/O Built-In**: `model_dump_json()` and `model_validate_json()` methods
4. **Schema Generation**: Automatic JSON Schema export for API documentation
5. **Industry Standard**: Widely adopted (FastAPI, LangChain, etc.)
6. **Performance**: Pydantic v2 uses Rust core (5-50× faster than v1)

### Negative

1. **Learning Curve**: Developers need to learn Pydantic patterns
2. **Dependency**: Adds Pydantic 2.0+ as core dependency
3. **Breaking Changes**: Pydantic v1 → v2 migration not trivial

### Neutral

1. **Schema Complexity**: 338 lines for complete schema (reasonable)
2. **Validation Overhead**: ~1-5ms per validation (acceptable)

## Alternatives Considered

### Alternative 1: dataclasses + jsonschema

**Approach**: Use Python dataclasses with separate JSON schema validation

**Advantages**:
- Standard library (dataclasses)
- No external dependencies (except jsonschema for validation)

**Disadvantages**:
- No runtime validation
- Manual JSON serialization
- Separate schema definition
- No type coercion

**Why Rejected**: Missing runtime validation and JSON I/O convenience

### Alternative 2: attrs + cattrs

**Approach**: Use attrs for classes, cattrs for serialization

**Advantages**:
- Lighter weight than Pydantic
- Flexible serialization

**Disadvantages**:
- Less integrated than Pydantic
- Smaller ecosystem
- Manual validation logic

**Why Rejected**: Less convenient than Pydantic's all-in-one approach

### Alternative 3: marshmallow

**Approach**: Use marshmallow for serialization and validation

**Advantages**:
- Mature validation library
- Flexible schemas

**Disadvantages**:
- Separate schema and data classes
- No type hint integration
- Slower than Pydantic v2

**Why Rejected**: Less type-safe, slower, no type hint integration

## Implementation

### Schema Structure (schema.py - 338 lines)

**Core Models**:
```python
class DocumentMetadata(BaseModel):
    document_id: str
    file_name: str
    source_mime: str
    num_pages: int
    processing_version: str
    pages: List[PageMetadata]

class PageMetadata(BaseModel):
    page_index: int
    dimensions: PageDimensions
    detected_issues: List[DetectedIssue]
    planned_actions: List[PlannedAction]
    elements: List[DocumentElement]
    transform_history: List[TransformHistory]

class DocumentElement(BaseModel):
    category: ElementCategory
    bbox: List[float]  # COCO format [x, y, width, height]
    confidence: float
    quality_issues: List[DetectedIssue]  # Per-element IQA
```

### Validation Examples

**Confidence Score Validation**:
```python
class DetectedIssue(BaseModel):
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]

# Validation
issue = DetectedIssue(type=IssueType.BLUR, confidence=1.5)  # ❌ Raises ValidationError
issue = DetectedIssue(type=IssueType.BLUR, confidence=0.85)  # ✅ Valid
```

**COCO Bounding Box Validation**:
```python
@field_validator("bbox")
@classmethod
def validate_bbox(cls, v: list[float]) -> list[float]:
    if len(v) != 4:
        raise ValueError("Bounding box must have exactly 4 values")
    x, y, width, height = v
    if x < 0 or y < 0:
        raise ValueError("Coordinates must be non-negative")
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    return v

# Validation
element = DocumentElement(category=ElementCategory.TEXT, bbox=[10, 20, -50, 30])  # ❌ Negative width
element = DocumentElement(category=ElementCategory.TEXT, bbox=[10, 20, 50, 30])   # ✅ Valid
```

### JSON Serialization/Deserialization

**Export to JSON**:
```python
def generate_json(metadata: DocumentMetadata, output_path: Path) -> None:
    """Generate JSON output file."""
    json_str = metadata.model_dump_json(indent=2, exclude_none=True)
    output_path.write_text(json_str)
```

**Load from JSON**:
```python
def load_json(json_path: Path) -> DocumentMetadata:
    """Load and validate JSON metadata."""
    json_str = json_path.read_text()
    return DocumentMetadata.model_validate_json(json_str)
```

### Schema Export for API Documentation

```python
# Generate JSON Schema for API documentation
schema = DocumentMetadata.model_json_schema()
Path("docs/schema/document_metadata_schema.json").write_text(
    json.dumps(schema, indent=2)
)
```

## Performance Impact

**Validation Overhead**:
- Small objects (DetectedIssue): ~0.1-0.5ms
- Medium objects (PageMetadata): ~1-2ms
- Large objects (DocumentMetadata): ~5-10ms

**JSON Serialization**:
- Small objects: ~0.5-1ms
- Medium objects: ~2-5ms
- Large objects (multi-page): ~10-50ms

**Total Impact**: ~10-50ms per document (negligible vs ~800ms processing time)

## References

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [schema.py Implementation](../../src/image_preprocessing_detector/schema.py)
- [ADR-009: COCO Bounding Box Format](0009-coco-bounding-box-format.md)
- [FastAPI Integration](https://fastapi.tiangolo.com/)

## Lessons Learned

1. **Type Safety + Validation**: Pydantic provides both at once
2. **Performance**: v2 Rust core is fast enough for real-time processing
3. **Ecosystem**: Wide adoption makes integration easy
