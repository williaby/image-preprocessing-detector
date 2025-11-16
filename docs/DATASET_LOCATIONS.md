---
schema_type: common
title: "Dataset Locations Map"
tags:
  - datasets
status: published
owner: docs-team
purpose: Documentation for dataset locations map.
---

**Purpose**: Complete reference showing where each dataset is located in the repository, cloud storage, and external sources.

**Last Updated**: 2025-11-14 (Verified with `du -sh`)
**Total Local Storage**: ~130 GB (training) + ~59 GB (benchmarks, excluding DocLayNet symlink) = **~189 GB actual**
**Note**: DocLayNet (42GB) accessed via symlink from `/home/byron/dev/data_ingestor/data/doclaynet_extracted/` - symlink adds 0GB storage

---

## Quick Reference

| **Storage Tier** | Local Path | Size | GCS Path | Git Status |
|------------------|-----------|------|----------|------------|
| **Training Data (Tier 1)** | `data/training/` | ~130 GB | `gs://image_detection_b/datasets/` | ❌ Gitignored |
| **Benchmarks (Tier 2)** | `data/benchmarks/` | ~101 GB* | Not uploaded (too large) | ❌ Gitignored |
| **Test Fixtures (Tier 3)** | `data/test_fixtures/` | ~828 KB | Not uploaded | ✅ Committed to git |
| **Raw Sources** | `data/raw/` | — | Not uploaded | ❌ Gitignored |

_* Includes DocLayNet symlink (42GB) pointing to `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet`_

**Note on Terminology**: This document uses **"Storage Tier 1/2/3"** (data organization). For benchmarking validation strategy, see [ADR-031](ADRs/0031-comprehensive-benchmarking-framework.md) which uses **"Validation Level 1/2/3"** (testing pyramid).

---

## 1. TRAINING DATA (Storage Tier 1) - Commercial Use Allowed

### 1.1 Phase 2 IQA Training Dataset ✅ PRESENT

**Purpose**: Train image quality assessment classifier (50k samples)

| Component | Local Path | Size | GCS Path | Status |
|-----------|-----------|------|----------|--------|
| **Train Set** | `data/training/iqa_phase2/train/` | 12.6 GB | `gs://image_detection_b/datasets/iqa_phase2/train/` | ✅ Present |
| - Images | `data/training/iqa_phase2/train/images/` | 12.6 GB | - | 35,000 PNG files |
| - Labels | `data/training/iqa_phase2/train/labels.json` | 18 MB | - | Multi-label annotations |
| **Val Set** | `data/training/iqa_phase2/val/` | 2.7 GB | `gs://image_detection_b/datasets/iqa_phase2/val/` | ✅ Present |
| - Images | `data/training/iqa_phase2/val/images/` | 2.7 GB | - | 7,500 PNG files |
| - Labels | `data/training/iqa_phase2/val/labels.json` | 3.9 MB | - | Multi-label annotations |
| **Test Set** | `data/training/iqa_phase2/test/` | 2.7 GB | `gs://image_detection_b/datasets/iqa_phase2/test/` | ✅ Present |
| - Images | `data/training/iqa_phase2/test/images/` | 2.7 GB | - | 7,500 PNG files |
| - Labels | `data/training/iqa_phase2/test/labels.json` | 3.9 MB | - | Multi-label annotations |

**Total**: 18 GB
**Source**: TableBank + Albumentations augmentation
**Generated**: Phase 2 Week 1 via `scripts/prepare_phase2_data.py`
**License**: Apache-2.0 (commercial use allowed)

---

### 1.2 Real-World Training Datasets ✅ PRESENT

#### Mobile Receipts (Voxel51)

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/training/mobile_receipts_voxel51/` | 379 MB | ✅ Present |
| - Train | `data/training/mobile_receipts_voxel51/train/` | ~266 MB | 500 images |
| - Val | `data/training/mobile_receipts_voxel51/val/` | ~113 MB | 213 images |

**Source**: HuggingFace `Voxel51/scanned_receipts`
**License**: CC BY 4.0 (attribution required)
**Purpose**: Mobile-captured receipts with realistic lighting, blur, skew

#### HITL Receipt OCR

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/training/receipts_hitl/` | 24 MB | ✅ Present |
| - Images | `data/training/receipts_hitl/ds0/` | 24 MB | 192 annotated receipts |

