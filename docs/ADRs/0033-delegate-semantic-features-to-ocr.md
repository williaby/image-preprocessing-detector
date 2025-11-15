---
title: "ADR-033: Delegate Semantic Document Features to OCR/Processing"
status: Accepted
date: 2025-01-14
deciders:
  - Byron Williams
  - Architecture Team
tags:
  - architecture
  - scope
  - boundaries
  - ocr
  - pipeline
owner: byron_williams
schema_type: knowledge
related_adrs:
  - 0007-hybrid-iqa-approach
  - 0008-multi-stage-pipeline-architecture
  - 0028-document-quality-score-routing
---

## Context

During functional requirements review (v2.2), we identified four requirements that violate the preprocessing/processing architectural boundary:

- **FR-4.11:** Table Structure Extraction (rows, columns, cells)
- **FR-4.12:** Reading Order Prediction (sequential element ordering)
- **FR-4.5:** Footnote Linking (reference markers to footnote text)
- **FR-4.6:** Figure-Caption Linking (semantic associations)

These requirements require **semantic understanding** of document content (cell relationships, reading flow, contextual linking), which belongs in the OCR/processing stage rather than preprocessing.

### The Boundary Test

To determine preprocessing vs. processing scope, we applied this decision criterion:

> **Boundary Test:** "Can this task be performed using only pixel-level analysis without understanding document semantics?"

| Task | Pixel-Level Only? | Classification |
|------|-------------------|----------------|
| Detect table exists (bbox) | ✅ YES | Preprocessing |
| Extract table structure (cells) | ❌ NO | Processing |
| Detect multi-column layout | ✅ YES | Preprocessing |
| Predict reading order | ❌ NO | Processing |
| Detect footnote region | ✅ YES | Preprocessing |
| Link footnote to reference | ❌ NO | Processing |

### Problem Statement

**Original FR-4.11 (Table Structure Extraction):**
- Planned to train ClusterTabNet or Table Transformer on PubTables-1M (Phase 3 Week 8-12)
- **Issue:** Docling already provides table structure extraction using TableFormer (93.6% accuracy)
- **Result:** 4-6 weeks of duplicate work with zero value-add over existing solution

**Original FR-4.12 (Reading Order Prediction):**
- Planned to implement graph-based heuristics or train GNN on DocSynth-300K (Phase 3 Week 7)
- **Issue:** Critical for RAG (5-29% performance impact per OHR-Bench research)
- **Result:** Reading order is consumed by semantic chunking (RAG), not routing decisions

**Original FR-4.5 & FR-4.6 (Linking):**
- Planned to implement semantic linking between footnotes/captions and their targets
- **Issue:** Requires OCR text extraction to perform pattern matching and contextual analysis
- **Result:** Preprocessing cannot perform these tasks without OCR (circular dependency)

### Scope Violation

Our own **FR 1.2 Out-of-Scope** states:
> "Downstream parsing logic (**table-to-JSON**, semantic chunking, vectorization)"

FR-4.11 converts table images → structured JSON (rows/columns/cells) = downstream parsing ❌

---

## Decision

**We delegate semantic document structure extraction to the OCR/Processing team** and redefine preprocessing scope to focus exclusively on:

1. **Physical Quality Assessment** (blur, skew, noise, contrast)
2. **Image Corrections** (deskew, CLAHE, denoising, DPI upscaling)
3. **Layout Detection** (bounding boxes only - WHERE elements are)
4. **Routing Metadata** (DQS scores, complexity indicators)

### Transferred Requirements

| FR ID | Original Scope | New Preprocessing Scope | Transferred to OCR |
|-------|---------------|-------------------------|-------------------|
| **FR-4.11** | Table structure extraction | Table quality assessment + complexity hints | Row/column structure, cell extraction |
| **FR-4.12** | Reading order prediction | Spatial hints (multi-column detection) | Sequential element ordering |
| **FR-4.5** | Footnote linking | Footnote region detection | Reference marker linking |
| **FR-4.6** | Figure-caption linking | Caption/figure detection + proximity hints | Semantic association |

### Updated Architecture

