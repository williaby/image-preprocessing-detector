# Project C: Fine-Tuning & Label Generation

> **Status**: Implementation Phase
> **Created**: 2025-12-17
> **Owner**: Core Team
> **Type**: Model Training & Label Generation

---

## 1. Project Purpose

The purpose of **Project C – Fine-Tuning & Label Generation** is to develop one or more trained multimodal models capable of replicating human-assigned DIQA-5000 quality scores with high fidelity, and to use those trained models to generate continuous DIQA-style labels for additional document image datasets at scale.

**Critical Constraint**: Project C is the **only project** in the program that performs learning or parameter updates.

---

## 2. Primary Objectives

### 2.1 Replicate DIQA-5000 Human Scores

Train a model to predict continuous DIQA-5000 scores that align with human judgment across:

| Dimension | Description |
|-----------|-------------|
| **Overall** | Overall document quality |
| **Sharpness** | Image sharpness/blur |
| **Color** | Color fidelity |

The trained model should achieve accuracy **comparable to or better than existing DIQA baselines** when evaluated by Project A.

### 2.2 Establish a Reusable Fine-Tuning Pipeline

Create a repeatable fine-tuning process that:

- Can be re-run with a different base model
- Can incorporate improved datasets over time
- Produces versioned, auditable training artifacts

**Key Requirement**: The pipeline must support **model substitution without redesign**.

### 2.3 Generate DIQA-Style Labels for External Datasets

Once a DIQA-aligned model is trained, Project C will use it to:

| Target Dataset | Purpose | Scale |
|----------------|---------|-------|
| **OCR-Quality** | Generate continuous DIQA-style scores | ~25,000+ images |
| **Additional datasets** | Future expansion | TBD |

**Downstream Uses**:

- OCR preprocessing decisions
- Model routing
- Dataset expansion and training

---

## 3. Scope of Work

### 3.1 Base Model Selection

| Priority | Model | Source |
|----------|-------|--------|
| P0 | **LLaMA 4 Maverick** | Primary target |
| P1 | Additional models | Based on Project A benchmarks |

Base models may be:

- Unmodified HF checkpoints
- Quantized variants from Project B

### 3.2 Training Dataset

**Primary Dataset**: DIQA-5000

| Split | Size (est.) | Usage | Policy |
|-------|-------------|-------|--------|
| **Train** | ~3,500 images | Learning | Used for fitting |
| **Validation** | ~750 images | Early stopping, selection | Used during training |
| **Test** | ~750 images | Final reporting | **NEVER used during training** |

**Rule**: All training must respect dataset boundaries.

### 3.3 Training Methodology

**Method**: Parameter-Efficient Fine-Tuning (PEFT)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Adapter Type** | LoRA | Memory efficient |
| **Learning Rate** | Low (2e-4) | Stable convergence |
| **Stopping** | Early stopping | Prevent overfitting |
| **Objective** | Regression | Continuous outputs |

**Critical**: The model must output **continuous predictions** aligned to DIQA scales, NOT classification.

### 3.4 Training Infrastructure

| Environment | Usage |
|-------------|-------|
| **Modal GPU** | Training and large-scale inference |
| **Local** | Data prep, pipeline dev, small validation |

Large-scale training and inference are **explicitly cloud-based**.

---

## 4. Evaluation and Acceptance

### 4.1 Evaluation Responsibility

> **Project C does not self-certify success.**

All trained models must be passed to **Project A** for evaluation using:

- PLCC (Pearson Linear Correlation Coefficient)
- SRCC (Spearman Rank Correlation Coefficient)
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)

Evaluation results determine whether a model is accepted.

### 4.2 Performance Targets

Target performance should approach **human-level agreement**:

| Criterion | Target |
|-----------|--------|
| Rank correlation with DIQA ground truth | High (≥0.85) |
| Error within human rater variance | Yes |
| Stable across DIQA dimensions | Yes |

**Note**: Exact thresholds are defined by Project A governance.

---

## 5. Multi-Stage Training Plan

