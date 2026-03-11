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
    _mode_map = {"RGB": "color", "RGBA": "color", "L": "grayscale", "1": "binarized", "P": "color"}
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
) -> dict[str, Any]:
    """Build extended sidecar entry with art-historical metadata."""
    cat = catalog_entry or {}
    return {
        "sample_id": entry["sample_id"],
        "calligrapher_name": cat.get("calligrapher", ""),
        "calligrapher_name_cjk": cat.get("calligrapher_cjk", ""),
        "calligrapher_dates": cat.get("calligrapher_dates", ""),
        "script_style": cat.get("script_style", ""),
        "script_style_cjk": cat.get("script_style_cjk", ""),
        "dynasty_period": cat.get("dynasty", ""),
        "period_century": cat.get("period_century", ""),
        "medium": cat.get("medium", ""),
        "format_type": cat.get("format_type", ""),
        "source_institution": cat.get("source_institution", entry.get("source_institution", "")),
        "source_url": cat.get("source_url", entry.get("source_url", "")),
        "catalog_number": entry.get("catalog_number"),
        "license_spdx": _normalize_license(cat.get("license", entry.get("license", ""))),
        "multi_script_work": cat.get("multi_script", False),
        "writing_tradition": cat.get("writing_tradition", "chinese"),
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
        ext = _build_extended_entry(entry, cat_entry, text_data)

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

    click.echo(f"\nEnrichment complete: {l2_count} L2 records, {sidecar_count} sidecar entries.")
    click.echo(f"  L2 output: {_L2_OUTPUT_DIR}")
    click.echo(f"  Sidecar: {_SIDECAR_PATH}")


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


if __name__ == "__main__":
    cli()
