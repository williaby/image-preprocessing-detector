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

# Datasets that contain no images (text corpora only).  The audit runner
# should skip image-path validation for these and mark them as
# "no-image-audit" rather than raising path-not-found errors.
_TEXT_CORPUS_EXCLUSIONS: tuple[str, ...] = (
    "openlid-v2",  # Language ID text corpus — no images
    "wili-2018",  # Language ID text corpus — superseded by openlid-v2
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

        self._validate_paths(warnings)
        self._validate_parameters(warnings)

        for warning in warnings:
            logger.warning("Config validation: %s", warning)

        return warnings

    def _validate_paths(self, warnings: list[str]) -> None:
        """Validate all configured file and directory paths."""
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

    def _validate_parameters(self, warnings: list[str]) -> None:
        """Validate non-path configuration parameters."""
        if self.sample_size < 1:
            warnings.append(f"sample_size must be >= 1, got {self.sample_size}")

        invalid_axes = set(self.stratification_axes) - VALID_STRATIFICATION_AXES
        if invalid_axes:
            warnings.append(f"Unknown stratification axes: {sorted(invalid_axes)}")

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
    "funsd-plus": {
        "image_base_path": _BASE_DATA_DIR / "forms" / "funsd_plus",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "funsd_plus_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "funsd_plus_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "funsd_plus_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "funsd_plus"
            / "layout_batch_0.json"
        ),
        "docling_ocr_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "funsd_plus"
            / "ocr_batch_0.jsonl"
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
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "ohr-bench_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "ohr-bench_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "ohr-bench"
            / "layout_batch_0.json"
        ),
        "docling_ocr_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "ohr-bench"
            / "ocr_batch_0.jsonl"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "quality_overall",
        ),
    },
    "jssoda": {
        "image_base_path": (
            _BASE_DATA_DIR / "language" / "multilingual_scripts" / "jssoda"
        ),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "jssoda_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "jssoda_llm_enrichment.json"),
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
        "image_base_path": (_BASE_DATA_DIR / "language" / "mlt19"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "mlt19_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "mlt19_llm_enrichment.json"),
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
        "image_base_path": (_BASE_DATA_DIR / "language" / "nepali_handwritten"),
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
            _BASE_DATA_DIR / "language" / "multilingual_scripts" / "dzongkha_digits"
        ),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "dzongkha-digits_metadata.json"),
        "sample_size": 62,
        "stratification_axes": (
            "capture_method",
            "has_handwriting",
        ),
    },
    "realdae": {
        "image_base_path": (_BASE_DATA_DIR / "camera_captured" / "realdae"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "realdae_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "realdae_llm_enrichment.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    "bhutan-afs": {
        "image_base_path": (_BASE_DATA_DIR / "documents" / "bhutan_financial"),
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
    # -----------------------------------------------------------------
    # Correction / Shadow Removal / Dewarping (6)
    # -----------------------------------------------------------------
    "anyphotodoc6300": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "anyphotodoc6300"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "anyphotodoc6300_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "docalign12k": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "docalign12k"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "docalign12k_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "wsrd": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "wsrd"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "wsrd_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "warpdoc": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "warpdoc"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "warpdoc_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "docreal": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "docreal"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "docreal_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "sd7k": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "sd7k"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "sd7k_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    # -----------------------------------------------------------------
    # Text Detection / Scene Text
    # -----------------------------------------------------------------
    "cocotext": {
        "image_base_path": (_BASE_DATA_DIR / "text_detection" / "cocotext"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "cocotext_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "cocotext_llm_enrichment.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "cocotext_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    # -----------------------------------------------------------------
    # Degraded / Archival Documents
    # -----------------------------------------------------------------
    "tobacco800": {
        "image_base_path": (_BASE_DATA_DIR / "degraded" / "tobacco800"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "tobacco800_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "tobacco800_llm_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    # -----------------------------------------------------------------
    # Quality Benchmarks
    # -----------------------------------------------------------------
    "smartdoc-qa": {
        "image_base_path": (
            Path("/mnt/e/image_detection/02_benchmark_only/smartdoc-qa")
        ),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "smartdoc-qa_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "smartdoc-qa_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "smartdoc-qa_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "resolution_category",
            "quality_overall",
        ),
    },
    # -----------------------------------------------------------------
    # Table / Layout Datasets
    # -----------------------------------------------------------------
    "tablebank": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "tablebank",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "tablebank_metadata.json"),
        "stratification_axes": (
            "domain_level1",
            "resolution_category",
            "has_table",
        ),
    },
    # -----------------------------------------------------------------
    # Financial / Forms / Invoice Datasets
    # -----------------------------------------------------------------
    "financebench": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "financebench",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "financebench_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "financebench_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "financebench_language_enrichment.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "resolution_category",
        ),
    },
    "invoices-kg": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "invoices-kg",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "invoices-kg_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "invoices_kg_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "invoices_kg_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "invoices-kaggle"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "resolution_category",
        ),
    },
    "nist-sd2": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "nist-sd2",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "nist-sd2_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "nist-sd2_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "nist-sd2"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "has_handwriting",
        ),
    },
    "nist-sd6": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "nist-sd6",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "nist_sd6_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "nist-sd6_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "nist-sd6"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "has_handwriting",
        ),
    },
    "nist-sd19": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "nist-sd19",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "nist_sd19_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "nist-sd19_language_enrichment.json"
        ),
        "stratification_axes": (
            "has_handwriting",
            "resolution_category",
        ),
    },
    # -----------------------------------------------------------------
    # Multilingual / Script Detection
    # -----------------------------------------------------------------
    "mdiw13": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "mdiw13"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "mdiw13_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "mdiw13_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "mdiw13"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "script_family",
            "capture_method",
        ),
    },
    "siw13": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "siw13"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "siw13_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "siw13_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent / "extracted" / "siw13" / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "script_family",
            "capture_method",
        ),
    },
    "cvsi": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "cvsi"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "cvsi_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "cvsi_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent / "extracted" / "cvsi" / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "script_family",
            "capture_method",
        ),
    },
    "hindi-synth": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "hindi_ocr_synthetic"),
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "hindi_ocr_synthetic_metadata.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "hindi_ocr_synthetic_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "hindi-synth"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "resolution_category",
            "domain_level1",
        ),
    },
    "yarmouk": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "yarmouk_ocr"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "yarmouk_ocr_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "yarmouk_ocr_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "yarmouk"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "script_family",
            "domain_level1",
        ),
    },
    "muharaf": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "muharaf"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "muharaf_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "muharaf_llm_enrichment.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "muharaf_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "muharaf"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "script_family",
            "has_handwriting",
        ),
    },
    "mle2e": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "mle2e"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "mle2e_metadata.json"),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent / "extracted" / "mle2e" / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "script_family",
            "capture_method",
        ),
    },
    # -----------------------------------------------------------------
    # Handwriting Datasets
    # -----------------------------------------------------------------
    "iam": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "iam",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "iam_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "iam_llm_enrichment.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "iam_language_enrichment.json"
        ),
        "stratification_axes": (
            "has_handwriting",
            "resolution_category",
        ),
    },
    "tibhcr": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "tibhcr",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "tibhcr_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "tibhcr_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "tibhcr"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "has_handwriting",
            "resolution_category",
        ),
    },
    "hasy": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "hasy",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "hasyv2_metadata.json"),
        "stratification_axes": (
            "resolution_category",
            "capture_method",
        ),
    },
    "pucit-ohul": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "pucit_ohul"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "pucit_ohul_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "pucit-ohul_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "pucit-ohul"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "script_family",
            "has_handwriting",
        ),
    },
    "signatr6k": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "signatr6k",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "signatr6k_metadata.json"),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "signatr6k"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "has_handwriting",
            "capture_method",
        ),
    },
    # -----------------------------------------------------------------
    # Math / Formula Datasets
    # -----------------------------------------------------------------
    "im2latex": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "im2latex",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "im2latex_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "im2latex_language_enrichment.json"
        ),
        "stratification_axes": (
            "resolution_category",
            "domain_level1",
        ),
    },
    "mathverse": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "mathverse",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "mathverse_metadata.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "mathverse_language_enrichment.json"
        ),
        "stratification_axes": (
            "resolution_category",
            "domain_level1",
        ),
    },
    # -----------------------------------------------------------------
    # Binarization / Degradation Benchmarks
    # -----------------------------------------------------------------
    "dibco": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "dibco",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "dibco_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "dibco_llm_enrichment.json"),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent / "extracted" / "dibco" / "layout_batch_0.json"
        ),
        "sample_size": 212,
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    # -----------------------------------------------------------------
    # Document Classification / ID Documents
    # -----------------------------------------------------------------
    "rvl-cdip": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "rvl-cdip",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "rvl_cdip_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "rvl-cdip_llm_enrichment.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "rvl-cdip_language_enrichment.json"
        ),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "rvl-cdip"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "capture_method",
        ),
    },
    "midv500": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "midv500",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "midv500_metadata.json"),
        "llm_enrichment_path": (DEFAULT_METADATA_ROOT / "midv500_llm_enrichment.json"),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "midv500_language_enrichment.json"
        ),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    # -----------------------------------------------------------------
    # Benchmarks / Multi-Task
    # -----------------------------------------------------------------
    "omnidocbench": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "omnidocbench",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "omnidocbench_metadata.json"),
        "docling_layout_path": (
            DEFAULT_METADATA_ROOT.parent
            / "extracted"
            / "omnidocbench"
            / "layout_batch_0.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "capture_method",
        ),
    },
    "multimodal-textbook": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "multimodal-textbook",
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "multimodal_textbook_metadata.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "multimodal_textbook_language_enrichment.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "resolution_category",
        ),
    },
    "ocr-quality": {
        "image_base_path": DEFAULT_IMAGE_ROOT / "ocr-quality",
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "ocr_quality_metadata.json"),
        "llm_enrichment_path": (
            DEFAULT_METADATA_ROOT / "ocr-quality_llm_enrichment.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "ocr_quality_language_enrichment.json"
        ),
        "stratification_axes": (
            "script_family",
            "quality_overall",
        ),
    },
    # -----------------------------------------------------------------
    # New Datasets (2025-2026 Onboarding)
    # -----------------------------------------------------------------
    "indicdlp": {
        "image_base_path": (_BASE_DATA_DIR / "layout" / "indicdlp"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "indicdlp_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "document-haystack": {
        "image_base_path": (
            Path("/mnt/e/image_detection/02_benchmark_only/document-haystack")
        ),
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "document-haystack_metadata.json"
        ),
        "stratification_axes": (
            "domain_level1",
            "capture_method",
        ),
    },
    "staindoc": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "staindoc"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "staindoc_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "q-doc": {
        "image_base_path": (Path("/mnt/e/image_detection/02_benchmark_only/q-doc")),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "q-doc_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "drccbi": {
        "image_base_path": (_BASE_DATA_DIR / "correction" / "drccbi"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "drccbi_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    "markushgrapher": {
        "image_base_path": (_BASE_DATA_DIR / "specialized" / "markushgrapher"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "markushgrapher_metadata.json"),
        "stratification_axes": (
            "domain_level1",
            "capture_method",
        ),
    },
    # Auto-registered by Layer 2 audit agent (2026-02-24) — midv2020 was not in
    # _KNOWN_CONFIGS prior to this audit run. Defaults derived from metadata path
    # convention and dataset characteristics (camera + scanner, GOV domain).
    "midv2020": {
        "image_base_path": (_BASE_DATA_DIR / "documents" / "midv2020"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "midv2020_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
            "resolution_category",
        ),
    },
    # Auto-registered by Layer 2 audit agent (2026-02-24) — doc3d was not in
    # _KNOWN_CONFIGS prior to this audit run. Defaults derived from metadata path
    # convention. WARNING: metadata JSON does not yet exist — annotate_base_metadata.py
    # must be run first. Primary use: warping_reg head (SIG-G5-3) training data.
    "doc3d": {
        "image_base_path": (
            _BASE_DATA_DIR / "camera_captured" / "doc3d" / "data" / "doc3d" / "img"
        ),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "doc3d_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "domain_level1",
        ),
    },
    # Auto-registered by Layer 2 audit agent (2026-02-24) — kuzushiji was not in
    # _KNOWN_CONFIGS. Defaults derived from metadata path convention and dataset
    # characteristics (scanner + handwriting + historical Japanese).
    # WARNING: metadata JSON does not yet exist — raw data must be downloaded first,
    # then materialize_kuzushiji.py must be run, then annotate_base_metadata.py.
    # See scripts/audit/results/kuzushiji/blocker_report.md for resolution steps.
    # 3 sub-datasets: K-MNIST (70K, 28px), K-49 (271K, 28px), K-Kanji (140K, 64px).
    # Primary heads: script_cls (JPAN), handwriting_presence_cls.
    "kuzushiji": {
        "image_base_path": (_BASE_DATA_DIR / "handwriting" / "kuzushiji"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "kuzushiji_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "has_handwriting",
            "resolution_category",
        ),
    },
    # -----------------------------------------------------------------
    # Handwriting Datasets — new (2026 onboarding)
    # -----------------------------------------------------------------
    "iiit-hw-hindi": {
        "image_base_path": (_BASE_DATA_DIR / "handwriting" / "iiit-hw-hindi"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "iiit-hw-hindi_metadata.json"),
        "stratification_axes": (
            "capture_method",
            "has_handwriting",
            "resolution_category",
        ),
    },
    "khatt": {
        "image_base_path": (_BASE_DATA_DIR / "handwriting" / "khatt"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "khatt_metadata.json"),
        "stratification_axes": (
            "script_family",
            "has_handwriting",
        ),
    },
    # CASIA-HWDB2: 5,091 full-page Chinese handwriting scans (DGRL binary format).
    # Sub-datasets: HWDB2.0, HWDB2.1, HWDB2.2. image_base_path points to the HWDB/
    # subdirectory which contains both *_images/ PNG dirs and *_index.jsonl sidecars.
    # capture_method=scanner_flatbed, iso639=zh, iso15924=Hans, text_scope=page.
    # Primary heads: handwriting_presence_cls, script_cls (Hans/CJK).
    "casia-hwdb2": {
        "image_base_path": (_BASE_DATA_DIR / "handwriting" / "casia-hwdb2" / "HWDB"),
        "metadata_json_path": (DEFAULT_METADATA_ROOT / "casia-hwdb2_metadata.json"),
        "stratification_axes": (
            "script_family",
            "has_handwriting",
            "resolution_category",
        ),
    },
    # CASIA-HWDB2-line: 52,160 Chinese handwriting line images (Teklia HF edition).
    # materialized from Parquet; images in images/{split}/, index in {split}_index.jsonl.
    # capture_method=scanner_flatbed, iso639=zh, iso15924=Hans, text_scope=line.
    # Primary heads: handwriting_presence_cls, script_cls (Hans/CJK).
    "casia-hwdb2-line": {
        "image_base_path": (
            _BASE_DATA_DIR / "handwriting" / "casia-hwdb2-line" / "images"
        ),
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "casia-hwdb2-line_metadata.json"
        ),
        "stratification_axes": (
            "script_family",
            "has_handwriting",
            "resolution_category",
        ),
    },
    # Auto-registered by Layer 2 audit agent (2026-02-24) — multilingual-scripts
    # was not in _KNOWN_CONFIGS prior to this audit run. Defaults derived from
    # metadata path convention. Dataset aggregates 4 subdatasets: jssoda (Jpan,
    # 2000), nepal_devanagari (Deva, 717), arabic_ocr (Arab, 500), dzongkha_digits
    # (Tibt, 62). Primary heads: script_cls (SIG-G2-1), handwriting_presence_cls.
    # NOTE: capture_method=unknown and domain_level1=UNK for all 3279 samples.
    # Stratification uses iso15924_script as effective axis via script_family.
    "multilingual-scripts": {
        "image_base_path": (_BASE_DATA_DIR / "language" / "multilingual_scripts"),
        "metadata_json_path": (
            DEFAULT_METADATA_ROOT / "multilingual_scripts_metadata.json"
        ),
        "language_enrichment_path": (
            DEFAULT_METADATA_ROOT / "multilingual_scripts_language_enrichment.json"
        ),
        "stratification_axes": (
            "script_family",
            "capture_method",
            "resolution_category",
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
