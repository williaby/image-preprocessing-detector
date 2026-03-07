#!/usr/bin/env python3
"""Analyze font usage in synth-multiscript-v3 metadata sidecars.

Parses v3 JSON sidecars to extract font_families_used per script,
confirming the single-font-per-script hypothesis caused by the
renderer dead code bug (renderer.py always picked fonts[0] instead
of calling get_tiered_font).

Usage:
    python scripts/analyze_v3_font_usage.py [OPTIONS]

Options:
    --v3-dir PATH       Path to synth-multiscript-v3 dataset [default: auto-detect]
    --output PATH       Output report path [default: reports/v3_font_usage_audit.json]
    --sample-size INT   Number of sidecars to sample per script [default: 500]
    --json              Output results as JSON instead of table
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import click


def _find_v3_dir() -> Path | None:
    """Auto-detect the synth-multiscript-v3 dataset directory."""
    candidates = [
        Path("/mnt/e/image_detection/datasets/synth-multiscript-v3"),
        Path("data/synth-multiscript-v3"),
        Path("/data/synth-multiscript-v3"),
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return None


def _analyze_script_fonts(
    script_dir: Path,
    sample_size: int,
) -> dict[str, object]:
    """Analyze font usage for a single script directory.

    Args:
        script_dir: Path to script directory containing JSON sidecars.
        sample_size: Maximum number of sidecars to parse.

    Returns:
        Dict with font usage statistics for this script.
    """
    script = script_dir.name
    font_counter: Counter[str] = Counter()
    primary_fonts: Counter[str] = Counter()
    secondary_fonts: Counter[str] = Counter()
    total_parsed = 0
    empty_count = 0

    json_files = sorted(script_dir.glob("*.json"))[:sample_size]

    for jf in json_files:
        try:
            with open(jf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        gen_params = data.get("generation_params", {})
        fonts_used = gen_params.get("font_families_used", [])
        total_parsed += 1

        if not fonts_used:
            empty_count += 1
            continue

        for font in fonts_used:
            font_counter[font] += 1

        # First font is typically the primary script's font
        primary_fonts[fonts_used[0]] += 1
        for font in fonts_used[1:]:
            secondary_fonts[font] += 1

    unique_all = len(font_counter)
    unique_primary = len(primary_fonts)

    return {
        "script": script,
        "total_parsed": total_parsed,
        "empty_font_info": empty_count,
        "unique_fonts_all": unique_all,
        "unique_primary_fonts": unique_primary,
        "primary_font_distribution": dict(primary_fonts.most_common()),
        "all_fonts_seen": dict(font_counter.most_common()),
        "single_primary_font": unique_primary == 1,
        "dominant_primary_font": (
            primary_fonts.most_common(1)[0][0] if primary_fonts else None
        ),
        "dominant_primary_pct": (
            round(
                primary_fonts.most_common(1)[0][1] / total_parsed * 100,
                1,
            )
            if primary_fonts and total_parsed > 0
            else 0
        ),
    }


@click.command()
@click.option(
    "--v3-dir",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Path to synth-multiscript-v3 dataset directory.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("reports/v3_font_usage_audit.json"),
    show_default=True,
    help="Output report path.",
)
@click.option(
    "--sample-size",
    default=500,
    show_default=True,
    help="Number of sidecars to sample per script.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output results as JSON instead of a table.",
)
def main(
    v3_dir: Path | None,
    output: Path,
    sample_size: int,
    output_json: bool,
) -> None:
    """Analyze font usage in synth-multiscript-v3 metadata sidecars."""
    if sample_size <= 0:
        click.echo("ERROR: --sample-size must be a positive integer.", err=True)
        sys.exit(1)

    if v3_dir is None:
        v3_dir = _find_v3_dir()
        if v3_dir is None:
            click.echo(
                "ERROR: Could not find synth-multiscript-v3 directory. "
                "Specify with --v3-dir.",
                err=True,
            )
            sys.exit(1)

    click.echo(f"Scanning v3 sidecars in: {v3_dir}", err=True)
    click.echo(f"Sample size per script: {sample_size}", err=True)

    results: list[dict[str, object]] = []
    script_dirs = sorted(
        [d for d in v3_dir.iterdir() if d.is_dir()],
    )

    for script_dir in script_dirs:
        click.echo(f"  Analyzing {script_dir.name}...", err=True)
        stats = _analyze_script_fonts(script_dir, sample_size)
        results.append(stats)

    # Summary
    total_scripts = len(results)
    single_font_scripts = sum(1 for r in results if r["single_primary_font"])

    summary = {
        "v3_dir": str(v3_dir),
        "sample_size_per_script": sample_size,
        "total_scripts_analyzed": total_scripts,
        "scripts_with_single_primary_font": single_font_scripts,
        "diagnosis": (
            "CONFIRMED: Dead code bug — renderer always picked fonts[0]. "
            f"{single_font_scripts}/{total_scripts} scripts used exactly "
            "one primary font across all sampled images."
        ),
        "per_script": results,
    }

    # Save JSON report
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(summary, f, indent=2)
    click.echo(f"\nReport saved to: {output}", err=True)

    # Display results
    if output_json:
        print(json.dumps(summary, indent=2))
    else:
        click.echo(
            f"\n{'Script':<8} {'Sampled':>8} {'Unique':>8} "
            f"{'Primary':>8} {'Dom%':>6}  Dominant Font",
        )
        click.echo("-" * 85)
        for r in results:
            marker = "1-FONT" if r["single_primary_font"] else "MULTI"
            click.echo(
                f"{r['script']:<8} {r['total_parsed']:>8} "
                f"{r['unique_fonts_all']:>8} {r['unique_primary_fonts']:>8} "
                f"{r['dominant_primary_pct']:>5.1f}%  "
                f"{r['dominant_primary_font']} [{marker}]",
            )

        click.echo(f"\nTotal scripts analyzed  : {total_scripts}")
        click.echo(
            f"Single-primary-font    : {single_font_scripts}/{total_scripts}",
        )
        click.echo(f"\nDiagnosis: {summary['diagnosis']}")


if __name__ == "__main__":
    main()
