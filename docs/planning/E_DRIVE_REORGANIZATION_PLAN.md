---
schema_type: planning
title: E Drive Data Reorganization Plan
description: Clean up and organize /mnt/e/ for Phase 7 training data management
status: draft
owner: core-maintainer
purpose: Organize local E drive storage structure for Phase 7 training datasets.
component: Development-Tools
source: Manual creation
---

> **Status**: IN PROGRESS - Manual actions required

---

## Migration Status (2025-12-16)

### Completed Moves

| Source | Destination | Status |
|--------|-------------|--------|
| `benchmarks/tablebank` | `01_base_data/tables/tablebank` | ✅ Done |
| `benchmarks/fintabnet` | `01_base_data/tables/fintabnet` | ✅ Done |
| `benchmarks/doclaynet` | `01_base_data/documents/doclaynet` | ✅ Done |
| `v4_datasets/rvl_cdip` | `01_base_data/documents/rvl_cdip` | ✅ Done |
| `benchmarks/nist_db2` | `01_base_data/forms/nist_db2` | ✅ Done |
| `benchmarks/nist_sd6` | `01_base_data/forms/nist_sd6` | ✅ Done |
| `v4_datasets/funsd` | `01_base_data/forms/funsd` | ✅ Done |
| `benchmarks/funsd_plus` | `01_base_data/forms/funsd_plus` | ✅ Done |
| `v4_datasets/sroie` | `01_base_data/forms/sroie` | ✅ Done |
| `v4_datasets/nist_sd19_pages` | `01_base_data/handwriting/nist_sd19_pages` | ✅ Done |
| `v4_datasets/maths_handwriting` | `01_base_data/handwriting/maths_handwriting` | ✅ Done |
| `benchmarks/signatr6k` | `01_base_data/handwriting/signatr6k` | ✅ Done |
| `benchmarks_hf/im2latex` | `01_base_data/formulas/im2latex` | ✅ Done |
| `benchmarks_hf/mathverse` | `01_base_data/formulas/mathverse` | ✅ Done |
| `benchmarks/multimodal_textbook` | `01_base_data/educational/multimodal_textbook` | ✅ Done |
| `benchmarks/sample_100_images` | `01_base_data/educational/sample_100_images` | ✅ Done |
| `benchmarks/*.json (textbook)` | `01_base_data/educational/` | ✅ Done |
| `v4_datasets/tobacco800` | `01_base_data/degraded/tobacco800` | ✅ Done |
| `v4_datasets/historical_degraded` | `01_base_data/degraded/historical_degraded` | ✅ Done |
| `benchmarks/diqa-5000` | `02_benchmark_only/diqa-5000` | ✅ Done |
| `benchmarks/dibco` | `02_benchmark_only/dibco` | ✅ Done |
| `benchmarks/ohr-bench` | `02_benchmark_only/ohr-bench` | ✅ Done |
| `benchmarks/omnidocbench` | `02_benchmark_only/omnidocbench` | ✅ Done |
| `benchmarks/smartdoc-qa` | `02_benchmark_only/smartdoc-qa` | ✅ Done |
| `iqa_phase7_150k_v3/images` | `03_training_datasets/phase7_v3/images` | ✅ Done |
| `iqa_phase7_150k_v3/*metadata*.json` | `03_training_datasets/phase7_v3/metadata/` | ✅ Done |
| `benchmarks/*.zip` | `07_archives/source_zips/` | ✅ Done |
| `iqa_phase7_150k_v3/archives/*.tar.gz` | `07_archives/dataset_backups/` | ✅ Done |
| `v4_staging/candidates/*` | `06_staging/candidates/` | ✅ Done |
| `v4_staging/forms` | `06_staging/forms` | ✅ Done |

### Manual Actions Required (Use Windows Explorer)

| Source | Destination | Reason |
|--------|-------------|--------|
| `benchmarks/pubtabnet` | `01_base_data/tables/pubtabnet` | ✅ DONE |

### Directories with Remaining Content (DUPLICATES - Review Before Deleting)

| Directory | Remaining Contents | Action Needed |
|-----------|-------------------|---------------|
| `benchmarks/` | `cocotext/`, `wili_2018/` | Decide: move to base_data or delete |
| `v4_datasets/` | `dibco/`, `docvqa/`, `funsd_plus/`, `mathverse/`, `multimodal_textbook/`, `ohr_bench/` | **DUPLICATES** - verify then delete |
| `benchmarks_hf/` | `multimodal_textbook/`, `ohr_bench/` | **DUPLICATES** - verify then delete |
| `v4_staging/` | `candidates/`, `filtered/`, `rejected/`, `selected/` (empty?) | Verify empty, then delete |
| `iqa_phase7_150k_v3/` | `archives/` (empty), `archives_clean/` (manifest only) | Verify, then delete |
| `iqa_datasets/` | `LIVE/` | Legacy dataset - decide to keep or archive |

