---
schema_type: common
title: "ADR-029: Three-Tier Dataset Strategy for Multi-Phase Training and Validation"
description: "Decision to adopt a three-tier dataset strategy (Training/Benchmarks/Test Fixtures) with synthetic and real-world data across all project phases (IQA, Layout, Preprocessing, Specialized Content)"
tags:
  - adr
  - phase_2
  - phase_3
  - dataset
  - training
  - validation
  - weak_supervision
  - iqa
  - layout
  - preprocessing
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the three-tier dataset strategy combining synthetic training data with automated labeling and external validation datasets with ground-truth annotations across all project capabilities (IQA, layout detection, preprocessing, specialized content)."
---

**Status**: ✅ **Accepted**
**Date**: 2025-11-13 (Phase 2 Week 1) | **Updated**: 2025-01-13 (Phase 3 Dataset Expansion)
**Deciders**: Byron Williams
**Related**: ADR-0022 (Synthetic Data Generation), ADR-0023 (Weak Supervision), ADR-0024 (Active Learning), ADR-0014 (Classical-ML Hybrid IQA), ADR-0031 (Benchmarking Framework)

---

## Context

### The Labeled Data Challenge

Phase 2 requires training a multi-label CNN for Image Quality Assessment (IQA) to detect 6 quality defects:
- **Blur**: Gaussian blur, motion blur, defocus
- **Noise**: Gaussian noise, salt-and-pepper, compression artifacts
- **Skew**: Document rotation (>2°)
- **Perspective**: Camera angle distortion
- **Low Contrast**: Poor lighting, faded scans
- **Orientation**: Incorrect rotation (90°, 180°, 270°)

**The Problem**: Publicly available IQA datasets (LIVE, CSIQ, LIVE Challenge) provide **overall quality scores** (MOS/DMOS) but **not multi-label defect classifications**. Research papers do not provide labeled datasets with specific defect types at scale.

**Requirements**:
1. **Training Set**: 50k+ samples with multi-label annotations (6 classes)
2. **Validation Set**: Ground-truth quality labels to validate model accuracy
3. **Test Fixtures**: Small samples (<50 MB) for CI/CD testing
4. **Licensing**: Permissive licenses allowing commercial use and redistribution

### Current Dataset Landscape

**Existing IQA Datasets**:
| Dataset | Size | Labels | License | Use Case |
|---------|------|--------|---------|----------|
| LIVE | 779 images | MOS scores (overall quality) | Academic/Research | Validation ✅ |
| CSIQ | 866 images | DMOS scores (overall quality) | Academic/Research | Validation ✅ |
| LIVE Challenge | 1,162 images | MOS scores (overall quality) | Academic/Research | Validation ✅ |
| DocLayNet | 40.97 GB | Layout annotations (no quality) | CDLA-Permissive-1.0 | Layout detection ❌ |
| TableBank | 46.38 GB | Table annotations (no quality) | Apache-2.0 | Layout detection ❌ |

**Gap Analysis**:
- ✅ **Ground-truth quality scores** exist (LIVE, CSIQ, LIVE Challenge)
- ❌ **Multi-label defect classifications** do not exist at scale
- ❌ **Document-specific IQA datasets** are scarce (most are natural images)
- ⚠️ **Camera captures** available but limited (scanned receipts, FUNSD)
- ⚠️ **Scanner artifacts** limited in public datasets

### Requirements for Phase 2 Training

**Training Performance Targets**:
- **mAP** (multi-label classification): > 0.88
- **Per-class F1**: > 0.85 for all 6 defect types
- **ECE** (calibration): < 0.1 (well-calibrated probabilities)

**Operational Constraints**:
- **Local Generation**: Create datasets locally (~2-3 days)
- **GCS Storage**: Upload to Google Cloud Storage (~26 GB)
- **Colab Training**: Download in Google Colab Pro for GPU training
- **Reproducibility**: Version-controlled dataset generation scripts

### Phase 3+ Dataset Expansion (2025-01-13 Update)

**Context**: Research analysis of 27 recent papers (Q4 2024 - Q4 2025) identified 10 additional datasets for Phase 3+ capabilities:

**New Capabilities**:
1. **Document-Specific IQA**: DIQA-5000 replaces LIVE/CSIQ natural image datasets
2. **Layout Detection**: DocSynth-300K (300k synthetic layouts, 6x larger than TableBank)
3. **Preprocessing**: DocRes unified model training data (SynDocDS, AnyPhotoDoc 6300)
4. **Reading Order**: ROOR dataset for sequence prediction
5. **Table Structure**: PubTables-1M (1M real-world tables from PubMed)
6. **Specialized Content**: StaVer + DDI-100 (stamps), IAM Handwriting dataset
7. **Comprehensive Benchmarking**: OmniDocBench (multi-domain document evaluation)

**Dataset Availability Status** (Validated 2025-01-13):
- ✅ **8/10 Available**: DocSynth-300K, SynDocDS, AnyPhotoDoc 6300, ROOR, PubTables-1M, StaVer, DDI-100, IAM Handwriting
- ⚠️ **2/10 Pending**: DIQA-5000 (Sept 2025 arXiv, dataset release pending), Seal-DB (Oct 2023 paper, code not released)

**Fallback Strategies**:
- DIQA-5000: Use LIVE/CSIQ until release (validated existing approach)
- Seal-DB: Use StaVer + DDI-100 for stamp detection (acceptable coverage)

**Impact on Three-Tier Strategy**:
- **Tier 1 (Training)**: +5 new datasets (DocSynth-300K, SynDocDS, PubTables-1M, IAM, StaVer+DDI-100)
- **Tier 2 (Benchmarks)**: +4 new benchmarks (DIQA-5000, AnyPhotoDoc 6300, ROOR, OmniDocBench)
- **Tier 3 (Test Fixtures)**: Expand with samples from new datasets (Phase 3 Week 2-3)

---

## Decision

**Adopt a hybrid dataset strategy combining synthetic training data with automated weak supervision labeling and external validation datasets with ground-truth quality scores.**

### Three-Tier Dataset Strategy

