---
schema_type: common
title: "Benchmark Dataset Installation Guide"
tags:
  - datasets
  - guide
  - installation
status: published
owner: docs-team
purpose: Guide for benchmark dataset installation guide.
---

**Last Updated**: 2025-11-11
**Purpose**: Complete guide for setting up all benchmark datasets for the Image Preprocessing Detector

---

## Dataset Status Overview

| Dataset | Status | Size | Phase | Notes |
|---------|--------|------|-------|-------|
| ✅ doclaynet | **Ready** (Symlinked) | 41GB | 1 | From data_ingestor project |
| ✅ signatr6k | **Ready** (Local) | 116MB | ? | Already present |
| ✅ synthetic_iqa | **Auto-generated** | 345KB | 1 | Generated on benchmark runs |
| ✅ cocotext | **Ready** (Extracted) | 52MB | 2 | Annotations only - images need COCO dataset |
| ✅ omnidocbench | **Automated Script** | 1.16GB | 3 | Rate-limit aware downloader |
| ✅ wili_2018 | **Ready** (Extracted) | 129MB | 2 | Language identification dataset |
| ⏸️ tablebank | **Automated Script** | 23.7GB | 2 | HuggingFace download available |
| ⏸️ pubtabnet | **Automated Script** | 10.5GB | 2 | HuggingFace download available |
| ⏸️ fintabnet | **Automated Script** | 3.2GB | 2 | HuggingFace download available |

**Total Disk Space Required**: ~80GB (excluding symlinked doclaynet)
**Note**: ICDAR MLT 2019 removed - competition dataset requires registration, use COCO-Text or TextOCR instead

---

## Google Cloud Storage (GCS) Integration

**Purpose**: Store and share training datasets, checkpoints, and models via Google Cloud Storage for Colab training

### GCS Authentication

The project includes a helper script for automatic GCS authentication using the service account stored in `.env`:

**Quick Start**:
```bash
# One-time setup: Authenticate with GCS
./scripts/auth_gcs.sh --cleanup

# Or source it to keep credentials for the session
source ./scripts/auth_gcs.sh
```

**What it does**:
- ✅ Reads `GCP_SA_KEY` from `.env` file
- ✅ Decodes base64-encoded service account JSON
- ✅ Authenticates with `gcloud`
- ✅ Sets project to `image-detection-478105`
- ✅ Verifies access to `gs://image_detection_b/`
- ✅ Exports environment variables (`GOOGLE_APPLICATION_CREDENTIALS`, `GCP_PROJECT`, `GCS_BUCKET`)

**Manual Authentication** (if needed):
```bash
# Extract service account from .env
export GCP_SA_KEY=$(grep "^GCP_SA_KEY=" .env | cut -d= -f2)
echo "$GCP_SA_KEY" | base64 -d > /tmp/gcs-sa.json

# Authenticate
gcloud auth activate-service-account --key-file=/tmp/gcs-sa.json
gcloud config set project image-detection-478105

# Verify
gsutil ls gs://image_detection_b/
```

### GCS Helper Scripts

After authentication, use [scripts/gcs_helpers.sh](../scripts/gcs_helpers.sh) to manage datasets and models:

```bash
# List bucket contents
./scripts/gcs_helpers.sh list

# Show storage usage and costs
./scripts/gcs_helpers.sh info

# Upload training configs
./scripts/gcs_helpers.sh upload-configs

# Upload Phase 2 dataset (~10GB, 10-30 minutes)
./scripts/gcs_helpers.sh upload-phase2

# Download Phase 2 dataset from GCS
./scripts/gcs_helpers.sh download-phase2

# Sync checkpoints to GCS
./scripts/gcs_helpers.sh sync-checkpoints phase2

# Download checkpoints from GCS
./scripts/gcs_helpers.sh download-checkpoints phase2

# Upload final trained models
./scripts/gcs_helpers.sh upload-models phase2
```

