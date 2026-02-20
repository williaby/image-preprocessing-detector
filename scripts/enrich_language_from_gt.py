#!/usr/bin/env python3
"""Enrich datasets with OpenLID language detection using ground truth text.

This script processes datasets that have GROUND TRUTH TEXT annotations
(not OCR extraction). It reads text directly from source annotation files
and runs OpenLID language detection.

Supported annotation formats:
- COCO-style JSON (cocotext, mlt19, hiertext)
- DocLayNet COCO annotations
- FUNSD form annotations
- PubTabNet/FinTabNet HTML tables
- Simple text transcription files

Usage:
    # List datasets with ground truth text
    python scripts/enrich_language_from_gt.py --list

    # Process single dataset
    python scripts/enrich_language_from_gt.py --dataset cocotext

    # Process all datasets with ground truth text
    python scripts/enrich_language_from_gt.py --all

    # Dry run (no saves)
    python scripts/enrich_language_from_gt.py --dataset mlt19 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

E_DRIVE_ROOT = Path("/mnt/e/image_detection")
BASE_DATA = E_DRIVE_ROOT / "01_base_data"
METADATA_REGISTRY = E_DRIVE_ROOT / "metadata_registry/json"

# Common glob patterns (S1192: avoid duplicate string literals)
JSON_GLOB = "*.json"

# Dataset configurations with ground truth text locations
DATASETS_WITH_GT_TEXT: dict[str, dict[str, Any]] = {
    # === COCO-style annotations with text ===
    "cocotext": {
        "annotation_file": BASE_DATA / "text_detection/cocotext/cocotext.v2.json",
        "format": "coco_text",
        "text_field": "utf8_string",
        "language_field": "language",  # Already has language!
        "images": 63686,
    },
    "mlt19": {
        "annotation_dir": BASE_DATA / "language/mlt19/TrainGT/TrainGT",
        "format": "mlt19_gt",
        "images": 20000,
    },
    "hiertext": {
        "annotation_file": BASE_DATA / "text_detection/hiertext/gt/train.jsonl",
        "format": "hiertext_json",  # Actually a single JSON file, not JSONL
        "images": 11639,
    },
    # === Document layout with text ===
    "doclaynet": {
        "annotation_file": BASE_DATA
        / "documents/doclaynet/ground_truth/coco/train.json",
        "format": "doclaynet_coco",
        "images": 80863,
    },
    # === Form annotations ===
    "funsd": {
        "annotation_dir": BASE_DATA / "forms/funsd/train/annotations",
        "format": "funsd_json",
        "images": 199,
    },
    # === Table HTML ===
    "pubtabnet": {
        "annotation_file": BASE_DATA
        / "tables/pubtabnet/pubtabnet/PubTabNet_2.0.0.jsonl",
        "format": "pubtabnet_jsonl",
        "images": 519030,
    },
    "fintabnet": {
        "annotation_dir": BASE_DATA / "tables/fintabnet/FinTabNet.c-PDF_Annotations",
        "format": "fintabnet_dir",
        "images": 97475,
    },
    # === Script identification datasets ===
    "mdiw13": {
        "annotation_dir": BASE_DATA / "language/mdiw13",
        "format": "mdiw13",
        "images": 290213,
    },
    "siw13": {
        "annotation_dir": BASE_DATA / "language/siw13",
        "format": "siw13",
        "images": 16291,
    },
    "cvsi": {
        "annotation_dir": BASE_DATA / "language/cvsi",
        "format": "cvsi",
        "images": 10715,
    },
    # === OCR ground truth ===
    "arabic_docs_ocr": {
        "annotation_dir": BASE_DATA / "language/arabic_docs_ocr",
        "format": "arabic_ocr_gt",
        "images": 10045,
        "known_language": "ar",
        "known_script": "Arab",
    },
    "yarmouk_ocr": {
        "annotation_dir": BASE_DATA / "language/yarmouk_ocr",
        "format": "arabic_ocr_gt",
        "images": 15062,
        "known_language": "ar",
        "known_script": "Arab",
    },
    "muharaf": {
        "annotation_dir": BASE_DATA / "handwriting/muharaf",
        "format": "arabic_ocr_gt",
        "images": 24952,
        "known_language": "ar",
        "known_script": "Arab",
    },
    # === Handwriting datasets ===
    "iam": {
        "annotation_file": BASE_DATA / "handwriting/iam/ascii/words.txt",
        "format": "iam_words",
        "images": 130212,
        "known_language": "en",
        "known_script": "Latn",
    },
    "pucit-ohul": {
        "annotation_dir": BASE_DATA / "handwriting/pucit_ohul",
        "format": "urdu_handwriting",
        "images": 7401,
        "known_language": "ur",
        "known_script": "Arab",
    },
    "nepali_handwritten": {
        "annotation_dir": BASE_DATA / "handwriting/nepali_handwritten",
        "format": "nepali_chars",
        "images": 958,
        "known_language": "ne",
        "known_script": "Deva",
    },
    # === Tibetan ===
    "tibhcr": {
        "annotation_dir": BASE_DATA / "handwriting/tibhcr",
        "format": "tibetan_chars",
        "images": 141698,
        "known_language": "bo",
        "known_script": "Tibt",
    },
    # === Hindi synthetic ===
    "hindi_ocr_synthetic": {
        "annotation_dir": BASE_DATA / "language/hindi_ocr_synthetic",
        "format": "hindi_synthetic",
        "images": 80009,
        "known_language": "hi",
        "known_script": "Deva",
    },
    # === Synthetic multiscript ===
    "synth-multiscript-250k": {
        "annotation_file": E_DRIVE_ROOT
        / "03_training_datasets/synthetic_multiscript/metadata.parquet",
        "format": "synth_multiscript",
        "images": 250000,
    },
    # === Receipt OCR ===
    "sroie": {
        "annotation_dir": BASE_DATA / "forms/sroie_voxel51_labeled/annotations",
        "format": "sroie_voxel51_json",
        "images": 973,
    },
    # NOTE: cc_ocr has images but no text annotation files available locally
    # Would need to download answers.tsv from the original CC-OCR dataset
    # === ID documents ===
    "midv500": {
        "annotation_dir": BASE_DATA / "documents/midv500",
        "format": "midv500_json",
        "images": 3612,
    },
    "midv500_data": {
        "annotation_dir": BASE_DATA / "documents/midv500_data",
        "format": "midv500_json",
        "images": 15050,
    },
    # === Multilingual scripts ===
    "multilingual_scripts": {
        "annotation_dir": BASE_DATA / "language/multilingual_scripts",
        "format": "multilingual_scripts",
        "images": 3279,
    },
    # === NIST ===
    "nist-sd19": {
        "annotation_dir": BASE_DATA / "handwriting/nist_sd19",
        "format": "nist_chars",
        "images": 3669,
        "known_language": "en",
        "known_script": "Latn",
    },
    # === RVL-CDIP ===
    "rvl_cdip": {
        "annotation_file": BASE_DATA / "documents/rvl_cdip/labels/train.txt",
        "format": "rvl_cdip_labels",
        "images": 16000,
        "known_language": "en",
        "known_script": "Latn",
    },
    # === Known-language datasets (monolingual) ===
    "financebench": {
        "annotation_file": E_DRIVE_ROOT
        / "02_benchmark_only/financebench/data/financebench_open_source.jsonl",
        "format": "financebench_jsonl",
        "images": 54121,
        "known_language": "en",
        "known_script": "Latn",
    },
    "im2latex": {
        "annotation_dir": BASE_DATA / "formulas/im2latex",
        "format": "im2latex",
        "images": 10000,
        "known_language": "en",
        "known_script": "Latn",
    },
    "mathverse": {
        "annotation_dir": E_DRIVE_ROOT / "02_benchmark_only/mathverse",
        "format": "mathverse",
        "images": 6940,
        "known_language": "en",
        "known_script": "Latn",
    },
    "multimodal_textbook": {
        "annotation_dir": BASE_DATA / "educational/multimodal_textbook",
        "format": "multimodal_textbook",
        "images": 1113,
        "known_language": "en",
        "known_script": "Latn",
    },
    "jssoda": {
        "annotation_dir": BASE_DATA / "language/multilingual_scripts/jssoda",
        "format": "jssoda",
        "images": 2000,
        "known_language": "ja",
        "known_script": "Jpan",
    },
    "funsd_plus": {
        "annotation_dir": BASE_DATA / "forms/funsd_plus/annotations",
        "format": "funsd_json",
        "images": 1139,
        "known_language": "en",
        "known_script": "Latn",
    },
    # === Datasets needing OpenLID detection ===
    "ohr-bench": {
        "annotation_dir": E_DRIVE_ROOT / "02_benchmark_only/ohr-bench/dataset/train",
        "format": "ohr_bench_arrow",
        "images": 16091,
    },
    "invoices_kg": {
        "annotation_file": BASE_DATA / "forms/invoices_kaggle/train/annotations.json",
        "format": "invoices_kg_json",
        "images": 1414,
    },
    # NOTE: omnidocbench arrow files contain only images, no text annotations
    # Requires OCR extraction before language detection can be run
    "ocr_quality": {
        "annotation_file": BASE_DATA / "ocr_quality/OCR-Quality.json",
        "format": "ocr_quality_json",
        "images": 1000,
    },
}

# =============================================================================
# Docling OCR Extracted Text Datasets
# =============================================================================
# These datasets have Docling OCR extracted text (not ground truth)
# Stored in /mnt/e/image_detection/annotations/{dataset}/ocr/*.jsonl

DOCLING_OCR_DATASETS: dict[str, dict[str, Any]] = {
    "diqa-5000": {
        "annotation_dir": E_DRIVE_ROOT / "annotations/diqa-5000",
        "format": "docling_ocr",
        "images": 5499,
    },
    "nist-sd2": {
        "annotation_dir": E_DRIVE_ROOT / "annotations/nist-sd2",
        "format": "docling_ocr",
        "images": 5590,
    },
    "nist-sd6": {
        "annotation_dir": E_DRIVE_ROOT / "annotations/nist-sd6",
        "format": "docling_ocr",
        "images": 5593,
    },
    "rvl-cdip": {
        "annotation_dir": E_DRIVE_ROOT / "annotations/rvl-cdip",
        "format": "docling_ocr",
        "images": 15903,
    },
    "smartdoc-qa": {
        "annotation_dir": E_DRIVE_ROOT / "annotations/smartdoc-qa",
        "format": "docling_ocr",
        "images": 2835,
    },
    # NOTE: sroie-docling removed - old annotations were from contaminated dataset (deleted)
    # Re-run Docling OCR on sroie_icdar2019 if needed
    "funsd-docling": {
        "annotation_dir": E_DRIVE_ROOT / "annotations/funsd",
        "format": "docling_ocr",
        "images": 1324,
    },
}


@dataclass
class LanguageResult:
    """Result of language detection."""

    language: str  # ISO 639-1/3
    script: str | None  # ISO 15924
    confidence: float
    method: str
    detected_languages: list[str]
    detected_scripts: list[str]


# =============================================================================
# OpenLID Integration
# =============================================================================

_openlid_detector = None


def get_openlid_detector():
    """Lazy-load OpenLID detector."""
    global _openlid_detector
    if _openlid_detector is None:
        try:
            from image_preprocessing_detector.schema_utils.openlid_integration import (
                OpenLIDDetector,
            )

            logger.info("Loading OpenLID-v2 detector...")
            _openlid_detector = OpenLIDDetector(auto_download=True)
            # Warm up
            _openlid_detector.detect("test")
            logger.info("OpenLID-v2 ready")
        except Exception as e:
            logger.error(f"Failed to load OpenLID: {e}")
            raise
    return _openlid_detector


def detect_language(text: str) -> LanguageResult:
    """Detect language using OpenLID-v2."""
    if not text or len(text.strip()) < 3:
        return LanguageResult(
            language="und",
            script=None,
            confidence=0.0,
            method="text_too_short",
            detected_languages=[],
            detected_scripts=[],
        )

    detector = get_openlid_detector()
    result = detector.detect(text)

    return LanguageResult(
        language=result.language_639_1 or result.language_639_3,
        script=result.script_code,
        confidence=result.confidence,
        method="openlid_v2",
        detected_languages=[result.language_639_1 or result.language_639_3],
        detected_scripts=[result.script_code] if result.script_code else [],
    )


# =============================================================================
# Text Extraction Functions
# =============================================================================


def extract_text_coco(
    annotation_file: Path, text_field: str = "utf8_string"
) -> dict[int, str]:
    """Extract text from COCO-style annotations, aggregated per image."""
    logger.info(f"Loading COCO annotations from {annotation_file}")

    with open(annotation_file) as f:
        data = json.load(f)

    anns = data.get("anns", {})
    if isinstance(anns, dict):
        anns = list(anns.values())

    # Aggregate text per image
    image_texts: dict[int, list[str]] = defaultdict(list)

    for ann in anns:
        image_id = ann.get("image_id")
        text = ann.get(text_field, "")
        if image_id and text:
            image_texts[image_id].append(text)

    # Join texts
    result = {img_id: " ".join(texts) for img_id, texts in image_texts.items()}
    logger.info(f"Extracted text for {len(result)} images")
    return result


def extract_text_hiertext(annotation_file: Path) -> dict[str, str]:
    """Extract text from HierText JSON format (single JSON file with annotations)."""
    logger.info(f"Loading HierText annotations from {annotation_file}")

    image_texts: dict[str, list[str]] = defaultdict(list)

    with open(annotation_file) as f:
        data = json.load(f)

    annotations = data.get("annotations", [])

    for ann in annotations:
        image_id = ann.get("image_id", "")
        paragraphs = ann.get("paragraphs", [])

        for para in paragraphs:
            for line_obj in para.get("lines", []):
                # Get line text directly
                line_text = line_obj.get("text", "")
                if line_text:
                    image_texts[image_id].append(line_text)

    result = {img_id: " ".join(texts) for img_id, texts in image_texts.items()}
    logger.info(f"Extracted text for {len(result)} images")
    return result


def extract_text_pubtabnet(annotation_file: Path) -> dict[str, str]:
    """Extract text from PubTabNet JSONL (table HTML)."""
    logger.info(f"Loading PubTabNet from {annotation_file}")

    image_texts: dict[str, str] = {}

    with open(annotation_file) as f:
        for line in f:
            doc = json.loads(line)
            filename = doc.get("filename", "")
            html = doc.get("html", {})

            # Extract text from HTML structure
            cells = html.get("cells", [])
            texts = []
            for cell in cells:
                tokens = cell.get("tokens", [])
                # Filter out HTML tags
                for token in tokens:
                    if not token.startswith("<") and not token.endswith(">"):
                        texts.append(token)

            if texts:
                image_texts[filename] = " ".join(texts)

    logger.info(f"Extracted text for {len(image_texts)} tables")
    return image_texts


def extract_text_funsd(annotation_dir: Path) -> dict[str, str]:
    """Extract text from FUNSD JSON annotations."""
    logger.info(f"Loading FUNSD annotations from {annotation_dir}")

    image_texts: dict[str, str] = {}

    for json_file in annotation_dir.glob(JSON_GLOB):
        with open(json_file) as f:
            data = json.load(f)

        form = data.get("form", [])
        texts = []
        for item in form:
            text = item.get("text", "")
            if text:
                texts.append(text)
            # Also get words
            words = item.get("words", [])
            for word in words:
                word_text = word.get("text", "")
                if word_text:
                    texts.append(word_text)

        if texts:
            image_id = json_file.stem
            image_texts[image_id] = " ".join(texts)

    logger.info(f"Extracted text for {len(image_texts)} forms")
    return image_texts


def extract_text_mlt19(annotation_dir: Path) -> dict[str, str]:
    """Extract text from MLT19 ground truth files."""
    logger.info(f"Loading MLT19 GT from {annotation_dir}")

    image_texts: dict[str, str] = {}

    for gt_file in annotation_dir.glob("*.txt"):
        texts = []
        with open(gt_file, encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 9:
                    # Format: x1,y1,x2,y2,x3,y3,x4,y4,script,text
                    text = ",".join(parts[9:])  # Text may contain commas
                    if text:
                        texts.append(text)

        if texts:
            image_id = gt_file.stem.replace("gt_", "")
            image_texts[image_id] = " ".join(texts)

    logger.info(f"Extracted text for {len(image_texts)} images")
    return image_texts


def extract_text_iam(annotation_file: Path) -> dict[str, str]:
    """Extract text from IAM words.txt format."""
    logger.info(f"Loading IAM words from {annotation_file}")

    image_texts: dict[str, list[str]] = defaultdict(list)

    with open(annotation_file, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split()
            if len(parts) >= 9:
                word_id = parts[0]  # a01-000u-00-00
                word = parts[-1]  # Last field is the word
                # Group by form (first two parts of word_id)
                form_id = "-".join(word_id.split("-")[:2])
                image_texts[form_id].append(word)

    result = {form_id: " ".join(words) for form_id, words in image_texts.items()}
    logger.info(f"Extracted text for {len(result)} forms")
    return result


def extract_text_sroie(annotation_dir: Path) -> dict[str, str]:
    """Extract text from SROIE box format."""
    logger.info(f"Loading SROIE from {annotation_dir}")

    image_texts: dict[str, str] = {}

    for txt_file in annotation_dir.glob("*.txt"):
        texts = []
        with open(txt_file, encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 9:
                    # Format: x1,y1,x2,y2,x3,y3,x4,y4,text
                    text = ",".join(parts[8:])
                    if text:
                        texts.append(text)

        if texts:
            image_texts[txt_file.stem] = " ".join(texts)

    logger.info(f"Extracted text for {len(image_texts)} receipts")
    return image_texts


def extract_text_cc_ocr(annotation_file: Path) -> dict[str, str]:
    """Extract text from CC-OCR TSV format."""
    logger.info(f"Loading CC-OCR from {annotation_file}")

    image_texts: dict[str, str] = {}

    with open(annotation_file, encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                image_id = parts[0]
                text = parts[1]
                image_texts[image_id] = text

    logger.info(f"Extracted text for {len(image_texts)} images")
    return image_texts


def _count_scripts_in_subdirs(parent_dir: Path) -> dict[str, int]:
    """Count images per script folder under a parent directory.

    Iterates over subdirectories of parent_dir, treating each as a script
    category and counting files matching ``*.*``.

    Returns:
        Mapping of script_name -> image count.
    """
    folder_scripts: dict[str, int] = {}
    for script_dir in parent_dir.iterdir():
        if not script_dir.is_dir():
            continue
        script_name = script_dir.name
        img_count = sum(1 for _ in script_dir.glob("*.*"))
        folder_scripts[script_name] = folder_scripts.get(script_name, 0) + img_count
    return folder_scripts


def _get_folder_label_parent_dirs(
    annotation_dir: Path, dataset_name: str
) -> list[Path] | None:
    """Return parent directories whose children are script folders.

    Returns None if the expected base path does not exist.
    """
    if dataset_name == "mdiw13":
        base_path = annotation_dir / "SIW_Database" / "SIW_MultiscriptDatabase"
        if not base_path.exists():
            logger.warning(f"MDIW13 path not found: {base_path}")
            return None
        return [d for d in base_path.iterdir() if d.is_dir()]

    if dataset_name == "siw13":
        base_path = annotation_dir / "SIW-13"
        if not base_path.exists():
            logger.warning(f"SIW-13 path not found: {base_path}")
            return None
        return [d for d in base_path.iterdir() if d.is_dir()]

    if dataset_name == "cvsi":
        valid_splits = {"Training", "Testing", "Validation"}
        if not annotation_dir.exists():
            logger.warning(f"CVSI path not found: {annotation_dir}")
            return None
        return [
            d for d in annotation_dir.iterdir() if d.is_dir() and d.name in valid_splits
        ]

    return []


def extract_folder_based_labels(
    annotation_dir: Path, dataset_name: str
) -> dict[str, int]:
    """Extract labels from folder-based script identification datasets.

    For datasets like MDIW13, SIW-13, CVSI where folder name = script/language.

    Args:
        annotation_dir: Root directory containing script folders.
        dataset_name: Dataset key used to resolve folder structure.

    Returns:
        Mapping of script folder name to image count.
    """
    logger.info(f"Extracting folder-based labels from {annotation_dir}")

    parent_dirs = _get_folder_label_parent_dirs(annotation_dir, dataset_name)
    if parent_dirs is None:
        return {}

    folder_scripts: dict[str, int] = {}
    for parent in parent_dirs:
        for script_name, count in _count_scripts_in_subdirs(parent).items():
            folder_scripts[script_name] = folder_scripts.get(script_name, 0) + count

    logger.info(
        f"Found {len(folder_scripts)} script categories: {dict(folder_scripts)}"
    )
    return folder_scripts


def extract_text_fintabnet_dir(annotation_dir: Path) -> dict[str, str]:
    """Extract text from FinTabNet JSON files directory.

    Each JSON file contains table cells with json_text_content field.
    """
    logger.info(f"Loading FinTabNet JSONs from {annotation_dir}")

    image_texts: dict[str, str] = {}
    json_files = list(annotation_dir.glob(JSON_GLOB))

    logger.info(f"Processing {len(json_files)} JSON files...")

    for json_file in tqdm(json_files, desc="FinTabNet JSONs"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            texts = []
            # Handle both list and single table formats
            tables = data if isinstance(data, list) else [data]
            for table in tables:
                cells = table.get("cells", [])
                for cell in cells:
                    text = cell.get("json_text_content", "")
                    if text:
                        texts.append(text)

            if texts:
                # Use filename without extension as ID
                image_id = json_file.stem
                image_texts[image_id] = " ".join(texts)
        except (json.JSONDecodeError, KeyError):
            continue  # Skip malformed files

    logger.info(f"Extracted text for {len(image_texts)} tables")
    return image_texts


def extract_text_midv500(annotation_dir: Path) -> dict[str, str]:
    """Extract text from MIDV500 JSON format (ID document fields).

    Document-level JSON files have field01, field02, etc. with 'value' containing text.
    Per-capture JSONs only have 'quad' data - we need document-level files.
    """
    logger.info(f"Loading MIDV500 from {annotation_dir}")

    image_texts: dict[str, str] = {}

    # Find document-level JSON files directly in ground_truth folder (not in subdirs)
    # Pattern: */ground_truth/*.json where file has field values, not just quads
    json_files = list(annotation_dir.rglob("ground_truth/*.json"))

    logger.info(f"Processing {len(json_files)} document JSON files...")

    for json_file in tqdm(json_files, desc="MIDV500 JSONs"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            texts = []
            for key, value in data.items():
                if isinstance(value, dict) and "value" in value:
                    text = value["value"]
                    if text and isinstance(text, str):
                        texts.append(text)

            if texts:
                image_id = json_file.stem
                image_texts[image_id] = " ".join(texts)
        except (json.JSONDecodeError, KeyError):
            continue

    logger.info(f"Extracted text for {len(image_texts)} documents")
    return image_texts


def extract_text_sroie_voxel51(annotation_dir: Path) -> dict[str, str]:
    """Extract text from SROIE voxel51 JSON annotations (text_detections field)."""
    logger.info(f"Loading SROIE voxel51 from {annotation_dir}")

    image_texts: dict[str, str] = {}

    for json_file in annotation_dir.glob(JSON_GLOB):
        try:
            with open(json_file) as f:
                data = json.load(f)

            texts = []
            # Collect structured fields
            for field in ("company", "date", "address", "total"):
                val = data.get(field, "")
                if val:
                    texts.append(str(val))
            # Collect text detections
            for det in data.get("text_detections", []):
                label = det.get("label", "")
                if label:
                    texts.append(label)

            if texts:
                image_texts[json_file.stem] = " ".join(texts)
        except (json.JSONDecodeError, KeyError):
            continue

    logger.info(f"Extracted text for {len(image_texts)} receipts")
    return image_texts


def extract_text_invoices_kg(annotation_file: Path) -> dict[str, str]:
    """Extract text from invoices-kg annotations JSON (ocred_text field)."""
    logger.info(f"Loading invoices-kg from {annotation_file}")

    image_texts: dict[str, str] = {}

    with open(annotation_file) as f:
        data = json.load(f)

    for item in data:
        filename = item.get("filename", "")
        text = item.get("ocred_text", "")
        if filename and text:
            image_texts[filename] = text

    logger.info(f"Extracted text for {len(image_texts)} invoices")
    return image_texts


def extract_text_ocr_quality(annotation_file: Path) -> dict[str, str]:
    """Extract text from OCR-Quality JSON (ocr_text field)."""
    logger.info(f"Loading OCR-Quality from {annotation_file}")

    image_texts: dict[str, str] = {}

    with open(annotation_file) as f:
        data = json.load(f)

    for item in data:
        image_path = item.get("image_path", "")
        text = item.get("ocr_text", "")
        if image_path and text:
            image_id = Path(image_path).stem
            image_texts[image_id] = text

    logger.info(f"Extracted text for {len(image_texts)} images")
    return image_texts


def extract_text_ohr_bench_arrow(annotation_dir: Path) -> dict[str, str]:
    """Extract text from OHR-Bench Arrow IPC streaming format (gt_text field)."""
    logger.info(f"Loading OHR-Bench from {annotation_dir}")

    image_texts: dict[str, str] = {}

    try:
        import pyarrow.ipc as ipc

        for arrow_file in annotation_dir.glob("*.arrow"):
            with open(arrow_file, "rb") as f:
                reader = ipc.open_stream(f)
                table = reader.read_all()

            if "gt_text" not in table.column_names:
                logger.warning(
                    f"No gt_text column in {arrow_file}. Columns: {table.column_names}"
                )
                continue

            # Use doc_name + page_idx as ID if available
            has_doc = "doc_name" in table.column_names
            has_page = "page_idx" in table.column_names

            for i in range(len(table)):
                val = table.column("gt_text")[i].as_py()
                text = str(val) if val else ""
                if has_doc and has_page:
                    doc = str(table.column("doc_name")[i].as_py())
                    page = str(table.column("page_idx")[i].as_py())
                    image_id = f"{doc}_page{page}"
                else:
                    image_id = str(i)
                if text:
                    image_texts[image_id] = text
    except ImportError:
        logger.error("pyarrow not available for Arrow reading")
        return {}
    except Exception as e:
        logger.error(f"Error reading Arrow files: {e}")
        return {}

    logger.info(f"Extracted text for {len(image_texts)} images")
    return image_texts


def extract_text_docling_ocr(annotation_dir: Path) -> dict[str, str]:
    """Extract text from Docling OCR JSONL files.

    JSONL format: {"source": "...", "text": "...", "confidence": 1.0, ...}
    """
    logger.info(f"Loading Docling OCR from {annotation_dir}")

    image_texts: dict[str, str] = {}

    ocr_dir = annotation_dir / "ocr"
    if not ocr_dir.exists():
        logger.warning(f"OCR directory not found: {ocr_dir}")
        return {}

    jsonl_files = list(ocr_dir.glob("*.jsonl"))
    logger.info(f"Processing {len(jsonl_files)} JSONL files...")

    for jsonl_file in jsonl_files:
        with open(jsonl_file, encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    source = data.get("source", "")
                    text = data.get("text", "")
                    success = data.get("success", True)

                    if success and text:
                        # Extract filename from source path
                        image_id = Path(source).stem
                        image_texts[image_id] = text
                except json.JSONDecodeError:
                    continue

    logger.info(f"Extracted text for {len(image_texts)} images")
    return image_texts


def extract_text_synth_multiscript(annotation_file: Path) -> dict[str, str]:
    """Extract text from synth-multiscript parquet file."""
    logger.info(f"Loading synth-multiscript from {annotation_file}")

    try:
        import pandas as pd

        df = pd.read_parquet(annotation_file)

        image_texts: dict[str, str] = {}
        for _, row in df.iterrows():
            # Check for text field
            text = row.get("text", row.get("caption", ""))
            image_id = row.get("file_name", row.get("image_id", ""))
            if text and image_id:
                image_texts[str(image_id)] = str(text)

        logger.info(f"Extracted text for {len(image_texts)} images")
        return image_texts
    except ImportError:
        logger.error("pandas not available for parquet reading")
        return {}
    except Exception as e:
        logger.error(f"Error reading parquet: {e}")
        return {}


def extract_multilingual_scripts_labels(annotation_dir: Path) -> dict[str, int]:
    """Extract script labels from multilingual_scripts combined_manifest.json."""
    logger.info(f"Loading multilingual_scripts from {annotation_dir}")

    manifest_file = annotation_dir / "combined_manifest.json"
    if not manifest_file.exists():
        logger.warning(f"Manifest not found: {manifest_file}")
        return {}

    with open(manifest_file) as f:
        data = json.load(f)

    scripts = data.get("scripts", {})
    logger.info(f"Found scripts: {scripts}")
    return scripts


# =============================================================================
# Script/Language Mapping
# =============================================================================

# Map folder names to ISO 639-1/3 language codes and ISO 15924 script codes
SCRIPT_FOLDER_MAPPING: dict[str, tuple[str, str]] = {
    # MDIW13 folders
    "Arabic": ("ar", "Arab"),
    "Bangla": ("bn", "Beng"),
    "Gujrati": ("gu", "Gujr"),
    "Gurmukhi": ("pa", "Guru"),
    "Hindi": ("hi", "Deva"),
    "Japanese": ("ja", "Jpan"),
    "Kannada": ("kn", "Knda"),
    "Malayalam": ("ml", "Mlym"),
    "Oriya": ("or", "Orya"),
    "Roman": ("en", "Latn"),
    "Tamil": ("ta", "Taml"),
    "Telugu": ("te", "Telu"),
    "Thai": ("th", "Thai"),
    # SIW-13 folders
    "Cambodian": ("km", "Khmr"),
    "Chinese": ("zh", "Hans"),
    "English": ("en", "Latn"),
    "Greek": ("el", "Grek"),
    "Hebrew": ("he", "Hebr"),
    "Korean": ("ko", "Kore"),
    "Mongolian": ("mn", "Mong"),
    "Russian": ("ru", "Cyrl"),
    "Tibetan": ("bo", "Tibt"),
    # CVSI folders
    "Bengali": ("bn", "Beng"),
    "Gujrathi": ("gu", "Gujr"),
    "Punjabi": ("pa", "Guru"),
    "Telegu": ("te", "Telu"),
    # Multilingual scripts
    "arabic": ("ar", "Arab"),
    "tibetan": ("bo", "Tibt"),
    "japanese": ("ja", "Jpan"),
}


# =============================================================================
# Main Processing
# =============================================================================


def _extract_text_by_format(fmt: str, config: dict[str, Any]) -> dict[str, str] | None:
    """Dispatch text extraction to the appropriate format handler.

    Returns:
        Extracted image_texts dict, or None if the format is unsupported.
    """
    # Formats that use annotation_file
    file_extractors: dict[str, Any] = {
        "coco_text": lambda: extract_text_coco(
            config["annotation_file"], config.get("text_field", "utf8_string")
        ),
        "hiertext_json": lambda: extract_text_hiertext(config["annotation_file"]),
        "hiertext_jsonl": lambda: extract_text_hiertext(config["annotation_file"]),
        "pubtabnet_jsonl": lambda: extract_text_pubtabnet(config["annotation_file"]),
        "fintabnet_jsonl": lambda: extract_text_pubtabnet(config["annotation_file"]),
        "iam_words": lambda: extract_text_iam(config["annotation_file"]),
        "cc_ocr_tsv": lambda: extract_text_cc_ocr(config["annotation_file"]),
        "synth_multiscript": lambda: extract_text_synth_multiscript(
            config["annotation_file"]
        ),
        "invoices_kg_json": lambda: extract_text_invoices_kg(config["annotation_file"]),
        "ocr_quality_json": lambda: extract_text_ocr_quality(config["annotation_file"]),
    }

    # Formats that use annotation_dir
    dir_extractors: dict[str, Any] = {
        "funsd_json": lambda: extract_text_funsd(config["annotation_dir"]),
        "mlt19_gt": lambda: extract_text_mlt19(config["annotation_dir"]),
        "sroie_box": lambda: extract_text_sroie(config["annotation_dir"]),
        "docling_ocr": lambda: extract_text_docling_ocr(config["annotation_dir"]),
        "fintabnet_dir": lambda: extract_text_fintabnet_dir(config["annotation_dir"]),
        "midv500_json": lambda: extract_text_midv500(config["annotation_dir"]),
        "sroie_voxel51_json": lambda: extract_text_sroie_voxel51(
            config["annotation_dir"]
        ),
        "ohr_bench_arrow": lambda: extract_text_ohr_bench_arrow(
            config["annotation_dir"]
        ),
    }

    extractor = file_extractors.get(fmt) or dir_extractors.get(fmt)
    if extractor:
        return extractor()
    return None


def _process_known_language(
    dataset_name: str, config: dict[str, Any], dry_run: bool
) -> dict[str, int]:
    """Handle datasets with a known mono-script language."""
    known_lang = config["known_language"]
    known_script = config["known_script"]
    image_count = config.get("images", 0)

    logger.info(
        f"Dataset {dataset_name} has known language: {known_lang}/{known_script}"
    )
    if not dry_run:
        update_registry_known_language(
            dataset_name, known_lang, known_script, image_count
        )

    return {
        "total": image_count,
        "processed": 0,
        "known_language": image_count,
        "detected": 0,
        "undetermined": 0,
    }


def _process_doclaynet_coco(
    dataset_name: str, config: dict[str, Any], dry_run: bool
) -> dict[str, int]:
    """Handle DocLayNet COCO format (no text, mark as English)."""
    logger.info("DocLayNet has no text in COCO - using known language en/Latn")
    image_count = config.get("images", 0)
    if not dry_run:
        update_registry_known_language(dataset_name, "en", "Latn", image_count)
    return {
        "total": image_count,
        "processed": 0,
        "known_language": image_count,
        "detected": 0,
        "undetermined": 0,
    }


def _process_folder_based(
    dataset_name: str, config: dict[str, Any], dry_run: bool
) -> dict[str, int]:
    """Handle folder-based script identification datasets."""
    stats = {
        "total": 0,
        "processed": 0,
        "known_language": 0,
        "detected": 0,
        "undetermined": 0,
    }
    folder_scripts = extract_folder_based_labels(config["annotation_dir"], dataset_name)
    if folder_scripts:
        if not dry_run:
            save_folder_based_results(dataset_name, folder_scripts)
        total_images = sum(folder_scripts.values())
        stats["known_language"] = total_images
        stats["total"] = total_images
    return stats


def _process_multilingual_scripts(
    dataset_name: str, config: dict[str, Any], dry_run: bool
) -> dict[str, int]:
    """Handle multilingual scripts manifest datasets."""
    stats = {
        "total": 0,
        "processed": 0,
        "known_language": 0,
        "detected": 0,
        "undetermined": 0,
    }
    scripts = extract_multilingual_scripts_labels(config["annotation_dir"])
    if scripts:
        if not dry_run:
            save_multilingual_scripts_results(dataset_name, scripts)
        total_images = sum(scripts.values())
        stats["known_language"] = total_images
        stats["total"] = total_images
    return stats


def _extract_gt_language(
    dataset_name: str,
    config: dict[str, Any],
    language_field: str,
    dry_run: bool,
) -> dict[str, int]:
    """Extract GT language labels directly from annotations when the dataset provides them.

    Args:
        dataset_name: Dataset key being processed.
        config: Dataset configuration with annotation_file and language_field.
        language_field: Field name in each annotation containing the GT language.
        dry_run: If True, do not write output files.

    Returns:
        Aggregated processing statistics.
    """
    annotation_file = config.get("annotation_file")
    stats = {
        "total": 0,
        "processed": 0,
        "known_language": 0,
        "detected": 0,
        "undetermined": 0,
    }

    if not annotation_file or not Path(annotation_file).exists():
        logger.warning(
            f"Annotation file not found for {dataset_name}: {annotation_file}"
        )
        return stats

    with open(annotation_file, encoding="utf-8") as f:
        data = json.load(f)

    anns = data.get("anns", {})
    if isinstance(anns, dict):
        anns = list(anns.values())

    # Aggregate GT language per image (use majority language if annotations differ)
    image_lang: dict[str, list[str]] = defaultdict(list)
    for ann in anns:
        image_id = ann.get("image_id")
        language = ann.get(language_field, "")
        if image_id and language:
            image_lang[str(image_id)].append(language)

    stats["total"] = len(image_lang)
    results: list[tuple[str, LanguageResult]] = []

    for image_id, languages in image_lang.items():
        # Use most frequent language as the GT label
        lang_count: dict[str, int] = defaultdict(int)
        for lang in languages:
            lang_count[lang] += 1
        best_lang = max(lang_count, key=lambda k, lc=lang_count: lc[k])

        result = LanguageResult(
            language=best_lang if best_lang else "und",
            script=None,
            confidence=1.0,
            method="ground_truth",
            detected_languages=[best_lang] if best_lang else [],
            detected_scripts=[],
        )
        results.append((image_id, result))
        if best_lang and best_lang != "und":
            stats["detected"] += 1
            stats["known_language"] += 1
        else:
            stats["undetermined"] += 1
        stats["processed"] += 1

    logger.info(
        f"Extracted GT language for {stats['detected']} / {stats['total']} images"
    )

    if not dry_run and results:
        save_language_results(dataset_name, results)

    return stats


def _run_openlid_detection(
    dataset_name: str,
    image_texts: dict[str, str],
    batch_size: int,
    dry_run: bool,
) -> dict[str, int]:
    """Run OpenLID on extracted text and return stats."""
    stats = {
        "total": len(image_texts),
        "processed": 0,
        "known_language": 0,
        "detected": 0,
        "undetermined": 0,
    }

    logger.info(f"Running OpenLID on {len(image_texts)} texts...")

    results: list[tuple[str, LanguageResult]] = []

    for image_id, text in tqdm(image_texts.items(), desc=f"Detecting {dataset_name}"):
        result = detect_language(text)
        results.append((image_id, result))

        if result.language == "und":
            stats["undetermined"] += 1
        else:
            stats["detected"] += 1

        stats["processed"] += 1

        if stats["processed"] % batch_size == 0:
            logger.info(
                f"Processed {stats['processed']}/{stats['total']} | "
                f"Detected: {stats['detected']} | Undetermined: {stats['undetermined']}"
            )

    # Aggregate language statistics
    lang_counts: dict[str, int] = defaultdict(int)
    for _, result in results:
        if result.language != "und":
            lang_counts[result.language] += 1

    logger.info(f"Language distribution for {dataset_name}:")
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:10]:
        pct = count / max(1, stats["detected"]) * 100
        logger.info(f"  {lang}: {count:,} ({pct:.1f}%)")

    if not dry_run and results:
        save_language_results(dataset_name, results)

    return stats


def process_dataset(
    dataset_name: str,
    config: dict[str, Any],
    dry_run: bool = False,
    batch_size: int = 1000,
) -> dict[str, int]:
    """Process a single dataset for language enrichment.

    Args:
        dataset_name: Dataset key to process.
        config: Dataset configuration.
        dry_run: If True, do not write output files.
        batch_size: Progress logging batch size.

    Returns:
        Aggregated processing statistics.
    """
    _empty_stats = {
        "total": 0,
        "processed": 0,
        "known_language": 0,
        "detected": 0,
        "undetermined": 0,
    }

    # Check for known language (mono-script datasets)
    if config.get("known_language") and config.get("known_script"):
        return _process_known_language(dataset_name, config, dry_run)

    fmt = config.get("format", "")

    # Special-case formats that return early
    if fmt == "doclaynet_coco":
        return _process_doclaynet_coco(dataset_name, config, dry_run)
    if fmt in ("mdiw13", "siw13", "cvsi"):
        return _process_folder_based(dataset_name, config, dry_run)
    if fmt == "multilingual_scripts":
        return _process_multilingual_scripts(dataset_name, config, dry_run)

    # Extract text via format dispatch
    try:
        image_texts = _extract_text_by_format(fmt, config)
    except FileNotFoundError as e:
        logger.error(f"Annotation file not found: {e}")
        return _empty_stats
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return _empty_stats

    if image_texts is None:
        logger.warning(f"Unsupported format: {fmt}")
        return _empty_stats

    if not image_texts:
        logger.warning(f"No text extracted for {dataset_name}")
        return {**_empty_stats, "total": len(image_texts)}

    # Check for existing language field (e.g., cocotext has language)
    language_field = config.get("language_field")
    if language_field:
        logger.info(
            f"Dataset {dataset_name} has existing language annotations "
            f"(field: {language_field!r}); extracting GT labels directly"
        )
        return _extract_gt_language(dataset_name, config, language_field, dry_run)

    return _run_openlid_detection(dataset_name, image_texts, batch_size, dry_run)


def update_registry_known_language(
    dataset_name: str,
    language: str,
    script: str,
    count: int,
) -> None:
    """Update metadata registry with known language for mono-script dataset."""
    output_file = METADATA_REGISTRY / f"{dataset_name}_language_enrichment.json"

    result = {
        "dataset": dataset_name,
        "enrichment_type": "known_language",
        "language": language,
        "script": script,
        "sample_count": count,
        "confidence": 1.0,
        "method": "dataset_known_language",
        "created_at": datetime.now(UTC).isoformat(),
    }

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Saved known language to {output_file}")


def save_folder_based_results(
    dataset_name: str,
    folder_scripts: dict[str, int],
) -> None:
    """Save folder-based script identification results."""
    output_file = METADATA_REGISTRY / f"{dataset_name}_language_enrichment.json"

    # Map folder names to language/script codes
    script_distribution: dict[str, int] = {}
    language_distribution: dict[str, int] = {}
    total_images = 0

    for folder_name, count in folder_scripts.items():
        mapping = SCRIPT_FOLDER_MAPPING.get(folder_name)
        if mapping:
            lang, script = mapping
            language_distribution[lang] = language_distribution.get(lang, 0) + count
            script_distribution[script] = script_distribution.get(script, 0) + count
        else:
            logger.warning(f"Unknown script folder: {folder_name}")
            language_distribution["und"] = language_distribution.get("und", 0) + count
        total_images += count

    result = {
        "dataset": dataset_name,
        "enrichment_type": "folder_based_labels",
        "total_samples": total_images,
        "folder_counts": folder_scripts,
        "language_distribution": dict(
            sorted(language_distribution.items(), key=lambda x: -x[1])
        ),
        "script_distribution": dict(
            sorted(script_distribution.items(), key=lambda x: -x[1])
        ),
        "confidence": 1.0,
        "method": "folder_name_label",
        "created_at": datetime.now(UTC).isoformat(),
    }

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Saved folder-based results to {output_file}")


def save_multilingual_scripts_results(
    dataset_name: str,
    scripts: dict[str, int],
) -> None:
    """Save multilingual scripts results from manifest."""
    output_file = METADATA_REGISTRY / f"{dataset_name}_language_enrichment.json"

    # Map script names to codes
    language_distribution: dict[str, int] = {}
    script_distribution: dict[str, int] = {}

    for script_name, count in scripts.items():
        mapping = SCRIPT_FOLDER_MAPPING.get(script_name.lower())
        if mapping:
            lang, script = mapping
            language_distribution[lang] = language_distribution.get(lang, 0) + count
            script_distribution[script] = script_distribution.get(script, 0) + count
        else:
            language_distribution["und"] = language_distribution.get("und", 0) + count

    result = {
        "dataset": dataset_name,
        "enrichment_type": "manifest_labels",
        "total_samples": sum(scripts.values()),
        "script_counts": scripts,
        "language_distribution": dict(
            sorted(language_distribution.items(), key=lambda x: -x[1])
        ),
        "script_distribution": dict(
            sorted(script_distribution.items(), key=lambda x: -x[1])
        ),
        "confidence": 1.0,
        "method": "manifest_label",
        "created_at": datetime.now(UTC).isoformat(),
    }

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Saved multilingual scripts results to {output_file}")


def save_language_results(
    dataset_name: str,
    results: list[tuple[str, LanguageResult]],
) -> None:
    """Save language detection results to metadata registry."""
    output_file = METADATA_REGISTRY / f"{dataset_name}_language_enrichment.json"

    # Aggregate statistics
    lang_counts: dict[str, int] = defaultdict(int)
    script_counts: dict[str, int] = defaultdict(int)
    confidence_sum = 0.0
    detected_count = 0

    sample_results = []
    for image_id, result in results:
        if result.language != "und":
            lang_counts[result.language] += 1
            detected_count += 1
            confidence_sum += result.confidence
        if result.script:
            script_counts[result.script] += 1

        sample_results.append(
            {
                "image_id": str(image_id),
                "language": result.language,
                "script": result.script,
                "confidence": round(result.confidence, 3),
                "method": result.method,
            }
        )

    output = {
        "dataset": dataset_name,
        "enrichment_type": "openlid_detection",
        "total_samples": len(results),
        "detected_count": detected_count,
        "undetermined_count": len(results) - detected_count,
        "avg_confidence": round(confidence_sum / max(1, detected_count), 3),
        "language_distribution": dict(sorted(lang_counts.items(), key=lambda x: -x[1])),
        "script_distribution": dict(sorted(script_counts.items(), key=lambda x: -x[1])),
        "created_at": datetime.now(UTC).isoformat(),
        "method": "openlid_v2",
        "samples": sample_results[:1000],  # First 1000 for reference
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Saved {len(results)} results to {output_file}")


def list_datasets() -> None:
    """List all datasets with ground truth text."""
    print("\nDatasets with Ground Truth Text:")
    print("=" * 70)

    total_images = 0
    for name, config in sorted(
        DATASETS_WITH_GT_TEXT.items(), key=lambda x: -x[1].get("images", 0)
    ):
        images = config.get("images", 0)
        total_images += images
        fmt = config.get("format", "unknown")
        known = "✓" if config.get("known_language") else ""

        # Check if annotation file exists
        ann_file = config.get("annotation_file") or config.get("annotation_dir")
        exists = "✓" if ann_file and Path(ann_file).exists() else "✗"

        print(
            f"  {name:30} {images:>10,} images  [{fmt:20}] exists:{exists} known:{known}"
        )

    print(f"\nTotal: {len(DATASETS_WITH_GT_TEXT)} datasets, {total_images:,} images")

    # Docling OCR datasets
    print("\n\nDatasets with Docling OCR Extracted Text:")
    print("=" * 70)

    docling_total = 0
    for name, config in sorted(
        DOCLING_OCR_DATASETS.items(), key=lambda x: -x[1].get("images", 0)
    ):
        images = config.get("images", 0)
        docling_total += images
        fmt = config.get("format", "unknown")

        ann_dir = config.get("annotation_dir")
        ocr_dir = ann_dir / "ocr" if ann_dir else None
        exists = "✓" if ocr_dir and ocr_dir.exists() else "✗"

        print(f"  {name:30} {images:>10,} images  [{fmt:20}] exists:{exists}")

    print(f"\nTotal: {len(DOCLING_OCR_DATASETS)} datasets, {docling_total:,} images")
    print(
        f"\nGrand Total: {len(DATASETS_WITH_GT_TEXT) + len(DOCLING_OCR_DATASETS)} datasets, {total_images + docling_total:,} images"
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich datasets with OpenLID using ground truth text"
    )
    parser.add_argument("--dataset", type=str, help="Specific dataset to process")
    parser.add_argument("--all", action="store_true", help="Process all datasets")
    parser.add_argument(
        "--all-gt", action="store_true", help="Process all ground truth datasets only"
    )
    parser.add_argument(
        "--all-docling",
        action="store_true",
        help="Process all Docling OCR datasets only",
    )
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--dry-run", action="store_true", help="Don't save results")
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Progress batch size"
    )
    args = parser.parse_args()

    if args.list:
        list_datasets()
        return 0

    # Combine all datasets
    all_datasets = {**DATASETS_WITH_GT_TEXT, **DOCLING_OCR_DATASETS}

    if args.dataset:
        if args.dataset not in all_datasets:
            logger.error(f"Unknown dataset: {args.dataset}")
            logger.info(f"Available GT: {', '.join(DATASETS_WITH_GT_TEXT.keys())}")
            logger.info(f"Available Docling: {', '.join(DOCLING_OCR_DATASETS.keys())}")
            return 1
        datasets_to_process = [(args.dataset, all_datasets[args.dataset])]
    elif args.all:
        datasets_to_process = list(all_datasets.items())
    elif args.all_gt:
        datasets_to_process = list(DATASETS_WITH_GT_TEXT.items())
    elif args.all_docling:
        datasets_to_process = list(DOCLING_OCR_DATASETS.items())
    else:
        parser.print_help()
        return 1

    # Process datasets
    total_stats = {
        "total": 0,
        "processed": 0,
        "detected": 0,
        "undetermined": 0,
        "known_language": 0,
    }

    for dataset_name, config in datasets_to_process:
        logger.info("=" * 60)
        logger.info(f"Processing: {dataset_name}")

        stats = process_dataset(
            dataset_name=dataset_name,
            config=config,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )

        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

        logger.info(f"Dataset {dataset_name}: {stats}")

    # Final summary
    logger.info("=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info(f"Total texts: {total_stats['total']:,}")
    logger.info(f"Known language: {total_stats['known_language']:,}")
    logger.info(f"Detected: {total_stats['detected']:,}")
    logger.info(f"Undetermined: {total_stats['undetermined']:,}")

    return 0


if __name__ == "__main__":
    exit(main())
