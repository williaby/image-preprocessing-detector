---
schema_type: common
title: "Functional Requirements v2.0"
description: "Detailed functional and non-functional requirements for the Image Preprocessing Detector system"
tags: [requirements, specifications, functional, non-functional, documentation]
status: published
owner: "docs-team"
review_cycle_days: 90
authors:
  - name: "Byron Williams"
purpose: "Specify detailed requirements for document preprocessing, quality assessment, and intelligent routing."
---

> **Version:** 2.2
> **Date:** 2025-01-13 (Updated with OHR-Bench and Reading Order elevation)
> **Status:** Active
> **Supersedes:** PRs #14-15 functional_requirements.md, v2.0 (2025-11-11)
> **Aligned with:** PROJECT_PLAN Phase 1-5, ADRs 0001-0032
> **Changes**: Added FR-2.3 (Learned Quality Assessment), FR-4.8 (Handwriting Detection), FR-4.11 (Table Structure Extraction), FR-4.12 (Reading Order Prediction - **CRITICAL** for RAG)

---

## 1.0 Introduction

### 1.1 Purpose

This document specifies the detailed functional and non-functional requirements for the **Image Preprocessing Detector**. This tool is a pre-processing validation and correction system designed to analyze and classify all incoming documents. Its purpose is to detect a range of quality, format, and content issues; perform foundational image corrections; and output structured JSON metadata. This JSON file will be used to route each document to the correct, specialized processing workflow.

### 1.2 Scope

**In-Scope:**
- Accept single document file (path or byte stream)
- Analyze file to identify properties and quality issues
- Run CV-based and ML-based detectors
- Perform foundational image corrections (deskew, upscale, denoise, CLAHE)
- Output structured JSON metadata file
- Calculate Document Quality Score (DQS) for intelligent routing (Phase 4)
- Preprocess embedded images in office documents (Phase 5)

**Out-of-Scope:**
- Full-page OCR or text extraction (beyond classification needs)
- Downstream parsing logic (table-to-JSON, semantic chunking, vectorization)
- PDF Portfolio files (deprecated format)
- Full office document parsing (delegated to Docling)

### 1.3 Audience

This document is intended for:
- Development team
- QA/Test engineers
- Project management
- Integration partners (Docling, LayoutParser, OCR engines)

---

## 2.0 Functional Requirements (FR)

### FR-1: General System & File Handling

#### FR-1.1: File Input
The system shall accept a single file input via:
- File path (absolute or relative)
- Byte stream (in-memory processing)

#### FR-1.2: Supported File Formats

**Phase 1-4 (Current Scope):**
- **Images**: .jpg, .jpeg, .png, .tiff, .bmp
- **PDFs**: .pdf (all types: image-only, born-digital, hybrid)

**Phase 5 (Office Format Preprocessing):**
- **Office**: .doc, .docx, .xls, .xlsx, .pptx
- **Scope**: Preprocess embedded images only (not full document parsing)
- **Integration**: Extract images → preprocess → pass to Docling
- **Rationale**: Office formats contain embedded images that benefit from preprocessing (DPI upscaling, deskewing, denoising). Full document parsing delegated to Docling.

**Out-of-Scope:**
- **PDF Portfolios**: Deprecated by Adobe, rarely encountered
- **Other**: .odt, .rtf, .epub (no current demand)

#### FR-1.3: JSON Output
The system shall output a single, structured JSON metadata file that conforms to the **Pydantic v2 Schema Definition** (see `src/image_preprocessing_detector/schema.py`).

**Schema:** `DocumentMetadata` model with fields:
- `file_path`: str
- `document_type`: Literal["image", "pdf", "office_word", "office_excel"]
- `pages`: List[PageMetadata]
- `quality_score`: Optional[DocumentQualityScore] (Phase 4)
- `pdf_type`: Optional[Literal["image_only", "born_digital", "hybrid"]] (Phase 2)
- `languages`: Optional[List[str]] (Phase 2)
- `upscaling`: Optional[Dict] (Phase 1B - completed)

#### FR-1.4: Error Handling
The system shall gracefully handle and log errors for:
- Unsupported file formats → Return error JSON with message
- Corrupted files that cannot be opened → Return error JSON
- Password-protected or encrypted files → Return error JSON
- PDF Portfolio files → Return error: "PDF Portfolio format not supported"

---

### FR-2: File Format Analysis

#### FR-2.1: PDF Type Classification (Phase 2)

The system shall analyze all `.pdf` files and classify the file type as one of:

- **"image_only"**: Contains no extractable digital text (i.e., a scanned document)
- **"born_digital"**: Contains extractable digital text and no significant image-based content
- **"hybrid"**: Contains both extractable digital text and significant embedded images that also contain text

**Method:** Use PyMuPDF text extraction attempt
- If zero text objects → "image_only"
- If text objects AND embedded images → "hybrid"
- If text objects AND no embedded images → "born_digital"

**Output:** Add `pdf_type` field to `DocumentMetadata`

**Rationale:** Critical for routing decisions (OCR vs. text extraction vs. visual reconciliation)

**Implementation:** Phase 2 (Week 8-9)

#### FR-2.2: Office Format Detection (Phase 5)

The system shall identify office document types:
- `.doc`/`.docx` → Flag `document_type` as "office_word"
- `.xls`/`.xlsx` → Flag `document_type` as "office_excel"
- `.ppt`/`.pptx` → Flag `document_type` as "office_powerpoint"

**Scope:** Extract embedded images for preprocessing only

#### FR-2.3: Learned Quality Assessment (Phase 2+)

The system shall perform **document-specific quality assessment** using a learned (ML-based) model trained on document quality datasets to complement classical IQA methods.

**3-Dimension Output** (aligns with DIQA-5000 benchmark):
1. **Overall Quality Score** (0.0 - 1.0): Holistic document quality assessment
2. **Sharpness Score** (0.0 - 1.0): Edge definition and blur assessment (complements FR-3.1)
3. **Color Fidelity Score** (0.0 - 1.0): Contrast, brightness, and color balance assessment (complements FR-3.7)

**Training Data:**
- **Phase 2**: 50k synthetic samples from TableBank with weak supervision (BRISQUE/NIQE labels)
- **Phase 3**: Augmented with DIQA-5000 (5,000 document images with ground-truth 3-dimension scores when released)
- **Fallback**: LIVE/CSIQ natural image IQA datasets (validation only until DIQA-5000 releases)

**Model Architecture:**
- **Phase 2**: MobileNetV3-Small or EfficientNet-B0 (multi-label classification)
- **Phase 3+**: Fine-tuned on DIQA-5000 for document-specific characteristics

**Method:**
- **Ensemble Approach**: Combine classical IQA (FR-3.x) with learned quality assessment
- **Classical**: Fast heuristics (Laplacian variance, histogram analysis) - always runs
- **Learned**: ML model inference (ONNX Runtime, INT8 quantized) - runs on flagged documents or all documents (configurable)

