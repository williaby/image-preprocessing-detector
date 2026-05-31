"""Parser for HierText hierarchical text dataset.

HierText is the gold standard for handwriting detection and legibility labels,
providing explicit `handwritten` and `legible` boolean fields at word/line level.

Dataset Structure:
    hiertext/
        gt/
            train.jsonl         # Training annotations (~1GB, 8,281 images)
            validation.jsonl    # Validation annotations (~200MB, 1,724 images)
            test.jsonl          # Test annotations (~200MB, 1,634 images)
        train/                  # Training images (download from S3)
        validation/             # Validation images
        test/                   # Test images

Annotation Format (single JSON object per file, not JSONL despite extension):
    {
        "info": {"date": "...", "version": "v1.0"},
        "annotations": [
            {
                "image_id": "0006289e4f292bcd",
                "paragraphs": [
                    {
                        "vertices": [[x, y], ...],
                        "legible": true,
                        "lines": [
                            {
                                "vertices": [[x, y], ...],
                                "text": "MOZART",
                                "legible": true,
                                "handwritten": false,
                                "vertical": false,
                                "words": [
                                    {
                                        "vertices": [[x, y], ...],
                                        "text": "MOZART",
                                        "legible": true,
                                        "handwritten": false,
                                        "vertical": false
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

Labels Extracted:
    - text_instances: Word-level annotations with polygon, text, attributes
    - language_code: None (multi-language, not labeled per instance)
    - raw_labels: Handwriting/legibility statistics for graded assessment

Handwriting Assessment Derivation:
    - HandwritingPresence: Derived from handwritten_word_count / total_word_count
    - HandwritingLegibility: Derived from illegible_word_count / handwritten_word_count
    - HandwritingContentType: Inferred from word lengths and content patterns

Dataset Statistics:
    - 11,639 images total (8,281 train, 1,724 val, 1,634 test)
    - ~1.2M word-level annotations
    - CC BY-SA 4.0 license (commercial use allowed with attribution)

Example:
    >>> parser = HiertextParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/hiertext"),
    ...     image_path=Path("/data/hiertext/train/0006289e4f292bcd.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["handwritten_word_count"])
    5
    >>> print(labels.raw_labels["handwriting_presence_ratio"])
    0.25
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "hiertext"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "hiertext_metadata.json"
__l4_integrate__ = "scripts/integrate_hiertext_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any, ClassVar

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class HiertextParser(BaseParser):
    """Parser for HierText hierarchical text dataset.

    Extracts word-level text annotations with explicit handwriting and legibility
    labels - the gold standard for graded handwriting assessment training.

    Key features:
    - Word-level `handwritten` boolean for presence classification
    - Word-level `legible` boolean for legibility classification
    - Polygon bounding boxes for accurate element localization
    - Hierarchical structure (paragraph → line → word)

    Caches annotation files at class level for efficient batch processing.
    """

    # Class-level cache for annotation data
    _annotations_cache: ClassVar[dict[str, dict[str, Any]] | None] = None
    _cache_path: ClassVar[Path | None] = None

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["hiertext", "hier-text", "hier_text"]

    def _load_annotations(self, dataset_path: Path) -> bool:
        """Load HierText annotations from JSON files.

        Uses class-level caching to avoid reloading for each image.
        Loads all splits (train, validation, test) into a unified index.

        Args:
            dataset_path (Path): Root path of the HierText dataset

        Returns:
            bool: True if annotations loaded successfully, False otherwise
        """
        # Check if already cached for this path
        if (
            HiertextParser._annotations_cache is not None
            and HiertextParser._cache_path == dataset_path
        ):
            return True

        gt_dir = dataset_path / "gt"
        if not gt_dir.exists():
            logger.warning(f"HierText gt/ directory not found in {dataset_path}")
            return False

        # Build image_id → annotation mapping
        annotations_by_id: dict[str, Any] = {}

        for split in ["train", "validation", "test"]:
            # Try both .jsonl and .json extensions
            for ext in [".jsonl", ".json"]:
                ann_path = gt_dir / f"{split}{ext}"
                if ann_path.exists():
                    try:
                        logger.debug(f"Loading HierText {split} from {ann_path}")
                        with open(ann_path, encoding="utf-8") as f:
                            data = json.load(f)

                        # Index by image_id
                        for ann in data.get("annotations", []):
                            img_id = ann.get("image_id")
                            if img_id:
                                annotations_by_id[img_id] = {
                                    "split": split,
                                    "paragraphs": ann.get("paragraphs", []),
                                }

                        logger.debug(
                            f"Loaded {len(data.get('annotations', []))} "
                            f"annotations from HierText {split}"
                        )
                        break  # Found file, skip other extension
                    except Exception as e:
                        logger.warning(f"Failed to load HierText {split}: {e}")

        if not annotations_by_id:
            logger.warning("No HierText annotations loaded")
            return False

        HiertextParser._annotations_cache = annotations_by_id
        HiertextParser._cache_path = dataset_path

        logger.info(f"Loaded HierText: {len(annotations_by_id)} images indexed")
        return True

    def _get_image_id(self, image_path: Path) -> str | None:
        """Extract HierText image ID from filename.

        HierText uses 16-character hex IDs as filenames.

        Args:
            image_path (Path): Path to the image file

        Returns:
            str | None: Image ID string if valid, None otherwise
        """
        stem = image_path.stem
        # HierText IDs are 16-character hex strings
        if len(stem) == 16 and all(c in "0123456789abcdef" for c in stem.lower()):
            return stem.lower()
        return None

    def _polygon_to_bbox(self, vertices: list[list[int]]) -> list[int]:
        """Convert polygon vertices to COCO-format bounding box.

        Args:
            vertices (list[list[int]]): List of [x, y] coordinate pairs

        Returns:
            list[int]: Bounding box as [x, y, width, height]
        """
        if not vertices:
            return [0, 0, 0, 0]

        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        return [x_min, y_min, x_max - x_min, y_max - y_min]

    def _infer_content_type(self, words: list[dict[str, Any]]) -> str:
        """Infer handwriting content type from word characteristics.

        Categories:
        - signatures_marks: Very short words, likely signatures
        - numeric: All digits
        - alphanumeric: Mixed letters and numbers
        - prose: Longer text content
        - mixed: Multiple types present

        Args:
            words (list[dict[str, Any]]): List of word annotations with text

        Returns:
            str: Content type string
        """
        if not words:
            return "not_applicable"

        handwritten_words = [w for w in words if w.get("handwritten", False)]
        if not handwritten_words:
            return "not_applicable"

        texts = [w.get("text", "") for w in handwritten_words]

        # Count characteristics
        numeric_count = sum(1 for t in texts if t.isdigit())
        short_count = sum(1 for t in texts if len(t) <= 3)
        long_count = sum(1 for t in texts if len(t) > 10)

        total = len(texts)

        # Classification logic
        if short_count > total * 0.8:
            return "signatures_marks"
        if numeric_count > total * 0.8:
            return "numeric"
        if long_count > total * 0.3:
            return "prose"
        if numeric_count > 0 and numeric_count < total:
            return "alphanumeric"
        return "mixed"

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse HierText annotations for an image.

        Extracts word-level annotations with handwriting and legibility labels,
        computing statistics for graded assessment training.

        Args:
            dataset_path (Path): Root path of the HierText dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with text_instances and raw_labels containing
            handwriting/legibility statistics for graded assessment
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
            labels.raw_labels["error"] = "invalid_image_id"
            return labels

        cache = HiertextParser._annotations_cache
        if cache is None or img_id not in cache:
            labels.raw_labels["error"] = "image_not_in_annotations"
            return labels

        ann = cache[img_id]
        labels.raw_labels["split"] = ann.get("split", "unknown")

        # Extract all words from paragraphs
        all_words: list[dict[str, Any]] = []
        text_instances: list[dict[str, Any]] = []

        # Counters for graded assessment
        total_words = 0
        handwritten_words = 0
        legible_words = 0
        illegible_handwritten_words = 0
        total_chars = 0
        handwritten_chars = 0

        for paragraph in ann.get("paragraphs", []):
            para_legible = paragraph.get("legible", True)

            for line in paragraph.get("lines", []):
                line_handwritten = line.get("handwritten", False)
                line_legible = line.get("legible", True)
                line_vertical = line.get("vertical", False)

                for word in line.get("words", []):
                    word_text = word.get("text", "")
                    word_handwritten = word.get("handwritten", line_handwritten)
                    word_legible = word.get("legible", line_legible)
                    word_vertices = word.get("vertices", [])

                    total_words += 1
                    total_chars += len(word_text)

                    if word_handwritten:
                        handwritten_words += 1
                        handwritten_chars += len(word_text)
                        if not word_legible:
                            illegible_handwritten_words += 1

                    if word_legible:
                        legible_words += 1

                    # Build text instance
                    instance: dict[str, Any] = {
                        "bbox": self._polygon_to_bbox(word_vertices),
                        "polygon": word_vertices,
                        "text": word_text,
                        "handwritten": word_handwritten,
                        "legible": word_legible,
                        "vertical": word.get("vertical", line_vertical),
                        "paragraph_legible": para_legible,
                    }
                    text_instances.append(instance)
                    all_words.append(word)

        # Set text_instances
        labels.text_instances = text_instances

        # Populate text_content field for Layer 2 integration
        if text_instances:
            # Aggregate all word text with space separation
            full_text = " ".join(str(inst.get("text", "")) for inst in text_instances)

            # Set text_content in raw_labels
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["text_content"] = {
                "full_text": full_text,
                "source_type": "ground_truth",
                "source_file": str(image_path.name),
                "extraction_method": "HiertextParser.parse",
            }

        # Compute graded assessment statistics
        labels.raw_labels["total_word_count"] = total_words
        labels.raw_labels["handwritten_word_count"] = handwritten_words
        labels.raw_labels["legible_word_count"] = legible_words
        labels.raw_labels["illegible_handwritten_count"] = illegible_handwritten_words
        labels.raw_labels["total_char_count"] = total_chars
        labels.raw_labels["handwritten_char_count"] = handwritten_chars

        # Compute ratios for graded labels
        if total_words > 0:
            presence_ratio = handwritten_words / total_words
            labels.raw_labels["handwriting_presence_ratio"] = round(presence_ratio, 4)
        else:
            labels.raw_labels["handwriting_presence_ratio"] = 0.0

        if handwritten_words > 0:
            legibility_ratio = 1.0 - (illegible_handwritten_words / handwritten_words)
            labels.raw_labels["handwriting_legibility_ratio"] = round(
                legibility_ratio, 4
            )
        else:
            labels.raw_labels["handwriting_legibility_ratio"] = None

        # Binary flags (backward compatible)
        labels.raw_labels["has_handwriting"] = handwritten_words > 0
        labels.raw_labels["has_text"] = total_words > 0

        # Infer content type
        labels.raw_labels["handwriting_content_type"] = self._infer_content_type(
            all_words
        )

        # Derive graded presence category
        presence_ratio = labels.raw_labels["handwriting_presence_ratio"]
        if presence_ratio == 0:
            labels.raw_labels["handwriting_presence_category"] = "NONE"
        elif presence_ratio < 0.1:
            labels.raw_labels["handwriting_presence_category"] = "SPARSE"
        elif presence_ratio < 0.3:
            labels.raw_labels["handwriting_presence_category"] = "MODERATE"
        elif presence_ratio < 0.6:
            labels.raw_labels["handwriting_presence_category"] = "SUBSTANTIAL"
        else:
            labels.raw_labels["handwriting_presence_category"] = "DOMINANT"

        return labels

    def supports_batch(self) -> bool:
        """HierText benefits from batch processing due to shared JSON files."""
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


__all__ = ["HiertextParser"]
