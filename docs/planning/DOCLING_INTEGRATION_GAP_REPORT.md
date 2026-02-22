---
title: Docling Integration Gap Report
schema_type: planning
status: active
owner: ml-team
purpose: "Identifies gaps, inconsistencies, and improvement areas in Project A's docling
  integration and handoff specification."
tags:
- routing
- integration
component: Strategy
source: Internal analysis of docling integration codebase
---

# Docling Integration Gap Report

> **Scope**: Covers `DoclingRoutingParams`, `DoclingRoutingEngine`, `ScriptRouter`,
> `PROJECT_A_TO_B_HANDOFF_SPECIFICATION.md`, `project-b-ocr-layout-workflow.puml`,
> and `rag-pipeline-overview.puml`.
>
> **Reference**: [docs/reference/DOCLING_CONFIGURATION_REFERENCE.md](../reference/DOCLING_CONFIGURATION_REFERENCE.md)
>
> **Date**: 2026-02-22

---

## Executive Summary

**Architectural boundary** (clarified 2026-02-22): Project A's role is to be an analysis oracle.
It delivers rich `DocumentMetadata` signals — DQS, script detection, orientation, quality scores,
page attributes, handwriting assessment — and Project B translates those signals into docling
configuration. Project A does **not** determine which docling engine, model, or CLI flags to
invoke. That is Project B's responsibility.

This boundary has two consequences for this report:

1. **Correctness bugs in existing Project A code** (Section 1) remain valid and should be fixed —
   wrong engine keys in docstrings, missing CLI flag emission, and undocumented VLM behavior are
   real bugs regardless of where docling config ultimately lives.

2. **Recommendations to expand `DoclingRoutingParams`** (formerly Section 2) are architecturally
   wrong — adding more docling-specific fields to Project A would push the boundary in the wrong
   direction. Section 2 is now reframed as a **signal coverage audit**: for each docling lever
   Project B might want to tune, we verify that Project A already exposes the right analysis
   signal.

The most critical existing bug is a **wrong engine key** (`paddleocr`) embedded in schema
docstrings and router code — PaddleOCR is accessible in docling only via the `rapidocr` engine
(RapidOCR wraps PaddleOCR; there is no first-class `paddleocr` key).

---

## Section 0 — Architectural Boundary

### 0.1 The Correct Separation of Concerns

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| **Analysis signals** | Project A | Detect quality, script, orientation, layout attributes, handwriting, shadow/warping severity |
| **Docling configuration** | Project B | Translate signals into `PipelineOptions`, OCR engine selection, enrichment flags, layout model variant, VLM model choice, CLI invocation |

Project A's `DocumentMetadata.json` is the contract. Everything in it is an analysis result, not a
docling instruction.

### 0.2 `DoclingRoutingEngine` and `DoclingRoutingParams` Are Architecturally Misplaced

**Locations**:

- [src/image_preprocessing_detector/routing/docling_router.py](../../src/image_preprocessing_detector/routing/docling_router.py)
- [src/image_preprocessing_detector/schema.py](../../src/image_preprocessing_detector/schema.py) —
  `DoclingRoutingParams`, including `to_cli_args()`

These components — a six-rule engine that converts Project A analysis into docling CLI arguments —
belong in Project B, not Project A. Project A should not be emitting `--pipeline=vlm` or
`--no-tables`; that translation is Project B's job.

**Impact**: Low urgency while Project B is not yet implemented. The existing code is not harmful
(Project B may choose to adopt these components as a starting point), but should be tracked.

**Recommendation**: When Project B begins integration work, migrate `DoclingRoutingEngine` and
`DoclingRoutingParams.to_cli_args()` to Project B's codebase. Project A retains `DocumentMetadata`
as the output contract; `DoclingRoutingParams` may evolve into a lighter "advisory hints" struct
that Project B can accept or override.

---

## Section 1 — Critical Bugs (Fix Before Production)

