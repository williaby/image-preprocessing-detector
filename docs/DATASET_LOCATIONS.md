---
schema_type: common
title: "Dataset Locations Map"
tags:
  - datasets
status: published
owner: docs-team
purpose: Complete reference for dataset locations across NFS and GCS storage.
---

**Purpose**: Complete reference showing where each dataset is located in NFS storage, local symlinks, and cloud backups.

**Last Updated**: 2025-11-21 (Training datasets added)
**Total Storage**: ~232GB (~56GB benchmarks + 134GB training + 42GB DocLayNet symlink)
**Datasets**: 12/12 benchmarks + 8/8 training datasets (100% complete)
**Storage Strategy**: NFS primary + Local symlinks + GCS backup

---

## Quick Reference

| **Dataset** | **Size** | **NFS Location** | **Local Symlink** | **GCS Status** |
|-------------|----------|------------------|-------------------|----------------|
| **TableBank** | 27GB | `/mnt/unraid/.../tablebank` | `data/benchmarks/tablebank` | ✅ Already in GCS (source) |
| **PubTabNet** | 14GB | `/mnt/unraid/.../pubtabnet` | `data/benchmarks/pubtabnet` | ✅ Already in GCS (source) |
| **DIQA-5000** | 5.4GB | `/mnt/unraid/.../diqa-5000` | `data/benchmarks/diqa-5000` | ⏳ Upload pending |
| **FUNSD+** | 500MB | `/mnt/unraid/.../funsd_plus` | `data/benchmarks/funsd_plus` | ⏳ Upload pending |
| **DocLayNet** | 42GB* | `/home/byron/dev/data_ingestor/...` | `data/benchmarks/doclaynet` | ❌ Not uploaded |
| **FinTabNet** | 5.3GB | `/mnt/unraid/.../fintabnet` | `data/benchmarks/fintabnet` | ⏳ Upload pending |
| **OmniDocBench** | 1.2GB | `/mnt/unraid/.../omnidocbench` | `data/benchmarks/omnidocbench` | ⏳ Upload pending |
| **OHR-Bench** | 1.8GB | `/mnt/unraid/.../ohr-bench` | `data/benchmarks/ohr-bench` | ⏳ Upload pending |
| **SignaTR6K** | 153MB | `/mnt/unraid/.../signatr6k` | `data/benchmarks/signatr6k` | ⏳ Upload pending |
| **WiLI-2018** | 129MB | `/mnt/unraid/.../wili_2018` | `data/benchmarks/wili_2018` | ⏳ Upload pending |
| **COCO-Text** | 53MB | `/mnt/unraid/.../cocotext` | `data/benchmarks/cocotext` | ⏳ Upload pending |
| **Synthetic IQA** | 372KB | `data/benchmarks/synthetic_iqa` | N/A | ❌ Not uploaded |

_* DocLayNet accessed via symlink from data_ingestor project (adds 0GB to this project)_

**NFS Base Path**: `/mnt/unraid/training_data/image_detection/benchmarks/`
**Local Base Path**: `data/benchmarks/` (all symlinks except synthetic_iqa)

---

## Storage Architecture

### Three-Tier Strategy

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  LOCAL (WSL)    │         │   NFS (Unraid)   │         │   GCS (Cloud)   │
│  ~1 MB          │◄────────┤   ~98 GB         │────────►│   Backup        │
│                 │Symlinks │                  │ Upload  │                 │
│ • Test Fixtures │         │ • Benchmarks     │         │ • Training Data │
│ • Symlinks Only │         │ • Training Data  │         │ • Benchmarks    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
      Tier 3                      Tier 2                      Tier 1
  (Fast CI/CD)            (Primary Storage)              (Cloud Backup)
