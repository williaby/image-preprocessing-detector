---
owner: docs-team
purpose: Documentation for Unified Labeling Strategy for Cross-Dataset Consistency.
schema_type: common
status: draft
tags:
- planning
- labeling
title: Unified Labeling Strategy for Cross-Dataset Consistency
---

**Date:** December 2025
**Status:** Strategic Planning Document

---

## Related Documents

### Strategic References

- [DeQA-Doc_Analysis_Deep_Dive.md](DeQA-Doc_Analysis_Deep_Dive.md) - VQualA 2025 winner methodology analysis
- [DIQA-5000_Pseudo_Labels_v2.md](DIQA-5000_Pseudo_Labels_v2.md) - Original multi-model ensemble approach

### Dataset Documentation

- [DATASET_CATALOG.md](../DATASET_CATALOG.md) - Inventory of all 22 datasets
- [dataset-taxonomy-coverage.md](../reference/dataset-taxonomy-coverage.md) - Label coverage matrix

### Existing Automated Labeling Pipeline

The current automated labeling infrastructure uses a **three-layer architecture**:

| Document | Purpose | Location |
|----------|---------|----------|
| **automated-data-labeling-pipeline.puml** | Pipeline architecture diagram | [docs/planning/](automated-data-labeling-pipeline.puml), [docs/architecture/](../architecture/diagrams/level-2/data-preparation/automated-data-labeling-pipeline.puml) |
| **labeling-workstreams-overview.puml** | Three-project labeling workstreams | [docs/development/labeling/](../development/labeling/labeling-workstreams-overview.puml) |
| **diqa-pseudo-labeling-workflow.puml** | DIQA-specific pseudo-labeling flow | [docs/planning/](diqa-pseudo-labeling-workflow.puml), [docs/architecture/](../architecture/diagrams/level-2/pseudo-labeling/diqa-pseudo-labeling-workflow.puml) |
| **metadata-versioning-schema.md** | Versioned metadata structure | [docs/reference/](../reference/metadata-versioning-schema.md) |
| **annotate_base_metadata.py** | Layer 1 (IMMUTABLE) + Layer 2 (ENRICHMENT) | [scripts/](../../scripts/annotate_base_metadata.py) |
| **build_training_labels.py** | Layer 3 (TRAINING) computation | [scripts/](../../scripts/build_training_labels.py) |

### Three-Layer Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Sample Metadata Record                       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: IMMUTABLE (annotate_base_metadata.py)                 │
│  ├── Source dataset labels (never modified)                     │
│  ├── Original file metadata (SHA256, dimensions, DPI)           │
│  └── Dataset-provided annotations (DIQA MOS, COCO bboxes)       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: ENRICHMENT (annotate_base_metadata.py)                │
│  ├── capture_method, domain classification                      │
│  ├── Phase 9 flags (has_table, has_formula, has_handwriting)   │
│  ├── Resolution analysis, versioned enrichments                 │
│  └── ★ NEW: Soft-label pseudo-predictions (this strategy)       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: TRAINING (build_training_labels.py)                   │
│  ├── Computed from IMMUTABLE + ENRICHMENT at training time      │
│  ├── 45-dim iqa_vector, anchor_score, anchor_source priority    │
│  └── ★ NEW: Soft-label distributions for KL-div training        │
└─────────────────────────────────────────────────────────────────┘
```

**This strategy extends the existing pipeline** by adding soft-label pseudo-predictions to Layer 2 (ENRICHMENT) and soft-label training support to Layer 3 (TRAINING)

---

## Executive Summary

We have **~2.5M images across 22 datasets** with **inconsistent labeling**:

| Label Status | Datasets | Images | Challenge |
|--------------|----------|--------|-----------|
| **3-dimension Document MOS** | 1 (DIQA-5000 only) | 5,500 | Our sole anchor |
| **Natural Image DMOS** | 2 (LIVE, CSIQ) | ~1,600 | Wrong domain, 1D only |
| **OCR Accuracy (no MOS)** | 1 (SmartDoc-QA) | 4,270 | Proxy metric only |
| **Domain-specific labels** | 12 | ~1M | Layout/structure, not quality |
| **No quality labels** | 6 | ~1.5M | Need full annotation |

**Critical Insight**: Only **DIQA-5000 (5,500 images)** has the 3-dimension document quality labels (overall, sharpness, color) we need. LIVE/CSIQ are natural images with 1 dimension. SmartDoc-QA has no MOS at all.

The core insight from DeQA-Doc is that we should train a model on **DIQA-5000 using soft-label distribution regression**, then use that model to pseudo-label all other datasets. This creates a **consistent 3-dimension quality scale** across all data.

---

## The Labeling Problem

### Current State

From [dataset-taxonomy-coverage.md](../reference/dataset-taxonomy-coverage.md):

```
Perceptual Scores (Axis 7):
- Human MOS: 4 datasets only
- Human DMOS: 0 additional
- LLM Score: 0 (not yet computed)
- Missing: 18 datasets need quality labels
```

### The Critical Label Inconsistency Problem

**The four "human-labeled" datasets have fundamentally different label structures:**

| Dataset | Label Type | Dimensions | Scale | Document-Specific? |
|---------|-----------|------------|-------|-------------------|
| **DIQA-5000** | MOS | 3 (overall, sharpness, color) | 1-5 | ✅ Yes |
| **LIVE** | DMOS | 1 (overall only) | 0-100 | ❌ No (natural images) |
| **CSIQ** | DMOS | 1 (overall only) | 0-1 | ❌ No (natural images) |
| **SmartDoc-QA** | OCR accuracy | 0 (no MOS!) | N/A | ✅ Yes (but no perceptual) |

**Critical Issues:**

1. **Only DIQA-5000 has the 3 dimensions we need** (overall, sharpness, color)
2. **LIVE and CSIQ are natural image datasets**, not documents—different quality semantics
3. **SmartDoc-QA has no MOS labels at all**—only OCR accuracy as proxy
4. **We cannot directly combine these** without losing information or introducing bias

### Why This Matters

1. **Training requires labels**: Our IQA models need per-image quality scores
2. **Labels must be consistent**: Can't mix 1-5 scale with 0-100 scale
3. **Dimension mismatch**: LIVE/CSIQ only have "overall", missing sharpness/color
4. **Domain mismatch**: Natural image IQA ≠ Document image IQA
5. **Human labels are expensive**: Only ~5,500 images have the right labels (DIQA-5000)

### Revised Understanding

**Effective training data for our 3-dimension model:**

| Dataset | Usable for Training | Notes |
|---------|---------------------|-------|
| **DIQA-5000** | ✅ Full (5,500 images) | Has all 3 dimensions |
| **LIVE** | ⚠️ Partial (779 images) | Overall only, natural images |
| **CSIQ** | ⚠️ Partial (866 images) | Overall only, natural images |
| **SmartDoc-QA** | ❌ Not directly | No perceptual MOS |

**This changes our strategy significantly.**

---

## The Solution: Hybrid DeQA-Doc → DocIQ-Replica Distillation

### Key Decision: Use DeQA-Doc as MLLM Teacher

Based on analysis of the [DeQA-Doc repository](/home/byron/dev/DeQA-Doc/), we recommend a **hybrid approach** that leverages the VQualA 2025 champion model as a teacher for knowledge distillation:

| Approach | Accuracy | Inference Speed | Scale Feasibility |
|----------|----------|-----------------|-------------------|
| DeQA-Doc only | 0.929 (best) | ~1s/image | ❌ 29 days for 2.5M images |
| DocIQ-Replica only | 0.88-0.90 | ~30ms/image | ✅ 21 hours for 2.5M images |
| **Hybrid (recommended)** | ~0.92 (distilled) | ~30ms/image | ✅ 21 hours for 2.5M images |

### Stage 1: DeQA-Doc High-Quality Anchor Labels

**Run DeQA-Doc inference on small, strategic datasets to create enriched ground truth:**

| Dataset | Images | Human Scores | Purpose | GCS/Location | Priority |
|---------|--------|--------------|---------|--------------|----------|
| **DIQA-5000** | 5,500 | 3-dim MOS (1-5) | Primary anchor with human MOS | `gs://image_detection_b/datasets/diqa-5000/` | CRITICAL |
| **SmartDoc-QA** | 4,270 | OCR accuracy | OCR correlation validation | `gs://image_detection_b/datasets/benchmarks/smartdoc-qa/` | HIGH |
| **OCR-Quality** | 1,000 | 1-dim (1-4) | OCR quality + multilingual | Local: `01_base_data/ocr_quality/` | **HIGH (NEW)** |
| **DIBCO** | 131 | Binarization GT | Extreme degradation edge cases | Local: `02_benchmark_only/dibco/` | HIGH |
| **FUNSD** | 199 | NER annotations | Real noisy scanned forms | Local: `01_base_data/forms/funsd/` | MEDIUM |
| **SROIE** | 973 | Entity extraction | Mobile capture / thermal print | Local: `01_base_data/forms/sroie/` | MEDIUM |
| **Tobacco-800** | 1,290 | N/A | Real archival degradation | Local: `01_base_data/degraded/tobacco800/` | MEDIUM |
| **Total Stage 1** | **~13,363** | | Diverse anchor set | | |

