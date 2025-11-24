---
schema_type: common
title: "Phase 4-10 Sprint Details (RAG Pipeline Numbering)"
description: "Detailed sprint breakdowns for Phases 4, 6, 8, and 10 - HISTORICAL REFERENCE"
tags: [planning, phase_planning, development, roadmap, historical]
status: archived
owner: "docs-team"
purpose: "Historical reference for sprint-level implementation tasks. Phase 4 is COMPLETE."
last_updated: "2025-01-24"
---

> **IMPORTANT**: This document uses RAG Pipeline phase numbering and is now a **HISTORICAL REFERENCE**. For current project status and official phase numbering, see [docs/planning/PROJECT_PLAN.md](../planning/PROJECT_PLAN.md).
>
> **Phase Status**:
> - **Phase 4 (Classical IQA)**: ✅ **COMPLETE** (January 2025) - Documented as Phase 1 + Phase 1C in PROJECT_PLAN.md
> - **Phase 6 (Layout-Lite)**: ⬜ Not Started
> - **Phase 8 (DQS & Routing)**: ⬜ In Progress (DQS calculation implementation)
> - **Phase 10 (Validation)**: ⬜ Not Started

This document provides detailed sprint breakdowns for Project A implementation phases. Each sprint includes specific tasks, dependencies, deliverables, and test requirements.

> **Note**: Phase 5 is intentionally skipped in the project numbering to maintain alignment with the four-project RAG pipeline architecture naming conventions.

---

## PHASE 4 — Classical IQA (Week 5-6)

Phase 4 implements classical computer vision-based Image Quality Assessment methods that serve as a baseline and fallback for the ML-based IQA system.

### Milestone 4.1: Laplacian-Based Blur Detection

**Timeline**: Day 1-2 (2 sprints)

#### Sprint 4.1.1: Core Blur Detection Implementation

**Description**: Implement Laplacian variance-based blur detection with configurable thresholds.

**Tasks**:
1. Create `BlurMetrics` dataclass with fields:
   - `laplacian_variance: float` - Raw variance score
   - `blur_score: float` - Normalized 0-1 score (0=blurry, 1=sharp)
   - `is_blurry: bool` - Binary classification
   - `severity: Severity` - LOW/MEDIUM/HIGH/CRITICAL
2. Implement `compute_laplacian_variance(image: np.ndarray) -> float`
3. Implement `normalize_blur_score(variance: float, min_var: float, max_var: float) -> float`
4. Implement blur severity classification based on thresholds
5. Add grayscale conversion handling for color images
6. Implement ROI-based blur detection for specific regions

**Dependencies**: OpenCV, NumPy

**Deliverables**:
- `src/image_preprocessing_detector/detection/blur_detector.py`
- Configurable threshold parameters in YAML

**Tests Required**:
- Unit tests for Laplacian variance calculation
- Unit tests for score normalization
- Integration test with synthetic blurred images
- Edge cases: all-black image, all-white image, high-frequency noise

#### Sprint 4.1.2: Blur Detection Integration

**Description**: Integrate blur detection into the IQA classical module and add configuration support.

**Tasks**:
1. Add blur detection to `iqa_classical.py` module
2. Create configuration schema for blur thresholds
3. Implement caching for repeated blur checks on same image
4. Add structured logging for blur detection results
5. Create CLI command for standalone blur detection testing
6. Document blur detection algorithm and threshold selection

**Dependencies**: Sprint 4.1.1

**Deliverables**:
- Updated `iqa_classical.py` with blur detection
- Configuration in `config/defaults.yaml`
- CLI command `imgprep blur-check`

**Tests Required**:
- Integration test with configuration loading
- CLI command test
- Performance benchmark (target: <10ms per image)

---

### Milestone 4.2: Wavelet Noise Estimator

**Timeline**: Day 3-4 (2 sprints)

#### Sprint 4.2.1: Wavelet-Based Noise Estimation

**Description**: Implement wavelet decomposition-based noise level estimation using Median Absolute Deviation (MAD).

**Tasks**:
1. Create `NoiseMetrics` dataclass with fields:
   - `noise_sigma: float` - Estimated noise standard deviation
   - `noise_score: float` - Normalized 0-1 score (0=noisy, 1=clean)
   - `is_noisy: bool` - Binary classification
   - `severity: Severity` - LOW/MEDIUM/HIGH/CRITICAL
2. Implement `wavelet_decompose(image: np.ndarray, wavelet: str = 'db1', level: int = 1) -> tuple`
3. Implement `estimate_noise_mad(detail_coeffs: np.ndarray) -> float`
4. Implement noise severity classification
5. Add support for different wavelet families (db1, haar, sym2)
6. Handle multi-channel images (process luminance channel)

**Dependencies**: PyWavelets (pywt), NumPy

**Deliverables**:
- `src/image_preprocessing_detector/detection/noise_detector.py`
- Wavelet configuration options

**Tests Required**:
- Unit tests for wavelet decomposition
- Unit tests for MAD estimation
- Integration test with synthetic noisy images (Gaussian, salt-pepper)
- Comparison with known noise levels

#### Sprint 4.2.2: Noise Detection Integration

**Description**: Integrate noise detection into IQA pipeline with configurable parameters.

**Tasks**:
1. Add noise detection to `iqa_classical.py` module
2. Create configuration schema for noise thresholds
3. Implement combined noise metrics (per-channel analysis)
4. Add noise type classification hints (Gaussian vs. salt-pepper patterns)
5. Create CLI command for standalone noise detection
6. Document noise estimation algorithm

**Dependencies**: Sprint 4.2.1

**Deliverables**:
- Updated `iqa_classical.py` with noise detection
- Configuration in `config/defaults.yaml`
- CLI command `imgprep noise-check`

