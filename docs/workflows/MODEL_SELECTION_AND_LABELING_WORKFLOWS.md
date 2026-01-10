---
owner: docs-team
purpose: Documentation for Model Selection and Labeling Workflows.
schema_type: common
status: draft
tags:
- labeling
- pipeline
title: Model Selection and Labeling Workflows
---

> **Status**: Active
> **Created**: 2025-12-18
> **Owner**: Core Team
> **Purpose**: Document workflows for model selection, benchmarking, fine-tuning, and dataset labeling

---

## Overview

This document captures all workflows related to Document Image Quality Assessment (DIQA) model development:

1. **IQA Model Benchmarking** - Evaluate traditional CNN-based quality assessment models
2. **VLM Model Benchmarking** - Evaluate Vision-Language Models for quality scoring
3. **IQA Model Fine-Tuning** - Train/adapt IQA models on DIQA-5000
4. **VLM Model Fine-Tuning** - Fine-tune VLMs for document quality assessment
5. **Pseudo-Label Generation** - Generate quality labels for unlabeled datasets
6. **Model Quantization** - Compress models for production deployment

> **Reference**: See `docs/benchmarks/diqa5000_benchmark_results.csv` for current benchmark results.

---

## Track Architecture Overview

The pseudo-labeling system uses a **two-track architecture** to leverage the strengths of both CNN-based IQA models and Vision-Language Models:

### Track A: IQA Models (CNN-based)

| Model | Sub-Track | Role | Precision | Parameters | Modal GPU | Status |
|-------|-----------|------|-----------|------------|-----------|--------|
| **DocIQ-Replica** | A3 | **Generalist Anchor** | FP32 | ~25M | A100-80GB | ⚠️ Requires Training |
| **MUSIQ** | A1 | Sharpness Specialist | FP32 | ~27M | T4/A10G | ✅ Available (PyIQA) |
| **QualiCLIP** | A2 | Color Specialist | FP32 | ~150M | T4/A10G | ✅ Available (PyIQA) |

> **DocIQ-Replica Note**: The original DocIQ model is not publicly available. We train a ResNet-50 based
> model from scratch on DIQA-5000 using the Layout Fusion Downsampler architecture (1600×1600 input,
> 11-class DocLayout-YOLO masks). Because it lacks IQA pretraining bias, it serves as the **Generalist Anchor**
> for Track A.

### Track B: VLM Models (Vision-Language)

| Model | Role | Precision | Parameters | Modal GPU | Status |
|-------|------|-----------|------------|-----------|--------|
| **Qwen3-VL-8B** | Generalist Anchor | FP16 | ~8B | A100-80GB | ✅ Available |
| **InternVL3-8B** | Overall Specialist | FP16 | ~8B | A100-80GB | ✅ Available |

### Track Comparison

| Aspect | Track A (IQA) | Track B (VLM) |
|--------|---------------|---------------|
| **GPU Requirement** | T4/A10G (16-24GB) | A100-80GB |
| **Batch Size** | 32-64 | 1-4 |
| **Inference Time** | <50ms/image | 200-400ms/image |
| **Training** | End-to-end fine-tuning | LoRA fine-tuning |
| **Cost/hour** | ~$0.40-1.00 | ~$4.50 |

### Specialty Matrix

Each model is trained on all three dimensions but optimized for checkpoint selection based on its role:

| Model | Track | Role | Overall | Sharpness | Color | Selection Criterion |
|-------|-------|------|---------|-----------|-------|---------------------|
| Qwen3-VL-8B | B (VLM) | Generalist Anchor | Primary ★ | Primary ★ | Primary ★ | Weighted(SRCC_mean, ECE) |
| DocIQ-Replica | A (IQA) | **Generalist Anchor** | Primary ★ | Primary ★ | Primary ★ | **Weighted(SRCC_mean, ECE)** |
| MUSIQ | A (IQA) | Sharpness Specialist | Secondary | **Primary ★** | Secondary | Weighted(SRCC_sharpness, ECE) |
| QualiCLIP | A (IQA) | Color Specialist | Secondary | Secondary | **Primary ★** | Weighted(SRCC_color, ECE) |
| InternVL3-8B | B (VLM) | Overall Specialist | **Primary ★** | Secondary | Secondary | Weighted(SRCC_overall, ECE) |

> **Two Generalist Anchors**: The ensemble has two generalist anchors—one per track. This provides
> balanced predictions from both IQA (DocIQ-Replica) and VLM (Qwen3-VL-8B) perspectives, with specialists
> refining dimension-specific assessments.

---

## 1. IQA Model Benchmarking Workflow

### Purpose

Evaluate CNN-based Image Quality Assessment models against the DIQA-5000 benchmark to establish baseline performance and select candidates for fine-tuning.

### Supported Models

| Model | Architecture | Input Size | Parameters | Status |
|-------|--------------|------------|------------|--------|
| ResNet50-ImageNet-IQA | ResNet-50 + IQA head | 224×224 | ~25M | ✅ Implemented |
| ResNet34-ImageNet-IQA | ResNet-34 + IQA head | 224×224 | ~21M | ✅ Implemented |
| ResNet18-ImageNet-IQA | ResNet-18 + IQA head | 224×224 | ~11M | ✅ Implemented |
| ConvNeXt-Tiny-ImageNet-IQA | ConvNeXt-T + IQA head | 224×224 | ~29M | ✅ Implemented |
| EfficientNet-B4-ImageNet-IQA | EfficientNet-B4 + IQA head | 380×380 | ~19M | ✅ Implemented |
| Swin-Tiny-ImageNet-IQA | Swin-T + IQA head | 224×224 | ~28M | ✅ Implemented |
| CLIP-ViT-B-32-IQA | CLIP + text prompts | 224×224 | ~150M | ✅ Implemented |
| PyIQA (MUSIQ, NIQE, BRISQUE, etc.) | Various | Various | Various | ✅ Implemented |

