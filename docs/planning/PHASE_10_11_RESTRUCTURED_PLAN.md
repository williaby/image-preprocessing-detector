# Restructured Geometric Corrections & Docling Integration Plan

**Date**: 2026-01-29
**Status**: ✅ Reviewed & Improved (5-model consensus validation)
**Supersedes**: PHASE_10_11_GEOMETRIC_CORRECTIONS.md (original structure)

> **Consensus Review**: 2026-01-29 - Validated by Gemini 2.5 Pro, Gemini 3 Pro Preview,
> GPT-5.2, DeepSeek R1-0528, Grok 4. Average confidence: 8.4/10. All critical gaps addressed.

---

## Executive Summary

This document presents a restructured approach to the remaining Phase 10/11 work, designed around **value streams** and **training dependencies** rather than arbitrary phase boundaries. The plan addresses both the original Phase 10/11 requirements and the gaps identified in the OCR Routing Design Analysis.

**Key Changes from Original Plan:**

1. **Unified Teacher Model Strategy** - SigLIP2 as multi-task teacher instead of separate models
2. **Heuristic-First Approach** - Implement all no-training solutions first, benchmark, then upgrade with ML where needed
3. **Parallel Streams** - Work organized for maximum parallelism
4. **Mobile Deployment as Optional** - MobileCLIP distillation only if mobile edge deployment required

**Timeline**: 7-9 weeks (vs original 22 days Phase 10 + deferred Phase 11)

---

## Part 1: Current State Assessment

### 1.1 Existing Infrastructure

| Component | Status | Performance |
|-----------|--------|-------------|
| **SigLIP2-IQA** (86M) | ✅ Trained | VQualA 0.886, SRCC 0.896 |
| **ResNet-18 Student** | ✅ Trained | ≤10ms GPU, ≤40ms CPU |
| **ResNet-50 Teacher** | ✅ Trained | 5-head IQA |
| **DocLayout-YOLO** | ✅ Deployed | 11 classes, 85+ FPS |
| **Orientation Detector** | ✅ Heuristic | 3-method ensemble |
| **Classical IQA** | ✅ Deployed | 8 detectors, <25ms |
| **Text Gate** | ✅ Deployed | <10ms |
| **DeQA Pseudo-Labeling** | ✅ Ready | 5-model VLM ensemble |
| **Arena Benchmarking** | ✅ Ready | DIQA-5000 + others |
| **Modal GPU Training** | ✅ Ready | A10G/A100 |

### 1.2 Gap Analysis Summary

| Gap | Priority | Training Needed? | Estimated Effort |
|-----|----------|------------------|------------------|
| **Script Detection** | CRITICAL | Yes (if heuristic <80%) | 3-5 days |
| **Text Layer Quality** | HIGH | No | 1 day |
| **Camera vs Scanned** | HIGH | Optional | 2 days |
| **Shadow Detection** | MEDIUM-HIGH | No | 1 day |
| **Warping Detection** | HIGH | No | 1-2 days |
| **Degradation Severity** | HIGH | No | 0.5 days |
| **Code Detection** | MEDIUM | Optional | 1-2 days |
| **Table Complexity** | MEDIUM | No | 1 day |
| **PSM Hints** | MEDIUM | No | 0.5 days |
| **DoclingRouter** | HIGH | No | 5-7 days |
| **Border Removal** | MEDIUM | No | 2 days |
| **Perspective Correction** | MEDIUM | Optional | 3-4 days |

---

## Part 2: Restructured Work Streams

### Overview

```text
Week 1-2: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Stream 1: Foundation & Schema
          Stream 2: Heuristic Detectors (no training)
          Stream 3: Benchmarking & Gap Validation

Week 3-4: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Stream 4: Teacher Model Extension (SigLIP2 + heads)
          Stream 5: DoclingRouter Core Implementation
          Stream 6: Classical Geometric Corrections

Week 5-6: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Stream 4: (continued) Teacher Training
          Stream 7: Pseudo-Labeling Pipeline
          Stream 5: (continued) Router Integration

Week 7-8: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Stream 8: Student Model Training (if mobile needed)
          Stream 9: End-to-End Integration & Verification

Week 9:   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Buffer / Documentation / Optimization
```

---

## Stream 1: Foundation & Schema (Week 1)

**Goal**: All schema extensions upfront to unblock downstream work

**Reference**: See [STREAM_1_SCHEMA_ANALYSIS.md](STREAM_1_SCHEMA_ANALYSIS.md) for detailed analysis.

### 1.1 Key Findings: Reuse Existing Infrastructure

**DO NOT create new enums for these - they already exist:**

| Need | Existing Solution | Location |
|------|-------------------|----------|
| Document Source | `CaptureMethod` enum | `annotation/schemas/enums.py` |
| Script Codes | `ISO15924Script` enum | `schema_utils/iso_language_script.py` |
| Script Families | `ScriptFamily` enum | `schema_utils/iso_language_script.py` |

### 1.2 Three-Tier Script Architecture

**Principle**: Preserve maximum source granularity. We don't know which scripts need which engines until after testing.

```text
TIER 1: Storage Layer (Full ISO 15924)
├── Store EXACT script code from source data
├── 200+ possible values (full ISO 15924 standard)
├── NEVER lose source granularity
└── Examples: "Gujr", "Knda", "Mlym" (not just "Deva")

TIER 2: ML Training Layer (Grouped Classes) - CONFIG FILE
├── Aggregated classes for tractable training
├── ~18 classes (expandable as data allows)
├── Mapping in: config/script_ml_classes.yaml
└── "OTHER" bucket for scripts without dedicated training

TIER 3: Routing Layer (Engine Groups) - CONFIG FILE
├── Groups scripts by OCR engine recommendation
├── FULLY CONFIGURABLE - update after testing!
├── Mapping in: config/script_routing.yaml
└── Override rules for specific ISO 15924 codes
```

### 1.3 New Config Files (Critical)

```yaml
# config/script_ml_classes.yaml
# ISO 15924 → ML training class mapping (hot-reloadable)

ml_classes:
  - LATN, CYRL, GREK, ARAB, HEBR
  - DEVA, BENG, TAML, TELU
  - HANS, HANT, JPAN, KORE
  - THAI, TIBT
  - INDIC_OTHER, SE_ASIAN_OTHER, OTHER, UNKNOWN

iso15924_to_ml_class:
  Latn: LATN
  Gujr: INDIC_OTHER  # Can split later with more data
  # ... (see STREAM_1_SCHEMA_ANALYSIS.md for full mapping)
```

```yaml
# config/script_routing.yaml
# Script → OCR engine routing (update after testing!)

routing_rules:
  LATN: {engine: "rapidocr", batch_size: 8}
  HANS: {engine: "paddleocr", batch_size: 2, lang_hint: "ch"}
  ARAB: {engine: "tesseract", batch_size: 4, rtl: true}

# Override specific scripts that need different handling
iso15924_overrides:
  # Gujr: {engine: "tesseract", notes: "PaddleOCR bad for Gujarati"}

vlm_escalation:
  always_escalate: ["Tibt", "Ethi", "Mymr"]
```

### 1.4 Schema Extensions (Bridging Existing Infrastructure)

