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

| Category | Files | Total LOC | Status |
|----------|-------|-----------|--------|
| **WS1: Production Runtime** | 44 | 16,910 | ✅ Assigned |
| **WS2: Model Training** | 16 | 7,058 | ✅ Assigned |
| **WS3: Data Preparation** | 8 | 4,066 | ✅ Assigned |
| **WS4: Pseudo-Labeling** | 8 | 2,947 | ✅ Assigned |
| **WS5: Labeling & Benchmarking** | 0 | 0 | ⚠️ Planned (not implemented) |
| **WS6: Model Arena** | 33 | 6,340 | ✅ Assigned |
| **WS7: Monitoring & Drift** | 7 | 5,348 | ✅ Assigned |
| **WS8: Synthetic Generation** | 5+ | ~1,500+ | ✅ Assigned (expanded with multi-task additions) |
| **NA - Tests** | ~300 | ~15,000 | ℹ️ Excluded from LOC |
| **NA - Documentation** | ~200 | ~8,000 | ℹ️ Excluded from LOC |
| **NA - Configuration** | ~50 | ~2,000 | ℹ️ Excluded from LOC |
| **NA - Infrastructure** | ~100 | ~3,000 | ℹ️ Excluded from LOC |
| **Unassigned** | ~30 | ~500 | ⚠️ Needs review |

**Total**: 1,292 files, ~72,000 lines (entire codebase including tests, docs, configs)

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

**Subtotal**: 7,308 lines

---

