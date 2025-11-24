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

### Overall Test Suite Score: 7/10 (revised based on actual CI run)

| Category | Score | Status |
|----------|-------|--------|
| Quantity (test-to-code ratio) | 9/10 | ~1.2:1 ratio, 723 tests |
| Organization | 9/10 | Well-structured |
| Quality Patterns | 8/10 | Strong AAA, property-based |
| **Coverage Config** | **7/10** | 89.72% with key modules covered |
| Real Data Testing | 5/10 | Underutilized fixtures |
| Edge Cases | 7/10 | Limited failure injection |

### Key Metrics (from full CI environment)

- **Tests collected**: 723
- **Tests passed**: 716 (7 skipped - Phase 3 features)
- **Coverage**: 89.72% (2,249 statements)
- **Source LOC**: ~11,300
- **Real-data tests**: 25 (test_real_fixtures.py in e2e + integration)

### Coverage by Module (actual CI run)

| Module | Coverage | Status |
|--------|----------|--------|
| `detection/iqa_classical.py` | 81.24% | OK |
| `detection/iqa_ml.py` | 83.90% | OK |
| `detection/text_gate.py` | 97.98% | Excellent |
| `ingestion/image_loader.py` | 97.22% | Excellent |
| `ingestion/pdf_loader.py` | 91.49% | Good |
| `ingestion/pdf_resolution.py` | 96.51% | Excellent |
| `ingestion/pdf_upscaler.py` | 98.98% | Excellent |
| `metrics/dqs_calculator.py` | 87.64% | Good |
| `output/json_generator.py` | 98.25% | Excellent |
| `schema.py` | 97.77% | Excellent |
| `utils/datetime_compat.py` | 95.30% | Excellent |
| `noxfile.py` | 62.60% | Needs work |

### Still Excluded from Coverage (needs tests)

The following modules are still excluded from coverage measurement and need tests:

#### layout_lite/ (9 files) - Phase 6 feature, NO tests
- `detection/layout_lite/analyzer.py` - Layout analyzer (139 LOC)
- `detection/layout_lite/table_detector.py` - Table detection (140 LOC)
- `detection/layout_lite/figure_detector.py` - Figure detection (113 LOC)
- `detection/layout_lite/column_detector.py` - Column detection (115 LOC)
- `detection/layout_lite/watermark_detector.py` - Watermark detection (90 LOC)
- `detection/layout_lite/fuzzy_scan_detector.py` - Scan quality (90 LOC)
- `detection/layout_lite/background_detector.py` - Background detection (92 LOC)
- `detection/layout_lite/layout_types.py` - Type definitions (78 LOC)
- `detection/layout_lite/constants.py` - Constants (64 LOC)

#### Training Module (6 files) - Requires PyTorch
- `training/teacher_trainer.py` - Teacher training (528 LOC)
- `training/student_trainer.py` - Student training (597 LOC)
- `training/distillation_loss.py` - Distillation (248 LOC)
- `training/generate_soft_labels.py` - Label generation (304 LOC)
- `training/checkpoint_utils.py` - Checkpointing

#### Other Excluded
- `cli.py` - CLI interface (tested via integration but excluded from unit coverage)
- `augmentation/genalog_config.py` - Augmentation config (297 LOC)
- `augmentation/genalog_degrader.py` - Degradation (313 LOC)
- `routing/recommendation_engine.py` - Routing logic
- `utils/gcs_uploader.py` - GCS upload (322 LOC)
- `utils/metadata_generator.py` - Metadata (438 LOC)

---

## Modules WITH Good Coverage (from CI)

These modules are tested and have good coverage:

| Module | Stmts | Miss | Coverage | Notes |
|--------|-------|------|----------|-------|
| `detection/iqa_classical.py` | 403 | 65 | 81.24% | Core IQA |
| `detection/iqa_ml.py` | 261 | 34 | 83.90% | ML inference |
| `detection/text_gate.py` | 87 | 1 | 97.98% | Text detection |
| `ingestion/image_loader.py` | 82 | 0 | 97.22% | Image loading |
| `ingestion/pdf_loader.py` | 78 | 4 | 91.49% | PDF loading |
| `ingestion/pdf_resolution.py` | 72 | 3 | 96.51% | DPI analysis |
| `ingestion/pdf_upscaler.py` | 88 | 0 | 98.98% | Upscaling |
| `metrics/dqs_calculator.py` | 266 | 27 | 87.64% | Quality scores |
| `output/json_generator.py` | 88 | 2 | 98.25% | JSON output |
| `classification/pdf_image_detector.py` | 46 | 0 | 98.28% | PDF classification |
| `core/config.py` | 39 | 1 | 97.87% | Configuration |
| `schema.py` | 169 | 2 | 97.77% | Data models |
| `utils/datetime_compat.py` | 109 | 4 | 95.30% | Date utilities |
| `utils/model_config.py` | 37 | 1 | 95.74% | Model config |
| **TOTAL** | **2,249** | **193** | **89.72%** | - |

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
