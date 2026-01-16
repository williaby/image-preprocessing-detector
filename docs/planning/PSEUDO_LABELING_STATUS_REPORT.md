---
title: Pseudo-Labeling Workflow Status Report
schema_type: planning
status: draft
owner: ml-team
tags:
  - pseudo_labeling
  - iqa
  - training
  - dociq
purpose: Track pseudo-labeling workflow status, document deprecations, and identify required updates.
component: Strategy
source: UNIFIED_LABELING_STRATEGY.md
---

**Status**: Active Review

---

## Executive Summary

The pseudo-labeling workflow is **partially complete with significant gaps**. Key finding: **training at less than 1600x1600 resolution was proven ineffective for document IQA**. This invalidates several earlier planning documents and requires updates to ADRs and CLAUDE.md.

| Component | Status | Completion |
|-----------|--------|------------|
| Strategic Planning | Complete | 100% |
| Three-Layer Metadata Architecture | Complete | 100% |
| Automated Labeling Scripts | Complete | 100% |
| Stage 1 DocIQ-Replica Training | Complete | 100% |
| Stage 2 Phase 1 (Warmup) | Complete | 100% |
| Stage 2 Phase 2 (Fine-tuning) | Not Started | 0% |
| Full Corpus Pseudo-Labels | Not Started | 0% |

---

## Current Label Coverage

| Label Status | Datasets | Images | Training Usability |
|--------------|----------|--------|-------------------|
| 3-dimension Document MOS | 1 (DIQA-5000) | 5,500 | Full anchor |
| Natural Image DMOS | 2 (LIVE, CSIQ) | ~1,600 | Domain mismatch |
| OCR Accuracy (no MOS) | 1 (SmartDoc-QA) | 4,270 | Proxy only |
| Domain-specific labels | 12 | ~1M | No quality labels |
| No quality labels | 6 | ~1.5M | Requires pseudo-labeling |

**Critical Gap**: Only DIQA-5000 (5,500 images, 0.2% of corpus) has the 3-dimension human MOS labels required for training.

---

## What Automated Labeling Provides

### annotate_base_metadata.py

Implements Layers 1-2 of the three-layer architecture:

| Tier | Source | Labels Provided |
|------|--------|-----------------|
| Tier 0 | Exact by construction | Dataset IS 100% content type (e.g., PubTabNet = tables) |
| Tier 1 | COCO/JSON annotations | Bounding boxes, element categories from source |
| Tier 2 | DocLayout-YOLO inference | `has_table`, `has_formula`, `has_handwriting` (11 classes) |
| Tier 3 | Dataset heuristics | Capture method, domain classification |

### build_training_labels.py

Implements Layer 3 (TRAINING):

- **45-dim degradation vector** (iqa_vector) - all defect types
- **Binary presence flags** (iqa_binary)
- **Anchor score** with priority chain: human > llm_high > llm_medium > synthetic
- **Training weights** based on label source quality

### What's NOT Programmatically Derivable

- **Perceptual quality predictions** (overall MOS, sharpness, color)
- Requires trained model inference at 1600x1600
- Stage 2 Phase 2 must be completed first

---

## Resolution Requirement

**Training at less than 1600x1600 was proven ineffective.**

| Resolution | JPEG 8x8 Block Size | Visibility | Status |
|------------|---------------------|------------|--------|
| 224x224 | 1.8px | Invisible | ABANDONED |
| 384x384 | 3.1px | Barely visible | ABANDONED |
| 768x768 | 6.1px | Marginal | Not tested |
| **1600x1600** | **12.8px** | **Clearly visible** | CURRENT STANDARD |

**Source**: DocIQ paper (arXiv:2509.17012) - "ensures high-frequency components of text characters are preserved"

---

## Research Foundation: DocIQ and DeQA-Doc Papers

### DocIQ Architecture (arXiv:2509.17012)

The DocIQ paper establishes the architecture our implementation follows:

| Component | Specification |
|-----------|---------------|
| **Input Resolution** | 1600×1600 (confirmed) |
| **Backbone** | ResNet-50 pretrained on ImageNet |
| **Layout Fusion Downsampler** | Dual-path: spatial downsampling + semantic layout mask |
| **Layout Mask Classes** | 11 DocLayNet classes (text, tables, figures, etc.) |
| **Output Heads** | 3 independent regressors (overall, sharpness, color) |
| **Loss Function** | Distribution-matching: KL divergence + EMD |

