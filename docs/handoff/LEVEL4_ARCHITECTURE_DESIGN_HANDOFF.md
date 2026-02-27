---
owner: docs-team
purpose: Handoff for Level 4 architecture documentation system design and implementation.
schema_type: common
status: draft
tags:
- architecture
- documentation
title: 'Handoff: Level 4 Architecture Documentation System'
---

> **Date**: 2026-02-23
> **Author**: Byron (via Claude Code)
> **Branch**: `docs/har-systematic-head-review`
> **Scope**: Level 4 architecture documentation — design specification and implementation guide

---

## 1. Why This Exists

The project has a well-maintained 4-level architecture documentation hierarchy (Level 0–3)
covering system context, workstream architecture, component workflows, and module
implementation. However, a structural gap was identified during a file coverage audit:

**The registry/catalog problem**: The annotation framework (`annotation/parsers/`,
`annotation/enrichment/providers/`) contains 81 adapter files — one per source dataset.
These follow a clean hub-and-spoke pattern: a documented framework with per-dataset
instances. The framework is in the Level 2/3 diagrams; the 81 instances are not.

Adding 81 rows to existing PUML diagrams would destroy readability. But leaving them
entirely undocumented creates a dead zone in the inventory.

The same gap exists for:

- Training dataset → source datasets mapping (10 training datasets, 51 sources)
- Training dataset → generation scripts (which script produced which dataset)
- Model checkpoints → training runs, metrics, deployment status

**Level 4 fills this gap**: a dedicated tier for instance registries and dataset catalogs —
more table than workflow, sitting alongside the diagram tree.

---

## 2. The Current State (What Already Exists)

### 2.1 Audit Infrastructure (Already Built)

Three scripts in `scripts/` provide the foundation:

| Script | Purpose | Output |
|--------|---------|--------|
| `scripts/audit_diagram_file_coverage.py` | Identifies four gap categories (A–D) between git-tracked files, FILE_INVENTORY, and PUML diagrams | `docs/architecture/DIAGRAM_COVERAGE_AUDIT.md` |
| `scripts/triage_gap_c.py` | Enriches GAP_C files (no PUML reference) with staleness signals | `docs/architecture/GAP_C_TRIAGE_REPORT.md` |
| `scripts/triage_gap_a.py` | Classifies GAP_A files (not in inventory) into NEEDS_INVENTORY / DATASET_ADAPTER / OPERATIONAL_SCRIPT / NEEDS_TRIAGE | `docs/architecture/GAP_A_TRIAGE_REPORT.md` |

The triage reports establish **which files are DATASET_ADAPTER** (the 135 files that Level 4
will document) versus **which files are NEEDS_INVENTORY** (the 40 files that need Level 2/3
coverage).

### 2.2 Annotation Parser Structure

```text
src/image_preprocessing_detector/annotation/
├── parsers/
│   ├── base.py                    ← Framework (in Level 2/3)
│   ├── registry.py                ← Framework (in Level 2/3)
│   ├── correction/                ← 6 dataset parsers
│   ├── document/                  ← ~15 dataset parsers
│   ├── formula/                   ← ~3 dataset parsers
│   ├── handwriting/               ← ~8 dataset parsers
│   ├── layout/                    ← 11 dataset parsers (doclaynet.py, funsd.py, …)
│   ├── multilingual/              ← ~6 dataset parsers
│   ├── quality/                   ← ~12 dataset parsers
│   └── generic.py
├── enrichment/
│   └── providers/
│       ├── base.py                ← Framework
│       ├── docling_layout.py      ← Provider instance
│       ├── language_detector.py   ← Provider instance
│       ├── siglip.py              ← Provider instance
│       ├── simulated.py           ← Provider instance
│       └── yolo.py                ← Provider instance
```

### 2.3 Existing File Header Convention

Parser files already follow a consistent module docstring pattern:

```python
"""Parser for DocLayNet layout annotation dataset.

DocLayNet provides COCO-format annotations for document layout analysis
...
"""
```

