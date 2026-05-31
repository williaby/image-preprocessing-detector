"""Parser for synth-multiscript-250k dataset.

Synthetically generated multi-script document images covering 27 scripts
with complete Layer 2 metadata. Each image has a co-located JSON metadata
file with language, script, layout detections, and quality information.

Dataset Structure:
    synthetic_multiscript/
        manifest.json
        generation_stats.json
        split_metadata.json
        {Script}/               # 27 script directories (Arab, Latn, Hans, etc.)
            {sample_id}.png     # Image file
            {sample_id}.json    # Metadata file (Layer 2 enriched)

Scripts (27 total):
    Arab, Armn, Beng, Cyrl, Deva, Ethi, Geor, Grek, Gujr, Guru,
    Hans, Hant, Hebr, Jpan, Khmr, Knda, Kore, Laoo, Latn, Mlym,
    Mymr, Orya, Sinh, Taml, Telu, Thai, Tibt

JSON Metadata Structure:
    {
        "sample_id": "uuid",
        "data": {
            "language": {"language_code": "ar", "script_code": "Arab", ...},
            "text_scope": {"estimated_chars": 127, "estimated_words": 22, ...},
            "layout_detections": [{"class_name": "Text", "bbox": [...], ...}],
            "content_flags": {"has_table": false, ...},
            "quality": {"overall_score": 1.0, ...},
            "resolution": {"dpi": 300, ...}
        }
    }

Example:
    >>> parser = SynthMultiscriptParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/synthetic_multiscript"),
    ...     image_path=Path("/data/synthetic_multiscript/Arab/sample.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'ar'
    >>> print(labels.iso15924_script_code)
    'Arab'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "synth-multiscript-v3"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "synth_multiscript_v3_metadata.json"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class SynthMultiscriptParser(BaseParser):
    """Parser for synth-multiscript-250k dataset.

    Reads co-located JSON metadata files for synthetically generated
    multi-script document images. The metadata is already in Layer 2
    enriched format, so parsing is straightforward field mapping.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return [
            "synth-multiscript-250k",
            "synth_multiscript_250k",
            "synthetic_multiscript",
            "synthetic-multiscript",
        ]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse synth-multiscript labels from co-located JSON file.

        Each image has a corresponding .json file with the same name
        containing complete metadata.

        Args:
            dataset_path (Path): Root path of the dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with language_code, script codes, and rich
            metadata in raw_labels including layout detections, text
            statistics, and quality scores.
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Find corresponding JSON metadata file
        json_path = image_path.with_suffix(".json")
        if not json_path.exists():
            # Try metadata registry location as fallback
            logger.debug(f"No JSON metadata found at {json_path}")
            return self._create_fallback_labels(image_path, labels)

        try:
            with open(json_path, encoding="utf-8") as f:
                metadata = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load JSON at {json_path}: {e}")
            return self._create_fallback_labels(image_path, labels)

        # Extract data section
        data = metadata.get("data", {})

        # Language and script information
        language_info = data.get("language", {})
        labels.language_code = language_info.get("language_code")
        labels.iso15924_script_code = language_info.get("script_code")
        labels.script_name = language_info.get("script_family")

        # Store additional language metadata
        labels.raw_labels["bcp47_tag"] = language_info.get("bcp47_tag")
        labels.raw_labels["is_rtl"] = language_info.get("is_rtl", False)
        labels.raw_labels["is_primary"] = language_info.get("is_primary", True)

        # Text statistics
        text_scope = data.get("text_scope", {})
        labels.raw_labels["estimated_chars"] = text_scope.get("estimated_chars")
        labels.raw_labels["estimated_words"] = text_scope.get("estimated_words")
        labels.raw_labels["text_density"] = text_scope.get("density")
        labels.raw_labels["content_type"] = text_scope.get("content_type")

        # Layout detections (COCO format bboxes)
        layout_detections = data.get("layout_detections", [])
        if layout_detections:
            labels.raw_labels["layout_detections"] = layout_detections
            labels.raw_labels["layout_detection_count"] = len(layout_detections)

        # Content flags
        content_flags = data.get("content_flags", {})
        labels.raw_labels["has_table"] = content_flags.get("has_table", False)
        labels.raw_labels["has_formula"] = content_flags.get("has_formula", False)
        labels.raw_labels["has_handwriting"] = content_flags.get(
            "has_handwriting", False
        )
        labels.raw_labels["has_signature"] = content_flags.get("has_signature", False)
        labels.raw_labels["has_figure"] = content_flags.get("has_figure", False)

        # Quality information
        quality = data.get("quality", {})
        labels.raw_labels["quality_score"] = quality.get("overall_score")
        labels.raw_labels["degradations"] = quality.get("degradations", [])

        # Resolution information
        resolution = data.get("resolution", {})
        labels.raw_labels["dpi"] = resolution.get("dpi")
        labels.raw_labels["resolution_category"] = resolution.get("category")
        labels.raw_labels["pixels"] = resolution.get("pixels")

        # Capture method (always synthetic for this dataset)
        capture_method = data.get("capture_method", {})
        labels.raw_labels["capture_method"] = capture_method.get("method", "synthetic")
        labels.raw_labels["is_synthetic"] = True

        # Structure information
        structure = data.get("structure", {})
        labels.raw_labels["layout_type"] = structure.get("layout_type")
        labels.raw_labels["text_density_category"] = structure.get("text_density")

        # Sample identification
        labels.raw_labels["sample_id"] = metadata.get("sample_id")
        labels.raw_labels["enrichment_version"] = metadata.get("enrichment_version")

        return labels

    def _create_fallback_labels(
        self, image_path: Path, labels: OriginalLabels
    ) -> OriginalLabels:
        """Create fallback labels from directory structure when JSON missing.

        Args:
            image_path (Path): Path to the image file
            labels (OriginalLabels): OriginalLabels instance to populate

        Returns:
            OriginalLabels: OriginalLabels with script inferred from directory name
        """
        # Ensure raw_labels is initialized
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Try to infer script from parent directory name
        parent_name = image_path.parent.name

        # ISO 15924 script codes are 4 letters, title case
        if len(parent_name) == 4 and parent_name[0].isupper():
            labels.iso15924_script_code = parent_name
            labels.raw_labels["inferred_from_directory"] = True
            labels.raw_labels["is_synthetic"] = True

        return labels

    def supports_batch(self) -> bool:
        """Batch parsing not optimized - each image has its own JSON."""
        return False


__all__ = ["SynthMultiscriptParser"]