### Duplicate Analysis

The following directories exist in BOTH old and new locations:

1. **DIBCO**: `v4_datasets/dibco/` vs `02_benchmark_only/dibco/` (from benchmarks)
2. **FUNSD+**: `v4_datasets/funsd_plus/` vs `01_base_data/forms/funsd_plus/` (from benchmarks)
3. **MathVerse**: `v4_datasets/mathverse/` vs `01_base_data/formulas/mathverse/` (from benchmarks_hf)
4. **OHR-Bench**: `v4_datasets/ohr_bench/` AND `benchmarks_hf/ohr_bench/` vs `02_benchmark_only/ohr-bench/`
5. **Multimodal Textbook**: `v4_datasets/multimodal_textbook/` AND `benchmarks_hf/multimodal_textbook/` vs `01_base_data/educational/`

---

## Current State Analysis

### Current Directory Structure

```
/mnt/e/
├── huggingface_cache/           # 621 GB - HuggingFace download cache
│   ├── datasets/
│   └── hub/
└── image_detection/
    ├── benchmarks/              # Mixed: base data + benchmark datasets + archives
    ├── benchmarks_hf/           # HuggingFace-sourced benchmarks (im2latex, mathverse)
    ├── iqa_datasets/            # Legacy (LIVE dataset only)
    ├── iqa_phase7_150k_v3/      # Phase 7 v3 training dataset with archives
    ├── v4_datasets/             # Downloaded v4 source datasets
    └── v4_staging/              # Candidate selection for v4 training
```

### Issues Identified

1. **Mixed Content in `benchmarks/`**:
   - Contains both training base data AND benchmark-only datasets
   - Contains unextracted zip files (hsf_page.zip, by_class.zip, etc.)
   - Contains extracted and compressed versions of same data
   - Large JSON files (multimodal_textbook.json ~23 GB combined)

2. **Duplicate Data Paths**:
   - `v4_datasets/dibco/` AND `benchmarks/dibco/`
   - `v4_datasets/funsd/` AND `benchmarks/funsd_plus/`
   - `v4_datasets/mathverse/` AND `benchmarks_hf/mathverse/`
   - `v4_datasets/ohr_bench/` AND `benchmarks/ohr-bench/`

3. **Unclear Naming**:
   - `iqa_datasets/` only contains legacy LIVE dataset
   - `benchmarks_hf/` duplicates structure with `v4_datasets/`

4. **Archive Accumulation**:
   - 46 archive files (.zip, .tar.gz) scattered across directories
   - Some extracted, some not
   - Consuming unnecessary space

---

## Proposed Directory Structure

