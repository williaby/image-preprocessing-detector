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
> **Size**: ~200 lines, ~2K tokens
> **Full Details**: See [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md)

---

## Training Datasets Overview

| Dataset | Purpose | Images | Status | Documentation |
|---------|---------|--------|--------|---------------|
| [orientation](#orientation) | Orientation Detection | 50,000 | ✅ Ready | [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) |
| [synthetic_multiscript](#synthetic_multiscript) | Script Detection | 250,000 (target) | 🔄 In Progress (~27K) | [synth-multiscript-250k_review.md](datasets/reviews/synth-multiscript-250k_review.md) |

**Storage Location**: `E:\image_detection\03_training_datasets\`

---

## orientation

> **Quick Stats**: 50,000 images | 4-class balanced | 12,500 unique documents

| Attribute | Value |
|-----------|-------|
| **Purpose** | Orientation detection (0°, 90°, 180°, 270°) |
| **Total Images** | 50,000 |
| **Unique Documents** | 12,500 (×4 rotations each) |
| **Split** | Train: 35,000 (70%) / Val: 7,500 (15%) / Test: 7,500 (15%) |
| **Status** | ✅ Ready |
| **Path** | `03_training_datasets/orientation/` |

**Key Features**:

- Document-level splitting (no leakage)
- 50% clean, 35% light degraded, 15% moderate degraded
- Japanese vertical text included (labeled as 0°, not 270°)
- Multilingual sources: Arabic, Japanese, Devanagari documents

**Generation Script**: [scripts/prepare_orientation_dataset.py](../scripts/prepare_orientation_dataset.py)

**Design Spec**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)

---

## synthetic_multiscript

> **Quick Stats**: 250,000 target | 27 scripts | 198 languages | 🔄 In Progress (~27K generated)

| Attribute | Value |
|-----------|-------|
| **Purpose** | Script detection (27-class classification) |
| **Target Images** | 250,000 |
| **Current Images** | ~27,004 (partial) |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **Status** | 🔄 In Progress |
| **Path** | `03_training_datasets/synthetic_multiscript/` |

**Script Coverage** (ISO 15924):

- Latin (Latn), Arabic (Arab), Devanagari (Deva)
- Chinese Simplified/Traditional (Hans, Hant), Japanese (Jpan), Korean (Kore)
- Cyrillic (Cyrl), Greek (Grek), Thai (Thai), Hebrew (Hebr)
- Bengali (Beng), Gujarati (Gujr), Gurmukhi (Guru), Kannada (Knda)
- Armenian (Armn), Georgian (Geor), Ethiopic (Ethi), Khmer (Khmr)
- 9 more scripts

**Key Features**:

- Multi-script documents (65% have 2-4 scripts per image)
- Synthetic IQA labels (8 dimensions)
- Layout metadata (layout_type, text_density)
- Text sourced from OpenLID-v2 corpus

**Technical Review**: [synth-multiscript-250k_review.md](datasets/reviews/synth-multiscript-250k_review.md)

---

## By Training Purpose

### Orientation Detection (Phase 10A)

| Dataset | Images | Model Target | Accuracy Target |
|---------|--------|--------------|-----------------|
| **orientation** | 50,000 | MobileNetV4-Conv-S | ≥97% overall |

### Script Detection (Phase 10B)

| Dataset | Images | Model Target | Accuracy Target |
|---------|--------|--------------|-----------------|
| **synthetic_multiscript** | 250,000 | SigLIP | ≥90% overall |

---

## Quick Selection Guide

**"I need to train orientation detection"**
→ Use `orientation` (50K images, 4-class balanced)
→ Spec: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)

**"I need to train script detection"**
→ Use `synthetic_multiscript` (250K target, 27 scripts)
→ ⚠️ Currently ~27K partial - verify completion status

---

## Status Legend

| Status | Meaning |
|--------|---------|
| ✅ Ready | Dataset complete and validated |
| 🔄 In Progress | Generation ongoing |

---

## Related Documentation

- **Design Specification**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)
- **Script Detection Review**: [synth-multiscript-250k_review.md](datasets/reviews/synth-multiscript-250k_review.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md)
- **Full Catalog**: [TRAINING_DATASET_CATALOG.md](TRAINING_DATASET_CATALOG.md)

---

**Last Updated**: 2026-02-01
**Maintained By**: Data team