**Output:**
- Add `learned_quality` field to `PageMetadata` with 3-dimension scores
- Integration with Document Quality Score (DQS) calculation (FR-5.1)

**Validation:**
- **Phase 2**: Pearson/Spearman correlation > 0.75 with LIVE/CSIQ ground-truth scores
- **Phase 3**: Pearson/Spearman correlation > 0.80 with DIQA-5000 ground-truth scores
- **Calibration**: DGQA (Domain-Generalized Quality Assessment) framework to address synthetic-to-real gap (ADR-011 update)

**Performance Targets:**
- **Latency**: < 50ms per page (GPU), < 200ms per page (CPU with ONNX INT8)
- **Accuracy**: mAP > 0.88 on multi-label quality classification
- **Calibration**: Expected Calibration Error (ECE) < 0.1

**Rationale:**
- Classical IQA methods (FR-3.1 - FR-3.12) are fast but limited to hand-crafted features
- Document-specific quality assessment requires learned models trained on document characteristics
- DIQA-5000 provides document-tailored benchmarks vs. LIVE/CSIQ natural images
- 3-dimension output enables fine-grained quality analysis for routing decisions

**Reference:**
- ADR-0014: Classical-ML Hybrid IQA (ensemble approach)
- ADR-0011: Hybrid Validation Strategy (synthetic + real-world calibration)
- ADR-0029: Dataset Selection Strategy (DIQA-5000 integration)
- Research: DocIQ/DIQA-5000 (arXiv:2509.17012, Sept 2025)

**Implementation:** Phase 2 Week 2-4 (training), Phase 3+ (DIQA-5000 integration when released)

---

### FR-3: Image Quality Detection & Correction (Per-page)

For all image files and for each page of an "image_only" or "hybrid" PDF:

#### FR-3.1: Blur Detection

The system shall calculate a quantitative **blur_score** based on the variance of the Laplacian.

**Method:** `cv2.Laplacian()` variance
- High variance = sharp image
- Low variance = blurry image

**Output:** Report score in JSON (0.0 - 1.0 normalized)

**Reference:** ADR-0014 (Classical ML Hybrid IQA)

#### FR-3.2: Skew Detection and Correction

The system shall detect the document's **skew_angle** in degrees using `cv2.minAreaRect()` on the content block.

**Detection:**
- Use `cv2.minAreaRect()` on thresholded image
- Report original detected angle in JSON

**Correction (with Do-No-Harm Guardrails):**
- **Threshold 1**: Only correct if |angle| > 2.0 degrees (configurable)
- **Threshold 2**: Apply correction and measure variance improvement
- **Threshold 3**: Only keep correction if variance improves by > 5%
- **Fallback**: If correction degrades quality, use original image

**Configuration:**
- `skew_angle_threshold`: Default 2.0° (range: 0.5° - 5.0°)
- `variance_improvement_threshold`: Default 5% (range: 1% - 10%)
- `enable_deskew_guardrails`: Default true

**Rationale:** Prevents over-correction on already-clean documents

**Reference:** ADR-0021 (Do-No-Harm Guardrails)

#### FR-3.3: Noise Detection

The system shall calculate a heuristic **noise_score** to identify potential issues like heavy stains, ink bleed-through, or "salt-and-pepper" noise.

**Method:** Connected component analysis
- Count of very small components (< 10 pixels) → salt-and-pepper noise
- Count of very large non-text components → stains/smudges

**Output:** Report score in JSON (0.0 - 1.0 normalized)

#### FR-3.4: Image Resolution

The system shall report the image resolution:
- **Width × Height** in pixels
- **DPI** (dots per inch) from metadata or calculated

#### FR-3.5: DPI Detection (Phase 1B - Completed)

The system shall attempt to read the image's DPI from its metadata:
- PDF: PyMuPDF `page.get_images()` image info
- JPG/PNG: EXIF tags or PIL metadata

#### FR-3.6: DPI Upscaling (Phase 1B - Completed)

If the detected DPI is below a configurable threshold (default: 300 DPI) or metadata is unavailable, the system shall upsample the image.

**Upscaling Configuration:**
- **Target DPI**: 300 (configurable)
- **Algorithm Options**:
  1. `lanczos` - Best quality (recommended for production)
  2. `bicubic` - Balanced speed/quality (development)
  3. `inter_linear` - Fastest (performance-critical)
  4. `inter_cubic` - Alternative high-quality
  5. `inter_area` - Downsampling (for oversized images)

**Output:**
- Report original DPI in JSON
- Report whether upsampling was applied
- Track upscaling metadata (algorithm, processing time, file sizes)

**Reference:**
- Phase 1B Implementation Summary
- ADR-0010 (300 DPI Normalization)

#### FR-3.7: Contrast Assessment

The system shall calculate a **contrast_score** using histogram analysis:
- Bimodal histogram = good contrast
- Single-peak histogram = low contrast

**Output:** Report score in JSON (0.0 - 1.0 normalized)

#### FR-3.8: Binarization Quality Assessment (Phase 2)

The system shall assess binarization quality to detect poor text/background separation.

**Detection Method:**
- Threshold analysis (Otsu, Sauvola, Niblack)
- Bimodal histogram validation
- Local variance analysis

**Output:** Report binarization quality score in JSON (0.0 - 1.0 normalized)

**Rationale:** Poor binarization causes complete OCR failure, especially on historical or degraded documents.

**Priority:** P0 (Critical)

**Reference:** Research: "Degraded Historical Document Binarization: A Review" (PMC 2021)

#### FR-3.9: Illumination Uniformity Detection (Phase 2)

The system shall detect uneven illumination (shadows, lighting gradients).

**Detection Method:**
- Local variance analysis across image regions
- Shadow detection algorithms
- Histogram analysis per quadrant

**Output:** Report illumination uniformity score in JSON (0.0 - 1.0 normalized)

**Rationale:** Uneven illumination causes OCR failures in shadowed regions.

**Priority:** P0 (Critical)

**Reference:** Research: "Robust Document Image Binarization Technique for Degraded Document Images" (IEEE 2013)

#### FR-3.10: Bleed-Through Detection (Phase 3)

The system shall detect bleed-through (ink from opposite side of page visible).

**Detection Method:**
- Dual-side image comparison (if available)
- Frequency domain analysis (single-side fallback)
- Color channel separation

**Output:** Report bleed-through severity in JSON (0.0 - 1.0 normalized)

**Rationale:** Bleed-through confuses OCR, treating reverse-side text as noise or false characters.

**Priority:** P1 (High)

**Reference:** Research: "Reduction of bleed-through in scanned manuscript documents" (Pattern Recognition 2011)

