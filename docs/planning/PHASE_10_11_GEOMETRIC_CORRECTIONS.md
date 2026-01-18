---
schema_type: planning
title: "Project A: Phase 10-11 - Geometric Corrections & Script Awareness"
description: "Comprehensive project plan for Phase 10 (Geometric Corrections, DoclingRouter,
  Schema Expansion) and Phase 11 (Script Awareness & Multilingual Support)"
tags:
  - planning
  - rag_pipeline
  - iqa
  - roadmap
status: draft
owner: core-maintainer
authors:
  - name: "Byron Williams"
  - name: "Claude Code"
purpose: "Document the implementation roadmap for geometric corrections (Phase 10)
  and script awareness (Phase 11), enabling perspective correction, coarse orientation
  detection, DoclingRouter integration, and multilingual document support."
component: "Strategy"
source: "Derived from tmp_cleanup/.tmp-phase10-implementation-plan-20260114.md"
---

**Project**: Project A - Image Preprocessing Detection & Quality Assessment for RAG Applications
**Phases**: 10 (Geometric Corrections) & 11 (Script Awareness)
**Position**: Extension phases building on completed Phases 0-6
**Repository**: `image-preprocessing-detector`

---

## Executive Summary

Phase 10 and Phase 11 extend Project A's preprocessing capabilities to handle geometric distortions and multilingual documents. Phase 10 focuses on **Latin/horizontal-centric** geometric corrections including border removal, coarse orientation detection, perspective correction, and DoclingRouter integration. Phase 11 adds **script awareness** for vertical text languages (Japanese, Mongolian) and rare scripts (Tibetan, Dzongkha).

**Key Innovation**: Gated correction pipeline that applies expensive operations (perspective detection, teacher inference) only when triggered by fast heuristics (table pre-detection, scan detection), maintaining the <150ms latency target.

**User Decisions Incorporated**:

1. ✅ Keep YOLOv10-doc Layout-Lite (leverage existing DocLayNet training)
2. ✅ Use for table detection → gate perspective + set Docling flags
3. ✅ Allow Teacher on CPU (accept >SLA latency in edge cases)
4. ✅ Increase perspective confidence threshold to 0.8 (safer)
5. ✅ Defer script detection to Phase 11 (occasional Japanese/Dzongkha, not core corpus)

---

## Status Dashboard

| Phase | Status | Progress | Est. Duration | Notes |
|-------|--------|----------|---------------|-------|
| **Phase 10A**: Geometric Corrections | ❌ NOT STARTED | 0% | 10 days | Border removal, orientation, perspective |
| **Phase 10B**: DoclingRouter & Schema | ❌ NOT STARTED | 0% | 7 days | Schema expansion, content-aware routing |
| **Phase 10C**: Verification | ❌ NOT STARTED | 0% | 5 days | Audits, line enhancement, contract resolution |
| **Phase 11**: Script Awareness | ❌ DEFERRED | 0% | 6-12 days | Text/visual script detection, multilingual benchmark |

**Total Phase 10**: 22 days (~88 hours of implementation + training)
**Total Phase 11**: 6-12 days (~36 hours of implementation + training)
**Combined Timeline**: 28-34 days

---

## Model Inventory

### Phase 10 Models

| Model | Architecture | Heads | Status | Training Effort | Phase |
|-------|--------------|-------|--------|-----------------|-------|
| **Model 1**: Coarse Orientation CNN | MobileNetV3-Small | 1 (4-class) | ❌ NEW | 2-3 days | 10A |
| **Model 2**: Perspective Detector | HRNet-W18 | 2 (corners + confidence) | ❌ NEW | 3-5 days | 10A |
| **Model 3**: Student ResNet-18 IQA | ResNet-18 | 8 | ✅ TRAINED | - | Existing |
| **Model 4**: Teacher ResNet-50 IQA | ResNet-50 | 8 | ✅ TRAINED | - | Existing |
| **Model 5**: YOLOv10-doc Layout-Lite | YOLOv10 | 1 | ✅ PRETRAINED | - | Existing |

### Phase 11 Models (Deferred)

| Model | Architecture | Heads | Status | Training Effort | Phase |
|-------|--------------|-------|--------|-----------------|-------|
| **Model 6**: Script Detection CNN | MobileNetV3-Small | 1 (10+ scripts) | ❌ FUTURE | 2-3 days | 11 |

**Phase 10 Training**: 2 new models, 5-8 days total
**Total Prediction Heads (Phase 10)**: 20 (1+2+8+8+1)
**Total Prediction Heads (Phase 11)**: 21 (+1 script detection)

---

## System Architecture

### Enhanced Pipeline Flow (Phase 10)

