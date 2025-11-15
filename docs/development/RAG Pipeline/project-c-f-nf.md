# Project C Requirements Specification

**OCR Fusion, Semantic Normalization & Hallucination Filtering Layer**
**Version 1.0.0 – Draft**

---

# 0. Executive Summary

**Project C** is the intelligence layer that sits between “raw OCR output” and “RAG-ready text units.” It consumes:

* **DocumentMetadata (Project A)**
* **OCRDocument (Project B)**

and produces:

* **NormalizedTextDocument (structured text units)**
* **RAGChunkSet (semantic chunk groups)**
* **TrustMetrics (hallucination detection, cross-engine confidence, consistency scores)**

Project C’s purpose:

1. **Fuse OCR from multiple engines** (Marker, DeepSeek-OCR, Tesseract, math OCR, handwriting OCR).
2. **Eliminate hallucinated text and remove parasitic or spurious regions**.
3. **Normalize structure**:

   * unify reading order
   * correct block segmentation
   * preserve hierarchy (titles → headers → paragraphs → tables → captions → footnotes)
4. **Create stable RAG chunk candidates** (NOT embeddings).
5. **Compute trust signals** so downstream systems know how reliable each chunk is.
6. **Identify text requiring human review**, if applicable.
7. **Output clean, logically grouped, RAG-ready text with metadata** to Project D.

Project C does **not** run OCR, layout detection, image quality assessment, or embeddings.

Its job is **cross-engine reconciliation, semantic correctness, structural consistency, and chunk-level trustworthiness.**

---

# 1. Introduction

## 1.1 Purpose

This document defines the functional and non-functional requirements for **Project C**, the post-OCR intelligence layer responsible for:

* cross-engine text fusion
* hallucination detection
* semantic segmentation
* page-level and document-level normalization
* creation of RAG-ready chunk sets
* generation of trust/confidence metadata

## 1.2 Scope

### In-Scope

Project C shall:

* Ingest outputs from A & B
* Merge and reconcile OCR results from multiple engines
* Detect and remove hallucinated or low-confidence text
* Normalize text, whitespace, casing, Unicode forms
* Reorder text according to structural and semantic cues
* Split text into **RAG-ready chunks** with block-level metadata
* Produce **chunk-level trust scores and quality indicators**
* Handle table and figure text normalization

### Out of Scope

Project C shall **not**:

* rerun IQA or page-image-level corrections (A)
* perform layout detection or reading-order prediction (B)
* embed text or write to vector DB (D)
* perform advanced semantic classification unrelated to RAG
* modify source images or re-render page content

---

# 2. Inputs & Outputs

## 2.1 Inputs

### Input A: DocumentMetadata (From Project A)

Key fields used:

* `pdf_type`
* `pre_ocr_risk`
* `pages[i].layout_summary`
* `pages[i].iqa_metrics`
* `ocr_routing_recommendation`

C uses this for:

* weighting confidence
* routing to fallback text strategies
* determining expected text quantity per page

### Input B: OCRDocument (From Project B)

Key fields:

* per-page `LayoutElement`s
* bounding boxes
* per-element `text`
* per-element `text_confidence`
* `reading_order`
* `element_type`
* table structures
* links (caption→figure, footnote→ref)

---

## 2.2 Outputs

### Output C1: NormalizedTextDocument

A structured representation including:

* unified reading-sequence text
* block-level metadata (section, title, header, footer, paragraph, list, caption, table cell)
* normalized whitespace, Unicode cleanup
* cross-engine fused text
* confidence scores per block

### Output C2: RAGChunkSet

Chunks contain:

* `chunk_id`
* `chunk_text`
* `chunk_type` (paragraph, list, table, caption, formula, footnote)
* `source_elements` (list of element_ids from B)
* `semantic_hints` (e.g., section title, heading chain)
* `tags` (e.g., contains_math, table_row, figure_caption)
* `trust_score` (0–1)
* `ocr_fusion_score`
* `hallucination_risk`
* `page_range`

### Output C3: TrustMetrics

A separate trust report:

* page-level risk indicators
* chunk-level OCR fusion confidence
* hallucination detection outputs
* semantic consistency warnings
* low-confidence blocks requiring review

---

# 3. Functional Requirements

---

# FR-C1: Multi-Engine OCR Fusion

Project C shall be able to combine OCR text from:

* Marker (Llama 4 Maverick)
* DeepSeek-OCR
* Tesseract or “fast OCR”
* math OCR engine
* handwriting OCR engine

