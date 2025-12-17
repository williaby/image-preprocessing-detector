---
schema_type: planning
title: "Phase 7 IQA Benchmarking: Analysis and Recommendations"
description: "Comprehensive analysis of benchmarking gaps and actionable recommendations for improved model evaluation"
tags:
  - planning
  - phase7
  - benchmarking
  - evaluation
status: published
owner: core-maintainer
purpose: Analyze benchmarking gaps and provide actionable recommendations for Phase 7 IQA evaluation.
component: Evaluation
source: Manual creation
---

> **Date**: 2025-12-15
> **Author**: Claude Code (Opus 4.5)

---

## Executive Summary

This report analyzes the current benchmarking approach for the Phase 7 IQA model and identifies significant gaps that undermine the validity of performance claims. The current approach relies primarily on **internal synthetic test sets**, which creates circular validation and prevents meaningful comparison with state-of-the-art methods.

### Key Findings

| Finding | Severity | Impact |
|---------|----------|--------|
| No cross-dataset evaluation | **CRITICAL** | Cannot validate generalization |
| DIQA-5000 not integrated | HIGH | Missing human perception validation |
| Wrong calibration metric (ECE vs ENCE) | HIGH | Regression requires ENCE |
| No OCR correlation metrics | HIGH | IQA scores may not predict downstream performance |
| Baseline models untested | MEDIUM | No SOTA comparison available |
| Missing statistical rigor | MEDIUM | Point estimates without uncertainty |

### Recommended Priority Actions

1. **Immediate** (Week 1): Run existing PyIQA baselines script to populate benchmark tracker
2. **Short-term** (Week 2-3): Integrate DIQA-5000 into evaluation pipeline
3. **Medium-term** (Week 4-6): Add OCR correlation and cross-dataset validation
4. **Ongoing**: Report all metrics with 95% confidence intervals

---

## 1. Current State Analysis

### 1.1 Existing Benchmark Infrastructure

**Strengths:**
- Well-structured benchmark framework in `benchmarks/` directory
- PyIQA baselines script exists (`scripts/evaluate_pyiqa_baselines.py`)
- DIQA-5000 dataset downloaded (5.4GB)
- Benchmark tracker CSV with appropriate columns
- Multiple datasets available locally (~105GB total)

**Weaknesses:**
- Benchmark tracker shows most models as "pending"
- Primary evaluation uses internal Phase7 MVP test set
- No integration with external human-annotated benchmarks
- No OCR correlation validation
- Single-seed training without uncertainty quantification

### 1.2 Current Benchmark Tracker Status

From `data/benchmarks/IQA_MODEL_BENCHMARK_TRACKER.csv`:

| Model Category | Status | Issue |
|----------------|--------|-------|
| Statistical Baselines | Complete | Good - establishes lower bounds |
| Pretrained Features | Complete | Useful for transfer learning comparison |
| Classical IQA (BRISQUE, NIQE) | **Pending** | Need to run PyIQA script |
| Deep Learning (MUSIQ, HyperIQA) | **Pending** | Critical baselines missing |
| Document-Specific (DocIQ) | Reference only | Need actual evaluation |
| Our Models | Training | No external validation planned |

### 1.3 Available Datasets (Underutilized)

| Dataset | Downloaded | Integrated | Gap |
|---------|------------|------------|-----|
| DIQA-5000 | Yes (5.4GB) | **No** | Human MOS scores unused |
| SmartDoc-QA | No | No | Mobile capture benchmark missing |
| OHR-Bench | Yes (1.8GB) | Partial | OCR correlation possible |
| FUNSD+ | Yes (500MB) | Partial | Document understanding |
| Synthetic IQA | Yes | Yes | Only internal validation |

---

## 2. Gap Analysis

### 2.1 CRITICAL: No Cross-Dataset Evaluation

**Current Approach:**
```
Train: Phase7 synthetic dataset (200K images)
Test:  Phase7 held-out split (30K images)
```

**Problem:** Testing on the same distribution as training creates circular validation. The model may achieve excellent metrics on synthetic degradations but fail on real-world documents.

**Industry Standard:**
```
Train: Dataset A (e.g., Phase7 synthetic + DIQA-5000 fine-tune)
Test:  Dataset B, C, D (e.g., SmartDoc-QA, SROIE, DocVQA)
```