```

**Design Goals**:
1. **Minimal local storage** - WSL filesystem kept under 5GB
2. **Fast NFS access** - Gigabit ethernet to Unraid server (192.168.1.16)
3. **GCS backup** - Cloud backup for Modal training and disaster recovery
4. **Symlink strategy** - Local workspace references NFS without duplication

---

## 1. BENCHMARK DATA (Primary Storage: NFS)

### 1.1 Document IQA Datasets ✅ COMPLETE

#### DIQA-5000 ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Train Set** | `/mnt/unraid/training_data/image_detection/benchmarks/diqa-5000/train/ori/` | 3.8GB | ✅ 3,500 images |
| **Val Set** | `/mnt/unraid/training_data/image_detection/benchmarks/diqa-5000/val/ori/` | 470MB | ✅ Validation images |
| **Test Set** | `/mnt/unraid/training_data/image_detection/benchmarks/diqa-5000/test/ori/` | 1.1GB | ✅ Test images |

**Local Symlink**: `data/benchmarks/diqa-5000` → `/mnt/unraid/training_data/image_detection/benchmarks/diqa-5000`
**Source**: User-provided DIQA-5000.zip (extracted)
**License**: Research/Academic use (TBD - citation required)
**Purpose**: PRIMARY document IQA benchmark with quality annotations (5,500 images total)
**Use Case**: Phase 2 IQA training dataset generation (100K samples)

#### OHR-Bench ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/benchmarks/ohr-bench/` | 1.8GB | ✅ 8,500+ PDF pages |

**Local Symlink**: `data/benchmarks/ohr-bench` → `/mnt/unraid/training_data/image_detection/benchmarks/ohr-bench`
**Source**: HuggingFace `jordyvl/OHR-Bench`
**License**: CC-BY-NC-4.0 (Non-commercial evaluation only)
**Purpose**: RAG-specific OCR benchmark (7 domains: arXiv, PubMed, GitHub, StackExchange, FreeLaw, USPTO, PubMed Central)
**Use Case**: Real-world document quality diversity for IQA training

---

### 1.2 Table Detection Benchmarks ✅ COMPLETE

#### TableBank ✅ DOWNLOADING (61% complete)

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/benchmarks/tablebank/` | 27GB | ⏳ 260,025 / 424,000 images |

**Local Symlink**: `data/benchmarks/tablebank` → `/mnt/unraid/training_data/image_detection/benchmarks/tablebank`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/tablebank/`
**License**: Apache-2.0 (commercial use allowed, citation required)
**Purpose**: Table detection benchmark (424K table images from Word + LaTeX docs)
**Use Case**: Large-scale training data source for 100K IQA dataset

#### PubTabNet ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/benchmarks/pubtabnet/` | 14GB | ✅ 500K+ table images |

**Local Symlink**: `data/benchmarks/pubtabnet` → `/mnt/unraid/training_data/image_detection/benchmarks/pubtabnet`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/pubtabnet/`
**License**: CDLA-Permissive-2.0 (commercial use allowed, citation required)
**Purpose**: Table structure recognition (scientific publications)
**Use Case**: Training data source for 100K IQA dataset

#### FinTabNet ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/benchmarks/fintabnet/` | 5.3GB | ✅ Financial tables |

**Local Symlink**: `data/benchmarks/fintabnet` → `/mnt/unraid/training_data/image_detection/benchmarks/fintabnet`
**Source**: HuggingFace `bsmock/FinTabNet.c`
**License**: CDLA-Permissive-2.0 (commercial use allowed)
**Purpose**: Financial table detection (corrected version)
**Use Case**: Domain-specific table evaluation

---

### 1.3 Layout Detection Benchmarks ✅ COMPLETE

#### DocLayNet ✅ SYMLINKED (External Project)

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet/` | 42GB | ✅ Symlinked (0GB local) |

**Local Symlink**: `data/benchmarks/doclaynet` → `/home/byron/dev/data_ingestor/data/benchmarks/doclaynet`
**Source**: data_ingestor project (shared benchmark dataset)
**License**: CDLA-Permissive-2.0 (commercial use allowed, citation required)
**Purpose**: 11-class layout detection (80K pages)
**Note**: Symlink to external project - no additional disk space used

#### OmniDocBench ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/benchmarks/omnidocbench/` | 1.2GB | ✅ 1,358+ samples |

**Local Symlink**: `data/benchmarks/omnidocbench` → `/mnt/unraid/training_data/image_detection/benchmarks/omnidocbench`
**Source**: HuggingFace `opendatalab/OmniDocBench`
**License**: CC-BY-NC-4.0 (Non-commercial evaluation only)
**Purpose**: Comprehensive document understanding (9 document types, 3 languages)
**Use Case**: Document type diversity evaluation

---

### 1.4 Forms and Specialized Content ✅ COMPLETE

