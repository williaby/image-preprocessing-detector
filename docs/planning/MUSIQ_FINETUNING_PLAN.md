---
owner: docs-team
purpose: Documentation for MUSIQ Fine-Tuning Implementation Plan.
schema_type: common
status: draft
tags:
- planning
title: MUSIQ Fine-Tuning Implementation Plan
---

## Sub-Track A1: Sharpness Specialist for DIQA Pseudo-Labeling

**Version:** 1.0
**Date:** December 2025
**Reference:** DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1

---

## 1. Executive Summary

This document provides the implementation plan for fine-tuning MUSIQ (Multi-Scale Image Quality Transformer) as the **Sharpness Specialist** in the DIQA pseudo-labeling ensemble. MUSIQ is pre-trained on KonIQ-10k for natural image quality assessment and has strong blur/sharpness detection capabilities, making it ideal for the sharpness dimension.

### Key Deliverables

| Deliverable | Description | Priority |
|-------------|-------------|----------|
| `MUSIQMultiTask` wrapper | PyIQA MUSIQ backbone + 3-head regression | Critical |
| Modal training script | Two-phase fine-tuning on DIQA-5000 | Critical |
| Checkpoint selection | Weighted SRCC/ECE scoring for sharpness | Critical |
| ONNX export | Production-ready inference artifact | High |
| Integration tests | Validation against baseline benchmarks | High |

### Target Metrics (Post Fine-Tuning)

| Metric | Baseline (PyIQA) | Target | Priority |
|--------|------------------|--------|----------|
| SRCC (sharpness) | 0.213 | > 0.88 | Critical |
| SRCC (overall) | 0.116 | > 0.75 | Secondary |
| SRCC (color) | 0.112 | > 0.70 | Secondary |
| ECE (sharpness) | N/A | < 0.08 | Critical |
| Inference (T4) | 24ms | < 50ms | Acceptable |

---

## 2. Architecture Design

### 2.1 MUSIQ Base Model (from PyIQA)

**Architecture Analysis:**

```
PyIQA MUSIQ Architecture:
├── conv_root: StdConv(3 → 64, 7x7, stride=2)
├── gn_root: GroupNorm(32, 64)
├── root_pool: MaxPool2d(3x3, stride=2)
├── block1: Bottleneck(64 → 256)
├── embedding: Linear(resnet_token_dim * 4 * patch_size^2 → 384)
├── transformer_encoder: TransformerEncoder(hidden_size=384)
│   ├── Multi-head self-attention
│   ├── Spatial hash embeddings
│   └── Scale embeddings
├── [CLS] token aggregation: index 0 → (batch, 384)
└── head: Linear(384 → 1)  ← REPLACE THIS
```

**Key Specifications:**

- **Backbone output:** 384-dimensional CLS token embedding
- **Input:** Variable resolution (multi-scale patches)
- **Pre-training:** KonIQ-10k (natural image quality, blur/noise/compression focus)
- **Original output:** Single MOS score [0-1]

### 2.2 MUSIQMultiTask Wrapper

