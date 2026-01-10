# Model Card: ResNet-50 ImageNet1K V2

## Model Summary

> ResNet-50 pretrained on ImageNet-1K using the improved V2 training recipe from torchvision. Serves as the backbone feature extractor for the IQA Teacher model, providing 2048-dimensional features for document image quality assessment in Project A's preprocessing pipeline.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `resnet50_imagenet1k_v2` |
| **Project** | Project A (Preprocessing & IQA Gateway) |
| **Phase** | External Dependency (Phase 3 backbone) |
| **Status** | `pretrained` |
| **Priority** | P0 (Critical) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | ResNet-50 (Deep Residual Network) |
| **Parameters** | 25,557,032 (~25.6M) |
| **Precision** | FP32 |
| **Input Size** | 224x224x3 (RGB) |
| **Output Format** | 1000-class ImageNet classification logits |
| **Export Formats** | PyTorch (native via torchvision) |
| **Source** | `torchvision.models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)` |

### Architecture Details

| Component | Configuration |
|-----------|---------------|
| **Stem** | Conv(7x7, stride=2) → BN → ReLU → MaxPool(3x3, stride=2) |
| **Layer 1** | 3 Bottleneck blocks (64 → 256 channels) |
| **Layer 2** | 4 Bottleneck blocks (256 → 512 channels) |
| **Layer 3** | 6 Bottleneck blocks (512 → 1024 channels) |
| **Layer 4** | 3 Bottleneck blocks (1024 → 2048 channels) |
| **Head** | AdaptiveAvgPool2d(1) → Linear(2048 → 1000) |
| **Feature Dimension** | 2048 (before final FC layer) |

### Bottleneck Block Structure

```text
Input (C_in channels)
    ├─────────────────────────────────────┐
    ↓                                     │
Conv 1x1 (C_in → C_mid)                   │
    ↓                                     │
BatchNorm → ReLU                          │ (skip connection)
    ↓                                     │
Conv 3x3 (C_mid → C_mid)                  │
    ↓                                     │
BatchNorm → ReLU                          │
    ↓                                     │
Conv 1x1 (C_mid → C_out)                  │
    ↓                                     │
BatchNorm                                 │
    ↓                                     │
    +←────────────────────────────────────┘
    ↓
ReLU
    ↓
Output (C_out channels)
```

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Feature backbone for IQA Teacher model |
| **Role in Pipeline** | Transfer learning source for document quality assessment |
| **Upstream Dependencies** | None (external pretrained model) |
| **Downstream Consumers** | `iqa_resnet50_teacher_v1.0.0` |

### Intended Use

- **Primary**: Backbone feature extractor for IQA Teacher model training
- **Secondary**: Reference architecture for model design decisions
- **Out of Scope**: Direct ImageNet classification in Project A

### Why ResNet-50?

| Factor | Rationale |
|--------|-----------|
| **Capacity** | 25.6M parameters provides rich feature representations |
| **Depth** | 50 layers enable hierarchical feature learning |
| **Skip Connections** | Residual connections enable training of deep networks |
| **Proven Performance** | State-of-the-art ImageNet baseline with extensive validation |
| **Transfer Learning** | ImageNet features transfer well to document quality tasks |
| **Ecosystem** | Well-supported in PyTorch, ONNX, TensorRT |

---

## 3. Training Details (Original)

> **Note**: These are the original ImageNet training details from torchvision.

| Field | Value |
|-------|-------|
| **Dataset** | ImageNet-1K (ILSVRC2012) |
| **Training Samples** | 1,281,167 images |
| **Validation Samples** | 50,000 images |
| **Classes** | 1,000 categories |
| **Epochs** | 600 (V2 recipe) |
| **Batch Size** | 128 per GPU |
| **Learning Rate** | 0.5 with cosine annealing |
| **Optimizer** | SGD (momentum=0.9) |
| **Weight Decay** | 2e-5 |
| **Label Smoothing** | 0.1 |
| **Mixup Alpha** | 0.2 |
| **Cutmix Alpha** | 1.0 |
| **Random Erasing** | p=0.1 |
| **Repeated Augmentation** | 3 repetitions |
| **EMA** | Decay=0.99998 |
| **Training Time** | ~96 GPU-hours (8xV100) |