**Typical Workflow**:
1. Prepare datasets locally (follow sections below)
2. Authenticate with GCS: `./scripts/auth_gcs.sh`
3. Upload datasets to GCS: `./scripts/gcs_helpers.sh upload-phase2`
4. Train in Google Colab (uses GCS for data loading)
5. Sync checkpoints: `./scripts/gcs_helpers.sh sync-checkpoints`
6. Download final models: `./scripts/gcs_helpers.sh download-checkpoints`

**See Also**:
- [docs/PHASE2_QUICKSTART.md](PHASE2_QUICKSTART.md) - Google Colab training guide
- [docs/setup/colab-storage-setup.md](setup/colab-storage-setup.md) - GCS configuration details

---

## ✅ Completed Datasets

### 1. DocLayNet (Phase 1 - Layout Detection)
**Status**: ✅ Ready via symlink
**Location**: `data/benchmarks/doclaynet` → `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet`
**Size**: 11GB (symlinked, no additional space needed)
**License**: CDLA-Permissive-2.0

**Verification**:
```bash
ls -l data/benchmarks/doclaynet
# Should show: documents/ and ground_truth/ directories
```

**No action needed** - Already available from data_ingestor project.

### 2. SignaTR6K (Handwriting Detection)
**Status**: ✅ Ready (local)
**Location**: `data/benchmarks/signatr6k`
**Size**: ~2GB
**License**: TBD (academic dataset)

**Verification**:
```bash
ls -lh data/benchmarks/signatr6k
# Should show dataset files
```

**No action needed** - Already present locally.

### 3. Synthetic IQA (Phase 1 - Image Quality Assessment)
**Status**: ✅ Auto-generated
**Location**: `data/benchmarks/synthetic_iqa`
**Size**: 364KB (dynamically generated)
**License**: Public Domain (project-generated)

**How it works**:
- Automatically generated when running IQA benchmarks
- Creates synthetic images with controlled degradations (blur, skew, noise, contrast)
- Can be regenerated anytime

**Usage**:
```bash
# Generates automatically on first run
poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke

# Force regeneration
rm -rf data/benchmarks/synthetic_iqa
poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke
```

**No manual download needed**.

### 4. COCO-Text (Phase 2 - Text Detection)
**Status**: ✅ Annotations extracted
**Location**: `data/benchmarks/cocotext/cocotext.v2.json`
**Size**: 53MB (annotations only)
**License**: CC-BY-4.0

**Current Status**:
- ✅ Annotations file extracted from `/home/byron/dev/image_detection/data/test/cocotext.v2.zip`
- ⚠️ Image files NOT included (need separate COCO dataset download)

**To download COCO images** (if needed for benchmarking):
```bash
cd data/benchmarks/cocotext

# Download COCO 2014 Train/Val images (used by COCO-Text)
wget http://images.cocodataset.org/zips/train2014.zip
wget http://images.cocodataset.org/zips/val2014.zip

# Extract
unzip train2014.zip
unzip val2014.zip

# Expected structure:
# data/benchmarks/cocotext/
# ├── cocotext.v2.json
# ├── train2014/
# └── val2014/
```

**Citation**:
```bibtex
@inproceedings{veit2016coco,
  title={Coco-text: Dataset and benchmark for text detection and recognition in natural images},
  author={Veit, Andreas and Matera, Tomas and Neumann, Luk{\'a}{\v{s}} and Matas, Ji{\v{r}}{\'i} and Belongie, Serge},
  booktitle={arXiv preprint arXiv:1601.07140},
  year={2016}
}
```

---

## ⚠️ Manual Installation Required

### 5. OmniDocBench (Phase 3 - Comprehensive Document Understanding)
**Status**: ✅ **Automated Download Available** (Requires HuggingFace Token)
**Source**: https://huggingface.co/datasets/opendatalab/OmniDocBench
**Size**: 1.25 GB
**License**: CC-BY-NC-4.0 (Evaluation only, non-commercial)

**Automated Installation** (Recommended):
```bash
# Download using automated script with rate-limit handling
poetry run python scripts/download_omnidocbench.py

# The script automatically:
# - Reads HF_TOKEN from .env file
# - Handles rate limiting (5,000 requests/5min for free tier)
# - Implements retry logic with exponential backoff
# - Tracks download progress
# - Saves to data/benchmarks/omnidocbench
```

