# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for FinanceBench dataset.

FinanceBench is a financial Q&A benchmark containing SEC filings (10K, 10Q, 8K,
Earnings reports) from publicly traded companies for evaluating RAG systems.

Dataset Structure:
    financebench/
        pdfs/
            {COMPANY}_{PERIOD}_{TYPE}.pdf
        extracted_images/
            {COMPANY}_{PERIOD}_{TYPE}_p{PAGE:03d}.png
        data/
            financebench_document_information.jsonl
            financebench_open_source.jsonl

Document Types:
    - 10k: Annual financial reports
    - 10q: Quarterly financial reports
    - 8k: Current event reports
    - earnings: Earnings call transcripts

GICS Sectors (9):
    - Communication Services
    - Consumer Discretionary
    - Consumer Staples
    - Financials
    - Health Care
    - Industrials
    - Information Technology
    - Materials
    - Utilities

Reference:
    - Paper: https://arxiv.org/abs/2311.11944
    - GitHub: https://github.com/patronus-ai/financebench
    - HuggingFace: https://huggingface.co/datasets/PatronusAI/financebench

Example:
    >>> parser = FinanceBenchParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/financebench"),
    ...     image_path=Path("/data/financebench/extracted_images/3M_2018_10K_p059.png"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["company"])
    "3M"
    >>> print(labels.raw_labels["doc_type"])
    "10k"
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class FinanceBenchParser(BaseParser):
    """Parser for FinanceBench financial document benchmark dataset.

    Extracts document metadata from filename pattern and JSONL metadata files.
    Supports batch parsing with cached metadata loading.
    """

    # Valid document types in FinanceBench
    DOC_TYPES = {"10k", "10q", "8k", "earnings"}

    # GICS sectors present in the dataset
    GICS_SECTORS = {
        "Communication Services",
        "Consumer Discretionary",
        "Consumer Staples",
        "Financials",
        "Health Care",
        "Industrials",
        "Information Technology",
        "Materials",
        "Utilities",
    }

    # Filename pattern: {COMPANY}_{PERIOD}_{TYPE}_p{PAGE}.png
    # Examples: 3M_2018_10K_p059.png, ADOBE_2022_10K_p001.png
    FILENAME_PATTERN = re.compile(
        r"^(?P<company>.+?)_(?P<period>\d{4}Q?\d?)_(?P<doc_type>\w+)_p(?P<page>\d+)\.png$",
        re.IGNORECASE,
    )

    # Cache for document metadata
    _doc_info_cache: dict[str, dict[str, Any]] | None = None
    _evidence_pages_cache: dict[str, set[int]] | None = None

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["financebench", "finance-bench", "finance_bench"]

    def _load_document_info(self, dataset_path: Path) -> dict[str, dict[str, Any]]:
        """Load document information from JSONL file.

        Args:
            dataset_path: Root path of the FinanceBench dataset

        Returns:
            Dict mapping doc_name to document metadata
        """
        if self._doc_info_cache is not None:
            return self._doc_info_cache

        doc_info_path = (
            dataset_path / "data" / "financebench_document_information.jsonl"
        )
        if not doc_info_path.exists():
            logger.warning(f"Document info file not found: {doc_info_path}")
            self._doc_info_cache = {}
            return self._doc_info_cache

        self._doc_info_cache = {}
        with open(doc_info_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    doc = json.loads(line)
                    doc_name = doc.get("doc_name", "")
                    if doc_name:
                        self._doc_info_cache[doc_name] = doc

        logger.info(
            f"Loaded {len(self._doc_info_cache)} document records from FinanceBench"
        )
        return self._doc_info_cache

    def _load_evidence_pages(self, dataset_path: Path) -> dict[str, set[int]]:
        """Load evidence page numbers from Q&A data.

        Args:
            dataset_path: Root path of the FinanceBench dataset

        Returns:
            Dict mapping doc_name to set of evidence page numbers
        """
        if self._evidence_pages_cache is not None:
            return self._evidence_pages_cache

        qa_path = dataset_path / "data" / "financebench_open_source.jsonl"
        if not qa_path.exists():
            logger.warning(f"Q&A data file not found: {qa_path}")
            self._evidence_pages_cache = {}
            return self._evidence_pages_cache

        self._evidence_pages_cache = {}
        with open(qa_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    qa = json.loads(line)
                    evidence_list = qa.get("evidence", [])
                    for evidence in evidence_list:
                        doc_name = evidence.get("doc_name", "")
                        page_num = evidence.get("evidence_page_num")
                        if doc_name and page_num is not None:
                            if doc_name not in self._evidence_pages_cache:
                                self._evidence_pages_cache[doc_name] = set()
                            # Page numbers are 0-indexed in evidence, +1 for filename
                            self._evidence_pages_cache[doc_name].add(page_num + 1)

        logger.info(
            f"Loaded evidence references for {len(self._evidence_pages_cache)} documents"
        )
        return self._evidence_pages_cache

    def _parse_filename(self, image_path: Path) -> dict[str, Any] | None:
        """Parse metadata from image filename.

        Args:
            image_path: Path to the image file

        Returns:
            Dict with company, period, doc_type, page_num or None if no match
        """
        filename = image_path.name
        match = self.FILENAME_PATTERN.match(filename)

        if not match:
            # Try simpler pattern for non-paginated files
            simple_match = re.match(
                r"^(?P<company>.+?)_(?P<period>\d{4}Q?\d?)_(?P<doc_type>\w+)\.png$",
                filename,
                re.IGNORECASE,
            )
            if simple_match:
                return {
                    "company": simple_match.group("company"),
                    "period": simple_match.group("period"),
                    "doc_type": simple_match.group("doc_type").lower(),
                    "page_num": 1,
                }
            return None

        return {
            "company": match.group("company"),
            "period": match.group("period"),
            "doc_type": match.group("doc_type").lower(),
            "page_num": int(match.group("page")),
        }

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse FinanceBench labels from filename and metadata files.

        Args:
            dataset_path: Root path of the FinanceBench dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with document metadata in raw_labels
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Parse filename for basic metadata
        parsed = self._parse_filename(image_path)
        if parsed is None:
            logger.warning(f"Could not parse FinanceBench filename: {image_path.name}")
            labels.raw_labels["parse_error"] = (
                f"Invalid filename format: {image_path.name}"
            )
            return labels

        # Set basic fields from filename
        labels.raw_labels["company"] = parsed["company"]
        labels.raw_labels["doc_period"] = parsed["period"]
        labels.raw_labels["doc_type"] = parsed["doc_type"]
        labels.raw_labels["page_num"] = parsed["page_num"]

        # Construct doc_name for lookup
        doc_name = (
            f"{parsed['company']}_{parsed['period']}_{parsed['doc_type'].upper()}"
        )

        # Try to get additional metadata from document info
        doc_info = self._load_document_info(dataset_path)
        if doc_name in doc_info:
            doc_meta = doc_info[doc_name]
            labels.raw_labels["gics_sector"] = doc_meta.get("gics_sector")
            labels.raw_labels["doc_link"] = doc_meta.get("doc_link")
        else:
            # Try case-insensitive lookup
            for key, doc_meta in doc_info.items():
                if key.lower() == doc_name.lower():
                    labels.raw_labels["gics_sector"] = doc_meta.get("gics_sector")
                    labels.raw_labels["doc_link"] = doc_meta.get("doc_link")
                    break

        # Check if this page is cited as evidence in Q&A
        evidence_pages = self._load_evidence_pages(dataset_path)
        is_evidence_page = False
        for key, pages in evidence_pages.items():
            if key.lower() == doc_name.lower() and parsed["page_num"] in pages:
                is_evidence_page = True
                break
        labels.raw_labels["is_evidence_page"] = is_evidence_page

        # Set document type for downstream compatibility
        labels.raw_labels["document_type"] = f"SEC {parsed['doc_type'].upper()}"

        return labels

    def supports_batch(self) -> bool:
        """FinanceBench supports batch parsing with cached metadata."""
        return True


__all__ = ["FinanceBenchParser"]
