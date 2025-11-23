---
schema_type: common
title: "Dual Storage Strategy"
tags:
  - datasets
  - infrastructure
  - gcs
status: published
owner: docs-team
purpose: Three-tier storage architecture for datasets across local, NFS, and cloud.
---

## Design Principles

1. **Local (WSL)**: Fast access for development, test fixtures, temporary synthetic augmentation
2. **NFS (Unraid)**: Large datasets, training data, benchmarks (48TB available)
3. **GCS (Cloud)**: Backup/fallback, remote access, disaster recovery

## Storage Tiers

### Tier 1: LOCAL (WSL Fast Storage)
**Total Budget**: <5 GB
**Purpose**: Development speed, test execution, temporary work

```
/home/byron/dev/image_detection/data/
├── test_fixtures/           # 824KB - KEEP LOCAL
│   ├── doclaynet/          # Small PDFs for unit tests
│   ├── tablebank/          # Small images for unit tests
│   └── wili_2018/          # Text files for language detection tests
│
├── promptcraft/             # 20KB - KEEP LOCAL
│   ├── channel_config.json # Model registry config
│   ├── experimental_models.json
│   └── performance_metrics.json
│
├── augmentation_temp/       # NEW - Temporary synthetic generation
│   └── .gitignore          # Output of active augmentation jobs
│                           # Auto-cleanup after upload to NFS
│
├── benchmarks/             # Symlinks to NFS (44KB .dvc files tracked)
│   ├── tablebank -> /mnt/unraid/training_data/image_detection/benchmarks/tablebank
│   ├── pubtabnet -> /mnt/unraid/training_data/image_detection/benchmarks/pubtabnet
│   ├── diqa-5000 -> /mnt/unraid/training_data/image_detection/benchmarks/diqa-5000
│   ├── external_iqa -> /mnt/unraid/training_data/image_detection/benchmarks/external_iqa
│   └── *.dvc               # DVC metadata files (tracked in git)
│
└── training/               # Symlinks to NFS (12KB .dvc files tracked)
    ├── iqa_phase2_100k -> /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k
    └── *.dvc               # DVC metadata files (tracked in git)
```

### Tier 2: NFS (Unraid Fast Local Network)
**Total Budget**: ~200 GB (48TB available, 53% used)
**Purpose**: Large datasets, training data, benchmarks

```
/mnt/unraid/training_data/image_detection/
├── benchmarks/              # Source datasets for training generation
│   ├── tablebank/          # ~27 GB (424K images)
│   │   └── TableBank/
│   │       └── Detection/
│   │           └── images/
│   ├── pubtabnet/          # ~16 GB (500K images)
│   │   └── pubtabnet/
│   │       ├── train/
│   │       ├── val/
│   │       └── test/
│   ├── diqa-5000/          # ~11 GB (5K images)
│   │   └── train/
│   │       └── ori/
│   ├── external_iqa/       # ~2 GB (LIVE, CSIQ, FUNSD)
│   │   ├── LIVE/
│   │   ├── CSIQ/
│   │   ├── LIVE_Challenge/
│   │   └── funsd/
│   ├── doclaynet/          # ~42 GB (PDFs) - For future Phase 6
│   ├── fintabnet/          # ~11 GB
│   ├── omnidocbench/       # ~6 GB
│   ├── ohr-bench/          # ~18 GB - Document IQA benchmark
│   └── wili_2018/          # ~3 GB - Language detection
│
├── training/                # Generated training datasets
│   ├── iqa_phase2_100k/    # ~50 GB (100K synthetic samples)
│   │   ├── images/         # 100K JPG files
│   │   ├── metadata/       # Sample-level metadata
│   │   └── metadata.json   # Dataset-level metadata
│   ├── iqa_phase2/         # ~2 GB (15K samples - previous version)
│   └── layout_phase6/      # Future: Layout detection training
│
└── validation/              # Validation run outputs
    ├── iqa_benchmarks/     # IQA benchmark results
    └── end_to_end/         # Full pipeline validation
```

### Tier 3: GCS (Cloud Backup/Fallback)
**Total Budget**: Unlimited (pay-as-you-go)
**Purpose**: Backup, disaster recovery, remote Modal access

