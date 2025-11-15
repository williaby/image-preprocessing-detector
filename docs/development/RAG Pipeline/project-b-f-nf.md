# Project B Requirements Specification

**Layout, OCR & Structural Extraction Engine**
**Version 1.0.0 – Draft**

---

## 0. Executive Summary

**Project B** is the **layout & OCR engine** in a four-project architecture:

* **Project A**: pre-OCR IQA + corrections + routing
* **Project B**: **detailed layout, OCR, and logical structure extraction**
* **Project C**: multi-engine fusion, confidence modeling, hallucination filtering, RAG-ready text units
* **Project D**: embedding + vector database ingestion + RAG plumbing

Project B’s job is to:

1. Take **cleaned images & DocumentMetadata** from Project A.
2. Run **detailed layout detection** and build a **document element graph**: text blocks, tables, figures, headers, footers, formulas, etc.
3. Predict **reading order** that respects multi-column layouts, tables, captions, footnotes.
4. Run the **right OCR engine(s)** per region:

   * base OCR via Marker (with Llama 4 Maverick)
   * specialized OCR for math, handwriting, low-quality pages, etc.
5. Produce a **structured OCRDocument** with:

   * per-element text
   * bounding boxes
   * reading sequence
   * region-level metadata and OCR confidence

Project B **does not**:

* do IQA or pixel-space corrections (that’s A)
* compute DQS or pre-OCR risk (A)
* decide final RAG chunks or embeddings (C/D)
* decide semantic trust / hallucination filtering (C)

It’s “just” the thing that understands the page as a set of objects and reads them. “Just,” in the sense that this is the part that actually hurts.

---

# 1. Introduction

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

---

# 2. Interfaces & Data Contracts

## 2.1 Inputs from Project A

Project B consumes:

1. **Page Images**

   * Rasterized pages at ≥ 300 DPI
   * Formats: PNG or JPEG (lossless or high-quality lossy)
   * One image per logical page

2. **DocumentMetadata v1.0.0**
   Key fields used by B include:

   * `document_id: str`
   * `page_count: int`
   * `pages[i].has_text: bool`
   * `pages[i].iqa_metrics` (skew, blur, DPI, etc.)
   * `pages[i].layout_summary` (single/multi/complex, has_tables, has_figures, has_dense_math, has_handwriting, etc.)
   * `pdf_type: Literal["image_only","born_digital","hybrid"]`
   * `pre_ocr_risk: float`
   * `ocr_routing_recommendation: Literal["ocr_fast","ocr_advanced","vision_simple","vision_structured"]`

Project B must treat Project A’s metadata as **advisory but authoritative** for IQA: it should not attempt to redo quality scoring.

## 2.2 Outputs to Project C

Project B shall output a structured **OCRDocument** object (JSON or msgpack) with at least:

* `document_id: str`
* `source_document_metadata_version: str` (e.g. A schema version)
* `pages: List[PageOCR]`

Where each `PageOCR` includes:

* `page_index: int`
* `width_px: int` / `height_px: int`
* `elements: List[LayoutElement]`
* `reading_order: List[str]` (ordered list of `element_id`)

Each `LayoutElement` includes:

* `element_id: str` (stable within document)
* `element_type: "text" | "table" | "figure" | "caption" | "page_header" | "page_footer" | "page_number" | "formula" | "footnote" | "signature" | "stamp" | "watermark" | "margin_note" | ...`
* `bbox_coco: [x, y, width, height]` (page pixel coordinates)
* `page_index: int`
* `ocr_engine: str` (e.g. `"marker_llama4"`, `"deepseek_ocr"`, `"math_ocr"`, `"handwriting_ocr"`, `"tesseract"`…)
* `text: Optional[str]` (for OCR’d regions)
* `text_confidence: Optional[float]` (0–1)
* `attributes: Dict[str, Any]` (e.g. `{"is_header_footer": true, "is_parasitic": true}`)
* `links: Optional[List[ElementLink]]` (e.g. caption ↔ figure; footnote ↔ ref)

For tables, an additional `table_structure` sub-object is required (see FR-B4.3).

---

# 3. Functional Requirements

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

---

## FR-B2: Parasitic Content & Page Role Detection

### FR-B2.1 Header/Footer Detection

Using layout detections, the system shall:

* identify repeating **Page-Header** and **Page-Footer** patterns across pages
* mark them as `attributes.is_parasitic = true`
* identify and mark **page numbers** similarly

### FR-B2.2 Semantic Noise Support for RAG (B-side responsibilities)

Even though Project B does not do chunking, it must:

* clearly flag parasitic elements so Project C can exclude them from semantic chunk sets by default
* ensure that header/footer/page number text are available separately if needed (e.g. for citations) but never mixed with main body paragraphs in `reading_order`.

---

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

---

## FR-B4: Tables, Figures, and Structured Regions

### FR-B4.1 Table Detection (Block-level)

Block-level table detection is already covered by layout model (FR-B1).

Each `element_type == "table"` must store:

* bounding box
* page index
* detector confidence

### FR-B4.2 Table Structure Extraction

