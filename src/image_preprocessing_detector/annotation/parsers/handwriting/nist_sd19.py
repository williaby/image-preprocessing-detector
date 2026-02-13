# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for NIST SD-19 handwriting dataset.

NIST Special Database 19 contains handwritten characters and digits from
various sources, organized by writer and character class.

Dataset Structure:
    nist-sd19/
        by_class/
            {class_id}/
                hsf_{writer_id}/
                    {char}_{sample}.png
        by_write/
            hsf_{writer_id}/
                {class}_{sample}.png

Writer Sources:
    - HSF 0-3: High school students
    - HSF 4: IRS workers
    - HSF 6: Census workers
    - HSF 7: IRS workers (second group)

Labels:
    - transcription: Character class (digit 0-9, letter A-Z, etc.)
    - writer_id: HSF writer identifier
    - class_id: Character class identifier
    - sample_id: Sample number

Example:
    >>> parser = NistSd19Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/nist-sd19"),
    ...     image_path=Path("/data/nist-sd19/by_class/30/hsf_0/a_0001.png"),
    ...     config={},
    ... )
    >>> print(labels.transcription)
    'A'
    >>> print(labels.writer_id)
    'hsf_0'
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class NistSd19Parser(BaseParser):
    """Parser for NIST SD-19 handwriting dataset.

    Extracts handwritten character labels from directory structure:
    - Writer ID (HSF identifier)
    - Character class (transcription)
    - Class ID and sample ID
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["nist-sd19", "nist_sd19", "sd19"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse NIST SD-19 labels from directory structure.

        Args:
            dataset_path: Root path of the NIST SD-19 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with writer_id, transcription, and raw_labels
            containing class_id and sample_id
        """
        labels = OriginalLabels()

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Extract information from path and filename
        path_parts = image_path.parts
        filename = image_path.stem

        # Try to extract writer ID from path (hsf_0, hsf_1, etc.)
        for part in path_parts:
            if part.startswith("hsf_") or part.startswith("hsf"):
                labels.writer_id = part
                break

        # Try to extract class from by_class structure or filename
        for i, part in enumerate(path_parts):
            if part == "by_class" and i + 1 < len(path_parts):
                class_id = path_parts[i + 1]
                labels.raw_labels["class_id"] = class_id
                # Map class ID to character (simplified mapping)
                if class_id.isdigit():
                    # Digit class (0-9)
                    labels.transcription = class_id
                break

        # Parse filename patterns
        # Common patterns: "a_0001.png", "digit_5_0001.png", etc.
        parts = filename.split("_")
        if len(parts) >= 2:
            if parts[0].isalpha() and len(parts[0]) == 1:
                # Single character label
                labels.transcription = parts[0].upper()
            elif parts[0].isdigit() and len(parts[0]) == 1:
                labels.transcription = parts[0]
            # Extract sample ID from last part
            if parts[-1].isdigit():
                labels.raw_labels["sample_id"] = parts[-1]

        return labels


__all__ = ["NistSd19Parser"]