The `__l4_*` metadata variables proposed below extend this — they go immediately
after the module docstring, before imports.

### 2.4 Existing Documentation Conventions

The existing levels follow YAML front matter + markdown format. See:

- `docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md` — full maintenance guide
- `docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md` — style reference
- `docs/handoff/SYNTH_MULTITASK_DIVERSITY_HANDOFF.md` — handoff document style reference

---

## 3. Design Decisions Already Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Location | `docs/architecture/diagrams/level-4/` | Alongside existing diagram tree |
| Format | Markdown tables (primary), PUML class diagrams (optional for framework overview) | "More table than workflow" |
| Linkage mechanism | `__l4_*` module-level variables in Python source files; YAML front matter in `.md` files | Grep-able, no runtime impact, aligns with existing SPDX header pattern |
| Coverage model | Automated harvest for known-pattern categories (parsers, providers, integrate scripts); manual for others | Parsers are structurally uniform; model checkpoints require human judgment |
| Level 3 relationship | Level 3 diagrams describe the framework/workflow; Level 4 documents the instances | Clean separation of "how it works" vs "what exists" |
| Audit integration | `triage_gap_a.py` DATASET_ADAPTER bucket identifies which files need `__l4_*` headers | The 135 DATASET_ADAPTER files are the Level 4 subject matter |

---

## 4. The `__l4_*` Header Convention

### 4.1 Python source files

Add these module-level variables immediately after the module docstring, before imports:

```python
"""Parser for DocLayNet layout annotation dataset. …"""

# --- Level 4 registry metadata ---
__l4_category__    = "parser"          # REQUIRED: parser | provider | integrate-script
__l4_dataset__     = "doclaynet"       # REQUIRED: canonical dataset name (from DATASET_NAMING_STANDARD.md)
__l4_workstream__  = "WS3"             # REQUIRED: workstream assignment
__l4_task__        = "layout"          # OPTIONAL: layout | quality | correction | handwriting | etc.
__l4_l2_file__     = "doclaynet_metadata.json"   # OPTIONAL: L2 metadata filename
__l4_integrate__   = "scripts/integrate_doclaynet_enrichments.py"  # OPTIONAL: paired integrate script

import ...
```

For `annotation/enrichment/providers/`:

```python
"""Docling layout enrichment provider. …"""

__l4_category__    = "provider"
__l4_task__        = "layout"
__l4_workstream__  = "WS3"
__l4_provides__    = "layout_boxes"    # what enrichment field this provider populates
```

### 4.2 Script files (`scripts/integrate_*.py`)

```python
"""Integrate doclaynet enrichment metadata into L2 registry. …"""

__l4_category__    = "integrate-script"
__l4_dataset__     = "doclaynet"
__l4_workstream__  = "WS3"
__l4_parser__      = "src/…/annotation/parsers/layout/doclaynet.py"
```

### 4.3 Markdown / YAML files (training datasets, configs)

YAML front matter — extend the existing front matter block:

```yaml
---
owner: docs-team
title: Skew Training Dataset
l4_category: training-dataset
l4_dataset: skew
l4_workstream: WS2
l4_source_datasets:
  - doclaynet
  - rvl_cdip
  - smartdoc_qa
l4_generation_script: scripts/generate_skew_dataset.py
l4_gcs_path: gs://image_detection_b/skew_training/
l4_image_count: 90412
---
```

### 4.4 Rules

- `__l4_category__` and `__l4_dataset__` are **required** for all adapter files in `ADAPTER_DIR_PATTERNS`
- `__l4_workstream__` is **required**
- All other fields are **optional but encouraged**
- Dataset names must match canonical names from `docs/datasets/DATASET_NAMING_STANDARD.md`
- The harvester script (`scripts/generate_level4_registries.py` — to be built) will warn on
  missing required fields and skip files with no `__l4_category__`

---

## 5. Proposed Level 4 Document Taxonomy

