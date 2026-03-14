"""Backfill annotation_source field on all 577 L2 JSON records for john11-manuscripts.

The apply script (apply_vlm_annotations_john11.py) set detection_method:
"vlm_contact_sheet_annotation" on ALL images, including the 82 that received
script-average defaults.  This script adds an explicit annotation_source field
so consumers can distinguish VLM-annotated (495) from default-filled (82) records.

Default ranges (no VLM coverage):
  - Arab: idx 60-111  (52 images)
  - Latn: idx 90-119  (30 images)
  Total: 82 defaults

All other scripts/indices are fully VLM-covered.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path("/home/byron/dev/image_detection")
L2_DIR = REPO_ROOT / "metadata_registry/json/john11-manuscripts"
ANNOTATION_INDEX = (
    REPO_ROOT / "data/john11-manuscripts/annotation_sheets/annotation_index.json"
)
BATCH2_JSON = (
    REPO_ROOT / "data/john11-manuscripts/annotation_sheets/vlm_annotations_batch2.json"
)

# ---------------------------------------------------------------------------
# Hardcoded VLM-coverage knowledge
# ---------------------------------------------------------------------------
# Batch2 scripts: ALL images are VLM-covered (0 defaults).
BATCH2_SCRIPTS: frozenset[str] = frozenset(
    ["Copt", "Syrc", "Geor", "Goth", "Cyrs", "Ethi", "Armn"]
)

# Batch3 hardcoded VLM-covered index ranges (see apply script BATCH3_DATA).
#   Grek: idx 0-67   (all 68 images covered)
#   Arab: idx 0-59   (60 covered; 60-111 are defaults → 52 defaults)
#   Latn: idx 0-89 plus 120-176 (147 covered; 90-119 are defaults → 30 defaults)
BATCH3_VLM_RANGES: dict[str, list[tuple[int, int]]] = {
    "Grek": [(0, 67)],
    "Arab": [(0, 59)],
    "Latn": [(0, 89), (120, 176)],
}

# Number of VLM-annotated images used to compute each script default.
# This is the n used in default_computed_from_n.
SCRIPT_DEFAULT_N: dict[str, int] = {
    "Arab": 60,
    "Latn": 90,
}

# ---------------------------------------------------------------------------
# Annotation source payloads
# ---------------------------------------------------------------------------
VLM_ANNOTATION_SOURCE: dict = {
    "method": "vlm_contact_sheet",
    "confidence": 0.75,
    "provenance_tier": "tier_2_model",
    "is_soft_label": True,
    "detection_method": "vlm_contact_sheet_annotation",
}

# Fields on which confidence should be lowered for default-filled records.
# Maps field_name -> (old_confidence, old_detection_method)
DEFAULT_CONFIDENCE_FIELDS: tuple[str, ...] = (
    "quality",
    "structure",
    "capture_method",
)
DEFAULT_LEGIBILITY_FIELD = "handwriting_assessment"
DEFAULT_LEGIBILITY_SUBFIELD = "legibility_confidence"

DEFAULT_DETECTION_METHOD_OLD = "vlm_contact_sheet_annotation"
DEFAULT_DETECTION_METHOD_NEW = "script_default_computation"
OLD_CONFIDENCE = 0.75
LOWERED_CONFIDENCE = 0.5
OLD_STRUCTURE_CONFIDENCE = 0.7
OLD_CAPTURE_CONFIDENCE = 0.7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_idx_to_sample_id(index_data: dict) -> dict[str, dict[int, str]]:
    """Return {script: {idx: sample_id}} mapping from annotation_index.json."""
    result: dict[str, dict[int, str]] = {}
    for script, sheets in index_data.items():
        script_map: dict[int, str] = {}
        for _sheet_num, entries in sheets.items():
            for entry in entries:
                script_map[entry["idx"]] = entry["sample_id"]
        result[script] = script_map
    return result


def _is_vlm_covered(script: str, idx: int) -> bool:
    """Return True when image at idx for script was annotated by VLM."""
    if script in BATCH2_SCRIPTS:
        return True
    ranges = BATCH3_VLM_RANGES.get(script)
    if ranges is None:
        # Unknown script — assume VLM-covered (conservative)
        return True
    for lo, hi in ranges:
        if lo <= idx <= hi:
            return True
    return False


def _build_default_annotation_source(script: str) -> dict:
    """Build annotation_source payload for a default-filled image."""
    n = SCRIPT_DEFAULT_N.get(script, 0)
    return {
        "method": "script_default",
        "default_computed_from_n": n,
        "confidence": 0.5,
        "provenance_tier": "tier_3_heuristic",
        "is_soft_label": True,
        "detection_method": "script_default_computation",
    }


def _patch_default_record(data_section: dict) -> int:
    """Lower confidence and fix detection_method on a default record.

    Returns number of fields mutated (for reporting).
    """
    mutations = 0

    for field_name in DEFAULT_CONFIDENCE_FIELDS:
        field = data_section.get(field_name)
        if field is None:
            continue
        if field.get("detection_method") == DEFAULT_DETECTION_METHOD_OLD:
            field["detection_method"] = DEFAULT_DETECTION_METHOD_NEW
            mutations += 1
        # Lower confidence regardless — these were written by the apply script
        # at VLM confidence levels but came from script defaults.
        old_conf = field.get("confidence")
        if old_conf is not None and old_conf > LOWERED_CONFIDENCE:
            field["confidence"] = LOWERED_CONFIDENCE
            mutations += 1

    # handwriting_assessment.legibility_confidence
    hw = data_section.get(DEFAULT_LEGIBILITY_FIELD)
    if hw is not None:
        old_leg = hw.get(DEFAULT_LEGIBILITY_SUBFIELD)
        if old_leg is not None and old_leg > LOWERED_CONFIDENCE:
            hw[DEFAULT_LEGIBILITY_SUBFIELD] = LOWERED_CONFIDENCE
            mutations += 1

    return mutations


# ---------------------------------------------------------------------------
# Core backfill logic
# ---------------------------------------------------------------------------


def _compute_default_sample_ids(
    idx_to_sample_id: dict[str, dict[int, str]],
) -> set[str]:
    """Return the set of sample_ids that are script-default (not VLM-covered)."""
    default_ids: set[str] = set()
    for script, idx_map in idx_to_sample_id.items():
        for idx, sample_id in idx_map.items():
            if not _is_vlm_covered(script, idx):
                default_ids.add(sample_id)
    return default_ids


def _script_for_sample_id(
    idx_to_sample_id: dict[str, dict[int, str]],
    sample_id: str,
) -> str | None:
    """Return the script name for a given sample_id, or None if not found."""
    for script, idx_map in idx_to_sample_id.items():
        if sample_id in idx_map.values():
            return script
    return None


def run_backfill(dry_run: bool) -> dict[str, int]:
    """Execute the backfill, returning summary counts."""
    index_data = json.loads(ANNOTATION_INDEX.read_text(encoding="utf-8"))
    idx_to_sample_id = _build_idx_to_sample_id(index_data)
    default_ids = _compute_default_sample_ids(idx_to_sample_id)

    l2_files = sorted(L2_DIR.glob("*.json"))
    total = len(l2_files)
    vlm_count = 0
    default_count = 0
    already_set = 0
    errors: list[str] = []

    for l2_path in l2_files:
        try:
            record = json.loads(l2_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{l2_path.name}: read error — {exc}")
            continue

        sample_id = record.get("sample_id", l2_path.stem)
        data_section = record.get("data", {})

        if "annotation_source" in data_section:
            already_set += 1
            continue

        is_default = sample_id in default_ids

        if is_default:
            script = _script_for_sample_id(idx_to_sample_id, sample_id)
            annotation_source = _build_default_annotation_source(script or "")
        else:
            annotation_source = dict(VLM_ANNOTATION_SOURCE)

        data_section["annotation_source"] = annotation_source

        if is_default:
            _patch_default_record(data_section)
            default_count += 1
        else:
            vlm_count += 1

        if not dry_run:
            l2_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    return {
        "total": total,
        "vlm": vlm_count,
        "default": default_count,
        "already_set": already_set,
        "errors": len(errors),
        "_error_details": errors,
    }


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def run_validate() -> dict[str, int | list[str]]:
    """Verify all 577 records have annotation_source and counts match."""
    l2_files = sorted(L2_DIR.glob("*.json"))
    total = len(l2_files)
    missing: list[str] = []
    vlm_count = 0
    default_count = 0
    unknown_method: list[str] = []

    for l2_path in l2_files:
        try:
            record = json.loads(l2_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            missing.append(f"{l2_path.name}: unreadable — {exc}")
            continue

        data_section = record.get("data", {})
        src = data_section.get("annotation_source")

        if src is None:
            missing.append(l2_path.stem)
            continue

        method = src.get("method")
        if method == "vlm_contact_sheet":
            vlm_count += 1
        elif method == "script_default":
            default_count += 1
        else:
            unknown_method.append(f"{l2_path.stem}: method={method!r}")

    return {
        "total": total,
        "vlm": vlm_count,
        "default": default_count,
        "missing_annotation_source": len(missing),
        "unknown_method": len(unknown_method),
        "_missing_details": missing,
        "_unknown_details": unknown_method,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """Backfill annotation_source on john11-manuscripts L2 records."""


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview changes without writing files.",
)
def backfill(dry_run: bool) -> None:
    """Add annotation_source to all 577 L2 JSON records.

    VLM-annotated images (495) receive method=vlm_contact_sheet.
    Default-filled images (82) receive method=script_default plus lowered
    confidence values on quality, structure, capture_method and
    handwriting_assessment.legibility_confidence.
    """
    if dry_run:
        click.echo("DRY RUN — no files will be written.")

    click.echo(f"L2 directory : {L2_DIR}")
    click.echo(f"Annotation index: {ANNOTATION_INDEX}")

    stats = run_backfill(dry_run=dry_run)

    click.echo("")
    click.echo("Results")
    click.echo("-------")
    click.echo(f"  Total L2 files   : {stats['total']}")
    click.echo(f"  VLM annotated    : {stats['vlm']}")
    click.echo(f"  Script defaults  : {stats['default']}")
    click.echo(f"  Already had field: {stats['already_set']}")
    click.echo(f"  Errors           : {stats['errors']}")

    if stats["_error_details"]:
        click.echo("\nErrors encountered:")
        for err in stats["_error_details"]:
            click.echo(f"  {err}")

    total_processed = stats["vlm"] + stats["default"]
    expected = 577 - stats["already_set"]
    if total_processed == expected and stats["errors"] == 0:
        action = "Would write" if dry_run else "Wrote"
        click.echo(
            f"\n{action} {total_processed} records (495 VLM + 82 defaults expected)."
        )
        if stats["vlm"] != 495 or stats["default"] != 82:
            click.echo(
                f"  WARNING: expected 495 VLM + 82 defaults, "
                f"got {stats['vlm']} VLM + {stats['default']} defaults."
            )
    else:
        click.echo(
            f"\nWARNING: processed {total_processed} but expected {expected}.",
            err=True,
        )
        sys.exit(1)


@cli.command()
def validate() -> None:
    """Verify all 577 records have annotation_source and counts are correct.

    Expected: 495 vlm_contact_sheet + 82 script_default = 577 total.
    """
    click.echo(f"Validating {L2_DIR}")
    stats = run_validate()

    click.echo("")
    click.echo("Validation Results")
    click.echo("------------------")
    click.echo(f"  Total files              : {stats['total']}")
    click.echo(f"  vlm_contact_sheet        : {stats['vlm']}")
    click.echo(f"  script_default           : {stats['default']}")
    click.echo(f"  Missing annotation_source: {stats['missing_annotation_source']}")
    click.echo(f"  Unknown method           : {stats['unknown_method']}")

    if stats["_missing_details"]:
        click.echo("\nMissing annotation_source:")
        for item in stats["_missing_details"][:20]:
            click.echo(f"  {item}")
        if len(stats["_missing_details"]) > 20:
            click.echo(f"  ... and {len(stats['_missing_details']) - 20} more")

    if stats["_unknown_details"]:
        click.echo("\nUnknown method values:")
        for item in stats["_unknown_details"]:
            click.echo(f"  {item}")

    passed = (
        stats["total"] == 577
        and stats["vlm"] == 495
        and stats["default"] == 82
        and stats["missing_annotation_source"] == 0
        and stats["unknown_method"] == 0
    )

    if passed:
        click.echo("\nPASSED: all 577 records valid (495 VLM + 82 defaults).")
    else:
        click.echo("\nFAILED: validation did not pass expected counts.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
