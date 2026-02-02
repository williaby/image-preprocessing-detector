# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for OHR-Bench dataset.

OHR-Bench (OCR Hallucination Recognition Benchmark) provides document images
across 16 categories for evaluating OCR hallucination detection. The dataset
is available on HuggingFace as `opendatalab/OHR-Bench` with Arrow metadata containing
quality scores and OCR ground truth.

Dataset Structure (Local):
    ohr_bench/
        {category}/
            *.jpg

HuggingFace Dataset: opendatalab/OHR-Bench
    Arrow format with metadata fields:
    - image_id: Unique identifier
    - category: Document category (16 classes)
    - quality_score: Image quality (0-100 scale, higher=better)
    - ocr_text: Ground truth OCR transcription
    - hallucination_score: OCR hallucination metric (0-100)

16 Document Categories:
    - academic: Research papers and academic documents
    - book: Book pages and chapters
    - exam: Examination papers and tests
    - finance: Financial reports and statements
    - form: Forms and questionnaires
    - handwritten: Handwritten notes and documents
    - legal: Legal documents and contracts
    - magazine: Magazine articles and layouts
    - medical: Medical records and prescriptions
    - newspaper: Newspaper articles and pages
    - note: Notes and memos
    - poster: Posters and flyers
    - receipt: Receipts and invoices
    - research: Research papers and publications
    - resume: Resumes and CVs
    - slide: Presentation slides

Labels Extracted:
    - category: Document category (from filename or Arrow metadata)
    - ohr_quality_score: Quality score 0-100 (from Arrow metadata)
    - quality_normalized: Quality score normalized to 0-1
    - hallucination_score: Hallucination metric (from Arrow metadata)
    - ocr_text_sample: First 500 chars of OCR ground truth
    - estimated_chars: Character count of OCR text
    - estimated_words: Word count of OCR text
    - domain: Mapped domain code (FIN, LEG, MED, etc.)