```text
┌────────────────────────────────────────────────────────────┐
│ STAGE 0: PRE-FLIGHT (Document-Level)          <5ms        │
├────────────────────────────────────────────────────────────┤
│ • DPI detection (PyMuPDF metadata)                         │
│ • Page count & file size                                   │
│ • Text extraction (pypdf - first 3 pages)                  │
│ OUTPUT: PreflightMetadata                                  │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ STAGE 1: INGESTION & BORDER REMOVAL            60-110ms   │
├────────────────────────────────────────────────────────────┤
│ • PDF → 300 DPI pages (PyMuPDF)                            │
│ • GATE 1: DPI upscaling (if <300 DPI) ←─────┐ +50ms       │
│ • Border detection & removal (NEW)          │             │
│ • Add 50px white padding (NEW)              │             │
│ OUTPUT: StandardizedPageImage (300 DPI RGB)   │             │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ STAGE 1.5: FAST TABLE PRE-DETECTION (NEW)     5ms         │
├────────────────────────────────────────────────────────────┤
│ • Downsample 1/4                                           │
│ • Hough Line Transform (H/V grid detection)                │
│ • Check: ≥3 H-lines AND ≥3 V-lines                         │
│ OUTPUT: has_potential_tables: bool                         │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ STAGE 2: GEOMETRIC CORRECTION (NEW)           30-60ms     │
├────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────┐   │
│ │ MODEL 1: Coarse Orientation CNN          3ms (always)│   │
│ │ • MobileNetV3-Small                                   │   │
│ │ • 1 head: [0°, 90°, 180°, 270°]                       │   │
│ └──────────────────────────────────────────────────────┘   │
│ • GATE 2: Rotate if confidence >0.9 ────────┐ +5ms         │
│                                              │              │
│ • Fine Deskewing (Hough Transform) ←────────┘ 10ms         │
│   Target: <0.5° residual skew                              │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ MODEL 2: Perspective Detector            15ms (gated)│   │
│ │ • HRNet-W18 corner detection                          │   │
│ │ • 2 heads: corners, confidence                        │   │
│ └──────────────────────────────────────────────────────┘   │
│ • GATE 3: IF (is_scan OR has_potential_tables) ─┐ +23ms    │
│   AND confidence >0.8:                          │           │
│   Apply homography transformation  ←────────────┘           │
│                                                             │
│ OUTPUT: GeometricallyCorrectImage                          │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ STAGE 3: PDF TYPE & TEXT GATE                 8ms         │
├────────────────────────────────────────────────────────────┤
│ • PDF type: image_only/born_digital/hybrid                 │
│ • Text gate heuristics                                     │
│ ROUTE: Branch A (no text) OR Branch B (text)               │
└────────────────────────────────────────────────────────────┘
         ↓                              ↓
    [BRANCH A]                     [BRANCH B]
    No Text Path                   Text Detected Path
         ↓                              ↓
┌─────────────────────────┐  ┌──────────────────────────────┐
│ Classical IQA (full)    │  │ YOLOv10-doc Layout-Lite      │
│ 8 detectors      25ms   │  │ MODEL 5              25ms    │
└─────────────────────────┘  │ • 1 head: 11 DocLayNet classes│
         ↓                   │ • Table detection for routing │
┌─────────────────────────┐  │ • Per-element IQA regions     │
│ Student IQA      10ms   │  └──────────────────────────────┘
│ MODEL 3                 │           ↓
│ • 8 heads               │  ┌──────────────────────────────┐
└─────────────────────────┘  │ Classical IQA (reduced) 15ms │
         ↓                   │ • Illumination, Contrast, Noise│
┌─────────────────────────┐  └──────────────────────────────┘
│ GATE 5: Teacher         │           ↓
│ If uncertainty >0.3     │  ┌──────────────────────────────┐
│ MODEL 4          30ms   │  │ Student IQA          10ms    │
│ • 8 heads               │  │ MODEL 3 (full page)          │
│ • GPU only (or CPU)     │  └──────────────────────────────┘
└─────────────────────────┘           ↓
         ↓                   ┌──────────────────────────────┐
         ↓                   │ GATE 5: Teacher      30ms    │
         ↓                   │ MODEL 4 (if uncertain)       │
         ↓                   └──────────────────────────────┘
         ↓                            ↓
         ↓                   ┌──────────────────────────────┐
         ↓                   │ GATE 6: Line Enhancement     │
         ↓                   │ Table regions only    10ms   │
         ↓                   │ (if faint grid detected)     │
         └───────────────────┴──────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────┐
│ STAGE 5: CORRECTION PIPELINE (Gated)          40ms        │
├────────────────────────────────────────────────────────────┤
│ • CLAHE, Denoise, Sharpen (conditional)                    │
│ • GATE 7: Confidence >0.7 per issue                        │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ STAGE 6: DQS & DOCLING ROUTER (ENHANCED)      5ms         │
├────────────────────────────────────────────────────────────┤
│ • DQS calculation (degradation + complexity)               │
│ • DoclingRouter (formula/code regex detection) (NEW)       │
│ • Generate DoclingConfigHints (NEW)                        │
│ OUTPUT: docling_config_hints: DoclingConfigHints           │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ STAGE 7: OUTPUT SERIALIZATION                 15ms        │
├────────────────────────────────────────────────────────────┤
│ • Validate schema                                          │
│ • Write DocumentMetadata.json                              │
│ • Write corrected images                                   │
│ OUTPUT: → Project B                                        │
└────────────────────────────────────────────────────────────┘
```

---

## Latency Budget (Phase 10)

### Per-Page Latency Breakdown (Latin/Horizontal Assumption)

| Path | Gates Triggered | Latency (ms) | Frequency |
|------|----------------|--------------|-----------|
| **Best Case** | None (clean digital, no tables) | 121 | 60% |
| **Typical** | Table heuristic + perspective | 159 | 30% |
| **Worst Case** | All (scan + tables + teacher + corrections) | 294 | 10% |
| **Weighted Average** | 0.6×121 + 0.3×159 + 0.1×294 | **150ms** ✅ | - |

**Meets Target**: ✅ Yes (exactly at <150ms weighted average)

**95th Percentile**: ~200ms (acceptable, mostly worst-case scans)

---

## Implementation Roadmap

