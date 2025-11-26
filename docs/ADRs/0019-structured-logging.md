---
schema_type: common
title: "ADR-019: Structured Logging with structlog + rich"
description: "Use structlog for structured logging with rich console output"
tags: [adr, logging, structlog, rich, observability]
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to use structlog + rich for structured logging with
  human-readable console output."
---


**Status**: Accepted
**Date**: 2025-01-08
**Deciders**: Byron Williams
**Related**:

- [utils/logging.py](../../src/image_preprocessing_detector/utils/logging.py)
- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md)

## Context

The system needs logging for:

- Development: Human-readable console output
- Production: Machine-readable JSON logs
- Performance: Timing and profiling
- Debugging: Structured context

## Decision

**Use structlog for structured logging with rich for console rendering.**

### Architecture

**Development Mode** (console):

```python
setup_logging(level="DEBUG", json_format=False)
logger.info("Processing page", page_num=1, width=2480, height=3509)
# Output: [2025-11-05 10:23:45] INFO Processing page page_num=1 width=2480 height=3509
```

**Production Mode** (JSON):

```python
setup_logging(level="INFO", json_format=True)
logger.info("Processing page", page_num=1, width=2480)
# Output: {"timestamp": "2025-11-05T10:23:45", "level": "info", "event": "Processing page", "page_num": 1, "width": 2480}
```

### Key Features

**Structured Context**:

```python
logger = get_logger(__name__)
logger.info("Detected skew", angle=5.2, confidence=0.85, severity="high")
```

**Performance Logging**:

```python
with log_performance("PDF rendering"):
    pages = pdf_loader.load("document.pdf")
# Output: PDF rendering took 1.23s
```

**Exception Logging**:

```python
try:
    result = detector.detect(image)
except Exception as e:
    logger.exception("Detection failed", detector="blur", image_shape=image.shape)
```

## Consequences

### Positive

1. **Structured Data**: Machine-readable logs for analysis
2. **Human-Readable**: Rich console output for development
3. **Context Preservation**: Automatic context tracking
4. **Performance Monitoring**: Built-in timing utilities
5. **JSON for Production**: Easy integration with log aggregation (ELK, Datadog)

### Negative

1. **Learning Curve**: Different from standard logging
2. **Dependencies**: Adds structlog + rich dependencies
3. **Overhead**: ~1-5ms per log statement vs ~0.1ms for stdlib logging

### Neutral

1. **Configuration**: Single `setup_logging()` call
2. **Compatibility**: Works with standard logging library

## Alternatives Considered

### Alternative 1: Standard Library logging

**Approach**: Use Python's built-in logging module

**Advantages**:

- No dependencies
- Familiar API
- Widespread adoption

**Disadvantages**:

- String formatting only
- No structured data
- Manual JSON serialization
- Limited console formatting

**Why Rejected**: Missing structured logging and rich console output

### Alternative 2: loguru

**Approach**: Use loguru for simplified logging

**Advantages**:

- Simple API
- Pretty console output
- Exception handling

**Disadvantages**:

- Not structured by default
- Less flexible than structlog
- Smaller ecosystem

**Why Rejected**: structlog better suited for structured logging needs

### Alternative 3: Python-json-logger

**Approach**: Use python-json-logger with stdlib logging

**Advantages**:

- JSON output
- Works with stdlib

**Disadvantages**:

- No console formatting
- Manual context management
- No rich integration

**Why Rejected**: Missing human-readable console output

## Implementation

### Configuration (utils/logging.py)

```python
def setup_logging(
    level: str = "INFO",
    json_format: bool = False
) -> None:
    """Configure structured logging."""

    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_format:
        # Production: JSON output
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Rich console output
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)
```

### Usage Patterns

**Basic Logging**:

```python
logger = get_logger(__name__)
logger.info("Starting processing", file_path=pdf_path)
logger.debug("Loaded page", page_num=1, dpi=300, size=(2480, 3509))
logger.warning("Low confidence", detector="skew", confidence=0.35)
logger.error("Failed to load", file_path=pdf_path, error=str(e))
```

**Performance Monitoring**:

```python
@contextmanager
def log_performance(operation: str):
    """Context manager for performance logging."""
    logger = get_logger(__name__)
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        logger.info(f"{operation} took {elapsed:.2f}s")

# Usage
with log_performance("Skew detection"):
    result = skew_detector.detect(image)
```

**Bind Context**:

```python
logger = get_logger(__name__).bind(document_id="doc_001", page_num=1)
logger.info("Processing started")  # Includes document_id and page_num
logger.info("Detected issue", issue_type="blur")  # Also includes document_id and page_num
```

### Console Output Examples

**Development Mode** (Rich):

```text
[2025-11-05 10:23:45] INFO  Processing document file_path=/path/to/doc.pdf
[2025-11-05 10:23:46] DEBUG Loaded page page_num=1 dpi=300 size=(2480, 3509)
[2025-11-05 10:23:47] WARN  Low confidence detector=skew confidence=0.35
[2025-11-05 10:23:48] INFO  Detected issues count=3 types=['blur', 'contrast', 'skew']
```text

**Production Mode** (JSON):

```json
{"timestamp": "2025-11-05T10:23:45", "level": "info", "event": "Processing document", "file_path": "/path/to/doc.pdf"}
{"timestamp": "2025-11-05T10:23:46", "level": "debug", "event": "Loaded page", "page_num": 1, "dpi": 300, "size": [2480, 3509]}
{"timestamp": "2025-11-05T10:23:47", "level": "warning", "event": "Low confidence", "detector": "skew", "confidence": 0.35}
{"timestamp": "2025-11-05T10:23:48", "level": "info", "event": "Detected issues", "count": 3, "types": ["blur", "contrast", "skew"]}
```

## Performance Impact

**Logging Overhead**:

- Console (rich): ~2-5ms per statement
- JSON: ~1-2ms per statement
- Stdlib logging: ~0.1ms per statement

**Total Impact**: ~10-50ms per document (negligible vs ~800ms processing)

## References

- [structlog Documentation](https://www.structlog.org/)
- [rich Documentation](https://rich.readthedocs.io/)
- [utils/logging.py Implementation](../../src/image_preprocessing_detector/utils/logging.py)

## Lessons Learned

1. **Structured Logging Essential**: Machine-readable logs critical for production
2. **Console Readability Matters**: Rich output improves development experience
3. **Performance Acceptable**: ~5ms overhead negligible for document processing