```python
# schema.py - Bridge existing enums to main schema

from image_preprocessing_detector.annotation.schemas.enums import CaptureMethod
from image_preprocessing_detector.schema_utils.iso_language_script import (
    ISO15924Script,
    ScriptFamily,
)

class ScriptDetectionResult(BaseModel):
    """Script detection with three-tier architecture support."""

    # TIER 1: Exact ISO 15924 code (NEVER aggregate)
    detected_script: str = Field(..., min_length=4, max_length=4)
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Source provenance (preserve original labels)
    source_label: str | None = Field(None)
    detection_method: str = Field(...)

    # Full probability distribution over ISO 15924 codes
    script_probabilities: dict[str, float] = Field(default_factory=dict)

    # Unknown handling
    is_unknown: bool = Field(default=False)
    unknown_reason: str | None = Field(None)

    # Region-level detection (for mixed-script docs)
    bbox: list[int] | None = Field(None)
    page_index: int | None = Field(None)

    # Tier 2/3 computed via config (not stored)
    def get_ml_class(self, mapping: ScriptMLMapping) -> str: ...
    def get_routing_config(self, router: ScriptRouter) -> dict: ...


class DocumentScriptDetection(BaseModel):
    """Document-level script detection preserving full granularity."""

    script_instances: list[ScriptDetectionResult] = Field(default_factory=list)
    dominant_script: str = Field(...)
    dominant_confidence: float = Field(...)
    script_distribution: dict[str, float] = Field(default_factory=dict)
    is_multilingual: bool = Field(default=False)
    unique_scripts: list[str] = Field(default_factory=list)


class DoclingRoutingParams(BaseModel):
    """Docling CLI parameters derived from Project A analysis."""

    pipeline: Literal["standard", "vlm", "legacy"] = "standard"
    vlm_model: str | None = None
    ocr_enabled: bool = True
    ocr_force: bool = False
    ocr_engine: str = "auto"
    ocr_lang: str | None = None
    psm: int | None = None
    tables_enabled: bool = True
    table_mode: Literal["fast", "accurate"] = "accurate"
    enrich_code: bool = False
    enrich_formula: bool = False
    page_batch_size: int = 4

    def to_cli_args(self) -> list[str]: ...


class TableComplexity(BaseModel):
    """Table structure complexity indicators."""

    has_borders: bool = True
    estimated_rows: int = 0
    estimated_columns: int = 0
    has_merged_cells: bool = False
    complexity_score: float = Field(ge=0.0, le=1.0, default=0.5)


# Extend PageLayoutSummary with CONTINUOUS scores (not binary!)
class PageLayoutSummary(BaseModel):
    # ... existing fields ...

    # Shadow detection (continuous)
    has_shadows: bool = False
    shadow_score: float = Field(default=0.0, ge=0.0, le=1.0)
    shadow_severity: Literal["none", "mild", "moderate", "severe"] = "none"

    # Warping detection (continuous)
    has_warping: bool = False
    warping_score: float = Field(default=0.0, ge=0.0, le=1.0)
    warping_type: str | None = None

    # Code detection
    has_code: bool = False
    code_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Table complexity
    table_complexity: TableComplexity | None = None


# Extend DocumentMetadata
class DocumentMetadata(BaseModel):
    # ... existing fields ...

    # Capture method (reuse existing enum!)
    capture_method: CaptureMethod | None = Field(None)
    capture_method_confidence: float | None = Field(None, ge=0.0, le=1.0)

    # Script detection (three-tier architecture)
    script_detection: DocumentScriptDetection | None = Field(None)

    # Text layer quality (continuous)
    text_layer_quality: float | None = Field(None, ge=0.0, le=1.0)
    text_layer_skip_ocr: bool = Field(default=False)

    # Degradation severity (simple literal, not enum)
    degradation_severity: Literal["simple", "complex"] = "simple"

    # Docling routing
    docling_params: DoclingRoutingParams | None = Field(None)
    recommended_psm: int | None = Field(None, ge=0, le=13)
```

### 1.5 Core Deliverables

- [x] Bridge `CaptureMethod` from annotation schemas to main schema
- [x] Create `ScriptDetectionResult` with three-tier support
- [x] Create `DocumentScriptDetection` for multi-script handling
- [x] Create `config/script_ml_classes.yaml` with ISO → ML mapping
- [x] Create `config/script_routing.yaml` with engine routing
- [x] Create `ScriptMLMapping` and `ScriptRouter` classes
- [x] Extend `PageLayoutSummary` with continuous scores
- [x] Extend `DocumentMetadata` with new fields
- [x] Unit tests for all new models (59 tests passing)
- [x] Migration guide for downstream consumers

### 1.6 Extended Deliverables (Parser Alignment & Documentation)

The following deliverables were added to ensure existing annotation infrastructure
aligns with the three-tier script architecture:

**Parser Infrastructure:**

- [x] Add `iso15924_script_code` field to `OriginalLabels` dataclass
- [x] Update 13 multilingual/handwriting parsers to populate `iso15924_script_code`:
  - `Mlt19Parser`, `ArabicDocsParser`, `TibhcrParser`, `NepaliHandwrittenParser`
  - `YarmoukParser`, `CvsiParser`, `Siw13Parser`, `Mle2eParser`
  - `CcOcrParser`, `Mdiw13Parser`, `HindiOcrSyntheticParser`
  - `PucitOhulParser`, `MultilingualScriptsParser`
- [x] Standardize `script_name` (human-readable) vs `iso15924_script_code` (ISO code)

**Validation Helpers:**

- [x] `is_valid_iso15924_code()` - Check if code is valid ISO 15924
- [x] `get_iso15924_script()` - Convert string to `ISO15924Script` enum
- [x] `validate_script_code_for_ml()` - Validate with suggestions for corrections

**DatasetInfo Template:**

- [x] Add `validate_script_code()` method to `DatasetInfo`
- [x] Update `validate_dataset_info()` to include script code validation
- [x] Provide corrective suggestions for common errors (case, legacy names)

**Architecture Documentation:**

- [x] Update Level 2 data-preparation/index.md with three-tier script architecture section
- [x] Update `STREAM_1_MIGRATION_GUIDE.md` with parser alignment section
- [x] Document all new validation helpers and parser changes

**Duration**: 3-4 days (core) + 1-2 days (extended)

---

## Stream 2: Heuristic Detectors (Week 1-2)

**Goal**: Implement all no-training detectors, establish accuracy baselines

### ⚠️ CRITICAL: Pipeline Ordering

**Orientation detection/correction MUST be the FIRST step in the pipeline** before any other analysis. Running text detection, script detection, IQA, or layout analysis on rotated images produces invalid results.

```text
CORRECT ORDER:

1. Orientation Detection → Correction (FIRST!)
2. Blank Page Detection (skip processing if blank)
3. Text Gate
4. Script Detection
5. IQA (Classical + ML)
6. Layout Detection
7. Other detectors
```

### 2.0 Orientation Detection & Correction (FIRST STEP)

**Location**: `src/detection/orientation_detector.py` (EXISTING)

**Status**: ✅ Already implemented with 85% accuracy

The existing `OrientationDetector` uses a 3-method ensemble:

- Text line angle analysis
- Edge histogram orientation
- Component aspect ratio analysis

```python
class OrientationDetector:
    """Detect page orientation using heuristic ensemble.

    CRITICAL: This MUST run before any other detection step.
    Rotated pages will cause:
    - Script detection to fail (CJK vs Latin confusion)
    - Text gate false negatives
    - IQA metrics to be invalid
    - Layout detection errors
    """

    def detect(self, image: np.ndarray) -> OrientationResult:
        """Detect orientation (0°, 90°, 180°, 270°).

        Returns:
            OrientationResult with:
            - detected_angle: 0, 90, 180, or 270
            - confidence: 0.0-1.0
            - needs_correction: bool
            - correction_applied: bool (after correction)
        """
        # Existing 3-method ensemble
        text_angle = self._text_line_analysis(image)
        edge_angle = self._edge_histogram_orientation(image)
        comp_angle = self._component_aspect_ratio(image)

        # Voting with confidence weighting
        return self._ensemble_vote([text_angle, edge_angle, comp_angle])
```

**Integration Point**: Orientation correction applied BEFORE detection phase:

```python
# In enhanced_pipeline.py process() method:
# Phase 2.0: ORIENTATION FIRST (critical!)
orientation = self.orientation_detector.detect(image)
if orientation.needs_correction:
    image = self._apply_orientation_correction(image, orientation)
    orientation.correction_applied = True
```

**Accuracy Target**: 85% (current baseline), 98%+ with ML upgrade (Stream 4)
**Latency**: <10ms
**Training Required**: No (upgrade in Stream 4 for edge cases)

### 2.0.1 Blank Page Detector

**Location**: `src/detection/blank_page_detector.py` (NEW)

