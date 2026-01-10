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
purpose: "Document the model training pipeline including knowledge distillation and
  high-level training workflows."
---
This level provides detailed diagrams for the Model Training workstream - training and optimization of production ML models.

---

## Training Workflow - High Level

Overview of the complete model training pipeline from data preparation to model registry.

![Training Workflow High Level](project-a-training-workflow-high-level.svg)

---

## Knowledge Distillation

Detailed flow of the teacher-student knowledge distillation process for IQA models.

![Knowledge Distillation](project-a-distillation.svg)

---

## Key Components

| Component | Source Files | Purpose |
|-----------|--------------|---------|
| Teacher Model | `modal/train_phase2_iqa.py` | ResNet-50 teacher training |
| Student Model | `modal/train_phase2_iqa.py` | ResNet-18 distillation |
| ONNX Export | `modal/export_onnx.py` | Production model export |
| Model Registry | GCS bucket | Versioned model storage |

---

## Model Architecture

| Model | Architecture | Parameters | Purpose |
|-------|--------------|------------|---------|
| IQA Teacher | ResNet-50 | ~25M | High-capacity reference model |
| IQA Student | ResNet-18 | ~11M | Production inference (distilled) |
| DocLayout-YOLO | YOLOv10-nano | ~3M | Layout detection (11 classes) |

---

## Knowledge Distillation Workflow

### Training Phases

The teacher-student training follows a two-phase approach:

| Phase | Model | Dataset | Epochs | Loss Function | Validation Metric | Target |
|-------|-------|---------|--------|---------------|-------------------|--------|
| **1. Teacher Training** | ResNet-50 | OHR-Bench (70% real, 30% synthetic) | 50 | MSE + Multi-Label BCE | PLCC | > 0.70 |
| **2. Student Distillation** | ResNet-18 | Teacher soft labels + hard labels | 30 | α×KL(teacher) + (1-α)×MSE(ground truth) | PLCC | > 0.65 |

### Distillation Loss Function

**Composite Loss** (balances teacher knowledge and ground truth):

```python
def distillation_loss(student_logits, teacher_logits, ground_truth, alpha=0.7, temperature=3.0):
    """
    Knowledge distillation loss with temperature scaling.

    Args:
        student_logits: Raw student model outputs (before softmax)
        teacher_logits: Raw teacher model outputs (before softmax)
        ground_truth: Hard labels from dataset
        alpha: Teacher weight (0.7 = 70% teacher, 30% ground truth)
        temperature: Softening parameter for probability distributions

    Returns:
        Combined loss value
    """
    # Soft targets from teacher (temperature-scaled)
    teacher_soft = F.softmax(teacher_logits / temperature, dim=1)
    student_soft = F.log_softmax(student_logits / temperature, dim=1)

    # KL divergence between student and teacher distributions
    distillation_loss = F.kl_div(
        student_soft,
        teacher_soft,
        reduction='batchmean'
    ) * (temperature ** 2)  # Scale back by T^2

    # MSE between student output and ground truth
    student_output = torch.sigmoid(student_logits)
    hard_loss = F.mse_loss(student_output, ground_truth)

    # Weighted combination
    return alpha * distillation_loss + (1 - alpha) * hard_loss
```

**Hyperparameters**:

- **α (alpha)**: 0.7 (70% teacher weight, 30% ground truth weight)
  - Higher α = more teacher knowledge transfer
  - Lower α = more direct supervision from ground truth
- **T (temperature)**: 3.0
  - Higher T = softer probability distributions (more information transfer)
  - T=1 reduces to standard cross-entropy

**Training Results** (Phase 3 Completed):

- **Teacher**: val_loss = 0.27 (50 epochs on OHR-Bench)
- **Student**: val_loss = 0.14 (30 epochs with distillation)
- **Improvement**: Student achieves 48% lower loss than teacher

### Checkpoint Selection

