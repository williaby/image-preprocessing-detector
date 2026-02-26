#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Level 4 Architecture Documentation Registry Generator.

Harvests ``__l4_*`` module-level metadata variables from Python adapter files
and ``l4_*`` YAML front-matter from Markdown training dataset docs, then
generates Level 4 registry Markdown tables.

Level 4 documents instance registries for the 135 DATASET_ADAPTER files that
are intentionally excluded from PUML diagrams: annotation parsers, enrichment
providers, and integrate scripts.  See:
    docs/handoff/LEVEL4_ARCHITECTURE_DESIGN_HANDOFF.md

Usage::

    # Generate all registries
    python scripts/generate_level4_registries.py

    # CI validation gate (orphan detection + header validation + path checks)
    python scripts/generate_level4_registries.py --check

    # Generate a single category
    python scripts/generate_level4_registries.py --category parser

    # Emit raw harvest as JSON (debugging)
    python scripts/generate_level4_registries.py --json

    # Generate new adapter stub with pre-filled headers
    python scripts/generate_level4_registries.py --scaffold --category parser \\
        --dataset doclaynet --task layout --workstream WS3

    # Verbose mode (log skipped files with reasons)
    python scripts/generate_level4_registries.py --check --verbose
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent

_CANONICAL_NAMES_FILE = _REPO_ROOT / "docs" / "datasets" / "canonical_names.json"
_LEVEL4_OUTPUT_DIR = (
    _REPO_ROOT / "docs" / "architecture" / "diagrams" / "level-4"
)
_DATASETS_SOURCE_DIR = _REPO_ROOT / "docs" / "datasets" / "source"
_TRAINING_DOCS_DIR = _REPO_ROOT / "docs" / "datasets" / "training"

# ---------------------------------------------------------------------------
# Adapter directory patterns
# These mirror ADAPTER_DIR_PATTERNS in triage_gap_a.py — keep in sync.
# Paths are relative to repo root.
# ---------------------------------------------------------------------------

_ADAPTER_DIRS: tuple[str, ...] = (
    "src/image_preprocessing_detector/annotation/parsers/correction",
    "src/image_preprocessing_detector/annotation/parsers/document",
    "src/image_preprocessing_detector/annotation/parsers/formula",
    "src/image_preprocessing_detector/annotation/parsers/handwriting",
    "src/image_preprocessing_detector/annotation/parsers/layout",
    "src/image_preprocessing_detector/annotation/parsers/multilingual",
    "src/image_preprocessing_detector/annotation/parsers/quality",
    "src/image_preprocessing_detector/annotation/enrichment/providers",
)

# integrate_*_enrichments.py scripts are handled separately as a name-pattern
_INTEGRATE_PATTERN = re.compile(r"^integrate_.+_enrichments\.py$")

# Files excluded from required-header checks (framework / package declarations)
_SKIP_FILENAMES: frozenset[str] = frozenset(
    {"__init__.py", "base.py", "registry.py", "template.py", "generic.py"}
)

# Controlled vocabulary for __l4_task__
_VALID_TASKS: frozenset[str] = frozenset(
    {
        "correction",
        "document",
        "formula",
        "handwriting",
        "layout",
        "multilingual",
        "quality",
        "language",
        "iqa",
    }
)

# Valid categories
_VALID_CATEGORIES: frozenset[str] = frozenset(
    {"parser", "provider", "integrate-script", "training-dataset"}
)

# Valid statuses
_VALID_STATUSES: frozenset[str] = frozenset({"active", "deprecated"})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_git_tracked_files(repo_root: Path) -> set[Path]:
    """Return set of paths (relative to repo_root) that are git-tracked."""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    return {repo_root / p for p in result.stdout.splitlines() if p}


def _load_canonical_names(repo_root: Path) -> set[str]:
    """Load canonical dataset names from canonical_names.json."""
    path = repo_root / "docs" / "datasets" / "canonical_names.json"
    if not path.exists():
        return set()
    with path.open() as f:
        data = json.load(f)
    return set(data.get("canonical_names", []))


def _normalize_dataset_name(name: str) -> str:
    """Normalize a dataset name to kebab-case for canonical comparison."""
    return name.lower().replace("_", "-")