### Phase 10A: Geometric Corrections (Days 1-10) ❌ NOT STARTED

**Priority: HIGH - Core geometric preprocessing**

**Duration**: 10 working days
**Total Sprints**: 15 sprints (~45 hours of implementation + training)

---

#### Sprint 10A.1: Border Removal (Days 1-2, 3 sprints)

**Objective**: Remove black scan margins, add white padding for DocLayNet

- **Sprint 10A.1.1**: Implement border detection algorithm (4 hours)
  - Create `src/correction/border_removal.py`
  - Class: `BorderRemovalCorrector`
  - Algorithm: Grayscale threshold → contour detection → largest contour bounding box
  - Parameters: `border_threshold=30`, `min_border_width=10`, `safety_margin=20`
  - Add unit tests for black border detection
  - Add edge case handling (no border, partial border)

- **Sprint 10A.1.2**: Implement white padding addition (2 hours)
  - Add method: `_add_padding_only()`
  - Use `cv2.copyMakeBorder()` with `BORDER_CONSTANT` white fill
  - Configurable `padding_pixels=50` for DocLayNet margin preservation
  - Return metadata: `border_removed`, `crop_box`, `padding_added`, `border_widths`
  - Add unit tests for padding-only case

- **Sprint 10A.1.3**: Integration and safety validation (3 hours)
  - Integrate `BorderRemovalCorrector` into main pipeline (Stage 1)
  - Safety margin validation: Don't crop within 20px of detected content
  - Test cases: Black borders (all sides), partial borders, no borders
  - Test: Headers/footers preserved (safety margin validation)
  - Add 15 unit tests + 5 integration tests

**Deliverables**:

- `src/correction/border_removal.py` (~150 lines)
- `tests/unit/test_border_removal.py` (~300 lines)
- Integration into `document_processor.py`

---

#### Sprint 10A.2: Coarse Orientation CNN (Days 3-5, 4 sprints)

**Objective**: Detect and correct 0°/90°/180°/270° rotation

- **Sprint 10A.2.1**: Dataset preparation (4 hours)
  - Create `scripts/prepare_orientation_dataset.py`
  - Source: SmartDoc-QA + horizontal subset of OHR-Bench
  - Apply rotations: 0°, 90°, 180°, 270° to each image
  - Target: 50K samples (12.5K per class)
  - Split: 80% train, 10% val, 10% test
  - Save to `data/training/orientation/`
  - Add dataset validation script

- **Sprint 10A.2.2**: Model architecture and training (6 hours + GPU time)
  - Create `src/models/orientation_cnn.py`
  - Architecture: MobileNetV3-Small (pretrained ImageNet)
  - Head: FC layer → 4-way softmax
  - Input: 224×224 RGB (downsampled from full page)
  - Training config:
    - Optimizer: AdamW, lr=1e-3, cosine decay
    - Batch size: 64
    - Epochs: 20-30
    - Augmentation: Brightness, contrast, scaling (NO rotation)
    - Loss: Cross-entropy
    - Early stopping: val_accuracy >98% for 3 epochs
  - Train on Modal A10 GPU (~2 hours)
  - Target: >98% accuracy, per-class >95%

- **Sprint 10A.2.3**: ONNX export and registration (2 hours)
  - Export to ONNX format for production
  - Export TorchScript for Modal backup
  - Save to `models/orientation/mobilenetv3_orientation.onnx`
  - Create model card with metrics
  - Register in local model registry

- **Sprint 10A.2.4**: Detector integration (3 hours)
  - Create `src/detection/orientation_detector.py`
  - Class: `CoarseOrientationDetector`
  - Load ONNX model with ONNXRuntime
  - Method: `predict(image) -> Tuple[int, float]` (angle, confidence)
  - Apply rotation if confidence >0.9 and angle != 0
  - Integrate into geometric correction stage (Stage 2)
  - Add 20 unit tests (4 classes × 5 scenarios)

**Deliverables**:

- `scripts/prepare_orientation_dataset.py` (~100 lines)
- `src/models/orientation_cnn.py` (~200 lines)
- `src/detection/orientation_detector.py` (~150 lines)
- `tests/unit/test_orientation_detector.py` (~400 lines)
- Trained model: `models/orientation/mobilenetv3_orientation.onnx`

---

#### Sprint 10A.3: Fast Table Pre-Detection (Day 6, 2 sprints)

**Objective**: Lightweight heuristic for perspective gating

- **Sprint 10A.3.1**: Implement Hough-based grid detection (3 hours)
  - Create `src/detection/table_predetector.py`
  - Class: `FastTablePreDetector`
  - Algorithm:
    1. Downsample to 1/4 resolution
    2. Canny edge detection
    3. Hough Line Transform (probabilistic)
    4. Classify H/V lines (assume horizontal text for Phase 10)
    5. Check grid: ≥3 H-lines AND ≥3 V-lines
  - Target latency: <5ms
  - Return: `(has_potential_tables: bool, metrics: dict)`
  - Metrics include: `h_line_count`, `v_line_count`, `total_lines`

- **Sprint 10A.3.2**: Integration and threshold tuning (2 hours)
  - Integrate into pipeline after border removal (Stage 1.5)
  - Tune H-line/V-line thresholds on validation set
  - Target: >85% recall (catch most tables for perspective gating)
  - Accept higher false positive rate (perspective correction is safe)
  - Add 10 unit tests (ruled tables, implicit tables, false positives)

**Deliverables**:

- `src/detection/table_predetector.py` (~120 lines)
- `tests/unit/test_table_predetector.py` (~250 lines)