**Criteria** (best checkpoint selection from training run):

1. **Best Validation PLCC** (primary metric)
2. **Latency Constraint**: < 100ms/page on CPU (enforced for student)
3. **Early Stopping**: Patience = 10 epochs (stop if no improvement)

**Selection Algorithm**:

```python
best_checkpoint = None
best_plcc = -1.0
no_improvement_count = 0

for epoch in range(max_epochs):
    val_plcc, val_latency = validate_epoch(model, val_loader)

    # Check latency constraint (student only)
    if model_type == "student" and val_latency > 100:
        logger.warning(f"Epoch {epoch}: Latency {val_latency}ms exceeds 100ms threshold")
        continue  # Skip this checkpoint

    # Update best if PLCC improved
    if val_plcc > best_plcc:
        best_plcc = val_plcc
        best_checkpoint = save_checkpoint(model, epoch)
        no_improvement_count = 0
    else:
        no_improvement_count += 1

    # Early stopping
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
| **WS3: Data Preparation** | `training_labels.parquet`, raw images (DIQA-5000, OHR-Bench, DocLayNet) | Base training dataset | 70% of total |
| **WS4: Pseudo-Labeling** | Pseudo-labeled images (5-model ensemble predictions) | Augment training data with high-confidence labels | < 10% of total |
| **WS8: Synthetic Generation** | Degraded images + ground truth from Genalog | Expand dataset with controlled degradations | 30% of total |

### Dataset Composition

**Training Dataset Breakdown**:

```python
# Total training dataset composition
total_samples = 50,000

real_data = {
    "diqa_5000": 4,000,      # 8% - Document IQA benchmark (train split)
    "ohr_bench": 12,000,     # 24% - Handwriting recognition quality
    "doclaynet": 10,000,     # 20% - Layout with quality variations
    "live_csiq": 2,000,      # 4% - Classical IQA benchmarks
    "tablebank": 5,000,      # 10% - Table-heavy documents
    "funsd": 2,000,          # 4% - Forms and handwriting
}
# Real total: 35,000 (70%)

synthetic_data = {
    "genalog_blur": 5,000,   # 10% - Systematic blur degradations
    "genalog_noise": 4,000,  # 8% - Noise variations
    "genalog_combined": 6,000 # 12% - Multi-degradation profiles
}
# Synthetic total: 15,000 (30%)

# Pseudo-labeled data used sparingly (high confidence only)
# Typically < 5,000 samples (< 10%)
```

**Data Loader Configuration**:

```python
from image_preprocessing_detector.datasets import HybridIQADataset

train_dataset = HybridIQADataset(
    metadata_path="data/training_labels.parquet",
    split="train",
    augmentation=True,  # Random flips, rotations, color jitter
    cache_size=1000     # Cache 1000 images in memory
)

val_dataset = HybridIQADataset(
    metadata_path="data/training_labels.parquet",
    split="val",
    augmentation=False  # No augmentation for validation
)
```

### Data Flow from Source to Training

```text
Workstream 3: Data Preparation
    ↓ (training_labels.parquet + images)
Workstream 8: Synthetic Generation
    ↓ (degraded images + ground truth)
    ├─→ Merge Real + Synthetic (70/30 split)
    └─→ Create train/val/test splits (80/10/10)
    ↓
Workstream 4: Pseudo-Labeling (optional augmentation)
    ↓ (high-confidence ensemble labels)
    ├─→ Add to training set (< 10% total)
    ↓
HybridIQADataset (PyTorch DataLoader)
    ↓
Workstream 2: Production Model Training
    ├─→ Teacher Training (Phase 1)
    └─→ Student Distillation (Phase 2)
    ↓
Model Registry (GCS)
    ↓
Workstream 6: Model Arena (validation)
    ↓ (PLCC > 0.65?)
