# Diagram Index & Traceability Matrix

**Date**: December 2025
**Purpose**: Maps PlantUML diagrams to source files, scripts, and documentation

## Quick Navigation

| Workstream | Primary Diagram | Key Documentation |
|------------|-----------------|-------------------|
| [Architecture Overview](#level-1-architecture-overview) | level-1/PROJECT_A_ARCHITECTURE_OVERVIEW.puml | This document |
| [Data Preparation](#data-preparation-workstream) | level-2/data-preparation/*.puml | DATASET_CATALOG.md |
| [Pseudo-Labeling](#pseudo-labeling-workstream) | level-2/pseudo-labeling/*.puml | benchmarks/README.md |
| [Model Training](#model-training-workstream) | level-2/model-training/*.puml | ADRs/0028-resnet-teacher-student.md |
| [Production Runtime](#production-runtime-workstream) | level-2/production-runtime/*.puml | api/*.md |

---

## Diagram Hierarchy

All diagrams are organized in a level-based folder structure:

```text
docs/architecture/diagrams/
├── level-0/                          # Pipeline Context
│   └── rag-pipeline-overview.puml
│
├── level-1/                          # Project A Architecture
│   ├── PROJECT_A_ARCHITECTURE_OVERVIEW.puml
│   └── PROJECT_A_WORKFLOW_HIERARCHY.puml
│
└── level-2/                          # Workstream Details
    ├── production-runtime/
    │   ├── project-a-primary-workflow-high-level.puml
    │   ├── project-a-primary-workflow-detailed.puml
    │   └── project-a-device-selection-flow.puml
    │
    ├── model-training/
    │   ├── project-a-distillation.puml
    │   └── project-a-training-workflow-high-level.puml
    │
    ├── data-preparation/
    │   ├── project-a-training-data-ingestion.puml
    │   └── automated-data-labeling-pipeline.puml
    │
    ├── pseudo-labeling/
    │   ├── diqa-pseudo-labeling-workflow.puml
    │   ├── diqa-training-phases.puml
    │   ├── diqa-checkpoint-selection.puml
    │   └── diqa-inference-pipeline.puml
    │
    ├── benchmarking/
    │   └── project-a-benchmark-workflow.puml
    │
    └── downstream-context/
        ├── project-b-ocr-layout-workflow.puml
        ├── project-c-fusion-chunking-workflow.puml
        └── project-d-vectorstore-workflow.puml
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
| Project A | image-detection (this repo) | CLAUDE.md, PROJECT_PLAN.md |
| Project B | (Not yet started) | project-b-f-nf.md |
| **Track 2: Audio/Video Processing** |||
| Audio Processor | github.com/ByronWilliamsCPA/audio-processor | PIPELINE-INTEGRATION-SUMMARY.md |
| **Downstream Processing** |||
| Project C | (Not yet started) | project-c-f-nf.md |
| Project D | (Not yet started) | - |

**Content Sources**:

| Source Type | Formats | Routing Target |
|-------------|---------|----------------|
| Documents | PDF, DOCX, PPTX | Project A |
| Images | PNG, JPG, TIFF | Project A |
| Audio | MP3, WAV, M4A, FLAC, OGG, AAC | Audio Processor |
| Video | MP4, MOV, AVI, MKV, WEBM | Audio Processor |

**API Contract (rag-processor -> Project A)**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/process` | POST | Accept multipart form data |
| `/status/{job_id}` | GET | Processing status updates |
| `/results/{job_id}` | GET | Deliver processed output |
| `/health` | GET | Service health check |

**Integration Points**:

- **Project B DOM Unification**: Single Docling instance handles all preprocessed inputs (document + audio)
- **Downstream Transparency**: Unified Docling DOM consumed identically by Projects C & D
- **Performance**: 10-page doc <30s, 100-page <2min; audio <1min/hour

**Related Repositories**:

- [rag-processor](https://github.com/ByronWilliamsCPA/rag-processor) - Pipeline frontend and orchestration
- [audio-processor](https://github.com/ByronWilliamsCPA/audio-processor) - Parallel audio/video track

---

## Level 1: Architecture Overview

### PROJECT_A_ARCHITECTURE_OVERVIEW.puml

**Location**: `level-1/`

**Purpose**: Complete system architecture showing all four workstreams.

| Section | Source Files | Documentation |
|---------|--------------|---------------|
| RAG Ecosystem | External repos | - |
| Production Runtime | See Production Runtime table | api/*.md |
| Model Training | See Model Training table | ADRs/0028-*.md |
| Data Preparation | See Data Preparation table | DATASET_CATALOG.md |
| Pseudo-Labeling | See Pseudo-Labeling table | benchmarks/README.md |

### PROJECT_A_WORKFLOW_HIERARCHY.puml

**Location**: `level-1/`

**Purpose**: Swimlane diagram showing data flow between workstreams.

---

## Data Preparation Workstream

### project-a-training-data-ingestion.puml

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

### project-a-distillation.puml

**Location**: `level-2/model-training/`

**Purpose**: Knowledge distillation from ResNet-50 teacher to ResNet-18 student.

| Component | Source Files | Scripts | Documentation |
|-----------|--------------|---------|---------------|
| **Teacher Training** ||||
| Teacher Trainer | src/.../training/teacher_trainer.py | modal/train_phase2_iqa.py | - |
| Teacher Model | src/.../models/resnet_teacher.py | - | - |
| **Distillation** ||||
| Distillation Loss | src/.../training/distillation_loss.py | - | ADRs/0028-resnet-teacher-student.md |
| Soft Label Gen | src/.../training/generate_soft_labels.py | - | - |
| **Student Training** ||||
| Student Trainer | src/.../training/student_trainer.py | modal/train_student_distillation.py | - |
| Student Model | src/.../models/resnet_student.py | - | - |
| **Export** ||||
| ONNX Export | src/.../models/model_optimizer.py | modal/export_phase7_onnx.py | - |
| GCS Upload | src/.../utils/gcs_uploader.py | - | MODEL_STORAGE.md |

### project-a-training-workflow-high-level.puml

**Location**: `level-2/model-training/`

**Purpose**: ML training lifecycle overview.

### Layout Model Training (GAP)

**Status**: No dedicated workflow diagram exists.

| Component | Source Files | Scripts | Documentation |
|-----------|--------------|---------|---------------|
| DocLayout-YOLO Training | - | modal/train_phase3_doclayout_yolo.py | - |
| Layout-Lite Training | - | modal/train_phase6_layout_lite.py | - |

**Recommendation**: Create `project-a-layout-training.puml` in `level-2/model-training/`.

---

## Production Runtime Workstream

### project-a-primary-workflow-high-level.puml

**Location**: `level-2/production-runtime/`

**Purpose**: End-to-end document processing overview.

### project-a-primary-workflow-detailed.puml

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
| DocLayout-YOLO | src/.../detection/doclayout_yolo.py | - |
| Layout-Lite Analyzer | src/.../detection/layout_lite/analyzer.py | - |
| Column Detector | src/.../detection/layout_lite/column_detector.py | - |
| Table Detector | src/.../detection/layout_lite/table_detector.py | - |
| Figure Detector | src/.../detection/layout_lite/figure_detector.py | - |
| Watermark Detector | src/.../detection/layout_lite/watermark_detector.py | - |
| Background Detector | src/.../detection/layout_lite/background_detector.py | - |
| Fuzzy Scan Detector | src/.../detection/layout_lite/fuzzy_scan_detector.py | - |
| DocLayout Integration | src/.../detection/layout_lite/doclayout_integration.py | - |
| **Correction** |||
| Corrections | src/.../correction/corrections.py | api/correction.md |
| **Scoring & Routing** |||
| DQS Calculator | src/.../metrics/dqs_calculator.py | ADRs/0030-document-quality-score.md |
| Routing Engine | src/.../routing/recommendation_engine.py | guides/project-b-handoff.md |
| **Output** |||
| Schema | src/.../schema.py | api/schema.md |
| JSON Generator | src/.../output/json_generator.py | api/output.md |

### project-a-device-selection-flow.puml

**Location**: `level-2/production-runtime/`

**Purpose**: Device priority and teacher escalation logic.

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Device Orchestrator | src/.../orchestration/device_orchestrator.py | ADRs/0036-device-priority.md |
| Device Probe | src/.../utils/device_probe.py | - |
| Model Loader | src/.../models/model_loader.py | - |
| Batch Inference | src/.../models/batch_inference.py | - |
| Tensor Cache | src/.../utils/tensor_cache.py | - |
| Modal Teacher | modal/teacher_inference.py | reference/MODAL_QUICK_REFERENCE.md |

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

### project-b-ocr-layout-workflow.puml

**Location**: `level-2/downstream-context/`

**Purpose**: Project B OCR orchestration context.

### project-c-fusion-chunking-workflow.puml

**Location**: `level-2/downstream-context/`

**Purpose**: Project C fusion and chunking context.

### project-d-vectorstore-workflow.puml

**Location**: `level-2/downstream-context/`

**Purpose**: Project D vector store context.

---

## Supporting Infrastructure

### Celery Workers (GAP - No Diagram)

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Celery App | src/.../workers/celery_app.py | - |
| Tasks | src/.../workers/tasks.py | - |

**Recommendation**: Create `project-a-worker-architecture.puml` in `level-2/production-runtime/`.

### Monitoring & Drift Detection (GAP - No Diagram)

| Component | Source Files | Documentation |
|-----------|--------------|---------------|
| Performance Drift | src/.../drift/performance.py | monitoring/drift-detection.md |
| Alerting | src/.../drift/alerting.py | monitoring/thresholds.md |
| Active Learning | src/.../drift/active_learning.py | - |
| Privacy Review | src/.../drift/privacy_review.py | - |
| Retraining | src/.../drift/retraining.py | - |

**Recommendation**: Create `project-a-monitoring-drift.puml` in `level-2/production-runtime/`.

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

## ADR Cross-Reference

| ADR | Related Diagrams | Key Source Files |
|-----|------------------|------------------|
| 0007-hybrid-iqa-approach.md | level-2/production-runtime/*.puml | detection/hybrid_iqa.py |
| 0008-multi-stage-pipeline-architecture.md | level-1/PROJECT_A_ARCHITECTURE_OVERVIEW.puml | - |
| 0010-300-dpi-normalization.md | level-2/data-preparation/*.puml | ingestion/pdf_resolution.py |
| 0014-classical-ml-hybrid-iqa.md | level-2/production-runtime/*.puml | detection/iqa_classical.py |
| 0015-yolov8-layout-detection.md | level-1/PROJECT_A_ARCHITECTURE_OVERVIEW.puml | detection/doclayout_yolo.py |
| 0028-resnet-teacher-student.md | level-2/model-training/*.puml | training/*.py, models/resnet_*.py |
| 0030-document-quality-score.md | level-2/production-runtime/*.puml | metrics/dqs_calculator.py |
| 0035-modal-gpu-integration.md | level-2/pseudo-labeling/*.puml | modal/*.py |
| 0036-device-priority.md | level-2/production-runtime/*.puml | orchestration/device_orchestrator.py |

---

## Documentation Cross-Reference

| Documentation | Related Diagrams |
|---------------|------------------|
| DATASET_CATALOG.md | level-2/data-preparation/*.puml |
| DATASET_LOCATIONS.md | level-2/data-preparation/*.puml |
| MODEL_STORAGE.md | level-2/model-training/*.puml |
| benchmarks/README.md | level-2/pseudo-labeling/*.puml |
| api/ingestion.md | level-2/production-runtime/*.puml |
| api/detection.md | level-2/production-runtime/*.puml |
| api/correction.md | level-2/production-runtime/*.puml |
| api/schema.md | level-2/production-runtime/*.puml |
| guides/project-b-handoff.md | level-1/PROJECT_A_ARCHITECTURE_OVERVIEW.puml |
| monitoring/drift-detection.md | (GAP - needs diagram) |
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
   - `level-1/` - Project A architecture
   - `level-2/{workstream}/` - Workstream details