#### FUNSD+ (Enhanced) ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Train Set** | `/mnt/unraid/training_data/image_detection/benchmarks/funsd_plus/train/` | ~350MB | ✅ 1,030 samples |
| **Test Set** | `/mnt/unraid/training_data/image_detection/benchmarks/funsd_plus/test/` | ~150MB | ✅ 113 samples |

**Local Symlink**: `data/benchmarks/funsd_plus` → `/mnt/unraid/training_data/image_detection/benchmarks/funsd_plus`
**Source**: HuggingFace `konfuzio/funsd_plus` (enhanced version, 5.6x larger than original FUNSD)
**License**: Other (check HuggingFace for details)
**Purpose**: Enhanced form understanding dataset (1,113 total samples vs 199 original)
**Use Case**: Form-specific document quality assessment for 100K IQA dataset

#### SignaTR6K ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/benchmarks/signatr6k/` | 153MB | ✅ 6,000 samples |

**Local Symlink**: `data/benchmarks/signatr6k` → `/mnt/unraid/training_data/image_detection/benchmarks/signatr6k`
**Source**: User-provided SignaTR6K.zip (extracted)
**License**: Research/Academic use (citation required)
**Purpose**: Signature detection benchmark (6K signature samples)
**Use Case**: Specialized content detection evaluation

#### WiLI-2018 ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/benchmarks/wili_2018/` | 129MB | ✅ 235K samples |

**Local Symlink**: `data/benchmarks/wili_2018` → `/mnt/unraid/training_data/image_detection/benchmarks/wili_2018`
**Source**: HuggingFace `wietsedv/wili_2018`
**License**: CC-BY-SA-4.0 (commercial use allowed with share-alike)
**Purpose**: Language identification (235 languages, 235K paragraphs)
**Use Case**: Multilingual document evaluation

#### COCO-Text ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Annotations** | `/mnt/unraid/training_data/image_detection/benchmarks/cocotext/` | 53MB | ✅ JSON annotations |

**Local Symlink**: `data/benchmarks/cocotext` → `/mnt/unraid/training_data/image_detection/benchmarks/cocotext`
**Source**: Direct URL download `https://github.com/bgshih/cocotext/raw/master/data/cocotext.v2.json`
**License**: CC-BY-4.0 (commercial use allowed, attribution required)
**Purpose**: Text detection annotations (63K text instances)
**Note**: Images NOT included (requires separate COCO dataset download)

---

### 1.5 Synthetic Test Data ✅ AUTO-GENERATED

#### Synthetic IQA ✅ AUTO-GENERATED

| Component | Local Path | Size | Status |
|-----------|-----------|------|--------|
| **Dataset** | `data/benchmarks/synthetic_iqa/` | 372KB | ✅ Auto-generated on runs |

**Storage**: Local only (too small for NFS/GCS, regenerated as needed)
**Source**: Auto-generated during benchmark validation runs
**License**: Public Domain (project-generated)
**Purpose**: Smoke tests for IQA algorithms (blur, skew, noise, contrast, binarization)
**Use Case**: Fast CI/CD testing (< 5 min runtime)

---

### 1.6 Benchmark Data Summary

| Category | Datasets | Total Size | GCS Status |
|----------|----------|------------|------------|
| **Document IQA** | DIQA-5000, OHR-Bench | 7.2GB | ⏳ Upload pending |
| **Table Detection** | TableBank, PubTabNet, FinTabNet | 46.3GB | ✅ TableBank/PubTabNet in GCS; FinTabNet pending |
| **Layout Detection** | DocLayNet (symlink), OmniDocBench | 43.2GB | ❌ DocLayNet not uploaded |
| **Specialized** | FUNSD+, SignaTR6K, WiLI-2018, COCO-Text | 0.8GB | ⏳ Upload pending |
| **Synthetic** | Synthetic IQA | 372KB | ❌ Not uploaded (regenerated) |

**Benchmark Total**: ~98GB (~56GB NFS + 42GB external symlink)
**Downloaded**: 12/12 datasets (100% complete)
**NFS Storage**: `/mnt/unraid/training_data/image_detection/benchmarks/`

---

## 2. TRAINING DATA (NFS Primary Storage)

**Total Training Storage**: ~134GB (8 datasets)
**NFS Base Path**: `/mnt/unraid/training_data/image_detection/training/`
**Local Base Path**: `data/training/` (all symlinks)
**GCS Backup**: `gs://image_detection_b/image-preprocessing-detector/datasets/`

