---
title: Google Colab Storage Setup Guide
description: Configure Google Drive and Google Cloud Storage for Phase 2 training
tags: [setup, google-colab, storage, phase-2]
---

# Google Colab Storage Setup Guide

**Project**: image-detection
**GCP Project ID**: image-detection-478105
**GCS Bucket**: image_detection_b
**Last Updated**: 2025-01-15

---

## Overview

This project supports **two storage options** for Colab training:

1. **Google Cloud Storage (GCS)**: **RECOMMENDED** - Secure, isolated, project-specific storage
2. **Google Drive**: Alternative option (requires full Drive access - see security warning below)

### ⚠️ Security Warning: Google Drive Access

When you mount Google Drive in Colab, it requests **full access to your entire personal Google Drive**. This means:

- Colab can read/write **all your personal files**
- No way to limit access to a specific folder
- Shares access with all notebooks in the same session

**Recommendation**: Use **Google Cloud Storage (GCS)** instead for better security isolation. You already have a GCS bucket set up (`gs://image_detection_b`), so this is the recommended approach.

---

## Option 1: Google Cloud Storage Setup (RECOMMENDED - Secure & Isolated)

### Your GCS Configuration

- **Project**: image-detection
- **Project ID**: image-detection-478105
- **Bucket**: `gs://image_detection_b`
- **Security**: Bucket-level IAM control, no access to personal files

### Why GCS is Better for This Use Case

✅ **Security**: Only accesses your specific project bucket
✅ **Isolation**: Completely separate from personal files
✅ **Cost-Effective**: ~$0.50/month for 25GB (vs $2/month for Drive 100GB)
✅ **Production-Ready**: Same storage used for deployment
✅ **Audit Trail**: Full GCS access logging

### GCS-Only Quick Start (5 Steps)

**Step 1: Authenticate in Colab**

```python
# Run this at the start of your training notebook
from google.colab import auth
auth.authenticate_user()

# Configure your project
!gcloud config set project image-detection-478105

# Verify bucket access
!gsutil ls gs://image_detection_b
```

**Step 2: Understand Expected File Structure**

GCS doesn't support empty directories - "folders" are created implicitly when you upload files with path prefixes. Here's the expected structure for each phase:

**Phase 2: IQA Training**
```
gs://image_detection_b/
├── configs/
│   └── colab_phase2_iqa_gcs.yaml
├── datasets/
│   └── iqa_phase2/
│       ├── train/
│       │   ├── images/
│       │   │   ├── img_000001.png
│       │   │   ├── img_000002.png
│       │   │   └── ... (35,000 images)
│       │   └── labels.json
│       ├── val/
│       │   ├── images/
│       │   │   └── ... (7,500 images)
│       │   └── labels.json
│       └── test/
│           ├── images/
│           │   └── ... (7,500 images)
│           └── labels.json
├── checkpoints/
│   └── phase2_iqa/
│       └── (created during training)
├── logs/
│   └── phase2_iqa/
│       └── (created during training)
└── models/
    └── phase2_iqa/
        └── (final models uploaded after training)
```

**Phase 3: Layout Detection**
```
gs://image_detection_b/
├── configs/
│   └── colab_phase3_yolov8_gcs.yaml
├── datasets/
│   └── layout_phase3/
│       ├── train/
│       │   ├── images/
│       │   │   └── ... (200,000+ images)
│       │   └── labels/  # YOLO format
│       │       └── ... (.txt annotation files)
│       ├── val/
│       │   ├── images/
│       │   └── labels/
│       └── test/
│           ├── images/
│           └── labels/
├── checkpoints/
│   └── phase3_yolov8/
└── models/
    └── phase3_yolov8/
```

**Step 3: Upload Configuration**

```bash
# Upload training config from your local machine
gsutil cp configs/colab_phase2_iqa_gcs.yaml gs://image_detection_b/configs/

# For Phase 3 (later)
gsutil cp configs/colab_phase3_yolov8_gcs.yaml gs://image_detection_b/configs/
```

**Step 4: Prepare and Upload Dataset**

**Phase 2 Dataset Generation:**

For complete dataset preparation instructions, see **[DATASET_PREPARATION.md](../DATASET_PREPARATION.md)**.

**Quick summary:**

```bash
# 1. Generate synthetic augmented dataset with weak supervision labels
poetry run python scripts/prepare_phase2_data.py \
    --source-dirs data/raw/tobacco800 \
    --output-dir datasets/iqa_phase2 \
    --num-samples 50000 \
    --preset medium

# 2. Upload dataset to GCS using helper script
./scripts/gcs_helpers.sh upload-phase2

# 3. Verify upload (should show ~10GB)
gsutil du -sh gs://image_detection_b/datasets/iqa_phase2/
```

