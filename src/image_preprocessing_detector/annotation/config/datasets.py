# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Dataset configuration registry for annotation metadata extraction.

This module provides typed configuration for all supported datasets,
replacing hardcoded paths in the monolithic annotate_base_metadata.py.

Key Components:
    - DatasetConfig: Frozen dataclass for dataset configuration
    - DATASET_CONFIGS: Registry of all 44 datasets
    - Helper functions: Path resolution and validation

Configuration Categories:
    - Benchmark datasets (4): diqa-5000, smartdoc-qa, dibco, omnidocbench
    - Base Training - Degraded (2): tobacco800, historical_degraded
    - Base Training - Documents (2): rvl_cdip, doclaynet
    - Base Training - Forms (5): nist-sd2, nist_sd6, funsd, funsd_plus, sroie
    - Base Training - Tables (3): tablebank, pubtabnet, fintabnet
    - Base Training - Handwriting (3): nist_sd19, signatr6k, maths_handwriting
    - Base Training - Formulas (2): im2latex, mathverse
    - Base Training - Educational (1): multimodal_textbook
    - Camera-captured (1): realdae
    - OCR Quality (1): ocr_quality
    - Correction/Shadow/Dewarping (6): anyphotodoc6300, docalign12k, wsrd,
      warpdoc, docreal, sd7k
    - Multilingual/Script (13): Various script and language datasets
    - Script Identification (3): cvsi, siw13, mle2e
    - OHR-Bench (1): ohr-bench

Example:
    >>> from image_preprocessing_detector.annotation.config.datasets import (
    ...     DATASET_CONFIGS,
    ...     DatasetConfig,
    ...     get_dataset_path,
    ... )
    >>>
    >>> # Get dataset configuration
    >>> diqa = DATASET_CONFIGS["diqa-5000"]
    >>> print(diqa.name)  # "diqa-5000"
    >>> print(diqa.capture_method)  # CaptureMethod.UNKNOWN
    >>>
    >>> # Resolve full path
    >>> from image_preprocessing_detector.annotation.config import AnnotationSettings
    >>> settings = AnnotationSettings.from_env()
    >>> full_path = get_dataset_path(diqa, settings)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..schemas.enums import CaptureMethod, DomainLevel1
from .settings import AnnotationSettings


@dataclass(frozen=True)
class DatasetConfig:
    """Configuration for a single dataset.

    All fields are immutable (frozen=True) to ensure configuration stability.
    Uses path suffixes for portability across environments.

    Attributes:
        name: Unique dataset identifier (matches DATASET_CONFIGS key)
        path_suffix: Path relative to e_drive_root (e.g., "01_base_data/tables/tablebank")
        pattern: Glob pattern for finding images (e.g., "**/*.jpg")
        capture_method: How the document was captured/digitized
        domain: Primary document domain classification
        is_benchmark: True if dataset is in BENCHMARK_ONLY (not BASE_DATA)
        has_human_mos: True if dataset contains human Mean Opinion Scores

        # Optional content flags (Tier 0 exact)
        has_table: Guaranteed table presence (True/False) or None (unknown)
        has_formula: Guaranteed formula presence (True/False) or None (unknown)
        has_handwriting: Guaranteed handwriting presence (True/False) or None (unknown)
        has_signature: Guaranteed signature presence (True/False) or None (unknown)

        # Parser reference
        parser_name: Name of parser function (e.g., "diqa" for DIQAParser)

        # Special flags
        has_coco_annotations: True if dataset has COCO-format annotations
        arrow_format: True if dataset requires Arrow format extraction
        has_paired_gt: True if dataset has pixel-aligned ground truth

        # Multilingual fields
        iso639_language: ISO 639-1 or 639-3 language code (e.g., "ur", "ar")
        iso15924_script: ISO 15924 script code (e.g., "Arab", "Deva")
        text_scope: Text granularity level (word/line/phrase/paragraph/page/mixed)
        paper_size: Physical paper size if known (e.g., "A4", "Letter")

        # Dataset-specific
        mos_file: Path to MOS scores file relative to dataset root
    """

    # Required fields
    name: str
    path_suffix: str
    pattern: str
    capture_method: CaptureMethod
    domain: DomainLevel1
    is_benchmark: bool = False
    has_human_mos: bool = False

    # Optional content flags (Tier 0 exact)
    has_table: bool | None = None
    has_formula: bool | None = None
    has_handwriting: bool | None = None
    has_signature: bool | None = None

    # Parser reference
    parser_name: str | None = None

    # Special flags
    has_coco_annotations: bool = False
    arrow_format: bool = False
    has_paired_gt: bool = False

    # Multilingual fields
    iso639_language: str | None = None
    iso15924_script: str | None = None
    text_scope: str | None = None
    paper_size: str | None = None

    # Dataset-specific
    mos_file: str | None = None


