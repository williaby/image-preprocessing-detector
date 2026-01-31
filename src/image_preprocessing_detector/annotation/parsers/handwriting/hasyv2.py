# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for HASYv2 (Handwritten Symbol) dataset.

This parser extracts symbol class labels from the HASYv2 CSV files.
The dataset contains 168,233 images of 369 handwritten symbol classes.

Dataset Structure:
    hasyv2_original/
        hasy-data/
            v2-00001.png
            v2-00002.png
            ...
        classification-task/
            fold-1/
                train.csv
                test.csv
            fold-2/
                ...
            ...
            fold-10/

CSV Format:
    path,symbol_id,latex,user_id
    ../../hasy-data/v2-00016.png,31,A,8071
    ...

Labels Extracted:
    - symbol_id: Numeric class ID (1-369)
    - latex: LaTeX representation of the symbol (e.g., 'A', '\\alpha', '\\sum')
    - user_id: Crowdsource contributor ID
    - fold: Which cross-validation fold (1-10)
    - split: train or test within the fold

Reference:
    - Paper: https://arxiv.org/abs/1701.08380
    - Dataset: https://zenodo.org/records/259444

Example:
    >>> parser = HASYv2Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/hasyv2_original"),
    ...     image_path=Path("/data/hasyv2_original/hasy-data/v2-00016.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["symbol_id"])
    31
    >>> print(labels.raw_labels["latex"])
    'A'
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class HASYv2Parser(BaseParser):
    """Parser for HASYv2 handwritten symbol dataset.

    Extracts symbol class labels from CSV files that map image paths
    to symbol IDs and LaTeX representations.
    """

    _label_cache: dict[str, dict[str, Any]] | None = None

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["hasyv2", "hasy-v2", "hasy_v2", "hasyv2_original"]

    def _build_label_cache(self, dataset_path: Path) -> dict[str, dict[str, Any]]:
        """Build a cache mapping image filenames to their labels.

        Args:
            dataset_path: Root path of the HASYv2 dataset

        Returns:
            Dictionary mapping filename (e.g., 'v2-00016.png') to label dict
        """
        if self._label_cache is not None:
            return self._label_cache

        label_cache: dict[str, dict[str, Any]] = {}
        classification_task_path = dataset_path / "classification-task"

        if not classification_task_path.exists():
            logger.warning(
                "HASYv2 classification-task directory not found at %s",
                classification_task_path,
            )
            return label_cache

        # Process all 10 folds
        for fold_num in range(1, 11):
            fold_dir = classification_task_path / f"fold-{fold_num}"
            if not fold_dir.exists():
                continue

            for split in ["train", "test"]:
                csv_path = fold_dir / f"{split}.csv"
                if not csv_path.exists():
                    continue

                try:
                    with open(csv_path, encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Extract filename from path like '../../hasy-data/v2-00016.png'
                            rel_path = row.get("path", "")
                            filename = Path(rel_path).name

                            if filename and filename not in label_cache:
                                label_cache[filename] = {
                                    "symbol_id": int(row.get("symbol_id", 0)),
                                    "latex": row.get("latex", ""),
                                    "user_id": int(row.get("user_id", 0)),
                                    "fold": fold_num,
                                    "split": split,
                                }
                except (OSError, csv.Error) as e:
                    logger.warning("Error reading CSV %s: %s", csv_path, e)

        logger.info("Built HASYv2 label cache with %d entries", len(label_cache))
        self._label_cache = label_cache
        return label_cache

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse HASYv2 labels for an image.

        Args:
            dataset_path: Root path of the HASYv2 dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels containing:
                - symbol_id: Numeric class ID
                - latex: LaTeX symbol representation
                - user_id: Crowdsource contributor ID
                - fold: Cross-validation fold number (1-10)
                - split: 'train' or 'test'
                - content_type: 'mathematical_symbol'
        """
        labels = OriginalLabels()

        # Initialize raw_labels dict
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Build label cache on first call
        label_cache = self._build_label_cache(dataset_path)

        # Look up labels by filename
        filename = image_path.name

        if filename in label_cache:
            cached = label_cache[filename]
            labels.raw_labels["symbol_id"] = cached["symbol_id"]
            labels.raw_labels["latex"] = cached["latex"]
            labels.raw_labels["user_id"] = cached["user_id"]
            labels.raw_labels["fold"] = cached["fold"]
            labels.raw_labels["split"] = cached["split"]
        else:
            logger.debug("No labels found for %s", filename)

        # Always mark as mathematical symbol content
        labels.raw_labels["content_type"] = "mathematical_symbol"

        return labels


__all__ = ["HASYv2Parser"]
