# Phase 7: Continuous Labels Strategy

## Executive Summary

Phase 7 transitions the IQA training pipeline from **binary labels (0/1)** to **continuous severity labels [0,1]**, enabling more nuanced quality assessment and improved model calibration. This document outlines the strategy for:

1. Integrating **DocCreator** for physics-based document degradation with XML ground truth
2. Integrating **Augraphy** for Python-native augmentation with continuous parameter extraction
3. Expanding the dataset from **100k to 150k images** using the same original source images
4. Implementing a **hybrid loss function** (SoftBCE + PLCC + Rank)
5. Optional **MLLM teacher distillation** using DeQA-Score pseudo-labels
6. **GDBC (Gated Dual-Bias Calibration)** for handling annotation noise

---

## 1. Current State Analysis

### 1.1 Existing Architecture

| Component | Current Implementation | Continuous Label Readiness |
|-----------|----------------------|---------------------------|
| **Labels** | Binary (0/1) per issue | Metadata contains raw metrics |
| **Weak Supervision** | Thresholds continuous → binary | Preserves raw values in dict |
| **Model Output** | Sigmoid → [0,1] continuous | Already continuous |
| **Loss Functions** | BCE (classification) + MSE (confidence) | Can adapt to regression |
| **Dataset** | 100k images, binary extraction | Infrastructure ready |

### 1.2 Key Insight

The current pipeline **already outputs continuous scores** but trains on binary labels. The transition requires:
1. Preserving augmentation parameters as continuous labels
2. Modifying loss functions for regression
3. Adding correlation-based objectives (PLCC, SRCC)

---

## 2. Data Generation Strategy

### 2.1 Dataset Composition (150k Total)

| Source | Count | Label Type | Ground Truth Quality |
|--------|-------|------------|---------------------|
| **DocCreator** (physics-based) | 45,000 | Perfect (XML) | ★★★★★ |
| **Augraphy** (parametric) | 90,000 | Perfect (computed) | ★★★★★ |
| **OHR-Bench** (existing) | 10,000 | MOS (crowdsourced) | ★★★☆☆ |
| **DIQA-5000** (existing) | 5,000 | MOS (expert) | ★★★★☆ |

### 2.2 DocCreator Integration

DocCreator provides **physics-based document degradation** with 7 degradation models:

```
┌─────────────────────────────────────────────────────────────────┐
│ DocCreator Degradation Pipeline                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Clean Image ─┬─→ Ink Degradation ──→ severity: 0.0-1.0        │
│               ├─→ Bleed-Through ────→ severity: 0.0-1.0        │
│               ├─→ Adaptive Blur ────→ severity: 0.0-1.0        │
│               ├─→ Paper Deformation ─→ severity: 0.0-1.0       │
│               ├─→ Phantom Character ─→ severity: 0.0-1.0       │
│               ├─→ Noise (paper) ────→ severity: 0.0-1.0        │
│               └─→ Watermark ────────→ severity: 0.0-1.0        │
│                                                                 │
│  Output: degraded_image.png + ground_truth.xml                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**XML Ground Truth Schema:**
```xml
<document>
  <degradation type="blur" severity="0.65" method="adaptive">
    <params>
      <kernel_size>7</kernel_size>
      <sigma>2.3</sigma>
      <spatial_variation>true</spatial_variation>
    </params>
  </degradation>
  <degradation type="noise" severity="0.42" method="paper_aging">
    <params>
      <intensity>0.42</intensity>
      <distribution>gaussian</distribution>
    </params>
  </degradation>
</document>
```

**Integration Module: `data/doccreator_loader.py`**

```python
from dataclasses import dataclass
from xml.etree import ElementTree as ET

@dataclass
class DocCreatorLabel:
    """Continuous label from DocCreator XML ground truth."""
    blur_severity: float        # [0, 1]
    noise_severity: float       # [0, 1]
    ink_degradation: float      # [0, 1]
    bleed_through: float        # [0, 1]
    paper_deformation: float    # [0, 1]
    overall_quality: float      # Computed: 1 - max(severities)

