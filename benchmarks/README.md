<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: CC0-1.0
-->

# Benchmarking Framework

> **What's Here**: Benchmark framework code (runners, adapters, metrics, configuration)
> **Dataset Files**: See [data/benchmarks/](../data/benchmarks/) for actual dataset storage

Comprehensive evaluation system for the Image Preprocessing Detector across Phases 1-3.

## Directory Purpose

**This directory (`benchmarks/`) contains benchmark infrastructure code:**

- Python modules for running benchmarks (`runners/`, `adapters/`, `metrics/`)
- Configuration registry (`registry.yml`) defining all benchmark suites
- Result aggregation and reporting tools (`scorers/`, `reports/`)
- Documentation for the benchmarking framework

**For actual dataset files**, see [data/benchmarks/](../data/benchmarks/) (~98GB total: ~56GB local + 42GB DocLayNet symlink, gitignored).

## Quick Start

```bash
# Install dependencies (if not already installed)
uv sync --extra dev

# Generate synthetic IQA test data
python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-smoke

# Run smoke tests (fast CI validation)
python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke

# Run all smoke tests
python -m benchmarks.runners.run_smoke --all
```text

## Architecture

**Framework Structure** (this directory):

```text
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
```text

**Dataset Storage** (separate location):

```text
data/benchmarks/             # Actual dataset files (~98GB total, gitignored)
├── doclaynet/              # Layout detection (42GB, symlinked to data_ingestor)
├── tablebank/              # Table detection (27GB, 424K images)
├── pubtabnet/              # Table structure (14GB, 500K images)
├── diqa-5000/              # Document IQA (5.4GB, 5.5K images)
├── fintabnet/              # Financial tables (5.3GB)
├── ohr-bench/              # OCR handwriting benchmark (1.8GB, 8.5K pages)
├── omnidocbench/           # Multi-domain comprehensive (1.2GB)
├── funsd_plus/             # Enhanced form understanding (500MB, 1.1K samples)
├── signatr6k/              # Handwriting detection (153MB, 6K samples)
├── wili_2018/              # Language detection (129MB, 235K samples)
├── cocotext/               # Text detection (53MB)
└── synthetic_iqa/          # Auto-generated test images (372KB)
```text

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
```text

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
```text

### Available Adapters

| Adapter | Phase | Dataset | License |
|---------|-------|---------|---------|
| `synthetic_iqa` | 1 | Internal | CC0-1.0 |
| `doclaynet` | 1 | DocLayNet | CDLA-Permissive-2.0 |
| `docbank` | 2 | DocBank | CC-BY-4.0 |
| `tablebank` | 2 | TableBank | CC-BY-4.0 |
| `pubtabnet` | 2 | PubTabNet | CDLA-Permissive-2.0 |
| `fintabnet` | 2 | FinTabNet | CDLA-Permissive-2.0 |
| `cocotext` | 2 | COCO-Text | CC-BY-4.0 |
| `wili_2018` | 2 | WiLI-2018 | CC-BY-SA-4.0 |
| `omnidocbench` | 3 | OmniDocBench | CC-BY-NC-4.0 (non-commercial) |

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
```text

### Layout Detection

```python
from benchmarks.metrics.detection_metrics import (
    calculate_map,     # mAP@[.5:.95]
    calculate_ap,      # Per-class AP
    bbox_iou,          # IoU calculation
    precision_recall_f1,  # Classification metrics
)
```text

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
```text

### Smoke Tests (CI)

```bash
# Single smoke test
python -m benchmarks.runners.run_smoke --suite doclaynet-layout-smoke

# All smoke tests
python -m benchmarks.runners.run_smoke --all

# Expected runtime: < 5 minutes for all smoke tests
```text

## Environment Variables

Configure via `.env` or environment:

```bash
export BENCHMARKS_DATA_DIR=/data/benchmarks
export BENCHMARKS_CACHE_DIR=/tmp/benchmarks_cache
export BENCHMARKS_OUTPUT_DIR=/reports
export BENCHMARKS_SEED=42
export HF_TOKEN=your_huggingface_token  # For gated datasets

# GCS Integration (for Colab training)
export GCP_SA_KEY=base64_encoded_service_account_json
export GCP_PROJECT=image-detection-478105
export GCS_BUCKET=gs://image_detection_b/
```text

## Output Format

Results are saved to `reports/{suite}/{timestamp}/`:

```text
reports/
└── synthetic-iqa-blur-full/
    └── 20251112_143022/
        ├── results.json      # Raw results
        └── summary.md        # Human-readable summary
```text

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
```text

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
```text

## GCS Integration for Colab Training

The project supports Google Cloud Storage for dataset sharing with Google Colab:

### Setup

```bash
# Authenticate with GCS
./scripts/auth_gcs.sh --cleanup

# Upload datasets to GCS
./scripts/gcs_helpers.sh upload-phase2

# Download datasets from GCS (in Colab)
./scripts/gcs_helpers.sh download-phase2
```text

### Available Commands

- `list` - List GCS bucket contents
- `info` - Show storage usage and costs
- `upload-configs` - Upload training configs
- `upload-phase2` - Upload Phase 2 datasets (~10GB)
- `download-phase2` - Download Phase 2 datasets from GCS
- `sync-checkpoints phase2` - Sync model checkpoints to GCS
- `download-checkpoints phase2` - Download checkpoints from GCS
- `upload-models phase2` - Upload final trained models

See [docs/DATASET_INSTALLATION.md](../docs/DATASET_INSTALLATION.md) for complete GCS setup guide.

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
```text

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
```text

## Testing

```bash
# Run all benchmark tests
poetry run pytest tests/benchmarks/ -v

# Run specific test file
poetry run pytest tests/benchmarks/test_image_metrics.py -v

# Run with coverage
poetry run pytest tests/benchmarks/ --cov=benchmarks --cov-report=html
```text

## Testing with Fixtures

For local development and CI/CD, use small test fixtures instead of full datasets:

### Test Fixtures vs Full Datasets

| Approach | Size | Use Case | Location |
|----------|------|----------|----------|
| **Test Fixtures** | 828KB | Local dev, CI/CD | `data/test_fixtures/` (committed) |
| **Smoke Tests** | Varies | Quick validation | Dataset subsets (20-100 samples) |
| **Full Benchmarks** | 88+ GB | Production validation | `data/benchmarks/` (gitignored) |

### Available Test Fixtures

```bash
# Check what's available
ls -lh data/test_fixtures/

# Current fixtures:
# - doclaynet/   432KB (5 PDFs)
# - tablebank/   324KB (5 images)
# - wili_2018/   52KB (10 text files)
# - iqa_samples/ ~2MB (planned for Phase 2)
```text

### Running Tests with Fixtures

```bash
# Unit tests (use synthetic data + fixtures)
poetry run pytest tests/unit/ -v

# Integration tests (use test fixtures)
poetry run pytest tests/integration/ -v -m "not requires_full_dataset"

# Smoke tests (use dataset subsets - requires downloads)
poetry run python -m benchmarks.runners.run_smoke --all
```text

### Benefits

- ✅ **No dataset downloads**: Work offline with 828KB fixtures
- ✅ **Fast CI/CD**: Tests complete in <5 minutes
- ✅ **Reproducible**: Same fixtures across all environments
- ✅ **Version controlled**: Fixtures committed to repository

See [data/test_fixtures/README.md](../data/test_fixtures/README.md) for details.

## Troubleshooting

### Dataset Not Found