```python
class BlankPageDetector:
    """Detect blank/near-blank pages for early pipeline exit.

    Should run immediately after orientation correction.
    Blank pages can skip all subsequent processing.
    """

    def __init__(
        self,
        content_threshold: float = 0.02,  # 2% non-white pixels
        edge_threshold: float = 0.01,      # 1% edge density
    ):
        self.content_threshold = content_threshold
        self.edge_threshold = edge_threshold

    def detect(self, image: np.ndarray) -> BlankPageResult:
        """Detect if page is blank.

        Methods:
        1. Pixel variance analysis (blank = low variance)
        2. Edge density (blank = minimal edges)
        3. Content ratio (non-white pixels / total)
        """
        variance = np.var(image)
        edges = cv2.Canny(image, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size

        # Grayscale content check
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        content_ratio = np.count_nonzero(gray < 250) / gray.size

        is_blank = (
            content_ratio < self.content_threshold and
            edge_density < self.edge_threshold
        )

        return BlankPageResult(
            is_blank=is_blank,
            content_ratio=content_ratio,
            edge_density=edge_density,
            variance=variance,
        )
```

**Accuracy Target**: 95%+
**Latency**: <5ms
**Training Required**: No

### 2.0.2 Handwriting Detector

**Location**: `src/detection/handwriting_detector.py` (NEW)

**Rationale**: DoclingRouter checks `has_handwriting` for VLM escalation but no detector was defined.

```python
class HandwritingDetector:
    """Detect handwritten content for VLM escalation routing.

    Handwritten content requires VLM pipeline for accurate OCR.
    """

    def detect(self, image: np.ndarray) -> HandwritingResult:
        """Detect handwriting using visual features.

        Heuristic signals:
        1. Stroke irregularity (handwriting = variable stroke width)
        2. Baseline variation (handwriting = inconsistent baselines)
        3. Character spacing variation (handwriting = irregular)
        4. Connected component complexity (handwriting = more complex)
        """
        # Binarize for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Analyze connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)

        # Stroke width variation (handwriting signature)
        stroke_variation = self._measure_stroke_variation(binary)

        # Baseline consistency
        baseline_variation = self._measure_baseline_variation(centroids, stats)

        # Character spacing variation
        spacing_variation = self._measure_spacing_variation(stats)

        # Combined score
        handwriting_score = self._combine_features(
            stroke_variation, baseline_variation, spacing_variation
        )

        return HandwritingResult(
            has_handwriting=handwriting_score > 0.5,
            handwriting_score=handwriting_score,
            stroke_variation=stroke_variation,
            baseline_variation=baseline_variation,
        )
```

**Accuracy Target**: 80%+
**Latency**: <15ms
**Training Required**: Optional (extend ML if <80%)

### 2.1 Text Layer Quality Analyzer

**Location**: `src/classification/text_layer_analyzer.py`

```python
class TextLayerAnalyzer:
    """Analyze PDF text layer quality using PyMuPDF."""

    def analyze(self, pdf_path: str) -> TextLayerQuality:
        """Calculate text layer quality score (0-1).

        Factors:
        1. Character extractability rate
        2. Unicode consistency (replacement chars)
        3. Font embedding completeness
        4. Coordinate precision
        5. Text density vs expected
        """
        import fitz

        doc = fitz.open(pdf_path)
        # ... implementation
        return TextLayerQuality(score=0.85, ...)
```

**Accuracy Target**: 85%+ correlation with OCR skip success
**Latency**: <50ms per PDF
**Training Required**: No

### 2.2 Shadow Detector

**Location**: `src/detection/shadow_detector.py`

**Approach**: Extend existing `IlluminationDetector`

```python
class ShadowDetector:
    """Detect shadows from uneven illumination."""

    def __init__(self, illumination_detector: IlluminationDetector):
        self.illumination = illumination_detector

    def detect(self, image: np.ndarray) -> ShadowDetection:
        """Detect shadows using gradient and variance analysis.

        Methods:
        1. Local brightness variance (grid-based)
        2. Gradient direction consistency
        3. Soft edge detection (shadow boundaries)
        """
        # Reuse illumination detector internals
        illum_result = self.illumination.detect(image)
        # Extend with shadow-specific analysis
        ...
```

**Accuracy Target**: 85%+
**Latency**: <10ms (extends existing detector)
**Training Required**: No

### 2.3 Warping Detector

**Location**: `src/detection/warping_detector.py`

**Approach**: Extend existing `SkewDetector` with curvature analysis

```python
class WarpingDetector:
    """Detect document warping/curvature."""

    def detect(self, image: np.ndarray) -> WarpingDetection:
        """Detect warping using text line curvature.

        Methods:
        1. Hough line curvature analysis
        2. Page boundary rectangularity
        3. Polynomial fit to text lines
        """
        # Reuse skew detector's Hough transform
        lines = self._detect_text_lines(image)
        curvature = self._measure_line_curvature(lines)
        ...
```

**Accuracy Target**: 80-90%
**Latency**: <15ms
**Training Required**: No

### 2.4 Camera vs Scanned Classifier

**Location**: `src/classification/document_source_classifier.py`

```python
class DocumentSourceClassifier:
    """Classify document capture source."""

    def classify(self, image: np.ndarray) -> DocumentSourceResult:
        """Classify as scanned/camera/digital.

        Heuristic signals:
        1. Page boundary analysis (rectangular = scan)
        2. Background uniformity (uniform = scan)
        3. Illumination patterns (even = scan)
        4. Edge sharpness (sharp = scan)
        5. Perspective distortion (present = camera)
        """
        ...
```

**Accuracy Target**: 80-90%
**Latency**: <20ms
**Training Required**: Optional (upgrade with ML if <85%)

### 2.5 Code Region Detector

**Location**: `src/detection/code_detector.py`

```python
class CodeDetector:
    """Detect code blocks using visual patterns."""

    def detect(self, image: np.ndarray, layout_elements: list) -> bool:
        """Detect code regions.

        Heuristic signals:
        1. Monospace font detection (uniform char width)
        2. High horizontal alignment (indentation)
        3. Dark background with light text
        4. Consistent line heights
        """
        ...
```

**Accuracy Target**: 75-85%
**Latency**: <10ms
**Training Required**: Optional

### 2.6 Table Complexity Analyzer

**Location**: `src/detection/table_complexity.py`

```python
class TableComplexityAnalyzer:
    """Analyze table structure complexity."""

    def analyze(self, table_bbox: list, image: np.ndarray) -> TableComplexity:
        """Analyze complexity within YOLO-detected table region.

        Methods:
        1. Line detection (Hough) for row/column count
        2. Border presence detection
        3. Cell regularity analysis
        """
        ...
```

**Accuracy Target**: 80-85%
**Latency**: <20ms per table
**Training Required**: No

### 2.7 Script Detector (Heuristic Baseline)

**Location**: `src/detection/script_detector.py`

```python
class ScriptDetectorHeuristic:
    """Fast script detection using visual features."""

    def detect(self, image: np.ndarray) -> ScriptDetection:
        """Detect dominant script.

        Methods:
        1. Character aspect ratio analysis
           - CJK: ~1.0 (square)
           - Latin: ~1.5-2.0 (taller)
        2. Stroke density patterns
           - CJK: Higher density per character
           - Latin: More whitespace
        3. Connected component analysis
           - CJK: Larger, more complex
           - Latin: Smaller, simpler
        4. Text direction indicators
           - RTL: Arabic, Hebrew
           - Vertical: CJK potential
        """
        ...
```

**Accuracy Target**: 70-80% (baseline for ML upgrade decision)
**Latency**: <15ms
**Training Required**: Yes, if baseline <80%

### 2.8 Supporting Components

```python
# Degradation Severity Classifier (pure logic)
class DegradationSeverityClassifier:
    """Classify degradation severity from existing IQA signals."""

    def classify(
        self,
        document_source: DocumentSource,
        dqs: DQSMetadata,
        has_shadows: bool,
        has_warping: bool,
    ) -> DegradationSeverity:
        # Camera = always complex
        if document_source == DocumentSource.CAMERA_CAPTURED:
            return DegradationSeverity.COMPLEX

        # Count severe issues
        severe_count = sum([
            dqs.degradation_score < 0.5,
            has_shadows,
            has_warping,
        ])

        return DegradationSeverity.COMPLEX if severe_count >= 2 else SIMPLE

# PSM Recommender (lookup table)
class PSMRecommender:
    """Recommend Tesseract PSM from layout attributes."""

    PSM_MAP = {
        ("single_column", False, False): 3,  # Fully automatic
        ("single_column", True, False): 6,   # Uniform block
        ("multi_column", False, False): 1,   # Auto with OSD
        ("sparse", False, True): 11,         # Sparse text
    }

    def recommend(self, layout_type: str, has_tables: bool, sparse: bool) -> int:
        return self.PSM_MAP.get((layout_type, has_tables, sparse), 3)
```

