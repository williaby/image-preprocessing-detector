---
schema_type: common
title: "Testing Strategy - Dataset Storage and Test Fixtures"
tags:
  - datasets
  - testing
  - infrastructure
  - gcs
status: published
owner: docs-team
purpose: Documentation for testing strategy - dataset storage and test fixtures.
---

**Last Updated**: 2025-11-13
**Purpose**: Document dataset storage strategy and GitHub test fixtures for CI/CD

---

## Dataset Storage Strategy

### Local Development Storage

**Keep locally** (88+ GB):
- **Purpose**: Development, debugging, benchmarking, local model training
- **Location**: `data/benchmarks/`
- **Datasets**:
  - doclaynet (40.97 GB) - Phase 1 active use
  - tablebank (46.38 GB) - Phase 2
  - omnidocbench (1.16 GB) - Phase 3
  - wili_2018 (128 MB) - Phase 2
  - signatr6k (116 MB) - Optional
  - cocotext (52 MB) - Phase 2
  - synthetic_iqa (345 KB) - Phase 1 active use
  - pubtabnet (10.5 GB downloading) - Phase 2
  - fintabnet (3.2 GB downloading) - Phase 2

**Disk space management**:
- Current available: 794.6 GB (sufficient)
- If constrained: Delete Phase 2+ datasets, keep Phase 1 datasets locally
- Re-download from GCS when needed: `gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/tablebank data/benchmarks/`

### Google Cloud Storage (GCS)

**Purpose**: Backup, team collaboration, Google Colab training data source

**Location**: `gs://image_detection_b/image-preprocessing-detector/datasets/`

**Upload status** (as of 2025-11-13):
- ✅ synthetic_iqa (345 KB)
- ✅ cocotext (52 MB)
- ✅ wili_2018 (128 MB)
- ✅ signatr6k (116 MB)
- ✅ omnidocbench (1.16 GB)
- 🔄 doclaynet (40.97 GB uploading)
- ⏸️ tablebank (pending - download complete)
- ⏸️ pubtabnet (pending - downloading)
- ⏸️ fintabnet (pending - downloading)

**Access from Google Colab**:
```python
# Authenticate
from google.colab import auth
auth.authenticate_user()

# Download dataset
!gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/tablebank /content/data/
```

### GitHub Repository

**DO NOT upload large datasets to GitHub**:
- GitHub has 100 MB single file limit
- Repository size should stay under 1 GB recommended limit
- Large files cause slow clones and poor performance

**Use test fixtures instead** (see below).

---

## GitHub Test Fixtures

### Purpose

Small, representative dataset samples for CI/CD testing without requiring full dataset downloads.

### Structure

```
data/
├── test_fixtures/          # ✅ Committed to GitHub (< 50 MB total)
│   ├── doclaynet/          # 5-10 representative samples
│   ├── tablebank/          # 5-10 table images
│   ├── cocotext/           # 5-10 text detection samples
│   ├── wili_2018/          # 5-10 language samples
│   ├── omnidocbench/       # 5-10 multi-task samples
│   ├── synthetic_iqa/      # Auto-generated (not needed)
│   └── README.md           # Documentation of fixture sources
│
└── benchmarks/             # ❌ .gitignore (88+ GB, local only)
    ├── doclaynet/
    ├── tablebank/
    └── ...
```

### Selection Criteria

**Representative samples** (5-10 files per dataset):
1. **Coverage**: Different document types, layouts, quality levels
2. **Edge cases**: Skewed pages, low contrast, blurry text, complex tables
3. **File size**: Prefer smaller files to stay under 50 MB total
4. **License**: Ensure samples are permissively licensed for GitHub distribution

**Specific selections**:

- **doclaynet**: 5 PDFs with different layouts (tables, images, text-heavy, mixed)
- **tablebank**: 5 images (simple tables, complex tables, rotated, low quality)
- **cocotext**: 5 images (dense text, sparse text, different fonts)
- **wili_2018**: 10 text samples (different languages: EN, FR, DE, ES, ZH, AR, RU, JA, KO, HI)
- **omnidocbench**: 5 images (different document types from benchmark)

