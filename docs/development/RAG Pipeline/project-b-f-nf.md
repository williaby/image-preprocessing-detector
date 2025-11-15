---
schema_type: common
title: "Project B Functional and Non-Functional Requirements"
description: "Requirements specification for Project B OCR orchestration and layout detection"
tags: [documentation, planning, architecture, ocr, layout_detection]
status: published
owner: "docs-team"
purpose: "Define all functional and non-functional requirements for Project B OCR orchestration and document layout analysis."
---

**Layout, OCR & Structural Extraction Engine**
**Version 1.0.0 – Draft**

## 1. Introduction

## 1.1 Purpose

This document defines the **functional and non-functional requirements** for **Project B**, which provides:

* **detailed document layout analysis**
* **reading order prediction**
* **specialized region detection** (tables, formulas, footnotes, watermarks, signatures, annotations)
* **per-region OCR** using one or more engines
* **structured logical document representation** feeding Project C

## 1.2 Scope

### In Scope

Project B shall:

* Ingest **DocumentMetadata** and page images produced by Project A.
* Perform **bounding-box layout detection** using a deep model (e.g. YOLOv8 trained on DocLayNet-like data).
* Predict **reading order** across complex, multi-column layouts.
* Detect and tag:

  * headers, footers, page numbers
  * tables & table structure
  * figures & captions
  * footnotes & references
  * formulas / math
  * watermarks, stamps, signatures, margin annotations
* Invoke appropriate **OCR engines** per region:

  * base engine (Marker + Llama 4 Maverick)
  * specialized engines for math, handwriting, complex layouts, or degraded regions
* Produce **OCRDocument JSON** with:

  * hierarchy (document → pages → blocks → spans)
  * bboxes, types, reading order
  * per-block text and confidence
  * minimal, stable identifiers for downstream linking

### Out of Scope

Project B does **not**:

* perform IQA or pixel-space correction beyond minimal pre-processing required by the OCR engines
* recalculate DQS or pre_ocr_risk
* perform fusion across multiple OCR outputs (that’s C)
* filter hallucinations or compute semantic trust scores (C)
* create RAG-ready chunk sets or embeddings (C/D)

## 3. Functional Requirements

## FR-B1: Layout Detection

### FR-B1.1 Layout Model

Project B shall use a **deep object detection model** trained on a DocLayNet-like dataset to detect document elements with bounding boxes.

* Model class: YOLOv8 or comparable one-stage detector
* Input: page image (RGB or grayscale)
* Output: bounding boxes, class labels, confidence scores
* Model must be configurable (path from environment or config file).

### FR-B1.2 Layout Classes

At minimum, B must detect the following element types per page:

1. Title
2. Section-Header
3. Text (body paragraphs)
4. List-Item
5. Table (block-level)
6. Picture/Figure
7. Formula (equations)
8. Caption
9. Page-Header
10. Page-Footer
11. Page-Number

Optional but recommended (for richer structure):

* Marginalia / margin-note
* Sidebars / callout boxes

All detections must be stored as `LayoutElement` entries with:

* `element_type` from the above set
* `bbox_coco`
* `detector_confidence`

### FR-B1.3 Post-Processing & Normalization

The system shall:

* merge overlapping boxes of the same class when appropriate
* eliminate low-confidence detections using configurable thresholds
* normalize coordinates into consistent pixel coordinate space
* snap bounding boxes slightly inward to avoid including adjacent text columns when possible

## FR-B3: Reading Order Prediction

### FR-B3.1 Element Graph Construction

Project B shall construct a **spatial graph** of layout elements for each page:

* nodes: `LayoutElement` instances
* edges: adjacency relationships (above/below, left/right, overlap)
* features:

  * bounding box geometry
  * element type
  * page column grouping

### FR-B3.2 Per-page Reading Order

Using the element graph, B shall:

* produce a **per-page ordered sequence** of `element_id` representing reading order
* respect:

  * multi-column layouts
  * title → section header → body progression
  * table/caption placement
  * figure/caption placement
  * footnotes after main text

### FR-B3.3 Cross-page Coherence

Project B shall maintain:

* proper ordering across pages, appending page blocks in a way that allows Project C to reconstruct document-wide logical sequence without guessing.

### FR-B3.4 Confidence & Error Signaling

For each page:

* compute `reading_order_confidence ∈ [0, 1]` based on rule heuristics or optional learned model
* expose this to Project C so that low-confidence layouts can be chunked via spatial fallback rather than semantic sequence.

## FR-B5: Specialized Region Detection

Project B shall detect and tag:

### FR-B5.1 Math / Formula Regions

* Regions with mathematical notation that should be routed to a specialized math OCR engine (Project C may still handle the actual parsing; B must segment and call the right OCR engine where required).

### FR-B5.2 Watermarks

* Semi-transparent text or logos that overlap main text
* They shall be flagged as `element_type == "watermark"` and `attributes.is_parasitic = true`.

### FR-B5.3 Stamps & Seals

* Circular or irregular graphic stamps that may occlude text
* Tagged as `element_type == "stamp"`.

### FR-B5.4 Signatures

* Handwritten signature regions typically located at page bottom or signatory areas
* Tagged as `element_type == "signature"`.

### FR-B5.5 Margin Notes / Annotations

* Handwritten or printed notes in margins
* Tagged as `element_type == "margin_note"`
* Should **not** be treated as part of main reading order by default, but links may be created.

