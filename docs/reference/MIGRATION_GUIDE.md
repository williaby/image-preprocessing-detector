---
schema_type: planning
title: Phase Numbering Migration Guide
description: Help developers navigate between old RAG Pipeline phase numbering and new sequential phase numbering systems
tags:
  - planning
  - documentation
  - rag_pipeline
status: published
owner: core-maintainer
authors:
  - name: "Claude Code"
  - name: "Byron Williams"
purpose: Provide clear mapping between old (4, 6, 8, 10) and new (0-9) phase numbering to prevent confusion.
component: Context
source: project-a
---

**Purpose**: Help developers navigate between old and new phase numbering systems

---

## Quick Reference: Phase Number Mapping

| Old Number | Old Name | New Number | New Name | Status |
|-----------|----------|-----------|----------|--------|
| N/A | N/A | **Phase 0** | Foundation & Scaffolding | ✅ Complete |
| N/A | N/A | **Phase 1** | MVP with Classical Methods | ✅ Complete |
| N/A | N/A | **Phase 1B** | DPI Upscaling | ✅ Complete |
| **Phase 4** | Classical IQA Enhancement | **Phase 1C** | Enhanced Classical IQA | ✅ Complete |
| N/A | N/A | **Phase 2** | Core Components | ✅ ~95% Complete |
| **Phase 6** | Layout-Lite Detection | **Phase 2** (partial) | Layout Detection (11 classes) | ✅ ~95% Complete |
| **Phase 8** | DQS & Routing | **Phase 2** (partial) | DQS & Routing | ✅ ~95% Complete |
| N/A | N/A | **Phase 3** | ML IQA Training (Teacher-Student) | ✅ Complete |
| N/A | N/A | **Phase 4** | Device-Priority Execution | ⏳ Not Started |
| N/A | N/A | **Phase 5** | Testing & Deployment | ⏳ Not Started |
| N/A | N/A | **Phase 6** | Monitoring & Drift Detection | ⏳ Not Started |
| N/A | N/A | **Phase 7** | ML IQA Optimization (Continuous Labels) | ⏳ Planned |
| N/A | N/A | **Phase 9** | Element Classification Models | ⏳ Not Started |
| **Phase 10** | Validation & Benchmarking | **Phase 5** (partial) | Testing & Deployment | ⏳ Not Started |

---

## Understanding the Phase Numbering Change

### Old System (Pre-December 2025)

**"RAG Pipeline" Numbering** - Used gaps to align with four-project RAG pipeline architecture:

- Phase 4, 6, 8, 10 (skipped 0-3, 5, 7, 9)
- Rationale: Aligned phase numbers with project milestones across A-B-C-D pipeline
- Problem: Caused confusion within Prepare-Doc development team

### New System (December 2025 – Current)

**Sequential Numbering** - Clear progression for Prepare-Doc:

- Phase 0-9 (sequential, no gaps)
- Sub-phases use letter suffixes (e.g., Phase 1B, Phase 1C)
- Rationale: Easier to understand for Prepare-Doc developers
- Benefit: Clear dependencies and progression

---

## Detailed Phase Correspondence

### Old Phase 4 → New Phase 1C

**Old Phase 4**: Classical IQA Enhancement (Weeks 5-6)
**New Phase 1C**: Enhanced Classical IQA (Weeks 5-6)

**What Changed**: Name only (clarity improvement)

**Deliverables** (Identical):

- 5 additional classical IQA detectors (total 8)
- Noise detection (wavelet-based)
- Illumination metrics
- JPEG blockiness detection
- Binarization quality detection
- Bleed-through detection

**Implementation**: `src/image_preprocessing_detector/detection/iqa_classical.py`

**Status**: ✅ COMPLETE

---

### Old Phase 6 → New Phase 2 (Partial)

**Old Phase 6**: Layout-Lite Detection (Weeks 6-8)
**New Phase 2**: Core Components (Weeks 7-9) - includes layout detection

**What Changed**: Layout-Lite was **absorbed into Phase 2** along with Schema, PDF type classification, DQS, and Routing

**Why**: These components are interdependent - layout detection drives DQS complexity scoring, which drives routing recommendations

**Layout-Lite Deliverables**:

- DocLayout-YOLO integration (11 DocLayNet classes)
- Structural complexity scoring
- Handwriting detection (via YOLO classes)
- Column detection
- Page attribute classification

**Implementation**:

- `src/detection/doclayout_yolo.py` (802 lines)
- `src/detection/layout_lite/` (8 detector modules)

**Status**: ✅ ~95% COMPLETE (integration testing remaining)

**Note**: Original plan called for "layout-lite" (simplified version). Current implementation uses **full DocLayout-YOLO** with 11 classes.

---

### Old Phase 8 → New Phase 2 (Partial)

