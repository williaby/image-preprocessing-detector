---
schema_type: common
title: "IQA Model Benchmark Reference"
tags:
  - ml
  - testing
  - evaluation
status: published
owner: docs-team
purpose: Complete reference for running and interpreting IQA model benchmarks.
---

> **Status**: Active | Version 1.0.0
> **Last Updated**: 2025-12-16
>
> Complete reference for running and interpreting IQA model benchmarks.

## Quick Start

```bash
# Full benchmark with all evaluations
poetry run python scripts/run_model_benchmark.py \
    --model-path checkpoints/phase7/best_model.pt \
    --model-name "MyModel_v1" \
    --update-csv

# Quick benchmark (Phase7 only, no bootstrap CI)
poetry run python scripts/run_model_benchmark.py \
    --model-path checkpoints/model.pt \
    --model-name "MyModel_v1" \
    --quick

# With OCR correlation evaluation
poetry run python scripts/run_model_benchmark.py \
    --model-path checkpoints/model.pt \
    --model-name "MyModel_v1" \
    --ocr-correlation
```

## Model Requirements

### Checkpoint Format

The benchmark script expects a PyTorch checkpoint (`.pt` file) with the following structure:

```python
checkpoint = {
    "state_dict": model.state_dict(),  # Required: model weights
    "config": {...},                    # Optional: model configuration
    "epoch": int,                       # Optional: training epoch
}
```

### Output Shape Requirements

Models must output predictions with shape `[N, 5]` where:

- `N` = batch size
- `5` = number of degradation heads in order: **Blur, Noise, Compression, Contrast, Geometric**

```python
# Expected output format
predictions = model(images)  # Shape: [batch_size, 5]
# predictions[:, 0] = blur severity [0, 1]
# predictions[:, 1] = noise severity [0, 1]
# predictions[:, 2] = compression severity [0, 1]
# predictions[:, 3] = contrast severity [0, 1]
# predictions[:, 4] = geometric severity [0, 1]
```

### Supported Model Architectures

| Source | Architecture | Notes |
|--------|--------------|-------|
| **Ours** | `MultiHeadIQA` (ResNet-50/18) | Full benchmark support |
| **PyIQA** | Various (HyperIQA, CLIP-IQA, etc.) | Planned - not yet implemented |
| **OpenCV** | Classical metrics | Planned - not yet implemented |

**Note**: Currently only custom `MultiHeadIQA` models are fully supported. PyIQA and OpenCV sources are documented in the CSV tracker for comparison but the benchmark script's `load_model()` function only supports custom checkpoints.

## Benchmark Workflow Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IQA Model Benchmark Pipeline                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │    Model     │───▶│   Phase7     │───▶│  DIQA-5000   │───▶│  SmartDoc  │ │
│  │   Loading    │    │     MVP      │    │ (optional)   │    │    -QA     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│         │                   │                   │                   │       │
│         ▼                   ▼                   ▼                   ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  Checkpoint  │    │  Per-Head    │    │   Bootstrap  │    │    OCR     │ │
│  │   Parsing    │    │   Metrics    │    │      CI      │    │ Correlation│ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│                                                                              │
│                              ┌──────────────┐                               │
│                              │    Results   │                               │
│                              │  Aggregation │                               │
│                              └──────────────┘                               │
│                                     │                                        │
│                     ┌───────────────┼───────────────┐                       │
│                     ▼               ▼               ▼                       │
│              ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│              │    JSON    │  │    CSV     │  │   Console  │                 │
│              │   Output   │  │   Update   │  │   Summary  │                 │
│              └────────────┘  └────────────┘  └────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

See [project-a-benchmark-workflow.puml](../planning/project-a-benchmark-workflow.puml) for the detailed PlantUML diagram.

## Datasets

### Phase7 MVP (Primary Benchmark)

| Attribute | Value |
|-----------|-------|
| **Purpose** | In-distribution IQA evaluation |
| **Samples** | ~23,000 test images |
| **Labels** | Continuous severity [0, 1] per degradation |
| **Heads** | Blur, Noise, Compression, Contrast, Geometric |
| **Location** | `data/phase7_mvp/02_splits/test/` |

**What it measures**: How well the model predicts degradation severity on images from the same distribution as training data.

### DIQA-5000 (Cross-Dataset Benchmark)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Cross-distribution generalization |
| **Samples** | ~5,000 test images |
| **Labels** | Mean Opinion Score (MOS) |
| **Metric** | Overall quality score |
| **Location** | `data/benchmarks/diqa-5000/` |

**What it measures**: Whether the model generalizes beyond its training distribution to predict human-perceived quality.

