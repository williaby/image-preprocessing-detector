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

## PHASE 9 — Specialized Element Training for Project B (Week 10–12)

Trains and exports specialized models that Project B will consume for element-specific processing. Project A centralizes all ML training infrastructure (Modal GPU, datasets, model registry) while Project B focuses on orchestration and inference.

### Rationale

With DocLayout-YOLO providing accurate bounding boxes, Project B can route detected elements to specialized processors. However, effective routing requires additional classifiers trained on domain-specific data. Project A trains these models and exports them for Project B consumption.

### 9.1 DocLayout-YOLO Extended Classes (HIGH PRIORITY)

Extend the standard DocLayNet 11 classes with additional element types needed for specialist routing.

#### 9.1.1 ⬜ Custom Class Training

**Base Model:** `juliozhao/DocLayout-YOLO-DocStructBench` (recommended) or `juliozhao/DocLayout-YOLO-D4LA-Docsynth300K_pretrained`

**Extended Classes (17 total):**

| Class | Source | Purpose |
|-------|--------|---------|
| Caption | DocLayNet | Standard |
| Footnote | DocLayNet | Standard |
| Formula | DocLayNet | Standard (split into subtypes below) |
| List-Item | DocLayNet | Standard |
| Page-Footer | DocLayNet | Parasitic content |
| Page-Header | DocLayNet | Parasitic content |
| Picture | DocLayNet | Standard |
| Section-Header | DocLayNet | Standard |
| Table | DocLayNet | Standard |
| Text | DocLayNet | Standard |
| Title | DocLayNet | Standard |
| **Handwriting** | New | Route to TrOCR |
| **Watermark** | New | Flag as parasitic |
| **Stamp** | New | Flag as parasitic |
| **Signature** | New | May need special handling |
| **Code-Block** | New | Preserve formatting |
| **Chart** | New | May need chart-to-data extraction |

**Training Dataset:**

| Source | Classes Covered | Annotation Status |
|--------|-----------------|-------------------|
| DocLayNet | 11 standard classes | Pre-annotated |
| IAM Handwriting Database | Handwriting regions | Needs bbox conversion |
| SignaTR6K | Signatures | Pre-annotated |
| Custom annotation | Watermarks, stamps, code | Manual annotation required |
| GitHub code screenshots | Code-Block | Synthetic generation |

**Training Configuration:**

```yaml
# configs/models/doclayout_yolo_extended.yaml
model:
  base: juliozhao/DocLayout-YOLO-DocStructBench
  architecture: YOLOv10
  image_size: 1600

training:
  epochs: 100
  batch_size: 16
  gpu: Modal A10 (24GB)
  optimizer: AdamW
  lr: 0.001
  warmup_epochs: 5

classes:
  # DocLayNet standard (11)
  - caption
  - footnote
  - formula
  - list_item
  - page_footer
  - page_header
  - picture
  - section_header
  - table
  - text
  - title
  # Extended (6 new)
  - handwriting
  - watermark
  - stamp
  - signature
  - code_block
  - chart

augmentation:
  - random_rotate: [-5, 5]
  - random_brightness: [0.8, 1.2]
  - random_noise: gaussian
  - jpeg_compression: [60, 100]
```

**Export:**

* ONNX format for production inference
* Target size: < 100MB
* Target latency: < 50ms/page (GPU), < 200ms/page (CPU)

#### 9.1.2 ⬜ Annotation Pipeline for Custom Classes

* Streamlit-based annotation UI (extend Phase 3 tooling)
* Target: 2,000 annotated samples per custom class
* Source: Internal document corpus + public datasets

---

### 9.2 Handwriting vs Printed Classifier (HIGH PRIORITY)

Binary classifier to determine if detected text regions contain handwriting.

#### 9.2.1 ⬜ Model Training

**Architecture:** ResNet-18 (lightweight, fast inference)

**Base Model:** `torchvision.models.resnet18(pretrained=True)`

**Training Dataset:**

| Dataset | Type | Samples | Source |
|---------|------|---------|--------|
| IAM Handwriting Database | Handwritten | ~13,000 lines | Public |
| IMGUR5K | Printed | ~5,000 images | Public |
| CVL Database | Handwritten | ~7,000 pages | Public |
| DocLayNet text crops | Printed | ~50,000 crops | Derived |
| Synthetic printed | Printed | ~20,000 | Generated |

