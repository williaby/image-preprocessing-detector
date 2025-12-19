#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""
Annotate base dataset images with versioned metadata schema.

Implements the three-layer metadata architecture from metadata-versioning-schema.md:
1. IMMUTABLE LAYER: Original labels preserved exactly as provided by source datasets
2. ENRICHMENT LAYER: Our derived annotations with full provenance (versioned)
3. TRAINING LAYER: Computed on-demand from original + enrichments

Usage:
    # Scan all datasets and create initial metadata
    python scripts/annotate_base_metadata.py --scan

    # Add enrichment version (classical CV detectors)
    python scripts/annotate_base_metadata.py --enrich classical_cv

    # Generate statistics report
    python scripts/annotate_base_metadata.py --stats

    # Export training-ready parquet
    python scripts/annotate_base_metadata.py --export train

Updated 2025-12-17: Initial implementation for Phase 7 taxonomy solidification.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image
from tqdm import tqdm

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


# Dataset configurations with known metadata mappings
DATASET_CONFIGS: dict[str, dict[str, Any]] = {
    # === Benchmark datasets (human MOS labels) ===
    "diqa-5000": {
        "path": BENCHMARK_ONLY / "diqa-5000",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.UNKNOWN,  # Mixed sources
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "mos_file": "mos_labels.json",  # Expected label file
        "original_labels_parser": "parse_diqa_labels",
    },
    "live": {
        "path": BENCHMARK_ONLY / "live",
        "pattern": "**/*.*",
        "capture_method": CaptureMethod.CAMERA_PROFESSIONAL,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "original_labels_parser": "parse_live_labels",
    },
    "csiq": {
        "path": BENCHMARK_ONLY / "csiq",
        "pattern": "**/*.*",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "original_labels_parser": "parse_csiq_labels",
    },
    "smartdoc-qa": {
        "path": BENCHMARK_ONLY / "smartdoc_qa",
        "pattern": "**/*.*",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "original_labels_parser": "parse_smartdoc_labels",
    },
    "dibco": {
        "path": BENCHMARK_ONLY / "dibco",
        "pattern": "**/*.*",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "original_labels_parser": "parse_dibco_labels",
    },
    # === Base training datasets ===
    # Phase 9 content flags: has_table, has_formula, has_handwriting, has_signature
    "tobacco800": {
        "path": BASE_DATA / "degraded/tobacco800",
        "pattern": "images/*.png",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        # Phase 9 content flags
        "has_table": False,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
    },
    "historical_degraded": {
        "path": BASE_DATA / "degraded/historical_degraded",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        # Phase 9 content flags
        "has_table": False,
        "has_formula": False,
        "has_handwriting": True,  # Historical docs often have handwriting
        "has_signature": False,
    },
    "rvl_cdip": {
        "path": BASE_DATA / "documents/rvl_cdip",
        "pattern": "images/*.jpg",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        # Phase 9 content flags - mixed content
        "has_table": True,  # Some docs have tables
        "has_formula": False,
        "has_handwriting": True,  # Some docs have handwritten annotations
        "has_signature": True,  # Some docs have signatures
    },
    "doclaynet": {
        "path": BASE_DATA / "documents/doclaynet",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": False,
        "original_labels_parser": "parse_doclaynet_labels",
        # Phase 9 content flags - has layout annotations
        "has_table": True,
        "has_formula": True,
        "has_handwriting": False,
        "has_signature": False,
    },
    "nist_db2": {
        "path": BASE_DATA / "forms/nist_db2",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        # Phase 9 content flags - check images
        "has_table": True,  # Form-like structure
        "has_formula": False,
        "has_handwriting": True,  # Filled-in checks
        "has_signature": True,  # Checks have signatures
    },
    "nist_sd6": {
        "path": BASE_DATA / "forms/nist_sd6",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.TAX,
        "has_human_mos": False,
        # Phase 9 content flags - tax forms
        "has_table": True,  # Form-like structure
        "has_formula": False,
        "has_handwriting": False,  # Synthesized forms
        "has_signature": False,
    },
    "funsd": {
        "path": BASE_DATA / "forms/funsd",
        "pattern": "images/*.jpg",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        "original_labels_parser": "parse_funsd_labels",
        # Phase 9 content flags - scanned forms
        "has_table": True,  # Form-like structure
        "has_formula": False,
        "has_handwriting": True,  # Filled-in forms
        "has_signature": True,  # Some forms have signatures
    },
    "funsd_plus": {
        "path": BASE_DATA / "forms/funsd_plus",
        "pattern": "images/*.jpg",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        # Phase 9 content flags - scanned forms
        "has_table": True,
        "has_formula": False,
        "has_handwriting": True,
        "has_signature": True,
    },
    "sroie": {
        "path": BASE_DATA / "forms/sroie",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        # Phase 9 content flags - receipts
        "has_table": True,  # Receipt line items
        "has_formula": False,
        "has_handwriting": False,  # Printed receipts
        "has_signature": False,
    },
    "tablebank": {
        "path": BASE_DATA / "tables/tablebank",
        "pattern": "**/images/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.SCIENTIFIC,
        "has_human_mos": False,
        "original_labels_parser": "parse_tablebank_labels",
        # Phase 9 content flags - 100% tables
        "has_table": True,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
    },
    "pubtabnet": {
        "path": BASE_DATA / "tables/pubtabnet",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.SCIENTIFIC,
        "has_human_mos": False,
        # Phase 9 content flags - 100% tables
        "has_table": True,
        "has_formula": False,
        "has_handwriting": False,
        "has_signature": False,
    },
    "nist_sd19": {
        "path": BASE_DATA / "handwriting/nist_sd19_pages",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.PERSONAL,
        "has_human_mos": False,
        # Phase 9 content flags - 100% handwriting
        "has_table": False,
        "has_formula": False,
        "has_handwriting": True,
        "has_signature": False,
    },
    "signatr6k": {
        "path": BASE_DATA / "handwriting/signatr6k",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.PERSONAL,
        "has_human_mos": False,
        "original_labels_parser": "parse_signatr_labels",
        # Phase 9 content flags - 100% signatures
        "has_table": False,
        "has_formula": False,
        "has_handwriting": True,
        "has_signature": True,  # This IS the signature dataset
    },
    "maths_handwriting": {
        "path": BASE_DATA / "handwriting/maths_handwriting",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        # Phase 9 content flags - handwritten math
        "has_table": False,
        "has_formula": True,  # Math formulas
        "has_handwriting": True,  # Handwritten
        "has_signature": False,
    },
    "im2latex": {
        "path": BASE_DATA / "formulas/im2latex",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.SCIENTIFIC,
        "has_human_mos": False,
        # Phase 9 content flags - 100% formulas
        "has_table": False,
        "has_formula": True,
        "has_handwriting": False,
        "has_signature": False,
    },
    "mathverse": {
        "path": BASE_DATA / "formulas/mathverse",
        "pattern": "images/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        # Phase 9 content flags - math diagrams
        "has_table": False,
        "has_formula": True,  # 100% math formulas
        "has_handwriting": False,
        "has_signature": False,
    },
    "multimodal_textbook": {
        "path": BASE_DATA / "educational/multimodal_textbook",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.BORN_DIGITAL,
        "domain": DomainLevel1.EDUCATIONAL,
        "has_human_mos": False,
        # Phase 9 content flags - mixed educational content
        "has_table": True,  # Textbooks often have tables
        "has_formula": True,  # Math/science textbooks
        "has_handwriting": False,
        "has_signature": False,
    },
}


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
    """Immutable labels from source dataset (preserved exactly)."""

    # Dataset-specific scores (only populated if from that dataset)
    diqa_mos: float | None = None
    diqa_mos_std: float | None = None
    diqa_distortion_type: str | None = None

    live_dmos: float | None = None
    live_dmos_std: float | None = None
    live_ref_image: str | None = None

    csiq_dmos: float | None = None

    smartdoc_mos: float | None = None
    smartdoc_capture_device: str | None = None
    smartdoc_lighting: str | None = None

    doclaynet_annotations: list[dict] | None = None
    tablebank_annotations: list[dict] | None = None
    funsd_annotations: list[dict] | None = None
    signatr_writer_id: str | None = None
    signatr_is_genuine: bool | None = None

    # Generic fallback
    raw_labels: dict | None = None


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

    # Language detection
    primary_language: str | None = None
    language_confidence: float | None = None
    script_type: str | None = None

    # LLM perceptual scores (added in later versions)
    llm_predicted_mos: float | None = None
    llm_predicted_normalized: float | None = None
    llm_prediction_confidence: float | None = None
    llm_model_name: str | None = None

    # Phase 9 content flags (dataset-level indicators for element classifiers)
    has_table: bool | None = None
    has_formula: bool | None = None
    has_handwriting: bool | None = None
    has_signature: bool | None = None


