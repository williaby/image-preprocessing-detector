---
schema_type: common
title: "ADR-030: Document Quality Score (DQS) Design"
description: "Aggregate IQA metrics and layout complexity into a holistic document
  quality score for routing and risk assessment"
tags:
- adr
- dqs
- quality_score
- routing
- metrics
- aggregation
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to compute a two-component Document Quality Score
  combining degradation and structural complexity for downstream routing."
---

**Status**: Accepted
**Date**: 2025-11-15
**Deciders**: Byron Williams
**Related**:

- [ADR-014: Classical CV + ML Hybrid IQA](0014-classical-ml-hybrid-iqa.md)
- [ADR-028: ResNet Teacher-Student Architecture](0028-resnet-teacher-student-architecture.md)
- [ADR-029: Prepare-Doc Scope Boundaries](0029-prepare-doc-scope-boundaries.md)
- [Prepare-Doc F&NF Requirements](../development/RAG%20Pipeline/Project_A_F_NF.md)

## Context

Prepare-Doc processes diverse document types ranging from pristine born-digital PDFs to heavily degraded scans. Downstream projects (B: OCR, C: Fusion, D: Indexing) need a **single holistic quality signal** to make intelligent routing decisions.

**Current State**:

- Classical IQA produces 5+ metrics per page (blur, noise, skew, contrast, illumination)
- ML IQA produces 5+ metrics per page (same dimensions, different algorithm)
- Layout-lite produces structural attributes (has_tables, has_handwriting, complexity)
- **Problem**: No single "quality score" to answer: "Is this document easy or hard to process?"

**Downstream Needs**:

1. **OCR Engine Selection** (Unify):
   - High-quality, simple layout → Fast OCR (Tesseract)
   - Degraded or complex layout → Advanced OCR (PaddleOCR, EasyOCR)
   - Handwriting present → Specialized OCR (TrOCR, IAM-trained models)

2. **Confidence Thresholds** (Chunk):
   - High-quality documents → Trust single OCR engine
   - Low-quality documents → Require multi-engine consensus

3. **Retrieval Strategy** (Embed):
   - Low-complexity documents → Standard chunking
   - High-complexity documents → Semantic chunking with layout awareness

**Key Questions**:

- How do we aggregate 10+ IQA metrics into a single score?
- Should we combine quality degradation and structural complexity, or keep them separate?
- What weights should different metrics have?
- How do we make the score interpretable and actionable?

## Decision

**Implement a two-component Document Quality Score (DQS)**:

```json
"dqs": {
  "degradation_score": 0.75,          // 0-1, higher = more degraded
  "structural_complexity_score": 0.60  // 0-1, higher = more complex
}
```

**Additionally compute**:

```json
"pre_ocr_risk": 0.45  // 0-1, probability of OCR failure (combined signal)
```

### Component 1: Degradation Score

**Definition**: Quantifies image quality degradation (blur, noise, artifacts). Higher score = worse quality.

**Inputs**:

- Classical IQA: `blur_classical`, `noise_classical`, `skew_classical`, `contrast_classical`, `illumination_classical`, `jpeg_artifacts_classical`
- ML IQA: `blur_ml`, `noise_ml`, `skew_ml`, `contrast_ml`, `illumination_ml`, `artifacts_ml`
- Both normalized to 0-1 where 0 = perfect, 1 = severe degradation

**Aggregation Formula (weighted average)**:

```python
degradation_score = (
    w_blur * max(blur_classical, blur_ml) +
    w_noise * max(noise_classical, noise_ml) +
    w_skew * max(skew_classical, skew_ml) +
    w_contrast * max(contrast_classical, contrast_ml) +
    w_illumination * max(illumination_classical, illumination_ml) +
    w_artifacts * max(jpeg_artifacts_classical, artifacts_ml)
) / sum(weights)
```

**Default Weights** (calibrated against OCR performance):

- `w_blur = 0.30` (most critical for OCR)
- `w_noise = 0.20`
- `w_skew = 0.15`
- `w_contrast = 0.15`
- `w_illumination = 0.10`
- `w_artifacts = 0.10`

**Rationale for max(classical, ml)**:

- Classical and ML IQA may disagree on edge cases
- Conservative approach: assume worst-case degradation
- Alternative considered: average(classical, ml) - REJECTED as too optimistic

**Page-level vs Document-level**:

- Compute per-page degradation score
- Document-level = **95th percentile** of page scores (worst 5% of pages dominate)
- Rationale: OCR fails on worst pages, not average quality

### Component 2: Structural Complexity Score

**Definition**: Quantifies document layout complexity. Higher score = more complex structure.

**Inputs** (from layout-lite):

- `layout_type`: `single_column=0.2`, `multi_column=0.5`, `three_column=0.7`, `complex=1.0`
- `has_tables`: `true=+0.3`, `false=+0.0`
- `has_figures`: `true=+0.2`, `false=+0.0`
- `has_dense_math`: `true=+0.4`, `false=+0.0`
- `has_handwriting`: `true=+0.5`, `false=+0.0`
- Capped at 1.0

**Aggregation Formula (additive with cap)**:

```python
page_complexity = min(1.0,
    layout_type_score +
    (0.3 if has_tables else 0) +
    (0.2 if has_figures else 0) +
    (0.4 if has_dense_math else 0) +
    (0.5 if has_handwriting else 0)
)
```

**Document-level = mean** of page complexities (complexity is additive across pages)

### Component 3: Pre-OCR Risk Score

**Definition**: Probability (0-1) that OCR will fail on this document. Combines degradation and complexity.

**Formula (logistic regression)**:

```python
pre_ocr_risk = sigmoid(
    β0 +
    β1 * degradation_score +
    β2 * structural_complexity_score +
    β3 * (degradation_score * structural_complexity_score)  # Interaction term
)

sigmoid(x) = 1 / (1 + exp(-x))
```

**Calibration**: Coefficients `β0, β1, β2, β3` tuned on validation set with ground-truth OCR failures.

**Initial Estimates** (before calibration):

- `β0 = -2.0` (low base rate of OCR failure)
- `β1 = 3.0` (degradation strongly predicts failure)
- `β2 = 2.0` (complexity moderately predicts failure)
- `β3 = 1.5` (interaction: complex + degraded = much higher risk)

**Validation Target**: Brier score < 0.15, AUC-ROC > 0.85 on OCR failure prediction.

## Output Schema

**DocumentMetadata**:

```json
{
  "document_id": "doc_12345",
  "dqs": {
    "degradation_score": 0.75,          // 95th percentile of page scores
    "structural_complexity_score": 0.60  // Mean of page scores
  },
  "pre_ocr_risk": 0.45,
  "pages": [
    {
      "page_number": 1,
      "degradation_score": 0.72,
      "structural_complexity_score": 0.65,
      "iqa_classical": { "blur": 0.20, "noise": 0.15, ... },
      "iqa_ml": { "blur": 0.18, "noise": 0.12, ... },
      "layout_type": "multi_column",
      "has_tables": true,
      ...
    }
  ]
}
```

## Routing Decision Logic

**OCR Routing Recommendation** (enum: `ocr_fast` | `ocr_advanced` | `vision_simple` | `vision_structured`):

```python
def compute_routing(dqs, pre_ocr_risk, layout, pdf_type):
    # High-risk documents → advanced OCR
    if pre_ocr_risk > 0.7 or dqs.degradation_score > 0.8:
        return "ocr_advanced"

    # Handwriting → specialized OCR
    if layout.has_handwriting:
        return "vision_structured"

    # Complex layout (tables, math, multi-column)
    if dqs.structural_complexity_score > 0.6:
        return "ocr_advanced"

    # Born-digital PDFs with low degradation → skip OCR, use text extraction
    if pdf_type == "born_digital" and dqs.degradation_score < 0.3:
        return "vision_simple"

    # Default: fast OCR for simple, clean documents
    return "ocr_fast"
```

**Teacher Escalation** (for ML IQA):

```python
def should_escalate_to_teacher(page, student_uncertainty):
    # High degradation + high uncertainty
    if page.degradation_score > 0.7 and student_uncertainty > 0.6:
        return True

    # High-risk documents
    if page.pre_ocr_risk > 0.8:
        return True

    # Classical vs ML IQA large discrepancy
    if abs(page.iqa_classical.blur - page.iqa_ml.blur) > 0.3:
        return True

    return False
```