```text
docs/architecture/diagrams/level-4/
├── index.md                                     MANUAL  — overview, taxonomy, maintenance guide
├── data-preparation/
│   ├── index.md                                 MANUAL  — WS3 overview, links to tables below
│   ├── annotation-parser-registry.md            AUTO    — harvested from __l4_category__=parser
│   ├── annotation-provider-registry.md          AUTO    — harvested from __l4_category__=provider
│   └── annotation-integrate-registry.md         AUTO    — harvested from __l4_category__=integrate-script
├── model-training/
│   ├── index.md                                 MANUAL  — WS2 overview
│   ├── training-dataset-registry.md             SEMI    — YAML front matter from training dataset docs
│   └── model-checkpoint-registry.md             MANUAL  — run IDs, metrics, deployment status
└── production-runtime/
    ├── index.md                                 MANUAL  — WS1 overview
    └── schema-field-population-registry.md      SEMI    — which datasets populate which L2 fields
                                                          (partial PUML already exists at level-2/
                                                           schema-field-population/)
```

**Coverage breakdown**:

| Document | Method | Est. Rows | Priority |
|----------|--------|-----------|----------|
| annotation-parser-registry.md | AUTO | 71 | P0 — largest gap |
| annotation-provider-registry.md | AUTO | 7 | P0 — pairs with parsers |
| annotation-integrate-registry.md | AUTO | ~51 | P0 — closes the WS3 triangle |
| training-dataset-registry.md | SEMI | 10 | P1 — small, high value |
| model-checkpoint-registry.md | MANUAL | ~8 | P2 — deferred |
| schema-field-population-registry.md | SEMI | ~30 | P2 — partially covered |

---

## 6. The Harvester Script (To Be Built)

`scripts/generate_level4_registries.py` — the key automation deliverable.

### Approach

```python
# Pseudo-code sketch — do not treat as final API
def harvest_python_l4_metadata(repo_root: Path) -> list[dict]:
    """
    For each .py file in git:
      - Extract __l4_* module-level variable assignments via AST (not regex/import)
      - Skip files with no __l4_category__
      - Return list of {path, l4_category, l4_dataset, l4_workstream, ...}
    Use ast.parse() + ast.walk() to find Assign nodes with targets named __l4_*
    """

def harvest_yaml_l4_metadata(repo_root: Path) -> list[dict]:
    """
    For each .md file with YAML front matter:
      - Extract l4_* front matter fields
      - Return same shape as Python harvest
    """

def generate_parser_registry(records: list[dict], output_path: Path) -> None:
    """
    Filter records where l4_category == "parser"
    Group by l4_task (layout, quality, correction, handwriting, …)
    Emit markdown table per group, sorted by l4_dataset
    Cross-reference l4_integrate field to link to integrate script
    """
```

### Why AST, not regex

The `__l4_*` variables use standard Python assignment syntax. AST parsing is:

- Immune to string formatting variations
- Handles multi-line values correctly
- Already used by vulture (which is configured in `pyproject.toml`)

### CLI

```text
python scripts/generate_level4_registries.py [options]

Options:
  --repo-root PATH    Repository root
  --output-dir PATH   Level 4 output dir (default: docs/architecture/diagrams/level-4/)
  --category {parser,provider,integrate-script,training-dataset,all}
  --check             Validate headers without writing (CI use)
  --json              Emit raw harvested metadata as JSON
```

`--check` mode is the CI gate: fail if any file in `ADAPTER_DIR_PATTERNS` is missing
required `__l4_*` fields.

---

## 7. Level 4 Index and Table Format

### `index.md` header convention (all Level 4 documents)

```yaml
---
owner: docs-team
title: 'Level 4: Annotation Parser Registry'
l4_category: parser
l4_generated: auto        # auto | manual | semi
l4_generator: scripts/generate_level4_registries.py
l4_last_generated: 2026-02-23
tags:
- architecture
- level-4
- registry
---
```

### Table format for AUTO documents (annotation-parser-registry.md)

