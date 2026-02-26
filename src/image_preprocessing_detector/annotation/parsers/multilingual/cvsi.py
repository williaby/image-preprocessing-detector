# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for CVSI dataset.

CVSI (Character-level Video Script Identification) contains
video frames with script identification labels for 10 different
scripts, organized by split and script class.

Dataset Structure:
    cvsi/
        Training/
            {Script}/
                *.jpg
        Testing/
            {Script}/
                *.jpg
        Validation/
            {Script}/
                *.jpg

10 Scripts:
    Arabic, Bengali, English, Gujrathi, Hindi, Kannada,
    Oriya, Punjabi, Tamil, Telegu

Extracts:
    - language_code: ISO 639 code based on script
    - script_name: Script class from directory
    - raw_labels: split, script_class, iso15924_script

Example:
    >>> parser = CvsiParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/cvsi"),
    ...     image_path=Path("/data/cvsi/Training/Hindi/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    hi
    >>> print(labels.script_name)
    Deva
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "cvsi"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "cvsi_metadata.json"
__l4_integrate__ = "scripts/integrate_cvsi_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class CvsiParser(BaseParser):
    """Parser for CVSI dataset.

    Extracts script class and split from directory structure.
    Maps script names to ISO 639 language codes and ISO 15924 script codes.
    """

    # Script to ISO mappings (language_code, iso15924_script)
    SCRIPT_MAPPING = {
        "Arabic": ("ar", "Arab"),
        "Bengali": ("bn", "Beng"),
        "English": ("en", "Latn"),
        "Gujrathi": ("gu", "Gujr"),
        "Hindi": ("hi", "Deva"),
        "Kannada": ("kn", "Knda"),
        "Oriya": ("or", "Orya"),
        "Punjabi": ("pa", "Guru"),
        "Tamil": ("ta", "Taml"),
        "Telegu": ("te", "Telu"),
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["cvsi"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse CVSI labels from directory structure.

        Args:
            dataset_path: Root path of the CVSI dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name (ISO 15924),
            and split information
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Extract script and split from path
        path_parts = image_path.parts
        for i, part in enumerate(path_parts):
            if part in ("Training", "Testing", "Validation"):
                labels.raw_labels["split"] = part.lower()
                if i + 1 < len(path_parts):
                    script_class = path_parts[i + 1]
                    labels.raw_labels["script_class"] = script_class
                    if script_class in self.SCRIPT_MAPPING:
                        lang_code, script_code = self.SCRIPT_MAPPING[script_class]
                        labels.language_code = lang_code
                        labels.script_name = script_class  # Human-readable name
                        labels.iso15924_script_code = script_code  # ISO 15924
                break

        return labels


__all__ = ["CvsiParser"]