Fusion occurs **per element**, not per page.

### FR-C1.1 Fusion Strategy

For each `LayoutElement`:

* compile texts from all available engines
* align sequences using word-level alignment (e.g., dynamic programming or WER alignment)
* select a fused output using:

  * highest confidence token
  * majority agreement
  * engine-specific confidence weights
  * contextual consistency
  * domain-specific rules (math/handwriting/table)

### FR-C1.2 Engine Weights

Default weights:

| Engine          | Domain Strength                           |
| --------------- | ----------------------------------------- |
| Marker          | General text, structure-aware             |
| DeepSeek-OCR    | images containing text, low-quality scans |
| Tesseract       | fallback, fast simple text                |
| math-ocr        | formulas                                  |
| handwriting-ocr | signatures & handwriting                  |

Weights are configurable.

### FR-C1.3 Conflict Resolution

If engines disagree significantly:

* log divergence
* compute `fusion_divergence_score`
* mark block as low-confidence
* optionally select the text from the engine better aligned with page type
* if still ambiguous: request fallback semantic cleanup (LLM-assisted post-processing if allowed)

---

# FR-C2: Hallucination Detection & Removal

Project C shall detect hallucinations arising from:

* LLM-based OCR engines (Marker/Llama-based)
* misinterpreted image textures
* watermark drift
* misread math formulas (“cosy” vs “cos y”)
* repeated lines not present in other engines

### FR-C2.1 Hallucination Detection Methods

1. **Cross-engine mismatch**

   * strong disagreement across engines → high hallucination risk

2. **Spatial mismatch**

   * predicted text bounding box is empty or mostly whitespace → likely hallucination

3. **Confidence coherence**

   * confidence high from LLM OCR, but baseline OCR shows no text → suspicious

4. **Visual density mismatch**

   * low pixel density but high textual richness → likely model hallucination

5. **Semantic anomaly detection**

   * repeated phrases
   * invented titles
   * invented “chapter” or “section” markers
   * unnatural language patterns not present elsewhere

### FR-C2.2 Removal

When hallucination is detected:

* remove text
* mark block as hallucinated
* log event
* create fallback placeholder: `"[[OCR_HALLUCINATION_REMOVED]]"` if needed

---

# FR-C3: Structural Normalization

### FR-C3.1 Reading Order Preservation

Project C shall honor the reading order from Project B but may:

* correct minor ordering errors
* merge split paragraphs
* reorder captions when B's reading order places them incorrectly
* ensure footnotes appear at correct locations in text stream

### FR-C3.2 Header/Footer Removal

Based on B’s `is_parasitic` flag:

Project C shall automatically remove:

* page headers
* page footers
* page numbers
* watermarks and stamps tagged as parasitic

Exceptions (configurable):

* legal documents requiring preservation
* financial statements where headers include material labels

### FR-C3.3 Table Normalization

For each table:

* extract cell texts
* unify row/column order into Markdown-like structure
* produce both:

  * a ***textual rendition*** (Markdown or TSV)
  * a ***structured representation*** for RAG chunking
* capture cell-level confidence and fusion disagreement

### FR-C3.4 Figures & Captions

C must:

* embed caption text immediately after the figure representation in logical order
* expose optional “figure summary text” (if LLM summarization is allowed in future version)

---

# FR-C4: Semantic Segmentation & Chunking

### FR-C4.1 Chunk Criteria

Chunks are made using:

* natural paragraph boundaries
* structural boundaries: titles, section headers
* table boundaries
* logical groupings (figure + caption)
* optional max token length

### FR-C4.2 Chunk Types

Valid chunk types:

* `paragraph`
* `section_header`
* `title`
* `list_block`
* `table_block`
* `figure_caption`
* `math_block`
* `footnote`

### FR-C4.3 Chunk Boundaries

C shall never:

* merge content from different layout types (e.g., list + table)
* combine paragraphs across section headers
* include parasitic text
* combine content across pages when the reading order indicates discontinuity

---

# FR-C5: Trust Scoring & Quality Metrics

Project C shall emit trust metrics including:

### FR-C5.1 OCR Fusion Confidence

* average token-level confidence
* divergence among engines
* agreement ratio

### FR-C5.2 Hallucination Risk

* binary flag (`high`, `medium`, `low`)
* driving factors (cross-engine mismatch, spatial mismatch, semantic anomaly)

### FR-C5.3 Structural Alignment Score

