# Image Preprocessing Detection System - Architecture Summary

**Quick Reference Guide for Technical Implementation**

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INPUT: PDF or Image File                         │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│         STAGE 1: INGESTION & STANDARDIZATION                         │
│  • Convert PDF → 300 DPI images (PyMuPDF)                           │
│  • DPI detection and upscaling flag                                  │
│  • Multi-page handling                                               │
│  Performance: 30-120ms/page (CPU)                                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│         STAGE 2: TEXT DETECTION GATE                                 │
│  • Ensemble: Morphological + EAST/DBNet-lite                         │
│  • Routes to appropriate processing path                             │
│  Performance: 3-8ms GPU / 20-40ms CPU                                │
└──────────────┬──────────────────────────────┬───────────────────────┘
               │                              │
        NO TEXT│                              │TEXT DETECTED
               ▼                              ▼
┌───────────────────────────┐  ┌─────────────────────────────────────┐
│  PATH A: IMAGE QUALITY    │  │  PATH B: DOCUMENT ELEMENT           │
│  ASSESSMENT               │  │  DETECTION                          │
│                           │  │                                     │
│  Classical CV:            │  │  YOLOv8n/s Object Detector:        │
│  • Skew (Hough)           │  │  • Tables                          │
│  • Contrast (Histogram)   │  │  • Images/Figures                  │
│  • Blur (Laplacian)       │  │  • Handwriting                     │
│                           │  │  • Mathematical Formulas           │
│  ML Model (CNN):          │  │                                     │
│  • Noise                  │  │  Secondary Analysis:                │
│  • Perspective            │  │  • Non-Latin scripts               │
│  • Orientation            │  │  • Superscript/footnotes (post-OCR)│
│                           │  │                                     │
│  Performance:             │  │  Performance:                       │
│  1-3ms GPU / 8-15ms CPU   │  │  2-7ms GPU / 25-70ms CPU           │
└───────────┬───────────────┘  └──────────────┬──────────────────────┘
            │                                 │
            └────────────┬────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│       STAGE 4: CORRECTION & OUTPUT GENERATION                        │
│  • Apply OpenCV corrections (deskew, CLAHE, sharpen, denoise)       │
│  • Confidence thresholds + do-no-harm guardrails                     │
│  • Generate JSON metadata with transform history                     │
│  • Aggregate multi-page results                                      │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│         OUTPUT: JSON Metadata + Corrected Images                     │
│  • Issues detected with confidence scores                            │
│  • Document elements with bounding boxes                             │
│  • Transform history for reproducibility                             │
│  • Ready for LayoutParser → Tesseract/Marker/Docling                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Architecture Decisions

### 1. Why Multi-Stage Pipeline (Not Monolithic)?

**Decision**: Modular pipeline with text detection fork

**Rationale**:
- Different detection tasks require different approaches (classification vs object detection)
- Independent optimization and testing of each component
- Easier maintenance and debugging
- Ability to upgrade components independently
- Better performance through specialized models

**Trade-off**: More components to maintain vs. simpler single model

---

### 2. Why Text Detection Fork?

**Decision**: Route images to different paths based on text presence

**Rationale**:
- Documents with text need layout analysis (tables, formulas, etc.)
- Images without text need quality assessment (blur, noise, etc.)
- Avoids running unnecessary models (performance optimization)
- Improves accuracy by specializing detection logic

**Implementation**: Ensemble of morphological analysis + EAST/DBNet-lite

---

### 3. Why Classical CV + ML Hybrid for IQA?

**Decision**: Combine classical OpenCV methods with lightweight CNN

**Rationale**:
- Classical methods excel at skew, contrast detection (fast, reliable)
- ML models better at noise, perspective, orientation (more robust)
- Hybrid approach balances speed and accuracy
- Fallback to classical if ML model fails

**Models**:
- Classical: Hough Transform, Histogram Analysis, Laplacian Variance
- ML: MobileNetV3-Small or EfficientNet-B0 (multi-label classifier)

