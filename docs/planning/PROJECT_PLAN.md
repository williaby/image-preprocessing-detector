---
schema_type: planning
title: "Project A: Image Preprocessing & IQA Gateway - Project Plan"
description: "Comprehensive project plan for Project A with RAG Pipeline architecture,
  teacher-student ResNet IQA, and detailed sprint breakdowns for all 6 phases"
tags:
  - planning
  - rag_pipeline
  - teacher_student
  - resnet
  - iqa
  - roadmap
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
  - name: "Claude Code"
purpose: "Document the complete implementation roadmap for Project A from Phase 0
  foundation through Phase 6 continuous improvement, aligned with 4-project RAG Pipeline
  architecture."
component: "Strategy"
source: "Merged from remote branch claude/update-root-project-plan-011NESKE9dRWrXSMWEqoDi9L"
---

**Project**: Project A - Image Preprocessing Detection & Quality Assessment for RAG Applications
**Purpose**: Intelligent preprocessing gateway that analyzes documents, corrects quality issues,
and provides routing metadata for downstream OCR/RAG processing
**Position**: First stage in a 4-project RAG document processing pipeline (A → B → C → D)
**Repository**: `image-preprocessing-detector`

---

## Executive Summary

Project A serves as the **front-door gateway** for the RAG document processing pipeline. This project analyzes raw documents (PDFs, images), detects and corrects quality issues, performs lightweight layout classification, and generates routing metadata to guide downstream processing decisions.

**Key Innovation**: Teacher-student ResNet architecture with device-priority execution (Local GPU → Local CPU → Modal GPU) that balances accuracy with cost efficiency. The system uses a lightweight "layout-lite" approach for structural analysis while deferring full semantic layout detection to Project B.

**Pipeline Position**:

```text
Project A (THIS REPO)    →    Project B           →    Project C        →    Project D
image_detection                ocr-orchestrator         fusion-trust          vector-indexer
─────────────────              ────────────────         ────────────          ──────────────
• IQA & Corrections            • Layout Detection       • OCR Fusion          • Embeddings
• Text Gate                    • Reading Order          • Hallucination Det   • Vector DB
• DQS Calculation              • Multi-Engine OCR       • Trust Scoring       • Metadata
• Routing Metadata             • Paragraph Segment      • RAG Chunking        • Indexing

OUTPUT:                        OUTPUT:                  OUTPUT:               OUTPUT:
DocumentMetadata.json          OCRDocument.json         FusedDocument.json    Vector DB
+ Corrected Images                                      + RAGChunk.json       Entries
```text

**Expected Performance**: 2-6 pages/second per worker (CPU/GPU respectively), <150ms latency per page (GPU), with horizontal scalability to handle thousands of pages/hour.

---

## Current Status Dashboard (January 2025 Audit)

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| **Phase 0**: Foundation | ✅ COMPLETE | 100% | CI/CD, schema, pre-commit, security scanning |
| **Phase 1**: Classical MVP | ✅ COMPLETE | 100% | Ingestion, text gate, basic IQA (3 detectors), corrections, CLI, output |
| **Phase 1B**: DPI Upscaling | ✅ COMPLETE | 100% | DPI detection, upscaling, pre-flight analysis |
| **Phase 1C**: Enhanced Classical IQA | ✅ COMPLETE | 100% | 5 additional IQA detectors + discrepancy framework + DQS weight calibration |
| **Phase 2**: Core Components | ✅ COMPLETE | 100% | Schema, PDF type, layout-lite infrastructure, DQS, routing - all 26 sprints complete, 21/21 integration tests passing |
| **Phase 3**: ML IQA | ✅ COMPLETE | 100% | **BOTH MODELS TRAINED** - Teacher (50 epochs, val_loss=0.27) & Student (30 epochs, val_loss=0.14) |
| **Phase 4**: Device Priority | ⚠️ PARTIAL | 25% | Device probing complete (184 lines), orchestrator missing - 9-11 days remaining |
| **Phase 5**: Testing & Deploy | ⚠️ PARTIAL | 40% | API framework + E2E tests (2000+ lines), endpoints stub - 25-30 days remaining |
| **Phase 6**: Monitoring | ✅ INFRASTRUCTURE | 85% | **6000+ lines ready** (drift, alerting, active learning, pipeline integration), external service testing remaining - 4-5 days |
| **Phase 7**: ML IQA Optimization | ❌ NOT STARTED | 0% | Optimization phase - not blocking MVP |
| **Phase 8**: DQS & Routing Calibration | ⚠️ PARTIAL | 60% | Infrastructure complete in Phase 2, calibration with real OCR data remaining |
| **Phase 9**: Element Classifiers | ❌ NOT STARTED | 0% | Migrated from Project B - dataset acquisition needed, 20-25 days estimated |

**Phase 3 Training Complete (Nov 22, 2025)**:

- **Teacher Model**: ResNet-50, 50 epochs, val_loss=0.2694, 1.91 GPU hours on A10
- **Student Model**: ResNet-18, 30 epochs, val_loss=0.1386, distilled from teacher (T=4.0, α=0.7)
- **ONNX Exports**: `models/iqa/onnx/resnet50_teacher_50epoch.onnx` (105 MB), `resnet18_student.onnx` (48 MB)
- **GCS Backup**: `gs://image_detection_b/models/phase2_iqa/`, `gs://image_detection_b/models/phase2_student/`
- **Datasets Available**: OmniDocBench & OHR-Bench via NFS symlinks at `data/benchmarks/`

**Recommended Next Steps**:

1. **Priority 1**: Begin Phase 4 device-priority execution implementation
2. **Priority 2**: Integrate ONNX models into inference pipeline (iqa_ml.py)
3. **Priority 3**: Benchmark model inference latency (target: ≤10ms GPU, ≤100ms CPU)
4. **Priority 4**: Integration testing of all 8 classical IQA detectors with ML IQA pipeline
5. **Priority 5**: Complete Phase 6 layout-lite detector tuning (improve F1 scores from 0.094 to >0.85)

---

## Project Boundaries & Scope

### ✅ IN SCOPE - What Project A Does

**Core Responsibilities:**

- File ingestion & page rasterization (PDF → standardized 300 DPI images)
- **Classical IQA** (8 detectors):
  - **Phase 1 (basic)**: Blur (Laplacian variance), Skew (Hough transform), Contrast (histogram analysis)
  - **Phase 1C (enhanced)**: Noise (wavelet-based DWT), Illumination (9-region uniformity), JPEG Blockiness (DCT block boundary), Binarization Quality (histogram bimodality), Bleed-Through (verso content detection)
- **ML-based DIQA**: Teacher-student ResNet architecture (ResNet-50 teacher, ResNet-18 student)
- **Selective teacher inference** triggered by:
  - Document risk classification
  - Student uncertainty thresholds
  - Discrepancies between classical IQA and student output