**Training Configuration:**

```yaml
# configs/models/handwriting_classifier.yaml
model:
  architecture: resnet18
  pretrained: true
  num_classes: 2  # [printed, handwritten]
  dropout: 0.3

training:
  epochs: 30
  batch_size: 64
  gpu: Modal T4 (16GB)
  optimizer: AdamW
  lr: 0.0001
  scheduler: CosineAnnealingLR

input:
  size: [224, 224]
  normalize: imagenet

augmentation:
  - random_rotation: [-10, 10]
  - random_affine: true
  - color_jitter: [0.1, 0.1, 0.1]
  - gaussian_blur: [0.1]
```

**Output Schema:**

```json
{
  "is_handwritten": true,
  "confidence": 0.92,
  "model_version": "handwriting_clf_v1.0"
}
```

**Export:**

* ONNX format: `models/handwriting_classifier/resnet18_handwriting.onnx`
* Target size: < 50MB
* Target latency: < 5ms/crop (GPU), < 20ms/crop (CPU)

---

### 9.3 Table Type Classifier (MEDIUM PRIORITY)

Multi-class classifier to identify table structure patterns for specialist routing.

#### 9.3.1 ⬜ Model Training

**Architecture:** ResNet-18 or EfficientNet-B0

**Base Model:** `torchvision.models.resnet18(pretrained=True)`

**Classes:**

| Class | Description | Specialist Routing |
|-------|-------------|-------------------|
| `simple_grid` | Regular rows/columns | Docling TableFormer |
| `merged_header` | Header spans columns | StructEqTable |
| `nested_rows` | Hierarchical structure | StructEqTable + VLM |
| `financial` | Numbers with totals | TableFormer + calculation validation |
| `form_like` | Key-value pairs | Docling standard |
| `scientific` | LaTeX-style | StructEqTable |

**Training Dataset:**

| Dataset | Samples | Classes Covered |
|---------|---------|-----------------|
| PubTables-1M | ~950,000 | Scientific, simple_grid |
| FinTabNet | ~113,000 | Financial |
| TableBank | ~417,000 | Mixed |
| ICDAR 2019 | ~2,000 | Complex tables |
| Custom forms | ~5,000 | Form-like (annotate) |

**Training Configuration:**

```yaml
# configs/models/table_type_classifier.yaml
model:
  architecture: resnet18
  pretrained: true
  num_classes: 6

training:
  epochs: 50
  batch_size: 32
  gpu: Modal T4
  class_weights: balanced  # Handle imbalanced classes

input:
  size: [384, 384]  # Larger for table structure
```

**Output Schema:**

```json
{
  "table_type": "financial",
  "confidence": 0.85,
  "structural_features": {
    "has_merged_cells": true,
    "appears_numeric": true,
    "estimated_rows": 12,
    "estimated_cols": 5
  },
  "recommended_specialist": "structeqtable",
  "validate_calculations": true
}
```

**Export:**

* ONNX format: `models/table_type_classifier/table_classifier.onnx`
* Target size: < 50MB
* Target latency: < 10ms/table (GPU)

---

### 9.4 Formula Complexity Classifier (MEDIUM PRIORITY)

Classify mathematical formulas for appropriate specialist routing.

#### 9.4.1 ⬜ Model Training

**Architecture:** ResNet-18

**Classes:**

| Class | Description | Specialist Routing |
|-------|-------------|-------------------|
| `simple_inline` | Single-line, basic operators | Granite-Docling |
| `block_equation` | Display-style equation | Texify |
| `multi_line` | Multi-line derivation | Texify + VLM validation |
| `matrix` | Matrix notation | UniMERNet |
| `handwritten_math` | Handwritten formulas | UniMERNet |

**Training Dataset:**

| Dataset | Samples | Source |
|---------|---------|--------|
| im2latex-100k | ~100,000 | arXiv formulas |
| UniMER-1M | ~1,000,000 | Diverse formulas |
| CROHME | ~10,000 | Handwritten math |
| Custom inline | ~10,000 | Synthetic from LaTeX |

