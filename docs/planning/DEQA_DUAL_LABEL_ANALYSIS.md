---
owner: docs-team
purpose: Implementation plan for DIQA-5000 dual label generation using DeQA-Doc models.
schema_type: common
status: published
tags:
- planning
- iqa
- planning
- diqa_5000
- pseudo_labeling
title: 'DeQA-Doc Dual Label Analysis: Specialist vs Ensemble'
---

> **STATUS**: ✅ IMPLEMENTATION COMPLETE (2025-01-13)
>
> The multi-mode labeling infrastructure has been implemented at
> `src/image_preprocessing_detector/labeling/deqa/` (core module) and
> `modal/deqa_labeling.py` (Modal deployment).
> See [Usage](#usage) for running label generation.

## Executive Summary

This document outlines the implementation plan to generate two sets of pseudo-labels for the DIQA-5000 dataset:

1. **Specialist labels**: Using 3 dimension-specific CNN models (one per quality dimension)
2. **Ensemble labels**: Using the complete VQualA 2025 champion ensemble (m0 + m1 + m3 + Q0 + Q1)
3. **VL labels**: Using a single configurable VL model (fastest, most flexible)

The goal is to evaluate score differences between approaches and determine which provides better pseudo-labels for training our downstream IQA models.

## Usage

### Running Label Generation

```bash
# Generate specialist labels (3 dimension-specific models)
modal run modal/deqa_labeling.py --dataset diqa-5000 --mode specialist

# Generate ensemble labels (5 VLM models - VQualA 2025 champion)
modal run --detach modal/deqa_labeling.py --dataset diqa-5000 --mode ensemble

# Generate VL labels (single model, fastest)
modal run modal/deqa_labeling.py --dataset diqa-5000 --mode vl

# Test with 100 samples first
modal run modal/deqa_labeling.py --dataset diqa-5000 --mode specialist --test

# Process all datasets
modal run --detach modal/deqa_labeling.py --dataset all --mode specialist
```

### Python API

```python
from image_preprocessing_detector.labeling.deqa import (
    DeQAConfig,
    InferenceMode,
    create_inference_engine,
    generate_comparison_report,
    load_labels,
)

# Create specialist config
config = DeQAConfig(mode=InferenceMode.SPECIALIST)
engine = create_inference_engine(config)
engine.load_models()

# Predict on image
from PIL import Image
image = Image.open("document.png")
scores = engine.predict(image)
# scores = {"overall": DeQAScore(...), "sharpness": DeQAScore(...), "color": DeQAScore(...)}

# Compare label sets
specialist_labels = load_labels("diqa-5000_specialist_labels.jsonl")
ensemble_labels = load_labels("diqa-5000_ensemble_labels.jsonl")
report = generate_comparison_report(specialist_labels, ensemble_labels)
```

## Background

### DeQA-Doc Model Architecture

From the [DeQA-Doc paper](https://arxiv.org/abs/2507.12796) and [GitHub repository](https://github.com/Junjie-Gao19/DeQA-Doc), the VQualA 2025 champion ensemble consists of:

#### CNN Models (3 models - mPLUG-Owl2 based)

| Model | Base | Training | Resolution | Pretrain | Final Score |
|-------|------|----------|------------|----------|-------------|
| **m0** | mPLUG-Owl2-7B | Full tuning | 1024×1024 | None | 0.8989 |
| **m1** | mPLUG-Owl2-7B | LoRA | 1024×1024 | None | 0.9033 |
| **m3** | mPLUG-Owl2-7B | LoRA | 1024×1024 | KonIQ-10k | TBD |

#### VLM Models (2 models - Qwen2.5-VL based)

| Model | Base | Training | Resolution | Notes |
|-------|------|----------|------------|-------|
| **Q0** | Qwen2.5-VL-7B | Full tuning | Dynamic | Primary Qwen model |
| **Q1** | Qwen2.5-VL-7B | Full tuning (5-fold) | Dynamic | 5-fold CV ensemble |

### Performance Comparison

| Configuration | Final Score | Notes |
|--------------|-------------|-------|
| m3 only | ~0.85-0.90 (est.) | Single model with KonIQ pretraining |
| Full ensemble (m0+m1+m3+Q0+Q1) | **0.9288** | VQualA 2025 Champion |

The full ensemble achieves:

- Overall SRCC: ~0.91+
- Sharpness SRCC: 0.9275
- Color SRCC: 0.9198

## Implementation Plan

### Phase 1: Model Setup & Validation

#### 1.1 Model Download and Configuration

**m3 Model (KonIQ-pretrained mPLUG-Owl2)**:

```python
# ModelScope: zhalala/DeQA-Doc (DIQA_model variant)
# HuggingFace base: MAGAer13/mplug-owl2-llama2-7b
# Requires LoRA adapter from DeQA-Doc training

MODEL_CONFIG_M3 = {
    "model_id": "deqa_m3_mplug_owl2",
    "base_model": "MAGAer13/mplug-owl2-llama2-7b",
    "model_path": "zhalala/DeQA-Doc",
    "model_type": "mplug_owl2",
    "training_method": "lora",
    "pretrain": "koniq-10k",
    "resolution": 1024,
    "dimensions": ["overall", "sharpness", "color"],
}
```

**Full Ensemble Configuration**:

```python
ENSEMBLE_CONFIG = {
    "models": {
        "m0": {
            "base_model": "MAGAer13/mplug-owl2-llama2-7b",
            "model_path": "zhalala/DeQA-Doc",
            "training_method": "full",
            "resolution": 1024,
        },
        "m1": {
            "base_model": "MAGAer13/mplug-owl2-llama2-7b",
            "model_path": "zhalala/DeQA-Doc",
            "training_method": "lora",
            "resolution": 1024,
        },
        "m3": {
            "base_model": "MAGAer13/mplug-owl2-llama2-7b",
            "model_path": "zhalala/DeQA-Doc",
            "training_method": "lora",
            "pretrain": "koniq-10k",
            "resolution": 1024,
        },
        "Q0": {
            "base_model": "Qwen/Qwen2.5-VL-7B-Instruct",
            "model_path": "zhalala/DeQA-Doc",
            "training_method": "full",
            "resolution": "dynamic",
        },
        "Q1": {
            "base_model": "Qwen/Qwen2.5-VL-7B-Instruct",
            "model_path": "zhalala/DeQA-Doc",
            "training_method": "full_5fold",
            "resolution": "dynamic",
        },
    },
    "aggregation": "weighted_mean",  # How ensemble predictions combine
}
```

#### 1.2 Validation Against Paper Results

Before generating labels, validate our inference matches paper-reported results:

| Model | Expected Final Score | Tolerance |
|-------|---------------------|-----------|
| m3 only | ~0.85-0.90 | ±0.02 |
| Full ensemble | 0.9288 | ±0.01 |

### Phase 2: Inference Pipeline Implementation

#### 2.1 Directory Structure

```text
src/image_preprocessing_detector/labeling/
├── deqa/
│   ├── __init__.py
│   ├── config.py              # Model configurations
│   ├── inference.py           # Core inference logic
│   ├── m3_inference.py        # m3-only pipeline
│   ├── ensemble_inference.py  # Full ensemble pipeline
│   ├── score_extraction.py    # Score parsing from VLM outputs
│   └── aggregation.py         # Ensemble aggregation strategies
├── modal/
│   └── deqa_labeling.py       # Modal deployment
└── outputs/
    └── diqa5000/
        ├── m3_only_labels.csv
        ├── full_ensemble_labels.csv
        └── comparison_analysis.csv
```

#### 2.2 Core Inference Interface

```python
# src/image_preprocessing_detector/labeling/deqa/inference.py

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch
from PIL import Image


@dataclass
class DeQAScore:
    """Quality score output from DeQA-Doc model."""

    overall: float
    sharpness: float
    color: float
    model_id: str
    confidence: dict[str, float] | None = None


@dataclass
class DeQAConfig:
    """Configuration for DeQA-Doc inference."""

    model_variant: Literal["m3_only", "full_ensemble"]
    resolution: int = 1024
    device: str = "cuda"
    precision: Literal["fp16", "bf16", "fp32"] = "bf16"
    batch_size: int = 1


class DeQAInference:
    """Base class for DeQA-Doc inference."""

    def __init__(self, config: DeQAConfig):
        self.config = config
        self.models = {}
        self._load_models()

    def _load_models(self) -> None:
        """Load model(s) based on configuration."""
        raise NotImplementedError

    def predict(self, image: Image.Image) -> DeQAScore:
        """Generate quality scores for an image."""
        raise NotImplementedError

    def predict_batch(self, images: list[Image.Image]) -> list[DeQAScore]:
        """Generate quality scores for a batch of images."""
        raise NotImplementedError
```

#### 2.3 m3-Only Inference

```python
# src/image_preprocessing_detector/labeling/deqa/m3_inference.py

class M3OnlyInference(DeQAInference):
    """Inference using only the m3 model (KonIQ-pretrained mPLUG-Owl2 with LoRA)."""

    def _load_models(self) -> None:
        """Load m3 model with KonIQ pretraining."""
        from modelscope import AutoModel

        # Load m3 model from ModelScope
        self.model = AutoModel.from_pretrained(
            "zhalala/DeQA-Doc",
            trust_remote_code=True,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )
        self.model.eval()

    def predict(self, image: Image.Image) -> DeQAScore:
        """Generate scores using m3 model only."""
        # Resize to 1024x1024
        image = image.resize((self.config.resolution, self.config.resolution))

        # Get scores for each dimension
        scores = self._run_inference(image)

        return DeQAScore(
            overall=scores["overall"],
            sharpness=scores["sharpness"],
            color=scores["color"],
            model_id="m3_only",
        )
```

#### 2.4 Full Ensemble Inference

```python
# src/image_preprocessing_detector/labeling/deqa/ensemble_inference.py

class FullEnsembleInference(DeQAInference):
    """Inference using full DeQA-Doc ensemble (m0 + m1 + m3 + Q0 + Q1)."""

    def _load_models(self) -> None:
        """Load all 5 models."""
        # Load mPLUG-Owl2 variants (m0, m1, m3)
        self.mplug_models = self._load_mplug_variants()

        # Load Qwen2.5-VL variants (Q0, Q1)
        self.qwen_models = self._load_qwen_variants()

    def predict(self, image: Image.Image) -> DeQAScore:
        """Generate scores using full ensemble."""
        # Get predictions from all models
        all_scores = []

        # mPLUG-Owl2 models (fixed 1024x1024 resolution)
        image_1024 = image.resize((1024, 1024))
        for model_id, model in self.mplug_models.items():
            scores = self._run_mplug_inference(model, image_1024)
            all_scores.append((model_id, scores))

        # Qwen2.5-VL models (dynamic resolution)
        for model_id, model in self.qwen_models.items():
            scores = self._run_qwen_inference(model, image)  # Original resolution
            all_scores.append((model_id, scores))

        # Aggregate ensemble predictions
        aggregated = self._aggregate_scores(all_scores)

        return DeQAScore(
            overall=aggregated["overall"],
            sharpness=aggregated["sharpness"],
            color=aggregated["color"],
            model_id="full_ensemble",
            confidence=aggregated.get("confidence"),
        )

    def _aggregate_scores(
        self,
        scores: list[tuple[str, dict[str, float]]],
    ) -> dict[str, float]:
        """Aggregate scores from multiple models.

        Default: Simple mean across all models.
        TODO: Investigate if DeQA-Doc uses weighted aggregation.
        """
        aggregated = {"overall": 0, "sharpness": 0, "color": 0}
        n_models = len(scores)

        for _, model_scores in scores:
            for dim in aggregated:
                aggregated[dim] += model_scores[dim]

        for dim in aggregated:
            aggregated[dim] /= n_models

        return aggregated
```

### Phase 3: Label Generation

#### 3.1 DIQA-5000 Dataset Processing

```python
# Generate labels for all splits
SPLITS = ["train", "val", "test"]

for split in SPLITS:
    dataset = DIQA5000Dataset(root_dir=DIQA_ROOT, split=split)

    # Generate m3-only labels
    m3_labels = generate_labels(dataset, variant="m3_only")
    save_labels(m3_labels, f"outputs/diqa5000/m3_only_{split}.csv")

    # Generate full ensemble labels
    ensemble_labels = generate_labels(dataset, variant="full_ensemble")
    save_labels(ensemble_labels, f"outputs/diqa5000/full_ensemble_{split}.csv")
```

#### 3.2 Output Format

```csv
# m3_only_labels.csv
image_id,overall_m3,sharpness_m3,color_m3,overall_gt,sharpness_gt,color_gt
test_res_00001,3.82,3.91,3.75,3.76,3.65,3.71
test_res_00002,4.15,4.22,4.08,4.10,4.18,4.05
...

# full_ensemble_labels.csv
image_id,overall_ens,sharpness_ens,color_ens,overall_gt,sharpness_gt,color_gt,m0_overall,m1_overall,m3_overall,Q0_overall,Q1_overall,...
test_res_00001,3.85,3.88,3.79,3.76,3.65,3.71,3.80,3.82,3.84,3.90,3.88,...
...
```

### Phase 4: Comparison Analysis

#### 4.1 Metrics to Compute

For each label set (m3-only vs full ensemble):

| Metric | Description |
|--------|-------------|
| **SRCC** | Spearman Rank Correlation Coefficient vs ground truth |
| **PLCC** | Pearson Linear Correlation Coefficient vs ground truth |
| **RMSE** | Root Mean Square Error vs ground truth |
| **MAE** | Mean Absolute Error vs ground truth |
| **ECE** | Expected Calibration Error (if uncertainty available) |
| **Label Stability** | Variance across predictions |

#### 4.2 Analysis Framework

```python
# src/image_preprocessing_detector/labeling/deqa/analysis.py

@dataclass
class LabelComparisonResult:
    """Results comparing two label sets."""

    dimension: str
    m3_srcc: float
    m3_plcc: float
    m3_rmse: float
    ensemble_srcc: float
    ensemble_plcc: float
    ensemble_rmse: float
    delta_srcc: float
    delta_plcc: float
    delta_rmse: float

    # Score distribution statistics
    m3_mean: float
    m3_std: float
    ensemble_mean: float
    ensemble_std: float

    # Score differences between methods
    mean_diff: float
    max_diff: float
    diff_std: float


def compare_label_sets(
    m3_labels: pd.DataFrame,
    ensemble_labels: pd.DataFrame,
    ground_truth: pd.DataFrame,
) -> dict[str, LabelComparisonResult]:
    """Compare m3-only vs full ensemble labels."""
    results = {}

    for dimension in ["overall", "sharpness", "color"]:
        # Compute correlations with ground truth
        m3_srcc = spearmanr(m3_labels[dimension], ground_truth[dimension])[0]
        ens_srcc = spearmanr(ensemble_labels[dimension], ground_truth[dimension])[0]

        # Compute differences between label sets
        diff = m3_labels[dimension] - ensemble_labels[dimension]

        results[dimension] = LabelComparisonResult(
            dimension=dimension,
            m3_srcc=m3_srcc,
            ensemble_srcc=ens_srcc,
            delta_srcc=ens_srcc - m3_srcc,
            # ... other metrics
        )

    return results
```

### Phase 5: Recommendations

#### 5.1 Decision Criteria

| Scenario | Recommendation |
|----------|----------------|
| Full ensemble SRCC significantly better (>0.02) | Use full ensemble for production |
| m3-only SRCC within 0.02 of ensemble | Use m3-only (simpler, faster) |
| High variance between models in ensemble | Investigate individual model quality |
| Systematic bias in one method | Document and correct in downstream training |

#### 5.2 Downstream Impact Assessment

Evaluate how label choice affects:

1. **Student model training** - Will m3-only labels produce similar student model quality?
2. **Inference latency** - m3-only is ~5x faster than full ensemble
3. **Compute cost** - m3-only requires ~1/5 the GPU resources
4. **Label stability** - Does ensemble reduce per-image variance?

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Setup | 1-2 days | Model loading validated |
| Phase 2: Pipeline | 2-3 days | Inference code complete |
| Phase 3: Generation | 1-2 days | Both label sets generated |
| Phase 4: Analysis | 1 day | Comparison report |
| Phase 5: Recommendations | 0.5 days | Final decision documented |

**Total estimated time**: 5-8 days

## Compute Requirements

### m3-Only Pipeline

- **GPU**: A100 80GB or 2x A10G 24GB
- **Time**: ~2-3s per image
- **Total for DIQA-5000**: ~4-6 hours

### Full Ensemble Pipeline

- **GPU**: 2x A100 80GB (parallel) or sequential on 1x A100
- **Time**: ~10-15s per image (all 5 models)
- **Total for DIQA-5000**: ~15-20 hours

## Files to Create

| File | Purpose |
|------|---------|
| `src/image_preprocessing_detector/labeling/deqa/__init__.py` | Package init |
| `src/image_preprocessing_detector/labeling/deqa/config.py` | Model configurations |
| `src/image_preprocessing_detector/labeling/deqa/inference.py` | Base inference class |
| `src/image_preprocessing_detector/labeling/deqa/m3_inference.py` | m3-only pipeline |
| `src/image_preprocessing_detector/labeling/deqa/ensemble_inference.py` | Full ensemble pipeline |
| `src/image_preprocessing_detector/labeling/deqa/analysis.py` | Comparison analysis |
| `modal/deqa_labeling.py` | Modal deployment |
| `scripts/generate_deqa_labels.py` | Label generation script |
| `tests/unit/labeling/deqa/test_inference.py` | Unit tests |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Model weights not publicly available | Contact authors, use ModelScope DIQA_model |
| Inference doesn't match paper results | Validate on paper's reported subset first |
| Full ensemble too expensive | Implement caching, batch processing |
| Q1 5-fold ensemble unclear | Start with Q0 only, add Q1 if weights available |

## References

- [DeQA-Doc Paper (arxiv:2507.12796)](https://arxiv.org/abs/2507.12796)
- [DeQA-Doc GitHub](https://github.com/Junjie-Gao19/DeQA-Doc)
- [DeQA-Score Paper (arxiv:2501.11561)](https://arxiv.org/abs/2501.11561)
- [ModelScope DIQA_model](https://modelscope.cn/models/zhalala/DeQA-Doc)
- [VQualA 2025 Challenge](https://research.github.io/)

---

*Document Version 1.0 - January 2025*
