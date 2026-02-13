---
schema_type: common
title: "Level 2: Model Training"
description: "Detailed model training workflow diagrams for Project A"
tags:
- architecture
- diagrams
- plantuml
- level_2
- model_training
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the model training pipeline including the two-model pipeline
  (MobileNetV4-Conv-S + SigLIP 2 NAFlex) and high-level training workflows."
---
This level provides detailed diagrams for the Model Training workstream - training and optimization of production ML models.

---

## Training Workflow - High Level

Overview of the complete model training pipeline from data preparation to model registry.

![Training Workflow High Level](project-a-training-workflow-high-level.svg)

---

## Multi-Task Training Pipeline

Detailed flow of the 3-step virtuous training cycle: MobileNetV4-Conv-S bootstrap, SigLIP 2 multi-task training, and MobileNetV4 distillation refinement.

![Multi-Task Training Pipeline](project-a-distillation.svg)

---

## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| SigLIP 2 NAFlex | `modal/train_siglip2_multitask.py` | Multi-task model (16 heads, 5 groups) |
| MobileNetV4-Conv-S | `modal/train_mobilenetv4.py` | Fast pre-correction gate (3 heads) |
| Docling Layout | Pre-trained (egret-xlarge / heron) | Layout detection (no additional training) |
| ONNX Export | `modal/export_onnx.py` | Production model export (multi-head) |
| Model Registry | GCS bucket | Versioned model storage |

---

## Model Architecture

| Model | Architecture | Parameters | Purpose |
|-------|--------------|------------|---------|
| SigLIP 2 NAFlex | ViT-B/16 (NAFlex packing) | ~88M | Multi-task model: 16 heads across 5 groups (IQA, Script, Orientation+Skew, Handwriting, Page Attrs) |
| MobileNetV4-Conv-S | MobileNetV4-Conv-Small | ~4M | Fast pre-correction gate: 3 heads (orientation, skew, resolution quality), ~3ms GPU |
| Docling Layout (accuracy) | docling-layout-egret-xlarge | ~55M | Layout detection (primary, high accuracy) |
| Docling Layout (speed) | docling-layout-heron | ~14M | Layout detection (fast path) |
| MobileCLIP-2 S4 | MobileCLIP-2 S4 | ~35M | **PLANNED**: Edge/mobile distillation target (deferred) |
| MobileCLIP-2 S0 | MobileCLIP-2 S0 | ~11.4M | **PLANNED**: Ultra-light distillation target (deferred) |

---

## Multi-Task Training Workflow

### 3-Step Virtuous Training Cycle

The training pipeline follows a 3-step virtuous cycle (per [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) Section 9). For optimization strategy (ILP allocation, PCGrad gradient surgery, Kendall uncertainty weighting, phased head training), see [TRAINING_OPTIMIZATION_PLAN.md](../../../planning/TRAINING_OPTIMIZATION_PLAN.md).

| Step | Model | Dataset | Strategy | Loss Function | Graduation Thresholds |
|------|-------|---------|----------|---------------|----------------------|
| **1. MobileNetV4 Bootstrap** | MobileNetV4-Conv-S (~4M) | Orientation (50K), Skew (40K), Resolution (30K) | Train on synthetic ground truth labels | Multi-task: CE (orientation) + MSE (skew) + MSE (resolution) | Orientation acc > 95%, Skew MAE < 0.5 deg, Resolution MAE < 0.1 |
| **2. SigLIP 2 Multi-Task** | SigLIP 2 NAFlex (~88M) | All 10 datasets (~503K total) | Frozen backbone + 16 task heads | Weighted multi-task: per-group loss weights | Per-head thresholds (see Graduation Criteria) |
| **3. MobileNetV4 Distillation** | MobileNetV4-Conv-S (~4M) | SigLIP 2 soft labels + hard labels | KL-divergence distillation (T=3) from SigLIP 2 | α×KL(SigLIP2 ‖ MobileNetV4) + (1-α)×Hard | Orientation acc > 98%, Skew MAE < 0.3 deg |

> **PLANNED (Deferred)**: Distillation cascade SigLIP 2 -> MobileCLIP-2 S4 (~35M) -> MobileCLIP-2 S0 (~11.4M) for edge/mobile deployment. Not part of initial training pipeline.

### Step 1: MobileNetV4-Conv-S Bootstrap

**Purpose**: Train the fast pre-correction gate on synthetic ground truth labels for orientation, skew, and resolution quality.

```python
def mobilenetv4_bootstrap_loss(predictions, targets):
    """
    Multi-task loss for MobileNetV4-Conv-S bootstrap training.

    Args:
        predictions: Dict with keys 'orientation', 'skew', 'resolution_quality'
        targets: Dict with ground truth labels

    Returns:
        Weighted combined loss
    """
    # Orientation: 4-class classification (0/90/180/270)
    orientation_loss = F.cross_entropy(
        predictions['orientation'], targets['orientation']
    )

    # Skew: regression (±10 degrees)
    skew_loss = F.mse_loss(
        predictions['skew'], targets['skew']
    )

    # Resolution quality: regression (0-1, character-height-aware)
    resolution_loss = F.mse_loss(
        predictions['resolution_quality'], targets['resolution_quality']
    )

    # Weighted combination
    return 1.0 * orientation_loss + 0.5 * skew_loss + 0.5 * resolution_loss
```

