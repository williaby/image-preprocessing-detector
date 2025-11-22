---
schema_type: common
title: "100K IQA Dataset Generation Guide"
tags:
  - datasets
  - training
  - infrastructure
  - gcs
status: published
owner: docs-team
purpose: Complete workflow for generating, tracking, and training with 100K IQA dataset.
---

## Complete Workflow: Generation → DVC → GCS → Training

This guide walks through the complete process of generating the 100K IQA training dataset, tracking it with DVC, uploading to GCS, and using it for training.

---

## Prerequisites

### 1. Verify Source Datasets

```bash
# Check available datasets
ls -lh data/benchmarks/

# Required datasets:
# - diqa-5000/          ✅ (350 originals × 10 distortions)
# - tablebank/          ✅ (278K images)
# - pubtabnet/          ✅ (PNG files)
# - doclaynet/          ⚠️  (if available)
# - iam/                ⚠️  (if available)
# - funsd/              ⚠️  (if available)
```

### 2. Install Dependencies

```bash
# Install ML dependencies
uv sync --extra ml

# Verify albumentations installed
uv run python -c "import albumentations; print(albumentations.__version__)"
```

### 3. Configure GCS Credentials

```bash
# Verify GCS credentials exist
ls -lh .gcp/service-account.json

# Test GCS access
gsutil ls gs://image_detection_b/
```

---

## Step 1: Generate 100K Dataset

### Option A: Full Generation (8-12 hours)

```bash
# Generate complete 100K dataset
uv run python scripts/generate_100k_iqa_dataset.py

# Monitor progress (separate terminal)
watch -n 5 'du -sh data/training/iqa_phase2_100k && \
  find data/training/iqa_phase2_100k/images -name "*.jpg" | wc -l'
```

**Expected Output**:
- **Duration**: 8-12 hours (local CPU)
- **Size**: ~40-50 GB
- **Files**: 100,000 JPEG images + metadata.json
- **Location**: `data/training/iqa_phase2_100k/`

### Option B: Test Run (10-15 minutes)

First validate the pipeline with 1000 samples:

```bash
# TODO: Add --test-mode flag to generation script
uv run python scripts/generate_100k_iqa_dataset.py \
  --output-dir data/training/iqa_phase2_test \
  --max-samples 1000
```

---

## Step 2: Validate Distribution

After generation, verify the 13-dimensional distribution matches targets:

```bash
# Validate dataset
uv run python scripts/validate_dataset_distributions.py \
  --dataset data/training/iqa_phase2_100k

# Check metadata
cat data/training/iqa_phase2_100k/metadata.json | jq '.actual_distributions'
```

**Expected Validation**:
- ✅ Defect type distribution within ±2% of target
- ✅ Color mode: ~60% RGB, ~35% grayscale, ~5% B&W
- ✅ Orientation: ~75% portrait, ~20% landscape
- ✅ Combined defects: ~20% none, ~40% single, ~25% two, ~15% three+
- ✅ DPI distribution balanced across 70-300+ DPI

---

## Step 3: Initialize DVC (First Time Only)

```bash
# Initialize DVC in project
dvc init

# Configure GCS as remote storage
dvc remote add -d gcs gs://image_detection_b/image-preprocessing-detector/datasets

# Set GCS credentials
dvc remote modify gcs credentialpath .gcp/service-account.json

# Commit DVC configuration
git add .dvc/config .dvc/.gitignore
git commit -m "chore: initialize DVC with GCS remote"
```

---

## Step 4: Track Dataset with DVC

```bash
# Add dataset to DVC tracking
dvc add data/training/iqa_phase2_100k

# This creates:
# - data/training/iqa_phase2_100k.dvc (metadata file, ~1KB)
# - Updates .gitignore to exclude actual dataset
```

**What happens**:
- DVC calculates MD5 checksum of entire dataset
- Creates `.dvc` file with metadata (file hashes, structure)
- Adds dataset to `.gitignore` (actual files not committed to Git)
- Dataset files stay local until `dvc push`

---

## Step 5: Upload to GCS

```bash
# Push dataset to GCS
dvc push data/training/iqa_phase2_100k

# This uploads to:
# gs://image_detection_b/image-preprocessing-detector/datasets/iqa_phase2_100k/
```

**Upload Details**:
- **Size**: ~40-50 GB
- **Duration**: 30-90 minutes (depends on internet speed)
- **Cost**: $1.04/month GCS storage
- **Parallel upload**: DVC uses multiple threads automatically

**Monitor Progress**:
```bash
# Check GCS bucket size
gsutil du -sh gs://image_detection_b/image-preprocessing-detector/datasets/
```

---

## Step 6: Commit DVC Metadata to Git

```bash
# Commit DVC file (NOT the actual dataset)
git add data/training/iqa_phase2_100k.dvc
git add data/training/.gitignore
git commit -m "feat(dataset): add 100K IQA training dataset with 13-dimensional distribution

- 100,000 samples with balanced defect types and severity
- Multi-dimensional distribution: color mode, orientation, DPI, JPEG quality
- Source: DIQA-5000, TableBank, PubTabNet, DocLayNet, IAM, FUNSD
- Tracked with DVC, uploaded to GCS
- Size: ~45 GB
"

# Push to GitHub
git push origin feature/phase-3
```

