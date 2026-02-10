---
schema_type: common
title: "Architecture Documentation Improvement Plan"
description: "Comprehensive plan for addressing documentation gaps, inconsistencies,
  and standardization across the three-level architecture hierarchy"
tags:
- architecture
- documentation
- improvement_plan
- action_items
status: draft
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: Documentation for Architecture Documentation Improvement Plan.
---
**Status**: 🟡 Partially Superseded
**Priority**: High
**Target Completion**: 6 weeks
**Multi-Model Review Date**: 2025-01-16

> **Architecture Migration Note**: This improvement plan was created before the migration from ResNet-50/18 teacher-student to MobileNetV4-Conv-S + SigLIP 2 NAFlex multi-task pipeline. Example code snippets below reference the old architecture. The actual documentation has been updated to reflect the new pipeline. See [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) for current architecture.
**Reviewers**: Gemini 3 Pro, GPT-5.1, DeepSeek R1

---

## Executive Summary

This document tracks improvements to the three-level architecture documentation hierarchy (Level 0: Pipeline, Level 1: Project, Level 2: Workstreams) based on a comprehensive multi-model AI evaluation. The documentation is **structurally sound** with strong cross-level consistency, but requires:

1. **Immediate fixes** to file path mismatches and deprecated content
2. **Enrichment** of "legacy" workstream documentation (Production Runtime, Model Training)
3. **Standardization** of "Integration & Boundaries" sections across all Level 2 docs
4. **Targeted Level 3** documentation for complex subsystems (Data Prep, Production Runtime, Monitoring)

**Overall Assessment**: 8-9/10 (High confidence)
**Key Strength**: Exceptional "Level 2.5" documentation for newer workstreams (Data Prep, Monitoring, Model Arena)
**Key Gap**: Production Runtime (15,000+ LOC) has minimal Level 2 narrative

---

## Document Hierarchy Overview

```
docs/architecture/diagrams/
├── level-0/
│   └── index.md                          # ✅ Complete: RAG pipeline (6 projects)
├── level-1/
│   └── index.md                          # ✅ Complete: Project A (8 workstreams)
├── level-2/
│   ├── production-runtime/
│   │   └── index.md                      # ✅ ENRICHED (66 → 670+ lines)
│   ├── model-training/
│   │   └── index.md                      # ✅ ENRICHED (63 → 755+ lines)
│   ├── data-preparation/
│   │   └── index.md                      # ✅ Excellent (429 lines, "Level 2.5")
│   ├── pseudo-labeling/
│   │   └── index.md                      # ✅ Dependencies added
│   ├── labeling-benchmarking/
│   │   └── index.md                      # ✅ CREATED (400+ lines)
│   ├── model-arena/
│   │   └── index.md                      # ✅ Excellent (810 lines, "Level 2.5")
│   ├── monitoring-drift/
│   │   └── index.md                      # ✅ Excellent (890 lines, "Level 2.5")
│   ├── synthetic-generation/
│   │   └── index.md                      # ✅ Excellent (653 lines)
│   ├── benchmarking/
│   │   └── index.md                      # 🔄 LEGACY (55 lines, superseded by model-arena)
│   └── downstream-context/
│       └── index.md                      # ℹ️ Context only (76 lines)
└── level-3/                              # 📋 TO BE CREATED
    ├── data-preparation/
    ├── production-runtime/
    └── monitoring-drift/
```

---

## 📊 Issue Tracking Summary

| Category | Total | Priority 1 | Priority 2 | Priority 3 |
|----------|-------|------------|------------|------------|
| **File Path Issues** | 2 | 2 | 0 | 0 |
| **Documentation Gaps** | 5 | 2 | 2 | 1 |
| **Standardization** | 4 | 0 | 1 | 3 |
| **Level 3 Docs Needed** | 5 | 0 | 5 | 0 |
| **Legacy Cleanup** | 2 | 1 | 1 | 0 |
| **TOTAL** | 18 | 5 | 9 | 4 |

---

## 🎯 Priority 1: Immediate Fixes (Week 1)

### Issue 1.1: Workstream 5 File Path Mismatch

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: High
- **Identified By**: All 3 models (Gemini, GPT-5.1, DeepSeek)
- **Problem**:
  - Level 1 references `docs/architecture/diagrams/level-2/labeling-benchmarking/index.md`
  - File does not exist
  - `benchmarking/index.md` exists but is legacy (55 lines, superseded by model-arena)
- **Impact**: Broken navigation, incomplete understanding of Workstream 5
- **Solutions** (choose one):
  - [ ] **Option A**: Create missing file (recommended if WS5 is distinct from Model Arena)
  - [ ] **Option B**: Update Level 1 reference to redirect to model-arena with note: `"Workstream 5: See [model-arena/index.md](../level-2/model-arena/index.md) (benchmarking/ is legacy)"`
- **Owner**: TBD
- **Target Date**: Week 1, Day 1
- **Dependencies**: None

---

### Issue 1.2: LOC Count Inconsistencies

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Low (cosmetic, but signals documentation drift risk)
- **Identified By**: GPT-5.1, DeepSeek
- **Problem**:
  - Model Arena: "1,500+" (Level 1 line 244) vs "~3,057 lines" (Level 2 line 671)
  - Monitoring & Drift: "7,500+ lines" (Level 1 line 141) vs "~7,400 lines" (Level 2 lines 18, 34)
- **Impact**: Erodes documentation trustworthiness over time
- **Solution**:
  - [ ] Sync counts: Update Level 1 to match Level 2 precision
  - [ ] Establish policy: Use `~X,XXX` format in both locations
  - [ ] **Future**: Automate LOC extraction from source code or CI
- **Files to Update**:
  - `docs/architecture/diagrams/level-1/index.md` (lines 141, 244)
- **Owner**: TBD
- **Target Date**: Week 1, Day 2
- **Dependencies**: None

---