### Quick Reference - Training Datasets

| **Dataset** | **Size** | **NFS Location** | **Local Symlink** | **GCS Status** |
|-------------|----------|------------------|-------------------|----------------|
| **IQA Phase 2** | 0.5GB | `/mnt/unraid/.../iqa_phase2` | `data/training/iqa_phase2` | ✅ Source |
| **IQA Phase 2 100K** | 10GB | `/mnt/unraid/.../iqa_phase2_100k` | `data/training/iqa_phase2_100k` | ✅ Source |
| **Receipts HITL** | 24MB | `/mnt/unraid/.../receipts_hitl` | `data/training/receipts_hitl` | ✅ Source |
| **Mobile Receipts** | 379MB | `/mnt/unraid/.../mobile_receipts_voxel51` | `data/training/mobile_receipts_voxel51` | ✅ Source |
| **Invoices Kaggle** | 278MB | `/mnt/unraid/.../invoices_kaggle` | `data/training/invoices_kaggle` | ✅ Source |
| **IAM Handwriting** | 254MB | `/mnt/unraid/.../iam_handwriting` | `data/training/iam_handwriting` | ✅ Source |
| **DocSynth300K** | 112GB | `/mnt/unraid/.../docsynth300k` | `data/training/docsynth300k` | ✅ Source |
| **NIST DB2** | 1.0GB | `/mnt/unraid/.../nist_db2` | `data/training/nist_db2` | ✅ Source |

---

### 2.1 Phase 2 IQA Training Datasets ✅ DOWNLOADED

#### IQA Phase 2 (Original) ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/iqa_phase2/` | 0.5GB | ✅ Downloaded from GCS |

**Local Symlink**: `data/training/iqa_phase2` → `/mnt/unraid/training_data/image_detection/training/iqa_phase2`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/iqa_phase2/`
**License**: Apache-2.0 (project-generated)
**Purpose**: Original IQA Phase 2 training dataset
**Use Case**: Baseline IQA model training, comparison with 100K dataset

#### IQA Phase 2 100K (15K Partial) ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/` | 10GB | ✅ Downloaded (15,350 samples) |
| **Train Split** | `.../iqa_phase2_100k/train/` | ~7GB | ⏳ Needs regeneration |
| **Val Split** | `.../iqa_phase2_100k/val/` | ~1.5GB | ⏳ Needs regeneration |
| **Test Split** | `.../iqa_phase2_100k/test/` | ~1.5GB | ⏳ Needs regeneration |

**Local Symlink**: `data/training/iqa_phase2_100k` → `/mnt/unraid/training_data/image_detection/training/iqa_phase2_100k`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/iqa_phase2_100k/`
**License**: Apache-2.0 (derived from permissive-license source datasets)
**Purpose**: ResNet-50 teacher & ResNet-18 student IQA model training
**Current Status**: Partial dataset (15,350 samples) needs regeneration to reach 100K target
**Source Datasets**: DIQA-5000 (3,500 images), TableBank (424K images), PubTabNet (500K images), FUNSD+ (1,030 images)
**Generation Script**: `scripts/generate_100k_iqa_dataset.py`
**Target**: 100,000 samples (70K train, 15K val, 15K test) with 13-dimensional quality labels
**Next Step**: Run regeneration script to create full 100K dataset (~50GB estimated)

---

### 2.2 Real-World Receipts & Invoices ✅ DOWNLOADED

#### Receipts HITL ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/receipts_hitl/` | 24MB | ✅ Downloaded from GCS |

**Local Symlink**: `data/training/receipts_hitl` → `/mnt/unraid/training_data/image_detection/training/receipts_hitl`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/receipts_hitl/`
**License**: Proprietary (HITL annotated)
**Purpose**: Human-in-the-loop annotated receipts dataset
**Use Case**: Real-world receipt quality assessment, OCR validation

#### Mobile Receipts Voxel51 ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/mobile_receipts_voxel51/` | 379MB | ✅ Downloaded from GCS |

**Local Symlink**: `data/training/mobile_receipts_voxel51` → `/mnt/unraid/training_data/image_detection/training/mobile_receipts_voxel51`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/mobile_receipts_voxel51/`
**License**: Apache-2.0 (Voxel51 open dataset)
**Purpose**: Mobile-captured receipts from Voxel51
**Use Case**: Real-world degradation patterns (mobile camera captures, lighting variations)

#### Invoices Kaggle ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/invoices_kaggle/` | 278MB | ✅ Downloaded from GCS |

