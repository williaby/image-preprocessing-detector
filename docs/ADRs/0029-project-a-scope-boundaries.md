---
schema_type: common
title: "ADR-029: Project A Scope Boundaries in RAG Pipeline"
description: "Define clear boundaries between Project A (preprocessing/IQA) and downstream
  Projects B/C/D to prevent scope creep and architectural drift"
tags:
- adr
- architecture
- scope
- boundaries
- rag_pipeline
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Establish explicit scope boundaries to prevent Project A from overlapping
  with OCR orchestration (B), fusion/trust (C), or vector indexing (D)."
---

**Status**: Accepted
**Date**: 2025-11-15
**Deciders**: Byron Williams
**Related**:
- [ADR-007: Hybrid IQA Approach](0007-hybrid-iqa-approach.md)
- [ADR-008: Multi-Stage Pipeline Architecture](0008-multi-stage-pipeline-architecture.md)
- [ADR-015: YOLOv8 Layout Detection](0015-yolov8-layout-detection.md)
- [Project Alignment Analysis](../development/RAG%20Pipeline/PROJECT_ALIGNMENT_ANALYSIS.md)
- [Project A F&NF Requirements](../development/RAG%20Pipeline/Project_A_F_NF.md)

## Context

The **Image Preprocessing Detector** (this repository) is part of a four-project RAG document pipeline:

```
Project A              Project B            Project C           Project D
image_detection   →    ocr-orchestrator →   fusion-trust   →    vector-indexer
───────────────        ────────────────     ─────────────       ──────────────
• IQA & Corrections    • Layout Detection   • OCR Fusion        • Embeddings
• Text Gate            • Reading Order      • Hallucination     • Vector DB
• DQS Calculation      • Multi-Engine OCR   • Trust Scoring     • Metadata
• Routing Metadata     • Paragraph Segment  • RAG Chunking      • Indexing
```

**Problem**: Without clear boundaries, Project A risks:
1. **Scope creep**: Building features that belong in Projects B/C/D
2. **Schema drift**: Current schema includes `DocumentElement` and per-element IQA, which may overlap with Project B's semantic layout detection
3. **Duplicate computation**: Project A and Project B both detecting layout independently
4. **Integration friction**: Unclear handoff contracts lead to impedance mismatches

**Critical Questions**:
- Where does "image quality assessment" end and "semantic layout detection" begin?
- Should Project A detect document elements (tables, figures, text blocks)?
- What metadata must Project A provide for Project B to make intelligent routing decisions?
- What should Project A explicitly **NOT** do?

## Decision

**Project A is the preprocessing and IQA gateway. Its responsibility is to prepare clean images and routing metadata, NOT to perform semantic understanding.**

### In Scope (MUST DO)

1. **Document Ingestion & Rendering**
   - Accept PDF, PNG, JPEG, TIFF, BMP inputs
   - Render PDFs to standardized 300 DPI page images
   - Classify PDF type: `image_only`, `born_digital`, `hybrid`
   - Detect and upscale low-resolution inputs (< 300 DPI)

2. **Image Quality Assessment (IQA)**
   - **Classical IQA**: Blur (Laplacian), noise (wavelet), skew (Hough), contrast, illumination, JPEG artifacts
   - **ML IQA**: ResNet teacher-student multi-head classification (blur, noise, skew, illumination, compression)
   - **Per-page quality scores**: Quantitative metrics for each quality dimension

3. **Image Corrections with Guardrails**
   - Deskew, denoise, CLAHE contrast enhancement, illumination correction
   - Mild dewarping/perspective correction
   - **Do-no-harm guardrails**: Roll back corrections that degrade quality metrics
   - Transform history tracking for audit trail

4. **Layout-Lite Detection**
   - **Coarse page-level attributes only**:
     - Layout type: `single_column`, `multi_column`, `three_column`, `complex`
     - Block presence: `has_tables`, `has_figures`, `has_dense_math`, `has_handwriting`
     - Structural complexity score (0-1)
   - **Purpose**: Routing metadata for Project B, NOT semantic understanding
   - **Technology**: Lightweight YOLOv8-nano for coarse regions OR heuristic-based classifiers
   - **NOT included**: Bounding boxes, element extraction, reading order, semantic labels

5. **Document Quality Score (DQS)**
   - `degradation_score` (0-1): Aggregation of blur, noise, skew, illumination metrics
   - `structural_complexity_score` (0-1): Aggregation of layout-lite attributes
   - Single holistic quality signal for downstream routing

6. **Pre-OCR Risk Score**
   - Single 0-1 score combining DQS, IQA, and layout attributes
   - Predicts likelihood of OCR failure
   - Used for teacher escalation and routing decisions

7. **OCR Routing Recommendation**
   - Enum: `ocr_fast` | `ocr_advanced` | `vision_simple` | `vision_structured`
   - Rules-based logic using:
     - DQS + pre-OCR risk
     - PDF type
     - Layout-lite attributes (handwriting, complexity, tables)
   - **Purpose**: Inform Project B which OCR engine(s) to use