def parse_doccreator_xml(xml_path: Path) -> DocCreatorLabel:
    """Parse DocCreator XML ground truth to continuous labels."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    severities = {
        'blur': 0.0,
        'noise': 0.0,
        'ink_degradation': 0.0,
        'bleed_through': 0.0,
        'paper_deformation': 0.0,
    }

    for degradation in root.findall('.//degradation'):
        deg_type = degradation.get('type')
        severity = float(degradation.get('severity', 0.0))

        # Map DocCreator types to our schema
        if deg_type in ['adaptive_blur', 'motion_blur', 'defocus']:
            severities['blur'] = max(severities['blur'], severity)
        elif deg_type in ['paper_noise', 'scanner_noise']:
            severities['noise'] = max(severities['noise'], severity)
        # ... additional mappings

    return DocCreatorLabel(
        blur_severity=severities['blur'],
        noise_severity=severities['noise'],
        ink_degradation=severities['ink_degradation'],
        bleed_through=severities['bleed_through'],
        paper_deformation=severities['paper_deformation'],
        overall_quality=1.0 - max(severities.values()),
    )
```

### 2.3 Augraphy Integration

Augraphy provides a **Python-native layered augmentation pipeline** with continuous parameter extraction:

```
┌─────────────────────────────────────────────────────────────────┐
│ Augraphy Layered Architecture                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Ink Layer ──┬─→ InkBleed ──────────→ params: {intensity: 0.4} │
│              ├─→ Letterpress ───────→ params: {n_copies: 3}    │
│              └─→ LowInkLine ────────→ params: {prob: 0.6}      │
│                                                                 │
│  Paper Layer ┬─→ WaterMark ─────────→ params: {alpha: 0.3}     │
│              ├─→ DirtyDrum ─────────→ params: {intensity: 0.5} │
│              └─→ PaperFactory ──────→ params: {texture: 'old'} │
│                                                                 │
│  Final ──────┬─→ GaussianBlur ──────→ params: {sigma: 2.1}     │
│              ├─→ Gamma ─────────────→ params: {gamma: 1.4}     │
│              └─→ JPEG ──────────────→ params: {quality: 65}    │
│                                                                 │
│  Output: augmented_image + return_dict with all params          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Integration Module: `data/augraphy_pipeline.py`**

```python
import augraphy
from augraphy import *

class AugraphyContinuousLabeler:
    """Augraphy pipeline with continuous label extraction."""

    def __init__(self, severity_preset: str = "medium"):
        self.severity_preset = severity_preset
        self._configure_pipelines()

    def _configure_pipelines(self):
        """Configure ink, paper, and post-processing layers."""

        # Severity ranges based on preset
        severity_ranges = {
            "light": (0.1, 0.4),
            "medium": (0.3, 0.7),
            "heavy": (0.5, 0.95),
        }
        low, high = severity_ranges[self.severity_preset]

        self.ink_phase = [
            InkBleed(
                intensity_range=(low, high),
                kernel_size_range=(3, 7),
                p=0.3
            ),
            Letterpress(
                n_copies_range=(1, 3),
                p=0.2
            ),
        ]

        self.paper_phase = [
            DirtyDrum(
                intensity_range=(low, high),
                p=0.25
            ),
            WaterMark(
                alpha_range=(0.1, 0.5),
                p=0.15
            ),
        ]

        self.post_phase = [
            GaussianBlur(
                sigma_range=(0.5, 3.0),
                p=0.3
            ),
            Gamma(
                gamma_range=(0.7, 1.5),
                p=0.25
            ),
            Jpeg(
                quality_range=(50, 95),
                p=0.2
            ),
        ]

        self.pipeline = AugraphyPipeline(
            ink_phase=self.ink_phase,
            paper_phase=self.paper_phase,
            post_phase=self.post_phase,
        )

    def augment(self, image: np.ndarray) -> tuple[np.ndarray, dict]:
        """Apply augmentation and extract continuous labels.

        Returns:
            Tuple of (augmented_image, continuous_labels_dict)
        """
        # Enable return_dict for parameter extraction
        result = self.pipeline.augment(image, return_dict=True)
        augmented = result['output']
        params = result['pipeline_params']

        # Convert params to continuous severity labels
        labels = self._params_to_continuous_labels(params)

        return augmented, labels

    def _params_to_continuous_labels(self, params: dict) -> dict:
        """Map augmentation parameters to [0,1] severity scores.

        Mapping functions:
        - GaussianBlur: severity = min(sigma / sigma_max, 1.0)
        - JPEG: severity = 1 - (quality / 100)
        - Gamma: severity = abs(gamma - 1.0) / 0.5 (normalized deviation)
        - Noise: severity = intensity (already [0,1])
        """
        labels = {
            'blur_severity': 0.0,
            'noise_severity': 0.0,
            'contrast_severity': 0.0,
            'compression_severity': 0.0,
            'ink_degradation': 0.0,
            'paper_degradation': 0.0,
        }

        for aug_name, aug_params in params.items():
            if 'GaussianBlur' in aug_name:
                sigma = aug_params.get('sigma', 0)
                labels['blur_severity'] = min(sigma / 5.0, 1.0)

            elif 'Jpeg' in aug_name:
                quality = aug_params.get('quality', 100)
                labels['compression_severity'] = 1.0 - (quality / 100.0)

            elif 'Gamma' in aug_name:
                gamma = aug_params.get('gamma', 1.0)
                labels['contrast_severity'] = min(abs(gamma - 1.0) / 0.5, 1.0)

            elif 'InkBleed' in aug_name or 'Letterpress' in aug_name:
                intensity = aug_params.get('intensity', 0)
                labels['ink_degradation'] = max(labels['ink_degradation'], intensity)

            elif 'DirtyDrum' in aug_name or 'WaterMark' in aug_name:
                intensity = aug_params.get('intensity', aug_params.get('alpha', 0))
                labels['paper_degradation'] = max(labels['paper_degradation'], intensity)

        # Compute overall quality (inverse of max severity)
        max_severity = max(labels.values())
        labels['overall_quality'] = 1.0 - max_severity

        return labels
```

### 2.4 Severity Mapping Functions

| Augmentation | Parameter | Mapping to [0,1] |
|--------------|-----------|------------------|
| GaussianBlur | σ (sigma) | `min(σ / σ_max, 1.0)` where σ_max = 5.0 |
| MotionBlur | kernel_size | `min(k / k_max, 1.0)` where k_max = 15 |
| JPEG | quality | `1.0 - (quality / 100.0)` |
| Gamma | γ | `min(abs(γ - 1.0) / 0.5, 1.0)` |
| GaussNoise | variance | `min(var / var_max, 1.0)` where var_max = 0.1 |
| Rotation | angle° | `min(abs(angle) / 45.0, 1.0)` |
| Perspective | scale | `scale / scale_max` where scale_max = 0.2 |
| Brightness | delta | `min(abs(delta) / 0.5, 1.0)` |

---

## 3. Continuous Label Schema

### 3.1 Schema Design

```python
from pydantic import BaseModel, Field
from typing import Literal

class ContinuousQualityLabel(BaseModel):
    """Continuous quality labels for Phase 7 training."""

    # Per-issue severity scores [0, 1]
    # 0 = no degradation, 1 = maximum degradation
    blur_severity: float = Field(ge=0.0, le=1.0, default=0.0)
    noise_severity: float = Field(ge=0.0, le=1.0, default=0.0)
    skew_severity: float = Field(ge=0.0, le=1.0, default=0.0)
    contrast_severity: float = Field(ge=0.0, le=1.0, default=0.0)
    compression_severity: float = Field(ge=0.0, le=1.0, default=0.0)

    # Document-specific degradations
    ink_degradation: float = Field(ge=0.0, le=1.0, default=0.0)
    paper_degradation: float = Field(ge=0.0, le=1.0, default=0.0)
    bleed_through: float = Field(ge=0.0, le=1.0, default=0.0)

    # Aggregated scores
    overall_quality: float = Field(ge=0.0, le=1.0, default=1.0)
    dmos: float = Field(ge=0.0, le=100.0, default=0.0)  # Differential MOS

    # Label provenance
    label_source: Literal["doccreator", "augraphy", "mos", "weak_supervision"]
    label_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    label_variance: float = Field(ge=0.0, default=0.0)  # For MOS labels (GDBC)

    # Augmentation metadata (for reproducibility)
    augmentation_params: dict = Field(default_factory=dict)
```

### 3.2 Backward Compatibility

To maintain compatibility with existing binary training:

```python
def continuous_to_binary(labels: ContinuousQualityLabel, threshold: float = 0.3) -> dict:
    """Convert continuous labels to binary for backward compatibility."""
    return {
        'blur': int(labels.blur_severity >= threshold),
        'noise': int(labels.noise_severity >= threshold),
        'skew': int(labels.skew_severity >= threshold),
        'illumination': int(labels.contrast_severity >= threshold),
        'artifacts': int(labels.compression_severity >= threshold),
    }

def binary_to_continuous(binary_labels: dict, confidence: float = 0.7) -> ContinuousQualityLabel:
    """Convert binary labels to soft continuous labels."""
    return ContinuousQualityLabel(
        blur_severity=binary_labels['blur'] * confidence,
        noise_severity=binary_labels['noise'] * confidence,
        skew_severity=binary_labels['skew'] * confidence,
        contrast_severity=binary_labels['illumination'] * confidence,
        compression_severity=binary_labels['artifacts'] * confidence,
        label_source='weak_supervision',
        label_confidence=confidence,
    )
```

---

## 4. Hybrid Loss Function

### 4.1 Loss Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Hybrid Loss Function for Continuous IQA                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  L_total = λ₁·L_SoftBCE + λ₂·L_PLCC + λ₃·L_Rank + λ₄·L_GDBC    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L_SoftBCE: Soft Binary Cross-Entropy                    │   │
│  │ • Handles probabilistic calibration y ∈ [0,1]           │   │
│  │ • Smooth transition from binary BCE                     │   │
│  │ • L = -[y·log(p) + (1-y)·log(1-p)]                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L_PLCC: Pearson Linear Correlation Coefficient          │   │
│  │ • Maximizes linear correlation with ground truth        │   │
│  │ • L = 1 - ρ(y_pred, y_true)                            │   │
│  │ • Ensures model learns relative severity ordering       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L_Rank: Margin Ranking Loss                             │   │
│  │ • Enforces: if y_A > y_B then pred_A > pred_B          │   │
│  │ • L = max(0, margin - (pred_A - pred_B))               │   │
│  │ • Handles tied/uncertain comparisons gracefully         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L_GDBC: Gated Dual-Bias Calibration (optional)          │   │
│  │ • Models subjective rating bias                         │   │
│  │ • Weights gradients by inverse annotation variance      │   │
│  │ • gate = 1 / (1 + σ²_annotation)                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Implementation

```python
# src/image_preprocessing_detector/models/continuous_loss.py

import torch
import torch.nn as nn
import torch.nn.functional as F

class ContinuousIQALoss(nn.Module):
    """Hybrid loss function for continuous IQA regression.

    Combines:
    - Soft BCE: Probabilistic calibration
    - PLCC Loss: Pearson correlation
    - Rank Loss: Pairwise ranking
    - GDBC: Annotation bias calibration (optional)

    Args:
        lambda_softbce: Weight for soft BCE loss (default: 0.3)
        lambda_plcc: Weight for PLCC loss (default: 0.4)
        lambda_rank: Weight for ranking loss (default: 0.2)
        lambda_gdbc: Weight for GDBC loss (default: 0.1)
        rank_margin: Margin for ranking loss (default: 0.05)
        use_gdbc: Enable GDBC for noisy annotations (default: True)
    """

    def __init__(
        self,
        lambda_softbce: float = 0.3,
        lambda_plcc: float = 0.4,
        lambda_rank: float = 0.2,
        lambda_gdbc: float = 0.1,
        rank_margin: float = 0.05,
        use_gdbc: bool = True,
    ):
        super().__init__()
        self.lambda_softbce = lambda_softbce
        self.lambda_plcc = lambda_plcc
        self.lambda_rank = lambda_rank
        self.lambda_gdbc = lambda_gdbc
        self.rank_margin = rank_margin
        self.use_gdbc = use_gdbc

    def forward(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
        variances: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute hybrid loss.

        Args:
            predictions: Model predictions [batch_size, num_issues] in [0,1]
            targets: Ground truth labels [batch_size, num_issues] in [0,1]
            variances: Optional annotation variances [batch_size, num_issues]
                       (from MOS datasets, for GDBC weighting)

        Returns:
            Dict with total_loss and component losses
        """
        # Soft BCE Loss (handles y ∈ [0,1])
        softbce_loss = self._soft_bce_loss(predictions, targets)

        # PLCC Loss (correlation)
        plcc_loss = self._plcc_loss(predictions, targets)

        # Ranking Loss (pairwise)
        rank_loss = self._rank_loss(predictions, targets)

        # GDBC Loss (bias calibration)
        if self.use_gdbc and variances is not None:
            gdbc_loss = self._gdbc_loss(predictions, targets, variances)
        else:
            gdbc_loss = torch.tensor(0.0, device=predictions.device)

        # Weighted combination
        total_loss = (
            self.lambda_softbce * softbce_loss +
            self.lambda_plcc * plcc_loss +
            self.lambda_rank * rank_loss +
            self.lambda_gdbc * gdbc_loss
        )

        return {
            'total_loss': total_loss,
            'softbce_loss': softbce_loss,
            'plcc_loss': plcc_loss,
            'rank_loss': rank_loss,
            'gdbc_loss': gdbc_loss,
        }

    def _soft_bce_loss(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """Soft Binary Cross-Entropy for continuous targets [0,1].

        Standard BCE formula works with soft targets:
        L = -[y·log(p) + (1-y)·log(1-p)]
        """
        # Clamp predictions to avoid log(0)
        eps = 1e-7
        predictions = torch.clamp(predictions, eps, 1 - eps)

        loss = -(
            targets * torch.log(predictions) +
            (1 - targets) * torch.log(1 - predictions)
        )

        return loss.mean()

    def _plcc_loss(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """Pearson Linear Correlation Coefficient Loss.

        L = 1 - ρ(pred, target)

        Maximizes linear correlation between predictions and targets.
        """
        # Flatten across all dimensions
        pred_flat = predictions.view(-1)
        target_flat = targets.view(-1)

        # Compute means
        pred_mean = pred_flat.mean()
        target_mean = target_flat.mean()

        # Compute covariance and standard deviations
        pred_centered = pred_flat - pred_mean
        target_centered = target_flat - target_mean

        covariance = (pred_centered * target_centered).mean()
        pred_std = pred_centered.std() + 1e-8
        target_std = target_centered.std() + 1e-8

        # Pearson correlation
        plcc = covariance / (pred_std * target_std)

        # Loss = 1 - correlation (minimize to maximize correlation)
        return 1 - plcc

    def _rank_loss(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        """Margin Ranking Loss for pairwise comparisons.

        For all pairs (i, j) where target_i > target_j:
        L = max(0, margin - (pred_i - pred_j))

        Ensures model respects quality ordering.
        """
        batch_size = predictions.size(0)

        if batch_size < 2:
            return torch.tensor(0.0, device=predictions.device)

        # Sample pairs for efficiency (all pairs is O(n²))
        num_pairs = min(batch_size * 4, batch_size * (batch_size - 1) // 2)

        # Generate random pair indices
        idx1 = torch.randint(0, batch_size, (num_pairs,), device=predictions.device)
        idx2 = torch.randint(0, batch_size, (num_pairs,), device=predictions.device)

        # Ensure different indices
        mask = idx1 != idx2
        idx1, idx2 = idx1[mask], idx2[mask]

        if len(idx1) == 0:
            return torch.tensor(0.0, device=predictions.device)

        # Get predictions and targets for pairs (flatten to 1D for simplicity)
        pred1 = predictions[idx1].mean(dim=-1)
        pred2 = predictions[idx2].mean(dim=-1)
        target1 = targets[idx1].mean(dim=-1)
        target2 = targets[idx2].mean(dim=-1)

        # Compute ranking direction: +1 if target1 > target2, -1 otherwise
        direction = torch.sign(target1 - target2)

        # Margin ranking loss
        loss = F.relu(self.rank_margin - direction * (pred1 - pred2))

        return loss.mean()

    def _gdbc_loss(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
        variances: torch.Tensor,
    ) -> torch.Tensor:
        """Gated Dual-Bias Calibration Loss.

        Weights MSE loss by inverse annotation variance:
        gate = 1 / (1 + σ²)
        L = gate * (pred - target)²

        High-variance annotations (disagreement) get lower weight.
        """
        # Compute sample weights from variance
        # gate = 1 / (1 + variance) → high variance = low weight
        gates = 1.0 / (1.0 + variances + 1e-8)

        # Weighted MSE
        mse = (predictions - targets) ** 2
        weighted_mse = gates * mse

        return weighted_mse.mean()


class MultiHeadContinuousLoss(nn.Module):
    """Multi-head version of ContinuousIQALoss for per-issue regression."""

    def __init__(
        self,
        head_names: list[str],
        head_weights: dict[str, float] | None = None,
        **kwargs,
    ):
        super().__init__()
        self.head_names = head_names
        self.head_weights = head_weights or {name: 1.0 for name in head_names}
        self.base_loss = ContinuousIQALoss(**kwargs)

    def forward(
        self,
        predictions: dict[str, torch.Tensor],
        targets: dict[str, torch.Tensor],
        variances: dict[str, torch.Tensor] | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute loss for each head and aggregate."""
        total_loss = torch.tensor(0.0)
        per_head_losses = {}

        for head_name in self.head_names:
            pred = predictions[head_name]
            target = targets[head_name]
            var = variances.get(head_name) if variances else None

            head_loss_dict = self.base_loss(pred, target, var)
            head_loss = head_loss_dict['total_loss']

            weighted_loss = head_loss * self.head_weights[head_name]
            total_loss = total_loss + weighted_loss
            per_head_losses[head_name] = head_loss

        # Normalize by number of heads
        total_loss = total_loss / len(self.head_names)

        return {
            'total_loss': total_loss,
            'per_head_losses': per_head_losses,
        }
```

---

## 5. MLLM Teacher Distillation (Optional)

### 5.1 Model Selection Based on Benchmarks

Based on comprehensive analysis of [Q-Doc](https://arxiv.org/html/2511.11410v1), [DeQA-Doc](https://arxiv.org/html/2507.12796), [Q-Bench](https://q-future.github.io/Q-Bench/), and [OmniDocBench](https://github.com/opendatalab/OmniDocBench), the following models are recommended for pseudo-label generation:

#### 5.1.1 Benchmark Summary

| Benchmark | Focus | Key Metrics |
|-----------|-------|-------------|
| **Q-Doc** | Document IQA (coarse/middle/fine) | Quality scoring, distortion detection, severity assessment |
| **DeQA-Doc** | Document quality regression | PLCC/SRCC on DIQA-5000 (sharpness, color, overall) |
| **Q-Bench** | General low-level vision | Perception, description, assessment tasks |
| **OmniDocBench** | Document parsing quality | Text/table/formula recognition accuracy |

#### 5.1.2 Model Rankings by Task

**Quality Score Regression (PLCC/SRCC correlation with human MOS):**

| Rank | Model | Dataset | Final Score / PLCC |
|------|-------|---------|-------------------|
| 🥇 | **DeQA-Doc (Qwen2.5-VL-7B + mPLUG ensemble)** | DIQA-5000 | **0.9288** |
| 🥈 | **DeQA-Doc (Qwen2.5-VL-7B 5-fold)** | DIQA-5000 | **0.9235** |
| 🥉 | DeQA-Doc (mPLUG-Owl2-7B) | DIQA-5000 | 0.9112 |
| 4 | DeepSeek-VL2 + CoT | Q-Doc | SRCC: 0.4603 |
| 5 | InternLM-XComposer-VL | Q-Bench | SRCC: 0.541 |

**Distortion Detection (blur, noise, defocus, brightness):**

| Rank | Model | Task | Balanced Accuracy |
|------|-------|------|-------------------|
| 🥇 | **GPT-4o** | Multi-distortion classification | **62.54%** |
| 🥈 | **DeepSeek-VL2 + CoT** | Multi-distortion classification | 51.20% |
| 🥉 | GPT-4o | Severity assessment (single) | 50.86% |
| 4 | DeepSeek-VL2 + CoT | Single distortion classification | 33.26% |

**Consistency Across All Levels (Q-Doc):**

| Model | Coarse (Score) | Middle (Detect) | Fine (Severity) | Verdict |
|-------|----------------|-----------------|-----------------|---------|
| **DeepSeek-VL2 + CoT** | ✅ Best SRCC | ✅ Good | ✅ Best overall | **Most consistent** |
| GPT-4o | ❌ Poor (0.13 SRCC) | ✅ Best | ✅ Good | Inconsistent |
| mPLUG-Owl3-7B | ⚠️ Medium | ⚠️ Medium | ⚠️ Medium | Moderate |

#### 5.1.3 Recommended Model Selection

Based on benchmark analysis, we recommend a **tiered approach**:

```
┌─────────────────────────────────────────────────────────────────┐
│ MLLM Selection Strategy for Phase 7 Pseudo-Labels              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TIER 1 (Primary - Quality Score Regression):                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DeQA-Doc with Qwen2.5-VL-7B                             │   │
│  │ • Best DIQA performance (0.9235 final score)            │   │
│  │ • Handles original resolution (no aggressive resize)    │   │
│  │ • Open-source, self-hostable                            │   │
│  │ • Cost: ~$0 (local GPU) or ~$0.002/image (cloud)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TIER 2 (Secondary - Distortion Detection):                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DeepSeek-VL2 (27B MoE)                                  │   │
│  │ • Most consistent across coarse/middle/fine levels      │   │
│  │ • Best with Chain-of-Thought prompting                  │   │
│  │ • Open-source, Apache 2.0 license                       │   │
│  │ • Cost: ~$0 (local) or ~$0.003/image (API)             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TIER 3 (Validation/Ensemble - Commercial):                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ GPT-4o (for distortion type verification only)          │   │
│  │ • Best multi-distortion classification (62.54%)         │   │
│  │ • Poor at quality scoring (SRCC: 0.13) - DO NOT USE    │   │
│  │ • Use only for distortion presence validation           │   │
│  │ • Cost: ~$0.01/image                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  NOT RECOMMENDED:                                               │
│  • Gemini-Pro: Underperforms on fine-grained quality tasks    │
│  • GPT-4V (old): Superseded by GPT-4o                         │
│  • Generic VLMs without IQA fine-tuning                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.1.4 Key Findings from Benchmarks

1. **GPT-4o fails at quality scoring** despite being state-of-the-art for general vision tasks
   - Q-Doc SRCC: 0.1321 (near random)
   - Excellent at distortion *identification* but poor at *severity estimation*

2. **DeQA-Doc (Qwen2.5-VL) is the clear winner for document IQA**
   - Final score 0.9235 on DIQA-5000 (5-fold ensemble)
   - Preserves fine-grained layout/text features via native resolution

3. **DeepSeek-VL2 is the most balanced** across all task levels
   - Only model maintaining competitive performance on coarse, middle, AND fine levels
   - MoE architecture provides efficient compute scaling

4. **Chain-of-Thought (CoT) prompting significantly improves performance**
   - DeepSeek-VL2 + CoT outperforms vanilla by 3-10% across tasks

### 5.2 Recommended Implementation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ MLLM Teacher Distillation Pipeline (Updated)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Unlabeled Images (150k) ─────────────────────────────────────┐ │
│                                                            ↓    │
│                                         ┌─────────────────────┐ │
│                                         │ DeQA-Doc            │ │
│                                         │ (Qwen2.5-VL-7B)     │ │
│                                         │ • Native resolution │ │
│                                         │ • DIQA-5000 trained │ │
│                                         │ • PLCC: 0.9235      │ │
│                                         └─────────────────────┘ │
│                                                   │             │
│                            ┌──────────────────────┼─────────┐   │
│                            ↓                      ↓         │   │
│                    Quality Scores         DeepSeek-VL2      │   │
│                    (overall, sharpness)   (distortion CoT)  │   │
│                            │                      │         │   │
│                            └──────────┬───────────┘         │   │
│                                       ↓                     │   │
│                              Ensemble Labels                │   │
│                              (JSON, [0,1] scores)           │   │
│                                       │                     │   │
│  ┌──────────────────────────────────────────────┐          │   │
│  │ ResNet-50 Student                            │←─────────┘   │
│  │ • Trained on ensemble pseudo-labels          │               │
│  │ • Learns DIQA-level quality understanding    │               │
│  │ • 1000x faster inference                     │               │
│  └──────────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 DeQA-Doc Prompt Template

```python
DEQA_PROMPT = """
Analyze this document image and rate its quality on a scale of 0.0 to 1.0 for each dimension.
0.0 = No degradation, perfect quality
1.0 = Maximum degradation, unreadable

Provide ratings for:
1. blur_severity: How blurry is the text/content?
2. noise_severity: How much visual noise/grain is present?
3. contrast_severity: How poor is the contrast/lighting?
4. skew_severity: How misaligned/rotated is the content?
5. compression_severity: How visible are compression artifacts?
6. overall_quality: Overall document quality (0.0 = worst, 1.0 = best)

Respond in JSON format only:
{
    "blur_severity": 0.XX,
    "noise_severity": 0.XX,
    "contrast_severity": 0.XX,
    "skew_severity": 0.XX,
    "compression_severity": 0.XX,
    "overall_quality": 0.XX
}
"""
```

### 5.3 Pseudo-Label Generation Script

```python
# scripts/generate_pseudo_labels.py

async def generate_pseudo_labels_batch(
    image_paths: list[Path],
    output_dir: Path,
    model: str = "gpt-4-vision-preview",
    batch_size: int = 10,
) -> None:
    """Generate pseudo-labels using MLLM for unlabeled images."""

    client = AsyncOpenAI()

    for batch_start in range(0, len(image_paths), batch_size):
        batch = image_paths[batch_start:batch_start + batch_size]

        tasks = [
            _query_mllm(client, image_path, model)
            for image_path in batch
        ]

        results = await asyncio.gather(*tasks)

        # Save pseudo-labels
        for image_path, labels in zip(batch, results):
            output_path = output_dir / f"{image_path.stem}_pseudo_labels.json"
            with open(output_path, 'w') as f:
                json.dump(labels, f, indent=2)

async def _query_mllm(
    client: AsyncOpenAI,
    image_path: Path,
    model: str,
) -> dict:
    """Query MLLM for quality assessment."""

    # Encode image as base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": DEQA_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"}
                    },
                ],
            }
        ],
        max_tokens=200,
    )

    # Parse JSON response
    content = response.choices[0].message.content
    labels = json.loads(content)
    labels['label_source'] = 'mllm_pseudo'
    labels['model'] = model

    return labels
```

---

## 6. Dataset Expansion Strategy

### 6.1 Source Images

Use the same **original clean images** from the 100k training set as seeds:

| Original Source | Clean Images | Augmentation Multiplier | Final Count |
|-----------------|--------------|-------------------------|-------------|
| OHR-Bench Clean | 2,000 | 15x DocCreator + 30x Augraphy | 90,000 |
| IIT-CDIP Sample | 1,500 | 10x DocCreator + 20x Augraphy | 45,000 |
| Historical Docs | 500 | 5x DocCreator + 10x Augraphy | 7,500 |
| MOS Datasets | 5,000 | 1x (original labels) | 5,000 |
| **Total** | **9,000** | **~17x average** | **147,500** |

### 6.2 Augmentation Distribution

```python
AUGMENTATION_DISTRIBUTION = {
    # DocCreator (30% of synthetic data) - Physics-based
    "doccreator": {
        "count": 45_000,
        "severity_distribution": {
            "light": 0.3,    # severity [0.1, 0.3]
            "medium": 0.4,   # severity [0.3, 0.6]
            "heavy": 0.3,    # severity [0.6, 0.9]
        },
        "degradation_types": {
            "blur": 0.25,
            "noise": 0.20,
            "ink_degradation": 0.20,
            "bleed_through": 0.15,
            "paper_deformation": 0.20,
        },
    },

    # Augraphy (60% of synthetic data) - Parametric
    "augraphy": {
        "count": 90_000,
        "severity_distribution": {
            "light": 0.35,
            "medium": 0.40,
            "heavy": 0.25,
        },
        "layer_probabilities": {
            "ink_phase": 0.6,
            "paper_phase": 0.5,
            "post_phase": 0.8,
        },
    },

    # MOS Datasets (10% - real labeled data)
    "mos_datasets": {
        "ohr_bench": 10_000,
        "diqa_5000": 5_000,
    },
}
```

### 6.3 Data Generation Pipeline

```python
# scripts/generate_phase7_dataset.py

def generate_phase7_dataset(
    source_images_dir: Path,
    output_dir: Path,
    target_count: int = 150_000,
) -> None:
    """Generate Phase 7 dataset with continuous labels."""

    # Initialize generators
    doccreator = DocCreatorGenerator(output_dir / "doccreator")
    augraphy = AugraphyContinuousLabeler(severity_preset="medium")

    # Load source images
    source_images = list(source_images_dir.glob("*.png"))

    # Calculate augmentation counts per source image
    doccreator_per_image = 45_000 // len(source_images)
    augraphy_per_image = 90_000 // len(source_images)

    all_samples = []

    for source_path in tqdm(source_images, desc="Processing source images"):
        image = cv2.imread(str(source_path))

        # Generate DocCreator augmentations
        for i in range(doccreator_per_image):
            severity = _sample_severity()
            degraded, labels = doccreator.generate(image, severity)

            output_path = output_dir / "images" / f"doccreator_{source_path.stem}_{i}.png"
            label_path = output_dir / "labels" / f"doccreator_{source_path.stem}_{i}.json"

            cv2.imwrite(str(output_path), degraded)
            save_continuous_label(label_path, labels)

            all_samples.append({
                "image_path": str(output_path),
                "label_path": str(label_path),
                "source": "doccreator",
            })

        # Generate Augraphy augmentations
        for i in range(augraphy_per_image):
            augmented, labels = augraphy.augment(image)

            output_path = output_dir / "images" / f"augraphy_{source_path.stem}_{i}.png"
            label_path = output_dir / "labels" / f"augraphy_{source_path.stem}_{i}.json"

            cv2.imwrite(str(output_path), augmented)
            save_continuous_label(label_path, labels)

            all_samples.append({
                "image_path": str(output_path),
                "label_path": str(label_path),
                "source": "augraphy",
            })

    # Create train/val/test splits
    create_splits(all_samples, output_dir, train=0.7, val=0.15, test=0.15)
```

---

## 7. Evaluation Metrics

### 7.1 Regression Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **PLCC** | Pearson correlation | > 0.90 |
| **SRCC** | Spearman rank correlation | > 0.88 |
| **KRCC** | Kendall rank correlation | > 0.75 |
| **MAE** | Mean Absolute Error | < 0.08 |
| **RMSE** | Root Mean Square Error | < 0.12 |

### 7.2 Calibration Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **ECE** | Expected Calibration Error | < 0.05 |
| **MCE** | Maximum Calibration Error | < 0.15 |
| **Reliability Diagram** | Visual calibration plot | Linear |

### 7.3 Per-Issue Performance

```python
def evaluate_continuous_model(
    model: nn.Module,
    test_loader: DataLoader,
) -> dict:
    """Comprehensive evaluation for continuous IQA model."""

    predictions = []
    targets = []

    with torch.no_grad():
        for images, labels in test_loader:
            pred = model(images)
            predictions.append(pred)
            targets.append(labels)

    predictions = torch.cat(predictions)
    targets = torch.cat(targets)

    metrics = {}

    # Overall metrics
    metrics['plcc'] = pearson_correlation(predictions, targets)
    metrics['srcc'] = spearman_correlation(predictions, targets)
    metrics['mae'] = mean_absolute_error(predictions, targets)
    metrics['rmse'] = root_mean_square_error(predictions, targets)

    # Per-issue metrics
    issue_names = ['blur', 'noise', 'skew', 'contrast', 'compression']
    for i, issue in enumerate(issue_names):
        metrics[f'{issue}_plcc'] = pearson_correlation(
            predictions[:, i], targets[:, i]
        )
        metrics[f'{issue}_mae'] = mean_absolute_error(
            predictions[:, i], targets[:, i]
        )

    return metrics
```

---

## 8. Implementation Milestones

### Phase 7.1: Data Infrastructure (Week 1)

- [ ] Implement `DocCreatorLoader` for XML parsing
- [ ] Implement `AugraphyContinuousLabeler` pipeline
- [ ] Create `ContinuousQualityLabel` Pydantic schema
- [ ] Update `IQADataset` to load continuous labels
- [ ] Write unit tests for data loaders

### Phase 7.2: Loss Functions (Week 1-2)

- [ ] Implement `SoftBCELoss`
- [ ] Implement `PLCCLoss`
- [ ] Implement `RankLoss`
- [ ] Implement `GDBCLoss`
- [ ] Implement `ContinuousIQALoss` (hybrid)
- [ ] Write unit tests for loss functions

### Phase 7.3: Dataset Generation (Week 2-3)

- [ ] Install and configure DocCreator
- [ ] Install and configure Augraphy
- [ ] Generate 45k DocCreator images
- [ ] Generate 90k Augraphy images
- [ ] Create train/val/test splits (70/15/15)
- [ ] Validate label distributions

### Phase 7.4: Training Pipeline (Week 3-4)

- [ ] Update `TeacherTrainer` for continuous labels
- [ ] Update training config (loss weights, metrics)
- [ ] Implement continuous evaluation metrics (PLCC, SRCC)
- [ ] Train ResNet-50 teacher on continuous labels
- [ ] Validate performance targets (PLCC > 0.90)

### Phase 7.5: Student Distillation (Week 4-5)

- [ ] Generate soft labels from continuous teacher
- [ ] Update `StudentTrainer` for continuous distillation
- [ ] Train ResNet-18 student
- [ ] Validate student-teacher correlation

### Phase 7.6: MLLM Integration (Optional, Week 5-6)

- [ ] Implement DeQA-Score pseudo-label generator
- [ ] Generate pseudo-labels for unlabeled data
- [ ] Fine-tune with pseudo-labeled data
- [ ] Evaluate MLLM distillation benefit

---

## 9. Configuration

### 9.1 Training Config Update

```yaml
# configs/phase7_continuous_training.yaml

experiment:
  name: "phase7_continuous_resnet50"
  description: "ResNet-50 with continuous IQA labels"
  version: "7.0.0"
  phase: "7"

model:
  architecture: "resnet50"
  pretrained: true
  num_heads: 5
  output_type: "continuous"  # NEW: continuous vs binary

loss:
  type: "continuous_iqa"  # NEW loss type
  lambda_softbce: 0.3
  lambda_plcc: 0.4
  lambda_rank: 0.2
  lambda_gdbc: 0.1
  rank_margin: 0.05
  use_gdbc: true

  head_weights:
    blur: 1.5
    noise: 1.0
    skew: 1.5
    contrast: 1.2
    compression: 0.8

dataset:
  train_path: "/data/phase7_continuous/train"
  label_type: "continuous"  # NEW: continuous vs binary

  # Data sources with weights
  sources:
    doccreator: 0.30
    augraphy: 0.60
    mos: 0.10

evaluation:
  metrics:
    - "plcc"
    - "srcc"
    - "krcc"
    - "mae"
    - "rmse"
    - "ece"  # Calibration

  targets:
    plcc: 0.90
    srcc: 0.88
    mae: 0.08
```

---

## 10. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| DocCreator installation complexity | Provide Docker container with pre-installed tools |
| Augraphy version incompatibility | Pin version in pyproject.toml, test in CI |
| Severity mapping inaccuracies | Validate against human MOS ratings |
| PLCC/SRCC training instability | Use gradient clipping, warmup scheduler |
| GDBC requires variance data | Default to uniform weighting if variance unavailable |
| MLLM cost ($1,500 for 150k images) | Use open-source DeQA-Doc (local GPU) instead of commercial APIs |
| Model calibration issues | Add temperature scaling post-training |
| GPT-4o poor at scoring | Use DeQA-Doc for quality regression, GPT-4o only for distortion detection |

---

## References

### Core Papers
1. DocCreator: A Tool for Creating Synthetic Documents (Kieu et al., 2013)
2. Augraphy: Data Augmentation Library for Document Images (Augraphy, 2023)
3. GDBC: Gated Dual-Bias Calibration for IQA (CVPR 2023)

### Benchmarks (MLLM Model Selection)
4. [Q-Doc: Benchmarking Document Image Quality Assessment Capabilities in MLLMs](https://arxiv.org/html/2511.11410v1) - Document-specific IQA benchmark with coarse/middle/fine evaluation levels
5. [DeQA-Doc: Adapting DeQA-Score to Document Image Quality Assessment](https://arxiv.org/html/2507.12796) - State-of-the-art DIQA using Qwen2.5-VL (Final Score: 0.9235)
6. [Q-Bench: General-Purpose Foundation Models on Low-level Vision](https://q-future.github.io/Q-Bench/) - ICLR 2024 Spotlight, comprehensive IQA benchmark
7. [OmniDocBench: Benchmarking Diverse PDF Document Parsing](https://github.com/opendatalab/OmniDocBench) - CVPR 2025, document parsing quality benchmark

### Datasets
8. DIQA-5000: Document Image Quality Assessment dataset with 5,000 images rated across 3 dimensions
9. OHR-Bench: Document Quality Assessment Benchmark (ICDAR 2021)

### Recommended Models (from benchmark analysis)
10. [DeepSeek-VL2: Mixture-of-Experts Vision-Language Models](https://arxiv.org/html/2412.10302v1) - Most consistent across quality assessment tasks
11. [Qwen2.5-VL](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct) - Best backbone for DeQA-Doc quality regression

---

## Appendix A: OpenRouter Cost Estimation

### A.1 Available Vision Models on OpenRouter

| Model | Input $/M tokens | Output $/M tokens | Context | Notes |
|-------|------------------|-------------------|---------|-------|
| **Qwen2.5-VL-72B-Instruct** | $0.08 | $0.33 | 32K | Best value for quality regression |
| Qwen2.5-VL-3B-Instruct | $0.03 | $0.09 | 131K | Budget option |
| Qwen3-VL-8B-Instruct | $0.064 | $0.40 | 256K | Newer generation |
| GPT-4o-mini | $0.15 | $0.60 | 128K | Good for distortion detection |
| GPT-4o | $2.50 | $10.00 | 128K | Premium (use sparingly) |
| GPT-4.1-nano | $0.10 | $0.40 | 1M | Fast, cheap |

**⚠️ Note:** DeepSeek-VL2 is **NOT available** on OpenRouter as of 2025. Alternative: Use DeepSeek API directly or substitute with Qwen3-VL.

### A.2 Token Estimation per Document Image

| Component | Token Estimate | Notes |
|-----------|---------------|-------|
| Image encoding (high-res) | ~1,000 tokens | 300 DPI document at 1024px |
| Image encoding (low-res) | ~85 tokens | Downsampled preview |
| Prompt template | ~200 tokens | Quality assessment prompt |
| JSON output | ~150 tokens | Continuous labels response |
| **Total per image** | **~1,350 tokens** | High-res analysis |

### A.3 Cost Calculation for 100k Images

**Scenario: Single-model approach using Qwen2.5-VL-72B-Instruct**

```
Images: 100,000
Input tokens/image: 1,200 (image + prompt)
Output tokens/image: 150 (JSON response)

Total input tokens: 100,000 × 1,200 = 120M tokens
Total output tokens: 100,000 × 150 = 15M tokens

Cost breakdown:
  Input:  120M × $0.08/M  = $9.60
  Output: 15M × $0.33/M   = $4.95
  ─────────────────────────────────
  TOTAL: $14.55 for 100k images
```

### A.4 Cost Calculation for 150k Images

**Scenario A: Budget (Qwen2.5-VL-72B only)**
```
Input:  180M × $0.08/M  = $14.40
Output: 22.5M × $0.33/M = $7.43
─────────────────────────────────
TOTAL: $21.83 for 150k images
```

**Scenario B: Hybrid (Qwen for quality + GPT-4o-mini for distortion)**
```
Qwen2.5-VL-72B (150k images):
  Input:  180M × $0.08/M  = $14.40
  Output: 22.5M × $0.33/M = $7.43
  Subtotal: $21.83

GPT-4o-mini (subset: 30k uncertain images):
  Input:  36M × $0.15/M  = $5.40
  Output: 4.5M × $0.60/M = $2.70
  Subtotal: $8.10
─────────────────────────────────
TOTAL: $29.93 for 150k images (hybrid)
```

**Scenario C: Premium (GPT-4o for all)**
```
Input:  180M × $2.50/M  = $450.00
Output: 22.5M × $10.00/M = $225.00
─────────────────────────────────
TOTAL: $675.00 for 150k images (NOT RECOMMENDED)
```

### A.5 Cost Summary

| Dataset Size | Budget (Qwen only) | Hybrid (Qwen + GPT-4o-mini) | Premium (GPT-4o) |
|--------------|--------------------|-----------------------------|------------------|
| 100k images | **$14.55** | $19.95 | $450.00 |
| 150k images | **$21.83** | $29.93 | $675.00 |

### A.6 Recommendations

1. **Primary approach**: Use **Qwen2.5-VL-72B-Instruct** exclusively
   - Best quality/cost ratio based on DeQA-Doc benchmarks
   - Cost: **~$0.00015/image** ($0.15 per 1,000 images)

2. **Validation subset**: Run GPT-4o-mini on 10% of images for distortion detection validation
   - Cost: ~$2.70 additional for 150k dataset

3. **Avoid GPT-4o** for bulk labeling - 30x more expensive than Qwen

4. **Alternative to DeepSeek-VL2**: Since unavailable on OpenRouter, use:
   - Qwen3-VL-8B-Instruct with CoT prompting
   - Or DeepSeek API directly (separate account required)

---

## Appendix B: Modal Self-Hosted Cost Estimation (Recommended)

Running open-source VLMs on Modal provides **significant cost savings** over API-based pricing while offering full control over inference parameters.

### B.1 Recommended Models for Modal Deployment

| Model | Parameters | GPU Required | VRAM | Inference Speed | Best For |
|-------|------------|--------------|------|-----------------|----------|
| **Qwen3-VL-8B-Instruct** | 8B | A10G (24GB) | ~16GB | 0.5-1.0 sec/img | Best quality/speed |
| **Qwen3-VL-8B-Thinking** | 8B | A10G (24GB) | ~16GB | 1.5-2.5 sec/img | Enhanced reasoning |
| Qwen2.5-VL-7B-Instruct | 7B | A10G (24GB) | ~14GB | 0.5-1.0 sec/img | DeQA-Doc compatible |
| Qwen2.5-VL-72B-Instruct | 72B | A100 (80GB) | ~75GB | 2-3 sec/img | Highest accuracy |
| Qwen3-VL-32B-Instruct | 32B | A100 (40GB) | ~35GB | 1.5-2.0 sec/img | Balance accuracy/speed |

### B.2 Modal GPU Pricing (as of Nov 2025)

| GPU | VRAM | Price/Hour | Best For |
|-----|------|------------|----------|
| **A10G** | 24GB | ~$0.60 | 7B-8B models |
| **A100-40GB** | 40GB | ~$1.10 | 32B models |
| **A100-80GB** | 80GB | ~$1.50 | 72B models |
| **H100** | 80GB | ~$3.50 | Maximum throughput |

### B.3 Cost Calculation for 150k Images

**Scenario A: Qwen3-VL-8B on A10G (RECOMMENDED)**
```
Model: Qwen3-VL-8B-Instruct
GPU: A10G (24GB)
Inference time: ~0.8 sec/image (batched)
Total time: 150,000 × 0.8 sec = 120,000 sec = 33.3 hours

Cost breakdown:
  GPU hours: 33.3 hours × $0.60/hr = $20.00
  Storage (temp): ~$1.00
  ─────────────────────────────────
  TOTAL: ~$21 for 150k images
```

**Scenario B: Qwen3-VL-8B-Thinking on A10G (Enhanced Reasoning)**
```
Model: Qwen3-VL-8B-Thinking
GPU: A10G (24GB)
Inference time: ~2.0 sec/image (CoT reasoning)
Total time: 150,000 × 2.0 sec = 300,000 sec = 83.3 hours

Cost breakdown:
  GPU hours: 83.3 hours × $0.60/hr = $50.00
  Storage (temp): ~$2.00
  ─────────────────────────────────
  TOTAL: ~$52 for 150k images
```

**Scenario C: Qwen2.5-VL-72B on A100 (Highest Accuracy)**
```
Model: Qwen2.5-VL-72B-Instruct
GPU: A100-80GB
Inference time: ~2.5 sec/image
Total time: 150,000 × 2.5 sec = 375,000 sec = 104 hours

Cost breakdown:
  GPU hours: 104 hours × $1.50/hr = $156.00
  Storage (temp): ~$4.00
  ─────────────────────────────────
  TOTAL: ~$160 for 150k images
```

### B.4 Cost Comparison: Modal vs OpenRouter

| Dataset | Model | Modal (Self-Hosted) | OpenRouter API | Savings |
|---------|-------|---------------------|----------------|---------|
| **150k images** | Qwen3-VL-8B | **$21** | $20.52 | ~Same |
| **150k images** | Qwen3-VL-8B-Thinking | **$52** | N/A | CoT reasoning |
| **150k images** | Qwen2.5-VL-72B | **$160** | $21.83 | API cheaper |
| **150k images** | GPT-4o equivalent | **$21** | $675 | **97% savings** |

### B.5 Modal Deployment Script

```python
# modal/pseudo_label_generator.py

import modal

app = modal.App("phase7-pseudo-labels")

# Define the image with Qwen3-VL dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.1.0",
        "transformers>=4.40.0",
        "accelerate>=0.27.0",
        "qwen-vl-utils",
        "pillow",
    )
    .run_commands("pip install flash-attn --no-build-isolation")
)

@app.cls(
    gpu=modal.gpu.A10G(),
    image=image,
    timeout=3600,
    container_idle_timeout=300,
)
class QwenVLLabeler:
    @modal.enter()
    def load_model(self):
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        import torch

        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen3-VL-8B-Instruct",
            torch_dtype=torch.bfloat16,
            device_map="auto",
            attn_implementation="flash_attention_2",
        )
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-8B-Instruct")

    @modal.method()
    def generate_labels(self, image_bytes: bytes) -> dict:
        from PIL import Image
        import io
        import json

        image = Image.open(io.BytesIO(image_bytes))

        prompt = """Analyze this document image and rate its quality on a scale of 0.0 to 1.0:
        - blur_severity: How blurry is the text/content?
        - noise_severity: How much visual noise is present?
        - contrast_severity: How poor is the contrast?
        - skew_severity: How misaligned is the content?
        - compression_severity: How visible are compression artifacts?
        - overall_quality: Overall quality (1.0 = best)

        Respond in JSON format only."""

        messages = [
            {"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ]}
        ]

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors="pt").to("cuda")

        output_ids = self.model.generate(**inputs, max_new_tokens=256)
        response = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]

        # Parse JSON from response
        try:
            labels = json.loads(response.split("```json")[-1].split("```")[0].strip())
        except:
            labels = {"error": "Failed to parse", "raw": response}

        return labels


@app.function(image=image, timeout=7200)
def batch_label_images(image_paths: list[str], output_dir: str):
    """Process batch of images and save labels."""
    import json
    from pathlib import Path

    labeler = QwenVLLabeler()

    for image_path in image_paths:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        labels = labeler.generate_labels.remote(image_bytes)

        output_path = Path(output_dir) / f"{Path(image_path).stem}_labels.json"
        with open(output_path, "w") as f:
            json.dump(labels, f, indent=2)


# Run with: modal run modal/pseudo_label_generator.py
```

### B.6 Throughput Optimization

To maximize throughput on Modal:

1. **Batch processing**: Process 4-8 images per GPU call to reduce overhead
2. **Parallel workers**: Spawn multiple containers for parallel processing
3. **Flash Attention 2**: Enable for 2-3x speedup on attention computation
4. **BF16 precision**: Use bfloat16 for optimal speed/quality tradeoff

**Optimized throughput estimates:**

| Configuration | Images/Hour | 150k Duration | Cost |
|---------------|-------------|---------------|------|
| 1x A10G, sequential | 4,500 | 33 hours | $20 |
| 4x A10G, parallel | 18,000 | 8.3 hours | $20 |
| 8x A10G, parallel | 36,000 | 4.2 hours | $20 |
| 1x H100, optimized | 12,000 | 12.5 hours | $44 |

### B.7 Recommendation

**For Phase 7 pseudo-label generation, use Modal with Qwen3-VL-8B-Instruct:**

1. **Best document understanding** - OCRBench 896-905, DocVQA 97%
2. **Cost-effective** - ~$21 for 150k images (similar to API pricing)
3. **Full control** - Custom prompts, batching, no rate limits
4. **Reproducible** - Same model weights, deterministic outputs
5. **Scalable** - Parallelize across multiple GPUs for faster processing

**Alternative**: If highest accuracy is critical, use Qwen2.5-VL-72B with the DeQA-Doc fine-tuned weights (requires downloading from HuggingFace).