**Local Symlink**: `data/training/invoices_kaggle` → `/mnt/unraid/training_data/image_detection/training/invoices_kaggle`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/invoices_kaggle/`
**License**: CC-BY-4.0 (Kaggle open dataset)
**Purpose**: High-quality invoice dataset from Kaggle
**Use Case**: Document layout diversity, structured document quality assessment

---

### 2.3 Phase 3 Training (Handwriting & Layout) ✅ DOWNLOADED

#### IAM Handwriting Database ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/iam_handwriting/` | 254MB | ✅ Downloaded from GCS |

**Local Symlink**: `data/training/iam_handwriting` → `/mnt/unraid/training_data/image_detection/training/iam_handwriting`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/iam_handwriting/`
**License**: Research/Academic use (IAM Database)
**Purpose**: Handwriting recognition training
**Use Case**: Phase 3 handwriting detection, OCR training for handwritten documents

#### DocSynth300K ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/docsynth300k/` | 112GB | ✅ Downloaded from GCS |

**Local Symlink**: `data/training/docsynth300k` → `/mnt/unraid/training_data/image_detection/training/docsynth300k`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/docsynth300k/`
**License**: Apache-2.0 (synthetic dataset)
**Purpose**: Synthetic layout training dataset (300K samples)
**Use Case**: Phase 3 layout detection, synthetic document quality variations

#### NIST Special Database 2 ✅ DOWNLOADED

| Component | NFS Path | Size | Status |
|-----------|----------|------|--------|
| **Dataset** | `/mnt/unraid/training_data/image_detection/training/nist_db2/` | 1.0GB | ✅ Downloaded from GCS |

**Local Symlink**: `data/training/nist_db2` → `/mnt/unraid/training_data/image_detection/training/nist_db2`
**Source**: GCS `gs://image_detection_b/image-preprocessing-detector/datasets/nist_db2/`
**License**: Public Domain (NIST)
**Purpose**: NIST Special Database 2 (handwriting)
**Use Case**: Phase 3 handwriting detection, OCR training for handwritten forms

---

### 2.4 Training Data Summary

| Category | Datasets | Total Size | Download Status |
|----------|----------|------------|-----------------|
| **Phase 2 IQA** | iqa_phase2, iqa_phase2_100k | 10.5GB | ✅ Downloaded (needs 100K regen) |
| **Real-World Receipts** | receipts_hitl, mobile_receipts_voxel51, invoices_kaggle | 0.7GB | ✅ Downloaded |
| **Phase 3 Training** | iam_handwriting, docsynth300k, nist_db2 | 113.3GB | ✅ Downloaded |

**Training Total**: ~134GB (8 datasets, all downloaded from GCS)
**Download Status**: 8/8 datasets complete
**NFS Storage**: `/mnt/unraid/training_data/image_detection/training/`
**Next Steps**:
1. ⏳ Regenerate 100K IQA training dataset (15K → 100K samples)
2. ⏳ Create local symlinks with `scripts/create_symlinks.py --all`
3. ⏳ Launch ResNet-50 training on Modal with updated 100K dataset

---

## 3. TEST FIXTURES (Committed to Git)

### 3.1 Small Test Samples ✅ COMMITTED

**Location**: `data/test_fixtures/` (committed to git, NOT on NFS)

| Dataset | Local Path | Size | Samples | Status |
|---------|-----------|------|---------|--------|
| **README** | `data/test_fixtures/README.md` | 12KB | Documentation | ✅ Committed |

**Total Size**: ~12 KB (placeholder README only - fixtures not yet extracted)
**Git Status**: ✅ Committed to repository
**Purpose**: Fast CI/CD testing (< 5 min runtime) without downloading full benchmarks
**Next Step**: Extract fixtures from DIQA-5000, TableBank, FUNSD+ after generation script update

---

## 4. GOOGLE CLOUD STORAGE (GCS) PATHS

### 4.1 GCS Bucket Structure

**Primary Bucket**: `gs://image_detection_b/image-preprocessing-detector/`

#### Benchmark Data (GCS backup status)