### Stage 1: DIQA-5000 Fine-Tuning (Required)

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: DIQA-5000 Fine-Tuning                            │
├─────────────────────────────────────────────────────────────┤
│  1. Load base model (LLaMA 4 Maverick)                     │
│  2. Apply PEFT/LoRA adapters                               │
│  3. Train on DIQA-5000 train split                         │
│  4. Validate against held-out val split                    │
│  5. Generate training manifest                             │
│  6. Deliver trained artifact to Project A                  │
└─────────────────────────────────────────────────────────────┘
```

**Deliverables**:

- Trained model checkpoint
- LoRA adapter weights
- Training manifest
- Model card

### Stage 2: OCR-Quality Mapping (Required)

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: OCR-Quality Mapping                              │
├─────────────────────────────────────────────────────────────┤
│  1. Run trained model on OCR-Quality dataset               │
│  2. Generate continuous DIQA-style scores                  │
│  3. Analyze correlation with OCR-Quality tiers:            │
│     • Excellent                                            │
│     • Good                                                 │
│     • Fair                                                 │
│     • Poor                                                 │
│  4. Produce mapping documentation                          │
└─────────────────────────────────────────────────────────────┘
```

**Deliverables**:

- DIQA-style predictions for OCR-Quality dataset
- Correlation analysis report
- Tier mapping documentation

### Stage 3: SmartDoc-QA Alignment (Optional)

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: SmartDoc-QA Alignment (Exploratory)              │
├─────────────────────────────────────────────────────────────┤
│  1. Apply trained model to SmartDoc-QA images              │
│  2. Correlate predicted scores with:                       │
│     • Capture conditions                                   │
│     • OCR degradation patterns                             │
│  3. Identify which labels can be inferred from DIQA        │
└─────────────────────────────────────────────────────────────┘
```

**Status**: Exploratory and optional

---

## 6. Outputs and Deliverables

### Required Deliverables

| Deliverable | Description | Format |
|-------------|-------------|--------|
| **Fine-Tuning Pipeline** | Documented training workflow | Python CLI |
| **Trained Model Artifacts** | Versioned checkpoints + adapters | Safetensors |
| **Training Manifest** | Complete provenance | YAML |
| **Label Generation Outputs** | DIQA predictions for OCR-Quality | JSON/Parquet |

### CLI Interface

```bash
# Stage 1: Train on DIQA-5000
train diqa --model llama4-maverick --peft lora --output ./checkpoints/

# Train from quantized base (Project B artifact)
train diqa --model llama4-maverick --base-variant int8 --peft qlora --output ./checkpoints/

# Resume training
train diqa --resume ./checkpoints/epoch_2/

# Train with config file
train diqa --config ./training_config.yaml

# Stage 2: Generate labels for OCR-Quality
train label-gen --checkpoint ./checkpoints/final/ --dataset ocr-quality --output ./labels/

# Stage 2: Analyze tier mapping
train analyze-mapping --predictions ./labels/ocr_quality_predictions.parquet --output ./reports/

# Stage 3: SmartDoc-QA alignment (optional)
train smartdoc-analysis --checkpoint ./checkpoints/final/ --dataset smartdoc-qa --output ./analysis/

# Generate model card
train model-card --checkpoint ./checkpoints/final/ --output ./MODEL_CARD.md

# Export for Project A
train export --checkpoint ./checkpoints/final/ --format project-a --output ./export/
```

### Training Manifest Schema

```yaml
# MANIFEST.yaml
artifact_id: llama4-maverick-diqa-v1.0.0
version: 1.0.0
created_at: "2025-12-17T10:00:00Z"
created_by: "project-c-pipeline"

base_model:
  source: huggingface
  id: meta-llama/Llama-4-Maverick
  revision: abc123def456
  checksum: sha256:...
  variant: base  # or int8 if from Project B

