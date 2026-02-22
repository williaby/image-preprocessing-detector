---
owner: ml-team
purpose: 'Model Card: SigLIP 2 Base NaFlex Document IQA (86M parameters).'
schema_type: common
status: draft
tags:
- iqa
- diqa_5000
title: 'Model Card: SigLIP2-IQA-Base-86M'
---

## Model Summary

> SigLIP2-IQA-Base-86M is a document image quality assessment model fine-tuned from Google's SigLIP 2 Base NaFlex backbone on the DIQA-5000 dataset. The model predicts three quality dimensions (overall, sharpness, color) with uncertainty estimation. It achieved **VQualA 0.886** on the DIQA-5000 test set, significantly outperforming all pretrained IQA models.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `siglip2-iqa-base-86m-v1.0.0` |
| **Project** | Prepare-Doc |
| **Phase** | Research / Candidate for Production |
| **Status** | `trained` |
| **Priority** | P1 (High - SOTA document IQA) |
| **Last Updated** | 2026-01-14 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Base Model** | `google/siglip2-base-patch16-naflex` |
| **Architecture** | SigLIP 2 ViT-B/16 + NaFlex (Native Flexible Resolution) |
| **Parameters** | 86M (backbone) + 1.6M (IQA heads) ≈ 88M total |
| **Precision** | FP32 (BF16/FP16 compatible) |
| **Input Size** | Variable (NaFlex: native aspect ratio preservation) |
| **Max Patches** | 576 (≈384×384 effective resolution) |
| **Output Format** | 3 quality scores + 3 uncertainty values |
| **Output Dimensions** | Overall, Sharpness, Color Fidelity |
| **License** | Apache 2.0 (inherited from SigLIP 2) |

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Multi-Dimensional Document Image Quality Assessment |
| **Role in Pipeline** | Quality scoring for document preprocessing gateway |
| **Upstream Dependencies** | None (standalone inference) |
| **Downstream Consumers** | DQS calculator, routing engine, OCR quality gating |

### Intended Use

- **Primary**: Document quality scoring for preprocessing pipeline
- **Secondary**: Pseudo-label generation for training larger models
- **Production**: CPU-optimized inference for edge/batch processing

### Out of Scope

- Natural image IQA (trained specifically on documents)
- Video quality assessment
- Real-time streaming (optimized for batch processing)

---

## 3. Performance Metrics

### DIQA-5000 Test Set Results

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| **VQualA** | **0.886** | 0.92 | -3.4% gap |
| **SRCC Overall** | 0.896 | 0.90 | ✅ Achieved |
| **SRCC Sharpness** | 0.869 | 0.90 | -3.1% gap |
| **SRCC Color** | 0.885 | 0.90 | -1.5% gap |
| **Best Val VQualA** | 0.875 | - | Early stopped |

### VQualA Formula

```python
vquala = 0.5 * srcc_overall + 0.25 * srcc_sharpness + 0.25 * srcc_color
# 0.886 = 0.5 * 0.896 + 0.25 * 0.869 + 0.25 * 0.885
```

### Comparison vs. Baselines (DIQA-5000)

| Model | SRCC Overall | VQualA | Inference |
|-------|--------------|--------|-----------|
| **SigLIP2-IQA-Base (ours)** | **0.896** | **0.886** | ~100ms |
| DeQA-Doc-3Specialists (VLM) | 0.733 | 0.786 | ~3000ms |
| MANIQA (pretrained) | 0.526 | 0.563 | ~1845ms |
| PyIQA-liqe (pretrained) | 0.403 | 0.511 | ~150ms |
| PyIQA-hyperiqa (pretrained) | 0.236 | 0.327 | ~152ms |

**Key Achievement**: +22% VQualA improvement over best pretrained model (MANIQA) and +10% over best VLM approach (DeQA-Doc).

---

## 4. Training Details

| Field | Value |
|-------|-------|
| **Dataset** | DIQA-5000 (Human MOS labels only) |
| **Train/Val/Test Split** | 3500 / 500 / 1000 |
| **Training Strategy** | Two-phase (head warmup + full fine-tuning) |
| **Phase 1 Epochs** | 10 (frozen backbone) |
| **Phase 2 Epochs** | 40 (full backbone unfrozen) |
| **Total Epochs** | 50 (early stopped at ~25 due to patience) |
| **Batch Size** | 16 |
| **Optimizer** | AdamW |
| **Phase 1 LR** | 2e-4 |
| **Phase 2 LR** | 2e-5 (backbone: 2e-6 with 0.1x multiplier) |
| **Weight Decay** | 0.01 |
| **Scheduler** | OneCycleLR |
| **Gradient Clipping** | 1.0 |
| **Early Stopping** | Patience=15 on validation VQualA |
| **GPU** | NVIDIA A10 (24GB) |
| **Training Time** | ~4 hours |

### Loss Functions

| Loss | Weight | Purpose |
|------|--------|---------|
| NormInNormLoss | 1.0 | Fast SRCC-aligned convergence |
| GaussianNLLLoss | 1.0 | Uncertainty estimation (μ, σ²) |

### Multi-Task Learning

- **PCGrad**: Enabled in Phase 1, disabled in Phase 2 (OOM)
- **Tasks**: Overall, Sharpness, Color (independent heads)

### Augmentation

| Augmentation | Probability | Notes |
|--------------|-------------|-------|
| Horizontal Flip | 0.5 | Label-preserving |
| Random Crop | 0.3 | Within safe bounds |

---

## 5. Architecture Details

### Model Structure