Workstream 1: Production Runtime (deployment)
```

---

## Model Deployment Pipeline

### Checkpoint Flow to Production

**End-to-End Flow**:

```text
1. Training Complete
   ↓ (modal/train_phase2_iqa.py)
   Save best checkpoint (best_val_plcc.pth)

2. Model Export
   ↓ (modal/export_onnx.py)
   Convert to ONNX Runtime format
   ├─→ resnet18_v1.0.0.onnx (student)
   └─→ resnet50_v1.0.0.onnx (teacher)

3. Upload to Model Registry
   ↓
   gs://image-detection-models/candidates/
   ├─ student/resnet18_v1.0.0.onnx
   ├─ student/resnet18_v1.0.0_metadata.json
   ├─ teacher/resnet50_v1.0.0.onnx
   └─ teacher/resnet50_v1.0.0_metadata.json

4. Arena Benchmark (Workstream 6 - Phase 2)
   ↓
   Validate on DIQA-5000 test set (1,000 samples)
   Result: PLCC = 0.68 [0.65, 0.71]

5. Graduation Check
   ↓
   PLCC > 0.65? ✅ YES
   Improvement > 10%? ✅ YES (209% improvement over baseline)

6. Promote to Production Registry
   ↓
   gs://image-detection-models/production/
   ├─ student/resnet18_v1.0.0.onnx
   └─ student/resnet18_v1.0.0_metadata.json

7. Deploy to Runtime (Workstream 1)
   ↓
   Update production configuration
   model_version: "resnet18_v1.0.0"

8. Monitor Performance (Workstream 7)
   ↓
   Track PLCC, latency, cost in production
   Baseline: PLCC = 0.68
```

### Model Metadata Schema

**Generated at Export Time**:

```json
{
  "model_id": "resnet18_v1.0.0",
  "architecture": "ResNet-18",
  "training_config": {
    "dataset": "OHR-Bench + DIQA-5000 + Synthetic (70/30)",
    "epochs": 30,
    "batch_size": 64,
    "learning_rate": 1e-4,
    "optimizer": "AdamW",
    "distillation_alpha": 0.7,
    "temperature": 3.0
  },
  "training_results": {
    "final_train_loss": 0.12,
    "final_val_loss": 0.14,
    "best_val_plcc": 0.72,
    "best_epoch": 28
  },
  "arena_validation": {
    "benchmark_date": "2025-01-12",
    "diqa5000_plcc": 0.68,
    "diqa5000_plcc_ci": [0.65, 0.71],
    "improvement_vs_baseline": 2.09,
    "graduated": true
  },
  "performance": {
    "inference_latency_gpu_ms": 15,
    "inference_latency_cpu_ms": 85,
    "model_size_mb": 42
  },
  "deployment": {
    "graduation_date": "2025-01-12",
    "approved_by": "ml_team",
    "production_deployed": true,
    "deployment_date": "2025-01-15"
  },
  "provenance": {
    "git_sha": "4dc216a",
    "modal_job_id": "mj-abc123",
    "training_duration_hours": 12.5
  }
}
```

### Export Formats

**Multiple Formats for Different Use Cases**:

| Format | Use Case | Size | Inference Backend |
|--------|----------|------|-------------------|
| **ONNX (.onnx)** | Production runtime (primary) | 42 MB | ONNX Runtime (GPU/CPU) |
| **TorchScript (.pt)** | Fallback if ONNX fails | 44 MB | PyTorch (GPU/CPU) |
| **PyTorch Checkpoint (.pth)** | Fine-tuning, experimentation | 48 MB | PyTorch training |

**Export Script** (`modal/export_onnx.py`):

```python
import torch
import onnx

