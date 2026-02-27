"""Parser module for the annotation system.

This module provides the parser architecture for extracting labels from
various dataset formats. Each dataset has a dedicated parser that implements
the DatasetParser protocol.

Package Structure:
    parsers/
    ├── __init__.py          # This file - exports and registry
    ├── base.py              # DatasetParser protocol definition
    ├── registry.py          # ParserRegistry with explicit registration
    ├── template.py          # Parser template generator for new datasets
    ├── quality/             # Quality score parsers (DIQA, SmartDoc, etc.)
    ├── layout/              # Layout annotation parsers (DocLayNet, FUNSD, etc.)
    ├── handwriting/         # Handwriting/signature parsers
    ├── multilingual/        # Multilingual/script parsers
    └── document/            # Document type parsers

Example:
    >>> from image_preprocessing_detector.annotation.parsers import (
    ...     ParserRegistry,
    ...     DatasetParser,
    ... )
    >>>
    >>> # Create registry with default parsers
    >>> registry = ParserRegistry.create_default()
    >>>
    >>> # Get parser for specific dataset
    >>> parser = registry.get_parser("diqa-5000")
    >>> if parser:
    ...     labels = parser.parse(dataset_path, image_path, config)

Template Generation:
    >>> from image_preprocessing_detector.annotation.parsers import (
    ...     generate_parser,
    ...     DatasetInfo,
    ...     ParserCategory,
    ... )
    >>>
    >>> # Generate parser for new dataset
    >>> info = DatasetInfo(
    ...     dataset_name="my-dataset",
    ...     category=ParserCategory.QUALITY,
    ... )
    >>> output_path = generate_parser(info)
"""

from __future__ import annotations

from .base import DatasetParser, ParseResult
from .registry import ParserRegistry
from .template import (
    DatasetInfo,
    ParserCategory,
    generate_config_entry,
    generate_parser,
    generate_test_stub,
    validate_dataset_info,
)

__all__ = [
    "DatasetInfo",
    "DatasetParser",
    "ParseResult",
    "ParserCategory",
    "ParserRegistry",
    "generate_config_entry",
    "generate_parser",
    "generate_test_stub",
    "validate_dataset_info",
]
