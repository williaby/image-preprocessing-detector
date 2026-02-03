---
schema_type: common
title: "IQA Training Dataset Methodology"
tags:
  - dataset
  - ml
  - training
status: published
owner: docs-team
purpose: Comprehensive methodology for creating training datasets for Document Image Quality Assessment models.
---

> **Version**: 1.0.0
> **Created**: 2025-12-16
> **Dataset Version**: phase7_mvp v1.0
> **Purpose**: Document Image Quality Assessment (IQA) model training

---

## Abstract

This document describes the methodology for creating the training dataset used for the
ResNet-50 teacher and ResNet-18 student IQA models in Project A of the RAG document
pipeline. The dataset comprises 25,000 document images from 16 diverse sources with
synthetic degradation augmentations and continuous severity labels. This methodology
enables full reproducibility and provides validation criteria for dataset adequacy.

---

## 1. Dataset Overview

### 1.1 Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 25,000 |
| **Train Split** | 17,469 (69.9%) |
| **Validation Split** | 3,719 (14.9%) |
| **Test Split** | 3,812 (15.2%) |
| **Image Resolution** | 384 x 384 pixels |
| **Format** | JPEG (variable quality 39-99) |
| **Total Size** | ~858 MB (compressed) |

### 1.2 Label Dimensions

Each sample has continuous severity labels in the range [0.0, 1.0]:

| Label | Description | Range |
|-------|-------------|-------|
| `blur_severity` | Gaussian/motion/median blur intensity | 0.0 (sharp) to 0.95 (severe) |
| `noise_severity` | Gaussian/salt-pepper/speckle noise level | 0.0 (clean) to 0.95 (severe) |
| `compression_severity` | JPEG compression artifact severity | 0.0 (high quality) to 0.95 (severe) |
| `contrast_severity` | Contrast/brightness degradation | 0.0 (normal) to 0.95 (severe) |
| `skew_severity` | Rotation angle magnitude | 0.0 (aligned) to 0.57 (max) |
| `perspective_severity` | Perspective distortion magnitude | 0.0 (none) to 0.38 (max) |
| `dqs_score` | Document Quality Score (aggregate) | 0.2 (poor) to 1.0 (excellent) |

---

## 2. Source Dataset Composition

### 2.1 Source Distribution

The dataset draws from 16 publicly available document image datasets to ensure domain
diversity and reduce bias toward any single document type.

| Source | Samples | Percentage | Domain Category | Document Type |
|--------|---------|------------|-----------------|---------------|
| **diqa_5000** | 3,500 | 14.0% | Real Degraded | Scanned |
| **rvl_cdip** | 3,500 | 14.0% | Mixed Layouts | Hybrid |
| **tablebank** | 2,500 | 10.0% | Tables | Born Digital |
| **doclaynet** | 2,500 | 10.0% | Mixed Layouts | Hybrid |
| **pubtabnet** | 2,000 | 8.0% | Tables | Born Digital |
| **sroie** | 1,500 | 6.0% | Receipts | Scanned |
| **nist_sd19** | 1,500 | 6.0% | Handwriting | Scanned |
| **tobacco_800** | 1,285 | 5.1% | Real Degraded | Scanned |
| **nist_db2** | 1,200 | 4.8% | Forms | Scanned |
| **nist_sd6** | 1,200 | 4.8% | Forms | Scanned |
| **maths_handwriting** | 1,200 | 4.8% | Math | Scanned |
| **funsd_plus** | 1,139 | 4.6% | Forms | Scanned |
| **multimodal_textbook** | 648 | 2.6% | Educational | Hybrid |
| **mathverse** | 500 | 2.0% | Math | Born Digital |
| **dibco** | 128 | 0.5% | Real Degraded | Scanned |

### 2.2 Domain Category Distribution

| Category | Train Samples | Percentage | Purpose |
|----------|---------------|------------|---------|
| Mixed Layouts | 4,196 | 24.0% | Multi-column, complex pages |
| Real Degraded | 3,925 | 22.5% | Authentic degradation patterns |
| Tables | 3,146 | 18.0% | Structured tabular content |
| Forms | 2,470 | 14.1% | Form fields, check boxes |
| Math | 1,187 | 6.8% | Mathematical formulas |
| Receipts | 1,048 | 6.0% | Mobile capture scenarios |
| Handwriting | 1,047 | 6.0% | Handwritten documents |
| Educational | 450 | 2.6% | Textbook content |

### 2.3 Document Type Distribution

| Type | Train Samples | Percentage | Characteristics |
|------|---------------|------------|-----------------|
| Scanned | 8,533 | 48.8% | Physical document scans |
| Hybrid | 5,441 | 31.1% | Mixed digital/scanned |
| Born Digital | 3,495 | 20.0% | Native digital documents |

