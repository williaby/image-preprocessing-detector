---
schema_type: common
title: "ADR-029: Phase 2 Dataset Selection Strategy for IQA Training and Validation"
description: "Decision to use 50k synthetic samples for training with weak supervision, supplemented by 3 external IQA datasets for validation with ground-truth quality labels"
tags:
  - adr
  - phase_2
  - dataset
  - training
  - validation
  - weak_supervision
  - iqa
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the decision to combine synthetic training data with automated labeling and external validation datasets with ground-truth quality scores to train a robust IQA model while addressing the labeled data scarcity problem."
---

**Status**: ✅ **Accepted**
**Date**: 2025-11-13 (Phase 2 Week 1)
**Deciders**: Byron Williams
**Related**: ADR-0022 (Synthetic Data Generation), ADR-0023 (Weak Supervision), ADR-0024 (Active Learning), ADR-0014 (Classical-ML Hybrid IQA)

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

---

## Decision

**Adopt a hybrid dataset strategy combining synthetic training data with automated weak supervision labeling and external validation datasets with ground-truth quality scores.**

### Three-Tier Dataset Strategy

#### Tier 1: Synthetic Training Data (50k samples, ~18 GB)

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

#### Tier 2: External Validation Data (~5 GB, 2,807 images)

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

#### Tier 3: Test Fixtures (Small samples for CI/CD, ~2 MB)

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

| Defect Type | Synthetic (Tier 1) | External (Tier 2) | Test Fixtures (Tier 3) |
|-------------|-------------------|-------------------|------------------------|
| **Blur** | ✅ GaussianBlur augmentation | ✅ LIVE Gaussian blur | ✅ LIVE blur sample |
| **Noise** | ✅ GaussianNoise augmentation | ✅ LIVE white noise, CSIQ pink noise | ✅ LIVE noise sample |
| **Skew** | ✅ Rotate augmentation | ❌ Not in LIVE/CSIQ | ✅ Synthetic rotated sample |
| **Perspective** | ✅ Affine shear augmentation | ❌ Not in LIVE/CSIQ | ⚠️ Synthetic combined defects |
| **Low Contrast** | ✅ RandomBrightnessContrast | ✅ CSIQ contrast degradation | ✅ LIVE fastfading sample |
| **Orientation** | ✅ RandomRotate90 augmentation | ❌ Not in LIVE/CSIQ | ✅ Synthetic rotated sample |

**Coverage Gaps**:
- ⚠️ **Perspective distortion**: Not in external datasets (camera angle artifact)
- ⚠️ **Skew**: Not in external datasets (document rotation artifact)
- ⚠️ **Real Camera Captures**: Limited in synthetic data (Phase 3-4: add scanned receipts, FUNSD)

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

**Datasets**:
- [LIVE IQA Database](https://live.ece.utexas.edu/research/quality/subjective.htm)
- [CSIQ Database](https://qualinet.github.io/databases/image/csiq_image_database/)
- [LIVE Challenge](https://live.ece.utexas.edu/research/ChallengeDB/)
- [TableBank](https://github.com/doc-analysis/TableBank)
- [IQA-Dataset](https://github.com/icbcbicc/IQA-Dataset) - Unified interface for 31 IQA datasets

**Internal**:
- [docs/DATASET_PREPARATION.md](../DATASET_PREPARATION.md) - Dataset preparation workflow
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
**Last Updated**: 2025-11-13
**Next Review**: Phase 2 Week 3 (after training complete)
