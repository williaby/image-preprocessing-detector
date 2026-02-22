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

> **Version**: 2.0.0
> **Last Updated**: 2026-02-21
> **Purpose**: Concise lookup for training dataset selection, status, and head group mapping
> **Audience**: LLM agents and ML engineers building the MobileNetV4 + SigLIP 2 pipeline
> **Architecture**: MobileNetV4-Conv-S (3 heads) + SigLIP 2 NAFlex (16 heads) + Docling Layout (pre-trained)
> **Full Details**: See [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md) | Individual files: [training/](training/)

---

## Quick Stats

| Metric | Count | Notes |
|--------|-------|-------|
| **Total Assembled Datasets** | 10 | Purpose-built from source datasets |
| **Ready** | 2 | orientation (50K), skew (90K) |
| **Partial / In Progress** | 3 | synth-multiscript-v3 (350K complete but imbalanced — generator bug), resolution quality (5.5K / 30K), IQA curated (partial) |
| **Planned** | 5+ | IQA Synthetic, Handwriting, Capture, Shadow, Warping, Code |
| **Total Images (all 10)** | ~503K | Across assembled datasets; synth-multiscript-v3 is the base for all synthetic views |
| **Storage Location** | `E:\image_detection\03_training_datasets\` | Primary local storage |

---

## Training Pipeline Overview

### Model Architecture

| Model | Params | Purpose | Inference | Training Step |
|-------|--------|---------|-----------|---------------|
| **MobileNetV4-Conv-S** | ~4M | Pre-correction gate: orientation (4-class), skew (regression), resolution quality (0-1) | ~3ms GPU / ~17ms CPU | Step 1 + Step 3 |
| **SigLIP 2 NAFlex** | ~88M | Full analysis: 16 heads across 5 groups (IQA, Script, Orient+Skew, Handwriting, Page Attrs) | ~50ms GPU | Step 2 |
| **Docling egret-xlarge** | ~55M | Layout detection (high accuracy, 23+ classes) | GPU | Pre-trained (no training) |
| **Docling heron** | ~14M | Layout detection (fast path) | CPU/GPU | Pre-trained (no training) |

### 3-Step Virtuous Training Cycle

| Step | Model | Datasets | Strategy |
|------|-------|----------|----------|
| **1. MobileNetV4 Bootstrap** | MobileNetV4-Conv-S | Orientation (50K), Skew (90K), Resolution Quality (30K) | Train on ground truth labels |
| **2. SigLIP 2 Multi-Task** | SigLIP 2 NAFlex | All 10 datasets (~503K) | Frozen backbone + 16 task heads (Kendall uncertainty weighting + PCGrad) |
| **3. MobileNetV4 Distillation** | MobileNetV4-Conv-S | SigLIP 2 soft labels + hard labels | KL-divergence distillation (T=3, alpha=0.7) |

> **Architecture**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) | **Optimization**: [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) | **Diversity**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md)

---

## All 10 Assembled Datasets

Purpose-built datasets consumed by the training pipeline. Each assembled or derived from source datasets.

| # | Dataset | Images | Head Group | Status | Key Sources / Notes |
|---|---------|-------:|------------|--------|---------------------|
| 1 | **[orientation](#orientation)** | 50,000 | G3 / MNV4 H1 | ✅ Ready | 4-class (0/90/180/270), synth + natural, document-level split |
| 2 | **[skew](#skew)** | 90,412 | G3 / MNV4 H2 | ✅ Ready | 71K synth + 19K natural, GCS `skew_training/` |
| 3 | **[resolution-quality](#resolution-quality)** | 30,000 | G5 / MNV4 H3 | 🔄 5.5K done | Char-height-aware (0-1), derived from synth-multiscript-v3 + PaddleOCR pipeline |
| 4 | **[iqa-curated](#iqa-curated)** | 16,000 | G1 | 🔄 In progress | DIQA-5000 + OHR-Bench + DocLayNet curated subsets |
| 5 | **[iqa-synthetic](#iqa-synthetic)** | 100,000 | G1 | 📋 Planned | Derived from synth-multiscript-v3; multi-degradation, pseudo-labels from augmentation params |
| 6 | **[script-detection](#synth-multiscript-v3)** | 350,012 | G2 | ✅ Complete — ⚠️ Imbalanced (generator bug; Arab 49K, 17 scripts below target) | synth-multiscript-v3 used directly; 27 scripts, 198 languages; rebalancing required |
| 7 | **[handwriting](#handwriting)** | 60,000 | G4 | 📋 Planned | HierText + COCO-Text + IAM derived labels |
| 8 | **[capture-method](#capture-method)** | 50,000 | G5 | 📋 Planned | Born-digital / scanner / camera / synthetic |
| 9 | **[shadow](#shadow)** | 15,000 | G5 | 📋 Planned | sd7k + wsrd + doc3d synthetic shadows |
| 10 | **[warping](#warping)** | 20,000 | G5 | 📋 Planned | warpdoc + anyphotodoc + doc3d dewarping |

> **Code detection** (10K) planned but not yet designed or assembled.
> **Diversity spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) -- 14 dimensions, global split registry (SHA256-keyed).

---

## By Head Group

### G1 -- IQA (SigLIP 2)

**Feeds**: Assembled datasets #4 (IQA Curated 16K) and #5 (IQA Synthetic 100K)

| Dataset | Images | Status | Label Type | Key Metric |
|---------|-------:|--------|------------|------------|
| **iqa-curated** | 16,000 | In progress | Human MOS + quality scores | SRCC target >0.65 |
| **iqa-synthetic** | 100,000 | Planned | Pseudo-labels from augmentation params (tier_0) | Coverage: 8 IQA dimensions |

**Dimensions**: blur, noise, compression, ink_degradation, paper_degradation, geometric_distortion, bleed_through, overall_quality (0-1)
**Strategy**: Regression (IQA scores) + binary classification (8 degradation flags)

---

### G2 -- Script Detection (SigLIP 2)

**Feeds**: Assembled dataset #6 (Script Detection 350K GCS-confirmed)

| Dataset | Images | Status | Scripts | Languages |
|---------|-------:|--------|---------|-----------|
| **synth-multiscript-v3** | 350,012 | ✅ Complete — ⚠️ Imbalanced (generator bug; rebalancing required before training) | 27 ISO 15924 | 198 OpenLID-v2 |

**Key metric**: >=90% accuracy across 27 scripts
**Strategy**: Multi-class classification with ISO 15924 script codes (108 classes via SigLIP 2)

---

### G3 -- Orientation + Skew (SigLIP 2 + MobileNetV4)

**Feeds**: Assembled datasets #1 (Orientation 50K) and #2 (Skew 90K)

| Dataset | Images | Status | Head | Label Type | Best Result |
|---------|-------:|--------|------|------------|-------------|
| **orientation** | 50,000 | ✅ Ready | MNV4 H1 | 4-class integer | orient_acc=99.5% |
| **skew** | 90,412 | ✅ Ready | MNV4 H2 | 42-bin + residual float | val MAE=0.837, test MAE=0.956, SRCC=0.936 |

**MobileNetV4 Config**: conv_small @ 224px, 50 epochs, CPU 17.5ms
**Strategy**: Classification (orientation 4-class) + hybrid regression (42-bin + residual)

---

### G4 -- Handwriting Detection (SigLIP 2)

**Feeds**: Assembled dataset #7 (Handwriting 60K)

| Dataset | Images | Status | Label Source | Key Labels |
|---------|-------:|--------|-------------|------------|
| **handwriting** | 60,000 | Planned | HierText (word-level `handwritten`), COCO-Text (`class`), IAM (transcriptions) | has_handwriting, handwriting_ratio, handwriting_confidence |

**Strategy**: 3 heads: has_handwriting (binary), handwriting_ratio (0-1 regression), handwriting_confidence (regression)

---

### G5 -- Page Attributes + Capture Method (SigLIP 2 + MobileNetV4)

**Feeds**: Assembled datasets #3 (Resolution Quality 30K), #8 (Capture 50K), #9 (Shadow 15K), #10 (Warping 20K)

| Dataset | Images | Status | MNV4/SigLIP | Label Type |
|---------|-------:|--------|-------------|------------|
| **resolution-quality** | 30,000 | 5.5K done | MNV4 H3 | Char-height score 0-1, coarse bucket |
| **capture-method** | 50,000 | Planned | SigLIP G5 | 4-class: born-digital/scanner/camera/synthetic |
| **shadow** | 15,000 | Planned | SigLIP G5 | Shadow severity regression |
| **warping** | 20,000 | Planned | SigLIP G5 | Warping severity regression |

**Resolution quality pipeline**: PaddleOCR text detection + CC analysis, char-height-aware scoring. See [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md).

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
| **Status** | ✅ Ready |
| **Created** | 2026-01-25 |
| **Local Path** | `03_training_datasets/orientation/` |
| **Head** | MobileNetV4-Conv-S H1 (4-class orientation) |

**Source document composition**: DocLayNet (scientific 2.5K, financial 1.875K, legal 1K), TableBank/PubTabNet (2K), RVL-CDIP (2K), FUNSD/FUNSD+ (899), SROIE (1K), NIST SD-19 (1K), JSSODa (2K), Arabic OCR (500), Bhutan AFS (125)

**Critical**: Japanese vertical text labeled as 0° (not 270°). Document-level split before rotation prevents leakage.

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

> **Quick Stats**: 350,012 images (✅ GCS-confirmed total — ⚠️ imbalanced distribution, rebalancing required) | 27 scripts | 198 languages | JPEG q95 | Layer 2 v2.3

| Attribute | Value |
|-----------|-------|
| **Purpose** | Pristine base for ALL synthetic training views (script, orientation, skew, IQA, etc.) |
| **Total Images** | 350,012 *(GCS-confirmed by live gsutil ls jpg count 2026-02-21; generator target met — ⚠️ severe distribution imbalance due to generator bug; Arab 49K, 17 scripts below 12,963 target)* |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **Schema** | Layer 2 Enrichment v2.3.0 |
| **Status** | ✅ Complete — ⚠️ Imbalanced distribution (rebalancing needed before training) |
| **Version** | 3.0 |
| **Output Path** | `synthetic_multiscript_v3/` (Unraid NFS) |
| **GCS Path** | `gs://image_detection_b/synth_multiscript_v3/` |
| **Head** | SigLIP 2 G2 (script detection, direct use) + source for all synthetic derived views |

