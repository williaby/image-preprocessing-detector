#!/usr/bin/env python3
"""Generate Layer 2 enrichment metadata for the John 1:1 manuscript dataset.

Two-pass enrichment:
  Pass 1 — Catalog-derived fields (script, text_content, domain=REL, handwriting)
  Pass 2 — Image-derived fields (Pillow measurements)

Output:
  - L2 records: metadata_registry/json/john11-manuscripts/{sample_id}.json
  - Extended sidecar: metadata_registry/john11_manuscripts_extended.jsonl

Usage:
    uv run python scripts/enrich_john11_manuscripts.py enrich
    uv run python scripts/enrich_john11_manuscripts.py validate
    uv run python scripts/enrich_john11_manuscripts.py stats

Requires:
    Pillow>=10.0.0   (already in base deps)
    PyYAML>=6.0      (already in base deps)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import click
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CATALOG_PATH = _PROJECT_ROOT / "config" / "john11_manuscript_catalog.yaml"
_REGISTRY_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "john11_manuscripts_registry.jsonl"
)
_L2_OUTPUT_DIR = (
    _PROJECT_ROOT / "metadata_registry" / "json" / "john11-manuscripts"
)
_SIDECAR_PATH = (
    _PROJECT_ROOT / "metadata_registry" / "john11_manuscripts_extended.jsonl"
)
_DEFAULT_IMAGE_DIR = Path(
    "/mnt/e/image_detection/01_base_data/manuscripts/john11"
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Script → metadata mappings
# ---------------------------------------------------------------------------

# ISO 15924 → language code, script family, text direction, is_rtl
_SCRIPT_METADATA: dict[str, tuple[str, str, str, bool]] = {
    "Grek": ("grc", "greek", "ltr", False),
    "Latn": ("la", "latin", "ltr", False),
    "Ethi": ("gez", "ethiopic", "ltr", False),
    "Armn": ("hy", "armenian", "ltr", False),
    "Syrc": ("syr", "syriac", "rtl", True),
    "Arab": ("ar", "arabic", "rtl", True),
    "Cyrs": ("cu", "cyrillic", "ltr", False),
    "Copt": ("cop", "coptic", "ltr", False),
    "Goth": ("got", "gothic", "ltr", False),
    "Geor": ("ka", "georgian", "ltr", False),
}

# John 1:1 text by language (ground truth)
_JOHN_1_1_TEXT: dict[str, str] = {
    "Grek": "Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος.",
    "Latn": "In principio erat Verbum, et Verbum erat apud Deum, et Deus erat Verbum.",
    "Ethi": "በቀዲሙ ቃል ውእቱ ነበረ ወቃል ኀበ እግዚአብሔር ውእቱ ነበረ ወእግዚአብሔር ውእቱ ቃል",
    "Armn": "Ի սկզբանէdelays էdelays Բանdelays, եdelays Բdelays առ Աdelays էrees, եrees Delays Delays Delays Delays",
    "Syrc": "ܒܪܫܝܬ ܐܝܬܘܗܝ ܗܘܐ ܡܠܬܐ ܘܗܘ ܡܠܬܐ ܐܝܬܘܗܝ ܗܘܐ ܠܘܬ ܐܠܗܐ ܘܐܠܗܐ ܐܝܬܘܗܝ ܗܘܐ ܗܘ ܡܠܬܐ",
    "Arab": "في البدء كان الكلمة والكلمة كان عند الله وكان الكلمة الله",
    "Cyrs": "Въ начал ѣ б ѣ Слово и Слово б ѣ оу Бога и Богъ б ѣ Слово",
    "Copt": "Ϩⲛ ⲧⲉϩⲟⲩⲉⲓⲧⲉ ⲛⲉϥϣⲟⲟⲡ ⲛϭⲓ ⲡⲗⲟⲅⲟⲥ",
    "Goth": "𐌸𐌰𐍄𐌰 𐍆𐍂𐌿𐌼𐌹𐍃𐍄𐌾𐌰 𐍅𐌰𐍃 𐍅𐌰𐌿𐍂𐌳",
    "Geor": "თავდაპირველად იყო სიტყვა და სიტყვა იყო ღმერთთან და ღმერთი იყო სიტყვა",
}

# Script style → legibility mapping (manuscript hands)
_LEGIBILITY_MAP: dict[str, tuple[str, float]] = {
    "uncial": ("GOOD", 0.75),
    "minuscule": ("GOOD", 0.70),
    "carolingian": ("GOOD", 0.80),
    "insular": ("FAIR", 0.60),
    "insular_majuscule": ("FAIR", 0.65),
    "insular_half_uncial": ("FAIR", 0.60),
    "gothic_uncial": ("FAIR", 0.55),
    "erkat'agir": ("GOOD", 0.70),
    "bolorgir": ("GOOD", 0.75),
    "fidel": ("GOOD", 0.70),
    "estrangela": ("FAIR", 0.55),
    "serto": ("FAIR", 0.55),
    "naskh": ("GOOD", 0.70),
    "sahidic_bohairic": ("FAIR", 0.55),
    "glagolitic_and_cyrillic": ("FAIR", 0.55),
    "mkhedruli_asomtavruli": ("FAIR", 0.55),
    "various": ("FAIR", 0.50),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_catalog() -> dict[int, dict[str, Any]]:
    with _CATALOG_PATH.open("r") as fh:
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
    return datetime.now(UTC).isoformat()


def _get_image_props(image_path: Path) -> dict[str, Any]:
    """Extract image properties via Pillow."""
    from PIL import Image

    props: dict[str, Any] = {}
    try:
        with Image.open(image_path) as img:
            props["width"] = img.width
            props["height"] = img.height
            props["color_mode"] = img.mode

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
        return "medium_150-299"
    if dpi < 150:
        return "low_<150"
    if dpi < 300:
        return "medium_150-299"
    if dpi == 300:
        return "standard_300"
    return "high_>300"


def _normalize_license(raw: str) -> str:
    """Normalize license strings to SPDX-like identifiers."""
    mapping = {
        "CC0": "CC0-1.0",
        "CC-BY-4.0": "CC-BY-4.0",
        "CC-BY-SA": "CC-BY-SA-4.0",
        "public_domain": "PD",
        "per-image": "mixed-open",
    }
    return mapping.get(raw, raw)


def _build_l2_record(
    entry: dict[str, Any],
    catalog_entry: dict[str, Any] | None,
    image_props: dict[str, Any],
) -> dict[str, Any]:
    """Build a complete L2 enrichment record (v2 schema)."""
    sample_id = entry["sample_id"]
    now = _now_iso()

    script_code = entry.get("script_iso15924", "Grek")
    lang_code, script_family, text_dir, is_rtl = _SCRIPT_METADATA.get(
        script_code, ("und", "unknown", "ltr", False)
    )

    bcp47 = f"{lang_code}-{script_code}"

    cat = catalog_entry or {}
    script_style = cat.get("script_style", "various")
    legibility_label, legibility_score = _LEGIBILITY_MAP.get(
        script_style, ("FAIR", 0.50)
    )

    gt_text = _JOHN_1_1_TEXT.get(script_code, "")

    width = image_props.get("width", 0)
    height = image_props.get("height", 0)
    dpi = image_props.get("dpi")
    raw_mode = image_props.get("color_mode", "RGB")
    _mode_map = {
        "RGB": "color",
        "RGBA": "color",
        "L": "grayscale",
        "1": "binarized",
        "P": "color",
    }
    color_mode = _mode_map.get(raw_mode, "color")

    ms_name = cat.get("manuscript_name", entry.get("source_institution", "unknown"))
    date_range = cat.get("date_range", "unknown")
    description = f"John 1:1 manuscript: {ms_name}, {date_range}, {script_code}"

    return {
        "sample_id": sample_id,
        "enrichment_version": 2,
        "schema_version": "2.4.0",
        "created_at": now,
        "created_by": "enrich_john11_manuscripts.py_v1.0.0",
        "method": "tier_1_annotation",
        "description": description,
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
                "detection_method": "institution_heuristic",
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
                "level1": "REL",
                "level2": "biblical_manuscript",
                "level3": "gospel_of_john",
                "confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata",
            },
            "structure": {
                "text_density": "dense",
                "layout_type": "single_column",
                "element_types": ["Text"],
                "confidence": 0.7,
                "provenance_tier": "tier_3_heuristic",
                "is_soft_label": True,
                "detection_method": "manuscript_heuristic",
                "text_directions_present": [text_dir],
            },
            "quality": {
                "overall_score": None,
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
                "script_family": script_family,
                "confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata",
                "text_direction": text_dir,
                "is_rtl": is_rtl,
                "is_primary": True,
            },
            "text_scope": {
                "scope": "page",
                "content_type": "handwritten",
                "density": "dense",
                "estimated_chars": len(gt_text) if gt_text else 50,
                "estimated_words": len(gt_text.split()) if gt_text else 10,
                "confidence": 0.8,
                "provenance_tier": "tier_1_annotation",
                "is_soft_label": False,
                "detection_method": "known_biblical_text",
            },
            "content_flags": {
                "has_table": False,
                "table_confidence": 1.0,
                "has_formula": False,
                "formula_confidence": 1.0,
                "has_handwriting": True,
                "handwriting_confidence": 1.0,
                "has_signature": False,
                "signature_confidence": 0.8,
                "has_figure": False,
                "figure_confidence": 0.6,
                "has_code": False,
                "code_confidence": 1.0,
                "provenance_tier": "tier_0_exact",
                "is_soft_label": False,
                "detection_method": "catalog_metadata",
            },
            "text_content": {
                "full_text": gt_text,
                "source_type": "ground_truth",
                "language_hint": lang_code,
                "is_complete": bool(gt_text),
                "confidence": 1.0 if gt_text else 0.0,
                "provenance_tier": "tier_0_exact" if gt_text else "tier_3_heuristic",
                "is_soft_label": not bool(gt_text),
            },
            "text_statistics": {
                "character_count": len(gt_text),
                "character_count_no_spaces": len(gt_text.replace(" ", "")),
                "word_count": len(gt_text.split()),
                "sentence_count": 1,
                "line_count": 1,
                "avg_word_length": (
                    round(
                        len(gt_text.replace(" ", "")) / max(len(gt_text.split()), 1),
                        1,
                    )
                ),
                "text_source": "ground_truth",
                "computation_method": "known_biblical_text",
                "inherited_confidence": 1.0 if gt_text else 0.0,
                "provenance_tier": "tier_0_exact" if gt_text else "tier_3_heuristic",
                "is_soft_label": not bool(gt_text),
            },
            "handwriting_assessment": {
                "presence": "DOMINANT",
                "presence_score": 0.95,
                "presence_confidence": 1.0,
                "legibility": legibility_label,
                "legibility_score": legibility_score,
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
                "orientation_detection_method": "manuscript_heuristic",
                "skew_angle_degrees": None,
                "skew_confidence": None,
                "skew_detection_method": None,
                "confidence": 0.8,
                "provenance_tier": "tier_3_heuristic",
                "is_soft_label": True,
                "detection_method": "manuscript_heuristic",
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


def _build_extended_entry(
    entry: dict[str, Any],
    catalog_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build extended sidecar entry with manuscript-historical metadata."""
    cat = catalog_entry or {}
    return {
        "sample_id": entry["sample_id"],
        "manuscript_name": cat.get("manuscript_name", ""),
        "ga_number": cat.get("ga_number"),
        "date_range": cat.get("date_range", ""),
        "institution": cat.get("institution", entry.get("source_institution", "")),
        "script_iso15924": entry.get("script_iso15924", ""),
        "script_style": cat.get("script_style", ""),
        "ood_reserved": cat.get("ood_reserved", False),
        "text_direction": cat.get("text_direction", "ltr"),
        "source_url": cat.get("source_url", entry.get("source_url", "")),
        "catalog_number": entry.get("catalog_number"),
        "license_spdx": _normalize_license(entry.get("license", "")),
        "notes": cat.get("notes", ""),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """Enrich John 1:1 manuscript dataset with L2 metadata."""
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
    entries = _load_registry()

    if not entries:
        click.echo("Registry is empty. Run harvest commands first.")
        return

    click.echo(f"Processing {len(entries)} registry entries...")
    _L2_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    l2_count = 0
    sidecar_count = 0

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
            dims = entry.get("original_dimensions", [0, 0])
            image_props = {
                "width": dims[0] if len(dims) > 0 else 0,
                "height": dims[1] if len(dims) > 1 else 0,
                "dpi": None,
                "color_mode": "RGB",
            }

        l2 = _build_l2_record(entry, cat_entry, image_props)
        ext = _build_extended_entry(entry, cat_entry)

        if dry_run:
            click.echo(f"  [DRY RUN] {sample_id}: {l2['description']}")
            continue

        l2_path = _L2_OUTPUT_DIR / f"{sample_id}.json"
        with l2_path.open("w") as fh:
            json.dump(l2, fh, ensure_ascii=False, indent=2)
        l2_count += 1

        with _SIDECAR_PATH.open("a") as fh:
            fh.write(json.dumps(ext, ensure_ascii=False) + "\n")
        sidecar_count += 1

    click.echo(
        f"\nEnrichment complete: {l2_count} L2 records, "
        f"{sidecar_count} sidecar entries."
    )
    click.echo(f"  L2 output: {_L2_OUTPUT_DIR}")
    click.echo(f"  Sidecar: {_SIDECAR_PATH}")


@cli.command("validate")
def validate() -> None:
    """Validate all L2 records against schema."""
    if not _L2_OUTPUT_DIR.exists():
        click.echo("No L2 records found. Run 'enrich' first.")
        return

    files = list(_L2_OUTPUT_DIR.glob("*.json"))
    click.echo(f"Validating {len(files)} L2 records...")

    errors = 0
    required_fields = [
        "sample_id",
        "enrichment_version",
        "schema_version",
        "data",
    ]
    required_data_fields = [
        "capture_method",
        "resolution",
        "domain",
        "language",
        "content_flags",
        "handwriting_assessment",
        "image_properties",
    ]

    for f in files:
        try:
            with f.open("r") as fh:
                record = json.load(fh)

            for field in required_fields:
                if field not in record:
                    click.echo(f"  [ERROR] {f.name}: missing '{field}'")
                    errors += 1

            data = record.get("data", {})
            for field in required_data_fields:
                if field not in data:
                    click.echo(f"  [ERROR] {f.name}: missing data.{field}")
                    errors += 1

            # Verify domain is REL
            domain = data.get("domain", {}).get("level1", "")
            if domain != "REL":
                click.echo(f"  [WARN] {f.name}: domain is '{domain}', expected 'REL'")

        except json.JSONDecodeError as exc:
            click.echo(f"  [ERROR] {f.name}: invalid JSON: {exc}")
            errors += 1

    if errors == 0:
        click.echo(f"All {len(files)} records pass validation.")
    else:
        click.echo(f"\n{errors} errors found in {len(files)} records.")


@cli.command("stats")
def stats() -> None:
    """Show enrichment statistics."""
    entries = _load_registry()

    if not entries:
        click.echo("Registry is empty.")
        return

    # Count L2 records
    l2_files = list(_L2_OUTPUT_DIR.glob("*.json")) if _L2_OUTPUT_DIR.exists() else []

    click.echo(f"Registry entries: {len(entries)}")
    click.echo(f"L2 records: {len(l2_files)}")

    # By script
    by_script: dict[str, int] = {}
    for e in entries:
        script = e.get("script_iso15924", "unknown")
        by_script[script] = by_script.get(script, 0) + 1

    click.echo("\nBy script:")
    for script, count in sorted(by_script.items(), key=lambda x: -x[1]):
        click.echo(f"  {script}: {count}")

    coverage = len(l2_files) / len(entries) * 100 if entries else 0
    click.echo(f"\nL2 coverage: {coverage:.1f}%")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