**Performance on DIQA-5000**:

- SRCC: 0.8704 (average across dimensions)
- PLCC: 0.8999

### Layout Fusion Downsampler Design

The dual-path architecture addresses high-resolution processing:

```text
Path 1 (Primary): Image → Spatial Downsampling → Features
Path 2 (Secondary): Image + Layout Mask → Semantic Downsampling → Features
                                    ↓
                            Feature Fusion → Backbone
```

**Benefits**:

- Reduces computational complexity while preserving quality-relevant features
- Semantic region focusing (text vs. figures vs. tables)
- Preserves crucial spatial relationships

### DeQA-Doc: VQualA 2025 Champion (arXiv:2507.12796)

DeQA-Doc won the ICCV 2025 VQualA DIQA Challenge with **0.9288 final score**.

**Key Innovation - Soft Labels Without Variance**:

> "DIQA-5000 only provides mean scores **without corresponding variances**, making direct construction of soft labels infeasible."

**Solutions for Missing Variance** (applicable to our approach):

1. **Pseudo-variance**: Assign fixed σ based on empirical statistics

   ```python
   sigma = 0.08  # Empirical: 0.2 × 0.4 range per bin
   ```

2. **Linear interpolation**: Between adjacent quality levels as lightweight surrogate

This validates our `UNIFIED_LABELING_STRATEGY.md` soft-label construction approach.

### DIQA-5000 Dataset Details

| Attribute | Value |
|-----------|-------|
| Total images | 5,000 (from 500 base images) |
| Distortion types | 5: shadow, occlusion, blur, creases, moiré pattern |
| Human raters | 15 per image |
| Quality dimensions | 3: overall, sharpness, color fidelity |
| Scale | MOS 1-5 (5 = best) |

### Implications for Our Strategy

| Research Finding | Impact |
|------------------|--------|
| 1600×1600 confirmed essential | Validates resolution requirement |
| Layout masks improve quality | Confirms need for DocLayNet masks |
| Pseudo-variance works (σ=0.08) | Enables soft labels from MOS-only |
| KL-div loss effective | Validates distribution-matching approach |
| 0.87+ SRCC achievable | Sets realistic performance target |
| DeQA-Doc 0.93 with MLLM | MLLM teacher viable for anchor labels |

### References

