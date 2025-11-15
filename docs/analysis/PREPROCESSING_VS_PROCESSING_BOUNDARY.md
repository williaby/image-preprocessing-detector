# Preprocessing vs Processing: Architectural Boundary Definition

**Date**: 2025-01-15
**Purpose**: Define clear separation of concerns between preprocessing and processing layers
**Status**: Active - Applies to all phases

---

## The Boundary Test

> **"Can this task be performed using only pixel-level analysis without understanding document semantics?"**
> - **YES** → Preprocessing responsibility
> - **NO** → Processing responsibility (delegate to Docling/Marker)

---

## Preprocessing Responsibilities (This System)

### Physical Quality Assessment
✅ Blur detection (Laplacian variance)
✅ Skew detection (Hough transform)
✅ Noise assessment (connected components)
✅ Contrast analysis (histogram bimodality)
✅ DPI detection and upscaling
✅ Perspective distortion
✅ Illumination uniformity

### Image Corrections (OpenCV-based)
✅ Deskew (rotation)
✅ CLAHE (contrast enhancement)
✅ Sharpening (blur correction)
✅ Denoising (bilateral filter, NLM)
✅ DPI upscaling (Lanczos, bicubic)

### Layout Detection (Bounding Boxes Only)
✅ Table bounding boxes (FR-4.2)
✅ Figure/image bounding boxes
✅ Formula bounding boxes
✅ Handwriting region detection
✅ Text block detection

### Routing Metadata
✅ Document Quality Score (DQS)
✅ Routing recommendation (OCR vs VLM)
✅ Confidence scores
✅ Transform history
✅ Complexity indicators

---

## Processing Responsibilities (Docling/Marker)

### Semantic Extraction
❌ OCR / text extraction
❌ **Table structure extraction** (rows, columns, cells) ← FR-4.11
❌ Reading order prediction
❌ Figure-caption linking
❌ Footnote linking
❌ Entity recognition
❌ Citation parsing

### Structured Data Extraction
❌ Table-to-JSON conversion
❌ Formula LaTeX extraction
❌ Metadata extraction (authors, dates, titles)
❌ Semantic chunking
❌ Vectorization / embeddings

---

## Examples

| Task | Preprocessing? | Rationale |
|------|---------------|-----------|
| Detect table bounding box | ✅ YES | Spatial pattern detection (pixel-level) |
| **Extract table rows/columns** | ❌ NO | Requires semantic understanding of cells |
| Detect blur | ✅ YES | Laplacian variance (pixel-level) |
| Read text via OCR | ❌ NO | Semantic content extraction |
| Detect formula bounding box | ✅ YES | Spatial pattern detection |
| Extract LaTeX from formula | ❌ NO | Semantic content extraction |
| Detect skew angle | ✅ YES | Hough transform (pixel-level) |
| Predict reading order | ❌ NO | Semantic document flow understanding |
| Detect low contrast | ✅ YES | Histogram analysis (pixel-level) |
| Link figure to caption | ❌ NO | Semantic relationship parsing |

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────────┐
│  PREPROCESSING (This System)                     │
│  ────────────────────────────────────────────    │
│  Input:  Raw PDF/image                           │
│  Task:   Physical quality assessment             │
│  Output: Cleaned images + JSON metadata          │
│  ────────────────────────────────────────────    │
│  • DPI normalization (300 DPI)                   │
│  • Quality detection (blur, skew, noise)         │
│  • Image corrections (deskew, CLAHE, sharpen)    │
│  • Bounding box detection (tables, figures)      │
│  • Routing metadata (DQS, complexity)            │
└──────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────┐
│  PROCESSING (Docling/Marker)                     │
│  ────────────────────────────────────────────    │
│  Input:  Cleaned images + preprocessing metadata │
│  Task:   Semantic extraction                     │
│  Output: Structured data (text, tables, chunks)  │
│  ────────────────────────────────────────────    │
│  • OCR / text extraction                         │
│  • Table structure extraction (TableFormer)      │
│  • Reading order prediction                      │
│  • Semantic chunking                             │
│  • Vectorization                                 │
└──────────────────────────────────────────────────┘
```

---

## Scope Definition (from FR 1.2)

**IN-SCOPE (Preprocessing)**:
- Accept single document file
- Analyze file to identify properties and quality issues
- Run CV-based and ML-based detectors
- Perform foundational image corrections
- Output structured JSON metadata
- Calculate Document Quality Score (DQS)

**OUT-OF-SCOPE (Processing)**:
- Full-page OCR or text extraction
- **Downstream parsing logic (table-to-JSON, semantic chunking, vectorization)**
- PDF Portfolio files
- Full office document parsing (delegated to Docling)

---

## Integration Pattern

**Preprocessing Output** (What we provide):
```json
{
  "pages": [
    {
      "image_path": "page1_corrected.png",
      "quality_score": 0.82,
      "detected_elements": [
        {
          "id": "table_001",
          "category": "table",
          "bbox": [120, 340, 450, 200],
          "confidence": 0.94,
          "quality_assessment": {
            "blur_score": 0.87,
            "contrast_score": 0.65
          }
        }
      ],
      "routing_recommendation": "ocr_advanced"
    }
  ]
}
```

**Processing Input** (What Docling expects):
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("page1_corrected.png")

# Docling extracts structure automatically
{
  "tables": [
    {
      "bbox": [120, 340, 450, 200],
      "structure": {
        "rows": 9,
        "columns": 5,
        "cells": [...]
      }
    }
  ]
}
```

