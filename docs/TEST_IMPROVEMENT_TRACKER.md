# Test Improvement Tracker

**Created**: 2025-11-24
**Last Updated**: 2025-11-24
**Status**: Active
**Purpose**: Track test coverage gaps, improvements, and real-data testing priorities

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Gap Analysis](#gap-analysis)
4. [Available Test Fixtures](#available-test-fixtures)
5. [Prioritized TODO List](#prioritized-todo-list)
6. [Fixture Recommendations](#fixture-recommendations)
7. [Implementation Progress](#implementation-progress)

---

## Executive Summary

### Overall Test Suite Score: 6/10 (revised down due to coverage gaps)

| Category | Score | Status |
|----------|-------|--------|
| Quantity (test-to-code ratio) | 9/10 | ~1.2:1 ratio |
| Organization | 9/10 | Well-structured |
| Quality Patterns | 8/10 | Strong AAA, property-based |
| **Coverage Config** | **4/10** | **79% of files excluded** |
| Real Data Testing | 5/10 | Underutilized fixtures |
| Edge Cases | 7/10 | Limited failure injection |

### Key Metrics

- **Test functions**: 543
- **Test classes**: 117
- **Shared fixtures**: 18
- **Test LOC**: ~13,700
- **Source LOC**: ~11,300
- **Real-data tests**: 14 (only in `test_real_fixtures.py`)

### Critical Finding: Coverage Exclusions

| Metric | Value | Issue |
|--------|-------|-------|
| Total source files | 57 | - |
| Files in coverage | **12 (21%)** | Most code excluded |
| Files excluded | **45 (79%)** | Major blind spot |
| Reported coverage | 89.74% | **Misleading** |
| Estimated true coverage | ~25-30% | Based on file ratio |

---

## Actual Coverage Analysis (2025-11-24)

### Files INCLUDED in Coverage (12 files)

| File | Stmts | Miss | Branch | Cover | Status |
|------|-------|------|--------|-------|--------|
| `__init__.py` | 5 | 0 | 0 | 100% | OK |
| `classification/__init__.py` | 4 | 0 | 0 | 100% | OK |
| `classification/pdf_image_detector.py` | 46 | 0 | 12 | 98% | OK |
| `classification/pdf_text_extractor.py` | 42 | 0 | 10 | 100% | OK |
| `classification/pdf_type_classifier.py` | 25 | 0 | 6 | 100% | OK |
| `core/__init__.py` | 0 | 0 | 0 | 100% | OK |
| `core/config.py` | 39 | 1 | 8 | 98% | OK |
| `schema.py` | 169 | 2 | 10 | 98% | OK |
| `utils/__init__.py` | 17 | 2 | 4 | 86% | OK |
| `utils/datetime_compat.py` | 109 | 4 | 40 | 95% | OK |
| `utils/log_config.py` | 19 | 0 | 2 | 100% | OK |
| `utils/model_config.py` | 37 | 37 | 10 | **0%** | **NEEDS TESTS** |
| **TOTAL** | **512** | **46** | **102** | **89.74%** | - |

### Files EXCLUDED from Coverage (45 files) - **NO TEST VALIDATION**

#### Detection Module (11 files) - Core functionality, ZERO coverage
- `detection/__init__.py`
- `detection/iqa_classical.py` - Classical IQA (551 LOC)
- `detection/iqa_ml.py` - ML IQA (722 LOC)
- `detection/text_gate.py` - Text detection (341 LOC)
- `detection/layout_lite/__init__.py`
- `detection/layout_lite/analyzer.py` - Layout analyzer (139 LOC)
- `detection/layout_lite/table_detector.py` - Table detection (140 LOC)
- `detection/layout_lite/figure_detector.py` - Figure detection (113 LOC)
- `detection/layout_lite/column_detector.py` - Column detection (115 LOC)
- `detection/layout_lite/watermark_detector.py` - Watermark detection (90 LOC)
- `detection/layout_lite/fuzzy_scan_detector.py` - Scan quality (90 LOC)
- `detection/layout_lite/background_detector.py` - Background detection (92 LOC)
- `detection/layout_lite/layout_types.py` - Type definitions (78 LOC)
- `detection/layout_lite/constants.py` - Constants (64 LOC)

#### Ingestion Module (7 files) - PDF/image loading, ZERO coverage
- `ingestion/__init__.py`
- `ingestion/pdf_loader.py` - PDF loading (264 LOC)
- `ingestion/image_loader.py` - Image loading (281 LOC)
- `ingestion/pdf_upscaler.py` - DPI upscaling (326 LOC)
- `ingestion/pdf_resolution.py` - Resolution analysis (204 LOC)
- `ingestion/pdf_analyzer.py` - Pre-flight analysis (255 LOC)
- `ingestion/document_processor.py` - Document processing (286 LOC)

#### Correction Module (2 files) - Image corrections, ZERO coverage
- `correction/__init__.py`
- `correction/corrections.py` - Skew/contrast/blur fixes (442 LOC)

#### Output Module (2 files) - JSON generation, ZERO coverage
- `output/__init__.py`
- `output/json_generator.py` - JSON output (391 LOC)

#### Models Module (4 files) - ML models, ZERO coverage
- `models/__init__.py`
- `models/resnet_teacher.py` - Teacher model (293 LOC)
- `models/resnet_student.py` - Student model (277 LOC)
- `models/loss_functions.py` - Loss functions (329 LOC)

#### Training Module (6 files) - Training pipelines, ZERO coverage
- `training/__init__.py`
- `training/teacher_trainer.py` - Teacher training (528 LOC)
- `training/student_trainer.py` - Student training (597 LOC)
- `training/distillation_loss.py` - Distillation (248 LOC)
- `training/generate_soft_labels.py` - Label generation (304 LOC)
- `training/checkpoint_utils.py` - Checkpointing

#### Other Excluded (9 files)
- `cli.py` - CLI interface (412 LOC)
- `augmentation/genalog_config.py` - Augmentation config (297 LOC)
- `augmentation/genalog_degrader.py` - Degradation (313 LOC)
- `metrics/dqs_calculator.py` - DQS calculation (498 LOC)
- `routing/recommendation_engine.py` - Routing logic
- `utils/gcs_uploader.py` - GCS upload (322 LOC)
- `utils/metadata_generator.py` - Metadata (438 LOC)

---

## Current State Assessment

### Strengths

- [x] Comprehensive test categories (unit, integration, property-based, security)
- [x] Strong AAA pattern usage
- [x] Hypothesis property-based testing
- [x] Well-organized pytest fixtures in conftest.py
- [x] 80% coverage enforcement
- [x] Good mocking practices

### Weaknesses

- [ ] Many core modules excluded from coverage
- [ ] Limited real-data test coverage
- [ ] No performance/latency tests
- [ ] layout_lite module has zero tests
- [ ] Limited parametrized tests
- [ ] No snapshot/golden file tests

---

## Gap Analysis

### Critical: Modules with NO Tests

| Module | Files | LOC | Priority | Status |
|--------|-------|-----|----------|--------|
| `detection/layout_lite/` | 9 | ~3,200 | **HIGH** | [ ] Not started |
| `augmentation/` | 2 | ~610 | MEDIUM | [ ] Not started |
| `models/resnet_student.py` | 1 | 277 | **HIGH** | [ ] Not started |
| `routing/recommendation_engine.py` | 1 | ~150 | MEDIUM | [ ] Not started |

### layout_lite Module Breakdown

| File | LOC | Tests Needed | Fixtures to Use |
|------|-----|--------------|-----------------|
| `analyzer.py` | 139 | [ ] | doclaynet PDFs, tablebank images |
| `table_detector.py` | 140 | [ ] | simple_table_1.png, complex_table_2.png |
| `figure_detector.py` | 113 | [ ] | tables_figures_2.pdf, embedded_graphics_5.jpg |
| `column_detector.py` | 115 | [ ] | multi_column_3.pdf |
| `watermark_detector.py` | 90 | [ ] | **NEEDS NEW FIXTURE** |
| `fuzzy_scan_detector.py` | 90 | [ ] | low_quality_4.jpg, low_contrast_5.pdf |
| `background_detector.py` | 92 | [ ] | **NEEDS NEW FIXTURE** |
| `layout_types.py` | 78 | N/A | Types only |
| `constants.py` | 64 | N/A | Constants only |

### Modules Needing More Real-Data Tests

| Module | Current Tests | Gap | Recommended Action |
|--------|---------------|-----|-------------------|
| `iqa_classical` | Unit (synthetic) | No accuracy validation | Add tests with skewed_4.pdf, low_contrast_5.pdf |
| `text_gate` | Unit (synthetic) | No multilingual testing | Render wili_2018 samples to images |
| `corrections` | Unit (synthetic) | No before/after validation | Add quality improvement tests |
| `pdf_classifier` | Unit + integration | Limited PDF diversity | Need more hybrid PDFs |
| `dqs_calculator` | Integration only | No unit tests | Add dedicated unit tests |

---

## Available Test Fixtures

### Current Inventory (`data/test_fixtures/`)

```
data/test_fixtures/           Total: ~828 KB
├── doclaynet/               5 PDFs, 432 KB
│   ├── simple_text_1.pdf    (18K) - Simple text document
│   ├── tables_figures_2.pdf (29K) - Tables and figures
│   ├── multi_column_3.pdf   (50K) - Multi-column layout
│   ├── skewed_4.pdf         (234K) - Skewed/rotated pages
│   └── low_contrast_5.pdf   (84K) - Low contrast scans
│
├── tablebank/               5 images, 324 KB
│   ├── simple_table_1.png   (5K) - Simple 3-5 column table
│   ├── complex_table_2.png  (44K) - Complex merged cells
│   ├── rotated_3.jpg        (74K) - Rotated table
│   ├── low_quality_4.jpg    (133K) - Blurry/low quality
│   └── embedded_graphics_5.jpg (51K) - Table with graphics
│
├── wili_2018/               10 text files, 52 KB
│   ├── eng_eng.txt, fra_fra.txt, deu_deu.txt
│   ├── spa_spa.txt, zho_zho.txt, ara_ara.txt
│   ├── rus_rus.txt, jpn_jpn.txt, kor_kor.txt
│   └── hin_hin.txt
│
├── cocotext/                NOT EXTRACTED
└── omnidocbench/            NOT EXTRACTED
```

### Fixture Usage in Tests

| Fixture | Tests Using It | Utilization |
|---------|---------------|-------------|
| `doclaynet_pdfs` | 4 tests | Underutilized |
| `skewed_pdf` | 1 test | **Needs more** |
| `multi_column_pdf` | 1 test | **Needs more** |
| `simple_text_pdf` | 1 test | Adequate |
| `tablebank_images` | 2 tests | Underutilized |
| `simple_table_image` | 1 test | **Needs more** |
| `complex_table_image` | 1 test | **Needs more** |
| `wili_text_samples` | 2 tests | **Underutilized** |

---

## Prioritized TODO List

### Priority 1: Critical (layout_lite - highest impact)

- [ ] **Create `tests/unit/detection/test_layout_lite.py`**
  - [ ] `test_table_detector_on_simple_table()` - tablebank/simple_table_1.png
  - [ ] `test_table_detector_on_complex_table()` - tablebank/complex_table_2.png
  - [ ] `test_table_detector_on_rotated()` - tablebank/rotated_3.jpg
  - [ ] `test_figure_detector_on_tables_figures_pdf()` - doclaynet/tables_figures_2.pdf
  - [ ] `test_figure_detector_on_embedded_graphics()` - tablebank/embedded_graphics_5.jpg
  - [ ] `test_column_detector_single_column()` - doclaynet/simple_text_1.pdf
  - [ ] `test_column_detector_multi_column()` - doclaynet/multi_column_3.pdf
  - [ ] `test_fuzzy_scan_on_low_quality()` - tablebank/low_quality_4.jpg
  - [ ] `test_fuzzy_scan_on_low_contrast()` - doclaynet/low_contrast_5.pdf
  - [ ] `test_full_analyzer_integration()` - All doclaynet PDFs

### Priority 2: High (Real-data IQA validation)

- [ ] **Enhance `tests/integration/test_real_fixtures.py`**
  - [ ] `test_skew_detection_accuracy_on_skewed_fixture()` - Validate angle detection
  - [ ] `test_contrast_detection_on_low_contrast_fixture()` - Validate severity
  - [ ] `test_blur_detection_on_low_quality_fixture()` - Validate blur score
  - [ ] `test_corrections_improve_skewed_pdf()` - Before/after comparison
  - [ ] `test_corrections_improve_low_contrast()` - Before/after comparison

### Priority 3: Medium (New fixtures needed)

- [ ] **Create `iqa_samples/` fixtures**
  - [ ] Extract 5 samples from LIVE dataset with ground-truth DMOS
  - [ ] Generate 3 synthetic variants (extreme blur, combined defects, orientation)
  - [ ] Create `labels.json` with quality scores
  - [ ] Document citation requirements

- [ ] **Create `layout_samples/` fixtures**
  - [ ] Find/create watermarked document sample
  - [ ] Find/create colorful background sample
  - [ ] Find/create dense math formula sample
  - [ ] Find/create handwriting sample

### Priority 4: Medium (Unit tests for routing)

- [ ] **Create `tests/unit/test_dqs_calculator.py`**
  - [ ] `test_degradation_score_calculation()`
  - [ ] `test_structural_complexity_calculation()`
  - [ ] `test_dqs_aggregation()`
  - [ ] `test_edge_cases_and_boundaries()`

- [ ] **Create `tests/unit/test_recommendation_engine.py`**
  - [ ] `test_routing_recommendations()`
  - [ ] `test_ocr_strategy_selection()`

### Priority 5: Lower (ML model testing)

- [ ] **Create `tests/unit/models/test_resnet_student.py`**
  - [ ] `test_model_initialization()`
  - [ ] `test_forward_pass()`
  - [ ] `test_inference_on_iqa_samples()` (requires iqa_samples fixtures)

- [ ] **Create `tests/unit/test_augmentation.py`**
  - [ ] `test_genalog_degrader_applies_degradation()`
  - [ ] `test_genalog_config_validation()`

### Priority 6: Nice-to-have

- [ ] Add parametrized tests using `@pytest.mark.parametrize`
- [ ] Add performance/latency benchmark tests
- [ ] Add snapshot tests for JSON output validation
- [ ] Enable and run mutation testing regularly
- [ ] Add chaos/fault-injection tests

---

## Fixture Recommendations

### New Fixtures to Create

#### 1. `iqa_samples/` (Critical for ML testing)

```
data/test_fixtures/iqa_samples/
├── live/                      # LIVE dataset extracts (~1.5 MB)
│   ├── reference.png          # Clean reference (DMOS=0)
│   ├── jpeg_artifact.png      # JPEG compression (DMOS~25)
│   ├── gaussian_blur.png      # Blur (DMOS~45)
│   ├── white_noise.png        # Noise (DMOS~38)
│   └── low_contrast.png       # Low contrast (DMOS~52)
├── synthetic/                 # Generated variants (~0.5 MB)
│   ├── extreme_blur.png       # Edge case: extreme blur
│   ├── combined_defects.png   # Multiple degradations
│   └── skewed_document.png    # Orientation testing
└── labels.json                # Ground truth scores
```

**Source**: LIVE Image Quality Database (requires academic citation)

#### 2. `layout_samples/` (For layout_lite edge cases)

```
data/test_fixtures/layout_samples/
├── watermarked_doc.pdf        # Watermark detection
├── colorful_background.jpg    # Background detection
├── dense_math.pdf             # Math formula detection
├── handwriting_sample.jpg     # Handwriting presence
└── manifest.json
```

**Sources**:
- Watermarked: Generate synthetically or find CC-licensed sample
- Colorful background: Generate with PIL
- Dense math: arXiv paper extract (CC-licensed)
- Handwriting: IAM Handwriting Database (requires license check)

#### 3. `degraded_samples/` (For corrections testing)

```
data/test_fixtures/degraded_samples/
├── severely_skewed.pdf        # >10° skew angle
├── motion_blur.jpg            # Motion blur artifact
├── uneven_lighting.jpg        # Lighting gradient
├── heavy_jpeg.jpg             # Heavy JPEG compression
└── manifest.json
```

**Source**: Generate synthetically from existing clean fixtures

---

## Implementation Progress

### Completed

- [x] Initial test suite review (2025-11-24)
- [x] Gap analysis completed (2025-11-24)
- [x] Fixture inventory documented (2025-11-24)
- [x] Priority list created (2025-11-24)
- [x] This tracking document created (2025-11-24)

### In Progress

- [ ] None currently

### Blocked

- [ ] `iqa_samples/` creation - Needs LIVE dataset download
- [ ] `resnet_student` tests - Needs iqa_samples fixtures

---

## References

- [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) - Dataset storage strategy
- [data/test_fixtures/README.md](../data/test_fixtures/README.md) - Fixture documentation
- [tests/conftest.py](../tests/conftest.py) - Pytest fixtures and configuration
- [pyproject.toml](../pyproject.toml) - Coverage configuration

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-11-24 | Initial creation with full gap analysis | Claude |
