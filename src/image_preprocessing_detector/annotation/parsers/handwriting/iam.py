# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for IAM Handwriting Database.

IAM Handwriting Database contains English handwritten text with multi-level
annotations: forms, lines, words, and character components.

Dataset Structure:
    iam_handwriting/
        *.png              - Form/line/word images (130,212 total)
        xml/*.xml          - Form-level annotations with word bboxes
        ascii/forms.txt    - Form-level metadata (writer IDs)
        ascii/lines.txt    - Line-level transcriptions and bboxes
        ascii/words.txt    - Word-level transcriptions and bboxes

XML Format:
    <form id="a01-000u" writer-id="000" ...>
        <handwritten-part>
            <line id="a01-000u-00" text="A MOVE to stop..." ...>
                <word id="a01-000u-00-00" text="A" tag="AT">
                    <cmp x="408" y="768" width="27" height="51" />
                </word>
            </line>
        </handwritten-part>
    </form>

TXT Format (lines.txt):
    a01-000u-00 ok 154 19 408 746 1661 89 A|MOVE|to|stop|Mr.|Gaitskell|from

TXT Format (words.txt):
    a01-000u-00-00 ok 154 408 768 27 51 AT A

Labels:
    - writer_id: Writer identifier (000-656)
    - text_content: Full transcription from XML/TXT
    - segmentation_ok: Whether segmentation is correct
    - bboxes: Word-level bounding boxes (XYWH format)
    - grammatical_tags: Part-of-speech tags

Example:
    >>> parser = IAMParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/iam_handwriting"),
    ...     image_path=Path("/data/iam_handwriting/a01-000u.png"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'en'
    >>> print(labels.provenance["writer_id"])
    '000'
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET  # noqa: N817

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class IAMParser(BaseParser):
    """Parser for IAM Handwriting Database.

    Extracts handwriting annotations from XML and TXT files:
    - Writer IDs from forms.txt
    - Word-level bounding boxes from XML
    - Line-level transcriptions from lines.txt
    - Word-level transcriptions from words.txt
    - Grammatical tags (POS tags)
    """

    def __init__(self) -> None:
        """Initialize IAM parser with cached annotation data."""
        super().__init__()
        self._forms_cache: dict[str, dict[str, str]] = {}
        self._lines_cache: dict[str, dict[str, Any]] = {}
        self._words_cache: dict[str, dict[str, Any]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["iam", "iam_handwriting", "iam-handwriting"]

    def _load_forms_txt(self, dataset_path: Path) -> None:
        """Load forms.txt metadata into cache.

        Format: a01-000u 000 2 prt 7 5 52 36
        Fields: form_id writer_id num_sentences seg_quality ...
        """
        if self._forms_cache:
            return

        forms_txt = dataset_path / "ascii" / "forms.txt"
        if not forms_txt.exists():
            logger.warning(f"forms.txt not found at {forms_txt}")
            return

        try:
            with open(forms_txt, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 8:
                        form_id = parts[0]
                        self._forms_cache[form_id] = {
                            "writer_id": parts[1],
                            "num_sentences": parts[2],
                            "seg_quality": parts[3],
                            "total_lines": parts[4],
                            "seg_lines": parts[5],
                            "total_words": parts[6],
                            "seg_words": parts[7],
                        }
        except Exception as e:
            logger.warning(f"Failed to load forms.txt: {e}")

    def _load_lines_txt(self, dataset_path: Path) -> None:
        """Load lines.txt metadata into cache.

        Format: a01-000u-00 ok 154 19 408 746 1663 91 A|MOVE|to|stop...
        Fields: line_id status gray_level num_components x y w h transcription
        """
        if self._lines_cache:
            return

        lines_txt = dataset_path / "ascii" / "lines.txt"
        if not lines_txt.exists():
            logger.warning(f"lines.txt not found at {lines_txt}")
            return

        try:
            with open(lines_txt, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 9:
                        line_id = parts[0]
                        # Transcription is everything after the bbox
                        transcription = " ".join(parts[8:])
                        # Convert pipe-separated words to spaces
                        transcription = transcription.replace("|", " ")

                        self._lines_cache[line_id] = {
                            "status": parts[1],
                            "gray_level": parts[2],
                            "num_components": parts[3],
                            "bbox": [
                                int(parts[4]),
                                int(parts[5]),
                                int(parts[6]),
                                int(parts[7]),
                            ],
                            "transcription": transcription,
                        }
        except Exception as e:
            logger.warning(f"Failed to load lines.txt: {e}")

    def _load_words_txt(self, dataset_path: Path) -> None:
        """Load words.txt metadata into cache.

        Format: a01-000u-00-00 ok 154 408 768 27 51 AT A
        Fields: word_id status gray_level x y w h tag transcription
        """
        if self._words_cache:
            return

        words_txt = dataset_path / "ascii" / "words.txt"
        if not words_txt.exists():
            logger.warning(f"words.txt not found at {words_txt}")
            return

        try:
            with open(words_txt, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 9:
                        word_id = parts[0]
                        self._words_cache[word_id] = {
                            "status": parts[1],
                            "gray_level": parts[2],
                            "bbox": [
                                int(parts[3]),
                                int(parts[4]),
                                int(parts[5]),
                                int(parts[6]),
                            ],
                            "tag": parts[7],
                            "transcription": " ".join(parts[8:]),
                        }
        except Exception as e:
            logger.warning(f"Failed to load words.txt: {e}")

    def _parse_xml(self, xml_path: Path) -> dict[str, Any]:
        """Parse form XML file for word-level annotations.

        Returns dict with:
            - writer_id: From XML attribute
            - lines: List of line dicts with words and transcriptions
            - full_text: Complete transcription
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            result: dict[str, Any] = {
                "writer_id": root.get("writer-id", "unknown"),
                "form_id": root.get("id", "unknown"),
                "lines": [],
                "full_text": "",
            }

            # Find handwritten-part
            handwritten_part = root.find("handwritten-part")
            if handwritten_part is None:
                return result

            # Extract all lines
            for line_elem in handwritten_part.findall("line"):
                words: list[dict[str, Any]] = []
                line_data: dict[str, Any] = {
                    "line_id": line_elem.get("id", ""),
                    "text": line_elem.get("text", ""),
                    "segmentation": line_elem.get("segmentation", "unknown"),
                    "words": words,
                }

                # Extract all words
                for word_elem in line_elem.findall("word"):
                    components: list[list[int]] = []
                    word_data: dict[str, Any] = {
                        "word_id": word_elem.get("id", ""),
                        "text": word_elem.get("text", ""),
                        "tag": word_elem.get("tag", ""),
                        "components": components,
                    }

                    # Extract component bboxes
                    for cmp_elem in word_elem.findall("cmp"):
                        bbox = [
                            int(cmp_elem.get("x", "0")),
                            int(cmp_elem.get("y", "0")),
                            int(cmp_elem.get("width", "0")),
                            int(cmp_elem.get("height", "0")),
                        ]
                        components.append(bbox)

                    words.append(word_data)

                result["lines"].append(line_data)
                if line_data["text"]:
                    if result["full_text"]:
                        result["full_text"] += " "
                    result["full_text"] += line_data["text"]

            return result

        except Exception as e:
            logger.debug(f"Failed to parse XML {xml_path}: {e}")
            return {
                "writer_id": "unknown",
                "form_id": "unknown",
                "lines": [],
                "full_text": "",
            }

    def _get_image_level(self, image_path: Path) -> str:
        """Determine annotation level from image filename.

        Returns: "form", "line", or "word"
        """
        stem = image_path.stem

        # Forms: a01-000u (2 parts)
        # Lines: a01-000u-00 (3 parts)
        # Words: a01-000u-00-00 (4 parts)
        parts = stem.split("-")
        if len(parts) == 2:
            return "form"
        if len(parts) == 3:
            return "line"
        if len(parts) >= 4:
            return "word"
        return "unknown"

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse IAM Handwriting labels from XML and TXT files.

        Args:
            dataset_path: Root path of the IAM dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, provenance,
            text_content, and raw_labels containing handwriting annotations
        """
        labels = OriginalLabels()

        # Set language/script for English handwriting
        labels.language_code = "en"
        labels.script_name = "Latin"

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Load annotation caches
        self._load_forms_txt(dataset_path)
        self._load_lines_txt(dataset_path)
        self._load_words_txt(dataset_path)

        # Determine annotation level
        level = self._get_image_level(image_path)
        labels.raw_labels["annotation_level"] = level

        # Extract base identifiers
        stem = image_path.stem
        form_id = "-".join(stem.split("-")[:2])  # e.g., "a01-000u"

        # Get writer ID from forms.txt
        if form_id in self._forms_cache:
            labels.writer_id = self._forms_cache[form_id]["writer_id"]
            labels.raw_labels.update(self._forms_cache[form_id])

        # Parse based on annotation level
        if level == "form":
            # Try to parse XML for form-level annotations
            xml_path = dataset_path / "xml" / f"{stem}.xml"
            if xml_path.exists():
                xml_data = self._parse_xml(xml_path)
                labels.raw_labels["xml_data"] = xml_data

                # Extract text content from XML
                if xml_data["full_text"]:
                    labels.transcription = xml_data["full_text"]
                    labels.raw_labels["text_source"] = "xml_word_attributes"

                    # Extract word-level bboxes for layout_detections
                    word_bboxes = []
                    for line in xml_data["lines"]:
                        for word in line["words"]:
                            if word["components"]:
                                # Aggregate component bboxes to word-level bbox
                                min_x = min(c[0] for c in word["components"])
                                min_y = min(c[1] for c in word["components"])
                                max_x = max(c[0] + c[2] for c in word["components"])
                                max_y = max(c[1] + c[3] for c in word["components"])
                                word_bbox = [
                                    min_x,
                                    min_y,
                                    max_x - min_x,
                                    max_y - min_y,
                                ]
                                word_bboxes.append(
                                    {
                                        "bbox": word_bbox,
                                        "label": "word",
                                        "text": word["text"],
                                        "tag": word["tag"],
                                    }
                                )

                    if word_bboxes:
                        labels.raw_labels["word_bboxes"] = word_bboxes

        elif level == "line":
            # Look up line in lines.txt
            line_id = stem
            if line_id in self._lines_cache:
                line_data = self._lines_cache[line_id]
                labels.raw_labels["line_data"] = line_data

                # Extract text content
                if line_data["transcription"]:
                    labels.transcription = line_data["transcription"]
                    labels.raw_labels["text_source"] = "lines_txt"

                # Store segmentation quality
                labels.raw_labels["segmentation_ok"] = line_data["status"] == "ok"

        elif level == "word":
            # Look up word in words.txt
            word_id = stem
            if word_id in self._words_cache:
                word_data = self._words_cache[word_id]
                labels.raw_labels["word_data"] = word_data

                # Extract text content
                if word_data["transcription"]:
                    labels.transcription = word_data["transcription"]
                    labels.raw_labels["text_source"] = "words_txt"

                # Store grammatical tag and segmentation quality
                labels.raw_labels["grammatical_tag"] = word_data["tag"]
                labels.raw_labels["segmentation_ok"] = word_data["status"] == "ok"

        return labels


__all__ = ["IAMParser"]