Project B shall perform **table structure recognition** inside each table region:

* detect grid of rows and columns
* detect spanning cells
* differentiate header rows from body rows

The result shall be stored in `table_structure`, including:

* `num_rows`, `num_cols`
* `cells: List[{row, col, row_span, col_span, bbox_coco, is_header}]`

### FR-B4.3 Figure–Caption Linking

Project B shall:

* associate **Caption** elements with their **Picture/Figure** elements via `links`
* use spatial proximity and pattern matching (e.g. “Figure 3”, “Fig. 3”).

### FR-B4.4 Footnote Linking

Project B shall:

* detect footnote references inside main text spans (superscript numbers etc.)
* link those references to Footnote elements using `links` (e.g. `{"type": "footnote_ref", "target_id": "footnote_007"}`).

---

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

---

## FR-B6: OCR Engine Orchestration

### FR-B6.1 Engine Registry

Project B shall maintain a configurable registry of OCR engines, e.g.:

* `"marker_llama4"` – base OCR / layout-aware engine
* `"deepseek_ocr"` – fallback / complex figure-heavy / low-quality pages
* `"math_ocr"` – math formula OCR engine
* `"handwriting_ocr"` – handwriting / signature engine
* `"fast_ocr"` – simple engine (e.g. Tesseract) for fast paths

### FR-B6.2 Routing Strategy (Per Page & Per Region)

Using:

* `ocr_routing_recommendation` from Project A
* page-level attributes (has_tables, has_figures, has_dense_math, has_handwriting)
* element types (text, formula, table, figure, caption, signature, etc.)

Project B shall:

* choose a **primary OCR engine** for each region
* optionally route specific regions to specialized engines:

  * formula regions → `"math_ocr"`
  * handwriting / signatures → `"handwriting_ocr"`
  * complex pictures → `"deepseek_ocr"` (for text in images)

### FR-B6.3 OCR Outputs

For each `LayoutElement` that contains readable text, B must:

* call the chosen OCR engine
* store:

  * `text: str` (UTF-8)
  * `text_confidence: float` (normalized, engine-specific mapping allowed)
  * `ocr_engine: str`

If OCR fails or is skipped:

* `text = null` or empty
* `text_confidence = 0.0`
* `attributes.ocr_status = "skipped" | "failed"`

### FR-B6.4 Minimal Pre-processing Responsibilities

Project A owns IQA corrections; Project B is only allowed to:

* scale/crop/normalize images to meet OCR engine’s input size requirements
* convert color space (RGB ↔ grayscale)
* apply very light binarization or thresholding where required by specific engines

These must be deterministic and recorded as a thin transform layer (e.g. `ocr_preprocessing_steps`) in the element attributes.

---

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

---

## FR-B8: Configurability & Model Swapping

Project B must allow:

* switching layout detection models via config (e.g., DocLayNet v1 vs v2)
* switching OCR engines or endpoint URIs via config
* enabling/disabling specialized detectors (math, watermark, signature, etc.) individually
* specifying thresholds (confidence cutoffs, NMS thresholds, etc.) externally, not hard-coded.

---

# 4. Non-Functional Requirements (NFRs)

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

---

# 5. System Architecture Requirements

## 5.1 High-level Pipeline

For each document:

1. **Ingest** DocumentMetadata + page images from A.
2. For each page:

   * Run **layout detection**.
   * Detect parasitic content (headers/footers/page numbers).
   * Build **element graph**.
   * Predict **reading order**.
   * Detect special regions (math, watermarks, stamps, signatures, margin notes).
   * For each region:

     * Choose OCR engine via routing logic.
     * Run OCR and capture text + confidence.
3. Assemble **logical structure** across pages.
4. Emit **OCRDocument** structure for Project C.

## 5.2 Modular Components

Core modules (preferably separable packages):

* `layout_detector`
* `parasitic_detector`
* `reading_order`
* `special_regions`
* `ocr_router`
* `ocr_client` (engine-agnostic)
* `structure_builder`
* `serializer` (to OCRDocument schema)

Each must be swappable without altering upstream/downstream contracts.

---

# 6. Data & Training Requirements

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

---

# 7. Deployment & Operations

## 7.1 Containerization

Project B shall be deployed as:

* container image with:

  * layout model weights
  * OCR client configuration
* environment variables or config files to:

  * point to Modal/OCR services
  * select models
  * set thresholds

## 7.2 Horizontal Scaling

* Multiple instances should be able to process documents independently.
* No shared mutable state; all coordination via queues / job system if needed.
* Project B should accept a list of pages and return structured results without needing global external state.

---

# 8. Phase Roadmap (Project B Only)

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

---

# 9. Acceptance Criteria

Project B is considered ready for integration with C when:

* It can process representative corpora (technical reports, academic papers, financial documents, contracts) from Project A output without manual intervention.
* Layout, reading order, and table structure metrics meet or exceed NFR-B2 targets.
* OCR quality demonstrates measurable improvement over a naive “run single OCR on whole page” baseline on evaluation sets.
* OCRDocument output is stable, schema-validated, and consumed cleanly by an integration harness simulating Project C.

---