### Workflow Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  IQA Benchmarking Workflow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. DATASET PREPARATION                                          │
│     └─ Download DIQA-5000 test split from GCS                   │
│        gs://assured-oss-457903-diqa5000/diqa5000-test.tar.gz    │
│                                                                  │
│  2. MODEL INITIALIZATION                                         │
│     ├─ Load ImageNet pretrained backbone                        │
│     ├─ Replace classification head with IQA regression head     │
│     │   └─ Linear → ReLU → Dropout → Linear(3) → Sigmoid        │
│     └─ Scale output to [1, 5] range                             │
│                                                                  │
│  3. INFERENCE                                                    │
│     ├─ Process all 1000 test samples                            │
│     ├─ Extract predictions for 3 dimensions:                    │
│     │   - Overall quality                                        │
│     │   - Sharpness                                              │
│     │   - Color fidelity                                         │
│     └─ Record inference time per sample                          │
│                                                                  │
│  4. METRIC COMPUTATION                                           │
│     ├─ Per-dimension metrics:                                    │
│     │   - PLCC (Pearson Linear Correlation Coefficient)         │
│     │   - SRCC (Spearman Rank Correlation Coefficient)          │
│     │   - MAE (Mean Absolute Error)                              │
│     │   - RMSE (Root Mean Squared Error)                         │
│     └─ Bootstrapped 95% confidence intervals (1000 iterations)  │
│                                                                  │
│  5. RESULTS GENERATION                                           │
│     ├─ JSON metrics with CIs                                     │
│     ├─ Markdown leaderboard                                      │
│     └─ Reproducibility manifest                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Commands

```bash
# Run individual benchmark (quick test)
uv run modal run modal/arena_iqa_benchmark.py::run_resnet50_benchmark --num-samples 10

# Run full benchmark (1000 samples, detached)
uv run modal run -d modal/arena_iqa_benchmark.py::run_resnet50_benchmark

# Run all IQA benchmarks in parallel
uv run modal run -d modal/arena_iqa_benchmark.py::run_resnet50_benchmark &
uv run modal run -d modal/arena_iqa_benchmark.py::run_resnet34_benchmark &
uv run modal run -d modal/arena_iqa_benchmark.py::run_resnet18_benchmark &
uv run modal run -d modal/arena_iqa_benchmark.py::run_convnext_tiny_benchmark &
uv run modal run -d modal/arena_iqa_benchmark.py::run_efficientnet_b4_benchmark &
uv run modal run -d modal/arena_iqa_benchmark.py::run_swin_tiny_benchmark &

# Run PyIQA metrics
uv run modal run modal/arena_iqa_benchmark.py::run_pyiqa_benchmark --metric-name musiq
```

### Output Schema

```json
{
  "model_id": "ResNet50-ImageNet-IQA",
  "num_samples": 1000,
  "successful": 1000,
  "failed": 0,
  "success_rate": 1.0,
  "timing": {
    "mean_ms": 112,
    "min_ms": 98,
    "max_ms": 245,
    "total_s": 112.4,
    "model_load_s": 1.9
  },
  "overall": {
    "plcc": 0.1773,
    "plcc_ci_lower": 0.1234,
    "plcc_ci_upper": 0.2312,
    "srcc": 0.1671,
    "srcc_ci_lower": 0.1145,
    "srcc_ci_upper": 0.2197,
    "mae": 0.4265,
    "rmse": 0.5813,
    "num_valid": 1000
  },
  "sharpness": { ... },
  "color": { ... }
}
```

### Infrastructure

- **GPU**: Tesla T4 (16GB) or A10 (24GB)
- **Memory**: 16GB
- **Timeout**: 3600s (1 hour)
- **Dataset Cache**: Modal volume `/data`

---

## 2. VLM Model Benchmarking Workflow

### Purpose

Evaluate Vision-Language Models for document quality assessment using natural language prompts and structured output parsing.

### Supported Models

| Model | Size | VRAM | Status |
|-------|------|------|--------|
| Qwen3-VL-8B | 8B | ~16GB | ✅ Implemented |
| InternVL3-8B | 8B | ~16GB | ✅ Implemented |
| Qwen3-VL-32B | 32B | ~40GB | ⚠️ Requires A100 |
| InternVL3.5-38B | 38B | ~50GB | ⚠️ Requires A100 |

### Workflow Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  VLM Benchmarking Workflow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. MODEL PREPARATION                                            │
│     ├─ Download model from HuggingFace                          │
│     ├─ Apply warmup inference (cold start mitigation)           │
│     └─ Configure generation parameters:                          │
│         - temperature: 0.0 (greedy decoding)                    │
│         - max_new_tokens: 256                                    │
│         - do_sample: False                                       │
│                                                                  │
│  2. IMAGE PREPROCESSING                                          │
│     ├─ Load image from dataset                                   │
│     ├─ Resize to 1024×1024 (consistency)                        │
│     └─ Convert to RGB                                            │
│                                                                  │
│  3. PROMPT CONSTRUCTION                                          │
│     └─ Structured prompt requesting:                             │
│         - Overall quality score (1-5)                            │
│         - Sharpness score (1-5)                                  │
│         - Color fidelity score (1-5)                             │
│         - Format: "overall: X.X, sharpness: X.X, color: X.X"    │
│                                                                  │
│  4. RESPONSE PARSING                                             │
│     ├─ Extract numeric scores via regex                         │
│     ├─ Handle parsing failures gracefully                       │
│     └─ Validate scores are in [1, 5] range                      │
│                                                                  │
│  5. METRIC COMPUTATION                                           │
│     └─ Same as IQA workflow (PLCC, SRCC, MAE, RMSE + CIs)       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Commands

```bash
# Quick test (10 samples)
uv run modal run modal/arena_vlm_benchmark.py::run_qwen3_vl_8b_benchmark --num-samples 10

# Full benchmark (detached)
uv run modal run -d modal/arena_vlm_benchmark.py::run_qwen3_vl_8b_benchmark
uv run modal run -d modal/arena_vlm_benchmark.py::run_internvl3_8b_benchmark
```

### Key Differences from IQA Benchmarking

