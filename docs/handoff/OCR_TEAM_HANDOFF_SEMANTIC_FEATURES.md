# OCR Team Handoff: Semantic Document Features

> **Handoff Date:** 2025-01-14
> **From:** Image Preprocessing Detector Team
> **To:** OCR/Document Processing Team
> **Status:** ACTIVE HANDOFF
> **Priority:** P0 (Critical for RAG pipeline quality)

---

## Executive Summary

This document transfers **four functional requirements** from the preprocessing system to the OCR/document processing pipeline. These requirements involve **semantic understanding** of document structure, which belongs in the processing stage (after image quality corrections) rather than the preprocessing stage.

### What's Being Transferred

| FR ID | Requirement | Current Status | Complexity | Timeline Impact |
|-------|-------------|----------------|------------|-----------------|
| **FR-4.11** | Table Structure Extraction | Phase 3 Week 8 planned | High | 4-6 weeks saved |
| **FR-4.12** | Reading Order Prediction | Phase 3 Week 7 planned | High | 10-14 days saved |
| **FR-4.5** | Footnote Linking | Phase 3 planned | Medium | 3-5 days saved |
| **FR-4.6** | Figure-Caption Linking | Phase 2 planned | Low | 2-3 days saved |

**Rationale:** These requirements require semantic document understanding (cell relationships, reading flow, contextual linking) rather than pixel-level analysis. The preprocessing system focuses on **physical quality** (blur, skew, noise) and **routing metadata** (bounding boxes, complexity scores), while the OCR system handles **semantic extraction** (structure, relationships, content).

---

## Architectural Boundary

### The Boundary Test

> **Preprocessing Scope:** "Can this task be performed using only pixel-level analysis without understanding document semantics?"

| Task | Preprocessing? | Rationale |
|------|---------------|-----------|
| Detect table exists (bbox) | ✅ YES | Spatial pattern detection |
| Extract table structure (cells) | ❌ NO | Requires understanding cell relationships |
| Predict reading order | ❌ NO | Requires document flow comprehension |
| Link footnotes to references | ❌ NO | Requires contextual analysis |
| Link captions to figures | ❌ NO | Requires semantic proximity |

### Updated System Boundary

```
┌────────────────────────────────────────────────────────┐
│  PREPROCESSING (Image Quality & Routing)               │
│  ────────────────────────────────────────────────      │
│  ✅ Physical Quality:                                  │
│     - Blur, skew, noise, contrast detection            │
│     - DPI detection and upscaling (300 DPI standard)   │
│     - Deskew, CLAHE, denoising corrections             │
│                                                         │
│  ✅ Layout Detection (Bounding Boxes Only):            │
│     - Tables, images, formulas (WHERE they are)        │
│     - Text blocks, headers, footers                    │
│     - 11 DocLayNet classes (COCO format bboxes)        │
│                                                         │
│  ✅ Routing Metadata:                                  │
│     - Document Quality Score (DQS)                     │
│     - Complexity indicators (multi-column, tables)     │
│     - Routing recommendations (OCR fast/advanced/VLM)  │
│                                                         │
│  OUTPUT: Cleaned images + JSON metadata                │
└────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────┐
│  OCR/PROCESSING (Semantic Extraction)                  │
│  ────────────────────────────────────────────────      │
│  ✅ Text Extraction:                                   │
│     - OCR (Tesseract, PaddleOCR, Surya, Azure Read)    │
│     - Language detection                               │
│     - Confidence scoring                               │
│                                                         │
│  ✅ Semantic Structure (NEW - TRANSFERRED):            │
│     - Table structure extraction (rows, columns)       │
│     - Reading order prediction (element sequence)      │
│     - Footnote linking (references to notes)           │
│     - Figure-caption linking (semantic proximity)      │
│                                                         │
│  ✅ Document Understanding:                            │
│     - Semantic chunking for RAG                        │
│     - Entity extraction                                │
│     - Document structure (TOC, sections, hierarchy)    │
│                                                         │
│  OUTPUT: Structured JSON (text, tables, chunks)        │
└────────────────────────────────────────────────────────┘
```

---

## FR-4.11: Table Structure Extraction

### Requirement Definition

**Original FR-4.11 (from functional_requirements_v2.md lines 771-840):**

> The system shall extract the internal structure of detected tables (rows, columns, cells) using a learned table structure recognition model.

**Transferred Scope:**
- Extract table structure: rows, columns, cells, spanning cells
- Convert tables to structured format (JSON, DataFrame, HTML)
- Handle complex tables (hierarchical headers, merged cells, footnotes)

### Why This Belongs in OCR/Processing

1. **Semantic Understanding Required:** Determining cell boundaries requires understanding text content, column headers, and semantic grouping
2. **Docling Already Does This:** Docling uses TableFormer internally (93.6% accuracy on PubTables-1M)
3. **Duplicate Effort:** Training a separate table structure model would duplicate Docling's proven capabilities
4. **Integration Point:** Table structure is consumed by downstream RAG chunking, not preprocessing routing

### What Preprocessing Will Provide

