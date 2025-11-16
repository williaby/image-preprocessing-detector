---
schema_type: common
title: "DVC Workflow Guide"
tags:
  - datasets
  - infrastructure
status: published
owner: docs-team
purpose: DVC workflow guide for dataset versioning and management.
---

**Data Version Control (DVC)** is used to track large datasets and model files without storing them in Git.

## Setup

DVC is initialized in this project with a local remote storage for development.

```bash
# DVC is already initialized
# Remote storage configured at: .dvc/cache_local
```

## Tracked Datasets

The following datasets are tracked with DVC:

### Training Data
- **Location**: `data/training/iqa_phase2/`
- **DVC File**: `data/training/iqa_phase2.dvc`
- **Size**: ~18.6 GB
- **Files**: 50,003 files
- **Purpose**: Phase 2 IQA training dataset with weak supervision labels

### Benchmarks

#### OHR-Bench

- **Location**: `data/benchmarks/ohr-bench/`
- **DVC File**: `data/benchmarks/ohr-bench.dvc`
- **Size**: ~1.8 GB
- **Purpose**: RAG-specific OCR benchmark for IQA evaluation

#### OmniDocBench (Phase 3)

- **Location**: `data/benchmarks/omnidocbench/`
- **DVC File**: `data/benchmarks/omnidocbench.dvc`
- **Size**: ~1.2 GB
- **Purpose**: Comprehensive document understanding evaluation

#### TableBank (Phase 2)

- **Location**: `data/benchmarks/tablebank/`
- **DVC File**: `data/benchmarks/tablebank.dvc`
- **Size**: ~400 MB to 27 GB (depends on version)
- **Purpose**: Table detection benchmark

#### PubTabNet (Phase 2)

- **Location**: `data/benchmarks/pubtabnet/`
- **DVC File**: `data/benchmarks/pubtabnet.dvc`
- **Size**: ~500 MB to 16 GB (depends on version)
- **Purpose**: Table structure recognition benchmark

#### FinTabNet (Phase 2)

- **Location**: `data/benchmarks/fintabnet/`
- **DVC File**: `data/benchmarks/fintabnet.dvc`
- **Size**: ~3 GB to 11 GB (depends on version)
- **Purpose**: Financial table detection and structure

#### WiLI-2018 (Phase 2)

- **Location**: `data/benchmarks/wili_2018/`
- **DVC File**: `data/benchmarks/wili_2018.dvc`
- **Size**: ~800 MB
- **Purpose**: Language identification (235 languages)

#### ICDAR MLT 2019 (Phase 2)

- **Location**: `data/benchmarks/icdar_mlt_2019/`
- **DVC File**: `data/benchmarks/icdar_mlt_2019.dvc`
- **Size**: ~3 GB
- **Purpose**: Multi-lingual text detection

**Note**: Synthetic IQA datasets (auto-generated) and DocLayNet (symlinked) are NOT tracked in DVC.

## Common Commands

### Pull Datasets
```bash
# Pull all tracked datasets
poetry run dvc pull

# Pull specific dataset
poetry run dvc pull data/training/iqa_phase2.dvc
poetry run dvc pull data/benchmarks/ohr-bench.dvc
```

### Add New Data to Tracking
```bash
# Add a new dataset directory
poetry run dvc add data/training/new_dataset

# Commit the .dvc file to git
git add data/training/new_dataset.dvc
git commit -m "Add new dataset to DVC tracking"

# Push data to remote storage
poetry run dvc push
```

### Update Existing Data
```bash
# After modifying a tracked dataset
poetry run dvc add data/training/iqa_phase2

# Commit updated .dvc file
git add data/training/iqa_phase2.dvc
git commit -m "Update IQA training dataset"

# Push updated data
poetry run dvc push
```

### Check Status
```bash
# See which datasets have changed
poetry run dvc status

# See data cache status
poetry run dvc cache dir
```

### Remove Data Locally (Keep Tracking)
```bash
# Remove local copy of dataset (keeps .dvc file)
rm -rf data/training/iqa_phase2

# Restore from DVC cache
poetry run dvc pull data/training/iqa_phase2.dvc
```

## Remote Storage

### Current Configuration
- **Type**: Local filesystem
- **Location**: `.dvc/cache_local`
- **Default**: Yes

### Adding Additional Remotes

For production or team collaboration, you can add cloud storage remotes:

#### AWS S3
```bash
poetry run dvc remote add -d s3remote s3://my-bucket/dvc-storage
poetry run dvc remote modify s3remote region us-east-1
```

#### Google Cloud Storage
```bash
poetry run dvc remote add -d gcsremote gs://my-bucket/dvc-storage
poetry run dvc remote modify gcsremote projectname my-project
```

#### SSH/SFTP
```bash
poetry run dvc remote add -d sshremote ssh://user@example.com/path/to/dvc-storage
```

### List Remotes
```bash
poetry run dvc remote list
```

## CI/CD Integration

In CI pipelines, datasets can be pulled automatically:

```yaml
# Example GitHub Actions workflow
steps:
  - name: Setup DVC
    run: poetry install --with dev,ml

  - name: Pull datasets
    run: poetry run dvc pull

  - name: Run tests
    run: poetry run pytest
```

## Best Practices

1. **Never commit large files to Git** - Always use DVC for files >10MB
2. **Commit .dvc files to Git** - These small metadata files belong in version control
3. **Use meaningful dataset names** - Make it clear what each dataset contains
4. **Document dataset changes** - Include details in commit messages when updating .dvc files
5. **Regular cleanup** - Use `dvc gc` to remove unused data from cache

## Troubleshooting

### Dataset Not Found
```bash
# Pull from remote
poetry run dvc pull data/training/iqa_phase2.dvc
```

### Cache Issues
```bash
# Verify cache
poetry run dvc cache dir

# Rebuild cache
poetry run dvc cache rebuild
```

### Permission Errors
```bash
# Fix permissions on cache
chmod -R u+w .dvc/cache
```

## Integration with Project Phases

- **Phase 2 (Current)**: IQA training dataset tracked (`data/training/iqa_phase2`)
- **Phase 3**: YOLOv8 layout detection datasets (to be added)
- **Phase 4+**: Additional datasets as needed

## References

- [DVC Documentation](https://dvc.org/doc)
- [DVC with Poetry](https://dvc.org/doc/install/poetry)
- [DVC Remote Storage](https://dvc.org/doc/command-reference/remote)

---

*Last Updated: 2025-11-16*
*Status: Active - Phase 2*