## Consequences

### Positive

1. **Holistic quality signal**: Single DQS replaces 10+ individual metrics for routing decisions
2. **Interpretable**: Two components (degradation, complexity) are intuitive for debugging
3. **Calibrated**: Pre-OCR risk score directly predicts OCR failure probability
4. **Flexible**: Weights and thresholds configurable per deployment
5. **Actionable**: Clear mapping from DQS → routing recommendation
6. **Page-level granularity**: Supports mixed-quality documents (some pages pristine, some degraded)

### Negative

1. **Information loss**: Aggregation discards nuances (e.g., specific type of blur)
   - **Mitigation**: Retain per-page IQA metrics in schema for debugging
2. **Weight tuning required**: Default weights may not generalize to all domains
   - **Mitigation**: Provide calibration script with user-supplied OCR ground truth
3. **Interaction complexity**: Pre-OCR risk formula may be hard to debug
   - **Mitigation**: Log intermediate values (degradation, complexity, interaction term)
4. **Versioning**: Changes to weights invalidate historical DQS scores
   - **Mitigation**: Include `dqs_version` field in schema

### Neutral

1. **Document-level only**: DQS is document-scoped, not suitable for per-page routing (if needed)
2. **No external benchmarks**: DQS is a custom metric, not comparable to other systems

## Calibration & Validation

### Phase 1: Initial Weights (Week 3)

**Approach**: Expert-driven weights based on OCR sensitivity literature

- Blur > Noise > Skew > Contrast > Illumination > Artifacts
- Validate on 100 manually annotated documents

### Phase 2: Data-Driven Calibration (Week 4)

**Dataset**: 500+ documents with ground-truth OCR quality (CER, WER)

- Fit logistic regression for `pre_ocr_risk` coefficients
- Optimize degradation weights to maximize correlation with OCR error rate
- Optimize complexity weights to maximize correlation with layout extraction failures

**Evaluation Metrics**:

- Degradation score: Spearman ρ > 0.7 with OCR CER
- Complexity score: Spearman ρ > 0.6 with layout extraction F1
- Pre-OCR risk: AUC-ROC > 0.85, Brier score < 0.15

### Phase 3: A/B Testing (Week 10)

**Experiment**: Route 50% of documents using DQS, 50% using heuristics

- Measure downstream OCR accuracy, latency, cost
- Target: DQS routing improves OCR CER by > 5% with < 10% latency increase

## Configuration Parameters

**config.yaml**:

```yaml
dqs:
  degradation_weights:
    blur: 0.30
    noise: 0.20
    skew: 0.15
    contrast: 0.15
    illumination: 0.10
    artifacts: 0.10

  degradation_aggregation: "max"  # max(classical, ml) or mean
  degradation_percentile: 95      # Document-level = 95th percentile of pages

  complexity_weights:
    single_column: 0.2
    multi_column: 0.5
    three_column: 0.7
    complex: 1.0
    has_tables: 0.3
    has_figures: 0.2
    has_dense_math: 0.4
    has_handwriting: 0.5

  pre_ocr_risk_coefficients:
    intercept: -2.0
    degradation: 3.0
    complexity: 2.0
    interaction: 1.5

  routing_thresholds:
    high_risk: 0.7
    high_degradation: 0.8
    high_complexity: 0.6
    low_degradation_born_digital: 0.3
```

## Alternatives Considered

### Alternative 1: Single Unified Score (0-1)

**Approach**: `quality_score = w1 * degradation + w2 * complexity`

**Pros**:

- Simplest possible interface
- Single threshold for all routing decisions

**Cons**:

- Information loss: cannot distinguish degraded+simple from pristine+complex
- Non-interpretable: what does 0.65 mean?
- **REJECTED**: Insufficient granularity for intelligent routing

### Alternative 2: Vector of Raw Metrics (No Aggregation)

**Approach**: Pass all 10+ IQA metrics to Unify, let it decide

**Pros**:

- No information loss
- Maximum flexibility for downstream projects

**Cons**:

- Pushes complexity to Unify (violates separation of concerns)
- Duplicates routing logic across multiple projects
- Harder to evolve (changes in Prepare-Doc break Unify)
- **REJECTED**: Poor separation of concerns, integration friction

### Alternative 3: ML Model for DQS

**Approach**: Train a regression model to predict OCR CER from IQA metrics

**Pros**:

- Data-driven, no manual weight tuning
- Potentially higher accuracy

**Cons**:

- Black-box: hard to debug and explain
- Requires large labeled dataset (500+ documents with OCR ground truth)
- More complex deployment (another model to maintain)
- **REJECTED**: Premature complexity, can revisit in Phase 3

### Alternative 4: Industry-Standard Metrics (BRISQUE, NIQE)

**Approach**: Use BRISQUE/NIQE as DQS

**Pros**:

- No calibration required
- Widely recognized metrics

**Cons**:

- Designed for natural images, not documents
- Weak correlation with OCR performance (ρ ~ 0.4-0.5)
- No structural complexity component
- **REJECTED**: Insufficient OCR predictive power

## Implementation Roadmap

**Week 3: Core Implementation**

- [ ] Implement `compute_degradation_score(page)` function
- [ ] Implement `compute_complexity_score(page)` function
- [ ] Implement `compute_pre_ocr_risk(document)` function
- [ ] Add DQS fields to schema (DocumentMetadata, PageMetadata)
- [ ] Add configuration parameters

**Week 4: Calibration**

- [ ] Collect 500-document validation set with OCR ground truth
- [ ] Fit logistic regression for pre-OCR risk coefficients
- [ ] Optimize degradation weights via grid search
- [ ] Validate: AUC-ROC > 0.85, Spearman ρ > 0.7

**Week 5: Routing Logic**

- [ ] Implement `compute_ocr_routing_recommendation(dqs, pdf_type, layout)`
- [ ] Implement `should_escalate_to_teacher(page, uncertainty)`
- [ ] Add routing recommendation to DocumentMetadata schema

**Week 10: A/B Testing**

- [ ] Deploy A/B test: DQS routing vs heuristics
- [ ] Measure OCR CER, latency, cost
- [ ] Target: > 5% OCR accuracy improvement

## Risk Mitigation

1. **Risk**: Weights don't generalize to new document types
   - **Mitigation**: Provide domain-specific config presets (e.g., `config_medical.yaml`, `config_legal.yaml`)
   - **Monitoring**: Track DQS distribution per document type, flag outliers

2. **Risk**: Pre-OCR risk miscalibrated (false positives/negatives)
   - **Mitigation**: Log routing decisions and OCR outcomes for continuous recalibration
   - **Monitoring**: Weekly Brier score and AUC-ROC on production data

3. **Risk**: 95th percentile too conservative (flags good docs as bad)
   - **Mitigation**: Make percentile configurable (e.g., 90th, 95th, 99th)
   - **A/B test**: Compare 90th vs 95th percentile, measure false positive rate

4. **Risk**: Complexity score unreliable without ML layout detection
   - **Mitigation**: Start with heuristic-based layout-lite, upgrade to YOLOv8-nano in Phase 2
   - **Validation**: Manual review of 200 documents, target > 85% accuracy

## References

- [Kanungo et al., "A Methodology for Quantitative Performance Evaluation of Document Image Quality" (1996)](https://ieeexplore.ieee.org/document/506424)
- [Ye & Doermann, "Document Image Quality Assessment: A Brief Survey" (2013)](https://link.springer.com/chapter/10.1007/978-3-642-36447-9_4)
- [BRISQUE: No-Reference Image Quality Assessment](https://live.ece.utexas.edu/research/quality/BRISQUE_release.zip)
- [ADR-014: Classical CV + ML Hybrid IQA](0014-classical-ml-hybrid-iqa.md)
- [ADR-028: ResNet Teacher-Student Architecture](0028-resnet-teacher-student-architecture.md)
- [Prepare-Doc F&NF Requirements](../development/RAG%20Pipeline/Project_A_F_NF.md)