---

## 3. Synthetic Degradation Pipeline

### 3.1 Degradation Types

Five categories of synthetic degradation are applied:

| Type | Augmentation Methods | Severity Levels |
|------|---------------------|-----------------|
| **Blur** | Gaussian, motion, median blur | Light (σ=1-3), Medium (σ=3-7), Heavy (σ=7-11), Extreme (σ=11-15) |
| **Noise** | Gaussian, salt-pepper, speckle | Light (var=5-15), Medium (15-30), Heavy (30-50), Extreme (50-80) |
| **Compression** | JPEG quality reduction | Light (Q=70-85), Medium (Q=50-70), Heavy (Q=30-50), Extreme (Q=15-30) |
| **Lighting** | Brightness, contrast, gamma | Light (±10%), Medium (±20%), Heavy (±30%), Extreme (±40%) |
| **Geometric** | Rotation, perspective | Light (1-3°), Medium (3-7°), Heavy (7-12°), Extreme (12-20°) |

### 3.2 Defect Level Distribution

| Level | Samples | Percentage | Description |
|-------|---------|------------|-------------|
| Clean | 6,214 | 24.9% | No synthetic degradation |
| Light | 6,897 | 27.6% | 1 defect type, low severity |
| Medium | 6,870 | 27.5% | 1-2 defect types, moderate severity |
| Heavy | 3,298 | 13.2% | 2-3 defect types, high severity |
| Extreme | 1,721 | 6.9% | 3-5 defect types, severe degradation |

### 3.3 Defect Type Frequency (Train Split)

| Defect Type | Occurrences | Notes |
|-------------|-------------|-------|
| Geometric | 6,578 | Rotation + perspective |
| Lighting | 6,556 | Brightness + contrast |
| Blur | 6,525 | Gaussian/motion/median |
| Noise | 6,489 | Various noise types |
| Compression | 6,393 | JPEG artifacts |

### 3.4 Severity Score Statistics (Train Split)

| Dimension | Mean | Std Dev | Min | Max |
|-----------|------|---------|-----|-----|
| Blur | 0.213 | 0.316 | 0.0 | 0.95 |
| Noise | 0.212 | 0.316 | 0.0 | 0.95 |
| Compression | 0.210 | 0.316 | 0.0 | 0.95 |
| Contrast | 0.213 | 0.316 | 0.0 | 0.95 |
| Skew | 0.129 | 0.190 | 0.0 | 0.57 |
| Perspective | 0.086 | 0.127 | 0.0 | 0.38 |
| **DQS** | 0.828 | 0.201 | 0.2 | 1.0 |

### 3.5 Parameter to Severity Mapping

The continuous severity labels [0.0, 0.95] are calculated from augmentation parameters:

| Defect Type | Parameter | Formula | Example |
|-------------|-----------|---------|---------|
| **Blur** | kernel_size (σ) | `(σ - 1) / 14` | σ=8 → 0.50 |
| **Noise** | variance | `variance / 80` | var=40 → 0.50 |
| **Compression** | JPEG quality Q | `(100 - Q) / 85` | Q=50 → 0.59 |
| **Contrast** | brightness_delta | `abs(delta) / 0.4` | ±0.2 → 0.50 |
| **Skew** | rotation_angle | `abs(angle) / 35` | 12° → 0.34 |
| **Perspective** | warp_factor | `warp / 0.25` | 0.1 → 0.40 |

**Clamping**: All severity values are clamped to [0.0, 0.95] to reserve 1.0 for
theoretically perfect quality (unachievable with any degradation).

### 3.6 Augmentation Application Order

Augmentations are applied in a **deterministic order** to ensure reproducibility:

1. **Geometric transforms** (rotation, perspective) - Applied first to avoid
   interpolation artifacts from subsequent operations
2. **Lighting transforms** (brightness, contrast, gamma) - Applied to pixel values
3. **Blur transforms** (Gaussian, motion, median) - Applied after lighting
4. **Noise transforms** (Gaussian, salt-pepper, speckle) - Added after blur
5. **Compression** (JPEG quality) - Applied last as final save operation

> **Rationale**: This order minimizes information loss. Geometric transforms on
> clean images preserve more detail than on noisy images. Compression is always
> last since it's part of the file save operation.

---

## 4. Dataset Generation Process

### 4.1 Pipeline Overview