### Issue 1.3: Legacy Documentation Cleanup

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Medium
- **Identified By**: All 3 models
- **Problem**: `benchmarking/index.md` is legacy but no deprecation notice
- **Impact**: Navigation confusion for new contributors
- **Solution**:
  - [ ] Move `benchmarking/` to `deprecated/benchmarking/`
  - [ ] Add deprecation header to `deprecated/benchmarking/index.md`:

    ```markdown
    ---
    status: deprecated
    deprecated_date: "2025-01-16"
    superseded_by: "model-arena/index.md"
    ---

    # ⚠️ DEPRECATED: Benchmarking

    **This document is deprecated as of 2025-01-16.**
    **See [Model Arena & Multi-Label Benchmarking](../model-arena/index.md) for current documentation.**
    ```

  - [ ] Add redirect in Level 1 table (line 243)
- **Files to Update**:
  - Create `docs/architecture/diagrams/deprecated/benchmarking/index.md`
  - Update `docs/architecture/diagrams/level-1/index.md` (line 243)
- **Owner**: TBD
- **Target Date**: Week 1, Day 3
- **Dependencies**: Issue 1.1 resolution

---

### Issue 1.4: Missing Genalog Dependency in Level 1

- **Status**: ✅ **COMPLETED** (2025-01-16) - Already documented
- **Severity**: Low
- **Identified By**: DeepSeek
- **Problem**: Synthetic Generation uses Genalog but not listed in Level 1 tech stack
- **Impact**: Incomplete technology inventory
- **Solution**:
  - [ ] Add to Level 1 Workstream 8 description (lines 152-169):

    ```markdown
    | Component | Purpose |
    |-----------|---------|
    | **Degradation Profiles** | Blur, noise, rotation, illumination, JPEG artifacts |
    | **Genalog Integration** | Microsoft Genalog engine for analog document simulation |
    | **Ground Truth Derivation** | Automatic quality labels from degradation parameters |
    | **Dataset Expansion** | 1 clean image → 10+ degraded variants |
    ```

- **Files to Update**:
  - `docs/architecture/diagrams/level-1/index.md` (lines 152-169)
- **Owner**: TBD
- **Target Date**: Week 1, Day 4
- **Dependencies**: None

---

### Issue 1.5: Model Arena Graduation Criteria Linkage

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Medium
- **Identified By**: DeepSeek
- **Problem**: Model Arena positioned as "quality gate" (Level 1 line 112) but Level 2 lacks explicit graduation criteria linkage to Production Runtime
- **Impact**: Unclear how benchmarks translate to production deployment decisions
- **Solution**:
  - [ ] Add cross-reference in Model Arena Level 2 "Integration Points" section (after line 585):

    ```markdown
    ### Production Runtime Deployment Gate

    **Model Arena serves as the quality gate for Production Runtime deployment:**

    - **Graduation Criteria**: PLCC > 0.65 (Phase 2 validation)
    - **Deployment Decision**: Models must pass Arena benchmark before runtime integration
    - **Rollback Trigger**: PLCC drop > 10% triggers retraining (Workstream 7)

    **Workflow**: Workstream 2 (Training) → Workstream 6 (Arena validation) → Workstream 1 (Runtime deployment)

    See [Production Runtime](../production-runtime/index.md) for deployment procedures.
    ```

- **Files to Update**:
  - `docs/architecture/diagrams/level-2/model-arena/index.md` (after line 585)
- **Owner**: TBD
- **Target Date**: Week 1, Day 5
- **Dependencies**: None

---

## 📋 Priority 2: Level 2 Documentation Enrichment (Weeks 2-3)

### Issue 2.1: Production Runtime Narrative Gap

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: High
- **Identified By**: All 3 models
- **Problem**:
  - 15,000+ LOC but Level 2 doc is only 66 lines
  - Diagram-heavy, minimal narrative
  - Missing: State machine, error handling, edge cases
- **Impact**: New developers cannot understand critical business logic without diagrams
- **Solution**: Expand to 400+ lines with structured sections
- **Target Additions**:

  #### Section 1: Pipeline State Machine (150 lines)

  ```markdown
  ## Primary Pipeline State Machine

  ### States
  | State | Entry Condition | Exit Condition | Timeout |
  |-------|----------------|----------------|---------|
  | `INGESTION` | PDF/image received | Pages extracted | 30s |
  | `TEXT_GATE` | Pages extracted | Text detection complete | 10s |
  | `CLASSICAL_IQA` | Text gate: NO_TEXT | Classical detectors complete | 30s |
  | `LAYOUT_LITE` | Text gate: TEXT_DETECTED | Layout classification complete | 60s |
  | `ML_IQA` | IQA route determined | Student inference complete | 100s |
  | `TEACHER_ESCALATION` | High uncertainty/discrepancy | Teacher inference complete | 200s |
  | `CORRECTION` | IQA complete | Corrections applied | 50s |
  | `DQS_CALCULATION` | Corrections complete | Quality score computed | 10s |
  | `ROUTING` | DQS computed | Routing recommendation generated | 5s |
  | `OUTPUT` | Routing complete | JSON serialized | 10s |

  ### Error Handling
  - **Timeout**: Default 2-minute per-page timeout, escalate to error state
  - **Partial Failure**: If 1 page fails, mark as `failed` in metadata, continue processing remaining pages
  - **Critical Failure**: If >50% pages fail, abort entire document with error metadata

  ### Fallback Strategies
  - **Device Unavailable**: Local GPU → Modal GPU → CPU (see DeviceOrchestrator)
  - **ML Model Failure**: Fallback to classical IQA only, flag in metadata
  - **Layout Detection Timeout**: Skip layout-lite, use text-gate-only routing
  ```

  #### Section 2: Error Handling Patterns (100 lines)

  ```markdown
  ## Error Handling & Recovery

  ### Error Categories
  | Category | Severity | Recovery Strategy | Example |
  |----------|----------|-------------------|---------|
  | `TRANSIENT` | Low | Retry with exponential backoff | Network timeout |
  | `RESOURCE` | Medium | Fallback device, reduce batch size | GPU OOM |
  | `DATA` | High | Skip page, log for review | Corrupted PDF |
  | `CRITICAL` | Critical | Abort document, alert | Missing model file |

  ### Retry Logic
  - **Exponential Backoff**: 1s, 2s, 4s, 8s (max 3 retries)
  - **Jitter**: ±20% to prevent thundering herd
  - **Circuit Breaker**: Open after 5 consecutive failures, 60s timeout
  ```

  #### Section 3: Inputs/Outputs/Dependencies (100 lines)

  ```markdown
  ## Workstream Dependencies

  ### Upstream Dependencies
  | Workstream | Consumed Artifacts | Purpose |
  |------------|-------------------|---------|
  | **None** | N/A | Production Runtime is the entry point |

  ### Downstream Consumers
  | Workstream | Provided Artifacts | Purpose |
  |------------|-------------------|---------|
  | **Project B (Unify)** | DocumentMetadata.json, corrected images | OCR orchestration input |
  | **Workstream 7 (Monitoring)** | Predictions, latency metrics | Drift detection, active learning |

  ### Internal Dependencies
  | Component | Source | Purpose |
  |-----------|--------|---------|
  | **Device Orchestrator** | `src/utils/device_orchestrator.py` | GPU/CPU device selection |
  | **Text Gate** | `src/detection/text_gate.py` | Fast text presence detection |
  | **Classical IQA** | `src/detection/iqa_classical.py` | 7 classical CV detectors |
  | **ML IQA** | `src/detection/iqa_ml.py` | Teacher-student ResNet models |
  | **Layout Lite** | `src/detection/layout_lite.py` | DocLayout-YOLO (11 classes) |
  | **Corrections** | `src/correction/` | Deskew, CLAHE, denoising |
  | **DQS Calculator** | `src/metrics/dqs_calculator.py` | Document Quality Score |
  | **Routing Engine** | `src/routing/` | OCR strategy recommendation |
  ```

