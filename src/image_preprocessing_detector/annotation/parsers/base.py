"""Base parser protocol for the annotation system.

This module defines the DatasetParser protocol that all dataset-specific
parsers must implement. Parsers are responsible for extracting original
labels from source datasets.

Design Principles:
    1. Stateless: Parsers should not maintain internal state between calls
    2. Thread-safe: Parsers may be called from multiple threads
    3. Fail-fast: Raise clear exceptions rather than returning partial data
    4. Type-safe: All methods have full type annotations

Example:
    >>> from image_preprocessing_detector.annotation.parsers.base import (
    ...     DatasetParser,
    ...     ParseResult,
    ... )
    >>>
    >>> class MyParser:
    ...     '''Parser for my custom dataset.'''
    ...
    ...     @property
    ...     def dataset_names(self) -> list[str]:
    ...         return ["my-dataset"]
    ...
    ...     def parse(
    ...         self,
    ...         dataset_path: Path,
    ...         image_path: Path,
    ...         config: dict[str, Any],
    ...     ) -> OriginalLabels:
    ...         # Extract labels from dataset files
    ...         return OriginalLabels(...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..schemas.immutable import OriginalLabels


@dataclass
class ParseResult:
    """Result of a parse operation with error tracking.

    Provides structured error reporting for parse operations, allowing
    callers to handle partial failures gracefully.

    Attributes:
        labels (OriginalLabels | None): Parsed OriginalLabels (may be partial on error)
        success (bool): Whether parsing completed successfully
        errors (list[str]): List of error messages encountered
        warnings (list[str]): List of non-fatal warning messages
        source_files (list[str]): List of source files used for parsing
    """

    labels: OriginalLabels | None
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)


@runtime_checkable
class DatasetParser(Protocol):
    """Protocol for dataset-specific label parsers.

    All dataset parsers must implement this protocol. Implementations
    should be stateless and thread-safe.

    The protocol defines:
        - dataset_names: Which datasets this parser handles
        - parse: Extract labels for a single image
        - supports_batch: Whether batch parsing is available
        - parse_batch: Optional batch parsing for performance

    Type Checking:
        Use @runtime_checkable to enable isinstance() checks:
        >>> isinstance(my_parser, DatasetParser)  # Works at runtime
    """

    @property
    def dataset_names(self) -> list[str]:
        """Dataset names this parser handles.

        Returns:
            list[str]: List of dataset name strings that this parser can process.
            Names should match keys in DATASET_CONFIGS.

        Example:
            >>> parser.dataset_names
            ["diqa-5000", "diqa-synthetic"]
        """

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels for a single image.

        This is the primary parsing method. Extract ground truth labels
        from dataset annotation files and return a populated OriginalLabels
        instance.

        Args:
            dataset_path (Path): Root path of the dataset (from DATASET_CONFIGS)
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary from DATASET_CONFIGS

        Returns:
            OriginalLabels: Populated OriginalLabels instance with all available labels

        Example:
            >>> labels = parser.parse(
            ...     dataset_path=Path("/data/diqa-5000"),
            ...     image_path=Path("/data/diqa-5000/train/ori/img001.jpg"),
            ...     config=DATASET_CONFIGS["diqa-5000"],
            ... )
            >>> print(labels.diqa_overall)
            4.2
        """

    def supports_batch(self) -> bool:
        """Whether this parser supports batch operations.

        Batch parsing can significantly improve performance for datasets
        with shared annotation files (e.g., single COCO JSON for all images).

        Returns:
            bool: True if parse_batch() provides optimized batch processing,
            False if it just loops over parse() (default implementation)."""
        return False

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images (optional optimization).

        For datasets with shared annotation files (like COCO JSON), batch
        parsing can load annotations once and extract labels for all images,
        significantly improving performance.

        The default implementation just calls parse() for each image.
        Override this method to provide optimized batch processing.

        Args:
            dataset_path (Path): Root path of the dataset
            image_paths (list[Path]): List of absolute paths to image files
            config (dict[str, Any]): Dataset configuration dictionary

        Returns:
            list[OriginalLabels]: List of OriginalLabels in same order as image_paths
        """
        return [self.parse(dataset_path, p, config) for p in image_paths]

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate dataset configuration (optional).

        Check that the configuration has all required fields and
        valid values for this parser.

        Args:
            config (dict[str, Any]): Dataset configuration to validate

        Returns:
            list[str]: List of validation error messages (empty if valid)"""
        return []


class BaseParser:
    """Base class for parser implementations.

    Provides common functionality for parsers. Subclass this instead
    of implementing DatasetParser protocol directly to get:
        - Default supports_batch() returning False
        - Default parse_batch() that loops over parse()
        - Default validate_config() returning empty list
        - Helper methods for common operations

    Subclasses must implement:
        - dataset_names property
        - parse() method
    """

    @property
    def dataset_names(self) -> list[str]:
        """Dataset names this parser handles. Override in subclass."""
        raise NotImplementedError("Subclasses must implement dataset_names")

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels for a single image. Override in subclass."""
        raise NotImplementedError("Subclasses must implement parse()")

    def supports_batch(self) -> bool:
        """Whether batch parsing is optimized. Override if providing batch support."""
        return False

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images. Override for batch optimization."""
        return [self.parse(dataset_path, p, config) for p in image_paths]

    def validate_config(self, _config: dict[str, Any]) -> list[str]:
        """Validate configuration. Override to add specific checks."""
        return []

    # Helper methods for common operations

    def _get_relative_path(self, dataset_path: Path, image_path: Path) -> str:
        """Get image path relative to dataset root.

        Args:
            dataset_path (Path): Dataset root path
            image_path (Path): Absolute image path

        Returns:
            str: Relative path string"""
        try:
            return str(image_path.relative_to(dataset_path))
        except ValueError:
            # image_path not under dataset_path
            return str(image_path)

    def _find_annotation_file(
        self,
        dataset_path: Path,
        patterns: list[str],
    ) -> Path | None:
        """Find annotation file matching patterns.

        Args:
            dataset_path (Path): Dataset root path
            patterns (list[str]): List of glob patterns to try

        Returns:
            Path | None: First matching file path, or None if not found"""
        for pattern in patterns:
            matches = list(dataset_path.glob(pattern))
            if matches:
                return matches[0]
        return None


class ParseError(Exception):
    """Exception raised when parsing fails.

    Args:
        dataset_name (str): Name of the dataset being parsed
        image_path (str | Path): Path to the image being processed
        cause (Exception | None): Original exception that caused the failure
        message (str | None): Human-readable error message
    """

    def __init__(
        self,
        dataset_name: str,
        image_path: str | Path,
        cause: Exception | None = None,
        message: str | None = None,
    ):
        self.dataset_name = dataset_name
        self.image_path = str(image_path)
        self.cause = cause
        self.message = message or f"Failed to parse {image_path}"

        super().__init__(
            f"[{dataset_name}] {self.message}" + (f": {cause}" if cause else "")
        )


__all__ = [
    "BaseParser",
    "DatasetParser",
    "ParseError",
    "ParseResult",
]
