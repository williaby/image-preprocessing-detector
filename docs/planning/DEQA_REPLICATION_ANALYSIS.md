---
owner: docs-team
purpose: Comprehensive reference for replicating VQualA 2025 DIQA Champion methodology.
schema_type: common
status: published
tags:
- planning
- iqa
- planning
- research
title: DeQA-Doc Replication Analysis
---

> **Created**: 2025-01-13
> **Purpose**: Comprehensive reference for replicating VQualA 2025 DIQA Champion methodology
> **Source Research**: Gemini deep-dive analysis + direct repository investigation

## Executive Summary

The VQualA 2025 Document Image Quality Assessment (DIQA) Challenge was won by the **DeQA-Doc** team with a final score of **0.9288**. This document captures the complete technical analysis for replicating their approach.

### Key Finding

The winning solution uses a **5-model ensemble** from two different architectures (mPLUG-Owl2 and Qwen2.5-VL), but the specific trained checkpoints (m0, m1, m3, Q0, Q1) are **not publicly released**. Only dimension-specific variants are available on ModelScope.

---

## 1. VQualA 2025 Challenge Scoring

### Final Score Formula

```text
Final Score = 0.5 × SRCC_overall + 0.25 × SRCC_sharpness + 0.25 × SRCC_color
```

Where SRCC = Spearman Rank Correlation Coefficient against ground truth MOS.

### Champion Results

| Configuration | Final Score | Notes |
|--------------|-------------|-------|
| m0 only | 0.9098 | mPLUG-Owl2, full fine-tune |
| m0 + m1 + m3 | 0.9156 | 3 mPLUG variants |
| m0 + m1 + m3 + Q0 | 0.9234 | + Qwen2.5-VL |
| **Full ensemble** | **0.9288** | All 5 models |

---

## 2. Model Architecture Deep Dive

### 2.1 The 5 Models

| Model | Base | Resolution | Training | Score |
|-------|------|------------|----------|-------|
| **m0** | mPLUG-Owl2-7B | 1024×1024 | Full fine-tuning | 0.9098 |
| **m1** | mPLUG-Owl2-7B | 1024×1024 | LoRA fine-tuning | 0.9108 |
| **m3** | mPLUG-Owl2-7B | 1024×1024 | LoRA + KonIQ pretrain | 0.9112 |
| **Q0** | Qwen2.5-VL-7B | Original (NaViT) | Full fine-tuning | 0.9054 |
| **Q1** | Qwen2.5-VL-7B | Original (NaViT) | 5-fold ensemble | 0.9235 |

### 2.2 Why Two Architectures?

**mPLUG-Owl2-7B**:

- CLIP-based visual encoder
- Fixed resolution (requires position embedding interpolation for 1024×1024)
- Excels at semantic "gist" understanding

**Qwen2.5-VL-7B**:

- NaViT (Native Resolution ViT) architecture
- Variable-length sequences, preserves original aspect ratio
- Excels at fine-grained spatial details

The ensemble exploits **architectural diversity** - different architectures make different types of errors, which cancel out when averaged.

### 2.3 Q1 Complexity

Q1 is actually **5 separate models** trained on different data folds:

1. Train on folds 2-5, validate on fold 1
2. Train on folds 1,3-5, validate on fold 2
3. ... etc.

At inference, average all 5 model outputs. This is why Q1 alone (0.9235) nearly matches the full mPLUG ensemble (0.9156).

---

## 3. DeQA-Score Technical Innovation

### 3.1 Soft Label Regression (Critical)

Unlike standard classification, DeQA-Score uses **distributional regression**:

1. **Quality tokens**: bad, poor, fair, good, excellent (mapped to 1-5)
2. **Output**: Probability distribution over these 5 tokens
3. **Training loss**: KL divergence between predicted and target distributions

### 3.2 The Missing Variance Problem

**Problem**: DIQA-5000 only provides MOS (mean opinion score), not variance.

**Solution**: Pseudo-variance injection