**Key v3 design -- Pristine Base + Deferred Degradation**:

Images stored pristine (no degradation baked in). Degradation parameters recorded in metadata for reproducible replay. Derived views apply their own transforms at derivation time.

**Derived views from this base**:

| View | Count | Output Size | Head |
|------|-------|-------------|------|
| Script Detection | 350K (direct, GCS-confirmed) — ⚠️ rebalancing required | Native DPI | SigLIP 2 G2 |
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

### iqa-curated

> **Quick Stats**: 16,000 target | Human MOS + expert quality scores

| Attribute | Value |
|-----------|-------|
| **Purpose** | IQA model training with human-labeled quality ground truth |
| **Target Size** | 16,000 |
| **Status** | 🔄 In Progress |
| **Head** | SigLIP 2 G1 |
| **Key Sources** | DIQA-5000 (5.5K, human MOS 1-5), OHR-Bench (8.5K, quality 0-100), DocLayNet curated |

**IQA pilot results** (Phase 1 complete, 200 images, Opus 4.6 VLM):

- SRCC overall: 0.39 (all images), 0.53 (non-rotated) -- below 0.65 target
- SRCC sharpness: 0.58
- Decision: Proceed with revised prompt v2.0 (orientation-independent scoring + finer granularity)
- Target: SRCC >0.60 before scaling to 2-5K

