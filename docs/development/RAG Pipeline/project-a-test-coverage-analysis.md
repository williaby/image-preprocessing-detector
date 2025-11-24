# Project A - Test Coverage Analysis

**Purpose:** Map functional requirements to tests and identify coverage gaps.

**Generated:** 2025-11-23

---

## Primary Workflow Test Coverage Summary

| Workflow Step | Test Files | Test Count | Coverage Status |
|---------------|------------|------------|-----------------|
| Input/Ingestion | test_pdf_loader.py, test_image_loader.py | 33 | ✅ Covered |
| DPI Detection/Upscaling | test_pdf_resolution.py, test_pdf_upscaler.py | 30 | ✅ Covered |
| PDF Classification | test_pdf_type_classifier.py, test_pdf_image_detector.py | 28 | ✅ Covered |
| Text Gate | test_text_gate.py | 15 | ✅ Covered |
| Classical IQA | test_iqa_classical.py, test_blur_detector.py | 72 | ✅ Covered |
| ML IQA | test_iqa_ml.py | 15 | ⚠️ Partial (models not deployed) |
| Layout-Lite | - | 0 | ❌ Not Implemented (Phase 6) |
| Corrections | test_corrections.py | 38 | ✅ Covered |
| DQS Calculation | test_dqs_calculator.py | 33 | ✅ Covered |
| JSON Output | test_json_generator.py, test_schema.py | 37 | ✅ Covered |
| **E2E Pipeline** | test_pipeline_e2e.py, test_real_fixtures.py | 25 | ✅ Covered |

---

## Functional Requirements Coverage

### FR-1: General System & File Handling

| Requirement | Description | Tests | Status |
|-------------|-------------|-------|--------|
| **FR-1.1** | File Input (path/bytes) | test_pdf_loader.py, test_image_loader.py | ✅ |
| **FR-1.2** | Supported File Formats | test_pdf_loader.py, test_image_loader.py | ✅ |
| **FR-1.3** | JSON Output Schema | test_schema.py (25 tests), test_json_generator.py (12 tests), test_pipeline_e2e.py::TestHandoffValidation | ✅ |
| **FR-1.4** | Error Handling | test_pdf_loader.py::test_error_handling, test_image_loader.py::test_invalid_* | ✅ |
| **FR-1.5** | CLI Interface | test_cli.py | ⚠️ Partial |

### FR-2: File Format Analysis

| Requirement | Description | Tests | Status |
|-------------|-------------|-------|--------|
| **FR-2.1** | PDF Type Classification | test_pdf_type_classifier.py (14), test_pdf_image_detector.py (8), test_pdf_text_extractor.py (6) | ✅ |
| **FR-2.3** | Learned Quality Assessment (ML IQA) | test_iqa_ml.py (15), test_resnet_teacher.py (SKIPPED), test_loss_functions.py (SKIPPED) | ⚠️ Partial |
| **FR-2.4** | Text Detection Gate | test_text_gate.py (15 tests covering all detection methods) | ✅ |

### FR-3: Image Quality Detection & Correction

| Requirement | Description | Tests | Status |
|-------------|-------------|-------|--------|
| **FR-3.1** | Blur Detection | test_iqa_classical.py::TestBlurDetection, test_blur_detector.py (20) | ✅ |
| **FR-3.2** | Skew Detection/Correction | test_iqa_classical.py::TestSkewDetection, test_corrections.py::test_deskew_* | ✅ |
| **FR-3.3** | Noise Detection | test_iqa_classical.py::TestNoiseDetection (wavelet estimator) | ✅ |
| **FR-3.4** | Image Resolution | test_pdf_resolution.py, test_image_loader.py | ✅ |
| **FR-3.5** | DPI Detection | test_pdf_resolution.py (12 tests) | ✅ |
| **FR-3.6** | DPI Upscaling | test_pdf_upscaler.py (18 tests), test_pdf_upscaling_integration.py | ✅ |
| **FR-3.7** | Contrast Assessment | test_iqa_classical.py::TestContrastDetection | ✅ |
| **FR-3.8** | Do-No-Harm Guardrails | test_corrections.py::test_guardrail_* (multiple tests) | ✅ |
| **FR-3.9** | Binarization Quality | - | ❌ Not Implemented |
| **FR-3.10** | Illumination Uniformity | - | ❌ Not Implemented |
| **FR-3.11** | Bleed-Through Detection | - | ❌ Phase 3 |
| **FR-3.12** | Warping/Curvature | - | ❌ Phase 3 |
| **FR-3.13** | Perspective Distortion | - | ❌ Phase 2 |
| **FR-3.14** | Hybrid IQA on Embedded Images | - | ❌ Phase 3 |

