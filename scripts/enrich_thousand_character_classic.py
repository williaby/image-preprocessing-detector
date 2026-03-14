#!/usr/bin/env python3
"""Generate Layer 2 enrichment metadata + extended sidecar for the
Thousand Character Classic dataset.

Two-pass enrichment:
  Pass 1 — Catalog-derived fields (high confidence, tier_0_exact / tier_1_annotation)
  Pass 2 — Image-derived fields (Pillow measurements, tier_0_exact)

Output:
  - L2 records: metadata_registry/json/thousand-character-classic/{sample_id}.json
  - Extended sidecar: metadata_registry/thousand_character_classic_extended.jsonl

Usage:
    uv run python scripts/enrich_thousand_character_classic.py enrich
    uv run python scripts/enrich_thousand_character_classic.py validate
    uv run python scripts/enrich_thousand_character_classic.py stats

Requires:
    Pillow>=10.0.0   (already in base deps)
    PyYAML>=6.0      (already in base deps)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CATALOG_PATH = _PROJECT_ROOT / "config" / "thousand_character_classic_catalog.yaml"
_TEXT_PATH = _PROJECT_ROOT / "config" / "thousand_character_classic_text.yaml"
_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "thousand_character_classic_registry.jsonl"
)
_L2_OUTPUT_DIR = (
    _PROJECT_ROOT / "metadata_registry" / "json" / "thousand-character-classic"
)
_SIDECAR_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "thousand_character_classic_extended.jsonl"
)
_DEFAULT_IMAGE_DIR = Path(
    "/mnt/e/image_detection/01_base_data/calligraphy/thousand-character-classic"
)
_LOCAL_IMAGE_DIR = _PROJECT_ROOT / "data" / "thousand-character-classic"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Script style → legibility mapping
# ---------------------------------------------------------------------------

_LEGIBILITY_MAP: dict[str, tuple[str, float]] = {
    "kaishu": ("GOOD", 0.75),
    "xiaokai": ("GOOD", 0.80),
    "xingkai": ("GOOD", 0.70),
    "haeseo": ("GOOD", 0.75),
    "lishu": ("GOOD", 0.70),
    "xingshu": ("FAIR", 0.55),
    "xingcao": ("FAIR", 0.45),
    "zhangcao": ("FAIR", 0.45),
    "caoshu": ("FAIR", 0.40),
    "choseo": ("FAIR", 0.40),
    "kuangcao": ("POOR", 0.25),
    "zhuanshu": ("POOR", 0.30),  # Archaic script, hard to read
    "mixed": ("FAIR", 0.50),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_catalog() -> dict[int, dict[str, Any]]:
    with _CATALOG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _load_text() -> dict[str, Any]:
    with _TEXT_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _load_registry() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if _REGISTRY_PATH.exists():
        with _REGISTRY_PATH.open("r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    return entries


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_image_props(image_path: Path) -> dict[str, Any]:
    """Extract image properties via Pillow."""
    from PIL import Image

    props: dict[str, Any] = {}
    try:
        with Image.open(image_path) as img:
            props["width"] = img.width
            props["height"] = img.height
            props["color_mode"] = img.mode  # RGB, L, RGBA, etc.

            # Try to get DPI from EXIF or image info
            dpi_info = img.info.get("dpi")
            if dpi_info and isinstance(dpi_info, tuple) and dpi_info[0] > 0:
                props["dpi"] = int(dpi_info[0])
            else:
                props["dpi"] = None
    except Exception as exc:
        logger.warning("Failed to read image %s: %s", image_path, exc)
    return props


def _dpi_category(dpi: int | None) -> str:
    if dpi is None:
        return "medium_150-299"  # Conservative default for web downloads
    if dpi < 150:
        return "low_<150"
    if dpi < 300:
        return "medium_150-299"
    if dpi == 300:
        return "standard_300"
    return "high_>300"


def _resolution_tier(width: int, height: int) -> str:
    """Classify image resolution into training-relevant tiers.

    Thresholds based on pixel area (width * height):
      very_high: >= 12 MP (4000x3000)  — full-res museum scans
      high:      >= 3 MP  (2000x1500)  — standard scans
      medium:    >= 750 K  (1000x750)  — web-resolution
      low:       < 750 K              — thumbnails / previews
    """
    area = width * height
    if area >= 12_000_000:
        return "very_high"
    if area >= 3_000_000:
        return "high"
    if area >= 750_000:
        return "medium"
    return "low"


def _build_l2_record(
    entry: dict[str, Any],
    catalog_entry: dict[str, Any] | None,
    text_data: dict[str, Any],
    image_props: dict[str, Any],
) -> dict[str, Any]:
    """Build a complete L2 enrichment record (v2 schema)."""
    sample_id = entry["sample_id"]
    now = _now_iso()

    # Determine fields from catalog (or defaults)
    cat = catalog_entry or {}
    lang_code = cat.get("language_code", "zh")
    script_code = cat.get("script_code", "Hant")
    content_type = cat.get("content_type", "handwritten")
    text_dir = cat.get("text_direction", "ttb")
    is_handwritten = content_type == "handwritten"
    script_style = cat.get("script_style", "mixed")
    writing_tradition = cat.get("writing_tradition", "chinese")

    # BCP 47 tag
    bcp47 = lang_code
    if script_code:
        bcp47 = f"{lang_code}-{script_code}"

    # Legibility from script style
    legibility_label, legibility_score = _LEGIBILITY_MAP.get(
        script_style, ("FAIR", 0.50)
    )

    # Full text content
    full_text_zh = text_data.get("full_text_zh", "")

    # Image dimensions
    width = image_props.get("width", 0)
    height = image_props.get("height", 0)
    dpi = image_props.get("dpi")
    raw_mode = image_props.get("color_mode", "RGB")
    # Map Pillow mode to schema enum: color|grayscale|binarized|null
    _mode_map = {
        "RGB": "color",
        "RGBA": "color",
        "L": "grayscale",
        "1": "binarized",
        "P": "color",
    }
    color_mode = _mode_map.get(raw_mode, "color")

    record: dict[str, Any] = {
        "sample_id": sample_id,
        "enrichment_version": 2,
        "schema_version": "2.4.0",
        "created_at": now,
        "created_by": "enrich_thousand_character_classic.py_v1.0.0",
        "method": "tier_1_annotation",
        "description": _build_description(cat),
        "provenance": {
            "git_sha": None,
            "script_version": "1.0.0",
            "model_checkpoint": None,
            "config_hash": None,
        },
        "data": {
            "capture_method": {
                "method": "scanner_flatbed",
                "confidence": 0.8,
                "provenance_tier": "tier_3_heuristic",
                "is_soft_label": True,
                "detection_method": "catalog_institution_heuristic",
            },
            "resolution": {
                "dpi": dpi,
                "category": _dpi_category(dpi),
                "pixels": [width, height],
                "confidence": 1.0 if dpi else 0.5,
                "provenance_tier": "tier_0_exact" if dpi else "tier_3_heuristic",
                "is_soft_label": dpi is None,
                "detection_method": "pillow_exif" if dpi else "dimension_heuristic",
            },
            "domain": {
                "level1": "EDU",
                "level2": "calligraphy",
                "level3": None,
                "confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata",
            },
            "structure": {
                "text_density": "dense",
                "layout_type": "single_column",
                "element_types": ["Text"],
                "confidence": 0.85,
                "provenance_tier": "tier_3_heuristic",
                "is_soft_label": True,
                "detection_method": "catalog_heuristic",
                "text_directions_present": [text_dir],
            },
            "quality": {
                "overall_score": None,  # Requires IQA model inference
                "degradations": [],
                "confidence": None,
                "provenance_tier": "tier_3_heuristic",
                "is_soft_label": True,
                "detection_method": "pending_classical_iqa",
            },
            "language": {
                "language_code": lang_code,
                "script_code": script_code,
                "bcp47_tag": bcp47,
                "script_family": "cjk",
                "confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata",
                "text_direction": text_dir,
                "is_rtl": False,
                "is_primary": True,
            },
            "text_scope": {
                "scope": "document",
                "content_type": content_type,
                "density": "dense",
                "estimated_chars": 1000,
                "estimated_words": 250,
                "confidence": 0.9,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "known_literary_text",
            },
            "content_flags": {
                "has_table": False,
                "table_confidence": 1.0,
                "has_formula": False,
                "formula_confidence": 1.0,
                "has_handwriting": is_handwritten,
                "handwriting_confidence": 1.0,
                "has_signature": False,
                "signature_confidence": 0.7,
                "has_figure": False,
                "figure_confidence": 0.8,
                "has_code": False,
                "code_confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata",
            },
            "text_content": {
                "full_text": full_text_zh,
                "source_type": "ground_truth",
                "language_hint": "zh",
                "is_complete": True,
                "confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
            },
            "text_statistics": {
                "character_count": 1000,
                "character_count_no_spaces": 1000,
                "word_count": 250,
                "sentence_count": 250,
                "line_count": 250,
                "avg_word_length": 4.0,
                "text_source": "ground_truth",
                "computation_method": "known_literary_text",
                "inherited_confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
            },
            "handwriting_assessment": {
                "presence": "DOMINANT" if is_handwritten else "NONE",
                "presence_score": 0.95 if is_handwritten else 0.0,
                "presence_confidence": 1.0,
                "legibility": legibility_label if is_handwritten else "NOT_APPLICABLE",
                "legibility_score": legibility_score if is_handwritten else 0.0,
                "legibility_confidence": 0.7,
                "content_type": "prose",
                "content_type_confidence": 1.0,
                "provenance_tier": "tier_1_annotation",
                "is_soft_label": False,
                "detection_method": "ground_truth",
            },
            "geometric": {
                "orientation_class": 0,
                "orientation_confidence": 0.8,
                "orientation_corrected": False,
                "orientation_detection_method": "format_type_heuristic",
                "skew_angle_degrees": None,
                "skew_confidence": None,
                "skew_detection_method": None,
                "confidence": 0.8,
                "provenance_tier": "tier_3_heuristic",
                "is_soft_label": True,
                "detection_method": "format_type_heuristic",
            },
            "image_properties": {
                "color_mode": color_mode,
                "document_age": "historical",
                "resolution_tier": _resolution_tier(width, height),
                "image_width": width,
                "image_height": height,
                "confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata_and_pillow",
            },
        },
    }

    # Multi-language entries for Korean/Japanese items with hangul/kana annotations
    if writing_tradition == "korean" and cat.get("multi_script"):
        record["data"]["languages"] = [
            record["data"]["language"],
            {
                "language_code": "ko",
                "script_code": "Hang",
                "bcp47_tag": "ko-Hang",
                "script_family": "cjk",
                "confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata",
                "text_direction": "ttb",
                "is_rtl": False,
                "is_primary": False,
            },
        ]

    return record


def _build_description(cat: dict[str, Any]) -> str:
    """Build a human-readable description from catalog entry."""
    parts = []
    if cat.get("calligrapher"):
        parts.append(cat["calligrapher"])
    if cat.get("calligrapher_cjk"):
        parts.append(f"({cat['calligrapher_cjk']})")
    if cat.get("dynasty"):
        parts.append(f"{cat['dynasty']} dynasty")
    if cat.get("script_style_cjk"):
        parts.append(cat["script_style_cjk"])
    elif cat.get("script_style"):
        parts.append(cat["script_style"])
    if cat.get("format_type"):
        parts.append(cat["format_type"].replace("_", " "))
    if cat.get("medium"):
        parts.append(cat["medium"].replace("_", " "))
    return ", ".join(parts) if parts else "Thousand Character Classic"


def _build_extended_entry(
    entry: dict[str, Any],
    catalog_entry: dict[str, Any] | None,
    text_data: dict[str, Any],
    image_props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build extended sidecar entry with art-historical metadata."""
    cat = catalog_entry or {}
    props = image_props or {}
    width = props.get("width", 0)
    height = props.get("height", 0)
    return {
        "sample_id": entry["sample_id"],
        "calligrapher_name": cat.get("calligrapher", ""),
        "calligrapher_name_cjk": cat.get("calligrapher_cjk", ""),
        "calligrapher_dates": cat.get("calligrapher_dates", ""),
        "script_style": cat.get("script_style", ""),
        "script_style_cjk": cat.get("script_style_cjk", ""),
        "script_components": cat.get("script_components", []),
        "dynasty_period": cat.get("dynasty", ""),
        "period_century": cat.get("period_century", ""),
        "medium": cat.get("medium", ""),
        "format_type": cat.get("format_type", ""),
        "source_institution": cat.get(
            "source_institution", entry.get("source_institution", "")
        ),
        "source_url": cat.get("source_url", entry.get("source_url", "")),
        "catalog_number": entry.get("catalog_number"),
        "license_spdx": _normalize_license(
            cat.get("license", entry.get("license", ""))
        ),
        "multi_script_work": cat.get("multi_script", False),
        "writing_tradition": cat.get("writing_tradition", "chinese"),
        "resolution_tier": _resolution_tier(width, height)
        if width and height
        else "unknown",
        "image_width": width,
        "image_height": height,
        "notes": cat.get("notes", ""),
        "translation_en": text_data.get("full_text_en", ""),
    }