@dataclass
class EnrichmentVersion:
    """Single version of enrichment with provenance."""

    version: int
    created_at: str
    created_by: str
    method: str  # "automated", "manual", "llm"
    description: str
    data: EnrichmentData = field(default_factory=EnrichmentData)


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

    # Enrichment history (versioned)
    current_version: int = 0
    enrichment_versions: list[EnrichmentVersion] = field(default_factory=list)

    # Record metadata
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    schema_version: str = "1.0"

    def add_enrichment(
        self,
        data: EnrichmentData,
        created_by: str,
        method: str,
        description: str,
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
                        "data": {k: val for k, val in v.data.__dict__.items() if val is not None},
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
            channels_map = {"1": 1, "L": 1, "P": 1, "RGB": 3, "RGBA": 4, "CMYK": 4, "LAB": 3}
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
# Label Parsers (Per-Dataset Original Label Extraction)
# =============================================================================


def parse_diqa_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse DIQA-5000 labels (MOS scores)."""
    labels = OriginalLabels()

    # Look for MOS labels file
    mos_file = dataset_path / "mos_labels.json"
    if mos_file.exists():
        try:
            with open(mos_file) as f:
                mos_data = json.load(f)
            filename = image_path.name
            if filename in mos_data:
                entry = mos_data[filename]
                labels.diqa_mos = entry.get("mos")
                labels.diqa_mos_std = entry.get("mos_std")
                labels.diqa_distortion_type = entry.get("distortion_type")
        except Exception as e:
            logger.debug(f"Failed to parse DIQA labels: {e}")

    return labels


def parse_live_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse LIVE IQA labels (DMOS scores)."""
    labels = OriginalLabels()

    # LIVE uses mat files or CSV - placeholder for actual parsing
    dmos_file = dataset_path / "dmos.csv"
    if dmos_file.exists():
        # Would need pandas or csv parsing
        pass

    return labels


def parse_csiq_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse CSIQ labels (DMOS scores)."""
    return OriginalLabels()  # Placeholder


def parse_smartdoc_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse SmartDoc-QA labels."""
    return OriginalLabels()  # Placeholder


def parse_dibco_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse DIBCO labels (binary ground truth)."""
    return OriginalLabels()  # Placeholder


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
        logger.debug(f"Loaded COCO annotations from {coco_path}: {len(filename_to_id)} images")
        return result
    except Exception as e:
        logger.warning(f"Failed to load COCO annotations from {coco_path}: {e}")
        return None


def parse_doclaynet_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse DocLayNet COCO annotations.

    DocLayNet categories (11 classes):
    - Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header,
    - Picture, Section-Header, Table, Text, Title
    """
    labels = OriginalLabels()

    # Look for COCO annotations in various locations
    coco_paths = [
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
        return labels

    # Get annotations for this image
    filename = image_path.name
    annotations = coco_data["annotations"].get(filename, [])

    if annotations:
        labels.doclaynet_annotations = annotations

    return labels


def parse_tablebank_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse TableBank COCO-format table annotations.

    TableBank provides bounding boxes for tables in documents.
    """
    labels = OriginalLabels()

    # TableBank structure: Detection/images/ and Detection/annotations/
    coco_paths = [
        dataset_path / "TableBank" / "Detection" / "annotations" / "tablebank_latex_train.json",
        dataset_path / "TableBank" / "Detection" / "annotations" / "tablebank_word_train.json",
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
    """Parse FUNSD form annotations."""
    labels = OriginalLabels()

    # FUNSD annotations are in JSON files alongside images
    json_path = image_path.with_suffix(".json")
    if json_path.exists():
        try:
            with open(json_path) as f:
                labels.funsd_annotations = json.load(f)
        except Exception as e:
            logger.debug(f"Failed to parse FUNSD annotations: {e}")

    return labels


def parse_signatr_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse SignaTR6K signature labels."""
    labels = OriginalLabels()

    # Extract writer ID from path structure (typically includes writer info)
    parts = image_path.parts
    for i, part in enumerate(parts):
        if part.startswith("writer"):
            labels.signatr_writer_id = part
            break

    return labels


# Registry of label parsers
LABEL_PARSERS = {
    "parse_diqa_labels": parse_diqa_labels,
    "parse_live_labels": parse_live_labels,
    "parse_csiq_labels": parse_csiq_labels,
    "parse_smartdoc_labels": parse_smartdoc_labels,
    "parse_dibco_labels": parse_dibco_labels,
    "parse_doclaynet_labels": parse_doclaynet_labels,
    "parse_tablebank_labels": parse_tablebank_labels,
    "parse_funsd_labels": parse_funsd_labels,
    "parse_signatr_labels": parse_signatr_labels,
}


# =============================================================================
# Main Processing Functions
# =============================================================================


def scan_dataset(dataset_name: str, config: dict[str, Any], limit: int | None = None) -> list[SampleMetadata]:
    """Scan a dataset and create initial metadata records."""
    samples: list[SampleMetadata] = []

    dataset_path = config["path"]
    pattern = config["pattern"]

    if not dataset_path.exists():
        logger.warning(f"Dataset path not found: {dataset_path}")
        return samples

    # Find all images
    image_files = sorted(dataset_path.glob(pattern))
    if limit:
        image_files = image_files[:limit]

    logger.info(f"Scanning {dataset_name}: {len(image_files)} files")

    # Get label parser if specified
    parser_name = config.get("original_labels_parser")
    label_parser = LABEL_PARSERS.get(parser_name) if parser_name else None

    for image_path in tqdm(image_files, desc=f"  {dataset_name}", leave=False):
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

        # Create initial enrichment with known capture method and domain
        initial_enrichment = EnrichmentData(
            capture_method=config["capture_method"].value,
            capture_confidence=0.95 if config["capture_method"] != CaptureMethod.UNKNOWN else 0.5,
            capture_detection_method="dataset_config",
            resolution_dpi=file_metadata.dpi,
            resolution_category=categorize_dpi(file_metadata.dpi).value,
            resolution_pixels=(file_metadata.width_px, file_metadata.height_px),
            domain_level1=config["domain"].value,
            domain_confidence=0.9 if config["domain"] != DomainLevel1.UNKNOWN else 0.3,
            # Phase 9 content flags (from dataset config)
            has_table=config.get("has_table"),
            has_formula=config.get("has_formula"),
            has_handwriting=config.get("has_handwriting"),
            has_signature=config.get("has_signature"),
        )

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

        # Add initial enrichment
        sample.add_enrichment(
            data=initial_enrichment,
            created_by="annotate_base_metadata.py_v1.0",
            method="automated",
            description="Initial scan with dataset config defaults",
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
            "live_dmos": sample.original_labels.live_dmos,
            "csiq_dmos": sample.original_labels.csiq_dmos,
            "smartdoc_mos": sample.original_labels.smartdoc_mos,
            # Enrichment data
            "enrichment_version": sample.current_version,
            "capture_method": enrichment.capture_method if enrichment else None,
            "capture_confidence": enrichment.capture_confidence if enrichment else None,
            "domain_level1": enrichment.domain_level1 if enrichment else None,
            "resolution_category": enrichment.resolution_category if enrichment else None,
            # LLM scores (if available)
            "llm_predicted_mos": enrichment.llm_predicted_mos if enrichment else None,
            "llm_model_name": enrichment.llm_model_name if enrichment else None,
            # Phase 9 content flags
            "has_table": enrichment.has_table if enrichment else None,
            "has_formula": enrichment.has_formula if enrichment else None,
            "has_handwriting": enrichment.has_handwriting if enrichment else None,
            "has_signature": enrichment.has_signature if enrichment else None,
            # Element annotations (JSON-serialized for bbox preservation)
            # These enable Phase 9 element classifier training
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
            # Derived element counts (for quick filtering)
            "table_count": (
                len([a for a in (sample.original_labels.doclaynet_annotations or [])
                     if a.get("category_name") == "Table"])
                + len(sample.original_labels.tablebank_annotations or [])
            ),
            "formula_count": (
                len([a for a in (sample.original_labels.doclaynet_annotations or [])
                     if a.get("category_name") == "Formula"])
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

        data = {
            "dataset_name": dataset_name,
            "sample_count": len(dataset_samples),
            "created_at": datetime.now(UTC).isoformat(),
            "schema_version": "1.0",
            "samples": [s.to_dict() for s in dataset_samples],
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(dataset_samples)} samples to {output_file}")


def generate_statistics(samples: list[SampleMetadata]) -> dict[str, Any]:
    """Generate statistics about the metadata collection."""
    stats: dict[str, Any] = {
        "total_samples": len(samples),
        "by_dataset": {},
        "by_capture_method": {},
        "by_domain": {},
        "by_resolution_category": {},
        "with_human_mos": 0,
        "with_llm_scores": 0,
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

            # LLM scores
            if enrichment.llm_predicted_mos is not None:
                stats["with_llm_scores"] += 1

        # Human MOS
        labels = sample.original_labels
        if any([labels.diqa_mos, labels.live_dmos, labels.csiq_dmos, labels.smartdoc_mos]):
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
    # Scan specific dataset
    python scripts/annotate_base_metadata.py --scan --dataset diqa-5000

    # Scan all datasets (with limit per dataset)
    python scripts/annotate_base_metadata.py --scan --limit 1000

    # Generate statistics
    python scripts/annotate_base_metadata.py --stats

    # Export to parquet
    python scripts/annotate_base_metadata.py --export
        """,
    )

    parser.add_argument("--scan", action="store_true", help="Scan datasets and create metadata")
    parser.add_argument("--dataset", type=str, help="Specific dataset to process")
    parser.add_argument("--limit", type=int, help="Limit samples per dataset")
    parser.add_argument("--stats", action="store_true", help="Generate statistics report")
    parser.add_argument("--export", action="store_true", help="Export to Parquet")
    parser.add_argument("--output", type=Path, default=METADATA_ROOT, help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    args = parser.parse_args()

    if not any([args.scan, args.stats, args.export]):
        parser.print_help()
        return

    # Ensure output directory exists
    args.output.mkdir(parents=True, exist_ok=True)

    all_samples: list[SampleMetadata] = []

    if args.scan:
        logger.info("=" * 70)
        logger.info("BASE DATASET METADATA ANNOTATION")
        logger.info("=" * 70)

        datasets_to_scan = (
            {args.dataset: DATASET_CONFIGS[args.dataset]}
            if args.dataset and args.dataset in DATASET_CONFIGS
            else DATASET_CONFIGS
        )

        if args.dry_run:
            logger.info("DRY RUN - would scan:")
            for name, config in datasets_to_scan.items():
                logger.info(f"  {name}: {config['path']}")
            return

        for dataset_name, config in datasets_to_scan.items():
            samples = scan_dataset(dataset_name, config, limit=args.limit)
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
                "with_human_mos": df["diqa_mos"].notna().sum(),
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

        logger.info("\nBy Capture Method:")
        for cm, count in sorted(stats.get("by_capture_method", {}).items(), key=lambda x: -x[1]):
            logger.info(f"  {cm}: {count:,}")

        logger.info("\nBy Domain:")
        for domain, count in sorted(stats.get("by_domain", {}).items(), key=lambda x: -x[1]):
            logger.info(f"  {domain}: {count:,}")

        logger.info(f"\nWith Human MOS: {stats.get('with_human_mos', 0):,}")

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