**Estimated Stage 1 Cost:**

- DeQA-Doc inference: ~14K images × 3 dimensions × ~1s = ~12 hours GPU time
- One-time cost, provides highest-quality soft-label distributions

**Why These Datasets:**

1. **DIQA-5000**: Our only 3-dimension human MOS anchor - DeQA-Doc labels will ENRICH (not replace) human MOS
2. **SmartDoc-QA**: Enables OCR accuracy correlation validation (SRCC target > 0.80)
3. **OCR-Quality** (NEW): Human-annotated OCR quality scores (1-4) + Chinese/multilingual coverage we lack
4. **DIBCO**: Tests extreme degradation handling (bleed-through, staining, fading)
5. **FUNSD**: Real scanned form noise patterns
6. **SROIE**: Mobile capture artifacts, thermal print degradation
7. **Tobacco-800**: Authentic archival degradation (yellowing, foxing)

**Excluded from Stage 1:**

- **OHR-Bench**: 8,561 page entries with 7-domain coverage, but stored as text annotations only (no direct images in arrow file). PDF extraction required. Consider for future expansion.

### Weight Considerations for DeQA-Doc Labels

**DeQA-Doc predictions should be weighted based on source:**

| Source | DeQA-Doc Role | Training Weight | Rationale |
|--------|---------------|-----------------|-----------|
| **DIQA-5000** | Enrich human MOS with soft distributions | See below | Human MOS is ground truth |
| **SmartDoc-QA** | Primary labels (no MOS exists) | 0.85 | High-confidence MLLM predictions |
| **OCR-Quality** | Validate against human scores (1-4) | 0.90 | Has independent human quality scores |
| **DIBCO** | Primary labels | 0.80 | Edge case domain |
| **FUNSD/SROIE/Tobacco** | Primary labels | 0.85 | Real-world degradation |

**Special Case: OCR-Quality Cross-Validation**

OCR-Quality has human quality scores (1-4 scale, inverted). Use for DeQA-Doc validation:

```python
def validate_deqa_on_ocr_quality(deqa_predictions: dict, ocr_quality_scores: dict) -> dict:
    """
    Validate DeQA-Doc predictions against OCR-Quality human scores.

    OCR-Quality uses inverted scale: 1=best, 4=worst
    DeQA-Doc uses: higher=better (0-1 normalized)

    Target: SRCC > 0.80 (strong negative correlation due to inverted scale)
    """
    # Invert OCR-Quality scores: 1->1.0, 4->0.0
    ocr_normalized = [(5 - score) / 4 for score in ocr_quality_scores]

    deqa_scores = [p['expected_value'] for p in deqa_predictions]

    srcc = scipy.stats.spearmanr(deqa_scores, ocr_normalized)[0]
    plcc = scipy.stats.pearsonr(deqa_scores, ocr_normalized)[0]

    return {
        'srcc': srcc,  # Target: > 0.80
        'plcc': plcc,
        'agreement_rate': sum(
            1 for d, o in zip(deqa_scores, ocr_normalized)
            if abs(d - o) < 0.2
        ) / len(deqa_scores)
    }
```

