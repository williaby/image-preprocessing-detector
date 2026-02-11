#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""
Annotate base dataset images with versioned metadata schema.

Implements the three-layer metadata architecture from metadata-versioning-schema.md:
1. IMMUTABLE LAYER: Original labels preserved exactly as provided by source datasets
2. ENRICHMENT LAYER: Our derived annotations with full provenance (versioned)
3. TRAINING LAYER: Computed on-demand from original + enrichments

Enrichment Tiers:
- Tier 0: Exact by construction (dataset IS 100% tables/formulas/signatures)
- Tier 1: Derived from existing COCO/JSON annotations
- Tier 2: DocLayout-YOLO inference (default) or dataset heuristics (--no-yolo)

Usage:
    # Scan all datasets with DocLayout-YOLO (default)
    python scripts/annotate_base_metadata.py --scan

    # Scan without YOLO (use dataset defaults only)
    python scripts/annotate_base_metadata.py --scan --no-yolo

    # Scan specific dataset
    python scripts/annotate_base_metadata.py --scan --dataset diqa-5000

    # Generate statistics report
    python scripts/annotate_base_metadata.py --stats

    # Export training-ready parquet
    python scripts/annotate_base_metadata.py --export

    # Extract OmniDocBench images from arrow format
    python scripts/annotate_base_metadata.py --extract-omnidocbench

Updated 2025-12-20: Added reproducibility fields, tiered enrichment, DocLayout-YOLO.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import ipc
from PIL import Image
from tqdm import tqdm

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants and Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
E_DRIVE_ROOT = Path("/mnt/e/image_detection")
BASE_DATA = E_DRIVE_ROOT / "01_base_data"
BENCHMARK_ONLY = E_DRIVE_ROOT / "02_benchmark_only"
METADATA_ROOT = E_DRIVE_ROOT / "metadata_registry"


# Current git SHA for reproducibility
def get_git_sha() -> str:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            check=True,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


# Schema version for tracking changes
SCHEMA_VERSION = "2.1.0"  # v2.1.0: geometric, physical_degradation, ml_iqa, code, image_properties, ocr_impact
SCRIPT_VERSION = "2.0.0"


class CaptureMethod(str, Enum):
    """Capture method taxonomy (Axis 4 from detection-taxonomy.md)."""

    BORN_DIGITAL = "born_digital"
    SCANNER_FLATBED = "scanner_flatbed"
    SCANNER_ADF = "scanner_adf"
    CAMERA_PROFESSIONAL = "camera_professional"
    CAMERA_SMARTPHONE = "camera_smartphone"
    FAX = "fax"
    UNKNOWN = "unknown"


class DomainLevel1(str, Enum):
    """Primary domain codes (Axis 1 from document-type-taxonomy.md)."""

    TAX = "TAX"
    LEGAL = "LEG"
    FINANCIAL = "FIN"
    TECHNICAL = "TEC"
    SCIENTIFIC = "SCI"
    ADMINISTRATIVE = "ADM"
    MEDICAL = "MED"
    EDUCATIONAL = "EDU"
    PERSONAL = "PER"
    UNKNOWN = "UNK"


class ResolutionCategory(str, Enum):
    """Resolution category bins."""

    LOW = "low_<150"
    MEDIUM = "medium_150-299"
    STANDARD = "standard_300"
    HIGH = "high_>300"


class EnrichmentTier(str, Enum):
    """Enrichment source tier for provenance tracking."""

    TIER_0_EXACT = "tier_0_exact"  # Dataset IS 100% this content type
    TIER_1_ANNOTATION = "tier_1_annotation"  # Derived from COCO/JSON annotations
    TIER_2_MODEL = "tier_2_model"  # DocLayout-YOLO inference
    TIER_3_HEURISTIC = "tier_3_heuristic"  # Dataset-level defaults (fallback)


# =============================================================================
# Dataset Configurations
# =============================================================================

# Tier 0 datasets: content type is exact by construction
TIER_0_DATASETS = {
    # Tables (100% table content)
    "tablebank": {"has_table": True, "text_scope": "page"},
    "pubtabnet": {"has_table": True, "text_scope": "page"},
    "fintabnet": {"has_table": True, "text_scope": "page"},
    # Formulas (100% formula content)
    "im2latex": {"has_formula": True, "text_scope": "phrase"},
    "mathverse": {"has_formula": True, "text_scope": "paragraph"},
    "maths_handwriting": {
        "has_formula": True,
        "has_handwriting": True,
        "text_scope": "phrase",
    },
    "hasyv2": {"has_formula": True, "has_handwriting": True, "text_scope": "character"},
    # Handwriting (100% handwritten content)
    "signatr6k": {"has_signature": True, "has_handwriting": True, "text_scope": "word"},
    "nist_sd19": {"has_handwriting": True, "text_scope": "page"},
    "pucit_ohul": {"has_handwriting": True, "text_scope": "word"},
}

# Datasets with COCO annotations (Tier 1)
TIER_1_DATASETS = {"doclaynet", "tablebank", "funsd"}

# Dataset configurations with known metadata mappings
DATASET_CONFIGS: dict[str, dict[str, Any]] = {
    # === Benchmark datasets ===
    "diqa-5000": {
        "path": BENCHMARK_ONLY / "diqa-5000",
        "pattern": "**/*.jpg",  # All images: ori (original) + res (enhanced)
        "capture_method": CaptureMethod.UNKNOWN,  # Per-image: ori=camera_smartphone, res=synthetic (set by parser)
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "mos_file": "train/train.csv",  # CSV with MOS scores
        "original_labels_parser": "parse_diqa_labels",
        "is_multilingual": True,  # 73% zh, 17% en, 10% mixed - per-image language detection required
        # No default_language_code: multilingual dataset, per-image detection via OpenLID/LLM
        # No default_script_name: mixed CJK (Hans) + Latin scripts
    },
    "smartdoc-qa": {
        "path": BENCHMARK_ONLY / "smartdoc-qa",  # Fixed: hyphen not underscore
        "pattern": "Dataset SmartDoc-QA/Captured_Images/**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "original_labels_parser": "parse_smartdoc_labels",
        "default_language_code": "en",  # Administrative documents
        "default_script_name": "Latn",
    },
    "dibco": {
        "path": BENCHMARK_ONLY / "dibco",
        "pattern": "DIBCO/**/*.*",  # Fixed: images in DIBCO/ subdirectory
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "original_labels_parser": "parse_dibco_labels",
        "has_handwriting": True,  # Historical docs with handwriting
    },
    "omnidocbench": {
        "path": BENCHMARK_ONLY / "omnidocbench",
        "pattern": "extracted_images/*.png",  # After extraction
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "arrow_format": True,  # Special handling needed
        "original_labels_parser": "parse_omnidocbench_labels",
    },
    # === Base training datasets ===
    "tobacco800": {
        "path": BASE_DATA / "degraded/tobacco800",
        "pattern": "images/*.png",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        "default_language_code": "en",  # US tobacco company documents
        "default_script_name": "Latn",
    },
    "historical_degraded": {
        "path": BASE_DATA / "degraded/historical_degraded",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "has_handwriting": True,
    },
    "rvl_cdip": {
        "path": BASE_DATA / "documents/rvl_cdip",
        "pattern": "images/*.jpg",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        "original_labels_parser": "parse_rvl_cdip_labels",
        "default_language_code": "en",  # US tobacco industry documents
        "default_script_name": "Latn",
    },
    "doclaynet": {
        "path": BASE_DATA / "documents/doclaynet",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "original_labels_parser": "parse_doclaynet_labels",
        "has_coco_annotations": True,
    },
    "nist-sd2": {
        "path": BASE_DATA / "forms/nist-sd2",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        "has_table": True,
        "has_handwriting": True,
        "has_signature": True,
        "original_labels_parser": "parse_nist_sd2_labels",
        "default_language_code": "en",  # US IRS tax forms
        "default_script_name": "Latn",
    },
    "nist_sd6": {
        "path": BASE_DATA / "forms/nist_sd6",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.TAX,
        "has_human_mos": False,
        "has_table": True,
        "original_labels_parser": "parse_nist_sd6_labels",
        "default_language_code": "en",  # US IRS tax forms
        "default_script_name": "Latn",
    },
    "funsd": {
        "path": BASE_DATA / "forms/funsd",
        "pattern": "*/images/*.png",  # Both train and test splits
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        "original_labels_parser": "parse_funsd_labels",
        "has_table": True,
        "has_handwriting": True,
        "has_signature": True,
        "default_language_code": "en",  # US tobacco industry forms
        "default_script_name": "Latn",
    },
    "funsd_plus": {
        "path": BASE_DATA / "forms/funsd_plus",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        "has_table": True,
        "has_handwriting": True,
        "has_signature": True,
        "original_labels_parser": "parse_funsd_plus_labels",
        "default_language_code": "en",  # Extended FUNSD, US tobacco forms
        "default_script_name": "Latn",
    },
    "sroie": {
        "path": BASE_DATA / "forms/sroie_icdar2019",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        "has_table": True,
        "original_labels_parser": "parse_sroie_labels",
        "default_language_code": "en",  # Malaysian receipts, primarily English text
        "default_script_name": "Latn",
    },
    "tablebank": {
        "path": BASE_DATA / "tables/tablebank",
        "pattern": "**/images/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.SCIENTIFIC,
        "has_human_mos": False,
        "original_labels_parser": "parse_tablebank_labels",
        "has_coco_annotations": True,
        # Tier 0: 100% tables by definition
        "has_table": True,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
        # TableBank is multilingual but predominantly English (arXiv/Word sources)
        "default_language_code": "en",
        "default_script_name": "Latn",
    },
    "pubtabnet": {
        "path": BASE_DATA / "tables/pubtabnet",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.SCIENTIFIC,
        "has_human_mos": False,
        # Tier 0: 100% tables by definition
        "has_table": True,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
        "original_labels_parser": "parse_pubtabnet_labels",
        "default_language_code": "en",  # PubMed scientific articles
        "default_script_name": "Latn",
    },
    "fintabnet": {
        "path": BASE_DATA / "tables/fintabnet",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        # Tier 0: 100% tables by definition
        "has_table": True,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
        "original_labels_parser": "parse_fintabnet_labels",
        "default_language_code": "en",  # US Fortune 500 financial reports
        "default_script_name": "Latn",
    },
    "nist_sd19": {
        "path": BASE_DATA / "handwriting/nist-sd19",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.PERSONAL,
        "has_human_mos": False,
        # Tier 0: 100% handwriting by definition
        "has_table": False,
        "has_formula": False,
        "has_handwriting": True,
        "has_signature": False,
        "original_labels_parser": "parse_nist_sd19_labels",
        "default_language_code": "en",  # US handwriting database
        "default_script_name": "Latn",
    },
    "signatr6k": {
        "path": BASE_DATA / "handwriting/signatr6k",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.PERSONAL,
        "has_human_mos": False,
        "original_labels_parser": "parse_signatr_labels",
        # Tier 0: 100% signatures by definition
        "has_table": False,
        "has_formula": False,
        "has_handwriting": True,
        "has_signature": True,
        "default_language_code": "en",  # Thomson Reuters legal (Canada/US)
        "default_script_name": "Latn",
    },
    "maths_handwriting": {
        "path": BASE_DATA / "handwriting/maths_handwriting",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        # Tier 0: 100% handwritten formulas by definition
        "has_table": False,
        "has_formula": True,
        "has_handwriting": True,
        "has_signature": False,
        "default_language_code": "zxx",  # No linguistic content (math symbols)
        "default_script_name": "Zmth",  # Mathematical notation
    },
    "hasyv2": {
        "path": BASE_DATA / "handwriting/hasy/hasy-data",
        "pattern": "*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        # Tier 0: 100% handwritten mathematical symbols by definition
        "has_table": False,
        "has_formula": True,
        "has_handwriting": True,
        "has_signature": False,
        "default_language_code": "zxx",  # No linguistic content (math symbols)
        "default_script_name": "Zmth",  # Mathematical notation
        "text_scope": "character",  # Single character per image
        "original_labels_parser": "parse_hasyv2_labels",
    },
    "im2latex": {
        "path": BASE_DATA / "formulas/im2latex",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.SCIENTIFIC,
        "has_human_mos": False,
        # Tier 0: 100% formulas by definition
        "has_table": False,
        "has_formula": True,
        "has_handwriting": False,
        "has_signature": False,
        "original_labels_parser": "parse_im2latex_labels",
        "default_language_code": "en",  # arXiv papers (English source)
        "default_script_name": "Latn",
    },
    "mathverse": {
        "path": BASE_DATA / "formulas/mathverse",
        "pattern": "images/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        # Tier 0: 100% formulas by definition
        "has_table": False,
        "has_formula": True,
        "has_handwriting": False,
        "has_signature": False,
        "original_labels_parser": "parse_mathverse_labels",
        "default_language_code": "en",  # English math problems
        "default_script_name": "Latn",
    },
    "multimodal_textbook": {
        "path": BASE_DATA / "educational/multimodal_textbook",
        "pattern": "example_data/sample_100_images/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
    },
    # === NEW: Camera-captured dataset ===
    "realdae": {
        "path": BASE_DATA / "camera_captured/realdae",
        "pattern": "**/*_in.jpg",  # Only input images, not GT
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "has_paired_gt": True,  # Has pixel-aligned ground truth
        "original_labels_parser": "parse_realdae_labels",
        # Mixed content, needs YOLO detection
        "default_language_code": "en",  # Document restoration benchmark
        "default_script_name": "Latn",
    },
    # === NEW: OCR-Quality with human scores ===
    "ocr_quality": {
        "path": BASE_DATA / "ocr_quality",
        "pattern": "pics/*.png",
        "capture_method": CaptureMethod.UNKNOWN,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,  # Has human quality scores 1-4
        "original_labels_parser": "parse_ocr_quality_labels",
    },
    # === NEW: Multilingual/Script Detection Datasets ===
    "pucit_ohul": {
        "path": BASE_DATA / "language/pucit-ohul",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        "has_handwriting": True,
        "iso639_language": "ur",  # Urdu
        "iso15924_script": "Arab",  # Arabic script
        "text_scope": "word",  # Word-level handwriting samples
        "original_labels_parser": "parse_pucit_ohul_labels",
    },
    "muharaf": {
        "path": BASE_DATA / "handwriting/muharaf/public",
        "pattern": "**/*",  # Both .jpg (pages) and .png (lines); suffix filter at scan
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.PERSONAL,  # Personal letters/manuscripts
        "has_human_mos": False,
        "has_handwriting": True,
        "has_signature": True,  # Some regions marked as signature-mark
        "iso639_language": "ar",  # Arabic
        "iso15924_script": "Arab",  # Arabic script
        "text_scope": "line",  # Line-level transcriptions
        "original_labels_parser": "parse_muharaf_labels",
    },
    "multilingual_scripts": {
        "path": BASE_DATA / "language/multilingual_scripts",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.UNKNOWN,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "text_scope": "mixed",  # Various script samples
        "original_labels_parser": "parse_multilingual_scripts_labels",
    },
    "midv500": {
        "path": BASE_DATA / "language/midv500_data/midv500",
        "pattern": "**/*.tif",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.PERSONAL,  # ID documents
        "has_human_mos": False,
        "text_scope": "page",
        "original_labels_parser": "parse_midv500_labels",
    },
    # === Unlabeled real-world documents (for inference/testing) ===
    "bhutan_financial": {
        "path": BASE_DATA / "documents/bhutan_financial",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        "has_table": True,
        "text_scope": "page",
        "paper_size": "A4",
        # No label parser - real-world government docs (tax report, national
        # financial document 2024) without ground truth labels
    },
    # === Phase 10B Script Detection Datasets ===
    "mdiw13": {
        "path": BASE_DATA / "language/mdiw13",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.UNKNOWN,  # Mixed domains (newspapers, letters)
        "has_human_mos": False,
        "has_handwriting": True,  # Includes handwritten letters
        "text_scope": "word",  # Word-level segmentation
        # Multi-script: 13 scripts (Arabic, Bengali, Gujarati, Gurmukhi,
        # Devanagari, Japanese, Kannada, Malayalam, Oriya, Latin, Tamil, Telugu, Thai)
        "original_labels_parser": "parse_mdiw13_labels",
    },
    "cc_ocr": {
        "path": BASE_DATA / "language/cc-ocr",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.UNKNOWN,  # Mixed (41% real-world, 59% synthetic)
        "domain": DomainLevel1.UNKNOWN,  # Multiple domains
        "has_human_mos": False,
        "text_scope": "mixed",  # Various scopes (scene text, documents)
        # CJK Mixed: Chinese (Simplified + Traditional), English, Multilingual
        "original_labels_parser": "parse_cc_ocr_labels",
    },
    "tibhcr": {
        "path": BASE_DATA / "language/huggingface_downloads/TibHCR/TibHCR",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.PERSONAL,  # Handwritten characters
        "has_human_mos": False,
        "has_handwriting": True,
        "iso15924_script": "Tibt",  # Tibetan script
        "text_scope": "word",  # Character-level samples
        "original_labels_parser": "parse_tibhcr_labels",
    },
    "mlt19": {
        "path": BASE_DATA / "language/mlt19",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        "domain": DomainLevel1.UNKNOWN,  # Scene text from various sources
        "has_human_mos": False,
        "text_scope": "phrase",  # Scene text instances
        # 10 languages: Arabic, Bangla, Chinese, Japanese, Korean, Latin,
        # Hindi, and 3 others
        "original_labels_parser": "parse_mlt19_labels",
    },
    # === HierText (hierarchical scene text) ===
    "hiertext": {
        "path": BASE_DATA / "text_detection/hiertext",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.UNKNOWN,  # Natural scene images (Open Images)
        "domain": DomainLevel1.UNKNOWN,  # Scene text from various sources
        "has_human_mos": False,
        "has_handwriting": True,  # Includes handwriting legibility labels
        "text_scope": "word",  # Word-level hierarchical annotations
        # TODO: Add parse_hiertext_labels for JSONL ground truth
    },
    # === Invoices-KG (Kaggle invoice OCR) ===
    "invoices-kg": {
        "path": BASE_DATA / "forms/invoices_kaggle",
        "pattern": "*/images/*.jpg",  # Both train and val splits
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        "has_table": True,  # Invoice items table structure
        "default_language_code": "en",  # English invoices
        "default_script_name": "Latn",
        # TODO: Add parse_invoices_kg_labels for annotations.json
    },
    # === Additional Kaggle Script Detection Datasets ===
    "arabic_docs_ocr": {
        "path": BASE_DATA / "language/arabic_docs_ocr",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.UNKNOWN,  # Mixed documents
        "has_human_mos": False,
        "iso639_language": "ar",  # Arabic
        "iso15924_script": "Arab",  # Arabic script
        "text_scope": "page",
        "original_labels_parser": "parse_arabic_docs_labels",
    },
    "hindi_ocr_synthetic": {
        "path": BASE_DATA / "language/hindi_ocr_synthetic",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.BORN_DIGITAL,  # Synthetic
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        "iso639_language": "hi",  # Hindi
        "iso15924_script": "Deva",  # Devanagari
        "text_scope": "line",  # Line-level images
        "original_labels_parser": "parse_hindi_synthetic_labels",
    },
    "nepali_handwritten": {
        "path": BASE_DATA / "language/nepali_handwritten",
        "pattern": "**/*",  # Mix of .jpg, .jpeg, .png; suffix filter at scan
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        "has_handwriting": True,
        "iso639_language": "ne",  # Nepali
        "iso15924_script": "Deva",  # Devanagari
        "text_scope": "word",  # Word-level samples
        "original_labels_parser": "parse_nepali_handwritten_labels",
    },
    "yarmouk_ocr": {
        "path": BASE_DATA / "language/yarmouk",  # Converted from PDFs
        "pattern": "**/*.png",  # PNG format from conversion
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.UNKNOWN,  # Mixed Arabic documents
        "has_human_mos": False,
        "iso639_language": "ar",  # Arabic
        "iso15924_script": "Arab",  # Arabic script
        "text_scope": "page",
        "original_labels_parser": "parse_yarmouk_labels",
    },
    # === Script Identification Datasets ===
    "cvsi": {
        "path": BASE_DATA / "language/cvsi",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        "domain": DomainLevel1.UNKNOWN,  # Scene text
        "has_human_mos": False,
        "text_scope": "word",  # Word-level script identification
        # 10 Indic scripts: Arabic, Bengali, English, Gujrathi, Hindi,
        # Kannada, Oriya, Punjabi, Tamil, Telegu
        "original_labels_parser": "parse_cvsi_labels",
    },
    "siw13": {
        "path": BASE_DATA / "language/siw13",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        "domain": DomainLevel1.UNKNOWN,  # Scene text
        "has_human_mos": False,
        "text_scope": "word",  # Word-level script identification
        # 13 scripts: Arabic, Cambodian, Chinese, English, Greek, Hebrew,
        # Japanese, Kannada, Korean, Mongolian, Russian, Thai, Tibetan
        "original_labels_parser": "parse_siw13_labels",
    },
    "mle2e": {
        "path": BASE_DATA / "language/mle2e",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        "domain": DomainLevel1.UNKNOWN,  # Scene text
        "has_human_mos": False,
        "text_scope": "line",  # Text line level
        # 4 scripts: Latin, Chinese, Kannada, Korean (Hangul)
        "original_labels_parser": "parse_mle2e_labels",
    },
    # === OHR-Bench (Arrow format benchmark) ===
    "ohr-bench": {
        "path": BENCHMARK_ONLY / "ohr-bench",
        "pattern": "extracted_images/**/*.png",  # After extraction (includes subdirs)
        "capture_method": CaptureMethod.UNKNOWN,
        "domain": DomainLevel1.UNKNOWN,  # Mixed benchmark
        "has_human_mos": False,
        "arrow_format": True,  # Needs extraction like omnidocbench
        "original_labels_parser": "parse_ohr_bench_labels",
    },
    # === FinanceBench (SEC Financial Documents) ===
    "financebench": {
        "path": BENCHMARK_ONLY / "financebench",
        "pattern": "extracted_images/*.png",  # After PDF extraction
        "capture_method": CaptureMethod.BORN_DIGITAL,  # SEC filings
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        "has_table": True,  # SEC filings contain tables
        "original_labels_parser": "parse_financebench_labels",
        "default_language_code": "en",  # US SEC filings
        "default_script_name": "Latn",
    },
}