```
┌─────────────────────────────────────────────────┐
│  PREPROCESSING (Image Quality & Routing)        │
│  ─────────────────────────────────────────────  │
│  ✅ Physical Quality:                           │
│     - Blur, skew, noise, contrast detection     │
│     - DPI detection and upscaling (300 DPI)     │
│     - Deskew, CLAHE, denoising corrections      │
│                                                  │
│  ✅ Layout Detection (Bounding Boxes):          │
│     - Tables, images, formulas (WHERE)          │
│     - 11 DocLayNet classes (COCO format)        │
│                                                  │
│  ✅ Routing Metadata:                           │
│     - Document Quality Score (DQS)              │
│     - Complexity indicators                     │
│     - Spatial hints (multi-column, proximity)   │
│                                                  │
│  OUTPUT: Cleaned images + JSON metadata         │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  OCR/PROCESSING (Semantic Extraction)           │
│  ─────────────────────────────────────────────  │
│  ✅ Text Extraction:                            │
│     - OCR (Tesseract, PaddleOCR, Surya)         │
│     - Language detection, confidence scoring    │
│                                                  │
│  ✅ Semantic Structure (NEW - TRANSFERRED):     │
│     - Table structure (Docling TableFormer)     │
│     - Reading order (Surya)                     │
│     - Footnote linking (pattern matching)       │
│     - Figure-caption linking (spatial + text)   │
│                                                  │
│  ✅ Document Understanding:                     │
│     - Semantic chunking for RAG                 │
│     - Entity extraction, hierarchy               │
│                                                  │
│  OUTPUT: Structured JSON (text, tables, chunks) │
└─────────────────────────────────────────────────┘
```

### Scope Boundary Definition

**New Scope Clarification (added to FR 1.2):**

> "Preprocessing detects **WHERE** elements are (bounding boxes, quality issues). OCR/Processing determines **WHAT'S IN** elements (structure, text, relationships)."

---

## Consequences

### Positive

1. **Eliminates Duplicate Work**
   - Docling already provides table structure extraction (93.6% TEDS accuracy)
   - No need to train/maintain separate table structure model
   - **Saved: 4-6 weeks development time, $10-30 GPU training costs**

