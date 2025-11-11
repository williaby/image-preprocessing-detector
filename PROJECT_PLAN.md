# Image Preprocessing Detection System - Comprehensive Project Plan

**Project**: Custom OpenCV-based Image Preprocessing Detection for RAG Applications
**Purpose**: Automated detection and correction of image quality issues and document elements before vector database ingestion
**Target**: Multi-page PDFs and images for downstream processing (LayoutParser → Tesseract/Marker/Docling)

---

## Executive Summary

This project builds an intelligent image preprocessing pipeline that analyzes documents (PDFs, images) and automatically detects required preprocessing steps before RAG ingestion. The system uses a **multi-stage pipeline architecture** combining classical computer vision techniques with modern deep learning models to achieve high accuracy while maintaining production-grade performance.

**Key Innovation**: Rather than a monolithic model, we employ a modular pipeline with a text-detection fork that routes images to specialized processing paths optimized for different document types.

**Expected Performance**: 6-15 pages/second per GPU worker, 50-150ms latency per page, with horizontal scalability to handle 1000s of pages/hour.

---

## System Architecture

### Overview: Multi-Stage Pipeline with Text Detection Fork

```
Input (PDF/Image)
    ↓
[1. Ingestion & Standardization]
    ↓ (Convert to 300 DPI images)
[2. Text Detection Gate]
    ↓                    ↓
[NO TEXT]           [TEXT DETECTED]
    ↓                    ↓
[3A. Image Quality   [3B. Document Element
    Assessment]          Detection]
    ↓                    ↓
[4. Correction & Output Generation]
    ↓
JSON Metadata for Downstream Processing
```

### Stage Breakdown

#### Stage 1: Ingestion & Standardization
- **Input Formats**: PDF, JPG, PNG, TIFF, etc.
- **Conversion**: PyMuPDF or pdf2image to convert PDFs → 300 DPI PNG images
- **Multi-page Handling**: Process each page individually, aggregate results
- **DPI Detection**: Check source DPI, flag if upscaling needed
- **Performance**: 30-120ms/page (CPU-bound)

#### Stage 2: Text Detection Gate
- **Primary Detector**: Ensemble approach
  - OpenCV EAST detector or DBNet-lite (lightweight)
  - Morphological stroke-density heuristic as backup
- **Decision Logic**:
  - Text detected → Route to Path B (Document Element Detection)
  - No text detected → Route to Path A (Image Quality Assessment)
- **Risk Mitigation**: Calibrate on validation set with aggressive augmentations (low-ink, halftone, fax scans) to minimize false negatives
- **Performance**: 3-8ms GPU / 20-40ms CPU

#### Stage 3A: Image Quality Assessment (No-Text Branch)

**Detection Categories:**
1. Noise
2. Blur
3. Skew/Rotation
4. Perspective Distortion
5. Low Contrast
6. Image Orientation

**Detection Methods:**

| Issue | Detection Method | Implementation |
|-------|------------------|----------------|
| Skew/Rotation | Classical CV | Hough Transform / Projection Profile |
| Low Contrast | Classical CV | Histogram analysis |
| Blur | Classical CV | Laplacian variance |
| Noise | ML Model | Multi-label CNN |
| Perspective | ML Model | Multi-label CNN |
| Orientation | ML Model | Multi-label CNN |

**ML Model**: Lightweight CNN (EfficientNet-B0 or MobileNetV3)
- **Architecture**: Multi-label classifier
- **Input**: 224x224 or 320x320 normalized image
- **Output**: Confidence scores for each issue type
- **Performance**: 1-3ms GPU / 8-15ms CPU

#### Stage 3B: Document Element Detection (Text Branch)

**Detection Categories:**
1. Tables
2. Images/Figures
3. Handwriting regions
4. Mathematical Formulas
5. Non-Latin characters (post-detection script identification)
6. Superscript/Footnotes (deferred to post-OCR)
7. **Revision Markings** (Yale manuscripts: strikethrough, insertions, margin notes)

**Handwriting Detection Methods (Phase 2)**

**Approach A: Noteshrink-Based Classical CV** (Recommended for Phase 2)
- **Algorithm**: K-means color clustering + HSV colorspace analysis
- **Background Separation**: Identify dominant paper color via k-means (8 clusters)
- **Ink Detection**: Pixels marked as foreground if:
  - Value differs > 0.3 from background OR
  - Saturation differs > 0.2 from background
- **Optimization**: 5% pixel sampling (20x speedup) via systematic sampling
- **Bit-Depth Reduction**: Convert 8-bit to 6-bit for noise-robust clustering
- **Output**: Binary handwriting mask + confidence score
- **Performance**: 10-20ms CPU (no GPU required)
- **Source**: Adapted from mzucker/noteshrink (2016)
- **Validation**: Tested on 56 handwriting samples (100% text detection, 38% skew rate)

**Approach B: SignaTR6K-Based Segmentation** (Phase 2+)
- **Dataset**: 6,257 annotated legal document crops (Thomson Reuters)
- **Content**: Overlapping handwritten + printed text, signatures, stamps
- **Format**: 256x256 crops with RGB pixel-wise segmentation masks
- **Train/Val/Test**: 5,169 / 530 / 558 splits
- **Model Options**: U-Net, DeepLabV3, or Mask R-CNN
- **Use Case**: Precise pixel-level handwriting segmentation when classical methods insufficient
- **Performance**: 5-15ms GPU (requires training infrastructure)

**Approach C: Hybrid Strategy** (Recommended)
- Phase 2: Noteshrink for fast binary detection
- Phase 3+: SignaTR6K segmentation for precise localization if needed
- Progressive enhancement as requirements evolve

**Object Detection Model: YOLOv8n/s**
- **Classes**: Table, Image, Handwriting, Formula
- **Input**: 640x640 image
- **Output**: Bounding boxes with class labels and confidence scores
- **Optimization**: INT8 quantization via ONNX/TensorRT (1.5-3x speedup)
- **Performance**: 2-7ms GPU / 25-70ms CPU

**Secondary Analysis (Heuristics)**
- **Non-Latin Script**: Lightweight OCR pass on detected text blocks → character-set identification
- **Superscript/Footnotes**: **Deferred to post-OCR** (analyze baseline shifts and font sizes from OCR output)

**Optimization Strategy**: Rule-first fast filters
- Propose "table-like" regions using connected components
- Run YOLO only on complex pages or when filters trigger
- Early exit on clean pages

#### Stage 4: Correction & Output Generation

**OpenCV Corrections Applied:**
| Issue | Correction Method | OpenCV Function |
|-------|-------------------|-----------------|
| Skew | Deskewing | cv2.warpAffine |
| Perspective | Perspective correction | cv2.warpPerspective |
| Blur | Sharpening | cv2.filter2D (unsharp mask) |
| Low Contrast | CLAHE | cv2.createCLAHE |
| Noise | Denoising | cv2.fastNlMeansDenoisingColored |
| Background | Normalization | cv2.morphologyEx |
| Low DPI | Upsampling | cv2.dnn_superres (Real-ESRGAN-x2-lite) |

**Correction Guardrails** (Do-No-Harm Principle):
- Apply confidence thresholds before correction
- Only deskew if angle > threshold AND variance improves
- Only apply CLAHE if low-contrast metric < threshold
- Track all corrections in transform_history for auditability

**Output Format**: JSON metadata per page, aggregated for multi-page documents

---

## Output JSON Schema

### Design Principles
- **COCO-aligned** for bounding boxes (easy LayoutParser integration)
- **Page-level diagnostics** for issue tracking
- **Transform history** for reproducibility and debugging
- **Compact and human-readable**

### Schema Structure

```json
{
  "document_id": "unique_doc_identifier",
  "file_name": "original_filename.pdf",
  "source_mime": "application/pdf",
  "num_pages": 5,
  "processing_version": {
    "pipeline_version": "1.0.0",
    "iqa_model_hash": "abc123...",
    "layout_model_hash": "def456...",
    "thresholds": {...},
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 200,
      "dpi_effective": 300,
      "detected_issues": [
        {
          "type": "blur",
          "confidence": 0.87,
          "severity": "medium",
          "metrics": {
            "laplacian_variance": 125.4
          }
        },
        {
          "type": "skew",
          "confidence": 0.92,
          "severity": "high",
          "metrics": {
            "angle_degrees": -3.2
          }
        }
      ],
      "planned_actions": [
        {
          "action": "deskew",
          "params": {"angle": -3.2},
          "confidence": 0.92,
          "reason": "skew_detected"
        },
        {
          "action": "sharpen",
          "params": {"kernel_size": 5, "alpha": 1.5},
          "confidence": 0.87,
          "reason": "blur_detected"
        }
      ],
      "elements": [
        {
          "id": "elem_001",
          "category": "table",
          "bbox": [150, 400, 1200, 600],
          "confidence": 0.94,
          "attributes": {}
        },
        {
          "id": "elem_002",
          "category": "handwriting",
          "bbox": [1500, 100, 300, 150],
          "confidence": 0.78,
          "attributes": {
            "handwriting_prob": 0.78
          }
        },
        {
          "id": "elem_003",
          "category": "formula",
          "bbox": [200, 2800, 800, 150],
          "confidence": 0.89,
          "attributes": {
            "formula_prob": 0.89
          }
        }
      ],
      "languages": [
        {
          "script": "Latin",
          "confidence": 0.98
        }
      ],
      "transform_history": [
        {
          "action": "deskew",
          "params": {"angle": -3.2},
          "started_at": "2025-01-15T10:30:01.123Z",
          "finished_at": "2025-01-15T10:30:01.145Z",
          "status": "success"
        },
        {
          "action": "sharpen",
          "params": {"kernel_size": 5, "alpha": 1.5},
          "started_at": "2025-01-15T10:30:01.150Z",
          "finished_at": "2025-01-15T10:30:01.167Z",
          "status": "success"
        }
      ]
    }
  ]
}
```

### Downstream Integration

**LayoutParser Handoff:**
- Consumes `elements` array as bounding boxes
- Receives corrected page image + metadata
- Coordinates in pixel space, origin (0,0) top-left

**Tesseract/Marker/Docling Integration:**
- Use `elements` to define ROIs for targeted OCR
- After OCR, persist hOCR/ALTO as separate artifacts
- Maintain mapping back to `page_index` and `element.id`

**Versioning & Reproducibility:**
- `processing_version` tracks model versions and thresholds
- `transform_history` provides full audit trail

---

## Training Data Strategy

### Critical Principle: Minimize Manual Annotation Burden

### Image Quality Assessment (IQA) Dataset

**Approach: Synthetic Data Generation + Weak Supervision**

**Data Sources:**
1. **Base Dataset**: Clean document images (10,000+ pages)
   - Publicly available document datasets (RVL-CDIP, Tobacco800)
   - Clean scanned documents from DocBank
   - Born-digital PDFs rendered at high DPI

2. **Synthetic Augmentation** (using Albumentations):
   - **Noise**: Gaussian noise, Poisson noise, salt-and-pepper
   - **Blur**: Gaussian blur, motion blur (various angles), defocus blur
   - **Low Contrast**: Histogram manipulation, brightness reduction
   - **Perspective**: Random perspective transform, slight rotations
   - **Real-world Artifacts**:
     - JPEG compression artifacts (ringing, blockiness)
     - Halftone dithering patterns
     - Uneven illumination gradients
     - Paper curl simulation
     - Fax/copier compression patterns

3. **Weak Supervision** (automated initial labeling):
   - Use BRISQUE/NIQE/PIQE scores for quality estimation
   - Laplacian variance for blur detection
   - Histogram spread for contrast issues
   - Snorkel-style label models to combine signals
   - **Manual validation** only on ambiguous samples (10-20% of dataset)