> **Terminology Note**: This ADR uses **"Storage Tier 1/2/3"** to describe data organization (Training/Benchmarks/Test Fixtures). For benchmarking validation strategy, see [ADR-031](0031-comprehensive-benchmarking-framework.md) which uses **"Validation Level 1/2/3"** for the testing pyramid (Test Fixtures → Smoke Tests → Full Benchmarks).

#### Storage Tier 1: Synthetic Training Data (50k samples, ~18 GB)

**Source**: TableBank dataset (46.38 GB, Apache-2.0 license)
**Generation**: Albumentations augmentation pipeline with document-specific transformations
**Labeling**: Weak supervision using classical IQA algorithms

**Implementation**:
```python
# scripts/prepare_phase2_data.py
from albumentations import Compose, GaussianBlur, GaussianNoise, Rotate, Affine

# Augmentation pipeline (medium preset)
transform = Compose([
    GaussianBlur(blur_limit=(3, 15), p=0.5),           # Label: blur
    GaussianNoise(var_limit=(10, 100), p=0.3),         # Label: noise
    Rotate(limit=15, border_mode=cv2.BORDER_CONSTANT, p=0.3),  # Label: skew
    Affine(rotate=0, shear=(-10, 10), p=0.2),          # Label: perspective
    # ... low_contrast, orientation
])

# Weak supervision labeling
from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur, detect_noise, detect_skew
)

labels = {
    "blur": detect_blur(image).is_blurry,              # BRISQUE + Laplacian
    "noise": detect_noise(image).is_noisy,             # Connected components
    "skew": detect_skew(image).angle > 2.0,            # Hough transform
    # ... perspective, low_contrast, orientation
}
```

**Dataset Structure**:
```
datasets/iqa_phase2/
├── train/                    # 35,000 samples (70%)
│   ├── images/
│   │   ├── 00000.jpg
│   │   └── ...
│   └── labels.json           # Multi-label annotations
├── val/                      # 7,500 samples (15%)
│   ├── images/
│   └── labels.json
├── test/                     # 7,500 samples (15%)
│   ├── images/
│   └── labels.json
└── metadata.json             # Generation config, source datasets
```

**Labels Format**:
```json
{
  "images": [
    {
      "file": "00000.jpg",
      "source": "tablebank/train/00123.png",
      "defects": {
        "blur": 0.8,          // Confidence scores [0-1]
        "noise": 0.0,
        "skew": 0.0,
        "perspective": 0.0,
        "low_contrast": 0.2,
        "orientation": 0.0
      },
      "weak_supervision": true,
      "generation_timestamp": "2025-11-13T10:30:00Z"
    }
  ]
}
```

**Advantages**:
- ✅ **Scale**: Generate 50k+ samples locally (vs. 2,807 from external datasets)
- ✅ **Document-Specific**: TableBank contains real document pages (not natural images)
- ✅ **Licensing**: Apache-2.0 allows commercial use and redistribution
- ✅ **Control**: Fine-tune augmentation severity and class balance
- ✅ **Reproducibility**: Version-controlled generation scripts

**Limitations**:
- ⚠️ **Weak Supervision Noise**: Labels are imperfect (classical detectors have ~10-15% error rate)
- ⚠️ **Synthetic Artifacts**: Augmented images may not match real-world camera/scanner defects
- ⚠️ **Limited Diversity**: TableBank is primarily printed documents (limited handwriting, diagrams)

#### Storage Tier 2: External Validation Data (~5 GB, 2,807 images)

**Datasets**:
1. **LIVE IQA Database** (779 images, ~1 GB)
   - Ground-truth DMOS scores (Difference Mean Opinion Score)
   - 5 defect types: JPEG compression, Gaussian blur, white noise, fastfading, JPEG2000
   - License: Academic/Research (cite required, redistribution for research allowed)

2. **CSIQ** (866 images, ~2 GB)
   - Ground-truth DMOS scores
   - 6 defect types: JPEG, JPEG2000, blur, contrast, pink noise, global contrast
   - License: Academic/Research

3. **LIVE Challenge** (1,162 images, ~2 GB)
   - Ground-truth MOS scores (authentic camera captures)
   - Real-world defects: blur, noise, compression (no synthetic augmentation)
   - License: Academic/Research

**Purpose**: **Validate model accuracy against human-annotated quality scores**

**Implementation**:
```python
# scripts/download_iqa_datasets.py
from iqadataset import load_dataset

# Download LIVE, CSIQ, LIVE Challenge
live = load_dataset("LIVE", dataset_root="data/benchmarks/external_iqa/", download=True)
csiq = load_dataset("CSIQ", dataset_root="data/benchmarks/external_iqa/", download=True)
live_challenge = load_dataset("LIVE_Challenge", dataset_root="data/benchmarks/external_iqa/", download=True)
```

**Validation Workflow**:
1. Train model on synthetic 50k dataset (Tier 1)
2. Evaluate on external validation datasets (Tier 2)
3. Compute correlation between predicted scores and ground-truth MOS/DMOS
4. **Target Metrics**:
   - Pearson correlation > 0.75 (linear correlation)
   - Spearman correlation > 0.75 (rank correlation)

**Advantages**:
- ✅ **Ground Truth**: Human-annotated quality scores (gold standard)
- ✅ **Real Defects**: LIVE Challenge has authentic camera captures
- ✅ **Research Standard**: LIVE/CSIQ are widely used benchmarks (comparable results)

**Limitations**:
- ⚠️ **Natural Images**: Most samples are natural scenes (not documents)
- ⚠️ **License Restrictions**: Research use only, not for commercial redistribution
- ⚠️ **Overall Scores**: MOS/DMOS are overall quality, not multi-label defect classifications

#### Storage Tier 3: Test Fixtures (Small samples for CI/CD, ~2 MB)

**Purpose**: Enable CI/CD testing without downloading 88+ GB of full datasets

**Sources**:
1. **LIVE Extracts** (5 samples, ~1.5 MB)
   - 1 reference image (clean, DMOS=0.0)
   - 1 JPEG compression sample (DMOS~25)
   - 1 Gaussian blur sample (DMOS~45)
   - 1 white noise sample (DMOS~38)
   - 1 low contrast sample (DMOS~52)

