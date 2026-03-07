"""Metadata-only parser for OpenPecha OCR Drutsa Tibetan dataset.

OpenPecha OCR Drutsa contains 32,364 line-level OCR images with
Tibetan Unicode text transcriptions, sourced from woodblock prints
and manuscripts.

Note:
    This is a **metadata-only parser** (script/language detection).
    Although Tibetan text transcriptions are available in the source
    parquet files, transcription extraction is not performed here and
    is deferred to a future phase.

Dataset Structure:
    openpecha-ocr-drutsa/
        extracted_images/
            {id}.png
        data/
            train-00000-of-00002.parquet
            train-00001-of-00002.parquet

Images are extracted from parquet to PNG. Labels (Tibetan text)
are available in the parquet files.

Extracts:
    - script_name: Fixed "Tibetan"
    - language_code: Fixed "bo" (Tibetan)
    - iso15924_script_code: Fixed "Tibt"
    - raw_labels: source_id

Example:
    >>> parser = OpenpechaOcrDrutsaParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/openpecha-ocr-drutsa"),
    ...     image_path=Path(
    ...         "/data/openpecha-ocr-drutsa/extracted_images/KS_11-061_line_9874_4.png"
    ...     ),
    ...     config={},
    ... )
    >>> print(labels.script_name)
    Tibetan
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "openpecha-ocr-drutsa"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "openpecha-ocr-drutsa_metadata.json"
__l4_integrate__ = "scripts/integrate_openpecha_ocr_drutsa_enrichments.py"


from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser


class OpenpechaOcrDrutsaParser(BaseParser):
    """Parser for OpenPecha OCR Drutsa Tibetan line-level OCR dataset.

    Fixed Tibetan script/language. Source ID extracted from filename.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["openpecha-ocr-drutsa"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse OCR Drutsa labels from filename.

        Sets fixed Tibetan script/language metadata and extracts source_id
        from the image filename stem. Transcription text is available in
        the source parquet files but is not loaded here; use a dedicated
        transcription extraction script to populate ``labels.transcription``.

        Args:
            dataset_path: Root path of the OCR Drutsa dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with script_name="Tibetan", language_code="bo"
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Fixed: Tibetan script (ISO 15924: Tibt, ISO 639: bo)
        labels.script_name = "Tibetan"
        labels.language_code = "bo"
        labels.iso15924_script_code = "Tibt"

        # Source ID from filename (e.g., KS_11-061_line_9874_4.png)
        labels.raw_labels["source_id"] = image_path.stem

        return labels


__all__ = ["OpenpechaOcrDrutsaParser"]