### 2.10 Stream 2 Deliverables

**CRITICAL (Week 1 - Must Complete First):**

- [ ] Integrate existing `OrientationDetector` as pipeline's FIRST step
- [ ] Add orientation correction to pipeline before any detection
- [ ] `BlankPageDetector` implementation + tests
- [ ] `HandwritingDetector` implementation + tests
- [ ] Verify pipeline ordering: Orientation → Blank → Corrections → Detection

**Core Detectors (Week 1-2):**

- [ ] `TextLayerAnalyzer` implementation + tests
- [ ] `ShadowDetector` implementation + tests
- [ ] `WarpingDetector` implementation + tests
- [ ] `DocumentSourceClassifier` implementation + tests
- [ ] `CodeDetector` implementation + tests
- [ ] `TableComplexityAnalyzer` implementation + tests
- [ ] `ScriptDetectorHeuristic` implementation + tests
- [ ] `DegradationSeverityClassifier` implementation + tests
- [ ] `PSMRecommender` implementation + tests

**Integration:**

- [ ] Integration into pipeline with correct ordering
- [ ] E2E test verifying orientation runs FIRST
- [ ] E2E test verifying blank page early exit
- [ ] E2E test verifying handwriting triggers VLM escalation

**Duration**: 5-7 days

---

## Stream 3: Benchmarking & Gap Validation (Week 2)

**Goal**: Benchmark heuristic accuracy, determine ML upgrade needs

### 3.1 Benchmark Datasets

| Task | Dataset | Samples | Labels Available |
|------|---------|---------|------------------|
| Script Detection | MLT-2019 | 10K+ | Script labels ✅ |
| Script Detection | COCO-Text | 63K | Script labels ✅ |
| Camera vs Scanned | SmartDoc-QA | 4,260 | Source labels ✅ |
| Warping | SmartDoc-QA | 4,260 | Visual inspection |
| Shadow | AnyPhotoDoc | 6,300 | Visual inspection |
| Text Layer Quality | DIQA-5000 | 5,000 | Correlate with OCR |

### 3.2 Accuracy Thresholds

| Task | Heuristic Target | ML Upgrade Threshold |
|------|------------------|---------------------|
| Script Detection | 80% | If <80%, train ML |
| Camera vs Scanned | 85% | If <85%, train ML |
| Shadow Detection | 85% | If <85%, extend ML IQA |
| Warping Detection | 80% | If <80%, extend ML IQA |
| Code Detection | 75% | If <75%, fine-tune YOLO |

### 3.3 Benchmark Protocol

```python
# scripts/benchmark_heuristics.py

def benchmark_script_detection():
    """Benchmark script detection on MLT-2019."""
    from labeling.arena import ArenaRunner

    detector = ScriptDetectorHeuristic()
    dataset = load_mlt2019()

    results = []
    for image, label in dataset:
        pred = detector.detect(image)
        results.append({
            "true": label.script,
            "pred": pred.dominant_script,
            "confidence": pred.dominant_confidence,
        })

    accuracy = calculate_accuracy(results)
    confusion = calculate_confusion_matrix(results)

    # Decision: proceed with ML if accuracy < 80%
    return {
        "accuracy": accuracy,
        "confusion_matrix": confusion,
        "needs_ml": accuracy < 0.80,
    }
```

### 3.4 Stream 3 Deliverables

- [ ] Benchmark scripts for each heuristic
- [ ] Accuracy report with confusion matrices
- [ ] Go/No-Go decision document for ML upgrades
- [ ] Dataset preparation for ML training (if needed)

**Duration**: 2-3 days (parallel with Stream 2)

---

## Stream 4: Teacher Model Extension (Weeks 3-5)

**Goal**: Extend SigLIP2 with additional task heads for high-accuracy detection

### 4.1 Architecture: SigLIP2 Multi-Task Teacher

**Key Insight**: Instead of training separate models, extend the existing SigLIP2-IQA model with additional heads. This provides:

- Single forward pass for all tasks
- Shared vision-language understanding
- Efficient pseudo-labeling
- Proven backbone (VQualA 0.886)

```python
class SigLIP2MultiTaskTeacher(nn.Module):
    """SigLIP2 with multiple task heads.

    Extends the trained SigLIP2-IQA model with heads for:
    - Script detection (12 classes)
    - Document source (3 classes)
    - Orientation (4 classes)
    - Shadows (regression)
    - Warping (regression)
    """

    def __init__(self, pretrained_iqa_path: str):
        super().__init__()

        # Load trained SigLIP2-IQA backbone
        self.backbone = self._load_backbone(pretrained_iqa_path)

        # Existing IQA heads (frozen or fine-tuned)
        self.iqa_heads = nn.ModuleDict({
            "overall": IQAHead(768, 2),     # mu, sigma
            "sharpness": IQAHead(768, 2),
            "color": IQAHead(768, 2),
        })

        # NEW: Detection heads
        self.detection_heads = nn.ModuleDict({
            "script": nn.Sequential(
                nn.Linear(768, 256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, 12),  # 12 script classes
            ),
            "document_source": nn.Sequential(
                nn.Linear(768, 64),
                nn.ReLU(),
                nn.Linear(64, 3),  # scanned/camera/digital
            ),
            "orientation": nn.Sequential(
                nn.Linear(768, 64),
                nn.ReLU(),
                nn.Linear(64, 4),  # 0/90/180/270
            ),
            "shadows": nn.Sequential(
                nn.Linear(768, 64),
                nn.ReLU(),
                nn.Linear(64, 2),  # mu, sigma
            ),
            "warping": nn.Sequential(
                nn.Linear(768, 64),
                nn.ReLU(),
                nn.Linear(64, 2),  # mu, sigma
            ),
        })

    def forward(
        self,
        pixel_values: torch.Tensor,
        spatial_shapes: torch.Tensor,
        tasks: list[str] | None = None,
    ) -> dict[str, torch.Tensor]:
        """Forward pass with selective task execution."""

        # Backbone features
        features = self.backbone(pixel_values, spatial_shapes).pooler_output

        outputs = {}

        # IQA (always computed)
        for name, head in self.iqa_heads.items():
            outputs[f"iqa_{name}"] = head(features)

        # Detection tasks (selective)
        tasks = tasks or list(self.detection_heads.keys())
        for name in tasks:
            if name in self.detection_heads:
                outputs[name] = self.detection_heads[name](features)

        return outputs
```

### 4.2 Training Strategy

**Phase 1: Head Training (Frozen Backbone)**

- Freeze SigLIP2 backbone and IQA heads
- Train only new detection heads
- Use existing datasets (MLT, SmartDoc-QA, synthetic)
- 10-15 epochs

**Phase 2: Joint Fine-Tuning (Optional)**

- Unfreeze backbone with low LR (0.1x multiplier)
- Use PCGrad for multi-task gradient conflict
- 20-30 epochs
- Only if Phase 1 accuracy insufficient

### 4.3 Training Data Sources

| Task | Primary Dataset | Augmentation |
|------|-----------------|--------------|
| Script (12 classes) | MLT-2019 (10K/class) | Font rendering |
| Document Source | SmartDoc-QA (4,260) | Synthetic scans |
| Orientation | Synthetic rotation | Random rotation |
| Shadows | VLM pseudo-labels | Synthetic shadows |
| Warping | SmartDoc-QA | Synthetic warping |

### 4.4 Expected Accuracy

| Task | Heuristic Baseline | Teacher Target |
|------|-------------------|----------------|
| Script Detection | 70-80% | 92-95% |
| Document Source | 80-90% | 94-97% |
| Orientation | 85% (current) | 98%+ |
| Shadows | 85% | 90%+ |
| Warping | 80-90% | 92%+ |

