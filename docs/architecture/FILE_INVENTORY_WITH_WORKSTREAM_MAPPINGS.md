---
description: Comprehensive inventory of all git-tracked files mapped to workstreams
  and workflow steps
owner: docs-team
purpose: 'Bidirectional validation: Ensure all files are documented and all documentation
  references exist.'
schema_type: common
status: draft
tags:
- architecture
title: Complete File Inventory with Workstream Mappings
---

**Purpose**: Cross-validate that:

1. All source files are assigned to workstreams
2. All workstream LOC counts are accurate
3. All workflow steps reference actual files
4. No files are missing from documentation

**Validation**: Compare this inventory against:

- LOC extraction script mappings ([`scripts/extract_workstream_loc.sh`](../../scripts/extract_workstream_loc.sh))
- Level 2 traceability tables (to be added)
- Level 3 swimlane diagrams (to be created)

---

## Quick Summary

> **Last Updated**: 2026-02-21. Stream 4C scripts added (WS3); new src modules added (WS1, WS2); model card deprecation completed; superseded planning docs archived.

| Category | Files | Total LOC | Status |
|----------|-------|-----------|--------|
| **WS1: Production Runtime** | 47+ | 16,910+ | ⚠️ Partial — border_removal, perspective_correction, siglip2_multitask, docling_router added; full recount needed |
| **WS2: Model Training** | 11+ | ~3,500 | ⚠️ Partial — siglip2_multitask.yaml added; legacy scripts deleted |
| **WS3: Data Preparation** | 20+ | 4,066+ | ⚠️ Partial — Stream 4C scripts (12 new) added; annotation/ package (~60 files) still untracked |
| **WS4: Pseudo-Labeling** | 3 | ~2,947 | ⚠️ Stale — modal scripts may not exist in repo |
| **WS5: Labeling & Benchmarking** | 0 | 0 | ⚠️ Planned (not implemented) |
| **WS6: Model Arena** | 33 | 6,340 | ✅ Assigned |
| **WS7: Monitoring & Drift** | 7 | 5,348 | ✅ Assigned |
| **WS8: Synthetic Generation** | 11 | ~1,500+ | ⚠️ Stale — package moved from augmentation/ to synthetic/ |
| **NA - Tests** | ~300 | ~15,000 | ℹ️ Excluded from LOC |
| **NA - Architecture Diagrams** | 153 | ~8,000 | ℹ️ Excluded from LOC — see dedicated section below |
| **NA - Documentation** | ~200 | ~8,000 | ℹ️ Excluded from LOC |
| **NA - Configuration** | ~50 | ~2,000 | ℹ️ Excluded from LOC |
| **NA - Infrastructure** | ~100 | ~3,000 | ℹ️ Excluded from LOC |
| **Unassigned** | ~30 | ~500 | ⚠️ Needs review |

### Intentionally Excluded Directories

The following directories are **by design not tracked** in workstream diagrams. Files in these directories will always appear in "in repo, not in inventory" comparisons — that is expected and correct.

| Directory | Count | Rationale |
|-----------|-------|-----------|
| `fonts/synthetic-gen/` | ~148 | Static font assets for WS8 generator; not pipeline source code |
| `.claude/` agents, commands, skills | ~97 | Meta-tooling (Claude Code agents), not product pipeline code |
| `data/test_fixtures/` | ~48 | Test support data, excluded by testing convention |
| `metadata_registry/aggregates/` | ~57 | Generated artifacts from `aggregate_layer2_metadata.py`; not source files |
| `.github/workflows/` | ~18 | CI/CD infra; tracked in deployment context, not pipeline workstreams |
| `docs/_archived/` | ~71 | Explicitly retired docs; no workstream mapping needed |
| `docs/planning/`, `docs/datasets/`, `docs/handoff/` | ~100+ | Documentation support files, not pipeline source code |
| `Dockerfile*`, `docker-compose.yaml`, `deployment/` | ~20 | Container/deployment infra; tracked separately |
| Linting/tooling configs (`.pre-commit-config.yaml`, `pyrightconfig.json`, etc.) | ~20 | Tooling config, not pipeline logic |

**Total**: ~1,679 files (excluding tests/ and tmp_cleanup/), ~72,000+ lines

---

## WS1: Production Runtime

**Total Files**: 44
**Total LOC**: 16,910
**Level 2 Doc**: [production-runtime/index.md](diagrams/level-2/production-runtime/index.md)

### Ingestion & Preflight (2,235 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/ingestion/**init**.py | 45 | Module exports |
| src/image_preprocessing_detector/ingestion/document_processor.py | 303 | Entry point - process document |
| src/image_preprocessing_detector/ingestion/pdf_loader.py | 265 | Load PDF, extract pages |
| src/image_preprocessing_detector/ingestion/image_loader.py | 280 | Load standalone images |
| src/image_preprocessing_detector/ingestion/office_processor.py | 492 | Load Office docs (DOCX, PPTX) |
| src/image_preprocessing_detector/ingestion/pdf_analyzer.py | 256 | Pre-flight analysis orchestrator |
| src/image_preprocessing_detector/ingestion/pdf_resolution.py | 264 | DPI detection |
| src/image_preprocessing_detector/ingestion/pdf_upscaler.py | 330 | DPI upscaling (5 algorithms) |

**Subtotal**: 2,235 lines

---

### Classification (472 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/classification/**init**.py | 21 | Module exports |
| src/image_preprocessing_detector/classification/pdf_type_classifier.py | 135 | Classify PDF type (image_only/born_digital/hybrid) |
| src/image_preprocessing_detector/classification/pdf_image_detector.py | 194 | Detect if PDF contains images |
| src/image_preprocessing_detector/classification/pdf_text_extractor.py | 122 | Extract text for born-digital detection |

**Subtotal**: 472 lines

---

### Detection - Text Gate & IQA (7,109 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/detection/**init**.py | 190 | Module exports |
| src/image_preprocessing_detector/detection/text_gate.py | 334 | Fast text presence detection (<10ms) |
| src/image_preprocessing_detector/detection/iqa_classical.py | 2,844 | 8 classical CV detectors (skew, blur, contrast, noise, etc.) |
| src/image_preprocessing_detector/detection/iqa_ml.py | 1,303 | ML IQA inference (legacy teacher-student; migrating to MobileNetV4 + SigLIP 2 multi-task pipeline) |
| src/image_preprocessing_detector/detection/hybrid_iqa.py | 351 | Hybrid IQA (classical + ML fusion) |
| src/image_preprocessing_detector/detection/advanced_detectors.py | 892 | Additional quality detectors |
| src/image_preprocessing_detector/detection/discrepancy.py | 786 | Classical vs ML discrepancy detection |
| src/image_preprocessing_detector/detection/orientation_detector.py | 608 | Page orientation detection (90°, 180°, 270°) |
| src/image_preprocessing_detector/detection/siglip2_multitask.py | TBD | SigLIP 2 NAFlex multi-task inference wrapper; lazy-loaded, device-aware; 8 production heads (IQA ×3, script, source, orientation, shadow, warping) |

