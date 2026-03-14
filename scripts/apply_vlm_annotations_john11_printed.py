"""Apply VLM per-image annotations to L2 JSON records for john11-printed-editions dataset.

Loads VLM annotation JSON files produced from contact sheet review and applies
degradation, quality, and layout annotations to the L2 enrichment records.
Images without VLM coverage receive script-level defaults computed from the
available annotated images for that script.

Print-specific canonical degradations differ from manuscripts:
  - Added: dot_gain, registration_error, ink_bleed (print-specific)
  - Shared: yellowing, foxing, bleed_through, staining, tears, water_damage,
            fading, creasing, binding_shadow, none

Usage:
    uv run python scripts/apply_vlm_annotations_john11_printed.py apply
    uv run python scripts/apply_vlm_annotations_john11_printed.py stats
    uv run python scripts/apply_vlm_annotations_john11_printed.py validate
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

import click

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path("/home/byron/dev/image_detection")
ANNOTATION_DIR = (
    REPO_ROOT / "data/john11-printed-editions/annotation_sheets"
)
L2_DIR = REPO_ROOT / "metadata_registry/json/john11-printed-editions"
REGISTRY_PATH = (
    REPO_ROOT / "metadata_registry/john11_printed_editions_registry.jsonl"
)

# ---------------------------------------------------------------------------
# Canonical value sets (print-specific)
# ---------------------------------------------------------------------------
CANONICAL_DEGRADATIONS = frozenset(
    [
        "yellowing",
        "foxing",
        "ink_bleed",
        "dot_gain",
        "registration_error",
        "bleed_through",
        "staining",
        "tears",
        "water_damage",
        "fading",
        "creasing",
        "binding_shadow",
        "none",
    ]
)

DEGRADATION_ALIASES: dict[str, str | None] = {
    "minor_staining": "staining",
    "severe_water_damage": "water_damage",
    "ink_spread": "ink_bleed",
    "ink_bleeding": "ink_bleed",
    "show_through": "bleed_through",
    "discoloration": "yellowing",
    "age_spots": "foxing",
    "offset_error": "registration_error",
    "halftone_visible": "dot_gain",
    "paper_loss": "tears",
    "edge_damage": "tears",
    "low_contrast": "fading",
    "noise": None,
    "marginal_notes": None,
    "surface_dirt": None,
}

VALID_CAPTURE_METHODS = frozenset(
    ["digital_photography", "flatbed_scan", "microfilm_scan", "screen_capture"]
)

VALID_LEGIBILITY = frozenset(
    ["EXCELLENT", "GOOD", "FAIR", "POOR", "ILLEGIBLE"]
)

LEGIBILITY_SCORE: dict[str, float] = {
    "EXCELLENT": 0.95,
    "GOOD": 0.75,
    "FAIR": 0.55,
    "POOR": 0.35,
    "ILLEGIBLE": 0.15,
}

VALID_ORIENTATIONS = frozenset([0, 90, 180, 270])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_degradation(raw: str) -> str | None:
    """Normalize a degradation string to canonical form."""
    cleaned = raw.strip().lower().replace(" ", "_").replace("-", "_")
    if cleaned in CANONICAL_DEGRADATIONS:
        return cleaned
    return DEGRADATION_ALIASES.get(cleaned, cleaned)


def _load_registry() -> list[dict]:
    """Load registry JSONL."""
    entries = []
    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open("r") as fh:
            for line in fh:
                if line.strip():
                    entries.append(json.loads(line))
    return entries


def _load_l2(sample_id: str) -> dict | None:
    """Load a single L2 record."""
    path = L2_DIR / f"{sample_id}.json"
    if path.exists():
        with path.open("r") as fh:
            return json.load(fh)
    return None


def _save_l2(sample_id: str, record: dict) -> None:
    """Save a single L2 record."""
    path = L2_DIR / f"{sample_id}.json"
    with path.open("w") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)


def _load_annotation_batches() -> dict[str, list[dict]]:
    """Load all VLM annotation JSON files from the annotation directory.

    Expected format: {script_code: [{idx, quality_score, degradations, ...}, ...]}
    Files named: vlm_annotations_batch{N}.json or vlm_annotations_{script}.json
    """
    all_annotations: dict[str, list[dict]] = {}

    if not ANNOTATION_DIR.exists():
        return all_annotations

    for json_file in sorted(ANNOTATION_DIR.glob("vlm_annotations_*.json")):
        with json_file.open("r") as fh:
            batch = json.load(fh)

        if isinstance(batch, dict):
            for script, items in batch.items():
                if script not in all_annotations:
                    all_annotations[script] = []
                all_annotations[script].extend(items)

    return all_annotations


def _build_script_index(entries: list[dict]) -> dict[str, list[dict]]:
    """Group registry entries by script, maintaining index order."""
    by_script: dict[str, list[dict]] = {}
    for entry in entries:
        script = entry.get("script_iso15924", "unknown")
        if script not in by_script:
            by_script[script] = []
        by_script[script].append(entry)
    return by_script


def _compute_defaults(annotations: list[dict]) -> dict:
    """Compute script-level defaults from available annotations."""
    if not annotations:
        return {
            "quality_score": 0.70,
            "degradations": ["none"],
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        }

    scores = [a["quality_score"] for a in annotations if "quality_score" in a]
    all_degs: list[str] = []
    for a in annotations:
        all_degs.extend(a.get("degradations", []))
    deg_counts = Counter(all_degs)
    # Keep degradations that appear in >25% of images
    threshold = len(annotations) * 0.25
    common_degs = [d for d, c in deg_counts.most_common() if c >= threshold and d != "none"]
    if not common_degs:
        common_degs = ["none"]

    capture_counts = Counter(a.get("capture_method", "flatbed_scan") for a in annotations)
    leg_counts = Counter(a.get("legibility", "GOOD") for a in annotations)

    return {
        "quality_score": round(statistics.mean(scores), 2) if scores else 0.70,
        "degradations": common_degs,
        "capture_method": capture_counts.most_common(1)[0][0],
        "legibility": leg_counts.most_common(1)[0][0],
        "orientation": 0,
    }


def _apply_annotation_to_l2(record: dict, annotation: dict) -> dict:
    """Apply a single VLM annotation to an L2 record."""
    data = record.get("data", {})

    # Quality
    quality_score = annotation.get("quality_score")
    degradations = annotation.get("degradations", [])
    normalized_degs = []
    for d in degradations:
        nd = _normalize_degradation(d)
        if nd is not None:
            normalized_degs.append(nd)
    if not normalized_degs:
        normalized_degs = ["none"]

    data["quality"] = {
        "overall_score": quality_score,
        "degradations": normalized_degs,
        "confidence": 0.85,
        "provenance_tier": "tier_2_model",
        "is_soft_label": True,
        "detection_method": "vlm_contact_sheet_review",
    }

    # Capture method
    capture = annotation.get("capture_method")
    if capture and capture in VALID_CAPTURE_METHODS:
        data["capture_method"]["method"] = capture
        data["capture_method"]["confidence"] = 0.85
        data["capture_method"]["provenance_tier"] = "tier_2_model"
        data["capture_method"]["detection_method"] = "vlm_contact_sheet_review"

    # Legibility (updates handwriting_assessment legibility for printed text)
    legibility = annotation.get("legibility")
    if legibility and legibility in VALID_LEGIBILITY:
        hw = data.get("handwriting_assessment", {})
        hw["legibility"] = legibility
        hw["legibility_score"] = LEGIBILITY_SCORE.get(legibility, 0.55)
        hw["legibility_confidence"] = 0.85
        data["handwriting_assessment"] = hw

    # Orientation
    orientation = annotation.get("orientation", 0)
    if orientation in VALID_ORIENTATIONS:
        geo = data.get("geometric", {})
        geo["orientation_class"] = orientation
        geo["orientation_confidence"] = 0.90
        geo["orientation_detection_method"] = "vlm_contact_sheet_review"
        data["geometric"] = geo

    record["data"] = data
    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """VLM annotation management for john11-printed-editions."""


@cli.command("apply")
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
def apply_annotations(dry_run: bool) -> None:
    """Apply VLM annotations to L2 records. Fill gaps with script-level defaults."""
    entries = _load_registry()
    if not entries:
        click.echo("Registry is empty.")
        return

    annotations = _load_annotation_batches()
    by_script = _build_script_index(entries)

    total_annotated = sum(len(v) for v in annotations.values())
    click.echo(f"Registry entries: {len(entries)}")
    click.echo(f"VLM annotations loaded: {total_annotated}")

    updated = 0
    defaulted = 0

    for script, script_entries in by_script.items():
        script_annotations = annotations.get(script, [])
        defaults = _compute_defaults(script_annotations)

        click.echo(
            f"\n  {script}: {len(script_entries)} images, "
            f"{len(script_annotations)} annotations"
        )

        for idx, entry in enumerate(script_entries):
            sample_id = entry["sample_id"]
            record = _load_l2(sample_id)
            if record is None:
                click.echo(f"    [SKIP] No L2 record: {sample_id}")
                continue

            # Find matching annotation by index
            annotation = None
            for a in script_annotations:
                if a.get("idx") == idx:
                    annotation = a
                    break

            if annotation:
                record = _apply_annotation_to_l2(record, annotation)
                updated += 1
            else:
                record = _apply_annotation_to_l2(record, defaults)
                defaulted += 1

            if not dry_run:
                _save_l2(sample_id, record)

    click.echo(
        f"\nDone: {updated} annotated, {defaulted} defaulted "
        f"({updated + defaulted} total)"
    )


@cli.command("stats")
def show_stats() -> None:
    """Show VLM annotation coverage statistics."""
    entries = _load_registry()
    annotations = _load_annotation_batches()

    click.echo(f"Registry entries: {len(entries)}")
    click.echo(f"VLM annotation scripts: {sorted(annotations.keys())}")
    click.echo(
        f"Total VLM annotations: {sum(len(v) for v in annotations.values())}"
    )

    by_script = _build_script_index(entries)
    click.echo("\nPer-script coverage:")
    for script in sorted(by_script.keys()):
        total = len(by_script[script])
        annotated = len(annotations.get(script, []))
        pct = annotated / total * 100 if total else 0
        click.echo(f"  {script}: {annotated}/{total} ({pct:.0f}%)")

    # Check L2 records for quality annotations
    l2_with_quality = 0
    l2_total = 0
    if L2_DIR.exists():
        for f in L2_DIR.glob("*.json"):
            l2_total += 1
            with f.open("r") as fh:
                record = json.load(fh)
            quality = record.get("data", {}).get("quality", {})
            if quality.get("overall_score") is not None:
                l2_with_quality += 1

    click.echo(f"\nL2 records with quality scores: {l2_with_quality}/{l2_total}")


@cli.command("validate")
def validate_annotations() -> None:
    """Validate VLM annotation data quality."""
    annotations = _load_annotation_batches()

    if not annotations:
        click.echo("No annotations found.")
        return

    errors = 0
    warnings = 0

    for script, items in annotations.items():
        click.echo(f"\n  {script}: {len(items)} annotations")
        for item in items:
            idx = item.get("idx", "?")

            # Validate quality score
            qs = item.get("quality_score")
            if qs is None or not (0.0 <= qs <= 1.0):
                click.echo(f"    [ERROR] idx={idx}: invalid quality_score={qs}")
                errors += 1

            # Validate degradations
            degs = item.get("degradations", [])
            for d in degs:
                nd = _normalize_degradation(d)
                if nd is None:
                    click.echo(f"    [WARN] idx={idx}: dropped degradation '{d}'")
                    warnings += 1
                elif nd not in CANONICAL_DEGRADATIONS:
                    click.echo(
                        f"    [WARN] idx={idx}: non-canonical degradation '{nd}'"
                    )
                    warnings += 1

            # Validate legibility
            leg = item.get("legibility")
            if leg and leg not in VALID_LEGIBILITY:
                click.echo(f"    [ERROR] idx={idx}: invalid legibility='{leg}'")
                errors += 1

            # Validate capture method
            cap = item.get("capture_method")
            if cap and cap not in VALID_CAPTURE_METHODS:
                click.echo(
                    f"    [ERROR] idx={idx}: invalid capture_method='{cap}'"
                )
                errors += 1

    click.echo(f"\nValidation: {errors} errors, {warnings} warnings")


if __name__ == "__main__":
    cli()
