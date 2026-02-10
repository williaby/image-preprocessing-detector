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
| orientation | 50,000 | Orientation Detection | ✅ Ready | [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) |
| synthetic_multiscript | 250,000 (target) | Script Detection | 🔄 In Progress | [synth-multiscript-250k_review.md](datasets/reviews/synth-multiscript-250k_review.md) |

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

## synthetic_multiscript

> **Quick Stats**: 250,000 target | 27 scripts | 198 languages | 🔄 In Progress (~27K)
>
> **Status**: 🔄 In Progress | **Started**: 2026-01-30

### Overview

Synthetic multilingual text images for Phase 10B script family classification. Generates document images with authentic text from OpenLID-v2 corpus across 27 ISO 15924 scripts.

**Purpose**: Train SigLIP script detection model for 27-class classification.

**Technical Review**: [synth-multiscript-250k_review.md](datasets/reviews/synth-multiscript-250k_review.md)

### Target Configuration

| Attribute | Value |
|-----------|-------|
| Total Images | 250,000 |
| Scripts | 27 ISO 15924 codes |
| Languages | 198 OpenLID-v2 varieties |
| Multi-script | 65% (2-4 scripts per image) |
| Single-script | 35% |
| Split | Train: 200K / Val: 25K / Test: 25K |

### Script Coverage (27 Scripts)

| Script Code | Script Name | Estimated Count |
|-------------|-------------|-----------------|
| Latn | Latin | ~35K |
| Arab | Arabic | ~20K |
| Deva | Devanagari | ~15K |
| Hans | Chinese Simplified | ~12K |
| Hant | Chinese Traditional | ~8K |
| Jpan | Japanese | ~10K |
| Kore | Korean | ~8K |
| Cyrl | Cyrillic | ~12K |
| Grek | Greek | ~5K |
| Thai | Thai | ~5K |
| Hebr | Hebrew | ~5K |
| Beng | Bengali | ~5K |
| Gujr | Gujarati | ~5K |
| Guru | Gurmukhi | ~5K |
| Knda | Kannada | ~5K |
| Armn | Armenian | ~5K |
| Geor | Georgian | ~5K |
| Ethi | Ethiopic | ~5K |
| Khmr | Khmer | ~5K |
| + 8 more | Various | ~100K |

### Current Progress

**Generated**: ~27,004 images (partial run)

**Scripts with samples**:

- Arab, Armn, Beng, Cyrl, Deva, Ethi, Geor, Grek
- Gujr, Guru, Hans, Hant, Hebr, Jpan, Khmr, Knda, Kore

**Pending**: Continue generation to reach 250K target.

### Expected Label Schema

```json
{
  "image_id": "img_000001",
  "scripts": [
    {
      "iso15924_code": "Latn",
      "language_code": "eng",
      "bcp47_tag": "en-Latn",
      "region": {
        "bbox": [100, 50, 400, 200],
        "text_content": "Sample text..."
      }
    },
    {
      "iso15924_code": "Arab",
      "language_code": "ara",
      "bcp47_tag": "ar-Arab",
      "region": {
        "bbox": [100, 250, 400, 400],
        "text_content": "نص عربي..."
      }
    }
  ],
  "layout_type": "two_column",
  "text_density": "medium",
  "iqa_labels": {
    "blur": 0.3,
    "noise": 0.1,
    "skew": 0.0,
    "overall_quality": 0.85
  },
  "composition": {
    "script_count": 2,
    "is_multilingual": true,
    "primary_script": "Latn"
  }
}
```

### Directory Structure

```text
synthetic_multiscript/
├── Arab/
│   ├── {uuid}.png
│   └── {uuid}.json
├── Armn/
├── Beng/
├── Cyrl/
├── Deva/
├── ... (27 script folders)
└── metadata/
    └── generation_config.json
```

### Key Features

- **Multi-script documents**: 65% have 2-4 scripts per image
- **Synthetic IQA labels**: 8 quality dimensions (blur, noise, skew, etc.)
- **Layout metadata**: Document layout type and text density
- **Per-region bounding boxes**: COCO format for each script region
- **Text corpus**: OpenLID-v2 (authentic language samples)

### Target Model Performance

| Metric | Target |
|--------|--------|
| Overall Accuracy | ≥90% |
| Per-script Accuracy | ≥80% (min) |
| Multi-script Detection | ≥85% |

---

## Appendix: Template for New Training Datasets

See [TRAINING_DATASET_TEMPLATE.md](TRAINING_DATASET_TEMPLATE.md) for the standard template to document new training datasets.

---

## Appendix: Generation Scripts

| Dataset | Script | Location |
|---------|--------|----------|
| orientation | `prepare_orientation_dataset.py` | [scripts/](../scripts/prepare_orientation_dataset.py) |
| synthetic_multiscript | (synthetic generator) | TBD |

---

## Appendix: Related Documentation

- **Design Specification**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)
- **Script Detection Review**: [synth-multiscript-250k_review.md](datasets/reviews/synth-multiscript-250k_review.md)
- **Source Dataset Catalog**: [DATASET_CATALOG.md](DATASET_CATALOG.md)
- **Layer 2 Schema**: [layer2_enrichment.schema.json](schema/layer2_enrichment.schema.json)

---

**Last Updated**: 2026-02-01
**Maintained By**: Data team
