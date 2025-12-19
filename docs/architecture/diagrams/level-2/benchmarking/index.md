---
schema_type: common
title: "Level 2: Benchmarking"
description: "IQA model benchmarking workflow diagrams for Project A"
tags: [architecture, diagrams, plantuml, level-2, benchmarking]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the IQA model benchmarking pipeline for evaluating model performance."
---

# Level 2: Benchmarking

This level provides detailed diagrams for the Benchmarking workstream - evaluating IQA model performance.

---

## Benchmark Workflow

Complete workflow for running IQA model benchmarks on DIQA-5000.

![Benchmark Workflow](project-a-benchmark-workflow.svg)

---

## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| Arena Benchmark | `modal/arena_benchmark.py` | Multi-model evaluation |
| Benchmark Runner | `scripts/run_model_benchmark.py` | Local benchmark execution |
| Results Analysis | `docs/benchmarks/` | Performance reports |

---

## Benchmark Metrics

| Metric | Description |
|--------|-------------|
| SRCC | Spearman Rank Correlation Coefficient |
| PLCC | Pearson Linear Correlation Coefficient |
| ECE | Expected Calibration Error |
| Latency | Inference time per image |

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Model Training](../model-training/index.md) | Training pipeline |
| **Level 2** | [Pseudo-Labeling](../pseudo-labeling/index.md) | Label generation |
