# scripts/

**Purpose**: Operational utilities for datasets, training, deployment, and cloud operations.

## What Goes Here

**✅ Belongs in scripts/**:
- Dataset download and preparation
- GCS/Google Drive sync utilities
- Training and checkpoint management
- Colab integration utilities
- Dataset validation and integrity checks
- PDF resolution validation
- Workflow validation

**❌ Does NOT belong here** (and where it should go instead):
- **Documentation tools** → `tools/` (pre-commit hooks, docs generation)
- **Training code** → `src/` (model implementation)
- **Testing code** → `tests/` (unit/integration tests)
- **Build tools** → `noxfile.py`, `pyproject.toml` (build configuration)

## Current Scripts

### Dataset Operations

#### Download Scripts

**`download_phase3_datasets.py`** (Phase 3+, NEW)
- Downloads 4 Phase 3+ datasets from HuggingFace and GitHub
- Datasets: OHR-Bench (10 GB), DocSynth-300K (113 GB), PubTables-1M (25 GB), IAM (266 MB)
- Features: Resumable downloads, parallel workers, priority-based ordering
- Usage: `poetry run python scripts/download_phase3_datasets.py [--dataset DATASET] [--dry-run]`

**`download_iqa_datasets.py`** (Phase 2)
- Downloads IQA benchmark datasets for image quality assessment
- Datasets: FUNSD, Signature-6K, Synthetic IQA
- Usage: `poetry run python scripts/download_iqa_datasets.py`

**`download_omnidocbench.py`** (Phase 2)
- Downloads OmniDocBench dataset for document understanding
- Size: ~1.16 GB
- Usage: `poetry run python scripts/download_omnidocbench.py`

**`download_table_datasets.py`** (Phase 3)
- Downloads table structure detection datasets
- Datasets: TableBank (74 GB), PubTabNet (27 GB), FinTabNet (14 GB)
- Usage: `poetry run python scripts/download_table_datasets.py`

#### Preparation Scripts

**`prepare_invoice_dataset.py`** (Phase 2, NEW)
- Prepares invoice training dataset from Kaggle source
- Processes 1,414 invoice images
- Usage: `poetry run python scripts/prepare_invoice_dataset.py`

**`prepare_phase2_data.py`** (Phase 2)
- Prepares Phase 2 training data for ML model training
- Handles receipts, mobile receipts, and invoices
- Usage: `poetry run python scripts/prepare_phase2_data.py`

#### Extraction Scripts

**`extract_test_fixtures.py`**
- Extracts test fixtures from datasets for unit testing
- Creates representative samples for fast test execution
- Usage: `poetry run python scripts/extract_test_fixtures.py`

**`extract_wili_samples.py`** (Phase 3)
- Extracts WiLI language identification samples
- Dataset: WiLI-2018 (~128 MB)
- Usage: `poetry run python scripts/extract_wili_samples.py`

#### Validation Scripts

**`validate_datasets.py`**
- Validates dataset integrity and structure
- Checks file counts, sizes, and required fields
- Usage: `poetry run python scripts/validate_datasets.py`

**`validate_pdf_resolution.py`** (Phase 1B, NEW)
- Validates PDF resolution for DPI upscaling
- Detects documents below 300 DPI threshold
- Usage: `poetry run python scripts/validate_pdf_resolution.py`

### Cloud Operations (GCS/Google Drive)

#### GCS Scripts

**`auth_gcs.sh`**
- Authenticates with Google Cloud Storage
- Sets up service account credentials
- Usage: `source scripts/auth_gcs.sh`

**`gcs_helpers.sh`**
- Helper functions for GCS operations
- Provides upload, download, and sync utilities
- Usage: `source scripts/gcs_helpers.sh` (library)

**`upload_datasets_to_gcs.sh`** (UPDATED)
- Uploads datasets to GCS for backup and Colab training access
- Supports 17 datasets including Phase 3+ datasets
- Features: Dry-run mode, dataset-specific upload, progress tracking
- Usage: `./scripts/upload_datasets_to_gcs.sh [--dry-run] [--dataset NAME] [--list]`

#### Google Drive Scripts

**`gdrive_sync.py`**
- Syncs datasets to Google Drive for alternative backup
- Provides redundancy for large datasets
- Usage: `poetry run python scripts/gdrive_sync.py`

#### Colab Integration

**`colab_utils.py`**
- Google Colab utility functions for cloud training
- Handles dataset mounting, GPU setup, and output sync
- Usage: Import in Colab notebooks

### Training Utilities

**`checkpoint_manager.py`** (Phase 2+)
- Manages model training checkpoints
- Features: Best model tracking, checkpoint cleanup, resume training
- Usage: Import in training scripts

### Monitoring & Validation

**`check_download_progress.sh`** (NEW)
- Monitors background dataset downloads in real-time
- Shows download status, sizes, and file counts
- Usage: `./scripts/check_download_progress.sh`

**`validate-workflows.sh`**
- Validates GitHub Actions workflow YAML syntax
- Prevents invalid workflow files from breaking CI/CD
- Usage: `./scripts/validate-workflows.sh`

## Distinction from Other Folders

### vs. tools/
- **scripts/**: Operational utilities for datasets, training, deployment
- **tools/**: Development and quality assurance tools (pre-commit, docs generation)

### vs. src/
- **scripts/**: Standalone operational utilities
- **src/**: Core library code and model implementations

### vs. tests/
- **scripts/**: Dataset preparation and validation
- **tests/**: Runtime test execution (pytest)

### vs. monitoring/
- **scripts/**: Development and training operations
- **monitoring/**: Runtime monitoring (post-deployment, Phase 4+)

## Common Workflow Patterns

### Dataset Download and Upload
```bash
# 1. Download Phase 3+ datasets
poetry run python scripts/download_phase3_datasets.py --dataset all

# 2. Monitor download progress
./scripts/check_download_progress.sh

# 3. Validate dataset integrity
poetry run python scripts/validate_datasets.py

# 4. Upload to GCS for backup and Colab access
./scripts/upload_datasets_to_gcs.sh --dry-run  # Preview
./scripts/upload_datasets_to_gcs.sh            # Execute
```

### Phase 2 Training Data Preparation
```bash
# 1. Download IQA datasets
poetry run python scripts/download_iqa_datasets.py

# 2. Prepare invoice dataset
poetry run python scripts/prepare_invoice_dataset.py

# 3. Prepare Phase 2 training data
poetry run python scripts/prepare_phase2_data.py

# 4. Upload to GCS
./scripts/upload_datasets_to_gcs.sh --dataset invoices_kaggle
```

### GCS Setup
```bash
# 1. Authenticate with GCS
source scripts/auth_gcs.sh

# 2. Test connection
./scripts/upload_datasets_to_gcs.sh --list

# 3. Upload specific dataset
./scripts/upload_datasets_to_gcs.sh --dataset ohr_bench
```

## Adding New Scripts

When creating a new operational script:

1. **Location**: Add to `scripts/` directory
2. **Naming**: Use descriptive names (`download_*.py`, `prepare_*.py`, `validate_*.py`)
3. **Documentation**: Add docstring and README section
4. **Dependencies**: Declare in `pyproject.toml` under appropriate group
5. **Error Handling**: Return non-zero exit codes on failure
6. **Logging**: Use `logging` module with consistent format

## Best Practices

1. **Idempotent**: Scripts should be safe to run multiple times
2. **Resumable**: Support resuming interrupted operations (downloads, uploads)
3. **Progress**: Show progress for long-running operations
4. **Validation**: Validate inputs and outputs
5. **Error Handling**: Clear error messages with actionable guidance
6. **Logging**: Structured logging with timestamps and severity levels
7. **Documentation**: Clear usage instructions and examples
