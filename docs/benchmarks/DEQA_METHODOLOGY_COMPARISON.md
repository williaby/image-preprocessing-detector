---
owner: docs-team
purpose: 'Analysis of DeQA-Score vs our benchmarking methodology.'
schema_type: common
status: published
tags:
- benchmarking
- methodology
- deqa-score
- iqa
title: 'DeQA Methodology Comparison'
---

# DeQA-Score vs Our Benchmarking Methodology: A Comprehensive Analysis

This document explains the fundamental differences between the DeQA-Score/DeQA-Doc approach and our current benchmarking infrastructure, clarifying why VLM-based models require different handling.

## Executive Summary

| Aspect | Our CNN Benchmarks | DeQA-Score VLM Approach |
|--------|-------------------|-------------------------|
| **Output Type** | Direct numeric regression | Token probability distribution |
| **Score Extraction** | Model outputs `[batch, 3]` tensor | Parse text OR extract logits for 5 level tokens |
| **Training Target** | Point estimate (MSE loss) | Soft label distribution (KL divergence) |
| **Evaluation** | SRCC/PLCC on predictions | SRCC/PLCC on distribution expectation |
| **Prompt** | None (image → score) | "The quality of this image is \<level\>" |

## 1. How DeQA-Score Actually Works

### 1.1 The Core Innovation: Soft Label Regression

Traditional IQA models output a single quality score. DeQA-Score fundamentally changes this by treating quality as a **probability distribution over discrete levels**.

**The Five Quality Levels:**

```
Level 1: "bad"       → score center c₁ = 1
Level 2: "poor"      → score center c₂ = 2
Level 3: "fair"      → score center c₃ = 3
Level 4: "good"      → score center c₄ = 4
Level 5: "excellent" → score center c₅ = 5
```

**Training Prompt Template:**

```
"The quality of this image is <level>"
```

The model is trained to predict probabilities for each level token, not generate free-form text.

### 1.2 Soft Label Construction

Given a Mean Opinion Score (MOS) μ and variance σ² from human annotations:

1. **Model quality as Gaussian**: x ~ N(μ, σ²)

2. **Compute raw probability for each level** by integrating the Gaussian PDF:

   ```
   pᵢʳᵃʷ = ∫[cᵢ-0.5 to cᵢ+0.5] f(x)dx
   ```

3. **Apply linear transformation** to ensure ∑pᵢ = 1 and recovered mean = μ:

   ```
   pᵢ = α·pᵢʳᵃʷ + β
   ```

4. **For datasets lacking variance** (like DIQA-5000), use pseudo-variance:

   ```
   pseudo_std = 0.2 × (max_score - min_score)
   ```

   For [1,5] range: pseudo_std = 0.8

### 1.3 Training Losses

**KL Divergence Loss** (for \<level\> token):

```
ℒ_kl = Σᵢ pᵢ · log(pᵢ / pᵢᵖʳᵉᵈ)
```

**Fidelity Loss** (for inter-image relationships):

```
ℒ_fd = 1 - √[p(A>B)·pᵖʳᵉᵈ(A>B)] - √[(1-p(A>B))·(1-pᵖʳᵉᵈ(A>B))]
```

where:

```
p(A>B) = Φ((μₐ - μᵦ)/√(σₐ² + σᵦ²))
```

### 1.4 Score Extraction at Inference

**Method 1: Closed-Set Softmax (Training/Proper Evaluation)**

```python
# Extract logits for only the 5 level tokens
level_logits = output_logits[:, [idx_bad, idx_poor, idx_fair, idx_good, idx_excellent]]
probabilities = softmax(level_logits)  # [p₁, p₂, p₃, p₄, p₅]

# Compute expected score
score = sum(pᵢ * cᵢ for i in range(5))  # weighted sum
# score = p₁*1 + p₂*2 + p₃*3 + p₄*4 + p₅*5
```

**Method 2: Text Parsing (Simplified Evaluation)**

```python
# Generate text response
response = model.generate(prompt="Rate the quality: ", image=img)
# response might be "good" or "The quality is excellent"

# Map to score
level_map = {"bad": 1, "poor": 2, "fair": 3, "good": 4, "excellent": 5}
score = level_map.get(parse_response(response), 3.0)  # default to fair
```

## 2. Our Current Benchmarking Approach

### 2.1 CNN-Based Models (ResNet, MANIQA, MUSIQ, etc.)

```python
# Direct numeric regression
class ResNetIQA(nn.Module):
    def forward(self, x):
        features = self.backbone(x)
        scores = self.head(features)  # [batch, 3] for overall/sharpness/color
        return torch.sigmoid(scores) * 4 + 1  # Scale to [1, 5]
```

**Output**: Direct tensor of shape `[batch, 3]` with numeric scores.

### 2.2 VLM Benchmarks (Qwen3-VL, InternVL)

Our current VLM approach uses **text parsing**:

```python
IQA_PROMPT = """Analyze this document image and rate its quality on a scale of 1-5.
Rate:
1. Overall quality: a number from 1.0 to 5.0
2. Sharpness: a number from 1.0 to 5.0
3. Color fidelity: a number from 1.0 to 5.0

Respond with ONLY three lines:
Overall: X.X
Sharpness: X.X
Color: X.X"""

def parse_vlm_response(response: str) -> dict:
    scores = {"overall": None, "sharpness": None, "color": None}
    for line in response.lower().split("\n"):
        for key in scores:
            if key in line:
                match = re.search(r"(\d+\.?\d*)", line)
                if match:
                    value = float(match.group(1))
                    if 1.0 <= value <= 5.0:
                        scores[key] = value
    return scores
```

**Problems with this approach:**

