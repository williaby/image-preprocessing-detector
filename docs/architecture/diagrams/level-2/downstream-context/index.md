---
schema_type: common
title: "Level 2: Downstream Context"
description: "Context diagrams for downstream projects (B, C, D) in the RAG pipeline"
tags:
- architecture
- diagrams
- plantuml
- level_2
- downstream_context
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the downstream projects that consume Prepare-Doc output - OCR orchestration,
  fusion, and vector store."
---
This level provides context diagrams for the downstream projects in the RAG pipeline that consume Prepare-Doc output.

---

## Unify: OCR & Layout Workflow

OCR orchestration and full layout detection (receives Prepare-Doc output).

![Unify OCR Layout Workflow](unify-ocr-layout-workflow.svg)

---

## Chunk: Fusion & Chunking Workflow

Multi-engine fusion, trust scoring, and RAG chunking.

![Chunk Fusion Chunking Workflow](chunk-fusion-chunking-workflow.svg)

---

## Embed: Vector Store Workflow

Embedding generation and vector database storage.

![Embed Vector Store Workflow](embed-vectorstore-workflow.svg)

---

## Pipeline Flow

```text
Prepare-Doc (THIS REPO)  →  Unify  →  Chunk  →  Embed
Preprocessing & IQA       OCR Layout     Fusion        Vector Store
───────────────────       ──────────     ──────        ────────────
• IQA & Corrections       • Full Layout  • Trust       • Embeddings
• Text Gate               • Reading Order• Scoring     • Vector DB
• DQS & Routing           • Table Struct • RAG Chunks  • Retrieval
```

---

## A→B Contract

Prepare-Doc outputs that Unify consumes:

| Output | Format | Description |
|--------|--------|-------------|
| DocumentMetadata.json | JSON | Quality scores, routing, layout summary |
| Corrected Images | PNG/JPEG | Deskewed, enhanced page images |
| pdf_type | Enum | image_only, born_digital, hybrid |
| ocr_routing_recommendation | Enum | OCR_FAST, OCR_ADVANCED, VISION_* |

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 0** | [RAG Pipeline Overview](../../level-0/index.md) | Multi-project context |
| **Level 1** | [Prepare-Doc Architecture](../../level-1/index.md) | Prepare-Doc system |
| **Level 2** | [Production Runtime](../production-runtime/index.md) | Prepare-Doc workflow |