**Target Dataset Size**: 50,000 images (80% synthetic augmentation, 20% real-world validation)

**Validation/Test Split**: Real-world documents with genuine quality issues (manually curated, 2,000 pages)

### Document Element Detection Dataset

**Approach: Transfer Learning + Active Learning + Selective Annotation**

**Data Sources:**

1. **Public Datasets** (Bootstrap training):
   - **PubLayNet**: 360k+ layout-annotated pages (tables, figures, text)
   - **DocLayNet**: Multi-domain layout dataset
   - **ICDAR Competitions**: Table detection (ICDAR 2013, 2019), formula detection (CROHME)
   - **PubTables-1M**: Table structure recognition
   - **IAM Handwriting Database**: Handwriting samples
   - **IIIT-HWS**: Scene text and handwriting

2. **Custom Annotation** (Selective):
   - **Handwriting vs Print**: 1,000 manually labeled examples (focus on ambiguous cases)
   - **Mathematical Formulas**: 500 additional examples from domain-specific sources
   - **Multi-lingual Documents**: 500 examples with non-Latin scripts
   - **Tool**: CVAT or Label Studio

3. **Active Learning Pipeline**:
   - Train initial model on public datasets
   - Run inference on unlabeled corpus
   - Select high-uncertainty samples (low confidence, class imbalance)
   - Human annotate only selected samples
   - Retrain and iterate (3-4 cycles)

4. **Semi-automatic Labeling**:
   - Use PaddleOCR table detector to prelabel tables
   - Use PubTables-1M model for initial bounding boxes
   - Human correction on subset (validation only)

**Target Dataset Composition:**
- 300k+ pages from public datasets
- 3k custom-annotated pages (high-value, focused)
- Active learning to identify annotation priorities

**Class Distribution Target:**
- Tables: 40%
- Images/Figures: 30%
- Handwriting: 15%
- Mathematical Formulas: 10%
- Mixed/Complex: 5%

### Data Augmentation Strategy

**Training-time Augmentation** (Albumentations):
- Random crops, rotations (-5° to +5°)
- Color jittering, brightness/contrast adjustments
- Random shadows, paper texture overlays
- Slight perspective distortions
- Mixup / CutMix for robustness

**Domain Randomization**:
- Scanner noise patterns
- Photocopy degradation
- Camera capture artifacts (lighting, angle)
- Compression artifacts (JPEG, PDF)

---

## Model Architecture & Training

### Image Quality Assessment (IQA) Model

**Architecture**: Multi-label Classification CNN

**Model Options** (ranked by efficiency):
1. **MobileNetV3-Small** (preferred for CPU deployment)
2. **EfficientNet-B0** (balanced GPU/CPU)
3. **EfficientNet-B1** (higher accuracy if GPU-available)

**Training Configuration:**
```python
# Hyperparameters
INPUT_SIZE = 224  # or 320 for better accuracy
BATCH_SIZE = 32
LEARNING_RATE = 1e-3 (with cosine annealing)
OPTIMIZER = AdamW
EPOCHS = 50 (with early stopping)
LOSS = BCEWithLogitsLoss (multi-label)

# Data Split
TRAIN: 70% (35,000 images)
VALIDATION: 15% (7,500 images)
TEST: 15% (7,500 images - real-world only)

# Augmentation
Albumentations pipeline (see Training Data Strategy)
```

**Transfer Learning**:
- Start with ImageNet-pretrained weights
- Fine-tune all layers (after initial frozen epochs)

**Calibration**:
- Temperature scaling on validation set for confidence calibration
- Threshold tuning per issue type (optimize F1-score)

**Output**: 6 binary predictions with confidence scores
- Noise, Blur, Skew, Perspective, Low Contrast, Orientation

### Document Element Detection Model

**Architecture**: YOLOv8n or YOLOv8s

**Model Selection Criteria**:
- **YOLOv8n**: Fastest, suitable for CPU deployment (3-5ms GPU)
- **YOLOv8s**: More accurate, recommended if GPU-available (5-7ms GPU)

**Training Configuration:**
```python
# Hyperparameters
INPUT_SIZE = 640
BATCH_SIZE = 16
LEARNING_RATE = 1e-2 (with warmup)
OPTIMIZER = SGD (momentum=0.937, weight_decay=5e-4)
EPOCHS = 100 (with early stopping)
LOSS = YOLOv8 default (box + classification + objectness)

# Data Split
TRAIN: 80% (~240k images)
VALIDATION: 10% (~30k images)
TEST: 10% (~30k images - domain-diverse)

# Augmentation
Mosaic, MixUp, HSV augmentation, flips, rotations
```

**Transfer Learning**:
- Start with COCO-pretrained YOLOv8 weights
- Fine-tune on document-specific dataset

**Class Weights**:
- Apply inverse frequency weighting to handle class imbalance
- Oversample rare classes (handwriting, formulas)

**Optimization**:
- **Quantization**: INT8 via ONNX export + TensorRT
- **Pruning**: Optional for extreme CPU deployment
- **NMS Tuning**: Adjust IoU threshold for overlapping elements

**Output**: Bounding boxes with class labels
- Classes: Table, Image, Handwriting, Formula

---

## Evaluation Metrics & Benchmarks

### Image Quality Assessment (IQA) Evaluation

**Primary Metrics:**
1. **Per-Class Metrics**:
   - Precision, Recall, F1-Score for each issue type
   - ROC-AUC for each binary classification

2. **Overall Performance**:
   - **Mean Average Precision (mAP)** across all labels
   - **Subset Accuracy**: All labels correct for an image

3. **Calibration**:
   - **Expected Calibration Error (ECE)**: Confidence vs accuracy alignment
   - Reliability diagrams per issue type

**Secondary Metrics:**
- Confusion matrix analysis (identify common misclassifications)
- False positive rate per issue (critical for avoiding over-correction)

**Benchmark Targets:**
- **Per-class F1-Score**: > 0.85 (acceptable), > 0.90 (target)
- **mAP**: > 0.88
- **ECE**: < 0.05 (well-calibrated)

**Test Set**: Real-world documents only (no synthetic)

### Document Element Detection Evaluation

**Primary Metrics:**
1. **Object Detection Standard**:
   - **mAP@.50**: Mean Average Precision at 50% IoU
   - **mAP@.50-.95**: COCO primary metric (averaged across IoU thresholds)

2. **Per-Class Average Precision**:
   - AP for Table, Image, Handwriting, Formula individually
   - Ensures balanced performance across rare/common classes

**Secondary Metrics:**
- **Precision/Recall Curves**: Per class
- **Confusion Matrix**: Misclassification analysis
- **Inference Time**: Latency per image at batch size 1

**Benchmark Targets:**
- **mAP@.50**: > 0.75 (acceptable), > 0.82 (target)
- **Per-Class AP**: > 0.70 for all classes (ensure rare class performance)
- **Inference Time**: < 10ms GPU (YOLOv8n), < 25ms CPU

**Test Set**: Domain-diverse documents (academic, legal, technical, handwritten notes)

### End-to-End Pipeline Evaluation

**Metric: JSON Accuracy**
- Compare generated JSON against ground-truth JSON
- **Scoring**:
  - Issue detection: Precision, Recall, F1 per issue type
  - Element detection: mAP with IoU matching
  - Action planning: Precision (are planned actions correct?)

**Benchmark Target**:
- **JSON Accuracy**: > 0.85 (at least 85% of pages have correct metadata)

**Performance Metrics:**
1. **Latency**:
   - Target: < 150ms per page (GPU), < 400ms (CPU)
   - Measured: p50, p95, p99 latencies

2. **Throughput**:
   - Target: > 6 pages/sec per GPU worker
   - Horizontal scaling: Linear scalability to 100s of workers

3. **Resource Usage**:
   - GPU memory: < 2GB per worker
   - CPU cores: 2-4 per worker
   - RAM: < 4GB per worker

---

## Risk Assessment & Mitigation Strategies

### Critical Production Risks

#### 1. Text/No-Text Gating Errors
**Risk**: False negatives on faint/stylized text → wrong processing path
**Impact**: HIGH - Missed text detection leads to incorrect preprocessing
**Mitigation**:
- Ensemble gate: Morphological stroke-density + EAST/DBNet-lite
- Calibrate on validation set with aggressive augmentations (low-ink, halftone, fax)
- Add confidence threshold: If text gate is uncertain (0.4-0.6), run both paths and merge results
- Monitoring: Track text-gate confidence distribution in production

#### 2. Synthetic→Real Domain Gap
**Risk**: IQA model trained on synthetic augmentations fails on real-world artifacts
**Impact**: HIGH - Over-correction or missed issues
**Mitigation**:
- Seed with real-world noisy documents (20% of training set)
- Add artifact-specific augmentations: JPEG ringing, halftone, motion blur, uneven illumination
- Legacy scanner color casts and copier patterns
- Test on real-world holdout set exclusively
- Active learning: Mine production failures, add to training set

#### 3. Over-Correction Harm
**Risk**: Deskew, CLAHE, denoising applied when not needed → degrades OCR accuracy
**Impact**: MEDIUM-HIGH - Downstream OCR failures
**Mitigation**:
- Confidence thresholds per correction (only apply if high confidence)
- "Do-no-harm" guardrails: Measure image quality improvement before/after
  - Only deskew if angle > 2° AND variance improves by > 5%
  - Only apply CLAHE if low-contrast metric < threshold
- A/B testing: Compare OCR accuracy with/without corrections on validation set
- Preserve original images for rollback if needed

#### 4. Multi-Model Maintenance & Drift
**Risk**: Thresholds and models drift as document sources change
**Impact**: MEDIUM - Gradual accuracy degradation
**Mitigation**:
- Telemetry: Log confidence scores, issue frequencies, correction outcomes
- Periodic calibration: Recompute PR curves quarterly on fresh validation set
- Drift detection: Monitor feature distributions (e.g., KL divergence on image histograms)
- Scheduled reevaluation: Run against held-out change-detection set monthly
- Versioning: Track model versions in JSON output for reproducibility

#### 5. Throughput Bottlenecks
**Risk**: PDF rasterization and YOLO inference dominate latency
**Impact**: MEDIUM - Unable to meet throughput SLAs
**Mitigation**:
- Batch PDF rendering: PyMuPDF parallel processing
- GPU acceleration: YOLOv8 INT8 quantization (1.5-3x speedup)
- Async worker pool: Separate rasterization and inference queues
- Early exit: Skip heavy models on "clean" pages (no issues detected by fast heuristics)
- Horizontal scaling: Deploy multiple workers behind load balancer

#### 6. Non-Latin Script Detection Dependency
**Risk**: Script identification requires OCR, adds latency
**Impact**: LOW-MEDIUM - Increased processing time for multi-lingual docs
**Mitigation**:
- Lightweight OCR: Tesseract OEM 0 fast mode on text blocks only
- Alternative: Small CTC-based script classifier (< 5ms)
- Defer to post-OCR: Let downstream OCR handle script ID if latency-critical
- Cache: Detect script once per document, apply to all pages

#### 7. Multi-Page Memory/IO Pressure
**Risk**: Large PDFs (100+ pages) cause memory spikes
**Impact**: MEDIUM - OOM crashes, system instability
**Mitigation**:
- Stream pages: Process one page at a time, don't load entire PDF
- Avoid intermediate writes: Keep images in memory until final output
- Cap concurrent pages: Limit worker pool size based on available memory
- Resource monitoring: Alert on memory usage > 80%

---

## Implementation Roadmap

### Phase 0: Foundation & Scaffolding (2-3 weeks)

**Goals:**
- Establish project structure, CI/CD, and evaluation framework
- Define JSON schema and telemetry hooks
- Create test harness for "JSON Accuracy" metric