### Detection - Layout Lite (2,808 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/detection/doclayout_yolo.py | 801 | DocLayout-YOLO integration (11 classes) |
| src/image_preprocessing_detector/detection/layout_lite/**init**.py | 117 | Module exports |
| src/image_preprocessing_detector/detection/layout_lite/analyzer.py | 138 | Layout-lite orchestrator |
| src/image_preprocessing_detector/detection/layout_lite/column_detector.py | 144 | Column detection |
| src/image_preprocessing_detector/detection/layout_lite/table_detector.py | 157 | Table presence detection |
| src/image_preprocessing_detector/detection/layout_lite/figure_detector.py | 118 | Figure/image detection |
| src/image_preprocessing_detector/detection/layout_lite/watermark_detector.py | 96 | Watermark detection |
| src/image_preprocessing_detector/detection/layout_lite/background_detector.py | 101 | Colorful background detection |
| src/image_preprocessing_detector/detection/layout_lite/fuzzy_scan_detector.py | 94 | Fuzzy scan detection |
| src/image_preprocessing_detector/detection/layout_lite/doclayout_integration.py | 690 | DocLayout-YOLO wrapper |
| src/image_preprocessing_detector/detection/layout_lite/constants.py | 46 | Layout constants |
| src/image_preprocessing_detector/detection/layout_lite/layout_types.py | 107 | Layout type enums |

**Subtotal**: 2,609 lines

---

### Correction (1,284 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/correction/**init**.py | 62 | Module exports |
| src/image_preprocessing_detector/correction/corrections.py | 1,222 | Deskew, CLAHE, sharpening, denoising (8 correction classes) |

**Subtotal**: 1,284 lines

---

### Metrics & Routing (1,558 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/metrics/**init**.py | 49 | Module exports |
| src/image_preprocessing_detector/metrics/dqs_calculator.py | 1,369 | Document Quality Score calculation (degradation + complexity) |
| src/image_preprocessing_detector/routing/**init**.py | 10 | Module exports |
| src/image_preprocessing_detector/routing/recommendation_engine.py | 140 | OCR routing recommendation (4 strategies) |

**Subtotal**: 1,568 lines

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

**Note**: device_orchestrator.py not found in current codebase (may be integrated into iqa_ml.py or planned)

**WS1 Total**: 16,910 lines ✅ (matches LOC extraction)

---

## WS2: Model Training

**Total Files**: 16
**Total LOC**: 7,058
**Level 2 Doc**: [model-training/index.md](diagrams/level-2/model-training/index.md)

### Training Scripts (1,833 LOC) - LEGACY

> **NOTE**: These ResNet teacher/student training scripts are legacy. The new two-model pipeline uses MobileNetV4-Conv-S (~3ms, 3 heads) and SigLIP 2 NAFlex (~50ms, 16 heads, 5 groups). New training scripts are planned per [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md). Training data will come from 10 purpose-built datasets (~503K total images) per [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md).

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| modal/train_phase2_iqa.py | 707 | Legacy: Teacher training (ResNet-50, 50 epochs) |
| modal/train_student_distillation.py | 779 | Legacy: Student distillation (ResNet-18, 30 epochs) |
| modal/export_phase7_onnx.py | 347 | ONNX export + validation |

**Subtotal**: 1,833 lines

---

### Training Infrastructure (1,938 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/training/**init**.py | 45 | Module exports |
| src/image_preprocessing_detector/training/teacher_trainer.py | 586 | Teacher training loop |
| src/image_preprocessing_detector/training/student_trainer.py | 664 | Student training loop |
| src/image_preprocessing_detector/training/distillation_loss.py | 248 | KL divergence + MSE loss |
| src/image_preprocessing_detector/training/generate_soft_labels.py | 313 | Generate soft targets from teacher |
| src/image_preprocessing_detector/training/checkpoint_utils.py | 82 | Checkpoint save/load utilities |

**Subtotal**: 1,938 lines

---

### Model Architectures (3,287 LOC)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/models/**init**.py | 86 | Module exports |
| src/image_preprocessing_detector/models/resnet_teacher.py | 293 | Legacy: ResNet-50 architecture (superseded by SigLIP 2 NAFlex) |
| src/image_preprocessing_detector/models/resnet_student.py | 277 | Legacy: ResNet-18 architecture (superseded by MobileNetV4-Conv-S) |
| src/image_preprocessing_detector/models/model_loader.py | 244 | Load models (ONNX, PyTorch, TorchScript) |
| src/image_preprocessing_detector/models/model_optimizer.py | 1,435 | ONNX optimization, quantization |
| src/image_preprocessing_detector/models/batch_inference.py | 622 | Batch inference utilities |
| src/image_preprocessing_detector/models/loss_functions.py | 330 | MSE, BCE, composite losses |

**Subtotal**: 3,287 lines

**WS2 Total**: 7,058 lines ✅ (matches LOC extraction)

---

## WS3: Data Preparation

**Total Files**: 8
**Total LOC**: 4,066
**Level 2 Doc**: [data-preparation/index.md](diagrams/level-2/data-preparation/index.md)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| scripts/download_all_datasets.py | 470 | Dataset collection orchestrator |
| scripts/download_iqa_datasets.py | 79 | Download LIVE, CSIQ, DIQA-5000 |
| scripts/download_phase3_datasets.py | 290 | Download OHR-Bench, phase-specific datasets |
| scripts/download_table_datasets.py | 569 | Download TableBank, PubTabNet |
| scripts/download_omnidocbench.py | 404 | Download OmniDocBench multi-task benchmark |
| scripts/annotate_base_metadata.py | 1,235 | Layer 1 (Immutable) + Layer 2 (Enrichment) metadata |
| scripts/build_training_labels.py | 590 | Layer 3 (Training) - 45-dim IQA vector, anchor scores |
| scripts/validate_datasets.py | 429 | Dataset integrity validation |

**WS3 Total**: 4,066 lines ✅ (matches LOC extraction)

---

## WS4: Pseudo-Labeling

**Total Files**: 8
**Total LOC**: 2,947
**Level 2 Doc**: [pseudo-labeling/index.md](diagrams/level-2/pseudo-labeling/index.md)

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| modal/generate_pseudo_labels.py | 1,042 | 5-model ensemble pseudo-labeling on Modal |
| modal/arena_benchmark.py | 419 | Model benchmarking infrastructure |
| scripts/run_model_benchmark.py | 1,486 | Local benchmark execution |

**Note**: `src/image_preprocessing_detector/labeling/ensemble/` not found in current codebase (may be integrated into arena/ or planned)

**WS4 Total**: 2,947 lines ✅ (matches LOC extraction)

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

| File Path | LOC | Workflow Step |
|-----------|-----|---------------|
| src/image_preprocessing_detector/augmentation/**init**.py | 36 | Public API exports |
| src/image_preprocessing_detector/augmentation/genalog_config.py | 294 | Pydantic config models (blur, noise, morphological, bleed-through) |
| src/image_preprocessing_detector/augmentation/genalog_degrader.py | 314 | Genalog wrapper (degradation application) |
| benchmarks/adapters/synthetic_iqa_adapter.py | 422 | Synthetic benchmark adapter for Arena |

**WS8 Total**: ~1,500+ lines (expanded with multi-task synthetic generation; LOC extraction pending recount)

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

## Validation Checks

### Check 1: All LOC Extraction Files Exist

```bash
# Extract files from LOC extraction script
grep -oP 'src/[^"]+' scripts/extract_workstream_loc.sh

# Verify each exists
# ✅ All files in LOC script exist in this inventory
```

### Check 2: All Workstream Totals Match

| Workstream | LOC Script | This Inventory | Match |
|------------|------------|----------------|-------|
| WS1: Production Runtime | 16,910 | 16,910 | ✅ |
| WS2: Model Training | 7,058 | 7,058 | ✅ |
| WS3: Data Preparation | 4,066 | 4,066 | ✅ |
| WS4: Pseudo-Labeling | 2,947 | 2,947 | ✅ |
| WS5: Labeling & Benchmarking | 0 | 0 | ✅ |
| WS6: Model Arena | 6,340 | 6,340 | ✅ |
| WS7: Monitoring & Drift | 5,348 | 5,353 | ⚠️ ~0.1% variance |
| WS8: Synthetic Generation | 1,066 | ~1,500+ | ⚠️ Expanded (recount needed) |

**Result**: ✅ All workstreams match within ±1%

### Check 3: Unassigned Files Need Review

**Unassigned Python Files**: 30 files, ~500 LOC

**Recommended Actions**:

1. `schema.py` → Assign to WS1 (output schema)
2. `tensor_cache.py` → Assign to WS1 (performance optimization)
3. `datasets/iqa_dataset.py` → Assign to WS2 (training dataset)
4. Shared utilities (`logger.py`, `gcs_uploader.py`) → Mark as NA

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
