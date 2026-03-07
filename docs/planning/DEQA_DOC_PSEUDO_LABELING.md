# DeQA-Doc Pseudo-Labeling Pipeline

> **Status**: Pipeline implemented | **Date**: 2026-03-06
> **Branch**: `feat/ood-cross-model-agreement`

## Overview

Uses [DeQA-Doc](https://github.com/Junjie-Gao19/DeQA-Doc) (VQualA 2025 DIQA Challenge Champion) to generate pseudo-labels for the unified training corpus across 3 DIQA dimensions: **overall quality**, **sharpness**, and **color fidelity**. Labels are gated through a Mahalanobis distance-based OOD detector to assign reliability-weighted sample weights for SigLIP 2 multi-task training.

## Why This Approach

**Problem**: No large-scale human-labeled document IQA dataset exists beyond DIQA-5000 (3.5K train). Classical IQA detectors (blur, noise, contrast) produce measurements that don't align with perceptual quality scores. The IQA Phase 7 165K dataset was flawed and excluded.

**Solution**: DeQA-Doc's per-dimension mPLUG-Owl2-7B models were trained on DIQA-5000 with a specialized DeQA loss (KL divergence + ranking). They produce high-quality soft probability distributions that match human MOS ratings. The OOD detector flags images far from DIQA-5000's distribution so their pseudo-labels receive lower training weight.

## Architecture

```
Unified Training Corpus
    |
    v
[DeQA-Doc Inference] ---- Per-dimension mPLUG-Owl2-7B (subprocess isolation)
    |                      3 models: overall, sharpness, color_fidelity
    |                      Output: soft probs [excellent,good,fair,poor,bad] + MOS
    v
[OOD Gating] ------------ Mahalanobis distance in SigLIP2 embedding space
    |                      AUROC 0.9963 (DIQA-5000 test vs synthetic OOD)
    |                      Thresholds: p75/p90/p97.5 calibrated on DIQA-5000
    v
[Gated Labels] ---------- Per-image sample weight (0.0 - 1.0)
    |                      DIQA-5000 GT always weight=1.0
    v
[SigLIP 2 Training] ----- Weighted loss: raw_loss * sample_weight per IQA head
```

## Acceptance Tiers

| Tier | Mahalanobis Percentile | Sample Weight | Description |
|------|----------------------|---------------|-------------|
| GROUND_TRUTH | N/A | 1.0 | DIQA-5000 images with human MOS labels |
| AUTO_ACCEPT | < p75 | 1.0 | Close to DIQA-5000 distribution |
| LOW_WEIGHT | p75 - p90 | 0.5 | Moderate OOD, reduced confidence |
| TIER2_TRIGGER | p90 - p97.5 | 0.3 | High OOD, optional VLM cross-validation |
| HARD_REJECT | > p97.5 | 0.0 | Extreme OOD, excluded from training |

## DeQA-Doc Model Provenance

- **Models**: Per-dimension fine-tunes of mPLUG-Owl2-7B on DIQA-5000
- **Source**: [ModelScope zhalala/DeQA-Doc](https://www.modelscope.cn/models/zhalala/DeQA-Doc/summary)
- **Training**: DeQA loss (CE + SoftKL + In-level + Ranking)
- **Quality levels**: excellent (5), good (4), fair (3), poor (2), bad (1)
- **Dimension prompts**:
  - overall: "The overall_quality of the image is"
  - sharpness: "The sharpness of the image is"
  - color_fidelity: "The color_fidelity of the image is"

## Subprocess Isolation

DeQA-Doc requires `transformers==4.36.1` and `torch==2.0.1`, incompatible with this project's `transformers>=4.40.0`. The bridge script runs inside the DeQA-Doc venv via subprocess:

```
image_detection process                 DeQA-Doc venv subprocess
    |                                        |
    |-- stdin: JSONL image paths ---------> |
    |                                        |-- load mPLUG-Owl2
    |                                        |-- batch inference
    |<-- stdout: JSONL predictions ---------|
```

## Pipeline Scripts

### Step 1: Generate pseudo-labels

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python scripts/generate_diqa_pseudo_labels.py \
        --manifest /path/to/training_manifest.jsonl \
        --deqa-venv /home/byron/dev/DeQA-Doc/DeQA-Score/.venv \
        --deqa-root /home/byron/dev/DeQA-Doc/DeQA-Score \
        --model-dir /path/to/deqa_models \
        --output /path/to/diqa_pseudo_labels.jsonl \
        --device cuda:0
```

### Step 2: Gate with OOD detector

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python scripts/gate_diqa_pseudo_labels.py \
        --pseudo-labels /path/to/diqa_pseudo_labels.jsonl \
        --embeddings /path/to/corpus_embeddings.npy \
        --embedding-ids /path/to/corpus_ids.json \
        --ood-params /mnt/e/image_detection/embeddings/ood_params_4400.npz \
        --output /path/to/gated_diqa_labels.jsonl \
        --diqa-gt /path/to/diqa5000_train.json
```

### Step 3: Place in training data directory

Copy `gated_diqa_labels.jsonl` to the Modal volume at `data/gated_diqa_labels.jsonl`. The training script auto-detects this file and merges pseudo-labels into the manifest.

## DQS Integration

The DQS calculator (`metrics/dqs_calculator.py`) now blends all 3 SigLIP 2 IQA dimensions:

```python
ml_quality = (
    config.ml_overall_weight * overall     # 0.60
    + config.ml_sharpness_weight * sharpness  # 0.25
    + config.ml_color_weight * color_fidelity  # 0.15
)
degradation_score = (1 - blend_ratio) * classical + blend_ratio * ml_quality
```

Falls back to `overall` only when sharpness/color are unavailable (backward compatible).

## Future Phase F: Individual Degradation Heads

Deferred until proper label sources exist:

| Head | Label Source Strategy | Prerequisite |
|------|---------------------|-------------|
| blur | Paired: sharp original + synthetic blur at known sigma | Calibrated blur severity scale |
| noise | Paired: clean original + synthetic noise types | Noise injection pipeline |
| contrast | Paired: calibrated original + synthetic contrast reduction | Contrast measurement standard |
| compression | Known JPEG QF applied to originals, target = QF/100 | QF extraction pipeline |

**Why deferred**: Synthetic degradation labels don't capture real-world document degradation distributions. The 3-dim DIQA scheme captures routing-relevant quality signal. Classical IQA detectors provide granular per-issue detection at runtime.

## Key Files

| File | Purpose |
|------|---------|
| `src/.../labeling/deqa/bridge_script.py` | Standalone script running in DeQA-Doc venv |
| `src/.../labeling/deqa/subprocess_runner.py` | Subprocess isolation orchestrator |
| `scripts/generate_diqa_pseudo_labels.py` | Batch pseudo-labeling pipeline |
| `scripts/gate_diqa_pseudo_labels.py` | OOD-gated label acceptance |
| `src/.../detection/ood_detector.py` | Mahalanobis OOD detector (reused) |
| `src/.../metrics/dqs_calculator.py` | DQS with 3-dim ML blend |
| `modal/train_siglip2_multitask.py` | Training with weighted IQA labels |
