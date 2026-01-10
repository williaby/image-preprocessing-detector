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
SCHEMA_VERSION = "2.0"
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
    "tablebank": {"has_table": True},
    "pubtabnet": {"has_table": True},
    "fintabnet": {"has_table": True},
    "im2latex": {"has_formula": True},
    "mathverse": {"has_formula": True},
    "maths_handwriting": {"has_formula": True, "has_handwriting": True},
    "signatr6k": {"has_signature": True, "has_handwriting": True},
    "nist_sd19": {"has_handwriting": True},
}

# Datasets with COCO annotations (Tier 1)
TIER_1_DATASETS = {"doclaynet", "tablebank", "funsd"}

# Dataset configurations with known metadata mappings
DATASET_CONFIGS: dict[str, dict[str, Any]] = {
    # === Benchmark datasets ===
    "diqa-5000": {
        "path": BENCHMARK_ONLY / "diqa-5000",
        "pattern": "**/ori/*.jpg",  # Fixed: images are in train/ori/, val/ori/, test/ori/
        "capture_method": CaptureMethod.UNKNOWN,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "mos_file": "train/train.csv",  # CSV with MOS scores
        "original_labels_parser": "parse_diqa_labels",
    },
    "smartdoc-qa": {
        "path": BENCHMARK_ONLY / "smartdoc-qa",  # Fixed: hyphen not underscore
        "pattern": "Dataset SmartDoc-QA/Captured_Images/**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.UNKNOWN,
        "has_human_mos": True,
        "original_labels_parser": "parse_smartdoc_labels",
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
    },
    # === Base training datasets ===
    "tobacco800": {
        "path": BASE_DATA / "degraded/tobacco800",
        "pattern": "images/*.png",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
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
    "nist_db2": {
        "path": BASE_DATA / "forms/nist_db2",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        "has_table": True,
        "has_handwriting": True,
        "has_signature": True,
    },
    "nist_sd6": {
        "path": BASE_DATA / "forms/nist_sd6",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.TAX,
        "has_human_mos": False,
        "has_table": True,
    },
    "funsd": {
        "path": BASE_DATA / "forms/funsd",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_ADF,
        "domain": DomainLevel1.ADMINISTRATIVE,
        "has_human_mos": False,
        "original_labels_parser": "parse_funsd_labels",
        "has_table": True,
        "has_handwriting": True,
        "has_signature": True,
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
    },
    "sroie": {
        "path": BASE_DATA / "forms/sroie",
        "pattern": "**/*.jpg",
        "capture_method": CaptureMethod.CAMERA_SMARTPHONE,
        "domain": DomainLevel1.FINANCIAL,
        "has_human_mos": False,
        "has_table": True,
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
    },
    "nist_sd19": {
        "path": BASE_DATA / "handwriting/nist_sd19_pages",
        "pattern": "**/*.png",
        "capture_method": CaptureMethod.SCANNER_FLATBED,
        "domain": DomainLevel1.PERSONAL,
        "has_human_mos": False,
        # Tier 0: 100% handwriting by definition
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
        # Tier 0: 100% signatures by definition
        "has_table": False,
        "has_formula": False,
        "has_handwriting": True,
        "has_signature": True,
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
        # Mixed content, needs YOLO detection
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
    """Immutable labels from source dataset (preserved exactly)."""

    # Dataset-specific scores (only populated if from that dataset)
    diqa_mos: float | None = None
    diqa_mos_std: float | None = None
    diqa_distortion_type: str | None = None

    # OCR-Quality human scores (1-4 scale, 1=best)
    ocr_quality_score: int | None = None
    ocr_quality_source: str | None = None
    ocr_quality_text: str | None = None

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

    # Language detection
    primary_language: str | None = None
    language_confidence: float | None = None
    script_type: str | None = None

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


@dataclass
class EnrichmentVersion:
    """Single version of enrichment with provenance and reproducibility."""

    version: int
    created_at: str
    created_by: str
    method: str  # "tier_0_exact", "tier_1_annotation", "tier_2_model", "tier_3_heuristic"
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
# DocLayout-YOLO Integration
# =============================================================================

# Global model cache
_YOLO_MODEL = None


def load_doclayout_yolo():
    """Load DocLayout-YOLO model (lazy loading, cached)."""
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    try:
        from ultralytics import YOLO

        # Try multiple model paths
        model_paths = [
            PROJECT_ROOT / "models" / "doclayout_yolo_docstructbench.pt",
            PROJECT_ROOT / "05_models" / "doclayout_yolo.pt",
            Path.home() / ".cache" / "doclayout_yolo.pt",
        ]

        for model_path in model_paths:
            if model_path.exists():
                logger.info(f"Loading DocLayout-YOLO from {model_path}")
                _YOLO_MODEL = YOLO(str(model_path))
                return _YOLO_MODEL

        # Try loading from HuggingFace or default
        logger.info("Loading DocLayout-YOLO from default location")
        _YOLO_MODEL = YOLO("yolov10x")  # Fallback to standard YOLO
        return _YOLO_MODEL

    except ImportError:
        logger.warning("ultralytics not installed, DocLayout-YOLO disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to load DocLayout-YOLO: {e}")
        return None


def run_doclayout_yolo(image_path: Path, conf_threshold: float = 0.25) -> dict[str, Any]:
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
                elif "picture" in class_lower or "figure" in class_lower or "image" in class_lower:
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
    """Parse DIQA-5000 labels (MOS scores from CSV)."""
    labels = OriginalLabels()

    # Try to find and parse the CSV file
    csv_files = ["train/train.csv", "val/val.csv", "test/test.csv"]
    for csv_file in csv_files:
        csv_path = dataset_path / csv_file
        if csv_path.exists():
            try:
                import csv

                with open(csv_path, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Match by filename
                        if row.get("image_name") == image_path.name:
                            if "mos" in row:
                                labels.diqa_mos = float(row["mos"])
                            if "mos_std" in row:
                                labels.diqa_mos_std = float(row["mos_std"])
                            break
            except Exception as e:
                logger.debug(f"Failed to parse DIQA labels from {csv_path}: {e}")

    return labels


def parse_smartdoc_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse SmartDoc-QA labels."""
    return OriginalLabels()  # Placeholder


def parse_dibco_labels(dataset_path: Path, image_path: Path) -> OriginalLabels:
    """Parse DIBCO labels (binary ground truth)."""
    return OriginalLabels()  # Placeholder


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
        logger.debug(f"Loaded COCO annotations from {coco_path}: {len(filename_to_id)} images")
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
    for part in parts:
        if part.startswith("writer"):
            labels.signatr_writer_id = part
            break

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
        return EnrichmentTier.TIER_0_EXACT, "Dataset content type is exact by construction"

    # Tier 1: Has COCO annotations we can derive from
    if dataset_name in TIER_1_DATASETS:
        has_annotations = any([
            original_labels.doclaynet_annotations,
            original_labels.tablebank_annotations,
            original_labels.funsd_annotations,
        ])
        if has_annotations:
            return EnrichmentTier.TIER_1_ANNOTATION, "Derived from COCO/JSON annotations"

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
) -> EnrichmentData:
    """Apply tiered enrichment logic to determine content flags.

    Tier 0: Exact by construction (dataset IS 100% this content type)
    Tier 1: Derived from COCO/JSON annotations
    Tier 2: DocLayout-YOLO inference
    Tier 3: Dataset-level heuristics (fallback)
    """
    dataset_name = sample.dataset_name
    original_labels = sample.original_labels

    tier, tier_description = get_enrichment_tier(dataset_name, config, original_labels, use_yolo)

    enrichment = EnrichmentData(
        capture_method=config["capture_method"].value,
        capture_confidence=0.95 if config["capture_method"] != CaptureMethod.UNKNOWN else 0.5,
        capture_detection_method="dataset_config",
        resolution_dpi=sample.original_file.dpi,
        resolution_category=categorize_dpi(sample.original_file.dpi).value,
        resolution_pixels=(sample.original_file.width_px, sample.original_file.height_px),
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
) -> list[SampleMetadata]:
    """Scan a dataset and create initial metadata records."""
    samples: list[SampleMetadata] = []

    dataset_path = config["path"]
    pattern = config["pattern"]

    if not dataset_path.exists():
        logger.warning(f"Dataset path not found: {dataset_path}")
        return samples

    # Check for arrow format (special handling)
    if config.get("arrow_format"):
        extracted_dir = dataset_path / "extracted_images"
        if not extracted_dir.exists() or not any(extracted_dir.iterdir()):
            logger.warning(f"{dataset_name} requires extraction. Run --extract-omnidocbench first.")
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
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}:
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

        # Apply tiered enrichment
        tier, tier_desc = get_enrichment_tier(dataset_name, config, original_labels, use_yolo)
        enrichment = apply_tiered_enrichment(sample, config, image_path, use_yolo, git_sha)

        # Add enrichment with reproducibility fields
        sample.add_enrichment(
            data=enrichment,
            created_by=f"annotate_base_metadata.py_v{SCRIPT_VERSION}",
            method=tier.value,
            description=tier_desc,
            git_sha=git_sha,
            model_checkpoint="doclayout_yolo" if tier == EnrichmentTier.TIER_2_MODEL else None,
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
        version_info = sample.enrichment_versions[-1] if sample.enrichment_versions else None

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
            # Enrichment data
            "enrichment_version": sample.current_version,
            "enrichment_tier": enrichment.content_flags_tier if enrichment else None,
            "enrichment_source": enrichment.content_flags_source if enrichment else None,
            "capture_method": enrichment.capture_method if enrichment else None,
            "capture_confidence": enrichment.capture_confidence if enrichment else None,
            "domain_level1": enrichment.domain_level1 if enrichment else None,
            "resolution_category": enrichment.resolution_category if enrichment else None,
            # Content flags
            "has_table": enrichment.has_table if enrichment else None,
            "has_formula": enrichment.has_formula if enrichment else None,
            "has_handwriting": enrichment.has_handwriting if enrichment else None,
            "has_signature": enrichment.has_signature if enrichment else None,
            "has_figure": enrichment.has_figure if enrichment else None,
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
            "schema_version": SCHEMA_VERSION,
            "script_version": SCRIPT_VERSION,
            "git_sha": get_git_sha(),
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

    parser.add_argument("--scan", action="store_true", help="Scan datasets and create metadata")
    parser.add_argument("--dataset", type=str, help="Specific dataset to process")
    parser.add_argument("--limit", type=int, help="Limit samples per dataset")
    parser.add_argument("--no-yolo", action="store_true", help="Disable DocLayout-YOLO (use Tier 3 fallback)")
    parser.add_argument("--stats", action="store_true", help="Generate statistics report")
    parser.add_argument("--export", action="store_true", help="Export to Parquet")
    parser.add_argument("--extract-omnidocbench", action="store_true", help="Extract OmniDocBench images from arrow")
    parser.add_argument("--output", type=Path, default=METADATA_ROOT, help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

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
                tier = "Tier 0" if name in TIER_0_DATASETS else "Tier 1" if name in TIER_1_DATASETS else "Tier 2/3"
                logger.info(f"  {name}: {config['path']} ({tier})")
            return

        for dataset_name, config in datasets_to_scan.items():
            samples = scan_dataset(dataset_name, config, limit=args.limit, use_yolo=use_yolo)
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
                "with_human_mos": df["diqa_mos"].notna().sum() + df["ocr_quality_score"].notna().sum(),
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
        for tier, count in sorted(stats.get("by_enrichment_tier", {}).items(), key=lambda x: -x[1]):
            logger.info(f"  {tier}: {count:,}")

        logger.info("\nBy Capture Method:")
        for cm, count in sorted(stats.get("by_capture_method", {}).items(), key=lambda x: -x[1]):
            logger.info(f"  {cm}: {count:,}")

        logger.info("\nBy Domain:")
        for domain, count in sorted(stats.get("by_domain", {}).items(), key=lambda x: -x[1]):
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