---

#### Sprint 10A.4: Perspective Detector CNN (Days 7-10, 4 sprints)

**Objective**: Detect quadrilateral corners for keystoning correction

- **Sprint 10A.4.1**: Dataset acquisition and augmentation (4 hours)
  - Download DocUNet dataset (~3K document dewarping images)
  - Use existing SmartDoc mobile captures (perspective distortion)
  - Create augmentation script: `scripts/augment_perspective_dataset.py`
  - Apply random homography transforms to flat scans
  - Generate 20K augmented samples
  - Total: 28K samples (DocUNet + SmartDoc + augmented)
  - Save to `data/training/perspective/`

- **Sprint 10A.4.2**: Model architecture and training (8 hours + GPU time)
  - Create `src/models/perspective_cnn.py`
  - Architecture: HRNet-W18 (High-Resolution Net)
  - Input: 512×512 RGB (resized from 300 DPI page)
  - Head 1: Corner Heatmaps
    - 4 channels (top-left, top-right, bottom-left, bottom-right)
    - Output: [4, 128, 128] heatmaps
    - Post-process: Soft-argmax → (x, y) coordinates
  - Head 2: Confidence Score
    - Global average pooling → FC → sigmoid
    - Trained on: Corner visibility + rectangularity score
    - Output: [0-1] confidence
  - Training config:
    - Optimizer: AdamW, lr=1e-3
    - Batch size: 16 (GPU memory constraints)
    - Epochs: 30-40
    - Loss: MSE (heatmaps) + BCE (confidence)
    - Augmentation: Perspective transforms, brightness/contrast, Gaussian noise
  - Validation targets:
    - Corner localization error: <5 pixels at 512×512
    - Confidence precision at 0.8 threshold: >90%
    - False positive rate: <5%

- **Sprint 10A.4.3**: ONNX export and corner extraction (3 hours)
  - Export to ONNX (primary) and TorchScript (Modal backup)
  - Implement soft-argmax corner extraction from heatmaps
  - Implement corner ordering: TL, TR, BR, BL
  - Create homography application function: `apply_homography()`
  - Save to `models/perspective/hrnet_w18_perspective.onnx`

- **Sprint 10A.4.4**: Detector integration and gating (4 hours)
  - Create `src/detection/perspective_detector.py`
  - Class: `PerspectiveDetector`
  - Create `src/correction/perspective_corrector.py`
  - Method: `apply_homography(image, corners) -> np.ndarray`
  - Gating logic:
    - Run perspective detection IF (is_scan OR has_potential_tables)
    - Apply correction IF confidence >0.8 (USER DECISION)
  - Integrate into geometric correction stage (Stage 2)
  - Add 25 unit tests (distortions, confidence thresholds, edge cases)

**Deliverables**:

- `scripts/augment_perspective_dataset.py` (~150 lines)
- `src/models/perspective_cnn.py` (~250 lines)
- `src/detection/perspective_detector.py` (~200 lines)
- `src/correction/perspective_corrector.py` (~100 lines)
- `tests/unit/test_perspective_*.py` (~500 lines total)
- Trained model: `models/perspective/hrnet_w18_perspective.onnx`

---

#### Sprint 10A.5: Combined Gate Integration (Day 10, 2 sprints)

**Objective**: Integrate all geometric gates into main pipeline

- **Sprint 10A.5.1**: Pipeline orchestration update (4 hours)
  - Update `src/pipeline/main_pipeline.py` (or create if not exists)
  - Add geometric correction stage between ingestion and text gate
  - Implement gate sequencing:
    1. Border removal (always)
    2. Table pre-detection (always, fast)
    3. Coarse orientation (always)
    4. Fine deskewing (always)
    5. Perspective detection (gated: is_scan OR has_potential_tables)
    6. Perspective correction (gated: confidence >0.8)
  - Add structured logging for each gate decision
  - Add Prometheus metrics for gate trigger rates

- **Sprint 10A.5.2**: Integration testing and benchmarking (4 hours)
  - Create `tests/integration/test_geometric_pipeline.py`
  - Test cases:
    - Clean digital PDF (no corrections)
    - Rotated scan (orientation correction)
    - Perspective-distorted scan (perspective correction)
    - Table document (perspective gated by table detection)
    - All corrections (rotation + deskew + perspective)
  - Performance benchmarking on SmartDoc-QA subset
  - Verify latency budget: <150ms weighted average
  - Add 30 integration tests

**Deliverables**:

- Updated `src/pipeline/main_pipeline.py` (+200 lines)
- `tests/integration/test_geometric_pipeline.py` (~400 lines)
- Configuration schema updates in `config.py`

---

### Phase 10B: DoclingRouter & Schema (Days 11-17) ❌ NOT STARTED

**Priority: HIGH - Project B integration**

**Duration**: 7 working days
**Total Sprints**: 9 sprints (~32 hours of implementation)

---

#### Sprint 10B.1: Schema Expansion (Days 11-12, 3 sprints)

**Objective**: Add DoclingConfigHints and perspective metadata to schema

