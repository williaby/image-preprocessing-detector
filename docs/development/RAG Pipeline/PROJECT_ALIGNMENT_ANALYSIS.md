---
schema_type: common
title: "Project Alignment Analysis"
description: "Gap analysis and alignment roadmap for RAG Pipeline Project A implementation"
tags: [architecture, roadmap, documentation, planning]
status: published
owner: "docs-team"
purpose: "Provide comprehensive gap analysis between current implementation and RAG Pipeline vision with actionable roadmap."
---

**Date:** 2025-11-15
**Status:** Analysis Complete
**Priority:** High - Critical for preventing scope creep and architectural drift

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

#### 2. PDF Type Classification
**Gap:** Not implemented
**Vision Requirement:**
- Classify PDFs as: `image_only`, `born_digital`, `hybrid`
- Required field in DocumentMetadata schema

**Impact:**
- Project B cannot optimize OCR engine selection
- Missing critical routing metadata

**Implementation Effort:** Medium - can use PyMuPDF text extraction + embedded image inspection

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

**Document Status:** Final
**Next Review:** After Phase 1 completion
**Owner:** Project A Team
**Related Documents:**
- [RAG-pipeline-project-overview.md](RAG-pipeline-project-overview.md)
- [Project_A_F_NF.md](Project_A_F_NF.md)
- [project-a-project-plan.md](project-a-project-plan.md)
- [document_metadata.schema.json](document_metadata.schema.json)
