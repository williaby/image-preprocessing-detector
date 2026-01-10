# Model Card: ResNet-18 ImageNet1K V2

## Model Summary

> ResNet-18 pretrained on ImageNet-1K, evaluated on DIQA-5000 as a lightweight backbone for document IQA. Shows near-zero correlations with quality labels, demonstrating ImageNet features alone do not transfer to document quality assessment without fine-tuning.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `ResNet18-ImageNet-IQA` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Dependency (Baseline Evaluation) |
| **Status** | `pretrained` |
| **Priority** | P3 (Evaluation/Research) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-18 (Deep Residual Network) |
| **Parameters** | 11,689,512 (~11.7M) |
| **Precision** | FP32 |
| **Input Size** | 224x224x3 (RGB) |
| **Output Format** | 1000-class ImageNet classification logits |
| **Source** | `torchvision.models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)` |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Lightweight backbone evaluation for document IQA |
| **Role in Pipeline** | Transfer learning baseline (not production) |
| **Upstream Dependencies** | None (external pretrained model) |
| **Downstream Consumers** | None (evaluation only) |

### Intended Use

- **Primary**: Baseline comparison for lightweight CNN architectures
- **Secondary**: Reference architecture for student model design
- **Out of Scope**: Production document quality assessment

---

## 3. Preprocessing Requirements

### Normalization

```python
mean = [0.485, 0.456, 0.406]  # ImageNet RGB mean
std = [0.229, 0.224, 0.225]   # ImageNet RGB std
```

### Complete Transform Pipeline

```python
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
```

---

## 4. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `ResNet18-ImageNet-IQA` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | 0.0963 | [0.0377, 0.1548] | 0.0905 | [0.0223, 0.1490] |
| Sharpness | -0.0205 | [-0.0875, 0.0451] | -0.0782 | [-0.1434, -0.0126] |
| Color | -0.0071 | [-0.0657, 0.0540] | -0.0162 | [-0.0806, 0.0476] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.4139 | 0.5618 |
| Sharpness | 0.4338 | 0.5914 |
| Color | 0.4125 | 0.5527 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 80 ms |
| Model Load Time | 2.9 s |

### Analysis

- **Overall**: Near-zero correlation (PLCC=0.10) indicates minimal predictive power
- **Sharpness**: Negative correlation (SRCC=-0.08) suggests inverse relationship
- **Color**: Near-zero correlation (PLCC=-0.01) - essentially random
- **Conclusion**: Fine-tuning required for document IQA tasks

---

## 5. Limitations & Known Issues

- **Domain Mismatch**: ImageNet features don't transfer to document quality
- **Near-zero correlations**: Predictions essentially uncorrelated with ground truth
- **Not production-ready**: Serves only as baseline comparison

---

## 6. Citation

```bibtex
@inproceedings{he2016deep,
  title={Deep Residual Learning for Image Recognition},
  author={He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
  booktitle={CVPR},
  year={2016}
}
```

---

## Production Readiness: ❌ NOT RECOMMENDED (baseline only)