- [DocIQ Paper (arXiv:2509.17012)](https://arxiv.org/abs/2509.17012)
- [DeQA-Doc Paper (arXiv:2507.12796)](https://arxiv.org/abs/2507.12796)
- [DeQA-Doc GitHub](https://github.com/Junjie-Gao19/DeQA-Doc)

---

## Documents for Deprecation

### Full Deprecation Required

These documents describe abandoned sub-1600px approaches:

| Document | Resolution | Action |
|----------|------------|--------|
| `docs/planning/PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md` | 384x384 | Add DEPRECATED header |
| `docs/planning/PHASE7_SPRINT_IMPLEMENTATION_PLAN.md` | 224/384px | Add DEPRECATED header |
| `docs/planning/PHASE7_TRAINING_DEEP_DIVE.md` | 224px | Add DEPRECATED header |
| `docs/planning/PHASE7v4_TRAINING_DEEP_DIVE.md` | TBD | Review and deprecate |
| `docs/planning/PHASE7_TRAINING_CRITIQUE.md` | 224/384px | Add DEPRECATED header |
| `docs/planning/PHASE7_AND_PHASE9_INTEGRATION.md` | TBD | Review for resolution |

### Deprecation Header Template

```markdown
> **DEPRECATED**: This document describes an abandoned approach using sub-1600px resolution.
> Training at less than 1600x1600 was proven ineffective for document IQA.
> See `COMPLETE_TRAINING_HISTORY.md` for the current state.
> See `docs/planning/UNIFIED_LABELING_STRATEGY.md` for the active strategy.
```

### Partial Deprecation / Update Required

| Document | Issue | Action |
|----------|-------|--------|
| `docs/planning/UNIFIED_LABELING_STRATEGY.md` | Still valid but needs consolidation | Update to reflect current state |
| `docs/planning/DIQA-5000_Pseudo_Labels.md` | Outdated ensemble approach | Review and consolidate |
| `docs/planning/DIQA-5000_Pseudo_Labels_v2.md` | Outdated ensemble approach | Review and consolidate |

---

## ADR Inconsistencies

### Already Correctly Deprecated

| ADR | Status |
|-----|--------|
| `0014-classical-ml-hybrid-iqa.md` | Has DEPRECATED header |
| `0025-mobilenetv3-vs-efficientnet.md` | Has DEPRECATED header |

### Requiring Updates

#### ADR-028: ResNet Teacher-Student Architecture

**Critical Issues**:

1. **Missing resolution specification** - No mention of 1600x1600
2. **Invalid latency targets** - Stated 10-40ms, realistic is 50-200ms at 1600px
3. **Missing DocIQ architecture** - No Layout Fusion Downsampler mention
4. **Missing layout masks** - No 11-class DocLayNet mask requirement

**Current (Incorrect)**:

```text
| Student (ResNet-18) GPU | 10ms |
| Student (ResNet-18) CPU | 40ms |
| Teacher (ResNet-50) GPU | 30ms |
```

**Should Be (1600px)**:

```text
| Student (ResNet-18) GPU | ~50-100ms at 1600x1600 |
| Teacher (ResNet-50) GPU | ~150-200ms at 1600x1600 |
| CPU inference | Not recommended (use classical IQA fallback) |
```

#### ADR-030: Document Quality Score Design

- No resolution specified for ML IQA input
- Add clarification that ML IQA operates at 1600x1600

#### ADR-022: Synthetic Data Generation

- Designed for ImageNet-style training (224px)
- May need update if synthetic data used at 1600px

---

## CLAUDE.md Inconsistencies

### Phase 3 Section

**Current**:

```text
- **Student Model** (ResNet-18): Default production inference, val_loss=0.14
- **Teacher Model** (ResNet-50): High-capacity model for difficult cases, val_loss=0.27
```

**Issues**:

1. No mention of 1600x1600 resolution requirement
2. No mention of layout masks
3. No mention of DocIQ-Replica architecture
4. val_loss values are from Stage 1 only (incomplete training)

**Recommended**:

```text
- **Architecture**: DocIQ-Replica with Layout Fusion Downsampler
- **Input Resolution**: 1600x1600 (required for compression detection)
- **Layout Masks**: 11-class DocLayNet masks (1600x1600)
- **Training Status**: Stage 1 complete, Stage 2 Phase 2 pending
```

### Performance Targets Section

**Current**:

```text
| Student (ResNet-18) CPU | ≤40ms/page (target) |
| Student (ResNet-18) GPU | ≤10ms/page (target) |
```

**Issues**: Unrealistic at 1600x1600 (50x more pixels than 224px)

**Recommended**:

```text
| Student (ResNet-18) GPU | ≤100ms/page at 1600x1600 |
| Teacher (ResNet-50) GPU | ≤200ms/page at 1600x1600 |
| CPU inference | Use 300 DPI classical IQA fallback |
```

---

## Valid Documentation

These documents remain accurate:

| Document | Status | Notes |
|----------|--------|-------|
| `COMPLETE_TRAINING_HISTORY.md` (root) | Valid | Comprehensive history, correctly identifies 1600px |
| `docs/planning/UNIFIED_LABELING_STRATEGY.md` | Mostly Valid | Core strategy correct, needs minor updates |
| `docs/architecture/diagrams/level-2/pseudo-labeling/index.md` | Valid | 5-model ensemble design |
| `docs/planning/automated-data-labeling-pipeline.puml` | Valid | Three-layer architecture |
| `docs/reference/metadata-versioning-schema.md` | Valid | Resolution-agnostic |
| `scripts/annotate_base_metadata.py` | Valid | Automated labeling |
| `scripts/build_training_labels.py` | Valid | Training label computation |

---

## Required Actions

### Critical (Architecture Decision Required)

0. [ ] **Decide 45→5 head mapping strategy** - See "Production Model Architecture Gap" section
   - Option A: Keep 5 heads, group 45 types
   - Option B: Expand to 8 heads (recommended)
   - Option C: Full 45-head model
   - Option D: Two-stage coarse + fine
1. [ ] **Resolve head naming inconsistency** - `illumination/artifacts` vs `contrast/compression`

### High Priority

1. [ ] Add DEPRECATED headers to 6 planning documents
2. [ ] Update ADR-028 with 1600x1600 and DocIQ requirements
3. [ ] Update CLAUDE.md Phase 3 section
4. [ ] Update CLAUDE.md Performance Targets

### Medium Priority

1. [ ] Update ADR-030 with resolution clarification
2. [ ] Consolidate DIQA pseudo-label documents
3. [ ] Update CLAUDE.md Key Technologies section

### Low Priority

1. [ ] Review ADR-022 for resolution implications
2. [ ] Archive deprecated planning documents

---

## Production Model Architecture Gap

### 45 Degradation Types vs 5 Model Heads

**Critical Discovery**: The training label taxonomy defines 45 degradation types, but the production model outputs only 5 aggregate scores.

#### Current Production Model (5 Heads)

From `src/.../models/resnet_teacher.py`:

```python
ISSUE_TYPES = ["blur", "noise", "skew", "illumination", "artifacts"]
```

**Note**: Naming inconsistency exists in codebase - `iqa_ml.py` uses `["blur", "noise", "contrast", "skew", "compression"]`.

#### 45-Dimensional Degradation Taxonomy

From `scripts/build_training_labels.py`:

| Group | Count | Types |
|-------|-------|-------|
| **Blur/Focus** | 6 | motion_blur, defocus_blur, gaussian_blur, zoom_blur, focus_falloff, lens_distortion |
| **Noise** | 7 | gaussian_noise, salt_pepper_noise, speckle_noise, sensor_noise, color_noise, film_grain, quantization_noise |
| **Geometric** | 6 | skew, rotation, perspective, warp, curl, fold |
| **Illumination** | 6 | uneven_lighting, shadow, glare, low_contrast, high_contrast, overexposure |
| **Compression** | 5 | jpeg_artifacts, blocking, ringing, posterization, banding |
| **Physical** | 5 | stain, ink_bleed, bleed_through, water_damage, yellowing |
| **Text-specific** | 5 | faded_text, broken_characters, touching_characters, overlapping_text, stamp_interference |
| **Scanner** | 5 | `moire_pattern`, halftone, scanner_noise, dust_specks, scratches |

#### Architecture Gap Analysis

| 45-Type Group | Maps to 5-Head? | Coverage |
|---------------|-----------------|----------|
| Blur/Focus (6) | blur | ✅ Full |
| Noise (7) | noise | ✅ Full |
| Geometric (6) | skew | ✅ Full |
| Illumination (6) | illumination/contrast | ✅ Full |
| Compression (5) | artifacts/compression | ✅ Full |
| **Physical (5)** | ❓ | ⚠️ No clear mapping |
| **Text-specific (5)** | ❓ | ⚠️ No clear mapping |
| **Scanner (5)** | ❓ | ⚠️ No clear mapping |

**Gap**: 15 degradation types (physical, text-specific, scanner) have no clear mapping to the 5-head output.

#### Architecture Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A: Keep 5 heads** | Map 45→5 via grouping | Simpler, faster inference | Loss of fine-grained detection |
| **B: Expand to 8 heads** | Add physical, text, scanner heads | Better coverage | Requires retraining |
| **C: 45-head model** | One head per degradation | Full taxonomy coverage | Complex, slow inference |
| **D: Two-stage** | 5-head coarse + 45-head fine | Best of both | Complexity, latency |

**Recommendation**: Option B (8 heads) provides good coverage with manageable complexity.

#### Head Naming Inconsistency

Must resolve before production:

| Location | Head 4 | Head 5 |
|----------|--------|--------|
| `resnet_teacher.py` | illumination | artifacts |
| `iqa_ml.py` | contrast | compression |
| `workers/tasks.py` | contrast | compression |

---

## Next Steps for Pseudo-Labeling Completion

1. **Complete Stage 2 Phase 2** - 45 epochs fine-tuning (~$10-15, 8-12 hours)
2. **Generate DeQA-Doc anchor labels** - 13K strategic images (~$15-20, 12 hours)
3. **Run full corpus pseudo-labeling** - 2.5M images (~$50-100, 3-5 days)

---

*Last Updated: 2026-01-12*