---

## FRs Under Review

**These FRs may violate the boundary and need review**:

1. **FR-4.11: Table Structure Extraction** ❌ REMOVE
   - Extracts rows/columns/cells (semantic)
   - Duplicates Docling TableFormer
   - See: FR_4_11_BOUNDARY_ANALYSIS.md

2. **FR-4.12: Reading Order Prediction** ⚠️ REVIEW NEEDED
   - Predicts element sequence (semantic flow)
   - May belong in processing layer

3. **FR-4.5: Footnote Linking** ⚠️ REVIEW NEEDED
   - Links footnotes to references (semantic)
   - May belong in processing layer

4. **FR-4.6: Figure-Caption Linking** ⚠️ REVIEW NEEDED
   - Links captions to figures (semantic)
   - May belong in processing layer

**These FRs are acceptable**:

1. **FR-4.4: Parasitic Content Detection** ✅ KEEP
   - Uses spatial heuristics (repeated patterns, positions)
   - No semantic understanding required

2. **FR-5.1: Mathematical Content** ✅ KEEP
   - Bounding box detection only
   - LaTeX extraction delegated to processing

---

## Decision Criteria

**KEEP in preprocessing if**:
1. Uses only pixel-level analysis (OpenCV operations)
2. Does not require semantic understanding
3. Provides routing metadata (not final structured output)
4. Can be done without OCR
5. Is physical quality assessment or correction

**DELEGATE to processing if**:
1. Requires understanding document semantics
2. Extracts structured data (JSON, DataFrames)
3. Involves text content analysis
4. Requires OCR or language understanding
5. Is downstream parsing logic

---

## References

- [FR_4_11_BOUNDARY_ANALYSIS.md](FR_4_11_BOUNDARY_ANALYSIS.md) - Detailed analysis
- [Functional Requirements v2.0](../requirements/functional_requirements_v2.md) - FR 1.2 scope
- [ARCHITECTURE_SUMMARY.md](../architecture/ARCHITECTURE_SUMMARY.md) - Pipeline design
- [ADR-009: COCO Bounding Box Format](../ADRs/0009-coco-bounding-box-format.md) - LayoutParser integration

---

**Last Updated**: 2025-01-15
**Applies To**: All project phases
**Enforcement**: Code reviews, ADRs, functional requirements
