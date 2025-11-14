---
title: Phase 2 Dataset Preparation Guide
description: Generate synthetic augmented dataset with weak supervision labels for IQA training
tags: [phase-2, dataset, augmentation, weak-supervision]
---

# Phase 2 Dataset Preparation Guide

**Last Updated**: 2025-01-15

This guide explains how to prepare the Phase 2 IQA training dataset using synthetic augmentation and weak supervision labeling.

---

## Overview

The Phase 2 dataset consists of 50,000 document images with quality issue labels:

- **50,000 total samples** (35k train / 7.5k val / 7.5k test)
- **6 quality issue classes**: noise, blur, skew, perspective, low_contrast, orientation
- **Synthetic augmentation**: Generated from clean document images
- **Weak supervision labels**: Automated labeling using image quality metrics
- **~10GB total size** (compressed)

---

## Prerequisites

### 1. Base Datasets

Download one or more base document datasets to use as source material:

**Recommended Options:**

| Dataset | Size | Images | Download Time | Use Case |
|---------|------|--------|---------------|----------|
| **Tobacco800** | ~1GB | 1,290 | 5-10 min | Quick testing, scanned documents |
| **DocBank** | ~40GB | 500k | 2-4 hours | Production training, diverse layouts |
| **RVL-CDIP** | ~50GB | 400k | 3-5 hours | Production training, document classification |

**Quick Start (Tobacco800):**

```bash
# Create base dataset directory
mkdir -p data/raw/tobacco800

# Download and extract (example - check dataset-installation.md for actual URLs)
cd data/raw/tobacco800
wget https://example.com/tobacco800.tar.gz
tar -xzf tobacco800.tar.gz
cd ../../..

# Verify
ls -lh data/raw/tobacco800/
```

**For complete download instructions**, see [DATASET_INSTALLATION.md](dataset-installation.md).

### 2. Python Dependencies

Ensure all dependencies are installed:

```bash
# Install with augmentation dependencies
poetry install --with dev

# Verify installation
poetry run python -c "import albumentations, cv2, numpy; print('✓ Dependencies OK')"
```

---

## Dataset Generation

### Step 1: Generate Synthetic Augmented Dataset

Run the preparation script with your source dataset:

```bash
# Basic usage (50k samples from Tobacco800)
poetry run python scripts/prepare_phase2_data.py \
    --source-dirs data/raw/tobacco800 \
    --output-dir datasets/iqa_phase2 \
    --num-samples 50000 \
    --preset medium

# Multiple source datasets
poetry run python scripts/prepare_phase2_data.py \
    --source-dirs data/raw/tobacco800 data/raw/docbank \
    --output-dir datasets/iqa_phase2 \
    --num-samples 50000 \
    --preset medium

# Heavy augmentation for challenging training
poetry run python scripts/prepare_phase2_data.py \
    --source-dirs data/raw/tobacco800 \
    --output-dir datasets/iqa_phase2 \
    --num-samples 50000 \
    --preset heavy
```

**Parameters:**

- `--source-dirs`: One or more directories containing source images (required)
- `--output-dir`: Output directory (default: `datasets/iqa_phase2`)
- `--num-samples`: Total samples to generate (default: 50000)
- `--preset`: Augmentation intensity - `light`, `medium`, `heavy` (default: `medium`)
- `--train-split`: Training set fraction (default: 0.70)
- `--val-split`: Validation set fraction (default: 0.15)
- `--test-split`: Test set fraction (default: 0.15)
- `--seed`: Random seed for reproducibility (default: 42)

**Processing Time:**

- Tobacco800 (1,290 images): ~20-30 minutes for 50k samples
- DocBank (500k images): ~30-45 minutes for 50k samples
- Progress bar shows real-time status

**Output Structure:**

```
datasets/iqa_phase2/
├── train/
│   ├── images/
│   │   ├── img_000001.png
│   │   ├── img_000002.png
│   │   └── ... (35,000 images)
│   └── labels.json
├── val/
│   ├── images/
│   │   └── ... (7,500 images)
│   └── labels.json
└── test/
    ├── images/
    │   └── ... (7,500 images)
    └── labels.json
```

### Step 2: Verify Generated Dataset

Check that dataset was created correctly:

```bash
# Verify directory structure
ls -lh datasets/iqa_phase2/
ls -lh datasets/iqa_phase2/train/images/ | head -20

# Check total size
du -sh datasets/iqa_phase2/

# Inspect labels.json
head -100 datasets/iqa_phase2/train/labels.json

# Verify image counts
find datasets/iqa_phase2/train/images -name "*.png" | wc -l  # Should be 35,000
find datasets/iqa_phase2/val/images -name "*.png" | wc -l    # Should be 7,500
find datasets/iqa_phase2/test/images -name "*.png" | wc -l   # Should be 7,500
```