### 4.5 Stream 4 Deliverables

- [ ] `SigLIP2MultiTaskTeacher` architecture
- [ ] Training script (`modal/train_siglip2_multitask.py`)
- [ ] Dataset loaders for each task
- [ ] Training run (Modal A10G)
- [ ] Model checkpoint + metrics
- [ ] Accuracy benchmarks on held-out sets

**Duration**: 7-10 days (training runs in background)

---

## Stream 5: DoclingRouter Implementation (Weeks 3-6)

**Goal**: Full Docling CLI parameter generation from Project A metadata

### 5.1 Routing Engine Architecture

```python
# src/routing/docling_router.py

class DoclingRoutingEngine:
    """Generate Docling CLI parameters from document analysis."""

    def __init__(self, config: DoclingRoutingConfig | None = None):
        self.config = config or DoclingRoutingConfig()

    def route(self, metadata: DocumentMetadata) -> DoclingRoutingParams:
        """Generate routing parameters from document metadata."""

        params = DoclingRoutingParams()

        # Rule 1: Text layer quality → OCR decision
        if metadata.pdf_type == PDFType.BORN_DIGITAL:
            if metadata.text_layer_quality >= 0.90:
                params.ocr_enabled = False
                params.pipeline = "standard"
                return params
            elif metadata.text_layer_quality >= 0.60:
                params.ocr_force = False  # Supplement only

        # Rule 2: Script-aware engine selection
        if metadata.script_detection:
            script = metadata.script_detection.dominant_script
            confidence = metadata.script_detection.dominant_confidence

            if script in [ScriptType.LATIN, ScriptType.CYRILLIC, ScriptType.GREEK]:
                if confidence >= 0.70 and metadata.dqs.degradation_score >= 0.6:
                    params.ocr_engine = "rapidocr"
                else:
                    params.ocr_engine = "tesseract"
            elif script in [ScriptType.HAN, ScriptType.HANGUL, ScriptType.HIRAGANA_KATAKANA]:
                params.ocr_engine = "auto"
                params.page_batch_size = 2  # Memory safety for CJK

        # Rule 3: VLM escalation for difficult documents
        if self._should_escalate_to_vlm(metadata):
            params.pipeline = "vlm"
            params.vlm_model = "deepseekocr_ollama"
            params.ocr_enabled = False

        # Rule 4: Table mode selection
        if metadata.page_layout_summary:
            summary = metadata.page_layout_summary[0]
            if summary.has_tables and summary.table_complexity:
                tc = summary.table_complexity
                if tc.has_merged_cells or tc.complexity_score >= 0.6:
                    params.table_mode = "accurate"
                else:
                    params.table_mode = "fast"

        # Rule 5: Enrichments
        if metadata.page_layout_summary:
            summary = metadata.page_layout_summary[0]
            params.enrich_code = summary.has_code
            params.enrich_formula = summary.has_dense_math

        # Rule 6: PSM recommendation
        params.psm = metadata.recommended_psm

        return params

    def _should_escalate_to_vlm(self, metadata: DocumentMetadata) -> bool:
        """Determine if VLM pipeline is needed.

        VLM escalation triggers:
        - Handwriting detected (OCR unreliable)
        - Severe quality degradation (DQS < 0.4)
        - Low script confidence (ambiguous script)
        - Complex degradation pattern
        - Extreme warping (>25°, classical correction unreliable)
        - Wet/damaged documents
        - Mixed orientation within document
        """
        escalation_reasons = []

        # Check handwriting
        if metadata.page_layout_summary and any(
            p.has_handwriting for p in metadata.page_layout_summary
        ):
            escalation_reasons.append("handwriting_detected")

        # Check quality degradation
        if metadata.dqs.degradation_score < 0.4:
            escalation_reasons.append("severe_degradation")

        # Check script confidence
        if (
            metadata.script_detection
            and metadata.script_detection.dominant_confidence < 0.55
        ):
            escalation_reasons.append("low_script_confidence")

        # Check degradation complexity
        if metadata.degradation_severity == DegradationSeverity.COMPLEX:
            escalation_reasons.append("complex_degradation")

        # NEW: Check extreme warping (>25° = 0.75+ warping_score)
        # Classical perspective correction is unreliable beyond this threshold
        if metadata.page_layout_summary and any(
            p.has_warping and p.warping_score > 0.75
            for p in metadata.page_layout_summary
        ):
            escalation_reasons.append("extreme_warping_over_25_degrees")

        # NEW: Check for wet/damaged documents (special degradation type)
        if metadata.page_layout_summary and any(
            "water_damage" in (p.degradations or []) or
            "torn" in (p.degradations or [])
            for p in metadata.page_layout_summary
        ):
            escalation_reasons.append("wet_or_damaged_document")

        # NEW: Check for mixed orientation within document
        # (different pages have different orientations after correction)
        if metadata.page_layout_summary and len(metadata.page_layout_summary) > 1:
            orientations = [
                p.orientation.detected_angle
                for p in metadata.page_layout_summary
                if hasattr(p, 'orientation') and p.orientation
            ]
            if len(set(orientations)) > 1:
                escalation_reasons.append("mixed_orientation_document")

        # Store reasons for debugging/telemetry
        if escalation_reasons:
            metadata.vlm_escalation_reasons = escalation_reasons

        return len(escalation_reasons) > 0
```

### 5.2 CLI Generation

```python
class DoclingRoutingParams(BaseModel):
    # ... fields ...

    def to_cli_args(self) -> list[str]:
        """Convert to Docling CLI arguments."""
        args = [f"--pipeline={self.pipeline}"]

        if self.vlm_model:
            args.append(f"--vlm-model={self.vlm_model}")

        if not self.ocr_enabled:
            args.append("--no-ocr")
        elif self.ocr_force:
            args.append("--force-ocr")

        if self.ocr_engine != "auto":
            args.append(f"--ocr-engine={self.ocr_engine}")

        if self.ocr_lang:
            args.append(f"--ocr-lang={self.ocr_lang}")

        if self.psm:
            args.append(f"--psm={self.psm}")

        args.append(f"--table-mode={self.table_mode}")

        if self.enrich_code:
            args.append("--enrich-code")

        if self.enrich_formula:
            args.append("--enrich-formula")

        args.append(f"--page-batch-size={self.page_batch_size}")

        return args

    def to_yaml(self) -> str:
        """Export as YAML configuration."""
        return yaml.dump(self.model_dump(), default_flow_style=False)
```

### 5.3 Stream 5 Deliverables

- [ ] `DoclingRoutingEngine` implementation
- [ ] Routing rules from analysis document
- [ ] CLI argument generation
- [ ] YAML export capability
- [ ] Unit tests for all routing paths
- [ ] Integration tests with mock Docling

**Duration**: 5-7 days

---

## Stream 6: Classical Geometric Corrections (Weeks 3-4)

**Goal**: Implement non-ML geometric corrections

### 6.1 Border Removal

```python
# src/correction/border_removal.py

class BorderRemover:
    """Remove black/white borders from scanned documents."""

    def remove(self, image: np.ndarray) -> tuple[np.ndarray, BorderInfo]:
        """Detect and remove borders.

        Methods:
        1. Edge detection along image boundaries
        2. Contour analysis for document rectangle
        3. Morphological operations for cleanup
        """
        # Detect document contour
        contour = self._find_document_contour(image)

        # Crop to contour
        cropped = self._crop_to_contour(image, contour)

        return cropped, BorderInfo(
            original_size=image.shape[:2],
            cropped_size=cropped.shape[:2],
            borders_removed=True,
        )
```

### 6.2 Perspective Correction

```python
# src/correction/perspective_correction.py

class PerspectiveCorrector:
    """Correct perspective distortion from camera capture."""

    def correct(
        self,
        image: np.ndarray,
        warping_detection: WarpingDetection,
    ) -> tuple[np.ndarray, PerspectiveInfo]:
        """Apply perspective correction.

        Approach: Classical CV with optional ML enhancement
        1. Detect document corners (Hough + contour)
        2. Compute homography matrix
        3. Apply perspective warp
        """
        if not warping_detection.has_warping:
            return image, PerspectiveInfo(corrected=False)

        # Detect corners
        corners = self._detect_corners(image)

        # Compute and apply homography
        corrected = self._apply_homography(image, corners)

        return corrected, PerspectiveInfo(
            corrected=True,
            original_corners=corners,
            curvature_before=warping_detection.curvature_score,
        )
```

