---
schema_type: common
title: "System Overview"
description: "High-level overview of the Image Preprocessing Detector architecture and workflow"
tags: [guide, architecture, documentation]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Provide a comprehensive overview of the system architecture and processing pipeline."
---

A comprehensive overview of the Image Preprocessing Detector system architecture, workflow, and design decisions.

## What is Image Preprocessing Detector?

The Image Preprocessing Detector is an intelligent system that analyzes documents (PDFs, images) and identifies required preprocessing steps before vector database ingestion for RAG (Retrieval-Augmented Generation) applications.

### Key Innovation

The system uses a **text detection gate** to route documents to specialized processing paths:

- **No-text path**: Classical computer vision + ML IQA (skew, blur, contrast, noise)
- **Text-detected path**: YOLOv8 layout detection + hybrid IQA on embedded images

This approach avoids expensive YOLOv8 inference for pure images while ensuring comprehensive analysis for text documents.

## Architecture

### High-Level Pipeline

```text
PDF/Image Input
    ↓
[Ingestion] - Standardize to 300 DPI
    ↓
[Text Detection Gate] - Fast ensemble heuristics
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
Classical IQA  YOLOv8 Layout → Extract elements → Per-element IQA
    ↓              ↓
[Correction] - Deskew, CLAHE, sharpening, denoising
    ↓              ↓
[JSON Output] - COCO-aligned metadata
```text

### Module Responsibilities

**Ingestion** ([ingestion/](../api/ingestion.md))

- PDF → standardized images (300 DPI)
- Image normalization and validation
- Multi-format support (PDF, PNG, JPEG, TIFF)

**Detection** ([detection/](../api/detection.md))

- Text gate: Fast text presence detection
- Classical IQA: Blur, skew, contrast detection
- (Phase 2+): ML-based IQA and layout detection

**Correction** ([correction/](../api/correction.md))

- OpenCV-based corrections with guardrails
- Deskew, CLAHE enhancement, sharpening, denoising
- Transform history tracking

**Output** ([output/](../api/output.md))

- JSON generation with COCO alignment
- Integration with downstream processors

## Design Decisions

### Why a Text Detection Gate?

**Problem**: Mixed document types require different processing strategies.

**Solution**: Fast text detection gate (< 10ms) routes to appropriate branch:

- Pure images → classical IQA only (fast path)
- Text documents → layout detection + hybrid IQA (comprehensive path)

This avoids expensive YOLOv8 inference for images while ensuring thorough analysis for documents.

### Why Hybrid IQA?

**Problem**: Text documents contain embedded images that need independent quality assessment.

**Solution**: Hybrid IQA approach:

1. YOLOv8 detects layout elements (tables, images, handwriting)
2. Each element gets independent IQA
3. Both page-level and element-level quality tracked

See [ARCHITECTURE_CORRECTION.md](../../ARCHITECTURE_CORRECTION.md) for detailed rationale.

### Why COCO-Aligned Bounding Boxes?

**Reason**: Compatibility with LayoutParser, Detectron2, and other document analysis tools.

**Format**: `[x, y, width, height]` instead of `[x1, y1, x2, y2]`

## Data Flow

### Example: Processing a Scanned Document

1. **Ingestion**
   - PyMuPDF extracts PDF pages
   - Pillow/OpenCV standardizes to 300 DPI
   - Output: numpy array (H, W, 3) RGB

2. **Text Gate**
   - Fast heuristics detect text presence
   - Result: text detected (confidence: 0.95)
   - Route: text-based processing path

3. **Layout Detection** (Phase 3)
   - YOLOv8 identifies tables, images, text blocks
   - Extracts bounding boxes in COCO format
   - Confidence scores for each element

4. **Hybrid IQA**
   - Page-level: blur, skew, contrast checks
   - Per-element: quality assessment for embedded images
   - Result: DetectedIssue list with locations

5. **Correction**
   - Apply deskew (angle: -2.5°)
   - Enhance contrast (CLAHE)
   - Track transform history

6. **Output**
   - Serialize to JSON
   - COCO-aligned metadata
   - Transform history for audit trail

## Phased Development

### Phase 0: Foundation (COMPLETE ✅)

- Project scaffolding
- Pydantic schema models
- Development infrastructure
- 100% docstring coverage

### Phase 1: MVP with Classical Methods (IN PROGRESS)

- PDF ingestion
- Text detection gate
- Classical IQA (blur, skew, contrast)
- OpenCV corrections
- JSON output

### Phase 2: ML for Image Quality (Planned)

- MobileNetV3/EfficientNet IQA
- Multi-label quality classification
- GPU acceleration

### Phase 3: ML for Document Layout (Planned)

- YOLOv8 layout detection
- Hybrid IQA implementation
- Per-element quality assessment

### Phase 4: Production Hardening (Planned)

- API service (FastAPI)
- Deployment automation
- Monitoring and telemetry
- Performance optimization

### Phase 5: Continuous Improvement (Ongoing)

- Model retraining
- Performance tuning
- Feature expansion

## Performance Targets

| Metric | Target | Phase |
|--------|--------|-------|
| **Text Gate** | < 10ms | Phase 1 |
| **Classical IQA** | < 500ms/page | Phase 1 |
| **ML IQA (GPU)** | < 150ms/page | Phase 2 |
| **Layout Detection** | < 100ms/page | Phase 3 |
| **Throughput** | > 6 pages/sec | Phase 3 |

## Use Cases

### RAG Document Preprocessing

Ensure documents are high-quality before embedding:

```python
# Detect quality issues
metadata = process_document("research_paper.pdf")

# Check for problems
for page in metadata.pages:
    if page.detected_issues:
        print(f"Page {page.page_number} needs preprocessing")
```

### OCR Optimization

Identify documents that need correction before OCR:

```python
# Apply corrections if needed
if any(issue.issue_type == "skew" for issue in page.detected_issues):
    corrected_image = apply_deskew(image, angle)
```

### Document Quality Assurance

Validate document quality for archival:

```python
# Quality check
if all(len(page.detected_issues) == 0 for page in metadata.pages):
    print("Document meets quality standards")
```

## Integration Points

### Upstream (Input)

- PDF documents
- Scanned images (PNG, JPEG, TIFF)
- Multi-page TIFF files

### Downstream (Output)

- **LayoutParser**: Document layout analysis
- **Tesseract**: OCR processing
- **Marker**: Markdown conversion
- **Docling**: Document understanding
- **Vector Databases**: ChromaDB, Weaviate, Qdrant

## See Also

- [Quick Start](quick-start.md) - Get started
- [Architecture](../development/architecture.md) - Detailed architecture
- [API Reference](../api/index.md) - API documentation
