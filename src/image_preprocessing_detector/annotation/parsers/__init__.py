# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser module for the annotation system.

This module provides the parser architecture for extracting labels from
various dataset formats. Each dataset has a dedicated parser that implements
the DatasetParser protocol.

Package Structure:
    parsers/
    ├── __init__.py          # This file - exports and registry
    ├── base.py              # DatasetParser protocol definition
    ├── registry.py          # ParserRegistry with explicit registration
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
"""

from __future__ import annotations

from .base import DatasetParser, ParseResult
from .registry import ParserRegistry

__all__ = [
    "DatasetParser",
    "ParseResult",
    "ParserRegistry",
]