def _extract_l4_metadata_from_py(path: Path) -> dict[str, Any] | None:
    """
    Extract ``__l4_*`` module-level variable assignments from a Python file
    using AST parsing.  Returns None if no ``__l4_category__`` is found.

    Only simple string-literal assignments are supported (which is the
    intended convention).  Dynamic assignments are not an anti-pattern in
    adapter code per the handoff spec.
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, OSError):
        return None

    metadata: dict[str, Any] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if not (name.startswith("__l4_") and name.endswith("__")):
                continue
            # Extract string literal value only
            if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            ):
                # Strip the __l4_ prefix and trailing __
                key = name[5:-2]  # "__l4_category__" → "category"
                metadata[key] = node.value.value

    if "category" not in metadata:
        return None
    return metadata


def _extract_l4_metadata_from_md(path: Path) -> dict[str, Any] | None:
    """
    Extract ``l4_*`` keys from YAML front-matter in a Markdown file.
    Returns None if no ``l4_category`` key is found in front matter.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not text.startswith("---"):
        return None

    end = text.find("\n---", 3)
    if end == -1:
        return None

    front_matter = text[3:end].strip()
    metadata: dict[str, Any] = {}
    for line in front_matter.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key.startswith("l4_"):
            raw_value = value.strip()
            # Parse simple YAML lists
            if raw_value.startswith("[") and raw_value.endswith("]"):
                items = [
                    i.strip().strip("\"'")
                    for i in raw_value[1:-1].split(",")
                    if i.strip()
                ]
                metadata[key[3:]] = items  # strip "l4_" prefix
            else:
                metadata[key[3:]] = raw_value.strip("\"'")

    # Also parse multi-line YAML list values (indented items with "- ")
    in_list_key: str | None = None
    list_values: list[str] = []
    for line in front_matter.splitlines():
        stripped = line.strip()
        if stripped.startswith("l4_") and stripped.endswith(":"):
            if in_list_key and list_values:
                metadata[in_list_key] = list_values
            in_list_key = stripped[3:-1]
            list_values = []
        elif in_list_key and stripped.startswith("- "):
            list_values.append(stripped[2:].strip())
        elif in_list_key and stripped and not stripped.startswith("#"):
            if list_values:
                metadata[in_list_key] = list_values
            in_list_key = None
            list_values = []
    if in_list_key and list_values:
        metadata[in_list_key] = list_values

    if "category" not in metadata:
        return None
    return metadata


# ---------------------------------------------------------------------------
# Harvest
# ---------------------------------------------------------------------------