```python
class MUSIQMultiTask(nn.Module):
    """MUSIQ backbone with multi-task head for DIQA dimensions.

    Replaces single MOS output with 3-dimensional quality prediction:
    - Overall quality (secondary for this specialist)
    - Sharpness (PRIMARY - this model's specialty)
    - Color fidelity (secondary for this specialist)
    """

    def __init__(
        self,
        pretrained_musiq: nn.Module,
        freeze_backbone: bool = True,
        head_hidden_dim: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()

        # Extract backbone (everything before final head)
        self.backbone = self._extract_backbone(pretrained_musiq)

        # Freeze backbone initially (Phase 1)
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False

        # Multi-task regression head
        # MUSIQ outputs 384-dim CLS token
        self.head = MultiTaskHead(
            in_features=384,
            hidden_dim=head_hidden_dim,
            dropout=dropout,
        )

    def _extract_backbone(self, musiq_model: nn.Module) -> nn.Module:
        """Extract MUSIQ backbone, removing final regression head."""
        # Create wrapper that returns features before head
        class MUSIQBackbone(nn.Module):
            def __init__(self, full_model):
                super().__init__()
                # Copy all components except final head
                self.conv_root = full_model.conv_root
                self.gn_root = full_model.gn_root
                self.root_pool = full_model.root_pool
                self.block1 = full_model.block1
                self.embedding = full_model.embedding
                self.transformer_encoder = full_model.transformer_encoder
                # Store other required attributes
                self.hash_bases = full_model.hash_bases
                self.scale_emb = full_model.scale_emb

            def forward(self, x, *args, **kwargs):
                # Run through backbone, return CLS token features
                # (Implementation follows PyIQA MUSIQ forward logic)
                features = self._extract_features(x)
                return features[:, 0]  # CLS token

        return MUSIQBackbone(musiq_model)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Forward pass returning 3 quality dimensions."""
        features = self.backbone(x)  # [batch, 384]
        return self.head(features)    # {overall, sharpness, color}

    def unfreeze_backbone(self) -> None:
        """Unfreeze backbone for Phase 2 training."""
        for param in self.backbone.parameters():
            param.requires_grad = True
```

### 2.3 MultiTaskHead Architecture

```python
class MultiTaskHead(nn.Module):
    """Shared MLP with 3 regression outputs for DIQA dimensions.

    Architecture matches DIQA-5000_Pseudo_Labels_v2.md Section 4.2:
    - Shared hidden layer for multi-task regularization
    - Per-dimension output heads
    - Sigmoid activation for [0, 1] bounded output
    """

    def __init__(
        self,
        in_features: int = 384,
        hidden_dim: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()

        # Shared feature transformation
        self.shared = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Per-dimension heads
        self.heads = nn.ModuleDict({
            'overall': nn.Linear(hidden_dim, 1),
            'sharpness': nn.Linear(hidden_dim, 1),
            'color': nn.Linear(hidden_dim, 1),
        })

        self._init_weights()

    def _init_weights(self) -> None:
        """Xavier initialization for stable training."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        """Returns dictionary of dimension scores in [0, 1]."""
        shared = self.shared(features)
        return {
            dim: torch.sigmoid(head(shared).squeeze(-1))
            for dim, head in self.heads.items()
        }
```

---

## 3. Training Protocol

### 3.1 Two-Phase Training (per Section 4.4A1)

#### Phase 1: Head Warmup (10 epochs)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Backbone** | Frozen | Preserve KonIQ-10k features |
| **Trainable** | Head only (~100K params) | Fast convergence |
| **Learning Rate** | 1e-3 | Standard for new layers |
| **Scheduler** | Linear warmup (2 epochs) + CosineAnnealingLR | Per consensus recommendations |
| **Batch Size** | 32 | Fits on T4/A10G |
| **Loss Weights** | [0.2, **0.6**, 0.2] | Sharpness specialist |

#### Phase 2: Full Fine-Tuning (20 epochs)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Backbone** | Unfrozen | Adapt to document domain |
| **Learning Rate (backbone)** | 1e-5 | Low to preserve features |
| **Learning Rate (head)** | 1e-4 | Higher for continued training |
| **Scheduler** | Linear warmup (3 epochs) + CosineAnnealingLR | Per consensus recommendations |
| **Batch Size** | 32 | Memory efficiency |
| **Loss Weights** | [0.2, **0.6**, 0.2] | Maintain specialist focus |
| **Augmentation** | HorizontalFlip, Rotation(±5°), ColorJitter | Label-preserving transforms |

### 3.2 Loss Function

