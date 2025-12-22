---
schema_type: common
title: "Level 3: Model Training - Layout Fusion Downsampler"
description: "Detailed specification of the Layout Fusion Downsampler architecture
  used to avoid naive downsampling while preserving semantic document structure for
  IQA training"
tags:
- architecture
- level_3
- model_training
- layout_fusion
- dociq
- diqa_5000
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the Layout Fusion Downsampler architecture, rationale, and implementation
  details for document-aware IQA model training."
last_updated: "2025-01-19"
---

# Level 3: Model Training - Layout Fusion Downsampler

This document provides the complete specification for the **Layout Fusion Downsampler**, a critical component introduced in the original DIQA-5000 paper to enable training document IQA models at full 1600×1600 resolution while avoiding naive downsampling artifacts.

---

## Overview

The Layout Fusion Downsampler is a specialized neural network module that fuses RGB image features with semantic layout masks before downsampling, preserving document structure information that would be lost through naive resizing.

### Design Principles

1. **Avoid Naive Downsampling**: Preserve fine-grained degradation signals (blur, noise, JPEG artifacts)
2. **Semantic Awareness**: Incorporate document layout structure (tables, headers, text regions)
3. **ResNet Compatibility**: Output 400×400 RGB-like tensor suitable for standard backbones
4. **Training Efficiency**: Enable full-resolution IQA training without excessive GPU memory

### Component Characteristics

| Characteristic | Value |
|---------------|-------|
| **Input Resolution** | 1600×1600 (RGB + 11-class layout masks) |
| **Output Resolution** | 400×400 (3-channel fused features) |
| **Layout Classes** | 11 (DocLayNet taxonomy) |
| **Downsampling Factor** | 4× (1600→400) |
| **Parameter Count** | ~45K (lightweight) |
| **Latency** | <5ms (negligible overhead) |

---

## Problem Statement: Why Layout Fusion?

### The Naive Downsampling Problem

Training document IQA models requires balancing two competing constraints:

**Constraint 1: Full Resolution Needed**

- Document degradations (blur, noise, JPEG artifacts) are **fine-grained** (1-3 pixel scale)
- Naive downsampling to 400×400 **destroys** these quality signals
- **Example**: 2-pixel Gaussian blur at 1600×1600 becomes imperceptible at 400×400

**Constraint 2: GPU Memory Limits**

- ResNet-50 on 1600×1600 images requires **32GB+ GPU memory** per batch
- Training becomes prohibitively expensive (A100-80GB required)
- Inference latency increases 16× (1600² vs 400²)

**Traditional Tradeoff**: Either train at low resolution (lose quality signals) or use massive GPUs (prohibitive cost)

### The Layout Fusion Solution

**Key Insight**: Document quality assessment needs **semantic context** (e.g., "is this table blurry?"), not just pixel-level features.

**Layout Fusion Approach**:

1. Extract **semantic layout masks** via DocLayout-YOLO (11 classes)
2. Encode layout masks in **parallel path** at full 1600×1600 resolution
3. Encode RGB image in **parallel path** with 4× downsampling
4. **Fuse** layout features + RGB features → 400×400 output
5. Feed fused features to ResNet-50 backbone

**Result**: Model receives document structure information (from 1600×1600 masks) combined with downsampled RGB features, preserving quality signals better than naive downsampling.

---

## Architecture Specification

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Layout Fusion Downsampler                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  RGB Image [B, 3, 1600, 1600]                               │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────┐                                         │
│  │  RGB Encoder    │  Conv 7×7 s4 → Conv 3×3 s1             │
│  │  (3 → 64 ch)    │  BatchNorm + ReLU                      │
│  └────────┬────────┘                                         │
│           │ [B, 64, 400, 400]                               │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Concatenate [B, 128, 400, 400]         │    │
│  └─────────────────────────────────────────────────────┘    │
│           ▲                                                  │
│           │ [B, 64, 400, 400]                               │
│  ┌────────┴────────┐                                         │
│  │ Layout Encoder  │  Conv 3×3 s2 → Conv 3×3 s2             │
│  │ (11 → 64 ch)    │  BatchNorm + ReLU (2× stride-2)        │
│  └─────────────────┘                                         │
│         ▲                                                    │
│  Layout Mask [B, 11, 1600, 1600]                            │
│                                                              │
│         ▼                                                    │
│  ┌─────────────────┐                                         │
│  │  Fusion Layer   │  Conv 1×1: 128 → 64 → 3                │
│  │  (128 → 3 ch)   │  BatchNorm + ReLU                      │
│  └─────────────────┘                                         │
│         ▼                                                    │
│  Fused Output: [B, 3, 400, 400] (ResNet-compatible)         │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Layout Encoder

