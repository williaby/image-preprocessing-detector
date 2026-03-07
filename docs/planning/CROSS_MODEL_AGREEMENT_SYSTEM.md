# Cross-Model Agreement System for OOD-Aware Document IQA

> **Status**: In Progress | Implementation Phase
> **Version**: 1.0.0
> **Created**: 2026-03-06
> **Updated**: 2026-03-06
> **Branch**: `feat/ood-cross-model-agreement`
> **Purpose**: Detect when SigLIP2-IQA predictions are unreliable on out-of-distribution
> documents using embedding-space OOD detection and cross-model agreement scoring.

---

## Problem Statement

SigLIP2-IQA-Base-86M (VQualA 0.886) was trained exclusively on DIQA-5000 (5,000 document
images). As deployment expands to diverse document types — handwritten forms, engineering
drawings, receipts, certificates, historical manuscripts — the model may produce confident
but wrong predictions on documents outside its training distribution.

**Key insight**: SigLIP2's built-in uncertainty (sigma-sq from GaussianNLL) captures
*aleatoric* uncertainty (data noise), not *epistemic* uncertainty (distribution shift).
A novel document type can produce a low-uncertainty but incorrect score.

**Solution**: Two-tier external reliability detection:

1. Tier 1: Embedding-space distance (free, ~1ms)
2. Tier 2: Cross-model validator agreement (conditional, ~2-3s)

---

## Architecture Overview

```
Input Image
    |
    v
[SigLIP2 Inference] --> IQA scores + embedding (768-dim)
    |
    v
[Tier 1: Embedding OOD] --> Mahalanobis distance from DIQA-5000 distribution
    |
    |-- In-distribution --> Return scores with high confidence
    |
    |-- OOD flagged --> Invoke Tier 2
                            |
                            v
                [Tier 2: Cross-Model Validation]
                    |-- VLM (Qwen3.5-9B or MiniCPM-V 4.5): categorical ratings
                    |-- CLIP-IQA+ / QualiCLIP: continuous scores
                            |
                            v
                [Calibrated Z-Scores] --> Agreement distance
                            |
                            v
                [ReliabilityResult] --> reliability_score, needs_review flag
```

---

## What Has Been Built

### Modified Files

| File | Changes |
| --- | --- |
| `src/.../detection/siglip2_multitask.py` | Added `embedding` field to `MultiTaskPrediction`, `_embedding` passthrough in `forward()`, `return_embedding` param on `predict()`/`predict_batch()`/`_postprocess()`, `has_embedding` in `prediction_to_dict()` |
| `src/.../detection/__init__.py` | Added Phase 10 imports and exports for OOD, calibration, and validator modules |

### New Modules

| File | Purpose |
| --- | --- |
| `src/.../detection/ood_detector.py` | `EmbeddingOODDetector`: Mahalanobis distance with Ledoit-Wolf shrinkage covariance. Fit from embeddings, save/load `.npz`, score single or batch. `OODResult` dataclass. |
| `src/.../detection/cross_model_calibration.py` | `CrossModelCalibrator`: Maps categorical VLM outputs to `P(MOS\|category)` distributions, maps continuous CLIP scores via isotonic regression. Computes z-scores for agreement. Save/load JSON. |
| `src/.../detection/cross_model_validator.py` | `CrossModelValidator`: Tier 1+2 integration. Tiered gating, agreement distance (Mahalanobis over z-vector), `ReliabilityResult` with `needs_review` flag. `ValidatorConfig` for file-based setup. |

### New Scripts

| File | Purpose |
| --- | --- |
| `scripts/run_vlm_prompting_experiment.py` | Benchmarks VLMs (Qwen3.5-9B, MiniCPM-V 4.5, etc.) with 3 prompting strategies on DIQA-5000. Computes SRCC/PLCC vs MOS per dimension. |
| `scripts/evaluate_ood_detection.py` | Evaluates OOD detection: AUROC, FPR@95TPR for Tier 1, Tier 2, and combined. Supports multiple OOD datasets. |
| `scripts/extract_siglip2_embeddings.py` | Extracts 768-dim penultimate embeddings from SigLIP2 for a dataset. Also fits OOD detector from extracted embeddings. |
| `scripts/generate_ood_poc_dataset.py` | Generates a 480-image synthetic proof-of-concept dataset (150 ID + 330 OOD across 11 categories) with known generation parameters and synthetic quality labels. Runs in ~12s on CPU. |