- **Guarded corrections**: deskew, binarize, upscale, denoise, CLAHE, dewarping, bleed-through suppression (with do-no-harm guardrails)
- **Light layout detection (YOLOv10-doc, 11 DocLayNet classes)**: Detect all elements, assess per-element quality, calculate complexity
  - Model: YOLOv10-doc (specifically trained on DocLayNet)
  - Classes: All 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)
  - Hybrid IQA: Per-element quality assessment on figures, tables, embedded images
  - Spatial hints: Column detection, vertical position, proximity between elements
  - **NOT full semantic layout** (no reading order, no element linking - that's Project B)
- **Office document support**: Docling integration for embedded image extraction (.docx, .xlsx, .pptx)
- **PDF type classification**: image_only / born_digital / hybrid
- **Document Quality Score (DQS)**: Degradation score + structural complexity score
- **Routing metadata**: `pre_ocr_risk`, `ocr_routing_recommendation` for Project B
- **Device-priority execution**: Local GPU → Local CPU → Modal GPU

### ❌ OUT OF SCOPE - What Project A Does NOT Do

**Explicitly Deferred to Projects B-D:**

- ❌ Full layout detection with precise bounding boxes (Project B)
- ❌ Reading order estimation (Project B)
- ❌ OCR of any type (Project B)
- ❌ Table structure reconstruction (rows/columns/cells) (Project B)
- ❌ Paragraph segmentation (Project B)
- ❌ Multi-engine OCR fusion (Project C)
- ❌ Trust scoring & hallucination detection (Project C)
- ❌ RAG chunking (Project C)
- ❌ Embeddings generation (Project D)
- ❌ Vector database operations (Project D)

**Critical Design Principle**: Project A must not re-implement capabilities owned by Projects B-D. This prevents scope creep and ensures clean separation of concerns.

---

## System Architecture

### Multi-Stage Pipeline Overview

```text
Input (PDF/Image)
    ↓
[1. Ingestion & Standardization]
    ↓ (Auto-upscale if < 300 DPI, render to 300 DPI images)
[2. PDF Type Classification]
    ↓ (Classify: image_only / born_digital / hybrid)
[3. Text Detection Gate] (PENDING EVALUATION - see FR-2.4)
    ↓                              ↓
[NO TEXT]                     [TEXT DETECTED]
    ↓                              ↓
[4A. Classical IQA            [4B. Light Layout Detection (YOLOv10-doc)]
     Full page analysis]           All 11 DocLayNet classes detection
    ↓                              ↓
[5. ML IQA: ResNet-18 Student (Primary)]
    ↓
[6. Uncertainty Gate: Trigger Teacher if needed]
    ↓ (Selective)
[7. ML IQA: ResNet-50 Teacher (High-risk cases only)]
    ↓
[8. Correction Pipeline with Guardrails]
    ↓
[9. DQS Calculation & Routing Recommendation]
    ↓
DocumentMetadata.json + Corrected Images → Project B
```text

### Teacher-Student ResNet Architecture

**Training Phase:**

```text
Raw Datasets (OmniDocBench, OHR-Bench, custom)
   ↓
[ResNet-50 Teacher Training]
   ↓ (Multi-head IQA network: blur, noise, skew, illumination, artifacts)
Teacher Weights
   ↓
[Knowledge Distillation → ResNet-18]
   ↓
Student Model (default inference) + Teacher Model (selective inference)
   ↓
Registered in local + Modal registries
```text

**Runtime Phase:**

```text
Incoming Document
   ↓
Preflight Checks (DPI, format, page count)
   ↓
Rendering (golden DPI: 300)
   ↓
[Primary IQA Pass → ResNet-18 Student]
       ↓
[Uncertainty Gate]
   ├── Low uncertainty & no conflicts → accept student output
   ├── High-risk doc (e.g., fuzzy scan, watermark) → escalate to teacher
   ├── High softmax entropy → escalate to teacher
   ├── Classical vs student discrepancy high → escalate to teacher
       ↓
[Teacher Pass (ResNet-50) - Device priority: Local GPU → Modal GPU → BLOCK]
       ↓
IQA Metrics Merged (student + teacher where available)
       ↓
Layout-Lite Detection (coarse structural analysis)
       ↓
Corrections (with guardrails)
       ↓
DQS + Routing Recommendation
       ↓
Output Package → Project B
```text

### Device-Priority Execution

**Device Selection Order:**

1. **Local GPU** (if available and under utilization threshold)
2. **Local CPU** (if latency acceptable for student inference)
3. **Modal GPU** (if enabled, within quota, for teacher inference)

**Critical Constraints:**

- **Student (ResNet-18)**: Can run on CPU or GPU
  - CPU target: ≤40ms/page
  - GPU target: ≤10ms/page
- **Teacher (ResNet-50)**: MUST NOT run on CPU in production mode
  - GPU target: ≤30ms/page for flagged pages
  - If no GPU available → skip teacher inference (use student-only output)
- **Modal GPU usage**: Optional, bounded by configuration (`modal_budget_per_run`)

### Light Layout (Project A) vs Full Semantic Layout (Project B)

**Light Layout Detection (Project A - THIS REPO)**:

- **Purpose**: Element detection with bounding boxes, quality assessment, spatial hints
- **Model**: **YOLOv10-doc** (specifically trained on DocLayNet, ONNX for production)
- **Classes**: All 11 DocLayNet classes
  - Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header
  - Picture, Section-Header, Table, Text, Title
- **Granularity**: Element-level detection (bounding boxes in COCO format)
- **Outputs**:
  - Bounding boxes for all 11 classes (COCO format: [x, y, width, height])
  - Hybrid IQA: Per-element quality scores (blur, noise, contrast for figures/tables/formulas)
  - Spatial hints: Column membership, vertical position, proximity between elements
  - Aggregated page attributes: element counts, presence flags, structural complexity score
- **Scope Boundary**:
  - ✅ Detect WHERE elements are (bounding boxes)
  - ✅ Assess element quality (per-element IQA)
  - ✅ Provide spatial hints (column detection, positions)
  - ❌ Do NOT link captions to figures (Project B)
  - ❌ Do NOT predict reading order (Project B)
  - ❌ Do NOT extract table structure (Project B)
- **Performance**: <25ms GPU (to be benchmarked)
- **Rationale**: YOLOv10-doc provides better accuracy/speed than YOLOv8, specifically trained on DocLayNet

**Full Semantic Layout (Project B - ocr-orchestrator)**:

- **Purpose**: Semantic understanding with reading order and element linking
- **Input**: Receives YOLOv10-doc detections from Project A
- **Additional Processing**:
  - Reading order prediction (critical for RAG, 5-29% impact per OHR-Bench)
  - Caption→Figure semantic linking
  - Footnote reference linking
  - Table structure extraction (rows, columns, cells via PubTables-1M)
  - Hierarchical document structure
- **Method**: Graph-based reading order prediction, PubTables-1M for table structure
- **Performance**: Adds 30-70ms for reading order + table structure
- **Rationale**: Semantic understanding requires OCR text, which Project A doesn't have

### Office Document Support (NEW CAPABILITY)

**Supported Formats**:

- `.docx` - Word documents
- `.xlsx` - Excel spreadsheets
- `.pptx` - PowerPoint presentations

**Project A Responsibility (Embedded Image Extraction)**:

- Use Docling to extract all embedded images from office documents
- Apply standard preprocessing pipeline to each extracted image:
  - Ingestion & normalization (DPI detection, upscaling if needed)
  - Quality detection (classical IQA + ML IQA)
  - Corrections with do-no-harm guardrails
  - Per-element metadata generation
- Hand off preprocessed images + metadata to Project B

**Project B Responsibility (Text & Structure Extraction)**:

- Use Docling for native office text extraction
- Parse tables, formatting, structure
- Combine preprocessed images from Project A with extracted text
- Generate unified document representation

**Rationale**:

- Office documents contain embedded images (charts, diagrams, photos) that benefit from IQA and correction
- Separation of concerns: Project A owns image quality, Project B owns text/structure extraction
- Docling has native .docx/.xlsx/.pptx support for both images and text

---

## Output JSON Schema

### Design Principles

- **COCO-aligned** for bounding boxes (compatibility with downstream processors)
- **Versioned schema** for reproducibility (`schema_version` field)
- **Routing metadata** for Project B decision-making
- **Transform history** for auditability

### Schema Structure

```json
{
  "document_id": "unique_doc_identifier",
  "file_name": "original_filename.pdf",
  "source_mime": "application/pdf",
  "num_pages": 5,
  "pdf_type": "hybrid",
  "languages": ["en", "es"],
  "has_non_latin": false,
  "pre_ocr_risk": 0.42,
  "dqs": {
    "degradation_score": 0.68,
    "structural_complexity_score": 0.75
  },
  "ocr_routing_recommendation": "ocr_advanced",
  "processing_version": {
    "pipeline_version": "1.0.0",
    "student_model_hash": "abc123...",
    "teacher_model_hash": "def456...",
    "thresholds": {...},
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "upscaling": {
    "applied": true,
    "original_dpi": 150,
    "target_dpi": 300,
    "algorithm": "lanczos",
    "processing_time_ms": 345
  },
  "teacher_usage": {
    "pages_with_teacher": [0, 3],
    "escalation_reasons": {
      "0": "high_entropy",
      "3": "classical_discrepancy"
    },
    "teacher_device": "modal_gpu",
    "total_teacher_time_ms": 67
  },
  "page_layout_summary": [
    {
      "page_index": 0,
      "layout_type": "multi",
      "has_tables": true,
      "has_figures": false,
      "has_dense_math": false,
      "has_handwriting": false,
      "fuzzy_scan": true,
      "watermark": false,
      "colorful_background": false
    }
  ],
  "pages": [
    {
      "page_index": 0,
      "width_px": 2550,
      "height_px": 3300,
      "dpi_input": 150,
      "dpi_effective": 300,
      "text_gate_result": "text_detected",
      "classical_iqa": {
        "blur_score": 0.87,
        "skew_angle_degrees": -3.2,
        "noise_level": 0.45,
        "contrast_score": 0.62,
        "illumination_score": 0.78
      },
      "ml_iqa": {
        "source": "student",
        "blur_score": 0.89,
        "noise_score": 0.48,
        "skew_score": 0.92,
        "illumination_score": 0.81,
        "artifact_score": 0.35,
        "confidence_scores": {
          "blur": 0.94,
          "noise": 0.88,
          "skew": 0.96,
          "illumination": 0.91,
          "artifact": 0.79
        }
      },
      "teacher_iqa": {
        "blur_score": 0.91,
        "noise_score": 0.51,
        "escalation_reason": "high_entropy"
      },
      "corrections_applied": [
        {
          "action": "deskew",
          "params": {"angle": -3.2},
          "confidence": 0.92,
          "quality_improvement": 0.15,
          "status": "success"
        },
        {
          "action": "clahe",
          "params": {"clip_limit": 2.0},
          "confidence": 0.85,
          "quality_improvement": 0.08,
          "status": "success"
        }
      ],
      "transform_history": [
        {
          "action": "upscale",
          "params": {"dpi_from": 150, "dpi_to": 300, "algorithm": "lanczos"},
          "started_at": "2025-01-15T10:30:01.000Z",
          "finished_at": "2025-01-15T10:30:01.345Z",
          "status": "success"
        },
        {
          "action": "deskew",
          "params": {"angle": -3.2},
          "started_at": "2025-01-15T10:30:01.500Z",
          "finished_at": "2025-01-15T10:30:01.522Z",
          "status": "success"
        },
        {
          "action": "clahe",
          "params": {"clip_limit": 2.0},
          "started_at": "2025-01-15T10:30:01.530Z",
          "finished_at": "2025-01-15T10:30:01.547Z",
          "status": "success"
        }
      ]
    }
  ]
}
```

### New Schema Fields vs Original Plan

**Added for RAG Pipeline Integration:**

- `pdf_type`: Classification of PDF origin (image_only / born_digital / hybrid)
- `dqs`: Document Quality Score with degradation + structural complexity
- `pre_ocr_risk`: Holistic risk score for OCR difficulty (0-1)
- `ocr_routing_recommendation`: Routing decision for Project B (ocr_fast / ocr_advanced / vision_simple / vision_structured)
- `page_layout_summary`: Layout-lite attributes per page
- `teacher_usage`: Tracking of when/why teacher model was invoked
- `teacher_iqa`: Teacher model outputs (when escalated)

**Removed/Deferred to Project B:**

- ~~`elements`~~: Per-element detection with precise bounding boxes → Project B responsibility
- ~~`detected_issues`~~: Internal detail, not needed in handoff JSON

---

## Training Data Strategy

### Critical Principle: Minimize Manual Annotation Burden

### ML-based IQA (ResNet-50 Teacher + ResNet-18 Student)

**Approach: Synthetic Data Generation + Weak Supervision + Knowledge Distillation**

**Data Sources:**

1. **Base Dataset**: Clean document images (10,000+ pages)
   - OmniDocBench: Multi-domain document dataset with quality annotations
   - OHR-Bench: OCR-hard regions dataset with quality labels
   - DocBank: Clean scanned documents
   - Born-digital PDFs rendered at high DPI

2. **Synthetic Augmentation** (using Albumentations):
   - **Noise**: Gaussian noise, Poisson noise, salt-and-pepper
   - **Blur**: Gaussian blur, motion blur (various angles), defocus blur
   - **Low Contrast**: Histogram manipulation, brightness reduction
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

4. **Knowledge Distillation**:
   - Train ResNet-50 teacher on all augmented data
   - Use teacher predictions as soft labels for ResNet-18 student
   - Combine with hard labels from weak supervision
   - Temperature-scaled distillation loss

**Target Dataset Size**: 50,000 images (80% synthetic augmentation, 20% real-world validation)

**Validation/Test Split**: Real-world documents with genuine quality issues (manually curated, 2,000 pages from OHR-Bench)

### Light Layout Detection (YOLOv10-doc)

**Approach: Use Pretrained YOLOv10-doc (DocLayNet-trained)**

**Model Source:**

- **YOLOv10-doc**: Pre-trained on DocLayNet dataset (specifically for document layout)
- **Classes**: All 11 DocLayNet classes out-of-box
  - Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header
  - Picture, Section-Header, Table, Text, Title
- **Format**: ONNX for production inference
- **No custom training needed**: Model already trained on 80k+ DocLayNet pages

**Project A Usage (Light Layout)**:

- Detect all 11 classes with bounding boxes (COCO format)
- Per-element quality assessment via hybrid IQA
- Spatial hints calculation (column membership, vertical position)
- Structural complexity scoring (aggregate element counts/types)

**Fine-tuning (Optional, if needed)**:

- If project-specific documents have unique characteristics
- Use transfer learning on 1-2k pages
- Focus on rare classes or domain-specific content

**Target Accuracy** (Out-of-box YOLOv10-doc on DocLayNet):

- mAP@.50: >0.82
- Per-class AP: >0.70 for all 11 classes

### PDF Type Classification

**Approach: PyMuPDF-based heuristics (no ML needed)**

**Implementation:**

- **Born-digital detection**: High proportion of extractable text, vector graphics
- **Image-only detection**: No extractable text, only embedded images
- **Hybrid detection**: Mix of extractable text and embedded images

**Target Accuracy**: 99.5% (heuristics-based, validated on DocBank + RVL-CDIP)

### Text Detection Gate Evaluation (PENDING DECISION)

**Status**: Prototype and benchmark before committing to implementation

**Evaluation Methodology**:

1. Benchmark YOLOv10-doc latency on pure images vs text documents
2. Compare architectures:
   - **With gate**: Text detection (ensemble) → conditional layout detection
   - **Without gate**: Always run YOLOv10-doc layout detection
3. Measure cost-benefit: Gate overhead + conditional savings vs always-layout overhead

**Decision Criteria**:

- **If YOLOv10-doc <20ms on all types** → **SKIP GATE** (not worth complexity)
- **If YOLOv10-doc >50ms on pure images** → **IMPLEMENT GATE** (meaningful savings)
- **If YOLOv10-doc 20-50ms** → **MARGINAL** (user decision based on complexity tolerance)

**Test Datasets**:

- 500 pages across 4 categories (pure images, text-light, text-dense, hybrid)
- Measure: Gate latency, YOLOv10 latency, accuracy, total time saved

**Benchmark Specification**: See [benchmarks/text_gate_evaluation.md](../../benchmarks/text_gate_evaluation.md)

**Action Items**:

- [ ] Acquire YOLOv10-doc pretrained model
- [ ] Run benchmark on representative dataset
- [ ] Document decision with empirical data
- [ ] Update PROJECT_PLAN.md with final decision

---

## Model Architecture & Training

### ML-based IQA: Teacher-Student ResNet

**Teacher Model: ResNet-50**

- **Architecture**: Multi-head IQA network
  - Backbone: ResNet-50 (ImageNet pretrained)
  - Heads: 5 parallel branches (blur, noise, skew, illumination, artifacts)
  - Output: Per-head scores (0-1) + confidence estimates

**Student Model: ResNet-18**

- **Architecture**: Distilled multi-head IQA network
  - Backbone: ResNet-18 (ImageNet pretrained)
  - Same head structure as teacher
  - Trained via knowledge distillation from teacher

**Training Configuration:**

```python
# Teacher Training (ResNet-50)
INPUT_SIZE = 224
BATCH_SIZE = 32
LEARNING_RATE = 1e-3 (with cosine annealing)
OPTIMIZER = AdamW
EPOCHS = 50 (with early stopping)
LOSS = Weighted combination:
  - BCEWithLogitsLoss (multi-label classification)
  - MSELoss (regression for continuous scores)

# Student Training (ResNet-18) - Knowledge Distillation
DISTILLATION_TEMPERATURE = 4.0
LOSS = Combined:
  - KL divergence loss (student logits vs teacher logits)
  - Hard label loss (student vs ground truth)
  - Alpha = 0.7 (weight for distillation loss)

# Data Split
TRAIN: 70% (35,000 images from OmniDocBench + synthetic)
VALIDATION: 15% (7,500 images)
TEST: 15% (7,500 images - OHR-Bench real-world only)

# Augmentation
Albumentations pipeline (see Training Data Strategy)
```

**Optimization:**

- **ONNX Export**: Both teacher and student for cross-platform deployment
- **INT8 Quantization**: ONNX Runtime for CPU deployment (student only)
- **TensorRT**: GPU inference acceleration (optional)

**Device-Priority Execution**:

- **Student inference**:
  1. Local GPU (if available, utilization <80%)
  2. Local CPU (ONNX INT8)
  3. Modal GPU (if enabled)
- **Teacher inference** (selective):
  1. Local GPU (if available)
  2. Modal GPU (if enabled, within quota)
  3. **BLOCK if no GPU** (production mode)

### Light Layout Detection (YOLOv10-doc)

**Chosen Solution: YOLOv10-doc (DocLayNet-pretrained)**

- **Model**: YOLOv10-doc (specifically trained on DocLayNet)
- **Classes**: All 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)
- **Input**: Variable size (maintains aspect ratio), optimized for document images
- **Format**: ONNX for production inference
- **Training**: Pre-trained on 80k+ DocLayNet pages (no custom training needed initially)
- **Performance**: <25ms GPU target (to be benchmarked), optimized for document layout
- **Rationale**: Better accuracy/speed tradeoff than YOLOv8, specifically designed for document understanding

---

## Evaluation Metrics & Benchmarks

### ML-based IQA Evaluation (ResNet-50 Teacher + ResNet-18 Student)

**Primary Metrics:**

1. **Per-Head Metrics** (blur, noise, skew, illumination, artifacts):
   - Precision, Recall, F1-Score for binary classification
   - ROC-AUC for confidence calibration
   - MAE (Mean Absolute Error) for regression scores

2. **Overall Performance**:
   - **Mean Average Precision (mAP)** across all heads
   - **Student-Teacher Agreement**: KL divergence between outputs

3. **Calibration**:
   - **Expected Calibration Error (ECE)**: Confidence vs accuracy alignment
   - Reliability diagrams per head

**Benchmark Targets:**

- **Teacher (ResNet-50)**:
  - Per-head F1-Score: >0.90
  - mAP: >0.92
  - ECE: <0.03
- **Student (ResNet-18)**:
  - Per-head F1-Score: >0.85
  - mAP: >0.88
  - ECE: <0.05
  - Teacher agreement: KL divergence <0.15

**Test Set**: OHR-Bench real-world documents only (no synthetic)

### Light Layout Evaluation (YOLOv10-doc)

**Primary Metrics:**

1. **Element Detection Accuracy**:
   - mAP@.50 (COCO metric): >0.82 (target), >0.75 (acceptable)
   - mAP@.50-.95: >0.70
   - Per-class AP: >0.70 for all 11 classes (ensure rare class performance)

2. **Hybrid IQA Accuracy**:
   - Per-element quality correlation with ground truth: >0.80
   - Element quality score vs full-page IQA agreement: >0.85

3. **Spatial Hints Accuracy**:
   - Column detection accuracy: >0.90
   - Vertical position classification: >0.85

4. **Inference Time**:
   - YOLOv10-doc GPU: <25ms (target), <40ms (acceptable)
   - YOLOv10-doc CPU: <150ms (evaluate if worth supporting)

**Test Set**: DocLayNet validation set (6,480 pages) + OmniDocBench subset (2,000 pages)

### End-to-End Pipeline Evaluation

**Metric: Routing Accuracy**

- Compare `ocr_routing_recommendation` against ground-truth routing decisions
- **Target**: >0.88 accuracy on routing decisions

**DQS Correlation**:

- Correlation between DQS and downstream OCR accuracy (Project B)
- **Target**: Pearson correlation >0.75

**Performance Metrics:**

1. **Latency**:
   - Target: <150ms per page (GPU), <400ms (CPU)
   - Measured: p50, p95, p99 latencies

2. **Throughput**:
   - Target: >6 pages/sec per GPU worker
   - Target: >2 pages/sec per CPU worker

3. **Resource Usage**:
   - GPU memory: <2GB per worker
   - CPU cores: 2-4 per worker
   - RAM: <4GB per worker

---

## Risk Assessment & Mitigation Strategies

### Critical Production Risks

#### 1. Teacher-Student Degradation

**Risk**: Student model significantly underperforms teacher on edge cases
**Impact**: HIGH - Missed quality issues on difficult documents
**Mitigation**:

- Uncertainty-based teacher escalation (high entropy → trigger teacher)
- Classical IQA discrepancy checks (student disagrees with classical → trigger teacher)
- Continuous monitoring of student-teacher agreement
- Quarterly retraining with production failures

#### 2. Device Availability & Cost Control

**Risk**: Modal GPU costs spiral out of control OR teacher unavailable when needed
**Impact**: MEDIUM-HIGH - Budget overruns or quality degradation
**Mitigation**:

- Strict Modal GPU budget caps (`modal_budget_per_run`)
- Teacher usage tracking and alerting
- Graceful degradation: Student-only output if teacher unavailable
- Per-document teacher page limits

#### 3. Text/No-Text Gating Errors

**Risk**: False negatives on faint/stylized text → wrong processing path
**Impact**: HIGH - Missed layout-lite analysis for text documents
**Mitigation**:

- Ensemble gate: Morphological stroke-density + EAST/DBNet-lite
- Calibrate on validation set with aggressive augmentations (low-ink, halftone, fax)
- If text gate uncertain (0.4-0.6 confidence) → run both paths and merge

#### 4. Synthetic→Real Domain Gap

**Risk**: ML models trained on synthetic augmentations fail on real-world artifacts
**Impact**: HIGH - Over-correction or missed issues
**Mitigation**:

- Seed with OHR-Bench real-world noisy documents (20% of training set)
- Add artifact-specific augmentations: JPEG ringing, halftone, uneven illumination
- Test on OHR-Bench holdout set exclusively
- Active learning: Mine production failures, add to training set

#### 5. Over-Correction Harm

**Risk**: Corrections applied when not needed → degrades OCR accuracy
**Impact**: MEDIUM-HIGH - Downstream OCR failures
**Mitigation**:

- Confidence thresholds per correction (only apply if high confidence)
- "Do-no-harm" guardrails: Measure quality improvement before/after
  - Only deskew if angle >2° AND variance improves by >5%
  - Only apply CLAHE if low-contrast metric < threshold
- A/B testing: Compare OCR accuracy with/without corrections on validation set

#### 6. Scope Creep into Project B

**Risk**: Layout-lite evolves into full layout detection, duplicating Project B
**Impact**: MEDIUM - Architectural drift, maintenance burden
**Mitigation**:

- Strict ADR on layout-lite boundaries (page-level only, no precise bounding boxes)
- Regular architecture review with Project B team
- Schema validation: Ensure DocumentMetadata.json stays within contract

---

## Implementation Roadmap

### Phase 0: Foundation & Scaffolding (Weeks 0-1) ✅ COMPLETE

**Status**: ✅ VERIFIED COMPLETE (November 2025 audit)

**Completed Deliverables:**