2. **Synthetic Variants** (3 samples, ~0.5 MB)
   - Extreme blur (edge case detection)
   - Combined defects (blur + noise)
   - Rotated/skewed document (orientation testing)

**Implementation**:
```python
# scripts/extract_iqa_fixtures.py
from iqadataset import load_dataset

# Load LIVE dataset
live = load_dataset("LIVE", dataset_root="data/benchmarks/external_iqa/")

# Extract 5 representative samples
fixtures = [
    live.get_sample("refimg_1.bmp"),      # Reference (clean)
    live.get_sample("img_jpeg_1.jpg"),    # JPEG compression
    live.get_sample("img_blur_1.bmp"),    # Gaussian blur
    live.get_sample("img_noise_1.bmp"),   # White noise
    live.get_sample("img_ff_1.bmp"),      # Low contrast
]

# Save to test fixtures
for i, sample in enumerate(fixtures):
    sample.save(f"data/test_fixtures/iqa_samples/live/{i}.jpg")
```

**Directory Structure**:
```
data/test_fixtures/
├── iqa_samples/                    # NEW: IQA-specific fixtures
│   ├── live/                       # LIVE dataset extracts
│   │   ├── reference_1.bmp        # Clean reference (DMOS=0.0)
│   │   ├── jpeg_1.jpg             # JPEG compression (DMOS=25.3)
│   │   ├── blur_1.bmp             # Gaussian blur (DMOS=45.7)
│   │   ├── noise_1.bmp            # White noise (DMOS=38.2)
│   │   └── contrast_1.bmp         # Low contrast (DMOS=52.1)
│   ├── synthetic/                  # Generated variants
│   │   ├── extreme_blur.png       # Edge case testing
│   │   ├── combined_defects.png   # Blur + noise
│   │   └── rotated_skewed.png     # Orientation testing
│   └── labels.json                 # Ground-truth quality scores
```

**CI/CD Integration**:
```python
# tests/integration/test_iqa_validation.py
def test_iqa_validation_pipeline():
    """Test IQA validation pipeline with ground-truth labels."""
    from image_preprocessing_detector.evaluation.iqa_validator import evaluate_iqa

    results = evaluate_iqa(
        model_path="models/phase2_iqa/best_model.pth",
        test_samples="data/test_fixtures/iqa_samples/labels.json"
    )

    # Expect reasonable correlation with ground-truth DMOS
    assert results["pearson_correlation"] > 0.6
    assert results["spearman_correlation"] > 0.6
```

**Advantages**:
- ✅ **Fast CI/CD**: No 5+ GB downloads required for integration tests
- ✅ **Offline Testing**: Developers can test IQA features without internet
- ✅ **Regression Detection**: Catch model accuracy degradation in automated tests

**Limitations**:
- ⚠️ **Limited Coverage**: Only 8 samples (not comprehensive)
- ⚠️ **License**: LIVE samples require citation in documentation

### Phase 3+ Dataset Additions (2025-01-13)

This section documents the expansion of the three-tier strategy to support Phase 3+ capabilities based on research analysis of Q4 2024 - Q4 2025 literature.

#### Tier 1: Training Data Expansion

**New Datasets for Phase 3+ Training**:

##### 1. DocSynth-300K (Layout Detection Training)
- **Source**: HuggingFace (juliozhao/DocSynth300K)
- **Size**: ~113 GB, 300,000 synthetic document layouts
- **License**: Not specified (arXiv:2410.12628 - assume research use)
- **Purpose**: Train YOLOv8/DLAFormer layout detection models (6x larger than TableBank)
- **Annotations**: Bounding boxes for text blocks, tables, images, headers, footers
- **Integration Tier**: Tier 1 (Training)
- **Download**: `huggingface-cli download juliozhao/DocSynth300K --repo-type dataset --local-dir data/training/layout/docsynth300k/`

**Structure**:
```
data/training/layout/
└── docsynth300k/
    ├── train/
    ├── val/
    ├── test/
    └── annotations/           # COCO-format annotations
```

##### 2. SynDocDS (Preprocessing Training - Shadow Removal)
- **Source**: MDPI Sensors 2024 paper (arXiv:2410.18116)
- **Size**: ~15 GB synthetic shadow dataset
- **License**: Apache-2.0 (inferred from paper)
- **Purpose**: Train shadow removal component (Note: DocRes unified model may obviate need)
- **Priority**: ⚠️ **LOWERED** - DocRes unified model handles shadow removal without separate training data
- **Integration Tier**: Tier 1 (Training) - **CONDITIONAL**
- **Download**: Available via paper authors (contact required)

**Note**: With DocRes adoption (ADR-020 update), SynDocDS becomes optional training data.

##### 3. PubTables-1M (Table Structure Extraction) - **REPLACED BY PUBTABNET**
- **Status**: ⚠️ **REMOVED** (2025-11-14) - Replaced by PubTabNet for storage optimization
- **Original Size**: ~109 GB (14 .tar.gz archives, unextracted)
- **Replacement**: PubTabNet (510k tables, 16GB, already extracted) - See Tier 2 Benchmarks
- **Rationale**: Storage optimization (109GB savings) + PubTabNet proven sufficient for SOTA table structure models
- **Decision**: ADR-029 Amendment (2025-11-14) - Use PubTabNet as primary training data for FR-4.11
- **Fallback**: Re-download from HuggingFace `bsmock/pubtables-1m` if PubTabNet insufficient (Phase 3 Week 6-7)
- **License**: CDLA-Permissive-1.0 (commercial use permitted)

**Decision Details**:
- **Academic Precedent**: TableFormer achieved 95.6% F1 with 460k tables (PubTabNet has 510k)
- **Performance Target**: FR-4.11 requires F1 >85%, achievable with PubTabNet based on literature
- **Test-First Strategy**: Train on PubTabNet (Phase 3 Week 1-5), re-download PubTables-1M only if F1 <85%
- **Storage Impact**: Freed 109GB immediately, can re-download in 2-3 hours if needed
- **Risk Assessment**: Low - PubTabNet same domain (PubMed scientific publications), proven annotations quality

