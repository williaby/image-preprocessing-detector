---
l4_category: training-dataset
l4_dataset: orientation
l4_workstream: WS2
l4_source_datasets:
  - doclaynet
  - tablebank
  - pubtabnet
  - rvl-cdip
  - funsd
  - sroie
  - nist-sd19
  - jssoda
  - arabic-docs
  - bhutan-afs
l4_generation_script: scripts/generate_orientation_dataset.py
l4_image_count: 50000
l4_status: active
---

## orientation

> **Quick Stats**: 50,000 images | 4-class balanced | 12,500 unique documents
>
> **Status**: ⚠️ LATIN-BIASED | **Created**: 2026-01-25
>
> The review (2026-02-21) found <1% non-Latin images across source documents. This fails the
> corpus diversity requirement and the MNV4-H1 bootstrap must use this dataset with awareness
> that non-Latin orientation detection is undertrained.

### Overview

Orientation detection training dataset for Phase 10A. Each unique source document is rotated to all four cardinal orientations (0°, 90°, 180°, 270°) with varied degradation levels.

**Purpose**: Train MobileNetV4-Conv-S orientation classifier for preprocessing pipeline.

**Design Specification**: [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md)

## Known Gaps

| Gap | Priority | Description |
|-----|----------|-------------|
| ORIENT-G01 | P1 | orientation_ambiguous class not labeled — symmetric documents (squares, circles) have no valid orientation label; these must be identified and excluded or given a 5th class |
| ORIENT-G02 | P1 | Latin dominance: <1% non-Latin images in source documents; non-Latin script orientation detection is undertrained |
| ORIENT-G03 | P1 | Needs non-Latin source augmentation (Arabic RTL, Japanese TTB, Hebrew) before SigLIP G3-1 fine-tuning |

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

**Usability**: This dataset is usable for initial MNV4-H1 bootstrap but must be rebalanced with
non-Latin sources before SigLIP G3-1 fine-tuning. Do not use as-is for the SigLIP orientation head.