- **Files to Update**:
  - `docs/architecture/diagrams/level-2/production-runtime/index.md`
- **Owner**: TBD
- **Target Date**: Week 2, Day 5
- **Dependencies**: None
- **Estimated Effort**: 8 hours

---

### Issue 2.2: Model Training Workflow Details

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Medium
- **Identified By**: All 3 models
- **Problem**:
  - Missing distillation mechanics
  - No explicit data consumption from WS3/4/8
  - Unclear checkpoint flow to Arena and runtime
- **Impact**: New engineers cannot understand training → deployment flow
- **Solution**: Add 200+ lines covering:

  #### Section 1: Distillation Workflow (100 lines)

  ```markdown
  ## Knowledge Distillation Workflow

  ### Training Phases
  | Phase | Model | Dataset | Epochs | Loss Function | Validation Metric |
  |-------|-------|---------|--------|---------------|-------------------|
  | **1. Teacher Training** | ResNet-50 | OHR-Bench (70% real, 30% synthetic) | 50 | MSE + Multi-Label BCE | PLCC > 0.70 |
  | **2. Student Distillation** | ResNet-18 | Teacher soft labels + hard labels | 30 | α×KL(teacher) + (1-α)×MSE(ground truth) | PLCC > 0.65 |

  ### Distillation Loss Function
  ```python
  # α = 0.7 (teacher weight), T = 3 (temperature)
  loss = α * KL_divergence(student_logits/T, teacher_logits/T) + (1-α) * MSE(student_output, ground_truth)
  ```

  ### Checkpoint Selection

  - **Teacher**: Best validation PLCC (early stopping patience=10)
  - **Student**: Best validation PLCC with latency constraint (<100ms/page CPU)

  ```

  #### Section 2: Data Consumption (50 lines)
  ```markdown
  ## Data Pipeline Integration

  ### Dataset Sources
  | Workstream | Artifact | Usage |
  |------------|----------|-------|
  | **WS3: Data Preparation** | `training_labels.parquet`, raw images | Base training dataset (70% of total) |
  | **WS4: Pseudo-Labeling** | Pseudo-labeled images (5-model ensemble) | Augment training data (unlabeled → labeled) |
  | **WS8: Synthetic Generation** | Degraded images + ground truth | Expand dataset 2-3x (30% of total) |

  ### Dataset Composition
  - **Real Data (70%)**: DIQA-5000, OHR-Bench, DocLayNet
  - **Synthetic Data (30%)**: Genalog-generated degradations
  - **Pseudo-Labeled (<10%)**: High-confidence ensemble predictions
  ```

  #### Section 3: Deployment Flow (50 lines)

  ```markdown
  ## Model Deployment Pipeline

  ### Checkpoint Flow
  ```text
  Training Complete (modal/train_phase2_iqa.py)
      ↓
  Export to ONNX + TorchScript (modal/export_onnx.py)
      ↓
  Upload to Model Registry (GCS bucket)
      ↓
  Arena Benchmark (Workstream 6)
      ↓ (PLCC > 0.65?)
  Production Deployment (Workstream 1)
      ↓
  Monitoring (Workstream 7)
  ```

  ### Model Registry Structure

  ```
  gs://image-detection-models/
  ├── teacher/
  │   ├── resnet50_v1.0.0.onnx
  │   └── resnet50_v1.0.0_metadata.json
  └── student/
      ├── resnet18_v1.0.0.onnx
      ├── resnet18_v1.0.0.pt (TorchScript)
      └── resnet18_v1.0.0_metadata.json
  ```

  ```

- **Files to Update**:
  - `docs/architecture/diagrams/level-2/model-training/index.md`
- **Owner**: TBD
- **Target Date**: Week 3, Day 3
- **Dependencies**: None
- **Estimated Effort**: 6 hours

---

