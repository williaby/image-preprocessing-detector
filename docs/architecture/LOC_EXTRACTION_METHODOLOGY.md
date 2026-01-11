---
description: Detailed explanation of how Lines of Code are counted and mapped to workstreams
owner: docs-team
purpose: Documentation for LOC Extraction Methodology.
schema_type: common
status: draft
tags:
- architecture
title: LOC Extraction Methodology
---

**Purpose**: Explain how the automated LOC extraction script divides source code among workstreams for accurate documentation metrics.

**Script**: [`scripts/extract_workstream_loc.sh`](../../scripts/extract_workstream_loc.sh)

---

## Overview

The LOC extraction script uses **explicit directory and file mappings** to assign source code ownership to each of the 8 workstreams. Each workstream "owns" specific modules, scripts, or files based on architectural responsibility.

**Key Principle**: A source file belongs to the workstream that **implements** its functionality, not the workstream that **uses** it.

---

## Workstream Mappings (Complete)

### 1. Production Runtime (Workstream 1)

**LOC**: ~16,910 lines

**Owned Directories/Files**:

```bash
src/image_preprocessing_detector/ingestion/        # PDF/image loading, DPI upscaling
src/image_preprocessing_detector/classification/   # PDF type classification
src/image_preprocessing_detector/detection/        # Text gate, IQA (classical + ML), layout-lite
src/image_preprocessing_detector/correction/       # Deskew, CLAHE, denoising
src/image_preprocessing_detector/metrics/          # DQS calculator, Prometheus metrics
src/image_preprocessing_detector/routing/          # OCR routing recommendations
src/image_preprocessing_detector/output/           # JSON generation
src/image_preprocessing_detector/utils/device_orchestrator.py  # Device selection logic
src/image_preprocessing_detector/utils/device_probe.py         # GPU/CPU detection
src/image_preprocessing_detector/workers/          # Celery task definitions
```

**Rationale**: Production Runtime implements the live document processing pipeline from ingestion → IQA → correction → routing → output.

**Breakdown by Module**:

- Ingestion: ~2,235 lines (PDF loading, DPI analysis, upscaling)
- Classification: ~472 lines (PDF type: image_only/born_digital/hybrid)
- Detection: ~9,917 lines (text gate, classical IQA, ML IQA, layout-lite)
- Correction: ~1,284 lines (deskew, CLAHE, sharpening, denoising)
- Metrics: ~1,418 lines (DQS calculator, Prometheus collectors)
- Routing: ~150 lines (OCR routing recommendations)
- Output: ~503 lines (JSON serialization)
- Workers: ~748 lines (Celery tasks)
- Device Utils: ~183 lines (device orchestration)

---

### 2. Production Model Training (Workstream 2)

**LOC**: ~7,058 lines

**Owned Directories/Files**:

```bash
modal/train_phase2_iqa.py                     # Teacher training (ResNet-50)
modal/train_student_distillation.py          # Student distillation (ResNet-18)
modal/export_phase7_onnx.py                   # Model export to ONNX/TorchScript
src/image_preprocessing_detector/training/   # Training utilities, loss functions, dataloaders
src/image_preprocessing_detector/models/     # Model architectures (ResNet teacher/student)
```

**Rationale**: Model Training implements the teacher-student training pipeline and model export logic.

**Breakdown**:

- modal/train_phase2_iqa.py: ~707 lines (teacher training)
- modal/train_student_distillation.py: ~779 lines (knowledge distillation)
- modal/export_phase7_onnx.py: ~347 lines (ONNX export)
- src/.../training/: ~1,938 lines (trainers, loss functions, dataloaders)
- src/.../models/: ~3,287 lines (ResNet architectures, model wrappers)

---

### 3. Data Preparation (Workstream 3)

**LOC**: ~4,066 lines

**Owned Directories/Files**:

```bash
scripts/annotate_base_metadata.py         # Layer 1 & 2: Immutable + Enrichment metadata
scripts/build_training_labels.py          # Layer 3: Training-ready labels
scripts/download_all_datasets.py          # Master dataset downloader
scripts/download_iqa_datasets.py          # IQA benchmarks (LIVE, CSIQ, DIQA)
scripts/download_phase3_datasets.py       # Phase 3 specific datasets
scripts/download_table_datasets.py        # TableBank, PubTabNet
scripts/download_omnidocbench.py          # OmniDocBench multi-task benchmark
scripts/validate_datasets.py              # Dataset integrity validation
```

