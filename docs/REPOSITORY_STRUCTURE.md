---
schema_type: common
title: "Repository Structure Reference"
tags:
  - architecture
  - modularity
status: published
owner: docs-team
purpose: Documentation for repository structure reference.
---

**Version**: 1.0
**Last Updated**: 2025-11-13
**Status**: ✅ Complete

## Overview

This document provides a comprehensive reference for the image-preprocessing-detector repository structure. Each folder includes a README explaining its purpose, contents, and distinctions from similar folders.

**Repository Stats** (after cleanup):
- **Total Folders**: 16 (down from 23, -30% reduction)
- **Folders with READMEs**: 16 (100% coverage)
- **Build Artifacts Removed**: 4 folders
- **Consolidations**: 3 folders merged

---

## Root Directory Structure

```
image_detection/
├── .github/              # GitHub Actions workflows and templates
├── benchmarks/           # Benchmark registry, results, and reports
├── configs/              # Training configuration files (YAML/JSON)
├── data/                 # Test fixtures and benchmark datasets
├── docs/                 # Project documentation
├── fuzz/                 # Fuzzing tests (ClusterFuzzLite)
├── LICENSES/             # License texts for REUSE compliance
├── logs/                 # Runtime logs (gitignored)
├── models/               # Trained model weights (gitignored)
├── monitoring/           # Monitoring configs (Phase 4+)
├── notebooks/            # Jupyter/Colab notebooks (gitignored)
├── overrides/            # MkDocs theme customization
├── scripts/              # Dataset management and utility scripts
├── src/                  # Source code
├── tests/                # Unit and integration tests
├── tmp_cleanup/          # Temporary reference files (anti-compaction)
├── tools/                # Development tools (linting, validation)
└── validation/           # Experimental validation scripts (gitignored)
```

---

## Folder Descriptions

### Core Project Structure

#### src/
**Purpose**: Main source code library

**Contains**:
- `image_preprocessing_detector/` - Core Python package
- Module structure follows pipeline architecture
- Production-ready library code

**See**: Source code follows `src/image_preprocessing_detector/` layout

#### tests/
**Purpose**: Automated test suite

**Contains**:
- `unit/` - Unit tests
- `integration/` - Integration tests
- Test fixtures in `data/test_fixtures/`

**Coverage**: Enforces 80%+ code coverage

#### docs/
**Purpose**: Project documentation

**Contains**:
- Architecture Decision Records (ADRs)
- Planning documents
- Technical guides
- API reference

