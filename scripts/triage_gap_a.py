#!/usr/bin/env python3
"""GAP_A triage: classify git-tracked files that are missing from FILE_INVENTORY.

Reads the GAP_A file list from audit_diagram_file_coverage.py and classifies
each file into one of four categories to guide inventory maintenance:

  NEEDS_INVENTORY  : Core library or training file; should be assigned to a
                     workstream and added to FILE_INVENTORY + a PUML diagram.
  DATASET_ADAPTER  : Per-dataset implementation within a documented framework
                     (e.g. annotation/parsers/). Framework is in inventory;
                     individual adapters need not be.
  OPERATIONAL_SCRIPT: Data-ops, audit, benchmark, or conversion utility that
                     is outside the production architecture scope.
  NEEDS_TRIAGE     : Mixed signals; human judgment required.

Classification uses a two-phase hybrid:
  1. Rule-based (first pass): path/name patterns assign high-confidence cases.
  2. Signal-based scoring (residual src/ files): import count + LOC determine
     whether a module is core library code or an implementation detail.

Usage:
  python scripts/triage_gap_a.py
  python scripts/triage_gap_a.py --scope src --bucket NEEDS_INVENTORY
  python scripts/triage_gap_a.py --no-write
  python scripts/triage_gap_a.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: resolve repo root and import sibling modules
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from audit_diagram_file_coverage import (  # noqa: E402
    _has_l4_header,
    compute_gaps,
    get_git_tracked_files,
    parse_inventory,
    parse_puml_references,
)
from triage_gap_c import (  # noqa: E402
    BulkFileStats,
    SKIP_FILENAMES,
    _months_since,
    build_import_index,
    get_bulk_file_stats,
    get_import_count,
    get_loc,
    get_naming_flags,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIAGRAMS_RELATIVE = "docs/architecture/diagrams"
INVENTORY_RELATIVE = "docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md"
DEFAULT_OUTPUT_RELATIVE = "docs/architecture/GAP_A_TRIAGE_REPORT.md"

BUCKET_INVENTORY = "NEEDS_INVENTORY"
BUCKET_ADAPTER = "DATASET_ADAPTER"
BUCKET_OPERATIONAL = "OPERATIONAL_SCRIPT"
BUCKET_TRIAGE = "NEEDS_TRIAGE"

# Score threshold: src/ files at or above this are classified NEEDS_INVENTORY.
INVENTORY_SCORE_THRESHOLD = 35

# ---------------------------------------------------------------------------
# Rule-based classification patterns
# ---------------------------------------------------------------------------

# Directory subtrees whose files are per-dataset adapter instances.
# The containing framework is already in the inventory; these files need not be.
ADAPTER_DIR_PATTERNS: tuple[str, ...] = (
    "annotation/parsers/",
    "annotation/enrichment/providers/",
    "annotation/storage/backends/",
    "labeling/domain/",
)

# Directory subtrees that are definitively operational/tooling scope.
OPERATIONAL_DIR_PATTERNS: tuple[str, ...] = (
    "scripts/audit/",
    "scripts/benchmarks/",
    "scripts/har/",
)

# Filename patterns (regex on basename) that indicate operational scripts.
# Tuple: (label, compiled_regex)
_OPERATIONAL_NAME_SPECS: tuple[tuple[str, str], ...] = (
    ("integrate_enrichment", r"^integrate_.+_enrichments\.py$"),
    ("download_script",      r"^download_"),
    ("convert_script",       r"^convert_"),
    ("benchmark_script",     r"^benchmark_"),
    ("setup_script",         r"^setup_"),
    ("shell_script",         r"\.sh$"),
    ("colab",                r"colab"),
    ("phase_ref",            r"phase[0-9]"),
)
OPERATIONAL_NAME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in _OPERATIONAL_NAME_SPECS
)

# Path-prefix → workstream hints (first match wins).
# Uses the abbreviated path style (src/.../ expands to full package path at match time).
_WS_HINT_SPECS: tuple[tuple[str, str], ...] = (
    ("ingestion/",       "WS1"),
    ("detection/",       "WS1"),
    ("correction/",      "WS1"),
    ("classification/",  "WS1"),
    ("routing/",         "WS1"),
    ("metrics/",         "WS1"),
    ("output/",          "WS1"),
    ("workers/",         "WS1"),
    ("api/",             "WS1"),
    ("schema_utils/",    "WS1"),
    ("models/",          "WS1"),
    ("pipeline/",        "WS1"),
    ("core/",            "WS1"),
    ("annotation/",      "WS3"),
    ("labeling/",        "WS3"),
    ("monitoring/",      "WS6"),
    ("orchestration/",   "WS1"),
    ("modal/train_",     "WS2"),
    ("modal/",           "WS2"),
    ("scripts/generate_", "WS3"),
    ("scripts/prepare_",  "WS3"),
    ("scripts/build_",    "WS3"),
    ("scripts/label_",    "WS3"),
    ("scripts/derive_",   "WS3"),
    ("scripts/merge_",    "WS3"),
    ("scripts/select_",   "WS3"),
    ("scripts/",          "WS3"),  # fallback: most scripts are data-prep
    ("config/",           "WS2"),  # model/training configs
    ("tools/",            "WS1"),
)

# ---------------------------------------------------------------------------
# File record
# ---------------------------------------------------------------------------


@dataclass
class FileRecord:
    """Signals and classification for one GAP_A file."""

    filepath: str
    creation_age_months: float
    last_touched_months: float
    commit_count: int
    loc: int
    import_count: int  # -1 = not applicable (scripts/modal/config)
    naming_flags: list[str]
    inventory_score: int = 0  # only meaningful for src/ NEEDS_TRIAGE candidates
    classification: str = BUCKET_TRIAGE
    classification_reason: str = ""
    suggested_workstream: str = "?"

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.filepath,
            "classification": self.classification,
            "reason": self.classification_reason,
            "suggested_workstream": self.suggested_workstream,
            "inventory_score": self.inventory_score,
            "creation_age_months": round(self.creation_age_months, 1),
            "last_touched_months": round(self.last_touched_months, 1),
            "commit_count": self.commit_count,
            "loc": self.loc,
            "import_count": self.import_count,
            "naming_flags": self.naming_flags,
        }


# ---------------------------------------------------------------------------
# Workstream inference
# ---------------------------------------------------------------------------


def infer_workstream(filepath: str) -> str:
    """Return the most likely workstream label for a file, or '?' if unknown."""
    for prefix, ws in _WS_HINT_SPECS:
        if prefix in filepath:
            return ws
    return "?"


# ---------------------------------------------------------------------------
# Rule-based classification helpers
# ---------------------------------------------------------------------------


def _is_adapter(filepath: str) -> tuple[bool, str]:
    """Return (True, reason) when the file is a per-dataset adapter instance."""
    for pattern in ADAPTER_DIR_PATTERNS:
        if pattern in filepath:
            return True, f"adapter-dir:{pattern.rstrip('/')}"
    # Per-dataset enrichment runner script
    basename = Path(filepath).name
    if re.match(r"^integrate_.+_enrichments\.py$", basename, re.IGNORECASE):
        return True, "integrate-enrichment-script"
    return False, ""


def _is_operational(filepath: str) -> tuple[bool, str]:
    """Return (True, reason) when the file is clearly operational/tooling scope."""
    # Directory-level rules
    for pattern in OPERATIONAL_DIR_PATTERNS:
        if pattern in filepath:
            return True, f"operational-dir:{pattern.rstrip('/')}"
    # tools/ and config/ default to operational
    if filepath.startswith("tools/") or filepath.startswith("config/"):
        return True, "tools-or-config"
    # Filename-level rules
    basename = Path(filepath).name
    for label, regex in OPERATIONAL_NAME_PATTERNS:
        if regex.search(basename):
            return True, f"name-pattern:{label}"
    return False, ""


# ---------------------------------------------------------------------------
# Signal-based scoring for residual src/ files
# ---------------------------------------------------------------------------


def _score_src_file(import_count: int, loc: int, commit_count: int) -> int:
    """Compute an inventory-membership score for an unclassified src/ module.

    Higher score → more likely to be a core library file that needs an
    inventory entry. The primary signals are import count (how many other
    modules depend on this?) and LOC (how substantial is it?).
    """
    score = 0

    if import_count >= 5:
        score += 40
    elif import_count >= 2:
        score += 25
    elif import_count == 1:
        score += 10
    # import_count == 0: no signal (may be registered dynamically)

    if loc >= 300:
        score += 15
    elif loc >= 100:
        score += 8
    elif loc < 50:
        score -= 5

    if commit_count >= 5:
        score += 10
    elif commit_count == 1:
        score -= 5

    return max(score, 0)


# ---------------------------------------------------------------------------
# Main classification logic
# ---------------------------------------------------------------------------


def classify_file(
    filepath: str,
    import_count: int,
    loc: int,
    commit_count: int,
) -> tuple[str, str, int]:
    """Classify a single GAP_A file.

    Returns (classification, reason, inventory_score).
    Rule-based checks run first; signal-based scoring only for residual src/.
    """
    # --- Rule 1: adapter directories take priority ---
    matched, reason = _is_adapter(filepath)
    if matched:
        return BUCKET_ADAPTER, reason, 0

    # --- Rule 2: obvious operational patterns ---
    matched, reason = _is_operational(filepath)
    if matched:
        return BUCKET_OPERATIONAL, reason, 0

    # --- Rule 3: src/ files — score-based ---
    if filepath.startswith("src/"):
        basename = Path(filepath).name
        # Package __init__.py files: import_count is always 0 because callers
        # import by package path, not by stem. Use LOC + commit_count as proxy.
        if basename == "__init__.py":
            if loc >= 100 or commit_count >= 3:
                return BUCKET_INVENTORY, "pkg-init:LOC≥100-or-commits≥3", loc
            return BUCKET_OPERATIONAL, "pkg-init:small-or-single-commit", 0

        score = _score_src_file(import_count, loc, commit_count)
        if score >= INVENTORY_SCORE_THRESHOLD:
            return BUCKET_INVENTORY, f"score:{score}", score
        if score > 0:
            return BUCKET_TRIAGE, f"score:{score}", score
        # score == 0 with no importers and small LOC: likely implementation detail
        return BUCKET_OPERATIONAL, "src-zero-signal", 0

    # --- Rule 4: modal/ scripts not caught earlier ---
    if filepath.startswith("modal/"):
        # Small support files (shared/__init__.py, test_gcs.py) → operational
        basename = Path(filepath).name
        if basename in {"__init__.py", "app.py"} or "test" in basename:
            return BUCKET_OPERATIONAL, "modal-support-file", 0
        # Remaining modal training scripts: may need inventory entry
        return BUCKET_TRIAGE, "modal-unclassified", 0

    # --- Rule 5: scripts/ default is OPERATIONAL — virtually all scripts are
    # data-ops tooling. The only scripts in the inventory are those already
    # listed there (which would not appear in GAP_A at all).
    if filepath.startswith("scripts/") or filepath.startswith("tools/"):
        return BUCKET_OPERATIONAL, "unclassified-script", 0

    # --- Fallback ---
    return BUCKET_TRIAGE, "unclassified", 0


# ---------------------------------------------------------------------------
# Enrichment orchestration
# ---------------------------------------------------------------------------


def enrich_and_classify(
    gap_a: list[str],
    repo_root: Path,
    git_files: set[str],
    import_index: dict[str, int],
    bulk_stats: BulkFileStats,
) -> list[FileRecord]:
    """Enrich every GAP_A file with signals and apply classification."""
    records: list[FileRecord] = []

    for filepath in sorted(gap_a):
        if Path(filepath).name in SKIP_FILENAMES:
            continue

        last_dt = bulk_stats.last_commit_dates.get(filepath)
        first_dt = bulk_stats.first_commit_dates.get(filepath)
        creation_age = _months_since(first_dt)
        last_touched = _months_since(last_dt)
        commit_count = bulk_stats.commit_counts.get(filepath, 0)
        loc = get_loc(repo_root, filepath)

        # Import count: only meaningful for src/ Python files
        is_src_py = filepath.startswith("src/") and filepath.endswith(".py")
        import_count = get_import_count(filepath, import_index) if is_src_py else -1

        naming_flags, _ = get_naming_flags(filepath)

        classification, reason, score = classify_file(
            filepath, import_count, loc, commit_count
        )

        # For adapter files, check whether the L4 header is present
        if classification == BUCKET_ADAPTER and not _has_l4_header(repo_root, filepath):
            reason += " [MISSING_L4_HEADER]"

        workstream = infer_workstream(filepath) if classification == BUCKET_INVENTORY else "—"

        records.append(
            FileRecord(
                filepath=filepath,
                creation_age_months=creation_age,
                last_touched_months=last_touched,
                commit_count=commit_count,
                loc=loc,
                import_count=import_count,
                naming_flags=naming_flags,
                inventory_score=score,
                classification=classification,
                classification_reason=reason,
                suggested_workstream=workstream,
            )
        )

    return records


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _import_str(count: int) -> str:
    return "n/a" if count < 0 else str(count)


def _age_str(months: float) -> str:
    if months >= 999:
        return "never"
    return f"{months:.0f}mo"


def _inventory_section(records: list[FileRecord]) -> list[str]:
    """Detailed table for NEEDS_INVENTORY, grouped by suggested workstream."""
    lines = ["## NEEDS_INVENTORY\n"]
    lines += [
        "These files are active core modules not yet assigned to a workstream.",
        "**Action**: Add to FILE_INVENTORY, assign workstream, add PUML reference.\n",
    ]
    by_ws: dict[str, list[FileRecord]] = defaultdict(list)
    for r in records:
        if r.classification == BUCKET_INVENTORY:
            by_ws[r.suggested_workstream].append(r)

    for ws in sorted(by_ws):
        lines.append(f"### {ws}\n")
        lines.append("| File | Score | Importers | LOC | Commits | Reason |")
        lines.append("| ---- | ----- | --------- | --- | ------- | ------ |")
        for r in sorted(by_ws[ws], key=lambda x: -x.inventory_score):
            lines.append(
                f"| `{r.filepath}` | {r.inventory_score}"
                f" | {_import_str(r.import_count)}"
                f" | {r.loc}"
                f" | {r.commit_count}"
                f" | {r.classification_reason} |"
            )
        lines.append("")
    return lines


def _adapter_section(records: list[FileRecord]) -> list[str]:
    """Condensed list for DATASET_ADAPTER, grouped by framework directory."""
    lines = ["## DATASET_ADAPTER\n"]
    lines += [
        "These files are per-dataset adapter instances within a documented framework.",
        "**Action**: No change needed — the framework is already in the inventory.\n",
    ]
    by_dir: dict[str, list[FileRecord]] = defaultdict(list)
    for r in records:
        if r.classification == BUCKET_ADAPTER:
            directory = "/".join(r.filepath.split("/")[:-1]) + "/"
            by_dir[directory].append(r)

    for directory in sorted(by_dir):
        items = sorted(by_dir[directory], key=lambda x: x.filepath)
        lines.append(f"**{directory}** ({len(items)} files)")
        for r in items:
            lines.append(f"- `{Path(r.filepath).name}`")
        lines.append("")
    return lines


def _operational_section(records: list[FileRecord]) -> list[str]:
    """Condensed list for OPERATIONAL_SCRIPT, grouped by operation type."""
    lines = ["## OPERATIONAL_SCRIPT\n"]
    lines += [
        "These files are data-ops utilities, audit tools, or one-off scripts",
        "outside the production architecture scope.",
        '**Action**: Document in a "Known Exclusions" section of the inventory.\n',
    ]
    by_reason: dict[str, list[FileRecord]] = defaultdict(list)
    for r in records:
        if r.classification == BUCKET_OPERATIONAL:
            # Shorten reason for grouping
            group = r.classification_reason.split(":")[0]
            by_reason[group].append(r)

    for group in sorted(by_reason):
        items = sorted(by_reason[group], key=lambda x: x.filepath)
        lines.append(f"**{group}** ({len(items)} files)")
        for r in items:
            lines.append(f"- `{r.filepath}`")
        lines.append("")
    return lines


def _triage_section(records: list[FileRecord]) -> list[str]:
    """Detailed table for NEEDS_TRIAGE."""
    lines = ["## NEEDS_TRIAGE\n"]
    lines += [
        "These files require human judgment. Review each one and assign to",
        "NEEDS_INVENTORY, DATASET_ADAPTER, or OPERATIONAL_SCRIPT as appropriate.\n",
    ]
    items = [r for r in records if r.classification == BUCKET_TRIAGE]
    if not items:
        lines += ["*No files require triage.*\n"]
        return lines

    lines.append("| File | Score | Importers | LOC | Commits | Naming | Reason |")
    lines.append("| ---- | ----- | --------- | --- | ------- | ------ | ------ |")
    for r in sorted(items, key=lambda x: x.filepath):
        flags = ",".join(r.naming_flags) if r.naming_flags else "—"
        lines.append(
            f"| `{r.filepath}` | {r.inventory_score}"
            f" | {_import_str(r.import_count)}"
            f" | {r.loc}"
            f" | {r.commit_count}"
            f" | {flags}"
            f" | {r.classification_reason} |"
        )
    lines.append("")
    return lines


def generate_report(
    records: list[FileRecord],
    output_path: Path,
    write: bool = True,
) -> str:
    """Build and optionally write the triage report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    counts: dict[str, int] = Counter(r.classification for r in records)
    total = len(records)

    lines: list[str] = [
        "# GAP_A Triage Report\n",
        f"*Generated: {now}*\n",
        "Files that are git-tracked but absent from FILE_INVENTORY, classified",
        "by whether they need an inventory entry or are intentionally excluded.\n",
        "## Summary\n",
        "| Bucket | Count | % | Action |",
        "| ------ | ----- | - | ------ |",
        f"| NEEDS_INVENTORY   | {counts.get(BUCKET_INVENTORY, 0):4d}"
        f" | {counts.get(BUCKET_INVENTORY, 0)*100//total:3d}%"
        " | Add to inventory + assign workstream |",
        f"| DATASET_ADAPTER   | {counts.get(BUCKET_ADAPTER, 0):4d}"
        f" | {counts.get(BUCKET_ADAPTER, 0)*100//total:3d}%"
        " | No action — framework already documented |",
        f"| OPERATIONAL_SCRIPT| {counts.get(BUCKET_OPERATIONAL, 0):4d}"
        f" | {counts.get(BUCKET_OPERATIONAL, 0)*100//total:3d}%"
        " | Document in Known Exclusions section |",
        f"| NEEDS_TRIAGE      | {counts.get(BUCKET_TRIAGE, 0):4d}"
        f" | {counts.get(BUCKET_TRIAGE, 0)*100//total:3d}%"
        " | Manual review required |",
        f"| **Total**         | {total:4d} |     | |",
        "",
        "### By Directory\n",
        "| Directory | NEEDS_INV | ADAPTER | OPERATIONAL | TRIAGE |",
        "| --------- | --------- | ------- | ----------- | ------ |",
    ]

    dirs = sorted({r.filepath.split("/")[0] for r in records})
    for d in dirs:
        subset = [r for r in records if r.filepath.startswith(f"{d}/")]
        inv = sum(1 for r in subset if r.classification == BUCKET_INVENTORY)
        ada = sum(1 for r in subset if r.classification == BUCKET_ADAPTER)
        ops = sum(1 for r in subset if r.classification == BUCKET_OPERATIONAL)
        tri = sum(1 for r in subset if r.classification == BUCKET_TRIAGE)
        lines.append(f"| `{d}/` | {inv} | {ada} | {ops} | {tri} |")
    lines.append("")

    lines += _inventory_section(records)
    lines += _adapter_section(records)
    lines += _operational_section(records)
    lines += _triage_section(records)

    lines += [
        "## Next Steps\n",
        "1. **NEEDS_INVENTORY**: For each file, open FILE_INVENTORY and add a row",
        "   under the suggested workstream. Then reference it in the appropriate PUML",
        "   diagram.",
        "2. **DATASET_ADAPTER**: No action. Each entry documents an instance of a",
        "   framework that is already inventoried at the framework level.",
        "3. **OPERATIONAL_SCRIPT**: Add a _Known Exclusions_ section to the FILE_INVENTORY",
        '   listing these scripts with a one-line description of "why excluded".',
        "4. **NEEDS_TRIAGE**: Review manually. If import_count > 0, prefer NEEDS_INVENTORY.",
        "   If it fits a clear dataset/tool pattern, assign the matching category.\n",
    ]

    report = "\n".join(lines) + "\n"

    if write:
        output_path.write_text(report, encoding="utf-8")

    return report


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def _apply_scope(files: set[str], scope: str) -> set[str]:
    """Filter GAP_A files to the requested directory scope."""
    if scope == "all":
        return files
    return {f for f in files if f.startswith(f"{scope}/")}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify GAP_A files (git-tracked, not in FILE_INVENTORY).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root directory (default: auto-detected)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Report output path (default: <repo-root>/{DEFAULT_OUTPUT_RELATIVE})",
    )
    parser.add_argument("--no-write", action="store_true", help="Print report to stdout only")
    parser.add_argument(
        "--scope",
        choices=["src", "scripts", "modal", "config", "tools", "all"],
        default="all",
    )
    parser.add_argument(
        "--bucket",
        choices=[BUCKET_INVENTORY, BUCKET_ADAPTER, BUCKET_OPERATIONAL, BUCKET_TRIAGE],
        default=None,
        help="Print files in a specific bucket to stdout",
    )
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    return parser


