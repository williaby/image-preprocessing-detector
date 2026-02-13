# Weak Label Pipeline Roadmap: Resolution Quality for MobileNetV4

## Goal

Train a production MobileNetV4 resolution_quality head on 30K+ labeled images
using a synthetic-first weak label approach with soft label teacher-student transfer.

## Pipeline Overview

```text
synthetic (250K, tier_0_exact, hard labels)
  -> Phase 2: train teacher
    -> Phase 3: teacher labels real data (15-30K, tier_2_model, soft labels)
      -> Phase 4: train student on synthetic + real (soft label distillation)
        -> Production MobileNetV4 resolution_quality head
```

---

## Phase 1: Schema Foundation + Synthetic Dataset

**Status**: In Progress
**Branch**: `feat/stream-1-schema-foundation`

### Deliverables

- Extended `ResolutionQualityResult` with provenance + soft label fields
- `ScriptAwareMeasurementConfig` + `resolve_script_family()`
- `EnrichmentData` extended with 15 new fields (DPI provenance, soft labels)
- Shared `measure_char_height_v2()` in `resolution_quality.py`
- `GeneratedSample` with font_size_pt, target_dpi, clean/degraded/analytical heights
- `ScriptConfig` with rq_min/max_font_size (6-48pt)
- Integration script extended for provenance + soft label fields
- Updated synth-multiscript-250k.md documentation
- Weak label output schema in V2 strategy doc

### Inputs

- Existing synth-multiscript generator
- `resolution_quality.py` module
- 7 DPI tier config (72/100/150/200/300/400/600)

### Outputs

- Schema-ready codebase for synthetic dataset generation

---

## Phase 2: Teacher Model Training

**Status**: Not Started
**Prerequisites**: Phase 1 complete, synthetic dataset generated (~250K images)

### Deliverables

- MobileNetV4-Conv-S teacher trained on tier_0_exact labels
- 3 heads: orientation (4-class), skew (regression), resolution_quality (regression + 5-class)
- quality_score regression head + coarse_bucket softmax head (multi-task)
- Validated against DIQA-5000 CC measurements (SRCC target: >0.60)
- Model checkpoint exported for inference

### Training Details

- **Platform**: Modal (A100 GPU)
- **Dataset**: synth-multiscript-v2-rq (~250K, tier_0_exact, 7 DPI tiers x 6-48pt fonts x 27 scripts)
- **Architecture**: MobileNetV4-Conv-S backbone -> 3 task heads
- **Resolution quality head**: dual output (regression 0-1 + softmax 5-class)
- **Loss**: MSE for regression + cross-entropy for classification + Kendall uncertainty weighting
- **Phased training**: warmup (orient+skew 5ep) -> expand (+RQ 5ep) -> full (20-40ep)

### Key Decisions for Phase 2 Planning

- MC Dropout vs ensemble for teacher uncertainty estimation?
- How many forward passes for uncertainty (5? 10?)?
- Validation split strategy for teacher (synthetic val set vs held-out DIQA-5000?)
- Should teacher also train on existing DIQA-5000 CC measurements (tier_3_heuristic)?

---

## Phase 3: Real Dataset Labeling with Soft Labels

**Status**: Not Started
**Prerequisites**: Phase 2 complete (validated teacher model)

### Deliverables

- Soft labels for DIQA-5000 (5.5K), OHR-Bench (8.5K), RealDAE (1.2K) -> ~15K
- Additional real datasets as available toward 30K target
- Per-image: bucket_probabilities, quality_score +/- std, char_height_px +/- std
- Active learning selection: flag top-N% uncertain predictions for manual review
- `integrate_resolution_quality.py` run to merge into L2 metadata

### Inference Details

- **Platform**: Local GPU or Modal (teacher inference, ~3ms/image)
- **MC Dropout**: N forward passes per image to estimate uncertainty
- **Script from L2 metadata**: Use if script_confidence >= 0.8, else "mixed"
- **Output**: tier_2_model labels with soft probabilities

### Key Decisions for Phase 3 Planning

- Uncertainty threshold for active learning flagging
- Manual review workflow (VLM re-scoring? Human annotation?)
- Which additional datasets beyond DIQA-5000/OHR-Bench/RealDAE?

---

## Phase 4: Student Model Training with Soft Labels

**Status**: Not Started
**Prerequisites**: Phase 3 complete (30K+ labeled real images)

### Deliverables

- Production MobileNetV4 student trained on combined data
- Soft label loss: KL-divergence on bucket_probabilities + uncertainty-weighted MSE
- Provenance-weighted training: tier_0 weight=1.0, tier_2 weight=conf*(1/std)
- Distillation: student learns teacher's uncertainty at bucket boundaries
- ONNX + TorchScript export for production deployment

### Key Decisions for Phase 4 Planning

- Temperature parameter for KL-divergence distillation
- Ratio of synthetic vs real data in training batches
- Whether to fine-tune the skew head on real skew labels simultaneously
- Validation protocol: held-out real test set vs cross-validation

---

## Cross-Phase Artifacts

| Artifact | Created | Used By |
|----------|---------|---------|
| resolution_quality.py (extended) | Phase 1 | All phases |
| synth-multiscript-v2-rq dataset | Phase 1 -> generate | Phase 2 |
| Teacher model checkpoint | Phase 2 | Phase 3, Phase 4 |
| Real dataset soft labels (L2 metadata) | Phase 3 | Phase 4 |
| Student model (ONNX/TorchScript) | Phase 4 | Production |

## Soft Label Schema

### tier_0_exact (Synthetic, Phase 1-2)

```json
{
  "coarse_bucket": "optimal",
  "bucket_probabilities": {"optimal": 1.0, "good": 0.0, "needs_light_upscale": 0.0, "needs_major_upscale": 0.0, "oversized": 0.0},
  "quality_score_std": 0.0,
  "char_height_std": 0.0,
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0
}
```

### tier_2_model (Weak Labels, Phase 3)

```json
{
  "coarse_bucket": "optimal",
  "bucket_probabilities": {"optimal": 0.63, "needs_light_upscale": 0.22, "good": 0.12, "needs_major_upscale": 0.01, "oversized": 0.02},
  "quality_score_std": 0.06,
  "char_height_std": 2.1,
  "label_provenance": "tier_2_model",
  "label_confidence": 0.82
}
```

## Consensus Validation

- **5-model consensus**: Gemini 2.5 Pro (9/10), Gemini 3 Pro Preview (9/10), DeepSeek R1 (8/10), Grok 4 (8/10)
- **GPT-5.2**: Empty response (recurring issue)
- **Mean confidence**: 8.5/10
- **Key unanimous findings**:
  - Clean measurement before degradation is essential for tier_0_exact
  - Store both char_height_clean_px and char_height_degraded_px
  - Provenance tier system is well-designed
  - Script-aware measurement parameters should start conservative
  - Arabic CC problem needs vertical projection profiling (V2 Phase B)
  - Font range 6pt minimum (not 8pt) for needs_major_upscale coverage
  - Shared measurement code between generator and labeling pipeline
