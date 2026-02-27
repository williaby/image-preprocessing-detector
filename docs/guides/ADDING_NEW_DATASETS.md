---
owner: docs-team
purpose: Guide for adding new datasets to the annotation metadata extraction system.
schema_type: common
status: draft
tags:
- guide
- datasets
- documentation
title: Adding New Datasets Guide
---

This guide walks through the process of adding a new dataset to the annotation
metadata extraction system.

## Quick Start (CLI Method)

The fastest way to add a new dataset is using the interactive CLI:

```bash
# Interactive mode - prompts for all values
uv run annotate add-dataset

# With arguments
uv run annotate add-dataset \
    --name "my-dataset" \
    --category quality \
    --domain GENERAL \
    --url "https://example.com/dataset" \
    --license "CC-BY-4.0" \
    --samples "5000"
```

The CLI generates:

1. Parser boilerplate file
2. Config entry code (copy/paste)
3. Test stub code (copy/paste)

## Manual Method

For more control, you can create files manually following this guide.

### Step 1: Understand Your Dataset

Before writing code, gather this information:

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Unique identifier | `diqa-5000`, `funsd` |
| **Category** | Parser type | quality, layout, handwriting, multilingual, document |
| **Domain** | Document domain | FORMS, TAX, MEDICAL, GENERAL, etc. |
| **Capture Method** | How documents were created | SCAN, CAMERA, BORN_DIGITAL, UNKNOWN |
| **Label Format** | Annotation structure | CSV, COCO JSON, per-image JSON, etc. |
| **Sample Count** | Number of images | ~5000, 10K+, etc. |
| **License** | Usage license | Apache-2.0, CC-BY-4.0, etc. |

### Step 2: Create Parser File

Create a new parser in the appropriate category directory:

```
src/image_preprocessing_detector/annotation/parsers/
├── quality/           # Quality assessment (DIQA, SmartDoc)
├── layout/            # Layout/structure (DocLayNet, FUNSD)
├── handwriting/       # Handwriting/signatures
├── multilingual/      # Script/language specific
└── document/          # General document types
```

**Example: `parsers/quality/my_dataset.py`**

```python
"""Parser for My Dataset.

Dataset Information:
    - Source: https://example.com/my-dataset
    - License: CC-BY-4.0
    - Domain: GENERAL
    - Samples: ~5000

Label Format:
    CSV file with columns: filename, quality_score, sharpness
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from ..base import BaseParser
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)


class MyDatasetParser(BaseParser):
    """Parser for My Dataset quality assessment dataset."""

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["my-dataset"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels for a single image."""
        labels = OriginalLabels()

        # Find and parse annotation file
        csv_path = dataset_path / "labels.csv"
        if csv_path.exists():
            try:
                with open(csv_path, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["filename"] == image_path.name:
                            labels.human_mos = float(row["quality_score"])
                            break
            except Exception as e:
                logger.debug(f"Failed to parse labels: {e}")

        return labels


__all__ = ["MyDatasetParser"]
```

### Step 3: Add Dataset Configuration

Add an entry to `config/datasets.py`:

```python
from .datasets import DatasetConfig
from ..schemas.enums import CaptureMethod, DomainLevel1

# Add to DATASET_CONFIGS dictionary
"my-dataset": DatasetConfig(
    name="my-dataset",
    path_suffix="base_data/quality/my-dataset",  # Relative to e_drive_root
    pattern="**/*.jpg",                          # Glob pattern for images
    capture_method=CaptureMethod.UNKNOWN,
    domain=DomainLevel1.GENERAL,
    is_benchmark=False,
    has_human_mos=True,
    parser_name="my_dataset",                    # Module name (without .py)
),
```

### Step 4: Register Parser

Add registration in `parsers/registry.py`:

```python
# In ParserRegistry.create_default() method:
from .quality.my_dataset import MyDatasetParser
registry.register(MyDatasetParser())
```

### Step 5: Write Tests

Create `tests/unit/annotation/test_my_dataset_parser.py`:

```python
"""Tests for MyDatasetParser."""

import pytest
from pathlib import Path

from image_preprocessing_detector.annotation.parsers.quality.my_dataset import (
    MyDatasetParser,
)
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels


class TestMyDatasetParser:
    """Test suite for MyDatasetParser."""

    @pytest.fixture
    def parser(self) -> MyDatasetParser:
        return MyDatasetParser()

    def test_dataset_names(self, parser: MyDatasetParser) -> None:
        assert "my-dataset" in parser.dataset_names

    def test_parse_returns_original_labels(
        self,
        parser: MyDatasetParser,
        tmp_path: Path,
    ) -> None:
        # Create test structure
        image_file = tmp_path / "test.jpg"
        image_file.touch()

        result = parser.parse(tmp_path, image_file, {})
        assert isinstance(result, OriginalLabels)

    def test_parse_extracts_quality_score(
        self,
        parser: MyDatasetParser,
        tmp_path: Path,
    ) -> None:
        # Create test CSV
        csv_path = tmp_path / "labels.csv"
        csv_path.write_text("filename,quality_score,sharpness\ntest.jpg,4.5,0.8\n")

        image_file = tmp_path / "test.jpg"
        image_file.touch()

        result = parser.parse(tmp_path, image_file, {})
        assert result.human_mos == 4.5
```

### Step 6: Validate Configuration

Run validation to check your configuration:

```bash
# Validate all configs
uv run annotate validate

# Validate specific dataset
uv run annotate validate -d my-dataset

# Check with path existence
uv run annotate validate --check-paths
```

### Step 7: Test the Pipeline

Run the full test suite:

```bash
# Run parser tests
uv run pytest tests/unit/annotation/ -v

# Run specific parser test
uv run pytest tests/unit/annotation/test_my_dataset_parser.py -v
```

## Common Label Formats

### CSV Format

```python
def parse(self, dataset_path, image_path, config):
    labels = OriginalLabels()
    csv_path = dataset_path / "annotations.csv"

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["filename"] == image_path.name:
                labels.human_mos = float(row["score"])
                break
    return labels
```

### COCO JSON Format

```python
def parse(self, dataset_path, image_path, config):
    labels = OriginalLabels()
    json_path = dataset_path / "annotations.json"

    with open(json_path) as f:
        coco = json.load(f)

    # Find image ID
    image_id = None
    for img in coco["images"]:
        if img["file_name"] == image_path.name:
            image_id = img["id"]
            break

    if image_id:
        labels.coco_annotations = [
            ann for ann in coco["annotations"]
            if ann["image_id"] == image_id
        ]
    return labels
```

### Per-Image JSON

```python
def parse(self, dataset_path, image_path, config):
    labels = OriginalLabels()
    ann_path = image_path.with_suffix(".json")

    if ann_path.exists():
        with open(ann_path) as f:
            labels.raw_labels = json.load(f)
    return labels
```

## Content Flags (Tier 0)

For datasets with guaranteed content characteristics, set Tier 0 flags:

| Flag | Use When |
|------|----------|
| `has_table=True` | Every image contains tables |
| `has_formula=True` | Every image contains math formulas |
| `has_handwriting=True` | Every image contains handwriting |
| `has_signature=True` | Every image contains signatures |

These flags enable exact tier classification without ML inference.

## Multilingual Datasets

For non-Latin script datasets, add language/script codes:

```python
DatasetConfig(
    name="arabic-docs",
    iso639_language="ar",        # ISO 639 language code
    iso15924_script="Arab",      # ISO 15924 script code
    text_scope="paragraph",      # word/line/phrase/paragraph/page/mixed
    # ... other fields
)
```

## Troubleshooting

### Parser Not Found

1. Check parser is registered in `registry.py`
2. Verify `parser_name` in config matches module name
3. Check import path is correct

### Labels Not Extracted

1. Add debug logging to parser
2. Verify annotation file path
3. Check image filename matching logic

### Validation Errors

```bash
# Get detailed validation output
uv run annotate validate -d my-dataset -v
```

## API Reference

### DatasetInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `dataset_name` | str | Unique identifier |
| `url` | str | Source URL |
| `license` | str | License type |
| `domain` | str | Document domain |
| `category` | ParserCategory | Parser category |
| `sample_count` | str | Approximate count |
| `has_table` | bool \| None | Table presence flag |
| `has_formula` | bool \| None | Formula presence flag |
| `has_handwriting` | bool \| None | Handwriting presence flag |
| `has_signature` | bool \| None | Signature presence flag |
| `iso639_language` | str \| None | Language code |
| `iso15924_script` | str \| None | Script code |

### DatasetConfig Fields

See `config/datasets.py` for complete field documentation.

## Next Steps

After adding a dataset:

1. Run the annotation pipeline on a sample
2. Verify metadata extraction is correct
3. Add to appropriate tier definition if needed
4. Update architecture documentation if significant