**Training Configuration:**

```yaml
# configs/models/formula_complexity_classifier.yaml
model:
  architecture: resnet18
  pretrained: true
  num_classes: 5

training:
  epochs: 40
  batch_size: 64
  gpu: Modal T4
```

**Export:**

* ONNX format: `models/formula_classifier/formula_complexity.onnx`
* Target size: < 50MB

---

### 9.5 Parasitic Content Detector (MEDIUM PRIORITY)

Detect watermarks, stamps, and background elements that should be excluded from RAG chunks.

#### 9.5.1 ⬜ Watermark Detection Enhancement

**Approach:** Extend DocLayout-YOLO OR train separate lightweight detector

**Detection Targets:**

| Type | Examples | Action |
|------|----------|--------|
| Text watermark | "DRAFT", "CONFIDENTIAL" | Skip OCR |
| Logo watermark | Company logos in background | Skip OCR |
| Stamp | Approval stamps, date stamps | Extract metadata only |
| Background pattern | Decorative backgrounds | Ignore |

**Training Dataset:**

| Source | Samples | Annotation |
|--------|---------|------------|
| Custom watermarked docs | ~5,000 | Manual annotation |
| Synthetic watermarks | ~20,000 | Generated overlay |
| Stamp datasets | ~3,000 | Public + custom |

**Output Schema:**

```json
{
  "parasitic_elements": [
    {
      "type": "text_watermark",
      "bbox": [100, 100, 400, 400],
      "confidence": 0.82,
      "is_parasitic": true,
      "ocr_action": "skip"
    }
  ]
}
```

---

### 9.6 Element Complexity Scorer (LOWER PRIORITY)

Unified model to predict whether any element needs specialist processing.

#### 9.6.1 ⬜ Multi-Task Model

**Architecture:** ResNet-18 with multi-head output

**Input:** Cropped element image + element_type embedding

**Outputs:**

* `complexity_level`: simple | moderate | complex
* `specialist_needed`: bool
* `recommended_specialist`: string (optional)
* `vlm_validation_recommended`: bool

**Training:** After 9.2, 9.3, 9.4 are complete, train unified model on combined dataset.

---

### 9.7 Domain-Specific TrOCR Fine-Tuning (OPTIONAL - DEFERRED)

Fine-tune TrOCR on domain-specific handwriting if off-the-shelf models underperform.

#### 9.7.1 ⬜ Evaluation Phase

* Run standard TrOCR on sample handwriting from target domain
* Measure CER/WER on held-out test set
* If CER > 10%, proceed with fine-tuning

#### 9.7.2 ⬜ Fine-Tuning (if needed)

**Base Model:** `microsoft/trocr-base-handwritten`

**Training Data:** Annotated handwriting samples from target domain (500+ samples minimum)

**Training Configuration:**

```yaml
# configs/models/trocr_domain_finetuned.yaml
model:
  base: microsoft/trocr-base-handwritten

training:
  epochs: 10
  batch_size: 8
  gpu: Modal A10
  lr: 5e-5

export:
  path: models/trocr_domain_finetuned/
```

---

### 9.8 Model Registry & Export (HIGH PRIORITY)

Establish model registry for Project B consumption.

#### 9.8.1 ⬜ Registry Structure

Each model includes both **full** and **light** variants for flexible deployment:

```text
models/
├── doclayout_yolo_extended/
│   ├── full/
│   │   ├── yolov10_17class.onnx           # ~100MB, 1600px input
│   │   ├── config.yaml
│   │   └── training_summary.json
│   ├── light/
│   │   ├── yolov10n_17class.onnx          # ~20MB, 1024px input
│   │   ├── config.yaml
│   │   └── training_summary.json
│   ├── class_mapping.json                  # Shared between variants
│   └── benchmarks.json                     # CPU/GPU/Modal L4 comparison
├── handwriting_classifier/
│   ├── full/
│   │   ├── resnet18_handwriting.onnx      # ~47MB
│   │   └── training_summary.json
│   ├── light/
│   │   ├── mobilenetv3_handwriting.onnx   # ~10MB
│   │   └── training_summary.json
│   ├── config.json                         # Shared config
│   └── benchmarks.json
├── table_type_classifier/
│   ├── full/
│   │   └── resnet18_table.onnx            # ~47MB
│   ├── light/
│   │   └── mobilenetv3_table.onnx         # ~10MB
│   └── benchmarks.json
├── formula_complexity_classifier/
│   ├── full/
│   │   └── resnet18_formula.onnx
│   ├── light/
│   │   └── mobilenetv3_formula.onnx
│   └── benchmarks.json
├── parasitic_detector/
│   ├── full/
│   │   └── resnet18_parasitic.onnx
│   ├── light/
│   │   └── mobilenetv3_parasitic.onnx
│   └── benchmarks.json
└── registry.json  # Master index of all models + variants
```