# NOTE: Removed non-existent datasets:
# - "live": Not downloaded, would need LIVE IQA database
# - "csiq": Not downloaded, would need CSIQ database


# =============================================================================
# Data Classes (Metadata Schema Implementation)
# =============================================================================


@dataclass
class OriginalFileMetadata:
    """Immutable file metadata extracted at ingestion."""

    format: str
    width_px: int
    height_px: int
    channels: int
    bit_depth: int
    file_size_bytes: int
    dpi: int | None = None
    color_space: str | None = None


@dataclass
class OriginalLabels:
    """Immutable labels from source dataset (preserved exactly).

    See docs/schema/LABEL_MAPPING_SPECIFICATION.md for field mappings.
    """

    # === Quality Scores (dataset-specific) ===
    # DIQA-5000: 3-dimension quality assessment (1-5 scale, higher is better)
    diqa_overall: float | None = None  # Overall quality MOS
    diqa_sharpness: float | None = None  # Sharpness quality MOS
    diqa_color_fidelity: float | None = None  # Color fidelity MOS
    diqa_original_image: str | None = None  # Reference to original (ori) image
    # Legacy field (alias for diqa_overall, for backward compatibility)
    diqa_mos: float | None = None
    diqa_mos_std: float | None = None  # Standard deviation (if available)
    diqa_distortion_type: str | None = None  # Distortion category (if available)

    # OCR-Quality human scores (1-4 scale, 1=best - INVERTED!)
    ocr_quality_score: int | None = None
    ocr_quality_source: str | None = None
    ocr_quality_text: str | None = None

    smartdoc_mos: float | None = None
    smartdoc_capture_device: str | None = None
    smartdoc_lighting: str | None = None

    # === Layout Annotations (COCO format) ===
    doclaynet_annotations: list[dict] | None = None
    tablebank_annotations: list[dict] | None = None
    funsd_annotations: list[dict] | None = None

    # === Handwriting Datasets ===
    signatr_writer_id: str | None = None
    signatr_is_genuine: bool | None = None
    writer_id: str | None = None  # Generic writer ID (IAM, NIST-SD19)
    transcription: str | None = None  # Ground truth text

    # === Multilingual/Script Datasets ===
    language_code: str | None = None  # Original language label (e.g., "ur", "jp")
    script_name: str | None = (
        None  # Original script label (e.g., "Arabic", "Devanagari")
    )
    iso15924_script_code: str | None = (
        None  # Standardized ISO 15924 code (e.g., "Arab", "Deva")
    )

    # === Scene Text Datasets (MLT-19 style) ===
    text_instances: list[dict] | None = None

    # === Table Structure (PubTabNet) ===
    table_html: str | None = None
    cell_annotations: list[dict] | None = None

    # === Generic Fallback ===
    raw_labels: dict | None = None


@dataclass
class LayoutDetection:
    """Single layout detection from DocLayout-YOLO or COCO annotations."""

    class_name: str
    bbox: list[float]  # [x1, y1, x2, y2] or [x, y, w, h] depending on source
    confidence: float
    source: str  # "doclayout_yolo", "coco_annotation", etc.


@dataclass
class EnrichmentData:
    """Single enrichment version data."""

    # Capture method detection
    capture_method: str | None = None
    capture_confidence: float | None = None
    capture_detection_method: str | None = None

    # Resolution analysis (aligned with taxonomy v4.0)
    resolution_dpi: int | None = None
    resolution_category: str | None = None
    resolution_pixels: tuple[int, int] | None = None

    # Domain classification
    domain_level1: str | None = None
    domain_level2: str | None = None
    domain_level3: str | None = None
    domain_confidence: float | None = None

    # Structure analysis
    text_density: str | None = None
    layout_type: str | None = None
    element_types: list[str] | None = None

    # Quality/degradation (list of detected degradations)
    quality_overall: float | None = None
    degradations: list[dict] | None = None

    # Language detection (legacy fields)
    primary_language: str | None = None
    language_confidence: float | None = None
    script_type: str | None = None

    # Language/Script (ISO-compliant, added v2.1)
    iso639_language: str | None = None  # ISO 639-1/3 code
    iso15924_script: str | None = None  # ISO 15924 script code
    script_family: str | None = None  # Script family (e.g., "latin", "cjk", "arabic")
    bcp47_tag: str | None = None  # Full BCP 47 language tag

    # Text Scope (added v2.1)
    text_scope: str | None = (
        None  # character, word, phrase, sentence, line, paragraph, page, document
    )
    text_scope_content_type: str | None = (
        None  # printed, handwritten, mixed, scene_text, synthetic
    )
    text_scope_estimated_chars: int | None = None
    text_scope_estimated_words: int | None = None
    text_scope_detection_method: str | None = (
        None  # dataset_metadata, ocr_output, dimension_heuristic
    )

    # Paper Size (ISO 216, added v2.1)
    paper_size: str | None = None  # A4, Letter, etc.
    paper_size_standard: str | None = None  # iso, ansi, jis, custom
    paper_size_orientation: str | None = None  # portrait, landscape
    paper_size_confidence: float | None = None
    paper_size_is_exact: bool | None = None

    # Dataset Source (added v2.1)
    dataset_short_code: str | None = (
        None  # Standardized short code from DATASET_REGISTRY
    )

    # LLM perceptual scores (added in later versions)
    llm_predicted_mos: float | None = None
    llm_predicted_normalized: float | None = None
    llm_prediction_confidence: float | None = None
    llm_model_name: str | None = None

    # Content flags with provenance
    has_table: bool | None = None
    has_formula: bool | None = None
    has_handwriting: bool | None = None
    has_signature: bool | None = None
    has_figure: bool | None = None
    content_flags_tier: str | None = None  # EnrichmentTier value
    content_flags_source: str | None = None  # Model name or "coco_annotation"

    # Layout detections (for Tier 1/2)
    layout_detections: list[dict] | None = None

    # --- v2.1.0 additions below ---

    # Geometric attributes (orientation, skew) -- v2.1
    orientation_class: int | None = None  # 0/90/180/270
    orientation_confidence: float | None = None
    orientation_corrected: bool | None = None
    orientation_detection_method: str | None = None
    skew_angle_degrees: float | None = None  # exact angle +-180
    skew_confidence: float | None = None
    skew_detection_method: str | None = None

    # Physical degradation (shadow, warping, watermark) -- v2.1
    shadow_severity: float | None = None  # 0-1
    shadow_type: str | None = None
    shadow_confidence: float | None = None
    warping_severity: float | None = None  # 0-1
    warping_type: str | None = None
    warping_confidence: float | None = None
    watermark_severity: float | None = None  # 0-1
    watermark_type: str | None = None
    watermark_confidence: float | None = None
    fuzzy_scan_score: float | None = None  # 0-1

    # ML IQA 6-dim scores -- v2.1
    ml_iqa_blur: float | None = None  # 0-1
    ml_iqa_noise: float | None = None  # 0-1
    ml_iqa_contrast: float | None = None  # 0-1
    ml_iqa_compression: float | None = None  # 0-1
    ml_iqa_skew: float | None = None  # 0-1
    ml_iqa_overall: float | None = None  # 0-1
    ml_iqa_model_name: str | None = None
    ml_iqa_model_version: str | None = None

    # Code detection -- v2.1 (ContentFlags + StructureInfo in JSON schema)
    has_code: bool | None = None
    code_confidence: float | None = None  # 0-1
    code_language: str | None = None
    code_rendering_style: str | None = None

    # Resolution enhancement -- v2.1
    character_height_px: float | None = None
    resolution_quality_score: float | None = None  # 0-1
    effective_dpi: int | None = None

    # Image properties (color mode, document age) -- v2.1
    color_mode: str | None = None  # "color", "grayscale", "binarized"
    document_age: str | None = None  # "modern", "aged", "historical"

    # OCR impact (future: populated by Project B) -- v2.1
    ocr_engine: str | None = None
    ocr_engine_version: str | None = None
    ocr_char_error_rate: float | None = None
    ocr_word_error_rate: float | None = None
    ocr_quality_before_correction: float | None = None
    ocr_quality_after_correction: float | None = None


@dataclass
class EnrichmentVersion:
    """Single version of enrichment with provenance and reproducibility."""

    version: int
    created_at: str
    created_by: str
    method: (
        str  # "tier_0_exact", "tier_1_annotation", "tier_2_model", "tier_3_heuristic"
    )
    description: str
    data: EnrichmentData = field(default_factory=EnrichmentData)

    # Reproducibility fields (consensus recommendation)
    git_sha: str | None = None
    model_checkpoint: str | None = None
    config_hash: str | None = None
    script_version: str | None = None


@dataclass
class SampleMetadata:
    """Complete metadata record for a single sample."""

    # Identity
    id: str
    file_hash: str

    # Source information (immutable)
    dataset_name: str
    dataset_version: str
    original_path: str
    original_filename: str
    download_date: str

    # Original labels (immutable)
    original_labels: OriginalLabels

    # Original file metadata (immutable)
    original_file: OriginalFileMetadata

    # Fields with defaults must come after non-default fields
    split: str = "unknown"  # train, test, val, unknown

    # Enrichment history (versioned)
    current_version: int = 0
    enrichment_versions: list[EnrichmentVersion] = field(default_factory=list)

    # Record metadata
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    schema_version: str = SCHEMA_VERSION

    def add_enrichment(
        self,
        data: EnrichmentData,
        created_by: str,
        method: str,
        description: str,
        git_sha: str | None = None,
        model_checkpoint: str | None = None,
        config_hash: str | None = None,
    ) -> int:
        """Add new enrichment version. Returns version number."""
        new_version = len(self.enrichment_versions) + 1
        enrichment = EnrichmentVersion(
            version=new_version,
            created_at=datetime.now(UTC).isoformat(),
            created_by=created_by,
            method=method,
            description=description,
            data=data,
            git_sha=git_sha or get_git_sha(),
            model_checkpoint=model_checkpoint,
            config_hash=config_hash,
            script_version=SCRIPT_VERSION,
        )
        self.enrichment_versions.append(enrichment)
        self.current_version = new_version
        return new_version

    def get_current_enrichment(self) -> EnrichmentData | None:
        """Get the current active enrichment data."""
        if not self.enrichment_versions or self.current_version == 0:
            return None
        # Find the version matching current_version
        for v in self.enrichment_versions:
            if v.version == self.current_version:
                return v.data
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "file_hash": self.file_hash,
            "source": {
                "dataset_name": self.dataset_name,
                "dataset_version": self.dataset_version,
                "original_path": self.original_path,
                "original_filename": self.original_filename,
                "download_date": self.download_date,
                "split": self.split,
            },
            "original_labels": {
                k: v for k, v in self.original_labels.__dict__.items() if v is not None
            },
            "original_file": self.original_file.__dict__,
            "enrichments": {
                "current_version": self.current_version,
                "versions": [
                    {
                        "version": v.version,
                        "created_at": v.created_at,
                        "created_by": v.created_by,
                        "method": v.method,
                        "description": v.description,
                        "git_sha": v.git_sha,
                        "model_checkpoint": v.model_checkpoint,
                        "config_hash": v.config_hash,
                        "script_version": v.script_version,
                        "data": {
                            k: val
                            for k, val in v.data.__dict__.items()
                            if val is not None
                        },
                    }
                    for v in self.enrichment_versions
                ],
            },
            "record_meta": {
                "created_at": self.created_at,
                "schema_version": self.schema_version,
            },
        }


# =============================================================================
# Utility Functions
# =============================================================================