| Aspect | IQA Models | VLM Models |
|--------|------------|------------|
| Input | Raw tensor | Image + text prompt |
| Output | Direct regression | Natural language (parsed) |
| Inference time | ~100ms | ~2-5s |
| Memory | 2-4GB | 16-50GB |
| Failure modes | OOM only | Parsing errors, hallucinations |

---

## 3. IQA Model Fine-Tuning Workflow (Track A)

### Purpose

Train CNN-based IQA models on DIQA-5000 to predict multi-dimensional quality scores. Track A contains three models with fundamentally different starting points, requiring distinct training protocols.

### Sub-Track Overview

| Sub-Track | Model | Starting Point | Role | Training Approach |
|-----------|-------|----------------|------|-------------------|
| **A1** | MUSIQ | Pretrained IQA (KonIQ-10k) | Sharpness Specialist | Fine-tune with specialist weights |
| **A2** | QualiCLIP | Pretrained CLIP (opinion-unaware) | Color Specialist | Fine-tune with specialist weights |
| **A3** | DocIQ-Replica | ImageNet only (no IQA) | **Generalist Anchor** | Train from scratch, equal weights |

### Multi-Task Loss Weighting

All models are trained on all three dimensions but with different loss weightings:

| Model | Role | Overall | Sharpness | Color | Strategy |
|-------|------|---------|-----------|-------|----------|
| DocIQ-Replica | Generalist Anchor | **0.34** | **0.33** | **0.33** | Equal weights |
| MUSIQ | Sharpness Specialist | 0.2 | **0.6** | 0.2 | Sharpness-weighted |
| QualiCLIP | Color Specialist | 0.2 | 0.2 | **0.6** | Color-weighted |

### Training Loss Function

```python
def dimension_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Combined MSE + rank loss + focal calibration."""
    mse = F.mse_loss(pred, target)
    rank = differentiable_rank_loss(pred, target)
    focal_ece = focal_calibration_loss(pred, target)

    return 0.6 * mse + 0.2 * rank + 0.2 * focal_ece
```

---

### Sub-Track A1: MUSIQ Fine-Tuning (Sharpness Specialist)

**Starting Point:** MUSIQ is pretrained on KonIQ-10k for natural image quality. It outputs a single MOS score (0-1 scale) and has strong blur/sharpness detection capabilities.

**Training Protocol:**

1. **Phase 1 - Head warmup** (10 epochs):
   - Freeze MUSIQ backbone completely
   - Train multi-task head only
   - Learning rate: 1e-3
   - Loss weights: [0.2, **0.6**, 0.2] (sharpness specialist)

2. **Phase 2 - Fine-tune backbone** (20 epochs):
   - Unfreeze backbone
   - Learning rate: 1e-5 (backbone), 1e-4 (head)
   - Same loss weights

3. **Checkpoint Selection:** Weighted(SRCC_sharpness, ECE) with `balanced` preset

---

### Sub-Track A2: QualiCLIP Fine-Tuning (Color Specialist)

**Starting Point:** QualiCLIP uses CLIP ViT-B/32 with learned quality-aware text prompts. It's "opinion-unaware" but has strong color/semantic understanding from CLIP pretraining.

**Training Protocol:**

1. **Phase 1 - Head warmup** (10 epochs):
   - Freeze CLIP vision encoder completely
   - Train multi-task head only
   - Learning rate: 1e-3
   - Loss weights: [0.2, 0.2, **0.6**] (color specialist)

2. **Phase 2 - Fine-tune encoder** (20 epochs):
   - Unfreeze vision encoder
   - Learning rate: 1e-6 (encoder), 1e-4 (head) — lower LR to preserve CLIP features
   - Same loss weights

3. **Checkpoint Selection:** Weighted(SRCC_color, ECE) with `balanced` preset

---

### Sub-Track A3: DocIQ-Replica Training (Generalist Anchor)

**Starting Point:** No pretrained IQA weights available. We train from ImageNet-pretrained ResNet-50 with Layout Fusion Downsampler, making this effectively a **from-scratch** IQA model for documents.

> **DocIQ Paper Alignment**: Implementing true DocIQ Replica with full Layout Fusion Downsampler architecture.

| Aspect | Specification |
|--------|---------------|
| **Input Resolution** | 1600×1600 |
| **Layout Masks** | 11-class semantic masks via DocLayout-YOLO |
| **Expected SRCC** | 0.75-0.80 |
| **GPU Memory** | A100-80GB (batch 4-8) |

**Architecture:**

```text
┌─────────────────────────────────────────────────────────────────┐
│                    DocIQ-Replica Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT: RGB Image (1600×1600) + Layout Mask (11×1600×1600)      │
│                           ↓                                      │
│  LAYOUT FUSION DOWNSAMPLER                                       │
│  ├─ RGB Encoder: Conv2d → BatchNorm → ReLU (64 channels)        │
│  ├─ Layout Encoder: Conv2d → BatchNorm → ReLU (64 channels)     │
│  └─ Fusion: Concat → Conv1x1 → 3 channels (400×400 output)      │
│                           ↓                                      │
│  RESNET-50 BACKBONE (ImageNet pretrained)                        │
│  └─ Features: 2048-dim                                           │
│                           ↓                                      │
│  MULTI-TASK HEAD                                                 │
│  ├─ Shared: Linear(2048→512) → ReLU → Dropout(0.1)              │
│  └─ Per-dimension: Linear(512→1) × 3                             │
│                           ↓                                      │
│  OUTPUT: {overall, sharpness, color} scores (1-5 scale)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Training Protocol:**

1. **Phase 1 - Head warmup** (15 epochs):
   - Freeze ResNet-50 backbone
   - Train multi-task head only
   - Learning rate: 1e-3 with linear warmup (5 epochs) + cosine decay
   - Loss weights: [**0.34**, **0.33**, **0.33**] (equal/generalist)

2. **Phase 2 - Full fine-tune** (45 epochs):
   - Unfreeze entire backbone
   - Learning rate: 1e-5 (backbone), 1e-4 (head) with cosine annealing
   - Same loss weights
   - Augmentation: horizontal flip, rotation (±5°), mild color jitter

3. **Checkpoint Selection:** Weighted(SRCC_mean, ECE) using `balanced` preset

---

### Track A Training Configuration Summary

| Parameter | MUSIQ (A1) | QualiCLIP (A2) | DocIQ-Replica (A3) |
|-----------|------------|----------------|---------------------|
| **Role** | Sharpness Specialist | Color Specialist | **Generalist Anchor** |
| **Backbone** | ViT-B/16 | CLIP ViT-B/32 | ResNet-50 + Layout Fusion |
| **Feature Dim** | 384 | 512 | 2048 |
| **Input Size** | Variable | 224×224 | **1600×1600** |
| **Layout Masks** | N/A | N/A | **11-class DocLayout-YOLO** |
| **Total Epochs** | 30 | 30 | **60** |
| **Loss Weights** | [0.2, **0.6**, 0.2] | [0.2, 0.2, **0.6**] | [**0.34**, **0.33**, **0.33**] |
| **Checkpoint Select** | SRCC_sharpness | SRCC_color | **SRCC_mean** |
| **Batch Size** | 32 | 32 | 4-8 (gradient accum) |
| **GPU** | T4/A10G | T4/A10G | **A100-80GB** |
| **Est. Time** | 4-6 hrs | 4-6 hrs | **12-18 hrs** |

### Training Commands

```bash
# Sub-Track A1: Fine-tune MUSIQ
uv run modal run --detach modal/train_musiq_finetune.py