**Tests Required**:
- Integration test with various noise types
- Performance benchmark (target: <20ms per image)
- Accuracy validation against known noise levels

---

### Milestone 4.3: Hough Skew Detection

**Timeline**: Day 5-6 (2 sprints)

#### Sprint 4.3.1: Probabilistic Hough Transform Implementation

**Description**: Implement skew angle detection using Probabilistic Hough Transform on document edges.

**Tasks**:
1. Create `SkewMetrics` dataclass with fields:
   - `skew_angle: float` - Detected skew angle in degrees
   - `skew_confidence: float` - Confidence in detection (0-1)
   - `num_lines_detected: int` - Number of supporting lines
   - `is_skewed: bool` - Binary classification (threshold-based)
   - `severity: Severity` - Based on angle magnitude
2. Implement `preprocess_for_hough(image: np.ndarray) -> np.ndarray`:
   - Canny edge detection
   - Optional dilation for better line detection
3. Implement `detect_lines_hough(edges: np.ndarray, min_line_length: int, max_line_gap: int) -> np.ndarray`
4. Implement `calculate_dominant_angle(lines: np.ndarray) -> tuple[float, float]`:
   - Filter near-horizontal/vertical lines
   - Use weighted voting for dominant angle
5. Handle edge cases: no lines detected, multiple dominant angles

**Dependencies**: OpenCV, NumPy

**Deliverables**:
- `src/image_preprocessing_detector/detection/skew_detector.py`
- Hough transform parameters in configuration

**Tests Required**:
- Unit tests for angle calculation
- Integration tests with known skew angles (0°, 5°, 15°, 45°)
- Edge cases: blank image, image with only noise
- Comparison with ground truth on synthetic rotated documents

#### Sprint 4.3.2: Skew Detection Integration

**Description**: Integrate skew detection with correction pipeline feedback.

**Tasks**:
1. Add skew detection to `iqa_classical.py` module
2. Link skew detection output to deskew correction module
3. Implement multi-angle voting for complex documents
4. Add visualization helper for detected lines (debug mode)
5. Create CLI command for standalone skew detection
6. Document skew detection algorithm and limitations

**Dependencies**: Sprint 4.3.1, Correction pipeline (deskew)

**Deliverables**:
- Updated `iqa_classical.py` with skew detection
- Integration with correction pipeline
- CLI command `imgprep skew-check`

**Tests Required**:
- End-to-end test: detect skew → apply deskew → verify correction
- Performance benchmark (target: <30ms per image)
- Document type variations (single-column, multi-column)

---

### Milestone 4.4: Lighting Metrics

**Timeline**: Day 7-8 (2 sprints)

#### Sprint 4.4.1: Lighting Uniformity Analysis

**Description**: Implement lighting analysis including contrast, brightness, and uniformity metrics.

**Tasks**:
1. Create `LightingMetrics` dataclass with fields:
   - `mean_brightness: float` - Average pixel intensity (0-255)
   - `brightness_std: float` - Brightness standard deviation
   - `contrast_ratio: float` - Weber/Michelson contrast
   - `uniformity_score: float` - Lighting uniformity (0-1)
   - `has_shadows: bool` - Shadow detection flag
   - `has_highlights: bool` - Overexposure detection flag
   - `severity: Severity` - Overall lighting quality
2. Implement `compute_histogram_metrics(image: np.ndarray) -> dict`:
   - Mean, std, skewness, kurtosis
3. Implement `compute_contrast_ratio(image: np.ndarray, method: str = 'rms') -> float`:
   - RMS contrast
   - Weber contrast
   - Michelson contrast
4. Implement `detect_lighting_issues(image: np.ndarray) -> tuple[bool, bool]`:
   - Shadow detection (large dark regions)
   - Highlight/overexposure detection (clipping)
5. Implement block-based uniformity analysis

**Dependencies**: OpenCV, NumPy, SciPy (for histogram metrics)

**Deliverables**:
- `src/image_preprocessing_detector/detection/lighting_detector.py`
- Lighting threshold configuration

**Tests Required**:
- Unit tests for each contrast method
- Integration tests with underexposed/overexposed images
- Synthetic tests with controlled lighting variations
- Edge cases: very dark, very bright, high contrast

#### Sprint 4.4.2: Lighting Detection Integration

**Description**: Integrate lighting metrics into IQA pipeline with CLAHE correction feedback.

**Tasks**:
1. Add lighting detection to `iqa_classical.py` module
2. Link lighting metrics to CLAHE correction parameters
3. Implement adaptive threshold selection based on image statistics
4. Add regional lighting analysis (document zones)
5. Create CLI command for standalone lighting analysis
6. Document lighting metrics and correction recommendations

**Dependencies**: Sprint 4.4.1, Correction pipeline (CLAHE)

**Deliverables**:
- Updated `iqa_classical.py` with lighting detection
- Integration with CLAHE correction
- CLI command `imgprep lighting-check`

**Tests Required**:
- End-to-end test: detect low contrast → apply CLAHE → verify improvement
- Performance benchmark (target: <15ms per image)
- Validation against human perception (if labeled data available)

---

### Milestone 4.5: JPEG Blockiness Detection

**Timeline**: Day 9-10 (2 sprints)

#### Sprint 4.5.1: Block Artifact Measurement

**Description**: Implement JPEG compression artifact detection based on 8x8 block boundary analysis.

**Tasks**:
1. Create `CompressionMetrics` dataclass with fields:
   - `blockiness_score: float` - Block artifact severity (0-1)
   - `estimated_quality: int` - Estimated JPEG quality factor (1-100)
   - `has_artifacts: bool` - Binary classification
   - `block_edge_strength: float` - Average edge strength at 8x8 boundaries
   - `severity: Severity` - Based on artifact level