- **Sprint 10B.1.1**: DoclingFlags and DoclingConfigHints models (3 hours)
  - Update `src/schema.py`
  - Create `DoclingFlags` model:
    - `do_ocr: bool` - Enable OCR for scanned/image-only PDFs
    - `do_table_structure: bool` - Enable TableFormer
    - `do_formula_understanding: bool` - Enable formula extraction
    - `do_code_extraction: bool` - Enable code block extraction
    - `generate_page_images: bool` (future, Phase 11+)
    - `do_picture_description: bool` (future, Phase 11+)
  - Create `DoclingConfigHints` model:
    - `has_dense_tables: bool` - ≥2 tables OR >30% table area
    - `has_scientific_formulas: bool` - LaTeX/Unicode math detected
    - `has_code_blocks: bool` - Code syntax patterns detected
    - `recommended_ocr_backend: str` - fast|paddleocr|advanced
    - `docling_flags: DoclingFlags`
    - `requires_heavy_processing: bool`
    - `estimated_processing_time: str` - fast|medium|slow
  - Add Pydantic v2 validation
  - Add JSON schema export

- **Sprint 10B.1.2**: PageMetadata geometric correction fields (3 hours)
  - Add to `PageMetadata`:
    - Border removal: `border_removed`, `border_widths`, `padding_added`
    - Orientation: `rotation_applied`, `rotation_confidence`
    - Deskewing: `skew_corrected`, `skew_detection_method`
    - Perspective: `perspective_corrected`, `perspective_confidence`, `perspective_corners`
    - Table pre-detection: `has_potential_tables`, `table_predetect_metrics`
  - Ensure backward compatibility (all new fields optional)
  - Update JSON schema export

- **Sprint 10B.1.3**: DocumentMetadata DoclingConfigHints field (2 hours)
  - Add `docling_config_hints: DoclingConfigHints` to `DocumentMetadata`
  - Deprecate `ocr_routing_recommendation` (keep for backward compatibility)
  - Add migration guide documentation
  - Add 20 schema validation tests
  - Test JSON serialization/deserialization

**Deliverables**:

- Updated `src/schema.py` (+150 lines)
- `tests/unit/test_schema_docling.py` (~300 lines)
- `docs/reference/docling_migration_guide.md`

---

#### Sprint 10B.2: DoclingRouter Implementation (Days 13-15, 4 sprints)

**Objective**: Formalize content-aware routing logic

- **Sprint 10B.2.1**: Table detection from layout-lite (3 hours)
  - Create `src/routing/docling_router.py`
  - Class: `DoclingRouter`
  - Implement table detection from YOLOv10-doc elements:
    - Count Table class elements
    - Calculate table area percentage
    - `has_dense_tables = (table_count >= 2) OR (table_area_pct > 0.3)`
  - Fallback to `has_potential_tables` heuristic flag
  - Add unit tests

