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

| # | Dataset | Images | Head Group | Status | Documentation |
|---|---------|-------:|------------|--------|---------------|
| 1 | orientation | 50,000 | G3 / MNV4 H1 | ✅ Ready | [training/orientation.md](training/orientation.md) |
| 2 | skew | 90,412 | G3 / MNV4 H2 | ✅ Ready | [training/skew.md](training/skew.md) |
| 3 | resolution-quality | 30,000 | G5 / MNV4 H3 | 🔄 5.5K done | [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md) |
| 4 | iqa-curated | 16,000 | G1 | 🔄 In progress | `results/iqa_vlm_labeling/` |
| 5 | iqa-synthetic | 100,000 | G1 | 📋 Planned | Derived from synth-multiscript-v3 |
| 6 | synth-multiscript-v3 | 350,012 | G2 (direct) | ✅ Complete — ⚠️ Imbalanced distribution (generator bug; see synth-multiscript-v3.md) | [training/synth-multiscript-v3.md](training/synth-multiscript-v3.md) |
| 7 | handwriting | 60,000 | G4 | 📋 Planned | [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |
| 8 | capture-method | 50,000 | G5 | 📋 Planned | [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |
| 9 | shadow | 15,000 | G5 | 📋 Planned | [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |
| 10 | warping | 20,000 | G5 | 📋 Planned | [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) |

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

> **Quick Stats**: 350,012 images (✅ Complete in total count — ⚠️ imbalanced distribution, see per-script breakdown) | 27 scripts | 198 languages | JPEG q95 | Layer 2 v2.3
>
> **Status**: ✅ Complete — ⚠️ Imbalanced (Arab 49K, 17 scripts below 12,963 target; rebalancing needed before training) | **Version**: 3.0

### Overview

Synthetic multilingual text images serving as the **pristine base** from which ALL synthetic training
views are derived. Generates document images with authentic text from OpenLID-v2 corpus across
27 ISO 15924 scripts with comprehensive Layer 2 v2.3 metadata.

**Purpose**: Unified base dataset for SigLIP 2 multi-task training and MobileNetV4 training.

**Full Documentation**: [training/synth-multiscript-v3.md](training/synth-multiscript-v3.md)

### Configuration

| Attribute | Value |
|-----------|-------|
| Total Images | 350,012 *(GCS-confirmed by live gsutil ls jpg count 2026-02-21; target met — ⚠️ distribution severely imbalanced due to generator bug)* |
| Scripts | 27 ISO 15924 codes |
| Languages | 198 OpenLID-v2 varieties |
| File Format | JPEG quality 95 (~200 KB/image, ~38 GB estimated at 190K) |
| Schema | Layer 2 Enrichment v2.3.0 |
| Multi-script | 55% (two 38% + three 10% + four+ 2% + priority 5%) |
| Single-script | 45% |
| Split | Use `splits.jsonl` at GCS prefix root for deterministic 80/10/10 assignment |
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
| Script Detection | 350K (direct, GCS-confirmed) — ⚠️ rebalancing required before training | Native DPI | SigLIP 2 G2 |
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

## resolution-quality

> **Quick Stats**: 30,000 target | 5,500 labeled (DIQA-5000) | char-height-aware scoring
>
> **Status**: 🔄 In Progress | **Head**: MobileNetV4-Conv-S H3

### Overview

Resolution quality scoring dataset for the third MobileNetV4 head. Labels are generated via a
two-stage pipeline: PaddleOCR v2 text detection followed by connected-component character-height
measurement.

**Purpose**: Train MobileNetV4-Conv-S H3 (resolution quality score 0-1, coarse bucket).

**Strategy**: [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md)

### Configuration

| Attribute | Value |
|-----------|-------|
| Target Size | 30,000 |
| Labeled So Far | 5,499 (DIQA-5000) |
| DPI Tiers | 7 (72/100/150/200/300/400/600), stratified |
| Image Size | 224px |
| Scoring | Char-height-aware piecewise 0-1 |

### Label Schema

| Field | Type | Description |
|-------|------|-------------|
| `character_height_px` | float | Best available char height |
| `resolution_quality_score` | float | Piecewise score 0-1 |
| `coarse_bucket` | str | needs_major_upscale / needs_light_upscale / optimal / good / oversized |
| `measurement_method` | str | sauvola_cc_v2 |
| `label_provenance` | str | classical_pipeline or tier_0_exact (for synth views) |

### Labeling Pipeline

**Script**: `scripts/label_resolution_quality.py` (dataset-agnostic, takes `--input-dir`)

**Integration**: `scripts/integrate_resolution_quality.py` (merges into L2 metadata)

**Method** (V2): Sauvola binarization (k=0.2) + morphological closing (3×1, 1×3) + KDE mode
for char height. Script-aware ensemble: CJK → 0.7 proj / 0.3 CC, Latin → 0.3 proj / 0.7 CC.

### Next Steps

1. Label OHR-Bench (8.5K) via labeling pipeline on A100 VM
2. Label RealDAE (1.2K) via labeling pipeline
3. Derive 30K view from synth-multiscript-v3 (tier_0 exact labels)
4. Validate coarse bucket distribution across DPI tiers

---

## iqa-curated

> **Quick Stats**: 16,000 target | Human MOS + VLM-scored quality
>
> **Status**: 🔄 In Progress | **Head**: SigLIP 2 G1

### Overview

Curated IQA dataset assembled from real document datasets with human mean-opinion-score labels
and VLM-scored quality annotations. Used for SigLIP 2 G1 fine-tuning after iqa-synthetic pre-training.

### Key Sources

| Source | Images | Labels | Provenance |
|--------|-------:|--------|------------|
| DIQA-5000 | 4,400 (train) | Human MOS (1-5), 3 dimensions | human_mos |
| OHR-Bench | 6,849 (train) | Quality scores (0-100), 7 domains | human_mos |
| DocLayNet curated | ~4,751 | VLM-scored (prompt v2.0) | vlm_scored |

### VLM Pilot Results (Phase 1)

| Metric | Value | Target |
|--------|-------|--------|
| SRCC overall (all) | 0.39 | >0.65 |
| SRCC overall (non-rotated) | 0.53 | >0.65 |
| SRCC sharpness | 0.58 | >0.65 |

**Decision**: Proceed with revised prompt v2.0 (orientation-independent scoring). Scale to 2-5K
images once SRCC > 0.60 in validation batch.

**Results location**: `results/iqa_vlm_labeling/`

**Scripts**: `scripts/select_iqa_vlm_images.py`, `scripts/collect_vlm_iqa_labels.py`

---

## iqa-synthetic

> **Quick Stats**: 100,000 target | tier_0 exact pseudo-labels | Derived from synth-multiscript-v3
>
> **Status**: 📋 Planned | **Head**: SigLIP 2 G1 (pre-training)

### Overview

Large-scale synthetic IQA dataset for SigLIP 2 G1 pre-training. Derived from synth-multiscript-v3
by replaying degradation parameters with exact ground truth.

**Key insight**: The augmentation parameters recorded during synth-multiscript-v3 generation ARE
the labels -- `label_provenance: tier_0_exact`, `label_confidence: 1.0`.

### Configuration

| Attribute | Value |
|-----------|-------|
| Target Size | 100,000 |
| Source | synth-multiscript-v3 (diverse quality tier subset) |
| Image Size | 384px |
| Label Confidence | 1.0 (tier_0_exact) |
| IQA Dimensions | 8 (blur, noise, compression, ink_degradation, paper_degradation, geometric_distortion, bleed_through, overall_quality) |

### Next Steps

1. Define selection strategy (stratified by quality tier, DPI, script)
2. Write derivation script to generate 384px views with parameter replay
3. Validate label distribution across 8 dimensions

---

## handwriting

> **Quick Stats**: 60,000 target | 3-head graded assessment
>
> **Status**: 📋 Planned | **Head**: SigLIP 2 G4

### Overview

Handwriting detection dataset with graded severity labels. Assembled from page-level images
where word-level handwriting annotations are aggregated to page level.

### Key Sources

| Source | Images | Word-Level Label | Page Aggregation |
|--------|-------:|-----------------|------------------|
| HierText | 8,281 (train) | `handwritten` boolean per word | handwriting_ratio = handwritten_words / total_words |
| COCO-Text | 43,686 (train) | `class: machine_printed\|handwritten` | handwriting_ratio |
| IAM | 6,161 lines | Full handwriting (657 writers) | has_handwriting=1, ratio=1.0 |

### Label Schema

| Field | Type | Description |
|-------|------|-------------|
| `has_handwriting` | bool | Any handwritten content present |
| `handwriting_ratio` | float | Fraction of words that are handwritten (0-1) |
| `handwriting_confidence` | float | Label confidence based on annotation density |

### Next Steps

1. Design page-level aggregation script for HierText + COCO-Text
2. Sample 60K balanced across ratio buckets (0%, 1-25%, 25-75%, 75-99%, 100%)
3. Validate with human review on boundary cases

---

## capture-method

> **Quick Stats**: 50,000 target | 4-class modality classification
>
> **Status**: 📋 Planned | **Head**: SigLIP 2 G5

### Overview

Capture method classification dataset for degradation-aware routing. Distinguishes between
born-digital, scanner, camera-captured, and synthetic documents.

### Key Sources

| Source | Images | Class | Confidence |
|--------|-------:|-------|------------|
| doclaynet | ~10K | born-digital | tier_0 (provenance documented) |
| rvl-cdip | ~10K | scanner | tier_0 (provenance documented) |
| smartdoc-qa / midv500 | ~15K | camera | tier_0 (provenance documented) |
| synth-multiscript-v3 | ~15K | synthetic | tier_0 |

### Label Schema

| Field | Type | Values |
|-------|------|--------|
| `capture_method` | str | born_digital, scanner, camera, synthetic |
| `capture_confidence` | float | 1.0 for provenance-documented sources |

### Next Steps

1. Validate capture method labels against Layer 2 metadata capture flags
2. Assemble 50K balanced split across 4 classes
3. Verify no overlap with reserved val/test splits from source datasets

---

## shadow

> **Quick Stats**: 15,000 target | Paired GT (shadow / clean)
>
> **Status**: 📋 Planned | **Head**: SigLIP 2 G5

### Overview

Shadow detection and severity regression dataset assembled from paired shadow/clean image datasets.

### Key Sources

| Source | Images | Type | License |
|--------|-------:|------|---------|
| sd7k | 7,239 | Paired GT (shadow/clean) | Unspecified |
| wsrd | 4,500 | Paired GT (shadow/clean) | Unspecified |
| doc3d | ~3,261 | Synthetic shadow overlays | CC-BY-NC-SA-4.0 |

### Label Schema

| Field | Type | Description |
|-------|------|-------------|
| `has_shadow` | bool | Shadow present |
| `shadow_severity` | float | Shadow coverage fraction 0-1 |
| `shadow_type` | str | natural, artificial, cast |

### Next Steps

1. Extract shadow severity from paired GT (pixel ratio of shadow mask)
2. Verify doc3d shadow overlay generation pipeline
3. Assemble 15K stratified by severity

---

## warping

> **Quick Stats**: 20,000 target | Paired GT (warped / flat)
>
> **Status**: 📋 Planned | **Head**: SigLIP 2 G5

### Overview

Document warping detection and severity regression dataset. Covers page curl, perspective
distortion, and bookbinding deformation.

### Key Sources

| Source | Images | Warp Types | License |
|--------|-------:|-----------|---------|
| warpdoc | 1,020 | 6 types (curl, fold, perspective, etc.) | Unspecified |
| anyphotodoc6300 | 6,306 | Camera perspective + dewarped GT | AGPL-3.0 |
| doc3d | ~12,674 | 3D geometry (depth, UV, normals) | CC-BY-NC-SA-4.0 |

### Label Schema

| Field | Type | Description |
|-------|------|-------------|
| `has_warping` | bool | Warping distortion present |
| `warp_severity` | float | Geometric distortion severity 0-1 |
| `warp_type` | str | perspective, curl, fold, combined |

### Next Steps

1. Extract warp severity from doc3d UV/depth maps (distortion energy metric)
2. Validate anyphotodoc6300 GT pairs for quality
3. Assemble 20K stratified by severity and warp type

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
- **Synth-Multiscript Full Doc**: [training/synth-multiscript-v3.md](training/synth-multiscript-v3.md)
- **Regeneration Plan**: [Plan File](../../.claude/plans/parallel-discovering-acorn.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md)
- **Layer 2 Schema**: [layer2_enrichment_v2.schema.json](../schema/layer2_enrichment_v2.schema.json)

---

**Last Updated**: 2026-02-12
**Maintained By**: Data team