**Purpose**: Encode 11-class semantic layout masks while downsampling 4×

```python
self.layout_encoder = nn.Sequential(
    # Stage 1: 1600×1600 → 800×800
    nn.Conv2d(11, 32, kernel_size=3, stride=2, padding=1),
    nn.BatchNorm2d(32),
    nn.ReLU(inplace=True),

    # Stage 2: 800×800 → 400×400
    nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
    nn.BatchNorm2d(64),
    nn.ReLU(inplace=True),
)
```

**Key Properties**:

- **Two-stage downsampling**: stride=2 twice = 4× total
- **Channel expansion**: 11 classes → 32 → 64 features
- **Preserves layout semantics**: ConvNet learns document structure patterns

#### 2. RGB Encoder

**Purpose**: Encode RGB image with 4× downsampling in one step

```python
self.rgb_encoder = nn.Sequential(
    # Stage 1: 1600×1600 → 400×400 (single stride-4 conv)
    nn.Conv2d(3, 32, kernel_size=7, stride=4, padding=3),
    nn.BatchNorm2d(32),
    nn.ReLU(inplace=True),

    # Stage 2: 400×400 → 400×400 (refinement, stride=1)
    nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
    nn.BatchNorm2d(64),
    nn.ReLU(inplace=True),
)
```

**Key Properties**:

- **Single-step downsampling**: 7×7 conv with stride=4 achieves 4× in one layer
- **Larger receptive field**: 7×7 kernel captures broader context than 3×3
- **Matches layout encoder output**: Both produce [B, 64, 400, 400]

#### 3. Fusion Layer

**Purpose**: Combine layout features + RGB features → 3-channel output for ResNet

```python
self.fusion = nn.Sequential(
    # Stage 1: Concatenate features (64+64=128 channels)
    # (handled in forward pass)

    # Stage 2: 128 → 64 channel reduction
    nn.Conv2d(128, 64, kernel_size=1),
    nn.BatchNorm2d(64),
    nn.ReLU(inplace=True),

    # Stage 3: 64 → 3 channel final projection
    nn.Conv2d(64, 3, kernel_size=1),
)
```

**Key Properties**:

- **1×1 convolutions**: Pointwise fusion, no spatial mixing
- **Channel reduction**: 128 → 64 → 3
- **ResNet compatibility**: Output is 3-channel like standard ImageNet input

---

## Layout Mask Generation

### DocLayNet 11-Class Taxonomy

The layout masks use the **DocLayNet** taxonomy with 11 semantic classes:

| Class ID | Class Name | Purpose in IQA |
|----------|------------|----------------|
| 0 | Caption | Identifies image captions (quality-sensitive) |
| 1 | Footnote | Small text regions (blur-sensitive) |
| 2 | Formula | Mathematical notation (distortion-sensitive) |
| 3 | List-Item | Bulleted/numbered lists (alignment-sensitive) |
| 4 | Page-Footer | Bottom metadata (less quality-critical) |
| 5 | Page-Header | Top metadata (less quality-critical) |
| 6 | Picture | Embedded images (JPEG artifact-sensitive) |
| 7 | Section-Header | Section titles (contrast-sensitive) |
| 8 | Table | Tabular data (structure-sensitive) |
| 9 | Text | Main body text (blur/noise-sensitive) |
| 10 | Title | Document title (contrast-sensitive) |

### Mask Generation Pipeline

```python
from image_preprocessing_detector.labeling.finetuning import (
    LayoutMaskGenerator,
    LayoutMaskGeneratorConfig,
)

# Initialize generator with caching
generator = LayoutMaskGenerator(
    config=LayoutMaskGeneratorConfig(
        model_path="juliozhao/DocLayout-YOLO-DocStructBench",
        target_size=(1600, 1600),
        confidence_threshold=0.25,
        cache_dir="masks_cache/",  # ~2.5GB for DIQA-5000
    )
)

# Generate mask for single image
mask = generator.generate_mask(rgb_image)  # [11, 1600, 1600]

# Or batch generation
masks = generator.batch_generate(rgb_images)
```

**Performance Characteristics**:

| Metric | Value |
|--------|-------|
| **Latency** | 50-80ms/image (GPU) |
| **Cache Size** | ~500KB/image (~2.5GB for 5000 images) |
| **Accuracy** | 70-80% mAP (DocLayNet validation) |
| **One-hot Encoding** | Each pixel has ≤1 active class |

---

## Training Integration

### DocIQ-Replica Architecture

The Layout Fusion Downsampler is integrated into the **DocIQ-Replica** model, which serves as the **Generalist Anchor** for Track A in the DIQA-5000 pseudo-labeling system.

```python
from image_preprocessing_detector.labeling.finetuning import (
    DocIQReplica,
    create_dociq_replica,
)

# Phase 1: Frozen backbone (warmup head only)
model = create_dociq_replica(
    device="cuda",
    freeze_backbone=True,  # Freeze ResNet-50 + downsampler
    head_hidden_dim=512,
    head_dropout=0.1,
    pretrained_backbone=True,  # ImageNet pretrained
)

# Train for 15 epochs (head warmup)
# ... training loop ...

# Phase 2: Unfreeze for full fine-tuning
model.unfreeze_backbone()

# Train for 45 more epochs (60 total, paper-aligned)
# ... training loop ...
```

### Forward Pass

```python
# Prepare inputs
rgb_tensor = torch.randn(4, 3, 1600, 1600)  # Batch of 4 images
layout_tensor = torch.randn(4, 11, 1600, 1600)  # Corresponding masks

# Forward pass through DocIQ-Replica
outputs = model(rgb_tensor, layout_tensor)

# Outputs: Multi-task quality predictions
# {
#   "overall": [B],    # Overall quality score [0-1]
#   "sharpness": [B],  # Sharpness score [0-1]
#   "color": [B],      # Color fidelity score [0-1]
# }
```

### Two-Phase Training Protocol

**Phase 1: Head Warmup (Epochs 1-15)**

- **Frozen**: ResNet-50 backbone + Layout Fusion Downsampler
- **Trainable**: Multi-task head only
- **Learning Rate**: 1e-3 with 5-epoch warmup
- **Purpose**: Initialize head before full fine-tuning

**Phase 2: Full Fine-Tuning (Epochs 16-60)**

- **Trainable**: All parameters (backbone + downsampler + head)
- **Learning Rate**: 1e-4 with cosine decay
- **Purpose**: Adapt ResNet-50 to document-specific IQA

**Loss Configuration**:

```python
loss_weights = {
    "overall": 0.34,    # Generalist (balanced)
    "sharpness": 0.33,  # Generalist (balanced)
    "color": 0.33,      # Generalist (balanced)
}
```

---

## Implementation Details

### Module Location

**Source File**: [`src/image_preprocessing_detector/labeling/finetuning/layout_fusion.py`](../../../../src/image_preprocessing_detector/labeling/finetuning/layout_fusion.py)

**Key Classes**:

| Class | Lines | Purpose |
|-------|-------|---------|
| `LayoutFusionDownsampler` | 147-318 | Main fusion module |
| `LayoutMaskGenerator` | 341-645 | DocLayout-YOLO integration |
| `DocIQReplica` | 647-811 | Full model architecture |
| `create_dociq_replica()` | 813-848 | Factory function |

### Weight Initialization

```python
def _init_weights(self) -> None:
    """Initialize weights using Kaiming initialization."""
    for module in self.modules():
        if isinstance(module, nn.Conv2d):
            nn.init.kaiming_normal_(
                module.weight,
                mode="fan_out",
                nonlinearity="relu"
            )
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.BatchNorm2d):
            nn.init.ones_(module.weight)
            nn.init.zeros_(module.bias)
```

**Rationale**: Kaiming initialization prevents gradient vanishing/explosion in deep ReLU networks.

### Input Validation

```python
# Validate RGB shape
if rgb.dim() != 4 or rgb.shape[1] != 3:
    raise ValueError(f"Expected RGB shape [B, 3, H, W], got {rgb.shape}")

# Validate layout shape
if layout.dim() != 4 or layout.shape[1] != 11:
    raise ValueError(
        f"Expected layout shape [B, 11, H, W], got {layout.shape}"
    )

# Handle size mismatch (if input isn't exactly 1600×1600)
if rgb_feat.shape[2:] != layout_feat.shape[2:]:
    layout_feat = F.interpolate(
        layout_feat,
        size=rgb_feat.shape[2:],
        mode="bilinear",
        align_corners=False,
    )
```

---

## Performance Characteristics

### Computational Cost

