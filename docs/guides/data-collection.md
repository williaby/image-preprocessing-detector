---
schema_type: common
title: "Data Collection Strategy - Phase 2 Week 1"
tags:
  - guide
  - datasets
status: published
owner: docs-team
purpose: Guide for data collection strategy - phase 2 week 1.
---

**Objective**: Collect 10k+ clean document images and generate 50k augmented training dataset
**Timeline**: Days 1-5 (Week 1 of Phase 2)
**Storage Required**: ~30GB

---

## Overview

Phase 2 requires a diverse training dataset for multi-label image quality assessment (IQA). We'll use a combination of:
1. **Public datasets** (10k clean base images)
2. **Synthetic augmentation** (40k degraded images via Albumentations)
3. **Weak supervision** (automatic labeling via BRISQUE/NIQE)
4. **Manual validation** (5k samples for quality control)

---

## Dataset Sources

### 1. RVL-CDIP (Primary Source)
**Ryerson Vision Lab - Complex Document Information Processing**

**Overview**:
- **Size**: 400,000 grayscale document images
- **Categories**: 16 document types (letter, form, email, resume, memo, etc.)
- **Format**: TIFF, grayscale
- **Resolution**: Variable (most 300 DPI)
- **Quality**: High-quality scans
- **License**: Public domain (government documents)

**Download**:
```bash
# Official source (Carnegie Mellon)
wget https://www.cs.cmu.edu/~aharley/rvl-cdip/rvl-cdip.tar.gz

# Extract (320GB compressed, 400k images)
tar -xzf rvl-cdip.tar.gz -C data/raw/rvl-cdip/

# Select diverse sample (10k images)
python scripts/data_collection/sample_rvlcdip.py \
    --input data/raw/rvl-cdip/ \
    --output data/raw/selected/ \
    --num-samples 6000 \
    --stratify-by-category
```

**Selection Criteria**:
- 375 images per category (6000 total) for balanced representation
- Prefer 300 DPI or higher
- Exclude severely degraded originals
- Ensure varied document layouts

**Storage**: 6000 images × 300KB avg = ~1.8GB

---

### 2. Tobacco800 (Secondary Source)
**Legacy Tobacco Document Library**

**Overview**:
- **Size**: 1,290 document images
- **Categories**: 10 document types
- **Format**: TIFF, mostly grayscale
- **Resolution**: 150-300 DPI
- **Quality**: Real-world scans with artifacts (valuable for validation)
- **License**: Public domain

**Download**:
```bash
# Official source
wget http://www.cs.cmu.edu/~aharley/tobacco800/Tobacco800.tar.gz

# Extract
tar -xzf Tobacco800.tar.gz -C data/raw/tobacco800/

# Use all 1,290 images (already filtered)
```

**Usage**:
- **Training**: 500 images (mixed with RVL-CDIP)
- **Validation**: 500 images (real-world quality variations)
- **Test**: 290 images (holdout set)

**Storage**: 1,290 images × 400KB avg = ~500MB

---

### 3. DocBank (Tertiary Source)
**Document Layout Analysis Benchmark**

**Overview**:
- **Size**: 500,000+ document pages with layout annotations
- **Format**: PDF + annotations
- **Source**: arXiv papers (LaTeX-generated PDFs)
- **Resolution**: Born-digital (vector PDFs)
- **Quality**: Very high (ideal baseline for augmentation)
- **License**: CC BY 4.0

**Download**:
```bash
# GitHub repository
git clone https://github.com/doc-analysis/DocBank.git data/raw/docbank/

# Download subset (requires manual selection)
# Focus on papers with images/figures for realistic content
```

**Selection Criteria**:
- 3,000 pages with diverse layouts
- Prefer pages with embedded images/figures
- Mix of single-column and multi-column
- Rasterize to 300 DPI for consistency

**Rasterization**:
```bash
python scripts/data_collection/rasterize_docbank.py \
    --input data/raw/docbank/PDFs/ \
    --output data/raw/selected/ \
    --dpi 300 \
    --num-samples 3000
```

**Storage**: 3,000 images × 500KB avg = ~1.5GB

---

## Data Collection Plan (Days 1-3)

### Day 1: Setup and RVL-CDIP Download

**Tasks**:
1. Create download scripts in `scripts/data_collection/`
2. Download RVL-CDIP dataset (320GB compressed, ~12 hours)
3. Implement stratified sampling script

**Scripts to Create**:
- `scripts/data_collection/download_rvlcdip.sh`
- `scripts/data_collection/sample_rvlcdip.py`

**Deliverables**:
- [ ] RVL-CDIP downloaded (or in progress)
- [ ] 6,000 diverse images selected

---

### Day 2: Tobacco800 and DocBank