**Special Case: DIQA-5000 Weighting Strategy**

For DIQA-5000, we have BOTH human MOS AND DeQA-Doc predictions. Combine them:

```python
# For DIQA-5000 images with human MOS:
def combine_human_deqa_labels(human_mos: float, human_std: float,
                               deqa_dist: list[float]) -> dict:
    """
    Combine human MOS with DeQA-Doc soft-label distributions.

    Strategy: Use human MOS as expected value, but incorporate
    DeQA-Doc's distribution shape for better uncertainty modeling.
    """
    # Human MOS provides the CENTER of the distribution
    human_center = (human_mos - 1) / 4  # Normalize 1-5 to 0-1

    # DeQA-Doc provides the SHAPE of the distribution
    deqa_center = sum(i * p for i, p in enumerate(deqa_dist)) / (len(deqa_dist) - 1)

    # If predictions agree (within 0.1), high confidence
    agreement = abs(human_center - deqa_center) < 0.1

    if agreement:
        # Use human center with DeQA-Doc shape - best of both
        return {
            'soft_label': shift_distribution(deqa_dist, to_center=human_center),
            'expected_value': human_center,
            'weight': 1.0,  # Full weight - human + model agreement
            'source': 'human_deqa_combined'
        }
    else:
        # Disagreement - trust human MOS but widen uncertainty
        return {
            'soft_label': construct_gaussian_dist(human_center, sigma=0.15),
            'expected_value': human_center,
            'weight': 0.95,  # Slightly reduced - uncertainty exists
            'source': 'human_priority_disagreement'
        }
```

### Overview (Updated)

```text
Stage 1: DeQA-Doc High-Quality Anchor Labels (NEW)
┌─────────────────────────────────────────────────────────────────────────┐
│  Run DeQA-Doc (MLLM, 0.929 accuracy) on ~12K strategic images          │
│  ─────────────────────────────────────────────────────────────────────  │
│  • DIQA-5000: Enrich human MOS with soft distributions                  │
│  • SmartDoc-QA: Enable OCR correlation validation                       │
│  • DIBCO/FUNSD/SROIE/Tobacco: Diverse real-world degradation           │
│  • Output: High-quality soft-label distributions for all 3 dimensions   │
│  • Cost: ~10 hours GPU (one-time)                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Phase 1: Train DocIQ-Replica on DeQA-Doc Labels
┌─────────────────────────────────────────────────────────────────────────┐
│  DIQA-5000 (5,500 images) → DocIQ-Replica Model (soft-label trained)   │
│  ─────────────────────────────────────────────────────────────────────  │
│  3 dimensions: overall, sharpness, color                                │
│  This is our ONLY source for 3-dimension document IQA labels           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Phase 2: Pseudo-Label Unlabeled Datasets
┌─────────────────────────────────────────────────────────────────────────┐
│  Trained Model → Inference on all unlabeled datasets                    │
│                                                                          │
│  Output per image:                                                       │
│  - Predicted distribution (10 bins)                                      │
│  - Expected quality score (0-1)                                         │
│  - Uncertainty (distribution variance)                                   │
│  - Confidence flag (low variance = high confidence)                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Phase 3: Quality-Gated Training Expansion
┌─────────────────────────────────────────────────────────────────────────┐
│  Expand training data using confidence-weighted pseudo-labels           │
│                                                                          │
│  High confidence (σ < 0.15): Full training weight (1.0)                │
│  Medium confidence (σ < 0.25): Reduced weight (0.5)                    │
│  Low confidence (σ >= 0.25): Excluded or minimal weight (0.1)          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Phase 4: Iterative Refinement
┌─────────────────────────────────────────────────────────────────────────┐
│  Re-train on expanded dataset → Re-pseudo-label → Repeat               │
│                                                                          │
│  Convergence criteria:                                                   │
│  - Label stability (< 5% change between iterations)                     │
│  - Validation SRCC on held-out human-labeled set                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Training on DIQA-5000 (Primary Anchor)

### Why DIQA-5000 Only?

The other "human-labeled" datasets cannot be used for 3-dimension training:

| Dataset | Why Excluded |
|---------|--------------|
| **LIVE** | Natural images (not documents), only "overall" dimension |
| **CSIQ** | Natural images (not documents), only "overall" dimension |
| **SmartDoc-QA** | No MOS labels—only OCR accuracy proxy |

**DIQA-5000 is the only dataset with:**

- Document images (not natural images)
- Human MOS ratings (not algorithmic scores)
- All 3 quality dimensions (overall, sharpness, color)
- Per-image variance information (reconstructible via pseudo-variance)

### Dataset Preparation

#### Step 1.1: Normalize DIQA-5000 Scores

DIQA-5000 MOS scores normalized to **0-1 scale (0=best, 1=worst)**:

| Dimension | Original Scale | Normalization | Notes |
|-----------|---------------|---------------|-------|
| **overall** | MOS 1-5 (5=best) | `(5 - mos) / 4` | Primary quality indicator |
| **sharpness** | MOS 1-5 (5=best) | `(5 - mos) / 4` | Text/edge clarity |
| **color** | MOS 1-5 (5=best) | `(5 - mos) / 4` | Color fidelity |

#### Step 1.2: Construct Soft Labels (Per Dimension)

Following DeQA-Doc methodology, convert point scores to distributions for **each of the 3 dimensions**:

```python
def construct_soft_label(
    score: float,  # Normalized 0-1
    n_bins: int = 10,
    sigma: float = 0.08  # Pseudo-variance (0.2 × range / 10 bins)
) -> np.ndarray:
    """
    Convert continuous score to soft label distribution.

    For DIQA-5000 where we only have MOS (no variance):
    - Use pseudo-variance σ = 0.08 (0.2 × 0.4 range per bin)

    Bins: [0.0-0.1, 0.1-0.2, ..., 0.9-1.0]
    """
    bin_centers = np.linspace(0.05, 0.95, n_bins)

    # Gaussian distribution centered on score
    soft_label = np.exp(-0.5 * ((bin_centers - score) / sigma) ** 2)

    # Normalize to sum to 1
    soft_label = soft_label / soft_label.sum()

    return soft_label
