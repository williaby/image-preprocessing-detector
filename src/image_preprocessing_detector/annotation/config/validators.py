"""Dataset configuration validators with clear error messages.

This module provides comprehensive validation for dataset configurations,
ensuring all required fields are present and valid before processing begins.

Features:
    - Structural validation (required fields, types)
    - Path existence validation
    - Cross-field consistency checks
    - Clear, actionable error messages
    - Batch validation with summary reporting

Example:
    >>> from image_preprocessing_detector.annotation.config.validators import (
    ...     validate_dataset_config,
    ...     validate_all_configs,
    ...     ValidationResult,
    ... )
    >>>
    >>> # Validate single config
    >>> result = validate_dataset_config(config)
    >>> if not result.is_valid:
    ...     for error in result.errors:
    ...         print(f"  - {error}")
    >>>
    >>> # Validate all configs
    >>> report = validate_all_configs(DATASET_CONFIGS)
    >>> print(report.summary())
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .datasets import DatasetConfig
    from .settings import AnnotationSettings


class ValidationSeverity(Enum):
    """Severity level for validation messages.

    Attributes:
        ERROR: Validation failure - config cannot be used
        WARNING: Potential issue - config may work but needs review
        INFO: Informational message - not a problem
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    """Single validation message with context.

    Attributes:
        severity: ERROR, WARNING, or INFO
        field: Field name that has the issue (or None for general issues)
        message: Human-readable description of the issue
        suggestion: Optional suggestion for fixing the issue
    """

    severity: ValidationSeverity
    field: str | None
    message: str
    suggestion: str | None = None

    def __str__(self) -> str:
        """Format message for display."""
        prefix = f"[{self.severity.value.upper()}]"
        field_str = f" ({self.field})" if self.field else ""
        suggestion_str = f" -> {self.suggestion}" if self.suggestion else ""
        return f"{prefix}{field_str} {self.message}{suggestion_str}"


@dataclass
class ValidationResult:
    """Result of validating a dataset configuration.

    Attributes:
        dataset_name: Name of the validated dataset
        is_valid: True if no errors (warnings OK)
        messages: List of all validation messages
    """

    dataset_name: str
    messages: list[ValidationMessage] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return not any(m.severity == ValidationSeverity.ERROR for m in self.messages)

    @property
    def errors(self) -> list[ValidationMessage]:
        """Get only error-level messages."""
        return [m for m in self.messages if m.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationMessage]:
        """Get only warning-level messages."""
        return [m for m in self.messages if m.severity == ValidationSeverity.WARNING]

    def add_error(
        self,
        message: str,
        field: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Add an error message."""
        self.messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field=field,
                message=message,
                suggestion=suggestion,
            )
        )

    def add_warning(
        self,
        message: str,
        field: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Add a warning message."""
        self.messages.append(
            ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field=field,
                message=message,
                suggestion=suggestion,
            )
        )

    def add_info(
        self,
        message: str,
        field: str | None = None,
    ) -> None:
        """Add an info message."""
        self.messages.append(
            ValidationMessage(
                severity=ValidationSeverity.INFO,
                field=field,
                message=message,
            )
        )

    def format(self) -> str:
        """Format result for display."""
        status = "VALID" if self.is_valid else "INVALID"
        lines = [f"Dataset: {self.dataset_name} [{status}]"]

        lines.extend(f"  {msg}" for msg in self.messages)

        return "\n".join(lines)


@dataclass
class BatchValidationReport:
    """Report from validating multiple dataset configs.

    Attributes:
        results: Mapping of dataset name to validation result
    """

    results: dict[str, ValidationResult] = field(default_factory=dict)

    @property
    def valid_count(self) -> int:
        """Count of valid configurations."""
        return sum(1 for r in self.results.values() if r.is_valid)

    @property
    def invalid_count(self) -> int:
        """Count of invalid configurations."""
        return sum(1 for r in self.results.values() if not r.is_valid)

    @property
    def total_errors(self) -> int:
        """Total error count across all configs."""
        return sum(len(r.errors) for r in self.results.values())

    @property
    def total_warnings(self) -> int:
        """Total warning count across all configs."""
        return sum(len(r.warnings) for r in self.results.values())

    def summary(self) -> str:
        """Generate summary report."""
        lines = [
            "=" * 60,
            "Dataset Configuration Validation Report",
            "=" * 60,
            f"Total Datasets: {len(self.results)}",
            f"  Valid:   {self.valid_count}",
            f"  Invalid: {self.invalid_count}",
            f"Total Errors:   {self.total_errors}",
            f"Total Warnings: {self.total_warnings}",
            "",
        ]

        # List invalid configs first
        invalid = [r for r in self.results.values() if not r.is_valid]
        if invalid:
            lines.append("INVALID CONFIGURATIONS:")
            lines.append("-" * 40)
            for result in invalid:
                lines.append(result.format())
                lines.append("")

        # Then configs with warnings
        with_warnings = [r for r in self.results.values() if r.is_valid and r.warnings]
        if with_warnings:
            lines.append("CONFIGURATIONS WITH WARNINGS:")
            lines.append("-" * 40)
            for result in with_warnings:
                lines.append(result.format())
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


