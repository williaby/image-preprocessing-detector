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

> **Purpose**: Fast lookup for training dataset selection
> **Use For**: "Which training dataset for orientation?", "Script detection dataset?"
> **Full Details**: See [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md)

---

## Training Datasets Overview

| Dataset | Purpose | Images | Status | Documentation |
|---------|---------|--------|--------|---------------|
| [orientation](#orientation) | Orientation Detection | 50,000 | Ready | [Design Spec](../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) |
| [synth-multiscript-v3](#synth-multiscript-v3) | Script Detection + Base for All Synthetic Views | 350,000 | Generating | [Full Doc](training/synth-multiscript-250k.md) |
| [skew](#skew) | Skew Estimation | 90,412 (71K synth + 19K natural) | Ready | [Pipeline Plan](../../tmp_cleanup/.tmp-skew-pipeline-project-plan.md) |

**Storage Location**: `E:\image_detection\03_training_datasets\`

---

## orientation

> **Quick Stats**: 50,000 images | 4-class balanced | 12,500 unique documents

| Attribute | Value |
|-----------|-------|
| **Purpose** | Orientation detection (0 deg, 90 deg, 180 deg, 270 deg) |
| **Total Images** | 50,000 |
| **Unique Documents** | 12,500 (x4 rotations each) |
| **Split** | Train: 35,000 (70%) / Val: 7,500 (15%) / Test: 7,500 (15%) |
| **Status** | Ready |
| **Path** | `03_training_datasets/orientation/` |

**Key Features**:

- Document-level splitting (no leakage)
- 50% clean, 35% light degraded, 15% moderate degraded
- Japanese vertical text included (labeled as 0 deg, not 270 deg)
- Multilingual sources: Arabic, Japanese, Devanagari documents

**Generation Script**: [scripts/prepare_orientation_dataset.py](../scripts/prepare_orientation_dataset.py)

**Design Spec**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)

---

## synth-multiscript-v3

> **Quick Stats**: 350,000 images | 27 scripts | 198 languages | JPEG q95 | Layer 2 v2.3

| Attribute | Value |
|-----------|-------|
| **Purpose** | Pristine base for ALL synthetic training views (script, orientation, skew, IQA, etc.) |
| **Total Images** | 350,000 |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **Schema** | Layer 2 Enrichment v2.3.0 |
| **Status** | Generating |
| **Output Path** | `synthetic_multiscript_v3/` |
| **GCS Path** | `gs://image_detection_b/synth_multiscript_v3/` |

**Key v3 Features**:

- Pristine base (no degradation baked in) + deferred degradation via seeds
- CJK vertical text (Jpan 30% TTB, Hans/Hant 10% TTB)
- English 40% secondary script weighting in multi-script compositions
- Skew range expanded to +/-22 deg (from +/-10 deg)
- Generation provenance (SHA256, degradation seeds, font families)
- Global split registry (SHA256-keyed, prevents cross-dataset leakage)

**Generation Script**: [scripts/generate_base_dataset_v3.py](../scripts/generate_base_dataset_v3.py)

**Validation Script**: [scripts/validate_base_dataset_v3.py](../scripts/validate_base_dataset_v3.py)

**Full Documentation**: [training/synth-multiscript-250k.md](training/synth-multiscript-250k.md)

**Replaces**: v1.0 (27K), v2.0 (250K) -- all old copies deleted.

---

## skew

> **Quick Stats**: 90,412 images | 71K synthetic + 19K natural scans | 384x384 JPEG q90

| Attribute | Value |
|-----------|-------|
| **Purpose** | Skew estimation (MobileNetV4 H2: 42-bin classification + residual regression) |
| **Total Images** | 90,412 |
| **Synthetic** | 71,498 (generated from source datasets) |
| **Natural Scans** | 18,914 (13 datasets, classical ensemble labeled) |
| **Split** | Train: 70,763 / Val: 9,025 / Test: 10,624 |
| **Status** | Ready |
| **Local Path** | `E:\03_training_datasets\skew\` |
| **GCS Path** | `gs://image_detection_b/skew_training/` |

**Key Features**:

- Hybrid classification+regression: 42 non-uniform bins + per-bin residual
- Skew range: +/-45 deg (full range for MobileNetV4 training)
- Natural scans from 13 real-document datasets (conf >= 0.7 filter)
- Best model result: MAE=0.837 (val), MAE=0.956 (test), SRCC=0.936, orient_acc=99.5%

**Generation Scripts**: `generate_skew_dataset.py`, `merge_skew_datasets.py`, `select_natural_scan_skew_subset.py`

---

## By Training Purpose

### Orientation Detection

| Dataset | Images | Model Target | Best Result |
|---------|--------|--------------|-------------|
| **orientation** | 50,000 | MobileNetV4-Conv-S H1 | orient_acc=99.5% |

### Skew Estimation

| Dataset | Images | Model Target | Best Result |
|---------|--------|--------------|-------------|
| **skew** | 90,412 | MobileNetV4-Conv-S H2 | MAE=0.837 (val), 0.956 (test) |

### Script Detection

| Dataset | Images | Model Target | Accuracy Target |
|---------|--------|--------------|-----------------|
| **synth-multiscript-v3** | 350,000 | SigLIP 2 G2 | >= 90% overall |

### Resolution Quality (Pending Derived View)

| Dataset | Images | Model Target | Notes |
|---------|--------|--------------|-------|
| Derived from **synth-multiscript-v3** | 30,000 | MobileNetV4-Conv-S H3 | Stratified across 7 DPI tiers |

### IQA Pre-Training (Pending Derived View)

| Dataset | Images | Model Target | Notes |
|---------|--------|--------------|-------|
| Derived from **synth-multiscript-v3** | 100,000 | SigLIP 2 G1 | Pseudo-labels from augmentation params |

---

## Quick Selection Guide

**"I need to train orientation detection"**
-> Use `orientation` (50K images, 4-class balanced)

**"I need to train skew estimation"**
-> Use `skew` (90K images, 42-bin + residual)

**"I need to train script detection"**
-> Use `synth-multiscript-v3` (350K base, 27 scripts)

**"I need resolution quality training data"**
-> Derive from `synth-multiscript-v3` (Phase 3 of plan)

**"I need IQA pseudo-labels for pre-training"**
-> Derive from `synth-multiscript-v3` (Phase 4 of plan)

---

## Status Legend

| Status | Meaning |
|--------|---------|
| Ready | Dataset complete, validated, and uploaded to GCS |
| Generating | Generation script ready, production run in progress |
| Pending | Derived view not yet generated |

---

## Related Documentation

- **Orientation Design**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)
- **Synth-Multiscript Full Doc**: [training/synth-multiscript-250k.md](training/synth-multiscript-250k.md)
- **Regeneration Plan**: [Plan File](../../.claude/plans/parallel-discovering-acorn.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md)
- **Full Catalog**: [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md)

---

**Last Updated**: 2026-02-12
**Maintained By**: Data team