### SmartDoc-QA (OCR Correlation)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Validate IQA predicts OCR performance |
| **Samples** | ~200 document images |
| **Labels** | Tesseract OCR accuracy (CACC/WACC) |
| **Sources** | Nokia phone, Samsung phone captures |
| **Location** | `/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/` |

**What it measures**: Whether low IQA scores correlate with poor OCR accuracy (practical utility validation).

## Dataset Preparation

### Phase7 MVP Directory Layout

```text
data/phase7_mvp/02_splits/
├── test/
│   ├── images/
│   │   ├── img_00001.png
│   │   ├── img_00002.png
│   │   └── ...
│   └── labels.csv
│       # Columns: image_path, blur, noise, compression, contrast, geometric
│       # Values: continuous severity scores [0, 1]
└── val/
    ├── images/
    └── labels.csv
```

### DIQA-5000 Directory Layout

```text
data/benchmarks/diqa-5000/
├── images/
│   ├── I01_01_01.png
│   ├── I01_01_02.png
│   └── ...
└── mos_scores.csv
    # Columns: image_name, mos
    # Values: Mean Opinion Score [1, 5] or normalized [0, 1]
```

### SmartDoc-QA Directory Layout

```text
/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/
├── Nokia/
│   ├── images/
│   │   ├── doc001_page01.jpg
│   │   └── ...
│   └── ocr_results.csv
│       # Columns: image, cacc, wacc (character/word accuracy)
├── Samsung/
│   ├── images/
│   └── ocr_results.csv
└── README.md
```

**Dataset Availability**:

- **Phase7 MVP**: Generated from training pipeline (see PROJECT_PLAN.md)
- **DIQA-5000**: Download from [official source](https://github.com/anse3832/DIQA)
- **SmartDoc-QA**: Download from [SmartDoc-QA challenge](https://smartdoc.univ-lr.fr/)

## Metrics Reference

### Correlation Metrics

| Metric | Full Name | Range | Interpretation |
|--------|-----------|-------|----------------|
| **SRCC** | Spearman Rank Correlation Coefficient | [-1, 1] | Monotonic relationship; higher = better ranking |
| **PLCC** | Pearson Linear Correlation Coefficient | [-1, 1] | Linear relationship; higher = better magnitude prediction |

**Target Values**:

- SRCC > 0.70: Good performance
- SRCC > 0.85: Excellent performance
- PLCC > 0.70: Good linear fit

### Error Metrics

| Metric | Full Name | Range | Interpretation |
|--------|-----------|-------|----------------|
| **MAE** | Mean Absolute Error | [0, 1] | Average prediction error; lower = better |
| **RMSE** | Root Mean Squared Error | [0, 1] | Penalizes large errors; lower = better |

**Target Values**:

- MAE < 0.25: Good accuracy
- RMSE < 0.30: Good precision

### Calibration Metrics

| Metric | Full Name | Range | Interpretation |
|--------|-----------|-------|----------------|
| **ENCE** | Expected Normalized Calibration Error | [0, ∞) | Uncertainty calibration for regression; lower = better |
| **MCE** | Maximum Calibration Error | [0, 1] | Worst-case bin calibration; lower = better |

**Target Values**:

- ENCE < 0.10: Well-calibrated uncertainty
- MCE < 0.15: No severe miscalibration

**ENCE Implementation Note**: The current benchmark uses a **heuristic proxy** for uncertainty: `|prediction - 0.5| + 0.1`. This approximates uncertainty based on prediction extremity (predictions near 0 or 1 are treated as more confident). For true uncertainty calibration, models should output explicit uncertainty estimates (e.g., predicted variance from a Gaussian head). ENCE values from this heuristic are **indicative only** and should be interpreted with caution.

**ENCE Explained**: ENCE measures whether predicted uncertainty matches actual error. If a model predicts high uncertainty, the actual error should be proportionally high. This is critical for selective teacher inference decisions. When using the heuristic proxy, this relationship is approximated rather than directly measured.

### OCR Correlation Metrics

| Metric | Full Name | Range | Interpretation |
|--------|-----------|-------|----------------|
| **CER Corr** | Character Accuracy Correlation | [-1, 1] | IQA quality vs OCR character accuracy (CACC) |
| **WER Corr** | Word Accuracy Correlation | [-1, 1] | IQA quality vs OCR word accuracy (WACC) |
| **Ranking** | Ranking Agreement | [0, 1] | Overlap of worst 10% by IQA and OCR |

**Interpretation Note**: These metrics correlate IQA scores with OCR **accuracy** (not error rate). Higher correlation means higher IQA quality scores correspond to higher OCR accuracy, which is the expected relationship. A positive correlation > 0.70 indicates strong predictive value.

**Target Values**:

- CER Correlation > 0.70: Strong OCR predictive value (higher IQA → higher OCR accuracy)
- Ranking Agreement > 0.80: Reliable worst-image detection

### Cross-Dataset Gap

```text
Gap = Phase7_SRCC - DIQA5000_SRCC
```

| Gap Value | Interpretation |
|-----------|----------------|
| < 0.05 | Excellent generalization |
| 0.05 - 0.10 | Good generalization |
| 0.10 - 0.15 | Moderate overfitting |
| > 0.15 | Significant overfitting concern |

## CSV Tracker Columns

The benchmark populates these columns in `IQA_MODEL_BENCHMARK_TRACKER.csv`:

### Metadata Columns

| Column | Description | Example |
|--------|-------------|---------|
| `Model` | Model identifier | `ResNet50_Teacher_v3` |
| `Type` | Architecture category | `deep_learning`, `classical`, `vision_language` |
| `Source` | Model origin | `Ours`, `PyIQA`, `OpenCV` |
| `Status` | Evaluation status | `evaluated`, `target`, `pending` |

### Phase7 MVP Columns

| Column | Source | Description |
|--------|--------|-------------|
| `Phase7_MVP_Spearman` | Macro SRCC | Average Spearman across heads |
| `Phase7_MVP_Pearson` | Macro PLCC | Average Pearson across heads |
| `Phase7_MVP_MAE` | Macro MAE | Average absolute error |
| `Phase7_MVP_RMSE` | Macro RMSE | Average root squared error |
| `Phase7_MVP_ENCE` | Macro ENCE | Average calibration error |
| `Phase7_MVP_MCE` | Max MCE | Worst-case calibration |

### Per-Degradation Columns

| Column | Source | Description |
|--------|--------|-------------|
| `Blur_Spearman` | Blur head | Blur detection performance |
| `Noise_Spearman` | Noise head | Noise detection performance |
| `Compress_Spearman` | Compression head | Compression artifact detection |
| `Contrast_Spearman` | Contrast head | Contrast issue detection |

### DIQA-5000 Columns

| Column | Source | Description |
|--------|--------|-------------|
| `DIQA5000_SRCC` | Test SRCC | Cross-dataset correlation |
| `DIQA5000_PLCC` | Test PLCC | Cross-dataset linear fit |
| `DIQA5000_SRCC_CI_Lower` | Bootstrap CI | 95% confidence lower bound |
| `DIQA5000_SRCC_CI_Upper` | Bootstrap CI | 95% confidence upper bound |

### OCR Correlation Columns

| Column | Source | Description |
|--------|--------|-------------|
| `OCR_CER_Correlation` | SmartDoc-QA | Character accuracy correlation |
| `OCR_WER_Correlation` | SmartDoc-QA | Word accuracy correlation |
| `OCR_Ranking_Agreement` | SmartDoc-QA | Worst-image overlap |

### Other Columns

| Column | Source | Description |
|--------|--------|-------------|
| `CrossDataset_SRCC_Gap` | Computed | Phase7 - DIQA5000 SRCC |
| `Training_Seeds` | User input | Seeds used for training |
| `Inference_ms` | Measured | Average inference time per sample |
| `Notes` | User input | Additional observations |

## CLI Reference

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--model-path` | Path to PyTorch checkpoint (.pt file) |
| `--model-name` | Model identifier for tracking |

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--model-type` | `deep_learning` | `deep_learning`, `classical`, or `vision_language` |
| `--source` | `Ours` | `Ours`, `PyIQA`, or `OpenCV` |
| `--phase7-path` | `data/phase7_mvp/02_splits` | Phase7 MVP dataset path |
| `--diqa5000-path` | `data/benchmarks/diqa-5000` | DIQA-5000 dataset path |
| `--smartdoc-qa-path` | `/mnt/e/...` | SmartDoc-QA dataset path |
| `--output-dir` | `data/benchmarks` | Output directory for JSON |
| `--csv-path` | `benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv` | Path to CSV tracker file |
| `--batch-size` | `64` | Inference batch size |
| `--training-seeds` | `42` | Training seeds (comma-separated) |
| `--notes` | `""` | Notes about the model |

### Flags

| Flag | Effect |
|------|--------|
| `--quick` | Phase7 only, skip DIQA-5000 and bootstrap CI |
| `--update-csv` | Update the benchmark tracker CSV |
| `--ocr-correlation` | Run SmartDoc-QA OCR correlation |

## Comparing Two Models

### Step 1: Run Benchmarks

```bash
# Benchmark Model A
poetry run python scripts/run_model_benchmark.py \
    --model-path checkpoints/model_a.pt \
    --model-name "Model_A" \
    --update-csv

# Benchmark Model B
poetry run python scripts/run_model_benchmark.py \
    --model-path checkpoints/model_b.pt \
    --model-name "Model_B" \
    --update-csv
```

### Step 2: Compare Key Metrics

Open `benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv` and compare:

| Comparison Area | Metrics to Compare | Decision Criteria |
|-----------------|-------------------|-------------------|
| **Overall Performance** | Phase7_MVP_Spearman, Phase7_MVP_Pearson | Higher is better |
| **Prediction Accuracy** | Phase7_MVP_MAE, Phase7_MVP_RMSE | Lower is better |
| **Uncertainty Quality** | Phase7_MVP_ENCE, Phase7_MVP_MCE | Lower is better |
| **Generalization** | DIQA5000_SRCC, CrossDataset_SRCC_Gap | Higher SRCC, lower gap |
| **OCR Utility** | OCR_CER_Correlation | Higher is better |
| **Speed** | Inference_ms | Lower is better |

### Step 3: Statistical Significance

Check if SRCC difference is significant using bootstrap CI:

```python
# If confidence intervals don't overlap, difference is likely significant
Model_A: DIQA5000_SRCC = 0.72 (0.68, 0.76)
Model_B: DIQA5000_SRCC = 0.78 (0.74, 0.82)
# Non-overlapping → Model_B significantly better
```

**Statistical Caveat**: Non-overlapping 95% CIs is a conservative heuristic for significance. Overlapping CIs do **not** necessarily mean no significant difference—the true significance depends on the joint distribution. For rigorous comparison, consider a paired bootstrap test or permutation test on the difference.

**Note**: This step requires full benchmark mode. Using `--quick` skips DIQA-5000 evaluation and bootstrap CI computation, making statistical comparison impossible.

### Step 4: Trade-off Analysis

Consider trade-offs based on use case:

| Use Case | Priority Metrics | Acceptable Trade-offs |
|----------|-----------------|----------------------|
| **Production (speed-critical)** | Inference_ms, Phase7_MVP_Spearman | Slightly lower DIQA5000_SRCC |
| **Quality-critical** | DIQA5000_SRCC, OCR_CER_Correlation | Higher inference time |
| **Selective inference** | Phase7_MVP_ENCE, Phase7_MVP_MCE | May use teacher for uncertain cases |

### Comparison Checklist

> **Warning**: Do not use `--quick` mode when comparing models. Quick mode skips DIQA-5000, bootstrap CI, and cross-dataset gap—all essential for valid comparison.

- [ ] Both models evaluated on same test splits
- [ ] Both models run in **full mode** (not `--quick`)
- [ ] Bootstrap CI computed for statistical comparison
- [ ] Cross-dataset gap acceptable (< 0.10)
- [ ] Per-head performance reviewed for domain-specific needs
- [ ] OCR correlation validates practical utility
- [ ] Inference time acceptable for deployment

## Example Benchmark Output

```text
============================================================
BENCHMARK SUMMARY
============================================================

Phase7 MVP:
  Macro SRCC: 0.3670
  Macro PLCC: 0.3720
  Macro MAE: 0.2930
  Macro ENCE: 0.1640

DIQA-5000:
  SRCC: 0.4750 (0.4220 - 0.5220)
  PLCC: 0.4160

Cross-Dataset Gap: 0.1080 ⚠️

OCR Correlation (SmartDoc-QA):
  CER Correlation: 0.7200 ✅
  WER Correlation: 0.6800
  Ranking Agreement: 0.8500

🎉 Benchmark complete!
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "CUDA out of memory" | Batch size too large | Reduce `--batch-size` to 32 or 16 |
| "Dataset not found" | Incorrect path | Verify `--phase7-path` points to correct directory |
| "No model checkpoint found" | Invalid .pt file | Ensure checkpoint contains `state_dict` |
| "SmartDoc-QA not found" | Missing dataset | Mount external drive or skip with `--quick` |
| ENCE shows 0.0 | Empty predictions or labels | Check dataset has valid samples; verify model outputs |

### Performance Tips

1. **Use GPU**: Benchmark runs 10x faster on CUDA
2. **Quick mode first**: Use `--quick` to validate model loads correctly
3. **Batch size tuning**: Larger batches are faster but use more memory
4. **Parallel workers**: Default `num_workers=4` is optimal for most systems

## Related Documentation

- [PROJECT_PLAN.md](../planning/PROJECT_PLAN.md) - Phase 7 training plans
- [IQA_MODEL_BENCHMARK_TRACKER.csv](../../benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv) - Current benchmark results
- [calibration.py](../../src/image_preprocessing_detector/metrics/calibration.py) - Calibration metric implementations
- [run_model_benchmark.py](../../scripts/run_model_benchmark.py) - Benchmark script source