### FR-4: Layout Analysis

| Requirement | Description | Tests | Status |
|-------------|-------------|-------|--------|
| **FR-4.1** | Layout Detection Model | test_phase2_complete.py (SKIPPED) | ❌ Phase 3 |
| **FR-4.2** | Layout Element Detection | - | ❌ Phase 3 |
| **FR-4.3** | COCO Bounding Box Format | test_schema.py::test_bounding_box_* | ✅ |
| **FR-4.4** | Parasitic Content | - | ❌ Phase 3 |
| **FR-4.5** | Footnote Detection | - | ❌ Phase 3 |
| **FR-4.6** | Figure-Caption Detection | - | ❌ Phase 2 |
| **FR-4.7** | Vertical Text Orientation | - | ❌ Phase 3 |
| **FR-4.8** | Handwriting Detection | - | ❌ Phase 2+ |

### FR-6: Correction Methods

| Requirement | Description | Tests | Status |
|-------------|-------------|-------|--------|
| **FR-6.1** | Blur Correction | test_corrections.py::test_sharpening_* | ✅ |
| **FR-6.2** | Skew Correction | test_corrections.py::test_deskew_* | ✅ |
| **FR-6.3** | Noise Reduction | test_corrections.py::test_denoise_* | ✅ |
| **FR-6.4** | Contrast Enhancement | test_corrections.py::test_clahe_* | ✅ |
| **FR-6.5** | DPI Upscaling | test_pdf_upscaler.py | ✅ |
| **FR-6.6** | Binarization Correction | - | ❌ Phase 2 |
| **FR-6.7** | Illumination Normalization | - | ❌ Phase 2 |
| **FR-6.8** | Dewarping | - | ❌ Phase 3 |
| **FR-6.9** | Perspective Correction | - | ❌ Phase 2 |
| **FR-6.10** | Bleed-Through Suppression | - | ❌ Phase 3 |

### FR-7: Document Quality Score (DQS)

| Requirement | Description | Tests | Status |
|-------------|-------------|-------|--------|
| **FR-7.1** | DQS Calculation | test_dqs_calculator.py (33 tests covering degradation, complexity, weights) | ✅ |
| **FR-7.2** | Pipeline Routing | test_dqs_calculator.py::test_pre_ocr_risk_*, test_pipeline_e2e.py::test_routing_strategies | ✅ |

---

## End-to-End Test Coverage

### test_pipeline_e2e.py (11 tests)

| Test | Requirements Covered |
|------|---------------------|
| test_clean_document_pipeline | FR-1.1, FR-3.1, FR-3.3, FR-3.7, FR-7.1 |
| test_blurry_document_pipeline | FR-3.1, FR-6.1, FR-7.1 |
| test_noisy_document_pipeline | FR-3.3, FR-6.3, FR-7.1 |
| test_multi_issue_document_pipeline | FR-3.1, FR-3.2, FR-3.3, FR-7.1 |
| test_multi_page_document_pipeline | FR-1.1, FR-7.1 |
| test_handoff_json_format | FR-1.3, FR-7.2 |
| test_routing_strategies | FR-7.2 |
| test_custom_config | NFR-3.1 |
| test_schema_validation | FR-1.3 |
| test_project_b_required_fields | FR-1.3 (handoff spec) |
| test_page_layout_consistency | FR-1.3 |

### test_real_fixtures.py (14 tests)

