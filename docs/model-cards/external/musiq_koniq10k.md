---
owner: docs-team
purpose: 'Documentation for Model Card: MUSIQ KonIQ-10k.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: MUSIQ KonIQ-10k'
---

---

## YAML Frontmatter (for HuggingFace)

```yaml
---
license: apache-2.0
language: en
tags:
  - image-quality-assessment
  - multi-scale-transformer
  - koniq-10k
  - no-reference-iqa
datasets:
  - koniq-10k
metrics:
  - srcc
  - plcc
pipeline_tag: image-classification
model-index:
  - name: musiq_koniq10k
    results:
      - task:
          type: image-quality-assessment
        dataset:
          name: KonIQ-10k
          type: koniq-10k
        metrics:
          - name: SRCC
            type: srcc
            value: 0.916
          - name: PLCC
            type: plcc
            value: 0.928
---
```

---

## Model Summary

> MUSIQ (Multi-scale Image Quality Transformer) for no-reference image quality assessment, pre-trained on KonIQ-10k. Uses multi-scale patch encoding with spatial hash embeddings to handle variable-resolution inputs natively without resize. Outputs a single Mean Opinion Score (MOS) in [0,1] representing perceptual quality.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `musiq_koniq10k` |
| **Project** | Prepare-Doc |
| **Phase** | External Pretrained (DIQA Base) |
| **Status** | `pretrained` |
| **Priority** | P0 (Critical) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | MUSIQ (Multi-Scale Image Quality Transformer) |
| **Parameters** | ~27M |
| **Precision** | FP32 |
| **Input Size** | Variable (multi-scale, native resolution) |
| **Output Format** | Single MOS score [0,1] |
| **Output Type** | regression |
| **Export Formats** | PyTorch (via PyIQA) |
| **Feature Dimension** | 384 (CLS token) |

### Architecture Details

```text
MUSIQ Architecture:
├── conv_root: StdConv(3 → 64, 7x7, stride=2)
├── gn_root: GroupNorm(32, 64)
├── root_pool: MaxPool2d(3x3, stride=2)
├── block1: Bottleneck(64 → 256)
├── embedding: Linear(resnet_token_dim * 4 * patch_size^2 → 384)
├── transformer_encoder: TransformerEncoder(hidden_size=384)
│   ├── Multi-head self-attention (6 layers, 6 heads)
│   ├── Spatial hash embeddings (learnable)
│   └── Scale embeddings (for multi-scale processing)
├── [CLS] token aggregation: index 0 → (batch, 384)
└── head: Linear(384 → 1) → MOS score
```

### Multi-Scale Processing

MUSIQ handles variable input resolutions through:

1. **Multi-scale patch extraction**: Images processed at multiple scales
2. **Spatial hash embeddings**: Position encoding without fixed grid
3. **Scale embeddings**: Distinguish patches from different scales
4. **Native resolution**: No resize required (preserves quality artifacts)

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | No-Reference Image Quality Assessment |
| **Role in Pipeline** | Base model for DIQA sharpness specialist fine-tuning |
| **Upstream Dependencies** | None (pretrained external) |
| **Downstream Consumers** | `diqa_musiq_sharpness` (fine-tuned version) |

### Intended Use

- **Primary**: Base model for fine-tuning on DIQA-5000 sharpness dimension
- **Secondary**: General natural image quality assessment
- **Out of Scope**: Document-specific quality (requires fine-tuning)

### MUSIQ Advantages for DIQA

| Feature | Benefit for Sharpness Detection |
|---------|----------------------------------|
| Multi-scale processing | Detects blur at multiple scales |
| ViT-based backbone | Strong local + global quality perception |
| Pre-trained on IQA | Transfer learning head start |
| No resize requirement | Preserves blur/sharpness artifacts |

---

## 3. Training Details (Original)

| Field | Value |
|-------|-------|
| **Dataset** | KonIQ-10k (10,073 images) |
| **Train/Val/Test Split** | 80/10/10 |
| **Original Output** | Single MOS score [0,1] |
| **Loss Function** | MSE |
| **GPU** | V100 |
| **Original Paper** | ICCV 2021 |

### KonIQ-10k Dataset

| Aspect | Details |
|--------|---------|
| **Size** | 10,073 images |
| **Resolution** | 1024x768 px |
| **Quality Labels** | MOS from 1,459 crowd workers |
| **Quality Range** | 1-5 MOS (normalized to 0-1) |
| **Distortions** | Natural distortions (blur, noise, compression) |

---

## 4. Preprocessing Requirements

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | `[batch, 3, H, W]` (variable H, W) |
| **Color Space** | RGB |
| **Value Range** | [0, 1] |
| **Channel Order** | CHW (PyTorch) |

### Normalization