def export_student_model(checkpoint_path: str, output_dir: str):
    """Export student model to multiple formats."""

    # Load trained model
    model = load_student_model(checkpoint_path)
    model.eval()

    # Dummy input for tracing
    dummy_input = torch.randn(1, 3, 224, 224)

    # Export to ONNX
    onnx_path = f"{output_dir}/resnet18_v1.0.0.onnx"
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        input_names=["image"],
        output_names=["quality_scores"],
        dynamic_axes={"image": {0: "batch_size"}}
    )

    # Validate ONNX model
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)

    # Export to TorchScript
    torchscript_path = f"{output_dir}/resnet18_v1.0.0.pt"
    traced_model = torch.jit.trace(model, dummy_input)
    traced_model.save(torchscript_path)

    print(f"Exported to: {onnx_path}, {torchscript_path}")
```

---

## Workstream Dependencies

### Upstream Dependencies

| Workstream | Consumed Artifacts | Purpose |
|------------|-------------------|---------|
| **WS3: Data Preparation** | `training_labels.parquet`, raw images (DIQA-5000, OHR-Bench, DocLayNet) | Base training dataset (70% of total) |
| **WS4: Pseudo-Labeling** | Pseudo-labeled images (5-model ensemble) | Augment training data with high-confidence labels (< 10%) |
| **WS8: Synthetic Generation** | Degraded images + ground truth labels | Expand dataset 2-3x (30% of total) |

### Data Consumption Details

**How Training Consumes Each Source**:

1. **Data Preparation (WS3)**:
   - Reads `training_labels.parquet` for sample metadata
   - Loads images from `data/01_base_data/` and `data/02_benchmark_only/`
   - Uses anchor scores for weighted loss (human=1.0, llm_high=0.8, synthetic=0.3)

2. **Pseudo-Labeling (WS4)**:
   - Optional augmentation with ensemble-labeled samples
   - Only uses high-confidence labels (agreement > 0.8)
   - Typically < 5,000 samples added to training set

3. **Synthetic Generation (WS8)**:
   - Consumes Genalog-degraded images with parametric ground truth
   - Provides systematic coverage of degradation space
   - Balances real-world distribution with edge cases

### Downstream Consumers

| Workstream | Provided Artifacts | Purpose |
|------------|-------------------|---------|
| **WS6: Model Arena** | Trained teacher/student checkpoints | Phase 2 validation (fine-tuned model benchmarking) |
| **WS1: Production Runtime** | ONNX exported models (after Arena graduation) | Student inference, teacher escalation |
| **WS7: Monitoring & Drift** | Model version metadata | Track deployed model performance over time |

### External Dependencies

| Service/Tool | Purpose | Configuration |
|--------------|---------|---------------|
| **Modal** | GPU training infrastructure | A10 GPU (24GB), 12-24 hour runs |
| **GCS Bucket** | Model registry and dataset storage | `gs://image-detection-models/`, `gs://image_detection_b/` |
| **PyTorch** | Training framework | 2.1.0+, CUDA 12.1 |
| **ONNX Runtime** | Model export and validation | 1.16+ |

---

## Training Configuration

### Hyperparameter Settings

**Teacher Training (ResNet-50)**:

```yaml
# configs/training/teacher_config.yaml
model:
  architecture: resnet50
  num_classes: 45  # 45-dimensional IQA vector
  pretrained: true  # ImageNet initialization

training:
  epochs: 50
  batch_size: 64
  learning_rate: 1e-4
  optimizer: AdamW
  weight_decay: 1e-5
  scheduler: CosineAnnealingLR
  warmup_epochs: 5

loss:
  type: composite
  mse_weight: 0.6
  bce_weight: 0.4  # Multi-label binary classification

validation:
  metric: plcc
  early_stopping_patience: 10
  save_best_only: true
```

**Student Distillation (ResNet-18)**:

```yaml
# configs/training/student_config.yaml
model:
  architecture: resnet18
  num_classes: 45
  pretrained: true

training:
  epochs: 30
  batch_size: 128  # 2x teacher batch size (smaller model)
  learning_rate: 5e-5  # Lower LR for fine-tuning
  optimizer: AdamW
  weight_decay: 1e-5
  scheduler: CosineAnnealingLR
  warmup_epochs: 3

loss:
  type: distillation
  alpha: 0.7  # 70% teacher, 30% ground truth
  temperature: 3.0
  hard_loss: mse

teacher:
  checkpoint: "models/teacher/resnet50_best.pth"
  device: cuda  # Load teacher on GPU for soft label generation

validation:
  metric: plcc
  latency_constraint_ms: 100  # CPU inference constraint
  early_stopping_patience: 10
```

### Training Infrastructure (Modal)

**GPU Configuration**:

```python
# modal/train_phase2_iqa.py
import modal

app = modal.App("image-detection-training")

@app.function(
    image=modal.Image.debian_slim()
        .pip_install(
            "torch==2.1.0",
            "torchvision==0.16.0",
            "onnx==1.15.0",
            "pandas",
            "pillow"
        )
        .apt_install("libgl1"),
    gpu="A10",  # 24GB GPU
    timeout=86400,  # 24 hours
    secrets=[modal.Secret.from_name("gcs-credentials")]
)
def train_teacher_model(config: dict):
    """Train ResNet-50 teacher model on Modal GPU."""
    # Download dataset from GCS
    download_dataset(config["dataset_uri"])

    # Initialize model
    model = create_teacher_model(num_classes=45)

    # Training loop
    for epoch in range(config["epochs"]):
        train_loss = train_epoch(model, train_loader)
        val_loss, val_plcc = validate_epoch(model, val_loader)

        # Save checkpoint if best
        if val_plcc > best_plcc:
            save_checkpoint(model, epoch, val_plcc)

    # Export best checkpoint
    export_to_onnx(best_checkpoint, output_dir)
```

**Cost Tracking**:

- **Teacher Training**: 50 epochs × 15 min/epoch = 12.5 hours × $0.456/hour = **$5.70**
- **Student Training**: 30 epochs × 10 min/epoch = 5 hours × $0.456/hour = **$2.28**
- **Total Training Cost**: ~$8/training run

---

## Model Registry Management

### Registry Structure

**Candidate Models** (pre-validation):

```text
gs://image-detection-models/candidates/
├── teacher/
│   ├── resnet50_v1.0.0.pth          # PyTorch checkpoint
│   ├── resnet50_v1.0.0.onnx         # ONNX export
│   └── resnet50_v1.0.0_metadata.json
└── student/
    ├── resnet18_v1.0.0.pth
    ├── resnet18_v1.0.0.onnx
    ├── resnet18_v1.0.0.pt           # TorchScript
    └── resnet18_v1.0.0_metadata.json
```

**Production Models** (post-Arena graduation):

```text
gs://image-detection-models/production/
├── teacher/
│   ├── resnet50_v1.0.0.onnx
│   └── resnet50_v1.0.0_metadata.json
└── student/
    ├── resnet18_v1.0.0.onnx         # Primary
    ├── resnet18_v1.0.0.pt           # Fallback
    └── resnet18_v1.0.0_metadata.json
```

### Versioning Strategy

**Semantic Versioning** (MAJOR.MINOR.PATCH):

- **MAJOR**: Architecture change (ResNet-18 → EfficientNet)
- **MINOR**: Training data change (new dataset added)
- **PATCH**: Hyperparameter tuning, bug fixes

**Examples**:

- `resnet18_v1.0.0`: Initial student model
- `resnet18_v1.1.0`: Re-trained with additional TableBank data
- `resnet18_v1.1.1`: Hyperparameter tuning (learning rate adjustment)
- `resnet18_v2.0.0`: Architecture change to ResNet-34

---

## Integration with Model Arena (Workstream 6)

### Phase 2: Fine-Tuned Validation

**Purpose**: Validate that fine-tuning improved performance before production deployment

**Workflow**:

