"""Parser for Multilingual Scripts collection.

Multilingual Scripts is a collection of multiple subdatasets:
- arabic_ocr: Arabic OCR dataset
- dzongkha_digits: Tibetan/Dzongkha digit recognition
- jssoda: Japanese handwriting
- mdiw13: 13 Indic scripts (handled by separate parser)
- nepal_devanagari: Nepali documents (717 images, unlabeled)

Dataset Structure:
    multilingual_scripts/
        combined_manifest.json         - Master manifest
        arabic_ocr/manifest.json       - Arabic OCR dataset
        dzongkha_digits/manifest.json  - Tibetan/Dzongkha digits
        jssoda/manifest.json           - Japanese handwriting
        mdiw13/                        - 13 Indic scripts (separate parser)
        nepal_devanagari/              - Nepali Devanagari (unlabeled)
            nepal_book_*.jpg           - 713 book page scans
            nepal_newspaper_*.jpg      - 4 newspaper page scans

Script/Language Mappings:
    - arabic_ocr: Arab script, ar language
    - dzongkha_digits: Tibt script, dz language
    - jssoda: Jpan script, ja language
    - nepal_devanagari: Deva script, ne language (unlabeled)

Example:
    >>> parser = MultilingualScriptsParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/multilingual_scripts"),
    ...     image_path=Path("/data/multilingual_scripts/arabic_ocr/train/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.script_name)
    Arabic
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "multilingual-scripts"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "multilingual_scripts_metadata.json"


import json
import logging
from pathlib import Path
from typing import Any, ClassVar

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class MultilingualScriptsParser(BaseParser):
    """Parser for Multilingual Scripts collection.

    Extracts script/language metadata from directory structure and
    manifest files. Handles multiple subdatasets with different
    labeling status.
    """

    # Script/language mapping based on subdataset
    SCRIPT_MAPPINGS: ClassVar[dict[str, dict[str, Any]]] = {
        "arabic_ocr": {
            "script": "Arab",
            "language": "ar",
            "script_name": "Arabic",
            "labeled": True,
        },
        "dzongkha_digits": {
            "script": "Tibt",
            "language": "dz",
            "script_name": "Tibetan",
            "labeled": True,
        },
        "jssoda": {
            "script": "Jpan",
            "language": "ja",
            "script_name": "Japanese",
            "labeled": True,
        },
        "nepal_devanagari": {
            "script": "Deva",
            "language": "ne",
            "script_name": "Devanagari",
            "labeled": False,
        },
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["multilingual_scripts"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        _config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Multilingual Scripts labels from directory structure and manifests.

        Args:
            dataset_path: Root path of the multilingual_scripts dataset
            image_path: Absolute path to the image file being processed
            _config: Dataset configuration (unused)
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with script_name, language_code, and raw_labels
            populated based on subdataset
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Determine subdataset from path
        path_parts = image_path.parts
        subdataset = None

        for part in path_parts:
            if part in self.SCRIPT_MAPPINGS:
                subdataset = part
                break
            # Check for mdiw13 (handled by separate parser)
            if part == "mdiw13" or "mdiw" in part.lower():
                subdataset = "mdiw13"
                break

        if subdataset and subdataset in self.SCRIPT_MAPPINGS:
            mapping = self.SCRIPT_MAPPINGS[subdataset]
            labels.script_name = (
                str(mapping["script_name"]) if mapping["script_name"] else None
            )
            labels.language_code = (
                str(mapping["language"]) if mapping["language"] else None
            )
            labels.iso15924_script_code = str(mapping["script"])  # ISO 15924
            labels.raw_labels["subdataset"] = subdataset
            labels.raw_labels["has_ground_truth_labels"] = mapping["labeled"]

            # Special handling for nepal_devanagari: extract document type
            if subdataset == "nepal_devanagari":
                filename = image_path.stem
                if filename.startswith("nepal_book"):
                    labels.raw_labels["document_type"] = "book"
                elif filename.startswith("nepal_newspaper"):
                    labels.raw_labels["document_type"] = "newspaper"
                labels.raw_labels["note"] = "Unlabeled real-world Nepali documents"

        elif subdataset == "mdiw13":
            # MDIW-13 has 13 Indic scripts - handled by separate parser
            labels.script_name = "Indic"  # Generic
            labels.raw_labels["subdataset"] = "mdiw13"
            labels.raw_labels["note"] = "13 Indic scripts - use MDIW13Parser"

        # Try to parse manifest for additional metadata
        manifest_paths = [
            dataset_path / subdataset / "manifest.json" if subdataset else None,
            dataset_path / "combined_manifest.json",
        ]

        for manifest_path in manifest_paths:
            if manifest_path and manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        # Look for this specific image in manifest
                        image_name = image_path.name
                        for sample in manifest.get("samples", []):
                            if sample.get("filename") == image_name:
                                labels.raw_labels["manifest_source"] = sample.get(
                                    "source"
                                )
                                labels.raw_labels["manifest_index"] = sample.get(
                                    "index"
                                )
                                break
                except Exception as e:
                    logger.debug(f"Failed to parse manifest at {manifest_path}: {e}")

        return labels


__all__ = ["MultilingualScriptsParser"]