**HuggingFace Token Setup** (One-time):
1. Create account at: https://huggingface.co/join
2. Get token at: https://huggingface.co/settings/tokens (create "Read" token)
3. Token already stored in `.env` as `HF_TOKEN`
4. Verify: `grep HF_TOKEN .env` should show your token

**Rate Limits (Free Tier)**:
- **5,000 requests per 5-minute window** (file downloads)
- **PRO tier**: 12,000 requests/5min (~$9/month)
- **Enterprise**: 50,000+ requests/5min
- Script automatically handles rate limiting and retries

**Manual Installation** (Alternative):
```bash
# Using HuggingFace CLI
poetry run huggingface-cli login  # Paste token when prompted
poetry run python -c "
from datasets import load_dataset
dataset = load_dataset('opendatalab/OmniDocBench', token=True)
dataset.save_to_disk('data/benchmarks/omnidocbench')
"
```

**Dataset Info**:
- **1,358 PDF pages** with comprehensive annotations
- **9 document types**: Academic papers, financial reports, newspapers, textbooks, etc.
- **3 languages**: English, Simplified Chinese, mixed
- **20,000+ block-level elements**: Paragraphs, titles, tables, figures, formulas
- **80,000+ span-level elements**: Text lines, formulas, superscripts/subscripts
- Evaluation-only license (non-commercial)

**Citation**:
```bibtex
@article{meng2024omnidocbench,
  title={OmniDocBench: Benchmarking Diverse PDF Document Parsing with Comprehensive Annotations},
  author={Meng, Linke and Yuan, Yangyang and Tang, Zhenrong and Zhang, Pengfei and Liu, Zican and Lu, Xinzhi and Li, Wenhao and Hu, Yan and Wang, Jue and Zhang, Du},
  journal={arXiv preprint arXiv:2410.24195},
  year={2024}
}
```

### 6. TableBank (Phase 2 - Table Detection)
**Status**: ✅ **Automated Download Available** (Requires HuggingFace Token)
**Source**: https://huggingface.co/datasets/liminghao1630/TableBank
**Size**: 23.7 GB (full dataset)
**License**: CC-BY-4.0

**Automated Installation** (Recommended):
```bash
# Download using automated script
poetry run python scripts/download_table_datasets.py --datasets tablebank

# The script automatically:
# - Downloads 5-part zip file from HuggingFace
# - Joins parts into single archive
# - Verifies integrity
# - Extracts contents
# - Saves to data/benchmarks/tablebank
```

**Dataset Info**:
- **417,234 high-quality labeled tables**
- **278,582 images** (78K Word + 200K LaTeX documents)
- **Official splits**: Train (260K), Val (10K), Test (8K)
- Table detection and structure recognition annotations

**Alternative - Manual Download**:
```bash
# Using HuggingFace CLI
huggingface-cli download liminghao1630/TableBank \
  --repo-type dataset \
  --local-dir data/benchmarks/tablebank

# Join zip parts
cd data/benchmarks/tablebank
cat TableBank.zip.* > TableBank.zip
unzip -q TableBank.zip
```

**Note**: The original GitHub releases (400MB subset) are no longer available.
The full dataset is now hosted on HuggingFace (23.7 GB).

**Citation**:
```bibtex
@article{li2020tablebank,
  title={TableBank: A benchmark dataset for table detection and recognition},
  author={Li, Minghao and Cui, Lei and Huang, Shaohan and Wei, Furu and Zhou, Ming and Li, Zhoujun},
  journal={arXiv preprint arXiv:1903.01949},
  year={2020}
}
```

### 7. PubTabNet (Phase 2 - Table Structure Recognition)
**Status**: ✅ Automated Download Available
**Source**: https://huggingface.co/datasets/ajimeno/PubTabNet
**Size**: 10.5 GB (full dataset)
**License**: CDLA-Permissive-2.0