# Sub-Track A2: Fine-tune QualiCLIP
uv run modal run --detach modal/train_qualiclip_finetune.py

# Sub-Track A3: Train DocIQ-Replica from scratch
uv run modal run --detach modal/train_dociq_replica.py

# Export to ONNX
uv run modal run modal/export_phase7_onnx.py --model-type production
```

### Output Artifacts

```text
gs://image_detection_b/models/diqa/track_a_iqa/
├── dociq_replica/v1.0.0/
│   ├── model.pt
│   ├── model.onnx
│   ├── config.json
│   └── MODEL_CARD.md
├── musiq/v1.0.0/
│   ├── model.pt
│   ├── config.json
│   └── MODEL_CARD.md
└── qualiclip/v1.0.0/
    ├── model.pt
    ├── config.json
    └── MODEL_CARD.md
```

---

## 4. VLM Model Fine-Tuning Workflow (Track B)

### Purpose

Fine-tune Vision-Language Models on DIQA-5000 using LoRA to learn human quality judgments and generate calibrated quality scores.

### Track B Model Roles

| Model | Role | Loss Weights | Selection Criterion |
|-------|------|--------------|---------------------|
| **Qwen3-VL-8B** | Generalist Anchor | [0.34, 0.33, 0.33] | Weighted(SRCC_mean, ECE) |
| **InternVL3-8B** | Overall Specialist | [**0.6**, 0.2, 0.2] | Weighted(SRCC_overall, ECE) |

### Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                  VLM Fine-Tuning Pipeline (Track B)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STAGE 1: BASE MODEL SELECTION                                   │
│  ├─ Qwen3-VL-8B (Generalist Anchor)                             │
│  └─ InternVL3-8B (Overall Specialist)                           │
│                                                                  │
│  STAGE 2: LoRA ADAPTER CONFIGURATION                             │
│  ├─ Method: LoRA (Low-Rank Adaptation)                          │
│  ├─ Rank (r): 16                                                 │
│  ├─ Alpha: 32                                                    │
│  ├─ Target modules: q_proj, k_proj, v_proj, o_proj              │
│  └─ Dropout: 0.05                                                │
│                                                                  │
│  STAGE 3: TRAINING                                               │
│  ├─ Dataset: DIQA-5000 train split (3500 images)                │
│  ├─ Epochs: 3                                                    │
│  ├─ Batch size: 4 (gradient_accum: 8 = 32 effective)            │
│  ├─ Learning rate: 2e-4                                          │
│  ├─ Loss: MSE + Rank + Focal ECE (same as Track A)              │
│  └─ Loss weights: Model-specific (see table above)              │
│                                                                  │
│  STAGE 4: VALIDATION                                             │
│  ├─ Validate on DIQA-5000 val split (750 images)                │
│  ├─ Compute PLCC, SRCC, ECE per dimension                       │
│  └─ Checkpoint selection: Weighted(SRCC, ECE) scoring           │
│                                                                  │
│  STAGE 5: EXPORT                                                 │
│  ├─ Export adapter weights (safetensors)                        │
│  ├─ Generate MODEL_CARD.md                                       │
│  └─ Upload to GCS versioned storage                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Prompt Template for VLM Training

```text
Assess this document image's quality on three dimensions.
Rate each from 1.0 (worst) to 5.0 (best):

1. **Overall**: General readability and professional appearance
2. **Sharpness**: Edge clarity, text legibility, blur presence
3. **Color**: Color accuracy, white balance, saturation

Respond ONLY with JSON: {"overall": X.X, "sharpness": X.X, "color": X.X}
```

### Track B Training Configuration

| Parameter | Qwen3-VL-8B | InternVL3-8B |
|-----------|-------------|--------------|
| **Role** | Generalist Anchor | Overall Specialist |
| Method | LoRA | LoRA |
| LoRA Rank | 16 | 16 |
| LoRA Alpha | 32 | 32 |
| Epochs | 3 | 3 |
| Batch Size | 4 (grad_accum=8) | 4 (grad_accum=8) |
| Learning Rate | 2e-4 | 2e-4 |
| Loss Weights | [0.34, 0.33, 0.33] | [**0.6**, 0.2, 0.2] |
| Checkpoint Select | SRCC_mean | SRCC_overall |
| GPU | A100-80GB | A100-80GB |
| Est. Time | 6-8 hrs | 6-8 hrs |

### Performance Targets (Post Fine-Tuning)

> **Note**: These are targets for fine-tuned models. Base model benchmarks show SRCC ~0.1-0.3.

| Model | Role | Target SRCC | Target ECE |
|-------|------|-------------|------------|
| Qwen3-VL-8B | Generalist | > 0.90 (all dims) | < 0.08 |
| InternVL3-8B | Overall Specialist | > 0.88 (overall) | < 0.08 |

### Output Artifacts

```text
gs://image_detection_b/models/diqa/track_b_vlm/
├── qwen3_vl_8b/v1.0.0/
│   ├── adapter_model.safetensors  # LoRA weights only
│   ├── adapter_config.json
│   └── MODEL_CARD.md
└── internvl3_8b/v1.0.0/
    ├── adapter_model.safetensors
    ├── adapter_config.json
    └── MODEL_CARD.md
