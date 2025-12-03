---
schema_type: planning
title: Deprecated Documentation
description: Track documentation that has been consolidated, deprecated, or deleted during project evolution
tags:
  - planning
  - documentation
status: published
owner: core-maintainer
authors:
  - name: "Claude Code"
  - name: "Byron Williams"
purpose: Maintain a historical record of deprecated documentation to help developers understand what was removed and why.
component: Context
source: project-a
---

**Purpose**: Track documentation that has been consolidated, deprecated, or deleted

---

## Overview

This file maintains a record of deprecated documentation to help developers understand what was removed and why, and where to find the current information.

---

## Deleted Documents (December 2025 Consolidation)

### 1. phase-sprint-details.md

**Original Path**: `docs/development/phase-sprint-details.md`
**Deletion Date**: 2025-12-01
**Reason**: Outdated phase numbering and severely incorrect status information

**Issues**:

- Used old "RAG Pipeline" phase numbering (Phase 4, 6, 8, 10)
- Claimed "Phase 6 (Layout-Lite): Not Started" when actually ~95% complete
- Claimed "Phase 8 (DQS & Routing): In Progress" when actually ~95% complete
- Layout model specification changed from YOLOv8-nano (4 classes) to DocLayout-YOLO (11 classes)

**Migration**:

- All current phase information consolidated into `docs/planning/PROJECT_PLAN.md`
- See `docs/MIGRATION_GUIDE.md` for phase number mapping

**Historical Note**:
The document was marked as "HISTORICAL REFERENCE" but the status section contradicted completion claims, causing confusion.

---

### 2. project-a-project-plan.md

**Original Path**: `docs/development/RAG Pipeline/project-a-project-plan.md`
**Deletion Date**: 2025-12-01
**Reason**: Redundant subset of PROJECT_PLAN.md with outdated information

**Issues**:

- Missing Phase 7 (continuous labels) documentation
- Text gate marked as "implemented" vs "PENDING EVALUATION" in master plan
- Training results showed epoch 20 checkpoint instead of full 50 epoch training
- Performance targets inconsistent with validated benchmarks

**Migration**:

- All relevant content integrated into `docs/planning/PROJECT_PLAN.md`
- Project A/B interface contract preserved in `docs/development/RAG Pipeline/project-ab-contract.md`

---

### 3. phase-7-continuous-labels-strategy.md

**Original Path**: `docs/development/phase-7-continuous-labels-strategy.md`
**Deletion Date**: 2025-12-01
**Reason**: Integrated into PROJECT_PLAN.md Phase 7 section

**Content Preserved**:
All strategy details (DocCreator integration, Augraphy pipeline, dataset composition, loss functions) are now documented in PROJECT_PLAN.md Phase 7 with full implementation details.

**Migration**:

- Phase 7 section in `docs/planning/PROJECT_PLAN.md` contains complete strategy summary
- For detailed implementation, refer to Phase 7 in consolidated plan

---

## Active Documentation (Current as of December 2025)

### Primary Planning Document

**`docs/planning/PROJECT_PLAN.md`** - ✅ **CANONICAL SOURCE**

- Complete project roadmap with all phases (0-9)
- Validated completion status (December 2025 audit)
- Authoritative performance targets
- Integration with Project B via contract reference
- Phase dependencies and blocking relationships

### Supporting Documents

**`docs/development/RAG Pipeline/project-ab-contract.md`** - ✅ **ACTIVE**

- Authoritative interface contract between Project A and Project B
- Schema v2.0.0 specification
- Model registry and handoff protocols
- Version: 2.0.0 (Last Updated: 2025-11)

**`docs/MIGRATION_GUIDE.md`** - ✅ **ACTIVE**

- Phase number mapping (old → new)
- Developer migration guide for old references

---

## Phase Numbering History

### Old Numbering System (DEPRECATED)

Used "RAG Pipeline" numbering with gaps:

- Phase 4: Enhanced Classical IQA
- Phase 6: Layout-Lite Detection
- Phase 8: DQS & Routing
- Phase 10: Validation & Benchmarking

### New Numbering System (CURRENT)

Sequential numbering for clarity:

- Phase 0: Foundation
- Phase 1: Classical MVP
- Phase 1B: DPI Upscaling
- Phase 1C: Enhanced Classical IQA
- Phase 2: Core Components (Schema, PDF type, Layout-Lite, DQS, Routing)
- Phase 3: ML IQA Training (Teacher-Student ResNet)
- Phase 4: Device-Priority Execution
- Phase 5: Testing & Deployment
- Phase 6: Monitoring & Drift Detection
- Phase 7: ML IQA Optimization (Continuous Labels)
- Phase 9: Element Classification Models (NEW - migrated from Project B)

**See**: `docs/MIGRATION_GUIDE.md` for complete mapping table

---

## Common Migration Scenarios

### Scenario 1: Looking for Sprint-Level Details

**Old Reference**: "See phase-sprint-details.md Sprint 4.3.1 for skew detection implementation"

**New Location**:

- High-level: `docs/planning/PROJECT_PLAN.md` Phase 1C (Enhanced Classical IQA)
- Implementation: `src/image_preprocessing_detector/detection/iqa_classical.py:SkewDetector`
- Tests: `tests/unit/detection/test_iqa_classical.py`

### Scenario 2: Looking for Phase 6 Information

**Old Reference**: "Phase 6 Layout-Lite Detection"

**New Location**:

- Now called **Phase 2** (Core Components)
- See `docs/planning/PROJECT_PLAN.md` Phase 2 section
- Implementation: `src/detection/layout_lite/` (8 detector modules)

### Scenario 3: Looking for Continuous Labels Strategy

**Old Reference**: "See phase-7-continuous-labels-strategy.md"

**New Location**:

- `docs/planning/PROJECT_PLAN.md` Phase 7 section
- Complete strategy summary with DocCreator/Augraphy integration details

### Scenario 4: Looking for Project A Implementation Plan

**Old Reference**: "See project-a-project-plan.md for detailed roadmap"

**New Location**:

- `docs/planning/PROJECT_PLAN.md` - Single authoritative source
- All phases (0-9) with validated completion status

---

## Rationale for Consolidation

**Problem**: Multiple planning documents with inconsistent information created confusion:

- Different phase numbering systems
- Conflicting status information (Not Started vs ~95% Complete)
- Outdated technical specifications
- Redundant content across 4+ documents

**Solution**: Single source of truth in `PROJECT_PLAN.md`

- Validated completion status (December 2025 audit)
- Consistent phase numbering
- Authoritative performance targets
- Clear integration with Project B contract

**Benefits**:

- Reduced developer confusion
- Single update point for planning changes
- Clear historical record in this file
- Migration guide for old references

---

## Maintenance

**When to Update This File**:

- Deprecating or deleting planning documents
- Changing phase numbering or structure
- Major reorganization of documentation

**Update Process**:

1. Document old file path and deletion date
2. List specific issues or reasons for deprecation
3. Provide migration path to current documentation
4. Update MIGRATION_GUIDE.md if phase numbers change

---

## Questions?

If you find a reference to a deprecated document and are unsure where to find the current information:

1. Check `docs/MIGRATION_GUIDE.md` for phase number mappings
2. Check `docs/planning/PROJECT_PLAN.md` for all current planning
3. Check this file's "Common Migration Scenarios" section
4. If still unclear, consult the development team

---

**Last Reviewed**: 2025-12-01
**Next Review**: As needed when deprecating additional documents