**Tasks:**
1. **Project Setup**
   - Initialize repository with Poetry for dependency management
   - Set up pre-commit hooks (Black, Ruff, MyPy, Markdownlint)
   - Configure CI/CD pipeline (GitHub Actions or GitLab CI)
   - Security: GPG key validation, dependency scanning (Safety, Bandit)

2. **Data Infrastructure**
   - Define JSON schema (see Output JSON Schema section)
   - Implement JSON serialization/deserialization utilities
   - Create ground-truth annotation tool for test set labeling
   - Set up data versioning with DVC (Data Version Control)

3. **Evaluation Framework**
   - Implement "JSON Accuracy" metric computation
   - Create test harness: Load ground-truth JSONs, compare with predictions
   - Build evaluation dashboard (Streamlit or Gradio)
   - Telemetry hooks: Log confidence scores, latencies, resource usage

4. **Documentation**
   - Architecture diagrams (Mermaid or draw.io)
   - API documentation (Sphinx with autodoc)
   - Dataset documentation (sources, licenses, statistics)

**Deliverables:**
- ✅ Repository with CI/CD pipeline
- ✅ JSON schema v1.0 with validation tests
- ✅ Evaluation framework with test harness
- ✅ 500-page ground-truth test set (manually annotated)

**Success Criteria:**
- Test harness can compute JSON Accuracy on sample data
- CI/CD pipeline passes all linting and security checks

---

### Phase 1: MVP with Classical Methods (3-4 weeks)

**Goals:**
- Implement functional pipeline with classical CV methods
- Validate end-to-end workflow from PDF to JSON
- Establish performance baseline

**Tasks:**

1. **PDF/Image Ingestion** ([src/ingestion/](src/ingestion/))
   - File format detection and validation
   - PDF to image conversion (PyMuPDF)
   - DPI detection and upscaling logic
   - Multi-page document handling

2. **Text Detection Gate** ([src/detection/text_gate.py](src/detection/text_gate.py))
   - Implement morphological stroke-density heuristic
   - Integrate OpenCV EAST detector
   - Ensemble logic with confidence thresholding
   - Calibration on validation set

3. **Classical IQA Detectors** ([src/detection/iqa_classical.py](src/detection/iqa_classical.py))
   - **Skew Detection**: Hough Transform / Projection Profile
   - **Low Contrast**: Histogram analysis (variance, range)
   - **Blur Detection**: Laplacian variance
   - **Orientation**: Histogram of oriented gradients (HOG)
   - Confidence scoring per detector

4. **Correction Pipeline** ([src/correction/](src/correction/))
   - Deskew: cv2.warpAffine with rotation matrix
   - CLAHE: cv2.createCLAHE on L channel (LAB color space)
   - Sharpening: Unsharp mask (cv2.filter2D)
   - Denoising: cv2.fastNlMeansDenoisingColored
   - Background normalization: Morphological operations
   - **Guardrails**: Confidence thresholds, do-no-harm checks

5. **Output Generation** ([src/output/json_generator.py](src/output/json_generator.py))
   - JSON schema implementation
   - Per-page metadata aggregation
   - Multi-page document assembly
   - Transform history logging

6. **CLI Tool** ([src/cli.py](src/cli.py))
   - Command-line interface for single-file processing
   - Batch processing support
   - Output directory management

**Deliverables:**
- ✅ End-to-end pipeline: PDF → JSON output
- ✅ Classical detectors with confidence scores
- ✅ Correction pipeline with guardrails
- ✅ CLI tool for testing

**Success Criteria:**
- Pipeline processes 100-page PDF without errors
- JSON Accuracy > 0.60 on test set (baseline)
- Latency < 500ms per page (CPU-only)

**Benchmark Results** (Expected):
| Metric | Target | Notes |
|--------|--------|-------|
| Skew Detection Accuracy | > 0.90 | Classical methods excel here |
| Contrast Detection | > 0.85 | Histogram analysis reliable |
| Blur Detection | > 0.75 | Laplacian variance has limitations |
| Overall JSON Accuracy | > 0.60 | Baseline for ML improvement |

---

### Phase 1B: PDF Resolution Pre-processing & DPI Upscaling (1-2 weeks)

**Goals:**
- Implement automatic DPI detection for PDF pages and images
- Add upscaling capability for low-resolution documents (<300 DPI)
- Seamlessly integrate with ingestion pipeline
- Ensure OCR-ready quality for downstream processing

**Background:**
This phase incorporates proven upscaling technology from the data_ingestor project (Phase 1C), which achieved 100% test success rate and 310-360ms processing time. The implementation uses OpenCV-based upscaling algorithms optimized for document processing.

**Tasks:**

1. **DPI Detection Module** ([src/ingestion/pdf_resolution.py](src/ingestion/pdf_resolution.py))
   - PyMuPDF-based DPI analysis for PDF pages
   - Image metadata extraction for raster formats (PNG, JPEG, TIFF)
   - Multi-page DPI analysis with per-page resolution reporting
   - Edge case handling: zero bbox, no images, password-protected PDFs
   - Confidence scoring for DPI measurements

2. **PDF Upscaling Module** ([src/ingestion/pdf_upscaler.py](src/ingestion/pdf_upscaler.py))
   - **OpenCV Upscaling Algorithms**:
     - `lanczos` - Best quality (recommended for production)
     - `bicubic` - Balanced speed/quality (development)
     - `inter_linear` - Fastest (performance-critical workflows)
     - `inter_cubic` - Alternative high-quality option
     - `inter_area` - Downsampling (for oversized images)
   - Page-by-page processing to minimize memory usage (<2GB)
   - Temporary file management with automatic cleanup
   - Error handling with graceful fallback to original
   - File size tracking and optimization
   - Progress logging for large documents

3. **Pre-flight Analysis Orchestrator** ([src/ingestion/pdf_analyzer.py](src/ingestion/pdf_analyzer.py))
   - Coordinate DPI detection and upscaling workflow
   - Decision logic: When to upscale vs use original
   - Metadata generation for upscaling operations
   - Integration with document router
   - Cleanup coordination for temporary files

4. **Configuration Integration** ([src/core/config.py](src/core/config.py))
   - Add 5 new settings:
     - `enable_pdf_upscaling: bool = True`
     - `pdf_min_dpi: int = 300`
     - `pdf_target_dpi: int = 300`
     - `pdf_upscale_algorithm: str = "lanczos"`
     - `pdf_preserve_original_on_error: bool = True`
   - Environment variable support
   - Configuration validation

5. **Pipeline Integration** ([src/ingestion/](src/ingestion/))
   - Integrate PDFDocumentAnalyzer into ingestion pipeline
   - Pre-flight analysis before image conversion
   - Automatic upscaling for low-DPI documents
   - Metadata tracking in DocumentMetadata schema
   - Update `transform_history` with upscaling operations

6. **Dependencies & Infrastructure**
   - Add required dependencies to `pyproject.toml`:
     - `opencv-python-headless = "^4.10.0"` (already present)
     - `pillow = ">=10.1.0,<11.0.0"` (already present)
     - `numpy = ">=1.26.1,<2.0.0"` (already present)
   - Update environment configuration templates
   - Add upscaling metrics to telemetry

7. **Testing** ([tests/unit/](tests/unit/), [tests/integration/](tests/integration/))
   - **Unit Tests** (26+ tests):
     - Resolution detection (12 tests)
       - Low-resolution detection
       - High-resolution detection
       - Multi-page analysis
       - Edge cases (zero bbox, no images)
       - Error handling
     - Upscaling (14 tests)
       - All 5 algorithms
       - Success cases
       - Error handling
       - File size tracking
       - Convenience functions
   - **Integration Tests** (8+ tests):
     - End-to-end upscaling workflow
     - Pipeline integration
     - Configuration respect
     - Metadata accuracy
     - Performance validation
     - Cleanup verification

8. **Validation Tools** ([scripts/validate_pdf_resolution.py](scripts/validate_pdf_resolution.py))
   - Manual validation script for DPI detection
   - Upscaling quality assessment
   - Before/after comparison utilities
   - Batch processing for test datasets

**Deliverables:**
- ✅ DPI detection module with 100% accuracy
- ✅ PDF upscaling module with 5 algorithm options
- ✅ Pre-flight analysis orchestrator
- ✅ Configuration integration with environment variables
- ✅ Pipeline integration with metadata tracking
- ✅ Comprehensive test suite (26+ unit tests, 8+ integration tests)
- ✅ Validation scripts for manual testing

**Success Criteria:**
- DPI detection accuracy: 100% on test PDFs
- Upscaling quality: >10% OCR improvement (150→300 DPI = 100% improvement)
- Processing time: <500ms per document (target: 310-360ms)
- Memory usage: <2GB per worker (page-by-page processing)
- Test coverage: 100% pass rate on all upscaling tests
- No quality regression on high-resolution documents (correctly skipped)
- Automatic cleanup: No orphaned temporary files

**Performance Benchmarks** (Expected):
| Metric | Target | Notes |
|--------|--------|-------|
| DPI Detection Accuracy | 100% | PyMuPDF metadata extraction |
| Processing Time | <500ms | 310-360ms achieved in data_ingestor |
| Memory Usage | <2GB | Page-by-page processing |
| DPI Improvement | >10% | 150→300 DPI = 100% improvement |
| Test Success Rate | 100% | All 34+ tests passing |
| Cleanup Success Rate | 100% | No orphaned temp files |

**Configuration Examples:**

**Production Settings:**
```python
enable_pdf_upscaling = True
pdf_min_dpi = 300                    # Standard OCR threshold
pdf_target_dpi = 300                 # Match OCR requirements
pdf_upscale_algorithm = "lanczos"    # Best quality
pdf_preserve_original_on_error = True # Safety fallback
```

**Development Settings:**
```python
enable_pdf_upscaling = True
pdf_min_dpi = 200                    # More lenient for testing
pdf_target_dpi = 300
pdf_upscale_algorithm = "bicubic"    # Faster for iteration
pdf_preserve_original_on_error = True
```

**Performance-Critical Settings:**
```python
enable_pdf_upscaling = True
pdf_min_dpi = 250                    # Slightly lower threshold
pdf_target_dpi = 300
pdf_upscale_algorithm = "inter_linear" # Fastest
pdf_preserve_original_on_error = True
```

**Integration Notes:**

**Source Code Reference:**
All implementation code is available in the data_ingestor project:
- `/home/byron/dev/data_ingestor/src/data_ingestor/utils/pdf_resolution.py` (196 lines)
- `/home/byron/dev/data_ingestor/src/data_ingestor/utils/pdf_upscaler.py` (289 lines)
- `/home/byron/dev/data_ingestor/src/data_ingestor/pipeline/pdf_analyzer.py` (242 lines)

**Handoff Documentation:**
See `/home/byron/dev/data_ingestor/docs/PHASE1C_HANDOFF.md` for complete integration guide.

**Edge Cases Handled:**
- ✅ Password-protected PDFs → Skip upscaling, use original
- ✅ Corrupted PDFs → Graceful error, use original
- ✅ PDFs with no images → Skip upscaling, use original
- ✅ Very large PDFs (>500MB) → Page-by-page processing
- ✅ High-resolution PDFs → Correctly skipped (no unnecessary processing)

**Dependencies on Phase 1:**
- Requires basic ingestion pipeline (PDF→image conversion)
- Integrates with DocumentMetadata schema
- Extends transform_history tracking

**Enables Phase 2+:**
- Ensures consistent 300 DPI input for IQA models
- Improves OCR quality for downstream processing
- Provides metadata for quality assessment validation

---

