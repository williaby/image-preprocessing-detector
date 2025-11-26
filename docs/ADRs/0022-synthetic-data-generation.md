---
schema_type: common
title: "ADR-022: Synthetic Data Generation with Albumentations for ML Training"
description: "Use Albumentations for synthetic data generation to augment training
  dataset from 10k to 50k images"
tags:
- adr
- synthetic_data
- augmentation
- albumentations
- training
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to use Albumentations for synthetic data generation
  to expand training dataset size."
---


**Status**: Accepted
**Date**: 2025-01-15
**Deciders**: Byron Williams
**Related**:

- [PROJECT_PLAN.md Phase 2](../../PROJECT_PLAN.md#phase-2-ml-for-image-quality-assessment-3-4-weeks)
- [ADR-006: Synthetic Validation Dataset Strategy](0006-synthetic-validation-dataset-strategy.md)
- [ADR-014: Classical CV + ML Hybrid for IQA](0014-classical-ml-hybrid-iqa.md)

## Context

Phase 2 requires training a multi-label IQA CNN to detect image quality issues (noise, blur, perspective, orientation). Training deep learning models requires large datasets (10k-100k+ images), but manual annotation is expensive ($0.10-1.00 per image = $1k-100k).

### Training Data Requirements

**Base Dataset**: 10k clean document images from DocLayNet
**Augmentation Target**: 50k total images (5× augmentation)
**Quality Issues to Generate**:

- Noise (Gaussian, salt-and-pepper, speckle)
- Blur (Gaussian, motion blur)
- Low contrast (histogram manipulation)
- Skew/rotation (-45° to +45°)
- Perspective distortion
- Orientation (90°, 180°, 270° rotations)

### Dataset Cost Analysis

**Manual Annotation**:

- 50k images × $0.50/image = $25,000
- Time: ~500 hours (100 images/hour)
- Quality variance: High

**Synthetic Generation**:

- Infrastructure: ~$500 (GPU compute)
- Time: ~40 hours (automated)
- Quality variance: Low (deterministic)
- Cost savings: **$24,500 (98% reduction)**

## Decision

**Use Albumentations library for synthetic data generation via deterministic augmentation pipelines.**

### Augmentation Pipeline Strategy

**Strategy 1: Single-Issue Augmentation** (80% of data)

- Apply one quality issue per image
- Clean ground truth labels
- Training: Simplifies multi-label learning

**Strategy 2: Multi-Issue Augmentation** (20% of data)

- Apply 2-3 quality issues per image
- Realistic edge cases
- Training: Improves robustness

### Albumentations Pipeline Implementation

```python
import albumentations as A

# Single-issue pipeline (noise only)
noise_aug = A.Compose([
    A.OneOf([
        A.GaussNoise(var_limit=(10.0, 50.0), p=1.0),
        A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
        A.MultiplicativeNoise(multiplier=(0.9, 1.1), p=1.0),
    ], p=1.0)
])

# Single-issue pipeline (blur only)
blur_aug = A.Compose([
    A.OneOf([
        A.GaussianBlur(blur_limit=(3, 7), p=1.0),
        A.MotionBlur(blur_limit=7, p=1.0),
        A.MedianBlur(blur_limit=5, p=1.0),
    ], p=1.0)
])

# Multi-issue pipeline (realistic combination)
multi_aug = A.Compose([
    A.Rotate(limit=10, p=0.5),                       # Skew
    A.GaussianBlur(blur_limit=(3, 5), p=0.3),        # Blur
    A.RandomBrightnessContrast(p=0.3),               # Contrast
    A.GaussNoise(var_limit=(10, 30), p=0.2),         # Noise
])
```

### Augmentation Distribution

| Quality Issue | Augmentation Method | Count | Notes |
|---------------|-------------------|-------|-------|
| Noise | GaussNoise, ISONoise, Multiplicative | 8,000 | 80% single-issue |
| Blur | GaussianBlur, MotionBlur, Median | 8,000 | 80% single-issue |
| Skew | Rotate (-45° to +45°) | 8,000 | 80% single-issue |
| Low Contrast | RandomBrightnessContrast | 8,000 | 80% single-issue |
| Perspective | Perspective distortion | 6,000 | Harder to generate |
| Orientation | Rotate (90°, 180°, 270°) | 2,000 | Simpler augmentation |
| **Multi-Issue** | Combined pipeline | 10,000 | 20% multi-issue |
| **Total** | All pipelines | **50,000** | 5× augmentation |

## Consequences

### Positive

1. **Cost Savings**: $24,500 savings vs manual annotation (98% reduction)
2. **Perfect Ground Truth**: Deterministic augmentation = perfect labels
3. **Scalability**: Generate unlimited training data
4. **Control**: Precise control over issue severity and distribution
5. **Consistency**: Reproducible augmentations with fixed seeds
6. **Fast Iteration**: Re-generate dataset in hours vs weeks

### Negative

1. **Synthetic Bias**: Augmentations may not perfectly match real-world issues
2. **Distribution Shift**: Need real-world validation for calibration (ADR-011)
3. **Complexity**: Pipeline configuration requires tuning
4. **Compute Cost**: GPU compute for augmentation (~$500)

### Neutral

1. **Dataset Size**: 50k images = ~200GB storage
2. **Generation Time**: ~40 hours on GPU cluster
3. **DVC Versioning**: Large datasets require DVC for version control

## Alternatives Considered

### Alternative 1: Manual Annotation Only

**Approach**: Manually annotate all 50k images

**Advantages**:

- Real-world ground truth
- No synthetic bias
- Captures authentic quality issues

**Disadvantages**:

- Expensive ($25,000)
- Slow (500 hours)
- Quality variance (inter-annotator disagreement)
- Cannot scale beyond budget

**Why Rejected**: Cost and time prohibitive

### Alternative 2: GAN-Based Synthetic Data

**Approach**: Train StyleGAN or similar to generate synthetic degraded documents

**Advantages**:

- More realistic than deterministic augmentation
- Unlimited data generation

**Disadvantages**:

- Requires training GAN first (weeks of work)
- No ground truth control (harder to label)
- Computational cost (100× higher than Albumentations)
- Complexity (debugging GAN training)

**Why Rejected**: Overkill for problem, Albumentations sufficient

### Alternative 3: Weak Supervision + Active Learning

**Approach**: Use BRISQUE/NIQE for automated labeling + selective human annotation

**Advantages**:

- Real-world images
- Scalable labeling
- Combines automated + human expertise

**Disadvantages**:

- Noisy labels from BRISQUE/NIQE
- Requires active learning infrastructure
- Still needs manual annotation for ambiguous cases

**Why Rejected**: Complementary strategy (ADR-023, ADR-024), not replacement

## Implementation

### Augmentation Pipeline Configuration

**File**: `src/training/data_augmentation.py`

```python
import albumentations as A
from albumentations.pytorch import ToTensorV2

class IQAAugmentationPipeline:
    """Albumentations pipeline for IQA training data generation."""

    def __init__(self, augmentation_type: str = "single_issue"):
        self.augmentation_type = augmentation_type
        self.pipelines = self._build_pipelines()

    def _build_pipelines(self):
        """Build augmentation pipelines for each quality issue."""
        pipelines = {}

        # Noise augmentation
        pipelines["noise"] = A.Compose([
            A.OneOf([
                A.GaussNoise(var_limit=(10.0, 50.0), p=1.0),
                A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
                A.MultiplicativeNoise(multiplier=(0.9, 1.1), p=1.0),
            ], p=1.0),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ])

        # Blur augmentation
        pipelines["blur"] = A.Compose([
            A.OneOf([
                A.GaussianBlur(blur_limit=(3, 7), p=1.0),
                A.MotionBlur(blur_limit=7, p=1.0),
                A.MedianBlur(blur_limit=5, p=1.0),
            ], p=1.0),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ])

        # Skew augmentation
        pipelines["skew"] = A.Compose([
            A.Rotate(limit=45, border_mode=cv2.BORDER_CONSTANT, value=255, p=1.0),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ])

        # Contrast augmentation
        pipelines["low_contrast"] = A.Compose([
            A.RandomBrightnessContrast(
                brightness_limit=(-0.1, 0.0),
                contrast_limit=(-0.3, -0.1),
                p=1.0
            ),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ])

        # Perspective augmentation
        pipelines["perspective"] = A.Compose([
            A.Perspective(scale=(0.05, 0.1), p=1.0),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ])

        # Orientation augmentation
        pipelines["orientation"] = A.Compose([
            A.RandomRotate90(p=1.0),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ])

        # Multi-issue augmentation
        pipelines["multi_issue"] = A.Compose([
            A.Rotate(limit=10, border_mode=cv2.BORDER_CONSTANT, value=255, p=0.5),
            A.GaussianBlur(blur_limit=(3, 5), p=0.3),
            A.RandomBrightnessContrast(p=0.3),
            A.GaussNoise(var_limit=(10, 30), p=0.2),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ])

        return pipelines

    def augment(self, image: np.ndarray, issue_type: str) -> Tuple[torch.Tensor, Dict]:
        """Apply augmentation and return tensor + metadata."""
        pipeline = self.pipelines[issue_type]
        augmented = pipeline(image=image)

        metadata = {
            "augmentation_type": self.augmentation_type,
            "issue_type": issue_type,
            "parameters": pipeline.get_params(),
        }

        return augmented["image"], metadata
```

### Dataset Generation Script

**File**: `scripts/generate_synthetic_dataset.py`

```python
import albumentations as A
from pathlib import Path
import json

def generate_synthetic_dataset(
    input_dir: Path,
    output_dir: Path,
    augmentation_config: Dict,
    num_augmentations: int = 5
):
    """Generate synthetic dataset from clean images."""

    augmentor = IQAAugmentationPipeline()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load base images
    base_images = list(input_dir.glob("*.jpg"))
    print(f"Found {len(base_images)} base images")

    # Generate augmented dataset
    for idx, img_path in enumerate(base_images):
        image = cv2.imread(str(img_path))

        for aug_idx in range(num_augmentations):
            # Select augmentation type
            issue_type = select_augmentation_type(augmentation_config)

            # Apply augmentation
            augmented, metadata = augmentor.augment(image, issue_type)

            # Save augmented image
            output_path = output_dir / f"{img_path.stem}_{issue_type}_{aug_idx}.jpg"
            save_image(augmented, output_path)

            # Save metadata
            meta_path = output_dir / f"{img_path.stem}_{issue_type}_{aug_idx}.json"
            save_json(metadata, meta_path)

    print(f"Generated {len(base_images) * num_augmentations} augmented images")
```

## Dataset Management

### DVC Versioning

```bash
# Initialize DVC for large dataset tracking
dvc init
dvc remote add -d storage s3://image-preprocessing/datasets

# Track synthetic dataset
dvc add data/training/synthetic_iqa_50k.tar.gz
git add data/training/synthetic_iqa_50k.tar.gz.dvc .gitignore
git commit -m "Add synthetic IQA training dataset (50k images)"

# Push to remote storage
dvc push
```

### Dataset Structure

```text
data/training/synthetic_iqa_50k/
├── noise/              # 8,000 images
│   ├── img_0001_gaussian_noise.jpg
│   ├── img_0001_gaussian_noise.json  # Metadata
│   └── ...
├── blur/               # 8,000 images
├── skew/               # 8,000 images
├── low_contrast/       # 8,000 images
├── perspective/        # 6,000 images
├── orientation/        # 2,000 images
├── multi_issue/        # 10,000 images
└── metadata.json       # Dataset-level metadata
```text

## Performance Impact

**Generation Time**:

- Single augmentation: ~100ms (CPU)
- 50k augmentations: ~1.4 hours (4× GPU parallel)
- Total pipeline: ~40 hours (including I/O)

**Storage**:

- 50k images × 4MB/image = ~200GB
- Compressed: ~50GB (4× compression)

**Compute Cost**:

- GPU hours: 40 hours × $1.50/hr = $60
- Total infrastructure: ~$500 (including storage)

## References

- [Albumentations Documentation](https://albumentations.ai/docs/)
- [ADR-006: Synthetic Validation Dataset Strategy](0006-synthetic-validation-dataset-strategy.md)
- [ADR-023: Weak Supervision with BRISQUE/NIQE](0023-weak-supervision-brisque-niqe.md)
- [ADR-024: Active Learning for Annotation Efficiency](0024-active-learning-annotation.md)
- [PROJECT_PLAN.md Phase 2](../../PROJECT_PLAN.md#phase-2-ml-for-image-quality-assessment-3-4-weeks)

## Lessons Learned

1. **Synthetic Works**: Albumentations generates realistic degradations
2. **Cost Effective**: 98% cost savings vs manual annotation
3. **Perfect Labels**: Deterministic augmentation = clean ground truth
4. **Combine with Real**: Use synthetic for training, real-world for validation (ADR-011)