**See**: [tmp_cleanup/.tmp-pubtables-analysis-20251114.md](../../tmp_cleanup/.tmp-pubtables-analysis-20251114.md) for complete analysis

##### 4. IAM Handwriting Database (Handwriting Detection)
- **Source**: HuggingFace (Teklia/IAM-line, Sept 2024 update)
- **Size**: 266 MB, 13,353 handwritten text line images
- **License**: Academic license (registration required)
- **Purpose**: Train handwriting detection model (FR-4.8, 95% accuracy target)
- **Annotations**: Handwritten vs. printed text labels
- **Integration Tier**: Tier 1 (Training)
- **Download**: `huggingface-cli download Teklia/IAM-line --repo-type dataset --local-dir data/training/specialized/handwriting/iam/`

**Structure**:
```
data/training/specialized/
├── handwriting/
│   └── iam/
│       ├── train/
│       ├── val/
│       └── test/
└── stamps/
    ├── staver/                # See below
    └── ddi-100/               # See below
```

##### 5. StaVer (Stamp Verification)
- **Source**: Kaggle (olegggatttor/stamp-verification)
- **Size**: ~50 MB, 400 images (200 stamped, 200 clean)
- **License**: CC BY-NC-SA 4.0 (academic/research use)
- **Purpose**: Train stamp detection model (FR-5.5)
- **Annotations**: Binary labels (stamp present/absent)
- **Integration Tier**: Tier 1 (Training)
- **Download**: `kaggle datasets download -d olegggatttor/stamp-verification -p data/training/specialized/stamps/staver/`

##### 6. DDI-100 (Document Defect Images)
- **Source**: GitHub (jenifferYingyiWu/AI-CU-2018)
- **Size**: ~5 GB, 99,870 images with stamps, hole punches, noise
- **License**: Not specified (assume research use)
- **Purpose**: Train noise artifact detection (stamps, hole punches) - FR-4.4
- **Annotations**: Multi-label defect classifications
- **Integration Tier**: Tier 1 (Training)
- **Download**: `git clone https://github.com/jenifferYingyiWu/AI-CU-2018 data/training/specialized/stamps/ddi-100/`

**Combined Usage**: StaVer + DDI-100 provide comprehensive stamp/artifact training data (100,270 total images).

#### Tier 2: Benchmark Data Expansion

**New Benchmarks for Phase 3+ Evaluation**:

##### 1. DIQA-5000 / DocIQ-5000 (Document-Specific IQA)
- **Source**: arXiv:2509.17012 (Sept 2025 paper)
- **Status**: ⚠️ **PENDING RELEASE** (dataset not yet public as of 2025-01-13)
- **Size**: ~3.9 GB (estimated), 5,000 document images with quality annotations
- **License**: TBD (pending release)
- **Purpose**: **Replace LIVE/CSIQ** natural image IQA benchmarks with document-specific evaluation
- **Annotations**: 3-dimensional quality scores (overall, sharpness, color fidelity)
- **Integration Tier**: Tier 2 (Benchmarks) - **HIGH PRIORITY**
- **Fallback**: Continue using LIVE/CSIQ until DIQA-5000 releases

**Target Structure**:
```
data/benchmarks/diqa-5000/
├── images/
├── annotations/               # 3-dimension quality scores
└── metadata.json              # Dataset statistics
```

**Rationale for Replacement**:
- LIVE/CSIQ are natural image datasets (not document-specific)
- DIQA-5000 provides document-tailored quality assessment (scanned documents, PDFs)
- 3-dimension output aligns with FR-2.3 learned quality assessment

##### 2. AnyPhotoDoc 6300 (Dewarping Benchmark)
- **Source**: arXiv:2410.12189 (Oct 2025 paper, DvD model)
- **Size**: ~2 GB, 6,300 camera-captured document images with warping
- **License**: Not specified (assume research use)
- **Purpose**: Benchmark dewarping accuracy (DocRes preprocessing validation)
- **Annotations**: Ground-truth flat documents + warped variants
- **Integration Tier**: Tier 2 (Benchmarks)
- **Download**: Contact paper authors (dataset release pending)

**Structure**:
```
data/benchmarks/anyphotodoc6300/
├── warped/                    # Camera-captured warped documents
├── ground_truth/              # Flat reference documents
└── annotations/               # Warp transformation parameters
```

##### 3. ROOR (Reading Order Recognition)
- **Source**: GitHub (chongzhangFDU/ROOR-Datasets)
- **Size**: Not specified (~500 MB estimated)
- **License**: CC BY 4.0 (commercial use with attribution)
- **Purpose**: Benchmark reading order prediction (FR-3.14 validation)
- **Annotations**: Ground-truth reading sequences for document elements
- **Integration Tier**: Tier 2 (Benchmarks) - **ELEVATED TO HIGH PRIORITY**
- **Download**: `git clone https://github.com/chongzhangFDU/ROOR-Datasets data/benchmarks/roor/`

**Structure**:
```
data/benchmarks/roor/
├── documents/
├── annotations/               # Reading order sequences
└── evaluation/                # Benchmark scripts
```

**Priority Elevation** (2025-01-13):
- **Previous Status**: Optional Phase 4-5 (not in core FR)
- **New Status**: **Phase 3 Critical** (elevated based on OHR-Bench findings)
- **Rationale**: OHR-Bench research demonstrates reading order errors cause **5-29% RAG performance loss**
- **Impact**: Reading Order Error (ROE) metric is **more critical** than individual quality defects
- **Action**: Create FR-3.14 (Reading Order Prediction) for Phase 3 implementation

##### 4. OmniDocBench (Comprehensive Document Evaluation)
- **Source**: HuggingFace (opendatalab/OmniDocBench)
- **Size**: 5.95 GB, multi-domain document benchmark
- **License**: Apache-2.0 (commercial use permitted)
- **Purpose**: **Comprehensive validation** across all document types (receipts, forms, tables, diagrams)
- **Annotations**: Multi-task annotations (layout, OCR, table structure, reading order)
- **Integration Tier**: Tier 2 (Benchmarks) - **CRITICAL**
- **Download**: `huggingface-cli download opendatalab/OmniDocBench --repo-type dataset --local-dir data/benchmarks/omnidocbench/`

