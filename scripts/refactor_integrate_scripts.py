#!/usr/bin/env python3
"""One-shot refactor: replace duplicated function/constant definitions in all
integrate_*_enrichments.py scripts with imports from l2_integration_utils.

Run from the repo root:
    PYTHONPATH=. uv run python3 scripts/refactor_integrate_scripts.py [--dry-run]

What it does per file:
  1. Detects which shared items (functions / constants) are defined locally.
  2. Removes those local definitions.
  3. Inserts a single `from l2_integration_utils import (...)` block after
     the existing imports section.
  4. Writes the result back in-place (or prints a diff in --dry-run mode).
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared items we want to remove from individual scripts and import centrally
# ---------------------------------------------------------------------------

# Maps importable name -> regex that matches its full definition block.
# Each regex anchors at the start of a line and captures everything up to
# (but not including) the next top-level `def` or `class` statement or EOF.
# We use a non-greedy match within the function block heuristic:
#   "^def NAME" ... up to the next "^def " / "^class " / "^# ===" block or EOF

SHARED_FUNCTIONS = [
    "load_metadata",
    "load_llm_enrichment",
    "load_language_enrichment",
    "load_skew_labels",
    "load_resolution_labels",
    "compute_text_statistics",
    "derive_content_flags",
    "compute_reliability_summary",
]

SHARED_CONSTANTS = [
    "DOCLING_TO_DOCLAYNET",
    "SCRIPT_TO_TEXT_DIRECTION",
    "TABLE_CLASSES",
    "FORMULA_CLASSES",
    "FIGURE_CLASSES",
    "CODE_CLASSES",
]

# Regex that matches the leading comment block for DOCLING_TO_DOCLAYNET only
# (the "Full Docling lowercase..." comment, not the KI-001 toggle or comment)
_DOCLING_COMMENT_RE = re.compile(
    r"^# Full Docling lowercase[^\n]*\n(?:# [^\n]*\n)*",
    re.MULTILINE,
)

# NOTE: We do NOT remove APPLY_KI_001_LAYOUT_CASING — it is a per-dataset
# toggle referenced by standardize_class_name() which stays in each script.
# We also do NOT remove the KI-001 comment block for the same reason.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_func_pattern(name: str) -> re.Pattern[str]:
    """Return a regex that matches ``def name(...)`` through its entire body."""
    # Match from `def name` at column 0 through the next line that starts a
    # new top-level definition, a section separator, or end-of-string.
    return re.compile(
        rf"^def {re.escape(name)}\b.*?(?=^def |\Z)",
        re.MULTILINE | re.DOTALL,
    )


def _build_const_pattern(name: str) -> re.Pattern[str]:
    """Return a regex for a module-level constant assignment block."""
    return re.compile(
        rf"^{re.escape(name)}\s*(?::\s*[^\n]+)?\s*=\s*(?:"
        # dict/frozenset/set literal spanning multiple lines
        r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        r"|"
        # single-line value (e.g. True, None, "string")
        r"[^\n]+"
        r")\n",
        re.MULTILINE | re.DOTALL,
    )


def _remove_definitions(source: str) -> tuple[str, list[str]]:
    """Remove shared function/constant definitions and return (new_source, removed_names)."""
    removed: list[str] = []

    for name in SHARED_FUNCTIONS:
        pat = _build_func_pattern(name)
        if pat.search(source):
            source = pat.sub("", source)
            removed.append(name)

    for name in SHARED_CONSTANTS:
        pat = _build_const_pattern(name)
        if pat.search(source):
            source = pat.sub("", source)
            removed.append(name)

    # Remove just the "Full Docling lowercase..." comment above DOCLING_TO_DOCLAYNET
    # (the KI-001 toggle and its comment block are left in place — they are
    # referenced by standardize_class_name() which stays in each script)
    if "DOCLING_TO_DOCLAYNET" in removed:
        source = _DOCLING_COMMENT_RE.sub("", source)

    return source, removed


def _build_import_block(removed: list[str]) -> str:
    """Build the `from l2_integration_utils import (...)` statement."""
    # Separate functions and constants for readability
    funcs = [n for n in removed if n in SHARED_FUNCTIONS]
    consts = [n for n in removed if n in SHARED_CONSTANTS]

    names: list[str] = sorted(funcs) + sorted(consts)
    if not names:
        return ""

    lines = ["from l2_integration_utils import ("]
    for n in names:
        lines.append(f"    {n},")
    lines.append(")")
    return "\n".join(lines) + "\n"


def _insert_import(source: str, import_block: str) -> str:
    """Insert import_block after the last complete top-level import block.

    Handles both single-line imports and parenthesised multi-line imports
    by tracking paren depth to find the true end of each import statement.
    """
    if not import_block:
        return source

    lines = source.splitlines(keepends=True)

    last_import_end = -1  # index of the last line that closes an import block
    paren_depth = 0
    in_import = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if in_import:
            paren_depth += line.count("(") - line.count(")")
            if paren_depth <= 0:
                in_import = False
                paren_depth = 0
                last_import_end = i
            continue

        if stripped.startswith("import ") or stripped.startswith("from "):
            # Skip items we don't want to place our import after
            if "from __future__" in stripped or "l2_integration_utils" in stripped:
                continue
            paren_depth = line.count("(") - line.count(")")
            if paren_depth > 0:
                in_import = True  # multi-line import; track closing paren
            else:
                last_import_end = i  # single-line import ends here

    if last_import_end == -1:
        # Fallback: place after the __future__ import line
        for i, line in enumerate(lines):
            if "from __future__" in line:
                last_import_end = i
                break

    if last_import_end == -1:
        return import_block + "\n" + source

    insert_at = last_import_end + 1
    lines.insert(insert_at, "\n" + import_block)
    return "".join(lines)


def _clean_excess_blank_lines(source: str) -> str:
    """Collapse runs of 3+ blank lines to 2."""
    return re.sub(r"\n{4,}", "\n\n\n", source)


def process_file(path: Path, dry_run: bool = False) -> bool:
    """Process a single integrate script. Returns True if file was changed."""
    original = path.read_text(encoding="utf-8")

    modified, removed = _remove_definitions(original)

    if not removed:
        return False  # Nothing to do

    import_block = _build_import_block(removed)
    modified = _insert_import(modified, import_block)
    modified = _clean_excess_blank_lines(modified)

    if modified == original:
        return False

    if dry_run:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path) + " (modified)",
            n=2,
        )
        sys.stdout.writelines(diff)
        return True

    path.write_text(modified, encoding="utf-8")
    print(f"  Updated: {path.name} (removed: {', '.join(removed)})")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print diffs, do not write")
    parser.add_argument(
        "--file",
        type=Path,
        help="Process a single file instead of all integrate scripts",
    )
    args = parser.parse_args()

    scripts_dir = Path(__file__).parent

    if args.file:
        targets = [args.file]
    else:
        targets = sorted(scripts_dir.glob("integrate_*enrichments*.py"))

    changed = 0
    for path in targets:
        if path.name == "refactor_integrate_scripts.py":
            continue
        if process_file(path, dry_run=args.dry_run):
            changed += 1

    mode = "Would update" if args.dry_run else "Updated"
    print(f"\n{mode} {changed}/{len(targets)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