```

---

## 5. Pseudo-Label Generation Workflow

### Purpose

Use trained models to generate DIQA-style quality labels for unlabeled document datasets at scale.

### Ensemble Architecture (5 Models)

| Model | Track | Role | Contribution |
|-------|-------|------|--------------|
| **Qwen3-VL-8B** | B (VLM) | Generalist Anchor | Primary for all dimensions |
| **DocIQ-Replica** | A (IQA) | **Generalist Anchor** | Primary for all dimensions |
| **MUSIQ** | A (IQA) | Sharpness Specialist | Primary for sharpness |
| **QualiCLIP** | A (IQA) | Color Specialist | Primary for color |
| **InternVL3-8B** | B (VLM) | Overall Specialist | Primary for overall |

> **Two Generalist Anchors**: The ensemble has two generalist anchors—one per track (Qwen3-VL-8B for VLMs,
> DocIQ-Replica for IQA). This provides balanced predictions from both perspectives, with specialists
> refining dimension-specific assessments.

### Per-Dimension Ensemble Weights

```python
ENSEMBLE_WEIGHTS = {
    'overall': {
        'qwen3_vl_8b': 0.30,     # Generalist anchor (VLM)
        'dociq_replica': 0.20,   # Generalist anchor (IQA)
        'musiq': 0.10,           # Off-specialty
        'qualiclip': 0.10,       # Off-specialty
        'internvl3_8b': 0.30,    # Overall specialist
    },
    'sharpness': {
        'qwen3_vl_8b': 0.15,     # Generalist anchor (VLM)
        'dociq_replica': 0.20,   # Generalist anchor (IQA)
        'musiq': 0.35,           # Sharpness specialist
        'qualiclip': 0.10,       # Off-specialty
        'internvl3_8b': 0.20,    # Off-specialty
    },
    'color': {
        'qwen3_vl_8b': 0.20,     # Generalist anchor (VLM)
        'dociq_replica': 0.20,   # Generalist anchor (IQA)
        'musiq': 0.10,           # Off-specialty
        'qualiclip': 0.40,       # Color specialist
        'internvl3_8b': 0.10,    # Off-specialty
    },
}
```

### Uncertainty Computation (Within-Dimension Variance)

> **CRITICAL**: Uncertainty is computed as **within-dimension model variance**, NOT cross-dimension divergence.

**Correct approach:**

```python
def compute_uncertainty(
    model_predictions: dict[str, dict[str, float]],
    dimension: str,
    specialist_indices: list[str]
) -> float:
    """
    Uncertainty = variance of specialist predictions for the SAME dimension.
    High variance = models disagree = high uncertainty.

    Example for sharpness dimension:
    - Qwen3-VL-8B predicts 4.2
    - DocIQ-Replica predicts 4.0
    - MUSIQ predicts 3.8
    → variance = 0.027 (low uncertainty, models agree)
    """
    specialist_preds = [
        model_predictions[model][dimension]
        for model in specialist_indices
    ]
    return np.var(specialist_preds)
```

**Why NOT cross-dimension divergence:**

Cross-dimension divergence (e.g., `abs(sharpness - color)`) often signals **truth**, not uncertainty.
A sharp black-and-white document might have Sharpness=5.0 but Color=1.0—this is correct, not uncertain.

### Stacker Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│              Hierarchical Stacker with Uncertainty               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT: All model predictions [5 models × 3 dimensions]         │
│                           ↓                                      │
│  WITHIN-DIMENSION VARIANCE COMPUTATION                           │
│  ├─ overall_var = var([qwen, dociq, internvl] on overall)       │
│  ├─ sharpness_var = var([qwen, dociq, musiq] on sharpness)      │
│  └─ color_var = var([qwen, dociq, qualiclip] on color)          │
│                           ↓                                      │
│  PER-DIMENSION ENCODERS                                          │
│  └─ Linear(5 → 32) for each dimension                           │
│                           ↓                                      │
│  VARIANCE ENCODER                                                │
│  └─ Linear(3 → 32) encoding uncertainty signal                  │
│                           ↓                                      │
│  FUSION                                                          │
│  └─ Concat → Linear(64 → 32) → ReLU → Linear(32 → 2)           │
│                           ↓                                      │
│  OUTPUT (per dimension):                                         │
│  ├─ pred: Calibrated quality score (1-5)                        │
│  └─ var: Predicted variance (uncertainty estimate)              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Workflow Commands

```bash
# Generate labels for local images
uv run modal run modal/generate_pseudo_labels.py \
    --input-dir ./data/images \
    --output-dir ./data/labels

# Generate labels from GCS bucket
uv run modal run modal/generate_pseudo_labels.py \
    --gcs-bucket my-bucket \
    --gcs-prefix documents/ \
    --output-dir ./data/labels