```bash
# Option 1: Use test fixtures (recommended for local dev)
# No download needed - fixtures committed to repository
poetry run pytest -v -m "not requires_full_dataset"

# Option 2: Download datasets locally
poetry run python scripts/download_table_datasets.py --all
poetry run python scripts/download_omnidocbench.py

# Option 3: Set custom data directory
export BENCHMARKS_DATA_DIR=/path/to/datasets

# Option 4: Use --data-dir flag
python -m benchmarks.runners.run_benchmark \
    --suite my-suite \
    --data-dir /path/to/datasets

# Option 5: Use GCS-stored datasets (Colab)
# See docs/DATASET_INSTALLATION.md for GCS setup
```text

### Missing Dependencies

```bash
# Install with all dependencies (includes HuggingFace Hub)
poetry install --with dev

# Install with ML dependencies (Phase 2+)
poetry install --with dev,ml

# Check installed packages
poetry show

# Verify HuggingFace Hub available
poetry run python -c "import huggingface_hub; print(huggingface_hub.__version__)"
```text

### Synthetic Dataset Generation Fails

```bash
# Regenerate synthetic datasets
rm -rf data/benchmarks/synthetic_iqa
python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-smoke
```text

## Benchmark Results & Comparisons

### Current Status

![Phase](https://img.shields.io/badge/Phase-1%20Complete-success)
![IQA](https://img.shields.io/badge/IQA%20Metrics-Implemented-blue)
![Layout](https://img.shields.io/badge/Layout%20Detection-Pending%20ML-yellow)
![Coverage](https://img.shields.io/badge/Test%20Coverage-80%2B%25-brightgreen)

**Last Updated**: 2025-11-12 | **Framework Version**: 1.0.0

### Quick Metrics Summary

| Category | Metric | Target | Current | Status |
|----------|--------|--------|---------|--------|
| **IQA - Blur** | Correlation (Pearson r) | ≥ 0.85 | TBD | 🔄 |
| **IQA - Blur** | RMSE | ≤ 0.05 | TBD | 🔄 |
| **IQA - Skew** | MAE (degrees) | ≤ 0.5° | TBD | 🔄 |
| **IQA - Deskew** | Success Rate | ≥ 99% | TBD | 🔄 |
| **IQA - Noise** | SNR Improvement | ≥ 6.0 | TBD | 🔄 |
| **IQA - Quality** | PSNR | ≥ 30.0 | TBD | 🔄 |
| **IQA - Quality** | SSIM | ≥ 0.9 | TBD | 🔄 |
| **IQA - Binarization** | F-measure | ≥ 0.95 | TBD | 🔄 |
| **Layout Detection** | mAP@[.5:.95] (DocLayNet) | ≥ 0.8 | TBD | ⏳ |
| **Layout Detection** | Per-class AP | — | TBD | ⏳ |

<sub>*Synthetic IQA benchmarks ready; awaiting Phase 1 detector integration</sub>
<sub>**Requires YOLOv8 model training (Phase 2)</sub>

### Comparison with State-of-the-Art Tools

Based on [OmniDocBench](https://arxiv.org/abs/2412.07626) and related benchmarks:

#### Layout Detection (DocLayNet val_docwise)

| Tool/Model | mAP@[.5:.95] | mAP@.50 | mAP@.75 | Reference |
|------------|--------------|---------|---------|-----------|
| **Mask R-CNN R50** (baseline) | 0.72 | — | — | DocLayNet 2022 |
| **Our Target** | **≥ 0.80** | **≥ 0.85** | **≥ 0.75** | Phase 2 |
| Our Current | TBD | TBD | TBD | ⏳ Pending ML |

#### Table Detection & Structure

| Tool | Detection F1 | Structure TEDS | Dataset | Reference |
|------|-------------|----------------|---------|-----------|
| **ICDAR 2019 Baseline** | 0.94 | — | ICDAR-2019 | Competition |
| **GTE (WACV 2021)** | — | 0.93 | PubTabNet | Table Extractor |
| **GTE (Finetuned)** | — | 0.91 | FinTabNet | Table Extractor |
| **Our Target** | **≥ 0.90** | **≥ 0.90** | Multi-dataset | Phase 2 |
| Our Current | TBD | TBD | — | ⏳ Pending ML |

#### OmniDocBench End-to-End (Phase 3)

Comparison with commercial and open-source document AI tools:

| Tool | Layout mAP | Text NED↓ | Table TEDS | Formula CDM | Composite | License |
|------|------------|-----------|------------|-------------|-----------|---------|
| **Marker** | 0.387 | 0.226 | 0.691 | 0.581 | 73.38 | Apache-2.0 |
| **Docling** | 0.447 | 0.171 | 0.762 | 0.640 | 77.82 | MIT |
| **MinerU** | 0.423 | 0.151 | 0.737 | 0.618 | 77.66 | AGPL-3.0 |
| **Mathpix** | 0.418 | **0.103** | **0.810** | **0.787** | **82.65** | Commercial |
| **GPT-4o** | 0.382 | 0.134 | 0.681 | 0.548 | 76.45 | Commercial |
| **Our Target** | **≥ 0.82** | **≤ 0.10** | **≥ 0.90** | **≥ 0.85** | **≥ 85.0** | Apache-2.0 |
| **Our Current** | TBD | TBD | TBD | TBD | TBD | ⏳ Phase 3 |

<sub>↓ Lower is better (Normalized Edit Distance)</sub>
<sub>Source: [OmniDocBench Paper](https://arxiv.org/abs/2412.07626), Table 2</sub>

#### Attribute-Sliced Performance (OmniDocBench)

Performance variation by document attributes (targets for Phase 3):

| Attribute | Category | Our Target | Baseline (Docling) |
|-----------|----------|------------|--------------------|
| **Data Source** | Academic | ≥ 0.80 | 0.77 |
| | Financial | ≥ 0.75 | 0.72 |
| | News | ≥ 0.82 | 0.79 |
| **Layout** | Single Column | ≥ 0.85 | 0.81 |
| | Double Column | ≥ 0.78 | 0.74 |
| **Language** | English | ≥ 0.85 | 0.82 |
| | Chinese | ≥ 0.80 | 0.76 |
| **Quality Flags** | Watermark | ≥ 0.75 | 0.68 |
| | Fuzzy Scan | ≥ 0.70 | 0.64 |
| | Colorful BG | ≥ 0.73 | 0.69 |

#### Handwriting vs Printed Classification

| Tool/Method | F1 Score | ROC-AUC | Dataset | Reference |
|-------------|----------|---------|---------|-----------|
| **COCO-Text (dataset support)** | — | — | 63K images | Veit et al. 2016 |
| **Our Target** | **≥ 0.90** | **≥ 0.95** | COCO-Text | Phase 2 |
| Our Current | TBD | TBD | — | ⏳ Pending ML |

#### Language Identification

| Method | Accuracy | Dataset | Languages | Reference |
|--------|----------|---------|-----------|-----------|
| **fastText** | ~0.98 | WiLI-2018 | 235 | Thoma 2018 |
| **ICDAR MLT (Script)** | 0.95 (recall) | MLT-2019 | 10 scripts | Competition |
| **Our Target** | **≥ 0.98** | WiLI-2018 | 235 | Phase 2 |
| Our Current | TBD | — | — | ⏳ Pending ML |

### Throughput Benchmarks

Target performance metrics (Phase 4):

| Configuration | Pages/Sec | Latency P50 | Latency P95 | Notes |
|---------------|-----------|-------------|-------------|-------|
| **GPU (T4)** | ≥ 6.0 | <100ms | <150ms | With YOLOv8 + MobileNetV3 |
| **CPU (8-core)** | ≥ 0.5 | <2s | <5s | Fallback mode |
| **Batch (GPU)** | ≥ 33 dpm | — | — | Document-wise processing |

Current: TBD (⏳ Pending Phase 4 production hardening)

### How to Run Benchmarks

```bash
# Run synthetic IQA benchmarks (available now)
python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full

# Full suite with all metrics (when datasets available)
python -m benchmarks.runners.run_smoke --all

# Generate latest comparison table
python -m benchmarks.runners.aggregate --format markdown
```text

### Detailed Results

Full benchmark results are stored in `reports/` after each run:

```text
reports/
├── synthetic-iqa-blur-full/
│   └── 20251112_143022/
│       ├── results.json      # Raw metrics
│       └── summary.md        # Formatted report
├── doclaynet-layout-full/
│   └── [timestamp]/
└── aggregate.csv             # Cross-suite comparison
```text

**Live Dashboard**: TBD (GitHub Pages planned for Phase 4)

### Paper Baselines by Task

For complete baseline references, see:

- **Layout**: [DocLayNet](https://arxiv.org/abs/2206.01062) (2022)
- **Tables**: [GTE](https://openaccess.thecvf.com/content/WACV2021/papers/Zheng_Global_Table_Extractor_GTE_A_Framework_for_Joint_Table_Identification_WACV_2021_paper.pdf) (WACV 2021)
- **Text**: [COCO-Text](https://arxiv.org/abs/1601.07140) (2016)
- **Language**: [WiLI-2018](https://arxiv.org/abs/1801.07779) (2018)
- **End-to-End**: [OmniDocBench](https://arxiv.org/abs/2412.07626) (2024)

## References

- [DocLayNet Paper](https://arxiv.org/abs/2206.01062) - Layout detection baseline
- [OmniDocBench Paper](https://arxiv.org/abs/2412.07626) - Comprehensive benchmark
- [GTE Paper](https://openaccess.thecvf.com/content/WACV2021/papers/Zheng_Global_Table_Extractor_GTE_A_Framework_for_Joint_Table_Identification_WACV_2021_paper.pdf) - Table extraction
- [COCO Evaluation](https://cocodataset.org/#detection-eval) - Detection metrics
- [Marker GitHub](https://github.com/VikParuchuri/marker) - Open-source document AI
- [Docling GitHub](https://github.com/DS4SD/docling) - IBM document processing
- [Project Plan](../docs/planning/PROJECT_PLAN.md) - Full development roadmap

## GCS Integration

Benchmark datasets are **NOT uploaded to GCS** due to size (~101 GB) and cost constraints.

**Rationale**:

- Benchmarks run locally on development machines
- Too expensive for cloud storage ($2.02/month at $0.020/GB/month)
- Can re-download from original sources if needed

**Training data GCS strategy**: See [docs/DATASET_LOCATIONS.md](../docs/DATASET_LOCATIONS.md#google-cloud-storage-gcs-paths) and [scripts/gcs_helpers.sh](../scripts/gcs_helpers.sh).

## Related Documentation

### Architecture Decisions

- [ADR-031: Comprehensive Benchmarking Framework](../docs/ADRs/0031-comprehensive-benchmarking-framework.md) - Design rationale and architecture
- [ADR-029: Three-Tier Dataset Strategy](../docs/ADRs/0029-phase2-dataset-selection-strategy.md) - Dataset organization (Storage Tiers)

### Dataset Documentation

- [docs/DATASET_LOCATIONS.md](../docs/DATASET_LOCATIONS.md) - Complete dataset inventory, sizes, and locations
- [data/benchmarks/README.md](../data/benchmarks/README.md) - Dataset file storage details
- [docs/reference/document-type-coverage.md](../docs/reference/document-type-coverage.md) - FR coverage matrix
- [docs/reference/detection-taxonomy.md](../docs/reference/detection-taxonomy.md) - Complete detection taxonomy

### Installation & Usage

- [docs/guides/dataset-installation.md](../docs/guides/dataset-installation.md) - Dataset installation guide
- [docs/references/CITATIONS.md](../docs/references/CITATIONS.md) - Citation information

## License

See `licenses/third_party/` for individual dataset licenses.

Framework code: Apache-2.0