| Test | Requirements Covered |
|------|---------------------|
| test_simple_text_pdf | FR-1.1, FR-1.2, FR-2.1, FR-3.*, FR-7.1 |
| test_tables_figures_pdf | FR-1.1, FR-2.1, FR-7.1 |
| test_multi_column_pdf | FR-1.1, FR-7.1 |
| test_skewed_pdf | FR-3.2, FR-6.2 |
| test_low_contrast_pdf | FR-3.7, FR-6.4 |
| test_all_doclaynet_pdfs | FR-1.1, FR-1.2, FR-7.1 |
| test_simple_table_image | FR-3.* |
| test_complex_table_image | FR-3.* |
| test_rotated_table_image | FR-3.2 |
| test_low_quality_table_image | FR-3.1, FR-3.3 |
| test_embedded_graphics_table_image | FR-3.* |
| test_all_tablebank_images | FR-3.* |
| test_handoff_json_from_real_pdf | FR-1.3 |
| test_handoff_consistency_across_fixtures | FR-1.3 |

---

## Coverage Gaps & Recommendations

### Critical Gaps (Phase 1-2 Requirements Not Tested)

1. **FR-3.9 Binarization Quality Assessment**
   - Status: Not implemented
   - Recommendation: Add to Phase 2 scope
   - Suggested test: `test_binarization_quality.py`

2. **FR-3.10 Illumination Uniformity Detection**
   - Status: Not implemented
   - Recommendation: Add to Phase 2 scope
   - Suggested test: `test_illumination_detector.py`

3. **FR-2.3 ML IQA (Teacher/Student Models)**
   - Status: Partially tested, models not deployed
   - Gap: Integration tests skip due to missing PyTorch
   - Recommendation: Add CI with GPU runner or mock models for unit tests

### Phase 3+ Requirements (Expected Gaps)

These requirements are expected to be not implemented yet:
- FR-3.11 Bleed-Through Detection
- FR-3.12 Warping/Curvature Detection
- FR-4.1-4.8 Layout Analysis
- FR-6.6-6.10 Advanced Corrections

### Test Infrastructure Recommendations

1. **Add fixture-based assertion tests**
   - The manifest.json files include "criterion" field (e.g., "skewed", "low_contrast")
   - Tests should assert that expected issues are detected

2. **Add annotation-based validation** (future)
   - DocLayNet has COCO annotations
   - Could validate layout detection against ground truth

3. **Add performance benchmarks**
   - NFR-1.2 specifies <150ms/page (GPU), <400ms/page (CPU)
   - Add timing assertions to E2E tests

---

## Test Count Summary

| Category | Test Count | Status |
|----------|------------|--------|
| Unit Tests | ~550 | ✅ |
| Integration Tests | ~30 | ✅ |
| E2E Tests | 25 | ✅ |
| Skipped (PyTorch) | ~20 | ⚠️ |
| **Total** | ~625 | 85.19% coverage |

---

## Mapping: Workflow Step → Tests → Requirements

```
INPUT STAGE
├── test_pdf_loader.py → FR-1.1, FR-1.2
├── test_image_loader.py → FR-1.1, FR-1.2
└── test_real_fixtures.py → FR-1.1, FR-1.2

INGESTION STAGE
├── test_pdf_resolution.py → FR-3.5
├── test_pdf_upscaler.py → FR-3.6
└── test_pdf_analyzer.py → FR-3.4, FR-3.5, FR-3.6

PDF CLASSIFICATION
├── test_pdf_type_classifier.py → FR-2.1
├── test_pdf_image_detector.py → FR-2.1
└── test_pdf_text_extractor.py → FR-2.1

TEXT GATE
└── test_text_gate.py → FR-2.4

IQA DETECTION
├── test_iqa_classical.py → FR-3.1, FR-3.2, FR-3.3, FR-3.7
├── test_blur_detector.py → FR-3.1
├── test_iqa_ml.py → FR-2.3
└── test_image_metrics.py → FR-3.1, FR-3.3

CORRECTIONS
└── test_corrections.py → FR-6.1, FR-6.2, FR-6.3, FR-6.4, FR-3.8

DQS CALCULATION
└── test_dqs_calculator.py → FR-7.1, FR-7.2

OUTPUT
├── test_json_generator.py → FR-1.3
├── test_schema.py → FR-1.3
└── test_pipeline_e2e.py::TestHandoffValidation → FR-1.3

E2E COVERAGE
├── test_pipeline_e2e.py → Full pipeline (FR-1 through FR-7)
└── test_real_fixtures.py → Full pipeline with real data
```

---

**Last Updated:** 2025-11-23
