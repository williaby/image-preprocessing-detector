---
title: Pseudo-Labeling Workstream Project Plan
schema_type: planning
status: draft
owner: ml-team
tags:
  - pseudo_labeling
  - iqa
  - training
  - dociq
purpose: Generate comprehensive pseudo-labels for ~2.5M document images to enable production IQA model training.
component: Strategy
source: UNIFIED_LABELING_STRATEGY.md
---

**Objective**: Generate comprehensive pseudo-labels for ~2.5M document images to enable production IQA model training

---

## Executive Summary

This project plan details the work required to complete the pseudo-labeling workflow, generating 3-dimension quality labels (overall, sharpness, color) for the entire document corpus. The approach follows the DocIQ architecture (1600×1600 + layout masks) validated by research.

**Total Estimated Cost**: $80-140
**Total Estimated Time**: 2-3 weeks
**Key Deliverable**: Pseudo-labels for ~2.5M images in Layer 2 (ENRICHMENT) metadata

---

## Current State

### What's Complete

| Component | Status | Artifacts |
|-----------|--------|-----------|
| Three-Layer Metadata Architecture | 100% | `annotate_base_metadata.py`, `build_training_labels.py` |
| Stage 1 DocIQ-Replica Training | 100% | `production_model_seed42.pt` (302MB), ECE=0.028 |
| Stage 2 Phase 1 Warmup | 100% | 15 epochs, Val SRCC=0.827 |
| 12,742 Layout Masks | 100% | 1600×1600, 11-class DocLayNet, NPZ format |
| Modal Infrastructure | 100% | `modal/generate_pseudo_labels.py`, GCS integration |
| UNIFIED_LABELING_STRATEGY.md | 100% | Soft-label approach documented |

### What's Incomplete

| Component | Status | Blocking Issues |
|-----------|--------|-----------------|
| Stage 2 Phase 2 Fine-tuning | 0% | Budget exhausted Dec 2024 |
| DeQA-Doc Anchor Labels | 0% | Not started |
| Full Corpus Pseudo-Labels | 0% | Requires a trained model |
| Documentation Updates | 0% | ADRs and CLAUDE.md need updates |

---

## Architecture Overview

### Target Output per Image

```json
{
  "soft_label_overall": [0.01, 0.02, 0.05, 0.12, 0.25, 0.30, 0.15, 0.06, 0.03, 0.01],
  "soft_label_sharpness": [...],
  "soft_label_color": [...],
  "predicted_score_overall": 0.45,
  "predicted_score_sharpness": 0.38,
  "predicted_score_color": 0.52,
  "prediction_uncertainty_overall": 0.018,
  "prediction_confidence_tier": "high",
  "prediction_model_version": "dociq-replica-v2.0",
  "anchor_source": "pseudo_high"
}
```

### Model Architecture (DocIQ-Replica)

| Component | Specification |
|-----------|---------------|
| Input Resolution | 1600×1600 |
| Backbone | ResNet-50 (ImageNet pretrained) |
| Layout Fusion | Dual-path downsampler + 11-class masks |
| Output | 3 distribution heads (10 bins each) |
| Loss | KL-divergence + EMD |
| Target SRCC | ≥0.87 (DocIQ benchmark) |

---

## Project Phases

### Phase 1: Stage 2 Phase 2 Fine-tuning (CRITICAL PATH)

**Objective**: Complete DocIQ-Replica training on multi-dataset corpus

**Duration**: 1-2 days
**Cost**: $15-25

#### Tasks

| Task | Description | Est. Time | Dependencies |
|------|-------------|-----------|--------------|
| 1.1 | Verify Stage 2 infrastructure on Modal | 2h | None |
| 1.2 | Resume training from Phase 1 checkpoint | 1h | 1.1 |
| 1.3 | Run 45 epochs fine-tuning | 12-18h | 1.2 |
| 1.4 | Validate on held-out DIQA-5000 test set | 2h | 1.3 |
| 1.5 | Export models (ONNX + TorchScript) | 1h | 1.4 |
| 1.6 | Register models in artifact registry | 1h | 1.5 |

#### Success Criteria

- Val SRCC ≥ 0.85 (overall dimension)
- Val PLCC ≥ 0.87
- ECE ≤ 0.05
- Output range covers [0.1, 0.9] (no collapsed predictions)

#### Inputs

- Stage 2 Phase 1 checkpoint (15 epochs warmup)
- 12,742 training images with layout masks
- DIQA-5000 validation split (500 images)

#### Outputs

- `dociq_replica_v2_teacher.pt` (~302MB)
- `dociq_replica_v2_student.pt` (~133MB)
- ONNX exports for production inference
- Training metrics report

---