### Verified Working

- All module imports succeed through `__init__.py`
- OOD detector correctly separates in-dist (d=25.79) from OOD (d=137.58) on synthetic data
- Save/load roundtrip verified (exact distance match)
- Calibrator fits 4 categories, computes z-scores correctly (z=-0.03 for well-matched case)
- Ledoit-Wolf shrinkage = 0.98 on 768-dim embeddings (appropriate regularization)

---

## What Remains To Be Done

### Phase 0: Proof-of-Concept with Synthetic Data (CPU only, no GPU needed)

**Priority: IMMEDIATE** -- Can run now, validates the entire pipeline end-to-end.

#### 0.1 Generate PoC Dataset (DONE -- script verified working)

```bash
uv run python3 scripts/generate_ood_poc_dataset.py \
    --output results/ood_poc_dataset/ --seed 42
```

Output: 480 images (150 in-dist + 330 OOD across 11 categories):

- **In-distribution**: Latin standard (100), Cyrillic (50)
- **OOD by script**: Tibetan (30), Myanmar (30), Ethiopic (30)
- **OOD by quality**: Pristine (30), Heavily degraded (30)
- **OOD by resolution**: Very low DPI (30), Very high DPI (30)
- **OOD by layout**: Form-based (30)
- **OOD by color**: Binarized (30)
- **OOD by composition**: Multi-script (30), CJK vertical (30)

Each image has synthetic quality labels (scores + categories) based on known
generation parameters -- enables full pipeline testing without VLM inference.

#### 0.2 Extract PoC Embeddings (requires GPU + SigLIP2 checkpoint)

```bash
# Extract ID embeddings
uv run python3 scripts/extract_siglip2_embeddings.py \
    --checkpoint models/siglip2_multitask/best_model.pt \
    --meta-path results/ood_poc_dataset/metadata.jsonl \
    --image-root "" \
    --output results/ood_poc_dataset/embeddings_all.npy \
    --device cuda:0

# Fit OOD detector on ID subset only
uv run python3 scripts/extract_siglip2_embeddings.py \
    --fit-ood results/ood_poc_dataset/embeddings_id.npy \
    --ood-output models/ood/ood_params_poc.npz
```

#### 0.3 Evaluate PoC OOD Detection

```bash
uv run python3 scripts/evaluate_ood_detection.py \
    --in-dist-embeddings results/ood_poc_dataset/embeddings_id.npy \
    --ood-embeddings results/ood_poc_dataset/embeddings_ood_script.npy \
                     results/ood_poc_dataset/embeddings_ood_quality.npy \
                     results/ood_poc_dataset/embeddings_ood_resolution.npy \
    --ood-name script_ood quality_ood resolution_ood \
    --output results/ood_poc_evaluation/
```

#### 0.4 Test Calibration with Synthetic Labels

Use `synthetic_categories` from `metadata.jsonl` to test calibration pipeline
without VLM inference. Verify z-scores are near zero for ID images and elevated
for OOD images.

#### 0.5 Expected PoC Outcomes

| OOD Category | Expected AUROC | Rationale |
| --- | --- | --- |
| Script (Tibetan/Myanmar/Ethiopic) | >0.90 | Very different visual patterns |
| Resolution (72/600 DPI) | >0.85 | Image structure differs significantly |
| Quality (pristine/degraded) | 0.70-0.85 | Texture/noise differences |
| Layout (form) | 0.60-0.80 | Spatial structure differs |
| Color (binarized) | >0.85 | Channel distribution very different |
| Multi-script | 0.60-0.75 | Partial overlap with ID |

**Note**: Synthetic PoC validates the *pipeline mechanics*, not final performance.
Real OOD evaluation (Phase 3) uses genuine document datasets for valid metrics.

