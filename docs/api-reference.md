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

- `--output PATH`: Output JSON file path (default: stdout)
- `--dpi INTEGER`: Override DPI for processing (default: 300)
- `--blur-threshold FLOAT`: Blur detection threshold (default: 0.85)
- `--skew-threshold FLOAT`: Skew detection threshold (default: 0.90)
- `--help`: Show help message

**Examples**:

```bash
# Process single file and save to JSON
poetry run imgprep process input.pdf --output result.json

# Process with custom thresholds
poetry run imgprep process input.pdf --blur-threshold 0.90 --skew-threshold 0.95

# Output to stdout for piping
poetry run imgprep process input.pdf | jq '.pages[0]'
```

**Output Format**:

The command outputs JSON conforming to the DocumentMetadata schema. See [JSON Schema](#json-schema) section below.

### imgprep batch

Batch process multiple documents (Phase 1+).

**Usage**:

```bash
poetry run imgprep batch INPUT_DIR [OPTIONS]
```

**Arguments**:

- `INPUT_DIR`: Directory containing input files

**Options**:

- `--output-dir PATH`: Output directory for JSON files
- `--pattern GLOB`: File pattern to match (default: `*.pdf`)
- `--workers INT`: Number of parallel workers (default: auto)
- `--help`: Show help message

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

```python
from image_preprocessing_detector.schema import DocumentMetadata
from image_preprocessing_detector.utils import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO", json_logs=False)
logger = get_logger(__name__)

# Process document (Phase 1+ implementation)
# from image_preprocessing_detector.pipeline import process_document
# metadata = process_document("document.pdf")
# metadata.to_json_file("output.json")

# Validate and load JSON schema
metadata = DocumentMetadata.from_json_file("output.json")
logger.info("Processed document", pages=metadata.num_pages)
```

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

### Common Exceptions

```python
from pathlib import Path
from image_preprocessing_detector.exceptions import (
    ProcessingError,
    InvalidInputError,
    UnsupportedFormatError,
)

try:
    metadata = process_document("document.pdf")
except FileNotFoundError:
    logger.error("Document not found")
except InvalidInputError as e:
    logger.error("Invalid input", error=str(e))
except UnsupportedFormatError as e:
    logger.error("Unsupported format", error=str(e))
except ProcessingError as e:
    logger.error("Processing failed", error=str(e))
```

## Performance Considerations

### Batch Processing

For processing multiple documents, use batch processing for better performance:

```python
from image_preprocessing_detector.pipeline import batch_process

results = batch_process(
    input_dir="documents/",
    output_dir="results/",
    workers=4,              # Parallel workers
    pattern="*.pdf",        # File pattern
)
```

### GPU Acceleration

ML-based detection (Phase 2+) supports GPU acceleration:

```python
from image_preprocessing_detector.pipeline import process_document

metadata = process_document(
    "document.pdf",
    use_gpu=True,          # Enable GPU acceleration
    batch_size=8,          # GPU batch size
)
```

## Advanced Usage

### Custom Thresholds

```python
from image_preprocessing_detector.config import ProcessingConfig

config = ProcessingConfig(
    blur_threshold=0.90,
    skew_threshold=0.95,
    contrast_threshold=0.85,
    min_confidence=0.80,
)

metadata = process_document("document.pdf", config=config)
```

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

All public APIs include comprehensive type hints for IDE support:

```python
from pathlib import Path
from typing import Optional
from image_preprocessing_detector.schema import DocumentMetadata

def process_document(
    input_path: Path,
    output_path: Optional[Path] = None,
    use_gpu: bool = False,
) -> DocumentMetadata:
    """Process a document and return metadata."""
    ...
```

## Further Documentation

- **Architecture**: See [ARCHITECTURE_SUMMARY.md](../ARCHITECTURE_SUMMARY.md)
- **Project Plan**: See [PROJECT_PLAN.md](../PROJECT_PLAN.md)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Security**: See [SECURITY.md](../SECURITY.md)

For complete schema documentation, see [schema.py](../src/image_preprocessing_detector/schema.py).