### Issue 2.3: Pseudo-Labeling Dependencies Section

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Low
- **Identified By**: GPT-5.1, DeepSeek
- **Problem**: Doesn't specify how Labeling Models (WS5) are invoked or outputs to WS2
- **Impact**: Missing context for new engineers relying on Level 2 docs
- **Solution**: Add "Workstream Dependencies" section (50 lines)

  ```markdown
  ## Workstream Dependencies

  ### Upstream Dependencies
  | Workstream | Consumed Artifacts | Purpose |
  |------------|-------------------|---------|
  | **WS3: Data Preparation** | `samples.parquet`, unlabeled images | Images requiring labels |
  | **WS5: Labeling & Benchmarking Models** | Trained MUSIQ, QualiCLIP, DocIQ, Qwen3-VL, InternVL3 models | Ensemble labeling (5 models) |

  ### Model Invocation
  - **Track A (IQA)**: MUSIQ (sharpness), QualiCLIP (color), DocIQ-Replica (overall)
  - **Track B (VLM)**: Qwen3-VL-8B (generalist), InternVL3-8B (overall)
  - **Inference Backend**: Modal GPU (batch processing, 32 images/batch)
  - **Checkpoint Selection**: Best SRCC + ECE weighted score from WS6 Arena

  ### Downstream Consumers
  | Workstream | Provided Artifacts | Purpose |
  |------------|-------------------|---------|
  | **WS2: Production Model Training** | Pseudo-labeled dataset (ensemble predictions) | Augment training data with high-confidence labels |

  ### Quality Gates
  - **Confidence Threshold**: Only labels with ensemble agreement >0.8 used for training
  - **Uncertainty Filtering**: High-variance predictions sent to manual review
  ```

- **Files to Update**:
  - `docs/architecture/diagrams/level-2/pseudo-labeling/index.md`
- **Owner**: TBD
- **Target Date**: Week 3, Day 5
- **Dependencies**: Issue 1.1 resolution (if WS5 doc created)
- **Estimated Effort**: 2 hours

---

### Issue 2.4: Downstream Context Reflection in Level 1

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Low
- **Identified By**: DeepSeek
- **Problem**: Level 2 downstream-context (Projects B/C/D) not reflected in Level 1 dependency mapping
- **Impact**: Incomplete inter-project contract visibility at Level 1
- **Solution**: Add "Downstream Projects Context" section to Level 1 (after line 230)

  ```markdown
  ## Downstream Projects Context

  Project A (Prepare-Doc) outputs are consumed by three downstream projects:

  | Project | Consumes | Purpose | Contract Document |
  |---------|----------|---------|-------------------|
  | **Project B (Unify)** | DocumentMetadata.json, corrected images | OCR orchestration, Docling DOM creation | [prepare-doc-unify-contract.md](../../development/RAG%20Pipeline/prepare-doc-unify-contract.md) |
  | **Project C (Chunk)** | Docling DOM (via Project B) | Trust scoring, RAG chunking | TBD |
  | **Project D (Embed)** | Chunks (via Project C) | Vector embeddings, retrieval | TBD |

  See [Downstream Context](../level-2/downstream-context/index.md) for detailed workflow diagrams.
  ```

- **Files to Update**:
  - `docs/architecture/diagrams/level-1/index.md` (after line 230)
- **Owner**: TBD
- **Target Date**: Week 3, Day 5
- **Dependencies**: None
- **Estimated Effort**: 1 hour

---

## 📐 Priority 3: Standardization (Weeks 4-5)

### Issue 3.1: Standardize "Integration & Boundaries" Sections

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Medium
- **Identified By**: GPT-5.1
- **Problem**: Only Data Prep, Monitoring, Synthetic Gen have explicit integration sections
- **Completion Note**: All 8 workstream docs now have comprehensive "Workstream Dependencies" sections added during Level 2 enrichment (Issues 2.1-2.3)
- **Impact**: Inconsistent documentation patterns across workstreams
- **Solution**: Add template section to **all** Level 2 docs without it
- **Template**:

  ```markdown
  ## Workstream Dependencies

  ### Upstream Dependencies
  | Workstream | Consumed Artifacts | Purpose |
  |------------|-------------------|---------|
  | ... | ... | ... |

  ### Downstream Consumers
  | Workstream | Provided Artifacts | Purpose |
  |------------|-------------------|---------|
  | ... | ... | ... |

  ### External Dependencies
  | Service/Tool | Purpose | Configuration |
  |--------------|---------|---------------|
  | ... | ... | ... |
  ```

- **Files to Update** (in order):
  1. [ ] `production-runtime/index.md` (covered in Issue 2.1)
  2. [ ] `model-training/index.md` (covered in Issue 2.2)
  3. [ ] `pseudo-labeling/index.md` (covered in Issue 2.3)
  4. [ ] `labeling-benchmarking/index.md` (if created for Issue 1.1)
- **Owner**: TBD
- **Target Date**: Week 4, Day 5
- **Dependencies**: Issues 2.1, 2.2, 2.3
- **Estimated Effort**: 4 hours (1 hour per doc)

---

### Issue 3.2: Adopt "Level 2.5" Standard Documentation Template

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Low
- **Identified By**: Gemini
- **Problem**: No documented template for achieving "Level 2.5" quality
- **Completion Note**: Created comprehensive template at `docs/architecture/LEVEL_2_DOCUMENTATION_TEMPLATE.md` with examples, guidelines, and quality checklist
- **Impact**: Inconsistent depth across new workstream docs
- **Solution**: Create template and guidelines document
- **Deliverable**: `docs/architecture/LEVEL_2_DOCUMENTATION_TEMPLATE.md`
- **Template Sections**:
  1. Overview (purpose, status, LOC, complexity assessment)
  2. Technical Diagrams (PlantUML sources)
  3. System Components (table with responsibilities, LOC, file paths)
  4. Key Features/Workflows (with code examples)
  5. API Documentation (if applicable)
  6. Performance Characteristics
  7. Workstream Dependencies (upstream/downstream/external)
  8. Integration Points (cross-workstream flows)
  9. Level 3 Decision Rationale
  10. Related Documentation
  11. Source Files (traceability)