**Automated Installation** (recommended):
```bash
# Download PubTabNet using HuggingFace Hub
poetry run python scripts/download_table_datasets.py --datasets pubtabnet

# Or download all table datasets at once
poetry run python scripts/download_table_datasets.py --all
```

**Dataset Details**:
- **Images**: 568,454 scientific publication tables
- **Format**: Single tar.gz archive
- **Features**: HTML structure annotations for table structure recognition
- **Splits**: Train (516,747), validation (51,707)
- **Image Format**: PNG images with COCO-aligned JSON annotations

**Manual Installation** (alternative):
```bash
cd data/benchmarks
mkdir -p pubtabnet

# Download using HuggingFace CLI
huggingface-cli download ajimeno/PubTabNet \
  pubtabnet.tar.gz \
  --repo-type dataset \
  --local-dir pubtabnet \
  --token $HF_TOKEN

# Extract
cd pubtabnet
tar -xzf pubtabnet.tar.gz
```

**Expected structure**:
```
data/benchmarks/pubtabnet/
├── train/
│   ├── images/
│   └── annotations.json
└── val/
    ├── images/
    └── annotations.json
```

**Citation**:
```bibtex
@article{zhong2020image,
  title={Image-based table recognition: data, model, and evaluation},
  author={Zhong, Xu and ShafieiBavani, Elaheh and Jimeno Yepes, Antonio},
  journal={arXiv preprint arXiv:1911.10683},
  year={2020}
}
```

### 8. FinTabNet (Phase 2 - Financial Table Detection)
**Status**: ✅ Automated Download Available
**Source**: https://huggingface.co/datasets/bsmock/FinTabNet.c
**Size**: 3.2 GB (corrected version)
**License**: CDLA-Permissive-2.0

**Automated Installation** (recommended):
```bash
# Download FinTabNet using HuggingFace Hub
poetry run python scripts/download_table_datasets.py --datasets fintabnet

# Or download all table datasets at once
poetry run python scripts/download_table_datasets.py --all
```

**Dataset Details**:
- **Version**: FinTabNet.c (corrected version with fixes)
- **Images**: Financial tables from annual reports
- **Format**: Two tar.gz archives (PDF annotations + structure)
- **Files**:
  - `FinTabNet.c-PDF_Annotations.tar.gz` - PDF annotations
  - `FinTabNet.c-Structure.tar.gz` - Table structure data
- **Features**: Table detection and cell structure recognition for financial documents

**Manual Installation** (alternative):
```bash
cd data/benchmarks
mkdir -p fintabnet

# Download using HuggingFace CLI
huggingface-cli download bsmock/FinTabNet.c \
  FinTabNet.c-PDF_Annotations.tar.gz \
  --repo-type dataset \
  --local-dir fintabnet \
  --token $HF_TOKEN

huggingface-cli download bsmock/FinTabNet.c \
  FinTabNet.c-Structure.tar.gz \
  --repo-type dataset \
  --local-dir fintabnet \
  --token $HF_TOKEN

# Extract both archives
cd fintabnet
tar -xzf FinTabNet.c-PDF_Annotations.tar.gz
tar -xzf FinTabNet.c-Structure.tar.gz
```

**Expected structure**:
```
data/benchmarks/fintabnet/
├── FinTabNet.c-PDF_Annotations/
│   ├── pdf/
│   ├── images/
│   └── annotations/
└── FinTabNet.c-Structure/
    └── ...
```

**Note**: This is the corrected version (FinTabNet.c) which includes bug fixes from the original FinTabNet release. The original IBM Developer site version is no longer actively maintained.

**Citation**:
```bibtex
@article{zheng2021global,
  title={Global table extractor (gte): A framework for joint table identification and cell structure recognition using visual context},
  author={Zheng, Xinyi and Burdick, Douglas and Popa, Lucian and Zhong, Xu and Wang, Nancy Xin Ru},
  journal={arXiv preprint arXiv:2005.00589},
  year={2021}
}
```

### 9. WiLI-2018 (Phase 2 - Language Identification)
**Source**: https://zenodo.org/record/841984
**Size**: ~800MB
**License**: CC-BY-SA-4.0

