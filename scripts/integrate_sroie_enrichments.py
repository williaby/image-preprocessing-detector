#!/usr/bin/env python3
"""Integrate all enrichment sources into sroie Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/integrate_tobacco800_enrichments.py

sroie specifics:
  - ICDAR 2019 Scanned Receipt OCR and Information Extraction
  - 973 camera/scanner-captured Malaysian receipts (626 train + 347 test)
  - FIN domain (100% retail receipts)
  - Primary English with some Chinese and Malay
  - Filenames overlap between train/test (both have X00000.jpg etc.)
    → Must use original_path (with split prefix) for unique identification
  - LLM/language enrichments are STALE (from old contaminated dataset) → SKIP
  - GT annotations available for all 973 images (JSON: quad coords + text)
  - v1 layout detections use non-standard labels (DocLayout-YOLO native)
  - Docling extracted batches only contain text_region class (OCR-oriented)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_sroie_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "sroie"
__l4_workstream__ = "WS3"
__l4_parser__ = "src/image_preprocessing_detector/annotation/parsers/layout/sroie.py"


import argparse
import json
import logging
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)
from l2_integration_utils import (
    compute_reliability_summary,
    compute_text_statistics,
    derive_content_flags,
    load_metadata,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ===================================================================
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "sroie"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "sroie_metadata.json"

# NOTE: LLM and language enrichments are STALE (from old contaminated dataset
# with 2,043 images and different IDs). They are intentionally NOT loaded.
# GT annotations are used instead for text content and language detection.
GT_ANNOTATIONS_DIR = Path("/mnt/e/image_detection/01_base_data/forms/sroie_icdar2019")
IMAGES_BASE_DIR = GT_ANNOTATIONS_DIR

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# --- KI-001 (variant): DocLayout-YOLO non-standard label taxonomy ----
APPLY_KI_001_LAYOUT_MAPPING = True

DOCLAYOUT_TO_DOCLAYNET: dict[str, str | None] = {
    "plain text": "Text",
    "title": "Title",
    "table": "Table",
    "figure": "Picture",
    "abandon": None,  # Drop - no DocLayNet equivalent
    "table_footnote": "Footnote",
    "table_caption": "Caption",
    "figure_caption": "Caption",
    "formula_caption": "Caption",
    "isolate_formula": "Formula",
}

# --- KI-005: Capture method from documentation -----------------------
# Mixed camera_smartphone + scanner_flatbed; default to camera_smartphone
# since majority are camera captures. VLM Phase 6 will refine.
KNOWN_CAPTURE_METHOD: str | None = None  # Preserve v1 per-sample values

# --- KI-008: script_family contains directionality ------------------
# v1 has "ltr" instead of "latin". Fixed by re-deriving from iso15924_script.

# --- KI-009: Language verification via GT text -----------------------
# Use langdetect on GT text instead of stale LLM enrichment.
APPLY_LANGDETECT = True

# ===================================================================
# Content flag class mappings (canonical layout -> content flags)
# ===================================================================


# ===================================================================
# Data loaders
# ===================================================================
def load_gt_annotations(
    gt_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Load GT annotations from SROIE JSON files.

    Indexes by "{split}/images/{filename}" to match original_path in metadata.
    Each GT record contains text_regions (with text and bbox_quad) and entities.

    Args:
        gt_dir: Root directory containing train/ and test/ subdirectories.

    Returns:
        Dict mapping original_path to GT annotation dict.
    """
    index: dict[str, dict[str, Any]] = {}

    for split in ("train", "test"):
        ann_dir = gt_dir / split / "annotations"
        if not ann_dir.exists():
            log.warning("GT annotations dir not found: %s", ann_dir)
            continue

        for json_file in sorted(ann_dir.glob("*.json")):
            with open(json_file, encoding="utf-8") as f:
                record: dict[str, Any] = json.load(f)

            # Key by the path format used in metadata original_path
            img_filename = json_file.stem + ".jpg"
            key = f"{split}/images/{img_filename}"
            record["_split"] = split
            record["_filename"] = img_filename
            index[key] = record

    log.info("  Indexed %d GT annotation records", len(index))
    return index


def extract_gt_text(gt_record: dict[str, Any]) -> str:
    """Extract full text from GT annotation record.

    Concatenates all text_region texts with newlines.

    Args:
        gt_record: Single GT annotation dict with text_regions.

    Returns:
        Concatenated text from all regions.
    """
    regions = gt_record.get("text_regions", [])
    texts = [r.get("text", "") for r in regions if r.get("text")]
    return "\n".join(texts)