```text
SigLIP2DocumentIQA(
  backbone: Siglip2VisionModel (86M params, frozen → unfrozen)
  heads: ModuleDict(
    overall: Sequential(Linear(768→256), ReLU, Dropout(0.3), Linear(256→2))
    sharpness: Sequential(Linear(768→256), ReLU, Dropout(0.3), Linear(256→2))
    color: Sequential(Linear(768→256), ReLU, Dropout(0.3), Linear(256→2))
  )
)
```

### Output Format

```python
{
  "overall": {"mu": 3.45, "sigma_sq": 0.05},
  "sharpness": {"mu": 3.82, "sigma_sq": 0.03},
  "color": {"mu": 3.61, "sigma_sq": 0.04}
}
```

### NaFlex Resolution Handling

- **Input**: Variable aspect ratio images
- **Patch Size**: 16×16 pixels
- **Max Patches**: 576 (≈384×384 effective resolution)
- **Aspect Ratio**: Preserved (no distortion)

---

## 6. Inference Performance

### Latency Benchmarks

| Device | Latency | Memory | Batch Size |
|--------|---------|--------|------------|
| A10 GPU | ~50ms | ~4GB | 16 |
| T4 GPU | ~100ms | ~4GB | 8 |
| CPU (4 cores) | ~500ms | ~2GB | 1 |

### Deployment Options

| Format | Size | Status |
|--------|------|--------|
| PyTorch (.pt) | ~350MB | ✅ Available |
| ONNX | TBD | Planned |
| TorchScript | TBD | Planned |

---

## 7. Usage Example

```python
import torch
from transformers import AutoProcessor
from PIL import Image

# Import model class from training script (or define locally)
# from modal.train_siglip2_iqa import SigLIP2DocumentIQA

# Load processor
processor = AutoProcessor.from_pretrained("google/siglip2-base-patch16-naflex")

# Initialize model and load checkpoint
model = SigLIP2DocumentIQA(
    model_id="google/siglip2-base-patch16-naflex",
    uncertainty=True,
)
checkpoint = torch.load("models/iqa/siglip2_base/siglip2_iqa_best.pt")
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# Process image
image = Image.open("document.png").convert("RGB")
inputs = processor(
    images=[image],
    return_tensors="pt",
    padding="max_length",
    max_num_patches=576,
)

# Get quality scores with uncertainty
with torch.no_grad():
    outputs = model(inputs["pixel_values"], inputs["spatial_shapes"])

# Output format: sigma_sq is variance, take sqrt for std deviation
print(f"Overall Quality: {outputs['overall']['mu'].item():.2f} ± {outputs['overall']['sigma_sq'].sqrt().item():.2f}")
print(f"Sharpness: {outputs['sharpness']['mu'].item():.2f} ± {outputs['sharpness']['sigma_sq'].sqrt().item():.2f}")
print(f"Color Fidelity: {outputs['color']['mu'].item():.2f} ± {outputs['color']['sigma_sq'].sqrt().item():.2f}")
```

---

## 8. Limitations & Known Issues

### Training Issues Encountered

1. **PCGrad OOM in Phase 2**: Disabled due to memory constraints with full backbone unfrozen
2. **OneCycleLR Premature Convergence**: Training ended early (~25 epochs) due to aggressive LR decay
3. **Resolution Ceiling**: 576 patches may limit sharpness detection for dense documents

### Recommended Improvements for v2.0

Based on multi-model consensus analysis:

| Improvement | Priority | Expected Impact |
|-------------|----------|-----------------|
| CosineAnnealingLR scheduler | Tier 1 | Prevent premature convergence |
| Gradient accumulation | Tier 1 | Enable PCGrad in Phase 2 |
| Increase max_num_patches to 784 | Tier 1 | +2-3% sharpness SRCC |
| MarginRankingLoss | Tier 2 | Direct SRCC optimization |
| LLRD (0.9 decay/layer) | Tier 2 | Better fine-tuning stability |
| Attention pooling | Tier 2 | Localized quality detection |

---

## 9. Files & Artifacts

| File | Description | Location |
|------|-------------|----------|
| `siglip2_iqa_best.pt` | Best checkpoint (epoch ~25) | Modal: `siglip2-iqa-results/siglip2/` |
| `siglip2_iqa_epoch40.pt` | Epoch 40 checkpoint | Modal: `siglip2-iqa-results/siglip2/` |
| `training_results.json` | Training metrics | Modal: `siglip2-iqa-results/siglip2/` |

### Storage Locations

| Environment | Path |
|-------------|------|
| **Modal Volume** | `siglip2-iqa-results/siglip2/` |
| **Local** | `models/iqa/siglip2_base/` |
| **GCS** | TBD (pending production promotion) |

---

## 10. Version History

| Version | Date | Changes | VQualA |
|---------|------|---------|--------|
| v1.0.0 | 2026-01-14 | Initial training on DIQA-5000 | 0.886 |

---

## 11. Related Models

- [SigLIP2-IQA-Large-400M](siglip2_iqa_large_400m.md) - Larger variant (planned)
- [DeQA-Doc-3Specialists](external/diqa_model_dimension_specific.md) - VLM baseline
- [ResNet Teacher-Student IQA](resnet_teacher_student_iqa.md) - Classical ML approach

---

## 12. Citation

```bibtex
@misc{siglip2_iqa_2026,
  title={SigLIP2-IQA: Document Image Quality Assessment with Native Flexible Resolution},
  author={Image Detection Team},
  year={2026},
  note={Fine-tuned on DIQA-5000 for document quality assessment}
}
```

---

## Production Readiness: Research/Candidate

**Status**: High-performing research model, candidate for production after improvements.

**Next Steps**:

1. Implement Tier 1+2 improvements
2. Train SigLIP 2 Large (400M) variant
3. Benchmark on additional document datasets
4. Export to ONNX for production deployment