- **Owner**: TBD
- **Target Date**: Week 5, Day 3
- **Dependencies**: Issues 2.1, 2.2, 2.3 (to extract patterns)
- **Estimated Effort**: 4 hours

---

### Issue 3.3: Automated LOC Count Extraction

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Low
- **Identified By**: GPT-5.1
- **Problem**: Manual LOC counts drift over time
- **Completion Note**: Created `scripts/extract_workstream_loc.sh` with JSON output and Level 1 update suggestions
- **Impact**: Documentation trustworthiness erosion
- **Solution**: Create CI job to extract LOC from source code
- **Implementation**:
  1. [ ] Script: `scripts/extract_workstream_loc.sh`
  2. [ ] CI job: `.github/workflows/update-architecture-metrics.yml`
  3. [ ] Output: JSON file with workstream LOC counts
  4. [ ] Manual step: Update Level 1 table from JSON quarterly
- **Owner**: TBD
- **Target Date**: Week 5, Day 5
- **Dependencies**: None
- **Estimated Effort**: 6 hours

---

### Issue 3.4: Cross-Level Reference Validation

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Low
- **Identified By**: Internal observation
- **Problem**: No automated check for broken cross-level links
- **Completion Note**: Created `scripts/validate_architecture_links.sh` with comprehensive link checking across all levels
- **Impact**: Risk of stale references as documentation evolves
- **Solution**: Create link checker for architecture docs
- **Implementation**:
  1. [ ] Script: `scripts/validate_architecture_links.sh`
  2. [ ] CI job: Add to `update-architecture-metrics.yml`
  3. [ ] Checks:
     - Level 0 → Level 1 references
     - Level 1 → Level 2 references
     - Level 2 → Level 3 references (when created)
     - Cross-workstream links
- **Owner**: TBD
- **Target Date**: Week 5, Day 5
- **Dependencies**: None
- **Estimated Effort**: 4 hours

---

## 🏗️ Priority 2: Level 3 Documentation Creation (Weeks 4-6)

### Issue 4.1: Data Preparation Level 3 - Metadata Schema

- **Status**: 📋 **REQUIRED** (Unanimous agreement)
- **Severity**: High
- **Identified By**: All 3 models
- **Justification**:
  - 1,235-line `annotate_base_metadata.py` script
  - Complex three-layer metadata architecture
  - Anchor weighting logic (6 priority levels)
- **Deliverable**: `docs/architecture/diagrams/level-3/data-preparation/metadata-schema-versioning.md`
- **Content** (400+ lines):
  1. **Three-Layer Architecture**:
     - ER diagrams for Layer 1 (Immutable), Layer 2 (Enrichment), Layer 3 (Training)
     - Data flow between layers
  2. **Versioning Strategy**:
     - EnrichmentVersion schema
     - Backward compatibility rules
  3. **Anchor Score Priority Logic**:
     - Decision tree for anchor source selection
     - Weight calculation formulas
  4. **Class Diagrams**:
     - `OriginalFileMetadata`
     - `OriginalLabels`
     - `EnrichmentData`
     - `TrainingLabels`
  5. **Code Traceability**:
     - Map each class to source file lines
- **Owner**: TBD
- **Target Date**: Week 4, Day 5
- **Dependencies**: None
- **Estimated Effort**: 12 hours

---

### Issue 4.2: Data Preparation Level 3 - Label Parsing & Generation

- **Status**: 📋 **REQUIRED** (Unanimous agreement)
- **Severity**: High
- **Identified By**: All 3 models
- **Justification**:
  - 9 dataset-specific parsers
  - 590-line `build_training_labels.py` script
  - COCO cache optimization (100x speedup)
- **Deliverable**: `docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md`
- **Content** (350+ lines):
  1. **Parser Architecture**:
     - Abstract parser interface
     - Parser registry pattern
  2. **Dataset-Specific Parsers**:
     - Sequence diagrams for DIQA, LIVE, DocLayNet, TableBank parsers
  3. **COCO Cache Strategy**:
     - Cache initialization flow
     - Memory vs speed tradeoffs
  4. **Training Label Builder**:
     - 45-dimensional IQA vector construction
     - Anchor score calculation
     - Output schema mapping
  5. **Performance Characteristics**:
     - Parser benchmarks (ms/sample)
     - Cache hit rate analysis
- **Owner**: TBD
- **Target Date**: Week 5, Day 3
- **Dependencies**: Issue 4.1 (schema understanding)
- **Estimated Effort**: 10 hours

---

### Issue 4.3: Production Runtime Level 3 - Pipeline State Machine

- **Status**: 📋 **REQUIRED** (Unanimous agreement)
- **Severity**: High
- **Identified By**: All 3 models
- **Justification**:
  - 15,000+ LOC codebase
  - Mission-critical end-to-end pipeline
  - Complex state transitions and error handling
- **Deliverable**: `docs/architecture/diagrams/level-3/production-runtime/pipeline-state-machine.md`
- **Content** (400+ lines):
  1. **State Diagram**:
     - PlantUML state machine with all transitions
     - Entry/exit conditions for each state
  2. **Error Handling**:
     - Error classification taxonomy
     - Recovery strategies per error type
     - Retry logic with exponential backoff
  3. **Timeout Management**:
     - Per-state timeout configurations
     - Timeout escalation flow
  4. **Edge Cases**:
     - Partial page failure handling
     - Critical failure abort conditions
     - Graceful degradation scenarios
  5. **Sequence Diagrams**:
     - Happy path (no errors)
     - Error path with retries
     - Fallback device selection
- **Owner**: TBD
- **Target Date**: Week 5, Day 5
- **Dependencies**: Issue 2.1 (Level 2 enrichment)
- **Estimated Effort**: 12 hours

---

### Issue 4.4: Production Runtime Level 3 - DeviceOrchestrator

- **Status**: 📋 **REQUIRED** (Unanimous agreement)
- **Severity**: High
- **Identified By**: All 3 models
- **Justification**:
  - Complex device selection logic
  - Budget enforcement (3 levels: doc/batch/monthly)
  - Circuit breaker patterns
