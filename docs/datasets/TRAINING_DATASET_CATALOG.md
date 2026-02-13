---
owner: docs-team
purpose: Comprehensive catalog of all training datasets.
schema_type: common
status: active
tags:
- datasets
- training
- catalog
title: Training Dataset Catalog
---

> **Purpose**: Comprehensive documentation for all training datasets
> **Use For**: Deep technical details, generation provenance, label schemas
> **Quick Lookup**: See [TRAINING_DATASET_QUICK_REFERENCE.md](TRAINING_DATASET_QUICK_REFERENCE.md) first
> **Size**: ~800 lines, ~8K tokens

---

## Catalog Summary

| Dataset | Images | Purpose | Status | Design Spec |
|---------|--------|---------|--------|-------------|
| orientation | 50,000 | Orientation Detection | Ready | [Design Spec](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) |
| synth-multiscript-v3 | 350,000 | Script Detection + Base for All Views | Generating | [Full Doc](training/synth-multiscript-250k.md) |
| skew | 90,412 | Skew Estimation | Ready | [Pipeline Plan](../../tmp_cleanup/.tmp-skew-pipeline-project-plan.md) |

**Storage Location**: `E:\image_detection\03_training_datasets\`

---

## orientation

> **Quick Stats**: 50,000 images | 4-class balanced | 12,500 unique documents
>
> **Status**: ✅ Ready | **Created**: 2026-01-25

### Overview

Orientation detection training dataset for Phase 10A. Each unique source document is rotated to all four cardinal orientations (0°, 90°, 180°, 270°) with varied degradation levels.

**Purpose**: Train MobileNetV4-Conv-S orientation classifier for preprocessing pipeline.

**Design Specification**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)

### Configuration

```json
{
  "total_unique_documents": 12500,
  "total_samples": 50000,
  "rotation_angles": [0, 90, 180, 270],
  "train_ratio": 0.70,
  "val_ratio": 0.15,
  "test_ratio": 0.15,
  "clean_ratio": 0.50,
  "light_degraded_ratio": 0.35,
  "moderate_degraded_ratio": 0.15,
  "random_seed": 42
}
```

### Source Document Composition

| Document Type | Count | Source Datasets | Why Critical |
|---------------|-------|----------------|--------------|
| Scientific papers | 2,500 | DocLayNet (scientific) | Multi-column, equations |
| Financial reports | 1,875 | DocLayNet (financial) | Tables, decimal alignment |
| Legal documents | 1,000 | DocLayNet (legal) | Dense text, paragraphs |
| Mixed layouts | 500 | DocLayNet (manuals, patents) | Element relationships |
| Tables | 2,000 | TableBank, PubTabNet | Row/column swap when rotated |
| Real scans | 2,000 | RVL-CDIP | Diverse quality |
| Forms | 899 | FUNSD, FUNSD+ | Grid structures |
| Receipts | 1,000 | SROIE | Narrow aspect ratio |
| Handwritten | 1,000 | NIST SD-19 | Stroke baseline |
| Japanese vertical | 991 | JSSODa | **CRITICAL**: labeled as 0° |
| Japanese horizontal | 1,009 | JSSODa | Balance Japanese samples |
| Arabic (RTL) | 500 | Arabic OCR | RTL script orientation |
| Bhutan financial | 125 | Bhutan AFS/Tax docs | Real government docs |

**Total**: 12,499 unique documents → 49,996 samples (×4 rotations)

### Split Details

| Split | Documents | Images | Percentage |
|-------|-----------|--------|------------|
| Train | 8,750 | 35,000 | 70% |
| Val | 1,875 | 7,500 | 15% |
| Test | 1,875 | 7,500 | 15% |

**Critical**: Document-level split BEFORE rotation to prevent data leakage.

### Degradation Distribution

| Level | Ratio | Description |
|-------|-------|-------------|
| Clean | 50% | Original quality |
| Light Degraded | 35% | Gaussian blur σ=0.5-1.0, light noise std=5-15, JPEG 75-90 |
| Moderate Degraded | 15% | Motion blur, perspective warp, shadows, JPEG 50-75 |

**Degradation Profile**:

- Camera artifacts (60% of degraded): motion blur, perspective, shadows, ISO noise
- Scanner artifacts (40% of degraded): gaussian blur, scan noise, JPEG compression

### Label Schema

```json
{
  "image_path": "orientation_train/90deg/005432.png",
  "orientation_class": 1,
  "orientation_degrees": 90,
  "source_document_id": "doclaynet_financial_0123",
  "source_dataset": "DocLayNet",
  "document_type": "financial_report",
  "split": "train",
  "quality_variant": "moderate_degraded",
  "degradation_types": ["motion_blur", "perspective_warp"],
  "is_vertical_text": false,
  "text_orientation": "horizontal_ltr"
}
```

### Directory Structure

```text
orientation/
├── generation.log
├── labels/
│   ├── train_labels.jsonl
│   ├── val_labels.jsonl
│   └── test_labels.jsonl
├── metadata/
│   ├── generation_config.json
│   ├── source_documents.json
│   └── split_assignments.json
├── train/
│   ├── 0deg/    (8,750 samples)
│   ├── 90deg/   (8,750 samples)
│   ├── 180deg/  (8,750 samples)
│   └── 270deg/  (8,750 samples)
├── val/
│   └── {0deg, 90deg, 180deg, 270deg}/
└── test/
    └── {0deg, 90deg, 180deg, 270deg}/