**JSON Metadata (Table Detection Only):**
```json
{
  "detected_elements": [
    {
      "id": "table_001",
      "category": "table",
      "bbox": [120, 340, 450, 200],
      "confidence": 0.94,
      "quality_assessment": {
        "blur_score": 0.87,
        "contrast_score": 0.65,
        "skew_angle": 0.8,
        "needs_correction": false
      },
      "complexity_indicators": {
        "has_borders": true,
        "estimated_rows": 9,
        "estimated_columns": 5,
        "complexity_score": 0.62
      }
    }
  ]
}
```

**What OCR Team Should Extract:**
```json
{
  "table_id": "table_001",
  "num_rows": 9,
  "num_cols": 5,
  "cells": [
    {
      "row": 0,
      "col": 0,
      "row_span": 1,
      "col_span": 1,
      "bounding_box": [125, 345, 85, 22],
      "is_header": true,
      "text": "Quarter"
    },
    {
      "row": 0,
      "col": 1,
      "row_span": 1,
      "col_span": 2,
      "bounding_box": [215, 345, 170, 22],
      "is_header": true,
      "text": "Revenue (in millions)"
    }
  ]
}
```

### Recommended Tools

**Option 1: Docling TableFormer (RECOMMENDED)**
- **Performance:** 98.5% TEDS (best-in-class)
- **License:** MIT License (commercial use allowed)
- **Integration:** `pip install docling`
- **Training Data:** PubTabNet, FinTabNet, TableBank (pretrained)
- **Advantages:**
  - Already integrated in Docling pipeline
  - Handles complex tables (spanning cells, hierarchical headers)
  - Active development (2025 commits)
  - Production-ready SDK

**Option 2: Microsoft Table Transformer**
- **Performance:** 81% ICDAR Exact Match
- **License:** MIT License
- **Integration:** HuggingFace `microsoft/table-transformer-structure-recognition`
- **Advantages:**
  - Well-documented, battle-tested
  - Official HuggingFace integration
  - Good community support

**Option 3: PaddleOCR PP-Structure**
- **Performance:** 95% TEDS on complex tables
- **License:** Apache 2.0
- **Integration:** Part of PaddleOCR pipeline
- **Advantages:**
  - All-in-one OCR + table extraction
  - Very active development
  - Strong performance on Asian language tables

### Implementation Notes

**Training Data Available:**
- **PubTables-1M:** 1M real-world tables from PubMed (Apache-2.0)
  - GitHub: microsoft/table-transformer
  - Size: ~25 GB
  - Annotations: Row/column structure, spanning cells
- **FinTabNet:** Financial tables with complex structures
- **TableBank:** 417k tables (Apache-2.0)

**Performance Targets:**
- GriTS F1 > 0.85 (Grid Table Similarity)
- TEDS > 0.90 (Tree Edit Distance-based Similarity)
- Latency < 500ms per table (CPU), < 200ms (GPU)

**Validation Datasets:**
- PubTables-1M test split (held-out tables)
- ICDAR 2013/2019 table competition datasets

### Cost-Benefit Analysis

**If Preprocessing Team Implemented:**
- Development: 4-6 weeks (Phase 3 Week 8-12)
- Training: $10-30 GPU costs (Colab Pro)
- Infrastructure: +200-500ms latency, +1-2 GB VRAM
- Maintenance: Model updates, retraining
- **Value-add:** ZERO (Docling already provides 93.6% accuracy)

**If OCR Team Uses Pretrained Docling:**
- Integration: 2-3 days
- Training: $0 (pretrained weights)
- Infrastructure: Already in Docling pipeline
- Maintenance: Upstream updates from IBM
- **Value-add:** HIGH (avoid duplicate work, leverage proven model)

---

## FR-4.12: Reading Order Prediction

### Requirement Definition

**Original FR-4.12 (from functional_requirements_v2.md lines 842-935):**

> The system shall predict the sequential reading order for document elements in complex layouts (multi-column, tables, figures, footnotes) to enable accurate text extraction and RAG retrieval.

**Transferred Scope:**
- Predict element sequence (text blocks, tables, figures, footnotes)
- Handle multi-column layouts (2-3 column academic papers)
- Generate ordered list of element IDs for RAG chunking
- Confidence scoring for reading order predictions

### Why This Belongs in OCR/Processing

1. **Critical RAG Impact:** OHR-Bench research shows **5-29% RAG performance loss** from reading order errors
2. **Semantic Flow Understanding:** Requires understanding document structure (sections, subsections, logical flow)
3. **Downstream Dependency:** Reading order is consumed by semantic chunking (RAG), not routing decisions
4. **Content-Aware:** May require partial text extraction to disambiguate order (e.g., "continued on next page")

### What Preprocessing Will Provide

**JSON Metadata (Layout Elements with Spatial Hints):**
```json
{
  "detected_elements": [
    {
      "id": "text_001",
      "category": "text",
      "bbox": [50, 100, 200, 400],
      "confidence": 0.95,
      "spatial_hints": {
        "column_index": 0,
        "vertical_position": "top",
        "is_multi_column": true
      }
    },
    {
      "id": "text_002",
      "category": "text",
      "bbox": [270, 100, 200, 400],
      "confidence": 0.93,
      "spatial_hints": {
        "column_index": 1,
        "vertical_position": "top",
        "is_multi_column": true
      }
    },
    {
      "id": "table_001",
      "category": "table",
      "bbox": [50, 520, 420, 150],
      "confidence": 0.89
    }
  ]
}
```

