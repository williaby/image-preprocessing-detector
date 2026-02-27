"""Parser for GNHK (GoodNotes Handwriting Knowledge) dataset.

GNHK contains 687 full-page handwritten document images with word-level
polygon annotations. Primarily English handwriting across diverse writing
styles, captured on tablets. Includes both handwritten (type='H') and
printed (type='P') word annotations with text transcriptions.

Dataset Structure:
    gnhk/
        paper/
            train/
                eng_AF_001.jpg      # 515 full-page images
                eng_AF_001.json     # Per-image word annotations
            test/
                eng_AF_004.jpg      # 172 full-page images
                eng_AF_004.json

Filename Convention:
    eng_{writer}_{seq}.jpg
    e.g.: eng_AF_001.jpg
          ^^^ language prefix (always "eng")
              ^^ writer ID
                  ^^^ sequence number

JSON Annotation Format:
    Each JSON file is an array of word-level annotations:
    [
        {
            "text": "word",       # Transcription (or %math%, %SC%, %NA%)
            "polygon": {          # 4-point bounding polygon
                "x0": int, "y0": int,
                "x1": int, "y1": int,
                "x2": int, "y2": int,
                "x3": int, "y3": int
            },
            "line_idx": int,      # Line number
            "type": "H" | "P"    # H=Handwritten, P=Printed
        }
    ]

Special Text Tokens:
    - ``%math%``: Mathematical content (654 occurrences)
    - ``%SC%``: Scribble / illegible (571 occurrences) — key for legibility
    - ``%NA%``: Not applicable / unreadable (466 occurrences)

Labels Extracted:
    - language_code: "en" (English)
    - script_name: "Latin"
    - iso15924_script_code: "Latn"
    - word_count: Total word annotations per image
    - handwritten_word_count: Words with type="H"
    - printed_word_count: Words with type="P"
    - illegible_word_count: Words with %SC% or %NA% text
    - line_count: Max line_idx + 1
    - writer_id: Extracted from filename

Example:
    >>> parser = GNHKParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../handwriting/gnhk"),
    ...     image_path=Path(".../gnhk/paper/train/eng_AF_001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'en'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "gnhk"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "gnhk_metadata.json"
__l4_integrate__ = "scripts/integrate_gnhk_enrichments.py"


import json
import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Filename pattern: eng_AF_001  (lang_writer_seq)
_GNHK_STEM_RE = re.compile(
    r"^eng_(?P<writer_id>[A-Z]{2})_(?P<seq>\d{3})$",
    re.IGNORECASE,
)

# Special text tokens indicating non-standard content
_ILLEGIBLE_TOKENS = frozenset({"%SC%", "%NA%"})


class GNHKParser(BaseParser):
    """Parser for GNHK English handwriting dataset.

    Extracts word-level annotations from per-image JSON files,
    including legibility markers (%SC% for scribble, %NA% for
    unreadable) that are critical for legibility classification.
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["gnhk"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse GNHK labels from companion JSON annotation file.

        Args:
            dataset_path: Root path of the GNHK dataset
            image_path: Absolute path to the JPEG image being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with English text metadata, word counts,
            legibility statistics, and writer identity
        """
        labels = OriginalLabels()

        # Set language/script for English handwriting
        labels.language_code = "en"
        labels.script_name = "Latin"
        labels.iso15924_script_code = "Latn"

        # Initialize raw_labels
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["dataset"] = "gnhk"
        labels.raw_labels["production"] = "handwritten"
        labels.raw_labels["capture_method"] = "camera_smartphone"

        # Parse filename metadata
        stem = image_path.stem
        m = _GNHK_STEM_RE.match(stem)
        if m:
            labels.raw_labels["writer_id"] = m.group("writer_id")
            labels.raw_labels["sequence"] = int(m.group("seq"))

        # Determine split from path
        if "train" in image_path.parts:
            labels.raw_labels["split"] = "train"
        elif "test" in image_path.parts:
            labels.raw_labels["split"] = "test"

        # Load companion JSON
        json_path = image_path.with_suffix(".json")
        if not json_path.exists():
            logger.debug("GNHK JSON annotation not found: %s", json_path)
            return labels

        try:
            with open(json_path, encoding="utf-8") as f:
                words: list[dict[str, Any]] = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load GNHK JSON %s: %s", json_path, exc)
            return labels

        # Count word types
        hw_count = 0
        printed_count = 0
        illegible_count = 0
        math_count = 0
        max_line = 0
        transcriptions: list[str] = []

        for word in words:
            word_type = word.get("type", "")
            text = word.get("text", "")
            line_idx = word.get("line_idx", 0)

            if word_type == "H":
                hw_count += 1
            elif word_type == "P":
                printed_count += 1

            if text in _ILLEGIBLE_TOKENS:
                illegible_count += 1
            elif text == "%math%":
                math_count += 1
            elif text and not text.startswith("%"):
                transcriptions.append(text)

            if line_idx > max_line:
                max_line = line_idx

        labels.raw_labels["word_count"] = len(words)
        labels.raw_labels["handwritten_word_count"] = hw_count
        labels.raw_labels["printed_word_count"] = printed_count
        labels.raw_labels["illegible_word_count"] = illegible_count
        labels.raw_labels["math_word_count"] = math_count
        labels.raw_labels["line_count"] = max_line + 1

        # Store legibility ratio (fraction of illegible words)
        if len(words) > 0:
            labels.raw_labels["illegible_ratio"] = round(
                illegible_count / len(words), 4
            )

        # Store sample transcription (first 5 words)
        if transcriptions:
            labels.raw_labels["text_content"] = {
                "sample_text": " ".join(transcriptions[:5]),
                "source_type": "dataset_provided",
                "source_format": "json_annotation",
                "extraction_method": "GNHKParser.parse",
                "extraction_timestamp": None,
                "is_complete": False,
                "encoding": "utf-8",
            }

        return labels


__all__ = ["GNHKParser"]
