# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
r"""Parser for im2latex-100k formula dataset.

im2latex-100k provides rendered LaTeX formulas from ArXiv papers with
corresponding LaTeX source code. Each formula image is paired with its
original LaTeX markup.

Dataset Structure:
    im2latex-100k/
        formula_images/
            train/
                0.png
                1.png
                ...
            validate/
            test/
        im2latex_formulas.lst      # LaTeX source (one formula per line, indexed)
        im2latex_train.lst         # Train split: image_id formula_id
        im2latex_validate.lst      # Validation split: image_id formula_id
        im2latex_test.lst          # Test split: image_id formula_id

Alternative Structure (common variant):
    im2latex/
        images/
            0.png, 1.png, ...
        im2latex_formulas.lst
        im2latex_train.lst
        im2latex_validate.lst
        im2latex_test.lst

Annotation Format:
    im2latex_formulas.lst:
        Line N: LaTeX formula code (indexed by line number 0..N-1)
        Example: \\alpha + \\beta = \\gamma

    im2latex_{split}.lst:
        image_id formula_id
        Example: 0 42  (image 0.png uses formula at line 42)

Labels Extracted:
    - latex_source: Full LaTeX formula code
    - formula_id: Index into formulas list
    - split: train/validate/test
    - sequence_length: Character count of LaTeX source
    - symbol_count: Approximate LaTeX symbol count

Dataset Statistics:
    - 103,556 formula images
    - Train: 83,883 (81%)
    - Validate: 9,319 (9%)
    - Test: 10,354 (10%)
    - Formula length: 38-997 characters

Example:
    >>> parser = Im2latexParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/im2latex"),
    ...     image_path=Path("/data/im2latex/images/42.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["latex_source"])
    '\\\\alpha + \\\\beta = \\\\gamma'
    >>> print(labels.raw_labels["split"])
    'train'
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, ClassVar

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class Im2latexParser(BaseParser):
    """Parser for im2latex-100k LaTeX formula dataset.

    Extracts LaTeX source code and split membership from dataset files:
    - LaTeX formula source code from formulas.lst
    - Train/validate/test split from split files
    - Formula complexity metrics (length, symbol count)

    Caches formulas and splits at class level for efficient batch processing.
    """

    # Class-level caches (shared across instances)
    _formulas_cache: ClassVar[dict[int, str] | None] = None
    _splits_cache: ClassVar[dict[int, tuple[str, int]] | None] = None
    _cache_path: ClassVar[Path | None] = None

    # Regex for counting LaTeX symbols (commands like \alpha, \frac, etc.)
    LATEX_COMMAND_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\\[a-zA-Z]+")

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["im2latex", "im2latex-100k", "im2latex_100k"]

    def _load_formulas(self, dataset_path: Path) -> dict[int, str]:
        """Load LaTeX formulas from im2latex_formulas.lst.

        Args:
            dataset_path: Root path of the im2latex dataset

        Returns:
            Dict mapping formula_id (line number) to LaTeX source
        """
        if (
            Im2latexParser._formulas_cache is not None
            and Im2latexParser._cache_path == dataset_path
        ):
            return Im2latexParser._formulas_cache

        formulas: dict[int, str] = {}

        # Try different possible locations for formulas file
        formula_paths = [
            dataset_path / "im2latex_formulas.lst",
            dataset_path / "formulas.lst",
            dataset_path / "formula_images" / "im2latex_formulas.lst",
        ]

        formula_file = None
        for path in formula_paths:
            if path.exists():
                formula_file = path
                break

        if formula_file is None:
            logger.warning(f"Formula file not found in {dataset_path}")
            return formulas

        try:
            logger.debug(f"Loading formulas from {formula_file}")
            with open(formula_file, encoding="utf-8", errors="replace") as f:
                for formula_id, line in enumerate(f):
                    # Store formula without trailing newline
                    formulas[formula_id] = line.rstrip("\n\r")

            logger.debug(f"Loaded {len(formulas)} formulas")
        except Exception as e:
            logger.warning(f"Failed to load formulas: {e}")

        return formulas

    def _load_splits(self, dataset_path: Path) -> dict[int, tuple[str, int]]:
        """Load image→formula mappings from split files.

        Args:
            dataset_path: Root path of the im2latex dataset

        Returns:
            Dict mapping image_id to (split_name, formula_id)
        """
        if (
            Im2latexParser._splits_cache is not None
            and Im2latexParser._cache_path == dataset_path
        ):
            return Im2latexParser._splits_cache

        splits: dict[int, tuple[str, int]] = {}

        for split_name in ["train", "validate", "test"]:
            # Try different possible locations
            split_paths = [
                dataset_path / f"im2latex_{split_name}.lst",
                dataset_path / f"{split_name}.lst",
                dataset_path / "formula_images" / f"im2latex_{split_name}.lst",
            ]

            split_file = None
            for path in split_paths:
                if path.exists():
                    split_file = path
                    break

            if split_file is None:
                continue

            try:
                with open(split_file, encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            try:
                                image_id = int(parts[0])
                                formula_id = int(parts[1])
                                splits[image_id] = (split_name, formula_id)
                            except ValueError:
                                continue

                logger.debug(f"Loaded {split_name} split with entries for images")
            except Exception as e:
                logger.debug(f"Failed to load {split_name} split: {e}")

        return splits

    def _ensure_caches(self, dataset_path: Path) -> None:
        """Ensure caches are loaded for the given dataset path.

        Args:
            dataset_path: Root path of the im2latex dataset
        """
        if Im2latexParser._cache_path != dataset_path:
            # Clear caches for new dataset path
            Im2latexParser._formulas_cache = None
            Im2latexParser._splits_cache = None

        if Im2latexParser._formulas_cache is None:
            Im2latexParser._formulas_cache = self._load_formulas(dataset_path)

        if Im2latexParser._splits_cache is None:
            Im2latexParser._splits_cache = self._load_splits(dataset_path)

        Im2latexParser._cache_path = dataset_path

    def _count_latex_symbols(self, latex: str) -> int:
        r"""Count LaTeX commands/symbols in formula.

        Args:
            latex: LaTeX source code

        Returns:
            Count of LaTeX commands (e.g., \\alpha, \\frac)
        """
        return len(self.LATEX_COMMAND_PATTERN.findall(latex))

    def _extract_image_id(self, image_path: Path) -> int | None:
        """Extract numeric image ID from filename.

        Args:
            image_path: Path to the image file

        Returns:
            Image ID as integer, or None if extraction fails
        """
        stem = image_path.stem

        # Try direct numeric conversion (e.g., "42.png" -> 42)
        try:
            return int(stem)
        except ValueError:
            pass

        # Try extracting trailing number (e.g., "formula_42.png" -> 42)
        match = re.search(r"(\d+)$", stem)
        if match:
            return int(match.group(1))

        return None

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse im2latex labels for an image.

        Extracts LaTeX source code and split membership.

        Args:
            dataset_path: Root path of the im2latex dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with raw_labels containing:
                - latex_source: Full LaTeX formula code
                - formula_id: Index into formulas list
                - split: train/validate/test
                - sequence_length: Character count of LaTeX
                - symbol_count: Count of LaTeX commands
                - content_type: "formula"
                - is_synthetic: True (born-digital rendered)
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Always set these flags for im2latex
        labels.raw_labels["content_type"] = "formula"
        labels.raw_labels["is_synthetic"] = True

        # Load caches
        self._ensure_caches(dataset_path)

        # Extract image ID from filename
        image_id = self._extract_image_id(image_path)
        if image_id is None:
            logger.debug(f"Could not extract image ID from {image_path}")
            labels.raw_labels["error"] = "image_id_not_extracted"
            return labels

        labels.raw_labels["image_id"] = image_id

        # Look up split and formula ID
        splits = Im2latexParser._splits_cache or {}
        formulas = Im2latexParser._formulas_cache or {}

        if image_id in splits:
            split_name, formula_id = splits[image_id]
            labels.raw_labels["split"] = split_name
            labels.raw_labels["formula_id"] = formula_id

            # Get LaTeX source
            if formula_id in formulas:
                latex_source = formulas[formula_id]
                labels.raw_labels["latex_source"] = latex_source
                labels.raw_labels["sequence_length"] = len(latex_source)
                labels.raw_labels["symbol_count"] = self._count_latex_symbols(
                    latex_source
                )

                # Estimate formula complexity (rough heuristic)
                # Simple: <50 chars, Medium: 50-200 chars, Complex: >200 chars
                if len(latex_source) < 50:
                    complexity = "simple"
                elif len(latex_source) < 200:
                    complexity = "medium"
                else:
                    complexity = "complex"
                labels.raw_labels["complexity"] = complexity
        else:
            # Image not found in any split file
            # Try to get formula directly if image_id matches formula_id
            if image_id in formulas:
                latex_source = formulas[image_id]
                labels.raw_labels["latex_source"] = latex_source
                labels.raw_labels["formula_id"] = image_id
                labels.raw_labels["sequence_length"] = len(latex_source)
                labels.raw_labels["symbol_count"] = self._count_latex_symbols(
                    latex_source
                )
                labels.raw_labels["split"] = "unknown"
            else:
                labels.raw_labels["error"] = "image_not_in_splits"

        return labels

    def supports_batch(self) -> bool:
        """im2latex benefits from batch processing due to shared formula file."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images efficiently.

        Loads formulas and splits once, then processes all images.

        Args:
            dataset_path: Root path of the dataset
            image_paths: List of absolute paths to image files
            config: Dataset configuration dictionary

        Returns:
            List of OriginalLabels in same order as image_paths
        """
        # Ensure caches are loaded
        self._ensure_caches(dataset_path)

        # Process each image
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["Im2latexParser"]
