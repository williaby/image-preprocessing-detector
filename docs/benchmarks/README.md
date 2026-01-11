---
owner: docs-team
purpose: Overview and documentation for DIQA-5000 Benchmark Results.
schema_type: common
status: draft
tags:
- benchmarking
title: DIQA-5000 Benchmark Results
---

This directory contains benchmark results for models evaluated on the DIQA-5000 test set.

## Files

- `diqa5000_benchmark_results.csv` - All benchmark results in CSV format

## CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `model_id` | string | Unique model identifier |
| `model_type` | string | Category: `iqa_cnn`, `iqa_pretrained`, `vlm`, `iqa_finetuned` |
| `benchmark_date` | date | YYYY-MM-DD format |
| `num_samples` | int | Number of test samples evaluated |
| `success_rate` | float | Proportion of successful inferences (0-1) |
| `overall_plcc` | float | Pearson correlation for overall quality |
| `overall_plcc_ci_lower` | float | 95% CI lower bound (bootstrapped) |
| `overall_plcc_ci_upper` | float | 95% CI upper bound (bootstrapped) |
| `overall_srcc` | float | Spearman correlation for overall quality |
| `overall_srcc_ci_lower` | float | 95% CI lower bound (bootstrapped) |
| `overall_srcc_ci_upper` | float | 95% CI upper bound (bootstrapped) |
| `overall_mae` | float | Mean Absolute Error for overall quality |
| `overall_rmse` | float | Root Mean Squared Error for overall quality |
| `sharpness_*` | float | Same metrics for sharpness dimension |
| `color_*` | float | Same metrics for color fidelity dimension |
| `inference_mean_ms` | float | Mean inference time per sample (ms) |
| `inference_total_s` | float | Total inference time (seconds) |
| `model_load_s` | float | Model loading time (seconds) |
| `gpu_type` | string | GPU used: `T4`, `A10`, `A100`, `CPU` |
| `notes` | string | Additional context |

## Model Types

- **iqa_cnn**: ImageNet-pretrained CNN backbones with IQA regression heads (not fine-tuned)
- **iqa_pretrained**: Models pretrained on IQA datasets (MUSIQ, QualiCLIP, NIQE, etc.)
- **iqa_finetuned**: Models fine-tuned on DIQA-5000 or similar document datasets
- **vlm**: Vision-Language Models using prompt-based quality assessment

## Adding New Results

Append new rows to `diqa5000_benchmark_results.csv` with the same column order.

### From Modal Benchmark Runs

```bash
# Run benchmark
uv run modal run -d modal/arena_iqa_benchmark.py::run_resnet50_benchmark

# View logs for results
uv run modal app logs <app-id>

# Manually append to CSV (or automate via script)
```

### Required Fields

All columns must be present. Use empty string for missing optional fields like `notes`.

## Metrics Reference

### Correlation Coefficients

- **PLCC** (Pearson Linear Correlation Coefficient): Measures linear relationship between predictions and ground truth. Range: [-1, 1], higher is better.
- **SRCC** (Spearman Rank Correlation Coefficient): Measures monotonic relationship. Range: [-1, 1], higher is better.

### Error Metrics

- **MAE** (Mean Absolute Error): Average absolute difference. Lower is better.
- **RMSE** (Root Mean Squared Error): Penalizes larger errors more. Lower is better.

### Confidence Intervals

- 95% bootstrapped CIs computed with 1000 iterations
- Seed: 42 for reproducibility
- Minimum 30 samples required for bootstrap

## Current Leaderboard (Overall Quality PLCC)

| Rank | Model | Overall PLCC | 95% CI |
|------|-------|--------------|--------|
| 1 | PyIQA-qualiclip | 0.2216 | [0.144, 0.288] |
| 2 | PyIQA-musiq | 0.2098 | [0.136, 0.275] |
| 3 | ResNet18-ImageNet-IQA | 0.0963 | [0.038, 0.155] |
| 4 | Swin-Tiny-ImageNet-IQA | 0.0474 | [-0.008, 0.099] |
| 5 | ConvNeXt-Tiny-ImageNet-IQA | -0.0330 | [-0.103, 0.031] |
| 6 | ResNet50-ImageNet-IQA | -0.0341 | [-0.098, 0.038] |
| 7 | ResNet34-ImageNet-IQA | -0.0602 | [-0.122, 0.008] |
| 8 | EfficientNet-B4-ImageNet-IQA | -0.1222 | [-0.185, -0.054] |

*Last updated: 2025-12-18*
