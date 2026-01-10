#!/usr/bin/env python3
"""Generate SVG files from PlantUML diagrams.

This script converts all .puml files in the docs/architecture/diagrams folder
to SVG format for inclusion in MkDocs documentation.

Usage:
    python tools/generate_diagram_svgs.py [--all] [--file PATH]

Options:
    --all       Convert all .puml files
    --file      Convert a specific .puml file
    --check     Check which files need regeneration (based on mtime)
    --clean     Remove all generated .svg files

Requirements:
    - Java (JDK 11+)
    - PlantUML jar (auto-downloaded if not present)

Output:
    Creates .svg file alongside each .puml file
    e.g., rag-pipeline-overview.puml -> rag-pipeline-overview.svg
"""

import argparse
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DIAGRAMS_DIR = PROJECT_ROOT / "docs/architecture/diagrams"
PLANTUML_JAR = SCRIPT_DIR / "plantuml.jar"
PLANTUML_URL = "https://github.com/plantuml/plantuml/releases/download/v1.2024.8/plantuml-1.2024.8.jar"


def download_plantuml() -> bool:
    """Download PlantUML jar if not present."""
    if PLANTUML_JAR.exists():
        return True

    print(f"Downloading PlantUML to {PLANTUML_JAR}...")
    try:
        # Create SSL context with certificate verification
        ssl_context = ssl.create_default_context()
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected
        # PLANTUML_URL is a hardcoded constant, not user-controlled
        with urllib.request.urlopen(  # noqa: S310
            PLANTUML_URL, context=ssl_context
        ) as response:
            with open(PLANTUML_JAR, "wb") as out_file:
                out_file.write(response.read())
        print("Download complete.")
        return True
    except Exception as e:
        print(f"Failed to download PlantUML: {e}")
        return False


def find_puml_files(base_dir: Path) -> list[Path]:
    """Find all .puml files recursively."""
    return sorted(base_dir.rglob("*.puml"))


def needs_regeneration(puml_file: Path) -> bool:
    """Check if SVG needs regeneration based on modification time."""
    svg_file = puml_file.with_suffix(".svg")
    if not svg_file.exists():
        return True
    return puml_file.stat().st_mtime > svg_file.stat().st_mtime


def generate_svg(puml_file: Path, jar_path: Path) -> bool:
    """Generate SVG from a PlantUML file.

    Note: PlantUML names output files based on the diagram name in @startuml.
    We rename to match the .puml filename for consistency.
    """
    output_dir = puml_file.parent
    expected_svg = puml_file.with_suffix(".svg")

    # Remove any existing SVG with matching stem to avoid confusion
    for old_svg in output_dir.glob("*.svg"):
        if old_svg.stem.lower() == puml_file.stem.lower().replace("-", "_"):
            old_svg.unlink()

    try:
        result = subprocess.run(
            [
                "java",
                "-jar",
                str(jar_path),
                "-tsvg",
                "-charset",
                "UTF-8",
                "-o",
                str(output_dir),
                str(puml_file),
            ],
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero - PlantUML may warn but still create SVG
        )

        # Find the generated SVG (PlantUML uses diagram name, not filename)
        generated_svgs = list(output_dir.glob("*.svg"))
        new_svgs = [
            s
            for s in generated_svgs
            if s.stat().st_mtime > puml_file.stat().st_mtime - 1
        ]

        if new_svgs:
            # Rename to match puml filename if needed
            generated = new_svgs[0]
            if generated != expected_svg:
                if expected_svg.exists():
                    expected_svg.unlink()
                generated.rename(expected_svg)

            # Verify it's a valid SVG (not just an error image)
            content = expected_svg.read_text(errors="ignore")[:500]
            if "Syntax Error" in content or "background:#000000" in content:
                print(f"  Error: {puml_file.name} generated an error diagram")
                return False

            print(f"  Generated: {expected_svg.relative_to(PROJECT_ROOT)}")
            return True
        if expected_svg.exists():
            print(f"  Generated: {expected_svg.relative_to(PROJECT_ROOT)}")
            return True
        print(f"  Warning: SVG not created for {puml_file.name}")
        if result.stderr:
            print(f"    stderr: {result.stderr[:200]}")
        return False
    except Exception as e:
        print(f"  Error converting {puml_file.name}: {e!s}")
        return False


def clean_svgs(base_dir: Path) -> int:
    """Remove all generated SVG files."""
    count = 0
    for svg_file in base_dir.rglob("*.svg"):
        # Only remove if corresponding .puml exists
        puml_file = svg_file.with_suffix(".puml")
        if puml_file.exists():
            svg_file.unlink()
            print(f"  Removed: {svg_file.relative_to(PROJECT_ROOT)}")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SVG files from PlantUML diagrams"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Convert all .puml files")
    group.add_argument("--file", type=Path, help="Convert a specific .puml file")
    group.add_argument(
        "--check", action="store_true", help="Check which files need regeneration"
    )
    group.add_argument(
        "--clean", action="store_true", help="Remove all generated .svg files"
    )

    args = parser.parse_args()

    # Handle clean operation
    if args.clean:
        print("Cleaning generated SVG files...")
        count = clean_svgs(DIAGRAMS_DIR)
        print(f"Removed {count} SVG files.")
        return 0

    # Handle check operation
    if args.check:
        print("Checking for files needing regeneration...")
        puml_files = find_puml_files(DIAGRAMS_DIR)
        needs_regen = [f for f in puml_files if needs_regeneration(f)]
        if needs_regen:
            print(f"\n{len(needs_regen)} files need regeneration:")
            for f in needs_regen:
                print(f"  - {f.relative_to(PROJECT_ROOT)}")
            return 1
        print("All SVG files are up to date.")
        return 0

    # Download PlantUML if needed
    if not download_plantuml():
        return 1

    # Determine files to process
    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}")
            return 1
        puml_files = [args.file]
    elif args.all:
        puml_files = find_puml_files(DIAGRAMS_DIR)
    else:
        # Default: only files needing regeneration
        all_files = find_puml_files(DIAGRAMS_DIR)
        puml_files = [f for f in all_files if needs_regeneration(f)]

    if not puml_files:
        print("No files to process.")
        return 0

    print(f"Processing {len(puml_files)} PlantUML file(s)...")

    success = 0
    failed = 0

    for puml_file in puml_files:
        if generate_svg(puml_file, PLANTUML_JAR):
            success += 1
        else:
            failed += 1

    print(f"\nComplete: {success} succeeded, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
