# Data Directory Organization

> **IMPORTANT**: This project now uses **NFS dual-storage** with local symlinks. See [docs/DATASET_LOCATIONS.md](../docs/DATASET_LOCATIONS.md) for authoritative storage locations.
>
> **Storage Strategy (Updated 2025-11-20)**:
>
> - **Local**: Symlinks only (~1MB) - `data/benchmarks/*`, `data/training/*` → NFS
> - **NFS Primary**: `/mnt/unraid/training_data/image_detection/` (~235GB) - All datasets
> - **GCS Backup**: `gs://image_detection_b/` (287GB) - Training datasets + selective benchmarks
>
> **Reference**: This structure implements the three-tier dataset strategy defined in [ADR-029](../docs/ADRs/0029-phase2-dataset-selection-strategy.md).

## Purpose

This directory contains all data used for training, validation, testing, and benchmarking the Image Preprocessing Detector. The organization follows a **strict separation** between training data and evaluation data to prevent data leakage and ensure valid performance metrics.

## Three-Tier Dataset Strategy

### Tier 1: Training Data (Synthetic + Real-World)

**Purpose**: Train machine learning models with permissive licensing for commercial use.

**Location**: `data/training/` (to be created in Phase 2 Week 1)

**Sources**:

- **Synthetic**: 50k samples generated from TableBank (Apache-2.0) with Albumentations augmentation
- **Weak Supervision**: Automated labeling using classical IQA algorithms (BRISQUE, Laplacian variance)
- **Real-World**: Future phases will add scanned receipts, FUNSD for domain diversity

**Structure** (per ADR-029):

```text
data/training/
├── iqa/                        # Image Quality Assessment training data
│   ├── train/                  # 35,000 samples (70%)
│   │   ├── images/
│   │   │   ├── 00000.jpg
│   │   │   └── ...
│   │   └── labels.json         # Multi-label annotations (6 defect types)
│   ├── val/                    # 7,500 samples (15%)
│   │   ├── images/
│   │   └── labels.json
│   ├── test/                   # 7,500 samples (15%)
│   │   ├── images/
│   │   └── labels.json
│   ├── synthetic/              # Source: TableBank + augmentations
│   ├── real/                   # Future: scanned receipts, FUNSD
│   └── annotations/            # Ground-truth labels (weak supervision)
├── layout/                     # Layout detection training (Phase 3)
│   ├── train/
│   ├── val/
│   └── test/
└── metadata.json               # Dataset generation config, versioning
```text

**Key Requirements**:

- ✅ **Never used for benchmarking**: Training data must be separate from evaluation
- ✅ **Permissive licensing**: Apache-2.0, CDLA-Permissive-1.0 (commercial use allowed)
- ✅ **Version controlled**: Generation scripts in `scripts/prepare_phase2_data.py`

**Related ADRs**:

- [ADR-029](../docs/ADRs/0029-phase2-dataset-selection-strategy.md): Three-tier dataset strategy
- [ADR-011](../docs/ADRs/0011-hybrid-validation-strategy.md): Hybrid validation (synthetic + real-world calibration)

### Tier 2: Benchmark Data (Evaluation Only)

**Purpose**: Evaluate model performance against standardized datasets with ground-truth annotations. **NEVER used for training**.

**Location**: `data/benchmarks/` (88+ GB, gitignored)

**Datasets**:

- **External IQA**: LIVE (779 images), CSIQ (866 images), LIVE Challenge (1,162 images)
- **Layout**: DocLayNet (40.97 GB), TableBank (46.38 GB), PubTabNet (970 MB)
- **Specialized**: OmniDocBench (5.95 GB), SignaTR6K (116 MB), Wili-2018 (2.85 GB)
- **Synthetic IQA**: Auto-generated during benchmark runs (validation/)

**Structure**:

```text
data/benchmarks/                # 88+ GB, gitignored
├── external_iqa/               # LIVE, CSIQ, LIVE Challenge (research-only licenses)
│   ├── LIVE/                   # 779 images, DMOS scores
│   ├── CSIQ/                   # 866 images, DMOS scores
│   └── LIVE_Challenge/         # 1,162 images, MOS scores
├── doclaynet/                  # Symlink to /home/byron/dev/data_ingestor/datasets/doclaynet/
├── omnidocbench/               # 5.95 GB, Apache-2.0
├── pubtabnet/                  # 970 MB, MIT
├── tablebank/                  # 46.38 GB, Apache-2.0
├── signatr6k/                  # 116 MB, CC BY 4.0
├── wili_2018/                  # 2.85 GB, Apache-2.0
├── cocotext/                   # Symlink to data_ingestor
├── fintabnet/                  # Symlink to data_ingestor
└── synthetic_iqa/              # Auto-generated during validation runs
```text

**Key Requirements**:

- ❌ **Never used for training**: Strict evaluation-only to prevent overfitting
- ✅ **Ground-truth annotations**: Human-labeled or standardized benchmarks
- ✅ **Standardized metrics**: Enables comparison with research papers

**Download Scripts**:

- `scripts/download_iqa_datasets.py`: Download LIVE, CSIQ, LIVE Challenge
- `scripts/download_omnidocbench.py`: Download OmniDocBench
- `scripts/download_table_datasets.py`: Download TableBank, PubTabNet

**Related ADRs**:

- [ADR-031](../docs/ADRs/0031-comprehensive-benchmarking-framework.md): Registry-based benchmarking
- [ADR-011](../docs/ADRs/0011-hybrid-validation-strategy.md): Real-world validation critical for calibration

**Related Documentation**:

- [benchmarks/README.md](../benchmarks/README.md): Benchmarking framework overview
- [benchmarks/registry.yml](../benchmarks/registry.yml): Suite configurations (40+ benchmarks)
- [docs/PUBLIC_DATASET_COVERAGE.md](../docs/PUBLIC_DATASET_COVERAGE.md): Dataset accessibility analysis

### Tier 3: Test Fixtures (CI/CD)

**Purpose**: Enable fast CI/CD testing without downloading 88+ GB of full datasets. Small representative samples committed to git.

**Location**: `data/test_fixtures/` (828 KB, committed to git)

**Datasets**:

- **CocoText**: 10 images with text annotations
- **DocLayNet**: 5 PDFs with layout annotations
- **OmniDocBench**: 8 samples across document types
- **TableBank**: 5 samples with table annotations
- **Wili-2018**: 10 language samples
- **IQA Samples** (Phase 2): 8 samples from LIVE (blur, noise, contrast) + synthetic variants

**Structure**:

```text
data/test_fixtures/             # 828 KB total, committed to git
├── cocotext/                   # 10 images (text detection)
├── doclaynet/                  # 5 PDFs (layout detection)
├── omnidocbench/               # 8 samples (diverse document types)
├── tablebank/                  # 5 samples (table detection)
├── wili_2018/                  # 10 samples (language ID)
├── iqa_samples/                # NEW: Phase 2 Week 3
│   ├── live/                   # 5 LIVE extracts (blur, noise, contrast)
│   ├── synthetic/              # 3 synthetic variants (edge cases)
│   └── labels.json             # Ground-truth DMOS/MOS scores
└── README.md                   # Test fixtures documentation
```text

**Key Requirements**:

- ✅ **Size constraint**: < 50 MB total (currently 828 KB)
- ✅ **Representative samples**: 5-10 samples per dataset
- ✅ **Fast CI/CD**: No internet required, < 5 min test runtime

**Extraction Scripts**:

- `scripts/extract_test_fixtures.py`: Extract samples from full datasets
- `scripts/extract_iqa_fixtures.py`: Extract LIVE samples (Phase 2 Week 3)

**Related Documentation**:

- [data/test_fixtures/README.md](test_fixtures/README.md): Detailed fixture documentation

## Current Directory Structure