```

#### Step 1.3: DIQA-5000 Training Dataset

```python
# Load DIQA-5000 with soft labels for all 3 dimensions
training_data = []

for image, scores in load_diqa5000():
    # scores = {'overall': 4.2, 'sharpness': 3.8, 'color': 4.5}
    training_data.append({
        'image_path': image,
        # Normalized scores (0=best, 1=worst)
        'overall_normalized': (5 - scores['overall']) / 4,
        'sharpness_normalized': (5 - scores['sharpness']) / 4,
        'color_normalized': (5 - scores['color']) / 4,
        # Soft label distributions (10 bins each)
        'overall_soft_label': construct_soft_label((5 - scores['overall']) / 4),
        'sharpness_soft_label': construct_soft_label((5 - scores['sharpness']) / 4),
        'color_soft_label': construct_soft_label((5 - scores['color']) / 4),
        'source_dataset': 'diqa-5000',
        'is_human_label': True,
        'weight': 1.0
    })

# Result: 5,500 images × 3 dimensions = 16,500 dimension-level labels
print(f"Training samples: {len(training_data)}")
print(f"Total dimension labels: {len(training_data) * 3}")
```

### Model Architecture: DocIQ-Replica with Soft Labels

Based on the DeQA-Doc analysis, modify DocIQ-Replica:

```python
class DocIQReplicaSoftLabel(nn.Module):
    """
    DocIQ-Replica with soft-label output heads.

    Architecture:
    - ResNet-50 backbone (ImageNet pretrained)
    - Layout Fusion Downsampler (1600×1600 → 400×400)
    - Three distribution heads (overall, sharpness, color)
    """

    def __init__(self, n_bins: int = 10):
        super().__init__()
        self.backbone = resnet50(pretrained=True)
        self.layout_fusion = LayoutFusionDownsampler(
            in_size=1600,
            out_size=400,
            n_classes=11  # DocLayNet classes
        )

        # Distribution heads (not regression heads!)
        hidden_dim = 2048  # ResNet-50 output
        self.head_overall = nn.Sequential(
            nn.Linear(hidden_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, n_bins),
            nn.LogSoftmax(dim=-1)  # For KL-div loss
        )
        self.head_sharpness = nn.Sequential(
            nn.Linear(hidden_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, n_bins),
            nn.LogSoftmax(dim=-1)
        )
        self.head_color = nn.Sequential(
            nn.Linear(hidden_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, n_bins),
            nn.LogSoftmax(dim=-1)
        )

    def forward(self, image, layout_mask=None):
        # Fuse layout information
        if layout_mask is not None:
            x = self.layout_fusion(image, layout_mask)
        else:
            x = F.interpolate(image, size=(400, 400))

        # Backbone features
        features = self.backbone(x)

        # Distribution predictions
        dist_overall = self.head_overall(features)
        dist_sharpness = self.head_sharpness(features)
        dist_color = self.head_color(features)

        return {
            'overall': dist_overall,
            'sharpness': dist_sharpness,
            'color': dist_color
        }

    def predict_score(self, distributions: dict) -> dict:
        """Convert distributions to point estimates."""
        bin_centers = torch.linspace(0.05, 0.95, 10).to(distributions['overall'].device)

        return {
            dim: (torch.exp(dist) * bin_centers).sum(dim=-1)
            for dim, dist in distributions.items()
        }
```

### Training Configuration

```python
# Loss: KL-Divergence (not MSE!)
loss_fn = nn.KLDivLoss(reduction='batchmean')

# Optimizer: Adam with DocIQ's schedule
optimizer = torch.optim.Adam(model.parameters(), lr=2e-4)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.6)

# Training loop
for epoch in range(60):
    for batch in dataloader:
        images = batch['image']
        soft_labels = batch['soft_label']  # Shape: [B, 10]

        # Forward pass
        distributions = model(images)

        # KL-div loss (target is soft label, input is log-probs)
        loss = loss_fn(distributions['overall'], soft_labels)

        # Backprop
        loss.backward()
        optimizer.step()

    scheduler.step()