**Subtotal**: 7,308+ lines (LOC recount needed)

---

### Detection - Layout Lite (2,808 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/detection/doclayout_yolo.py | 801 | docling-layout integration (11 classes) |
| src/image_preprocessing_detector/detection/layout_lite/**init**.py | 117 | Module exports |
| src/image_preprocessing_detector/detection/layout_lite/analyzer.py | 138 | Layout-lite orchestrator |
| src/image_preprocessing_detector/detection/layout_lite/column_detector.py | 144 | Column detection |
| src/image_preprocessing_detector/detection/layout_lite/table_detector.py | 157 | Table presence detection |
| src/image_preprocessing_detector/detection/layout_lite/figure_detector.py | 118 | Figure/image detection |
| src/image_preprocessing_detector/detection/layout_lite/watermark_detector.py | 96 | Watermark detection |
| src/image_preprocessing_detector/detection/layout_lite/background_detector.py | 101 | Colorful background detection |
| src/image_preprocessing_detector/detection/layout_lite/fuzzy_scan_detector.py | 94 | Fuzzy scan detection |
| src/image_preprocessing_detector/detection/layout_lite/doclayout_integration.py | 690 | docling-layout wrapper |
| src/image_preprocessing_detector/detection/layout_lite/constants.py | 46 | Layout constants |
| src/image_preprocessing_detector/detection/layout_lite/layout_types.py | 107 | Layout type enums |

**Subtotal**: 2,609 lines

---

### Correction (1,284+ LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/correction/**init**.py | 62 | Module exports |
| src/image_preprocessing_detector/correction/corrections.py | 1,222 | Deskew, CLAHE, sharpening, denoising (8 correction classes) |
| src/image_preprocessing_detector/correction/border_removal.py | TBD | Scanner/camera border removal via Otsu + morphology; retains ≥70% area |
| src/image_preprocessing_detector/correction/perspective_correction.py | TBD | Perspective distortion fix via Canny + quad detection + homography; blocks if warping_score > 0.75 |

**Subtotal**: 1,284+ lines (LOC recount needed)

---

### Metrics & Routing (1,558+ LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/metrics/**init**.py | 49 | Module exports |
| src/image_preprocessing_detector/metrics/dqs_calculator.py | 1,369 | Document Quality Score calculation (degradation + complexity) |
| src/image_preprocessing_detector/routing/**init**.py | 10 | Module exports |
| src/image_preprocessing_detector/routing/recommendation_engine.py | 140 | OCR routing recommendation (4 strategies) |
| src/image_preprocessing_detector/routing/docling_router.py | TBD | Docling-specific routing: 6 rules (text layer quality → script-aware → VLM → table mode → enrichments → PSM) |

**Subtotal**: 1,568+ lines (LOC recount needed)

---

### Output (503 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/output/**init**.py | 17 | Module exports |
| src/image_preprocessing_detector/output/json_generator.py | 486 | Generate DocumentMetadata.json |

**Subtotal**: 503 lines

---

### Device Orchestration & Workers (931 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/utils/device_probe.py | 183 | GPU/CPU capability detection |
| src/image_preprocessing_detector/workers/**init**.py | 27 | Celery app initialization |
| src/image_preprocessing_detector/workers/celery_app.py | 250 | Celery configuration |
| src/image_preprocessing_detector/workers/tasks.py | 471 | Celery task definitions (process_document, batch_process) |

**Subtotal**: 931 lines

**Note**: `orchestration/device_orchestrator.py` now EXISTS at `src/image_preprocessing_detector/orchestration/device_orchestrator.py` and `src/image_preprocessing_detector/orchestration/modal_client.py`. Also add to WS1: `src/image_preprocessing_detector/utils/budget_enforcement.py`.

**Additional WS1 files found in repo but not yet in inventory** (needs LOC recount):

| File Path | Suggested WS1 Sub-Area |
|-----------|------------------------|
| src/image_preprocessing_detector/orchestration/device_orchestrator.py | Device Orchestration |
| src/image_preprocessing_detector/orchestration/modal_client.py | Device Orchestration |
| src/image_preprocessing_detector/utils/budget_enforcement.py | Device Orchestration |
| src/image_preprocessing_detector/detection/deskew_pipeline.py | Detection - Text Gate & IQA |
| src/image_preprocessing_detector/detection/shadow_detector.py | Detection - Text Gate & IQA |
| src/image_preprocessing_detector/detection/warping_detector.py | Detection - Text Gate & IQA |
| src/image_preprocessing_detector/detection/code_detector.py | Detection - Text Gate & IQA |
| src/image_preprocessing_detector/detection/blank_page_detector.py | Detection - Text Gate & IQA |
| src/image_preprocessing_detector/detection/handwriting_detector.py | Detection - Text Gate & IQA |
| src/image_preprocessing_detector/detection/script_detector.py | Detection - Text Gate & IQA |
| src/image_preprocessing_detector/detection/table_complexity.py | Detection - Layout Lite |
| src/image_preprocessing_detector/routing/script_router.py | Metrics & Routing |
| src/image_preprocessing_detector/routing/psm_recommender.py | Metrics & Routing |
| src/image_preprocessing_detector/metrics/calibration.py | Metrics & Routing |
| src/image_preprocessing_detector/classification/degradation_classifier.py | Classification |
| src/image_preprocessing_detector/classification/document_source_classifier.py | Classification |
| src/image_preprocessing_detector/classification/text_layer_analyzer.py | Classification |
| src/image_preprocessing_detector/utils/datetime_compat.py | Shared Utility |
| src/image_preprocessing_detector/utils/log_config.py | Shared Utility |
| src/image_preprocessing_detector/utils/metadata_generator.py | Shared Utility |
| src/image_preprocessing_detector/utils/model_config.py | Shared Utility |

**WS1 Planned files** (referenced in PUML diagrams; not yet in repo):

| File Path | Suggested WS1 Sub-Area | Diagram Source |
|-----------|------------------------|----------------|
| src/image_preprocessing_detector/routing/document_type_router.py | Metrics & Routing | prepare-doc-primary-workflow-detailed.puml, prepare-doc-primary-workflow-high-level.puml, PREPARE_DOC_WORKFLOW_HIERARCHY.puml |
| src/image_preprocessing_detector/detection/mobilenetv4_precorrection.py | Detection - Text Gate & IQA | prepare-doc-primary-workflow-detailed.puml, production-runtime-swimlane.puml |
| src/image_preprocessing_detector/detection/stage_gate.py | Detection - Text Gate & IQA | prepare-doc-primary-workflow-detailed.puml, production-runtime-swimlane.puml |

**Additional WS1 files (continued)**:

| File Path | Suggested WS1 Sub-Area |
|-----------|------------------------|
| src/image_preprocessing_detector/utils/path_security.py | Shared Utility |
| src/image_preprocessing_detector/schema.py | WS1 - Output Schema |
| src/image_preprocessing_detector/cli.py | WS1 - Entry Point |
| src/image_preprocessing_detector/cli_layout.py | WS1 - Entry Point |
| src/image_preprocessing_detector/core/config.py | WS1 - Core Config |
| src/image_preprocessing_detector/core/exceptions.py | WS1 - Core Config |
| src/image_preprocessing_detector/api/app.py | WS1 - API |
| src/image_preprocessing_detector/api/config.py | WS1 - API |
| src/image_preprocessing_detector/api/middleware.py | WS1 - API |
| src/image_preprocessing_detector/api/models.py | WS1 - API |
| src/image_preprocessing_detector/api/routes/batch.py | WS1 - API |
| src/image_preprocessing_detector/api/routes/health.py | WS1 - API |
| src/image_preprocessing_detector/api/routes/process.py | WS1 - API |
| src/image_preprocessing_detector/logging/errors.py | WS1 - Logging |
| src/image_preprocessing_detector/logging/outcomes.py | WS1 - Logging |
| `src/image_preprocessing_detector/pipeline/__init__.py` | WS1 - Pipeline |

**WS1 Total**: 16,910 lines ✅ (matches LOC extraction)

---

## WS2: Model Training

**Total Files**: 16
**Total LOC**: 7,058
**Level 2 Doc**: [model-training/index.md](diagrams/level-2/model-training/index.md)

### Training Scripts — CURRENT (in repo)

> **NOTE**: The two-model pipeline uses MobileNetV4-Conv-S (~3ms, 3 heads) and SigLIP 2 NAFlex (~50ms, 16 heads, 5 groups). See [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) and [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md).

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| modal/train_siglip2_multitask.py | TBD | SigLIP 2 multi-task training (Stream 4C); two-phase: frozen backbone → fine-tune w/ PCGrad |
| modal/train_siglip2_iqa.py | TBD | SigLIP 2 IQA training |
| modal/train_siglip2_iqa_v2.py | TBD | SigLIP 2 IQA v2 training |
| modal/train_skew_estimator.py | TBD | MobileNetV4 skew estimator training |
| modal/train_phase3_doclayout_yolo.py | TBD | docling-layout fine-tuning |
| modal/train_phase6_layout_lite.py | TBD | Layout-lite training |
| config/siglip2_multitask.yaml | TBD | SigLIP 2 model architecture, head configs, training hyperparams (phase 1/2 LR, loss weights, EMA, mixed precision, go/no-go thresholds) |

### Shared Training Utilities — CURRENT (in repo)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| `modal/shared/__init__.py` | ~5 | Package init |
| modal/shared/metrics_utils.py | 223 | Training metrics (PLCC, SRCC, MAE) shared across training scripts |
| modal/shared/gcs_utils.py | 130 | GCS auth setup, upload/download helpers |
| modal/shared/dataset_utils.py | 61 | Dataset loading utilities shared across training scripts |
| modal/shared/constants.py | 58 | Shared constants (bucket names, paths, class labels) |

### Training Scripts — PLANNED (not yet in repo)

> Referenced in level-3 model-training swimlane and level-1 workflow hierarchy.

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| modal/train_mobilenetv4.py | TBD | MobileNetV4-Conv-S bootstrap + distillation training (Steps 1 and 3 of virtuous cycle) |
| modal/export_onnx.py | TBD | ONNX export for both SigLIP 2 and MobileNetV4 models |
| src/image_preprocessing_detector/training/siglip2_trainer.py | TBD | SigLIP 2 multi-task training configuration and loop |
| src/image_preprocessing_detector/training/mobilenetv4_trainer.py | TBD | MobileNetV4 bootstrap + distillation trainer |
| src/image_preprocessing_detector/training/generate_soft_labels.py | TBD | Generate SigLIP 2 soft labels for MobileNetV4 distillation |
| src/image_preprocessing_detector/models/siglip2_naflex.py | TBD | SigLIP 2 NAFlex model definition (88M params, 22 heads) |
| src/image_preprocessing_detector/models/mobilenetv4_gate.py | TBD | MobileNetV4-Conv-S pre-correction gate (3 heads) |
| src/image_preprocessing_detector/datasets/multitask_dataset.py | TBD | PyTorch MultiTaskDataset (parquet loading, per-task transforms, SHA256-keyed splits) |

---

### Training Scripts — LEGACY (❌ NOT IN REPO — deleted)

> These files were in a previous inventory but no longer exist in the repository.

| File Path | LOC | Status |
|-----------|-----|--------|
| ~~modal/train_phase2_iqa.py~~ | 707 | ❌ Deleted — replaced by train_siglip2_iqa.py |
| ~~modal/train_student_distillation.py~~ | 779 | ❌ Deleted — superseded |
| ~~modal/export_phase7_onnx.py~~ | 347 | ❌ Deleted |

---

### Training Infrastructure (❌ NOT IN REPO — src/training/ package deleted)

> The `src/image_preprocessing_detector/training/` package no longer exists. Training logic lives in modal scripts.

| File Path | LOC | Status |
|-----------|-----|--------|
| ~~src/image_preprocessing_detector/training/teacher_trainer.py~~ | 586 | ❌ Deleted |
| ~~src/image_preprocessing_detector/training/student_trainer.py~~ | 664 | ❌ Deleted |
| ~~src/image_preprocessing_detector/training/distillation_loss.py~~ | 248 | ❌ Deleted |
| ~~src/image_preprocessing_detector/training/generate_soft_labels.py~~ | 313 | ❌ Deleted |
| ~~src/image_preprocessing_detector/training/checkpoint_utils.py~~ | 82 | ❌ Deleted |

---

### Model Architectures (in repo)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/models/skew_estimator.py | TBD | MobileNetV4-Conv-S + 3 heads (orient, bins, regression) |
| src/image_preprocessing_detector/models/onnx_runtime.py | TBD | ONNX Runtime inference wrapper |

### Model Architectures (❌ NOT IN REPO — legacy ResNet models deleted)

| File Path | LOC | Status |
|-----------|-----|--------|
| ~~src/image_preprocessing_detector/models/resnet_teacher.py~~ | 293 | ❌ Deleted — superseded by SigLIP 2 NAFlex |
| ~~src/image_preprocessing_detector/models/resnet_student.py~~ | 277 | ❌ Deleted — superseded by MobileNetV4-Conv-S |
| ~~src/image_preprocessing_detector/models/model_loader.py~~ | 244 | ❌ Deleted |
| ~~src/image_preprocessing_detector/models/model_optimizer.py~~ | 1,435 | ❌ Deleted |
| ~~src/image_preprocessing_detector/models/batch_inference.py~~ | 622 | ❌ Deleted |
| ~~src/image_preprocessing_detector/models/loss_functions.py~~ | 330 | ❌ Deleted |

**WS2 Total**: Requires full recount (legacy scripts deleted; 6 new modal training scripts added)

---

## WS3: Data Preparation

**Total Files**: 8
**Total LOC**: 4,066
**Level 2 Doc**: [data-preparation/index.md](diagrams/level-2/data-preparation/index.md)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| scripts/download_all_datasets.py | 470 | Dataset collection orchestrator |
| scripts/download_phase3_datasets.py | 290 | Download OHR-Bench, phase-specific datasets |
| scripts/download_table_datasets.py | 569 | Download TableBank, PubTabNet |
| scripts/annotate_base_metadata.py | 1,235 | Layer 1 (Immutable) + Layer 2 (Enrichment) metadata |
| scripts/build_training_labels.py | 590 | Layer 3 (Training) - 45-dim IQA vector, anchor scores |
| scripts/validate_datasets.py | 429 | Dataset integrity validation |

### Stream 4C — Multi-Task Dataset Preparation (⚠️ NOT IN PREVIOUS INVENTORY)

These 10 scripts form the **Stream 4C dataset preparation sub-system** for SigLIP 2 multi-task training. They run in three logical stages: augmentation generation → label computation → manifest assembly/validation.

**Stage 1: Augmentation Generation**

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| scripts/generate_v3_shadow_view.py | TBD | Synthesize 8K shadow images from v3 base (4 types: edge/cast/spotlight/scanner_lid) |
| scripts/generate_v3_warping_view.py | TBD | Synthesize 5K warped images from v3 base (perspective/page_curl/fold) |
| scripts/derive_v3_orientation_view.py | TBD | Extract non-Latin v3 images + fetch orientation labels from sidecars (≤20K synthetic) |
| scripts/build_orientation_real_component.py | TBD | Download DocLayNet/RVL-CDIP PDFs from GCS, render pages, apply 4 rotations (≤30K real) |

**Stage 2: Label Computation**

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| scripts/label_shadow_severity.py | TBD | Compute luminance-delta severity for sd7k/wsrd paired images; writes to L2 metadata |
| scripts/label_warping_severity.py | TBD | Compute SSIM-based severity for warpdoc/wsrd/anyphotodoc6300/docalign12k; writes to L2 metadata |
| scripts/harmonize_handwriting_labels.py | TBD | Assemble handwriting-presence manifest from IAM/FUNSD/HierText/COCO-Text/L2 DocLayout inference |
| scripts/generate_multitask_labels.py | TBD | Run SigLIP 2 teacher in eval mode on unlabeled corpus → pseudo-labels for active learning |

**Stage 3: Audit & Manifest Assembly**

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| scripts/audit_font_coverage.py | TBD | Verify synth-multiscript-v3 fonts meet ≥5 families/script; exits non-zero if under threshold |
| scripts/audit_v3_per_script_counts.py | TBD | Count v3 images per script from GCS; compare vs target; generate resume-points for generator |
| scripts/prepare_multitask_datasets.py | TBD | Main orchestrator: 6 Click sub-commands (script/orientation/source/shadow/warping/merge) + OOD leakage checks + ≤60% synthetic mixing enforcement |
| scripts/evaluate_dataset_diversity.py | TBD | Dataset Diversity Report (DDR) generator; evaluates 14 dimensions, markdown reports, OOD checks |

**Note**: `label_shadow_severity.py` and `label_warping_severity.py` write back into L2 metadata registry — see planned [L2 Metadata Enrichment diagram](../diagrams/level-2/data-preparation/).

---

### Scripts — ❌ NOT IN REPO

| File Path | LOC | Status |
|-----------|-----|--------|
| ~~scripts/download_iqa_datasets.py~~ | 79 | ❌ Not found in repo |
| ~~scripts/download_omnidocbench.py~~ | 404 | ❌ Not found in repo |

### Large Annotation Package — ⚠️ NOT YET IN INVENTORY

The `src/image_preprocessing_detector/annotation/` package (~60 files, ~19,600 LOC) is the primary WS3 implementation but was not tracked in the original inventory. Key sub-packages:

| Sub-Package | Files | Purpose |
|-------------|-------|---------|
| annotation/parsers/correction/ | 8 | Dataset-specific correction parsers |
| annotation/parsers/document/ | 10 | Document dataset parsers |
| annotation/parsers/layout/ | 10 | Layout dataset parsers |
| annotation/parsers/multilingual/ | 14 | Multilingual/script parsers |
| annotation/parsers/handwriting/ | 9 | Handwriting dataset parsers |
| annotation/parsers/quality/ | 5 | IQA quality parsers |
| annotation/enrichment/ | 7 | Enrichment manager + providers |
| annotation/schemas/ | 6 | Pydantic schemas |
| annotation/workflow/ | 6 | Orchestration pipeline |
| annotation/storage/ | 3 | Parquet storage |
| annotation/integrity/ | 3 | Atomic writes + checksums |
| annotation/monitoring/ | 2 | Metrics + logging |

**WS3 Total**: Requires recount (annotation/ package not included in previous count)

---

## WS4: Pseudo-Labeling

**Total Files**: 8
**Total LOC**: 2,947
**Level 2 Doc**: [pseudo-labeling/index.md](diagrams/level-2/pseudo-labeling/index.md)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| scripts/run_model_benchmark.py | 1,486 | Local benchmark execution |

### WS4 Scripts — ❌ NOT IN REPO (verify)

| File Path | LOC | Status |
|-----------|-----|--------|
| ~~modal/generate_pseudo_labels.py~~ | 1,042 | ❌ Not found in current repo listing |
| ~~modal/arena_benchmark.py~~ | 419 | ❌ Not found in current repo listing |

**Note**: `src/image_preprocessing_detector/labeling/ensemble/` not found in current codebase (may be integrated into arena/ or planned)

### WS4 Planned Files (referenced in PUML diagrams)

| File Path | LOC | Diagram Source |
|-----------|-----|----------------|
| modal/stage1_deqa_inference.py | TBD | pseudo-labeling-swimlane.puml, schema-field-population-workflow.puml |
| modal/teacher_inference.py | TBD | pseudo-labeling-swimlane.puml, schema-field-population-workflow.puml |

**WS4 Total**: Requires recount (2 modal scripts absent from repo)

---

## WS5: Labeling & Benchmarking Models

**Total Files**: 0
**Total LOC**: 0
**Level 2 Doc**: [labeling-benchmarking/index.md](diagrams/level-2/labeling-benchmarking/index.md)

**Status**: ⚠️ **Infrastructure planned but not implemented**

**Planned Files**:

- `modal/labeling_models/train_musiq.py` (~200 lines)
- `modal/labeling_models/train_qualiclip.py` (~180 lines)
- `modal/labeling_models/train_dociq.py` (~250 lines)
- `modal/labeling_models/train_vlm.py` (~220 lines)
- `modal/labeling_models/export_for_pseudo_labeling.py` (~150 lines)
- `src/image_preprocessing_detector/labeling/models/` (wrappers, ~300 lines)

**Expected Total**: ~1,300 lines when implemented

### WS5 Planned Files (referenced in PUML diagrams)

| File Path | LOC | Diagram Source |
|-----------|-----|----------------|
| src/image_preprocessing_detector/labeling/deqa/config.py | TBD | metadata-schema-architecture.puml |
| src/image_preprocessing_detector/labeling/finetuning/dataset.py | TBD | metadata-schema-architecture.puml |

---

## WS6: Model Arena

**Total Files**: 33
**Total LOC**: 6,340
**Level 2 Doc**: [model-arena/index.md](diagrams/level-2/model-arena/index.md)

### Core Infrastructure (2,357 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/labeling/arena/**init**.py | 97 | Public API exports |
| src/image_preprocessing_detector/labeling/arena/runner.py | 630 | ArenaRunner orchestrator |
| src/image_preprocessing_detector/labeling/arena/metrics.py | 445 | PLCC, SRCC, MAE, RMSE with bootstrap CIs |
| src/image_preprocessing_detector/labeling/arena/schemas.py | 482 | Data models, serialization |
| src/image_preprocessing_detector/labeling/arena/leaderboard.py | 305 | Leaderboard generation (Markdown, HTML) |
| src/image_preprocessing_detector/labeling/arena/cli.py | 196 | CLI (run, leaderboard, compare) |
| src/image_preprocessing_detector/labeling/arena/modal_client.py | 202 | Modal GPU client |

**Subtotal**: 2,357 lines

---

### Dataset Adapters (441 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/labeling/arena/datasets/**init**.py | 40 | Dataset exports |
| src/image_preprocessing_detector/labeling/arena/datasets/base.py | 201 | Abstract BenchmarkDataset interface |
| src/image_preprocessing_detector/labeling/arena/datasets/diqa5000.py | 200 | DIQA-5000 dataset implementation |

**Subtotal**: 441 lines

---

### Inference Backends (1,082 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/labeling/arena/inference/**init**.py | 60 | Backend factory |
| src/image_preprocessing_detector/labeling/arena/inference/base.py | 122 | Abstract InferenceBackend |
| src/image_preprocessing_detector/labeling/arena/inference/local.py | 301 | PyTorch local GPU/CPU backend |
| src/image_preprocessing_detector/labeling/arena/inference/huggingface.py | 243 | HuggingFace transformers backend |
| src/image_preprocessing_detector/labeling/arena/inference/modal.py | 180 | Modal serverless backend |
| src/image_preprocessing_detector/labeling/arena/inference/api.py | 102 | API backend (OpenAI, Gemini) |
| src/image_preprocessing_detector/labeling/arena/inference/regression.py | 74 | Regression model wrapper |

**Subtotal**: 1,082 lines

---

### Utilities (2,460 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/labeling/arena/utils/**init**.py | 25 | Utility exports |
| src/image_preprocessing_detector/labeling/arena/utils/reproducibility.py | 312 | Manifest generation, seed control |
| src/image_preprocessing_detector/labeling/arena/utils/bootstrap.py | 268 | Bootstrap confidence interval calculation |
| src/image_preprocessing_detector/labeling/arena/utils/visualization.py | 245 | Result plotting |
| *(and 18 more utility files)* | ~1,610 | Various arena utilities |

**Subtotal**: 2,460 lines

**WS6 Total**: 6,340 lines ✅ (matches LOC extraction)

---

## WS7: Monitoring & Drift Detection

**Total Files**: 7
**Total LOC**: 5,348
**Level 2 Doc**: [monitoring-drift/index.md](diagrams/level-2/monitoring-drift/index.md)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/drift/**init**.py | 985 | Distribution tracking, KL divergence, PSI |
| src/image_preprocessing_detector/drift/performance.py | 1,027 | Performance monitoring, evaluation jobs |
| src/image_preprocessing_detector/drift/alerting.py | 1,061 | Multi-channel alerting (Log, Slack, Webhook) |
| src/image_preprocessing_detector/drift/active_learning.py | 842 | Sample harvesting for retraining |
| src/image_preprocessing_detector/drift/privacy_review.py | 695 | GDPR/CCPA-compliant review workflow |
| src/image_preprocessing_detector/drift/retraining.py | 743 | Retraining orchestration |
| monitoring/ *(configs)* | ~5 | Prometheus/Grafana YAML configs |

**WS7 Total**: 5,353 lines ✅ (matches LOC extraction ~5,348)

---

## WS8: Synthetic Data Generation

**Total Files**: 5+ (expanded with multi-task generation)
**Total LOC**: ~1,500+ (expanded from 1,066 after multi-task additions to config.py, generator.py, augmentation_hybrid.py, schema_adapter.py, cli.py)
**Level 2 Doc**: [synthetic-generation/index.md](diagrams/level-2/synthetic-generation/index.md)

### WS8 Files — CURRENT (package moved from augmentation/ to synthetic/)

> **Path correction**: The `augmentation/` package no longer exists. All synthetic generation code is in `src/image_preprocessing_detector/synthetic/`.

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/synthetic/config.py | TBD | 7 DPI tiers, ColorMode enum, composition weights |
| src/image_preprocessing_detector/synthetic/generator.py | TBD | Base image generation (per-script pool pruning; bug fixed 2026-02-09) |
| src/image_preprocessing_detector/synthetic/augmentation.py | TBD | Standard degradation pipeline |
| src/image_preprocessing_detector/synthetic/augmentation_fast.py | TBD | Fast augmentation variant |
| src/image_preprocessing_detector/synthetic/augmentation_hybrid.py | TBD | Hybrid augmentation (AGED/HISTORICAL profiles) |
| src/image_preprocessing_detector/synthetic/cli.py | TBD | CLI flags (--color-mode, --skew, --orientation) |
| src/image_preprocessing_detector/synthetic/corpus.py | TBD | Text corpus management |
| src/image_preprocessing_detector/synthetic/fonts.py | TBD | Font selection/loading |
| src/image_preprocessing_detector/synthetic/renderer.py | TBD | Text rendering |
| src/image_preprocessing_detector/synthetic/schema_adapter.py | TBD | Multi-task metadata (`metadata["data"]["multi_task"]`) |
| src/image_preprocessing_detector/synthetic/validation.py | TBD | Output validation |

### Stream 4C Multi-Task Dataset Scripts (WS8 extension)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| scripts/generate_base_dataset_v3.py | TBD | v3 base dataset generation (bug fixed: per-script dict) |
| scripts/prepare_multitask_datasets.py | TBD | 6 sub-commands: script/orientation/source/shadow/warping/merge |
| scripts/generate_v3_shadow_view.py | TBD | 8K shadow images (edge/cast/spotlight/scanner_lid) |
| scripts/generate_v3_warping_view.py | TBD | 5K warped images (perspective/page_curl/fold) |
| scripts/derive_v3_orientation_view.py | TBD | Non-Latin v3 orientation component |
| scripts/build_orientation_real_component.py | TBD | DocLayNet/RVL-CDIP PDFs, 4 rotations |
| scripts/label_shadow_severity.py | TBD | Shadow severity labeling for L2 |
| scripts/label_warping_severity.py | TBD | Warping severity labeling for L2 |
| scripts/generate_multitask_labels.py | TBD | Combined multi-task label generation |
| scripts/evaluate_dataset_diversity.py | TBD | DDR evaluation script |

### WS8 Files — ❌ NOT IN REPO (stale paths)

| File Path | LOC | Status |
|-----------|-----|--------|
| ~~`src/image_preprocessing_detector/augmentation/__init__.py`~~ | 36 | ❌ Path wrong — now synthetic/ |
| ~~src/image_preprocessing_detector/augmentation/genalog_config.py~~ | 294 | ❌ Path wrong — now synthetic/ |
| ~~src/image_preprocessing_detector/augmentation/genalog_degrader.py~~ | 314 | ❌ Path wrong — now synthetic/ |
| ~~benchmarks/adapters/synthetic_iqa_adapter.py~~ | 422 | ❌ Not found in repo |

**WS8 Total**: Requires full recount (package path changed; 10+ new Stream 4C scripts added)

---

## NA - Test Files

**Total Files**: ~300
**Total LOC**: ~15,000
**Reason**: Excluded from workstream LOC counts (separate test suite)

**Sample** (first 20):

| File Path | LOC | Test Scope |
|-----------|-----|------------|
| tests/unit/test_schema.py | 450 | Pydantic schema validation |
| tests/unit/ingestion/test_pdf_upscaler.py | 890 | DPI upscaling (38 tests) |
| tests/unit/detection/test_text_gate.py | 320 | Text gate ensemble |
| tests/integration/test_pipeline.py | 680 | End-to-end pipeline |
| tests/e2e/test_device_orchestrator.py | 540 | Device fallback logic |
| *(and ~295 more test files)* | ~12,120 | ... |

**Total Test LOC**: ~15,000 lines (not counted in workstream totals)

---

## NA - Documentation

**Total Files**: ~200
**Total LOC**: ~8,000
**Reason**: Documentation infrastructure, not application code

**Key Documentation**:

| File Path | LOC | Purpose |
|-----------|-----|---------|
| docs/architecture/ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md | 992 | Improvement tracking (this session) |
| docs/architecture/LEVEL_2_DOCUMENTATION_TEMPLATE.md | 650 | Level 2.5 standard |
| docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md | *(this file)* | File inventory |
| docs/architecture/LOC_EXTRACTION_METHODOLOGY.md | 580 | LOC extraction explained |
| docs/planning/PROJECT_PLAN.md | 2,100+ | Project phases and sprints |
| *(and ~195 more doc files)* | ~4,680 | Various documentation |

---

## NA - Configuration

**Total Files**: ~50
**Total LOC**: ~2,000
**Reason**: Configuration files, not application logic

**Key Config Files**:

| File Path | LOC | Purpose |
|-----------|-----|---------|
| pyproject.toml | 180 | Project metadata, dependencies, tool configs |
| uv.lock | 1,200+ | Dependency lockfile |
| config/layout_taxonomy.yaml | TBD | Unified layout label taxonomy (57 canonical classes, 6 schemas); referenced in schema-field-population-workflow.puml |
| configs/training/*.yaml | ~200 | Training hyperparameters |
| configs/monitoring/*.yaml | ~100 | Prometheus alert rules |
| .github/workflows/*.yml | ~400 | CI/CD pipelines |

---

## Unassigned Files (Needs Review)

**Total Files**: ~30
**Total LOC**: ~500

**These Python files need workstream assignment**:

| File Path | LOC | Suggested Workstream |
|-----------|-----|---------------------|
| src/image_preprocessing_detector/utils/logger.py | 85 | NA - Shared utility |
| src/image_preprocessing_detector/utils/gcs_uploader.py | 120 | NA - Shared utility |
| src/image_preprocessing_detector/utils/tensor_cache.py | 60 | WS1 - Production Runtime (performance optimization) |
| src/image_preprocessing_detector/schema.py | 118 | WS1 - Production Runtime (output schema) |
| src/image_preprocessing_detector/datasets/iqa_dataset.py | 180 | WS2 - Model Training (PyTorch dataset) |
| *(and ~25 more files)* | ~137 | ... |

**Action Required**: Review these files and either:

1. Assign to workstream (update LOC extraction script)
2. Mark as NA - Shared utility (exclude from counts)
3. Mark as obsolete (remove from codebase)

---

## NA - Architecture Diagrams

**Total Files**: 153 (as of 2026-02-21)
**Reason**: Documentation assets — PlantUML sources, rendered SVGs/PNGs, and index/narrative markdown files. Excluded from workstream LOC counts.

> **Anomalies found**: Two files have accidentally nested duplicate path segments (PlantUML ran from wrong directory). These are invalid artifacts:
>
> - `docs/architecture/diagrams/level-2/production-runtime/docs/architecture/diagrams/level-2/production-runtime/Project_A_Worker_Architecture.svg`
> - `docs/architecture/diagrams/level-2/schema-field-population/docs/architecture/diagrams/level-2/schema-field-population/schema-field-population-summary.svg`

### Root Architecture Documents

| File Path | Purpose |
|-----------|---------|
| docs/architecture/ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md | Improvement tracking |
| docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md | Maintenance procedures |
| docs/architecture/AUDIT.md | Architecture audit results |
| docs/architecture/DOCUMENTATION_IMPROVEMENT_SESSION_SUMMARY.md | Session summary |
| docs/architecture/FINAL_SESSION_SUMMARY.md | Final session summary |
| docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md | This file |
| docs/architecture/LEVEL_2_DOCUMENTATION_TEMPLATE.md | Level 2.5 standard template |
| docs/architecture/LEVEL_3_AGENT_ASSIGNMENTS.md | Level 3 agent assignments |
| docs/architecture/LEVEL_3_IMPLEMENTATION_ROADMAP.md | Level 3 roadmap |
| docs/architecture/LOC_EXTRACTION_METHODOLOGY.md | LOC extraction methodology |
| docs/architecture/SWIMLANE_TRACEABILITY_PROPOSAL.md | Swimlane traceability proposal |
| docs/architecture/workstream_loc_counts.json | JSON LOC counts per workstream |
| docs/architecture/diagrams/INDEX.md | Master diagram index |
| docs/architecture/diagrams/README.md | Diagrams README |
| docs/architecture/diagrams/STYLE_GUIDE.md | PlantUML style guide |

### Level 0 — RAG Pipeline Overview

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-0/index.md | Index |
| docs/architecture/diagrams/level-0/rag-pipeline-overview.puml | Source |
| docs/architecture/diagrams/level-0/rag-pipeline-overview.svg | Rendered |
| docs/architecture/diagrams/level-0/RAG_Pipeline_Overview.png | Rendered |
| docs/architecture/diagrams/level-0/rag-pipeline-visual.png | Rendered |
| docs/architecture/diagrams/level-0/rag-pipeline-visual.signature.bin | Signature |

### Level 1 — Prepare-Doc Architecture

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-1/index.md | Index |
| docs/architecture/diagrams/level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml | Source |
| docs/architecture/diagrams/level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.svg | Rendered |
| docs/architecture/diagrams/level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.png | Rendered |
| docs/architecture/diagrams/level-1/PREPARE_DOC_WORKFLOW_HIERARCHY.puml | Source |
| docs/architecture/diagrams/level-1/PREPARE_DOC_WORKFLOW_HIERARCHY.svg | Rendered |
| docs/architecture/diagrams/level-1/Project_A_Workflow_Hierarchy.png | Rendered |

### Level 2 — Workstream Details

#### WS3: Data Preparation

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/data-preparation/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/data-preparation/automated-data-labeling-pipeline.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/data-preparation/automated-data-labeling-pipeline.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/data-preparation/metadata-schema-architecture.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/data-preparation/metadata-schema-architecture.svg | Rendered | ✅ NEW |
| docs/architecture/diagrams/level-2/data-preparation/prepare-doc-training-data-ingestion.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/data-preparation/prepare-doc-training-data-ingestion.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/data-preparation/prepare-doc-training-data-ingestion.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/data-preparation/resolution-quality-labeling-pipeline.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/data-preparation/resolution-quality-labeling-pipeline.svg | Rendered | ✅ NEW |
| docs/architecture/diagrams/level-2/data-preparation/skew-orientation-labeling-pipeline.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/data-preparation/skew-orientation-labeling-pipeline.svg | Rendered | ✅ NEW |

#### WS5: Labeling & Benchmarking

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/labeling-benchmarking/index.md | Index | ✅ NEW |
| docs/architecture/diagrams/level-2/labeling-benchmarking/domain-classification-pipeline.md | Narrative | ✅ NEW |
| docs/architecture/diagrams/level-2/labeling-benchmarking/domain-classification-pipeline.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/labeling-benchmarking/domain-classification-pipeline.svg | Rendered | ✅ NEW |

#### WS6: Model Arena

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/model-arena/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/model-arena/model-arena-architecture.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/model-arena/model-arena-architecture.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/model-arena/model-arena-architecture.png | Rendered | ✅ |

#### WS2: Model Training

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/model-training/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-distillation.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-distillation.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-distillation.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-infrastructure.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-infrastructure.svg | Rendered | ✅ NEW |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-high-level.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-high-level.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-test-coverage.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-test-coverage.svg | Rendered | ✅ NEW |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-v2.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-v2.svg | Rendered | ✅ NEW |

#### WS7: Monitoring & Drift

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/monitoring-drift/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/monitoring-drift/monitoring-drift-architecture.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/monitoring-drift/monitoring-drift-architecture.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/monitoring-drift/monitoring-drift-architecture.png | Rendered | ✅ |

#### WS1: Production Runtime

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/production-runtime/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-device-selection-flow.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-device-selection-flow.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-device-selection-flow.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed-test-coverage.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed-test-coverage.svg | Rendered | ✅ NEW |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-high-level.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-high-level.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-test-coverage.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-test-coverage.svg | Rendered | ✅ NEW |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-worker-architecture.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/production-runtime/prepare-doc-worker-architecture.svg | Rendered | ✅ NEW |

#### WS4: Pseudo-Labeling

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/pseudo-labeling/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-checkpoint-selection.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-checkpoint-selection.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-checkpoint-selection.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-inference-pipeline.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-inference-pipeline.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-inference-pipeline.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-pseudo-labeling-workflow.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-pseudo-labeling-workflow.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-training-phases.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-training-phases.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/diqa-training-phases.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/pseudo-labeling/soft-label-pipeline-integration.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/pseudo-labeling/soft-label-pipeline-integration.svg | Rendered | ✅ NEW |

#### Schema Field Population (cross-workstream)

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/schema-field-population/index.md | Index | ✅ NEW |
| docs/architecture/diagrams/level-2/schema-field-population/schema-field-population-summary.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/schema-field-population/schema-field-population-summary.svg | Rendered | ✅ NEW |
| docs/architecture/diagrams/level-2/schema-field-population/schema-field-population-workflow.puml | Source | ✅ NEW |
| docs/architecture/diagrams/level-2/schema-field-population/schema-field-population-workflow.svg | Rendered | ✅ NEW |

#### WS8: Synthetic Generation

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/synthetic-generation/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/synthetic-generation/synthetic-generation-architecture.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/synthetic-generation/synthetic-generation-architecture.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/synthetic-generation/synthetic-generation-architecture.png | Rendered | ✅ |

#### Downstream Context (informational)

| File Path | Type | Status |
|-----------|------|--------|
| docs/architecture/diagrams/level-2/downstream-context/index.md | Index | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/chunk-fusion-chunking-workflow.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/chunk-fusion-chunking-workflow.svg | Rendered | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/chunk-fusion-chunking-workflow.png | Rendered | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/embed-vectorstore-workflow.puml | Source | ✅ |
| docs/architecture/diagrams/level-2/downstream-context/embed-vectorstore-workflow.png | Rendered | ✅ |

### Level 3 — Module Implementation (all NEW)

#### WS3: Data Preparation

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-3/data-preparation/index.md | Index |
| docs/architecture/diagrams/level-3/data-preparation/data-preparation-swimlane.puml | Source |
| docs/architecture/diagrams/level-3/data-preparation/data-preparation-swimlane.svg | Rendered |
| docs/architecture/diagrams/level-3/data-preparation/data-preparation-swimlane.png | Rendered |
| docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md | Narrative |
| docs/architecture/diagrams/level-3/data-preparation/metadata-schema-versioning.md | Narrative |

#### WS2: Model Training

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-3/model-training/index.md | Index |
| docs/architecture/diagrams/level-3/model-training/model-training-swimlane.puml | Source |
| docs/architecture/diagrams/level-3/model-training/model-training-swimlane.svg | Rendered |
| docs/architecture/diagrams/level-3/model-training/model-training-swimlane.png | Rendered |
| docs/architecture/diagrams/level-3/model-training/layout-fusion-downsampler.md | Narrative (legacy) |

#### WS7: Monitoring & Drift

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-3/monitoring-drift/index.md | Index |
| docs/architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.puml | Source |
| docs/architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.svg | Rendered |
| docs/architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.png | Rendered |
| docs/architecture/diagrams/level-3/monitoring-drift/end-to-end-lifecycle.md | Narrative |

#### WS1: Production Runtime

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-3/production-runtime/index.md | Index |
| docs/architecture/diagrams/level-3/production-runtime/production-runtime-swimlane.puml | Source |
| docs/architecture/diagrams/level-3/production-runtime/production-runtime-swimlane.svg | Rendered |
| docs/architecture/diagrams/level-3/production-runtime/production-runtime-swimlane.png | Rendered |
| docs/architecture/diagrams/level-3/production-runtime/device-orchestrator.md | Narrative |
| docs/architecture/diagrams/level-3/production-runtime/pipeline-state-machine.md | Narrative |

#### WS4: Pseudo-Labeling

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-3/pseudo-labeling/index.md | Index |
| docs/architecture/diagrams/level-3/pseudo-labeling/pseudo-labeling-swimlane.puml | Source |
| docs/architecture/diagrams/level-3/pseudo-labeling/pseudo-labeling-swimlane.svg | Rendered |
| docs/architecture/diagrams/level-3/pseudo-labeling/ensemble-stacking.md | Narrative |

#### WS8: Synthetic Generation

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/level-3/synthetic-generation/index.md | Index |
| docs/architecture/diagrams/level-3/synthetic-generation/synthetic-generation-swimlane.puml | Source |
| docs/architecture/diagrams/level-3/synthetic-generation/synthetic-generation-swimlane.svg | Rendered |
| docs/architecture/diagrams/level-3/synthetic-generation/augmentation-pipeline.md | Narrative |

### Deprecated Diagrams

| File Path | Type |
|-----------|------|
| docs/architecture/diagrams/deprecated/README.md | README |
| docs/architecture/diagrams/deprecated/benchmarking/index.md | Index |
| docs/architecture/diagrams/deprecated/benchmarking/project-a-benchmark-workflow.puml | Source |
| docs/architecture/diagrams/deprecated/benchmarking/project-a-benchmark-workflow.svg | Rendered |
| docs/architecture/diagrams/deprecated/benchmarking/project-a-benchmark-workflow.png | Rendered |

---

## Validation Checks

### Check 1: All LOC Extraction Files Exist

```bash
# Extract files from LOC extraction script
grep -oP 'src/[^"]+' scripts/extract_workstream_loc.sh

# Verify each exists
# ✅ All files in LOC script exist in this inventory
```

### Check 2: All Workstream Totals Match

> ⚠️ LOC counts are stale as of 2026-02-21. Many source files were added/removed since the last extraction run. All workstreams need a recount via `scripts/extract_workstream_loc.sh`.

| Workstream | Last Known LOC | Current Status |
|------------|----------------|----------------|
| WS1: Production Runtime | 16,910 | ⚠️ Stale — 30+ new files untracked |
| WS2: Model Training | 7,058 | ❌ Stale — training/ package deleted, 6 new modal scripts |
| WS3: Data Preparation | 4,066 | ❌ Stale — annotation/ package (~19,600 LOC) untracked |
| WS4: Pseudo-Labeling | 2,947 | ⚠️ Stale — 2 modal scripts absent from repo |
| WS5: Labeling & Benchmarking | 0 | ✅ Still 0 (planned only) |
| WS6: Model Arena | 6,340 | ✅ Likely current |
| WS7: Monitoring & Drift | 5,348 | ✅ Likely current |
| WS8: Synthetic Generation | ~1,500+ | ❌ Stale — package path changed + 10 new scripts |

### Check 3: Unassigned Files Need Review

**Unassigned Python Files**: 30+ files

**Recommended Actions**:

1. `schema.py` → Assign to WS1 (output schema)
2. `tensor_cache.py` → Assign to WS1 (performance optimization)
3. `utils/gcs_uploader.py`, `utils/log_config.py`, etc. → Mark as NA - Shared utility
4. `src/image_preprocessing_detector/annotation/` entire package → Assign to WS3
5. `src/image_preprocessing_detector/orchestration/` → Assign to WS1
6. `src/image_preprocessing_detector/api/` → Assign to WS1
7. `src/image_preprocessing_detector/labeling/domain/` → Assign to WS5/WS6
8. New `modal/train_*.py` scripts → Assign to WS2
9. ~~`src/image_preprocessing_detector/datasets/iqa_dataset.py`~~ — ❌ not in repo

---

## Next Steps

### 1. Add Workflow Step Annotations (Manual)

Update "Workflow Step" column for each file with:

- Specific pipeline stage (e.g., "Ingestion - PDF loading")
- Component name (e.g., "Classical IQA - Blur detector")
- Phase (e.g., "Phase 1: Dataset collection")

### 2. Create Traceability Tables in Level 2 Docs

For each workstream, add to index.md:

```markdown
## Source File Traceability

| Workflow Step | Source Files | LOC | Total |
|---------------|--------------|-----|-------|
| Ingestion & Preflight | pdf_loader.py, pdf_analyzer.py, pdf_resolution.py, pdf_upscaler.py, ... | 265, 256, 264, 330, ... | 2,235 |
| Classification | pdf_type_classifier.py, pdf_image_detector.py, pdf_text_extractor.py | 135, 194, 122 | 472 |
| ... | ... | ... | ... |
```

### 3. Create Level 3 Swimlane Diagrams

For complex workstreams (Production Runtime, Data Prep, Monitoring):

- Annotate each workflow step with source files + LOC
- Include legend showing total matches LOC extraction
- Add to `level-3/[workstream]/[workstream]-swimlane.puml`

### 4. Enhance LOC Extraction Script

Add validation mode:

```bash
./scripts/extract_workstream_loc.sh --validate-inventory

# Output:
# ✅ All files in inventory match LOC mappings
# ⚠️ 30 unassigned files need review
# 📝 Suggested assignments: [list]
```

---

## Maintenance

### After Adding New Source Files

1. Run `git ls-files` to update inventory
2. Assign file to workstream in this document
3. Update LOC extraction script mapping
4. Add file to appropriate workflow step in traceability table/swimlane

### Quarterly Review

1. Regenerate this inventory: `python3 /tmp/generate_file_inventory.py`
2. Review "Unassigned" section
3. Update LOC extraction script with new assignments
4. Validate totals still match

---

*This inventory will be auto-generated and manually annotated with workflow steps during Level 3 documentation creation.*
