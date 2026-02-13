"""JSON Schema Validation Utilities.

Provides validation for:
- Layer 2 Enrichment Metadata (training pipeline)
- Document Metadata (Project B output)

Usage:
    from image_preprocessing_detector.schema_utils.validation import (
        validate_enrichment,
        validate_document_metadata,
        ValidationResult,
    )

    result = validate_enrichment(enrichment_data)
    if not result.valid:
        print(f"Errors: {result.errors}")
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

try:
    from jsonschema import Draft7Validator, ValidationError
    from jsonschema.exceptions import SchemaError

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    Draft7Validator = None
    ValidationError = Exception
    SchemaError = Exception


# Schema file paths (relative to project root)
SCHEMA_DIR = Path(__file__).parent.parent.parent.parent.parent / "docs" / "schema"
LAYER2_SCHEMA_PATH = SCHEMA_DIR / "layer2_enrichment.schema.json"
OUTPUT_SCHEMA_PATH = SCHEMA_DIR / "document_metadata.schema.json"

# Cached schemas
_schema_cache: dict[str, dict] = {}


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str | None = None


def _load_schema(schema_path: Path) -> dict:
    """Load and cache a JSON schema."""
    cache_key = str(schema_path)

    if cache_key not in _schema_cache:
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        with open(schema_path, encoding="utf-8") as f:
            _schema_cache[cache_key] = json.load(f)

    return _schema_cache[cache_key]


def get_layer2_schema() -> dict:
    """Get the Layer 2 Enrichment schema."""
    return _load_schema(LAYER2_SCHEMA_PATH)


def get_output_schema() -> dict:
    """Get the Document Metadata output schema."""
    return _load_schema(OUTPUT_SCHEMA_PATH)


def validate_enrichment(
    data: dict[str, Any],
    raise_on_error: bool = False,
) -> ValidationResult:
    """Validate Layer 2 enrichment data against schema.

    Args:
        data: Enrichment data dictionary
        raise_on_error: If True, raise ValidationError on first error

    Returns:
        ValidationResult with valid flag, errors, and warnings

    Raises:
        ValidationError: If raise_on_error=True and validation fails
        ImportError: If jsonschema is not installed
    """
    if not JSONSCHEMA_AVAILABLE:
        raise ImportError(
            "jsonschema package required for validation. "
            "Install with: pip install jsonschema"
        )

    schema = get_layer2_schema()
    return _validate_against_schema(data, schema, raise_on_error)


def validate_document_metadata(
    data: dict[str, Any],
    raise_on_error: bool = False,
) -> ValidationResult:
    """Validate document metadata against output schema.

    Args:
        data: Document metadata dictionary
        raise_on_error: If True, raise ValidationError on first error

    Returns:
        ValidationResult with valid flag, errors, and warnings
    """
    if not JSONSCHEMA_AVAILABLE:
        raise ImportError(
            "jsonschema package required for validation. "
            "Install with: pip install jsonschema"
        )

    schema = get_output_schema()
    return _validate_against_schema(data, schema, raise_on_error)


def _validate_against_schema(
    data: dict[str, Any],
    schema: dict,
    raise_on_error: bool = False,
) -> ValidationResult:
    """Internal validation against a schema."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        validator = Draft7Validator(schema)

        for error in sorted(validator.iter_errors(data), key=lambda e: e.path):
            error_path = ".".join(str(p) for p in error.path) or "(root)"
            error_msg = f"{error_path}: {error.message}"

            if raise_on_error:
                raise ValidationError(error_msg)

            errors.append(error_msg)

    except SchemaError as e:
        errors.append(f"Invalid schema: {e.message}")

    # Add warnings for deprecated or optional patterns
    warnings.extend(_check_warnings(data, schema))

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        schema_version=schema.get("$id", "unknown"),
    )