```

---

## Phase 2: Pseudo-Labeling Unlabeled Datasets

### Stage 2 Model Selection: Quantized DeQA-Doc vs Custom DocIQ-Replica

For scaling to 2.5M images, we have two viable approaches:

#### Option A: Quantized DeQA-Doc (8-bit or 4-bit)

DeQA-Doc can be quantized to reduce memory and improve inference speed:

| Configuration | Model Size | VRAM Required | Speed | Accuracy (est.) |
|---------------|-----------|---------------|-------|-----------------|
| **FP16 (baseline)** | ~14 GB | 24+ GB | ~1s/img | 0.929 |
| **INT8 (8-bit)** | ~7 GB | 12-16 GB | ~0.7s/img | 0.92-0.93 |
| **INT4 (4-bit)** | ~3.5 GB | 8-10 GB | ~0.5s/img | 0.88-0.91 |
| **GPTQ/AWQ 4-bit** | ~3.5 GB | 8 GB | ~0.4s/img | 0.89-0.92 |

**Pros:**

- Uses proven VQualA 2025 champion model directly
- No training required, just quantization
- Preserves full MLLM reasoning capabilities
- Available via ModelScope/HuggingFace transformers
- 4-bit quantization makes it feasible on consumer GPUs (RTX 3090/4090)

**Cons:**

- Still 10-20x slower than custom CNN (~0.5s vs ~30ms)
- Requires transformers + bitsandbytes setup
- 4-bit quantization may degrade accuracy on edge cases
- Cannot batch as efficiently as pure CNN

**Estimated Time for 2.5M images:**

- 8-bit: 2.5M × 0.7s = ~20 days (1 GPU)
- 4-bit: 2.5M × 0.5s = ~14 days (1 GPU)

#### Option B: Custom DocIQ-Replica (CNN Student)

Train a ResNet-50/18 student model on Stage 1 DeQA-Doc labels:

| Configuration | Model Size | VRAM Required | Speed | Accuracy (target) |
|---------------|-----------|---------------|-------|-------------------|
| **ResNet-50** | ~100 MB | 4 GB | ~30ms/img | 0.88-0.92 |
| **ResNet-18** | ~45 MB | 2 GB | ~15ms/img | 0.85-0.90 |

**Pros:**

- 15-30x faster inference than quantized DeQA-Doc
- Easy to batch (1000+ images/batch on T4)
- Fits on any GPU, even consumer hardware
- Can export to ONNX/TensorRT for edge deployment
- Training cost is one-time (~10 hours GPU)

**Cons:**

- Requires training Phase 1 first
- Accuracy ceiling limited by teacher labels
- May miss complex quality patterns MLLM captures
- Need to handle distribution shift between Stage 1 and full corpus

**Estimated Time for 2.5M images:**

- ResNet-50: 2.5M × 0.03s = ~21 hours (1 GPU)
- ResNet-18: 2.5M × 0.015s = ~10 hours (1 GPU)

#### Recommendation: Hybrid Two-Pass Approach

**Best of both worlds:**

1. **Pass 1: DocIQ-Replica (fast)** - Label all 2.5M images (~21 hours)
2. **Pass 2: Quantized DeQA-Doc (selective)** - Re-label only uncertain samples

```python
# Selective re-labeling threshold
UNCERTAINTY_THRESHOLD = 0.0625  # ~15-20% of images flagged

def should_relabel_with_mllm(replica_result: dict) -> bool:
    """Determine if sample needs MLLM verification."""
    return (
        replica_result['uncertainty'] > UNCERTAINTY_THRESHOLD or
        replica_result['predicted_score'] < 0.3 or  # Low quality edge case
        replica_result['predicted_score'] > 0.9     # High quality verification
    )
```

**Expected Savings:**

- DocIQ-Replica labels: 2.5M images × 30ms = 21 hours
- Flagged for MLLM: ~500K images (20%)
- MLLM re-labeling: 500K × 0.5s = ~3 days
- **Total: ~4 days** vs 14-20 days for full MLLM

**Quality Assurance:**

- Cross-check MLLM vs Replica on re-labeled samples
- If disagreement > 0.2 normalized score, flag for review
- Use MLLM labels when disagreement detected

### Inference Pipeline

Once Phase 1 model is trained, run inference on all unlabeled datasets:

```python
def pseudo_label_dataset(
    model: DocIQReplicaSoftLabel,
    dataset_path: Path,
    output_path: Path,
    batch_size: int = 32
):
    """
    Generate pseudo-labels for an unlabeled dataset.

    Output per image:
    - predicted_distribution: [10] float array
    - predicted_score: float (expected value)
    - uncertainty: float (distribution variance)
    - confidence_tier: str ('high', 'medium', 'low')
    """
    model.eval()
    results = []

    for batch in DataLoader(dataset_path, batch_size=batch_size):
        with torch.no_grad():
            distributions = model(batch['image'])

            # Convert log-probs to probs
            probs = torch.exp(distributions['overall'])

            # Expected value (score)
            bin_centers = torch.linspace(0.05, 0.95, 10)
            scores = (probs * bin_centers).sum(dim=-1)

            # Variance (uncertainty)
            variances = ((probs * (bin_centers - scores.unsqueeze(-1))**2).sum(dim=-1))

            for i, path in enumerate(batch['path']):
                uncertainty = variances[i].item()
                results.append({
                    'image_path': str(path),
                    'predicted_distribution': probs[i].tolist(),
                    'predicted_score': scores[i].item(),
                    'uncertainty': uncertainty,
                    'confidence_tier': (
                        'high' if uncertainty < 0.015 else
                        'medium' if uncertainty < 0.0625 else
                        'low'
                    )
                })

    # Save to parquet
    pd.DataFrame(results).to_parquet(output_path)
    return len(results)
```

### Dataset Priority Order

Based on [dataset-taxonomy-coverage.md](../reference/dataset-taxonomy-coverage.md):

| Priority | Dataset | Images | Reason |
|----------|---------|--------|--------|
| 1 | **tobacco800** | 1,290 | Real degradation, ground truth |
| 2 | **historical_degraded** | 1,356 | Real degradation, ground truth |
| 3 | **funsd/funsd_plus** | 1,699 | Real scan noise, existing labels |
| 4 | **sroie** | 973 | Mobile capture, similar to SmartDoc |
| 5 | **rvl_cdip** | 400K | Large scale, real scans |
| 6 | **doclaynet** | 80K | Layout labels, born-digital |
| 7 | **tablebank** | 278K | Tables, compression-sensitive |
| 8 | **pubtabnet** | 568K | Tables, scientific |
| 9 | **nist_db2/sd6** | 11K | Forms, binary B&W |
| 10 | **Others** | ~500K | Lower priority |

### Confidence Thresholds

```python
# Confidence tiers based on distribution variance
CONFIDENCE_THRESHOLDS = {
    'high': {
        'max_variance': 0.015,   # σ < 0.12 (tight distribution)
        'training_weight': 1.0,
        'description': 'Model is confident'
    },
    'medium': {
        'max_variance': 0.0625,  # σ < 0.25 (moderate spread)
        'training_weight': 0.5,
        'description': 'Model has some uncertainty'
    },
    'low': {
        'max_variance': float('inf'),
        'training_weight': 0.1,  # Or exclude entirely
        'description': 'Model is uncertain'
    }
}
```

---

## Phase 3: Quality-Gated Training Expansion

### Expanded Training Dataset

```python
def build_expanded_training_set(
    human_labeled: pd.DataFrame,
    pseudo_labeled: pd.DataFrame,
    min_confidence: str = 'medium'
) -> pd.DataFrame:
    """
    Combine human-labeled and pseudo-labeled data.

    Human labels: weight 1.0, always included
    Pseudo labels: weight based on confidence tier
    """
    # Human labels (gold standard)
    human_labeled['source'] = 'human'
    human_labeled['weight'] = 1.0

    # Filter pseudo-labels by confidence
    confidence_filter = {
        'high': ['high'],
        'medium': ['high', 'medium'],
        'low': ['high', 'medium', 'low']
    }

    pseudo_filtered = pseudo_labeled[
        pseudo_labeled['confidence_tier'].isin(confidence_filter[min_confidence])
    ].copy()

    # Apply confidence-based weights
    pseudo_filtered['source'] = 'pseudo'
    pseudo_filtered['weight'] = pseudo_filtered['confidence_tier'].map({
        'high': 1.0,
        'medium': 0.5,
        'low': 0.1
    })

    # Combine
    return pd.concat([human_labeled, pseudo_filtered], ignore_index=True)
