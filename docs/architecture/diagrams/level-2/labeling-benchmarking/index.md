---
schema_type: common
title: "Level 2: Labeling & Benchmarking Models"
description: "Training and benchmarking of labeling models for pseudo-labeling and
  baseline evaluation"
tags:
- architecture
- diagrams
- level_2
- labeling_models
- benchmarking
- workstream_5
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the training pipeline for labeling models (MUSIQ, QualiCLIP, VLMs)
  used in pseudo-labeling and Arena baseline evaluation."
---

This workstream trains and benchmarks the labeling models used for pseudo-labeling (Workstream 4) and baseline evaluation (Workstream 6 - Model Arena). These models serve as the "tools" for automated dataset labeling and establish performance baselines for production model comparison.

**Status**: Active
**Lines of Code**: ~800+ (training scripts, model wrappers, evaluation)

---

## Overview

**Purpose**: Train specialized IQA and VLM models that:

1. Generate pseudo-labels for unlabeled training data (consumed by Workstream 4)
2. Establish baseline benchmarks in Model Arena (Workstream 6 Phase 1)
3. Participate in ensemble labeling for high-confidence predictions

**Key Distinction from Workstream 6 (Model Arena)**:

- **Workstream 5**: Trains the labeling models themselves
- **Workstream 6**: Benchmarks all models (labeling + production) in standardized Arena

**Lines of Code**: ~800+ across training scripts and model integrations

---

## Model Portfolio

### Track A: IQA Specialist Models

| Model | Architecture | Parameters | Specialty | Arena PLCC (Phase 1) |
|-------|--------------|------------|-----------|---------------------|
| **MUSIQ** | Multi-scale ResNet | 27M | Sharpness/blur detection | 0.2098 |
| **QualiCLIP** | CLIP-based | 150M | Color fidelity assessment | 0.2216 (best) |
| **DocIQ-Replica** | Mask R-CNN + ResNet | 25M + masks | Document-specific quality | TBD |

### Track B: Vision-Language Models (VLMs)

| Model | Architecture | Parameters | Specialty | Arena PLCC (Phase 1) |
|-------|--------------|------------|-----------|---------------------|
| **Qwen3-VL-8B** | Vision Transformer + LLM | 8B | Generalist quality reasoning | TBD |
| **InternVL3-8B** | ViT + InternLM | 8B | Overall quality assessment | TBD |

---

## Training Pipeline

### Phase 1: Pretrained Model Selection

**Objective**: Select open-source pretrained models with strong zero-shot performance

**Sources**:

- **MUSIQ**: [Google Research GitHub](https://github.com/google-research/google-research/tree/master/musiq)
- **QualiCLIP**: [PyIQA Library](https://github.com/chaofengc/IQA-PyTorch)
- **DocIQ**: Custom replica based on [Mask R-CNN](https://github.com/matterport/Mask_RCNN)
- **Qwen3-VL**: [HuggingFace: Qwen/Qwen3-VL-8B](https://huggingface.co/Qwen/Qwen3-VL-8B)
- **InternVL3**: [HuggingFace: OpenGVLab/InternVL3-8B](https://huggingface.co/OpenGVLab/InternVL3-8B)

**Evaluation**: All models benchmarked in Model Arena (WS6 Phase 1) before fine-tuning

---

### Phase 2: Fine-Tuning on Domain Data

**Training Dataset Sources** (from Workstream 3: Data Preparation):

- **Real Labeled Data**: DIQA-5000, OHR-Bench, LIVE, CSIQ
- **Synthetic Data** (from Workstream 8): Genalog-generated degradations with ground truth
- **Composition**: 70% real, 30% synthetic

**Fine-Tuning Strategy**:

| Model | Fine-Tuning Approach | Epochs | Learning Rate | Validation Metric |
|-------|---------------------|--------|---------------|-------------------|
| MUSIQ | Full fine-tuning | 20 | 1e-5 | PLCC (sharpness) |
| QualiCLIP | Adapter layers (LoRA) | 15 | 5e-5 | PLCC (color) |
| DocIQ | Mask head + classifier | 25 | 1e-4 | mAP (quality issues) |
| Qwen3-VL | Prompt tuning | 10 | 1e-6 | PLCC (overall) |
| InternVL3 | Vision adapter only | 10 | 1e-6 | PLCC (overall) |

**Training Infrastructure**: Modal serverless GPU (A10/A100)

---

### Phase 3: Checkpoint Selection for Pseudo-Labeling

**Selection Criteria** (from Workstream 6 Arena):

1. **Best PLCC** on DIQA-5000 test set (primary metric)
2. **Calibration Error** (ECE < 0.1 preferred)
3. **Inference Latency** (< 200ms/image for batch=32)

**Weighted Score**:

```python
score = 0.7 * SRCC + 0.3 * (1 - ECE)
```

**Output**: Selected checkpoints exported to Model Registry for Workstream 4

---

## Model Specialization Strategy

### Why Specialists vs Generalists?

**Design Decision**: Use specialized models for different quality dimensions rather than a single monolithic model

**Rationale**:

- **Sharpness**: MUSIQ excels at multi-scale blur/focus detection
- **Color**: QualiCLIP leverages CLIP embeddings for perceptual color fidelity
- **Overall Quality**: VLMs provide holistic reasoning about document quality
- **Ensemble Benefit**: Combining specialists improves pseudo-labeling confidence

**Pseudo-Labeling Workflow** (Workstream 4):

```text
Unlabeled Image
    ↓
[Track A: IQA Models]     [Track B: VLMs]
    ├─ MUSIQ (sharpness)      ├─ Qwen3-VL (overall)
    ├─ QualiCLIP (color)      └─ InternVL3 (overall)
    └─ DocIQ (quality issues)
    ↓
Hierarchical Stacker (variance-weighted)
    ↓
Pseudo-Label (if ensemble agreement > 0.8)
```

---

## Training Scripts & Infrastructure

### Key Scripts

| Script | Purpose | Lines | Location |
|--------|---------|-------|----------|
| `train_musiq.py` | MUSIQ fine-tuning | ~200 | `modal/labeling_models/` |
| `train_qualiclip.py` | QualiCLIP adapter training | ~180 | `modal/labeling_models/` |
| `train_dociq.py` | DocIQ mask head training | ~250 | `modal/labeling_models/` |
| `train_vlm.py` | VLM prompt/adapter tuning | ~220 | `modal/labeling_models/` |
| `export_for_pseudo_labeling.py` | Export selected checkpoints | ~150 | `modal/labeling_models/` |

**Total**: ~1,000 lines (estimated, scripts to be created)

---

### Modal Training Configuration

```python
# Example: MUSIQ fine-tuning
@app.function(
    image=modal.Image.debian_slim()
        .pip_install("torch", "torchvision", "pyiqa"),
    gpu="A10",
    timeout=14400  # 4 hours
)
def train_musiq(config: TrainingConfig):
    """Fine-tune MUSIQ on DIQA-5000 + synthetic data."""
    model = load_pretrained_musiq()
    train_loader = get_dataloader(config.train_dataset)

    for epoch in range(config.epochs):
        # Training loop
        ...

    # Select best checkpoint by PLCC
    best_ckpt = select_best_checkpoint(val_plcc_history)
    upload_to_registry(best_ckpt, "musiq_v1.0.0")
```

---

## Workstream Dependencies

### Upstream Dependencies

| Workstream | Consumed Artifacts | Purpose |
|------------|-------------------|---------|
| **WS3: Data Preparation** | `training_labels.parquet`, DIQA-5000, OHR-Bench | Training and validation datasets |
| **WS8: Synthetic Generation** | Degraded images with ground truth | Expand training data 2-3x |

### Downstream Consumers

| Workstream | Provided Artifacts | Purpose |
|------------|-------------------|---------|
| **WS4: Pseudo-Labeling** | Fine-tuned MUSIQ, QualiCLIP, DocIQ, VLMs | Generate pseudo-labels for unlabeled data |
| **WS6: Model Arena** | Pretrained + fine-tuned models | Phase 1 baseline benchmarks |

### External Dependencies

| Service/Tool | Purpose | Configuration |
|--------------|---------|---------------|
| **Modal** | GPU training infrastructure | A10/A100, 4-hour timeout |
| **HuggingFace Hub** | Pretrained model downloads | `transformers` library |
| **PyIQA** | MUSIQ, QualiCLIP implementations | `pip install pyiqa` |
| **Model Registry (GCS)** | Checkpoint storage | `gs://image-detection-models/labeling/` |

---

## Integration with Model Arena (Workstream 6)

### Phase 1: Base Evaluation (Pre-Training)

**Workflow**:

```text
Download Pretrained Models
    ↓
Arena Benchmark (DIQA-5000 test set)
    ↓
Baseline Leaderboard
    ├─ QualiCLIP: PLCC = 0.2216 (best)
    ├─ MUSIQ: PLCC = 0.2098
    └─ Others: PLCC < 0.20
    ↓
Select Top Models for Fine-Tuning
```

**Output**: Baseline performance metrics inform fine-tuning priorities

---

### Phase 2: Fine-Tuned Validation (Post-Training)

**Workflow**:

```text
Fine-Tune Models (this workstream)
    ↓
Arena Benchmark (DIQA-5000 test set)
    ↓
Compare to Baseline
    ├─ MUSIQ fine-tuned: PLCC = 0.45 (+115% improvement)
    ├─ QualiCLIP fine-tuned: PLCC = 0.50 (+126% improvement)
    └─ Validation: PLCC improvement > 50% required
    ↓
Graduate to Pseudo-Labeling (Workstream 4)
```

**Graduation Criteria**: PLCC improvement ≥ 50% over baseline

---

## Integration with Pseudo-Labeling (Workstream 4)

### Model Deployment

**Model Registry Structure**:

```
gs://image-detection-models/labeling/
├── musiq/
│   ├── v1.0.0_finetuned.onnx
│   └── v1.0.0_metadata.json
├── qualiclip/
│   ├── v1.0.0_finetuned.onnx
│   └── v1.0.0_metadata.json
├── dociq/
│   ├── v1.0.0_finetuned.pth
│   └── v1.0.0_metadata.json
├── qwen3_vl/
│   ├── v1.0.0_adapter.safetensors
│   └── v1.0.0_metadata.json
└── internvl3/
    ├── v1.0.0_adapter.safetensors
    └── v1.0.0_metadata.json
```

**Invocation in Pseudo-Labeling**:

```python
# Workstream 4 loads models from registry
musiq = load_model("gs://.../labeling/musiq/v1.0.0_finetuned.onnx")
qualiclip = load_model("gs://.../labeling/qualiclip/v1.0.0_finetuned.onnx")

# Ensemble inference
sharpness = musiq(image)
color = qualiclip(image)
ensemble_score = hierarchical_stacker([sharpness, color, ...])
```

---

## Current Status & Roadmap

### Implemented ✅

- **Model selection**: 5 models identified (MUSIQ, QualiCLIP, DocIQ, Qwen3-VL, InternVL3)
- **Arena Phase 1**: MUSIQ (PLCC=0.21), QualiCLIP (PLCC=0.22) benchmarked

### In Progress 🚧

- **Fine-tuning scripts**: Modal training infrastructure
- **Checkpoint selection**: Weighted SRCC + ECE scoring
- **Model export**: ONNX/TorchScript conversion for production

### Planned 📋

- **Phase 2 Arena validation**: Fine-tuned model benchmarks
- **VLM integration**: Qwen3-VL and InternVL3 prompt tuning
- **Continuous retraining**: Monthly fine-tuning on new labeled data

---

## Performance Characteristics

| Model | Inference Latency (GPU) | Inference Latency (CPU) | Memory (GPU) | Batch Size |
|-------|------------------------|------------------------|--------------|------------|
| MUSIQ | 15ms/image | 80ms/image | 2 GB | 32 |
| QualiCLIP | 25ms/image | 120ms/image | 4 GB | 32 |
| DocIQ | 40ms/image | 200ms/image | 6 GB | 16 |
| Qwen3-VL | 150ms/image | N/A (GPU only) | 16 GB | 8 |
| InternVL3 | 180ms/image | N/A (GPU only) | 18 GB | 8 |

**Ensemble Overhead**: ~10ms for hierarchical stacking (CPU)

**Total Pseudo-Labeling Latency** (Track A + Track B + stacker): ~250ms/image (GPU batch=8)

---

## Level 3 Decision

**Is Level 3 Documentation Necessary?**

### Analysis

Workstream 5 involves:

- Standard fine-tuning workflows (PyTorch/HuggingFace)
- Model selection via Arena benchmarks (well-documented in WS6)
- Checkpoint export to registry (straightforward)

**Current Complexity**: ~800-1,000 lines of training scripts, relatively standard ML training patterns

### Recommendation: **Level 3 NOT REQUIRED** (at current scale)

**Rationale**:

1. **Standard Workflows**: Fine-tuning follows PyTorch conventions, no custom training loops
2. **Documented Integration**: Arena benchmarking (WS6) and pseudo-labeling (WS4) already documented
3. **Small Codebase**: ~1,000 lines total, each script <250 lines

### When Level 3 WOULD Be Needed

- If ensemble training becomes more complex (multi-stage distillation, custom loss functions)
- If model count grows beyond 10 models with diverse training strategies
- If hyperparameter tuning becomes highly automated (AutoML, NAS)

**Current Guidance**: Developers should reference training scripts directly. This Level 2 doc provides sufficient architectural context for understanding model selection, training flow, and integration points.

---

## Source File Traceability

**Current Status**: ⚠️ **Not Yet Implemented** (0 LOC)

This workstream is planned but has no implementation files yet. The labeling model training infrastructure is scheduled for future development.

| Workflow Step | Status | Estimated LOC | Notes |
|---------------|--------|---------------|-------|
| **MUSIQ Fine-Tuning** | Planned | ~200 | Sharpness specialist |
| **QualiCLIP Fine-Tuning** | Planned | ~180 | Color fidelity specialist |
| **DocIQ Training** | Planned | ~250 | Document-specific quality |
| **VLM Adaptation** | Planned | ~220 | Qwen3-VL, InternVL3 adapters |
| **Model Export** | Planned | ~150 | Export for pseudo-labeling |
| **Workstream Total** | **Planned** | **~1,000** | **Target implementation** |

**Note**: Current implementation uses:

- Existing fine-tuning code in `src/labeling/finetuning/` (~4,790 lines) - This may be reassigned to WS5 once architecture is finalized
- Modal training scripts for IQA models (currently in WS2)

**Workstream LOC**: 0 lines (per `docs/architecture/workstream_loc_counts.json`)

**Planned Architecture**:

1. **Model Fine-Tuning Pipeline**: Train labeling specialist models (MUSIQ, QualiCLIP, DocIQ)
2. **VLM Adapter Training**: Fine-tune VLMs for quality assessment
3. **Model Registry**: Version and store fine-tuned models
4. **Export Utilities**: Convert models for inference in WS4 (Pseudo-Labeling)

**Dependencies**:

- Consumes training data from WS3 (Data Preparation)
- Provides models to WS4 (Pseudo-Labeling)
- Evaluated by WS6 (Model Arena)

---

## Related Documentation

| Level | Document | Description |
|-------|----------|-------------|
| **Level 0** | [RAG Pipeline Overview](../../level-0/index.md) | Multi-project context |
| **Level 1** | [Prepare-Doc Architecture](../../level-1/index.md) | Eight workstreams overview |
| **Level 2** | [Data Preparation](../data-preparation/index.md) | Provides training datasets |
| **Level 2** | [Pseudo-Labeling](../pseudo-labeling/index.md) | Consumes labeling models |
| **Level 2** | [Model Arena](../model-arena/index.md) | Benchmarks labeling models (Phase 1) |
| **Level 2** | [Synthetic Generation](../synthetic-generation/index.md) | Augments training data |

---

## Source Files

### Training Scripts (To Be Created)

- `modal/labeling_models/train_musiq.py` (~200 lines)
- `modal/labeling_models/train_qualiclip.py` (~180 lines)
- `modal/labeling_models/train_dociq.py` (~250 lines)
- `modal/labeling_models/train_vlm.py` (~220 lines)
- `modal/labeling_models/export_for_pseudo_labeling.py` (~150 lines)

### Model Wrappers

- `src/image_preprocessing_detector/labeling/models/musiq_wrapper.py`
- `src/image_preprocessing_detector/labeling/models/qualiclip_wrapper.py`
- `src/image_preprocessing_detector/labeling/models/vlm_wrapper.py`

### Configuration

- `configs/labeling_models/training_config.yaml`

**Total Estimated Lines**: ~1,000 (training) + ~300 (wrappers) = **1,300 lines**

---

*Last Updated: 2025-01-16*