def _check_warnings(data: dict[str, Any], _schema: dict) -> list[str]:
    """Check for non-fatal issues and best practice violations."""
    warnings = []

    # Check for missing optional but recommended fields
    if "data" in data:
        enrichment_data = data["data"]

        if "provenance" not in data:
            warnings.append(
                "Missing 'provenance' field - recommended for reproducibility"
            )

        if "quality" in enrichment_data:
            quality = enrichment_data["quality"]
            if "degradations" not in quality or not quality["degradations"]:
                warnings.append(
                    "No degradations recorded - consider running IQA analysis"
                )

        if "content_flags" in enrichment_data:
            flags = enrichment_data["content_flags"]
            if "tier" not in flags:
                warnings.append("content_flags missing 'tier' - provenance unclear")

    # Check for bbox format consistency
    if "layout_detections" in data.get("data", {}):
        for i, det in enumerate(data["data"]["layout_detections"]):
            if "bbox_source_format" not in det:
                warnings.append(f"layout_detections[{i}] missing 'bbox_source_format'")

    return warnings


def validate_iqa_vector(
    vector: list[float],
    strict: bool = False,
) -> ValidationResult:
    """Validate a 45-dimensional IQA vector.

    Args:
        vector: IQA severity vector
        strict: If True, require values in [0, 1]

    Returns:
        ValidationResult
    """
    errors = []
    warnings = []

    if len(vector) != 45:
        errors.append(f"Expected 45 dimensions, got {len(vector)}")

    for i, val in enumerate(vector):
        if not isinstance(val, (int, float)):
            errors.append(f"Index {i}: expected number, got {type(val).__name__}")
        elif strict and not (0.0 <= val <= 1.0):
            errors.append(f"Index {i}: value {val} outside [0, 1] range")
        elif val < 0:
            warnings.append(f"Index {i}: negative value {val}")
        elif val > 1:
            warnings.append(f"Index {i}: value {val} exceeds 1.0")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_bbox(
    bbox: list[float],
    image_width: int | None = None,
    image_height: int | None = None,
) -> ValidationResult:
    """Validate a COCO-format bounding box.

    Args:
        bbox: [x, y, width, height]
        image_width: Optional image width for bounds check
        image_height: Optional image height for bounds check

    Returns:
        ValidationResult
    """
    errors = []
    warnings = []

    if len(bbox) != 4:
        errors.append(f"Expected 4 values, got {len(bbox)}")
        return ValidationResult(valid=False, errors=errors)

    x, y, w, h = bbox

    # Check non-negative
    if x < 0:
        errors.append(f"x ({x}) must be >= 0")
    if y < 0:
        errors.append(f"y ({y}) must be >= 0")
    if w <= 0:
        errors.append(f"width ({w}) must be > 0")
    if h <= 0:
        errors.append(f"height ({h}) must be > 0")

    # Check bounds if dimensions provided
    if image_width is not None and x + w > image_width:
        warnings.append(f"Bbox exceeds image width: x+w ({x + w}) > {image_width}")

    if image_height is not None and y + h > image_height:
        warnings.append(f"Bbox exceeds image height: y+h ({y + h}) > {image_height}")

    # Check for suspiciously small/large boxes
    area = w * h
    if area < 10:
        warnings.append(f"Very small bbox area: {area} pixels")
    if image_width and image_height:
        image_area = image_width * image_height
        if area > 0.95 * image_area:
            warnings.append("Bbox covers >95% of image - possibly incorrect")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


class SchemaValidator:
    """Reusable validator with cached schema.

    Use this when validating many records against the same schema.
    """

    def __init__(self, schema_type: str = "layer2"):
        """Initialize validator.

        Args:
            schema_type: "layer2" for enrichment, "output" for document metadata
        """
        if not JSONSCHEMA_AVAILABLE:
            raise ImportError("jsonschema package required")

        if schema_type == "layer2":
            self.schema = get_layer2_schema()
        elif schema_type == "output":
            self.schema = get_output_schema()
        else:
            raise ValueError(f"Unknown schema_type: {schema_type}")

        self._validator = Draft7Validator(self.schema)
        self.schema_type = schema_type

    def validate(
        self,
        data: dict[str, Any],
        raise_on_error: bool = False,
    ) -> ValidationResult:
        """Validate data against cached schema."""
        return _validate_against_schema(data, self.schema, raise_on_error)

    def is_valid(self, data: dict[str, Any]) -> bool:
        """Quick check if data is valid."""
        result: bool = self._validator.is_valid(data)
        return result

    def iter_errors(self, data: dict[str, Any]) -> Iterator[ValidationError]:
        """Iterate over validation errors."""
        return cast(Iterator[ValidationError], self._validator.iter_errors(data))