**Source**: https://humansintheloop.org/resources/datasets/free-receipt-ocr-dataset/
**License**: CC0 1.0 (Public Domain - no restrictions)
**Purpose**: Annotated receipts with JSON labels

#### Kaggle High-Quality Invoices

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/training/invoices_kaggle/` | 278 MB | ✅ Present |
| - Train | `data/training/invoices_kaggle/train/` | ~195 MB | 989 images |
| - Val | `data/training/invoices_kaggle/val/` | ~83 MB | 425 images |
| **Download Cache** | `data/downloads/kaggle_invoices/` | - | Intermediate download |

**Source**: Kaggle (Osama Hosam Abdellatif)
**License**: ODbL 1.0 (attribution required)
**Purpose**: High-resolution invoice annotations

**Real-World Training Subtotal**: ~681 MB (905 images)

---

### 1.3 Phase 3 Layout Training ✅ PRESENT

#### DocSynth-300K

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/training/layout/docsynth300k/` | 112 GB | ✅ Present |

**Source**: HuggingFace `juliozhao/DocSynth300K`
**License**: Not specified (assume research use)
**Purpose**: Synthetic layout detection training (300k samples)
**Downloaded**: Phase 3 Week 1 via `scripts/download_phase3_datasets.py`

---

### 1.4 Phase 3 Table Structure Training ✅ PRESENT

#### PubTables-1M

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/training/tables/pubtables1m/` | 83 GB | ✅ Present |

**Source**: HuggingFace `bsmock/pubtables-1m`
**License**: CDLA-Permissive-1.0 (commercial use allowed)
**Purpose**: Table structure extraction (1M real-world tables)
**Downloaded**: Phase 3 Week 1 via `scripts/download_phase3_datasets.py`

---

### 1.5 Phase 3 Handwriting Training ✅ PRESENT

#### IAM Handwriting Database

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/training/specialized/handwriting/iam/` | 254 MB | ✅ Present |

**Source**: HuggingFace `Teklia/IAM-line`
**License**: MIT (commercial use allowed)
**Purpose**: Handwriting detection (13,353 text line images)
**Downloaded**: Phase 2 Week 4 via `scripts/download_phase3_datasets.py`

---

### 1.6 Training Data Summary

| Category | Local Path | Size | Status |
|----------|-----------|------|--------|
| **IQA Phase 2** | `data/training/iqa_phase2/` | 18 GB | ✅ Present |
| **Real-World** | `data/training/mobile_receipts_voxel51/` | 379 MB | ✅ Present |
| | `data/training/receipts_hitl/` | 24 MB | ✅ Present |
| | `data/training/invoices_kaggle/` | 278 MB | ✅ Present |
| **Layout** | `data/training/layout/docsynth300k/` | 112 GB | ✅ Present |
| **Tables** | `data/training/tables/pubtables1m/` | 83 GB | ✅ Present |
| **Handwriting** | `data/training/specialized/handwriting/iam/` | 254 MB | ✅ Present |

**Training Data Total**: ~130 GB (verified with `du -sh`)

---

## 2. BENCHMARK DATA (Storage Tier 2) - Evaluation Only

### 2.1 IQA Validation Datasets ✅ PRESENT