## FR-B7: Logical Structure Assembly

### FR-B7.1 Page-level Text Blocks

For `element_type == "text"` or `list_item` etc., B must:

* combine OCR results for fragmented bounding boxes that truly belong to the same logical paragraph (e.g., due to line-level detection)
* maintain text + bbox per logical block
* preserve reading order sequence.

### FR-B7.2 Document-level Structure

Project B shall create a **shallow logical hierarchy**:

* titles
* section headers
* body blocks
* tables & captions
* footnotes

Represented via:

* parent/child relationships in `LayoutElement` (e.g., `parent_id`)
* stable `element_id` mapping so Project C can build deeper semantics without re-resolving page structure.

### FR-B7.3 No Chunking Responsibility

Project B shall **not** attempt to:

* decide RAG chunk sizes
* merge blocks into semantic units beyond paragraphs and simple logical groupings

It only needs to output units and their structural relationships clearly enough for Project C to build RAG chunks and fusion.

## 4. Non-Functional Requirements (NFRs)

## NFR-B1: Performance

Assuming Modal GPU workers:

* **Layout detection latency**:

  * Target: ≤ 100 ms per page on mid-range GPU
  * Acceptable: ≤ 300 ms per page

* **OCR latency (base engine) per page, average complexity**:

  * Target: ≤ 300 ms
  * Acceptable: ≤ 800 ms

* **Throughput per worker** (layout + OCR):

  * Target: ≥ 3–5 pages/second sustained
  * Scaling: linear with workers

Project B must support:

* batch processing mode (for many pages)
* streaming mode (page-by-page) for time-sensitive flows

## NFR-B2: Accuracy Targets

These are *B’s* KPIs; C/D may care about derived RAG metrics, but B owns these.

### NFR-B2.1 Layout Detection

* mAP@0.50 (DocLayNet-style classes): ≥ 0.82 (target)
* mAP@0.50–0.95: ≥ 0.70 (target)
* Per-class AP for text/table/figure/caption: ≥ 0.75

### NFR-B2.2 Reading Order

Measured on reading-order datasets (e.g., DocSynth/ROOR):

* Pairwise F1 for correct ordering: ≥ 0.85
* Kendall’s tau (order correlation): ≥ 0.80

### NFR-B2.3 Table Structure

* Table structure similarity (TEDS or GriTS):

  * Target: ≥ 0.90 on evaluation set of realistic tables

### NFR-B2.4 OCR Quality

Compared to baseline single-engine OCR on a standardized benchmark:

* Word Error Rate (WER) improvement of ≥ 10% relative
* Character Error Rate (CER) improvement of ≥ 10% relative
* For low-quality pages flagged high-risk by Project A, B’s routing must demonstrate significant benefit over naive “same engine everywhere” baseline.

## NFR-B3: Robustness & Fallback

* If layout detection fails, B must degrade to:

  * simple page segmentation (rough horizontal stripe/column segmentation)
  * full-page OCR with minimal structural info
  * signal `layout_confidence` low so C knows to fall back to robust chunking strategies.

* If a specialized OCR engine is not available:

  * log clearly
  * fall back to a default OCR engine
  * mark `ocr_engine_fallback = true` in attributes.

## NFR-B4: Logging & Observability

* Log per-page:

  * layout model used & version
  * OCR engine(s) used per region
  * key latency breakdowns (layout vs OCR vs structure assembly)
* Provide optional “debug overlay” images:

  * bounding boxes + labels + reading order indices (for offline QA)

## NFR-B5: Security & Privacy

* No external calls other than to explicitly configured OCR/model services (e.g., Modal endpoints under your control).
* No page images or text snippets logged at INFO level; only hashed or redacted IDs in production.
* Debug overlays must be explicitly enabled and kept out of default logs and metrics.

## 6. Data & Training Requirements

## 6.1 Layout Model Training

* Train or fine-tune on a dataset that covers:

  * scientific articles
  * business reports
  * financial statements
  * forms
  * technical manuals

* Include multiple domains to generalize across typical RAG sources (technical, legal, financial, academic).

## 6.2 Reading Order

* Use synthetic + real datasets for reading order, including:

  * multi-column pages
  * complex layouts with tables and figures
  * pages with heavy footnoting

Models or heuristics must generalize across languages and moderate variations in typography.

## 6.3 Specialized Regions

* For math, stamps, signatures, etc., B may use:

  * dedicated detectors (CNNs)
  * transfer learning from general object detection where realistic datasets exist

Training details live elsewhere; requirement is that model swapping and domain extension are possible with minimal code change.

## 8. Phase Roadmap (Project B Only)

### Phase B1 – Layout & Basic OCR

* Integrate layout model with DocLayNet-style classes
* Per-page layout detection
* Per-region OCR using base engine (Marker + Llama 4 Maverick)
* Simple reading order (column-aware)

### Phase B2 – Parasitic Content & Advanced Reading Order

* Header/footer/page-number detection across pages
* Parasitic flags in elements
* Improved reading order with graph-based logic
* Reading order confidence scoring

### Phase B3 – Tables & Structured Regions

* Table structure recognition
* Figure–caption linking
* Footnote linking
* Initial math/watermark/signature/margin-note detection

### Phase B4 – Routing, Optimization & Hardening

* Engine routing logic (simple rules tied to Project A metadata)
* Performance tuning & batching
* Robust fallback modes
* Observability, logs, debug overlays