```python
def musiq_specialist_loss(
    predictions: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    weights: dict[str, float] = {'overall': 0.2, 'sharpness': 0.6, 'color': 0.2},
) -> torch.Tensor:
    """Weighted multi-task loss for sharpness specialist.

    Combines:
    - MSE for point prediction (60%)
    - Rank loss for SRCC optimization (20%)
    - Focal calibration loss for ECE (20%)
    """
    total_loss = 0.0

    for dim in ['overall', 'sharpness', 'color']:
        pred = predictions[dim]
        target = targets[dim]

        # MSE component
        mse = F.mse_loss(pred, target)

        # Differentiable rank loss (for SRCC)
        rank = differentiable_rank_loss(pred, target)

        # Focal calibration loss (for ECE)
        focal_ece = focal_calibration_loss(pred, target, gamma=2.0)

        # Combined dimension loss
        dim_loss = 0.6 * mse + 0.2 * rank + 0.2 * focal_ece

        # Apply specialist weighting
        total_loss += weights[dim] * dim_loss

    return total_loss


def differentiable_rank_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    margin: float = 0.1,
) -> torch.Tensor:
    """Pairwise ranking loss for SRCC optimization."""
    # Create pairwise differences
    pred_diff = pred.unsqueeze(1) - pred.unsqueeze(0)
    target_diff = target.unsqueeze(1) - target.unsqueeze(0)

    # Soft ranking: penalize when pred order doesn't match target order
    # Use smooth approximation of sign function
    target_sign = torch.tanh(target_diff * 10)
    pred_sign = torch.tanh(pred_diff * 10)

    # Margin ranking loss
    loss = F.relu(margin - target_sign * pred_sign)

    # Return mean over all pairs (excluding diagonal)
    mask = 1 - torch.eye(pred.size(0), device=pred.device)
    return (loss * mask).sum() / mask.sum()


def focal_calibration_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    gamma: float = 2.0,
) -> torch.Tensor:
    """Focal loss variant for calibration.

    Harder examples (larger errors) get more weight.
    """
    error = (pred - target).abs()

    # Normalize to [0, 1] (scores already in [0, 1])
    confidence = 1.0 - error

    # Focal weighting: harder examples get more weight
    focal_weight = (1 - confidence) ** gamma

    return (focal_weight * error ** 2).mean()
```

### 3.3 Data Augmentation

```python
# Phase 1 (head warmup): Minimal augmentation
PHASE1_AUGMENTATION = A.Compose([
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ToTensorV2(),
])

# Phase 2 (full fine-tune): Label-preserving augmentation
PHASE2_AUGMENTATION = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=5, p=0.3),  # Small rotation to preserve quality perception
    A.ColorJitter(
        brightness=0.1,
        contrast=0.1,
        saturation=0.1,
        hue=0.05,
        p=0.3,
    ),
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ToTensorV2(),
])
```

---

## 4. Modal Training Infrastructure

### 4.1 Modal Configuration

```python
# modal/train_musiq_finetuning.py

import modal

app = modal.App("diqa-musiq-finetuning")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # PyIQA for MUSIQ backbone
        "pyiqa>=0.1.12",
        # Deep learning
        "torch>=2.1.0",
        "torchvision>=0.16.0",
        # Data augmentation
        "albumentations>=1.3.0",
        # Image processing
        "opencv-python-headless>=4.8.0",
        "pillow>=10.0.0",
        # Metrics
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        # Export
        "onnx>=1.14.0",
        # GCS
        "google-cloud-storage>=2.10.0",
    )
    .add_local_dir(
        local_path="src/image_preprocessing_detector",
        remote_path="/root/image_preprocessing_detector",
        copy=True,
    )
    .add_local_file(
        ".gcp/service-account.json",
        "/root/.gcp/service-account.json",
        copy=True,
    )
)


@app.cls(
    gpu="T4",  # 16GB VRAM sufficient for MUSIQ fine-tuning
    timeout=14400,  # 4 hours
    container_idle_timeout=300,
    secrets=[modal.Secret.from_name("gcs-credentials")],
)
class MUSIQTrainer:
    """Modal class for MUSIQ fine-tuning on DIQA-5000."""

    @modal.enter()
    def setup(self):
        """Initialize model and data on container start."""
        import pyiqa

        # Load pre-trained MUSIQ from PyIQA
        self.base_musiq = pyiqa.create_metric("musiq", device="cuda")

        # Download DIQA-5000 from GCS
        self.dataset_path = self._download_diqa5000()

    @modal.method()
    def train(
        self,
        phase1_epochs: int = 10,
        phase2_epochs: int = 20,
        batch_size: int = 32,
        checkpoint_interval: int = 5,
    ) -> dict:
        """Run two-phase MUSIQ fine-tuning."""
        # Implementation details in Section 4.2
        pass
```

