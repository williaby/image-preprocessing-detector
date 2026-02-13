# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Generic parser for datasets without specific label formats.

This parser provides minimal metadata extraction for datasets that lack
structured annotations or custom parsers. It extracts file-level information
and relies on enrichment providers (YOLO, SigLIP) for additional metadata.

Supported Datasets:
    - historical_degraded: Historical degraded documents
    - bhutan_financial: Government financial documents
    - mathverse: Mathematical visual reasoning (formula images)

Note:
    Most datasets have dedicated parsers. This generic parser is only for
    datasets that truly have no structured annotations or dedicated parsers.
    im2latex has been moved to a dedicated parser in the formula/ module.

Example:
    >>> parser = GenericParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/historical_degraded"),
    ...     image_path=Path("/data/historical_degraded/images/doc_001.png"),
    ...     config={"domain": "UNKNOWN"},
    ... )
    >>> labels.raw_labels
    {'source': 'generic', 'dataset': 'historical_degraded', 'domain': 'UNKNOWN'}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..schemas.immutable import OriginalLabels
from .base import BaseParser

logger = logging.getLogger(__name__)

# Datasets handled by this generic parser
# Only includes datasets that truly have no structured annotations
GENERIC_DATASETS = [
    "historical_degraded",
    "bhutan_financial",
    "mathverse",  # Formula images without labels
    # NOTE: im2latex moved to dedicated Im2latexParser in formula/ module
]


class GenericParser(BaseParser):
    """Generic parser for datasets without specific label formats.

    Extracts minimal file-level metadata from the image path and dataset
    configuration. Designed to work with any dataset that lacks structured
    annotations, allowing the enrichment pipeline to add ML-derived labels.

    Features:
        - Extracts dataset name from path or config
        - Records domain and capture method from config
        - Preserves relative path for traceability
        - Supports all image formats

    Attributes:
        _datasets: List of dataset names this parser handles
    """

    def __init__(self, datasets: list[str] | None = None) -> None:
        """Initialize GenericParser.

        Args:
            datasets: Optional custom list of dataset names. Defaults to
                     GENERIC_DATASETS if not provided.
        """
        super().__init__()
        self._datasets = datasets or GENERIC_DATASETS

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return self._datasets

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse minimal metadata for datasets without specific labels.

        Extracts basic information from file path and configuration.
        Additional metadata is expected to be added by enrichment providers.

        Args:
            dataset_path: Root path of the dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary with optional fields:
                - name: Dataset identifier
                - domain: Document domain (e.g., 'ADM', 'FIN', 'EDU')
                - capture_method: How document was captured

        Returns:
            OriginalLabels with raw_labels containing:
                - source: 'generic'
                - dataset: Dataset name
                - domain: Document domain (if available)
                - capture_method: Capture method (if available)
                - relative_path: Image path relative to dataset root
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Mark as generically parsed
        labels.raw_labels["source"] = "generic"

        # Extract dataset name from config or path
        dataset_name = config.get("name")
        if not dataset_name:
            # Try to infer from dataset_path
            dataset_name = dataset_path.name
        labels.raw_labels["dataset"] = dataset_name

        # Extract domain if available in config
        domain = config.get("domain")
        if domain:
            # Handle both enum and string
            if hasattr(domain, "value"):
                labels.raw_labels["domain"] = domain.value
            else:
                labels.raw_labels["domain"] = str(domain)

        # Extract capture method if available
        capture_method = config.get("capture_method")
        if capture_method:
            if hasattr(capture_method, "value"):
                labels.raw_labels["capture_method"] = capture_method.value
            else:
                labels.raw_labels["capture_method"] = str(capture_method)

        # Store relative path for traceability
        try:
            relative_path = image_path.relative_to(dataset_path)
            labels.raw_labels["relative_path"] = str(relative_path)
        except ValueError:
            # image_path not under dataset_path
            labels.raw_labels["relative_path"] = str(image_path.name)

        # Dataset-specific metadata extraction
        self._extract_dataset_specific(labels, dataset_name, image_path, config)

        return labels

    def _extract_dataset_specific(
        self,
        labels: OriginalLabels,
        dataset_name: str,
        _image_path: Path,
        _config: dict[str, Any],
    ) -> None:
        """Extract dataset-specific metadata where possible.

        Args:
            labels: OriginalLabels to update
            dataset_name: Name of the dataset
            _image_path: Path to the image (reserved for future per-image logic)
            _config: Dataset configuration (reserved for future per-dataset logic)
        """
        if labels.raw_labels is None:
            return

        if dataset_name == "historical_degraded":
            # Historical documents with various degradation types
            labels.raw_labels["is_degraded"] = True
            labels.raw_labels["is_historical"] = True

        elif dataset_name == "bhutan_financial":
            # Government financial documents
            labels.raw_labels["document_type"] = "financial"

        elif dataset_name == "mathverse":
            # Mathematical visual reasoning dataset
            labels.raw_labels["content_type"] = "formula"
            labels.raw_labels["is_educational"] = True

        # NOTE: im2latex moved to dedicated Im2latexParser in formula/ module

    def supports_batch(self) -> bool:
        """Generic parser supports batch processing."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images.

        The generic parser's batch implementation is a simple loop since
        there are no shared annotation files to optimize access for.

        Args:
            dataset_path: Root path of the dataset
            image_paths: List of absolute paths to image files
            config: Dataset configuration dictionary

        Returns:
            List of OriginalLabels in same order as image_paths
        """
        return [self.parse(dataset_path, p, config) for p in image_paths]


def register_generic_parser(registry: Any) -> None:
    """Register the generic parser in the parser registry.

    Args:
        registry: ParserRegistry instance to register with
    """
    parser = GenericParser()
    registry.register(parser)
    logger.info(
        "Registered GenericParser for %d datasets: %s",
        len(GENERIC_DATASETS),
        ", ".join(GENERIC_DATASETS),
    )


__all__ = ["GENERIC_DATASETS", "GenericParser", "register_generic_parser"]
