# Stream 4: Teacher Model Extension — Implementation Plan

**Date**: 2026-02-15
**Branch**: `claude/phase-10-stream-4-plan-jWl98`
**Status**: PLANNING
**Parent**: [PHASE_10_11_RESTRUCTURED_PLAN.md](PHASE_10_11_RESTRUCTURED_PLAN.md)
**Requirements**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md)

---

## 1. Objective

Extend the existing SigLIP2-IQA model (86M params, VQualA 0.886) with five new task heads for multi-task document analysis, producing a single forward-pass teacher model that replaces separate heuristic detectors with higher-accuracy ML predictions.

**Stream 4 produces the teacher model. Streams 7 and 8 consume it downstream for pseudo-labeling and student distillation.**

---

## 2. Dependencies & Prerequisites

### 2.1 Upstream Dependencies (Must Be Complete)

| Dependency | Source | Status | Required By |
|---|---|---|---|
| SigLIP2-IQA base model checkpoint | Phase 3 / `modal/train_siglip2_iqa_v2.py` | ✅ Trained (VQualA 0.886) | Model architecture |
| Stream 1 schema extensions | `schema.py` + `config/` | ✅ Complete (59 tests) | Schema alignment |
| `config/script_ml_classes.yaml` | Stream 1 | ✅ Planned | Script class mapping |
| `ISO15924Script` enum | `schema_utils/iso_language_script.py` | ✅ Exists | Script classes |
| `CaptureMethod` enum | `annotation/schemas/enums.py` | ✅ Exists | Source classification |
| Heuristic baselines (Stream 3) | `results/stream3_benchmarks/GO_NOGO_DECISION.md` | ✅ Complete | Go/No-Go thresholds confirmed |

### 2.1.1 Stream 3 Go/No-Go Results (Confirmed 2026-02-14)

Stream 3 benchmarks confirm all five Stream 4 heads are needed. Results from
`results/stream3_benchmarks/GO_NOGO_DECISION.md`:

| Detector | Score | Target | Decision | Impact on Stream 4 |
|---|---|---|---|---|
| ScriptDetectorHeuristic | 15.6% acc | 80% | FAIL | Script head required — heuristic unusable |
| DocumentSourceClassifier | 64.7% acc | 85% | FAIL | Source head required |
| ShadowDetector | 60.1% F1 | 85% | FAIL | Shadow head required |
| **WarpingDetector** | **94.7% F1** | **80%** | **PASS** | Binary detection ships as heuristic; warping head provides continuous severity regression for DoclingRouter routing and improves per-type accuracy (WarpDoc types: 70–74% F1) |
| HandwritingDetector | 5.3% F1 | 75% | FAIL | Deferred to later stream (see §11) |
| OrientationDetector | not run | 85% | — | Separately validated at ~85%; ML target 98%+ |

**Key implication**: The warping heuristic is sufficient for binary detection (94.7%). The
warping regression head in this plan is retained for two reasons:

1. Continuous severity score (0–1) required by `DoclingRoutingEngine` for VLM escalation
   threshold logic (`warping_score > 0.75` → extreme warping → VLM)
2. Per-type warping accuracy on WarpDoc is only 70–74% F1; regression improves these cases

### 2.2 Dataset Availability (Updated 2026-02-15)

The project now has **59 source datasets** (up from 51 at original planning) and **10 assembled training datasets** (~503K total). Several datasets that were gaps at planning time are now ready.

#### Assembled Training Datasets (Purpose-Built)

| # | Training Dataset | Images | Head Group | Status | Change Since Plan |
|---|---|-------:|---|---|---|
| 1 | **Orientation** | 50,000 | G3 / MNV4 | ✅ Ready | Unchanged |
| 2 | **Skew** | 90,412 | G3 / MNV4 | ✅ Ready (GCS `skew_training/`) | **NEW — was a gap** |
| 3 | **Resolution Quality** | 30,000 target (5.5K done) | G5 / MNV4 | 🔄 In progress | **NEW — PaddleOCR pipeline** |
| 4 | **IQA Curated** | 16,000 | G1 | 🔄 In progress | Unchanged |
| 5 | **IQA Synthetic** | 100,000 | G1 | 📋 Planned | Unchanged |
| 6 | **Script Detection** | 108,000 target | G2 | 🔄 Generating | **CHANGED — now 108 scripts from OpenLID v2** |
| 7 | **Handwriting** | 60,000 | G4 | 📋 Planned | Out of Stream 4 scope |
| 8 | **Capture Method** | 50,000 | G5 | 📋 Planned | Stream 4 uses subset |
| 9 | **Shadow** | 15,000 | G5 | 📋 Planned | **NEW sources: sd7k, wsrd** |
| 10 | **Warping** | 20,000 | G5 | 📋 Planned | **NEW sources: warpdoc, anyphotodoc6300** |

#### Source Datasets Available Per Head (Stream 4 Scope)

