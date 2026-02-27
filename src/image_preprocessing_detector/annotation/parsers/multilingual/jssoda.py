"""Parser for JSSODa (Japanese Scene Text Organization Dataset) dataset.

JSSODa contains Japanese document images with vertical and horizontal text
orientations. The dataset is useful for text orientation detection and
multi-column layout understanding.

Dataset Structure:
    jssoda/
        manifest.json           # Complete metadata for all images
        vertical/               # Vertical text images (991 images)
            jssoda_vertical_00000.png
            ...
        horizontal/             # Horizontal text images (1009 images)
            jssoda_horizontal_00000.png
            ...

Manifest Structure:
    {
        "vertical": [
            {
                "filename": "jssoda_vertical_00000.png",
                "path": "jssoda/vertical/jssoda_vertical_00000.png",
                "is_vertical": true,
                "num_columns": 3,
                "source": "llm-jp/JSSODa",
                "split": "train",
                "index": 2
            },
            ...
        ],
        "horizontal": [
            {
                "filename": "jssoda_horizontal_00000.png",
                "path": "jssoda/horizontal/jssoda_horizontal_00000.png",
                "is_vertical": false,
                "num_columns": 1,
                "source": "llm-jp/JSSODa",
                "split": "train",
                "index": 0
            },
            ...
        ]
    }

Labels:
    - language_code: ja (Japanese)
    - script_name: Japanese
    - iso15924_script_code: Jpan (Japanese)
    - raw_labels: is_vertical, num_columns, text_orientation, split, source

Example:
    >>> parser = JssodaParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/multilingual_scripts/jssoda"),
    ...     image_path=Path(
    ...         "/data/multilingual_scripts/jssoda/vertical/jssoda_vertical_00001.png"
    ...     ),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ja'
    >>> print(labels.raw_labels["is_vertical"])
    True
    >>> print(labels.raw_labels["text_orientation"])
    'vertical'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "jssoda"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "jssoda_metadata.json"
__l4_integrate__ = "scripts/integrate_jssoda_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class JssodaParser(BaseParser):
    """Parser for JSSODa (Japanese Scene Text Organization Dataset).

    Extracts text orientation and column count metadata from manifest.json.
    The dataset is specifically for Japanese document images with both
    vertical and horizontal text layouts.
    """

    def __init__(self) -> None:
        """Initialize parser with manifest cache."""
        super().__init__()
        self._manifest_cache: dict[Path, dict[str, dict[str, Any]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["jssoda", "js-soda", "jssoda-japanese"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse JSSODa labels from manifest.json.

        Args:
            dataset_path: Root path of the JSSODa dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script codes, and text
            orientation metadata (is_vertical, num_columns, text_orientation)
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Always Japanese
        labels.language_code = "ja"
        labels.script_name = "Japanese"
        labels.iso15924_script_code = "Jpan"

        # Load manifest data
        manifest_data = self._load_manifest(dataset_path)

        # Look up image in manifest
        image_name = image_path.name
        if image_name in manifest_data:
            record = manifest_data[image_name]
            is_vertical = record.get("is_vertical", False)

            labels.raw_labels["is_vertical"] = is_vertical
            labels.raw_labels["text_orientation"] = (
                "vertical" if is_vertical else "horizontal"
            )
            labels.raw_labels["num_columns"] = record.get("num_columns", 1)
            labels.raw_labels["split"] = record.get("split", "train")
            labels.raw_labels["source"] = record.get("source", "llm-jp/JSSODa")
            labels.raw_labels["original_index"] = record.get("index")
        else:
            # Fallback: infer from directory name
            parent_name = image_path.parent.name
            if parent_name == "vertical":
                labels.raw_labels["is_vertical"] = True
                labels.raw_labels["text_orientation"] = "vertical"
            elif parent_name == "horizontal":
                labels.raw_labels["is_vertical"] = False
                labels.raw_labels["text_orientation"] = "horizontal"
            labels.raw_labels["inferred_from_directory"] = True
            logger.debug(
                f"No manifest record found for {image_name}, inferred from directory"
            )

        return labels

    def _load_manifest(self, dataset_path: Path) -> dict[str, dict[str, Any]]:
        """Load and cache manifest data, indexed by filename.

        Args:
            dataset_path: Root path of the JSSODa dataset

        Returns:
            Dictionary mapping image filename to record data
        """
        if dataset_path in self._manifest_cache:
            return self._manifest_cache[dataset_path]

        manifest_data: dict[str, dict[str, Any]] = {}
        manifest_path = dataset_path / "manifest.json"

        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    raw_manifest = json.load(f)

                # Index by filename for fast lookup
                for orientation in ["vertical", "horizontal"]:
                    for record in raw_manifest.get(orientation, []):
                        filename = record.get("filename", "")
                        if filename:
                            manifest_data[filename] = record

                logger.debug(
                    f"Loaded {len(manifest_data)} records from {manifest_path}"
                )
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load manifest at {manifest_path}: {e}")

        self._manifest_cache[dataset_path] = manifest_data
        return manifest_data

    def supports_batch(self) -> bool:
        """Batch parsing is optimized - manifest is loaded once."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images efficiently.

        Loads manifest once and extracts labels for all images.

        Args:
            dataset_path: Root path of the dataset
            image_paths: List of absolute paths to image files
            config: Dataset configuration dictionary

        Returns:
            List of OriginalLabels in same order as image_paths
        """
        # Pre-load manifest
        self._load_manifest(dataset_path)

        # Parse each image (manifest is now cached)
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["JssodaParser"]