**Base Datasets** (download before generation):
- **Tobacco800**: 1,290 scanned documents (~1GB, fastest)
- **DocBank**: 500k document pages (~40GB)
- **RVL-CDIP**: 400k document images (~50GB)

See [DATASET_INSTALLATION.md](../DATASET_INSTALLATION.md) for download instructions.

**Phase 3 Dataset Sources (Phase 3 Week 1):**

```bash
# 1. Download annotated datasets:
#    - PubLayNet: 360k annotated document pages
#    - DocLayNet: 80k annotated documents
#    - TableBank: 417k table images
#    (See docs/DATASET_INSTALLATION.md for download instructions)

# 2. Convert annotations to YOLO format
#    (Use scripts from Phase 3)

# 3. Upload to GCS
gsutil -m cp -r datasets/layout_phase3/train gs://image_detection_b/datasets/layout_phase3/
gsutil -m cp -r datasets/layout_phase3/val gs://image_detection_b/datasets/layout_phase3/
gsutil -m cp -r datasets/layout_phase3/test gs://image_detection_b/datasets/layout_phase3/

# Verify upload (should show ~40-50GB)
gsutil du -sh gs://image_detection_b/datasets/layout_phase3/
```

**Step 5: In Your Training Notebook**

```python
# Download config
!gsutil cp gs://image_detection_b/configs/colab_phase2_iqa_gcs.yaml /content/config.yaml

# Download dataset to local SSD (faster training)
!gsutil -m cp -r gs://image_detection_b/datasets/iqa_phase2 /content/data_cache/

# Train (checkpoints saved locally)
# ... your training code ...

# Upload checkpoints to GCS (run periodically or at end)
!gsutil -m cp -r /content/checkpoints/* gs://image_detection_b/checkpoints/phase2_iqa/

# Upload final model
!gsutil cp /content/models/best_model.onnx gs://image_detection_b/models/phase2_iqa/
```

**That's it!** No Google Drive access needed. ✅

---

## Option 2: Google Drive Setup (Alternative - Requires Full Drive Access)

### 1. Subscribe to Google Drive Storage

**Required**: 100GB plan ($1.99/month)

