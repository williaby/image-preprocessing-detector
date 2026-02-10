#!/usr/bin/env python3
"""Enrich datasets with domain and metadata via OpenRouter LLM models.

This script processes datasets using free text-only LLM models (primary)
and low-cost vision models (fallback for image-only samples) to extract:
- Domain classification (DomainLevel1: TAX, LEG, FIN, TEC, SCI, ADM, MED, EDU, PER, UNK)
- Language/script detection (ISO 639 + ISO 15924)
- Content type classification
- Capture method, content flags, orientation (vision only)

Follows the enrichment pattern from enrich_language_from_gt.py.

Usage:
    # List available datasets
    python scripts/enrich_metadata_from_llm.py --list

    # Process single dataset (text-based, free)
    python scripts/enrich_metadata_from_llm.py --dataset doclaynet --limit 50

    # Dry run (no saves)
    python scripts/enrich_metadata_from_llm.py --dataset tablebank --limit 5 --dry-run

    # Resume (skip already-processed samples)
    python scripts/enrich_metadata_from_llm.py --dataset doclaynet --resume

    # Force vision mode
    python scripts/enrich_metadata_from_llm.py --dataset diqa-5000 --limit 10 --vision-only

    # Override models
    python scripts/enrich_metadata_from_llm.py --dataset doclaynet \\
        --primary-model "meta-llama/llama-3.3-70b-instruct:free" --limit 20

Environment:
    OPENROUTER_API_KEY: Required. Your OpenRouter API key.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
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
ANNOTATIONS_DIR = E_DRIVE_ROOT / "annotations"

# Datasets with ground truth text available (can use free text models)
# Maps dataset_name -> config dict with text extraction info
DATASETS_WITH_TEXT: dict[str, dict[str, Any]] = {
    # === Document layout with Docling OCR text ===
    "doclaynet": {
        "annotation_dir": E_DRIVE_ROOT / "metadata_registry/extracted/doclaynet",
        "format": "docling_ocr",
        "images": 80863,
        "image_dir": BASE_DATA / "documents/doclaynet/ground_truth/images",
        "text_source": "extracted",
    },
    # === Form annotations ===
    "funsd": {
        "annotation_dir": BASE_DATA / "forms/funsd/train/annotations",
        "format": "funsd_json",
        "images": 199,
        "image_dir": BASE_DATA / "forms/funsd/train/images",
    },
    # === Table datasets ===
    "pubtabnet": {
        "annotation_file": BASE_DATA / "tables/pubtabnet/pubtabnet/PubTabNet_2.0.0.jsonl",
        "format": "pubtabnet_jsonl",
        "images": 519030,
    },
    "fintabnet": {
        "annotation_dir": BASE_DATA / "tables/fintabnet/FinTabNet.c-PDF_Annotations",
        "format": "fintabnet_dir",
        "images": 97475,
    },
    "tablebank": {
        "annotation_file": BASE_DATA / "tables/tablebank/tablebank_word/Detection/train.json",
        "format": "tablebank_coco",
        "images": 163417,
    },
    # === Text detection with ground truth text ===
    "cocotext": {
        "annotation_file": BASE_DATA / "text_detection/cocotext/cocotext.v2.json",
        "format": "coco_text",
        "images": 63686,
    },
    "hiertext": {
        "annotation_file": BASE_DATA / "text_detection/hiertext/gt/train.jsonl",
        "format": "hiertext_json",
        "images": 11639,
    },
    "mlt19": {
        "annotation_dir": BASE_DATA / "language/mlt19/TrainGT/TrainGT",
        "format": "mlt19_gt",
        "images": 20000,
    },
    # === Receipt/form OCR ===
    "sroie": {
        "annotation_dir": BASE_DATA / "forms/sroie_voxel51_labeled/annotations",
        "format": "sroie_voxel51_json",
        "images": 973,
    },
    "invoices_kg": {
        "annotation_file": BASE_DATA / "forms/invoices_kaggle/train/annotations.json",
        "format": "invoices_kg_json",
        "images": 1414,
    },
    # === Financial ===
    "financebench": {
        "annotation_file": E_DRIVE_ROOT / "02_benchmark_only/financebench/data/financebench_open_source.jsonl",
        "format": "financebench_jsonl",
        "images": 150,
    },
    # === RVL-CDIP (with Docling OCR text) ===
    "rvl-cdip": {
        "annotation_dir": ANNOTATIONS_DIR / "rvl-cdip",
        "format": "docling_ocr",
        "images": 15903,
        "text_source": "extracted",
    },
    # === SmartDoc-QA (with Docling OCR text) ===
    "smartdoc-qa": {
        "annotation_dir": ANNOTATIONS_DIR / "smartdoc-qa",
        "format": "docling_ocr",
        "images": 2835,
        "text_source": "extracted",
    },
    # === OCR quality dataset ===
    "ocr-quality": {
        "annotation_file": BASE_DATA / "ocr_quality/OCR-Quality.json",
        "format": "ocr_quality_json",
        "images": 1000,
        "text_source": "extracted",
    },
    # === Handwriting datasets ===
    "muharaf": {
        "annotation_dir": BASE_DATA / "handwriting/muharaf/public",
        "format": "muharaf_paired_txt",
        "images": 24495,
    },
    "iam": {
        "annotation_file": BASE_DATA / "handwriting/iam_handwriting/ascii/lines.txt",
        "format": "iam_lines_txt",
        "images": 130212,
    },
    # === Document ID dataset ===
    "midv500": {
        "annotation_dir": BASE_DATA / "documents/midv500/midv500",
        "format": "midv500_gt_json",
        "images": 3612,
    },
}

# Datasets requiring vision (no text annotations available)
DATASETS_VISION_ONLY: dict[str, dict[str, Any]] = {
    "diqa-5000": {
        "image_dir": E_DRIVE_ROOT / "02_benchmark_only/diqa-5000",
        "images": 5500,
        "recursive": True,
        "pattern": "*_ori_*.*",
    },
    "realdae": {
        "image_dir": BASE_DATA / "camera_captured/realdae",
        "images": 600,
        "recursive": True,
        "pattern": "*_in.*",
    },
    "tobacco800": {
        "image_dir": BASE_DATA / "degraded/tobacco800/images",
        "images": 1290,
    },
    "dibco": {
        "image_dir": BASE_DATA / "degraded/historical_degraded/DIBCO_2009_2018",
        "images": 116,
        "recursive": True,
        "pattern": "*_in.*",
    },
    "jssoda": {
        "image_dir": BASE_DATA / "language/multilingual_scripts/jssoda",
        "images": 2000,
        "recursive": True,
    },
}


# =============================================================================
# Text Extraction (simplified, delegates to format-specific helpers)
# =============================================================================


def extract_text_samples(
    dataset_name: str,
    config: dict[str, Any],
    limit: int | None = None,
) -> list[tuple[str, str, str]]:
    """Extract text samples from a dataset's annotations.

    Args:
        dataset_name: Name of the dataset.
        config: Dataset configuration dict.
        limit: Maximum number of samples to extract.

    Returns:
        List of (image_id, text, text_source) tuples.
    """
    fmt = config.get("format", "")
    text_source = config.get("text_source", "ground_truth")
    samples: list[tuple[str, str, str]] = []

    if fmt == "doclaynet_coco" or fmt == "tablebank_coco":
        samples = _extract_coco_text(config["annotation_file"])
    elif fmt == "coco_text":
        samples = _extract_coco_text_field(config["annotation_file"])
    elif fmt == "funsd_json":
        samples = _extract_funsd_text(config["annotation_dir"])
    elif fmt == "pubtabnet_jsonl":
        samples = _extract_jsonl_html(config["annotation_file"], limit)
    elif fmt == "fintabnet_dir":
        samples = _extract_fintabnet_text(config["annotation_dir"])
    elif fmt == "docling_ocr":
        samples = _extract_docling_ocr(config["annotation_dir"])
        text_source = "extracted"
    elif fmt == "hiertext_json":
        samples = _extract_hiertext(config["annotation_file"])
    elif fmt == "mlt19_gt":
        samples = _extract_mlt19_gt(config["annotation_dir"])
    elif fmt == "sroie_voxel51_json":
        samples = _extract_sroie_text(config["annotation_dir"])
    elif fmt == "invoices_kg_json":
        samples = _extract_invoices_kg(config["annotation_file"])
    elif fmt == "financebench_jsonl":
        samples = _extract_financebench(config["annotation_file"])
    elif fmt == "ocr_quality_json":
        samples = _extract_ocr_quality(config["annotation_file"])
        text_source = "extracted"
    elif fmt == "muharaf_paired_txt":
        samples = _extract_muharaf(config["annotation_dir"])
    elif fmt == "iam_lines_txt":
        samples = _extract_iam_lines(config["annotation_file"])
    elif fmt == "midv500_gt_json":
        samples = _extract_midv500(config["annotation_dir"])
    else:
        logger.warning(f"Unsupported text format: {fmt} for {dataset_name}")
        return []

    # Apply text_source to all samples
    samples = [(img_id, text, text_source) for img_id, text, _ in samples]

    if limit:
        samples = samples[:limit]

    logger.info(f"Extracted {len(samples)} text samples from {dataset_name}")
    return samples


def _extract_coco_text(annotation_file: Path) -> list[tuple[str, str, str]]:
    """Extract text from COCO-format annotations by concatenating per-image."""
    if not annotation_file.exists():
        logger.warning(f"Annotation file not found: {annotation_file}")
        return []

    with open(annotation_file) as fh:
        data = json.load(fh)

    # Build image_id -> filename mapping
    id_to_file: dict[int, str] = {}
    for img in data.get("images", []):
        id_to_file[img["id"]] = img.get("file_name", str(img["id"]))

    # Concatenate annotation text per image
    image_texts: dict[str, list[str]] = {}
    for ann in data.get("annotations", []):
        img_id = ann.get("image_id")
        text = ann.get("text", "") or ann.get("caption", "")
        if text and img_id in id_to_file:
            fname = id_to_file[img_id]
            if fname not in image_texts:
                image_texts[fname] = []
            image_texts[fname].append(str(text))

    return [
        (img_id, " ".join(texts), "ground_truth")
        for img_id, texts in image_texts.items()
        if texts
    ]


def _extract_coco_text_field(annotation_file: Path) -> list[tuple[str, str, str]]:
    """Extract text from COCO annotations with utf8_string field."""
    if not annotation_file.exists():
        return []

    with open(annotation_file) as fh:
        data = json.load(fh)

    image_texts: dict[str, list[str]] = {}
    for ann_id, ann in data.get("anns", data.get("annotations", {})).items():
        text = ann.get("utf8_string", "")
        img_id = str(ann.get("image_id", ann_id))
        if text:
            if img_id not in image_texts:
                image_texts[img_id] = []
            image_texts[img_id].append(text)

    return [
        (img_id, " ".join(texts), "ground_truth")
        for img_id, texts in image_texts.items()
        if texts
    ]


def _extract_funsd_text(annotation_dir: Path) -> list[tuple[str, str, str]]:
    """Extract text from FUNSD-format JSON annotations."""
    if not annotation_dir.exists():
        return []

    samples = []
    for json_file in sorted(annotation_dir.glob("*.json")):
        with open(json_file) as fh:
            data = json.load(fh)
        texts = []
        for item in data.get("form", []):
            text = item.get("text", "")
            if text:
                texts.append(text)
        if texts:
            img_id = json_file.stem
            samples.append((img_id, " ".join(texts), "ground_truth"))
    return samples


def _extract_jsonl_html(
    annotation_file: Path,
    limit: int | None = None,
) -> list[tuple[str, str, str]]:
    """Extract text from PubTabNet JSONL (strip HTML, use text content)."""
    if not annotation_file.exists():
        return []

    import re

    samples = []
    with open(annotation_file) as fh:
        for i, line in enumerate(fh):
            if limit and i >= limit:
                break
            try:
                entry = json.loads(line)
                html = entry.get("html", {}).get("structure", {}).get("tokens", [])
                # Simple HTML stripping
                text = " ".join(html)
                text = re.sub(r"<[^>]+>", " ", text).strip()
                if text and len(text) > 20:
                    img_id = entry.get("filename", str(i))
                    samples.append((img_id, text[:4000], "ground_truth"))
            except json.JSONDecodeError:
                continue
    return samples


def _extract_fintabnet_text(annotation_dir: Path) -> list[tuple[str, str, str]]:
    """Extract text from FinTabNet PDF annotation directory."""
    if not annotation_dir.exists():
        return []

    import re

    samples = []
    for json_file in sorted(annotation_dir.glob("**/*.json"))[:5000]:
        try:
            with open(json_file) as fh:
                data = json.load(fh)
            texts = []
            for table in data if isinstance(data, list) else [data]:
                html = table.get("html", "")
                text = re.sub(r"<[^>]+>", " ", str(html)).strip()
                if text:
                    texts.append(text)
            if texts:
                img_id = json_file.stem
                samples.append((img_id, " ".join(texts)[:4000], "ground_truth"))
        except (json.JSONDecodeError, KeyError):
            continue
    return samples


def _extract_docling_ocr(annotation_dir: Path) -> list[tuple[str, str, str]]:
    """Extract text from Docling OCR JSONL files."""
    ocr_dir = annotation_dir / "ocr"
    if not ocr_dir.exists():
        ocr_dir = annotation_dir
    if not ocr_dir.exists():
        return []

    samples = []
    for jsonl_file in sorted(ocr_dir.glob("*.jsonl")):
        with open(jsonl_file) as fh:
            for line in fh:
                try:
                    entry = json.loads(line)
                    text = entry.get("text", "")
                    img_id = entry.get("image_id", entry.get("filename", ""))
                    if not img_id:
                        source = entry.get("source", "")
                        if source:
                            img_id = Path(source).name
                    if text and img_id:
                        samples.append((str(img_id), text[:4000], "extracted"))
                except json.JSONDecodeError:
                    continue
    return samples


def _extract_hiertext(annotation_file: Path) -> list[tuple[str, str, str]]:
    """Extract text from HierText JSON (single large JSON with annotations)."""
    if not annotation_file.exists():
        return []

    with open(annotation_file) as fh:
        data = json.load(fh)

    samples = []
    for ann in data.get("annotations", []):
        image_id = ann.get("image_id", "")
        texts: list[str] = []
        for para in ann.get("paragraphs", []):
            for line in para.get("lines", []):
                line_text = line.get("text", "")
                if line_text:
                    texts.append(line_text)
        if texts:
            samples.append((str(image_id), " ".join(texts)[:4000], "ground_truth"))
    return samples


def _extract_mlt19_gt(annotation_dir: Path) -> list[tuple[str, str, str]]:
    """Extract text from MLT19 ground truth files (CSV-like per image)."""
    if not annotation_dir.exists():
        return []

    samples = []
    for txt_file in sorted(annotation_dir.glob("*.txt")):
        texts: list[str] = []
        with open(txt_file, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.strip().split(",")
                if len(parts) >= 10:
                    # Format: x1,y1,x2,y2,x3,y3,x4,y4,script,text
                    text = ",".join(parts[9:])  # text may contain commas
                    if text and text != "###":
                        texts.append(text)
        if texts:
            # Image ID matches txt filename: tr_img_00001.txt -> tr_img_00001
            samples.append((txt_file.stem, " ".join(texts)[:4000], "ground_truth"))
    return samples


def _extract_sroie_text(annotation_dir: Path) -> list[tuple[str, str, str]]:
    """Extract text from SROIE VoxelFiftyone JSON annotations."""
    if not annotation_dir.exists():
        return []

    samples = []
    for json_file in sorted(annotation_dir.glob("*.json")):
        try:
            with open(json_file) as fh:
                data = json.load(fh)
            texts: list[str] = []
            # Top-level fields contain key receipt information
            for field in ("company", "date", "address", "total"):
                val = data.get(field, "")
                if val:
                    texts.append(f"{field}: {val}")
            # text_detections contain OCR text
            for det in data.get("text_detections", []):
                label = det.get("label", "")
                if label:
                    texts.append(label)
            if texts:
                img_id = data.get("filename", json_file.stem)
                img_id = Path(img_id).stem  # strip .jpg
                samples.append((img_id, " ".join(texts)[:4000], "ground_truth"))
        except (json.JSONDecodeError, KeyError):
            continue
    return samples


def _extract_invoices_kg(annotation_file: Path) -> list[tuple[str, str, str]]:
    """Extract text from Invoices Kaggle annotations JSON."""
    if not annotation_file.exists():
        return []

    with open(annotation_file) as fh:
        data = json.load(fh)

    samples = []
    for entry in data:
        img_id = entry.get("filename", "")
        # Prefer ocred_text, fallback to json_data
        text = entry.get("ocred_text", "")
        if not text:
            text = entry.get("json_data", "")
        if text and img_id:
            samples.append((Path(img_id).stem, str(text)[:4000], "ground_truth"))
    return samples


def _extract_financebench(annotation_file: Path) -> list[tuple[str, str, str]]:
    """Extract text from FinanceBench JSONL (evidence text per Q&A entry)."""
    if not annotation_file.exists():
        return []

    samples = []
    with open(annotation_file) as fh:
        for line in fh:
            try:
                entry = json.loads(line)
                # Use evidence text for domain classification
                evidence_texts: list[str] = []
                for ev in entry.get("evidence", []):
                    ev_text = ev.get("evidence_text", "")
                    if ev_text:
                        evidence_texts.append(ev_text)
                text = " ".join(evidence_texts)
                if not text:
                    # Fallback to question + answer
                    text = f"{entry.get('question', '')} {entry.get('answer', '')}"
                doc_id = entry.get("financebench_id", entry.get("doc_name", ""))
                if text.strip() and doc_id:
                    samples.append((doc_id, text[:4000], "ground_truth"))
            except json.JSONDecodeError:
                continue
    return samples


def _extract_ocr_quality(annotation_file: Path) -> list[tuple[str, str, str]]:
    """Extract OCR text from OCR-Quality JSON dataset."""
    if not annotation_file.exists():
        return []

    with open(annotation_file) as fh:
        data = json.load(fh)

    samples = []
    for entry in data:
        text = entry.get("ocr_text", "")
        img_path = entry.get("image_path", "")
        idx = entry.get("index", "")
        img_id = Path(img_path).stem if img_path else str(idx)
        if text and img_id:
            samples.append((img_id, str(text)[:4000], "extracted"))
    return samples


def _extract_muharaf(annotation_dir: Path) -> list[tuple[str, str, str]]:
    """Extract Arabic text from Muharaf paired .txt files."""
    if not annotation_dir.exists():
        return []

    samples = []
    for txt_file in sorted(annotation_dir.glob("*.txt")):
        # Check paired image exists
        img_candidates = [
            txt_file.with_suffix(".png"),
            txt_file.with_suffix(".jpg"),
        ]
        has_image = any(c.exists() for c in img_candidates)
        if not has_image:
            continue
        text = txt_file.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            samples.append((txt_file.stem, text[:4000], "ground_truth"))
    return samples


def _extract_iam_lines(annotation_file: Path) -> list[tuple[str, str, str]]:
    """Extract text from IAM lines.txt (pipe-separated transcriptions).

    Groups lines by form ID to produce one text sample per form.
    Format: line_id ok graylevel components x y w h word1|word2|...
    """
    if not annotation_file.exists():
        return []

    form_texts: dict[str, list[str]] = {}
    with open(annotation_file, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split(" ", 8)
            if len(parts) < 9:
                continue
            line_id = parts[0]  # e.g., a01-000u-00
            # Form ID is first two segments: a01-000u
            form_id = "-".join(line_id.split("-")[:2])
            transcription = parts[8].replace("|", " ")
            if form_id not in form_texts:
                form_texts[form_id] = []
            form_texts[form_id].append(transcription)

    return [
        (form_id, " ".join(texts)[:4000], "ground_truth")
        for form_id, texts in form_texts.items()
        if texts
    ]


def _extract_midv500(annotation_dir: Path) -> list[tuple[str, str, str]]:
    """Extract text from MIDV-500 ground truth JSON files.

    Each document type has a ground_truth/ dir with JSON files containing
    fieldNN -> {quad, value} entries.
    """
    if not annotation_dir.exists():
        return []

    import glob

    samples = []
    gt_files = sorted(glob.glob(str(annotation_dir / "*/ground_truth/*.json")))
    for gt_file in gt_files:
        try:
            with open(gt_file) as fh:
                data = json.load(fh)
            texts: list[str] = []
            for key, val in data.items():
                if isinstance(val, dict) and "value" in val:
                    texts.append(str(val["value"]))
            if texts:
                img_id = Path(gt_file).stem
                samples.append((img_id, " ".join(texts)[:4000], "ground_truth"))
        except (json.JSONDecodeError, KeyError):
            continue
    return samples


def load_image_paths(
    dataset_name: str,
    config: dict[str, Any],
    limit: int | None = None,
) -> list[tuple[str, Path]]:
    """Load image paths for vision-only classification.

    Args:
        dataset_name: Name of the dataset.
        config: Dataset configuration dict.
        limit: Maximum number of images.

    Returns:
        List of (image_id, image_path) tuples.
    """
    image_dir = config.get("image_dir")
    if not image_dir or not Path(image_dir).exists():
        logger.warning(f"Image directory not found for {dataset_name}: {image_dir}")
        return []

    image_dir = Path(image_dir)
    extensions = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
    recursive = config.get("recursive", False)
    pattern = config.get("pattern", "")

    if pattern and recursive:
        paths = sorted(image_dir.rglob(pattern))
    elif pattern:
        paths = sorted(image_dir.glob(pattern))
    elif recursive:
        paths = sorted(
            p for p in image_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in extensions
        )
    else:
        paths = sorted(
            p for p in image_dir.iterdir()
            if p.suffix.lower() in extensions
        )

    if limit:
        paths = paths[:limit]

    return [(p.stem, p) for p in paths]


# =============================================================================
# Output
# =============================================================================


def save_enrichment(
    dataset_name: str,
    results: list[tuple[str, Any]],
    stats: dict[str, Any],
    output_dir: Path,
) -> Path:
    """Save enrichment results to JSON.

    Args:
        dataset_name: Name of the dataset.
        results: List of (image_id, EnrichmentResult) tuples.
        stats: Pipeline statistics.
        output_dir: Directory to save output.

    Returns:
        Path to saved JSON file.
    """
    domain_counter: Counter[str] = Counter()
    language_counter: Counter[str] = Counter()
    mode_counter: Counter[str] = Counter()

    samples = []
    for image_id, result in results:
        result_dict = asdict(result)
        result_dict["image_id"] = image_id
        samples.append(result_dict)

        domain_counter[result.domain_level1] += 1
        if result.iso639_language:
            language_counter[result.iso639_language] += 1
        mode_counter[result.input_mode] += 1

    output = {
        "dataset": dataset_name,
        "enrichment_type": "llm_metadata_enrichment",
        "pipeline_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_samples": len(results),
        "classified_count": sum(1 for _, r in results if r.domain_level1 != "UNK"),
        "skipped_count": 0,
        "avg_domain_confidence": (
            sum(r.domain_confidence for _, r in results) / len(results)
            if results else 0.0
        ),
        "escalation_rate": stats.get("escalation_rate", 0.0),
        "domain_distribution": dict(domain_counter.most_common()),
        "language_distribution": dict(language_counter.most_common()),
        "input_mode_distribution": dict(mode_counter),
        "model_usage": stats.get("model_usage", {}),
        "total_tokens": stats.get("total_tokens", 0),
        "samples": samples,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{dataset_name}_llm_enrichment.json"
    with open(output_path, "w") as fh:
        json.dump(output, fh, indent=2, default=str)

    logger.info(f"Saved enrichment to {output_path}")
    return output_path


def load_existing_ids(dataset_name: str, output_dir: Path) -> set[str]:
    """Load already-processed image IDs for resume support.

    Args:
        dataset_name: Name of the dataset.
        output_dir: Directory containing existing enrichment files.

    Returns:
        Set of already-processed image_ids.
    """
    output_path = output_dir / f"{dataset_name}_llm_enrichment.json"
    if not output_path.exists():
        return set()

    try:
        with open(output_path) as fh:
            data = json.load(fh)
        return {s["image_id"] for s in data.get("samples", [])}
    except (json.JSONDecodeError, KeyError):
        return set()


# =============================================================================
# Main Pipeline
# =============================================================================


def process_dataset(
    dataset_name: str,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    """Process a single dataset for domain enrichment.

    Args:
        dataset_name: Name of the dataset.
        config: Dataset configuration dict.
        args: CLI arguments.
    """
    from image_preprocessing_detector.labeling.domain.classifier import (
        MetadataEnricher,
        SampleInput,
    )
    from image_preprocessing_detector.labeling.domain.config import (
        DomainModelConfig,
        DomainPipelineConfig,
    )

    # Build pipeline config with optional overrides
    pipeline_kwargs: dict[str, Any] = {}
    if args.primary_model:
        pipeline_kwargs["primary_text_model"] = DomainModelConfig(
            model_id=args.primary_model, role="primary_text"
        )
    if args.vision_model:
        pipeline_kwargs["primary_vision_model"] = DomainModelConfig(
            model_id=args.vision_model, role="primary_vision", supports_vision=True
        )

    pipeline_config = DomainPipelineConfig(**pipeline_kwargs)
    enricher = MetadataEnricher(pipeline_config)

    # Resume support
    skip_ids: set[str] = set()
    if args.resume:
        skip_ids = load_existing_ids(dataset_name, METADATA_REGISTRY)
        if skip_ids:
            logger.info(f"Resuming: skipping {len(skip_ids)} already-processed samples")

    # Build sample inputs
    samples: list[SampleInput] = []
    is_vision = args.vision_only or dataset_name in DATASETS_VISION_ONLY

    if not is_vision:
        # Text-based classification
        text_samples = extract_text_samples(dataset_name, config, args.limit)
        for image_id, text, text_source in text_samples:
            if image_id not in skip_ids:
                samples.append(SampleInput(
                    image_id=image_id,
                    text=text,
                    text_source=text_source,
                ))
    else:
        # Vision-based classification
        vision_config = DATASETS_VISION_ONLY.get(dataset_name, config)
        image_paths = load_image_paths(dataset_name, vision_config, args.limit)
        for image_id, image_path in image_paths:
            if image_id not in skip_ids:
                samples.append(SampleInput(
                    image_id=image_id,
                    image_path=image_path,
                ))

    if not samples:
        logger.warning(f"No samples to process for {dataset_name}")
        return

    logger.info(
        f"Processing {len(samples)} samples from {dataset_name} "
        f"(mode: {'vision' if is_vision else 'text'})"
    )

    if args.dry_run:
        logger.info("[DRY RUN] Would process samples. Showing first 3:")
        for sample in samples[:3]:
            text_preview = (sample.text[:100] + "...") if sample.text else "N/A"
            logger.info(f"  {sample.image_id}: text={text_preview}")
        return

    # Process with progress bar
    results: list[tuple[str, Any]] = []
    with tqdm(total=len(samples), desc=dataset_name) as pbar:
        for sample in samples:
            result = enricher.enrich_sample(
                text=sample.text,
                image_path=sample.image_path,
                text_source=sample.text_source,
            )
            results.append((sample.image_id, result))
            pbar.update(1)
            pbar.set_postfix(
                domain=result.domain_level1,
                conf=f"{result.domain_confidence:.2f}",
            )

    # Save results
    stats = enricher.get_stats()
    output_path = save_enrichment(dataset_name, results, stats, METADATA_REGISTRY)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Dataset: {dataset_name}")
    print(f"Samples processed: {len(results)}")
    print(f"Output: {output_path}")
    print(f"Total tokens: {stats.get('total_tokens', 0):,}")
    print(f"Escalation rate: {stats.get('escalation_rate', 0):.1%}")
    print(f"Errors: {stats.get('errors', 0)}")

    # Domain distribution
    domain_dist = Counter(r.domain_level1 for _, r in results)
    print(f"\nDomain Distribution:")
    for domain, count in domain_dist.most_common():
        pct = count / len(results) * 100
        print(f"  {domain}: {count} ({pct:.1f}%)")

    # Language distribution (top 5)
    lang_dist = Counter(
        r.iso639_language for _, r in results if r.iso639_language
    )
    if lang_dist:
        print(f"\nTop Languages:")
        for lang, count in lang_dist.most_common(5):
            print(f"  {lang}: {count}")

    print(f"{'='*60}\n")


def list_datasets() -> None:
    """Print available datasets."""
    print("\n=== Datasets with Text (free text models) ===")
    for name, config in sorted(DATASETS_WITH_TEXT.items()):
        source = config.get("text_source", "ground_truth")
        print(f"  {name:<25} {config['images']:>8} images  [{source}]")

    print("\n=== Datasets (vision-only, paid models) ===")
    for name, config in sorted(DATASETS_VISION_ONLY.items()):
        print(f"  {name:<25} {config['images']:>8} images")

    total = sum(c["images"] for c in DATASETS_WITH_TEXT.values())
    total += sum(c["images"] for c in DATASETS_VISION_ONLY.values())
    print(f"\nTotal: {len(DATASETS_WITH_TEXT) + len(DATASETS_VISION_ONLY)} datasets, {total:,} images")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich datasets with domain and metadata via OpenRouter LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset", type=str, help="Dataset name to process")
    parser.add_argument("--all", action="store_true", help="Process all datasets")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--limit", type=int, help="Max samples to process")
    parser.add_argument("--resume", action="store_true", help="Skip already-processed samples")
    parser.add_argument("--primary-model", type=str, help="Override primary text model")
    parser.add_argument("--vision-model", type=str, help="Override vision model")
    parser.add_argument("--text-only", action="store_true", help="Skip vision-only datasets")
    parser.add_argument("--vision-only", action="store_true", help="Force vision mode")

    args = parser.parse_args()

    if args.list:
        list_datasets()
        return

    if not args.dataset and not args.all:
        parser.print_help()
        sys.exit(1)

    # Determine datasets to process
    datasets: dict[str, dict[str, Any]] = {}
    if args.dataset:
        if args.dataset in DATASETS_WITH_TEXT:
            datasets[args.dataset] = DATASETS_WITH_TEXT[args.dataset]
        elif args.dataset in DATASETS_VISION_ONLY:
            datasets[args.dataset] = DATASETS_VISION_ONLY[args.dataset]
        else:
            logger.error(f"Unknown dataset: {args.dataset}")
            logger.info("Use --list to see available datasets")
            sys.exit(1)
    elif args.all:
        datasets.update(DATASETS_WITH_TEXT)
        if not args.text_only:
            datasets.update(DATASETS_VISION_ONLY)

    for name, config in datasets.items():
        try:
            process_dataset(name, config, args)
        except Exception as exc:
            logger.error(f"Failed to process {name}: {exc}")
            if not args.all:
                raise


if __name__ == "__main__":
    main()
