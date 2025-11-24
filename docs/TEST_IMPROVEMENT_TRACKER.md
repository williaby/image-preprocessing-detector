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
- [x] ~~No performance/latency tests~~ (tests/benchmark/test_performance.py added)
- [x] ~~layout_lite module has zero tests~~ (test_layout_lite.py added)
- [x] ~~Limited parametrized tests~~ (added to DQS and routing tests)
- [ ] No snapshot/golden file tests

---

## Gap Analysis

### Critical: Modules Status

| Module | Files | LOC | Priority | Status |
|--------|-------|-----|----------|--------|
| `detection/layout_lite/` | 9 | ~3,200 | **HIGH** | [x] Tests added (test_layout_lite.py) |
| `augmentation/` | 2 | ~610 | MEDIUM | [x] Tests added (test_genalog_config.py, test_genalog_degrader.py) |
| `models/resnet_student.py` | 1 | 277 | **HIGH** | [ ] Not started |
| `routing/recommendation_engine.py` | 1 | ~150 | MEDIUM | [x] Tests added (test_recommendation_engine.py) |

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

### Priority 1: Critical (layout_lite - highest impact) ✅ COMPLETED

- [x] **Created `tests/unit/detection/test_layout_lite.py`** (~512 lines, 35 tests)
  - [x] `TestTableDetector` - Tests for Hough line detection on tablebank fixtures
  - [x] `TestColumnDetector` - Tests for projection profile analysis
  - [x] `TestFigureDetector` - Tests for connected component analysis
  - [x] `TestFuzzyScanDetector` - Tests for blur/noise detection on low_quality_4.jpg
  - [x] `TestWatermarkDetector` - Tests for FFT analysis
  - [x] `TestBackgroundDetector` - Tests for color analysis
  - [x] `TestLayoutLiteAnalyzer` - Full analyzer integration tests
  - [x] `TestLayoutLiteEdgeCases` - Edge cases (small/large images, all black/white)

### Priority 2: High (Real-data IQA validation) ✅ COMPLETED

- [x] **Enhanced `tests/integration/test_real_fixtures.py`** (+235 lines, 6 tests)
  - [x] `test_skew_detection_accuracy_on_skewed_fixture()` - Validates angle detection on skewed_4.pdf
  - [x] `test_contrast_detection_on_low_contrast_fixture()` - Validates on low_contrast_5.pdf
  - [x] `test_blur_detection_on_low_quality_fixture()` - Validates blur on low_quality_4.jpg
  - [x] `test_clean_document_not_flagged()` - False positive detection on simple_text_1.pdf
  - [x] `test_deskew_correction_reduces_angle()` - Before/after deskew comparison
  - [x] `test_contrast_enhancement_improves_score()` - Before/after CLAHE comparison

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

### Priority 4: Medium (Unit tests for DQS & routing) ✅ COMPLETED

- [x] **Created `tests/unit/metrics/test_dqs_calculator.py`** (~670 lines, 45+ tests)
  - [x] `TestCalculateDegradationScore` - Weighted formula, validation, ML blending
  - [x] `TestCalculateStructuralComplexityScore` - Layout types, feature weights
  - [x] `TestAggregateDQS` - Page-to-document aggregation (median/max)
  - [x] `TestNormalizeClassicalIQA` - Detector output normalization
  - [x] `TestCalculatePreOCRRisk` - Risk scoring with penalties
  - [x] `TestDQSEdgeCases` - Boundary conditions

- [x] **Created `tests/unit/routing/test_recommendation_engine.py`** (~430 lines, 20+ tests)
  - [x] `TestVisionStructuredRouting` - Tables/figures → VISION_STRUCTURED
  - [x] `TestOCRFastRouting` - Born-digital + high quality → OCR_FAST
  - [x] `TestOCRAdvancedRouting` - High risk/handwriting → OCR_ADVANCED
  - [x] `TestVisionSimpleRouting` - Image-only + simple → VISION_SIMPLE
  - [x] `TestConservativeFallback` - Fallback behavior
  - [x] `TestMultiPageDocuments` - Multi-page routing logic
  - [x] `TestEdgeCases` - Boundary conditions

