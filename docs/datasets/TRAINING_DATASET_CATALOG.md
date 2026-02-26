---
owner: docs-team
purpose: High-level catalog and index for all assembled training datasets.
schema_type: common
status: active
tags:
- datasets
- training
- catalog
title: Training Dataset Catalog
---

> **Purpose**: High-level index pointing to individual dataset detail files
> **Quick Lookup**: See [TRAINING_DATASET_QUICK_REFERENCE.md](TRAINING_DATASET_QUICK_REFERENCE.md)
> for head↔dataset mapping, OOD cross-reference, and per-dataset quick stats
> **Individual Files**: [training/](training/) — one file per dataset, 11-section detail
> **Template**: [TRAINING_DATASET_TEMPLATE.md](TRAINING_DATASET_TEMPLATE.md)

---

## Summary

10 assembled training datasets, one per training task area.
See [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) for diversity
specs and [HAR_SYNTHESIS.md](../planning/HAR_SYNTHESIS.md) for gap registry and remediation backlog.

**Storage**: `E:\image_detection\03_training_datasets\` (local) / `gs://image_detection_b/` (GCS)

| # | Dataset | Images | Heads Fed | Status | HAR Score | P0 Gaps | Detail File |
|---|---------|-------:|-----------|--------|-----------|---------|-------------|
| 1 | **orientation** | 50,000 | MNV4-H1, SIG-G3-1 | ✅ Ready | 82/100 | 0 | [training/orientation.md](training/orientation.md) |
| 2 | **skew** | 90,412 | MNV4-H2, SIG-G3-2 | ✅ Ready | 76/100 | 0 | [training/skew.md](training/skew.md) |
| 3 | **resolution-quality** | 30,000 target | MNV4-H3, SIG-G5-5 | 🔄 5.5K done | 54/100 | 1 | [training/resolution-quality.md](training/resolution-quality.md) |
| 4 | **iqa** | 116,000 target | SIG-G1-1 → G1-6 | 🔄 Phase 1 in progress | 46–61/100 | 6–8 | [training/iqa.md](training/iqa.md) |
| 5 | **script-detection** | 350,012 | SIG-G2-1 | ⚠️ Complete — rebalancing needed | 61/100 | 2 | [training/synth-multiscript-v3.md](training/synth-multiscript-v3.md) |
| 6 | **handwriting** | 60,000 target | SIG-G4-1 → G4-5 | ❌ Blocked | 14–35/100 | 17 | [training/handwriting.md](training/handwriting.md) |
| 7 | **capture-method** | 50,000 target | SIG-G5-1 | ⚠️ Needs Work | 55/100 | 0 | [training/capture-method.md](training/capture-method.md) |
| 8 | **shadow** | 15,000 target | SIG-G5-2 | ❌ Blocked | 28/100 | 3 | [training/shadow.md](training/shadow.md) |
| 9 | **warping** | 20,000 target | SIG-G5-3 | ❌ Blocked | 17/100 | 4 | [training/warping.md](training/warping.md) |
| 10 | **code-detection** | 10,000 target | SIG-G5-4 | ⚠️ Needs Work | 55/100 | 5 | [training/code-detection.md](training/code-detection.md) |

> **HAR scores and P0 gap counts** sourced from [HAR_MASTER_INDEX.md](../planning/HAR_MASTER_INDEX.md)
> (completed 2026-02-25). Scores: ✅ Ready ≥75, ⚠️ Needs Work 50–74, ❌ Blocked <50 or P0 unresolved.

---

## Training Pipeline Architecture

Three-step virtuous training cycle. See [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
and [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) for full specs.

| Step | Model | Primary Datasets | Strategy |
|------|-------|-----------------|----------|
| **1. MNV4 Bootstrap** | MobileNetV4-Conv-S | orientation (#1), skew (#2), resolution-quality (#3) | Ground truth hard labels |
| **2. SigLIP 2 Multi-Task** | SigLIP 2 NAFlex | All 10 datasets (#1–#10) | Frozen backbone + 19 task heads |
| **3. MNV4 Distillation** | MobileNetV4-Conv-S | SigLIP 2 soft labels + hard labels | KL-divergence (T=3, α=0.7) |

**Datasets ready to start training**: #1 (orientation), #2 (skew) → MNV4-H1/H2 can train now.

---

## Label Provenance Tiers

All training labels carry a declared `label_provenance` field:

| Tier | Type | Confidence | Datasets |
|------|------|------------|---------|
| `tier_0_exact` | Synthetic parameters are the labels | 1.0 | synth-multiscript-v3 derived views (orientation, resolution-quality, IQA Phase 2) |
| `classical_ensemble` | Multi-method classical detection, conf ≥ 0.7 | 0.7–0.95 | skew (natural scan labels) |
| `tier_2_vlm` | VLM annotation, SRCC > 0.60 required | 0.6–0.85 | iqa Phase 1 curated (DIQA-5000, OHR-Bench) |
| `human_mos` | Human mean opinion scores | ~0.9 | iqa Phase 1 (gold standard subset) |

**Global split registry**: SHA256-keyed JSONL (`splits.jsonl`) prevents the same base image from
appearing in both train and test across synth-multiscript-v3 derived views.

---

## Quick Selection Guide

| If you need... | Use dataset | Status |
|----------------|-------------|--------|
| Orientation detection training | #1 orientation | ✅ Ready |
| Skew estimation training | #2 skew | ✅ Ready |
| Script detection training | #5 script-detection | ⚠️ Rebalancing needed |
| Resolution quality scoring | #3 resolution-quality | 🔄 5.5K labeled |
| IQA individual degradation heads | #4 iqa (Phase 2 synthetic) | 📋 Planned |
| IQA overall quality head | #4 iqa (Phase 1 curated) | 🔄 In progress |
| Handwriting detection | #6 handwriting | ❌ Blocked |
| Capture method classification | #7 capture-method | ⚠️ Needs Work |
| Shadow severity regression | #8 shadow | ❌ Blocked |
| Warping severity regression | #9 warping | ❌ Blocked |
| Code detection | #10 code-detection | ⚠️ Needs Work |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [TRAINING_DATASET_QUICK_REFERENCE.md](TRAINING_DATASET_QUICK_REFERENCE.md) | Head↔dataset mapping, OOD cross-reference, per-dataset quick stats |
| [TRAINING_DATASET_TEMPLATE.md](TRAINING_DATASET_TEMPLATE.md) | 11-section template for individual detail files |
| [HAR_MASTER_INDEX.md](../planning/HAR_MASTER_INDEX.md) | HAR adequacy scores and gap counts for all 22 heads |
| [HAR_SYNTHESIS.md](../planning/HAR_SYNTHESIS.md) | Cross-head gap registry and prioritized remediation backlog |
| [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) | 14 diversity dimensions, per-dataset targets |
| [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) | 19-head architecture, performance targets, training phases |
| [OOD_DATASET_CATALOG.md](OOD_DATASET_CATALOG.md) | 4,700 OOD images across 9 categories |
| [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) | 57 source datasets, L2 audit grades |

---

**Last Updated**: 2026-02-23
**Maintained By**: Data team