**Results**: `results/iqa_vlm_labeling/`

---

### iqa-synthetic

> **Quick Stats**: 100,000 target | Derived from synth-multiscript-v3 | Pseudo-labels

| Attribute | Value |
|-----------|-------|
| **Purpose** | IQA pre-training with synthetic pseudo-labels (tier_0 exact) |
| **Target Size** | 100,000 |
| **Status** | 📋 Planned |
| **Head** | SigLIP 2 G1 (pre-training, before iqa-curated fine-tune) |
| **Derivation** | 100K subset of synth-multiscript-v3, diverse DPI/quality tiers |

**Label provenance**: tier_0 (synthetic exact -- augmentation parameters ARE the labels; confidence=1.0)

**8 IQA dimensions**: blur, noise, compression, ink_degradation, paper_degradation, geometric_distortion, bleed_through, overall_quality

---

### handwriting

> **Quick Stats**: 60,000 target | 3-head graded assessment

| Attribute | Value |
|-----------|-------|
| **Purpose** | Handwriting detection with graded severity |
| **Target Size** | 60,000 |
| **Status** | 📋 Planned |
| **Head** | SigLIP 2 G4 (has_handwriting, handwriting_ratio, handwriting_confidence) |
| **Key Sources** | HierText (word-level `handwritten` boolean), COCO-Text (class + legibility), IAM (657 writers) |

