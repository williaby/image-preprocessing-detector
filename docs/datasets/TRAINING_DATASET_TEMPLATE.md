---
owner: docs-team
purpose: Template for creating consistent training dataset documentation.
schema_type: common
status: active
tags:
- datasets
- training
- template
title: Training Dataset Documentation Template
---

> **Version**: 1.0.0
> **Last Updated**: 2026-02-01
> **Purpose**: Standardized template for documenting assembled training datasets
> **Scope**: Training datasets created/assembled from source datasets for model training

---

## Template Overview

Training datasets differ from source datasets:

- **Assembled/Generated**: Created from one or more source datasets via scripts
- **Purpose-Built**: Designed for specific ML training tasks (IQA, orientation, script detection)
- **Labeled**: May use soft labels, pseudo-labels, or parameter-based labels
- **Reproducible**: Have generation configs and scripts for reproducibility

---

## Quick Reference Format (for TRAINING_DATASET_QUICK_REFERENCE.md)

Use this condensed format in the quick reference table:

```markdown
| Dataset | Purpose | Images | Train/Val/Test | Label Type | Status |
|---------|---------|--------|----------------|------------|--------|
| stage2_diqa_ensemble | IQA ensemble training | 12,742 | 8,918/1,273/2,551 | DeQA soft-labels + MOS | ✅ Ready |
```

---

## Full Training Dataset Card Template

For individual README.md files in each training dataset directory:

```markdown
# [Dataset Name]

**Created**: YYYY-MM-DD
**Version**: X.Y.Z
**Status**: Ready / In Progress / Deprecated
**Purpose**: Brief description of training purpose

---

## Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Complete dataset name |
| **Version** | Version number |
| **Created** | Creation date |
| **Training Phase** | Phase X |
| **Model Target** | Model(s) this dataset trains |
| **Total Images** | Count |
| **Storage Size** | GB |

[1-2 paragraph description of what this dataset is and why it was created]

---

## Source Datasets

| Source Dataset | Images Used | Selection Criteria |
|----------------|-------------|-------------------|
| dataset-1 | 5,000 | Random sample |
| dataset-2 | 3,000 | Quality threshold > 0.5 |

**Total Sources**: X datasets
**Selection Script**: `scripts/assemble_xxx.py`

---

## Composition & Splits

### Split Strategy

| Split | Images | Percentage | Purpose |
|-------|--------|------------|---------|
| Train | 10,000 | 70% | Model training |
| Val | 1,500 | 10% | Hyperparameter tuning |
| Test | 3,000 | 20% | Final evaluation |
| **Total** | **14,500** | **100%** | |

### Split Method

- [ ] Official splits preserved (from source dataset)
- [ ] Random split with fixed seed
- [ ] Stratified by category/source
- [ ] By document (no image from same doc in multiple splits)

**Random Seed**: 42 (if applicable)
**Leakage Prevention**: [Describe measures taken]

---

## Label Format

### Label Type

- [ ] Hard labels (discrete classes)
- [ ] Soft labels (probability distributions)
- [ ] Pseudo-labels (model-generated)
- [ ] Parameter-based (derived from augmentation params)
- [ ] Human annotations (ground truth)

### Label Schema

```json
{
  "image_id": "string - unique identifier",
  "source_dataset": "string - original dataset name",
  "split": "string - train/val/test",
  "local_path": "string - path relative to dataset root",

  // Label fields (customize per dataset)
  "label": 0.75,
  "soft_label": [0.1, 0.2, 0.4, 0.2, 0.1],

  // Optional provenance
  "sha256": "string - file checksum"
}
```

### Label Statistics

| Metric | Value |
|--------|-------|
| Label Range | [min, max] |
| Mean | X.XX |
| Std Dev | X.XX |
| Distribution | [describe shape] |

---

## Generation Provenance

### Generation Script

```bash
python scripts/assemble_xxx.py --output /path/to/output --config config.json
```

### Configuration

```json
{
  "random_seed": 42,
  "train_ratio": 0.7,
  "val_ratio": 0.1,
  "test_ratio": 0.2,
  // ... other config parameters
}
```

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| torch | 2.0+ | Model inference (if labels generated) |

---

## Directory Structure

```
dataset_name/
├── README.md                     # This file
├── MANIFEST.json                 # Machine-readable manifest
├── splits/
│   ├── train.jsonl               # Training records
│   ├── val.jsonl                 # Validation records
│   └── test.jsonl                # Test records
├── images/
│   ├── source_1/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── source_2/
│       └── ...
├── metadata/
│   └── generation_config.json    # Generation parameters
├── checksums/
│   └── all_checksums.sha256      # File integrity verification
└── tarballs/                     # Optional: packaged splits
    ├── train.tar.gz
    ├── val.tar.gz
    └── test.tar.gz