---

### 4. Why YOLOv8 for Layout Detection?

**Decision**: YOLOv8n/s for document element detection

**Rationale**:
- Best balance of speed and accuracy for object detection
- Mature ecosystem with ONNX/TensorRT support
- Proven performance on document analysis tasks
- Fast inference: 2-7ms GPU with quantization
- Easier to deploy than Transformer-based models

**Alternative Considered**: Vision Transformers (DETR/DINO)
- Rejected due to higher latency (20-50ms) and GPU memory requirements

---

### 5. Why Synthetic Data Generation?

**Decision**: Generate training data via augmentation instead of manual labeling

**Rationale**:
- Reduces annotation cost by 80-90%
- Controllable degradation levels for balanced dataset
- Fast iteration: Regenerate data with new augmentation strategies
- Weak supervision: Use BRISQUE/NIQE for initial labels

**Critical**: Must validate on real-world test set to avoid domain gap

---

### 6. Why Active Learning?

**Decision**: Use active learning to minimize custom annotation effort

**Rationale**:
- Focuses annotation budget on high-value samples
- Iterative improvement without massive labeling effort
- Identifies rare classes and edge cases automatically
- Reduces annotation from 10k→2k pages for same accuracy

**Process**: Train → Infer → Select uncertain → Annotate → Retrain (3-4 cycles)

---

### 7. Why Defer Superscript/Footnote to Post-OCR?

**Decision**: Detect superscript/footnotes after OCR, not before

**Rationale**:
- OCR provides precise baseline and font size information
- Pre-OCR detection is inaccurate (pixel-level analysis unreliable)
- Adds latency and complexity to preprocessing pipeline
- Downstream OCR tools already extract this information

**Trade-off**: Requires coordination with downstream team (LayoutParser/Tesseract)

---

## Model Specifications

### Image Quality Assessment (IQA) Model

| Parameter | Value |
|-----------|-------|
| Architecture | MobileNetV3-Small or EfficientNet-B0 |
| Task | Multi-label Classification |
| Input Size | 224×224 or 320×320 |
| Classes | Noise, Blur, Skew, Perspective, Low Contrast, Orientation |
| Output | 6 binary predictions with confidence scores |
| Training Data | 50k images (80% synthetic, 20% real) |
| Performance | 1-3ms GPU / 8-15ms CPU (ONNX INT8) |
| Target mAP | > 0.88 |
| Target F1 | > 0.85 per class |

### Document Element Detection Model

| Parameter | Value |
|-----------|-------|
| Architecture | YOLOv8n or YOLOv8s |
| Task | Object Detection |
| Input Size | 640×640 |
| Classes | Table, Image, Handwriting, Formula |
| Output | Bounding boxes with class labels and confidence |
| Training Data | 300k+ images (public + 3k custom) |
| Performance | 2-7ms GPU / 25-70ms CPU (ONNX INT8) |
| Target mAP@.50 | > 0.82 |
| Target AP | > 0.70 per class |

---

## Performance Targets

### Latency (Per Page)

| Configuration | Target (p95) | Notes |
|---------------|--------------|-------|
| GPU (T4) | < 150ms | YOLOv8n INT8, batch=4 |
| GPU (A10) | < 100ms | YOLOv8s INT8, batch=8 |
| CPU (8 cores) | < 400ms | ONNX INT8, single page |

### Throughput (Per Worker)

| Configuration | Target | Notes |
|---------------|--------|-------|
| GPU (T4) | > 6 pages/sec | ~21,600 pages/hour |
| GPU (A10) | > 12 pages/sec | ~43,200 pages/hour |
| CPU (8 cores) | > 2 pages/sec | ~7,200 pages/hour |

### Accuracy

| Metric | Target |
|--------|--------|
| IQA mAP | > 0.88 |
| IQA F1 per class | > 0.85 |
| Layout mAP@.50 | > 0.82 |
| Layout AP per class | > 0.70 |
| End-to-end JSON Accuracy | > 0.85 |