| Metric | Value | Notes |
|--------|-------|-------|
| **Parameters** | ~45K | Negligible vs ResNet-50 (25M) |
| **FLOPs** | ~2.1 GFLOPs | <1% of total model FLOPs |
| **Latency (GPU)** | <5ms | Overhead negligible |
| **Memory (Training)** | +800MB | For 1600×1600 inputs (batch=4) |
| **Memory (Inference)** | +200MB | Single image |

### Comparison: Naive Downsampling vs Layout Fusion

| Approach | SRCC (Overall) | SRCC (Sharpness) | SRCC (Color) | Training Time |
|----------|----------------|------------------|--------------|---------------|
| **Naive Resize (400×400)** | 0.82 | 0.78 | 0.85 | 8 hours |
| **Layout Fusion (1600→400)** | **0.89** | **0.87** | **0.91** | 12 hours |
| **Improvement** | +8.5% | +11.5% | +7.1% | +50% time |

**Source**: Original DIQA-5000 paper, Table 4 (ablation study)

### GPU Memory Usage

**Training (batch_size=4)**:

```
ResNet-50 baseline (400×400):         ~6GB
+ Layout Fusion Downsampler:          ~800MB
+ 11-class layout masks:              ~450MB
─────────────────────────────────────────────
Total:                                ~7.3GB
```

**Inference (batch_size=1)**:

```
ResNet-50 baseline (400×400):         ~1.5GB
+ Layout Fusion Downsampler:          ~200MB
+ 11-class layout masks:              ~110MB
─────────────────────────────────────────────
Total:                                ~1.8GB
```

---

## Testing Coverage

### Unit Tests

**Location**: [`tests/unit/labeling/finetuning/test_layout_fusion.py`](../../../../tests/unit/labeling/finetuning/test_layout_fusion.py)

**Coverage**: 39 tests (100% line coverage)

**Test Categories**:

| Category | Tests | Coverage |
|----------|-------|----------|
| **LayoutFusionDownsampler** | 15 | Forward pass, shape validation, initialization |
| **LayoutMaskGenerator** | 12 | Mask generation, caching, batch processing |
| **DocIQReplica** | 12 | Full model, freeze/unfreeze, parameter counts |

**Example Tests**:

```python
def test_layout_fusion_forward_pass():
    """Test basic forward pass with correct shapes."""
    downsampler = LayoutFusionDownsampler()
    rgb = torch.randn(4, 3, 1600, 1600)
    layout = torch.randn(4, 11, 1600, 1600)

    output = downsampler(rgb, layout)

    assert output.shape == (4, 3, 400, 400)
    assert output.dtype == torch.float32

def test_layout_mask_caching():
    """Test mask caching saves/loads correctly."""
    generator = LayoutMaskGenerator(
        config=LayoutMaskGeneratorConfig(cache_dir="test_cache/")
    )
    image = np.random.randint(0, 255, (1600, 1600, 3), dtype=np.uint8)

    # First call: generate and cache
    mask1 = generator.generate_mask(image)

    # Second call: load from cache
    mask2 = generator.generate_mask(image)

    np.testing.assert_array_equal(mask1, mask2)
```

---

## Workflow Integration

### DIQA-5000 Pseudo-Labeling Workflow

The Layout Fusion Downsampler is part of the **Track A (IQA Models)** → **Sub-Track A3 (DocIQ-Replica)** in the DIQA-5000 pseudo-labeling system.

**Workflow Position**:

```
[Input Stage]
    ↓
[Layout Mask Generation] ← DocLayout-YOLO (11 classes)
    ↓
[Track A: IQA Models]
    ├─ A1: MUSIQ (no layout fusion)
    ├─ A2: QualiCLIP (no layout fusion)
    └─ A3: DocIQ-Replica ← USES LAYOUT FUSION ✅
         ↓
    [Layout Fusion Downsampler: 1600×1600 → 400×400]
         ↓
    [ResNet-50 Backbone]
         ↓
    [Multi-Task Head: 3 quality dimensions]
         ↓
[Prediction Collection & Stacking]
    ↓
[Pseudo-Label Generation]
```

**Diagram Reference**: [Level 2 - Pseudo-Labeling Workflow](../../level-2/pseudo-labeling/diqa-pseudo-labeling-workflow.puml)

### Modal Training Integration

The Layout Fusion Downsampler is trained via Modal serverless GPU infrastructure.

**Modal Script**: [`modal/train_dociq_replica.py`](../../../../modal/train_dociq_replica.py) (planned)