**Evidence from Literature:**
- DocIQ reports SRCC on DIQA-5000 (0.870) AND SmartDoc-QA (0.909)
- MUSIQ reports across LIVE, TID2013, KADID-10K, KONIQ-10K
- Cross-dataset drop < 0.10 indicates good generalization

**Required Action:**
1. Evaluate trained model on DIQA-5000 test split
2. Add SmartDoc-QA dataset for mobile capture validation
3. Report SRCC drop between in-distribution and cross-dataset

### 2.2 HIGH: Human Perception Validation Missing

**Current Approach:**
- Severity labels computed from synthetic parameters (e.g., `blur_severity = tanh(σ/10)`)
- No validation that these labels match human perception
- No correlation with human Mean Opinion Scores (MOS)

**Problem:** The PHASE7_CRITICAL_EVALUATION.md correctly identifies that:
> "The severity mappings are arbitrary without validation. A perceptual study should occur before dataset generation."

**Available Solution (Zero Cost):**
DIQA-5000 provides exactly what a custom perceptual study would deliver:
- 5,000 document images from 500 originals
- 15 human annotators per image
- Mean Opinion Scores (MOS) for quality assessment
- Document-specific degradations (blur, shadows, creases, moiré)

**Required Action:**
1. Correlate Phase7 model predictions with DIQA-5000 MOS labels
2. Target: Pearson correlation > 0.70 with human scores
3. Report per-degradation breakdown (blur, noise, compression, etc.)

### 2.3 HIGH: Wrong Calibration Metric

**Current Approach:**
- Uses ECE (Expected Calibration Error) as primary calibration metric
- Target: ECE < 0.08

**Problem:** ECE is designed for **classification** tasks. For **regression** with uncertainty prediction, the correct metric is ENCE (Expected Normalized Calibration Error):

| Metric | Suitable For | Formula |
|--------|--------------|---------|
| ECE | Classification | Average difference between confidence and accuracy per bin |
| **ENCE** | Regression | Average difference between RMV (√mean σ²) and RMSE per bin |
| MCE | Both | Maximum calibration error in any single bin |

**Evidence from Literature:**
> "For regression tasks, ENCE measures whether predicted uncertainty (σ²) matches actual prediction error. Published ENCE values: before calibration 12-25%, after STD scaling 4-8%."

**Required Action:**
1. Implement ENCE calculation in `benchmarks/metrics/`
2. Add MCE (Maximum Calibration Error) for worst-case analysis
3. Report both ENCE and MCE alongside current ECE

### 2.4 HIGH: No OCR Correlation Metrics

**Current Approach:**
- IQA model predicts severity scores
- No validation that scores correlate with OCR performance
- No measurement of downstream task impact

**Problem:** The PHASE7_CRITICAL_EVALUATION.md states:
> "IQA scores are meaningless if they don't correlate with OCR performance. Add Character Error Rate (CER) and Word Error Rate (WER) correlation as primary validation metrics."

**The OCR "Cliff Function":**
Research shows OCR accuracy follows a sigmoidal pattern:
- **Plateau:** For blur σ < 1.5, CER ≈ 0%
- **Cliff:** For 1.5 < σ < 2.5, CER spikes dramatically
- **Tail:** For σ > 2.5, CER saturates at ~100%

Linear severity mappings miss this critical non-linearity.

**Required Metrics:**
```python
# Correlation between IQA severity and OCR performance
cer_correlation = spearmanr(iqa_severity, character_error_rate)
wer_correlation = spearmanr(iqa_severity, word_error_rate)
ranking_agreement = overlap(iqa_worst_10pct, ocr_worst_10pct)

# Targets
cer_correlation > 0.70
ranking_agreement > 0.80
```

**Required Action:**
1. Create validation set with known CER/WER (use OHR-Bench or FUNSD)
2. Run Tesseract/EasyOCR on validation images
3. Compute correlation between IQA predictions and OCR error rates
4. Report in benchmark tracker

### 2.5 MEDIUM: Baseline Models Untested

**Current State in Benchmark Tracker:**

| Model | Status | DIQA-5000 SRCC | Notes |
|-------|--------|----------------|-------|
| BRISQUE | pending | - | Classical baseline |
| NIQE | pending | - | No-reference baseline |
| MUSIQ | pending | 0.855 (paper) | Transformer SOTA |
| HyperIQA | pending | 0.802 (paper) | Strong performer |
| DocIQ | reference | 0.870 (paper) | Document-specific SOTA |

