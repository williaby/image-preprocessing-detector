---
schema_type: common
title: "Functional Requirements v2.0"
description: "Detailed functional and non-functional requirements for the Image Preprocessing Detector system"
tags: [requirements, specifications, functional, non-functional, documentation]
status: published
owner: "docs-team"
review_cycle_days: 90
authors:
  - name: "Byron Williams"
purpose: "Specify detailed requirements for document preprocessing, quality assessment, and intelligent routing."
---

> **Version:** 2.0
> **Date:** 2025-11-11
> **Status:** Active
> **Supersedes:** PRs #14-15 functional_requirements.md
> **Aligned with:** PROJECT_PLAN Phase 1-5, ADRs 0001-0028

---

## 1.0 Introduction

### 1.1 Purpose

This document specifies the detailed functional and non-functional requirements for the **Image Preprocessing Detector**. This tool is a pre-processing validation and correction system designed to analyze and classify all incoming documents. Its purpose is to detect a range of quality, format, and content issues; perform foundational image corrections; and output structured JSON metadata. This JSON file will be used to route each document to the correct, specialized processing workflow.

### 1.2 Scope

**In-Scope:**
- Accept single document file (path or byte stream)
- Analyze file to identify properties and quality issues
- Run CV-based and ML-based detectors
- Perform foundational image corrections (deskew, upscale, denoise, CLAHE)
- Output structured JSON metadata file
- Calculate Document Quality Score (DQS) for intelligent routing (Phase 4)
- Preprocess embedded images in office documents (Phase 5)

**Out-of-Scope:**
- Full-page OCR or text extraction (beyond classification needs)
- Downstream parsing logic (table-to-JSON, semantic chunking, vectorization)
- PDF Portfolio files (deprecated format)
- Full office document parsing (delegated to Docling)

### 1.3 Audience

This document is intended for:
- Development team
- QA/Test engineers
- Project management
- Integration partners (Docling, LayoutParser, OCR engines)

---

## 2.0 Functional Requirements (FR)

### FR-1: General System & File Handling

#### FR-1.1: File Input
The system shall accept a single file input via:
- File path (absolute or relative)
- Byte stream (in-memory processing)

#### FR-1.2: Supported File Formats

**Phase 1-4 (Current Scope):**
- **Images**: .jpg, .jpeg, .png, .tiff, .bmp
- **PDFs**: .pdf (all types: image-only, born-digital, hybrid)

**Phase 5 (Office Format Preprocessing):**
- **Office**: .doc, .docx, .xls, .xlsx, .pptx
- **Scope**: Preprocess embedded images only (not full document parsing)
- **Integration**: Extract images → preprocess → pass to Docling
- **Rationale**: Office formats contain embedded images that benefit from preprocessing (DPI upscaling, deskewing, denoising). Full document parsing delegated to Docling.

**Out-of-Scope:**
- **PDF Portfolios**: Deprecated by Adobe, rarely encountered
- **Other**: .odt, .rtf, .epub (no current demand)

#### FR-1.3: JSON Output
The system shall output a single, structured JSON metadata file that conforms to the **Pydantic v2 Schema Definition** (see `src/image_preprocessing_detector/schema.py`).

**Schema:** `DocumentMetadata` model with fields:
- `file_path`: str
- `document_type`: Literal["image", "pdf", "office_word", "office_excel"]
- `pages`: List[PageMetadata]
- `quality_score`: Optional[DocumentQualityScore] (Phase 4)
- `pdf_type`: Optional[Literal["image_only", "born_digital", "hybrid"]] (Phase 2)
- `languages`: Optional[List[str]] (Phase 2)
- `upscaling`: Optional[Dict] (Phase 1B - completed)

#### FR-1.4: Error Handling
The system shall gracefully handle and log errors for:
- Unsupported file formats → Return error JSON with message
- Corrupted files that cannot be opened → Return error JSON
- Password-protected or encrypted files → Return error JSON
- PDF Portfolio files → Return error: "PDF Portfolio format not supported"

---

### FR-2: File Format Analysis

#### FR-2.1: PDF Type Classification (Phase 2)

The system shall analyze all `.pdf` files and classify the file type as one of:

- **"image_only"**: Contains no extractable digital text (i.e., a scanned document)
- **"born_digital"**: Contains extractable digital text and no significant image-based content
- **"hybrid"**: Contains both extractable digital text and significant embedded images that also contain text

**Method:** Use PyMuPDF text extraction attempt
- If zero text objects → "image_only"
- If text objects AND embedded images → "hybrid"
- If text objects AND no embedded images → "born_digital"

**Output:** Add `pdf_type` field to `DocumentMetadata`

**Rationale:** Critical for routing decisions (OCR vs. text extraction vs. visual reconciliation)

**Implementation:** Phase 2 (Week 8-9)

#### FR-2.2: Office Format Detection (Phase 5)

The system shall identify office document types:
- `.doc`/`.docx` → Flag `document_type` as "office_word"
- `.xls`/`.xlsx` → Flag `document_type` as "office_excel"
- `.ppt`/`.pptx` → Flag `document_type` as "office_powerpoint"

**Scope:** Extract embedded images for preprocessing only

---

### FR-3: Image Quality Detection & Correction (Per-page)

For all image files and for each page of an "image_only" or "hybrid" PDF:

#### FR-3.1: Blur Detection

The system shall calculate a quantitative **blur_score** based on the variance of the Laplacian.

**Method:** `cv2.Laplacian()` variance
- High variance = sharp image
- Low variance = blurry image

**Output:** Report score in JSON (0.0 - 1.0 normalized)

**Reference:** ADR-0014 (Classical ML Hybrid IQA)

#### FR-3.2: Skew Detection and Correction

The system shall detect the document's **skew_angle** in degrees using `cv2.minAreaRect()` on the content block.

**Detection:**
- Use `cv2.minAreaRect()` on thresholded image
- Report original detected angle in JSON

**Correction (with Do-No-Harm Guardrails):**
- **Threshold 1**: Only correct if |angle| > 2.0 degrees (configurable)
- **Threshold 2**: Apply correction and measure variance improvement
- **Threshold 3**: Only keep correction if variance improves by > 5%
- **Fallback**: If correction degrades quality, use original image

**Configuration:**
- `skew_angle_threshold`: Default 2.0° (range: 0.5° - 5.0°)
- `variance_improvement_threshold`: Default 5% (range: 1% - 10%)
- `enable_deskew_guardrails`: Default true

**Rationale:** Prevents over-correction on already-clean documents

**Reference:** ADR-0021 (Do-No-Harm Guardrails)

#### FR-3.3: Noise Detection

The system shall calculate a heuristic **noise_score** to identify potential issues like heavy stains, ink bleed-through, or "salt-and-pepper" noise.

**Method:** Connected component analysis
- Count of very small components (< 10 pixels) → salt-and-pepper noise
- Count of very large non-text components → stains/smudges

**Output:** Report score in JSON (0.0 - 1.0 normalized)

#### FR-3.4: Image Resolution

The system shall report the image resolution:
- **Width × Height** in pixels
- **DPI** (dots per inch) from metadata or calculated

#### FR-3.5: DPI Detection (Phase 1B - Completed)

The system shall attempt to read the image's DPI from its metadata:
- PDF: PyMuPDF `page.get_images()` image info
- JPG/PNG: EXIF tags or PIL metadata

#### FR-3.6: DPI Upscaling (Phase 1B - Completed)

If the detected DPI is below a configurable threshold (default: 300 DPI) or metadata is unavailable, the system shall upsample the image.

**Upscaling Configuration:**
- **Target DPI**: 300 (configurable)
- **Algorithm Options**:
  1. `lanczos` - Best quality (recommended for production)
  2. `bicubic` - Balanced speed/quality (development)
  3. `inter_linear` - Fastest (performance-critical)
  4. `inter_cubic` - Alternative high-quality
  5. `inter_area` - Downsampling (for oversized images)

**Output:**
- Report original DPI in JSON
- Report whether upsampling was applied
- Track upscaling metadata (algorithm, processing time, file sizes)

**Reference:**
- Phase 1B Implementation Summary
- ADR-0010 (300 DPI Normalization)

#### FR-3.7: Contrast Assessment