```

### Weighted Loss Function

```python
class WeightedKLDivLoss(nn.Module):
    """KL-Divergence loss with per-sample weights."""

    def __init__(self, reduction='batchmean'):
        super().__init__()
        self.kl_div = nn.KLDivLoss(reduction='none')
        self.reduction = reduction

    def forward(self, input: torch.Tensor, target: torch.Tensor,
                weight: torch.Tensor) -> torch.Tensor:
        # input: log-probs [B, n_bins]
        # target: soft labels [B, n_bins]
        # weight: per-sample weights [B]

        loss = self.kl_div(input, target)  # [B, n_bins]
        loss = loss.sum(dim=-1)  # [B]
        weighted_loss = loss * weight

        if self.reduction == 'batchmean':
            return weighted_loss.sum() / weight.sum()
        return weighted_loss
```

---

## Phase 4: Iterative Refinement

### Self-Training Loop

```python
def iterative_refinement(
    initial_model: DocIQReplicaSoftLabel,
    human_data: pd.DataFrame,
    unlabeled_datasets: list[Path],
    max_iterations: int = 3,
    stability_threshold: float = 0.05
):
    """
    Iteratively improve pseudo-labels through self-training.

    Convergence criteria:
    1. Label stability: < 5% average score change
    2. Validation SRCC on held-out human set
    """
    model = initial_model
    prev_pseudo_labels = None

    for iteration in range(max_iterations):
        print(f"\n=== Iteration {iteration + 1} ===")

        # Step 1: Pseudo-label all unlabeled datasets
        current_pseudo_labels = {}
        for dataset_path in unlabeled_datasets:
            labels = pseudo_label_dataset(model, dataset_path)
            current_pseudo_labels[dataset_path] = labels

        # Step 2: Check for convergence (label stability)
        if prev_pseudo_labels is not None:
            avg_change = compute_label_change(prev_pseudo_labels, current_pseudo_labels)
            print(f"Average label change: {avg_change:.3f}")
            if avg_change < stability_threshold:
                print("Converged!")
                break

        # Step 3: Build expanded training set
        pseudo_df = pd.concat([
            pd.read_parquet(p) for p in current_pseudo_labels.values()
        ])
        expanded_data = build_expanded_training_set(
            human_data, pseudo_df, min_confidence='medium'
        )
        print(f"Expanded training set: {len(expanded_data)} samples")

        # Step 4: Retrain model
        model = train_model(expanded_data, epochs=30)  # Fewer epochs for fine-tuning

        # Step 5: Validate on held-out human set
        val_srcc = evaluate_srcc(model, human_validation_set)
        print(f"Validation SRCC: {val_srcc:.4f}")

        prev_pseudo_labels = current_pseudo_labels

    return model, current_pseudo_labels
```

---

## Integration with Existing Pipeline

This section describes how the soft-label approach integrates with the existing three-layer automated labeling pipeline documented in:

- [automated-data-labeling-pipeline.puml](automated-data-labeling-pipeline.puml)
- [metadata-versioning-schema.md](../reference/metadata-versioning-schema.md)

### Current Pipeline Architecture (No Changes Required)

The existing pipeline already supports the structure needed for soft-label integration:

```
Layer 1: IMMUTABLE ──────────────────────────────────────────────────
  │  • Original DIQA-5000 MOS scores preserved (diqa.mos, diqa.mos_std)
  │  • File metadata (dimensions, DPI, hash)
  │  • No changes needed
  │
Layer 2: ENRICHMENT ─────────────────────────────────────────────────
  │  • capture_method, domain classification (existing)
  │  • Phase 9 flags (existing)
  │  • ★ ADD: Soft-label pseudo-predictions (new enrichment version)
  │
Layer 3: TRAINING ───────────────────────────────────────────────────
     • anchor_score computation (existing priority chain)
     • 45-dim iqa_vector (existing)
     • ★ ADD: Soft-label distribution support
     • ★ UPDATE: anchor_source priority chain
```

### annotate_base_metadata.py Updates

**File:** [scripts/annotate_base_metadata.py](../../scripts/annotate_base_metadata.py)

Add soft-label fields to the `EnrichmentData` dataclass:

```python
@dataclass
class EnrichmentData:
    # ... existing fields (capture_method, domain, resolution, etc.) ...

    # NEW: Soft-label pseudo annotations (Phase 7 - Unified Labeling)
    # These are stored as a new enrichment VERSION, not modifications to existing data
    soft_label_overall: list[float] | None = None       # [10] bin distribution
    soft_label_sharpness: list[float] | None = None     # [10] bin distribution
    soft_label_color: list[float] | None = None         # [10] bin distribution
    predicted_score_overall: float | None = None        # Expected value (0-1 scale)
    predicted_score_sharpness: float | None = None      # Expected value (0-1 scale)
    predicted_score_color: float | None = None          # Expected value (0-1 scale)
    prediction_uncertainty_overall: float | None = None # Distribution variance
    prediction_uncertainty_sharpness: float | None = None
    prediction_uncertainty_color: float | None = None
    prediction_confidence_tier: str | None = None       # 'high'/'medium'/'low'
    prediction_model_version: str | None = None         # e.g., "dociq-replica-soft-v1.0"
    prediction_model_checkpoint: str | None = None      # GCS path to model weights
