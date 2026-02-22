---
owner: docs-team
purpose: Documentation for PlantUML Diagram Audit and Recommendations.
schema_type: common
status: active
tags:
- architecture
title: PlantUML Diagram Audit and Recommendations
---

**Date**: February 2026 (updated from December 2025 original)
**Scope**: Project A - Preprocessing, IQA, Layout & Routing Gateway
**Author**: Claude Code Analysis

## Executive Summary

This document provides a comprehensive audit of all PlantUML diagrams in the project, establishes a clear hierarchical structure, identifies gaps, overlaps, and inconsistencies, and provides actionable recommendations for diagram consolidation and maintenance.

## RAG Pipeline Ecosystem

The broader RAG pipeline consists of multiple repositories working together:

| Repository | Purpose | Status |
|------------|---------|--------|
| [rag-processor](https://github.com/ByronWilliamsCPA/rag-processor) | Pipeline frontend, job orchestration | In Development |
| **image_detection** (THIS REPO) | Project A: Preprocessing, IQA, Layout | Active Development |
| [audio-processor](https://github.com/ByronWilliamsCPA/audio-processor) | Audio track: Transcription, diarization | In Development |
| Project B | OCR orchestration (multi-engine) | **Not Yet Started** |
| Project C | Fusion & chunking | Not Yet Started |
| Project D | Vector store integration | Not Yet Started |

**Scope Update**: Layout analysis (docling-layout with 11 DocLayNet classes, reading order, table structure) was moved from Project B to Project A for simplification. Project B will focus solely on OCR orchestration.

## Project Architecture Context

Project A serves as the "front door" for a four-project RAG document pipeline. The system architecture consists of four interconnected workstreams:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROJECT A WORKSTREAMS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │ Data Preparation │───▶│ Pseudo-Labeling  │───▶│ Model Training   │       │
│  │                  │    │                  │    │                  │       │
│  │ • Dataset ingest │    │ • 5-model        │    │ • Teacher (R50)  │       │
│  │ • Normalization  │    │   ensemble       │    │ • Distillation   │       │
│  │ • Train/Val/Test │    │ • Stacking       │    │ • Student (R18)  │       │
│  │ • Augmentation   │    │ • Calibration    │    │ • ONNX export    │       │
│  └──────────────────┘    └──────────────────┘    └────────┬─────────┘       │
│                                                           │                  │
│                                                           ▼                  │
│                                              ┌──────────────────────┐        │
│                                              │ Production Runtime   │        │
│                                              │                      │        │
│                                              │ • Document analysis  │        │
│                                              │ • Full layout detect │        │
│                                              │ • IQA + corrections  │        │
│                                              │ • DQS + routing      │        │
│                                              │ • Handoff to Proj B  │        │
│                                              └──────────────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Distinction**: The pseudo-labeling workstream uses accuracy-optimized models (MUSIQ, QualiCLIP, DocIQ-Replica, Qwen3-VL-8B, InternVL3-8B) to generate consistent labels. These are NOT production models. The production runtime uses MobileNetV4-Conv-S (~3ms, 3 heads) for fast pre-correction and SigLIP 2 NAFlex (~50ms, 16 heads) for full multi-task analysis.

> **Note**: This audit was conducted in December 2025 and predates the migration from ResNet-50/18 teacher-student to SigLIP 2 NAFlex + MobileNetV4-Conv-S. Some gap analysis items below reference the old architecture. See [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) for current architecture.

---

## Diagram Inventory

### Retained Diagrams (Canonical)

#### Level 0: Pipeline Context

| File | Location | Purpose |
|------|----------|---------|
| `rag-pipeline-overview.puml` | `docs/architecture/diagrams/` | Multi-track RAG pipeline overview (Document + Audio tracks) |

#### Level 1: Project A Architecture (NEW)

| File | Location | Purpose |
|------|----------|---------|
| `PROJECT_A_ARCHITECTURE_OVERVIEW.puml` | `docs/` | **NEW** - Complete system architecture showing all workstreams |
| `PROJECT_A_WORKFLOW_HIERARCHY.puml` | `docs/` | **NEW** - Swimlane diagram showing data flow between workstreams |

#### Level 2: Production Runtime

| File | Location | Purpose |
|------|----------|---------|
| `project-a-primary-workflow-high-level.puml` | `docs/planning/` | End-to-end document processing (simplified) |
| `project-a-primary-workflow-detailed.puml` | `docs/planning/` | Detailed implementation with module references |
| `project-a-device-selection-flow.puml` | `docs/development/RAG Pipeline/` | Device priority and teacher escalation logic |

#### Level 2: Model Training

| File | Location | Purpose |
|------|----------|---------|
| `project-a-distillation.puml` | `docs/development/RAG Pipeline/` | Knowledge distillation (teacher → student) |
| `project-a-training-workflow-high-level.puml` | `docs/planning/` | ML training lifecycle overview |

#### Level 2: Data Preparation

| File | Location | Purpose |
|------|----------|---------|
| `project-a-training-data-ingestion.puml` | `docs/development/RAG Pipeline/` | Dataset collection and preparation |
| `automated-data-labeling-pipeline.puml` | `docs/planning/` | Three-layer labeling architecture |

#### Level 2: Pseudo-Labeling

| File | Location | Purpose |
|------|----------|---------|
| `diqa-pseudo-labeling-workflow.puml` | `docs/planning/` | 5-model ensemble workflow |
| `diqa-training-phases.puml` | `docs/planning/` | Training phases for ensemble models |
| `diqa-checkpoint-selection.puml` | `docs/planning/` | Weighted SRCC+ECE scoring algorithm |
| `diqa-inference-pipeline.puml` | `docs/planning/` | Modal serverless batch inference |

#### Level 2: Benchmarking & Evaluation

| File | Location | Purpose |
|------|----------|---------|
| `project-a-benchmark-workflow.puml` | `docs/planning/` | IQA model benchmarking workflow |

#### Supplementary (Test Coverage)

| File | Location | Purpose |
|------|----------|---------|
| `project-a-primary-workflow-test-coverage.puml` | `docs/planning/` | High-level with test annotations |
| `project-a-primary-workflow-detailed-test-coverage.puml` | `docs/planning/` | Detailed with test annotations |
| `project-a-training-workflow-test-coverage.puml` | `docs/planning/` | Training with test annotations |

#### Related Projects (Downstream Context)

| File | Location | Purpose |
|------|----------|---------|
| `project-b-ocr-layout-workflow.puml` | `docs/development/RAG Pipeline/` | Project B OCR orchestration |
| `project-c-fusion-chunking-workflow.puml` | `docs/development/RAG Pipeline/` | Project C fusion pipeline |
| `project-d-vectorstore-workflow.puml` | `docs/development/RAG Pipeline/` | Project D embedding pipeline |

### Diagrams to Remove (Redundant/Draft)

#### Duplicate Device Selection

| File | Reason |
|------|--------|
| `project-a-runtime-device-teacher-gating.puml` | Duplicate of `project-a-device-selection-flow.puml` |

#### Labeling Workstream Confusion

| File | Reason |
|------|--------|
| `labeling-workstreams-overview.puml` | Uses "Project A/B/C" naming that conflicts with main pipeline Projects A-D. Should be renamed or removed. |
| `project-a-arena-benchmarking.puml` | Arena concept replaced by benchmark workflow |
| `project-b-quantization.puml` | Out of scope for Project A |
| `project-c-finetuning.puml` | Covered by diqa-training-phases.puml |

#### Opus Workflows (Superseded)

| File | Reason |
|------|--------|
| `workflows_opus/model_artifact_promotion.puml` | Promote to docs if needed, otherwise redundant with project-a-distillation.puml export section |
| `workflows_opus/unified_primary_workflow.puml` | Too detailed; functionality split across retained diagrams |

#### All tmp_cleanup Diagrams (Per User Request)

All diagrams in `tmp_cleanup/workflows_*/` should be deleted:

- `workflows_gemini/` (4 files)
- `workflows_copilot/` (4 files)
- `workflows_sonnet/` (6 files)

---

## Gap Analysis

### Critical Gaps

#### 1. Layout Model Training Workflow

**Status**: MISSING (CRITICAL after scope change)
**Need**: Dedicated workflow for docling-layout training
**Impact**: Full layout analysis moved to Project A; no documentation for how the layout model is trained
**Scope Change**: Layout analysis (including reading order, table structure) now in Project A, not Project B
**Recommendation**: Create `project-a-layout-training.puml` covering:

- DocLayNet dataset preparation (80K pages, 11 classes)
- YOLOv10-nano fine-tuning process
- Reading order prediction training
- Table structure extraction training
- ONNX export and model registry integration
- Performance validation (mAP targets)

#### 2. Celery Worker Integration

**Status**: MISSING
**Need**: Task queue architecture diagram
**Impact**: Phase 4 worker pool implementation (98% complete) has no documentation
**Recommendation**: Create `project-a-worker-architecture.puml` covering:

- Worker pool topology (default, GPU, batch queues)
- Task routing logic
- Redis broker/result backend configuration
- GPU worker separation

#### 3. ~~Monitoring & Drift Detection~~ (FILLED)

**Status**: **RESOLVED** (February 2026)
**Resolution**: Created `level-2/monitoring-drift/monitoring-drift-architecture.puml` and `level-3/monitoring-drift/monitoring-drift-swimlane.puml` with complete traceability to 5,353+ LOC implementation + 5,400+ LOC tests. Includes `end-to-end-lifecycle.md` documenting the 7-phase closed-loop from drift detection through retraining.

#### 4. Budget Enforcement & Circuit Breaker

**Status**: MENTIONED BUT NOT DETAILED
**Need**: Dedicated workflow for cost controls
**Impact**: Three-tier budget enforcement (doc/batch/monthly) referenced but not visualized
**Recommendation**: Add section to `project-a-device-selection-flow.puml` or create separate diagram

### Minor Gaps

#### 5. ONNX Runtime Integration

**Status**: IMPLICIT
**Need**: Inference session management details
**Impact**: Provider selection, session caching not documented
**Recommendation**: Add notes to `project-a-primary-workflow-detailed.puml`

#### 6. Error Handling Taxonomy

**Status**: SCATTERED
**Need**: Consolidated error recovery flows
**Impact**: Graceful fallbacks mentioned but not systematically documented
**Recommendation**: Create appendix or notes section in primary workflow

---

## Inconsistency Analysis

### Model Architecture Naming

| Source | YOLO Variant Referenced |
|--------|------------------------|
| `project-a-primary-workflow-detailed.puml` | "DocLayout-YOLO" |
| `tmp_cleanup/workflows_copilot/layout_training_phase3_yolov8.puml` | "YOLOv8n/s" |
| `tmp_cleanup/workflows_sonnet/04_phase6_doclayout_yolo_training.puml` | "YOLOv10-nano" |
| CLAUDE.md | "YOLOv10-doc (specifically trained on DocLayNet)" |

**Resolution**: ~~Standardize on "DocLayout-YOLO (YOLOv10-nano)"~~ **SUPERSEDED**: Current standard is `docling-layout-egret-xlarge` (accuracy) / `docling-layout-heron` (speed). See [ML_MODEL_REGISTRY.md](../../planning/ML_MODEL_REGISTRY.md).

### DQS Weight Configurations

| Source | Weights |
|--------|---------|
| `unified_primary_workflow.puml` | blur=0.30, noise=0.25, contrast=0.20, illumination=0.15, artifacts=0.10 |
| `01_document_processing_pipeline.puml` | blur=0.25, noise=0.20, contrast=0.15, skew=0.15, lighting=0.12, compression=0.08, bleed-through=0.05 |
| CLAUDE.md (Phase 1C) | Weight calibration mentioned but values not specified |

**Resolution**: Document canonical weights in `project-a-primary-workflow-detailed.puml` and ensure consistency with `src/image_preprocessing_detector/metrics/dqs_calculator.py`.

### Labeling Workstream Naming Conflict

The `docs/development/labeling/` folder uses "Project A/B/C" to mean:

- Project A = Arena Benchmarking
- Project B = Quantization
- Project C = Fine-Tuning

This conflicts with the main pipeline where:

- Project A = Preprocessing, IQA & Full Layout (this repo)
- Project B = OCR Orchestration only (layout moved to A)
- Project C = Fusion & Chunking
- Project D = Vector Store

**Resolution**: Rename labeling workstreams to avoid confusion:

- "Arena Benchmarking Workstream" (not "Project A")
- "Quantization Workstream" (not "Project B")
- "Fine-Tuning Workstream" (not "Project C")

Or better: consolidate into the DIQA pseudo-labeling diagrams which already cover this.

### Performance Target Discrepancies

| Metric | Source A | Source B |
|--------|----------|----------|
| Student CPU latency | "≤40ms/page (target)" | "<40ms/page" vs "≤100ms (acceptable)" |
| Teacher escalation rate | "<10% of pages" | Not specified |
| IQA mAP target | ">0.88" | Not consistently referenced |

**Resolution**: Create a performance targets table in the primary workflow diagram legends.

---

## Overlap Analysis

### Redundant Device Selection Diagrams

Three diagrams cover essentially the same content:

1. `project-a-runtime-device-teacher-gating.puml` (45 lines)
2. `project-a-device-selection-flow.puml` (similar content)
3. `06_teacher_escalation_decision.puml` (347 lines, most detailed)

**Resolution**: Keep `project-a-device-selection-flow.puml`, update with detail from sonnet version, delete duplicates.

### Redundant Primary Workflow Diagrams

Five variations exist in `docs/planning/`:

1. `project-a-primary-workflow-high-level.puml` (75 lines)
2. `project-a-primary-workflow-detailed.puml` (detailed)
3. `project-a-primary-workflow-test-coverage.puml` (annotated)
4. `project-a-primary-workflow-detailed-test-coverage.puml` (combo)
5. `unified_primary_workflow.puml` (735 lines)

Plus 3+ in `tmp_cleanup/`.

**Resolution**:

- Keep high-level and detailed as separate views
- Keep test-coverage versions as CI documentation
- Delete unified (superseded by new architecture overview)
- Delete all tmp_cleanup versions

---

## Recommendations

### Immediate Actions

1. **Delete tmp_cleanup diagrams**: Remove all 14 files in `tmp_cleanup/workflows_*/`

2. **Delete duplicates**:
   - `project-a-runtime-device-teacher-gating.puml`
   - `workflows_opus/unified_primary_workflow.puml`

3. **Rename labeling diagrams**: Update naming in `docs/development/labeling/` to avoid Project A/B/C confusion

### Short-Term Actions (Next Sprint)

1. **Create layout training workflow**: Document docling-layout training process

2. **Create worker architecture diagram**: Document Celery worker integration

3. **Standardize model naming**: ~~"DocLayout-YOLO (YOLOv10-nano)"~~ **DONE**: Use `docling-layout-egret-xlarge` (accuracy) / `docling-layout-heron` (speed)

4. **Document DQS weights**: Add canonical weights to detailed workflow with source reference

### Medium-Term Actions

1. **Create monitoring/drift diagram**: Document Phase 6 infrastructure

2. **Add budget enforcement details**: Expand device selection diagram

3. **Create diagram index**: Add `docs/DIAGRAM_INDEX.md` with navigation guide

### Maintenance Guidelines

1. **Single source of truth**: Each concept should have ONE authoritative diagram
2. **Hierarchy preservation**: New diagrams should fit the established Level 0/1/2 structure
3. **Cross-references**: Use PlantUML links (`[[filename.puml]]`) between diagrams
4. **Version tracking**: Include version and date in diagram footers
5. **Test coverage alignment**: Keep test-coverage diagrams synchronized with code

---

## Diagram Hierarchy (Final)

All diagrams are now consolidated under `docs/architecture/diagrams/` with a level-based folder structure:

```text
docs/architecture/diagrams/
├── README.md                              ◄─── Quick start guide
├── INDEX.md                               ◄─── Complete traceability matrix
├── STYLE_GUIDE.md                         ◄─── Styling standards
│
├── level-0/                               ◄─── Pipeline Context (1 diagram)
│   └── rag-pipeline-overview.puml
│
├── level-1/                               ◄─── Project A Architecture (2 diagrams)
│   ├── PROJECT_A_ARCHITECTURE_OVERVIEW.puml
│   └── PROJECT_A_WORKFLOW_HIERARCHY.puml
│
├── level-2/                               ◄─── Workstream Details (28 diagrams)
│   ├── production-runtime/          (WS1)   6 diagrams
│   ├── model-training/              (WS2)   5 diagrams
│   ├── data-preparation/            (WS3)   3 diagrams
│   ├── pseudo-labeling/             (WS4)   5 diagrams
│   ├── labeling-benchmarking/       (WS5)   1 diagram
│   ├── model-arena/                 (WS6)   1 diagram
│   ├── monitoring-drift/            (WS7)   1 diagram
│   ├── synthetic-generation/        (WS8)   1 diagram
│   ├── schema-field-population/             2 diagrams (summary + full reference)
│   └── downstream-context/                  3 diagrams
│
├── level-3/                               ◄─── Module Implementation (6 swimlanes)
│   ├── production-runtime/          (WS1)   swimlane + 2 module docs
│   ├── model-training/              (WS2)   swimlane + 1 module doc
│   ├── data-preparation/            (WS3)   swimlane + 2 module docs
│   ├── pseudo-labeling/             (WS4)   swimlane + 1 module doc
│   ├── monitoring-drift/            (WS7)   swimlane + 1 module doc
│   └── synthetic-generation/        (WS8)   swimlane + 1 module doc
│
└── deprecated/                            ◄─── Superseded diagrams
    └── benchmarking/                        1 diagram
```

**Total**: 38 PUML diagrams across 4 levels + 10 module documentation files.

> **Note**: This structure reflects the February 2026 audit update. Original diagram copies may still exist in `docs/planning/` for backwards compatibility.

---

## February 2026 Audit Update

The following actions were taken to bring documentation in sync with the actual codebase:

### Gaps Filled

- **Monitoring & Drift Detection**: Level 2 architecture diagram + Level 3 swimlane + end-to-end lifecycle doc created
- **Level 3 Module Documentation**: 4 index.md files created for production-runtime, data-preparation, model-training, monitoring-drift
- **Missing SVGs**: 13 PUML files that lacked SVG renders now have generated SVGs
- **Workstreams WS5-WS8**: labeling-benchmarking, model-arena, monitoring-drift, synthetic-generation, schema-field-population all now documented in INDEX.md

### Artifacts Cleaned

- 3 nested-path SVG generation artifacts deleted (level-1, level-2/synthetic-generation, level-3/data-preparation)
- 1 stale archived file deleted (level-2/data-preparation/index.v1-archived.md)
- 11 PNG/SVG files renamed from spaces/PascalCase to kebab-case
- 4 duplicate SVGs removed (space-named duplicates of existing kebab-case SVGs)

### Stale References Fixed

- `src/.../augmentation/genalog_config.py` and `genalog_degrader.py` references updated to `src/.../synthetic/config.py`, `generator.py`, `augmentation_hybrid.py`, `schema_adapter.py` in synthetic-generation PUML and index.md

### Remaining Gaps (from original audit)

- ~~**Layout Model Training workflow**~~: **RESOLVED** (February 2026) - Created `project-a-training-infrastructure.puml` covering dataset assembly, ILP allocation, Modal GPU training, phased head training, active learning loop, and ONNX export
- ~~**Celery Worker architecture**~~: **RESOLVED** (February 2026) - Created `project-a-worker-architecture.puml` covering FastAPI, Redis broker, 3 worker pools, device orchestration, circuit breaker, and monitoring
- **Budget Enforcement details**: Partial (covered in worker-architecture diagram + device-orchestrator.md Level 3 doc)
- ~~**Level 3 for WS4, WS8**~~: **RESOLVED** (February 2026) - Created swimlane + module docs for both pseudo-labeling and synthetic-generation
- **Level 3 for WS5, WS6**: **DEFERRED** - WS5 has 0 LOC implemented; WS6 has simple linear flow with self-contained components (both explicitly state Level 3 not required in their index.md)

### PUML Syntax Issues

- ~~`project-a-training-data-ingestion.puml`~~: **FIXED** (February 2026) - Replaced stereotype-based partition colors with inline `#Color` syntax
- ~~`schema-field-population-workflow.puml`~~: **RESOLVED** (February 2026) - Created simplified `schema-field-population-summary.puml` for SVG rendering; full 387-line diagram kept as text reference

---

## Appendix: Files to Delete

### tmp_cleanup/workflows_gemini/

- `iqa_student_training_workflow.puml`
- `iqa_teacher_training_workflow.puml`
- `layout_model_training_workflow.puml`
- `ingestion_workflow.puml`

### tmp_cleanup/workflows_copilot/

- `layout_training_phase3_yolov8.puml`
- `iqa_dataset_generation_and_versioning.puml`
- `model_artifact_promotion.puml`
- `document_processing_workflow.puml`

### tmp_cleanup/workflows_sonnet/

- `01_document_processing_pipeline.puml`
- `01_document_processing_pipeline_detail.puml`
- `04_phase6_doclayout_yolo_training.puml`
- `05_dataset_generation_100k.puml`
- `06_teacher_escalation_decision.puml`
- `07_dpi_upscaling_preflight.puml`

### docs/development/RAG Pipeline/

- `project-a-runtime-device-teacher-gating.puml` (duplicate)

### docs/planning/workflows_opus/

- `model_artifact_promotion.puml`
- `unified_primary_workflow.puml`

### docs/development/labeling/ (rename or merge)

- `labeling-workstreams-overview.puml` → merge into diqa diagrams
- `project-a-arena-benchmarking.puml` → merge into benchmark workflow
- `project-b-quantization.puml` → out of scope
- `project-c-finetuning.puml` → covered by diqa-training-phases