Example:
    >>> parser = OhrBenchParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/ohr_bench"),
    ...     image_path=Path("/data/ohr_bench/finance/report_001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["category"])
    "finance"
    >>> print(labels.raw_labels["ohr_quality_score"])
    85.5
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ClassVar

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class OhrBenchParser(BaseParser):
    """Parser for OHR-Bench OCR hallucination benchmark dataset.

    Extracts document category from filename or directory structure,
    and quality scores from Arrow metadata when available.

    Supports two data sources:
    1. Local files: Extracts category from directory structure
    2. HuggingFace Arrow: Extracts quality scores, OCR text, hallucination metrics

    Quality scores are critical for IQA training (P0 priority).
    """

    # OHR-Bench document categories (16 categories)
    OHR_CATEGORIES: ClassVar[set[str]] = {
        "academic",
        "book",
        "exam",
        "finance",
        "form",
        "handwritten",
        "legal",
        "magazine",
        "medical",
        "newspaper",
        "note",
        "poster",
        "receipt",
        "research",
        "resume",
        "slide",
    }

    # Category to domain mapping for Layer 2 enrichment
    CATEGORY_TO_DOMAIN: ClassVar[dict[str, str]] = {
        "finance": "FIN",
        "legal": "LEG",
        "medical": "MED",
        "academic": "EDU",
        "research": "SCI",
        "exam": "EDU",
        "form": "GOV",
        "receipt": "COM",
        "book": "PUB",
        "magazine": "PUB",
        "newspaper": "PUB",
        "slide": "EDU",
        "resume": "HR",
        "note": "UNK",
        "poster": "UNK",
        "handwritten": "UNK",
    }

    # Class-level cache for HuggingFace dataset
    _hf_dataset_cache: ClassVar[Any | None] = None
    _hf_image_index: ClassVar[dict[str, dict[str, Any]] | None] = None
    _cache_initialized: ClassVar[bool] = False

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["ohr-bench", "ohr_bench"]

    def _load_hf_dataset(self, dataset_path: Path) -> bool:
        """Load OHR-Bench dataset from HuggingFace.

        Caches the dataset at class level for efficient batch processing.
        Builds an index mapping image names to metadata records.

        Args:
            dataset_path: Local dataset path (used as cache_dir)

        Returns:
            True if dataset loaded successfully, False otherwise
        """
        if OhrBenchParser._cache_initialized:
            return OhrBenchParser._hf_dataset_cache is not None

        OhrBenchParser._cache_initialized = True

        try:
            ds = self._try_load_dataset(dataset_path)
            if ds is None:
                return False

            image_index = self._build_image_index(ds)
            OhrBenchParser._hf_dataset_cache = ds
            OhrBenchParser._hf_image_index = image_index

            logger.debug(f"Indexed {len(image_index)} OHR-Bench records")
            return True

        except ImportError:
            logger.debug("HuggingFace datasets library not available")
            return False
        except Exception as e:
            logger.debug(f"Failed to load OHR-Bench dataset: {e}")
            return False

    def _try_load_dataset(self, dataset_path: Path) -> Any | None:
        """Try to load dataset from HuggingFace or local Arrow files.

        Args:
            dataset_path: Local dataset path

        Returns:
            Loaded dataset or None if loading fails
        """
        from datasets import load_dataset

        logger.debug("Loading OHR-Bench from HuggingFace...")
        cache_dir = str(dataset_path) if dataset_path.exists() else None

        try:
            return load_dataset(
                "opendatalab/OHR-Bench",
                cache_dir=cache_dir,
                trust_remote_code=True,
            )
        except Exception as e:
            logger.debug(f"Could not load from HuggingFace: {e}")
            return self._try_load_local_arrow(dataset_path)

    def _try_load_local_arrow(self, dataset_path: Path) -> Any | None:
        """Try to load dataset from local Arrow files.

        Args:
            dataset_path: Local dataset path

        Returns:
            Loaded dataset or None if loading fails
        """
        arrow_files = list(dataset_path.glob("**/*.arrow"))
        if not arrow_files:
            return None

        try:
            from datasets import Dataset

            ds = Dataset.from_file(str(arrow_files[0]))
            return {"train": ds}  # Wrap in dict for consistency
        except Exception as e:
            logger.debug(f"Could not load local Arrow: {e}")
            return None

    def _build_image_index(self, ds: Any) -> dict[str, dict[str, Any]]:
        """Build index mapping image names to metadata records.

        Args:
            ds: HuggingFace dataset (Dataset or DatasetDict)

        Returns:
            Dict mapping image identifiers to metadata records
        """
        image_index: dict[str, dict[str, Any]] = {}

        # Handle both Dataset and DatasetDict
        if hasattr(ds, "keys"):
            for split_name in ds:
                self._index_split(ds[split_name], image_index)
        else:
            self._index_split(ds, image_index)

        return image_index

    def _index_split(
        self, split_ds: Any, image_index: dict[str, dict[str, Any]]
    ) -> None:
        """Index records from a single dataset split.

        Args:
            split_ds: Dataset split to index
            image_index: Index dict to update
        """
        for record in split_ds:
            if "image_id" in record:
                image_index[str(record["image_id"])] = record
            if "id" in record:
                image_index[str(record["id"])] = record
            if "image" in record and hasattr(record["image"], "filename"):
                filename = Path(record["image"].filename).stem
                image_index[filename] = record

    def _get_arrow_metadata(
        self, image_path: Path, dataset_path: Path
    ) -> dict[str, Any] | None:
        """Get Arrow metadata for an image.

        Args:
            image_path: Path to the image file
            dataset_path: Root path of the dataset

        Returns:
            Metadata dict if found, None otherwise
        """
        if not self._load_hf_dataset(dataset_path):
            return None

        if OhrBenchParser._hf_image_index is None:
            return None

        # Try to find by various identifiers
        image_name = image_path.stem
        image_name_with_ext = image_path.name

        for key in [image_name, image_name_with_ext, str(image_path)]:
            if key in OhrBenchParser._hf_image_index:
                return OhrBenchParser._hf_image_index[key]

        # Try partial matching (image name might have prefix/suffix)
        for indexed_key in OhrBenchParser._hf_image_index:
            if image_name in indexed_key or indexed_key in image_name:
                return OhrBenchParser._hf_image_index[indexed_key]

        return None

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse OHR-Bench labels from filename, directory, and Arrow metadata.

        Combines three sources of labels:
        1. Category from filename/directory structure
        2. Quality scores from Arrow metadata (if available)
        3. Domain mapping from category

        Args:
            dataset_path: Root path of the OHR-Bench dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with:
            - category, document_type from directory structure
            - ohr_quality_score (0-100), quality_normalized (0-1) from Arrow
            - hallucination_score from Arrow
            - ocr_text_sample, estimated_chars, estimated_words from Arrow
            - domain mapped from category
        """
        labels = OriginalLabels()
        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Source 1: Extract category from filename or parent directory
        category = self._extract_category(image_path, labels)

        # Source 2: Try to get Arrow metadata for quality scores
        arrow_meta = self._get_arrow_metadata(image_path, dataset_path)
        if arrow_meta:
            category = self._extract_arrow_metadata(arrow_meta, labels, category)
            labels.raw_labels["has_arrow_metadata"] = True
        else:
            labels.raw_labels["has_arrow_metadata"] = False

        # Source 3: Map category to domain
        if category and category in self.CATEGORY_TO_DOMAIN:
            labels.raw_labels["domain"] = self.CATEGORY_TO_DOMAIN[category]

        return labels

    def _extract_category(
        self, image_path: Path, labels: OriginalLabels
    ) -> str | None:
        """Extract category from filename or parent directory.

        Args:
            image_path: Path to the image file
            labels: OriginalLabels to update

        Returns:
            Category string if found, None otherwise
        """
        filename = image_path.stem.lower()
        parent = image_path.parent.name.lower()

        for cat in self.OHR_CATEGORIES:
            if cat in filename or cat in parent:
                labels.raw_labels["category"] = cat
                labels.raw_labels["document_type"] = cat.title()
                return cat
        return None

    def _extract_arrow_metadata(
        self,
        arrow_meta: dict[str, Any],
        labels: OriginalLabels,
        category: str | None,
    ) -> str | None:
        """Extract metadata from Arrow record.

        Args:
            arrow_meta: Arrow metadata dict
            labels: OriginalLabels to update
            category: Current category (may be None)

        Returns:
            Updated category string
        """
        # Extract quality score (0-100 scale, higher=better)
        if "quality_score" in arrow_meta:
            quality_score = arrow_meta["quality_score"]
            labels.raw_labels["ohr_quality_score"] = quality_score
            labels.raw_labels["quality_normalized"] = quality_score / 100.0

        # Extract hallucination score
        if "hallucination_score" in arrow_meta:
            labels.raw_labels["hallucination_score"] = arrow_meta["hallucination_score"]

        # Extract OCR text statistics
        self._extract_ocr_text(arrow_meta, labels)

        # Update category from Arrow if not found from filename
        if category is None and "category" in arrow_meta:
            category = arrow_meta["category"]
            labels.raw_labels["category"] = category
            labels.raw_labels["document_type"] = category.title()

        return category

    def _extract_ocr_text(
        self, arrow_meta: dict[str, Any], labels: OriginalLabels
    ) -> None:
        """Extract OCR text and compute statistics.

        Args:
            arrow_meta: Arrow metadata dict
            labels: OriginalLabels to update
        """
        if "ocr_text" not in arrow_meta:
            return

        ocr_text = arrow_meta["ocr_text"] or ""
        labels.raw_labels["ocr_text_sample"] = ocr_text[:500]
        labels.raw_labels["estimated_chars"] = len(ocr_text)
        labels.raw_labels["estimated_words"] = len(ocr_text.split())

    def supports_batch(self) -> bool:
        """OHR-Bench benefits from batch processing with shared Arrow cache."""
        return True

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images efficiently.

        Loads Arrow metadata once and processes all images.

        Args:
            dataset_path: Root path of the dataset
            image_paths: List of absolute paths to image files
            config: Dataset configuration dictionary

        Returns:
            List of OriginalLabels in same order as image_paths
        """
        # Trigger Arrow loading for cache
        self._load_hf_dataset(dataset_path)

        # Process each image
        return [self.parse(dataset_path, p, config) for p in image_paths]


__all__ = ["OhrBenchParser"]