**Old Phase 8**: DQS & Routing (Weeks 9)
**New Phase 2**: Core Components (Weeks 7-9) - includes DQS and routing

**What Changed**: DQS & Routing absorbed into Phase 2 for same reason as layout detection

**DQS & Routing Deliverables**:

- PDF type classification (image_only/born_digital/hybrid)
- Document Quality Score calculation (degradation + complexity)
- Pre-OCR risk scoring
- OCR routing recommendation (4 strategies)

**Implementation**:

- `src/classification/pdf_type_classifier.py` (96.77% test coverage)
- `src/metrics/dqs_calculator.py` (1,370 lines)
- `src/routing/recommendation_engine.py` (141 lines, comprehensive tests)

**Status**: ✅ ~95% COMPLETE (integration testing remaining)

---

### Old Phase 10 → New Phase 5 (Partial)

**Old Phase 10**: Validation & Benchmarking (Ongoing)
**New Phase 5**: Testing, Documentation & Deployment (Weeks 18-20)

**What Changed**: Validation and benchmarking expanded into comprehensive testing & deployment phase

**Phase 5 Deliverables** (Superset of old Phase 10):

- End-to-end pipeline testing
- Performance benchmarking (all components)
- Load testing and stress testing
- Documentation updates
- Deployment automation (Docker, Docker Compose)
- Production runbooks

**Status**: ⏳ NOT STARTED (blocked by Phase 4)

---

## New Phases (Not in Old System)

### Phase 0: Foundation & Scaffolding

**Status**: ✅ COMPLETE

**Why Added**: Foundational work was underestimated in original plan

**Deliverables**:

- Project skeleton (Poetry, pre-commit, CI/CD)
- Modal workspace setup
- GPU/CPU device probing
- Configuration system (YAML)
- Logging/telemetry scaffolding

**Timeline**: Weeks 0-1

---

### Phase 1: MVP with Classical Methods

**Status**: ✅ COMPLETE

**Why Added**: Original plan jumped to Phase 4; need MVP before enhancements

**Deliverables**:

- Ingestion pipeline (PDF → images)
- Text gate (fast text detection)
- Basic classical IQA (blur, skew, contrast)
- Correction pipeline (deskew, CLAHE)
- CLI
- JSON output

**Timeline**: Weeks 2-5

---

### Phase 1B: DPI Upscaling

**Status**: ✅ COMPLETE

**Why Added**: Critical feature discovered during Phase 1

**Deliverables**:

- DPI detection (PyMuPDF-based)
- Automatic upscaling for <300 DPI documents
- Pre-flight analysis orchestration
- 5 upscaling algorithms (Lanczos, bicubic, etc.)

**Implementation**:

- `src/ingestion/pdf_resolution.py`
- `src/ingestion/pdf_upscaler.py`
- `src/ingestion/pdf_analyzer.py`

**Timeline**: Integrated during Phase 1

---

### Phase 3: ML IQA Training (Teacher-Student ResNet)

**Status**: ✅ COMPLETE

**Why Added**: ML training is major component, deserves dedicated phase

**Deliverables**:

- ResNet-50 teacher training (50 epochs, val_loss=0.2694)
- Knowledge distillation to ResNet-18 student (30 epochs, val_loss=0.1386)
- ONNX export (both models)
- GCS backup
- Model registry integration

**Training Completed**: November 22, 2025

**Dataset**: 100K images with binary labels (0/1)

**Timeline**: Weeks 10-14

---

### Phase 7: ML IQA Optimization (Continuous Labels)

**Status**: ⏳ PLANNED (Not yet executed)

**Why Added**: Continuous labels are major improvement, warrant dedicated phase

**Deliverables**:

- Dataset expansion (100K → 150K)
- DocCreator integration (45K physics-based samples)
- Augraphy integration (90K parametric samples)
- Hybrid loss function (SoftBCE + PLCC + Rank)
- Model retraining with continuous [0,1] labels

**Dependencies**: Phase 3 (binary models as baseline)

**Timeline**: TBD

---

### Phase 9: Element Classification Models

**Status**: ⏳ NOT STARTED

**Why Added**: Element classifiers migrated from Unify scope

**Deliverables**:

- Handwriting classifier (full/light variants)
- Table type classifier (6 classes)
- Formula complexity classifier (5 classes)
- Parasitic content detector (watermark, stamp, signature)
- Model registry integration

**Rationale**: Prepare-Doc has training infrastructure and datasets; Unify will consume via model registry

**Dependencies**: Phase 3 (ML infrastructure)

**Timeline**: TBD

---

## Migration Checklist for Developers

When encountering old phase references in code, comments, or documentation:

### Step 1: Identify Old Phase Number

- [ ] Note the phase number (e.g., "Phase 6")
- [ ] Check document date (pre-December 2025 = old system)

### Step 2: Map to New Phase Number