```text
data/
├── annotations/                # Ground-truth annotations (purpose: TBD - clarify vs training/annotations)
├── augmented/                  # Augmented training data (purpose: TBD - clarify vs training/iqa/)
├── benchmarks/                 # Full benchmark datasets (88+ GB, gitignored)
│   ├── cocotext/               # Symlink to data_ingestor
│   ├── external_iqa/           # LIVE, CSIQ, LIVE Challenge
│   ├── fintabnet/              # Symlink to data_ingestor
│   ├── omnidocbench/           # 5.95 GB
│   ├── pubtabnet/              # 970 MB
│   ├── signatr6k/              # 116 MB
│   ├── synthetic_iqa/          # Auto-generated
│   ├── tablebank/              # 46.38 GB
│   └── wili_2018/              # 2.85 GB
├── iqa/                        # Purpose: TBD - clarify vs training/iqa/ vs benchmarks/external_iqa/
├── labels/                     # Label mappings (purpose: clarify)
├── layout/                     # Purpose: TBD - clarify vs training/layout/ vs benchmarks/doclaynet/
├── promptcraft/                # Purpose: TBD - no reference in functional requirements
├── raw/                        # Base clean documents for synthetic generation
│   ├── docbank/
│   ├── rvl-cdip/
│   └── tobacco800/
├── test/                       # Purpose: TBD - clarify vs test_fixtures/
└── test_fixtures/              # Small samples for CI/CD (828 KB, committed)
    ├── cocotext/
    ├── doclaynet/
    ├── omnidocbench/
    ├── tablebank/
    └── wili_2018/
```text

**Known Issues**:

- ⚠️ **Unclear directories**: `iqa/`, `layout/`, `promptcraft/`, `test/`, `annotations/`, `augmented/` have undefined purposes
- ⚠️ **Missing training/**: ADR-029 structure not yet implemented
- ⚠️ **Potential overlap**: Need to clarify purpose vs intended structure

## Intended Directory Structure (ADR-029)

**Target structure for Phase 2 Week 2 migration:**

```text
data/
├── training/                   # NEW: Explicit training data (Tier 1)
│   ├── iqa/                    # IQA training (50k samples, ~18 GB)
│   │   ├── train/              # 70% split
│   │   ├── val/                # 15% split
│   │   ├── test/               # 15% split
│   │   ├── synthetic/          # TableBank + augmentations
│   │   ├── real/               # Future: scanned receipts
│   │   └── annotations/        # Weak supervision labels
│   ├── layout/                 # Phase 3: Layout detection training
│   └── metadata.json           # Generation config
├── benchmarks/                 # Evaluation only (Tier 2) - NO CHANGES
│   ├── external_iqa/
│   ├── doclaynet/
│   ├── omnidocbench/
│   └── ...
├── test_fixtures/              # CI/CD (Tier 3) - NO CHANGES
│   ├── cocotext/
│   ├── doclaynet/
│   └── iqa_samples/            # NEW: Phase 2 Week 3
├── raw/                        # Base documents for generation
│   ├── docbank/
│   ├── rvl-cdip/
│   └── tobacco800/
└── labels/                     # Shared label mappings (class definitions)
```text

**Deprecated/Clarify**:

- ❓ **annotations/**: Migrate to `training/iqa/annotations/` or clarify purpose
- ❓ **augmented/**: Migrate to `training/iqa/synthetic/` or clarify purpose
- ❓ **iqa/**: Migrate to `training/iqa/` or clarify if still needed
- ❓ **layout/**: Migrate to `training/layout/` (Phase 3) or clarify purpose
- ❓ **promptcraft/**: Clarify purpose or remove (not in functional requirements)
- ❓ **test/**: Merge with `test_fixtures/` or clarify distinction

## GCS Integration (Cloud Storage Workflow)

**Reference**: [ADR-030](../docs/ADRs/0030-gcs-colab-training-workflow.md) - GCS-first storage strategy

### GCS Bucket Structure

All datasets (training + benchmarks) are uploaded to Google Cloud Storage for:

- **Training**: Google Colab Pro downloads datasets for GPU training
- **Backup**: Cloud backup of large datasets (88+ GB benchmarks)
- **Sharing**: Distribute datasets across team/environments

```text
gs://image-detection-datasets/           # Primary bucket
├── training/                             # Tier 1: Training data
│   ├── iqa_phase2/                       # 50k samples, ~18 GB
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   ├── layout_phase3/                    # Phase 3 layout training
│   └── metadata.json
├── benchmarks/                           # Tier 2: Evaluation data
│   ├── external_iqa/                     # LIVE, CSIQ, LIVE Challenge (~5 GB)
│   ├── doclaynet/                        # DocLayNet dataset (40.97 GB)
│   ├── omnidocbench/                     # OmniDocBench (5.95 GB)
│   ├── tablebank/                        # TableBank (46.38 GB)
│   └── ...
├── models/                               # Trained models
│   ├── phase2_iqa_v1.pth                 # PyTorch checkpoint
│   ├── phase2_iqa_v1.onnx                # ONNX export (INT8 quantized)
│   └── training_logs/                    # TensorBoard logs
└── checkpoints/                          # Training checkpoints
    └── phase2_iqa_epoch_10.pth
```text

**Note**: Test fixtures (Tier 3) are NOT uploaded to GCS - they're committed to git (< 50 MB).

### Authentication

**Service Account**: `colab-training@image-detection-478105.iam.gserviceaccount.com`

```bash
# scripts/auth_gcs.sh
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Verify authentication
gcloud auth list
gsutil ls gs://image-detection-datasets/
```text

**Security**:

- Service account key stored in `.gcp/service-account.json` (gitignored)
- Read-only permissions for Colab training (safety)
- Read-write permissions for local uploads (developer machine)

**Reference**: [ADR-004](../docs/ADRs/0004-github-actions-security-hardening.md) - Secret management

### Upload/Download Scripts

**scripts/upload_datasets_to_gcs.sh**: Upload local datasets to GCS

```bash
#!/bin/bash
# Upload training datasets (after local generation)
gsutil -m cp -r data/training/iqa_phase2 gs://image-detection-datasets/training/

# Upload benchmark datasets (for cloud access)
gsutil -m cp -r data/benchmarks/external_iqa/LIVE gs://image-detection-datasets/benchmarks/external_iqa/
gsutil -m cp -r data/benchmarks/external_iqa/CSIQ gs://image-detection-datasets/benchmarks/external_iqa/

# Verify upload
gsutil du -sh gs://image-detection-datasets/
```text

**scripts/download_from_gcs.sh**: Download datasets from GCS (for Colab training)

```bash
#!/bin/bash
# Download training dataset in Google Colab
gsutil -m cp -r gs://image-detection-datasets/training/iqa_phase2 /content/datasets/

# Download validation datasets
gsutil -m cp -r gs://image-detection-datasets/benchmarks/external_iqa /content/datasets/
```text

**Performance**:

- **Upload**: ~50-100 MB/s (parallel transfers with `gsutil -m`)
- **Download**: ~100-200 MB/s in Google Colab (same region)
- **Total Upload Time**: ~10-15 minutes for 26 GB (training + validation)

**Reference**: [ADR-030](../docs/ADRs/0030-gcs-colab-training-workflow.md) - GCS performance benchmarks

## Data Flow and Workflows

### 1. Training Data Generation (Phase 2 Week 1)

```bash
# Step 1: Generate 50k synthetic training dataset locally
poetry run python scripts/prepare_phase2_data.py \
  --source=data/raw/tablebank/ \
  --output=data/training/iqa/ \
  --samples=50000 \
  --augmentation=medium \
  --weak-supervision

# Step 2: Validate dataset structure
poetry run python scripts/validate_datasets.py --dataset=data/training/iqa/

# Step 3: Upload to Google Cloud Storage
source scripts/auth_gcs.sh
./scripts/upload_datasets_to_gcs.sh data/training/iqa/ gs://image-detection-datasets/training/iqa_phase2/
```text

### 2. Benchmark Data Download

```bash
# Download external IQA datasets (LIVE, CSIQ, LIVE Challenge)
poetry run python scripts/download_iqa_datasets.py \
  --output=data/benchmarks/external_iqa/

# Download layout datasets (DocLayNet, OmniDocBench)
poetry run python scripts/download_omnidocbench.py \
  --output=data/benchmarks/omnidocbench/

# Download table datasets (TableBank, PubTabNet)
poetry run python scripts/download_table_datasets.py \
  --output=data/benchmarks/
```text

### 3. Test Fixture Extraction (Phase 2 Week 3)

```bash
# Extract IQA test fixtures from LIVE dataset
poetry run python scripts/extract_iqa_fixtures.py \
  --source=data/benchmarks/external_iqa/LIVE/ \
  --output=data/test_fixtures/iqa_samples/ \
  --samples=5

# Commit test fixtures to git
git add data/test_fixtures/iqa_samples/
git commit -m "test: Add IQA test fixtures for CI/CD"
```text

### 4. Running Benchmarks

```bash
# Run smoke tests (20-100 samples, < 5 min)
python -m benchmarks.runners.run_benchmark \
  --suite=iqa_smoke \
  --config=benchmarks/registry.yml

# Run full benchmarks (requires 88+ GB datasets)
python -m benchmarks.runners.run_benchmark \
  --suite=iqa_full \
  --config=benchmarks/registry.yml \
  --output=results/iqa_full_$(date +%Y%m%d).json
```text

### 5. Running Tests

```bash
# Unit tests (no dataset downloads required)
poetry run pytest -v -m "unit"

# Integration tests (uses test fixtures only)
poetry run pytest -v -m "integration"

# Full test suite (includes benchmarks, requires full datasets)
poetry run pytest -v -m "not requires_full_dataset"
```text

## Relationship to Other Directories

### validation/ (Phase 0-1 Prototype)

**Location**: `validation/` (2,105 lines of Python, predates benchmarks framework)

**Purpose**: Early Phase 0-1 validation scripts using synthetic data from Microsoft Genalog

**Status**: ⚠️ **Legacy** - Superseded by `benchmarks/` framework (ADR-031)

**Scripts**:

- `synthetic_generator.py`: Generate synthetic IQA samples (now in `scripts/prepare_phase2_data.py`)
- `validate_detectors.py`: Test classical detectors (now in `benchmarks/runners/`)
- `download_ocr_quality.py`: Download LIVE/CSIQ (now in `scripts/download_iqa_datasets.py`)

**Recommendation**: Archive as `validation_archive/` and migrate scripts to `scripts/` or `benchmarks/` (see migration plan)

**Related ADRs**:

- [ADR-006](../docs/ADRs/0006-synthetic-validation-dataset-strategy.md): Original synthetic validation approach
- [ADR-031](../docs/ADRs/0031-comprehensive-benchmarking-framework.md): Replacement benchmarking framework

### benchmarks/ (Benchmarking Framework)

**Location**: `benchmarks/` (comprehensive testing framework)

**Purpose**: Registry-based benchmarking with progressive validation (fixtures → smoke → full)

**Structure**:

```text
benchmarks/
├── adapters/                   # Dataset adapters (BaseAdapter interface)
├── metrics/                    # Metric calculations (mAP, F1, ECE)
├── scorers/                    # Result aggregation
├── runners/                    # Execution engines
├── registry.yml                # Central suite configuration (40+ benchmarks)
└── README.md                   # Framework documentation
```text

**Related Documentation**:

- [benchmarks/README.md](../benchmarks/README.md): Framework overview
- [benchmarks/registry.yml](../benchmarks/registry.yml): Suite definitions

## Critical Design Principles

### 1. Prevent Data Leakage

**Rule**: Training data (Tier 1) and benchmark data (Tier 2) must be **strictly separated**.

**Why**: Training on benchmark data would invalidate evaluation metrics and overestimate performance.

**Enforcement**:

- `data/training/` and `data/benchmarks/` are separate top-level directories
- No symlinks between training and benchmarks
- Validation scripts check for overlap (see `scripts/validate_datasets.py`)

**Related ADR**: [ADR-029](../docs/ADRs/0029-phase2-dataset-selection-strategy.md) - Explicit separation requirement

### 2. Hybrid Validation (Synthetic + Real-World)

**Rule**: Train on synthetic data (perfect labels), calibrate on real-world data (production distribution).

**Why**: ADR-011 proved that synthetic-only validation can cause catastrophic miscalibration:

- Original contrast threshold (0.18) → **100% false positives** on real-world PDFs
- Calibrated threshold (0.15) → 53% detection (appropriate)

**Implementation**:

- **Training**: `data/training/iqa/synthetic/` (50k samples, weak supervision)
- **Calibration**: `data/benchmarks/external_iqa/` (LIVE, CSIQ - ground-truth)

**Related ADR**: [ADR-011](../docs/ADRs/0011-hybrid-validation-strategy.md) - Critical calibration discovery

### 3. Three-Tier Testing Pyramid

**Rule**: Progressive validation to balance speed and coverage.

**Tiers**:

1. **Test Fixtures** (< 50 MB, committed): Fast CI/CD (< 5 min)
2. **Smoke Tests** (20-100 samples): Quick validation (< 5 min)
3. **Full Benchmarks** (88+ GB): Comprehensive evaluation (hours)

**When to Use**:

- **Development**: Test fixtures for instant feedback
- **Pre-commit**: Smoke tests for rapid validation
- **Release**: Full benchmarks for production readiness

**Related ADR**: [ADR-031](../docs/ADRs/0031-comprehensive-benchmarking-framework.md) - Progressive validation

## Migration Plan

**Timeline**: Phase 2 Weeks 1-3 (before ML training starts)

### Week 1: Documentation (Current)

- ✅ Create `data/README.md` (this file)
- ⏳ Create `docs/DETECTION_TAXONOMY.md` (research-based issue classification)
- ⏳ Update `docs/requirements/functional_requirements_v2.md` (add missing issues)

### Week 2: Restructuring

- ⏳ Create `data/training/` directory structure
- ⏳ Generate 50k synthetic IQA dataset → `data/training/iqa/`
- ⏳ Archive `validation/` → `validation_archive/`
- ⏳ Clarify or remove unclear directories (`iqa/`, `layout/`, `test/`, `promptcraft/`)
- ⏳ Add `.gitkeep` or README to empty directories

### Week 3: Validation

- ⏳ Extract IQA test fixtures → `data/test_fixtures/iqa_samples/`
- ⏳ Verify structure matches ADR-029
- ⏳ Update cross-references in documentation
- ⏳ Validate no data leakage (training vs benchmarks)

**Effort Estimate**: 26 hours (documentation: 8 hours, restructuring: 12 hours, validation: 6 hours)

## License and Citation Requirements

### Permissive Licenses (Commercial Use Allowed)

**Training Data**:

- TableBank: Apache-2.0
- Albumentations: MIT
- Synthetic generation: No restrictions
- **Voxel51 Scanned Receipts**: CC BY 4.0 (713 images) - Attribution required
- **HITL Free Receipt OCR**: CC0 1.0 (192 images) - Public domain, no restrictions
- **Kaggle High-Quality Invoices**: ODbL 1.0 (1,414 annotated images) - Attribution required

**Benchmark Data (Training-Eligible)**:

- **FUNSD**: MIT (199 government forms) - Attribution required

**Benchmark Data (Evaluation-Only)**:

- OmniDocBench: Apache-2.0
- PubTabNet: MIT
- TableBank: Apache-2.0
- Wili-2018: Apache-2.0
- SignaTR6K: CC BY 4.0

### Dataset Citations (Permissive Licenses)

#### Voxel51 Scanned Receipts

**License**: CC BY 4.0 (Commercial use permitted with attribution)
**Source**: <https://huggingface.co/datasets/Voxel51/scanned_receipts>
**Size**: 713 mobile-captured receipt images
**Citation**:

```bibtex
@inproceedings{huang2019icdar,
  title={ICDAR 2019 Competition on Scanned Receipt OCR and Information Extraction},
  author={Huang, Zheng and Chen, Kai and He, Jianhua and Bai, Xiang and Karatzas, Dimosthenis and Lu, Shijian and Jawahar, C.V.},
  booktitle={2019 International Conference on Document Analysis and Recognition (ICDAR)},
  pages={1516--1520},
  year={2019},
  organization={IEEE}
}
```text

#### HITL Free Receipt OCR Dataset

**License**: CC0 1.0 (Public Domain - No attribution required)
**Source**: <https://humansintheloop.org/resources/datasets/free-receipt-ocr-dataset/>
**Size**: 192 annotated receipt images with JSON labels
**Note**: Dedicated to the public domain by Humans in the Loop under CC0 1.0 license

#### Kaggle High-Quality Invoice Images

**License**: ODbL 1.0 (Commercial use permitted with attribution)
**Source**: <https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr>
**Author**: Osama Hosam Abdellatif
**Size**: 1,414 annotated high-resolution invoices (989 train, 425 val)
**Preparation Script**: `scripts/prepare_invoice_dataset.py`

#### FUNSD (Form Understanding in Noisy Scanned Documents)

**License**: MIT (Commercial use permitted with attribution)
**Source**: <https://guillaumejaume.github.io/FUNSD/>
**Size**: 199 annotated government forms (149 train, 50 test)
**Citation**:

```bibtex
@article{jaume2019funsd,
  title={FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents},
  author={Jaume, Guillaume and Ekenel, Hazim Kemal and Thiran, Jean-Philippe},
  journal={2019 International Conference on Document Analysis and Recognition Workshops (ICDARW)},
  volume={2},
  pages={1--6},
  year={2019},
  organization={IEEE}
}
```text

### Research-Only Licenses (Citation Required)

**LIVE, CSIQ, LIVE Challenge**:

- **License**: Academic/Research use only
- **Restriction**: Cannot redistribute commercially
- **Citation**: Required in documentation and publications
- **Usage**: Validation only (not training)

**Citations**:

```bibtex
@article{sheikh2006live,
  title={A statistical evaluation of recent full reference image quality assessment algorithms},
  author={Sheikh, H.R. and Sabir, M.F. and Bovik, A.C.},
  journal={IEEE Transactions on Image Processing},
  year={2006}
}

@article{larson2010csiq,
  title={Most apparent distortion: full-reference image quality assessment and the role of strategy},
  author={Larson, E.C. and Chandler, D.M.},
  journal={Journal of Electronic Imaging},
  year={2010}
}

@article{ghadiyaram2015live,
  title={Massive online crowdsourced study of subjective and objective picture quality},
  author={Ghadiyaram, D. and Bovik, A.C.},
  journal={IEEE Transactions on Image Processing},
  year={2015}
}
```text

## Troubleshooting

### "Dataset not found" errors

```bash
# Check if dataset exists
ls -lh data/benchmarks/external_iqa/LIVE/

# Download if missing
poetry run python scripts/download_iqa_datasets.py --output=data/benchmarks/external_iqa/
```text

### "Insufficient disk space" errors

**Benchmark datasets are large (88+ GB)**:

```bash
# Check available disk space
df -h /home/byron/dev/image_detection/

# Use GCS for large datasets
./scripts/upload_datasets_to_gcs.sh data/benchmarks/ gs://imgprep-datasets/benchmarks/
```text

### "Data leakage" warnings

**Validation scripts detect overlap between training and benchmarks**:

```bash
# Validate dataset separation
poetry run python scripts/validate_datasets.py --check-leakage

# Fix: ensure training/ and benchmarks/ are separate
```text

### Import errors in validation scripts

**Legacy `validation/` scripts need PYTHONPATH**:

```bash
# Validation scripts predate proper package structure
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
  poetry run python validation/validate_detectors.py
```text

## References

**Architecture Decision Records**:

- [ADR-029](../docs/ADRs/0029-phase2-dataset-selection-strategy.md): Three-tier dataset strategy ⭐
- [ADR-031](../docs/ADRs/0031-comprehensive-benchmarking-framework.md): Registry-based benchmarking
- [ADR-011](../docs/ADRs/0011-hybrid-validation-strategy.md): Hybrid validation (synthetic + real-world) ⭐
- [ADR-006](../docs/ADRs/0006-synthetic-validation-dataset-strategy.md): Synthetic validation (Phase 0 prototype)

**Documentation**:

- [benchmarks/README.md](../benchmarks/README.md): Benchmarking framework
- [benchmarks/registry.yml](../benchmarks/registry.yml): 40+ benchmark suite definitions
- [data/test_fixtures/README.md](test_fixtures/README.md): Test fixtures documentation
- [docs/PUBLIC_DATASET_COVERAGE.md](../docs/PUBLIC_DATASET_COVERAGE.md): Dataset accessibility analysis

**Scripts**:

- [scripts/prepare_phase2_data.py](../scripts/prepare_phase2_data.py): Generate synthetic training data
- [scripts/download_iqa_datasets.py](../scripts/download_iqa_datasets.py): Download LIVE, CSIQ, LIVE Challenge
- [scripts/extract_iqa_fixtures.py](../scripts/extract_iqa_fixtures.py): Extract test fixtures
- [scripts/validate_datasets.py](../scripts/validate_datasets.py): Validate dataset structure

---

**Created**: 2025-11-13 (Phase 2 Week 1 - Documentation Phase)
**Status**: 🚧 **In Progress** - Migration to ADR-029 structure pending
**Next Review**: Phase 2 Week 3 (after directory restructuring complete)