The system shall calculate a **contrast_score** using histogram analysis:
- Bimodal histogram = good contrast
- Single-peak histogram = low contrast

**Output:** Report score in JSON (0.0 - 1.0 normalized)

---

### FR-4: Layout Analysis (Per-page)

#### FR-4.1: Layout Detection Model

The system shall use a **deep learning object detection model** trained on the DocLayNet dataset.

**Model:** YOLOv8 (Phase 3) or classical heuristics (Phase 1)

**Reference:** ADR-0015 (YOLOv8 Layout Detection)

#### FR-4.2: Layout Element Detection

The system shall detect and provide bounding boxes for the following layout classes:

**DocLayNet Classes (11):**
1. **Caption** - Descriptive text for figures/tables
2. **Footnote** - Notes at page bottom
3. **Formula** - Mathematical equations
4. **List-Item** - Bulleted/numbered list items
5. **Page-Footer** - Repeating footer content
6. **Page-Header** - Repeating header content
7. **Picture** - Figures, charts, diagrams
8. **Section-Header** - Section titles
9. **Table** - Structured data in rows/columns
10. **Text** - Main body paragraphs
11. **Title** - Document title

**Extended Classes (Phase 3):**
12. **Handwriting** - Handwritten text regions (requires separate classifier)
13. **Revision-Marking** - Strikethrough, insertions, margin notes (optional, Yale manuscripts)

**Derived Metadata:**
- **Multi-column detection**: Automatic from spatial analysis of Text blocks
- **Reading order**: Automatic from top-to-bottom, left-to-right sort
- **Parasitic content**: Flagged if class is Page-Header or Page-Footer

**Reference:** ADR-0008 (Multi-Stage Pipeline Architecture)

#### FR-4.3: Bounding Box Format

**CRITICAL**: Bounding boxes shall use **COCO format**: `[x, y, width, height]`

**Where:**
- `x`: X-coordinate of top-left corner (pixels from left edge)
- `y`: Y-coordinate of top-left corner (pixels from top edge)
- `width`: Width of bounding box (pixels)
- `height`: Height of bounding box (pixels)

**Rationale:**
- Industry-standard COCO format ensures compatibility with LayoutParser
- Consistent with DocLayNet dataset format

**Example:**
```json
{
  "class_label": "Table",
  "bounding_box": [120, 340, 450, 200],
  "confidence": 0.94
}
```

**Reference:** ADR-0009 (COCO Bounding Box Format Standardization)

**Note:** This supersedes PRs #14-15 which incorrectly specified `[x1, y1, x2, y2]` format.

---

### FR-5: Specialized Content Detection (Per-page)

#### FR-5.1: Mathematical Content (Phase 3)

The system shall identify all mathematical equations on a page by providing the bounding boxes for the **Formula** class (as per FR-4.2).

**Output:** Bounding box + confidence score for each formula

**Routing:** Formula regions may be routed to specialized Math OCR (Nougat, pix2tex) in downstream processing

#### FR-5.2: Handwritten Content (Phase 2)

**FR-5.2.1:** The system shall process all regions detected as **Text** (from FR-4.2).

**FR-5.2.2:** The system shall classify each Text region as either **"Printed"** or **"Handwritten"**.

**Method:** CNN classifier or texture analysis (Bag-of-Visual-Words)

**Output:** Add `text_type` property to Text layout element in JSON

**Accuracy Target:** F1-score ≥ 0.90 on validation set (NFR-2.4)

**Reference:** ADR-0012 (Defer Handwriting Detection to Phase 2)

#### FR-5.3: Language Detection (Phase 2)

**FR-5.3.1:** The system shall perform language detection on the document.

**FR-5.3.2:** The system shall report the primary detected language(s) (e.g., `['en', 'fr']`).

**FR-5.3.3:** The system shall explicitly flag the presence of **Non-Latin scripts** (e.g., Arabic, Chinese, Japanese).

**Method:** Library-based detection (langdetect, fasttext, or py3langid)

**Output:**
- `languages: List[str]` in DocumentMetadata
- `has_non_latin: bool` in DocumentMetadata

**Rationale:** Critical for OCR language pack selection and multi-script document handling

---

### FR-6: Document Quality Score (DQS) - Phase 4

