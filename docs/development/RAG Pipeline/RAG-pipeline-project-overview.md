# Document Intelligence Program

## Updated Project Structure & Division of Responsibilities

**Version:** 2.0
**Scope:** Applies to Project A, Project B, Project C, and Project D
**Purpose:** Ensure project teams understand what they own, what they consume, and what they must not duplicate.

---

# 1. End-to-End Pipeline Summary

```
Source Files
   ↓
(A) Preprocessing & IQA
   ↓  Corrected images + DocumentMetadata
(B) OCR & Structure Extraction
   ↓  Paragraph-centric OCRDocument
(C) Fusion, Trust & RAG Chunk Builder
   ↓  FusedDocument + rag_chunks
(D) Vector Indexing & Metadata Enrichment
   ↓  Vector DB for RAG
Downstream RAG Applications
```

---

# 2. Project A — Preprocessing, IQA & Coarse Layout

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

---

# 3. Project B — OCR & Fine Structural Parsing

### Mission

Perform multi-engine OCR and full document layout analysis, producing paragraph-centric structured text aligned with headings and page geometry.

### Inputs

* Corrected page images
* DocumentMetadata.json from Project A (including `pre_ocr_risk` + layout summary)

### Outputs

* **OCRDocument.json** containing:

  * Full block-level layout (DocLayNet / DocLayout-YOLO)
  * Reading order
  * Paragraph objects derived from **Marker**
  * Per-engine OCR text (Marker, DeepSeek-OCR, optional specialized engines)
  * Headings, titles, captions
  * Page/block/paragraph IDs and coordinates
  * Table & math extraction hooks

### Responsibilities (In Scope)

* Profile selection based on A’s routing metadata

  * heavy model for complex/multi-column pages
  * math-aware OCR for dense equations
  * dual-engine OCR for low-quality scans
* Full layout detection (YOLO-based)
* Reading order reconstruction
* **Marker OCR as primary engine** with paragraph segmentation
* DeepSeek-OCR as secondary engine for refinement / error detection
* Table, figure, math, handwriting pipelines when needed
* Produce **semantic paragraphs** aligned to layout and headings

### Out of Scope (MUST NOT implement)

* IQA or image corrections
* Multi-engine fusion
* Noise classification or trust scoring
* Chunking logic for RAG (beyond paragraph segmentation)

---

# 4. Project C — Fusion, Trust, Noise & RAG Chunking

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

---

# 5. Project D — RAG Indexing & Metadata Enrichment

### Mission

Transform trusted RAG chunks into embeddings with hierarchical metadata and upsert them into vector databases for downstream retrieval.

### Inputs

* FusedDocument.json from Project C
* rag_chunks[] with trust/noise scores & structural metadata

### Outputs

* Vector DB entries
* Metadata catalog entries
* Optional full-text (BM25) indices
* Ingestion report (success / skipped / quarantined)

### Responsibilities (In Scope)

* Apply project-specific acceptance policies:

  * drop low-trust chunks
  * quarantine noise-heavy sections
  * route table/math chunks to special indexes
* Embedding generation:

  * Local models
  * Modal GPU calls
  * External API embeddings
* Hierarchical metadata construction:

  * heading_path
  * paragraph_ids
  * structural_role (body, caption, table_cell, figure_context)
  * page_range
  * document_type / pdf_type
  * RAG_readiness_score
  * OCR trust metrics
* Vector DB operations:

  * upsert
  * namespace/collection creation
  * metadata indexing
  * optional BM25 sync

### Out of Scope (MUST NOT implement)

* OCR
* Layout detection
* Fusion or chunk segmentation
* RAG application logic (chatbots, QA, etc.)

---

# 6. Cross-Project Design Principles

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

---

# 7. Responsibility Matrix (RACI-style quick reference)

| Task                          | A | B | C | D |
| ----------------------------- | - | - | - | - |
| Rasterize pages               | ✔ | — | — | — |
| IQA / DIQA                    | ✔ | — | — | — |
| Corrections (deskew, denoise) | ✔ | — | — | — |
| Coarse layout classification  | ✔ | — | — | — |
| Detailed layout detection     | — | ✔ | — | — |
| Reading order                 | — | ✔ | — | — |
| OCR (Marker, DeepSeek)        | — | ✔ | — | — |
| Paragraph segmentation        | — | ✔ | — | — |
| Multi-engine fusion           | — | — | ✔ | — |
| Noise classification          | — | — | ✔ | — |
| Trust scoring                 | — | — | ✔ | — |
| RAG chunking                  | — | — | ✔ | — |
| Embeddings                    | — | — | — | ✔ |
| Vector indexing               | — | — | — | ✔ |
| Metadata catalog              | — | — | — | ✔ |

---

# 8. Repository Structure (Recommended)

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

---

# 9. Summary

This unified reference defines:

* **What each project owns**
* **What each project must not duplicate**
* **How structural information and paragraph segmentation propagate**
* **Where accuracy, trust, and noise control happen**
* **Where embeddings & indexing live**

It ensures every team delivers its part cleanly while maintaining a high-precision end-to-end pipeline optimized for RAG.

---
