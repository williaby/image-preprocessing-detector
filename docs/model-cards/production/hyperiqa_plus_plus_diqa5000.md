---
owner: docs-team
purpose: 'Documentation for Model Card: HyperIQA++ DIQA-5000.'
schema_type: common
status: published
tags:
- iqa
- production
title: 'Model Card: HyperIQA++ DIQA-5000'
---

## Model Summary

> HyperIQA-based model enhanced with 7 DocIQ and VQualA 2025 innovations for document image quality assessment. Trained on DIQA-5000 dataset with two-phase training protocol. Predicts quality scores for overall quality, sharpness, and color fidelity dimensions with soft label distributions.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `hyperiqa_plus_plus_diqa5000_v1.0.0` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | VQualA 2025 Enhancement |
| **Status** | `trained` |
| **Priority** | P0 (Critical) |
| **Last Updated** | 2026-01-14 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | HyperIQA + SpatialAttention + SoftLabelHeads |
| **Parameters** | ~138M |
| **Precision** | FP32 (training) |
| **Input Size** | 1600x1600x3 |
| **Output Format** | 3 quality dimensions (overall, sharpness, color) |
| **Output Type** | Regression + Soft Label Distribution |
| **Export Formats** | PyTorch |
| **Base Model** | PyIQA HyperIQA (pretrained) |

### Architecture Components

| Component | Description |
|-----------|-------------|
| **Backbone** | HyperIQA base_model (ResNet-50 FeatureListNet) |
| **HyperNet** | Content-adaptive feature processing |
| **Spatial Attention** | Layout-aware region weighting (DocIQ-Simplified) |
| **Soft Label Heads** | 3x heads with 10-bin distributions (DeQA-Doc innovation) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Document Image Quality Assessment |
| **Role in Pipeline** | High-accuracy IQA for DIQA-5000 benchmark |
| **Upstream Dependencies** | Image Ingestion |
| **Downstream Consumers** | DQS Calculator, Routing Engine |

### Intended Use

- **Primary**: Document IQA with soft label uncertainty estimation
- **Secondary**: Multi-dimensional quality assessment (overall, sharpness, color)
- **Out of Scope**: Real-time inference (1600x1600 input size is compute-intensive)

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Dataset** | DIQA-5000 |
| **Train/Val/Test Split** | 80/10/10 |
| **Total Epochs** | 20 (early stopping from 60) |
| **Phase 1 Epochs** | 10 (frozen backbone, head warmup) |
| **Phase 2 Epochs** | 10 (full fine-tuning) |
| **Phase 1 Batch Size** | 16 |
| **Phase 2 Batch Size** | 2 (effective 12 with grad accum) |
| **Gradient Accumulation** | 6 steps |
| **Phase 1 Learning Rate** | 2e-4 |
| **Phase 2 Learning Rates** | 2e-5 (backbone), 1e-4 (hypernet), 2e-4 (heads) |
| **LR Schedule** | Step decay (γ=0.6, step=10) |
| **Optimizer** | AdamW |
| **Weight Decay** | 1e-4 |
| **Gradient Clipping** | 1.0 |
| **Loss Function** | KL Divergence + NormInNormLoss |
| **Multi-Task Optimization** | PCGrad (Gradient Surgery) |
| **Early Stopping** | Patience 10 on VQualA score |
| **GPU** | Modal A10G (24GB) |
| **Training Date** | 2026-01-13 |
| **Training Script** | `modal/train_hyperiqa_plus_plus.py` |

### Training Innovations (VQualA 2025)

| Innovation | Source | Description |
|------------|--------|-------------|
| High-resolution input | DocIQ | 1600x1600 for fine detail |
| Soft label distribution | DeQA-Doc | 10-bin probability output |
| Spatial attention | DocIQ-Simplified | Layout-aware weighting |
| NormInNormLoss | Li et al. 2020 | 10x faster convergence |
| PCGrad | Yu et al. 2020 | Gradient conflict resolution |
| Two-phase training | VQualA 2025 | Frozen→Full fine-tuning |
| Extended protocol | VQualA 2025 | 60 epochs with early stopping |

---

## 4. Performance Metrics

### 4.1 Primary Benchmark: DIQA-5000 Test Set

| Metric | Value | 95% CI | Target | Status |
|--------|-------|--------|--------|--------|
| **Overall PLCC** | 0.8865 | [0.8734, 0.8990] | ≥ 0.85 | ✅ Exceeds |
| **Overall SRCC** | 0.8596 | [0.8388, 0.8784] | ≥ 0.78 | ✅ Exceeds |
| **Overall MAE** | 2.225 | - | - | - |
| **VQualA Score** | 0.8838 | - | ≥ 0.80 | ✅ Exceeds |

### 4.2 Per-Dimension Performance (Test Set)

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI | MAE | RMSE |
|-----------|------|-------------|------|-------------|-----|------|
| **Overall** | 0.8865 | [0.8734, 0.8990] | 0.8596 | [0.8388, 0.8784] | 2.225 | 2.258 |
| **Sharpness** | 0.8942 | [0.8803, 0.9068] | 0.8510 | [0.8288, 0.8714] | 2.227 | 2.260 |
| **Color** | 0.8699 | [0.8556, 0.8847] | 0.8521 | [0.8315, 0.8714] | 2.326 | 2.354 |

