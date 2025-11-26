---
schema_type: common
title: "ADR-028: Document Quality Score (DQS) for Intelligent Pipeline Routing"
description: "Decision to implement a quantitative Document Quality Score for dynamic routing between OCR-based and Vision-based RAG pipelines"
tags:
  - adr
  - architecture
  - routing
  - scoring
  - pipeline_selection
  - production
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the decision to implement a two-axis quality scoring system that enables intelligent routing of documents to the optimal processing pipeline based on degradation and structural complexity."
---

**Status**: ✅ **Accepted**
**Date**: 2025-11-11 (Phase 4 Production Planning)
**Deciders**: Byron Williams
**Related**: ADR-0007 (Hybrid IQA), ADR-0008 (Multi-Stage Pipeline), ADR-0020 (CPU-First Deployment), project_mandate.md

---

## Context

### The Pipeline Selection Problem

Production RAG systems face a critical architectural trade-off: there is **no single "best" pipeline** for all documents. Research demonstrates two competing approaches with fundamentally different failure modes:

**1. OCR-based Pipelines (Nougat, LayoutLM, Marker)**

- **Strengths**: Excellent at understanding complex structures (tables, formulas, multi-column layouts)
- **Weaknesses**: Brittle; fail catastrophically on degraded images (blur, noise, low contrast)
- **Use Case**: Clean, structurally complex documents

**2. Vision-based Pipelines (ColPali, VLM-based embedders)**

- **Strengths**: Robust to image degradation; can retrieve from blurry or noisy scans
- **Weaknesses**: May struggle with novel layouts and complex text-heavy documents
- **Use Case**: Degraded but structurally simple documents

This trade-off is documented in recent research ("Lost in OCR Translation?" study) and represents a **strategic impasse**: choosing one architecture sacrifices performance on the other document type.

### Current System Limitations

The current Image Preprocessing Detector (Phase 0-1) performs detection and correction but **lacks intelligent routing logic**:

- Detects issues: ✅ (blur, skew, noise, layout complexity)
- Corrects issues: ✅ (deskew, upscale, CLAHE)
- Routes documents: ❌ (missing)

Without routing, downstream systems must choose:

- **Single Pipeline**: Apply same processing to all docs (suboptimal)
- **Manual Triage**: Human selects pipeline (doesn't scale)
- **Random Assignment**: Process failure, retry different pipeline (inefficient)

### Requirements

A production-grade system needs:

1. **Quantitative Assessment**: Measure document quality along multiple dimensions
2. **Routing Logic**: Map quality metrics to optimal pipeline
3. **Explainability**: Provide reasoning for routing decision (audit trail)
4. **Configurability**: Allow threshold tuning for different use cases
5. **Extensibility**: Support adding new pipelines and quality dimensions

---

## Decision

**Implement a Document Quality Score (DQS) framework that quantifies document quality along two orthogonal axes and uses these scores to dynamically route documents to the optimal processing pipeline.**

### Two-Axis Scoring Model

**Axis 1: Degradation Score (0.0 - 1.0)**

- **Measures**: Physical image quality degradation
- **Components**:
  - Blur score (Laplacian variance)
  - Noise score (connected component analysis)
  - Contrast score (histogram analysis)
  - Skew angle (document rotation)
  - Resolution (DPI)
- **Scale**: 0.0 = severe degradation, 1.0 = pristine quality

**Axis 2: Structural Complexity Score (0.0 - 1.0)**

- **Measures**: Layout and content complexity
- **Components**:
  - Multi-column detection (text block analysis)
  - Table count and complexity (row × column count)
  - Formula count (mathematical notation)
  - Figure count and captions
  - Mixed-script detection (Latin + Non-Latin)
- **Scale**: 0.0 = simple single-column, 1.0 = highly complex layout

### Routing Decision Matrix

```text
                    LOW STRUCTURAL          HIGH STRUCTURAL
                    COMPLEXITY              COMPLEXITY
                    (Simple Layout)         (Tables, Multi-col)
                    ─────────────────────────────────────────
HIGH DEGRADATION │  Vision-based (VLM)  │  Vision-based (VLM)  │
(Blurry, Noisy)  │  + Post-OCR cleanup  │  + Structure hints   │
                 │                       │                      │
─────────────────┼──────────────────────┼──────────────────────┤
                 │                       │                      │
LOW DEGRADATION  │  Fast OCR            │  Advanced OCR        │
(Clean, Sharp)   │  (Tesseract)         │  (Nougat/Marker)     │
                 │                       │  + Layout Parser     │
                 └───────────────────────┴──────────────────────┘

Quadrant 1 (High Deg, Low Struct):   Vision → Simple Chunking
Quadrant 2 (High Deg, High Struct):  Vision → Structure-aware (challenging!)
Quadrant 3 (Low Deg, Low Struct):    Fast OCR → Standard RAG
Quadrant 4 (Low Deg, High Struct):   Advanced OCR → Layout-preserving RAG
```text

### Implementation

**Schema Addition** (src/image_preprocessing_detector/schema.py):

```python
from typing import Literal
from pydantic import BaseModel, Field

class DocumentQualityScore(BaseModel):
    """Document Quality Score for pipeline routing."""

    degradation_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Image quality score (0=severe degradation, 1=pristine)"
    )

    structural_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Layout complexity score (0=simple, 1=complex)"
    )

    component_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Individual quality component scores"
    )

    routing_recommendation: Literal[
        "vision_simple",      # Quadrant 1: Vision + Simple
        "vision_structured",  # Quadrant 2: Vision + Structure
        "ocr_fast",           # Quadrant 3: Fast OCR
        "ocr_advanced"        # Quadrant 4: Advanced OCR
    ] = Field(
        ...,
        description="Recommended processing pipeline"
    )

    routing_confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence in routing decision"
    )

    routing_rationale: str = Field(
        ...,
        description="Human-readable explanation of routing decision"
    )


class DocumentMetadata(BaseModel):
    """Extended with DQS field."""

    # ... existing fields ...

    quality_score: Optional[DocumentQualityScore] = Field(
        None,
        description="Document quality score and routing recommendation"
    )
```text

**DQS Calculator** (src/image_preprocessing_detector/scoring/dqs_calculator.py):

```python
class DQSCalculator:
    """Calculate Document Quality Score for routing decisions."""

    def __init__(self, config: Settings):
        self.config = config

    def calculate_degradation_score(
        self,
        page_metadata: PageMetadata
    ) -> float:
        """
        Calculate degradation score from component scores.

        Components (weighted average):
        - Blur (40%): Laplacian variance normalized
        - Noise (20%): Connected component analysis
        - Contrast (20%): Histogram spread
        - Skew (10%): Angle severity
        - Resolution (10%): DPI adequacy
        """
        # Normalize blur score (higher variance = sharper)
        blur_component = self._normalize_blur(
            page_metadata.blur_score
        )

        # Normalize noise score (lower noise = cleaner)
        noise_component = self._normalize_noise(
            page_metadata.noise_score
        )

        # Normalize contrast score
        contrast_component = self._normalize_contrast(
            page_metadata.contrast_score
        )

        # Normalize skew (lower angle = better)
        skew_component = self._normalize_skew(
            page_metadata.skew_angle
        )

        # Normalize resolution (higher DPI = better, up to 300)
        resolution_component = self._normalize_dpi(
            page_metadata.original_dpi or 300
        )

        # Weighted average
        degradation_score = (
            0.40 * blur_component +
            0.20 * noise_component +
            0.20 * contrast_component +
            0.10 * skew_component +
            0.10 * resolution_component
        )

        return degradation_score

    def calculate_structural_score(
        self,
        page_metadata: PageMetadata
    ) -> float:
        """
        Calculate structural complexity score.

        Components (additive with saturation):
        - Multi-column: +0.3 if detected
        - Tables: +0.1 per table (max +0.4)
        - Formulas: +0.1 per formula (max +0.3)
        - Figures: +0.05 per figure (max +0.2)
        - Mixed scripts: +0.2 if detected

        Saturates at 1.0 (max complexity)
        """
        structural_score = 0.0

        # Multi-column detection
        if self._is_multi_column(page_metadata.layout_elements):
            structural_score += 0.3

        # Count tables (saturate at 4)
        table_count = self._count_elements(
            page_metadata.layout_elements, "Table"
        )
        structural_score += min(0.4, table_count * 0.1)

        # Count formulas (saturate at 3)
        formula_count = self._count_elements(
            page_metadata.layout_elements, "Formula"
        )
        structural_score += min(0.3, formula_count * 0.1)

        # Count figures (saturate at 4)
        figure_count = self._count_elements(
            page_metadata.layout_elements, "Picture"
        )
        structural_score += min(0.2, figure_count * 0.05)

        # Mixed scripts
        if page_metadata.has_non_latin:
            structural_score += 0.2

        return min(1.0, structural_score)  # Cap at 1.0

    def route_document(
        self,
        degradation_score: float,
        structural_score: float
    ) -> Tuple[str, float, str]:
        """
        Determine routing recommendation from scores.

        Returns:
            (routing_recommendation, confidence, rationale)
        """
        # Thresholds (configurable)
        deg_threshold = self.config.dqs_degradation_threshold  # 0.6
        struct_threshold = self.config.dqs_structural_threshold  # 0.5

        # Decision matrix
        if degradation_score < deg_threshold:
            # High degradation
            if structural_score < struct_threshold:
                routing = "vision_simple"
                confidence = self._calculate_confidence(
                    degradation_score, structural_score,
                    expect_low_deg=False, expect_low_struct=True
                )
                rationale = (
                    f"High degradation (score={degradation_score:.2f}) "
                    f"with simple layout (score={structural_score:.2f}). "
                    "Routing to vision-based pipeline with simple chunking."
                )
            else:
                routing = "vision_structured"
                confidence = self._calculate_confidence(
                    degradation_score, structural_score,
                    expect_low_deg=False, expect_low_struct=False
                )
                rationale = (
                    f"High degradation (score={degradation_score:.2f}) "
                    f"with complex layout (score={structural_score:.2f}). "
                    "Routing to vision-based pipeline with structure hints. "
                    "NOTE: This is challenging - consider manual review."
                )
        else:
            # Low degradation
            if structural_score < struct_threshold:
                routing = "ocr_fast"
                confidence = self._calculate_confidence(
                    degradation_score, structural_score,
                    expect_low_deg=True, expect_low_struct=True
                )
                rationale = (
                    f"Low degradation (score={degradation_score:.2f}) "
                    f"with simple layout (score={structural_score:.2f}). "
                    "Routing to fast OCR (Tesseract) with standard RAG chunking."
                )
            else:
                routing = "ocr_advanced"
                confidence = self._calculate_confidence(
                    degradation_score, structural_score,
                    expect_low_deg=True, expect_low_struct=False
                )
                rationale = (
                    f"Low degradation (score={degradation_score:.2f}) "
                    f"with complex layout (score={structural_score:.2f}). "
                    "Routing to advanced OCR (Nougat/Marker) with layout-preserving RAG."
                )

        return routing, confidence, rationale
```text

**Configuration** (src/image_preprocessing_detector/core/config.py):

```python
class Settings(BaseSettings):
    """Extended with DQS settings."""

    # ... existing settings ...

    # DQS Configuration
    enable_dqs: bool = Field(
        default=True,
        description="Enable Document Quality Score calculation"
    )

    dqs_degradation_threshold: float = Field(
        default=0.6,
        ge=0.0, le=1.0,
        description="Threshold for degradation score (below = high degradation)"
    )

    dqs_structural_threshold: float = Field(
        default=0.5,
        ge=0.0, le=1.0,
        description="Threshold for structural score (above = complex)"
    )

    # Component weights (degradation score)
    dqs_blur_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    dqs_noise_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    dqs_contrast_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    dqs_skew_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    dqs_resolution_weight: float = Field(default=0.1, ge=0.0, le=1.0)
```text

---

## Consequences

### Positive

1. **Intelligent Routing**: Documents automatically routed to optimal pipeline
   - **Impact**: Maximize accuracy by matching document characteristics to pipeline strengths
   - **Metric**: Expected 15-25% accuracy improvement on mixed-quality corpora

2. **Explainable Decisions**: Every routing includes human-readable rationale
   - **Impact**: Users can audit and understand why a pipeline was selected
   - **Example**: "High degradation (0.43) with complex layout (0.78) → vision_structured"

3. **Configurability**: Thresholds tunable for different use cases
   - **Impact**: Adjust routing sensitivity for conservative (high accuracy) vs. aggressive (high speed) modes
   - **Configuration**: `dqs_degradation_threshold`, `dqs_structural_threshold`

4. **Quantitative Monitoring**: DQS provides production metrics
   - **Metrics to Track**:
     - Distribution of documents across quadrants
     - Correlation between DQS and downstream RAG accuracy
     - Pipeline utilization (% using vision vs. OCR)
   - **Alert**: Flag documents in "vision_structured" (Quadrant 2) for manual review

5. **Future-Proof Architecture**: Easy to add new pipelines
   - **Examples**:
     - Add "hybrid" routing (OCR for text + Vision for images)
     - Add "specialist" routing (HTR for handwriting, Math OCR for formulas)

6. **Research Foundation**: Provides data for pipeline optimization
   - **A/B Testing**: Compare DQS-routed vs. random assignment
   - **Model Training**: Use DQS as training labels for meta-routing model

### Negative

1. **Computational Overhead**: DQS adds latency
   - **Impact**: +10-20ms per page (scoring calculation)
   - **Mitigation**: Cache scores, compute during ingestion phase
   - **Acceptable**: <15% of total pipeline latency

2. **Maintenance Burden**: Thresholds require tuning
   - **Impact**: Initial calibration needed on validation set
   - **Mitigation**: Provide default thresholds from research
   - **Ongoing**: Monthly review of routing accuracy

3. **Quadrant 2 Challenge**: High degradation + high structure is hard
   - **Issue**: Both Vision and OCR struggle with complex degraded docs
   - **Mitigation**: Flag for manual review, apply best-effort routing
   - **Long-term**: Research specialized pipelines for this case

4. **Dependency on Upstream Quality**: DQS only as good as detectors
   - **Issue**: Inaccurate blur/noise scores → wrong routing
   - **Mitigation**: Validate detector accuracy (Phase 1-2)
   - **Monitoring**: Track correlation between DQS and actual pipeline performance

### Neutral

1. **JSON Schema Extension**: Adds `quality_score` field to DocumentMetadata
2. **Configuration Expansion**: 7 new settings for DQS tuning

---

## Alternatives Considered

### Alternative 1: Rule-Based Routing (No Scoring)

**Description**: Hard-coded rules (e.g., "if blur > X, use Vision")

**Pros**:

- Simple to implement
- No overhead from score calculation
- Transparent decision logic

**Cons**:

- Brittle: Fails when multiple issues interact (blur + tables)
- Not extensible: Adding new pipelines requires code changes
- No explainability: Just "rule matched" not "score was X"

**Rejected**: Too simplistic for production complexity

---

### Alternative 2: ML-Based Meta-Routing

**Description**: Train classifier to predict optimal pipeline

**Pros**:

- Can learn complex interactions between quality dimensions
- Potentially higher accuracy than rule-based
- Adapts to production data

**Cons**:

- Requires labeled training data (which pipeline is "best" per doc)
- Black box: Hard to explain routing decision
- Overfitting risk: May not generalize
- Overhead: Model inference latency

**Deferred**: Consider for Phase 5 after collecting production data

---

### Alternative 3: Single Composite Score

**Description**: Combine all factors into one 0-1 score

**Pros**:

- Simple to understand ("quality = 0.73")
- Easy to threshold (e.g., > 0.5 → OCR)

**Cons**:

- Loses critical information: Can't distinguish degradation from complexity
- Poor routing: Document with low degradation but high structure would route same as high degradation, low structure
- Not aligned with pipeline trade-off (Vision vs. OCR axes)

**Rejected**: Two-axis model matches problem structure

---

### Alternative 4: Always Process Both Pipelines

**Description**: Run both Vision and OCR, use best result

**Pros**:

- Guaranteed optimal result (by definition)
- No routing errors

**Cons**:

- 2× computational cost (prohibitive at scale)
- 2× latency (unacceptable for real-time)
- How to choose "best" result? Requires meta-scoring anyway

**Rejected**: Not scalable for production

---

## Implementation Details

### Phase Integration

**Phase 1-3** (Current): Build foundation

- ✅ Phase 1: Detect degradation issues (blur, noise, skew)
- ✅ Phase 1B: DPI detection and upscaling
- ✅ Phase 2: ML-based IQA for accurate scoring
- ✅ Phase 3: Layout detection for structural scoring

**Phase 4** (Production - Implement DQS):

- Week 17: Implement DQSCalculator class
- Week 18: Add routing logic and schema extension
- Week 19: Calibrate thresholds on validation set
- Week 20: Deploy with monitoring

**Phase 5** (Optimization):

- Collect production routing data
- Tune thresholds based on downstream RAG accuracy
- Evaluate ML-based meta-routing

### Threshold Calibration Process

**Step 1: Create Ground Truth** (Manual annotation)

- Sample 500 documents from production corpus
- Manually classify optimal pipeline per document
- Annotate as: "vision_simple", "vision_structured", "ocr_fast", "ocr_advanced"

**Step 2: Compute DQS on Ground Truth**

- Run DQSCalculator on all 500 documents
- Generate (degradation_score, structural_score) per document

**Step 3: Optimize Thresholds**

- Grid search over threshold pairs: degradation ∈ [0.3, 0.4, ..., 0.8], structural ∈ [0.3, 0.4, ..., 0.8]
- Metric: Routing accuracy (% documents routed to annotated optimal pipeline)
- Target: > 85% routing accuracy

**Step 4: Validate**

- Test on held-out 100 documents
- Measure downstream RAG accuracy for DQS-routed vs. random assignment
- Expected improvement: 15-25%

### Monitoring Metrics

**Deployment Metrics** (Prometheus/Grafana):

```yaml
# Document distribution across quadrants
dqs_quadrant_count{quadrant="vision_simple"} 1234
dqs_quadrant_count{quadrant="vision_structured"} 56
dqs_quadrant_count{quadrant="ocr_fast"} 3456
dqs_quadrant_count{quadrant="ocr_advanced"} 789

# Score distributions (histograms)
dqs_degradation_score_bucket{le="0.3"} 123
dqs_degradation_score_bucket{le="0.6"} 456
dqs_structural_score_bucket{le="0.5"} 678

# Routing confidence
dqs_routing_confidence_avg 0.87
dqs_routing_confidence_p50 0.92
dqs_routing_confidence_p95 0.65

# Problematic cases (Quadrant 2: high deg + high struct)
dqs_challenging_docs_count 56
dqs_challenging_docs_percent 2.1
```text

**Quality Metrics** (Post-processing validation):

```yaml
# Downstream RAG accuracy by quadrant
rag_accuracy_by_quadrant{quadrant="vision_simple"} 0.89
rag_accuracy_by_quadrant{quadrant="ocr_advanced"} 0.94

# Pipeline utilization
pipeline_usage_percent{pipeline="vision"} 35
pipeline_usage_percent{pipeline="ocr"} 65
```text

### Alerts

**Critical**:

- `dqs_challenging_docs_percent > 10%` → Many Quadrant 2 docs, review corpus quality
- `dqs_routing_confidence_avg < 0.7` → Low confidence, review thresholds

**Warning**:

- `dqs_quadrant_imbalance > 80%` → 80%+ docs in one quadrant, not getting value from routing
- `rag_accuracy_by_quadrant < 0.8` → Specific quadrant performing poorly, review pipeline

---

## Migration Path

**Phase 4 Week 17**: Schema and calculator implementation
**Phase 4 Week 18**: Routing logic integration
**Phase 4 Week 19**: Threshold calibration
**Phase 4 Week 20**: Production deployment with feature flag

**Feature Flag**:

```python
if settings.enable_dqs:
    quality_score = dqs_calculator.calculate(page_metadata)
    routing = quality_score.routing_recommendation
else:
    routing = "ocr_fast"  # Default fallback
```text

**Rollout Strategy**:

1. Week 20: Deploy with `enable_dqs=false` (shadow mode: calculate but don't route)
2. Week 21: Enable for 10% traffic (A/B test)
3. Week 22: Enable for 50% traffic
4. Week 23: Enable for 100% traffic if metrics positive

---

## Validation

### Unit Tests

```python
def test_dqs_quadrant_1():
    """High degradation + simple layout → vision_simple."""
    page = PageMetadata(
        blur_score=0.2,  # Low (blurry)
        noise_score=0.6,  # High (noisy)
        contrast_score=0.4,
        skew_angle=1.2,
        original_dpi=150,
        layout_elements=[
            DocumentElement(class_label="Text", ...)
        ]
    )
    dqs = calculator.calculate(page)
    assert dqs.degradation_score < 0.6  # High degradation
    assert dqs.structural_score < 0.5   # Low complexity
    assert dqs.routing_recommendation == "vision_simple"

def test_dqs_quadrant_4():
    """Low degradation + complex layout → ocr_advanced."""
    page = PageMetadata(
        blur_score=0.9,  # High (sharp)
        noise_score=0.1,  # Low (clean)
        contrast_score=0.8,
        skew_angle=0.3,
        original_dpi=300,
        layout_elements=[
            DocumentElement(class_label="Text", ...),
            DocumentElement(class_label="Table", ...),
            DocumentElement(class_label="Formula", ...)
        ]
    )
    dqs = calculator.calculate(page)
    assert dqs.degradation_score >= 0.6  # Low degradation
    assert dqs.structural_score >= 0.5   # High complexity
    assert dqs.routing_recommendation == "ocr_advanced"
```text

### Integration Tests

**Test: End-to-End Routing**

- Process 10 sample documents (2-3 per quadrant)
- Verify DQS calculated correctly
- Verify routing matches expected quadrant
- Verify JSON output includes routing rationale

**Test: Threshold Sensitivity**

- Process same document with different threshold configs
- Verify routing changes as expected when crossing thresholds

---

## References

**Research:**

- "Lost in OCR Translation?" study - OCR vs. Vision pipeline trade-off
- DocLayNet paper - Layout complexity metrics
- COCO dataset - Object detection for structure analysis

**Internal:**

- `docs/project_mandate.md` - Strategic justification for routing
- `docs/image_preprocessing.doc` - Academic taxonomy of document issues
- ADR-0007: Hybrid IQA Approach - Per-element quality assessment
- ADR-0008: Multi-Stage Pipeline Architecture - Pipeline modularity
- ADR-0020: CPU-First Deployment Strategy - Production constraints

**External:**

- [Tesseract Documentation](https://tesseract-ocr.github.io/) - OCR-based pipeline
- [ColPali Paper](https://arxiv.org/abs/2407.01449) - Vision-based retrieval
- [Nougat Paper](https://arxiv.org/abs/2308.13418) - Advanced OCR for structured docs

---

**Created**: 2025-11-11
**Last Updated**: 2025-11-11
**Next Review**: Phase 4 Planning (Week 17)