**Structure**:
```
data/benchmarks/omnidocbench/
├── receipts/
├── forms/
├── tables/
├── diagrams/
├── annotations/               # Multi-task ground-truth
└── evaluation/                # Benchmark runners
```

**Rationale**: OmniDocBench provides **end-to-end validation** across all FR categories, replacing piecemeal benchmarks.

##### 5. OHR-Bench (OCR-RAG Performance Benchmark)
- **Source**: HuggingFace (opendatalab/OHR-Bench)
- **Size**: ~10 GB (estimated), 8,500+ PDF pages from 7 domains
- **License**: CC-BY-4.0 (commercial use with attribution)
- **Purpose**: **RAG-specific validation** - measures cascading impact of OCR quality on RAG retrieval and generation
- **Annotations**: Ground-truth structured data, OCR noise variants (formatting/semantic, mild/moderate/severe), Q&A pairs (8,498 total)
- **Integration Tier**: Tier 2 (Benchmarks) - **CRITICAL** (RAG evaluation)
- **Download**: `huggingface-cli download opendatalab/OHR-Bench --repo-type dataset --local-dir data/benchmarks/ohr-bench/`

**Structure**:
```
data/benchmarks/ohr-bench/
├── pdfs/                      # 8,500+ PDF pages
│   ├── textbook/
│   ├── law/
│   ├── finance/
│   ├── newspaper/
│   ├── manual/
│   ├── academic/
│   └── administration/
├── ground_truth/              # Structured data extraction
├── ocr_variants/              # OCR noise levels (mild, moderate, severe)
├── qa_pairs/                  # 8,498 Q&A for RAG evaluation
└── annotations/               # ROE (Reading Order Error) annotations
```

**Key Metrics** (From Research Analysis):
- **NDCG@5**: 0.74 (best OCR) vs. 0.773 (ground truth) = **4.5% retrieval gap**
- **Reading Order Error (ROE)**: 5-29% RAG performance loss
- **Semantic Noise**: More impactful than formatting noise for RAG
- **Multimodal Retrieval**: Recovers ~70% of OCR accuracy loss during generation

**Rationale**:
- First comprehensive benchmark measuring OCR's cascading impact on end-to-end RAG
- Validates FR-4.4 (RAG-Specific Document Quality Score) routing strategy
- Demonstrates that preprocessing quality directly limits RAG performance (invisible ceiling)
- Reading order errors identified as **critical bottleneck** (5-29% impact)

**Integration with FR-4.4**:
- Use OHR-Bench NDCG@5 metric for retrieval-readiness scoring
- Use ROE metric for reading order prediction validation (FR-3.14)
- Validate DQS routing: IF quality_score < 0.7 THEN use_multimodal_retrieval

#### Tier 3: Test Fixtures Expansion (Phase 3)

**New Test Fixtures for CI/CD**:

##### 1. DocSynth-300K Fixtures (5 samples, ~5 MB)
- Extract 5 representative layout samples for CI/CD
- Purpose: Fast layout detection validation

##### 2. PubTables-1M Fixtures (5 samples, ~3 MB)
- Extract 5 table structure samples
- Purpose: Table structure extraction smoke tests

##### 3. IAM Handwriting Fixtures (10 samples, ~2 MB)
- Extract 10 handwritten text samples
- Purpose: Handwriting detection CI/CD

##### 4. StaVer+DDI-100 Fixtures (10 samples, ~5 MB)
- Extract 10 stamp/artifact samples
- Purpose: Noise artifact detection tests

**Total Expansion**: +30 samples, ~15 MB (well within 50 MB limit)

**Extraction Script**: `scripts/extract_phase3_fixtures.py` (to be created in Phase 3 Week 2)

### Code Support

**Dataset Generation**:
- [scripts/prepare_phase2_data.py](../../scripts/prepare_phase2_data.py): Generate 50k synthetic samples with weak supervision
- [scripts/validate_datasets.py](../../scripts/validate_datasets.py): Validate dataset structure and labels
- [scripts/upload_datasets_to_gcs.sh](../../scripts/upload_datasets_to_gcs.sh): Upload to Google Cloud Storage

**External Dataset Download**:
- [scripts/download_iqa_datasets.py](../../scripts/download_iqa_datasets.py): Download LIVE, CSIQ, LIVE Challenge
- [scripts/download_omnidocbench.py](../../scripts/download_omnidocbench.py): Download OmniDocBench (Phase 3)
- [scripts/download_table_datasets.py](../../scripts/download_table_datasets.py): Download TableBank, PubTabNet

**Test Fixtures**:
- [scripts/extract_iqa_fixtures.py](../../scripts/extract_iqa_fixtures.py): Extract LIVE samples for CI/CD (planned Week 3)
- [data/test_fixtures/README.md](../../data/test_fixtures/README.md): Test fixtures documentation

**GCS Integration**:
- [scripts/auth_gcs.sh](../../scripts/auth_gcs.sh): Authenticate with Google Cloud Storage
- [scripts/gcs_helpers.sh](../../scripts/gcs_helpers.sh): GCS upload/download helpers

---

## Consequences

### Positive

1. **Scalable Training**: 50k synthetic samples provide scale needed for CNN training
   - **Impact**: Sufficient data to train MobileNetV3/EfficientNet without overfitting
   - **Metric**: Target mAP > 0.88 with 50k samples vs. < 0.7 with <5k samples

2. **Permissive Licensing**: Synthetic data allows commercial use
   - **Impact**: No licensing restrictions on trained model or deployment
   - **Comparison**: LIVE/CSIQ are research-only (cannot redistribute commercially)

3. **Document-Specific**: TableBank contains real document pages
   - **Impact**: Model learns document characteristics (not natural image IQA)
   - **Advantage**: Better performance on production documents vs. models trained on natural images

