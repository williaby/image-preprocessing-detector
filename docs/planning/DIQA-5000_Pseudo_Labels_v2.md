---
owner: docs-team
purpose: 'Documentation for Document Image Quality Assessment: Pseudo-Labeling System.'
schema_type: common
status: draft
tags:
- planning
- iqa
- weak_supervision
title: 'Document Image Quality Assessment: Pseudo-Labeling System'
---

## Technical Implementation Specification

**Version:** 2.0
**Date:** December 2025
**Purpose:** Single-use offline tool for generating DIQA-style pseudo-labels
**Compute:** Modal A100 (80GB VRAM)

---

## 1. Executive Summary

This document specifies an **offline pseudo-labeling tool** that generates DIQA-style quality annotations for unlabeled document images. The system uses a 5-model ensemble with full-precision inference on Modal A100 GPUs, optimizing purely for **label accuracy** without production latency or memory constraints.

### Design Philosophy

- **Accuracy over speed**: 400-500ms per image is acceptable
- **Full precision**: No quantization compromises
- **Single-use tool**: Not a production inference system
- **DIQA replication**: Focus on the 3 DIQA quality dimensions only

### Target Metrics

| Metric | Target | Priority |
|--------|--------|----------|
| SRCC (vs human ratings) | > 0.94 | **Critical** |
| Expected Calibration Error (ECE) | < 0.08 | **Critical** |
| SRCC 95% CI Width | < 0.03 | High |
| Inference Latency | < 500ms | Low (acceptable) |

### Quality Dimensions

The system predicts scores (1-5 scale) for three DIQA quality dimensions:

| Dimension | Primary Signals | Best Model Type |
|-----------|-----------------|-----------------|
| **Sharpness** | High-frequency content, edge gradients, blur kernels | CNNs with early-layer features (DocIQ, MUSIQ) |
| **Color Fidelity** | Color histograms, white balance, saturation | Models with color-aware pretraining (QualiCLIP) |
| **Overall** | Holistic assessment, readability, semantic quality | VLMs with semantic understanding (Qwen, InternVL) |

---

## 2. Compute Environment

### Modal Configuration

```python
# Modal stub configuration
app = modal.App("diqa-pseudo-labeling")

# Full-precision inference on A100
gpu_image = modal.Image.debian_slim().pip_install(
    "torch>=2.0",
    "transformers>=4.40",
    "accelerate",
    "timm",
    "open-clip-torch",
)

@app.cls(
    gpu="A100-80GB",  # Full 80GB VRAM - no memory constraints
    timeout=3600,      # 1 hour per batch
    container_idle_timeout=300,
)
class DIQAEnsemble:
    ...
```

### Resource Allocation

| Resource | Specification | Notes |
|----------|---------------|-------|
| GPU | A100 80GB | Modal serverless |
| Precision | FP16 (VLMs), FP32 (small models) | No quantization |
| Batch Size | 1-4 images | Maximize accuracy |
| Timeout | 500ms/image acceptable | No latency pressure |

---

## 3. Ensemble Architecture

### 3.1 Model Roster (Full Precision)

### Track A: IQA Models (CNN-based)

| Model | Sub-Track | Role | Precision | Parameters | Modal GPU | Status |
|-------|-----------|------|-----------|------------|-----------|--------|
| **DocIQ-Replica** | A3 | **Generalist Anchor** | FP32 | ~25M | A10G | ⚠️ **Requires Training** |
| **MUSIQ** | A1 | Sharpness Specialist | FP32 | ~27M | T4/A10G | ✅ Available (PyIQA) |
| **QualiCLIP** | A2 | Color Specialist | FP32 | ~150M | T4/A10G | ✅ Available (PyIQA) |