**What OCR Team Should Extract:**
```json
{
  "reading_order": [
    {"element_id": "text_001", "sequence": 1},
    {"element_id": "text_002", "sequence": 2},
    {"element_id": "table_001", "sequence": 3},
    {"element_id": "caption_001", "sequence": 4, "parent_element": "table_001"}
  ],
  "layout_type": "multi_column",
  "num_columns": 2,
  "reading_order_confidence": 0.92
}
```

### Recommended Tools

**Option 1: Surya Reading Order Detection (RECOMMENDED)**
- **Performance:** Proven on complex multi-column layouts
- **License:** Modified AI Pubs Open Rail-M (free for research, startups <$2M)
- **Integration:** `pip install surya-ocr`
- **Advantages:**
  - Pretrained on 90+ languages
  - Fast inference (273ms/page on A10 GPU)
  - Handles academic papers, newspapers, magazines
  - No training required

**Option 2: Graph-Based Spatial Reasoning (Classical)**
- **Performance:** F1 > 0.85 on simple layouts
- **License:** N/A (algorithm-based)
- **Implementation:** Custom spatial graph construction
- **Advantages:**
  - No ML model required
  - Interpretable, debuggable
  - Works well for simple 1-2 column layouts
- **Disadvantages:**
  - Fails on complex layouts (3+ columns, irregular grids)
  - No learning from errors

**Option 3: Graph Neural Network (Custom Training)**
- **Training Data:** DocSynth-300K (300k synthetic layouts, 113 GB)
- **License:** Research use (verify arXiv:2410.12628)
- **Advantages:**
  - Learns from complex layout patterns
  - Generalizes to novel document types
- **Disadvantages:**
  - 2-3 weeks training time
  - Large dataset download (113 GB)
  - Surya pretrained likely better

### Implementation Notes

**Training Data Available:**
- **DocSynth-300K:** 300k synthetic layouts with ground-truth reading order
  - HuggingFace: juliozhao/DocSynth300K
  - Size: 113 GB
  - License: Research use (verify)
- **ROOR Dataset:** Reading Order on OCR'd Text (real-world)
  - GitHub: chongzhangFDU/ROOR-Datasets
  - License: CC BY 4.0

**Performance Targets (OHR-Bench Validation):**
- **Reading Order Error (ROE) < 10%** (critical)
- **NDCG@5 > 0.77** (RAG retrieval quality)
- **F1 > 0.85** on pairwise reading order predictions
- **Kendall's Tau > 0.80** (rank correlation)

**Validation Strategy:**
1. Test on OHR-Bench dataset (8,500+ PDFs, 7 domains)
2. Measure impact on RAG retrieval (NDCG@5 metric)
3. Compare reading order errors vs OCR quality errors
4. Validate on multi-column academic papers (DocLayNet subset)

### Why This Is Critical for RAG

**OHR-Bench Research Findings:**
- Reading order errors cause **5-29% RAG performance loss**
- **More impactful than individual quality defects** (blur, skew)
- Retrieval stage is bottleneck (4.5% NDCG gap from OCR errors)
- Correct reading order enables accurate semantic chunking

**Example Failure:**
```
# Incorrect Reading Order (Left-to-right, ignoring columns)
Column 1 Line 1 → Column 2 Line 1 → Column 1 Line 2 → Column 2 Line 2
Result: Semantic incoherence, breaks paragraph flow

# Correct Reading Order (Column-aware)
Column 1 Line 1 → Column 1 Line 2 → ... → Column 2 Line 1 → Column 2 Line 2
Result: Coherent text for RAG chunking
```

### Cost-Benefit Analysis

**If Preprocessing Team Implemented:**
- Development: 10-14 days (Phase 3 Week 7)
- Dataset Download: 113 GB (DocSynth-300K)
- Training: Custom graph-based or GNN training
- **Value-add:** Routing metadata (minimal)

**If OCR Team Uses Surya:**
- Integration: 1-2 days
- Training: $0 (pretrained)
- Dataset: Not needed
- **Value-add:** HIGH (direct RAG quality improvement)

---

## FR-4.5: Footnote Linking

### Requirement Definition

**Original FR-4.5 (from functional_requirements_v2.md lines 687-704):**

> The system shall link footnotes to their references in the main text.

**Transferred Scope:**
- Detect superscript numbers/symbols in main text (reference markers)
- Detect footnote regions (spatial proximity to page bottom)
- Link reference markers to corresponding footnote text
- Handle multi-page footnotes (continued footnotes)

### Why This Belongs in OCR/Processing

1. **Text Content Required:** Requires OCR to detect superscript numbers/symbols
2. **Semantic Linking:** Requires matching reference markers to footnote numbers (content-based)
3. **RAG Integration:** Linked footnotes improve context for RAG retrieval
4. **Minimal Routing Value:** Preprocessing only needs to detect "has footnotes" (boolean flag)

### What Preprocessing Will Provide

**JSON Metadata (Footnote Detection Only):**
```json
{
  "detected_elements": [
    {
      "id": "footnote_001",
      "category": "footnote",
      "bbox": [50, 1100, 500, 80],
      "confidence": 0.91,
      "spatial_hints": {
        "position": "page_bottom",
        "estimated_count": 3
      }
    }
  ],
  "has_footnotes": true
}
```

