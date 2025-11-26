---
schema_type: common
title: "Project A Implementation Plan"
description: "Detailed implementation roadmap for Project A preprocessing and IQA system"
tags: [planning, roadmap, development, project_management]
status: published
owner: "docs-team"
purpose: "Provide phase-by-phase implementation plan for Project A preprocessing and IQA system."
---

## 1. Overview

Project A serves as the entry point for all documents into the RAG pipeline. It ingests documents, assesses quality, applies corrections, and generates routing metadata for Project B (OCR Orchestration).

## 2. Scope

### **In Scope**

* Document ingestion and rendering:
  * PDF extraction (image_only, born_digital, hybrid classification)
  * Image loading with DPI detection and upscaling
  * Standardization to 300 DPI

* Teacher–student ML IQA pipeline:
  * ResNet-50 teacher training
  * Knowledge distillation to ResNet-18 student
  * Selective teacher inference (uncertainty, discrepancy, risk-based)

* Classical IQA detection:
  * Blur, noise, skew, contrast, lighting, compression artifacts
  * Binarization quality, bleed-through detection

* Image corrections:
  * Deskew, denoise, contrast enhancement, sharpening
  * Rotation/orientation, bleed-through suppression

* Layout-lite detection:
  * DocLayout-YOLO (11 DocLayNet classes)
  * Handwriting classifier
  * Structural complexity scoring

* Device-priority execution:
  1. Local GPU
  2. Local CPU
  3. Modal GPU

* DQS calculation and OCR routing recommendations

### **Out of Scope (Project B Responsibility)**

* Full semantic layout detection (reading order, table structure)
* OCR text extraction
* Multi-engine fusion

### **Deferred to Post-Benchmarking**

* Office document support (.docx, .xlsx, .pptx)
* Per-element (Hybrid) IQA on cropped regions
* Dewarping correction (page curvature)

## 3. Architecture

```text
                   ╔════════════════════════════════════════╗
                   ║           TRAINING PHASE               ║
                   ╠════════════════════════════════════════╣
Raw Datasets (OHR-Bench, synthetic)
   ↓
[ResNet-50 Teacher Training] (Phase 2)
   ↓
Teacher Weights (gs://image_detection_b/models/phase2_iqa/)
   ↓
[Knowledge Distillation → ResNet-18] (Phase 2)
   ↓
Student Model (default inference)
Teacher Model (selective inference)


                   ╔════════════════════════════════════════╗
                   ║           RUNTIME PHASE                ║
                   ╠════════════════════════════════════════╣
Incoming Document (PDF/Image)
   ↓
[Preflight Analysis] (DPI detection, upscaling)
   ↓
[PDF Type Classification] (image_only/born_digital/hybrid)
   ↓
[Text Gate] (< 10ms heuristic routing)
   ↓
[Classical IQA Pass] (Phase 4)
   ├── Blur (Laplacian)
   ├── Noise (wavelet)
   ├── Skew (Hough)
   ├── Contrast (histogram)
   ├── Lighting metrics
   ├── JPEG blockiness
   ├── Binarization quality
   └── Bleed-through detection
   ↓
[ML IQA Pass → ResNet-18 Student]
       ↓
[Uncertainty Gate]
   ├── Low uncertainty & no conflicts → accept student output
   ├── High-risk doc → escalate to teacher
   ├── Softmax entropy high → escalate to teacher
   └── Classical vs student discrepancy → escalate to teacher
       ↓
[Teacher Pass (ResNet-50)] - device priority logic
       ↓
IQA Metrics Merged
       ↓
[Corrections] (Phase 5)
   ├── Deskew
   ├── Denoise
   ├── Contrast enhancement (CLAHE)
   ├── Sharpening
   ├── Rotation/orientation
   └── Bleed-through suppression
       ↓
[Layout-Lite Detection] (Phase 6)
   ├── DocLayout-YOLO (11 classes)
   ├── Handwriting classifier
   └── Complexity scorer
       ↓
[DQS + Routing] (Phase 8)
       ↓
Output Package → Project B
   ├── DocumentMetadata.json
   └── Corrected page images
```text

## 4. Non-Functional Requirements

