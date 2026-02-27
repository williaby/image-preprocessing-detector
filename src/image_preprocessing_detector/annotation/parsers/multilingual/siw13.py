"""Parser for SIW-13 dataset.

SIW-13 (Script Identification in the Wild) contains scene text
images with script identification labels for 13 different scripts.

Dataset Structure:
    siw13/
        Training/
            {Script}/
                *.jpg
        Testing/
            {Script}/
                *.jpg

13 Scripts:
    Arabic, Cambodian, Chinese, English, Greek, Hebrew,
    Japanese, Kannada, Korean, Mongolian, Russian, Thai, Tibetan

Extracts:
    - language_code: ISO 639 code based on script
    - script_name: ISO 15924 script code
    - raw_labels: split, script_class, iso15924_script

Example:
    >>> parser = Siw13Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/siw13"),
    ...     image_path=Path("/data/siw13/Training/Chinese/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    zh
    >>> print(labels.script_name)
    Hans
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "siw13"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "siw13_metadata.json"
__l4_integrate__ = "scripts/integrate_siw13_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class Siw13Parser(BaseParser):
    """Parser for SIW-13 dataset.

    Extracts script class and split from directory structure.
    Maps script names to ISO 639 language codes and ISO 15924 script codes.
    """

    # Script to ISO mappings (language_code, iso15924_script)
    SCRIPT_MAPPING = {
        "Arabic": ("ar", "Arab"),
        "Cambodian": ("km", "Khmr"),
        "Chinese": ("zh", "Hans"),
        "English": ("en", "Latn"),
        "Greek": ("el", "Grek"),
        "Hebrew": ("he", "Hebr"),
        "Japanese": ("ja", "Jpan"),
        "Kannada": ("kn", "Knda"),
        "Korean": ("ko", "Kore"),
        "Mongolian": ("mn", "Mong"),
        "Russian": ("ru", "Cyrl"),
        "Thai": ("th", "Thai"),
        "Tibetan": ("bo", "Tibt"),
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["siw13"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse SIW-13 labels from directory structure.

        Args:
            dataset_path: Root path of the SIW-13 dataset
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
            if part in ("Training", "Testing"):
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


__all__ = ["Siw13Parser"]