**What OCR Team Should Extract:**
```json
{
  "footnotes": [
    {
      "footnote_id": "fn_001",
      "reference_locations": [
        {"element_id": "text_003", "char_offset": 245, "marker": "1"}
      ],
      "footnote_text": "See 26 U.S.C. § 1031 for like-kind exchange rules.",
      "bbox": [50, 1100, 500, 25]
    }
  ]
}
```

### Recommended Approach

**Detection + Linking Pipeline:**
1. **OCR Extraction:** Extract all text with bounding boxes
2. **Superscript Detection:** Identify superscript numerals/symbols in main text
3. **Footnote Region Detection:** Use preprocessing bbox (`category: "footnote"`)
4. **Text Matching:** Match superscript markers to footnote text (number/symbol matching)
5. **Validation:** Verify spatial proximity (reference above footnote on page)

**Tools:**
- **Tesseract/PaddleOCR:** OCR with superscript detection
- **Regex Matching:** Pattern matching for footnote markers (1, 2, 3, *, †, ‡)
- **Layout Analysis:** Use preprocessing footnote bboxes as hints

### Implementation Notes

**Priority:** P1 (High for academic/legal documents)

**Document Types:**
- Academic papers (citations, references)
- Legal documents (statute references, case citations)
- Research reports (data sources, methodology notes)

**Performance Targets:**
- Footnote detection recall > 0.90 (find 90%+ of footnotes)
- Linking accuracy > 0.85 (correctly match 85%+ references)

**Validation:**
- Test on academic papers with extensive footnotes
- Legal documents with statutory references
- Historical manuscripts with marginal notes

---

## FR-4.6: Figure-Caption Linking

### Requirement Definition

**Original FR-4.6 (from functional_requirements_v2.md lines 706-725):**

> The system shall link figure captions to their parent figures.

**Transferred Scope:**
- Link `Caption` elements to `Picture` elements
- Handle spatial proximity (captions above/below figures)
- Pattern matching ("Figure N", "Fig. N", "Table N")
- Multi-panel figures (Figure 1a, 1b, 1c)

### Why This Belongs in OCR/Processing

1. **Text Content Required:** Requires OCR to extract caption text ("Figure 1:", "Fig. 2A:")
2. **Semantic Linking:** Requires pattern matching on caption text (content-based)
3. **RAG Integration:** Captions provide context for image understanding (VLM processing)
4. **Low Routing Value:** Preprocessing only needs to detect "has captions" (boolean flag)

### What Preprocessing Will Provide

**JSON Metadata (Detection Only):**
```json
{
  "detected_elements": [
    {
      "id": "picture_001",
      "category": "picture",
      "bbox": [100, 300, 400, 250],
      "confidence": 0.89
    },
    {
      "id": "caption_001",
      "category": "caption",
      "bbox": [100, 560, 400, 40],
      "confidence": 0.92,
      "spatial_hints": {
        "nearest_picture": "picture_001",
        "proximity": "below"
      }
    }
  ]
}
```

**What OCR Team Should Extract:**
```json
{
  "figures": [
    {
      "figure_id": "picture_001",
      "caption_id": "caption_001",
      "caption_text": "Figure 1: Revenue growth by quarter (2020-2024)",
      "figure_number": "1",
      "bbox": [100, 300, 400, 250]
    }
  ]
}
```

### Recommended Approach

**Detection + Linking Pipeline:**
1. **OCR Extraction:** Extract caption text
2. **Pattern Matching:** Regex for "Figure N:", "Fig. N:", "Table N:"
3. **Spatial Proximity:** Use preprocessing `spatial_hints.nearest_picture`
4. **Validation:** Verify caption-figure association (number matching, spatial consistency)

**Regex Patterns:**
```python
figure_patterns = [
    r"Figure\s+(\d+[a-z]?)",
    r"Fig\.\s+(\d+[a-z]?)",
    r"FIG\.\s+(\d+[a-z]?)"
]
```

### Implementation Notes

**Priority:** P2 (Medium)

**Document Types:**
- Academic papers (charts, diagrams, experimental results)
- Technical documentation (architecture diagrams, flowcharts)
- Research reports (data visualizations)

**Performance Targets:**
- Caption detection recall > 0.85
- Linking accuracy > 0.80 (correctly match 80%+ captions)

---

## What Preprocessing WILL Provide

### Guaranteed Outputs (Contract)

**1. Cleaned Images (300 DPI Standard)**
- DPI upscaling applied if < 300 DPI
- Deskew correction (if |skew| > 2.0°)
- CLAHE contrast enhancement (if contrast_score < 0.18)
- Denoising (if noise_score > 0.25)
- Sharpening (if blur_score < threshold)

**2. Layout Element Detection (COCO Format Bounding Boxes)**
- 11 DocLayNet classes: Caption, Footnote, Formula, List-item, Page-footer, Page-header, Picture, Section-header, Table, Text, Title
- Bounding box format: `[x, y, width, height]` (COCO standard)
- Confidence scores per element
- YOLOv8 detection (mAP@.50 > 0.82 target)

**3. Quality Assessment Metadata**
- Per-page quality scores: blur, contrast, noise, skew
- Per-element quality (for Picture and Figure elements)
- `needs_correction` flags
- Transform history (audit trail of corrections applied)

