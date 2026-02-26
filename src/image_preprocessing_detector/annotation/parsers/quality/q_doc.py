# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Q-Doc quality assessment benchmark dataset.

Q-Doc is a document quality assessment benchmark that uses multiple VLM
(Vision-Language Model) evaluators. The dataset contains sub-directories
for different VLM model evaluation code and quality score outputs.

Dataset Structure:
    q-doc/
        images/
            {document_id}.png
        code_for_gpt/           # GPT evaluation code and results
        code_for_llama3.2/      # LLaMA 3.2 evaluation code and results
        code_for_gemini/        # Gemini evaluation code and results
        scores/
            quality_scores.json  # Aggregated quality scores
            quality_scores.csv   # Alternative CSV format

Score Files:
    JSON: List of {image_path, quality_score, ...} entries
    CSV: Columns include image_path, quality_score, and model-specific scores

Example:
    >>> parser = QDocParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/q-doc"),
    ...     image_path=Path("/data/q-doc/images/doc_042.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["source"])
    "q-doc"
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "q-doc"
__l4_workstream__ = "WS3"
__l4_task__ = "quality"
__l4_l2_file__ = "q_doc_metadata.json"


import contextlib
import csv
import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Module-level cache for quality scores (load once per file)
_SCORE_CACHE: dict[str, dict[str, Any]] = {}


def _load_quality_scores(score_path: Path) -> dict[str, Any] | None:
    """Load and cache quality score file (JSON or CSV).

    Args:
        score_path: Path to quality score file

    Returns:
        Dict mapping image identifiers to score entries, or None
    """
    cache_key = str(score_path)
    if cache_key in _SCORE_CACHE:
        return _SCORE_CACHE[cache_key]

    if not score_path.exists():
        return None

    try:
        result: dict[str, Any] = {}

        if score_path.suffix == ".json":
            with open(score_path) as f:
                data = json.load(f)
            if isinstance(data, list):
                for entry in data:
                    image_key = entry.get("image_path", entry.get("image", ""))
                    if image_key:
                        # Index by both full path and filename
                        result[image_key] = entry
                        result[Path(image_key).name] = entry
                        result[Path(image_key).stem] = entry
            elif isinstance(data, dict):
                result = data

        elif score_path.suffix == ".csv":
            with open(score_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    image_key = row.get("image_path", row.get("image", ""))
                    if image_key:
                        result[image_key] = dict(row)
                        result[Path(image_key).name] = dict(row)
                        result[Path(image_key).stem] = dict(row)

        if result:
            _SCORE_CACHE[cache_key] = result
            logger.debug(
                f"Loaded quality scores from {score_path}: {len(result)} entries"
            )
            return result

    except Exception as e:
        logger.warning(f"Failed to load quality scores from {score_path}: {e}")

    return None


class QDocParser(BaseParser):
    """Parser for Q-Doc quality assessment benchmark.

    Extracts document quality scores from JSON or CSV score files.
    Supports multiple VLM evaluator outputs. Marks dataset as a
    benchmark for evaluation-only use.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["q-doc"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Q-Doc quality scores.

        Args:
            dataset_path: Root path of the Q-Doc dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with quality assessment metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["source"] = "q-doc"
        labels.raw_labels["task"] = "quality_assessment"
        labels.raw_labels["is_benchmark"] = True

        # Search for quality score files in various locations
        score_paths = [
            dataset_path / "scores" / "quality_scores.json",
            dataset_path / "scores" / "quality_scores.csv",
            dataset_path / "quality_scores.json",
            dataset_path / "quality_scores.csv",
            dataset_path / "scores.json",
            dataset_path / "scores.csv",
        ]

        # Also check for JSON/CSV files in dataset root
        for json_file in dataset_path.glob("*.json"):
            if json_file not in score_paths:
                score_paths.append(json_file)

        scores = None
        for score_path in score_paths:
            scores = _load_quality_scores(score_path)
            if scores:
                labels.raw_labels["score_file"] = str(
                    score_path.relative_to(dataset_path)
                )
                break

        if scores:
            # Look up quality scores for this image
            filename = image_path.name
            stem = image_path.stem

            entry = scores.get(filename) or scores.get(stem)

            if entry:
                # Extract quality score
                quality_score = entry.get(
                    "quality_score", entry.get("score", entry.get("quality"))
                )
                if quality_score is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        labels.raw_labels["quality_score"] = float(quality_score)

                # Store full entry for downstream use
                labels.raw_labels["score_entry"] = entry

        return labels


__all__ = ["QDocParser"]