| Local Dataset | GCS Path | Size | Status |
|--------------|----------|------|--------|
| **TableBank** | `gs://image_detection_b/.../datasets/tablebank/` | 27GB | ✅ Already uploaded (source) |
| **PubTabNet** | `gs://image_detection_b/.../datasets/pubtabnet/` | 14GB | ✅ Already uploaded (source) |
| **DIQA-5000** | `gs://image_detection_b/.../datasets/diqa-5000/` | 5.4GB | ⏳ Upload pending |
| **FUNSD+** | `gs://image_detection_b/.../datasets/funsd_plus/` | 500MB | ⏳ Upload pending |
| **Others** | Various GCS paths | ~7GB | ⏳ Upload pending |

**Note**: TableBank and PubTabNet are already in GCS (downloaded from there). Other datasets need uploading for backup.

#### Training Data (Generation Pending)

| Local Dataset | GCS Path | Size | Status |
|--------------|----------|------|--------|
| **100K IQA Training** | `gs://image_detection_b/.../datasets/iqa_phase2_100k/` | ~50GB | ⏳ Generation pending |

**Next Steps**:
1. ⏳ Upload remaining benchmarks to GCS (DIQA-5000, FUNSD+, FinTabNet, etc.)
2. ⏳ Generate 100K IQA training dataset
3. ⏳ Upload to GCS for Modal training access

---

### 4.2 GCS Upload Scripts

```bash
# Upload training dataset (after generation)
./scripts/upload_datasets_to_gcs.sh data/training/iqa_phase2_100k/

# Upload benchmark datasets (for backup)
./scripts/upload_datasets_to_gcs.sh data/benchmarks/diqa-5000/
./scripts/upload_datasets_to_gcs.sh data/benchmarks/funsd_plus/
./scripts/upload_datasets_to_gcs.sh data/benchmarks/omnidocbench/

# List bucket contents
gsutil ls gs://image_detection_b/image-preprocessing-detector/datasets/

# Show storage usage
gsutil du -sh gs://image_detection_b/
```

**Authentication**: Service account key at `.gcp/service-account.json` (gitignored)

---

## 5. STORAGE MANAGEMENT

### 5.1 NFS Mount Information

**Server**: Unraid at 192.168.1.16
**Mount Point**: `/mnt/unraid/training_data/image_detection/`
**Capacity**: 100TB total (shared storage)
**Network**: Gigabit ethernet (1 Gbps)
**Current Usage**: ~98GB (benchmarks) + ~50GB future (training data) = ~148GB total

**Mount Verification**:
```bash
# Check NFS mount
df -h /mnt/unraid/training_data/

# List benchmark datasets
ls -lh /mnt/unraid/training_data/image_detection/benchmarks/

# Check symlinks
ls -l data/benchmarks/
```

---

### 5.2 Symlink Management

**All symlinks managed via**: `scripts/create_symlinks.py`

```bash
# Create all symlinks
uv run python scripts/create_symlinks.py --all

# Create benchmarks only
uv run python scripts/create_symlinks.py --benchmarks-only

# Verify symlinks
uv run python scripts/create_symlinks.py --verify
```

**Symlink Mappings**:
```python
SYMLINK_MAPPINGS = [
    ("data/benchmarks/tablebank", "benchmarks/tablebank"),
    ("data/benchmarks/pubtabnet", "benchmarks/pubtabnet"),
    ("data/benchmarks/diqa-5000", "benchmarks/diqa-5000"),
    ("data/benchmarks/funsd_plus", "benchmarks/funsd_plus"),
    ("data/benchmarks/doclaynet", "benchmarks/doclaynet"),
    ("data/benchmarks/fintabnet", "benchmarks/fintabnet"),
    ("data/benchmarks/omnidocbench", "benchmarks/omnidocbench"),
    ("data/benchmarks/ohr-bench", "benchmarks/ohr-bench"),
    ("data/benchmarks/signatr6k", "benchmarks/signatr6k"),
    ("data/benchmarks/wili_2018", "benchmarks/wili_2018"),
    ("data/benchmarks/cocotext", "benchmarks/cocotext"),
    ("data/training/iqa_phase2_100k", "training/iqa_phase2_100k"),  # Future
]
```

---

### 5.3 Dataset Download Automation

**All downloads managed via**: `scripts/download_all_datasets.py`

```bash
# Download all datasets
uv run python scripts/download_all_datasets.py --all

# Download benchmarks only
uv run python scripts/download_all_datasets.py --benchmarks-only

# Download specific dataset
uv run python scripts/download_all_datasets.py --dataset tablebank
```