2. **Clear Architectural Boundary**
   - Preprocessing: Pixel-level analysis only
   - OCR/Processing: Semantic understanding
   - No circular dependencies (preprocessing doesn't need OCR text)

3. **Faster Development Timeline**
   - Phase 3 reduced from 16 weeks → 12-14 weeks
   - Eliminated dataset downloads (DocSynth-300K 113 GB optional)
   - Focused effort on actual preprocessing tasks

4. **Better Tool Selection**
   - OCR team can use pretrained models (TableFormer, Surya)
   - No custom training required for semantic tasks
   - Leverage industry-proven solutions (Docling ecosystem)

5. **RAG Quality Improvement**
   - Reading order prediction in correct pipeline stage (directly impacts RAG chunking)
   - Footnote/caption linking enables better semantic context
   - Table structure enables structured data retrieval

### Negative

1. **Handoff Coordination Required**
   - Created [OCR Team Handoff Document](../handoff/OCR_TEAM_HANDOFF_SEMANTIC_FEATURES.md)
   - JSON schema contract must be maintained between teams
   - Integration testing required across preprocessing → OCR boundary

2. **Preprocessing Metadata Dependency**
   - OCR team relies on preprocessing spatial hints (multi-column, proximity)
   - Bounding box quality impacts OCR's ability to extract structure
   - Requires clear SLA on preprocessing metadata accuracy

3. **Distributed Responsibility**
   - Table handling split: preprocessing detects, OCR extracts structure
   - Reading order split: preprocessing provides spatial hints, OCR orders elements
   - Requires coordination on error handling and validation

4. **Documentation Updates**
   - Updated FR 1.2 (scope boundary clarification)
   - Rewrote FR-4.5, FR-4.6, FR-4.11, FR-4.12 (detection-only scope)
   - Created handoff document with 80+ pages of specifications
   - Updated PROJECT_PLAN.md (removed Phase 3 semantic tasks)

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OCR team unable to integrate tools | Low | High | Handoff doc includes 3 tool options per FR, with pretrained weights |
| Preprocessing spatial hints insufficient | Medium | Medium | Iterative refinement based on OCR team feedback, validate on test documents |
| JSON schema incompatibility | Low | Medium | Schema contract defined in handoff doc, integration tests validate |
| Reading order quality below target | Medium | High | OCR team uses Surya pretrained model (proven on multi-column), fallback to graph heuristics |

---

## Implementation Plan

### Phase 1: Handoff (Week 1)
- [x] Create OCR Team Handoff Document (80+ pages, comprehensive)
- [x] Update FR 1.2 scope boundary clarification
- [x] Rewrite FR-4.5, FR-4.6, FR-4.11, FR-4.12 (detection-only)
- [x] Create ADR-033 (this document)
- [ ] Schedule handoff meeting with OCR team
- [ ] Present handoff document and answer questions

### Phase 2: OCR Integration (Week 1-2)
- [ ] OCR team integrates Docling TableFormer (FR-4.11)
- [ ] OCR team integrates Surya Reading Order (FR-4.12)
- [ ] OCR team implements footnote linking (FR-4.5)
- [ ] OCR team implements figure-caption linking (FR-4.6)

### Phase 3: Validation (Week 3-4)
- [ ] End-to-end pipeline testing (preprocessing → OCR → RAG)
- [ ] Validate on test documents (academic papers, financial reports, legal docs)
- [ ] Benchmark performance (GriTS F1 > 0.85, ROE < 10%, NDCG@5 > 0.77)
- [ ] Iterate on preprocessing spatial hints based on OCR feedback

### Phase 4: Production (Week 5+)
- [ ] Update integration documentation
- [ ] Monitoring and alerting for handoff boundary
- [ ] Performance profiling (latency, throughput)

---

## Alternatives Considered

### Alternative 1: Keep FR-4.11 in Preprocessing (Rejected)

**Pros:**
- Single-team ownership of table processing
- No handoff coordination required

**Cons:**
- Duplicates Docling's TableFormer (93.6% accuracy already proven)
- 4-6 weeks development time with zero value-add
- Violates "preprocessing detects WHERE, OCR extracts WHAT" boundary
- Creates maintenance burden for table structure model

**Decision:** Rejected due to duplicate work and boundary violation

### Alternative 2: Keep FR-4.12 in Preprocessing (Rejected)

**Pros:**
- Preprocessing provides complete layout + reading order metadata
- No OCR dependency for reading order

**Cons:**
- Reading order is consumed by RAG semantic chunking (OCR responsibility)
- Requires 113 GB DocSynth-300K dataset download
- 10-14 days development time vs. 1-2 days integrating Surya pretrained
- Reading order errors have 5-29% RAG impact (should be close to RAG chunking)

**Decision:** Rejected due to misaligned architectural responsibility

### Alternative 3: Hybrid Approach - Preprocessing Provides Basic Reading Order Hints (Partially Accepted)

**Pros:**
- Preprocessing provides spatial hints (multi-column detection, column membership)
- OCR team uses hints for full reading order prediction
- Clear division: preprocessing = spatial analysis, OCR = sequential ordering

**Cons:**
- Requires coordination on spatial hint format
- OCR team depends on preprocessing accuracy

**Decision:** **Accepted** - This is the implemented approach (FR-4.12 redefined as "Layout Spatial Hints")

---

## Validation Criteria

### Preprocessing Team (This System)

**Success Criteria:**
- [ ] Layout detection provides accurate bounding boxes (mAP@.50 > 0.82)
- [ ] Spatial hints accurate (multi-column detection > 95% accuracy)
- [ ] Table quality assessment enables routing (complexity score correlates with OCR difficulty)
- [ ] JSON metadata contract validated (no breaking changes)

**Validation:**
- Test on 100+ documents (academic papers, financial reports, legal docs)
- Measure downstream OCR team's success rate with preprocessing metadata
- Validate DQS routing recommendations align with OCR processing time

### OCR Team (Transferred Responsibilities)

**Success Criteria:**
- [ ] Table structure extraction: GriTS F1 > 0.85, TEDS > 0.90
- [ ] Reading order prediction: ROE < 10% (OHR-Bench), NDCG@5 > 0.77 (RAG)
- [ ] Footnote linking: Accuracy > 0.85
- [ ] Figure-caption linking: Accuracy > 0.80

**Validation:**
- PubTables-1M test split (table structure)
- OHR-Bench dataset (reading order + RAG impact)
- Academic papers (footnotes, captions)

---

## References

### Internal Documents
- [OCR Team Handoff Document](../handoff/OCR_TEAM_HANDOFF_SEMANTIC_FEATURES.md)
- [Functional Requirements v2.2](../requirements/functional_requirements_v2.md)
- [Preprocessing vs Processing Boundary Analysis](../analysis/PREPROCESSING_VS_PROCESSING_BOUNDARY.md)
- [FR-4.11 Boundary Analysis](../analysis/FR_4_11_BOUNDARY_ANALYSIS.md)

### Research Papers
- [OHR-Bench: OCR Hinders RAG](https://arxiv.org/abs/2410.12628) - Reading order impact (5-29% RAG loss)
- [PubTables-1M](https://arxiv.org/abs/2110.00061) - Table structure dataset
- [DocSynth-300K](https://arxiv.org/abs/2410.12628) - Reading order dataset
- [Docling Paper](https://arxiv.org/abs/2408.09869) - TableFormer 98.5% TEDS

### Tools & Datasets
- **Docling TableFormer:** github.com/docling-project/docling (MIT License)
- **Surya Reading Order:** github.com/VikParuchuri/surya (Modified AI Pubs Open Rail-M)
- **Microsoft Table Transformer:** github.com/microsoft/table-transformer (MIT License)
- **PubTables-1M Dataset:** github.com/microsoft/table-transformer (Apache-2.0)
- **OHR-Bench Dataset:** HuggingFace: opendatalab/OHR-Bench (CC-BY-4.0)

---

## Decision Record

**Date:** 2025-01-14
**Status:** Accepted
**Deciders:**
- Byron Williams (Lead Developer, Preprocessing Team)
- [OCR Team Lead - TBD]
- [Project Manager - TBD]

**Decision:**
Delegate semantic document structure extraction (table structure, reading order, footnote/caption linking) to OCR/Processing team. Redefine preprocessing scope to focus on physical quality assessment, image corrections, layout detection (bounding boxes only), and routing metadata.

**Rationale:**
1. Eliminates duplicate work (Docling already provides table structure at 93.6% accuracy)
2. Clarifies architectural boundary (pixel-level vs. semantic understanding)
3. Saves 6-8 weeks development time
4. Enables OCR team to use pretrained models (TableFormer, Surya)
5. Positions reading order prediction close to RAG chunking (where it's consumed)

**Review Date:** 2025-04-14 (90 days after implementation)

---

## Appendix: Cost-Benefit Analysis

### Preprocessing Team (Before Transfer)

**Planned Development (Phase 3):**
- FR-4.11 (Table Structure): 4-6 weeks, $10-30 GPU training
- FR-4.12 (Reading Order): 10-14 days, 113 GB dataset download
- FR-4.5 (Footnote Linking): 3-5 days development
- FR-4.6 (Figure-Caption Linking): 2-3 days development
- **Total:** 8-10 weeks, $500-1,000 costs

**Actual Value-Add:** ZERO (Docling already provides table structure, Surya provides reading order)

### OCR Team (After Transfer)

**Integration Effort:**
- FR-4.11 (Docling TableFormer): 2-3 days integration
- FR-4.12 (Surya Reading Order): 1-2 days integration
- FR-4.5 (Footnote Linking): 2-3 days pattern matching implementation
- FR-4.6 (Figure-Caption Linking): 1-2 days spatial + text matching
- **Total:** 6-10 days integration

**Training Costs:** $0 (pretrained models)

**Value-Add:** HIGH (direct RAG quality improvement, leverages proven models)

### Net Savings

- **Time Saved:** 6-8 weeks
- **Cost Saved:** $500-1,000 (GPU training avoided)
- **Storage Saved:** 113 GB (DocSynth-300K optional)
- **Maintenance Reduced:** No custom model retraining required

---

**END OF ADR-033**
