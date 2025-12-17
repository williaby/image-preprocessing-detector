---
schema_type: planning
title: "Phase 2 Cleanup Plan"
tags:
  - ml
  - maintenance
status: draft
owner: core-maintainer
purpose: Plan for removing deprecated Phase 2 IQA training assets.
component: training
source: internal
---

> **Created**: 2025-12-16
> **Status**: Awaiting Approval
> **Reason**: Phase 2 binary labels superseded by Phase 7 continuous severity approach

---

## Executive Summary

Phase 2 IQA training used **weak supervision labels** (BRISQUE/NIQE scores binned into 3-5
discrete levels). Phase 7 replaces this with **ground truth continuous labels** [0.0, 0.95]
derived directly from augmentation parameters, providing superior calibration and
interpretability.

**Recommendation**: Remove all Phase 2 assets to reduce confusion and repository bloat.

---

## Phase 2 vs Phase 7 Comparison

| Aspect | Phase 2 (Deprecated) | Phase 7 (Current) |
|--------|---------------------|-------------------|
| **Labels** | Weak supervision (BRISQUE/NIQE) | Ground truth from augmentation params |
| **Label Type** | Discrete bins (3-5 levels) | Continuous [0.0, 0.95] |
| **Dataset Size** | 100K samples | 25K samples (higher quality) |
| **Sources** | 3 sources | 16 diverse sources |
| **Resolution** | 224×224 | 384×384 |
| **DQS Formula** | Undocumented | Fully documented |
| **Reproducibility** | Weak (BRISQUE varies) | Strong (deterministic) |

---

## Files to Remove

### Category 1: Scripts (4 files)

```bash
scripts/prepare_phase2_data.py
scripts/prepare_phase2_hybrid.py
scripts/generate_phase2_validation_datasets.py
scripts/benchmark_phase2.py
```

### Category 2: Modal Training (2 files)

```bash
modal/train_phase2_iqa.py
modal/train_phase2_iqa_example.py
```

### Category 3: Configs (4 files)

```bash
configs/colab_phase2_iqa.yaml
configs/colab_phase2_iqa_gcs.yaml
configs/modal_phase2_iqa.yaml
configs/modal_phase2_iqa_test.yaml
```

### Category 4: Tests (3 files)

```bash
tests/integration/test_phase2_complete.py
tests/unit/scripts/test_generate_phase2_validation_datasets.py
tests/unit/scripts/test_prepare_phase2_data.py
```

### Category 5: Data Files (4 items, ~9GB)

```bash
data/training/iqa_phase2                  # symlink
data/training/iqa_phase2_100k             # symlink
data/training/iqa_phase2.dvc              # DVC tracking
data/training/iqa_phase2_100k.dvc         # DVC tracking
data/training/iqa_phase2_100k.tar.gz      # 9GB archive
```

### Category 6: Documentation (3 files to remove)

```bash
docs/PHASE2_QUICKSTART.md
docs/validation/phase2_complete_validation_summary.md
docs/ADRs/0029-phase2-dataset-selection-strategy.md
docs/ADRs/0034-resnet18-phase2-iqa.md
```

### Category 7: Notebooks (1 file)

```bash
notebooks/colab/phase2_iqa_training.ipynb
```

### Category 8: Temp/Reference Files (18 files)

```bash
tmp_cleanup/.tmp-mkdocs-phase2-part1-summary.md
tmp_cleanup/.tmp-mkdocs-phase2-tasks.md
tmp_cleanup/.tmp-phase2-branch-mapping-20251115.md
tmp_cleanup/.tmp-phase2-completion-progress-20250124.md
tmp_cleanup/.tmp-phase2-completion-update-20251201.md
tmp_cleanup/.tmp-phase2-corrected-validation-20250124.md
tmp_cleanup/.tmp-phase2-docs-analysis-20251111.md
tmp_cleanup/.tmp-phase2-implementation-20251113.md
tmp_cleanup/.tmp-phase2-implementation-roadmap-20251112.md
tmp_cleanup/.tmp-phase2-model-research-20251114.md
tmp_cleanup/.tmp-phase2-model-specification-20251114.md
tmp_cleanup/.tmp-phase2-pr-workflow-20251115.md
tmp_cleanup/.tmp-phase2-progress-20251112.md
tmp_cleanup/.tmp-phase2-training-status-20251117.md
tmp_cleanup/.tmp-phase2-validation-20250204.md
tmp_cleanup/.tmp-phase2-validation-20251114.md
tmp_cleanup/.tmp-phase2-vs-phase7-comparison-20251209.md
tmp_cleanup/.tmp-phase2-vs-phase7-comprehensive-comparison-20251209.md
tmp_cleanup/.tmp-phase2-vs-phase7-critical-differences-20251209.md
tmp_cleanup/workflows_copilot/iqa_modal_training_phase2.puml
tmp_cleanup/workflows_sonnet/02_phase2_teacher_training.puml
tmp_cleanup/workflows_sonnet/03_phase2_student_distillation.puml
```