```

### Output Schema

```json
{
  "image_id": "doc_001.jpg",
  "overall_score": 4.2,
  "sharpness_score": 3.8,
  "color_score": 4.5,
  "overall_uncertainty": 0.15,
  "sharpness_uncertainty": 0.22,
  "color_uncertainty": 0.11,
  "model_predictions": {
    "qwen3_vl_8b": {"overall": 4.1, "sharpness": 3.9, "color": 4.4},
    "dociq_replica": {"overall": 4.0, "sharpness": 3.7, "color": 4.3},
    "musiq": {"overall": 4.2, "sharpness": 3.8, "color": 4.5},
    "qualiclip": {"overall": 4.3, "sharpness": 3.6, "color": 4.6},
    "internvl3_8b": {"overall": 4.2, "sharpness": 3.9, "color": 4.4}
  },
  "within_dim_variances": {
    "overall": 0.012,
    "sharpness": 0.048,
    "color": 0.006
  },
  "high_uncertainty": false,
  "model_disagreement": false,
  "inference_time_ms": 423,
  "timestamp": "2025-12-18T10:30:00Z"
}
```

---

## 6. Model Quantization Workflow

### Purpose

Compress models for production deployment while maintaining acceptable accuracy degradation.

### Quantization Methods

| Model Type | Method | Bits | Expected SRCC Loss |
|------------|--------|------|-------------------|
| VLM (72B+) | GPTQ/AWQ | 4/8 | < 1.5% |
| IQA CNN | PTQ | 8 | < 0.5% |
| CLIP-based | PTQ | 8 | < 0.8% |

### Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                  Quantization Pipeline                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. MODEL INTAKE                                                 │
│     └─ Load full-precision model from HuggingFace/local         │
│                                                                  │
│  2. CALIBRATION                                                  │
│     ├─ Select calibration dataset (128-1000 samples)            │
│     └─ Run forward passes to collect activation statistics      │
│                                                                  │
│  3. QUANTIZATION                                                 │
│     ├─ Apply quantization recipe (GPTQ/AWQ/PTQ)                 │
│     └─ Generate quantized weights                                │
│                                                                  │
│  4. VALIDATION                                                   │
│     ├─ Smoke test: Load and run inference                       │
│     └─ Quality check: Compare SRCC vs full-precision            │
│                                                                  │
│  5. PACKAGING                                                    │
│     ├─ Export safetensors format                                 │
│     ├─ Generate quantization_config.json                        │
│     └─ Create MANIFEST.yaml with metadata                       │
│                                                                  │
│  6. PUBLISHING                                                   │
│     └─ Upload to HuggingFace private repo                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. End-to-End Model Selection Pipeline

### Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│               Model Selection Decision Tree                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  START: Benchmark all candidate models on DIQA-5000 test        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PHASE 1: Base Model Evaluation                           │   │
│  │  ├─ Run IQA benchmarks (ResNet, ConvNeXt, Swin, etc.)    │   │
│  │  ├─ Run VLM benchmarks (Qwen, InternVL, etc.)            │   │
│  │  └─ Compute metrics + 95% CIs                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PHASE 2: Selection Criteria                              │   │
│  │  ├─ SRCC > 0.90 on Overall dimension?                    │   │
│  │  ├─ CI width < 0.10? (statistical significance)          │   │
│  │  └─ Inference time < 500ms? (production viable)          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│           ┌──────────────┴──────────────┐                       │
│           │                             │                        │
│           ▼                             ▼                        │
│  ┌─────────────────┐          ┌─────────────────┐               │
│  │  MEETS CRITERIA │          │ BELOW CRITERIA  │               │
│  │  → Production   │          │ → Fine-tune     │               │
│  │    candidate    │          │   candidate     │               │
│  └─────────────────┘          └─────────────────┘               │
│           │                             │                        │
│           ▼                             ▼                        │
│  ┌─────────────────┐          ┌─────────────────┐               │
│  │  PHASE 3A:      │          │  PHASE 3B:      │               │
│  │  Quantize       │          │  Fine-tune on   │               │
│  │  (Project B)    │          │  DIQA-5000      │               │
│  │                 │          │  (Project C)    │               │
│  └─────────────────┘          └─────────────────┘               │
│           │                             │                        │
│           └──────────────┬──────────────┘                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PHASE 4: Final Evaluation                                │   │
│  │  ├─ Re-benchmark quantized/fine-tuned models             │   │
│  │  ├─ Compare to baseline                                   │   │
│  │  └─ Select best model for production                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PHASE 5: Pseudo-Label Generation                         │   │
│  │  ├─ Deploy selected models as ensemble                    │   │
│  │  └─ Generate labels for unlabeled datasets                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Metrics Reference

### Correlation Metrics

| Metric | Full Name | Range | Direction | Use Case |
|--------|-----------|-------|-----------|----------|
| PLCC | Pearson Linear Correlation Coefficient | [-1, 1] | Higher is better | Linear relationship |
| SRCC | Spearman Rank Correlation Coefficient | [-1, 1] | Higher is better | Rank ordering |

### Error Metrics

| Metric | Full Name | Range | Direction | Use Case |
|--------|-----------|-------|-----------|----------|
| MAE | Mean Absolute Error | [0, ∞) | Lower is better | Average deviation |
| RMSE | Root Mean Squared Error | [0, ∞) | Lower is better | Penalizes large errors |

### Expected Calibration Error (ECE) for Regression

For 1-5 regression scores, ECE measures how well predicted uncertainties match actual errors:

```python
def compute_regression_ece(
    predictions: np.ndarray,
    targets: np.ndarray,
    uncertainties: np.ndarray,
    n_bins: int = 10
) -> float:
    """
    Expected Calibration Error for regression with uncertainty estimates.

    For well-calibrated predictions:
    - Predicted uncertainty should match empirical error
    - Within each confidence bin, RMSE ≈ mean predicted std

    Args:
        predictions: Model predictions [N]
        targets: Ground truth values [N]
        uncertainties: Predicted standard deviations [N]
        n_bins: Number of confidence bins

    Returns:
        ECE score (lower is better, 0 = perfectly calibrated)
    """
    # Bin by predicted uncertainty
    bin_edges = np.linspace(uncertainties.min(), uncertainties.max(), n_bins + 1)

    ece = 0.0
    total_samples = len(predictions)

    for i in range(n_bins):
        mask = (uncertainties >= bin_edges[i]) & (uncertainties < bin_edges[i + 1])
        n_in_bin = mask.sum()
        if n_in_bin == 0:
            continue

        # Expected: mean predicted uncertainty in bin
        expected_error = uncertainties[mask].mean()

        # Actual: RMSE of predictions in bin
        actual_error = np.sqrt(((predictions[mask] - targets[mask]) ** 2).mean())

        # Weighted absolute difference
        ece += (n_in_bin / total_samples) * abs(expected_error - actual_error)

    return ece