### Step 2: SigLIP 2 Multi-Task Training

**Purpose**: Train all 16 task heads on frozen SigLIP 2 backbone across 5 head groups.

**Head Groups**:

| Group | Heads | Task Type | Dataset Sources |
|-------|-------|-----------|-----------------|
| **G1: IQA** | blur, noise, contrast, compression, illumination, overall | Regression (0-1) | IQA (16K+100K) |
| **G2: Script** | script_class | Classification (108 classes) | Script (108K) |
| **G3: Orientation+Skew** | orientation_class, skew_angle | Classification + Regression | Orientation (50K), Skew (40K) |
| **G4: Handwriting** | has_handwriting, handwriting_ratio, handwriting_confidence | Classification + Regression | Handwriting (60K) |
| **G5: Page Attrs** | capture_method, shadow_severity, warping_severity, resolution_quality | Classification + Regression | Capture (50K), Shadow (15K), Warping (20K), Resolution (30K) |

### Step 3: MobileNetV4 Distillation Refinement

**Purpose**: Re-train MobileNetV4-Conv-S using SigLIP 2 soft labels as teacher for improved accuracy on orientation, skew, and resolution quality.

```python
def mobilenetv4_distillation_loss(
    student_logits, teacher_logits, ground_truth, alpha=0.7, temperature=3.0
):
    """
    KL-divergence distillation from SigLIP 2 to MobileNetV4-Conv-S.

    Args:
        student_logits: MobileNetV4 raw outputs (3 heads)
        teacher_logits: SigLIP 2 outputs for matching heads (Group 3 + Group 5)
        ground_truth: Hard labels from dataset
        alpha: Teacher weight (0.7 = 70% SigLIP 2, 30% ground truth)
        temperature: Softening parameter (T=3)

    Returns:
        Combined distillation loss
    """
    # Soft targets from SigLIP 2 (temperature-scaled)
    teacher_soft = F.softmax(teacher_logits / temperature, dim=1)
    student_soft = F.log_softmax(student_logits / temperature, dim=1)

    # KL divergence between MobileNetV4 and SigLIP 2 distributions
    kl_loss = F.kl_div(
        student_soft, teacher_soft, reduction='batchmean'
    ) * (temperature ** 2)

    # Hard label loss
    hard_loss = F.mse_loss(torch.sigmoid(student_logits), ground_truth)

    return alpha * kl_loss + (1 - alpha) * hard_loss
```

### Checkpoint Selection

**Criteria** (best checkpoint selection per model):

1. **Per-Head Graduation Thresholds** (primary -- see Graduation Criteria section)
2. **Latency Constraint**: MobileNetV4 < 15ms/page GPU, < 50ms/page CPU; SigLIP 2 < 60ms/page GPU
3. **Early Stopping**: Patience = 10 epochs (stop if no improvement on primary metric)

**Selection Algorithm**:

```python
best_checkpoint = None
best_metric = -1.0
no_improvement_count = 0

for epoch in range(max_epochs):
    val_metrics, val_latency = validate_epoch(model, val_loader)
    primary_metric = compute_primary_metric(val_metrics, model_type)

    # Check latency constraint
    latency_limit = 50 if model_type == "mobilenetv4" else 60  # ms GPU
    if val_latency > latency_limit:
        logger.warning(f"Epoch {epoch}: Latency {val_latency}ms exceeds {latency_limit}ms")
        continue

    # Update best if primary metric improved
    if primary_metric > best_metric:
        best_metric = primary_metric
        best_checkpoint = save_checkpoint(model, epoch)
        no_improvement_count = 0
    else:
        no_improvement_count += 1

    if no_improvement_count >= patience:
        logger.info(f"Early stopping at epoch {epoch}")
        break

return best_checkpoint
```

---

## Data Pipeline Integration

### Dataset Sources (Workstream 3: Data Preparation)

The training pipeline consumes datasets from multiple workstreams:

| Workstream | Artifact | Usage | Proportion |
|------------|----------|-------|------------|
| **WS3: Data Preparation** | `training_labels.parquet`, raw images from 10 purpose-built datasets | Base training data across all task heads | ~80% of total |
| **WS4: Pseudo-Labeling** | Pseudo-labeled images (ensemble predictions) | Augment training data with high-confidence labels | < 10% of total |
| **WS8: Synthetic Generation** | Augmented images (aged/historical profiles, multi-degradation) | Expand dataset diversity (color modes, document age) | ~20% of total |

### Dataset Composition

> **Full specification**: See [DATASET_DIVERSITY_REQUIREMENTS.md](../../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)

**10 Purpose-Built Training Datasets (~503K total)**:

```python
# Total training dataset composition
total_samples = 503_000  # Approximate

datasets = {
    # Pre-correction (MobileNetV4-Conv-S, Step 1)
    "orientation": 50_000,          # 10% - 4-class orientation (0/90/180/270)
    "skew": 40_000,                 # 8% - ±10° skew angle regression
    "resolution_quality": 30_000,   # 6% - Character-height-aware resolution (0-1)

    # IQA (SigLIP 2 Group 1, Step 2)
    "iqa_curated": 16_000,          # 3% - DIQA-5000 + OHR-Bench + DocLayNet curated
    "iqa_synthetic": 100_000,       # 20% - Multi-degradation synthetic (aged/historical profiles)

    # Script detection (SigLIP 2 Group 2, Step 2)
    "script_detection": 108_000,    # 21% - synth-multiscript-250K subset (108 scripts)

    # Handwriting (SigLIP 2 Group 4, Step 2)
    "handwriting": 60_000,          # 12% - Has-handwriting, ratio, confidence

    # Page attributes (SigLIP 2 Group 5, Step 2)
    "capture_method": 50_000,       # 10% - Born-digital/scanner/camera/synthetic
    "shadow": 15_000,               # 3% - Shadow severity regression
    "warping": 20_000,              # 4% - Warping severity regression

    # Code detection
    "code_detection": 10_000,       # 2% - Code block detection
}

# Diversity dimensions (14 total):
# capture_method, resolution_tier, color_mode, document_age,
# script, orientation, skew_angle, degradation_type, etc.
# Global split registry: SHA256-keyed to prevent cross-dataset leakage
```

**Data Loader Configuration**:

```python
from image_preprocessing_detector.datasets import MultiTaskDataset

train_dataset = MultiTaskDataset(
    metadata_path="data/training_labels.parquet",
    split="train",
    task_groups=["iqa", "script", "orientation", "handwriting", "page_attrs"],
    augmentation=True,   # Random flips, color jitter, aged/historical profiles
    color_modes=["rgb", "grayscale", "binarized"],  # Color mode diversity
    cache_size=2000      # Cache 2000 images in memory
)

val_dataset = MultiTaskDataset(
    metadata_path="data/training_labels.parquet",
    split="val",
    task_groups=["iqa", "script", "orientation", "handwriting", "page_attrs"],
    augmentation=False   # No augmentation for validation
)
```

### Data Flow from Source to Training

```text
Workstream 3: Data Preparation
    ↓ (training_labels.parquet + images from 10 datasets)
Workstream 8: Synthetic Generation
    ↓ (augmented images: aged/historical profiles, multi-degradation)
    ├─→ Merge per-task datasets with diversity enforcement
    └─→ Create train/val/test splits (80/10/10, SHA256-keyed global registry)
    ↓
Workstream 4: Pseudo-Labeling (optional augmentation)
    ↓ (high-confidence ensemble labels)
    ├─→ Add to training set (< 10% total)
    ↓
MultiTaskDataset (PyTorch DataLoader)
    ↓
Workstream 2: Production Model Training (3-Step Virtuous Cycle)
    ├─→ Step 1: MobileNetV4-Conv-S bootstrap (orientation, skew, resolution)
    ├─→ Step 2: SigLIP 2 multi-task (frozen backbone + 16 heads)
    └─→ Step 3: MobileNetV4-Conv-S distillation (SigLIP 2 soft labels)
    ↓
Model Registry (GCS)
    ↓
Workstream 6: Model Arena (validation)
    ↓ (per-head graduation thresholds)
Workstream 1: Production Runtime (deployment)
```

---

## Model Deployment Pipeline

### Checkpoint Flow to Production

**End-to-End Flow**:

```text
1. Training Complete (3-Step Virtuous Cycle)
   ↓ (modal/train_mobilenetv4.py, modal/train_siglip2_multitask.py)
   Save best checkpoints per model

2. Model Export
   ↓ (modal/export_onnx.py)
   Convert to multi-head ONNX format
   ├─→ siglip2_naflex_v1.0.0.onnx (16 output heads)
   ├─→ mobilenetv4_v1.0.0.onnx (3 output heads)
   └─→ Docling layout models (pre-trained, no export needed)

3. Upload to Model Registry
   ↓
   gs://image-detection-models/candidates/
   ├─ siglip2_naflex/siglip2_naflex_v1.0.0.onnx
   ├─ siglip2_naflex/siglip2_naflex_v1.0.0_metadata.json
   ├─ mobilenetv4/mobilenetv4_v1.0.0.onnx
   └─ mobilenetv4/mobilenetv4_v1.0.0_metadata.json

4. Arena Benchmark (Workstream 6)
   ↓
   Validate per-head thresholds on held-out test sets
   Results: IQA PLCC > 0.65, Orientation acc > 95%, etc.

5. Graduation Check (per-head thresholds)
   ↓
   IQA PLCC > 0.65? ✅
   Orientation acc > 95%? ✅ (98% with distillation)
   Skew MAE < 0.5 deg? ✅
   Resolution quality MAE < 0.1? ✅
   Script acc > 90%? ✅
   Handwriting F1 > 0.85? ✅

6. Promote to Production Registry
   ↓
   gs://image-detection-models/production/
   ├─ siglip2_naflex/siglip2_naflex_v1.0.0.onnx
   ├─ mobilenetv4/mobilenetv4_v1.0.0.onnx
   └─ docling_layout/ (pre-trained model references)

7. Deploy to Runtime (Workstream 1)
   ↓
   Update production configuration
   siglip2_version: "siglip2_naflex_v1.0.0"
   mobilenetv4_version: "mobilenetv4_v1.0.0"

8. Monitor Performance (Workstream 7)
   ↓
   Track per-head metrics, latency, cost in production
```