### 4.3 VQualA Score Breakdown

The VQualA score combines multiple quality dimensions:

```text
VQualA = 0.8838 = weighted_mean(overall_plcc, sharpness_plcc, color_plcc, ...)
```

### 4.4 Training Convergence

| Phase | Best Epoch | Best PLCC | Best VQualA |
|-------|------------|-----------|-------------|
| Phase 1 (head warmup) | 8 | 0.8816 | 0.8636 |
| Phase 2 (fine-tuning) | 20 | 0.8910 | 0.8837 |

---

## 5. Preprocessing Requirements

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | `[N, 3, 1600, 1600]` |
| **Color Space** | RGB |
| **Value Range** | [0, 1] (normalized) |
| **Channel Order** | CHW (PyTorch) |

### Normalization

```python
# ImageNet normalization
mean = [0.485, 0.456, 0.406]
std = [0.229, 0.224, 0.225]
```

### Resize Strategy

```python
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize((1600, 1600)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])
```

---

## 6. Output Specification

### Output Structure

```python
{
    "overall": {
        "score": float,      # Expected value [1, 5]
        "probs": Tensor,     # [10] bin probabilities
        "logits": Tensor     # [10] raw logits
    },
    "sharpness": {
        "score": float,
        "probs": Tensor,
        "logits": Tensor
    },
    "color": {
        "score": float,
        "probs": Tensor,
        "logits": Tensor
    },
    "attention_map": Tensor  # Spatial attention weights
}
```

### Soft Label Bins

```python
# 10 bins spanning MOS scale [1, 5]
bin_centers = [1.0, 1.44, 1.89, 2.33, 2.78, 3.22, 3.67, 4.11, 4.56, 5.0]
```

---

## 7. Inference Example

```python
import torch
from image_preprocessing_detector.labeling.hyperiqa_plus_plus import HyperIQAPlusPlus
from torchvision import transforms
from PIL import Image

# Load model
model = HyperIQAPlusPlus(num_bins=10, use_pretrained=False)
checkpoint = torch.load("models/hyperiqa_plus_plus/hyperiqa_plus_plus_best.pt",
                        map_location="cpu")
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# Preprocess image
transform = transforms.Compose([
    transforms.Resize((1600, 1600)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])

image = Image.open("document.jpg").convert("RGB")
input_tensor = transform(image).unsqueeze(0)

# Inference
with torch.no_grad():
    output = model(input_tensor)

print(f"Overall Quality: {output['overall']['score'].item():.3f}")
print(f"Sharpness: {output['sharpness']['score'].item():.3f}")
print(f"Color Fidelity: {output['color']['score'].item():.3f}")
```

---

## 8. Limitations & Known Issues

### Limitations

- **Compute-Intensive**: 1600x1600 input requires significant GPU memory
- **Domain-Specific**: Trained on document images; may not generalize to natural images
- **Soft Labels**: Requires ground truth soft label distributions for training

### Known Failure Modes

- May struggle with extremely degraded documents (outside training distribution)
- Color fidelity assessment less accurate than sharpness/overall

### Hardware Requirements

| Configuration | Minimum | Recommended |
|--------------|---------|-------------|
| GPU Memory | 8GB | 24GB |
| System RAM | 16GB | 32GB |
| Inference Batch | 1-2 | 4-8 |

---

## 9. Lineage & Dependencies

### Model Lineage

```text
PyIQA HyperIQA (pretrained)
    └── HyperIQA++ (this model)
         ├── SpatialAttentionModule (DocIQ-Simplified)
         └── SoftLabelHeads (DeQA-Doc)
```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyTorch | ≥2.0 | Model framework |
| PyIQA | ≥0.1.10 | HyperIQA backbone |
| torchvision | ≥0.15 | Transforms |

---

## 10. References

1. Su et al., "Blindly Assess Image Quality in the Wild Guided by a Self-Adaptive Hyper Network" (HyperIQA), CVPR 2020
2. DocIQ methodology for document image quality assessment
3. DeQA-Doc soft label distribution approach
4. Li et al., "Norm-in-Norm Loss with Faster Convergence and Better Performance for Image Quality Assessment", ACM MM 2020
5. Yu et al., "Gradient Surgery for Multi-Task Learning" (PCGrad), NeurIPS 2020

---

## 11. Artifact Locations

| Artifact | Location |
|----------|----------|
| **Model Checkpoint** | `models/hyperiqa_plus_plus/hyperiqa_plus_plus_best.pt` |
| **Training Script** | `modal/train_hyperiqa_plus_plus.py` |
| **Model Architecture** | `src/image_preprocessing_detector/labeling/hyperiqa_plus_plus/model.py` |
| **Loss Functions** | `src/image_preprocessing_detector/labeling/hyperiqa_plus_plus/loss.py` |
| **Modal Volume** | `hyperiqa-checkpoints` |

---

## 12. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-14 | Initial release with DIQA-5000 training |
