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

## Current Leaderboard (Overall Quality SRCC)

Rankings use SRCC (Spearman Rank Correlation), the standard metric for VQualA 2025 Challenge.

### Top Performers

| Rank | Model | Type | Overall SRCC | VQualA Score† | Latency |
|------|-------|------|--------------|---------------|---------|
| 🥇 1 | SigLIP2-IQA-Base-86M-v1.0.0 | Fine-tuned | **0.896** | **0.886** | 100ms |
| 🥈 2 | HyperIQA-Plus-Plus-DIQA5000-v1.0.0 | Fine-tuned | **0.860** | **0.856** | 2.9ms |
| 🥉 3 | DeQA-Doc-3Specialists | VLM | **0.733** | 0.711 | ~2000ms‡ |
| 4 | PyIQA-maniqa | Pretrained | 0.526 | 0.544 | 1845ms |
| 5 | DeQA-Score-Mix3-Prompted | VLM | 0.491 | 0.498 | ~2000ms‡ |
| 6 | PyIQA-liqe | Pretrained | 0.403 | 0.429 | 150ms |

†VQualA Score = 0.5×SRCC_overall + 0.25×SRCC_sharpness + 0.25×SRCC_color
‡VLM latency measured on A100 GPU; varies significantly by hardware and configuration.

### Pretrained IQA Models (Baselines)

| Rank | Model | Overall SRCC | 95% CI |
|------|-------|--------------|--------|
| 1 | PyIQA-maniqa | 0.526 | [0.477, 0.567] |
| 2 | PyIQA-liqe | 0.403 | [0.346, 0.459] |
| 3 | PyIQA-dbcnn | 0.288 | [0.227, 0.347] |
| 4 | PyIQA-hyperiqa | 0.236 | [0.172, 0.298] |
| 5 | PyIQA-topiq_nr | 0.176 | [0.114, 0.233] |
| 6 | PyIQA-clipiqa | 0.160 | [0.104, 0.218] |
| 7 | PyIQA-musiq | 0.116 | [0.047, 0.180] |
| 8 | PyIQA-qualiclip | 0.104 | [0.036, 0.165] |

### Notes

- **SigLIP2** and **HyperIQA++** are our fine-tuned models achieving SOTA on DIQA-5000
- **DeQA-Doc** models are VLM-based (7B params) requiring A100-class GPU
- See [DEQA_METHODOLOGY_COMPARISON.md](DEQA_METHODOLOGY_COMPARISON.md) for VLM evaluation methodology

*Last updated: 2026-01-16*
