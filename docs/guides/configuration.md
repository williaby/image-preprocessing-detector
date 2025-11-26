---
schema_type: common
title: "Configuration Guide"
description: "Configuration options for CLI and library usage"
tags: [guide, documentation]
status: draft
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Guide users through configuration options and settings."
---

Configuration options for customizing the Image Preprocessing Detector's behavior.

## Command Line Configuration

### Detection Thresholds

Control the sensitivity of quality issue detection:

```bash
# Stricter blur detection (higher threshold = more strict)
poetry run imgprep process input.pdf --output result.json \
  --blur-threshold 0.9

# More lenient skew detection (lower threshold = more lenient)
poetry run imgprep process input.pdf --output result.json \
  --skew-threshold 0.6

# Custom contrast threshold
poetry run imgprep process input.pdf --output result.json \
  --contrast-threshold 0.75
```

### Combined Configuration

```bash
# Process with all custom thresholds
poetry run imgprep process input.pdf --output result.json \
  --blur-threshold 0.9 \
  --skew-threshold 0.8 \
  --contrast-threshold 0.75
```

## Environment Variables

Currently, configuration is primarily through CLI arguments. Environment variable support is planned for Phase 4.

## Logging Configuration

Configure logging output:

```python
from image_preprocessing_detector.utils import setup_logging

# Development: human-readable logs
setup_logging(
    level="DEBUG",
    json_logs=False,
)

# Production: structured JSON logs
setup_logging(
    level="INFO",
    json_logs=True,
    log_file="processing.log",
)
```

## Dry Run Mode

Test detection without applying corrections:

```bash
# Detection only, no corrections
poetry run imgprep process input.pdf --output result.json --dry-run
```

This is useful for:

- Validating detection accuracy
- Estimating processing requirements
- Testing threshold configurations

## Batch Processing Configuration

Process multiple documents efficiently:

```bash
# Basic batch processing
poetry run imgprep batch input_dir/ output_dir/

# With custom thresholds
poetry run imgprep batch input_dir/ output_dir/ \
  --blur-threshold 0.9 \
  --dry-run
```

## Default Values

| Parameter | Default | Range | Notes |
|-----------|---------|-------|-------|
| **blur-threshold** | 0.8 | 0.0-1.0 | Higher = stricter |
| **skew-threshold** | 0.7 | 0.0-1.0 | Minimum confidence |
| **contrast-threshold** | 0.7 | 0.0-1.0 | Normalized score |
| **DPI** | 300 | Fixed | Standard resolution |

## Future Configuration (Phase 4+)

Planned configuration options:

- Configuration file support (YAML/TOML)
- Environment variable support
- GPU acceleration settings
- ML model selection
- Custom correction parameters
- API rate limiting

## See Also

- [Quick Start](quick-start.md) - Getting started
- [API Reference](../api/index.md) - CLI documentation
