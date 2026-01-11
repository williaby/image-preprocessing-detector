---
owner: docs-team
purpose: Documentation for Level 3 Documentation + Swimlane Traceability -
  Implementation Roadmap.
schema_type: common
status: draft
tags:
- architecture
title: Level 3 Documentation + Swimlane Traceability - Implementation Roadmap
---

**Approved Approach**: Option C (Hybrid) - Traceability tables at Level 2, detailed swimlanes at Level 3

**User Decisions**:

- ✅ Issue 4.5 (Monitoring Level 3): APPROVED for end-to-end lifecycle visibility
- ✅ Issue 6.1 (Swimlane Traceability): APPROVED with Option C hybrid approach
- ✅ Execution: Parallel implementation (traceability + Level 3 docs simultaneously)

---

## 📊 Remaining Work Summary

### Level 3 Documentation (5 docs, 54 hours)

| Issue | Workstream | Deliverable | Effort | Approved |
|-------|------------|-------------|--------|----------|
| 4.1 | Data Preparation | metadata-schema-versioning.md | 12h | ✅ Unanimous |
| 4.2 | Data Preparation | label-parsing-generation.md | 10h | ✅ Unanimous |
| 4.3 | Production Runtime | pipeline-state-machine.md | 12h | ✅ Unanimous |
| 4.4 | Production Runtime | device-orchestrator.md | 10h | ✅ Unanimous |
| 4.5 | Monitoring & Drift | end-to-end-lifecycle.md | 10h | ✅ User approved |

### Swimlane Traceability (1 issue, 32 hours)

| Task | Deliverable | Effort | Approved |
|------|-------------|--------|----------|
| 6.1.A | Traceability tables (8 Level 2 docs) | 8h | ✅ User approved |
| 6.1.B | Production Runtime swimlane.puml | 8h | ✅ User approved |
| 6.1.B | Data Prep swimlane.puml | 4h | ✅ User approved |
| 6.1.B | Model Training swimlane.puml | 4h | ✅ User approved |
| 6.1.B | Monitoring swimlane.puml | 4h | ✅ User approved |
| 6.1.C | Enhanced LOC validation | 4h | ✅ User approved |

**Total**: 86 hours over 4-6 weeks

---

## 🗓️ Week-by-Week Schedule

### Week 3: Data Preparation (24 hours)

**Monday-Tuesday: Traceability Tables** (8 hours)

- [ ] Add "Source File Traceability" section to all 8 Level 2 index.md files
- [ ] Use FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md as source
- [ ] Validate subtotals match LOC extraction

**Wednesday-Thursday: Data Prep Level 3 Docs** (22 hours)

- [ ] Issue 4.1: Create `level-3/data-preparation/metadata-schema-versioning.md` (12h)
  - ER diagrams for three layers
  - Anchor score priority logic (6 levels)
  - Versioning strategy and backward compatibility
  - Class diagrams (OriginalFileMetadata, OriginalLabels, EnrichmentData, TrainingLabels)
  - Code traceability map (annotate_base_metadata.py lines 64-523)

- [ ] Issue 4.2: Create `level-3/data-preparation/label-parsing-generation.md` (10h)
  - 9 dataset-specific parser implementations
  - COCO cache optimization (100x speedup)
  - 45-dim IQA vector construction
  - Training label builder (build_training_labels.py lines 145-410)
  - Sequence diagrams for parser flows

**Friday: Data Prep Swimlane** (4 hours)

- [ ] Create `level-3/data-preparation/data-preparation-swimlane.puml`
  - 4 swimlanes: Dataset Collection, Layer 1 (Immutable), Layer 2 (Enrichment), Layer 3 (Training)
  - Annotate all 8 scripts with LOC from FILE_INVENTORY
  - Legend: Total 4,066 lines (validate matches)

**Week 3 Deliverables**:

- 8 Level 2 docs with traceability tables
- 2 Data Prep Level 3 docs
- 1 Data Prep swimlane diagram

---

### Week 4: Production Runtime (28 hours)

**Monday-Wednesday: Production Runtime Level 3 Docs** (22 hours)

- [ ] Issue 4.3: Create `level-3/production-runtime/pipeline-state-machine.md` (12h)
  - Full PlantUML state diagram (13 states with transitions)
  - Error recovery flows (4 categories)
  - Timeout escalation sequences
  - Edge case handling (partial failures, circuit breaker)
  - State transition table with entry/exit conditions

- [ ] Issue 4.4: Create `level-3/production-runtime/device-orchestrator.md` (10h)
  - Device selection algorithm (decision tree diagram)
  - Budget enforcement (3-tier implementation)
  - Circuit breaker state machine (CLOSED → OPEN → HALF_OPEN)
  - Performance characteristics by device
  - Integration with iqa_ml.py

