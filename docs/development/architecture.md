---
schema_type: common
title: "System Architecture"
description: "Technical architecture of the Image Preprocessing Detector system"
tags: [architecture, pipeline, rag_pipeline]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the overall system architecture and design patterns."
---

This document provides a comprehensive overview of the Image Preprocessing Detector system architecture, including its role in the larger RAG pipeline ecosystem.

## Project Context: Four-Project RAG Pipeline

Image Preprocessing Detector is **Project A** in a four-project RAG document processing pipeline:

```
Project A (THIS PROJECT)  →  Project B          →  Project C         →  Project D
Preprocessing & IQA             OCR Orchestration    Fusion & Trust       Vector Indexing
─────────────────────         ─────────────────    ──────────────       ───────────────
• IQA & Corrections           • Full Layout        • Multi-Engine       • Embeddings
• Text Gate                   • Reading Order        Fusion             • Vector DB
• DQS Calculation             • Table Structure    • Trust Scoring      • Retrieval
• Routing Metadata            • Multi-Engine OCR   • RAG Chunking       • Search

OUTPUT:                       OUTPUT:              OUTPUT:              OUTPUT:
DocumentMetadata.json         OCRDocument.json     FusedDocument.json   Vector DB Entries
+ Corrected Images
```

**Project A Mission**: Deliver clean, corrected, quality-scored page images with reliable metadata that determines which workflows Project B should use.

For complete RAG pipeline architecture, see [RAG Pipeline Overview](RAG%20Pipeline/RAG-pipeline-project-overview.md).

## High-Level Architecture

### Multi-Stage Pipeline with Text Detection Gate

The system uses a **text detection gate** to route documents to specialized processing paths:

```
PDF/Image Input
    ↓
[Pre-flight Analysis] - DPI detection & upscaling (Phase 4)
    ↓ (Auto-upscale if < 300 DPI)
[Ingestion] - Standardize to 300 DPI images
    ↓
[PDF Type Classification] - image_only/born_digital/hybrid (Phase 8)
    ↓
[Text Gate] - Fast ensemble heuristics
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
Classical IQA  Layout-Lite Classifier → Coarse page attributes
    ↓              ↓
ML IQA         ML IQA (Teacher-Student ResNet)
(Student)      (Student + selective Teacher)
    ↓              ↓
[Correction] - Deskew, CLAHE, sharpening, denoising
    ↓              ↓
[DQS Calculation] (Phase 8) - Degradation + Structural Complexity scores
    ↓              ↓
[Routing Recommendation] (Phase 8) - ocr_fast/advanced, vision_simple/structured
    ↓              ↓
[JSON Output] - DocumentMetadata.json + corrected images
    ↓
HANDOFF TO PROJECT B (OCR Orchestration)
```

### Key Design Decisions

**Why Text Detection Gate?**
- **Problem**: Mixed document types require different processing strategies
- **Solution**: Fast text detection gate (<10ms) routes to appropriate branch, avoiding expensive layout inference for pure images
- See [ADR-0029: Project A Scope Boundaries](../ADRs/0029-project-a-scope-boundaries.md)

**Why Teacher-Student ML IQA?**
- **Problem**: ResNet-50 provides superior accuracy but is slower
- **Solution**: ResNet-18 student for default inference, ResNet-50 teacher for difficult/high-risk cases
- See [ADR-0034: ResNet18 Phase2 IQA](../ADRs/0034-resnet18-phase2-iqa.md)

**Why Layout-Lite vs Full Layout?**
- **Project A Scope**: Coarse page attributes only (has_tables, has_figures, layout_type)
- **Project B Scope**: Full semantic layout with DocLayNet-style detection
- See [ADR-0033: Delegate Semantic Features to OCR](../ADRs/0033-delegate-semantic-features-to-ocr.md)

## Module Architecture

### Core Components

```
src/image_preprocessing_detector/
├── schema.py                 # Pydantic v2 models (COCO-aligned)
├── ingestion/                # PDF/image loading and normalization
│   ├── pdf_analyzer.py       # Pre-flight DPI analysis
│   ├── pdf_resolution.py     # DPI detection
│   └── pdf_upscaler.py       # OpenCV upscaling (5 algorithms)
├── detection/                # Quality assessment and routing
│   ├── text_gate.py          # Fast text presence detection
│   ├── iqa_classical.py      # Classical CV detectors
│   ├── iqa_ml.py             # Teacher-student ML IQA
│   └── layout_lite.py        # Coarse layout classification
├── correction/               # OpenCV-based corrections
│   └── guardrails.py         # Safety thresholds
├── routing/                  # DQS and routing logic (Phase 8)
│   ├── dqs.py                # Document Quality Score
│   ├── pdf_classifier.py     # PDF type classification
│   └── recommendation.py     # OCR routing strategies
├── output/                   # JSON serialization
└── utils/                    # Logging, device probing
```

### Data Flow Pattern

