#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Dataset-specific configuration for Layer 2 metadata audits.

Provides a ``DatasetAuditConfig`` dataclass that collects every path and
parameter an audit run needs, plus a factory method for known datasets.

Usage:
    from scripts.audit.audit_config import (
        DatasetAuditConfig,
        load_dataset_config,
        list_known_datasets,
    )

    cfg = load_dataset_config("diqa-5000")
    cfg.validate()

    # Or build ad-hoc:
    cfg = DatasetAuditConfig(
        dataset_name="my-custom",
        metadata_json_path=Path("/data/my_custom_metadata.json"),
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = PROJECT_ROOT / "docs" / "schema" / "layer2_enrichment_v2.schema.json"
DEFAULT_METADATA_ROOT = Path("/mnt/e/image_detection/metadata_registry/json")
DEFAULT_IMAGE_ROOT = Path("/mnt/e/image_detection/01_base_datasets")
_BASE_DATA_DIR = Path("/mnt/e/image_detection/01_base_data")
DEFAULT_SAMPLE_SIZE = 36

# Stratification axes supported by the sampling step.
VALID_STRATIFICATION_AXES: frozenset[str] = frozenset(
    {
        "capture_method",
        "domain_level1",
        "resolution_category",
        "quality_overall",
        "layout_type",
        "text_density",
        "script_family",
        "has_table",
        "has_handwriting",
    }
)

# Default stratification axes when none are specified.
DEFAULT_STRATIFICATION_AXES: tuple[str, ...] = (
    "capture_method",
    "domain_level1",
    "resolution_category",
)


# ---------------------------------------------------------------------------
# DatasetAuditConfig
# ---------------------------------------------------------------------------
@dataclass
class DatasetAuditConfig:
    """All parameters needed for a single dataset audit run.

    Attributes:
        dataset_name: Canonical dataset name (e.g. ``diqa-5000``).
        image_base_path: Root directory containing the dataset images.
        metadata_json_path: Path to the primary Layer 2 metadata JSON
            produced by ``annotate_base_metadata.py``.
        schema_path: Path to the JSON Schema file to validate against.
        llm_enrichment_path: Optional path to LLM enrichment JSON.
        language_enrichment_path: Optional path to language enrichment
            JSON.
        docling_layout_path: Optional path to Docling layout JSON.
        docling_ocr_path: Optional path to Docling OCR JSON.
        csv_paths: Additional CSV files relevant to the audit
            (e.g. ground-truth labels exported from annotation tools).
        sample_size: Number of samples to audit (default 36).
        stratification_axes: Axes used for stratified sample selection.
    """

    dataset_name: str
    image_base_path: Path | None = None
    metadata_json_path: Path | None = None
    schema_path: Path = field(default_factory=lambda: SCHEMA_PATH)
    llm_enrichment_path: Path | None = None
    language_enrichment_path: Path | None = None
    docling_layout_path: Path | None = None
    docling_ocr_path: Path | None = None
    csv_paths: list[Path] = field(default_factory=list)
    sample_size: int = DEFAULT_SAMPLE_SIZE
    stratification_axes: tuple[str, ...] = DEFAULT_STRATIFICATION_AXES

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Check that referenced paths exist and parameters are sane.

        Returns:
            A list of human-readable warning strings.  An empty list
            means the configuration is fully valid.
        """
        warnings: list[str] = []

        if not self.dataset_name:
            warnings.append("dataset_name is empty")

        if self.metadata_json_path and not self.metadata_json_path.exists():
            warnings.append(
                f"metadata_json_path does not exist: {self.metadata_json_path}"
            )

        if self.schema_path and not self.schema_path.exists():
            warnings.append(f"schema_path does not exist: {self.schema_path}")

        if self.image_base_path and not self.image_base_path.is_dir():
            warnings.append(
                f"image_base_path is not a directory: {self.image_base_path}"
            )

        optional_paths: list[tuple[str, Path | None]] = [
            ("llm_enrichment_path", self.llm_enrichment_path),
            ("language_enrichment_path", self.language_enrichment_path),
            ("docling_layout_path", self.docling_layout_path),
            ("docling_ocr_path", self.docling_ocr_path),
        ]
        for name, path in optional_paths:
            if path is not None and not path.exists():
                warnings.append(f"{name} does not exist: {path}")

        for csv_path in self.csv_paths:
            if not csv_path.exists():
                warnings.append(f"csv_path does not exist: {csv_path}")

        if self.sample_size < 1:
            warnings.append(f"sample_size must be >= 1, got {self.sample_size}")

        invalid_axes = set(self.stratification_axes) - (VALID_STRATIFICATION_AXES)
        if invalid_axes:
            warnings.append(f"Unknown stratification axes: {sorted(invalid_axes)}")

        for warning in warnings:
            logger.warning("Config validation: %s", warning)

        return warnings

    def as_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "image_base_path": str(self.image_base_path)
            if self.image_base_path
            else None,
            "metadata_json_path": str(self.metadata_json_path)
            if self.metadata_json_path
            else None,
            "schema_path": str(self.schema_path),
            "llm_enrichment_path": str(self.llm_enrichment_path)
            if self.llm_enrichment_path
            else None,
            "language_enrichment_path": str(self.language_enrichment_path)
            if self.language_enrichment_path
            else None,
            "docling_layout_path": str(self.docling_layout_path)
            if self.docling_layout_path
            else None,
            "docling_ocr_path": str(self.docling_ocr_path)
            if self.docling_ocr_path
            else None,
            "csv_paths": [str(p) for p in self.csv_paths],
            "sample_size": self.sample_size,
            "stratification_axes": list(self.stratification_axes),
        }


# ---------------------------------------------------------------------------
# Known dataset registry
# ---------------------------------------------------------------------------
# Each entry returns kwargs for DatasetAuditConfig.  Paths are resolved
# relative to DEFAULT_METADATA_ROOT / DEFAULT_IMAGE_ROOT so they work on
# the canonical development machine.  Callers can override individual
# fields after construction.

_KNOWN_CONFIGS: dict[str, dict[str, Any]] = {
    "diqa-5000": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "diqa-5000",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "diqa-5000_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "diqa-5000_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "diqa-5000_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
            "quality_overall",
        ),
    },
    "doclaynet": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "doclaynet",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "doclaynet_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "doclaynet_language_enrichment.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "layout_type",
            "has_table",
        ),
    },
    "funsd": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "funsd",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "funsd_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "funsd_language_enrichment.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "resolution_category",
            "has_handwriting",
        ),
    },
    "pubtabnet": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "pubtabnet",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "pubtabnet_metadata.json"),
        "stratification_axes": (
            "domain_level1",
            "resolution_category",
            "has_table",
        ),
    },
    "fintabnet": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "fintabnet",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "fintabnet_metadata.json"),
        "stratification_axes": (
            "domain_level1",
            "resolution_category",
        ),
    },
    "sroie": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "sroie",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "sroie_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "sroie_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    "hiertext": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "hiertext",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "hiertext_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "hiertext_language_enrichment.json"
        ),
        "stratification_axes": (
            "script_family",
            "text_density",
            "has_handwriting",
        ),
    },
    "cc-ocr": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "cc-ocr",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "cc_ocr_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    "arabic-docs-ocr": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "arabic-docs-ocr",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "arabic_docs_ocr_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "arabic_docs_ocr_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    "ohr-bench": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "ohr-bench",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "ohr_bench_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "quality_overall",
        ),
    },
    "jssoda": {
        "image_base_path": (
            _BASE_DATA_DIR
            / "language"
            / "multilingual_scripts"
            / "jssoda"
        ),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "jssoda_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "jssoda_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "jssoda_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    "mlt19": {
        "image_base_path": (
            _BASE_DATA_DIR / "language" / "mlt19"
        ),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "mlt19_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "mlt19_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "mlt19_language_enrichment.json"
        ),
        "stratification_axes": (
            "script_family",
            "domain_level1",
            "capture_method",
        ),
    },
    "nepali-handwritten": {
        "image_base_path": (
            _BASE_DATA_DIR
            / "language"
            / "nepali_handwritten"
        ),
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "nepali_handwritten_metadata.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "nepali_handwritten_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "resolution_category",
            "has_handwriting",
        ),
    },
    "dzongkha-digits": {
        "image_base_path": (
            _BASE_DATA_DIR
            / "language"
            / "multilingual_scripts"
            / "dzongkha_digits"
        ),
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "dzongkha-digits_metadata.json"
        ),
        "sample_size": 62,
        "stratification_axes": (
            "capture_method",
            "has_handwriting",
        ),
    },
    "realdae": {
        "image_base_path": (
            _BASE_DATA_DIR
            / "camera_captured"
            / "realdae"
        ),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "realdae_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "realdae_llm_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    "bhutan-afs": {
        "image_base_path": (
            _BASE_DATA_DIR
            / "documents"
            / "bhutan_financial"
        ),
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "bhutan_financial_metadata.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "bhutan-afs"
            / "layout_batch_0.json"
        ),
        "docling_ocr_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "bhutan-afs"
            / "ocr_batch_0.jsonl"
        ),
        "sample_size": 135,
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
}


def load_dataset_config(
    dataset_name: str,
    *,
    sample_size: int | None = None,
    schema_path: Path | None = None,
) -> DatasetAuditConfig:
    """Build a ``DatasetAuditConfig`` for a known dataset.

    Args:
        dataset_name: Canonical dataset name.
        sample_size: Override the default sample size (36).
        schema_path: Override the default schema path.

    Returns:
        A fully-populated ``DatasetAuditConfig``.

    Raises:
        ValueError: If *dataset_name* is not in the known registry.
    """
    if dataset_name not in _KNOWN_CONFIGS:
        known = ", ".join(sorted(_KNOWN_CONFIGS))
        msg = (
            f"Unknown dataset '{dataset_name}'. "
            f"Known datasets: {known}. "
            f"Build a DatasetAuditConfig manually for custom datasets."
        )
        raise ValueError(msg)

    kwargs: dict[str, Any] = {
        "dataset_name": dataset_name,
        **_KNOWN_CONFIGS[dataset_name],
    }
    if sample_size is not None:
        kwargs["sample_size"] = sample_size
    if schema_path is not None:
        kwargs["schema_path"] = schema_path

    return DatasetAuditConfig(**kwargs)


def list_known_datasets() -> list[str]:
    """Return sorted list of datasets with pre-built configurations."""
    return sorted(_KNOWN_CONFIGS)