### **Performance**

| Metric | Target | Notes |
|--------|--------|-------|
| Student inference (CPU) | ≤40 ms/page | Production default |
| Student inference (GPU) | ≤10 ms/page | Local GPU preferred |
| Teacher inference (GPU) | ≤30 ms/page | Flagged pages only |
| Text Gate | < 10 ms/page | Fast routing decision |
| Full pipeline (GPU) | < 150 ms/page | End-to-end with corrections |
| Full pipeline (CPU) | < 500 ms/page | CPU-only mode |

### **Cost Optimization**

* Modal GPU usage must be optional and bounded
* Teacher fallback is disabled by default in high-volume batch mode
* Student-only mode for cost-sensitive deployments

### **Stability**

* If teacher unavailable (no GPU locally or remote budget exceeded), pipeline MUST continue using student-only outputs
* Corrections include guardrails to prevent quality degradation
* All transforms tracked in audit trail

---

## PHASE 0 — Project Setup (Week 0–1) ✅ COMPLETE

### Infrastructure (COMPLETE ✅)

0.1 ✅ Project skeleton (poetry, pre-commit, CI/CD)
0.2 ✅ Modal workspace + credentials (gcs-credentials secret)
0.3 ✅ GPU/CPU device probing utilities
0.4 ✅ Configuration system (YAML) including:

* teacher_fallback_enabled
* uncertainty thresholds
* discrepancy thresholds
* max_pages_for_teacher
0.5 ✅ Logging/telemetry scaffolding (structlog + rich)

---

## PHASE 2 — ResNet Teacher & Student Training (Week 2–4) ✅ COMPLETE

### Infrastructure (COMPLETE ✅)

2.0a ✅ Three-tier storage architecture (NFS + local symlinks + GCS backup)
2.0b ✅ Dataset management scripts (create_symlinks.py, organize_dual_storage.py)
2.0c ✅ 100K dataset generation pipeline with 13-dimensional distribution tracking
2.0d ✅ Modal training infrastructure with GCS integration

### Teacher Training (COMPLETE ✅)