```

### Generation

**Script**: [scripts/prepare_orientation_dataset.py](../scripts/prepare_orientation_dataset.py)

**Usage**:

```bash
uv run python scripts/prepare_orientation_dataset.py --dry-run
uv run python scripts/prepare_orientation_dataset.py --output /mnt/e/image_detection/03_training_datasets/orientation
```

### Target Model Performance

| Metric | S4 Teacher | S0 Student |
|--------|------------|------------|
| Overall Accuracy | ≥98% | ≥97% |
| Per-class Accuracy | ≥97% | ≥95% |
| Vertical Japanese | ≥95% (as 0°) | ≥93% (as 0°) |

---

## synth-multiscript-v3

> **Quick Stats**: 350,000 images | 27 scripts | 198 languages | JPEG q95 | Layer 2 v2.3
>
> **Status**: Generating | **Version**: 3.0

### Overview

Synthetic multilingual text images serving as the **pristine base** from which ALL synthetic training
views are derived. Generates document images with authentic text from OpenLID-v2 corpus across
27 ISO 15924 scripts with comprehensive Layer 2 v2.3 metadata.

**Purpose**: Unified base dataset for SigLIP 2 multi-task training and MobileNetV4 training.

**Full Documentation**: [training/synth-multiscript-250k.md](training/synth-multiscript-250k.md)

### Configuration

| Attribute | Value |
|-----------|-------|
| Total Images | 350,000 |
| Scripts | 27 ISO 15924 codes |
| Languages | 198 OpenLID-v2 varieties |
| File Format | JPEG quality 95 (~200 KB/image, ~70 GB total) |
| Schema | Layer 2 Enrichment v2.3.0 |
| Multi-script | 55% (two 38% + three 10% + four+ 2% + priority 5%) |
| Single-script | 45% |
| Split | Train: 280K (80%) / Val: 35K (10%) / Test: 35K (10%) |
| Skew Range | +/-22 deg (expanded from +/-10 deg) |

### Key Design: Pristine Base + Deferred Degradation

Images stored **pristine** (no degradation baked in). Degradation parameters recorded in metadata
for reproducible replay. Derived views apply their own transforms at derivation time.

### v3-Specific Features

- **CJK Vertical Text**: Jpan 30% TTB, Hans/Hant 10% TTB with `text_direction` per block
- **English Secondary Weighting**: 40% probability as secondary in multi-script compositions
- **Generation Provenance**: SHA256 hash, degradation seed, font families per image
- **Global Split Registry**: SHA256-keyed JSONL prevents cross-dataset train/test leakage
- **Hybrid Augmentation**: Augraphy (document effects) + Albumentations (general effects)
- **Document Age**: 80% modern, 15% aged, 5% historical
- **Color Modes**: 60% color, 30% grayscale, 10% binarized

### Derived Views (from this base)

| View | Count | Output Size | Model Target |
|------|-------|-------------|--------------|
| Script Detection | 350K (direct) | Native DPI | SigLIP 2 G2 |
| Orientation | 50K | 224px | MobileNetV4 H1 |
| Skew | 50-80K synth | 384px | MobileNetV4 H2 |
| Resolution Quality | 30K | 224px | MobileNetV4 H3 |
| IQA Pseudo-Labels | 100K | 384px | SigLIP 2 G1 |
| Shadow | 15K | 384px | SigLIP 2 G5 |
| Warping | 20K | 384px | SigLIP 2 G5 |

### Generation

**Script**: [scripts/generate_base_dataset_v3.py](../scripts/generate_base_dataset_v3.py)

**Validation**: [scripts/validate_base_dataset_v3.py](../scripts/validate_base_dataset_v3.py)

```bash
python scripts/generate_base_dataset_v3.py \
    --output-dir /path/to/synthetic_multiscript_v3 \
    --total-images 350000 --workers 4 --seed 42 --augmenter hybrid --yes