**Tasks**:
1. Download Tobacco800 (small, ~5 minutes)
2. Clone DocBank repository
3. Implement PDF rasterization script for DocBank
4. Rasterize 3,000 DocBank pages to 300 DPI

**Scripts to Create**:
- `scripts/data_collection/download_tobacco800.sh`
- `scripts/data_collection/rasterize_docbank.py`

**Deliverables**:
- [ ] Tobacco800 downloaded (1,290 images)
- [ ] DocBank cloned and 3,000 pages rasterized

---

### Day 3: Dataset Organization and Validation

**Tasks**:
1. Organize all images into `data/raw/selected/`
2. Validate image quality (resolution, format, corruption)
3. Create dataset manifest (CSV with metadata)
4. Split into train/val/test sets

**Scripts to Create**:
- `scripts/data_collection/validate_dataset.py`
- `scripts/data_collection/create_manifest.py`
- `scripts/data_collection/split_dataset.py`

**Dataset Manifest** (CSV format):
```csv
image_path,source,category,resolution,width,height,file_size
data/raw/selected/img_0001.tif,rvlcdip,letter,300,2550,3300,245120
data/raw/selected/img_0002.tif,tobacco800,form,300,2200,2800,312458
...
```

**Train/Val/Test Split**:
- **Train**: 70% (7,000 images) → augmented to 50k
- **Val**: 15% (1,500 images) → augmented to 10k
- **Test**: 15% (1,500 images) → **NO augmentation** (real-world only)

**Deliverables**:
- [ ] 10,000+ clean images in `data/raw/selected/`
- [ ] Dataset manifest CSV
- [ ] Train/val/test split CSVs

---

## Synthetic Augmentation (Days 3-4)

**Objective**: Generate 40k augmented training images + 10k validation images

**Augmentation Pipeline**: See `data/augmentation.py` (implemented separately)

**Augmentation Parameters**:
```python
# Per image, apply 1-3 random augmentations:
- Noise: 20% probability (Gaussian, ISO, multiplicative)
- Blur: 15% probability (Gaussian, motion, defocus)
- Low Contrast: 15% probability (brightness/contrast reduction)
- Perspective: 10% probability (skew, rotation, distortion)
- Orientation: 5% probability (90/180/270 degree rotation)
- Compression: 10% probability (JPEG artifacts)
```

**Generation Script**:
```bash
# Generate augmented dataset
python scripts/data_collection/generate_augmented.py \
    --input data/raw/selected/train.csv \
    --output data/augmented/ \
    --num-augmented-per-image 7 \
    --save-metadata
```

**Expected Output**:
- 7,000 train images × 7 augmentations = 49,000 augmented images
- 1,500 val images × 7 augmentations = 10,500 augmented images
- Total: 59,500 images (~18GB)

**Storage Layout**:
```
data/augmented/
├── train/
│   ├── img_0001_aug_0.png
│   ├── img_0001_aug_1.png
│   └── ...
├── val/
│   ├── img_7001_aug_0.png
│   └── ...
└── metadata.json  # Augmentation parameters per image
```

---

## Weak Supervision Labeling (Days 4-5)

**Objective**: Generate initial labels using image quality metrics

**Labeling Functions**: See `data/weak_supervision.py` (implemented separately)

**Quality Metrics**:
1. **BRISQUE**: Blind/Referenceless Image Spatial Quality Evaluator
   - Range: 0-100 (lower = better quality)
   - Thresholds: <30 (good), 30-50 (moderate), >50 (poor)

2. **NIQE**: Natural Image Quality Evaluator
   - Range: 0-100 (lower = better)
   - Thresholds: <5 (excellent), 5-10 (good), >10 (poor)

3. **Laplacian Variance**: Blur detection
   - Threshold: >200 (sharp), 100-200 (moderate), <100 (blurry)

4. **RMS Contrast**: Low contrast detection
   - Threshold: >0.4 (good), 0.3-0.4 (low), <0.3 (very low)

**Label Generation**:
```bash
python scripts/data_collection/weak_label.py \
    --input data/augmented/ \
    --output data/labels/ \
    --use-metrics brisque niqe laplacian rms_contrast
```

**Label Format** (JSON per image):
```json
{
  "image_path": "data/augmented/train/img_0001_aug_0.png",
  "labels": {
    "noise": {"value": 0, "confidence": 0.85, "source": "brisque"},
    "blur": {"value": 1, "confidence": 0.92, "source": "laplacian"},
    "skew": {"value": 0, "confidence": 0.70, "source": "hough"},
    "perspective": {"value": 0, "confidence": 0.65, "source": "edge_analysis"},
    "low_contrast": {"value": 1, "confidence": 0.88, "source": "rms_contrast"},
    "orientation": {"value": 0, "confidence": 0.95, "source": "orientation_detector"}
  },
  "quality_scores": {
    "brisque": 45.2,
    "niqe": 7.8
  }
}
```

