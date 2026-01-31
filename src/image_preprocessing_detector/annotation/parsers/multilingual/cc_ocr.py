# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for CC-OCR benchmark dataset.

CC-OCR (Comprehensive OCR Benchmark) is a large-scale OCR benchmark
covering multiple tracks including multi-scene text, multilingual text,
document parsing, and key information extraction.

Dataset Structure:
    CC-OCR/
        {track}/
            {subset}/
                images/
                    *.png
                annotations/
                    *.json

Tracks:
    - Multi-Scene Text: Scene text recognition
    - Multilingual Text: Chinese character OCR
    - Document Parsing: Document structure analysis
    - Key Info Extraction: Form/invoice data extraction

Extracts:
    - language_code: Language from JSON annotations
    - transcription: Ground truth text
    - raw_labels: track, subset, scene_type, full annotation

Example:
    >>> parser = CcOcrParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/cc-ocr"),
    ...     image_path=Path("/data/cc-ocr/multilingual_text/subset1/images/img001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    zh
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class CcOcrParser(BaseParser):
    """Parser for CC-OCR benchmark dataset.

    Extracts track, subset, and language/text annotations from
    directory structure and JSON annotation files.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["cc_ocr"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse CC-OCR labels from directory and JSON annotations.

        Args:
            dataset_path: Root path of the CC-OCR dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, transcription, and track
            information populated
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Default to Chinese for CC-OCR (Simplified Chinese)
        labels.language_code = "zh"
        labels.script_name = "Chinese"  # Human-readable name
        labels.iso15924_script_code = "Hans"  # ISO 15924

        # Parse track and subset from path
        path_parts = image_path.parts

        for part in path_parts:
            # Look for track patterns
            if (
                "scene" in part.lower()
                or "multilingual" in part.lower()
                or "document" in part.lower()
                or "parsing" in part.lower()
                or "extraction" in part.lower()
                or "key" in part.lower()
            ):
                labels.raw_labels["track"] = part

        # Try to load JSON annotations if available
        json_path = image_path.with_suffix(".json")
        if not json_path.exists():
            # Try annotations subdirectory
            json_path = (
                image_path.parent.parent / "annotations" / f"{image_path.stem}.json"
            )

        if json_path.exists():
            try:
                with open(json_path) as f:
                    anno = json.load(f)
                    if "language" in anno:
                        labels.language_code = anno["language"]
                    if "text" in anno:
                        labels.transcription = anno["text"]
                    labels.raw_labels["annotation"] = anno
            except Exception as e:
                logger.debug(f"Failed to parse CC-OCR annotation at {json_path}: {e}")

        return labels


__all__ = ["CcOcrParser"]