```python
# For score range [1, 5]:
sigma_pseudo = 0.2 * (5 - 1) = 0.8
```

### 3.3 Soft Label Construction

Given MOS μ and pseudo-variance σ², compute probability for each quality level:

```python
from scipy.stats import norm

def compute_soft_labels(mos: float, sigma: float = 0.8) -> list[float]:
    """Compute soft label distribution from MOS."""
    levels = [1, 2, 3, 4, 5]  # bad, poor, fair, good, excellent
    probs = []
    for level in levels:
        # Integrate Gaussian over bin [level-0.5, level+0.5]
        p = norm.cdf(level + 0.5, mos, sigma) - norm.cdf(level - 0.5, mos, sigma)
        probs.append(p)
    # Normalize
    total = sum(probs)
    return [p / total for p in probs]

# Example: MOS = 3.7
# Result: [0.001, 0.023, 0.213, 0.528, 0.235]
```

### 3.4 Alternative: Linear Interpolation

For "zero variance" scenarios (Dirac delta):

```python
def linear_interpolation(mos: float) -> list[float]:
    """Sparse soft label using linear interpolation."""
    lower = int(mos)
    upper = lower + 1
    weight_upper = mos - lower
    weight_lower = upper - mos

    probs = [0.0] * 5
    probs[lower - 1] = weight_lower  # -1 for 0-indexing
    probs[upper - 1] = weight_upper
    return probs

# Example: MOS = 3.7
# Result: [0, 0, 0.3, 0.7, 0]
```

---

## 4. Ensemble Aggregation Protocol

### 4.1 Correct Method (Probability Averaging)

**Step 1**: Get probability vectors from each model:

```python
m0_probs = model_m0(image)  # [p_bad, p_poor, p_fair, p_good, p_excellent]
m1_probs = model_m1(image)
# ... etc.
```

**Step 2**: Average probability distributions:

```python
import numpy as np

all_probs = [m0_probs, m1_probs, m3_probs, Q0_probs, Q1_probs]
P_ensemble = np.mean(all_probs, axis=0)
```

**Step 3**: Convert to scalar score:

```python
# Weighted sum: score = Σ p_i × level_i
levels = [1, 2, 3, 4, 5]
final_score = sum(P_ensemble[i] * levels[i] for i in range(5))
```

### 4.2 Why Not Average Scores Directly?

Averaging probabilities preserves **uncertainty information**. Example:

| Model | Probs [bad, poor, fair, good, excellent] | Score |
|-------|------------------------------------------|-------|
| Model A | [0, 0, 0, 1.0, 0] | 4.0 |
| Model B | [0, 0, 1.0, 0, 0] | 3.0 |

- **Score averaging**: (4.0 + 3.0) / 2 = 3.5
- **Probability averaging**: [0, 0, 0.5, 0.5, 0] → score = 3.5

Same result here, but with more complex distributions, probability averaging better captures the ensemble's collective uncertainty.

---

## 5. Resolution Handling

### 5.1 mPLUG-Owl2 (1024×1024)

Standard CLIP uses fixed position embeddings for 224×224 or 448×448. For 1024×1024:

1. **Option A**: Remove absolute position embeddings entirely
2. **Option B**: Bi-linearly interpolate position embeddings

The DeQA-Doc repo implements dynamic interpolation in the visual encoder.

**Config requirement**: `image_size: 1024`

### 5.2 Qwen2.5-VL (Native Resolution)

Uses NaViT architecture:

- Processes images as variable-length sequences
- No padding or resizing
- Preserves original aspect ratio and detail

This is why Qwen excels at documents with varying layouts (receipts, certificates, etc.).

---

## 6. Available Resources

### 6.1 Repositories

| Repository | URL | Contents |
|------------|-----|----------|
| DeQA-Doc (master) | <https://github.com/Junjie-Gao19/DeQA-Doc> | Training scripts, LlamaFactory patches |
| DeQA-Score | <https://github.com/zhiyuanyou/DeQA-Score> | Original mPLUG training code |
| LlamaFactory | <https://github.com/hiyouga/LLaMA-Factory> | Qwen training framework |