```python
# Required preprocessing values (ImageNet statistics)
mean = [0.485, 0.456, 0.406]
std = [0.229, 0.224, 0.225]
```

### Resize Strategy

| Field | Value |
|-------|-------|
| **Method** | None required (native resolution) |
| **Recommended Max** | 1024px longer edge |
| **Notes** | Multi-scale patches handle any size |

### Complete Transform Pipeline

```python
from torchvision import transforms
from PIL import Image

# MUSIQ accepts variable resolutions - no resize needed
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

image = Image.open("document.png").convert("RGB")
input_tensor = transform(image).unsqueeze(0)
# Shape: [1, 3, H, W] where H, W are original dimensions
```

---

## 5. Performance Metrics

### 5.1 Original Benchmark (KonIQ-10k)

| Metric | Value | Notes |
|--------|-------|-------|
| SRCC | 0.916 | Spearman correlation |
| PLCC | 0.928 | Pearson correlation |

### 5.2 Cross-Dataset Performance (from paper)

| Dataset | SRCC | PLCC | Notes |
|---------|------|------|-------|
| KonIQ-10k | 0.916 | 0.928 | Primary benchmark |
| LIVE-Challenge | 0.893 | 0.902 | In-the-wild |
| SPAQ | 0.909 | 0.917 | Smartphone photos |
| PaQ-2-PiQ | 0.892 | 0.903 | Patch-level quality |

### 5.3 DIQA-5000 Baseline (Pre-Fine-Tuning)

| Dimension | SRCC | Notes |
|-----------|------|-------|
| Overall | 0.116 | Weak on documents |
| Sharpness | 0.213 | Best natural alignment |
| Color | 0.112 | Domain gap |

**Analysis**: MUSIQ shows reasonable sharpness correlation (0.213 SRCC) out-of-box due to KonIQ-10k's blur/noise focus. Fine-tuning on DIQA-5000 expected to improve to 0.88+ SRCC.

### 5.4 Inference Performance

| Device | Latency | Notes |
|--------|---------|-------|
| T4 GPU | ~24ms | PyIQA default |
| A10 GPU | ~18ms | Faster CUDA cores |
| CPU | ~150ms | Not recommended |

---

## 6. Limitations & Known Issues

### Limitations

- **Domain Gap**: Trained on natural photos, not documents
- **Single Output**: Original model outputs single MOS (not per-dimension)
- **Computational Cost**: Transformer + multi-scale more expensive than CNN
- **No Uncertainty**: Original model has no calibration mechanism

### Known Failure Modes

- **Document Images**: Weak on scanned documents (requires fine-tuning)
- **Extreme Resolutions**: Very large images (>4K) may exceed memory
- **Moiré Patterns**: Not specifically trained on screen captures

### Why Fine-Tuning is Required

| Issue | Solution |
|-------|----------|
| Single MOS output | Add multi-task head (overall, sharpness, color) |
| Document domain gap | Fine-tune on DIQA-5000 |
| No calibration | Add focal calibration loss |

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Base Model** | None (original MUSIQ) |
| **Original Paper** | "MUSIQ: Multi-scale Image Quality Transformer" (ICCV 2021) |
| **Authors** | Ke et al. (Google Research) |
| **Derived Models** | `diqa_musiq_sharpness_v1.0.0` (planned) |
| **Required Libraries** | PyIQA >= 0.1.12, PyTorch >= 2.0 |

### Dependency Versions

```text
pyiqa>=0.1.12
torch>=2.0.0
torchvision>=0.15.0
timm>=0.9.0
einops>=0.7.0
```

---

## 8. Files & Artifacts

### PyIQA Installation (Recommended)

MUSIQ is loaded automatically via PyIQA - no manual download required:

```python
import pyiqa
musiq = pyiqa.create_metric("musiq", device="cuda")
```

### Manual Files (Optional)

| File | Description | Size | Source |
|------|-------------|------|--------|
| `musiq_koniq_ckpt.pth` | PyIQA checkpoint | ~108MB | Auto-downloaded |

### Storage Locations

| Environment | Path | Notes |
|-------------|------|-------|
| **PyTorch Cache** | `~/.cache/pyiqa/` | Auto-downloaded on first use |
| **E: Drive** | `E:/image_detection/05_models/external/musiq_koniq10k/` | Offline backup (if needed) |
| **GCS** | `gs://image_detection_b/models/external/musiq_koniq10k/` | Future backup |

---

## 9. Inference Example

### PyIQA Inference (Original)

