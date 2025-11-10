---
schema_type: common
title: "API Reference"
description: "Complete API reference for Image Preprocessing Detector CLI and Python interfaces"
tags: [api_reference, documentation, guide]
status: published
owner: "docs-team"
review_cycle_days: 90
authors:
  - name: "Byron Williams"
purpose: "Provide comprehensive API documentation for CLI commands, Python API, and JSON schema."
---

This document provides reference documentation for the Image Preprocessing Detector's external interface.

## Command Line Interface

### imgprep process

Process a document and detect preprocessing requirements.

**Usage**:

```bash
poetry run imgprep process INPUT [OPTIONS]
```

**Arguments**:

- `INPUT`: Path to input PDF or image file

**Options**:

- `--output PATH`, `-o PATH`: Output JSON file path (required)
- `--dry-run`: Detection only, skip corrections (flag)
- `--blur-threshold FLOAT`: Blur detection threshold 0.0-1.0 (default: 0.8)
- `--skew-threshold FLOAT`: Skew detection threshold 0.0-1.0 (default: 0.7)
- `--contrast-threshold FLOAT`: Contrast detection threshold 0.0-1.0 (default: 0.7)
- `--help`: Show help message

**Examples**:

```bash
# Process single file and save to JSON
poetry run imgprep process input.pdf --output result.json

# Process with custom thresholds
poetry run imgprep process input.pdf --output result.json --blur-threshold 0.90 --skew-threshold 0.95

# Detection only (skip corrections)
poetry run imgprep process input.pdf --output result.json --dry-run
```

**Output Format**:

The command outputs JSON conforming to the DocumentMetadata schema. See [JSON Schema](#json-schema) section below.

### imgprep batch

Batch process multiple documents.

**Usage**:

```bash
poetry run imgprep batch INPUT_DIR OUTPUT_DIR [OPTIONS]
```

**Arguments**:

- `INPUT_DIR`: Directory containing input PDF or image files
- `OUTPUT_DIR`: Directory where results will be saved

**Options**:

- `--dry-run`: Detection only, skip corrections (flag)
- `--blur-threshold FLOAT`: Blur detection threshold 0.0-1.0 (default: 0.8)
- `--skew-threshold FLOAT`: Skew detection threshold 0.0-1.0 (default: 0.7)
- `--contrast-threshold FLOAT`: Contrast detection threshold 0.0-1.0 (default: 0.7)
- `--help`: Show help message

**Examples**:

```bash
# Process all PDFs and images in a directory
poetry run imgprep batch input_dir/ output_dir/

# Batch process with dry-run
poetry run imgprep batch docs/ results/ --dry-run

# Batch process with custom thresholds
poetry run imgprep batch docs/ results/ --blur-threshold 0.9
```

## Python API

### Installation

```bash
# Standard installation
pip install image-preprocessing-detector

# With Poetry
poetry add image-preprocessing-detector

# From source
git clone https://github.com/williaby/image-preprocessing-detector.git
cd image-preprocessing-detector
poetry install
```

### Basic Usage

Currently, the primary interface is the CLI. The Python API provides schema validation:

```python
from image_preprocessing_detector.schema import DocumentMetadata
from image_preprocessing_detector.utils import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO", json_logs=False)
logger = get_logger(__name__)

# Use the CLI to generate output, then validate and load JSON
metadata = DocumentMetadata.from_json_file("output.json")
logger.info("Processed document", pages=metadata.num_pages)
```

**Note**: Direct Python processing API (`process_document` function) is planned for a future release and is not yet available. Use the CLI for document processing.

### Schema Validation

```python
from image_preprocessing_detector.schema import (
    DetectedIssue,
    DocumentElement,
    PageMetadata,
    DocumentMetadata,
)

# Create metadata with validation
metadata = DocumentMetadata(
    source_file="document.pdf",
    num_pages=10,
    processing_version="0.1.0",
)

# Access page metadata
for page in metadata.pages:
    print(f"Page {page.page_number}: {len(page.detected_issues)} issues")

# Serialize to JSON
json_str = metadata.model_dump_json(indent=2)

# Deserialize from JSON
loaded_metadata = DocumentMetadata.model_validate_json(json_str)
```

## JSON Schema

### DocumentMetadata

Root metadata object for a processed document.

**Fields**:

- `document_id` (str, required): Unique identifier for the document
- `file_name` (str, required): Original filename
- `source_mime` (str, required): Source MIME type (e.g., "application/pdf", "image/jpeg")
- `num_pages` (int, required): Total number of pages (must be > 0)
- `processing_version` (ProcessingVersion, required): Processing pipeline version information
- `pages` (List[PageMetadata], required): Metadata for each page

**Example**:

```json
{
  "document_id": "doc_123",
  "file_name": "document.pdf",
  "source_mime": "application/pdf",
  "num_pages": 5,
  "processing_version": {
    "pipeline_version": "0.1.0",
    "iqa_model_hash": null,
    "layout_model_hash": null,
    "thresholds": {
      "blur": 0.8,
      "skew": 0.7,
      "contrast": 0.7
    },
    "timestamp": "2025-11-07T12:00:00Z"
  },
  "pages": [...]
}
```

### PageMetadata

Metadata for a single page.

**Fields**:

- `page_index` (int, required): Zero-based page index (must be >= 0)
- `width_px` (int, required): Page width in pixels (must be > 0)
- `height_px` (int, required): Page height in pixels (must be > 0)
- `dpi_input` (int, required): Input DPI of the page (must be > 0)
- `dpi_effective` (int, required): Effective DPI after processing (must be > 0)
- `detected_issues` (List[DetectedIssue], optional): Page-level quality issues detected
- `planned_actions` (List[PlannedAction], optional): Planned correction actions
- `elements` (List[DocumentElement], optional): Detected document elements (tables, images, etc.)
- `languages` (List[LanguageInfo], optional): Detected languages/scripts
- `transform_history` (List[TransformHistory], optional): History of transformations applied

**Example**:

```json
{
  "page_index": 0,
  "width_px": 2550,
  "height_px": 3300,
  "dpi_input": 300,
  "dpi_effective": 300,
  "detected_issues": [...],
  "planned_actions": [...],
  "elements": [...],
  "languages": [],
  "transform_history": []
}
```

### DetectedIssue

An image quality issue detected in the document.

**Fields**:

- `type` (IssueType, required): Issue type enum value ("noise", "blur", "skew", "perspective", "low_contrast", "orientation", "low_dpi")
- `confidence` (float, required): Detection confidence (0.0-1.0, validated)
- `severity` (IssueSeverity, required): Severity level enum value ("low", "medium", "high", "critical")
- `metrics` (dict, optional): Additional metrics specific to the issue type

**Example**:

```json
{
  "type": "blur",
  "confidence": 0.92,
  "severity": "high",
  "metrics": {
    "laplacian_variance": 45.2,
    "threshold": 100.0
  }
}
```

### DocumentElement

A document element (table, image, handwriting, formula, text block, figure).

**Fields**:

- `id` (str, required): Unique identifier for this element
- `category` (ElementCategory, required): Category enum value ("table", "image", "handwriting", "formula", "text_block", "figure")
- `bbox` (List[int], required): Bounding box in COCO format [x, y, width, height] (exactly 4 non-negative integers)
- `polygon` (List[List[int]], optional): Optional polygon points for irregular shapes
- `confidence` (float, required): Detection confidence (0.0-1.0, validated)
- `attributes` (dict, optional): Additional attributes (script, handwriting_prob, etc.)
- `quality_issues` (List[DetectedIssue], optional): Quality issues specific to this element (for hybrid IQA on embedded images)
- `needs_correction` (bool, optional): Whether this element requires quality correction (default: false)
- `correction_applied` (dict, optional): Details of correction applied to this element

**Example**:

```json
{
  "id": "elem_001",
  "category": "table",
  "bbox": [100, 200, 800, 600],
  "polygon": null,
  "confidence": 0.95,
  "attributes": {
    "num_rows": 10,
    "num_cols": 5
  },
  "quality_issues": [],
  "needs_correction": false,
  "correction_applied": null
}
```

## Logging

### Setup Logging

```python
from image_preprocessing_detector.utils import setup_logging, get_logger

# Setup structured logging
setup_logging(
    level="INFO",          # Log level
    json_logs=False,       # Human-readable output
    log_file=None,        # Optional log file
)

# Get logger instance
logger = get_logger(__name__)

# Use logger
logger.info("Processing document", file="input.pdf", pages=10)
logger.warning("Quality issue detected", issue_type="blur", confidence=0.85)
logger.error("Processing failed", error=str(e))
```

### Log Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: Confirmation that things are working
- `WARNING`: Indication of potential problems
- `ERROR`: Serious problems that need attention
- `CRITICAL`: Critical failures

## Error Handling

The CLI provides clear error messages for common issues:

- **File not found**: Clear message when input file doesn't exist
- **Invalid format**: Warnings for unsupported file formats
- **Processing errors**: Detailed error messages with suggestions

Use the `--dry-run` flag to validate inputs without performing corrections.

For Python API error handling, standard Python exceptions are raised:

```python
from pathlib import Path

try:
    # Validate JSON output from CLI
    metadata = DocumentMetadata.from_json_file("output.json")
except FileNotFoundError:
    logger.error("Output file not found")
except Exception as e:
    logger.error("Failed to load metadata", error=str(e))
```

## Performance Considerations

### Batch Processing

Use the CLI `batch` command to process multiple documents efficiently:

```bash
# Process entire directory
poetry run imgprep batch input_dir/ output_dir/

# The batch command automatically:
# - Finds all supported files (.pdf, .jpg, .jpeg, .png, .tiff)
# - Processes them sequentially
# - Saves results to individual JSON files in output directory
```

### Custom Thresholds

Adjust detection sensitivity using CLI options:

```bash
# More sensitive blur detection (higher threshold = more strict)
poetry run imgprep process input.pdf --output result.json --blur-threshold 0.9

# Less sensitive skew detection (lower threshold = more lenient)
poetry run imgprep process input.pdf --output result.json --skew-threshold 0.6

# Combine multiple thresholds
poetry run imgprep batch docs/ results/ \
  --blur-threshold 0.9 \
  --skew-threshold 0.8 \
  --contrast-threshold 0.75
```

### GPU Acceleration

ML-based detection with GPU acceleration is planned for Phase 2+ and is not yet available.

### Transform History

Track all preprocessing transforms applied:

```python
# Access transform history
for transform in metadata.transform_history:
    print(f"{transform.transform_type}: {transform.parameters}")

# Check if specific transform was applied
has_deskew = any(
    t.transform_type == "deskew"
    for t in metadata.transform_history
)
```

## Type Hints

The schema module includes comprehensive type hints for IDE support:

```python
from pathlib import Path
from image_preprocessing_detector.schema import DocumentMetadata, PageMetadata

# All Pydantic models include full type hints
metadata: DocumentMetadata = DocumentMetadata.from_json_file("output.json")

# Type-safe access to fields
source_file: str = metadata.source_file
num_pages: int = metadata.num_pages
pages: list[PageMetadata] = metadata.pages
```

## Further Documentation

- **Architecture**: See [ARCHITECTURE_SUMMARY.md](../ARCHITECTURE_SUMMARY.md)
- **Project Plan**: See [PROJECT_PLAN.md](../PROJECT_PLAN.md)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Security**: See [SECURITY.md](../SECURITY.md)

For complete schema documentation, see [schema.py](../src/image_preprocessing_detector/schema.py).