**4. Routing Metadata**
- Document Quality Score (DQS) - two axes:
  - Degradation Score (0.0-1.0): Physical quality
  - Structural Complexity Score (0.0-1.0): Layout complexity
- Routing recommendation: `vision_simple`, `vision_structured`, `ocr_fast`, `ocr_advanced`
- Confidence scores for routing decisions

**5. Spatial Hints (for Semantic Processing)**
- Multi-column detection (boolean + column count)
- Element spatial proximity (nearest neighbors)
- Complexity indicators (table row/column estimates, has_borders)

### JSON Schema Contract

**Preprocessing Output Schema:**
```json
{
  "file_path": "document.pdf",
  "document_type": "pdf",
  "pdf_type": "hybrid",
  "pages": [
    {
      "page_number": 1,
      "width": 2550,
      "height": 3300,
      "dpi": 300,
      "quality_assessment": {
        "blur_score": 0.87,
        "contrast_score": 0.65,
        "noise_score": 0.12,
        "skew_angle": 0.8,
        "overall_quality": 0.82
      },
      "detected_elements": [
        {
          "id": "text_001",
          "category": "text",
          "bbox": [50, 100, 200, 400],
          "confidence": 0.95,
          "quality_issues": [],
          "spatial_hints": {
            "column_index": 0,
            "is_multi_column": true
          }
        },
        {
          "id": "table_001",
          "category": "table",
          "bbox": [50, 520, 420, 150],
          "confidence": 0.89,
          "complexity_indicators": {
            "has_borders": true,
            "estimated_rows": 9,
            "estimated_columns": 5,
            "complexity_score": 0.62
          },
          "quality_issues": [
            {"issue_type": "low_contrast", "severity": "MEDIUM", "confidence": 0.73}
          ]
        },
        {
          "id": "caption_001",
          "category": "caption",
          "bbox": [50, 680, 420, 40],
          "confidence": 0.92,
          "spatial_hints": {
            "nearest_picture": "table_001",
            "proximity": "below"
          }
        },
        {
          "id": "footnote_001",
          "category": "footnote",
          "bbox": [50, 1100, 500, 80],
          "confidence": 0.91,
          "spatial_hints": {
            "position": "page_bottom",
            "estimated_count": 3
          }
        }
      ],
      "transform_history": [
        {
          "action": "dpi_upscaling",
          "timestamp": "2025-01-14T10:30:00Z",
          "parameters": {"original_dpi": 150, "target_dpi": 300, "algorithm": "lanczos"}
        },
        {
          "action": "deskew",
          "timestamp": "2025-01-14T10:30:01Z",
          "parameters": {"angle": 1.2, "variance_improvement": 0.08}
        }
      ]
    }
  ],
  "quality_score": {
    "degradation_score": 0.82,
    "structural_complexity_score": 0.65,
    "routing_recommendation": "ocr_advanced",
    "routing_confidence": 0.89,
    "routing_rationale": "High quality with complex layout (tables, multi-column)"
  }
}
```

---

## What OCR Team Should Extract (Transferred Responsibilities)

### 1. Table Structure (FR-4.11)

**Input:** Table bounding boxes from preprocessing
**Output:** Row/column structure, cell-level text

**Recommended Tool:** Docling TableFormer (98.5% TEDS)

**Example Output:**
```json
{
  "table_id": "table_001",
  "num_rows": 9,
  "num_cols": 5,
  "cells": [
    {
      "row": 0, "col": 0,
      "row_span": 1, "col_span": 1,
      "bbox": [55, 525, 80, 22],
      "is_header": true,
      "text": "Quarter",
      "confidence": 0.95
    }
  ],
  "structure_confidence": 0.92
}
```

### 2. Reading Order (FR-4.12)

**Input:** Layout element bboxes + spatial hints from preprocessing
**Output:** Ordered sequence of element IDs

**Recommended Tool:** Surya Reading Order Detection

**Example Output:**
```json
{
  "reading_order": [
    {"element_id": "text_001", "sequence": 1},
    {"element_id": "text_002", "sequence": 2},
    {"element_id": "table_001", "sequence": 3},
    {"element_id": "caption_001", "sequence": 4, "parent_element": "table_001"},
    {"element_id": "footnote_001", "sequence": 5}
  ],
  "layout_type": "multi_column",
  "num_columns": 2,
  "reading_order_confidence": 0.92
}
```

### 3. Footnote Linking (FR-4.5)

**Input:** Footnote bboxes from preprocessing + OCR text
**Output:** Reference markers linked to footnote text

**Example Output:**
```json
{
  "footnotes": [
    {
      "footnote_id": "footnote_001",
      "reference_locations": [
        {"element_id": "text_001", "char_offset": 245, "marker": "1"}
      ],
      "footnote_text": "26 U.S.C. § 1031 like-kind exchange rules.",
      "linking_confidence": 0.88
    }
  ]
}
```

### 4. Figure-Caption Linking (FR-4.6)

**Input:** Picture + Caption bboxes with spatial hints
**Output:** Linked figure-caption pairs

**Example Output:**
```json
{
  "figures": [
    {
      "figure_id": "picture_001",
      "caption_id": "caption_001",
      "caption_text": "Figure 1: Revenue growth by quarter",
      "figure_number": "1",
      "linking_confidence": 0.91
    }
  ]
}
```