**Problem:** Cannot claim competitive performance without running these baselines.

**Quick Win Available:**
The existing `scripts/evaluate_pyiqa_baselines.py` can populate these columns:

```bash
uv run python scripts/evaluate_pyiqa_baselines.py \
    --dataset all \
    --models musiq hyperiqa brisque niqe clipiqa dbcnn
```

**Required Action:**
1. Run PyIQA baselines script on DIQA-5000
2. Update benchmark tracker with actual measurements
3. Compare Phase7 model against SOTA (target: within 0.05 SRCC of MUSIQ)

### 2.6 MEDIUM: Missing Statistical Rigor

**Current Approach:**
- Single random seed (42)
- Point estimates without confidence intervals
- No significance testing for comparisons
- No effect size reporting

**Industry Standard:**
```
Method: Phase7_ResNet50
DIQA-5000 SRCC: 0.842 ± 0.015 (95% CI: 0.812-0.872)
vs MUSIQ baseline: Δ = +0.013 (p=0.023*, Cohen's d=0.31)
Seeds: [42, 123, 456], n=3
```

**Required Elements:**
1. **Confidence Intervals:** Bootstrap with 1000 resamples, report 95% CI
2. **Multi-seed Training:** Minimum 3 seeds, report mean ± std
3. **Significance Testing:** Paired t-test or Wilcoxon signed-rank
4. **Effect Size:** Cohen's d or r² for improvement claims
5. **Multiple Comparison Correction:** Bonferroni when comparing many methods

**Required Action:**
1. Implement bootstrap CI calculation in evaluation scripts
2. Train with multiple seeds (add to training config)
3. Add significance tests to benchmark comparison

---

## 3. Recommended Evaluation Protocol

### 3.1 Primary Benchmark Datasets

| Tier | Dataset | Purpose | Priority |
|------|---------|---------|----------|
| **Tier 1** | DIQA-5000 | Human MOS validation | **Required** |
| **Tier 1** | Phase7 MVP Test | In-distribution performance | Required |
| **Tier 2** | SmartDoc-QA | Mobile capture generalization | High |
| **Tier 2** | OHR-Bench | OCR correlation | High |
| **Tier 3** | KONIQ-10K | Authentic distortion scale | Medium |
| **Tier 3** | DocVQA subset | Document understanding | Medium |

### 3.2 Primary Metrics (Must Report)

| Metric | Type | Target | Notes |
|--------|------|--------|-------|
| **SRCC** | Correlation | > 0.80 | Spearman rank correlation |
| **PLCC** | Correlation | > 0.80 | After 4-param logistic fit |
| **ENCE** | Calibration | < 8% | Correct metric for regression |
| **MCE** | Calibration | < 15% | Worst-bin calibration |
| **CER Corr** | Downstream | > 0.70 | OCR correlation |

### 3.3 Secondary Metrics (Should Report)

| Metric | Type | Target | Notes |
|--------|------|--------|-------|
| KRCC | Correlation | > 0.60 | Kendall rank (conservative) |
| MAE | Error | < 0.15 | Mean absolute error |
| RMSE | Error | < 0.20 | Root mean squared error |
| Inference Time | Efficiency | < 30ms GPU | Per-image latency |

### 3.4 Reporting Format

**Per-Dataset Results Table:**
```markdown
| Dataset | Split | N | SRCC (95% CI) | PLCC (95% CI) | ENCE | MCE |
|---------|-------|---|---------------|---------------|------|-----|
| DIQA-5000 | test | 1,100 | 0.842 (0.81-0.87) | 0.851 (0.82-0.88) | 6.2% | 11.3% |
| SmartDoc-QA | full | 125 | 0.789 (0.72-0.85) | 0.802 (0.74-0.86) | 8.1% | 14.2% |
| Phase7 MVP | test | 30,000 | 0.912 (0.90-0.92) | 0.921 (0.91-0.93) | 4.3% | 8.7% |
```

**Baseline Comparison Table:**
```markdown
| Model | DIQA-5000 SRCC | Δ vs Ours | p-value | Significance |
|-------|----------------|-----------|---------|--------------|
| MUSIQ | 0.855 | -0.013 | 0.142 | ns |
| HyperIQA | 0.802 | +0.040 | 0.003 | ** |
| DocIQ | 0.870 | -0.028 | 0.067 | ns |
| Phase7 (Ours) | 0.842 | - | - | - |
```