```text
Source Images (E: drive)
        │
        ▼
┌───────────────────────────────────┐
│  1. consolidate_base_images.py    │  Random sample from 16 sources
│     - Sample 25K images           │  Seed: 42
│     - Create symlinks             │  SHA256 hash per image
│     - Generate manifest.json      │
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│  2. generate_iqa_dataset.py       │  Apply degradations
│     - Resize to 384x384           │  Seed: 42
│     - Apply augmentations         │  Continuous severity labels
│     - Calculate DQS scores        │
│     - Generate metadata.json      │
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│  3. create_phase7_splits.py       │  Stratified splitting
│     - 70/15/15 train/val/test     │  By source dataset
│     - Prevent source leakage      │  Separate metadata per split
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│  4. create_phase7_tar_archives.py │  Package for upload
│     - Compress with gzip          │  Include metadata.json
│     - Create manifest.json        │
└───────────────────────────────────┘
        │
        ▼
    Upload to GCS
    gs://image_detection_b/datasets/phase7_mvp/
```

### 4.2 Reproducibility Configuration

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Random Seed | 42 | All sampling and augmentation |
| Target Resolution | 384 x 384 | Preserves JPEG block boundaries |
| Resize Method | Lanczos | High-quality downsampling |
| JPEG Quality Range | 39-99 | Varies by defect level |

### 4.3 Scripts Location

All generation scripts are in the repository:

```text
scripts/
├── consolidate_base_images.py   # Step 1: Source sampling
├── generate_iqa_dataset.py      # Step 2: Augmentation
├── create_phase7_splits.py      # Step 3: Train/val/test split
└── create_phase7_tar_archives.py # Step 4: Packaging
```

---

## 5. Per-Image Lineage Tracking

### 5.1 Manifest Structure

Each image has complete lineage in `metadata.json`:

```json
{
  "filename": "sample_011496.jpg",
  "source_dataset": "nist_sd6",
  "original_path": "/mnt/e/image_detection/01_base_data/forms/nist_sd6/sd06/data/sfrs2_2/r0292/r0292_05.png",
  "sha256_original": "717b5ceafe806853d3bb571a3e51571e3f5092cc45257526ebe91a35b43d3b21",
  "defect_level": "extreme",
  "defects_applied": ["geometric_extreme", "noise_extreme", "compression_extreme", "blur_extreme", "lighting_extreme"],
  "dqs_score": 0.2,
  "jpeg_quality": 43,
  "document_type": "scanned",
  "domain_category": "forms",
  "severity_scores": {
    "blur_severity": 0.95,
    "noise_severity": 0.95,
    "compression_severity": 0.95,
    "contrast_severity": 0.95,
    "skew_severity": 0.57,
    "perspective_severity": 0.38
  }
}
```

### 5.2 Verification

To verify a sample's source:

1. Extract `sha256_original` from metadata
2. Locate source file via `original_path`
3. Compute SHA256 hash of first 64KB
4. Compare hashes

```python
import hashlib

def verify_source(original_path: str, expected_hash: str) -> bool:
    with open(original_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read(65536)).hexdigest()
    return actual_hash == expected_hash
```

---

## 6. Source Dataset References

### 6.1 Dataset Citations

| Dataset | Citation | License |
|---------|----------|---------|
| **DIQA-5000** | Document Image Quality Assessment Dataset | CC-BY-4.0 |
| **RVL-CDIP** | Harley et al. (2015), Ryerson Vision Lab | Academic |
| **TableBank** | Li et al. (2019), Microsoft Research | CC-BY-4.0 |
| **DocLayNet** | Pfitzmann et al. (2022), IBM Research | CDLA-Permissive-2.0 |
| **PubTabNet** | Zhong et al. (2020), IBM Research | CDLA-Permissive-2.0 |
| **SROIE** | ICDAR 2019 Competition | Custom |
| **NIST SD-19** | NIST Special Database 19 | Public Domain |
| **Tobacco-800** | Lewis et al. (2006), IIT | Academic |
| **NIST DB-2** | NIST Special Database 2 | Public Domain |
| **NIST SD-6** | NIST Special Database 6 | Public Domain |
| **HASYv2** | Thoma (2017), Math Handwriting | CC0 |
| **FUNSD** | Jaume et al. (2019), IBM Research | CC-BY-4.0 |
| **DIBCO** | Document Image Binarization Competition | Various |
| **MathVerse** | Math Reasoning Benchmark | CC-BY-4.0 |
| **Multimodal Textbook** | DAMO-NLP-SG | Apache-2.0 |

### 6.2 Source Data Location

All source datasets are stored on the E: drive with a category-based organization:

```text
/mnt/e/image_detection/
├── 01_base_data/                    # Training data organized by category
│   ├── degraded/                    # Real degradation sources
│   │   └── tobacco800/              # Historical scans
│   ├── documents/                   # Multi-category documents
│   │   ├── rvl_cdip/                # 16 document categories
│   │   └── doclaynet/               # Document layouts
│   ├── forms/                       # Structured forms
│   │   ├── nist_db2/                # Check images
│   │   ├── nist_sd6/                # Tax forms
│   │   ├── funsd_plus/              # Form understanding
│   │   └── sroie/                   # Receipts
│   ├── tables/                      # Tabular data
│   │   ├── tablebank/               # LaTeX/Word tables
│   │   ├── pubtabnet/               # Scientific tables
│   │   └── fintabnet/               # Financial tables
│   ├── handwriting/                 # Handwritten content
│   │   ├── nist_sd19_pages/         # Handwriting pages
│   │   ├── maths_handwriting/       # Math handwriting
│   │   └── signatr6k/               # Signatures
│   ├── formulas/                    # Mathematical content
│   │   ├── mathverse/               # Math diagrams
│   │   └── im2latex/                # Math formulas
│   ├── educational/                 # Educational content
│   │   ├── multimodal_textbook/     # Textbook pages
│   │   └── sample_100_images/       # Sample images
│   ├── language/                    # Multilingual content
│   └── text_detection/              # Text detection datasets
└── 02_benchmark_only/               # Evaluation-only datasets (NOT for training)
    ├── diqa-5000/                   # Human MOS scores - evaluation anchor
    ├── dibco/                       # Binarization benchmark
    ├── ohr-bench/                   # OCR benchmark
    ├── omnidocbench/                # Document understanding benchmark
    └── smartdoc-qa/                 # Mobile capture benchmark
```

> **Note**: The `02_benchmark_only/` datasets contain human-annotated quality scores
> and should be reserved for model evaluation to prevent data leakage.

See [DATASET_CATALOG.md](docs/reference/DATASET_CATALOG.md) for complete catalog.

---

## 7. Dataset Adequacy Validation

### 7.1 Domain Coverage Criteria

| Criterion | Target | Achieved | Status |
|-----------|--------|----------|--------|
| Source datasets | ≥10 | 16 | Pass |
| Domain categories | ≥5 | 8 | Pass |
| Document types | 3 (scanned/hybrid/born-digital) | 3 | Pass |
| Real degraded samples | ≥15% | 22.5% | Pass |
| Clean samples | 20-30% | 24.9% | Pass |
| Extreme degraded samples | 5-10% | 6.9% | Pass |

### 7.2 Label Distribution Criteria

| Criterion | Target | Achieved | Status |
|-----------|--------|----------|--------|
| Severity range coverage | [0.0, 0.95] | [0.0, 0.95] | Pass |
| DQS range coverage | [0.2, 1.0] | [0.2, 1.0] | Pass |
| Balanced defect types | ±10% variance | 6,393-6,578 | Pass |
| Multi-defect samples | ≥20% | ~46% (medium+heavy+extreme) | Pass |

### 7.3 Statistical Validation

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Mean DQS | 0.828 | Slight bias toward good quality |
| DQS Std Dev | 0.201 | Good spread across quality levels |
| Defect type balance | σ=70 | Excellent balance |
| Domain diversity | H=2.7 bits | Good entropy |

### 7.4 Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Synthetic degradation only | May not capture all real-world artifacts | 22.5% real degraded samples (DIQA, Tobacco, DIBCO) |
| 384x384 resolution | Loss of fine detail | Preserves JPEG block boundaries; higher res possible |
| English-centric | May underperform on other scripts | RVL-CDIP has some multilingual content |
| No color documents | Limited color artifact detection | Focus is on document legibility, not color accuracy |

---

## 8. Model Training Configuration

### 8.1 ResNet-50 Teacher Architecture

```python
ProductionTrainingConfig:
    model_architecture: "resnet50"
    num_heads: 5  # blur, noise, compression, contrast, geometric
    dropout: 0.3
    pretrained: True  # ImageNet weights
    input_resolution: 384
    loss_type: "gaussian_nll"  # Uncertainty-aware
```

### 8.2 Training Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Epochs | 100 | Extended for convergence |
| Batch Size | 32 | Limited by 384x384 resolution |
| Learning Rate | 1e-4 | AdamW optimizer |
| Weight Decay | 0.02 | Regularization |
| Warmup Epochs | 5 | Gradual LR increase |
| Gradient Clip | 1.0 | Stability |
| Seed | 42 | Reproducibility |

### 8.3 Early Stopping Criteria