### Phase 2: DeQA-Doc Anchor Labels (OPTIONAL HIGH-VALUE)

**Objective**: Generate high-quality MLLM labels for strategic datasets

**Duration**: 1-2 days
**Cost**: $20-35

This phase uses DeQA-Doc (MLLM, 0.93 accuracy) to create enriched ground truth for datasets where we have no human MOS or need validation.

#### Target Datasets

| Dataset | Images | Purpose | Priority |
|---------|--------|---------|----------|
| DIQA-5000 | 5,500 | Enrich human MOS with soft distributions | CRITICAL |
| SmartDoc-QA | 4,270 | Enable OCR correlation validation | HIGH |
| OCR-Quality | 1,000 | Cross-validate against human 1-4 scores | HIGH |
| DIBCO | 131 | Extreme degradation edge cases | MEDIUM |
| FUNSD | 199 | Real noisy scanned forms | MEDIUM |
| SROIE | 973 | Mobile capture / thermal print | MEDIUM |
| Tobacco-800 | 1,290 | Real archival degradation | MEDIUM |
| **Total** | **~13,363** | | |

#### Tasks

| Task | Description | Est. Time | Dependencies |
|------|-------------|-----------|--------------|
| 2.1 | Set up DeQA-Doc inference on Modal | 4h | None |
| 2.2 | Prepare dataset tarballs for GCS | 2h | None |
| 2.3 | Run DIQA-5000 inference (5.5K × 3 dims) | 6h | 2.1, 2.2 |
| 2.4 | Run SmartDoc-QA inference | 4h | 2.1 |
| 2.5 | Run remaining datasets | 4h | 2.1 |
| 2.6 | Validate OCR-Quality correlation (SRCC > 0.80) | 2h | 2.4 |
| 2.7 | Merge MLLM labels with human MOS (DIQA-5000) | 2h | 2.3 |
| 2.8 | Export to metadata registry | 2h | 2.7 |

#### Success Criteria

- DIQA-5000: Human-MLLM agreement > 85% (within 0.1 normalized)
- SmartDoc-QA: SRCC with OCR accuracy > 0.80
- OCR-Quality: SRCC with human scores > 0.80

#### Outputs

- DeQA-Doc predictions for 13K images (Parquet)
- Combined human+MLLM labels for DIQA-5000
- Validation report with correlation metrics

---

### Phase 3: Full Corpus Pseudo-Labeling

**Objective**: Generate pseudo-labels for all unlabeled datasets (~2.5M images)

**Duration**: 4-7 days
**Cost**: $40-70

#### Hybrid Two-Pass Approach

```text
Pass 1: DocIQ-Replica (fast) ──────────────────────────────────
  │  • All 2.5M images
  │  • ~30ms/image on GPU
  │  • Total: ~21 hours
  │  • Output: 3D distributions + uncertainty
  ↓
Uncertainty Filter ────────────────────────────────────────────
  │  • Flag high-uncertainty samples (variance > 0.0625)
  │  • Flag edge cases (score < 0.3 or > 0.9)
  │  • Expected: ~15-20% flagged (~400-500K images)
  ↓
Pass 2: DeQA-Doc MLLM (selective) ─────────────────────────────
  │  • Flagged images only
  │  • ~0.5s/image (quantized)
  │  • Total: ~3-4 days
  │  • Use MLLM prediction when disagreement > 0.2
  ↓
Final Labels ──────────────────────────────────────────────────
  │  • Merge Pass 1 + Pass 2
  │  • Assign confidence tiers
  │  • Export to Layer 2 metadata
```

#### Dataset Processing Order

| Priority | Dataset | Images | Est. Time (Pass 1) |
|----------|---------|--------|-------------------|
| 1 | tobacco800 | 1,290 | 1 min |
| 2 | historical_degraded | 1,356 | 1 min |
| 3 | funsd/funsd_plus | 1,699 | 1 min |
| 4 | sroie | 973 | 1 min |
| 5 | rvl_cdip | 400,000 | 3.3h |
| 6 | doclaynet | 80,000 | 40 min |
| 7 | tablebank | 278,000 | 2.3h |
| 8 | pubtabnet | 568,000 | 4.7h |
| 9 | nist_db2/sd6 | 11,000 | 5 min |
| 10 | Others | ~500,000 | 4h |
| | **Total** | **~2.5M** | **~21h** |

#### Tasks

