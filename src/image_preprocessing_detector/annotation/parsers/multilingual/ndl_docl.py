"""Parser for NDL-DocL (National Diet Library Document Layout) dataset.

NDL-DocL contains scanned Japanese documents from the National Diet Library
with Pascal VOC XML layout annotations. The dataset spans two subsets:
kotenseki (rare books, pre-1868) and kindai (modern, post-1868).

Dataset Structure:
    ndl-docl/
        full_images/                    # Full page images (PNG)
            kotenseki/
                *.png
            kindai/
                *.png
        tugidigi-annotation/            # Pascal VOC XML annotations
            kotenseki/
                *.xml
            kindai/
                *.xml

Pascal VOC XML Format:
    <annotation>
        <filename>image_name.png</filename>
        <size>
            <width>...</width>
            <height>...</height>
        </size>
        <object>
            <name>label_name</name>
            <bndbox>
                <xmin>...</xmin>
                <ymin>...</ymin>
                <xmax>...</xmax>
                <ymax>...</ymax>
            </bndbox>
        </object>
        ...
    </annotation>

Labels:
    - language_code: ja (Japanese)
    - script_name: Japanese
    - iso15924_script_code: Jpan (Japanese)
    - raw_labels: subset, has_kuzushiji, layout_annotations, document_era

Example:
    >>> parser = NdlDoclParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/ndl-docl/full_images"),
    ...     image_path=Path("/data/ndl-docl/full_images/kotenseki/page001.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ja'
    >>> print(labels.raw_labels["subset"])
    'kotenseki'
    >>> print(labels.raw_labels["has_kuzushiji"])
    True
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "ndl-docl"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "ndl-docl_metadata.json"
__l4_integrate__ = "scripts/integrate_ndl_docl_enrichments.py"


import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Subsets and their era classification
_SUBSET_ERA_MAP: dict[str, str] = {
    "kotenseki": "pre-1868",
    "kindai": "post-1868",
}


class NdlDoclParser(BaseParser):
    """Parser for NDL-DocL (National Diet Library Document Layout) dataset.

    Extracts layout annotations from Pascal VOC XML files and classifies
    documents by era based on the kotenseki/kindai subset.
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["ndl-docl", "ndl_docl", "layout-dataset"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse NDL-DocL labels from Pascal VOC XML annotations.

        Args:
            dataset_path (Path): Root path of the NDL-DocL full_images directory
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with language/script metadata, subset info,
            kuzushiji flag, and layout annotations from XML
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Always Japanese
        labels.language_code = "ja"
        labels.script_name = "Japanese"
        labels.iso15924_script_code = "Jpan"

        # Determine subset from image path
        subset = self._determine_subset(image_path)
        labels.raw_labels["subset"] = subset

        # Kotenseki (rare books) likely contains kuzushiji (classical script)
        labels.raw_labels["has_kuzushiji"] = subset == "kotenseki"

        # Set document era
        labels.raw_labels["document_era"] = _SUBSET_ERA_MAP.get(subset, "unknown")

        # Parse Pascal VOC XML annotations
        dataset_root = dataset_path.parent  # ndl-docl/ root
        annotations = self._parse_xml_annotation(dataset_root, image_path, subset)
        labels.raw_labels["layout_annotations"] = annotations

        return labels

    def _determine_subset(self, image_path: Path) -> str:
        """Determine the subset (kotenseki or kindai) from the image path.

        Args:
            image_path (Path): Absolute path to the image

        Returns:
            str: Subset name string ("kotenseki", "kindai", or "unknown")
        """
        parts = image_path.parts
        for part in parts:
            if part in _SUBSET_ERA_MAP:
                return part
        return "unknown"

    def _parse_xml_annotation(
        self,
        dataset_root: Path,
        image_path: Path,
        subset: str,
    ) -> list[dict[str, Any]]:
        """Parse Pascal VOC XML annotation file for the given image.

        Args:
            dataset_root (Path): Root path of the NDL-DocL dataset (parent of full_images/)
            image_path (Path): Absolute path to the image
            subset (str): Dataset subset ("kotenseki" or "kindai")

        Returns:
            list[dict[str, Any]]: List of annotation dicts with label and bbox keys
        """
        # XML annotations are in tugidigi-annotation/{subset}/
        xml_name = image_path.stem + ".xml"
        xml_path = dataset_root / "tugidigi-annotation" / subset / xml_name

        if not xml_path.exists():
            # Try without subset directory
            xml_path = dataset_root / "tugidigi-annotation" / xml_name
            if not xml_path.exists():
                logger.debug("No XML annotation found for %s", image_path.name)
                return []

        annotations: list[dict[str, Any]] = []
        try:
            tree = ET.parse(xml_path)  # noqa: S314
            root = tree.getroot()

            for obj in root.findall("object"):
                name_elem = obj.find("name")
                bndbox = obj.find("bndbox")

                if name_elem is None or bndbox is None:
                    continue

                label = name_elem.text or ""
                bbox: dict[str, int] = {}
                for coord in ("xmin", "ymin", "xmax", "ymax"):
                    coord_elem = bndbox.find(coord)
                    if coord_elem is not None and coord_elem.text:
                        bbox[coord] = int(coord_elem.text)

                if label and len(bbox) == 4:
                    annotations.append({"label": label, "bbox": bbox})

        except (ET.ParseError, OSError) as exc:
            logger.warning("Failed to parse XML annotation %s: %s", xml_path, exc)

        return annotations

    def supports_batch(self) -> bool:
        """Batch parsing is supported."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images.

        Args:
            dataset_path (Path): Root path of the dataset
            image_paths (list[Path]): List of absolute paths to image files
            config (dict[str, Any]): Dataset configuration dictionary

        Returns:
            list[OriginalLabels]: List of OriginalLabels in same order as image_paths
        """
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["NdlDoclParser"]