```

**New enrichment version pattern** (following [metadata-versioning-schema.md](../reference/metadata-versioning-schema.md)):

```yaml
enrichments:
  current_version: 4
  versions:
    - version: 1  # Initial import
    - version: 2  # Classical CV IQA
    - version: 3  # ML IQA (ResNet-18 student)
    - version: 4  # NEW: Soft-label pseudo-predictions
      created_at: "2025-12-18T..."
      created_by: "dociq-replica-soft-v1.0"
      method: "pseudo_label"
      description: "DIQA-anchored soft-label pseudo-predictions"
      data:
        soft_label_overall: [0.01, 0.02, 0.05, 0.12, 0.25, 0.30, 0.15, 0.06, 0.03, 0.01]
        predicted_score_overall: 0.45
        prediction_uncertainty_overall: 0.018
        prediction_confidence_tier: "high"
```

### build_training_labels.py Updates

**File:** [scripts/build_training_labels.py](../../scripts/build_training_labels.py)

#### 1. Update AnchorSource Enum

```python
class AnchorSource(str, Enum):
    """Priority order for anchor score selection."""
    HUMAN = "human"                    # Weight: 1.0 (DIQA-5000 MOS)
    PSEUDO_HIGH = "pseudo_high"        # Weight: 0.9 (NEW - high confidence)
    PSEUDO_MEDIUM = "pseudo_medium"    # Weight: 0.5 (NEW - medium confidence)
    LLM_HIGH = "llm_high"             # Weight: 0.8 (existing)
    LLM_MEDIUM = "llm_medium"         # Weight: 0.5 (existing)
    PSEUDO_LOW = "pseudo_low"          # Weight: 0.2 (NEW - low confidence)
    LLM_LOW = "llm_low"               # Weight: 0.2 (existing)
    SYNTHETIC = "synthetic"            # Weight: 0.3 (existing)
```

#### 2. Update compute_anchor_score()

```python
def compute_anchor_score(record: dict) -> tuple[float, AnchorSource, float]:
    """
    Compute anchor score with updated priority chain.

    Priority (updated for soft-label pseudo-predictions):
    1. Human MOS (DIQA-5000) - weight 1.0
    2. High-confidence pseudo-labels - weight 0.9  # NEW
    3. Medium-confidence pseudo-labels - weight 0.5  # NEW
    4. LLM high-confidence - weight 0.8
    5. LLM medium-confidence - weight 0.5
    6. Low-confidence pseudo-labels - weight 0.2  # NEW
    7. LLM low-confidence - weight 0.2
    8. Synthetic (computed from degradation vector) - weight 0.3
    """
    # Priority 1: Human MOS (existing - unchanged)
    if record.get('diqa_mos'):
        return normalize_diqa_mos(record['diqa_mos']), AnchorSource.HUMAN, 1.0

    # Priority 2-3: High/medium confidence pseudo-labels (NEW)
    if record.get('predicted_score_overall') is not None:
        confidence_tier = record.get('prediction_confidence_tier', 'low')
        score = record['predicted_score_overall']

        if confidence_tier == 'high':
            return score, AnchorSource.PSEUDO_HIGH, 0.9
        elif confidence_tier == 'medium':
            return score, AnchorSource.PSEUDO_MEDIUM, 0.5
        # Low confidence falls through to lower priority

    # Priority 4-5: LLM predictions (existing)
    llm = record.get('perceptual_scores', {}).get('llm', {})
    if llm.get('has_score'):
        conf = llm['prediction_confidence']
        score = llm['predicted_normalized']
        if conf >= 0.8:
            return score, AnchorSource.LLM_HIGH, 0.8
        elif conf >= 0.5:
            return score, AnchorSource.LLM_MEDIUM, 0.5

    # Priority 6: Low-confidence pseudo-labels (NEW)
    if record.get('predicted_score_overall') is not None:
        return record['predicted_score_overall'], AnchorSource.PSEUDO_LOW, 0.2

    # Priority 7: Low-confidence LLM (existing)
    if llm.get('has_score'):
        return llm['predicted_normalized'], AnchorSource.LLM_LOW, 0.2

    # Priority 8: Synthetic (existing)
    synthetic_score = compute_synthetic_score(record.get('quality', {}))
    return synthetic_score, AnchorSource.SYNTHETIC, 0.3
```

#### 3. Add Soft-Label Distribution Support

```python
def build_training_record(record: dict) -> dict:
    """
    Build training-ready record with soft-label support.

    Returns dict with:
    - Standard fields (anchor_score, iqa_vector, etc.)
    - NEW: soft_label_* distributions for KL-div training
    """
    anchor_score, anchor_source, weight = compute_anchor_score(record)

    training_record = {
        # Existing fields
        'sample_id': record['id'],
        'anchor_score': anchor_score,
        'anchor_source': anchor_source.value,
        'anchor_weight': weight,
        'iqa_vector': build_degradation_vector(record),
        'iqa_binary': [v > 0.1 for v in build_degradation_vector(record)],

        # NEW: Soft-label distributions (if available)
        'soft_label_overall': record.get('soft_label_overall'),
        'soft_label_sharpness': record.get('soft_label_sharpness'),
        'soft_label_color': record.get('soft_label_color'),
        'has_soft_labels': record.get('soft_label_overall') is not None,

        # NEW: Training mode flag
        'use_kl_loss': record.get('soft_label_overall') is not None,
    }

    return training_record