def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA256 hash of file (first 64KB for speed)."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        chunk = f.read(chunk_size)
        sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def extract_file_metadata(image_path: Path) -> OriginalFileMetadata:
    """Extract image file metadata."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            mode = img.mode

            # Determine channels from mode
            channels_map = {
                "1": 1,
                "L": 1,
                "P": 1,
                "RGB": 3,
                "RGBA": 4,
                "CMYK": 4,
                "LAB": 3,
            }
            channels = channels_map.get(mode, 3)

            # Try to get DPI from EXIF or info
            dpi = None
            if "dpi" in img.info:
                dpi_info = img.info["dpi"]
                if isinstance(dpi_info, tuple):
                    dpi = int(dpi_info[0])
                elif isinstance(dpi_info, (int, float)):
                    dpi = int(dpi_info)

            return OriginalFileMetadata(
                format=img.format or image_path.suffix.lstrip(".").upper(),
                width_px=width,
                height_px=height,
                channels=channels,
                bit_depth=8,  # Default, could be enhanced
                file_size_bytes=image_path.stat().st_size,
                dpi=dpi,
                color_space=mode,
            )
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {image_path}: {e}")
        return OriginalFileMetadata(
            format=image_path.suffix.lstrip(".").upper(),
            width_px=0,
            height_px=0,
            channels=0,
            bit_depth=0,
            file_size_bytes=image_path.stat().st_size if image_path.exists() else 0,
        )


def categorize_dpi(dpi: int | None) -> ResolutionCategory:
    """Categorize DPI into resolution bins."""
    if dpi is None:
        return ResolutionCategory.STANDARD  # Default assumption
    if dpi < 150:
        return ResolutionCategory.LOW
    if dpi < 300:
        return ResolutionCategory.MEDIUM
    if dpi == 300:
        return ResolutionCategory.STANDARD
    return ResolutionCategory.HIGH


# =============================================================================
# DocLayout-YOLO Integration
# =============================================================================

# Global model cache
_YOLO_MODEL = None


def load_doclayout_yolo():
    """Load DocLayout-YOLO model (lazy loading, cached).

    Loads the DocStructBench variant of DocLayout-YOLO (10 document
    layout classes: title, plain text, abandon, figure, figure_caption,
    table, table_caption, table_footnote, isolate_formula, formula_caption).

    Loading strategy (in order):
    1. Local .pt files at known project paths
    2. HuggingFace cached model via huggingface_hub + doclayout_yolo
    3. Direct HuggingFace download + doclayout_yolo

    Returns:
        Loaded YOLOv10 model instance or None if loading fails.
    """
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    HF_REPO = "juliozhao/DocLayout-YOLO-DocStructBench"
    HF_FILENAME = "doclayout_yolo_docstructbench_imgsz1024.pt"

    # Strategy 1: Try local model files
    local_paths = [
        PROJECT_ROOT / "models" / "doclayout_yolo_docstructbench.pt",
        PROJECT_ROOT / "05_models" / "doclayout_yolo.pt",
        Path.home() / ".cache" / "doclayout_yolo.pt",
    ]

    for model_path in local_paths:
        if model_path.exists():
            try:
                from doclayout_yolo import YOLOv10

                logger.info(f"Loading DocLayout-YOLO from {model_path}")
                _YOLO_MODEL = YOLOv10(str(model_path))
                return _YOLO_MODEL
            except Exception as e:
                logger.warning(f"Failed to load from {model_path}: {e}")

    # Strategy 2: Download from HuggingFace and load with doclayout_yolo
    try:
        from doclayout_yolo import YOLOv10
        from huggingface_hub import hf_hub_download

        logger.info(f"Loading DocLayout-YOLO from HuggingFace: {HF_REPO}")
        model_path = hf_hub_download(repo_id=HF_REPO, filename=HF_FILENAME)
        _YOLO_MODEL = YOLOv10(model_path)
        logger.info(
            f"DocLayout-YOLO loaded: {len(_YOLO_MODEL.names)} classes "
            f"({list(_YOLO_MODEL.names.values())[:3]}...)"
        )
        return _YOLO_MODEL
    except ImportError as e:
        logger.warning(f"Required packages not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to load DocLayout-YOLO from HuggingFace: {e}")

    logger.warning(
        "DocLayout-YOLO not available. Install doclayout-yolo and "
        "huggingface-hub packages, or place model at "
        "models/doclayout_yolo_docstructbench.pt"
    )
    return None


def run_doclayout_yolo(
    image_path: Path, conf_threshold: float = 0.25
) -> dict[str, Any]:
    """Run DocLayout-YOLO inference for content detection.

    Returns:
        dict with has_table, has_formula, has_figure, layout_detections
    """
    model = load_doclayout_yolo()
    if model is None:
        return {
            "has_table": None,
            "has_formula": None,
            "has_figure": None,
            "has_handwriting": None,
            "layout_detections": [],
            "error": "Model not available",
        }

    try:
        results = model(str(image_path), conf=conf_threshold, verbose=False)

        detections = {
            "has_table": False,
            "has_formula": False,
            "has_figure": False,
            "has_handwriting": False,  # YOLO may not detect this
            "layout_detections": [],
        }

        for r in results:
            for box in r.boxes:
                class_id = int(box.cls)
                class_name = model.names.get(class_id, f"class_{class_id}")
                confidence = float(box.conf)

                detection = {
                    "class_name": class_name,
                    "bbox": box.xyxy[0].tolist(),
                    "confidence": confidence,
                    "source": "doclayout_yolo",
                }
                detections["layout_detections"].append(detection)

                # Map class names to content flags
                class_lower = class_name.lower()
                if "table" in class_lower:
                    detections["has_table"] = True
                elif "formula" in class_lower or "equation" in class_lower:
                    detections["has_formula"] = True
                elif (
                    "picture" in class_lower
                    or "figure" in class_lower
                    or "image" in class_lower
                ):
                    detections["has_figure"] = True

        return detections

    except Exception as e:
        logger.warning(f"DocLayout-YOLO inference failed for {image_path}: {e}")
        return {
            "has_table": None,
            "has_formula": None,
            "has_figure": None,
            "has_handwriting": None,
            "layout_detections": [],
            "error": str(e),
        }


# =============================================================================
# Label Parsers (Per-Dataset Original Label Extraction)
# =============================================================================


def parse_diqa_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse DIQA-5000 labels (3-dimension MOS scores from CSV).

    DIQA-5000 CSV format:
    - res: restored/enhanced image filename (what we match against)
    - ori: original image filename (reference)
    - overall: overall quality MOS (1-5 scale, higher is better)
    - sharpness: sharpness quality MOS (1-5 scale)
    - color_fidelity: color fidelity MOS (1-5 scale)

    DIQA-5000 structure: {split}/{ori|res}/{split}_{ori|res}_{id}.jpg
    - ori/ images: camera-captured real-world documents (camera_smartphone)
    - res/ images: algorithmically enhanced versions (synthetic)

    This captures both the 3-dimension scores for ensemble training
    and maintains backward compatibility with diqa_mos (= overall).
    """
    labels = OriginalLabels()
    labels.raw_labels = {}

    # Determine which split based on image path
    # Images are in train/ori/, val/ori/, test/ori/ subdirectories
    image_name = image_path.name
    path_str = str(image_path)
    split = None
    for s in ["train", "val", "test"]:
        if f"/{s}/" in path_str:
            split = s
            break

    # Store split in raw_labels for downstream extraction
    if split:
        labels.raw_labels["split"] = split

    # Determine capture_method from ori/res folder
    # ori/ = camera-captured (DocIQ paper: "using a specified mobile phone")
    # res/ = algorithmically enhanced (synthetic restoration)
    if "/ori/" in path_str:
        labels.raw_labels["capture_method"] = "camera_smartphone"
    elif "/res/" in path_str:
        labels.raw_labels["capture_method"] = "synthetic"

    # Try to find and parse the appropriate CSV file
    csv_files = ["train/train.csv", "val/val.csv", "test/test.csv"]
    if split:
        # Prioritize the matching split
        csv_files = [f"{split}/{split}.csv"] + [f for f in csv_files if split not in f]

    for csv_file in csv_files:
        csv_path = dataset_path / csv_file
        if csv_path.exists():
            try:
                import csv

                with open(csv_path, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Match by 'res' (restored image) filename
                        # DIQA-5000 uses res/ori pairs
                        if row.get("res") == image_name:
                            # 3-dimension quality scores
                            if "overall" in row:
                                labels.diqa_overall = float(row["overall"])
                                labels.diqa_mos = float(
                                    row["overall"]
                                )  # Backward compat
                            if "sharpness" in row:
                                labels.diqa_sharpness = float(row["sharpness"])
                            if "color_fidelity" in row:
                                labels.diqa_color_fidelity = float(
                                    row["color_fidelity"]
                                )
                            if "ori" in row:
                                labels.diqa_original_image = row["ori"]
                            return labels  # Found match, return early
            except Exception as e:
                logger.debug(f"Failed to parse DIQA labels from {csv_path}: {e}")

    return labels


def parse_smartdoc_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse SmartDoc-QA labels from filename encoding and OCR accuracy files.

    SmartDoc-QA filename format:
        {S|M}_Img_{Android|WP}_D{doc}_L{light}_r{rot}_a{angle}_b{blur}[_Mb#|_Ob#].jpg
        Where:
        - S/M: Phone model identifier
        - Android/WP: Operating system (Android or Windows Phone)
        - D{1-30}: Document number
        - L{1-2}: Lighting condition (1=normal, 2=challenging)
        - r{angle}: Rotation angle in degrees
        - a{angle}: Viewing angle
        - b{blur}: Blur level (-5 to 5, negative = blur, positive = sharp)
        - _Mb#: Motion blur variant
        - _Ob#: Out-of-focus blur variant

    OCR Accuracy files (UNLV-ISRI format):
        - .cacc.txt: Character accuracy report
        - .wacc.txt: Word accuracy report

    The phone folder name indicates the capture device.
    """
    labels = OriginalLabels()

    # Extract phone/device from parent folder structure
    # Structure: Captured_Images/{phone}/Images/{filename}
    image_parts = image_path.parts
    for i, part in enumerate(image_parts):
        if part == "Images" and i > 0:
            labels.smartdoc_capture_device = image_parts[i - 1]
            break

    # Parse filename to extract capture parameters
    filename = image_path.stem  # Without extension
    import re

    # Pattern: {S|M}_Img_{Android|WP}_D{doc}_L{light}_r{rot}_a{angle}_b{blur}[_Mb#|_Ob#]
    pattern = r"^([SM])_Img_(Android|WP)_D(\d+)_L([12])_r(-?\d+)_a(-?\d+)_b(-?\d+)(?:_(Mb|Ob)(\d+))?$"
    match = re.match(pattern, filename)

    if match:
        (
            phone_id,
            os_type,
            doc_num,
            lighting,
            rotation,
            angle,
            blur,
            blur_type,
            blur_level,
        ) = match.groups()

        # Store lighting condition (1=normal, 2=challenging)
        labels.smartdoc_lighting = "normal" if lighting == "1" else "challenging"

        # Store raw capture parameters in raw_labels for reference
        labels.raw_labels = {
            "phone_id": phone_id,
            "os_type": os_type,
            "document_number": int(doc_num),
            "lighting_code": lighting,
            "rotation_degrees": int(rotation),
            "viewing_angle": int(angle),
            "blur_level": int(blur),
            "blur_type": blur_type,  # Mb=motion blur, Ob=out-of-focus blur
            "blur_variant": int(blur_level) if blur_level else None,
        }

    # Look for OCR accuracy files
    # OCR accuracy files are in: Captured_Images/{phone}/OCR_Accuracy_Finereader/{filename}.cacc.txt
    phone_folder = image_path.parent.parent  # Go up from Images/ to phone folder
    ocr_folder = phone_folder / "OCR_Accuracy_Finereader"

    # Try to find character accuracy file
    cacc_path = ocr_folder / f"{filename}.cacc.txt"
    wacc_path = ocr_folder / f"{filename}.wacc.txt"

    if cacc_path.exists():
        try:
            with open(cacc_path) as f:
                content = f.read()
                # Parse UNLV-ISRI format: Look for accuracy percentage
                # Line format: "   99.56%  Accuracy"
                acc_match = re.search(
                    r"^\s*(\d+\.\d+)%\s+Accuracy$", content, re.MULTILINE
                )
                if acc_match:
                    char_accuracy = float(acc_match.group(1))
                    # Convert character accuracy to 1-5 MOS scale
                    # 100% -> 5.0, 90% -> 4.0, 80% -> 3.0, 70% -> 2.0, <70% -> 1.0
                    if char_accuracy >= 99:
                        labels.smartdoc_mos = 5.0
                    elif char_accuracy >= 95:
                        labels.smartdoc_mos = 4.5
                    elif char_accuracy >= 90:
                        labels.smartdoc_mos = 4.0
                    elif char_accuracy >= 85:
                        labels.smartdoc_mos = 3.5
                    elif char_accuracy >= 80:
                        labels.smartdoc_mos = 3.0
                    elif char_accuracy >= 75:
                        labels.smartdoc_mos = 2.5
                    elif char_accuracy >= 70:
                        labels.smartdoc_mos = 2.0
                    else:
                        labels.smartdoc_mos = 1.0 + (char_accuracy / 70.0)

                    # Store raw accuracy in raw_labels
                    if labels.raw_labels is None:
                        labels.raw_labels = {}
                    labels.raw_labels["character_accuracy_percent"] = char_accuracy
        except Exception as e:
            logger.debug(
                f"Failed to parse SmartDoc character accuracy from {cacc_path}: {e}"
            )

    if wacc_path.exists():
        try:
            with open(wacc_path) as f:
                content = f.read()
                # Parse UNLV-ISRI format: Look for word accuracy
                acc_match = re.search(
                    r"^\s*(\d+\.\d+)%\s+Accuracy$", content, re.MULTILINE
                )
                if acc_match:
                    word_accuracy = float(acc_match.group(1))
                    if labels.raw_labels is None:
                        labels.raw_labels = {}
                    labels.raw_labels["word_accuracy_percent"] = word_accuracy
        except Exception as e:
            logger.debug(
                f"Failed to parse SmartDoc word accuracy from {wacc_path}: {e}"
            )

    return labels


def parse_dibco_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse DIBCO labels from directory structure.

    DIBCO (Document Image Binarization Contest) structure:
        DIBCO/{year}/
            DIBCO{year}_Test_images-handwritten/
            DIBCO{year}_Test_images-printed/
            DIBCO{year}-GT-Test-images_handwritten/  (ground truth)
            DIBCO{year}-GT-Test-images_printed/      (ground truth)

    Labels extracted:
        - Competition year (2009-2017)
        - Document type (handwritten or printed)
        - Has paired GT (binary binarization ground truth)

    Note: DIBCO provides binary ground truth images for document binarization
    evaluation, not quality scores. The GT images are pixel-aligned masks.
    """
    labels = OriginalLabels()

    # Extract year and document type from path structure
    path_parts = image_path.parts
    import re

    for part in path_parts:
        # Match year folders: "2009", "2010", etc.
        if re.match(r"^20\d{2}$", part):
            year = part
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["dibco_year"] = int(year)

        # Match folder names to determine document type
        lower_part = part.lower()
        if "handwritten" in lower_part or "handwriting" in lower_part:
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["document_type"] = "handwritten"
            # This is a handwriting dataset
            labels.raw_labels["has_handwriting"] = True
        elif "printed" in lower_part:
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["document_type"] = "printed"
            labels.raw_labels["has_handwriting"] = False

        # Check if this is a ground truth image
        if "gt" in lower_part or "ground" in lower_part:
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["is_ground_truth"] = True

    # Look for corresponding GT image
    # GT images are typically in parallel folder structure
    str_path = str(image_path)
    if "Test_images" in str_path and "-GT-" not in str_path:
        # This is a test image, look for GT
        gt_path_str = str_path.replace("Test_images", "GT-Test-images")
        gt_path = Path(gt_path_str)
        if gt_path.exists():
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["has_ground_truth"] = True
            labels.raw_labels["ground_truth_path"] = str(gt_path)

    return labels


def parse_ocr_quality_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse OCR-Quality labels (human scores 1-4)."""
    labels = OriginalLabels()

    # Load from JSON or Parquet
    json_path = dataset_path / "OCR-Quality.json"
    parquet_path = dataset_path / "OCR-Quality.parquet"

    if parquet_path.exists():
        try:
            table = pq.read_table(parquet_path)
            df = table.to_pandas()
            # Find matching row by image name
            img_name = image_path.stem
            match = df[df["image_path"].str.contains(img_name, na=False)]
            if not match.empty:
                row = match.iloc[0]
                labels.ocr_quality_score = int(row.get("human_score", 0))
                labels.ocr_quality_source = str(row.get("source", ""))
                labels.ocr_quality_text = str(row.get("ocr_text", ""))[:500]  # Truncate
        except Exception as e:
            logger.debug(f"Failed to parse OCR-Quality labels: {e}")

    return labels


# COCO annotation cache (load once per dataset, not per image)
_COCO_CACHE: dict[str, dict[str, Any]] = {}


def _load_coco_annotations(coco_path: Path) -> dict[str, Any] | None:
    """Load and cache COCO annotations file.

    Returns dict mapping image filename -> list of annotations.
    """
    cache_key = str(coco_path)
    if cache_key in _COCO_CACHE:
        return _COCO_CACHE[cache_key]

    if not coco_path.exists():
        return None

    try:
        with open(coco_path) as f:
            coco_data = json.load(f)

        # Build filename -> image_id mapping
        filename_to_id: dict[str, int] = {}
        for img in coco_data.get("images", []):
            filename_to_id[img["file_name"]] = img["id"]

        # Build image_id -> annotations mapping
        id_to_annotations: dict[int, list[dict]] = {}
        for ann in coco_data.get("annotations", []):
            img_id = ann["image_id"]
            if img_id not in id_to_annotations:
                id_to_annotations[img_id] = []
            id_to_annotations[img_id].append(ann)

        # Build category_id -> category_name mapping
        categories: dict[int, str] = {}
        for cat in coco_data.get("categories", []):
            categories[cat["id"]] = cat["name"]

        # Create final mapping: filename -> annotations with category names
        result: dict[str, Any] = {"annotations": {}, "categories": categories}
        for filename, img_id in filename_to_id.items():
            annotations = id_to_annotations.get(img_id, [])
            # Add category names to annotations
            for ann in annotations:
                ann["category_name"] = categories.get(ann.get("category_id"), "unknown")
            result["annotations"][filename] = annotations

        _COCO_CACHE[cache_key] = result
        logger.debug(
            f"Loaded COCO annotations from {coco_path}: {len(filename_to_id)} images"
        )
        return result
    except Exception as e:
        logger.warning(f"Failed to load COCO annotations from {coco_path}: {e}")
        return None


def derive_content_flags_from_coco(annotations: list[dict]) -> dict[str, bool]:
    """Derive content flags from COCO annotations (Tier 1)."""
    flags = {
        "has_table": False,
        "has_formula": False,
        "has_figure": False,
        "has_handwriting": False,
    }

    for ann in annotations:
        cat_name = ann.get("category_name", "").lower()
        if "table" in cat_name:
            flags["has_table"] = True
        elif "formula" in cat_name or "equation" in cat_name:
            flags["has_formula"] = True
        elif "picture" in cat_name or "figure" in cat_name:
            flags["has_figure"] = True

    return flags


def parse_doclaynet_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse DocLayNet COCO annotations with per-document language detection.

    DocLayNet categories (11 classes):
    - Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header,
    - Picture, Section-Header, Table, Text, Title

    Language detection:
    - Collection-based: german_laws -> de, japanese_laws -> ja, etc.
    - Filename prefix: EN-, DE-, FR- prefixes in doc_name
    - Default: English (95% of dataset)
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Language mapping by collection name
    collection_lang_map = {
        "german_laws": ("de", "Latn"),
        "japanese_laws": ("ja", "Jpan"),
        "russian_laws": ("ru", "Cyrl"),
        "patents_cn": ("zh", "Hans"),
        "philippine_laws": ("en", "Latn"),  # English/Filipino, primarily English
    }

    # Language mapping by doc_name prefix
    prefix_lang_map = {
        "DE-": ("de", "Latn"),
        "FR-": ("fr", "Latn"),
        "EN-": ("en", "Latn"),
        "JA-": ("ja", "Jpan"),
        "ZH-": ("zh", "Hans"),
    }

    # Look for COCO annotations in various locations
    coco_paths = [
        dataset_path / "ground_truth" / "coco" / "train.json",
        dataset_path / "ground_truth" / "coco" / "val.json",
        dataset_path / "ground_truth" / "coco" / "test.json",
        dataset_path / "COCO" / "train.json",
        dataset_path / "COCO" / "val.json",
        dataset_path / "COCO" / "test.json",
        dataset_path / "annotations" / "train.json",
        dataset_path / "annotations" / "instances_train.json",
    ]

    coco_data = None
    for coco_path in coco_paths:
        coco_data = _load_coco_annotations(coco_path)
        if coco_data:
            break

    if not coco_data:
        # Default to English if no COCO data found
        labels.language_code = "en"
        labels.script_name = "Latn"
        return labels

    # Get annotations for this image
    filename = image_path.name
    annotations = coco_data["annotations"].get(filename, [])

    if annotations:
        labels.doclaynet_annotations = annotations

    # Try to find image metadata for language detection
    images_data = coco_data.get("images", [])
    image_meta = None
    for img in images_data:
        if img.get("file_name") == filename:
            image_meta = img
            break

    if image_meta:
        # Extract collection and doc_name
        collection = image_meta.get("collection", "")
        doc_name = image_meta.get("doc_name", "")
        doc_category = image_meta.get("doc_category", "")

        labels.raw_labels["collection"] = collection
        labels.raw_labels["doc_name"] = doc_name
        labels.raw_labels["doc_category"] = doc_category

        # Check collection for language
        if collection in collection_lang_map:
            labels.language_code, labels.script_name = collection_lang_map[collection]
            labels.raw_labels["language_source"] = "collection"
        else:
            # Check doc_name prefix for language
            for prefix, (lang, script) in prefix_lang_map.items():
                if doc_name.startswith(prefix):
                    labels.language_code = lang
                    labels.script_name = script
                    labels.raw_labels["language_source"] = "filename_prefix"
                    break

    # Default to English if no language detected (95% of DocLayNet is English)
    if not labels.language_code:
        labels.language_code = "en"
        labels.script_name = "Latn"
        labels.raw_labels["language_source"] = "default"

    return labels


def parse_tablebank_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse TableBank COCO-format table annotations.

    TableBank provides bounding boxes for tables in documents.
    """
    labels = OriginalLabels()

    # TableBank structure: Detection/images/ and Detection/annotations/
    coco_paths = [
        dataset_path
        / "TableBank"
        / "Detection"
        / "annotations"
        / "tablebank_latex_train.json",
        dataset_path
        / "TableBank"
        / "Detection"
        / "annotations"
        / "tablebank_word_train.json",
        dataset_path / "Detection" / "annotations" / "train.json",
        dataset_path / "annotations" / "train.json",
    ]

    coco_data = None
    for coco_path in coco_paths:
        coco_data = _load_coco_annotations(coco_path)
        if coco_data:
            break

    if not coco_data:
        return labels

    # Get annotations for this image
    filename = image_path.name
    annotations = coco_data["annotations"].get(filename, [])

    if annotations:
        labels.tablebank_annotations = annotations

    return labels


def parse_funsd_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse FUNSD form annotations.

    FUNSD (Form Understanding in Noisy Scanned Documents) structure:
    - Current structure: {train,test}/images/*.png with {train,test}/annotations/*.json
    - Legacy structure: {training,testing}_data/annotations/*.json
    - Alternative: annotations alongside images

    FUNSD annotation format (if available):
    - "form": list of form entities
    - Each entity has: "text", "box", "label", "linking", "words"
    - Labels: "question", "answer", "header", "other"
    """
    labels = OriginalLabels()

    # Detect split from path (train/test/unknown)
    path_str = str(image_path)
    split = "unknown"
    if "/train/" in path_str:
        split = "train"
    elif "/test/" in path_str:
        split = "test"

    # Try multiple possible annotation locations
    json_paths = [
        # Alongside image
        image_path.with_suffix(".json"),
        # Current structure: {train,test}/annotations/*.json
        dataset_path / split / "annotations" / f"{image_path.stem}.json",
        # Standard FUNSD training structure (legacy)
        dataset_path / "training_data" / "annotations" / f"{image_path.stem}.json",
        # Standard FUNSD testing structure (legacy)
        dataset_path / "testing_data" / "annotations" / f"{image_path.stem}.json",
        # Alternative annotation folder
        dataset_path / "annotations" / f"{image_path.stem}.json",
    ]

    for json_path in json_paths:
        if json_path.exists():
            try:
                with open(json_path) as f:
                    raw_annotations = json.load(f)
                # Convert FUNSD format to COCO-like format for compatibility
                # FUNSD: {"form": [{"box": [x,y,w,h], "text": "...", "label": "question"}, ...]}
                # COCO-like: [{"bbox": [x,y,w,h], "category_name": "form_field", ...}, ...]
                if "form" in raw_annotations:
                    labels.funsd_annotations = []
                    for entity in raw_annotations["form"]:
                        # Map FUNSD labels to semantic category names
                        label = entity.get("label", "other")
                        category_map = {
                            "question": "form_field_question",
                            "answer": "form_field_answer",
                            "header": "header",
                            "other": "text",
                        }
                        labels.funsd_annotations.append(
                            {
                                "bbox": entity.get("box", []),
                                "category_name": category_map.get(label, "text"),
                                "text": entity.get("text", ""),
                                "original_label": label,
                            }
                        )
                else:
                    labels.funsd_annotations = raw_annotations
                break  # Found annotations, stop searching
            except Exception as e:
                logger.debug(f"Failed to parse FUNSD annotations from {json_path}: {e}")

    # Even without annotations, we know it's a form dataset (Tier 0)
    if labels.raw_labels is None:
        labels.raw_labels = {}
    labels.raw_labels["document_type"] = "form"
    labels.raw_labels["is_scanned"] = True
    labels.raw_labels["split"] = split  # Track the dataset split

    return labels


def parse_signatr_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse SignaTR6K signature labels from directory structure.

    SignaTR6K structure:
        {train|test|validation}/crop/{id}.png   - Cropped signature images
        {train|test|validation}/label/{id}.png  - Binary mask labels

    Labels extracted:
        - Split: train/test/validation
        - Image ID: numeric identifier
        - Has paired mask: whether label image exists

    Note: SignaTR6K provides signature images with binary segmentation masks
    for signature extraction tasks. There are no writer IDs or genuine/forgery
    labels in this dataset structure - it's purely for signature localization.
    """
    labels = OriginalLabels()

    # Extract split and image info from path structure
    path_parts = image_path.parts
    if labels.raw_labels is None:
        labels.raw_labels = {}

    for i, part in enumerate(path_parts):
        # Identify split
        if part in ("train", "test", "validation"):
            labels.raw_labels["split"] = part

        # Identify if this is crop or label
        if part == "crop":
            labels.raw_labels["image_type"] = "signature"
            # Check for corresponding mask
            label_path = image_path.parent.parent / "label" / image_path.name
            if label_path.exists():
                labels.raw_labels["has_mask"] = True
                labels.raw_labels["mask_path"] = str(label_path)
        elif part == "label":
            labels.raw_labels["image_type"] = "mask"

    # Extract numeric ID from filename
    try:
        image_id = int(image_path.stem)
        labels.raw_labels["signature_id"] = image_id
    except ValueError:
        labels.raw_labels["signature_id"] = image_path.stem

    return labels


# Module-level cache for PUCIT-OHUL Excel labels (avoids reopening XLSX per image)
_pucit_label_cache: dict[Path, dict[str, tuple[str | None, str | None]]] = {}


def _load_pucit_excel(excel_file: Path) -> dict[str, tuple[str | None, str | None]]:
    """Load and cache all labels from a PUCIT-OHUL Excel file.

    Returns dict mapping image key -> (transcription, writer_id).
    """
    if excel_file in _pucit_label_cache:
        return _pucit_label_cache[excel_file]

    label_map: dict[str, tuple[str | None, str | None]] = {}
    try:
        import openpyxl

        wb = openpyxl.load_workbook(excel_file, read_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row and len(row) >= 2 and row[0] is not None:
                image_key = str(row[0])
                transcription = str(row[1]) if row[1] else None
                writer_id = str(row[2]) if len(row) >= 3 and row[2] else None
                label_map[image_key] = (transcription, writer_id)
        wb.close()
        logger.debug("Loaded %d labels from %s", len(label_map), excel_file.name)
    except ImportError:
        logger.debug("openpyxl not available for PUCIT-OHUL label parsing")
    except Exception:
        logger.debug("Failed to parse PUCIT-OHUL labels from %s", excel_file)

    _pucit_label_cache[excel_file] = label_map
    return label_map


def parse_pucit_ohul_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse PUCIT-OHUL Urdu handwriting labels from cached Excel data.

    PUCIT-OHUL (Punjab University Center for IT - Offline Handwritten Urdu Lines):
        Pucit/
            train_labels_v2.xlsx - Training labels
            test_labels_v2.xlsx  - Testing labels
            train_lines/         - Training images
            test_lines/          - Testing images

    Excel data is cached on first access per file for O(1) lookups.
    """
    labels = OriginalLabels()

    # Set language/script based on dataset (known from dataset metadata)
    labels.language_code = "ur"  # Urdu
    labels.script_name = "Arabic"  # Urdu uses Arabic script
    labels.iso15924_script_code = "Arab"  # ISO 15924 for Arabic script

    # Determine split from path
    path_str = str(image_path)
    split = None
    if "train_lines" in path_str or "/train/" in path_str:
        split = "train"
    elif "test_lines" in path_str or "/test/" in path_str:
        split = "test"

    if labels.raw_labels is None:
        labels.raw_labels = {}
    if split:
        labels.raw_labels["split"] = split

    # Find Pucit directory with Excel files
    pucit_path = None
    for parent in image_path.parents:
        if (parent / "train_labels_v2.xlsx").exists():
            pucit_path = parent
            break
        if (parent / "Pucit" / "train_labels_v2.xlsx").exists():
            pucit_path = parent / "Pucit"
            break

    if pucit_path and split:
        excel_file = pucit_path / f"{split}_labels_v2.xlsx"
        if excel_file.exists():
            label_map = _load_pucit_excel(excel_file)
            # O(1) dict lookup instead of iterating all rows
            match = label_map.get(image_path.stem) or label_map.get(image_path.name)
            if match:
                transcription, writer_id = match
                if transcription:
                    labels.transcription = transcription
                if writer_id:
                    labels.writer_id = writer_id

    return labels


def parse_multilingual_scripts_labels(
    dataset_path: Path, image_path: Path
) -> OriginalLabels:
    """Parse multilingual scripts labels from manifest and directory structure.

    Multilingual Scripts collection structure:
        multilingual_scripts/
            combined_manifest.json         - Master manifest
            arabic_ocr/manifest.json       - Arabic OCR dataset
            dzongkha_digits/manifest.json  - Tibetan/Dzongkha digits
            jssoda/manifest.json           - Japanese handwriting
            mdiw13/                        - 13 Indic scripts (zipped)
            nepal_devanagari/              - Nepali Devanagari (unlabeled)

    Script/Language mappings:
        - arabic_ocr: Arabic script (Arab), Arabic language (ar)
        - dzongkha_digits: Tibetan script (Tibt), Dzongkha language (dz)
        - jssoda: Japanese script (Jpan), Japanese language (ja)
        - mdiw13: Multiple Indic scripts (Deva, Beng, Taml, etc.)
        - nepal_devanagari: Devanagari script (Deva), Nepali language (ne)

    Label Status:
        - arabic_ocr, dzongkha_digits, jssoda, mdiw13: Academic datasets with labels
        - nepal_devanagari: Real-world Nepali documents (717 images), no ground
          truth labels - only script/language metadata derived from path.
          Two sources:
            - nepal_book_*: 713 book page scans
            - nepal_newspaper_*: 4 newspaper page scans
    """
    labels = OriginalLabels()

    # Script/language mapping based on subdataset
    SCRIPT_MAPPINGS = {
        "arabic_ocr": {
            "script": "Arab",
            "language": "ar",
            "script_name": "Arabic",
            "labeled": True,
        },
        "dzongkha_digits": {
            "script": "Tibt",
            "language": "dz",
            "script_name": "Tibetan",
            "labeled": True,
        },
        "jssoda": {
            "script": "Jpan",
            "language": "ja",
            "script_name": "Japanese",
            "labeled": True,
        },
        "nepal_devanagari": {
            "script": "Deva",
            "language": "ne",
            "script_name": "Devanagari",
            "labeled": False,
        },
        # MDIW-13 has 13 scripts - would need filename parsing
    }

    # Determine subdataset from path
    path_parts = image_path.parts
    subdataset = None

    for part in path_parts:
        if part in SCRIPT_MAPPINGS:
            subdataset = part
            break
        # Check for mdiw13 (13 Indic scripts)
        if part == "mdiw13" or "mdiw" in part.lower():
            subdataset = "mdiw13"
            break

    if subdataset and subdataset in SCRIPT_MAPPINGS:
        mapping = SCRIPT_MAPPINGS[subdataset]
        labels.script_name = mapping["script_name"]
        labels.language_code = mapping["language"]
        if labels.raw_labels is None:
            labels.raw_labels = {}
        labels.raw_labels["iso15924_script"] = mapping["script"]
        labels.raw_labels["subdataset"] = subdataset
        labels.raw_labels["has_ground_truth_labels"] = mapping.get("labeled", True)

        # Special handling for nepal_devanagari: extract document type from filename
        if subdataset == "nepal_devanagari":
            filename = image_path.stem
            if filename.startswith("nepal_book"):
                labels.raw_labels["document_type"] = "book"
            elif filename.startswith("nepal_newspaper"):
                labels.raw_labels["document_type"] = "newspaper"
            labels.raw_labels["note"] = "Unlabeled real-world Nepali documents"
    elif subdataset == "mdiw13":
        # MDIW-13 has 13 Indic scripts - requires further parsing
        labels.script_name = "Indic"  # Generic
        if labels.raw_labels is None:
            labels.raw_labels = {}
        labels.raw_labels["subdataset"] = "mdiw13"
        labels.raw_labels["note"] = (
            "13 Indic scripts - specific script needs filename parsing"
        )

    # Try to parse manifest for additional metadata
    manifest_paths = [
        dataset_path / subdataset / "manifest.json" if subdataset else None,
        dataset_path / "combined_manifest.json",
    ]

    for manifest_path in manifest_paths:
        if manifest_path and manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                    # Look for this specific image in manifest
                    image_name = image_path.name
                    for sample in manifest.get("samples", []):
                        if sample.get("filename") == image_name:
                            if labels.raw_labels is None:
                                labels.raw_labels = {}
                            labels.raw_labels["manifest_source"] = sample.get("source")
                            labels.raw_labels["manifest_index"] = sample.get("index")
                            break
            except Exception as e:
                logger.debug(f"Failed to parse manifest at {manifest_path}: {e}")

    return labels


def parse_rvl_cdip_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse RVL-CDIP document classification labels from filename.

    RVL-CDIP (Ryerson Vision Lab Complex Document Information Processing) structure:
        images/rvl_{class}_{number}.jpg

    The 16 document classes are:
        - advertisement, budget, email, file_folder
        - form, handwritten, invoice, letter
        - memo, news_article, presentation, questionnaire
        - resume, scientific_publication, scientific_report, specification

    Labels are encoded in the filename prefix (e.g., "rvl_advertisement_0000.jpg").
    """
    labels = OriginalLabels()

    # RVL-CDIP class definitions (16 classes)
    rvl_classes = {
        "advertisement": 0,
        "budget": 1,
        "email": 2,
        "file_folder": 3,
        "form": 4,
        "handwritten": 5,
        "invoice": 6,
        "letter": 7,
        "memo": 8,
        "news_article": 9,
        "presentation": 10,
        "questionnaire": 11,
        "resume": 12,
        "scientific_publication": 13,
        "scientific_report": 14,
        "specification": 15,
    }

    # Parse class from filename: rvl_{class}_{number}.jpg
    filename = image_path.stem  # e.g., "rvl_advertisement_0000"

    if labels.raw_labels is None:
        labels.raw_labels = {}

    if filename.startswith("rvl_"):
        # Remove 'rvl_' prefix and split by underscore
        parts = filename[4:].rsplit(
            "_", 1
        )  # Split from right to handle multi-word classes
        if len(parts) == 2:
            class_name = parts[0]  # e.g., "advertisement" or "scientific_publication"
            image_number = parts[1]  # e.g., "0000"

            if class_name in rvl_classes:
                labels.raw_labels["document_class"] = class_name
                labels.raw_labels["document_class_id"] = rvl_classes[class_name]
                labels.raw_labels["image_number"] = image_number

                # Map to document type for downstream compatibility
                labels.document_type = class_name.replace("_", " ").title()

    return labels


# Cache for PubTabNet JSONL annotations (loaded once per file)
_pubtabnet_cache: dict[str, dict[str, dict]] = {}


def parse_pubtabnet_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse PubTabNet table annotations from JSONL file.

    PubTabNet (Image-based Table Recognition Dataset) structure:
        pubtabnet/
            train/
                PMC*.png
            val/
                PMC*.png
            PubTabNet_2.0.0.jsonl  - Annotations for all images

    JSONL format:
        {"filename": "PMC1234_table_0.png", "split": "train",
         "html": {"structure": {"tokens": ["<thead>", ...]},
                  "cells": [{"tokens": [...], "bbox": [x1, y1, x2, y2]}]}}

    Extracts:
        - table_html: HTML structure tokens joined as string
        - cell_annotations: List of cell dicts with tokens and bboxes
    """
    labels = OriginalLabels()

    # Try multiple possible JSONL locations
    jsonl_paths = [
        dataset_path / "PubTabNet_2.0.0.jsonl",
        dataset_path / "pubtabnet.jsonl",
        dataset_path / "annotations.jsonl",
        dataset_path.parent / "PubTabNet_2.0.0.jsonl",
    ]

    # Find and load JSONL if not cached
    jsonl_path = None
    for path in jsonl_paths:
        if path.exists():
            jsonl_path = path
            break

    if not jsonl_path:
        return labels

    # Load annotations into cache if not already done
    cache_key = str(jsonl_path)
    if cache_key not in _pubtabnet_cache:
        try:
            annotations_by_filename: dict[str, dict] = {}
            with open(jsonl_path) as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if "filename" in entry:
                            annotations_by_filename[entry["filename"]] = entry
            _pubtabnet_cache[cache_key] = annotations_by_filename
            logger.debug(
                f"Loaded {len(annotations_by_filename)} PubTabNet annotations from {jsonl_path}"
            )
        except Exception as e:
            logger.warning(f"Failed to load PubTabNet JSONL from {jsonl_path}: {e}")
            _pubtabnet_cache[cache_key] = {}

    # Look up annotation for this image
    filename = image_path.name
    annotations = _pubtabnet_cache.get(cache_key, {})
    entry = annotations.get(filename)

    if entry and "html" in entry:
        html_data = entry["html"]

        # Extract HTML structure as string
        if "structure" in html_data and "tokens" in html_data["structure"]:
            labels.table_html = "".join(html_data["structure"]["tokens"])

        # Extract cell annotations
        if "cells" in html_data:
            labels.cell_annotations = html_data["cells"]

        # Store split information if available
        if labels.raw_labels is None:
            labels.raw_labels = {}
        if "split" in entry:
            labels.raw_labels["split"] = entry["split"]

    return labels


def parse_fintabnet_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse FinTabNet table annotations from JSONL file.

    FinTabNet (Financial Table Dataset) has similar structure to PubTabNet:
        fintabnet/
            images/
                *.png
            annotations.jsonl or fintabnet.jsonl

    Uses same format as PubTabNet for consistency.
    """
    labels = OriginalLabels()

    # Try multiple possible JSONL locations
    jsonl_paths = [
        dataset_path / "fintabnet.jsonl",
        dataset_path / "annotations.jsonl",
        dataset_path / "FinTabNet.jsonl",
        dataset_path.parent / "fintabnet.jsonl",
    ]

    jsonl_path = None
    for path in jsonl_paths:
        if path.exists():
            jsonl_path = path
            break

    if not jsonl_path:
        return labels

    # Reuse PubTabNet cache mechanism (same format)
    cache_key = str(jsonl_path)
    if cache_key not in _pubtabnet_cache:
        try:
            annotations_by_filename: dict[str, dict] = {}
            with open(jsonl_path) as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if "filename" in entry:
                            annotations_by_filename[entry["filename"]] = entry
            _pubtabnet_cache[cache_key] = annotations_by_filename
        except Exception as e:
            logger.warning(f"Failed to load FinTabNet JSONL from {jsonl_path}: {e}")
            _pubtabnet_cache[cache_key] = {}

    # Look up annotation for this image
    filename = image_path.name
    annotations = _pubtabnet_cache.get(cache_key, {})
    entry = annotations.get(filename)

    if entry and "html" in entry:
        html_data = entry["html"]
        if "structure" in html_data and "tokens" in html_data["structure"]:
            labels.table_html = "".join(html_data["structure"]["tokens"])
        if "cells" in html_data:
            labels.cell_annotations = html_data["cells"]

    return labels


# Cache for im2latex formulas (loaded once)
_im2latex_formulas_cache: dict[str, list[str]] = {}
_im2latex_index_cache: dict[str, dict[str, int]] = {}


def parse_im2latex_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse im2latex-100k LaTeX formula annotations.

    im2latex-100k structure:
        im2latex/
            formula_images/
                im2latex_train_filter/
                    *.png
                im2latex_validate_filter/
                    *.png
            im2latex_formulas.lst   - One LaTeX formula per line (0-indexed)
            im2latex_train.lst      - formula_idx filename
            im2latex_validate.lst   - formula_idx filename
            im2latex_test.lst       - formula_idx filename

    Alternatively (simplified structure):
        im2latex/
            images/
                *.png
            formulas.lst
            train.lst / val.lst / test.lst

    Extracts:
        - transcription: LaTeX source for the formula
        - raw_labels: formula_index, split
    """
    labels = OriginalLabels()

    # Try to find formulas list file
    formula_paths = [
        dataset_path / "im2latex_formulas.lst",
        dataset_path / "formulas.lst",
        dataset_path.parent / "im2latex_formulas.lst",
    ]

    formula_file = None
    for path in formula_paths:
        if path.exists():
            formula_file = path
            break

    if not formula_file:
        return labels

    # Load formulas into cache
    cache_key = str(formula_file)
    if cache_key not in _im2latex_formulas_cache:
        try:
            with open(formula_file, encoding="utf-8", errors="replace") as f:
                formulas = [line.strip() for line in f]
            _im2latex_formulas_cache[cache_key] = formulas
            logger.debug(f"Loaded {len(formulas)} formulas from {formula_file}")
        except Exception as e:
            logger.warning(f"Failed to load im2latex formulas from {formula_file}: {e}")
            _im2latex_formulas_cache[cache_key] = []

    # Try to find image-to-formula index mapping
    index_files = [
        (dataset_path / "im2latex_train.lst", "train"),
        (dataset_path / "im2latex_validate.lst", "validate"),
        (dataset_path / "im2latex_test.lst", "test"),
        (dataset_path / "train.lst", "train"),
        (dataset_path / "val.lst", "val"),
        (dataset_path / "test.lst", "test"),
    ]

    # Build filename to index mapping
    index_cache_key = str(dataset_path)
    if index_cache_key not in _im2latex_index_cache:
        filename_to_index: dict[str, int] = {}
        for index_file, split in index_files:
            if index_file.exists():
                try:
                    with open(index_file, encoding="utf-8", errors="replace") as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                formula_idx = int(parts[0])
                                filename = parts[1]
                                # Store both with and without extension
                                filename_to_index[filename] = formula_idx
                                filename_to_index[Path(filename).stem] = formula_idx
                except Exception as e:
                    logger.debug(f"Failed to parse index file {index_file}: {e}")
        _im2latex_index_cache[index_cache_key] = filename_to_index

    # Look up formula for this image
    formulas = _im2latex_formulas_cache.get(cache_key, [])
    index_map = _im2latex_index_cache.get(index_cache_key, {})

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Try to find the formula index
    filename = image_path.name
    stem = image_path.stem

    formula_idx = index_map.get(filename) or index_map.get(stem)

    if formula_idx is not None and 0 <= formula_idx < len(formulas):
        labels.transcription = formulas[formula_idx]
        labels.raw_labels["formula_index"] = formula_idx

    # Determine split from path
    path_str = str(image_path).lower()
    if "train" in path_str:
        labels.raw_labels["split"] = "train"
    elif "val" in path_str or "validate" in path_str:
        labels.raw_labels["split"] = "val"
    elif "test" in path_str:
        labels.raw_labels["split"] = "test"

    return labels


def parse_nist_sd19_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse NIST SD-19 handwriting labels from directory structure.

    NIST SD-19 (Special Database 19) structure:
        nist-sd19/
            by_class/
                {class_id}/
                    hsf_{writer_id}/
                        {char}_{sample}.png
            by_write/
                hsf_{writer_id}/
                    {class}_{sample}.png

    The dataset contains handwritten characters and digits from:
        - HSF 0-3: High school students
        - HSF 4: IRS workers
        - HSF 6: Census workers
        - HSF 7: IRS workers (second group)

    Extracts:
        - transcription: Character class (digit 0-9, letter A-Z, etc.)
        - writer_id: HSF writer identifier
        - raw_labels: class_id, sample_id
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Extract information from path and filename
    path_parts = image_path.parts
    filename = image_path.stem

    # Try to extract writer ID from path (hsf_0, hsf_1, etc.)
    for part in path_parts:
        if part.startswith(("hsf_", "hsf")):
            labels.writer_id = part
            break

    # Try to extract class from by_class structure or filename
    for i, part in enumerate(path_parts):
        if part == "by_class" and i + 1 < len(path_parts):
            class_id = path_parts[i + 1]
            labels.raw_labels["class_id"] = class_id
            # Map class ID to character (simplified mapping)
            if class_id.isdigit():
                # Digit class (0-9)
                labels.transcription = class_id
            break

    # Parse filename patterns
    # Common patterns: "a_0001.png", "digit_5_0001.png", etc.
    parts = filename.split("_")
    if len(parts) >= 2:
        if parts[0].isalpha() and len(parts[0]) == 1:
            # Single character label
            labels.transcription = parts[0].upper()
        elif parts[0].isdigit() and len(parts[0]) == 1:
            labels.transcription = parts[0]
        labels.raw_labels["sample_id"] = parts[-1] if parts[-1].isdigit() else None

    return labels


def parse_mdiw13_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse MDIW-13 multi-script dataset labels from directory structure.

    MDIW-13 (Multi-lingual Database for Script Identification) structure:
        mdiw13/
            {script_name}/
                Document/
                    *.png
                Line/
                    *.png
                Word/
                    *.png

    The 13 scripts are: Arabic, Bengali, Gujarati, Gurmukhi, Devanagari,
    Japanese, Kannada, Malayalam, Oriya, Roman (Latin), Tamil, Telugu, Thai

    Extracts:
        - script_name: Script class from directory
        - language_code: ISO 639 code derived from script
        - raw_labels: segmentation_level (Document/Line/Word)
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Script name to ISO 15924 and ISO 639 mappings
    script_mappings = {
        "Arabic": ("Arab", "ar"),
        "Bengali": ("Beng", "bn"),
        "Gujarati": ("Gujr", "gu"),
        "Gurmukhi": ("Guru", "pa"),
        "Devanagari": ("Deva", "hi"),
        "Japanese": ("Jpan", "ja"),
        "Kannada": ("Knda", "kn"),
        "Malayalam": ("Mlym", "ml"),
        "Oriya": ("Orya", "or"),
        "Roman": ("Latn", "en"),
        "Tamil": ("Taml", "ta"),
        "Telugu": ("Telu", "te"),
        "Thai": ("Thai", "th"),
    }

    # Parse script from directory structure
    path_parts = image_path.parts

    for part in path_parts:
        if part in script_mappings:
            iso15924, iso639 = script_mappings[part]
            labels.script_name = part  # Human-readable name
            labels.iso15924_script_code = iso15924  # Standardized ISO 15924 code
            labels.language_code = iso639
            break

    # Determine segmentation level
    for part in path_parts:
        if part in ("Document", "Line", "Word"):
            labels.raw_labels["segmentation_level"] = part.lower()
            break

    return labels


def parse_cc_ocr_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse CC-OCR benchmark labels from TSV files.

    CC-OCR structure:
        CC-OCR/
            {track}/           # doc_parsing, kie, multi_lan_ocr, multi_scene_ocr
                *.tsv          # Annotation files with columns:
                               # index, image, image_name, question, answer, category, l2-category, split

    TSV columns:
        - image_name: Filename (e.g., "0.jpg")
        - answer: Ground truth OCR text (UTF-8, LaTeX for documents)
        - category: Track (doc_parsing, kie, multi_lan_ocr, multi_scene_ocr)
        - l2-category: Subset name (39 unique values)
        - split: Always "test" (benchmark-only)

    Extracts:
        - transcription: Full OCR text from "answer" column
        - language_code: Inferred from track/category
        - raw_labels: track, subset, split
    """
    import csv

    labels = OriginalLabels()

    # Default to Chinese (Simplified) - can be overridden by track detection
    labels.language_code = "zh"
    labels.script_name = "Chinese"
    labels.iso15924_script_code = "Hans"

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Parse track from path
    path_parts = image_path.parts
    track = None
    for part in path_parts:
        if part in ("doc_parsing", "kie", "multi_lan_ocr", "multi_scene_ocr"):
            track = part
            labels.raw_labels["track"] = track
            break

    # Find TSV file containing this image
    # TSV files are in the track directory (not per-image)
    if track:
        track_dir = dataset_path / track
        if not track_dir.exists():
            logger.warning(f"Track directory not found: {track_dir}")
            return labels

        tsv_files = list(track_dir.glob("*.tsv"))

        # Search all TSV files for matching image_name
        image_name = image_path.name
        for tsv_file in tsv_files:
            try:
                with open(tsv_file, encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter="\t")
                    for row in reader:
                        if row.get("image_name") == image_name:
                            # Found matching row
                            labels.transcription = row.get("answer", "")
                            labels.raw_labels["category"] = row.get("category", "")
                            labels.raw_labels["l2_category"] = row.get(
                                "l2-category", ""
                            )
                            labels.raw_labels["split"] = row.get("split", "test")
                            labels.raw_labels["question"] = row.get("question", "")
                            labels.raw_labels["subset_file"] = tsv_file.name

                            # Infer language from track
                            if track == "multi_lan_ocr":
                                # Multilingual - would need subcategory analysis
                                labels.raw_labels["multilingual"] = True
                            elif track in ("doc_parsing", "kie"):
                                # Assume Chinese
                                labels.language_code = "zh"
                            elif track == "multi_scene_ocr":
                                # Mixed Chinese/English - default Chinese
                                labels.language_code = "zh"

                            return labels  # Found match, return

            except Exception as e:
                logger.debug(f"Failed to parse TSV {tsv_file}: {e}")
                continue

    # If no TSV match found, return minimal labels
    logger.warning(f"No TSV annotation found for {image_name} in track {track}")
    return labels


def parse_tibhcr_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse TibHCR Tibetan handwriting labels from directory structure.

    TibHCR (Tibetan Handwritten Character Recognition) structure:
        TibHCR/
            train/
                {character_class}/
                    *.png
            test/
                {character_class}/
                    *.png

    Contains 47 character classes from 235 writers.

    Extracts:
        - transcription: Character class
        - raw_labels: split, character_class
    """
    labels = OriginalLabels()

    # Fixed: Tibetan script
    labels.language_code = "bo"
    labels.script_name = "Tibetan"
    labels.iso15924_script_code = "Tibt"  # ISO 15924 for Tibetan

    if labels.raw_labels is None:
        labels.raw_labels = {}

    path_parts = image_path.parts

    # Determine split
    for part in path_parts:
        if part in ("train", "test", "val", "validation"):
            labels.raw_labels["split"] = part
            break

    # Character class is typically the parent directory name
    parent_dir = image_path.parent.name
    if parent_dir not in ("train", "test", "val", "validation", "images"):
        labels.raw_labels["character_class"] = parent_dir
        labels.transcription = parent_dir

    return labels


def parse_mlt19_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse MLT-19 multilingual scene text labels from annotations.

    MLT-19 (ICDAR 2019 Multilingual Text) structure:
        mlt19/
            ImagesPart1/
                img_{id}.jpg
            ImagesPart2/
                img_{id}.jpg
            train_gt/
                gt_img_{id}.txt
            val_gt/
                gt_img_{id}.txt

    Annotation format (per line):
        x1,y1,x2,y2,x3,y3,x4,y4,language,transcription

    Languages: Arabic, Latin, Chinese, Japanese, Korean, Bangla, Hindi, etc.

    Extracts:
        - text_instances: List of text boxes with language and transcription
        - raw_labels: language codes found, split
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Language name to ISO 639 code
    lang_to_iso = {
        "Arabic": "ar",
        "Latin": "en",  # Default for Latin
        "Chinese": "zh",
        "Japanese": "ja",
        "Korean": "ko",
        "Bangla": "bn",
        "Hindi": "hi",
        "Symbols": None,
        "Mixed": None,
        "None": None,
    }

    # Try to find ground truth file
    # MLT-19 structure: TrainGT/TrainGT/tr_img_{id}.txt or train_gt/gt_{stem}.txt
    gt_dirs = [
        dataset_path / "TrainGT" / "TrainGT",  # Actual structure
        dataset_path / "train_gt",
        dataset_path / "val_gt",
        dataset_path / "test_gt",
        dataset_path / "gt",
    ]

    gt_file = None
    for gt_dir in gt_dirs:
        # Try multiple filename patterns
        candidates = [
            gt_dir / f"gt_{image_path.stem}.txt",
            gt_dir / f"{image_path.stem}.txt",  # tr_img_00001.txt
        ]
        for candidate in candidates:
            if candidate.exists():
                gt_file = candidate
                break
        if gt_file:
            break

    if gt_file:
        try:
            text_instances = []
            languages_found = set()

            with open(gt_file, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",", 9)  # 8 coords + language + transcription
                    if len(parts) >= 10:
                        coords = [float(x) for x in parts[:8]]
                        language = parts[8]
                        transcription = parts[9] if len(parts) > 9 else ""

                        languages_found.add(language)
                        text_instances.append(
                            {
                                "bbox": coords,
                                "language": language,
                                "transcription": transcription,
                            }
                        )

            labels.text_instances = text_instances
            labels.raw_labels["languages"] = list(languages_found)

            # Set language code based on languages found
            # Filter out non-linguistic markers (Symbols, Mixed, None)
            linguistic_langs = {
                lang
                for lang in languages_found
                if lang in lang_to_iso and lang_to_iso[lang] is not None
            }

            if len(linguistic_langs) == 1:
                # Single language - set that language
                lang = next(iter(linguistic_langs))
                labels.language_code = lang_to_iso[lang]
            elif len(linguistic_langs) > 1:
                # Multiple languages in same document - use 'mul' (ISO 639-3)
                labels.language_code = "mul"
            # If no linguistic languages found (only Symbols/Mixed/None), leave empty

        except Exception as e:
            logger.debug(f"Failed to parse MLT-19 GT file {gt_file}: {e}")
    else:
        # No GT file found - mark as undetermined for test images
        # MLT-19 test set GT was never released (ICDAR competition holdout)
        labels.raw_labels["gt_available"] = False

    # Determine split from path
    path_str = str(image_path).lower()
    if "train" in path_str:
        labels.raw_labels["split"] = "train"
    elif "val" in path_str:
        labels.raw_labels["split"] = "val"
    elif "test" in path_str:
        labels.raw_labels["split"] = "test"
        # Test images without GT - mark as undetermined baseline
        # Language can be enriched later via visual detection
        if not gt_file and not labels.language_code:
            labels.language_code = "und"  # ISO 639-2 undetermined
            labels.raw_labels["language_source"] = "baseline_und"

    return labels


def parse_arabic_docs_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse Arabic Documents OCR labels from directory structure.

    Structure: Documents/{category}/{filename}.jpg
    12 categories of Arabic documents.
    """
    labels = OriginalLabels()
    labels.language_code = "ar"
    labels.script_name = "Arabic"
    labels.iso15924_script_code = "Arab"  # ISO 15924 for Arabic

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Extract category from parent directory
    path_parts = image_path.parts
    for i, part in enumerate(path_parts):
        if part == "Documents" and i + 1 < len(path_parts):
            labels.raw_labels["category"] = path_parts[i + 1]
            labels.document_type = path_parts[i + 1]
            break

    return labels


def parse_hindi_synthetic_labels(
    dataset_path: Path, image_path: Path
) -> OriginalLabels:
    """Parse Hindi OCR Synthetic labels from filename/directory.

    Structure: data_80k/{split}/{id}.png with paired .txt files
    Synthetic line images with Hindi text.
    """
    labels = OriginalLabels()
    labels.language_code = "hi"
    labels.script_name = "Devanagari"
    labels.iso15924_script_code = "Deva"  # ISO 15924 for Devanagari

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Try to find corresponding transcription file
    txt_path = image_path.with_suffix(".txt")
    if txt_path.exists():
        try:
            with open(txt_path, encoding="utf-8", errors="replace") as f:
                labels.transcription = f.read().strip()
        except Exception:
            pass

    # Extract split from path
    path_str = str(image_path).lower()
    if "train" in path_str:
        labels.raw_labels["split"] = "train"
    elif "val" in path_str:
        labels.raw_labels["split"] = "val"
    elif "test" in path_str:
        labels.raw_labels["split"] = "test"

    return labels


def parse_nepali_handwritten_labels(
    dataset_path: Path, image_path: Path
) -> OriginalLabels:
    """Parse Nepali Handwritten labels from directory structure.

    Structure: {train,test}/{id}.jpg
    Nepali handwritten text images.
    """
    labels = OriginalLabels()
    labels.language_code = "ne"
    labels.script_name = "Devanagari"
    labels.iso15924_script_code = "Deva"  # ISO 15924 for Devanagari

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Extract split from parent directory
    parent = image_path.parent.name
    if parent in ("train", "test", "val"):
        labels.raw_labels["split"] = parent

    return labels


def parse_yarmouk_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse Yarmouk OCR dataset labels from directory structure.

    Structure: {Training,Testing,Samples}/{id}.jpg
    Arabic OCR dataset with text annotations.
    """
    labels = OriginalLabels()
    labels.language_code = "ar"
    labels.script_name = "Arabic"
    labels.iso15924_script_code = "Arab"  # ISO 15924 for Arabic

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Extract split from parent directory
    path_parts = image_path.parts
    for part in path_parts:
        if part == "Training":
            labels.raw_labels["split"] = "train"
            break
        if part == "Testing":
            labels.raw_labels["split"] = "test"
            break
        if part == "Samples":
            labels.raw_labels["split"] = "sample"
            break

    return labels


def parse_ohr_bench_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse OHR-Bench labels (16 document categories).

    OHR-Bench (OCR Hallucination Benchmark) has 16 document types:
    academic, book, exam, finance, form, handwritten, legal,
    magazine, medical, newspaper, note, poster, receipt, research,
    resume, slide

    Note: Arrow format - labels may come from extraction metadata.
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Try to extract category from filename or parent directory
    filename = image_path.stem
    parent = image_path.parent.name

    ohr_categories = {
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

    for cat in ohr_categories:
        if cat in filename.lower() or cat in parent.lower():
            labels.raw_labels["category"] = cat
            labels.document_type = cat.title()
            break

    return labels


def parse_financebench_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse FinanceBench labels from filename pattern and metadata.

    FinanceBench contains SEC filings (10K, 10Q, 8K, Earnings) from public companies.
    Filename pattern: {COMPANY}_{PERIOD}_{TYPE}_p{PAGE}.png
    Examples: 3M_2018_10K_p059.png, ADOBE_2022_10K_p001.png

    Document Types:
        - 10k: Annual financial reports
        - 10q: Quarterly financial reports
        - 8k: Current event reports
        - earnings: Earnings call transcripts
    """
    import json
    import re

    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Filename pattern: {COMPANY}_{PERIOD}_{TYPE}_p{PAGE}.png
    filename_pattern = re.compile(
        r"^(?P<company>.+?)_(?P<period>\d{4}Q?\d?)_(?P<doc_type>\w+)_p(?P<page>\d+)\.png$",
        re.IGNORECASE,
    )

    filename = image_path.name
    match = filename_pattern.match(filename)

    if match:
        company = match.group("company")
        period = match.group("period")
        doc_type = match.group("doc_type").lower()
        page_num = int(match.group("page"))

        labels.raw_labels["company"] = company
        labels.raw_labels["doc_period"] = period
        labels.raw_labels["doc_type"] = doc_type
        labels.raw_labels["page_num"] = page_num
        labels.document_type = f"SEC {doc_type.upper()}"

        # Try to get additional metadata from JSONL files
        doc_name = f"{company}_{period}_{doc_type.upper()}"
        doc_info_path = (
            dataset_path / "data" / "financebench_document_information.jsonl"
        )

        if doc_info_path.exists():
            with open(doc_info_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        if doc.get("doc_name", "").lower() == doc_name.lower():
                            labels.raw_labels["gics_sector"] = doc.get("gics_sector")
                            labels.raw_labels["doc_link"] = doc.get("doc_link")
                            break

    return labels


def parse_midv500_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse MIDV-500 ID document labels from path structure.

    Structure: {num}_{country_code}_{doc_type}/images/{condition}/{id}.tif
    Examples: 01_alb_id, 06_bra_passport, 12_deu_drvlic_new
    50 countries, various document types (ID, passport, driving licence).
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # ISO 3166-1 alpha-3 to language/script mapping
    country_to_lang_script = {
        "alb": ("sq", "Latn"),  # Albania - Albanian
        "aut": ("de", "Latn"),  # Austria - German
        "aze": ("az", "Latn"),  # Azerbaijan - Azerbaijani
        "bra": ("pt", "Latn"),  # Brazil - Portuguese
        "chl": ("es", "Latn"),  # Chile - Spanish
        "chn": ("zh", "Hans"),  # China - Chinese
        "cze": ("cs", "Latn"),  # Czech Republic - Czech
        "deu": ("de", "Latn"),  # Germany - German
        "dza": ("ar", "Arab"),  # Algeria - Arabic
        "esp": ("es", "Latn"),  # Spain - Spanish
        "est": ("et", "Latn"),  # Estonia - Estonian
        "fin": ("fi", "Latn"),  # Finland - Finnish
        "grc": ("el", "Grek"),  # Greece - Greek
        "hrv": ("hr", "Latn"),  # Croatia - Croatian
        "hun": ("hu", "Latn"),  # Hungary - Hungarian
        "irn": ("fa", "Arab"),  # Iran - Persian
        "ita": ("it", "Latn"),  # Italy - Italian
        "jpn": ("ja", "Jpan"),  # Japan - Japanese
        "ltu": ("lt", "Latn"),  # Lithuania - Lithuanian
        "lva": ("lv", "Latn"),  # Latvia - Latvian
        "mys": ("ms", "Latn"),  # Malaysia - Malay
        "nld": ("nl", "Latn"),  # Netherlands - Dutch
        "nor": ("no", "Latn"),  # Norway - Norwegian
        "pol": ("pl", "Latn"),  # Poland - Polish
        "prt": ("pt", "Latn"),  # Portugal - Portuguese
        "rou": ("ro", "Latn"),  # Romania - Romanian
        "rus": ("ru", "Cyrl"),  # Russia - Russian
        "srb": ("sr", "Cyrl"),  # Serbia - Serbian
        "svk": ("sk", "Latn"),  # Slovakia - Slovak
        "svn": ("sl", "Latn"),  # Slovenia - Slovenian
        "swe": ("sv", "Latn"),  # Sweden - Swedish
        "tur": ("tr", "Latn"),  # Turkey - Turkish
        "ukr": ("uk", "Cyrl"),  # Ukraine - Ukrainian
        "usa": ("en", "Latn"),  # USA - English
        "zaf": ("en", "Latn"),  # South Africa - English (primary)
        # Additional country codes found in MIDV-500
        "mac": ("zh", "Hans"),  # Macau - Chinese
        "mda": ("ro", "Latn"),  # Moldova - Romanian
        "ury": ("es", "Latn"),  # Uruguay - Spanish
        "xpo": ("en", "Latn"),  # Synthetic/placeholder - default English
    }

    path_parts = image_path.parts

    # Extract country code from directory name like "01_alb_id"
    for part in path_parts:
        if "_" in part:
            subparts = part.lower().split("_")
            if len(subparts) >= 2:
                # Format: {num}_{country}_{doctype}[_variant]
                country_code = subparts[1] if subparts[0].isdigit() else subparts[0]
                if len(country_code) == 3:
                    labels.raw_labels["country_code"] = country_code.upper()

                    # Map to language and script
                    if country_code in country_to_lang_script:
                        labels.language_code, labels.script_name = (
                            country_to_lang_script[country_code]
                        )

                    # Extract document type
                    doc_types = {
                        "id",
                        "passport",
                        "drvlic",
                        "homereturn",
                        "internalpassport",
                    }
                    for subpart in subparts[2:]:
                        if subpart in doc_types:
                            labels.raw_labels["document_type"] = subpart
                            labels.document_type = subpart.replace(
                                "drvlic", "Driving License"
                            ).title()
                            break
                    break

    return labels


def parse_funsd_plus_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse FUNSD+ (Extended FUNSD) labels.

    Similar to FUNSD but with additional samples.
    Reuses FUNSD annotation format.
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

    if labels.raw_labels is None:
        labels.raw_labels = {}
    labels.raw_labels["document_type"] = "form"
    labels.raw_labels["is_scanned"] = True

    return labels


def parse_sroie_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse SROIE receipt labels from annotation files.

    Structure: {train,test}/{id}.jpg with paired .txt files
    Contains OCR text and key entity annotations.
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Try to find transcription file
    txt_path = image_path.with_suffix(".txt")
    if txt_path.exists():
        try:
            with open(txt_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                # SROIE format: x1,y1,x2,y2,x3,y3,x4,y4,text
                text_instances = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",", 8)
                    if len(parts) >= 9:
                        try:
                            coords = [int(x) for x in parts[:8]]
                            text = parts[8]
                            text_instances.append(
                                {
                                    "bbox": coords,
                                    "text": text,
                                }
                            )
                        except ValueError:
                            continue
                if text_instances:
                    labels.text_instances = text_instances
        except Exception as e:
            logger.debug(f"Failed to parse SROIE annotations: {e}")

    # Extract split from path
    path_str = str(image_path).lower()
    if "train" in path_str:
        labels.raw_labels["split"] = "train"
    elif "test" in path_str:
        labels.raw_labels["split"] = "test"

    labels.raw_labels["document_type"] = "receipt"

    return labels


def parse_mathverse_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse MathVerse Q&A labels.

    Contains mathematical problems with Q&A pairs.
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Try to find metadata JSON
    json_path = image_path.with_suffix(".json")
    if json_path.exists():
        try:
            with open(json_path) as f:
                data = json.load(f)
                labels.raw_labels["question"] = data.get("question")
                labels.raw_labels["answer"] = data.get("answer")
                labels.raw_labels["problem_type"] = data.get("type")
        except Exception:
            pass

    return labels


def parse_nist_sd2_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse NIST Special Database 2 (Tax Form) labels.

    SD2 contains IRS 1040 tax forms with field annotations in .fmt files.
    Each .png image has a companion .fmt file with structured field data.
    """
    labels = OriginalLabels()
    labels.language_code = "en"
    labels.script_name = "Latin"

    if labels.raw_labels is None:
        labels.raw_labels = {}

    labels.raw_labels["form_type"] = "1040"
    labels.raw_labels["document_type"] = "tax_form"

    # Try to find and parse companion .fmt file
    fmt_path = image_path.with_suffix(".fmt")
    if fmt_path.exists():
        try:
            with open(fmt_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if lines:
                    # First line is form ID
                    labels.raw_labels["form_id"] = lines[0].strip()

                    # Extract field count and sample values
                    field_values = []
                    for line in lines[1:]:
                        line = line.strip()
                        if line and " " in line:
                            field_id, value = line.split(" ", 1)
                            if value and value != "_ICON_":
                                field_values.append(value)

                    labels.raw_labels["field_count"] = len(lines) - 1
                    if field_values:
                        labels.raw_labels["has_handwritten_content"] = True
                        # Store first few field values as sample
                        labels.raw_labels["sample_fields"] = field_values[:5]
        except Exception as e:
            logger.debug(f"Failed to parse NIST DB2 .fmt file: {e}")

    return labels


def parse_nist_sd6_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse NIST Special Database 6 (Tax Form) labels.

    SD6 contains IRS 1040 tax forms similar to DB2, with field annotations.
    Each .png image has a companion .fmt file with structured field data.
    """
    labels = OriginalLabels()
    labels.language_code = "en"
    labels.script_name = "Latin"

    if labels.raw_labels is None:
        labels.raw_labels = {}

    labels.raw_labels["form_type"] = "1040"
    labels.raw_labels["document_type"] = "tax_form"

    # Try to find and parse companion .fmt file
    fmt_path = image_path.with_suffix(".fmt")
    if fmt_path.exists():
        try:
            with open(fmt_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if lines:
                    # First line is form ID
                    labels.raw_labels["form_id"] = lines[0].strip()

                    # Extract field count and sample values
                    field_values = []
                    for line in lines[1:]:
                        line = line.strip()
                        if line and " " in line:
                            field_id, value = line.split(" ", 1)
                            if value and value != "_ICON_":
                                field_values.append(value)

                    labels.raw_labels["field_count"] = len(lines) - 1
                    if field_values:
                        labels.raw_labels["has_handwritten_content"] = True
                        # Store first few field values as sample
                        labels.raw_labels["sample_fields"] = field_values[:5]
        except Exception as e:
            logger.debug(f"Failed to parse NIST SD6 .fmt file: {e}")

    return labels


def parse_cvsi_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse CVSI (Character-level Video Script Identification) labels.

    Structure: {Training,Testing,Validation}/{Script}/*.jpg
    10 scripts: Arabic, Bengali, English, Gujrathi, Hindi, Kannada,
    Oriya, Punjabi, Tamil, Telegu
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Script to ISO mappings
    script_mapping = {
        "Arabic": ("ar", "Arab"),
        "Bengali": ("bn", "Beng"),
        "English": ("en", "Latn"),
        "Gujrathi": ("gu", "Gujr"),
        "Hindi": ("hi", "Deva"),
        "Kannada": ("kn", "Knda"),
        "Oriya": ("or", "Orya"),
        "Punjabi": ("pa", "Guru"),
        "Tamil": ("ta", "Taml"),
        "Telegu": ("te", "Telu"),
    }

    # Extract script and split from path
    path_parts = image_path.parts
    for i, part in enumerate(path_parts):
        if part in ("Training", "Testing", "Validation"):
            labels.raw_labels["split"] = part.lower()
            if i + 1 < len(path_parts):
                script_name = path_parts[i + 1]
                labels.raw_labels["script_class"] = script_name
                if script_name in script_mapping:
                    lang_code, iso15924 = script_mapping[script_name]
                    labels.language_code = lang_code
                    labels.script_name = script_name  # Human-readable name
                    labels.iso15924_script_code = iso15924  # ISO 15924
            break

    return labels


def parse_siw13_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse SIW-13 (Script Identification in the Wild) labels.

    Structure: SIW-13/{Training,Testing}/{Script}/*.jpg
    13 scripts: Arabic, Cambodian, Chinese, English, Greek, Hebrew,
    Japanese, Kannada, Korean, Mongolian, Russian, Thai, Tibetan
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Script to ISO mappings
    script_mapping = {
        "Arabic": ("ar", "Arab"),
        "Cambodian": ("km", "Khmr"),
        "Chinese": ("zh", "Hans"),
        "English": ("en", "Latn"),
        "Greek": ("el", "Grek"),
        "Hebrew": ("he", "Hebr"),
        "Japanese": ("ja", "Jpan"),
        "Kannada": ("kn", "Knda"),
        "Korean": ("ko", "Kore"),
        "Mongolian": ("mn", "Mong"),
        "Russian": ("ru", "Cyrl"),
        "Thai": ("th", "Thai"),
        "Tibetan": ("bo", "Tibt"),
    }

    # Extract script and split from path
    path_parts = image_path.parts
    for i, part in enumerate(path_parts):
        if part in ("Training", "Testing"):
            labels.raw_labels["split"] = part.lower()
            if i + 1 < len(path_parts):
                script_name = path_parts[i + 1]
                labels.raw_labels["script_class"] = script_name
                if script_name in script_mapping:
                    lang_code, iso15924 = script_mapping[script_name]
                    labels.language_code = lang_code
                    labels.script_name = script_name  # Human-readable name
                    labels.iso15924_script_code = iso15924  # ISO 15924
            break

    return labels


def parse_mle2e_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse MLE2E (Multi-Language End-to-End) labels.

    Structure: {Training,Testing}/*.jpg with companion .txt annotation files
    4 scripts: Latin, Chinese, Kannada, Korean (Hangul)

    Annotation format: x1,y1,x2,y2,script[,transcription]
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Script to ISO mappings: script -> (language_code, iso15924, human_readable_name)
    script_mapping = {
        "latin": ("en", "Latn", "Latin"),
        "chinese": ("zh", "Hans", "Chinese"),
        "kannada": ("kn", "Knda", "Kannada"),
        "korean": ("ko", "Hang", "Korean"),
    }

    # Extract split and language from path
    # Structure: {Training,Testing}/{language}/*.jpg
    path_parts = image_path.parts
    for i, part in enumerate(path_parts):
        if part == "Training":
            labels.raw_labels["split"] = "train"
            # Check next part for language
            if i + 1 < len(path_parts):
                lang_dir = path_parts[i + 1].lower()
                if lang_dir in script_mapping:
                    lang_code, iso15924, human_name = script_mapping[lang_dir]
                    labels.language_code = lang_code
                    labels.script_name = human_name  # Human-readable name
                    labels.iso15924_script_code = iso15924  # ISO 15924 code
                    labels.raw_labels["script_from_path"] = lang_dir
            break
        if part == "Testing":
            labels.raw_labels["split"] = "test"
            # Check next part for language
            if i + 1 < len(path_parts):
                lang_dir = path_parts[i + 1].lower()
                if lang_dir in script_mapping:
                    lang_code, iso15924, human_name = script_mapping[lang_dir]
                    labels.language_code = lang_code
                    labels.script_name = human_name  # Human-readable name
                    labels.iso15924_script_code = iso15924  # ISO 15924 code
                    labels.raw_labels["script_from_path"] = lang_dir
            break

    # Try to find and parse companion annotation file (may override path-based language)
    txt_path = image_path.with_suffix(".txt")
    if txt_path.exists():
        try:
            with open(txt_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                scripts_found: set[str] = set()
                text_instances: list[dict[str, str]] = []
                for line in lines:
                    line = line.strip()
                    if line:
                        parts = line.split(",")
                        if len(parts) >= 5:
                            script = parts[4].lower()
                            scripts_found.add(script)
                            if len(parts) >= 6:
                                text_instances.append(
                                    {
                                        "script": script,
                                        "text": parts[5],
                                    }
                                )

                if scripts_found:
                    labels.raw_labels["scripts"] = list(scripts_found)
                    # Set primary script based on first found
                    primary_script = next(iter(scripts_found))
                    if primary_script in script_mapping:
                        lang_code, iso15924, human_name = script_mapping[primary_script]
                        labels.language_code = lang_code
                        labels.script_name = human_name  # Human-readable name
                        labels.iso15924_script_code = iso15924  # ISO 15924 code
                if text_instances:
                    labels.text_instances = text_instances[:5]  # Sample
        except Exception as e:
            logger.debug(f"Failed to parse MLE2E annotation: {e}")

    return labels


def parse_omnidocbench_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse OmniDocBench labels from extracted image filenames.

    OmniDocBench structure (after extraction):
        omnidocbench/
            extracted_images/
                {doc_type}_{doc_name}_page_{pagenum}.png

    Document types:
        - PPT: PowerPoint presentations
        - book_en: English books
        - color: Colored documents
        - data: Data/spreadsheet documents
        - docstructbench: Document structure benchmark images
        - eastmoney: Financial documents (eastmoney.com)
        - exam: Examination papers
        - jiaocai: Textbook materials (Chinese)
        - magazine: Magazine pages
        - newspaper: Newspaper articles
        - notes: Handwritten/typed notes
        - scihub: Scientific papers
        - show: Presentation slides
        - yanbaopptmerge: Research report PPTs
        - yanbaor2: Research reports v2

    Extracts:
        - raw_labels.doc_type: Document type prefix
        - raw_labels.doc_name: Document identifier/name
        - raw_labels.page_num: Page number
        - language_code: Language if detectible from name
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    filename = image_path.stem

    # Document type to domain/language/script mapping
    # Format: prefix -> (doc_type, language_code, script_name)
    doc_type_mapping = {
        "PPT": ("presentation", None, None),
        "book_en": ("book", "en", "Latn"),
        "book_eng": ("book", "en", "Latn"),
        "book_zh": ("book", "zh", "Hans"),
        "color": ("document", None, None),
        "data": ("spreadsheet", None, None),
        "docstructbench": ("document", None, None),
        "eastmoney": ("financial", "zh", "Hans"),
        "exam": ("examination", None, None),
        "jiaocai": ("textbook", "zh", "Hans"),  # 教材 = Chinese textbook
        "jiaocaineedrop": ("textbook", "zh", "Hans"),
        "dianzishu": ("ebook", "zh", "Hans"),  # 电子书 = Chinese e-book
        "magazine": ("magazine", None, None),
        "newspaper": ("newspaper", None, None),
        "notes": ("notes", None, None),
        "paper": ("scientific", "en", "Latn"),  # Academic papers, typically English
        "scihub": ("scientific", "en", "Latn"),
        "show": ("presentation", None, None),
        "textbook": ("textbook", "en", "Latn"),  # Generic textbook, default English
        "yanbaopptmerge": ("research_report", "zh", "Hans"),
        "yanbaor2": ("research_report", "zh", "Hans"),
        "pdf": ("document", None, None),  # Generic PDF
    }

    # Try to extract document type from filename prefix
    remainder = filename
    for prefix, (doc_type, lang, script) in doc_type_mapping.items():
        if filename.startswith(prefix):
            labels.raw_labels["doc_type"] = doc_type
            labels.raw_labels["doc_type_prefix"] = prefix
            if lang:
                labels.language_code = lang
            if script:
                labels.script_name = script
            # Extract remaining parts after prefix
            remainder = filename[len(prefix) :].lstrip("_")
            break
    else:
        # Unknown prefix
        labels.raw_labels["doc_type"] = "unknown"

    # Check for language codes in filename if not already set from prefix
    # Patterns: _en_, _eng_, _zh_, _chi_, _chn_, etc.
    if not labels.language_code:
        filename_lower = filename.lower()
        if (
            "_en_" in filename_lower
            or "_eng_" in filename_lower
            or "_english" in filename_lower
        ):
            labels.language_code = "en"
            labels.script_name = "Latn"
        elif (
            "_zh_" in filename_lower
            or "_chi_" in filename_lower
            or "_chn_" in filename_lower
            or "_chinese" in filename_lower
        ):
            labels.language_code = "zh"
            labels.script_name = "Hans"
        elif filename_lower.startswith(("en_", "eng_")):
            labels.language_code = "en"
            labels.script_name = "Latn"
        elif filename_lower.startswith(("zh_", "chi_")):
            labels.language_code = "zh"
            labels.script_name = "Hans"

    # Default to English for certain document types known to be English-majority
    # Note: OmniDocBench has ~30% English, ~60% Chinese, ~10% mixed
    # Only apply defaults to clearly English document types

    # Try to extract page number
    # Pattern: ..._page_XXX or _XXXX at end
    import re

    page_match = re.search(r"_page_(\d+)$", filename)
    if page_match:
        labels.raw_labels["page_num"] = int(page_match.group(1))
        # Document name is everything before _page_
        doc_name_end = filename.rfind("_page_")
        if doc_name_end > 0:
            labels.raw_labels["doc_name"] = filename[:doc_name_end]
    else:
        # Try alternate pattern: _XXXX at end (4 digits)
        page_match = re.search(r"_(\d{3,4})$", filename)
        if page_match:
            labels.raw_labels["page_num"] = int(page_match.group(1))
            labels.raw_labels["doc_name"] = filename[: filename.rfind("_")]

    return labels


def parse_realdae_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse RealDAE (Real-world Document Image Artifact Elimination) labels.

    RealDAE structure:
        realdae/
            task_{type}_{split}/
                {origin}_{number}_{gt|in}.jpg

    Types: bleed (bleed-through), color (color degradation), shadow (shadow removal)
    Splits: train, test
    File types: _in.jpg (input/degraded), _gt.jpg (ground truth/clean)

    Extracts:
        - raw_labels.task_type: bleed, color, or shadow
        - raw_labels.split: train or test
        - raw_labels.is_input: True if *_in.jpg, False if *_gt.jpg
        - raw_labels.paired_file: Path to corresponding gt/in file
        - raw_labels.origin: Origin prefix
        - raw_labels.sample_id: Sample number
    """
    labels = OriginalLabels()

    if labels.raw_labels is None:
        labels.raw_labels = {}

    # Extract task type and split from directory name
    # Pattern: task_{type}_{split} (e.g., task_bleed_train, task_shadow_test)
    path_parts = image_path.parts
    for part in path_parts:
        if part.startswith("task_"):
            parts = part.split("_")
            if len(parts) >= 3:
                labels.raw_labels["task_type"] = parts[1]  # bleed, color, shadow
                labels.raw_labels["split"] = parts[2]  # train, test
            break

    # Parse filename pattern: {origin}_{number}_{gt|in}.jpg
    filename = image_path.stem
    if filename.endswith("_in"):
        labels.raw_labels["is_input"] = True
        labels.raw_labels["is_ground_truth"] = False
        base_name = filename[:-3]  # Remove _in
        gt_file = image_path.parent / f"{base_name}_gt.jpg"
        if gt_file.exists():
            labels.raw_labels["paired_file"] = str(gt_file)
    elif filename.endswith("_gt"):
        labels.raw_labels["is_input"] = False
        labels.raw_labels["is_ground_truth"] = True
        base_name = filename[:-3]  # Remove _gt
        in_file = image_path.parent / f"{base_name}_in.jpg"
        if in_file.exists():
            labels.raw_labels["paired_file"] = str(in_file)

    # Extract origin and sample ID from base name
    # Pattern: origin1000_103 -> origin="origin1000", sample_id="103"
    if "_" in filename:
        name_parts = filename.rsplit("_", 2)  # Split from right, max 2 splits
        if len(name_parts) >= 2:
            labels.raw_labels["origin"] = name_parts[0]
            # Sample ID is the number before _gt/_in
            if len(name_parts) >= 2:
                try:
                    labels.raw_labels["sample_id"] = int(name_parts[1])
                except ValueError:
                    labels.raw_labels["sample_id"] = name_parts[1]

    return labels


def parse_muharaf_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse Muharaf Arabic Historical Manuscripts labels.

    Muharaf contains Arabic handwriting from Lebanese diaspora (19th-21st century).

    Structure:
        muharaf/public/
            *.jpg  - Page images (457 pages)
            *.png  - Line images (24,495 lines)
            *.xml  - PAGE XML annotations
            *.txt  - Text transcriptions (one per line image)

    Extracts:
        - language_code: "ar" (Arabic)
        - script_name: "Arabic"
        - iso15924_script_code: "Arab"
        - transcription: from companion .txt file
        - raw_labels: reading_direction, production type
    """
    labels = OriginalLabels()

    # Set language/script for Arabic handwriting
    labels.language_code = "ar"
    labels.script_name = "Arabic"
    labels.iso15924_script_code = "Arab"

    if labels.raw_labels is None:
        labels.raw_labels = {}

    labels.raw_labels["dataset"] = "muharaf"
    labels.raw_labels["production"] = "handwritten-cursive"
    labels.raw_labels["reading_direction"] = "right-to-left"

    # Determine if page image or line image
    suffix = image_path.suffix.lower()
    if suffix == ".jpg":
        labels.raw_labels["image_type"] = "page"
    elif suffix == ".png":
        labels.raw_labels["image_type"] = "line"

    # Try to read companion .txt file for transcription
    txt_path = image_path.with_suffix(".txt")
    if txt_path.exists():
        try:
            transcription = txt_path.read_text(encoding="utf-8").strip()
            if transcription:
                labels.transcription = transcription
        except Exception:
            logger.debug(f"Failed to read transcription from {txt_path.name}")

    return labels


# Registry of label parsers
LABEL_PARSERS = {
    "parse_diqa_labels": parse_diqa_labels,
    "parse_smartdoc_labels": parse_smartdoc_labels,
    "parse_dibco_labels": parse_dibco_labels,
    "parse_doclaynet_labels": parse_doclaynet_labels,
    "parse_tablebank_labels": parse_tablebank_labels,
    "parse_funsd_labels": parse_funsd_labels,
    "parse_signatr_labels": parse_signatr_labels,
    "parse_ocr_quality_labels": parse_ocr_quality_labels,
    "parse_pucit_ohul_labels": parse_pucit_ohul_labels,
    "parse_multilingual_scripts_labels": parse_multilingual_scripts_labels,
    "parse_rvl_cdip_labels": parse_rvl_cdip_labels,
    "parse_pubtabnet_labels": parse_pubtabnet_labels,
    "parse_fintabnet_labels": parse_fintabnet_labels,
    "parse_im2latex_labels": parse_im2latex_labels,
    "parse_nist_sd19_labels": parse_nist_sd19_labels,
    "parse_mdiw13_labels": parse_mdiw13_labels,
    "parse_cc_ocr_labels": parse_cc_ocr_labels,
    "parse_tibhcr_labels": parse_tibhcr_labels,
    "parse_mlt19_labels": parse_mlt19_labels,
    "parse_arabic_docs_labels": parse_arabic_docs_labels,
    "parse_hindi_synthetic_labels": parse_hindi_synthetic_labels,
    "parse_nepali_handwritten_labels": parse_nepali_handwritten_labels,
    "parse_yarmouk_labels": parse_yarmouk_labels,
    "parse_ohr_bench_labels": parse_ohr_bench_labels,
    "parse_financebench_labels": parse_financebench_labels,
    "parse_midv500_labels": parse_midv500_labels,
    "parse_funsd_plus_labels": parse_funsd_plus_labels,
    "parse_sroie_labels": parse_sroie_labels,
    "parse_mathverse_labels": parse_mathverse_labels,
    "parse_nist_sd2_labels": parse_nist_sd2_labels,
    "parse_nist_sd6_labels": parse_nist_sd6_labels,
    "parse_cvsi_labels": parse_cvsi_labels,
    "parse_siw13_labels": parse_siw13_labels,
    "parse_mle2e_labels": parse_mle2e_labels,
    "parse_realdae_labels": parse_realdae_labels,
    "parse_omnidocbench_labels": parse_omnidocbench_labels,
    "parse_muharaf_labels": parse_muharaf_labels,
}


# =============================================================================
# Tiered Enrichment Logic
# =============================================================================


def get_enrichment_tier(
    dataset_name: str,
    config: dict[str, Any],
    original_labels: OriginalLabels,
    use_yolo: bool,
) -> tuple[EnrichmentTier, str]:
    """Determine the enrichment tier for content flags.

    Returns:
        (tier, description) tuple
    """
    # Tier 0: Exact by construction
    if dataset_name in TIER_0_DATASETS:
        return (
            EnrichmentTier.TIER_0_EXACT,
            "Dataset content type is exact by construction",
        )

    # Tier 1: Has COCO annotations we can derive from
    if dataset_name in TIER_1_DATASETS:
        has_annotations = any(
            [
                original_labels.doclaynet_annotations,
                original_labels.tablebank_annotations,
                original_labels.funsd_annotations,
            ]
        )
        if has_annotations:
            return (
                EnrichmentTier.TIER_1_ANNOTATION,
                "Derived from COCO/JSON annotations",
            )

    # Tier 2: DocLayout-YOLO inference (if enabled)
    if use_yolo:
        return EnrichmentTier.TIER_2_MODEL, "DocLayout-YOLO inference"

    # Tier 3: Dataset-level heuristics (fallback)
    return EnrichmentTier.TIER_3_HEURISTIC, "Dataset-level defaults (fallback)"


def apply_tiered_enrichment(
    sample: SampleMetadata,
    config: dict[str, Any],
    image_path: Path,
    use_yolo: bool,
    git_sha: str,
    existing_openlid: dict[str, Any] | None = None,
) -> EnrichmentData:
    """Apply tiered enrichment logic to determine content flags.

    Tier 0: Exact by construction (dataset IS 100% this content type)
    Tier 1: Derived from COCO/JSON annotations
    Tier 2: DocLayout-YOLO inference
    Tier 3: Dataset-level heuristics (fallback)

    Language/Script Priority:
    1. Ground truth from parser (original_labels.language_code) - highest
    2. Existing OpenLID detection (existing_openlid) - preserve if no ground truth
    3. Dataset defaults - only if no other data available

    Args:
        sample: Sample metadata being enriched
        config: Dataset configuration
        image_path: Path to the image file
        use_yolo: Whether to use DocLayout-YOLO inference
        git_sha: Current git SHA for provenance
        existing_openlid: Optional existing OpenLID-detected language data to preserve
    """
    dataset_name = sample.dataset_name
    original_labels = sample.original_labels

    tier, tier_description = get_enrichment_tier(
        dataset_name, config, original_labels, use_yolo
    )

    # Determine capture_method: prefer parser-derived value over config default
    config_capture = config["capture_method"]
    parser_capture = (
        original_labels.raw_labels.get("capture_method")
        if original_labels.raw_labels
        else None
    )
    if parser_capture:
        capture_method_value = parser_capture
        capture_confidence = 0.95
        capture_detection_method = "parser_ground_truth"
    elif config_capture != CaptureMethod.UNKNOWN:
        capture_method_value = config_capture.value
        capture_confidence = 0.95
        capture_detection_method = "dataset_config"
    else:
        capture_method_value = config_capture.value
        capture_confidence = 0.5
        capture_detection_method = "dataset_config"

    enrichment = EnrichmentData(
        capture_method=capture_method_value,
        capture_confidence=capture_confidence,
        capture_detection_method=capture_detection_method,
        resolution_dpi=sample.original_file.dpi,
        resolution_category=categorize_dpi(sample.original_file.dpi).value,
        resolution_pixels=(
            sample.original_file.width_px,
            sample.original_file.height_px,
        ),
        domain_level1=config["domain"].value,
        domain_confidence=0.9 if config["domain"] != DomainLevel1.UNKNOWN else 0.3,
        content_flags_tier=tier.value,
    )

    # Apply tier-specific logic
    if tier == EnrichmentTier.TIER_0_EXACT:
        # Use exact values from TIER_0_DATASETS
        tier0_flags = TIER_0_DATASETS.get(dataset_name, {})
        enrichment.has_table = tier0_flags.get("has_table", False)
        enrichment.has_formula = tier0_flags.get("has_formula", False)
        enrichment.has_handwriting = tier0_flags.get("has_handwriting", False)
        enrichment.has_signature = tier0_flags.get("has_signature", False)
        enrichment.has_figure = False
        enrichment.content_flags_source = "tier_0_exact_by_construction"

    elif tier == EnrichmentTier.TIER_1_ANNOTATION:
        # Derive from COCO annotations
        annotations = (
            original_labels.doclaynet_annotations
            or original_labels.tablebank_annotations
            or original_labels.funsd_annotations
            or []
        )
        flags = derive_content_flags_from_coco(annotations)
        enrichment.has_table = flags["has_table"]
        enrichment.has_formula = flags["has_formula"]
        enrichment.has_figure = flags["has_figure"]
        enrichment.has_handwriting = flags["has_handwriting"]
        enrichment.content_flags_source = "coco_annotation"

        # Store layout detections
        enrichment.layout_detections = [
            {
                "class_name": ann.get("category_name", "unknown"),
                "bbox": ann.get("bbox", []),
                "confidence": 1.0,
                "source": "coco_annotation",
            }
            for ann in annotations
        ]

    elif tier == EnrichmentTier.TIER_2_MODEL:
        # Run DocLayout-YOLO inference
        yolo_results = run_doclayout_yolo(image_path)
        enrichment.has_table = yolo_results.get("has_table", False)
        enrichment.has_formula = yolo_results.get("has_formula", False)
        enrichment.has_figure = yolo_results.get("has_figure", False)
        enrichment.has_handwriting = yolo_results.get("has_handwriting", False)
        enrichment.layout_detections = yolo_results.get("layout_detections", [])
        enrichment.content_flags_source = "doclayout_yolo"

    else:  # TIER_3_HEURISTIC
        # Fallback to dataset-level defaults
        enrichment.has_table = config.get("has_table")
        enrichment.has_formula = config.get("has_formula")
        enrichment.has_handwriting = config.get("has_handwriting")
        enrichment.has_signature = config.get("has_signature")
        enrichment.has_figure = None
        enrichment.content_flags_source = "dataset_heuristic"

    # === Apply new schema v2.1 fields ===

    # Text scope (from TIER_0_DATASETS or config)
    tier0_flags = TIER_0_DATASETS.get(dataset_name, {})
    enrichment.text_scope = tier0_flags.get("text_scope") or config.get("text_scope")
    if enrichment.has_handwriting:
        enrichment.text_scope_content_type = "handwritten"
    elif enrichment.has_formula:
        enrichment.text_scope_content_type = (
            "printed"  # Most formulas are printed/rendered
        )
    else:
        enrichment.text_scope_content_type = config.get(
            "text_scope_content_type", "printed"
        )
    enrichment.text_scope_detection_method = "dataset_metadata"

    # Language/Script Priority Hierarchy:
    # 1. Ground truth from parser (original_labels) - highest priority
    # 2. Existing OpenLID detection - preserve if no ground truth
    # 3. Dataset defaults - only if no other data available

    # Map script names to ISO 15924 codes
    script_to_iso = {
        "Arabic": "Arab",
        "Tibetan": "Tibt",
        "Japanese": "Jpan",
        "Devanagari": "Deva",
        "Latin": "Latn",
        "Chinese": "Hans",
        "Korean": "Kore",
        "Cyrillic": "Cyrl",
        "Greek": "Grek",
        "Hebrew": "Hebr",
        "Thai": "Thai",
        "Tamil": "Taml",
        "Telugu": "Telu",
        "Bengali": "Beng",
        "Gujarati": "Gujr",
        "Kannada": "Knda",
        "Malayalam": "Mlym",
        "Oriya": "Orya",
        "Punjabi": "Guru",
        "Urdu": "Arab",  # Urdu uses Arabic script
    }

    # Check for ground truth from parser (Priority 1 - highest)
    has_ground_truth_language = bool(
        config.get("iso639_language") or original_labels.language_code
    )
    has_ground_truth_script = bool(
        config.get("iso15924_script") or original_labels.script_name
    )

    # Apply language with priority hierarchy
    if config.get("iso639_language"):
        # Config override (explicit dataset-level ground truth)
        enrichment.iso639_language = config.get("iso639_language")
        enrichment.text_scope_detection_method = "dataset_config"
    elif original_labels.language_code:
        # Parser-extracted ground truth (Priority 1)
        enrichment.iso639_language = original_labels.language_code
        enrichment.text_scope_detection_method = "parser_ground_truth"
    elif existing_openlid and existing_openlid.get("iso639_language"):
        # Preserve existing OpenLID detection (Priority 2)
        enrichment.iso639_language = existing_openlid["iso639_language"]
        enrichment.text_scope_detection_method = existing_openlid.get(
            "text_scope_detection_method", "openlid_v2"
        )
    else:
        # Dataset default fallback (Priority 3 - lowest)
        # Skip default for multilingual datasets - requires per-image detection
        if not config.get("is_multilingual"):
            enrichment.iso639_language = config.get("default_language_code")
            enrichment.text_scope_detection_method = "dataset_default"
        else:
            enrichment.iso639_language = None
            enrichment.text_scope_detection_method = "pending_per_image_detection"

    # Apply script with priority hierarchy
    if config.get("iso15924_script"):
        # Config override (explicit dataset-level ground truth)
        enrichment.iso15924_script = config.get("iso15924_script")
    elif original_labels.script_name:
        # Parser-extracted ground truth (Priority 1)
        enrichment.iso15924_script = script_to_iso.get(
            original_labels.script_name, original_labels.script_name
        )
    elif existing_openlid and existing_openlid.get("iso15924_script"):
        # Preserve existing OpenLID detection (Priority 2)
        enrichment.iso15924_script = existing_openlid["iso15924_script"]
        # Also preserve related OpenLID fields
        enrichment.bcp47_tag = existing_openlid.get("bcp47_tag")
        enrichment.primary_language = existing_openlid.get("primary_language")
        enrichment.language_confidence = existing_openlid.get("language_confidence")
    else:
        # Dataset default fallback (Priority 3 - lowest)
        # Skip default for multilingual datasets - requires per-image detection
        if not config.get("is_multilingual"):
            enrichment.iso15924_script = config.get("default_script_name")
        else:
            enrichment.iso15924_script = None

    # Script family (from config, with auto-derivation from ISO 15924)
    enrichment.script_family = config.get("script_family")
    if enrichment.script_family is None and enrichment.iso15924_script:
        # Centralised lookup from iso_language_script module
        enrichment.script_family = _get_script_family(enrichment.iso15924_script)

    # Paper size (from config if specified)
    enrichment.paper_size = config.get("paper_size")
    if enrichment.paper_size:
        enrichment.paper_size_standard = (
            "iso" if enrichment.paper_size.startswith("A") else "ansi"
        )

    # Dataset short code (standardized identifier)
    enrichment.dataset_short_code = dataset_name.replace("_", "-")

    # === v2.1.0 fields (geometric, physical degradation, ML IQA, code, image properties) ===

    # Code detection: derive from layout detections if available
    if enrichment.layout_detections:
        code_classes = {"code", "source_code", "listing"}
        enrichment.has_code = any(
            det.get("class_name", "").lower() in code_classes
            for det in enrichment.layout_detections
        )
        enrichment.code_confidence = (
            1.0 if tier == EnrichmentTier.TIER_1_ANNOTATION else 0.8
        )
    elif tier == EnrichmentTier.TIER_0_EXACT:
        enrichment.has_code = False
        enrichment.code_confidence = 1.0

    # Resolution enhancement: effective_dpi mirrors resolution_dpi until resampling detection
    enrichment.effective_dpi = sample.original_file.dpi

    # Image properties: color_mode from config or auto-detect, document_age from config
    enrichment.color_mode = config.get("color_mode")
    enrichment.document_age = config.get("document_age")

    # Auto-derive document_age for known historical/degraded datasets
    if enrichment.document_age is None:
        historical_datasets = {"dibco", "historical_degraded"}
        aged_datasets = {"tobacco800", "rvl_cdip"}
        if dataset_name in historical_datasets:
            enrichment.document_age = "historical"
        elif dataset_name in aged_datasets:
            enrichment.document_age = "aged"

    # Geometric, physical degradation, ML IQA, OCR impact:
    # Left as None -- populated by dedicated enrichment passes
    # (production pipeline inference, orientation detection, shadow/warping models)

    return enrichment


# =============================================================================
# OmniDocBench Arrow Extraction
# =============================================================================


def extract_omnidocbench_images(output_dir: Path | None = None) -> int:
    """Extract images from OmniDocBench arrow files.

    Args:
        output_dir: Directory to save extracted images (default: omnidocbench/extracted_images/)

    Returns:
        Number of images extracted
    """
    omnidoc_path = BENCHMARK_ONLY / "omnidocbench" / "train"
    if output_dir is None:
        output_dir = BENCHMARK_ONLY / "omnidocbench" / "extracted_images"

    output_dir.mkdir(parents=True, exist_ok=True)

    total_extracted = 0
    arrow_files = sorted(omnidoc_path.glob("data-*.arrow"))

    logger.info(f"Extracting OmniDocBench images from {len(arrow_files)} arrow files")

    for arrow_path in tqdm(arrow_files, desc="Arrow files"):
        try:
            with open(arrow_path, "rb") as f:
                reader = ipc.open_stream(f)
                table = reader.read_all()

            for i in range(table.num_rows):
                row = table.slice(i, 1).to_pydict()
                img_struct = row["image"][0]

                img_path = img_struct.get("path", f"image_{total_extracted:05d}.png")
                img_bytes = img_struct.get("bytes", b"")

                if img_bytes:
                    # Sanitize filename
                    safe_name = Path(img_path).name.replace("/", "_").replace("\\", "_")
                    output_path = output_dir / safe_name

                    # Save image
                    img = Image.open(io.BytesIO(img_bytes))
                    img.save(output_path)
                    total_extracted += 1

        except Exception as e:
            logger.warning(f"Failed to process {arrow_path}: {e}")

    logger.info(f"Extracted {total_extracted} images to {output_dir}")
    return total_extracted


# =============================================================================
# Main Processing Functions
# =============================================================================


def scan_dataset(
    dataset_name: str,
    config: dict[str, Any],
    limit: int | None = None,
    use_yolo: bool = True,
    existing_openlid_data: dict[str, dict[str, Any]] | None = None,
) -> list[SampleMetadata]:
    """Scan a dataset and create initial metadata records.

    Args:
        dataset_name: Name of the dataset to scan
        config: Dataset configuration dictionary
        limit: Optional limit on number of samples to process
        use_yolo: Whether to use DocLayout-YOLO inference
        existing_openlid_data: Optional dict mapping file_hash to existing
            OpenLID-detected language/script data to preserve
    """
    samples: list[SampleMetadata] = []
    existing_openlid_data = existing_openlid_data or {}

    dataset_path = config["path"]
    pattern = config["pattern"]

    if not dataset_path.exists():
        logger.warning(f"Dataset path not found: {dataset_path}")
        return samples

    # Check for arrow format (special handling)
    if config.get("arrow_format"):
        extracted_dir = dataset_path / "extracted_images"
        if not extracted_dir.exists() or not any(extracted_dir.iterdir()):
            logger.warning(
                f"{dataset_name} requires extraction. Run --extract-omnidocbench first."
            )
            return samples

    # Find all images
    image_files = sorted(dataset_path.glob(pattern))
    if limit:
        image_files = image_files[:limit]

    if not image_files:
        logger.warning(f"No images found for {dataset_name} with pattern {pattern}")
        return samples

    logger.info(f"Scanning {dataset_name}: {len(image_files)} files (YOLO: {use_yolo})")

    # Get git SHA for reproducibility
    git_sha = get_git_sha()

    # Get label parser if specified
    parser_name = config.get("original_labels_parser")
    label_parser = LABEL_PARSERS.get(parser_name) if parser_name else None

    for image_path in tqdm(image_files, desc=f"  {dataset_name}", leave=False):
        # Skip non-image files
        if image_path.suffix.lower() not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".tif",
            ".tiff",
            ".bmp",
        }:
            continue

        # Generate unique ID
        sample_id = str(uuid.uuid4())

        # Compute file hash
        file_hash = compute_sha256(image_path)

        # Extract file metadata
        file_metadata = extract_file_metadata(image_path)

        # Parse original labels if parser available
        if label_parser:
            original_labels = label_parser(dataset_path, image_path)
        else:
            original_labels = OriginalLabels()

        # Create sample metadata
        sample = SampleMetadata(
            id=sample_id,
            file_hash=file_hash,
            dataset_name=dataset_name,
            dataset_version="1.0",
            original_path=str(image_path.relative_to(dataset_path)),
            original_filename=image_path.name,
            download_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            original_labels=original_labels,
            original_file=file_metadata,
        )

        # Extract split from raw_labels if available
        if original_labels.raw_labels and "split" in original_labels.raw_labels:
            sample.split = original_labels.raw_labels["split"]

        # Fallback: detect split from image path if not set by parser
        if sample.split == "unknown":
            path_str_lower = str(image_path).lower()
            for split_name in ["train", "val", "test"]:
                if f"/{split_name}/" in path_str_lower:
                    sample.split = split_name
                    break

        # Apply tiered enrichment
        tier, tier_desc = get_enrichment_tier(
            dataset_name, config, original_labels, use_yolo
        )
        # Check for existing OpenLID data to preserve
        existing_openlid = existing_openlid_data.get(file_hash)
        enrichment = apply_tiered_enrichment(
            sample, config, image_path, use_yolo, git_sha, existing_openlid
        )

        # Add enrichment with reproducibility fields
        sample.add_enrichment(
            data=enrichment,
            created_by=f"annotate_base_metadata.py_v{SCRIPT_VERSION}",
            method=tier.value,
            description=tier_desc,
            git_sha=git_sha,
            model_checkpoint="doclayout_yolo"
            if tier == EnrichmentTier.TIER_2_MODEL
            else None,
        )

        samples.append(sample)

    return samples


def save_metadata_parquet(samples: list[SampleMetadata], output_path: Path) -> None:
    """Save metadata to Parquet format for efficient querying."""
    if not samples:
        logger.warning("No samples to save")
        return

    # Build flat records for Parquet
    records = []
    for sample in samples:
        enrichment = sample.get_current_enrichment()
        version_info = (
            sample.enrichment_versions[-1] if sample.enrichment_versions else None
        )

        record = {
            "sample_id": sample.id,
            "file_hash": sample.file_hash,
            "dataset_name": sample.dataset_name,
            "original_path": sample.original_path,
            "original_filename": sample.original_filename,
            # File metadata
            "width_px": sample.original_file.width_px,
            "height_px": sample.original_file.height_px,
            "file_size_bytes": sample.original_file.file_size_bytes,
            "dpi": sample.original_file.dpi,
            "format": sample.original_file.format,
            # Original labels (human MOS)
            "diqa_mos": sample.original_labels.diqa_mos,
            "ocr_quality_score": sample.original_labels.ocr_quality_score,
            "smartdoc_mos": sample.original_labels.smartdoc_mos,
            # Original labels (handwriting)
            "writer_id": sample.original_labels.writer_id,
            "transcription": sample.original_labels.transcription,
            # Original labels (multilingual)
            "original_language_code": sample.original_labels.language_code,
            "original_script_name": sample.original_labels.script_name,
            # Enrichment data
            "enrichment_version": sample.current_version,
            "enrichment_tier": enrichment.content_flags_tier if enrichment else None,
            "enrichment_source": enrichment.content_flags_source
            if enrichment
            else None,
            "capture_method": enrichment.capture_method if enrichment else None,
            "capture_confidence": enrichment.capture_confidence if enrichment else None,
            "domain_level1": enrichment.domain_level1 if enrichment else None,
            "resolution_category": enrichment.resolution_category
            if enrichment
            else None,
            # Content flags
            "has_table": enrichment.has_table if enrichment else None,
            "has_formula": enrichment.has_formula if enrichment else None,
            "has_handwriting": enrichment.has_handwriting if enrichment else None,
            "has_signature": enrichment.has_signature if enrichment else None,
            "has_figure": enrichment.has_figure if enrichment else None,
            # Language/Script (ISO-compliant)
            "iso639_language": enrichment.iso639_language if enrichment else None,
            "iso15924_script": enrichment.iso15924_script if enrichment else None,
            "script_family": enrichment.script_family if enrichment else None,
            "bcp47_tag": enrichment.bcp47_tag if enrichment else None,
            # Text Scope
            "text_scope": enrichment.text_scope if enrichment else None,
            "text_scope_content_type": (
                enrichment.text_scope_content_type if enrichment else None
            ),
            "text_scope_estimated_chars": (
                enrichment.text_scope_estimated_chars if enrichment else None
            ),
            "text_scope_estimated_words": (
                enrichment.text_scope_estimated_words if enrichment else None
            ),
            # Paper Size
            "paper_size": enrichment.paper_size if enrichment else None,
            "paper_size_standard": enrichment.paper_size_standard
            if enrichment
            else None,
            "paper_size_orientation": (
                enrichment.paper_size_orientation if enrichment else None
            ),
            # Dataset Source
            "dataset_short_code": (
                enrichment.dataset_short_code if enrichment else None
            ),
            # Reproducibility
            "git_sha": version_info.git_sha if version_info else None,
            "model_checkpoint": version_info.model_checkpoint if version_info else None,
            "script_version": version_info.script_version if version_info else None,
            # Element annotations (JSON-serialized for bbox preservation)
            "doclaynet_annotations_json": (
                json.dumps(sample.original_labels.doclaynet_annotations)
                if sample.original_labels.doclaynet_annotations
                else None
            ),
            "tablebank_annotations_json": (
                json.dumps(sample.original_labels.tablebank_annotations)
                if sample.original_labels.tablebank_annotations
                else None
            ),
            "funsd_annotations_json": (
                json.dumps(sample.original_labels.funsd_annotations)
                if sample.original_labels.funsd_annotations
                else None
            ),
            "layout_detections_json": (
                json.dumps(enrichment.layout_detections)
                if enrichment and enrichment.layout_detections
                else None
            ),
            # Derived element counts (for quick filtering)
            "table_count": (
                len(
                    [
                        a
                        for a in (sample.original_labels.doclaynet_annotations or [])
                        if a.get("category_name") == "Table"
                    ]
                )
                + len(sample.original_labels.tablebank_annotations or [])
            ),
            "formula_count": (
                len(
                    [
                        a
                        for a in (sample.original_labels.doclaynet_annotations or [])
                        if a.get("category_name") == "Formula"
                    ]
                )
            ),
            # Timestamps
            "created_at": sample.created_at,
            "schema_version": sample.schema_version,
        }
        records.append(record)

    # Create PyArrow table
    table = pa.Table.from_pylist(records)

    # Save to Parquet
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path, compression="snappy")

    logger.info(f"Saved {len(records)} samples to {output_path}")


def _count_images_on_disk(dataset_name: str) -> int | None:
    """Count total image files on disk for a dataset.

    Resolves path from DATASET_CONFIGS and counts files matching the
    dataset's glob pattern. Returns None if dataset not in configs or
    path not found.
    """
    config = DATASET_CONFIGS.get(dataset_name)
    if not config:
        return None

    dataset_path: Path = config["path"]
    pattern: str = config["pattern"]

    if not dataset_path.exists():
        return None

    image_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
    count = sum(
        1 for f in dataset_path.glob(pattern) if f.suffix.lower() in image_extensions
    )
    return count


def save_metadata_json(samples: list[SampleMetadata], output_dir: Path) -> None:
    """Save full metadata to JSON files (one per dataset)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group by dataset
    by_dataset: dict[str, list[SampleMetadata]] = {}
    for sample in samples:
        if sample.dataset_name not in by_dataset:
            by_dataset[sample.dataset_name] = []
        by_dataset[sample.dataset_name].append(sample)

    for dataset_name, dataset_samples in by_dataset.items():
        output_file = output_dir / f"{dataset_name}_metadata.json"

        # Calculate split coverage
        split_counts: dict[str, int] = {}
        for s in dataset_samples:
            split_counts[s.split] = split_counts.get(s.split, 0) + 1

        # Count total images on disk (independent of limit or processing)
        image_count_on_disk = _count_images_on_disk(dataset_name)

        data = {
            "dataset_name": dataset_name,
            "sample_count": len(dataset_samples),
            "image_count_on_disk": image_count_on_disk,
            "splits_included": list(split_counts.keys()),
            "split_counts": split_counts,
            "created_at": datetime.now(UTC).isoformat(),
            "schema_version": SCHEMA_VERSION,
            "script_version": SCRIPT_VERSION,
            "git_sha": get_git_sha(),
            "samples": [s.to_dict() for s in dataset_samples],
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        disk_info = (
            f" (disk: {image_count_on_disk})" if image_count_on_disk is not None else ""
        )
        logger.info(f"Saved {len(dataset_samples)} samples to {output_file}{disk_info}")


def load_existing_metadata(
    output_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Load existing metadata indexed by file_hash for merge operations.

    This allows preserving OpenLID-detected language/script data when
    re-running the annotation script.

    Args:
        output_dir: Directory containing JSON metadata files

    Returns:
        Dictionary mapping file_hash to existing enrichment data
    """
    existing: dict[str, dict[str, Any]] = {}

    json_dir = output_dir / "json"
    if not json_dir.exists():
        return existing

    for json_file in json_dir.glob("*_metadata.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            for sample in data.get("samples", []):
                file_hash = sample.get("file_hash")
                if not file_hash:
                    continue

                # Extract current enrichment data if available
                enrichment_versions = sample.get("enrichment_versions", [])
                current_version = sample.get("current_version", 0)

                for version in enrichment_versions:
                    if version.get("version") == current_version:
                        enrichment_data = version.get("data", {})
                        # Check if this has OpenLID-detected language data
                        detection_method = enrichment_data.get(
                            "text_scope_detection_method", ""
                        )
                        if "openlid" in detection_method.lower():
                            existing[file_hash] = {
                                "iso639_language": enrichment_data.get(
                                    "iso639_language"
                                ),
                                "iso15924_script": enrichment_data.get(
                                    "iso15924_script"
                                ),
                                "script_family": enrichment_data.get("script_family"),
                                "bcp47_tag": enrichment_data.get("bcp47_tag"),
                                "primary_language": enrichment_data.get(
                                    "primary_language"
                                ),
                                "language_confidence": enrichment_data.get(
                                    "language_confidence"
                                ),
                                "text_scope_detection_method": detection_method,
                            }
                        break

        except Exception as e:
            logger.warning(f"Failed to load existing metadata from {json_file}: {e}")

    if existing:
        logger.info(
            f"Loaded {len(existing)} samples with OpenLID language data to preserve"
        )

    return existing


def generate_statistics(samples: list[SampleMetadata]) -> dict[str, Any]:
    """Generate statistics about the metadata collection."""
    stats: dict[str, Any] = {
        "total_samples": len(samples),
        "by_dataset": {},
        "by_capture_method": {},
        "by_domain": {},
        "by_resolution_category": {},
        "by_enrichment_tier": {},
        "with_human_mos": 0,
        "with_tables": 0,
        "with_formulas": 0,
        "with_handwriting": 0,
    }

    for sample in samples:
        # By dataset
        ds = sample.dataset_name
        if ds not in stats["by_dataset"]:
            stats["by_dataset"][ds] = 0
        stats["by_dataset"][ds] += 1

        enrichment = sample.get_current_enrichment()
        if enrichment:
            # By capture method
            cm = enrichment.capture_method or "unknown"
            if cm not in stats["by_capture_method"]:
                stats["by_capture_method"][cm] = 0
            stats["by_capture_method"][cm] += 1

            # By domain
            domain = enrichment.domain_level1 or "unknown"
            if domain not in stats["by_domain"]:
                stats["by_domain"][domain] = 0
            stats["by_domain"][domain] += 1

            # By DPI category
            res_cat = enrichment.resolution_category or "unknown"
            if res_cat not in stats["by_resolution_category"]:
                stats["by_resolution_category"][res_cat] = 0
            stats["by_resolution_category"][res_cat] += 1

            # By enrichment tier
            tier = enrichment.content_flags_tier or "unknown"
            if tier not in stats["by_enrichment_tier"]:
                stats["by_enrichment_tier"][tier] = 0
            stats["by_enrichment_tier"][tier] += 1

            # Content flags
            if enrichment.has_table:
                stats["with_tables"] += 1
            if enrichment.has_formula:
                stats["with_formulas"] += 1
            if enrichment.has_handwriting:
                stats["with_handwriting"] += 1

        # Human MOS
        labels = sample.original_labels
        if any([labels.diqa_mos, labels.ocr_quality_score, labels.smartdoc_mos]):
            stats["with_human_mos"] += 1

    return stats


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Annotate base dataset images with versioned metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scan all datasets with DocLayout-YOLO (default)
    python scripts/annotate_base_metadata.py --scan

    # Scan without YOLO (use dataset defaults/annotations only)
    python scripts/annotate_base_metadata.py --scan --no-yolo

    # Scan specific dataset
    python scripts/annotate_base_metadata.py --scan --dataset diqa-5000

    # Extract OmniDocBench images first
    python scripts/annotate_base_metadata.py --extract-omnidocbench

    # Generate statistics
    python scripts/annotate_base_metadata.py --stats

    # Export to parquet
    python scripts/annotate_base_metadata.py --export

Enrichment Tiers:
    Tier 0: Exact by construction (dataset IS 100% tables/formulas/etc)
    Tier 1: Derived from COCO/JSON annotations
    Tier 2: DocLayout-YOLO inference (default)
    Tier 3: Dataset-level heuristics (fallback with --no-yolo)
        """,
    )

    parser.add_argument(
        "--scan", action="store_true", help="Scan datasets and create metadata"
    )
    parser.add_argument("--dataset", type=str, help="Specific dataset to process")
    parser.add_argument("--limit", type=int, help="Limit samples per dataset")
    parser.add_argument(
        "--no-yolo",
        action="store_true",
        help="Disable DocLayout-YOLO (use Tier 3 fallback)",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Generate statistics report"
    )
    parser.add_argument("--export", action="store_true", help="Export to Parquet")
    parser.add_argument(
        "--extract-omnidocbench",
        action="store_true",
        help="Extract OmniDocBench images from arrow",
    )
    parser.add_argument(
        "--output", type=Path, default=METADATA_ROOT, help="Output directory"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )

    args = parser.parse_args()

    if not any([args.scan, args.stats, args.export, args.extract_omnidocbench]):
        parser.print_help()
        return

    # Ensure output directory exists
    args.output.mkdir(parents=True, exist_ok=True)

    # Handle OmniDocBench extraction
    if args.extract_omnidocbench:
        logger.info("=" * 70)
        logger.info("OMNIDOCBENCH IMAGE EXTRACTION")
        logger.info("=" * 70)
        count = extract_omnidocbench_images()
        logger.info(f"Extraction complete: {count} images")
        if not args.scan:
            return

    all_samples: list[SampleMetadata] = []
    use_yolo = not args.no_yolo

    if args.scan:
        logger.info("=" * 70)
        logger.info("BASE DATASET METADATA ANNOTATION")
        logger.info(f"Schema Version: {SCHEMA_VERSION}")
        logger.info(f"Script Version: {SCRIPT_VERSION}")
        logger.info(f"Git SHA: {get_git_sha()}")
        logger.info(f"DocLayout-YOLO: {'ENABLED' if use_yolo else 'DISABLED'}")
        logger.info("=" * 70)

        datasets_to_scan = (
            {args.dataset: DATASET_CONFIGS[args.dataset]}
            if args.dataset and args.dataset in DATASET_CONFIGS
            else DATASET_CONFIGS
        )

        if args.dry_run:
            logger.info("DRY RUN - would scan:")
            for name, config in datasets_to_scan.items():
                tier = (
                    "Tier 0"
                    if name in TIER_0_DATASETS
                    else "Tier 1"
                    if name in TIER_1_DATASETS
                    else "Tier 2/3"
                )
                logger.info(f"  {name}: {config['path']} ({tier})")
            return

        # Load existing metadata to preserve OpenLID language/script data
        existing_openlid_data = load_existing_metadata(args.output)

        for dataset_name, config in datasets_to_scan.items():
            samples = scan_dataset(
                dataset_name,
                config,
                limit=args.limit,
                use_yolo=use_yolo,
                existing_openlid_data=existing_openlid_data,
            )
            all_samples.extend(samples)
            logger.info(f"  {dataset_name}: {len(samples)} samples")

        # Save metadata
        logger.info("\nSaving metadata...")

        # JSON (full detail, per dataset)
        save_metadata_json(all_samples, args.output / "json")

        # Parquet (flat, efficient)
        save_metadata_parquet(all_samples, args.output / "samples.parquet")

    if args.stats:
        # Load existing metadata
        parquet_path = args.output / "samples.parquet"
        if parquet_path.exists():
            table = pq.read_table(parquet_path)
            logger.info(f"Loaded {table.num_rows} samples from {parquet_path}")

            # Generate stats from parquet
            df = table.to_pandas()
            stats = {
                "total_samples": len(df),
                "by_dataset": df["dataset_name"].value_counts().to_dict(),
                "by_capture_method": df["capture_method"].value_counts().to_dict(),
                "by_domain": df["domain_level1"].value_counts().to_dict(),
                "by_enrichment_tier": df["enrichment_tier"].value_counts().to_dict(),
                "with_human_mos": df["diqa_mos"].notna().sum()
                + df["ocr_quality_score"].notna().sum(),
                "with_tables": df["has_table"].sum() if "has_table" in df else 0,
                "with_formulas": df["has_formula"].sum() if "has_formula" in df else 0,
            }
        elif all_samples:
            stats = generate_statistics(all_samples)
        else:
            logger.error("No metadata found. Run --scan first.")
            return

        logger.info("\n" + "=" * 70)
        logger.info("METADATA STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total samples: {stats['total_samples']:,}")

        logger.info("\nBy Dataset:")
        for ds, count in sorted(stats["by_dataset"].items(), key=lambda x: -x[1]):
            logger.info(f"  {ds}: {count:,}")

        logger.info("\nBy Enrichment Tier:")
        for tier, count in sorted(
            stats.get("by_enrichment_tier", {}).items(), key=lambda x: -x[1]
        ):
            logger.info(f"  {tier}: {count:,}")

        logger.info("\nBy Capture Method:")
        for cm, count in sorted(
            stats.get("by_capture_method", {}).items(), key=lambda x: -x[1]
        ):
            logger.info(f"  {cm}: {count:,}")

        logger.info("\nBy Domain:")
        for domain, count in sorted(
            stats.get("by_domain", {}).items(), key=lambda x: -x[1]
        ):
            logger.info(f"  {domain}: {count:,}")

        logger.info(f"\nWith Human MOS: {stats.get('with_human_mos', 0):,}")
        logger.info(f"With Tables: {stats.get('with_tables', 0):,}")
        logger.info(f"With Formulas: {stats.get('with_formulas', 0):,}")

    if args.export:
        parquet_path = args.output / "samples.parquet"
        if parquet_path.exists():
            logger.info(f"Parquet export already exists: {parquet_path}")
        elif all_samples:
            save_metadata_parquet(all_samples, parquet_path)
        else:
            logger.error("No metadata to export. Run --scan first.")


if __name__ == "__main__":
    main()