### 1.1 `paddleocr` Is Not a Valid Docling Engine Key

**Severity**: CRITICAL — will pass an invalid value to docling's engine selector

**Locations**:

- [schema.py:767](../../src/image_preprocessing_detector/schema.py#L767) — field description:
  `"OCR engine: 'auto', 'rapidocr', 'paddleocr', 'tesseract'"`
- [script_router.py:174](../../src/image_preprocessing_detector/routing/script_router.py#L174) —
  method docstring: `Returns: Engine name string (e.g., "rapidocr", "paddleocr", "tesseract")`
- `config/script_routing.yaml` — may reference `paddleocr` in routing rules (unverified)

**Clarification**: Docling does not expose PaddleOCR directly. PaddleOCR is available *through*
the `rapidocr` engine — RapidOCR wraps PaddleOCR models. A Docling maintainer confirmed:
*"We have RapidOCR in docling, which wraps PaddleOCR."*
([discussion #626](https://github.com/docling-project/docling/discussions/626))

Docling's registered engine keys are: `auto`, `rapidocr`, `easyocr`, `tesseract`,
`tesseract_cli`, `ocrmac`. Passing `paddleocr` is an invalid key.

**Fix required**:

1. Update `DoclingRoutingParams.ocr_engine` field description — replace `'paddleocr'` with
   `'rapidocr'` and add a note that RapidOCR is the PaddleOCR-backed path
2. Update `ScriptRouter.get_engine()` docstring to use `rapidocr` in the example
3. Audit `config/script_routing.yaml` for any `engine: paddleocr` entries — replace with
   `engine: rapidocr`

---

### 1.2 `--tables` / `--no-tables` Never Emitted

**Severity**: HIGH — note: architectural relocation pending (§0.2), but the bug exists now

**Location**: [schema.py:794-830](../../src/image_preprocessing_detector/schema.py#L794) —
`DoclingRoutingParams.to_cli_args()`

**Problem**: The `tables_enabled` field exists in `DoclingRoutingParams` but `to_cli_args()`
never emits `--no-tables` when `tables_enabled=False`. Because docling defaults to tables
enabled, the current code has no way to signal table-skip to Project B via CLI args — an
optimization that matters for throughput on simple text-only documents.

While `to_cli_args()` will ultimately move to Project B (§0.2), the immediate fix ensures the
advisory hint is correctly serializable in the interim.

**Fix required**: Add to `to_cli_args()`:

```python
if not self.tables_enabled:
    args.append("--no-tables")
```

---

### 1.3 VLM Pipeline Selects No VLM Model

**Severity**: MEDIUM — relies on docling default, not an explicit routing decision

**Location**: [docling_router.py:340-348](../../src/image_preprocessing_detector/routing/docling_router.py#L340)
— `_apply_vlm_escalation_rule()`

**Problem**: When the VLM pipeline is triggered, `params.vlm_model` remains `None` throughout
all six routing rules. `DoclingRoutingParams.vlm_model` defaults to `None` and `to_cli_args()`
only emits `--vlm-model=<value>` when it is not None. Project B therefore receives
`--pipeline=vlm` with no model specification.

Docling's default VLM is `granite_docling` (IBM Granite DocLing model). This may be intentional
but it is undocumented and untestable. Per §0.2, VLM model selection is Project B's decision
anyway — but the intent should be documented.

**Fix required**:

1. Add a docstring note to `DoclingRoutingParams.vlm_model` and `_apply_vlm_escalation_rule()`
   stating that `None` means "use docling default (`granite_docling`)" and that Project B should
   make the final VLM model selection based on the escalation reason supplied in `DocumentMetadata`
2. Expose the VLM escalation reason (e.g., `handwriting_detected`, `low_dqs_degradation`,
   `unknown_script`) in `DocumentMetadata` so Project B has the signal to choose the right VLM

---

## Section 2 — Signal Coverage Audit for Project B

This section maps docling configuration levers to the Project A analysis signals that Project B
can use to set them. Where a signal is missing from `DocumentMetadata`, the recommendation is
to ensure Project A exposes it — not to add the docling config parameter to Project A.

### 2.1 OCR Enablement → `text_layer_quality`, `text_layer_skip_ocr`

**Docling lever**: `ocr_enabled`, `force_backend_text`

**Signals available in `DocumentMetadata`**:

- `pages[].text_layer_quality` — 0–1 score of native text layer quality
- `pages[].text_layer_skip_ocr` — boolean: Project A recommends skipping OCR

**Coverage**: ✅ Complete. Project B can set `ocr_enabled=False` and `force_backend_text=True`
when `text_layer_quality >= 0.90` and `text_layer_skip_ocr=True`.

---

### 2.2 OCR Engine Selection → Script Detection

**Docling lever**: `ocr_engine` (`auto`, `rapidocr`, `easyocr`, `tesseract`, `tesseract_cli`)

**Signals available in `DocumentMetadata`**:

- `script_detection.dominant_script` — ISO 15924 code (e.g., `Latn`, `Arab`, `Hant`)
- `script_detection.ml_class` — grouped ML class (e.g., `LATN`, `ARAB`, `CJK`)
- `script_detection.confidence` — detection confidence 0–1

**Coverage**: ✅ Complete. Project B's engine selection table:

| Script class | Recommended engine |
|-------------|-------------------|
| `LATN`, `CYRL`, `GREK` | `rapidocr` (RapidOCR/PaddleOCR) |
| `ARAB`, `HEBR` | `easyocr` (RTL support) |
| `CJK`, `HANG`, `KANA_HIRA` | `rapidocr` (CJK models) |
| Low confidence or `Zzzz` | `auto` or VLM escalation |

---

### 2.3 VLM Escalation → DQS, Handwriting, Script Confidence, Warping

**Docling lever**: `pipeline=vlm`, `vlm_model`

**Signals available in `DocumentMetadata`**:

- `dqs.degradation_score` — overall degradation
- `handwriting_assessment.has_handwriting`, `.handwriting_ratio`
- `script_detection.confidence` — low confidence → unknown script → VLM
- `pages[].warping_score` — *pre-correction* warping severity

**Coverage**: ✅ Largely complete. **One gap**: warping escalation should use the
*post-correction* warping state, not the raw detection score. The existing
`DoclingRoutingEngine` triggers VLM on `warping_score > 0.75` but Project A's correction
pipeline already applies perspective correction. Project B should check whether correction
was applied (`transform_history` in `PageMetadata`) before escalating on warping alone.

---

### 2.4 Table Extraction → `has_tables`, Layout Complexity

**Docling lever**: `tables_enabled`, `table_mode` (`FAST` / `ACCURATE`), `do_table_structure`

**Signals available in `DocumentMetadata`**:

- `page_layout_summary[].has_tables` — table presence per page
- `dqs.structural_complexity_score` — document-level complexity

**Coverage**: ✅ Complete. Project B can:

- Disable table extraction when no page has `has_tables=True` (throughput optimization)
- Use `TableFormerMode.ACCURATE` when `structural_complexity_score >= 0.7`

---

### 2.5 Enrichments → `has_figures`, `has_code`, Domain Classification

**Docling levers**: `do_picture_description`, `do_chart_extraction`, `do_code_enrichment`,
`do_formula_enrichment`

**Signals available in `DocumentMetadata`**:

- `page_layout_summary[].has_figures` — figure presence
- `pages[].code_content_ratio` — fraction of page with code-like content (SigLIP 2 head)
- `page_layout_summary[].has_dense_math` — formula presence

**Coverage**: ⚠️ Partial gap. `has_figures` and `has_dense_math` are present. However:

- **Chart extraction**: No domain classification signal in `DocumentMetadata` currently.
  `has_figures=True` is necessary but not sufficient — charts are figures, but not all figures
  are charts. Project A could expose a `figure_type_distribution` or domain hint (financial/
  scientific) to help Project B decide whether `do_chart_extraction` is worthwhile.
- **Picture description quality gate**: Project B should check `pages[].overall_quality >= 0.6`
  before enabling picture description enrichment — describing blurry/degraded images wastes
  compute.

**Recommendation**: No new `DoclingRoutingParams` fields needed. Ensure `DocumentMetadata`
exposes `pages[].overall_quality` at the page level for Project B to use as a quality gate,
and consider adding a `domain_hints` field (e.g., `financial`, `scientific`) derived from
content analysis in a future SigLIP 2 head.

---

### 2.6 Layout Model Variant → Structural Complexity

**Docling lever**: Layout model preset (`DOCLING_LAYOUT_HERON` vs `DOCLING_LAYOUT_EGRET_LARGE`
vs `DOCLING_LAYOUT_EGRET_XLARGE`)

**Signals available in `DocumentMetadata`**:

- `dqs.structural_complexity_score` — 0–1 complexity metric
- `page_layout_summary[].has_tables`, `.has_figures` — content flags

**Coverage**: ✅ Complete. Project B can apply:

- `HERON` (fast, 4GB): `structural_complexity_score < 0.5`, simple single/multi-column
- `EGRET_LARGE` (8GB): `structural_complexity_score >= 0.5` or `has_tables=True`
- `EGRET_XLARGE` (12GB): `structural_complexity_score >= 0.8` or extreme table complexity

---

### 2.7 Resolution Scaling → Resolution Quality, Character Height

**Docling lever**: `images_scale` (default 1.0)

**Signals available in `DocumentMetadata`**:

- `pages[].resolution_quality` — 0–1 resolution adequacy score
- `pages[].char_height_px` — median character height in pixels (MobileNetV4 measurement)
- `pages[].dpi_effective` — effective DPI after upscaling

**Coverage**: ✅ Complete. Project B can map:

| `resolution_quality` | Recommended `images_scale` |
|--------------------|--------------------------|
| `>= 0.7` (optimal) | `1.0` |
| `0.4–0.7` (adequate) | `1.5` |
| `< 0.4` (marginal) | `2.0` |

---

### 2.8 PSM Modes → Orientation, Layout Type

**Docling lever**: `ocr_options.tesseract_parameters["tessedit_pageseg_mode"]` (PSM 0–13)

**Signals available in `DocumentMetadata`**:

- `pages[].orientation.detected_angle` — 0/90/180/270
- `page_layout_summary[].layout_type` — single_column/multi_column/complex

**Coverage**: ✅ Complete. Project B can:

- Set PSM 0 (auto OSD) when orientation correction was skipped
- Set PSM 6 (single block) for single-column simple layouts
- Set PSM 3 (auto) for multi-column/complex layouts

---

## Section 3 — Inconsistencies in Documentation

### 3.1 `PROJECT_A_TO_B_HANDOFF_SPECIFICATION.md` Is Significantly Outdated

**File**: [docs/planning/PROJECT_A_TO_B_HANDOFF_SPECIFICATION.md](PROJECT_A_TO_B_HANDOFF_SPECIFICATION.md)
**Date on file**: 2026-01-12

The specification predates significant architectural decisions and does not reflect the current
system. Specific gaps:

| Missing Element | Current State |
|----------------|---------------|
| `docling_params: DoclingRoutingParams` field | Exists in schema.py since routing work |
| `script_detection: DocumentScriptDetection` | Added in three-tier architecture work |
| `text_layer_quality`, `text_layer_skip_ocr` | Added for born-digital path |
| `degradation_severity: "simple"/"complex"` | Added for DocRes/VLM routing |
| Handwriting assessment fields | Added via `HandwritingAssessment` model |
| SigLIP 2 multi-task model (16 heads) | Spec still describes 5-head ResNet-18 |
| 6-rule routing engine | Spec shows simplified 5-row decision table |
| 7-class capture method classification | Not mentioned |
| `code_content_ratio` head | Not mentioned |
| **Architectural boundary** | Spec implies Project A prescribes docling config; reality is Project B owns configuration decisions |

**Recommendation**: Update the spec to v2 reflecting:

1. Complete `DocumentMetadata` JSON schema including all fields added since January 2026
2. Clear architectural boundary statement: Project A = analysis signals, Project B = docling
   configuration translation
3. The advisory role of `DoclingRoutingParams` — Project B may use or override it
4. SigLIP 2 16-head output fields
5. Remove "4.3 ML IQA Architecture Gap" section (resolved by SigLIP 2)
6. Remove pseudo-label gap (different model architecture now)

---

### 3.2 `project-b-ocr-layout-workflow.puml` Does Not Reflect Docling Usage

**File**: [docs/architecture/diagrams/level-2/downstream-context/project-b-ocr-layout-workflow.puml](../architecture/diagrams/level-2/downstream-context/project-b-ocr-layout-workflow.puml)

The diagram describes a custom multi-engine OCR architecture that does not match what
docling provides. Specific inconsistencies:

| Diagram Shows | Docling Reality |
|---------------|----------------|
| "YOLOv8 / OmniDocBench model" for layout | Docling uses TableFormer + Heron/Egret layout models |
| "Marker / Llama-4 Maverick" as primary OCR | Docling OCR: RapidOCR, EasyOCR, Tesseract, OcrMac |
| "DeepSeek-OCR" as secondary OCR | Not a docling engine |
| "PubTables-1M / ClusterTabNet" for table structure | Docling uses TableFormer |
| No mention of docling as orchestration layer | Docling IS the orchestration layer |

**Recommendation**: Either (a) update to reflect docling-based architecture, or (b) clearly
label this as a "future alternative" or "design variant" and create a separate diagram for the
docling-based implementation.

---

### 3.3 Level-0 Diagram Naming Inconsistencies

**File**: [docs/architecture/diagrams/level-0/rag-pipeline-overview.puml](../architecture/diagrams/level-0/rag-pipeline-overview.puml)

| Diagram Label | Project Docs Label | Issue |
|---------------|--------------------|-------|
| "Unify (foundry-unify)" | "Project B (OCR Orchestration)" | Different names for same component |
| "Docling DOM" | — | Mentioned only as data store, not as OCR orchestration |
| "foundry-prepare-doc" | "Project A" | Service name vs project name inconsistency |

The level-0 diagram uses service/microservice names (`foundry-*`) that differ from the project
names used in all other documentation. **Recommendation**: Align naming — either adopt
`foundry-*` names throughout or use `Project A/B/C/D` throughout. Document the canonical
naming convention in CLAUDE.md.

---

### 3.4 `docling_parameters` vs `docling_params` Field Name Mismatch

**Locations**:

- [docs/PROJECT_OVERVIEW_DETAILED.md:362](../PROJECT_OVERVIEW_DETAILED.md) — lists field as
  `docling_parameters: structured params for docling-layout integration`
- [src/image_preprocessing_detector/schema.py:1345](../../src/image_preprocessing_detector/schema.py#L1345) —
  actual field name is `docling_params: DoclingRoutingParams | None`

**Recommendation**: Correct `PROJECT_OVERVIEW_DETAILED.md` section 4.1 to use `docling_params`.

---

### 3.5 ScriptRouter References Non-Docling Engine

**File**: [routing/script_router.py:174](../../src/image_preprocessing_detector/routing/script_router.py#L174)

The `get_engine()` docstring says `Returns: Engine name string (e.g., "rapidocr", "paddleocr", "tesseract")`.
This is the same `paddleocr` bug from §1.1 — wrong engine key in documentation.

If `config/script_routing.yaml` maps any script to `engine: paddleocr`, docling will receive
an invalid engine value at runtime and either silently fall back to `auto` or raise an error.

---

## Section 4 — Architecture Notes

### 4.1 VLM Warping Trigger May Double-Compensate

[docling_router.py:325](../../src/image_preprocessing_detector/routing/docling_router.py#L325)
triggers VLM escalation when `warping_score > 0.75`. However, Project A's correction pipeline
already applies perspective correction for detected warping (via `correction/perspective_correction.py`).
The image delivered to docling has already been corrected.

Project B should check `transform_history` in `PageMetadata` to determine whether perspective
correction was applied before deciding to escalate on a raw `warping_score` from the pre-correction
analysis.

### 4.2 No Page-Range Signal for Selective Processing

For very large documents where Project A detects quality problems on specific page ranges
(e.g., pages 50–80 have extreme shadow severity), docling supports `page_range` in the
`convert()` call. Project A currently has no way to flag specific page ranges as needing
different treatment.

This is a lower-priority enhancement. If Project B supports per-page decisions, `PageMetadata`
is already per-page; Project B can filter pages by quality score and invoke docling selectively.

### 4.3 `do_picture_classification` Model Availability

The `--enrich-picture-classes` flag requires the picture classification model which may not be
downloaded by default. Project B should validate model availability before enabling this
enrichment based on Project A's `has_figures` signal. Failure mode: silent skip or runtime error.

---

## Section 5 — Recommended Actions Summary

### P0 — Fix Before Any Integration Testing

| ID | Action | File |
|----|--------|------|
| P0-1 | Remove `paddleocr` from `DoclingRoutingParams.ocr_engine` description | `schema.py:767` |
| P0-2 | Remove `paddleocr` from `ScriptRouter.get_engine()` docstring | `script_router.py:174` |
| P0-3 | Audit `config/script_routing.yaml` for `paddleocr` engine entries | `config/script_routing.yaml` |
| P0-4 | Emit `--no-tables` in `to_cli_args()` when `tables_enabled=False` | `schema.py:794` |
| P0-5 | Document VLM default behavior (granite_docling) and expose escalation reason in `DocumentMetadata` | `docling_router.py`, `schema.py` |

### P1 — Before Project B Integration Design

| ID | Action | File |
|----|--------|------|
| P1-1 | Update `PROJECT_A_TO_B_HANDOFF_SPECIFICATION.md` to v2 — reflect current schema and architectural boundary | Planning doc |
| P1-2 | Fix field name: `docling_parameters` → `docling_params` in `PROJECT_OVERVIEW_DETAILED.md` | `PROJECT_OVERVIEW_DETAILED.md:362` |
| P1-3 | Redraw or clarify `project-b-ocr-layout-workflow.puml` | PUML diagram |
| P1-4 | Add migration note to `DoclingRoutingEngine` / `to_cli_args()` that these components belong in Project B (§0.2) | `docling_router.py`, `schema.py` |

### P2 — Enhancement Phase

| ID | Action | File |
|----|--------|------|
| P2-1 | Add `domain_hints` field to `DocumentMetadata` for Project B chart/enrichment decisions | `schema.py` |
| P2-2 | Ensure `pages[].overall_quality` is present at page level for Project B quality gating | `schema.py` |
| P2-3 | Align level-0 diagram naming (`foundry-*` vs `Project A/B/C/D`) | `rag-pipeline-overview.puml` |
| P2-4 | Reassess VLM warping trigger (use post-correction state from `transform_history`) | `docling_router.py:325` |
| P2-5 | Migrate `DoclingRoutingEngine` and `to_cli_args()` to Project B codebase | Project B integration work |

---

*Report generated 2026-02-22 based on review of docling main branch + project source files.
Updated 2026-02-22 to reflect architectural boundary: Project A = analysis signals, Project B = docling configuration.*