8. **Output to Project B**
   - Corrected page images (300 DPI, standardized color space)
   - `DocumentMetadata.json` with:
     - PDF type, language hints, page count
     - Per-page IQA metrics (classical + ML)
     - Layout-lite attributes
     - DQS, pre-OCR risk, routing recommendation
     - Transform history

### Out of Scope (MUST NOT DO)

1. **Semantic Layout Detection**
   - ❌ Full DocLayNet-style 11+ class layout (title, caption, header, footer, paragraph, list, etc.)
   - ❌ Reading order prediction
   - ❌ Paragraph segmentation
   - ❌ Table structure extraction (rows, columns, cells)
   - **Rationale**: This is Project B's responsibility using LayoutLM/Donut/Nougat

2. **Text Recognition & OCR**
   - ❌ Any form of OCR (Tesseract, EasyOCR, PaddleOCR, etc.)
   - ❌ Text extraction (except for PDF type classification using PyMuPDF)
   - ❌ Language detection beyond coarse hints
   - **Rationale**: Project B orchestrates multi-engine OCR

3. **OCR Fusion & Trust Scoring**
   - ❌ Combining outputs from multiple OCR engines
   - ❌ Hallucination detection
   - ❌ Confidence scoring for OCR outputs
   - **Rationale**: This is Project C's responsibility

4. **RAG Chunking & Embedding**
   - ❌ Semantic chunking of text
   - ❌ Generating embeddings
   - ❌ Vector database operations
   - **Rationale**: This is Project D's responsibility

5. **End-to-End RAG Evaluation**
   - ❌ Measuring retrieval accuracy (Recall@K, MRR)
   - ❌ Question-answering metrics
   - **Rationale**: This is evaluated at the pipeline level, not in Project A

### Boundary Cases (CLARIFICATIONS)

**Q: Should Project A detect handwriting?**
- ✅ **YES**: Coarse page-level flag (`has_handwriting: bool`)
- ❌ **NO**: Fine-grained handwriting transcription (Project B)

**Q: Should Project A detect tables?**
- ✅ **YES**: Coarse presence flag (`has_tables: bool`)
- ❌ **NO**: Table bounding boxes, structure extraction, cell detection (Project B)

**Q: Should Project A detect formulas?**
- ✅ **YES**: Coarse density flag (`has_dense_math: bool`)
- ❌ **NO**: Formula parsing or LaTeX generation (Project B with Nougat/Mathpix)

**Q: Should Project A output bounding boxes for elements?**
- ❌ **NO** (changed from earlier design):
  - Original design included `DocumentElement.bbox` for per-element IQA
  - **NEW**: Layout-lite provides page-level attributes only, no bounding boxes
  - **Rationale**: Bounding boxes belong to semantic layout (Project B)
  - **Exception**: Internal use for hybrid IQA research is acceptable, but not in production schema

**Q: Should Project A detect language?**
- ✅ **YES**: Coarse hints (e.g., `languages: ["en"]`, `has_non_latin: false`)
- ❌ **NO**: Fine-grained language spans or script detection (Project B with langdetect)

## Hybrid IQA Boundary Clarification

**Context**: [ADR-007 (Hybrid IQA)](0007-hybrid-iqa-approach.md) proposed per-element IQA for embedded images in text documents.

**Refined Position**:
- **Research Phase**: Per-element IQA is acceptable for exploring whether embedded images need different quality thresholds than full-page IQA
- **Production Phase 1**: Use **layout-lite page-level attributes** only
  - Example: `has_figures: true` → adjust IQA thresholds globally for that page
  - No element-level bounding boxes in production schema
- **Future (Phase 3+)**: If per-element IQA proves critical:
  - Revisit boundary with Project B
  - Potentially add coarse element bounding boxes to layout-lite (NOT semantic labels)

**Current Status**: Project A uses page-level IQA only. Element-level detection deferred to Project B.

## Consequences

### Positive

1. **Clear ownership**: Each project has well-defined responsibilities, reducing duplication
2. **Prevents scope creep**: Project A team can reject features that belong in B/C/D
3. **Simpler schema**: Removing `DocumentElement` and per-element IQA reduces complexity
4. **Faster handoff**: Project A outputs only what Project B needs for routing decisions
5. **Easier testing**: Project A can validate IQA and corrections without needing OCR ground truth
6. **Better integration**: Clear contracts reduce impedance mismatches between projects

### Negative

1. **Potential inefficiency**: Project A and Project B may both run layout detection models
   - **Mitigation**: Layout-lite uses lightweight YOLOv8-nano (< 10ms), while Project B uses full LayoutLM/Donut
2. **Deferred optimization**: Per-element IQA may improve quality but is deferred
   - **Mitigation**: Revisit in Phase 3 if evidence shows page-level IQA insufficient
3. **Routing accuracy risk**: Coarse layout-lite may miss nuances that full layout would catch
   - **Mitigation**: Iterate on layout-lite attributes based on Project B feedback

### Neutral

1. **Dependency on Project B**: Project A cannot validate OCR quality directly (relies on Project B telemetry)
2. **Schema evolution**: May need to add new layout-lite attributes as routing needs evolve

## Handoff Contract (Project A → Project B)

### Required Outputs