> **DocIQ-Replica Note**: The original DocIQ model is not publicly available. We train a ResNet-50 based
> model from scratch on DIQA-5000. Because it lacks IQA pretraining bias, it serves as the **Generalist Anchor**
> for Track A (analogous to Qwen3-VL-8B's role in Track B). See Section 4.4A for training protocols.

### Track B: VLM Models (Vision-Language)

| Model | Role | Precision | Parameters | Modal GPU | Status |
|-------|------|-----------|------------|-----------|--------|
| **Qwen3-VL-8B** | Generalist Anchor | FP16 | ~8B | A100-80GB | ✅ Available |
| **InternVL3-8B** | Overall Specialist | FP16 | ~8B | A100-80GB | ✅ Available |

*Note: Both VLMs fit comfortably on a single A100 80GB together (~32GB total).*

### Track Comparison

| Aspect | Track A (IQA) | Track B (VLM) |
|--------|---------------|---------------|
| **GPU Requirement** | T4/A10G (16-24GB) | A100-80GB |
| **Batch Size** | 32-64 | 1-4 |
| **Inference Time** | <50ms/image | 200-400ms/image |
| **Training** | End-to-end fine-tuning | LoRA fine-tuning |
| **Cost/hour** | ~$0.40-1.00 | ~$4.50 |

### 3.2 Track A: IQA Model Deployment

IQA models can run on smaller GPUs with larger batch sizes:

```python
@app.cls(gpu="A10G")
class IQAInference:
    """MUSIQ, QualiCLIP, DocIQ-Replica - all fit on A10G with room to spare."""

    def __init__(self):
        import pyiqa

        # MUSIQ (~27M params, sharpness specialist)
        self.musiq = pyiqa.create_metric("musiq", device="cuda")

        # QualiCLIP (~150M params, color specialist)
        self.qualiclip = pyiqa.create_metric("qualiclip", device="cuda")

        # DocIQ-Replica (trained ResNet-50, sharpness specialist)
        # TODO: Load from trained checkpoint after Phase 4A training
        # self.dociq = load_dociq_replica("path/to/checkpoint.pt")
```

### 3.3 Track B: VLM Deployment

VLMs require A100 for full-precision inference:

```python
@app.cls(gpu="A100-80GB")
class VLMInference:
    """Qwen3-VL-8B + InternVL3-8B - require A100."""

    def __init__(self):
        # Qwen3-VL-8B (~16GB)
        self.qwen = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-VL-8B-Instruct",
            device_map="auto",
            torch_dtype=torch.float16,
        )
        # InternVL3-8B (~16GB)
        self.internvl = AutoModel.from_pretrained(
            "OpenGVLab/InternVL3-8B",
            device_map="auto",
            torch_dtype=torch.float16,
        )
```

### 3.4 Specialty Matrix

Each model is trained on all three dimensions but optimized for checkpoint selection based on its role:

| Model | Track | Role | Overall | Sharpness | Color | Selection Criterion |
|-------|-------|------|---------|-----------|-------|---------------------|
| Qwen3-VL-8B | B (VLM) | Generalist Anchor | Primary ★ | Primary ★ | Primary ★ | Weighted(SRCC_mean, ECE) |
| DocIQ-Replica | A (IQA) | **Generalist Anchor** | Primary ★ | Primary ★ | Primary ★ | **Weighted(SRCC_mean, ECE)** |
| MUSIQ | A (IQA) | Sharpness Specialist | Secondary | **Primary ★** | Secondary | Weighted(SRCC_sharpness, ECE) |
| QualiCLIP | A (IQA) | Color Specialist | Secondary | Secondary | **Primary ★** | Weighted(SRCC_color, ECE) |
| InternVL3-8B | B (VLM) | Overall Specialist | **Primary ★** | Secondary | Secondary | Weighted(SRCC_overall, ECE) |

> **Checkpoint Selection Strategy**: Within a configurable SRCC band (default ±0.02), checkpoints compete
> on a weighted score (default 70% SRCC, 30% ECE). This allows trading small SRCC losses for significant
> ECE improvements while keeping SRCC as the primary driver. See Section 4.5 for details.
>
> **Two Generalist Anchors**: The ensemble has two generalist anchors—one per track. This provides
> balanced predictions from both IQA (DocIQ-Replica) and VLM (Qwen3-VL-8B) perspectives, with specialists
> refining dimension-specific assessments.

### 3.5 Why Multi-Task Training (Retained)

Training specialists on all dimensions (not just their specialty) provides:

1. **Multi-Task Regularization:** Prevents overfitting to quirks of one dimension
2. **Correlated Supervision:** Exploits correlations between quality dimensions
3. **Ensemble Flexibility:** Every model contributes to every dimension with different weights

---

## 4. Multi-Task Training Protocol

### 4.1 Loss Weighting by Model

| Model | Track | Role | Overall | Sharpness | Color | Strategy |
|-------|-------|------|---------|-----------|-------|----------|
| Qwen3-VL-8B | B (VLM) | Generalist Anchor | 0.34 | 0.33 | 0.33 | Equal weights |
| DocIQ-Replica | A (IQA) | **Generalist Anchor** | **0.34** | **0.33** | **0.33** | Equal weights |
| MUSIQ | A (IQA) | Sharpness Specialist | 0.2 | **0.6** | 0.2 | Sharpness-weighted |
| QualiCLIP | A (IQA) | Color Specialist | 0.2 | 0.2 | **0.6** | Color-weighted |
| InternVL3-8B | B (VLM) | Overall Specialist | **0.6** | 0.2 | 0.2 | Overall-weighted |

### 4.2 Multi-Task Head Architecture

```python
class MultiTaskHead(nn.Module):
    """Shared multi-task prediction head for all base models."""

    def __init__(self, in_features: int, hidden: int = 256):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(in_features, hidden),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        self.heads = nn.ModuleDict({
            'overall': nn.Linear(hidden, 1),
            'sharpness': nn.Linear(hidden, 1),
            'color': nn.Linear(hidden, 1)
        })

    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        shared = self.shared(features)
        return {dim: head(shared).squeeze(-1) for dim, head in self.heads.items()}
```

### 4.3 Training Loss

```python
def dimension_loss(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Combined MSE + rank loss + focal calibration."""
    mse = F.mse_loss(pred, target)
    rank = differentiable_rank_loss(pred, target)
    focal_ece = focal_calibration_loss(pred, target)

    return 0.6 * mse + 0.2 * rank + 0.2 * focal_ece


def focal_calibration_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    gamma: float = 2.0
) -> torch.Tensor:
    """
    Focal loss variant for calibration.
    Harder examples (larger errors) get more weight.
    """
    error = (pred - target).abs()
    confidence = 1.0 - error / 4.0  # Normalize to [0, 1] for 1-5 scale
    focal_weight = (1 - confidence) ** gamma
    return (focal_weight * error ** 2).mean()
```

### 4.4 Training Protocols (Track-Specific)

#### 4.4A Track A: IQA Model Training (Three Sub-Tracks)

Track A contains three models with fundamentally different starting points, requiring distinct training protocols:

| Sub-Track | Model | Starting Point | Role | Training Approach |
|-----------|-------|----------------|------|-------------------|
| **A1** | MUSIQ | Pretrained IQA (KonIQ-10k) | Sharpness Specialist | Fine-tune with specialist weights |
| **A2** | QualiCLIP | Pretrained CLIP (opinion-unaware) | Color Specialist | Fine-tune with specialist weights |
| **A3** | DocIQ-Replica | ImageNet only (no IQA) | **Generalist Anchor** | Train from scratch, equal weights |

---

##### Sub-Track A1: MUSIQ Fine-Tuning (Sharpness Specialist)

**Starting Point:** MUSIQ is pretrained on KonIQ-10k for natural image quality. It outputs a single MOS score (0-1 scale) and has strong blur/sharpness detection capabilities.

**Architecture Modification:**

```python
class MUSIQMultiTask(nn.Module):
    """MUSIQ backbone with multi-task head for DIQA dimensions."""

    def __init__(self, pretrained_musiq):
        super().__init__()
        # Freeze MUSIQ backbone initially
        self.backbone = pretrained_musiq.backbone
        for param in self.backbone.parameters():
            param.requires_grad = False

        # Replace single-score head with multi-task head
        # MUSIQ outputs 384-dim features from ViT-B/16
        self.head = MultiTaskHead(in_features=384, hidden=256)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.backbone(x)
        return self.head(features)
```

**Training Protocol (A1):**

1. **Phase 1 - Head warmup** (10 epochs):
   - Freeze backbone completely
   - Train multi-task head only
   - Learning rate: 1e-3
   - Loss weights: [0.2, **0.6**, 0.2] (sharpness specialist)

2. **Phase 2 - Fine-tune backbone** (20 epochs):
   - Unfreeze backbone
   - Learning rate: 1e-5 (backbone), 1e-4 (head)
   - Same loss weights

3. **Checkpoint Selection:** Best `ECE_sharpness` with `ECE_mean` tiebreaker

**Why Sharpness Specialist:** MUSIQ's KonIQ-10k pretraining focuses on blur, noise, and compression artifacts—directly relevant to sharpness assessment.

---

##### Sub-Track A2: QualiCLIP Fine-Tuning (Color Specialist)

**Starting Point:** QualiCLIP uses CLIP ViT-B/32 with learned quality-aware text prompts. It's "opinion-unaware" (no MOS labels in training) but has strong color/semantic understanding from CLIP pretraining.

**Architecture Modification:**

```python
class QualiCLIPMultiTask(nn.Module):
    """QualiCLIP with multi-task head for DIQA dimensions."""

    def __init__(self, pretrained_qualiclip):
        super().__init__()
        # Freeze CLIP vision encoder initially
        self.vision_encoder = pretrained_qualiclip.visual
        for param in self.vision_encoder.parameters():
            param.requires_grad = False

        # CLIP ViT-B/32 outputs 512-dim features
        self.head = MultiTaskHead(in_features=512, hidden=256)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.vision_encoder(x)
        return self.head(features)
```

**Training Protocol (A2):**

1. **Phase 1 - Head warmup** (10 epochs):
   - Freeze CLIP vision encoder completely
   - Train multi-task head only
   - Learning rate: 1e-3
   - Loss weights: [0.2, 0.2, **0.6**] (color specialist)

2. **Phase 2 - Fine-tune encoder** (20 epochs):
   - Unfreeze vision encoder
   - Learning rate: 1e-6 (encoder), 1e-4 (head) — lower LR to preserve CLIP features
   - Same loss weights

3. **Checkpoint Selection:** Best `ECE_color` with `ECE_mean` tiebreaker

**Why Color Specialist:** CLIP's image-text pretraining gives it strong color vocabulary and semantic understanding of visual attributes like "vibrant", "faded", "saturated".

---

##### Sub-Track A3: DocIQ-Replica Training (Generalist Anchor)

**Starting Point:** No pretrained IQA weights available. We train from ImageNet-pretrained ResNet-50, making this effectively a **from-scratch** IQA model for documents.

> **DocIQ Paper Alignment**: Implementing **Option 1 (True DocIQ Replica)** with full Layout Fusion
> Downsampler architecture matching the original paper.
>
> | Aspect | Specification |
> |--------|---------------|
> | **Input Resolution** | 1600×1600 |
> | **Layout Masks** | 11-class semantic masks via DocLayout-YOLO |
> | **Expected SRCC** | 0.75-0.80 |
> | **Implementation Time** | 2-3 weeks |
> | **GPU Memory** | A100-80GB (batch 4-8) or A10G with gradient accumulation |

**Architecture:**

```python
class LayoutFusionDownsampler(nn.Module):
    """Fuses RGB image with semantic layout masks.

    Matches DocIQ paper architecture: downsamples 1600×1600 input
    while incorporating 11-class layout mask information.
    """

    def __init__(self, n_layout_classes: int = 11):
        super().__init__()
        # Layout mask encoder (11 classes → 64 channels)
        self.layout_encoder = nn.Sequential(
            nn.Conv2d(n_layout_classes, 32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
        )

        # RGB encoder (3 → 64 channels, matching layout spatial dims)
        self.rgb_encoder = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=7, stride=4, padding=3),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
        )

        # Fusion layer (64 + 64 → 3 for ResNet input)
        self.fusion = nn.Sequential(
            nn.Conv2d(128, 64, kernel_size=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 3, kernel_size=1),
        )

    def forward(
        self,
        rgb: torch.Tensor,      # [B, 3, 1600, 1600]
        layout: torch.Tensor    # [B, 11, 1600, 1600] one-hot
    ) -> torch.Tensor:          # [B, 3, 400, 400] fused
        rgb_feat = self.rgb_encoder(rgb)        # [B, 64, 400, 400]
        layout_feat = self.layout_encoder(layout)  # [B, 64, 400, 400]
        fused = torch.cat([rgb_feat, layout_feat], dim=1)  # [B, 128, 400, 400]
        return self.fusion(fused)  # [B, 3, 400, 400]


class DocIQReplica(nn.Module):
    """Full DocIQ Replica with Layout Fusion Downsampler.

    Matches original DocIQ paper architecture:
    - 1600×1600 input resolution
    - Layout Fusion Downsampler with semantic masks
    - ResNet-50 backbone
    - Multi-task head for quality prediction

    Serves as the GENERALIST ANCHOR for Track A.
    """

    def __init__(self, n_layout_classes: int = 11):
        super().__init__()
        # Layout-aware downsampler (DocIQ paper component)
        self.downsampler = LayoutFusionDownsampler(n_layout_classes)

        # ResNet-50 backbone (receives 400×400 fused features)
        self.backbone = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        self.backbone.fc = nn.Identity()

        # Document-specific IQA head (larger hidden dim for generalist)
        self.head = MultiTaskHead(in_features=2048, hidden=512)

    def forward(
        self,
        rgb: torch.Tensor,      # [B, 3, 1600, 1600]
        layout: torch.Tensor    # [B, 11, 1600, 1600]
    ) -> dict[str, torch.Tensor]:
        # Fuse RGB with layout masks
        fused = self.downsampler(rgb, layout)  # [B, 3, 400, 400]
        # Extract features
        features = self.backbone(fused)
        # Predict quality scores
        return self.head(features)
```

**Layout Mask Generation Pipeline:**

```python
class LayoutMaskGenerator:
    """Generates 11-class layout masks using DocLayout-YOLO.

    Classes: Caption, Footnote, Formula, List-Item, Page-Footer,
             Page-Header, Picture, Section-Header, Table, Text, Title
    """

    def __init__(self, model_path: str = "DocLayout-YOLO-DocStructBench"):
        from ultralytics import YOLO
        self.model = YOLO(model_path)
        self.n_classes = 11

    def generate_mask(
        self,
        image: np.ndarray,  # [H, W, 3] RGB
        target_size: tuple[int, int] = (1600, 1600)
    ) -> np.ndarray:  # [11, H, W] one-hot
        # Run detection
        results = self.model(image, verbose=False)

        # Initialize empty mask
        h, w = target_size
        mask = np.zeros((self.n_classes, h, w), dtype=np.float32)

        # Fill mask from detections
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                mask[cls_id, y1:y2, x1:x2] = 1.0

        return mask

    def batch_generate(
        self,
        images: list[np.ndarray],
        cache_dir: str | None = None
    ) -> list[np.ndarray]:
        """Generate masks for batch, with optional caching."""
        masks = []
        for img in images:
            # Check cache if enabled
            if cache_dir:
                cache_path = self._get_cache_path(img, cache_dir)
                if os.path.exists(cache_path):
                    masks.append(np.load(cache_path))
                    continue

            mask = self.generate_mask(img)
            if cache_dir:
                np.save(cache_path, mask)
            masks.append(mask)

        return masks
```

> **✅ IMPLEMENTATION STATUS: COMPLETE**
>
> The Layout Fusion Downsampler has been implemented as a standalone module that **MUST be used
> for ALL IQA-based training** where the model cannot accept the full 1600×1600 image resolution.
>
> **Module Location:** `src/image_preprocessing_detector/labeling/finetuning/layout_fusion.py`
>
> **Key Components:**
>
> | Component | Description |
> |-----------|-------------|
> | `LayoutFusionDownsampler` | Fuses RGB images with 11-class semantic layout masks, downsampling 1600×1600 → 400×400 |
> | `LayoutMaskGenerator` | Generates masks via DocLayout-YOLO with caching support |
> | `DocIQReplica` | Full DocIQ paper architecture (Generalist Anchor) with two-phase training |
> | `create_dociq_replica()` | Factory function for easy model creation |
>
> **Usage Example:**
>
> ```python
> from image_preprocessing_detector.labeling.finetuning import (
>     LayoutFusionDownsampler,
>     LayoutMaskGenerator,
>     DocIQReplica,
> )
>
> # Generate layout masks for training
> mask_generator = LayoutMaskGenerator()
> layout_mask = mask_generator.generate_mask(image)
>
> # Use DocIQ Replica with layout fusion
> model = DocIQReplica(freeze_backbone=True)  # Phase 1: frozen
> outputs = model(rgb_tensor, layout_tensor)
> # outputs: {"overall": [B], "sharpness": [B], "color": [B]}
> ```
>
> **Unit Tests:** 39 tests in `tests/unit/labeling/finetuning/test_layout_fusion.py`

**Training Protocol (A3):**

> **Aligned with DocIQ Paper**: 60 epochs total (paper uses 60), step decay LR schedule.
> Simplified from 3-phase to 2-phase per consensus recommendations.

1. **Phase 1 - Head warmup** (15 epochs):
   - Freeze ResNet-50 backbone
   - Train multi-task head only
   - Learning rate: 1e-3 with linear warmup (5 epochs) + cosine decay
   - Loss weights: [**0.34**, **0.33**, **0.33**] (equal/generalist)

2. **Phase 2 - Full fine-tune** (45 epochs):
   - Unfreeze entire backbone
   - Learning rate: 1e-5 (backbone), 1e-4 (head) with cosine annealing
   - Same loss weights
   - Label-preserving augmentation: horizontal flip, rotation (±5°), mild color jitter

3. **Checkpoint Selection:** Weighted(SRCC_mean, ECE) using `balanced` preset

   > **Note**: Original DocIQ paper uses SRCC/PLCC for evaluation, not ECE.
   > We use weighted scoring (70% SRCC, 30% ECE) within a ±0.02 SRCC band,
   > allowing small SRCC tradeoffs for significant calibration improvements.
   > See Section 4.5 for full algorithm and presets.

**Why Generalist:** Without IQA pretraining to bias it toward any dimension, DocIQ-Replica can learn balanced representations across all three quality dimensions. This makes it the natural **anchor model for Track A**, providing stable predictions that specialists can refine.

---

##### Track A Training Configuration Summary

| Parameter | MUSIQ (A1) | QualiCLIP (A2) | DocIQ-Replica (A3) |
|-----------|------------|----------------|---------------------|
| **Role** | Sharpness Specialist | Color Specialist | **Generalist Anchor** |
| **Backbone** | ViT-B/16 | CLIP ViT-B/32 | ResNet-50 + Layout Fusion |
| **Feature Dim** | 384 | 512 | 2048 |
| **Input Size** | Variable | 224×224 | **1600×1600** (paper-aligned) |
| **Layout Masks** | N/A | N/A | **11-class DocLayout-YOLO** |
| **Total Epochs** | 30 | 30 | **60** (paper-aligned) |
| **Loss Weights** | [0.2, **0.6**, 0.2] | [0.2, 0.2, **0.6**] | [**0.34**, **0.33**, **0.33**] |
| **Checkpoint Select** | SRCC_sharpness | SRCC_color | **SRCC_mean** (ECE tiebreaker) |
| **Batch Size** | 32 | 32 | 4-8 (gradient accum) |
| **GPU** | T4/A10G | T4/A10G | **A100-80GB** |
| **Est. Time** | 4-6 hrs | 4-6 hrs | **12-18 hrs** |

---

##### Updated Specialty Matrix (Track A)

| Model | Role | Overall | Sharpness | Color | Selection |
|-------|------|---------|-----------|-------|-----------|
| DocIQ-Replica | **Generalist Anchor** | Primary ★ | Primary ★ | Primary ★ | **Weighted(SRCC_mean, ECE)** |
| MUSIQ | Sharpness Specialist | Secondary | **Primary ★** | Secondary | Weighted(SRCC_sharpness, ECE) |
| QualiCLIP | Color Specialist | Secondary | Secondary | **Primary ★** | Weighted(SRCC_color, ECE) |

#### 4.4B Track B: VLM Fine-Tuning (LoRA)

**Applies to:** Qwen3-VL-8B, InternVL3-8B

VLMs use LoRA fine-tuning rather than full fine-tuning:

```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(base_model, lora_config)
```

**Training Configuration (Track B):**

| Parameter | Qwen3-VL-8B | InternVL3-8B |
|-----------|-------------|--------------|
| Method | LoRA | LoRA |
| LoRA Rank | 16 | 16 |
| LoRA Alpha | 32 | 32 |
| Epochs | 3 | 3 |
| Batch Size | 4 (grad_accum=8) | 4 (grad_accum=8) |
| Learning Rate | 2e-4 | 2e-4 |
| GPU | A100-80GB | A100-80GB |
| Est. Time | 6-8 hrs | 6-8 hrs |

**Prompt Template for VLM Training:**

```text
Assess this document image's quality on three dimensions.
Rate each from 1.0 (worst) to 5.0 (best):

1. **Overall**: General readability and professional appearance
2. **Sharpness**: Edge clarity, text legibility, blur presence
3. **Color**: Color accuracy, white balance, saturation

Respond ONLY with JSON: {"overall": X.X, "sharpness": X.X, "color": X.X}
```

### 4.5 Checkpoint Selection

> **Strategy**: SRCC-primary selection with weighted ECE consideration. Within a configurable SRCC band,
> checkpoints compete on a combined score that allows trading small SRCC losses for significant ECE gains.
> This aligns with the original DocIQ paper (SRCC/PLCC) while adding calibration awareness.

```python
def compute_checkpoint_score(
    checkpoint: dict,
    specialty: str,
    best_srcc: float,
    srcc_weight: float = 0.7,
    ece_weight: float = 0.3,
    srcc_band: float = 0.02,
) -> float:
    """
    Compute weighted score for checkpoint selection.

    Within the SRCC band, we allow trading small SRCC losses for ECE gains.
    Outside the band, checkpoints are excluded.

    Args:
        checkpoint: Checkpoint metrics dict
        specialty: 'overall', 'sharpness', 'color', or 'mean'
        best_srcc: Best SRCC value among all checkpoints
        srcc_weight: Weight for SRCC component (default 0.7)
        ece_weight: Weight for ECE component (default 0.3)
        srcc_band: SRCC tolerance band (default 0.02)

    Returns:
        Combined score (higher is better), or -inf if outside band
    """
    srcc = checkpoint[f'srcc_{specialty}']
    ece = checkpoint['ece_mean']

    # Exclude checkpoints outside SRCC band
    if srcc < best_srcc - srcc_band:
        return float('-inf')

    # Normalize SRCC: 0 = band floor, 1 = best
    # This makes small SRCC differences within band less dramatic
    srcc_normalized = (srcc - (best_srcc - srcc_band)) / srcc_band

    # Normalize ECE: assume ECE range [0, 0.15], invert so lower is better
    # Clamped to [0, 1] range
    ece_normalized = max(0, min(1, 1 - (ece / 0.15)))

    return srcc_weight * srcc_normalized + ece_weight * ece_normalized


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

    Returns:
        Best checkpoint based on weighted score

    Example:
        Checkpoint A: SRCC=0.85, ECE=0.08 → score = 0.7*1.0 + 0.3*0.47 = 0.84
        Checkpoint B: SRCC=0.84, ECE=0.04 → score = 0.7*0.5 + 0.3*0.73 = 0.57
        Checkpoint C: SRCC=0.84, ECE=0.02 → score = 0.7*0.5 + 0.3*0.87 = 0.61

        With these weights, A wins. But if ECE improvement is larger:
        Checkpoint D: SRCC=0.84, ECE=0.01 → score = 0.7*0.5 + 0.3*0.93 = 0.63

        Adjusting weights to srcc_weight=0.6, ece_weight=0.4:
        Checkpoint A: 0.6*1.0 + 0.4*0.47 = 0.79
        Checkpoint D: 0.6*0.5 + 0.4*0.93 = 0.67

        A still wins, but the gap narrows for calibration-critical applications.
    """
    # Find best SRCC
    best_srcc = max(c[f'srcc_{specialty}'] for c in checkpoints)

    # Score all checkpoints
    scored = [
        (c, compute_checkpoint_score(c, specialty, best_srcc, srcc_weight, ece_weight, srcc_band))
        for c in checkpoints
    ]

    # Filter out excluded checkpoints and sort by score
    valid = [(c, s) for c, s in scored if s > float('-inf')]
    valid.sort(key=lambda x: x[1], reverse=True)

    return valid[0][0]
```

**Configuration Presets:**

| Preset | SRCC Weight | ECE Weight | SRCC Band | Use Case |
|--------|-------------|------------|-----------|----------|
| **SRCC-Dominant** | 0.8 | 0.2 | 0.015 | When ranking accuracy is critical |
| **Balanced** (default) | 0.7 | 0.3 | 0.02 | General-purpose pseudo-labeling |
| **Calibration-Aware** | 0.6 | 0.4 | 0.025 | When uncertainty estimates matter |

```python
CHECKPOINT_PRESETS = {
    'srcc_dominant': {'srcc_weight': 0.8, 'ece_weight': 0.2, 'srcc_band': 0.015},
    'balanced': {'srcc_weight': 0.7, 'ece_weight': 0.3, 'srcc_band': 0.02},
    'calibration_aware': {'srcc_weight': 0.6, 'ece_weight': 0.4, 'srcc_band': 0.025},
}
```

---

## 5. Uncertainty-Aware Stacking (REVISED)

### 5.1 Critical Fix: Within-Dimension Variance

**Previous approach (INCORRECT):**

```python
# WRONG: Cross-dimension divergence as uncertainty
uncertainty = abs(DocIQ_sharpness - DocIQ_color)
```

**Problem:** Divergence between dimensions often signals **truth** (e.g., a sharp B&W document has Sharpness=5.0 but Color=1.0), not model uncertainty.

**Corrected approach:**

```python
# CORRECT: Within-dimension model variance as uncertainty
def compute_uncertainty(
    model_predictions: dict[str, dict[str, float]],
    dimension: str,
    specialist_indices: list[int]
) -> float:
    """
    Uncertainty = variance of specialist predictions for the same dimension.
    High variance = models disagree = high uncertainty.
    """
    specialist_preds = [
        model_predictions[model][dimension]
        for model in specialist_indices
    ]
    return np.var(specialist_preds)
```

### 5.2 Revised Stacker Architecture

```python
class HierarchicalStacker(nn.Module):
    """
    Combines specialist predictions using within-dimension variance
    as the uncertainty signal (not cross-dimension divergence).
    """

    def __init__(self, n_models: int = 5, hidden: int = 32):
        super().__init__()

        # Model indices by dimension
        # 0=Qwen (gen), 1=DocIQ (gen), 2=MUSIQ (spec), 3=QualiCLIP (spec), 4=InternVL (spec)
        # Generalists (0, 1) contribute to ALL dimensions
        # Specialists contribute primarily to their specialty
        self.specialties = {
            'overall': [0, 1, 4],   # Qwen (gen), DocIQ (gen), InternVL (specialist)
            'sharpness': [0, 1, 2], # Qwen (gen), DocIQ (gen), MUSIQ (specialist)
            'color': [0, 1, 3],     # Qwen (gen), DocIQ (gen), QualiCLIP (specialist)
        }

        # Per-dimension encoders
        self.dim_encoders = nn.ModuleDict({
            dim: nn.Linear(n_models, hidden)
            for dim in ['overall', 'sharpness', 'color']
        })

        # Variance encoder (uncertainty signal)
        self.variance_encoder = nn.Linear(3, hidden)  # 3 within-dim variances

        # Fusion and output
        self.fusion = nn.Sequential(
            nn.Linear(hidden * 2, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 2)  # [prediction, log_variance]
        )

    def forward(
        self,
        all_preds: torch.Tensor
    ) -> dict[str, dict[str, torch.Tensor]]:
        """
        Args:
            all_preds: [batch, n_models, 3] - all model predictions

        Returns:
            Dict with pred and var for each dimension
        """
        batch_size = all_preds.shape[0]
        results = {}

        # Compute within-dimension variances
        variances = []
        for i, dim in enumerate(['overall', 'sharpness', 'color']):
            specialist_idx = self.specialties[dim]
            dim_preds = all_preds[:, specialist_idx, i]  # [batch, n_specialists]
            var = dim_preds.var(dim=1, keepdim=True)     # [batch, 1]
            variances.append(var)

        variance_tensor = torch.cat(variances, dim=1)    # [batch, 3]
        variance_feat = self.variance_encoder(variance_tensor)

        # Process each dimension
        for i, dim in enumerate(['overall', 'sharpness', 'color']):
            # Encode all model predictions for this dimension
            dim_preds = all_preds[:, :, i]  # [batch, n_models]
            dim_feat = self.dim_encoders[dim](dim_preds)

            # Fuse with variance (uncertainty) signal
            combined = torch.cat([dim_feat, variance_feat], dim=-1)
            output = self.fusion(combined)

            pred = output[:, 0]
            var = F.softplus(output[:, 1]) + 1e-6

            results[dim] = {'pred': pred, 'var': var}

        return results
```

### 5.3 Calibration Loss

```python
def stacker_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    pred_var: torch.Tensor
) -> torch.Tensor:
    """
    Heteroscedastic loss with calibration regularization.
    """
    # Negative log-likelihood (encourages uncertainty matching)
    nll = 0.5 * (torch.log(pred_var) + (pred - target)**2 / pred_var)

    # Calibration: predicted std should match actual error
    pred_std = torch.sqrt(pred_var)
    actual_error = (pred - target).abs()
    calibration = F.mse_loss(pred_std, actual_error)

    return nll.mean() + 0.5 * calibration
```

### 5.4 Temperature Scaling

```python
class TemperatureScaler(nn.Module):
    """Per-dimension temperature scaling for final calibration."""

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(3))

    def forward(
        self,
        pred: torch.Tensor,
        var: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return pred, var * self.temperature.unsqueeze(0)
```

---

## 6. ECE Definition for Regression (FORMALIZED)

### 6.1 Binned ECE for Continuous Scores

For 1-5 regression scores, we define ECE using equal-width bins:

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
    bin_edges = np.linspace(
        uncertainties.min(),
        uncertainties.max(),
        n_bins + 1
    )

    ece = 0.0
    total_samples = len(predictions)

    for i in range(n_bins):
        # Find samples in this uncertainty bin
        mask = (uncertainties >= bin_edges[i]) & (uncertainties < bin_edges[i + 1])
        if i == n_bins - 1:  # Include right edge in last bin
            mask = (uncertainties >= bin_edges[i]) & (uncertainties <= bin_edges[i + 1])

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

### 6.2 Alternative: Variance-Based Calibration

```python
def compute_variance_calibration(
    predictions: np.ndarray,
    targets: np.ndarray,
    predicted_variances: np.ndarray
) -> dict[str, float]:
    """
    Variance-based calibration metrics.

    Returns:
        - ece: Expected Calibration Error
        - nll: Negative Log-Likelihood (lower is better)
        - sharpness: Mean predicted std (lower is better, given calibration)
    """
    errors = predictions - targets
    pred_std = np.sqrt(predicted_variances)

    # NLL under Gaussian assumption
    nll = 0.5 * np.mean(
        np.log(predicted_variances) + (errors ** 2) / predicted_variances
    )

    # Calibration: are errors proportional to predicted uncertainty?
    # Compute correlation between |error| and predicted std
    calibration_corr = np.corrcoef(np.abs(errors), pred_std)[0, 1]

    # ECE via binning
    ece = compute_regression_ece(predictions, targets, pred_std)

    return {
        'ece': ece,
        'nll': nll,
        'sharpness': pred_std.mean(),
        'calibration_correlation': calibration_corr,
    }
```

---

## 7. Ensemble Weighting

### 7.1 Per-Dimension Weight Matrix

```python
ENSEMBLE_WEIGHTS = {
    'overall': {
        'qwen3_vl_8b': 0.30,     # Generalist anchor (VLM)
        'dociq_replica': 0.20,   # Generalist anchor (IQA) - balanced contribution
        'musiq': 0.10,           # Off-specialty (IQA)
        'qualiclip': 0.10,       # Off-specialty (IQA)
        'internvl3_8b': 0.30,    # Overall specialist (VLM)
    },
    'sharpness': {
        'qwen3_vl_8b': 0.15,     # Generalist anchor (VLM)
        'dociq_replica': 0.20,   # Generalist anchor (IQA) - balanced contribution
        'musiq': 0.35,           # Sharpness specialist (IQA)
        'qualiclip': 0.10,       # Off-specialty (IQA)
        'internvl3_8b': 0.20,    # Off-specialty (VLM)
    },
    'color': {
        'qwen3_vl_8b': 0.20,     # Generalist anchor (VLM)
        'dociq_replica': 0.20,   # Generalist anchor (IQA) - balanced contribution
        'musiq': 0.10,           # Off-specialty (IQA)
        'qualiclip': 0.40,       # Color specialist (IQA)
        'internvl3_8b': 0.10,    # Off-specialty (VLM)
    },
}
```

> **Generalist Anchor Weights**: Both Qwen3-VL-8B (Track B) and DocIQ-Replica (Track A) receive
> consistent 15-30% weight across all dimensions. Specialists (MUSIQ, QualiCLIP, InternVL3) get
> higher weights (30-40%) only on their specialty dimension.

### 7.2 Learned vs Fixed Weights

For this single-use tool, the learned HierarchicalStacker is preferred over fixed weights since we're optimizing for accuracy without runtime constraints.

---

## 8. Inference Pipeline

### 8.1 Pipeline Flow

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    DIQA PSEUDO-LABELING PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Load Image → RGB conversion, normalization                          │
│                              ↓                                          │
│  ┌───────────────────────────┴───────────────────────────┐              │
│  │                                                       │              │
│  ▼                                                       ▼              │
│  ┌─────────────────────────┐       ┌─────────────────────────┐          │
│  │  TRACK A: IQA MODELS    │       │  TRACK B: VLM MODELS    │          │
│  │  (A10G / T4)            │       │  (A100-80GB)            │          │
│  ├─────────────────────────┤       ├─────────────────────────┤          │
│  │ DocIQ-Replica (FP32)    │       │ Qwen3-VL-8B (FP16)      │          │
│  │ MUSIQ (FP32)            │       │ InternVL3-8B (FP16)     │          │
│  │ QualiCLIP (FP32)        │       │                         │          │
│  │                         │       │                         │          │
│  │ Batch: 32-64            │       │ Batch: 1-4              │          │
│  │ Latency: <50ms/img      │       │ Latency: 200-400ms/img  │          │
│  └─────────────────────────┘       └─────────────────────────┘          │
│                │                               │                        │
│                └───────────────┬───────────────┘                        │
│                                ▼                                        │
│  3. Collect Predictions: [5 models × 3 dimensions]                      │
│                                ↓                                        │
│  4. Compute Within-Dimension Variances (uncertainty)                    │
│                                ↓                                        │
│  5. HierarchicalStacker Forward Pass                                    │
│                                ↓                                        │
│  6. Temperature Scaling                                                 │
│                                ↓                                        │
│  7. Output: 3 scores + 3 uncertainties + metadata                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Output Format

```python
@dataclass
class DIQAPseudoLabel:
    """Output format for pseudo-labeled images."""

    # Quality scores (1-5 scale)
    overall_score: float
    sharpness_score: float
    color_score: float

    # Calibrated uncertainties (standard deviation)
    overall_uncertainty: float
    sharpness_uncertainty: float
    color_uncertainty: float

    # Metadata
    model_predictions: dict[str, dict[str, float]]
    within_dim_variances: dict[str, float]
    inference_time_ms: float

    # Quality flags
    high_uncertainty: bool  # Any dimension uncertainty > threshold
    model_disagreement: bool  # Any within-dim variance > threshold


# Example output
{
    'overall_score': 4.2,
    'sharpness_score': 3.8,
    'color_score': 4.5,
    'overall_uncertainty': 0.15,
    'sharpness_uncertainty': 0.22,
    'color_uncertainty': 0.11,
    'model_predictions': {
        'qwen3_vl_8b': {'overall': 4.1, 'sharpness': 3.9, 'color': 4.4},
        'dociq_replica': {'overall': 4.0, 'sharpness': 3.7, 'color': 4.3},
        'musiq': {'overall': 4.2, 'sharpness': 3.8, 'color': 4.5},
        'qualiclip': {'overall': 4.3, 'sharpness': 3.6, 'color': 4.6},
        'internvl3_8b': {'overall': 4.2, 'sharpness': 3.9, 'color': 4.4},
    },
    'within_dim_variances': {
        'overall': 0.012,
        'sharpness': 0.048,
        'color': 0.006,
    },
    'inference_time_ms': 423,
    'high_uncertainty': False,
    'model_disagreement': False,
}
```

---

## 9. Validation & Testing

### 9.1 Benchmark Metrics (DIQA-5000)

| Metric | Description | Target |
|--------|-------------|--------|
| DIQA5000_SRCC | Spearman rank correlation | > 0.94 |
| DIQA5000_PLCC | Pearson linear correlation | > 0.92 |
| DIQA5000_SRCC_CI_Lower | 95% CI lower bound | Report |
| DIQA5000_SRCC_CI_Upper | 95% CI upper bound | Report |
| DIQA5000_ECE | Expected calibration error | < 0.08 |

### 9.2 Confidence Interval Computation

```python
def compute_srcc_with_ci(
    predictions: np.ndarray,
    targets: np.ndarray,
    n_bootstrap: int = 1000,
    ci: float = 0.95
) -> dict[str, float]:
    """
    Compute SRCC with bootstrap confidence intervals.
    """
    from scipy.stats import spearmanr

    # Point estimate
    srcc, _ = spearmanr(predictions, targets)

    # Bootstrap resampling
    n = len(predictions)
    bootstrap_srccs = []

    for _ in range(n_bootstrap):
        indices = np.random.choice(n, size=n, replace=True)
        boot_srcc, _ = spearmanr(predictions[indices], targets[indices])
        bootstrap_srccs.append(boot_srcc)

    # Compute percentile CI
    alpha = 1 - ci
    ci_lower = np.percentile(bootstrap_srccs, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_srccs, 100 * (1 - alpha / 2))

    return {
        'DIQA5000_SRCC': srcc,
        'DIQA5000_SRCC_CI_Lower': ci_lower,
        'DIQA5000_SRCC_CI_Upper': ci_upper,
        'DIQA5000_SRCC_CI_Width': ci_upper - ci_lower,
    }
```

### 9.3 Validation Checklist

- [ ] Per-dimension SRCC > 0.94 on DIQA-5000 benchmark
- [ ] SRCC 95% confidence interval width < 0.03
- [ ] Overall ECE < 0.08 across all dimensions
- [ ] Uncertainty correlates with actual prediction error (r > 0.6)
- [ ] Within-dimension variance correctly identifies model disagreement
- [ ] Specialist checkpoints outperform generalist on specialty dimension

### 9.4 Expected Per-Model Performance (Post Fine-Tuning)

> **Important**: These targets are for **fine-tuned models**, not base models. Base model benchmarks
> (see `docs/benchmarks/diqa5000_benchmark_results.csv`) show SRCC ~0.1-0.3, requiring fine-tuning.

| Model | Track | Role | Target SRCC | Target ECE | Notes |
|-------|-------|------|-------------|------------|-------|
| Qwen3-VL-8B | B (VLM) | Generalist Anchor | > 0.90 (all dims) | < 0.08 (all) | LoRA fine-tuned, balanced weights |
| DocIQ-Replica | A (IQA) | **Generalist Anchor** | > 0.85 (all dims) | < 0.08 (mean) | Trained from scratch, equal loss weights |
| MUSIQ | A (IQA) | Sharpness Specialist | > 0.88 (sharpness) | < 0.08 (sharpness) | Fine-tuned, 60% sharpness weight |
| QualiCLIP | A (IQA) | Color Specialist | > 0.85 (color) | < 0.08 (color) | Fine-tuned, 60% color weight |
| InternVL3-8B | B (VLM) | Overall Specialist | > 0.88 (overall) | < 0.08 (overall) | LoRA fine-tuned, 60% overall weight |

> **Generalist vs Specialist Targets**: Generalists (Qwen3-VL-8B, DocIQ-Replica) are expected to
> achieve balanced performance across all dimensions. Specialists are expected to excel on their
> specialty dimension with acceptable (but not optimal) performance on other dimensions.

**Baseline Performance (No Fine-Tuning):**

| Model | Overall SRCC | Sharpness SRCC | Color SRCC | Source |
|-------|-------------|----------------|------------|--------|
| PyIQA-MUSIQ | 0.116 | 0.213 | 0.112 | Benchmark 2025-12-18 |
| PyIQA-QualiCLIP | 0.104 | 0.196 | 0.102 | Benchmark 2025-12-18 |

> **Conclusion**: All IQA models require fine-tuning on DIQA-5000 to achieve target performance.

### 9.5 Additional Test Coverage

Beyond DIQA-5000, validate on:

1. **Synthetic degradation set**: Clean documents with controlled blur/noise/compression
2. **Edge cases**: Monochrome receipts, scan lines, moiré patterns
3. **Distribution shift**: Document types not in DIQA-5000

---

## 10. Implementation Checklist

### Phase 1: Model Setup

- [ ] Configure Modal with A100 for all models (single GPU sufficient)
- [ ] Load all 5 models in full precision
- [ ] Verify VRAM usage and inference times
- [ ] Implement VLM prompting for Qwen and InternVL

### Phase 2: Training

- [ ] Implement multi-task heads for each base model
- [ ] Train specialists with weighted loss (60% specialty weight)
- [ ] Log ECE/SRCC for all dimensions per epoch
- [ ] Select checkpoints using specialty ECE criterion

### Phase 3: Stacker

- [ ] Implement revised HierarchicalStacker with within-dim variance
- [ ] Train stacker on held-out validation predictions
- [ ] Apply temperature scaling
- [ ] Validate calibration (ECE < 0.08)

### Phase 4: Validation

- [ ] Run DIQA-5000 benchmark with bootstrap CIs
- [ ] Test on synthetic degradations
- [ ] Verify uncertainty correlation with error
- [ ] Document edge case performance

### Phase 5: Deployment

- [ ] Package as Modal app for batch inference
- [ ] Implement output format and logging
- [ ] Run on target unlabeled dataset
- [ ] Export pseudo-labels with uncertainty metadata

---

## Appendix A: Complete Model Configuration

```python
MODEL_CONFIG = {
    # ============ Track B: VLM Models ============
    'qwen3_vl_8b': {
        'name': 'Qwen3-VL-8B',
        'hf_path': 'Qwen/Qwen3-VL-8B-Instruct',
        'track': 'B',
        'role': 'generalist_anchor',
        'precision': 'float16',
        'modal_gpu': 'A100-80GB',
        'specialty': None,
        'loss_weights': {'overall': 0.34, 'sharpness': 0.33, 'color': 0.33},
        'checkpoint_selection': 'ece_mean',
        'fine_tuning': 'lora',
        'status': 'available',
    },
    'internvl3_8b': {
        'name': 'InternVL3-8B',
        'hf_path': 'OpenGVLab/InternVL3-8B',
        'track': 'B',
        'role': 'overall_specialist',
        'precision': 'float16',
        'input_size': 448,
        'modal_gpu': 'A100-80GB',
        'specialty': 'overall',
        'loss_weights': {'overall': 0.6, 'sharpness': 0.2, 'color': 0.2},
        'checkpoint_selection': 'ece_overall',
        'fine_tuning': 'lora',
        'status': 'available',
    },
    # ============ Track A: IQA Models ============
    'dociq_replica': {
        'name': 'DocIQ-Replica',
        'backbone': 'resnet50',
        'architecture': 'layout_fusion_downsampler',  # True DocIQ replica
        'track': 'A',
        'sub_track': 'A3',
        'role': 'generalist_anchor',  # No IQA pretraining bias → balanced training
        'precision': 'float32',
        'input_size': 1600,  # Paper-aligned: 1600×1600
        'layout_masks': True,  # 11-class DocLayout-YOLO masks
        'n_layout_classes': 11,
        'modal_gpu': 'A100-80GB',  # Required for 1600×1600 + masks
        'specialty': None,  # Generalist - no specialty dimension
        'loss_weights': {'overall': 0.34, 'sharpness': 0.33, 'color': 0.33},  # Equal weights
        'checkpoint_selection': 'weighted',  # Weighted(SRCC, ECE) scoring
        'checkpoint_preset': 'balanced',     # 70% SRCC, 30% ECE, ±0.02 band
        'fine_tuning': 'full',
        'total_epochs': 60,  # Paper-aligned: 60 epochs
        'lr_schedule': 'warmup_cosine',  # 5 epoch warmup + cosine decay
        'augmentation': ['horizontal_flip', 'rotation_5deg', 'mild_color_jitter'],
        'status': 'requires_training',  # Original DocIQ not available
    },
    'musiq': {
        'name': 'MUSIQ',
        'pyiqa_name': 'musiq',
        'backbone': 'vit_b_16',
        'track': 'A',
        'sub_track': 'A1',
        'role': 'sharpness_specialist',  # KonIQ-10k pretraining → blur/noise expertise
        'precision': 'float32',
        'input_size': 'variable',
        'modal_gpu': 'T4',
        'specialty': 'sharpness',
        'loss_weights': {'overall': 0.2, 'sharpness': 0.6, 'color': 0.2},
        'checkpoint_selection': 'ece_sharpness',
        'fine_tuning': 'full',
        'total_epochs': 30,
        'status': 'available',
    },
    'qualiclip': {
        'name': 'QualiCLIP',
        'pyiqa_name': 'qualiclip',
        'backbone': 'clip_vit_b_32',
        'track': 'A',
        'sub_track': 'A2',
        'role': 'color_specialist',  # CLIP pretraining → color vocabulary understanding
        'precision': 'float32',
        'input_size': 224,
        'modal_gpu': 'T4',
        'specialty': 'color',
        'loss_weights': {'overall': 0.2, 'sharpness': 0.2, 'color': 0.6},
        'checkpoint_selection': 'ece_color',
        'fine_tuning': 'full',
        'total_epochs': 30,
        'status': 'available',
    },
}
```

## Appendix B: Stacker Configuration

```python
STACKER_CONFIG = {
    'architecture': 'HierarchicalStacker',
    'hidden_dim': 32,
    'n_models': 5,
    'n_dimensions': 3,

    # Training
    'learning_rate': 1e-3,
    'weight_decay': 1e-4,
    'epochs': 100,
    'batch_size': 256,
    'calibration_weight': 0.5,
    'early_stopping_patience': 10,

    # Temperature scaling
    'temp_scaling_epochs': 20,
    'temp_scaling_lr': 0.01,

    # Model indices and roles
    # Model order: qwen3_vl_8b, dociq_replica, musiq, qualiclip, internvl3_8b
    'model_order': ['qwen3_vl_8b', 'dociq_replica', 'musiq', 'qualiclip', 'internvl3_8b'],
    'model_roles': {
        'qwen3_vl_8b': 'generalist_anchor',   # Track B generalist
        'dociq_replica': 'generalist_anchor', # Track A generalist
        'musiq': 'sharpness_specialist',
        'qualiclip': 'color_specialist',
        'internvl3_8b': 'overall_specialist',
    },

    # Specialist indices by dimension
    # Generalists (indices 0, 1) contribute to ALL dimensions
    # Specialists contribute primarily to their specialty
    'specialties': {
        'overall': [0, 1, 4],      # qwen3 (gen), dociq (gen), internvl3 (specialist)
        'sharpness': [0, 1, 2],    # qwen3 (gen), dociq (gen), musiq (specialist)
        'color': [0, 1, 3],        # qwen3 (gen), dociq (gen), qualiclip (specialist)
    },

    # Uncertainty thresholds
    'high_uncertainty_threshold': 0.5,  # Flag if predicted std > 0.5
    'high_variance_threshold': 0.1,     # Flag if within-dim variance > 0.1
}
```

---

## Appendix C: Model Naming, Storage, and Versioning

### C.1 Model Naming Convention

**Format:** `{task}_{architecture}_{variant}_v{major}.{minor}.{patch}`

| Component | Description | Examples |
|-----------|-------------|----------|
| `task` | Primary task | `diqa`, `iqa`, `vlm` |
| `architecture` | Model architecture | `resnet50`, `musiq`, `qwen3vl8b` |
| `variant` | Specialization | `sharpness`, `color`, `overall`, `generalist` |
| `version` | Semantic version | `v1.0.0`, `v1.2.3` |

**Examples:**

```text
diqa_resnet50_sharpness_v1.0.0      # DocIQ-Replica for sharpness
diqa_musiq_sharpness_v1.0.0         # Fine-tuned MUSIQ
diqa_qualiclip_color_v1.0.0         # Fine-tuned QualiCLIP
diqa_qwen3vl8b_generalist_v1.0.0    # LoRA fine-tuned Qwen3-VL
diqa_internvl3_overall_v1.0.0       # LoRA fine-tuned InternVL3
diqa_stacker_ensemble_v1.0.0        # Trained stacker weights
```

### C.2 Storage Structure

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

### C.3 Model Card Template

Each trained model MUST have a `MODEL_CARD.md` file:

```markdown
# Model Card: {model_name}

## Model Details

| Field | Value |
|-------|-------|
| **Model ID** | `diqa_resnet50_sharpness_v1.0.0` |
| **Track** | A (IQA) / B (VLM) |
| **Architecture** | ResNet-50 + MultiTaskHead |
| **Parameters** | 25.6M |
| **Precision** | FP32 |
| **Input Size** | 384×384 |
| **Output** | 3 scores (overall, sharpness, color) |

## Training Details

| Field | Value |
|-------|-------|
| **Dataset** | DIQA-5000 train split (3500 images) |
| **Epochs** | 50 |
| **Batch Size** | 32 |
| **Learning Rate** | 1e-4 |
| **Optimizer** | AdamW |
| **Loss** | MSE + Rank + Focal ECE |
| **GPU** | Modal A10G |
| **Training Time** | 8.5 hours |
| **Training Date** | 2025-12-20 |

## Performance Metrics

### DIQA-5000 Test Set (n=1000)

| Dimension | SRCC | SRCC 95% CI | PLCC | ECE |
|-----------|------|-------------|------|-----|
| Overall | 0.82 | [0.79, 0.85] | 0.84 | 0.065 |
| Sharpness | 0.87 | [0.84, 0.90] | 0.88 | 0.052 |
| Color | 0.78 | [0.74, 0.82] | 0.80 | 0.071 |

### Inference Performance

| Metric | Value |
|--------|-------|
| Latency (T4) | 42ms |
| Latency (A10G) | 28ms |
| Memory | 1.2GB |

## Intended Use

- **Primary use**: Sharpness quality assessment for document images
- **Secondary use**: Multi-dimensional quality scoring (with caveats)
- **Out of scope**: Natural image IQA, video quality

## Limitations

- Trained only on DIQA-5000; may not generalize to all document types
- Color dimension performance below target (0.78 vs 0.80 target)
- Not suitable for real-time streaming applications

## Lineage

| Field | Value |
|-------|-------|
| **Base Model** | ResNet-50 (ImageNet1K_V2) |
| **Parent Version** | N/A (first version) |
| **Training Script** | `modal/train_dociq_replica.py` |
| **Commit SHA** | `abc123def456` |

## Files

| File | Description | Size |
|------|-------------|------|
| `model.pt` | PyTorch checkpoint | 98MB |
| `model.onnx` | ONNX export | 97MB |
| `config.json` | Model configuration | 2KB |

## Citation

    ```bibtex
    @misc{diqa_resnet50_sharpness,
      title={DocIQ-Replica: Sharpness Specialist for DIQA},
      author={Project A Team},
      year={2025},
      note={Internal model}
    }
    ```

```

### C.4 Version Promotion Workflow

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
│     ├─ Check ECE < threshold                                            │
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

### C.5 Model Registry Schema

```python
@dataclass
class ModelRegistryEntry:
    """Schema for model registry entries."""

    # Identity
    model_id: str                    # e.g., "diqa_resnet50_sharpness_v1.0.0"
    track: Literal['A', 'B']         # IQA or VLM
    version: str                     # Semantic version
    created_at: datetime

    # Location
    gcs_path: str                    # gs://bucket/path/to/model/
    checkpoint_file: str             # model.pt or adapter_model.safetensors
    onnx_file: str | None            # Optional ONNX export

    # Performance
    diqa5000_srcc_overall: float
    diqa5000_srcc_sharpness: float
    diqa5000_srcc_color: float
    diqa5000_ece_mean: float

    # Metadata
    training_commit: str             # Git commit SHA
    training_script: str             # Path to training script
    base_model: str                  # Parent model or pretrained source
    status: Literal['dev', 'staging', 'prod', 'deprecated']

    # Inference
    inference_latency_ms: float      # Mean latency on T4
    memory_mb: float                 # Peak VRAM usage
```

---

## Summary of Changes from v1.0

| Aspect | v1.0 | v2.0 | Rationale |
|--------|------|------|-----------|
| **Qwen model** | Qwen2.5-VL-72B | Qwen3-VL-8B | Updated to latest, smaller efficient model |
| **Overall specialist** | DeepSeek-VL | InternVL3-8B | Better availability, consistent naming |
| **DocIQ** | Assumed available | Requires training (DocIQ-Replica) | Model not publicly available |
| **DocIQ role** | Sharpness specialist | **Generalist Anchor** | No IQA pretraining bias → balanced training |
| **DocIQ architecture** | Simplified ResNet-50 | **True DocIQ Replica** with Layout Fusion Downsampler | Paper alignment decision |
| **DocIQ input size** | 384×384 | **1600×1600** | Aligned with original DocIQ paper |
| **Layout masks** | Not used | **11-class DocLayout-YOLO** | Required for Layout Fusion Downsampler |
| **DocIQ epochs** | 50 | **60** | Aligned with original DocIQ paper |
| **Checkpoint selection** | ECE-primary | **Weighted(SRCC, ECE)** with band | SRCC-primary (70%), ECE gains within ±0.02 band |
| **Track architecture** | Single pipeline | Split Track A (IQA) / Track B (VLM) | Different GPU/training requirements |
| **Sub-tracks** | N/A | A1 (MUSIQ), A2 (QualiCLIP), A3 (DocIQ) | Distinct training protocols per model |
| **Performance targets** | SRCC > 0.94 (base) | SRCC > 0.85-0.90 (fine-tuned) | Realistic based on benchmarks |
| **Latency target** | <150ms | Track A: <50ms, Track B: 200-400ms | Track-specific optimization |
| **Uncertainty signal** | Cross-dim divergence | Within-dim variance | Fix logical flaw |
| **ECE definition** | Undefined | Formally specified | Enable validation |
| **Model storage** | Undefined | GCS with versioning + MODEL_CARD.md | Reproducibility |
| **Deployment** | Production pipeline | Offline batch job | Clarified scope |

---

*Document Version 2.0 — December 2025*
