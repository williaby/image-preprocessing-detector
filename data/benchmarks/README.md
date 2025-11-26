# Benchmark Datasets

> **What's Here**: Actual dataset files (images, PDFs, annotations) - ~105GB total (63GB local + 42GB DocLayNet symlink)
> **Framework Code**: See [benchmarks/](../../benchmarks/) for benchmark runners and metrics

This directory contains datasets used for benchmarking and training the Image Preprocessing Detector.

**⚠️ All datasets are gitignored** (too large for GitHub) and must be downloaded locally.

## Directory Purpose

**This directory (`data/benchmarks/`) contains actual dataset files:**

- Raw images, PDFs, and document scans
- Ground truth annotations (COCO format, bounding boxes, labels)
- Synthetic test data (auto-generated)
- Dataset metadata and splits

**For benchmark framework code** (runners, adapters, metrics), see [benchmarks/](../../benchmarks/).

## Quick Reference

| Dataset | Status | Size | Phase | Use Case |
|---------|--------|------|-------|----------|
| **Synthetic IQA** | ✅ Auto-generated | 364KB | 1 | Blur, skew, noise, contrast testing |
| **DocLayNet** | ✅ Symlinked | 42GB | 1 | Layout detection (→ data_ingestor/data/benchmarks/doclaynet) |
| **SignaTR6K** | ✅ Downloaded | 153MB | 2 | Handwriting detection (6K samples) |
| **COCO-Text** | ✅ Downloaded | 53MB | 2 | Text detection and recognition |
| **DIQA-5000** | ✅ Downloaded | 5.4GB | 2 | Document IQA with quality annotations (5.5K images) |
| **FUNSD+** | ✅ Downloaded | 500MB | 2 | Enhanced form understanding (1,113 samples) |
| **OHR-Bench** | ✅ Downloaded | 1.8GB | 2 | OCR handwriting recognition benchmark (8.5K pages) |
| **OmniDocBench** | ✅ Downloaded | 1.2GB | 3 | Comprehensive document understanding |
| **TableBank** | ✅ Downloaded | 27GB | 2 | Table detection (424K images) |
| **PubTabNet** | ✅ Downloaded | 14GB | 2 | Table structure recognition (500K images) |
| **FinTabNet** | ✅ Downloaded | 5.3GB | 2 | Financial table detection |
| **WiLI-2018** | ✅ Downloaded | 129MB | 2 | Language identification (235K samples) |

**Total Space Required**: ~63GB (excluding symlinked DocLayNet)

## Installation

**Complete installation guide**: See [docs/DATASET_INSTALLATION.md](../../docs/DATASET_INSTALLATION.md)

### Quick Setup (Automated)

```bash
# Download all benchmark datasets (automated)
poetry run python scripts/download_all_datasets.py --all

# Create local symlinks to NFS storage
poetry run python scripts/create_symlinks.py --all

# Verify installation
poetry run python scripts/create_symlinks.py --verify

# Generate synthetic IQA test data (auto-generated on benchmark runs)
poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke
```text

**Note**: All datasets are automatically downloaded to NFS storage at `/mnt/unraid/training_data/image_detection/benchmarks/` and symlinked to local `data/benchmarks/` for fast access.

## Directory Structure

```text
data/benchmarks/
├── README.md                          # This file
├── doclaynet/                         # ✅ Symlinked (42GB)
│   ├── documents/
│   └── ground_truth/
├── diqa-5000/                         # ✅ Downloaded (5.4GB)
│   ├── train/ori/ (3.8GB)
│   ├── val/ori/ (470MB)
│   └── test/ori/ (1.1GB)
├── funsd_plus/                        # ✅ Downloaded (500MB)
│   ├── train/ (1,030 samples)
│   └── test/ (113 samples)
├── ohr-bench/                         # ✅ Downloaded (1.8GB)
├── signatr6k/                         # ✅ Downloaded (153MB)
├── synthetic_iqa/                     # ✅ Auto-generated (364KB)
│   ├── blur/
│   ├── skew/
│   ├── noise/
│   ├── contrast/
│   └── binarization/
├── cocotext/                          # ✅ Downloaded (53MB)
│   └── cocotext.v2.json
├── omnidocbench/                      # ✅ Downloaded (1.2GB)
├── tablebank/                         # ✅ Downloaded (27GB, 424K images)
├── pubtabnet/                         # ✅ Downloaded (14GB, 500K images)
├── fintabnet/                         # ✅ Downloaded (5.3GB)
└── wili_2018/                         # ✅ Downloaded (129MB)
```text

