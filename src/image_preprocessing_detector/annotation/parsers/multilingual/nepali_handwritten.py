# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Nepali Handwritten dataset.

Nepali Handwritten contains handwritten Nepali text images
in Devanagari script with PASCAL VOC XML bounding box annotations.

Dataset Structure:
    nepali_handwritten/
        train/
            *.jpg          # Handwritten text images
            *.xml          # PASCAL VOC annotations
        test/
            *.jpg
            *.xml

Annotation Format:
    PASCAL VOC XML with <object> elements containing <bndbox> coordinates.
    Bounding boxes are converted from PASCAL VOC format [xmin, ymin, xmax, ymax]
    to COCO format [x, y, width, height].

Extracts:
    - language_code: Fixed "ne" (Nepali)
    - script_name: Fixed "Devanagari"
    - iso15924_script_code: Fixed "Deva"
    - raw_labels: split, pascal_voc_objects (with COCO-format bboxes)

Example:
    >>> parser = NepaliHandwrittenParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/nepali_handwritten"),
    ...     image_path=Path("/data/nepali_handwritten/train/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    ne
    >>> print(labels.raw_labels.get("num_objects"))
    5
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "nepali-handwritten"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "nepali_handwritten_metadata.json"
__l4_integrate__ = "scripts/integrate_nepali_handwritten_enrichments.py"


import logging
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET  # noqa: N817  # nosemgrep: python.lang.security.audit.insecure-xml-use

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class NepaliHandwrittenParser(BaseParser):
    """Parser for Nepali Handwritten dataset.

    Extracts split information from directory structure.
    Fixed Nepali language/Devanagari script.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["nepali_handwritten"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Nepali Handwritten labels from PASCAL VOC XML and directory structure.

        Extracts bounding boxes from PASCAL VOC XML files and converts them
        to COCO format [x, y, width, height] for Layer 2 compatibility.

        Args:
            dataset_path: Root path of the nepali_handwritten dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with:
                - language_code="ne" (Nepali)
                - script_name="Devanagari"
                - iso15924_script_code="Deva"
                - raw_labels containing split, pascal_voc_objects, num_objects

        Note:
            PASCAL VOC format uses [xmin, ymin, xmax, ymax] coordinates.
            These are converted to COCO format [x, y, width, height] in raw_labels.
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Fixed: Devanagari script (ISO 15924: Deva, ISO 639: ne)
        labels.language_code = "ne"
        labels.script_name = "Devanagari"
        labels.iso15924_script_code = "Deva"

        # Extract split from parent directory
        parent = image_path.parent.name
        if parent in ("train", "test", "val"):
            labels.raw_labels["split"] = parent

        # Parse PASCAL VOC XML for bounding boxes
        xml_path = image_path.with_suffix(".xml")
        if xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()

                # Extract image dimensions if available
                size_elem = root.find("size")
                if size_elem is not None:
                    width_elem = size_elem.find("width")
                    height_elem = size_elem.find("height")
                    if width_elem is not None and height_elem is not None:
                        labels.raw_labels["image_width"] = int(width_elem.text or "0")
                        labels.raw_labels["image_height"] = int(height_elem.text or "0")

                # Extract all objects with bounding boxes
                objects = []
                for obj in root.findall("object"):
                    # Get object name/category (default to "text")
                    name_elem = obj.find("name")
                    name = name_elem.text if name_elem is not None else "text"

                    # Parse bounding box coordinates
                    bbox_elem = obj.find("bndbox")
                    if bbox_elem is not None:
                        try:
                            xmin_elem = bbox_elem.find("xmin")
                            ymin_elem = bbox_elem.find("ymin")
                            xmax_elem = bbox_elem.find("xmax")
                            ymax_elem = bbox_elem.find("ymax")
                            if (
                                xmin_elem is None
                                or ymin_elem is None
                                or xmax_elem is None
                                or ymax_elem is None
                            ):
                                continue
                            xmin = int(float(xmin_elem.text or "0"))
                            ymin = int(float(ymin_elem.text or "0"))
                            xmax = int(float(xmax_elem.text or "0"))
                            ymax = int(float(ymax_elem.text or "0"))

                            # Convert PASCAL VOC [xmin, ymin, xmax, ymax]
                            # to COCO format [x, y, width, height]
                            x = xmin
                            y = ymin
                            width = xmax - xmin
                            height = ymax - ymin

                            # Validate bounding box dimensions
                            if width > 0 and height > 0:
                                obj_dict: dict[str, Any] = {
                                    "bbox": [x, y, width, height],
                                    "category": name,
                                    "bbox_format": "coco",  # Converted to COCO
                                    "original_format": "pascal_voc",
                                }

                                # Extract optional "difficult" flag
                                difficult_elem = obj.find("difficult")
                                if difficult_elem is not None:
                                    obj_dict["difficult"] = difficult_elem.text == "1"

                                objects.append(obj_dict)
                            else:
                                logger.warning(
                                    "Invalid bbox dimensions for %s: width=%d, height=%d",
                                    image_path.name,
                                    width,
                                    height,
                                )
                        except (ValueError, AttributeError) as e:
                            logger.warning(
                                "Failed to parse bbox for object in %s: %s",
                                image_path.name,
                                e,
                            )
                            continue

                # Store extracted objects
                if objects:
                    labels.raw_labels["pascal_voc_objects"] = objects
                    labels.raw_labels["num_objects"] = len(objects)
                else:
                    # No valid objects found
                    labels.raw_labels["num_objects"] = 0

            except ET.ParseError as exc:
                logger.exception("XML parse error for %s", xml_path)
                labels.raw_labels["xml_parse_error"] = str(exc)
            except FileNotFoundError:
                logger.debug("XML file not found (may be expected): %s", xml_path)
        else:
            # XML file doesn't exist - not an error for this dataset
            logger.debug("No XML annotation found for %s", image_path.name)
            labels.raw_labels["num_objects"] = 0

        return labels


__all__ = ["NepaliHandwrittenParser"]
