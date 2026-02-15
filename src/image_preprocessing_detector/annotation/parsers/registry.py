# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser registry for the annotation system.

This module provides the ParserRegistry class for managing dataset parsers.
Uses explicit registration instead of pkgutil auto-discovery to avoid
import-order issues and improve testability.

Design Decision:
    We use explicit registration instead of auto-discovery because:
    1. Predictable import order - no surprises from module load order
    2. Testability - easy to create isolated test registries
    3. Performance - no filesystem scanning on import
    4. Type safety - static analysis can verify registrations

Example:
    >>> from image_preprocessing_detector.annotation.parsers import (
    ...     ParserRegistry,
    ... )
    >>>
    >>> # Create empty registry
    >>> registry = ParserRegistry()
    >>>
    >>> # Register a parser
    >>> from .quality.diqa import DIQAParser
    >>> registry.register(DIQAParser())
    >>>
    >>> # Or create with all defaults
    >>> registry = ParserRegistry.create_default()
    >>> parser = registry.get_parser("diqa-5000")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import DatasetParser

if TYPE_CHECKING:
    pass  # No type-only imports needed yet; guard kept for future additions

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Parser registry with explicit registration.

    Manages a collection of DatasetParser instances, mapping dataset
    names to their corresponding parsers.

    Thread Safety:
        The registry is designed for single-threaded registration
        during initialization, followed by multi-threaded read access.
        Do not register parsers after concurrent read access begins.

    Attributes:
        _parsers: Internal mapping of dataset names to parsers
    """

    def __init__(self) -> None:
        """Initialize an empty parser registry."""
        self._parsers: dict[str, DatasetParser] = {}

    def register(self, parser: DatasetParser) -> None:
        """Register a parser for its dataset names.

        The parser's dataset_names property is read to determine which
        datasets it handles. Each dataset name is registered.

        Args:
            parser: Parser instance implementing DatasetParser protocol

        Raises:
            ValueError: If a parser is already registered for any dataset name
            TypeError: If parser doesn't implement DatasetParser protocol
        """
        if not isinstance(parser, DatasetParser):
            raise TypeError(
                f"Parser must implement DatasetParser protocol, got {type(parser).__name__}"
            )

        for name in parser.dataset_names:
            if name in self._parsers:
                existing = self._parsers[name]
                raise ValueError(
                    f"Parser already registered for dataset '{name}': "
                    f"{type(existing).__name__}"
                )
            self._parsers[name] = parser
            logger.debug("Registered parser for dataset: %s", name)

    def unregister(self, dataset_name: str) -> bool:
        """Unregister a parser for a dataset.

        Useful for testing or dynamic parser replacement.

        Args:
            dataset_name: Dataset name to unregister

        Returns:
            True if a parser was unregistered, False if not found
        """
        if dataset_name in self._parsers:
            del self._parsers[dataset_name]
            return True
        return False

    def get_parser(self, dataset_name: str) -> DatasetParser | None:
        """Get parser for a dataset.

        Args:
            dataset_name: Name of the dataset (as in DATASET_CONFIGS)

        Returns:
            DatasetParser instance, or None if not found
        """
        return self._parsers.get(dataset_name)

    def has_parser(self, dataset_name: str) -> bool:
        """Check if a parser is registered for a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            True if a parser is registered
        """
        return dataset_name in self._parsers

    def list_datasets(self) -> list[str]:
        """List all registered dataset names.

        Returns:
            Sorted list of dataset names
        """
        return sorted(self._parsers.keys())

    def list_parsers(self) -> list[tuple[str, str]]:
        """List all registered parsers with their datasets.

        Returns:
            List of (dataset_name, parser_class_name) tuples
        """
        return [
            (name, type(parser).__name__)
            for name, parser in sorted(self._parsers.items())
        ]

    def __len__(self) -> int:
        """Return number of registered dataset mappings."""
        return len(self._parsers)

    def __contains__(self, dataset_name: str) -> bool:
        """Check if dataset is registered."""
        return dataset_name in self._parsers

    @classmethod
    def create_default(cls) -> ParserRegistry:
        """Create registry with all standard parsers registered.

        This is the recommended way to create a production registry.
        All parsers from the parsers subpackages are registered.

        Returns:
            ParserRegistry with all standard parsers

        Example:
            >>> registry = ParserRegistry.create_default()
            >>> "diqa-5000" in registry
            True
        """
        registry = cls()

        # Import and register parsers by category
        # Each category catches ImportError separately to allow partial loading

        # Quality parsers
        try:
            from .quality import register_quality_parsers

            register_quality_parsers(registry)
        except ImportError as e:
            logger.warning("Failed to load quality parsers: %s", e)

        # Layout parsers
        try:
            from .layout import register_layout_parsers

            register_layout_parsers(registry)
        except ImportError as e:
            logger.warning("Failed to load layout parsers: %s", e)

        # Handwriting parsers
        try:
            from .handwriting import register_handwriting_parsers

            register_handwriting_parsers(registry)
        except ImportError as e:
            logger.warning("Failed to load handwriting parsers: %s", e)

        # Multilingual parsers
        try:
            from .multilingual import register_multilingual_parsers

            register_multilingual_parsers(registry)
        except ImportError as e:
            logger.warning("Failed to load multilingual parsers: %s", e)

        # Document parsers
        try:
            from .document import register_document_parsers

            register_document_parsers(registry)
        except ImportError as e:
            logger.warning("Failed to load document parsers: %s", e)

        # Formula parsers
        try:
            from .formula import register_formula_parsers

            register_formula_parsers(registry)
        except ImportError as e:
            logger.warning("Failed to load formula parsers: %s", e)

        # Correction parsers (shadow removal, dewarping)
        try:
            from .correction import register_correction_parsers

            register_correction_parsers(registry)
        except ImportError as e:
            logger.warning("Failed to load correction parsers: %s", e)

        # Generic parser for datasets without specific label formats
        try:
            from .generic import register_generic_parser

            register_generic_parser(registry)
        except ImportError as e:
            logger.warning("Failed to load generic parser: %s", e)

        logger.info("Created default parser registry with %d datasets", len(registry))

        return registry

    @classmethod
    def create_empty(cls) -> ParserRegistry:
        """Create an empty registry for testing.

        Returns:
            Empty ParserRegistry
        """
        return cls()


__all__ = [
    "ParserRegistry",
]