- **Sprint 10B.2.2**: Formula and code detection (3 hours)
  - Implement regex-based formula detection on extracted text:
    - LaTeX delimiters: `[\$\\]`
    - Equation environments: `\\begin\{equation\}`
    - Math symbols: `∫|∑|∏|√`
    - Math keywords: `theorem|lemma|proof|corollary`
  - Implement code block detection:
    - Markdown code blocks: `` ``` ``
    - Language keywords: `def |class |function |import |return`
    - Syntax characters: `=>|->|\{|\}`
  - Check Layout-Lite for Formula class detection
  - Add unit tests for each pattern

- **Sprint 10B.2.3**: OCR backend recommendation logic (3 hours)
  - Implement recommendation logic:
    - IF `pdf_type == born_digital` → "fast"
    - ELIF `dqs_score < 0.5` (high quality scan) → "paddleocr"
    - ELSE → "advanced" (multi-engine fusion)
  - Implement Docling flag mapping:
    - `do_ocr = (pdf_type == image_only)`
    - `do_table_structure = has_dense_tables`
    - `do_formula_understanding = has_scientific_formulas`
    - `do_code_extraction = has_code_blocks`
  - Implement processing complexity estimation:
    - "fast": born-digital without tables (~2-3 sec/page)
    - "medium": standard documents (~5-8 sec/page)
    - "slow": table-heavy or degraded (~10-20 sec/page)

- **Sprint 10B.2.4**: DoclingRouter integration (3 hours)
  - Method: `generate_hints(page_metadata, extracted_text, layout_elements) -> DoclingConfigHints`
  - Integrate into DQS & Routing stage (Stage 6)
  - Populate `docling_config_hints` in DocumentMetadata
  - Add 35 unit tests covering all detection scenarios
  - Add logging for routing decisions

**Deliverables**:

- `src/routing/docling_router.py` (~250 lines)
- `tests/unit/test_docling_router.py` (~600 lines)
- Configuration schema in `config.py`

---

#### Sprint 10B.3: Integration Testing (Days 16-17, 2 sprints)

**Objective**: End-to-end validation with all components

- **Sprint 10B.3.1**: E2E integration test suite (4 hours)
  - Create `tests/integration/test_phase10_e2e.py`
  - Test scenarios:
    - `test_born_digital_contract_no_tables()`: Clean digital → minimal processing
    - `test_scanned_financial_report()`: Dense tables → perspective + TableFormer
    - `test_scientific_paper_born_digital()`: Formulas + code → formula extraction
    - `test_hybrid_pdf_with_embedded_scan()`: Mixed content routing
    - `test_rotated_scan_with_tables()`: Orientation + perspective chain
  - Validate all DoclingConfigHints fields populated correctly
  - Validate geometric correction metadata populated

- **Sprint 10B.3.2**: Performance validation (3 hours)
  - Create `scripts/benchmark_phase10.py`
  - Test latency budget compliance:
    - Best case (clean digital): <150ms
    - Typical (digital with table): <200ms
    - Worst case (scan + tables + corrections): <350ms
    - Weighted average: <180ms
  - Generate performance report
  - Add CI performance regression gate

**Deliverables**:

- `tests/integration/test_phase10_e2e.py` (~800 lines)
- `scripts/benchmark_phase10.py` (~300 lines)
- Performance report in `docs/reports/phase10_performance.md`

---

### Phase 10C: Verification (Days 18-22) ❌ NOT STARTED

**Priority: MEDIUM - Quality assurance**

**Duration**: 5 working days
**Total Sprints**: 6 sprints (~22 hours of implementation)

---

#### Sprint 10C.1: Margin Preservation Audit (Day 18, 1 sprint)

**Objective**: Verify ingestion doesn't crop content aggressively

- **Sprint 10C.1.1**: Margin preservation validation (4 hours)
  - Create `validation/audit_margin_preservation.py`
  - Test cases:
    - `multi_column_layout.pdf` - Wide margins needed
    - `page_header_footer.pdf` - Don't crop headers/footers
    - `margin_notes.pdf` - Preserve annotation space
  - Check for >10% area reduction (indicates aggressive cropping)
  - Verify 50px padding added by BorderRemovalCorrector
  - Action items:
    - If cropping detected → update ingestion to preserve margins
    - If no cropping → verify padding is correctly applied

**Deliverables**:

- `validation/audit_margin_preservation.py` (~150 lines)
- Audit report in `docs/reports/margin_audit.md`

---

#### Sprint 10C.2: Denoising Filter Review (Day 19, 1 sprint)

**Objective**: Verify NLM denoising is adequate for document images

- **Sprint 10C.2.1**: Denoising filter validation (3 hours)
  - Verify existing NLM denoising (`cv2.fastNlMeansDenoisingColored`) is edge-preserving
  - Check for median filter for salt-and-pepper noise
  - Test on noisy document samples from OHR-Bench
  - Action items:
    - ✅ If NLM exists and is edge-preserving → no action
    - ⚠️ If missing median filter → add `cv2.medianBlur` for speckle noise
    - ⚠️ If using simple Gaussian blur → replace with bilateral filter
  - Document findings and recommendations

**Deliverables**:

- Denoising review report in `docs/reports/denoising_review.md`
- Updates to correction pipeline if needed

---

#### Sprint 10C.3: Layout-Lite Contract Resolution (Day 20, 1 sprint)

**Objective**: Resolve PROJECT_PLAN.md inconsistency per GPT-5.2 finding

- **Sprint 10C.3.1**: Contract clarification and documentation (3 hours)
  - Current inconsistency:
    - Lines 110-115: "YOLOv10-doc... Detect WHERE elements are"
    - Lines 463-466: "`elements` removed/deferred → Project B"
    - Lines 1129-1178: "Heuristics-Based... detect_tables/figures"
  - Resolution per USER DECISION: Keep YOLOv10-doc for:
    1. ✅ Table detection → set `docling_flags.do_table_structure`
    2. ✅ Gate perspective correction (tables present)
    3. ✅ Per-element IQA (assess quality of figures, tables, formulas)
    4. ✅ Structural complexity scoring
  - NOT exported to Project B:
    - ❌ Bounding boxes (Project B runs its own DocLayNet)
    - ❌ Reading order (Project B responsibility)
    - ❌ Element linking (Project B responsibility)
  - Update PROJECT_PLAN.md with clarified contract
  - Update schema.py with `exclude=True` for internal fields

**Deliverables**:

- Updated PROJECT_PLAN.md (layout-lite section)
- Updated schema.py (internal field exclusion)

---

#### Sprint 10C.4: Line Enhancement (Days 21-22, 3 sprints)

**Objective**: Morphological closing for faint table grids

- **Sprint 10C.4.1**: Faint grid detection (3 hours)
  - Create `src/correction/line_enhancer.py`
  - Class: `TableLineEnhancer`
  - Implement grid line count detection: Canny + Hough
  - Threshold: `faint_threshold=10` (min lines to consider "faint")
  - Add unit tests for faint vs clear grids

- **Sprint 10C.4.2**: Morphological enhancement (3 hours)
  - Implement morphological closing for H/V lines:
    - H kernel: `cv2.getStructuringElement(MORPH_RECT, (50, 1))`
    - V kernel: `cv2.getStructuringElement(MORPH_RECT, (1, 50))`
    - Apply `cv2.morphologyEx(gray, MORPH_CLOSE, kernel)`
  - Blend enhanced grid with original: 0.7 original + 0.3 enhanced
  - Only apply to detected table regions (from YOLOv10-doc)
  - Add validation: don't harm text legibility

- **Sprint 10C.4.3**: Integration and testing (3 hours)
  - Integrate into text branch processing (after YOLOv10-doc)
  - Only enhance Table class elements
  - Add metadata: `element.attributes["line_enhanced"] = True`
  - Add 15 unit tests (faint grids, clear grids, broken lines, no lines)
  - Validate text not degraded by enhancement

**Deliverables**:

- `src/correction/line_enhancer.py` (~180 lines)
- `tests/unit/test_line_enhancer.py` (~300 lines)

---

### Phase 10 Success Criteria

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Orientation Detection Accuracy | >98% | SmartDoc-QA test set |
| Perspective Detection Precision | >90% at 0.8 confidence | DocUNet + SmartDoc test |
| Table Heuristic Recall | >85% | Annotated table documents |
| Border Removal Safety | 100% (no header/footer crop) | Manual audit |
| Latency (Weighted Average) | <150ms | Performance benchmark |
| Schema Validation | 100% pass | Integration tests |
| DoclingRouter Accuracy | >95% flag correctness | E2E test suite |
| Test Coverage | >80% for new modules | pytest-cov |

---

### Phase 10 Deliverables Summary

| Category | Deliverables |
|----------|--------------|
| **New Models** | Coarse Orientation CNN (MobileNetV3-Small), Perspective Detector (HRNet-W18) |
| **Detection Modules** | `orientation_detector.py`, `table_predetector.py`, `perspective_detector.py` |
| **Correction Modules** | `border_removal.py`, `perspective_corrector.py`, `line_enhancer.py` |
| **Routing Modules** | `docling_router.py` |
| **Schema Updates** | `DoclingFlags`, `DoclingConfigHints`, geometric correction metadata |
| **Tests** | 150+ new tests (unit + integration) |
| **Documentation** | Phase 10 report, migration guide, performance benchmarks |

---

## Phase 11: Script Awareness (Days 23-34) ❌ DEFERRED

**Priority: MEDIUM - Multilingual support**

**Status**: Deferred per user decision for efficiency

**Duration**: 6-12 working days (depending on visual CNN inclusion)
**Total Sprints**: 10-16 sprints (~36-48 hours of implementation + training)

**Why Deferred**:

1. ✅ SmartDoc-QA benchmarking works without it (English-only)
2. ✅ Occasional Japanese/Dzongkha docs acceptable with temporary limitations
3. ✅ Allows faster Phase 10 delivery (22 days vs 28-31 days)
4. ✅ Can validate core geometric fixes first, then add script layer
5. ✅ Script awareness is additive layer (doesn't change Phase 10 work)

---

### Sprint 11.1: Text-Based Script Detection (Days 23-24, 3 sprints)

**Objective**: Unicode range analysis and text direction detection

- **Sprint 11.1.1**: Unicode script classifier (4 hours)
  - Create `src/detection/script_detector.py`
  - Class: `ScriptDetector`
  - Implement Unicode range analysis:
    - Latin: U+0000-U+024F
    - CJK: U+4E00-U+9FFF (Chinese, Japanese, Korean)
    - Japanese Hiragana/Katakana: U+3040-U+30FF
    - Arabic: U+0600-U+06FF
    - Cyrillic: U+0400-U+04FF
    - Devanagari: U+0900-U+097F
    - Tibetan: U+0F00-U+0FFF
  - Return dominant script and script distribution
  - Add unit tests for each script range

- **Sprint 11.1.2**: Text direction detection (3 hours)
  - Implement text direction detection:
    - Horizontal LTR: Latin, CJK (modern), Cyrillic, Devanagari
    - Horizontal RTL: Arabic, Hebrew
    - Vertical: Japanese (traditional), Mongolian
  - Use Unicode Bidi algorithm hints
  - Return: `text_direction: "horizontal_ltr" | "horizontal_rtl" | "vertical"`
  - Add unit tests

- **Sprint 11.1.3**: Schema updates and integration (2 hours)
  - Create `ScriptMetadata` model:
    - `dominant_script: str`
    - `script_distribution: dict[str, float]`
    - `text_direction: str`
    - `is_vertical: bool`
  - Add to `PageMetadata`
  - Integrate into pipeline after text extraction
  - Add unit tests

**Deliverables**:

- `src/detection/script_detector.py` (~200 lines)
- `tests/unit/test_script_detector.py` (~400 lines)
- Schema updates for script metadata

---

### Sprint 11.2: Geometric Correction Adaptation (Days 25-26, 3 sprints)

**Objective**: Script-aware angle interpretation and deskewing

- **Sprint 11.2.1**: Script-aware orientation interpretation (3 hours)
  - Modify `CoarseOrientationDetector` to consider script:
    - For vertical text (Japanese traditional): 90°/270° may be correct orientation
    - For RTL text: Adjust baseline expectations
  - Add script context to rotation decision
  - Add unit tests for vertical text orientation

- **Sprint 11.2.2**: Text direction-aware deskewing (3 hours)
  - Modify Hough deskewing for vertical text:
    - Detect vertical text lines instead of horizontal
    - Adjust angle calculation for vertical baseline
  - Add configuration: `skew_detection_mode: "horizontal" | "vertical" | "auto"`
  - Add unit tests for vertical deskewing

- **Sprint 11.2.3**: Table heuristic adjustment (2 hours)
  - Modify `FastTablePreDetector` for vertical text:
    - Swap H-line/V-line interpretation for vertical documents
    - Adjust grid detection thresholds
  - Add script-aware gating logic
  - Add unit tests

**Deliverables**:

- Updated `orientation_detector.py`
- Updated `table_predetector.py`
- Updated Hough deskewing logic
- Unit tests for script-aware corrections

---

### Sprint 11.3: Visual Script CNN (Days 27-29, 4 sprints) - OPTIONAL

**Objective**: MobileNetV3 script classifier for visual-only detection

**Note**: Only implement if corpus analysis shows significant need (>5% non-Latin documents)

- **Sprint 11.3.1**: Dataset acquisition (4 hours)
  - Download MLT dataset (Multi-Lingual Text)
  - Collect script-specific document samples
  - Target: 10 script classes, 5K samples per class
  - Split: 80% train, 10% val, 10% test

- **Sprint 11.3.2**: Model architecture and training (6 hours + GPU time)
  - Architecture: MobileNetV3-Small
  - Input: 224×224 RGB (document thumbnail)
  - Head: FC → 10-way softmax (or more scripts)
  - Training config similar to orientation CNN
  - Target: >90% accuracy on script classification

- **Sprint 11.3.3**: ONNX export and integration (2 hours)
  - Export to ONNX for production
  - Integrate as fallback when text extraction fails
  - Add to script detection pipeline

- **Sprint 11.3.4**: Ensemble text + visual detection (2 hours)
  - Combine text-based and visual script detection
  - Use text-based as primary (more accurate when text available)
  - Fall back to visual for image-only documents
  - Add confidence-weighted ensemble

**Deliverables**:

- `src/models/script_cnn.py` (~200 lines)
- Trained model: `models/script/mobilenetv3_script.onnx`
- Updated `script_detector.py` with visual fallback

---

### Sprint 11.4: Multilingual Benchmarking (Days 30-32, 3 sprints)

**Objective**: Validate on multilingual datasets

- **Sprint 11.4.1**: OHR-Bench evaluation (4 hours)
  - Run full pipeline on OHR-Bench (includes Japanese vertical text)
  - Measure:
    - Script detection accuracy
    - Orientation detection accuracy (vertical documents)
    - Deskewing accuracy (vertical baselines)
  - Generate evaluation report

- **Sprint 11.4.2**: OmniDocBench evaluation (4 hours)
  - Run full pipeline on OmniDocBench (20+ scripts)
  - Measure script detection across all 20+ scripts
  - Identify scripts with <80% detection accuracy
  - Document per-script performance

- **Sprint 11.4.3**: Performance validation and reporting (3 hours)
  - Measure latency impact of script detection
  - Verify latency budget maintained (<150ms weighted)
  - Create Phase 11 completion report
  - Document known limitations and future improvements

**Deliverables**:

- `scripts/benchmark_multilingual.py` (~300 lines)
- Evaluation reports in `docs/reports/`
- Phase 11 completion report

---

### Phase 11 Success Criteria

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Script Detection Accuracy (Latin) | >99% | OmniDocBench subset |
| Script Detection Accuracy (CJK) | >95% | OHR-Bench + OmniDocBench |
| Script Detection Accuracy (Rare) | >85% | OmniDocBench (Tibetan, etc.) |
| Vertical Text Orientation | >95% | OHR-Bench Japanese subset |
| Vertical Deskewing Accuracy | >90% | Custom vertical text test set |
| Latency Impact | <5ms overhead | Performance benchmark |
| Test Coverage | >80% for new modules | pytest-cov |

---

### Phase 11 Deliverables Summary

| Category | Deliverables |
|----------|--------------|
| **New Models** | Script Detection CNN (optional) |
| **Detection Modules** | `script_detector.py` |
| **Schema Updates** | `ScriptMetadata` model |
| **Corrections** | Script-aware orientation, deskewing, table detection |
| **Tests** | 50+ new tests |
| **Benchmarks** | OHR-Bench, OmniDocBench evaluations |

---

## Appendix A: MobileCLIP-2 Cascade Distillation Analysis

**Recommendation**: For Phase 11 script detection, consider **S4 → S0 Cascade Distillation** instead of direct S0 fine-tuning.

### Rationale

| Approach | Orientation Accuracy | Script Accuracy (Tibetan) | Training Cost | Timeline |
|----------|---------------------|---------------------------|---------------|----------|
| Direct S0 | 95-96% | 70-75% | ~$15 | 6 days |
| S4→S0 Cascade | **98-99%** | **80-85%** | ~$105 | 10 days |

**Key Insight**: S4 matches SigLIP-SO400M accuracy (81.9% ImageNet) and provides richer representations for rare scripts. Cascade distillation preserves this capacity in the S0 deployment model.

**ROI**: +$300/year savings from reduced reprocessing (3% fewer orientation errors) vs +$90 training investment.

---

## Appendix B: Complete Timeline Summary

| Phase | Duration | Sprints | Hours | Status |
|-------|----------|---------|-------|--------|
| **10A**: Geometric Corrections | 10 days | 15 | ~45h | ❌ NOT STARTED |
| **10B**: DoclingRouter & Schema | 7 days | 9 | ~32h | ❌ NOT STARTED |
| **10C**: Verification | 5 days | 6 | ~22h | ❌ NOT STARTED |
| **Phase 10 Total** | **22 days** | **30** | **~99h** | ❌ NOT STARTED |
| **11.1-11.2**: Text-Based Script | 4 days | 6 | ~17h | ❌ DEFERRED |
| **11.3**: Visual Script CNN | 3 days | 4 | ~14h | ❌ OPTIONAL |
| **11.4**: Multilingual Benchmark | 3 days | 3 | ~11h | ❌ DEFERRED |
| **Phase 11 Total** | **6-10 days** | **9-13** | **~28-42h** | ❌ DEFERRED |
| **Combined Total** | **28-32 days** | **39-43** | **~127-141h** | - |

---

## Next Steps

1. **Confirm Phase 10 scope** (Latin-centric, defer script to Phase 11)
2. **Begin Sprint 10A.1** (Border removal implementation)
3. **Parallel work**: Start dataset preparation for Coarse Orientation CNN
4. **Create tracking**: Phase 10 sprint board with 30 sprints
5. **Update PROJECT_PLAN.md** with Phase 10/11 references

---

*This planning document extends the main PROJECT_PLAN.md. For overall project context and Phases 0-9, see [PROJECT_PLAN.md](PROJECT_PLAN.md).*