```

### New Diagram: Soft-Label Integration

A new diagram has been created showing how soft-labels integrate with the three-layer architecture:

- [soft-label-pipeline-integration.puml](soft-label-pipeline-integration.puml) - Complete soft-label integration flow

### Existing Diagrams Requiring Updates

The following diagrams need updates to reflect soft-label integration:

| Diagram | Update Required |
|---------|-----------------|
| [automated-data-labeling-pipeline.puml](automated-data-labeling-pipeline.puml) | Add soft-label pseudo-prediction step in Layer 2 |
| [diqa-pseudo-labeling-workflow.puml](diqa-pseudo-labeling-workflow.puml) | Update to show soft-label distribution output instead of scalar |
| [labeling-workstreams-overview.puml](../development/labeling/labeling-workstreams-overview.puml) | Update Project C to show KL-div loss instead of MSE |

### Backward Compatibility

The soft-label fields are **optional** and **additive**:

- Existing records without soft-labels continue to work
- The anchor_score priority chain falls back to existing sources
- Training can mix soft-label and scalar-label samples (weighted loss)

---

## Validation Strategy

### DIQA-5000 Split (Primary Validation)

Since DIQA-5000 is our only 3-dimension anchor, we use careful stratified splitting:

| Split | Images | Purpose |
|-------|--------|---------|
| **Training** | 4,000 (72.7%) | Model training |
| **Validation** | 500 (9.1%) | Hyperparameter tuning |
| **Test** | 1,000 (18.2%) | Final evaluation (never touch during development) |

**Stratification criteria:**

- Balance across distortion types (shadow, occlusion, blur, crease, moiré)
- Balance across quality score ranges (low/medium/high)
- Balance across all 3 dimensions

### Secondary Validation (Overall Dimension Only)

LIVE and CSIQ can validate the **overall dimension only** (not sharpness/color):

| Dataset | Images | Purpose | Limitation |
|---------|--------|---------|------------|
| LIVE | 779 | Cross-domain generalization | Natural images, overall only |
| CSIQ | 866 | Compression artifact detection | Natural images, overall only |

### SmartDoc-QA Proxy Validation

SmartDoc-QA provides **OCR accuracy correlation**, not MOS validation:

| Metric | Target | Notes |
|--------|--------|-------|
| SRCC(predicted_quality, OCR_accuracy) | > 0.80 | Quality should predict OCR success |

This validates that our predicted quality scores are **functionally meaningful** (predict OCR performance), even without ground-truth MOS.

### Metrics

```python
def evaluate_model(model, validation_set):
    """
    Evaluation metrics for IQA model.
    """
    predictions = []
    targets = []

    for batch in validation_set:
        with torch.no_grad():
            dist = model(batch['image'])['overall']
            score = model.predict_score({'overall': dist})['overall']
        predictions.extend(score.tolist())
        targets.extend(batch['score_normalized'].tolist())

    return {
        'srcc': scipy.stats.spearmanr(predictions, targets)[0],
        'plcc': scipy.stats.pearsonr(predictions, targets)[0],
        'rmse': np.sqrt(np.mean((np.array(predictions) - np.array(targets))**2)),
        'mae': np.mean(np.abs(np.array(predictions) - np.array(targets)))
    }
```

### Target Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| **SRCC (overall)** | > 0.90 | Spearman rank correlation |
| **PLCC (overall)** | > 0.90 | Pearson linear correlation |
| **RMSE** | < 0.10 | On 0-1 scale |
| **Cross-dataset SRCC** | > 0.85 | Generalization test |

---

## Implementation Roadmap

### Week 1-2: Data Preparation

- [ ] Parse and normalize all human-labeled datasets
- [ ] Implement soft-label construction
- [ ] Create unified training dataloader
- [ ] Set up validation splits

### Week 3-4: Phase 1 Training

- [ ] Implement DocIQReplicaSoftLabel architecture
- [ ] Train on combined human-labeled data
- [ ] Validate on held-out sets
- [ ] Tune hyperparameters

### Week 5-6: Phase 2 Pseudo-Labeling

- [ ] Implement pseudo-labeling pipeline
- [ ] Run inference on priority datasets
- [ ] Analyze confidence distributions
- [ ] Quality-check pseudo-labels

### Week 7-8: Phase 3-4 Expansion & Refinement

- [ ] Build expanded training set
- [ ] Implement weighted loss
- [ ] Run iterative refinement
- [ ] Validate convergence

### Week 9-10: Integration & Documentation

- [ ] Update metadata pipeline scripts
- [ ] Export final pseudo-labels to registry
- [ ] Document final model and methodology
- [ ] Prepare for downstream training

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Poor generalization to documents | Medium | High | Include SmartDoc-QA in training (mobile capture proxy) |
| Pseudo-label drift | Medium | Medium | Iterative refinement with stability checks |
| Domain shift to tables/forms | High | Medium | Prioritize pseudo-labeling diverse datasets |
| Low confidence on born-digital | Low | Low | Born-digital typically higher quality, less variability |
| Computational cost | Low | Medium | Batch inference, efficient dataloader |

---

## References

1. [DeQA-Doc_Analysis_Deep_Dive.md](DeQA-Doc_Analysis_Deep_Dive.md) - Soft-label methodology
2. [DIQA-5000_Pseudo_Labels_v2.md](DIQA-5000_Pseudo_Labels_v2.md) - Original multi-model approach
3. [dataset-taxonomy-coverage.md](../reference/dataset-taxonomy-coverage.md) - Label coverage matrix
4. [DATASET_CATALOG.md](../DATASET_CATALOG.md) - Dataset inventory
5. DeQA-Doc Paper: [arXiv:2507.12796](https://arxiv.org/abs/2507.12796)
6. DocIQ Paper: [arXiv:2509.17012](https://arxiv.org/abs/2509.17012)

---

*Document Version 1.0 - December 2025*