```text
Training Complete (this workstream)
    ↓
Export to ONNX + Metadata
    ↓
Upload to Candidates Registry
    ↓
Trigger Arena Benchmark (Workstream 6)
    ├─→ Load model from candidates/
    ├─→ Run inference on DIQA-5000 test set (1,000 samples)
    ├─→ Compute PLCC, SRCC, MAE, RMSE with 95% CIs
    └─→ Compare to Phase 1 baseline (QualiCLIP PLCC = 0.22)
    ↓
Graduation Decision
    ├─ PLCC > 0.65? ✅
    ├─ Improvement > 10%? ✅
    └─ CI lower bound > baseline mean? ✅
    ↓
Promote to Production Registry
    ↓
Deploy to Runtime (Workstream 1)
```

**Graduation Criteria** (from Model Arena):

- **Target PLCC**: > 0.65
- **Minimum Improvement**: +10% vs baseline
- **Confidence**: 95% CI lower bound > 0.22 (baseline mean)

**Historical Results**:

| Model Version | Arena PLCC | CI Lower | CI Upper | Improvement | Graduated |
|---------------|------------|----------|----------|-------------|-----------|
| resnet18_v0.9.0 | 0.58 | 0.54 | 0.62 | +163% | ❌ (below 0.65) |
| resnet18_v1.0.0 | 0.68 | 0.65 | 0.71 | +209% | ✅ |

---

## Retraining Workflow (Triggered by Workstream 7)

### Drift-Triggered Retraining

**When Monitoring detects PLCC drop > 10%**:

```text
Workstream 7: Drift Detection
    ↓ (Alert: PLCC dropped from 0.68 → 0.61)
Workstream 7: Active Learning
    ↓ (Harvest 1,000 difficult samples)
Workstream 7: Privacy Review
    ↓ (Approve 850 samples, reject 150 with PII)
Workstream 8: Synthetic Augmentation
    ↓ (Apply Genalog degradations → 850 × 3 = 2,550 samples)
Workstream 2: Retraining (this workstream)
    ├─→ Original dataset: 50,000 samples
    ├─→ Harvested samples: 850 samples
    └─→ Synthetic augmentation: 2,550 samples
    ↓
    Total retraining dataset: 53,400 samples
    ↓
Train Updated Student Model
    ↓ (30 epochs, same config as original)
Export to ONNX
    ↓
Workstream 6: Arena Phase 3 Validation
    ↓ (Benchmark on DIQA-5000 + failure cases)
    Result: PLCC = 0.70 [0.67, 0.73] ✅ (recovered)
    ↓
Deploy to Production (Workstream 1)
```

**Retraining Frequency**:

- **Drift-Triggered**: When PLCC drop > 10% (automatic)
- **Scheduled**: Monthly retraining with accumulated samples (optional)
- **Manual**: On-demand for experiments or dataset updates

---

## Performance Characteristics

| Metric | Teacher (ResNet-50) | Student (ResNet-18) | Notes |
|--------|---------------------|---------------------|-------|
| **Training Time** | 12.5 hours (50 epochs) | 5 hours (30 epochs) | A10 GPU on Modal |
| **Validation PLCC** | 0.72 | 0.68 | Both exceed 0.65 threshold |
| **Validation Loss** | 0.27 | 0.14 | Student benefits from distillation |
| **Inference Latency (GPU)** | 30-50ms/image | 10-25ms/image | 2-5x faster student |
| **Inference Latency (CPU)** | 150-300ms/image | 40-100ms/image | 2-3x faster student |
| **Model Size** | 98 MB (ONNX) | 42 MB (ONNX) | 2.3x smaller student |
| **Training Cost** | $5.70 (Modal A10) | $2.28 (Modal A10) | ~$8 total |

**Why Student Outperforms Teacher on Validation**:

- **Regularization Effect**: Distillation acts as regularization, preventing overfitting
- **Focused Capacity**: Student learns to mimic teacher's robust features without noise
- **Ensemble Effect**: Student trained on both teacher soft labels and ground truth hard labels