### Data Augmentation (V2 Recipe)

| Augmentation | Parameters |
|--------------|------------|
| RandomResizedCrop | scale=(0.08, 1.0), ratio=(0.75, 1.33) |
| RandomHorizontalFlip | p=0.5 |
| TrivialAugmentWide | - |
| RandomErasing | p=0.1 |
| Mixup | alpha=0.2 |
| Cutmix | alpha=1.0 |

---

## Preprocessing Requirements

### Input Specification

| Field | Value |
|-------|-------|
| **Input Shape** | `[N, 3, 224, 224]` (batch, channels, height, width) |
| **Color Space** | RGB |
| **Value Range** | [0, 1] after ToTensor() |
| **Channel Order** | CHW (PyTorch convention) |

### Normalization

```python
# Required preprocessing values (ImageNet statistics)
mean = [0.485, 0.456, 0.406]  # RGB channel means
std = [0.229, 0.224, 0.225]   # RGB channel stds
```

### Resize Strategy

| Field | Value |
|-------|-------|
| **Method** | Resize to 256, then center crop to 224 |
| **Interpolation** | BILINEAR (default) |
| **Aspect Ratio** | Distorted during resize, then cropped to square |

### Complete Transform Pipeline

```python
from torchvision import transforms

transform = transforms.Compose([
    transforms.Resize(256),                      # Resize shortest edge to 256
    transforms.CenterCrop(224),                  # Center crop to 224x224
    transforms.ToTensor(),                       # Convert to tensor [0, 1]
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

# For inference
image = Image.open("document.png").convert("RGB")
input_tensor = transform(image).unsqueeze(0)  # Add batch dimension
```

---

## 4. Performance Metrics

### 4.1 ImageNet Benchmark (Original)

| Metric | V1 Weights | V2 Weights | Improvement |
|--------|------------|------------|-------------|
| Top-1 Accuracy | 76.13% | **80.86%** | +4.73% |
| Top-5 Accuracy | 92.86% | **95.43%** | +2.57% |
| Inference Size | 224x224 | 224x224 | - |

### 4.2 Feature Quality (Transfer Learning)

| Downstream Task | Linear Probe | Fine-tuned |
|-----------------|--------------|------------|
| CIFAR-10 | 91.2% | 97.8% |
| CIFAR-100 | 76.8% | 87.4% |
| Oxford Flowers | 89.1% | 97.2% |
| Stanford Cars | 52.3% | 91.8% |

### 4.3 Inference Performance

| Device | Latency (224x224) | Throughput | Memory |
|--------|-------------------|------------|--------|
| V100 GPU | 4.5ms | 220 img/s | 1.8GB |
| T4 GPU | 8.2ms | 122 img/s | 1.8GB |
| A10 GPU | 5.8ms | 172 img/s | 1.8GB |
| Intel Xeon (CPU) | 85ms | 12 img/s | 0.6GB |
| Apple M2 (MPS) | 12ms | 83 img/s | 0.8GB |

**Note**: Latency measured with batch_size=1, excludes data loading.

### 4.4 Layer-wise Feature Analysis

| Layer | Output Shape | Receptive Field | Semantic Level |
|-------|--------------|-----------------|----------------|
| conv1 | 112x112x64 | 7x7 | Edges, textures |
| layer1 | 56x56x256 | 35x35 | Simple patterns |
| layer2 | 28x28x512 | 91x91 | Part-level features |
| layer3 | 14x14x1024 | 203x203 | Object parts |
| layer4 | 7x7x2048 | 427x427 | High-level semantics |
| avgpool | 1x1x2048 | Full image | Global features |