Expected output statistics (from script):

```
DATASET GENERATION COMPLETE
============================================================

Output directory: datasets/iqa_phase2
Total samples: 50000

TRAIN SET (35000 samples):
  Issue frequencies:
    noise          :  7000 (20.0%)
    blur           :  5250 (15.0%)
    skew           :  3500 (10.0%)
    perspective    :  3500 (10.0%)
    low_contrast   :  5250 (15.0%)
    orientation    :  1750 (5.0%)

VAL SET (7500 samples):
  Issue frequencies:
    noise          :  1500 (20.0%)
    blur           :  1125 (15.0%)
    skew           :   750 (10.0%)
    perspective    :   750 (10.0%)
    low_contrast   :  1125 (15.0%)
    orientation    :   375 (5.0%)

TEST SET (7500 samples):
  Issue frequencies:
    noise          :  1500 (20.0%)
    blur           :  1125 (15.0%)
    skew           :   750 (10.0%)
    perspective    :   750 (10.0%)
    low_contrast   :  1125 (15.0%)
    orientation    :   375 (5.0%)
```

---

## Upload to Google Cloud Storage

### Step 3: Configure GCS Access

```bash
# Verify gcloud authentication
gcloud auth list

# If not authenticated, login
gcloud auth login

# Set project
gcloud config set project image-detection-478105

# Verify bucket access
gsutil ls gs://image_detection_b
```

### Step 4: Upload Configuration

Upload the Phase 2 training configuration:

```bash
./scripts/gcs_helpers.sh upload-configs
```

This uploads:
- `configs/colab_phase2_iqa_gcs.yaml` → `gs://image_detection_b/configs/`

### Step 5: Upload Dataset to GCS

Use the GCS helper script to upload your generated dataset:

```bash
# Upload Phase 2 dataset (takes 10-30 minutes for ~10GB)
./scripts/gcs_helpers.sh upload-phase2
```

**What this does:**

1. Verifies `datasets/iqa_phase2/` exists locally
2. Uploads `train/`, `val/`, `test/` directories to GCS in parallel
3. Verifies upload with size check
4. Shows total bucket size

**Progress output:**

```
[INFO] Uploading Phase 2 dataset to GCS...
[INFO] This may take 10-30 minutes for ~10GB...
Copying file://datasets/iqa_phase2/train/images/img_000001.png [Content-Type=image/png]...
...
[INFO] Verifying upload...
10.2 GiB    gs://image_detection_b/datasets/iqa_phase2
[INFO] ✓ Phase 2 dataset uploaded
```

### Step 6: Verify GCS Upload