**Graded label strategy**: HierText and COCO-Text provide word-level handwritten/machine-printed labels; page-level ratio computed from word density.

---

### capture-method

> **Quick Stats**: 50,000 target | 4-class capture modality

| Attribute | Value |
|-----------|-------|
| **Purpose** | Capture method classification for degradation-aware routing |
| **Target Size** | 50,000 |
| **Status** | 📋 Planned |
| **Head** | SigLIP 2 G5 |
| **Classes** | born-digital, scanner, camera, synthetic |
| **Key Sources** | doclaynet (📄 born-digital), rvl-cdip (🖨️ scanner), smartdoc-qa/midv500 (📱 camera), synth-multiscript-v3 (🎨 synthetic) |

---

### shadow

> **Quick Stats**: 15,000 target | Paired GT (shadow / clean)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Shadow detection and severity regression |
| **Target Size** | 15,000 |
| **Status** | 📋 Planned |
| **Head** | SigLIP 2 G5 |
| **Key Sources** | sd7k (7.2K paired), wsrd (4.5K paired), doc3d synthetic overlays |

**Label type**: Paired GT (shadow input / clean reference) -- shadow severity regression 0-1

---

### warping

> **Quick Stats**: 20,000 target | Paired GT (warped / flat)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Document warping detection and severity regression |
| **Target Size** | 20,000 |
| **Status** | 📋 Planned |
| **Head** | SigLIP 2 G5 |
| **Key Sources** | warpdoc (1K, 6 warp types), anyphotodoc6300 (6.3K), doc3d (perspective/curl overlays) |

**Label type**: Paired GT (warped input / flat reference) -- warping severity regression 0-1

---

## Ground Truth Provenance

Training datasets use three label provenance tiers:

| Tier | Label Type | Confidence | Datasets |
|------|-----------|------------|---------|
| **tier_0 (exact)** | Synthetic exact -- augmentation parameters ARE the labels | 1.0 | synth-multiscript-v3 (orientation, skew, resolution quality, IQA pseudo-labels) |
| **tier_1 (classical ensemble)** | Multi-method heuristics with confidence filter | 0.7-0.95 | skew (natural scans: Hough + projection + gradient, conf ≥ 0.7) |
| **tier_2 (human / VLM)** | Human MOS or VLM-scored with validation | 0.6-0.85 | iqa-curated (DIQA-5000 human MOS, OHR-Bench quality scores, VLM IQA pilot) |

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
→ Use `synth-multiscript-v3` (350K GCS-confirmed, 27 scripts — ⚠️ rebalancing required before training; Arab 49K, 17 scripts below target)

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
| ✅ Ready | Dataset complete, validated, and uploaded to GCS |
| 🔄 Generating | Generation script running or partially complete |
| 🔄 In Progress | Labels partially assembled; assembly script ready |
| 📋 Planned | Design spec exists; no generation started |

---

## References

### Dataset Documentation

- **Individual training dataset files**: [training/](training/) -- per-dataset deep documentation
  - [training/orientation.md](training/orientation.md) -- source composition, label schema, directory structure
  - [training/synth-multiscript-v3.md](training/synth-multiscript-v3.md) -- script coverage, derived views, validation
- **Full Catalog**: [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md) -- deep technical details for all datasets
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) -- 57 source datasets, audit grades, label provenance

### Architecture & Planning

- **SigLIP 2 Requirements**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) -- 16-head architecture, head groups G1-G5
- **Training Optimization**: [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) -- ILP allocation, PCGrad, phased head training
- **Dataset Diversity**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) -- 10 dataset specs, 14 diversity dimensions, global split registry
- **MobileNetV4 Design**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) -- orientation + skew + resolution design
- **Resolution Quality V2**: [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md) -- char-height measurement pipeline

### Training Infrastructure

- **Modal Training**: [docs/reference/MODAL_QUICK_REFERENCE.md](../reference/MODAL_QUICK_REFERENCE.md) -- GPU training workflow
- **Training Script (Skew)**: `modal/train_skew_estimator.py` -- MobileNetV4 + 3-head training
- **GCS Bucket**: `gs://image_detection_b/` -- training dataset mirror

---

**Last Updated**: 2026-02-21
**Maintained By**: Data team