| Head | Source Datasets | Total Images | Status |
|---|---|---|---|
| **Script** | synth-multiscript-v3 (350,012, 27 scripts, ⚠️ imbalanced dist.), MDIW13 (290K, 13 scripts), SIW13 (16K), CVSI (10K), tibhcr (142K), hindi-synth (80K), arabic-docs (10K), Script Detection assembled (108K generating from 108 scripts via OpenLID v2) | **~950K+** available | ✅ Ample data; v2 (250K) DELETED; v3 complete on GCS; OpenLID v2 generation in progress |
| **Script (eval)** | MLT-2019 (10K, 10 languages) | 10K | ✅ RESERVED for eval |
| **Document Source** | SmartDoc-QA (4.3K camera), RVL-CDIP (16K scanned), DocLayNet (81K born-digital), tobacco800 (1.3K scanned), realdae (1.2K camera), midv500 (3.6K camera) | **~107K** available | ✅ Labels extractable from metadata |
| **Orientation** | Assembled orientation dataset (50K, 4-class) | 50K | ✅ Ready |
| **Shadows** | sd7k (7,239 paired GT), wsrd (4,500 paired GT), realdae (1,200 camera), doc3d (102K 3D info) | **~115K** total | ✅ sd7k + wsrd are paired GT; enrichment feasible |
| **Warping** | warpdoc (1,020 paired GT, 6 warping types), anyphotodoc6300 (6,306 paired GT), doc3d (102K warping mesh), docalign12k (~12K aligned pairs), docreal (200 paired GT), SmartDoc-QA (4.3K perspective) | **~126K** total | ✅ Multiple paired GT sources |

**Key improvements since original plan**:

1. **Skew dataset assembled** (90K) — eliminates a major blocker
2. **Script detection expanding** from 27 scripts (synth-multiscript) to 108 scripts (OpenLID v2 generation)
3. **Shadow/warping sources identified**: sd7k (7K) + wsrd (4.5K) provide direct paired GT for shadow severity labeling; warpdoc + anyphotodoc6300 provide warping GT
4. **MobileNetV4 skew already trained**: val MAE=0.837, orient_acc=99.5%, CPU 17.5ms — validates the architecture
5. **59 total source datasets** with Layer 2 aggregates for 57 datasets

### 2.3 Infrastructure

| Resource | Availability | Notes |
|---|---|---|
| Modal A10G/A100 GPU | ✅ Ready | 40GB+ VRAM for multi-task training |
| GCS bucket `image_detection_b` | ✅ Ready | Dataset storage |
| Modal volumes | ✅ Ready | `siglip2-iqa-results` + dataset volumes |
| HuggingFace `transformers` | ✅ 4.51+ | SigLIP2 support |
| PyTorch 2.5+ | ✅ Installed | Training framework |

---

## 3. Architecture

### 3.1 Model: `SigLIP2MultiTaskTeacher`

Extends `SigLIP2DocumentIQAv2` by adding five detection head groups alongside the existing three IQA heads. The shared 768-dim feature vector from the SigLIP2 ViT-B/16 backbone feeds all heads.

```text
SigLIP2 ViT-B/16 Backbone (86M params, 784 max patches)
    |
Shared Feature Vector (768-dim)
    |
    ├── IQA Heads (EXISTING, from train_siglip2_iqa_v2.py)
    │   ├── overall:   Linear(768→256) → ReLU → Dropout(0.3) → Linear(256→2) [mu, σ²]
    │   ├── sharpness: Linear(768→256) → ReLU → Dropout(0.3) → Linear(256→2) [mu, σ²]
    │   └── color:     Linear(768→256) → ReLU → Dropout(0.3) → Linear(256→2) [mu, σ²]
    │
    ├── Script Head (NEW)
    │   └── script: Linear(768→256) → ReLU → Dropout(0.3) → Linear(256→N) [N=12 classes]
    │
    ├── Document Source Head (NEW)
    │   └── source: Linear(768→64) → ReLU → Linear(64→3) [scanned/camera/digital]
    │
    ├── Orientation Head (NEW)
    │   └── orient: Linear(768→64) → ReLU → Linear(64→4) [0°/90°/180°/270°]
    │
    ├── Shadow Head (NEW)
    │   └── shadow: Linear(768→64) → ReLU → Linear(64→2) [mu, σ]
    │
    └── Warping Head (NEW)
        └── warp: Linear(768→64) → ReLU → Linear(64→2) [mu, σ]

Total: ~88M params (86M backbone + ~2M heads)
```

### 3.2 Head Architecture Design Decisions

| Head | Type | Output Dim | Hidden Dim | Rationale |
|---|---|---|---|---|
| Script | Classification | 12 | 256 | Largest class count; needs capacity for CJK/Tibetan disambiguation |
| Document Source | Classification | 3 | 64 | Small class count; lightweight head sufficient |
| Orientation | Classification | 4 | 64 | Small class count; clear visual signals |
| Shadow | Regression | 2 (mu, σ) | 64 | Continuous severity; uncertainty for calibration |
| Warping | Regression | 2 (mu, σ) | 64 | Continuous severity; uncertainty for calibration |

### 3.3 Script Classes

The three-tier script architecture (Stream 1) supports both the original 12-class grouping and the expanded 108-class coverage now possible via OpenLID v2 generation.