#### LIVE Dataset

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/external_iqa/LIVE/` | ~300 MB | ✅ Present |
| - Images | `data/benchmarks/external_iqa/LIVE/refimgs/` | - | 29 reference images |
| - Distorted | `data/benchmarks/external_iqa/LIVE/*/` | - | 779 total images |
| - Scores | `data/benchmarks/external_iqa/LIVE/dmos.mat` | - | DMOS quality scores |

**Source**: http://live.ece.utexas.edu/research/quality/
**License**: Academic/Research only (citation required)
**Purpose**: Natural image quality (JPEG, blur, noise, fastfading)

#### CSIQ Dataset

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/external_iqa/CSIQ/` | ~800 MB | ✅ Present |
| - Images | `data/benchmarks/external_iqa/CSIQ/src_imgs/` | - | Reference images |
| - Distorted | `data/benchmarks/external_iqa/CSIQ/dst_imgs/` | - | 866 total images |
| - Scores | `data/benchmarks/external_iqa/CSIQ/csiq.txt` | - | DMOS quality scores |

**Source**: http://vision.eng.shizuoka.ac.jp/mod/page/view.php?id=23
**License**: Academic/Research only (citation required)
**Purpose**: Natural image quality (JPEG, JPEG2000, blur, contrast, pink noise)

#### LIVE Challenge Dataset

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/external_iqa/LIVE_Challenge/` | ~900 MB | ✅ Present |
| - Images | `data/benchmarks/external_iqa/LIVE_Challenge/Images/` | - | 1,162 images |
| - Scores | `data/benchmarks/external_iqa/LIVE_Challenge/Data/AllMOS_release.mat` | - | MOS quality scores |

**Source**: http://live.ece.utexas.edu/research/ChallengeDB/
**License**: Academic/Research only (citation required)
**Purpose**: Authentic camera captures (blur, noise, compression)

**External IQA Subtotal**: ~2 GB (2,807 images)
**Downloaded**: Phase 2 Week 1 via `scripts/download_iqa_datasets.py`

---

### 2.2 Layout Detection Benchmarks

#### DocLayNet ✅ PRESENT (Symlinked)

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/doclaynet/` → `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet` | 41 GB (symlink) | ✅ Symlinked |

**Source**: Symlinked from data_ingestor project
**License**: CDLA-Permissive-2.0 (commercial use allowed)
**Purpose**: 11-class layout detection (80k pages)
**Note**: No additional disk space needed

#### OmniDocBench ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/omnidocbench/` | 1.2 GB | ✅ Present |
| - Train Split | `data/benchmarks/omnidocbench/train/` | - | 1,358 PDF pages |
| - Cache | `data/benchmarks/omnidocbench/.cache/` | - | HuggingFace download cache |

**Source**: HuggingFace `opendatalab/OmniDocBench`
**License**: Apache-2.0 (commercial use allowed)
**Purpose**: Comprehensive document understanding (9 document types, 3 languages)
**Downloaded**: Phase 1 via `scripts/download_omnidocbench.py`

#### OHR-Bench ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/ohr-bench/` | 1.8 GB | ✅ Present |
| - Figures | `data/benchmarks/ohr-bench/figs/` | - | 8,500+ PDFs |
| - Cache | `data/benchmarks/ohr-bench/.cache/` | - | HuggingFace download cache |

**Source**: HuggingFace `opendatalab/OHR-Bench`
**License**: CC-BY-4.0 (commercial use allowed)
**Purpose**: RAG-specific OCR benchmark (7 domains)
**Downloaded**: Phase 3 Week 1 via `scripts/download_phase3_datasets.py`

---

### 2.3 Table Detection Benchmarks

#### TableBank ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/tablebank/` | 74 GB | ✅ Present |
| - TableBank | `data/benchmarks/tablebank/TableBank/` | - | 417k tables |
| - Cache | `data/benchmarks/tablebank/.cache/` | - | HuggingFace download cache |

**Source**: HuggingFace `liminghao1630/TableBank`
**License**: Apache-2.0 (commercial use allowed)
**Purpose**: Table detection (278k images from Word + LaTeX docs)
**Downloaded**: Phase 1 via `scripts/download_table_datasets.py`

#### PubTabNet ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/pubtabnet/` | 27 GB | ✅ Present |
| - PubTabNet | `data/benchmarks/pubtabnet/pubtabnet/` | - | 568k tables |
| - Cache | `data/benchmarks/pubtabnet/.cache/` | - | HuggingFace download cache |

**Source**: HuggingFace `ajimeno/PubTabNet`
**License**: MIT (commercial use allowed)
**Purpose**: Table structure recognition (scientific publications)
**Downloaded**: Phase 1 via `scripts/download_table_datasets.py`

#### FinTabNet ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/fintabnet/` | 14 GB | ✅ Present |
| - PDF Annotations | `data/benchmarks/fintabnet/FinTabNet.c-PDF_Annotations/` | - | Financial tables |
| - Structure | `data/benchmarks/fintabnet/FinTabNet.c-Structure/` | - | Cell structure data |
| - Cache | `data/benchmarks/fintabnet/.cache/` | - | HuggingFace download cache |

**Source**: HuggingFace `bsmock/FinTabNet.c`
**License**: CDLA-Permissive-1.0 (commercial use allowed)
**Purpose**: Financial table detection (corrected version)
**Downloaded**: Phase 1 via `scripts/download_table_datasets.py`

---

### 2.4 Specialized Content Benchmarks

#### SignaTR6K ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/signatr6k/` | 142 MB | ✅ Present |
| - Train | `data/benchmarks/signatr6k/train/` | - | Signature samples |
| - Val | `data/benchmarks/signatr6k/validation/` | - | Validation samples |
| - Test | `data/benchmarks/signatr6k/test/` | - | Test samples |

**Source**: Already present locally
**License**: CC BY 4.0 (commercial use allowed)
**Purpose**: Signature detection (6,000 signatures)

#### WiLI-2018 ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/wili_2018/` | 129 MB | ✅ Present |

**Source**: Zenodo (already extracted)
**License**: Apache-2.0 (commercial use allowed)
**Purpose**: Language identification (235 languages, 235k paragraphs)

#### COCO-Text ✅ PRESENT

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Annotations** | `data/benchmarks/cocotext/` | 53 MB | ✅ Present |

**Source**: Already extracted from test data
**License**: CC-BY-4.0 (commercial use allowed)
**Purpose**: Text detection annotations
**Note**: Images NOT included (need separate COCO dataset download)

#### Synthetic IQA ✅ PRESENT (Auto-Generated)

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/synthetic_iqa/` | 372 KB | ✅ Auto-generated |
| - Synthetic | `data/benchmarks/synthetic_iqa/synthetic_iqa/` | - | Generated on benchmark runs |

**Source**: Auto-generated during validation runs
**License**: Public Domain (project-generated)
**Purpose**: Smoke tests for IQA algorithms

---

### 2.5 Benchmark Data Summary

| Category | Local Path | Size | Status |
|----------|-----------|------|--------|
| **IQA Validation** | `data/benchmarks/external_iqa/` | 2 GB | ✅ Present |
| **Layout Detection** | `data/benchmarks/doclaynet/` | 0 GB (symlink) | ✅ Symlinked |
| | `data/benchmarks/omnidocbench/` | 1.2 GB | ✅ Present |
| | `data/benchmarks/ohr-bench/` | 1.8 GB | ✅ Present |
| **Table Detection** | `data/benchmarks/tablebank/` | 74 GB | ✅ Present |
| | `data/benchmarks/pubtabnet/` | 27 GB | ✅ Present |
| | `data/benchmarks/fintabnet/` | 14 GB | ✅ Present |
| **Specialized** | `data/benchmarks/signatr6k/` | 142 MB | ✅ Present |
| | `data/benchmarks/wili_2018/` | 129 MB | ✅ Present |
| | `data/benchmarks/cocotext/` | 53 MB | ✅ Present |
| | `data/benchmarks/synthetic_iqa/` | 372 KB | ✅ Present |

**Benchmark Data Total**: ~101 GB (59GB local + 42GB DocLayNet symlink, verified with `du -sh`)

---

## 3. TEST FIXTURES (Storage Tier 3) - Committed to Git

### 3.1 Test Fixtures ✅ COMMITTED

| Dataset | Local Path | Size | Samples | Status |
|---------|-----------|------|---------|--------|
| **CocoText** | `data/test_fixtures/cocotext/` | 4 KB | 10 images | ✅ Committed |
| **DocLayNet** | `data/test_fixtures/doclaynet/` | 432 KB | 5 PDFs | ✅ Committed |
| **OmniDocBench** | `data/test_fixtures/omnidocbench/` | 4 KB | 8 samples | ✅ Committed |
| **TableBank** | `data/test_fixtures/tablebank/` | 324 KB | 5 samples | ✅ Committed |
| **WiLI-2018** | `data/test_fixtures/wili_2018/` | 52 KB | 10 samples | ✅ Committed |
| **README** | `data/test_fixtures/README.md` | 12 KB | Documentation | ✅ Committed |

**Test Fixtures Total**: ~828 KB
**Git Status**: ✅ Committed to repository
**Purpose**: Fast CI/CD testing (< 5 min runtime)
**Note**: NOT uploaded to GCS (too small, version controlled)

---

## 4. RAW SOURCE DATA - Base Documents

### 4.1 Raw Datasets (Empty Placeholders)

| Dataset | Local Path | Size | Status |
|---------|-----------|------|--------|
| **DocBank** | `data/raw/docbank/` | 4 KB | ⚠️ Empty placeholder |
| **RVL-CDIP** | `data/raw/rvl-cdip/` | 4 KB | ⚠️ Empty placeholder |
| **Tobacco800** | `data/raw/tobacco800/` | 4 KB | ⚠️ Empty placeholder |

**Note**: These directories exist but datasets are not downloaded locally. TableBank was used as the source for Phase 2 IQA training data instead.

---

## 5. PENDING/PLANNED DATASETS

### 5.1 Phase 3+ Datasets (Not Yet Required)

#### DIQA-5000 (Document IQA Benchmark)

| Component | Expected Path | Size | Status |
|-----------|--------------|------|--------|
| **Dataset** | `data/benchmarks/diqa-5000/` | ~3.9 GB | ⚠️ **Pending Release** (Sept 2025) |

**Purpose**: PRIMARY document IQA benchmark (replaces LIVE/CSIQ)
**License**: TBD
**Download**: Wait for official release

#### AnyPhotoDoc 6300

| Component | Expected Path | Size | Status |
|-----------|--------------|------|--------|
| **Dataset** | `data/benchmarks/anyphotodoc/` | ~2 GB | ⏳ Phase 3 Week 3 |

**Purpose**: Dewarping benchmark (6,300 camera-captured warped documents)
**License**: Research
**Download**: `scripts/download_phase3_datasets.py --dataset anyphotodoc`

#### StaVer (Stamp Verification)

| Component | Expected Path | Size | Status |
|-----------|--------------|------|--------|
| **Dataset** | `data/benchmarks/staver/` | ~50 MB | ⏳ Phase 3 Week 2 |

**Purpose**: Stamp detection (400 images: 200 stamped, 200 clean)
**License**: CC BY-NC-SA 4.0
**Download**: Manual from paper authors

#### DDI-100 (Document Degradation)

| Component | Expected Path | Size | Status |
|-----------|--------------|------|--------|
| **Dataset** | `data/benchmarks/ddi-100/` | ~5 GB | ⏳ Phase 3 Week 2 |

**Purpose**: Stamps, hole punches, noise artifacts (99,870 images)
**License**: Research (assume)
**Download**: Manual from paper authors

#### FUNSD (Forms Understanding)

| Component | Expected Path | Size | Status |
|-----------|--------------|------|--------|
| **Dataset** | `data/benchmarks/external_iqa/funsd/` | ~50 MB | ⚠️ Partially present |

**Note**: Directory exists but may need verification
**Purpose**: Government forms (199 annotated forms)
**License**: MIT
**Source**: https://guillaumejaume.github.io/FUNSD/

---

## 6. GOOGLE CLOUD STORAGE (GCS) PATHS

### 6.1 GCS Bucket Structure

**Primary Bucket**: `gs://image_detection_b/`

#### Training Data

| Local Path | GCS Path | Size | Status |
|-----------|----------|------|--------|
| `data/training/iqa_phase2/` | `gs://image_detection_b/datasets/iqa_phase2/` | 18 GB | ✅ Uploaded |
| `data/training/mobile_receipts_voxel51/` | `gs://image_detection_b/datasets/mobile_receipts_voxel51/` | 379 MB | ⏳ Not uploaded |
| `data/training/receipts_hitl/` | `gs://image_detection_b/datasets/receipts_hitl/` | 24 MB | ⏳ Not uploaded |
| `data/training/invoices_kaggle/` | `gs://image_detection_b/datasets/invoices_kaggle/` | 278 MB | ⏳ Not uploaded |
| `data/training/layout/docsynth300k/` | Not uploaded (too large) | 112 GB | ❌ Local only |
| `data/training/tables/pubtables1m/` | Not uploaded (too large) | 83 GB | ❌ Local only |

#### Benchmark Data

| Local Path | GCS Path | Size | Status |
|-----------|----------|------|--------|
| `data/benchmarks/external_iqa/` | `gs://image_detection_b/benchmarks/external_iqa/` | 2 GB | ⏳ Not uploaded |
| `data/benchmarks/omnidocbench/` | Not uploaded | 1.2 GB | ❌ Local only |
| Other benchmarks | Not uploaded | ~117 GB | ❌ Local only |

**Note**: Large datasets (>10 GB) typically stay local or downloaded on-demand from HuggingFace

#### Configuration Files

| Local Path | GCS Path | Size | Status |
|-----------|----------|------|--------|
| `configs/colab_phase2_iqa_gcs.yaml` | `gs://image_detection_b/configs/colab_phase2_iqa_gcs.yaml` | ~1 KB | ✅ Uploaded |

### 6.2 GCS Upload Scripts

```bash
# Upload Phase 2 IQA training dataset
./scripts/gcs_helpers.sh upload-phase2

# Upload individual datasets
gsutil -m cp -r data/training/iqa_phase2 gs://image_detection_b/datasets/

# Upload configs
./scripts/gcs_helpers.sh upload-configs

# List bucket contents
./scripts/gcs_helpers.sh list

# Show storage usage
./scripts/gcs_helpers.sh info
```

---

## 7. DIRECTORY STRUCTURE SUMMARY

```
/home/byron/dev/image_detection/data/
│
├── training/                          # Tier 1: Training Data (~213 GB)
│   ├── iqa_phase2/                    # ✅ 18 GB - Phase 2 IQA (50k samples)
│   │   ├── train/                     # 35k images + labels.json
│   │   ├── val/                       # 7.5k images + labels.json
│   │   └── test/                      # 7.5k images + labels.json
│   ├── mobile_receipts_voxel51/       # ✅ 379 MB - Voxel51 receipts
│   │   ├── train/                     # 500 images
│   │   └── val/                       # 213 images
│   ├── receipts_hitl/                 # ✅ 24 MB - HITL receipts
│   │   └── ds0/                       # 192 images
│   ├── invoices_kaggle/               # ✅ 278 MB - Kaggle invoices
│   │   ├── train/                     # 989 images
│   │   └── val/                       # 425 images
│   ├── layout/
│   │   └── docsynth300k/              # ✅ 112 GB - Layout training
│   ├── tables/
│   │   └── pubtables1m/               # ✅ 83 GB - Table structure
│   └── specialized/
│       └── handwriting/
│           └── iam/                   # ✅ 254 MB - IAM handwriting
│
├── benchmarks/                        # Tier 2: Benchmarks (~120 GB)
│   ├── external_iqa/                  # ✅ 2 GB - LIVE, CSIQ, LIVE Challenge
│   │   ├── LIVE/                      # 779 images
│   │   ├── CSIQ/                      # 866 images
│   │   └── LIVE_Challenge/            # 1,162 images
│   ├── doclaynet/                     # ✅ Symlink → data_ingestor (41 GB)
│   ├── omnidocbench/                  # ✅ 1.2 GB - Document understanding
│   ├── ohr-bench/                     # ✅ 1.8 GB - RAG-specific OCR
│   ├── tablebank/                     # ✅ 74 GB - Table detection
│   ├── pubtabnet/                     # ✅ 27 GB - Table structure
│   ├── fintabnet/                     # ✅ 14 GB - Financial tables
│   ├── signatr6k/                     # ✅ 142 MB - Signatures
│   ├── wili_2018/                     # ✅ 129 MB - Language ID
│   ├── cocotext/                      # ✅ 53 MB - Text annotations
│   └── synthetic_iqa/                 # ✅ 372 KB - Auto-generated
│
├── test_fixtures/                     # Tier 3: Test Fixtures (~828 KB, git)
│   ├── cocotext/                      # ✅ 4 KB - 10 samples
│   ├── doclaynet/                     # ✅ 432 KB - 5 PDFs
│   ├── omnidocbench/                  # ✅ 4 KB - 8 samples
│   ├── tablebank/                     # ✅ 324 KB - 5 samples
│   ├── wili_2018/                     # ✅ 52 KB - 10 samples
│   └── README.md                      # ✅ 12 KB - Documentation
│
├── raw/                               # Base source documents
│   ├── docbank/                       # ⚠️ Empty (placeholder)
│   ├── rvl-cdip/                      # ⚠️ Empty (placeholder)
│   └── tobacco800/                    # ⚠️ Empty (placeholder)
│
├── downloads/                         # Temporary download cache
│   └── kaggle_invoices/               # ✅ Intermediate downloads
│
├── augmentation.py                    # Helper scripts for data augmentation
├── weak_supervision.py                # Helper scripts for weak supervision
└── __pycache__/                       # Python cache (auto-generated)
```

---

## 8. STORAGE SUMMARY

### 8.1 Current Local Storage Usage

| Category | Path | Size | Git Status |
|----------|------|------|------------|
| **Training Data** | `data/training/` | ~213 GB | ❌ Gitignored |
| **Benchmark Data** | `data/benchmarks/` | ~120 GB | ❌ Gitignored |
| **Test Fixtures** | `data/test_fixtures/` | ~828 KB | ✅ Committed |
| **Raw Sources** | `data/raw/` | ~12 KB | ❌ Gitignored (empty) |
| **Downloads Cache** | `data/downloads/` | (varies) | ❌ Gitignored |

**Total Local**: ~333 GB
**Available Disk**: 798 GB

### 8.2 GCS Storage Usage

| Category | GCS Path | Size | Status |
|----------|----------|------|--------|
| **Training Data** | `gs://image_detection_b/datasets/iqa_phase2/` | 18 GB | ✅ Uploaded |
| **Configs** | `gs://image_detection_b/configs/` | ~100 KB | ✅ Uploaded |

**Total GCS**: ~18 GB
**Monthly Cost**: ~$0.36 (Standard storage @ $0.020/GB)

---

## 9. DOWNLOAD & GENERATION SCRIPTS

### 9.1 Dataset Download Scripts

| Script | Datasets | Command |
|--------|----------|---------|
| **IQA Datasets** | LIVE, CSIQ, LIVE Challenge | `poetry run python scripts/download_iqa_datasets.py` |
| **Table Datasets** | TableBank, PubTabNet, FinTabNet | `poetry run python scripts/download_table_datasets.py --all` |
| **OmniDocBench** | OmniDocBench | `poetry run python scripts/download_omnidocbench.py` |
| **Phase 3 Datasets** | OHR-Bench, DocSynth-300K, PubTables-1M, IAM | `poetry run python scripts/download_phase3_datasets.py --dataset <name>` |

### 9.2 Dataset Generation Scripts

| Script | Output | Command |
|--------|--------|---------|
| **Phase 2 IQA Training** | `data/training/iqa_phase2/` | `poetry run python scripts/prepare_phase2_data.py --num-samples 50000` |
| **Test Fixtures** | `data/test_fixtures/` | `poetry run python scripts/extract_test_fixtures.py` |

### 9.3 GCS Upload Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| **GCS Helpers** | All GCS operations | `./scripts/gcs_helpers.sh <command>` |
| **Upload Phase 2** | Upload IQA training dataset | `./scripts/gcs_helpers.sh upload-phase2` |
| **Upload Configs** | Upload training configs | `./scripts/gcs_helpers.sh upload-configs` |
| **List Bucket** | Show GCS contents | `./scripts/gcs_helpers.sh list` |
| **Storage Info** | Show usage and costs | `./scripts/gcs_helpers.sh info` |

---

## 10. VERIFICATION COMMANDS

### 10.1 Check Local Dataset Presence

```bash
# Show all dataset sizes
du -sh data/benchmarks/* data/training/* data/test_fixtures/*

# Check specific dataset
ls -lh data/training/iqa_phase2/train/images/ | head -20

# Count images in training set
find data/training/iqa_phase2/train/images -name "*.png" | wc -l
# Expected: 35,000

# Verify symlinks
ls -l data/benchmarks/doclaynet
# Should show: -> /home/byron/dev/data_ingestor/data/benchmarks/doclaynet
```

### 10.2 Check GCS Uploads

```bash
# List GCS bucket contents
./scripts/gcs_helpers.sh list

# Check specific dataset
gsutil ls gs://image_detection_b/datasets/iqa_phase2/

# Show storage usage
./scripts/gcs_helpers.sh info
```

### 10.3 Validate Dataset Structure

```bash
# Validate datasets (future script)
poetry run python scripts/validate_datasets.py --all

# Check for data leakage between training and benchmarks
poetry run python scripts/validate_datasets.py --check-leakage
```

---

## 11. MIGRATION STATUS

### 11.1 Completed Migrations ✅

- ✅ Phase 2 IQA training dataset generated (18 GB)
- ✅ Real-world datasets downloaded (receipts, invoices)
- ✅ Phase 3 layout training downloaded (DocSynth-300K, 112 GB)
- ✅ Phase 3 table training downloaded (PubTables-1M, 83 GB)
- ✅ Phase 3 handwriting downloaded (IAM, 254 MB)
- ✅ External IQA benchmarks downloaded (LIVE, CSIQ, LIVE Challenge)
- ✅ Test fixtures committed to git (828 KB)
- ✅ **Directory cleanup complete**: Deleted 7 legacy/placeholder directories (2025-11-14)
- ✅ **ADR-029 structure verified**: Three-tier strategy fully implemented

### 11.2 Pending Actions ⏳

- ⏳ Upload real-world datasets to GCS (receipts, invoices) - Priority 1
- ⏳ Extract test fixtures from LIVE dataset for CI/CD - Priority 1
- ⏳ Upload external IQA benchmarks to GCS (optional) - Priority 2
- ⏳ Download Phase 3 specialized datasets (StaVer, DDI-100, AnyPhotoDoc) - Priority 2
- ⚠️ Wait for DIQA-5000 release (Sept 2025) - Long-term

---

## 12. RELATED DOCUMENTATION

- [data/README.md](../data/README.md): Data organization overview
- [docs/guides/dataset-installation.md](dataset-installation.md): Installation guide
- [docs/guides/dataset-preparation.md](dataset-preparation.md): Phase 2 preparation
- [docs/research/public-dataset-coverage.md](../research/public-dataset-coverage.md): Coverage analysis
- [docs/reference/document-type-coverage.md](../reference/document-type-coverage.md): Type coverage matrix
- [benchmarks/README.md](../../benchmarks/README.md): Benchmarking framework

---

**Last Updated**: 2025-11-14
**Status**: ✅ **Phase 2 Complete** - All datasets downloaded/generated, directory cleanup complete
**Storage**: 213 GB training + 120 GB benchmarks = **333 GB total**
**Cleanup**: ✅ Deleted 7 legacy directories (annotations/, augmented/, iqa/, labels/, layout/, promptcraft/, test/)
**Next Steps**: Extract test fixtures, upload real-world datasets to GCS
**Next Review**: Phase 3 Week 1 (specialized datasets: StaVer, DDI-100, AnyPhotoDoc)
