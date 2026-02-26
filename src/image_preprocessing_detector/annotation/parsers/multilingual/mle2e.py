# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for MLE2E dataset.

MLE2E (Multi-Language End-to-End) is a scene text dataset with
end-to-end text detection and recognition for 4 different scripts.

Dataset Structure:
    mle2e/
        Training/
            *.jpg
            *.txt  (annotation files)
        Testing/
            *.jpg
            *.txt

4 Scripts:
    Latin, Chinese, Kannada, Korean (Hangul)

Annotation Format (per line in .txt):
    x1,y1,x2,y2,script[,transcription]

Extracts:
    - language_code: ISO 639 code based on detected scripts
    - script_name: ISO 15924 script code (primary script)
    - text_instances: Sample text instances from annotations
    - raw_labels: split, scripts (list of all scripts found), iso15924_script

Example:
    >>> parser = Mle2eParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/mle2e"),
    ...     image_path=Path("/data/mle2e/Training/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    zh
    >>> print(labels.text_instances[:2])
    [{"script": "chinese", "text": "你好"}, ...]
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "mle2e"
__l4_workstream__ = "WS3"
__l4_task__ = "multilingual"
__l4_l2_file__ = "mle2e_metadata.json"
__l4_integrate__ = "scripts/integrate_mle2e_enrichments.py"


import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class Mle2eParser(BaseParser):
    """Parser for MLE2E dataset.

    Extracts split information from directory structure and parses
    multi-script text annotations from companion .txt files.
    """

    # Script to ISO mappings (language_code, iso15924_script)
    SCRIPT_MAPPING = {
        "latin": ("en", "Latn"),
        "chinese": ("zh", "Hans"),
        "kannada": ("kn", "Knda"),
        "korean": ("ko", "Hang"),
    }

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["mle2e"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MLE2E labels from directory and annotation files.

        Args:
            dataset_path: Root path of the MLE2E dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with language_code, script_name, text_instances,
            and split information
        """
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Extract split from path
        path_parts = image_path.parts
        for part in path_parts:
            if part == "Training":
                labels.raw_labels["split"] = "train"
                break
            if part == "Testing":
                labels.raw_labels["split"] = "test"
                break

        # Try to find and parse companion annotation file
        txt_path = image_path.with_suffix(".txt")
        if txt_path.exists():
            try:
                with open(txt_path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    scripts_found: set[str] = set()
                    text_instances: list[dict[str, str]] = []
                    for line in lines:
                        line = line.strip()
                        if line:
                            parts = line.split(",")
                            if len(parts) >= 5:
                                script = parts[4].lower()
                                scripts_found.add(script)
                                if len(parts) >= 6:
                                    text_instances.append(
                                        {
                                            "script": script,
                                            "text": parts[5],
                                        }
                                    )

                    if scripts_found:
                        labels.raw_labels["scripts"] = list(scripts_found)
                        # Set primary script based on first found
                        primary_script = next(iter(scripts_found))
                        if primary_script in self.SCRIPT_MAPPING:
                            lang_code, script_code = self.SCRIPT_MAPPING[primary_script]
                            labels.language_code = lang_code
                            labels.script_name = (
                                primary_script.title()
                            )  # Human-readable
                            labels.iso15924_script_code = script_code  # ISO 15924
                    if text_instances:
                        # Sample first 5 text instances
                        labels.text_instances = text_instances[:5]
            except Exception as e:
                logger.debug(f"Failed to parse MLE2E annotation at {txt_path}: {e}")

        return labels


__all__ = ["Mle2eParser"]