#### 9.8.2 ⬜ Registry Manifest

```json
{
  "registry_version": "2.0.0",
  "default_variant": "light",
  "models": {
    "doclayout_yolo_extended": {
      "classes": 17,
      "class_mapping": "doclayout_yolo_extended/class_mapping.json",
      "variants": {
        "full": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "doclayout_yolo_extended/full/yolov10_17class.onnx",
          "architecture": "yolov10",
          "input_size": [1600, 1600],
          "size_mb": 100,
          "recommended_device": "modal_l4"
        },
        "light": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "doclayout_yolo_extended/light/yolov10n_17class.onnx",
          "architecture": "yolov10n",
          "input_size": [1024, 1024],
          "size_mb": 20,
          "recommended_device": "cpu"
        }
      },
      "benchmarks": "doclayout_yolo_extended/benchmarks.json"
    },
    "handwriting_classifier": {
      "classes": 2,
      "variants": {
        "full": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "handwriting_classifier/full/resnet18_handwriting.onnx",
          "architecture": "resnet18",
          "input_size": [224, 224],
          "size_mb": 47,
          "recommended_device": "modal_l4"
        },
        "light": {
          "version": "1.0.0",
          "format": "onnx",
          "path": "handwriting_classifier/light/mobilenetv3_handwriting.onnx",
          "architecture": "mobilenetv3_small",
          "input_size": [224, 224],
          "size_mb": 10,
          "recommended_device": "cpu"
        }
      },
      "benchmarks": "handwriting_classifier/benchmarks.json"
    }
  }
}
```

#### 9.8.3 ⬜ GCS Sync

* Upload trained models to `gs://image_detection_b/models/phase9/`
* Version tagging for rollback capability
* Checksum verification

---

### 9.9 Light Model Variants for Local Benchmarking (HIGH PRIORITY)

Train lightweight versions of each Phase 9 model for local CPU inference and benchmarking. Based on Phase 4 benchmarks, local GPUs (RTX A500, P2000) provide minimal benefit for small models—CPU is often faster due to transfer overhead elimination.

#### 9.9.1 ⬜ Model Variant Strategy

Each Phase 9 model ships in two variants:

| Model | Full Version | Light Version | Use Case |
|-------|-------------|---------------|----------|
| DocLayout-YOLO | YOLOv10 (17 classes) | YOLOv10-nano | CPU inference, edge deployment |
| Handwriting Classifier | ResNet-18 | MobileNetV3-small | CPU inference, high-throughput |
| Table Type Classifier | ResNet-18 | MobileNetV3-small | CPU inference |
| Formula Complexity | ResNet-18 | MobileNetV3-small | CPU inference |
| Parasitic Detector | ResNet-18 | MobileNetV3-small | CPU inference |
| Element Complexity | ResNet-18 multi-head | MobileNetV3-small multi-head | CPU inference |

#### 9.9.2 ⬜ Light Model Specifications

**DocLayout-YOLO-Nano:**

```yaml
# configs/models/doclayout_yolo_nano.yaml
model:
  base: yolov10n  # Nano variant
  image_size: 1024  # Reduced from 1600
  classes: 17

training:
  epochs: 100
  batch_size: 32
  gpu: Modal T4

export:
  path: models/doclayout_yolo_extended/yolov10n_17class.onnx
  target_size: < 20MB
  target_latency: < 100ms/page (CPU)
```

**MobileNetV3-small Classifiers:**