### CI/CD Integration

**GitHub Actions** ([.github/workflows/ci.yml](.github/workflows/ci.yml)):

```yaml
- name: Run unit tests with test fixtures
  run: |
    poetry run pytest tests/unit/ -v
  # Uses data/test_fixtures/ automatically

- name: Run integration tests (fixtures only)
  run: |
    poetry run pytest tests/integration/ -v -m "not requires_full_dataset"
```

**Test markers**:
```python
# tests/integration/test_pipeline.py

@pytest.mark.requires_full_dataset
def test_full_doclaynet_benchmark():
    """Requires full doclaynet dataset (88 GB) - skip in CI."""
    # Only runs locally with full datasets
    pass

def test_pipeline_with_fixtures():
    """Uses test_fixtures/ - runs in CI."""
    # Runs in CI with small fixtures
    pass
```

### Updating Test Fixtures

**When to update**:
- Adding new detection capabilities (need new edge cases)
- Discovering bugs in production (add failing samples)
- Phase transitions (add Phase 2/3 specific samples)

**How to update**:
```bash
# Extract new samples from full datasets
poetry run python scripts/extract_test_fixtures.py --dataset doclaynet --count 5

# Verify size constraint
du -sh data/test_fixtures/  # Should be < 50 MB

# Commit to GitHub
git add data/test_fixtures/
git commit -m "test: Update doclaynet fixtures with complex layout samples"
```

---

## Testing Workflow

### Local Development

**Use full datasets**:
```bash
# Run all tests including benchmarks (requires 88+ GB)
poetry run pytest -v

# Run specific benchmark
poetry run python -m benchmarks.runners.run_smoke --suite doclaynet-layout-smoke
```

### CI/CD (GitHub Actions)

**Use test fixtures only**:
```bash
# Automatically uses data/test_fixtures/
poetry run pytest -v -m "not requires_full_dataset"
```

### Google Colab Training

**Download from GCS**:
```python
# Download specific dataset for training
!gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/tablebank /content/data/

# Train model
!poetry run python src/train_iqa_model.py --dataset tablebank
```

---

## Disk Space Recovery

If local disk space becomes constrained:

```bash
# Check current usage
du -sh data/benchmarks/*

# Delete Phase 2+ datasets (can re-download from GCS)
rm -rf data/benchmarks/tablebank
rm -rf data/benchmarks/pubtabnet
rm -rf data/benchmarks/fintabnet

# Keep Phase 1 datasets (actively used)
# - doclaynet (40.97 GB)
# - synthetic_iqa (345 KB)

# Re-download when needed
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/tablebank data/benchmarks/
```

---

## Storage Summary

| Storage Type | Size | Purpose | Committed to Git |
|--------------|------|---------|------------------|
| Test fixtures | < 50 MB | CI/CD testing | ✅ Yes |
| Full datasets | 88+ GB | Local development | ❌ No (.gitignore) |
| GCS backup | 102+ GB | Backup, Colab training | N/A (cloud) |

**Best practice**:
- ✅ Keep full datasets local for development
- ✅ Upload all datasets to GCS for backup/Colab
- ✅ Use small test fixtures for CI/CD
- ❌ Never commit full datasets to GitHub

---

## Next Steps

1. **Create test fixtures extraction script**: `scripts/extract_test_fixtures.py`
2. **Extract representative samples** from each dataset (< 50 MB total)
3. **Update .gitignore**: Allow `data/test_fixtures/`, exclude `data/benchmarks/`
4. **Update CI configuration**: Use `-m "not requires_full_dataset"` marker
5. **Document fixture sources**: Create `data/test_fixtures/README.md`

---

**References**:

- [DATASET_INSTALLATION.md](guides/dataset-installation.md) - Full dataset download instructions
- [PROJECT_PLAN.md](planning/PROJECT_PLAN.md) - Phase-specific dataset requirements
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) - CI/CD configuration
