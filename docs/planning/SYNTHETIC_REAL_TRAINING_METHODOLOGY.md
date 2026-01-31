# Training Methodology: Synthetic + Real Document IQA

> **Status**: Draft Proposal
> **Created**: 2026-01-30
> **Related**: Phase 7 - ML IQA Model Optimization

## Overview

This document outlines a curriculum learning approach that uses synthetic documents as the foundation and refines on real documents for production-quality IQA models.

## Training Philosophy

**Core Principle**: Synthetic data provides controlled, balanced coverage of degradation types and scripts. Real data provides domain-specific nuances and authentic degradation patterns.

```
Stage 1: Synthetic Foundation (broad coverage, controlled quality)
    ↓
Stage 2: Mixed Training (synthetic + real, 70/30 ratio)
    ↓
Stage 3: Real Document Fine-tuning (domain-specific refinement)
    ↓
Stage 4: Active Learning (production feedback loop)
```

## Stage 1: Synthetic Foundation

### Dataset: 250K Multi-Script Synthetic Documents

**Source**: `data/synthetic_250k/` (currently generating)

**Composition**:

- 27 scripts (Latin, Arabic, CJK, Indic, etc.)
- 8 IQA dimensions (blur, noise, contrast, skew, illumination, compression, bleed_through, overall_quality)
- Hybrid augmentation: Augraphy (document effects) + Albumentations (capture effects)
- Multi-script distribution: 35% single, 45% two-script, 12% three-script, 8% four+

**Training Objective**:

- Learn general degradation patterns across all scripts
- Establish robust feature representations
- Achieve balanced coverage of quality issues

**Training Configuration**:

```python
STAGE1_CONFIG = {
    "epochs": 30,
    "learning_rate": 1e-3,
    "batch_size": 64,
    "warmup_epochs": 3,
    "augmentation": "light",  # Synthetic already degraded
    "label_smoothing": 0.1,
}
```

**Expected Outcome**:

- Model learns general IQA patterns
- Good generalization across scripts
- May underperform on domain-specific documents (forms, tables, handwriting)

## Stage 2: Mixed Training

### Dataset Composition

| Source | Samples | Ratio | Purpose |
|--------|---------|-------|---------|
| Synthetic 250K | 175K | 70% | Maintain broad coverage |
| DIQA-5000 | 3,500 | 1.4% | Real degradation patterns |
| OHR-Bench | 10K | 4% | OCR-specific documents |
| TableBank (sampled) | 30K | 12% | Table documents |
| PubTabNet (sampled) | 25K | 10% | Scientific documents |
| FUNSD+ | 1,113 | 0.4% | Form documents |
| DocLayNet (sampled) | 5K | 2% | Multi-class layout |

**Total**: ~250K samples (70% synthetic, 30% real)

**Training Configuration**:

```python
STAGE2_CONFIG = {
    "epochs": 20,
    "learning_rate": 5e-4,  # Lower LR for fine-tuning
    "batch_size": 32,
    "warmup_epochs": 2,
    "augmentation": "medium",  # Apply to real documents
    "label_smoothing": 0.05,
    "pretrained": "stage1_checkpoint.pt",

    # Curriculum sampling
    "synthetic_weight": 0.7,
    "real_weight": 0.3,
    "hard_negative_mining": True,
}
```

**Sampling Strategy**:

- Weighted sampler to maintain 70/30 ratio per batch
- Hard negative mining: oversample difficult real examples
- Domain-balanced: ensure each real dataset represented per epoch

## Stage 3: Real Document Fine-tuning

### Domain-Specific Models (Optional)

For production deployments with specific document types:

**Option A: Single Fine-tuned Model**

```python
STAGE3_UNIFIED_CONFIG = {
    "epochs": 10,
    "learning_rate": 1e-4,
    "batch_size": 32,
    "dataset": "real_only",  # 75K real samples
    "pretrained": "stage2_checkpoint.pt",
    "freeze_backbone_epochs": 3,  # Freeze early layers initially
}
```

**Option B: Domain-Specific Heads**

```python
STAGE3_MULTIDOMAIN_CONFIG = {
    "epochs": 10,
    "domains": ["scientific", "forms", "tables", "handwriting", "general"],
    "shared_backbone": True,
    "domain_specific_heads": True,
    "learning_rate": 1e-4,
}
```

## Stage 4: Active Learning (Production)

### Feedback Loop Architecture

```
Production Inference
       ↓
[Uncertainty Detection] → High uncertainty samples flagged
       ↓
[Human Review Queue] → Annotator validates/corrects
       ↓
[Retraining Dataset] → Accumulated corrections
       ↓
[Periodic Retraining] → Monthly model updates
```

**Uncertainty Triggers**:

- Prediction confidence < 0.7
- Teacher-student discrepancy > 0.15
- Out-of-distribution detection score > threshold

**Retraining Cadence**:

- Accumulate 1,000+ corrections before retraining
- Monthly retraining with rolling 6-month window
- A/B testing before production deployment

## Label Scheme Alignment

### Synthetic Labels (8 dimensions, continuous 0-1)

