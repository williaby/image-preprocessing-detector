"""Parser for RVL-CDIP document classification dataset.

RVL-CDIP (Ryerson Vision Lab Complex Document Information Processing) provides
16-class document classification labels encoded in filenames, with additional
layout annotations and OCR text available for enhanced analysis.

Dataset Structure:
    rvl_cdip/
        images/
            rvl_{class}_{number}.jpg
        annotations/rvl-cdip/
            layout/
                layout_batch_{N}.json  (COCO format with 11 DocLayNet classes)
            ocr/
                ocr_batch_{N}.jsonl    (OCR text extraction)

16 Document Classes:
    - advertisement, budget, email, file_folder
    - form, handwritten, invoice, letter
    - memo, news_article, presentation, questionnaire
    - resume, scientific_publication, scientific_report, specification

Filename Format:
    rvl_{class}_{number}.jpg
    Example: rvl_advertisement_0000.jpg

Layout Annotations:
    - 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer,
      Page-Header, Picture, Section-Header, Table, Text, Title)
    - COCO format with bounding boxes, confidence scores, and areas
    - ~50,000 annotations across 27 batch files

OCR Text:
    - Full-text extraction for all 16,000 images
    - JSONL format with confidence scores
    - Includes processing metadata

Example:
    >>> parser = RvlCdipParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/rvl_cdip"),
    ...     image_path=Path("/data/rvl_cdip/images/rvl_advertisement_0000.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["document_class"])
    "advertisement"
    >>> print(len(labels.raw_labels["layout_detections"]))
    15  # Number of layout elements detected
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "rvl-cdip"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "rvl_cdip_metadata.json"
__l4_integrate__ = "scripts/integrate_rvl_cdip_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class RvlCdipParser(BaseParser):
    """Parser for RVL-CDIP document classification dataset.

    Extracts document class from filename pattern (rvl_{class}_{number}.jpg),
    layout annotations from COCO JSON files, and OCR text from JSONL files.
    Maps class names to numeric IDs and sets document_type field for
    downstream compatibility.

    Annotation Sources:
        - Layout: annotations/rvl-cdip/layout/layout_batch_{N}.json (COCO format)
        - OCR: annotations/rvl-cdip/ocr/ocr_batch_{N}.jsonl (JSONL format)
    """

    # RVL-CDIP class definitions (16 classes)
    RVL_CLASSES = {
        "advertisement": 0,
        "budget": 1,
        "email": 2,
        "file_folder": 3,
        "form": 4,
        "handwritten": 5,
        "invoice": 6,
        "letter": 7,
        "memo": 8,
        "news_article": 9,
        "presentation": 10,
        "questionnaire": 11,
        "resume": 12,
        "scientific_publication": 13,
        "scientific_report": 14,
        "specification": 15,
    }

    # DocLayNet classes used in layout annotations (11 classes)
    DOCLAYNET_CLASSES = {
        0: "Caption",
        1: "Footnote",
        2: "Formula",
        3: "List-Item",
        4: "Page-Footer",
        5: "Page-Header",
        6: "Picture",
        7: "Section-Header",
        8: "Table",
        9: "Text",
        10: "Title",
    }

    # Cache for loaded annotation files (optimization for batch processing)
    _layout_cache: dict[str, dict[str, Any]] = {}
    _ocr_cache: dict[str, list[dict[str, Any]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["rvl_cdip"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse RVL-CDIP labels from filename, layout annotations, and OCR text.

        Args:
            dataset_path (Path): Root path of the RVL-CDIP dataset.
            image_path (Path): Absolute path to the image file being processed.
            config (dict[str, Any]): Dataset configuration dictionary (optional).
                extract_layout (bool): Default True - Extract layout annotations.
                extract_ocr (bool): Default True - Extract OCR text.

        Returns:
            OriginalLabels: OriginalLabels with document_class, document_class_id,
                document_type, layout_detections, and text_content populated in raw_labels.
        """
        labels = OriginalLabels()

        # Parse class from filename: rvl_{class}_{number}.jpg
        filename = image_path.stem  # e.g., "rvl_advertisement_0000"

        if labels.raw_labels is None:
            labels.raw_labels = {}

        if filename.startswith("rvl_"):
            # Remove 'rvl_' prefix and split by underscore
            # Split from right to handle multi-word classes like "scientific_publication"
            parts = filename[4:].rsplit("_", 1)
            if len(parts) == 2:
                class_name = parts[
                    0
                ]  # e.g., "advertisement" or "scientific_publication"
                image_number = parts[1]  # e.g., "0000"

                if class_name in self.RVL_CLASSES:
                    labels.raw_labels["document_class"] = class_name
                    labels.raw_labels["document_class_id"] = self.RVL_CLASSES[
                        class_name
                    ]
                    labels.raw_labels["image_number"] = image_number

                    # Map to document type for downstream compatibility
                    # Convert snake_case to Title Case
                    labels.raw_labels["document_type"] = class_name.replace(
                        "_", " "
                    ).title()

        # Extract layout annotations if enabled (default: True)
        extract_layout = config.get("extract_layout", True)
        if extract_layout:
            layout_detections = self._extract_layout_annotations(
                image_path.name, dataset_path
            )
            if layout_detections:
                labels.raw_labels["layout_detections"] = layout_detections

        # Extract OCR text if enabled (default: True)
        extract_ocr = config.get("extract_ocr", True)
        if extract_ocr:
            text_content = self._extract_ocr_text(image_path.name, dataset_path)
            if text_content:
                labels.raw_labels["text_content"] = text_content

        return labels

    def _extract_layout_annotations(
        self, filename: str, dataset_path: Path
    ) -> list[dict[str, Any]] | None:
        """Extract layout annotations from COCO JSON batch files.

        Args:
            filename (str): Image filename (e.g., "rvl_advertisement_0000.jpg").
            dataset_path (Path): Root path of the RVL-CDIP dataset.

        Returns:
            list[dict[str, Any]] | None: List of layout detections with bounding boxes
                and class labels, or None if no annotations found.
        """
        # Determine annotation directory path
        # Try multiple possible paths for flexibility
        possible_paths = [
            dataset_path / "annotations" / "rvl-cdip" / "layout",
            dataset_path.parent / "annotations" / "rvl-cdip" / "layout",
            Path("/mnt/e/image_detection/annotations/rvl-cdip/layout"),
        ]

        layout_dir = None
        for path in possible_paths:
            if path.exists():
                layout_dir = path
                break

        if not layout_dir:
            logger.debug(f"Layout annotation directory not found for {filename}")
            return None

        # Search all batch files for this image's annotations
        # Note: We don't know which batch file contains this image, so we check all
        layout_detections = []

        for batch_file in sorted(layout_dir.glob("layout_batch_*.json")):
            # Load batch file (with caching for performance)
            batch_key = str(batch_file)
            if batch_key not in self._layout_cache:
                try:
                    with open(batch_file) as f:
                        self._layout_cache[batch_key] = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to load {batch_file}: {e}")
                    continue

            coco_data = self._layout_cache[batch_key]

            # Find image_id for this filename
            image_id = None
            for img in coco_data.get("images", []):
                if img.get("file_name") == filename:
                    image_id = img.get("id")
                    break

            if image_id is None:
                continue  # Not in this batch, try next

            # Extract annotations for this image_id
            for ann in coco_data.get("annotations", []):
                if ann.get("image_id") == image_id:
                    # Convert COCO annotation to standardized format
                    detection = {
                        "bbox": ann.get("bbox"),  # [x, y, width, height]
                        "category_id": ann.get("category_id"),
                        "category_name": ann.get(
                            "category_name",
                            self.DOCLAYNET_CLASSES.get(ann.get("category_id")),
                        ),
                        "confidence": ann.get("confidence"),
                        "area": ann.get("area"),
                        "source": "doclayout_yolo",
                    }
                    layout_detections.append(detection)

            # Found the image, no need to check remaining batches
            if image_id is not None:
                break

        return layout_detections or None

    def _extract_ocr_text(
        self, filename: str, dataset_path: Path
    ) -> dict[str, Any] | None:
        """Extract OCR text from JSONL batch files.

        Args:
            filename (str): Image filename (e.g., "rvl_advertisement_0000.jpg").
            dataset_path (Path): Root path of the RVL-CDIP dataset.

        Returns:
            dict[str, Any] | None: Dictionary with full_text, confidence, and provenance
                metadata, or None if no OCR found.
        """
        # Determine annotation directory path
        possible_paths = [
            dataset_path / "annotations" / "rvl-cdip" / "ocr",
            dataset_path.parent / "annotations" / "rvl-cdip" / "ocr",
            Path("/mnt/e/image_detection/annotations/rvl-cdip/ocr"),
        ]

        ocr_dir = None
        for path in possible_paths:
            if path.exists():
                ocr_dir = path
                break

        if not ocr_dir:
            logger.debug(f"OCR annotation directory not found for {filename}")
            return None

        # Construct expected source path (GCS path format used in JSONL files)
        expected_source = (
            f"image-preprocessing-detector/datasets/rvl_cdip/rvl_cdip/images/{filename}"
        )

        # Search all batch files for this image's OCR text
        for batch_file in sorted(ocr_dir.glob("ocr_batch_*.jsonl")):
            batch_key = str(batch_file)

            # Load batch file (with caching for performance)
            if batch_key not in self._ocr_cache:
                entries = []
                try:
                    with open(batch_file) as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                entries.append(json.loads(line))
                    self._ocr_cache[batch_key] = entries
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Failed to load {batch_file}: {e}")
                    continue

            # Search for matching entry
            for entry in self._ocr_cache[batch_key]:
                source = entry.get("source", "")
                if source.endswith(filename) or source == expected_source:
                    if entry.get("success"):
                        # Calculate text statistics
                        text = entry.get("text", "")
                        char_count = len(text)
                        word_count = len(text.split())

                        return {
                            "full_text": text,
                            "source_type": "ocr_tesseract",  # Confidence=1.0 suggests Tesseract
                            "source_file": str(batch_file),
                            "confidence": entry.get("confidence", 1.0),
                            "processing_time_ms": entry.get("processing_time_ms"),
                            "tables_found": entry.get("tables_found", 0),
                            "character_count": char_count,
                            "word_count": word_count,
                        }
                    # OCR failed for this image
                    logger.warning(
                        f"OCR extraction failed for {filename}: "
                        f"{entry.get('error', 'Unknown error')}"
                    )
                    return None

        # Not found in any batch file
        return None


__all__ = ["RvlCdipParser"]
