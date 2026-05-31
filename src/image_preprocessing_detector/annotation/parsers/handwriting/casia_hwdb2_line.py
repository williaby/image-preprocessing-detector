"""Parser for CASIA-HWDB2-line Chinese handwriting line dataset (Teklia HF edition).

CASIA-HWDB2-line is a line-level extraction from CASIA HWDB2 full-page handwriting
scans. The Teklia HuggingFace edition provides 52,160 Chinese handwriting line images
(height=128px, variable width) with ground-truth text transcriptions.

After downloading via HuggingFace CLI, the Parquet files must be materialized to
individual JPEG images. During materialization, a sidecar index file is written:
    {split}_index.jsonl  — one JSON object per line with keys:
        filename: str  (relative path under images/{split}/)
        text: str      (Chinese transcription, 1-50 chars)

Dataset Structure (after materialization):
    casia-hwdb2-line/
        data/
            train.parquet       -- HF download (raw Parquet)
            validation.parquet
            test.parquet
        images/
            train/              -- materialized JPEG files
                00000001.jpg
                ...
            validation/
                ...
            test/
                ...
        train_index.jsonl       -- sidecar metadata index
        validation_index.jsonl
        test_index.jsonl

Labels Extracted:
    - transcription: Chinese text string (UTF-8, 1-50 characters)
    - language_code: "zh"
    - script_name: "Hans"
    - iso15924_script_code: "Hans"
    - raw_labels: {"split": "train|validation|test", "char_count": N}

Materialization:
    Run `scripts/materialize_casia_hwdb2_line.py` to extract images from Parquet
    and generate sidecar index files before running this parser.

Example:
    >>> parser = CasiaHwdb2LineParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../casia-hwdb2-line"),
    ...     image_path=Path("/mnt/e/.../casia-hwdb2-line/images/train/00000001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.transcription)
    '2007年高校招生录取工作即将陆续展开'
    >>> print(labels.iso15924_script_code)
    'Hans'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "casia-hwdb2-line"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "casia-hwdb2-line_metadata.json"
__l4_integrate__ = "scripts/integrate_casia_hwdb2_line_enrichments.py"


import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Valid split directory names
_VALID_SPLITS = frozenset({"train", "validation", "test"})


class CasiaHwdb2LineParser(BaseParser):
    """Parser for CASIA-HWDB2-line Chinese handwriting line dataset (Teklia HF edition).

    Reads transcription labels from sidecar JSONL index files produced
    by the materialization script. Each image file maps to one line in
    the split's index file.

    Script metadata (Hans, zho, ISO 15924 Hans) is always set — all
    images in this dataset are Chinese simplified handwriting.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["casia-hwdb2-line", "casia_hwdb2_line", "hwdb2-line"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse CASIA-HWDB2-line labels for a single line image.

        Args:
            dataset_path (Path): Root path of the casia-hwdb2-line dataset.
            image_path (Path): Absolute path to a materialized JPEG line image.
            config (dict[str, Any]): Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels: OriginalLabels with Chinese transcription and Hans script metadata.
        """
        labels = OriginalLabels()

        # Set Chinese handwriting script metadata (constant for this dataset)
        labels.language_code = "zh"
        labels.script_name = "Hans"
        labels.iso15924_script_code = "Hans"

        # Determine split from parent directory name
        split = self._detect_split(image_path)

        labels.raw_labels = {
            "dataset": "casia-hwdb2-line",
            "split": split,
            "production": "handwritten",
            "writing_system": "simplified-chinese",
        }

        # Load transcription from sidecar index
        transcription = self._lookup_transcription(dataset_path, image_path, split)
        if transcription:
            labels.transcription = transcription
            if labels.raw_labels is not None:
                labels.raw_labels["char_count"] = len(transcription)
        else:
            logger.debug(
                "No transcription found for %s (index may not be materialized)",
                image_path.name,
            )

        return labels

    def _detect_split(self, image_path: Path) -> str:
        """Detect split name from the image path parent directory.

        Args:
            image_path (Path): Path to the image file.

        Returns:
            str: Split name ("train", "validation", "test") or "unknown".
        """
        for part in reversed(image_path.parts):
            if part in _VALID_SPLITS:
                return part
        return "unknown"

    def _lookup_transcription(
        self,
        dataset_path: Path,
        image_path: Path,
        split: str,
    ) -> str | None:
        """Look up transcription from sidecar JSONL index.

        The index file is loaded once and cached by (dataset_path, split).

        Args:
            dataset_path (Path): Root path of the dataset.
            image_path (Path): Path to the image file.
            split (str): Split name (train/validation/test).

        Returns:
            str | None: Chinese transcription string, or None if not found.
        """
        index = _load_index(dataset_path, split)
        if index is None:
            return None
        filename = image_path.name
        return index.get(filename)


@lru_cache(maxsize=8)
def _load_index(dataset_path: Path, split: str) -> dict[str, str] | None:
    """Load and cache a split's JSONL transcription index.

    Cached per (dataset_path, split) pair — loaded once per process.

    Args:
        dataset_path (Path): Root path of the dataset.
        split (str): Split name (train/validation/test).

    Returns:
        dict[str, str] | None: Dict mapping filename → transcription string, or None if index
        file does not exist.
    """
    index_path = dataset_path / f"{split}_index.jsonl"
    if not index_path.exists():
        logger.warning(
            "CASIA-HWDB2-line index not found: %s — run "
            "scripts/materialize_casia_hwdb2_line.py first",
            index_path,
        )
        return None

    index: dict[str, str] = {}
    try:
        with index_path.open("r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    filename = record.get("filename", "")
                    text = record.get("text", "")
                    if filename and text:
                        index[filename] = text
                except json.JSONDecodeError:
                    logger.debug(
                        "Skipping malformed line %d in %s", line_num, index_path
                    )
    except OSError as exc:
        logger.error("Failed to read index %s: %s", index_path, exc)  # noqa: TRY400
        return None

    logger.debug("Loaded %d transcriptions from %s", len(index), index_path)
    return index