**See**: [Project documentation](../README.md#documentation)

---

### Data & Training

#### data/
**README**: [data/README.md](../data/README.md)

**Purpose**: Test fixtures and benchmark datasets (small files only)

**Contains**:
- `test_fixtures/` - Small test files for CI/CD (<50 MB total)
- `benchmarks/` - Small benchmark samples
- `annotations/` - Annotation files

**Does NOT contain**: Training datasets (→ `data/training/` gitignored)

**Distinction**:
- **data/**: Small files committed to git
- **data/training/**: Large training datasets (gitignored)
- **benchmarks/**: Benchmark results and registry

#### benchmarks/
**README**: [benchmarks/README.md](../benchmarks/README.md)

**Purpose**: Benchmark registry, evaluation results, and reports

**Contains**:
- `registry.yml` - Benchmark dataset registry
- `reports/` - Smoke test reports (moved from root)
- Benchmark results and metrics

**Distinction**:
- **benchmarks/**: Results and performance metrics
- **data/**: Actual dataset files
- **models/**: Model weights being benchmarked

---

### Development & Training

#### scripts/
**README**: [scripts/README.md](../scripts/README.md)

**Purpose**: Operational utilities for dataset management, GCS, and Colab training

**Contains**:
- `download_*.py` - Dataset download scripts
- `*_gcs.*` - Google Cloud Storage utilities
- `colab_*.py` - Colab training helpers
- `checkpoint_manager.py` - Multi-session training management

**Distinction**:
- **scripts/**: Operational utilities (reusable, production workflows)
- **tools/**: Development tools (linting, validation, code generation)
- **validation/**: One-off experimental scripts

#### configs/
**README**: [configs/README.md](../configs/README.md)

**Purpose**: Training configuration files (YAML/JSON)

**Contains**:
- `colab_phase2_iqa.yaml` - IQA training config
- `colab_phase3_yolov8.yaml` - Layout detection config
- Model architecture and hyperparameter configs

**Distinction**:
- **configs/**: Text configuration files (YAML/JSON, committed)
- **models/**: Binary model weights (.pth, .onnx, gitignored)

#### models/
**README**: [models/README.md](../models/README.md)

**Purpose**: Trained model weights and exported inference models

**Contains** (all gitignored):
- `.pth`, `.pt`, `.safetensors` - PyTorch weights
- `.onnx` - Exported ONNX models
- `metadata.json` - Model information

**Storage**: Google Drive (training), GCS (distribution), local on-demand

**Distinction**:
- **models/**: Binary model files (gitignored)
- **configs/**: Configuration files (committed)

#### notebooks/
**README**: [notebooks/README.md](../notebooks/README.md)

**Purpose**: Jupyter/Colab notebooks for interactive training

**Contains** (gitignored):
- `colab/phase2_iqa_training.ipynb` - Phase 2 IQA training
- `colab/phase3_yolov8_training.ipynb` - Phase 3 layout training
- Interactive model evaluation notebooks

**Storage**: Google Drive (working copies)

**Distinction**:
- **notebooks/**: Interactive .ipynb files (gitignored)
- **scripts/**: Standalone Python utilities
- **validation/**: One-off experimental code

---

### Validation & Testing

#### validation/
**README**: [validation/README.md](../validation/README.md)

**Purpose**: One-off experimental validation scripts (all gitignored)

**Contains** (all gitignored):
- `validate_*.py` - Experimental validation scripts
- `datasets/` - Downloaded datasets for validation
- `*.json` - Validation results

**Lifecycle**: Create → Experiment → Document in ADR → Archive/Delete

**Distinction**:
- **validation/**: Exploratory, one-off scripts (gitignored)
- **tests/**: Automated tests run in CI/CD (committed)
- **benchmarks/**: Systematic performance evaluation

#### fuzz/
**README**: [fuzz/README.md](../fuzz/README.md)

**Purpose**: Fuzzing tests for security and robustness

**Contains**:
- Fuzzing harnesses
- ClusterFuzzLite integration

**CI/CD**: Automated fuzzing in GitHub Actions

---

### Tools & Infrastructure

#### tools/
**README**: [tools/README.md](../tools/README.md)

**Purpose**: Development tools for code quality and documentation

**Contains**:
- `validate_front_matter.py` - YAML front matter validation
- `gen_tools_catalog.py` - Tools catalog generation
- `frontmatter_contract/` - Schema definitions

**Distinction**:
- **tools/**: Development-time validation (pre-deployment)
- **scripts/**: Operational utilities (datasets, training)
- **monitoring/**: Runtime monitoring (post-deployment)

#### monitoring/
**README**: [monitoring/README.md](../monitoring/README.md)

**Purpose**: Monitoring and observability configs (Phase 4+)

**Status**: Placeholder for future implementation

**Will contain**:
- Prometheus metrics configs
- Grafana dashboards
- Alert rules

**Distinction**:
- **monitoring/**: Production observability (Phase 4+)
- **tools/**: Development tooling
- **logs/**: Actual log files (gitignored)

#### tmp_cleanup/
**README**: [tmp_cleanup/README.md](../tmp_cleanup/README.md)

**Purpose**: Temporary reference files for context preservation

**Contains** (gitignored):
- `.tmp-*.md` - Temporary analysis files
- Context preservation for multi-turn tasks
- Implementation summaries

**Lifecycle**: Create → Use → Migrate to docs/ or delete

**Distinction**:
- **tmp_cleanup/**: Temporary, informal notes (gitignored)
- **docs/**: Permanent, formal documentation

---

### Documentation & Configuration

#### overrides/
**README**: [overrides/README.md](../overrides/README.md)

**Purpose**: MkDocs theme customization

**Contains**:
- `main.html` - Custom base template
- Theme overrides (Jinja2 templates)

**Distinction**:
- **overrides/**: HTML templates for docs site (committed)
- **docs/**: Markdown documentation content
- **site/**: Built documentation (gitignored)

#### LICENSES/
**README**: [LICENSES/README.md](../LICENSES/README.md)

**Purpose**: License texts for REUSE Specification compliance

**Contains**:
- `Apache-2.0.txt` - Project code license
- `CC-BY-4.0.txt` - Documentation license
- `CC0-1.0.txt`, `MIT.txt`, `ODbL-1.0.txt` - Other licenses

**REUSE**: Compliance verified in CI/CD

---

## Gitignore Strategy

### Build Artifacts (Deleted)
- ~~`__pycache__/`~~ - Python bytecode (deleted)
- ~~`htmlcov/`~~ - Coverage reports (deleted)
- ~~`site/`~~ - MkDocs output (deleted)
- ~~`dist/`~~ - Package distributions (deleted)

### Large Files (Gitignored)
- `data/training/` - Training datasets
- `models/**/*.pth` - Model weights
- `logs/` - Runtime logs
- `notebooks/**/*.ipynb` - Jupyter notebooks
- `validation/*.py` - Experimental scripts
- `tmp_cleanup/.tmp-*` - Temporary reference files

### Small Files (Committed)
- `configs/*.yaml` - Configuration files
- `scripts/*.py` - Utility scripts
- `tools/*.py` - Development tools
- `data/test_fixtures/` - Small test files (<50 MB)
- All README files

---

## Folder Consolidations

### Completed Consolidations

1. **datasets/ → data/training/**
   - Training datasets now in `data/training/` (gitignored)
   - Reduces root-level clutter

2. **reports/ → benchmarks/reports/**
   - Benchmark reports now with benchmark registry
   - Logical grouping of related artifacts

3. **logs/ → .gitignore**
   - Runtime logs gitignored, not tracked
   - Kept folder for Phase 4 monitoring integration

---

## Folder Usage Quick Reference

### "Where should I put...?"

| Item | Location | Reason |
|------|----------|--------|
| Training config (YAML) | `configs/` | Configuration files |
| Trained model (.pth) | `models/` | Model weights (gitignored) |
| Dataset download script | `scripts/` | Operational utility |
| Colab training notebook | `notebooks/` | Interactive training (gitignored) |
| One-off validation script | `validation/` | Experimental (gitignored) |
| Unit test | `tests/unit/` | Automated testing |
| Benchmark result | `benchmarks/` | Performance evaluation |
| Small test image (<1 MB) | `data/test_fixtures/` | CI/CD test data |
| Large training dataset | `data/training/` | Training data (gitignored) |
| Development tool | `tools/` | Code quality tools |
| Temporary analysis | `tmp_cleanup/` | Context preservation (gitignored) |
| Formal documentation | `docs/` | Project documentation |
| MkDocs template | `overrides/` | Documentation site customization |
| License text | `LICENSES/` | REUSE compliance |
| Production code | `src/` | Library source code |

---

## Phase-Specific Usage

### Phase 1: MVP (Current)
**Active folders**:
- `src/` - Classical CV implementation
- `tests/` - Unit/integration tests
- `scripts/` - Dataset utilities
- `data/` - Test fixtures

**Inactive**: `notebooks/`, `models/`, `monitoring/`

### Phase 2: ML for IQA (Upcoming)
**New usage**:
- `notebooks/colab/` - IQA training notebooks
- `configs/` - Training configs
- `models/iqa/` - Trained IQA models
- `data/training/iqa_phase2/` - Training datasets

### Phase 3: Layout Detection
**Additional**:
- `models/layout/` - YOLOv8 models
- `data/training/layout_phase3/` - Layout datasets
- `configs/colab_phase3_yolov8.yaml` - YOLOv8 config

### Phase 4: Production
**New folders**:
- `monitoring/` - Prometheus, Grafana configs
- `logs/` - Application logs (active)

---

## Navigation Tips

### Finding Documentation
- **Architecture**: `docs/architecture/`
- **Planning**: `docs/planning/`
- **ADRs**: `docs/ADRs/`
- **API Reference**: `docs/api/index.md`

### Finding Code
- **Core library**: `src/image_preprocessing_detector/`
- **Tests**: `tests/`
- **Scripts**: `scripts/`
- **Tools**: `tools/`

### Finding Training Artifacts
- **Configs**: `configs/`
- **Notebooks**: `notebooks/colab/`
- **Models**: `models/` (download from GCS if needed)

---

## Repository Health

### Size Guidelines
- **Keep small**: `data/`, `configs/`, `tools/`, `docs/`
- **Gitignore large**: `models/`, `data/training/`, `notebooks/`, `logs/`
- **Total repo size target**: <500 MB (excluding gitignored files)

### Maintenance
- **Monthly**: Clean `tmp_cleanup/` (delete files >60 days)
- **Per Phase**: Update README files for new usage patterns
- **Before commits**: Run pre-commit hooks to validate structure

---

## Related Documentation

- [Root README.md](../README.md) - Project overview
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [PROJECT_PLAN.md](planning/PROJECT_PLAN.md) - Complete project plan
- Individual folder README files for detailed information

---

**Maintained by**: Core maintainers
**Questions**: Open an issue on GitHub
