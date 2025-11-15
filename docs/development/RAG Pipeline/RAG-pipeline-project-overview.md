---
schema_type: common
title: "RAG Pipeline Project Overview"
description: "Four-project architecture overview for document processing RAG pipeline"
tags: [architecture, documentation, rag, pipeline]
status: published
owner: "docs-team"
purpose: "Define the complete four-project RAG pipeline architecture with clear responsibility boundaries."
---

## Updated Project Structure & Division of Responsibilities

**Version:** 2.0
**Scope:** Applies to Project A, Project B, Project C, and Project D
**Purpose:** Ensure project teams understand what they own, what they consume, and what they must not duplicate.

## 2. Project A — Preprocessing, IQA & Coarse Layout

### Mission

Deliver clean, corrected, quality-scored page images with reliable metadata that determines which workflows Project B should use.

### Inputs

* Raw PDFs, images, Office documents
* Rasterized pages (when needed)

### Outputs

* **Corrected page images** (deskewed, denoised, corrected)
* **DocumentMetadata.json** containing:

  * IQA metrics (overall, sharpness, color)
  * DQS degradation scores
  * **pre_ocr_risk**
  * Text gate result
  * **Coarse layout & attribute summary:**

    * layout_type (single / multi / complex)
    * has_tables, has_figures
    * has_dense_math, has_handwriting
    * page attributes: fuzzy_scan, watermark, colorful_background

### Responsibilities (In Scope)

* File ingestion & page rasterization
* Classical IQA (blur, skew, noise, DPI, contrast, illumination)
* Learned DIQA (teacher→student)
* Guarded corrections (deskew, binarize, upscale, etc.)
* **Lightweight layout classification** using OmniDocBench page attributes
* Emit routing metadata for Project B

### Out of Scope (MUST NOT implement)

* Full layout detection or precise bounding boxes
* Reading order estimation
* OCR of any type
* Chunking or RAG logic

## 4. Project C — Fusion, Trust, Noise & RAG Chunking

### Mission

Determine the “ground-truth” text via multi-engine fusion, suppress noise, compute trust scores, and convert paragraphs into retrieval-optimized RAG chunks.

### Inputs

* OCRDocument.json from Project B
* Paragraph structure from Marker
* Multi-engine text (Marker + DeepSeek-OCR)

### Outputs

* **FusedDocument.json**
* **rag_chunks[]** with:

  * canonical fused text
  * paragraph IDs
  * chunk_trust_score
  * semantic_noise_score
  * formatting_noise_score
  * RAG_readiness_score
  * Full provenance (doc/page/block/paragraph)
  * Structural context (heading_path, table/figure associations)

### Responsibilities (In Scope)

* Multi-engine fusion: paragraph-level and line-level
* Disagreement scoring between engines
* Noise taxonomy application:

  * **semantic noise** (headers, footers, page numbers, watermarks, junk)
  * **formatting noise** (column mixing, table breakage, caption separation)
* Trust scoring:

  * chunk_trust_score
  * semantic_noise_score
  * formatting_noise_score
  * model_uncertainty
* RAG chunk building:

  * Merge paragraphs when necessary
  * Enforce token windows (e.g., 200–600 tokens)
  * Keep captions with tables/figures
  * Maintain section hierarchy via `heading_path`

### Out of Scope (MUST NOT implement)

* OCR
* Layout detection
* IQA/corrections
* Embedding generation or vector DB logic

## 6. Cross-Project Design Principles

### 1. Immutable Interfaces

Each project consumes upstream outputs *as-is* and must not re-interpret or re-implement earlier stages.

### 2. Schema-First Design

Each artifact has a JSON schema in `/docs/schema/`.

### 3. Reliability Through Multi-Engine Validation

Marker + DeepSeek-OCR comparisons are normalized in Project C rather than buried upstream.

### 4. Trust & Noise Are First-Class Signals

Every chunk entering D has validated, comparable trust metrics.

### 5. Hierarchical Metadata

Section/heading paths flow from B → C → D, giving RAG hierarchical retrieval power.

### 6. Evaluation With OmniDocBench & OHR-Bench

All teams benchmark their components with:

* OmniDocBench (layout, attributes, table/math/reading order)
* OHR-Bench (semantic noise, formatting noise, RAG sensitivity)

### 7. Human-in-the-Loop Extensibility

Each project allows corrected “gold” inputs to feed training sets.

## 8. Repository Structure (Recommended)

```
/docs/
    overview.md
    schema/
        document_metadata.schema.json
        ocr_document.schema.json
        fused_document.schema.json
        rag_chunk.schema.json
/src/
    ...
/models/
/configs/
/tests/
README.md
CHANGELOG.md
```
