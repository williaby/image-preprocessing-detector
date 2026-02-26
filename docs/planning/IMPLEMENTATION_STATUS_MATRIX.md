---
title: Planning Document Implementation Status Matrix
schema_type: common
status: active
owner: core-maintainer
purpose: "Track implementation status of all planning documents with source code mappings."
tags:
- planning
- tracking
- status
---

# Planning Document Implementation Status Matrix

> **Last Updated**: 2026-02-21
> **Documents Tracked**: 21
> **Purpose**: Map each planning document to its implementation status and source code modules

## Status Legend

| Icon | Status | Meaning |
|------|--------|---------|
| ✅ | Complete | Fully implemented with tests |
| ⚠️ | Partial | Some components implemented, work in progress |
| 📋 | Design-Only | Planning/design document, no implementation yet |
| 🔄 | Superseded | Replaced by newer planning or approach |
| 📊 | Reference | Analysis/report document, not for implementation |

---

## Summary Table

| Document | Status | % Complete | Key Modules | Last Verified |
|----------|--------|------------|-------------|---------------|
| **[MASTER_PROJECT_PLAN.md](#master_project_planmd)** | ✅ | **Primary** | **Consolidated roadmap — use this** | 2026-02-21 |
| [docs/PROJECT_OVERVIEW.md](#project_overviewmd) | ✅ | Reference | System narrative — target-state architecture | 2026-02-21 |
| [PROJECT_PLAN.md](#project_planmd) | 🔄 | Superseded | See MASTER_PROJECT_PLAN.md | 2026-02-21 |
| [SIGLIP2_MULTITASK_REQUIREMENTS.md](#siglip2_multitask_requirementsmd) | 📋 | 0% | None | 2026-02-10 |
| [DATASET_DIVERSITY_REQUIREMENTS.md](#dataset_diversity_requirementsmd) | ⚠️ | 25% | `synthetic/` | 2026-02-10 |
| [TRAINING_OPTIMIZATION_PLAN.md](#training_optimization_planmd) | 📋 | 0% | None | 2026-02-10 |
| [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](#mobileclip2_s4_s0_dataset_designmd) | ✅ | 100% | Training dataset ready | 2026-02-10 |
| [STREAM_1_SCHEMA_ANALYSIS.md](#stream_1_schema_analysismd) | ⚠️ | 65% | `schema_utils/` | 2026-02-10 |
| [METADATA_ANNOTATION_REFACTORING_PLAN.md](#metadata_annotation_refactoring_planmd) | ⚠️ | 85% | `annotation/` | 2026-02-10 |
| [UNIFIED_LABELING_STRATEGY.md](#unified_labeling_strategymd) | ⚠️ | 40% | `annotation/`, `labeling/` | 2026-02-10 |
| [PSEUDO_LABELING_PROJECT_PLAN.md](#pseudo_labeling_project_planmd) | ⚠️ | 35% | `annotation/enrichment/` | 2026-02-10 |
| [PSEUDO_LABELING_STATUS_REPORT.md](#pseudo_labeling_status_reportmd) | 📊 | N/A | Reference document | 2026-02-10 |
| [SIGLIP2_LARGE_400M_TRAINING_LOG.md](#siglip2_large_400m_training_logmd) | 📋 | 0% | None (planning) | 2026-02-10 |
| [SYNTHETIC_REAL_TRAINING_METHODOLOGY.md](#synthetic_real_training_methodologymd) | 📋 | 0% | None | 2026-02-10 |
| [SCRIPT_TAXONOMY.md](#script_taxonomymd) | ⚠️ | 70% | `schema_utils/script_ml_mapping.py` | 2026-02-10 |
| [PREPARE_DOC_TO_UNIFY_HANDOFF_SPECIFICATION.md](#project_a_to_b_handoff_specificationmd) | ⚠️ | 80% | `schema.py`, `output/` | 2026-02-10 |
| [ANNOTATION_TEST_ANALYSIS.md](#annotation_test_analysismd) | 📊 | N/A | Analysis document | 2026-02-10 |
| [DATA_AVAILABILITY_REPORT.md](#data_availability_reportmd) | 📊 | N/A | Reference document | 2026-02-10 |
| [DATASET_AUDIT_REPORT.md](#dataset_audit_reportmd) | 📊 | N/A | Reference document | 2026-02-10 |
| [DATASET_GAPS_REPORT.md](#dataset_gaps_reportmd) | 📊 | N/A | Reference document | 2026-02-10 |
| [PHASE_10_11_RESTRUCTURED_PLAN.md](#phase_10_11_restructured_planmd) | 🔄 | Superseded | See MASTER_PROJECT_PLAN.md | 2026-02-21 |

---

## Implementation Details

### PROJECT_PLAN.md

**Status**: 🔄 Superseded

> **Superseded by [PHASE_10_11_RESTRUCTURED_PLAN.md](#phase_10_11_restructured_planmd)** (2026-02-21).
> Retain for historical context. Phase numbering (0–9), layout model (YOLOv10-doc), and ML IQA
> architecture (ResNet-50/18) in this document are outdated. Current architecture uses SigLIP 2 +
> MobileNetV4, and docling-layout-egret-xlarge / docling-layout-heron.

**Historical Phase Completion (as of supersession)**:

- Phase 0–3, 6: ✅ Complete
- Phase 4: ✅ 98% (async I/O deferred)
- Phase 5: ⚠️ 40% (API endpoints stubbed)
- Phase 7, 9: ❌ Not started (absorbed into value streams in PHASE_10_11_RESTRUCTURED_PLAN.md)

---

### SIGLIP2_MULTITASK_REQUIREMENTS.md

**Status**: 📋 Design-Only (0%)

**Description**: Multi-task training plan for SigLIP 2 with 19 heads across 5 groups (IQA, Script, Orientation+Skew, Handwriting, Page Attributes). Two-model pipeline with MobileNetV4-Conv-S pre-correction check.

**Implementation Status**:

- ❌ No SigLIP 2 inference wrapper exists
- ❌ No MobileNetV4 integration
- ✅ SigLIPProvider exists but uses older SigLIP Base 86M model (single-task IQA only)
- ❌ Multi-head architecture not implemented
- ❌ Character-height-aware resolution not implemented

**Related Code**:

- `annotation/enrichment/providers/siglip.py` - Single-task IQA provider (existing)
- No multi-task code exists yet

**Dependencies**:

- Training datasets: orientation (50K ready), skew/resolution/handwriting (pending)
- SigLIP 2 model training (not started)
- MobileNetV4 model training (not started)

**Next Steps**:

1. Complete dataset generation (DATASET_DIVERSITY_REQUIREMENTS.md)
2. Train SigLIP 2 multi-task model
3. Implement multi-head inference wrapper
4. Integrate MobileNetV4 pre-correction model

---

### DATASET_DIVERSITY_REQUIREMENTS.md

**Status**: ⚠️ Partial (25%)

**Description**: 10 training dataset specifications with 14 diversity dimensions for multi-task model training.

**Implementation Status**:

- ✅ Orientation dataset: 50K images at `E:\03_training_datasets\orientation`
- ⚠️ Synth-multiscript: 250K target (~27K partial on GCS)
- ❌ Skew dataset: 40K needed, not started
- ❌ Resolution quality dataset: 30K needed, not started
- ❌ Handwriting dataset: 60K needed, not started
- ❌ Capture method dataset: 50K needed, not started
- ❌ Shadow/Warping/Code datasets: Not started

**Key Modules**:

- `synthetic/generator.py` - Document generation (supports multi-task metadata)
- `synthetic/config.py` - DPI tiers, ColorMode, augmentation profiles
- `synthetic/augmentation_hybrid.py` - AGED/HISTORICAL degradation
- `synthetic/schema_adapter.py` - Multi-task metadata nesting

**Implemented Features**:

- ✅ 7 DPI tiers (72/100/150/200/300/400/600)
- ✅ ColorMode enum (binarized/grayscale/color)
- ✅ Skew, orientation, char_height measurement
- ✅ Document age profiles (MODERN/AGED/HISTORICAL)
- ✅ Multi-task metadata schema adapter

**Missing Features**:

- ❌ Global split registry (SHA256-keyed)
- ❌ Automated diversity dimension tracking
- ❌ Dataset sufficiency validation

---

### TRAINING_OPTIMIZATION_PLAN.md

**Status**: 📋 Design-Only (0%)

**Description**: 5-model consensus plan for ILP-based dataset allocation, multi-task training with Kendall uncertainty weighting, and active learning.

**Implementation Status**:

- ❌ ILP optimization (PuLP/OR-Tools) not implemented
- ❌ Active learning triggers not implemented
- ❌ Multi-task training (Kendall, PCGrad) not implemented
- ❌ Phased head training not implemented

**Related Code**: None exists

**Dependencies**:

- Requires completed datasets (DATASET_DIVERSITY_REQUIREMENTS.md)
- Requires SigLIP 2 multi-task model architecture
- Training infrastructure exists (Modal integration ready)

---

### MOBILECLIP2_S4_S0_DATASET_DESIGN.md

**Status**: ✅ Complete (100%)

**Description**: 50K orientation detection dataset design specification.

**Implementation Status**:

- ✅ Dataset generated: 50,000 images at `E:\03_training_datasets\orientation`
- ✅ 4-class orientation (0°/90°/180°/270°)
- ✅ Balanced distribution
- ✅ Multi-script coverage
- ✅ Quality diversity

**Location**: `E:\image_detection\03_training_datasets\orientation`

**Related Docs**: [TRAINING_DATASET_QUICK_REFERENCE.md](../datasets/TRAINING_DATASET_QUICK_REFERENCE.md)

---

### STREAM_1_SCHEMA_ANALYSIS.md

**Status**: ⚠️ Partial (65%)

**Description**: Schema utilities analysis and config-driven architecture proposal.

**Implementation Status**:

- ✅ Layout taxonomy: `schema_utils/layout_taxonomy.py` + `config/layout_taxonomy.yaml`
- ✅ Script ML mapping: `schema_utils/script_ml_mapping.py` + `config/script_ml_mapping.yaml`
- ✅ ISO language/script: `schema_utils/iso_language_script.py`
- ✅ ISO paper sizes: `schema_utils/iso_paper_sizes.py`
- ✅ Degradation mapping: `schema_utils/degradation_mapping.py`
- ✅ Text scope: `schema_utils/text_scope.py`
- ✅ Dataset source: `schema_utils/dataset_source.py`
- ⚠️ Main schema.py: NOT yet updated with new enums/types (still uses old patterns)

**Key Modules**:

- `schema_utils/` - 10+ utility modules with YAML-driven configs
- `config/` - YAML config files (layout_taxonomy.yaml, script_ml_mapping.yaml)
- `cli_layout.py` - CLI for layout taxonomy operations

**Missing**:

- ❌ schema.py refactoring to use new schema_utils
- ❌ Migration path from old to new schema patterns
- ❌ Integration tests for schema_utils in main pipeline

---

### METADATA_ANNOTATION_REFACTORING_PLAN.md

**Status**: ⚠️ Partial (85%)

**Description**: Refactoring monolithic annotate_base_metadata.py into modular annotation package.

**Implementation Status**:

- ✅ Phase 1 (Foundation): 25/27 tasks - Schema, config, base classes
- ✅ Phase 2 (Core Refactoring): 36/36 tasks - 45+ parsers, 524 tests
- ✅ Phase 3 (Extensibility): 14/14 tasks - Plugin architecture, 139 tests
- ✅ Phase 4 (ML Integration): 9/18 tasks - SigLIPProvider core, optional enhancements deferred
- ✅ Phase 5 (Production Hardening): 24/24 tasks - 833 tests, 80% coverage
- ❌ Phase 6 (Test Hardening): 0/30 tasks - Not started (see ANNOTATION_TEST_ANALYSIS.md)

**Key Modules**:

- `annotation/parsers/` - 45+ dataset parsers across 6 categories
- `annotation/schemas/` - Immutable, enrichment, sample schemas
- `annotation/config/` - Dataset configs, tiers, settings
- `annotation/workflow/` - Pipeline, orchestrator, scanner, progress
- `annotation/enrichment/` - SigLIPProvider, YOLOProvider, manager
- `annotation/storage/` - Parquet writer, cache
- `annotation/integrity/` - Hashing, checkpointing, atomic ops

**Files**:

- 85+ source files in `annotation/` module
- 802 tests in `tests/unit/annotation/`
- 80% test coverage

**Missing**:

- ❌ Phase 6: E2E tests, integration test hardening, error path coverage
- ❌ Optional: VLM providers (GPT-4V, Gemini Vision)
- ❌ Optional: Advanced enrichment (table/figure extraction)

---

### UNIFIED_LABELING_STRATEGY.md

**Status**: ⚠️ Partial (40%)

**Description**: Soft-label pseudo-labeling strategy using DocIQ architecture and DeQA-Doc approach.

**Implementation Status**:

- ✅ Three-layer metadata architecture implemented
- ✅ SigLIPProvider for quality score prediction
- ✅ EnrichmentManager with tier ordering
- ⚠️ Soft-label distribution regression (partial - single MOS score, not 10-bin distribution)
- ❌ Full corpus pseudo-labeling (not started)
- ❌ KL-divergence training (not implemented)

**Key Modules**:

- `annotation/enrichment/providers/siglip.py` - Quality prediction (single score)
- `annotation/enrichment/manager.py` - Provider orchestration
- `annotation/schemas/enrichment.py` - EnrichmentData schema

**Related Scripts**:

- `scripts/annotate_base_metadata.py` - Layer 1 (IMMUTABLE) + Layer 2 (ENRICHMENT)
- `scripts/build_training_labels.py` - Layer 3 (TRAINING)

**Missing**:

- ❌ Soft-label distribution output (currently single float MOS)
- ❌ Uncertainty estimation
- ❌ Confidence tier classification
- ❌ Full DocIQ-Replica model integration (1600x1600 resolution)

---

### PSEUDO_LABELING_PROJECT_PLAN.md

**Status**: ⚠️ Partial (35%)

**Description**: Project plan to generate pseudo-labels for ~2.5M images using DocIQ-Replica model.

**Implementation Status**:

- ✅ Three-layer metadata architecture: 100%
- ✅ Stage 1 DocIQ-Replica training: 100%
- ✅ Stage 2 Phase 1 warmup: 100%
- ✅ 12,742 layout masks generated
- ✅ Modal infrastructure ready
- ❌ Stage 2 Phase 2 fine-tuning: 0% (budget exhausted)
- ❌ Full corpus pseudo-labels: 0%
- ❌ DeQA-Doc anchor labels: 0%

**Key Modules**:

- `annotation/enrichment/providers/siglip.py` - Quality prediction wrapper
- Modal scripts (external): `modal/generate_pseudo_labels.py`

**Blockers**:

- Budget constraint ($80-140 estimated for completion)
- Requires Stage 2 Phase 2 training completion
- Waiting on training infrastructure access

---

### PSEUDO_LABELING_STATUS_REPORT.md

**Status**: 📊 Reference (N/A)

**Type**: Status report tracking pseudo-labeling workflow progress

**Purpose**: Documents current state, label coverage, automated labeling capabilities, and resolution requirements (1600x1600 proven necessary).

**Key Findings**:

- Only DIQA-5000 (5,500 images, 0.2% of corpus) has 3-dimension human MOS
- Training at <1600x1600 was proven ineffective
- Stage 1 complete, Stage 2 Phase 2 not started

---

### SIGLIP2_LARGE_400M_TRAINING_LOG.md

**Status**: 📋 Design-Only (0%)

**Description**: Training log/planning for SigLIP 2 Large 400M model to achieve VQualA ≥0.92.

**Implementation Status**:

- ✅ SigLIP Base 86M trained (VQualA 0.886, SRCC 0.896)
- ❌ SigLIP 2 Large 400M training not started
- ❌ Multi-model consensus recommendations not implemented

**Related Code**:

- `annotation/enrichment/providers/siglip.py` - Currently uses Base 86M model

**Next Steps** (from planning):

- Train SigLIP 2 Large with CosineAnnealingLR
- Implement PCGrad for multi-task
- Test 1296+ patches resolution
- Implement ranking loss

---

### SYNTHETIC_REAL_TRAINING_METHODOLOGY.md

**Status**: 📋 Design-Only (0%)

**Description**: Curriculum learning approach: Synthetic foundation → Mixed training → Real fine-tuning → Active learning.

**Implementation Status**:

- ❌ Stage 1: Synthetic foundation training not started
- ❌ Stage 2: Mixed training not started
- ❌ Stage 3: Real fine-tuning not started
- ❌ Stage 4: Active learning not started

**Related Code**:

- `synthetic/` module exists for dataset generation
- Training infrastructure ready (Modal integration)
- No training scripts implemented

**Dependencies**:

- Requires synth-multiscript 250K dataset completion
- Requires multi-task model architecture

---

### SCRIPT_TAXONOMY.md

**Status**: ⚠️ Partial (70%)

**Description**: Hierarchical script classification with 4-class CJK internal model and post-processing.

**Implementation Status**:

- ✅ Script ML mapping implemented: `schema_utils/script_ml_mapping.py`
- ✅ Config-driven: `config/script_ml_mapping.yaml`
- ✅ ISO 15924 script codes
- ✅ External classes (10 user-facing)
- ⚠️ Internal training classes (13 classes) - config exists but no trained model
- ⚠️ Post-processing logic for CJK derivation - function signature exists, not fully tested

**Key Modules**:

- `schema_utils/script_ml_mapping.py` - Script taxonomy resolver
- `config/script_ml_mapping.yaml` - Script definitions

**Missing**:

- ❌ Trained multi-script detection model
- ❌ CJK post-processing integration in inference pipeline
- ❌ End-to-end validation with real documents

---

### PREPARE_DOC_TO_UNIFY_HANDOFF_SPECIFICATION.md

**Status**: ⚠️ Partial (80%)

**Description**: Complete specification of DocumentMetadata.json format for Unify handoff.

**Implementation Status**:

- ✅ DocumentMetadata schema: `schema.py`
- ✅ JSON output generation: `output/json_generator.py`
- ✅ Corrected images output
- ✅ DQS calculation: `metrics/dqs_calculator.py`
- ✅ Routing recommendations: `routing/recommendation_engine.py`
- ✅ PDF type classification: `classification/pdf_type_classifier.py`
- ⚠️ Layout-lite metadata (partial - infrastructure exists, accuracy needs improvement)
- ⚠️ Multi-language detection (basic implementation, not production-ready)

**Key Modules**:

- `schema.py` - DocumentMetadata, PageMetadata, DetectedIssue
- `output/json_generator.py` - JSON serialization
- `metrics/dqs_calculator.py` - DQS calculation
- `routing/recommendation_engine.py` - OCR routing logic

**Missing**:

- ❌ Full validation against Unify ingestion requirements
- ❌ Schema versioning/migration support
- ⚠️ Layout-lite accuracy (<85% F1 currently)

---

### ANNOTATION_TEST_ANALYSIS.md

**Status**: 📊 Reference (N/A)

**Type**: Test quality analysis report for annotation module

**Purpose**: Identifies quality issues, mock overuse, missing E2E coverage in 802 annotation tests.

**Key Findings**:

- 0 E2E annotation tests (critical gap)
- ~80 tests (10%) heavily mocked
- ~47 tests (6%) with weak assertions
- ~5% error path coverage (target: 30%)

**Recommendations**: Tracked in METADATA_ANNOTATION_REFACTORING_PLAN.md Phase 6

---

### DATA_AVAILABILITY_REPORT.md

**Status**: 📊 Reference (N/A)

**Type**: Dataset availability audit report

**Purpose**: Documents which datasets have images, Docling OCR text, and DocLayout-YOLO labels.

**Key Stats**:

- 48/50 image datasets available on E drive (100% of image datasets)
- 7 datasets with Docling OCR text (14%)
- 7 datasets with DocLayout-YOLO labels (14%)
- ~2,064,000+ total images on disk

---

### DATASET_AUDIT_REPORT.md

**Status**: 📊 Reference (N/A)

**Type**: Dataset documentation compliance audit

**Purpose**: Tracks documentation, metadata, parser, cross-file, and aggregation status for 50 datasets.

**Key Metrics**:

- Documentation: 2 complete, 46 partial, 2 missing
- Metadata: 27 complete, 5 partial, 18 missing
- Parser: 31 complete, 10 partial, 9 missing
- Cross-file: 45 complete, 5 partial, 0 missing
- Aggregation: 11 complete, 9 partial, 30 missing

---

### DATASET_GAPS_REPORT.md

**Status**: 📊 Reference (N/A)

**Type**: Data availability gaps tracking

**Purpose**: Tracks missing images, text, and COCO layout annotations across datasets.

**Key Stats**:

- 9 datasets have both text + COCO (~931K images, 27%)
- 29 datasets have text only (~785K images, 23%)
- 2 datasets have COCO only (~578K images, 17%)
- 10 datasets have neither (~1.08M images, 31%)

---

### PHASE_10_11_RESTRUCTURED_PLAN.md

**Status**: ⚠️ Active (current master plan)

**Description**: Value-stream-organized plan for remaining work. Supersedes PROJECT_PLAN.md
(Phase 0–9 structure). 5-model consensus validated (avg 8.4/10). Organizes work into 8 parallel
streams: Schema, Heuristics, Benchmarking, Teacher Model (SigLIP 2), DoclingRouter, Classical
Geometric Corrections, Pseudo-Labeling, Student Distillation.

**Stream Status** (as of 2026-02-21):

- Stream 1 (Schema): ✅ Complete — schema_utils/, config/
- Stream 2 (Heuristics): ✅ Complete — shadow, warping, orientation heuristics
- Stream 3 (Benchmarking): ✅ Complete — go/no-go decisions confirmed
- Stream 4A (Architecture): ✅ Complete — `modal/train_siglip2_multitask.py` written
- Stream 4B (Dataset Prep): ⚠️ In progress — Phase 3 severity labeling running; Phases 5–7 deferred
- Stream 4C (OOD/Diversity): ✅ Complete — DDR framework, OOD registry, remediation plan
- Stream 5 (DoclingRouter): ⚠️ In progress — `routing/docling_router.py` exists
- Stream 6 (Geometric): ⚠️ In progress — border removal, perspective correction created
- Stream 7–8 (Pseudo-labels, Distillation): ❌ Not started — gated on Stream 4 training

**Layout model**: docling-layout-egret-xlarge (accuracy) / docling-layout-heron (speed)

**Key Documents**:

- [STREAM_4_IMPLEMENTATION_PLAN.md](STREAM_4_IMPLEMENTATION_PLAN.md) — Stream 4 detail
- [STREAM_4C_DATASET_HANDOFF.md](STREAM_4C_DATASET_HANDOFF.md) — Dataset prep handoff
- [HANDOFF_REMAINING_PHASES.md](HANDOFF_REMAINING_PHASES.md) — Phases 5–7 deferred work
- [ML_MODEL_REGISTRY.md](ML_MODEL_REGISTRY.md) — All model specs

---

## Verification Methodology

For each document, verification included:

1. **Reading planning document** (first 100-200 lines) to understand scope
2. **Checking source code** in `src/image_preprocessing_detector/` for matching modules
3. **Reviewing test coverage** in `tests/` for implementation evidence
4. **Cross-referencing** with PROJECT_PLAN.md phase completion status
5. **Validating** against CLAUDE.md project status

## Update Frequency

This matrix should be updated:

- After completing any planning document implementation
- When new planning documents are created
- Monthly as part of project status review
- Before major releases

## Related Documentation

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Master project plan with phase breakdowns
- [CLAUDE.md](../../CLAUDE.md) - Project context and current status
- [docs/architecture/](../architecture/) - Architecture documentation system
- [docs/datasets/](../datasets/) - Dataset documentation

---

**Note**: This matrix reflects status as of 2026-02-10. For real-time implementation status, consult git commit history and CI/CD pipeline results.