def validate_dataset_config(
    config: DatasetConfig,
    settings: AnnotationSettings | None = None,
    check_paths: bool = False,
) -> ValidationResult:
    """Validate a single dataset configuration.

    Performs comprehensive validation including:
    - Required field presence
    - Field type correctness
    - Value range/format validation
    - Cross-field consistency
    - Path existence (if settings provided and check_paths=True)

    Args:
        config: DatasetConfig to validate
        settings: Optional AnnotationSettings for path validation
        check_paths: If True and settings provided, verify paths exist

    Returns:
        ValidationResult with all messages

    Example:
        >>> result = validate_dataset_config(config)
        >>> if not result.is_valid:
        ...     print("Validation failed:")
        ...     for error in result.errors:
        ...         print(f"  {error}")
    """
    result = ValidationResult(dataset_name=config.name)

    # === Required Field Validation ===
    _validate_required_fields(config, result)

    # === Name Format Validation ===
    _validate_name_format(config, result)

    # === Pattern Validation ===
    _validate_pattern(config, result)

    # === Content Flag Consistency ===
    _validate_content_flags(config, result)

    # === Multilingual Field Validation ===
    _validate_multilingual_fields(config, result)

    # === Parser Reference Validation ===
    _validate_parser_reference(config, result)

    # === Path Existence (if requested) ===
    if check_paths and settings:
        _validate_paths(config, settings, result)

    return result


def _validate_required_fields(config: DatasetConfig, result: ValidationResult) -> None:
    """Validate all required fields are present and non-empty."""
    # name
    if not config.name:
        result.add_error(
            "Dataset name is required",
            field="name",
            suggestion="Set a unique identifier for the dataset",
        )

    # path_suffix
    if not config.path_suffix:
        result.add_error(
            "Path suffix is required",
            field="path_suffix",
            suggestion="Set path relative to e_drive_root (e.g., 'base_data/tables/tablebank')",
        )

    # pattern
    if not config.pattern:
        result.add_error(
            "Glob pattern is required",
            field="pattern",
            suggestion="Set a pattern like '**/*.jpg' or 'images/**/*.png'",
        )


def _validate_name_format(config: DatasetConfig, result: ValidationResult) -> None:
    """Validate dataset name follows conventions."""
    if not config.name:
        return

    # Should be lowercase with hyphens or underscores
    if config.name != config.name.lower():
        result.add_warning(
            f"Dataset name '{config.name}' contains uppercase characters",
            field="name",
            suggestion="Use lowercase names (e.g., 'diqa-5000' not 'DIQA-5000')",
        )

    # Should not contain spaces
    if " " in config.name:
        result.add_error(
            f"Dataset name '{config.name}' contains spaces",
            field="name",
            suggestion="Use hyphens instead of spaces (e.g., 'my-dataset' not 'my dataset')",
        )

    # Should match a safe pattern
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", config.name):
        result.add_warning(
            f"Dataset name '{config.name}' uses non-standard characters",
            field="name",
            suggestion="Use only lowercase letters, numbers, hyphens, and underscores",
        )


def _validate_pattern(config: DatasetConfig, result: ValidationResult) -> None:
    """Validate glob pattern is well-formed."""
    if not config.pattern:
        return

    # Should have a file extension
    if "." not in config.pattern:
        result.add_warning(
            f"Pattern '{config.pattern}' has no file extension",
            field="pattern",
            suggestion="Include extension like '**/*.jpg' for better filtering",
        )

    # Common image extensions
    valid_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
    pattern_lower = config.pattern.lower()
    has_valid_ext = any(ext in pattern_lower for ext in valid_extensions)

    if not has_valid_ext and "*" in config.pattern:
        result.add_info(
            f"Pattern '{config.pattern}' may match non-image files",
            field="pattern",
        )


def _validate_content_flags(config: DatasetConfig, result: ValidationResult) -> None:
    """Validate content flags are consistent with domain."""
    # Table dataset should have has_table=True
    if config.domain.value == "FORMS" and config.has_table is False:
        result.add_warning(
            "FORMS domain dataset has has_table=False",
            field="has_table",
            suggestion="FORMS datasets typically contain tables; verify this is correct",
        )

    # Handwriting parser should have handwriting flag
    if (
        config.parser_name
        and "handwriting" in config.parser_name.lower()
        and config.has_handwriting is None
    ):
        result.add_warning(
            "Handwriting parser without has_handwriting flag",
            field="has_handwriting",
            suggestion="Set has_handwriting=True for handwriting datasets",
        )

    # Signature parser should have signature flag
    if (
        config.parser_name
        and "signat" in config.parser_name.lower()
        and config.has_signature is None
    ):
        result.add_warning(
            "Signature parser without has_signature flag",
            field="has_signature",
            suggestion="Set has_signature=True for signature datasets",
        )


