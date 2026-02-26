---
owner: docs-team
purpose: Index and navigation for diagram  & traceability matrix.
schema_type: common
status: active
tags:
- architecture
- documentation
title: Diagram Index & Traceability Matrix
---

**Date**: February 2026
**Purpose**: Maps PlantUML diagrams to source files, scripts, and documentation

## Quick Navigation

| Workstream | Level | Primary Diagrams | Key Documentation |
|------------|-------|------------------|-------------------|
| [Pipeline Context](#level-0-pipeline-context) | 0 | level-0/rag-pipeline-overview.puml | - |
| [Architecture Overview](#level-1-architecture-overview) | 1 | level-1/PREPARE_DOC_*.puml | This document |
| [Production Runtime](#production-runtime-workstream) | 2 | level-2/production-runtime/*.puml | api/*.md |
| [Model Training](#model-training-workstream) | 2 | level-2/model-training/*.puml | SIGLIP2_MULTITASK_REQUIREMENTS.md |
| [Data Preparation](#data-preparation-workstream) | 2 | level-2/data-preparation/*.puml | DATASET_CATALOG.md |
| [Pseudo-Labeling](#pseudo-labeling-workstream) | 2 | level-2/pseudo-labeling/*.puml | benchmarks/README.md |
| [Labeling & Benchmarking](#labeling--benchmarking-workstream) | 2 | level-2/labeling-benchmarking/*.puml | - |
| [Model Arena](#model-arena-workstream) | 2 | level-2/model-arena/*.puml | - |
| [Monitoring & Drift](#monitoring--drift-workstream) | 2, 3 | level-2/monitoring-drift/*.puml | monitoring/drift-detection.md |
| [Synthetic Generation](#synthetic-generation-workstream) | 2 | level-2/synthetic-generation/*.puml | - |
| [Schema Field Population](#schema-field-population-workstream) | 2 | level-2/schema-field-population/*.puml | - |
| [Downstream Context](#downstream-context) | 2 | level-2/downstream-context/*.puml | - |
| [Level 3 Details](#level-3-module-implementation) | 3 | level-3/*/*.puml | Swimlane + module docs |

---

## Diagram Hierarchy

All diagrams are organized in a level-based folder structure:

```text
docs/architecture/diagrams/
├── README.md                              # Quick start guide
├── INDEX.md                               # Traceability matrix (this file)
├── STYLE_GUIDE.md                         # Styling standards
│
├── level-0/                               # Pipeline Context
│   ├── index.md
│   └── rag-pipeline-overview.puml
│
├── level-1/                               # Prepare-Doc Architecture
│   ├── index.md
│   ├── PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml
│   └── PREPARE_DOC_WORKFLOW_HIERARCHY.puml
│
├── level-2/                               # Workstream Details
│   ├── production-runtime/                # WS1
│   │   ├── index.md
│   │   ├── prepare-doc-primary-workflow-high-level.puml
│   │   ├── prepare-doc-primary-workflow-detailed.puml
│   │   ├── prepare-doc-device-selection-flow.puml
│   │   ├── prepare-doc-worker-architecture.puml
│   │   ├── prepare-doc-primary-workflow-test-coverage.puml
│   │   └── prepare-doc-primary-workflow-detailed-test-coverage.puml
│   │
│   ├── model-training/                    # WS2
│   │   ├── index.md
│   │   ├── prepare-doc-training-workflow-high-level.puml
│   │   ├── prepare-doc-training-infrastructure.puml
│   │   ├── prepare-doc-training-workflow-v2.puml  (LEGACY)
│   │   ├── prepare-doc-distillation.puml
│   │   └── prepare-doc-training-workflow-test-coverage.puml
│   │
│   ├── data-preparation/                  # WS3
│   │   ├── index.md
│   │   ├── prepare-doc-training-data-ingestion.puml
│   │   ├── automated-data-labeling-pipeline.puml
│   │   ├── metadata-schema-architecture.puml
│   │   ├── resolution-quality-labeling-pipeline.puml
│   │   ├── skew-orientation-labeling-pipeline.puml
│   │   ├── stream-4c-dataset-preparation.puml      [Stream 4C 3-stage pipeline]
│   │   ├── l2-metadata-enrichment.puml             [labeling scripts → L2 v2.4.0 registry feedback]
│   │   ├── unified-training-corpus-architecture.puml  [UTC: one corpus, all heads via filtered views]
│   │   └── corpus-split-lifecycle.puml             [split assignment, reserved pool, OOD promotion]
│   │
│   ├── pseudo-labeling/                   # WS4
│   │   ├── index.md
│   │   ├── diqa-pseudo-labeling-workflow.puml
│   │   ├── diqa-training-phases.puml
│   │   ├── diqa-checkpoint-selection.puml
│   │   ├── diqa-inference-pipeline.puml
│   │   └── soft-label-pipeline-integration.puml
│   │
│   ├── labeling-benchmarking/             # WS5
│   │   ├── index.md
│   │   ├── domain-classification-pipeline.puml
│   │   └── domain-classification-pipeline.md
│   │
│   ├── model-arena/                       # WS6
│   │   ├── index.md
│   │   └── model-arena-architecture.puml
│   │
│   ├── monitoring-drift/                  # WS7
│   │   ├── index.md
│   │   └── monitoring-drift-architecture.puml
│   │
│   ├── synthetic-generation/              # WS8
│   │   ├── index.md
│   │   └── synthetic-generation-architecture.puml
│   │
│   ├── schema-field-population/           # Cross-cutting
│   │   ├── index.md
│   │   ├── schema-field-population-summary.puml
│   │   └── schema-field-population-workflow.puml  (text reference only)
│   │
│   └── downstream-context/                # External
│       ├── index.md
│       ├── unify-ocr-layout-workflow.puml
│       ├── chunk-fusion-chunking-workflow.puml
│       └── embed-vectorstore-workflow.puml
│
├── level-3/                               # Module Implementation
│   ├── production-runtime/                # WS1 details
│   │   ├── index.md
│   │   ├── production-runtime-swimlane.puml
│   │   ├── pipeline-state-machine.md
│   │   └── device-orchestrator.md
│   │
│   ├── data-preparation/                  # WS3 details
│   │   ├── index.md
│   │   ├── data-preparation-swimlane.puml
│   │   ├── metadata-schema-versioning.md
│   │   └── label-parsing-generation.md
│   │
│   ├── model-training/                    # WS2 details
│   │   ├── index.md
│   │   ├── model-training-swimlane.puml
│   │   └── layout-fusion-downsampler.md
│   │
│   ├── monitoring-drift/                  # WS7 details
│   │   ├── index.md
│   │   ├── monitoring-drift-swimlane.puml
│   │   └── end-to-end-lifecycle.md
│   │
│   ├── pseudo-labeling/                   # WS4 details
│   │   ├── index.md
│   │   ├── pseudo-labeling-swimlane.puml
│   │   └── ensemble-stacking.md
│   │
│   └── synthetic-generation/              # WS8 details
│       ├── index.md
│       ├── synthetic-generation-swimlane.puml
│       └── augmentation-pipeline.md
│
└── deprecated/                            # Superseded diagrams
    ├── README.md
    └── benchmarking/
        ├── index.md
        └── project-a-benchmark-workflow.puml
```

---

## Level 0: Pipeline Context

### rag-pipeline-overview.puml

**Location**: `level-0/`

**Purpose**: Multi-track RAG pipeline architecture showing parallel document and audio processing tracks converging to unified Docling DOM.

| Component | Repository | Key Documentation |
|-----------|------------|-------------------|
| **Pipeline Orchestration** |||
| rag-processor | github.com/ByronWilliamsCPA/rag-processor | PROJECT_A_INTEGRATION_GUIDE.md |
| Web UI / Content Routing | rag-processor | - |
| **Track 1: Document Processing** |||
| Prepare-Doc | image-detection (this repo) | CLAUDE.md, PROJECT_PLAN.md |
| Unify | (Not yet started) | project-b-f-nf.md |
| **Track 2: Audio/Video Processing** |||
| Audio Processor | github.com/ByronWilliamsCPA/audio-processor | PIPELINE-INTEGRATION-SUMMARY.md |
| **Downstream Processing** |||
| Chunk | (Not yet started) | chunk-f-nf.md |
| Embed | (Not yet started) | - |

**Content Sources**:

| Source Type | Formats | Routing Target |
|-------------|---------|----------------|
| Documents | PDF, DOCX, PPTX | Prepare-Doc |
| Images | PNG, JPG, TIFF | Prepare-Doc |
| Audio | MP3, WAV, M4A, FLAC, OGG, AAC | Audio Processor |
| Video | MP4, MOV, AVI, MKV, WEBM | Audio Processor |

**API Contract (rag-processor -> Prepare-Doc)**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/process` | POST | Accept multipart form data |
| `/status/{job_id}` | GET | Processing status updates |
| `/results/{job_id}` | GET | Deliver processed output |
| `/health` | GET | Service health check |

**Integration Points**:

- **Unify DOM Unification**: Single Docling instance handles all preprocessed inputs (document + audio)
- **Downstream Transparency**: Unified Docling DOM consumed identically by Projects C & D
- **Performance**: 10-page doc <30s, 100-page <2min; audio <1min/hour

**Related Repositories**:

- [rag-processor](https://github.com/ByronWilliamsCPA/rag-processor) - Pipeline frontend and orchestration
- [audio-processor](https://github.com/ByronWilliamsCPA/audio-processor) - Parallel audio/video track

---

## Level 1: Architecture Overview

### PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml

**Location**: `level-1/`

**Purpose**: Complete system architecture showing all four workstreams.

| Section | Source Files | Documentation |
|---------|--------------|---------------|
| RAG Ecosystem | External repos | - |
| Production Runtime | See Production Runtime table | api/*.md |
| Model Training | See Model Training table | ADRs/0028-*.md (SUPERSEDED), [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md), [DATASET_DIVERSITY_REQUIREMENTS.md](../../../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |
| Data Preparation | See Data Preparation table | DATASET_CATALOG.md |
| Pseudo-Labeling | See Pseudo-Labeling table | benchmarks/README.md |

### PREPARE_DOC_WORKFLOW_HIERARCHY.puml

**Location**: `level-1/`

**Purpose**: Swimlane diagram showing data flow between workstreams.

---

## Data Preparation Workstream

### prepare-doc-training-data-ingestion.puml

**Location**: `level-2/data-preparation/`

**Purpose**: Dataset collection, normalization, and split creation.

| Component | Source Files | Scripts | Documentation |
|-----------|--------------|---------|---------------|
| **Layer 1: IMMUTABLE** ||||
| Field harmonization | - | scripts/annotate_base_metadata.py | DATASET_CATALOG.md |
| COCO label parsers | - | scripts/annotate_base_metadata.py | - |
| Bbox serialization | - | scripts/annotate_base_metadata.py | - |
| Derived counts | - | scripts/annotate_base_metadata.py | - |
| **Layer 2: ENRICHMENT** ||||
| Versioned enrichment | - | scripts/annotate_base_metadata.py | - |
| Phase 9 content flags | - | scripts/annotate_base_metadata.py | - |
| Capture method | - | scripts/annotate_base_metadata.py | - |
| Layout label taxonomy | src/.../schema_utils/layout_taxonomy.py | scripts/standardize_layout_labels.py | config/layout_taxonomy.yaml |
| **Layer 3: TRAINING** ||||
| 45-dimensional IQA vector | - | scripts/build_training_labels.py | - |
| Anchor score computation | - | scripts/build_training_labels.py | - |
| Score normalization | - | scripts/build_training_labels.py | - |
| Element labels | - | scripts/build_training_labels.py | - |

### automated-data-labeling-pipeline.puml

**Location**: `level-2/data-preparation/`

**Purpose**: Three-layer labeling architecture.

**Dataset Download Scripts**:

| Dataset | Script | Documentation |
|---------|--------|---------------|
| All datasets | scripts/download_all_datasets.py | DATASET_CATALOG.md |
| IQA datasets | scripts/download_iqa_datasets.py | DATASET_CATALOG.md |
| Phase 3 datasets | scripts/download_phase3_datasets.py | - |
| Table datasets | scripts/download_table_datasets.py | - |
| DocBank | scripts/download_docbank.py | - |
| OmniDocBench | scripts/download_omnidocbench.py | - |
| ViDoRe Finance | scripts/download_vidore_finance.py | - |
| DIQA-5000 upload | scripts/upload_diqa5000_to_gcs.py | - |

### metadata-schema-architecture.puml

**Location**: `level-2/data-preparation/`

**Purpose**: Three-layer metadata architecture (Immutable → Enrichment → Training) showing data flow from source datasets through schema utilities to training.

### unified-training-corpus-architecture.puml

**Location**: `level-2/data-preparation/`

**Purpose**: Unified Training Corpus (UTC) architecture — single corpus serving all 25 training heads via filtered views. Replaces the N per-head dataset approach.

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Tier A Synthetic | synth-multiscript-v3 + 7 derived task views | docs/datasets/training/synth-multiscript-v3.md |
| Tier B Real-World | 57 source datasets, ~3.3M total samples | docs/datasets/DATASET_QUICK_REFERENCE.md |
| L2 Enrichment v2.4.0 | annotation/ pipeline | docs/schema/layer2_enrichment_v2.schema.json |
| Corpus Manifest | corpus_manifest_v1 (sha256 PK, split_type, ood_source) | docs/schema/corpus_manifest_v1.schema.json |
| Split Assignment | DatasetSplitSpec + source_native splits | docs/schema/dataset_split_spec_v1.schema.json |
| Reserved Pool | ~88% at construction, first OOD expansion source | corpus_manifest_v1.schema.json |
| Per-Head Views | 25 heads (22 SigLIP 2 + 3 MobileNetV4) | docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md |

### corpus-split-lifecycle.puml

**Location**: `level-2/data-preparation/`

**Purpose**: State machine for corpus record lifecycle — from ingestion through split assignment, reserved pool, activation, and OOD promotion with clean/contaminated boundary tracking.

| State Transition | Trigger | Key Fields Set |
|-----------------|---------|----------------|
| → EXCLUDED | Near-dup (Hamming ≤ 5) or disqualified | exclusion_reason, near_duplicate_of |
| → RESERVED | Within ingest_sample_size but outside active ratios | reserved_at |
| → ACTIVE TRAIN | Active train ratio or source_native train | split_type=train, split_source |
| → ACTIVE VAL/TEST | Val/test ratio or source_native | val/test_immutable_since (LOCK) |
| RESERVED → TRAIN | Activation for training | activated_at |
| RESERVED → OOD | Direct OOD promotion (clean boundary) | ood_source=promoted_from_reserved |
| TRAIN → OOD | Post-construction promotion (last resort) | promoted_to_ood_at, ood_source=promoted_from_train |
| → OOD (construction) | ood_predesignations in DatasetSplitSpec | ood_source=predesignated, ood_predesignated=true |

### Schema Visualizations (Mermaid)

**Location**: `docs/schema/`

**Purpose**: Interactive schema diagrams with entity relationships, class structures, and data flows.

| Schema | Visualization | Description |
|--------|---------------|-------------|
| layer2_enrichment.schema.json | [layer2_enrichment_schema.md](../../../schema/layer2_enrichment_schema.md) | Layer 2 enrichment with provenance tracking |
| document_metadata.schema.json | [document_metadata_schema.md](../../../schema/document_metadata_schema.md) | Prepare-Doc → Unify handoff schema |

**Diagram Types in Each Visualization**:

- Entity Relationship Diagram (object references)
- Class Diagrams (properties, types, constraints)
- Enumeration Values (all enum options)
- Data Flow Diagrams (processing pipeline)

| Layer | Components | Source Files | Documentation |
|-------|------------|--------------|---------------|
| **External Sources** ||||
| IQA Benchmarks | DIQA-5000, SmartDoc-QA, OCR-Quality | /mnt/e/.../02_benchmark_only/ | DATASET_CATALOG.md |
| Layout Datasets | DocLayNet, TableBank, FUNSD | /mnt/e/.../01_base_data/ | DATASET_CATALOG.md |
| Handwriting | SignaTR6K, NIST-SD19, PUCIT-OHUL | /mnt/e/.../01_base_data/ | DATASET_CATALOG.md |
| **Layer 1: IMMUTABLE** ||||
| OriginalLabels | DIQA, Layout, Handwriting fields | scripts/annotate_base_metadata.py:470-520 | LABEL_MAPPING_SPECIFICATION.md |
| Label Parsers | parse_diqa_labels, parse_doclaynet_labels | scripts/annotate_base_metadata.py:920-1050 | LABEL_MAPPING_SPECIFICATION.md |
| **Layer 2: ENRICHMENT** ||||
| EnrichmentData | Quality normalization, content flags | scripts/annotate_base_metadata.py | - |
| ISO Standards | Language, Script, Paper Size, Text Scope | src/.../schema_utils/*.py | layer2_enrichment.schema.json |
| Schema Utilities | ISO639, ISO15924, TextScope, PaperSize | src/.../schema_utils/\_\_init\_\_.py | - |
| Layout Taxonomy | 6-schema hub-and-spoke conversion (~57 canonical classes) | src/.../schema_utils/layout_taxonomy.py | config/layout_taxonomy.yaml |
| **Layer 3: TRAINING** ||||
| Parquet Export | samples.parquet (~1M records) | scripts/annotate_base_metadata.py | - |
| DataLoader | DIQA5000Dataset with normalization | modal/train_siglip2_iqa_v2.py | - |
| Model Heads | overall, sharpness, color heads | src/.../labeling/deqa/config.py | - |

**Key Terminology Mapping** (DIQA-5000):

| CSV Column | Schema Field | Training Field | Model Head |
|------------|--------------|----------------|------------|
| overall | diqa_overall | overall | overall |
| sharpness | diqa_sharpness | sharpness | sharpness |
| color_fidelity | diqa_color_fidelity | color | color |

---

## Pseudo-Labeling Workstream

### diqa-pseudo-labeling-workflow.puml

**Location**: `level-2/pseudo-labeling/`

**Purpose**: 5-model ensemble workflow for generating pseudo-labels.

| Component | Source Files | Scripts | Documentation |
|-----------|--------------|---------|---------------|
| Arena Runner | src/.../labeling/arena/runner.py | - | benchmarks/README.md |
| Arena CLI | src/.../labeling/arena/cli.py | - | - |
| Metrics | src/.../labeling/arena/metrics.py | - | - |
| Regression Inference | src/.../labeling/arena/inference/regression.py | - | - |

### diqa-training-phases.puml

**Location**: `level-2/pseudo-labeling/`

**Purpose**: Training phases for Track A (IQA) and Track B (VLM) models.

| Phase | Models | Documentation |
|-------|--------|---------------|
| Phase 1: Track A | MUSIQ, QualiCLIP, DocIQ-Replica | - |
| Phase 2: Track B | Qwen3-VL-8B, InternVL3-8B | - |
| Phase 3: Stacking | HierarchicalStacker | - |

### diqa-checkpoint-selection.puml

**Location**: `level-2/pseudo-labeling/`

**Purpose**: Weighted SRCC + ECE scoring for checkpoint selection.

### diqa-inference-pipeline.puml

**Location**: `level-2/pseudo-labeling/`

**Purpose**: Modal serverless batch inference infrastructure.

| Component | Source Files | Scripts | Documentation |
|-----------|--------------|---------|---------------|
| Modal Benchmark | - | modal/arena_benchmark.py | reference/MODAL_QUICK_REFERENCE.md |
| Full Benchmark | - | modal/arena_full_benchmark.py | - |
| IQA Benchmark | - | modal/arena_iqa_benchmark.py | - |
| VLM Benchmark | - | modal/arena_vlm_benchmark.py | - |
| Local Benchmark | - | scripts/run_model_benchmark.py | - |
| Pseudo-label Gen | - | modal/generate_pseudo_labels.py | - |

**Benchmark Results**: `docs/benchmarks/*.csv`

---

## Model Training Workstream

### prepare-doc-distillation.puml

**Location**: `level-2/model-training/`

**Purpose**: ~~Knowledge distillation from ResNet-50 teacher to ResNet-18 student~~ (LEGACY). Superseded by two-model pipeline: MobileNetV4-Conv-S (~3ms, pre-correction) + SigLIP 2 NAFlex (~50ms, 19 heads, 5 groups). See [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md).

| Component | Source Files | Scripts | Documentation |
|-----------|--------------|---------|---------------|
| **Legacy Teacher Training** ||||
| Teacher Trainer | src/.../training/teacher_trainer.py | modal/train_phase2_iqa.py | - |
| Teacher Model | src/.../models/resnet_teacher.py | - | - |
| **Legacy Distillation** ||||
| Distillation Loss | src/.../training/distillation_loss.py | - | ADRs/0028-resnet-teacher-student.md (SUPERSEDED) |
| Soft Label Gen | src/.../training/generate_soft_labels.py | - | - |
| **Legacy Student Training** ||||
| Student Trainer | src/.../training/student_trainer.py | modal/train_student_distillation.py | - |
| Student Model | src/.../models/resnet_student.py | - | - |
| **Export** ||||
| ONNX Export | src/.../models/model_optimizer.py | modal/export_phase7_onnx.py | - |
| GCS Upload | src/.../utils/gcs_uploader.py | - | MODEL_STORAGE.md |

> **NOTE**: ResNet teacher/student training files above are legacy. New SigLIP 2 multi-task (19 heads) and MobileNetV4-Conv-S (3 heads) training scripts are planned. See [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) and [DATASET_DIVERSITY_REQUIREMENTS.md](../../../planning/DATASET_DIVERSITY_REQUIREMENTS.md) for the new architecture and 10 purpose-built datasets (~503K total images).

### prepare-doc-training-workflow-high-level.puml

**Location**: `level-2/model-training/`

**Purpose**: ML training lifecycle overview.

### prepare-doc-training-infrastructure.puml

**Location**: `level-2/model-training/`

**Purpose**: Training infrastructure and optimization loop showing dataset assembly, ILP allocation, Modal GPU training, phased head training, active learning, and model export/registration.

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| **Dataset Assembly** |||
| 10 purpose-built datasets (~503K) | WS3 data-prep + WS8 synthetic | [DATASET_DIVERSITY_REQUIREMENTS.md](../../../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |
| **ILP Sample Allocation** |||
| PuLP/OR-Tools optimization | (planned) | [TRAINING_OPTIMIZATION_PLAN.md](../../../planning/TRAINING_OPTIMIZATION_PLAN.md) |
| **Modal GPU Training** |||
| SigLIP 2 multi-task training | modal/train_siglip2_iqa_v2.py (1,597 LOC) | [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) |
| Training utilities | modal/shared/metrics_utils.py (223 LOC) | - |
| GCS utilities | modal/shared/gcs_utils.py (130 LOC) | - |
| **Phased Head Training** |||
| Warmup → Expand → Full → Refine | (planned) | TRAINING_OPTIMIZATION_PLAN.md |
| **Active Learning Loop** |||
| Targeted sample generation | modal/shared/dataset_utils.py (61 LOC) | - |
| **Export & Registration** |||
| ONNX export (SigLIP 2 + MobileNetV4) | modal/shared/constants.py (58 LOC) | - |

---

## Production Runtime Workstream

### prepare-doc-primary-workflow-high-level.puml

**Location**: `level-2/production-runtime/`

**Purpose**: End-to-end document processing overview.

### prepare-doc-primary-workflow-detailed.puml

**Location**: `level-2/production-runtime/`

**Purpose**: Detailed implementation with module references.

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| **Ingestion & Pre-flight** |||
| Document Processor | src/.../ingestion/document_processor.py | api/ingestion.md |
| PDF Loader | src/.../ingestion/pdf_loader.py | - |
| PDF Analyzer | src/.../ingestion/pdf_analyzer.py | - |
| PDF Resolution | src/.../ingestion/pdf_resolution.py | - |
| PDF Upscaler | src/.../ingestion/pdf_upscaler.py | - |
| Image Loader | src/.../ingestion/image_loader.py | - |
| Office Processor | src/.../ingestion/office_processor.py | - |
| **Classification** |||
| PDF Type Classifier | src/.../classification/pdf_type_classifier.py | - |
| PDF Image Detector | src/.../classification/pdf_image_detector.py | - |
| PDF Text Extractor | src/.../classification/pdf_text_extractor.py | - |
| **Detection** |||
| Text Gate | src/.../detection/text_gate.py | api/detection.md |
| Classical IQA | src/.../detection/iqa_classical.py | api/detection.md |
| ML IQA | src/.../detection/iqa_ml.py | api/detection.md |
| Hybrid IQA | src/.../detection/hybrid_iqa.py | - |
| Advanced Detectors | src/.../detection/advanced_detectors.py | - |
| Discrepancy | src/.../detection/discrepancy.py | - |
| Orientation | src/.../detection/orientation_detector.py | - |
| **Layout Detection** |||
| docling-layout | src/.../detection/doclayout_yolo.py | - |
| Layout-Lite Analyzer | src/.../detection/layout_lite/analyzer.py | - |
| Column Detector | src/.../detection/layout_lite/column_detector.py | - |
| Table Detector | src/.../detection/layout_lite/table_detector.py | - |
| Figure Detector | src/.../detection/layout_lite/figure_detector.py | - |
| Watermark Detector | src/.../detection/layout_lite/watermark_detector.py | - |
| Background Detector | src/.../detection/layout_lite/background_detector.py | - |
| Fuzzy Scan Detector | src/.../detection/layout_lite/fuzzy_scan_detector.py | - |
| DocLayout Integration | src/.../detection/layout_lite/doclayout_integration.py | - |
| Layout Taxonomy | src/.../schema_utils/layout_taxonomy.py | config/layout_taxonomy.yaml |
| **Correction** |||
| Corrections | src/.../correction/corrections.py | api/correction.md |
| **Scoring & Routing** |||
| DQS Calculator | src/.../metrics/dqs_calculator.py | ADRs/0030-document-quality-score.md |
| Routing Engine | src/.../routing/recommendation_engine.py | guides/project-b-handoff.md |
| **Output** |||
| Schema | src/.../schema.py | api/schema.md |
| JSON Generator | src/.../output/json_generator.py | api/output.md |

### prepare-doc-device-selection-flow.puml

**Location**: `level-2/production-runtime/`

**Purpose**: Device priority and confidence-based classical fallback logic.

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Device Orchestrator | src/.../orchestration/device_orchestrator.py | ADRs/0036-device-priority.md |
| Device Probe | src/.../utils/device_probe.py | - |
| Model Loader | src/.../models/model_loader.py | - |
| Batch Inference | src/.../models/batch_inference.py | - |
| Tensor Cache | src/.../utils/tensor_cache.py | - |
| Modal Inference | modal/teacher_inference.py (legacy; migrating to multi-task inference) | reference/MODAL_QUICK_REFERENCE.md |

### prepare-doc-worker-architecture.puml

**Location**: `level-2/production-runtime/`

**Purpose**: Celery worker pools, FastAPI routing, and device orchestration architecture.

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| **Client Layer (FastAPI)** |||
| FastAPI App | src/.../api/app.py | - |
| Health Routes | src/.../api/routes/health.py | - |
| Process Route | src/.../api/routes/process.py | - |
| Batch Route | src/.../api/routes/batch.py | - |
| **Middleware** |||
| API Configuration | src/.../api/config.py | - |
| Middleware Stack | src/.../api/middleware.py | - |
| **Message Broker** |||
| Celery App | src/.../workers/celery_app.py | - |
| **Worker Pools** |||
| Celery Tasks | src/.../workers/tasks.py | - |
| **Device Orchestration** |||
| Device Orchestrator | src/.../orchestration/device_orchestrator.py | level-3/production-runtime/device-orchestrator.md |
| Modal Client | src/.../orchestration/modal_client.py | reference/MODAL_QUICK_REFERENCE.md |
| **Monitoring** |||
| Flower Dashboard | External: Celery Flower | - |
| Prometheus Metrics | Embedded in tasks | - |
| Structured Logging | src/.../utils/logging.py | - |

---

## ⚠️ Benchmarking Workstream (DEPRECATED)

### project-a-benchmark-workflow.puml

**Location**: `level-2/benchmarking/` → **MOVED** to `deprecated/benchmarking/`

**Status**: **DEPRECATED as of 2025-01-16**

**Superseded By**: [Model Arena & Multi-Label Benchmarking](level-2/model-arena/index.md)

**Purpose**: Legacy IQA model benchmarking workflow (basic workflow only)

**Migration Note**: For current benchmarking infrastructure, see:

- **Level 2**: [model-arena/index.md](level-2/model-arena/index.md) - Comprehensive multi-phase benchmarking
- **Level 2**: [labeling-benchmarking/index.md](level-2/labeling-benchmarking/index.md) - Labeling model training

---

## Downstream Context

### unify-ocr-layout-workflow.puml

**Location**: `level-2/downstream-context/`

**Purpose**: Unify OCR orchestration context.

### chunk-fusion-chunking-workflow.puml

**Location**: `level-2/downstream-context/`

**Purpose**: Chunk fusion and chunking context.

### embed-vectorstore-workflow.puml

**Location**: `level-2/downstream-context/`

**Purpose**: Embed vector store context.

---

## Labeling & Benchmarking Workstream

### domain-classification-pipeline.puml

**Location**: `level-2/labeling-benchmarking/`

**Purpose**: Domain classification pipeline for document categorization (WS5).

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Domain Classifier | src/.../labeling/domain/ | [domain-classification-pipeline.md](level-2/labeling-benchmarking/domain-classification-pipeline.md) |

---

## Model Arena Workstream

### model-arena-architecture.puml

**Location**: `level-2/model-arena/`

**Purpose**: Multi-phase model benchmarking and arena evaluation infrastructure (WS6). Supersedes the deprecated benchmarking workstream.

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Arena Runner | src/.../labeling/arena/runner.py | - |
| Arena CLI | src/.../labeling/arena/cli.py | - |
| Arena Metrics | src/.../labeling/arena/metrics.py | - |

---

## Monitoring & Drift Workstream

### monitoring-drift-architecture.puml

**Location**: `level-2/monitoring-drift/`

**Purpose**: Monitoring infrastructure, drift detection, and active learning pipeline (WS7).

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Performance Drift | src/.../drift/performance.py | monitoring/drift-detection.md |
| Alerting | src/.../drift/alerting.py | monitoring/thresholds.md |
| Active Learning | src/.../drift/active_learning.py | - |
| Privacy Review | src/.../drift/privacy_review.py | - |
| Retraining | src/.../drift/retraining.py | - |

---

## Synthetic Generation Workstream

### synthetic-generation-architecture.puml

**Location**: `level-2/synthetic-generation/`

**Purpose**: Controlled degradation and multi-task augmentation for training data expansion (WS8).

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Configuration | src/.../synthetic/config.py | [index.md](level-2/synthetic-generation/index.md) |
| Generator Engine | src/.../synthetic/generator.py | - |
| Hybrid Augmentation | src/.../synthetic/augmentation_hybrid.py | - |
| Schema Adapter | src/.../synthetic/schema_adapter.py | - |
| CLI | src/.../synthetic/cli.py | - |

---

## Schema Field Population Workstream

### schema-field-population-summary.puml

**Location**: `level-2/schema-field-population/`

**Purpose**: Simplified activity diagram showing 8-pass schema field population as a linear flow with tier colors and gap annotations. Renderable version for SVG generation.

### schema-field-population-workflow.puml (Text Reference)

**Location**: `level-2/schema-field-population/`

**Purpose**: Comprehensive 387-line component diagram showing full schema field population workflow. Too complex for PlantUML SVG rendering; kept as text reference. See summary diagram above for the renderable version.

---

## Supporting Infrastructure

### API Layer

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| FastAPI App | src/.../api/app.py | api/rest-api.md |
| API Config | src/.../api/config.py | - |
| Middleware | src/.../api/middleware.py | - |
| Models | src/.../api/models.py | - |
| Health Routes | src/.../api/routes/health.py | - |
| Process Routes | src/.../api/routes/process.py | - |
| Batch Routes | src/.../api/routes/batch.py | - |

---

## Level 3: Module Implementation

Level 3 provides detailed module-level documentation with LOC annotations and swimlane diagrams for each workstream.

### Production Runtime (WS1)

**Location**: `level-3/production-runtime/`

| Document | Purpose |
|----------|---------|
| [production-runtime-swimlane.puml](level-3/production-runtime/production-runtime-swimlane.puml) | Complete swimlane with LOC annotations |
| [pipeline-state-machine.md](level-3/production-runtime/pipeline-state-machine.md) | 16-state pipeline specification |
| [device-orchestrator.md](level-3/production-runtime/device-orchestrator.md) | Device selection, budget enforcement, circuit breaker |

**Key Source Files**: 16,910+ LOC across ingestion, detection, correction, routing, and orchestration modules.

### Model Training (WS2)

**Location**: `level-3/model-training/`

| Document | Purpose |
|----------|---------|
| [model-training-swimlane.puml](level-3/model-training/model-training-swimlane.puml) | Training phase swimlane with LOC annotations |
| [layout-fusion-downsampler.md](level-3/model-training/layout-fusion-downsampler.md) | LEGACY (superseded by SigLIP 2 NAFlex) |

**Key Source Files**: 7,058+ LOC. Legacy ResNet architecture; see [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) for current design.

### Data Preparation (WS3)

**Location**: `level-3/data-preparation/`

| Document | Purpose |
|----------|---------|
| [data-preparation-swimlane.puml](level-3/data-preparation/data-preparation-swimlane.puml) | Data prep swimlane with LOC annotations |
| [metadata-schema-versioning.md](level-3/data-preparation/metadata-schema-versioning.md) | Three-layer metadata architecture |
| [label-parsing-generation.md](level-3/data-preparation/label-parsing-generation.md) | 45-dimensional training label generation |

**Key Source Files**: ~19,600 LOC in annotation package + 4,066+ LOC in scripts.

### Pseudo-Labeling (WS4)

**Location**: `level-3/pseudo-labeling/`

| Document | Purpose |
|----------|---------|
| [pseudo-labeling-swimlane.puml](level-3/pseudo-labeling/pseudo-labeling-swimlane.puml) | 7-swimlane pseudo-labeling pipeline with LOC annotations |
| [ensemble-stacking.md](level-3/pseudo-labeling/ensemble-stacking.md) | 5-model ensemble, variance weighting, calibration, filtering |

**Key Source Files**: ~2,947 LOC across modal/ scripts (generate_pseudo_labels.py, stage1_deqa_inference.py, teacher_inference.py, shared/ utilities).

### Monitoring & Drift (WS7)

**Location**: `level-3/monitoring-drift/`

| Document | Purpose |
|----------|---------|
| [monitoring-drift-swimlane.puml](level-3/monitoring-drift/monitoring-drift-swimlane.puml) | Monitoring swimlane with LOC annotations |
| [end-to-end-lifecycle.md](level-3/monitoring-drift/end-to-end-lifecycle.md) | 7-phase closed-loop lifecycle |

**Key Source Files**: 5,353+ implementation LOC + 5,400+ test LOC across drift detection, alerting, active learning, privacy review, and retraining modules.

### Synthetic Generation (WS8)

**Location**: `level-3/synthetic-generation/`

| Document | Purpose |
|----------|---------|
| [synthetic-generation-swimlane.puml](level-3/synthetic-generation/synthetic-generation-swimlane.puml) | 7-swimlane generation pipeline with LOC annotations |
| [augmentation-pipeline.md](level-3/synthetic-generation/augmentation-pipeline.md) | Hybrid augmentation, 3 aging profiles, DPI tiers, color modes |

**Key Source Files**: ~1,400 LOC across config.py, generator.py, augmentation_hybrid.py, schema_adapter.py, cli.py.

---

## ADR Cross-Reference

| ADR | Related Diagrams | Key Source Files |
|-----|------------------|------------------|
| 0007-hybrid-iqa-approach.md | level-2/production-runtime/*.puml | detection/hybrid_iqa.py |
| 0008-multi-stage-pipeline-architecture.md | level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml | - |
| 0010-300-dpi-normalization.md | level-2/data-preparation/*.puml | ingestion/pdf_resolution.py |
| 0014-classical-ml-hybrid-iqa.md | level-2/production-runtime/*.puml | detection/iqa_classical.py |
| 0015-yolov8-layout-detection.md | level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml | detection/doclayout_yolo.py |
| 0028-resnet-teacher-student.md **(SUPERSEDED by SigLIP 2 + MobileNetV4 two-model pipeline)** | level-2/model-training/*.puml | training/*.py, models/resnet_*.py |
| 0030-document-quality-score.md | level-2/production-runtime/*.puml | metrics/dqs_calculator.py |
| 0035-modal-gpu-integration.md | level-2/pseudo-labeling/*.puml | modal/*.py |
| 0036-device-priority.md | level-2/production-runtime/*.puml | orchestration/device_orchestrator.py |

---

## Documentation Cross-Reference

| Documentation | Related Diagrams |
|---------------|------------------|
| DATASET_CATALOG.md | level-2/data-preparation/*.puml |
| DATASET_LOCATIONS.md | level-2/data-preparation/*.puml |
| config/layout_taxonomy.yaml | level-2/data-preparation/*.puml, level-2/production-runtime/*.puml |
| MODEL_STORAGE.md | level-2/model-training/*.puml |
| benchmarks/README.md | level-2/pseudo-labeling/*.puml |
| api/ingestion.md | level-2/production-runtime/*.puml |
| api/detection.md | level-2/production-runtime/*.puml |
| api/correction.md | level-2/production-runtime/*.puml |
| api/schema.md | level-2/production-runtime/*.puml |
| guides/project-b-handoff.md | level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml |
| monitoring/drift-detection.md | level-2/monitoring-drift/*.puml, level-3/monitoring-drift/*.puml |
| reference/MODAL_QUICK_REFERENCE.md | level-2/pseudo-labeling/*.puml, level-2/model-training/*.puml |

---

## Maintenance Guidelines

1. **Update diagrams when source files change**: If a module is renamed or moved, update the traceability notes in the relevant PUML files.

2. **Keep this index synchronized**: When adding new diagrams or source files, update both the PUML traceability notes and this index.

3. **Use consistent path notation**: In PUML files, use `src/.../` prefix for brevity; in this index, use full relative paths.

4. **Link related ADRs**: When architectural decisions affect diagram content, reference the ADR in the diagram notes.

5. **Track gaps**: Use this index to identify missing diagrams and prioritize documentation work.

6. **Maintain folder structure**: New diagrams must be placed in the appropriate level folder:
   - `level-0/` - Multi-repo pipeline context
   - `level-1/` - Prepare-Doc architecture
   - `level-2/{workstream}/` - Workstream details
   - `level-3/{workstream}/` - Module implementation with LOC annotations
   - `deprecated/{workstream}/` - Superseded diagrams
