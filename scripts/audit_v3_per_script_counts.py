#!/usr/bin/env python3
"""Audit per-script image counts in synth-multiscript-v3 GCS bucket.

Reads splits.jsonl to count images per ISO 15924 script code,
then compares against the target distribution.  Generates a resume-point
JSON file that the generator can use to skip already-complete scripts.

Usage:
    python scripts/audit_v3_per_script_counts.py [OPTIONS]

Options:
    --splits-jsonl PATH      Path to splits.jsonl file (local) [default: auto-detect]
    --gcs-path TEXT          GCS bucket path to list [default: gs://image_detection_b/synth_multiscript_v3/]
    --output PATH            Output JSON path [default: results/v3_per_script_audit.json]
    --expected-per-script INT  Expected images per script [default: 12963]
    --tolerance FLOAT        Acceptable fractional deviation from expected [default: 0.05]
    --verify                 Run verification check (exit 0 if all scripts at target)
    --use-splits-jsonl / --no-use-splits-jsonl
                             Count from local splits.jsonl instead of GCS listing
                             (faster, no GCS access) [default: True]

Notes:
    - Default mode reads splits.jsonl locally (fast, no GCS credentials needed).
    - GCS listing mode requires gsutil to be configured.
    - The --output JSON is consumed by generate_base_dataset_v3.py
      --resume-from-audit when that flag is implemented.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import click

DEFAULT_GCS_PATH = "gs://image_detection_b/synth_multiscript_v3/"
DEFAULT_TOTAL = 350_000
DEFAULT_NUM_SCRIPTS = 27
# Floor division: 350_000 // 27 = 12_962 with 26 scripts getting +1 = 12_963
DEFAULT_PER_SCRIPT = DEFAULT_TOTAL // DEFAULT_NUM_SCRIPTS  # 12,962

# Known script codes in v3 (27 scripts, Mongolian excluded as OOD candidate)
V3_SCRIPTS: list[str] = [
    "Latn", "Arab", "Deva", "Hans", "Hant", "Cyrl", "Jpan", "Hang",
    "Thai", "Beng", "Gujr", "Guru", "Knda", "Mlym", "Orya", "Taml",
    "Telu", "Tibt", "Mymr", "Khmr", "Sinh", "Laoo", "Cher", "Cans",
    "Ethi", "Geor", "Hebr",
]

# Candidate locations for splits.jsonl, checked in order
_SPLITS_JSONL_CANDIDATES: list[Path] = [
    Path("metadata_registry/splits.jsonl"),
    Path("/mnt/e/image_detection/metadata_registry/splits.jsonl"),
    Path(
        "/mnt/e/image_detection/03_training_datasets"
        "/synthetic_multiscript_v3/splits.jsonl"
    ),
    Path("data/synth_multiscript_v3/splits.jsonl"),
]

# Field names tried in order when extracting the script code from a JSONL entry
_SCRIPT_FIELD_CANDIDATES: tuple[str, ...] = (
    "script",
    "script_code",
    "ml_class",
)


def _extract_script_from_entry(entry: dict[str, object]) -> str:
    """Extract the ISO 15924 script code from a splits.jsonl entry.

    Tries top-level fields first, then the nested label dict.

    Args:
        entry: Parsed JSON object from splits.jsonl.

    Returns:
        Script code string, or "UNKNOWN" if not found.
    """
    for field in _SCRIPT_FIELD_CANDIDATES:
        value = entry.get(field)
        if isinstance(value, str) and value:
            return value

    # Nested label dict (e.g. {"label": {"script": "Latn"}})
    label = entry.get("label")
    if isinstance(label, dict):
        nested = label.get("script")
        if isinstance(nested, str) and nested:
            return nested

    # source_path encodes the script as its parent directory
    # e.g. /mnt/.../synth_multiscript_v3/Cyrl/uuid.jpg  → "Cyrl"
    source_path = entry.get("source_path")
    if isinstance(source_path, str) and source_path:
        parent = Path(source_path).parent.name
        if parent and parent != "synth_multiscript_v3":
            return parent

    return "UNKNOWN"


def _count_from_splits_jsonl(splits_jsonl_path: Path) -> dict[str, int]:
    """Count images per script from a local splits.jsonl file.

    Args:
        splits_jsonl_path: Path to the splits.jsonl file.

    Returns:
        Dict mapping script code to image count.

    Raises:
        FileNotFoundError: If splits.jsonl is not found at the given path.
    """
    if not splits_jsonl_path.exists():
        raise FileNotFoundError(f"splits.jsonl not found: {splits_jsonl_path}")

    counts: dict[str, int] = defaultdict(int)
    total = 0
    parse_errors = 0

    click.echo(f"Reading {splits_jsonl_path}...", err=True)
    with splits_jsonl_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry: dict[str, object] = json.loads(line)
                script = _extract_script_from_entry(entry)
                counts[script] += 1
                total += 1
            except json.JSONDecodeError:
                parse_errors += 1

    click.echo(f"Total entries  : {total:,}", err=True)
    if parse_errors:
        click.echo(f"Parse errors   : {parse_errors:,}", err=True)
    return dict(counts)


def _count_from_gcs(gcs_path: str) -> dict[str, int]:
    """Count images per script by listing a GCS bucket path.

    Parses the ISO 15924 script code from the parent directory name, which
    follows the output structure: ``{output_dir}/{ScriptCode}/{sample_id}.jpg``.

    Args:
        gcs_path: GCS path to list (e.g. ``gs://bucket/prefix/``).

    Returns:
        Dict mapping script code to image count.
    """
    click.echo(f"Listing GCS path: {gcs_path} (this may take several minutes)...", err=True)
    try:
        result = subprocess.run(
            ["gsutil", "ls", "-r", gcs_path],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        click.echo("gsutil ls timed out after 10 minutes.", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo(
            "gsutil not found.  Install Google Cloud SDK or use --use-splits-jsonl.",
            err=True,
        )
        sys.exit(1)

    if result.returncode != 0:
        click.echo(f"gsutil ls failed: {result.stderr}", err=True)
        sys.exit(1)

    counts: dict[str, int] = defaultdict(int)
    known_lower = {s.lower(): s for s in V3_SCRIPTS}

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.endswith(":"):
            # gsutil -r prints directory headers ending with ":"
            continue
        # Directory structure: .../ScriptCode/sample_id.jpg
        parts = Path(line).parts
        # Walk from the end; the parent dir of the file is the script dir
        if len(parts) >= 2:
            candidate = parts[-2]
            canonical = known_lower.get(candidate.lower())
            if canonical:
                counts[canonical] += 1
            else:
                counts["UNKNOWN"] += 1

    return dict(counts)


def _find_splits_jsonl() -> Path | None:
    """Auto-detect the splits.jsonl location from known candidate paths."""
    for candidate in _SPLITS_JSONL_CANDIDATES:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            # Drive not mounted (e.g. /mnt/e not available in WSL)
            continue
    return None


def _build_resume_data(
    counts: dict[str, int],
    expected_per_script: int,
    tolerance: float,
    source: str,
) -> dict[str, object]:
    """Build the resume-point JSON consumed by the generator.

    Args:
        counts: Per-script image counts from the audit.
        expected_per_script: Target images per script.
        tolerance: Acceptable fractional deviation (e.g. 0.05 = ±5%).
        source: How counts were obtained ("splits_jsonl" or "gcs_listing").

    Returns:
        Dict ready for JSON serialisation.
    """
    lower_bound = int(expected_per_script * (1 - tolerance))
    total = sum(counts.values())
    target_total = expected_per_script * len(V3_SCRIPTS)

    per_script: dict[str, dict[str, object]] = {}
    for script in V3_SCRIPTS:
        found = counts.get(script, 0)
        per_script[script] = {
            "found": found,
            "target": expected_per_script,
            "remaining": max(0, expected_per_script - found),
            "done": found >= lower_bound,
        }

    return {
        "audit_total": total,
        "target_total": target_total,
        "target_per_script": expected_per_script,
        "tolerance": tolerance,
        "per_script": per_script,
        "scripts_needing_generation": [
            script for script in V3_SCRIPTS if counts.get(script, 0) < lower_bound
        ],
        "source": source,
    }


@click.command()
@click.option(
    "--splits-jsonl",
    "splits_jsonl_path",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Path to splits.jsonl. Auto-detected if not provided.",
)
@click.option(
    "--gcs-path",
    default=DEFAULT_GCS_PATH,
    show_default=True,
    help="GCS path to list images from (used when --no-use-splits-jsonl).",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("results/v3_per_script_audit.json"),
    show_default=True,
    help="Output JSON path for resume-point data.",
)
@click.option(
    "--expected-per-script",
    default=DEFAULT_PER_SCRIPT,
    show_default=True,
    help="Expected images per script.",
)
@click.option(
    "--tolerance",
    default=0.05,
    show_default=True,
    help="Acceptable fractional deviation from expected (0.05 = ±5%).",
)
@click.option(
    "--verify",
    is_flag=True,
    default=False,
    help="Exit 0 if all scripts are at target; exit 1 otherwise.",
)
@click.option(
    "--use-splits-jsonl/--no-use-splits-jsonl",
    default=True,
    show_default=True,
    help="Count from local splits.jsonl (faster) instead of GCS listing.",
)
def main(
    splits_jsonl_path: Path | None,
    gcs_path: str,
    output: Path,
    expected_per_script: int,
    tolerance: float,
    verify: bool,
    use_splits_jsonl: bool,
) -> None:
    """Audit per-script image counts in synth-multiscript-v3."""
    # Obtain counts
    if use_splits_jsonl:
        if splits_jsonl_path is None:
            splits_jsonl_path = _find_splits_jsonl()
        if splits_jsonl_path is None or not splits_jsonl_path.exists():
            click.echo(
                "splits.jsonl not found.  Provide --splits-jsonl or use "
                "--no-use-splits-jsonl for GCS listing mode.",
                err=True,
            )
            sys.exit(1)
        counts = _count_from_splits_jsonl(splits_jsonl_path)
        source = "splits_jsonl"
    else:
        counts = _count_from_gcs(gcs_path)
        source = "gcs_listing"

    total = sum(counts.values())
    target_total = expected_per_script * len(V3_SCRIPTS)
    lower_bound = int(expected_per_script * (1 - tolerance))
    upper_bound = int(expected_per_script * (1 + tolerance))

    # Print table
    click.echo(f"\n{'Script':<8} {'Found':>10} {'Target':>10} {'Delta':>8}  Status")
    click.echo("-" * 56)

    below_target: list[str] = []
    above_target: list[str] = []

    for script in V3_SCRIPTS:
        count = counts.get(script, 0)
        delta = count - expected_per_script
        if count < lower_bound:
            status = "BELOW"
            below_target.append(script)
        elif count > upper_bound:
            status = "ABOVE"
            above_target.append(script)
        else:
            status = "OK"
        click.echo(
            f"{script:<8} {count:>10,} {expected_per_script:>10,} {delta:>+8,}  {status}"
        )

    unknown_count = counts.get("UNKNOWN", 0)
    if unknown_count:
        click.echo(f"{'UNKNOWN':<8} {unknown_count:>10,} {'':>10} {'':>8}  (unclassified)")

    click.echo(f"\nTotal images : {total:,} / {target_total:,} target")
    click.echo(f"Below target : {len(below_target)} — {below_target}")
    click.echo(f"Above target : {len(above_target)} — {above_target}")

    # Write resume-point JSON
    resume_data = _build_resume_data(counts, expected_per_script, tolerance, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        json.dump(resume_data, fh, indent=2)
    click.echo(f"\nResume-point data written to: {output}")

    # Verification mode
    if verify:
        if below_target:
            click.echo(
                f"\nVERIFICATION FAILED: {len(below_target)} scripts below target.",
                err=True,
            )
            sys.exit(1)
        click.echo(
            f"\nVERIFICATION PASSED: All {len(V3_SCRIPTS)} scripts at target.", err=True
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