---

## Step 7: Download Dataset for Training (Modal/Colab)

### In Modal Training Script

```python
# modal/train_phase2_iqa.py

@app.function(
    image=image,
    gpu="T4",
    secrets=[modal.Secret.from_name("gcs-credentials")],
)
def train_teacher_model():
    import subprocess

    # Pull dataset from GCS via DVC
    print("Downloading 100K dataset from GCS...")
    subprocess.run([
        "dvc", "pull",
        "data/training/iqa_phase2_100k"
    ], check=True)

    # Dataset now available at data/training/iqa_phase2_100k/
    dataset_dir = Path("data/training/iqa_phase2_100k")

    # Load dataset
    train_loader = create_dataloader(dataset_dir)

    # Train model
    model = train_resnet50_teacher(train_loader)
```

### Manual Download (Local Training)

```bash
# Pull dataset from GCS
dvc pull data/training/iqa_phase2_100k

# Dataset downloaded to: data/training/iqa_phase2_100k/
```

---

## Step 8: Update Training Configuration

Update Modal training config to use new dataset:

```yaml
# configs/modal_phase2_iqa.yaml

data:
  dataset_path: data/training/iqa_phase2_100k  # Updated from iqa_phase2
  train_split: 0.70  # 70K samples
  val_split: 0.15    # 15K samples
  test_split: 0.15   # 15K samples

  # Multi-dimensional metadata tracking
  use_metadata: true
  metadata_file: data/training/iqa_phase2_100k/metadata.json

  # Data loader settings
  batch_size: 128
  num_workers: 4
  pin_memory: true
```

---

## Step 9: Run Training

```bash
# Start Modal training with new dataset
uv run modal run modal/train_phase2_iqa.py

# Expected duration: 12-14 hours (with T4 GPU)
# Expected cost: $7-14 (or free with $30/month tier)
```

---

## Troubleshooting

### Generation Issues

**Error: "albumentations not found"**
```bash
uv sync --extra ml
```

**Error: "Source dataset not found"**
```bash
# Check which datasets are available
ls -lh data/benchmarks/
# Update COMPOSITION in generate_100k_iqa_dataset.py
```

**Slow generation (>15 hours)**
```bash
# Check CPU usage
htop
# Consider running overnight or on more powerful machine
```

### DVC Issues

**Error: "GCS credentials not found"**
```bash
# Verify credentials file exists
ls .gcp/service-account.json

# Re-configure DVC remote
dvc remote modify gcs credentialpath .gcp/service-account.json
```

**Error: "dvc push failed"**
```bash
# Check GCS permissions
gsutil ls gs://image_detection_b/

# Verify service account has write permissions
```

### Upload Issues

**Slow upload (>2 hours)**
```bash
# Check internet speed
speedtest-cli

# Upload during off-peak hours
# Consider uploading from cloud VM with better bandwidth
```

---

## Dataset Versioning

### Creating Dataset Versions

When updating the dataset:

```bash
# Update generation script
# Regenerate dataset
uv run python scripts/generate_100k_iqa_dataset.py \
  --output-dir data/training/iqa_phase2_100k_v2

# Add to DVC
dvc add data/training/iqa_phase2_100k_v2

# Commit
git add data/training/iqa_phase2_100k_v2.dvc
git commit -m "feat(dataset): v2 with improved augmentation"

# Push to GCS
dvc push data/training/iqa_phase2_100k_v2
```

### Switching Dataset Versions

```bash
# Checkout old version
git checkout v1.0.0

# Pull old dataset
dvc pull data/training/iqa_phase2_100k

# Or pull specific version
dvc pull data/training/iqa_phase2_100k_v1
```

---

## Cost Summary

| Item | Cost | Frequency |
|------|------|-----------|
| **Generation** | $0 (local CPU) | One-time |
| **GCS Storage** | $1.04/month (40GB) | Monthly |
| **GCS Upload** | $0 (egress free within GCS) | One-time |
| **GCS Download (Modal)** | $0 (ingress free) | Per training run |
| **Modal Training** | $7-14 (T4 GPU, 12-14 hours) | Per training run |
| **TOTAL (first month)** | ~$8-15 | - |
| **TOTAL (subsequent months)** | $1.04/month (storage only) | - |

---

## Next Steps

After dataset is generated and uploaded:

1. ✅ **Update training scripts** → Use new dataset path
2. ✅ **Run teacher model training** → Modal training (12-14 hours)
3. ✅ **Validate teacher performance** → mAP > 0.88 target
4. ✅ **Train student model** → Knowledge distillation from teacher
5. ✅ **Export models** → ONNX + TorchScript for production

---

**Created**: 2025-11-18
**Version**: 1.0.0
**Status**: Ready for execution
