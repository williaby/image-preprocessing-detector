"""Parser for SALAMI legibility assessment dataset.

SALAMI (Statistical Analysis of Legibility Assessment Maps and Images)
contains 250 manuscript images with pixel-level legibility assessments
from 20 expert annotators. Each image has region-level legibility ratings
and pre-computed mean score maps and uncertainty (std) maps.

Dataset Structure:
    salami/
        salami_1.0/
            images/
                input/              # 250 original manuscript PNGs
                    00_00.png       # {batch}_{idx}.png
                mean_score_maps/    # 250 mean legibility maps
                    00_00.png
                std_maps/           # 250 uncertainty maps
                    00_00.png
            src/
                assessments.json    # 4,811 region-level annotations
                images.json         # 250 image metadata (batch, lang)
                users.json          # 20 expert profiles

Assessment Schema:
    - img_id: "{batch}_{idx}" matching image filename
    - annotations: list of {x, y, width, height, rating}
    - rating: "0-20% readable", "20-40% readable", "40-60% readable",
              "60-80% readable", "80-100% readable"
    - user_id: assessor ID (20 experts)

Languages/Scripts:
    Armenian, Georgian, German, Gothic, Greek, Latin, Ottoman, Slavonic

Labels Extracted:
    - legibility ratings from expert consensus
    - language/script per image
    - mean legibility score from pre-computed maps
    - assessment count and agreement metrics

Example:
    >>> parser = SalamiParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path(".../salami"),
    ...     image_path=Path(".../salami/salami_1.0/images/input/00_00.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["language"])
    'Greek'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "salami"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "salami_metadata.json"
__l4_integrate__ = "scripts/integrate_salami_enrichments.py"

import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Map SALAMI language names to ISO 15924 script codes
_LANG_TO_SCRIPT: dict[str, str] = {
    "Armenian": "Armn",
    "Georgian": "Geor",
    "German": "Latn",
    "Gothic": "Goth",
    "Greek": "Grek",
    "Latin": "Latn",
    "Ottoman": "Arab",
    "Slavonic": "Cyrl",
}

# Map legibility rating strings to numeric scores (0-1 midpoint)
_RATING_TO_SCORE: dict[str, float] = {
    "0-20% readable": 0.1,
    "20-40% readable": 0.3,
    "40-60% readable": 0.5,
    "60-80% readable": 0.7,
    "80-100% readable": 0.9,
}


class SalamiParser(BaseParser):
    """Parser for SALAMI legibility assessment dataset.

    Extracts multi-expert legibility assessments and per-image language
    metadata. Supports batch processing since all annotations are stored
    in shared JSON files.
    """

    def __init__(self) -> None:
        super().__init__()
        self._images_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._assessments_cache: dict[str, dict[str, list[dict[str, Any]]]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["salami"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse SALAMI legibility labels for a single image.

        Args:
            dataset_path (Path): Root path of the SALAMI dataset
            image_path (Path): Path to a PNG in images/input/
            config (dict[str, Any]): Dataset configuration dictionary

        Returns:
            OriginalLabels: OriginalLabels with legibility ratings and script metadata
        """
        labels = OriginalLabels()

        # Initialize raw_labels
        if labels.raw_labels is None:
            labels.raw_labels = {}

        labels.raw_labels["dataset"] = "salami"
        labels.raw_labels["production"] = "handwritten"
        labels.raw_labels["capture_method"] = "scanner_flatbed"

        # Image ID matches filename stem (e.g., "00_00")
        img_id = image_path.stem

        # Load image metadata (language, batch)
        images_index = self._load_images(dataset_path)
        if img_id in images_index:
            img_meta = images_index[img_id]
            lang = img_meta.get("lang", "")
            labels.raw_labels["language"] = lang
            labels.raw_labels["batch"] = img_meta.get("batch")

            # Set script code from language
            script_code = _LANG_TO_SCRIPT.get(lang)
            if script_code:
                labels.iso15924_script_code = script_code
                labels.script_name = lang
        else:
            logger.debug("No image metadata for SALAMI ID: %s", img_id)

        # Load legibility assessments
        assessments_index = self._load_assessments(dataset_path)
        if img_id in assessments_index:
            img_assessments = assessments_index[img_id]
            labels.raw_labels["assessment_count"] = len(img_assessments)

            # Compute mean legibility from all region ratings
            all_scores: list[float] = []
            for assessment in img_assessments:
                for ann in assessment.get("annotations", []):
                    rating = ann.get("rating", "")
                    score = _RATING_TO_SCORE.get(rating)
                    if score is not None:
                        all_scores.append(score)

            if all_scores:
                mean_score = sum(all_scores) / len(all_scores)
                labels.raw_labels["legibility_score"] = round(mean_score, 3)
                labels.raw_labels["legibility_regions"] = len(all_scores)
                labels.raw_labels["legibility_expert_count"] = len(
                    {a.get("user_id") for a in img_assessments}
                )
        else:
            logger.debug("No assessments for SALAMI ID: %s", img_id)

        return labels

    def _load_images(self, dataset_path: Path) -> dict[str, dict[str, Any]]:
        """Load and cache images.json metadata index.

        Args:
            dataset_path (Path): Root of SALAMI dataset

        Returns:
            dict[str, dict[str, Any]]: Dict mapping img_id to metadata (lang, batch)
        """
        cache_key = str(dataset_path)
        if cache_key in self._images_cache:
            return self._images_cache[cache_key]

        json_path = dataset_path / "salami_1.0" / "src" / "images.json"
        index: dict[str, dict[str, Any]] = {}

        if not json_path.exists():
            logger.warning("SALAMI images.json not found: %s", json_path)
            self._images_cache[cache_key] = index
            return index

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                img_id = entry.get("id", "")
                if img_id:
                    index[img_id] = entry
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load SALAMI images.json: %s", exc)

        self._images_cache[cache_key] = index
        logger.debug("Loaded %d SALAMI image entries", len(index))
        return index

    def _load_assessments(self, dataset_path: Path) -> dict[str, list[dict[str, Any]]]:
        """Load and cache assessments.json, grouped by img_id.

        Args:
            dataset_path (Path): Root of SALAMI dataset

        Returns:
            dict[str, list[dict[str, Any]]]: Dict mapping img_id to list of assessment entries
        """
        cache_key = str(dataset_path)
        if cache_key in self._assessments_cache:
            return self._assessments_cache[cache_key]

        json_path = dataset_path / "salami_1.0" / "src" / "assessments.json"
        index: dict[str, list[dict[str, Any]]] = {}

        if not json_path.exists():
            logger.warning("SALAMI assessments.json not found: %s", json_path)
            self._assessments_cache[cache_key] = index
            return index

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                img_id = entry.get("img_id", "")
                if img_id:
                    if img_id not in index:
                        index[img_id] = []
                    index[img_id].append(entry)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load SALAMI assessments.json: %s", exc)

        self._assessments_cache[cache_key] = index
        logger.debug(
            "Loaded %d SALAMI assessment groups for %d images",
            sum(len(v) for v in index.values()),
            len(index),
        )
        return index


__all__ = ["SalamiParser"]