**Manual Installation**:
```bash
cd data/benchmarks
mkdir -p wili_2018
cd wili_2018

# Download from Zenodo
wget https://zenodo.org/record/841984/files/wili-2018.zip

# Extract
unzip wili-2018.zip

# Expected structure:
# data/benchmarks/wili_2018/
# ├── x_train.txt
# ├── x_test.txt
# ├── y_train.txt
# └── y_test.txt
```

**Dataset Info**:
- 235,000 paragraphs
- 235 languages
- Wikipedia-based text samples

**Citation**:
```bibtex
@inproceedings{thoma2018wili,
  title={The WiLI benchmark dataset for written language identification},
  author={Thoma, Martin},
  booktitle={arXiv preprint arXiv:1801.07779},
  year={2018}
}
```

---

## .gitignore Configuration

**Current Rule** (line 119 in `.gitignore`):
```gitignore
# Benchmark datasets (large) - added 2025-11-05
data/benchmarks/
```

This rule covers **ALL datasets** in `data/benchmarks/` directory.

**Exceptions** (files that SHOULD be tracked):
- `data/benchmarks/README.md` - Dataset overview (needs to be re-added to git)

**To track README**:
```bash
# Force add README despite gitignore
git add -f data/benchmarks/README.md
git commit -m "docs: Add benchmark datasets README"
```

**Verification**:
```bash
# Check what's tracked
git ls-files data/benchmarks/

# Should show only:
# data/benchmarks/README.md
```

---

## Disk Space Management

### Current Space Usage:
```bash
df -h /home/byron/dev/image_detection
# Available: 798GB
```

### Expected Dataset Sizes:
| Dataset | Size | Cumulative |
|---------|------|------------|
| doclaynet (symlink) | 11GB* | 0GB (symlinked) |
| signatr6k | 2GB | 2GB |
| synthetic_iqa | 364KB | 2GB |
| cocotext (annotations) | 53MB | 2GB |
| cocotext (images) | 25GB | 27GB |
| omnidocbench | 1.2GB | 28.2GB |
| tablebank | 400MB | 28.6GB |
| pubtabnet (small) | 500MB | 29.1GB |
| fintabnet | 3GB | 32.1GB |
| wili_2018 | 800MB | 32.9GB |
| icdar_mlt_2019 | 3GB | 35.9GB |
| **Total** | **~47GB** | **~36GB actual** |

*doclaynet symlinked from data_ingestor - no additional space needed

### Cleanup Commands:
```bash
# Remove old benchmark results (keep latest only)
cd reports/
for suite in */; do
  cd "$suite"
  ls -t | tail -n +2 | xargs rm -rf  # Keep newest, delete rest
  cd ..
done

# Remove synthetic datasets (can regenerate)
rm -rf data/benchmarks/synthetic_iqa

# Remove COCO images if not needed
rm -rf data/benchmarks/cocotext/{train2014,val2014}
```

---

## Quick Setup Commands

### Essential Datasets (Phase 1):
```bash
# 1. Verify doclaynet symlink
ls -l data/benchmarks/doclaynet

# If missing, recreate:
ln -s /home/byron/dev/data_ingestor/data/benchmarks/doclaynet data/benchmarks/doclaynet

# 2. Generate synthetic IQA
poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke
```

### High-Priority Datasets (Phase 3):
```bash
# OmniDocBench (automated with rate-limit handling)
# Token already configured in .env
poetry run python scripts/download_omnidocbench.py

# Alternative: Manual download with CLI
poetry run huggingface-cli login  # Use token from .env: grep HF_TOKEN .env
poetry run python -c "
from datasets import load_dataset
dataset = load_dataset('opendatalab/OmniDocBench', token=True)
dataset.save_to_disk('data/benchmarks/omnidocbench')
"
```

