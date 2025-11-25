# OmniDocBench Baseline Evaluation Framework

Modular benchmarking framework for evaluating Project A models against OmniDocBench, with versioned result tracking for comparing improvements over baselines.

## Purpose

1. **Establish Baselines**: Measure performance of classical CV and pre-trained models
2. **Track Improvements**: Compare trained models (v1, v2, etc.) against baselines
3. **Version Control**: Maintain history of all benchmark runs with timestamps
4. **Fair Comparison**: Use identical evaluation protocol across all model variants

## Architecture

```
scripts/omnidocbench_baseline/
├── __init__.py                    # Package documentation
├── README.md                      # This file
├── model_registry.yaml            # All model variant configurations
├── benchmark_runner.py            # Main evaluation driver
├── compare_results.py             # Version comparison utility
├── extract_ground_truth.py        # OmniDocBench GT extraction
└── models/
    ├── __init__.py
    ├── base.py                    # Abstract model interfaces
    ├── registry.py                # Model loading and configuration
    └── adapters/
        ├── classical_cv.py        # OpenCV heuristics adapter
        ├── resnet.py              # ResNet IQA adapter
        ├── layout_lite.py         # Layout-lite heuristics adapter
        ├── doclayout_yolo.py      # DocLayout-YOLO adapter [placeholder]
        └── language.py            # Language detection adapter [placeholder]
```

## Registered Models

### IQA Models (Image Quality Assessment)

| Model ID | Type | Description | Status |
|----------|------|-------------|--------|
| `classical_cv_baseline` | Heuristics | OpenCV Laplacian, FFT, histogram | ✅ Active |
| `resnet50_teacher_baseline` | ResNet-50 | ImageNet pre-trained (no IQA training) | ✅ Active |
| `resnet50_teacher_v1` | ResNet-50 | Trained on OHR-Bench (binary labels) | ⏳ Planned |
| `resnet50_teacher_v2` | ResNet-50 | Trained with continuous labels | ⏳ Planned |
| `resnet18_student_baseline` | ResNet-18 | ImageNet pre-trained | ✅ Active |
| `resnet18_student_v1` | ResNet-18 | Distilled from teacher_v1 | ⏳ Planned |
| `resnet18_student_v2` | ResNet-18 | Distilled from teacher_v2 | ⏳ Planned |

### Layout Models

| Model ID | Type | Description | Status |
|----------|------|-------------|--------|
| `layout_lite_baseline` | Heuristics | Column/table/figure detection | ✅ Active |
| `doclayout_yolo_docstructbench` | YOLO | DocStructBench pre-trained | ⏳ Planned |
| `doclayout_yolo_d4la` | YOLO | D4LA + DocSynth300K | ⏳ Planned |

## Usage

### Run Benchmarks

```bash
# Single model evaluation
python scripts/omnidocbench_baseline/benchmark_runner.py --model classical_cv_baseline

# Multiple models
python scripts/omnidocbench_baseline/benchmark_runner.py \
    --models classical_cv_baseline,resnet18_student_baseline

# Model group
python scripts/omnidocbench_baseline/benchmark_runner.py --group all_iqa_baselines

# Limited samples (for testing)
python scripts/omnidocbench_baseline/benchmark_runner.py --model classical_cv_baseline --limit 100

# List available models
python scripts/omnidocbench_baseline/benchmark_runner.py --list-models
```

### Compare Results

```bash
# Compare baseline vs trained model
python scripts/omnidocbench_baseline/compare_results.py \
    --baseline classical_cv_baseline \
    --compare resnet18_student_v1

# Track version progression
python scripts/omnidocbench_baseline/compare_results.py \
    --progression resnet18_student

# Generate markdown report
python scripts/omnidocbench_baseline/compare_results.py \
    --baseline classical_cv_baseline \
    --compare resnet18_student_v1 \
    --output-format markdown \
    --output docs/benchmarks/comparison_report.md
```

### Example Workflow: Training Improvement Tracking

```bash
# 1. Establish baseline (before training)
python scripts/omnidocbench_baseline/benchmark_runner.py \
    --models classical_cv_baseline,resnet18_student_baseline

# 2. After training v1 model, run benchmark
python scripts/omnidocbench_baseline/benchmark_runner.py --model resnet18_student_v1

# 3. Compare improvement
python scripts/omnidocbench_baseline/compare_results.py \
    --baseline resnet18_student_baseline \
    --compare resnet18_student_v1

# 4. After training v2 (continuous labels), benchmark
python scripts/omnidocbench_baseline/benchmark_runner.py --model resnet18_student_v2

# 5. Track full progression
python scripts/omnidocbench_baseline/compare_results.py \
    --progression resnet18_student
```

