"""Parser for Arabic Documents OCR dataset.

Arabic Documents OCR contains scanned Arabic documents across
12 different categories/document types with Supervisely annotations.

Dataset Structure:
    arabic_docs_ocr/
        Documents/
            Documents/
                {category}/
                    img/  # Images (JPG/PNG)
                    ann/  # Supervisely JSON annotations

12 Categories:
    Administrative form, Book, Business card, Comics, Handwritten text,
    Invoice, Label, Magazine, Map, Newspaper, Official document, Receipt

Annotation Format (Supervisely):
    {
      "size": {"height": int, "width": int},
      "objects": [
        {
          "classTitle": "Title" | "Body text" | "Page",
          "geometryType": "rectangle" | "polygon",
          "points": {
            "exterior": [[x1, y1], [x2, y2], ...],
            "interior": []
          },
          "tags": [
            {"name": "Transcription", "value": "Arabic text"}
          ]
        }
      ]
    }

Extracts:
    - Bounding boxes (COCO format from rectangles)
    - Polygons (page boundaries)
    - Text transcriptions (from tags)
    - Layout classes (Title, Body text, Page)
    - Image dimensions
    - language_code: Fixed "ar" (Arabic)
    - script_name: Fixed "Arabic"
    - document_type: Category from directory

Example:
    >>> parser = ArabicDocsParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/arabic_docs_ocr"),
    ...     image_path=Path(
    ...         "/data/arabic_docs_ocr/Documents/Documents/Invoice/img/001.jpg"
    ...     ),
    ...     config={},
    ... )
    >>> print(len(labels.bbox))  # Multiple bounding boxes
    >>> print(labels.text_content)  # Concatenated Arabic text
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "arabic-docs"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "arabic_docs_metadata.json"
__l4_integrate__ = "scripts/integrate_arabic_docs_ocr_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class ArabicDocsParser(BaseParser):
    """Parser for Arabic Documents OCR dataset with Supervisely annotations.

    Extracts bounding boxes, polygons, text transcriptions, and layout classes
    from Supervisely JSON format.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["arabic_docs_ocr"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Arabic Documents labels from Supervisely JSON.

        Args:
            dataset_path: Root path of the arabic_docs_ocr dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with bounding boxes, text transcriptions, layout classes,
            language/script metadata, and document category
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Fixed: Arabic script (ISO 15924: Arab, ISO 639: ar)
        labels.language_code = "ar"
        labels.script_name = "Arabic"  # Human-readable name
        labels.iso15924_script_code = "Arab"  # Standardized ISO 15924 code

        # Extract category from parent directory
        path_parts = image_path.parts
        category = None
        for i, part in enumerate(path_parts):
            if part == "Documents" and i + 1 < len(path_parts):
                category = path_parts[i + 1]
                labels.raw_labels["category"] = category
                labels.raw_labels["document_type"] = category
                break

        # Find corresponding annotation JSON file
        # Pattern: img/001.jpg -> ann/001.json
        if image_path.parent.name == "img":
            ann_dir = image_path.parent.parent / "ann"
            json_path = ann_dir / f"{image_path.stem}.json"

            if not json_path.exists():
                logger.warning(
                    f"Annotation file not found for {image_path.name}: {json_path}"
                )
                return labels

            # Parse Supervisely JSON
            try:
                with open(json_path, encoding="utf-8") as f:
                    ann_data = json.load(f)

                # Extract image dimensions
                if "size" in ann_data:
                    labels.raw_labels["image_width"] = ann_data["size"].get("width")
                    labels.raw_labels["image_height"] = ann_data["size"].get("height")

                # Extract objects (bounding boxes, polygons, transcriptions)
                bbox_list = []
                polygon_list = []
                text_list = []
                class_list = []

                for obj in ann_data.get("objects", []):
                    class_title = obj.get("classTitle", "")
                    geometry_type = obj.get("geometryType", "")
                    points = obj.get("points", {})
                    exterior = points.get("exterior", [])

                    # Extract text transcription from tags
                    text = None
                    for tag in obj.get("tags", []):
                        if tag.get("name") == "Transcription":
                            text = tag.get("value", "")
                            if text:
                                text_list.append(text)
                            break

                    # Convert rectangle to COCO bbox [x, y, width, height]
                    if geometry_type == "rectangle" and len(exterior) == 2:
                        x1, y1 = exterior[0]
                        x2, y2 = exterior[1]
                        x_min = min(x1, x2)
                        y_min = min(y1, y2)
                        width = abs(x2 - x1)
                        height = abs(y2 - y1)

                        bbox_dict = {
                            "bbox": [x_min, y_min, width, height],
                            "category": class_title,
                            "text": text,
                        }
                        bbox_list.append(bbox_dict)
                        class_list.append(class_title)

                    # Store polygon points (for page boundaries)
                    elif geometry_type == "polygon" and exterior:
                        polygon_list.append(
                            {"class": class_title, "points": exterior, "text": text}
                        )
                        class_list.append(class_title)

                # Store extracted data
                if bbox_list:
                    labels.raw_labels["bbox"] = bbox_list

                if text_list:
                    # Concatenate all transcriptions with newlines
                    labels.raw_labels["text_content"] = "\n".join(text_list)
                    labels.raw_labels["text_source"] = "ground_truth"
                    labels.raw_labels["transcription_count"] = len(text_list)

                if polygon_list:
                    labels.raw_labels["polygons"] = polygon_list

                if class_list:
                    labels.raw_labels["layout_classes"] = list(set(class_list))
                    labels.raw_labels["object_count"] = len(class_list)

            except json.JSONDecodeError:
                logger.exception("Failed to parse JSON %s", json_path)
            except Exception:
                logger.exception("Error processing annotation %s", json_path)

        return labels


__all__ = ["ArabicDocsParser"]