### 6.3 Stream 6 Deliverables

- [ ] `BorderRemover` implementation + tests
- [ ] `PerspectiveCorrector` implementation + tests
- [ ] Integration with correction pipeline
- [ ] Performance benchmarks

**Duration**: 4-5 days

---

## Stream 7: Pseudo-Labeling Pipeline (Weeks 5-6)

**Goal**: Use teacher model to label training data for student models

### 7.1 Labeling Pipeline

```python
# scripts/generate_multitask_labels.py

class MultiTaskLabeler:
    """Generate pseudo-labels using SigLIP2 teacher.

    IMPORTANT: Stores FULL softmax distributions, not just argmax.
    This enables:
    - Soft-label training (knowledge distillation with soft targets)
    - Uncertainty quantification (entropy of distribution)
    - Calibration analysis (confidence vs accuracy)
    - Active learning sample selection (high entropy = uncertain)
    """

    # Class mappings for human-readable labels
    SCRIPT_CLASSES = [
        "LATN", "CYRL", "GREK", "ARAB", "HEBR",
        "DEVA", "BENG", "TAML", "TELU",
        "HANS", "HANT", "JPAN", "KORE",
        "THAI", "TIBT",
        "INDIC_OTHER", "SE_ASIAN_OTHER", "OTHER", "UNKNOWN"
    ]
    SOURCE_CLASSES = ["scanned", "camera", "digital"]
    ORIENTATION_CLASSES = [0, 90, 180, 270]

    def __init__(self, teacher_path: str):
        self.teacher = SigLIP2MultiTaskTeacher.load(teacher_path)
        self.teacher.eval()

    def label_dataset(
        self,
        image_paths: list[str],
        tasks: list[str],
        store_distributions: bool = True,  # NEW: Store full softmax
    ) -> list[dict]:
        """Generate labels for all images.

        Args:
            image_paths: Paths to images to label
            tasks: Tasks to generate labels for
            store_distributions: If True, store full softmax distributions
                                 for soft-label training and uncertainty analysis
        """

        results = []
        for path in tqdm(image_paths):
            image = load_image(path)

            with torch.no_grad():
                outputs = self.teacher(image, tasks=tasks)

            # Compute softmax distributions for classification tasks
            script_probs = outputs["script"].softmax(-1)
            source_probs = outputs["document_source"].softmax(-1)
            orient_probs = outputs["orientation"].softmax(-1)

            labels = {
                "image_path": path,

                # === Script Detection ===
                "script_class": self.SCRIPT_CLASSES[script_probs.argmax().item()],
                "script_class_idx": script_probs.argmax().item(),
                "script_confidence": script_probs.max().item(),
                "script_entropy": self._entropy(script_probs).item(),

                # === Document Source ===
                "source_class": self.SOURCE_CLASSES[source_probs.argmax().item()],
                "source_class_idx": source_probs.argmax().item(),
                "source_confidence": source_probs.max().item(),

                # === Orientation ===
                "orientation_angle": self.ORIENTATION_CLASSES[orient_probs.argmax().item()],
                "orientation_class_idx": orient_probs.argmax().item(),
                "orientation_confidence": orient_probs.max().item(),

                # === Regression outputs (continuous 0-1) ===
                "shadow_score": outputs["shadows"][0].item(),
                "shadow_uncertainty": outputs["shadows"][1].item(),  # sigma
                "warping_score": outputs["warping"][0].item(),
                "warping_uncertainty": outputs["warping"][1].item(),  # sigma
            }

            # Store full distributions for soft-label training
            if store_distributions:
                labels["script_distribution"] = {
                    cls: prob.item()
                    for cls, prob in zip(self.SCRIPT_CLASSES, script_probs.squeeze())
                }
                labels["source_distribution"] = {
                    cls: prob.item()
                    for cls, prob in zip(self.SOURCE_CLASSES, source_probs.squeeze())
                }
                labels["orientation_distribution"] = {
                    str(angle): prob.item()
                    for angle, prob in zip(self.ORIENTATION_CLASSES, orient_probs.squeeze())
                }

            results.append(labels)

        return results

    def _entropy(self, probs: torch.Tensor) -> torch.Tensor:
        """Calculate entropy of probability distribution.

        High entropy = high uncertainty = good candidate for active learning.
        """
        return -torch.sum(probs * torch.log(probs + 1e-10), dim=-1)

    def export_for_training(
        self,
        results: list[dict],
        output_path: str,
        format: str = "parquet",  # parquet preferred for large datasets
    ):
        """Export labels for training.

        Parquet format preserves nested dicts (distributions) efficiently.
        """
        import pandas as pd

        df = pd.DataFrame(results)

        if format == "parquet":
            df.to_parquet(output_path, index=False)
        elif format == "json":
            df.to_json(output_path, orient="records", indent=2)
        else:
            raise ValueError(f"Unknown format: {format}")
```

### 7.2 Dataset Creation

| Target Dataset | Source | Teacher Labels | Manual Validation |
|----------------|--------|----------------|-------------------|
| Script Training | Unlabeled docs | Script class + confidence | 1% sample |
| Orientation Training | Unlabeled docs | Orientation class | 1% sample |
| Source Training | Unlabeled docs | Source class | 1% sample |

### 7.3 Stream 7 Deliverables

- [ ] `MultiTaskLabeler` implementation
- [ ] Labeling scripts for Modal
- [ ] Generated label files (JSON/Parquet)
- [ ] Manual validation report
- [ ] Training dataset manifests

**Duration**: 3-4 days

---

## Stream 8: Student Model Training (Weeks 7-8) - OPTIONAL

**Goal**: Distill teacher to mobile-deployable student

**Note**: This stream is only needed if mobile/edge deployment is required. For server deployment, the SigLIP2 teacher can be used directly.

### 8.1 MobileCLIP-2 Distillation

```python
# modal/train_mobileclip_student.py

class MobileCLIPDistillation:
    """Distill SigLIP2 teacher to MobileCLIP-2 S0 student."""

    def __init__(
        self,
        teacher_path: str,
        student_variant: str = "S0",  # S0, S2, or S4
    ):
        self.teacher = SigLIP2MultiTaskTeacher.load(teacher_path)
        self.student = MobileCLIP2.from_pretrained(f"apple/MobileCLIP2-{student_variant}")

        # Add task heads to student
        self.student_heads = nn.ModuleDict({
            "script": nn.Linear(768, 12),
            "document_source": nn.Linear(768, 3),
            "orientation": nn.Linear(768, 4),
        })

    def distillation_loss(
        self,
        student_logits: dict,
        teacher_logits: dict,
        targets: dict,
        temperature: float = 4.0,
        alpha: float = 0.7,
    ) -> torch.Tensor:
        """Combined distillation + task loss."""

        distill_loss = 0
        task_loss = 0

        for task in student_logits:
            # Soft targets from teacher
            soft_targets = F.softmax(teacher_logits[task] / temperature, dim=-1)
            soft_student = F.log_softmax(student_logits[task] / temperature, dim=-1)
            distill_loss += F.kl_div(soft_student, soft_targets, reduction="batchmean")

            # Hard targets
            task_loss += F.cross_entropy(student_logits[task], targets[task])

        return alpha * distill_loss * (temperature ** 2) + (1 - alpha) * task_loss
```

### 8.2 Cascade Strategy (if highest accuracy needed)

If direct S0 training doesn't meet accuracy targets:

```text
SigLIP2 Teacher → MobileCLIP-2 S4 → MobileCLIP-2 S0
     (86M)            (321M)            (11.4M)
```

### 8.3 Expected Performance

| Model | Params | Latency (iPhone 12) | Script Acc | Source Acc |
|-------|--------|---------------------|------------|------------|
| SigLIP2 Teacher | 86M | ~200ms | 95% | 97% |
| MobileCLIP-2 S4 | 321M | 19.6ms | 93% | 95% |
| MobileCLIP-2 S0 | 11.4M | **1.5ms** | 88% | 92% |