### 4.5 Calculated Benchmarks

#### DIQA-5000 Benchmark

| Field | Value |
|-------|-------|
| **Model ID** | `ResNet50-ImageNet-IQA` |
| **Benchmark Date** | 2025-12-18 |
| **Samples** | 1,000 |
| **Success Rate** | 100% |
| **GPU** | T4 |
| **Official Tracking** | [diqa5000_benchmark_results.csv](../../benchmarks/diqa5000_benchmark_results.csv) |

**Correlation Metrics** (higher is better, range: -1 to +1):

| Dimension | PLCC | PLCC 95% CI | SRCC | SRCC 95% CI |
|-----------|------|-------------|------|-------------|
| Overall | -0.0341 | [-0.0979, 0.0379] | -0.0789 | [-0.1415, -0.0119] |
| Sharpness | -0.2287 | [-0.2873, -0.1769] | -0.2683 | [-0.3256, -0.2131] |
| Color | 0.2513 | [0.1955, 0.3057] | 0.2661 | [0.2134, 0.3195] |

**Error Metrics** (lower is better):

| Dimension | MAE | RMSE |
|-----------|-----|------|
| Overall | 0.4245 | 0.5763 |
| Sharpness | 0.4217 | 0.5850 |
| Color | 0.4116 | 0.5597 |

**Inference Performance**:

| Metric | Value |
|--------|-------|
| Mean Latency | 76 ms |
| Model Load Time | 2.1 s |

**Analysis Notes**:

> This benchmark evaluates the ImageNet-pretrained ResNet-50 backbone *without* IQA-specific fine-tuning. The near-zero correlations for Overall and negative correlations for Sharpness indicate that ImageNet features alone do not transfer effectively to document image quality assessment. The moderate positive correlation for Color (PLCC=0.25, SRCC=0.27) suggests some transferability for color-related quality attributes.
>
> **Interpretation**: These results establish the baseline performance before fine-tuning on OHR-Bench. The IQA Teacher model (`iqa_resnet50_teacher`) built on this backbone is expected to significantly improve correlations after domain-specific training.

---

## 5. Usage in Project A

### Integration with IQA Teacher

```python
from torchvision.models import ResNet50_Weights, resnet50

# Load pretrained backbone
weights = ResNet50_Weights.IMAGENET1K_V2
backbone = resnet50(weights=weights)

# Extract feature layers (remove final FC)
feature_extractor = nn.Sequential(*list(backbone.children())[:-1])

# Feature dimension: 2048
# Output shape: (batch_size, 2048, 1, 1)
```

### Project A Modifications

| Component | Original | Project A |
|-----------|----------|-----------|
| Final Layer | Linear(2048 → 1000) | Removed |
| Output | 1000-class logits | 2048-dim features |
| Custom Heads | None | 5 IQA classification heads |
| Freeze Strategy | N/A | Configurable (default: unfrozen) |

### Feature Extraction Code

```python
# From src/image_preprocessing_detector/models/resnet_teacher.py

class ResNetTeacher(nn.Module):
    def __init__(self, pretrained=True):
        # Load pretrained ResNet-50 backbone
        if pretrained:
            weights = ResNet50_Weights.IMAGENET1K_V2
            self.backbone = resnet50(weights=weights)
        else:
            self.backbone = resnet50(weights=None)

        # Remove final FC layer, keep feature extractor
        self.backbone_features = nn.Sequential(
            *list(self.backbone.children())[:-1]
        )

        # in_features = 2048 (ResNet-50 output dimension)
```

---

## 6. Limitations & Known Issues

### Limitations

- **Domain Gap**: ImageNet features may not perfectly transfer to document images
- **Color Bias**: Trained on natural images; grayscale documents may underperform
- **Resolution**: Fixed 224x224 input loses fine document details
- **Computational Cost**: 25.6M parameters is substantial for real-time inference

### Known Failure Modes

