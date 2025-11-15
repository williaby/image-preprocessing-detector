# Project Alignment Analysis: Current Implementation vs. RAG Pipeline Vision

**Date:** 2025-11-15
**Status:** Analysis Complete
**Priority:** High - Critical for preventing scope creep and architectural drift

---

## Executive Summary

The RAG Pipeline documentation provides a clear four-project architecture where this repository (**image_detection**) is **Project A** - the preprocessing and IQA gateway. While the current implementation has the correct general scope, there are critical gaps in functionality and schema alignment that need to be addressed to prevent confusion and ensure clean handoffs to downstream projects.

**Key Finding:** Current implementation is ~60% aligned with Project A vision. Major gaps exist in ML IQA models, routing metadata, and schema structure.

---

## Architecture Overview

### The Four-Project Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG DOCUMENT PIPELINE                         │
└─────────────────────────────────────────────────────────────────┘

Project A (THIS REPO)          Project B                Project C                Project D
image_detection          →     ocr-orchestrator    →    fusion-trust        →    vector-indexer
─────────────────────          ────────────────         ─────────────            ──────────────
• IQA & Corrections            • Layout Detection       • OCR Fusion            • Embeddings
• Text Gate                    • Reading Order          • Hallucination Det.    • Vector DB
• DQS Calculation              • Multi-Engine OCR       • Trust Scoring         • Metadata
• Routing Metadata             • Paragraph Segment      • RAG Chunking          • Indexing

OUTPUT:                        OUTPUT:                  OUTPUT:                 OUTPUT:
DocumentMetadata.json          OCRDocument.json         FusedDocument.json      Vector DB
+ Corrected Images                                      + RAGChunk.json         Entries
```

---

## Current Implementation Status

### ✅ Correctly Implemented (Aligned with Project A)

| Component | Status | Notes |
|-----------|--------|-------|
| Classical IQA | ✅ Complete | Blur, skew, noise, contrast detection implemented |
| Text Detection Gate | ✅ Complete | Fast ensemble heuristics for routing |
| Basic Corrections | ✅ Complete | Deskew, CLAHE, sharpening, denoising with guardrails |
| DPI Upscaling | ✅ Complete | Phase 1B - proven implementation from data_ingestor |
| Transform History | ✅ Complete | Audit trail for all corrections |
| COCO Bounding Boxes | ✅ Complete | Proper format for downstream compatibility |
| Scope Boundaries | ✅ Correct | No OCR, no full layout detection, no chunking |

### ❌ Critical Missing Components (Required for Project A)

#### 1. Teacher-Student ML IQA Models
**Gap:** No ML-based IQA implementation
**Vision Requirement:**
- ResNet-50 teacher model (high-capacity reference)
- ResNet-18 student model (production default)
- Uncertainty gating for teacher escalation
- Device-priority execution (local GPU → CPU → Modal GPU)

**Impact:**
- Cannot provide learned quality scores (overall_quality, sharpness_score, color_fidelity_score)
- Missing key routing signal for Project B
- No teacher fallback for high-risk documents

**Implementation Phase:** Phase 2-3 per project plan

---

#### 2. PDF Type Classification
**Gap:** Not implemented
**Vision Requirement:**
- Classify PDFs as: `image_only`, `born_digital`, `hybrid`
- Required field in DocumentMetadata schema

**Impact:**
- Project B cannot optimize OCR engine selection
- Missing critical routing metadata

**Implementation Effort:** Medium - can use PyMuPDF text extraction + embedded image inspection

---

#### 3. Coarse Layout Classification
**Gap:** Partially implemented via DocumentElement, but missing page-level summary
**Vision Requirement:**
```json
"page_layout_summary": [
  {
    "page_index": 0,
    "layout_type": "multi_column",  // single_column | multi_column | three_column | complex | unknown
    "has_tables": true,
    "has_figures": true,
    "has_dense_math": false,
    "has_handwriting": false,
    "page_attributes": {
      "fuzzy_scan": false,
      "watermark": false,
      "colorful_background": false
    }
  }
]
```

**Current State:**
- Has `DocumentElement` with per-element categories
- Missing page-level coarse classification
- Missing OmniDocBench-style attributes

**Impact:**
- Project B cannot route to appropriate OCR profiles
- Missing lightweight layout indicators for routing

**Implementation Effort:** Medium - requires lightweight classifier or heuristics

---

#### 4. DQS (Document Quality Score)
**Gap:** Not calculated
**Vision Requirement:**
```json
"dqs": {
  "degradation_score": 0.75,      // 0-1, based on blur/noise/skew/illumination
  "structural_complexity_score": 0.60  // 0-1, based on layout complexity
}
```

**Impact:**
- No holistic quality signal for downstream projects
- Cannot distinguish pristine docs from degraded scans
- Missing key routing input

**Implementation Effort:** Low - aggregate existing IQA metrics

---

#### 5. Pre-OCR Risk Score
**Gap:** Not calculated
**Vision Requirement:**
```json
"pre_ocr_risk": 0.35  // 0-1, aggregated risk that OCR will struggle
```

**Impact:**
- Project B cannot adjust confidence thresholds
- No early warning for problematic documents

**Implementation Effort:** Low - combine DQS + IQA metrics

---

#### 6. OCR Routing Recommendation
**Gap:** Not implemented
**Vision Requirement:**
```json
"ocr_routing_recommendation": "ocr_advanced"
// Enum: ocr_fast | ocr_advanced | vision_simple | vision_structured
```

**Impact:**
- Project B must rediscover what this project already knows
- Wasted computation, potential routing errors

**Implementation Effort:** Low - rules-based from DQS + layout + risk

---

#### 7. Device-Priority Execution Logic
**Gap:** Not implemented
**Vision Requirement:**
- Explicit device probing (GPU availability, utilization, Modal quota)
- Priority rules: Local GPU → Local CPU → Modal GPU
- Budget constraints and logging

**Impact:**
- Cannot optimize inference costs
- No teacher fallback logic
- Missing performance optimization layer

**Implementation Effort:** High - requires Modal integration, GPU probing, budget tracking

---

## Schema Alignment Issues

### Current Schema (`schema.py`)

```python
class DocumentMetadata:
    document_id: str
    file_name: str
    source_mime: str
    num_pages: int
    upscaling: dict | None       # ✅ Good addition for Phase 1B
    processing_version: ProcessingVersion
    pages: list[PageMetadata]

    # ❌ MISSING:
    # - pdf_type
    # - languages
    # - has_non_latin
    # - pre_ocr_risk
    # - dqs
    # - ocr_routing_recommendation
    # - page_layout_summary