```

---

## Training Usage

### Target Models

| Model | Architecture | Purpose |
|-------|--------------|---------|
| Model-A | ResNet-18 | Student IQA |
| Model-B | ResNet-50 | Teacher IQA |

### Training Recipe

```python
from dataset_loader import TrainingDataset

# Load dataset
train_ds = TrainingDataset(
    root="/path/to/dataset",
    split="train",
    transform=train_transforms
)

# DataLoader
train_loader = DataLoader(
    train_ds,
    batch_size=32,
    shuffle=True
)
```

### Expected Performance

| Metric | Target | Achieved | Notes |
|--------|--------|----------|-------|
| SRCC | > 0.85 | - | Spearman correlation |
| PLCC | > 0.85 | - | Pearson correlation |
| MAE | < 0.15 | - | Mean absolute error |

---

## Evaluation Strategy

### Tier 1: Primary Evaluation

| Dataset/Split | Ground Truth | Metrics |
|---------------|--------------|---------|
| This dataset test | Human MOS / Official labels | SRCC, PLCC, MAE |

### Tier 2: Secondary Evaluation (if applicable)

| Dataset | Ground Truth | Purpose |
|---------|--------------|---------|
| External benchmark | Official labels | Cross-domain generalization |

---

## Quality Assurance

### Integrity Verification

```bash
# Verify checksums
cd /path/to/dataset
sha256sum -c checksums/all_checksums.sha256
```

### Visual Inspection

Run the inspection script to verify a random sample:

```bash
python scripts/inspect_training_dataset.py --dataset dataset_name --samples 100
```

---

## Known Issues & Limitations

- **Issue 1**: Description and mitigation
- **Issue 2**: Description and mitigation

---

## Related Documents

- [Source Dataset 1](link) - Description
- [Generation Script](link) - Assembly script
- [Training Plan](link) - Overall training strategy

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | YYYY-MM-DD | Initial release |

---

*Document Version 1.0*

```

---

## MANIFEST.json Schema

Each training dataset should include a machine-readable manifest:

```json
{
  "name": "dataset_name",
  "version": "1.0.0",
  "created": "2025-12-19",
  "description": "Brief description",
  "purpose": "iqa_training | orientation | script_detection | layout | ...",
  "phase": "phase7",

  "sources": [
    {
      "name": "source_dataset_1",
      "path": "01_base_data/category/source_1/",
      "images_used": 5000
    }
  ],

  "splits": {
    "train": {"count": 10000, "path": "splits/train.jsonl"},
    "val": {"count": 1500, "path": "splits/val.jsonl"},
    "test": {"count": 3000, "path": "splits/test.jsonl"}
  },

  "totals": {
    "images": 14500,
    "size_gb": 12.5
  },

  "labels": {
    "type": "soft_labels | pseudo_labels | parameter_based | hard_labels",
    "format": "jsonl",
    "schema_version": "1.0"
  },

  "generation": {
    "script": "scripts/assemble_xxx.py",
    "config": "metadata/generation_config.json",
    "timestamp": "2025-12-19T10:00:00Z",
    "random_seed": 42
  },

  "checksums": {
    "algorithm": "sha256",
    "file": "checksums/all_checksums.sha256"
  }
}
```

---

## Status Markers

| Status | Meaning |
|--------|---------|
| ✅ Ready | Dataset complete and validated |
| 🔄 In Progress | Generation/assembly ongoing |
| ⚠️ Partial | Some splits/sources incomplete |
| ❌ Blocked | Generation blocked by dependency |
| 🗃️ Archived | Superseded by newer version |

---

## Template Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-01 | Initial template based on source dataset template patterns |
