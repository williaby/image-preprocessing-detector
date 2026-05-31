"""Parser for COCO-Text v2 scene text detection dataset.

COCO-Text provides word-level text annotations for images from MS COCO 2014.
Each image may contain multiple text instances with bounding boxes, transcriptions,
and attributes (legibility, class, language).

Dataset Structure:
    cocotext/
        cocotext.v2.json          # Main annotation file (53MB)
        images/                    # Images from COCO 2014 (requires separate download)
            COCO_train2014_*.jpg
            COCO_val2014_*.jpg

Annotation Format (cocotext.v2.json):
    {
        "imgs": {
            "image_id": {
                "id": 123456,
                "width": 640,
                "height": 480,
                "file_name": "COCO_train2014_000000123456.jpg",
                "set": "train"
            }
        },
        "anns": {
            "annotation_id": {
                "id": 1,
                "image_id": 123456,
                "bbox": [x, y, width, height],  # COCO format
                "utf8_string": "Hello World",
                "language": "english",          # english/not_english/na
                "class": "machine printed",     # machine printed/handwritten
                "legibility": "legible",        # legible/illegible
                "area": 1200
            }
        },
        "imgToAnns": {
            "image_id": [ann_id1, ann_id2, ...]
        }
    }

Labels Extracted:
    - text_instances: List of word-level annotations with bbox, text, attributes
    - language_code: Mapped from COCO-Text language labels
    - raw_labels: Split info, handwriting detection, legibility stats

Dataset Statistics:
    - 63,686 images (from COCO 2014 train/val)
    - 145,859 text instances
    - ~43K train, ~10K val, ~10K test images

Example:
    >>> parser = CocotextParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/cocotext"),
    ...     image_path=Path("/data/cocotext/images/COCO_train2014_000000123456.jpg"),
    ...     config={},
    ... )
    >>> print(len(labels.text_instances))
    5
    >>> print(labels.raw_labels["has_handwriting"])
    True
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "cocotext"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "cocotext_metadata.json"
__l4_integrate__ = "scripts/integrate_cocotext_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any, ClassVar

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class CocotextParser(BaseParser):
    """Parser for COCO-Text v2 scene text detection dataset.

    Extracts word-level text annotations including:
    - Bounding boxes (COCO format: [x, y, width, height])
    - Text transcriptions (utf8_string)
    - Language labels (english/not_english/na)
    - Text class (machine printed/handwritten)
    - Legibility (legible/illegible)

    Caches the annotation file at class level for efficient batch processing.
    """

    # Class-level cache for annotation data (shared across instances)
    _annotations_cache: ClassVar[dict[str, Any] | None] = None
    _filename_to_id_cache: ClassVar[dict[str, int] | None] = None
    _cache_path: ClassVar[Path | None] = None

    # Language mapping from COCO-Text to ISO 639-1
    LANGUAGE_MAP: ClassVar[dict[str, str]] = {
        "english": "en",
        "not_english": "und",  # Undetermined (ISO 639-3)
        "na": "",  # Not applicable (no text)
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["cocotext", "coco-text", "coco_text"]

    def _load_annotations(self, dataset_path: Path) -> bool:
        """Load COCO-Text annotations from JSON file.

        Uses class-level caching to avoid reloading for each image.

        Args:
            dataset_path (Path): Root path of the COCO-Text dataset

        Returns:
            bool: True if annotations loaded successfully, False otherwise
        """
        # Check if already cached for this path
        if (
            CocotextParser._annotations_cache is not None
            and CocotextParser._cache_path == dataset_path
        ):
            return True

        # Try to find annotation file
        # Check both dataset_path and parent (for when path points to images/)
        search_paths = [dataset_path, dataset_path.parent]
        ann_patterns = [
            "cocotext.v2.json",
            "COCO_Text.json",
            "annotations/cocotext.v2.json",
        ]

        ann_path = None
        for search_path in search_paths:
            for pattern in ann_patterns:
                candidate = search_path / pattern
                if candidate.exists():
                    ann_path = candidate
                    break
            if ann_path:
                break

        if ann_path is None:
            logger.warning(f"COCO-Text annotation file not found in {dataset_path}")
            return False

        try:
            logger.debug(f"Loading COCO-Text annotations from {ann_path}")
            with open(ann_path, encoding="utf-8") as f:
                data = json.load(f)

            # Build filename → image_id mapping for fast lookup
            filename_to_id: dict[str, int] = {}
            if "imgs" in data:
                for img_id, img_info in data["imgs"].items():
                    filename = img_info.get("file_name", "")
                    if filename:
                        filename_to_id[filename] = int(img_id)
                        # Also index by basename for flexibility
                        filename_to_id[Path(filename).name] = int(img_id)

            CocotextParser._annotations_cache = data
            CocotextParser._filename_to_id_cache = filename_to_id
            CocotextParser._cache_path = dataset_path

            logger.debug(
                f"Loaded COCO-Text: {len(data.get('imgs', {}))} images, "
                f"{len(data.get('anns', {}))} annotations"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to load COCO-Text annotations: {e}")
            return False

    def _get_image_id(self, image_path: Path) -> int | None:
        """Get COCO image ID from filename.

        Args:
            image_path (Path): Path to the image file

        Returns:
            int | None: Image ID if found, None otherwise
        """
        if CocotextParser._filename_to_id_cache is None:
            return None

        # Try full filename first, then basename
        for name in [str(image_path), image_path.name]:
            if name in CocotextParser._filename_to_id_cache:
                return CocotextParser._filename_to_id_cache[name]

        # Try extracting ID from filename pattern: COCO_train2014_000000123456.jpg
        stem = image_path.stem
        if "_" in stem:
            try:
                # Extract numeric ID from end of filename
                return int(stem.split("_")[-1])
            except ValueError:
                pass

        return None

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse COCO-Text annotations for an image.

        Args:
            dataset_path (Path): Root path of the COCO-Text dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with text_instances and raw_labels containing
            text annotations, language info, and attribute statistics
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Load annotations if not cached
        if not self._load_annotations(dataset_path):
            labels.raw_labels["error"] = "annotations_not_found"
            return labels

        # Get image ID
        img_id = self._get_image_id(image_path)
        if img_id is None:
            labels.raw_labels["error"] = "image_id_not_found"
            return labels

        cache = CocotextParser._annotations_cache
        if cache is None:
            return labels

        # Get image metadata
        imgs = cache.get("imgs", {})
        img_id_str = str(img_id)
        if img_id_str in imgs:
            img_info = imgs[img_id_str]
            labels.raw_labels["split"] = img_info.get("set", "unknown")
            labels.raw_labels["image_width"] = img_info.get("width")
            labels.raw_labels["image_height"] = img_info.get("height")

        # Get annotations for this image
        img_to_anns = cache.get("imgToAnns", {})
        ann_ids = img_to_anns.get(img_id_str, [])

        if not ann_ids:
            # No text in this image
            labels.raw_labels["text_count"] = 0
            labels.raw_labels["has_text"] = False
            return labels

        # Extract annotations
        anns = cache.get("anns", {})
        text_instances: list[dict[str, Any]] = []
        languages: set[str] = set()
        has_handwriting = False
        illegible_count = 0
        total_chars = 0

        for ann_id in ann_ids:
            ann_id_str = str(ann_id)
            if ann_id_str not in anns:
                continue

            ann = anns[ann_id_str]

            # Build text instance
            instance: dict[str, Any] = {
                "bbox": ann.get("bbox"),  # [x, y, width, height]
                "text": ann.get("utf8_string", ""),
                "language": ann.get("language", "na"),
                "text_class": ann.get("class", ""),
                "legibility": ann.get("legibility", ""),
                "area": ann.get("area"),
            }

            text_instances.append(instance)

            # Track statistics
            lang = ann.get("language", "na")
            languages.add(lang)

            if ann.get("class") == "handwritten":
                has_handwriting = True

            if ann.get("legibility") == "illegible":
                illegible_count += 1

            text = ann.get("utf8_string", "")
            if text:
                total_chars += len(text)

        # Set text_instances in labels
        labels.text_instances = text_instances

        # Set language (use most common, prioritizing "english")
        if "english" in languages:
            labels.language_code = "en"
        elif "not_english" in languages:
            labels.language_code = "und"
        else:
            labels.language_code = None

        # Populate raw_labels with statistics
        labels.raw_labels["text_count"] = len(text_instances)
        labels.raw_labels["has_text"] = len(text_instances) > 0
        labels.raw_labels["has_handwriting"] = has_handwriting
        labels.raw_labels["has_scene_text"] = True  # COCO-Text is scene text
        labels.raw_labels["illegible_count"] = illegible_count
        labels.raw_labels["total_chars"] = total_chars
        labels.raw_labels["languages_present"] = list(languages)

        # Count by class
        machine_printed = sum(
            1 for t in text_instances if t.get("text_class") == "machine printed"
        )
        handwritten = sum(
            1 for t in text_instances if t.get("text_class") == "handwritten"
        )
        labels.raw_labels["machine_printed_count"] = machine_printed
        labels.raw_labels["handwritten_count"] = handwritten

        return labels

    def supports_batch(self) -> bool:
        """COCO-Text benefits from batch processing due to shared JSON file."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images efficiently.

        Loads annotations once and processes all images.

        Args:
            dataset_path (Path): Root path of the dataset
            image_paths (list[Path]): List of absolute paths to image files
            config (dict[str, Any]): Dataset configuration dictionary

        Returns:
            list[OriginalLabels]: List of OriginalLabels in same order as image_paths
        """
        # Ensure annotations are loaded
        self._load_annotations(dataset_path)

        # Process each image
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["CocotextParser"]