def main() -> int:  # noqa: PLR0912
    """Entry point."""
    args = _build_parser().parse_args()
    repo_root: Path = args.repo_root.resolve()
    output_path: Path = args.output or repo_root / DEFAULT_OUTPUT_RELATIVE

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
    gap_a = _apply_scope(gaps.new_not_in_inventory, args.scope)

    log(f"GAP_A files to classify: {len(gap_a)}")
    log("Building bulk git stats (single git log pass) …")
    bulk_stats = get_bulk_file_stats(repo_root)

    log("Building import index (scanning all tracked .py files) …")
    import_index = build_import_index(repo_root, git_files)

    log("Classifying files …")
    records = enrich_and_classify(gap_a, repo_root, git_files, import_index, bulk_stats)

    # Console summary
    bucket_counts: dict[str, int] = Counter(r.classification for r in records)
    log(f"\nClassification results ({len(records)} files):")
    log(f"  {BUCKET_INVENTORY:<20}: {bucket_counts.get(BUCKET_INVENTORY, 0)}")
    log(f"  {BUCKET_ADAPTER:<20}: {bucket_counts.get(BUCKET_ADAPTER, 0)}")
    log(f"  {BUCKET_OPERATIONAL:<20}: {bucket_counts.get(BUCKET_OPERATIONAL, 0)}")
    log(f"  {BUCKET_TRIAGE:<20}: {bucket_counts.get(BUCKET_TRIAGE, 0)}")
    log("")

    # Optional bucket detail on console
    if args.bucket:
        items = [r for r in records if r.classification == args.bucket]
        if args.bucket in (BUCKET_INVENTORY, BUCKET_TRIAGE):
            items.sort(key=lambda r: (-r.inventory_score, r.filepath))
        else:
            items.sort(key=lambda r: r.filepath)
        for r in items:
            if r.inventory_score < args.min_score:
                continue
            log(
                f"  [{r.inventory_score:3d}] {r.filepath}"
                f"  ws={r.suggested_workstream}"
                f" | {r.commit_count}c | {r.loc}L"
                f" | importers={_import_str(r.import_count)}"
                + (f" | {','.join(r.naming_flags)}" if r.naming_flags else "")
                + f" | {r.classification_reason}"
            )
        log("")

    # JSON output
    if args.json:
        data = {
            "generated": datetime.now().isoformat(),
            "totals": dict(bucket_counts),
            "files": [r.as_dict() for r in sorted(records, key=lambda r: r.filepath)],
        }
        print(json.dumps(data, indent=2))

    # Write report
    report = generate_report(records, output_path, write=not args.no_write)
    if not args.no_write:
        log(f"Report written to: {output_path}")
    elif not args.json:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
