# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Muharaf Arabic Historical Manuscripts dataset.

Muharaf contains Arabic handwriting from Lebanese diaspora (19th-21st century)
with PAGE XML annotations (W3C 2019-07-15 schema) containing polygon
coordinates and expert transcriptions.

Dataset Structure:
    muharaf/
        public/
            *.jpg          - Page images (457 pages)
            *.png          - Line images (24,495 lines)
            *.xml          - PAGE XML annotations (1,216 files)
            *.json         - Alternative JSON format (3,648 files)
            *.txt          - Text transcriptions (24,495 files)

PAGE XML Format:
    - TextRegion elements with polygon Coords
    - TextLine elements with Arabic Unicode transcriptions
    - Reading order metadata (RTL)
    - Language/script attributes (Arabic, handwritten-cursive)
    - Center-line (baseline) coordinates in UserDefined

Labels Extracted:
    - language_code: "ar" (Arabic)
    - script_name: "Arabic"
    - transcription: Arabic text from Unicode elements
    - text_content: Full text content with metadata
    - raw_labels: Polygon coordinates, reading order, metadata

Conversion:
    - PAGE XML polygons → YOLO axis-aligned bboxes
    - Original polygon preserved in raw_labels
    - Normalized to [x_center, y_center, width, height] (0-1 range)

