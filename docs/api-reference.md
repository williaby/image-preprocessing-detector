# API Reference

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

- `source_file` (str): Path to source document
- `num_pages` (int): Total number of pages
- `processing_version` (str): Version of processing pipeline
- `pages` (List[PageMetadata]): Per-page metadata
- `created_at` (datetime): Processing timestamp
- `transform_history` (List[TransformHistory]): Document-level transforms

**Example**:

```json
{
  "source_file": "document.pdf",
  "num_pages": 5,
  "processing_version": "0.1.0",
  "pages": [...],
  "created_at": "2025-11-07T12:00:00Z",
  "transform_history": []
}
```

### PageMetadata

Metadata for a single page.

**Fields**:

- `page_number` (int): Page number (1-indexed)
- `dpi` (int): Page DPI
- `dimensions` (Tuple[int, int]): Page dimensions (width, height)
- `detected_issues` (List[DetectedIssue]): Quality issues detected
- `elements` (List[DocumentElement]): Document elements (tables, images, etc.)
- `transform_history` (List[TransformHistory]): Page-level transforms

**Example**:

```json
{
  "page_number": 1,
  "dpi": 300,
  "dimensions": [2550, 3300],
  "detected_issues": [...],
  "elements": [...],
  "transform_history": []
}
```

### DetectedIssue

An image quality issue detected in the document.

**Fields**:

- `issue_type` (str): Issue type ("blur", "skew", "low_contrast", "noise", etc.)
- `severity` (str): Severity level ("low", "medium", "high")
- `confidence` (float): Detection confidence (0.0-1.0)
- `location` (Optional[BoundingBox]): Issue location (COCO format: [x, y, width, height])
- `metadata` (dict): Additional issue-specific metadata

**Example**:

```json
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
```

### DocumentElement

A document element (table, image, handwriting, formula).

**Fields**:

- `element_type` (str): Element type ("table", "image", "handwriting", "formula", "text")
- `bbox` (BoundingBox): Bounding box (COCO format: [x, y, width, height])
- `confidence` (float): Detection confidence (0.0-1.0)
- `quality_issues` (List[DetectedIssue]): Per-element quality issues (hybrid IQA)
- `metadata` (dict): Element-specific metadata

**Example**:

```json
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
