# Model Card: ConvNeXt-Tiny ImageNet1K

## Model Summary

> ConvNeXt-Tiny is a modernized CNN architecture (2022) incorporating Vision Transformer design principles while maintaining CNN efficiency. Evaluated on DIQA-5000, it shows slightly better sharpness correlation (0.15 PLCC) than ResNets, but overall near-zero correlation for document quality assessment.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `ConvNeXt-Tiny-ImageNet-IQA` |
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
| **Architecture** | ConvNeXt-Tiny |
| **Parameters** | ~28M |
| **Precision** | FP32 |
| **Input Size** | 224x224x3 (RGB) |
| **Key Innovation** | ViT-inspired CNN with depthwise convolutions, Layer Norm, GELU |
| **Source** | `torchvision.models.convnext_tiny(weights=ConvNeXt_Tiny_Weights.IMAGENET1K_V1)` |

### Design Innovations (vs ResNet)

- Depthwise separable convolutions for efficiency
- Larger kernel sizes (7×7 vs 3×3)
- Layer normalization (vs batch normalization)
- GELU activation (vs ReLU)
- Inverted bottleneck design

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Modern CNN architecture evaluation for document IQA |
| **Role in Pipeline** | Transfer learning baseline (not production) |
| **Upstream Dependencies** | None (external pretrained model) |
| **Downstream Consumers** | None (evaluation only) |

---

## 3. Preprocessing Requirements

### Normalization

```python
mean = [0.485, 0.456, 0.406]  # ImageNet RGB mean
std = [0.229, 0.224, 0.225]   # ImageNet RGB std
```

---

## 4. Performance Metrics

### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `ConvNeXt-Tiny-ImageNet-IQA` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |

**Correlation Metrics**:

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | -0.0330 | [-0.1027, 0.0309] | -0.1179 | [-0.1798, -0.0550] |
| Sharpness | **0.1489** | [0.0889, 0.2129] | **0.1206** | [0.0593, 0.1830] |
| Color | -0.0823 | [-0.1379, -0.0276] | -0.1256 | [-0.1846, -0.0659] |

**Error Metrics**:

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.4471 | 0.5715 |
| Sharpness | 0.4376 | 0.6084 |
| Color | 0.4218 | 0.5587 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 78 ms |
| Model Load Time | 2.6 s |

### Key Findings

- **Sharpness**: Best among ImageNet backbones (PLCC=0.15), but still insufficient
- **Overall**: Near-zero negative correlation - predictions inversely related
- **Color**: Weak negative correlation - domain mismatch evident
- **Conclusion**: Modern CNN design shows marginal improvement for sharpness only

---

## 5. Limitations & Known Issues

- **Still requires fine-tuning**: Marginal sharpness improvement (0.15 PLCC) insufficient for production
- **Overall quality prediction fails**: Near-zero/negative correlations
- **Not worth additional effort**: Fine-tuning cost doesn't justify marginal gains over simpler ResNet

---

## 6. Citation

```bibtex
@inproceedings{liu2022convnet,
  title={A ConvNet for the 2020s},
  author={Liu, Zhuang and Mao, Hanzi and Wu, Chao-Yuan and Feichtenhofer, Christoph and Darrell, Trevor and Xie, Saining},
  booktitle={CVPR},
  year={2022}
}
```

---

## Production Readiness: ❌ NOT RECOMMENDED (baseline only)