---

## Integration Workflow

### End-to-End Pipeline

```
┌──────────────────────────────────────────────────────┐
│  STEP 1: PREPROCESSING (This System)                 │
│  ─────────────────────────────────────────────────   │
│  Input: Raw PDF/image                                │
│  Process:                                            │
│    1. DPI detection → upscale to 300 DPI            │
│    2. Quality detection (blur, skew, noise)         │
│    3. Corrections (deskew, CLAHE, denoise)          │
│    4. Layout detection (YOLOv8 bboxes)              │
│    5. DQS calculation (routing decision)            │
│  Output: cleaned_image.png + metadata.json          │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  STEP 2: OCR/PROCESSING (Your System)                │
│  ─────────────────────────────────────────────────   │
│  Input: cleaned_image.png + metadata.json            │
│  Process:                                            │
│    1. OCR text extraction (Tesseract/PaddleOCR)     │
│    2. Table structure (Docling TableFormer)         │
│    3. Reading order (Surya)                         │
│    4. Footnote linking (pattern matching)           │
│    5. Figure-caption linking (spatial + text)       │
│    6. Semantic chunking (for RAG)                   │
│  Output: structured_document.json                    │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  STEP 3: RAG INGESTION                               │
│  ─────────────────────────────────────────────────   │
│  Input: structured_document.json                     │
│  Process:                                            │
│    1. Chunk text (preserve reading order)           │
│    2. Embed chunks (vector database)                │
│    3. Store metadata (tables, figures, footnotes)   │
│  Output: Vector database ready for retrieval        │
└──────────────────────────────────────────────────────┘
```

### Handoff Protocol

**Step 1: Preprocessing completes → writes files**
```bash
output/
  ├── cleaned_images/
  │   └── document_page_001.png (300 DPI, corrected)
  └── metadata/
      └── document.json (preprocessing metadata)
```

**Step 2: OCR team reads files → processes → writes output**
```bash
output/
  ├── cleaned_images/
  │   └── document_page_001.png
  ├── metadata/
  │   ├── document.json (preprocessing metadata)
  │   └── document_ocr.json (OCR output - NEW)
  └── structured/
      └── document_structured.json (final output - NEW)
```

**Step 3: RAG ingestion reads `document_structured.json`**

---

## Datasets & Research

### Datasets Available for Transferred FRs

**For FR-4.11 (Table Structure):**
- **PubTables-1M:** 1M tables with row/column annotations (Apache-2.0)
  - GitHub: microsoft/table-transformer
  - Size: ~25 GB
  - Pre-trained weights available
- **FinTabNet:** Financial tables with complex structures
- **TableBank:** 417k tables (Apache-2.0)

**For FR-4.12 (Reading Order):**
- **DocSynth-300K:** 300k synthetic layouts with ground-truth reading order
  - HuggingFace: juliozhao/DocSynth300K
  - Size: 113 GB
  - License: Research use (verify arXiv:2410.12628)
- **ROOR Dataset:** Reading Order on OCR'd Text (real-world)
  - GitHub: chongzhangFDU/ROOR-Datasets
  - License: CC BY 4.0
- **OHR-Bench:** RAG evaluation dataset with reading order annotations
  - HuggingFace: opendatalab/OHR-Bench
  - Size: 8,500+ PDFs, 7 domains
  - License: CC-BY-4.0

**For FR-4.5 (Footnote Linking):**
- Limited specialized datasets
- Recommend using DocLayNet footnote annotations as starting point
- Academic paper datasets (PubLayNet, DocBank) contain footnote examples

**For FR-4.6 (Figure-Caption Linking):**
- DocLayNet has Caption and Picture classes (can derive linking training data)
- PubLayNet scientific papers (arXiv subset)

### Research Papers & References