### Phase 2: ML for Image Quality Assessment (3-4 weeks)

**Goals:**
- Train and deploy multi-label IQA CNN
- Improve detection accuracy for noise, blur, perspective
- Replace or augment classical methods

**Tasks:**

1. **Data Collection & Augmentation**
   - Collect 10k clean document images
   - Build Albumentations augmentation pipeline
   - Generate 50k synthetic augmented images
   - Weak supervision: BRISQUE/NIQE scores for initial labels
   - Manual validation on 10k ambiguous samples

2. **Model Training** ([models/iqa/](models/iqa/))
   - Implement MobileNetV3-Small and EfficientNet-B0
   - Training loop with early stopping, checkpointing
   - Hyperparameter tuning (learning rate, batch size)
   - Cross-validation on real-world validation set

3. **Model Evaluation**
   - Compute per-class Precision, Recall, F1, ROC-AUC
   - Mean Average Precision (mAP)
   - Calibration: ECE, reliability diagrams
   - Confusion matrix analysis

4. **Model Optimization**
   - Temperature scaling for calibration
   - Threshold tuning per issue type (maximize F1)
   - ONNX export for CPU inference
   - Quantization: INT8 via ONNX Runtime

5. **Integration** ([src/detection/iqa_ml.py](src/detection/iqa_ml.py))
   - Load ONNX model in inference pipeline
   - Ensemble with classical methods (voting or confidence-weighted)
   - A/B testing: Compare classical vs ML vs ensemble
   - Update confidence thresholds for correction pipeline

**Deliverables:**
- ✅ Trained IQA model (ONNX format)
- ✅ Training dataset (50k images, versioned with DVC)
- ✅ Evaluation report with benchmark metrics
- ✅ Integrated ML detection in pipeline

**Success Criteria:**
- mAP > 0.88 on test set
- Per-class F1 > 0.85 for all issues
- ECE < 0.05 (well-calibrated)
- JSON Accuracy > 0.75 (improvement from Phase 1)
- Latency < 200ms per page (CPU with ONNX)

**Benchmark Results** (Expected):
| Issue Type | F1-Score | Notes |
|------------|----------|-------|
| Noise | > 0.90 | ML excels vs classical |
| Blur | > 0.88 | Improved from classical |
| Skew | > 0.92 | Ensemble with classical |
| Perspective | > 0.87 | ML handles complex cases |
| Low Contrast | > 0.90 | Ensemble with histogram |
| Orientation | > 0.93 | CNN handles rotations well |

---

### Phase 3: ML for Document Layout Detection (4-5 weeks)

**Goals:**
- Train and deploy YOLOv8 object detector for document elements
- Integrate with pipeline for text-detected documents
- Achieve production-ready accuracy and performance

**Tasks:**

1. **Dataset Preparation**
   - Download and preprocess public datasets:
     - PubLayNet (360k pages)
     - DocLayNet (multi-domain)
     - ICDAR table/formula datasets
     - IAM/IIIT-HWS handwriting datasets
   - Convert to YOLO format (class, x_center, y_center, width, height)
   - Data cleaning: Remove low-quality annotations
   - Class mapping: Consolidate to target classes (Table, Image, Handwriting, Formula)

2. **Custom Annotation** ([data/custom_annotations/](data/custom_annotations/))
   - Set up CVAT or Label Studio
   - Annotate 1000 handwriting examples (ambiguous cases)
   - Annotate 500 formula examples (domain-specific)
   - Annotate 500 multi-lingual documents (non-Latin scripts)
   - Quality control: Inter-annotator agreement checks

3. **Active Learning Pipeline** ([scripts/active_learning.py](scripts/active_learning.py))
   - Train baseline model on public datasets
   - Inference on unlabeled corpus
   - Select high-uncertainty samples (low confidence, low mAP classes)
   - Human annotate selected samples (500-1000)
   - Retrain and iterate (3-4 cycles)

4. **Model Training** ([models/layout/](models/layout/))
   - YOLOv8n and YOLOv8s training configurations
   - Transfer learning from COCO-pretrained weights
   - Class weighting for imbalance handling
   - Hyperparameter tuning: NMS threshold, confidence threshold
   - Model ensemble: Average predictions from multiple checkpoints

5. **Model Evaluation**
   - mAP@.50 and mAP@.50-.95
   - Per-class Average Precision
   - Precision/Recall curves
   - Inference time benchmarking

6. **Model Optimization**
   - ONNX export with dynamic shapes
   - INT8 quantization via TensorRT
   - Pruning for CPU deployment (optional)
   - Batch inference support

7. **Integration** ([src/detection/layout_detector.py](src/detection/layout_detector.py))
   - Load YOLOv8 model (PyTorch or ONNX)
   - Bounding box post-processing: NMS, confidence filtering
   - Element metadata generation (attributes, confidence)
   - Rule-first fast filters: Pre-filter pages for YOLO triggering
   - Early exit on clean pages

**Deliverables:**
- ✅ Trained YOLOv8 model (PyTorch + ONNX)
- ✅ Document element dataset (300k+ images, versioned)
- ✅ Evaluation report with per-class AP
- ✅ Integrated layout detector in pipeline
- ✅ Active learning scripts for continuous improvement

**Success Criteria:**
- mAP@.50 > 0.82 on test set
- Per-class AP > 0.70 for all classes (including rare classes)
- Inference time < 10ms GPU (YOLOv8n), < 70ms CPU (ONNX INT8)
- JSON Accuracy > 0.85 (end-to-end pipeline)
- Throughput > 6 pages/sec per GPU worker

**Benchmark Results** (Expected):
| Element Type | AP@.50 | Notes |
|--------------|--------|-------|
| Table | > 0.88 | Abundant training data |
| Image | > 0.85 | Clear visual features |
| Handwriting | > 0.75 | Challenging, improved with custom data |
| Formula | > 0.78 | Rare class, active learning critical |

---

### Phase 4: Advanced Features & Production Hardening (3-4 weeks)

**Goals:**
- Implement secondary analysis (non-Latin scripts, superscript/footnotes)
- Optimize for production performance and scalability
- Deploy containerized service with API

**Tasks:**

1. **Secondary Analysis** ([src/detection/](src/detection/))
   - **Non-Latin Script Detection**:
     - Integrate lightweight OCR (Tesseract fast mode)
     - Character-set identification on text blocks
     - Unicode range analysis (Latin vs CJK vs Arabic, etc.)
   - **Superscript/Footnote Detection** (Post-OCR):
     - Parse OCR output (hOCR or ALTO XML)
     - Analyze baseline shifts and font sizes
     - Flag superscript/subscript characters
     - Identify footnote regions by position and size

2. **Performance Optimization** ([src/optimization/](src/optimization/))
   - **Profiling**: cProfile, line_profiler on critical paths
   - **Bottleneck Analysis**: Identify CPU vs GPU vs IO bounds
   - **Optimizations**:
     - Batch inference: Process multiple pages in parallel
     - Pinned memory: Zero-copy transfers for GPU
     - Async IO: Separate rasterization and inference queues
     - Early exit: Skip models on clean pages
     - Cache: DPI detection, rendered images
   - **Quantization**: TensorRT INT8 for YOLO and IQA models

3. **Worker Pool Architecture** ([src/workers/](src/workers/))
   - Async worker pool with Celery or RQ
   - Work queue with backpressure handling
   - Resource monitoring and caps (memory, GPU)
   - Graceful degradation: Fallback to CPU if GPU unavailable

4. **API Development** ([src/api/](src/api/))
   - FastAPI service with endpoints:
     - POST /process: Single file upload
     - POST /batch: Batch file upload
     - GET /status/{job_id}: Job status polling
     - GET /result/{job_id}: Download JSON result
   - Input validation: File size limits, format checks
   - Authentication: API key-based auth
   - Rate limiting: Per-user quotas

5. **Deployment** ([docker/](docker/))
   - Dockerfile for service container
   - Docker Compose for local development
   - Kubernetes manifests for production (optional)
   - Environment configuration (env vars for model paths, thresholds)
   - Health checks and readiness probes
   - Logging: Structured JSON logs (Python logging)
   - Monitoring: Prometheus metrics (latency, throughput, errors)

6. **Testing** ([tests/](tests/))
   - Unit tests: 80%+ coverage (pytest)
   - Integration tests: End-to-end pipeline tests
   - Performance tests: Latency and throughput benchmarks
   - Regression tests: JSON Accuracy on holdout set

7. **Documentation**
   - API documentation: OpenAPI/Swagger
   - Deployment guide: Docker and Kubernetes
   - Model documentation: Architecture, training details, performance
   - User guide: Example usage, output format explanation

**Deliverables:**
- ✅ Full-featured pipeline with secondary analysis
- ✅ Optimized inference (batching, quantization, early exit)
- ✅ FastAPI service with Docker container
- ✅ Comprehensive test suite (80%+ coverage)
- ✅ Production-ready documentation

**Success Criteria:**
- JSON Accuracy > 0.85 on diverse test set
- Latency p95 < 150ms per page (GPU), < 400ms (CPU)
- Throughput > 10 pages/sec per GPU worker (batch=4)
- Test coverage > 80%
- Container image < 2GB

**Performance Benchmarks** (Expected):
| Configuration | Latency (p95) | Throughput | Notes |
|---------------|---------------|------------|-------|
| GPU (T4) | 120ms | 12 pages/sec | YOLOv8n INT8, batch=4 |
| GPU (A10) | 80ms | 18 pages/sec | YOLOv8s INT8, batch=8 |
| CPU (8 cores) | 350ms | 3 pages/sec | ONNX INT8, single page |

---

### Phase 5: Production Operations, Monitoring & Continuous Improvement (Ongoing)

**Timeline**: Ongoing (starts Week 21)
**Status**: 📋 PLANNED

**Goals:**
- Establish comprehensive production monitoring, observability, and alerting infrastructure
- Implement automated drift detection and model performance tracking
- Build continuous improvement pipeline with data flywheel and active learning
- Achieve operational excellence with SRE practices and incident response
- Optimize costs and resource utilization while maintaining SLAs
- Enable rapid experimentation with A/B testing and canary deployments

---

## Phase 5 Overview

Phase 5 is the operational phase that ensures long-term system health, continuous improvement, and production excellence. Unlike earlier phases focused on building features, Phase 5 establishes the infrastructure and processes for maintaining and evolving the system over time.

### Phase 5 Sub-Phases

```
Phase 5A: Operational Foundation (Weeks 21-24)
    → Monitoring, logging, alerting infrastructure

Phase 5B: Intelligence & Automation (Weeks 25-32)
    → Drift detection, data flywheel, MLOps automation

Phase 5C: Optimization & Scale (Weeks 33-40)
    → Cost optimization, advanced features, scale testing

Phase 5D: Ongoing Operations (Week 41+)
    → Continuous monitoring, quarterly retraining, incident response
```

---

## Phase 5A: Operational Foundation (Weeks 21-24, 4 weeks)

### Objectives

Establish core production infrastructure for monitoring, logging, and alerting.

### Tasks

#### 1. Observability Infrastructure ([monitoring/](monitoring/))

**Prometheus Metrics Collection:**
- Service-level metrics:
  - Request rate, error rate, duration (RED metrics)
  - p50, p95, p99, p999 latency histograms
  - Throughput (pages/sec, requests/sec)
  - Queue depth and processing backlog
- Model-level metrics:
  - Inference time per model (IQA, layout detection)
  - Confidence score distributions
  - Issue detection frequencies (blur, skew, noise, etc.)
  - Element detection frequencies (tables, images, handwriting)
- Resource metrics:
  - GPU utilization, memory usage, temperature
  - CPU utilization per worker
  - Memory usage (RSS, heap, GPU VRAM)
  - Disk I/O for temporary files