2.1 ✅ Multi-head model architecture (ResNet-50, 5 IQA heads: blur, noise, lighting, contrast, compression)
2.2 ✅ Loss functions for classification + regression (MultiHeadIQALoss)
2.3 ✅ Heavy augmentations for robustness (100K synthetic dataset)
2.4 ✅ Training loops for Modal GPU (T4/A10)
2.5 ✅ Best checkpoint: epoch 20, val_loss=0.2694
2.6 ✅ Export teacher to ONNX (gs://image_detection_b/models/phase2_iqa/resnet50_teacher_50epoch.onnx, 105MB)
2.7 ✅ Teacher training summary documented (models/iqa/onnx/training_summary_50epoch.json)

### Student Distillation (COMPLETE ✅)

2.8 ✅ ResNet-18 student architecture (12.5M params, 2.47x smaller than teacher)
2.9 ✅ DistillationLoss (KL divergence + BCE, T=4.0, α=0.7)
2.10 ✅ StudentTrainer with frozen teacher soft targets
2.11 ✅ Student training on Modal T4 GPU (30 epochs, val_loss=0.138)
2.12 ✅ Student training summary documented (models/iqa/onnx/training_summary_student.json)

### Pending Items

2.13 ⬜ Export student to ONNX + TorchScript
2.14 ⬜ Student vs teacher performance comparison (formal benchmark)
2.15 ⬜ Register models in local registry (GCS complete)

---

## PHASE 3 — Manual Validation & Dataset Preparation (Week 4–5) ✅ COMPLETE

### Validation Infrastructure (COMPLETE ✅)

3.1 ✅ Streamlit-based manual validation UI (tools/manual_validation_ui.py)

* Image preview with quality metric visualization
* Interactive checkbox interface for 6 quality issues
* Progress tracking and auto-advance
* Keyboard shortcuts for navigation

3.2 ✅ Ambiguous case sampling (scripts/sample_ambiguous_cases.py)

* Uncertainty scoring based on weak supervision confidence
* Edge case detection (borderline quality metrics)
* Composite priority ranking (0.7 *uncertainty + 0.3* edge_case)

3.3 ✅ Annotation guide and session planning (data/ANNOTATION_GUIDE.md)

* Quality issue definitions with examples
* Session planning (4 hours × 2 sessions, 2000 images)

### Dataset Creation (COMPLETE ✅)

3.4 ✅ PyTorch Dataset class (data/dataset.py)

* Multi-label binary classification
* Support for albumentations and torchvision transforms
* Train/val/test split support

3.5 ✅ Dataset merging script (scripts/create_final_dataset.py)

* Merges weak supervision + manual corrections
* Manual corrections take precedence
* Dataset integrity verification

3.6 ✅ Weak supervision pipeline (data/weak_supervision.py)

* BRISQUE/NIQE quality scoring
* Confidence-weighted label generation

---

## PHASE 4 — Classical IQA Enhancement (Week 6–7)

Extends the existing classical IQA detectors with additional quality metrics.

### Existing Detectors (COMPLETE ✅)

4.1 ✅ Blur detection (Laplacian variance) — `detection/iqa_classical.py:BlurDetector`
4.2 ✅ Skew detection (Hough + projection ensemble) — `detection/iqa_classical.py:SkewDetector`
4.3 ✅ Contrast detection (histogram analysis) — `detection/iqa_classical.py:ContrastDetector`

### New Detectors (COMPLETE ✅)

4.4 ✅ Noise detection (wavelet-based estimator) — `detection/iqa_classical.py:NoiseDetector`

* Estimate noise level using wavelet decomposition
* Detect salt-and-pepper noise patterns
* Output: noise_score (0-1), noise_type (gaussian/salt_pepper/speckle)
* Performance: < 3ms per page (target: < 5ms)

4.5 ✅ Lighting/illumination metrics — `detection/iqa_classical.py:IlluminationDetector`

* Detect uneven illumination across page regions
* Identify shadows, hotspots, vignetting
* Output: illumination_score (0-1), IlluminationType enum
* Performance: < 4ms per page (target: < 10ms)

4.6 ✅ JPEG blockiness/compression artifacts — `detection/iqa_classical.py:JPEGBlockinessDetector`

* Detect 8x8 DCT block boundaries
* Estimate compression quality factor
* Output: compression_score (0-1), estimated_quality (1-100)
* Performance: < 3ms per page (target: < 5ms)

4.7 ✅ Binarization quality detection — `detection/iqa_classical.py:BinarizationQualityDetector`

* Assess how well document would binarize
* Detect problematic regions (low contrast, noise)
* Output: binarization_score (0-1), problem_regions (list of ProblemRegion)
* Performance: < 6ms per page (target: < 10ms)

4.8 ✅ Bleed-through detection — `detection/iqa_classical.py:BleedThroughDetector`

* Detect text/images showing through from verso side
* Estimate bleed-through severity
* Output: bleed_through_detected (bool), severity (0-1), affected_regions (list)
* Performance: < 8ms per page (target: < 15ms)

### Calibration (COMPLETE ✅)

4.9 ✅ Student vs classical discrepancy threshold tuning — `detection/discrepancy.py`

* DiscrepancyThresholds: Per-head configurable thresholds
* ClassicalScoreAdapter: Converts detector outputs to normalized scores
* DiscrepancyAnalyzer: Comprehensive escalation rules
* Threshold rationale documented in module docstring

4.10 ✅ DQS weight calibration for new detectors — `metrics/dqs_calculator.py`

* DQSWeightConfig: Configurable weights (blur: 0.25, noise: 0.20, etc.)
* ExtendedIQAScores: Unified score container for all 7 detectors
* calculate_extended_degradation_score: Weighted DQS calculation
* Weight rationale documented in DQSWeightConfig docstring

### Deliverables

* [x] 5 new detector classes in `detection/iqa_classical.py`
* [x] Unit tests with >90% coverage for new detectors
* [ ] Integration tests with real document samples (deferred to Phase 10)
* [x] Updated DQS calculator with new metric weights
* [x] Performance benchmark (all detectors < 50ms total) — Achieved: < 25ms total

---

## PHASE 5 — Corrections Enhancement (Week 7–8)

Extends the existing corrections module with additional transforms.

### Existing Corrections (COMPLETE ✅)

5.1 ✅ Deskew correction — `correction/corrections.py:DeskewCorrector`

* Rotation with confidence-based guardrails
* Skip if angle < 0.5° or > 45°, confidence < 0.3

5.2 ✅ Contrast enhancement (CLAHE) — `correction/corrections.py:ContrastEnhancer`

* Adaptive histogram equalization in LAB color space
* Clip limit: 2.0, tile grid: 8×8

5.3 ✅ Sharpening — `correction/corrections.py:Sharpener`

* Unsharp mask with severity-based adjustment

### New Corrections (PLANNED ⬜)

5.4 ⬜ Denoise correction

* Algorithm: OpenCV `fastNlMeansDenoising` / `fastNlMeansDenoisingColored`
* Guardrails:
  * Skip if noise_score > 0.8 (already clean)
  * Skip if blur_score < 0.3 (would worsen blur)
  * Verify sharpness not degraded after correction
* Parameters: h=10 (filter strength), templateWindowSize=7, searchWindowSize=21
* Target: < 50ms per page

5.5 ⬜ Rotation/orientation correction

* Detect and correct 90°/180°/270° rotations
* Use text orientation detection (EAST or Tesseract OSD)
* Guardrails:
  * Confidence threshold for rotation detection
  * Skip if confidence < 0.7
* Target: < 20ms per page (detection), < 5ms (rotation)

5.6 ⬜ Bleed-through suppression

* Prerequisite: Phase 4.8 bleed-through detection
* Algorithm: Adaptive thresholding + morphological operations
* Guardrails:
  * Only apply if bleed_through_detected = True
  * Verify text clarity not degraded
  * Rollback if OCR confidence drops
* Target: < 30ms per page

### Guardrail Framework (PLANNED ⬜)

5.7 ⬜ Quality re-verification after corrections

* Re-run IQA on corrected image
* Compare before/after quality scores
* Automatic rollback if quality degraded
* Log all rollback decisions with rationale

5.8 ⬜ Transform history enhancement

* Record before/after quality metrics
* Track rollback events
* Export correction effectiveness statistics

### Deliverables

* [ ] 3 new corrector classes in `correction/corrections.py`
* [ ] Quality re-verification framework
* [ ] Unit tests with before/after quality validation
* [ ] Integration tests with edge cases (already clean, severely degraded)
* [ ] Performance benchmark (all corrections < 100ms total)

---

## PHASE 6 — Layout-Lite Detection (Week 8–9)

Implements coarse layout detection for routing decisions.

### Existing Detectors (COMPLETE ✅)

6.1 ✅ Column detection — `detection/layout_lite/column_detector.py`
6.2 ✅ Table detection — `detection/layout_lite/table_detector.py`
6.3 ✅ Figure detection — `detection/layout_lite/figure_detector.py`
6.4 ✅ Fuzzy scan detection — `detection/layout_lite/fuzzy_scan_detector.py`
6.5 ✅ Watermark detection — `detection/layout_lite/watermark_detector.py`
6.6 ✅ Colorful background detection — `detection/layout_lite/background_detector.py`
6.7 ✅ Complexity scorer — `metrics/dqs_calculator.py:calculate_structural_complexity_score`

### DocLayout-YOLO Integration (PLANNED ⬜)

6.8 ⬜ DocLayout-YOLO model training

* Architecture: YOLOv10-based, document-optimized
* Classes (11 DocLayNet): Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title
* Dataset: DocLayNet + PubLayNet combined
* Training: Modal GPU (A10), ~8 hours
* Config: `configs/models/doclayout_yolo.yaml`

6.9 ⬜ DocLayout-YOLO inference integration

* ONNX export for production inference
* Batch inference support
* Output: List of detected elements with COCO bounding boxes
* Target: < 30ms per page (GPU), < 100ms per page (CPU)

6.10 ⬜ Element-level metadata extraction

* Populate `DocumentElement` schema with detected elements
* Calculate element coverage statistics
* Generate page layout summary

### Handwriting Detection (PLANNED ⬜)

6.11 ⬜ Handwriting classifier

* Binary classifier: handwriting present (yes/no)
* Architecture: Lightweight CNN or use YOLO detection
* Training data: IAM Handwriting + synthetic
* Output: has_handwriting (bool), confidence (0-1), regions (list)
* Target: < 15ms per page

6.12 ⬜ Dense math/formula detection

* Detect pages with significant mathematical content
* Use Formula class from DocLayout-YOLO
* Output: has_dense_math (bool), formula_coverage (0-1)

### Structural Features API (PLANNED ⬜)

6.13 ⬜ Unified layout analysis API

* Combine all detectors into single `analyze_layout()` function
* Return `PageLayoutSummary` with all attributes
* Cache results for multi-pass access

6.14 ⬜ Layout complexity scoring update

* Incorporate DocLayout-YOLO element counts
* Weight by element type complexity
* Calibrate against OCR difficulty

### Deliverables

* [ ] Trained DocLayout-YOLO model (ONNX, < 50MB)
* [ ] Handwriting classifier model
* [ ] Integrated layout analysis API
* [ ] Unit tests for each detector
* [ ] Performance benchmark (full layout < 50ms GPU, < 150ms CPU)
* [ ] Documentation with example outputs

---

## PHASE 8 — DQS & Routing (Week 9–10)

Calibrates quality scoring and routing logic.

### Existing Implementation (COMPLETE ✅)

8.1 ✅ DQS calculation — `metrics/dqs_calculator.py`

* Degradation score (weighted IQA metrics)
* Structural complexity score (layout-based)

8.2 ✅ Pre-OCR risk calculation — `metrics/dqs_calculator.py:calculate_pre_ocr_risk`

8.3 ✅ Routing recommendation engine — `routing/recommendation_engine.py`

* 4 strategies: ocr_fast, ocr_advanced, vision_simple, vision_structured
* Decision tree with rationale strings

### Calibration & Tuning (PLANNED ⬜)

8.4 ⬜ DQS weight optimization

* Collect OCR accuracy data on test set
* Correlate DQS components with OCR error rates
* Optimize weights via grid search or Bayesian optimization
* Document final weight selection rationale

8.5 ⬜ Routing threshold calibration

* Define routing accuracy metric
* Test routing decisions against OCR outcomes
* Adjust thresholds for optimal routing accuracy
* Target: >90% routing accuracy

8.6 ⬜ Teacher escalation threshold tuning

* Analyze teacher vs student agreement rates
* Identify optimal uncertainty thresholds
* Balance teacher usage (cost) vs accuracy gain
* Target: <10% teacher escalation rate with <2% accuracy loss

### Integration (PLANNED ⬜)

8.7 ⬜ End-to-end pipeline integration

* Wire all phases into unified CLI workflow
* Ensure proper data flow between modules
* Handle edge cases (empty pages, corrupt files)

8.8 ⬜ JSON schema finalization

* Verify all new fields populated correctly
* Validate against schema definition
* Add schema version tracking

8.9 ⬜ Output package for Project B

* DocumentMetadata.json with all routing metadata
* Corrected images in standardized format
* Handoff documentation for Project B team

### Deliverables

* [ ] Calibrated DQS weights with documentation
* [ ] Validated routing thresholds
* [ ] End-to-end pipeline integration
* [ ] Project B handoff package specification
* [ ] Integration tests covering full workflow

---

## PHASE 10 — Validation & Benchmarking (Week 10–11)

Comprehensive testing and documentation.

### Benchmarking (PLANNED ⬜)

10.1 ⬜ Full pipeline benchmark

* Test on diverse document corpus (>1000 documents)
* Measure end-to-end latency (GPU and CPU modes)
* Profile memory usage and throughput
* Identify bottlenecks

10.2 ⬜ Teacher vs student performance comparison

* Compare IQA accuracy on held-out test set
* Measure latency difference
* Document when teacher adds value
* Cost-benefit analysis

10.3 ⬜ Classical vs ML IQA comparison

* Compare detection accuracy for each issue type
* Identify complementary strengths
* Validate discrepancy-based escalation logic

10.4 ⬜ Correction effectiveness analysis

* Measure quality improvement per correction type
* Track rollback rates
* Identify problematic document types

10.5 ⬜ Routing accuracy validation

* Compare routing recommendations to optimal OCR outcomes
* Calculate routing accuracy per document type
* Identify misrouting patterns

### Stress Testing (PLANNED ⬜)

10.6 ⬜ Large batch processing

* Process 10,000+ documents in batch mode
* Monitor resource usage over time
* Test recovery from failures
* Validate output consistency

10.7 ⬜ Edge case testing

* Corrupt/malformed files
* Extremely large documents (>100 pages)
* Unusual formats and resolutions
* Multi-language documents

### Documentation (PLANNED ⬜)

10.8 ⬜ Update architecture diagrams (PlantUML)
10.9 ⬜ API reference documentation
10.10 ⬜ Performance tuning guide
10.11 ⬜ Troubleshooting guide
10.12 ⬜ Project B handoff documentation

### Deliverables

* [ ] Benchmark report with latency/throughput metrics
* [ ] Teacher vs student comparison report
* [ ] Correction effectiveness report
* [ ] Routing accuracy report
* [ ] Updated documentation suite
* [ ] Release notes for v1.0

---

## POST-BENCHMARKING — Future Enhancements (Phase 12+)

Features deferred until after initial benchmarking validates core pipeline.

### Office Document Support (DEFERRED)

12.1 ⬜ Office document ingestion (.docx, .xlsx, .pptx)

* Extract embedded images for IQA processing
* Library: python-docx, openpyxl, python-pptx
* Separate processing path from PDF/image

### Per-Element IQA (DEFERRED)

12.2 ⬜ Hybrid IQA on cropped regions

* Run IQA on individual tables, figures, formulas
* Populate `quality_issues` field in `DocumentElement`
* Enable targeted corrections per element

### Advanced Corrections (DEFERRED)

12.3 ⬜ Dewarping correction

* Correct page curvature from book scans
* Algorithm: Contour detection + perspective transform
* Complex implementation, only needed for book scans

### Evaluation Criteria for Inclusion

Each deferred feature will be evaluated based on:

* Benchmark results showing need
* User feedback and feature requests
* Implementation complexity vs benefit
* Impact on pipeline latency

---

## 5. Summary of Teacher Policy

**Default inference:**

* **ResNet-18 student only**

**Teacher runs only if:**

* Document is high-risk (based on PDF type, complexity)
* Student output has high entropy (> 0.8 threshold)
* Student contradicts classical IQA (discrepancy > configured threshold)
* Config explicitly forces teacher pass
* GPU available locally or via Modal

**Teacher must NOT run:**

* If no GPU exists (local or Modal)
* During high-volume batch runs unless explicitly enabled
* If page budget exceeded (max_pages_for_teacher config)

---

## 6. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| DocLayout-YOLO training fails | High | Fall back to existing CV-based detectors |
| Teacher model too slow | Medium | Tune escalation thresholds, reduce teacher usage |
| Corrections degrade quality | Medium | Guardrail framework with automatic rollback |
| Routing accuracy insufficient | High | Conservative fallback to ocr_advanced |
| Modal costs exceed budget | Medium | Disable teacher fallback, use CPU-only mode |

---

## 7. Timeline Summary

| Phase | Duration | Status | Key Deliverables |
|-------|----------|--------|------------------|
| Phase 0 | Week 0-1 | ✅ Complete | Project setup, infrastructure |
| Phase 2 | Week 2-4 | ✅ Complete | Teacher & student models trained |
| Phase 3 | Week 4-5 | ✅ Complete | Manual validation UI, dataset |
| Phase 4 | Week 6-7 | ⬜ Planned | Classical IQA enhancement (5 new detectors) |
| Phase 5 | Week 7-8 | ⬜ Planned | Corrections enhancement (3 new correctors) |
| Phase 6 | Week 8-9 | ⬜ Planned | Layout-lite (DocLayout-YOLO, handwriting) |
| Phase 8 | Week 9-10 | ⬜ Planned | DQS calibration, routing tuning |
| Phase 10 | Week 10-11 | ⬜ Planned | Benchmarking, documentation |

**Total Timeline**: ~11 weeks to benchmarking

---