```
gs://image_detection_b/image-preprocessing-detector/
├── datasets/
│   ├── tablebank/          # Mirror of NFS benchmarks/tablebank
│   ├── pubtabnet/          # Mirror of NFS benchmarks/pubtabnet
│   ├── diqa-5000/          # Mirror of NFS benchmarks/diqa-5000
│   ├── external_iqa/       # Mirror of NFS benchmarks/external_iqa
│   ├── doclaynet/
│   ├── fintabnet/
│   ├── omnidocbench/
│   ├── ohr-bench/
│   ├── wili_2018/
│   └── iqa_phase2_100k/    # Mirror of NFS training/iqa_phase2_100k
│
├── checkpoints/            # Training checkpoints from Modal
│   └── phase2_iqa/
│       ├── epoch_10.pth
│       └── best_model.pth
│
└── models/                 # Trained models (ONNX, TorchScript)
    └── phase2_iqa/
        ├── resnet50_teacher.onnx
        └── resnet18_student.onnx
```

## Data Flow Patterns

### Pattern 1: Dataset Generation (Local → NFS → GCS)
```
1. Load source datasets from NFS (symlinked to local)
2. Generate synthetic samples to LOCAL temp dir (fast I/O)
3. Stream completed batches to NFS (100K samples)
4. DVC push from NFS to GCS (backup)
5. Cleanup local temp dir
```

### Pattern 2: Training (NFS → Modal → GCS)
```
1. Modal pulls dataset from GCS (or NFS if accessible)
2. Training runs on Modal GPU
3. Checkpoints saved to GCS every 5 epochs
4. Final models exported to GCS (ONNX, TorchScript)
```

### Pattern 3: Benchmarking (NFS → Local → Results)
```
1. Benchmark datasets on NFS (symlinked to local)
2. Run benchmarks locally (small batches, fast iteration)
3. Results saved to local (JSON, CSV)
4. Periodic backup to GCS
```

### Pattern 4: Development Testing (Local Only)
```
1. Test fixtures in local data/test_fixtures/
2. Fast unit test execution (no network I/O)
3. CI/CD uses local test fixtures
```

## Symlink Strategy

### Local Symlinks (Development)
```bash
# Benchmarks (source datasets)
data/benchmarks/tablebank -> /mnt/unraid/training_data/image_detection/benchmarks/tablebank
data/benchmarks/pubtabnet -> /mnt/unraid/training_data/image_detection/benchmarks/pubtabnet
data/benchmarks/diqa-5000 -> /mnt/unraid/training_data/image_detection/benchmarks/diqa-5000
data/benchmarks/external_iqa -> /mnt/unraid/training_data/image_detection/benchmarks/external_iqa

# Training datasets
data/training/iqa_phase2_100k -> /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k
```

### NFS Organization Principles
1. **Path parity**: NFS structure mirrors local `data/` structure
2. **No nesting**: Datasets at predictable depth (3 levels max)
3. **DVC tracking**: All NFS datasets have `.dvc` files in git
4. **Atomic uploads**: Use `gsutil rsync` for GCS backup

## DVC Configuration

### Local .dvc/config (Git-tracked)
```ini
[core]
    remote = gcs

['remote "gcs"']
    url = gs://image_detection_b/image-preprocessing-detector
    credentialpath = .gcp/service-account.json

['remote "nfs"']
    url = /mnt/unraid/training_data/image_detection
```

### Usage Patterns
```bash
# Pull from GCS (first time or if NFS unavailable)
dvc pull data/benchmarks/tablebank

# Pull from NFS (preferred for local dev)
dvc pull --remote nfs data/benchmarks/tablebank

# Push to GCS (backup)
dvc push data/training/iqa_phase2_100k

# Push to NFS (for NFS-first workflow)
dvc add data/training/iqa_phase2_100k
dvc push --remote nfs data/training/iqa_phase2_100k
```

## Storage Budget Tracking

| Tier | Current | Budget | Margin |
|------|---------|--------|--------|
| Local WSL | 1 GB | 5 GB | 4 GB |
| NFS Unraid | 53 TB | 100 TB | 47 TB |
| GCS Cloud | ~200 GB | Unlimited | N/A |

## Migration Checklist

- [ ] Create NFS directory structure
- [ ] Move large benchmarks to NFS (tablebank, pubtabnet, diqa-5000)
- [ ] Create local symlinks to NFS
- [ ] Update DVC remote configuration
- [ ] Test dataset generation with NFS source datasets
- [ ] Verify Modal can access GCS datasets
- [ ] Document Python script for NFS organization
- [ ] Add monitoring for NFS space usage