```bash
# List bucket contents
./scripts/gcs_helpers.sh list

# Show storage usage and costs
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

## Dataset Format

### labels.json Structure

Each split (train/val/test) has a `labels.json` file with this structure:

```json
[
  {
    "image_path": "img_000001.png",
    "labels": {
      "noise": {
        "value": 1,
        "confidence": 0.85,
        "source": "brisque",
        "brisque_score": 55.3
      },
      "blur": {
        "value": 0,
        "confidence": 0.92,
        "source": "laplacian",
        "laplacian_variance": 250.7
      },
      "skew": {
        "value": 0,
        "confidence": 0.88,
        "source": "hough_transform",
        "skew_angle_degrees": 1.2
      },
      "perspective": {
        "value": 0,
        "confidence": 0.75,
        "source": "edge_straightness",
        "edge_deviation_degrees": 3.5
      },
      "low_contrast": {
        "value": 0,
        "confidence": 0.88,
        "source": "rms_contrast",
        "rms_contrast": 0.45
      },
      "orientation": {
        "value": 0,
        "confidence": 0.95,
        "source": "heuristic_upright",
        "note": "Labeled from augmentation metadata"
      }
    },
    "quality_scores": {
      "brisque": 55.3,
      "niqe": 12.8,
      "laplacian_variance": 250.7,
      "rms_contrast": 0.45,
      "skew_angle_degrees": 1.2,
      "edge_deviation_degrees": 3.5
    }
  }
]
```

**Field Descriptions:**

- `image_path`: Relative path to image (e.g., `img_000001.png`)
- `labels`: Dictionary with 6 quality issue types
  - `value`: Binary label (0 = no issue, 1 = issue present)
  - `confidence`: Confidence score [0, 1]
  - `source`: Labeling function name
  - Additional metadata fields (e.g., `brisque_score`, `laplacian_variance`)
- `quality_scores`: Raw quality metric scores for analysis

---

## Augmentation Details

### Applied Transformations

The augmentation pipeline applies the following transformations with probabilities:

| Issue Type | Probability | Transformations |
|------------|-------------|-----------------|
| **Noise** | 20% | Gaussian noise, ISO noise, multiplicative noise |
| **Blur** | 15% | Gaussian blur, motion blur, defocus, median blur |
| **Low Contrast** | 15% | Brightness/contrast reduction, CLAHE, equalization |
| **Perspective** | 10% | Perspective distortion (scale 0.02-0.10) |
| **Orientation** | 5% | Rotation (±10° skew or 90/180/270° rotation) |
| **Compression** | 10% | JPEG compression (quality 50-95) |
| **Downscale** | 20% | Downscale + upscale (0.5-0.9x) |

**Presets:**

- **Light**: Reduced probabilities (10%, 8%, 8%, 5%, 2%, 5%)
- **Medium** (default): Balanced probabilities (above)
- **Heavy**: Increased probabilities (35%, 25%, 25%, 20%, 10%, 20%)

### Weak Supervision Labeling

Labels are generated automatically using reference-free image quality metrics:

| Issue Type | Metric | Threshold | Confidence |
|------------|--------|-----------|------------|
| **Noise** | BRISQUE | >30 (good), >50 (poor) | 0.70-0.90 |
| **Blur** | Laplacian Variance | <100 (blurry), <50 (very blurry) | 0.75-0.95 |
| **Skew** | Hough Transform | >2° (acceptable), >5° (skewed) | 0.75-0.92 |
| **Perspective** | Edge Straightness | >5° (straight), >10° (distorted) | 0.65-0.80 |
| **Low Contrast** | RMS Contrast | <0.3 (low), <0.2 (very low) | 0.75-0.90 |
| **Orientation** | Augmentation Metadata | N/A | 0.95-0.99 |

**Note**: These thresholds are initial estimates and will be refined during Phase 2 Week 2 validation.

---

## Troubleshooting

### Issue: Script fails with "No source images found"

**Solution**: Verify source directory exists and contains images:

```bash
ls -lh data/raw/tobacco800/
find data/raw/tobacco800/ -name "*.png" | head -10
```

### Issue: "ModuleNotFoundError: No module named 'albumentations'"

**Solution**: Install dependencies:

```bash
poetry install --with dev
```

### Issue: Script runs slowly

**Reasons**:
- Large source images (>2MB) require more processing time
- Heavy augmentation preset increases processing time
- Disk I/O bottleneck (especially on HDD)

**Solutions**:
- Use SSD for faster disk I/O
- Reduce `--num-samples` for testing
- Use `--preset light` for faster generation

### Issue: GCS upload fails with authentication error

**Solution**: Re-authenticate and set project:

```bash
gcloud auth login
gcloud config set project image-detection-478105
gsutil ls gs://image_detection_b  # Test access
```

### Issue: GCS upload is slow

**Solution**: The script uses parallel transfer (`-m` flag) with 4 processes. This is already optimized. Upload time depends on internet speed:

- 10 Mbps: ~2-3 hours for 10GB
- 50 Mbps: ~30-40 minutes for 10GB
- 100 Mbps: ~15-20 minutes for 10GB

---

## Next Steps

After generating and uploading the dataset:

1. **Verify GCS Structure**:
   ```bash
   gsutil ls gs://image_detection_b/datasets/iqa_phase2/
   gsutil ls gs://image_detection_b/datasets/iqa_phase2/train/images/ | head -20
   ```

2. **Open Colab Training Notebook**:
   - [notebooks/colab/phase2_iqa_training.ipynb](../notebooks/colab/phase2_iqa_training.ipynb)

3. **Follow Training Guide**:
   - [COLAB_TRAINING_GUIDE.md](colab-training.md)

---

## Quick Reference Commands

```bash
# Generate dataset (50k samples)
poetry run python scripts/prepare_phase2_data.py \
    --source-dirs data/raw/tobacco800 \
    --output-dir datasets/iqa_phase2 \
    --num-samples 50000 \
    --preset medium

# Upload configs
./scripts/gcs_helpers.sh upload-configs

# Upload dataset
./scripts/gcs_helpers.sh upload-phase2

# Check storage
./scripts/gcs_helpers.sh info

# Start training
# Open: notebooks/colab/phase2_iqa_training.ipynb
```

---

*For complete Phase 2 implementation details, see [phase-2-plan.md](project/phases/phase-2-plan.md)*
