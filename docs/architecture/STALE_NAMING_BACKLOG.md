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

## SigLIP head count (16 after this change, 19 in older text)

Level 1 and Level 0 pages now say 16 heads. These files still say 19 and need a pass together with code review:

- `docs/architecture/diagrams/level-2/model-training/index.md`
- `docs/architecture/diagrams/level-2/production-runtime/index.md`
- `docs/architecture/diagrams/level-2/model-arena/index.md`
- `docs/architecture/diagrams/level-2/synthetic-generation/index.md`
- `docs/architecture/diagrams/level-3/production-runtime/device-orchestrator.md`
- `docs/architecture/diagrams/level-3/production-runtime/pipeline-state-machine.md`
- `docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md`
- `docs/architecture/diagrams/level-3/data-preparation/metadata-schema-versioning.md`
- `docs/architecture/diagrams/level-3/monitoring-drift/end-to-end-lifecycle.md`
- `docs/PROJECT_OVERVIEW_DETAILED.md` and `docs/PROJECT_OVERVIEW.md`: head count updated, but the group-by-group prose
  (for example "Six IQA regression heads", "Four additional regression heads") still describes the older 19-head
  layout and should be reconciled with `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`.

## Other files with retired names

- `docs/schema/document_metadata.schema.json` (lines 5, 82) and `docs/schema/layer2_enrichment_v2.schema.json`
  (lines 185, 1624, 1692): "Project A", "Project B" in descriptions. Schema text changes may need a version note.
- `docs/planning/MASTER_PROJECT_PLAN.md` (lines 46, 66-70): "Multi-engine OCR" and the retired-name mapping table.
  Planning history; the mapping table is intentional.
- `docs/planning/DOCLING_INTEGRATION_GAP_REPORT.md` (line 367): historical description of the old multi-engine design.
- `docs/ADRs/0029-prepare-doc-scope-boundaries.md` (lines 33, 37, 131): "four-project" pipeline, `ocr-orchestrator`,
  `fusion-trust`, `vector-indexer`. Accepted ADR; supersede rather than edit.
- `docs/development/RAG Pipeline/prepare-doc-f-nf.md` (lines 46, 101): "four-project OCR/RAG pipeline" and
  "Multi-engine OCR fusion (Chunk)".
- `docs/development/RAG Pipeline/foundry-unify-team-handoff.md` (line 534): "Project" labels in a link table to an
  archived document.
- `docs/reference/MIGRATION_GUIDE.md` (lines 48, 408): "four-project RAG pipeline" in numbering history.
- `docs/prompts/layer2_audit_prompt.md` (line 16): "four-project RAG document pipeline".
- `docs/handoff/LEVEL4_ARCHITECTURE_DESIGN_HANDOFF.md`, `docs/benchmarks/DEQA_METHODOLOGY_COMPARISON.md`,
  `docs/datasets/**`: matched the level-count or naming search; dataset and benchmark pages not reviewed in detail.