4. **Validation Rigor**: External datasets provide objective quality baseline
   - **Impact**: Validate model against human-annotated quality scores (gold standard)
   - **Metric**: Pearson/Spearman correlation > 0.75 with LIVE/CSIQ

5. **CI/CD Integration**: Test fixtures enable automated testing
   - **Impact**: Catch IQA model regressions in CI without 88+ GB dataset downloads
   - **Time Savings**: 30 min CI runtime vs. 2+ hours with full datasets

6. **Reproducibility**: Version-controlled dataset generation
   - **Impact**: Exact dataset can be regenerated with same scripts
   - **Benefit**: Debugging, ablation studies, dataset updates

### Negative

1. **Weak Supervision Noise**: Classical detectors have 10-15% error rate
   - **Impact**: Some training labels are incorrect (noisy labels)
   - **Mitigation**: Use larger dataset to average out noise, validate on external datasets
   - **Risk**: Model may learn detector biases rather than true quality patterns

2. **Synthetic-Real Gap**: Augmented images may not match real defects
   - **Impact**: Model may underperform on authentic camera/scanner artifacts
   - **Mitigation**: Phase 3-4 will incorporate real-world datasets (scanned receipts, FUNSD)
   - **Monitoring**: Track performance on LIVE Challenge (authentic captures)

3. **Natural Image Validation**: LIVE/CSIQ are not document-specific
   - **Impact**: Validation results may not generalize to production documents
   - **Mitigation**: Create document-specific validation set in Phase 4 (production corpus samples)
   - **Note**: LIVE Challenge has some scanned documents but primarily natural scenes

4. **License Restrictions**: External datasets research-only
   - **Impact**: Cannot redistribute LIVE/CSIQ samples or trained model weights commercially
   - **Mitigation**: Use external datasets for validation only, train on permissive synthetic data
   - **Compliance**: Document citation requirements in README

5. **Storage Overhead**: 26 GB total dataset size
   - **Impact**: Local disk space (88 GB including source data), GCS storage costs (~$0.52/month)
   - **Mitigation**: Use GCS Nearline for infrequent access ($0.01/GB/month)

6. **Generation Time**: 8-12 hours to generate 50k samples
   - **Impact**: Cannot iterate quickly on dataset composition
   - **Mitigation**: Generate once, version-control, reuse for multiple experiments

### Neutral

1. **Dataset Format**: JSON labels with image paths (standard format)
2. **Split Ratio**: 70/15/15 train/val/test (standard ML practice)
3. **Class Balance**: Weak supervision creates natural class distribution (some defects rarer than others)

---

## Alternatives Considered

### Alternative 1: Manual Annotation of Real Documents

**Description**: Hire annotators to label 50k+ real document images with quality defects

**Pros**:
- Gold standard quality labels (no weak supervision noise)
- Real-world camera/scanner artifacts (no synthetic gap)
- Document-specific defects (production relevance)

**Cons**:
- **Cost**: $0.10-0.50 per image × 50k = $5k-$25k (prohibitive for Phase 2)
- **Time**: 3-6 months for annotation (delays Phase 2 by quarters)
- **Expertise**: Requires domain expertise to label quality defects accurately
- **Subjectivity**: Inter-annotator agreement may be low for borderline cases

**Rejected**: Cost and time prohibitive for Phase 2. Consider for Phase 4-5 validation.

---

### Alternative 2: Transfer Learning from Natural Image IQA Models

**Description**: Use pre-trained IQA models (BRISQUE, NIQE, KonCept512) trained on LIVE/CSIQ

**Pros**:
- No training data required (use existing model)
- Pre-trained on ground-truth quality scores (LIVE/CSIQ)
- Fast to deploy (no training phase)

**Cons**:
- **Domain Mismatch**: Natural image IQA ≠ document IQA (different defects, lighting, composition)
- **Single-Task**: Most models predict overall quality score, not multi-label defect classification
- **No Customization**: Cannot fine-tune for document-specific defects (skew, perspective)
- **Performance**: Likely lower accuracy than document-specific model

**Rejected**: Domain mismatch makes natural image IQA models unsuitable. Consider as baseline for comparison.

---

### Alternative 3: Active Learning with Small Seed Dataset

**Description**: Start with 1k manually labeled samples, use active learning to expand

**Pros**:
- Lower initial annotation cost ($100-$500 for 1k samples)
- Iterative improvement (annotate high-uncertainty samples)
- Reduces weak supervision noise (human labels where model uncertain)

**Cons**:
- **Complexity**: Requires active learning infrastructure (uncertainty sampling, human-in-the-loop)
- **Time**: Iterative annotation cycles extend timeline (weeks to months)
- **Scale**: Difficult to reach 50k samples cost-effectively
- **Overhead**: Development effort for active learning pipeline

**Deferred**: Consider for Phase 4-5 to improve model on production edge cases. Too complex for Phase 2.

---

### Alternative 4: Crowdsourced Annotation (Amazon MTurk)

**Description**: Use crowdsourcing platform to label images at scale

**Pros**:
- Lower cost than expert annotation ($0.05-0.10 per image × 50k = $2.5k-$5k)
- Faster than hiring annotators (days to weeks)
- Scalable (unlimited annotator pool)

**Cons**:
- **Quality Concerns**: Crowdworkers may not have domain expertise (low inter-annotator agreement)
- **Verification Overhead**: Requires quality control (majority voting, expert review)
- **Time**: Still 2-4 weeks minimum for 50k samples
- **Cost**: Still >$2k (budget constraint for Phase 2)

**Deferred**: Consider for Phase 4 validation dataset. Too costly and slow for Phase 2 training.

---

### Alternative 5: Use Only External Datasets (No Synthetic Data)

**Description**: Train on LIVE + CSIQ + LIVE Challenge (~2.8k images)

**Pros**:
- Ground-truth quality labels (no weak supervision noise)
- Research-standard datasets (comparable results)
- No generation time (download only)

**Cons**:
- **Insufficient Scale**: 2.8k images too small for CNN training (overfitting risk)
- **Natural Images**: Not document-specific (domain mismatch)
- **License Restrictions**: Research-only (cannot commercialize)
- **No Multi-Label**: MOS/DMOS are overall scores, not defect classifications