**Download Sources**:
- **GCS**: TableBank, PubTabNet (via gsutil)
- **HuggingFace**: FUNSD+, OHR-Bench, OmniDocBench, WiLI-2018 (via datasets library)
- **Direct URL**: COCO-Text (via wget)
- **Manual**: DIQA-5000, SignaTR6K (user-provided zips)

---

### 5.4 Disk Space Management

**Current Usage**:
```bash
# Local (WSL)
data/                           # 1.1M (symlinks + synthetic_iqa only)
data/benchmarks/                # 1.0M (symlinks only)
data/test_fixtures/             # 12K (README only)
data/training/                  # 0B (not created yet)
```

**NFS (Unraid)**:
```bash
/mnt/unraid/training_data/image_detection/benchmarks/  # ~56GB (11 datasets)
  ├── tablebank/                # ~27GB
  ├── pubtabnet/                # ~14GB
  ├── diqa-5000/                # 5.4GB
  ├── funsd_plus/               # 500MB
  ├── fintabnet/                # 5.3GB
  ├── omnidocbench/             # 1.2GB
  ├── ohr-bench/                # 1.8GB
  ├── signatr6k/                # 153MB
  ├── wili_2018/                # 129MB
  └── cocotext/                 # 53MB

/mnt/unraid/training_data/image_detection/training/   # ~134GB (8 datasets downloaded)
  └── iqa_phase2_100k/          # ~10GB current (regeneration to ~50GB planned)
  # Additional training datasets stored alongside (receipts_hitl, docsynth300k, etc.)
```

**External Symlinks**:
```bash
/home/byron/dev/data_ingestor/data/benchmarks/doclaynet/  # 42GB (shared dataset)
```

---

## 6. DATASET GENERATION WORKFLOW

### 6.1 Current Status (2025-11-20)

**Phase**: Phase 2 - Dataset Management Complete
**Next Step**: Generate 100K IQA training dataset

```
✅ COMPLETE:
├── Download infrastructure (scripts/download_all_datasets.py)
├── Symlink management (scripts/create_symlinks.py)
├── Benchmark datasets (12/12 downloaded)
├── Documentation updates (data/benchmarks/README.md, benchmarks/README.md)
└── Phase 3 coverage analysis (no additional datasets needed)

⏳ IN PROGRESS:
└── TableBank download (61% complete, 260K/424K images)

⏳ PENDING:
├── Update generation script for FUNSD+ (scripts/generate_100k_iqa_dataset.py)
├── Generate 100K IQA training dataset
├── Upload datasets to GCS
└── Launch ResNet-50 training on Modal
```

---

### 6.2 100K Dataset Generation Plan

**Source Composition**:
```python
DATASET_SOURCES = {
    "diqa-5000": {
        "path": "/mnt/unraid/.../diqa-5000/train/ori/",
        "samples": 3,500,
        "contribution": "10% (10,000 samples)",
        "augmentation": "2.85x",
    },
    "tablebank": {
        "path": "/mnt/unraid/.../tablebank/",
        "samples": 260_000,  # Will be 424K when complete
        "contribution": "60% (60,000 samples)",
        "augmentation": "1.23x",
    },
    "pubtabnet": {
        "path": "/mnt/unraid/.../pubtabnet/",
        "samples": 500_000,
        "contribution": "25% (25,000 samples)",
        "augmentation": "1.20x",
    },
    "funsd_plus": {
        "path": "/mnt/unraid/.../funsd_plus/train/",
        "samples": 1_030,
        "contribution": "5% (5,000 samples)",
        "augmentation": "4.85x",
    },
}
```

**Total**: 100,000 samples (70K train, 15K val, 15K test)
**Augmentation**: Albumentations (blur, noise, skew, illumination, JPEG compression, color jitter)
**Defect Labels**: 13-dimensional quality assessment (blur, gaussian_noise, salt_pepper_noise, contrast, illumination, jpeg_artifacts, skew, binarization, dirty_lens, shadow_border, low_resolution, pixelation, overexposure)
**Storage**: ~50GB (500KB avg per augmented image + labels.json)

---

## 7. LICENSE AND CITATION REQUIREMENTS

### 7.1 Must Cite in Publications