1. **Pre-flight Analysis** (Phase 4): DPI detection → automatic upscaling if <300 DPI
2. **Ingestion** (Phase 0): PyMuPDF extracts PDF pages → Pillow/OpenCV standardizes to 300 DPI
3. **PDF Type Classification** (Phase 8): Classify as image_only/born_digital/hybrid
4. **Text Gate** (Phase 0): Fast heuristics (<10ms) → route to appropriate branch
5. **Detection Branch**:
   - No-text: Classical IQA (Phase 4) + Student ML IQA (Phase 2)
   - Text: Layout-lite classification (Phase 6) + Student ML IQA (Phase 2) + selective Teacher inference
6. **Correction** (Phase 4): Apply OpenCV transforms with confidence-based thresholds
7. **DQS & Routing** (Phase 8): Calculate quality scores + generate routing recommendations
8. **Output** (Phase 8): Serialize DocumentMetadata.json + write corrected images → handoff to Project B

## Phase-Based Development

The system is developed in phases aligned with the RAG pipeline architecture:

- **Phase 0** (Week 0-1): Project Setup - ✅ **COMPLETE**
- **Phase 2** (Week 2-4): ResNet Teacher & Student ML IQA - 🔄 **PLANNED**
- **Phase 4** (Week 5-6): Classical IQA + DPI Upscaling - 🔄 **PLANNED**
- **Phase 6** (Week 6-8): Layout-Lite Detection - ⏳ **PLANNED**
- **Phase 8** (Week 9): DQS & Routing - ⏳ **PLANNED**
- **Phase 10** (Week 10): Validation & Documentation - ⏳ **PLANNED**

See [Project Plan](RAG%20Pipeline/project-a-project-plan.md) for detailed implementation roadmap.

## Performance Architecture

### Performance Targets

**ML IQA (Phase 2)**:

| Metric | Target | Notes |
|--------|--------|-------|
| Student (ResNet-18) CPU | ≤40ms/page (target), ≤100ms (acceptable) | Production default |
| Student (ResNet-18) GPU | ≤10ms/page (target), ≤25ms (acceptable) | Local GPU preferred |
| Teacher (ResNet-50) GPU | ≤30ms/page | Flagged pages only |
| IQA mAP | > 0.88 | Multi-label classification on OHR-Bench |

**End-to-End (Phase 10)**:

| Metric | Target | Notes |
|--------|--------|-------|
| Latency (GPU) | <150ms/page | Full pipeline with GPU |
| Latency (CPU) | <500ms/page | Full pipeline CPU-only |
| Throughput (GPU) | ≥6 pages/sec/worker | With T4 GPU |
| Throughput (CPU) | ≥2 pages/sec/worker | CPU-only mode |

### Device Priority Strategy

The system follows a device priority execution model:

1. **Local GPU** (preferred): CUDA-enabled GPU for fastest inference
2. **Local CPU**: CPU-only mode with optimized ONNX models
3. **Modal GPU**: Serverless GPU fallback for training/batch processing

See [ADR-0020: CPU-First Deployment Strategy](../ADRs/0020-cpu-first-deployment-strategy.md)

## Schema Architecture

### COCO-Aligned Bounding Boxes

**Critical**: All bounding boxes use COCO format `[x, y, width, height]` (not `[x1, y1, x2, y2]`) for LayoutParser compatibility.

```python
from pydantic import BaseModel

class DocumentElement(BaseModel):
    element_type: str  # "image", "table", "figure"
    bbox: list[float]  # [x, y, width, height] in COCO format
    confidence: float
    quality_issues: list[DetectedIssue] = []  # Hybrid IQA
```

See [Schema Documentation](../api/schema.md) for complete Pydantic models.

## Integration Architecture

### Project B Handoff

Project A outputs:
- `DocumentMetadata.json` with routing recommendations
- Corrected page images (300 DPI standardized)
- PDF type classification (image_only/born_digital/hybrid)
- Document Quality Score (DQS) and pre-OCR risk

Project B consumes:
- Uses routing recommendations to select OCR strategy
- Applies full semantic layout detection
- Performs table structure extraction
- Determines reading order

See [OCR Team Handoff](../handoff/OCR_TEAM_HANDOFF_SEMANTIC_FEATURES.md)

## Security Architecture

- **No secrets in code**: All API keys via environment variables
- **Encrypted .env**: GPG-encrypted configuration
- **Signed commits**: All commits must be GPG-signed
- **Dependency scanning**: Bandit, Safety, OSV Scanner
- **Fuzzing**: ClusterFuzzLite integration

See [Security Documentation](../security/codeql-python-scanning-guide.md)

## Related Documentation

- [Project Plan](RAG%20Pipeline/project-a-project-plan.md) - Implementation roadmap
- [RAG Pipeline Overview](RAG%20Pipeline/RAG-pipeline-project-overview.md) - Multi-project architecture
- [Architecture Decision Records](../ADRs/README.md) - Design decision history
- [API Reference](../api/index.md) - Module documentation
- [Testing Strategy](../TESTING_STRATEGY.md) - Quality assurance approach