def _validate_multilingual_fields(
    config: DatasetConfig, result: ValidationResult
) -> None:
    """Validate multilingual/script fields."""
    # ISO 639 language code format (2-3 letters)
    if config.iso639_language and not re.match(r"^[a-z]{2,3}$", config.iso639_language):
        result.add_error(
            f"Invalid ISO 639 language code: '{config.iso639_language}'",
            field="iso639_language",
            suggestion="Use 2-3 letter lowercase code (e.g., 'en', 'ara')",
        )

    # ISO 15924 script code format (4 letters, Title case)
    if config.iso15924_script and not re.match(
        r"^[A-Z][a-z]{3}$", config.iso15924_script
    ):
        result.add_error(
            f"Invalid ISO 15924 script code: '{config.iso15924_script}'",
            field="iso15924_script",
            suggestion="Use 4 letter Title case code (e.g., 'Arab', 'Latn')",
        )

    # If language set, script should usually be set too
    if config.iso639_language and not config.iso15924_script:
        result.add_info(
            "Language code set without script code",
            field="iso15924_script",
        )

    # Valid text_scope values
    valid_scopes = {"word", "line", "phrase", "paragraph", "page", "mixed"}
    if config.text_scope and config.text_scope not in valid_scopes:
        result.add_error(
            f"Invalid text_scope: '{config.text_scope}'",
            field="text_scope",
            suggestion=f"Use one of: {', '.join(sorted(valid_scopes))}",
        )


def _validate_parser_reference(config: DatasetConfig, result: ValidationResult) -> None:
    """Validate parser_name reference."""
    if not config.parser_name:
        result.add_warning(
            "No parser_name specified",
            field="parser_name",
            suggestion="Set parser_name to enable label extraction",
        )
        return

    # Parser name should be lowercase with underscores
    if config.parser_name != config.parser_name.lower():
        result.add_warning(
            f"Parser name '{config.parser_name}' should be lowercase",
            field="parser_name",
        )


def _validate_paths(
    config: DatasetConfig,
    settings: AnnotationSettings,
    result: ValidationResult,
) -> None:
    """Validate that dataset paths exist on filesystem."""
    from .datasets import get_dataset_path

    full_path = get_dataset_path(config, settings)

    if not full_path.exists():
        result.add_warning(
            f"Dataset path does not exist: {full_path}",
            field="path_suffix",
            suggestion="Verify path_suffix is correct and dataset is downloaded",
        )
    elif not full_path.is_dir():
        result.add_error(
            f"Dataset path is not a directory: {full_path}",
            field="path_suffix",
        )
    else:
        # Check if pattern matches any files
        matches = list(full_path.glob(config.pattern))
        if not matches:
            result.add_warning(
                f"Pattern '{config.pattern}' matches no files in {full_path}",
                field="pattern",
                suggestion="Verify the glob pattern matches your image files",
            )
        else:
            result.add_info(f"Found {len(matches)} files matching pattern")


def validate_all_configs(
    configs: dict[str, DatasetConfig],
    settings: AnnotationSettings | None = None,
    check_paths: bool = False,
) -> BatchValidationReport:
    """Validate all dataset configurations.

    Args:
        configs: Dictionary mapping dataset names to configs
        settings: Optional settings for path validation
        check_paths: Whether to verify paths exist

    Returns:
        BatchValidationReport with all results

    Example:
        >>> report = validate_all_configs(DATASET_CONFIGS)
        >>> print(report.summary())
    """
    report = BatchValidationReport()

    for name, config in configs.items():
        # Verify name matches key
        if config.name != name:
            result = ValidationResult(dataset_name=name)
            result.add_error(
                f"Config name '{config.name}' doesn't match dict key '{name}'",
                field="name",
                suggestion="Ensure config.name matches the DATASET_CONFIGS key",
            )
            report.results[name] = result
        else:
            result = validate_dataset_config(config, settings, check_paths)
            report.results[name] = result

    return report


def quick_validate(config: DatasetConfig | dict[str, Any]) -> bool:
    """Quick validation check for essential fields only.

    Args:
        config: DatasetConfig or dict with config fields

    Returns:
        True if essential fields are present and valid

    Example:
        >>> if quick_validate(config):
        ...     # Safe to proceed
        ...     process_dataset(config)
    """
    if isinstance(config, dict):
        return bool(
            config.get("name") and config.get("path_suffix") and config.get("pattern")
        )

    return bool(config.name and config.path_suffix and config.pattern)


__all__ = [
    "BatchValidationReport",
    "ValidationMessage",
    "ValidationResult",
    "ValidationSeverity",
    "quick_validate",
    "validate_all_configs",
    "validate_dataset_config",
]