| Metric | Target | Priority |
|--------|--------|----------|
| ECE (Expected Calibration Error) | < 0.08 | Primary |
| MAE (Mean Absolute Error) | < 0.15 | Secondary |
| Correlation | > 0.85 | Production |
| Uncertainty Correlation | > 0.50 | Calibration |

### 8.4 Document Quality Score (DQS) Formula

The DQS aggregates page-level IQA metrics into a document-level quality score:

**Per-Page Degradation Score:**

```text
page_degradation = 0.4 × blur_score + 0.3 × noise_score + 0.3 × contrast_score
```

**Document-Level Aggregation:**

```text
degradation_score = median(page_degradation) across all pages
complexity_score = max(layout_complexity) across all pages
```

**Pre-OCR Risk Score:**

```text
risk = (1 - degradation_score) × 0.4
     + complexity_score × 0.3
     + pdf_type_penalty
     + handwriting_penalty

where:
  pdf_type_penalty = 0.2 (image_only) | 0.1 (hybrid) | 0.0 (born_digital)
  handwriting_penalty = 0.1 if has_handwriting else 0.0
```

**Interpretation:**

| Score Range | Quality Level | OCR Expectation |
|-------------|---------------|-----------------|
| 0.8 - 1.0 | Excellent | High accuracy expected |
| 0.6 - 0.8 | Good | Standard processing |
| 0.4 - 0.6 | Fair | May need enhancement |
| 0.2 - 0.4 | Poor | Requires correction |
| 0.0 - 0.2 | Very Poor | OCR may fail |

> **Implementation**: See `src/image_preprocessing_detector/metrics/dqs_calculator.py`

---

## 9. Reproducibility Instructions

### 9.1 Prerequisites

1. Access to source datasets on E: drive (see Section 6.2)
2. Python 3.12+ with dependencies: `uv sync --extra ml`
3. ~50 GB disk space for intermediate files

### 9.2 Regeneration Steps

```bash
# Step 1: Sample base images from sources (requires E: drive access)
python scripts/consolidate_base_images.py

# Step 2: Apply augmentations and generate labels
python scripts/generate_iqa_dataset.py

# Step 3: Create train/val/test splits
python scripts/create_phase7_splits.py

# Step 4: Package into archives
python scripts/create_phase7_tar_archives.py

# Step 5: Upload to GCS (optional)
gsutil -m cp data/phase7_mvp/03_archives/*.tar.gz \
    gs://image_detection_b/datasets/phase7_mvp/
```

### 9.3 Verification

After regeneration, verify against original:

```bash
# Compare manifest hashes
sha256sum data/phase7_mvp/00_base_images/manifest.json
# Expected: (compare with original)

# Verify sample count
python -c "
import json
with open('data/phase7_mvp/01_augmented/metadata.json') as f:
    print(f'Samples: {json.load(f)[\"total_samples\"]}')"
# Expected: 25000

# Verify split sizes
wc -l data/phase7_mvp/02_splits/*.json
# Expected: train ~17469, val ~3719, test ~3812
```

### 9.4 Dependency Pinning

Critical dependencies for exact reproducibility:

| Package | Version | Purpose |
|---------|---------|---------|
| albumentations | 1.4.23 | Image augmentation transforms |
| pillow | 11.0.0 | Image I/O and preprocessing |
| numpy | 2.2.0 | Array operations |
| opencv-python | 4.10.0.84 | Computer vision operations |
| torch | 2.5.1 | Model training framework |
| torchvision | 0.20.1 | Image transforms and models |

**Lock File**: The exact versions are pinned in `uv.lock`. To ensure identical
environment:

```bash
# Install exact pinned versions
uv sync --frozen --extra ml

# Verify critical packages
uv pip list | grep -E "albumentations|pillow|numpy|opencv|torch"
```

> **Note**: Augmentation behavior may differ between albumentations versions.
> Always use the pinned version for reproducibility.

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-16 | Initial release with 16-source 25K dataset |

---

## 11. References

1. **Project Documentation**
   - [PHASE7_SPRINT_IMPLEMENTATION_PLAN.md](docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md)
   - [PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md](docs/planning/PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md)

2. **Dataset Catalogs**
   - [DATASET_CATALOG.md](/mnt/e/image_detection/DATASET_CATALOG.md) - Full source catalog
   - [docs/reference/DATASET_CATALOG.md](docs/reference/DATASET_CATALOG.md) - Local reference copy

3. **Model Training**
   - [modal/train_phase7_production.py](modal/train_phase7_production.py) - Production training script
   - [benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv](benchmarks/results/IQA_MODEL_BENCHMARK_TRACKER.csv) - Evaluation results

---

**Document Maintainer**: Byron Williams
**Last Updated**: 2025-12-16