## Output Format

### Benchmark Results (`docs/benchmarks/omnidocbench_results/`)

```json
{
  "model": {
    "id": "resnet18_student_v1",
    "name": "ResNet-18 Student v1",
    "version": "1.0.0",
    "type": "resnet"
  },
  "metadata": {
    "timestamp": "2025-01-25T10:30:00",
    "processed": 1358,
    "errors": 0,
    "elapsed_seconds": 245.3
  },
  "binary_attributes": {
    "fuzzy_scan": {"precision": 0.85, "recall": 0.82, "f1": 0.83},
    "watermark": {"precision": 0.90, "recall": 0.75, "f1": 0.82}
  },
  "correlations": {
    "fuzzy_scan_score_correlation": 0.72
  },
  "summary": {
    "mean_f1": 0.83
  }
}
```

### Comparison Report

```
==========================================================================================
COMPARISON: ResNet-18 Student (Baseline) (v0.0.0) → ResNet-18 Student v1 (v1.0.0)
==========================================================================================

Binary Attribute Detection:
------------------------------------------------------------------------------------------
Attribute                   Baseline    Current      Delta   Relative   Target
------------------------------------------------------------------------------------------
fuzzy_scan                      0.450      0.830     ↑0.380    +84.4%   ✅0.85
watermark                       0.520      0.820     ↑0.300    +57.7%   ❌0.85
colorful_background             0.600      0.870     ↑0.270    +45.0%   ✅0.85

Summary:
------------------------------------------------------------------------------------------
  Mean F1: 0.523 → 0.840 (↑0.317)
  Improvements: 5 | Regressions: 0
  Target Met: ✅ (>= 0.80)
==========================================================================================
```

## Project A Targets

| Attribute | F1 Target | Notes |
|-----------|-----------|-------|
| `fuzzy_scan` | ≥ 0.85 | Core IQA attribute |
| `watermark` | ≥ 0.85 | Page attribute |
| `colorful_background` | ≥ 0.85 | Page attribute |
| `has_tables` | ≥ 0.85 | Element presence |
| `has_figures` | ≥ 0.85 | Element presence |
| `layout_type` | ≥ 0.80 (accuracy) | Layout classification |
| Overall Mean F1 | ≥ 0.80 | Summary metric |

## OmniDocBench to Project A Mapping

### Layout Type Mapping

| OmniDocBench | Project A |
|--------------|-----------|
| `single_column` | `single_column` |
| `double_column` | `multi_column` |
| `three_column` | `three_column` |
| `1andmore_column` | `complex` |
| `other_layout` | `complex` |

### Page Attributes

| OmniDocBench | Project A | Notes |
|--------------|-----------|-------|
| `fuzzy_scan` | `fuzzy_scan` | Direct mapping |
| `watermark` | `watermark` | Direct mapping |
| `colorful_backgroud` | `colorful_background` | Note: OmniDocBench has typo |

### Element Presence (Derived)

| Condition | Project A Flag |
|-----------|----------------|
| `table` blocks > 0 | `has_tables` |
| `figure` blocks > 0 | `has_figures` |
| `equation_isolated` blocks >= 3 | `has_dense_math` |

## Adding New Models

1. **Define in registry** (`model_registry.yaml`):
```yaml
- id: my_new_model_v1
  name: "My New Model v1"
  version: "1.0.0"
  type: resnet  # or classical_cv, yolo, etc.
  config:
    architecture: resnet18
    checkpoint: "models/my_new_model_v1.pth"
  benchmarkable_attributes:
    - fuzzy_scan
```

2. **Run benchmark**:
```bash
python scripts/omnidocbench_baseline/benchmark_runner.py --model my_new_model_v1
```

3. **Compare to baseline**:
```bash
python scripts/omnidocbench_baseline/compare_results.py \
    --baseline resnet18_student_baseline \
    --compare my_new_model_v1
```

## Requirements

```bash
# Core dependencies
poetry install --with dev

# For ML models (ResNet, etc.)
poetry install --with dev,ml

# HuggingFace token for dataset access
export HF_TOKEN=hf_xxx
```

## Related Files

- `benchmarks/registry.yml` - Benchmark suite configuration
- `scripts/validate_layout_lite.py` - Layout-lite validation script
- `src/image_preprocessing_detector/detection/layout_lite/` - Detection implementations
- `docs/development/RAG Pipeline/MODELS.md` - Model architecture documentation