```
/mnt/e/
├── image_detection/
│   │
│   ├── 01_base_data/                    # SOURCE: Clean base images for training
│   │   ├── tables/
│   │   │   ├── tablebank/               # 260,025 images
│   │   │   ├── pubtabnet/               # 519,030 images
│   │   │   └── fintabnet/               # 97,475 images
│   │   ├── documents/
│   │   │   ├── doclaynet/               # 81,471 pages
│   │   │   └── rvl_cdip/                # ~15,986 mixed documents
│   │   ├── forms/
│   │   │   ├── nist_db2/                # 5,590 tax forms
│   │   │   ├── nist_sd6/                # 5,595 census forms
│   │   │   ├── funsd/                   # 199 annotated forms
│   │   │   ├── funsd_plus/              # ~1,139 extended forms
│   │   │   └── sroie/                   # 1,000 receipts
│   │   ├── handwriting/
│   │   │   ├── iam/                     # (to download) 13,353 lines
│   │   │   ├── nist_sd19_pages/         # 3,669 pages
│   │   │   ├── maths_handwriting/       # 15,000 symbols
│   │   │   └── signatr6k/               # 12,514 signatures
│   │   ├── formulas/
│   │   │   ├── im2latex/                # 10,000 rendered formulas
│   │   │   └── mathverse/               # ~3,000 math diagrams
│   │   ├── educational/
│   │   │   └── multimodal_textbook/     # Sample: 1,113 images + annotations
│   │   └── degraded/
│   │       ├── tobacco800/              # ~1,600 archival docs
│   │       └── historical_degraded/     # ~190 palm leaf + LRDE
│   │
│   ├── 02_benchmark_only/               # RESERVED: Never use for training
│   │   ├── diqa-5000/                   # 5,500 images with MOS scores
│   │   ├── anyphotodoc-6300/            # AnyPhotoDoc benchmark
│   │   ├── roor/                        # ROOR benchmark
│   │   ├── omnidocbench/                # OmniDocBench benchmark
│   │   ├── smartdoc-qa/                 # SmartDoc QA benchmark
│   │   ├── dibco/                       # DIBCO 2009-2017 (100 images)
│   │   └── ohr-bench/                   # OCR Hallucination benchmark
│   │
│   ├── 03_training_datasets/            # GENERATED: Augmented + labeled
│   │   ├── phase2_100k/                 # Binary labels (legacy)
│   │   │   ├── train/
│   │   │   ├── val/
│   │   │   └── test/
│   │   ├── phase7_v3/                   # Continuous labels (current)
│   │   │   ├── train/                   # 107,636 samples
│   │   │   ├── val/                     # 23,207 samples
│   │   │   ├── test/                    # 23,398 samples
│   │   │   └── metadata/                # Split metadata JSONs
│   │   └── phase7_v4/                   # (future) Production dataset
│   │       ├── train/
│   │       ├── val/
│   │       ├── test/
│   │       └── metadata/
│   │
│   ├── 04_checkpoints/                  # MODEL: Training checkpoints
│   │   ├── phase2/
│   │   │   └── resnet50_binary/
│   │   ├── phase7_v3/
│   │   │   ├── resnet50_teacher/
│   │   │   └── resnet18_student/
│   │   └── phase7_v4/
│   │       ├── resnet50_teacher/
│   │       └── resnet18_student/
│   │
│   ├── 05_models/                       # FINAL: Production-ready models
│   │   ├── phase2/
│   │   │   ├── resnet50_best.pth
│   │   │   └── resnet50_best.onnx
│   │   ├── phase7_v3/
│   │   │   ├── teacher_best.pth
│   │   │   ├── student_best.pth
│   │   │   └── student_best.onnx
│   │   └── phase7_v4/
│   │       ├── teacher_best.pth
│   │       ├── student_best.pth
│   │       └── student_best.onnx
│   │
│   ├── 06_staging/                      # TEMP: Dataset preparation workspace
│   │   ├── candidates/                  # Pre-selection pool by domain
│   │   ├── selected/                    # Verified selections
│   │   ├── filtered/                    # Rejected (quality/duplicates)
│   │   └── augmented/                   # Post-augmentation before split
│   │
│   └── 07_archives/                     # COLD: Compressed backups
│       ├── source_zips/                 # Original download archives
│       ├── dataset_backups/             # Compressed training datasets
│       └── checkpoint_backups/          # Old checkpoint archives
│
└── huggingface_cache/                   # Can be cleared after data extracted
    ├── datasets/
    └── hub/
```

---

## Data Categories

### 1. Base Data (01_base_data/)

**Purpose**: Clean source images available for training augmentation

| Directory | Source | Images | Domain | License |
|-----------|--------|--------|--------|---------|
| tables/tablebank | Microsoft | 260,025 | Tables | CC-BY-4.0 |
| tables/pubtabnet | IBM | 519,030 | Scientific | CDLA-Permissive |
| tables/fintabnet | IBM | 97,475 | Financial | Custom |
| documents/doclaynet | IBM | 81,471 | Mixed | CDLA-Permissive |
| documents/rvl_cdip | Ryerson | 15,986 | Mixed | Academic |
| forms/nist_db2 | NIST | 5,590 | Tax | Public Domain |
| forms/nist_sd6 | NIST | 5,595 | Census | Public Domain |
| forms/funsd | IBM | 199 | Generic | CC-BY-4.0 |
| forms/funsd_plus | Extended | 1,139 | Generic | CC-BY-4.0 |
| forms/sroie | ICDAR | 1,000 | Receipts | Custom |
| handwriting/nist_sd19_pages | NIST | 3,669 | Pages | Public Domain |
| handwriting/maths_handwriting | HASYv2 | 15,000 | Symbols | CC0 |
| handwriting/signatr6k | Research | 12,514 | Signatures | Academic |
| formulas/im2latex | Harvard | 10,000 | LaTeX | MIT |
| formulas/mathverse | Research | 3,000 | Math | CC-BY-4.0 |
| educational/multimodal_textbook | DAMO | 1,113+ | STEM | Apache-2.0 |
| degraded/tobacco800 | IIT | 1,600 | Archival | Academic |
| degraded/historical_degraded | Mixed | 190 | Historical | Various |

