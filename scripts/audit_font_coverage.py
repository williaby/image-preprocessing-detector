#!/usr/bin/env python3
"""Audit font coverage per script for synth-multiscript generation.

Scans font directories and reports per-script font family counts.
Exits non-zero if any script is below the minimum family threshold.

Usage:
    python scripts/audit_font_coverage.py [OPTIONS]

Options:
    --fonts-dir PATH    Directory containing font files [default: fonts/synthetic-gen/]
    --scripts TEXT      Comma-separated ISO 15924 script codes to check
                        [default: all 27 scripts in synth-multiscript-v3]
    --min-families INT  Minimum font families required per script [default: 5]
    --fail-below        Exit with code 1 if any script is below --min-families
    --json              Output results as JSON instead of table
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import click

# ISO 15924 codes for the 27 scripts in synth-multiscript-v3
# (Mongolian / Mong is explicitly ABSENT — OOD candidate)
V3_SCRIPTS: list[str] = [
    "Latn",
    "Arab",
    "Deva",
    "Hans",
    "Hant",
    "Cyrl",
    "Jpan",
    "Hang",
    "Thai",
    "Beng",
    "Gujr",
    "Guru",
    "Knda",
    "Mlym",
    "Orya",
    "Taml",
    "Telu",
    "Tibt",
    "Mymr",
    "Khmr",
    "Sinh",
    "Laoo",
    "Cher",
    "Cans",
    "Ethi",
    "Geor",
    "Hebr",
]

# Map ISO 15924 codes to common font naming patterns used in font filenames.
# Allows heuristic assignment of font files to scripts based on filename substrings.
SCRIPT_FONT_PATTERNS: dict[str, list[str]] = {
    "Latn": ["latin", "roman", "serif", "sans", "mono", "noto-latin", "liberation"],
    "Arab": ["arabic", "arab", "scheherazade", "amiri", "lateef", "reem"],
    "Deva": ["devanagari", "deva", "noto-deva", "mangal", "sanskrit"],
    "Hans": ["cjk", "chinese", "simplified", "hans", "noto-sc", "wqy"],
    "Hant": ["cjk", "chinese", "traditional", "hant", "noto-tc"],
    "Cyrl": ["cyrillic", "cyrl", "slavic", "russian"],
    "Jpan": ["japanese", "jpan", "noto-jp", "ipafont", "noto-cjk"],
    "Hang": ["korean", "hang", "noto-kr", "nanum"],
    "Thai": ["thai", "noto-thai", "thsarabun"],
    "Beng": ["bengali", "beng", "noto-beng", "vrinda"],
    "Gujr": ["gujarati", "gujr", "noto-gujr"],
    "Guru": ["gurmukhi", "guru", "noto-guru"],
    "Knda": ["kannada", "knda", "noto-knda"],
    "Mlym": ["malayalam", "mlym", "noto-mlym"],
    "Orya": ["oriya", "odia", "orya", "noto-orya"],
    "Taml": ["tamil", "taml", "noto-taml", "latha"],
    "Telu": ["telugu", "telu", "noto-telu"],
    "Tibt": ["tibetan", "tibt", "noto-tibt", "jomolhari"],
    "Mymr": ["myanmar", "mymr", "noto-mymr", "padauk"],
    "Khmr": ["khmer", "khmr", "noto-khmr", "busra"],
    "Sinh": ["sinhala", "sinh", "noto-sinh", "iskpota"],
    "Laoo": ["lao", "laoo", "noto-lao"],
    "Cher": ["cherokee", "cher", "noto-cher"],
    "Cans": ["aboriginal", "cans", "syllabics", "noto-cans"],
    "Ethi": ["ethiopic", "ethi", "noto-ethi"],
    "Geor": ["georgian", "geor", "noto-geor", "bpg"],
    "Hebr": ["hebrew", "hebr", "noto-hebr", "david", "frank"],
}

# System font paths to also check alongside the project fonts directory
SYSTEM_FONT_PATHS: list[Path] = [
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path(Path.home() / ".fonts"),
    Path("/mnt/e/image_detection/fonts"),
]

_FONT_EXTENSIONS: frozenset[str] = frozenset(
    {".ttf", ".otf", ".woff", ".woff2", ".ttc"}
)


def _collect_font_paths(fonts_dir: Path) -> list[Path]:
    """Collect all font file paths from the project and system directories.

    Args:
        fonts_dir: Project-specific font directory to scan first.

    Returns:
        Deduplicated list of font file paths.
    """
    seen: set[Path] = set()
    result: list[Path] = []

    search_roots = [fonts_dir] + SYSTEM_FONT_PATHS
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() in _FONT_EXTENSIONS and path not in seen:
                seen.add(path)
                result.append(path)
    return result


def _assign_font_to_scripts(font_path: Path) -> list[str]:
    """Determine which scripts a font file likely supports.

    Uses substring matching against SCRIPT_FONT_PATTERNS on the lowercased
    filename stem.  A font may match multiple scripts (e.g. Noto CJK covers
    Hans, Hant, and Jpan).

    Args:
        font_path: Path to the font file.

    Returns:
        List of ISO 15924 codes that the font is assigned to.
    """
    name_lower = font_path.stem.lower()
    matched: list[str] = []
    for script, patterns in SCRIPT_FONT_PATTERNS.items():
        if any(pat in name_lower for pat in patterns):
            matched.append(script)
    return matched


def _extract_font_family(font_path: Path) -> str:
    """Extract a rough font family identifier from the file stem.

    Splits on the first hyphen or underscore to get the family prefix
    (e.g. "NotoSans-Regular" -> "NotoSans").

    Args:
        font_path: Path to the font file.

    Returns:
        Font family string (lowercase).
    """
    stem = font_path.stem
    for sep in ("-", "_"):
        if sep in stem:
            return stem.split(sep)[0].lower()
    return stem.lower()


def _scan_fonts(fonts_dir: Path) -> dict[str, int]:
    """Scan font directories and return per-script font family counts.

    Args:
        fonts_dir: Root project font directory to scan.

    Returns:
        Dict mapping ISO 15924 script code to number of distinct font
        families found for that script.
    """
    # script -> set of family names
    script_families: dict[str, set[str]] = defaultdict(set)

    all_font_paths = _collect_font_paths(fonts_dir)

    for font_path in all_font_paths:
        family = _extract_font_family(font_path)
        for script in _assign_font_to_scripts(font_path):
            script_families[script].add(family)

    return {script: len(families) for script, families in script_families.items()}


@click.command()
@click.option(
    "--fonts-dir",
    type=click.Path(path_type=Path),
    default=Path("fonts/synthetic-gen"),
    show_default=True,
    help="Directory containing project font files.",
)
@click.option(
    "--scripts",
    default=",".join(V3_SCRIPTS),
    show_default=False,
    help="Comma-separated ISO 15924 script codes to check (default: all 27 v3 scripts).",
)
@click.option(
    "--min-families",
    default=5,
    show_default=True,
    help="Minimum font families required per script.",
)
@click.option(
    "--fail-below",
    is_flag=True,
    default=False,
    help="Exit with code 1 if any script is below --min-families.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output results as JSON instead of a table.",
)
def main(
    fonts_dir: Path,
    scripts: str,
    min_families: int,
    fail_below: bool,
    output_json: bool,
) -> None:
    """Audit font coverage per script for synth-multiscript generation."""
    script_list = [s.strip() for s in scripts.split(",") if s.strip()]

    click.echo(f"Scanning fonts in: {fonts_dir} + system paths...", err=True)
    counts = _scan_fonts(fonts_dir)

    results: list[dict[str, object]] = []
    below_threshold: list[str] = []

    for script in script_list:
        count = counts.get(script, 0)
        passes = count >= min_families
        status = "OK" if passes else f"BELOW (need {min_families})"
        if not passes:
            below_threshold.append(script)
        results.append(
            {
                "script": script,
                "families_found": count,
                "min_required": min_families,
                "passes": passes,
                "status": status,
            }
        )

    if output_json:
        print(json.dumps(results, indent=2))
    else:
        click.echo(f"\n{'Script':<8} {'Families':>10} {'Min':>6}  Status")
        click.echo("-" * 42)
        for row in results:
            marker = "OK" if row["passes"] else "BELOW"
            click.echo(
                f"{row['script']:<8} {row['families_found']:>10} "
                f"{row['min_required']:>6}  {marker}"
            )
        click.echo(f"\nTotal scripts checked : {len(results)}")
        click.echo(f"Passing              : {len(results) - len(below_threshold)}")
        click.echo(f"Below threshold      : {len(below_threshold)}")
        if below_threshold:
            click.echo(f"Scripts needing fonts: {', '.join(below_threshold)}")

    if fail_below and below_threshold:
        click.echo(
            f"\nFAIL: {len(below_threshold)} scripts below minimum {min_families} families.",
            err=True,
        )
        sys.exit(1)
    elif not below_threshold:
        click.echo(
            f"\nPASS: All {len(script_list)} scripts have >= {min_families} font families.",
            err=True,
        )


if __name__ == "__main__":
    main()