def harvest_all(
    repo_root: Path,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Harvest all __l4_* metadata from adapter .py files and l4_* front-matter
    from Markdown training dataset docs.

    Returns:
        (py_records, md_records) — separate lists by source file type.
        Each record is the metadata dict augmented with ``_path`` (str relative
        to repo_root) and ``_source_type`` ("python" or "markdown").
    """
    py_records: list[dict[str, Any]] = []
    md_records: list[dict[str, Any]] = []

    # Python adapter files
    for dir_rel in _ADAPTER_DIRS:
        adapter_dir = repo_root / dir_rel
        if not adapter_dir.is_dir():
            if verbose:
                print(f"  [SKIP] directory not found: {dir_rel}", file=sys.stderr)
            continue
        for py_file in sorted(adapter_dir.glob("*.py")):
            if py_file.name in _SKIP_FILENAMES:
                if verbose:
                    print(
                        f"  [SKIP] framework file: {py_file.relative_to(repo_root)}",
                        file=sys.stderr,
                    )
                continue
            metadata = _extract_l4_metadata_from_py(py_file)
            if metadata is None:
                if verbose:
                    print(
                        f"  [SKIP] no __l4_category__: {py_file.relative_to(repo_root)}",
                        file=sys.stderr,
                    )
                continue
            metadata["_path"] = str(py_file.relative_to(repo_root))
            metadata["_source_type"] = "python"
            py_records.append(metadata)

    # Integrate scripts
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        for py_file in sorted(scripts_dir.glob("*.py")):
            if not _INTEGRATE_PATTERN.match(py_file.name):
                continue
            metadata = _extract_l4_metadata_from_py(py_file)
            if metadata is None:
                if verbose:
                    print(
                        f"  [SKIP] no __l4_category__: {py_file.relative_to(repo_root)}",
                        file=sys.stderr,
                    )
                continue
            metadata["_path"] = str(py_file.relative_to(repo_root))
            metadata["_source_type"] = "python"
            py_records.append(metadata)

    # Markdown training dataset docs
    if _TRAINING_DOCS_DIR.is_dir():
        for md_file in sorted(_TRAINING_DOCS_DIR.glob("*.md")):
            metadata = _extract_l4_metadata_from_md(md_file)
            if metadata is None:
                if verbose:
                    print(
                        f"  [SKIP] no l4_category front matter: {md_file.relative_to(repo_root)}",
                        file=sys.stderr,
                    )
                continue
            metadata["_path"] = str(md_file.relative_to(repo_root))
            metadata["_source_type"] = "markdown"
            md_records.append(metadata)

    return py_records, md_records


# ---------------------------------------------------------------------------
# Validation (--check mode)
# ---------------------------------------------------------------------------


class ValidationError:
    """Single validation finding."""

    def __init__(self, path: str, severity: str, message: str) -> None:
        self.path = path
        self.severity = severity  # "ERROR" | "WARN"
        self.message = message

    def __str__(self) -> str:
        return f"  [{self.severity}] {self.path}: {self.message}"


def validate_headers(
    repo_root: Path,
    verbose: bool = False,
) -> list[ValidationError]:
    """
    Validate Level 4 header coverage across all adapter files.

    Performs four consensus-required checks:
      A. Orphan detection: walk adapter directories explicitly for un-headered files
      B. Required-field presence: __l4_category__, __l4_dataset__, __l4_workstream__
      C. Canonical name validation: __l4_dataset__ against canonical_names.json
      D. Cross-reference path existence: __l4_integrate__, __l4_parser__ must exist

    Returns:
        List of ValidationError objects.  Empty list means CI gate passes.
    """
    canonical_names = _load_canonical_names(repo_root)
    errors: list[ValidationError] = []

    def _check_file(py_file: Path) -> None:
        rel = str(py_file.relative_to(repo_root))

        if py_file.name in _SKIP_FILENAMES:
            return

        metadata = _extract_l4_metadata_from_py(py_file)

        # [A] Orphan detection
        if metadata is None:
            errors.append(
                ValidationError(rel, "ERROR", "missing __l4_category__ (GAP_E: no Level 4 header)")
            )
            return

        # [B] Required field presence
        # __l4_dataset__ is NOT required for providers (they are not dataset-specific)
        category = metadata.get("category", "")
        required_fields = ["category", "workstream"]
        if category != "provider":
            required_fields.append("dataset")
        for required_field in required_fields:
            if required_field not in metadata:
                errors.append(
                    ValidationError(
                        rel,
                        "ERROR",
                        f"missing required __l4_{required_field}__",
                    )
                )

        # Category value check
        if category and category not in _VALID_CATEGORIES:
            errors.append(
                ValidationError(
                    rel,
                    "ERROR",
                    f"__l4_category__={category!r} not in {sorted(_VALID_CATEGORIES)}",
                )
            )

        # [C] Canonical name validation
        dataset = metadata.get("dataset", "")
        if dataset and canonical_names:
            normalized = _normalize_dataset_name(dataset)
            normalized_canonical = {_normalize_dataset_name(n) for n in canonical_names}
            if normalized not in normalized_canonical:
                errors.append(
                    ValidationError(
                        rel,
                        "ERROR",
                        f"__l4_dataset__={dataset!r} not found in canonical_names.json "
                        f"(normalized: {normalized!r})",
                    )
                )

        # __l4_task__ controlled vocabulary (warning only — not all adapters have task)
        task = metadata.get("task", "")
        if task and task not in _VALID_TASKS:
            errors.append(
                ValidationError(
                    rel,
                    "WARN",
                    f"__l4_task__={task!r} not in controlled vocabulary {sorted(_VALID_TASKS)}",
                )
            )

        # [D] Cross-reference path existence
        for path_field in ("integrate", "parser"):
            ref_path_str = metadata.get(path_field, "")
            if ref_path_str:
                ref_path = repo_root / ref_path_str
                if not ref_path.exists():
                    severity = "ERROR" if path_field == "parser" else "WARN"
                    errors.append(
                        ValidationError(
                            rel,
                            severity,
                            f"__l4_{path_field}__={ref_path_str!r} does not exist on disk",
                        )
                    )

        # l2_file: warn only (metadata files may be on network storage)
        l2_file = metadata.get("l2_file", "")
        if l2_file and verbose:
            # Only report in verbose mode — L2 files may not be locally present
            metadata_dir = repo_root / "metadata_registry" / "json"
            candidate = metadata_dir / l2_file
            if not candidate.exists():
                print(
                    f"  [NOTE] {rel}: __l4_l2_file__={l2_file!r} not found locally (may be on E:\\\\)",
                    file=sys.stderr,
                )

        # Status field
        status = metadata.get("status", "")
        if status and status not in _VALID_STATUSES:
            errors.append(
                ValidationError(
                    rel,
                    "WARN",
                    f"__l4_status__={status!r} not in {sorted(_VALID_STATUSES)}",
                )
            )

    # [A] Walk adapter directories explicitly (not just files with headers)
    for dir_rel in _ADAPTER_DIRS:
        adapter_dir = repo_root / dir_rel
        if not adapter_dir.is_dir():
            continue
        for py_file in sorted(adapter_dir.glob("*.py")):
            _check_file(py_file)

    # Integrate scripts
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        for py_file in sorted(scripts_dir.glob("*.py")):
            if _INTEGRATE_PATTERN.match(py_file.name):
                _check_file(py_file)

    return errors


# ---------------------------------------------------------------------------
# Registry generators
# ---------------------------------------------------------------------------


def _dataset_link(dataset_name: str) -> str:
    """
    Return a Markdown link to docs/datasets/source/{name}.md if the file
    exists, otherwise return the plain dataset name.
    Normalizes the name (kebab → underscores) when looking for the file.
    """
    # Try both kebab and underscore forms
    for candidate in (dataset_name, dataset_name.replace("-", "_")):
        source_file = _DATASETS_SOURCE_DIR / f"{candidate}.md"
        if source_file.exists():
            rel = f"../../../datasets/source/{candidate}.md"
            return f"[{dataset_name}]({rel})"
    return f"`{dataset_name}`"


def _generate_parser_registry(
    records: list[dict[str, Any]],
    output_path: Path,
    repo_root: Path,
) -> int:
    """
    Generate annotation-parser-registry.md, grouped by __l4_task__.

    Returns:
        Number of rows written.
    """
    parser_records = [r for r in records if r.get("category") == "parser"]

    # Group by task
    by_task: dict[str, list[dict[str, Any]]] = {}
    for rec in sorted(parser_records, key=lambda r: (r.get("task", ""), r.get("dataset", ""))):
        task = rec.get("task", "unknown")
        by_task.setdefault(task, []).append(rec)

    lines: list[str] = [
        "---",
        "owner: docs-team",
        "title: 'Level 4: Annotation Parser Registry'",
        "l4_category: parser",
        "l4_generated: auto",
        "l4_generator: scripts/generate_level4_registries.py",
        f"l4_last_generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "tags:",
        "- architecture",
        "- level-4",
        "- registry",
        "---",
        "",
        "# Level 4: Annotation Parser Registry",
        "",
        "> **Auto-generated** — do not edit manually. Regenerate with:",
        "> `python scripts/generate_level4_registries.py --category parser`",
        "",
        f"Total: {len(parser_records)} dataset parsers across {len(by_task)} task categories.",
        "",
    ]

    total_rows = 0
    task_order = [
        "layout", "quality", "correction", "handwriting", "multilingual", "document", "formula",
    ]
    ordered_tasks = task_order + [t for t in sorted(by_task) if t not in task_order]

    for task in ordered_tasks:
        if task not in by_task:
            continue
        task_records = by_task[task]
        lines.append(f"## {task.capitalize()} Parsers ({len(task_records)} datasets)")
        lines.append("")
        lines.append("| Dataset | Parser File | Integrate Script | L2 Metadata File | Status |")
        lines.append("| ------- | ----------- | ---------------- | ---------------- | ------ |")
        for rec in task_records:
            dataset = rec.get("dataset", "—")
            path = rec.get("_path", "—")
            integrate = rec.get("integrate", "—")
            l2_file = rec.get("l2_file", "—")
            status = rec.get("status", "active")
            status_icon = "✅" if status == "active" else "⛔"

            integrate_cell = f"`{integrate}`" if integrate and integrate != "—" else "—"
            l2_cell = f"`{l2_file}`" if l2_file and l2_file != "—" else "—"

            lines.append(
                f"| {_dataset_link(dataset)} | `{path}` "
                f"| {integrate_cell} | {l2_cell} | {status_icon} |"
            )
            total_rows += 1
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total_rows


def _generate_provider_registry(
    records: list[dict[str, Any]],
    output_path: Path,
    repo_root: Path,
) -> int:
    """Generate annotation-provider-registry.md."""
    provider_records = sorted(
        [r for r in records if r.get("category") == "provider"],
        key=lambda r: r.get("task", "") + r.get("_path", ""),
    )

    lines: list[str] = [
        "---",
        "owner: docs-team",
        "title: 'Level 4: Annotation Enrichment Provider Registry'",
        "l4_category: provider",
        "l4_generated: auto",
        "l4_generator: scripts/generate_level4_registries.py",
        f"l4_last_generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "tags:",
        "- architecture",
        "- level-4",
        "- registry",
        "---",
        "",
        "# Level 4: Annotation Enrichment Provider Registry",
        "",
        "> **Auto-generated** — do not edit manually. Regenerate with:",
        "> `python scripts/generate_level4_registries.py --category provider`",
        "",
        f"Total: {len(provider_records)} enrichment providers.",
        "",
        "| Provider File | Task | Workstream | Provides | Status |",
        "| ------------- | ---- | ---------- | -------- | ------ |",
    ]

    for rec in provider_records:
        path = rec.get("_path", "—")
        task = rec.get("task", "—")
        workstream = rec.get("workstream", "—")
        provides = rec.get("provides", "—")
        status = rec.get("status", "active")
        status_icon = "✅" if status == "active" else "⛔"
        lines.append(
            f"| `{path}` | {task} | {workstream} | `{provides}` | {status_icon} |"
        )

    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(provider_records)


def _generate_integrate_registry(
    records: list[dict[str, Any]],
    output_path: Path,
    repo_root: Path,
) -> int:
    """Generate annotation-integrate-registry.md."""
    integrate_records = sorted(
        [r for r in records if r.get("category") == "integrate-script"],
        key=lambda r: r.get("dataset", ""),
    )

    lines: list[str] = [
        "---",
        "owner: docs-team",
        "title: 'Level 4: Annotation Integrate Script Registry'",
        "l4_category: integrate-script",
        "l4_generated: auto",
        "l4_generator: scripts/generate_level4_registries.py",
        f"l4_last_generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "tags:",
        "- architecture",
        "- level-4",
        "- registry",
        "---",
        "",
        "# Level 4: Annotation Integrate Script Registry",
        "",
        "> **Auto-generated** — do not edit manually. Regenerate with:",
        "> `python scripts/generate_level4_registries.py --category integrate-script`",
        "",
        f"Total: {len(integrate_records)} integrate scripts.",
        "",
        "| Dataset | Script | Workstream | Paired Parser | Status |",
        "| ------- | ------ | ---------- | ------------- | ------ |",
    ]

    for rec in integrate_records:
        dataset = rec.get("dataset", "—")
        path = rec.get("_path", "—")
        workstream = rec.get("workstream", "—")
        parser_path = rec.get("parser", "—")
        status = rec.get("status", "active")
        status_icon = "✅" if status == "active" else "⛔"
        parser_cell = f"`{parser_path}`" if parser_path and parser_path != "—" else "—"
        lines.append(
            f"| {_dataset_link(dataset)} | `{path}` "
            f"| {workstream} | {parser_cell} | {status_icon} |"
        )

    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(integrate_records)


def _generate_training_dataset_registry(
    records: list[dict[str, Any]],
    output_path: Path,
    repo_root: Path,
) -> int:
    """Generate training-dataset-registry.md (SEMI — uses fence markers)."""
    td_records = sorted(
        [r for r in records if r.get("category") == "training-dataset"],
        key=lambda r: r.get("dataset", ""),
    )

    auto_block_lines: list[str] = [
        f"Total: {len(td_records)} training datasets.",
        "",
        "| Training Dataset | Images | Workstream | Sources | Generation Script | GCS Path | Status |",
        "| ---------------- | ------ | ---------- | ------- | ----------------- | -------- | ------ |",
    ]

    for rec in td_records:
        dataset = rec.get("dataset", "—")
        images = rec.get("image_count", "—")
        workstream = rec.get("workstream", "—")
        sources = rec.get("source_datasets", [])
        sources_cell = ", ".join(sources[:3])
        if len(sources) > 3:
            sources_cell += f" +{len(sources) - 3} more"
        gen_script = rec.get("generation_script", "—")
        gcs_path = rec.get("gcs_path", "—")
        status = rec.get("status", "active")
        status_icon = "✅" if status == "active" else "⛔"

        gen_cell = f"`{gen_script}`" if gen_script and gen_script != "—" else "—"
        auto_block_lines.append(
            f"| `{dataset}` | {images} | {workstream} | {sources_cell} "
            f"| {gen_cell} | `{gcs_path}` | {status_icon} |"
        )

    auto_block_lines.append("")

    # Read existing file if present (preserve manual sections outside fence)
    generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fence_start = "<!-- AUTO-GENERATED-START -->"
    fence_end = "<!-- AUTO-GENERATED-END -->"

    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        if fence_start in existing and fence_end in existing:
            before = existing[: existing.index(fence_start)]
            after = existing[existing.index(fence_end) + len(fence_end):]
            new_content = (
                before
                + fence_start
                + "\n"
                + f"<!-- Last generated: {generated_date} -->\n"
                + "\n".join(auto_block_lines)
                + fence_end
                + after
            )
            output_path.write_text(new_content, encoding="utf-8")
            return len(td_records)

    # First-time generation: write full file with fence markers
    header_lines = [
        "---",
        "owner: docs-team",
        "title: 'Level 4: Training Dataset Registry'",
        "l4_category: training-dataset",
        "l4_generated: semi",
        "l4_generator: scripts/generate_level4_registries.py",
        f"l4_last_generated: {generated_date}",
        "tags:",
        "- architecture",
        "- level-4",
        "- registry",
        "---",
        "",
        "# Level 4: Training Dataset Registry",
        "",
        "> **Semi-automated** — table auto-generated from `l4_*` front-matter in",
        "> `docs/datasets/training/*.md`.  Narrative sections below are manually maintained.",
        "",
        fence_start,
        f"<!-- Last generated: {generated_date} -->",
    ]
    footer_lines = [
        fence_end,
        "",
        "## Notes",
        "",
        "<!-- Add manually maintained notes here. This section is preserved on regeneration. -->",
        "",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(header_lines + auto_block_lines + footer_lines) + "\n",
        encoding="utf-8",
    )
    return len(td_records)


# ---------------------------------------------------------------------------
# Scaffold
# ---------------------------------------------------------------------------


_SCAFFOLD_TEMPLATES: dict[str, str] = {
    "parser": textwrap.dedent(
        '''\
        # SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
        # SPDX-License-Identifier: MIT
        """Parser for {dataset} annotation dataset.

        TODO: Add dataset description here.
        """

        # --- Level 4 registry metadata ---
        __l4_category__    = "parser"
        __l4_dataset__     = "{dataset}"
        __l4_workstream__  = "{workstream}"
        __l4_task__        = "{task}"
        __l4_l2_file__     = "{dataset}_metadata.json"
        __l4_integrate__   = "scripts/integrate_{dataset_us}_enrichments.py"
        __l4_status__      = "active"

        from __future__ import annotations

        # TODO: Add imports and implementation here.
        '''
    ),
    "provider": textwrap.dedent(
        '''\
        # SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
        # SPDX-License-Identifier: MIT
        """{dataset} enrichment provider.

        TODO: Add provider description here.
        """

        # --- Level 4 registry metadata ---
        __l4_category__    = "provider"
        __l4_task__        = "{task}"
        __l4_workstream__  = "{workstream}"
        __l4_provides__    = "TODO_field_name"
        __l4_status__      = "active"

        from __future__ import annotations

        # TODO: Add imports and implementation here.
        '''
    ),
    "integrate-script": textwrap.dedent(
        '''\
        #!/usr/bin/env python3
        # SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
        # SPDX-License-Identifier: MIT
        """Integrate {dataset} enrichment metadata into L2 registry.

        TODO: Add script description here.
        """

        # --- Level 4 registry metadata ---
        __l4_category__    = "integrate-script"
        __l4_dataset__     = "{dataset}"
        __l4_workstream__  = "{workstream}"
        __l4_parser__      = "src/image_preprocessing_detector/annotation/parsers/{task}/{dataset_us}.py"
        __l4_status__      = "active"

        from __future__ import annotations

        # TODO: Add imports and implementation here.
        '''
    ),
}


def scaffold_adapter(
    category: str,
    dataset: str,
    task: str,
    workstream: str,
) -> str:
    """Return a stub Python file string with pre-filled __l4_* headers."""
    template = _SCAFFOLD_TEMPLATES.get(category)
    if template is None:
        raise ValueError(f"No scaffold template for category {category!r}")
    dataset_us = dataset.replace("-", "_")
    return template.format(
        dataset=dataset,
        dataset_us=dataset_us,
        task=task,
        workstream=workstream,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Level 4 architecture documentation registry generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_LEVEL4_OUTPUT_DIR,
        help="Level 4 output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--category",
        choices=["parser", "provider", "integrate-script", "training-dataset", "all"],
        default="all",
        help="Category to generate (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate headers only, with orphan detection (CI mode). Exit 1 on errors.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit raw harvest as JSON to stdout",
    )
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Emit new adapter stub to stdout (requires --dataset, --task, --workstream)",
    )
    parser.add_argument("--dataset", help="Dataset name for --scaffold mode")
    parser.add_argument("--task", help="Task name for --scaffold mode")
    parser.add_argument("--workstream", default="WS3", help="Workstream for --scaffold mode")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log skipped files with reasons",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root

    # --scaffold mode
    if args.scaffold:
        if not args.dataset or not args.task:
            print("ERROR: --scaffold requires --dataset and --task", file=sys.stderr)
            return 1
        if args.category == "all":
            print("ERROR: --scaffold requires --category (not 'all')", file=sys.stderr)
            return 1
        print(scaffold_adapter(args.category, args.dataset, args.task, args.workstream))
        return 0

    # --check mode: validate headers and exit
    if args.check:
        print("Validating Level 4 headers...", file=sys.stderr)
        errors = validate_headers(repo_root, verbose=args.verbose)
        error_count = sum(1 for e in errors if e.severity == "ERROR")
        warn_count = sum(1 for e in errors if e.severity == "WARN")

        if errors:
            for err in sorted(errors, key=lambda e: (e.severity, e.path)):
                print(str(err), file=sys.stderr)
            print(
                f"\nResult: {error_count} error(s), {warn_count} warning(s)",
                file=sys.stderr,
            )
        else:
            print("  ✓ All Level 4 headers valid — 0 errors, 0 warnings", file=sys.stderr)

        return 1 if error_count > 0 else 0

    # Harvest
    py_records, md_records = harvest_all(repo_root, verbose=args.verbose)
    all_records = py_records + md_records

    # --json mode
    if args.emit_json:
        json.dump(all_records, sys.stdout, indent=2)
        print()
        return 0

    # Generate registries
    output_dir: Path = args.output_dir
    generated: list[str] = []

    data_prep_dir = output_dir / "data-preparation"
    model_training_dir = output_dir / "model-training"

    cat = args.category

    if cat in ("parser", "all"):
        out = data_prep_dir / "annotation-parser-registry.md"
        rows = _generate_parser_registry(all_records, out, repo_root)
        generated.append(f"  {out.relative_to(repo_root)}: {rows} rows")

    if cat in ("provider", "all"):
        out = data_prep_dir / "annotation-provider-registry.md"
        rows = _generate_provider_registry(all_records, out, repo_root)
        generated.append(f"  {out.relative_to(repo_root)}: {rows} rows")

    if cat in ("integrate-script", "all"):
        out = data_prep_dir / "annotation-integrate-registry.md"
        rows = _generate_integrate_registry(all_records, out, repo_root)
        generated.append(f"  {out.relative_to(repo_root)}: {rows} rows")

    if cat in ("training-dataset", "all"):
        out = model_training_dir / "training-dataset-registry.md"
        rows = _generate_training_dataset_registry(all_records, out, repo_root)
        generated.append(f"  {out.relative_to(repo_root)}: {rows} rows")

    if generated:
        print("Generated Level 4 registries:", file=sys.stderr)
        for line in generated:
            print(line, file=sys.stderr)
    else:
        print("No registries generated for category:", args.category, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
