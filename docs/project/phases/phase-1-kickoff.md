# Phase 1: MVP with Classical Methods - KICKOFF 🚀

**Start Date**: 2025-01-15
**Duration**: 3-4 weeks (Weeks 4-7 from project start)
**Status**: ✅ APPROVED - Implementation begins

---

## Executive Summary

Phase 1 implements a functional image preprocessing pipeline using classical computer vision methods. This establishes the baseline system architecture and validates the end-to-end workflow from PDF input to structured JSON output.

**Key Innovation**: CPU-first approach optimized for Quadro P2000 + Xeon E5-2690 hardware, with clear GPU acceleration path in Phase 2-3.

---

## ✅ Finalized Decisions & Constraints

### Hardware Configuration (Unraid Server)
- **GPU**: NVIDIA Quadro P2000 (5GB VRAM, 1024 CUDA cores, Pascal architecture)
- **CPU**: 2× Intel Xeon E5-2690 (16 cores total @ 2.9-3.8 GHz)
- **RAM**: Assumed 32GB+ (typical for Xeon setup)
- **Deployment**: Shared GPU environment (Unraid multi-container)

**Phase 1 Strategy**: CPU-only implementation
- Quadro P2000 is modest GPU (equivalent to GTX 1050 Ti)
- Shared GPU environment requires careful resource management
- Reserve GPU for Phase 2-3 when ML models are added
- Classical CV methods run efficiently on dual Xeon CPUs

### Performance Targets
- **Throughput**: 1,000 pages/hour (0.28 pages/sec)
- **Latency**: < 500ms per page (generous budget for classical methods)
- **Baseline**: 3.6 seconds/page from OCR project
- **Target Improvement**: 7x faster than baseline (500ms vs 3.6s)

### v1 Detection Scope
**Must-Have** (Phase 1):
- ✅ Tables
- ✅ Text blocks
- ✅ Images/Figures

**Ideally** (if time permits in Phase 1, otherwise Phase 3):
- 🎯 Handwriting detection
- 🎯 Mathematical formulas

**Deferred to Post-OCR**:
- Superscript/subscript (requires baseline information)
- Footnotes (better detected after OCR)

### Test Data Sources
1. **DocLayNet** (1,000 annotated pages)
   - 11 layout classes: Caption, Footnote, Formula, List-item, Page-footer, Page-header, Picture, Section-header, Table, Text, Title
   - COCO format annotations
   - Validation for layout detection

2. **READoc** (500 PDFs with Markdown ground truth)
   - PDF→Markdown structure fidelity
   - End-to-end validation

3. **PubTables-1M** (500 table samples)
   - Table structure recognition
   - Specialized validation for tables

---

## Phase 1 Architecture

### Pipeline Overview

```
Input: PDF/Image file
    ↓
[Stage 1: Ingestion & Standardization]
- Load PDF with PyMuPDF
- Convert to 300 DPI images
- Detect current DPI (flag if upscaling needed)
- Multi-page handling
    ↓
[Stage 2: Text Detection Gate]
- Morphological stroke-density heuristic
- OpenCV EAST detector (if available)
- Ensemble decision (route to appropriate path)
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
[Stage 3A]     [Stage 3B]
Classical IQA  Classical Layout Detection
    ↓              ↓
- Skew (Hough) - Connected components
- Blur (Lap.)  - Contour analysis
- Contrast     - Text block detection
    ↓              ↓
[Stage 4: Correction & Output]
- Apply OpenCV corrections (with guardrails)
- Generate JSON using Pydantic schema
- Aggregate multi-page results
    ↓
Output: JSON metadata + corrected images
```

### Technology Stack (Phase 1)

**Core Libraries**:
- `opencv-python` 4.8+ - Image processing, classical CV
- `pymupdf` 1.26+ - PDF parsing and rendering
- `numpy` 1.24+ - Array operations
- `pillow` 10.0+ - Image I/O

**No ML Dependencies in Phase 1**:
- PyTorch, YOLOv8, ONNX → Phase 2-3
- Keeps Phase 1 lightweight and CPU-efficient

---

## Implementation Tasks

### Task 1: PDF/Image Ingestion (Week 1) ⏳

**Module**: `src/ingestion/`

**Files to Create**:
- `__init__.py` - Module exports
- `pdf_loader.py` - PDF to image conversion with PyMuPDF
- `image_loader.py` - Direct image loading (JPG, PNG, TIFF)
- `dpi_detector.py` - DPI detection and metadata extraction
- `document_processor.py` - High-level orchestration

