---
owner: docs-team
purpose: Quick reference for training datasets - task-based lookup.
schema_type: common
status: active
tags:
- datasets
- training
- quick_reference
title: Training Dataset Quick Reference
---

> **Version**: 2.1.0
> **Last Updated**: 2026-02-23
> **Purpose**: Concise lookup for training dataset selection, status, and head group mapping
> **Audience**: LLM agents and ML engineers building the MobileNetV4 + SigLIP 2 pipeline
> **Architecture**: MobileNetV4-Conv-S (3 heads) + SigLIP 2 NAFlex (19 heads) + Docling Layout (pre-trained)
> **Full Details**: See [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md) | Individual files: [training/](training/)
> **Review Status**: ❌ NOT READY FOR PHASE 2 TRAINING — 5-model consensus review 2026-02-23; 6 of 11 acceptance criteria fail. See [CORPUS_OOD_REVIEW_REPORT.md](../planning/CORPUS_OOD_REVIEW_REPORT.md) and [UNIFIED_TRAINING_CORPUS.md](UNIFIED_TRAINING_CORPUS.md) Gap Registry.

---

## Quick Stats

| Metric | Count | Notes |
|--------|-------|-------|
| **Total Assembled Datasets** | 10 | One per training task area — matches [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |
| **Ready** | 1 | skew (90K) — orientation demoted to LATIN-BIASED pending Stream 4C rebuild |
| **Partial / In Progress** | 2 | resolution-quality (5.5K / 30K), iqa Phase 1 curated (~16K / 116K) |
| **Blocked** | 4 | handwriting (N_A sentinel defect), capture-method (3 classes near-zero), shadow (labeling script missing), warping (formula undefined) |
| **Arch Issue / Imbalanced** | 3 | orientation (Latin-biased), synth-multiscript-v3 (Arab 3.8× over cap), code-detection (code_reg must rename to code_cls) |
| **Total Images (all 10)** | ~513K | Across assembled datasets; synth-multiscript-v3 actual count is 190,485 (not 350K) |
| **Storage Location** | `E:\image_detection\03_training_datasets\` | Primary local storage |
| **OOD Images** | 0 acquired | Status as of 2026-02-21: 0 images acquired across all 9 OOD categories; target revised to 12,000–15,000 |

---

## Training Pipeline Overview

### Model Architecture

| Model | Params | Purpose | Inference | Training Step |
|-------|--------|---------|-----------|---------------|
| **MobileNetV4-Conv-S** | ~4M | Pre-correction gate: orientation (4-class), skew (regression), resolution quality (0-1) | ~3ms GPU / ~17ms CPU | Step 1 + Step 3 |
| **SigLIP 2 NAFlex** | ~88M | Full analysis: 19 heads across 5 groups (IQA, Script, Orient+Skew, Handwriting, Page Attrs) | ~50ms GPU | Step 2 |
| **Docling egret-xlarge** | ~55M | Layout detection (high accuracy, 23+ classes) | GPU | Pre-trained (no training) |
| **Docling heron** | ~14M | Layout detection (fast path) | CPU/GPU | Pre-trained (no training) |

### 3-Step Virtuous Training Cycle

> ⚠️ TRAINING GATE: This cycle cannot begin until ALL P0 blockers are resolved. Current state: 10 P0 blockers block training start (P0-1 through P0-10). See Gap Registry in [UNIFIED_TRAINING_CORPUS.md](UNIFIED_TRAINING_CORPUS.md) for full list and acceptance criteria.

| Step | Model | Datasets | Strategy |
|------|-------|----------|----------|
| **1. MobileNetV4 Bootstrap** | MobileNetV4-Conv-S | Orientation (50K), Skew (90K), Resolution Quality (30K) | Train on ground truth labels |
| **2. SigLIP 2 Multi-Task** | SigLIP 2 NAFlex | All 10 datasets (~503K) | Frozen backbone + 16 task heads (Kendall uncertainty weighting + PCGrad) |
| **3. MobileNetV4 Distillation** | MobileNetV4-Conv-S | SigLIP 2 soft labels + hard labels | KL-divergence distillation (T=3, alpha=0.7) |

> **Architecture**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) | **Optimization**: [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) | **Diversity**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md)

---

## 10 Assembled Datasets

Purpose-built datasets consumed by the training pipeline. Each corresponds to one training task area from [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md). See [Head ↔ Dataset Cross-Reference](#head--dataset-cross-reference) below for the full head-to-dataset mapping.

| # | Dataset | Images | Head Group | Status | HAR Score | P0 Blockers | Key Sources / Notes |
|---|---------|-------:|------------|--------|-----------|-------------|---------------------|
| 1 | **[orientation](#orientation)** | 50,000 | G3 / MNV4 H1 | ⚠️ LATIN-BIASED | N/A | 1 (Latin bias; orientation_ambiguous unlabeled) | <1% non-Latin images; fails diversity requirement; Stream 4C rebuild pending |
| 2 | **[skew](#skew)** | 90,412 | G3 / MNV4 H2 | ✅ READY | ✅ (pre-HAR) | 1 (G3-2 narrow-range dataset missing — separate deliverable) | 71K synth + 19K natural, GCS `skew_training/` |
| 3 | **[resolution-quality](#resolution-quality)** | 30,000 | G5 / MNV4 H3 + SIG-G5-5 | 🔄 IN PROGRESS — 18% | MNV4-H3: 26/100, SIG-G5-5: 39/100 | 4 (OHR-Bench labeling, RealDAE labeling, multi-DPI pipeline, SIG-G5-5 corrected-image assembly) | 5.5K/30K labeled; V2 Sauvola strategy required |
| 4 | **[iqa](#iqa)** | 116,000 (16K curated + 100K synthetic) | G1 (all 6 heads) | 🔄 IN PROGRESS — 4.7% | G1-1: 45, G1-2: 37, G1-3: 49, G1-4: 54, G1-5: 65, G1-6: 37 (avg ~47/100) | 13 (across 6 heads) | 5.5K/116K; Phase 2 synthetic pipeline not started |
| 5 | **[script-detection](#synth-multiscript-v3)** | 190,485 | G2 / SIG-G2-1 | ⚠️ IMBALANCED | N/A | 1 (Arab 3.8× cap violation) | Actual count 190,485 (not 350K); Arab 49K vs. ~13K cap; 17 scripts below floor; rebalancing required |
| 6 | **[handwriting](#handwriting)** | 60,000 | G4 (all 5 heads) | ❌ BLOCKED — N_A sentinel defect unresolved | G4-1: 32, G4-2: 21, G4-3: 25, G4-4: 26, G4-5: 14 (avg ~24/100) | 17 (across 5 heads; N_A sentinel is single biggest blocker) | N_A must encode as -1.0 (not 0.0); KHATT/CASIA-HWDB/IIIT-INDIC/HKR not yet acquired |
| 7 | **[capture-method](#capture-method)** | 50,000 | G5 / SIG-G5-1 | ❌ BLOCKED — 3 classes near-zero | 59/100 | 4 (3 missing classes + ADF/flatbed indistinguishable) | CAMERA_PROFESSIONAL, FAX, SCANNER_ADF each well below minimum; ADF heuristic labeling pending |
| 8 | **[shadow](#shadow)** | ~18,000 | G5 / SIG-G5-2 | ❌ BLOCKED — label_shadow_severity.py script not created | 28/100 | 3 (labeling script missing, L2 fields null, book gutter gap) | 0 real records; generation scripts complete; GPU VM execution required |
| 9 | **[warping](#warping)** | ~24,000 | G5 / SIG-G5-3 | ❌ BLOCKED — 3D-mesh derivation formula undefined | 17/100 (LOWEST) | 4 (formula undefined + prerequisite chain blocked) | 0 real records; `label_warping_severity.py` not run; HAR 17/100 lowest of all 22 heads |
| 10 | **[code-detection](#code-detection)** | 10,000 | G5 / SIG-G5-4 | ⚠️ ARCH ISSUE — code_reg must rename to code_cls | 55/100 | 5 (architecture rename + 4 validation gaps) | P0: head name `code_reg` must become `code_cls` (binary classification); 8,613 dry-run records |

> **Diversity spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) -- 14 dimensions, global split registry (SHA256-keyed).
>
> **HAR Score**: Head Assembly Readiness score from the systematic per-head review (5-model consensus 2026-02-23). Scores below 50/100 indicate critical structural gaps. N/A = not yet assessed under HAR framework. Full scores in [CORPUS_OOD_REVIEW_REPORT.md](../planning/CORPUS_OOD_REVIEW_REPORT.md).

---

## By Head Group

### G1 -- IQA (SigLIP 2)

**Feeds**: Assembled dataset #4 (iqa — 116K total, assembled in two phases)

**6 heads** (per [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)):

| Head ID | Head Name | Phase / Label Source |
|---------|-----------|----------------------|
| SIG-G1-1 | `blur_score` | Phase 2 synthetic — augmentation blur param |
| SIG-G1-2 | `noise_score` | Phase 2 synthetic — augmentation noise param |
| SIG-G1-3 | `contrast_score` | Phase 2 synthetic — augmentation contrast param |
| SIG-G1-4 | `skew_score` (severity 0–1) | Phase 2 synthetic — augmentation skew magnitude |
| SIG-G1-5 | `compression_score` | Phase 2 synthetic — augmentation JPEG quality param |
| SIG-G1-6 | `overall_quality` | Phase 1 curated — human MOS (DIQA-5000, OHR-Bench) |

| Phase | Images | Status | Label Type | Key Metric |
|-------|-------:|--------|------------|------------|
| **Phase 1: curated** | 16,000 | 🔄 In progress | Human MOS 1–5 (DIQA-5000); quality 0–100 (OHR-Bench) | SRCC target >0.65 vs human MOS |
| **Phase 2: synthetic** | 100,000 | 📋 Planned | Tier_0 pseudo-labels from synth-multiscript-v3 augmentation params | Coverage: 5 individual degradation dims |

**Strategy**: All 6 heads use regression (0–1). Phase 1 provides ground-truth labels for `overall_quality`; Phase 2 provides exact augmentation parameters as labels for the 5 individual degradation heads.

---

### G2 -- Script Detection (SigLIP 2)

**Feeds**: Assembled dataset #5 (script-detection — 190,485 GCS-confirmed)

| Dataset | Images | Status | Scripts | Languages |
|---------|-------:|--------|---------|-----------|
| **synth-multiscript-v3** | 190,485 | ⚠️ IMBALANCED — Arab 3.8× over cap (49K vs. ~13K); 17 scripts below floor; rebalancing required before training | 27 ISO 15924 | 198 OpenLID-v2 |

**Key metric**: >=90% accuracy across 27 scripts
**Strategy**: Multi-class classification with ISO 15924 script codes (108 classes via SigLIP 2)
**Note**: Generator stopped at 190,485 due to per-script pool exhaustion bug (350K was the target, not the actual count).

---

### G3 -- Orientation + Skew (SigLIP 2 + MobileNetV4)

**Feeds**: Assembled datasets #1 (orientation 50K) and #2 (skew 90K) — shared with MobileNetV4 H1/H2; SigLIP 2 G3 trains on same data for redundancy/teacher signal

| Dataset | Images | Status | Head | Label Type | Best Result |
|---------|-------:|--------|------|------------|-------------|
| **orientation** | 50,000 | ⚠️ LATIN-BIASED (rebuild pending) | MNV4 H1 | 4-class integer | orient_acc=99.5% (old config) |
| **skew** | 90,412 | ✅ READY | MNV4 H2 | 42-bin + residual float | val MAE=0.837, test MAE=0.956, SRCC=0.936 |

**MobileNetV4 Config**: conv_small @ 224px, 50 epochs, CPU 17.5ms
**Strategy**: Classification (orientation 4-class) + hybrid regression (42-bin + residual)

> ⚠️ NOTE (SIG-G3-2): The 90K skew dataset covers the full ±45° range and serves MNV4-H2 bootstrap. SIG-G3-2 requires a SEPARATE ±2° narrow-range dataset (~20K images) for sub-degree post-correction precision (MAE target <0.3°). The existing dataset residuals cluster around 0.956° — this target cannot be met without the narrow-range dataset. This is a distinct, unbuilt deliverable (Gap P0-1 in UNIFIED_TRAINING_CORPUS.md).

---

### G4 -- Handwriting Detection (SigLIP 2)

**Feeds**: Assembled dataset #6 (handwriting — 60K)

**5 heads** (per [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)):

| Head ID | Head Name | Type | Classes / Range |
|---------|-----------|------|-----------------|
| SIG-G4-1 | `presence_cls` | 5-class cls | NONE / SPARSE / MODERATE / SUBSTANTIAL / DOMINANT |
| SIG-G4-2 | `legibility_cls` | 6-class cls | N/A / EXCELLENT / GOOD / FAIR / POOR / ILLEGIBLE |
| SIG-G4-3 | `content_cls` | 7-class cls | n/a / numeric / alphanumeric / prose / cursive / mixed / specialized |
| SIG-G4-4 | `presence_reg` | regression | 0–1 (area ratio) |
| SIG-G4-5 | `legibility_reg` | regression | 0–1 (quality score) |

| Dataset | Images | Status | Label Source | Key Labels |
|---------|-------:|--------|-------------|------------|
| **handwriting** | 60,000 | 📋 Planned | HierText (word-level `handwritten` + `legible`), COCO-Text (`class` + `legibility`), IAM (657 writers) | All 5 head labels derived via harmonization |

**Strategy**: 5 heads total — 3 classification + 2 regression. HierText and COCO-Text provide word-level labels aggregated to page-level ratios. Label harmonization script: `scripts/harmonize_handwriting_labels.py`.

---

### G5 -- Page Attributes + Capture Method (SigLIP 2 + MobileNetV4)

**Feeds**: Assembled datasets #3 (resolution-quality 30K), #7 (capture-method 50K), #8 (shadow 15K), #9 (warping 20K), #10 (code-detection 10K)

**5 heads** (per [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)):

| Head ID | Head Name | Type | Dataset |
|---------|-----------|------|---------|
| SIG-G5-1 | `capture_cls` | 7-class cls | capture-method (#7) |
| SIG-G5-2 | `shadow_reg` | regression 0–1 | shadow (#8) |
| SIG-G5-3 | `warping_reg` | regression 0–1 | warping (#9) |
| SIG-G5-4 | `code_cls` ⚠️ P0: rename pending in SIGLIP2_MULTITASK_REQUIREMENTS.md and training script | binary cls (sigmoid + BCE) | code-detection (#10) |
| SIG-G5-5 | `resolution_quality_reg` | regression 0–1 | resolution-quality (#3) — validation head, primary is MNV4-H3 |

| Dataset | Images | Status | Head | Label Type |
|---------|-------:|--------|------|------------|
| **resolution-quality** | 30,000 | 🔄 IN PROGRESS — 18% (5.5K/30K) | MNV4-H3 + SIG-G5-5 (validation) | Char-height score 0–1, coarse bucket |
| **capture-method** | 50,000 | ❌ BLOCKED — 3 classes near-zero | SIG-G5-1 | 7-class: born-digital / scanner-flatbed / scanner-adf / camera-pro / camera-phone / fax / synthetic |
| **shadow** | ~18,000 | ❌ BLOCKED — label_shadow_severity.py script not created | SIG-G5-2 | Shadow severity regression 0–1 (paired GT) |
| **warping** | ~24,000 | ❌ BLOCKED — 3D-mesh derivation formula undefined | SIG-G5-3 | Warping severity regression 0–1 (paired GT) |
| **code-detection** | 10,000 | ⚠️ ARCH ISSUE — code_reg must rename to code_cls | SIG-G5-4 | Binary `has_code` cls + confidence 0–1 |

**Resolution quality pipeline**: PaddleOCR text detection + CC analysis, char-height-aware scoring. See [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md).

---

## Head ↔ Dataset ↔ OOD Cross-Reference

Three-way mapping of all 22 training heads: each head traces to exactly one training dataset and exactly one primary OOD evaluation category. Dataset numbers reference the [10 Assembled Datasets](#10-assembled-datasets) table. OOD categories reference [OOD_DATASET_CATALOG.md](OOD_DATASET_CATALOG.md).

| Head ID | Model | Group | Head Name | Task Type | Training Dataset | # | Dataset Status | OOD Category |
|---------|-------|-------|-----------|-----------|-----------------|---|----------------|--------------|
| **MNV4-H1** | MobileNetV4-Conv-S | — | `orientation` | 4-class cls | [orientation](#orientation) | 1 | ⚠️ LATIN-BIASED | OOD-Geometry |
| **MNV4-H2** | MobileNetV4-Conv-S | — | `skew` (angle °) | regression | [skew](#skew) | 2 | ✅ READY | OOD-Geometry |
| **MNV4-H3** | MobileNetV4-Conv-S | — | `resolution_quality` | regression | [resolution-quality](#resolution-quality) | 3 | 🔄 IN PROGRESS — 18% | OOD-Resolution |
| **SIG-G1-1** | SigLIP 2 | G1 | `blur_score` | regression | [iqa](#iqa) Phase 2 synthetic | 4 | 🔄 IN PROGRESS — 4.7% | OOD-Degradation |
| **SIG-G1-2** | SigLIP 2 | G1 | `noise_score` | regression | [iqa](#iqa) Phase 2 synthetic | 4 | 🔄 IN PROGRESS — 4.7% | OOD-Degradation |
| **SIG-G1-3** | SigLIP 2 | G1 | `contrast_score` | regression | [iqa](#iqa) Phase 2 synthetic | 4 | 🔄 IN PROGRESS — 4.7% | OOD-Degradation |
| **SIG-G1-4** | SigLIP 2 | G1 | `skew_score` (severity 0–1) ¹ | regression | [iqa](#iqa) Phase 2 synthetic | 4 | 🔄 IN PROGRESS — 4.7% | OOD-Degradation |
| **SIG-G1-5** | SigLIP 2 | G1 | `compression_score` | regression | [iqa](#iqa) Phase 2 synthetic | 4 | 🔄 IN PROGRESS — 4.7% | OOD-Degradation |
| **SIG-G1-6** | SigLIP 2 | G1 | `overall_quality` | regression | [iqa](#iqa) Phase 1 curated | 4 | 🔄 IN PROGRESS — 4.7% | OOD-Degradation |
| **SIG-G2-1** | SigLIP 2 | G2 | `script_code` (19 ML classes) | multi-class cls | [script-detection](#synth-multiscript-v3) | 5 | ⚠️ IMBALANCED | OOD-Script |
| **SIG-G3-1** | SigLIP 2 | G3 | `orientation_cls` (validation) ² | 4-class cls | [orientation](#orientation) | 1 | ⚠️ LATIN-BIASED | OOD-Geometry |
| **SIG-G3-2** | SigLIP 2 | G3 | `skew_reg` (validation, °) ² ³ | regression | [skew](#skew) | 2 | ✅ READY (broad range only) | OOD-Geometry |
| **SIG-G4-1** | SigLIP 2 | G4 | `presence_cls` | 5-class cls | [handwriting](#handwriting) | 6 | ❌ BLOCKED | OOD-Handwriting |
| **SIG-G4-2** | SigLIP 2 | G4 | `legibility_cls` | 6-class cls | [handwriting](#handwriting) | 6 | ❌ BLOCKED | OOD-Handwriting |
| **SIG-G4-3** | SigLIP 2 | G4 | `content_cls` | 7-class cls | [handwriting](#handwriting) | 6 | ❌ BLOCKED | OOD-Handwriting |
| **SIG-G4-4** | SigLIP 2 | G4 | `presence_reg` | regression | [handwriting](#handwriting) | 6 | ❌ BLOCKED | OOD-Handwriting |
| **SIG-G4-5** | SigLIP 2 | G4 | `legibility_reg` | regression | [handwriting](#handwriting) | 6 | ❌ BLOCKED | OOD-Handwriting |
| **SIG-G5-1** | SigLIP 2 | G5 | `capture_cls` (7 classes) | 7-class cls | [capture-method](#capture-method) | 7 | ❌ BLOCKED — 3 classes near-zero | OOD-Capture |
| **SIG-G5-2** | SigLIP 2 | G5 | `shadow_reg` | regression | [shadow](#shadow) | 8 | ❌ BLOCKED — labeling script missing | OOD-Degradation |
| **SIG-G5-3** | SigLIP 2 | G5 | `warping_reg` | regression | [warping](#warping) | 9 | ❌ BLOCKED — formula undefined | OOD-Capture |
| **SIG-G5-4** | SigLIP 2 | G5 | `code_cls` ⚠️ P0: rename pending in SIGLIP2_MULTITASK_REQUIREMENTS.md and training script | binary cls | [code-detection](#code-detection) | 10 | ⚠️ ARCH ISSUE | OOD-Code |
| **SIG-G5-5** | SigLIP 2 | G5 | `resolution_quality_reg` (validation) ² | regression | [resolution-quality](#resolution-quality) | 3 | 🔄 IN PROGRESS — 18% | OOD-Resolution |

> ¹ `skew_score` (G1) measures skew as a quality severity (0–1 degradation signal). `skew` (MNV4-H2 / SIG-G3-2) predicts the actual correction angle in degrees. Different constructs, same source dataset for G3. Label conflict between SIG-G1-4 and MNV4-H2 is a P0 blocker (P0-2) — derivation method for skew_score must be defined before multi-task training.
>
> ² Validation heads: SigLIP 2 G3 and G5-5 share datasets with MobileNetV4. SigLIP trains on the same data to provide teacher signal for future MobileNetV4 distillation and to cross-validate MobileNetV4 predictions at runtime.
>
> ³ SIG-G3-2 narrow-range gap: The 90K skew dataset covers full ±45° range and serves MNV4-H2. SIG-G3-2 requires a SEPARATE ±2° narrow-range dataset (~20K images) for sub-degree post-correction precision. This is a distinct, unbuilt deliverable (P0-1).

**Coverage check**: All 10 training datasets have at least one head assigned. All 22 heads have exactly one training dataset and one primary OOD category. All 9 OOD categories cover at least one head.

---

## OOD Evaluation Coverage

The holdout OOD dataset ([OOD_DATASET_CATALOG.md](OOD_DATASET_CATALOG.md)) has a revised target of **12,000–15,000 images** across 9 categories (up from original 4,700; revised by 5-model consensus 2026-02-23 due to statistical inadequacy). Current status: **0 images acquired** across all 9 OOD categories as of 2026-02-21. Each category stress-tests specific training datasets in conditions not seen during training. The `evaluation_pipeline_stage` field in the OOD registry controls which model(s) score each image.

> ⚠️ OOD STATUS: 0 images acquired. OOD evaluation is blocked until training corpus P0 gaps are resolved. All OOD results must be declared "directional only" until scaling to 12,000–15,000 images is complete (P1-3). Do not use directional results to pass/fail acceptance criteria.
>
> ⚠️ ENTROPY REJECTION INVALID: The current entropy ≥0.7 open-set rejection threshold is uncalibrated and insufficient for SigLIP 2 (P0-10). Must be replaced with temperature scaling + Energy Score (LogSumExp) before any OOD evaluation begins.
>
> **Reserved scripts** (never in training): Mongolian (Mong), Syriac (Syrc), Georgian (Geor)
> **Registry**: `metadata_registry/ood_registry.jsonl` — ground-truth schema covers all 22 head outputs
> **Dedup**: All OOD images verified against training manifests via SHA256 + pHash (Hamming ≤ 5)

| OOD Category | Target | Training Dataset(s) | # | Heads Evaluated | What It Covers |
|---|---:|---|---|---|---|
| **OOD-Script** | 600 | script-detection | 5 | SIG-G2-1 | Reserved scripts (Mong/Syrc/Geor); open-set rejection; Phase 2 preview scripts (Grek/Armn/Ethi); decorative font OOV |
| **OOD-Geometry** | 500 | orientation, skew | 1, 2 | MNV4-H1, MNV4-H2, SIG-G3-1, SIG-G3-2 | Symmetric docs (0°/180° disambiguation), extreme perspective (>30° tilt), Japanese TTB (labeled 0°) |
| **OOD-Capture** | 600 | capture-method, warping | 7, 9 | SIG-G5-1, SIG-G5-3 | Screen recaptures (moiré), ADF curl artifacts, 4th-gen photocopies, high-speed production scanners |
| **OOD-Degradation** | 800 | iqa, shadow | 4, 8 | SIG-G1-1, SIG-G1-2, SIG-G1-3, SIG-G1-4, SIG-G1-5, SIG-G1-6, SIG-G5-2 | Multiply-distorted (≥5 types), watermarks, book gutter shadow (gradient not in sd7k), binarized 1-bit |
| **OOD-Handwriting** | 500 | handwriting | 6 | SIG-G4-1, SIG-G4-2, SIG-G4-3, SIG-G4-4, SIG-G4-5 | KHATT Arabic (ILLEGIBLE class absent from training), CASIA CJK, IIIT-INDIC Devanagari, specialized content |
| **OOD-Resolution** | 500 | resolution-quality | 3 | MNV4-H3, SIG-G5-5 | Vector PDFs at 72/150/300 DPI (char-height paradox), bicubic-upscaled rasters (2× and 4×) |
| **OOD-Domain** | 500 | script-detection (secondary) | 5 | All 22 heads (robustness) | Non-English government forms, religious texts, thermal receipts — novel domain combinations |
| **OOD-Code** | 200 | code-detection | 10 | SIG-G5-4 | Source code screenshots (IDE/GitHub), mixed prose+code (arXiv, Jupyter), terminal output |
| **OOD-Mixed** | 700 | orientation, skew, iqa, shadow, warping | 1, 2, 4, 8, 9 | MNV4-H1, MNV4-H2, SIG-G1-1 through SIG-G1-6, SIG-G3-1, SIG-G3-2, SIG-G5-2, SIG-G5-3 | Cascade failures: Mongolian TTB + aged + perspective; CJK HW + gutter shadow; screen recapture + RTL |
| **Current Total (Plan)** | **4,700** | — | — | — | Per-category targets shown above; 0 acquired as of 2026-02-21 |
| **Revised Target** | **12,000–15,000** | — | — | — | 5-model consensus 2026-02-23: current plan is 2.5-3× below statistical minimum for per-head rigor |

### OOD ↔ Training Dataset Reverse Map

| # | Training Dataset | Heads Fed | Primary OOD | Secondary OOD | Key Stress Scenario |
|---|---|---|---|---|---|
| 1 | orientation | MNV4-H1, SIG-G3-1 | OOD-Geometry | OOD-Mixed | Symmetric 0°/180° ambiguity; cascade failure with TTB Mongolian |
| 2 | skew | MNV4-H2, SIG-G3-2 | OOD-Geometry | OOD-Capture | Extreme perspective (>30°); ADF page curl skew artifacts |
| 3 | resolution-quality | MNV4-H3, SIG-G5-5 | OOD-Resolution | — | Born-digital low-DPI vs. char-height paradox; upscale artifact detection |
| 4 | iqa | SIG-G1-1, G1-2, G1-3, G1-4, G1-5, G1-6 | OOD-Degradation | OOD-Mixed | ≥5 simultaneous distortion types; gutter shadow in compound stacks |
| 5 | script-detection | SIG-G2-1 | OOD-Script | OOD-Domain | Unseen script families; historical variants (Fraktur, Ottoman Arabic) |
| 6 | handwriting | SIG-G4-1, G4-2, G4-3, G4-4, G4-5 | OOD-Handwriting | OOD-Mixed | ILLEGIBLE class absent from training; non-Latin handwriting (Arab/CJK/Deva) |
| 7 | capture-method | SIG-G5-1 | OOD-Capture | OOD-Degradation | Screen recapture moiré (no training analog); 4th-gen photocopy noise cascade |
| 8 | shadow | SIG-G5-2 | OOD-Degradation | OOD-Mixed | Book gutter gradient profile not present in sd7k training data |
| 9 | warping | SIG-G5-3 | OOD-Capture | OOD-Mixed | ADF curl artifacts with concurrent skew; extreme perspective compound |
| 10 | code-detection | SIG-G5-4 | OOD-Code | — | Terminal output, mixed prose+code, novel code document types |

---

## Per-Dataset Details

### orientation

> **Quick Stats**: 50,000 images | 4-class balanced | 12,500 unique documents

| Attribute | Value |
|-----------|-------|
| **Purpose** | Orientation detection (0°, 90°, 180°, 270°) |
| **Total Images** | 50,000 |
| **Unique Documents** | 12,500 (×4 rotations each) |
| **Split** | Train: 35,000 (70%) / Val: 7,500 (15%) / Test: 7,500 (15%) |
| **Status** | ⚠️ LATIN-BIASED — non-Latin <1%; fails diversity requirement; Stream 4C rebuild pending |
| **Created** | 2026-01-25 |
| **Local Path** | `03_training_datasets/orientation/` |
| **Head** | MobileNetV4-Conv-S H1 (4-class orientation) |

**Source document composition**: DocLayNet (scientific 2.5K, financial 1.875K, legal 1K), TableBank/PubTabNet (2K), RVL-CDIP (2K), FUNSD/FUNSD+ (899), SROIE (1K), NIST SD-19 (1K), JSSODa (2K), Arabic OCR (500), Bhutan AFS (125)

**Critical**: Japanese vertical text labeled as 0° (not 270°). Document-level split before rotation prevents leakage.

> ⚠️ P0 GAP: Non-Latin documents constitute <1% of the current dataset. The ideal spec requires non-Latin ≥5% (MNV4-H1 requirement) and ≥40% of the synthetic v3 component. The Stream 4C rebuild targets this gap but execution is pending. Additionally, ~2,500 `orientation_ambiguous` samples (blank/figure-only/symmetric pages) must be labeled but are not yet present.

**Degradation**: 50% clean, 35% light (Gaussian blur, JPEG 75-90), 15% moderate (motion blur, perspective warp, shadows)

**Generation Script**: [scripts/prepare_orientation_dataset.py](../scripts/prepare_orientation_dataset.py)

**Full Documentation**: [training/orientation.md](training/orientation.md)

**Design Spec**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)

---

### skew

> **Quick Stats**: 90,412 images | 71K synthetic + 19K natural scans | 384×384 JPEG q90

| Attribute | Value |
|-----------|-------|
| **Purpose** | Skew estimation (42-bin classification + residual regression) |
| **Total Images** | 90,412 |
| **Synthetic** | 71,498 (derived from source datasets) |
| **Natural Scans** | 18,914 (13 datasets, classical ensemble labeled, conf ≥ 0.7) |
| **Split** | Train: 70,763 / Val: 9,025 / Test: 10,624 |
| **Skew Range** | ±45° (42 non-uniform bins) |
| **Status** | ✅ Ready |
| **Created** | 2026-02-11 |
| **Local Path** | `E:\03_training_datasets\skew\` |
| **GCS Path** | `gs://image_detection_b/skew_training/` |
| **Head** | MobileNetV4-Conv-S H2 (42-bin + residual) |

**Training results (best config: conv_small @ 224px, 50 epochs)**:

| Metric | Value |
|--------|-------|
| Val MAE | 0.837° (epoch 47) |
| Test MAE | 0.956° |
| SRCC | 0.936 |
| Orient Acc | 99.5% |
| CPU Inference | 17.5ms (p50=17.4ms, p95=18.8ms) |
| Within 0.5° | 70.8% |

**Key features**:

- Per-bin residual clamping: `max_residual` matches each bin's half-width (not a global constant)
- Natural scan source datasets: FUNSD, DocLayNet, SROIE, and 10 others
- Classical ensemble labeling: Hough + projection + gradient methods

**Generation Scripts**: `generate_skew_dataset.py`, `merge_skew_datasets.py`, `select_natural_scan_skew_subset.py`, `label_skew_classical.py`

---

### synth-multiscript-v3

> **Quick Stats**: 190,485 images (GCS-confirmed actual count — ⚠️ imbalanced distribution, rebalancing required) | 27 scripts | 198 languages | JPEG q95 | Layer 2 v2.3

| Attribute | Value |
|-----------|-------|
| **Purpose** | Pristine base for ALL synthetic training views (script, orientation, skew, IQA, etc.) |
| **Total Images** | 190,485 *(GCS-confirmed by live gsutil ls jpg count 2026-02-21; generator stopped due to per-script pool exhaustion bug — 350K was the target only, not the actual count; ⚠️ severe distribution imbalance: Arab 49K vs. ~13K budget; 17 scripts below target)* |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **Schema** | Layer 2 Enrichment v2.3.0 |
| **Status** | ⚠️ IMBALANCED — Arab 3.8× over cap (P0-6); rebalancing required before training |
| **Version** | 3.0 |
| **Output Path** | `synthetic_multiscript_v3/` (Unraid NFS) |
| **GCS Path** | `gs://image_detection_b/synth_multiscript_v3/` |
| **Head** | SigLIP 2 G2 (script detection, direct use) + source for all synthetic derived views |

**Key v3 design -- Pristine Base + Deferred Degradation**:

Images stored pristine (no degradation baked in). Degradation parameters recorded in metadata for reproducible replay. Derived views apply their own transforms at derivation time.

**Derived views from this base**:

| View | Count | Output Size | Head |
|------|-------|-------------|------|
| Script Detection | 190,485 (direct, GCS-confirmed actual count) — ⚠️ rebalancing required | Native DPI | SigLIP 2 G2 |
| Orientation | 50K | 224px | MNV4 H1 |
| Skew | 50-80K synth | 384px | MNV4 H2 |
| Resolution Quality | 30K | 224px | MNV4 H3 |
| IQA Pseudo-Labels | 100K | 384px | SigLIP 2 G1 |
| Shadow | 15K | 384px | SigLIP 2 G5 |
| Warping | 20K | 384px | SigLIP 2 G5 |

**v3-specific features**:

- CJK vertical text: Jpan 30% TTB, Hans/Hant 10% TTB
- English 40% secondary script weighting in multi-script compositions
- Skew range expanded to ±22° (from ±10° in v2)
- Generation provenance: SHA256, degradation seeds, font families per image
- Global split registry (SHA256-keyed, prevents cross-dataset leakage)
- Color modes: 60% color, 30% grayscale, 10% binarized
- Document age: 80% modern, 15% aged, 5% historical

**Validation results (2026-02-15)**: CJK TTB PASS, split registry PASS (345,638 entries), schema 100% v2.3.0

**Generation Script**: [scripts/generate_base_dataset_v3.py](../scripts/generate_base_dataset_v3.py)

**Validation Script**: [scripts/validate_base_dataset_v3.py](../scripts/validate_base_dataset_v3.py)

**Full Documentation**: [training/synth-multiscript-v3.md](training/synth-multiscript-v3.md)

**Deprecated Versions**: v1.0 (27K) DELETED, v2.0 (250K) DELETED

---

### resolution-quality

> **Quick Stats**: 30,000 target | 5,500 labeled (DIQA-5000) | char-height-aware scoring

| Attribute | Value |
|-----------|-------|
| **Purpose** | Resolution quality scoring for MobileNetV4 head |
| **Target Size** | 30,000 (stratified across 7 DPI tiers) |
| **Labeled So Far** | 5,499 (DIQA-5000 complete) |
| **Status** | 🔄 In Progress |
| **Head** | MobileNetV4-Conv-S H3 (resolution quality score 0-1) |
| **Next Sources** | OHR-Bench (8.5K), RealDAE (1.2K) |

**Pipeline**: PaddleOCR v2 text detection + connected-component analysis (two-stage char-height measurement)

**Label schema**: `character_height_px`, `resolution_quality_score` (0-1), `coarse_bucket` (needs_major_upscale / needs_light_upscale / optimal / good / oversized)

**Labeling script**: `scripts/label_resolution_quality.py` (dataset-agnostic)

**Integration script**: `scripts/integrate_resolution_quality.py` (merges into L2 metadata)

**Strategy**: Sauvola binarization (k=0.2) + horizontal projection profiles; script-aware ensemble (CJK: 0.7 proj/0.3 CC, Latin: 0.3 proj/0.7 CC). See [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md).

---

### iqa

> **Quick Stats**: 116,000 target (16K curated + 100K synthetic) | 6 regression heads | Two-phase assembly

| Attribute | Value |
|-----------|-------|
| **Purpose** | IQA model training — all 6 SigLIP 2 G1 heads |
| **Total Target** | 116,000 (16K Phase 1 + 100K Phase 2) |
| **Status** | 🔄 Phase 1 in progress / Phase 2 planned |
| **Heads** | SIG-G1-1 through SIG-G1-6 (blur, noise, contrast, skew_severity, compression, overall_quality) |
| **Phase 1 Sources** | DIQA-5000 (5.5K, human MOS 1–5), OHR-Bench (8.5K, quality 0–100) |
| **Phase 2 Sources** | synth-multiscript-v3 (100K subset, diverse DPI/quality tiers) |

**Phase 1 — Curated (16K): trains `overall_quality` head (SIG-G1-6)**

- Label type: Human MOS + VLM scoring (tier_2)
- IQA pilot results (200 images, Opus 4.6 VLM): SRCC overall=0.53 (non-rotated), SRCC sharpness=0.58
- Decision: Proceed with revised prompt v2.0 (orientation-independent scoring + finer granularity)
- Gate: SRCC >0.60 required before scaling to 2–5K
- Results: `results/iqa_vlm_labeling/`

**Phase 2 — Synthetic (100K): trains individual degradation heads (SIG-G1-1 through SIG-G1-5)**

- Label type: Tier_0 exact — augmentation parameters ARE the labels (confidence=1.0)
- Derivation: 100K subset of synth-multiscript-v3 with recorded degradation params
- 5 head labels: blur (Gaussian sigma), noise (σ level), contrast (CLAHE clip), skew (rotation magnitude), compression (JPEG quality)
- Training order: Phase 2 pre-trains degradation heads → Phase 1 fine-tunes overall_quality

---

### handwriting

> **Quick Stats**: 60,000 target | 5-head graded assessment | ❌ BLOCKED

| Attribute | Value |
|-----------|-------|
| **Purpose** | Handwriting detection and graded severity assessment |
| **Target Size** | 60,000 |
| **Status** | ❌ BLOCKED — N_A sentinel defect unresolved; P0 prerequisites (KHATT, CASIA-HWDB, IIIT-INDIC, HKR) not acquired |
| **Heads** | SIG-G4-1 through SIG-G4-5 (presence_cls, legibility_cls, content_cls, presence_reg, legibility_reg) |
| **Key Sources** | HierText (word-level `handwritten` + `legible`), COCO-Text (`class` + `legibility`), IAM (657 writers) |

**Graded label strategy**: HierText and COCO-Text provide word-level labels aggregated to page-level ratios. Harmonization script: `scripts/harmonize_handwriting_labels.py` (dry-run: 38,967 records, 9,289 positive).

> ⚠️ P0 SENTINEL DEFECT: N_A values must be encoded as **-1.0** (with masked loss during training), NOT 0.0 (which maps to "illegible" and corrupts regression heads G4-2 and G4-5). This must be resolved in the label schema before assembling the handwriting dataset.
>
> ⚠️ P0 ILLEGIBLE CLASS VOID: 0 ILLEGIBLE handwriting samples exist across all current datasets. Both SIG-G4-2 and SIG-G4-5 require ≥5,000 ILLEGIBLE samples. Training must not begin without them.
>
> ⚠️ P0 PREREQUISITES: KHATT (Arabic cursive), CASIA-HWDB (CJK handwriting), IIIT-INDIC (Devanagari), and HKR (Cyrillic) are not yet acquired. Without these four datasets, the handwriting heads cannot reliably classify non-Latin scripts.

---

### capture-method

> **Quick Stats**: 50,000 target | 7-class capture modality | ❌ BLOCKED

| Attribute | Value |
|-----------|-------|
| **Purpose** | Capture method classification for degradation-aware routing |
| **Target Size** | 50,000 |
| **Status** | ❌ BLOCKED — 3 classes near-zero: CAMERA_PROFESSIONAL, FAX, and SCANNER_ADF each well below minimum targets; ADF/flatbed indistinguishable without heuristic labeling |
| **Head** | SIG-G5-1 (`capture_cls`, 7-class) |
| **Classes** | BORN_DIGITAL / SCANNER_FLATBED / SCANNER_ADF / CAMERA_PROFESSIONAL / CAMERA_SMARTPHONE / FAX / SYNTHETIC |
| **Key Sources** | doclaynet (📄 born-digital), rvl-cdip (🖨️ scanner), smartdoc-qa/midv500 (📱 camera), synth-multiscript-v3 (🎨 synthetic) |
| **HAR Score** | 59/100 |

> ⚠️ P0 GAPS: SCANNER_ADF requires manual verification of 100 samples before label propagation (ADF heuristic: edge-parallel dark bands, systematic micro-skew). FAX heuristic labeling pending. CAMERA_PROFESSIONAL (MIDV500, SmartDoc-QA) source labeling pending. Modern CIS flatbed ≥1,500 samples (Gap 8) unresolved — RVL-CDIP/Tobacco800/NIST SD-2/SD-6 are 1990s CCD technology only.

---

### shadow

> **Quick Stats**: ~18,000 target | Paired GT (shadow / clean) | ❌ BLOCKED

| Attribute | Value |
|-----------|-------|
| **Purpose** | Shadow detection and severity regression |
| **Target Size** | ~18,000 (revised from 15,000; per UNIFIED_TRAINING_CORPUS.md §3.8) |
| **Current State** | 0 assembled — `label_shadow_severity.py` script not yet created; L2 `shadow_severity` fields null |
| **Status** | ❌ BLOCKED — labeling script not created; 0 real records; GPU VM execution required |
| **Head** | SIG-G5-2 (`shadow_reg`, regression 0–1) |
| **Key Sources** | sd7k (7.2K paired), wsrd (4.5K paired), v3 Augraphy synthetic overlays |
| **HAR Score** | 28/100 |

**Label type**: Paired GT (shadow input / clean reference) — shadow severity regression 0–1

> ⚠️ P0 GAPS: (1) `label_shadow_severity.py` script must be created and run on GPU VM before any real records exist. (2) L2 `shadow_severity` fields currently null for sd7k and wsrd. (3) Book gutter shadow gap (Gap 5): sd7k is flat-document only; book spine shadows (~1,000 samples) required — do not mark shadow training complete without them. SSIM-based severity labels are permanently invalid (5-model consensus).

---

### warping

> **Quick Stats**: ~24,000 target | Paired GT (warped / flat) | ❌ BLOCKED

| Attribute | Value |
|-----------|-------|
| **Purpose** | Document warping detection and severity regression |
| **Target Size** | ~24,000 (revised from 20,000; per UNIFIED_TRAINING_CORPUS.md §3.9) |
| **Current State** | 0 assembled — 3D-mesh derivation formula undefined; `label_warping_severity.py` not yet run; 0 real records |
| **Status** | ❌ BLOCKED — 3D-mesh derivation formula undefined + labeling script not run; HAR 17/100 (LOWEST of all 22 heads) |
| **Head** | SIG-G5-3 (`warping_reg`, regression 0–1) |
| **Key Sources** | warpdoc (1K, 6 warp types), anyphotodoc6300 (6.3K), docalign12k (12K at 0.3× weight), docreal (200), drccbi (325) |
| **HAR Score** | 17/100 (LOWEST of all 22 heads) |

**Label type**: Paired GT (warped input / flat reference) — warping severity regression 0–1

> ⚠️ P0 GAPS: (1) 3D-mesh warping severity derivation formula is undefined — must be specified before `label_warping_severity.py` can be written. (2) `label_warping_severity.py` script not yet run on GPU VM. (3) L2 `warping_severity` fields null for anyphotodoc6300, warpdoc, docalign12k. (4) Blocked prerequisite chain: formula → script → GPU run → L2 fields → real records. SSIM-based severity labels are permanently invalid (5-model consensus).

---

### code-detection

> **Quick Stats**: 10,000 target | 5K positive + 5K negative | Code vs. non-code | ⚠️ ARCH ISSUE

| Attribute | Value |
|-----------|-------|
| **Purpose** | Code block detection and confidence scoring in document pages |
| **Target Size** | 10,000 |
| **Status** | ⚠️ ARCH ISSUE — head is named `code_reg` but training signal is boolean (has_code); must be renamed `code_cls` with sigmoid + BCE loss before training |
| **Head** | SIG-G5-4 (`code_cls` — ⚠️ P0: currently named `code_reg` in SIGLIP2_MULTITASK_REQUIREMENTS.md and training scripts; rename pending) |
| **Key Sources (positive)** | GitHub rendered code snippets (8 languages, PIL+Pygments), multimodal_textbook pages with `has_code=True` |
| **Key Sources (negative)** | DocLayNet prose-only pages, multimodal_textbook pages with `has_code=False` |
| **HAR Score** | 55/100 |

**Generation approach**: PIL + Pygments renderer; 8 languages; dark/light themes; 4 DPI configs (72/150/300/600); "screenshot" and "printed-code-in-doc" styles.

**Generation script**: `scripts/generate_code_detection_dataset.py` (dry-run complete: 8,613 records — 5K pos + 3.6K neg; actual image generation on GPU VM pending)

**Label type**: Binary `has_code` bool + continuous confidence 0–1 derived from code pixel area ratio.

> ⚠️ P0 ARCHITECTURAL FIX REQUIRED: Do not train until `code_reg` is renamed to `code_cls` in all of: `SIGLIP2_MULTITASK_REQUIREMENTS.md`, `modal/train_siglip2_multitask.py`, and the head registry. The head uses boolean supervision — regression (MSE) is the wrong loss function; binary classification (sigmoid + BCE) is required.

---

## Ground Truth Provenance

Training datasets use three label provenance tiers:

| Tier | Label Type | Confidence | Datasets |
|------|-----------|------------|---------|
| **tier_0 (exact)** | Synthetic exact -- augmentation parameters ARE the labels | 1.0 | synth-multiscript-v3 (orientation, skew, resolution quality, IQA pseudo-labels) |
| **tier_1 (classical ensemble)** | Multi-method heuristics with confidence filter | 0.7-0.95 | skew (natural scans: Hough + projection + gradient, conf ≥ 0.7) |
| **tier_2 (human / VLM)** | Human MOS or VLM-scored with validation | 0.6-0.85 | iqa Phase 1 curated (DIQA-5000 human MOS, OHR-Bench quality scores, VLM IQA pilot) |

**Global split registry**: SHA256-keyed JSONL in `splits.jsonl` -- prevents the same base image appearing in both train and test across derived views. Critical for synth-multiscript-v3 derived datasets.

---

## Critical Training Filters

### Split Leakage Prevention

| Risk | Mitigation |
|------|------------|
| Same document in train + test (orientation) | Document-level split BEFORE rotation; `source_document_id` keyed |
| Same base image in synth train + resolution-quality test | Global split registry (SHA256-keyed); all derived views share the same registry |
| Natural scan sources overlap with eval benchmarks | Natural scans in skew drawn from training splits of source datasets only |

### Label Provenance Requirements

**Never use unlabeled data as training targets**. All training labels must have a declared `label_provenance`:

- `tier_0_exact` -- synthetic parameters (highest confidence)
- `classical_ensemble` -- multi-method classical detection (requires conf ≥ 0.7)
- `vlm_scored` -- VLM annotation (requires SRCC > 0.60 against human MOS)
- `human_mos` -- human mean opinion scores (gold standard)

### Special Handling

**Pristine base -- no baked-in degradation** (synth-multiscript-v3): All degradation applied at derivation time per derived view. Do not apply degradation to the base images.

**Per-bin residual clamping** (skew): `max_residual` must match each bin's individual half-width, NOT a global constant. Global clamping causes systematic error at bin boundaries.

**QAT state_dict mismatch** (skew modal training): `prepare_qat()` adds fake-quant keys. Load pre-QAT `best_model.pt` into fresh model for evaluation; use `strict=False` for resume.

**Vertical Japanese text** (orientation): JSSODa top-to-bottom text labeled as 0° (upright), NOT 270°. Ensures the model treats vertical CJK as a valid upright state.

---

## Quick Selection Guide

**"I need to train orientation detection"**
→ Use `orientation` (50K images, 4-class balanced, ✅ Ready)

**"I need to train skew estimation"**
→ Use `skew` (90K images, 42-bin + residual, ✅ Ready)

**"I need to train script detection"**
→ Use `synth-multiscript-v3` (190,485 GCS-confirmed actual count, 27 scripts — ⚠️ IMBALANCED: Arab 49K vs. ~13K cap (3.8×); 17 scripts below floor; rebalancing required before training — P0-6)

**"I need resolution quality training data"**
→ Derive from `synth-multiscript-v3` (30K target; 5.5K from DIQA-5000 labeled so far)

**"I need IQA pseudo-labels for pre-training"**
→ Derive from `synth-multiscript-v3` (100K target, tier_0 exact labels)

**"I need handwriting / capture / shadow / warping data"**
→ See [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) for assembly plans (all Planned)

---

## Status Legend

| Status | Meaning |
|--------|---------|
| ✅ READY | Dataset complete, validated, and uploaded to GCS; all P0 blockers resolved |
| ⚠️ LATIN-BIASED | Dataset exists but fails diversity requirements; rebuild required before training |
| ⚠️ IMBALANCED | Dataset exists but class distribution violates corpus spec constraints; rebalancing required |
| ⚠️ ARCH ISSUE | Architecture or naming defect must be fixed before training begins |
| 🔄 IN PROGRESS | Labels partially assembled; progress percentage shown |
| ❌ BLOCKED | Hard blocker(s) prevent dataset assembly; training must not begin |
| 📋 Planned | Design spec exists; no generation started (legacy — now replaced by more specific statuses above) |

---

## References

### Dataset Documentation

- **Individual training dataset files**: [training/](training/) -- per-dataset deep documentation
  - [training/orientation.md](training/orientation.md) -- source composition, label schema, directory structure
  - [training/synth-multiscript-v3.md](training/synth-multiscript-v3.md) -- script coverage, derived views, validation
- **Full Catalog**: [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md) -- deep technical details for all datasets
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) -- 57 source datasets, audit grades, label provenance