**Table Structure Extraction:**
- [PubTables-1M Paper](https://arxiv.org/abs/2110.00061) (2021)
- [TableFormer](https://github.com/docling-project/docling) (Docling integration, 2024-2025)
- [Table Transformer](https://arxiv.org/abs/2110.00061) (Microsoft, 2021)

**Reading Order Prediction:**
- [DocSynth-300K](https://arxiv.org/abs/2410.12628) (2024)
- [OHR-Bench: OCR Hinders RAG](https://arxiv.org/abs/2410.12628) (2024) - **Critical for understanding RAG impact**
- [ROOR Dataset](https://github.com/chongzhangFDU/ROOR-Datasets) (Reading order benchmarks)

**Document Understanding:**
- [DocLayNet Paper](https://arxiv.org/abs/2206.01062) (2022) - Layout detection benchmark
- [LayoutParser](https://arxiv.org/abs/2103.15348) (2021) - Document layout analysis toolkit

---

## Performance Targets & Validation

### FR-4.11: Table Structure Extraction

**Metrics:**
- **GriTS F1 > 0.85** (Grid Table Similarity)
- **TEDS > 0.90** (Tree Edit Distance-based Similarity)
- **Latency < 500ms per table** (CPU), < 200ms (GPU)

**Validation Datasets:**
- PubTables-1M test split
- ICDAR 2013/2019 table competition datasets

**Known Baseline:** Docling TableFormer achieves **98.5% TEDS** (exceeds targets)

### FR-4.12: Reading Order Prediction

**Metrics (OHR-Bench Critical):**
- **Reading Order Error (ROE) < 10%** (CRITICAL - impacts RAG 5-29%)
- **NDCG@5 > 0.77** (RAG retrieval quality)
- **F1 > 0.85** on pairwise reading order predictions
- **Kendall's Tau > 0.80** (rank correlation)

**Validation Datasets:**
- OHR-Bench (8,500+ PDFs, RAG-specific evaluation)
- ROOR Dataset (reading order ground truth)
- DocLayNet multi-column subset

**Known Baseline:** Surya handles 90+ languages, multi-column layouts (no published ROE on OHR-Bench)

### FR-4.5: Footnote Linking

**Metrics:**
- **Footnote detection recall > 0.90** (find 90%+ of footnotes)
- **Linking accuracy > 0.85** (correctly match 85%+ references)
- **Latency < 100ms per page** (pattern matching + OCR)

**Validation:**
- Academic papers with extensive footnotes
- Legal documents with statutory references

### FR-4.6: Figure-Caption Linking

**Metrics:**
- **Caption detection recall > 0.85**
- **Linking accuracy > 0.80** (correctly match 80%+ captions)
- **Latency < 50ms per page** (pattern matching + spatial)

**Validation:**
- Academic papers with charts/diagrams
- Technical documentation

---

## Timeline & Milestones

### Preprocessing Team Timeline (Unchanged)

**Phase 1 (Weeks 4-7): MVP - Classical Methods** ✅ COMPLETE
- Classical IQA (blur, skew, contrast detection)
- Text detection gate
- Basic corrections (deskew, CLAHE, sharpen, denoise)

**Phase 1B (Weeks 7-8): DPI Upscaling** ✅ COMPLETE
- DPI detection and upscaling (5 OpenCV algorithms)
- 300 DPI normalization standard

**Phase 2 (Weeks 8-11): ML-Based IQA** 📋 IN PROGRESS
- Train MobileNetV3 on 50k synthetic IQA dataset
- PDF type classification (image_only, born_digital, hybrid)
- Handwriting vs. printed classification

**Phase 3 (Weeks 12-16): Layout Detection** 📋 PLANNED
- YOLOv8 layout detection (11 DocLayNet classes)
- ~~Table structure extraction~~ ❌ REMOVED (transferred to OCR)
- ~~Reading order prediction~~ ❌ REMOVED (transferred to OCR)
- Hybrid IQA (per-element quality assessment)

**Phase 4 (Weeks 17-20): Production Hardening** 📋 PLANNED
- Document Quality Score (DQS) calculation
- Intelligent pipeline routing
- REST API (FastAPI)
- Monitoring and alerting

### OCR Team Timeline (NEW - Transferred Work)

**Immediate (Week 1-2): Tool Integration**
- Integrate Docling TableFormer (FR-4.11)
- Integrate Surya Reading Order (FR-4.12)
- Implement footnote linking (FR-4.5)
- Implement figure-caption linking (FR-4.6)

**Week 3-4: Validation**
- Benchmark TableFormer on PubTables-1M test split (GriTS F1 > 0.85)
- Benchmark Surya on OHR-Bench (ROE < 10%)
- Test footnote linking on academic papers
- Test figure-caption linking on technical docs

**Week 5-6: Integration Testing**
- End-to-end pipeline testing (preprocessing → OCR → RAG)
- Performance benchmarking (latency, throughput)
- Quality validation (NDCG@5 > 0.77 on OHR-Bench)

**Week 7-8: Production Hardening**
- Error handling and edge cases
- Logging and monitoring integration
- Documentation and runbooks

---

## Contact & Support

### Preprocessing Team Contacts

**Lead Developer:** Byron Williams
- Email: byron@example.com
- GitHub: @byronwilliams (example)

**Project Repository:**
- GitHub: github.com/your-org/image_preprocessing_detector (example)
- Documentation: `/docs/` directory
- Handoff docs: `/docs/handoff/` directory

### Questions & Clarifications

**For questions about:**
- **Preprocessing JSON schema:** See `src/image_preprocessing_detector/schema.py`
- **Layout detection classes:** See `docs/requirements/functional_requirements_v2.md` FR-4.2
- **Quality assessment scores:** See `docs/ADRs/0014-classical-ml-hybrid-iqa.md`
- **Routing metadata (DQS):** See `docs/ADRs/0028-document-quality-score-routing.md`

**For handoff coordination:**
- Create GitHub issue in preprocessing repo with tag `ocr-handoff`
- Expected response time: 24-48 hours
- Escalation: Project manager (if needed)

---

## Appendix A: Scope Clarification (Out-of-Scope for Preprocessing)

The following tasks are **explicitly out-of-scope** for the preprocessing system and **must be handled by OCR/processing:**

### ❌ Out-of-Scope (OCR/Processing Responsibility)

1. **Full OCR Text Extraction**
   - Tesseract, PaddleOCR, Azure Read API
   - Text confidence scoring
   - Language pack selection

2. **Table Structure Extraction** (FR-4.11 - TRANSFERRED)
   - Row/column structure
   - Cell-level bounding boxes
   - Spanning cells, merged cells
   - Table-to-JSON conversion

3. **Reading Order Prediction** (FR-4.12 - TRANSFERRED)
   - Sequential element ordering
   - Multi-column flow handling
   - Cross-page continuations

4. **Semantic Linking** (FR-4.5, FR-4.6 - TRANSFERRED)
   - Footnote reference matching
   - Figure-caption associations
   - Cross-references

5. **Semantic Chunking for RAG**
   - Paragraph-aware splitting
   - Semantic boundary detection
   - Chunk size optimization

6. **Entity Extraction**
   - Named entity recognition (NER)
   - Date/currency extraction
   - Legal entity identification

7. **Document Structure Parsing**
   - Table of Contents (TOC)
   - Section hierarchy
   - Document outline

### ✅ In-Scope (Preprocessing Responsibility)

1. **Physical Quality Assessment**
   - Blur, skew, noise, contrast detection
   - DPI detection and upscaling
   - Image quality scoring

2. **Image Corrections**
   - Deskew, CLAHE, denoising, sharpening
   - Do-no-harm guardrails
   - Transform history tracking

3. **Layout Detection (Bounding Boxes Only)**
   - 11 DocLayNet classes (Caption, Footnote, Formula, etc.)
   - COCO format bboxes
   - Confidence scores

4. **Routing Metadata**
   - Document Quality Score (DQS)
   - Complexity indicators
   - Routing recommendations (OCR fast/advanced, VLM)

5. **Spatial Hints**
   - Multi-column detection
   - Element proximity analysis
   - Complexity scoring (table row/column estimates)

---

## Appendix B: Validation Checklist for OCR Team

Use this checklist to verify successful integration of transferred FRs:

### FR-4.11: Table Structure Extraction

- [ ] Docling TableFormer integrated and tested
- [ ] PubTables-1M test split evaluation complete (GriTS F1 > 0.85)
- [ ] Table structure JSON schema defined and validated
- [ ] Latency < 500ms per table on CPU (or < 200ms on GPU)
- [ ] Complex tables handled (spanning cells, hierarchical headers)
- [ ] Integration with RAG chunking tested

### FR-4.12: Reading Order Prediction

- [ ] Surya Reading Order integrated and tested
- [ ] OHR-Bench evaluation complete (ROE < 10%)
- [ ] Multi-column layouts handled correctly
- [ ] Reading order JSON schema defined
- [ ] NDCG@5 > 0.77 on RAG retrieval tasks
- [ ] Integration with semantic chunking tested

### FR-4.5: Footnote Linking

- [ ] OCR extracts footnote text with bounding boxes
- [ ] Superscript detection implemented (Tesseract/regex)
- [ ] Reference marker to footnote linking working (accuracy > 0.85)
- [ ] Footnote JSON schema defined
- [ ] Tested on academic papers and legal documents

### FR-4.6: Figure-Caption Linking

- [ ] OCR extracts caption text
- [ ] Pattern matching for "Figure N:", "Fig. N:" working
- [ ] Spatial proximity linking using preprocessing hints
- [ ] Figure-caption JSON schema defined
- [ ] Tested on academic papers and technical docs (accuracy > 0.80)

### End-to-End Integration

- [ ] Preprocessing → OCR pipeline tested on 100+ documents
- [ ] JSON schema contract validated (no breaking changes)
- [ ] Performance benchmarks meet targets (latency, throughput)
- [ ] RAG retrieval quality validated (NDCG@5 > 0.77)
- [ ] Error handling for edge cases implemented
- [ ] Logging and monitoring integrated

---

## Appendix C: Example Documents for Testing

Use these example document types to validate transferred FR implementations:

### Test Case 1: Academic Paper (Multi-Column)
**File:** `test_data/academic_paper_multicolumn.pdf`
**Tests:** FR-4.12 (reading order), FR-4.6 (figure-caption linking)
**Expected:**
- 2-column layout detected
- Reading order: Column 1 → Column 2 (per page)
- 5 figures with captions correctly linked

### Test Case 2: Financial Report (Complex Tables)
**File:** `test_data/sec_10k_filing.pdf`
**Tests:** FR-4.11 (table structure)
**Expected:**
- 8 tables detected
- Complex table structures extracted (merged cells, hierarchical headers)
- GriTS F1 > 0.85 on ground truth

### Test Case 3: Legal Document (Footnotes)
**File:** `test_data/legal_brief_footnotes.pdf`
**Tests:** FR-4.5 (footnote linking)
**Expected:**
- 15 footnotes detected
- Superscript markers correctly linked to footnote text
- Linking accuracy > 0.85

### Test Case 4: Technical Manual (Mixed Content)
**File:** `test_data/technical_manual_diagrams.pdf`
**Tests:** FR-4.6 (figure-caption), FR-4.12 (reading order)
**Expected:**
- 12 diagrams with captions
- Figure-caption linking accuracy > 0.80
- Reading order preserves diagram context

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-14 | Byron Williams | Initial handoff document created |

---

## Sign-off

**Preprocessing Team:**
- [ ] Byron Williams (Lead Developer) - Date: __________
- [ ] Project Manager - Date: __________

**OCR Team:**
- [ ] OCR Team Lead - Date: __________
- [ ] Technical Architect - Date: __________

**Notes:**
_Space for any additional handoff notes, concerns, or clarifications_

---

**END OF HANDOFF DOCUMENT**