**Thursday-Friday: Production Runtime Swimlane** (8 hours)

- [ ] Create `level-3/production-runtime/production-runtime-swimlane.puml`
  - 4 swimlanes: Ingestion & Preflight, Classification & Routing, Quality Analysis, Correction & Scoring
  - Annotate all 44 files with LOC from FILE_INVENTORY (16,910 total)
  - Break down Detection into Text Gate + IQA + Layout Lite subsections
  - Legend: Total matches LOC extraction

**Week 4 Deliverables**:

- 2 Production Runtime Level 3 docs
- 1 Production Runtime swimlane diagram

---

### Week 5: Model Training (Optional, 4-8 hours)

**Option A: Swimlane Only** (4 hours)

- [ ] Create `level-3/model-training/model-training-swimlane.puml`
  - 4 swimlanes: Data Pipeline, Teacher Training, Student Distillation, Model Export
  - Annotate all 16 files with LOC (7,058 total)
  - Show data flow from WS3/4/8 → Training → WS6 → WS1

**Option B: Full Level 3** (8 hours)

- [ ] Assess if distillation complexity warrants additional Level 3 doc
- [ ] If yes: Create `level-3/model-training/distillation-internals.md`
- [ ] If no: Swimlane sufficient (Level 2 already comprehensive)

**Recommendation**: Option A (swimlane only) - Level 2 doc already has detailed distillation loss function code

**Week 5 Deliverable**:

- 1 Model Training swimlane diagram

---

### Week 6: Monitoring & Enhanced Validation (18 hours)

**Monday-Wednesday: Monitoring Level 3** (14 hours)

- [ ] Issue 4.5: Create `level-3/monitoring-drift/end-to-end-lifecycle.md` (10h)
  - Complete lifecycle sequence diagram (drift → alert → harvest → privacy → retrain → arena → deploy)
  - RetrainingJob state machine (6 states)
  - PrivacyReview workflow (4 states)
  - Cross-component integration (6 components)
  - Compliance workflows (GDPR/CCPA)
  - Deployment gates (Arena PLCC validation)

- [ ] Create `level-3/monitoring-drift/monitoring-drift-swimlane.puml` (4h)
  - 6 swimlanes: Drift Detection, Performance Monitoring, Alerting, Active Learning, Privacy Review, Retraining
  - Annotate all 7 files with LOC (5,348 total)
  - Show integration flow between components

**Thursday-Friday: Enhanced Validation** (4 hours)

- [ ] Enhance `scripts/extract_workstream_loc.sh` with `--validate-tables` option
  - Extract LOC from Level 2 traceability tables
  - Compare to LOC mapping
  - Output discrepancy report

- [ ] Add `--validate-swimlane <workstream>` option
  - Extract file annotations from Level 3 swimlanes
  - Compare to LOC mapping and FILE_INVENTORY
  - Validate total sum matches

- [ ] Create validation report template
- [ ] Test validation on all created tables and swimlanes

**Week 6 Deliverables**:

- 1 Monitoring Level 3 doc
- 1 Monitoring swimlane diagram
- Enhanced LOC script with validation modes

---

## 📋 Detailed Task Breakdown

### Issue 4.1: Data Prep Metadata Schema (12 hours)

**File**: `level-3/data-preparation/metadata-schema-versioning.md`

**Content Outline** (500+ lines):

1. **Three-Layer Architecture Overview** (100 lines)
   - Conceptual diagram showing layer separation
   - Data flow: Source → Immutable → Enrichment → Training
   - Rationale for separation (immutability, versioning, flexibility)

2. **Layer 1: Immutable (Original Labels)** (120 lines)
   - `OriginalFileMetadata` class diagram
   - `OriginalLabels` class diagram
   - Field descriptions and sources
   - Code reference: annotate_base_metadata.py lines 64-98

3. **Layer 2: Enrichment (Derived Annotations)** (150 lines)
   - `EnrichmentData` class diagram
   - `EnrichmentVersion` class diagram
   - Enrichment methods (automated, manual, llm)
   - Versioning workflow
   - Code reference: annotate_base_metadata.py lines 362-523

4. **Layer 3: Training (Computed Labels)** (100 lines)
   - `TrainingLabels` class diagram
   - Anchor score priority logic (decision tree)
   - Anchor weighting (6 levels: human=1.0, llm_high=0.8, llm_medium=0.5, llm_low=0.3, synthetic=0.3, none=0.0)
   - Code reference: build_training_labels.py lines 60-137