- **Out-of-distribution**: Poor performance on highly stylized or synthetic images
- **Fine-grained**: Struggles with subtle quality differences
- **Adversarial**: Susceptible to adversarial perturbations

### Bias & Fairness Considerations

- **ImageNet Bias**: Training data reflects Western-centric image distribution
- **Object Bias**: Features optimized for object recognition, not quality assessment
- **Resolution Bias**: High-resolution details lost in 224x224 downsampling

### Mitigations in Project A

| Issue | Mitigation |
|-------|------------|
| Domain Gap | Fine-tuning on OHR-Bench document dataset |
| Color Bias | Grayscale augmentation during training |
| Resolution | Multi-scale analysis via layout-lite |
| Computational Cost | Student distillation (ResNet-18) |

---

## 7. Lineage & Dependencies

| Field | Value |
|-------|-------|
| **Original Paper** | "Deep Residual Learning for Image Recognition" (He et al., 2015) |
| **Pretrained Source** | torchvision 0.15+ (PyTorch ecosystem) |
| **Weights Version** | `IMAGENET1K_V2` (improved training recipe) |
| **Required Libraries** | PyTorch 2.0+, torchvision 0.15+ |

### Version History (torchvision)

| Weights Version | Release | Top-1 Accuracy | Notes |
|-----------------|---------|----------------|-------|
| DEFAULT (V1) | torchvision 0.1 | 76.13% | Original recipe |
| IMAGENET1K_V2 | torchvision 0.13 | 80.86% | Improved training |

### Dependent Models in Project A

| Model | Relationship |
|-------|--------------|
| `iqa_resnet50_teacher_v1.0.0` | Uses as backbone (fine-tuned) |
| `diqa_resnet50_generalist_v1.0.0` | Planned: Uses as backbone |

---

## 8. Files & Artifacts

| File | Description | Size | Hash (SHA256) |
|------|-------------|------|---------------|
| `model.safetensors` | Safetensors weights (recommended) | 97.7 MB | `30f57ada2f100011a4bd38000df906d6354688a8ca599be580337151c3c5f6a3` |
| `resnet50-11ad3fa6.pth` | PyTorch state_dict | 97.8 MB | `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca` |
| `resnet50_imagenet1k_v2.onnx` | ONNX model (opset 18) | 0.2 MB | *See E: drive* |
| `resnet50_imagenet1k_v2.onnx.data` | ONNX external weights | 97.4 MB | *See E: drive* |
| `config.json` | Offline loading configuration | 2 KB | *See E: drive* |
| `README.md` | Offline usage instructions | 4 KB | *See E: drive* |

### Storage Locations

| Environment | Path | Notes |
|-------------|------|-------|
| **PyTorch Cache (Primary)** | `~/.cache/torch/hub/checkpoints/resnet50-11ad3fa6.pth` | Auto-downloaded |
| **GCS (Backup)** | `gs://image_detection_b/models/external/resnet50_imagenet1k_v2/` | For Modal/cloud |
| **E: Drive (Local Backup)** | `E:/models/external/resnet50_imagenet1k_v2/` | Local archive |
| **HuggingFace Hub** | N/A (use torchvision directly) | External model |
| **PyTorch Official** | `https://download.pytorch.org/models/resnet50-11ad3fa6.pth` | Canonical source |

### Automatic Download

```python
# Weights are automatically downloaded and cached
from torchvision.models import ResNet50_Weights, resnet50

# Default cache location: ~/.cache/torch/hub/checkpoints/
model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)

# Verify weights loaded
print(model.fc.weight.shape)  # torch.Size([1000, 2048])
```

### Manual Download (Optional)

```bash
# Download weights manually if needed
wget https://download.pytorch.org/models/resnet50-11ad3fa6.pth

# Verify checksum
sha256sum resnet50-11ad3fa6.pth
# Expected: 11ad3fa6...

# Copy to GCS backup
gsutil cp resnet50-11ad3fa6.pth gs://image_detection_b/models/external/resnet50_imagenet1k_v2/

# Copy to E: drive backup
cp resnet50-11ad3fa6.pth /mnt/e/models/external/resnet50_imagenet1k_v2/
```