**Decision point**: The Script Detection assembled dataset (#6) is being generated with 108 scripts from OpenLID v2. This changes the training approach:

#### Option A: 12-Class Grouped (Original Plan)

Train with 12 ML classes grouped from ISO 15924. Simpler, faster convergence, sufficient for routing.

| Index | ML Class | ISO 15924 Codes | Notes |
|---|---|---|---|
| 0 | LATN | Latn | Latin scripts |
| 1 | CYRL | Cyrl | Cyrillic |
| 2 | GREK | Grek | Greek |
| 3 | ARAB | Arab | Arabic, Persian, Urdu |
| 4 | HEBR | Hebr | Hebrew |
| 5 | DEVA | Deva, Beng, Taml, Telu | Indic scripts (grouped) |
| 6 | HANS | Hans, Hant | Chinese simplified + traditional |
| 7 | JPAN | Jpan | Japanese (Hiragana, Katakana, Kanji) |
| 8 | KORE | Kore | Korean (Hangul) |
| 9 | THAI | Thai | Thai |
| 10 | TIBT | Tibt | Tibetan |
| 11 | OTHER | All remaining | Catch-all for rare scripts |

#### Option B: Expanded Classes (Leveraging OpenLID v2)

Train with N classes where N matches the OpenLID v2 script generation (up to 108). Higher granularity, better routing, but requires more training data per class and longer convergence.

**Recommendation**: Start with **Option A (12 classes)** for Stream 4 Phase 1. The `config/script_ml_classes.yaml` mapping allows expanding to Option B without retraining the backbone — only the script head output dimension changes. This de-risks the initial training run while preserving the path to full 108-script coverage in a follow-up iteration.

---

## 4. Implementation Phases

### Phase A: Model Architecture & Dataset Loaders (3-4 days)

**Goal**: Build the multi-task model class and all dataset loading infrastructure.

#### A.1 Create `SigLIP2MultiTaskTeacher` Class

**File**: `modal/train_siglip2_multitask.py` (NEW)

**Approach**: Extend from `SigLIP2DocumentIQAv2` patterns in `train_siglip2_iqa_v2.py`.

```python
class SigLIP2MultiTaskTeacher(nn.Module):
    """SigLIP2 backbone + IQA heads + 5 detection heads."""

    def __init__(
        self,
        model_id: str = "google/siglip2-base-patch16-naflex",
        pretrained_iqa_path: str | None = None,
        num_script_classes: int = 12,
        num_source_classes: int = 3,
        num_orientation_classes: int = 4,
    ): ...

    def load_iqa_checkpoint(self, path: str) -> None:
        """Load pretrained IQA backbone + heads, freeze them."""

    def freeze_backbone(self) -> None: ...
    def freeze_iqa_heads(self) -> None: ...
    def unfreeze_backbone(self) -> None: ...

    def forward(
        self,
        pixel_values: torch.Tensor,
        spatial_shapes: torch.Tensor | None = None,
        tasks: list[str] | None = None,
    ) -> dict[str, dict | torch.Tensor]: ...
```

Key implementation details:

- Load pretrained backbone + IQA heads from v2 checkpoint
- New heads initialized with Xavier uniform
- `tasks` parameter enables selective head execution (reduces compute for single-task inference)
- Classification heads return raw logits (softmax applied in loss or post-processing)
- Regression heads return `{mu, sigma_sq}` dicts (same pattern as IQA heads)

#### A.2 Dataset Loaders

**File**: `modal/train_siglip2_multitask.py` (dataset classes in same file, following existing pattern)

| Loader | Source Format | Labels | Key Logic |
|---|---|---|---|
| `ScriptDataset` | Image files + JSON manifest | ISO 15924 → ML class index | Reads `script_ml_classes.yaml` mapping |
| `DocumentSourceDataset` | Image files + metadata JSON | `CaptureMethod` enum → index | 3-class mapping |
| `OrientationDataset` | Images at `orientation/` | 0/90/180/270 → index | Pre-rotated images with GT label |
| `ShadowWarpingDataset` | Image files + scores JSON | 0-1 float | Paired with uncertainty if available |
| `MultiTaskDataset` | Union of all above | Per-sample task mask | Handles missing labels gracefully |

`MultiTaskDataset` is the critical class — it must handle:

- Samples that have labels for only a subset of tasks
- Per-task loss masking (don't backprop on missing labels)
- Balanced sampling across task groups (prevent IQA domination)

#### A.3 Config File

**File**: `config/siglip2_multitask.yaml` (NEW)

```yaml
model:
  backbone: "google/siglip2-base-patch16-naflex"
  max_num_patches: 784
  pretrained_iqa_checkpoint: "siglip2_iqa_best.pt"

heads:
  iqa:
    dimensions: ["overall", "sharpness", "color"]
    hidden_dim: 256
    uncertainty: true
    freeze_during_phase1: true
  script:
    num_classes: 12
    hidden_dim: 256
    dropout: 0.3
    class_weights: "balanced"  # auto-compute from dataset distribution
  document_source:
    num_classes: 3
    hidden_dim: 64
  orientation:
    num_classes: 4
    hidden_dim: 64
  shadow:
    hidden_dim: 64
    uncertainty: true
  warping:
    hidden_dim: 64
    uncertainty: true

training:
  phase1:
    description: "Frozen backbone, train new heads only"
    epochs: 15
    lr: 2e-4
    freeze_backbone: true
    freeze_iqa_heads: true
  phase2:
    description: "Unfreeze backbone with low LR"
    epochs: 30
    lr: 1e-5
    backbone_lr_multiplier: 0.1
    iqa_lr_multiplier: 0.01  # Protect IQA performance
    use_pcgrad: true

loss:
  script: "cross_entropy"
  document_source: "cross_entropy"
  orientation: "cross_entropy"
  shadow: "gaussian_nll"
  warping: "gaussian_nll"
  iqa: "norm_in_norm + gaussian_nll"

  task_weights:
    iqa: 1.0       # Protect existing performance
    script: 1.0     # Primary new task
    source: 0.5     # Secondary
    orientation: 0.5
    shadow: 0.3     # Lower priority
    warping: 0.3
```

#### A.4 Deliverables

- [ ] `SigLIP2MultiTaskTeacher` model class with selective task execution
- [ ] `MultiTaskDataset` with per-sample task masking
- [ ] Individual dataset loaders (Script, Source, Orientation, Shadow/Warping)
- [ ] `config/siglip2_multitask.yaml` configuration
- [ ] Unit tests for model forward pass (all head combinations)
- [ ] Unit tests for dataset loaders (mock data)

---

### Phase B: Training Script & Loss Functions (2-3 days)

**Goal**: Complete Modal training script with multi-task loss, PCGrad, and phased training.

#### B.1 Training Loop

**File**: `modal/train_siglip2_multitask.py` (extend)

Follows the two-phase training strategy from the restructured plan:

```text
Phase 1 (15 epochs): Frozen backbone + frozen IQA heads
  → Train ONLY new detection heads
  → LR: 2e-4 with CosineAnnealingLR
  → Gradient accumulation: 4 steps
  → Mixed precision: BF16

Phase 2 (30 epochs, OPTIONAL): Unfreeze everything
  → Low backbone LR (0.1x multiplier)
  → Very low IQA LR (0.01x multiplier)
  → PCGrad for gradient conflict resolution
  → LLRD: 0.9 decay per layer
  → EMA in last 10 epochs
```

#### B.2 Multi-Task Loss

```python
class MultiTaskLoss(nn.Module):
    """Combined loss with per-task weighting and missing-label masking."""

    def forward(
        self,
        predictions: dict[str, torch.Tensor],
        targets: dict[str, torch.Tensor],
        task_masks: dict[str, torch.Tensor],  # Binary mask: 1=has label, 0=missing
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """Compute weighted sum of per-task losses, masking missing labels."""

        total_loss = 0.0
        loss_dict = {}

        for task_name, pred in predictions.items():
            if task_name not in targets:
                continue

            mask = task_masks.get(task_name)
            if mask is not None and mask.sum() == 0:
                continue  # No labels for this task in this batch

            if task_name in CLASSIFICATION_TASKS:
                loss = F.cross_entropy(pred, targets[task_name], reduction="none")
            elif task_name in REGRESSION_TASKS:
                loss = gaussian_nll_loss(pred, targets[task_name])
            else:
                loss = norm_in_norm_loss(pred, targets[task_name])

            if mask is not None:
                loss = (loss * mask).sum() / mask.sum()
            else:
                loss = loss.mean()

            weighted = loss * self.task_weights[task_name]
            total_loss += weighted
            loss_dict[task_name] = loss.item()

        return total_loss, loss_dict
```

#### B.3 PCGrad Integration

Re-use the PCGrad implementation already present in `train_siglip2_iqa_v2.py`, extending it for 8 tasks (3 IQA + 5 detection):

```python
def pcgrad_backward(task_losses: dict[str, torch.Tensor], optimizer):
    """Project conflicting gradients across tasks."""
    # Compute per-task gradients
    task_grads = {}
    for task_name, loss in task_losses.items():
        optimizer.zero_grad()
        loss.backward(retain_graph=True)
        task_grads[task_name] = [p.grad.clone() for p in model.parameters() if p.grad is not None]

    # Project conflicts
    for i, (name_i, grads_i) in enumerate(task_grads.items()):
        for name_j, grads_j in list(task_grads.items())[i+1:]:
            # If gradients conflict (negative cosine similarity), project
            cos_sim = sum(
                (gi * gj).sum() for gi, gj in zip(grads_i, grads_j)
            )
            if cos_sim < 0:
                # Project out conflicting component
                ...
```

#### B.4 Balanced Batch Sampling

```python
class MultiTaskBatchSampler:
    """Ensure each batch has samples from all task groups.

    Problem: Script dataset is 250K, orientation is 50K, shadows is 15K.
    Without balancing, script dominates training.

    Solution: Round-robin across task groups, with within-task shuffling.
    Each batch: ~25% IQA, ~25% script, ~25% orientation/source, ~25% shadow/warping
    """
```

#### B.5 Deliverables

- [ ] `MultiTaskLoss` with per-task weighting and missing-label masking
- [ ] PCGrad integration for 8-task gradient conflict resolution
- [ ] Two-phase training loop (frozen → unfrozen)
- [ ] `MultiTaskBatchSampler` for balanced task representation
- [ ] LLRD optimizer setup for multi-task (different LR per head group)
- [ ] Training metrics: per-task loss, overall loss, per-task accuracy
- [ ] Checkpoint saving with head-group versioning
- [ ] Modal app definition with A100 40GB GPU

---

### Phase C: Dataset Preparation & Upload (2-3 days, parallel with A/B)

**Goal**: Prepare all training data and upload to GCS. Significant progress has been made since the original plan — several datasets that were gaps are now available.

#### C.1 Script Dataset Assembly

**Sources** (much richer than original plan):

- synth-multiscript-v3 (350,012, 27 scripts, GCS) ✅ Ready — ⚠️ Imbalanced distribution; rebalancing needed
- MDIW13 (290K, 13 scripts, GCS) ✅ Ready
- SIW13 (16K, 13 scripts) ✅ Ready
- CVSI (10K, 10 scripts) ✅ Ready
- tibhcr (142K Tibetan) ✅ Ready — **eliminates original Tibetan gap**
- hindi-synth (80K Hindi/Devanagari) ✅ Ready
- Script Detection assembled (108K, 108 scripts from OpenLID v2) 🔄 Generating

Tasks:

- [ ] Verify GCS paths and accessibility for synth-multiscript-v3 and MDIW13
- [ ] Assess OpenLID v2 generation progress — determine if 108K script dataset will be ready for Stream 4 training
- [ ] Create ISO 15924 → 12-class mapping in `config/script_ml_classes.yaml` (if not done in Stream 1)
- [ ] Write `ScriptDataset` manifest generator:
  - Map source script labels to ML class indices
  - **Tibetan coverage**: tibhcr provides 142K samples (was critical gap at ~5K)
  - Split by document ID (prevent leakage across train/val/test)
  - Target: 200K+ train, 25K val, 25K test
  - Stratified split ensuring minimum 1,000 samples per class per split
- [ ] Handle class imbalance:
  - Compute class weights for weighted cross-entropy
  - Document per-class sample counts
  - Consider downsampling Latin/CJK to prevent domination

#### C.2 Orientation Dataset

**Source**: Assembled orientation dataset (50K, 4-class) ✅ Ready at `E:\03_training_datasets\orientation\`

Tasks:

- [ ] Verify orientation dataset is accessible or upload to GCS
- [ ] Verify label format (filename or sidecar JSON with rotation angle)
- [ ] Create manifest with 4-class labels (0/90/180/270)
- [ ] Split: 40K train, 5K val, 5K test (by document ID, pre-rotation)
- [ ] Note: MobileNetV4 already achieves 99.5% orient accuracy — SigLIP2 orientation head is for redundancy/validation

#### C.3 Document Source Dataset

**Sources** (much richer than original plan):

- SmartDoc-QA (4.3K camera, Audit A 92) ✅ Ready
- RVL-CDIP (16K scanned, Audit B 87) ✅ Ready
- DocLayNet (81K born-digital, Audit A 96) ✅ Ready
- tobacco800 (1.3K scanned, Audit A 91) ✅ Ready
- realdae (1.2K camera, Audit B 84) ✅ Ready
- midv500 (3.6K camera, MIT license) ✅ Ready

Tasks:

- [ ] Extract capture method from Layer 2 aggregates (57 datasets have metadata)
- [ ] Map to 3 classes: scanned, camera, digital
  - Camera: SmartDoc-QA + realdae + midv500 (~9K)
  - Scanned: RVL-CDIP + tobacco800 (~17K)
  - Digital: DocLayNet born-digital subset (~30K)
- [ ] Subsample digital class to prevent domination (target ~10K per class)
- [ ] Upload assembled dataset to GCS
- [ ] Split: 80/10/10 stratified

#### C.4 Shadow Dataset

**Sources** (new paired GT datasets available):

- sd7k (7,239 paired GT: shadow/clean) ✅ Ready — **best source for severity labels**
- wsrd (4,500 paired GT: shadow/clean, Audit A 95) ✅ Ready
- realdae (1,200 camera) ✅ Ready
- doc3d (102K with 3D illumination data) ✅ Available

Tasks:

- [ ] Extract shadow severity scores from sd7k + wsrd paired images
  - Compute severity = SSIM difference between shadow and clean images
  - Normalize to 0-1 scale
- [ ] Sample clean images (no shadows) from DocLayNet/TableBank for negative examples
- [ ] Create paired JSON labels (image_path → shadow_score 0-1)
- [ ] Upload to GCS
- [ ] Target: 15K (7K sd7k + 4.5K wsrd + 3.5K negatives from clean docs)

#### C.5 Warping Dataset

**Sources** (new paired GT datasets available):

- warpdoc (1,020 paired GT, 6 warping types, Audit B 85) ✅ Ready
- anyphotodoc6300 (6,306 paired GT corrected/distorted, Audit A 92) ✅ Ready
- docalign12k (~12K aligned pairs) ✅ Ready
- docreal (200 paired GT, MIT) ✅ Ready
- SmartDoc-QA (4.3K perspective metadata) ✅ Ready
- doc3d (102K with warping mesh data) ✅ Available

Tasks:

- [ ] Extract warping severity from warpdoc + anyphotodoc6300 paired images
  - Compute severity from distortion magnitude between distorted/flat pairs
  - warpdoc provides 6 warping types (book spine, fold, crumple, etc.)
- [ ] Use doc3d warping mesh data for additional samples
- [ ] Add clean documents as negative examples (warping_score = 0.0)
- [ ] Create paired JSON labels (image_path → warping_score 0-1)
- [ ] Upload to GCS
- [ ] Target: 20K (1K warpdoc + 6K anyphotodoc + 4K doc3d + 4K SmartDoc + 5K negatives)

#### C.6 Deliverables

- [ ] All datasets on GCS with manifests
- [ ] `config/script_ml_classes.yaml` with ISO 15924 → 12-class mapping
- [ ] Per-class sample count report with class weight recommendations
- [ ] Train/val/test split manifests (JSON format)
- [ ] Data loading smoke test on Modal (verify GCS access)
- [ ] Dataset summary documenting source provenance per training sample

---

### Phase D: Training Execution (3-5 days)

**Goal**: Run multi-task training on Modal, achieve accuracy targets.

#### D.1 Phase 1 Training (Frozen Backbone)

```bash
# Launch training on Modal A100
uv run modal run --detach modal/train_siglip2_multitask.py \
    --phase 1 \
    --epochs 15 \
    --batch-size 8 \
    --accumulation 4 \
    --lr 2e-4

# Monitor
modal app logs siglip2-multitask-training --follow
```

**Expected Phase 1 outcomes** (new heads only, backbone frozen):

- Script accuracy: 80-85% (backbone features already discriminative)
- Orientation accuracy: 90-95%
- Source accuracy: 85-90%
- Shadow MAE: <0.15
- Warping MAE: <0.15
- IQA VQualA: unchanged (heads frozen)

#### D.2 Phase 2 Training (Optional, Joint Fine-Tuning)

Only execute if Phase 1 falls short of targets.

```bash
uv run modal run --detach modal/train_siglip2_multitask.py \
    --phase 2 \
    --pretrained-checkpoint /results/multitask/phase1_best.pt \
    --epochs 30 \
    --backbone-lr-multiplier 0.1 \
    --iqa-lr-multiplier 0.01 \
    --use-pcgrad
```

**Phase 2 Go/No-Go criteria**:

| Task | Phase 1 Target | Phase 2 Trigger |
|---|---|---|
| Script | ≥ 85% | If < 85%, run Phase 2 |
| Orientation | ≥ 95% | If < 95%, run Phase 2 |
| Source | ≥ 90% | If < 90%, run Phase 2 |
| Shadow MAE | ≤ 0.12 | If > 0.12, run Phase 2 |
| IQA VQualA | ≥ 0.88 | If < 0.88 (regression), STOP and investigate |

#### D.3 IQA Regression Guard

**Critical**: IQA VQualA must not drop below 0.86 during joint training. If it does:

1. Increase `iqa_lr_multiplier` from 0.01 → 0.001 (more protection)
2. Increase `iqa` task weight from 1.0 → 2.0
3. If still regressing, freeze IQA heads entirely in Phase 2

#### D.4 Deliverables

- [ ] Phase 1 training run complete
- [ ] Phase 1 accuracy report (per-task metrics)
- [ ] Go/No-Go decision for Phase 2
- [ ] Phase 2 training run (if triggered)
- [ ] Final model checkpoint (`siglip2_multitask_best.pt`)
- [ ] Training curves (loss, per-task accuracy)
- [ ] IQA regression analysis (VQualA before/after)

---

### Phase E: Evaluation & Benchmarking (2 days)

**Goal**: Comprehensive accuracy benchmarks on held-out test sets.

#### E.1 Accuracy Benchmarks

| Task | Heuristic Baseline | Teacher Target | Eval Dataset | Metric |
|---|---|---|---|---|
| Script Detection | 70-80% | 92-95% | MLT-2019 test (RESERVED) | Top-1 accuracy |
| Document Source | 80-90% | 94-97% | SmartDoc-QA test | Top-1 accuracy |
| Orientation | 85% (ensemble) | 98%+ | Orientation test (5K) | Top-1 accuracy |
| Shadows | 85% (heuristic) | 90%+ | RealDAE test | MAE, correlation |
| Warping | 80-90% (heuristic) | 92%+ | SmartDoc-QA test | MAE, correlation |
| IQA (protection) | VQualA 0.886 | ≥ 0.886 | DIQA-5000 test | VQualA |

#### E.2 Confusion Matrix Analysis

For each classification head:

- Full confusion matrix on test set
- Per-class precision, recall, F1
- Identification of systematic errors (e.g., CJK confusion, rare script failures)
- Confidence calibration analysis (ECE, reliability diagram)

#### E.3 Latency Benchmarks

| Configuration | Target | Measurement |
|---|---|---|
| All heads, GPU (A10) | < 60ms/page | torch.cuda.Event timing |
| All heads, CPU | < 500ms/page | time.perf_counter |
| Script head only, GPU | < 55ms/page | Selective execution |
| IQA heads only, GPU | < 55ms/page | Selective execution (regression test) |

#### E.4 Deliverables

- [ ] Accuracy report with confusion matrices
- [ ] Calibration analysis (ECE per head)
- [ ] Latency benchmark report
- [ ] IQA regression test (VQualA comparison)
- [ ] Failure case analysis with example images
- [ ] Model card documentation

---

### Phase F: Production Inference Wrapper (2 days)

**Goal**: Create inference module usable by the pipeline.

#### F.1 Inference Wrapper

**File**: `src/image_preprocessing_detector/detection/siglip2_multitask.py` (NEW)

```python
class SigLIP2MultiTaskInference:
    """Production inference wrapper for SigLIP2 multi-task teacher.

    Usage:
        detector = SigLIP2MultiTaskInference(
            checkpoint_path="models/siglip2_multitask_best.pt"
        )
        results = detector.predict(image, tasks=["script", "orientation"])
    """

    def __init__(
        self,
        checkpoint_path: str,
        device: str = "auto",
        use_onnx: bool = False,
    ): ...

    def predict(
        self,
        image: np.ndarray | PIL.Image.Image,
        tasks: list[str] | None = None,
    ) -> MultiTaskPrediction: ...

    def predict_batch(
        self,
        images: list[np.ndarray],
        tasks: list[str] | None = None,
        batch_size: int = 8,
    ) -> list[MultiTaskPrediction]: ...


@dataclass
class MultiTaskPrediction:
    """Structured prediction output."""
    # IQA
    iqa_overall: float
    iqa_sharpness: float
    iqa_color: float
    iqa_uncertainty: dict[str, float]

    # Script
    script_class: str  # ML class label (e.g., "LATN")
    script_confidence: float
    script_distribution: dict[str, float]  # Full softmax

    # Orientation
    orientation_angle: int  # 0, 90, 180, 270
    orientation_confidence: float

    # Source
    source_class: str  # "scanned", "camera", "digital"
    source_confidence: float

    # Shadow / Warping
    shadow_score: float
    shadow_uncertainty: float
    warping_score: float
    warping_uncertainty: float
```

#### F.2 ONNX Export

```python
def export_to_onnx(
    model: SigLIP2MultiTaskTeacher,
    output_path: str,
    opset_version: int = 17,
):
    """Export model to ONNX for production inference.

    Separate ONNX files per head group for flexible deployment:
    - siglip2_backbone.onnx (shared)
    - siglip2_iqa_heads.onnx
    - siglip2_detection_heads.onnx
    """
```

#### F.3 Deliverables

- [ ] `SigLIP2MultiTaskInference` class with batch support
- [ ] `MultiTaskPrediction` dataclass
- [ ] ONNX export script
- [ ] Integration test with real images
- [ ] Device auto-detection (GPU/CPU fallback)
- [ ] Model loading from checkpoint or ONNX

---

## 5. File Inventory

### New Files

| File | Purpose | Est. Lines |
|---|---|---|
| `modal/train_siglip2_multitask.py` | Multi-task training script (Modal) | ~2,500 |
| `src/image_preprocessing_detector/detection/siglip2_multitask.py` | Production inference wrapper | ~400 |
| `config/siglip2_multitask.yaml` | Multi-task model configuration | ~80 |
| `scripts/prepare_multitask_datasets.py` | Dataset assembly and manifest generation | ~500 |
| `tests/unit/test_siglip2_multitask.py` | Unit tests for model and inference | ~400 |
| `tests/unit/test_multitask_dataset.py` | Unit tests for dataset loaders | ~300 |

### Modified Files

| File | Change | Impact |
|---|---|---|
| `config/script_ml_classes.yaml` | Add 12-class mapping (may already exist from Stream 1) | LOW |
| `src/image_preprocessing_detector/models/__init__.py` | Export `SigLIP2MultiTaskInference` | LOW |

### Not Modified (Stream 4 scope boundary)

| File | Why Not | Owner |
|---|---|---|
| `schema.py` | Schema extensions are Stream 1 responsibility | Stream 1 |
| `routing/recommendation_engine.py` | Routing updates are Stream 5 responsibility | Stream 5 |
| `pipeline/enhanced_pipeline.py` | Pipeline integration is Stream 9 responsibility | Stream 9 |

---

## 6. Testing Strategy

### 6.1 Unit Tests

| Test File | Coverage |
|---|---|
| `test_siglip2_multitask.py` | Model forward pass, selective task execution, checkpoint loading |
| `test_multitask_dataset.py` | Dataset loading, task masking, balanced sampling |
| `test_multitask_loss.py` | Loss computation, missing-label masking, task weighting |

### 6.2 Integration Tests

| Test | Validates |
|---|---|
| `test_modal_training_smoke` | Modal app launches, trains 2 epochs, saves checkpoint |
| `test_checkpoint_roundtrip` | Save → load → predict gives identical results |
| `test_onnx_export` | ONNX export produces valid graph, matches PyTorch output |
| `test_iqa_preservation` | Loading pretrained IQA weights preserves VQualA |

### 6.3 Benchmark Tests

| Test | Pass Criteria |
|---|---|
| `test_latency_gpu` | All heads < 60ms on A10G |
| `test_latency_cpu` | All heads < 500ms on 4-core CPU |
| `test_memory_gpu` | < 6GB peak VRAM for batch=8 |

---

## 7. Risk Assessment (Updated 2026-02-15)

| Risk | Likelihood | Impact | Mitigation | Change |
|---|---|---|---|---|
| IQA performance regression during joint training | MEDIUM | HIGH | Freeze IQA heads in Phase 1; aggressive LR protection in Phase 2; regression monitoring | Unchanged |
| Script accuracy < 85% on Tibetan | **LOW** (was HIGH) | MEDIUM | tibhcr provides 142K Tibetan samples (was ~5K); massive improvement in data coverage | **REDUCED** — tibhcr dataset eliminates the critical Tibetan gap |
| PCGrad memory overhead with 8 tasks | MEDIUM | MEDIUM | Gradient accumulation (8 tasks × 4 steps); reduce batch size if OOM | Unchanged |
| Dataset quality issues (noisy labels) | LOW | MEDIUM | Label cleaning scripts; confidence-based sample weighting; Layer 2 audit grades (57 datasets audited) | Unchanged |
| Training wall-clock > 7 days on Modal | LOW | LOW | Background execution; early stopping; Phase 2 optional | Unchanged |
| CJK confusion (Chinese vs Japanese vs Korean) | **LOW** (was MEDIUM) | MEDIUM | synth-multiscript-v3 (350,012, 27 scripts) + MDIW13 (13 scripts) + jssoda (2K Japanese vert+horiz) + hindi-synth (80K Hindi) provide explicit script annotations; test on MLT-2019 | **REDUCED** — more diverse script data available |
| OpenLID v2 script generation not ready in time | MEDIUM | LOW | 108K dataset being generated; can proceed with synth-multiscript-v3 (350,012, 27 scripts) + MDIW13 (232K) as fallback | **NEW** — generation in progress |
| Shadow/warping severity label quality | LOW | MEDIUM | sd7k + wsrd provide paired GT (shadow/clean); SSIM-based severity computation is deterministic and reproducible | **REDUCED** — was higher risk when only Doc3D enrichment was planned |

---

## 8. Success Criteria

### Must-Have (Phase 1 completion)

- [ ] Script detection accuracy ≥ 85% on held-out test set
- [ ] Orientation accuracy ≥ 95%
- [ ] Document source accuracy ≥ 90%
- [ ] Shadow MAE ≤ 0.12
- [ ] Warping MAE ≤ 0.12
- [ ] IQA VQualA ≥ 0.86 (no regression beyond 0.026)
- [ ] Inference latency < 60ms/page on GPU

### Nice-to-Have (Phase 2 completion)

- [ ] Script detection accuracy ≥ 92%
- [ ] Orientation accuracy ≥ 98%
- [ ] IQA VQualA ≥ 0.88 (improved through joint training)
- [ ] ONNX export functional
- [ ] TorchScript export functional

---

## 9. Timeline

```text
Day 1-2:   Phase A.1 - Model architecture (SigLIP2MultiTaskTeacher)
Day 2-3:   Phase A.2 - Dataset loaders and MultiTaskDataset
Day 3-4:   Phase A.3 - Config + unit tests
Day 3-5:   Phase C   - Dataset preparation + GCS upload (PARALLEL with A/B)
Day 4-5:   Phase B.1 - Training loop + multi-task loss
Day 5-6:   Phase B.2 - PCGrad + balanced sampling + Modal app
Day 6-8:   Phase D.1 - Phase 1 training run (background on Modal)
Day 8-9:   Phase E   - Evaluation + benchmarking
Day 9:     Phase D.2 - Phase 2 Go/No-Go decision
Day 9-10:  Phase F   - Production inference wrapper
Day 10:    Phase D.2 - Phase 2 training (if triggered, background)

Total: 7-10 days (training runs in background)
```

---

## 10. Downstream Integration Points

### Stream 7 (Pseudo-Labeling Pipeline) — Consumes teacher

```python
# Stream 7 will use the teacher to generate pseudo-labels:
teacher = SigLIP2MultiTaskInference("siglip2_multitask_best.pt")
for image in unlabeled_corpus:
    prediction = teacher.predict(image)
    labels.append({
        "script_distribution": prediction.script_distribution,  # Full softmax
        "source_class": prediction.source_class,
        "orientation_angle": prediction.orientation_angle,
        "shadow_score": prediction.shadow_score,
        "warping_score": prediction.warping_score,
    })
```

### Stream 8 (Student Distillation) — Consumes teacher soft labels

The teacher's full probability distributions (not just argmax) are stored for knowledge distillation. The student learns from soft targets at temperature T=4.

### Stream 9 (Pipeline Integration) — Consumes inference wrapper

```python
# Stream 9 will integrate the inference wrapper into the pipeline:
self.multitask_detector = SigLIP2MultiTaskInference(checkpoint_path)
prediction = self.multitask_detector.predict(corrected_image)
page_result.script = prediction.script_class
page_result.shadow_score = prediction.shadow_score
# ...
```

---

## 11. Comparison: Plan vs SIGLIP2_MULTITASK_REQUIREMENTS.md

The restructured plan (Stream 4) takes a **narrower scope** than the full SIGLIP2 multitask requirements document. This is intentional — Stream 4 is the first iteration.

| Aspect | SIGLIP2_MULTITASK_REQUIREMENTS | Stream 4 (This Plan) | Rationale |
|---|---|---|---|
| Head groups | 5 groups, 19 heads | IQA (3) + 5 detection heads (8 total) | Skip handwriting heads (Group 4) — defer to later stream |
| Script classes | 10-20+ expandable | 12 fixed | Start with 12, expand via config after baseline |
| MobileNetV4 pre-correction | Full 3-head model | OUT OF SCOPE | Separate workstream; Stream 4 = teacher only |
| Handwriting assessment | 5 heads (3 cls + 2 reg) | DEFERRED | Requires label harmonization (3+ days); add in follow-up |
| Resolution quality | Regression head | DEFERRED | Part of MobileNetV4 scope |
| Training phases | 6 phases (IQA → Script → HW → Orient → PageAttr → Joint) | 2 phases (frozen → unfrozen) | Simpler iteration; add heads incrementally |
| Distillation | SigLIP2 → MobileCLIP-2 S4 → S0 | OUT OF SCOPE (Stream 8) | Teacher must be proven first |

**Key simplification**: Stream 4 focuses on the five highest-value detection heads (script, source, orientation, shadow, warping) that directly enable the DoclingRouter (Stream 5). Handwriting heads, resolution quality, and student distillation are deferred to subsequent streams where their dataset dependencies will be resolved.

---

## 12. Dataset Evolution Summary (Since Original Plan)

The dataset landscape has improved significantly since the PHASE_10_11_RESTRUCTURED_PLAN was written:

| Area | Original Plan State | Current State (2026-02-15) | Impact |
|---|---|---|---|
| **Total source datasets** | 51 | 59 (+8) | More diverse training data |
| **Layer 2 aggregates** | 20/51 | 57/59 | Better metadata for dataset selection |
| **Tibetan samples** | ~5,200 (CRITICAL gap) | **142K** (tibhcr 141,698) | Tibetan risk eliminated |
| **Skew training data** | ❌ Gap (need generation) | ✅ **90,412** assembled on GCS | Major blocker resolved |
| **Shadow paired GT** | None (need enrichment) | ✅ sd7k (7,239) + wsrd (4,500) | Direct severity labels available |
| **Warping paired GT** | SmartDoc-QA only (4.3K) | ✅ warpdoc (1K) + anyphotodoc (6.3K) + docalign12k (12K) + docreal (200) | Multiple paired GT sources |
| **Script classes** | 27 scripts (synth-multiscript) | **108 scripts** (OpenLID v2 generation in progress) | Path to fine-grained detection |
| **Hindi/Devanagari** | ~4K samples | ✅ **80K** (hindi-synth) | Indic coverage vastly improved |
| **Audit coverage** | Unknown | 52/55 audited (95%), mean 85.2 | Quality assurance for all datasets |
| **MobileNetV4 training** | Not started | ✅ Trained: orient_acc 99.5%, CPU 17ms | Architecture validated |
| **Japanese vertical** | Gap (needed 1,050 samples) | ✅ jssoda (2,000 vert+horiz) | Japanese coverage improved |

**Net assessment**: The dataset situation is substantially stronger than when Stream 4 was planned. The two critical gaps (Tibetan coverage and skew training data) have been resolved. Shadow/warping labeling now has direct paired GT sources instead of requiring indirect enrichment. The expanded script coverage from OpenLID v2 provides a clear path to fine-grained detection beyond the initial 12 classes.

---

**End of Implementation Plan**