2. Implement `compute_block_edge_strength(image: np.ndarray) -> float`:
   - Extract 8x8 block boundaries
   - Compute gradient magnitude at boundaries
   - Compare to non-boundary gradient average
3. Implement `estimate_jpeg_quality(image: np.ndarray) -> int`:
   - DCT coefficient analysis (if applicable)
   - Empirical quality estimation from blockiness
4. Implement `detect_ringing_artifacts(image: np.ndarray) -> float`:
   - Gibbs phenomenon detection near edges
5. Handle non-JPEG images (return clean scores)

**Dependencies**: OpenCV, NumPy

**Deliverables**:
- `src/image_preprocessing_detector/detection/compression_detector.py`
- JPEG quality threshold configuration

**Tests Required**:
- Unit tests with JPEG images at various quality levels (10, 30, 50, 70, 90)
- Comparison: PNG vs JPEG at same visual content
- Edge cases: lossless images, heavily compressed images
- Validation against known JPEG quality settings

#### Sprint 4.5.2: Compression Detection Integration

**Description**: Integrate compression artifact detection into IQA pipeline.

**Tasks**:
1. Add compression detection to `iqa_classical.py` module
2. Create configuration schema for compression thresholds
3. Implement format-aware detection (JPEG vs. other formats)
4. Add compression artifact visualization (debug mode)
5. Create CLI command for standalone compression analysis
6. Document blockiness detection algorithm

**Dependencies**: Sprint 4.5.1

**Deliverables**:
- Updated `iqa_classical.py` with compression detection
- Configuration in `config/defaults.yaml`
- CLI command `imgprep compression-check`

**Tests Required**:
- Integration test with mixed format inputs
- Performance benchmark (target: <10ms per image)
- Real-world document samples with compression artifacts

---

### Milestone 4.6: Student vs Classical Discrepancy Tuning

**Timeline**: Day 11-12 (2 sprints)

#### Sprint 4.6.1: Discrepancy Metrics Implementation

**Description**: Implement discrepancy calculation between ML student model and classical IQA outputs.

**Tasks**:
1. Create `DiscrepancyResult` dataclass with fields:
   - `blur_discrepancy: float` - |student_blur - classical_blur|
   - `noise_discrepancy: float` - |student_noise - classical_noise|
   - `contrast_discrepancy: float` - |student_contrast - classical_contrast|
   - `skew_discrepancy: float` - |student_skew - classical_skew|
   - `max_discrepancy: float` - Maximum across all metrics
   - `mean_discrepancy: float` - Average discrepancy
   - `should_escalate: bool` - Threshold-based escalation decision
2. Implement `normalize_scores(classical: ClassicalIQAScores, student: MLIQAScores) -> tuple`:
   - Align score ranges (both 0-1, same direction)
3. Implement `compute_discrepancy(classical: ClassicalIQAScores, student: MLIQAScores) -> DiscrepancyResult`
4. Implement `should_escalate_to_teacher(discrepancy: DiscrepancyResult, threshold: float) -> bool`
5. Add per-metric discrepancy thresholds (not just global)

**Dependencies**: iqa_classical.py, iqa_ml.py

**Deliverables**:
- `src/image_preprocessing_detector/detection/discrepancy_checker.py`
- Discrepancy threshold configuration

**Tests Required**:
- Unit tests for score normalization
- Unit tests for discrepancy calculation
- Integration test with mock student/classical outputs
- Edge cases: identical scores, maximally different scores

#### Sprint 4.6.2: Threshold Tuning and Validation

**Description**: Tune discrepancy thresholds using validation dataset and integrate with escalation logic.

**Tasks**:
1. Create validation dataset with known quality issues
2. Implement threshold tuning script:
   - Run classical IQA on validation set
   - Run student ML IQA on validation set
   - Compute discrepancies for all samples
   - Find optimal threshold for precision/recall balance
3. Implement discrepancy logging and analysis tools
4. Integrate discrepancy check into main pipeline
5. Add configuration for per-metric thresholds
6. Document threshold selection methodology

**Dependencies**: Sprint 4.6.1, Validation dataset

**Deliverables**:
- Tuned threshold values in configuration
- `scripts/tune_discrepancy_threshold.py`
- Integration with `MLIQADetector.should_escalate_to_teacher()`

**Tests Required**:
- Validation on held-out test set
- Precision/recall analysis for escalation decisions
- Performance impact analysis (escalation rate vs. accuracy gain)
- A/B comparison: with/without discrepancy check

---

## PHASE 6 — Layout-Lite Detection (Week 6-8)