- Business metrics:
  - Pages processed per hour/day/month
  - Processing cost per page
  - Error recovery success rate

**Grafana Dashboards:**
- **Operations Dashboard**:
  - Service health overview (uptime, error rate)
  - Real-time latency and throughput
  - Queue depth and worker status
  - Resource utilization trends
- **Model Performance Dashboard**:
  - Confidence score distributions over time
  - Issue/element detection frequency trends
  - Per-model inference time trends
  - Correction application rates
- **Business Dashboard**:
  - Processing volume and trends
  - Cost per page metrics
  - SLA compliance (latency, throughput)
  - User-reported issues tracking

**Alerting Rules:**
```yaml
# Example Prometheus alerting rules
groups:
  - name: preprocessing_service
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m])) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "p95 latency above 500ms for 10 minutes"

      - alert: GPUMemoryHigh
        expr: gpu_memory_used_bytes / gpu_memory_total_bytes > 0.90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU memory usage above 90%"
```

**Implementation:**
```bash
# Monitoring stack deployment
docker-compose -f monitoring/docker-compose.yml up -d
  - Prometheus (metrics storage)
  - Grafana (dashboards)
  - AlertManager (alert routing)
  - Node Exporter (system metrics)
  - NVIDIA DCGM Exporter (GPU metrics)
```

---

#### 2. Structured Logging Infrastructure ([src/telemetry/logging.py](src/telemetry/logging.py))

**Log Collection Architecture:**
```
Application (structlog)
    ↓ (JSON logs)
Filebeat / Fluentd
    ↓
Loki / Elasticsearch
    ↓
Grafana / Kibana (visualization)
```

**Structured Log Format:**
```json
{
  "timestamp": "2025-01-15T10:30:01.123Z",
  "level": "INFO",
  "logger": "preprocessing.detection.iqa",
  "correlation_id": "req-abc123",
  "document_id": "doc-xyz789",
  "page_index": 2,
  "event": "issue_detected",
  "issue_type": "blur",
  "confidence": 0.87,
  "processing_time_ms": 45,
  "model_version": "iqa-v1.2.0",
  "worker_id": "worker-03",
  "gpu_id": 0
}
```

**Log Levels and Usage:**
- **DEBUG**: Detailed tracing (disabled in production)
- **INFO**: Normal operations (issue detected, correction applied)
- **WARNING**: Recoverable issues (low confidence, fallback used)
- **ERROR**: Processing failures (model error, IO error)
- **CRITICAL**: Service failures (OOM, GPU crash)

**Correlation ID Tracking:**
- Generate unique ID per document/request
- Propagate through entire pipeline
- Enable end-to-end tracing across services

**Log Retention:**
- Hot storage: 7 days (fast queries)
- Warm storage: 30 days (standard queries)
- Cold storage: 1 year (compliance, long-term analysis)

---

#### 3. Distributed Tracing ([monitoring/tracing/](monitoring/tracing/))

**Technology**: Jaeger or Grafana Tempo

**Span Structure:**
```
Document Processing (root span)
├── PDF Ingestion (10ms)
├── Text Detection Gate (5ms)
├── Layout Detection (25ms)
│   ├── YOLOv8 Inference (20ms)
│   └── Post-processing (5ms)
├── IQA per Element (30ms)
│   ├── Element 1 IQA (10ms)
│   ├── Element 2 IQA (10ms)
│   └── Element 3 IQA (10ms)
├── Correction Pipeline (40ms)
│   ├── Deskew (15ms)
│   ├── CLAHE (10ms)
│   └── Sharpening (15ms)
└── JSON Output (5ms)

Total: 115ms
```

**Tracing Benefits:**
- Identify bottlenecks in pipeline
- Track latency across distributed workers
- Debug slow requests with detailed traces
- Optimize resource allocation

---

#### 4. Error Tracking & Incident Management ([monitoring/errors/](monitoring/errors/))

**Sentry Integration:**
- Automatic error capture with stack traces
- Error grouping and deduplication
- User impact tracking (affected documents)
- Release tracking (correlate errors with deployments)

**Error Categories:**
```python
# Custom error contexts
with sentry_sdk.push_scope() as scope:
    scope.set_context("document", {
        "id": doc_id,
        "page_count": num_pages,
        "source_dpi": dpi,
        "file_size_mb": file_size
    })
    scope.set_context("model", {
        "iqa_version": iqa_version,
        "layout_version": layout_version,
        "onnx_runtime_version": onnx_version
    })
    # Process document (errors auto-captured)
```

**On-Call Rotation:**
- Set up PagerDuty or Opsgenie integration
- Define escalation policies (critical → page immediately, warning → email)
- Create runbooks for common incidents
- Schedule on-call rotation (weekly or bi-weekly)

---

#### 5. Health Checks & Readiness Probes

**Kubernetes Health Endpoints:**
```python
# FastAPI health check endpoints
@app.get("/health")
async def health():
    """Liveness probe - is service running?"""
    return {"status": "healthy", "timestamp": utcnow()}

@app.get("/ready")
async def ready():
    """Readiness probe - can service handle requests?"""
    checks = {
        "models_loaded": check_models_loaded(),
        "gpu_available": check_gpu_available(),
        "disk_space": check_disk_space(),
        "queue_healthy": check_queue_depth()
    }
    ready = all(checks.values())
    status = "ready" if ready else "not_ready"
    return {"status": status, "checks": checks}
```

**Health Check Criteria:**
- All models loaded successfully
- GPU accessible (if GPU deployment)
- Sufficient disk space (> 10% free)
- Queue depth below threshold (< 1000 pending)
- Recent successful processing (within last 60s)

---

### Deliverables (Phase 5A)

- ✅ Prometheus + Grafana monitoring stack deployed
- ✅ 3 Grafana dashboards (Operations, Model Performance, Business)
- ✅ Alerting rules configured and tested
- ✅ Structured logging with Loki/Elasticsearch
- ✅ Distributed tracing with Jaeger/Tempo
- ✅ Sentry error tracking integrated
- ✅ Health check endpoints implemented
- ✅ On-call rotation and runbooks established

### Success Criteria (Phase 5A)

- Mean time to detection (MTTD) < 5 minutes for critical issues
- Mean time to recovery (MTTR) < 30 minutes for service outages
- 100% of critical alerts delivered within 2 minutes
- Log query performance < 1 second for recent logs (7 days)
- Distributed traces available for all requests
- Dashboard load time < 2 seconds

---

## Phase 5B: Intelligence & Automation (Weeks 25-32, 8 weeks)

### Objectives

Implement automated drift detection, data flywheel, and MLOps pipeline for continuous improvement.

### Tasks

#### 1. Model Drift Detection ([src/monitoring/drift.py](src/monitoring/drift.py))

**Feature Distribution Monitoring:**

**Image Statistics Tracking:**
```python
# Track distribution of image properties
image_features = {
    "mean_brightness": np.mean(image),
    "std_brightness": np.std(image),
    "entropy": scipy.stats.entropy(histogram),
    "edge_density": cv2.Canny(image).sum() / image.size,
    "color_variance": np.var(image, axis=(0,1)),
}

# Compute KL divergence from training distribution
kl_divergence = compute_kl(production_dist, training_dist)
if kl_divergence > threshold:
    alert("Feature drift detected", kl_divergence)
```

**Confidence Score Distribution Monitoring:**
```python
# Track confidence scores per issue type
confidence_stats = {
    "blur": {
        "mean": 0.65,
        "std": 0.20,
        "p50": 0.68,
        "p95": 0.92,
        "distribution": histogram
    }
}

# Alert if distribution shifts significantly
if wasserstein_distance(current, baseline) > threshold:
    alert("Confidence distribution drift", issue_type)
```

**Performance Metrics Tracking:**
```python
# Weekly evaluation on held-out change-detection set
weekly_metrics = {
    "iqa_map": 0.89,  # down from 0.91 baseline
    "layout_map50": 0.84,  # stable
    "json_accuracy": 0.86  # down from 0.88 baseline
}

# Alert if mAP drops > 5%
if current_map < baseline_map * 0.95:
    alert("Model performance degradation", current_map)
```

**Drift Detection Dashboard:**
- Feature distribution plots (training vs production)
- Confidence score trends over time
- Performance metrics trend (weekly mAP, F1)
- Drift alerts and resolution timeline

---

#### 2. Data Flywheel & Active Learning ([scripts/continuous_improvement/](scripts/continuous_improvement/))

**Data Collection Pipeline:**
```python
# Automatic failure collection
def collect_failures():
    """Mine production data for labeling candidates"""
    candidates = []

    # Low confidence samples
    low_conf = query_db("confidence < 0.70")
    candidates.extend(sample(low_conf, 100))

    # User-reported errors
    user_errors = query_db("user_feedback = 'incorrect'")
    candidates.extend(user_errors)

    # High-uncertainty samples
    high_uncertainty = query_db("entropy > threshold")
    candidates.extend(sample(high_uncertainty, 100))

    # Class imbalance (rare classes)
    rare_classes = ["handwriting", "formula"]
    for cls in rare_classes:
        rare_samples = query_db(f"element_type = {cls}")
        candidates.extend(sample(rare_samples, 50))

    return candidates
```

**Active Learning Workflow:**
```
Week 1-4: Collect production failures (auto + manual reporting)
    ↓
Week 5: Mine high-value samples (500 candidates)
    ↓
Week 6: Human annotation (CVAT, 2 annotators for agreement)
    ↓
Week 7: Add to training set, trigger retraining pipeline
    ↓
Week 8: Evaluate new model, A/B test if passing
    ↓
Week 9-12: Gradual rollout, monitor metrics
```