```

### Vision Schema (`document_metadata.schema.json`)

**Required Fields Not Present:**
1. `pdf_type` - Critical for OCR engine selection
2. `languages` - Array of BCP-47/ISO 639-1 codes
3. `has_non_latin` - Boolean for script detection
4. `pre_ocr_risk` - Float 0-1
5. `dqs.degradation_score` - Float 0-1
6. `dqs.structural_complexity_score` - Float 0-1
7. `ocr_routing_recommendation` - Enum
8. `page_layout_summary` - Array of page-level layout metadata

**Current Fields Not in Vision:**
1. `detected_issues` - Per-page quality issues (may be internal only)
2. `planned_actions` - Per-page correction plans (may be internal only)
3. `elements` - Per-element detection (overlaps with Project B's responsibility)

**Concern:** Current schema appears to leak into Project B's domain with per-element layout detection.

---

## Responsibility Boundary Analysis

### Clear Boundaries (No Confusion)

| Responsibility | Owner | Current Status |
|----------------|-------|----------------|
| OCR Execution | Project B | ✅ Not in scope |
| Reading Order | Project B | ✅ Not in scope |
| Multi-Engine Fusion | Project C | ✅ Not in scope |
| RAG Chunking | Project C | ✅ Not in scope |
| Embeddings | Project D | ✅ Not in scope |

### Boundary Confusion Areas

| Responsibility | Owner | Current Concern |
|----------------|-------|-----------------|
| **Coarse Layout** (page-level) | Project A | ⚠️ Missing from current impl |
| **Detailed Layout** (element bboxes) | Project B | ⚠️ Current schema has `DocumentElement` - may be overstepping |
| **IQA on Elements** | Unclear | ⚠️ Current schema has `quality_issues` per element (hybrid IQA approach) |

**Analysis:** The current `DocumentElement` with per-element IQA suggests Project A is doing element-level quality assessment (hybrid IQA). This may be intentional for the "text-detected path" where layout detection identifies embedded images for per-element IQA. However, this needs clarification:

**Option 1:** Project A does lightweight element detection ONLY for IQA purposes (assess quality of embedded images in text docs)
**Option 2:** Project A does NO element detection - Project B handles all layout, Project A only provides page-level signals

**Recommendation:** Clarify with architecture decision record whether hybrid IQA (per-element quality in text documents) is Project A's responsibility or should be deferred to Project B.

---

## Data Handoff Analysis

### Project A → Project B Handoff

**Vision Requirements:**
- Corrected page images (standardized to 300 DPI)
- `DocumentMetadata.json` with routing metadata

**Current Gaps:**
- ❌ Missing routing metadata (pdf_type, dqs, pre_ocr_risk, ocr_routing_recommendation)
- ❌ Missing page_layout_summary
- ⚠️ Unclear if corrected images are output to filesystem or only in-memory

**Impact:** Project B cannot make intelligent decisions without routing metadata.

---

## Recommended Actions

### Phase 1: Immediate Schema Alignment (Week 1)

**Priority: CRITICAL**

1. **Update `schema.py` to match canonical vision:**
   ```python
   class DocumentMetadata:
       # Add required fields:
       pdf_type: Literal["image_only", "born_digital", "hybrid"] | None
       languages: list[str]  # BCP-47 codes
       has_non_latin: bool
       pre_ocr_risk: float  # 0-1
       dqs: DQS  # New model with degradation_score + structural_complexity_score
       ocr_routing_recommendation: Literal["ocr_fast", "ocr_advanced", "vision_simple", "vision_structured"]
       page_layout_summary: list[PageLayoutSummary]  # New model
   ```

2. **Create new Pydantic models:**
   - `DQS` (degradation_score, structural_complexity_score)
   - `PageLayoutSummary` (layout_type, has_tables, has_figures, has_dense_math, has_handwriting, page_attributes)
   - `PageAttributes` (fuzzy_scan, watermark, colorful_background)

3. **Decide on `DocumentElement` scope:**
   - If hybrid IQA is in scope: Document as explicit Project A responsibility
   - If out of scope: Remove or mark as experimental/Phase 2+

4. **Add schema versioning:**
   - Ensure `schema_version` field matches canonical specs
   - Create migration path for existing outputs

**Deliverable:** Updated `schema.py` matching `document_metadata.schema.json`

---

### Phase 2: Implement Missing Core Components (Weeks 2-4)

**Priority: HIGH**

1. **PDF Type Classification** (Week 2)
   - Use PyMuPDF text extraction
   - Detect embedded images
   - Classify as image_only/born_digital/hybrid
   - ~99.5% accuracy target

2. **Coarse Layout Classification** (Week 2-3)
   - Implement lightweight page-level classifier
   - Output: layout_type (single/multi/three_column/complex)
   - Detect: has_tables, has_figures, has_dense_math, has_handwriting
   - OmniDocBench-style page attributes
   - Can use heuristics initially, ML model later

3. **DQS Calculation** (Week 3)
   - Aggregate classical IQA metrics → degradation_score
   - Aggregate layout complexity → structural_complexity_score
   - Tunable weighting via config

4. **Pre-OCR Risk Score** (Week 3)
   - Combine DQS + IQA + layout attributes
   - Output single 0-1 risk score

5. **Routing Recommendation Logic** (Week 4)
   - Rules-based using DQS + pdf_type + layout + handwriting flags
   - Output: ocr_routing_recommendation enum
   - Document routing rationale

**Deliverable:** Complete routing metadata pipeline

---

### Phase 3: ML IQA Implementation (Weeks 5-9)

**Priority: HIGH (Critical for production quality)**

1. **Dataset Pipeline** (Week 5)
   - Ingest OmniDocBench, DocLayNet, etc.
   - Synthetic augmentation
   - Difficulty stratification

2. **ResNet-50 Teacher Training** (Weeks 5-7)
   - Multi-head architecture (overall, sharpness, color_fidelity)
   - Heavy augmentations
   - Validation on OHR-Bench
   - Export to ONNX + TorchScript

3. **ResNet-18 Student Distillation** (Weeks 7-8)
   - Knowledge distillation from teacher
   - Benchmark CPU vs GPU latency
   - Target: student correlation vs teacher ≥ 0.9

4. **Uncertainty Gating Logic** (Week 8)
   - Softmax entropy calculation
   - Top-2 logit margin
   - Discrepancy vs classical IQA
   - Teacher escalation manager

5. **Integration** (Week 9)
   - Update schema with learned_quality fields
   - Wire into DQS calculation
   - Add to routing logic

**Deliverable:** Production-ready ML IQA with teacher fallback

---

### Phase 4: Device-Priority Execution (Week 9)

**Priority: MEDIUM (Cost optimization)**

1. **Device Probing**
   - GPU availability detection
   - Utilization monitoring
   - Modal quota checking

2. **Priority Rules**
   - Local GPU → CPU → Modal GPU
   - Budget constraints
   - Teacher CPU blocking (production mode)

3. **Logging & Metrics**
   - Device selection decisions
   - Teacher escalation reasons
   - Cost tracking

**Deliverable:** Cost-optimized inference pipeline

---

### Phase 5: Documentation & Boundaries (Week 10)

**Priority: HIGH (Prevent future confusion)**

1. **Update CLAUDE.md**
   - Add explicit "This is Project A" section
   - Reference RAG Pipeline overview
   - Document what Projects B/C/D will handle
   - Add "Project Boundaries" warning section

2. **Create Architecture Decision Records**
   - ADR-001: Hybrid IQA approach (per-element quality for embedded images)
   - ADR-002: Schema alignment with RAG pipeline vision
   - ADR-003: Device-priority execution strategy

3. **Update README**
   - Add four-project architecture diagram
   - Link to RAG Pipeline docs
   - Clarify handoff to Project B

4. **Create Integration Guide**
   - How Project B should consume DocumentMetadata.json
   - Expected file structure for handoff
   - Validation procedures

**Deliverable:** Crystal-clear project boundaries and integration docs

---

## Risk Assessment

### High Risk Areas

1. **Schema Drift** (HIGH)
   - Current schema diverging from canonical vision
   - Will cause integration problems with future Projects B/C/D
   - **Mitigation:** Immediate schema alignment in Phase 1

2. **Scope Creep into Project B** (MEDIUM)
   - `DocumentElement` detection may overlap with Project B layout
   - **Mitigation:** Clear ADR on hybrid IQA boundaries

3. **Missing Routing Metadata** (HIGH)
   - Project B cannot make intelligent decisions
   - **Mitigation:** Implement Phase 2 components quickly

### Low Risk Areas

1. **Classical IQA** (LOW) - Well implemented, stable
2. **Text Gate** (LOW) - Working as designed
3. **Corrections** (LOW) - Guardrails in place

---

## Success Metrics

### Schema Alignment (Target: 100%)
- [ ] All required fields from `document_metadata.schema.json` present
- [ ] No extraneous fields that confuse Project B
- [ ] Schema versioning implemented

### Functionality Alignment (Target: 95%)
- [ ] PDF type classification (99.5% accuracy)
- [ ] Coarse layout classification (90%+ accuracy)
- [ ] DQS calculation (correlates with OCR success)
- [ ] Routing recommendations (measurable improvement in Project B)
- [ ] ML IQA (student correlation ≥ 0.9 vs teacher)

### Documentation Clarity (Target: 100%)
- [ ] CLAUDE.md explicitly states "This is Project A"
- [ ] Project boundaries documented in ADRs
- [ ] Integration guide for Project B handoff
- [ ] No confusion in future Claude Code sessions

---

## Timeline Summary

| Phase | Duration | Priority | Dependencies |
|-------|----------|----------|--------------|
| Phase 1: Schema Alignment | Week 1 | CRITICAL | None |
| Phase 2: Core Components | Weeks 2-4 | HIGH | Phase 1 |
| Phase 3: ML IQA | Weeks 5-9 | HIGH | Phase 2 |
| Phase 4: Device Priority | Week 9 | MEDIUM | Phase 3 |
| Phase 5: Documentation | Week 10 | HIGH | Phases 1-4 |

**Total Duration:** ~10 weeks to full alignment

**Quick Wins (Weeks 1-4):**
- Schema alignment
- PDF type classification
- DQS + routing metadata
- Clear project boundaries

---

## Conclusion

The RAG Pipeline vision provides **excellent architectural clarity** that prevents the common pitfall of monolithic "do everything" document processing systems. The current implementation is on the right track but needs:

1. **Immediate schema alignment** to prevent integration debt
2. **Core routing metadata** to enable Project B's intelligent decisions
3. **Clear boundary documentation** to prevent scope creep
4. **ML IQA implementation** for production-quality assessment

**Bottom Line:** This analysis provides a clear roadmap from 60% alignment to 95%+ alignment with the canonical vision. Following this plan will ensure clean handoffs to Projects B/C/D and prevent architectural drift.

---

**Document Status:** Final
**Next Review:** After Phase 1 completion
**Owner:** Project A Team
**Related Documents:**
- [RAG-pipeline-project-overview.md](RAG-pipeline-project-overview.md)
- [Project_A_F_NF.md](Project_A_F_NF.md)
- [project-a-project-plan.md](project-a-project-plan.md)
- [document_metadata.schema.json](document_metadata.schema.json)