- **Deliverable**: `docs/architecture/diagrams/level-3/production-runtime/device-orchestrator.md`
- **Content** (350+ lines):
  1. **Device Priority Algorithm**:
     - Decision tree: Local GPU → Modal GPU → CPU (or BLOCK)
     - Policy configuration matrix
  2. **Budget Enforcement**:
     - Three-tier budget tracking
     - Budget depletion handling
  3. **Circuit Breaker**:
     - Modal GPU failure detection
     - Circuit breaker state machine (CLOSED → OPEN → HALF_OPEN)
     - Recovery criteria
  4. **Performance Characteristics**:
     - Latency per device type
     - Cost tracking
     - Prometheus metrics
  5. **Code Traceability**:
     - `src/utils/device_orchestrator.py` class diagram
     - Integration points with `iqa_ml.py`
- **Owner**: TBD
- **Target Date**: Week 6, Day 3
- **Dependencies**: Issue 4.3 (state machine context)
- **Estimated Effort**: 10 hours

---

### Issue 4.5: Monitoring & Drift Detection Level 3 - End-to-End Lifecycle

- **Status**: ✅ **APPROVED** (2025-01-16 - User decision: implement for end-to-end lifecycle visibility)
- **Severity**: Medium
- **Identified By**: GPT-5.1, DeepSeek
- **Justification**:
  - 7,400 LOC with 6 sub-systems
  - Stateful workflows (privacy review, retraining jobs)
  - Complex cross-component flows
- **Consensus**: Despite Level 2 recommending "no Level 3", two models argue for end-to-end lifecycle documentation
- **Deliverable**: `docs/architecture/diagrams/level-3/monitoring-drift/end-to-end-lifecycle.md`
- **Content** (300+ lines):
  1. **Complete Lifecycle Sequence Diagram**:
     - Drift detection → Alert → Active learning → Privacy review → Retraining → Arena → Deployment
  2. **State Machines**:
     - RetrainingJob status flow (PENDING → PREPARING → TRAINING → VALIDATING → COMPLETED/FAILED)
     - PrivacyReview workflow (PENDING → REQUIRES_REVIEW → APPROVED/REJECTED)
  3. **Integration Flow**:
     - How 6 components interact (Drift, Performance, Alerting, Active Learning, Privacy, Retraining)
  4. **Compliance Workflows**:
     - GDPR/CCPA review process
     - Audit trail generation
  5. **Deployment Gates**:
     - Arena PLCC validation
     - Production deployment criteria
- **Owner**: TBD
- **Target Date**: Week 6, Day 5 (CONDITIONAL - pending approval)
- **Dependencies**: None (Level 2 already comprehensive)
- **Estimated Effort**: 10 hours
- **Approval Required**: ✅ YES (2-1 split decision)

---

## 🗂️ Legacy Cleanup (Week 1)

### Issue 5.1: Create Deprecated Directory Structure

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Medium
- **Problem**: Legacy docs mixed with current docs, causing navigation confusion
- **Solution**: Create deprecated directory and move legacy content
- **Actions**:

  ```bash
  # 1. Create deprecated directory
  mkdir -p docs/architecture/diagrams/deprecated

  # 2. Move legacy benchmarking
  mv docs/architecture/diagrams/level-2/benchmarking \
     docs/architecture/diagrams/deprecated/

  # 3. Create README in deprecated/
  cat > docs/architecture/diagrams/deprecated/README.md << 'EOF'
  # Deprecated Architecture Documentation

  This directory contains architecture documentation that has been superseded by newer documents.

  **Do not use these documents for current development.**

  | Document | Deprecated Date | Superseded By | Reason |
  |----------|----------------|---------------|--------|
  | benchmarking/ | 2025-01-16 | [model-arena/](../level-2/model-arena/index.md) | Model Arena expanded to multi-phase benchmarking |
  EOF

  # 4. Update .gitignore (if needed)
  echo "# Keep deprecated docs for historical reference" >> .gitignore
  ```

- **Files to Create/Update**:
  - `docs/architecture/diagrams/deprecated/README.md`
  - `docs/architecture/diagrams/deprecated/benchmarking/index.md` (add deprecation header)
- **Owner**: TBD
- **Target Date**: Week 1, Day 3
- **Dependencies**: None
- **Estimated Effort**: 1 hour

---

### Issue 5.2: Update Navigation/Index Files

- **Status**: ✅ **COMPLETED** (2025-01-16)
- **Severity**: Low
- **Problem**: Index files may reference deprecated content
- **Completion Note**: Updated `docs/architecture/diagrams/INDEX.md` with deprecation notice and migration path for benchmarking workstream
- **Solution**: Audit and update all index files
- **Files to Audit**:
  - [ ] `docs/architecture/diagrams/INDEX.md` (if exists)
  - [ ] `docs/architecture/diagrams/level-1/index.md` (table at line 233-247)
  - [ ] `docs/README.md` (if contains architecture links)
  - [ ] Root `README.md` (if contains architecture links)
- **Actions**:
  - Add `(deprecated)` notation next to legacy links
  - Add redirect notes pointing to current docs
- **Owner**: TBD
- **Target Date**: Week 1, Day 4
- **Dependencies**: Issue 5.1
- **Estimated Effort**: 2 hours

---

## 🎨 Priority 2: Swimlane Traceability (Option C - Hybrid)

### Issue 6.1: Create Swimlane Diagrams with LOC Traceability