### Priority 5: Lower (ML model testing) - Partially Complete

- [ ] **Create `tests/unit/models/test_resnet_student.py`**
  - [ ] `test_model_initialization()`
  - [ ] `test_forward_pass()`
  - [ ] `test_inference_on_iqa_samples()` (requires iqa_samples fixtures)

- [x] **Created `tests/unit/augmentation/`** (~450 lines, 40+ tests)
  - [x] `test_genalog_config.py` - BlurConfig, SaltPepperConfig, MorphologicalConfig validation
  - [x] `test_genalog_degrader.py` - GenalogDegrader initialization, apply(), apply_batch()

### Priority 6: Nice-to-have

- [x] Add parametrized tests using `@pytest.mark.parametrize` ✅ COMPLETED
- [x] Add performance/latency benchmark tests ✅ COMPLETED
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
- [x] FIXTURE_ACQUISITION_TODO.md created (2025-11-24)
- [x] Coverage exemptions reduced in pyproject.toml (2025-11-24)
- [x] `tests/unit/detection/test_layout_lite.py` created (512 lines, 35 tests) (2025-11-24)
- [x] `tests/unit/augmentation/test_genalog_config.py` created (250 lines, 25 tests) (2025-11-24)
- [x] `tests/unit/augmentation/test_genalog_degrader.py` created (200 lines, 15 tests) (2025-11-24)
- [x] `tests/unit/routing/test_recommendation_engine.py` created (430 lines, 20+ tests) (2025-11-24)
- [x] `tests/integration/test_real_fixtures.py` enhanced with IQA validation (235 lines, 6 tests) (2025-11-24)
- [x] `tests/unit/metrics/test_dqs_calculator.py` created (670 lines, 45+ tests) (2025-11-24)
- [x] New fixtures added to conftest.py: low_quality_image, low_contrast_pdf (2025-11-24)
- [x] `tests/benchmark/test_performance.py` created (300+ lines, 15+ tests) (2025-11-24)
- [x] Added parametrized tests to test_dqs_calculator.py and test_recommendation_engine.py (2025-11-24)
- [x] `tests/unit/models/test_resnet_models.py` created (500+ lines, 35+ tests) (2025-11-24)
- [x] `tests/unit/utils/test_metadata_generator.py` created (400+ lines, 25+ tests) (2025-11-24)
- [x] `tests/unit/utils/test_gcs_uploader.py` created (350+ lines, 20+ tests) (2025-11-24)

### In Progress

- [ ] Snapshot tests for JSON output validation

### Blocked

- [ ] `iqa_samples/` creation - Needs LIVE dataset download (see FIXTURE_ACQUISITION_TODO.md)
- [ ] `layout_samples/` fixtures - Needs manual acquisition (see FIXTURE_ACQUISITION_TODO.md)

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
| 2025-11-24 | Added FIXTURE_ACQUISITION_TODO.md with manual acquisition guide | Claude |
| 2025-11-24 | Reduced coverage exemptions in pyproject.toml | Claude |
| 2025-11-24 | Added layout_lite tests (35 tests, 512 lines) | Claude |
| 2025-11-24 | Added augmentation tests (40 tests, 450 lines) | Claude |
| 2025-11-24 | Added routing recommendation engine tests (20+ tests, 430 lines) | Claude |
| 2025-11-24 | Added IQA validation tests to test_real_fixtures.py (6 tests, 235 lines) | Claude |
| 2025-11-24 | Added DQS calculator unit tests (45+ tests, 670 lines) | Claude |
| 2025-11-24 | Added performance benchmark tests (15+ tests, 300+ lines) | Claude |
| 2025-11-24 | Added parametrized tests to DQS calculator and routing engine | Claude |
| 2025-11-24 | Added ResNet model tests - teacher and student (35+ tests, 500+ lines) | Claude |
| 2025-11-24 | Added metadata generator tests (25+ tests, 400+ lines) | Claude |
| 2025-11-24 | Added GCS uploader tests with mocks (20+ tests, 350+ lines) | Claude |