**Per-Degradation Breakdown:**
```markdown
| Degradation | SRCC | PLCC | Notes |
|-------------|------|------|-------|
| Blur (Gaussian) | 0.891 | 0.902 | Strong |
| Blur (Motion) | 0.823 | 0.834 | Moderate |
| Noise | 0.867 | 0.879 | Good |
| Compression | 0.756 | 0.771 | Needs work |
| Shadows | 0.812 | 0.825 | Good |
```

---

## 4. Implementation Roadmap

### Phase 1: Quick Wins (Week 1)

**Task 1.1: Run PyIQA Baselines**
```bash
# Already exists - just run it
uv run python scripts/evaluate_pyiqa_baselines.py \
    --dataset all \
    --models musiq hyperiqa brisque niqe clipiqa dbcnn tres
```

**Task 1.2: Update Benchmark Tracker**
- Populate DIQA-5000 columns with actual measurements
- Add confidence intervals to results

**Deliverable:** Baseline comparison numbers in benchmark tracker

### Phase 2: DIQA-5000 Integration (Week 2-3)

**Task 2.1: Create DIQA-5000 Evaluation Script**
```python
# scripts/evaluate_on_diqa5000.py
def evaluate_phase7_on_diqa5000(model_path, diqa_path):
    """Evaluate Phase7 model on DIQA-5000 test set."""
    # Load model
    model = load_phase7_model(model_path)

    # Load DIQA-5000 with MOS labels
    test_set = load_diqa5000_test(diqa_path)

    # Predict
    predictions = model.predict(test_set.images)

    # Compute correlations with human MOS
    srcc = spearmanr(predictions, test_set.mos_labels)
    plcc = pearsonr_after_logistic_fit(predictions, test_set.mos_labels)

    # Per-degradation breakdown
    for degradation in test_set.degradation_types:
        mask = test_set.degradation == degradation
        srcc_deg = spearmanr(predictions[mask], test_set.mos_labels[mask])

    return results
```

**Task 2.2: Add to Training Pipeline**
- Include DIQA-5000 validation during training
- Track SRCC on external benchmark, not just internal loss

**Deliverable:** DIQA-5000 SRCC/PLCC numbers for Phase7 model

### Phase 3: OCR Correlation (Week 4-5)

**Task 3.1: Create OCR Validation Set**
```python
# scripts/create_ocr_validation_set.py
def create_ocr_validation_set(ohr_bench_path, output_path):
    """Create validation set with ground truth CER/WER."""
    images = load_ohr_bench_images(ohr_bench_path)

    for image in images:
        # Run OCR
        text_pred = tesseract.ocr(image)
        text_gt = load_ground_truth(image.id)

        # Compute error rates
        cer = character_error_rate(text_pred, text_gt)
        wer = word_error_rate(text_pred, text_gt)

        yield {
            'image': image,
            'cer': cer,
            'wer': wer,
            'ground_truth': text_gt
        }
```

**Task 3.2: Compute IQA-OCR Correlation**
```python
def validate_ocr_correlation(model, validation_set):
    """Validate IQA predictions correlate with OCR performance."""
    iqa_scores = model.predict(validation_set.images)

    cer_corr = spearmanr(iqa_scores, validation_set.cer)
    wer_corr = spearmanr(iqa_scores, validation_set.wer)

    # Ranking agreement: do worst IQA images have worst OCR?
    iqa_worst = np.argsort(iqa_scores)[:len(iqa_scores)//10]
    ocr_worst = np.argsort(validation_set.cer)[-len(validation_set.cer)//10:]
    ranking_agreement = len(set(iqa_worst) & set(ocr_worst)) / len(iqa_worst)

    return {
        'cer_correlation': cer_corr,
        'wer_correlation': wer_corr,
        'ranking_agreement': ranking_agreement
    }
```

**Deliverable:** OCR correlation metrics in benchmark tracker

### Phase 4: Statistical Rigor (Week 6)

**Task 4.1: Implement Bootstrap CI**
```python
def compute_bootstrap_ci(predictions, targets, metric_fn, n_bootstrap=1000):
    """Compute 95% confidence interval via bootstrap."""
    scores = []
    n = len(predictions)

    for _ in range(n_bootstrap):
        idx = np.random.choice(n, n, replace=True)
        score = metric_fn(predictions[idx], targets[idx])
        scores.append(score)

    ci_lower = np.percentile(scores, 2.5)
    ci_upper = np.percentile(scores, 97.5)

    return {
        'mean': np.mean(scores),
        'std': np.std(scores),
        'ci_95': (ci_lower, ci_upper)
    }
```