- **Status**: ✅ **APPROVED** (2025-01-16 - User decision: Option C Hybrid approach)
- **Severity**: High
- **Identified By**: User requirement based on swimlane traceability proposal
- **Problem**: No visual verification that all source files are accounted for in workflow diagrams
- **Impact**: Cannot validate documentation completeness, difficult developer onboarding, no refactoring impact analysis
- **Solution**: Hybrid approach - traceability tables at Level 2, detailed swimlanes at Level 3
- **Deliverables**:

  #### Part A: Level 2 Traceability Tables (8 hours)

  Add to ALL 8 workstream Level 2 index.md files:

  ```markdown
  ## Source File Traceability

  | Workflow Step | Source Files | LOC | Total |
  |---------------|--------------|-----|-------|
  | [Step 1] | file1.py, file2.py, file3.py | 100, 200, 150 | 450 |
  | [Step 2] | file4.py | 300 | 300 |
  ...
  ```

  **Files to Update** (8):
  1. production-runtime/index.md
  2. model-training/index.md
  3. data-preparation/index.md
  4. pseudo-labeling/index.md
  5. labeling-benchmarking/index.md
  6. model-arena/index.md
  7. monitoring-drift/index.md
  8. synthetic-generation/index.md

  #### Part B: Level 3 Swimlane Diagrams (20 hours)

  Create detailed swimlanes for 4 complex workstreams:

  1. **Production Runtime** (`level-3/production-runtime/production-runtime-swimlane.puml`) - 8 hours
     - 4 swimlanes: Ingestion & Preflight, Classification & Routing, Quality Analysis, Correction & Scoring
     - Annotate all 44 files (16,910 LOC)
     - Include legend: Total matches LOC extraction

  2. **Data Preparation** (`level-3/data-preparation/data-preparation-swimlane.puml`) - 4 hours
     - 4 swimlanes: Dataset Collection, Layer 1 (Immutable), Layer 2 (Enrichment), Layer 3 (Training)
     - Annotate all 8 scripts (4,066 LOC)

  3. **Model Training** (`level-3/model-training/model-training-swimlane.puml`) - 4 hours
     - 4 swimlanes: Data Preparation, Teacher Training, Student Distillation, Model Export
     - Annotate all 16 files (7,058 LOC)

  4. **Monitoring & Drift** (`level-3/monitoring-drift/monitoring-drift-swimlane.puml`) - 4 hours
     - 6 swimlanes: Drift Detection, Performance Monitoring, Alerting, Active Learning, Privacy Review, Retraining
     - Annotate all 7 files (5,348 LOC)

  #### Part C: Enhanced LOC Validation (4 hours)

  Update `scripts/extract_workstream_loc.sh` with:
  - `--validate-tables`: Compare Level 2 tables vs LOC mappings
  - `--validate-swimlane <workstream>`: Compare Level 3 swimlane annotations vs LOC mappings
  - Output discrepancy reports

- **Total Effort**: 32 hours (8 + 20 + 4)
- **Owner**: TBD
- **Target Date**: Weeks 3-6 (parallel with Level 3 docs)
- **Dependencies**: Issues 3.3, 3.4, 4.1-4.5 (automation + Level 3 docs)
- **Execution Strategy**: **PARALLEL** with Level 3 documentation
  - Week 3-4: Traceability tables (8h) + Data Prep docs & swimlane (16h) = 24h
  - Week 5: Production Runtime docs & swimlane (20h)
  - Week 6: Monitoring docs & swimlane + validation enhancement (14h)

---

## 📅 Implementation Timeline

### Week 1: Immediate Fixes (5 days)

| Day | Task | Owner | Estimated Hours |
|-----|------|-------|-----------------|
| 1 | Issue 1.1: Fix Workstream 5 file path mismatch | TBD | 2h |
| 2 | Issue 1.2: Sync LOC counts | TBD | 1h |
| 3 | Issue 1.3 & 5.1: Legacy cleanup + deprecated directory | TBD | 2h |
| 4 | Issue 1.4 & 5.2: Genalog dependency + navigation updates | TBD | 2h |
| 5 | Issue 1.5: Model Arena graduation criteria linkage | TBD | 1h |
| **Total** | | | **8 hours** |

---

### Weeks 2-3: Level 2 Enrichment (10 days)

| Task | Owner | Estimated Hours | Target Date |
|------|-------|-----------------|-------------|
| Issue 2.1: Production Runtime narrative (400 lines) | TBD | 8h | Week 2, Day 5 |
| Issue 2.2: Model Training workflow (200 lines) | TBD | 6h | Week 3, Day 3 |
| Issue 2.3: Pseudo-Labeling dependencies (50 lines) | TBD | 2h | Week 3, Day 5 |
| Issue 2.4: Downstream context in Level 1 | TBD | 1h | Week 3, Day 5 |
| **Total** | | **17 hours** | |

---

### Weeks 4-5: Standardization (10 days)

| Task | Owner | Estimated Hours | Target Date |
|------|-------|-----------------|-------------|
| Issue 3.1: Integration sections (4 docs) | TBD | 4h | Week 4, Day 5 |
| Issue 3.2: Level 2.5 template document | TBD | 4h | Week 5, Day 3 |
| Issue 3.3: Automated LOC extraction CI | TBD | 6h | Week 5, Day 5 |
| Issue 3.4: Cross-level reference validator | TBD | 4h | Week 5, Day 5 |
| **Total** | | **18 hours** | |

---

### Weeks 4-6: Level 3 Documentation (15 days, parallel with Standardization)

| Task | Owner | Estimated Hours | Target Date |
|------|-------|-----------------|-------------|
| Issue 4.1: Data Prep - Metadata schema | TBD | 12h | Week 4, Day 5 |
| Issue 4.2: Data Prep - Label parsing | TBD | 10h | Week 5, Day 3 |
| Issue 4.3: Production Runtime - State machine | TBD | 12h | Week 5, Day 5 |
| Issue 4.4: Production Runtime - DeviceOrchestrator | TBD | 10h | Week 6, Day 3 |
| Issue 4.5: Monitoring - Lifecycle (CONDITIONAL) | TBD | 10h | Week 6, Day 5 |
| **Total** | | **54 hours** (44h if Issue 4.5 skipped) | |

---

### Overall Effort Summary