def get_dataset_path(config: DatasetConfig, settings: AnnotationSettings) -> Path:
    """Resolve full path for a dataset.

    Args:
        config: Dataset configuration
        settings: AnnotationSettings instance with e_drive_root

    Returns:
        Full resolved path to dataset directory

    Example:
        >>> settings = AnnotationSettings(e_drive_root=Path("/mnt/e/image_detection"))
        >>> config = DATASET_CONFIGS["diqa-5000"]
        >>> path = get_dataset_path(config, settings)
        >>> print(path)  # /mnt/e/image_detection/02_benchmark_only/diqa-5000
    """
    return settings.e_drive_root / config.path_suffix


def is_benchmark_dataset(config: DatasetConfig) -> bool:
    """Check if dataset is a benchmark dataset.

    Args:
        config: Dataset configuration

    Returns:
        True if dataset is in BENCHMARK_ONLY, False if in BASE_DATA
    """
    return config.is_benchmark


def get_parser_module_name(config: DatasetConfig) -> str | None:
    """Get parser module name from parser_name.

    Maps parser_name to module path in parsers/ directory.

    Args:
        config: Dataset configuration

    Returns:
        Module name (e.g., "diqa_parser") or None if no parser

    Example:
        >>> config = DATASET_CONFIGS["diqa-5000"]
        >>> module = get_parser_module_name(config)
        >>> print(module)  # "diqa_parser"
    """
    if config.parser_name is None:
        return None
    # Convert parser_name to module name (e.g., "diqa" -> "diqa_parser")
    return f"{config.parser_name}_parser"


# =============================================================================
# Common Glob Patterns (S1192: avoid duplicate string literals)
# =============================================================================
JPG_GLOB = "**/*.jpg"
PNG_GLOB = "**/*.png"
IMAGES_JPG_GLOB = "images/*.jpg"

# =============================================================================
# Dataset Configuration Registry
# =============================================================================

