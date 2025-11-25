# OmniDocBench Baseline Evaluation

Baseline evaluation scripts for Project A against OmniDocBench benchmark.

## Purpose

Establish baseline performance metrics for Project A's layout-lite detectors before any training. This provides a reference point for measuring improvements as models are trained.

## Evaluation Scope

### In Scope (Project A)

| Category | Attributes | Metric |
|----------|------------|--------|
| Page Attributes | `fuzzy_scan`, `watermark`, `colorful_background` | Binary F1 |
| Layout Classification | single/multi/three-column, complex | Accuracy, Macro F1 |
| Element Presence | `has_tables`, `has_figures`, `has_dense_math` | Binary F1 |

### Out of Scope (Project B)

- Text/OCR recognition (NED, BLEU, METEOR)
- Table structure extraction (TEDS)
- Formula recognition (CDM)
- Reading order

## Usage

### Quick Start (HuggingFace)

```bash
# Ensure HF_TOKEN is set
export HF_TOKEN=hf_xxx

# Run evaluation (will download dataset)
python scripts/omnidocbench_baseline/run_baseline_evaluation.py

# Limit samples for testing
python scripts/omnidocbench_baseline/run_baseline_evaluation.py --limit 100
```

### Two-Step Workflow (Pre-extracted)

```bash
# Step 1: Extract ground truth (one-time)
python scripts/omnidocbench_baseline/extract_ground_truth.py \
    --output data/omnidocbench_baseline/layout_labels.json

# Step 2: Run evaluation
python scripts/omnidocbench_baseline/run_baseline_evaluation.py \
    --ground-truth data/omnidocbench_baseline/layout_labels.json \
    --images data/omnidocbench_baseline/images/
```

## Output

Results are saved to `docs/benchmarks/omnidocbench_baseline/`:

- `baseline_evaluation_results.json` - Full metrics in JSON format
- `baseline_evaluation_report.md` - Human-readable markdown report

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

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Binary Flag F1 | ≥ 0.85 | Per-attribute |
| Layout Accuracy | ≥ 0.80 | Overall |
| Mean F1 | ≥ 0.80 | Across all flags |

## Requirements

```bash
# Install dependencies
poetry install --with dev,ml

# Or pip
pip install datasets huggingface-hub scikit-learn numpy opencv-python
```

## Related Files

- `benchmarks/registry.yml` - Benchmark suite configuration
- `scripts/validate_layout_lite.py` - Layout-lite validation script
- `src/image_preprocessing_detector/detection/layout_lite/` - Detection implementations