### Model Metadata Schema

**Generated at Export Time** (example for SigLIP 2 NAFlex):

```json
{
  "model_id": "siglip2_naflex_v1.0.0",
  "architecture": "SigLIP 2 NAFlex (ViT-B/16)",
  "parameters": "88M",
  "head_groups": 5,
  "total_heads": 16,
  "training_config": {
    "datasets": "10 purpose-built (~503K total)",
    "training_step": "Step 2 (multi-task, frozen backbone + heads)",
    "epochs": 30,
    "batch_size": 64,
    "learning_rate": 1e-4,
    "optimizer": "AdamW",
    "backbone_frozen": true,
    "loss_weights": {
      "iqa": 0.25, "script": 0.20, "orientation_skew": 0.20,
      "handwriting": 0.15, "page_attrs": 0.20
    }
  },
  "training_results": {
    "iqa_plcc": 0.72,
    "orientation_accuracy": 0.97,
    "skew_mae_deg": 0.35,
    "script_accuracy": 0.93,
    "handwriting_f1": 0.89
  },
  "arena_validation": {
    "benchmark_date": "2026-02-01",
    "all_heads_graduated": true,
    "per_head_results": "see arena_details.json"
  },
  "performance": {
    "inference_latency_gpu_ms": 50,
    "inference_latency_cpu_ms": 200,
    "model_size_mb": 340
  },
  "provenance": {
    "git_sha": "abc1234",
    "modal_job_id": "mj-siglip2-001",
    "training_duration_hours": 18.0,
    "dataset_diversity_spec": "DATASET_DIVERSITY_REQUIREMENTS.md"
  }
}
```

### Export Formats

**Multiple Formats for Different Use Cases**:

| Format | Model | Use Case | Approx Size | Inference Backend |
|--------|-------|----------|-------------|-------------------|
| **ONNX (.onnx)** | SigLIP 2 NAFlex | Production runtime (primary, 16 heads) | ~340 MB | ONNX Runtime (GPU/CPU) |
| **ONNX (.onnx)** | MobileNetV4-Conv-S | Fast pre-correction gate (3 heads) | ~16 MB | ONNX Runtime (GPU/CPU) |
| **TorchScript (.pt)** | Both | Fallback if ONNX fails | ~350 / ~18 MB | PyTorch (GPU/CPU) |
| **PyTorch Checkpoint (.pth)** | Both | Fine-tuning, experimentation | ~360 / ~20 MB | PyTorch training |

**Export Script** (`modal/export_onnx.py`):

```python
import torch
import onnx

def export_siglip2_model(checkpoint_path: str, output_dir: str):
    """Export SigLIP 2 NAFlex multi-head model to ONNX."""

    model = load_siglip2_model(checkpoint_path)
    model.eval()

    # SigLIP 2 NAFlex: variable resolution via NAFlex packing
    dummy_input = torch.randn(1, 3, 384, 384)

    # 16 output heads across 5 groups
    output_names = [
        # G1: IQA (6 heads)
        "blur", "noise", "contrast", "compression", "illumination", "overall_quality",
        # G2: Script (1 head)
        "script_class",
        # G3: Orientation+Skew (2 heads)
        "orientation_class", "skew_angle",
        # G4: Handwriting (3 heads)
        "has_handwriting", "handwriting_ratio", "handwriting_confidence",
        # G5: Page Attrs (4 heads)
        "capture_method", "shadow_severity", "warping_severity", "resolution_quality",
    ]

    onnx_path = f"{output_dir}/siglip2_naflex_v1.0.0.onnx"
    torch.onnx.export(
        model, dummy_input, onnx_path,
        input_names=["image"],
        output_names=output_names,
        dynamic_axes={"image": {0: "batch_size", 2: "height", 3: "width"}}
    )

    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)

def export_mobilenetv4_model(checkpoint_path: str, output_dir: str):
    """Export MobileNetV4-Conv-S pre-correction gate to ONNX."""

    model = load_mobilenetv4_model(checkpoint_path)
    model.eval()

    dummy_input = torch.randn(1, 3, 256, 256)

    onnx_path = f"{output_dir}/mobilenetv4_v1.0.0.onnx"
    torch.onnx.export(
        model, dummy_input, onnx_path,
        input_names=["image"],
        output_names=["orientation", "skew_angle", "resolution_quality"],
        dynamic_axes={"image": {0: "batch_size"}}
    )

    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
```

---

## Workstream Dependencies

### Upstream Dependencies