**Key Features**:
1. **PDF Rendering**:
   ```python
   # Convert PDF to 300 DPI images
   doc = fitz.open(pdf_path)
   for page_num in range(len(doc)):
       page = doc[page_num]
       pix = page.get_pixmap(dpi=300)  # Target DPI
       img = np.frombuffer(pix.samples, dtype=np.uint8)
   ```

2. **DPI Detection**:
   - Extract from PDF metadata
   - Calculate from page dimensions
   - Flag if upscaling needed (< 300 DPI)

3. **Multi-page Handling**:
   - Process each page independently
   - Aggregate results at document level
   - Track page index, dimensions, DPI

**Tests**: 5-7 unit tests
- PDF loading with various DPI
- Multi-page document handling
- DPI detection accuracy
- Error handling (corrupted PDFs)

**Deliverable**: Functional ingestion module, 80%+ test coverage

---

### Task 2: Text Detection Gate (Week 1-2) 🚪

**Module**: `src/detection/text_gate.py`

**Approach**: Ensemble of fast heuristics
1. **Morphological Stroke Density**:
   ```python
   # Detect text-like structures via morphology
   gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
   gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
   stroke_density = np.count_nonzero(gradient > threshold) / gradient.size
   ```

2. **Connected Components Analysis**:
   - Count components with text-like aspect ratios
   - Typical text: aspect ratio 1:2 to 1:10
   - Cluster detection: groups of similar-sized components

3. **Edge Density**:
   - Canny edge detection
   - Text regions have consistent edge patterns

**Decision Logic**:
```python
has_text = (stroke_density > 0.05) or (text_components > 10)
confidence = weighted_average([stroke_density, component_score, edge_score])
```

**Tests**: 3-5 unit tests
- Text-heavy documents (high recall)
- Pure images (no false positives)
- Mixed documents (correct routing)

**Deliverable**: Text gate with 90%+ accuracy on test set

---

### Task 3: Classical IQA Detectors (Week 2) 🔍

**Module**: `src/detection/iqa_classical.py`

**Detectors to Implement**:

1. **Skew Detection** (Hough Transform):
   ```python
   def detect_skew(image: np.ndarray) -> tuple[float, float]:
       edges = cv2.Canny(image, 50, 150)
       lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100)
       angles = [compute_angle(line) for line in lines]
       skew_angle = np.median(angles)
       confidence = 1.0 - (np.std(angles) / 45.0)  # Confidence based on consistency
       return skew_angle, confidence
   ```

2. **Blur Detection** (Laplacian Variance):
   ```python
   def detect_blur(image: np.ndarray) -> tuple[float, float]:
       gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
       laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
       # Empirical thresholds: < 100 = blurry, > 500 = sharp
       blur_score = 1.0 - min(laplacian_var / 500.0, 1.0)
       confidence = 0.9  # Classical methods have consistent confidence
       return blur_score, confidence
   ```

3. **Low Contrast Detection** (Histogram Analysis):
   ```python
   def detect_low_contrast(image: np.ndarray) -> tuple[float, float]:
       gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
       hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
       # Measure histogram spread
       mean = np.mean(gray)
       std = np.std(gray)
       contrast_score = std / 128.0  # Normalized to [0, 1]
       confidence = 0.85
       return 1.0 - contrast_score, confidence  # Higher = worse contrast
   ```

**Tests**: 6-9 unit tests (2-3 per detector)
- Known skew angles
- Artificially blurred images
- Low-contrast synthetic images

**Deliverable**: Classical IQA with documented thresholds

---

### Task 4: Correction Pipeline (Week 2-3) 🔧

**Module**: `src/correction/`

**Files**:
- `corrections.py` - OpenCV correction functions
- `guardrails.py` - Do-no-harm validation
- `pipeline.py` - Orchestration

**Corrections to Implement**:

1. **Deskew**:
   ```python
   def apply_deskew(image: np.ndarray, angle: float, confidence: float) -> np.ndarray:
       if confidence < 0.85 or abs(angle) < 2.0:
           return image  # Guardrail: Don't correct if uncertain or small angle

       # Measure quality before
       quality_before = measure_variance(image)

       # Apply rotation
       center = (image.shape[1] // 2, image.shape[0] // 2)
       M = cv2.getRotationMatrix2D(center, angle, 1.0)
       deskewed = cv2.warpAffine(image, M, (image.shape[1], image.shape[0]))

       # Validate improvement
       quality_after = measure_variance(deskewed)
       if quality_after > quality_before * 1.05:  # 5% improvement required
           return deskewed
       return image  # Rollback if no improvement
   ```