5. **Anchor Score Priority Algorithm** (80 lines)
   - Decision tree diagram
   - Pseudocode for selection
   - Examples with different label combinations

6. **Traceability** (50 lines)
   - Map each class to source file lines
   - Cross-reference to DATASET_LOCATIONS.md

**Source Files Referenced**:

- scripts/annotate_base_metadata.py (1,235 lines)
- scripts/build_training_labels.py (590 lines)

---

### Issue 4.2: Data Prep Label Parsing (10 hours)

**File**: `level-3/data-preparation/label-parsing-generation.md`

**Content Outline** (450+ lines):

1. **Parser Architecture** (80 lines)
   - Abstract parser interface
   - Parser registry pattern
   - COCO cache optimization strategy

2. **Dataset-Specific Parsers** (200 lines)
   - parse_diqa_labels() - sequence diagram
   - parse_live_labels() - sequence diagram
   - parse_doclaynet_labels() - COCO format handling
   - parse_tablebank_labels() - COCO format handling
   - parse_funsd_labels() - form field annotations
   - parse_signatr_labels() - writer_id extraction
   - 3 more parsers
   - Code reference: annotate_base_metadata.py lines 635-852

3. **COCO Cache Optimization** (70 lines)
   - Cache initialization flow
   - Memory vs speed tradeoffs
   - 100x speedup analysis

4. **Training Label Builder** (100 lines)
   - 45-dimensional IQA vector construction
   - Per-degradation severity scoring
   - Anchor score calculation
   - Output schema mapping
   - Code reference: build_training_labels.py lines 145-410

**Source Files Referenced**:

- scripts/annotate_base_metadata.py (lines 635-852 for parsers)
- scripts/build_training_labels.py (lines 145-410 for training labels)

---

### Issue 4.3: Production Runtime State Machine (12 hours)

**File**: `level-3/production-runtime/pipeline-state-machine.md`

**Content Outline** (550+ lines):

1. **Complete State Diagram** (PlantUML, 150 lines)
   - 13 states with transitions
   - Entry/exit conditions for each
   - Timeout values
   - Fallback paths

2. **State Transition Tables** (120 lines)
   - Happy path sequence
   - Error recovery paths (3 scenarios)
   - Fallback paths (2 scenarios)
   - Timeout escalation logic

3. **Error Recovery Flows** (180 lines)
   - Category 1: Transient (retry with backoff)
   - Category 2: Resource (fallback device)
   - Category 3: Data (skip page)
   - Category 4: Critical (abort + alert)
   - Code examples for each

4. **Edge Cases** (100 lines)
   - Partial page failure (< 10%, 10-50%, > 50%)
   - Circuit breaker triggered
   - Budget exhausted
   - All devices unavailable

**Source Files Referenced**:

- All 44 Production Runtime files from FILE_INVENTORY
- Focus on: iqa_ml.py, device_probe.py, workers/tasks.py

---

### Issue 4.4: Production Runtime DeviceOrchestrator (10 hours)

**File**: `level-3/production-runtime/device-orchestrator.md`

**Content Outline** (450+ lines):

1. **Device Selection Algorithm** (120 lines)
   - Decision tree diagram (PlantUML)
   - Priority: Local GPU → Modal GPU → CPU (or BLOCK)
   - Policy enforcement

2. **Budget Enforcement** (100 lines)
   - Three-tier tracking (per-document, per-batch, monthly)
   - Pre-request checks
   - Post-request updates
   - Budget exhaustion handling

3. **Circuit Breaker Implementation** (80 lines)
   - State machine diagram (CLOSED → OPEN → HALF_OPEN)
   - Failure threshold (5 consecutive)
   - Timeout (60s)
   - Recovery criteria (2 successes)

4. **Performance by Device** (80 lines)
   - Latency comparison table
   - Throughput analysis
   - Cost tracking
   - Policy recommendations (dev/staging/prod)

5. **Integration Points** (70 lines)
   - How iqa_ml.py invokes orchestrator
   - Modal GPU client integration
   - Prometheus metrics emission

**Source Files Referenced**:

- src/.../detection/iqa_ml.py (device selection logic)
- src/.../utils/device_probe.py (GPU detection)
- modal/teacher_inference.py (Modal integration)

---

### Issue 4.5: Monitoring End-to-End Lifecycle (10 hours)

**File**: `level-3/monitoring-drift/end-to-end-lifecycle.md`

**Content Outline** (450+ lines):