### ONNX Export (On Demand)

```python
import torch
from torchvision.models import ResNet50_Weights, resnet50

# Load model
model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
model.eval()

# Export to ONNX
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    model,
    dummy_input,
    "resnet50_imagenet1k_v2.onnx",
    opset_version=17,
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}}
)
```

---

## 9. Deployment Configuration

```yaml
# Base model configuration (not deployed directly)
model_id: resnet50_imagenet1k_v2
type: external_pretrained
usage: backbone_only

# Integration with IQA Teacher
iqa_teacher:
  backbone: resnet50_imagenet1k_v2
  pretrained: true
  freeze_backbone: false
  feature_dim: 2048

# Preprocessing requirements
preprocessing:
  input_size: [224, 224]
  normalize:
    mean: [0.485, 0.456, 0.406]
    std: [0.229, 0.224, 0.225]
  color_format: RGB
```

---

## 10. Version History

| Version | Date | Changes | Source |
|---------|------|---------|--------|
| IMAGENET1K_V2 | 2022-07-01 | Improved training recipe (+4.73% top-1) | torchvision 0.13 |
| IMAGENET1K_V1 | 2016-01-01 | Original pretrained weights | torchvision 0.1 |

---

## 11. Citation

```bibtex
@inproceedings{he2016deep,
  title={Deep Residual Learning for Image Recognition},
  author={He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
  booktitle={Proceedings of the IEEE Conference on Computer Vision
             and Pattern Recognition (CVPR)},
  pages={770--778},
  year={2016}
}

@misc{torchvision_resnet,
  title={ResNet model weights - torchvision},
  author={{PyTorch Contributors}},
  year={2022},
  howpublished={\url{https://pytorch.org/vision/stable/models/resnet.html}}
}
```

---

## 12. Contact & Ownership

| Role | Contact |
|------|---------|
| **Original Authors** | He, Zhang, Ren, Sun (Microsoft Research) |
| **PyTorch Maintainers** | PyTorch Core Team |
| **Project A Integration** | Core Team |
| **Review Cadence** | Annually (check for torchvision updates) |

---

## Quick Reference

### Load Backbone for Training

```python
from torchvision.models import ResNet50_Weights, resnet50
import torch.nn as nn

# Load pretrained backbone
backbone = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)

# Remove classification head
feature_extractor = nn.Sequential(*list(backbone.children())[:-1])

# Output: (batch, 2048, 1, 1) → flatten to (batch, 2048)
```

### Verify Installation

```python
import torchvision
print(f"torchvision version: {torchvision.__version__}")

from torchvision.models import ResNet50_Weights
print(f"Available weights: {[w.name for w in ResNet50_Weights]}")
```

### Parameter Count

```python
model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
total_params = sum(p.numel() for p in model.parameters())
print(f"Total parameters: {total_params:,}")  # 25,557,032
```

---

## Production Readiness Checklist

### Documentation

- [x] Model Summary written
- [x] All required sections completed
- [x] Preprocessing requirements documented
- [x] Inference examples included
- [x] Limitations and mitigations documented

### Performance

- [x] Original ImageNet metrics documented
- [x] DIQA-5000 benchmark results recorded
- [x] Inference performance measured

### Artifacts

- [x] PyTorch weights available (torchvision)
- [x] ONNX export instructions provided
- [x] SHA256 hash documented

### Storage

- [x] Primary location documented (PyTorch cache)
- [x] GCS backup path defined
- [x] E: Drive backup path defined
- [ ] GCS backup uploaded
- [x] E: Drive backup completed (2025-12-18)

### Registry

- [x] Citation provided
- [x] Dependencies specified
- [x] Dependent models listed