### 4.2 Training Loop Implementation

```python
def train_musiq_specialist(
    base_model,
    train_dataset,
    val_dataset,
    config: MUSIQTrainingConfig,
) -> MUSIQMultiTask:
    """Two-phase MUSIQ training with checkpoint management."""

    # Wrap MUSIQ with multi-task head
    model = MUSIQMultiTask(
        pretrained_musiq=base_model,
        freeze_backbone=True,  # Phase 1
        head_hidden_dim=config.head_hidden_dim,
        dropout=config.dropout,
    )
    model = model.cuda()

    # Optimizer (head only for Phase 1)
    optimizer = torch.optim.AdamW(
        model.head.parameters(),
        lr=config.phase1_lr,
        weight_decay=config.weight_decay,
    )

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.phase1_epochs,
    )

    best_checkpoint = None
    checkpoints = []

    # ============ PHASE 1: Head Warmup ============
    print("=" * 60)
    print("PHASE 1: Head Warmup (Backbone Frozen)")
    print("=" * 60)

    for epoch in range(config.phase1_epochs):
        train_loss = train_epoch(
            model, train_dataset, optimizer, config.loss_weights
        )
        val_metrics = validate(model, val_dataset)
        scheduler.step()

        # Save checkpoint
        checkpoint = save_checkpoint(
            model, optimizer, epoch, val_metrics, phase=1
        )
        checkpoints.append(checkpoint)

        print(f"Epoch {epoch+1}/{config.phase1_epochs} | "
              f"Loss: {train_loss:.4f} | "
              f"SRCC_sharpness: {val_metrics['srcc_sharpness']:.4f} | "
              f"ECE: {val_metrics['ece_mean']:.4f}")

    # ============ PHASE 2: Full Fine-Tuning ============
    print("=" * 60)
    print("PHASE 2: Full Fine-Tuning (Backbone Unfrozen)")
    print("=" * 60)

    # Unfreeze backbone
    model.unfreeze_backbone()

    # New optimizer with differential learning rates
    optimizer = torch.optim.AdamW([
        {'params': model.backbone.parameters(), 'lr': config.phase2_backbone_lr},
        {'params': model.head.parameters(), 'lr': config.phase2_head_lr},
    ], weight_decay=config.weight_decay)

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.phase2_epochs,
    )

    for epoch in range(config.phase2_epochs):
        train_loss = train_epoch(
            model, train_dataset, optimizer, config.loss_weights
        )
        val_metrics = validate(model, val_dataset)
        scheduler.step()

        # Save checkpoint
        checkpoint = save_checkpoint(
            model, optimizer, config.phase1_epochs + epoch, val_metrics, phase=2
        )
        checkpoints.append(checkpoint)

        print(f"Epoch {config.phase1_epochs + epoch + 1}/{config.total_epochs} | "
              f"Loss: {train_loss:.4f} | "
              f"SRCC_sharpness: {val_metrics['srcc_sharpness']:.4f} | "
              f"ECE: {val_metrics['ece_mean']:.4f}")

    # Select best checkpoint using weighted scoring
    best_checkpoint = select_best_checkpoint(
        checkpoints,
        specialty='sharpness',
        **CHECKPOINT_PRESETS['balanced'],
    )

    # Load best checkpoint and return
    model.load_state_dict(best_checkpoint['model_state_dict'])
    return model
```

---

## 5. Checkpoint Selection Strategy

### 5.1 Weighted SRCC + ECE Scoring

Per DIQA-5000_Pseudo_Labels_v2.md Section 4.5, checkpoint selection uses weighted scoring
within an SRCC band, allowing small SRCC losses for significant ECE improvements:

```python
CHECKPOINT_PRESETS = {
    'srcc_dominant': {'srcc_weight': 0.8, 'ece_weight': 0.2, 'srcc_band': 0.015},
    'balanced': {'srcc_weight': 0.7, 'ece_weight': 0.3, 'srcc_band': 0.02},
    'calibration_aware': {'srcc_weight': 0.6, 'ece_weight': 0.4, 'srcc_band': 0.025},
}

# For MUSIQ (sharpness specialist), use specialty-specific selection
def select_musiq_checkpoint(checkpoints: list[dict]) -> dict:
    """Select best MUSIQ checkpoint using Weighted(SRCC_sharpness, ECE) scoring.

    Selection criterion from Section 4.4A1:
    - Within SRCC band (±0.02 from best): compete on weighted score
    - Score = 0.7 * normalized_SRCC + 0.3 * normalized_ECE
    - Strategy: Weighted(SRCC_sharpness, ECE) with 'balanced' preset

    This allows trading small SRCC losses (e.g., 0.01) for significant
    ECE improvements (e.g., 0.05 → 0.03).
    """
    return select_best_checkpoint(
        checkpoints,
        specialty='sharpness',  # Focus on sharpness dimension
        **CHECKPOINT_PRESETS['balanced'],
    )
```

### 5.2 Validation Metrics

```python
def compute_validation_metrics(
    predictions: dict[str, np.ndarray],
    targets: dict[str, np.ndarray],
) -> dict[str, float]:
    """Compute full validation metrics suite."""
    from scipy.stats import spearmanr, pearsonr

    metrics = {}

    for dim in ['overall', 'sharpness', 'color']:
        pred = predictions[dim]
        target = targets[dim]

        # Correlation metrics
        srcc, _ = spearmanr(pred, target)
        plcc, _ = pearsonr(pred, target)

        # Error metrics
        mae = np.abs(pred - target).mean()
        rmse = np.sqrt(((pred - target) ** 2).mean())

        # Calibration (ECE)
        ece = compute_regression_ece(pred, target, uncertainties=None)

        metrics[f'srcc_{dim}'] = srcc
        metrics[f'plcc_{dim}'] = plcc
        metrics[f'mae_{dim}'] = mae
        metrics[f'rmse_{dim}'] = rmse
        metrics[f'ece_{dim}'] = ece

    # Aggregate metrics
    metrics['srcc_mean'] = np.mean([metrics[f'srcc_{d}'] for d in ['overall', 'sharpness', 'color']])
    metrics['ece_mean'] = np.mean([metrics[f'ece_{d}'] for d in ['overall', 'sharpness', 'color']])

    return metrics
```

---

## 6. Data Pipeline

### 6.1 DIQA-5000 PyTorch Dataset

```python
class DIQA5000TrainingDataset(torch.utils.data.Dataset):
    """PyTorch Dataset for DIQA-5000 with continuous labels.

    Wraps the existing DIQA5000Dataset for training with:
    - On-the-fly augmentation
    - Proper tensor conversion
    - Label normalization to [0, 1]
    """

    def __init__(
        self,
        root_dir: str | Path,
        split: str = "train",
        transform: A.Compose | None = None,
    ):
        # Load base dataset (already normalizes to [0, 1])
        self.base_dataset = DIQA5000Dataset(
            root_dir=root_dir,
            split=split,
            normalize_scores=True,  # MOS [1-5] -> [0-1]
        )
        self.transform = transform

    def __len__(self) -> int:
        return len(self.base_dataset)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        sample = self.base_dataset[idx]

        # Apply augmentation
        image = sample.image  # numpy array [H, W, C]
        if self.transform:
            transformed = self.transform(image=image)
            image = transformed['image']
        else:
            # Default: just normalize and convert
            image = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0

        # Convert labels to tensors
        labels = {
            'overall': torch.tensor(sample.ground_truth['overall'], dtype=torch.float32),
            'sharpness': torch.tensor(sample.ground_truth['sharpness'], dtype=torch.float32),
            'color': torch.tensor(sample.ground_truth['color'], dtype=torch.float32),
        }

        return image, labels
```

### 6.2 Data Split Strategy

| Split | Samples | Usage |
|-------|---------|-------|
| Train | 3,500 | Model training |
| Val | 750 | Checkpoint selection, early stopping |
| Test | 750 | Final benchmark (never seen during training) |