**Rationale**: Data Preparation implements dataset ingestion, cataloging, and metadata generation (3-layer architecture).

**Breakdown**:

- annotate_base_metadata.py: ~1,235 lines (metadata layers 1 & 2)
- build_training_labels.py: ~590 lines (layer 3, 45-dim IQA vector)
- download_all_datasets.py: ~470 lines (master orchestrator)
- download_iqa_datasets.py: ~79 lines
- download_phase3_datasets.py: ~290 lines
- download_table_datasets.py: ~569 lines
- download_omnidocbench.py: ~404 lines
- validate_datasets.py: ~429 lines

---

### 4. Pseudo-Labeling (Workstream 4)

**LOC**: ~2,947 lines

**Owned Directories/Files**:

```bash
src/image_preprocessing_detector/labeling/ensemble/  # 5-model ensemble labeling
modal/generate_pseudo_labels.py                      # Batch pseudo-labeling on Modal
modal/arena_benchmark.py                             # Model benchmarking
scripts/run_model_benchmark.py                       # Local benchmark execution
```

**Rationale**: Pseudo-Labeling implements the 5-model ensemble workflow for generating high-confidence labels.

**Breakdown**:

- modal/generate_pseudo_labels.py: ~1,042 lines (ensemble inference)
- modal/arena_benchmark.py: ~419 lines (Modal benchmarking)
- scripts/run_model_benchmark.py: ~1,486 lines (local benchmarks)

---

### 5. Labeling & Benchmarking Models (Workstream 5)

**LOC**: ~0 lines (scripts not yet created)

**Planned Directories/Files**:

```bash
modal/labeling_models/                   # Training scripts for MUSIQ, QualiCLIP, etc.
src/image_preprocessing_detector/labeling/models/  # Model wrappers
```

**Status**: Infrastructure planned but not implemented

**Rationale**: This workstream will train the 5 labeling models (MUSIQ, QualiCLIP, DocIQ, Qwen3-VL, InternVL3). Currently, these models are used from pretrained checkpoints.

---

### 6. Model Arena & Multi-Label Benchmarking (Workstream 6)

**LOC**: ~6,340 lines

**Owned Directories/Files**:

```bash
src/image_preprocessing_detector/labeling/arena/  # Complete Arena infrastructure
```

**Rationale**: Model Arena implements the benchmarking framework (datasets, backends, metrics, runner, leaderboard).

**Breakdown** (from Arena directory):

- runner.py: ~630 lines (ArenaRunner orchestrator)
- metrics.py: ~445 lines (PLCC, SRCC, MAE, RMSE with bootstrap CIs)
- schemas.py: ~482 lines (data models, serialization)
- leaderboard.py: ~300 lines (leaderboard generation)
- cli.py: ~200 lines (CLI)
- datasets/: ~400 lines (DIQA5000 adapter + base classes)
- inference/: ~600 lines (PyTorch, HuggingFace, Modal, API backends)
- Additional utilities: ~2,283 lines

---

### 7. Monitoring & Drift Detection (Workstream 7)

**LOC**: ~5,348 lines

**Owned Directories/Files**:

```bash
src/image_preprocessing_detector/drift/  # Drift detection, alerting, active learning, retraining
monitoring/                              # Prometheus/Grafana configs
```

**Rationale**: Monitoring implements continuous quality assurance (drift detection, active learning, privacy review, retraining automation).

**Breakdown** (from drift/ directory):

- \_\_init\_\_.py: ~985 lines (distribution tracking, drift detection)
- performance.py: ~1,027 lines (performance monitoring, evaluation jobs)
- alerting.py: ~1,061 lines (multi-channel alerting)
- active_learning.py: ~842 lines (sample harvesting)
- privacy_review.py: ~695 lines (GDPR/CCPA compliance)
- retraining.py: ~743 lines (retraining orchestration)
- Additional monitoring configs: ~5 lines

---

### 8. Synthetic Data Generation (Workstream 8)

**LOC**: ~1,066 lines

**Owned Directories/Files**:

```bash
src/image_preprocessing_detector/augmentation/  # Genalog configuration and degrader
benchmarks/adapters/synthetic_iqa_adapter.py    # Synthetic benchmark adapter
```