2. **CLAHE** (Contrast Limited Adaptive Histogram Equalization):
   ```python
   def apply_clahe(image: np.ndarray, confidence: float) -> np.ndarray:
       if confidence < 0.80:
           return image  # Guardrail

       lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
       l, a, b = cv2.split(lab)

       clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
       l_clahe = clahe.apply(l)

       enhanced = cv2.merge([l_clahe, a, b])
       return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
   ```

3. **Sharpening** (Unsharp Mask):
   ```python
   def apply_sharpen(image: np.ndarray, confidence: float) -> np.ndarray:
       if confidence < 0.80:
           return image

       gaussian = cv2.GaussianBlur(image, (0, 0), 3.0)
       sharpened = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
       return sharpened
   ```

**Tests**: 6-9 unit tests
- Correction with high confidence (should apply)
- Correction with low confidence (should skip)
- Quality degradation detection (should rollback)

**Deliverable**: Safe correction pipeline with guardrails

---

### Task 5: Output Generation (Week 3) 📄

**Module**: `src/output/json_generator.py`

**Implementation**:
```python
from image_preprocessing_detector.schema import (
    DocumentMetadata,
    PageMetadata,
    DetectedIssue,
    PlannedAction,
    ProcessingVersion,
)

def generate_document_metadata(
    doc_id: str,
    file_name: str,
    pages_data: list[dict],
) -> DocumentMetadata:
    """Generate DocumentMetadata from processing results."""

    pages = []
    for page_data in pages_data:
        page = PageMetadata(
            page_index=page_data["index"],
            width_px=page_data["width"],
            height_px=page_data["height"],
            dpi_input=page_data["dpi_input"],
            dpi_effective=page_data["dpi_effective"],
            detected_issues=[
                DetectedIssue(
                    type=issue["type"],
                    confidence=issue["confidence"],
                    severity=issue["severity"],
                    metrics=issue.get("metrics", {}),
                )
                for issue in page_data.get("issues", [])
            ],
            planned_actions=[
                PlannedAction(
                    action=action["action"],
                    params=action["params"],
                    confidence=action["confidence"],
                    reason=action["reason"],
                )
                for action in page_data.get("actions", [])
            ],
        )
        pages.append(page)

    return DocumentMetadata(
        document_id=doc_id,
        file_name=file_name,
        source_mime="application/pdf",
        num_pages=len(pages),
        processing_version=ProcessingVersion(
            pipeline_version="0.1.0",
            thresholds={
                "skew": 0.85,
                "blur": 0.80,
                "contrast": 0.80,
            },
        ),
        pages=pages,
    )
```

**Tests**: 3-5 unit tests
- Single-page document
- Multi-page document
- JSON serialization/deserialization
- Schema validation

**Deliverable**: JSON generation using existing Pydantic schema

---

### Task 6: CLI Tool (Week 3) ⌨️

**Module**: `src/cli.py`

**Commands**:
```bash
# Process single file
imgprep process input.pdf --output result.json

# Batch processing
imgprep batch input_dir/ --output-dir results/

# With threshold tuning
imgprep process input.pdf \
  --blur-threshold 0.85 \
  --skew-threshold 0.90 \
  --output result.json

# Dry run (detection only, no correction)
imgprep process input.pdf --dry-run --output result.json
```

**Implementation** (using Click):
```python
import click
from pathlib import Path
from image_preprocessing_detector.pipeline import process_document

@click.group()
def cli():
    """Image Preprocessing Detector CLI."""
    pass

@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), required=True)
@click.option("--blur-threshold", default=0.80, type=float)
@click.option("--skew-threshold", default=0.85, type=float)
@click.option("--dry-run", is_flag=True, help="Detection only, no corrections")
def process(input_path, output, blur_threshold, skew_threshold, dry_run):
    """Process a single PDF/image file."""
    result = process_document(
        input_path,
        thresholds={
            "blur": blur_threshold,
            "skew": skew_threshold,
        },
        apply_corrections=not dry_run,
    )
    result.to_json_file(output)
    click.echo(f"✓ Processed {input_path} → {output}")

@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--output-dir", "-o", type=click.Path(), required=True)
@click.option("--workers", "-w", default=4, type=int)
def batch(input_dir, output_dir, workers):
    """Process a directory of files in parallel."""
    # Implementation in Week 3
    pass

if __name__ == "__main__":
    cli()
```

**Tests**: 3-5 integration tests
- Single file processing
- Batch processing
- Error handling (invalid inputs)

