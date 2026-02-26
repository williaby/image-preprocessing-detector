#!/usr/bin/env python3
"""GAP_C triage: enrich undocumented files with staleness signals and score for review.

Reads the GAP_C file list from audit_diagram_file_coverage.py and enriches
each file with five signals to help distinguish genuinely outdated files from
current files that are simply not yet documented in PUML diagrams.

Triage buckets:
  REVIEW_REMOVE   (score >= 60) — strong staleness signals; review for deletion
  REVIEW_NEEDED   (score 35-59) — mixed signals; needs human judgment
  PROBABLY_CURRENT (score < 35)  — likely still active, just undocumented

Usage:
  python scripts/triage_gap_c.py
  python scripts/triage_gap_c.py --scope src --bucket REVIEW_REMOVE
  python scripts/triage_gap_c.py --no-write
  python scripts/triage_gap_c.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Bootstrap: resolve repo root and import audit module
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from audit_diagram_file_coverage import (
    compute_gaps,
    get_git_tracked_files,
    parse_inventory,
    parse_puml_references,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIAGRAMS_RELATIVE = "docs/architecture/diagrams"
INVENTORY_RELATIVE = "docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md"
DEFAULT_OUTPUT_RELATIVE = "docs/architecture/GAP_C_TRIAGE_REPORT.md"

BUCKET_REMOVE = "REVIEW_REMOVE"
BUCKET_NEEDED = "REVIEW_NEEDED"
BUCKET_CURRENT = "PROBABLY_CURRENT"

# Thresholds are calibrated for repos < 6 months old where age signals contribute 0.
# Age bonuses (up to +35) would push these higher in older repos.
BUCKET_REMOVE_THRESHOLD = 40
BUCKET_NEEDED_THRESHOLD = 25

# Files that are always legitimate and should be skipped entirely
# (PEP 561 marker, empty package stubs, etc.)
SKIP_FILENAMES: frozenset[str] = frozenset({"py.typed", ".gitkeep", "__pycache__"})

# Directory subtrees where modules are dynamically discovered (registry/plugin pattern).
# Files in these directories will always show import_count=0 because they are loaded
# via importlib/pkgutil auto-discovery, NOT via direct import statements. Applying
# the no-importers signal here produces false positives.
DYNAMIC_IMPORT_DIRS: tuple[str, ...] = (
    "annotation/parsers/",  # registry.py auto-discovers all parser subclasses
)

# Naming patterns that indicate a file may be outdated.
# Tuple: (flag_name, regex_pattern, score_weight)
STALE_PATTERNS: list[tuple[str, str, int]] = [
    ("phase_ref", r"phase[0-9]", 25),
    ("old_legacy", r"(?:old|legacy|deprecated|backup)", 25),
    ("download", r"^download_", 15),
    ("colab", r"colab", 20),
    ("convert_once", r"^convert_", 10),
    ("test_script", r"^test_", 5),
    ("poc", r"^poc_", 15),
    ("temp", r"(?:^tmp_|^temp_)", 20),
]

_COMPILED_PATTERNS = [
    (name, re.compile(pat, re.IGNORECASE), weight)
    for name, pat, weight in STALE_PATTERNS
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FileSignals:
    """Enrichment signals for a single GAP_C file."""

    filepath: str
    creation_age_months: float  # months since FIRST commit (file creation date)
    last_touched_months: float  # months since LAST commit (may be a bulk rename)
    commit_count: int
    loc: int
    import_count: int  # -1 means "not applicable" (scripts/)
    config_ref_count: int  # -1 means "not applicable"
    naming_flags: list[str]
    naming_score: int
    score: int = 0
    bucket: str = BUCKET_CURRENT
    score_reasons: list[str] = field(default_factory=list)


class BulkFileStats(NamedTuple):
    last_commit_dates: dict[str, datetime]
    first_commit_dates: dict[str, datetime]  # file creation dates
    commit_counts: dict[str, int]


# ---------------------------------------------------------------------------
# Signal 1 & 2 — Age and commit count (single bulk git log pass)
# ---------------------------------------------------------------------------


def _parse_git_date(date_str: str) -> datetime | None:
    """Parse a git ISO-format date string to a timezone-aware datetime."""
    date_str = date_str.strip()
    if not date_str:
        return None
    # git outputs: "2025-08-20 14:22:00 +0000"
    try:
        # Remove timezone offset for simple parsing, treat as UTC
        parts = date_str.rsplit(" ", 1)
        dt = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def get_bulk_file_stats(repo_root: Path) -> BulkFileStats:
    """Collect first/last commit dates and commit counts in one git log pass.

    Iterates commits newest-first with file names. For each file:
    - First occurrence  → most recent commit date (last_commit_dates)
    - Last occurrence   → oldest commit date, i.e. when it was created (first_commit_dates)
    - Total occurrences → commit_count

    This single pass replaces N per-file ``git log -1`` calls.

    Note: ``--follow`` is not used here to keep the call fast; rename tracking
    would require per-file calls and is unnecessary for staleness detection.
    """
    result = subprocess.run(
        [
            "git",
            "log",
            "--format=COMMIT %ai",
            "--name-only",
            "--diff-filter=ACDMR",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    last_dates: dict[str, datetime] = {}
    first_dates: dict[str, datetime] = {}
    commit_counter: Counter[str] = Counter()
    current_date: datetime | None = None

    for line in result.stdout.splitlines():
        if line.startswith("COMMIT "):
            current_date = _parse_git_date(line[7:])
        elif line.strip() and current_date is not None:
            fp = line.strip()
            if fp not in last_dates:
                # Newest-first → first occurrence = most recent commit
                last_dates[fp] = current_date
            # Every occurrence → last occurrence = first/oldest commit (creation)
            first_dates[fp] = current_date
            commit_counter[fp] += 1

    return BulkFileStats(
        last_commit_dates=last_dates,
        first_commit_dates=first_dates,
        commit_counts=dict(commit_counter),
    )


def _months_since(dt: datetime | None) -> float:
    """Return months elapsed since dt, or 999 if dt is None (never committed)."""
    if dt is None:
        return 999.0
    now = datetime.now(tz=UTC)
    delta = now - dt
    return delta.days / 30.44


# ---------------------------------------------------------------------------
# Signal 3 — LOC
# ---------------------------------------------------------------------------


def get_loc(repo_root: Path, filepath: str) -> int:
    """Return line count for a file, or 0 if unreadable."""
    try:
        return len((repo_root / filepath).read_text(errors="replace").splitlines())
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Signal 4 — Import count (src/ only)
# ---------------------------------------------------------------------------


def build_import_index(repo_root: Path, git_files: set[str]) -> dict[str, int]:
    """Build {module_stem -> count_of_files_that_import_it} by scanning all tracked .py files.

    Reads every tracked Python file once and counts how many unique files
    reference each module stem via import statements.
    """
    # Capture full module path then split on "." to get the stem.
    # e.g. "from a.b.enums import X" -> captures "a.b.enums" -> stem "enums"
    #      "from .enums import X"    -> captures ".enums"    -> stem "enums"
    # Use ^\s* (not just ^) so indented imports inside if TYPE_CHECKING / try
    # blocks are also counted. The old regex r"from\s+[\w.]*\.?(\w+)\s+import"
    # was greedy-backtracking incorrectly, yielding only the last character.
    from_pattern = re.compile(r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE)
    import_pattern = re.compile(r"^\s*import\s+([\w]+)", re.MULTILINE)

    module_ref_files: dict[str, set[str]] = {}

    for fp in git_files:
        if not fp.endswith(".py"):
            continue
        try:
            content = (repo_root / fp).read_text(errors="replace")
        except OSError:
            continue

        imported: set[str] = set()
        for m in from_pattern.finditer(content):
            stem = m.group(1).split(".")[-1]
            if stem:  # skip "from . import X" which gives empty stem
                imported.add(stem)
        imported.update(import_pattern.findall(content))

        for mod in imported:
            if mod not in module_ref_files:
                module_ref_files[mod] = set()
            module_ref_files[mod].add(fp)

    return {mod: len(files) for mod, files in module_ref_files.items()}


def get_import_count(filepath: str, import_index: dict[str, int]) -> int:
    """Look up how many files import the module defined at filepath."""
    stem = Path(filepath).stem
    return import_index.get(stem, 0)


# ---------------------------------------------------------------------------
# Signal 5 — Naming pattern flags
# ---------------------------------------------------------------------------


def get_naming_flags(filepath: str) -> tuple[list[str], int]:
    """Return (matched_flag_names, total_score) for stale naming patterns."""
    filename = Path(filepath).name
    flags: list[str] = []
    total_weight = 0
    for name, pattern, weight in _COMPILED_PATTERNS:
        if pattern.search(filename):
            flags.append(name)
            total_weight += weight
    return flags, total_weight


# ---------------------------------------------------------------------------
# Config file reference check (config/ only)
# ---------------------------------------------------------------------------


def get_config_ref_count(repo_root: Path, filepath: str) -> int:
    """Count how many tracked Python files reference this config file by name."""
    config_stem = Path(
        filepath
    ).stem  # e.g., "siglip2_multitask" from siglip2_multitask.yaml
    result = subprocess.run(
        ["git", "grep", "-l", config_stem, "--", "*.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return len(result.stdout.splitlines())


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _score_age(
    age_months: float, base_score: int, medium_score: int, low_score: int
) -> tuple[int, str]:
    if age_months >= 18:
        return base_score, f"age≥18mo (+{base_score})"
    if age_months >= 12:
        return medium_score, f"age≥12mo (+{medium_score})"
    if age_months >= 6:
        return low_score, f"age≥6mo (+{low_score})"
    return 0, ""


def score_src_file(signals: FileSignals) -> None:
    """Apply scoring rules for src/ library files (in-place mutation).

    Uses creation_age_months (first commit) rather than last-touched date so
    that bulk rename/reformat commits don't reset the staleness clock.

    Special cases:
    - ``__init__.py`` files: import_count is always 0 (imported via package path,
      not by stem), so the no-importers signal is skipped for them.
    - Files in ``DYNAMIC_IMPORT_DIRS``: loaded via importlib/pkgutil auto-discovery,
      never directly imported, so the no-importers signal is skipped for them too.
    - Large files (LOC > 200) with a single commit are NOT flagged as stubs;
      the single-commit bonus is halved to reduce false positives.
    """
    total = 0
    reasons: list[str] = []
    is_init = signals.filepath.endswith("__init__.py")

    pts, reason = _score_age(
        signals.creation_age_months, base_score=30, medium_score=15, low_score=5
    )
    total += pts
    if reason:
        reasons.append(reason)

    if signals.commit_count == 1:
        # Large single-commit files are probably active, not stubs
        bonus = 10 if signals.loc > 200 else 20
        total += bonus
        reasons.append(f"single-commit (+{bonus})")
    elif signals.commit_count <= 3:
        total += 5
        reasons.append("≤3 commits (+5)")

    # __init__.py and registry-pattern plugin dirs always show import_count=0 by design
    # — skip to avoid false positives for both cases.
    is_dynamic_plugin = any(d in signals.filepath for d in DYNAMIC_IMPORT_DIRS)
    if not is_init and not is_dynamic_plugin and signals.import_count == 0:
        total += 20
        reasons.append("no-importers (+20)")
    elif not is_init and not is_dynamic_plugin and signals.import_count == 1:
        total += 5
        reasons.append("1 importer (+5)")

    if signals.loc <= 30:
        total += 10
        reasons.append(f"stub ({signals.loc}LOC +10)")

    total += signals.naming_score
    if signals.naming_flags:
        reasons.append(
            f"naming:{','.join(signals.naming_flags)} (+{signals.naming_score})"
        )

    signals.score = total
    signals.score_reasons = reasons


def score_scripts_file(signals: FileSignals) -> None:
    """Apply scoring rules for scripts/ entry-point files (in-place mutation).

    Uses creation_age_months (first commit) to avoid bulk rename commits
    resetting the staleness clock. import_count is NOT scored since entry-point
    scripts are not imported by other files by design.
    """
    total = 0
    reasons: list[str] = []

    pts, reason = _score_age(
        signals.creation_age_months, base_score=35, medium_score=20, low_score=5
    )
    total += pts
    if reason:
        reasons.append(reason)

    if signals.commit_count == 1:
        # Large single-commit scripts are probably still in active use
        bonus = 10 if signals.loc > 200 else 25
        total += bonus
        reasons.append(f"single-commit (+{bonus})")
    elif signals.commit_count <= 3:
        total += 8
        reasons.append("≤3 commits (+8)")

    if signals.loc <= 20:
        total += 10
        reasons.append(f"stub ({signals.loc}LOC +10)")

    total += signals.naming_score
    if signals.naming_flags:
        reasons.append(
            f"naming:{','.join(signals.naming_flags)} (+{signals.naming_score})"
        )

    signals.score = total
    signals.score_reasons = reasons


def score_config_file(signals: FileSignals) -> None:
    """Apply scoring rules for config/ YAML files (in-place mutation)."""
    total = 0
    reasons: list[str] = []

    pts, reason = _score_age(
        signals.creation_age_months, base_score=20, medium_score=10, low_score=0
    )
    total += pts
    if reason:
        reasons.append(reason)

    if signals.config_ref_count == 0:
        total += 40
        reasons.append("no-py-refs (+40)")
    elif signals.config_ref_count == 1:
        total += 5
        reasons.append("1 py-ref (+5)")

    total += signals.naming_score
    if signals.naming_flags:
        reasons.append(
            f"naming:{','.join(signals.naming_flags)} (+{signals.naming_score})"
        )

    signals.score = total
    signals.score_reasons = reasons


def score_modal_or_tools_file(signals: FileSignals) -> None:
    """Apply scoring rules for modal/ and tools/ files (in-place mutation)."""
    total = 0
    reasons: list[str] = []

    pts, reason = _score_age(
        signals.creation_age_months, base_score=25, medium_score=12, low_score=5
    )
    total += pts
    if reason:
        reasons.append(reason)

    if signals.commit_count == 1:
        total += 20
        reasons.append("single-commit (+20)")

    total += signals.naming_score
    if signals.naming_flags:
        reasons.append(
            f"naming:{','.join(signals.naming_flags)} (+{signals.naming_score})"
        )

    signals.score = total
    signals.score_reasons = reasons


def assign_bucket(signals: FileSignals) -> None:
    """Set signals.bucket based on score (in-place mutation)."""
    if signals.score >= BUCKET_REMOVE_THRESHOLD:
        signals.bucket = BUCKET_REMOVE
    elif signals.score >= BUCKET_NEEDED_THRESHOLD:
        signals.bucket = BUCKET_NEEDED
    else:
        signals.bucket = BUCKET_CURRENT


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def enrich_and_score(
    gap_c: set[str],
    repo_root: Path,
    git_files: set[str],
    import_index: dict[str, int],
    bulk_stats: BulkFileStats,
) -> list[FileSignals]:
    """Build FileSignals for every GAP_C file, score, and assign bucket."""
    results: list[FileSignals] = []

    for filepath in sorted(gap_c):
        # Skip known-legitimate non-code marker files
        if Path(filepath).name in SKIP_FILENAMES:
            continue

        top_dir = filepath.split("/")[0]
        first_date = bulk_stats.first_commit_dates.get(filepath)
        last_date = bulk_stats.last_commit_dates.get(filepath)
        creation_age_months = _months_since(first_date)
        last_touched_months = _months_since(last_date)
        commit_count = bulk_stats.commit_counts.get(filepath, 0)
        loc = get_loc(repo_root, filepath)
        naming_flags, naming_score = get_naming_flags(filepath)

        # Compute directory-specific signals
        if top_dir == "src":
            import_count = get_import_count(filepath, import_index)
            config_ref_count = -1
        elif top_dir == "config":
            import_count = -1
            config_ref_count = get_config_ref_count(repo_root, filepath)
        else:
            import_count = -1
            config_ref_count = -1

        signals = FileSignals(
            filepath=filepath,
            creation_age_months=creation_age_months,
            last_touched_months=last_touched_months,
            commit_count=commit_count,
            loc=loc,
            import_count=import_count,
            config_ref_count=config_ref_count,
            naming_flags=naming_flags,
            naming_score=naming_score,
        )

        # Apply directory-appropriate scoring
        if top_dir == "src":
            score_src_file(signals)
        elif top_dir == "scripts":
            score_scripts_file(signals)
        elif top_dir == "config":
            score_config_file(signals)
        else:
            score_modal_or_tools_file(signals)

        assign_bucket(signals)
        results.append(signals)

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _age_str(months: float) -> str:
    """Format months as a human-readable age string."""
    if months >= 999:
        return "never"
    return f"{months:.0f}mo"


def _import_str(count: int) -> str:
    if count == -1:
        return "n/a"
    return str(count)


def _config_ref_str(count: int) -> str:
    if count == -1:
        return "n/a"
    return str(count)


def _bucket_table(scored: list[FileSignals], bucket: str) -> list[str]:
    """Render a sorted table for one bucket."""
    items = [s for s in scored if s.bucket == bucket]
    items.sort(key=lambda s: s.score, reverse=True)

    if not items:
        return ["_No files in this bucket._", ""]

    lines = [
        "| File | Score | Created | Last Touched | Commits | LOC | Importers | Flags |",
        "| ---- | ----- | ------- | ------------ | ------- | --- | --------- | ----- |",
    ]
    for s in items:
        lines.append(
            f"| `{s.filepath}` | {s.score}"
            f" | {_age_str(s.creation_age_months)}"
            f" | {_age_str(s.last_touched_months)}"
            f" | {s.commit_count}"
            f" | {s.loc}"
            f" | {_import_str(s.import_count)}"
            f" | {', '.join(s.naming_flags) if s.naming_flags else '—'} |"
        )
    lines.append("")
    return lines


def _bucket_condensed(scored: list[FileSignals], bucket: str) -> list[str]:
    """Render a compact list for the PROBABLY_CURRENT bucket."""
    items = [s for s in scored if s.bucket == bucket]
    items.sort(key=lambda s: (s.filepath.split("/")[0], s.filepath))

    if not items:
        return ["_No files in this bucket._", ""]

    lines: list[str] = []
    current_dir: str = ""
    for s in items:
        top = s.filepath.split("/")[0] + "/"
        if top != current_dir:
            current_dir = top
            lines.append(
                f"**`{top}`** ({sum(1 for x in items if x.filepath.startswith(top.rstrip('/')))} files)"
            )
            lines.append("")
        lines.append(
            f"- `{s.filepath}` — created {_age_str(s.creation_age_months)} ago, {s.commit_count} commits, {s.loc} LOC"
        )
    lines.append("")
    return lines


def generate_report(
    scored: list[FileSignals],
    output_path: Path,
    *,
    write: bool = True,
) -> str:
    """Render the triage report as markdown and optionally write to disk."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    bucket_counts: dict[str, int] = Counter(s.bucket for s in scored)
    dir_counts: dict[str, int] = Counter(s.filepath.split("/")[0] + "/" for s in scored)

    # Summary by bucket x directory
    dirs = sorted(dir_counts)
    lines: list[str] = [
        "---",
        "title: GAP_C Triage Report — Undocumented File Staleness Review",
        f"generated: {now}",
        "schema_type: common",
        "status: generated",
        "---",
        "",
        "# GAP_C Triage Report",
        "",
        f"> **Generated**: {now}  ",
        "> **Script**: `scripts/triage_gap_c.py`  ",
        "> **Source**: GAP_C from `scripts/audit_diagram_file_coverage.py`",
        "",
        "Files in git with no PUML architecture diagram reference, scored for staleness.",
        "This report is a **review aid** — no files are deleted automatically.",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Bucket | Count | Action |",
        "| ------ | ----- | ------ |",
        f"| REVIEW_REMOVE (score ≥ {BUCKET_REMOVE_THRESHOLD}) | {bucket_counts.get(BUCKET_REMOVE, 0)} | Review each; delete or archive if confirmed outdated |",
        f"| REVIEW_NEEDED (score {BUCKET_NEEDED_THRESHOLD}-{BUCKET_REMOVE_THRESHOLD - 1}) | {bucket_counts.get(BUCKET_NEEDED, 0)} | Human judgment required |",
        f"| PROBABLY_CURRENT (score < {BUCKET_NEEDED_THRESHOLD}) | {bucket_counts.get(BUCKET_CURRENT, 0)} | Likely active; add PUML reference if warranted |",
        "",
        "| Directory | Total | REVIEW_REMOVE | REVIEW_NEEDED | PROBABLY_CURRENT |",
        "| --------- | ----- | ------------- | ------------- | ---------------- |",
    ]
    for d in dirs:
        d_items = [s for s in scored if s.filepath.startswith(d.rstrip("/"))]
        remove = sum(1 for s in d_items if s.bucket == BUCKET_REMOVE)
        needed = sum(1 for s in d_items if s.bucket == BUCKET_NEEDED)
        current = sum(1 for s in d_items if s.bucket == BUCKET_CURRENT)
        lines.append(f"| `{d}` | {len(d_items)} | {remove} | {needed} | {current} |")
    lines += ["", "---", ""]

    # REVIEW_REMOVE
    lines += [
        f"## {BUCKET_REMOVE}",
        "",
        "Strong staleness signals. Review each file and delete or archive if confirmed outdated.",
        "Check git blame and search for any remaining callers before deleting.",
        "",
    ]
    lines += _bucket_table(scored, BUCKET_REMOVE)
    lines += ["---", ""]

    # REVIEW_NEEDED
    lines += [
        f"## {BUCKET_NEEDED}",
        "",
        "Mixed signals. Requires human judgment — check if the file is still",
        "imported, called by a Makefile/CI target, or referenced in docs.",
        "",
    ]
    lines += _bucket_table(scored, BUCKET_NEEDED)
    lines += ["---", ""]

    # PROBABLY_CURRENT
    lines += [
        f"## {BUCKET_CURRENT}",
        "",
        "Low staleness score — these files are likely still active and simply",
        "not yet documented in an architecture diagram.",
        "Consider adding a reference to the appropriate PUML diagram.",
        "",
    ]
    lines += _bucket_condensed(scored, BUCKET_CURRENT)
    lines += ["---", ""]

    # Next steps
    lines += [
        "## Next Steps",
        "",
        "| Action | Bucket | How |",
        "| ------ | ------ | --- |",
        "| Delete outdated file | REVIEW_REMOVE | Confirm no callers, then `git rm <file>` |",
        "| Archive to docs/ | REVIEW_REMOVE | Move to `docs/_archived/` with a dated note |",
        "| Keep and accept | REVIEW_REMOVE/NEEDED | Add to FILE_INVENTORY Intentionally Excluded table |",
        "| Add PUML reference | PROBABLY_CURRENT | In the appropriate diagram note: `- src/.../module.py (N lines)` |",
        "",
        "_Re-run `scripts/audit_diagram_file_coverage.py` after changes to verify gap closure._",
        "",
    ]

    report = "\n".join(lines) + "\n"

    if write:
        output_path.write_text(report, encoding="utf-8")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--scope",
        choices=["src", "scripts", "modal", "config", "tools", "all"],
        default="all",
    )
    parser.add_argument(
        "--bucket",
        choices=[BUCKET_REMOVE, BUCKET_NEEDED, BUCKET_CURRENT],
        default=None,
        help="Print files in a specific bucket to stdout",
    )
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    return parser