```

**Target**: ECE < 0.08 for all models

### Confidence Intervals

- **Method**: Bootstrap resampling (1000 iterations)
- **Confidence Level**: 95%
- **Seed**: 42 (reproducibility)
- **Minimum samples**: 30 (for valid bootstrap)

### Checkpoint Selection Algorithm

> **Strategy**: SRCC-primary selection with weighted ECE consideration. Within a configurable SRCC band,
> checkpoints compete on a combined score that allows trading small SRCC losses for significant ECE gains.

```python
def select_best_checkpoint(
    checkpoints: list[dict],
    specialty: str,
    srcc_weight: float = 0.7,
    ece_weight: float = 0.3,
    srcc_band: float = 0.02,
) -> dict:
    """
    Select checkpoint using weighted SRCC + ECE scoring.

    Within the SRCC band (default ±0.02 from best), checkpoints compete on
    a weighted score. This allows giving up a little SRCC (e.g., 0.01) for
    a significant ECE improvement (e.g., 0.05 → 0.03).

    Args:
        checkpoints: List of checkpoint metrics dicts
        specialty: 'overall', 'sharpness', 'color', or 'mean' (for generalists)
        srcc_weight: Weight for SRCC in combined score (default 0.7)
        ece_weight: Weight for ECE in combined score (default 0.3)
        srcc_band: SRCC tolerance band from best (default 0.02)
    """
    # Find best SRCC
    best_srcc = max(c[f'srcc_{specialty}'] for c in checkpoints)

    # Score checkpoints within band
    scored = []
    for c in checkpoints:
        srcc = c[f'srcc_{specialty}']
        ece = c['ece_mean']

        # Exclude checkpoints outside SRCC band
        if srcc < best_srcc - srcc_band:
            continue

        # Normalize and combine scores
        srcc_norm = (srcc - (best_srcc - srcc_band)) / srcc_band
        ece_norm = max(0, min(1, 1 - (ece / 0.15)))
        score = srcc_weight * srcc_norm + ece_weight * ece_norm

        scored.append((c, score))

    return max(scored, key=lambda x: x[1])[0]
```

**Configuration Presets:**

| Preset | SRCC Weight | ECE Weight | SRCC Band | Use Case |
|--------|-------------|------------|-----------|----------|
| **SRCC-Dominant** | 0.8 | 0.2 | 0.015 | When ranking accuracy is critical |
| **Balanced** (default) | 0.7 | 0.3 | 0.02 | General-purpose pseudo-labeling |
| **Calibration-Aware** | 0.6 | 0.4 | 0.025 | When uncertainty estimates matter |

---

## 9. Infrastructure Reference

### Modal GPU Options

| GPU | VRAM | Use Case | Cost/hour |
|-----|------|----------|-----------|
| T4 | 16GB | IQA benchmarking, small VLMs | ~$0.40 |
| A10 | 24GB | Medium VLMs, training | ~$1.00 |
| A100-40GB | 40GB | Large VLMs | ~$3.00 |
| A100-80GB | 80GB | 72B+ models, ensemble | ~$4.50 |

### GCS Buckets

| Bucket | Contents |
|--------|----------|
| `assured-oss-457903-diqa5000` | DIQA-5000 dataset |
| `image_detection_b` | Model checkpoints, artifacts |

### Modal Secrets

| Secret Name | Contents |
|-------------|----------|
| `gcs-credentials` | Base64-encoded GCP service account JSON |

---

## 10. File Reference

### Benchmarking Scripts

| File | Purpose |
|------|---------|
| `modal/arena_iqa_benchmark.py` | IQA model benchmarking |
| `modal/arena_vlm_benchmark.py` | VLM model benchmarking |
| `modal/arena_benchmark.py` | Base VLM inference |
| `modal/arena_full_benchmark.py` | Full DIQA-5000 evaluation |

### Training Scripts

| File | Purpose |
|------|---------|
| `modal/train_phase2_iqa.py` | IQA teacher training |
| `modal/train_student_distillation.py` | Student KD training |
| `modal/generate_pseudo_labels.py` | Pseudo-label generation |
| `modal/teacher_inference.py` | Teacher inference endpoint |
| `modal/export_phase7_onnx.py` | ONNX model export |

### Supporting Scripts

| File | Purpose |
|------|---------|
| `scripts/annotate_base_metadata.py` | Three-layer metadata annotation |
| `scripts/build_training_labels.py` | Training label generation |
| `scripts/upload_diqa5000_to_gcs.py` | Dataset upload to GCS |

---

## Appendix A: Quick Reference Commands

```bash
# === BENCHMARKING ===
# IQA quick test
uv run modal run modal/arena_iqa_benchmark.py::run_resnet50_benchmark --num-samples 10

# IQA full benchmark (detached)
uv run modal run -d modal/arena_iqa_benchmark.py::run_resnet50_benchmark

# PyIQA benchmarks
uv run modal run modal/arena_iqa_benchmark.py::run_pyiqa_benchmark --metric-name musiq
uv run modal run modal/arena_iqa_benchmark.py::run_pyiqa_benchmark --metric-name qualiclip

# VLM quick test
uv run modal run modal/arena_vlm_benchmark.py::run_qwen3_vl_8b_benchmark --num-samples 10

# === TRAINING (Track A) ===
# Sub-Track A1: Fine-tune MUSIQ
uv run modal run --detach modal/train_musiq_finetune.py

# Sub-Track A2: Fine-tune QualiCLIP
uv run modal run --detach modal/train_qualiclip_finetune.py

# Sub-Track A3: Train DocIQ-Replica from scratch
uv run modal run --detach modal/train_dociq_replica.py

# === TRAINING (Track B) ===
# Qwen3-VL-8B LoRA fine-tuning
uv run modal run --detach modal/train_qwen3_lora.py

# InternVL3-8B LoRA fine-tuning
uv run modal run --detach modal/train_internvl3_lora.py

# === PSEUDO-LABELING ===
# Generate labels
uv run modal run modal/generate_pseudo_labels.py --input-dir ./data/images

# === MONITORING ===
# Check running apps
uv run modal app list