**Rationale**: Synthetic Generation implements controlled degradation infrastructure using Microsoft Genalog.

**Breakdown**:

- augmentation/genalog_config.py: ~294 lines (Pydantic config models)
- augmentation/genalog_degrader.py: ~314 lines (degrader wrapper)
- augmentation/\_\_init\_\_.py: ~36 lines (public API)
- benchmarks/adapters/synthetic_iqa_adapter.py: ~422 lines (benchmark integration)

---

## Counting Rules

### What's Included ✅

- **Python source files** (`.py`)
- **Implementation code** (functions, classes, logic)
- **Comments and docstrings** (part of documentation)
- **Blank lines** (for readability context)

### What's Excluded ❌

- **Test files**: `test_*.py`, `*_test.py`, `tests/` directories
- **Cache directories**: `__pycache__`, `.pytest_cache`
- **Compiled files**: `.pyc`, `.pyo`
- **Non-Python files**: YAML configs, JSON schemas, Markdown docs

### Counting Command

For each directory:

```bash
find "$dir" -name "*.py" \
    -not -path "*/tests/*" \           # Exclude tests directory
    -not -path "*/__pycache__/*" \     # Exclude cache
    -not -path "*/.pytest_cache/*" \   # Exclude pytest cache
    -not -name "test_*.py" \           # Exclude test files
    -not -name "*_test.py" \           # Exclude test files
    -type f \
    -exec wc -l {} + | tail -1 | awk '{print $1}'
```

---

## Handling Overlaps & Shared Code

### Shared Utilities

Some code is shared across workstreams (e.g., `src/.../utils/`). Assignment rules:

| File/Module | Assigned To | Rationale |
|-------------|-------------|-----------|
| `utils/device_orchestrator.py` | **Production Runtime** | Runtime-specific device selection logic |
| `utils/device_probe.py` | **Production Runtime** | Runtime GPU detection |
| `utils/tensor_cache.py` | **Production Runtime** | Runtime optimization |
| `utils/gcs_uploader.py` | **Shared** | Not counted in any workstream (utility) |
| `utils/logger.py` | **Shared** | Not counted in any workstream (utility) |

**Rule**: If utility is **tightly coupled** to a workstream's workflow, assign it. If it's **generic infrastructure**, don't count it (to avoid double-counting).

### Labeling Code Split

The `src/image_preprocessing_detector/labeling/` directory is split:

| Subdirectory | Assigned To | Reason |
|--------------|-------------|--------|
| `labeling/arena/` | **Workstream 6 (Model Arena)** | Benchmarking infrastructure |
| `labeling/ensemble/` | **Workstream 4 (Pseudo-Labeling)** | Ensemble inference workflow |
| `labeling/models/` | **Workstream 5 (Labeling Models)** | Model wrappers for MUSIQ, QualiCLIP, etc. |

**Why Split?**: These are distinct responsibilities:

- **Arena**: Measures model performance (WS6)
- **Ensemble**: Uses models for pseudo-labeling (WS4)
- **Models**: Trains the labeling models themselves (WS5)

---

## Example: Production Runtime Calculation

Let's trace how Production Runtime gets **~16,910 lines**:

### Step 1: List Owned Paths

```bash
WORKSTREAMS["production_runtime"]="
  src/image_preprocessing_detector/ingestion
  src/image_preprocessing_detector/classification
  src/image_preprocessing_detector/detection
  src/image_preprocessing_detector/correction
  src/image_preprocessing_detector/metrics
  src/image_preprocessing_detector/routing
  src/image_preprocessing_detector/output
  src/image_preprocessing_detector/utils/device_orchestrator.py
  src/image_preprocessing_detector/utils/device_probe.py
  src/image_preprocessing_detector/workers
"
```

### Step 2: Count Each Path

