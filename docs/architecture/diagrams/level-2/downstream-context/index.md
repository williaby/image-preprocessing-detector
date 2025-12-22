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
purpose: "Document the downstream projects that consume Project A output - OCR orchestration,
  fusion, and vector store."
---

# Level 2: Downstream Context

This level provides context diagrams for the downstream projects in the RAG pipeline that consume Project A output.

---

## Project B: OCR & Layout Workflow

OCR orchestration and full layout detection (receives Project A output).

![Project B OCR Layout Workflow](project-b-ocr-layout-workflow.svg)

---

## Project C: Fusion & Chunking Workflow

Multi-engine fusion, trust scoring, and RAG chunking.

![Project C Fusion Chunking Workflow](project-c-fusion-chunking-workflow.svg)

---

## Project D: Vector Store Workflow

Embedding generation and vector database storage.

![Project D Vector Store Workflow](project-d-vectorstore-workflow.svg)

---

## Pipeline Flow

```
Project A (THIS REPO)  →  Project B  →  Project C  →  Project D
Preprocessing & IQA       OCR Layout     Fusion        Vector Store
───────────────────       ──────────     ──────        ────────────
• IQA & Corrections       • Full Layout  • Trust       • Embeddings
• Text Gate               • Reading Order• Scoring     • Vector DB
• DQS & Routing           • Table Struct • RAG Chunks  • Retrieval
```

---

## A→B Contract

Project A outputs that Project B consumes:

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
| **Level 1** | [Project A Architecture](../../level-1/index.md) | Project A system |
| **Level 2** | [Production Runtime](../production-runtime/index.md) | Project A workflow |