---

## 7. Model Export and Storage

### 7.1 ONNX Export

```python
def export_musiq_onnx(
    model: MUSIQMultiTask,
    output_path: str,
    opset_version: int = 17,
) -> None:
    """Export fine-tuned MUSIQ to ONNX format."""
    model.eval()

    # MUSIQ handles variable input sizes via multi-scale patches
    # Use representative input size for export
    dummy_input = torch.randn(1, 3, 384, 384, device='cuda')

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=opset_version,
        input_names=['image'],
        output_names=['overall', 'sharpness', 'color'],
        dynamic_axes={
            'image': {0: 'batch_size', 2: 'height', 3: 'width'},
            'overall': {0: 'batch_size'},
            'sharpness': {0: 'batch_size'},
            'color': {0: 'batch_size'},
        },
    )
    print(f"Exported ONNX model to {output_path}")
```

### 7.2 GCS Storage Structure

```
gs://image_detection_b/models/diqa/
└── track_a_iqa/
    └── musiq/
        └── v1.0.0/
            ├── model.pt              # PyTorch checkpoint
            ├── model.onnx            # ONNX export
            ├── config.json           # Training configuration
            ├── metrics.json          # Final validation metrics
            └── MODEL_CARD.md         # Model documentation
```

---

## 8. Implementation Checklist

### Phase 1: Infrastructure Setup (Week 1)

- [ ] Create `src/image_preprocessing_detector/labeling/finetuning/musiq_wrapper.py`
  - [ ] Implement `MUSIQMultiTask` class
  - [ ] Implement `MultiTaskHead` class
  - [ ] Add backbone extraction logic for PyIQA MUSIQ
  - [ ] Add unit tests

- [ ] Create `src/image_preprocessing_detector/labeling/finetuning/musiq_loss.py`
  - [ ] Implement `musiq_specialist_loss`
  - [ ] Implement `differentiable_rank_loss`
  - [ ] Implement `focal_calibration_loss`
  - [ ] Add unit tests

- [ ] Create `src/image_preprocessing_detector/labeling/finetuning/musiq_config.py`
  - [ ] Define `MUSIQTrainingConfig` dataclass
  - [ ] Define checkpoint selection presets
  - [ ] Add configuration validation

### Phase 2: Training Script (Week 1-2)

- [ ] Create `modal/train_musiq_finetuning.py`
  - [ ] Modal app configuration (T4 GPU, 4hr timeout)
  - [ ] GCS dataset download logic
  - [ ] Two-phase training loop
  - [ ] Checkpoint management
  - [ ] Metrics logging
  - [ ] ONNX export

- [ ] Create `configs/musiq_finetuning.yaml`
  - [ ] Phase 1 hyperparameters
  - [ ] Phase 2 hyperparameters
  - [ ] Loss weights
  - [ ] Checkpoint selection settings

### Phase 3: Data Pipeline (Week 2)

- [ ] Extend `DIQA5000Dataset` for training
  - [ ] Create `DIQA5000TrainingDataset` wrapper
  - [ ] Add augmentation pipelines (Phase 1, Phase 2)
  - [ ] Add proper DataLoader creation

- [ ] Verify DIQA-5000 GCS upload
  - [ ] Confirm train/val/test splits available
  - [ ] Verify CSV format and image paths
  - [ ] Test download from Modal container

### Phase 4: Training Run (Week 2-3)

- [ ] Run Phase 1 training (10 epochs)
  - [ ] Monitor loss convergence
  - [ ] Validate SRCC_sharpness improving
  - [ ] Save checkpoints

- [ ] Run Phase 2 training (20 epochs)
  - [ ] Monitor backbone fine-tuning stability
  - [ ] Track differential learning rates
  - [ ] Save checkpoints

- [ ] Checkpoint selection
  - [ ] Apply weighted SRCC/ECE scoring
  - [ ] Select best sharpness specialist checkpoint
  - [ ] Export final model

### Phase 5: Validation (Week 3)