def _normalize_license(raw: str) -> str:
    """Normalize license strings to SPDX-like identifiers."""
    mapping = {
        "CC0": "CC0-1.0",
        "CC_BY_4.0": "CC-BY-4.0",
        "public_domain": "PD",
        "open_access": "OA",
        "KOGL": "KOGL-Type-I",
        "viewable_online": "viewable-online",
        "check_institution": "check-institution",
        "check_yale_policy": "check-yale",
        "contact_museum": "contact-museum",
    }
    return mapping.get(raw, raw)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """Enrich Thousand Character Classic dataset with L2 metadata."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


@cli.command("enrich")
@click.option(
    "--image-dir",
    type=click.Path(path_type=Path, exists=False),
    default=_DEFAULT_IMAGE_DIR,
    show_default=True,
    help="Base directory containing downloaded images.",
)
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
def enrich(image_dir: Path, dry_run: bool) -> None:
    """Generate L2 enrichment records and extended sidecar."""
    catalog = _load_catalog()
    text_data = _load_text()
    entries = _load_registry()

    if not entries:
        click.echo("Registry is empty. Run harvest commands first.")
        return

    click.echo(f"Processing {len(entries)} registry entries...")
    _L2_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    l2_count = 0
    sidecar_count = 0

    # Clear sidecar if not dry run
    if not dry_run and _SIDECAR_PATH.exists():
        _SIDECAR_PATH.unlink()

    for entry in entries:
        sample_id = entry["sample_id"]
        cat_num = entry.get("catalog_number")
        cat_entry = catalog.get(cat_num) if cat_num else None

        # Pass 2: Image-derived properties
        source_path = entry.get("source_path", "")
        image_path = image_dir / source_path
        if image_path.exists():
            image_props = _get_image_props(image_path)
        else:
            image_props = {
                "width": entry.get("original_dimensions", [0, 0])[0],
                "height": entry.get("original_dimensions", [0, 0])[1],
                "dpi": None,
                "color_mode": "color",
            }

        # Build L2 record
        l2 = _build_l2_record(entry, cat_entry, text_data, image_props)

        # Build extended sidecar
        ext = _build_extended_entry(entry, cat_entry, text_data, image_props)

        if dry_run:
            click.echo(f"  [DRY RUN] {sample_id}: {l2['description']}")
            continue

        # Write L2 JSON
        l2_path = _L2_OUTPUT_DIR / f"{sample_id}.json"
        with l2_path.open("w") as fh:
            json.dump(l2, fh, ensure_ascii=False, indent=2)
        l2_count += 1

        # Append sidecar
        with _SIDECAR_PATH.open("a") as fh:
            fh.write(json.dumps(ext, ensure_ascii=False) + "\n")
        sidecar_count += 1

    click.echo(
        f"\nEnrichment complete: {l2_count} L2 records, {sidecar_count} sidecar entries."
    )
    click.echo(f"  L2 output: {_L2_OUTPUT_DIR}")
    click.echo(f"  Sidecar: {_SIDECAR_PATH}")


# ---------------------------------------------------------------------------
# Classical IQA enrichment helpers
# ---------------------------------------------------------------------------

_SEVERITY_TO_NUMERIC: dict[str, float] = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.75,
    "critical": 1.0,
}

_SEVERITY_TO_CATEGORICAL: dict[str, str] = {
    "low": "mild",
    "medium": "moderate",
    "high": "severe",
    "critical": "severe",
}

_PROVENANCE_TIER_ORDER = {
    "tier_3_heuristic": 0,
    "tier_2_model": 1,
    "tier_1_annotation": 2,
    "tier_0_exact": 3,
}


def _run_iqa_detectors(image_path: Path) -> dict[str, Any]:
    """Run all 8 classical IQA detectors on a single image.

    Returns dict with keys: degradations, overall_score, skew_angle, skew_confidence,
    quality_confidence.
    """
    import cv2

    from image_preprocessing_detector.detection.iqa_classical import (
        BinarizationQualityDetector,
        BleedThroughDetector,
        BlurDetector,
        ContrastDetector,
        IlluminationDetector,
        JPEGBlockinessDetector,
        NoiseDetector,
        SkewDetector,
    )

    img = cv2.imread(str(image_path))
    if img is None:
        logger.warning("OpenCV failed to read: %s", image_path)
        return {
            "degradations": [],
            "overall_score": None,
            "skew_angle": None,
            "skew_confidence": None,
            "quality_confidence": None,
        }

    degradations: list[dict[str, Any]] = []
    quality_scores: list[float] = []  # 0=bad, 1=good
    confidences: list[float] = []
    skew_angle: float | None = None
    skew_confidence: float | None = None

    # --- 1. Skew ---
    try:
        skew_det = SkewDetector()
        skew_r = skew_det.detect(img)
        skew_angle = round(skew_r.angle, 3)
        skew_confidence = round(skew_r.confidence, 3)
        sev_val = skew_r.severity.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        # Quality = 1 - severity (no skew = high quality)
        quality_scores.append(1.0 - sev_num)
        confidences.append(skew_r.confidence)
        if skew_r.is_skewed:
            degradations.append(
                {
                    "type": "skew",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(sev_num, 3),
                    "confidence": round(skew_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": f"hough_projection_{skew_r.method}",
                    "location": "global",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning("Skew detection failed for %s: %s", image_path.name, exc)

    # --- 2. Blur ---
    try:
        blur_det = BlurDetector()
        blur_r = blur_det.detect(img)
        sev_val = blur_r.severity.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        quality_scores.append(blur_r.blur_score)
        confidences.append(blur_r.confidence)
        if blur_r.is_blurred:
            degradations.append(
                {
                    "type": "blur",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(1.0 - blur_r.blur_score, 3),
                    "confidence": round(blur_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": "laplacian_variance",
                    "location": "global",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning("Blur detection failed for %s: %s", image_path.name, exc)

    # --- 3. Noise ---
    try:
        noise_det = NoiseDetector()
        noise_r = noise_det.detect(img)
        sev_val = noise_r.severity.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        quality_scores.append(noise_r.noise_score)
        confidences.append(noise_r.confidence)
        if noise_r.is_noisy:
            degradations.append(
                {
                    "type": "noise",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(1.0 - noise_r.noise_score, 3),
                    "confidence": round(noise_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": "wavelet_mad",
                    "location": "global",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning("Noise detection failed for %s: %s", image_path.name, exc)

    # --- 4. Contrast ---
    try:
        contrast_det = ContrastDetector()
        contrast_r = contrast_det.detect(img)
        sev_val = contrast_r.severity.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        quality_scores.append(contrast_r.score)
        confidences.append(contrast_r.confidence)
        if contrast_r.is_low_contrast:
            degradations.append(
                {
                    "type": "low_contrast",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(1.0 - contrast_r.score, 3),
                    "confidence": round(contrast_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": "histogram_analysis",
                    "location": "global",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning("Contrast detection failed for %s: %s", image_path.name, exc)

    # --- 5. Illumination ---
    try:
        illum_det = IlluminationDetector()
        illum_r = illum_det.detect(img)
        sev_val = illum_r.severity.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        quality_scores.append(illum_r.score)
        confidences.append(illum_r.confidence)
        if illum_r.has_issues:
            degradations.append(
                {
                    "type": "illumination_uneven",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(1.0 - illum_r.score, 3),
                    "confidence": round(illum_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": "regional_brightness_analysis",
                    "location": "global",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning("Illumination detection failed for %s: %s", image_path.name, exc)

    # --- 6. JPEG Blockiness ---
    try:
        jpeg_det = JPEGBlockinessDetector()
        jpeg_r = jpeg_det.detect(img)
        sev_val = jpeg_r.severity.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        quality_scores.append(jpeg_r.compression_score)
        confidences.append(jpeg_r.confidence)
        if jpeg_r.has_artifacts:
            degradations.append(
                {
                    "type": "compression_artifact",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(jpeg_r.blockiness_score, 3),
                    "confidence": round(jpeg_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": "dct_block_boundary",
                    "location": "global",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning("JPEG detection failed for %s: %s", image_path.name, exc)

    # --- 7. Binarization Quality ---
    try:
        binar_det = BinarizationQualityDetector()
        binar_r = binar_det.detect(img)
        sev_val = binar_r.severity.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        quality_scores.append(binar_r.binarization_score)
        confidences.append(binar_r.confidence)
        if sev_val in ("medium", "high", "critical"):
            degradations.append(
                {
                    "type": "poor_binarization",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(1.0 - binar_r.binarization_score, 3),
                    "confidence": round(binar_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": "bimodality_otsu",
                    "location": "global",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning("Binarization detection failed for %s: %s", image_path.name, exc)

    # --- 8. Bleed-Through ---
    try:
        bleed_det = BleedThroughDetector()
        bleed_r = bleed_det.detect(img)
        sev_val = bleed_r.severity_level.value
        sev_num = _SEVERITY_TO_NUMERIC.get(sev_val, 0.25)
        quality_scores.append(1.0 - bleed_r.severity)
        confidences.append(bleed_r.confidence)
        if bleed_r.bleed_through_detected:
            degradations.append(
                {
                    "type": "bleed_through",
                    "severity": _SEVERITY_TO_CATEGORICAL.get(sev_val, "mild"),
                    "severity_numeric": round(bleed_r.severity, 3),
                    "confidence": round(bleed_r.confidence, 3),
                    "provenance_tier": "tier_2_model",
                    "is_soft_label": True,
                    "detection_method": "morphological_background",
                    "location": "global"
                    if bleed_r.affected_ratio > 0.3
                    else "localized",
                    "region": None,
                }
            )
    except Exception as exc:
        logger.warning(
            "Bleed-through detection failed for %s: %s", image_path.name, exc
        )

    # Compute overall quality score (mean of individual quality scores)
    overall_score: float | None = None
    quality_confidence: float | None = None
    if quality_scores:
        overall_score = round(sum(quality_scores) / len(quality_scores), 4)
        quality_confidence = round(min(confidences) if confidences else 0.0, 3)

    return {
        "degradations": degradations,
        "overall_score": overall_score,
        "skew_angle": skew_angle,
        "skew_confidence": skew_confidence,
        "quality_confidence": quality_confidence,
    }


def _compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary from all L2 data fields."""
    all_fields = [
        "capture_method",
        "resolution",
        "domain",
        "structure",
        "quality",
        "language",
        "text_scope",
        "content_flags",
        "text_content",
        "text_statistics",
        "handwriting_assessment",
        "geometric",
        "image_properties",
    ]
    total_schema_fields = 22  # Full L2 schema field count

    min_conf = 1.0
    min_conf_field: str | None = None
    min_prov = "tier_0_exact"
    assessed = 0
    unassessed = 0
    hard = 0
    soft = 0

    for field_name in all_fields:
        field_data = data.get(field_name)
        if not isinstance(field_data, dict):
            continue

        conf = field_data.get("confidence")
        prov = field_data.get("provenance_tier")

        if conf is not None:
            assessed += 1
            if conf >= 0.9:
                hard += 1
            elif conf >= 0.7:
                soft += 1
            if conf < min_conf:
                min_conf = conf
                min_conf_field = field_name
        else:
            unassessed += 1

        if prov and _PROVENANCE_TIER_ORDER.get(prov, 0) < _PROVENANCE_TIER_ORDER.get(
            min_prov, 3
        ):
            min_prov = prov

    unpopulated = total_schema_fields - len(
        [f for f in all_fields if isinstance(data.get(f), dict)]
    )

    # Determine category
    if assessed == 0:
        category = "unassessed"
        min_conf_val = None
    else:
        min_conf_val = round(min_conf, 3)
        if min_conf >= 0.9:
            category = "hard_label"
        elif min_conf >= 0.7:
            category = "soft_label"
        elif min_conf >= 0.5:
            category = "active_learning"
        else:
            category = "unreliable"

    return {
        "min_confidence": min_conf_val,
        "min_confidence_field": min_conf_field,
        "min_confidence_category": category,
        "min_provenance_tier": min_prov,
        "assessed_field_count": assessed,
        "unassessed_field_count": unassessed,
        "unpopulated_field_count": unpopulated,
        "hard_field_count": hard,
        "soft_field_count": soft,
    }