Example:
    >>> parser = MuharafParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/muharaf"),
    ...     image_path=Path("/data/muharaf/public/page_001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ar'
    >>> print(labels.transcription)
    'لبنان في ١٧/١٠/١٩٦٠'  # noqa: RUF002 # Intentional Arabic-Indic digits
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# PAGE XML namespace (W3C 2019-07-15 schema)
PAGE_NS = {"page": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"}


class MuharafParser(BaseParser):
    """Parser for Muharaf Arabic Historical Manuscripts dataset.

    Extracts annotations from PAGE XML format:
    - Polygon coordinates (converted to YOLO bbox)
    - Arabic text transcriptions
    - Reading order metadata
    - Language/script attributes
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["muharaf", "muharaf-arabic-manuscripts"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Muharaf labels from PAGE XML files.

        Args:
            dataset_path: Root path of the Muharaf dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with Arabic text, language/script metadata,
            and polygon coordinates converted to YOLO bboxes
        """
        labels = OriginalLabels()

        # Set language/script for Arabic handwriting
        labels.language_code = "ar"
        labels.script_name = "Arabic"
        labels.iso15924_script_code = "Arab"

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Add dataset metadata
        labels.raw_labels["dataset"] = "muharaf"
        labels.raw_labels["production"] = "handwritten-cursive"
        labels.raw_labels["reading_direction"] = "right-to-left"

        # Try to find and parse companion PAGE XML file
        xml_path = image_path.with_suffix(".xml")
        if not xml_path.exists():
            # Try alternate locations (may be in same directory)
            xml_path = self._find_annotation_file(
                dataset_path,
                [
                    f"**/{image_path.stem}.xml",
                ],
            )

        if xml_path and xml_path.exists():
            try:
                self._parse_page_xml(xml_path, image_path, labels)
            except Exception as e:
                logger.warning(f"Failed to parse PAGE XML for {image_path.name}: {e}")
        else:
            logger.debug(f"No PAGE XML found for {image_path.name}")

        return labels

    def _parse_page_xml(
        self,
        xml_path: Path,
        image_path: Path,
        labels: OriginalLabels,
    ) -> None:
        """Parse PAGE XML file and populate labels.

        Args:
            xml_path: Path to PAGE XML file
            image_path: Path to image file (for dimensions)
            labels: OriginalLabels instance to populate
        """
        tree = ET.parse(xml_path)  # noqa: S314 # Trusted dataset XML
        root = tree.getroot()

        # Extract page metadata
        page_elem = root.find(".//page:Page", PAGE_NS)
        if page_elem is None:
            logger.warning(f"No Page element in {xml_path.name}")
            return

        # Get image dimensions for normalization
        image_width = int(page_elem.get("imageWidth", 0))
        image_height = int(page_elem.get("imageHeight", 0))

        if image_width == 0 or image_height == 0:
            logger.warning(f"Invalid image dimensions in {xml_path.name}")
            return

        # Store image dimensions
        labels.raw_labels["image_width"] = image_width
        labels.raw_labels["image_height"] = image_height

        # Extract reading order
        reading_order = self._extract_reading_order(root)
        if reading_order:
            labels.raw_labels["reading_order"] = reading_order

        # Extract text regions and lines
        text_regions = []
        all_text_lines = []
        full_text_parts = []

        for region_elem in root.findall(".//page:TextRegion", PAGE_NS):
            region_id = region_elem.get("id", "")
            region_type = region_elem.get("type", "paragraph")

            # Extract region polygon
            region_coords = self._extract_coords(region_elem)
            region_bbox = None
            if region_coords and image_width > 0 and image_height > 0:
                region_bbox = self._polygon_to_yolo_bbox(
                    region_coords, image_width, image_height
                )

            # Extract text lines within region
            text_lines = []
            for line_elem in region_elem.findall(".//page:TextLine", PAGE_NS):
                line_id = line_elem.get("id", "")
                line_index = line_elem.get("index", "0")

                # Extract line polygon
                line_coords = self._extract_coords(line_elem)
                line_bbox = None
                if line_coords and image_width > 0 and image_height > 0:
                    line_bbox = self._polygon_to_yolo_bbox(
                        line_coords, image_width, image_height
                    )

                # Extract text content
                text_equiv = line_elem.find(".//page:TextEquiv/page:Unicode", PAGE_NS)
                text = text_equiv.text if text_equiv is not None else ""

                if text:
                    full_text_parts.append(text)

                # Extract language/script attributes
                lang = line_elem.get("primaryLanguage", "Arabic")
                production = line_elem.get("production", "handwritten-cursive")
                reading_dir = line_elem.get("readingDirection", "right-to-left")

                # Extract center-line (baseline) if available
                center_line = self._extract_center_line(line_elem)

                line_data = {
                    "line_id": line_id,
                    "line_index": int(line_index),
                    "text": text,
                    "polygon": line_coords,
                    "bbox": line_bbox,
                    "language": lang,
                    "production": production,
                    "reading_direction": reading_dir,
                }

                if center_line:
                    line_data["center_line"] = center_line

                text_lines.append(line_data)
                all_text_lines.append(line_data)

            region_data = {
                "region_id": region_id,
                "region_type": region_type,
                "polygon": region_coords,
                "bbox": region_bbox,
                "lines": text_lines,
            }

            text_regions.append(region_data)

        # Store all extracted data
        if text_regions:
            labels.raw_labels["text_regions"] = text_regions
            labels.raw_labels["text_lines"] = all_text_lines
            labels.raw_labels["region_count"] = len(text_regions)
            labels.raw_labels["line_count"] = len(all_text_lines)

        # Set transcription field (join all text lines)
        if full_text_parts:
            full_text = "\n".join(full_text_parts)
            labels.transcription = full_text

            # Populate Layer 2 text_content schema fields
            labels.text_content = {
                "full_text": full_text,
                "source_type": "dataset_provided",
                "source_format": "page_xml_unicode",
                "extraction_method": "MuharafParser.parse",
                "extraction_timestamp": None,
                "is_complete": True,
                "encoding": "utf-8",
            }

    def _extract_coords(self, elem: ET.Element) -> list[list[float]] | None:
        """Extract polygon coordinates from Coords element.

        Args:
            elem: XML element containing Coords child

        Returns:
            List of [x, y] coordinate pairs, or None if not found
        """
        coords_elem = elem.find(".//page:Coords", PAGE_NS)
        if coords_elem is None:
            return None

        points_str = coords_elem.get("points", "")
        if not points_str:
            return None

        try:
            # Parse "x1,y1 x2,y2 x3,y3 ..." format
            coords = []
            for point in points_str.strip().split():
                x, y = point.split(",")
                coords.append([float(x), float(y)])
            return coords
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse polygon coordinates: {e}")
            return None

    def _polygon_to_yolo_bbox(
        self,
        polygon: list[list[float]],
        image_width: int,
        image_height: int,
    ) -> dict[str, Any]:
        """Convert polygon coordinates to YOLO bbox format.

        Args:
            polygon: List of [x, y] coordinate pairs
            image_width: Image width in pixels
            image_height: Image height in pixels

        Returns:
            Dict with normalized YOLO bbox [x_center, y_center, width, height]
            and metadata about the conversion
        """
        if not polygon or image_width == 0 or image_height == 0:
            return {
                "bbox": [0.0, 0.0, 0.0, 0.0],
                "bbox_type": "axis_aligned",
                "conversion_note": "invalid_input",
            }

        # Calculate axis-aligned bounding box
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        # Convert to YOLO format (normalized center + dimensions)
        x_center = ((min_x + max_x) / 2) / image_width
        y_center = ((min_y + max_y) / 2) / image_height
        width = (max_x - min_x) / image_width
        height = (max_y - min_y) / image_height

        return {
            "bbox": [x_center, y_center, width, height],
            "bbox_type": "axis_aligned",
            "conversion_note": "polygon_to_bbox",
        }

    def _extract_reading_order(self, root: ET.Element) -> list[dict[str, Any]] | None:
        """Extract reading order metadata from ReadingOrder element.

        Args:
            root: Root XML element

        Returns:
            List of reading order group dictionaries, or None if not found
        """
        reading_order_elem = root.find(".//page:ReadingOrder", PAGE_NS)
        if reading_order_elem is None:
            return None

        groups = []
        for group in reading_order_elem.findall(".//page:OrderedGroupIndexed", PAGE_NS):
            group_id = group.get("id", "")
            caption = group.get("caption", "")
            index = int(group.get("index", 0))

            region_refs = []
            for ref in group.findall(".//page:RegionRefIndexed", PAGE_NS):
                region_refs.append(
                    {
                        "region_ref": ref.get("regionRef", ""),
                        "index": int(ref.get("index", 0)),
                    }
                )

            groups.append(
                {
                    "group_id": group_id,
                    "caption": caption,
                    "index": index,
                    "region_refs": region_refs,
                }
            )

        return groups if groups else None

    def _extract_center_line(self, line_elem: ET.Element) -> list[list[float]] | None:
        """Extract center-line (baseline) coordinates from UserDefined.

        Args:
            line_elem: TextLine XML element

        Returns:
            List of [x, y] coordinate pairs for baseline, or None if not found
        """
        user_attr = line_elem.find(
            './/page:UserDefined/page:UserAttribute[@name="center-line"]', PAGE_NS
        )
        if user_attr is None:
            return None

        value = user_attr.get("value", "")
        if not value:
            return None

        try:
            # Parse "x1,y1 x2,y2 ..." format
            coords = []
            for point in value.strip().split():
                x, y = point.split(",")
                coords.append([float(x), float(y)])
            return coords
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse center-line coordinates: {e}")
            return None


__all__ = ["MuharafParser"]
