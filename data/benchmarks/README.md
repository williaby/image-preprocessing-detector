# Benchmark Datasets

> **What's Here**: Actual dataset files (images, PDFs, annotations) - ~101GB total (59GB local + 42GB DocLayNet symlink)
> **Framework Code**: See [benchmarks/](../../benchmarks/) for benchmark runners and metrics

This directory contains datasets used for benchmarking the Image Preprocessing Detector.

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
| **SignaTR6K** | ✅ Local | 2GB | ? | Handwriting detection |
| **COCO-Text** | ✅ Extracted | 53MB | 2 | Text detection and recognition |
| **OmniDocBench** | ⚠️ Manual | 1.2GB | 3 | Comprehensive document understanding |
| **TableBank** | ⏸️ Manual | 400MB | 2 | Table detection |
| **PubTabNet** | ⏸️ Manual | 500MB | 2 | Table structure recognition |
| **FinTabNet** | ⏸️ Manual | 3GB | 2 | Financial table detection |
| **WiLI-2018** | ⏸️ Manual | 800MB | 2 | Language identification |
| **ICDAR MLT 2019** | ⏸️ Manual | 3GB | 2 | Multi-lingual text detection |

**Total Space Required**: ~36GB (excluding symlinked DocLayNet)

## Installation

**Complete installation guide**: See [docs/DATASET_INSTALLATION.md](../../docs/DATASET_INSTALLATION.md)

### Quick Setup

```bash
# 1. Verify doclaynet symlink
ls -l doclaynet/

# 2. Generate synthetic IQA (auto-generated on benchmark runs)
cd ../..
poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke

# 3. Install OmniDocBench (requires HuggingFace account)
poetry run huggingface-cli login
poetry run python -c "
from datasets import load_dataset
dataset = load_dataset('opendatalab/OmniDocBench')
dataset.save_to_disk('data/benchmarks/omnidocbench')
"

# 4. Download Phase 2 datasets (see full guide for details)
```

## Directory Structure

```
data/benchmarks/
├── README.md                          # This file
├── doclaynet/                         # ✅ Symlinked (11GB)
│   ├── documents/
│   └── ground_truth/
├── signatr6k/                         # ✅ Present (verify)
├── synthetic_iqa/                     # ✅ Auto-generated
│   ├── blur/
│   ├── skew/
│   ├── noise/
│   ├── contrast/
│   └── binarization/
├── cocotext/                          # ✅ Extracted
│   └── cocotext.v2.json
├── omnidocbench/                      # ⏸️ Manual download
├── tablebank/                         # ⏸️ Manual download
├── pubtabnet/                         # ⏸️ Manual download
├── fintabnet/                         # ⏸️ Manual download
├── wili_2018/                         # ⏸️ Manual download
└── icdar_mlt_2019/                    # ⏸️ Manual download
```

## Gitignore Configuration

**All datasets are gitignored** via rule in `.gitignore`:
```gitignore
# Line 119
data/benchmarks/
```

Only this README file is tracked in git (forced with `git add -f`).

## License Compliance

### Must Cite in Publications
- DocLayNet (CDLA-Permissive-2.0)
- TableBank, COCO-Text (CC-BY-4.0)
- PubTabNet, FinTabNet (CDLA-Permissive-2.0)
- WiLI-2018 (CC-BY-SA-4.0)
- OmniDocBench (CC-BY-NC-4.0)

### Commercial Use Restrictions
- ⚠️ **OmniDocBench**: Non-commercial evaluation only (CC-BY-NC-4.0)
- ✅ All others: Commercial use allowed with attribution

## Troubleshooting

### Dataset not found error
```bash
# Check dataset exists
ls -R doclaynet/ | head -20

# Regenerate synthetic datasets
rm -rf synthetic_iqa/
poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke
```

### HuggingFace rate limit (429 error)
```bash
# Login with HF account
poetry run huggingface-cli login
```

### Disk space full
```bash
# Check space
df -h

# Remove optional datasets or old results
rm -rf ../reports/*/$(ls -t ../reports/*/ | tail -n +2)
```

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

**Last Updated**: 2025-11-11
**Datasets Gitignored**: Yes (all except this README)
**Results Committed**: Yes (small JSON files in `reports/`)
