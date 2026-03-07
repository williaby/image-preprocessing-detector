# DeQA-Doc Integration Handoff

> **Date**: 2026-03-07
> **Project**: Prepare-Doc (image_detection)
> **Upstream**: [Junjie-Gao19/DeQA-Doc](https://github.com/Junjie-Gao19/DeQA-Doc)
> **Branch**: `feat/ood-cross-model-agreement`

## Summary

We integrated DeQA-Doc's per-dimension mPLUG-Owl2-7B models as a **pseudo-labeling oracle** for our SigLIP 2 multi-task training pipeline. The models are not modified — they run unaltered in a subprocess-isolated environment. All changes are on our side: a bridge protocol, OOD-gated acceptance, and training integration.

This document describes every adaptation we made and why.

---

## 1. What We Use From DeQA-Doc

| Component | Source | How We Use It |
|-----------|--------|---------------|
| Per-dimension mPLUG-Owl2-7B checkpoints | [ModelScope zhalala/DeQA-Doc](https://www.modelscope.cn/models/zhalala/DeQA-Doc/summary) | Unmodified inference for pseudo-label generation |
| `src/model/builder.py` → `load_pretrained_model()` | DeQA-Score repo | Called by our bridge script to load models |
| `src/mm_utils.py` → `get_model_name_from_path()`, `tokenizer_image_token()` | DeQA-Score repo | Tokenization and input construction |
| `src/constants.py` → `DEFAULT_IMAGE_TOKEN`, `IMAGE_TOKEN_INDEX` | DeQA-Score repo | Token constants for prompt building |
| `src/conversation.py` → `conv_templates["mplug_owl2"]` | DeQA-Score repo | Conversation template for prompt formatting |
| Dimension prompts | DeQA-Doc training config | `"The overall_quality of the image is"`, `"The sharpness of the image is"`, `"The color_fidelity of the image is"` |
| Quality level names + MOS mapping | DeQA-Doc training | `[excellent=5, good=4, fair=3, poor=2, bad=1]` |

**We do NOT modify any DeQA-Doc source code or model weights.**

---

## 2. Why Subprocess Isolation

DeQA-Doc requires `transformers==4.36.1` and `torch==2.0.1`. Our project uses `transformers>=4.40.0` and `torch>=2.1`. These are incompatible at the Python import level.

**Solution**: The DeQA-Doc models run inside their own venv via subprocess. Communication uses a JSONL protocol over stdin/stdout:

```text
image_detection process                 DeQA-Doc venv subprocess
    |                                        |
    |-- stdin: {"image_path": "/abs/..."}    |
    |          (one per line)           ---> |-- loads mPLUG-Owl2 model
    |                                        |-- batch inference
    |<-- stdout: {"image_path": "...",  <--- |
    |      "dimension": "overall",           |
    |      "level_probs": [0.05,...],         |
    |      "expected_mos": 3.42,             |
    |      "score_normalized": 0.605,        |
    |      "status": "ok"}                   |
    |                                        |
    |<-- stdout: {"status":"done",      <--- |
    |      "processed": N, "errors": M}      |
```

---

## 3. Files We Created

### Core Integration (`src/image_preprocessing_detector/labeling/deqa/`)

| File | Purpose | Lines |
|------|---------|-------|
| `__init__.py` | Package docstring explaining subprocess isolation rationale | 14 |
| `bridge_script.py` | **Standalone** script that runs inside the DeQA-Doc venv. Zero dependencies on our codebase. Loads one per-dimension model, reads image paths from stdin, writes JSONL predictions to stdout. | 319 |
| `subprocess_runner.py` | Orchestrator on our side. `DeQASubprocessRunner` launches one bridge subprocess per dimension (overall, sharpness, color_fidelity), feeds image paths, collects results. | 366 |

### Pipeline Scripts (`scripts/`)

| File | Purpose |
|------|---------|
| `generate_diqa_pseudo_labels.py` | Batch pipeline: reads a training manifest JSONL, runs DeQA-Doc inference via `DeQASubprocessRunner`, writes pseudo-labels with checkpointing (resumable). |
| `gate_diqa_pseudo_labels.py` | OOD acceptance gate: takes pseudo-labels + SigLIP 2 embeddings, computes Mahalanobis distance, assigns tiered sample weights (1.0/0.5/0.3/0.0). DIQA-5000 GT images always get weight=1.0. |

### Training Integration (`modal/train_siglip2_multitask.py`)

Added `_load_diqa_pseudo_labels()` function and modified the dataset class to:

- Auto-detect `data/gated_diqa_labels.jsonl` on the Modal volume
- Merge pseudo-labels into training manifest by SHA256
- Apply per-sample `sample_weight` to the loss for IQA heads

### DQS Calculator (`src/.../metrics/dqs_calculator.py`)

Extended `DQSConfig` with 3-dimension ML quality blending:

```python
ml_quality = (
    ml_overall_weight * overall         # 0.60
    + ml_sharpness_weight * sharpness   # 0.25
    + ml_color_weight * color_fidelity  # 0.15
)
```

Falls back to `overall` only when sharpness/color are unavailable (backward compatible with single-head models).

---

## 4. Specific Adaptations to DeQA-Doc's Inference

### 4a. Square Padding (Replicated)

We replicated the `_expand2square()` function from DeQA-Score's inference code. This pads non-square images to square using the image processor's mean pixel values as background color, matching DeQA-Doc's training-time preprocessing.

```python
def _expand2square(pil_img, background_color):
    width, height = pil_img.size
    if width == height:
        return pil_img
    side = max(width, height)
    result = Image.new(pil_img.mode, (side, side), background_color)
    # Center-paste the original
    ...
```

### 4b. Suppressed Weight Reinitialization

DeQA-Doc's `load_pretrained_model()` triggers PyTorch's default weight initialization for `nn.Linear` and `nn.LayerNorm`, which is wasteful when loading pretrained weights. We suppress this:

```python
torch.nn.Linear.reset_parameters = lambda _self: None
torch.nn.LayerNorm.reset_parameters = lambda _self: None
```

This is done inside the bridge script before model loading. It does **not** modify DeQA-Doc code.

### 4c. Prompt Construction

We build prompts using DeQA-Doc's conversation template exactly as their inference code does:

```python
conv = conv_templates["mplug_owl2"].copy()
user_msg = "How would you rate the quality of this image?\n" + DEFAULT_IMAGE_TOKEN
conv.append_message(conv.roles[0], user_msg)
conv.append_message(conv.roles[1], None)
prompt = conv.get_prompt() + " " + DIMENSION_PROMPTS[dimension]
```

The dimension-specific suffix (e.g., `"The overall_quality of the image is"`) matches DeQA-Doc's training prompts exactly.

### 4d. Score Extraction

Instead of parsing generated text, we extract logits at the last token position for the 5 quality level tokens (`excellent`, `good`, `fair`, `poor`, `bad`), apply softmax, and compute expected MOS:

```python
level_ids = [tokenizer(f" {name}", add_special_tokens=False)["input_ids"][-1]
             for name in ["excellent", "good", "fair", "poor", "bad"]]

logits_at_levels = output_logits[j, level_ids]
probs = torch.softmax(logits_at_levels, dim=0)
expected_mos = sum(p * m for p, m in zip(probs, [5.0, 4.0, 3.0, 2.0, 1.0]))
score_normalized = (expected_mos - 1.0) / 4.0  # Map [1,5] -> [0,1]
```

This is how DeQA-Score's own evaluation works — direct logit extraction rather than text generation, which is faster and deterministic.

### 4e. Batched Inference

The bridge script supports batched inference (`--batch-size N`, default 4). Images are preprocessed individually but fed as a concatenated tensor batch to the model. DeQA-Doc's original code processes one image at a time; our batching improves throughput ~3x on A100.

---

## 5. OOD Gating (Not Part of DeQA-Doc)

This is entirely our addition. DeQA-Doc models were trained on DIQA-5000 (~3.5K train images). Our training corpus includes ~140K+ images from diverse sources (DocLayNet, RVL-CDIP, SD7K, etc.) that may be out-of-distribution for the DeQA-Doc models.

We use a Mahalanobis distance detector fitted on DIQA-5000's SigLIP 2 embeddings (AUROC 0.9963 on held-out test) to assign reliability-weighted sample weights:

| Tier | Mahalanobis Percentile | Sample Weight |
|------|----------------------|---------------|
| GROUND_TRUTH | N/A (DIQA-5000 images) | 1.0 |
| AUTO_ACCEPT | < p75 | 1.0 |
| LOW_WEIGHT | p75 - p90 | 0.5 |
| TIER2_TRIGGER | p90 - p97.5 | 0.3 |
| HARD_REJECT | > p97.5 | 0.0 |

---

## 6. Environment Setup Requirements

To run the DeQA-Doc inference pipeline:

```bash
# 1. Clone DeQA-Doc and set up its venv
git clone https://github.com/Junjie-Gao19/DeQA-Doc.git
cd DeQA-Doc/DeQA-Score
python -m venv .venv
source .venv/bin/activate
pip install torch==2.0.1 transformers==4.36.1 Pillow
pip install -e .  # Install DeQA-Score package
deactivate

# 2. Download per-dimension models from ModelScope
# Models go into: /path/to/deqa_models/{overall,sharpness,color_fidelity}/

# 3. Run pseudo-labeling from our project
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python scripts/generate_diqa_pseudo_labels.py \
        --manifest /path/to/training_manifest.jsonl \
        --deqa-venv /path/to/DeQA-Doc/DeQA-Score/.venv \
        --deqa-root /path/to/DeQA-Doc/DeQA-Score \
        --model-dir /path/to/deqa_models \
        --output /path/to/diqa_pseudo_labels.jsonl \
        --device cuda:0
```

---

## 7. What We Did NOT Change

- **No model weight modifications**: All 3 per-dimension checkpoints used as-is
- **No DeQA-Doc source patches**: Bridge script imports DeQA-Doc modules but doesn't modify them
- **No training recipe changes**: We don't retrain or fine-tune DeQA-Doc models
- **No prompt modifications**: Dimension prompts match DeQA-Doc's training prompts exactly
- **No score rescaling**: MOS values computed identically to DeQA-Score's own evaluation

---

## 8. Known Limitations

1. **Inference speed**: ~2-3s per image per dimension on A100 (7B model). 3 dimensions = ~6-9s/image. Our batching reduces this but it's still the bottleneck.
2. **transformers pinning**: DeQA-Doc's mPLUG-Owl2 implementation depends on `transformers==4.36.1` internals. Upgrading breaks model loading.
3. **No Qwen2.5-VL integration yet**: We have a model card for DeQA-Doc's Qwen2.5-VL-7B variant but haven't integrated it into the bridge script. The prompt format differs.
4. **OOD gating is conservative**: p97.5 hard reject means ~2.5% of images get weight=0. This could be relaxed if DeQA-Doc models prove robust to OOD inputs.

---

## 9. File Inventory

```text
src/image_preprocessing_detector/labeling/deqa/
    __init__.py              # Package docs
    bridge_script.py         # Runs in DeQA-Doc venv (standalone)
    subprocess_runner.py     # Orchestrates bridge subprocess

scripts/
    generate_diqa_pseudo_labels.py   # Batch pseudo-labeling
    gate_diqa_pseudo_labels.py       # OOD acceptance gating

docs/
    planning/DEQA_DOC_PSEUDO_LABELING.md   # Design doc
    model-cards/external/deqa_mix.md       # DeQA-Mix model card
    model-cards/external/deqa_mplug_owl2_7b.md  # Base model card
    model-cards/external/deqa_qwen25_vl_7b.md   # Qwen variant card

modal/
    train_siglip2_multitask.py   # Training script (modified to load gated labels)
```

---

## 10. Contact

For questions about this integration: Byron Williams (project maintainer)
For questions about DeQA-Doc models/training: [Junjie Gao et al.](https://github.com/Junjie-Gao19/DeQA-Doc)