#### FR-3.11: Warping/Curvature Detection (Phase 3)

The system shall detect document warping and curvature (e.g., book spine curvature).

**Detection Method:**
- Line straightness analysis
- Curve fitting algorithms
- Hough transform for curved lines

**Output:** Report warping severity in JSON (0.0 - 1.0 normalized)

**Rationale:** Curved text lines cause OCR failures, especially on book scans and mobile captures.

**Priority:** P1 (High)

**Reference:** Research: "Straightening warped text lines using polynomial regression" (DAS 2016)

#### FR-3.12: Perspective Distortion Detection (Phase 2)

The system shall detect perspective distortion (trapezoidal shape from camera angle).

**Detection Method:**
- Corner detection
- Parallel line analysis (should be parallel but aren't)
- Homography estimation

**Output:** Report perspective distortion score in JSON (0.0 - 1.0 normalized)

**Rationale:** Mobile captures often have perspective distortion affecting OCR accuracy.

**Priority:** P2 (Medium)

**Reference:** Research: "Automatic Document Image Rectification Using Geometric Features" (ICDAR 2017)

---

### FR-4: Layout Analysis (Per-page)

#### FR-4.1: Layout Detection Model

The system shall use a **deep learning object detection model** trained on the DocLayNet dataset.

**Model:** YOLOv8 (Phase 3) or classical heuristics (Phase 1)

**Reference:** ADR-0015 (YOLOv8 Layout Detection)

#### FR-4.2: Layout Element Detection

The system shall detect and provide bounding boxes for the following layout classes:

**DocLayNet Classes (11):**
1. **Caption** - Descriptive text for figures/tables
2. **Footnote** - Notes at page bottom
3. **Formula** - Mathematical equations
4. **List-Item** - Bulleted/numbered list items
5. **Page-Footer** - Repeating footer content
6. **Page-Header** - Repeating header content
7. **Picture** - Figures, charts, diagrams
8. **Section-Header** - Section titles
9. **Table** - Structured data in rows/columns
10. **Text** - Main body paragraphs
11. **Title** - Document title

**Extended Classes (Phase 3):**
12. **Handwriting** - Handwritten text regions (requires separate classifier)
13. **Revision-Marking** - Strikethrough, insertions, margin notes (optional, Yale manuscripts)

**Derived Metadata:**
- **Multi-column detection**: Automatic from spatial analysis of Text blocks
- **Reading order**: Automatic from top-to-bottom, left-to-right sort
- **Parasitic content**: Flagged if class is Page-Header or Page-Footer

**Reference:** ADR-0008 (Multi-Stage Pipeline Architecture)

#### FR-4.3: Bounding Box Format

**CRITICAL**: Bounding boxes shall use **COCO format**: `[x, y, width, height]`

**Where:**
- `x`: X-coordinate of top-left corner (pixels from left edge)
- `y`: Y-coordinate of top-left corner (pixels from top edge)
- `width`: Width of bounding box (pixels)
- `height`: Height of bounding box (pixels)

**Rationale:**
- Industry-standard COCO format ensures compatibility with LayoutParser
- Consistent with DocLayNet dataset format

**Example:**
```json
{
  "class_label": "Table",
  "bounding_box": [120, 340, 450, 200],
  "confidence": 0.94
}
```

**Reference:** ADR-0009 (COCO Bounding Box Format Standardization)

**Note:** This supersedes PRs #14-15 which incorrectly specified `[x1, y1, x2, y2]` format.

#### FR-4.4: Parasitic Content Detection (Phase 3)

The system shall detect parasitic content (headers, footers, watermarks) that should not be included in RAG chunks.

**Detection Method:**
- Pattern matching across pages (repeated headers/footers)
- Spatial analysis (consistently at page top/bottom)
- Use Page-Header and Page-Footer classes from FR-4.2

**Output:** Mark regions as `parasitic: true` in JSON

**Rationale:** Headers/footers pollute RAG chunks with irrelevant content, degrading retrieval quality.

**Priority:** P0 (Critical for RAG applications)

**Document Types:** Academic papers, reports, legal documents, textbooks

**RAG-Specific Validation (OHR-Bench Integration):**

The system shall validate parasitic content detection and overall document quality using **OHR-Bench** RAG-specific metrics:

**Validation Metrics:**
1. **NDCG@5 (Retrieval Quality)**:
   - **Target**: NDCG@5 > 0.77 (matches ground-truth performance)
   - **Baseline**: Best OCR achieves 0.74, ground truth achieves 0.773
   - **Gap**: 4.5% retrieval performance gap due to OCR errors
   - **Use Case**: Measure impact of parasitic content removal on RAG retrieval accuracy

2. **Reading Order Error (ROE)**:
   - **Target**: ROE < 10% (reading order errors minimized)
   - **Critical**: 5-29% RAG performance loss from reading order errors
   - **Integration**: Validate FR-4.12 (Reading Order Prediction) effectiveness
   - **Use Case**: Ensure correct element sequencing after parasitic content removal

3. **Semantic Noise Impact**:
   - **Measure**: Proportion of retrieved chunks containing parasitic content
   - **Target**: < 5% of RAG chunks contain parasitic elements
   - **Method**: OHR-Bench semantic noise analysis (parasitic content vs. relevant content)

**DQS Routing Logic (RAG-Specific):**

Integrate with FR-7 (Document Quality Score) for intelligent RAG pipeline routing:

```python
# RAG-specific routing decision
if quality_score < 0.7:
    routing_recommendation = "use_multimodal_retrieval"  # ColPali or similar VLM
    rationale = "Low OCR quality (NDCG@5 < 0.74), multimodal retrieval recovers ~70% of accuracy loss"
elif parasitic_content_ratio > 0.15:
    routing_recommendation = "aggressive_filtering"
    rationale = "High parasitic content (>15%), apply strict filtering before RAG ingestion"
elif reading_order_confidence < 0.80:
    routing_recommendation = "simple_chunking"
    rationale = "Low reading order confidence, use spatial chunking instead of semantic"
else:
    routing_recommendation = "standard_ocr_rag"
    rationale = "High quality document, standard OCR + semantic chunking"
```

**Output Extension:**
```json
{
  "parasitic_content": {
    "detected": true,
    "regions": [
      {"type": "page_header", "bounding_box": [0, 0, 800, 50], "confidence": 0.95},
      {"type": "page_footer", "bounding_box": [0, 1100, 800, 50], "confidence": 0.92}
    ],
    "parasitic_ratio": 0.12,
    "rag_impact": {
      "ndcg_at_5_predicted": 0.76,
      "roe_predicted": 0.08,
      "routing_recommendation": "standard_ocr_rag"
    }
  }
}
```

**Benchmark Integration:**
- **Dataset**: OHR-Bench (HuggingFace: opendatalab/OHR-Bench)
  - 8,500+ PDFs from 7 domains
  - Ground-truth RAG retrieval annotations
  - **License**: CC-BY-4.0
- **Validation**: Compare parasitic content detection against OHR-Bench ground truth
- **Metrics**: NDCG@5, ROE, semantic noise ratio

**Performance Targets:**
- **NDCG@5**: > 0.77 (match or exceed ground truth retrieval performance)
- **ROE**: < 10% (reading order errors minimized)
- **Parasitic Content Recall**: > 0.90 (detect 90%+ of headers/footers)
- **Parasitic Content Precision**: > 0.85 (minimize false positives)

**Critical Findings from OHR-Bench:**
- **Retrieval Stage Impact**: RAG retrieval is more critical than generation (4.5% NDCG gap)
- **Reading Order Priority**: Reading order errors (5-29% impact) > individual quality defects
- **Multimodal Fallback**: Multimodal retrieval recovers ~70% of OCR accuracy loss for low-quality documents
- **Semantic Noise**: Parasitic content (headers/footers) is a form of semantic noise impacting retrieval

**Reference:**
- Research: "OCR Hinders RAG: Evaluating the Cascading Impact of OCR on RAG" (OHR-Bench, arXiv 2024)
- ADR-0029: Dataset Selection Strategy (OHR-Bench integration)
- ADR-0031: Comprehensive Benchmarking Framework (OHR-Bench adapter)

#### FR-4.5: Footnote Linking (Phase 3)

The system shall link footnotes to their references in the main text.

**Detection Method:**
- Detect superscript numbers in text (reference markers)
- Detect footnote regions (spatial proximity to page bottom)
- Link superscript numbers to corresponding footnotes

**Output:** Add `footnote_ref` property linking footnotes to reference locations

**Rationale:** Footnotes disconnected from context lose semantic meaning in RAG applications.

**Priority:** P1 (High for academic/research documents)

**Document Types:** Academic papers, research reports, legal documents, historical manuscripts

**Reference:** Research: "Footnote Detection and Recognition in Historical Documents" (ICDAR 2019)

#### FR-4.6: Figure-Caption Linking (Phase 2)

The system shall link figure captions to their parent figures.

**Detection Method:**
- Detect Caption class from FR-4.2
- Detect Picture class from FR-4.2
- Spatial proximity analysis (captions typically above/below figures)
- Pattern matching ("Figure N", "Fig. N")

**Output:** Add `caption_for` property linking captions to figures

**Rationale:** Captions separated from figures lose context in RAG retrieval.

**Priority:** P2 (Medium)

**Document Types:** Academic papers, research reports, technical documentation, textbooks

**Reference:** ADR-007 (Hybrid IQA Approach)

#### FR-4.7: Vertical Text Orientation Detection (Phase 3)

The system shall detect vertical text orientation (rotated text, Asian scripts).

**Detection Method:**
- Text orientation detection (0°, 90°, 180°, 270°)
- Asian script detection (Chinese, Japanese, Korean - vertical writing)
- Rotated labels in diagrams

**Output:** Add `text_orientation` property (0, 90, 180, 270 degrees)

**Rationale:** Vertical text requires rotation before OCR to avoid recognition failures.

**Priority:** P2 (Medium for multi-lingual support)

**Document Types:** Asian language documents, technical diagrams, mobile captures (rotated), posters

**Reference:** ADR-008 (Multi-Stage Pipeline Architecture)

#### FR-4.8: Handwriting Detection in Mixed Documents (Phase 2+)

The system shall detect handwritten text regions distinct from printed text (see also FR-5.2).

**Method:**
- CNN classifier or texture analysis on Text regions (from FR-4.2)
- Binary classification: "Printed" vs. "Handwritten"

**Training Data:**
- **Phase 2+**: IAM Handwriting Database (13,353 handwritten lines, HuggingFace: Teklia/IAM-line)
- **Augmentation**: Mixed with printed text from TableBank/DocLayNet

**Output:** Add `text_type: "handwritten"` property to Text layout elements

**Accuracy Target:** **F1-score ≥ 0.95** (elevated from 0.90 based on Phase 3+ research)

**Rationale:**
- Handwritten regions require different OCR engines (e.g., Microsoft Azure Read API handwriting mode)
- Critical for routing decisions in mixed documents (forms, annotations, historical manuscripts)

**Document Types:** Forms, student assignments, historical manuscripts, annotated documents

**Reference:**
- ADR-0012: Defer Handwriting Detection to Phase 2
- ADR-0029: Dataset Selection Strategy (IAM Handwriting integration)

#### FR-4.11: Table Structure Extraction (Phase 3+)

The system shall extract the internal structure of detected tables (rows, columns, cells) using a learned table structure recognition model.

**Prerequisite:** Table bounding boxes from FR-4.2 (layout detection)

**Method:** ClusterTabNet or similar deep learning approach
- **Input**: Cropped table region from layout detection
- **Output**: Table structure annotations (rows, columns, cells, spanning cells)
- **Format**: COCO-aligned bounding boxes for cells + row/column metadata

**Training Data:**
- **Primary**: PubTables-1M (1 million real-world tables from PubMed, Apache-2.0)
  - **Size**: ~25 GB
  - **Annotations**: Row/column structure, cell bounding boxes, spanning cells
  - **Source**: GitHub: microsoft/table-transformer
- **Augmentation**: TableBank (417k tables, Apache-2.0) for additional layout diversity

**Model Architecture:**
- **Option 1**: ClusterTabNet (cluster-based table structure recognition)
- **Option 2**: Table Transformer (Microsoft, DETR-based)
- **Deployment**: ONNX Runtime (INT8 quantized) for CPU-first inference

**Output Structure:**
```json
{
  "table_id": "table_001",
  "bounding_box": [120, 340, 450, 200],
  "num_rows": 8,
  "num_cols": 5,
  "cells": [
    {
      "row": 0,
      "col": 0,
      "row_span": 1,
      "col_span": 1,
      "bounding_box": [125, 345, 85, 22],
      "is_header": true
    }
  ]
}
```

**Validation:**
- **Benchmark**: PubTables-1M test split (held-out tables)
- **Metrics**: GriTS (Grid Table Similarity) or TEDS (Tree Edit Distance-based Similarity)
- **Target**: GriTS F1 > 0.85, TEDS > 0.90

**Performance Targets:**
- **Latency**: < 200ms per table (GPU), < 500ms per table (CPU with ONNX INT8)
- **Accuracy**: GriTS F1 > 0.85 on complex tables (spanning cells, nested headers)

**Rationale:**
- Detecting table bounding boxes (FR-4.2) is insufficient for structured data extraction
- RAG applications require structured table data (rows/columns) for semantic understanding
- PubTables-1M provides large-scale real-world table structure annotations
- ClusterTabNet approach handles complex tables (spanning cells, hierarchical headers)

**Priority:** P1 (High for academic papers, business reports, technical documentation)

**Document Types:** Academic papers, financial reports, technical specifications, scientific literature

**Reference:**
- ADR-0029: Dataset Selection Strategy (PubTables-1M integration)
- Research: PubTables-1M (arXiv:2110.00061, 2021)
- Research: ClusterTabNet (table structure recognition)

**Implementation:** Phase 3 Week 8-12 (training and integration)

**Note:** This requirement complements FR-4.2 (table detection) by adding structure extraction. The two-stage pipeline (detect → extract structure) enables efficient processing.

#### FR-4.12: Reading Order Prediction (Phase 3)

The system shall predict the sequential reading order for document elements in complex layouts (multi-column, tables, figures, footnotes) to enable accurate text extraction and RAG retrieval.

**Prerequisite:** Layout element detection from FR-4.2 (bounding boxes for text, tables, figures, etc.)

**Method:** Graph-based spatial reasoning
- **Input**: Layout elements with bounding boxes from YOLOv8 detection
- **Process**:
  - Construct spatial relationship graph (elements as nodes, spatial relationships as edges)
  - Apply reading order algorithm (top-to-bottom, left-to-right with multi-column handling)
  - Handle special cases: footnotes, captions, sidebars, page numbers
- **Output**: Ordered sequence of element IDs representing reading flow

**Training Data:**
- **Primary**: DocSynth-300K (300k synthetic layouts, HuggingFace: juliozhao/DocSynth300K)
  - Contains diverse multi-column layouts with ground-truth reading order
  - **Size**: 113 GB
  - **License**: Not specified (assume research use, check arXiv:2410.12628)
- **Validation**: ROOR dataset (Reading Order on OCR'd Text, GitHub: chongzhangFDU/ROOR-Datasets)
  - Real-world reading order annotations
  - **License**: CC BY 4.0
- **Fallback**: Synthetic generation using DocLayNet + spatial heuristics if ROOR unavailable

**Algorithm Options:**
- **Option 1**: Graph-based heuristics (classical spatial reasoning) - Phase 3 Week 7
- **Option 2**: Learned model (graph neural network or transformer) - Phase 4+ if needed
- **Hybrid**: Classical for simple layouts, learned for complex (multi-column, tables)

**Output Structure:**
```json
{
  "reading_order": [
    {"element_id": "text_001", "sequence": 1},
    {"element_id": "text_002", "sequence": 2},
    {"element_id": "table_001", "sequence": 3},
    {"element_id": "caption_001", "sequence": 4, "parent_element": "table_001"}
  ],
  "layout_type": "multi_column",
  "reading_order_confidence": 0.92
}
```

**Validation:**
- **Benchmark 1**: ROOR dataset (if available)
  - **Metric**: F1-score > 0.85 on pairwise reading order predictions
  - **Metric**: Kendall's Tau > 0.80 (rank correlation)
- **Benchmark 2**: OHR-Bench (HuggingFace: opendatalab/OHR-Bench)
  - **Metric**: Reading Order Error (ROE) < 10%
  - **Critical**: OHR-Bench shows 5-29% RAG performance loss from reading order errors
  - **Use Case**: Validate impact on RAG retrieval (NDCG@5 metric)

**Performance Targets:**
- **Latency**: < 50ms per page (graph construction + ordering)
- **Accuracy**: F1 > 0.85 on ROOR, ROE < 10% on OHR-Bench
- **Scalability**: Linear time complexity with number of elements (O(n log n))

**Rationale:**
- **Critical for RAG**: OHR-Bench research shows reading order errors cause **5-29% RAG performance loss**
- **More impactful than quality**: Reading order errors impact RAG retrieval more than individual quality defects
- **Multi-column handling**: Academic papers, newspapers, magazines require correct column flow
- **Semantic coherence**: Incorrect reading order destroys document meaning for downstream processors

**Priority:** P0 (Critical for RAG applications)

**Document Types:**
- Academic papers (2-column layouts)
- Newspapers and magazines (multi-column)
- Forms (complex spatial layouts)
- Technical documentation (mixed layouts with figures/tables)
- Historical documents (varied layouts)

**Integration with FR-4.4 (Parasitic Content)**:
- Parasitic content (headers, footers) excluded from reading order or marked with low priority
- Page numbers and watermarks handled separately

**Integration with FR-7 (Document Quality Score)**:
- Reading order confidence feeds into Structural Complexity Score
- Low confidence triggers fallback to simpler OCR strategies

**Reference:**
- ADR-0029: Dataset Selection Strategy (ROOR elevated to Phase 3 Critical, OHR-Bench integration)
- ADR-0031: Comprehensive Benchmarking Framework (ROOR and OHR-Bench adapters)
- Research: "OCR Hinders RAG: Evaluating the Cascading Impact of OCR on RAG" (OHR-Bench, arXiv 2024)
- Research: DocSynth-300K (arXiv:2410.12628, 2024)

**Implementation:** Phase 3 Week 7 (graph-based heuristics), Phase 4+ (learned model if needed)

**Phase Elevation Rationale:**
- **Previous Status**: Optional Phase 4-5 (not in core FR)
- **New Status**: **Phase 3 Critical** (based on OHR-Bench research findings)
- **Evidence**: 5-29% RAG performance loss from reading order errors justifies priority elevation
- **Timeline Impact**: Implemented in Phase 3 Week 7 (prioritized over DLAFormer optional research)

---

### FR-5: Specialized Content Detection (Per-page)

#### FR-5.1: Mathematical Content (Phase 3)

The system shall identify all mathematical equations on a page by providing the bounding boxes for the **Formula** class (as per FR-4.2).

**Output:** Bounding box + confidence score for each formula

**Routing:** Formula regions may be routed to specialized Math OCR (Nougat, pix2tex) in downstream processing

#### FR-5.2: Handwritten Content (Phase 2)

**FR-5.2.1:** The system shall process all regions detected as **Text** (from FR-4.2).

**FR-5.2.2:** The system shall classify each Text region as either **"Printed"** or **"Handwritten"**.

**Method:** CNN classifier or texture analysis (Bag-of-Visual-Words)

**Output:** Add `text_type` property to Text layout element in JSON

**Accuracy Target:** F1-score ≥ 0.90 on validation set (NFR-2.4)

**Reference:** ADR-0012 (Defer Handwriting Detection to Phase 2)

#### FR-5.3: Language Detection (Phase 2)

**FR-5.3.1:** The system shall perform language detection on the document.

**FR-5.3.2:** The system shall report the primary detected language(s) (e.g., `['en', 'fr']`).

**FR-5.3.3:** The system shall explicitly flag the presence of **Non-Latin scripts** (e.g., Arabic, Chinese, Japanese).

**Method:** Library-based detection (langdetect, fasttext, or py3langid)

**Output:**
- `languages: List[str]` in DocumentMetadata
- `has_non_latin: bool` in DocumentMetadata

**Rationale:** Critical for OCR language pack selection and multi-script document handling

**Document Types:** Multi-lingual documents, academic papers, international business documents

#### FR-5.4: Watermark Detection (Phase 3)

The system shall detect watermarks that may interfere with text extraction.

**Detection Method:**
- Frequency domain analysis (repeated patterns)
- Transparency/opacity analysis
- Pattern recognition (text vs image watermarks)

**Output:** Add `watermark_detected: bool` and bounding boxes in JSON

**Rationale:** Watermarks can confuse OCR (treating watermark text as document content) or require VLM processing for semantic interpretation.

**Priority:** P1 (High for legal/business documents)

**Document Types:** Legal documents, contracts, official certificates, business reports, security documents

**Action:** Detect-only (flag for downstream VLM or specialized processing)

**Reference:** DETECTION_TAXONOMY.md Section 1 (IQA Issues)

#### FR-5.5: Stamp/Seal Detection (Phase 3)

The system shall detect stamps and seals that may obscure text or require special handling.

**Detection Method:**
- Circle detection (Hough transform for circular seals)
- Color analysis (stamps typically red, blue, or black ink)
- Texture analysis (stamp patterns)

**Output:** Add `stamp_detected: bool` and bounding boxes in JSON

**Rationale:** Stamps can obscure underlying text or contain important metadata requiring VLM interpretation.

**Priority:** P2 (Medium for official documents)

**Document Types:** Government documents, contracts, historical archives, notarized documents, international shipping

**Action:** Detect-only (flag region for preservation or VLM analysis)

**Reference:** Research: "Automatic Detection and Recognition of Official Seals in Document Images" (ICDAR 2019)

#### FR-5.6: Signature Detection (Phase 3)

The system shall detect handwritten signatures.

**Detection Method:**
- Continuous stroke detection
- Ink analysis (pen pressure, continuous vs disconnected strokes)
- Spatial analysis (signatures typically at bottom of documents)

**Output:** Add `signature_detected: bool` and bounding boxes in JSON

**Rationale:** Signatures interfere with layout detection and require separate handling for legal/compliance purposes.

**Priority:** P2 (Medium for legal/business documents)

**Document Types:** Contracts, forms, legal documents, invoices, receipts, notarized documents

**Action:** Detect-only (flag region for privacy/compliance or VLM verification)

**Reference:** SignaTR6K dataset (benchmark for signature detection)

#### FR-5.7: Margin Annotation Detection (Phase 3)

The system shall detect margin annotations (handwritten notes, comments).

**Detection Method:**
- Edge detection (notes typically in margins)
- Spatial isolation (not part of main text flow)
- Handwriting detection (typically handwritten vs printed main text)

**Output:** Add `margin_annotations: bool` and bounding boxes in JSON

**Rationale:** Margin annotations should be separated from main text but preserved for historical/scholarly analysis.

**Priority:** P2 (Medium for academic/historical documents)

**Document Types:** Historical manuscripts, academic papers, annotated drafts, student assignments

**Action:** Detect-only (separate from main text for distinct processing)

**Reference:** DETECTION_TAXONOMY.md Section 3 (Specialized Content)

---

### FR-6: Correction Methods

#### FR-6.1: Blur Correction (Phase 1) - ✅ COMPLETE

The system shall apply sharpening corrections to blurred images.

**Method:**
- Unsharp mask
- Deconvolution (Wiener filter)

**Guardrails:** Only apply if blur_score > threshold and correction improves quality metrics

**Reference:** ADR-021 (Do-No-Harm Guardrails)

#### FR-6.2: Skew Correction (Phase 1) - ✅ COMPLETE

The system shall apply rotation correction to skewed documents.

**Method:** Affine rotation transform

**Guardrails:** See FR-3.2 (threshold-based correction)

**Reference:** ADR-021 (Do-No-Harm Guardrails)

#### FR-6.3: Noise Reduction (Phase 1) - ✅ COMPLETE

The system shall apply denoising to noisy images.

**Method:**
- Bilateral filter
- Non-Local Means (NLM)
- BM3D (advanced)

**Guardrails:** Only apply if noise_score > threshold

**Reference:** ADR-021 (Do-No-Harm Guardrails)

#### FR-6.4: Contrast Enhancement (Phase 1) - ✅ COMPLETE

The system shall apply contrast enhancement to low-contrast images.

**Method:**
- CLAHE (Contrast Limited Adaptive Histogram Equalization)
- Histogram equalization

**Guardrails:** Only apply if contrast_score < threshold

**Reference:** ADR-021 (Do-No-Harm Guardrails), ADR-011 (Hybrid Validation - Real-World Calibration)

#### FR-6.5: DPI Upscaling (Phase 1B) - ✅ COMPLETE

The system shall upscale low-resolution images to 300 DPI.

**Method:** See FR-3.6 for algorithms and configuration

**Guardrails:** Preserve original on error, skip if already high-resolution

**Reference:** Phase 1B Implementation Summary, ADR-010 (300 DPI Normalization)

#### FR-6.6: Binarization Correction (Phase 2)

The system shall apply adaptive binarization to improve text/background separation.

**Method:**
- Otsu thresholding (global)
- Sauvola thresholding (local adaptive)
- Niblack thresholding (local adaptive)

**Guardrails:** Compare before/after OCR confidence, only apply if improvement > 10%

**Priority:** P0 (Critical for degraded documents)

**Document Types:** Historical manuscripts, faded documents, photocopies, low-quality scans

**Reference:** Research: "Degraded Historical Document Binarization: A Review" (PMC 2021)

#### FR-6.7: Illumination Normalization (Phase 2)

The system shall normalize uneven illumination.

**Method:**
- Illumination estimation (Gaussian smoothing)
- Adaptive histogram equalization per region
- Shadow removal algorithms

**Guardrails:** Preserve original if normalization creates artifacts

**Priority:** P0 (Critical for mobile captures)

**Document Types:** Mobile captures, book scans, historical documents, poor lighting conditions

**Reference:** Research: "Robust Document Image Binarization Technique for Degraded Document Images" (IEEE 2013)

#### FR-6.8: Dewarping (Phase 3)

The system shall correct document warping and curvature.

**Method:**
- Polynomial regression (classical)
- DocUNet (deep learning - U-Net architecture)

**Guardrails:** Apply only if warping_score > threshold, validate grid straightness

**Priority:** P1 (High for book scans)

**Document Types:** Book scans, bound documents, mobile captures at angles

**Reference:** Research: "DocUNet: Document Image Unwarping via A Stacked U-Net" (CVPR 2018)

#### FR-6.9: Perspective Correction (Phase 2)

The system shall correct perspective distortion using homography transforms.

**Method:**
- Corner detection (document boundaries)
- Homography matrix estimation
- Perspective transform (warp to rectangle)

**Guardrails:** Validate corner detection accuracy, preserve original if correction fails

**Priority:** P2 (Medium for mobile captures)

**Document Types:** Mobile captures, angled scans, desktop photography

**Reference:** Research: "Automatic Document Image Rectification Using Geometric Features" (ICDAR 2017)

#### FR-6.10: Bleed-Through Suppression (Phase 3)

The system shall suppress bleed-through artifacts.

**Method:**
- Frequency domain filtering
- Dual-side image subtraction (if available)
- Color channel separation

**Guardrails:** Apply only if bleed-through detected, preserve legibility

**Priority:** P1 (High for historical documents)

**Document Types:** Historical manuscripts, thin paper documents, double-sided printing

**Reference:** Research: "Reduction of bleed-through in scanned manuscript documents" (Pattern Recognition 2011)

---

### FR-7: Document Quality Score (DQS) - Phase 4

#### FR-7.1: DQS Calculation

The system shall calculate a **Document Quality Score (DQS)** with two orthogonal axes:

**Axis 1: Degradation Score (0.0 - 1.0)**
- Measures physical image quality degradation
- Components: blur, noise, contrast, skew, resolution
- Scale: 0.0 = severe degradation, 1.0 = pristine quality

**Axis 2: Structural Complexity Score (0.0 - 1.0)**
- Measures layout and content complexity
- Components: multi-column, tables, formulas, figures, mixed scripts
- Scale: 0.0 = simple single-column, 1.0 = highly complex layout

**Reference:** ADR-0028 (Document Quality Score for Intelligent Pipeline Routing)

#### FR-7.2: Pipeline Routing Recommendation

The system shall provide a **routing_recommendation** based on DQS:

**Routing Matrix:**
```
                    LOW STRUCTURAL          HIGH STRUCTURAL
                    COMPLEXITY              COMPLEXITY
                    ─────────────────────────────────────────
HIGH DEGRADATION │  vision_simple       │  vision_structured   │
(Blurry, Noisy)  │  (VLM + Simple)      │  (VLM + Structure)   │
                 │                       │                      │
─────────────────┼──────────────────────┼──────────────────────┤
                 │                       │                      │
LOW DEGRADATION  │  ocr_fast            │  ocr_advanced        │
(Clean, Sharp)   │  (Tesseract)         │  (Nougat/Marker)     │
                 │                       │                      │
                 └───────────────────────┴──────────────────────┘
```

**Output:**
- `routing_recommendation`: Literal["vision_simple", "vision_structured", "ocr_fast", "ocr_advanced"]
- `routing_confidence`: float (0.0 - 1.0)
- `routing_rationale`: str (human-readable explanation)

---

## 3.0 Non-Functional Requirements (NFR)

### NFR-1: Performance

#### NFR-1.1: Hardware Configuration

**GPU Mode (Recommended for Production):**
- Hardware: NVIDIA T4 or better
- Use for: ML models (Phase 2-3), YOLOv8 layout detection

**CPU Mode (Development/Testing):**
- Hardware: Intel Xeon or equivalent
- Use for: Classical CV methods (Phase 1), validation

#### NFR-1.2: Performance Targets (GPU Mode)

**Latency:**
- **Target**: < 150ms per page
- **Acceptable**: < 400ms per page
- **Measurement**: p50, p95, p99 latencies

**Throughput:**
- **Target**: > 6 pages/sec per worker
- **Acceptable**: > 2 pages/sec per worker
- **Scalability**: Linear scalability to 100s of workers

**Batch Processing:**
- **Target**: 100 docs (5 pages each) in < 90 seconds
- **Calculation**: 500 pages / 90 sec = 5.56 pages/sec

#### NFR-1.3: Performance Targets (CPU Mode)

**Latency:**
- **Target**: < 400ms per page
- **Acceptable**: < 1000ms per page

**Throughput:**
- **Target**: > 2 pages/sec per worker
- **Acceptable**: > 0.5 pages/sec per worker

**Note:** CPU mode primarily for Phase 1 (classical CV) and development/testing.

**Reference:** ADR-0020 (CPU-First Deployment Strategy)

#### NFR-1.4: Resource Constraints

**GPU Memory:** < 2GB per worker

**CPU Cores:** 2-4 per worker

**RAM:** < 4GB per worker

**Disk:** Temporary file processing only (no persistent storage)

---

### NFR-2: Accuracy & Reliability

#### NFR-2.1: PDF Type Classification Accuracy

PDF type classification (FR-2.1) shall be **99.9% accurate** on the validation test set.

**Rationale:** High accuracy required to prevent routing errors

#### NFR-2.2: Skew Detection Accuracy

Skew angle detection (FR-3.2) shall be accurate to within **±0.5 degrees**.

**Method:** Compare detected angle to ground truth on validation set

#### NFR-2.3: Layout Model Accuracy

The layout detection model (FR-4.1) shall achieve:

**Primary Metric:**
- **mAP@.50** (COCO metric): > 0.82 (target), > 0.75 (acceptable)

**Secondary Metrics:**
- **mAP@.50-.95**: > 0.70
- **Per-class AP**: > 0.70 for all 11 classes (ensure rare class performance)

**Validation Dataset:** DocLayNet validation set (6,480 pages)

**Reference:** PROJECT_PLAN Phase 3 targets

#### NFR-2.4: Handwriting Classification Accuracy

The "Handwritten" vs. "Printed" classifier (FR-5.2) shall achieve an **F1-score ≥ 0.90** on the validation test set.

**Method:** Evaluate on balanced test set with 1000+ samples per class

#### NFR-2.5: Error Handling & Reliability

The system shall log all processing errors (per FR-1.4) without crashing or terminating the parent process/service.

**Requirements:**
- Must return a valid error-state JSON
- Error messages must be user-friendly
- Stack traces logged for debugging (not exposed to user)
- Graceful degradation: partial results if possible

---

### NFR-3: Maintainability & Extensibility

#### NFR-3.1: Configurability

All detection and correction thresholds shall be externalized into a configuration file (`.env` or `Settings` class) and not hard-coded.

**Examples:**
- `blur_threshold`
- `skew_angle_threshold`
- `dqs_degradation_threshold`
- `target_dpi`
- `pdf_upscale_algorithm`

**Implementation:** `src/image_preprocessing_detector/core/config.py`

#### NFR-3.2: Model Swapping

The layout detection model (FR-4.1) shall be loaded from a path specified in the configuration file, allowing the model file to be updated (e.g., a "v2" model) without requiring a new code deployment.

**Configuration:**
```python
layout_model_path: Path = Field(
    default=Path("models/yolov8_doclaynet_v1.onnx"),
    description="Path to YOLOv8 ONNX model"
)
```

#### NFR-3.3: Code Quality

The system's code shall adhere to team-defined linting standards and include docstrings for all major functions and classes.

**Standards:**
- **Formatter**: Ruff format
- **Linter**: Ruff check
- **Type Checker**: MyPy (strict on src/, relaxed on tests/)
- **Security**: Bandit + Safety
- **Coverage**: ≥ 80% test coverage

**References:**
- ADR-0001 (Consolidate Linting with Ruff)
- ADR-0013 (Real Testing Over Mocking)

---

### NFR-4: Deployment & Operations

#### NFR-4.1: Containerization

The system shall be delivered as a containerized application:
- Dockerfile for building image
- Pre-built image on container registry
- Docker Compose for local development

**Base Image:** Python 3.12 slim or alpine

**Dependencies:** All dependencies specified in `pyproject.toml`

#### NFR-4.2: Logging

The system shall generate **structured, human-readable logs** for all major processing steps:
- `file_received`
- `analysis_started`
- `correction_applied: deskew`
- `analysis_complete`
- `error_occurred`

**Format:** JSON-formatted logs using `structlog` + `rich` console

**Output:** All logs written to stdout/stderr

**Reference:** ADR-0019 (Structured Logging)

#### NFR-4.3: Statelessness

The application shall be **stateless**:
- No reliance on local disk (except temporary file processing)
- No in-memory session data between requests
- Each request is independent

**Rationale:** Enables horizontal scaling and Kubernetes deployment

---

### NFR-5: Security

#### NFR-5.1: Input Validation

All file inputs shall be validated:
- File size limits (default: 100MB, configurable)
- File format verification (magic bytes, not just extension)
- Path traversal prevention (no `../` in paths)

#### NFR-5.2: Dependency Scanning

All dependencies shall be scanned for vulnerabilities:
- **Bandit**: Python security analysis
- **Safety**: Dependency vulnerability check
- **OSV-Scanner**: OpenSSF vulnerability database

**CI/CD:** Scans run automatically on every PR and weekly

**Reference:** ADR-0004 (GitHub Actions Security Hardening)

#### NFR-5.3: Secrets Management

No secrets or API keys shall be hard-coded:
- All secrets in environment variables
- `.env.example` provided (no actual secrets)
- `.env` encrypted with GPG for local development

---

## 4.0 Phase Roadmap

### Phase 1: MVP with Classical Methods (Weeks 4-7) - ✅ COMPLETE
- Classical IQA (blur, skew, contrast detection)
- Text detection gate
- Basic corrections (deskew, CLAHE, sharpen, denoise)
- CLI tool
- JSON output

### Phase 1B: DPI Upscaling (Weeks 7-8) - ✅ COMPLETE
- DPI detection (PyMuPDF, EXIF)
- Automatic upscaling (5 OpenCV algorithms)
- Upscaling metadata tracking

### Phase 2: ML-Based IQA (Weeks 8-11) - 📋 PLANNED
- MobileNetV3/EfficientNet IQA model
- PDF type classification (image_only, born_digital, hybrid)
- Language detection (langdetect/fasttext)
- Handwriting vs. printed classification

### Phase 3: Document Layout Detection (Weeks 12-16) - 📋 PLANNED
- YOLOv8 layout detection (11 DocLayNet classes)
- Hybrid IQA (per-element quality assessment)
- Table structure recognition
- Formula/figure detection

### Phase 4: Production Hardening (Weeks 17-20) - 📋 PLANNED
- Document Quality Score (DQS) calculation
- Intelligent pipeline routing
- REST API (FastAPI)
- Monitoring and alerting (Prometheus/Grafana)
- Docker deployment

### Phase 5: Continuous Improvement (Weeks 21+) - 📋 PLANNED
- Office format preprocessing (embedded images)
- Active learning pipeline
- Model retraining automation
- A/B testing framework

---

## 5.0 Validation & Testing

### 5.1: Unit Testing

**Coverage:** ≥ 80% line coverage

**Test Categories:**
- Schema validation (Pydantic models)
- Detector accuracy (blur, skew, noise)
- Correction effectiveness (deskew, upscale)
- Configuration loading

**Framework:** pytest + pytest-cov

### 5.2: Integration Testing

**Test Scenarios:**
- End-to-end pipeline (file → JSON)
- Multi-page PDF processing
- Error handling (corrupted files, unsupported formats)
- DQS routing accuracy

### 5.3: Property-Based Testing

**Framework:** Hypothesis

**Test Properties:**
- Bounding boxes always within page dimensions
- DQS scores always in [0.0, 1.0]
- JSON schema validation never fails

**Reference:** ADR-0003 (Adopt Property-Based Testing)

### 5.4: Performance Testing

**Metrics:**
- Latency (p50, p95, p99)
- Throughput (pages/sec)
- Memory usage
- GPU utilization

**Tools:** pytest-benchmark, memory_profiler

---

## 6.0 Glossary

**COCO Format**: Common Objects in Context bounding box format `[x, y, width, height]`

**DPI**: Dots Per Inch, a measure of image resolution

**DQS**: Document Quality Score, a two-axis quality metric for routing

**IQA**: Image Quality Assessment

**OCR**: Optical Character Recognition

**VLM**: Vision-Language Model (e.g., ColPali)

**YOLOv8**: You Only Look Once version 8, an object detection model

---

## 7.0 References

**Project Documentation:**
- [PROJECT_PLAN.md](../../PROJECT_PLAN.md) - 50+ page implementation roadmap
- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md) - System design overview
- [PR_14_15_RECONCILIATION.md](../PR_14_15_RECONCILIATION.md) - Reconciliation with original PRs

**Architecture Decision Records:**
- [ADR-0007: Hybrid IQA Approach](../ADRs/0007-hybrid-iqa-approach.md)
- [ADR-0008: Multi-Stage Pipeline Architecture](../ADRs/0008-multi-stage-pipeline-architecture.md)
- [ADR-0009: COCO Bounding Box Format](../ADRs/0009-coco-bounding-box-format.md)
- [ADR-0010: 300 DPI Normalization](../ADRs/0010-300-dpi-normalization.md)
- [ADR-0021: Do-No-Harm Guardrails](../ADRs/0021-do-no-harm-guardrails.md)
- [ADR-0028: Document Quality Score Routing](../ADRs/0028-document-quality-score-routing.md)

**External Resources:**
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Docling](https://github.com/DS4SD/docling)

---

**Version:** 2.0
**Created:** 2025-11-11
**Last Updated:** 2025-11-11
**Status:** Active - Replaces PRs #14-15 functional_requirements.md
**Next Review:** Phase 2 Planning (Week 8)