#### FR-6.1: DQS Calculation

The system shall calculate a **Document Quality Score (DQS)** with two orthogonal axes:

**Axis 1: Degradation Score (0.0 - 1.0)**
- Measures physical image quality degradation
- Components: blur, noise, contrast, skew, resolution
- Scale: 0.0 = severe degradation, 1.0 = pristine quality

**Axis 2: Structural Complexity Score (0.0 - 1.0)**
- Measures layout and content complexity
- Components: multi-column, tables, formulas, figures, mixed scripts
- Scale: 0.0 = simple single-column, 1.0 = highly complex layout

**Reference:** ADR-0028 (Document Quality Score for Intelligent Pipeline Routing)

#### FR-6.2: Pipeline Routing Recommendation

The system shall provide a **routing_recommendation** based on DQS:

**Routing Matrix:**
```
                    LOW STRUCTURAL          HIGH STRUCTURAL
                    COMPLEXITY              COMPLEXITY
                    ─────────────────────────────────────────
HIGH DEGRADATION │  vision_simple       │  vision_structured   │
(Blurry, Noisy)  │  (VLM + Simple)      │  (VLM + Structure)   │
                 │                       │                      │
─────────────────┼──────────────────────┼──────────────────────┤
                 │                       │                      │
LOW DEGRADATION  │  ocr_fast            │  ocr_advanced        │
(Clean, Sharp)   │  (Tesseract)         │  (Nougat/Marker)     │
                 │                       │                      │
                 └───────────────────────┴──────────────────────┘
```

**Output:**
- `routing_recommendation`: Literal["vision_simple", "vision_structured", "ocr_fast", "ocr_advanced"]
- `routing_confidence`: float (0.0 - 1.0)
- `routing_rationale`: str (human-readable explanation)

---

## 3.0 Non-Functional Requirements (NFR)

### NFR-1: Performance

#### NFR-1.1: Hardware Configuration

**GPU Mode (Recommended for Production):**
- Hardware: NVIDIA T4 or better
- Use for: ML models (Phase 2-3), YOLOv8 layout detection

**CPU Mode (Development/Testing):**
- Hardware: Intel Xeon or equivalent
- Use for: Classical CV methods (Phase 1), validation

#### NFR-1.2: Performance Targets (GPU Mode)

**Latency:**
- **Target**: < 150ms per page
- **Acceptable**: < 400ms per page
- **Measurement**: p50, p95, p99 latencies

**Throughput:**
- **Target**: > 6 pages/sec per worker
- **Acceptable**: > 2 pages/sec per worker
- **Scalability**: Linear scalability to 100s of workers

**Batch Processing:**
- **Target**: 100 docs (5 pages each) in < 90 seconds
- **Calculation**: 500 pages / 90 sec = 5.56 pages/sec

#### NFR-1.3: Performance Targets (CPU Mode)

**Latency:**
- **Target**: < 400ms per page
- **Acceptable**: < 1000ms per page

**Throughput:**
- **Target**: > 2 pages/sec per worker
- **Acceptable**: > 0.5 pages/sec per worker

**Note:** CPU mode primarily for Phase 1 (classical CV) and development/testing.

**Reference:** ADR-0020 (CPU-First Deployment Strategy)

#### NFR-1.4: Resource Constraints

**GPU Memory:** < 2GB per worker

**CPU Cores:** 2-4 per worker

**RAM:** < 4GB per worker

**Disk:** Temporary file processing only (no persistent storage)

---

### NFR-2: Accuracy & Reliability

#### NFR-2.1: PDF Type Classification Accuracy

PDF type classification (FR-2.1) shall be **99.9% accurate** on the validation test set.

**Rationale:** High accuracy required to prevent routing errors

#### NFR-2.2: Skew Detection Accuracy

Skew angle detection (FR-3.2) shall be accurate to within **±0.5 degrees**.

**Method:** Compare detected angle to ground truth on validation set

#### NFR-2.3: Layout Model Accuracy

The layout detection model (FR-4.1) shall achieve:

**Primary Metric:**
- **mAP@.50** (COCO metric): > 0.82 (target), > 0.75 (acceptable)