**Deliverables**:
- [ ] Labels for all 59,500 augmented images
- [ ] Label confidence scores
- [ ] Quality metric distributions

---

## Manual Validation (Day 5)

**Objective**: Validate 5,000 ambiguous samples to improve label quality

**Selection Strategy**:
1. Low confidence labels (confidence < 0.70)
2. Conflicting labels (multiple labeling functions disagree)
3. Rare classes (ensure minimum samples)

**Annotation Tool**:
- **CVAT** (Computer Vision Annotation Tool)
- **Label Studio** (simpler, web-based)

**Annotation Interface**:
```
Image: [Display image]

Quality Issues (check all that apply):
☐ Noise (Gaussian, salt-and-pepper, ISO)
☐ Blur (Gaussian, motion, defocus)
☐ Skew (text lines not horizontal)
☐ Perspective (distortion, warping)
☐ Low Contrast (faded, washed out)
☐ Orientation (rotated 90/180/270°)

Confidence: ● Low  ● Medium  ● High
```

**Validation Workflow**:
```bash
# Select ambiguous samples
python scripts/data_collection/select_for_validation.py \
    --input data/labels/ \
    --output data/validation_queue.csv \
    --num-samples 5000 \
    --strategy low_confidence

# Import to Label Studio
# (Manual annotation step)

# Export validated labels
python scripts/data_collection/merge_validated_labels.py \
    --weak-labels data/labels/ \
    --manual-labels data/validated_labels.json \
    --output data/labels_final/
```

**Deliverables**:
- [ ] 5,000 manually validated labels
- [ ] Updated label confidence scores
- [ ] Inter-annotator agreement metrics

---

## Ground-Truth Test Set (Day 5)

**Objective**: Create 2,000 image test set with high-quality labels

**Source**: Reserve 1,500 images from initial split + 500 from Tobacco800 validation set

**Requirements**:
- **NO synthetic augmentation** (real-world images only)
- **Manual annotation** for all images
- **Multiple annotators** for quality control (3 annotators per image)
- **High confidence** labels only (>0.90 inter-annotator agreement)

**Test Set Composition**:
- **Clean images**: 500 (no quality issues)
- **Single issue**: 600 (one quality problem)
- **Multiple issues**: 600 (2-3 quality problems)
- **Severe issues**: 300 (critical quality problems)

**Deliverables**:
- [ ] 2,000 test images with gold-standard labels
- [ ] Inter-annotator agreement report (Fleiss' Kappa)
- [ ] Test set manifest with confidence scores

---

## Data Versioning with DVC

**Setup** (Day 5):
```bash
# Initialize DVC
poetry run dvc init

# Add remote storage (example: AWS S3)
poetry run dvc remote add -d storage s3://your-bucket/image-preprocessing-detector/datasets

# Track datasets
poetry run dvc add data/raw/selected/
poetry run dvc add data/augmented/
poetry run dvc add data/labels_final/
poetry run dvc add data/test_set/

# Commit DVC files
git add data/.dvc .dvc/config
git commit -m "Add Phase 2 dataset (10k base, 50k augmented, 2k test)"

# Push datasets to remote
poetry run dvc push
```

**DVC Benefits**:
- Version control for large datasets
- Reproducible data pipeline
- Team collaboration (shared remote storage)
- Efficient storage (deduplication)

---

## Summary Checklist

### Week 1 Deliverables
- [ ] **10,000+ base images** from RVL-CDIP (6k), Tobacco800 (1.3k), DocBank (3k)
- [ ] **50,000+ augmented images** for training
- [ ] **10,000+ augmented images** for validation
- [ ] **2,000 test images** (real-world, manually labeled)
- [ ] **Weak supervision labels** for all augmented images
- [ ] **5,000 manually validated labels** for ambiguous cases
- [ ] **DVC configuration** with remote storage
- [ ] **Dataset manifests** (CSV) with metadata

### Storage Usage
```
data/raw/selected/        1.8GB  (6k RVL-CDIP)
data/raw/tobacco800/      0.5GB  (1.3k Tobacco800)
data/raw/docbank/         1.5GB  (3k DocBank)
data/augmented/train/    15.0GB  (50k augmented)
data/augmented/val/       3.0GB  (10k augmented)
data/test_set/            0.8GB  (2k real-world)
data/labels_final/        0.5GB  (JSON labels)
----------------------------------------------
Total:                   23.1GB  (well under 30GB budget)
```

---

## Next Steps

After data collection (Week 1):
1. **Week 2**: Train MobileNetV3-Small on collected dataset
2. **Week 3**: Evaluate and optimize model
3. **Week 4**: Integrate into detection pipeline

---

*Last Updated: 2025-11-12*
*Status: Ready to execute*
*Timeline: Days 1-5 (Week 1 of Phase 2)*