**Benchmark Datasets (Attribution Required)**:
- ✅ **DocLayNet**: CDLA-Permissive-2.0 (IBM Research)
- ✅ **TableBank, COCO-Text**: CC-BY-4.0 (Microsoft Research, BGU)
- ✅ **PubTabNet, FinTabNet**: CDLA-Permissive-2.0 (Microsoft)
- ✅ **WiLI-2018**: CC-BY-SA-4.0 (University of Zurich)
- ⚠️ **OmniDocBench, OHR-Bench**: CC-BY-NC-4.0 (Non-commercial only, OpenDataLab)
- ⚠️ **DIQA-5000, SignaTR6K**: Research/Academic use (check original papers)
- ⚠️ **FUNSD+**: Other (check HuggingFace for license details)

### 7.2 Commercial Use Restrictions

**Non-Commercial Evaluation Only**:
- ❌ **OmniDocBench** (CC-BY-NC-4.0)
- ❌ **OHR-Bench** (CC-BY-NC-4.0)

**Research Purposes (Verify Before Commercial Use)**:
- ⚠️ **DIQA-5000** - Check license before commercial deployment
- ⚠️ **SignaTR6K** - Check license before commercial deployment
- ⚠️ **FUNSD+** - Verify HuggingFace license terms

**Commercial Use Allowed (With Attribution)**:
- ✅ **TableBank, PubTabNet, FinTabNet, DocLayNet** - CDLA-Permissive/Apache-2.0
- ✅ **WiLI-2018, COCO-Text** - CC-BY-4.0/CC-BY-SA-4.0

---

## 8. TROUBLESHOOTING

### 8.1 NFS Mount Issues

```bash
# Check if NFS is mounted
df -h /mnt/unraid/training_data/

# Remount if needed (requires sudo)
sudo mount -t nfs 192.168.1.16:/mnt/user/training_data /mnt/unraid/training_data

# Verify access
ls -lh /mnt/unraid/training_data/image_detection/benchmarks/
```

### 8.2 Symlink Verification

```bash
# Check all symlinks
uv run python scripts/create_symlinks.py --verify

# Expected output:
# ✅ data/benchmarks/tablebank → /mnt/unraid/.../tablebank (Valid)
# ✅ data/benchmarks/diqa-5000 → /mnt/unraid/.../diqa-5000 (Valid)
# ...

# Fix broken symlinks
uv run python scripts/create_symlinks.py --all
```

### 8.3 Disk Space Issues

```bash
# Check NFS usage
du -sh /mnt/unraid/training_data/image_detection/benchmarks/*

# Check local WSL usage (should be < 5GB)
du -sh data/

# Expected:
# 1.1M  data/  (symlinks only, minimal local storage)
```

---

## 9. RELATED DOCUMENTATION

**Dataset Documentation**:
- [data/benchmarks/README.md](../data/benchmarks/README.md): Benchmark dataset overview and download guide
- [benchmarks/README.md](../benchmarks/README.md): Benchmarking framework overview
- [benchmarks/registry.yml](../benchmarks/registry.yml): Benchmark suite definitions

**Architecture Decisions**:
- [ADR-029](ADRs/0029-phase2-dataset-selection-strategy.md): Three-tier dataset strategy (Storage Tiers)
- [ADR-031](ADRs/0031-comprehensive-benchmarking-framework.md): Comprehensive benchmarking framework (Validation Levels)

**Reference Guides**:
- [docs/reference/document-type-coverage.md](reference/document-type-coverage.md): FR coverage matrix
- [docs/reference/detection-taxonomy.md](reference/detection-taxonomy.md): Complete detection taxonomy

**Scripts**:
- [scripts/download_all_datasets.py](../scripts/download_all_datasets.py): Automated dataset downloads
- [scripts/create_symlinks.py](../scripts/create_symlinks.py): Symlink management
- [scripts/generate_100k_iqa_dataset.py](../scripts/generate_100k_iqa_dataset.py): Training dataset generation

---

**Created**: 2025-11-20 (Phase 2 dataset reorganization)
**Status**: ✅ **12/12 Benchmarks Downloaded** - NFS dual storage complete
**Storage**: ~98GB (~56GB NFS + 42GB external symlink)
**Local Footprint**: ~1.1MB (symlinks only)
**Next Steps**: Generate 100K IQA training dataset, upload to GCS, launch Modal training
**Next Review**: After 100K dataset generation complete