**Secondary Metrics:**
- **mAP@.50-.95**: > 0.70
- **Per-class AP**: > 0.70 for all 11 classes (ensure rare class performance)

**Validation Dataset:** DocLayNet validation set (6,480 pages)

**Reference:** PROJECT_PLAN Phase 3 targets

#### NFR-2.4: Handwriting Classification Accuracy

The "Handwritten" vs. "Printed" classifier (FR-5.2) shall achieve an **F1-score ≥ 0.90** on the validation test set.

**Method:** Evaluate on balanced test set with 1000+ samples per class

#### NFR-2.5: Error Handling & Reliability

The system shall log all processing errors (per FR-1.4) without crashing or terminating the parent process/service.

**Requirements:**
- Must return a valid error-state JSON
- Error messages must be user-friendly
- Stack traces logged for debugging (not exposed to user)
- Graceful degradation: partial results if possible

---

### NFR-3: Maintainability & Extensibility

#### NFR-3.1: Configurability

All detection and correction thresholds shall be externalized into a configuration file (`.env` or `Settings` class) and not hard-coded.

**Examples:**
- `blur_threshold`
- `skew_angle_threshold`
- `dqs_degradation_threshold`
- `target_dpi`
- `pdf_upscale_algorithm`

**Implementation:** `src/image_preprocessing_detector/core/config.py`

#### NFR-3.2: Model Swapping

The layout detection model (FR-4.1) shall be loaded from a path specified in the configuration file, allowing the model file to be updated (e.g., a "v2" model) without requiring a new code deployment.

**Configuration:**
```python
layout_model_path: Path = Field(
    default=Path("models/yolov8_doclaynet_v1.onnx"),
    description="Path to YOLOv8 ONNX model"
)
```

#### NFR-3.3: Code Quality

The system's code shall adhere to team-defined linting standards and include docstrings for all major functions and classes.

**Standards:**
- **Formatter**: Ruff format
- **Linter**: Ruff check
- **Type Checker**: MyPy (strict on src/, relaxed on tests/)
- **Security**: Bandit + Safety
- **Coverage**: ≥ 80% test coverage

**References:**
- ADR-0001 (Consolidate Linting with Ruff)
- ADR-0013 (Real Testing Over Mocking)

---

### NFR-4: Deployment & Operations

#### NFR-4.1: Containerization

The system shall be delivered as a containerized application:
- Dockerfile for building image
- Pre-built image on container registry
- Docker Compose for local development

**Base Image:** Python 3.12 slim or alpine

**Dependencies:** All dependencies specified in `pyproject.toml`

#### NFR-4.2: Logging

The system shall generate **structured, human-readable logs** for all major processing steps:
- `file_received`
- `analysis_started`
- `correction_applied: deskew`
- `analysis_complete`
- `error_occurred`

**Format:** JSON-formatted logs using `structlog` + `rich` console

**Output:** All logs written to stdout/stderr

**Reference:** ADR-0019 (Structured Logging)

#### NFR-4.3: Statelessness

The application shall be **stateless**:
- No reliance on local disk (except temporary file processing)
- No in-memory session data between requests
- Each request is independent

**Rationale:** Enables horizontal scaling and Kubernetes deployment

---

### NFR-5: Security

#### NFR-5.1: Input Validation

All file inputs shall be validated:
- File size limits (default: 100MB, configurable)
- File format verification (magic bytes, not just extension)
- Path traversal prevention (no `../` in paths)

#### NFR-5.2: Dependency Scanning

All dependencies shall be scanned for vulnerabilities:
- **Bandit**: Python security analysis
- **Safety**: Dependency vulnerability check
- **OSV-Scanner**: OpenSSF vulnerability database

**CI/CD:** Scans run automatically on every PR and weekly

**Reference:** ADR-0004 (GitHub Actions Security Hardening)

#### NFR-5.3: Secrets Management

No secrets or API keys shall be hard-coded:
- All secrets in environment variables
- `.env.example` provided (no actual secrets)
- `.env` encrypted with GPG for local development

---

## 4.0 Phase Roadmap

### Phase 1: MVP with Classical Methods (Weeks 4-7) - ✅ COMPLETE
- Classical IQA (blur, skew, contrast detection)
- Text detection gate
- Basic corrections (deskew, CLAHE, sharpen, denoise)
- CLI tool
- JSON output

