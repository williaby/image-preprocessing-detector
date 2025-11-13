---
title: Phase 2 Quick Start Guide
description: Fast-track setup for Phase 2 IQA training on Google Colab
tags: [phase-2, quickstart, google-colab]
---

# Phase 2 Quick Start Guide

**Get from zero to training in 60 minutes** (plus dataset download/upload time)

---

## Prerequisites Checklist

- [ ] Google Colab Pro subscription ($10/month)
- [ ] GCP Project: `image-detection-478105`
- [ ] GCS Bucket: `image_detection_b`
- [ ] Python 3.11+ installed locally
- [ ] Poetry installed locally
- [ ] gcloud CLI installed and authenticated

---

## Step 1: Download Base Dataset (5-10 minutes)

**Quick option**: Tobacco800 (~1GB, 1,290 images)

```bash
# Create directory
mkdir -p data/raw/tobacco800

# Download Tobacco800 (see DATASET_INSTALLATION.md for actual URL)
cd data/raw/tobacco800
# ... download and extract instructions ...
cd ../../..

# Verify
ls -lh data/raw/tobacco800/
```

**Production option**: DocBank or RVL-CDIP (see [DATASET_INSTALLATION.md](DATASET_INSTALLATION.md))

---

## Step 2: Generate Synthetic Dataset (20-30 minutes)

```bash
# Install dependencies
poetry install --with dev

# Generate 50k augmented samples
poetry run python scripts/prepare_phase2_data.py \
    --source-dirs data/raw/tobacco800 \
    --output-dir datasets/iqa_phase2 \
    --num-samples 50000 \
    --preset medium

# Verify output
du -sh datasets/iqa_phase2/  # Should show ~10GB
find datasets/iqa_phase2/train/images -name "*.png" | wc -l  # Should show 35000
```

**Output structure:**
```
datasets/iqa_phase2/
├── train/ (35,000 images + labels.json)
├── val/   (7,500 images + labels.json)
└── test/  (7,500 images + labels.json)
```

---

## Step 3: Authenticate with GCP (2 minutes)

```bash
# Login to gcloud
gcloud auth login

# Set project
gcloud config set project image-detection-478105

# Verify bucket access
gsutil ls gs://image_detection_b
```

---

## Step 4: Upload to GCS (10-30 minutes)

```bash
# Upload training config
./scripts/gcs_helpers.sh upload-configs

# Upload dataset (parallel transfer, ~10-30 min for 10GB)
./scripts/gcs_helpers.sh upload-phase2

# Verify upload
./scripts/gcs_helpers.sh info
```

Expected output:
```
[INFO] Storage usage by directory:
10.2 GiB    gs://image_detection_b/datasets/iqa_phase2
100 KiB     gs://image_detection_b/configs

[INFO] Total bucket size:
10.2 GiB    gs://image_detection_b

[INFO] Estimated monthly cost (Standard storage @ $0.020/GB):
10.20 GB × $0.020 = $0.20/month
```

---

## Step 5: Start Training in Colab (5 minutes setup)

1. **Open training notebook**:
   - [notebooks/colab/phase2_iqa_training.ipynb](../notebooks/colab/phase2_iqa_training.ipynb)

2. **Upload to Google Colab**:
   - Go to [colab.research.google.com](https://colab.research.google.com)
   - Upload notebook or connect to GitHub

3. **Run initial cells**:
   ```python
   # Cell 1: Authenticate
   from google.colab import auth
   auth.authenticate_user()
   !gcloud config set project image-detection-478105

   # Cell 2: Download dataset to Colab local SSD
   !gsutil -m cp -r gs://image_detection_b/datasets/iqa_phase2 /content/data_cache/

   # Cell 3: Download config
   !gsutil cp gs://image_detection_b/configs/colab_phase2_iqa_gcs.yaml /content/config.yaml
   ```

4. **Start training** (follow notebook)

---

## GCS Helper Commands

```bash
# Upload configs
./scripts/gcs_helpers.sh upload-configs

# Upload Phase 2 dataset
./scripts/gcs_helpers.sh upload-phase2

# Download Phase 2 dataset (if needed locally)
./scripts/gcs_helpers.sh download-phase2

# Sync checkpoints from Colab to GCS
./scripts/gcs_helpers.sh sync-checkpoints phase2

# Download checkpoints from GCS
./scripts/gcs_helpers.sh download-checkpoints phase2

# Upload final models
./scripts/gcs_helpers.sh upload-models phase2

# List bucket contents
./scripts/gcs_helpers.sh list

# Show storage info and costs
./scripts/gcs_helpers.sh info
```

---

## Troubleshooting

### Dataset Generation Issues

```bash
# No source images found
ls -lh data/raw/tobacco800/
find data/raw/tobacco800/ -name "*.png" | head -10

# Dependencies missing
poetry install --with dev
poetry run python -c "import albumentations, cv2, numpy; print('✓ OK')"
```

### GCS Upload Issues

```bash
# Re-authenticate
gcloud auth login
gcloud config set project image-detection-478105

# Test bucket access
gsutil ls gs://image_detection_b

# Check internet speed (10 Mbps = 30-40 min, 100 Mbps = 15-20 min for 10GB)
```

### Colab Training Issues

```bash
# Download dataset failed - check authentication
from google.colab import auth
auth.authenticate_user()
!gcloud config get-value project  # Should show: image-detection-478105

# GPU not available - upgrade to Colab Pro
!nvidia-smi  # Should show GPU info
```

---

## Expected Timeline

| Task | Time | Notes |
|------|------|-------|
| Download Tobacco800 | 5-10 min | Depends on internet speed |
| Generate dataset (50k) | 20-30 min | CPU-intensive |
| Upload to GCS | 10-30 min | Depends on upload speed (100 Mbps ~15 min) |
| Colab setup | 5 min | One-time authentication |
| **Total setup time** | **40-75 min** | Plus training time |
| Training (50 epochs) | 3-6 hours | With V100/T4 GPU |

---

## Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Google Colab Pro | $10/month | 12-hour sessions, V100/T4 GPUs |
| GCS Storage (10GB) | $0.20/month | Standard storage |
| **Total** | **~$10.20/month** | During active training |

After training completes, you can delete the GCS dataset to save costs (~$0.20/month).

---

## Next Steps

After training completes:

1. **Download trained model**:
   ```bash
   ./scripts/gcs_helpers.sh download-models phase2
   ```

2. **Validate model** (Phase 2 Week 2):
   - Run validation on test set
   - Compute metrics (mAP, per-class precision/recall)
   - Calibrate confidence thresholds

3. **Export to ONNX** (automatic in training notebook):
   - INT8 quantization for CPU deployment
   - Production-ready model

4. **Proceed to Phase 3**: YOLOv8 layout detection

---

## Complete Documentation

- **Dataset Preparation**: [DATASET_PREPARATION.md](DATASET_PREPARATION.md)
- **GCS Storage Setup**: [setup/colab-storage-setup.md](setup/colab-storage-setup.md)
- **Colab Training Guide**: [COLAB_TRAINING_GUIDE.md](COLAB_TRAINING_GUIDE.md)
- **Phase 2 Plan**: [project/phases/phase-2-plan.md](project/phases/phase-2-plan.md)

---

*Last Updated: 2025-01-15*