1. **No probability distribution** - loses uncertainty information
2. **Parsing errors** - VLM might output unexpected formats
3. **No soft label training** - model wasn't trained for this task
4. **Prompt mismatch** - different from DeQA-Score's training prompt

## 3. Why DeQA-Doc Models Don't Work with Our Infrastructure

### 3.1 Fundamental Architecture Difference

| Component | Our VLM Benchmark | DeQA-Score |
|-----------|-------------------|------------|
| **Prompt** | Multi-line instructions | Single template: "The quality of this image is \<level\>" |
| **Output** | Free-form text | Single token prediction with logit extraction |
| **Score** | Regex parsing | Closed-set softmax → expectation |
| **Training** | General VLM (not IQA-specific) | Soft label regression with fidelity loss |

### 3.2 The DeQA-Doc Evaluation Methodology

DeQA-Doc was trained and evaluated using:

1. **Soft label targets** constructed from DIQA-5000 MOS scores
2. **KL divergence loss** on the 5-level probability distribution
3. **Score extraction** via closed-set softmax on level tokens
4. **Final score** = E[p] = Σᵢ pᵢ × cᵢ

### 3.3 What Would Be Required to Benchmark DeQA-Doc

To properly benchmark DeQA-Doc models, we would need:

```python
def benchmark_deqa_model(model, tokenizer, image):
    # 1. Use the EXACT training prompt
    prompt = "The quality of this image is"

    # 2. Get model output logits (not generated text)
    inputs = processor(image, prompt, return_tensors="pt")
    outputs = model(**inputs, output_hidden_states=True)
    logits = outputs.logits[:, -1, :]  # Last token logits

    # 3. Extract probabilities for ONLY the 5 level tokens
    level_tokens = tokenizer.encode(["bad", "poor", "fair", "good", "excellent"])
    level_logits = logits[:, level_tokens]
    probabilities = torch.softmax(level_logits, dim=-1)

    # 4. Compute expected score
    centers = torch.tensor([1, 2, 3, 4, 5])
    score = (probabilities * centers).sum()

    return {
        "overall": score.item(),
        "distribution": probabilities.tolist()
    }
```

## 4. DIQA-5000 Dataset Structure

### 4.1 Ground Truth Format

```json
{
    "image_id": "doc_0001.png",
    "mos_overall": 3.47,
    "mos_sharpness": 4.12,
    "mos_color": 3.89,
    "std_overall": null,      // Not provided in DIQA-5000
    "std_sharpness": null,
    "std_color": null,
    "num_annotators": 15
}
```

**Key limitation**: DIQA-5000 provides only MOS, not variance → DeQA-Doc uses pseudo-variance (σ = 0.8).

### 4.2 VQualA 2025 Challenge Protocol

The VQualA 2025 DIQA Challenge evaluated submissions on:

1. **Overall quality SRCC** (weight: 0.50)
2. **Sharpness SRCC** (weight: 0.25)
3. **Color fidelity SRCC** (weight: 0.25)

**Final Score** = 0.5 × SRCC_overall + 0.25 × SRCC_sharpness + 0.25 × SRCC_color

DeQA-Doc's winning ensemble achieved **Final Score = 0.9288**.

## 5. Comparison of Approaches

### 5.1 CNN vs VLM Trade-offs

| Metric | CNN (MANIQA, MUSIQ) | VLM (DeQA-Score) |
|--------|---------------------|------------------|
| **Inference Speed** | 20-80ms | 2000-3000ms |
| **GPU Memory** | 2-8 GB | 16-24 GB |
| **Training Data** | Task-specific IQA datasets | General + IQA fine-tuning |
| **Interpretability** | Limited | Can provide reasoning |
| **Generalization** | Domain-specific | Better zero-shot |

### 5.2 Our Best Results vs DeQA-Doc

| Model | Overall SRCC | Sharpness SRCC | Color SRCC | Final Score |
|-------|--------------|----------------|------------|-------------|
| **MANIQA (our best)** | 0.526 | 0.559 | 0.546 | ~0.54 |
| **DeQA-Doc Ensemble** | ~0.91+ | 0.9275 | 0.9198 | **0.9288** |

The gap is substantial (~0.4 Final Score difference).

## 6. Recommendations

### 6.1 Short-term: Add Proper VLM Evaluation

To benchmark VLM models properly:

1. **Use closed-set softmax** extraction instead of text parsing
2. **Match training prompts** exactly ("The quality of this image is \<level\>")
3. **Extract logits** for the 5 level tokens specifically
4. **Compute expected score** from probability distribution

### 6.2 Medium-term: Implement DeQA-Score Training

To train our own VLM-based IQA model:

1. **Construct soft labels** from MOS using pseudo-variance
2. **Use KL divergence loss** on level token probabilities
3. **Add fidelity loss** for inter-image relationship learning
4. **Fine-tune mPLUG-Owl2 or Qwen2.5-VL** on DIQA-5000

### 6.3 Long-term: Hybrid Approach

Combine CNN speed with VLM accuracy:

1. **Fast CNN** (ResNet-18) for initial screening
2. **VLM oracle** (DeQA-Score) for uncertain cases
3. **Ensemble** CNN + VLM predictions for final score

## References

- [DeQA-Score Paper (CVPR 2025)](https://arxiv.org/abs/2501.11561)
- [DeQA-Doc Paper (ICCVW 2025)](https://arxiv.org/abs/2507.12796)
- [DeQA-Score GitHub](https://github.com/zhiyuanyou/DeQA-Score)
- [DeQA-Doc GitHub](https://github.com/Junjie-Gao19/DeQA-Doc)
- [DeQA-Score Project Page](https://depictqa.github.io/deqa-score/)
- [EmergentMind DIQA Overview](https://www.emergentmind.com/topics/document-image-quality-assessment-diqa)