---

### Phase 1: Data Collection and Experimentation (GPU required)

**Priority: HIGH** — These are blocking steps that require GPU compute.

#### 1.1 Extract DIQA-5000 Training Embeddings

- Run `SigLIP2MultiTaskDetector.predict(image, return_embedding=True)` on all 3,500
  DIQA-5000 training images
- Save embeddings as `.npy` array (shape: 3500 x 768)
- Requires: SigLIP2 checkpoint + GPU

```bash
# Pseudocode — needs a small script to iterate DIQA-5000 train set
uv run python3 scripts/extract_siglip2_embeddings.py \
    --checkpoint models/siglip2_multitask/best_model.pt \
    --meta-path /path/to/diqa-5000/metas/train.json \
    --image-root /path/to/diqa-5000/images/ \
    --output results/embeddings/diqa5000_train.npy
```

#### 1.2 Fit OOD Detector on Training Embeddings

- Call `EmbeddingOODDetector.from_embeddings(train_embeddings, threshold_percentile=95.0)`
- Save to `models/ood/ood_params.npz`
- Validate on DIQA-5000 val set (500 images) — expect <5% false positive rate

#### 1.3 Run VLM Prompting Experiment

- Run `scripts/run_vlm_prompting_experiment.py` with Qwen3.5-9B and MiniCPM-V 4.5
- Three strategies: overall_only, single_prompt_3dim, separate_prompts
- Evaluate SRCC vs MOS for each model x strategy combination
- Select best VLM and prompting strategy
- Requires: VLM model weights + GPU (24GB+ VRAM for 9B model)

#### 1.4 CLIP-IQA+ / QualiCLIP Benchmark

- Install `pyiqa` package
- Run CLIP-IQA+ and QualiCLIP on DIQA-5000
- Compare SRCC vs MOS (LIQE was 0.403 on DIQA-5000 — these should beat it)
- Select best continuous validator

### Phase 2: Calibration (after Phase 1 data collection)

**Priority: HIGH** — Requires Phase 1 results.

#### 2.1 Fit Categorical Calibration

- Use VLM ratings from Phase 1.3 + DIQA-5000 MOS
- Call `CrossModelCalibrator.fit_categorical()` per dimension
- Inspect distributions — check for sparse categories, non-Gaussian shapes
- Save to `models/ood/calibration_params.json`

#### 2.2 Fit Continuous Calibration

- Use CLIP-IQA+ scores from Phase 1.4 + DIQA-5000 MOS
- Call `CrossModelCalibrator.fit_continuous()`
- Save to same calibration file

#### 2.3 Fit Z-Score Covariance

- Compute z-score vectors for all calibration images
- Call `CrossModelValidator.fit_z_covariance()`
- Save to `models/ood/z_covariance.npz`

### Phase 3: OOD Evaluation (after Phase 2)

**Priority: HIGH** — Validates the entire system.

#### 3.1 Acquire OOD Datasets

- **Tobacco800**: Historical scanned memos/letters (~1,600 images)
- **RVL-CDIP subset**: 16 document classes (~5,000 images)
- **CORD**: Receipt images (~1,000 images)
- **Handwritten samples**: From existing Egyptian-Handwriting, GNHK, SALAMI datasets
  (already in the project per OOD_DATASET_DESIGN.md)

#### 3.2 Extract OOD Embeddings

- Run SigLIP2 with `return_embedding=True` on each OOD dataset
- Save as `.npy` per dataset

#### 3.3 Run Full Pipeline on OOD Sets

- For each OOD dataset: run VLM + CLIP-IQA+ validators
- Compute ReliabilityResult for each image
- Save as JSONL

#### 3.4 Evaluate OOD Detection

- Run `scripts/evaluate_ood_detection.py`
- Target: AUROC > 0.85 on at least one OOD dataset
- Analyze which tier (1 vs 2 vs combined) works best per OOD type

### Phase 4: Production Integration (after Phase 3 validates)

**Priority: MEDIUM** — Only after Phase 3 shows the system works.