---

## Files to Update (Not Remove)

Many docs reference "Phase 2" in historical context. These should be **updated** to clarify
Phase 2 is deprecated, not removed entirely:

### Priority Updates (mention Phase 2 as current approach)

1. `docs/guides/modal-training.md` - Update to reference Phase 7
2. `docs/guides/dataset-preparation.md` - Update to reference Phase 7
3. `docs/guides/iqa.md` - Update to reference Phase 7
4. `docs/reference/MODAL_QUICK_REFERENCE.md` - Update to reference Phase 7
5. `docs/DATASET_LOCATIONS.md` - Remove Phase 2 paths

### Low Priority (historical references OK)

- ADRs that document decisions (historical record)
- Planning docs that compare approaches
- Changelog entries

---

## Cleanup Commands

### Step 1: Remove Scripts and Modal Files

```bash
git rm scripts/prepare_phase2_data.py
git rm scripts/prepare_phase2_hybrid.py
git rm scripts/generate_phase2_validation_datasets.py
git rm scripts/benchmark_phase2.py
git rm modal/train_phase2_iqa.py
git rm modal/train_phase2_iqa_example.py
```

### Step 2: Remove Configs

```bash
git rm configs/colab_phase2_iqa.yaml
git rm configs/colab_phase2_iqa_gcs.yaml
git rm configs/modal_phase2_iqa.yaml
git rm configs/modal_phase2_iqa_test.yaml
```

### Step 3: Remove Tests

```bash
git rm tests/integration/test_phase2_complete.py
git rm tests/unit/scripts/test_generate_phase2_validation_datasets.py
git rm tests/unit/scripts/test_prepare_phase2_data.py
```

### Step 4: Remove Data Files

```bash
# Remove symlinks and DVC files (keep actual data on unraid for now)
git rm data/training/iqa_phase2
git rm data/training/iqa_phase2_100k
git rm data/training/iqa_phase2.dvc
git rm data/training/iqa_phase2_100k.dvc

# Delete large archive (9GB) - run separately
rm data/training/iqa_phase2_100k.tar.gz
```

### Step 5: Remove Documentation

```bash
git rm docs/PHASE2_QUICKSTART.md
git rm docs/validation/phase2_complete_validation_summary.md
git rm docs/ADRs/0029-phase2-dataset-selection-strategy.md
git rm docs/ADRs/0034-resnet18-phase2-iqa.md
```

### Step 6: Remove Notebook

```bash
git rm notebooks/colab/phase2_iqa_training.ipynb
```

### Step 7: Remove Temp Files

```bash
rm -rf tmp_cleanup/.tmp-*phase2*
rm -f tmp_cleanup/workflows_copilot/iqa_modal_training_phase2.puml
rm -f tmp_cleanup/workflows_sonnet/02_phase2_teacher_training.puml
rm -f tmp_cleanup/workflows_sonnet/03_phase2_student_distillation.puml
```

### Step 8: Commit

```bash
git commit -m "chore: remove deprecated Phase 2 IQA training assets

Phase 2 used weak supervision labels (BRISQUE/NIQE) with discrete bins.
Phase 7 replaces this with continuous severity labels [0.0, 0.95]
derived from augmentation parameters, providing:
- Better calibration (ground truth vs weak supervision)
- Higher resolution (384x384 vs 224x224)
- More diverse sources (16 vs 3)
- Full reproducibility (documented DQS formula)

Removed:
- 4 scripts (prepare_phase2_*.py, benchmark_phase2.py)
- 2 Modal training files
- 4 config files
- 3 test files (1,200+ lines)
- 4 data files/symlinks + 9GB archive
- 4 documentation files
- 1 Colab notebook
- 22 temp reference files

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"
```

---

## Impact Assessment

### No Breaking Changes

- ✅ No imports from Phase 2 modules in `src/`
- ✅ No references in `pyproject.toml`
- ✅ Phase 7 training pipeline is independent

### Test Coverage

- Removing 3 test files (~1,200 lines)
- No impact on current test suite (Phase 7 tests are separate)

### Storage Savings

- **9GB** from `iqa_phase2_100k.tar.gz`
- ~50MB from scripts, configs, notebooks

### Documentation

- 93 files reference "phase2" but most are historical/comparison
- 4 dedicated Phase 2 docs removed
- Remaining references provide historical context

---

## Approval Checklist

- [ ] Review cleanup plan
- [ ] Confirm Phase 7 pipeline is working independently
- [ ] Backup 9GB archive if needed for historical reference
- [ ] Execute cleanup commands
- [ ] Verify tests still pass
- [ ] Update any docs that incorrectly reference Phase 2 as current

---

**Document Maintainer**: Byron Williams
**Last Updated**: 2025-12-16