| Task | Description | Est. Time | Dependencies |
|------|-------------|-----------|--------------|
| 3.1 | Generate layout masks for unmapped datasets | 8h | Phase 1 |
| 3.2 | Pass 1: Run DocIQ-Replica on all datasets | 24h | 3.1 |
| 3.3 | Analyze uncertainty distribution | 2h | 3.2 |
| 3.4 | Pass 2: Run DeQA-Doc on flagged samples | 72-96h | 3.3, Phase 2 |
| 3.5 | Merge Pass 1 + Pass 2 predictions | 4h | 3.4 |
| 3.6 | Assign confidence tiers | 2h | 3.5 |
| 3.7 | Export to Layer 2 metadata (Parquet) | 4h | 3.6 |
| 3.8 | Validate sample quality (manual review) | 4h | 3.7 |

#### Confidence Tiers

```python
CONFIDENCE_THRESHOLDS = {
    'high': {
        'max_variance': 0.015,   # variance < 0.015 (std < 0.12)
        'training_weight': 1.0,
    },
    'medium': {
        'max_variance': 0.0625,  # variance < 0.0625 (std < 0.25)
        'training_weight': 0.5,
    },
    'low': {
        'max_variance': float('inf'),
        'training_weight': 0.1,
    }
}
```

#### Outputs

- Pseudo-labels for ~2.5M images (Parquet)
- Confidence tier distribution report
- Per-dataset quality summary
- Integration with `build_training_labels.py`

---

### Phase 4: Documentation Updates

**Objective**: Update ADRs and CLAUDE.md to reflect current architecture

**Duration**: 1 day
**Cost**: $0 (engineering time only)

#### Tasks

| Task | Description | Est. Time | Dependencies |
|------|-------------|-----------|--------------|
| 4.1 | Add DEPRECATED headers to 6 planning docs | 1h | None |
| 4.2 | Update ADR-028 with DocIQ architecture | 2h | None |
| 4.3 | Update CLAUDE.md Phase 3 section | 1h | None |
| 4.4 | Update CLAUDE.md Performance Targets | 1h | None |
| 4.5 | Update ADR-030 with resolution clarification | 1h | None |
| 4.6 | Consolidate DIQA pseudo-label documents | 2h | None |
| 4.7 | Review and commit all changes | 1h | 4.1-4.6 |

#### Documents to Deprecate

```markdown
> **DEPRECATED**: This document describes an abandoned approach using sub-1600px resolution.
> Training at less than 1600x1600 was proven ineffective for document IQA.
> See `COMPLETE_TRAINING_HISTORY.md` for current state.
> See `docs/planning/PSEUDO_LABELING_STATUS_REPORT.md` for active strategy.
```

Apply to:

- `PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md`
- `PHASE7_SPRINT_IMPLEMENTATION_PLAN.md`
- `PHASE7_TRAINING_DEEP_DIVE.md`
- `PHASE7v4_TRAINING_DEEP_DIVE.md`
- `PHASE7_TRAINING_CRITIQUE.md`
- `PHASE7_AND_PHASE9_INTEGRATION.md`

---

### Phase 5: Validation & Integration

**Objective**: Validate pseudo-labels and integrate with training pipeline

**Duration**: 2-3 days
**Cost**: $5-10

#### Tasks

| Task | Description | Est. Time | Dependencies |
|------|-------------|-----------|--------------|
| 5.1 | Sample 1000 images for manual review | 4h | Phase 3 |
| 5.2 | Compute inter-rater agreement (pseudo vs human) | 4h | 5.1 |
| 5.3 | Update `build_training_labels.py` for pseudo sources | 4h | Phase 3 |
| 5.4 | Run training label generation pipeline | 8h | 5.3 |
| 5.5 | Validate anchor_source priority chain | 2h | 5.4 |
| 5.6 | Generate training dataset statistics | 2h | 5.5 |
| 5.7 | Create final validation report | 4h | 5.6 |

#### Validation Metrics

| Metric | Target | Method |
|--------|--------|--------|
| Pseudo-Human SRCC | > 0.85 | Compare pseudo to DIQA-5000 test set |
| Pseudo-Human Agreement | > 80% | Within 0.15 normalized score |
| Confidence Tier Distribution | 60% high, 30% medium, 10% low | Healthy distribution |
| OCR Correlation | SRCC > 0.75 | SmartDoc-QA OCR accuracy |

---

## Timeline Summary

```text
Week 1:
├── Day 1-2: Phase 1 - Stage 2 Fine-tuning (CRITICAL)
├── Day 3-4: Phase 2 - DeQA-Doc Anchor Labels (parallel with layout masks)
└── Day 5: Phase 4 - Documentation Updates

Week 2:
├── Day 1-2: Phase 3.1-3.3 - Layout masks + Pass 1 inference
├── Day 3-5: Phase 3.4 - Pass 2 MLLM inference (runs in background)
└── Day 5: Phase 3.5-3.6 - Merge + confidence tiers

Week 3:
├── Day 1-2: Phase 3.7-3.8 - Export + manual validation
└── Day 3-4: Phase 5 - Validation & Integration
```

