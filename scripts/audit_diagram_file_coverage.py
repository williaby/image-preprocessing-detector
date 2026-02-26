#!/usr/bin/env python3
"""Audit file coverage: compare git-tracked files against FILE_INVENTORY and PUML diagrams.

Produces five gap categories:
  GAP_A: In git, NOT in inventory  → newly added files needing workstream assignment
  GAP_B: In inventory, NOT in git  → deleted/renamed files still listed (stale entries)
  GAP_C: In git, NO PUML reference → architecturally undocumented files
  GAP_D: PUML references NOT in git → broken diagram references
  GAP_E: Adapter file missing __l4_* header → not covered by Level 4 instance registry

Usage:
  python scripts/audit_diagram_file_coverage.py
  python scripts/audit_diagram_file_coverage.py --no-write
  python scripts/audit_diagram_file_coverage.py --gap A
  python scripts/audit_diagram_file_coverage.py --gap E
  python scripts/audit_diagram_file_coverage.py --scope src
  python scripts/audit_diagram_file_coverage.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKAGE = "image_preprocessing_detector"

# Directories included in the gap analysis (relative to repo root)
SOURCE_DIRS = ["src/", "scripts/", "modal/", "tools/", "config/"]

# Path prefixes that are intentionally excluded from workstream tracking.
# Files in these directories will always show up in GAP_A/GAP_C — that's expected.
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "src/image_preprocessing_detector/__pycache__",
    "fonts/",
    ".claude/",
    "data/test_fixtures/",
    "metadata_registry/aggregates/",
    ".github/workflows/",
    "docs/_archived/",
)

# File extensions treated as source files in PUML references
SOURCE_EXTENSIONS = {".py", ".yaml", ".yml", ".sh", ".json"}

# Markers in PUML that indicate a file is intentionally absent (future work)
PLANNED_MARKERS = ("(planned)", "(estimated)", "(wip)", "(future)", "(tbd)")

# Adapter directories whose Python files MUST carry __l4_* headers (GAP_E check).
# Each entry is a full path prefix relative to repo root.
ADAPTER_DIR_PATTERNS_L4: tuple[str, ...] = (
    "src/image_preprocessing_detector/annotation/parsers/correction/",
    "src/image_preprocessing_detector/annotation/parsers/document/",
    "src/image_preprocessing_detector/annotation/parsers/formula/",
    "src/image_preprocessing_detector/annotation/parsers/handwriting/",
    "src/image_preprocessing_detector/annotation/parsers/layout/",
    "src/image_preprocessing_detector/annotation/parsers/multilingual/",
    "src/image_preprocessing_detector/annotation/parsers/quality/",
    "src/image_preprocessing_detector/annotation/enrichment/providers/",
)

# Framework / utility filenames that are exempt from the L4 header requirement.
ADAPTER_SKIP_FILES: frozenset[str] = frozenset(
    {"__init__.py", "base.py", "registry.py", "template.py", "generic.py"}
)

# Pattern that identifies integrate-enrichment scripts in scripts/
_INTEGRATE_RE = re.compile(r"^integrate_.+_enrichments\.py$", re.IGNORECASE)

# Regex that detects the presence of an __l4_category__ module variable
_L4_HEADER_RE = re.compile(r"^__l4_category__\s*=", re.MULTILINE)

# Inventory and diagram locations (relative to repo root)
INVENTORY_RELATIVE = "docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md"
DIAGRAMS_RELATIVE = "docs/architecture/diagrams"
DEFAULT_OUTPUT_RELATIVE = "docs/architecture/DIAGRAM_COVERAGE_AUDIT.md"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PumlReference:
    """A single file reference extracted from a PUML diagram."""

    raw_path: str
    normalized_path: str
    source_puml: str
    is_planned: bool = False


@dataclass
class GapSets:
    """The five gap categories computed by this audit."""

    # GAP_A: git-tracked but not in inventory
    new_not_in_inventory: set[str] = field(default_factory=set)
    # GAP_B: in inventory but not in git
    stale_not_in_git: set[str] = field(default_factory=set)
    # GAP_C: git-tracked but not referenced in any PUML
    undocumented_in_puml: set[str] = field(default_factory=set)
    # GAP_D: PUML references a path that doesn't exist in git (non-planned only)
    broken_puml_refs: list[PumlReference] = field(default_factory=list)
    # GAP_E: adapter file in ADAPTER_DIR_PATTERNS_L4 missing __l4_category__ header
    missing_l4_headers: set[str] = field(default_factory=set)
    # L4_COVERED: adapter files that DO carry __l4_* headers (positive signal)
    l4_covered: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Step 1 — Git-tracked files
# ---------------------------------------------------------------------------


def get_git_tracked_files(repo_root: Path) -> set[str]:
    """Return all git-tracked paths under SOURCE_DIRS, relative to repo root."""
    args = ["git", "ls-files", *SOURCE_DIRS]
    result = subprocess.run(
        args, cwd=repo_root, capture_output=True, text=True, check=True
    )
    raw = set(result.stdout.splitlines())
    return _filter_source_files(raw)


def _filter_source_files(paths: set[str]) -> set[str]:
    """Remove build artifacts and intentionally excluded directories."""
    kept: set[str] = set()
    for p in paths:
        if any(p.startswith(excl) for excl in EXCLUDED_PREFIXES):
            continue
        if "__pycache__" in p or p.endswith(".pyc"):
            continue
        kept.add(p)
    return kept


# ---------------------------------------------------------------------------
# Step 2 — Parse FILE_INVENTORY markdown
# ---------------------------------------------------------------------------


def parse_inventory(inventory_path: Path) -> set[str]:
    """Extract file paths from pipe-delimited tables in the FILE_INVENTORY document.

    Handles the markdown rendering quirk where ``__init__`` appears as ``**init**``.
    Skips header rows and non-path content.
    """
    if not inventory_path.exists():
        print(f"[WARN] Inventory not found: {inventory_path}", file=sys.stderr)
        return set()

    paths: set[str] = set()
    text = inventory_path.read_text(encoding="utf-8")

    for line in text.splitlines():
        # Only look at lines that start with a pipe (table rows)
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue

        # Extract the first cell of the table
        parts = stripped.split("|")
        if len(parts) < 2:
            continue
        first_cell = parts[1].strip()

        # Restore __init__ from markdown bold rendering
        first_cell = first_cell.replace("**init**", "__init__")

        # Must start with one of the source directories
        if not any(first_cell.startswith(d.rstrip("/")) for d in SOURCE_DIRS):
            continue

        # Skip header rows (no file extension, contains spaces typical of headers)
        if " " in first_cell or "|" in first_cell:
            continue

        # Skip rows where LOC is a header label
        if len(parts) >= 3 and parts[2].strip().upper() in ("LOC", "LINES"):
            continue

        # Basic sanity: must contain at least one dot (has an extension) or be __init__
        if "." not in first_cell and "__init__" not in first_cell:
            continue

        paths.add(first_cell)

    return paths


# ---------------------------------------------------------------------------
# Step 3 — Parse PUML diagrams for file references
# ---------------------------------------------------------------------------

# Regex patterns for extracting file paths from PUML content.
# Matches paths that start with a known source directory prefix.
_PATH_PATTERN = re.compile(
    r"""
    (?:^|[\s\-•*])          # start of line or list bullet
    (                       # capture group: the path
        (?:src|scripts|modal|tools|config)  # known top-level dirs
        /[a-zA-Z0-9_./${}/-]+              # path components (allow ... for abbreviations)
        \.(?:py|yaml|yml|sh|json)          # must end with a known extension
    )
    (?:\s|$|\(|\[)          # followed by space, EOL, opening paren, or bracket
    """,
    re.VERBOSE | re.MULTILINE,
)

# Catches abbreviated directory refs like "note right: src/ingestion/" — not file refs
_DIRECTORY_ONLY = re.compile(r"^(?:src|scripts|modal|tools|config)/[a-zA-Z0-9_/]*/$")


def parse_puml_references(diagrams_dir: Path) -> list[PumlReference]:
    """Scan all PUML files under diagrams_dir and extract file path references."""
    refs: list[PumlReference] = []
    puml_files = sorted(diagrams_dir.rglob("*.puml"))

    for puml_path in puml_files:
        content = puml_path.read_text(encoding="utf-8", errors="replace")
        puml_name = str(puml_path)

        for line in content.splitlines():
            for match in _PATH_PATTERN.finditer(line):
                raw = match.group(1)

                # Skip directory-only references
                if _DIRECTORY_ONLY.match(raw):
                    continue

                normalized = _normalize_puml_path(raw)

                # Detect planned/estimated markers on the same line
                line_lower = line.lower()
                is_planned = any(marker in line_lower for marker in PLANNED_MARKERS)

                refs.append(
                    PumlReference(
                        raw_path=raw,
                        normalized_path=normalized,
                        source_puml=puml_name,
                        is_planned=is_planned,
                    )
                )

    return refs


def _normalize_puml_path(path: str) -> str:
    """Expand abbreviated PUML paths to their full git-tracked equivalents.

    Two abbreviation styles are used in the diagrams:
      ``src/.../module/file.py``  → ``src/image_preprocessing_detector/module/file.py``
      ``src/module/file.py``      → ``src/image_preprocessing_detector/module/file.py``

    Paths that already contain the package name, or that start with scripts/,
    modal/, tools/, or config/ are returned unchanged.
    """
    if not path.startswith("src/"):
        return path  # scripts/, modal/, tools/, config/ are already full paths

    if PACKAGE in path:
        return path  # already fully qualified

    # Handle src/.../module/file.py
    if ".../" in path:
        return re.sub(r"src/\.\.\./", f"src/{PACKAGE}/", path)

    # Handle src/module/file.py (missing package segment)
    return path.replace("src/", f"src/{PACKAGE}/", 1)


# ---------------------------------------------------------------------------
# Step 3b — Level 4 header checks (GAP_E)
# ---------------------------------------------------------------------------


def _has_l4_header(repo_root: Path, filepath: str) -> bool:
    """Return True if a Python file contains a ``__l4_category__`` module variable."""
    try:
        text = (repo_root / filepath).read_text(encoding="utf-8", errors="replace")
        return bool(_L4_HEADER_RE.search(text))
    except OSError:
        return False


def populate_gap_e(gaps: GapSets, repo_root: Path, git_files: set[str]) -> None:
    """Populate ``gaps.missing_l4_headers`` (GAP_E) and ``gaps.l4_covered`` in-place.

    Walks all adapter directories and integrate-enrichment scripts.  Files in
    ADAPTER_SKIP_FILES are silently ignored.
    """
    for filepath in sorted(git_files):
        basename = Path(filepath).name
        if basename in ADAPTER_SKIP_FILES:
            continue

        is_adapter_dir = any(filepath.startswith(d) for d in ADAPTER_DIR_PATTERNS_L4)
        is_integrate = (
            filepath.startswith("scripts/")
            and _INTEGRATE_RE.match(basename) is not None
        )

        if not (is_adapter_dir or is_integrate):
            continue

        if _has_l4_header(repo_root, filepath):
            gaps.l4_covered.add(filepath)
        else:
            gaps.missing_l4_headers.add(filepath)


# ---------------------------------------------------------------------------
# Step 4 — Compute gap sets
# ---------------------------------------------------------------------------


def compute_gaps(
    git_files: set[str],
    inventory_files: set[str],
    puml_refs: list[PumlReference],
) -> GapSets:
    """Compute the four gap categories from the three input sets."""
    gaps = GapSets()

    # Unique normalized paths from PUML (all refs, for GAP_C)
    all_puml_paths = {ref.normalized_path for ref in puml_refs}

    # Non-planned PUML paths (for GAP_D — broken references)
    confirmed_puml_paths = {
        ref.normalized_path for ref in puml_refs if not ref.is_planned
    }

    gaps.new_not_in_inventory = git_files - inventory_files
    gaps.stale_not_in_git = inventory_files - git_files
    gaps.undocumented_in_puml = git_files - all_puml_paths

    # GAP_D: non-planned PUML paths that don't exist in git
    seen_broken: set[str] = set()
    for ref in puml_refs:
        if ref.is_planned:
            continue
        if (
            ref.normalized_path not in git_files
            and ref.normalized_path not in seen_broken
        ):
            seen_broken.add(ref.normalized_path)
            gaps.broken_puml_refs.append(ref)

    return gaps


# ---------------------------------------------------------------------------
# Step 5 — Coverage metrics
# ---------------------------------------------------------------------------


def _compute_coverage(
    git_files: set[str], puml_refs: list[PumlReference]
) -> dict[str, float]:
    """Compute coverage percentages for the summary."""
    all_puml = {ref.normalized_path for ref in puml_refs}
    inventory_coverage = 0.0  # computed in main
    puml_coverage = (
        len(git_files & all_puml) / len(git_files) * 100 if git_files else 0.0
    )
    return {"puml_coverage_pct": puml_coverage}


# ---------------------------------------------------------------------------
# Step 6 — Group files by top-level directory for reporting
# ---------------------------------------------------------------------------


def _group_by_dir(paths: set[str]) -> dict[str, list[str]]:
    """Group file paths by their top-level directory (e.g., src/, scripts/)."""
    groups: dict[str, list[str]] = defaultdict(list)
    for p in sorted(paths):
        top = p.split("/")[0] + "/"
        groups[top].append(p)
    return dict(groups)


def _group_broken_by_puml(refs: list[PumlReference]) -> dict[str, list[PumlReference]]:
    """Group broken PUML references by the diagram file they appear in."""
    groups: dict[str, list[PumlReference]] = defaultdict(list)
    for ref in refs:
        groups[ref.source_puml].append(ref)
    return dict(groups)


# ---------------------------------------------------------------------------
# Step 7 — Generate markdown report
# ---------------------------------------------------------------------------


def generate_report(
    gaps: GapSets,
    git_files: set[str],
    inventory_files: set[str],
    puml_refs: list[PumlReference],
    output_path: Path,
    *,
    write: bool = True,
) -> str:
    """Render the gap report as a markdown string and optionally write it to disk."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_puml_paths = {ref.normalized_path for ref in puml_refs}
    puml_covered = len(git_files & all_puml_paths)
    inv_covered = len(git_files & inventory_files)

    lines: list[str] = [
        "---",
        "title: Diagram File Coverage Audit",
        f"generated: {now}",
        "schema_type: common",
        "status: generated",
        "---",
        "",
        "# Diagram File Coverage Audit",
        "",
        f"> **Generated**: {now}  ",
        "> **Script**: `scripts/audit_diagram_file_coverage.py`  ",
        f"> **Inventory**: `{INVENTORY_RELATIVE}`",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Git-tracked source files | {len(git_files)} |",
        f"| Files in FILE_INVENTORY | {len(inventory_files)} |",
        f"| Unique PUML file references (normalized) | {len(all_puml_paths)} |",
        f"| PUML diagrams scanned | {len({r.source_puml for r in puml_refs})} |",
        "",
        "| Gap Category | Count | Meaning |",
        "|-------------|-------|---------|",
        f"| **GAP_A**: In git, NOT in inventory | {len(gaps.new_not_in_inventory)} | Newly added; need workstream assignment |",
        f"| **GAP_B**: In inventory, NOT in git | {len(gaps.stale_not_in_git)} | Deleted/renamed; remove from inventory |",
        f"| **GAP_C**: In git, NO PUML reference | {len(gaps.undocumented_in_puml)} | No architecture diagram reference |",
        f"| **GAP_D**: PUML ref not in git | {len(gaps.broken_puml_refs)} | Broken diagram reference (non-planned) |",
        f"| **GAP_E**: Adapter missing L4 header | {len(gaps.missing_l4_headers)} | Not covered by Level 4 instance registry |",
        "",
        "| Coverage | Percentage |",
        "|----------|-----------|",
        f"| Files covered by FILE_INVENTORY | {inv_covered / len(git_files) * 100:.1f}% ({inv_covered}/{len(git_files)}) |"
        if git_files
        else "| Files covered by FILE_INVENTORY | N/A |",
        f"| Files referenced in PUML diagrams | {puml_covered / len(git_files) * 100:.1f}% ({puml_covered}/{len(git_files)}) |"
        if git_files
        else "| Files referenced in PUML diagrams | N/A |",
        f"| Adapter files with L4 header (L4_COVERED) | {len(gaps.l4_covered) / max(len(gaps.l4_covered) + len(gaps.missing_l4_headers), 1) * 100:.1f}% ({len(gaps.l4_covered)}/{len(gaps.l4_covered) + len(gaps.missing_l4_headers)}) |",
        "",
        "---",
        "",
    ]

    # ----- GAP_A -----
    lines += [
        "## GAP_A — In Git, NOT in Inventory",
        "",
        "These files are git-tracked but have no entry in `FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`.",
        "Review each to determine: (a) assign to a workstream and add to inventory, or",
        "(b) add to the Intentionally Excluded section if it's tooling/docs/test support.",
        "",
    ]
    if gaps.new_not_in_inventory:
        for top_dir, files in sorted(_group_by_dir(gaps.new_not_in_inventory).items()):
            lines.append(f"### `{top_dir}` ({len(files)} files)")
            lines.append("")
            for f in files:
                lines.append(f"- `{f}`")
            lines.append("")
    else:
        lines += ["_No gaps — all git-tracked files are in the inventory._", ""]

    lines += ["---", ""]

    # ----- GAP_B -----
    lines += [
        "## GAP_B — In Inventory, NOT in Git",
        "",
        "These entries appear in `FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md` but are **not**",
        "git-tracked. They were likely deleted, renamed, or moved. Remove them from the inventory.",
        "",
    ]
    if gaps.stale_not_in_git:
        for top_dir, files in sorted(_group_by_dir(gaps.stale_not_in_git).items()):
            lines.append(f"### `{top_dir}` ({len(files)} files)")
            lines.append("")
            for f in files:
                lines.append(f"- `{f}`")
            lines.append("")
    else:
        lines += ["_No gaps — all inventory entries exist in git._", ""]

    lines += ["---", ""]

    # ----- GAP_C -----
    lines += [
        "## GAP_C — In Git, No PUML Reference",
        "",
        "These git-tracked files are not referenced in any architecture diagram.",
        "Review each to determine: (a) add a reference to the appropriate PUML diagram,",
        "or (b) accept as undocumented (e.g., one-off scripts, migration utilities).",
        "",
        "> **Note**: `scripts/` entries are frequently standalone utilities with no",
        "> expected PUML reference. Focus review on `src/` first.",
        "",
    ]
    if gaps.undocumented_in_puml:
        for top_dir, files in sorted(_group_by_dir(gaps.undocumented_in_puml).items()):
            lines.append(f"### `{top_dir}` ({len(files)} files)")
            lines.append("")
            for f in files:
                lines.append(f"- `{f}`")
            lines.append("")
    else:
        lines += [
            "_No gaps — all git-tracked files have at least one PUML reference._",
            "",
        ]

    lines += ["---", ""]

    # ----- GAP_D -----
    lines += [
        "## GAP_D — PUML References NOT in Git",
        "",
        "These paths appear in PUML diagram notes but are **not** git-tracked.",
        "Files marked `(planned)` or `(estimated)` in the PUML are **excluded** from this list.",
        "Fix by: (a) removing the reference if the file was deleted, or (b) creating the file.",
        "",
    ]
    if gaps.broken_puml_refs:
        for puml_src, refs in sorted(
            _group_broken_by_puml(gaps.broken_puml_refs).items()
        ):
            # Show just the relative path from docs/architecture/
            puml_display = puml_src.replace(str(Path.cwd()) + "/", "")
            lines.append(f"### `{puml_display}`")
            lines.append("")
            for ref in refs:
                lines.append(f"- `{ref.normalized_path}` (raw: `{ref.raw_path}`)")
            lines.append("")
    else:
        lines += [
            "_No broken references — all PUML paths resolve to git-tracked files._",
            "",
        ]

    lines += ["---", ""]

    # ----- GAP_E -----
    lines += [
        "## GAP_E — Adapter Files Missing Level 4 Header",
        "",
        "These files live in adapter directories (`annotation/parsers/`, "
        "`annotation/enrichment/providers/`, `scripts/integrate_*_enrichments.py`)",
        "but do not contain an `__l4_category__` module variable.",
        "Add the `# --- Level 4 registry metadata ---` block to each file so the",
        "harvester can include them in the Level 4 instance registries.",
        "",
        "Run `python scripts/generate_level4_registries.py --scaffold --category <cat>`",
        "to generate a stub header block.",
        "",
    ]
    if gaps.missing_l4_headers:
        for top_dir, files in sorted(_group_by_dir(gaps.missing_l4_headers).items()):
            lines.append(f"### `{top_dir}` ({len(files)} files)")
            lines.append("")
            for f in files:
                lines.append(f"- `{f}`")
            lines.append("")
    else:
        lines += ["_No gaps — all adapter files have Level 4 headers. ✅_", ""]

    lines += ["---", ""]

    # ----- Triage guidance -----
    lines += [
        "## Triage Guidance",
        "",
        "| Action | Gap | Steps |",
        "|--------|-----|-------|",
        "| Assign to workstream | GAP_A | Open `FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`, find the correct WS section, add a table row |",
        "| Mark as excluded | GAP_A | Add to the `Intentionally Excluded Directories` table in the inventory |",
        "| Remove stale entry | GAP_B | Delete the table row from the inventory; check if any PUML also references it (→ GAP_D) |",
        "| Add PUML reference | GAP_C | In the appropriate diagram's note block, add a bullet: `- src/.../module/file.py (N lines)` |",
        "| Fix broken PUML ref | GAP_D | Update the path to the file's new location, or remove the note entirely |",
        "| Add L4 header | GAP_E | Insert `# --- Level 4 registry metadata ---` block after module docstring; re-run harvester |",
        "",
        "_Re-run this script after making changes to verify gaps are closed._",
        "",
    ]

    report = "\n".join(lines) + "\n"

    if write:
        output_path.write_text(report, encoding="utf-8")
        print(f"Report written to: {output_path}")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root directory (default: auto-detect from script location)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output report path (default: <repo-root>/{DEFAULT_OUTPUT_RELATIVE})",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print report to stdout instead of writing to file",
    )
    parser.add_argument(
        "--gap",
        choices=["A", "B", "C", "D", "E"],
        default=None,
        help="Show only a specific gap category in the console summary",
    )
    parser.add_argument(
        "--scope",
        choices=["all", "src", "scripts", "modal"],
        default="all",
        help="Limit gap analysis to files in a specific top-level directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw gap data as JSON to stdout (in addition to writing the report)",
    )
    return parser


def _resolve_repo_root(provided: Path | None) -> Path:
    """Auto-detect repo root from this script's location or use provided path."""
    if provided is not None:
        return provided.resolve()
    # This script lives at <repo_root>/scripts/audit_diagram_file_coverage.py
    return Path(__file__).resolve().parent.parent


def _apply_scope_filter(paths: set[str], scope: str) -> set[str]:
    """Filter a path set to the requested scope."""
    if scope == "all":
        return paths
    prefix = scope.rstrip("/") + "/"
    return {p for p in paths if p.startswith(prefix)}


def main() -> int:
    """Entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    repo_root = _resolve_repo_root(args.repo_root)
    output_path = args.output or repo_root / DEFAULT_OUTPUT_RELATIVE

    print(f"Repository root : {repo_root}")
    print(f"Inventory       : {repo_root / INVENTORY_RELATIVE}")
    print(f"Diagrams dir    : {repo_root / DIAGRAMS_RELATIVE}")
    print()

    # Collect data
    print("Collecting git-tracked files …")
    git_files = get_git_tracked_files(repo_root)

    print("Parsing FILE_INVENTORY …")
    inventory_files = parse_inventory(repo_root / INVENTORY_RELATIVE)

    print("Parsing PUML diagrams …")
    puml_refs = parse_puml_references(repo_root / DIAGRAMS_RELATIVE)

    # Apply scope filter
    if args.scope != "all":
        git_files = _apply_scope_filter(git_files, args.scope)
        inventory_files = _apply_scope_filter(inventory_files, args.scope)

    print(
        f"\nFound {len(git_files)} git files, "
        f"{len(inventory_files)} inventory entries, "
        f"{len(puml_refs)} PUML references ({len({r.source_puml for r in puml_refs})} diagrams)\n"
    )

    # Compute gaps
    gaps = compute_gaps(git_files, inventory_files, puml_refs)
    populate_gap_e(gaps, repo_root, git_files)

    # Console summary
    l4_total = len(gaps.l4_covered) + len(gaps.missing_l4_headers)
    l4_pct = len(gaps.l4_covered) / l4_total * 100 if l4_total else 100.0
    print("Gap summary:")
    print(f"  GAP_A (git, not in inventory)  : {len(gaps.new_not_in_inventory)}")
    print(f"  GAP_B (inventory, not in git)  : {len(gaps.stale_not_in_git)}")
    print(f"  GAP_C (git, no PUML reference) : {len(gaps.undocumented_in_puml)}")
    print(f"  GAP_D (broken PUML references) : {len(gaps.broken_puml_refs)}")
    print(f"  GAP_E (adapter missing L4 hdr) : {len(gaps.missing_l4_headers)}")
    print(
        f"  L4_COVERED                     : {len(gaps.l4_covered)}/{l4_total} ({l4_pct:.1f}%)"
    )
    print()

    # Optionally show specific gap details on console
    if args.gap == "A" and gaps.new_not_in_inventory:
        print("GAP_A files:")
        for p in sorted(gaps.new_not_in_inventory):
            print(f"  {p}")
    elif args.gap == "B" and gaps.stale_not_in_git:
        print("GAP_B files:")
        for p in sorted(gaps.stale_not_in_git):
            print(f"  {p}")
    elif args.gap == "C" and gaps.undocumented_in_puml:
        print("GAP_C files:")
        for p in sorted(gaps.undocumented_in_puml):
            print(f"  {p}")
    elif args.gap == "D" and gaps.broken_puml_refs:
        print("GAP_D references:")
        for ref in gaps.broken_puml_refs:
            print(f"  {ref.normalized_path} (in {ref.source_puml})")
    elif args.gap == "E" and gaps.missing_l4_headers:
        print("GAP_E files (missing __l4_category__):")
        for p in sorted(gaps.missing_l4_headers):
            print(f"  {p}")

    # JSON output
    if args.json:
        data = {
            "generated": datetime.now().isoformat(),
            "stats": {
                "git_files": len(git_files),
                "inventory_files": len(inventory_files),
                "puml_references": len(puml_refs),
                "l4_covered": len(gaps.l4_covered),
                "l4_total_adapters": l4_total,
            },
            "gap_a": sorted(gaps.new_not_in_inventory),
            "gap_b": sorted(gaps.stale_not_in_git),
            "gap_c": sorted(gaps.undocumented_in_puml),
            "gap_d": [
                {"path": r.normalized_path, "raw": r.raw_path, "puml": r.source_puml}
                for r in gaps.broken_puml_refs
            ],
            "gap_e": sorted(gaps.missing_l4_headers),
            "l4_covered": sorted(gaps.l4_covered),
        }
        print(json.dumps(data, indent=2))

    # Write report
    report = generate_report(
        gaps,
        git_files,
        inventory_files,
        puml_refs,
        output_path,
        write=not args.no_write,
    )

    if args.no_write:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