### Architecture & Planning

- **SigLIP 2 Requirements**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) -- 19-head architecture (G1×6, G2×1, G3×2, G4×5, G5×5), head groups G1–G5
- **Training Optimization**: [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) -- ILP allocation, PCGrad, phased head training
- **Dataset Diversity**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) -- 10 dataset specs, 14 diversity dimensions, global split registry
- **MobileNetV4 Design**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) -- orientation + skew + resolution design
- **Resolution Quality V2**: [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md) -- char-height measurement pipeline

### Training Infrastructure

- **Modal Training**: [docs/reference/MODAL_QUICK_REFERENCE.md](../reference/MODAL_QUICK_REFERENCE.md) -- GPU training workflow
- **Training Script (Skew)**: `modal/train_skew_estimator.py` -- MobileNetV4 + 3-head training
- **GCS Bucket**: `gs://image_detection_b/` -- training dataset mirror

---

**Last Updated**: 2026-02-23
**Maintained By**: Data team
**Review Source**: [CORPUS_OOD_REVIEW_REPORT.md](../planning/CORPUS_OOD_REVIEW_REPORT.md) (5-model consensus, 2026-02-23)
**Master Spec**: [UNIFIED_TRAINING_CORPUS.md](UNIFIED_TRAINING_CORPUS.md) (authoritative ideal-state specification)