training:
  method: lora
  peft_config:
    r: 16
    alpha: 32
    dropout: 0.05
    target_modules:
      - q_proj
      - k_proj
      - v_proj
      - o_proj

  hyperparameters:
    learning_rate: 2.0e-4
    batch_size: 4
    gradient_accumulation_steps: 8
    effective_batch_size: 32
    num_epochs: 3
    warmup_ratio: 0.1
    weight_decay: 0.01

  early_stopping:
    enabled: true
    patience: 3
    metric: val_plcc_overall

  dataset:
    name: diqa5000
    version: v1.0
    train_samples: 3500
    val_samples: 750
    # test split NOT used during training

  hardware:
    provider: modal
    gpu_type: A100-40GB
    training_duration_hours: 4.5

validation_metrics:
  overall:
    plcc: 0.91
    srcc: 0.89
    mae: 0.09
    rmse: 0.12
  sharpness:
    plcc: 0.87
    srcc: 0.85
    mae: 0.11
    rmse: 0.14
  color:
    plcc: 0.89
    srcc: 0.86
    mae: 0.10
    rmse: 0.13

output_artifacts:
  adapter_weights: ./adapter_model.safetensors
  adapter_config: ./adapter_config.json
  training_state: ./training_state.json
  model_card: ./MODEL_CARD.md

checksum: sha256:...
```

### Label Generation Output Schema

```json
{
  "dataset": "ocr-quality",
  "model_artifact": "llama4-maverick-diqa-v1.0.0",
  "generation_timestamp": "2025-12-17T15:00:00Z",
  "num_samples": 25000,
  "predictions": [
    {
      "image_id": "ocr_quality_00001",
      "diqa_overall": 0.78,
      "diqa_sharpness": 0.82,
      "diqa_color": 0.75,
      "original_tier": "Good",
      "inference_time_ms": 45
    }
  ],
  "tier_correlation": {
    "excellent": {"mean_overall": 0.92, "std": 0.05},
    "good": {"mean_overall": 0.78, "std": 0.08},
    "fair": {"mean_overall": 0.58, "std": 0.10},
    "poor": {"mean_overall": 0.32, "std": 0.12}
  }
}
```

---

## 7. Out-of-Scope Items

Project C **explicitly does not include**:

| Item | Owner |
|------|-------|
| Benchmark leaderboard management | Project A |
| Quantization workflows | Project B |
| OCR preprocessing pipelines | Existing pipeline |
| Production inference services | Operations |
| Human annotation collection | External |
| UI development | External |

**Rule**: Project C produces trained models and labels, **not deployed systems**.

---

## 8. Dependencies

| Dependency | Source | Required For |
|------------|--------|--------------|
| DIQA-5000 dataset | External | Stage 1 |
| Base models | Hugging Face | Stage 1 |
| Quantized artifacts | Project B | Optional |
| Modal GPU | Infrastructure | Training |
| Evaluation feedback | Project A | Acceptance |

---

## 9. Relationship to Other Projects

```
┌─────────────────────────────────────────────────────────────┐
│               Project C: Fine-Tuning & Labels               │
│                  (Learning & Label Gen)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Inputs:                                                    │
│  ┌───────────────┐    ┌───────────────┐                    │
│  │ Base Model    │    │ Quantized     │                    │
│  │ (HuggingFace) │    │ (Project B)   │                    │
│  └───────┬───────┘    └───────┬───────┘                    │
│          │                    │ (optional)                 │
│          └──────────┬─────────┘                            │
│                     ▼                                       │
│  ┌─────────────────────────────────────┐                   │
│  │  Stage 1: DIQA-5000 Fine-Tuning     │                   │
│  └─────────────────────────────────────┘                   │
│                     │                                       │
│                     ▼                                       │
│  ┌─────────────────────────────────────┐                   │
│  │  Project A: Evaluation              │◀─── Pass/Fail     │
│  └─────────────────────────────────────┘                   │
│                     │                                       │
│                     ▼ (if passed)                          │
│  ┌─────────────────────────────────────┐                   │
│  │  Stage 2: OCR-Quality Labels        │                   │
│  └─────────────────────────────────────┘                   │
│                     │                                       │
│                     ▼                                       │
│  ┌─────────────────────────────────────┐                   │
│  │  Stage 3: SmartDoc-QA (optional)    │                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Relationships**:

- **Project A (Benchmarking Arena)**: Evaluates all trained outputs
- **Project B (Quantization Factory)**: Provides optional optimized baselines
- **Project C depends on Project A** to determine success
- **Project C depends on Project B** only if quantized baselines are selected

---

## 10. Guiding Principle

> **Project C's job is not to prove the model is good.**
> **Project C's job is to produce candidates that Project A can judge.**

---

## 11. Implementation Architecture

### Module Structure

```
src/image_preprocessing_detector/labeling/finetuning/
├── __init__.py
├── cli.py                  # Click-based CLI
├── config.py               # Training configuration
├── trainer.py              # Main training loop
├── data_pipeline.py        # DIQA-5000 data loading
├── model_heads.py          # Multi-head regression
├── model_card.py           # Model card generation
├── manifest.py             # Training manifest
├── export.py               # Export utilities
├── callbacks.py            # Training callbacks
└── stages/                 # Multi-stage workflows
    ├── __init__.py
    ├── stage1_diqa.py              # DIQA-5000 fine-tuning
    ├── stage2_ocr_quality.py       # OCR-Quality label generation
    └── stage3_smartdoc.py          # SmartDoc-QA analysis
```

### Key Classes

```python
# Training configuration
@dataclass
class DIQATrainingConfig:
    """Configuration for DIQA-5000 fine-tuning."""

    # Base model
    base_model: str
    use_quantized_base: bool = False
    quantized_base_ref: str | None = None

    # PEFT configuration
    peft_method: str = "lora"
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj"
    ])

    # Training hyperparameters
    learning_rate: float = 2e-4
    batch_size: int = 4
    gradient_accumulation_steps: int = 8
    num_epochs: int = 3
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01

    # Early stopping
    early_stopping_patience: int = 3
    metric_for_best_model: str = "val_plcc_overall"

    # Output
    output_dir: Path
    checkpoint_every_n_steps: int = 500
    keep_best_k_checkpoints: int = 3


# Main trainer
class DIQATrainer:
    """Trainer for DIQA-5000 fine-tuning."""

    def __init__(self, config: DIQATrainingConfig): ...

    def train(
        self,
        train_dataset: DIQA5000Dataset,
        val_dataset: DIQA5000Dataset,
    ) -> TrainingResult: ...

    def generate_labels(
        self,
        dataset: Dataset,
        output_path: Path,
    ) -> LabelGenerationResult: ...


# Label generation
class LabelGenerator:
    """Generate DIQA-style labels for external datasets."""

    def __init__(self, checkpoint_path: Path): ...

    def generate(
        self,
        images: list[np.ndarray],
        batch_size: int = 8,
    ) -> list[DIQAPrediction]: ...

    def generate_dataset(
        self,
        dataset_name: str,
        output_path: Path,
    ) -> LabelGenerationResult: ...
```

---

## 12. Timeline

| Week | Milestone |
|------|-----------|
| 1 | CLI scaffold, config schema |
| 2 | Data pipeline (DIQA-5000 loading) |
| 3 | LoRA training implementation |
| 4 | Multi-head regression output |
| 5 | Checkpointing, early stopping |
| 6 | Model card, manifest generation |
| 7 | Project A integration (Stage 1 complete) |
| 8 | Stage 2: OCR-Quality label generation |
| 9 | Stage 2: Tier mapping analysis |
| 10 | Stage 3: SmartDoc-QA (optional) |
| 11 | Documentation, testing |

---

## 13. Open Questions

1. **DIQA-5000 Format**: Exact label format (continuous range)?
2. **Multi-Task**: One model for all dimensions or separate?
3. **QLoRA Priority**: Prioritize QLoRA from quantized base?
4. **Modal Config**: GPU allocation and scheduling?
5. **OCR-Quality Access**: Dataset availability?
6. **Stage 3 Priority**: Required for v1?

---

*Last Updated: 2025-12-17*