```python
import pyiqa
import torch
from PIL import Image
from torchvision import transforms

# Load model via PyIQA (recommended)
musiq = pyiqa.create_metric("musiq", device="cuda")

# Prepare image
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

image = Image.open("image.png").convert("RGB")
input_tensor = transform(image).unsqueeze(0).cuda()

# Inference - returns MOS score [0, 1]
with torch.no_grad():
    score = musiq(input_tensor)

print(f"Quality Score: {score.item():.4f}")
# Higher score = better quality
```

### Feature Extraction (For Fine-Tuning)

```python
import pyiqa
import torch

# Load MUSIQ and wrap for feature extraction
base_musiq = pyiqa.create_metric("musiq", device="cuda")

# Access internal model
inner_model = base_musiq.net

# Features are extracted at CLS token (384-dim)
# See musiq_wrapper.py for MUSIQMultiTask implementation
```

### Using MUSIQMultiTask Wrapper

```python
from image_preprocessing_detector.labeling.finetuning.musiq_wrapper import (
    create_musiq_multitask,
)

# Create multi-task version for fine-tuning
model = create_musiq_multitask(
    device="cuda",
    freeze_backbone=True,  # Phase 1
    head_hidden_dim=256,
    head_dropout=0.1,
)

# Forward pass returns 3 dimensions
with torch.no_grad():
    outputs = model(input_tensor)

print(f"Overall: {outputs['overall'].item():.4f}")
print(f"Sharpness: {outputs['sharpness'].item():.4f}")
print(f"Color: {outputs['color'].item():.4f}")
```

---

## 10. Usage in Prepare-Doc

### Role in DIQA Pipeline

```text
External Pretrained Models
─────────────────────────
    ResNet-50 ImageNet1K V2  ←  Backbone for IQA models
    [MUSIQ KonIQ-10k]        ←  THIS MODEL (base for sharpness)
        ↓
    Fine-tune on DIQA-5000
        ↓
    diqa_musiq_sharpness     ←  Production specialist
        ↓
    DIQA Stacker Ensemble    ←  Final pseudo-labels
```

### Fine-Tuning Protocol

| Phase | Description | Config |
|-------|-------------|--------|
| Phase 1 | Head warmup (frozen backbone) | 10 epochs, LR=1e-3 |
| Phase 2 | Full fine-tuning | 20 epochs, backbone LR=1e-5, head LR=1e-4 |

### Expected Improvement After Fine-Tuning

| Metric | Before | After (Target) |
|--------|--------|----------------|
| SRCC (sharpness) | 0.213 | > 0.88 |
| SRCC (overall) | 0.116 | > 0.75 |
| SRCC (color) | 0.112 | > 0.70 |
| ECE | N/A | < 0.08 |

---

## 11. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0.0 | 2025-12-18 | Initial model card | Prepare-Doc Team |

---

## 12. Citation

### MUSIQ Paper

```bibtex
@inproceedings{ke2021musiq,
  title={MUSIQ: Multi-scale Image Quality Transformer},
  author={Ke, Junjie and Wang, Qifei and Wang, Yilin and Milanfar, Peyman and Yang, Feng},
  booktitle={Proceedings of the IEEE/CVF International Conference on Computer Vision},
  pages={5148--5157},
  year={2021}
}
```

### KonIQ-10k Dataset

```bibtex
@article{hosu2020koniq,
  title={KonIQ-10k: An ecologically valid database for deep learning of blind image quality assessment},
  author={Hosu, Vlad and Lin, Hanhe and Sziranyi, Tamas and Saupe, Dietmar},
  journal={IEEE Transactions on Image Processing},
  volume={29},
  pages={4041--4056},
  year={2020}
}
```

### PyIQA Library

```bibtex
@misc{pyiqa,
  title={PyIQA: Python Image Quality Assessment},
  author={Chaofeng Chen},
  year={2022},
  howpublished={\url{https://github.com/chaofengc/IQA-PyTorch}}
}
```

---

## 13. Contact & Ownership

| Role | Contact |
|------|---------|
| **Model Owner** | Google Research (original) |
| **PyIQA Maintainer** | Chaofeng Chen |
| **Prepare-Doc Integration** | Core Team |
| **Review Cadence** | On fine-tuning milestones |

---

## Production Readiness Checklist

### Documentation

- [x] Model Summary written
- [x] All required sections completed
- [x] Limitations documented
- [x] Inference example tested

### Integration

- [x] PyIQA loading verified
- [x] MUSIQMultiTask wrapper implemented
- [x] Fine-tuning config created
- [ ] DIQA-5000 fine-tuning completed

### Artifacts

- [x] Available via PyIQA (auto-download)
- [ ] E: Drive backup (optional)
- [ ] GCS backup (optional)
- [ ] ONNX export (after fine-tuning)

### Derived Models

- [ ] `diqa_musiq_sharpness_v1.0.0` trained
- [ ] Production deployment validated
- [ ] Stacker ensemble integrated