### 8.4 Stream 8 Deliverables (if executed)

- [ ] Distillation training script
- [ ] S4 intermediate model (if cascade)
- [ ] S0 student model
- [ ] ONNX export
- [ ] TorchScript export
- [ ] Accuracy benchmarks

**Duration**: 5-7 days

---

## Stream 9: End-to-End Integration (Week 8-9)

**Goal**: Complete pipeline integration and verification

### 9.1 Integration Points

```python
# src/pipeline/enhanced_pipeline.py

class EnhancedDocumentPipeline:
    """Full pipeline with all new detection capabilities.

    CRITICAL PIPELINE ORDERING (see Stream 2 documentation):
    1. Orientation detection/correction (FIRST!)
    2. Blank page detection (early exit)
    3. Geometric corrections (border, perspective)
    4. Text gate → branch to appropriate detection
    5. Script, IQA, layout detection
    6. Aggregation and routing
    """

    def __init__(self):
        # === PHASE 1: Pre-processing (run FIRST) ===
        self.orientation_detector = OrientationDetector()  # CRITICAL: Must be first!
        self.blank_page_detector = BlankPageDetector()

        # === PHASE 2: Geometric Corrections ===
        self.border_remover = BorderRemover()
        self.perspective_corrector = PerspectiveCorrector()

        # === PHASE 3: Detection Components ===
        # Existing components
        self.text_gate = TextGate()
        self.iqa_classical = ClassicalIQA()
        self.iqa_ml = MLIQADetector()
        self.layout_detector = DocLayoutYOLO()

        # New detection components
        self.text_layer_analyzer = TextLayerAnalyzer()
        self.script_detector = ScriptDetector()  # Heuristic or ML
        self.shadow_detector = ShadowDetector()
        self.warping_detector = WarpingDetector()
        self.source_classifier = DocumentSourceClassifier()
        self.code_detector = CodeDetector()
        self.table_analyzer = TableComplexityAnalyzer()
        self.handwriting_detector = HandwritingDetector()  # NEW: For VLM escalation

        # === PHASE 4: Classification & Routing ===
        self.severity_classifier = DegradationSeverityClassifier()
        self.docling_router = DoclingRoutingEngine()

    def process(self, input_path: str) -> DocumentMetadata:
        """Process document through enhanced pipeline.

        CRITICAL: Pipeline order matters! Orientation must be corrected
        before any other detection to avoid invalid results.
        """

        # ══════════════════════════════════════════════════════════════
        # PHASE 1: Pre-flight Analysis (document-level)
        # ══════════════════════════════════════════════════════════════
        dpi_info = self.analyze_dpi(input_path)
        text_layer_quality = self.text_layer_analyzer.analyze(input_path)
        pdf_type = self.classify_pdf_type(input_path)

        # Load pages for per-page processing
        images = self.load_pages(input_path)

        # ══════════════════════════════════════════════════════════════
        # PHASE 2: Per-Page Processing (ORDER IS CRITICAL!)
        # ══════════════════════════════════════════════════════════════
        page_results = []
        for page_idx, image in enumerate(images):

            # ─────────────────────────────────────────────────────────
            # STEP 1: ORIENTATION DETECTION & CORRECTION (MUST BE FIRST!)
            # Running any detection on rotated images produces invalid results
            # ─────────────────────────────────────────────────────────
            orientation = self.orientation_detector.detect(image)
            if orientation.needs_correction:
                image = self._apply_orientation_correction(image, orientation)
                orientation.correction_applied = True

            # ─────────────────────────────────────────────────────────
            # STEP 2: BLANK PAGE DETECTION (early exit)
            # Skip all processing for blank pages
            # ─────────────────────────────────────────────────────────
            blank_check = self.blank_page_detector.detect(image)
            if blank_check.is_blank:
                page_results.append(PageResult(
                    page_index=page_idx,
                    is_blank=True,
                    orientation=orientation,
                    skip_reason="blank_page",
                ))
                continue  # Skip to next page

            # ─────────────────────────────────────────────────────────
            # STEP 3: GEOMETRIC CORRECTIONS (before detection)
            # Apply corrections on properly-oriented, non-blank pages
            # ─────────────────────────────────────────────────────────
            # 3a: Warping detection (needed for perspective correction)
            warping = self.warping_detector.detect(image)

            # 3b: Border removal
            image, border_info = self.border_remover.remove(image)

            # 3c: Perspective correction (if warping detected)
            perspective_info = None
            if warping.has_warping and warping.warping_score < 0.75:
                # Only correct moderate warping; extreme warping (>25°) → VLM
                image, perspective_info = self.perspective_corrector.correct(
                    image, warping
                )

            # ─────────────────────────────────────────────────────────
            # STEP 4: CORE DETECTION (on corrected image)
            # Now safe to run detection on properly oriented/corrected image
            # ─────────────────────────────────────────────────────────
            text_detected = self.text_gate.detect(image)
            iqa_scores = self.iqa_ml.detect(image)
            layout = self.layout_detector.detect(image)

            # Script detection (on corrected, properly-oriented image)
            script = self.script_detector.detect(image)
            shadows = self.shadow_detector.detect(image)
            source = self.source_classifier.classify(image)
            code = self.code_detector.detect(image, layout)
            table_complexity = self.table_analyzer.analyze_tables(layout, image)
            handwriting = self.handwriting_detector.detect(image)

            page_results.append(PageResult(
                page_index=page_idx,
                is_blank=False,
                orientation=orientation,
                border_info=border_info,
                perspective_info=perspective_info,
                warping=warping,
                text_detected=text_detected,
                iqa_scores=iqa_scores,
                layout=layout,
                script=script,
                shadows=shadows,
                source=source,
                code=code,
                table_complexity=table_complexity,
                handwriting=handwriting,
            ))

        # ══════════════════════════════════════════════════════════════
        # PHASE 3: Aggregation
        # ══════════════════════════════════════════════════════════════
        metadata = self.aggregate_results(page_results)

        # ══════════════════════════════════════════════════════════════
        # PHASE 4: Severity Classification & Routing
        # ══════════════════════════════════════════════════════════════
        metadata.degradation_severity = self.severity_classifier.classify(
            metadata.document_source,
            metadata.dqs,
            any(p.has_shadows for p in metadata.page_layout_summary),
            any(p.has_warping for p in metadata.page_layout_summary),
        )

        # Docling routing (includes VLM escalation logic)
        metadata.docling_params = self.docling_router.route(metadata)

        return metadata
```

### 9.2 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| E2E Latency (GPU) | <200ms/page | All new detectors |
| E2E Latency (CPU) | <600ms/page | Fallback path |
| Script Detection | >90% | With ML teacher |
| Document Source | >92% | With ML or heuristic |
| DoclingRouter Coverage | 100% routes | All paths tested |

### 9.3 Test Suite

```python
# tests/e2e/test_enhanced_pipeline.py

class TestEnhancedPipeline:

    def test_born_digital_skips_ocr(self):
        """Born digital with good text layer should skip OCR."""
        result = pipeline.process("born_digital.pdf")
        assert result.docling_params.ocr_enabled == False

    def test_camera_captured_routes_to_vlm(self):
        """Camera-captured with warping should escalate to VLM."""
        result = pipeline.process("camera_document.jpg")
        assert result.docling_params.pipeline == "vlm"

    def test_cjk_reduces_batch_size(self):
        """CJK documents should have reduced batch size."""
        result = pipeline.process("chinese_document.pdf")
        assert result.docling_params.page_batch_size == 2

    def test_code_enables_enrichment(self):
        """Documents with code should enable code enrichment."""
        result = pipeline.process("code_documentation.pdf")
        assert result.docling_params.enrich_code == True
```

### 9.4 Stream 9 Deliverables

- [ ] Enhanced pipeline implementation
- [ ] Integration test suite
- [ ] Performance benchmarks
- [ ] Documentation updates
- [ ] API documentation

**Duration**: 5-7 days

---

## Part 3: Timeline Summary

### Gantt-Style View