```

### Deprecated Versions

| Version | Images | Status |
|---------|--------|--------|
| v1.0 (27K) | 27,004 | DELETED |
| v2.0 (250K) | ~62,500 partial | DELETED |

---

## skew

> **Quick Stats**: 90,412 images | 71K synthetic + 19K natural | 384x384 JPEG q90
>
> **Status**: Ready | **Created**: 2026-02-11

### Overview

Skew estimation training dataset for MobileNetV4-Conv-S Head 2. Combines synthetic document images
with classical-ensemble-labeled natural scans from 13 real-document datasets.

**Purpose**: Train hybrid 42-bin classification + residual regression skew estimator.

### Configuration

| Attribute | Value |
|-----------|-------|
| Total Images | 90,412 |
| Synthetic | 71,498 |
| Natural Scans | 18,914 (13 datasets, conf >= 0.7) |
| Image Size | 384x384 JPEG quality 90 |
| Skew Range | +/-45 deg (42 non-uniform bins) |
| Split | Train: 70,763 / Val: 9,025 / Test: 10,624 |
| Local Path | `E:\03_training_datasets\skew\` |
| GCS Path | `gs://image_detection_b/skew_training/` |

### Training Results

| Config | Val MAE | Test MAE | SRCC | Orient Acc | CPU Inference |
|--------|---------|----------|------|------------|---------------|
| conv_small @ 224px, 50ep | **0.837** | **0.956** | **0.936** | 99.5% | 17.5ms |
| conv_small @ 320px, 10ep | 1.028 | 1.028 | - | - | 18.1ms |
| conv_small @ 384px, 10ep | 1.005 | 1.005 | - | - | 20.5ms |

### Key Features

- **Hybrid heads**: Orientation (4-class) + bins (42-class) + regression (continuous)
- **Per-bin residual clamping**: max_residual matches each bin's half-width
- **Natural scan diversity**: 13 source datasets (FUNSD, DocLayNet, SROIE, etc.)
- **Classical ensemble labeling**: Hough + projection + gradient methods, conf >= 0.7 filter

### Generation Scripts

| Script | Purpose |
|--------|---------|
| `generate_skew_dataset.py` | Generate synthetic skew images |
| `merge_skew_datasets.py` | Merge synthetic + natural scans |
| `select_natural_scan_skew_subset.py` | Select and stratify natural scans |
| `label_skew_classical.py` | Classical ensemble labeling |

---

## Appendix: Template for New Training Datasets

See [TRAINING_DATASET_TEMPLATE.md](TRAINING_DATASET_TEMPLATE.md) for the standard template to document new training datasets.

---

## Appendix: Generation Scripts

| Dataset | Script | Location |
|---------|--------|----------|
| orientation | `prepare_orientation_dataset.py` | [scripts/](../scripts/prepare_orientation_dataset.py) |
| synth-multiscript-v3 | `generate_base_dataset_v3.py` | [scripts/](../scripts/generate_base_dataset_v3.py) |
| skew | `generate_skew_dataset.py` | [scripts/](../scripts/generate_skew_dataset.py) |

---

## Appendix: Related Documentation

- **Orientation Design**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](../planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)
- **Synth-Multiscript Full Doc**: [training/synth-multiscript-250k.md](training/synth-multiscript-250k.md)
- **Regeneration Plan**: [Plan File](../../.claude/plans/parallel-discovering-acorn.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md)
- **Layer 2 Schema**: [layer2_enrichment_v2.schema.json](../schema/layer2_enrichment_v2.schema.json)

---

**Last Updated**: 2026-02-12
**Maintained By**: Data team
