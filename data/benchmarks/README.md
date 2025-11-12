# Benchmark Datasets

This directory contains datasets used for benchmarking the Image Preprocessing Detector.

**⚠️ All datasets are gitignored** (too large for GitHub) and must be downloaded locally.

## Quick Reference

| Dataset | Status | Size | Phase | Use Case |
|---------|--------|------|-------|----------|
| **Synthetic IQA** | ✅ Auto-generated | 364KB | 1 | Blur, skew, noise, contrast testing |
| **DocLayNet** | ✅ Symlinked | 11GB | 1 | Layout detection (tables, figures, text blocks) |
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

## See Also

- **[docs/DATASET_INSTALLATION.md](../../docs/DATASET_INSTALLATION.md)** - Complete installation guide
- **[benchmarks/README.md](../../benchmarks/README.md)** - Benchmarking framework overview
- **[benchmarks/registry.yml](../../benchmarks/registry.yml)** - Benchmark suite definitions
- **[CITATIONS.md](../../CITATIONS.md)** - Complete citation information

---

**Last Updated**: 2025-11-11
**Datasets Gitignored**: Yes (all except this README)
**Results Committed**: Yes (small JSON files in `reports/`)