@cli.command("enrich-iqa")
@click.option(
    "--image-dir",
    type=click.Path(path_type=Path, exists=False),
    default=None,
    help="Base directory containing images. Auto-detects local data/ or E: drive.",
)
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
def enrich_iqa(image_dir: Path | None, dry_run: bool) -> None:
    """Run classical IQA detectors on all images and update L2 records.

    Populates: quality.overall_score, quality.degradations[],
    geometric.skew_angle_degrees, sample_reliability_summary.
    """
    # Auto-detect image directory
    if image_dir is None:
        if _LOCAL_IMAGE_DIR.exists():
            image_dir = _LOCAL_IMAGE_DIR
        elif _DEFAULT_IMAGE_DIR.exists():
            image_dir = _DEFAULT_IMAGE_DIR
        else:
            click.echo("No image directory found. Use --image-dir to specify.")
            return

    click.echo(f"Image directory: {image_dir}")

    entries = _load_registry()
    if not entries:
        click.echo("Registry is empty.")
        return

    l2_files = list(_L2_OUTPUT_DIR.glob("*.json"))
    if not l2_files:
        click.echo("No L2 records found. Run 'enrich' first.")
        return

    # Build sample_id → L2 file path map
    l2_map: dict[str, Path] = {p.stem: p for p in l2_files}

    updated = 0
    skipped = 0
    errors = 0

    click.echo(f"Running 8 classical IQA detectors on {len(entries)} images...")

    for idx, entry in enumerate(entries, 1):
        sample_id = entry["sample_id"]
        source_path = entry.get("source_path", "")
        img_path = image_dir / source_path

        if not img_path.exists():
            logger.warning("Image not found: %s", img_path)
            skipped += 1
            continue

        l2_path = l2_map.get(sample_id)
        if not l2_path:
            logger.warning("No L2 record for %s", sample_id)
            skipped += 1
            continue

        # Run IQA
        try:
            iqa_results = _run_iqa_detectors(img_path)
        except Exception as exc:
            logger.warning("IQA failed for %s: %s", img_path.name, exc)
            errors += 1
            continue

        if dry_run:
            deg_count = len(iqa_results["degradations"])
            score = iqa_results["overall_score"]
            click.echo(
                f"  [{idx}/{len(entries)}] {img_path.name}: "
                f"score={score}, {deg_count} degradations"
            )
            continue

        # Load existing L2, update, write back
        with l2_path.open("r") as fh:
            record = json.load(fh)

        data = record.get("data", {})

        # Update quality
        data["quality"] = {
            "overall_score": iqa_results["overall_score"],
            "degradations": iqa_results["degradations"],
            "confidence": iqa_results["quality_confidence"],
            "provenance_tier": "tier_2_model",
            "is_soft_label": True,
            "detection_method": "classical_ensemble_8detector",
        }

        # Update geometric skew
        if iqa_results["skew_angle"] is not None:
            geo = data.get("geometric", {})
            geo["skew_angle_degrees"] = iqa_results["skew_angle"]
            geo["skew_confidence"] = iqa_results["skew_confidence"]
            geo["skew_detection_method"] = "hough_projection_ensemble"
            data["geometric"] = geo

        # Compute and add sample_reliability_summary
        data["sample_reliability_summary"] = _compute_reliability_summary(data)

        record["data"] = data

        with l2_path.open("w") as fh:
            json.dump(record, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

        updated += 1

        if idx % 50 == 0:
            click.echo(f"  Progress: {idx}/{len(entries)} ({updated} updated)")

    click.echo(
        f"\nIQA enrichment complete: {updated} updated, {skipped} skipped, {errors} errors"
    )


@cli.command("validate")
def validate() -> None:
    """Validate L2 records against the schema."""
    try:
        import jsonschema
    except ImportError:
        click.echo("jsonschema not installed. Run: uv add jsonschema")
        return

    schema_path = _PROJECT_ROOT / "docs" / "schema" / "layer2_enrichment_v2.schema.json"
    if not schema_path.exists():
        click.echo(f"Schema not found: {schema_path}")
        return

    with schema_path.open("r") as fh:
        schema = json.load(fh)

    l2_files = list(_L2_OUTPUT_DIR.glob("*.json"))
    if not l2_files:
        click.echo("No L2 records found. Run 'enrich' first.")
        return

    errors = 0
    for path in l2_files:
        with path.open("r") as fh:
            record = json.load(fh)
        try:
            jsonschema.validate(record, schema)
        except jsonschema.ValidationError as exc:
            click.echo(f"  [FAIL] {path.name}: {exc.message}")
            errors += 1

    click.echo(f"\nValidated {len(l2_files)} records: {errors} errors")


@cli.command("stats")
def stats() -> None:
    """Show enrichment statistics."""
    l2_files = list(_L2_OUTPUT_DIR.glob("*.json"))
    click.echo(f"L2 records: {len(l2_files)}")

    if _SIDECAR_PATH.exists():
        with _SIDECAR_PATH.open("r") as fh:
            sidecar_count = sum(1 for line in fh if line.strip())
        click.echo(f"Sidecar entries: {sidecar_count}")

    if not l2_files:
        return

    # Analyze field coverage
    fields_populated: dict[str, int] = {}
    for path in l2_files:
        with path.open("r") as fh:
            record = json.load(fh)
        data = record.get("data", {})
        for key, val in data.items():
            if val is not None:
                fields_populated[key] = fields_populated.get(key, 0) + 1

    click.echo(f"\nField coverage ({len(l2_files)} records):")
    for field, count in sorted(fields_populated.items()):
        pct = count / len(l2_files) * 100
        click.echo(f"  {field}: {count}/{len(l2_files)} ({pct:.0f}%)")


@cli.command("audit-dedup")
@click.option(
    "--image-dir",
    type=click.Path(path_type=Path, exists=False),
    default=_DEFAULT_IMAGE_DIR,
    show_default=True,
    help="Base directory containing downloaded images.",
)
@click.option(
    "--threshold",
    type=int,
    default=10,
    show_default=True,
    help="pHash Hamming distance threshold for near-duplicate detection.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=_PROJECT_ROOT / "metadata_registry" / "tcc_dedup_audit.json",
    show_default=True,
    help="Path to write audit report.",
)
def audit_dedup(image_dir: Path, threshold: int, output: Path) -> None:
    """Detect near-duplicate images across institutions via pHash."""
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        click.echo(
            "ERROR: imagehash and Pillow required. Install with: uv add imagehash",
            err=True,
        )
        raise SystemExit(1)

    registry = _load_registry()
    click.echo(f"Loaded {len(registry)} registry entries")

    # Group by catalog_number
    groups: dict[int, list[dict[str, Any]]] = {}
    for entry in registry:
        cat_num = entry.get("catalog_number")
        if cat_num is not None:
            groups.setdefault(cat_num, []).append(entry)

    duplicates: list[dict[str, Any]] = []
    sha_dupes: list[dict[str, Any]] = []
    checked = 0

    # Check SHA256 exact duplicates across ALL entries
    sha_map: dict[str, list[dict[str, Any]]] = {}
    for entry in registry:
        sha = entry.get("sha256", "")
        if sha:
            sha_map.setdefault(sha, []).append(entry)
    for sha, entries in sha_map.items():
        if len(entries) > 1:
            sha_dupes.append(
                {
                    "sha256": sha,
                    "count": len(entries),
                    "sample_ids": [e["sample_id"] for e in entries],
                    "institutions": list(
                        {e.get("source_institution", "") for e in entries}
                    ),
                }
            )

    # pHash near-duplicate detection within catalog groups
    for cat_num, entries in sorted(groups.items()):
        if len(entries) < 2:
            continue

        # Compute pHash for each image
        hashes: list[tuple[dict[str, Any], Any]] = []
        for entry in entries:
            file_path = entry.get("file_path", "")
            if not file_path:
                continue
            img_path = image_dir / file_path
            if not img_path.exists():
                continue
            try:
                with Image.open(img_path) as img:
                    phash = imagehash.phash(img)
                hashes.append((entry, phash))
                checked += 1
            except Exception as exc:
                logger.warning("Cannot hash %s: %s", img_path, exc)

        # Compare all pairs
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                e1, h1 = hashes[i]
                e2, h2 = hashes[j]
                distance = h1 - h2
                if distance <= threshold:
                    duplicates.append(
                        {
                            "catalog_number": cat_num,
                            "sample_id_a": e1["sample_id"],
                            "sample_id_b": e2["sample_id"],
                            "institution_a": e1.get("source_institution", ""),
                            "institution_b": e2.get("source_institution", ""),
                            "hamming_distance": distance,
                            "is_exact": distance == 0,
                        }
                    )

    report = {
        "timestamp": _now_iso(),
        "total_entries": len(registry),
        "images_checked": checked,
        "phash_threshold": threshold,
        "sha256_exact_duplicates": sha_dupes,
        "phash_near_duplicates": duplicates,
        "summary": {
            "sha256_duplicate_groups": len(sha_dupes),
            "phash_duplicate_pairs": len(duplicates),
            "exact_phash_pairs": sum(1 for d in duplicates if d["is_exact"]),
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as fh:
        json.dump(report, fh, indent=2)
    click.echo("\nDedup audit complete:")
    click.echo(f"  SHA256 duplicate groups: {len(sha_dupes)}")
    click.echo(f"  pHash near-duplicate pairs: {len(duplicates)}")
    click.echo(f"  Report: {output}")


@cli.command("audit-labels")
@click.option(
    "--sample-pct",
    type=float,
    default=0.10,
    show_default=True,
    help="Percentage of images to sample for validation (0.0-1.0).",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=_PROJECT_ROOT / "metadata_registry" / "tcc_label_audit.jsonl",
    show_default=True,
    help="Path to write audit sample file.",
)
@click.option("--seed", type=int, default=42, help="Random seed for reproducibility.")
def audit_labels(sample_pct: float, output: Path, seed: int) -> None:
    """Generate stratified sample for label validation audit."""
    import random

    random.seed(seed)

    registry = _load_registry()
    catalog = _load_catalog()
    click.echo(f"Loaded {len(registry)} registry entries")

    # Build extended entries for stratification
    strata: dict[str, list[dict[str, Any]]] = {}
    for entry in registry:
        cat_num = entry.get("catalog_number")
        cat = catalog.get(cat_num) if cat_num else None
        institution = (cat or {}).get(
            "source_institution", entry.get("source_institution", "unknown")
        )
        script = (cat or {}).get("script_style", "unknown")
        key = f"{institution}|{script}"
        strata.setdefault(key, []).append(entry)

    # Stratified sampling
    sampled: list[dict[str, Any]] = []
    for stratum_key, entries in sorted(strata.items()):
        n_sample = max(1, int(len(entries) * sample_pct))
        chosen = random.sample(entries, min(n_sample, len(entries)))
        institution, script = stratum_key.split("|", 1)
        for entry in chosen:
            cat_num = entry.get("catalog_number")
            cat = catalog.get(cat_num) if cat_num else None
            sampled.append(
                {
                    "sample_id": entry["sample_id"],
                    "file_path": entry.get("file_path", ""),
                    "source_institution": institution,
                    "catalog_number": cat_num,
                    "script_style": script,
                    "dynasty": (cat or {}).get("dynasty", ""),
                    "period_century": (cat or {}).get("period_century", ""),
                    "calligrapher": (cat or {}).get("calligrapher", ""),
                    "script_components": (cat or {}).get("script_components", []),
                    # Validation fields (to be filled by reviewer)
                    "script_style_correct": None,
                    "dynasty_correct": None,
                    "notes_reviewer": "",
                }
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as fh:
        for item in sampled:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    click.echo("\nLabel audit sample generated:")
    click.echo(f"  Total strata: {len(strata)}")
    click.echo(
        f"  Sampled entries: {len(sampled)} ({sample_pct:.0%} of {len(registry)})"
    )
    click.echo(f"  Output: {output}")
    click.echo("\nStrata breakdown:")
    for key, entries in sorted(strata.items()):
        n_sample = max(1, int(len(entries) * sample_pct))
        click.echo(f"  {key}: {min(n_sample, len(entries))}/{len(entries)}")


if __name__ == "__main__":
    cli()