```markdown
## Layout Parsers (11 datasets)

| Dataset | Parser File | Task | Integrate Script | L2 Metadata |
| ------- | ----------- | ---- | ---------------- | ----------- |
| [doclaynet](../../../datasets/source/doclaynet.md) | `parsers/layout/doclaynet.py` | layout | `integrate_doclaynet_enrichments.py` | `doclaynet_metadata.json` |
| [funsd](../../../datasets/source/funsd.md) | `parsers/layout/funsd.py` | layout | `integrate_funsd_enrichments.py` | `funsd_metadata.json` |
…

## Quality Parsers (12 datasets)

| Dataset | Parser File | Task | Integrate Script | L2 Metadata |
…
```

Note: Dataset names link to `docs/datasets/source/{name}.md` where those files exist —
this is the bridge between Level 4 and the existing dataset documentation tier.

### Table format for SEMI documents (training-dataset-registry.md)

```markdown
## Training Datasets

| Training Dataset | Images | Sources | Generation Script | GCS Path | Status |
| ---------------- | ------ | ------- | ----------------- | -------- | ------ |
| skew | 90,412 | doclaynet, rvl_cdip, smartdoc_qa (+8 more) | `generate_skew_dataset.py` | `gs://…/skew_training/` | ✅ Complete |
| orientation | 50,000 | doclaynet, rvl_cdip | `build_orientation_real_component.py` | `gs://…/orientation/` | ✅ Complete |
…
```

---

## 8. Integration with Existing Audit Tools

### 8.1 Updates to `triage_gap_a.py`

Once `__l4_*` headers are present, the triage script's DATASET_ADAPTER classification
becomes verifiable rather than path-pattern-based. Add a check:

```python
# In enrich_and_classify():
if record.classification == BUCKET_ADAPTER:
    has_l4_header = check_l4_header(filepath, repo_root)
    if not has_l4_header:
        record.classification_reason += " [MISSING_L4_HEADER]"
```

### 8.2 Updates to `audit_diagram_file_coverage.py`

Add a fifth gap category: **GAP_E** — files in ADAPTER_DIR_PATTERNS that lack
required `__l4_*` headers. This makes missing Level 4 headers a first-class audit
finding alongside missing PUML references.

### 8.3 CI gate

Add to `.github/workflows/ci.yml` after the existing validation jobs:

```yaml
- name: Validate Level 4 headers
  run: python scripts/generate_level4_registries.py --check