def _apply_scope(files: set[str], scope: str) -> set[str]:
    if scope == "all":
        return files
    prefix = scope.rstrip("/") + "/"
    return {f for f in files if f.startswith(prefix)}


def main() -> int:
    """Entry point."""
    args = _build_parser().parse_args()
    repo_root: Path = args.repo_root.resolve()
    output_path: Path = args.output or repo_root / DEFAULT_OUTPUT_RELATIVE

    # When --json is active, route all status output to stderr so stdout
    # contains only parseable JSON.
    def log(msg: str) -> None:
        if args.json:
            print(msg, file=sys.stderr)
        else:
            print(msg)

    log("Collecting git-tracked files …")
    git_files = get_git_tracked_files(repo_root)

    log("Parsing FILE_INVENTORY …")
    inventory_files = parse_inventory(repo_root / INVENTORY_RELATIVE)

    log("Parsing PUML diagrams …")
    puml_refs = parse_puml_references(repo_root / DIAGRAMS_RELATIVE)

    gaps = compute_gaps(git_files, inventory_files, puml_refs)
    gap_c = _apply_scope(gaps.undocumented_in_puml, args.scope)

    log(f"GAP_C files to triage: {len(gap_c)}")
    log("Building bulk git stats (single git log pass) …")
    bulk_stats = get_bulk_file_stats(repo_root)

    log("Building import index (scanning all tracked .py files) …")
    import_index = build_import_index(repo_root, git_files)

    log(
        f"Checking config references for {sum(1 for f in gap_c if f.startswith('config/'))} config files …"
    )
    scored = enrich_and_score(gap_c, repo_root, git_files, import_index, bulk_stats)

    # Apply min-score filter for console output
    filtered = [s for s in scored if s.score >= args.min_score]

    # Console summary
    bucket_counts: dict[str, int] = Counter(s.bucket for s in scored)
    log(f"\nTriage results ({len(gap_c)} files):")
    log(f"  {BUCKET_REMOVE:<20}: {bucket_counts.get(BUCKET_REMOVE, 0)}")
    log(f"  {BUCKET_NEEDED:<20}: {bucket_counts.get(BUCKET_NEEDED, 0)}")
    log(f"  {BUCKET_CURRENT:<20}: {bucket_counts.get(BUCKET_CURRENT, 0)}")
    log("")

    # Optional bucket detail on console
    if args.bucket:
        items = [s for s in filtered if s.bucket == args.bucket]
        items.sort(key=lambda s: s.score, reverse=True)
        for s in items:
            log(
                f"  [{s.score:3d}] {s.filepath}"
                f"  created={_age_str(s.creation_age_months)} touched={_age_str(s.last_touched_months)}"
                f" | {s.commit_count}c | {s.loc}L"
                f" | importers={_import_str(s.import_count)}"
                + (f" | {','.join(s.naming_flags)}" if s.naming_flags else "")
            )
        log("")

    # JSON output
    if args.json:
        data = {
            "generated": datetime.now().isoformat(),
            "totals": dict(bucket_counts),
            "files": [
                {
                    "path": s.filepath,
                    "score": s.score,
                    "bucket": s.bucket,
                    "creation_age_months": round(s.creation_age_months, 1),
                    "last_touched_months": round(s.last_touched_months, 1),
                    "commit_count": s.commit_count,
                    "loc": s.loc,
                    "import_count": s.import_count,
                    "config_ref_count": s.config_ref_count,
                    "naming_flags": s.naming_flags,
                    "reasons": s.score_reasons,
                }
                for s in sorted(scored, key=lambda s: s.score, reverse=True)
            ],
        }
        print(json.dumps(data, indent=2))

    # Write report
    report = generate_report(scored, output_path, write=not args.no_write)
    if not args.no_write:
        log(f"Report written to: {output_path}")
    elif not args.json:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