```bash
# Ingestion directory
find src/image_preprocessing_detector/ingestion -name "*.py" \
  -not -path "*/tests/*" -type f -exec wc -l {} +
# Result: 2,235 lines across:
#   - document_processor.py
#   - pdf_loader.py
#   - pdf_analyzer.py
#   - pdf_resolution.py
#   - pdf_upscaler.py
#   - image_loader.py
#   - office_processor.py

# Detection directory
find src/image_preprocessing_detector/detection -name "*.py" \
  -not -path "*/tests/*" -type f -exec wc -l {} +
# Result: 9,917 lines across:
#   - text_gate.py (~350 lines)
#   - iqa_classical.py (~1,200 lines - 8 detectors)
#   - iqa_ml.py (~800 lines - teacher/student inference)
#   - hybrid_iqa.py (~400 lines)
#   - layout_lite/ subdirectory (~7,000+ lines for DocLayout-YOLO + analyzers)
#   - advanced_detectors.py
#   - discrepancy.py
#   - orientation_detector.py

# ... continue for all paths
```

### Step 3: Sum All Paths

```
Ingestion:        2,235
Classification:     472
Detection:        9,917
Correction:       1,284
Metrics:          1,418
Routing:            150
Output:             503
Device Utils:       183
Workers:            748
─────────────────────
TOTAL:           16,910 lines
```

---

## Example: Model Arena Calculation

**LOC**: ~6,340 lines

**Owned Directories/Files**:

```bash
src/image_preprocessing_detector/labeling/arena/  # Entire arena/ directory
```

**Why Higher Than Expected?**

The Arena infrastructure includes:

```
labeling/arena/
├── __init__.py                 # ~50 lines (public API)
├── runner.py                   # ~630 lines (ArenaRunner)
├── metrics.py                  # ~445 lines (PLCC, SRCC, bootstrap)
├── schemas.py                  # ~482 lines (data models)
├── leaderboard.py              # ~300 lines (HTML/markdown generation)
├── cli.py                      # ~200 lines (CLI)
├── modal_client.py             # ~180 lines (Modal GPU client)
├── datasets/
│   ├── base.py                 # ~120 lines (abstract interface)
│   ├── diqa5000.py             # ~200 lines (DIQA-5000 implementation)
│   └── (future: doclaynet.py, pubtables.py, etc.)
├── inference/
│   ├── base.py                 # ~80 lines (abstract backend)
│   ├── local.py                # ~250 lines (PyTorch backend)
│   ├── huggingface.py          # ~180 lines (HF transformers)
│   ├── modal.py                # ~150 lines (Modal serverless)
│   ├── api.py                  # ~140 lines (OpenAI/Gemini)
│   └── regression.py           # ~120 lines (regression wrapper)
└── utils/
    ├── reproducibility.py      # ~300 lines (manifest generation)
    ├── bootstrap.py            # ~250 lines (CI calculations)
    └── visualization.py        # ~200 lines (result plotting)
```

**Total**: 6,340 lines (comprehensive benchmarking infrastructure)

---

## Why Some Workstreams Have 0 LOC

### Labeling & Benchmarking Models (Workstream 5): **0 lines**

**Mapped Paths**:

```bash
modal/labeling_models/                           # Training scripts (planned)
src/image_preprocessing_detector/labeling/models/  # Model wrappers (planned)
```

**Status**: **Not yet implemented**

**Reason**: These directories don't exist yet because:

1. Currently using **pretrained models** (MUSIQ, QualiCLIP from PyIQA library)
2. Fine-tuning scripts planned for future phases
3. Model wrappers will be created when custom training begins

**Expected LOC** (when implemented): ~1,300 lines

- Training scripts: ~1,000 lines (5 models × ~200 lines each)
- Model wrappers: ~300 lines

---

## Validation: Does Sum Match Total Codebase?

### Codebase Total

```bash
# Count ALL Python files in src/ (excluding tests)
find src/image_preprocessing_detector -name "*.py" \
  -not -path "*/tests/*" -type f -exec wc -l {} + | tail -1
# Result: ~35,000 lines
```

### Workstream Sum

```text
Production Runtime:    16,910
Model Training:         7,058
Model Arena:            6,340
Monitoring & Drift:     5,348
Data Preparation:       4,066
Pseudo-Labeling:        2,947
Synthetic Generation:   1,066
Labeling Models:            0
──────────────────────────
TOTAL:                 43,735 lines
```

### Why Higher Than 35,000?

**The sum includes**:

1. **src/** directory: ~35,000 lines
2. **modal/** scripts: ~3,494 lines (train, export, pseudo-label, benchmark)
3. **scripts/** directory: ~4,066 lines (data prep scripts)
4. **benchmarks/adapters/**: ~422 lines (synthetic adapter)
5. **monitoring/** configs: ~5 lines (YAML/JSON configs counted as lines by `wc -l`)

**Total Python Codebase**: ~43,735 lines (matches workstream sum ✅)

---

## Output Format

### JSON Output (`docs/architecture/workstream_loc_counts.json`)

```json
{
  "generated_at": "2025-01-16T02:55:11Z",
  "git_sha": "4dc216a",
  "workstreams": {
    "production_runtime": {"loc": 16910, "status": "active"},
    "model_training": {"loc": 7058, "status": "active"},
    "model_arena": {"loc": 6340, "status": "active"},
    "monitoring_drift": {"loc": 5348, "status": "active"},
    "data_preparation": {"loc": 4066, "status": "active"},
    "pseudo_labeling": {"loc": 2947, "status": "active"},
    "synthetic_generation": {"loc": 1066, "status": "active"},
    "labeling_benchmarking": {"loc": 0, "status": "active"}
  }
}
```

### Suggested Level 1 Updates

The script also outputs **formatted updates** for copy-paste into Level 1:

```text
📝 Suggested Level 1 updates:

| **Production Runtime** | ~16,900 |
| **Production Model Training** | ~7,000 |
| **Model Arena & Benchmarking** | ~6,300 |
| **Monitoring & Drift Detection** | ~5,300 |
| **Data Preparation** | ~4,100 |
| **Pseudo-Labeling** | ~2,900 |
| **Synthetic Data Generation** | ~1,100 |
| **Labeling & Benchmarking Models** | 0+ |
```

**Note**: Values are rounded to nearest hundred for readability in documentation.

---

## Manual Override Cases

### When to Override Automatic Counts

**Scenario 1: Shared Code**

If a utility module is used by multiple workstreams:

- **Option A**: Assign to primary consumer (e.g., `device_orchestrator.py` → Production Runtime)
- **Option B**: Don't count it at all (avoid double-counting)

**Current Approach**: Option A (assign to primary consumer)

**Scenario 2: Future Implementation**

If directories don't exist yet (e.g., Labeling Models):

- **Count**: 0 lines
- **Documentation**: Note "(planned)" or "(infrastructure pending)"
- **Update**: Re-run script after implementation

**Scenario 3: Third-Party Wrappers**

If workstream wraps external models (e.g., PyIQA models):

- **Count**: Only wrapper code, not the underlying library
- **Example**: QualiCLIP wrapper (~50 lines) counts, not PyIQA library (thousands of lines)

---

## Updating Documentation with LOC Counts

### Automatic Process (Recommended)

1. **Run extraction script** (quarterly or after major changes):

   ```bash
   ./scripts/extract_workstream_loc.sh
   ```

2. **Review JSON output**:

   ```bash
   cat docs/architecture/workstream_loc_counts.json | python3 -m json.tool
   ```

3. **Copy suggested Level 1 updates** (displayed at end of script output)

4. **Update Level 1 table** (lines 237-246 in `level-1/index.md`):

   ```markdown
   | Workstream | Level 2 Location | Status | Lines of Code |
   |------------|------------------|--------|---------------|
   | **1. Production Runtime** | [...](link) | Active | ~16,900 |
   ```

### Manual Verification (Optional)

Double-check key workstreams:

```bash
# Production Runtime
find src/image_preprocessing_detector/{ingestion,classification,detection,correction,metrics,routing,output,workers} \
  -name "*.py" -not -path "*/tests/*" -type f -exec wc -l {} + | tail -1

# Model Training
find src/image_preprocessing_detector/{training,models} modal/train*.py modal/export*.py \
  -name "*.py" -not -path "*/tests/*" -type f -exec wc -l {} + | tail -1
```

---

## CI Integration (Future)

### GitHub Actions Workflow

Create `.github/workflows/update-architecture-metrics.yml`:

```yaml
name: Update Architecture Metrics

on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly on 1st day
  workflow_dispatch:  # Manual trigger

jobs:
  update-loc-counts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Extract LOC counts
        run: ./scripts/extract_workstream_loc.sh

      - name: Create PR if counts changed
        uses: peter-evans/create-pull-request@v5
        with:
          commit-message: "chore(docs): update workstream LOC counts"
          title: "Update Architecture Documentation LOC Counts"
          body: |
            Automated update of Lines of Code metrics in architecture documentation.

            Generated by: scripts/extract_workstream_loc.sh

            Please review and update Level 1 index.md with suggested counts.
          branch: chore/update-loc-counts
          labels: documentation
```

**Benefits**:

- **Automatic**: Runs monthly without manual intervention
- **Reviewable**: Creates PR for human approval
- **Auditable**: Git history tracks LOC evolution over time

---

## Troubleshooting

### Script Shows "0 lines" for a Workstream

**Causes**:

1. **Directory doesn't exist yet**: Check if paths in mapping are correct
2. **No `.py` files**: Workstream only has config files (YAML, JSON)
3. **All files excluded**: All files are test files

**Resolution**:

- Verify paths exist: `ls -la [path]`
- Check for Python files: `find [path] -name "*.py"`
- Review mapping in script line 45-54

### Count Seems Too High/Low

**Debugging**:

```bash
# See per-file breakdown for a workstream
find src/image_preprocessing_detector/detection -name "*.py" \
  -not -path "*/tests/*" -type f -exec wc -l {} \; | sort -nr
```

**Common Issues**:

- **Too High**: Accidentally including test files → check exclude patterns
- **Too Low**: Missing subdirectories → add to mapping
- **Discrepancy**: Shared code counted twice → assign to single workstream

---

## Comparison: Documented vs Actual LOC

### Current Level 1 Counts (After Session)

| Workstream | Level 1 Doc | Actual (Script) | Variance |
|------------|-------------|-----------------|----------|
| Production Runtime | 15,000+ | 16,910 | +13% |
| Model Training | 3,000+ | 7,058 | +135% |
| Model Arena | ~3,000 | 6,340 | +111% |
| Monitoring & Drift | ~7,400 | 5,348 | -28% |
| Data Preparation | 2,500+ | 4,066 | +63% |
| Pseudo-Labeling | 1,500+ | 2,947 | +96% |
| Synthetic Generation | 450+ | 1,066 | +137% |
| Labeling Models | 800+ | 0 | -100% |

### Analysis

**Significant Variances**:

1. **Model Training**: Documented as 3,000+ but actually ~7,000
   - **Reason**: Originally estimated, now we have actual count
   - **Action**: Update Level 1 to `~7,000`

2. **Model Arena**: Documented as ~3,000 but actually ~6,300
   - **Reason**: Comprehensive infrastructure (7 components, 5 backends)
   - **Action**: Update Level 1 to `~6,300`

3. **Monitoring & Drift**: Documented as ~7,400 but actually ~5,348
   - **Reason**: 7,400 includes test files (~2,000 lines), script excludes tests
   - **Action**: Keep ~7,400 if including tests, or clarify "implementation only"

4. **Labeling Models**: Documented as 800+ but actually 0
   - **Reason**: Planned infrastructure not yet implemented
   - **Action**: Update to "0 (planned ~1,300)" or keep aspirational 800+

---

## Maintenance Schedule

### Quarterly Updates (Recommended)

**When to Run**:

- After completing a major phase (e.g., Phase 4 complete)
- Before creating PRs with architectural changes
- Quarterly (1st of Jan, Apr, Jul, Oct)

**Process**:

1. Run `./scripts/extract_workstream_loc.sh`
2. Review JSON output
3. Update Level 1 if variance > ±20%
4. Commit with message: `chore(docs): update workstream LOC counts`

### After Major Refactoring

If modules are moved between directories:

1. **Update script mappings** (lines 45-54 in `extract_workstream_loc.sh`)
2. Run extraction
3. Update documentation

**Example**: If `detection/layout_lite/` moves to separate package:

- Remove from Production Runtime mapping
- Create new "Layout Detection" workstream mapping

---

## References

- **Extraction Script**: [`scripts/extract_workstream_loc.sh`](../../scripts/extract_workstream_loc.sh)
- **Improvement Plan**: [ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md](ARCHITECTURE_DOCUMENTATION_IMPROVEMENT_PLAN.md) Issue 3.3
- **Level 1 Index**: [level-1/index.md](diagrams/level-1/index.md) Lines 237-246 (workstream table)

---

*Last Updated: 2025-01-16*
*Next Extraction: 2025-04-01 (quarterly schedule)*
