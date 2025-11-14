---
title: Phase 2 Quick Start Guide
description: Fast-track setup for Phase 2 IQA training on Modal
tags: [phase-2, quickstart, modal]
---

# Phase 2 Quick Start Guide

**Get from zero to training in 30 minutes** (plus dataset download/upload time)

---

## Prerequisites Checklist

- [ ] Modal account (free tier: $30/month credits)
- [ ] GCP Project: `image-detection-478105`
- [ ] GCS Bucket: `image_detection_b`
- [ ] GCS service account key (for Modal secret)
- [ ] Python 3.11+ installed locally
- [ ] Poetry installed locally
- [ ] gcloud CLI installed and authenticated

---

## Step 1: Download Base Dataset (5-10 minutes)

**Quick option**: Tobacco800 (~1GB, 1,290 images)

```bash
# Create directory
mkdir -p data/raw/tobacco800

# Download Tobacco800 (see guides/dataset-installation.md for actual URL)
cd data/raw/tobacco800
# ... download and extract instructions ...
cd ../../..

# Verify
ls -lh data/raw/tobacco800/
```

**Production option**: DocBank or RVL-CDIP (see [DATASET_INSTALLATION.md](guides/dataset-installation.md))

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

## Step 5: Setup Modal and Start Training (5 minutes setup)

1. **Install Modal CLI**:
   ```bash
   poetry add modal
   poetry install
   ```

2. **Authenticate with Modal**:
   ```bash
   poetry run modal token new
   # Opens browser for authentication
   ```

3. **Setup GCS credentials**:
   ```bash
   # Use helper script (auto-encodes to base64)
   ./scripts/modal_helpers.sh setup-gcs-secret /path/to/gcp-service-account-key.json

   # Or manually:
   GCP_SA_KEY_B64=$(base64 -w 0 /path/to/key.json)
   poetry run modal secret create gcs-credentials GCP_SA_KEY="$GCP_SA_KEY_B64"
   ```

4. **Test GPU access**:
   ```bash
   ./scripts/modal_helpers.sh test-gpu
   # Should show: "✅ Hello from Modal GPU: Tesla T4"
   ```

5. **Start training**:
   ```bash
   ./scripts/modal_helpers.sh train-phase2
   # Or manually:
   poetry run modal run modal/train_phase2_iqa.py
   ```

6. **Monitor training**:
   - Open Modal dashboard: https://modal.com/apps
   - View logs, GPU utilization, costs in real-time

---

## Helper Commands

### Modal Commands

```bash
# Setup GCS credentials in Modal
./scripts/modal_helpers.sh setup-gcs-secret /path/to/key.json

# Test GPU access
./scripts/modal_helpers.sh test-gpu

# Start Phase 2 training
./scripts/modal_helpers.sh train-phase2

# Start Phase 3 training (later)
./scripts/modal_helpers.sh train-phase3

# Monitor training
./scripts/modal_helpers.sh monitor

# Check Modal usage and costs
./scripts/modal_helpers.sh costs

# List Modal secrets
./scripts/modal_helpers.sh secrets
```

### GCS Commands

```bash
# Upload configs
./scripts/gcs_helpers.sh upload-configs

# Upload Phase 2 dataset
./scripts/gcs_helpers.sh upload-phase2

# Download Phase 2 dataset (if needed locally)
./scripts/gcs_helpers.sh download-phase2

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

### Modal Training Issues

```bash
# Authentication failed
poetry run modal token new

# GCS access failed - check secret
poetry run modal secret list  # Should show: gcs-credentials
poetry run modal run modal/test_gcs.py  # Test GCS access

# Training failed - check logs
poetry run modal logs --tail 100  # View recent logs

# GPU allocation failed - check Modal dashboard
# Visit: https://modal.com/apps
```

---

## Expected Timeline

| Task | Time | Notes |
|------|------|-------|
| Download Tobacco800 | 5-10 min | Depends on internet speed |
| Generate dataset (50k) | 20-30 min | CPU-intensive |
| Upload to GCS | 10-30 min | Depends on upload speed (100 Mbps ~15 min) |
| Modal setup | 5 min | One-time authentication + secret setup |
| **Total setup time** | **40-75 min** | Plus training time |
| Training (50 epochs) | 3-6 hours | With T4 GPU, no session timeouts |

---

## Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Modal (T4 GPU) | $0-3 | Free tier: $30/month credits, T4 @ $0.59/hr (~5-6 hours) |
| GCS Storage (10GB) | $0.20/month | Standard storage |
| **Total** | **~$0.20-3** | During active training |

**Phase 2 Training Cost**: ~$3 (5 hours @ $0.59/hr) - covered by free tier!

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

- **Dataset Preparation**: [dataset-preparation.md](guides/dataset-preparation.md)
- **Modal Training Guide**: [modal-training.md](guides/modal-training.md)
- **Modal Storage Setup**: [modal-storage.md](guides/modal-storage.md)
- **Phase 2 Plan**: [phase-2-plan.md](project/phases/phase-2-plan.md)
- **Architecture Decision**: [ADR-030 GCS + Modal Workflow](ADRs/0030-gcs-modal-training-workflow.md)

---

*Last Updated: 2025-11-14*