### Phase 1B: DPI Upscaling (Weeks 7-8) - ✅ COMPLETE
- DPI detection (PyMuPDF, EXIF)
- Automatic upscaling (5 OpenCV algorithms)
- Upscaling metadata tracking

### Phase 2: ML-Based IQA (Weeks 8-11) - 📋 PLANNED
- MobileNetV3/EfficientNet IQA model
- PDF type classification (image_only, born_digital, hybrid)
- Language detection (langdetect/fasttext)
- Handwriting vs. printed classification

### Phase 3: Document Layout Detection (Weeks 12-16) - 📋 PLANNED
- YOLOv8 layout detection (11 DocLayNet classes)
- Hybrid IQA (per-element quality assessment)
- Table structure recognition
- Formula/figure detection

### Phase 4: Production Hardening (Weeks 17-20) - 📋 PLANNED
- Document Quality Score (DQS) calculation
- Intelligent pipeline routing
- REST API (FastAPI)
- Monitoring and alerting (Prometheus/Grafana)
- Docker deployment

### Phase 5: Continuous Improvement (Weeks 21+) - 📋 PLANNED
- Office format preprocessing (embedded images)
- Active learning pipeline
- Model retraining automation
- A/B testing framework

---

## 5.0 Validation & Testing

### 5.1: Unit Testing

**Coverage:** ≥ 80% line coverage

**Test Categories:**
- Schema validation (Pydantic models)
- Detector accuracy (blur, skew, noise)
- Correction effectiveness (deskew, upscale)
- Configuration loading

**Framework:** pytest + pytest-cov

### 5.2: Integration Testing

**Test Scenarios:**
- End-to-end pipeline (file → JSON)
- Multi-page PDF processing
- Error handling (corrupted files, unsupported formats)
- DQS routing accuracy

### 5.3: Property-Based Testing

**Framework:** Hypothesis

**Test Properties:**
- Bounding boxes always within page dimensions
- DQS scores always in [0.0, 1.0]
- JSON schema validation never fails

**Reference:** ADR-0003 (Adopt Property-Based Testing)

### 5.4: Performance Testing

**Metrics:**
- Latency (p50, p95, p99)
- Throughput (pages/sec)
- Memory usage
- GPU utilization

**Tools:** pytest-benchmark, memory_profiler

---

## 6.0 Glossary

**COCO Format**: Common Objects in Context bounding box format `[x, y, width, height]`

**DPI**: Dots Per Inch, a measure of image resolution

**DQS**: Document Quality Score, a two-axis quality metric for routing

**IQA**: Image Quality Assessment

**OCR**: Optical Character Recognition

**VLM**: Vision-Language Model (e.g., ColPali)

**YOLOv8**: You Only Look Once version 8, an object detection model

---

## 7.0 References

**Project Documentation:**
- [PROJECT_PLAN.md](../../PROJECT_PLAN.md) - 50+ page implementation roadmap
- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md) - System design overview
- [PR_14_15_RECONCILIATION.md](../PR_14_15_RECONCILIATION.md) - Reconciliation with original PRs

**Architecture Decision Records:**
- [ADR-0007: Hybrid IQA Approach](../ADRs/0007-hybrid-iqa-approach.md)
- [ADR-0008: Multi-Stage Pipeline Architecture](../ADRs/0008-multi-stage-pipeline-architecture.md)
- [ADR-0009: COCO Bounding Box Format](../ADRs/0009-coco-bounding-box-format.md)
- [ADR-0010: 300 DPI Normalization](../ADRs/0010-300-dpi-normalization.md)
- [ADR-0021: Do-No-Harm Guardrails](../ADRs/0021-do-no-harm-guardrails.md)
- [ADR-0028: Document Quality Score Routing](../ADRs/0028-document-quality-score-routing.md)

**External Resources:**
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Docling](https://github.com/DS4SD/docling)

---

**Version:** 2.0
**Created:** 2025-11-11
**Last Updated:** 2025-11-11
**Status:** Active - Replaces PRs #14-15 functional_requirements.md
**Next Review:** Phase 2 Planning (Week 8)