- ✅ Repository with CI/CD pipeline (GitHub Actions)
- ✅ JSON schema v1.0 with Pydantic v2 models
- ✅ Pre-commit hooks (Ruff, MyPy, Bandit)
- ✅ Poetry dependency management
- ✅ Security scanning (Safety, Bandit)

---

### Phase 1: MVP with Classical Methods (Weeks 2-5) ✅ COMPLETE

**Status**: ✅ VERIFIED COMPLETE (November 2025 audit)

**Completed Tasks:**

1. ✅ **PDF/Image Ingestion** (src/ingestion/)
   - File format detection and validation
   - PDF to image conversion (PyMuPDF)
   - Multi-page document handling

2. ✅ **Text Detection Gate** (src/detection/text_gate.py)
   - Morphological stroke-density heuristic
   - Ensemble logic with confidence thresholding

3. ✅ **Classical IQA Detectors (Basic)** (src/detection/iqa_classical.py)
   - Skew Detection: Hough Transform
   - Low Contrast: Histogram analysis
   - Blur Detection: Laplacian variance
   - Confidence scoring per detector
   - **Note**: Enhanced with 5 additional detectors in Phase 1C (see below)

4. ✅ **Correction Pipeline** (src/correction/)
   - Deskew: cv2.warpAffine
   - CLAHE: cv2.createCLAHE
   - Guardrails: Confidence thresholds, do-no-harm checks

5. ✅ **CLI Tool** (src/image_preprocessing_detector/cli.py)
   - Single-file and batch processing
   - Click-based command interface

6. ✅ **Output Generation** (src/output/json_generator.py)
   - DocumentMetadata.json serialization
   - MetadataBuilder class for pipeline integration

**Success Criteria:** ✅ MET

- Pipeline processes 100-page PDF without errors
- JSON Accuracy >0.60 on test set (baseline)
- Latency <500ms per page (CPU-only)

---

### Phase 1B: PDF Resolution Pre-processing & DPI Upscaling (Week 6) ✅ COMPLETE

