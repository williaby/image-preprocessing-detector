"""Dataset Source Tracking for Document Image Samples.

Provides standardized vocabulary and utilities for tracking the provenance
of document image samples back to their original source datasets.

Key Concepts:
- Each sample has a unique sample_id (UUID) for cross-layer linking
- source_info maps to the original dataset (name, version, path)
- file_hash provides integrity verification via SHA-256
- Enrichments are versioned separately from source data

Supported Dataset Types:
- IQA Benchmarks: DIQA, SmartDoc-QA, DIBCO, OCR-Quality
- Document Layout: DocLayNet, PubLayNet, FUNSD, TableBank
- Handwriting: IAM, CVL, RIMES
- Scene Text: COCO-Text, ICDAR
- Specialized: SignaTR, OmniDocBench, RealDAE
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class DatasetCategory(str, Enum):
    """High-level dataset category classification."""

    IQA_BENCHMARK = "iqa_benchmark"  # Quality assessment benchmarks
    DOCUMENT_LAYOUT = "document_layout"  # Layout detection datasets
    HANDWRITING = "handwriting"  # Handwriting recognition
    SCENE_TEXT = "scene_text"  # Text in natural scenes
    DEGRADED_DOCS = "degraded_docs"  # Artificially/naturally degraded
    SPECIALIZED = "specialized"  # Domain-specific (tables, forms, etc.)
    CAMERA_CAPTURED = "camera_captured"  # Smartphone/camera captures
    SYNTHETIC = "synthetic"  # Synthetically generated
    UNKNOWN = "unknown"


class LicenseType(str, Enum):
    """Dataset license classification."""

    CC_BY = "cc-by"  # Creative Commons Attribution
    CC_BY_NC = "cc-by-nc"  # CC Non-Commercial
    CC_BY_SA = "cc-by-sa"  # CC ShareAlike
    CC_BY_NC_SA = "cc-by-nc-sa"  # CC Non-Commercial ShareAlike
    CC0 = "cc0"  # Public Domain
    MIT = "mit"  # MIT License
    APACHE = "apache"  # Apache 2.0
    RESEARCH_ONLY = "research_only"  # Academic/research use only
    CUSTOM = "custom"  # Custom license
    UNKNOWN = "unknown"  # License not documented


# Dataset registry with metadata - SHORT CODES aligned with DATASET_CATALOG.md
# Each entry contains: full_name, category, size, license, and other metadata
DATASET_REGISTRY: dict[str, dict] = {
    # === Tables ===
    "tablebank": {
        "full_name": "TableBank",
        "category": DatasetCategory.SPECIALIZED,
        "size": 278582,
        "license": LicenseType.APACHE,
        "annotation_format": "coco",
        "content_type": "tables",
        "url": "https://github.com/doc-analysis/TableBank",
    },
    "pubtabnet": {
        "full_name": "PubTabNet",
        "category": DatasetCategory.SPECIALIZED,
        "size": 568000,
        "license": LicenseType.CUSTOM,  # CDLA-Sharing
        "annotation_format": "jsonl",
        "content_type": "tables",
    },
    "fintabnet": {
        "full_name": "FinTabNet",
        "category": DatasetCategory.SPECIALIZED,
        "size": 97475,
        "license": LicenseType.RESEARCH_ONLY,
        "content_type": "tables",
    },
    # === Document Layout ===
    "doclaynet": {
        "full_name": "DocLayNet",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 80863,
        "license": LicenseType.CUSTOM,  # CDLA-Permissive
        "annotation_format": "coco",
        "classes": 11,
        "url": "https://github.com/DS4SD/DocLayNet",
    },
    "publaynet": {
        "full_name": "PubLayNet",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 360000,
        "license": LicenseType.CC_BY,
        "annotation_format": "coco",
        "classes": 5,
    },
    "rvl-cdip": {
        "full_name": "RVL-CDIP",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 400000,
        "license": LicenseType.RESEARCH_ONLY,
        "classes": 16,
        "url": "https://adamharley.com/rvl-cdip/",
    },
    "bhutan-afs": {
        "full_name": "Bhutan Government Financial Statements",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 125,
        "license": LicenseType.CC0,  # Public domain
        "content_type": "financial",
    },
    # === Forms ===
    "nist-sd2": {
        "full_name": "NIST Special Database 2 (Tax Forms)",
        "category": DatasetCategory.SPECIALIZED,
        "size": 5590,
        "license": LicenseType.CC0,  # Public domain
        "content_type": "forms",
    },
    "nist-sd6": {
        "full_name": "NIST Special Database 6 (Census Forms)",
        "category": DatasetCategory.SPECIALIZED,
        "size": 5595,
        "license": LicenseType.CC0,
        "content_type": "forms",
    },
    "funsd": {
        "full_name": "Form Understanding in Noisy Scanned Documents",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 199,
        "license": LicenseType.CC_BY,
        "annotation_format": "custom_json",
        "has_forms": True,
    },
    "funsd-plus": {
        "full_name": "FUNSD+ Extended",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 1500,
        "license": LicenseType.CC_BY,
        "has_forms": True,
    },
    "sroie": {
        "full_name": "SROIE Receipts",
        "category": DatasetCategory.SPECIALIZED,
        "size": 973,
        "license": LicenseType.RESEARCH_ONLY,
        "content_type": "receipts",
    },
    # === Handwriting ===
    "nist-sd19": {
        "full_name": "NIST Special Database 19 (Handwriting)",
        "category": DatasetCategory.HANDWRITING,
        "size": 810000,
        "license": LicenseType.CC0,
        "scopes": ["character", "word", "page"],
    },
    "hasyv2": {
        "full_name": "HASYv2 (Math Handwriting)",
        "category": DatasetCategory.HANDWRITING,
        "size": 168233,
        "license": LicenseType.CC0,
        "content_type": "symbols",
    },
    "signatr6k": {
        "full_name": "SignaTR6K",
        "category": DatasetCategory.HANDWRITING,
        "size": 12514,
        "license": LicenseType.RESEARCH_ONLY,
        "content_type": "signatures",
    },
    "iam": {
        "full_name": "IAM Handwriting Database",
        "category": DatasetCategory.HANDWRITING,
        "size": 13000,
        "license": LicenseType.RESEARCH_ONLY,
        "scopes": ["word", "line", "sentence"],
    },
    # === Formulas ===
    "im2latex": {
        "full_name": "im2latex-100k",
        "category": DatasetCategory.SPECIALIZED,
        "size": 100000,
        "license": LicenseType.CC0,
        "content_type": "formulas",
        "url": "https://zenodo.org/records/56198",
    },
    "mathverse": {
        "full_name": "MathVerse",
        "category": DatasetCategory.SPECIALIZED,
        "size": 3940,
        "license": LicenseType.MIT,
        "content_type": "formulas",
    },
    # === Degraded Documents ===
    "tobacco800": {
        "full_name": "Tobacco-800",
        "category": DatasetCategory.DEGRADED_DOCS,
        "size": 1290,
        "license": LicenseType.RESEARCH_ONLY,
    },
    "dibco-train": {
        "full_name": "DIBCO Training Subset",
        "category": DatasetCategory.DEGRADED_DOCS,
        "size": 500,
        "license": LicenseType.RESEARCH_ONLY,
        "has_ground_truth": True,
    },
    "historical-degraded": {
        "full_name": "Historical Degraded Documents",
        "category": DatasetCategory.DEGRADED_DOCS,
        "size": 1356,
        "license": LicenseType.UNKNOWN,
        "content_type": "historical",
    },
    # === Camera Captured ===
    "realdae": {
        "full_name": "RealDAE",
        "category": DatasetCategory.CAMERA_CAPTURED,
        "size": 600,
        "license": LicenseType.RESEARCH_ONLY,
        "has_pairs": True,
    },
    # === Language & Script Detection ===
    "jssoda": {
        "full_name": "JSSODa (Japanese Synthetic OCR)",
        "category": DatasetCategory.SYNTHETIC,
        "size": 2000,
        "license": LicenseType.CC_BY,
        "scripts": ["Japanese"],
    },
    "arabic-ocr": {
        "full_name": "Arabic OCR Dataset",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 500,
        "license": LicenseType.UNKNOWN,
        "scripts": ["Arabic"],
    },
    "dzongkha-digits": {
        "full_name": "Dzongkha Handwritten Digits",
        "category": DatasetCategory.HANDWRITING,
        "size": 1000,
        "license": LicenseType.CC0,
        "scripts": ["Tibetan"],
    },
    "mdiw13": {
        "full_name": "MDIW-13 (Multi-Script Document)",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 86655,
        "license": LicenseType.RESEARCH_ONLY,
        "scripts": 13,
    },
    "midv500": {
        "full_name": "MIDV-500 (ID Documents)",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 50,  # 50 countries
        "license": LicenseType.MIT,
        "scripts": ["Latin", "Cyrillic"],
    },
    "tibhcr": {
        "full_name": "TibHCR (Tibetan Handwriting)",
        "category": DatasetCategory.HANDWRITING,
        "size": 141698,
        "license": LicenseType.RESEARCH_ONLY,
        "scripts": ["Tibetan"],
    },
    "cc-ocr": {
        "full_name": "CC-OCR (CJK Benchmark)",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 7058,
        "license": LicenseType.MIT,
        "scripts": ["CJK"],
    },
    "nepal-devanagari": {
        "full_name": "Nepal Devanagari Documents",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 717,
        "license": LicenseType.CC0,
        "scripts": ["Devanagari"],
    },
    "mlt19": {
        "full_name": "MLT-19 (ICDAR Multilingual)",
        "category": DatasetCategory.SCENE_TEXT,
        "size": 20000,  # Approximate
        "license": LicenseType.MIT,
        "scripts": 10,
    },
    "pucit-ohul": {
        "full_name": "PUCIT-OHUL Urdu Handwriting",
        "category": DatasetCategory.HANDWRITING,
        "size": 6714,
        "license": LicenseType.RESEARCH_ONLY,
        "scripts": ["Arabic"],  # Urdu uses Arabic script
        "content_type": "handwriting",
        "url": "https://paperswithcode.com/dataset/pucit-ohul",
    },
    "multilingual-scripts": {
        "full_name": "Multilingual Script Samples",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 3279,
        "license": LicenseType.UNKNOWN,
        "scripts": ["mixed"],
        "content_type": "script_detection",
    },
    # === IQA Reference ===
    "ocr-quality": {
        "full_name": "OCR-Quality Dataset",
        "category": DatasetCategory.IQA_BENCHMARK,
        "size": 1000,
        "license": LicenseType.UNKNOWN,
        "has_mos": True,
    },
    # === Benchmark-Only (Evaluation) ===
    "diqa-5000": {
        "full_name": "DIQA-5000",
        "category": DatasetCategory.IQA_BENCHMARK,
        "size": 5500,
        "license": LicenseType.RESEARCH_ONLY,
        "has_mos": True,
        "benchmark_only": True,
    },
    "dibco-eval": {
        "full_name": "DIBCO Evaluation Set",
        "category": DatasetCategory.DEGRADED_DOCS,
        "size": 131,
        "license": LicenseType.RESEARCH_ONLY,
        "has_ground_truth": True,
        "benchmark_only": True,
    },
    "smartdoc-qa": {
        "full_name": "SmartDoc-QA",
        "category": DatasetCategory.CAMERA_CAPTURED,
        "size": 4270,
        "license": LicenseType.RESEARCH_ONLY,
        "has_mos": True,
        "benchmark_only": True,
    },
    "ohr-bench": {
        "full_name": "OHR-Bench",
        "category": DatasetCategory.IQA_BENCHMARK,
        "size": 8561,
        "license": LicenseType.RESEARCH_ONLY,
        "benchmark_only": True,
    },
    "omnidocbench": {
        "full_name": "OmniDocBench",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 20000,
        "license": LicenseType.RESEARCH_ONLY,
        "format": "arrow",
        "benchmark_only": True,
    },
    # === Educational ===
    "multimodal-textbook": {
        "full_name": "Multimodal Textbook",
        "category": DatasetCategory.DOCUMENT_LAYOUT,
        "size": 1113,
        "license": LicenseType.APACHE,
        "content_type": "educational",
    },
}


class SourceInfo(TypedDict):
    """Source dataset information for provenance tracking."""

    dataset_name: str  # Short name (e.g., "doclaynet")
    dataset_version: str  # Version string (e.g., "1.0", "2023-01")
    original_path: str  # Path within dataset (e.g., "train/images/doc_001.png")
    original_filename: str  # Original filename
    download_date: str | None  # ISO date when dataset was obtained
    dataset_url: str | None  # Source URL for dataset


class FileIntegrity(TypedDict):
    """File integrity verification data."""

    file_hash: str  # SHA-256 hash of file contents
    hash_algorithm: str  # Algorithm used (always "sha256")
    file_size_bytes: int  # File size for quick validation


class SampleSourceInfo(TypedDict):
    """Complete source tracking for a sample."""

    sample_id: str  # UUID for cross-layer linking
    source: SourceInfo  # Dataset source information
    integrity: FileIntegrity  # File hash and size
    category: str  # DatasetCategory enum value
    license: str  # LicenseType enum value
    created_at: str  # ISO timestamp when sample was indexed


@dataclass(frozen=True)
class DatasetInfo:
    """Dataset information with full metadata."""

    name: str
    full_name: str
    category: DatasetCategory
    size: int
    license: LicenseType
    url: str | None = None
    annotation_format: str | None = None
    has_mos: bool = False
    has_ground_truth: bool = False


def get_dataset_info(dataset_name: str) -> DatasetInfo | None:
    """Get dataset metadata from registry.

    Args:
        dataset_name: Short dataset name (e.g., "doclaynet")

    Returns:
        DatasetInfo if found, None otherwise
    """
    if dataset_name not in DATASET_REGISTRY:
        return None

    reg = DATASET_REGISTRY[dataset_name]
    return DatasetInfo(
        name=dataset_name,
        full_name=reg.get("full_name", dataset_name),
        category=reg.get("category", DatasetCategory.UNKNOWN),
        size=reg.get("size", 0),
        license=reg.get("license", LicenseType.UNKNOWN),
        url=reg.get("url"),
        annotation_format=reg.get("annotation_format"),
        has_mos=reg.get("has_mos", False),
        has_ground_truth=reg.get("has_ground_truth", False),
    )


def create_source_info(
    dataset_name: str,
    dataset_version: str,
    original_path: str,
    original_filename: str,
    download_date: str | None = None,
) -> SourceInfo:
    """Create a SourceInfo dict for a sample.

    Args:
        dataset_name: Short dataset name
        dataset_version: Version of the dataset
        original_path: Path within the dataset
        original_filename: Original filename
        download_date: When the dataset was obtained

    Returns:
        SourceInfo TypedDict
    """
    dataset_url = None
    if dataset_name in DATASET_REGISTRY:
        dataset_url = DATASET_REGISTRY[dataset_name].get("url")

    return SourceInfo(
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        original_path=original_path,
        original_filename=original_filename,
        download_date=download_date,
        dataset_url=dataset_url,
    )


def create_file_integrity(
    file_hash: str,
    file_size_bytes: int,
    hash_algorithm: str = "sha256",
) -> FileIntegrity:
    """Create a FileIntegrity dict.

    Args:
        file_hash: SHA-256 hash of file contents
        file_size_bytes: File size in bytes
        hash_algorithm: Hash algorithm used (default: sha256)

    Returns:
        FileIntegrity TypedDict
    """
    return FileIntegrity(
        file_hash=file_hash,
        hash_algorithm=hash_algorithm,
        file_size_bytes=file_size_bytes,
    )


def validate_sample_id(sample_id: str) -> bool:
    """Validate that a sample_id is a valid UUID.

    Args:
        sample_id: Sample identifier to validate

    Returns:
        True if valid UUID format
    """
    import re

    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    return bool(uuid_pattern.match(sample_id))


def get_datasets_by_category(category: DatasetCategory) -> list[str]:
    """Get all dataset names in a category.

    Args:
        category: DatasetCategory to filter by

    Returns:
        List of dataset names
    """
    return [
        name
        for name, info in DATASET_REGISTRY.items()
        if info.get("category") == category
    ]


def get_datasets_with_mos() -> list[str]:
    """Get datasets that have Mean Opinion Score annotations.

    Returns:
        List of dataset names with MOS annotations
    """
    return [
        name for name, info in DATASET_REGISTRY.items() if info.get("has_mos", False)
    ]


def get_datasets_by_license(license_type: LicenseType) -> list[str]:
    """Get datasets with a specific license type.

    Args:
        license_type: License to filter by

    Returns:
        List of dataset names
    """
    return [
        name
        for name, info in DATASET_REGISTRY.items()
        if info.get("license") == license_type
    ]
