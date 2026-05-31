"""Parser for FUNSD+ (Extended FUNSD) form understanding dataset.

FUNSD+ is an extended version of FUNSD with additional samples, using
the same annotation format and structure.

Dataset Structure:
    FUNSD+/
        annotations/
            *.json
        images/
            *.png

FUNSD+ Annotation Format (dict/object, same as FUNSD - P0-4 fix):
    {
        "form": [
            {
                "text": "Entity text",
                "box": [x1, y1, x2, y2],
                "label": "question|answer|header|other",
                "linking": [[entity_id1, entity_id2], ...],
                "words": [
                    {"text": "word", "box": [x1, y1, x2, y2]}
                ]
            }
        ]
    }

Labels (same as FUNSD):
    - question: Form field questions
    - answer: Form field answers
    - header: Form headers
    - other: Other text elements

Example:
    >>> parser = FunsdPlusParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/funsd_plus"),
    ...     image_path=Path("/data/funsd_plus/images/form001.png"),
    ...     config={},
    ... )
    >>> print(labels.funsd_annotations["form"][0]["label"])
    answer
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "funsd-plus"
__l4_workstream__ = "WS3"
__l4_task__ = "layout"
__l4_l2_file__ = "funsd_plus_metadata.json"
__l4_integrate__ = "scripts/integrate_funsd_plus_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class FunsdPlusParser(BaseParser):
    """Parser for FUNSD+ (Extended FUNSD) form understanding dataset.

    Extracts form entity annotations using the same format as FUNSD.
    FUNSD+ provides additional form samples beyond the original FUNSD dataset.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["funsd_plus", "funsd+"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse FUNSD+ form annotations.

        Args:
            dataset_path (Path): Root path of the FUNSD+ dataset
            image_path (Path): Absolute path to the image file being processed
            config (dict[str, Any]): Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels: OriginalLabels with funsd_annotations (dict) and raw_labels populated

        """
        labels = OriginalLabels()

        # Same annotation format as FUNSD
        json_paths = [
            image_path.with_suffix(".json"),
            dataset_path / "annotations" / f"{image_path.stem}.json",
        ]

        for json_path in json_paths:
            if json_path.exists():
                try:
                    with open(json_path) as f:
                        labels.funsd_annotations = json.load(f)
                    break
                except Exception as e:
                    logger.debug(
                        f"Failed to parse FUNSD+ annotations from {json_path}: {e}"
                    )

        # Even without annotations, we know it's a form dataset (Tier 0)
        if labels.raw_labels is None:
            labels.raw_labels = {}
        labels.raw_labels["document_type"] = "form"
        labels.raw_labels["is_scanned"] = True

        return labels


__all__ = ["FunsdPlusParser"]