| Dimension | Meaning |
|-----------|---------|
| blur | 0=sharp, 1=severely blurred |
| noise | 0=clean, 1=heavy noise |
| contrast | 0=good, 1=poor contrast |
| skew | 0=straight, 1=severely skewed |
| illumination | 0=even, 1=uneven lighting |
| compression | 0=no artifacts, 1=heavy JPEG artifacts |
| bleed_through | 0=none, 1=severe bleed-through |
| overall_quality | 1=perfect, 0=worst |

### Real Document Labels (13 dimensions from Phase 3)

| Dimension | Source | Mapping to Synthetic |
|-----------|--------|---------------------|
| blur | DIQA-5000, generated | Direct (blur) |
| noise | DIQA-5000, generated | Direct (noise) |
| skew | Generated, measured | Direct (skew) |
| illumination | Generated | Direct (illumination) |
| artifacts | DIQA-5000 | Maps to compression |
| dpi | Metadata | Inverse of quality |
| color_mode | Metadata | N/A (categorical) |
| orientation | Metadata | N/A (categorical) |
| combined_defects | Count | Sum of above |
| jpeg_quality | Metadata | Maps to compression |
| layout_type | Classification | N/A (use layout-lite) |
| text_density | Classification | N/A (use layout-lite) |
| language_script | Metadata | N/A (use OpenLID) |

### Harmonization Strategy

```python
def harmonize_labels(synthetic_labels: dict, real_labels: dict) -> dict:
    """Map real document labels to 8-dimension synthetic format."""
    harmonized = {
        "blur": real_labels.get("blur", 0.0),
        "noise": real_labels.get("noise", 0.0),
        "contrast": 1.0 - real_labels.get("contrast_score", 1.0),
        "skew": real_labels.get("skew", 0.0),
        "illumination": real_labels.get("illumination", 0.0),
        "compression": real_labels.get("artifacts", real_labels.get("jpeg_quality_inv", 0.0)),
        "bleed_through": real_labels.get("bleed_through", 0.0),
        "overall_quality": 1.0 - max(
            real_labels.get("blur", 0.0),
            real_labels.get("noise", 0.0),
            real_labels.get("artifacts", 0.0),
        ),
    }
    return harmonized
```

## Dataset Preparation Pipeline

### Step 1: Generate Synthetic Labels

```bash
# Already running on VM
python scripts/generate_dataset_parallel.py --workers 8 --samples 250000
```

### Step 2: Prepare Real Document Labels

```bash
# Extract/generate labels for real datasets
python scripts/prepare_real_document_labels.py \
    --datasets diqa_5000,ohr_bench,tablebank,pubtabnet,funsd_plus \
    --output data/training/real_documents_labeled/ \
    --harmonize-to synthetic
```

### Step 3: Create Mixed Training Manifest

```bash
# Combine synthetic + real with sampling weights
python scripts/create_mixed_training_manifest.py \
    --synthetic data/synthetic_250k/ \
    --real data/training/real_documents_labeled/ \
    --output data/training/mixed_250k_manifest.json \
    --synthetic-ratio 0.7
```

### Step 4: Train with Curriculum

```bash
# Stage 1: Synthetic only
modal run modal/train_curriculum_stage1.py

# Stage 2: Mixed training
modal run modal/train_curriculum_stage2.py --pretrained stage1

# Stage 3: Fine-tuning (optional)
modal run modal/train_curriculum_stage3.py --pretrained stage2
```

## Evaluation Strategy

### Held-out Test Sets (Never Used in Training)

| Test Set | Samples | Purpose |
|----------|---------|---------|
| Synthetic test (10%) | 25K | Generalization on synthetic |
| DIQA-5000 test | 500 | Real degradation accuracy |
| OHR-Bench test | 1K | OCR document quality |
| In-house annotated | 200 | Human-verified ground truth |

### Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| MAE (per dimension) | < 0.10 | Mean absolute error |
| R² (overall quality) | > 0.85 | Correlation with human judgment |
| mAP @ IoU 0.5 | > 0.80 | Multi-label classification |
| Latency (CPU) | < 40ms | ResNet-18 inference |
| Latency (GPU) | < 10ms | ResNet-18 inference |

## Implementation Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Synthetic generation | 24-48h | 250K samples with labels |
| Real document labeling | 1 week | Harmonized labels for 75K real docs |
| Stage 1 training | 4h (GPU) | Synthetic-pretrained model |
| Stage 2 training | 3h (GPU) | Mixed-trained model |
| Evaluation | 1 day | Benchmark results |
| Stage 3 (optional) | 2h (GPU) | Fine-tuned model |

## Open Questions

1. **Label quality for real documents**: Some real datasets lack fine-grained IQA labels. Should we use classical detectors to generate pseudo-labels?

2. **Domain weighting**: Should certain domains (forms, tables) be weighted higher based on production traffic?

3. **Continuous vs discrete labels**: The synthetic pipeline uses continuous (0-1). Should we maintain this or bucket into severity levels?

4. **Distillation timing**: Should we distill to student after Stage 2 or Stage 3?

## References

- ADR-0022: Phase 2 Dataset Strategy
- ADR-0028: IQA Label Scheme
- [docs/model-cards/production/iqa_resnet18_student.md](../model-cards/production/iqa_resnet18_student.md)
- [scripts/generate_100k_iqa_dataset.py](../../scripts/generate_100k_iqa_dataset.py)