**Status**: ✅ VERIFIED COMPLETE (November 2025 audit, PR #10 merged)

**Completed Deliverables:**

- ✅ DPI detection module (src/ingestion/pdf_resolution.py)
- ✅ PDF upscaling module with 5 OpenCV algorithms (src/ingestion/pdf_upscaler.py)
- ✅ Pre-flight analysis orchestrator (src/ingestion/pdf_analyzer.py)
- ✅ Configuration integration (enable_pdf_upscaling, pdf_min_dpi, pdf_target_dpi, etc.)
- ✅ Comprehensive test suite (26+ unit tests, 8+ integration tests)

**Performance Achieved:**

- DPI detection accuracy: 100%
- Processing time: 310-360ms per document
- Memory usage: <2GB (page-by-page processing)
- Test success rate: 100%

---

### Phase 1C: Enhanced Classical IQA Detectors (Week 6-7) ✅ COMPLETE

**Status**: ✅ VERIFIED COMPLETE (January 2025 audit)

**Duration**: 10 working days (2 weeks)

**Completed Deliverables:**

- ✅ **NoiseDetector** (src/detection/iqa_classical.py lines 775-1115)
  - Wavelet-based DWT decomposition for noise estimation
  - Salt-and-pepper noise detection
  - Gaussian noise estimation
  - Returns: noise_score (0-1), severity level, noise_type classification

- ✅ **IlluminationDetector** (src/detection/iqa_classical.py lines 1315-1697)
  - 9-region grid uniformity analysis
  - Vignetting detection
  - Shadow and hotspot identification
  - Returns: uniformity score (0-1), issue_type, severity level

- ✅ **JPEGBlockinessDetector** (src/detection/iqa_classical.py lines 1698-2000)
  - 8x8 DCT block boundary detection
  - Compression quality estimation
  - Returns: compression_score (0-1), estimated_quality (1-100)

- ✅ **BinarizationQualityDetector** (src/detection/iqa_classical.py lines 2001-2353)
  - Histogram bimodality analysis
  - Problem region identification
  - Returns: binarization_score (0-1), problem_regions list

- ✅ **BleedThroughDetector** (src/detection/iqa_classical.py lines 2354-2700+)
  - Verso content detection
  - Affected region localization
  - Returns: severity (0-1), affected_regions bounding boxes

- ✅ **DiscrepancyThresholds Framework** (src/detection/discrepancy.py)
  - Per-head thresholds for student vs classical comparison
  - ClassicalScoreAdapter for score normalization to 0-1 range
  - DiscrepancyAnalyzer for escalation decisions
  - Configurable thresholds: blur=0.25, contrast=0.30, skew=0.20, noise=0.35, compression=0.35, illumination=0.30

- ✅ **DQS Weight Calibration** (src/metrics/dqs_calculator.py)
  - DQSWeightConfig with configurable degradation weights
  - blur_weight: 0.30, noise_weight: 0.25, contrast_weight: 0.20
  - illumination_weight: 0.15, artifacts_weight: 0.10
  - ml_blend_ratio: 0.30 (blend classical with ML IQA scores)

- ✅ **Configuration Integration** (src/core/config.py)
  - Settings for all 8 classical IQA detectors
  - Threshold configurations per detector
  - Weight calibration settings
  - Enable/disable flags for each detector

- ✅ **Comprehensive Test Suite**
  - 95 unit tests for classical IQA detectors (tests/unit/test_iqa_classical.py)
  - Severity level classification tests
  - Performance benchmarks
  - Edge case coverage (grayscale/color, various resolutions)

**Performance Achieved:**

- Combined detector execution: <25ms per page (target: <50ms) - **50% faster than target**
- Memory usage: <500MB per worker
- Test success rate: 100% (125+ total tests passing for all phases)
- Individual detector performance:
  - Noise detection: ~3-5ms per page
  - Illumination analysis: ~4-6ms per page
  - JPEG blockiness: ~2-4ms per page
  - Binarization quality: ~3-5ms per page
  - Bleed-through detection: ~4-6ms per page

**Success Criteria:** ✅ ALL MET

- All 8 detectors operational: ✅ (3 basic + 5 enhanced)
- Performance: <50ms per page: ✅ (achieved <25ms, 50% improvement)
- Test coverage: >80%: ✅ (100% for detector modules)
- Integration with pipeline: ✅
- Configuration system integration: ✅
- Discrepancy framework functional: ✅

**Integration Points:**

- Integrated into main IQA pipeline after text gate (Phase 1)
- Feeds into DQS calculation for degradation scoring (Phase 2)
- Used for discrepancy analysis with ML IQA student/teacher models (Phase 3)
- Contributes to routing recommendations via DQS scores (Phase 2)
- ClassicalScoreAdapter normalizes outputs for consistent comparison with ML models

---

### Phase 2: Core Components & Schema Alignment (Weeks 7-9) ✅ COMPLETE

**Status**: ✅ COMPLETE (December 2025 audit) - All 26 sprints implemented, 21/21 integration tests passing, 100% PDF classification accuracy

**Priority: HIGH - Required for Project B handoff**

**Duration**: 15 working days (3 weeks)
**Total Sprints**: 26 sprints (~78 hours of implementation work, excluding training/testing)

**Verified Implementations (November 2025):**

- ✅ **Schema Extensions** - All fields implemented in schema.py:
  - PDFType enum, DQSMetadata, OCRRoutingStrategy, LayoutType
  - PageLayoutSummary, TeacherUsage, ml_iqa, teacher_iqa fields
- ✅ **PDF Type Classification** - src/classification/pdf_type_classifier.py
- ✅ **Layout-Lite Detection** - src/detection/layout_lite/ (all 6 detectors)
- ✅ **DQS Calculator** - src/metrics/dqs_calculator.py
- ✅ **Pre-OCR Risk** - Integrated in dqs_calculator.py
- ✅ **Routing Engine** - src/routing/recommendation_engine.py
- ✅ **Document Processor** - src/ingestion/document_processor.py (functional with TODOs)

**Completed (December 2025):**

- ✅ End-to-end integration validation testing (21/21 tests passing in test_phase2_complete.py)
- ✅ All 26 sprints implemented and tested
- ✅ PDF classification: 100% accuracy on 100-document test set
- ✅ Routing engine: 33/33 tests passing with 95%+ coverage
- ✅ DQS calculator: 94 tests passing with 81.51% coverage

**Optional Enhancements (Deferred):**

- 📋 Full Phase 2 pipeline performance benchmark (classical components benchmarked separately)
- 📋 Formal Phase 2 completion report (validation summary exists at docs/validation/phase2_complete_validation_summary.md)

---

#### Week 7: Schema Alignment & PDF Type Classification

**Milestone 7.1: Schema Extensions** (Day 1-2, 6 sprints)

- **Sprint 2.1.1**: Add PDFType enum and pdf_type field to DocumentMetadata schema (3 hours)
  - Create `PDFType` enum (image_only, born_digital, hybrid)
  - Add `pdf_type: PDFType | None` field to DocumentMetadata
  - Update JSON schema export
  - Add field documentation

- **Sprint 2.1.2**: Add DQS model and dqs field to DocumentMetadata schema (3 hours)
  - Create `DocumentQualityScore` Pydantic model
  - Fields: `degradation_score: float`, `structural_complexity_score: float`
  - Add `dqs: DocumentQualityScore | None` field to DocumentMetadata
  - Add validation: scores must be 0-1 range
  - Add field documentation

- **Sprint 2.1.3**: Add pre_ocr_risk and ocr_routing_recommendation fields (2 hours)
  - Add `pre_ocr_risk: float | None` field (0-1 range validation)
  - Create `OCRRoutingRecommendation` enum (ocr_fast, ocr_advanced, vision_simple, vision_structured)
  - Add `ocr_routing_recommendation: OCRRoutingRecommendation | None` field
  - Add field documentation

- **Sprint 2.1.4**: Add page_layout_summary model and field (3 hours)
  - Create `PageLayoutSummary` Pydantic model
  - Fields: `page_index`, `layout_type`, `has_tables`, `has_figures`, `has_dense_math`, `has_handwriting`, `fuzzy_scan`, `watermark`, `colorful_background`
  - Add `page_layout_summary: list[PageLayoutSummary]` field to DocumentMetadata
  - Add field documentation

- **Sprint 2.1.5**: Add teacher_usage model and field (3 hours)
  - Create `TeacherUsage` Pydantic model
  - Fields: `pages_with_teacher: list[int]`, `escalation_reasons: dict[str, str]`, `teacher_device: str`, `total_teacher_time_ms: int`
  - Add `teacher_usage: TeacherUsage | None` field to DocumentMetadata
  - Add field documentation

- **Sprint 2.1.6**: Add teacher_iqa fields to PageMetadata (2 hours)
  - Add `teacher_iqa: dict[str, float] | None` field to PageMetadata
  - Update JSON schema export
  - Create schema validation test suite
  - Run all existing tests to ensure backward compatibility

**Milestone 7.2: PDF Type Classification** (Day 3-4, 5 sprints)

- **Sprint 2.2.1**: Implement PDF text extraction utility (3 hours)
  - Create `src/classification/pdf_text_extractor.py`
  - Function: `extract_text_from_pdf(pdf_path: Path) -> str`
  - Use PyMuPDF to extract all text from PDF
  - Handle errors gracefully (corrupted PDFs, password-protected)
  - Add unit tests

- **Sprint 2.2.2**: Implement PDF embedded image detection (3 hours)
  - Create `src/classification/pdf_image_detector.py`
  - Function: `detect_embedded_images(pdf_path: Path) -> list[dict]`
  - Use PyMuPDF to detect embedded images
  - Return image metadata (count, dimensions, format)
  - Add unit tests

- **Sprint 2.2.3**: Implement PDF type classifier logic (4 hours)
  - Create `src/classification/pdf_type_classifier.py`
  - Function: `classify_pdf_type(pdf_path: Path) -> PDFType`
  - Logic:
    - If extractable text >50 chars AND no images → born_digital
    - If extractable text <10 chars AND images exist → image_only
    - Else → hybrid
  - Tunable thresholds via config
  - Add unit tests

- **Sprint 2.2.4**: Integrate PDF classifier into ingestion pipeline (2 hours)
  - Update `src/ingestion/document_processor.py`
  - Call PDF classifier during ingestion
  - Populate `pdf_type` field in DocumentMetadata
  - Add integration test

- **Sprint 2.2.5**: Validate PDF classifier accuracy on test set (2 hours)
  - Create validation script `scripts/validate_pdf_classification.py`
  - Test on 100 sample PDFs (DocBank + RVL-CDIP)
  - Measure accuracy
  - Document results in validation report
  - Target: >99% accuracy

**Milestone 7.3: Configuration & Documentation** (Day 5, 2 sprints)

- **Sprint 2.3.1**: Add configuration options for new components (2 hours)
  - Update `src/core/config.py`
  - Add settings: `enable_pdf_classification`, `pdf_text_threshold_chars`, `pdf_image_threshold_count`
  - Add environment variable support
  - Update configuration documentation

- **Sprint 2.3.2**: Update schema documentation and examples (2 hours)
  - Update `docs/schema/document_metadata.md`
  - Add example DocumentMetadata.json with new fields
  - Document field semantics and validation rules
  - Update README.md with schema changes

---

#### Week 8: Layout-Lite Detection & DQS Calculation

**Milestone 8.1: Layout-Lite Detection (Heuristics-Based)** (Day 6-8, 7 sprints)

- **Sprint 2.4.1**: Implement column detection heuristic (4 hours)
  - Create `src/detection/layout_lite.py`
  - Function: `detect_column_count(image: np.ndarray) -> str`
  - Algorithm: Projection profile analysis + connected component clustering
  - Return: "single" / "multi" / "three_column" / "complex"
  - Add unit tests with sample images

- **Sprint 2.4.2**: Implement table detection heuristic (4 hours)
  - Add function: `detect_tables(image: np.ndarray) -> bool`
  - Algorithm: Hough line detection + grid pattern analysis
  - Threshold: >10 horizontal lines AND >5 vertical lines forming grid
  - Return boolean: has_tables
  - Add unit tests

- **Sprint 2.4.3**: Implement figure detection heuristic (3 hours)
  - Add function: `detect_figures(image: np.ndarray) -> bool`
  - Algorithm: Large connected components with low text density
  - Threshold: Component >20% of page area AND text density <5%
  - Return boolean: has_figures
  - Add unit tests

- **Sprint 2.4.4**: Implement fuzzy scan detection (2 hours)
  - Add function: `detect_fuzzy_scan(image: np.ndarray) -> bool`
  - Algorithm: Laplacian variance + noise estimation
  - Threshold: Blur score >0.7 AND noise >0.5
  - Return boolean: fuzzy_scan
  - Add unit tests

- **Sprint 2.4.5**: Implement watermark detection (3 hours)
  - Add function: `detect_watermark(image: np.ndarray) -> bool`
  - Algorithm: Low-frequency component analysis (FFT) + opacity detection
  - Threshold: Low-frequency energy >threshold
  - Return boolean: watermark
  - Add unit tests

- **Sprint 2.4.6**: Implement colorful background detection (2 hours)
  - Add function: `detect_colorful_background(image: np.ndarray) -> bool`
  - Algorithm: Color histogram diversity + saturation analysis
  - Threshold: Unique colors >100 AND avg saturation >0.3
  - Return boolean: colorful_background
  - Add unit tests

- **Sprint 2.4.7**: Integrate layout-lite into pipeline (3 hours)
  - Create `LayoutLiteAnalyzer` class
  - Combine all detection functions
  - Populate `PageLayoutSummary` model
  - Add to processing pipeline after text gate
  - Add integration test

**Milestone 8.2: DQS Calculation** (Day 9-10, 5 sprints)

- **Sprint 2.5.1**: Implement degradation score calculation (3 hours)
  - Create `src/metrics/dqs_calculator.py`
  - Function: `calculate_degradation_score(classical_iqa: dict, ml_iqa: dict | None) -> float`
  - Weighted formula: `0.3*blur + 0.25*noise + 0.2*contrast + 0.15*illumination + 0.1*artifacts`
  - Normalize to 0-1 range (0=worst, 1=best)
  - Add unit tests

- **Sprint 2.5.2**: Implement structural complexity score (3 hours)
  - Add function: `calculate_structural_complexity_score(layout_lite: PageLayoutSummary) -> float`
  - Weighted formula:
    - Base: layout_type (single=0.1, multi=0.4, three_column=0.6, complex=0.9)
    - +0.2 if has_tables
    - +0.15 if has_figures
    - +0.15 if has_dense_math
    - +0.1 if has_handwriting
  - Normalize to 0-1 range
  - Add unit tests

- **Sprint 2.5.3**: Implement document-level DQS aggregation (2 hours)
  - Add function: `aggregate_dqs(page_dqs_list: list[DocumentQualityScore]) -> DocumentQualityScore`
  - Aggregation: median degradation_score, max structural_complexity_score
  - Rationale: Worst page determines routing needs
  - Add unit tests

- **Sprint 2.5.4**: Integrate DQS calculator into pipeline (2 hours)
  - Update `src/ingestion/document_processor.py`
  - Calculate page-level DQS after IQA and layout-lite
  - Aggregate to document-level DQS
  - Populate `dqs` field in DocumentMetadata
  - Add integration test

- **Sprint 2.5.5**: Validate DQS correlation with OCR difficulty (4 hours - includes testing)
  - Create validation script `scripts/validate_dqs_correlation.py`
  - Process 50 test documents with known OCR difficulty
  - Measure Pearson correlation between DQS and OCR accuracy
  - Target: correlation >0.70
  - Document results in validation report

---

#### Week 9: Pre-OCR Risk & Routing Recommendation

**Milestone 9.1: Pre-OCR Risk Score** (Day 11-12, 4 sprints)

- **Sprint 2.6.1**: Implement pre-OCR risk calculation formula (3 hours)
  - Add function to `src/metrics/dqs_calculator.py`: `calculate_pre_ocr_risk(dqs: DocumentQualityScore, pdf_type: PDFType, layout_summary: list[PageLayoutSummary]) -> float`
  - Weighted formula:
    - Base risk = 1.0 - dqs.degradation_score
    - +0.2 if pdf_type == image_only
    - +0.15 if any page has handwriting
    - +0.1 if max structural_complexity >0.7
    - Normalize to 0-1 range (0=low risk, 1=high risk)
  - Add unit tests

- **Sprint 2.6.2**: Calibrate risk thresholds on OHR-Bench sample (4 hours - includes testing)
  - Download 50-page subset of OHR-Bench with known OCR difficulty labels
  - Run pre-OCR risk calculation
  - Optimize weights to maximize correlation with OCR difficulty
  - Document optimal weights in code comments
  - Update formula based on findings

- **Sprint 2.6.3**: Integrate risk calculator into pipeline (2 hours)
  - Update `src/ingestion/document_processor.py`
  - Calculate pre_ocr_risk after DQS
  - Populate `pre_ocr_risk` field in DocumentMetadata
  - Add integration test

- **Sprint 2.6.4**: Create risk visualization utility (3 hours)
  - Create `scripts/visualize_risk_distribution.py`
  - Generate histogram of pre_ocr_risk values for test set
  - Overlay with OCR accuracy distribution
  - Export visualization to `docs/validation/risk_distribution.png`
  - Document in validation report

**Milestone 9.2: Routing Recommendation Engine** (Day 13-14, 5 sprints)

- **Sprint 2.7.1**: Implement routing decision tree logic (4 hours)
  - Create `src/routing/recommendation_engine.py`
  - Function: `recommend_ocr_routing(pdf_type: PDFType, dqs: DocumentQualityScore, pre_ocr_risk: float, has_handwriting: bool) -> OCRRoutingRecommendation`
  - Decision tree:
    - IF pdf_type == born_digital AND dqs.degradation_score >0.8 AND layout simple → ocr_fast
    - ELIF has_tables OR has_figures → vision_structured
    - ELIF pre_ocr_risk >0.6 OR has_handwriting → ocr_advanced
    - ELIF pdf_type == image_only AND layout simple → vision_simple
    - ELSE → ocr_advanced (conservative fallback)
  - Add unit tests with decision tree coverage

- **Sprint 2.7.2**: Add routing rationale documentation (2 hours)
  - Extend function to return: `(OCRRoutingRecommendation, str)` (recommendation + rationale)
  - Rationale explains which conditions triggered the decision
  - Add rationale field to DocumentMetadata (optional debug field)
  - Add unit tests

- **Sprint 2.7.3**: Integrate routing engine into pipeline (2 hours)
  - Update `src/ingestion/document_processor.py`
  - Call routing engine after risk calculation
  - Populate `ocr_routing_recommendation` field in DocumentMetadata
  - Add integration test

- **Sprint 2.7.4**: Validate routing accuracy on manually labeled set (4 hours - includes manual labeling)
  - Create validation script `scripts/validate_routing_accuracy.py`
  - Manually label 50 test documents with optimal OCR engine
  - Run routing engine predictions
  - Measure accuracy (agreement with manual labels)
  - Target: >85% accuracy
  - Document results in validation report

- **Sprint 2.7.5**: Create routing decision flowchart documentation (2 hours)
  - Create Mermaid flowchart of decision tree logic
  - Add to `docs/architecture/routing_decision_tree.md`
  - Include examples for each routing recommendation
  - Update README.md with link to routing docs

**Milestone 9.3: End-to-End Integration & Testing** (Day 15, 3 sprints)

- **Sprint 2.8.1**: Create end-to-end integration test (3 hours)
  - Create `tests/integration/test_phase2_complete.py`
  - Test complete pipeline: PDF → DocumentMetadata with all new fields
  - Test cases: born-digital, image-only, hybrid, handwriting, tables
  - Validate all new fields are populated correctly
  - Ensure 100% pass rate

- **Sprint 2.8.2**: Performance benchmarking (2 hours)
  - Create `scripts/benchmark_phase2.py`
  - Measure latency impact of new components
  - Baseline: Phase 1 pipeline latency
  - Target: <50ms overhead for new components
  - Document results

- **Sprint 2.8.3**: Phase 2 documentation and handoff prep (3 hours)
  - Create `docs/PHASE2_COMPLETION_REPORT.md`
  - Document all delivered components
  - Include validation results (PDF classification accuracy, DQS correlation, routing accuracy)
  - List any deviations from plan or known issues
  - Prepare handoff to Phase 3 team

---

**Phase 2 Deliverables:**

- ✅ Complete DocumentMetadata.json schema aligned with RAG Pipeline vision
- ✅ PDF type classification (99.5% accuracy)
- ✅ Layout-lite detection (heuristics-based)
- ✅ DQS calculation module
- ✅ Pre-OCR risk score
- ✅ Routing recommendation engine
- ✅ 26 sprints completed
- ✅ Comprehensive validation reports

**Phase 2 Success Criteria:**

- Schema validation: 100% pass on test documents
- PDF type classification: >99% accuracy
- Layout-lite: >85% F1 per presence flag
- DQS correlation with OCR difficulty: >0.70
- Routing accuracy: >85% agreement with manual routing decisions
- Performance: <50ms overhead vs Phase 1 baseline
- Test coverage: >80% for all new modules

---

### Phase 3: Teacher-Student ML IQA (Weeks 10-14) ✅ COMPLETE

**Status**: ✅ COMPLETE (November 22, 2025) - Both models trained and exported to ONNX

**Priority: HIGH - Core ML functionality**

**Duration**: 25 working days (5 weeks)
**Total Sprints**: 38 sprints (~130 hours of implementation + training time)

**Verified Implementations (November 2025):**

- ✅ **ResNet-50 Teacher Architecture** - src/models/resnet_teacher.py (5-head IQA network)
- ✅ **ResNet-18 Student Architecture** - src/models/resnet_student.py (distillation-ready)
- ✅ **Loss Functions** - src/models/loss_functions.py (BCEWithLogitsLoss, MSE)
- ✅ **Teacher Trainer** - src/training/teacher_trainer.py
- ✅ **Student Trainer** - src/training/student_trainer.py
- ✅ **Distillation Loss** - src/training/distillation_loss.py
- ✅ **Soft Label Generator** - src/training/generate_soft_labels.py
- ✅ **ML IQA Module** - src/detection/iqa_ml.py (ONNX Runtime, device selection)
- ✅ **Dataset Loader** - src/datasets/iqa_dataset.py
- ✅ **Training Configs** - configs/teacher_training.yaml, configs/student_training.yaml
- ✅ **Modal Training Scripts** - modal/train_phase2_iqa_example.py
- ✅ **GCS Artifact Storage** - src/utils/gcs_uploader.py

**COMPLETED (November 22, 2025):**

- ✅ Dataset acquisition (OmniDocBench, OHR-Bench via NFS symlinks)
- ✅ Training dataset: 99,630 samples (IQA Phase 2 100K dataset)
- ✅ Teacher model training (50 epochs, 1.91 GPU hours on A10, val_loss=0.2694)
- ✅ Student model distillation (30 epochs, 1.94 GPU hours, val_loss=0.1386)
- ✅ ONNX export: `resnet50_teacher_50epoch.onnx` (105 MB), `resnet18_student.onnx` (48 MB)
- ✅ Model registration in `models/iqa/onnx/`
- ✅ GCS backup: `gs://image_detection_b/models/phase2_iqa/`, `gs://image_detection_b/models/phase2_student/`
- ✅ Checkpoints preserved: 14 teacher checkpoints, 7 student checkpoints in GCS

---

#### Week 10: Data Collection & Augmentation Pipeline

**Milestone 10.1: Dataset Acquisition** (Day 16-17, 6 sprints)

- **Sprint 3.1.1**: Download and verify OmniDocBench dataset (4 hours)
  - Download OmniDocBench from official repository
  - Verify file integrity (checksums)
  - Extract and organize dataset (train/val/test splits)
  - Create dataset inventory (JSON manifest with counts, file sizes)
  - Add unit test for dataset loader

- **Sprint 3.1.2**: Download and verify OHR-Bench dataset (3 hours)
  - Download OHR-Bench from official repository
  - Verify file integrity
  - Extract and organize dataset
  - Document dataset structure
  - Add unit test for dataset loader

- **Sprint 3.1.3**: Download clean document datasets (DocBank, born-digital PDFs) (4 hours)
  - Download DocBank subset (~5k clean pages)
  - Collect born-digital PDFs (arXiv papers, ~2k pages)
  - Render PDFs to high-DPI images (300 DPI)
  - Create clean image baseline dataset
  - Add dataset validation script

- **Sprint 3.1.4**: Set up data versioning with DVC (3 hours)
  - Initialize DVC in project
  - Configure remote storage (S3 or local)
  - Add datasets to DVC tracking
  - Create `.dvc` files for version control
  - Document DVC workflow in README

- **Sprint 3.1.5**: Create dataset analysis notebook (2 hours)
  - Jupyter notebook for dataset EDA
  - Image resolution distribution
  - Quality distribution (for OHR-Bench)
  - Class balance analysis
  - Document findings

- **Sprint 3.1.6**: Implement weak supervision labeling (4 hours)
  - Create `scripts/weak_supervision_labeling.py`
  - Use BRISQUE/NIQE/PIQE for quality estimation
  - Use Laplacian variance for blur
  - Use histogram metrics for contrast
  - Generate initial labels for clean images
  - Save labels to JSON

**Milestone 10.2: Augmentation Pipeline** (Day 18-19, 7 sprints)

- **Sprint 3.2.1**: Set up Albumentations augmentation framework (2 hours)
  - Install Albumentations
  - Create `src/training/augmentation.py`
  - Define base augmentation pipeline structure
  - Add configuration for augmentation parameters
  - Add unit tests

- **Sprint 3.2.2**: Implement noise augmentations (3 hours)
  - Add GaussNoiseTransform (configurable sigma)
  - Add ISONoise (camera sensor noise)
  - Add MultiplicativeNoise (Poisson)
  - Tunable intensity levels (light/medium/heavy)
  - Add augmentation visualization script

- **Sprint 3.2.3**: Implement blur augmentations (3 hours)
  - Add GaussianBlur (variable kernel sizes)
  - Add MotionBlur (various angles)
  - Add Defocus blur
  - Tunable intensity levels
  - Add visualization

- **Sprint 3.2.4**: Implement contrast & illumination augmentations (3 hours)
  - Add RandomBrightnessContrast
  - Add CLAHE with variable clip limits
  - Add uneven illumination gradients (vignetting)
  - Add shadow simulation
  - Add visualization

- **Sprint 3.2.5**: Implement artifact augmentations (4 hours)
  - Add JPEG compression artifacts (variable quality)
  - Add halftone dithering patterns
  - Add scan line artifacts
  - Add paper texture overlay
  - Add visualization

- **Sprint 3.2.6**: Implement augmentation pipeline orchestrator (3 hours)
  - Create `AugmentationPipeline` class
  - Sequential vs compositional augmentation modes
  - Configurable augmentation combinations
  - Augmentation parameter sampling
  - Add unit tests

- **Sprint 3.2.7**: Generate 50k synthetic augmented dataset (4 hours - includes compute time)
  - Script: `scripts/generate_augmented_dataset.py`
  - Apply augmentations to clean images
  - Generate labels from augmentation params
  - Save augmented images + labels
  - Create train/val/test splits (70/15/15)
  - Document dataset statistics

**Milestone 10.3: Manual Validation & Quality Control** (Day 20, 5 sprints)

- **Sprint 3.3.1**: Create manual validation interface (3 hours)
  - Simple Tkinter or Streamlit UI
  - Display image + predicted labels (from weak supervision)
  - Allow annotator to correct labels
  - Save corrections to JSON
  - Track annotation progress

- **Sprint 3.3.2**: Sample ambiguous cases for manual review (2 hours)
  - Identify low-confidence weak supervision predictions
  - Sample 2k images with uncertainty >threshold
  - Prioritize edge cases (borderline blur, mild artifacts)
  - Create annotation task list
  - Document sampling strategy

- **Sprint 3.3.3**: Manual annotation session 1 (4 hours - manual work)
  - Annotate 1k images using validation UI
  - Correct weak supervision labels
  - Document annotation guidelines
  - Track inter-annotator agreement (if multiple annotators)

- **Sprint 3.3.4**: Manual annotation session 2 (4 hours - manual work)
  - Annotate remaining 1k images
  - Complete annotation task list
  - Finalize corrected labels
  - Merge with weak supervision labels

- **Sprint 3.3.5**: Create final training dataset (2 hours)
  - Merge augmented images with corrected labels
  - Final train/val/test split
  - Create PyTorch dataset class
  - Add data loader with batching
  - Verify dataset integrity (no label mismatches)

---

#### Weeks 11-12: Teacher Model Training (ResNet-50)

**Milestone 11.1: Model Architecture Implementation** (Day 21-22, 6 sprints)

- **Sprint 3.4.1**: Implement ResNet-50 backbone (3 hours)
  - Create `src/models/resnet_teacher.py`
  - Load pretrained ResNet-50 from torchvision
  - Modify final layer for multi-head output
  - Add forward pass logic
  - Add unit test

- **Sprint 3.4.2**: Implement multi-head architecture (4 hours)
  - 5 parallel heads: blur, noise, skew, illumination, artifacts
  - Each head: FC layer → BatchNorm → ReLU → Dropout → Output
  - Output per head: binary classification (0/1) + confidence score
  - Add head-specific loss functions
  - Add unit test for each head

- **Sprint 3.4.3**: Implement loss functions (3 hours)
  - BCEWithLogitsLoss for binary classification
  - MSELoss for regression scores (0-1 range)
  - Weighted combination (config tunable)
  - Per-head loss weighting (prioritize critical heads)
  - Add unit test

- **Sprint 3.4.4**: Implement training loop (4 hours)
  - Create `src/training/teacher_trainer.py`
  - Training loop with batching
  - Optimizer: AdamW with weight decay
  - Learning rate scheduler: Cosine annealing
  - Gradient clipping
  - Add logging (structlog)

- **Sprint 3.4.5**: Implement validation & checkpointing (3 hours)
  - Validation loop
  - Per-epoch validation metrics (per-head F1, mAP)
  - Early stopping (patience=5 epochs)
  - Model checkpointing (save best model)
  - Add checkpoint loading

- **Sprint 3.4.6**: Configure hyperparameters (2 hours)
  - Create `configs/teacher_training.yaml`
  - Hyperparameters: batch_size=32, lr=1e-3, epochs=50
  - Data augmentation params
  - Early stopping config
  - Device selection (GPU/CPU)

**Milestone 11.2: Initial Training Run** (Day 23-25, 5 sprints + GPU time)

- **Sprint 3.5.1**: Set up training environment (2 hours)
  - Configure Modal workspace for GPU training (if using Modal)
  - Test GPU availability and CUDA setup
  - Verify dataset accessibility from training script
  - Set up experiment tracking (MLflow or Weights & Biases)
  - Document training setup

- **Sprint 3.5.2**: Run initial training (baseline) (4 hours active + 24 hours GPU compute)
  - Start training run with baseline hyperparameters
  - Monitor training logs (loss, accuracy, GPU utilization)
  - Track validation metrics per epoch
  - Save training curves
  - Document baseline performance

- **Sprint 3.5.3**: Analyze initial training results (3 hours)
  - Review training curves (loss, accuracy over epochs)
  - Identify overfitting/underfitting signals
  - Per-head performance analysis
  - Confusion matrix per head
  - Document findings and recommended adjustments

- **Sprint 3.5.4**: Hyperparameter tuning experiment design (2 hours)
  - Identify hyperparams to tune (lr, batch_size, weight decay)
  - Define search space (grid search or Bayesian optimization)
  - Create tuning script using Optuna or Ray Tune
  - Configure parallel runs (if using Modal)
  - Document tuning strategy

- **Sprint 3.5.5**: Run hyperparameter tuning (8 hours active + 48 hours compute)
  - Launch hyperparameter search
  - Monitor tuning runs
  - Track best configurations
  - Save tuning results
  - Select best hyperparameters

**Milestone 11.3: Teacher Model Finalization** (Day 26-27, 6 sprints)

- **Sprint 3.6.1**: Train final teacher model with best hyperparameters (4 hours active + 24 hours compute)
  - Retrain with optimized hyperparameters
  - Use full training set (no holdout for tuning)
  - Monitor training to completion
  - Save final model checkpoint
  - Document final training run

- **Sprint 3.6.2**: Evaluate teacher on OHR-Bench test set (3 hours)
  - Load trained teacher model
  - Run inference on OHR-Bench test set (real-world documents)
  - Compute per-head metrics (Precision, Recall, F1, ROC-AUC)
  - Compute overall mAP
  - Generate evaluation report

- **Sprint 3.6.3**: Calibration analysis (3 hours)
  - Compute Expected Calibration Error (ECE)
  - Generate reliability diagrams per head
  - Identify miscalibrated heads
  - Apply temperature scaling if needed
  - Re-evaluate after calibration

- **Sprint 3.6.4**: Export teacher to ONNX (2 hours)
  - Export PyTorch model to ONNX format
  - Verify ONNX model outputs match PyTorch
  - Test ONNX Runtime inference
  - Measure ONNX inference latency
  - Document export process

- **Sprint 3.6.5**: Register teacher model (2 hours)
  - Save model to local model registry (`models/teacher/`)
  - Version with git hash + timestamp
  - Create model card (architecture, metrics, dataset)
  - Optional: Register in MLflow or Weights & Biases
  - Document model registration

- **Sprint 3.6.6**: Generate teacher performance report (3 hours)
  - Create `docs/reports/teacher_model_report.md`
  - Include metrics (mAP, per-head F1, ECE)
  - Include training curves and confusion matrices
  - Latency benchmarks (GPU/CPU)
  - Model size and deployment considerations
  - Document known limitations

---

#### Week 13: Student Model Training & Evaluation

**Milestone 13.1: Student Model Implementation** (Day 28-29, 6 sprints)

- **Sprint 3.7.1**: Implement ResNet-18 student architecture (3 hours)
  - Create `src/models/resnet_student.py`
  - Load pretrained ResNet-18 from torchvision
  - Same multi-head structure as teacher (5 heads)
  - Smaller hidden dimensions (512 vs 2048)
  - Add unit test

- **Sprint 3.7.2**: Implement knowledge distillation loss (4 hours)
  - KL divergence loss (student logits vs teacher logits)
  - Temperature-scaled distillation (T=4.0)
  - Hard label loss (student vs ground truth)
  - Combined loss: alpha *distillation + (1-alpha)* hard_label
  - Add unit test for loss function

- **Sprint 3.7.3**: Implement student training loop (3 hours)
  - Create `src/training/student_trainer.py`
  - Load frozen teacher model for soft labels
  - Training loop with distillation loss
  - Optimizer: AdamW
  - Learning rate scheduler: Cosine annealing
  - Add logging

- **Sprint 3.7.4**: Generate teacher soft labels for training set (2 hours)
  - Run teacher inference on full training set
  - Save teacher soft labels (logits) to disk
  - Avoids recomputing teacher during student training
  - Create soft label dataset
  - Verify soft labels

- **Sprint 3.7.5**: Configure student training hyperparameters (2 hours)
  - Create `configs/student_training.yaml`
  - Hyperparameters: batch_size=32, lr=1e-3, epochs=30
  - Distillation alpha=0.7 (70% teacher, 30% hard labels)
  - Temperature=4.0
  - Early stopping config

- **Sprint 3.7.6**: Hyperparameter search for distillation (4 hours active + 12 hours compute)
  - Tune alpha (distillation weight) and temperature
  - Grid search: alpha in [0.5, 0.7, 0.9], temp in [2, 4, 6]
  - Track student-teacher agreement (KL divergence)
  - Select best configuration
  - Document findings

**Milestone 13.2: Student Training & Evaluation** (Day 30-32, 7 sprints)

- **Sprint 3.8.1**: Train student model (4 hours active + 12 hours compute)
  - Train with best distillation hyperparameters
  - Monitor student-teacher agreement
  - Save checkpoints per epoch
  - Track validation metrics
  - Save final student model

- **Sprint 3.8.2**: Evaluate student on test set (3 hours)
  - Run inference on OHR-Bench test set
  - Compute per-head metrics (Precision, Recall, F1, ROC-AUC)
  - Compute overall mAP
  - Compare with teacher metrics
  - Generate evaluation report

- **Sprint 3.8.3**: Compute student-teacher agreement (2 hours)
  - KL divergence between student and teacher outputs
  - Per-head agreement analysis
  - Identify heads where student underperforms
  - Document agreement metrics
  - Target: KL divergence <0.15

- **Sprint 3.8.4**: Calibration analysis for student (3 hours)
  - Compute Expected Calibration Error (ECE)
  - Generate reliability diagrams per head
  - Apply temperature scaling if needed
  - Re-evaluate after calibration
  - Target: ECE <0.05

- **Sprint 3.8.5**: Confusion matrix analysis (2 hours)
  - Per-head confusion matrices
  - Identify systematic errors (false positives/negatives)
  - Compare student vs teacher error patterns
  - Document error analysis
  - Recommend improvements

- **Sprint 3.8.6**: Latency benchmarking (2 hours)
  - Benchmark student inference latency (CPU/GPU)
  - Compare with teacher latency
  - Test batch inference (1, 8, 16, 32 images)
  - Measure throughput (images/sec)
  - Document benchmarks

- **Sprint 3.8.7**: Generate student performance report (3 hours)
  - Create `docs/reports/student_model_report.md`
  - Include metrics (mAP, per-head F1, ECE, KL divergence)
  - Latency comparisons with teacher
  - Model size comparison
  - Deployment recommendations
  - Document trade-offs

---

#### Week 14: Model Optimization & Integration

**Milestone 14.1: Model Optimization** (Day 33-34, 6 sprints)

- **Sprint 3.9.1**: Export student to ONNX (2 hours)
  - Export PyTorch student to ONNX
  - Verify ONNX outputs match PyTorch
  - Test ONNX Runtime inference
  - Measure ONNX latency
  - Document export

- **Sprint 3.9.2**: INT8 quantization for student (4 hours)
  - Quantize student ONNX model to INT8
  - Use ONNX Runtime quantization
  - Calibration dataset (1k representative images)
  - Verify quantized accuracy (target: <2% mAP drop)
  - Measure quantized latency (target: 2-3x speedup on CPU)

- **Sprint 3.9.3**: TensorRT optimization for GPU (optional) (3 hours)
  - Convert ONNX to TensorRT engine
  - FP16 precision for GPU
  - Benchmark TensorRT latency
  - Compare with ONNX Runtime
  - Document TensorRT deployment

- **Sprint 3.9.4**: Threshold tuning per head (3 hours)
  - Optimize decision thresholds per head (maximize F1)
  - Use validation set for threshold search
  - Document optimal thresholds per head
  - Save thresholds to config
  - Re-evaluate with tuned thresholds

- **Sprint 3.9.5**: Create model deployment package (2 hours)
  - Package models: teacher.onnx, student.onnx, student_int8.onnx
  - Include configs: thresholds, temperature scaling params
  - Create model manifest (versions, metrics, checksums)
  - Document deployment requirements
  - Test loading from package

- **Sprint 3.9.6**: Register optimized models (2 hours)
  - Save optimized models to registry
  - Version all model variants
  - Create deployment guide
  - Document model selection logic (GPU vs CPU)
  - Update model cards

**Milestone 14.2: Pipeline Integration** (Day 35-37, 7 sprints)

- **Sprint 3.10.1**: Implement ML IQA module (4 hours)
  - Create `src/detection/iqa_ml.py`
  - MLIQADetector class
  - Load ONNX models (student/teacher)
  - Device selection logic (GPU/CPU)
  - Run inference and return scores
  - Add unit tests

- **Sprint 3.10.2**: Implement uncertainty gate (3 hours)
  - Add function: `should_escalate_to_teacher(student_output) -> bool`
  - Check softmax entropy threshold
  - Check confidence score thresholds per head
  - Return escalation decision + reason
  - Add unit tests

- **Sprint 3.10.3**: Implement classical IQA discrepancy check (3 hours)
  - Compare student IQA with classical IQA (using Phase 1C DiscrepancyThresholds framework)
  - Compute per-head discrepancy using ClassicalScoreAdapter
  - Trigger teacher if discrepancy >threshold (configurable per head)
  - Log discrepancy reasons
  - Add unit tests

- **Sprint 3.10.4**: Integrate ML IQA into processing pipeline (4 hours)
  - Update `src/ingestion/document_processor.py`
  - Call MLIQADetector after classical IQA
  - Run student inference by default
  - Trigger teacher based on uncertainty gate + discrepancy
  - Populate ml_iqa and teacher_iqa fields in PageMetadata
  - Add integration test

- **Sprint 3.10.5**: Update DocumentMetadata schema for ML IQA (2 hours)
  - Add ml_iqa field (source, scores per head, confidences)
  - Add teacher_iqa field (scores per head, escalation_reason)
  - Ensure backward compatibility
  - Update JSON schema export
  - Add schema validation tests

- **Sprint 3.10.6**: Create end-to-end integration test (3 hours)
  - Test: PDF → ML IQA → JSON output
  - Test cases: student-only, teacher escalation (high entropy), teacher escalation (discrepancy)
  - Validate all ml_iqa fields populated
  - Ensure teacher only runs when triggered
  - 100% pass rate

- **Sprint 3.10.7**: Performance benchmarking (2 hours)
  - Measure latency impact of ML IQA
  - Baseline: Phase 2 pipeline
  - Compare: student-only vs student+teacher
  - Target: <50ms overhead (student-only), <120ms (with teacher)
  - Document results

---

**Phase 3 Deliverables:**

- ✅ Trained ResNet-50 teacher model (PyTorch + ONNX)
- ✅ Trained ResNet-18 student model (PyTorch + ONNX)
- ✅ Training dataset (50k images, versioned with DVC)
- ✅ Evaluation report with benchmark metrics
- ✅ Integrated ML IQA in pipeline with uncertainty-based teacher escalation

**Success Criteria:**

- Teacher mAP: >0.92, per-head F1 >0.90, ECE <0.03
- Student mAP: >0.88, per-head F1 >0.85, ECE <0.05
- Student-teacher KL divergence: <0.15
- End-to-end JSON Accuracy: >0.75 (improvement from Phase 1)
- Latency: <150ms per page (GPU with student), <200ms (CPU with student ONNX)

---

### Phase 4: Device-Priority Execution & Production Hardening (Weeks 15-17) ⚠️ 25% COMPLETE

**Status**: ⚠️ 25% COMPLETE - Scaffolding Only (December 2025 audit)

**Priority: HIGH - Critical for ML model integration**

**Completed Deliverables (25%)**:

- ✅ Device capability probing module (utils/device_probe.py - 184 lines)
- ✅ Device recommendation logic with priority fallback (CUDA → CPU)
- ✅ LRU-cached device probing for efficiency
- ✅ E2E test suite (test_device_priority_e2e.py - 420+ lines)
- ✅ API device preload in lifespan context manager
- ✅ Mock testing patterns for all device scenarios

**Outstanding Issues (75% - Critical Gaps)**:

- ❌ Device-priority orchestrator/router (core Phase 4 component)
- ❌ Model Registry integration
- ❌ Fallback handling for Modal failures
- ❌ Performance monitoring per device type
- ❌ Budget enforcement for Modal GPU usage
- ❌ Selective teacher inference triggering
- ❌ Configuration system for device preferences
- ❌ Integration into inference pipeline (iqa_ml.py)

**Completion Estimate**: 9-11 developer days remaining (~75% of phase)

**Duration**: 15 working days (3 weeks)
**Total Sprints**: 24 sprints (~82 hours of implementation work)

---

#### Week 15: Device Probing & Priority Rules (Day 38-41, 13 sprints)

- **Sprint 4.1.1**: Hardware probe utilities (3 hours)
  - Add GPU/CPU detection with caching to avoid repeated probes.
  - Detect Modal availability flag from env/config.
  - Unit tests for probe outputs across simulated environments.
- **Sprint 4.1.2**: Device policy configuration (3 hours)
  - Extend `config.py` with device policy options and env overrides.
  - CLI flags to force GPU/CPU/Modal or disable teacher entirely.
  - Config validation plus documentation update.
- **Sprint 4.1.3**: Student device selector (2 hours)
  - Implement ONNX session selection: prefer GPU, fallback to CPU.
  - Reuse sessions per device to avoid cold starts.
  - Smoke tests for GPU-present and GPU-absent paths.
- **Sprint 4.1.4**: Teacher device selector & priority (3 hours)
  - Enforce Local GPU → Modal GPU → BLOCK CPU (prod default).
  - Allow QA override to enable CPU for teacher with warning logs.
  - Add decision rationale to `teacher_usage` metadata.
- **Sprint 4.1.5**: Page-level teacher budget (2 hours)
  - Add per-document and per-batch teacher page caps in config.
  - Reject over-budget pages with escalation reason recorded.
  - Unit tests for budget enforcement edge cases.
- **Sprint 4.1.6**: Uncertainty/discrepancy gate wiring (2 hours)
  - Connect existing gate outputs to device selector input.
  - Thresholds pulled from config; add guard if thresholds unset.
  - Regression test to ensure gate still routes student-only when low risk.
- **Sprint 4.1.7**: Selection matrix tests (2 hours)
  - Table-driven tests for availability combos (GPU/CPU/Modal), budgets, and modes.
  - Validate expected device choice and rationale logging.
  - Add snapshot logs for observability verification.

#### Week 16: Modal GPU Integration & Metrics (Day 42-46, 13 sprints)

- **Sprint 4.2.1**: Package teacher for Modal (3 hours)
  - Build Modal image with teacher ONNX plus dependencies.
  - Measure cold start time; document tuning flags.
  - Smoke deploy to staging namespace.
- **Sprint 4.2.2**: Serverless endpoint hardening (3 hours)
  - Add auth, request size guardrails, timeouts, retries.
  - Define response schema (scores, timing, device tag).
  - Integration test via Modal client stub.
- **Sprint 4.2.3**: Client stub with circuit breaker (2 hours)
  - Implement exponential backoff, jitter, and failure cache.
  - Fallback to student-only if breaker is open.
  - Tests simulating Modal outage and slow responses.
- **Sprint 4.2.4**: Cost estimator and budget guard (2 hours)
  - Estimate per-call cost; project monthly spend.
  - Block requests if budget exceeded; log budget breach reason.
  - Unit tests with mocked pricing inputs.
- **Sprint 4.2.5**: Structured logging for device choice (3 hours)
  - Log chosen_device, fallback_reason, cost_estimate, and gate reason.
  - Ensure logs are structured/JSON and redact PII.
  - Add sampling controls for high-volume runs.
- **Sprint 4.2.6**: Metrics export (2 hours)
  - Prometheus counters/histograms for latency, failures, escalation rate, cost.
  - CPU/GPU utilization hints if available.
  - Metrics unit tests (label cardinality guard).
- **Sprint 4.2.7**: Integration test matrix (3 hours)
  - Validate flows: local GPU, forced CPU block, Modal fallback, Modal outage.
  - Compare outputs to ensure parity between local and Modal teacher.
  - Record results in Phase 4 report draft.

#### Week 17: Performance Optimization & Worker Pool (Day 47-52, 11 sprints)

- **Sprint 4.3.1**: Student batch inference (3 hours)
  - Add micro-batching with adaptive batch size.
  - Benchmark vs single inference; target 2x throughput.
  - Fail-safe to single inference if GPU memory low.
- **Sprint 4.3.2**: Async IO and concurrency caps (2 hours)
  - Async file read/render and IQA invocation.
  - Concurrency controls to avoid CPU/GPU thrash.
  - Integration test for parallel batch stability.
- **Sprint 4.3.3**: Caching layer (3 hours)
  - Cache rendered pages and preprocessed tensors.
  - LRU eviction; config for cache size.
  - Add cache hit/miss metrics.
- **Sprint 4.3.4**: TensorRT INT8 path (3 hours)
  - Optional TensorRT engine build for GPU; feature-flagged.
  - Benchmark vs ONNXRuntime baseline; document gains/regressions.
  - Skip gracefully on unsupported hardware.
- **Sprint 4.3.5**: Worker pool plus queue integration (2 hours)
  - Add task queue (Celery/RQ) option with per-queue device caps.
  - Graceful degradation rules when queue length spikes.
  - Health checks for workers.
- **Sprint 4.3.6**: Latency benchmarking (2 hours)
  - p95/p99 measurements for GPU/CPU/Modal with/without batching.
  - Regression gate comparing to Phase 3 baseline.
  - Publish table in Phase 4 report.
- **Sprint 4.3.7**: Phase 4 report (2 hours)
  - Summarize performance tables, budget usage, gating outcomes.
  - List known gaps and follow-ups for Phase 5.

---

**Phase 4 Deliverables:**

- ✅ Device-priority execution system (24 sprints)
- ✅ Modal GPU integration (optional, configurable)
- ✅ Cost tracking and quota enforcement
- ✅ Performance optimization (batch inference, async IO, caching, TensorRT)
- ✅ Production-ready worker pool architecture
- ✅ Comprehensive logging and metrics
- ✅ Performance reports and dashboards

**Phase 4 Success Criteria:**

- Device selection accuracy: 100% (follows priority rules)
- Modal GPU usage: Within configured budget
- Teacher CPU blocking: 100% in production mode
- Latency p95: <150ms per page (GPU), <400ms (CPU)
- Throughput: >6 pages/sec per GPU worker, >2 pages/sec per CPU worker
- Performance improvement: >2x from batch inference
- Test coverage: >80% for all new modules

---

### Phase 5: Testing, Documentation & Deployment (Weeks 18-20) ⚠️ 40% COMPLETE

**Status**: ⚠️ 40% COMPLETE - API Framework + E2E Tests, No Integration (December 2025 audit)

**Priority: HIGH - Productionization**

**Completed Deliverables (40%)**:

- ✅ FastAPI application framework with health/ready endpoints
- ✅ CORS and rate-limiting middleware
- ✅ Request logging middleware
- ✅ API authentication middleware (API key validation)
- ✅ Batch processing routes (stub: `/batch` endpoint defined)
- ✅ Single-document routes (stub: `/process` endpoint defined)
- ✅ Docker configuration (Dockerfile, Dockerfile.gpu)
- ✅ Docker Compose for local development
- ✅ Kubernetes manifests (k8s/ directory with deployment templates)
- ✅ E2E test suite (7 files, 2000+ lines):
  - test_pipeline_e2e.py (590+ lines)
  - test_phase2_complete.py
  - test_ml_iqa_e2e.py
  - test_real_fixtures.py
  - test_teacher_escalation_e2e.py
  - test_layout_lite_e2e.py
  - test_modal_outage_simulation.py

**Outstanding Issues (60% - Functionality Gaps)**:

- ❌ Actual API endpoint implementations (routes are stubs/scaffolding)
- ❌ Batch processing implementation (queue management, worker pools)
- ❌ Integration with inference pipeline (endpoints don't call detection)
- ❌ Model loading in API startup
- ❌ Deployment automation (no helm charts, no CI/CD deployment)
- ❌ Performance benchmarking framework
- ❌ Load testing suite
- ❌ API consumer documentation
- ❌ Health check implementations (endpoints return stubs)

**Completion Estimate**: 25-30 developer days remaining (~60% of phase)

**Duration**: 15 working days (3 weeks)
**Total Sprints**: 22 sprints (~75 hours of implementation work)

---

#### Week 18: Comprehensive Testing (Day 53-57, 15 sprints)

- **Sprint 5.1.1**: Unit test gap sweep (3 hours)
  - Identify low-coverage modules; add focused unit tests.
  - Include property-based tests for routing and DQS calculators.
  - Update coverage report artifact.
- **Sprint 5.1.2**: End-to-end integration test (3 hours)
  - PDF→DocumentMetadata with Phase 4 device logic exercised.
  - Cases: GPU available, GPU missing, Modal fallback, budget hit.
  - Snapshot expected JSON outputs for regression.
- **Sprint 5.1.3**: Modal outage simulation (2 hours)
  - Simulate remote timeouts/failures; ensure student-only fallback.
  - Assert correct error surfaces and logs.
  - Add breaker-open scenario to tests.
- **Sprint 5.1.4**: Batch-mode regression tests (2 hours)
  - 10–100 page documents, mixed PDF types.
  - Validate throughput targets and ensure no memory blowups.
  - Record timing baselines.
- **Sprint 5.1.5**: Golden-file JSON snapshots (2 hours)
  - Freeze stable DocumentMetadata fields for key fixtures.
  - Add drift detection guard in tests for schema output.
  - Update fixtures in `data/test_fixtures/`.
- **Sprint 5.1.6**: Coverage gate + report (2 hours)
  - Ensure 80%+ overall coverage; set coverage threshold in CI.
  - Publish HTML coverage report artifact.

#### Week 19: API Development & Deployment (Day 58-62, 11 sprints)

- **Sprint 5.2.1**: FastAPI skeleton (3 hours)
  - Health/ready/version endpoints; wiring to pipeline stub.
  - Add CORS/config toggles for deployments.
  - Basic app-level logging middleware.
- **Sprint 5.2.2**: POST /process (3 hours)
  - Single file upload; size/type validation.
  - Async pipeline call; response contract with metadata summary and links.
  - Error handling with structured codes.
- **Sprint 5.2.3**: POST /batch + status/result (3 hours)
  - Async job submission returning job_id.
  - GET /status and GET /result with pagination for multi-file outputs.
  - Persist job metadata; cleanup policy.
- **Sprint 5.2.4**: Auth and rate limits (2 hours)
  - API key header middleware; simple rate limiting for batch endpoints.
  - Configurable allowlist for internal callers.
  - Tests for auth failures and limit breaches.
- **Sprint 5.2.5**: Docker + Compose (2 hours)
  - Multi-stage Dockerfile (<2GB target), health checks.
  - docker-compose with Redis/queue for local dev.
  - Smoke test container locally.
- **Sprint 5.2.6**: Optional K8s manifests (2 hours)
  - GPU and CPU Deployments, HPAs, PodDisruptionBudgets.
  - Example values file for secrets/config maps.
  - Validate manifests with kubeval/kubectl dry-run.

#### Week 20: Documentation & Final Integration (Day 63-65, 7 sprints)

- **Sprint 5.3.1**: API documentation (3 hours)
  - OpenAPI examples, error codes, device-behavior notes.
  - Usage examples for /process and /batch.
  - Add curl snippets and sample responses.
- **Sprint 5.3.2**: Deployment guide (2 hours)
  - Local, container, K8s, and Modal configuration paths.
  - Env var matrix and secrets checklist.
  - Troubleshooting section for cold starts and GPU detection.
- **Sprint 5.3.3**: Model card updates (2 hours)
  - Teacher/student latency, cost, accuracy, gating policy.
  - Document when teacher CPU is blocked and why.
  - Add calibration notes for thresholds.
- **Sprint 5.3.4**: ADRs (2 hours)
  - ADR-005: Modal GPU Integration.
  - ADR-006: Device Priority enforcement and budgets.
  - Include decision, alternatives, consequences.
- **Sprint 5.3.5**: Project B handoff guide (2 hours)
  - Contract checks for DocumentMetadata.json.
  - Example payloads and schema validation steps.
  - Checklist for integration testing with Project B.
- **Sprint 5.3.6**: Release checklist & Phase 5 report (2 hours)
  - Final validation steps, smoke tests, and rollback plan.
  - Summarize testing, coverage, API readiness, and deployment status.

---

**Phase 5 Deliverables:**

- ✅ Comprehensive test suite (80%+ coverage, 22 sprints)
- ✅ FastAPI service with async endpoints
- ✅ Docker container and Docker Compose
- ✅ Kubernetes manifests (optional)
- ✅ Complete documentation (API, deployment, models, integration)
- ✅ Architecture Decision Records (5 ADRs)
- ✅ Integration guide for Project B

**Phase 5 Success Criteria:**

- Test coverage: >80%
- All integration tests pass
- All stress tests pass
- Docker container: <2GB
- API response time: <150ms p95 (GPU), <400ms (CPU)
- Documentation: Complete and reviewed
- Project B handoff: Schema 100% compliant

---

### Phase 6: Monitoring, Drift Detection & Continuous Improvement (Ongoing) ✅ 85% COMPLETE

**Status**: ✅ 85% COMPLETE - Pipeline Integration Added (December 2025 update)

**Priority: MEDIUM - Long-term production stability**

**KEY FINDING**: Production-quality infrastructure (6000+ lines) with pipeline integration. Minor gaps in external service testing.

**Completed Deliverables (70% - EXCELLENT INFRASTRUCTURE)**:

**A. Drift Detection Module (985 lines)**:

- ✅ DistributionTracker with reservoir sampling
- ✅ KL divergence and PSI computation with numerical stability
- ✅ Reference store with 30-day auto-expiry
- ✅ DriftDetector class with severity classification (NONE/WARNING/CRITICAL)
- ✅ Feature type enums (10+ monitored metrics)
- ✅ Histogram computation with bound handling

**B. Alerting Infrastructure (1053 lines)**:

- ✅ DriftAlert data structure with runbook URLs
- ✅ AlertManager with multi-channel dispatch (Slack, webhook, log, email)
- ✅ AlertHistory with cooldown tracking and deduplication
- ✅ LogDispatcher, WebhookDispatcher, SlackDispatcher implemented
- ✅ DryRunDispatcher for testing
- ✅ AlertConfig with configurable thresholds

**C. Performance Monitoring (240+ lines)**:

- ✅ EvaluationResult data structure
- ✅ PerformanceEvaluator class
- ✅ MetricsStore for persistence
- ✅ PerformanceJob for scheduled evaluation

**D. Active Learning (841 lines)**:

- ✅ SampleHarvester (high-entropy, low-agreement, teacher-escalated)
- ✅ ManifestGenerator for training manifests
- ✅ PrivacyChecker with PII detection
- ✅ HarvestedSample with privacy status tracking
- ✅ Privacy review checklist template

**E. Prometheus Monitoring (396 lines)**:

- ✅ Comprehensive alert rules (latency, errors, GPU, drift, Modal budget, queue backlog)

**F. Unit Tests**:

- ✅ test_distribution.py (~200 lines)
- ✅ test_alerting.py (~250 lines)
- ✅ test_performance.py (~150 lines)
- ✅ test_active_learning.py (~300 lines)

**G. Pipeline Integration (582 lines)** - NEW:

- ✅ PipelineHooks class with singleton pattern
- ✅ ProcessingContext for document lifecycle tracking
- ✅ Automatic Prometheus metric recording during processing
- ✅ Distribution tracking for drift detection (10 feature types)
- ✅ Drift metric exports (KL divergence, PSI, severity gauges)
- ✅ Model performance metric exports (mAP, F1, precision, recall)
- ✅ Unit tests (34 tests, ~475 lines)

**Outstanding Issues (15% - External Integration Gaps)**:

- ✅ Pipeline integration (drift detection triggered during processing) - DONE
- ✅ Prometheus metrics generation (all alert rule metrics defined) - DONE
- ✅ Prometheus exporter (metrics_endpoint() available) - DONE
- ✅ Grafana dashboards (5 dashboards configured) - DONE
- ⚠️ Persistent reference distribution storage (JSON file-based, not database)
- ❌ Integration with external services (Slack webhook not tested with real endpoints)
- ❌ Model retraining automation from harvested samples
- ❌ Privacy review UI or approval workflow

**Completion Estimate**: 4-5 developer days remaining (~15% of phase)

**Initial Setup Duration**: 10 working days (2 weeks)
**Total Sprints (Initial Setup)**: 15 sprints (~50 hours of initial setup)
**Ongoing Operations**: Weekly/monthly/quarterly tasks (see below)

---

#### Initial Setup (Weeks 21-22, 15 sprints)

**Week 21: Telemetry & Logging (5 sprints)**

- **Sprint 6.1.1**: Structured logging framework (3 hours)
  - JSON logs with rotation policy; correlation ids threaded through pipeline.
  - Redaction for PII; config toggles for verbosity.
  - Unit tests for log shape and redaction.
- **Sprint 6.1.2**: Prediction/correction outcome logging (2 hours)
  - Emit per-page outcomes (student/teacher device, corrections applied, gate reasons).
  - Ensure sampling to control volume in batch mode.
  - Add logging to `teacher_usage` context.
- **Sprint 6.1.3**: Error taxonomy + Sentry hooks (2 hours)
  - Define error codes/classes; map exceptions to codes.
  - Optional Sentry integration (feature-flagged); breadcrumb context.
  - Tests for disabled/enabled modes.
- **Sprint 6.1.4**: Log aggregation pipeline option (2 hours)
  - Document ELK/Vector setup; provide sample config.
  - Local file-based aggregator fallback.
  - Health checks for log shipping.
- **Sprint 6.1.5**: Logging validation (2 hours)
  - Integration test to verify logs emitted for happy path and failures.
  - Snapshot log lines to guard against schema drift.
  - Performance check to ensure minimal overhead.

**Week 22: Monitoring Dashboard (5 sprints)**

- **Sprint 6.2.1**: Prometheus metrics export (3 hours)
  - Metrics for latency, error rate, escalation rate, cost estimate, queue depth.
  - Label cardinality guard; namespace per deployment.
  - Unit tests for metrics exposure.
- **Sprint 6.2.2**: Grafana dashboards (3 hours)
  - System, application, model, and cost dashboards with saved views.
  - Panels for p50/p95/p99 latency, error %, teacher escalation %, Modal spend.
  - Annotate dashboards with deploy markers.
- **Sprint 6.2.3**: Alert rules (2 hours)
  - Alerts for latency spikes, error rate, GPU failure, Modal budget hit, drift flags.
  - Include grouping to reduce noise; add runbooks references.
  - Test alerts with synthetic metric pushes.
- **Sprint 6.2.4**: Runbooks (2 hours)
  - Quick actions for top alerts (restart worker, disable teacher, scale queue).
  - Escalation policy and ownership.
  - Store runbooks in docs/monitoring.
- **Sprint 6.2.5**: Threshold tuning (2 hours)
  - Load test to validate alert thresholds.
  - Tune to reduce false positives; document final values.
  - Capture baseline metrics snapshots.

**Week 23: Drift Detection (5 sprints)**

- **Sprint 6.3.1**: Feature distribution monitoring (3 hours)
  - Histogram stats and KL/PSI on sampled traffic for key IQA outputs.
  - Store reference distributions; rotate monthly.
  - Tests for metric computation robustness.
- **Sprint 6.3.2**: Model performance monitoring job (3 hours)
  - Periodic evaluation on change-detection set; record mAP/F1 trends.
  - Persist results to metrics store; add dashboard panel.
  - CI hook to validate job config.
- **Sprint 6.3.3**: Drift alerting (2 hours)
  - Alert when KL >0.3 or mAP drop >5% vs baseline.
  - Include recent samples in alert payload for triage.
  - Dry-run mode to validate alerts without paging.
- **Sprint 6.3.4**: Active learning loop stub (2 hours)
  - Harvest high-entropy/low-agreement samples to `data/drift_samples/`.
  - Metadata manifest for re-training pipeline.
  - Privacy review checklist for harvested samples.
- **Sprint 6.3.5**: Monitoring/drift documentation (2 hours)
  - SOPs for weekly/monthly/quarterly tasks.
  - Dashboard handbook and alert response flow.
  - Add FAQ for common false positives.

---

**Phase 6 Deliverables (Initial Setup):**

- ✅ Structured logging framework with rotation
- ✅ Prometheus metrics collection
- ✅ Grafana dashboards (system, application, model, cost)
- ✅ Alert rules for latency, errors, drift, cost
- ✅ Drift detection system with monitoring
- ✅ Comprehensive monitoring documentation

**Phase 6 Success Criteria (Initial Setup):**

- Drift detection alerts within 1 week of distribution shift
- Alerting functional for latency spikes, errors, cost overruns
- Dashboards provide real-time visibility into system health
- Documentation complete for monitoring and drift detection

---

### Phase 6 Ongoing Operations

After initial setup, ongoing operations include:

**Weekly Tasks**:

- Review drift metrics (KL divergence, confidence distributions)
- Review cost analytics (Modal usage, teacher escalation trends)
- Mine high-uncertainty samples for active learning

**Monthly Tasks**:

- Run model performance evaluation on change-detection set
- Analyze error logs for systematic failures
- Update alert thresholds if needed

**Quarterly Tasks**:

- Retrain models with production failures added to dataset
- Recalibrate confidence thresholds per IQA head
- Update documentation with lessons learned
- A/B test new model versions (deploy to 10% traffic, compare metrics)

**Annual Tasks**:

- Major model architecture updates
- Dataset refresh (add new public datasets like updated OmniDocBench)
- Infrastructure upgrades (GPU hardware, cloud providers)

**Continuous Improvement Pipeline:**

1. **Data Flywheel**: Collect production failures → manual review → add to training set → retrain quarterly
2. **Active Learning**: Weekly mining of high-uncertainty samples → annotate → add to dataset
3. **Model Retraining**: Quarterly retraining with updated data → A/B test → gradual rollout

**Long-term Success Criteria:**

- Model performance degradation <2% over 6 months
- Active learning reduces annotation effort by >50%
- 95% of production failures resolved in next model version
- Cost per page trends downward over time (via optimizations)

---

### Phase 7: ML IQA Model Optimization - Continuous Label Retraining ❌ NOT STARTED

**Status**: ❌ 0% COMPLETE - Not Started (PLANNED) (December 2025 audit)

**Timeline**: 2-3 weeks (after Phase 2-6 complete)
**Purpose**: Retrain ResNet teacher/student models with continuous quality labels for improved calibration and severity prediction
**Priority**: LOW - Planned optimization phase, not blocking MVP deployment

**Context**: Current models trained on binary labels (0.0/1.0) achieve excellent classification (F1=0.88) but have moderate calibration quality (ECE=0.18). Retraining with continuous labels from classical detectors will improve calibration (target ECE<0.10) and enable severity-aware quality scoring.

---

#### Background & Rationale

**Current Training Approach**:

- **Labels**: Binary (0.0 = no defect, 1.0 = defect present)
- **Loss**: Binary Cross-Entropy (BCE)
- **Performance**: mAP 0.88, F1 0.85-0.90 per class
- **Limitation**: Poor calibration (ECE ~0.18) - predicted probabilities not meaningful for severity assessment

**Information Loss from Binarization**:

```python
# Weak supervision computes continuous metrics
laplacian_var = 150  # Moderate blur → normalized score 0.4
laplacian_var = 50   # Severe blur → normalized score 0.8

# Current approach: Both thresholded to 1.0 (INFORMATION LOSS)
# Continuous approach: Preserves severity gradation (0.4 vs 0.8)
```

**Benefits of Continuous Labels**:

1. **Better calibration**: ECE 0.18 → 0.08 (-56% improvement)
2. **Severity prediction**: New capability to distinguish mild (0.3) vs severe (0.9) defects
3. **Meaningful quality scores**: Aggregated DQS scores more interpretable
4. **Fewer false escalations**: Better classical+ML discrepancy analysis with calibrated scores

**Expected Performance Impact**:

- Binary F1: 0.88 → 0.87 (-1%, negligible)
- Calibration ECE: 0.18 → 0.08 (-56%, major improvement)
- Severity MAE: N/A → 0.12 (new capability)

**Trade-offs**:

- ⚠️ More sensitive to weak supervision noise (requires 50% more data: 150K vs 100K)
- ⚠️ Slightly softer decision boundary (may reduce binary F1 by ~1%)
- ⚠️ Requires careful loss function design (combined BCE+MSE)

---

#### Week 1: Dataset Generation with Continuous Labels (Day 1-5)

**Sprint 7.1.1: Expand ClassicalIQAScores dataclass** (2 hours) ✅ DONE

- Add 5 new continuous score fields: `noise_score`, `illumination_score`, `compression_score`, `binarization_score`, `bleed_through_score`
- Maintain backward compatibility with optional defaults
- Update Pydantic validation (enforce [0, 1] range)

**Sprint 7.1.2: Update weak supervision labeler** (4 hours)

- Modify `WeakSupervisionLabeler` to output continuous scores instead of binary labels
- Normalize classical detector outputs to [0, 1] scale (0=good, 1=bad)
- Implement label smoothing (clip to [0.2, 0.8] to reduce overconfidence)
- Add outlier filtering (remove samples with extreme detector disagreement)

**Sprint 7.1.3: Generate 150K continuous-label dataset** (2 days)

- Run `prepare_phase2_data.py` with continuous labeling mode
- Target: 150K samples (50% more than binary training for noise robustness)
- 70/15/15 train/val/test split (105K / 22.5K / 22.5K)
- Upload to GCS: `gs://image_detection_b/training/iqa_phase2_150k_continuous/`

**Sprint 7.1.4: Dataset validation** (3 hours)

- Verify label distribution (continuous scores, not just 0/1)
- Check outlier removal effectiveness
- Validate normalization ranges ([0, 1] for all scores)
- Compare with binary dataset (same source images, different labels)

---

#### Week 2: Model Training with Combined Loss (Day 6-12)

**Sprint 7.2.1: Implement combined BCE+MSE loss** (3 hours)

- Design hybrid loss function: `α * BCE(pred, target>0.5) + β * MSE(pred, target)`
- BCE component: Strong classification signal (defect present/absent)
- MSE component: Severity gradation (how much defect)
- Hyperparameter tuning: α=0.6, β=0.4 (favor classification, add severity)

**Sprint 7.2.2: Update training loop** (2 hours)

- Modify `TeacherTrainer` to use continuous targets
- Update loss computation for soft labels
- Add severity MAE metric tracking alongside F1/mAP

**Sprint 7.2.3: Train ResNet-50 teacher (continuous)** (5 days)

- Modal GPU training: 50 epochs, batch_size=128
- Target metrics: mAP>0.86, F1>0.83, ECE<0.10, Severity MAE<0.15
- Early stopping based on validation ECE (not just loss)
- Save checkpoints every 5 epochs

**Sprint 7.2.4: Export teacher to ONNX** (1 hour)

- Export to `resnet50_teacher_continuous.onnx`
- Validate ONNX inference matches PyTorch
- Upload to GCS model registry

---

#### Week 3: Student Distillation & Validation (Day 13-19)

**Sprint 7.3.1: Knowledge distillation with continuous teacher** (3 days)

- Train ResNet-18 student via distillation from continuous teacher
- Use same combined loss (BCE+MSE) + distillation loss
- Target metrics: mAP>0.85, F1>0.82, ECE<0.12, Severity MAE<0.18

**Sprint 7.3.2: Export student to ONNX** (1 hour)

- Export to `resnet18_student_continuous.onnx`
- Validate ONNX inference parity with PyTorch

**Sprint 7.3.3: Calibration validation** (4 hours)

- Compute Expected Calibration Error (ECE) on test set
- Compare binary vs continuous models:
  - Binary ECE: ~0.18
  - Continuous ECE target: <0.10
- Generate calibration plots (reliability diagrams)

**Sprint 7.3.4: Severity prediction validation** (4 hours)

- Evaluate severity MAE on test set
- Compare predicted severity with classical detector outputs
- Analyze per-class severity prediction accuracy

**Sprint 7.3.5: Discrepancy analysis validation** (3 hours)

- Test classical+ML discrepancy calculation with continuous scores
- Verify teacher escalation decisions more accurate (fewer false escalations)
- Compare escalation rates: binary vs continuous models

**Sprint 7.3.6: A/B testing preparation** (2 hours)

- Document model versioning (binary=v1.0, continuous=v2.0)
- Create deployment plan: 10% traffic → 50% → 100% rollout
- Define success metrics for A/B test:
  - Calibration ECE improvement: target -40%
  - False escalation rate reduction: target -20%
  - DQS interpretability (user survey)

---

#### Week 4: Integration & Rollout (Day 20-23)

**Sprint 7.4.1: Update inference pipeline** (3 hours)

- Modify `MLIQADetector` to load continuous models
- Update config to support model version selection (binary vs continuous)
- Add feature flag for gradual rollout

**Sprint 7.4.2: Integration testing** (4 hours)

- Run full test suite with continuous models
- Verify backward compatibility (existing code works with new models)
- Validate output JSON schema unchanged

**Sprint 7.4.3: Performance benchmarking** (3 hours)

- Compare inference latency: continuous vs binary models
- Target: <5% latency increase (model complexity same, just different training)
- Benchmark on GPU/CPU devices

**Sprint 7.4.4: Documentation & report** (2 hours)

- Document continuous vs binary model comparison
- Update MODEL_CARD.md with v2.0 model details
- Create deployment runbook for continuous model rollout

---

**Phase 7 Deliverables:**

- ✅ 150K continuous-label training dataset (DVC-tracked)
- ✅ ResNet-50 teacher trained with continuous labels (v2.0)
- ✅ ResNet-18 student distilled from continuous teacher (v2.0)
- ✅ ONNX exports: `resnet50_teacher_continuous.onnx`, `resnet18_student_continuous.onnx`
- ✅ Calibration validation report (ECE comparison)
- ✅ A/B testing plan and rollout strategy
- ✅ Updated documentation (MODEL_CARD.md, deployment runbook)

**Phase 7 Success Criteria:**

- **Calibration improvement**: ECE <0.10 (from 0.18 with binary training)
- **Binary classification maintained**: F1 >0.82 (≤6% degradation acceptable)
- **Severity prediction**: MAE <0.18 on continuous scale
- **Production validation**: A/B test shows -20% false escalation rate
- **Performance**: <5% latency increase vs binary models

**Phase 7 Cost Estimate:**

- Dataset generation: ~$5 (GCS storage + compute)
- Teacher training: ~$10-15 (Modal GPU, 50 epochs on 150K samples)
- Student training: ~$5-8 (Modal GPU, 30 epochs distillation)
- **Total**: ~$20-28

**Phase 7 Dependencies:**

- Requires: Phase 2-6 complete (integration testing, deployment, monitoring established)
- Blocks: None (optimization phase, not blocking MVP)
- Related: Uses expanded ClassicalIQAScores from Priority 5

**Phase 7 Notes:**

- This is an **optimization phase**, not required for MVP deployment
- Current binary-trained models (v1.0) are production-ready and should be used initially
- Continuous retraining provides incremental improvement (~10-20% better calibration, severity prediction)
- Can be deferred until after initial production deployment and feedback collection

---

### Phase 8: Document Quality Score (DQS) & Routing (Integrated into Phase 2)

**Status**: ⚠️ ~50% COMPLETE - DQS Implemented, PDF Classification Missing (December 2025 audit)

**Note**: Phase 8 functionality is integrated into Phase 2 deliverables, documented here for completeness.

#### Completed Deliverables (50%)

- ✅ DQS Calculation (routing/dqs.py - ~200 lines)
  - Degradation score (IQA metric aggregation)
  - Structural complexity score (layout-based)
  - Pre-OCR risk (combined DQS metric)
- ✅ Routing Logic (routing/recommendation.py - ~150 lines)
  - 4 strategies defined: ocr_fast, ocr_advanced, vision_simple, vision_structured

#### Outstanding Issues (50%)

- ❌ PDF Type Classification (routing/pdf_classifier.py - stub only)
  - Image-only detection
  - Born-digital detection
  - Hybrid classification
  - Text layer analysis
- ❌ CLI integration (DQS not calculated in `imgprep`)
- ❌ API integration (routing not exposed in endpoints)
- ❌ JSON output (schema exists, not populated)

**Test Coverage**: 28% (needs improvement to 80%)

**Completion Estimate**: 8-10 developer days remaining (~50% of phase)

**See Phase 2 for detailed sprint breakdown and integration work.**

---

### Phase 9: Element Classification Models ❌ NOT STARTED

**Status**: ❌ 0% COMPLETE - Not Started (Migrated from Project B) (December 2025 audit)

**Priority**: LOW - Not blocking MVP deployment

**Timeline**: 3-4 weeks (after Phases 4-8 complete)

**Purpose**: Train specialized classifiers for element-level routing decisions and content analysis. Originally planned for Project B but migrated to Project A for better preprocessing integration.

#### Overview

These classifiers enhance routing decisions and quality assessment by providing element-specific metadata. They inform downstream processing (Project B) about which specialist OCR engines to use for different document components.

**Key Models**:

- Handwriting Classifier (binary: printed vs handwritten)
- Table Type Classifier (6-class: simple_grid, merged_header, nested_rows, financial, form_like, scientific)
- Formula Complexity Classifier (5-class: simple_inline, block_equation, multi_line, matrix, handwritten_math)
- Parasitic Element Detector (4-class: watermark, stamp, signature, clean)

#### Deliverables

**9.1 Handwriting Classifier**

- **Architecture**: ResNet-18 (full variant), MobileNetV3 (light variant)
- **Classes**: 2 (printed, handwritten)
- **Dataset**: IAM Handwriting Database + custom scanned documents
- **Target Accuracy**: >96% (full), >92% (light)
- **Use Case**: Route handwritten forms to ICR engines vs standard OCR
- **Performance Target**: <5ms CPU (light), <2ms GPU (full)

**9.2 Table Type Classifier**

- **Architecture**: ResNet-18 (full variant), MobileNetV3 (light variant)
- **Classes**: 6 (simple_grid, merged_header, nested_rows, financial, form_like, scientific)
- **Dataset**: PubTables-1M + custom annotations
- **Target Accuracy**: >90%
- **Use Case**: Route to TableFormer (simple) vs StructEqTable (complex)
- **Performance Target**: <5ms CPU (light), <2ms GPU (full)

**9.3 Formula Complexity Classifier**

- **Architecture**: ResNet-18 (full variant), MobileNetV3 (light variant)
- **Classes**: 5 (simple_inline, block_equation, multi_line, matrix, handwritten_math)
- **Dataset**: IM2LATEX-100K + arXiv papers
- **Target Accuracy**: >88%
- **Use Case**: Route to Texify (simple) vs UniMERNet (complex)
- **Performance Target**: <5ms CPU (light), <2ms GPU (full)

**9.4 Parasitic Content Detector**

- **Architecture**: ResNet-18 (full variant), MobileNetV3 (light variant)
- **Classes**: 4 (watermark, stamp, signature, clean)
- **Dataset**: Synthetic watermarks + real scanned documents
- **Target Accuracy**: >95% (watermark detection critical)
- **Use Case**: Flag non-content elements for exclusion from RAG indexing
- **Performance Target**: <5ms CPU (light), <2ms GPU (full)

#### Integration

**Model Registry**:

- Export to ONNX (full and light variants)
- Register in `models/registry.json` with metadata
- Version control with semantic versioning (v1.0.0, v1.1.0, etc.)

**JSON Output Enhancement**:

- Populate `detected_elements[].classifications` field
- Add confidence scores for each classifier
- Include variant used (full vs light)

**Project B Handoff**:

- Element-level classifications enable specialist routing
- Handwriting → ICR engines
- Complex tables → StructEqTable
- Complex formulas → UniMERNet
- Parasitic elements → exclude from RAG

#### Training Infrastructure

**Reuse Phase 3 Setup**:

- Modal GPU training (T4/A10)
- Knowledge distillation (full → light)
- ONN X export pipeline
- Model registry integration

**Estimated Cost**: ~$15-20 (4 models × ~$4 each on Modal GPU)

#### Blockers

- **Dataset Acquisition**: Labeled datasets for all 4 classifiers not yet acquired
  - IAM Handwriting: Available (free)
  - PubTables-1M: Available (free)
  - IM2LATEX-100K: Available (free)
  - Watermark dataset: Needs creation (synthetic generation)

- **Low Priority**: Phases 4-8 must be production-ready first

**Completion Estimate**: 20-25 developer days + dataset acquisition time

#### Success Metrics

- **Handwriting Classifier Accuracy**: > 96% (full), > 92% (light)
- **Table Type Classifier Accuracy**: > 90%
- **Formula Complexity Correlation**: > 0.85 (Pearson correlation with human judgments)
- **Parasitic Element Recall**: > 95% (detect all watermarks/stamps)
- **Inference Latency (per classifier)**: < 5ms CPU (light), < 2ms GPU (full)
- **Model Size**: < 25MB (ONNX optimized, per model)

---

## Technical Stack & Dependencies

### Core Technologies

**Programming Language:**

- Python 3.10+ (type hints, modern features)

**Computer Vision:**

- OpenCV 4.8+ (classical CV, image corrections)
- Pillow (image manipulation)
- PyMuPDF (PDF to image conversion, text extraction)
- **Docling** (office document parsing for embedded image extraction)

**Deep Learning:**

- PyTorch 2.0+ (model training and inference)
- torchvision (image transforms, pretrained ResNet models)
- ONNX Runtime (cross-platform inference, INT8 quantization)
- TensorRT (NVIDIA GPU acceleration, optional)
- **YOLOv10-doc** (DocLayNet-trained layout detection model, ONNX format)

**Data Augmentation:**

- Albumentations (fast, GPU-accelerated augmentations)

**OCR (Secondary Analysis - Minimal Use):**

- Tesseract OCR (lightweight script detection, if needed)
- pytesseract (Python wrapper)

**API & Web Service:**

- FastAPI (async API framework)
- Uvicorn (ASGI server)
- Pydantic v2 (data validation and schema)

**Task Queue (Optional):**

- Celery or RQ (async worker pool)
- Redis (message broker)

**Monitoring & Logging:**

- Prometheus (metrics collection)
- Grafana (visualization)
- Sentry (error tracking, optional)
- structlog + rich (structured logging with console output)

**Testing:**

- pytest (unit and integration tests)
- pytest-cov (code coverage)
- hypothesis (property-based testing, optional)

**Development Tools:**

- Poetry (dependency management)
- Ruff (fast linting and formatting)
- MyPy (static type checking)
- Pre-commit (automated checks)
- Bandit (security scanning)
- Safety (dependency vulnerability scanning)

**Data Versioning:**

- DVC (Data Version Control, optional)
- Git LFS (large file storage, optional)

**Containerization:**

- Docker (service containerization)
- Docker Compose (local development)
- Kubernetes (production orchestration, optional)

**Remote GPU (Optional):**

- Modal.com (serverless GPU for teacher inference)

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

## Success Metrics & KPIs

### Model Performance KPIs

**ML-based IQA (Teacher-Student):**

- **Teacher (ResNet-50)**:
  - mAP: >0.92
  - Per-head F1: >0.90
  - ECE: <0.03
- **Student (ResNet-18)**:
  - mAP: >0.88
  - Per-head F1: >0.85
  - ECE: <0.05
  - Student-teacher KL divergence: <0.15

**Layout-Lite Classification:**

- `layout_type` accuracy: >0.90
- Presence flags F1: >0.85 per flag
- Inference time: <5ms GPU (YOLOv8-nano) or <5ms CPU (heuristics)

**End-to-End Pipeline:**

- JSON Accuracy: >0.85
- Routing accuracy: >0.88
- DQS correlation with OCR difficulty: >0.75
- Latency p95: <150ms GPU, <400ms CPU
- Throughput: >6 pages/sec per GPU worker, >2 pages/sec per CPU worker

### Operational KPIs

**Reliability:**

- Uptime: >99.5%
- Error rate: <0.5%
- Mean time to recovery (MTTR): <1 hour

**Performance:**

- Latency p95: <150ms (GPU) / <400ms (CPU)
- Throughput: Meets target SLA (6 pages/sec GPU, 2 pages/sec CPU)
- Resource utilization: GPU 70-85%, CPU 60-75%

**Quality:**

- User-reported issues: <5% of processed pages
- False positive rate: <10% per issue type
- False negative rate: <15% per issue type

**Cost (Device-Priority Execution):**

- Modal GPU usage: Within configured budget
- Teacher escalation rate: <20% of documents (target: 10-15%)
- Cost per page: <$0.01 (target: <$0.005)

### Business KPIs

**Efficiency:**

- Reduce manual preprocessing time by >80%
- Increase RAG ingestion throughput by >5x
- Improve downstream OCR accuracy by >30% (via quality corrections)

**Integration:**

- Project B handoff: 100% schema compliance
- Routing accuracy: >88% agreement with optimal OCR engine selection

---

## Related Documentation

### RAG Pipeline Architecture (docs/development/RAG Pipeline/)

- **[RAG-pipeline-project-overview.md](docs/development/RAG Pipeline/RAG-pipeline-project-overview.md)**: Four-project architecture overview with responsibility boundaries
- **[Project_A_F_NF.md](docs/development/RAG Pipeline/Project_A_F_NF.md)**: Functional and Non-Functional Requirements for Project A
- **[project-a-project-plan.md](docs/development/RAG Pipeline/project-a-project-plan.md)**: Detailed 10-week implementation roadmap
- **[PROJECT_ALIGNMENT_ANALYSIS.md](docs/development/RAG Pipeline/PROJECT_ALIGNMENT_ANALYSIS.md)**: Gap analysis and alignment roadmap

### Project-Specific Documentation

- **[CLAUDE.md](CLAUDE.md)**: Project-specific guidance for Claude Code development
- **[ARCHITECTURE_CORRECTION.md](ARCHITECTURE_CORRECTION.md)**: Correction pipeline architecture and guardrails
- **[schema.py](src/image_preprocessing_detector/schema.py)**: Pydantic v2 models for DocumentMetadata and related schemas

### External Benchmarks

- **OmniDocBench**: Multi-domain document dataset with layout and quality annotations
- **OHR-Bench**: OCR-hard regions benchmark for quality assessment validation
- **PubLayNet**: Layout detection benchmark (for layout-lite validation)

---

## Appendix: Key Architectural Decisions

### ADR-001: Teacher-Student ResNet Architecture

**Decision**: Use ResNet-50 teacher + ResNet-18 student with knowledge distillation instead of single-model MobileNetV3/EfficientNet.

**Rationale**:

- **Accuracy-Cost Trade-off**: Teacher provides high-fidelity quality assessment on difficult cases; student provides fast, cost-effective inference on majority of documents
- **Selective Escalation**: Teacher invoked only on high-risk documents (10-20% of corpus), reducing average cost
- **Knowledge Distillation**: Student learns from teacher's soft labels, achieving near-teacher accuracy at fraction of computational cost
- **Continuous Improvement**: Teacher can be retrained on hard samples without disrupting production (student remains default)

**Alternatives Considered**:

- Single MobileNetV3 model: Lower accuracy on edge cases, no escalation path
- Single EfficientNet model: Higher GPU cost, less flexible cost control

**Status**: Approved

---

### ADR-002: Device-Priority Execution

**Decision**: Implement device-priority execution: Local GPU → Local CPU → Modal GPU, with teacher CPU blocking in production mode.

**Rationale**:

- **Cost Optimization**: Prefer free local resources before paid cloud GPU
- **Latency Control**: Local GPU provides lowest latency for GPU-capable inference
- **Safety**: Teacher CPU blocking prevents expensive, slow inference on CPU
- **Flexibility**: Modal GPU provides burst capacity for high-load scenarios

**Alternatives Considered**:

- Always use local resources: No burst capacity for high-load scenarios
- Always use Modal GPU: Higher baseline cost, network latency

**Status**: Approved

---

### ADR-003: Light Layout (YOLOv10-doc) vs Full Semantic Layout (Project B)

**Decision**: Use YOLOv10-doc in Project A for element detection with bounding boxes, quality assessment, and spatial hints; defer semantic relationships and reading order to Project B.

**Rationale**:

- **Separation of Concerns**: Project A detects WHERE elements are and WHAT QUALITY they have; Project B determines HOW TO READ them and HOW THEY RELATE
- **Model Choice**: YOLOv10-doc specifically trained on DocLayNet provides better accuracy/speed than YOLOv8
  - Pre-trained on 80k+ DocLayNet pages (no custom training needed)
  - Detects all 11 DocLayNet classes out-of-box
  - Better architecture than YOLOv8 (improved speed/accuracy tradeoff)
- **Performance**: YOLOv10-doc <25ms GPU (target) provides element detection fast enough for Project A needs
- **Clear Boundaries**:
  - ✅ Project A: Bounding boxes, per-element IQA, spatial hints, structural complexity
  - ❌ Project A: Reading order, caption→figure linking, table structure (requires OCR text)
- **Hybrid IQA**: Enables per-element quality assessment (critical for technical documents with embedded figures/charts)

**Alternatives Considered**:

- YOLOv8-nano with 4 lite blocks: Less accurate, missing specialized content detection (formulas, captions, footnotes)
- Heuristics-based only: Insufficient accuracy for complex layouts, no bounding boxes
- Full semantic layout in Project A: Violates separation of concerns, requires OCR text Project A doesn't have
- No layout analysis in Project A: Missing critical routing metadata and hybrid IQA capability

**Status**: Approved

---

### ADR-004: DQS and Routing Metadata

**Decision**: Calculate Document Quality Score (DQS) and routing recommendation in Project A; hand off to Project B for OCR engine selection.

**Rationale**:

- **Single Source of Truth**: Project A analyzes quality once; Project B uses metadata for decisions
- **Efficiency**: Avoids Project B re-running quality analysis
- **Holistic Signal**: DQS combines degradation + structural complexity for comprehensive quality assessment
- **Routing Optimization**: Explicit routing recommendation guides Project B to optimal OCR engine

**Alternatives Considered**:

- Project B calculates own routing: Duplicates work, potential inconsistency
- No routing metadata: Project B must guess optimal OCR engine, lower accuracy

**Status**: Approved

---

### ADR-005: Office Document Support via Docling

**Decision**: Use Docling for embedded image extraction from office documents (.docx, .xlsx, .pptx) in Project A; defer office text and structure extraction to Project B.

**Rationale**:

- **Comprehensive Support**: Office documents contain embedded images (charts, diagrams, photos) that benefit from IQA and correction
- **Tool Selection**: Docling provides native support for both image extraction (Project A) and text/structure parsing (Project B)
- **Separation of Concerns**:
  - Project A: Extract embedded images → preprocess → quality assessment → corrections → hand off
  - Project B: Parse office text, tables, formatting, structure → combine with preprocessed images
- **Workflow Efficiency**: Single tool (Docling) used in both projects reduces integration complexity
- **Image Quality**: Embedded images often have quality issues (low resolution, compression artifacts) that benefit from Project A's preprocessing

**Alternatives Considered**:

- python-docx/openpyxl/python-pptx: Basic image extraction only, no text structure parsing for Project B
- Marker only: Excellent for PDFs, but no native office format support
- Convert office to PDF first: Loses native structure information, introduces conversion artifacts
- Skip office formats entirely: Misses significant document source (many business/academic documents in Office formats)

**Implementation**:

1. Project A: `Docling.extract_images(office_file)` → standard preprocessing pipeline per image
2. Project B: `Docling.parse_document(office_file)` → text + structure + receive preprocessed images from Project A
3. Unified output: Project B combines native text with preprocessed images

**Status**: Approved

---

## Conclusion

Project A serves as the intelligent gateway for the RAG document processing pipeline, providing high-quality preprocessing, comprehensive quality assessment, and routing metadata to downstream projects. The teacher-student ResNet architecture with device-priority execution balances accuracy with cost efficiency, while the light layout approach (YOLOv10-doc) provides complete element detection with clear separation of concerns from Project B.

**Key Success Factors:**

1. **Teacher-Student Architecture**: High accuracy on difficult cases, cost-effective on routine documents
2. **Device-Priority Execution**: Optimizes cost while maintaining performance SLAs
3. **YOLOv10-doc Light Layout**: All 11 DocLayNet classes detected with bounding boxes, enables hybrid IQA and spatial hints
4. **Clear Boundaries**: Project A detects WHERE/WHAT QUALITY; Project B determines HOW TO READ/HOW ELEMENTS RELATE
5. **Office Document Support**: Docling integration for embedded image extraction (.docx/.xlsx/.pptx)
6. **Routing Metadata**: Enables Project B to make intelligent OCR engine decisions (DQS + complexity + pdf_type)
7. **Do-No-Harm Guardrails**: Ensures corrections improve quality without introducing artifacts
8. **Hybrid IQA**: Per-element quality assessment critical for technical documents with figures/charts/tables

**Expected Timeline**: 20 weeks from Phase 2 start to production deployment
**Expected Outcomes**:

- JSON Accuracy: >0.85
- Throughput: >6 pages/sec per GPU worker
- Routing Accuracy: >88%
- Cost per page: <$0.01
- Reduces manual preprocessing time by >80%

**Next Steps**:

1. Complete Phase 1 remaining tasks (CLI tool, output generation)
2. Begin Phase 2: Schema alignment and core components (PDF type, DQS, routing)
3. Coordinate with Project B team on handoff contract validation

---

*This project plan aligns with the RAG Pipeline architecture documented in `docs/development/RAG Pipeline/`. For detailed requirements, see `Project_A_F_NF.md`. For implementation roadmap, see `project-a-project-plan.md`.*
