# Benchmarking Framework

Comprehensive evaluation system for the Image Preprocessing Detector across Phases 1-3.

## Quick Start

```bash
# Install dependencies (if not already installed)
poetry install --with dev

# Generate synthetic IQA test data
python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-smoke

# Run smoke tests (fast CI validation)
python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke

# Run all smoke tests
python -m benchmarks.runners.run_smoke --all
```

## Architecture

```
benchmarks/
├── registry.yml              # Central suite configuration
├── adapters/                 # Dataset adapters
│   ├── base.py              # BaseAdapter interface
│   ├── doclaynet_adapter.py # DocLayNet (layout)
│   └── synthetic_iqa_adapter.py # Synthetic IQA tests
├── metrics/                  # Metric calculations
│   ├── detection_metrics.py # mAP, per-class AP, IoU
│   └── image_metrics.py     # Blur, skew, PSNR, SSIM, etc.
├── scorers/                  # Result aggregation
│   └── aggregate_scorer.py  # Statistics and summaries
├── runners/                  # Execution engines
│   ├── run_benchmark.py     # Full benchmark runner
│   └── run_smoke.py         # Fast CI smoke tests
└── labelmaps/               # Label mappings
    └── omnidoc_to_doclaynet.yaml
```

## Registry Configuration

All benchmark suites are defined in `registry.yml`:

```yaml
suites:
  - name: synthetic-iqa-blur-full
    phase: 1
    task: iqa
    dataset: synthetic_iqa
    subset: blur
    metrics:
      - blur_correlation
      - blur_rmse
    split: test
    smoke_subset: 20  # Use 20 samples for smoke tests
    target:
      correlation: 0.85
      rmse: 0.05
```

## Dataset Adapters

All adapters implement the `BaseAdapter` interface:

```python
from benchmarks.adapters import load_adapter

# Load DocLayNet
adapter = load_adapter(
    "doclaynet",
    data_dir="/data/doclaynet",
    split="val_docwise"
)

# Iterate over samples
for sample in adapter:
    print(sample.image_path, len(sample.annotations))
```

### Available Adapters

| Adapter | Phase | Dataset | License |
|---------|-------|---------|---------|
| `synthetic_iqa` | 1 | Internal | CC0-1.0 |
| `doclaynet` | 1 | DocLayNet | CDLA-Permissive-2.0 |
| `docbank` | 2 | DocBank | CC-BY-4.0 |
| `tablebank` | 2 | TableBank | CC-BY-4.0 |
| `cocotext` | 2 | COCO-Text | CC-BY-4.0 |
| `wili_2018` | 2 | WiLI-2018 | CC-BY-SA-4.0 |
| `omnidocbench` | 3 | OmniDocBench | CC-BY-NC-4.0 (eval-only) |

## Metrics

### Image Quality Assessment (IQA)

Implements FR-3.1 → FR-3.7:

```python
from benchmarks.metrics.image_metrics import (
    blur_correlation,  # Pearson r ≥ 0.85
    blur_rmse,         # RMSE ≤ 0.05
    skew_mae,          # MAE ≤ 0.5°
    deskew_success_rate,  # ≥ 99%
    snr_db,            # SNR improvement ≥ 6 dB
    psnr,              # PSNR ≥ 30 dB
    ssim,              # SSIM ≥ 0.9
    binarization_metrics,  # F-measure ≥ 0.95
)
```

### Layout Detection

```python
from benchmarks.metrics.detection_metrics import (
    calculate_map,     # mAP@[.5:.95]
    calculate_ap,      # Per-class AP
    bbox_iou,          # IoU calculation
    precision_recall_f1,  # Classification metrics
)
```

## Running Benchmarks

### Full Benchmarks

```bash
# Run specific suite
python -m benchmarks.runners.run_benchmark --suite doclaynet-layout-full

# Custom data directory
python -m benchmarks.runners.run_benchmark \
    --suite synthetic-iqa-blur-full \
    --data-dir /path/to/data \
    --output-dir /path/to/reports
```

### Smoke Tests (CI)

```bash
# Single smoke test
python -m benchmarks.runners.run_smoke --suite doclaynet-layout-smoke

# All smoke tests
python -m benchmarks.runners.run_smoke --all

# Expected runtime: < 5 minutes for all smoke tests
```

## Environment Variables

Configure via `.env` or environment:

```bash
export BENCHMARKS_DATA_DIR=/data/benchmarks
export BENCHMARKS_CACHE_DIR=/tmp/benchmarks_cache
export BENCHMARKS_OUTPUT_DIR=/reports
export BENCHMARKS_SEED=42
export HF_TOKEN=your_huggingface_token  # For gated datasets
```

## Output Format

Results are saved to `reports/{suite}/{timestamp}/`:

```
reports/
└── synthetic-iqa-blur-full/
    └── 20251112_143022/
        ├── results.json      # Raw results
        └── summary.md        # Human-readable summary
```

### results.json

```json
{
  "suite_name": "synthetic-iqa-blur-full",
  "task_type": "iqa",
  "timestamp": "2025-11-12T14:30:22",
  "results": [
    {
      "sample_id": "blur_sigma_0.00",
      "metrics": {
        "blur_sigma_gt": 0.0,
        "blur_sigma_pred": 0.0
      }
    }
  ],
  "aggregates": {
    "blur_correlation": {
      "mean": 0.92,
      "std": 0.03,
      "min": 0.87,
      "max": 0.98
    }
  }
}
```

### summary.md

```markdown
# Benchmark Summary: synthetic-iqa-blur-full

**Task**: iqa
**Samples**: 9

## Metrics

| Metric | Mean | Std | Min | Max | Target | Status |
|--------|------|-----|-----|-----|--------|--------|
| blur_correlation | 0.920 | 0.030 | 0.870 | 0.980 | 0.850 | ✓ PASS |
| blur_rmse | 0.042 | 0.008 | 0.030 | 0.055 | 0.050 | ✓ PASS |
```

## Phase Roadmap

### Phase 1 (Current)

- [x] Base adapter interface
- [x] Synthetic IQA adapter (blur, skew, noise, contrast)
- [x] DocLayNet adapter (layout detection)
- [x] Image quality metrics (blur, skew, PSNR, SSIM)
- [x] Detection metrics (mAP, IoU)
- [x] Aggregate scorer
- [x] Benchmark runners (full + smoke)
- [ ] CI integration (GitHub Actions)

### Phase 2 (Planned)

- [ ] TableBank adapter (table detection)
- [ ] FinTabNet adapter (table structure)
- [ ] COCO-Text adapter (handwriting classification)
- [ ] WiLI-2018 adapter (language ID)
- [ ] TEDS scorer (table structure)
- [ ] ML model integration (MobileNetV3, YOLOv8)

### Phase 3 (Planned)

- [ ] OmniDocBench adapter (end-to-end)
- [ ] Composite scoring (layout + text + table + formula)
- [ ] Attribute-sliced evaluation
- [ ] Reading order evaluation
- [ ] Production throughput benchmarks

## CI Integration

### GitHub Actions Workflow

Add to `.github/workflows/benchmarks.yml`:

```yaml
name: Benchmarks

on:
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev
      - name: Run smoke tests
        run: poetry run python -m benchmarks.runners.run_smoke --all
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: smoke-test-results
          path: reports/
```

## Adding New Adapters

1. Create adapter class inheriting from `BaseAdapter`
2. Implement required methods (`__iter__`, `__len__`, `get_sample`, etc.)
3. Register with `@DatasetRegistry.register("name")`
4. Add suite definition to `registry.yml`
5. Add unit tests to `tests/benchmarks/`

Example:

```python
from benchmarks.adapters.base import BaseAdapter, DatasetRegistry, PageSample

@DatasetRegistry.register("my_dataset")
class MyDatasetAdapter(BaseAdapter):
    def __iter__(self):
        # Yield PageSample instances
        pass

    def __len__(self):
        return len(self._sample_ids)

    def get_sample(self, sample_id):
        # Return specific sample
        pass

    @property
    def license(self):
        return "CC-BY-4.0"

    @property
    def split_info(self):
        return {"train": 1000, "val": 200, "test": 200}
```

## Testing

```bash
# Run all benchmark tests
poetry run pytest tests/benchmarks/ -v

# Run specific test file
poetry run pytest tests/benchmarks/test_image_metrics.py -v

# Run with coverage
poetry run pytest tests/benchmarks/ --cov=benchmarks --cov-report=html
```

## Troubleshooting

### Dataset Not Found

```bash
# Set data directory
export BENCHMARKS_DATA_DIR=/path/to/datasets

# Or use --data-dir flag
python -m benchmarks.runners.run_benchmark \
    --suite my-suite \
    --data-dir /path/to/datasets
```

### Missing Dependencies

```bash
# Install with ML dependencies (Phase 2+)
poetry install --with dev,ml

# Check installed packages
poetry show
```

### Synthetic Dataset Generation Fails

```bash
# Regenerate synthetic datasets
rm -rf data/benchmarks/synthetic_iqa
python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-smoke
```

## References

- [DocLayNet Paper](https://arxiv.org/abs/2206.01062)
- [OmniDocBench](https://opendatalab.com/OmniDocBench)
- [COCO Evaluation](https://cocodataset.org/#detection-eval)
- [Project Plan](../PROJECT_PLAN.md)

## License

See `licenses/third_party/` for individual dataset licenses.

Framework code: Apache-2.0