- [ ] Benchmark on DIQA-5000 test set
  - [ ] Compute SRCC per dimension
  - [ ] Compute ECE per dimension
  - [ ] Compare against baseline (SRCC 0.213 → target 0.88)

- [ ] Integration with Arena
  - [ ] Register fine-tuned model in benchmark suite
  - [ ] Generate leaderboard entry
  - [ ] Document performance improvements

- [ ] Create MODEL_CARD.md
  - [ ] Training details
  - [ ] Performance metrics with CIs
  - [ ] Usage examples
  - [ ] Limitations

---

## 9. Risk Mitigation

### 9.1 Potential Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Overfitting on 3.5K samples | Medium | High | Strong augmentation, early stopping, dropout |
| Domain shift (natural → document) | Medium | Medium | Two-phase training, low backbone LR |
| SRCC target not achievable | Low | High | Fallback to ensemble without MUSIQ specialist |
| PyIQA API changes | Low | Medium | Pin version, implement fallback loading |

### 9.2 Fallback Strategies

1. **If SRCC < 0.80 after training:**
   - Increase Phase 2 epochs to 30
   - Try smaller backbone learning rate (5e-6)
   - Consider data augmentation adjustments

2. **If overfitting observed:**
   - Reduce Phase 2 epochs
   - Increase dropout to 0.2
   - Add weight decay regularization

3. **If training unstable:**
   - Reduce batch size to 16
   - Add gradient clipping (max_norm=1.0)
   - Use warmup learning rate schedule

---

## 10. Appendix: Configuration Reference

### 10.1 Full Training Configuration

```python
@dataclass
class MUSIQTrainingConfig:
    """Complete configuration for MUSIQ fine-tuning.

    Aligned with DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1 and
    consensus recommendations (warmup + cosine decay LR schedule).
    """

    # Model architecture
    head_hidden_dim: int = 256
    dropout: float = 0.1

    # Phase 1: Head warmup
    phase1_epochs: int = 10
    phase1_lr: float = 1e-3
    phase1_warmup_epochs: int = 2  # Linear warmup per consensus
    phase1_freeze_backbone: bool = True

    # Phase 2: Full fine-tuning
    phase2_epochs: int = 20
    phase2_backbone_lr: float = 1e-5
    phase2_head_lr: float = 1e-4
    phase2_warmup_epochs: int = 3  # Linear warmup per consensus

    # Training
    batch_size: int = 32
    weight_decay: float = 1e-4
    gradient_clip_norm: float = 1.0

    # Loss weights (sharpness specialist)
    loss_weights: dict[str, float] = field(default_factory=lambda: {
        'overall': 0.2,
        'sharpness': 0.6,
        'color': 0.2,
    })

    # Checkpoint selection (Weighted SRCC + ECE scoring)
    checkpoint_preset: str = 'balanced'  # 70% SRCC, 30% ECE, ±0.02 band
    checkpoint_interval: int = 5

    # Early stopping
    early_stopping_patience: int = 10
    early_stopping_metric: str = 'srcc_sharpness'

    # LR schedule
    lr_schedule: str = 'warmup_cosine'  # Per consensus recommendations

    @property
    def total_epochs(self) -> int:
        return self.phase1_epochs + self.phase2_epochs
```

### 10.2 Expected Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Infrastructure | 3-4 days | Wrapper classes, loss functions, configs |
| Training Script | 2-3 days | Modal job, data pipeline |
| Training Run | 6-8 hours | Checkpoints, logs |
| Validation | 1-2 days | Benchmarks, MODEL_CARD |
| **Total** | **~1.5 weeks** | Production-ready MUSIQ specialist |

### 10.3 Estimated Costs

| Resource | Rate | Duration | Cost |
|----------|------|----------|------|
| Modal T4 GPU | ~$0.40/hr | 8 hours | ~$3.20 |
| GCS Storage | $0.02/GB/mo | 10 GB | ~$0.20/mo |
| **Total Training** | - | - | **~$3.50** |

---

*Document Version 1.0 - December 2025*
*Reference: DIQA-5000_Pseudo_Labels_v2.md Section 4.4A1*