### Medium-Priority Datasets (Phase 2):
```bash
# TableBank (400MB)
cd data/benchmarks && mkdir -p tablebank && cd tablebank
wget https://github.com/doc-analysis/TableBank/releases/download/v1.0/TableBank_data.zip
unzip TableBank_data.zip

# PubTabNet subset (500MB)
cd ../pubtabnet
wget https://dax-cdn.cdn.appdomain.cloud/dax-pubtabnet/2.0.0/pubtabnet.tar.gz
tar -xzf pubtabnet.tar.gz

# WiLI-2018 (800MB)
cd ../wili_2018
wget https://zenodo.org/record/841984/files/wili-2018.zip
unzip wili-2018.zip
```

---

## Verification Checklist

After installing datasets, verify:

```bash
# Check dataset directories exist
ls -d data/benchmarks/*/

# Expected output:
# data/benchmarks/cocotext/
# data/benchmarks/doclaynet/
# data/benchmarks/fintabnet/
# data/benchmarks/icdar_mlt_2019/
# data/benchmarks/omnidocbench/
# data/benchmarks/pubtabnet/
# data/benchmarks/signatr6k/
# data/benchmarks/synthetic_iqa/
# data/benchmarks/tablebank/
# data/benchmarks/wili_2018/

# Check dataset sizes
du -sh data/benchmarks/*/

# Verify gitignore working
git status data/benchmarks/
# Should show: "nothing to commit" (all datasets ignored)

# Test benchmark suite
poetry run python -m benchmarks.runners.run_smoke --all
```

---

## Troubleshooting

### Issue: Dataset not found
**Solution**: Check dataset directory exists and has correct structure

```bash
# Verify dataset structure
ls -R data/benchmarks/doclaynet | head -20

# Check registry configuration
cat benchmarks/registry.yml | grep -A 5 "dataset: doclaynet"
```

### Issue: HuggingFace rate limit (429 error)
**Solution**: Login with HF account

```bash
poetry run huggingface-cli login
# Paste your token from: https://huggingface.co/settings/tokens
```

### Issue: Disk space full
**Solution**: Remove optional datasets or use cleanup commands

```bash
# Check space
df -h

# Remove large optional datasets
rm -rf data/benchmarks/cocotext/{train2014,val2014}  # 25GB
rm -rf data/benchmarks/pubtabnet  # Use small subset instead
```

### Issue: Symlink broken
**Solution**: Recreate symlink

```bash
# Remove broken symlink
rm data/benchmarks/doclaynet

# Recreate
ln -s /home/byron/dev/data_ingestor/data/benchmarks/doclaynet data/benchmarks/doclaynet

# Verify
ls -l data/benchmarks/doclaynet
```

---

## License Compliance Summary

### Must Cite in Publications:
- ✅ DocLayNet (CDLA-Permissive-2.0)
- ✅ TableBank (CC-BY-4.0)
- ✅ PubTabNet (CDLA-Permissive-2.0)
- ✅ FinTabNet (CDLA-Permissive-2.0)
- ✅ COCO-Text (CC-BY-4.0)
- ✅ WiLI-2018 (CC-BY-SA-4.0)
- ✅ OmniDocBench (CC-BY-NC-4.0)

### Commercial Use Restrictions:
- ⚠️ **OmniDocBench**: Non-commercial evaluation only (CC-BY-NC-4.0)
- ✅ **All others**: Commercial use allowed with attribution

### Share-Alike Requirements:
- ⚠️ **WiLI-2018**: CC-BY-SA-4.0 (derivatives must use same license)
- ✅ **All others**: No share-alike requirement

---

## See Also

- [benchmarks/README.md](../benchmarks/README.md) - Benchmarking framework overview
- [benchmarks/registry.yml](../benchmarks/registry.yml) - Benchmark suite definitions
- [CITATIONS.md](../CITATIONS.md) - Complete citation information
- [PUBLIC_DATASET_COVERAGE.md](../research/public-dataset-coverage.md) - Dataset coverage analysis

---

**Next Steps**:

1. **Download OmniDocBench**: `poetry run python scripts/download_omnidocbench.py` (automated)
2. Download Phase 2 datasets (TableBank, PubTabNet, WiLI-2018)
3. Verify all dataset structures
4. Run smoke tests to validate setup

**Questions?** Check the troubleshooting section or create an issue at https://github.com/williaby/image-preprocessing-detector/issues
