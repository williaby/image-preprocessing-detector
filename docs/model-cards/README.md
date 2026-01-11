---
schema_type: common
title: "Model Cards Directory"
description: "Centralized repository for all ML model documentation in Project A"
tags:
- reference
- machine_learning
- documentation
- model_registry
status: published
owner: core-maintainer
purpose: Documentation for Model Cards Directory.
---
This directory contains standardized documentation for all ML models used in Project A (Preprocessing, IQA & Coarse Layout Gateway).

## Directory Structure

```text
docs/model-cards/
├── README.md                    # This file
├── TEMPLATE.md                  # Standard model card template
├── REGISTRY.md                  # Complete model inventory and status
│
├── production/                  # Trained and deployed models
│   ├── iqa_resnet50_teacher.md
│   ├── iqa_resnet18_student.md
│   └── layout_yolov10_doclaynet.md
│
├── classical/                   # Rule-based detectors
│   ├── classical_iqa_ensemble.md
│   ├── textgate_heuristic.md
│   └── pdftype_classifier.md
│
├── planned/                     # Documented but not yet trained
│   ├── diqa/                    # DIQA pseudo-labeling ensemble
│   │   ├── diqa_resnet50_generalist.md
│   │   ├── diqa_musiq_sharpness.md
│   │   ├── diqa_qualiclip_color.md
│   │   ├── diqa_qwen3vl_generalist.md
│   │   ├── diqa_internvl3_overall.md
│   │   └── diqa_stacker_ensemble.md
│   │
│   └── phase9/                  # Phase 9 element classifiers
│       ├── classify_resnet18_table.md
│       ├── classify_resnet18_handwriting.md
│       ├── classify_resnet18_formula.md
│       └── classify_mobilenetv3_parasitic.md
│
├── external/                    # External pretrained models (backbones)
│   ├── resnet50_imagenet1k_v2.md
│   └── musiq_koniq10k.md
│
└── deprecated/                  # Archived model cards (historical reference)
```

## Quick Links

### Core Documents

| Document | Purpose |
|----------|---------|
| [TEMPLATE.md](TEMPLATE.md) | Standard model card template for new models |
| [REGISTRY.md](REGISTRY.md) | Complete inventory with status and metrics |

### Production Models (✅ Ready)

| Model | Purpose | Status |
|-------|---------|--------|
| [iqa_resnet50_teacher](production/iqa_resnet50_teacher.md) | High-capacity IQA for escalation | Trained |
| [iqa_resnet18_student](production/iqa_resnet18_student.md) | Fast production IQA inference | Trained |
| [layout_yolov10_doclaynet](production/layout_yolov10_doclaynet.md) | Document element detection | Pretrained |

### Classical Detectors (✅ Complete)

| Model | Purpose | Status |
|-------|---------|--------|
| [classical_iqa_ensemble](classical/classical_iqa_ensemble.md) | 8 rule-based quality detectors | Complete |
| [textgate_heuristic](classical/textgate_heuristic.md) | Fast text presence detection | Complete |
| [pdftype_classifier](classical/pdftype_classifier.md) | PDF type classification | Complete |

### Planned Models (❌ Not Started)

| Model | Purpose | Phase |
|-------|---------|-------|
| [diqa_resnet50_generalist](planned/diqa/diqa_resnet50_generalist.md) | DIQA Track A anchor | DIQA |
| [diqa_musiq_sharpness](planned/diqa/diqa_musiq_sharpness.md) | Sharpness specialist | DIQA |
| [diqa_qualiclip_color](planned/diqa/diqa_qualiclip_color.md) | Color specialist | DIQA |
| [diqa_qwen3vl_generalist](planned/diqa/diqa_qwen3vl_generalist.md) | VLM Track B anchor | DIQA |
| [diqa_internvl3_overall](planned/diqa/diqa_internvl3_overall.md) | Overall specialist | DIQA |
| [diqa_stacker_ensemble](planned/diqa/diqa_stacker_ensemble.md) | Ensemble fusion | DIQA |
| [classify_resnet18_table](planned/phase9/classify_resnet18_table.md) | Table type classifier | 9 |
| [classify_resnet18_handwriting](planned/phase9/classify_resnet18_handwriting.md) | Handwriting detector | 9 |

### External Pretrained Models (Backbones)

| Model | Purpose | Used By |
|-------|---------|---------|
| [resnet50_imagenet1k_v2](external/resnet50_imagenet1k_v2.md) | Feature backbone for IQA Teacher | iqa_resnet50_teacher, diqa_resnet50_generalist |
| [musiq_koniq10k](external/musiq_koniq10k.md) | Multi-scale IQA transformer | diqa_musiq_sharpness (fine-tuned) |

## Creating a New Model Card

1. Copy [TEMPLATE.md](TEMPLATE.md) to the appropriate subdirectory
2. Rename following convention: `{task}_{architecture}_{variant}.md`
3. Fill in all required sections
4. Update [REGISTRY.md](REGISTRY.md) with the new entry
5. Link from this README

## Benchmark Tracking

Model performance benchmarks are tracked in two complementary locations:

### Official Tracking Files (Primary Source)

All benchmark results are stored in CSV format in [`docs/benchmarks/`](../benchmarks/):

| Benchmark | CSV File | Description |
|-----------|----------|-------------|
| DIQA-5000 | [diqa5000_benchmark_results.csv](../benchmarks/diqa5000_benchmark_results.csv) | Document IQA correlation metrics |
| *Future* | *TBD* | Additional benchmarks as evaluated |

These CSVs serve as the **single source of truth** for benchmark data. They include:

- All models evaluated in a single run
- Full metrics with confidence intervals
- Inference performance data
- Evaluation metadata (date, GPU, sample count)

### Per-Model Benchmark Sections (Derived)

Each model card includes a **Section 4.5: Calculated Benchmarks** with:

- Key metrics from official tracking files
- Confidence intervals for correlation metrics
- Inference latency data
- Analysis notes and interpretation

When updating benchmark results:

1. **Always update the CSV first** (official tracking file)
2. **Then update individual model cards** with relevant metrics
3. Include links back to the official CSV from each model card

## Naming Convention

**Format:** `{task}_{architecture}_{variant}`

| Component | Description | Examples |
|-----------|-------------|----------|
| `task` | Primary task | `iqa`, `layout`, `diqa`, `classify` |
| `architecture` | Model architecture | `resnet50`, `resnet18`, `yolov10`, `musiq` |
| `variant` | Role/specialization | `teacher`, `student`, `sharpness`, `color` |

## Status Definitions

| Status | Symbol | Description |
|--------|--------|-------------|
| Trained | ✅ | Model trained and validated on benchmarks |
| Pretrained | ✅ | Using external pretrained weights |
| Complete | ✅ | Rule-based detector implemented |
| Partial | ⚠️ | Framework ready, training incomplete |
| Planned | ❌ | Documented specification, not started |
| Deprecated | 🚫 | No longer supported, kept for reference |

## Related Documentation

| Document | Location |
|----------|----------|
| Project Plan | [docs/planning/PROJECT_PLAN.md](../planning/PROJECT_PLAN.md) |
| DIQA Specification | [docs/planning/DIQA-5000_Pseudo_Labels_v2.md](../planning/DIQA-5000_Pseudo_Labels_v2.md) |
| Model Reference | [docs/reference/MODEL_CARDS.md](../reference/MODEL_CARDS.md) |
