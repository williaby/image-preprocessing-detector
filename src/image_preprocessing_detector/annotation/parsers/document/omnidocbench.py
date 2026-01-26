# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for OmniDocBench dataset.

OmniDocBench is a comprehensive document understanding benchmark stored in
Apache Arrow format, requiring pre-extraction of images.

Dataset Structure:
    omnidocbench/
        train/
            data-*.arrow        # Arrow format files
        extracted_images/       # Extracted images (created by extraction script)
            *.png

Arrow Format:
    Each record contains:
    - image: {path: str, bytes: bytes}
    - Additional metadata fields (vary by document type)

Note: Images must be extracted from Arrow files before processing.
Run extraction script first: scripts/annotate_base_metadata.py --extract-omnidocbench

Example:
    >>> parser = OmnidocbenchParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/omnidocbench"),
    ...     image_path=Path("/data/omnidocbench/extracted_images/doc_001.png"),
    ...     config={},
    ... )
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class OmnidocbenchParser(BaseParser):
    """Parser for OmniDocBench Arrow format benchmark.

    Currently provides minimal parsing as labels are embedded in Arrow format.
    Full parsing would require loading Arrow metadata during extraction phase.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["omnidocbench"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse OmniDocBench labels.

        Args:
            dataset_path: Root path of the OmniDocBench dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with minimal metadata (labels come from Arrow format)

        Note:
            Full label parsing requires Arrow metadata access during extraction.
            This parser primarily serves as a placeholder for future enhancement.
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Store source information
        labels.raw_labels["source"] = "omnidocbench"
        labels.raw_labels["format"] = "arrow_extracted"

        # Extract original filename from path if available
        # Format: extracted_images/{original_name}.png
        if "extracted_images" in str(image_path):
            labels.raw_labels["original_filename"] = image_path.name

        return labels

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate OmniDocBench configuration.

        Args:
            config: Dataset configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check if extraction has been run
        if "path" in config:
            dataset_path = Path(config["path"])
            extracted_dir = dataset_path / "extracted_images"
            if not extracted_dir.exists():
                errors.append(
                    "OmniDocBench requires image extraction. "
                    "Run: scripts/annotate_base_metadata.py --extract-omnidocbench"
                )
            elif not any(extracted_dir.iterdir()):
                errors.append(
                    f"Extracted images directory exists but is empty: {extracted_dir}"
                )

        return errors


__all__ = ["OmnidocbenchParser"]