**Total**: ~1.03M base images available

### 2. Benchmark-Only (02_benchmark_only/)

**Purpose**: Reserved ONLY for model evaluation - NEVER used in training

| Dataset | Images | Purpose | Ground Truth |
|---------|--------|---------|--------------|
| **DIQA-5000** | 5,500 | IQA calibration | Human MOS scores |
| **AnyPhotoDoc-6300** | 6,300 | Photo document IQA | Human ratings |
| **ROOR** | TBD | Real-world OCR quality | OCR accuracy |
| **OmniDocBench** | TBD | Multi-task evaluation | Multiple |
| **SmartDoc-QA** | TBD | Mobile capture QA | QA accuracy |
| **DIBCO** | 100 | Historical degradation | Binarization GT |
| **OHR-Bench** | 1,358 | OCR hallucination | OCR accuracy |

**Critical**: These datasets must NEVER leak into training to preserve benchmark validity.

### 3. Training Datasets (03_training_datasets/)

**Purpose**: Augmented, labeled datasets ready for model training

| Dataset | Samples | Labels | Status |
|---------|---------|--------|--------|
| phase2_100k | 99,630 | Binary 0/1 | Legacy |
| phase7_v3 | 154,241 | Continuous [0,1] | Current |
| phase7_v4 | ~200,000 | Continuous [0,1] | Planned |

Each dataset directory contains:

- `train/`: Training images
- `val/`: Validation images
- `test/`: Test images
- `metadata/`: Split metadata, label files, generation configs

### 4. Checkpoints (04_checkpoints/)

**Purpose**: Training checkpoints for resumption and analysis

Structure per phase:

```
phase7_v3/
├── resnet50_teacher/
│   ├── epoch_001.pth
│   ├── epoch_002.pth
│   ├── ...
│   └── best_ece.pth
└── resnet18_student/
    ├── epoch_001.pth
    └── ...
```

### 5. Models (05_models/)

**Purpose**: Final production-ready models

Each model includes:

- PyTorch checkpoint (`.pth`)
- ONNX export (`.onnx`)
- Model card (`MODEL_CARD.md`)
- Inference config (`config.yaml`)

### 6. Staging (06_staging/)

**Purpose**: Temporary workspace for dataset preparation

- `candidates/`: Domain-sorted images for selection
- `selected/`: Quality-verified selections
- `filtered/`: Rejected images (duplicates, low quality)
- `augmented/`: Post-augmentation before final split

### 7. Archives (07_archives/)

**Purpose**: Cold storage for compressed backups

- `source_zips/`: Original downloaded archives
- `dataset_backups/`: Compressed training datasets
- `checkpoint_backups/`: Archived old checkpoints

---

## Migration Plan

### Phase 1: Create Directory Structure

```bash
# Create new directory tree
mkdir -p /mnt/e/image_detection/{01_base_data,02_benchmark_only,03_training_datasets,04_checkpoints,05_models,06_staging,07_archives}

# Create subdirectories
mkdir -p /mnt/e/image_detection/01_base_data/{tables,documents,forms,handwriting,formulas,educational,degraded}
mkdir -p /mnt/e/image_detection/02_benchmark_only/{diqa-5000,anyphotodoc-6300,roor,omnidocbench,smartdoc-qa,dibco,ohr-bench}
mkdir -p /mnt/e/image_detection/03_training_datasets/{phase2_100k,phase7_v3,phase7_v4}/{train,val,test,metadata}
mkdir -p /mnt/e/image_detection/04_checkpoints/{phase2,phase7_v3,phase7_v4}
mkdir -p /mnt/e/image_detection/05_models/{phase2,phase7_v3,phase7_v4}
mkdir -p /mnt/e/image_detection/06_staging/{candidates,selected,filtered,augmented}
mkdir -p /mnt/e/image_detection/07_archives/{source_zips,dataset_backups,checkpoint_backups}
```

### Phase 2: Move Base Data

