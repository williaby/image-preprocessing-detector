---
schema_type: common
title: "Stale Naming Backlog"
description: "Architecture files that still use retired Foundry pipeline names and need diagram tooling or history-aware edits."
tags:
- architecture
- backlog
status: draft
owner: "core-maintainer"
purpose: "Track files deliberately left unchanged when entry points were aligned with the shared Level 0 naming."
---

# Stale Naming Backlog

Entry points were aligned with the canonical names in [pipeline-level-0.md](pipeline-level-0.md). The files below still
carry retired framing and were not edited: they are PlantUML sources (regenerate SVG and PNG with the diagram tooling),
generated images, schema descriptions, or planning history. Canonical names: `DoclingDOM.json` (not `OCRDocument.json`),
`RAGChunkSet.json`, Unify runs OCR through docling-serve first (specialist engines and fusion come later), no
embedding stage in the pipeline, no Project A-F names.

## Diagram sources (edit the puml, then regenerate images)

- `docs/architecture/diagrams/level-0/rag-pipeline-overview.puml`: Unify box says "Multi-engine OCR"; should say OCR
  through docling-serve. Regenerate `rag-pipeline-overview.svg` and PNG.
- `docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml`: `OCRDocument` (3 places)
  should be `DoclingDOM`; the multi-engine flow is a later phase.
- `docs/architecture/diagrams/level-2/downstream-context/chunk-fusion-chunking-workflow.puml`: `OCRDocument` input
  should be `DoclingDOM`; fusion in Chunk is not the current plan.
- `docs/architecture/diagrams/level-2/downstream-context/data_ingestor-migration.puml`: `OCRDocument` (2 places)
  should be `DoclingDOM`.
- `docs/architecture/diagrams/level-2/downstream-context/embed-vectorstore-workflow.puml`: file name and title still
  say Embed service; content should read as the application-side embedding contract.
- Generated `.svg` and `.png` files beside the sources above carry the same text.

## SigLIP head count

Markdown pages now say 16 heads across 5 groups (Release 1). Remaining follow-ups:

- `docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md`: the per-head table still lists
  the pre-Release-1 head names (for example five IQA heads, `script_family`); it carries an inline "under revision"
  note and needs a rewrite against `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`.
- `docs/architecture/diagrams/level-2/model-arena/index.md`: graduation and benchmark tables still list IQA heads such
  as "noise" and "etc."; align with the three DIQA-aligned IQA heads.
- Diagram sources (`.puml`) and generated `.svg`/`.png` files under `docs/architecture/diagrams/` may still say 19 heads
  (not checked; see the diagram section above).

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