#### 4.1 Add Config to siglip2_multitask.yaml

- OOD detection on/off toggle
- Tier 2 model paths and thresholds
- Agreement threshold tuning

#### 4.2 Wire into Inference Pipeline

- Add `ReliabilityResult` to the standard inference output
- Tier 1 always-on (negligible cost)
- Tier 2 conditional on Tier 1 flag

#### 4.3 Performance Benchmarks

- Tier 1 latency: target <5ms overhead
- Tier 2 latency: measure VLM + CLIP-IQA+ combined
- Memory impact of keeping OOD params loaded

### Stretch Goals

| Goal | Priority | Description |
| --- | --- | --- |
| Learned risk model (GBDT) | LOW | Replace Mahalanobis aggregation with trained GBDT once OOD feedback accumulates |
| Additional VLM validators | LOW | Add InternVL3.5 or DeepSeek-VL2 for more diversity |
| GMM-based category distributions | LOW | Replace Gaussian assumption with Gaussian Mixture Models for multi-modal categories |
| Embedding PCA visualization | LOW | Visualize DIQA-5000 vs OOD in 2D/3D embedding space |

---

## Design Decisions and Rationale

### Why not use SigLIP2's sigma-sq for OOD detection?

Unanimous consensus from 6-model review: sigma-sq from GaussianNLL captures *aleatoric*
uncertainty (measurement noise), not *epistemic* uncertainty (model doesn't know). A novel
document type can have low sigma-sq but wrong predictions. Embedding distance captures
distributional shift directly.

### Why calibrate to MOS, not SigLIP2 scores?

GPT-5.2 identified reference-model bias: calibrating validators to SigLIP2's predictions
would only detect when validators disagree with SigLIP2, not when SigLIP2 is actually
wrong. Calibrating to ground-truth MOS decouples the system from the primary model's errors.

### Why Qwen3.5-9B over Qwen3-VL-8B?

Qwen3.5 (released Feb 2026) uses early-fusion multimodal training — vision is trained
jointly with text from scratch, not bolted-on. This gives better document understanding
(OmniDocBench 90.8) and maximally different architecture from SigLIP2's ViT regression head.

### Why exclude Gemma 3 and Phi-4-reasoning-vision?

Both use SigLIP/SigLIP-2 as their vision encoder — architecturally too similar to our
primary model. Cross-model agreement requires architectural diversity for errors to be
uncorrelated.

### Why Mahalanobis over Isolation Forest or GBDT?

Mahalanobis is unsupervised — it only needs the in-distribution calibration set. Isolation
Forest and GBDT require labeled OOD examples for training/tuning, which we don't have at
the start. Can upgrade later once OOD feedback accumulates.

---

## VLM Model Candidates (Evaluated March 2026)

| Model | Doc Benchmark | Arch Diversity vs SigLIP2 | Params | Status |
| --- | --- | --- | --- | --- |
| **Qwen3.5-9B** | OmniDocBench 90.8 | Very High (early fusion + MoE) | 9B | Primary candidate |
| **MiniCPM-V 4.5** | OCRBench > GPT-4o | High (unified OCR learning) | ~8B | Secondary candidate |
| DeepSeek-VL2-Small | DocVQA 93.3% | High (MoE) | 2.8B active | Fallback (fastest) |
| InternVL3.5-8B | Good | High | 8B | Optional diversity |
| Gemma 3 | Good | Low (uses SigLIP) | 12-27B | Excluded |
| Phi-4-reasoning-vision | Good | Low (uses SigLIP-2) | 15B | Excluded |

---

## Consensus Sources

Design validated by 6-model consensus (Gemini 2.5 Pro, Gemini 3 Pro, GPT-5.2,
DeepSeek R1, Grok-4, Grok-4.1-fast). Key agreements:

1. Tier 1 sigma-sq gate fundamentally flawed — use embedding distance
2. Real OOD datasets mandatory (not just synthetic corruption)
3. Calibrate to MOS not SigLIP2 to avoid reference-model bias
4. Separate prompts per dimension for VLM
5. Mahalanobis acceptable as unsupervised baseline