### 6.2 Pre-trained Models (Publicly Available)

| Model | Source | Status | Notes |
|-------|--------|--------|-------|
| DeQA-Score-Mix3 | HuggingFace `zhiyuanyou/DeQA-Score-Mix3` | ✅ Working | Overall quality only |
| deqa_0618_overall | ModelScope `zhalala/DeQA-Doc` | ✅ Working | Dimension-specific |
| deqa_0618_sharpness | ModelScope `zhalala/DeQA-Doc` | ✅ Working | Dimension-specific |
| deqa_0618_color | ModelScope `zhalala/DeQA-Doc` | ✅ Working | Dimension-specific |
| deqa_lora_0623_* | ModelScope `zhalala/DeQA-Doc` | ❌ Broken | Config references local paths |
| m0, m1, m3 | Not released | ❌ N/A | Competition checkpoints |
| Q0, Q1 | Not released | ❌ N/A | Competition checkpoints |

### 6.3 Datasets

| Dataset | Images | Access | Use |
|---------|--------|--------|-----|
| DIQA-5000 | 5,000 | VQualA CodaLab | Challenge dataset |
| KonIQ-10k | 10,073 | Public | m3 transfer learning |

---

## 7. Training Requirements

### 7.1 Hardware

| Model | Training Type | Hardware Required |
|-------|--------------|-------------------|
| m0 | Full fine-tune | 8× A100 80GB |
| m1 | LoRA | 2× RTX 3090 24GB |
| m3 | LoRA + transfer | 2× RTX 3090 24GB |
| Q0 | Full fine-tune | 8× A100 80GB |
| Q1 | 5-fold | 5× Q0 training runs |

### 7.2 Training Scripts

**mPLUG-Owl2 (m0, m1, m3)**:

```bash
# m0: Full fine-tuning
scripts/train.sh \
    --model_type mplug_owl2 \
    --image_resolution 1024 \
    --batch_size 8 \
    --learning_rate 2e-5 \
    --epochs 3 \
    --loss_type kl_divergence \
    --use_pseudo_variance True

# m1: LoRA fine-tuning
scripts/train_lora.sh \
    --lora_r 64 \
    --lora_alpha 16 \
    --target_modules q_proj v_proj

# m3: KonIQ pretrain → DIQA fine-tune
scripts/train_lora.sh --data_paths KONIQ  # Stage 1
scripts/train_lora.sh --data_paths DIQA --resume_from_checkpoint  # Stage 2
```

**Qwen2.5-VL (Q0, Q1)**:

Requires LlamaFactory with patched source files:

1. Copy `DeQA-Doc/Llamafactory/src/` over `LLaMA-Factory/src/`
2. Run: `llamafactory-cli train examples/train_full/qwen2.5_vl_diqa_sft.yaml`

### 7.3 Key Training Parameters

- **Learning rate**: 2e-5
- **Epochs**: 3
- **Batch size**: 8 (per GPU)
- **Loss**: KL divergence
- **Pseudo-variance**: σ = 0.8

---

## 8. Cost Estimates (Modal)

### Path A: Inference Only (~$5)

| Task | GPU | Hours | Cost |
|------|-----|-------|------|
| Additional model inference | A100-40GB | 2h | $4.20 |

### Path B: Full Training (~$100-280)

| Model | GPU | Hours | Cost |
|-------|-----|-------|------|
| m0 (full) | A100-80GB | 8h | $20 |
| m1 (LoRA) | A10 | 4h | $4.40 |
| m3 (transfer) | A10 | 8h | $8.80 |
| Q0 (full) | A100-80GB | 8h | $20 |
| Q1 (5-fold) | A100-40GB | 20h | $42 |
| **Total** | | | **~$95** |

---

## 9. Current Implementation Status

### 9.1 Completed Label Runs