```

Fail condition: any file in `ADAPTER_DIR_PATTERNS` missing `__l4_category__` or
`__l4_dataset__`.

---

## 9. Bootstrapping Order (Recommended)

This is the recommended implementation sequence to get to a working Level 4 system
incrementally, verifying at each step.

### Phase 0 — Infrastructure (1–2 days)

1. Write `scripts/generate_level4_registries.py` with `--check` mode only (no writes yet)
2. Create `docs/architecture/diagrams/level-4/` directory tree with stub `index.md` files
3. Update `ARCHITECTURE_MAINTENANCE_GUIDE.md` to document Level 4 alongside Levels 0–3

### Phase 1 — Annotation WS3 (2–3 days)

1. Add `__l4_*` headers to all 71 parser files (can be partially scripted using
   existing docstrings — dataset name is usually in the first sentence)
2. Add `__l4_*` headers to all 7 enrichment provider files
3. Add `__l4_*` headers to all ~51 `scripts/integrate_*_enrichments.py` files
4. Run harvester → generate `annotation-parser-registry.md`,
   `annotation-provider-registry.md`, `annotation-integrate-registry.md`
5. Verify cross-links to `docs/datasets/source/` pages

### Phase 2 — Training Datasets WS2 (1–2 days)

1. Add `l4_*` YAML front matter to the 10 training dataset docs in
   `docs/datasets/training/`
2. Run harvester → generate `training-dataset-registry.md`

### Phase 3 — CI Gate + Maintenance Automation

1. Add `--check` mode to CI workflow
2. Update Level 3 swimlane for WS3 data preparation to reference Level 4 registries
3. Document "how to add a new dataset" incorporating the `__l4_*` header step

### Phase 4 — Manual Documents (ongoing)

1. `model-checkpoint-registry.md` — manually maintained as training runs complete
2. `schema-field-population-registry.md` — consolidate existing PUML coverage

---

## 10. Open Questions for the Implementing Team

These were explicitly left open in the design conversation:

| # | Question | Context |
|---|----------|---------|
| Q1 | Should `source-dataset-registry.md` become Level 4 canonical, or just link to `docs/datasets/`? | `docs/datasets/DATASET_QUICK_REFERENCE.md` already contains much of this information. Creating a Level 4 duplicate risks staleness. Linking may be sufficient. |
| Q2 | Table granularity for annotation-parser-registry: one flat table (71 rows) or grouped by task category? | Grouped (by layout, quality, correction, handwriting, etc.) is more readable but requires consistent `__l4_task__` values across all 71 files. |
| Q3 | Should `generate_level4_registries.py` regenerate files in-place (overwriting), or use a header fence like `<!-- AUTO-GENERATED -->` to preserve manually-edited sections? | Files like `annotation-parser-registry.md` are fully auto-generated (no manual editing expected). The fence pattern is only needed for SEMI documents. |
| Q4 | Naming convention for `__l4_dataset__`: exact canonical name or allow aliases? | Canonical names are defined in `docs/datasets/DATASET_NAMING_STANDARD.md`. The harvester should validate against that file's registry. |
| Q5 | Should Level 4 documents appear in DIAGRAM_INDEX.md and be included in PUML reference counts? | Currently the audit counts PUML references only. Level 4 could be a parallel coverage path, but this requires updating `audit_diagram_file_coverage.py`. |

---

## 11. Key Files to Read Before Starting

| File | Why |
|------|-----|
| `docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md` | Existing Level 0–3 conventions; Level 4 must be consistent |
| `docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md` | Style reference for a Level 3 WS3 document |
| `docs/architecture/DIAGRAM_COVERAGE_AUDIT.md` | Current audit baseline (579 files, 453 GAP_C, 425 GAP_A) |
| `docs/architecture/GAP_A_TRIAGE_REPORT.md` | The 135 DATASET_ADAPTER files are exactly the Level 4 subject matter |
| `scripts/audit_diagram_file_coverage.py` | Audit infrastructure; Level 4 should integrate here (GAP_E) |
| `scripts/triage_gap_a.py` | `ADAPTER_DIR_PATTERNS` constant defines which directories require `__l4_*` headers |
| `src/…/annotation/parsers/base.py` | Parser framework; `DatasetParser` protocol is what every parser implements |
| `src/…/annotation/parsers/layout/doclaynet.py` | Reference parser — existing header style to extend with `__l4_*` |
| `docs/datasets/DATASET_NAMING_STANDARD.md` | Canonical dataset names; `__l4_dataset__` values must match |
| `docs/datasets/TRAINING_DATASET_CATALOG.md` | Training dataset documentation; source for `training-dataset-registry.md` |

---

## 12. Success Criteria

The Level 4 system is complete when:

1. `python scripts/generate_level4_registries.py --check` passes with 0 warnings
2. `docs/architecture/diagrams/level-4/data-preparation/annotation-parser-registry.md`
   exists with all 71 parsers in the table
3. Every row in the parser registry links to a `docs/datasets/source/{name}.md` page
4. `ARCHITECTURE_MAINTENANCE_GUIDE.md` documents Level 4 alongside Levels 0–3
5. "How to add a new dataset" checklist includes the `__l4_*` header step
6. CI passes with the Level 4 header validation gate enabled

---

*Handoff prepared 2026-02-23. Branch: `docs/har-systematic-head-review`.*
*Related triage reports: `docs/architecture/GAP_A_TRIAGE_REPORT.md`,*
*`docs/architecture/GAP_C_TRIAGE_REPORT.md`.*