---

## Level 3 Assessment

**Recommendation**: **Level 3 CONDITIONAL** (Per multi-model consensus)

**Rationale**:

- **Standard PyTorch Workflows**: Training follows conventional fine-tuning patterns
- **Well-Documented Distillation**: Loss function and training loop are straightforward
- **Small Codebase**: ~3,000 lines total across training scripts

**When Level 3 WOULD Be Needed**:

- If custom loss functions become more complex (e.g., adversarial training, meta-learning)
- If multi-stage distillation is added (teacher ensemble → super-teacher → student)
- If automated hyperparameter tuning (AutoML, NAS) is integrated
- If model architecture search becomes more sophisticated

**Current Guidance**: This Level 2 doc provides sufficient detail for understanding the training pipeline. Developers should reference training scripts directly (`modal/train_phase2_iqa.py`) for implementation details.

**Decision**: Enrich Level 2 first (as done above), revisit Level 3 if complexity grows.

---

## Source File Traceability

This section maps training pipeline stages to implementation files with LOC counts.

| Workflow Step | Source Files | LOC | Total | Percentage |
|---------------|--------------|-----|-------|------------|
| **Data Pipeline** | `src/image_preprocessing_detector/datasets/iqa_dataset.py` | 180 | 180 | 2.5% |
| **Teacher Training** | `modal/train_phase2_iqa.py`, `src/training/teacher_trainer.py`, `src/models/resnet_teacher.py` | 707, 586, 293 | 1,586 | 22.5% |
| **Student Training** | `modal/train_student_distillation.py`, `src/training/student_trainer.py`, `src/models/resnet_student.py` | 779, 664, 277 | 1,720 | 24.4% |
| **Knowledge Distillation** | `src/training/distillation_loss.py`, `src/training/generate_soft_labels.py` | 248, 313 | 561 | 7.9% |
| **Model Architectures** | `src/models/model_optimizer.py`, `src/models/batch_inference.py`, `src/models/loss_functions.py`, `src/models/model_loader.py` | 1435, 622, 330, 244 | 2,631 | 37.3% |
| **Model Export** | `modal/export_phase7_onnx.py` | 347 | 347 | 4.9% |
| **Supporting** | `src/training/checkpoint_utils.py`, `src/training/__init__.py`, `src/models/__init__.py` | 82, 45, 86 | 213 | 3.0% |
| **Workstream Total** | **16 files** | — | **7,058** | **100%** |

**Validation**: All LOC counts validated against `docs/architecture/workstream_loc_counts.json`.

**Key Components**:

1. **Modal Training Scripts** (1,833 lines, 26.0%):
   - `train_phase2_iqa.py`: Teacher training on Modal GPU
   - `train_student_distillation.py`: Student knowledge distillation
   - `export_phase7_onnx.py`: ONNX/TorchScript export

2. **Training Logic** (1,938 lines, 27.5%):
   - Teacher/student trainers with different configurations
   - Distillation loss (KL + BCE + MSE)
   - Soft label generation from teacher
   - Checkpoint management

3. **Model Architectures** (3,287 lines, 46.6%):
   - ResNet-50 teacher, ResNet-18 student
   - Model optimizer (graph optimizations, quantization)
   - Batch inference engine
   - Loss functions (multi-task, distillation)

**Training Metrics**:

- Teacher: 50 epochs, val_loss=0.27
- Student: 30 epochs, val_loss=0.14 (better than teacher!)
- Total training time: 20-36 hours on Modal GPU

**Level 3 Documentation**: See [level-3/model-training/](../level-3/model-training/) for swimlane diagram.

---

## Related Diagrams

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Data Preparation](../data-preparation/index.md) | Dataset ingestion |
| **Level 2** | [Pseudo-Labeling](../pseudo-labeling/index.md) | Label generation |
