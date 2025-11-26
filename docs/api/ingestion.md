---
schema_type: common
title: "Ingestion API"
description: "PDF and image loading with standardization to 300 DPI"
tags: [api_reference, documentation, pdf_processing, image_processing]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document the ingestion module for loading PDFs and images."
---

The ingestion module handles loading and standardizing documents from multiple formats (PDF, PNG, JPEG, TIFF) to a consistent 300 DPI format for processing.

## Overview

The ingestion pipeline consists of two main components:

- **PDF Loader**: Extracts pages from PDFs using PyMuPDF
- **Image Loader**: Loads and normalizes images using Pillow and OpenCV

All outputs are standardized to 300 DPI for consistent downstream processing.

## PDF Loading

::: image_preprocessing_detector.ingestion.pdf_loader
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      heading_level: 2

## Image Loading

::: image_preprocessing_detector.ingestion.image_loader
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      heading_level: 2

## Usage Examples

### Load PDF

```python
from image_preprocessing_detector.ingestion import load_pdf_pages

# Load all pages
pages = load_pdf_pages("document.pdf", target_dpi=300)

for page_num, image in enumerate(pages, start=1):
    print(f"Page {page_num}: {image.shape}")
    # image is a numpy array (H, W, 3) in RGB format
```

### Load Image

```python
from image_preprocessing_detector.ingestion import load_and_normalize_image

# Load and standardize image
image = load_and_normalize_image("scan.jpg", target_dpi=300)
print(f"Image shape: {image.shape}")  # (H, W, 3) RGB
```

### Batch Processing

```python
from pathlib import Path
from image_preprocessing_detector.ingestion import (
    load_pdf_pages,
    load_and_normalize_image,
)

def process_directory(input_dir: Path):
    """Process all documents in directory."""
    for file_path in input_dir.iterdir():
        if file_path.suffix.lower() == ".pdf":
            pages = load_pdf_pages(str(file_path))
            print(f"Loaded {len(pages)} pages from {file_path.name}")
        elif file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff"}:
            image = load_and_normalize_image(str(file_path))
            print(f"Loaded image {file_path.name}: {image.shape}")
```

## DPI Standardization

All ingestion functions standardize to 300 DPI for consistency:

- **PDF Pages**: Rendered at 300 DPI using PyMuPDF
- **Images**: Scaled proportionally based on metadata DPI
- **Fallback**: If DPI metadata missing, assumes 72 DPI and scales accordingly

**Why 300 DPI?**

- Industry standard for document scanning
- Sufficient resolution for OCR and layout detection
- Balances quality and computational cost

## Supported Formats

| Format | Extensions | Notes |
|--------|-----------|-------|
| **PDF** | `.pdf` | Multi-page support via PyMuPDF |
| **PNG** | `.png` | Lossless, preserves quality |
| **JPEG** | `.jpg`, `.jpeg` | Lossy compression |
| **TIFF** | `.tiff`, `.tif` | Multi-page support |

## Error Handling

```python
from pathlib import Path
from image_preprocessing_detector.ingestion import load_pdf_pages
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

try:
    pages = load_pdf_pages("document.pdf")
except FileNotFoundError:
    logger.error("PDF file not found")
except Exception as e:
    logger.error("Failed to load PDF", error=str(e))
```

## Performance Considerations

- **Memory**: Each 300 DPI page consumes ~25MB (A4 size)
- **Speed**: PDF rendering ~0.5-1s per page
- **Optimization**: Process pages sequentially to manage memory

## See Also

- [Schema API](schema.md) - Data models
- [Detection API](detection.md) - Quality assessment
- [User Guide: Image Quality](../guides/iqa.md) - IQA overview