---

## Critical Implementation Guidelines

### 1. Correction Guardrails (Do-No-Harm Principle)

**Always apply confidence thresholds before correction:**

```python
# Example: Deskew only if confident and improvement is measurable
if skew_confidence > 0.85 and abs(skew_angle) > 2.0:
    variance_before = compute_variance(image)
    deskewed = apply_deskew(image, skew_angle)
    variance_after = compute_variance(deskewed)

    if variance_after > variance_before * 1.05:  # 5% improvement
        image = deskewed
        log_correction("deskew", skew_angle, success=True)
    else:
        log_correction("deskew", skew_angle, success=False, reason="no_improvement")
```

**Why Critical**: Over-correction can harm OCR accuracy more than no correction

---

### 2. Text Detection Gate Ensemble

**Use ensemble to minimize false negatives:**

```python
# Ensemble approach
morphological_score = stroke_density_analysis(image)
east_score = east_detector(image)

# Conservative gating (high recall)
has_text = (morphological_score > 0.3) or (east_score > 0.5)

# If uncertain, run both paths and merge results
if 0.4 < max(morphological_score, east_score) < 0.6:
    results = merge_results(
        run_iqa_path(image),
        run_layout_path(image)
    )
```

**Why Critical**: False negatives (missed text) lead to wrong processing path

---

### 3. Early Exit Optimization

**Skip expensive models on clean pages:**

```python
# Fast heuristic check first
if is_page_clean(image):  # Low entropy, uniform histogram, no structural complexity
    return {"issues": [], "elements": [], "early_exit": True}

# If potentially complex, run full pipeline
results = run_full_pipeline(image)
```

**Expected Savings**: 30-50% of pages can early-exit, 3-5x speedup on those pages

---

### 4. Batch Inference

**Process multiple pages in parallel:**

```python
# Bad: Sequential processing
for page in pages:
    result = model.infer(page)  # 5ms each → 50ms for 10 pages

# Good: Batch processing
results = model.infer_batch(pages)  # 8ms total for 10 pages (1.6× overhead)
```

**Expected Improvement**: 4-6x throughput increase with batch=4-8

---

### 5. Quantization

**Always quantize models for production:**

```bash
# PyTorch → ONNX → INT8 quantization
python -m torch.onnx.export model.pth model.onnx
python -m onnxruntime.quantization.quantize_dynamic model.onnx model_int8.onnx

# Expected speedup: 1.5-3x on CPU, 1.2-1.8x on GPU
```

---

## Risk Mitigation Checklist

### Before Production Deployment

- [ ] **Text gate calibrated** on faint/stylized text validation set
- [ ] **IQA model tested** on real-world scans (not just synthetic)
- [ ] **Correction guardrails** validated (no over-correction)
- [ ] **Confidence thresholds** tuned per issue type (maximize F1)
- [ ] **Performance benchmarks** meet targets (latency, throughput)
- [ ] **Resource monitoring** configured (alerts on memory, GPU usage)
- [ ] **Drift detection** implemented (feature distributions, mAP tracking)
- [ ] **Rollback plan** ready (preserve original images)
- [ ] **A/B testing** framework for gradual model updates
- [ ] **Documentation** complete (API, deployment, model details)

---

## Technology Stack

### Core Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
opencv-python = "^4.8.0"
torch = "^2.0.0"
torchvision = "^0.15.0"
ultralytics = "^8.0.0"  # YOLOv8
timm = "^0.9.0"  # EfficientNet, MobileNet
albumentations = "^1.3.0"
onnxruntime = "^1.15.0"
pymupdf = "^1.22.0"
pytesseract = "^0.3.10"
fastapi = "^0.100.0"
pydantic = "^2.0.0"
```

### Development Tools

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
black = "^23.7.0"
ruff = "^0.0.280"
mypy = "^1.4.0"
```

---

## Quick Start Commands