```yaml
# configs/models/handwriting_classifier_light.yaml
model:
  architecture: mobilenetv3_small
  pretrained: true
  num_classes: 2
  dropout: 0.2

training:
  epochs: 30
  batch_size: 128  # Larger batch for smaller model
  gpu: Modal T4

export:
  path: models/handwriting_classifier/mobilenetv3_handwriting.onnx
  target_size: < 10MB
  target_latency: < 5ms/crop (CPU)
```

#### 9.9.3 ⬜ Accuracy vs Latency Tradeoffs

| Model | Full Accuracy Target | Light Accuracy Target | Acceptable Degradation |
|-------|---------------------|----------------------|------------------------|
| DocLayout-YOLO | mAP ≥ 0.82 | mAP ≥ 0.75 | ≤ 8.5% |
| Handwriting Classifier | F1 ≥ 0.95 | F1 ≥ 0.90 | ≤ 5% |
| Table Type Classifier | Accuracy ≥ 0.85 | Accuracy ≥ 0.80 | ≤ 5.9% |
| Formula Complexity | Accuracy ≥ 0.85 | Accuracy ≥ 0.80 | ≤ 5.9% |

#### 9.9.4 ⬜ Benchmark Requirements

Both full and light variants must be benchmarked on:

| Device | Benchmark Requirement |
|--------|----------------------|
| CPU (8-core) | Required - primary deployment target |
| Local GPU (P2000/RTX A500) | Required - compare against CPU |
| Modal L4 | Required - cloud fallback baseline |

**Benchmark Output Format:**

```json
{
  "model": "handwriting_classifier",
  "variant": "light",
  "architecture": "mobilenetv3_small",
  "benchmarks": {
    "cpu": {"mean_ms": 4.2, "p95_ms": 5.8, "p99_ms": 6.1},
    "gpu_local": {"mean_ms": 5.1, "p95_ms": 6.2, "p99_ms": 7.0},
    "modal_l4": {"mean_ms": 0.8, "p95_ms": 1.2, "p99_ms": 1.4}
  },
  "accuracy": {
    "f1_score": 0.92,
    "vs_full_model_delta": -0.03
  }
}
```

#### 9.9.5 ⬜ Deployment Configuration

```yaml
# configs/inference/model_selection.yaml
model_variants:
  default: light  # Use light models by default for CPU

  # Override rules
  overrides:
    - condition: "modal_l4_available"
      variant: full
    - condition: "accuracy_critical"
      variant: full
    - condition: "latency_critical"
      variant: light

  # Fallback chain
  device_priority:
    - modal_l4: full
    - cpu: light
    # Note: Local GPU not recommended (negative speedup for small models)
```

---

### Phase 9 Deliverables

| Deliverable | Priority | Target |
|-------------|----------|--------|
| DocLayout-YOLO extended (17 classes) - Full | High | Week 11 |
| DocLayout-YOLO extended (17 classes) - Light (nano) | High | Week 11 |
| Handwriting classifier - Full + Light | High | Week 10 |
| Table type classifier - Full + Light | Medium | Week 11 |
| Formula complexity classifier - Full + Light | Medium | Week 11 |
| Parasitic content detector - Full + Light | Medium | Week 12 |
| Model registry + GCS sync | High | Week 12 |
| **Benchmark suite (CPU/GPU/Modal)** | **High** | **Week 12** |
| Project A→B contract document | High | Week 10 |
| Integration tests | High | Week 12 |

### Phase 9 Dependencies

* **Requires:** Phase 6 DocLayout-YOLO base training complete
* **Requires:** Modal GPU infrastructure (Phase 0)
* **Enables:** Project B specialist routing

### Phase 9 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Insufficient training data for custom classes | High | Start annotation early, use synthetic augmentation |
| Model accuracy below threshold | Medium | Iterate on architecture, increase data |
| ONNX export issues | Low | Test export early, use standard ops |
| GCS sync failures | Low | Retry logic, checksum verification |

---

## PHASE 10 — Validation & Benchmarking (Week 12–13)

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
| Phase 9 | Week 10-12 | ⬜ Planned | Specialized element training for Project B |
| Phase 10 | Week 12-13 | ⬜ Planned | Benchmarking, documentation |

**Total Timeline**: ~13 weeks to benchmarking

---
