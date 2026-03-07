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
    --deep              Use fontTools cmap inspection for ground-truth script coverage
"""

from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import click

logger = logging.getLogger(__name__)

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
    "Latn": [
        "latin",
        "roman",
        "serif",
        "sans",
        "mono",
        "noto-latin",
        "liberation",
        "roboto",
        "fira",
        "dejavu",
        "gentium",
        "charis",
        "andika",
        "doulos",
    ],
    "Arab": [
        "arabic",
        "arab",
        "scheherazade",
        "amiri",
        "lateef",
        "reem",
        "kufi",
        "nastaliq",
        "awami",
        "harmattan",
        "arefruqaa",
        "tajawal",
        "mada",
        "elmessiri",
        "cairo",
    ],
    "Deva": [
        "devanagari",
        "deva",
        "noto-deva",
        "mangal",
        "sanskrit",
        "kalam",
        "hind-",
        "mukta-",
        "baloo2",
        "tirodevanagari",
        "lohit-deva",
    ],
    "Hans": [
        "cjk",
        "simplified",
        "hans",
        "notosc",
        "notosanssc",
        "notoserif sc",
        "wqy",
        "mashan",
        "liujian",
        "longcang",
        "zhimang",
        "zcool",
    ],
    "Hant": ["traditional", "hant", "nototc", "notosanstc", "notoserif tc"],
    "Cyrl": [
        "cyrillic",
        "cyrl",
        "slavic",
        "russian",
        "liberation",
        "dejavu",
        "roboto",
        "fira",
        "ptsans",
        "ptserif",
        "badscript",
        "caveat",
        "marckscript",
        "russoone",
    ],
    "Jpan": ["japanese", "jpan", "notojp", "notosansjp", "ipafont"],
    "Hang": ["korean", "hang", "notokr", "notosanskr", "nanum", "gothica1"],
    "Thai": [
        "thai",
        "noto-thai",
        "thsarabun",
        "loopedthai",
        "kanit",
        "pridi",
        "baijamjuree",
        "mitr",
        "prompt",
        "sarabun",
        "itim",
    ],
    "Beng": [
        "bengali",
        "beng",
        "noto-beng",
        "vrinda",
        "kalpurush",
        "solaimanlipi",
        "atma",
        "galada",
    ],
    "Gujr": [
        "gujarati",
        "gujr",
        "noto-gujr",
        "hindvadodara",
        "muktavaani",
        "rasa",
        "baloobhai",
    ],
    "Guru": ["gurmukhi", "guru", "noto-guru", "muktamahee", "baloopaaji"],
    "Knda": [
        "kannada",
        "knda",
        "noto-knda",
        "timmana",
        "balootamma",
        "hindmysuru",
        "benne",
    ],
    "Mlym": [
        "malayalam",
        "mlym",
        "noto-mlym",
        "manjari",
        "rachana",
        "meera",
        "anjalioldlipi",
        "chilanka",
    ],
    "Orya": [
        "oriya",
        "odia",
        "orya",
        "noto-orya",
        "baloobhaina",
        "anekodia",
        "alkatra",
    ],
    "Taml": [
        "tamil",
        "taml",
        "noto-taml",
        "latha",
        "catamaran",
        "muktamalar",
        "hindmadurai",
        "arimamadurai",
        "kavivanar",
    ],
    "Telu": [
        "telugu",
        "telu",
        "noto-telu",
        "hindguntur",
        "ramabhadra",
        "mandali",
        "ntr",
    ],
    "Tibt": [
        "tibetan",
        "tibt",
        "noto-tibt",
        "jomolhari",
        "uchen",
        "ddcuchen",
        "monlam",
        "tibetanmachine",
    ],
    "Mymr": ["myanmar", "mymr", "noto-mymr", "padauk", "khyay"],
    "Khmr": ["khmer", "khmr", "noto-khmr", "busra", "battambang", "content", "moul"],
    "Sinh": ["sinhala", "sinh", "noto-sinh", "iskpota", "abhayalibre", "yaldevi"],
    "Laoo": ["lao", "laoo", "noto-lao", "loopedlao", "phetsarath"],
    "Cher": ["cherokee", "cher", "noto-cher", "aboriginal"],
    "Cans": [
        "canadianaboriginal",
        "cans",
        "syllabics",
        "noto-cans",
        "bjcree",
        "aboriginal",
    ],
    "Ethi": ["ethiopic", "ethi", "noto-ethi", "abyssinica", "brana", "zemen"],
    "Geor": ["georgian", "geor", "noto-geor", "bpg"],
    "Hebr": ["hebrew", "hebr", "noto-hebr", "david", "frank", "heebo", "suezone"],
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

# Unicode block ranges mapped to ISO 15924 script codes.
# Each entry: (start, end, script_code).  A font is assigned to a script
# if its cmap contains >= CMAP_MIN_CODEPOINTS codepoints in that range.
CMAP_MIN_CODEPOINTS: int = 10

UNICODE_SCRIPT_RANGES: list[tuple[int, int, str]] = [
    # Latin
    (0x0041, 0x024F, "Latn"),  # Basic Latin + Latin Extended-A/B
    # Arabic
    (0x0600, 0x06FF, "Arab"),  # Arabic block
    (0x0750, 0x077F, "Arab"),  # Arabic Supplement
    (0xFB50, 0xFDFF, "Arab"),  # Arabic Presentation Forms-A
    # Devanagari
    (0x0900, 0x097F, "Deva"),
    # Bengali
    (0x0980, 0x09FF, "Beng"),
    # Gurmukhi
    (0x0A00, 0x0A7F, "Guru"),
    # Gujarati
    (0x0A80, 0x0AFF, "Gujr"),
    # Oriya
    (0x0B00, 0x0B7F, "Orya"),
    # Tamil
    (0x0B80, 0x0BFF, "Taml"),
    # Telugu
    (0x0C00, 0x0C7F, "Telu"),
    # Kannada
    (0x0C80, 0x0CFF, "Knda"),
    # Malayalam
    (0x0D00, 0x0D7F, "Mlym"),
    # Sinhala
    (0x0D80, 0x0DFF, "Sinh"),
    # Thai
    (0x0E00, 0x0E7F, "Thai"),
    # Lao
    (0x0E80, 0x0EFF, "Laoo"),
    # Tibetan
    (0x0F00, 0x0FFF, "Tibt"),
    # Myanmar
    (0x1000, 0x109F, "Mymr"),
    # Georgian
    (0x10A0, 0x10FF, "Geor"),
    (0x2D00, 0x2D2F, "Geor"),  # Georgian Supplement
    # Ethiopic
    (0x1200, 0x137F, "Ethi"),
    (0x1380, 0x139F, "Ethi"),  # Ethiopic Supplement
    # Cherokee
    (0x13A0, 0x13FF, "Cher"),
    (0xAB70, 0xABBF, "Cher"),  # Cherokee Supplement
    # Canadian Aboriginal Syllabics
    (0x1400, 0x167F, "Cans"),
    (0x18B0, 0x18FF, "Cans"),  # Unified Canadian Aboriginal Syllabics Extended
    # Khmer
    (0x1780, 0x17FF, "Khmr"),
    (0x19E0, 0x19FF, "Khmr"),  # Khmer Symbols
    # CJK Unified Ideographs (shared by Hans, Hant, Jpan)
    (0x4E00, 0x9FFF, "Hans"),
    (0x4E00, 0x9FFF, "Hant"),
    (0x4E00, 0x9FFF, "Jpan"),
    # Hiragana + Katakana (Japanese-specific)
    (0x3040, 0x309F, "Jpan"),  # Hiragana
    (0x30A0, 0x30FF, "Jpan"),  # Katakana
    # Hangul (Korean)
    (0xAC00, 0xD7AF, "Hang"),  # Hangul Syllables
    (0x1100, 0x11FF, "Hang"),  # Hangul Jamo
    # Cyrillic
    (0x0400, 0x04FF, "Cyrl"),
    (0x0500, 0x052F, "Cyrl"),  # Cyrillic Supplement
    # Greek
    (0x0370, 0x03FF, "Grek"),
    # Hebrew
    (0x0590, 0x05FF, "Hebr"),
    (0xFB1D, 0xFB4F, "Hebr"),  # Hebrew Presentation Forms
    # Armenian
    (0x0530, 0x058F, "Armn"),
]

# OS/2 table panose and class-based font style classification
_STYLE_SERIF_CLASSES = {1, 2, 3, 4, 5, 6, 7}
_STYLE_SANS_CLASS = 8
_STYLE_DISPLAY_CLASSES = {9, 10}


def _classify_font_style(font_path: Path) -> str:
    """Classify a font as serif/sans/mono/handwriting/display from OS/2 table.

    Args:
        font_path: Path to the font file.

    Returns:
        One of: serif, sans, mono, handwriting, display, unknown.
    """
    try:
        from fontTools.ttLib import TTFont

        font = TTFont(font_path, fontNumber=0)
        os2 = font.get("OS/2")
        if os2 is None:
            font.close()
            return "unknown"

        # Check panose for handwriting (family_type=3 = Script)
        panose = os2.panose
        if panose and panose.bFamilyType == 3:
            font.close()
            return "handwriting"

        # Check if monospace via post table
        post = font.get("post")
        if post and post.isFixedPitch:
            font.close()
            return "mono"

        # Use sFamilyClass (high byte) for serif/sans/display
        family_class = (os2.sFamilyClass >> 8) & 0xFF
        font.close()

        if family_class in _STYLE_SERIF_CLASSES:
            return "serif"
        if family_class == _STYLE_SANS_CLASS:
            return "sans"
        if family_class in _STYLE_DISPLAY_CLASSES:
            return "display"

        # Fallback: check name for common patterns
        name_lower = font_path.stem.lower()
        if "serif" in name_lower and "sans" not in name_lower:
            return "serif"
        if "sans" in name_lower:
            return "sans"
        if "mono" in name_lower:
            return "mono"

        return "unknown"
    except Exception:
        return "unknown"


def _deep_assign_font_to_scripts(font_path: Path) -> list[str]:
    """Determine script support by inspecting the font's cmap table.

    Opens the font with fontTools and checks which Unicode script ranges
    have sufficient codepoint coverage (>= CMAP_MIN_CODEPOINTS).

    For .ttc (TrueType Collection) files, inspects the first sub-font.

    Args:
        font_path: Path to the font file.

    Returns:
        List of ISO 15924 codes that the font supports.
    """
    try:
        from fontTools.ttLib import TTFont

        font = TTFont(font_path, fontNumber=0)
        cmap = font.getBestCmap()
        if cmap is None:
            font.close()
            return []

        codepoints = set(cmap.keys())
        font.close()

        # Count codepoints per script range
        script_counts: dict[str, int] = defaultdict(int)
        for start, end, script in UNICODE_SCRIPT_RANGES:
            count = sum(1 for cp in codepoints if start <= cp <= end)
            script_counts[script] += count

        return [
            script
            for script, count in script_counts.items()
            if count >= CMAP_MIN_CODEPOINTS
        ]
    except Exception as exc:
        logger.debug("Failed to inspect cmap for %s: %s", font_path, exc)
        return []


def _deep_scan_fonts(
    fonts_dir: Path,
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """Scan fonts using cmap inspection for ground-truth script coverage.

    Args:
        fonts_dir: Root project font directory to scan.

    Returns:
        Tuple of (script_family_counts, style_distribution).
        style_distribution maps script -> {style: count}.
    """
    script_families: dict[str, set[str]] = defaultdict(set)
    style_dist: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    all_font_paths = _collect_font_paths(fonts_dir)
    total = len(all_font_paths)

    for idx, font_path in enumerate(all_font_paths):
        if idx % 500 == 0:
            click.echo(
                f"  Deep scanning: {idx}/{total} fonts...",
                err=True,
            )

        family = _extract_font_family(font_path)
        scripts = _deep_assign_font_to_scripts(font_path)
        style = _classify_font_style(font_path) if scripts else "unknown"

        for script in scripts:
            script_families[script].add(family)
            style_dist[script][style] += 1

    counts = {script: len(families) for script, families in script_families.items()}
    return counts, dict(style_dist)


def _collect_font_paths(fonts_dir: Path) -> list[Path]:
    """Collect all font file paths from the project and system directories.

    Args:
        fonts_dir: Project-specific font directory to scan first.

    Returns:
        Deduplicated list of font file paths.
    """
    seen: set[Path] = set()
    result: list[Path] = []

    search_roots = [fonts_dir, *SYSTEM_FONT_PATHS]
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
@click.option(
    "--deep",
    is_flag=True,
    default=False,
    help="Use fontTools cmap inspection for ground-truth script coverage.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Save deep audit results to this JSON path.",
)
def main(
    fonts_dir: Path,
    scripts: str,
    min_families: int,
    fail_below: bool,
    output_json: bool,
    deep: bool,
    output: Path | None,
) -> None:
    """Audit font coverage per script for synth-multiscript generation."""
    script_list = [s.strip() for s in scripts.split(",") if s.strip()]

    style_dist: dict[str, dict[str, int]] = {}
    if deep:
        click.echo(
            f"Deep scanning fonts in: {fonts_dir} + system paths (cmap inspection)...",
            err=True,
        )
        counts, style_dist = _deep_scan_fonts(fonts_dir)
    else:
        click.echo(
            f"Scanning fonts in: {fonts_dir} + system paths...",
            err=True,
        )
        counts = _scan_fonts(fonts_dir)

    results: list[dict[str, object]] = []
    below_threshold: list[str] = []

    for script in script_list:
        count = counts.get(script, 0)
        passes = count >= min_families
        status = "OK" if passes else f"BELOW (need {min_families})"
        if not passes:
            below_threshold.append(script)
        row: dict[str, object] = {
            "script": script,
            "families_found": count,
            "min_required": min_families,
            "passes": passes,
            "status": status,
        }
        if deep and script in style_dist:
            row["style_distribution"] = style_dist[script]
        results.append(row)

    if output_json:
        print(json.dumps(results, indent=2))
    elif deep:
        click.echo(
            f"\n{'Script':<8} {'Families':>10} {'Min':>6}  "
            f"{'Serif':>6} {'Sans':>6} {'Mono':>6} "
            f"{'HW':>6} {'Disp':>6}  Status",
        )
        click.echo("-" * 78)
        for row in results:
            marker = "OK" if row["passes"] else "BELOW"
            sd = row.get("style_distribution", {})
            if not isinstance(sd, dict):
                sd = {}
            click.echo(
                f"{row['script']:<8} {row['families_found']:>10} "
                f"{row['min_required']:>6}  "
                f"{sd.get('serif', 0):>6} {sd.get('sans', 0):>6} "
                f"{sd.get('mono', 0):>6} {sd.get('handwriting', 0):>6} "
                f"{sd.get('display', 0):>6}  {marker}",
            )
        click.echo(f"\nTotal scripts checked : {len(results)}")
        click.echo(
            f"Passing              : {len(results) - len(below_threshold)}",
        )
        click.echo(f"Below threshold      : {len(below_threshold)}")
        if below_threshold:
            click.echo(
                f"Scripts needing fonts: {', '.join(below_threshold)}",
            )
    else:
        click.echo(f"\n{'Script':<8} {'Families':>10} {'Min':>6}  Status")
        click.echo("-" * 42)
        for row in results:
            marker = "OK" if row["passes"] else "BELOW"
            click.echo(
                f"{row['script']:<8} {row['families_found']:>10} "
                f"{row['min_required']:>6}  {marker}",
            )
        click.echo(f"\nTotal scripts checked : {len(results)}")
        click.echo(
            f"Passing              : {len(results) - len(below_threshold)}",
        )
        click.echo(f"Below threshold      : {len(below_threshold)}")
        if below_threshold:
            click.echo(
                f"Scripts needing fonts: {', '.join(below_threshold)}",
            )

    # Save deep audit results to file
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "mode": "deep" if deep else "heuristic",
            "fonts_dir": str(fonts_dir),
            "min_families": min_families,
            "total_scripts": len(results),
            "passing": len(results) - len(below_threshold),
            "below_threshold": below_threshold,
            "per_script": results,
        }
        with open(output, "w") as f:
            json.dump(report, f, indent=2)
        click.echo(f"\nReport saved to: {output}", err=True)

    if fail_below and below_threshold:
        click.echo(
            f"\nFAIL: {len(below_threshold)} scripts below minimum "
            f"{min_families} families.",
            err=True,
        )
        sys.exit(1)
    elif not below_threshold:
        click.echo(
            f"\nPASS: All {len(script_list)} scripts have >= "
            f"{min_families} font families.",
            err=True,
        )


if __name__ == "__main__":
    main()