| Category | Total Hours | Working Days (8h/day) |
|----------|-------------|----------------------|
| **Week 1: Immediate Fixes** | 8h | 1 day |
| **Weeks 2-3: Level 2 Enrichment** | 17h | 2.1 days |
| **Weeks 4-5: Standardization** | 18h | 2.3 days |
| **Weeks 4-6: Level 3 Docs** | 54h (44h if 4.5 skipped) | 6.8 days (5.5 days) |
| **TOTAL** | **97 hours** (87h if 4.5 skipped) | **12.1 days** (10.9 days) |

**Note**: Level 3 tasks can run in parallel with Standardization tasks, reducing calendar time.

---

## 🎯 Success Criteria

### Documentation Quality Metrics

- [ ] **Consistency**: Zero broken cross-level references (validated by Issue 3.4 CI)
- [ ] **Completeness**: All Level 2 docs have ≥300 lines OR explicit "Level 2.5" designation
- [ ] **Standardization**: All Level 2 docs have "Workstream Dependencies" section
- [ ] **LOC Accuracy**: ±5% tolerance between Level 1 and Level 2 counts
- [ ] **Legacy Clarity**: All deprecated docs have deprecation headers and redirects

### Level 3 Documentation Metrics

- [ ] **Data Preparation**: 2 Level 3 docs created (metadata + parsing)
- [ ] **Production Runtime**: 2 Level 3 docs created (state machine + device orchestrator)
- [ ] **Monitoring & Drift**: 1 Level 3 doc created (CONDITIONAL, pending approval)

### Process Improvements

- [ ] **Automation**: LOC extraction CI running quarterly
- [ ] **Validation**: Link checker CI running on all PRs touching architecture docs
- [ ] **Template**: Level 2.5 template documented and referenced in contributor guide

---

## 🔄 Review & Approval Process

### Approval Required For

1. **Issue 4.5 (Monitoring Level 3 doc)**: 2-1 model vote, human decision needed
   - **For**: GPT-5.1 (cross-component flows valuable), DeepSeek (stateful workflows complex)
   - **Against**: Gemini (Level 2 already "Level 2.5" quality)
   - **Recommendation**: Approve if team anticipates significant Monitoring expansion; defer otherwise

2. **Week 1 Deliverables**: Quick review to unblock downstream work
3. **Level 3 Docs**: Architect review before publication
4. **CI/Automation Scripts**: DevOps review for security/performance

### Review Schedule

| Milestone | Deliverables | Reviewer | Review Date |
|-----------|--------------|----------|-------------|
| **Week 1 Complete** | Issues 1.1-1.5, 5.1-5.2 | Tech Lead | Week 1, Day 5 (EOD) |
| **Week 3 Complete** | Issues 2.1-2.4 | Architect | Week 3, Day 5 (EOD) |
| **Week 5 Complete** | Issues 3.1-3.4 | Tech Lead + DevOps | Week 5, Day 5 (EOD) |
| **Week 6 Complete** | Issues 4.1-4.5 | Architect | Week 6, Day 5 (EOD) |

---

## 📊 Progress Tracking

### Overall Progress

- **Total Issues**: 19 (added Issue 6.1)
- **Completed**: 14 (74%)
- **In Progress**: 0 (0%)
- **Planned**: 5 (26%)

### By Priority

| Priority | Total | Completed | In Progress | Planned |
|----------|-------|-----------|-------------|---------|
| **Priority 1** | 5 | 5 | 0 | 0 |
| **Priority 2** | 10 | 4 | 0 | 6 |
| **Priority 3** | 4 | 0 | 0 | 4 |

### By Category

| Category | Total | Completed | In Progress | Planned |
|----------|-------|-----------|-------------|---------|
| **File Path Issues** | 2 | 2 | 0 | 0 |
| **Documentation Gaps** | 5 | 4 | 0 | 1 |
| **Standardization** | 4 | 0 | 0 | 4 |
| **Level 3 Docs** | 5 | 0 | 0 | 5 |
| **Legacy Cleanup** | 2 | 2 | 0 | 0 |

---

## 📝 Notes & Decisions

### Decision Log

| Date | Decision | Rationale | Approver |
|------|----------|-----------|----------|
| 2025-01-16 | Adopt "Level 2.5" standard for all workstreams | Reduces need for Level 3 docs, proven successful in Monitoring/Arena | Multi-Model Consensus |
| 2025-01-16 | APPROVE Issue 4.5 (Monitoring Level 3) | End-to-end lifecycle visibility needed for 6-component system | User Decision |
| 2025-01-16 | APPROVE Issue 6.1 (Option C Hybrid Traceability) | Bidirectional validation + visual onboarding, tables at L2 + swimlanes at L3 | User Decision |
| 2025-01-16 | Updated diagram-maintenance-agent for 4-level hierarchy | Enforce Level 3 swimlane LOC annotation requirements | Implementation |

### Open Questions

1. **Issue 1.1**: Should Workstream 5 have its own Level 2 doc or redirect to Model Arena?
   - **Recommendation**: Create separate doc if WS5 includes model training details distinct from Arena benchmarking
2. **Issue 4.5**: Approve Monitoring & Drift Level 3 doc?
   - **Recommendation**: Approve if planning significant Monitoring expansion or compliance audits

### References

- **Multi-Model Evaluation**: Gemini 3 Pro, GPT-5.1, DeepSeek R1 (2025-01-16)
- **Source Documents**:
  - [level-0/index.md](diagrams/level-0/index.md)
  - [level-1/index.md](diagrams/level-1/index.md)
  - [level-2/*/index.md](diagrams/level-2/)

---

## 🔗 Related Documents

- [Level 0: RAG Pipeline Overview](diagrams/level-0/index.md)
- [Level 1: Project A Architecture](diagrams/level-1/index.md)
- [Level 2: All Workstreams](diagrams/level-2/)
- [Level 2.5 Documentation Template](LEVEL_2_DOCUMENTATION_TEMPLATE.md) (to be created in Issue 3.2)

---

*Last Updated: 2025-01-16*
*Next Review: Week 1, Day 5 (2025-01-23)*