1. **Complete Lifecycle Sequence** (PlantUML, 120 lines)
   - Production Runtime → Drift Detection
   - Drift Detection → Alert Manager
   - Alert Manager → Active Learning
   - Active Learning → Privacy Review
   - Privacy Review → Retraining Orchestrator
   - Retraining → Model Training (WS2)
   - Model Training → Model Arena (WS6)
   - Model Arena → Production Runtime (re-deploy)

2. **State Machines** (140 lines)
   - RetrainingJob: PENDING → PREPARING → TRAINING → VALIDATING → COMPLETED/FAILED/CANCELLED
   - PrivacyReview: PENDING → REQUIRES_REVIEW → APPROVED/REJECTED

3. **Cross-Component Flows** (100 lines)
   - How 6 components interact
   - Data flow between Drift, Performance, Alerting, Active Learning, Privacy, Retraining
   - Prometheus metrics at each step

4. **Compliance Workflows** (90 lines)
   - GDPR 30-day retention
   - CCPA opt-out support
   - Audit trail generation

**Source Files Referenced**:

- src/.../drift/**init**.py (drift detection)
- src/.../drift/performance.py (evaluation jobs)
- src/.../drift/alerting.py (multi-channel dispatch)
- src/.../drift/active_learning.py (sample harvesting)
- src/.../drift/privacy_review.py (review workflow)
- src/.../drift/retraining.py (orchestration)

---

### Issue 6.1: Swimlane Traceability (32 hours)

#### Part A: Level 2 Traceability Tables (8 hours, 1 hour per workstream)

**Format** (add to each Level 2 index.md before "Related Diagrams"):

```markdown
## Source File Traceability

| Workflow Step | Source Files | LOC | Total |
|---------------|--------------|-----|-------|
| [Step 1 Name] | file1.py, file2.py | 100, 200 | 300 |
| [Step 2 Name] | file3.py | 150 | 150 |
...

**Workstream Total**: X,XXX lines ✅ (matches LOC extraction)
```

**Files to Update**:

1. production-runtime/index.md - 11 workflow steps (Ingestion, Preflight, Classification, Text Gate, Classical IQA, ML IQA, Layout-Lite, Correction, DQS, Routing, Output)
2. model-training/index.md - 4 workflow steps (Data Pipeline, Teacher Training, Student Distillation, Model Export)
3. data-preparation/index.md - 4 workflow steps (Dataset Collection, Layer 1, Layer 2, Layer 3)
4. pseudo-labeling/index.md - 5 workflow steps (Track A Training, Track B Training, Checkpoint Selection, Ensemble Stacking, Batch Inference)
5. labeling-benchmarking/index.md - 3 workflow steps (Pretrained Selection, Fine-Tuning, Checkpoint Export)
6. model-arena/index.md - 7 workflow steps (ArenaRunner, Dataset Adapters, Inference Backends, Metrics, Schemas, Leaderboard, CLI)
7. monitoring-drift/index.md - 6 workflow steps (Drift, Performance, Alerting, Active Learning, Privacy, Retraining)
8. synthetic-generation/index.md - 3 workflow steps (Configuration, Degrader, Benchmark Adapter)

**Source**: Use FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md for LOC counts

---

#### Part B: Level 3 Swimlane Diagrams (20 hours)

**1. Production Runtime Swimlane** (8 hours)

**File**: `level-3/production-runtime/production-runtime-swimlane.puml`

**Structure**:

```plantuml
@startuml Production_Runtime_Detailed_Swimlane
title Production Runtime - Complete Workflow with LOC Traceability
footer Workstream 1: Production Runtime | LOC: 16,910 | January 2025

|#FFF3E0|Ingestion & Preflight|
|#E3F2FD|Classification & Routing|
|#E8F5E9|Quality Analysis|
|#F3E5F5|Correction & Scoring|

|Ingestion & Preflight|
start
:Load document;
note right
  **Source Files:**
  - document_processor.py (303 lines)
  - pdf_loader.py (265 lines)
  - image_loader.py (280 lines)
  - office_processor.py (492 lines)
  **Total**: 1,340 lines
end note

:Analyze DPI;
note right
  **Source Files:**
  - pdf_analyzer.py (256 lines)
  - pdf_resolution.py (264 lines)
  **Total**: 520 lines
end note

... (continue for all steps)

legend right
  **Total LOC**: 16,910 lines ✅
  **Validation**: Matches LOC extraction
endlegend

@enduml
```

**Annotations Required**: All 44 files from FILE_INVENTORY with LOC

---

**2. Data Prep Swimlane** (4 hours)

**File**: `level-3/data-preparation/data-preparation-swimlane.puml`

**Structure**: 4 swimlanes (Collection, Layer 1, Layer 2, Layer 3)

**Annotations Required**: All 8 scripts with LOC (4,066 total)

---

**3. Model Training Swimlane** (4 hours)

**File**: `level-3/model-training/model-training-swimlane.puml`

**Structure**: 4 swimlanes (Data Pipeline, Teacher, Distillation, Export)

**Annotations Required**: All 16 files with LOC (7,058 total)

---

**4. Monitoring Swimlane** (4 hours)

**File**: `level-3/monitoring-drift/monitoring-drift-swimlane.puml`

**Structure**: 6 swimlanes (one per component)

**Annotations Required**: All 7 files with LOC (5,348 total)

---

#### Part C: Enhanced LOC Validation (4 hours)

**Updates to `scripts/extract_workstream_loc.sh`**:

1. **Add `--validate-tables` mode** (2 hours)

   ```bash
   ./scripts/extract_workstream_loc.sh --validate-tables production_runtime

   # Output:
   # Extracting LOC from traceability table in level-2/production-runtime/index.md
   # Table total: 16,850 lines
   # LOC mapping total: 16,910 lines
   # Difference: 60 lines (0.4%)
   # Missing files: tensor_cache.py (60 lines)
   ```

2. **Add `--validate-swimlane <workstream>` mode** (2 hours)

   ```bash
   ./scripts/extract_workstream_loc.sh --validate-swimlane production_runtime

   # Output:
   # Extracting LOC from swimlane in level-3/production-runtime/production-runtime-swimlane.puml
   # Swimlane total: 16,850 lines (from annotations)
   # LOC mapping total: 16,910 lines
   # Difference: 60 lines (0.4%)
   # Files in mapping but not in swimlane: tensor_cache.py
   ```

3. **Create validation report** (integrated into script)

---

## 🎯 Success Criteria

### Level 3 Documentation

- [ ] All 5 docs created (Data Prep × 2, Production Runtime × 2, Monitoring × 1)
- [ ] Each doc ≥400 lines with diagrams, algorithms, and code references
- [ ] All state machines use PlantUML diagrams
- [ ] All workflows reference specific source file line numbers
- [ ] Markdown linting passing

### Swimlane Traceability

- [ ] All 8 Level 2 docs have traceability tables
- [ ] All 4 Level 3 swimlanes created with LOC annotations
- [ ] All swimlane totals match LOC extraction within ±2%
- [ ] Legend on each swimlane shows validation
- [ ] Enhanced LOC script operational with both validation modes

### Validation

- [ ] `--validate-tables` reports ≤5% variance for all 8 workstreams
- [ ] `--validate-swimlane` reports ≤2% variance for all 4 swimlanes
- [ ] All discrepancies investigated and resolved
- [ ] FILE_INVENTORY updated with any reassignments

---

## 🔧 Tools & References

### Primary References

1. **[FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md](FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md)** - Source of truth for file-to-workstream mappings
2. **[LEVEL_2_DOCUMENTATION_TEMPLATE.md](LEVEL_2_DOCUMENTATION_TEMPLATE.md)** - Standards for Level 2 tables
3. **[SWIMLANE_TRACEABILITY_PROPOSAL.md](SWIMLANE_TRACEABILITY_PROPOSAL.md)** - Detailed swimlane examples
4. **[LOC_EXTRACTION_METHODOLOGY.md](LOC_EXTRACTION_METHODOLOGY.md)** - How LOC counting works

### Source Code to Document

- `scripts/annotate_base_metadata.py` - 1,235 lines (three-layer metadata)
- `scripts/build_training_labels.py` - 590 lines (training label generation)
- `src/.../detection/iqa_ml.py` - 1,303 lines (student/teacher inference)
- `src/.../drift/*.py` - 5,348 lines (6 monitoring components)

### Existing Swimlane Example

- `level-1/PROJECT_A_WORKFLOW_HIERARCHY.puml` - Pattern for LOC annotations

---

## 📝 Next Immediate Actions

**To start Week 3**:

1. [ ] Create level-3 directories:

   ```bash
   mkdir -p docs/architecture/diagrams/level-3/{data-preparation,production-runtime,model-training,monitoring-drift}
   ```

2. [ ] Begin with Issue 4.1 (Data Prep Metadata Schema)
   - Read annotate_base_metadata.py in detail
   - Extract class definitions
   - Create ER diagrams for three layers

3. [ ] Add first traceability table (Data Prep) as template
   - Use as reference for remaining 7 tables

**Estimated Time to First Deliverable**: 12 hours (Issue 4.1)

---

*Roadmap approved: 2025-01-16*
*Ready to begin: Week 3 implementation*