**Files**:
1. `<document_id>_page_NNN.png` - Corrected page images (300 DPI, RGB)
2. `<document_id>_metadata.json` - DocumentMetadata schema

**DocumentMetadata.json Fields** (minimum):
```json
{
  "document_id": "string",
  "file_name": "string",
  "pdf_type": "image_only | born_digital | hybrid",
  "num_pages": "int",
  "languages": ["en"],
  "has_non_latin": false,
  "dqs": {
    "degradation_score": 0.75,
    "structural_complexity_score": 0.60
  },
  "pre_ocr_risk": 0.40,
  "ocr_routing_recommendation": "ocr_advanced",
  "pages": [
    {
      "page_number": 1,
      "layout_type": "multi_column",
      "has_tables": true,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": false,
      "structural_complexity": 0.65,
      "iqa_classical": { "blur": 0.15, "noise": 0.10, ... },
      "iqa_ml": { "blur": 0.18, "noise": 0.12, ... },
      "transforms_applied": ["deskew", "clahe"]
    }
  ]
}
```

### Forbidden Outputs

Project A **MUST NOT** output:
- OCR text or bounding boxes
- Reading order
- Semantic element labels (title, caption, paragraph, etc.)
- Table cell structure
- Embeddings or vectors

## Implementation Roadmap

**Phase 1 (Weeks 1-2)**: Schema Alignment
- [ ] Remove `DocumentElement` class (or mark internal-only)
- [ ] Add `pdf_type`, `languages`, `has_non_latin` to DocumentMetadata
- [ ] Add `dqs`, `pre_ocr_risk`, `ocr_routing_recommendation` fields
- [ ] Add layout-lite attributes to PageMetadata

**Phase 2 (Weeks 2-4)**: Core Components
- [ ] Implement PDF type classification (PyMuPDF text extraction)
- [ ] Implement layout-lite classifier (YOLOv8-nano or heuristics)
- [ ] Implement DQS calculation (aggregate IQA metrics)
- [ ] Implement pre-OCR risk score
- [ ] Implement routing recommendation logic

**Phase 3 (Weeks 5-9)**: ML IQA
- [ ] Train ResNet-50 teacher (page-level only)
- [ ] Distill ResNet-18 student
- [ ] Integrate ML IQA into pipeline

**Phase 4 (Week 10)**: Validation & Documentation
- [ ] Document handoff contract with Project B
- [ ] Create integration tests for schema compliance
- [ ] Benchmark end-to-end pipeline

## Alternatives Considered

### Alternative 1: Full Layout Detection in Project A

**Approach**: Project A runs full DocLayNet-style layout detection and passes bounding boxes to Project B

**Pros**:
- Project B can skip layout detection entirely
- Single source of truth for layout

**Cons**:
- Massive scope creep (doubles Project A complexity)
- Project A team must maintain layout model training/tuning
- Tight coupling: layout model changes require Project A redeployment
- **REJECTED**: Violates separation of concerns

### Alternative 2: No Layout Information in Project A

**Approach**: Project A outputs only IQA metrics, zero layout information

**Pros**:
- Simplest Project A design
- Clearest boundary

**Cons**:
- Project B must rediscover layout for routing (e.g., handwriting detection)
- Project A cannot compute meaningful routing recommendations
- **REJECTED**: Insufficient metadata for intelligent routing

### Alternative 3: Shared Layout Service

**Approach**: Both Project A and Project B call a shared layout microservice

**Pros**:
- Single layout model, no duplication

**Cons**:
- Adds operational complexity (new service to deploy)
- Latency overhead (network calls)
- Project A still needs coarse layout for DQS calculation
- **REJECTED**: Premature optimization, added complexity not justified

## Risk Mitigation

1. **Risk**: Layout-lite attributes insufficient for routing
   - **Mitigation**: Iterate based on Project B feedback, add new attributes as needed
   - **Monitoring**: Track routing decision accuracy and OCR failure rates

2. **Risk**: Duplicate computation (Project A and B both run layout models)
   - **Mitigation**: Use lightweight models in Project A (YOLOv8-nano < 10ms), full models in Project B
   - **Monitoring**: Measure end-to-end pipeline latency, optimize if bottleneck found

3. **Risk**: Schema drift over time
   - **Mitigation**: Establish formal schema review process before adding new fields
   - **Governance**: Require ADR for any new cross-project metadata fields

4. **Risk**: Per-element IQA proves critical later
   - **Mitigation**: Deferred to Phase 3, revisit with data-driven evidence
   - **Decision gate**: Require A/B test showing >5% OCR accuracy improvement before implementing

## References

- [Project Alignment Analysis](../development/RAG%20Pipeline/PROJECT_ALIGNMENT_ANALYSIS.md)
- [Project A F&NF Requirements](../development/RAG%20Pipeline/Project_A_F_NF.md)
- [ADR-007: Hybrid IQA Approach](0007-hybrid-iqa-approach.md)
- [ADR-008: Multi-Stage Pipeline Architecture](0008-multi-stage-pipeline-architecture.md)
- [RAG Pipeline Project Overview](../development/RAG%20Pipeline/RAG-pipeline-project-overview.md)