- [ ] Use quick reference table above
- [ ] Old Phase 6 → New Phase 2
- [ ] Old Phase 8 → New Phase 2
- [ ] Old Phase 4 → New Phase 1C
- [ ] Old Phase 10 → New Phase 5

### Step 3: Update Reference

- [ ] Update code comments to new phase number
- [ ] Update documentation links to point to `PROJECT_PLAN.md`
- [ ] If referencing deliverables, verify they're still in scope

### Step 4: Validate Status

- [ ] Check `PROJECT_PLAN.md` for current completion status
- [ ] Old docs may say "Not Started" when actually complete
- [ ] Example: Old Phase 6 said "Not Started", but Phase 2 is ~95% complete

---

## Common Pitfalls

### Pitfall 1: Assuming Phase Numbers Align Across Projects

**Wrong**: "Prepare-Doc Phase 6 corresponds to Unify Phase 6"

**Right**: Phase numbers are **independent per project**. Use the **Prepare-Doc/B contract** to understand handoffs, not phase numbers.

**Reference**: `docs/development/RAG Pipeline/project-ab-contract.md`

---

### Pitfall 2: Using Outdated Status Information

**Wrong**: Checking old docs for completion status

**Right**: ONLY trust `docs/planning/PROJECT_PLAN.md` "Current Status Dashboard" section

**Why**: Old docs (e.g., phase-sprint-details.md) claimed "Phase 6: Not Started" when actually ~95% complete

---

### Pitfall 3: Looking for "Layout-Lite"

**Wrong**: Searching for "layout-lite" implementation

**Right**: Prepare-Doc uses **full DocLayout-YOLO** (11 classes), not simplified version

**Implementation**: `src/detection/doclayout_yolo.py`

**Note**: "Layout-lite" approach was abandoned in favor of full layout detection

---

## Examples of Updated References

### Example 1: Code Comment

**Old**:

```python
# TODO: Integrate with layout detection in Phase 6
```

**New**:

```python
# TODO: Complete Phase 2 integration testing (layout detection implemented)
```

---

### Example 2: Documentation Link

**Old**:

```markdown
See [Phase 6 Sprint Details](docs/development/phase-sprint-details.md#phase-6) for layout detection implementation.
```

**New**:

```markdown
See [Phase 2 Documentation](docs/planning/PROJECT_PLAN.md#phase-2-core-components-schema-alignment-weeks-7-9) for layout detection details.

Implementation: `src/detection/doclayout_yolo.py` (802 lines, 11 DocLayNet classes)
```

---

### Example 3: Commit Message

**Old**:

```text
feat(phase-6): add layout-lite detector
```

**New**:

```text
feat(phase-2): add DocLayout-YOLO detector with 11 classes
```

---

## FAQs

### Q1: Why did the phase numbering change?

**A**: The old "RAG Pipeline" numbering (4, 6, 8, 10) was designed to align with the four-project RAG pipeline architecture but caused confusion within Prepare-Doc. Sequential numbering (0-9) is clearer for Prepare-Doc developers.

---

### Q2: What happened to Phase 5 and Phase 7 in the old system?

**A**: The old system intentionally skipped numbers to maintain alignment with the RAG pipeline architecture. The new system is sequential for clarity.

---

### Q3: Why are Phase 6 and Phase 8 (old) both in Phase 2 (new)?

**A**: They were consolidated because they're interdependent:

- Layout detection → structural complexity score
- Structural complexity score → DQS calculation
- DQS calculation → routing recommendations

Keeping them in separate phases created artificial boundaries.

---

### Q4: Where can I find sprint-level details from the old plan?

**A**: Sprint-level breakdowns from `phase-sprint-details.md` were consolidated into:

- High-level: `docs/planning/PROJECT_PLAN.md` (milestones and deliverables)
- Implementation: Source code (e.g., `src/detection/iqa_classical.py`)
- Tests: Test files (e.g., `tests/unit/detection/test_iqa_classical.py`)

---

### Q5: Is the old phase numbering completely deprecated?

**A**: Yes. All references should use the new sequential numbering. The old numbering is preserved in this guide for historical reference only.

**Exception**: External stakeholders unfamiliar with the change may still use old numbers. Gently redirect them to this guide.

---

## Additional Resources

- **Current Planning**: `docs/planning/PROJECT_PLAN.md` (authoritative source)
- **Deprecated Docs**: `docs/DEPRECATED_DOCS.md` (list of deleted files)
- **Prepare-Doc/B Contract**: `docs/development/RAG Pipeline/project-ab-contract.md`
- **Phase Comparison**: `tmp_cleanup/.tmp-planning-docs-comparison-20250201.md` (detailed analysis)

---

**Last Reviewed**: 2025-12-01
**Maintained By**: Prepare-Doc Core Team
**Questions**: Consult development team or reference this guide
