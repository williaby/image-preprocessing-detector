---
schema_type: common
title: "Stale Naming Backlog"
description: "Architecture files that still use retired Foundry pipeline names and need diagram tooling or history-aware edits."
tags:
- architecture
- documentation
status: draft
owner: "core-maintainer"
purpose: "Track files deliberately left unchanged when entry points were aligned with the shared Level 0 naming."
---

# Stale Naming Backlog

Entry points were aligned with the canonical names in [pipeline-level-0.md](pipeline-level-0.md). The files below still
carry retired framing and were not edited: they are PlantUML sources (regenerate SVG and PNG with the diagram tooling),
generated images, schema descriptions, or planning history. Canonical names: `DoclingDOM.json` (not `OCRDocument.json`),
`RAGChunkSet.json`, Unify runs OCR through docling-serve first (specialist engines come later; fusion of multi-engine
output stays with Chunk per ADR-0029), no embedding stage in the pipeline, no Project A-F names.

## Diagram sources (edit the puml, then regenerate images)

- `docs/architecture/diagrams/level-0/rag-pipeline-overview.puml`: Unify box says "Multi-engine OCR"; should say OCR
  through docling-serve. Regenerate `rag-pipeline-overview.svg`; the PNG beside it is `RAG_Pipeline_Overview.png`. The
  diagram also still shows Engine Selection and Result Fusion boxes inside Unify, which contradict ADR-0029.
- `docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml`: `OCRDocument` (3 places)
  should be `DoclingDOM`; the multi-engine flow is a later phase.
- `docs/architecture/diagrams/level-2/downstream-context/chunk-fusion-chunking-workflow.puml`: `OCRDocument` input
  should be `DoclingDOM`. Fusion stays in Chunk per ADR-0029 and applies once specialist OCR engines produce
  multi-engine output.
- `docs/architecture/diagrams/level-2/downstream-context/data_ingestor-migration.puml`: `OCRDocument` (2 places)
  should be `DoclingDOM`.
- `docs/architecture/diagrams/level-2/downstream-context/embed-vectorstore-workflow.puml`: file name and title still
  say Embed service; content should read as the application-side embedding contract.
- Generated `.svg` and `.png` files beside the sources above carry the same text.

## SigLIP head count

Three head-count definitions coexist and are not yet reconciled:

- **16 heads** (3+1+2+5+5, including the five handwriting heads): the design in
  `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`. This is the number the Markdown pages edited here now use. It is the
  full design, not the Release 1 scope.
- **16 heads, Release 1** in `docs/planning/MASTER_PROJECT_PLAN.md` section 5a: a different subset, taken from 22 heads
  with the handwriting group and the fine-skew head deferred to Release 2.
- **8 tasks** implemented today in `siglip2_multitask.py` (3 IQA, script, source, orientation, shadow, warping).

Follow-ups, none of them done here:

- Reconcile the three definitions in one place (likely the requirements doc, whose line 47 still says "IQA (6
  regression heads)" against its own 3+1+2+5+5 breakdown) and then align the pages below.
- Many files outside this PR still say 19 heads (some "19" matches are script-class counts, so review each hit):
  planning docs (`docs/planning/`), dataset docs (`docs/datasets/`), handoff docs,
  `docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`, `LEVEL_2_DOCUMENTATION_TEMPLATE.md`, and roughly 14
  PlantUML sources with generated SVGs under `docs/architecture/diagrams/` do. Re-run
  `grep -rnE '19[ -]heads?|19 task heads|19 prediction' docs` to list them.
- `docs/architecture/diagrams/INDEX.md` (Per-Head Views row) still says "25 heads (22 SigLIP 2 + 3 MobileNetV4)".
- Head tables that still list older head names (each page carries an inline note):
  - `docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md`: five IQA heads, `script_family`.
  - `docs/architecture/diagrams/level-2/model-training/index.md`: group table (six IQA heads, three handwriting heads)
    and the ONNX output names.
  - `docs/architecture/diagrams/level-2/model-arena/index.md`: graduation and benchmark tables still list IQA heads such
    as "noise".

## Navigation

- `mkdocs.yml` nav (around lines 220-239): entries "RAG Processor → Project A", "Project A (This Project)", "Project B
  (OCR)", "Project C (Fusion)" and "ADR-029 Project A Scope" keep retired labels, and their targets
  (`rag-processor-project-a-contract.md`, `project-a-project-plan.md`, `unify-f-nf.md`, `chunk-f-nf.md`,
  `0029-project-a-scope-boundaries.md`) do not exist, so the non-strict build warns and skips them. Fix the labels and
  targets together.

## Needs schema release (JSON, out of scope for Markdown passes)

- `docs/schema/document_metadata.schema.json` (lines 5, 82) and `docs/schema/layer2_enrichment_v2.schema.json`
  (lines 5, 185, 1624, 1687, 1692): "Project A", "Project B" in descriptions. Schema text changes need a schema release
  and version note. Mirror copy: `docs/development/RAG Pipeline/document_metadata.schema.json`.

## Other files with retired names

- `docs/handoff/LEVEL4_ARCHITECTURE_DESIGN_HANDOFF.md`, `docs/benchmarks/DEQA_METHODOLOGY_COMPARISON.md`,
  `docs/datasets/**`: matched the level-count or naming search; dataset and benchmark pages not reviewed in detail.
  `docs/datasets/source/{thousand-character-classic,john11-manuscripts,john11-printed-editions}.md` say "Project A team"
  as dataset maintainer; unclear whether that means Prepare-Doc.
- `docs/ADRs/0029-prepare-doc-scope-boundaries.md`: body still uses the four-project names (`ocr-orchestrator`,
  `fusion-trust`, `vector-indexer`); a retirement note was added under its status. A superseding ADR is still optional.
- `docs/planning/MASTER_PROJECT_PLAN.md` and `docs/architecture/diagrams/level-0/index.md`: the struck-through legacy
  mapping rows are intentional history.
