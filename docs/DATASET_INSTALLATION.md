# Benchmark Dataset Installation Guide

**Last Updated**: 2025-11-11
**Purpose**: Complete guide for setting up all benchmark datasets for the Image Preprocessing Detector

---

## Dataset Status Overview

| Dataset | Status | Size | Phase | Notes |
|---------|--------|------|-------|-------|
| ✅ doclaynet | **Ready** (Symlinked) | 11GB | 1 | From data_ingestor project |
| ✅ signatr6k | **Ready** (Local) | ~2GB | ? | Already present |
| ✅ synthetic_iqa | **Auto-generated** | 364KB | 1 | Generated on benchmark runs |
| ✅ cocotext | **Ready** (Extracted) | 53MB | 2 | Annotations only - images need COCO dataset |
| ⚠️ omnidocbench | **Manual Required** | 1.2GB | 3 | Rate limited - needs HF account |
| ⏸️ tablebank | **Manual Required** | 400MB | 2 | Not yet downloaded |
| ⏸️ pubtabnet | **Manual Required** | 500MB-19GB | 2 | Not yet downloaded |
| ⏸️ fintabnet | **Manual Required** | 3GB | 2 | Not yet downloaded |
| ⏸️ wili_2018 | **Manual Required** | 800MB | 2 | Not yet downloaded |
| ⏸️ icdar_mlt_2019 | **Manual Required** | 3GB | 2 | Not yet downloaded |

**Total Disk Space Required**: ~42GB (excluding symlinked doclaynet)

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
**Status**: ⚠️ **Rate Limited - Requires HuggingFace Account**
**Source**: https://huggingface.co/datasets/opendatalab/OmniDocBench
**Size**: 1.2GB
**License**: CC-BY-NC-4.0 (Evaluation only, non-commercial)

**Issue**: Download was rate-limited by HuggingFace (HTTP 429). Need authenticated access.

**Manual Installation**:
```bash
# 1. Create/login to HuggingFace account at https://huggingface.co/join

# 2. Get your access token from https://huggingface.co/settings/tokens

# 3. Login via CLI
poetry run huggingface-cli login
# Paste your token when prompted

# 4. Download dataset
poetry run python -c "
from datasets import load_dataset
dataset = load_dataset('opendatalab/OmniDocBench')
dataset.save_to_disk('data/benchmarks/omnidocbench')
print('✓ OmniDocBench downloaded successfully')
"
```

**Dataset Info**:
- 1,358 examples
- High-quality document understanding annotations
- Multiple document types
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
**Source**: https://github.com/doc-analysis/TableBank
**Size**: ~400MB
**License**: CC-BY-4.0

**Manual Installation**:
```bash
# Download from GitHub releases
cd data/benchmarks
mkdir -p tablebank
cd tablebank

# Download detection subset (Latex + Word)
wget https://github.com/doc-analysis/TableBank/releases/download/v1.0/TableBank_data.zip

# Extract
unzip TableBank_data.zip

# Expected structure:
# data/benchmarks/tablebank/
# ├── Latex/
# │   ├── images/
# │   └── annotations/
# └── Word/
#     ├── images/
#     └── annotations/
```

**Alternative** (full dataset):
```bash
# Full dataset available at:
# https://conversationhub.blob.core.windows.net/tablebank/TableBank_both.zip (862MB)
```

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
**Source**: https://github.com/ibm-aur-nlp/PubTabNet
**Size**: 500MB (small subset) or 19GB (full dataset)
**License**: CDLA-Permissive-2.0

**Manual Installation** (small subset recommended):
```bash
cd data/benchmarks
mkdir -p pubtabnet
cd pubtabnet

# Option 1: Small subset for development (500MB)
wget https://dax-cdn.cdn.appdomain.cloud/dax-pubtabnet/2.0.0/pubtabnet.tar.gz
tar -xzf pubtabnet.tar.gz

# Option 2: Full dataset (19GB)
# Visit: https://dax-cdn.cdn.appdomain.cloud/dax-pubtabnet/2.0.0/pubtabnet_full.tar.gz
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
**Source**: https://developer.ibm.com/exchanges/data/all/fintabnet/
**Size**: ~3GB
**License**: CDLA-Permissive-2.0

**Manual Installation**:
```bash
# 1. Visit: https://developer.ibm.com/exchanges/data/all/fintabnet/
# 2. Accept license terms
# 3. Download dataset (requires IBM account)

# Extract to:
mkdir -p data/benchmarks/fintabnet
cd data/benchmarks/fintabnet
# Extract downloaded zip file here
```

**Expected structure**:
```
data/benchmarks/fintabnet/
├── FinTabNet_1.0.0_table_example_complete/
│   ├── pdf/
│   ├── images/
│   └── annotations/
└── FinTabNet_1.0.0_cell_example_complete/
    └── ...
```

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

### 10. ICDAR MLT 2019 (Phase 2 - Multi-lingual Text Detection)
**Source**: https://rrc.cvc.uab.es/?ch=15
**Size**: ~3GB
**License**: Competition dataset (check terms)

**Manual Installation**:
```bash
# 1. Register at: https://rrc.cvc.uab.es/?ch=15&com=introduction
# 2. Download training and validation data
# 3. Extract to:

mkdir -p data/benchmarks/icdar_mlt_2019
cd data/benchmarks/icdar_mlt_2019
# Extract downloaded files here

# Expected structure:
# data/benchmarks/icdar_mlt_2019/
# ├── train/
# │   ├── images/
# │   └── gt/
# └── validation/
#     ├── images/
#     └── gt/
```

**Dataset Info**:
- Multi-lingual text detection
- 10 languages
- Competition dataset from ICDAR 2019

**Citation**:
```bibtex
@inproceedings{nayef2019icdar2019,
  title={ICDAR2019 robust reading challenge on multi-lingual scene text detection and recognition—RRC-MLT-2019},
  author={Nayef, Nibal and Yin, Fei and Bizid, Imen and Choi, Hyunsoo and Feng, Yongcai and Karatzas, Dimosthenis and Lyu, Ziyuan and Gomez, Lluis and others},
  booktitle={2019 International Conference on Document Analysis and Recognition (ICDAR)},
  year={2019}
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
# OmniDocBench (requires HF account)
poetry run huggingface-cli login
poetry run python -c "
from datasets import load_dataset
dataset = load_dataset('opendatalab/OmniDocBench')
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
- [docs/PUBLIC_DATASET_COVERAGE.md](PUBLIC_DATASET_COVERAGE.md) - Dataset coverage analysis

---

**Next Steps**:
1. Complete OmniDocBench download (requires HF account)
2. Download Phase 2 datasets (TableBank, PubTabNet, WiLI-2018)
3. Verify all dataset structures
4. Run smoke tests to validate setup

**Questions?** Check the troubleshooting section or create an issue at https://github.com/williaby/image-preprocessing-detector/issues