---

## Cost Breakdown

| Phase | GPU Hours | Est. Cost | Notes |
|-------|-----------|-----------|-------|
| Phase 1: Stage 2 Fine-tuning | 18h | $15-25 | T4/A10 GPU |
| Phase 2: DeQA-Doc Anchors | 12h | $20-35 | A10/A100 for MLLM |
| Phase 3: Full Corpus | 96h | $40-70 | Hybrid approach |
| Phase 5: Validation | 4h | $5-10 | Spot inference |
| **Total** | **~130h** | **$80-140** | |

**Cost Optimization**:

- Use Modal spot instances where possible (40% savings)
- Batch inference for Pass 1 (1000+ images/batch)
- Quantize DeQA-Doc to 4-bit for Pass 2 (2x speedup)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Stage 2 training fails to converge | Low | High | Resume from Phase 1 checkpoint, adjust LR |
| Output range collapses | Medium | High | Add output range gate, early stopping |
| DeQA-Doc MLLM quality varies | Low | Medium | Validate on DIQA-5000 first |
| Pass 2 exceeds budget | Medium | Medium | Reduce MLLM coverage to 10% |
| Modal infrastructure issues | Low | High | Retry with exponential backoff |
| Layout mask generation bottleneck | Medium | Medium | Parallelize across workers |

---

## Dependencies

```text
Phase 1 (Stage 2 Fine-tuning)
    ↓
    ├── Phase 2 (DeQA-Doc Anchors) [parallel]
    ↓
Phase 3 (Full Corpus)
    ↓
Phase 4 (Documentation) [can start Week 1]
    ↓
Phase 5 (Validation & Integration)
```

---

## Success Criteria

### Minimum Viable (Must Have)

- [ ] Stage 2 Phase 2 training complete (Val SRCC ≥ 0.85)
- [ ] Pseudo-labels for ≥ 1M images
- [ ] Integration with `build_training_labels.py`
- [ ] Documentation updated (ADRs, CLAUDE.md)

### Target (Should Have)

- [ ] Pseudo-labels for all 2.5M images
- [ ] DeQA-Doc anchor labels for 13K strategic images
- [ ] Confidence tier distribution: 60% high, 30% medium
- [ ] Pseudo-human SRCC > 0.85 on validation set

### Stretch (Nice to Have)

- [ ] MLLM verification for all low-confidence samples
- [ ] Interactive dashboard for label quality monitoring
- [ ] Automated retraining pipeline trigger

---

## Appendix A: Soft Label Construction

```python
def construct_soft_label(
    score: float,  # Normalized 0-1 (0=best, 1=worst)
    n_bins: int = 10,
    sigma: float = 0.08  # Pseudo-variance from DeQA-Doc
) -> np.ndarray:
    """Convert continuous score to soft label distribution."""
    bin_centers = np.linspace(0.05, 0.95, n_bins)
    soft_label = np.exp(-0.5 * ((bin_centers - score) / sigma) ** 2)
    return soft_label / soft_label.sum()
```

---

## Appendix B: Anchor Source Priority Chain

```python
class AnchorSource(str, Enum):
    HUMAN = "human"                # Weight: 1.0 (DIQA-5000 MOS)
    MLLM_HIGH = "mllm_high"        # Weight: 0.95 (DeQA-Doc high conf)
    PSEUDO_HIGH = "pseudo_high"    # Weight: 0.90 (DocIQ-Replica high conf)
    PSEUDO_MEDIUM = "pseudo_medium" # Weight: 0.50
    MLLM_MEDIUM = "mllm_medium"    # Weight: 0.60
    PSEUDO_LOW = "pseudo_low"      # Weight: 0.20
    SYNTHETIC = "synthetic"        # Weight: 0.30
```

---

## Appendix C: Key File Locations

| File | Purpose |
|------|---------|
| `scripts/annotate_base_metadata.py` | Layer 1-2 metadata annotation |
| `scripts/build_training_labels.py` | Layer 3 training label computation |
| `modal/generate_pseudo_labels.py` | DocIQ-Replica (Pass 1) + DeQA-Doc (Pass 2) pseudo-labeling |
| `modal/stage1_deqa_inference.py` | DIQA inference pipeline |
| `src/image_preprocessing_detector/labeling/finetuning/` | DocIQ-Replica training |
| `docs/planning/UNIFIED_LABELING_STRATEGY.md` | Strategic approach |
| `docs/planning/PSEUDO_LABELING_STATUS_REPORT.md` | Current status |

---

*Last Updated: 2026-01-12*