- Go to [Google One](https://one.google.com/)
- Upgrade to 100GB plan
- Total storage needed:
  - Phase 2: ~25GB (dataset + checkpoints + logs)
  - Phase 3: ~50GB (larger dataset)
  - Buffer: ~25GB

### 2. Create Directory Structure

Create this structure in your Google Drive:

```
MyDrive/
└── image-preprocessing-detector/
    ├── datasets/
    │   └── iqa_phase2/
    │       ├── train/
    │       │   ├── images/
    │       │   └── labels.json
    │       ├── val/
    │       │   ├── images/
    │       │   └── labels.json
    │       └── test/
    │           ├── images/
    │           └── labels.json
    ├── checkpoints/
    │   └── phase2_iqa/
    ├── logs/
    │   └── phase2_iqa/
    ├── models/
    │   └── phase2_iqa/
    └── configs/
        └── colab_phase2_iqa.yaml
```

### 3. Mount in Colab Notebook

The training notebook will automatically mount your Drive:

```python
from google.colab import drive
drive.mount('/content/drive')

# Verify structure
!ls "/content/drive/MyDrive/image-preprocessing-detector"
```

### 4. Upload Configuration

Upload the training configuration to your Drive:

```bash
# On your local machine
cp configs/colab_phase2_iqa.yaml ~/Google\ Drive/image-preprocessing-detector/configs/
```

---

## Option 2: Google Cloud Storage Setup (Backup & Production)

### Your GCS Configuration

- **Project**: image-detection
- **Project ID**: image-detection-478105
- **Bucket**: `gs://image_detection_b`
- **Region**: (check in GCP Console)

### 1. Install gsutil in Colab

```python
# Already installed in Colab, just authenticate
from google.colab import auth
auth.authenticate_user()

# Configure project
!gcloud config set project image-detection-478105
```

### 2. Create Directory Structure in GCS

```bash
# Create directories
gsutil mkdir gs://image_detection_b/datasets/
gsutil mkdir gs://image_detection_b/checkpoints/
gsutil mkdir gs://image_detection_b/models/
gsutil mkdir gs://image_detection_b/logs/

# Set lifecycle rules (optional - auto-delete old checkpoints)
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["checkpoints/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://image_detection_b
```

### 3. Upload Dataset to GCS

```bash
# Upload Phase 2 dataset
gsutil -m cp -r datasets/iqa_phase2 gs://image_detection_b/datasets/

# Verify upload
gsutil du -sh gs://image_detection_b/datasets/iqa_phase2
```

### 4. Use GCS in Training (Optional)

To use GCS instead of Google Drive, modify your Colab notebook:

```python
# Download dataset from GCS to local SSD (faster training)
!gsutil -m cp -r gs://image_detection_b/datasets/iqa_phase2 /content/data_cache/

# Train using local cache
dataset_root = "/content/data_cache/iqa_phase2"

# Upload checkpoints to GCS after each save
!gsutil -m cp -r /content/checkpoints/* gs://image_detection_b/checkpoints/phase2_iqa/
```

---

## Recommended Workflow: Hybrid Approach

Use both storage systems for optimal results:

### During Training (Google Drive)

1. **Mount Google Drive** in Colab notebook
2. **Load dataset** from Drive to local cache (`/content/data_cache`)
3. **Save checkpoints** to Drive (`/content/drive/MyDrive/checkpoints/`)
4. **Save logs** to Drive for TensorBoard

**Advantages**:
- Native Colab integration
- Automatic syncing
- Easy access from multiple Colab sessions

### After Training (GCS Backup)

1. **Backup final model** to GCS bucket
2. **Archive checkpoints** to GCS
3. **Store production models** in GCS

**Advantages**:
- Versioning and lifecycle management
- Production deployment integration
- CI/CD pipeline compatibility
- Lower cost for archival storage

### Example: Sync Drive → GCS

```python
# In Colab notebook, after training completes
from google.colab import auth
auth.authenticate_user()

# Configure GCS project
!gcloud config set project image-detection-478105

# Sync trained model to GCS
!gsutil -m cp -r /content/drive/MyDrive/models/phase2_iqa \
    gs://image_detection_b/models/phase2_$(date +%Y%m%d)/

# Backup best checkpoint
!gsutil cp /content/drive/MyDrive/checkpoints/phase2_iqa/best_model.pth \
    gs://image_detection_b/models/phase2_iqa_best_$(date +%Y%m%d).pth
```

---

## Storage Cost Comparison

### Google Drive
- **100GB Plan**: $1.99/month (flat rate)
- **Phase 2 Usage**: ~25GB
- **Best for**: Active training, frequent access

### Google Cloud Storage
- **Standard Storage**: $0.020/GB/month
- **Phase 2 Usage**: ~25GB = $0.50/month
- **Nearline (archive)**: $0.010/GB/month = $0.25/month
- **Best for**: Backup, archival, production deployment

**Recommendation**: Use Google Drive for training ($2/month), GCS for archival (<$1/month)

---

## Quick Start Checklist

### Before Training

- [ ] Google Colab Pro subscription active ($10/month)
- [ ] Google Drive 100GB plan active ($2/month)
- [ ] Directory structure created in Google Drive
- [ ] Dataset uploaded to Google Drive (`~/MyDrive/image-preprocessing-detector/datasets/iqa_phase2/`)
- [ ] Configuration file uploaded (`~/MyDrive/image-preprocessing-detector/configs/colab_phase2_iqa.yaml`)

### Optional: GCS Setup

- [ ] GCP project created (image-detection-478105)
- [ ] GCS bucket created (image_detection_b)
- [ ] Directory structure created in GCS
- [ ] Lifecycle rules configured (optional)

### Verify Setup

```python
# In Colab notebook
from google.colab import drive
drive.mount('/content/drive')

# Check Google Drive structure
!ls -lh "/content/drive/MyDrive/image-preprocessing-detector"
!ls -lh "/content/drive/MyDrive/image-preprocessing-detector/datasets/iqa_phase2"

# Optional: Check GCS
from google.colab import auth
auth.authenticate_user()
!gcloud config set project image-detection-478105
!gsutil ls gs://image_detection_b
```

---

## Troubleshooting

### Google Drive Mount Issues

```python
# Force remount
from google.colab import drive
drive.flush_and_unmount()
drive.mount('/content/drive', force_remount=True)
```

### GCS Authentication Issues

```python
# Re-authenticate
from google.colab import auth
auth.authenticate_user()

# Verify project
!gcloud config get-value project

# Test bucket access
!gsutil ls gs://image_detection_b
```

### Slow Transfer Speeds

```python
# Use parallel transfer for large files
!gsutil -m cp -r source destination

# Monitor transfer progress
!gsutil -m -o "GSUtil:parallel_process_count=4" cp -r source destination
```

---

## Next Steps

1. **Setup Google Drive** following Option 1 above
2. **Upload dataset** to Drive (see [DATASET_INSTALLATION.md](../DATASET_INSTALLATION.md))
3. **Open training notebook**: [notebooks/colab/phase2_iqa_training.ipynb](../../notebooks/colab/phase2_iqa_training.ipynb)
4. **Start training** following [COLAB_TRAINING_GUIDE.md](../COLAB_TRAINING_GUIDE.md)

**Optional**: Setup GCS backup following Option 2 for production deployment.

---

*For complete training instructions, see [COLAB_TRAINING_GUIDE.md](../COLAB_TRAINING_GUIDE.md)*