**Task 4.2: Multi-Seed Training**
- Train with seeds [42, 123, 456]
- Report mean ± std across seeds
- Use for significance testing

**Deliverable:** All metrics reported with 95% CI

### Phase 5: Cross-Dataset Validation (Week 7-8)

**Task 5.1: Add SmartDoc-QA Dataset**
- Download SmartDoc-QA benchmark
- Create adapter for evaluation pipeline
- Run cross-dataset evaluation

**Task 5.2: Report Generalization Gap**
```python
def report_generalization_gap(model, datasets):
    """Report SRCC drop across datasets."""
    results = {}

    for name, dataset in datasets.items():
        srcc = evaluate_srcc(model, dataset)
        results[name] = srcc

    # Compute gap
    in_dist = results['phase7_test']
    cross_dist = np.mean([results['diqa5000'], results['smartdoc']])
    gap = in_dist - cross_dist

    # Alert if gap too large
    if gap > 0.10:
        print(f"WARNING: Generalization gap {gap:.3f} exceeds threshold 0.10")

    return results
```

**Deliverable:** Cross-dataset SRCC table with generalization gap

---

## 5. New Metrics to Implement

### 5.1 ENCE (Expected Normalized Calibration Error)

```python
def compute_ence(predictions, uncertainties, targets, n_bins=15):
    """Compute ENCE for regression with uncertainty.

    ENCE measures whether predicted uncertainty (σ²) matches actual error.

    Args:
        predictions: Model mean predictions (N,)
        uncertainties: Model predicted std (N,)
        targets: Ground truth values (N,)
        n_bins: Number of calibration bins

    Returns:
        ENCE value (0 = perfect calibration)
    """
    # Sort by predicted uncertainty
    sorted_idx = np.argsort(uncertainties)
    predictions = predictions[sorted_idx]
    uncertainties = uncertainties[sorted_idx]
    targets = targets[sorted_idx]

    # Bin by uncertainty
    bin_size = len(predictions) // n_bins
    ence = 0.0

    for i in range(n_bins):
        start = i * bin_size
        end = start + bin_size if i < n_bins - 1 else len(predictions)

        bin_preds = predictions[start:end]
        bin_uncert = uncertainties[start:end]
        bin_targets = targets[start:end]

        # RMV: Root Mean Variance (expected uncertainty)
        rmv = np.sqrt(np.mean(bin_uncert ** 2))

        # RMSE: Root Mean Squared Error (actual error)
        rmse = np.sqrt(np.mean((bin_preds - bin_targets) ** 2))

        # Normalized calibration error for this bin
        if rmv > 0:
            ence += np.abs(rmv - rmse) / rmv

    return ence / n_bins
```

### 5.2 MCE (Maximum Calibration Error)

```python
def compute_mce(predictions, confidences, targets, n_bins=15):
    """Compute Maximum Calibration Error.

    MCE captures worst-bin calibration (important for safety-critical routing).
    """
    # Use same binning as ECE/ENCE
    bin_errors = []

    for bin_idx in range(n_bins):
        # ... compute per-bin calibration error ...
        bin_errors.append(abs(avg_confidence - accuracy))

    return max(bin_errors)
```

### 5.3 OCR Correlation Metrics

```python
def compute_ocr_correlation_metrics(iqa_scores, cer_scores, wer_scores):
    """Compute suite of OCR correlation metrics."""
    return {
        'cer_spearman': spearmanr(iqa_scores, cer_scores)[0],
        'cer_pearson': pearsonr(iqa_scores, cer_scores)[0],
        'wer_spearman': spearmanr(iqa_scores, wer_scores)[0],
        'wer_pearson': pearsonr(iqa_scores, wer_scores)[0],
        'ranking_agreement_10pct': compute_ranking_agreement(
            iqa_scores, cer_scores, percentile=10
        ),
        'ranking_agreement_25pct': compute_ranking_agreement(
            iqa_scores, cer_scores, percentile=25
        ),
    }
```

---

## 6. Updated Benchmark Tracker Schema

Recommend extending `IQA_MODEL_BENCHMARK_TRACKER.csv` with additional columns:

```csv
# Current columns (keep)
Model,Type,Source,Status,
Phase7_MVP_MAE,Phase7_MVP_RMSE,Phase7_MVP_Pearson,Phase7_MVP_Spearman,Phase7_MVP_ECE,
DIQA5000_Overall_SRCC,DIQA5000_Overall_PLCC,DIQA5000_Sharpness_SRCC,DIQA5000_ColorFidelity_SRCC,
SmartDocQA_CACC_SRCC,SmartDocQA_WACC_SRCC,Notes

# NEW columns to add
Phase7_MVP_ENCE,Phase7_MVP_MCE,  # Correct calibration metrics
DIQA5000_SRCC_CI_Lower,DIQA5000_SRCC_CI_Upper,  # Confidence intervals
OCR_CER_Correlation,OCR_WER_Correlation,OCR_Ranking_Agreement,  # OCR metrics
CrossDataset_SRCC_Gap,  # Generalization gap
Training_Seeds,  # Multi-seed indicator
```

---

## 7. Success Criteria Summary

### Minimum Viable Benchmarking (v1)

| Criterion | Target | Validation Method |
|-----------|--------|-------------------|
| DIQA-5000 SRCC | > 0.70 | External human MOS |
| DIQA-5000 PLCC | > 0.70 | External human MOS |
| OCR CER Correlation | > 0.70 | OHR-Bench validation |
| Cross-dataset gap | < 0.10 | SmartDoc-QA comparison |
| ENCE | < 8% | Regression calibration |

### Competitive Benchmarking (v2)

| Criterion | Target | Comparison |
|-----------|--------|------------|
| DIQA-5000 SRCC | > 0.85 | Match MUSIQ (0.855) |
| SmartDoc-QA SRCC | > 0.85 | Match DocIQ (0.909) |
| Statistical significance | p < 0.05 | vs baseline methods |
| Multi-seed variance | std < 0.02 | Reproducibility |

---

## 8. Appendix: Reference Implementations

### A.1 PyIQA Baseline Evaluation

```bash
# Install pyiqa
pip install pyiqa

# Run comprehensive baseline evaluation
python scripts/evaluate_pyiqa_baselines.py \
    --dataset all \
    --models musiq hyperiqa brisque niqe clipiqa dbcnn tres maniqa \
    --output-dir data/benchmarks \
    --device cuda
```

### A.2 DIQA-5000 Dataset Structure

```
data/benchmarks/diqa-5000/
├── train/
│   └── ori/           # 3.8GB, training originals
├── val/
│   └── ori/           # 470MB, validation originals
├── test/
│   └── ori/           # 1.1GB, test originals
└── annotations/
    ├── train.json     # MOS labels for training
    ├── val.json       # MOS labels for validation
    └── test.json      # MOS labels for test
```

### A.3 Key External Resources

| Resource | Purpose | URL |
|----------|---------|-----|
| IQA-PyTorch | 30+ IQA methods | github.com/chaofengc/IQA-PyTorch |
| DIQA-5000 | Human MOS benchmark | CodaLab VQualA 2025 |
| SmartDoc-QA | Mobile document quality | ICDAR 2015 |
| DocIQ Paper | Document-specific SOTA | arXiv:2509.17012 |
| Calibration Framework | ENCE implementation | github.com/EFS-OpenSource/calibration-framework |

---

## 9. Conclusion

The current benchmarking approach has significant gaps that undermine confidence in model performance claims. The primary issues are:

1. **Circular validation** - Testing on same distribution as training
2. **Missing human perception validation** - DIQA-5000 exists but unused
3. **Wrong calibration metric** - ECE is for classification, ENCE for regression
4. **No downstream validation** - IQA scores not linked to OCR performance

The recommended protocol addresses all gaps with **zero additional cost** by leveraging:
- Existing downloaded datasets (DIQA-5000, OHR-Bench)
- Pre-trained baseline models (via PyIQA)
- Standard evaluation metrics (SRCC, PLCC, ENCE)

Implementing this protocol requires approximately **2-3 weeks of engineering effort** and will transform the evaluation from "internal synthetic validation" to "industry-standard cross-dataset benchmarking with human perception correlation."

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Related Documents**:
- [PHASE7_CRITICAL_EVALUATION.md](PHASE7_CRITICAL_EVALUATION.md)
- [PHASE7_IDEAL_STATE_PROJECT_PLAN.md](PHASE7_IDEAL_STATE_PROJECT_PLAN.md)
- [data/benchmarks/README.md](../../data/benchmarks/README.md)