**Deliverable**: Functional CLI tool

---

## Success Criteria

### Functional Requirements
- ✅ End-to-end: PDF → JSON output
- ✅ Multi-page document support
- ✅ DPI detection and flagging
- ✅ Text detection gate (90%+ accuracy)
- ✅ Classical IQA (skew, blur, contrast)
- ✅ Correction pipeline with guardrails
- ✅ CLI tool (process + batch commands)

### Performance Requirements
- **Latency**: < 500ms per page (Phase 1 target)
- **Accuracy**: JSON Accuracy > 0.60 (baseline)
- **Stability**: No crashes on DocLayNet test set (1,000 pages)

### Code Quality
- **Test Coverage**: > 80% (unit + integration)
- **Code Quality**: All pre-commit hooks pass
- **Documentation**: Docstrings for all public functions

---

## Testing Strategy

### Unit Tests (Week 1-3, ongoing)
- **Target**: 30-40 unit tests by end of Phase 1
- **Coverage**: > 80% for all modules
- **Focus**: Individual functions, edge cases, error handling

### Integration Tests (Week 3)
- **Target**: 10-15 integration tests
- **Scenarios**:
  - End-to-end processing of sample PDFs
  - Multi-page documents with various issues
  - Batch processing workflows

### Validation Tests (Week 3)
- **DocLayNet Subset**: Test on 100 random samples
- **Metrics**:
  - Processing success rate (> 95%)
  - Average latency (< 500ms/page)
  - Crash rate (< 1%)

---

## Risk Mitigation

### Risk #1: Quadro P2000 Underutilization
**Mitigation**: Accepted - GPU reserved for Phase 2-3 ML models
**Impact**: Phase 1 CPU-only, no impact to timeline

### Risk #2: Classical Methods Insufficient Accuracy
**Mitigation**: Focus on high-precision thresholds (favor precision over recall)
**Fallback**: Skip corrections when confidence low (do-no-harm principle)

### Risk #3: Shared GPU Environment Conflicts
**Mitigation**: Phase 1 avoids GPU entirely
**Future**: Phase 2-3 will implement GPU resource management (CUDA_VISIBLE_DEVICES)

### Risk #4: Unraid Container Overhead
**Mitigation**: Benchmark early (Week 1) to establish baseline
**Contingency**: If overhead significant, recommend dedicated CPU allocation

---

## Phase 1 Timeline

| Week | Tasks | Deliverables |
|------|-------|--------------|
| **Week 1** | PDF ingestion, text gate | Ingestion module (80% coverage), text gate (90% accuracy) |
| **Week 2** | Classical IQA, correction start | IQA detectors (documented thresholds), correction functions |
| **Week 3** | Correction pipeline, output, CLI | Complete pipeline, JSON output, functional CLI |
| **Week 4** | Testing, validation, documentation | 80%+ coverage, DocLayNet validation, Phase 1 complete |

---

## Next Milestone

**Phase 1 Complete**: Functional baseline system with classical CV methods

**Phase 2 Goals** (Weeks 8-11):
- Train IQA multi-label CNN (MobileNetV3)
- GPU acceleration for ML inference
- Improve accuracy (JSON Accuracy > 0.75)
- Leverage Quadro P2000 for model inference

---

## Resources

### Documentation
- [PROJECT_PLAN.md](../../planning/PROJECT_PLAN.md) - Complete implementation plan
- [ARCHITECTURE_SUMMARY.md](../../architecture/ARCHITECTURE_SUMMARY.md) - Architecture reference
- [PHASE_0_COMPLETE.md](PHASE_0_COMPLETE.md) - Foundation summary

### Test Data
- DocLayNet: `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet/`
- READoc: `/home/byron/dev/data_ingestor/data/benchmarks/readoc/`
- PubTables-1M: `/home/byron/dev/data_ingestor/data/benchmarks/pubtables/`

### Hardware Specs
- **GPU**: NVIDIA Quadro P2000 (5GB VRAM, 1024 CUDA cores, Pascal)
- **CPU**: 2× Intel Xeon E5-2690 (16 cores, 2.9-3.8 GHz)
- **Platform**: Unraid server (multi-container environment)

---

**Phase 1 Start**: 2025-01-15
**Phase 1 Target Completion**: 2025-02-12 (4 weeks)

✅ **APPROVED - Implementation begins immediately**

---

*Generated via multi-model consensus (Gemini 2.5 Pro + GPT-5)*
*All decisions finalized and documented in DECISION_MATRIX.md*