DATASET_CONFIGS: dict[str, DatasetConfig] = {
    # =========================================================================
    # Benchmark Datasets (4)
    # =========================================================================
    "diqa-5000": DatasetConfig(
        name="diqa-5000",
        path_suffix="02_benchmark_only/diqa-5000",
        # Include both ori/ (original scanned) and res/ (synthetic degradation) images
        # Parser detects folder and sets is_synthetic_degradation accordingly
        pattern=JPG_GLOB,  # train/{ori,res}/, val/{ori,res}/, test/{ori,res}/
        capture_method=CaptureMethod.UNKNOWN,  # Determined per-image by parser
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=True,
        has_human_mos=True,
        mos_file="train/train.csv",
        parser_name="diqa",
    ),
    "smartdoc-qa": DatasetConfig(
        name="smartdoc-qa",
        path_suffix="02_benchmark_only/smartdoc-qa",
        pattern="Dataset SmartDoc-QA/Captured_Images/**/*.jpg",
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=True,
        has_human_mos=True,
        parser_name="smartdoc",
    ),
    "dibco": DatasetConfig(
        name="dibco",
        path_suffix="02_benchmark_only/dibco",
        pattern="DIBCO/**/*.*",
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=True,
        has_human_mos=False,
        has_handwriting=True,  # Historical docs with handwriting
        parser_name="dibco",
    ),
    "omnidocbench": DatasetConfig(
        name="omnidocbench",
        path_suffix="02_benchmark_only/omnidocbench",
        pattern="extracted_images/*.png",  # After extraction
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=True,
        has_human_mos=False,
        arrow_format=True,  # Special handling needed
        parser_name="omnidocbench",
    ),
    # =========================================================================
    # Base Training - Degraded (2)
    # =========================================================================
    "tobacco800": DatasetConfig(
        name="tobacco800",
        path_suffix="01_base_data/degraded/tobacco800",
        pattern="images/*.png",
        capture_method=CaptureMethod.SCANNER_ADF,
        domain=DomainLevel1.ADMINISTRATIVE,
        is_benchmark=False,
        has_human_mos=False,
        parser_name="tobacco800",
    ),
    "historical_degraded": DatasetConfig(
        name="historical_degraded",
        path_suffix="01_base_data/degraded/historical_degraded",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        has_handwriting=True,
        parser_name="generic",
    ),
    # =========================================================================
    # Base Training - Documents (2)
    # =========================================================================
    "rvl_cdip": DatasetConfig(
        name="rvl_cdip",
        path_suffix="01_base_data/documents/rvl_cdip",
        pattern=IMAGES_JPG_GLOB,
        capture_method=CaptureMethod.SCANNER_ADF,
        domain=DomainLevel1.ADMINISTRATIVE,
        is_benchmark=False,
        has_human_mos=False,
        parser_name="rvl_cdip",
    ),
    "doclaynet": DatasetConfig(
        name="doclaynet",
        path_suffix="01_base_data/documents/doclaynet",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        has_coco_annotations=True,
        parser_name="doclaynet",
    ),
    # =========================================================================
    # Base Training - Forms (5)
    # =========================================================================
    "nist-sd2": DatasetConfig(
        name="nist-sd2",
        path_suffix="01_base_data/forms/nist-sd2",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.FINANCIAL,
        is_benchmark=False,
        has_human_mos=False,
        has_table=True,
        has_handwriting=True,
        has_signature=True,
        parser_name="nist-sd2",
    ),
    "nist_sd6": DatasetConfig(
        name="nist_sd6",
        path_suffix="01_base_data/forms/nist_sd6",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.TAX,
        is_benchmark=False,
        has_human_mos=False,
        has_table=True,
        parser_name="nist_sd6",
    ),
    "funsd": DatasetConfig(
        name="funsd",
        path_suffix="01_base_data/forms/funsd",
        pattern=IMAGES_JPG_GLOB,  # Images converted to JPG format
        capture_method=CaptureMethod.SCANNER_ADF,
        domain=DomainLevel1.ADMINISTRATIVE,
        is_benchmark=False,
        has_human_mos=False,
        has_table=True,
        has_handwriting=True,
        has_signature=True,
        parser_name="funsd",
    ),
    "funsd_plus": DatasetConfig(
        name="funsd_plus",
        path_suffix="01_base_data/forms/funsd_plus",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.SCANNER_ADF,
        domain=DomainLevel1.ADMINISTRATIVE,
        is_benchmark=False,
        has_human_mos=False,
        has_table=True,
        has_handwriting=True,
        has_signature=True,
        parser_name="funsd_plus",
    ),
    "sroie": DatasetConfig(
        name="sroie",
        path_suffix="01_base_data/forms/sroie_icdar2019",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.FINANCIAL,
        is_benchmark=False,
        has_human_mos=False,
        has_table=True,
        parser_name="sroie",
    ),
    # =========================================================================
    # Base Training - Tables (3)
    # =========================================================================
    "tablebank": DatasetConfig(
        name="tablebank",
        path_suffix="01_base_data/tables/tablebank",
        pattern="**/images/*.jpg",
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.SCIENTIFIC,
        is_benchmark=False,
        has_human_mos=False,
        has_coco_annotations=True,
        # Tier 0: 100% tables by definition
        has_table=True,
        has_formula=False,
        has_handwriting=False,
        has_signature=False,
        parser_name="tablebank",
    ),
    "pubtabnet": DatasetConfig(
        name="pubtabnet",
        path_suffix="01_base_data/tables/pubtabnet",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.SCIENTIFIC,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% tables by definition
        has_table=True,
        has_formula=False,
        has_handwriting=False,
        has_signature=False,
        parser_name="pubtabnet",
    ),
    "fintabnet": DatasetConfig(
        name="fintabnet",
        path_suffix="01_base_data/tables/fintabnet",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.FINANCIAL,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% tables by definition
        has_table=True,
        has_formula=False,
        has_handwriting=False,
        has_signature=False,
        parser_name="fintabnet",
    ),
    # =========================================================================
    # Base Training - Handwriting (3)
    # =========================================================================
    "nist_sd19": DatasetConfig(
        name="nist_sd19",
        path_suffix="01_base_data/handwriting/nist-sd19",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.PERSONAL,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% handwriting by definition
        has_table=False,
        has_formula=False,
        has_handwriting=True,
        has_signature=False,
        parser_name="nist_sd19",
    ),
    "signatr6k": DatasetConfig(
        name="signatr6k",
        path_suffix="01_base_data/handwriting/signatr6k",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.PERSONAL,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% signatures by definition
        has_table=False,
        has_formula=False,
        has_handwriting=True,
        has_signature=True,
        parser_name="signatr",
    ),
    "maths_handwriting": DatasetConfig(
        name="maths_handwriting",
        path_suffix="01_base_data/handwriting/maths_handwriting",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.EDUCATIONAL,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% handwritten formulas by definition
        has_table=False,
        has_formula=True,
        has_handwriting=True,
        has_signature=False,
        parser_name="maths_handwriting",
    ),
    "muharaf": DatasetConfig(
        name="muharaf",
        path_suffix="01_base_data/handwriting/muharaf/public",
        pattern="**/*.{jpg,png}",
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.PERSONAL,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% Arabic handwritten historical manuscripts
        has_table=False,
        has_formula=False,
        has_handwriting=True,
        has_signature=True,  # Some regions marked as signature-mark
        parser_name="muharaf",
        iso639_language="ar",
        iso15924_script="Arab",
        text_scope="line",  # Line-level transcriptions
    ),
    "iam": DatasetConfig(
        name="iam",
        path_suffix="01_base_data/handwriting/iam_handwriting",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.ADMINISTRATIVE,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% English handwriting by definition
        has_table=False,
        has_formula=False,
        has_handwriting=True,
        has_signature=False,
        parser_name="iam",
        iso639_language="en",
        iso15924_script="Latn",
        text_scope="mixed",  # Forms, lines, and words
    ),
    # HASYv2 - Original dataset with full labels (168,233 images, 369 classes)
    "hasyv2": DatasetConfig(
        name="hasyv2",
        path_suffix="01_base_data/handwriting/hasy/hasy-data",
        pattern="*.png",
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.EDUCATIONAL,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% handwritten mathematical symbols by definition
        has_table=False,
        has_formula=True,
        has_handwriting=True,
        has_signature=False,
        parser_name="hasyv2",
    ),
    # =========================================================================
    # Base Training - Formulas (2)
    # =========================================================================
    "im2latex": DatasetConfig(
        name="im2latex",
        path_suffix="01_base_data/formulas/im2latex",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.SCIENTIFIC,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% formulas by definition
        has_table=False,
        has_formula=True,
        has_handwriting=False,
        has_signature=False,
        parser_name="generic",  # No structured labels, just formula images
    ),
    "mathverse": DatasetConfig(
        name="mathverse",
        path_suffix="01_base_data/formulas/mathverse",
        pattern=IMAGES_JPG_GLOB,
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.EDUCATIONAL,
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: 100% formulas by definition
        has_table=False,
        has_formula=True,
        has_handwriting=False,
        has_signature=False,
        parser_name="generic",  # No structured labels, visual reasoning dataset
    ),
    # =========================================================================
    # Base Training - Educational (1)
    # =========================================================================
    "multimodal_textbook": DatasetConfig(
        name="multimodal_textbook",
        path_suffix="01_base_data/educational/multimodal_textbook",
        pattern="example_data/sample_100_images/*.jpg",
        capture_method=CaptureMethod.BORN_DIGITAL,
        domain=DomainLevel1.EDUCATIONAL,
        is_benchmark=False,
        has_human_mos=False,
        parser_name="multimodal_textbook",
    ),
    # =========================================================================
    # Camera-captured (1)  # noqa: ERA001
    # =========================================================================
    "realdae": DatasetConfig(
        name="realdae",
        path_suffix="01_base_data/camera_captured/realdae",
        pattern="**/*_in.jpg",  # Only input images, not GT
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        has_paired_gt=True,  # Has pixel-aligned ground truth
        parser_name="realdae",
    ),
    # =========================================================================
    # OCR Quality (1)
    # =========================================================================
    "ocr_quality": DatasetConfig(
        name="ocr_quality",
        path_suffix="01_base_data/ocr_quality",
        pattern="pics/*.png",
        capture_method=CaptureMethod.UNKNOWN,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=True,  # Has human quality scores 1-4
        parser_name="ocr_quality",
    ),
    # =========================================================================
    # Multilingual/Script Detection Datasets (13)
    # =========================================================================
    "pucit_ohul": DatasetConfig(
        name="pucit_ohul",
        path_suffix="01_base_data/language/pucit-ohul",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.EDUCATIONAL,
        is_benchmark=False,
        has_human_mos=False,
        has_handwriting=True,
        iso639_language="ur",  # Urdu
        iso15924_script="Arab",  # Arabic script
        text_scope="word",
        parser_name="pucit_ohul",
    ),
    "multilingual_scripts": DatasetConfig(
        name="multilingual_scripts",
        path_suffix="01_base_data/language/multilingual_scripts",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.UNKNOWN,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        text_scope="mixed",
        parser_name="multilingual_scripts",
    ),
    "midv500": DatasetConfig(
        name="midv500",
        path_suffix="01_base_data/language/midv500_data/midv500",
        pattern="**/*.tif",
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.PERSONAL,  # ID documents
        is_benchmark=False,
        has_human_mos=False,
        text_scope="page",
        parser_name="midv500",
    ),
    "bhutan_financial": DatasetConfig(
        name="bhutan_financial",
        path_suffix="01_base_data/documents/bhutan_financial",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.FINANCIAL,
        is_benchmark=False,
        has_human_mos=False,
        has_table=True,
        text_scope="page",
        paper_size="A4",
        parser_name="generic",  # Generic parser for docs without ground truth labels
    ),
    "mdiw13": DatasetConfig(
        name="mdiw13",
        path_suffix="01_base_data/language/mdiw13",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.UNKNOWN,  # Mixed domains
        is_benchmark=False,
        has_human_mos=False,
        has_handwriting=True,  # Includes handwritten letters
        text_scope="word",
        # Multi-script: 13 scripts (Arabic, Bengali, Gujarati, etc.)
        parser_name="mdiw13",
    ),
    "cc_ocr": DatasetConfig(
        name="cc_ocr",
        path_suffix="01_base_data/language/huggingface_downloads/CC-OCR/extracted_images",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.UNKNOWN,  # Mixed (41% real-world, 59% synthetic)
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        text_scope="mixed",
        # CJK Mixed: Chinese (Simplified + Traditional), English, Multilingual
        parser_name="cc_ocr",
    ),
    "cocotext": DatasetConfig(
        name="cocotext",
        path_suffix="01_base_data/text_detection/cocotext/images",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,  # COCO natural images
        domain=DomainLevel1.UNKNOWN,  # Various scene types
        is_benchmark=False,
        has_human_mos=False,
        text_scope="word",
        # Multi-language scene text detection
        parser_name="cocotext",
    ),
    "tibhcr": DatasetConfig(
        name="tibhcr",
        path_suffix="01_base_data/language/huggingface_downloads/TibHCR/TibHCR",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.PERSONAL,  # Handwritten characters
        is_benchmark=False,
        has_human_mos=False,
        has_handwriting=True,
        iso15924_script="Tibt",  # Tibetan script
        text_scope="word",
        parser_name="tibhcr",
    ),
    "mlt19": DatasetConfig(
        name="mlt19",
        path_suffix="01_base_data/language/mlt19",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        text_scope="phrase",
        # 10 languages: Arabic, Bangla, Chinese, Japanese, Korean, Latin, Hindi
        parser_name="mlt19",
    ),
    "arabic_docs_ocr": DatasetConfig(
        name="arabic_docs_ocr",
        path_suffix="01_base_data/language/arabic_docs_ocr",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        iso639_language="ar",  # Arabic
        iso15924_script="Arab",  # Arabic script
        text_scope="page",
        parser_name="arabic_docs",
    ),
    "hindi_ocr_synthetic": DatasetConfig(
        name="hindi_ocr_synthetic",
        path_suffix="01_base_data/language/hindi_ocr_synthetic",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.BORN_DIGITAL,  # Synthetic
        domain=DomainLevel1.EDUCATIONAL,
        is_benchmark=False,
        has_human_mos=False,
        iso639_language="hi",  # Hindi
        iso15924_script="Deva",  # Devanagari
        text_scope="line",
        parser_name="hindi_synthetic",
    ),
    "nepali_handwritten": DatasetConfig(
        name="nepali_handwritten",
        path_suffix="01_base_data/language/nepali_handwritten",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.EDUCATIONAL,
        is_benchmark=False,
        has_human_mos=False,
        has_handwriting=True,
        iso639_language="ne",  # Nepali
        iso15924_script="Deva",  # Devanagari
        text_scope="word",
        parser_name="nepali_handwritten",
    ),
    "yarmouk_ocr": DatasetConfig(
        name="yarmouk_ocr",
        path_suffix="01_base_data/language/yarmouk",
        pattern=PNG_GLOB,
        capture_method=CaptureMethod.SCANNER_FLATBED,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        iso639_language="ar",  # Arabic
        iso15924_script="Arab",  # Arabic script
        text_scope="page",
        parser_name="yarmouk",
    ),
    # =========================================================================
    # Script Identification Datasets (3)
    # =========================================================================
    "cvsi": DatasetConfig(
        name="cvsi",
        path_suffix="01_base_data/language/cvsi",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        text_scope="word",
        # 10 Indic scripts: Arabic, Bengali, English, Gujarati, Hindi, etc.
        parser_name="cvsi",
    ),
    "siw13": DatasetConfig(
        name="siw13",
        path_suffix="01_base_data/language/siw13",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        text_scope="word",
        # 13 scripts: Arabic, Cambodian, Chinese, English, Greek, Hebrew, etc.
        parser_name="siw13",
    ),
    "mle2e": DatasetConfig(
        name="mle2e",
        path_suffix="01_base_data/language/mle2e",
        pattern=JPG_GLOB,
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,  # Scene text
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_human_mos=False,
        text_scope="line",
        # 4 scripts: Latin, Chinese, Kannada, Korean (Hangul)
        parser_name="mle2e",
    ),
    # =========================================================================
    # OHR-Bench (1)  # noqa: ERA001
    # =========================================================================
    "ohr-bench": DatasetConfig(
        name="ohr-bench",
        path_suffix="02_benchmark_only/ohr-bench",
        pattern="extracted_images/**/*.png",  # After extraction (nested by domain)
        capture_method=CaptureMethod.UNKNOWN,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=True,
        has_human_mos=False,
        arrow_format=True,  # Needs extraction like omnidocbench
        parser_name="ohr_bench",
    ),
    # =========================================================================
    # FinanceBench (1) - SEC Financial Documents
    # =========================================================================
    "financebench": DatasetConfig(
        name="financebench",
        path_suffix="02_benchmark_only/financebench",
        pattern="extracted_images/*.png",  # After PDF extraction
        capture_method=CaptureMethod.BORN_DIGITAL,  # SEC filings are born digital
        domain=DomainLevel1.FINANCIAL,
        is_benchmark=True,
        has_human_mos=False,
        # Tier 0: SEC filings contain tables but no formulas/handwriting
        has_table=True,
        has_formula=False,
        has_handwriting=False,
        has_signature=False,
        parser_name="financebench",
    ),
    # =========================================================================
    # Generated Training Datasets (03_training_datasets)
    # =========================================================================
    "synth-multiscript-250k": DatasetConfig(
        name="synth-multiscript-250k",
        path_suffix="03_training_datasets/synthetic_multiscript",
        pattern=PNG_GLOB,  # Images organized by script: {Script}/*.png
        capture_method=CaptureMethod.BORN_DIGITAL,  # Synthetic generation
        domain=DomainLevel1.UNKNOWN,  # Mixed domains
        is_benchmark=False,
        has_human_mos=False,
        # Tier 0: Pure synthetic text documents
        has_table=False,
        has_formula=False,
        has_handwriting=False,
        has_signature=False,
        text_scope="paragraph",
        # Multi-script: 27 scripts (Arab, Latn, Hans, Deva, etc.)
        parser_name="synth_multiscript",
    ),
    # =========================================================================
    # Base Training - Correction / Shadow Removal / Dewarping (6)
    # =========================================================================
    "anyphotodoc6300": DatasetConfig(
        name="anyphotodoc6300",
        path_suffix="01_base_data/correction/anyphotodoc6300",
        pattern="init_*/*.[jJ][pP][gG]",  # Camera-captured; mixed .JPG/.jpg case
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_paired_gt=True,
        parser_name="anyphotodoc6300",
    ),
    "docalign12k": DatasetConfig(
        name="docalign12k",
        path_suffix="01_base_data/correction/docalign12k",
        pattern="distorted_hard/**/*.jpg",  # Distorted inputs; flat/ has GT
        capture_method=CaptureMethod.SYNTHETIC,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_paired_gt=True,
        parser_name="docalign12k",
    ),
    "wsrd": DatasetConfig(
        name="wsrd",
        path_suffix="01_base_data/correction/wsrd",
        pattern="**/*.png",  # NTIRE 2023+2024 shadow/shadow_free pairs
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_paired_gt=True,
        parser_name="wsrd",
    ),
    "warpdoc": DatasetConfig(
        name="warpdoc",
        path_suffix="01_base_data/correction/warpdoc",
        pattern="WarpDoc/image/**/*.jpg",  # Camera-captured warped; digital/ has GT
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_paired_gt=True,
        parser_name="warpdoc",
    ),
    "docreal": DatasetConfig(
        name="docreal",
        path_suffix="01_base_data/correction/docreal",
        pattern="DocReal/distorted/*.png",  # 201 distorted; scanned/ has 50 GT
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_paired_gt=True,
        parser_name="docreal",
    ),
    "sd7k": DatasetConfig(
        name="sd7k",
        path_suffix="01_base_data/correction/sd7k",
        pattern="**/input/*.png",  # Only input images, not ground truth targets
        capture_method=CaptureMethod.CAMERA_SMARTPHONE,
        domain=DomainLevel1.UNKNOWN,
        is_benchmark=False,
        has_paired_gt=True,
        parser_name="sd7k",
    ),
}