def detect_language_simple(text: str) -> tuple[str, str, float]:
    """Detect language from text using character analysis.

    Simple heuristic for SROIE receipts: check CJK character ratio.
    Falls back to langdetect if available.

    Args:
        text: Text to analyze.

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence).
    """
    if not text or len(text.strip()) < 5:
        return ("en", "Latn", 0.5)

    # Count CJK characters
    cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    total_alpha = len(re.findall(r"[a-zA-Z]", text)) + cjk_count

    if total_alpha == 0:
        return ("en", "Latn", 0.5)

    cjk_ratio = cjk_count / total_alpha if total_alpha > 0 else 0

    # Try langdetect for more accuracy
    try:
        from langdetect import detect  # type: ignore[import-untyped]

        detected = detect(text)
        if detected in ("zh-cn", "zh-tw", "zh"):
            return ("zh", "Hant", 0.75)
        if detected == "ms":
            return ("ms", "Latn", 0.70)
        if detected == "en":
            return ("en", "Latn", 0.80)
        # Map other detected languages
        return (detected, "Latn", 0.65)
    except Exception:
        pass

    # Fallback to CJK ratio heuristic
    if cjk_ratio > 0.3:
        return ("zh", "Hant", 0.65)
    return ("en", "Latn", 0.70)