| Workstream | Consumed Artifacts | Purpose |
|------------|-------------------|---------|
| **WS3: Data Preparation** | `training_labels.parquet`, raw images from 10 purpose-built datasets (~503K) | Base training data across all task heads (~80%) |
| **WS4: Pseudo-Labeling** | Pseudo-labeled images (ensemble predictions) | Augment training data with high-confidence labels (< 10%) |
| **WS8: Synthetic Generation** | Augmented images (aged/historical profiles, multi-degradation, color modes) | Expand dataset diversity (~20%) |

### Data Consumption Details

**How Training Consumes Each Source**:

1. **Data Preparation (WS3)**:
   - Reads `training_labels.parquet` for multi-task sample metadata
   - Loads images from 10 purpose-built datasets (see Dataset Composition)
   - Uses per-task label types: classification (orientation, script), regression (skew, IQA), binary (handwriting)
   - Global split registry (SHA256-keyed) prevents cross-dataset train/test leakage

2. **Pseudo-Labeling (WS4)**:
   - Optional augmentation with ensemble-labeled samples
   - Only uses high-confidence labels (agreement > 0.8)
   - Particularly valuable for handwriting and capture method labels

3. **Synthetic Generation (WS8)**:
   - Augmented images with aged/historical profiles (yellowing, foxing, ink fading)
   - Multi-degradation profiles across 14 diversity dimensions
   - Color mode diversity: RGB, grayscale, binarized
   - Synth-multiscript-250K: base images generated once, multi-task views derived

### Downstream Consumers

| Workstream | Provided Artifacts | Purpose |
|------------|-------------------|---------|
| **WS6: Model Arena** | Trained SigLIP 2 + MobileNetV4 checkpoints | Per-head graduation validation |
| **WS1: Production Runtime** | ONNX exported models (after Arena graduation) | MobileNetV4 pre-correction (~3ms) + SigLIP 2 multi-task (~50ms) |
| **WS7: Monitoring & Drift** | Model version metadata (per-head metrics) | Track per-head performance over time |

### External Dependencies

| Service/Tool | Purpose | Configuration |
|--------------|---------|---------------|
| **Modal** | GPU training infrastructure | A10 GPU (24GB), 18-24 hour runs (SigLIP 2), 6-8 hours (MobileNetV4) |
| **GCS Bucket** | Model registry and dataset storage | `gs://image-detection-models/`, `gs://image_detection_b/` |
| **PyTorch** | Training framework | 2.1.0+, CUDA 12.1 |
| **ONNX Runtime** | Model export and validation (multi-head ONNX) | 1.16+ |
| **HuggingFace** | SigLIP 2 NAFlex pre-trained backbone | `google/siglip2-base-patch16-naflex` |

---

## Training Configuration

### Hyperparameter Settings

**SigLIP 2 NAFlex Multi-Task (Step 2)**:

```yaml
# configs/training/siglip2_multitask_config.yaml
model:
  architecture: siglip2_naflex
  backbone: google/siglip2-base-patch16-naflex
  backbone_params: 88M
  backbone_frozen: true  # Frozen backbone, train heads only
  head_groups:
    iqa:
      heads: [blur, noise, contrast, compression, illumination, overall_quality]
      task_type: regression  # 0-1 scores
    script:
      heads: [script_class]
      task_type: classification  # 108 script classes
    orientation_skew:
      heads: [orientation_class, skew_angle]
      task_type: [classification, regression]  # 4 classes + ±10 deg
    handwriting:
      heads: [has_handwriting, handwriting_ratio, handwriting_confidence]
      task_type: [classification, regression, regression]
    page_attrs:
      heads: [capture_method, shadow_severity, warping_severity, resolution_quality]
      task_type: [classification, regression, regression, regression]

training:
  epochs: 30
  batch_size: 64
  learning_rate: 1e-4
  optimizer: AdamW
  weight_decay: 1e-5
  scheduler: CosineAnnealingLR
  warmup_epochs: 5

loss:
  type: weighted_multi_task
  group_weights:
    iqa: 0.25
    script: 0.20
    orientation_skew: 0.20
    handwriting: 0.15
    page_attrs: 0.20

validation:
  per_head_thresholds:
    iqa_plcc: 0.65
    orientation_accuracy: 0.95
    skew_mae_deg: 0.5
    resolution_quality_mae: 0.1
    script_accuracy: 0.90
    handwriting_f1: 0.85
  early_stopping_patience: 10
  save_best_only: true
```

**MobileNetV4-Conv-S Bootstrap (Step 1) + Distillation (Step 3)**:

```yaml
# configs/training/mobilenetv4_config.yaml
model:
  architecture: mobilenetv4_conv_s
  params: ~4M
  heads:
    orientation: {type: classification, classes: 4}  # 0/90/180/270
    skew: {type: regression, range: [-10, 10]}       # ±10 degrees
    resolution_quality: {type: regression, range: [0, 1]}  # Character-height-aware

# Step 1: Bootstrap training on synthetic ground truth
bootstrap:
  epochs: 30
  batch_size: 256  # Small model, large batches
  learning_rate: 1e-3
  optimizer: AdamW
  weight_decay: 1e-5
  scheduler: CosineAnnealingLR
  warmup_epochs: 3
  loss:
    type: multi_task
    orientation_weight: 1.0
    skew_weight: 0.5
    resolution_weight: 0.5

# Step 3: Distillation from SigLIP 2 soft labels
distillation:
  epochs: 20
  batch_size: 256
  learning_rate: 5e-4
  optimizer: AdamW
  loss:
    type: distillation
    alpha: 0.7  # 70% SigLIP 2 soft labels, 30% ground truth
    temperature: 3.0
  teacher:
    model: siglip2_naflex
    checkpoint: "models/siglip2_naflex/siglip2_naflex_best.pth"
    heads_used: [orientation_class, skew_angle, resolution_quality]  # From Groups 3+5

validation:
  per_head_thresholds:
    orientation_accuracy: 0.95  # Step 1 target (0.98 after Step 3)
    skew_mae_deg: 0.5          # Step 1 target (0.3 after Step 3)
    resolution_quality_mae: 0.1
  latency_constraint_gpu_ms: 15
  latency_constraint_cpu_ms: 50
  early_stopping_patience: 10
```

### Training Infrastructure (Modal)

**GPU Configuration**:

```python
# modal/train_siglip2_multitask.py
import modal

app = modal.App("image-detection-training")

@app.function(
    image=modal.Image.debian_slim()
        .pip_install(
            "torch==2.1.0",
            "torchvision==0.16.0",
            "transformers",  # HuggingFace for SigLIP 2 backbone
            "onnx==1.15.0",
            "pandas",
            "pillow"
        )
        .apt_install("libgl1"),
    gpu="A10",  # 24GB GPU
    timeout=86400,  # 24 hours
    secrets=[modal.Secret.from_name("gcs-credentials")]
)
def train_siglip2_multitask(config: dict):
    """Train SigLIP 2 NAFlex multi-task model (Step 2) on Modal GPU."""
    # Download 10 purpose-built datasets from GCS
    download_datasets(config["dataset_uris"])

    # Initialize SigLIP 2 with frozen backbone + 16 task heads
    model = create_siglip2_multitask(
        backbone="google/siglip2-base-patch16-naflex",
        freeze_backbone=True,
        head_groups=config["head_groups"],
    )

    # Multi-task training loop
    for epoch in range(config["epochs"]):
        train_loss = train_multitask_epoch(model, train_loader)
        val_metrics = validate_multitask_epoch(model, val_loader)

        # Check per-head graduation thresholds
        if all_heads_graduated(val_metrics, config["thresholds"]):
            save_checkpoint(model, epoch, val_metrics)
            break

    export_to_onnx(best_checkpoint, output_dir, num_outputs=16)
```

**Cost Tracking** (3-Step Virtuous Cycle):

- **Step 1 (MobileNetV4 Bootstrap)**: 30 epochs x 5 min/epoch = 2.5 hours x $0.456/hour = **$1.14**
- **Step 2 (SigLIP 2 Multi-Task)**: 30 epochs x 35 min/epoch = 17.5 hours x $0.456/hour = **$7.98**
- **Step 3 (MobileNetV4 Distillation)**: 20 epochs x 5 min/epoch = 1.7 hours x $0.456/hour = **$0.78**
- **Total Training Cost**: ~$10/training run

---

## Model Registry Management

### Registry Structure

**Candidate Models** (pre-validation):

```text
gs://image-detection-models/candidates/
├── siglip2_naflex/
│   ├── siglip2_naflex_v1.0.0.pth          # PyTorch checkpoint (16 heads)
│   ├── siglip2_naflex_v1.0.0.onnx         # ONNX export (16 outputs)
│   └── siglip2_naflex_v1.0.0_metadata.json
├── mobilenetv4/
│   ├── mobilenetv4_v1.0.0.pth             # PyTorch checkpoint (3 heads)
│   ├── mobilenetv4_v1.0.0.onnx            # ONNX export (3 outputs)
│   └── mobilenetv4_v1.0.0_metadata.json
└── docling_layout/
    ├── egret_xlarge_ref.json               # Reference to pre-trained model
    └── heron_ref.json                      # Reference to pre-trained model
```

**Production Models** (post-Arena graduation):

```text
gs://image-detection-models/production/
├── siglip2_naflex/
│   ├── siglip2_naflex_v1.0.0.onnx         # Primary (16 heads, ~50ms GPU)
│   ├── siglip2_naflex_v1.0.0.pt           # Fallback (TorchScript)
│   └── siglip2_naflex_v1.0.0_metadata.json
├── mobilenetv4/
│   ├── mobilenetv4_v1.0.0.onnx            # Primary (3 heads, ~3ms GPU)
│   ├── mobilenetv4_v1.0.0.pt              # Fallback (TorchScript)
│   └── mobilenetv4_v1.0.0_metadata.json
└── docling_layout/
    ├── egret_xlarge_ref.json               # Accuracy path
    └── heron_ref.json                      # Speed path
```

### Versioning Strategy

**Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR**: Architecture change (e.g., SigLIP 2 -> SigLIP 3) or head group restructuring
- **MINOR**: Training data change (new dataset added, diversity update)
- **PATCH**: Hyperparameter tuning, distillation re-run, bug fixes

