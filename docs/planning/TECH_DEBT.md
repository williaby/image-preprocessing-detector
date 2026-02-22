---
title: Technical Debt Tracker
category: planning
status: published
last_updated: 2026-02-10
---

# Technical Debt Tracker

This document tracks known technical debt in the Prepare-Doc (Image Preprocessing & IQA) codebase. Items are prioritized by severity and impact on development velocity, maintainability, and production readiness.

## Summary Table

| ID | Item | Severity | Impact | Status | Priority |
|----|------|----------|--------|--------|----------|
| TD-1 | Empty Module Placeholders | Low | Confusion for new contributors | Open | P3 |
| TD-2 | Stale pyproject.toml Exclusions | Low | Minor maintenance burden | Open | P4 |
| TD-3 | Budget Enforcement Dual-System | Medium | Inconsistent limits, documentation mismatch | Open | P2 |
| TD-4 | Layer 2 Metadata Coverage Gap | Medium | Incomplete dataset enrichment | Open | P2 |
| TD-5 | Pre-existing Broken Test Files | Low | Test suite hygiene | Open | P3 |
| TD-6 | Architecture Level 3 Documentation Gaps | Low | Deferred until implementation complete | Deferred | P4 |

**Severity Levels**: Critical (blocks development), High (major impact), Medium (moderate impact), Low (minor impact)

**Priority Levels**: P1 (immediate), P2 (next sprint), P3 (next phase), P4 (backlog)

---

## TD-1: Empty Module Placeholders (Removed Code)

### Description

Three modules under `src/image_preprocessing_detector/` are empty placeholder directories containing only `__pycache__` directories. Their code was removed in commit `f67c8d4` (Feb 9, 2026) as part of the SigLIP 2 architecture pivot:

- **augmentation/** (644 LOC removed): Genalog-based document degradation framework. Replaced by `synthetic/` module (`augmentation.py`, `augmentation_fast.py`, `augmentation_hybrid.py`)
- **training/** (2,647 LOC removed): Teacher-student knowledge distillation (ResNet). Replaced by `modal/train_siglip2.py`
- **models/** (3,517 LOC removed): ResNet-50/18 architectures, loss functions, model optimizer. Model inference now via ONNX artifacts in `models/iqa/onnx/`

**Total**: 6,808 LOC removed.

These modules are currently excluded from coverage (`pyproject.toml`), mypy, and type checking.

### Impact

**Low Severity**:

- Confuses new contributors who see empty directories in the source tree
- Adds noise to file navigation and IDE indexing
- No functional impact (excluded from all tooling)

### Recommended Action

**Option A (Preferred)**: Remove empty directories entirely

```bash
rm -rf src/image_preprocessing_detector/augmentation/
rm -rf src/image_preprocessing_detector/training/
rm -rf src/image_preprocessing_detector/models/
```

**Option B**: Keep as placeholders for future SigLIP 2 implementation

- Add `.gitkeep` files with explanatory comments
- Document purpose in module-level README or docstring

**Decision Criteria**: If SigLIP 2 implementation is planned for these directories within next 2 sprints, keep as placeholders. Otherwise, remove.

### Related Items

See TD-2 for stale exclusion cleanup in `pyproject.toml`.

---

## TD-2: Stale pyproject.toml Exclusions

### Description

The coverage omit section in `pyproject.toml` contains file-specific exclusions for files that no longer exist:

```toml
[tool.coverage.run]
omit = [
    "src/image_preprocessing_detector/models/resnet_student.py",
    "src/image_preprocessing_detector/models/resnet_teacher.py",
    "src/image_preprocessing_detector/models/loss_functions.py",
    # ... wildcard models/* already covers these
]
```

These files were removed in commit `f67c8d4`. The wildcard `models/*` already covers them.

### Impact

**Low Severity**:

- Harmless (no functional impact)
- Minor maintenance burden (outdated configuration)
- Could confuse new contributors reviewing coverage exclusions

### Recommended Action

Clean up stale file-specific exclusions:

```bash
# Edit pyproject.toml
# Remove individual file exclusions under models/ already covered by models/*
# Keep only wildcard exclusions for clarity
```

**After cleanup**:

```toml
[tool.coverage.run]
omit = [
    "src/image_preprocessing_detector/models/*",
    "src/image_preprocessing_detector/training/*",
    "src/image_preprocessing_detector/augmentation/*",
    "tests/*",
    "scripts/*",
]
```

### Related Items

See TD-1 for module placeholder cleanup.

---

## TD-3: Budget Enforcement Dual-System

### Description

Two separate budget enforcement systems exist with different units and thresholds:

**System 1: BudgetEnforcer** (`utils/budget_enforcement.py`, 405 LOC)

- Tracks dollar amounts
- Defaults: daily $10, monthly $100
- Unit: USD currency

**System 2: BudgetTracker** in DeviceOrchestrator (`orchestration/device_orchestrator.py`)

- Tracks page counts and GPU hours
- Defaults: per-doc 10 pages, per-batch 100 pages, monthly 10 GPU hours
- Unit: Pages and GPU hours

### Impact

**Medium Severity**:

- Inconsistent budget limits across systems
- Documentation mismatch: Architecture docs (`device-orchestrator.md`) document dollar-based tiers ($0.05/$5/$30) that don't match code defaults
- Potential confusion for production deployment (which system is authoritative?)
- Dual maintenance burden

### Recommended Action

**Phase 1 (Immediate)**: Align documentation with code

- Update `docs/architecture/diagrams/level-3/workstream-4-iqa/device-orchestrator.md` to reflect actual code defaults
- Document relationship between both systems (if intentional)

**Phase 2 (Next Sprint)**: Unify budget tracking

- **Option A**: Extend BudgetEnforcer to support both page-based and dollar-based limits
- **Option B**: Remove BudgetEnforcer and consolidate into DeviceOrchestrator's BudgetTracker
- **Option C**: Keep both systems but add clear documentation on when each is used

**Recommended**: Option A (extend BudgetEnforcer) for maximum flexibility.

```python
# Unified budget tracking API
class UnifiedBudgetEnforcer:
    def check_budget(
        self,
        usage_type: Literal["pages", "dollars", "gpu_hours"],
        amount: float,
        period: Literal["doc", "batch", "daily", "monthly"]
    ) -> BudgetCheckResult:
        ...
```

---

## TD-4: Layer 2 Metadata Coverage Gap

### Description

Only 20/51 source datasets have aggregated enrichment statistics. The aggregation script exists (`scripts/aggregate_layer2_metadata.py`) but requires Layer 2 enrichment JSON files from external storage (`/mnt/e/image_detection/metadata_registry/json/`).

**Current Coverage**:

- ⭐⭐⭐ Good metadata: 4 datasets (capture + domain + content flags)
- ⭐⭐ Partial metadata: 6 datasets (capture + domain)
- ⭐ Minimal metadata: 10 datasets (domain only)
- **No metadata**: 26 datasets (pending Layer 2 enrichment)

### Impact

**Medium Severity**:

- Incomplete dataset characterization for training task selection
- Missing capture method, domain, and content flags in Quick Reference tables
- Cannot perform comprehensive dataset diversity analysis
- Blocks full implementation of diversity requirements (see `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md`)

### Recommended Action

**Immediate**: Run aggregation for priority datasets

```bash
# Priority datasets for SigLIP 2 training
python scripts/aggregate_layer2_metadata.py --dataset ohr-bench --verbose
python scripts/aggregate_layer2_metadata.py --dataset diqa-5000 --verbose
python scripts/aggregate_layer2_metadata.py --dataset doclaynet --verbose
python scripts/aggregate_layer2_metadata.py --dataset pubtabnet --verbose
```

**Ongoing**: Establish Layer 2 enrichment workflow

1. Enrich datasets in priority order (IQA → Layout → Script → Text)
2. Run aggregation script after each enrichment batch
3. Update `docs/datasets/DATASET_QUICK_REFERENCE.md` with new metadata
4. Target: 80% coverage (41/51 datasets) by end of Phase 4

**Automation Opportunity**: Add pre-commit hook or CI job to detect new Layer 2 JSON files and auto-run aggregation.

---

## TD-5: Pre-existing Broken Test Files

### Description

Two test files have known issues related to hyphenated names in method/keyword arguments:

1. `tests/unit/annotation/config/test_datasets.py`
2. `tests/unit/scripts/test_measure_dataset_sufficiency.py`

These tests are skipped or fail due to Python naming convention violations.

### Impact

**Low Severity**:

- Test suite hygiene issue (tests cannot run)
- False signal on test coverage metrics
- Potential regression risk if underlying functionality changes

### Recommended Action

**Fix hyphenated names to use underscores**:

```python
# Before (invalid Python)
def test-function-name():  # Invalid Python identifier
    ...

# After (valid Python)
def test_function_name():
    ...
```

**Steps**:

1. Review both test files for hyphenated identifiers
2. Replace hyphens with underscores in function names, method names, and keyword arguments
3. Verify tests pass: `uv run --extra dev python -m pytest tests/unit/annotation/config/test_datasets.py -v`
4. Update test counts in documentation if coverage changes

**Estimated Effort**: 1-2 hours

---

## TD-6: Architecture Level 3 Documentation Gaps

### Description

Two workstreams are explicitly deferred for Level 3 architecture documentation:

- **WS5 (API/Deployment)**: 0 LOC implemented (Phase 5 at 40% completion)
- **WS6 (Output Generation)**: Simple linear flow, Level 2 documentation deemed sufficient

### Impact

**Low Severity**:

- No functional impact (Level 2 docs provide adequate coverage for current implementation)
- Missing detailed state machines and swimlanes for future API implementation
- Deferred by design (no implementation to document yet)

### Recommended Action

**Status**: Deferred until implementation complete

**Trigger Conditions**:

- Create WS5 Level 3 docs when Phase 5 implementation reaches >80% completion
- Create WS6 Level 3 docs if output pipeline becomes more complex (e.g., adds streaming, batching, or multi-format support)

**No immediate action required**.

---

## Resolution Process

### How to Close Tech Debt Items

1. **Fix Implementation**: Address the technical debt in code
2. **Update Documentation**: Reflect changes in architecture docs, planning docs
3. **Verify Tests**: Ensure test coverage and quality gates pass
4. **Update This Document**: Mark item as "Closed" with resolution date and commit hash
5. **Add to Changelog**: Document debt resolution in `CHANGELOG.md` under "Technical Debt" section

### Prioritization Criteria

**P1 (Immediate)**: Blocks critical development or production deployment
**P2 (Next Sprint)**: Moderate impact on development velocity or maintainability
**P3 (Next Phase)**: Low impact, can be deferred to next phase boundary
**P4 (Backlog)**: Cleanup items, deferred until explicitly triggered

---

## Related Documentation

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Phase tracking and sprint planning
- [Architecture Maintenance Guide](../architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md) - Level 3 documentation standards
- [Dataset Diversity Requirements](DATASET_DIVERSITY_REQUIREMENTS.md) - Layer 2 metadata requirements
- [SigLIP 2 Multi-Task Requirements](SIGLIP2_MULTITASK_REQUIREMENTS.md) - Architecture pivot context

---

**Last Updated**: 2026-02-10
**Next Review**: After Phase 4 completion (Device Priority & Production Hardening)