**Annotation Interface:**
- Use CVAT or Label Studio for annotation
- Pre-populate with model predictions (faster annotation)
- Inter-annotator agreement checks (Cohen's kappa > 0.80)
- Quality control: 10% of annotations reviewed by expert

**Training Set Versioning:**
```bash
# DVC for dataset versioning
dvc add data/training_v1.2.dvc
git commit -m "Training set v1.2: +500 handwriting samples"
git tag training-v1.2
dvc push
```

---

#### 3. MLOps Automation ([mlops/](mlops/))

**Automated Retraining Pipeline:**
```yaml
# GitHub Actions: Quarterly retraining
name: Quarterly Model Retraining
on:
  schedule:
    - cron: '0 0 1 */3 *'  # First day of quarter
  workflow_dispatch:  # Manual trigger

jobs:
  retrain_iqa:
    runs-on: [self-hosted, gpu]
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Download latest training data
        run: dvc pull data/iqa_training.dvc

      - name: Train IQA model
        run: |
          python scripts/train_iqa.py \
            --config configs/iqa_retrain.yaml \
            --output models/iqa/candidate

      - name: Evaluate on validation set
        run: |
          python scripts/evaluate_iqa.py \
            --model models/iqa/candidate \
            --test-set data/iqa_validation \
            --output eval_results.json

      - name: Check acceptance criteria
        run: |
          python scripts/check_model_quality.py \
            --results eval_results.json \
            --min-map 0.88 \
            --max-latency 200

      - name: Trigger A/B test
        if: success()
        run: |
          curl -X POST $AB_TEST_ENDPOINT \
            -d '{"candidate": "models/iqa/candidate"}'
```

**Model Registry:**
```python
# MLflow model tracking
import mlflow

with mlflow.start_run():
    # Log parameters
    mlflow.log_params({
        "architecture": "mobilenetv3",
        "input_size": 224,
        "batch_size": 32,
        "learning_rate": 1e-3
    })

    # Train model
    model = train_iqa(config)

    # Log metrics
    mlflow.log_metrics({
        "val_map": 0.89,
        "val_f1_blur": 0.91,
        "val_f1_skew": 0.93,
        "inference_time_ms": 45
    })

    # Log model
    mlflow.pytorch.log_model(model, "iqa_model")
    mlflow.log_artifact("configs/iqa.yaml")
```

**Model Versioning Strategy:**
- Semantic versioning: v1.2.3 (major.minor.patch)
- Major: Breaking changes (architecture, output format)
- Minor: New features (additional classes, improved accuracy)
- Patch: Bug fixes, calibration updates
- Tag models in registry: production, staging, candidate

---

#### 4. A/B Testing Framework ([src/api/ab_testing.py](src/api/ab_testing.py))

**Traffic Splitting:**
```python
# Route requests to model variants
def get_model_variant(document_id):
    """Assign document to model variant"""
    hash_val = hash(document_id) % 100

    # 10% to candidate model, 90% to production
    if hash_val < 10:
        return "candidate"
    else:
        return "production"

# Process with assigned model
variant = get_model_variant(document_id)
result = process_document(document, model_variant=variant)

# Log variant assignment
log_event("ab_test_assignment", {
    "document_id": document_id,
    "variant": variant,
    "timestamp": utcnow()
})
```

**Metrics Comparison:**
```python
# Compare variants after 1 week
ab_test_results = {
    "production": {
        "latency_p95": 145,
        "error_rate": 0.008,
        "user_reported_issues": 12
    },
    "candidate": {
        "latency_p95": 138,  # 5% faster
        "error_rate": 0.006,  # 25% fewer errors
        "user_reported_issues": 7  # 42% fewer issues
    }
}

# Statistical significance test
p_value = ttest_ind(production_latencies, candidate_latencies)
if p_value < 0.05 and candidate_better:
    approve_rollout("candidate")
```

**Rollout Strategy:**
```
Week 1: 10% traffic to candidate (A/B test)
    ↓ (Monitor metrics, check for regressions)
Week 2: 25% traffic to candidate (if passing)
    ↓
Week 3: 50% traffic to candidate
    ↓
Week 4: 100% traffic to candidate (promote to production)
    ↓
Rollback plan: Instant rollback if error rate > 2x baseline
```

**Rollback Automation:**
```python
# Auto-rollback on critical issues
def monitor_rollout():
    while rollout_in_progress:
        metrics = fetch_metrics(candidate_model)

        # Check rollback conditions
        if metrics.error_rate > baseline.error_rate * 2:
            rollback("Error rate too high")
        elif metrics.latency_p95 > baseline.latency_p95 * 1.5:
            rollback("Latency too high")
        elif metrics.user_issues > threshold:
            rollback("User-reported issues")

        sleep(60)  # Check every minute
```

---

#### 5. Periodic Calibration ([scripts/calibration.py](scripts/calibration.py))

**Quarterly Calibration Workflow:**
```python
# Recalibrate confidence thresholds
def calibrate_thresholds(validation_set):
    """Find optimal thresholds per issue type"""
    optimal_thresholds = {}

    for issue_type in ["blur", "skew", "contrast", "noise"]:
        # Compute precision-recall curve
        precisions, recalls, thresholds = precision_recall_curve(
            y_true=validation_set[f"{issue_type}_label"],
            y_score=validation_set[f"{issue_type}_confidence"]
        )

        # Find threshold that maximizes F1
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls)
        optimal_idx = np.argmax(f1_scores)
        optimal_thresholds[issue_type] = thresholds[optimal_idx]

    return optimal_thresholds

# Update production config
update_config("thresholds.yaml", optimal_thresholds)
deploy_config_update()
```

**Temperature Scaling:**
```python
# Recalibrate confidence scores
def temperature_scaling(logits, temperature):
    """Scale logits for better calibration"""
    return logits / temperature

# Find optimal temperature on validation set
optimal_temp = find_optimal_temperature(validation_set)
save_temperature("models/iqa/temperature.json", optimal_temp)
```

**Calibration Metrics:**
- Expected Calibration Error (ECE) < 0.05
- Reliability diagrams (confidence vs accuracy)
- Brier score for probabilistic predictions

---

### Deliverables (Phase 5B)

- ✅ Drift detection system with KL divergence, confidence monitoring
- ✅ Data flywheel: automated failure collection, active learning pipeline
- ✅ MLOps automation: scheduled retraining, model registry (MLflow)
- ✅ A/B testing framework with traffic splitting and auto-rollback
- ✅ Quarterly calibration scripts with threshold optimization
- ✅ Dataset versioning with DVC
- ✅ Model versioning with semantic versioning + registry

### Success Criteria (Phase 5B)

- Drift detection: Alert within 1 week of distribution shift (95% accuracy)
- Active learning: Reduce annotation effort by > 50% (500 samples vs 1000+)
- Model retraining: Automated quarterly retraining with < 5% manual intervention
- A/B testing: 95% of rollouts complete without rollback
- Calibration: ECE < 0.05 after quarterly recalibration
- 95% of production failures resolved in next model version

---

## Phase 5C: Optimization & Scale (Weeks 33-40, 8 weeks)

### Objectives

Optimize costs, enhance performance, and prepare for scale (10x traffic growth).

### Tasks

#### 1. Cost Optimization ([scripts/cost_optimization/](scripts/cost_optimization/))

**GPU Utilization Optimization:**
```python
# Maximize GPU batch processing
def optimize_batch_size():
    """Find optimal batch size for GPU memory"""
    batch_sizes = [1, 2, 4, 8, 16, 32]
    results = []

    for batch_size in batch_sizes:
        try:
            latency, throughput, memory = benchmark_batch(batch_size)
            cost_per_page = (gpu_cost_per_hour / 3600) / throughput
            results.append({
                "batch_size": batch_size,
                "latency": latency,
                "throughput": throughput,
                "memory_gb": memory,
                "cost_per_page": cost_per_page
            })
        except OOMError:
            break

    # Select batch size with best cost/performance
    optimal = min(results, key=lambda x: x["cost_per_page"])
    return optimal["batch_size"]
```

**Auto-scaling Policies:**
```yaml
# Kubernetes HPA (Horizontal Pod Autoscaler)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: preprocessing-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: preprocessing-service
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: queue_depth
        target:
          type: AverageValue
          averageValue: "500"  # Scale if queue > 500
```

**Cost Analysis Dashboard:**
- Cost per page (GPU, CPU, storage, network)
- Monthly cost trends
- Resource utilization vs cost
- Optimization opportunities (spot instances, reserved capacity)

**Savings Opportunities:**
```
1. Spot instances: 60-70% cost reduction (trade-off: interruptions)
2. Reserved capacity: 30-40% cost reduction (1-year commit)
3. Batch processing: 2-4x throughput increase → lower cost/page
4. Early exit optimization: 30-50% of pages skip expensive models
5. Model quantization: CPU-only deployment for low-priority workloads
```

---

#### 2. Performance Optimization ([scripts/performance/](scripts/performance/))

**Latency Optimization:**
```python
# Profile and optimize hot paths
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Process document
result = process_document(document)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 slowest functions

# Identify bottlenecks:
# 1. YOLO inference (25ms) → Batch processing, INT8 quantization
# 2. Image I/O (15ms) → In-memory processing, avoid disk writes
# 3. JSON serialization (10ms) → Use orjson (faster than stdlib)
```

**Throughput Optimization:**
```python
# Async processing pipeline
async def process_document_async(document):
    """Parallel processing of independent stages"""
    # Stage 1: Ingestion (can run in parallel for multi-page)
    pages = await asyncio.gather(*[
        ingest_page(page) for page in document.pages
    ])

    # Stage 2: Detection (batch inference)
    detection_results = await batch_detect(pages)

    # Stage 3: Correction (parallel per page)
    corrected_pages = await asyncio.gather(*[
        correct_page(page, results)
        for page, results in zip(pages, detection_results)
    ])

    return corrected_pages
```

**Caching Strategy:**
```python
# Cache expensive operations
@lru_cache(maxsize=10000)
def detect_text_gate(image_hash):
    """Cache text detection results"""
    return text_gate_detector(image)

# DPI detection caching
dpi_cache = {}
def get_dpi_cached(pdf_path):
    if pdf_path not in dpi_cache:
        dpi_cache[pdf_path] = detect_dpi(pdf_path)
    return dpi_cache[pdf_path]
```

---

#### 3. Scalability Testing ([tests/scale/](tests/scale/))

**Load Testing:**
```python
# Locust load test
from locust import HttpUser, task, between

class PreprocessingUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def process_document(self):
        with open("test_document.pdf", "rb") as f:
            self.client.post("/process", files={"file": f})

# Run load test
# locust -f tests/scale/load_test.py --users 100 --spawn-rate 10
```

**Scale Targets:**
- 10x current throughput (60 pages/sec → 600 pages/sec)
- Sustained load: 100,000 pages/hour for 24 hours
- Burst capacity: 200,000 pages/hour for 1 hour
- Latency under load: p95 < 200ms (no degradation)

**Chaos Engineering:**
```bash
# Test resilience with chaos experiments
chaos-mesh apply -f experiments/gpu-failure.yaml   # Simulate GPU crash
chaos-mesh apply -f experiments/network-delay.yaml # Network latency
chaos-mesh apply -f experiments/pod-kill.yaml      # Random pod termination

# Validate: System recovers within 5 minutes
# Validate: No data loss during failures
# Validate: Auto-scaling responds appropriately
```

---

#### 4. Advanced Features

**Multi-Region Deployment:**
```
Region: US-East (Primary)
    → Serves North America traffic
    → Primary model registry and training

Region: EU-West (Secondary)
    → Serves Europe traffic
    → Model sync from US-East (hourly)

Region: AP-Southeast (Secondary)
    → Serves Asia-Pacific traffic
    → Model sync from US-East (hourly)

Benefits:
- Lower latency (geographic proximity)
- Regulatory compliance (data residency)
- Disaster recovery (multi-region redundancy)
```

**Feature Flags:**
```python
# LaunchDarkly or custom feature flags
def should_use_new_correction(document):
    """Gradual rollout of new correction algorithm"""
    if feature_flag("new_correction_v2").is_enabled(document.user_id):
        return True
    return False

# Rollout strategy:
# Week 1: 5% of users
# Week 2: 20% of users
# Week 3: 50% of users
# Week 4: 100% of users
```

---

#### 5. Documentation & Knowledge Management

**Operational Runbooks:**
- Incident Response Playbook
- Model Deployment Guide
- Rollback Procedures
- Capacity Planning Guide
- Cost Optimization Guide
- Performance Tuning Guide

**Quarterly Business Reviews (QBRs):**
- System health overview
- Key metrics trends (latency, throughput, costs)
- Model performance evolution
- Feature roadmap and prioritization
- Resource planning and budgeting

**Post-Incident Reviews (PIRs):**
```markdown
# Post-Incident Review: Latency Spike on 2025-03-15

## Incident Summary
- **Date**: 2025-03-15 14:30 UTC
- **Duration**: 45 minutes
- **Impact**: p95 latency increased from 150ms to 800ms
- **Root Cause**: Memory leak in ONNX Runtime

## Timeline
- 14:30: Alert triggered (latency > 500ms)
- 14:35: On-call engineer paged
- 14:40: Investigation started
- 14:55: Root cause identified (memory leak)
- 15:05: Mitigation deployed (worker restart)
- 15:15: Latency returned to normal

## Action Items
- [ ] Upgrade ONNX Runtime to v1.16.1 (fixes memory leak)
- [ ] Add memory leak detection to monitoring
- [ ] Implement automatic worker restart on high memory usage
- [ ] Update runbook with memory leak troubleshooting
```

---

### Deliverables (Phase 5C)

- ✅ Cost optimization: GPU batch size tuning, auto-scaling policies
- ✅ Performance optimization: 20% latency reduction, 2x throughput increase
- ✅ Scalability testing: 10x load test passing, chaos engineering validated
- ✅ Multi-region deployment (optional): 3 regions operational
- ✅ Feature flags framework for gradual rollouts
- ✅ Comprehensive operational runbooks (8+ documents)
- ✅ Quarterly Business Review process established
- ✅ Post-Incident Review template and process

### Success Criteria (Phase 5C)

- Cost per page reduced by > 30% from Phase 4 baseline
- Latency p95 < 150ms under 10x load
- System handles 10x traffic without degradation
- Auto-scaling responds within 2 minutes of load spike
- 100% of incidents have Post-Incident Reviews
- Runbooks cover 90% of common operational scenarios

---

## Phase 5D: Ongoing Operations (Week 41+)

### Objectives

Sustain operational excellence through continuous monitoring, quarterly retraining, and iterative improvements.

### Recurring Activities

#### Weekly Activities

**Monday: Weekly Planning**
- Review previous week's metrics
- Prioritize active learning candidates
- Plan model experiments
- Review incident reports

**Wednesday: Model Performance Review**
- Check drift detection alerts
- Review confidence score distributions
- Analyze user-reported issues
- Identify retraining priorities

**Friday: Retrospective**
- Team retro: What went well, what to improve
- Update documentation based on learnings
- Share knowledge across team

---

#### Monthly Activities

**Week 1: Active Learning Cycle**
- Mine high-value samples from production
- Annotate 100-200 samples
- Add to training set

**Week 2: Performance Analysis**
- Deep dive on latency/throughput trends
- Cost analysis and optimization opportunities
- Capacity planning review

**Week 3: Security & Compliance**
- Dependency updates (Dependabot, Safety)
- Security scanning (Bandit, CodeQL)
- Compliance audit (data retention, PII handling)

**Week 4: Knowledge Sharing**
- Tech talk: New features, optimizations
- Update documentation
- Cross-team collaboration

---

#### Quarterly Activities

**Q1: Model Retraining**
- Retrain IQA and layout models with new data
- A/B test candidate models
- Gradual rollout to production

**Q2: Calibration & Tuning**
- Recalibrate confidence thresholds
- Tune correction guardrails
- Update configurations

**Q3: Capacity Planning**
- Forecast traffic growth
- Plan infrastructure scaling
- Budget for next quarter

**Q4: Annual Review**
- Year-in-review metrics
- Roadmap planning for next year
- Team retrospective

---

#### On-Call Responsibilities

**Primary On-Call (24/7 rotation):**
- Respond to critical alerts (< 15 min)
- Triage and resolve incidents
- Escalate to secondary if needed
- Write Post-Incident Reviews

**Secondary On-Call (backup):**
- Provide support to primary
- Review and approve rollbacks
- Coordinate with engineering team

**On-Call Runbook Topics:**
- High error rate → Check logs, rollback recent deployment
- High latency → Check GPU memory, restart workers
- Model drift alert → Review drift metrics, plan retraining
- GPU crash → Restart GPU workers, check DCGM logs
- Disk full → Clean up temporary files, expand storage

---

### Key Performance Indicators (KPIs)

**Service Health KPIs:**
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Uptime** | > 99.5% | Monthly uptime percentage |
| **Error Rate** | < 0.5% | Failed requests / total requests |
| **Latency p95** | < 150ms | 95th percentile response time |
| **Throughput** | > 10 pages/sec | Pages processed per second |
| **MTTD** | < 5 min | Mean time to detection (incidents) |
| **MTTR** | < 30 min | Mean time to recovery (incidents) |

**Model Performance KPIs:**
| Metric | Target | Measurement |
|--------|--------|-------------|
| **IQA mAP** | > 0.88 | Weekly evaluation on test set |
| **Layout mAP@.50** | > 0.82 | Weekly evaluation on test set |
| **JSON Accuracy** | > 0.85 | End-to-end pipeline accuracy |
| **Drift Detection** | < 1 week | Time to detect distribution shift |
| **Model Degradation** | < 2% / 6mo | Performance loss over 6 months |

**Operational Excellence KPIs:**
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Cost per Page** | < $0.01 | Monthly cost / pages processed |
| **GPU Utilization** | 70-85% | Average GPU utilization |
| **Active Learning Efficiency** | > 50% | Annotation reduction vs random |
| **Rollback Rate** | < 5% | Deployments requiring rollback |
| **Incident Rate** | < 2 / month | Critical incidents per month |

---

### Team Structure & Roles

**Phase 5 Team Composition:**

**Site Reliability Engineer (SRE)** - 1 FTE
- Manage production infrastructure
- Respond to incidents (on-call rotation)
- Optimize performance and costs
- Maintain monitoring and alerting
- Write and update runbooks

**ML Engineer** - 1 FTE
- Monitor model performance
- Manage retraining pipeline
- Active learning and data curation
- A/B testing and model deployment
- Drift detection and calibration

**Data Engineer** - 0.5 FTE (part-time)
- Data pipeline maintenance
- Dataset versioning and management
- Active learning data collection
- Data quality monitoring

**Data Annotator** - 0.25 FTE (part-time)
- Weekly active learning annotation
- Quality control on production failures
- Inter-annotator agreement checks

**Product Manager** - 0.25 FTE (part-time)
- Roadmap planning
- Feature prioritization
- Stakeholder communication
- Quarterly business reviews

---

### Technology Stack (Phase 5)

**Monitoring & Observability:**
- Prometheus (metrics storage and querying)
- Grafana (dashboards and visualization)
- AlertManager (alert routing and silencing)
- Loki or Elasticsearch (log aggregation)
- Jaeger or Grafana Tempo (distributed tracing)
- Node Exporter (system metrics)
- NVIDIA DCGM Exporter (GPU metrics)

**Error Tracking & Incident Management:**
- Sentry (error tracking and release tracking)
- PagerDuty or Opsgenie (on-call management)
- Statuspage or Uptime Robot (public status page)

**MLOps & Experimentation:**
- MLflow (model registry and experiment tracking)
- DVC (dataset versioning)
- Weights & Biases (optional, experiment visualization)
- Feature flags: LaunchDarkly or GrowthBook

**CI/CD & Deployment:**
- GitHub Actions (CI/CD pipelines)
- ArgoCD or FluxCD (GitOps deployment)
- Kubernetes (container orchestration)
- Helm (Kubernetes package manager)

**Data & Storage:**
- PostgreSQL (metadata storage)
- Redis (caching and job queues)
- S3 or MinIO (model artifacts, datasets)
- DVC remotes (dataset versioning storage)

---

### Long-Term Roadmap (Beyond Phase 5)

**Phase 6: Advanced AI Features (Months 13-18)**
- Vision Transformer models (DETR, DINO) for layout detection
- Self-supervised learning for reduced annotation needs
- Multi-modal fusion (text + image embeddings)
- Zero-shot element classification

**Phase 7: Enterprise Features (Months 19-24)**
- Multi-tenancy and user management
- Custom model training per tenant
- SLA guarantees and premium tiers
- Enterprise SSO and RBAC

**Phase 8: Intelligence & Automation (Months 25-30)**
- Reinforcement learning from human feedback (RLHF)
- Automated hyperparameter tuning (AutoML)
- Self-healing systems (auto-remediation)
- Predictive scaling and cost optimization

---

## Phase 5 Summary

### Total Deliverables

**Phase 5A (Foundation):**
- Monitoring stack, dashboards, alerting, logging, tracing, error tracking

**Phase 5B (Intelligence):**
- Drift detection, data flywheel, MLOps automation, A/B testing, calibration

**Phase 5C (Optimization):**
- Cost optimization, performance tuning, scalability testing, runbooks

**Phase 5D (Ongoing):**
- Continuous monitoring, quarterly retraining, operational excellence

### Total Success Criteria

- **Uptime**: > 99.5%
- **Latency**: p95 < 150ms
- **Cost**: < $0.01 per page
- **Model Performance**: IQA mAP > 0.88, Layout mAP@.50 > 0.82
- **Drift Detection**: < 1 week to alert
- **MTTR**: < 30 minutes
- **Active Learning**: > 50% annotation reduction
- **Rollback Rate**: < 5%

### Budget Estimate (Phase 5, Annual)

| Category | Cost | Notes |
|----------|------|-------|
| **Team** | $300k-$400k | 3 FTEs (SRE, ML Eng, Data Eng + annotators) |
| **Infrastructure** | $30k-$60k | Monitoring stack, logging, storage |
| **Compute** | $36k-$72k | GPU workers, auto-scaling (from Phase 4) |
| **Tools** | $10k-$20k | Sentry, PagerDuty, feature flags, MLflow |
| **Annotation** | $6k-$12k | Active learning (500-1000 samples/quarter) |
| **Total** | $382k-$564k | Annual operational cost |

**Note**: Compute costs overlap with Phase 4 production infrastructure.

---

## Phase 5 Dependencies

**Requires Completion:**
- Phase 4: Production API, deployment, initial monitoring

**Enables:**
- Long-term operational excellence
- Continuous model improvement
- Cost optimization at scale
- Rapid experimentation and iteration

---

## Conclusion: Phase 5 as Operational Excellence

Phase 5 transforms the Image Preprocessing Detector from a deployed system to a **world-class production service** with:

1. **Comprehensive Observability**: Full visibility into system health, model performance, and business metrics
2. **Automated Intelligence**: Drift detection, active learning, and MLOps automation reduce manual toil
3. **Cost Efficiency**: Optimization delivers 30%+ cost reduction while maintaining SLAs
4. **Operational Maturity**: Runbooks, on-call processes, and incident response ensure reliability
5. **Continuous Improvement**: Data flywheel and quarterly retraining keep models fresh and accurate

**Key Philosophy**: Phase 5 is not a one-time project, but an **ongoing commitment** to operational excellence that ensures the system remains reliable, performant, and continuously improving over years of production use.

---

## Technical Stack & Dependencies

### Core Technologies

**Programming Language:**
- Python 3.10+ (type hints, modern features)

**Computer Vision:**
- OpenCV 4.8+ (classical CV, image corrections)
- Pillow (image manipulation)
- pdf2image or PyMuPDF (PDF to image conversion)

**Deep Learning:**
- PyTorch 2.0+ (model training and inference)
- Ultralytics YOLOv8 (object detection)
- torchvision (image transforms, pretrained models)
- timm (EfficientNet, MobileNet via PyTorch Image Models)

**Data Augmentation:**
- Albumentations (fast, GPU-accelerated augmentations)

**Inference Optimization:**
- ONNX Runtime (cross-platform inference)
- TensorRT (NVIDIA GPU acceleration, INT8 quantization)

**OCR (Secondary Analysis):**
- Tesseract OCR (lightweight script detection)
- pytesseract (Python wrapper)

**API & Web Service:**
- FastAPI (async API framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)

**Task Queue:**
- Celery or RQ (async worker pool)
- Redis (message broker)

**Monitoring & Logging:**
- Prometheus (metrics collection)
- Grafana (visualization)
- Sentry (error tracking)
- structlog (structured logging)

**Testing:**
- pytest (unit and integration tests)
- pytest-cov (code coverage)
- hypothesis (property-based testing)

**Development Tools:**
- Poetry (dependency management)
- Black (code formatting, 88 chars)
- Ruff (fast linting)
- MyPy (static type checking)
- Pre-commit (automated checks)

**Data Versioning:**
- DVC (Data Version Control)
- Git LFS (large file storage)

**Containerization:**
- Docker (service containerization)
- Docker Compose (local development)
- Kubernetes (production orchestration, optional)

### System Requirements

**Development Environment:**
- CPU: 8+ cores (for data processing)
- RAM: 32GB+ (for large dataset handling)
- GPU: NVIDIA GPU with 8GB+ VRAM (RTX 3080, A4000, or better)
- Storage: 500GB+ SSD (datasets, models, checkpoints)

**Production Deployment (Per Worker):**
- **GPU Worker**:
  - GPU: NVIDIA T4 (16GB), L4, or A10 (24GB)
  - CPU: 4 cores
  - RAM: 8GB
  - Storage: 50GB
- **CPU Worker** (for cost-sensitive deployments):
  - CPU: 8 cores (Intel Xeon or AMD EPYC)
  - RAM: 16GB
  - Storage: 50GB

**Scaling:**
- Load Balancer: Nginx or cloud LB (AWS ALB, GCP Cloud Load Balancing)
- Horizontal scaling: 10-100 workers for high-throughput scenarios

---

## Key Decisions & Open Questions

### Critical Decisions Needed Before Implementation

**1. Throughput and Hardware Budget**
- **Question**: What is the target throughput (pages/hour)?
- **Options**:
  - Low: < 10k pages/hour → CPU-only deployment feasible
  - Medium: 10k-100k pages/hour → 5-10 GPU workers
  - High: > 100k pages/hour → 20+ GPU workers with auto-scaling
- **Decision Needed**: Define target throughput to size infrastructure

**2. Detection Priorities (v1 Scope)**
- **Question**: Which element classes are must-have for v1?
- **Options**:
  - Minimal: Tables, Images only (simpler, faster deployment)
  - Standard: Tables, Images, Handwriting (balanced)
  - Full: Tables, Images, Handwriting, Formulas (complex, higher cost)
- **Decision Needed**: Prioritize classes based on downstream requirements

**3. Superscript/Footnote Detection Timing**
- **Question**: Is superscript/footnote detection a v1 requirement or post-OCR v2?
- **Options**:
  - v1 Pre-OCR: More complex, less accurate, add latency
  - v2 Post-OCR: Simpler, more accurate, deferred to downstream
- **Recommendation**: **Defer to post-OCR (v2)** for higher accuracy and simpler v1
- **Decision Needed**: Confirm with downstream team (LayoutParser/Tesseract)

**4. Language/Script Coverage**
- **Question**: Expected script coverage (Latin-only vs multi-script)?
- **Options**:
  - Latin-only: Simpler, no pre-OCR script ID needed
  - Multi-script: Requires script detection, more training data
- **Decision Needed**: Define language requirements based on document sources

**5. PDF Source Mix**
- **Question**: Mix of vector PDFs vs scanned images? Camera captures expected?
- **Implications**:
  - Vector PDFs: Clean rasterization, fewer quality issues
  - Scanned images: More quality issues, perspective correction needed
  - Camera captures: Perspective, lighting, blur challenges
- **Decision Needed**: Understand document source distribution for training data strategy

**6. Precision vs Recall Balance**
- **Question**: Preferred balance for issue detection?
- **Options**:
  - High Precision: Avoid false positives (minimize unnecessary corrections)
  - High Recall: Flag more issues (ensure no issues missed)
- **Recommendation**: **Favor Precision** to avoid over-correction harm
- **Decision Needed**: Define acceptable precision/recall trade-offs per issue type

**7. Downstream Integration Format**
- **Question**: Does LayoutParser require specific metadata format?
- **Decision Needed**: Validate JSON schema with downstream teams

**8. Deployment Environment**
- **Question**: On-premise, cloud (AWS/GCP/Azure), or hybrid?
- **Implications**:
  - Cloud: Auto-scaling, managed services, higher cost
  - On-premise: Fixed capacity, lower variable cost, more management
- **Decision Needed**: Define deployment target for infrastructure planning

---

## Resource Requirements & Budget

### Team Composition (Recommended)

**Phase 0-2 (Foundation + Classical + IQA ML)**: 2-3 people, 8-10 weeks
- 1x ML Engineer (model training, data augmentation)
- 1x Software Engineer (pipeline, API, infrastructure)
- 1x Data Annotator (part-time, validation set labeling)

**Phase 3 (Layout Detection)**: 3-4 people, 4-5 weeks
- 1x ML Engineer (YOLOv8 training, optimization)
- 1x Software Engineer (integration, optimization)
- 1-2x Data Annotators (custom annotation, active learning)

**Phase 4 (Production Hardening)**: 2-3 people, 3-4 weeks
- 1x ML Engineer (optimization, quantization)
- 1x DevOps Engineer (containerization, deployment, monitoring)
- 1x Software Engineer (API, testing, documentation)

**Phase 5 (Ongoing)**: 1-2 people, ongoing
- 1x ML Engineer (monitoring, retraining, improvements)
- 1x Data Annotator (part-time, continuous labeling)

**Total Team-Weeks**: ~60-80 team-weeks over 5-6 months

### Compute Resources & Costs

**Development (4-5 months):**
- 1x GPU Workstation: $5,000 one-time (or cloud equivalent)
- Cloud GPU (training): ~$1.50/hr for V100/A10
  - IQA training: ~50 GPU-hours = $75
  - YOLOv8 training: ~100 GPU-hours = $150
  - Active learning iterations: ~50 GPU-hours = $75
  - **Total**: ~$300 for training compute

**Production (Monthly, per worker):**
- **GPU Worker** (T4): $0.35/hr × 730 hrs = $255/month
- **CPU Worker** (8 cores): $0.15/hr × 730 hrs = $110/month

**Example Scaling:**
- 10 GPU workers: $2,550/month
- 20 GPU workers: $5,100/month

**Storage:**
- Training datasets (300GB): $20/month (S3 or equivalent)
- Model artifacts (10GB): $2/month

**Total Estimated Budget:**
- **Development**: $60k-$120k (team salaries, compute, tools)
- **Production (Year 1)**: $30k-$60k (compute, storage, monitoring)

---

## Success Metrics & KPIs

### Model Performance KPIs

**Image Quality Assessment:**
- mAP > 0.88
- Per-class F1 > 0.85 for all issues
- ECE < 0.05 (calibration)

**Document Element Detection:**
- mAP@.50 > 0.82
- Per-class AP > 0.70 for all classes
- Inference time < 10ms GPU, < 70ms CPU

**End-to-End Pipeline:**
- JSON Accuracy > 0.85
- Latency p95 < 150ms GPU, < 400ms CPU
- Throughput > 6 pages/sec per GPU worker

### Operational KPIs

**Reliability:**
- Uptime > 99.5%
- Error rate < 0.5%
- Mean time to recovery (MTTR) < 1 hour

**Performance:**
- Latency p95 < 150ms (GPU) / < 400ms (CPU)
- Throughput meets target SLA (define based on Decision #1)
- Resource utilization: GPU 70-85%, CPU 60-75%

**Quality:**
- User-reported issues < 5% of processed pages
- False positive rate < 10% per issue type
- False negative rate < 15% per issue type

### Business KPIs

**Efficiency:**
- Reduce manual preprocessing time by > 80%
- Increase RAG ingestion throughput by > 5x
- Reduce OCR error rate by > 30% (via quality improvements)

**Cost:**
- Processing cost < $0.01 per page
- Annotation cost < $0.05 per page (via weak supervision + active learning)

---

## Risk Register Summary

| Risk | Severity | Likelihood | Mitigation Priority | Status |
|------|----------|------------|---------------------|--------|
| Text/no-text gating errors | HIGH | MEDIUM | HIGH | Ensemble + calibration |
| Synthetic→real domain gap | HIGH | MEDIUM | HIGH | Real-world seed data |
| Over-correction harm | MED-HIGH | MEDIUM | HIGH | Guardrails + thresholds |
| Model drift | MEDIUM | HIGH | MEDIUM | Monitoring + retraining |
| Throughput bottlenecks | MEDIUM | MEDIUM | MEDIUM | Optimization + scaling |
| Script detection latency | LOW-MED | LOW | LOW | Lightweight OCR |
| Multi-page memory pressure | MEDIUM | LOW | MEDIUM | Streaming + caps |

---

## Appendix: Alternative Architectures Considered

### 1. Unified Multi-Task Model
**Approach**: Single backbone (EfficientNet) with multiple heads for IQA and layout detection
**Pros**: Shared features, fewer models to maintain
**Cons**: Complex training, loss balancing challenges, harder to debug
**Decision**: **Rejected** - Modular pipeline easier to maintain and optimize independently

### 2. Vision Transformer (ViT) for Layout
**Approach**: Use DocLayNet-trained DETR/DINO for layout detection
**Pros**: State-of-art accuracy on layout tasks
**Cons**: Heavier inference (20-50ms GPU), more GPU memory (4-6GB), less mature ecosystem
**Decision**: **Deferred to v2** - YOLOv8 provides better throughput for v1

### 3. PaddleOCR PP-Structure
**Approach**: Use PaddleOCR's end-to-end document structure pipeline
**Pros**: Mature, fast, good table detection
**Cons**: Introduces Paddle dependency (rest is PyTorch), less flexibility
**Decision**: **Consider for v2** if table detection underperforms

### 4. Segment Anything (SAM) + Classifier
**Approach**: SAM for region proposals, then classify regions
**Pros**: Robust proposals, handles diverse element types
**Cons**: Very heavy (50-100ms inference), overkill for throughput needs
**Decision**: **Rejected** - Too slow for production requirements

---

## Next Steps & Immediate Actions

### Week 1: Kickoff & Planning
1. ✅ Finalize key decisions (see Key Decisions section)
2. ✅ Set up project repository with CI/CD
3. ✅ Define ground-truth test set requirements (500 pages)
4. ✅ Identify team members and assign roles
5. ✅ Set up development environment (GPU workstations or cloud)

### Week 2-3: Data & Evaluation Setup (Phase 0)
1. Implement JSON schema and validation
2. Build evaluation framework (JSON Accuracy metric)
3. Begin ground-truth test set annotation (CVAT/Label Studio)
4. Set up DVC for dataset versioning
5. Create architecture diagrams and documentation

### Week 4-7: MVP Implementation (Phase 1)
1. Implement PDF ingestion and text detection gate
2. Build classical IQA detectors (skew, contrast, blur)
3. Implement correction pipeline with guardrails
4. Create CLI tool for testing
5. Evaluate baseline performance on test set

### Week 8+: ML Model Development (Phase 2-3)
1. Collect and augment IQA training data
2. Train IQA CNN (MobileNetV3 or EfficientNet)
3. Download and prepare layout detection datasets
4. Train YOLOv8 on document elements
5. Integrate ML models into pipeline

---

## Conclusion

This project plan outlines a **phased, modular approach** to building a production-grade image preprocessing detection system. By combining classical computer vision with modern deep learning, we balance accuracy with performance while maintaining maintainability.

**Key Success Factors:**
1. **Modular architecture** enables independent optimization of components
2. **Synthetic data generation + weak supervision** minimizes annotation burden
3. **Phased implementation** delivers value incrementally and reduces risk
4. **Guardrails and calibration** prevent over-correction and maintain quality
5. **Monitoring and drift detection** ensure long-term production stability

**Expected Timeline**: 5-6 months from kickoff to production deployment
**Expected Outcomes**:
- JSON Accuracy > 0.85
- Throughput > 6 pages/sec per GPU worker
- Scalable to 1000s of pages/hour
- Reduces manual preprocessing time by > 80%

**Next Step**: Finalize key decisions (see Key Decisions section) and proceed with Phase 0 foundation work.

---

*This project plan synthesized from multi-model expert analysis (Gemini 2.5 Pro + GPT-5) using the Zen MCP smart consensus framework.*
