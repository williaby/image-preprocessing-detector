"""
JSON output generation and metadata export.

Phase 1: Pydantic-based JSON schema output
Phase 2-3: Additional output formats (COCO, LayoutParser)
"""

from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
    load_json,
)

__all__ = [
    "MetadataBuilder",
    "generate_json",
    "load_json",
]