**Examples**:

- `siglip2_naflex_v1.0.0`: Initial multi-task model (16 heads)
- `siglip2_naflex_v1.1.0`: Re-trained with additional handwriting data
- `siglip2_naflex_v1.1.1`: Loss weight adjustment for script head
- `mobilenetv4_v1.0.0`: Initial pre-correction gate (Step 1 bootstrap)
- `mobilenetv4_v1.1.0`: Step 3 distillation with SigLIP 2 soft labels

---

## Integration with Model Arena (Workstream 6)

### Phase 2: Fine-Tuned Validation

**Purpose**: Validate that fine-tuning improved performance before production deployment

**Workflow**:

```text
Training Complete (3-Step Virtuous Cycle)
    ↓
Export to multi-head ONNX + Metadata
    ↓
Upload to Candidates Registry
    ↓
Trigger Arena Benchmark (Workstream 6)
    ├─→ Load SigLIP 2 + MobileNetV4 from candidates/
    ├─→ Run per-head validation on held-out test sets
    ├─→ Compute per-head metrics with 95% CIs
    └─→ Check graduation thresholds per head
    ↓
Graduation Decision (ALL heads must pass)
    ├─ IQA PLCC > 0.65? ✅
    ├─ Orientation acc > 95%? ✅ (98% with distillation)
    ├─ Skew MAE < 0.5 deg? ✅
    ├─ Resolution quality MAE < 0.1? ✅
    ├─ Script acc > 90%? ✅
    └─ Handwriting F1 > 0.85? ✅
    ↓
Promote to Production Registry
    ↓
Deploy to Runtime (Workstream 1)
```

**Graduation Criteria** (per-head thresholds, from Model Arena):

| Head / Group | Metric | Threshold | Notes |
|-------------|--------|-----------|-------|
| IQA (G1) | PLCC | > 0.65 | Overall quality correlation |
| Orientation (G3) | Accuracy | > 95% (98% after Step 3) | 4-class: 0/90/180/270 |
| Skew (G3) | MAE | < 0.5 degrees | Regression ±10 deg |
| Resolution Quality (G5) | MAE | < 0.1 | 0-1 score |
| Script (G2) | Accuracy | > 90% | 108-class classification |
| Handwriting (G4) | F1 | > 0.85 | Binary detection |

**Historical Results** (to be populated after first training run):

| Model Version | Head | Metric | Value | Graduated |
|---------------|------|--------|-------|-----------|
| *Pending first training run* | | | | |

---

## Retraining Workflow (Triggered by Workstream 7)

### Drift-Triggered Retraining

**When Monitoring detects per-head metric degradation**:

```text
Workstream 7: Drift Detection
    ↓ (Alert: e.g., IQA PLCC dropped below 0.65, or script acc below 90%)
Workstream 7: Active Learning
    ↓ (Harvest difficult samples for degraded head(s))
Workstream 7: Privacy Review
    ↓ (Approve samples, reject those with PII)
Workstream 8: Synthetic Augmentation
    ↓ (Apply augmentation profiles for affected task)
Workstream 2: Retraining (this workstream)
    ├─→ Original 10 datasets (~503K)
    ├─→ Harvested samples for affected heads
    └─→ Synthetic augmentation for affected heads
    ↓
Re-run affected training steps:
    ├─→ If MobileNetV4 heads degraded: Re-run Step 1 + Step 3
    ├─→ If SigLIP 2 heads degraded: Re-run Step 2 + Step 3
    └─→ Full re-run if multiple groups affected
    ↓
Export to multi-head ONNX
    ↓
Workstream 6: Arena Validation (per-head thresholds)
    ↓
Deploy to Production (Workstream 1)
```

**Retraining Frequency**:

- **Drift-Triggered**: When any per-head metric drops below graduation threshold (automatic)
- **Scheduled**: Monthly retraining with accumulated samples (optional)
- **Manual**: On-demand for experiments or dataset updates

---

## Performance Characteristics

| Metric | SigLIP 2 NAFlex (~88M) | MobileNetV4-Conv-S (~4M) | Notes |
|--------|------------------------|--------------------------|-------|
| **Training Time** | ~17.5 hours (Step 2, 30 epochs) | ~4.2 hours (Step 1 + Step 3) | A10 GPU on Modal |
| **Task Heads** | 16 heads across 5 groups | 3 heads (orientation, skew, resolution) | SigLIP 2 covers all tasks |
| **Inference Latency (GPU)** | ~50ms/image | ~3ms/image | MobileNetV4 is ~17x faster |
| **Inference Latency (CPU)** | ~200ms/image | ~12ms/image | MobileNetV4 for pre-correction |
| **Model Size** | ~340 MB (ONNX) | ~16 MB (ONNX) | 21x smaller MobileNetV4 |
| **Training Cost** | $7.98 (Modal A10) | $1.92 (Modal A10, Steps 1+3) | ~$10 total |
| **Variable Resolution** | Native (NAFlex packing) | Fixed (256x256) | SigLIP 2 handles any aspect ratio |