# View logs
uv run modal app logs <app-id>
```

---

## Appendix B: Model Versioning and Storage

### Model Naming Convention

**Format:** `{task}_{architecture}_{variant}_v{major}.{minor}.{patch}`

| Component | Description | Examples |
|-----------|-------------|----------|
| `task` | Primary task | `diqa`, `iqa`, `vlm` |
| `architecture` | Model architecture | `resnet50`, `musiq`, `qwen3vl8b` |
| `variant` | Specialization | `sharpness`, `color`, `overall`, `generalist` |
| `version` | Semantic version | `v1.0.0`, `v1.2.3` |

**Examples:**

```text
diqa_resnet50_generalist_v1.0.0     # DocIQ-Replica (generalist anchor)
diqa_musiq_sharpness_v1.0.0         # Fine-tuned MUSIQ
diqa_qualiclip_color_v1.0.0         # Fine-tuned QualiCLIP
diqa_qwen3vl8b_generalist_v1.0.0    # LoRA fine-tuned Qwen3-VL
diqa_internvl3_overall_v1.0.0       # LoRA fine-tuned InternVL3
diqa_stacker_ensemble_v1.0.0        # Trained stacker weights
```

### Storage Structure

```text
gs://image_detection_b/models/diqa/
├── track_a_iqa/
│   ├── dociq_replica/
│   │   ├── v1.0.0/
│   │   │   ├── model.pt
│   │   │   ├── model.onnx
│   │   │   ├── config.json
│   │   │   └── MODEL_CARD.md
│   │   └── v1.1.0/
│   │       └── ...
│   ├── musiq/
│   │   └── v1.0.0/
│   │       ├── model.pt
│   │       ├── config.json
│   │       └── MODEL_CARD.md
│   └── qualiclip/
│       └── v1.0.0/
│           └── ...
├── track_b_vlm/
│   ├── qwen3_vl_8b/
│   │   └── v1.0.0/
│   │       ├── adapter_model.safetensors  # LoRA weights only
│   │       ├── adapter_config.json
│   │       └── MODEL_CARD.md
│   └── internvl3_8b/
│       └── v1.0.0/
│           └── ...
├── stacker/
│   └── v1.0.0/
│       ├── stacker.pt
│       ├── temperature_scales.json
│       └── MODEL_CARD.md
└── benchmarks/
    └── diqa5000_results.csv
```

### Model Card Template

Each trained model MUST have a `MODEL_CARD.md` file with:

- **Model Details**: ID, track, architecture, parameters, precision, input size
- **Training Details**: Dataset, epochs, batch size, learning rate, optimizer, GPU, training time
- **Performance Metrics**: DIQA-5000 SRCC/PLCC/ECE per dimension with 95% CIs
- **Inference Performance**: Latency on T4/A10G, memory usage
- **Intended Use**: Primary use case, secondary uses, out of scope
- **Limitations**: Known limitations and edge cases
- **Lineage**: Base model, parent version, training script, commit SHA

### Version Promotion Workflow

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     Model Version Promotion                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. TRAINING (dev/)                                                     │
│     └─ Train model, save to gs://.../dev/{model}/                      │
│                                                                         │
│  2. VALIDATION (staging/)                                               │
│     ├─ Run DIQA-5000 benchmark                                          │
│     ├─ Check SRCC > threshold                                           │
│     ├─ Check ECE < 0.08                                                 │
│     └─ If pass → promote to staging/                                    │
│                                                                         │
│  3. INTEGRATION TEST (staging/)                                         │
│     ├─ Run ensemble with all models                                     │
│     ├─ Validate stacker performance                                     │
│     └─ If pass → promote to prod/                                       │
│                                                                         │
│  4. PRODUCTION (prod/)                                                  │
│     ├─ Copy to versioned directory                                      │
│     ├─ Update MODEL_CARD.md                                             │
│     └─ Tag in model registry                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix C: Performance Targets Summary

### Target Metrics (Post Fine-Tuning)

> **Important**: These targets are for **fine-tuned models**. Base model benchmarks show SRCC ~0.1-0.3.
> See `docs/benchmarks/diqa5000_benchmark_results.csv` for current baseline performance.

| Model | Track | Role | Target SRCC | Target ECE | Notes |
|-------|-------|------|-------------|------------|-------|
| Qwen3-VL-8B | B (VLM) | Generalist Anchor | > 0.90 (all dims) | < 0.08 | LoRA fine-tuned |
| DocIQ-Replica | A (IQA) | **Generalist Anchor** | > 0.85 (all dims) | < 0.08 | Trained from scratch |
| MUSIQ | A (IQA) | Sharpness Specialist | > 0.88 (sharpness) | < 0.08 | Fine-tuned |
| QualiCLIP | A (IQA) | Color Specialist | > 0.85 (color) | < 0.08 | Fine-tuned |
| InternVL3-8B | B (VLM) | Overall Specialist | > 0.88 (overall) | < 0.08 | LoRA fine-tuned |

### Ensemble Target Metrics

| Metric | Target | Priority |
|--------|--------|----------|
| SRCC (vs human ratings) | > 0.94 | **Critical** |
| Expected Calibration Error (ECE) | < 0.08 | **Critical** |
| SRCC 95% CI Width | < 0.03 | High |
| Inference Latency | < 500ms/image | Low (acceptable) |

### Baseline Performance (No Fine-Tuning)

| Model | Overall PLCC | Overall SRCC | Sharpness PLCC | Color PLCC |
|-------|-------------|--------------|----------------|------------|
| PyIQA-QualiCLIP | 0.2216 | 0.1038 | 0.3070 | 0.2153 |
| PyIQA-MUSIQ | 0.2098 | 0.1158 | 0.3074 | 0.2080 |
| ResNet18-ImageNet-IQA | 0.0963 | 0.0905 | -0.0205 | -0.0071 |
| Swin-Tiny-ImageNet-IQA | 0.0474 | 0.0798 | -0.1270 | 0.0311 |

> **Conclusion**: All models require fine-tuning on DIQA-5000 to achieve target performance.

---

*Last Updated: 2025-12-18*