def standardize_class_name(class_name: str) -> str | None:
    """Convert DocLayout-YOLO class_name to DocLayNet PascalCase.

    Returns None for classes that should be dropped (e.g., "abandon").
    """
    if APPLY_KI_001_LAYOUT_MAPPING:
        return DOCLAYOUT_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def get_color_mode_from_image(image_path: Path) -> str:
    """Read image color mode using PIL.

    Args:
        image_path: Path to image file.

    Returns:
        Color mode string: "color", "grayscale", or "binarized".
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            mode = img.mode
            if mode in ("1",):
                return "binarized"
            if mode in ("L", "LA"):
                return "grayscale"
            return "color"
    except Exception:
        return "color"  # Default for JPEG receipts


def integrate_sample(
    sample: dict[str, Any],
    gt_index: dict[str, dict[str, Any]],
    images_base_dir: Path,
    color_mode_cache: dict[str, str],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Uses original_path for unique identification since filenames overlap
    between train and test splits.
    """
    original_path = sample["source"]["original_path"]
    filename = sample["source"]["original_filename"]
    split = sample["source"].get("split", "unknown")

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    gt_record = gt_index.get(original_path)

    data: dict[str, Any] = {}

    # SPLIT (from source metadata - train/test)
    data["split"] = split

    # CAPTURE METHOD (preserve v1 per-sample value from dataset_config)
    data["capture_method"] = v1_data.get("capture_method", "camera_smartphone")
    data["capture_confidence"] = v1_data.get("capture_confidence", 0.95)
    data["capture_detection_method"] = "dataset_config"

    # DOMAIN (100% FIN - retail receipts)
    data["domain_level1"] = "FIN"
    data["domain_confidence"] = 0.95
    data["domain_detection_method"] = "dataset_documentation"

    # LANGUAGE / SCRIPT (from GT text via langdetect or heuristic)
    if gt_record and APPLY_LANGDETECT:
        gt_text = extract_gt_text(gt_record)
        lang, script, lang_conf = detect_language_simple(gt_text)
        data["iso639_language"] = lang
        data["iso15924_script"] = script
        data["language_confidence"] = lang_conf
        data["text_scope_detection_method"] = "langdetect_gt_text"
    else:
        # Fallback to v1 values
        data["iso639_language"] = v1_data.get("iso639_language", "en")
        data["iso15924_script"] = v1_data.get("iso15924_script", "Latn")
        data["language_confidence"] = 0.70
        data["text_scope_detection_method"] = "base_metadata"

    # KI-008 fix: derive script_family from iso15924_script
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # v2.3.0: TEXT DIRECTION
    # All receipt scripts (English, Chinese, Malay) are horizontal LTR on receipts
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # LAYOUT DETECTIONS (standardize v1 non-standard labels)
    v1_layout = v1_data.get("layout_detections", [])
    standardized_layout: list[dict[str, Any]] = []
    dropped_count = 0
    for det in v1_layout:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        mapped = standardize_class_name(original_class)
        if mapped is None:
            dropped_count += 1
            continue
        new_det["class_name"] = mapped
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        new_det["source_schema"] = "doclayout_yolo"
        standardized_layout.append(new_det)

    data["layout_detections"] = standardized_layout
    data["layout_source"] = "doclayout_yolo_v1_standardized"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)
    if dropped_count > 0:
        data["layout_dropped_abandon"] = dropped_count

    # CONTENT FLAGS (from standardized layout)
    flags = derive_content_flags(standardized_layout)
    data["has_table"] = flags["has_table"]
    data["has_formula"] = flags["has_formula"]
    data["has_figure"] = flags["has_figure"]
    data["has_code"] = flags["has_code"]
    data["has_handwriting"] = False  # Thermal print receipts
    data["has_signature"] = False
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "doclayout_yolo_standardized"
    data["content_flags_confidence"] = 0.80

    data["handwriting_present"] = False

    # ORIENTATION (receipts are upright)
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.90
    data["orientation_detection_method"] = "dataset_documentation"

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "page"

    # IMAGE PROPERTIES COLOR MODE
    img_path = images_base_dir / original_path
    if original_path in color_mode_cache:
        data["image_properties_color_mode"] = color_mode_cache[original_path]
    elif img_path.exists():
        color_mode = get_color_mode_from_image(img_path)
        color_mode_cache[original_path] = color_mode
        data["image_properties_color_mode"] = color_mode
    else:
        # Fallback: JPEG receipts are almost always color
        data["image_properties_color_mode"] = "color"

    # RESOLUTION (preserve v1)
    for field in ("resolution_category", "resolution_pixels"):
        if field in v1_data:
            data[field] = v1_data[field]

    # TEXT CONTENT (from GT annotations)
    if gt_record:
        gt_text = extract_gt_text(gt_record)
        if gt_text.strip():
            data["text_has_content"] = True
            data["text_content"] = gt_text
            data["text_content_confidence"] = 0.95  # GT text is high quality
            data["text_content_source"] = "ground_truth_annotation"
            data["text_statistics"] = compute_text_statistics(gt_text)
        else:
            data["text_has_content"] = False
            data["text_content"] = ""
            data["text_content_confidence"] = 0.0
            data["text_content_source"] = "none"
            data["text_statistics"] = compute_text_statistics("")
    else:
        data["text_has_content"] = False
        data["text_content"] = ""
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

    # ADDITIONAL DERIVED FIELDS
    data["dataset_short_code"] = DATASET_NAME

    # RELIABILITY SUMMARY
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def run_integration(
    metadata: dict[str, Any],
    gt_index: dict[str, dict[str, Any]],
    images_base_dir: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "gt_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "capture_method_dist": Counter(),
        "content_type_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
        "layout_dropped_abandon_total": 0,
        "color_mode_dist": Counter(),
    }

    now = datetime.now(UTC).isoformat()
    color_mode_cache: dict[str, str] = {}

    for sample in metadata["samples"]:
        stats["total"] += 1
        original_path = sample["source"]["original_path"]

        integrated_data = integrate_sample(
            sample,
            gt_index,
            images_base_dir,
            color_mode_cache,
        )

        stats["integrated"] += 1
        if original_path in gt_index:
            stats["gt_matched"] += 1
        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["lang_method_dist"][
            integrated_data.get("text_scope_detection_method", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
        ] += 1
        stats["content_type_dist"][
            integrated_data.get("text_scope_content_type", "unknown")
        ] += 1
        stats["color_mode_dist"][
            integrated_data.get("image_properties_color_mode", "unknown")
        ] += 1

        if integrated_data.get("has_table"):
            stats["has_table_count"] += 1
        if integrated_data.get("has_formula"):
            stats["has_formula_count"] += 1
        if integrated_data.get("has_handwriting"):
            stats["has_handwriting_count"] += 1
        if integrated_data.get("has_figure"):
            stats["has_figure_count"] += 1
        stats["layout_dropped_abandon_total"] += integrated_data.get(
            "layout_dropped_abandon", 0
        )

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "GT text extraction + layout standardization + "
                    "v2.3.0 text_direction fields"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            versions = sample["enrichments"]["versions"]
            replaced = False
            for i, ver in enumerate(versions):
                if ver.get("version") == ENRICHMENT_VERSION_NUMBER:
                    versions[i] = new_version
                    replaced = True
                    break
            if not replaced:
                versions.append(new_version)
            sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER

    return stats


# ===================================================================
# Summary printer
# ===================================================================
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary with distributions."""
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"GT matched:           {stats['gt_matched']}")
    print(f"Has text content:     {stats['has_text_content_count']}")
    print(f"Abandon labels dropped: {stats['layout_dropped_abandon_total']}")
    print()

    print("Split distribution:")
    for split, count in stats["split_dist"].most_common():
        print(f"  {split:20s}: {count:5d}")
    print()

    print("Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {domain:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Language distribution:")
    for lang, count in stats["lang_dist"].most_common(15):
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {sf:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Language method distribution:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"  {method:30s}: {count:5d}")
    print()

    print("Capture method distribution:")
    for cm, count in stats["capture_method_dist"].most_common():
        print(f"  {cm:20s}: {count:5d}")
    print()

    print("Color mode distribution:")
    for cm, count in stats["color_mode_dist"].most_common():
        print(f"  {cm:20s}: {count:5d}")
    print()

    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print("=" * 60)


# ===================================================================
# CLI
# ===================================================================
def main() -> int:
    """Entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description=f"Integrate all enrichment sources into {DATASET_NAME} metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to dataset metadata JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--gt-annotations-dir",
        type=Path,
        default=GT_ANNOTATIONS_DIR,
        help="Path to GT annotations root dir (default: %(default)s)",
    )
    parser.add_argument(
        "--images-base-dir",
        type=Path,
        default=IMAGES_BASE_DIR,
        help="Path to images root dir for color mode detection (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report only, do not write output"
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    gt_index = load_gt_annotations(args.gt_annotations_dir)

    if not gt_index:
        log.error("No GT annotations loaded. Check --gt-annotations-dir path.")
        return 1

    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        gt_index=gt_index,
        images_base_dir=args.images_base_dir,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