**Rejected**: Insufficient scale and domain mismatch. Use external datasets for validation only.

---

## Implementation Details

### Phase 2 Timeline

**Week 1** (Current):
- ✅ Generate 50k synthetic training dataset (~8-12 hours)
- ✅ Download external validation datasets (~3-4 hours)
- ✅ Upload datasets to GCS (~1-2 hours)

**Week 2**:
- Implement model architectures (MobileNetV3, EfficientNet)
- Implement training pipeline with early stopping
- Train IQA model on Google Colab Pro (~24-48 hours GPU time)

**Week 3**:
- Evaluate model on validation datasets (LIVE, CSIQ, LIVE Challenge)
- Compute mAP, F1, ECE metrics
- Extract IQA test fixtures from LIVE dataset (5 samples ~2MB)
- Export model to ONNX with INT8 quantization

**Week 4**:
- Implement ML detector (iqa_ml.py) with ONNX Runtime
- Implement ensemble fusion (classical + ML)
- Integration testing and documentation

### Dataset Coverage Matrix

#### Phase 2: Image Quality Assessment (IQA)

| Defect Type | Synthetic (Tier 1) | External (Tier 2) | Test Fixtures (Tier 3) |
|-------------|-------------------|-------------------|------------------------|
| **Blur** | ✅ GaussianBlur augmentation | ✅ LIVE Gaussian blur → **DIQA-5000** | ✅ LIVE blur sample |
| **Noise** | ✅ GaussianNoise augmentation | ✅ LIVE white noise, CSIQ pink noise → **DIQA-5000** | ✅ LIVE noise sample |
| **Skew** | ✅ Rotate augmentation | ❌ Not in LIVE/CSIQ → **DIQA-5000** | ✅ Synthetic rotated sample |
| **Perspective** | ✅ Affine shear augmentation | ❌ Not in LIVE/CSIQ → **DIQA-5000** | ⚠️ Synthetic combined defects |
| **Low Contrast** | ✅ RandomBrightnessContrast | ✅ CSIQ contrast degradation → **DIQA-5000** | ✅ LIVE fastfading sample |
| **Orientation** | ✅ RandomRotate90 augmentation | ❌ Not in LIVE/CSIQ → **DIQA-5000** | ✅ Synthetic rotated sample |

**Phase 2 Coverage Gaps (Addressed by DIQA-5000)**:
- ⚠️ **Natural Images**: LIVE/CSIQ are natural scenes, not documents → **DIQA-5000 solves** (document-specific)
- ⚠️ **Missing Defects**: Skew, perspective, orientation not in LIVE/CSIQ → **DIQA-5000 includes** (document artifacts)
- ⚠️ **Single Score**: MOS/DMOS overall quality only → **DIQA-5000 provides** 3-dimension scores (overall, sharpness, color fidelity)

#### Phase 3: Layout Detection

| Element Type | Training Data (Tier 1) | Benchmarks (Tier 2) | Test Fixtures (Tier 3) |
|-------------|----------------------|---------------------|------------------------|
| **Text Blocks** | ✅ DocSynth-300K (300k samples) | ✅ OmniDocBench | ✅ DocSynth fixtures (5 samples) |
| **Tables** | ✅ PubTables-1M (1M tables) | ✅ OmniDocBench, PubTabNet | ✅ PubTables fixtures (5 samples) |
| **Images/Figures** | ✅ DocSynth-300K | ✅ OmniDocBench | ✅ DocSynth fixtures |
| **Headers/Footers** | ✅ DocSynth-300K | ✅ OmniDocBench | ✅ DocSynth fixtures |
| **Reading Order** | ⚠️ DocSynth-300K (if available) | ✅ ROOR | ⚠️ OPTIONAL (Phase 4-5) |
| **Table Structure** | ✅ PubTables-1M (rows/columns/cells) | ✅ PubTables-1M test split | ✅ PubTables fixtures |

#### Phase 3: Preprocessing

| Preprocessing Task | Training Data (Tier 1) | Benchmarks (Tier 2) | Model |
|-------------------|----------------------|---------------------|-------|
| **Dewarping** | ✅ DocRes pretrained (or SynDocDS) | ✅ AnyPhotoDoc 6300 | **DocRes** (unified) |
| **Shadow Removal** | ✅ DocRes pretrained (or SynDocDS) | ⚠️ No benchmark identified | **DocRes** (unified) |
| **Deblurring** | ✅ DocRes pretrained | ✅ DIQA-5000 (blur subset) | **DocRes** (unified) |
| **Binarization** | ✅ DocRes pretrained | ⚠️ DIBCO (Phase 4) | **DocRes** (unified) |
| **Contrast Enhancement** | ✅ DocRes pretrained | ✅ DIQA-5000 (contrast subset) | **DocRes** (unified) |

**Note**: DocRes is a **unified multi-task model** trained on composite data (not separate datasets per task). SynDocDS optional if fine-tuning required.

#### Phase 3: Specialized Content

| Content Type | Training Data (Tier 1) | Benchmarks (Tier 2) | Test Fixtures (Tier 3) |
|-------------|----------------------|---------------------|------------------------|
| **Handwriting** | ✅ IAM Handwriting (13k samples) | ✅ OmniDocBench (handwriting subset) | ✅ IAM fixtures (10 samples) |
| **Stamps** | ✅ StaVer (400 samples) + DDI-100 (99k samples) | ⚠️ No benchmark identified | ✅ StaVer+DDI fixtures (10 samples) |
| **Hole Punches** | ✅ DDI-100 (99k samples) | ⚠️ No benchmark identified | ✅ DDI fixtures |
| **Noise Artifacts** | ✅ DDI-100 | ⚠️ No benchmark identified | ✅ DDI fixtures |

**Coverage Summary**:
- ✅ **Phase 2 IQA**: Fully covered (DIQA-5000 pending, LIVE/CSIQ fallback)
- ✅ **Phase 3 Layout**: Fully covered (DocSynth-300K, PubTables-1M, OmniDocBench)
- ✅ **Phase 3 Preprocessing**: Fully covered (DocRes unified model, AnyPhotoDoc 6300)
- ⚠️ **Phase 3 Specialized**: Partially covered (handwriting ✅, stamps ⚠️ training only)
- ⚠️ **Reading Order**: Optional scope (ROOR available if approved for Phase 4-5)