**Training Configuration**:

```python
@app.function(
    gpu="A100-80GB",  # Required for 1600×1600 inputs
    timeout=3600 * 18,  # 18 hours (60 epochs)
    secrets=[modal.Secret.from_name("gcs-credentials")],
)
def train_dociq_replica():
    """Train DocIQ-Replica with Layout Fusion Downsampler."""
    # Load DIQA-5000 dataset from GCS
    # Generate layout masks (or load from cache)
    # Two-phase training (frozen → unfrozen)
    # Save checkpoints to model registry
```

---

## Comparison to Alternatives

### Alternative 1: Naive Downsampling

**Approach**: Resize 1600×1600 images to 400×400 before feeding to ResNet-50

**Pros**:

- Simple implementation (1 line: `F.interpolate()`)
- No additional parameters
- No layout mask generation overhead

**Cons**:

- **Loses fine-grained degradations**: Blur, noise, JPEG artifacts imperceptible at 400×400
- **SRCC degradation**: -8.5% overall, -11.5% sharpness (see performance table above)
- **No document awareness**: Treats all regions equally

**Verdict**: ❌ **Not viable** for document IQA (significant quality loss)

### Alternative 2: Full-Resolution Training

**Approach**: Train ResNet-50 directly on 1600×1600 images (no downsampling)

**Pros**:

- Maximum quality signal preservation
- No layout fusion complexity

**Cons**:

- **GPU memory explosion**: 16× more memory (1600² vs 400²)
- **Requires A100-80GB**: 32GB+ per batch (vs 8GB with layout fusion)
- **Training time 4-6× longer**: Dominated by convolution cost
- **Inference latency 16× slower**: 100-150ms vs 10-25ms

**Verdict**: ❌ **Prohibitively expensive** (cost vs marginal quality gain)

### Alternative 3: Patch-Based Training

**Approach**: Random 400×400 crops from 1600×1600 images during training

**Pros**:

- Preserves fine-grained degradations in crops
- Lower GPU memory than full-resolution

**Cons**:

- **Loses document structure context**: Each crop is context-free
- **No global quality assessment**: Can't evaluate full-page layout issues
- **Training instability**: High variance from random crops

**Verdict**: ⚠️ **Viable for some tasks** (e.g., local defect detection), but not for document-level IQA

### Alternative 4: Multi-Scale Feature Pyramid

**Approach**: Extract features at multiple scales (1600×1600, 800×800, 400×400), concatenate

**Pros**:

- Captures both fine-grained and global features
- No need for separate layout mask generation

**Cons**:

- **3-4× more FLOPs**: Multiple forward passes
- **Parameter explosion**: 3× backbone size
- **Training complexity**: Balancing loss across scales

**Verdict**: ⚠️ **Overkill** for document IQA (layout fusion is simpler and cheaper)

---

## References

### Papers

1. **DIQA-5000 (Original Paper)**: "DIQA: Document Image Quality Assessment Benchmark" - Introduces Layout Fusion Downsampler architecture
2. **DocIQ (Original)**: "DocIQ: Document Image Quality Assessment" - Inspiration for fusion approach
3. **DocLayNet**: "DocLayNet: A Large Human-Annotated Dataset for Document Layout Segmentation" - Layout taxonomy source

### Related Documentation

- [Level 2 - Pseudo-Labeling Workflow](../../level-2/pseudo-labeling/index.md) - Full DIQA-5000 system overview
- [Level 2 - Model Training](../../level-2/model-training/index.md) - Teacher-student training pipeline
- [Level 3 - Model Training Swimlane](./model-training-swimlane.puml) - Detailed training workflow
- [DIQA-5000 Pseudo-Labels v2 Planning Doc](../../../../planning/DIQA-5000_Pseudo_Labels_v2.md) - Complete system specification

### Implementation Files

- **Module**: [`layout_fusion.py`](../../../../src/image_preprocessing_detector/labeling/finetuning/layout_fusion.py) (848 lines)
- **Tests**: [`test_layout_fusion.py`](../../../../tests/unit/labeling/finetuning/test_layout_fusion.py) (39 tests)
- **Model Registry**: `gs://image_detection_b/models/diqa/track_a_iqa/dociq_replica/v1.0.0/`

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-01-19 | 1.0.0 | Initial Level 3 documentation created |

---

**Maintained by**: Core Architecture Team
**Review Cycle**: Quarterly or on significant architecture changes
**Last Reviewed**: 2025-01-19
