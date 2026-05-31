"""Parser for MIDV-500 ID document dataset.

MIDV-500 (Mobile Identity Document Video) provides images of identity documents
from 50 countries with various document types (ID cards, passports, driver's licenses).

Dataset Structure:
    midv500/
        {doc_id}/                        # e.g., 01_alb_id
            images/
                {doc_id}.tif             # Template image
                CA/                      # Camera captures (video frames)
                    CA01_01.tif
                    CA01_02.tif
            ground_truth/
                {doc_id}.json            # Template with field text + quads
                CA/                      # Frame annotations (document quads only)
                    CA01_01.json

Document Types:
    - ID card
    - Passport
    - Driver's license (driving_licence, driverlicense, dl)

Country Coverage:
    50 countries with 2-3 letter country codes (e.g., RU, USA, DEU)
    Includes Cyrillic script countries (RU, UA, BY, BG, RS, KZ)

Ground Truth Annotations:
    Template JSON files contain field-level annotations:
    {
      "field01": {"quad": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]], "value": "John"},
      "field02": {"quad": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]], "value": "Smith"},
      ...
      "photo": {"quad": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]},
      "signature": {"quad": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]}
    }

Example:
    >>> parser = Midv500Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/midv500"),
    ...     image_path=Path("/data/midv500/01_alb_id/images/01_alb_id.tif"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["country_code"])
    "ALB"
    >>> print(labels.text_content["full_text"])
    "Sojli Monika Shqiptare/Albanian ..."
    >>> print(len(labels.layout_detections))
    11  # Field quads extracted
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "midv500"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "midv500_metadata.json"
__l4_integrate__ = "scripts/integrate_midv500_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class Midv500Parser(BaseParser):
    """Parser for MIDV-500 ID document dataset.

    Extracts country code and document type from directory structure.
    Loads ground truth text and field quads from template JSON files.
    Sets script_name for Cyrillic countries.
    """

    # Cyrillic countries (for script detection)
    # Supports both 2-letter and 3-letter country codes
    CYRILLIC_COUNTRIES = {
        "RU",
        "RUS",  # Russia
        "UA",
        "UKR",  # Ukraine
        "BY",
        "BLR",  # Belarus
        "BG",
        "BGR",  # Bulgaria
        "RS",
        "SRB",  # Serbia
        "KZ",
        "KAZ",  # Kazakhstan
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["midv500"]

    def _extract_doc_id_from_path(self, image_path: Path) -> str | None:
        """Extract document ID from image path.

        Args:
            image_path (Path): Path to image file (e.g., .../01_alb_id/images/01_alb_id.tif).

        Returns:
            str | None: Document ID string (e.g., "01_alb_id") or None if not found.
        """
        # Document ID is the parent directory name (e.g., 01_alb_id, 02_aut_drvlic_new)
        # Path structure: {doc_id}/images/{image_file}
        parts = image_path.parts
        for i, part in enumerate(parts):
            if part == "images" and i > 0:
                return parts[i - 1]

        # Fallback: check if parent directory looks like doc_id pattern
        parent = image_path.parent.name
        if "_" in parent and parent[0].isdigit():
            return parent

        return None

    def _load_ground_truth_template(
        self,
        dataset_path: Path,
        doc_id: str,
    ) -> dict[str, Any] | None:
        """Load ground truth template JSON for document type.

        Args:
            dataset_path (Path): Root dataset path.
            doc_id (str): Document ID (e.g., "01_alb_id").

        Returns:
            dict[str, Any] | None: Template JSON data or None if not found.
        """
        # Try multiple template file path patterns
        template_patterns = [
            dataset_path / doc_id / "ground_truth" / f"{doc_id}.json",
            dataset_path / "midv500" / doc_id / "ground_truth" / f"{doc_id}.json",
            dataset_path.parent / doc_id / "ground_truth" / f"{doc_id}.json",
        ]

        for template_path in template_patterns:
            if template_path.exists():
                try:
                    with open(template_path) as f:
                        result: dict[str, Any] = json.load(f)
                        return result
                except (OSError, json.JSONDecodeError) as e:
                    logger.warning(
                        "Failed to load template JSON from %s: %s",
                        template_path,
                        e,
                    )
                    continue

        logger.debug("Template JSON not found for doc_id=%s", doc_id)
        return None

    def _extract_text_from_template(
        self,
        template_data: dict[str, Any],
    ) -> str:
        """Extract all text values from template JSON.

        Args:
            template_data (dict[str, Any]): Template JSON with field## entries.

        Returns:
            str: Concatenated text from all fields.
        """
        text_parts = []
        for field_id in sorted(template_data.keys()):
            if field_id.startswith("field"):
                field_data = template_data[field_id]
                if isinstance(field_data, dict) and "value" in field_data:
                    text_parts.append(field_data["value"])

        return " ".join(text_parts)

    def _extract_quads_from_template(
        self,
        template_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract quadrilateral annotations from template JSON.

        Args:
            template_data (dict[str, Any]): Template JSON with field## entries containing quads.

        Returns:
            list[dict[str, Any]]: List of layout detections with COCO bboxes.
        """
        layout_detections = []

        for field_id in sorted(template_data.keys()):
            field_data = template_data.get(field_id)
            if not isinstance(field_data, dict) or "quad" not in field_data:
                continue

            quad = field_data["quad"]
            if len(quad) != 4:
                logger.warning("Invalid quad for field %s: %s", field_id, quad)
                continue

            # Convert quad [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] to COCO bbox
            try:
                xs = [pt[0] for pt in quad]
                ys = [pt[1] for pt in quad]
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)
                coco_bbox = [x_min, y_min, x_max - x_min, y_max - y_min]

                # Determine class name based on field type
                class_name = "Text"  # Default for field## entries
                if field_id == "photo":
                    class_name = "Picture"
                elif field_id == "signature":
                    class_name = "Signature"

                layout_detections.append(
                    {
                        "class_name": class_name,
                        "bbox": coco_bbox,
                        "bbox_original": quad,
                        "bbox_source_format": "quad_4pt",
                        "confidence": 1.0,  # Ground truth
                        "source": "midv500_template",
                        "field_id": field_id,
                    }
                )
            except (TypeError, ValueError, IndexError) as e:
                logger.warning(
                    "Failed to convert quad to bbox for field %s: %s",
                    field_id,
                    e,
                )
                continue

        return layout_detections

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MIDV-500 labels from path structure and template JSON.

        Args:
            dataset_path (Path): Root path of the MIDV-500 dataset.
            image_path (Path): Absolute path to the image file being processed.
            config (dict[str, Any]): Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels: OriginalLabels with country_code, document_type in raw_labels,
                text_content from template JSON, layout_detections from field quads,
                and script_name set for Cyrillic countries.
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Extract document ID from path (e.g., "01_alb_id")
        doc_id = self._extract_doc_id_from_path(image_path)
        if doc_id:
            labels.raw_labels["document_id"] = doc_id

            # Extract country code from doc_id (e.g., "01_alb_id" -> "ALB")
            # Format: {number}_{country_code}_{doc_type}
            parts_doc_id = doc_id.split("_")
            if len(parts_doc_id) >= 2:
                # Country code is typically the second part
                country_code_candidate = parts_doc_id[1].upper()
                if len(country_code_candidate) in (2, 3):
                    labels.raw_labels["country_code"] = country_code_candidate

                # Document type is the remaining parts
                if len(parts_doc_id) >= 3:
                    doc_type_raw = "_".join(parts_doc_id[2:])
                    labels.raw_labels["document_type"] = doc_type_raw

                    # Normalize document type
                    doc_type_lower = doc_type_raw.lower()
                    if doc_type_lower in (
                        "drvlic",
                        "driverlicense",
                        "driving_licence",
                        "dl",
                    ):
                        labels.raw_labels["document_type_normalized"] = "driver_license"
                    elif "passport" in doc_type_lower:
                        labels.raw_labels["document_type_normalized"] = "passport"
                    elif "id" in doc_type_lower:
                        labels.raw_labels["document_type_normalized"] = "id"
                    else:
                        labels.raw_labels["document_type_normalized"] = doc_type_lower

        # Load ground truth template JSON if available
        if doc_id:
            template = self._load_ground_truth_template(dataset_path, doc_id)

            if template:
                # Extract text content from template and store in transcription field
                full_text = self._extract_text_from_template(template)
                if full_text:
                    labels.transcription = full_text

                # Extract field quads from template and store in raw_labels
                layout_detections = self._extract_quads_from_template(template)
                if layout_detections:
                    labels.raw_labels["layout_detections"] = layout_detections
                    labels.raw_labels["template_file"] = f"{doc_id}.json"

        # Set script name for Cyrillic countries
        country_code = labels.raw_labels.get("country_code")
        if country_code in self.CYRILLIC_COUNTRIES:
            labels.script_name = "Cyrillic"

        return labels


__all__ = ["Midv500Parser"]