### Validation Metrics

**Training Metrics** (50k synthetic dataset):
- **mAP** (multi-label average precision): > 0.88
- **Per-class F1**: > 0.85 for all 6 defect types
- **ECE** (Expected Calibration Error): < 0.1

**Validation Metrics** (external datasets):
- **Pearson Correlation** (predicted vs. ground-truth MOS/DMOS): > 0.75
- **Spearman Correlation** (rank correlation): > 0.75
- **MAE** (Mean Absolute Error): < 0.15 (normalized quality scores)

**Test Fixture Metrics** (CI/CD):
- **Regression Detection**: Alert if correlation drops > 10% from baseline
- **Performance**: CI runtime < 5 min for IQA validation tests

---

## Migration Path

**Phase 2**: Use synthetic training data + external validation
**Phase 3-4**: Augment with real-world datasets (scanned receipts, FUNSD)
**Phase 5**: Active learning on production corpus for continuous improvement

**Dataset Versioning**:
```
datasets/
├── iqa_phase2_v1/          # Current: 50k synthetic + weak supervision
├── iqa_phase2_v2/          # Future: + 10k scanned receipts (real camera captures)
└── iqa_phase4_v1/          # Production: + 5k production corpus samples (active learning)
```

---

## Validation

### Unit Tests

```python
def test_synthetic_dataset_structure():
    """Validate synthetic dataset structure and labels."""
    dataset = load_dataset("datasets/iqa_phase2/train")
    assert len(dataset) == 35000  # 70% of 50k
    assert "labels.json" in dataset.files

    # Check label format
    labels = json.load(dataset.open("labels.json"))
    assert "images" in labels
    assert len(labels["images"]) == 35000

    # Check defect labels
    sample = labels["images"][0]
    assert "defects" in sample
    assert all(defect in sample["defects"] for defect in
               ["blur", "noise", "skew", "perspective", "low_contrast", "orientation"])
```

### Integration Tests

```python
def test_validation_correlation():
    """Test model correlation with LIVE ground-truth."""
    from image_preprocessing_detector.evaluation.iqa_validator import evaluate_iqa

    results = evaluate_iqa(
        model_path="models/phase2_iqa/best_model.pth",
        dataset="data/benchmarks/external_iqa/LIVE"
    )

    assert results["pearson_correlation"] > 0.75
    assert results["spearman_correlation"] > 0.75
```

---

## References

**Datasets (Phase 2 - IQA)**:
- [LIVE IQA Database](https://live.ece.utexas.edu/research/quality/subjective.htm) - Natural image IQA benchmark
- [CSIQ Database](https://qualinet.github.io/databases/image/csiq_image_database/) - Natural image IQA benchmark
- [LIVE Challenge](https://live.ece.utexas.edu/research/ChallengeDB/) - Authentic camera captures
- [TableBank](https://github.com/doc-analysis/TableBank) - 46.38 GB table dataset (Apache-2.0)
- [IQA-Dataset](https://github.com/icbcbicc/IQA-Dataset) - Unified interface for 31 IQA datasets

**Datasets (Phase 3+ - Training Data)**:
- [DocSynth-300K](https://huggingface.co/datasets/juliozhao/DocSynth300K) - 300k synthetic layouts (Apache-2.0)
- [PubTables-1M](https://github.com/microsoft/table-transformer) - 1M real-world tables (Apache-2.0)
- [IAM Handwriting](https://huggingface.co/datasets/Teklia/IAM-line) - 13k handwritten text lines (Academic)
- [StaVer](https://www.kaggle.com/datasets/olegggatttor/stamp-verification) - 400 stamp verification images (CC BY-NC-SA 4.0)
- [DDI-100](https://github.com/jenifferYingyiWu/AI-CU-2018) - 99k document defect images (Research use)
- [SynDocDS](https://arxiv.org/abs/2410.18116) - Synthetic shadow removal dataset (Sensors 2024)

**Datasets (Phase 3+ - Benchmarks)**:
- [DIQA-5000](https://arxiv.org/abs/2509.17012) - Document-specific IQA benchmark (⚠️ Pending release, Sept 2025)
- [AnyPhotoDoc 6300](https://arxiv.org/abs/2410.12189) - Dewarping benchmark (Oct 2025, ⚠️ Contact authors)
- [ROOR](https://github.com/chongzhangFDU/ROOR-Datasets) - Reading order recognition (CC BY 4.0)
- [OmniDocBench](https://huggingface.co/datasets/opendatalab/OmniDocBench) - Multi-domain comprehensive benchmark (Apache-2.0)

**Internal**:
- [docs/guides/dataset-preparation.md](../guides/dataset-preparation.md) - Dataset preparation workflow
- [docs/PHASE2_QUICKSTART.md](../PHASE2_QUICKSTART.md) - Phase 2 quick start guide
- [docs/TESTING_STRATEGY.md](../TESTING_STRATEGY.md) - Testing strategy and test fixtures
- [data/test_fixtures/README.md](../../data/test_fixtures/README.md) - Test fixtures documentation
- ADR-0022: Synthetic Data Generation - Albumentations augmentation strategy
- ADR-0023: Weak Supervision (BRISQUE, NIQE) - Automated labeling approach
- ADR-0024: Active Learning - Future annotation strategy

**Research**:
- Sheikh et al. (2006) - "A statistical evaluation of recent full reference image quality assessment algorithms" (LIVE dataset)
- Larson & Chandler (2010) - "Most apparent distortion: full-reference image quality assessment and the role of strategy" (CSIQ dataset)
- Ghadiyaram & Bovik (2015) - "Massive online crowdsourced study of subjective and objective picture quality" (LIVE Challenge)

---

**Created**: 2025-11-13
**Last Updated**: 2025-01-13 (Phase 3+ dataset expansion)
**Next Review**: Phase 3 Week 1 (validate new dataset downloads)