def validate_dataset_configs() -> list[str]:
    """Validate all dataset configurations for consistency.

    Checks:
        - All keys match config.name
        - Path suffixes are valid
        - Parser names are lowercase snake_case
        - Multilingual fields are consistent

    Returns:
        List of validation error messages (empty if valid)
    """
    issues: list[str] = []

    for key, config in DATASET_CONFIGS.items():
        # Check key matches name
        if key != config.name:
            issues.append(f"Key '{key}' does not match config.name '{config.name}'")

        # Check path suffix doesn't start with /
        if config.path_suffix.startswith("/"):
            issues.append(f"{config.name}: path_suffix should not start with /")

        # Check parser name is lowercase snake_case
        if config.parser_name and (
            config.parser_name != config.parser_name.lower()
            or " " in config.parser_name
        ):
            issues.append(
                f"{config.name}: parser_name should be lowercase snake_case, got '{config.parser_name}'"
            )

        # Check multilingual consistency
        if config.iso639_language and not config.iso15924_script:
            issues.append(
                f"{config.name}: has iso639_language but missing iso15924_script"
            )

        # Check is_benchmark consistency with path_suffix
        if config.is_benchmark and not config.path_suffix.startswith(
            "02_benchmark_only"
        ):
            issues.append(
                f"{config.name}: is_benchmark=True but path not in 02_benchmark_only/"
            )
        # Non-benchmark datasets can be in 01_base_data or 03_training_datasets
        valid_non_benchmark_prefixes = ("01_base_data", "03_training_datasets")
        if not config.is_benchmark and not config.path_suffix.startswith(
            valid_non_benchmark_prefixes
        ):
            issues.append(
                f"{config.name}: is_benchmark=False but path not in {valid_non_benchmark_prefixes}"
            )

    return issues


__all__ = [
    "DATASET_CONFIGS",
    "DatasetConfig",
    "get_dataset_path",
    "get_parser_module_name",
    "is_benchmark_dataset",
    "validate_dataset_configs",
]