```bash
# Tables
mv benchmarks/tablebank 01_base_data/tables/
mv benchmarks/pubtabnet 01_base_data/tables/
mv benchmarks/fintabnet 01_base_data/tables/

# Documents
mv benchmarks/doclaynet 01_base_data/documents/
mv v4_datasets/rvl_cdip 01_base_data/documents/

# Forms
mv benchmarks/nist_db2 01_base_data/forms/
mv benchmarks/nist_sd6 01_base_data/forms/
mv v4_datasets/funsd 01_base_data/forms/
mv benchmarks/funsd_plus 01_base_data/forms/
mv v4_datasets/sroie 01_base_data/forms/

# Handwriting
mv v4_datasets/nist_sd19_pages 01_base_data/handwriting/
mv v4_datasets/maths_handwriting 01_base_data/handwriting/
mv benchmarks/signatr6k 01_base_data/handwriting/

# Formulas
mv benchmarks_hf/im2latex 01_base_data/formulas/
mv benchmarks_hf/mathverse 01_base_data/formulas/

# Educational
mv benchmarks/multimodal_textbook 01_base_data/educational/
mv benchmarks/sample_100_images 01_base_data/educational/multimodal_textbook/sample_images

# Degraded
mv v4_datasets/tobacco800 01_base_data/degraded/
mv v4_datasets/historical_degraded 01_base_data/degraded/
```

### Phase 3: Move Benchmark-Only Data

```bash
# Benchmark datasets (NEVER use for training)
mv benchmarks/diqa-5000 02_benchmark_only/
mv benchmarks/dibco 02_benchmark_only/
mv benchmarks/ohr-bench 02_benchmark_only/
mv benchmarks/omnidocbench 02_benchmark_only/
mv benchmarks/smartdoc-qa 02_benchmark_only/

# Note: AnyPhotoDoc-6300 and ROOR may need download
```

### Phase 4: Move Training Datasets

```bash
# Phase 7 v3
mv iqa_phase7_150k_v3/images 03_training_datasets/phase7_v3/
mv iqa_phase7_150k_v3/*metadata*.json 03_training_datasets/phase7_v3/metadata/
```

### Phase 5: Consolidate Archives

```bash
# Move all archives to cold storage
mv benchmarks/*.zip 07_archives/source_zips/
mv benchmarks/*.tar.gz 07_archives/source_zips/ 2>/dev/null
mv iqa_phase7_150k_v3/archives/*.tar.gz 07_archives/dataset_backups/
```

### Phase 6: Cleanup Duplicates

```bash
# Remove duplicate directories (verify contents first!)
rm -rf v4_datasets/dibco     # Duplicate of 02_benchmark_only/dibco
rm -rf v4_datasets/funsd_plus # Duplicate of 01_base_data/forms/funsd_plus
rm -rf v4_datasets/mathverse  # Duplicate of 01_base_data/formulas/mathverse
rm -rf v4_datasets/ohr_bench  # Duplicate of 02_benchmark_only/ohr-bench

# Remove empty directories
rm -rf benchmarks_hf  # Contents moved to 01_base_data
rm -rf v4_datasets    # Contents moved to 01_base_data
rm -rf v4_staging     # Replaced by 06_staging
rm -rf iqa_datasets   # Legacy, only contained LIVE
```

---

## Validation Checklist

After migration, verify:

- [ ] All base data accessible under `01_base_data/`
- [ ] Benchmark datasets isolated in `02_benchmark_only/`
- [ ] Training datasets have proper train/val/test splits
- [ ] No duplicate data across directories
- [ ] Archives consolidated in `07_archives/`
- [ ] Empty old directories removed
- [ ] Total storage reduced by removing duplicates

---

## Storage Estimates

| Category | Estimated Size | Notes |
|----------|---------------|-------|
| 01_base_data | ~100-150 GB | Extracted images |
| 02_benchmark_only | ~15-20 GB | Reserved benchmarks |
| 03_training_datasets | ~50-100 GB | Augmented datasets |
| 04_checkpoints | ~5-10 GB | Training checkpoints |
| 05_models | ~1-2 GB | Final models |
| 06_staging | Variable | Temp workspace |
| 07_archives | ~50-100 GB | Compressed backups |
| huggingface_cache | 621 GB | Can clear after extraction |

**Potential savings**: 100-200 GB by removing duplicates and clearing HF cache

---

## Notes

1. **HuggingFace Cache**: After verifying all data extracted, can clear `/mnt/e/huggingface_cache/` to save ~621 GB

2. **Large JSON Files**: The multimodal_textbook JSON files (~23 GB) should stay with their dataset in `01_base_data/educational/`

3. **Benchmark Isolation**: The `02_benchmark_only/` directory should have read-only permissions to prevent accidental use in training

4. **GCS Sync**: Update any GCS sync scripts to reflect new directory structure