**Two-Model Pipeline Rationale**:

- **MobileNetV4 pre-correction**: Corrects orientation, skew, and resolution BEFORE SigLIP 2 sees the image
- **SigLIP 2 benefits**: All 16 heads produce more accurate results on corrected images
- **Redundancy**: SigLIP 2 also has orientation/skew/resolution heads (Groups 3+5) for validation and teacher capability
- **Step 3 virtuous cycle**: SigLIP 2 soft labels improve MobileNetV4 accuracy (orientation 95% -> 98%)

---

## Level 3 Assessment

**Recommendation**: **Level 3 CONDITIONAL** (Per multi-model consensus)

**Rationale**:

- **Standard PyTorch Workflows**: Training follows conventional fine-tuning + distillation patterns
- **Well-Documented Multi-Task Setup**: Head group configuration and loss weighting are straightforward
- **3-Step Cycle is Sequential**: Each step has clear inputs/outputs

**When Level 3 WOULD Be Needed**:

- If the MobileCLIP-2 distillation cascade (S4 -> S0) is implemented for edge deployment
- If automated hyperparameter tuning (AutoML) for per-head loss weights is integrated
- If NAFlex packing implementation requires custom CUDA kernels
- If multi-model ensemble training replaces the current 3-step cycle

**Current Guidance**: This Level 2 doc provides sufficient detail for understanding the training pipeline. Developers should reference training scripts directly (`modal/train_siglip2_multitask.py`, `modal/train_mobilenetv4.py`) for implementation details. The Layout Fusion Downsampler is documented at Level 3 as a **legacy** fallback path (see [layout-fusion-downsampler.md](../level-3/model-training/layout-fusion-downsampler.md)).

**Decision**: Enrich Level 2 first (as done above), revisit Level 3 when MobileCLIP-2 cascade is implemented.

---

## Source File Traceability

This section maps training pipeline stages to implementation files with LOC counts.

| Workflow Step | Source Files | LOC | Total | Percentage |
|---------------|--------------|-----|-------|------------|
| **Data Pipeline** | `src/image_preprocessing_detector/datasets/multitask_dataset.py` | 350 | 350 | 4.5% |
| **SigLIP 2 Training** | `modal/train_siglip2_multitask.py`, `src/training/siglip2_trainer.py`, `src/models/siglip2_multitask.py` | TBD | TBD | TBD |
| **MobileNetV4 Training** | `modal/train_mobilenetv4.py`, `src/training/mobilenetv4_trainer.py`, `src/models/mobilenetv4_gate.py` | TBD | TBD | TBD |
| **Distillation** | `src/training/distillation_loss.py`, `src/training/generate_soft_labels.py` | TBD | TBD | TBD |
| **Model Architectures** | `src/models/model_optimizer.py`, `src/models/batch_inference.py`, `src/models/loss_functions.py`, `src/models/model_loader.py` | TBD | TBD | TBD |
| **Model Export** | `modal/export_onnx.py` (multi-head support) | TBD | TBD | TBD |
| **Supporting** | `src/training/checkpoint_utils.py`, `src/training/__init__.py`, `src/models/__init__.py` | TBD | TBD | TBD |
| **Workstream Total** | **TBD files** | -- | **TBD** | **100%** |

> **Note**: LOC counts will be updated after implementation. The new pipeline replaces ResNet-50/ResNet-18 with SigLIP 2 NAFlex + MobileNetV4-Conv-S.

**Key Components** (planned):

1. **Modal Training Scripts**:
   - `train_siglip2_multitask.py`: SigLIP 2 multi-task training (Step 2, frozen backbone + 16 heads)
   - `train_mobilenetv4.py`: MobileNetV4 bootstrap (Step 1) + distillation (Step 3)
   - `export_onnx.py`: Multi-head ONNX export for both models

2. **Training Logic**:
   - SigLIP 2 multi-task trainer with per-group loss weighting
   - MobileNetV4 bootstrap + distillation trainers
   - KL-divergence distillation from SigLIP 2 to MobileNetV4 (T=3)
   - Per-head checkpoint selection with graduation thresholds

3. **Model Architectures**:
   - SigLIP 2 NAFlex (~88M, frozen ViT-B/16 backbone + 16 task heads)
   - MobileNetV4-Conv-S (~4M, 3 heads: orientation, skew, resolution)
   - Docling layout models (pre-trained, egret-xlarge / heron)
   - Multi-task loss functions (weighted per-group)

**Training Metrics** (targets):

- SigLIP 2: ~17.5 hours training, per-head graduation thresholds
- MobileNetV4 Bootstrap: ~2.5 hours, orientation > 95%, skew MAE < 0.5 deg
- MobileNetV4 Distillation: ~1.7 hours, orientation > 98%, skew MAE < 0.3 deg
- Total training time: ~22 hours on Modal A10 GPU

**Level 3 Documentation**: See [level-3/model-training/](../level-3/model-training/) for swimlane diagram.

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Data Preparation](../data-preparation/index.md) | Dataset ingestion |
| **Level 2** | [Pseudo-Labeling](../pseudo-labeling/index.md) | Label generation |