* consistency between B’s layout graph and the output chunk chain

### FR-C5.4 Document-Level Rollup

* number of suspicious blocks
* pages with >20% low-confidence text
* table recognition quality measure

---

# FR-C6: Normalization & Cleanup

### FR-C6.1 Unicode Normalization

Normalize text to NFKC or NFC.

### FR-C6.2 Whitespace & Newline Normalization

* collapse multi-spaces
* remove line break artifacts
* preserve paragraph boundaries

### FR-C6.3 Bullet/List Standardization

Convert all list types into:

* Markdown lists
* or a structured array representation

### FR-C6.4 Math Normalization

For formulas:

* remove OCR misinterpretations (e.g., l vs 1 vs |) using math-ocr priority
* unify LaTeX-like representations

---

# FR-C7: Errors, Fallbacks, and Degradation Modes

### FR-C7.1 Layout Failures

If Project B's layout is poor:

* use spatial clustering (simple stripe segmentation)
* fallback to page-level chunking
* flag low structural confidence

### FR-C7.2 Missing OCR

If OCR is missing entirely:

* insert placeholder text
* do not generate embeddings later (handled in D)
* mark high-risk pages

### FR-C7.3 Corrupt Blocks

If block-level fusion fails:

* fallback to highest-confidence engine
* log with `block_fusion_fallback=true`

---

# 4. Non-Functional Requirements (NFRs)

---

# NFR-C1: Accuracy & Quality Targets

### OCR Fusion Quality

* Weighted CER improvement ≥ **15%** vs baseline single-engine OCR
* Fusion disagreement rate ≤ **10%** in clean pages

### Hallucination Filtering

* ≥ **95%** detection of synthetic text introduced by LLM OCR
* ≤ **2%** false-positive removal of valid text

### Structural Consistency

* Section boundary accuracy ≥ **90%**
* Paragraph merge/split accuracy ≥ **92%**

### Chunk Quality

* ≤ **3%** chunks containing cross-page contamination
* ≤ **5%** chunks containing parasitic text

---

# NFR-C2: Performance

Assuming GPU-accelerated environment (Modal / HF Inference):

* Fusion + normalization per page: **≤ 50–150 ms**
* Chunk assembly for 100 pages: **≤ 1.5 seconds**
* Trust scoring per document: **≤ 300 ms**

---

# NFR-C3: Scalability

* Process up to **10,000 pages per hour** per worker
* Scale horizontally with no shared state

---

# NFR-C4: Observability

C must log:

* per-block fusion stats
* hallucination detection results
* chunk boundaries
* trust score distributions

Optionally generate:

* debug traces
* per-page HTML with visualization overlays

---

# NFR-C5: Security

* No LLM calls to external endpoints except approved OCR engines
* No PII in logs
* Document text stored only in ephemeral runtime unless configured otherwise

---

# 5. System Architecture Requirements

Project C comprises these modules:

1. **fusion_engine**
2. **hallucination_detector**
3. **structure_normalizer**
4. **chunk_builder**
5. **trust_engine**
6. **serializer**

Each must be modular and unit-testable.

---

# 6. Data & Training Requirements

## C6.1 Datasets for Fusion Evaluation

Use:

* DocLayNet
* OmniDocBench
* DocFin
* business/financial reports
* synthetic hallucination benchmarks (LLM-generated artifacts)

## C6.2 Benchmarks for Chunking

Use text segmentation datasets (Wiki-727K or custom RAG-oriented corpora).

---

# 7. Deployment Requirements

* C must be deployable as a containerized service behind a queue or API
* Accept batch and single-document modes
* Produce deterministic output for given inputs

---

# 8. Roadmap

### Phase C1 – Basic Fusion

* Combine Marker + “fast OCR”
* No hallucination filtering
* Basic normalization

### Phase C2 – Hallucination Filtering

* Introduce divergence-based detection
* LLM anomaly detection optional

### Phase C3 – Full Structural Normalization

* Tables, figures, captions, math, footnotes

### Phase C4 – RAG Chunking & Trust Scoring

* produce high-quality chunk sets
* expose trust scores to D

---

# 9. Acceptance Criteria

Project C is complete when:

* It can ingest any valid Project B output and always return a valid chunk set
* Chunk-level trust scores reflect actual OCR reliability
* Hallucinations are reliably detected and removed
* Structure is correct for at least 90% of complex documents
* RAG chunks do not contain contamination, duplication, hallucination, or parasitic text

---