Phase 6 implements lightweight layout detection for coarse page classification. This is NOT full semantic layout detection (Project B's responsibility), but provides routing metadata for downstream processing.

### Milestone 6.1: YOLOv8-Nano Detector

**Timeline**: Day 1-4 (4 sprints)

#### Sprint 6.1.1: YOLOv8-Nano Model Setup

**Description**: Set up YOLOv8-nano model for coarse layout element detection.

**Tasks**:
1. Install Ultralytics YOLOv8 package
2. Download pre-trained YOLOv8-nano weights
3. Create model wrapper class `LayoutLiteDetector`:
   - `__init__(model_path: str, device: str = 'auto')`
   - `detect(image: np.ndarray) -> list[LayoutElement]`
4. Define `LayoutElement` dataclass:
   - `category: ElementCategory` - text_block, table, figure, formula
   - `bbox: tuple[int, int, int, int]` - COCO format [x, y, w, h]
   - `confidence: float` - Detection confidence
5. Implement device selection logic (GPU preferred)
6. Add batch inference support

**Dependencies**: Ultralytics, PyTorch, OpenCV

**Deliverables**:
- `src/image_preprocessing_detector/detection/layout_lite.py`
- Model weights in `models/yolov8n-layout/`

**Tests Required**:
- Unit test for model loading
- Integration test with sample document images
- Performance benchmark (target: <50ms per image on GPU)

#### Sprint 6.1.2: Document-Specific Fine-Tuning Preparation

**Description**: Prepare dataset and configuration for fine-tuning YOLOv8-nano on document layouts.

**Tasks**:
1. Create data loader for PubLayNet subset (or similar)
2. Define YAML configuration for fine-tuning:
   - Classes: text_block, table, figure, formula, handwriting
   - Image size: 640x640
   - Augmentation settings
3. Implement data preprocessing pipeline:
   - Resize to model input size
   - Normalize pixel values
   - Convert annotations to YOLO format
4. Create train/val/test splits
5. Set up training configuration (epochs, batch size, learning rate)
6. Document dataset requirements and preparation steps

**Dependencies**: Sprint 6.1.1, PubLayNet or custom dataset

**Deliverables**:
- `configs/layout_lite_training.yaml`
- `scripts/prepare_layout_dataset.py`
- Dataset documentation

**Tests Required**:
- Data loader unit tests
- Annotation conversion validation
- Data augmentation verification

#### Sprint 6.1.3: YOLOv8-Nano Fine-Tuning

**Description**: Fine-tune YOLOv8-nano on document layout dataset.

**Tasks**:
1. Implement training script for Modal GPU:
   - Load pre-trained weights
   - Configure optimizer (AdamW)
   - Set up learning rate scheduler
   - Enable mixed precision training
2. Train for 50-100 epochs with early stopping
3. Implement checkpoint saving (best mAP)
4. Log training metrics (loss, mAP, per-class AP)
5. Export best model to ONNX format
6. Create model card with performance summary

**Dependencies**: Sprint 6.1.2, Modal GPU access

**Deliverables**:
- `modal/train_layout_lite.py`
- Fine-tuned model weights
- Training logs and metrics
- ONNX exported model

**Tests Required**:
- Validation mAP@0.5 > 0.75
- Per-class precision/recall analysis
- Inference speed validation

#### Sprint 6.1.4: Layout Detection Integration

**Description**: Integrate YOLOv8-nano layout detection into the main pipeline.

**Tasks**:
1. Add layout detection to detection pipeline
2. Implement post-processing:
   - NMS (Non-Maximum Suppression) refinement
   - Confidence thresholding
   - Small region filtering
3. Map detections to `DocumentElement` schema
4. Add layout visualization helper
5. Create CLI command for standalone layout detection
6. Update documentation

**Dependencies**: Sprint 6.1.3

**Deliverables**:
- Updated detection pipeline with layout-lite
- CLI command `imgprep layout-check`
- Visualization utilities

**Tests Required**:
- End-to-end pipeline test
- Performance benchmark (target: <50ms GPU, <200ms CPU)
- Integration with schema output

---

### Milestone 6.2: Handwriting Classifier

**Timeline**: Day 5-6 (2 sprints)

#### Sprint 6.2.1: Handwriting Detection Model

**Description**: Implement binary classifier for handwriting presence detection.

**Tasks**:
1. Create `HandwritingDetector` class:
   - `__init__(model_path: str = None)`
   - `detect_handwriting(image: np.ndarray) -> HandwritingResult`
   - `detect_in_region(image: np.ndarray, bbox: tuple) -> HandwritingResult`
2. Define `HandwritingResult` dataclass:
   - `has_handwriting: bool`
   - `confidence: float`
   - `regions: list[tuple[int, int, int, int]]` - Detected handwriting regions
3. Implement lightweight CNN classifier (MobileNetV3-small backbone)
4. Add ONNX model loading and inference
5. Implement sliding window detection for large documents
6. Add confidence calibration

**Dependencies**: PyTorch, ONNX Runtime

**Deliverables**:
- `src/image_preprocessing_detector/detection/handwriting_detector.py`
- Pre-trained model weights
- ONNX exported model

**Tests Required**:
- Unit test with handwritten samples
- Unit test with typed text samples
- Binary classification accuracy > 95%
- Performance benchmark (target: <30ms per image)

#### Sprint 6.2.2: Handwriting Integration

**Description**: Integrate handwriting detection with layout-lite and schema output.

**Tasks**:
1. Add handwriting detection to layout-lite pipeline
2. Update `PageLayoutSummary.has_handwriting` field population
3. Implement per-element handwriting scoring in `DocumentElement`
4. Add handwriting region visualization
5. Create CLI option for handwriting detection
6. Document handwriting detection algorithm

**Dependencies**: Sprint 6.2.1, Layout-lite detector

**Deliverables**:
- Integrated handwriting detection
- Updated schema population
- CLI integration

**Tests Required**:
- Integration test with mixed documents
- Schema validation with handwriting fields
- End-to-end pipeline test

---

### Milestone 6.3: Complexity Scorer

**Timeline**: Day 7-8 (2 sprints)

#### Sprint 6.3.1: Structural Complexity Metrics

**Description**: Implement page structural complexity scoring for routing decisions.

**Tasks**:
1. Create `ComplexityScorer` class:
   - `__init__(weights: dict = None)`
   - `compute_complexity(elements: list[LayoutElement], page_size: tuple) -> ComplexityResult`
2. Define `ComplexityResult` dataclass:
   - `complexity_score: float` - Overall 0-1 score
   - `element_count: int` - Number of detected elements
   - `element_diversity: float` - Variety of element types
   - `layout_density: float` - Coverage ratio
   - `nesting_depth: int` - Estimated nesting (tables in tables)
   - `factors: dict[str, float]` - Per-factor breakdown
3. Implement complexity factors:
   - Element count normalization
   - Element type diversity (Shannon entropy)
   - Spatial density (total bbox area / page area)
   - Overlap complexity (intersecting elements)
4. Implement weighted combination with configurable weights
5. Add complexity category classification (SIMPLE, MODERATE, COMPLEX, VERY_COMPLEX)

**Dependencies**: Layout-lite detector output

**Deliverables**:
- `src/image_preprocessing_detector/detection/complexity_scorer.py`
- Complexity weight configuration

**Tests Required**:
- Unit tests for each complexity factor
- Integration test with layout detector output
- Calibration against human complexity ratings
- Edge cases: empty page, single element, maximum elements

#### Sprint 6.3.2: Complexity Integration

**Description**: Integrate complexity scoring into pipeline and schema.

**Tasks**:
1. Add complexity scoring to layout-lite pipeline
2. Update `PageLayoutSummary.complexity_score` field
3. Implement document-level complexity aggregation
4. Add complexity-based routing hints
5. Create complexity visualization (heatmap)
6. Document complexity scoring methodology

**Dependencies**: Sprint 6.3.1

**Deliverables**:
- Integrated complexity scoring
- Updated schema population
- Documentation

**Tests Required**:
- End-to-end pipeline test
- Schema validation
- Routing decision validation

---

### Milestone 6.4: Structural Features API

**Timeline**: Day 9-10 (2 sprints)

#### Sprint 6.4.1: Unified Structural Features Interface

**Description**: Create unified API for all structural features (layout, handwriting, complexity).

**Tasks**:
1. Create `StructuralFeaturesExtractor` class:
   - `__init__(config: StructuralConfig)`
   - `extract(image: np.ndarray) -> StructuralFeatures`
   - `extract_batch(images: list[np.ndarray]) -> list[StructuralFeatures]`
2. Define `StructuralFeatures` dataclass combining:
   - Layout elements
   - Handwriting detection
   - Complexity scores
   - Page attributes (fuzzy_scan, watermark, colorful_background)
3. Implement page attribute detection:
   - Fuzzy scan detection (blur + noise combination)
   - Watermark detection (transparency patterns)
   - Background color detection (non-white dominant)
4. Add caching for repeated feature extraction
5. Implement async batch processing

**Dependencies**: Layout-lite, Handwriting detector, Complexity scorer

**Deliverables**:
- `src/image_preprocessing_detector/detection/structural_features.py`
- Unified configuration schema

**Tests Required**:
- Unit tests for each feature type
- Integration test with full pipeline
- Batch processing performance test
- API documentation validation

#### Sprint 6.4.2: Structural Features Documentation and CLI

**Description**: Complete documentation and CLI integration for structural features.

**Tasks**:
1. Create comprehensive API documentation
2. Add CLI commands for structural analysis:
   - `imgprep analyze-structure` - Full structural analysis
   - `imgprep page-attributes` - Page attribute detection only
3. Implement JSON output for structural features
4. Add visualization tools for structural analysis
5. Create usage examples and tutorials
6. Update main pipeline to use structural features API

**Dependencies**: Sprint 6.4.1

**Deliverables**:
- API documentation
- CLI commands
- Usage examples
- Updated pipeline integration

**Tests Required**:
- CLI command tests
- JSON output validation
- Documentation accuracy verification

---

## PHASE 8 — DQS & Routing (Week 9)

Phase 8 implements Document Quality Score calculation and OCR routing recommendations for Project B handoff.

### Milestone 8.1: DQS Weighting Optimization

**Timeline**: Day 1-2 (2 sprints)

#### Sprint 8.1.1: DQS Weight Calibration Framework

**Description**: Implement framework for calibrating DQS weights against OCR performance.

**Tasks**:
1. Create `DQSCalibrator` class:
   - `__init__(ocr_performance_data: pd.DataFrame)`
   - `optimize_weights(metric: str = 'f1') -> dict[str, float]`
   - `evaluate_weights(weights: dict) -> dict[str, float]`
2. Implement correlation analysis between IQA metrics and OCR performance:
   - Blur score vs. character error rate (CER)
   - Noise score vs. CER
   - Contrast score vs. CER
   - Skew score vs. CER
3. Implement weight optimization using grid search
4. Add cross-validation for weight stability
5. Create visualization for weight sensitivity analysis
6. Document calibration methodology

**Dependencies**: OCR performance dataset (from evaluation runs)

**Deliverables**:
- `src/image_preprocessing_detector/routing/dqs_calibrator.py`
- `scripts/calibrate_dqs_weights.py`
- Calibration report template

**Tests Required**:
- Unit tests for correlation calculation
- Unit tests for optimization
- Stability test across different datasets
- Documentation of optimal weights

#### Sprint 8.1.2: DQS Calculator Enhancement

**Description**: Enhance DQS calculation with calibrated weights and additional factors.

**Tasks**:
1. Update `calculate_dqs()` with calibrated weights
2. Add configuration for custom weight overrides
3. Implement DQS confidence interval estimation
4. Add DQS breakdown by factor (for explainability)
5. Implement DQS trend analysis for multi-page documents
6. Update schema with enhanced DQS metadata

**Dependencies**: Sprint 8.1.1

**Deliverables**:
- Updated `src/image_preprocessing_detector/metrics/dqs_calculator.py`
- Enhanced DQS configuration
- Updated schema fields

**Tests Required**:
- Integration test with calibrated weights
- Schema validation
- Performance benchmark

---

### Milestone 8.2: Per-Page and Document Scoring

**Timeline**: Day 3-4 (2 sprints)

#### Sprint 8.2.1: Page-Level Scoring Implementation

**Description**: Implement detailed per-page quality scoring with all IQA dimensions.

**Tasks**:
1. Create `PageQualityScore` dataclass:
   - `page_index: int`
   - `degradation_score: float` - IQA-based degradation
   - `structural_complexity: float` - Layout-based complexity
   - `combined_score: float` - Weighted combination
   - `risk_factors: list[str]` - Identified risk factors
   - `confidence: float` - Score confidence
2. Implement per-page scoring pipeline:
   - Aggregate IQA metrics (blur, noise, contrast, skew, compression)
   - Include ML IQA scores (student and teacher if available)
   - Include structural features
3. Add page ranking by quality (worst pages first)
4. Implement page quality visualization
5. Add page-level logging and telemetry

**Dependencies**: IQA pipeline, Structural features

**Deliverables**:
- `src/image_preprocessing_detector/metrics/page_scorer.py`
- Page quality visualization tools

**Tests Required**:
- Unit tests for score aggregation
- Integration test with full pipeline
- Ranking validation

#### Sprint 8.2.2: Document-Level Scoring Aggregation

**Description**: Implement document-level quality score aggregation.

**Tasks**:
1. Create `DocumentQualityScorer` class:
   - `__init__(aggregation_method: str = 'weighted_mean')`
   - `score_document(pages: list[PageQualityScore]) -> DocumentQualityScore`
2. Implement aggregation methods:
   - Weighted mean (default)
   - Worst-page (min)
   - Percentile-based (e.g., 10th percentile)
   - Confidence-weighted mean
3. Add document-level risk assessment
4. Implement quality trend analysis (improving/degrading pages)
5. Update `DocumentMetadata.dqs` with enhanced scoring
6. Add document quality report generation

**Dependencies**: Sprint 8.2.1

**Deliverables**:
- `src/image_preprocessing_detector/metrics/document_scorer.py`
- Document quality report template
- Updated schema integration

**Tests Required**:
- Unit tests for each aggregation method
- Integration test with multi-page documents
- Schema validation
- Report generation test

---

### Milestone 8.3: Routing Logic Implementation

**Timeline**: Day 5-6 (2 sprints)

#### Sprint 8.3.1: Routing Decision Engine

**Description**: Implement OCR routing recommendation logic based on DQS and structural features.

**Tasks**:
1. Create `RoutingDecisionEngine` class:
   - `__init__(config: RoutingConfig)`
   - `recommend_routing(doc_metadata: DocumentMetadata) -> RoutingRecommendation`
2. Define `RoutingRecommendation` dataclass:
   - `strategy: OCRRoutingStrategy` - ocr_fast, ocr_advanced, vision_simple, vision_structured
   - `confidence: float` - Decision confidence
   - `factors: dict[str, float]` - Factor contributions
   - `alternative: OCRRoutingStrategy | None` - Fallback recommendation
   - `explanation: str` - Human-readable explanation
3. Implement routing rules:
   - High quality + simple layout → ocr_fast
   - High quality + complex layout → ocr_advanced
   - Low quality + simple layout → vision_simple
   - Low quality + complex layout → vision_structured
4. Add PDF type influence on routing
5. Implement teacher results influence on routing
6. Add routing decision logging

**Dependencies**: DQS calculator, Structural features

**Deliverables**:
- `src/image_preprocessing_detector/routing/decision_engine.py`
- Routing configuration schema

**Tests Required**:
- Unit tests for each routing rule
- Integration test with various document types
- Decision explanation validation
- Edge case handling

#### Sprint 8.3.2: Routing Configuration and Thresholds

**Description**: Implement configurable routing thresholds and A/B testing support.

**Tasks**:
1. Create routing configuration schema:
   - DQS thresholds for each strategy
   - Complexity thresholds
   - PDF type preferences
   - Teacher influence weights
2. Implement threshold tuning framework
3. Add A/B testing support (random routing with logging)
4. Implement routing statistics collection
5. Create routing threshold tuning script
6. Document routing decision logic

**Dependencies**: Sprint 8.3.1

**Deliverables**:
- Routing configuration in `config/routing.yaml`
- `scripts/tune_routing_thresholds.py`
- Routing documentation

**Tests Required**:
- Configuration validation tests
- A/B testing functionality test
- Statistics collection test
- Documentation accuracy

---

### Milestone 8.4: JSON Schema Output

**Timeline**: Day 7-8 (2 sprints)

#### Sprint 8.4.1: Enhanced Schema Implementation

**Description**: Update DocumentMetadata schema with all routing-related fields.

**Tasks**:
1. Verify and update `DocumentMetadata` schema:
   - `pdf_type: PDFType` - Classification result
   - `languages: list[str]` - Detected languages
   - `has_non_latin: bool` - Non-Latin script flag
   - `pre_ocr_risk: float` - Risk score
   - `dqs: DQSMetadata` - Quality scores
   - `ocr_routing_recommendation: OCRRoutingStrategy` - Routing decision
   - `page_layout_summary: list[PageLayoutSummary]` - Per-page layout
2. Add routing explanation fields
3. Implement schema versioning
4. Add backward compatibility handling
5. Create schema migration utilities
6. Update JSON serialization with all new fields

**Dependencies**: All previous milestones

**Deliverables**:
- Updated `src/image_preprocessing_detector/schema.py`
- Schema migration utilities
- Versioning documentation

**Tests Required**:
- Schema validation tests
- JSON serialization/deserialization tests
- Backward compatibility tests
- Example output generation

#### Sprint 8.4.2: Output Pipeline Integration

**Description**: Integrate all routing metadata into final output pipeline.

**Tasks**:
1. Update `DocumentProcessor` to populate all routing fields
2. Implement output validation (schema compliance check)
3. Add output statistics and summary generation
4. Create sample output generator for documentation
5. Implement output diffing tool (compare outputs)
6. Update CLI output formatting

**Dependencies**: Sprint 8.4.1

**Deliverables**:
- Updated `DocumentProcessor`
- Output validation utilities
- Sample outputs for documentation
- Updated CLI

**Tests Required**:
- End-to-end output generation test
- Schema compliance validation
- CLI output test
- Sample output verification

---

## PHASE 10 — Validation, Reporting, Documentation (Week 10)

Phase 10 focuses on comprehensive validation, performance benchmarking, and documentation completion.

### Milestone 10.1: Full Pipeline Benchmark

**Timeline**: Day 1-2 (2 sprints)

#### Sprint 10.1.1: Benchmark Framework Implementation

**Description**: Create comprehensive benchmark framework for full pipeline evaluation.

**Tasks**:
1. Create `PipelineBenchmark` class:
   - `__init__(config: BenchmarkConfig)`
   - `run_benchmark(dataset_path: str) -> BenchmarkReport`
   - `compare_runs(reports: list[BenchmarkReport]) -> ComparisonReport`
2. Define `BenchmarkReport` dataclass:
   - Latency metrics (mean, p50, p95, p99)
   - Throughput metrics (pages/sec)
   - Memory usage (peak, average)
   - GPU utilization (if applicable)
   - Per-component breakdown
   - Error rates
3. Implement benchmark dataset preparation
4. Add warm-up iterations handling
5. Implement statistical significance testing
6. Create benchmark result visualization

**Dependencies**: Complete pipeline

**Deliverables**:
- `src/image_preprocessing_detector/benchmarks/pipeline_benchmark.py`
- Benchmark configuration
- Result visualization tools

**Tests Required**:
- Benchmark framework unit tests
- Result accuracy validation
- Statistical validity tests

#### Sprint 10.1.2: Benchmark Execution and Analysis

**Description**: Execute comprehensive benchmarks and analyze results.

**Tasks**:
1. Create benchmark dataset:
   - 100+ diverse documents
   - Various quality levels
   - Multiple page counts (1, 5, 10, 50+ pages)
   - Different document types
2. Run benchmarks on multiple hardware configurations:
   - CPU only
   - GPU (T4)
   - GPU (A10/A100 if available)
3. Analyze results against performance targets
4. Identify performance bottlenecks
5. Generate benchmark report
6. Create performance regression baseline

**Dependencies**: Sprint 10.1.1, Benchmark dataset

**Deliverables**:
- Benchmark execution scripts
- Performance analysis report
- Baseline metrics for regression testing

**Tests Required**:
- Benchmark reproducibility test
- Performance target validation
- Regression baseline validation

---

### Milestone 10.2: Teacher vs Student Performance Report

**Timeline**: Day 3-4 (2 sprints)

#### Sprint 10.2.1: Model Comparison Framework

**Description**: Implement framework for comparing teacher and student model performance.

**Tasks**:
1. Create `ModelComparisonReport` class:
   - `__init__(student_results: dict, teacher_results: dict)`
   - `compute_metrics() -> ComparisonMetrics`
   - `generate_report() -> str`
2. Define comparison metrics:
   - Accuracy correlation (student vs. teacher)
   - Latency ratio
   - Memory ratio
   - Escalation rate analysis
   - Error case analysis
3. Implement per-metric comparison (blur, noise, contrast, skew, compression)
4. Add visualization for comparison results
5. Implement statistical tests for significance

**Dependencies**: Trained student and teacher models

**Deliverables**:
- `src/image_preprocessing_detector/analysis/model_comparison.py`
- Comparison visualization tools

**Tests Required**:
- Metric calculation unit tests
- Report generation tests
- Statistical test validation

#### Sprint 10.2.2: End-to-End Performance Analysis

**Description**: Analyze end-to-end performance with and without teacher escalation.

**Tasks**:
1. Run evaluation on validation dataset:
   - Student-only mode
   - Teacher-only mode (baseline)
   - Student + selective teacher escalation
2. Compare against ground truth labels
3. Analyze escalation effectiveness:
   - True positive rate (correct escalations)
   - False positive rate (unnecessary escalations)
   - Cost-benefit analysis
4. Generate comprehensive performance report
5. Create recommendations for production configuration
6. Document findings and trade-offs

**Dependencies**: Sprint 10.2.1, Validation dataset with labels

**Deliverables**:
- Performance analysis report
- Production configuration recommendations
- Trade-off documentation

**Tests Required**:
- Evaluation script validation
- Report accuracy verification

---

### Milestone 10.3: Stress Tests

**Timeline**: Day 5-6 (2 sprints)

#### Sprint 10.3.1: Large Batch Processing Tests

**Description**: Implement and run stress tests for large batch processing.

**Tasks**:
1. Create `StressTestSuite` class:
   - `test_large_batch(num_documents: int)`
   - `test_large_pages(pages_per_doc: int)`
   - `test_concurrent_processing(num_workers: int)`
   - `test_memory_pressure(target_memory_gb: float)`
2. Implement test scenarios:
   - 1000+ document batch processing
   - 100+ page document processing
   - Concurrent worker scaling (1, 2, 4, 8 workers)
   - Memory pressure with limited resources
3. Add monitoring integration (memory, CPU, GPU)
4. Implement failure recovery testing
5. Create stress test report template

**Dependencies**: Complete pipeline, Large test dataset

**Deliverables**:
- `tests/stress/test_large_batch.py`
- Stress test execution scripts
- Monitoring dashboards

**Tests Required**:
- Stress test framework validation
- Monitoring accuracy validation

#### Sprint 10.3.2: Error Handling and Recovery Tests

**Description**: Test error handling and recovery under stress conditions.

**Tasks**:
1. Implement fault injection framework:
   - Random file corruption
   - Network failures (for Modal)
   - Memory exhaustion simulation
   - GPU memory overflow
2. Test graceful degradation:
   - GPU → CPU fallback
   - Teacher unavailable → student-only
   - Partial processing recovery
3. Test data integrity under failures
4. Generate error handling report
5. Document recovery procedures
6. Create operational runbook

**Dependencies**: Sprint 10.3.1

**Deliverables**:
- Fault injection framework
- Error handling test suite
- Operational runbook

**Tests Required**:
- Fault injection validation
- Recovery verification
- Data integrity tests

---

### Milestone 10.4: PlantUML Diagram Updates

**Timeline**: Day 7 (1 sprint)

#### Sprint 10.4.1: Architecture Diagram Updates

**Description**: Update all PlantUML diagrams to reflect final implementation.

**Tasks**:
1. Update main architecture diagram:
   - Add Phase 2 ML IQA components
   - Add Phase 4 Classical IQA components
   - Add Phase 6 Layout-lite components
   - Add Phase 8 Routing components
2. Create detailed component diagrams:
   - IQA pipeline flow
   - Escalation decision tree
   - Routing decision tree
   - Data flow diagram
3. Create sequence diagrams:
   - Document processing flow
   - Teacher escalation flow
   - Batch processing flow
4. Verify diagram accuracy against code
5. Export diagrams to PNG/SVG for documentation

**Dependencies**: All previous phases complete

**Deliverables**:
- Updated `docs/diagrams/*.puml`
- Exported diagram images
- Diagram index documentation

**Tests Required**:
- Diagram syntax validation
- Manual accuracy review

---

### Milestone 10.5: Final Documentation

**Timeline**: Day 8-10 (3 sprints)

#### Sprint 10.5.1: README and Quick Start Update

**Description**: Update README with complete feature documentation.

**Tasks**:
1. Update README.md:
   - Feature overview (all phases)
   - Quick start guide
   - Installation instructions
   - CLI usage examples
   - API overview
2. Create QUICKSTART.md for new users
3. Update CHANGELOG.md with all changes
4. Create MIGRATION.md for upgrading from earlier versions
5. Add badges (CI, coverage, version)
6. Review and update contributing guidelines

**Dependencies**: All features complete

**Deliverables**:
- Updated README.md
- QUICKSTART.md
- Updated CHANGELOG.md
- MIGRATION.md

**Tests Required**:
- Link validation
- Example code verification
- Installation instruction testing

#### Sprint 10.5.2: API Reference Documentation

**Description**: Create comprehensive API reference documentation.

**Tasks**:
1. Generate API documentation from docstrings:
   - All public classes
   - All public functions
   - Configuration schemas
2. Create API usage guides:
   - IQA API guide
   - Layout-lite API guide
   - Routing API guide
   - Schema reference
3. Add code examples for common use cases
4. Create API changelog (breaking changes)
5. Set up documentation hosting (GitHub Pages or similar)
6. Implement documentation versioning

**Dependencies**: Sprint 10.5.1

**Deliverables**:
- `docs/api/` - API reference
- `docs/guides/` - Usage guides
- Documentation website configuration

**Tests Required**:
- Documentation build test
- Example code execution
- Link validation

#### Sprint 10.5.3: Operational Documentation

**Description**: Create operational documentation for production deployment.

**Tasks**:
1. Create deployment guide:
   - Prerequisites
   - Configuration options
   - Environment setup
   - GPU configuration
2. Create operations runbook:
   - Monitoring procedures
   - Alert handling
   - Troubleshooting guide
   - Recovery procedures
3. Create performance tuning guide:
   - Hardware recommendations
   - Configuration optimization
   - Batch size tuning
4. Create security documentation:
   - Input validation
   - Dependency management
   - Secrets handling
5. Final documentation review and polish
6. Create documentation index

**Dependencies**: Sprint 10.5.2

**Deliverables**:
- `docs/operations/` - Operational documentation
- `docs/deployment/` - Deployment guide
- Documentation index

**Tests Required**:
- Procedure verification
- Configuration validation
- Security review

---

## Summary

| Phase | Milestones | Total Sprints | Estimated Days |
|-------|------------|---------------|----------------|
| Phase 4 | 6 milestones (4.1-4.6) | 12 sprints | 12 days |
| Phase 6 | 4 milestones (6.1-6.4) | 10 sprints | 10 days |
| Phase 8 | 4 milestones (8.1-8.4) | 8 sprints | 8 days |
| Phase 10 | 5 milestones (10.1-10.5) | 9 sprints | 10 days |
| **Total** | **19 milestones** | **39 sprints** | **40 days** |

### Sprint Execution Guidelines

1. **Sequential Dependencies**: Sprints within a milestone should be completed sequentially unless explicitly noted as parallelizable.

2. **Cross-Phase Dependencies**:
   - Phase 6 (Layout-lite) can start after Phase 4 (Classical IQA) is 50% complete
   - Phase 8 (Routing) requires both Phase 4 and Phase 6 to be substantially complete
   - Phase 10 (Validation) should only start after all other phases are code-complete

3. **Quality Gates**:
   - Each sprint must pass all unit tests before completion
   - Each milestone must pass integration tests
   - Each phase must pass end-to-end validation

4. **Documentation Requirements**:
   - Each sprint should update relevant documentation
   - Each milestone should have a completion summary
   - Each phase should have updated architecture diagrams

5. **Code Review Requirements**:
   - All code changes require review
   - Security-sensitive code requires additional security review
   - Performance-critical code requires benchmark validation
