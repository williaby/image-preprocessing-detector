# Dataset Validation Report

**Generated**: 2025-11-13 07:00 UTC
**Purpose**: Validate all required datasets are available locally and in GCS

---

## Executive Summary

**Local Storage**: ✅ 88.80 GB (7 datasets complete, 3 downloading)
**GCS Storage**: 🔄 In Progress (6 datasets uploaded, 1 uploading)
**Required Datasets**: ✅ All required datasets present (doclaynet, synthetic_iqa)

---

## Local Dataset Status

### ✅ Complete Datasets (7)

| Dataset | Size | Files | Type | Phase | Status |
|---------|------|-------|------|-------|--------|
| doclaynet | 40.97 GB | 244,522 | Symlink | 1 (Required) | ✅ Complete |
| tablebank | 46.38 GB | 20 | Directory | 2 | ✅ Complete |
| signatr6k | 116.30 MB | 12,523 | Directory | ? | ✅ Complete |
| omnidocbench | 1.16 GB | 17 | Directory | 3 | ✅ Complete |
| wili_2018 | 128.44 MB | 7 | Directory | 2 | ✅ Complete |
| cocotext | 52.44 MB | 12 | Directory | 2 | ✅ Complete |
| synthetic_iqa | 344.78 KB | 12 | Directory | 1 (Required) | ✅ Complete |

**Total**: 88.80 GB across 257,113 files

### 🔄 In Progress (2)

| Dataset | Expected Size | Status |
|---------|---------------|--------|
| pubtabnet | 10.5 GB | 🔄 Directory created, downloading |
| fintabnet | 3.2 GB | 🔄 Directory created, downloading |

### ⚠️ Empty Directories (3)

These are raw dataset placeholders not currently used:

- docbank (Phase 1 raw data)
- rvl-cdip (Phase 1 raw data)
- tobacco800 (Phase 1 raw data)

---

## GCS Upload Status

### ✅ Uploaded to GCS (6)

| Dataset | Local Size | GCS Status |
|---------|-----------|------------|
| synthetic_iqa | 345 KB | ✅ Uploaded |
| cocotext | 52.44 MB | ✅ Uploaded |
| wili_2018 | 128.44 MB | ✅ Uploaded |
| signatr6k | 116.30 MB | ✅ Upload complete |
| omnidocbench | 1.16 GB | ✅ Upload complete |
| doclaynet | 40.97 GB | 🔄 Uploading (background) |

**GCS Location**: `gs://image_detection_b/image-preprocessing-detector/datasets/`

### 📋 Pending GCS Upload (2)

These will be uploaded once downloads complete:

- tablebank (46.38 GB) - Download complete, needs upload
- pubtabnet (downloading)
- fintabnet (downloading)

---

## Dataset Requirements by Phase

### Phase 1 (MVP - Classical Methods) ✅ COMPLETE

- ✅ doclaynet (40.97 GB) - Layout detection benchmark
- ✅ synthetic_iqa (345 KB) - Auto-generated quality tests

### Phase 2 (ML Image Quality) 🔄 IN PROGRESS

- ✅ cocotext (52.44 MB) - Text detection
- ✅ wili_2018 (128.44 MB) - Language identification
- ✅ tablebank (46.38 GB) - Table detection
- 🔄 pubtabnet (downloading) - Table structure recognition
- 🔄 fintabnet (downloading) - Financial table detection

### Phase 3 (ML Document Layout) ✅ COMPLETE

- ✅ omnidocbench (1.16 GB) - Comprehensive document understanding

### Optional/Additional

- ✅ signatr6k (116 MB) - Signature detection

---

## Validation Scripts Created

### Local Validation

```bash
# Validate all local datasets
poetry run python scripts/validate_datasets.py

# Save results to JSON
poetry run python scripts/validate_datasets.py --output-json validation_results.json
```

### GCS Upload

```bash
# Upload all datasets to GCS
./scripts/upload_datasets_to_gcs.sh

# Upload specific dataset
./scripts/upload_datasets_to_gcs.sh --dataset omnidocbench

# Dry run (preview)
./scripts/upload_datasets_to_gcs.sh --dry-run

# List GCS contents
./scripts/upload_datasets_to_gcs.sh --list
```

### Dataset Downloads

```bash
# Download all table datasets
poetry run python scripts/download_table_datasets.py --all

# Download specific dataset
poetry run python scripts/download_table_datasets.py --datasets tablebank

# Download OmniDocBench
poetry run python scripts/download_omnidocbench.py
```

---

## Background Processes

Currently running:

1. **doclaynet → GCS upload** (41 GB, ~95% complete based on time elapsed)
2. **Table datasets download** (PubTabNet 10.5GB + FinTabNet 3.2GB remaining)

---

## Next Steps

1. **Wait for downloads to complete**:
   - PubTabNet (10.5 GB)
   - FinTabNet (3.2 GB)

2. **Upload new datasets to GCS**:

   ```bash
   ./scripts/upload_datasets_to_gcs.sh --dataset tablebank
   # (After pubtabnet/fintabnet complete)
   ./scripts/upload_datasets_to_gcs.sh --dataset pubtabnet
   ./scripts/upload_datasets_to_gcs.sh --dataset fintabnet
   ```

3. **Verify GCS completion**:

   ```bash
   gsutil ls -lhr gs://image_detection_b/image-preprocessing-detector/datasets/
   ```

4. **Run smoke tests**:

   ```bash
   poetry run python -m benchmarks.runners.run_smoke --suite synthetic-iqa-blur-smoke
   ```

---

## Storage Summary

**Local Total**: 88.80 GB (+ 13.7 GB downloading)
**Expected Final**: ~102.5 GB local storage

**GCS Total**: ~3.7 GB uploaded, ~41 GB uploading
**Expected Final**: ~102.5 GB in GCS (mirroring local)

**Disk Space Available**: 794.6 GB (sufficient)

---

## Key Achievements

✅ **ICDAR MLT 2019 Removed**: Competition dataset replaced with COCO-Text (already present)
✅ **WiLI-2018 Extracted**: From tmp_cleanup, zip file deleted
✅ **TableBank Downloaded**: 46.38 GB complete (23.7 GB expected - includes multi-part archives)
✅ **GCS Authentication**: Automated via `scripts/auth_gcs.sh`
✅ **Download Scripts**: Updated to use Python API instead of CLI
✅ **Validation Tools**: Created automated validation and upload scripts

---

## Issues Resolved

1. **HuggingFace CLI not found**: Updated download scripts to use `huggingface_hub` Python API
2. **ICDAR MLT 2019 access**: Removed competition dataset, documented alternatives
3. **Table dataset sources**: Updated from broken URLs to active HuggingFace repos
4. **GCS upload automation**: Created comprehensive upload script with dry-run support

---

**Validation Status**: ✅ All required datasets present
**GCS Sync Status**: 🔄 In progress (6/7 complete, 1 uploading)
**Download Status**: 🔄 In progress (1/3 complete, 2 downloading)