## Gitignore Configuration

**All datasets are gitignored** via rule in `.gitignore`:

```gitignore
# Line 119
data/benchmarks/
```text

Only this README file is tracked in git (forced with `git add -f`).

## License Compliance

### Must Cite in Publications

- DocLayNet (CDLA-Permissive-2.0)
- TableBank, COCO-Text (CC-BY-4.0)
- PubTabNet, FinTabNet (CDLA-Permissive-2.0)
- WiLI-2018 (CC-BY-SA-4.0)
- OmniDocBench, OHR-Bench (CC-BY-NC-4.0)
- DIQA-5000, SignaTR6K (Research/Academic)
- FUNSD+ (Other - check HuggingFace)

### Commercial Use Restrictions

- ⚠️ **OmniDocBench, OHR-Bench**: Non-commercial evaluation only (CC-BY-NC-4.0)
- ⚠️ **DIQA-5000, SignaTR6K, FUNSD+**: Research purposes (check licenses before commercial use)
- ✅ **All others**: Commercial use allowed with attribution

## Troubleshooting

### Dataset not found error

```bash
# Check dataset exists
ls -R doclaynet/ | head -20

# Regenerate synthetic datasets
rm -rf synthetic_iqa/
poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke
```text

### HuggingFace rate limit (429 error)

```bash
# Login with HF account
poetry run huggingface-cli login
```text

### Disk space full

```bash
# Check space
df -h

# Remove optional datasets or old results
rm -rf ../reports/*/$(ls -t ../reports/*/ | tail -n +2)
```text

## Cloud Storage Strategy

**This directory is LOCAL ONLY** - benchmarks are NOT uploaded to GCS due to size (~101 GB) and cost.

**Rationale**:

- Too large for cost-effective cloud storage ($2.02/month @ $0.020/GB/month)
- Benchmarks run locally on development machines (not in Colab)
- Can re-download from HuggingFace/external sources if needed

**Training data GCS uploads**: Small datasets (<1 GB) uploaded selectively for Colab training. See [docs/DATASET_LOCATIONS.md](../../docs/DATASET_LOCATIONS.md#google-cloud-storage-gcs-paths).

**GCS Helper Scripts**: [scripts/gcs_helpers.sh](../../scripts/gcs_helpers.sh) for selective uploads/downloads.

## See Also

### Benchmark Framework (Code)

- **[benchmarks/README.md](../../benchmarks/README.md)** - Framework overview (runners, adapters, metrics)
- **[benchmarks/registry.yml](../../benchmarks/registry.yml)** - Benchmark suite definitions and configuration

### Architecture Decisions

- **[ADR-029: Three-Tier Dataset Strategy](../../docs/ADRs/0029-phase2-dataset-selection-strategy.md)** - Storage organization (Storage Tiers)
- **[ADR-031: Comprehensive Benchmarking Framework](../../docs/ADRs/0031-comprehensive-benchmarking-framework.md)** - Evaluation framework (Validation Levels)

### Dataset Documentation

- **[docs/DATASET_LOCATIONS.md](../../docs/DATASET_LOCATIONS.md)** - Complete dataset inventory, sizes, and GCS paths
- **[docs/reference/document-type-coverage.md](../../docs/reference/document-type-coverage.md)** - FR coverage matrix
- **[docs/reference/detection-taxonomy.md](../../docs/reference/detection-taxonomy.md)** - Complete detection taxonomy

### Installation & Documentation

- **[docs/guides/dataset-installation.md](../../docs/guides/dataset-installation.md)** - Complete dataset installation guide
- **[docs/references/CITATIONS.md](../../docs/references/CITATIONS.md)** - Complete citation information for all datasets

---

**Last Updated**: 2025-11-20
**Datasets Gitignored**: Yes (all except this README)
**Datasets Downloaded**: 12/12 (100% complete)
**Total Size**: ~105GB (63GB local + 42GB symlink)