### Setup Environment

```bash
# Create environment
poetry install

# Setup pre-commit hooks
poetry run pre-commit install
```

### Training

```bash
# Train IQA model
poetry run python scripts/train_iqa.py --config configs/iqa_mobilenet.yaml

# Train YOLOv8 layout detector
poetry run python scripts/train_layout.py --config configs/yolo_layout.yaml
```

### Evaluation

```bash
# Evaluate IQA model
poetry run python scripts/evaluate_iqa.py --model models/iqa/best.onnx

# Evaluate layout detector
poetry run python scripts/evaluate_layout.py --model models/layout/best.onnx

# End-to-end JSON accuracy
poetry run python scripts/evaluate_pipeline.py --test-set data/test/
```

### Inference

```bash
# Process single file
poetry run python src/cli.py process input.pdf --output result.json

# Batch processing
poetry run python src/cli.py batch input_dir/ --output-dir results/
```

### Deployment

```bash
# Build Docker container
docker build -t image-preprocessing:latest .

# Run API service
docker run -p 8000:8000 --gpus all image-preprocessing:latest

# Test API
curl -X POST http://localhost:8000/process \
  -F "file=@document.pdf" \
  -o result.json
```

---

## File Structure (Recommended)

```
image_detection/
├── configs/                    # Training and inference configs
│   ├── iqa_mobilenet.yaml
│   └── yolo_layout.yaml
├── data/                       # Datasets (managed by DVC)
│   ├── iqa/                   # IQA training data
│   ├── layout/                # Layout detection data
│   ├── test/                  # Ground-truth test set
│   └── annotations/           # Custom annotations
├── models/                     # Trained models
│   ├── iqa/                   # IQA checkpoints
│   └── layout/                # YOLOv8 checkpoints
├── src/                        # Source code
│   ├── ingestion/             # PDF/image loading
│   ├── detection/             # Detection modules
│   │   ├── text_gate.py
│   │   ├── iqa_classical.py
│   │   ├── iqa_ml.py
│   │   └── layout_detector.py
│   ├── correction/            # Image corrections
│   ├── output/                # JSON generation
│   ├── api/                   # FastAPI service
│   └── cli.py                 # Command-line interface
├── scripts/                    # Training and evaluation scripts
│   ├── train_iqa.py
│   ├── train_layout.py
│   ├── evaluate_pipeline.py
│   └── active_learning.py
├── tests/                      # Unit and integration tests
├── docker/                     # Docker files
│   ├── Dockerfile
│   └── docker-compose.yml
├── monitoring/                 # Monitoring configs
│   ├── prometheus.yml
│   └── grafana-dashboards/
├── PROJECT_PLAN.md             # This comprehensive plan
├── ARCHITECTURE_SUMMARY.md     # This quick reference
└── pyproject.toml              # Poetry dependencies
```

---

## Key Contacts & Decisions Needed

### Critical Questions for Stakeholders

1. **Throughput Target**: What pages/hour do we need to process?
2. **Hardware Budget**: GPU vs CPU deployment? How many workers?
3. **Language Coverage**: Latin-only or multi-script?
4. **PDF Sources**: Vector PDFs, scanned images, or camera captures?
5. **Detection Priorities**: Which element classes are must-have for v1?
6. **Superscript/Footnotes**: v1 requirement or defer to post-OCR v2?
7. **Downstream Integration**: Does LayoutParser require specific metadata format?
8. **Deployment Environment**: On-premise, cloud (AWS/GCP/Azure), or hybrid?

### Next Steps

1. Schedule stakeholder meeting to finalize decisions
2. Set up development environment and repository
3. Begin Phase 0: Foundation & Scaffolding (2-3 weeks)
4. Start ground-truth test set annotation (500 pages)

---

*For complete details, see [PROJECT_PLAN.md](PROJECT_PLAN.md)*
*Generated via multi-model consensus (Gemini 2.5 Pro + GPT-5)*