| File | Mode | Models | Images |
|------|------|--------|--------|
| `diqa-5000_specialist_labels.jsonl` | specialist | Mix3 (prompts) | 5,000 |
| `diqa-5000_ensemble_labels.jsonl` | ensemble | Mix3 | 5,000 |
| `diqa-5000_vl_labels.jsonl` | vl | Mix3 | 5,000 |
| `diqa-5000_specialist_true_labels.jsonl` | specialist_true | 3 ModelScope | 5,000 |
| `diqa-5000_ensemble_true_labels.jsonl` | ensemble_true | 3 ModelScope | 5,000 |

### 9.2 Comparison Results (Mix3 vs True Specialists)

| Dimension | SRCC | MAE |
|-----------|------|-----|
| Overall | 0.5523 | 0.3492 |
| Sharpness | 0.4771 | 0.3837 |
| Color | 0.5019 | 0.4391 |

Moderate correlation confirms these are genuinely different models.

### 9.3 Key Finding

`specialist_true` and `ensemble_true` produce **identical results** (SRCC = 1.0) because:

- Both use the same 3 dimension-specific models
- Each model only outputs one dimension
- No actual "ensemble" diversity exists

---

## 10. Recommendations

### Immediate Actions (Path A)

1. Check `zhalala/DeQA-Doc-Mix` on ModelScope for additional models
2. Create ensemble combining:
   - 3 dimension-specific models (already have)
   - Mix3 baseline model
   - Any additional variants found
3. Benchmark against DIQA-5000 ground truth

### Future Work (Path B)

If Path A doesn't achieve acceptable performance:

1. Train m0 and m1 using DeQA-Score codebase
2. Train Q0 using LlamaFactory patches
3. Optionally train m3 (KonIQ transfer) and Q1 (5-fold)

### Expected Performance

| Approach | Expected Score | Cost |
|----------|----------------|------|
| Current (3 specialists) | Unknown | $0 (done) |
| Path A (expanded ensemble) | ~0.90-0.92 | ~$5 |
| Path B (full replica) | ~0.9288 | ~$100 |

---

## 11. References

- [DeQA-Doc Paper](https://arxiv.org/abs/2507.12796)
- [DeQA-Doc GitHub](https://github.com/Junjie-Gao19/DeQA-Doc)
- [DeQA-Score GitHub](https://github.com/zhiyuanyou/DeQA-Score)
- [VQualA 2025 Challenge](https://research.github.io/)
- [VQualA 2025 CodaLab](https://codalab.lisn.upsaclay.fr/competitions/23020)
- [LlamaFactory](https://github.com/hiyouga/LLaMA-Factory)
- [KonIQ-10k Dataset](http://database.mmsp-kn.de/koniq-10k-database.html)
- [mPLUG-Owl2 HuggingFace](https://huggingface.co/MAGAer13/mplug-owl2-llama2-7b)
- [Qwen2.5-VL HuggingFace](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)

---

## Appendix A: DIQA-5000 Dataset Structure

```text
DIQA-5000/
├── images/
│   ├── train/
│   │   ├── doc_001_aug_0.jpg
│   │   └── ...
│   └── test/
└── metas/
    ├── train.json  # {"img_path": "...", "mos": 3.4}
    └── test.json
```

## Appendix B: Model Output Format

```json
{
  "image": "test/doc_001.jpg",
  "dataset": "diqa-5000",
  "mode": "ensemble_true",
  "scores": {
    "overall": 3.45,
    "sharpness": 3.82,
    "color": 3.61
  },
  "per_model_scores": {
    "overall": {"full": 3.45},
    "sharpness": {"full": 3.82},
    "color": {"full": 3.61}
  },
  "probs": {
    "overall": {
      "bad": 0.01,
      "poor": 0.05,
      "fair": 0.20,
      "good": 0.50,
      "excellent": 0.24
    }
  },
  "timestamp": "2025-01-13T12:00:00Z"
}
```
