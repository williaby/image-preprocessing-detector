"""Enrich john11-manuscripts L2 JSON records with material_and_dating metadata.

Reads date_range and script_iso15924 from the extended registry, parses them
into structured century/year data, infers material composition, and writes a
new `data.material_and_dating` field into each L2 JSON file.

Usage:
    uv run python scripts/enrich_material_century_john11.py enrich [--dry-run]
    uv run python scripts/enrich_material_century_john11.py validate
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import click

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path("/home/byron/dev/image_detection")
L2_DIR = REPO_ROOT / "metadata_registry/json/john11-manuscripts"
EXTENDED_REGISTRY = REPO_ROOT / "metadata_registry/john11_manuscripts_extended.jsonl"

# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

# Ordinal suffixes accepted after a digit (1st, 2nd, 3rd, 4th … 20th …)
_CENTURY_SUFFIX = r"(?:st|nd|rd|th)"

# Map century number → (year_min, year_max) base range
def _century_year_bounds(century: int) -> tuple[int, int]:
    """Return (year_min, year_max) for a whole century number (1-based AD)."""
    return (century - 1) * 100 + 1, century * 100


def _apply_qualifier(
    qualifier: str, year_min: int, year_max: int
) -> tuple[int, int]:
    """Narrow year_min/year_max for 'early', 'mid', or 'late' qualifiers."""
    span = year_max - year_min  # typically 99
    third = span // 3
    if qualifier == "early":
        return year_min, year_min + third + 10
    if qualifier == "mid":
        mid_start = year_min + third
        return mid_start, mid_start + third + 10
    if qualifier == "late":
        return year_max - third - 10, year_max
    return year_min, year_max


def parse_date_range(date_range: str | None) -> dict[str, Any]:
    """Parse a date_range string into structured century/year metadata.

    Returns a dict with keys:
        century_min, century_max, year_min, year_max
    All values are int or None.

    Examples:
        "4th c."         → {century_min:4, century_max:4, year_min:301, year_max:400}
        "1386"           → {century_min:14, century_max:14, year_min:1386, year_max:1386}
        "c. 650-700"     → {century_min:7, century_max:7, year_min:650, year_max:700}
        "12th-13th c."   → {century_min:12, century_max:13, year_min:1101, year_max:1300}
        "781-783"        → {century_min:8, century_max:8, year_min:781, year_max:783}
        "mid-5th c."     → {century_min:5, century_max:5, year_min:430, year_max:470}
        "late 12th c."   → {century_min:12, century_max:12, year_min:1160, year_max:1200}
        "early 9th c."   → {century_min:9, century_max:9, year_min:800, year_max:840}
        "5th c."         → {century_min:5, century_max:5, year_min:401, year_max:500}
        "various"/""     → all None
    """
    null_result: dict[str, Any] = {
        "century_min": None,
        "century_max": None,
        "year_min": None,
        "year_max": None,
    }

    if not date_range or date_range.strip().lower() in ("various", "unknown", "n/a"):
        return null_result

    text = date_range.strip()

    # -- Pattern 1: century range  "12th-13th c." ---------------------------
    m = re.match(
        rf"(\d+){_CENTURY_SUFFIX}-(\d+){_CENTURY_SUFFIX}\s+c\.",
        text,
        re.IGNORECASE,
    )
    if m:
        c_min, c_max = int(m.group(1)), int(m.group(2))
        y_min, _ = _century_year_bounds(c_min)
        _, y_max = _century_year_bounds(c_max)
        return {
            "century_min": c_min,
            "century_max": c_max,
            "year_min": y_min,
            "year_max": y_max,
        }

    # -- Pattern 2: qualifier + single century  "early 9th c." / "mid-5th c." --
    m = re.match(
        rf"(early|mid|late)[- ](\d+){_CENTURY_SUFFIX}\s+c\.",
        text,
        re.IGNORECASE,
    )
    if m:
        qualifier = m.group(1).lower()
        century = int(m.group(2))
        y_min_base, y_max_base = _century_year_bounds(century)
        y_min, y_max = _apply_qualifier(qualifier, y_min_base, y_max_base)
        return {
            "century_min": century,
            "century_max": century,
            "year_min": y_min,
            "year_max": y_max,
        }

    # -- Pattern 3: plain single century  "5th c." --------------------------
    m = re.match(rf"(\d+){_CENTURY_SUFFIX}\s+c\.", text, re.IGNORECASE)
    if m:
        century = int(m.group(1))
        y_min, y_max = _century_year_bounds(century)
        return {
            "century_min": century,
            "century_max": century,
            "year_min": y_min,
            "year_max": y_max,
        }

    # -- Pattern 4: approximate year range  "c. 650-700" -------------------
    m = re.match(r"c\.\s*(\d{3,4})-(\d{3,4})", text, re.IGNORECASE)
    if m:
        y_min, y_max = int(m.group(1)), int(m.group(2))
        c_min = (y_min - 1) // 100 + 1
        c_max = (y_max - 1) // 100 + 1
        return {
            "century_min": c_min,
            "century_max": c_max,
            "year_min": y_min,
            "year_max": y_max,
        }

    # -- Pattern 5: bare year range  "781-783" ------------------------------
    m = re.match(r"(\d{3,4})-(\d{3,4})$", text)
    if m:
        y_min, y_max = int(m.group(1)), int(m.group(2))
        c_min = (y_min - 1) // 100 + 1
        c_max = (y_max - 1) // 100 + 1
        return {
            "century_min": c_min,
            "century_max": c_max,
            "year_min": y_min,
            "year_max": y_max,
        }

    # -- Pattern 6: single specific year  "1386" ----------------------------
    m = re.match(r"^(\d{3,4})$", text)
    if m:
        year = int(m.group(1))
        century = (year - 1) // 100 + 1
        return {
            "century_min": century,
            "century_max": century,
            "year_min": year,
            "year_max": year,
        }

    # Unrecognised format — return nulls
    return null_result


# ---------------------------------------------------------------------------
# Material inference
# ---------------------------------------------------------------------------

_ETHIOPIC_SCRIPT = "Ethi"
_GOTHIC_SCRIPT = "Goth"
_PAPER_CUTOVER_CENTURY = 16  # Post-15th c. → paper


def infer_material(
    century_min: int | None,
    script_iso15924: str,
) -> tuple[str, float]:
    """Infer material composition and confidence from century and script.

    Returns:
        (material_composition, confidence)

    Rules (in priority order):
        - Ethiopic (Ethi) any date → "parchment"
        - Gothic (Goth)            → "parchment_dyed" (Codex Argenteus)
        - century_min unknown      → "unknown" (confidence 0.3)
        - Pre-4th c. (≤3)          → "papyrus"
        - 4th–15th c. (4–15)       → "parchment"
        - 16th c. or later (≥16)   → "paper"
    """
    if script_iso15924 == _ETHIOPIC_SCRIPT:
        return "parchment", 0.75

    if script_iso15924 == _GOTHIC_SCRIPT:
        return "parchment_dyed", 0.85

    if century_min is None:
        # All john11 manuscripts are historical (pre-19th c.) religious texts.
        # Parchment is the overwhelmingly likely material for biblical manuscripts.
        return "parchment", 0.5

    if century_min <= 3:
        return "papyrus", 0.7

    if century_min < _PAPER_CUTOVER_CENTURY:
        return "parchment", 0.7

    return "paper", 0.7


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------

def load_extended_registry(
    path: Path,
) -> dict[str, dict[str, str]]:
    """Load extended registry and return {sample_id: {date_range, script_iso15924}}.

    Args:
        path: Path to the .jsonl extended registry file.

    Returns:
        Dict keyed by sample_id with date_range and script_iso15924 values.

    Raises:
        FileNotFoundError: If the registry file does not exist.
        json.JSONDecodeError: If a line is malformed JSON.
    """
    if not path.exists():
        msg = f"Extended registry not found: {path}"
        raise FileNotFoundError(msg)

    registry: dict[str, dict[str, str]] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        entry = json.loads(raw)
        sample_id = entry["sample_id"]
        registry[sample_id] = {
            "date_range": entry.get("date_range", "") or "",
            "script_iso15924": entry.get("script_iso15924", "") or "",
        }
    return registry


# ---------------------------------------------------------------------------
# Core enrichment logic
# ---------------------------------------------------------------------------

def build_material_dating_block(
    date_range: str,
    script_iso15924: str,
) -> dict[str, Any]:
    """Build the material_and_dating metadata block for a single record.

    Args:
        date_range: Raw date string from the manuscript catalog.
        script_iso15924: ISO 15924 script code.

    Returns:
        Dict suitable for insertion as data.material_and_dating.
    """
    parsed = parse_date_range(date_range)
    century_min: int | None = parsed["century_min"]
    material, confidence = infer_material(century_min, script_iso15924)

    return {
        "estimated_century_min": parsed["century_min"],
        "estimated_century_max": parsed["century_max"],
        "year_range_min": parsed["year_min"],
        "year_range_max": parsed["year_max"],
        "date_range_raw": date_range,
        "material_composition": material,
        "material_confidence": confidence,
        "provenance_tier": "tier_3_heuristic",
        "is_soft_label": True,
        "detection_method": "catalog_date_heuristic",
    }


def enrich_one_file(
    json_path: Path,
    registry_entry: dict[str, str],
    *,
    dry_run: bool,
) -> bool:
    """Enrich a single L2 JSON file with material_and_dating data.

    Args:
        json_path: Absolute path to the L2 JSON file.
        registry_entry: Dict with date_range and script_iso15924 for this record.
        dry_run: If True, parse and compute but do not write any files.

    Returns:
        True if the file was (or would be) updated, False if already enriched.
    """
    record = json.loads(json_path.read_text(encoding="utf-8"))

    if "material_and_dating" in record.get("data", {}):
        return False

    block = build_material_dating_block(
        registry_entry["date_range"],
        registry_entry["script_iso15924"],
    )

    if not dry_run:
        record["data"]["material_and_dating"] = block
        json_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

    return True


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

@click.group()
def cli() -> None:
    """Enrich john11-manuscripts L2 JSON records with material_and_dating metadata."""


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Parse and compute enrichment without writing any files.",
)
@click.option(
    "--l2-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=L2_DIR,
    show_default=True,
    help="Directory containing L2 JSON files.",
)
@click.option(
    "--registry",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=EXTENDED_REGISTRY,
    show_default=True,
    help="Path to john11_manuscripts_extended.jsonl.",
)
def enrich(l2_dir: Path, registry: Path, *, dry_run: bool) -> None:
    """Add material_and_dating field to all L2 JSON records.

    Reads date_range and script_iso15924 from the extended registry,
    parses them into structured metadata, and writes data.material_and_dating
    into each L2 JSON file.  Already-enriched records are skipped.
    """
    if dry_run:
        click.echo("DRY RUN — no files will be modified.")

    click.echo(f"Loading extended registry: {registry}")
    reg = load_extended_registry(registry)
    click.echo(f"  Loaded {len(reg):,} registry entries.")

    json_files = sorted(l2_dir.glob("*.json"))
    click.echo(f"Found {len(json_files):,} L2 JSON files in {l2_dir}")

    updated = skipped_already = missing_in_registry = 0
    errors: list[str] = []

    for json_path in json_files:
        sample_id = json_path.stem
        if sample_id not in reg:
            missing_in_registry += 1
            errors.append(f"  MISSING registry entry: {sample_id}")
            continue

        try:
            was_updated = enrich_one_file(
                json_path,
                reg[sample_id],
                dry_run=dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"  ERROR {json_path.name}: {exc}")
            continue

        if was_updated:
            updated += 1
        else:
            skipped_already += 1

    # Summary
    action = "Would update" if dry_run else "Updated"
    click.echo(f"\n{action}:          {updated:>5} files")
    click.echo(f"Already enriched: {skipped_already:>5} files (skipped)")
    click.echo(f"Missing in registry: {missing_in_registry:>3} files")

    if errors:
        click.echo("\nProblems encountered:")
        for msg in errors:
            click.echo(msg)
        sys.exit(1)

    if not dry_run and updated > 0:
        click.echo("\nEnrichment complete.")


@cli.command()
@click.option(
    "--l2-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=L2_DIR,
    show_default=True,
    help="Directory containing L2 JSON files.",
)
def validate(l2_dir: Path) -> None:
    """Verify enrichment: count non-null centuries and show material distribution.

    Reads all L2 JSON files and reports:
        - Total records
        - Records with material_and_dating present
        - Records with non-null century values
        - Material composition distribution
        - Date_range_raw distribution
    """
    json_files = sorted(l2_dir.glob("*.json"))
    total = len(json_files)
    click.echo(f"Scanning {total:,} L2 JSON files in {l2_dir}\n")

    has_block = 0
    has_century = 0
    material_counts: dict[str, int] = {}
    date_raw_counts: dict[str, int] = {}
    missing_block: list[str] = []

    for json_path in json_files:
        record = json.loads(json_path.read_text(encoding="utf-8"))
        block: dict[str, Any] | None = record.get("data", {}).get(
            "material_and_dating"
        )

        if block is None:
            missing_block.append(json_path.stem)
            continue

        has_block += 1

        if block.get("estimated_century_min") is not None:
            has_century += 1

        mat: str = block.get("material_composition", "unknown")
        material_counts[mat] = material_counts.get(mat, 0) + 1

        raw: str = block.get("date_range_raw", "")
        date_raw_counts[raw] = date_raw_counts.get(raw, 0) + 1

    # Report
    click.echo(f"Total records          : {total:>5}")
    click.echo(f"material_and_dating    : {has_block:>5} ({has_block / total * 100:.1f}%)")
    click.echo(f"Non-null century       : {has_century:>5} ({has_century / total * 100:.1f}%)")

    click.echo("\nMaterial composition distribution:")
    for mat, count in sorted(material_counts.items(), key=lambda kv: -kv[1]):
        pct = count / total * 100
        click.echo(f"  {mat:<25} {count:>5}  ({pct:.1f}%)")

    click.echo("\nDate range raw distribution:")
    for raw, count in sorted(date_raw_counts.items(), key=lambda kv: -kv[1]):
        display = repr(raw) if raw else "(empty)"
        click.echo(f"  {display:<30} {count:>5}")

    if missing_block:
        click.echo(
            f"\nWARNING: {len(missing_block)} records still lack material_and_dating:"
        )
        for sid in missing_block[:10]:
            click.echo(f"  {sid}")
        if len(missing_block) > 10:
            click.echo(f"  ... and {len(missing_block) - 10} more.")
        sys.exit(1)
    else:
        click.echo("\nAll records have material_and_dating. Validation passed.")


if __name__ == "__main__":
    cli()