```text
Week 1:  [S1: Schema═══════] [S2: Heuristics═══════════════════════
Week 2:  ══════════════════] [S3: Benchmark═══]

Week 3:  [S4: Teacher Training═════════════════════════════════════
Week 3:  [S5: DoclingRouter════════════════════════════════════════
Week 3:  [S6: Classical Corrections════════]

Week 4:  ══════════════════════════════════════════════════════════
         ══════════════════════════════════════════════════════════
         ══════════════════════════════]

Week 5:  ══════════════════════════════════════════════════════════
         ══════════════════════════════════════════════════════════
         [S7: Pseudo-Labeling══════════════════]

Week 6:  ══════════════════════════════════════]
         ══════════════════════════════════════════════════════════]
         ══════════════════════════════════════]

Week 7:  [S8: Student Training (OPTIONAL)══════════════════════════
         [S9: E2E Integration══════════════════════════════════════

Week 8:  ══════════════════════════════════════════════════════════]
         ══════════════════════════════════════════════════════════]

Week 9:  [Buffer / Documentation / Optimization═══════════════════]
```

### Resource Allocation

| Week | GPU (Modal) | Local Dev | Parallel Streams |
|------|-------------|-----------|------------------|
| 1 | - | Schema + Heuristics | S1, S2 |
| 2 | - | Benchmarking | S2, S3 |
| 3 | A10G (Teacher) | Router + Corrections | S4, S5, S6 |
| 4 | A10G (Teacher) | Router + Corrections | S4, S5, S6 |
| 5 | A10G (Teacher) | Pseudo-labeling | S4, S5, S7 |
| 6 | - | Router + Integration | S5, S7, S9 |
| 7 | T4 (Student) | E2E Testing | S8, S9 |
| 8 | T4 (Student) | E2E Testing | S8, S9 |
| 9 | - | Buffer | - |

---

## Part 4: Decision Points

### Decision 1: ML Script Detection

**When**: End of Week 2 (after Stream 3 benchmarking)

**Criteria**: Heuristic script detection accuracy on MLT-2019

| Result | Action |
|--------|--------|
| ≥80% accuracy | Use heuristic, skip ML |
| 70-80% accuracy | Train SigLIP2 script head |
| <70% accuracy | Train SigLIP2 + cascade to MobileCLIP |

### Decision 2: Mobile Deployment

**When**: Week 4 (before Stream 8 starts)

**Question**: Is mobile/edge deployment required?

| Answer | Action |
|--------|--------|
| Yes | Execute Stream 8 (MobileCLIP distillation) |
| No | Use SigLIP2 teacher directly in production |

### Decision 3: Perspective Correction Approach

**When**: Week 3 (during Stream 6)

**Criteria**: Classical CV perspective correction accuracy

| Result | Action |
|--------|--------|
| ≥85% accuracy | Use classical CV |
| <85% accuracy | Evaluate ML perspective model (MobileViT-v2) |

---

## Part 5: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Script heuristic <70% accuracy | Medium | High | Early ML fallback, use MLT dataset |
| Teacher training takes >7 days | Low | Medium | Background Modal runs, early start |
| Docling CLI changes | Low | Medium | Version-pin, abstract interface |
| Performance regression | Medium | High | Strict latency gates, profiling |
| CJK script accuracy low | Medium | High | Dedicated CJK training samples |

---

## Part 6: Success Criteria

### Functional Requirements

| Requirement | Target | Validation |
|-------------|--------|------------|
| Script detection coverage | 12 scripts | Unit tests |
| Script detection accuracy | ≥90% (ML), ≥80% (heuristic) | MLT-2019 benchmark |
| Document source accuracy | ≥90% | SmartDoc-QA benchmark |
| DoclingRouter coverage | 100% routes | Integration tests |
| Text layer quality correlation | ≥85% with OCR skip | DIQA-5000 |

### Performance Requirements

| Metric | Target | Validation |
|--------|--------|------------|
| E2E latency (GPU) | <200ms/page | E2E benchmarks |
| Script detection latency | <20ms | Component benchmarks |
| DoclingRouter latency | <5ms | Component benchmarks |
| Memory usage | <4GB | Profiling |

### Quality Requirements

| Metric | Target | Validation |
|--------|--------|------------|
| Test coverage | ≥80% | Coverage report |
| Documentation | Complete | Review |
| Code quality | Ruff + BasedPyright clean | CI |

---

## Appendix A: Comparison with Original Plan

| Aspect | Original Plan | Restructured Plan |
|--------|---------------|-------------------|
| **Structure** | Phase 10A/10B/10C/11 | 9 parallel streams |
| **Duration** | 22 days + deferred Phase 11 | 7-9 weeks |
| **Script Detection** | Deferred (Phase 11) | Week 2-5 (Stream 4) |
| **Model Architecture** | MobileCLIP-2 (orientation + script) | SigLIP2 multi-task teacher |
| **Mobile Deployment** | Required | Optional (Stream 8) |
| **Heuristic Baseline** | Not explicitly planned | Stream 2, with benchmarks |
| **DoclingRouter** | 7 days | 5-7 days + parallel |
| **Training Data** | Unclear | Teacher pseudo-labeling |

---

## Appendix B: File Structure

```text
config/
├── script_ml_classes.yaml              # NEW: ISO 15924 → ML class mapping
└── script_routing.yaml                 # NEW: Script → OCR engine routing

src/image_preprocessing_detector/
├── schema_utils/
│   ├── iso_language_script.py          # EXISTING: ISO 15924/639 enums
│   ├── script_ml_mapping.py            # NEW: Config-driven ML class mapping
│   └── script_router.py                # NEW: Config-driven OCR routing
├── classification/
│   ├── document_source_classifier.py   # NEW (uses existing CaptureMethod enum)
│   └── text_layer_analyzer.py          # NEW
├── detection/
│   ├── orientation_detector.py         # EXISTING - CRITICAL: Must run FIRST!
│   ├── blank_page_detector.py          # NEW: Early exit for blank pages
│   ├── handwriting_detector.py         # NEW: VLM escalation trigger
│   ├── script_detector.py              # NEW (three-tier aware)
│   ├── shadow_detector.py              # NEW
│   ├── warping_detector.py             # NEW
│   ├── code_detector.py                # NEW
│   └── table_complexity.py             # NEW
├── correction/
│   ├── border_removal.py               # NEW
│   └── perspective_correction.py       # NEW
├── routing/
│   ├── recommendation_engine.py        # EXISTING
│   ├── docling_router.py               # NEW (uses ScriptRouter)
│   └── psm_recommender.py              # NEW
├── models/
│   └── siglip2_multitask.py            # NEW
└── pipeline/
    └── enhanced_pipeline.py            # NEW

modal/
├── train_siglip2_multitask.py          # NEW
├── train_mobileclip_student.py         # NEW (optional)
└── generate_multitask_labels.py        # NEW

scripts/
├── benchmark_heuristics.py             # NEW
└── validate_routing.py                 # NEW
```

---

## Appendix C: Key Design Decisions

### C.1 Three-Tier Script Architecture

| Decision | Rationale |
|----------|-----------|
| Store full ISO 15924 | Don't know which scripts need which engines until testing |
| Config-driven ML mapping | Can split/merge classes as training data grows |
| Config-driven routing | Update engine assignments without code changes |
| Preserve source labels | Debugging and traceability |

### C.2 Reuse vs New

| Need | Decision | Reason |
|------|----------|--------|
| Document source | Reuse `CaptureMethod` | Already has 7 values including FAX |
| Script codes | Reuse `ISO15924Script` | Already has 30+ scripts |
| Script families | Reuse `ScriptFamily` | Already has routing-friendly groups |
| Degradation severity | New literal type | Simple "simple"/"complex" sufficient |

### C.3 Continuous vs Binary Labels

**All detection scores MUST be continuous (0-1 floats):**

- `shadow_score: float` not `has_shadows: bool` only
- `warping_score: float` not `has_warping: bool` only
- `code_confidence: float` not `has_code: bool` only
- `script_probabilities: dict[str, float]` not `detected_script: str` only

Binary flags retained for convenience but continuous scores required for:

- Gradient-based training
- Confidence-weighted routing
- Calibration and uncertainty quantification

---

**End of Document**
