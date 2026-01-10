---
title: "Level 3 Documentation - Agent Task Assignments"
date: "2025-01-16"
status: "ready_to_execute"
total_agents: 4
total_effort: "86 hours"
---

# Level 3 Documentation - Agent Task Assignments

**Strategy**: Assign each Level 3 workstream to a specialized documentation-writer sub-agent to manage token limits and enable parallel execution.

**Execution**: Each agent works independently with full context from reference documents.

---

## 🤖 Agent 1: Data Preparation Level 3

**Agent Type**: documentation-writer
**Estimated Time**: 27 hours
**Priority**: High (unanimous consensus)

### Task Assignment

Create complete Level 3 documentation for Data Preparation workstream including:

1. **metadata-schema-versioning.md** (12 hours, 500+ lines)
2. **label-parsing-generation.md** (10 hours, 450+ lines)
3. **data-preparation-swimlane.puml** (4 hours)
4. **Traceability table** in Level 2 index.md (1 hour)

### Context Documents

**Must Read Before Starting**:

- `/home/byron/dev/image_detection/docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md` - Complete file-to-LOC mapping for WS3
- `/home/byron/dev/image_detection/docs/architecture/LEVEL_3_IMPLEMENTATION_ROADMAP.md` - Detailed content outlines for Issues 4.1 and 4.2
- `/home/byron/dev/image_detection/docs/architecture/diagrams/level-2/data-preparation/index.md` - Existing Level 2 documentation
- `/home/byron/dev/image_detection/docs/architecture/SWIMLANE_TRACEABILITY_PROPOSAL.md` - Swimlane format and annotation standards

**Source Code to Document**:

- `/home/byron/dev/image_detection/scripts/annotate_base_metadata.py` (1,235 lines)
  - Lines 64-98: Capture method and domain taxonomy
  - Lines 101-361: Dataset configuration system
  - Lines 362-523: Three-layer metadata architecture (IMMUTABLE + ENRICHMENT)
  - Lines 635-852: Label parsers (9 dataset-specific parsers)
- `/home/byron/dev/image_detection/scripts/build_training_labels.py` (590 lines)
  - Lines 60-137: Degradation index (45-dimensional)
  - Lines 119-137: Anchor score priority logic
  - Lines 145-410: Training label builder

### Deliverable 1: metadata-schema-versioning.md

**Location**: `docs/architecture/diagrams/level-3/data-preparation/metadata-schema-versioning.md`

**Required Content** (500+ lines):

1. **Overview** (80 lines)
   - Three-layer architecture conceptual diagram
   - Rationale for separation
   - Data flow visualization

2. **Layer 1: IMMUTABLE** (120 lines)
   - `OriginalFileMetadata` class diagram (ER notation)
   - `OriginalLabels` class diagram
   - Field descriptions with source dataset mappings
   - Preservation guarantees
   - Code traceability: annotate_base_metadata.py lines 64-362

3. **Layer 2: ENRICHMENT** (150 lines)
   - `EnrichmentData` class diagram
   - `EnrichmentVersion` class diagram
   - Enrichment methods (automated, manual, llm)
   - Versioning workflow diagram
   - Backward compatibility rules
   - Code traceability: annotate_base_metadata.py lines 363-523

4. **Layer 3: TRAINING** (120 lines)
   - `TrainingLabels` class diagram
   - Computed on-demand architecture
   - Anchor score priority decision tree
   - Anchor weighting table (6 levels with formulas)
   - Code traceability: build_training_labels.py lines 60-137, 145-410

5. **Anchor Score Priority Algorithm** (80 lines)
   - Decision tree PlantUML diagram
   - Pseudocode implementation
   - Examples with different label combinations
   - Edge case handling

6. **Versioning & Migration** (50 lines)
   - Enrichment version management
   - Backward compatibility strategy
   - Migration procedures

**Acceptance Criteria**:

- ≥500 lines total
- Include 3-5 PlantUML diagrams (class diagrams, decision trees)
- All class fields documented with types and purposes
- Code references to specific line numbers
- Markdown linting passing

---

### Deliverable 2: label-parsing-generation.md

**Location**: `docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md`

**Required Content** (450+ lines):

1. **Parser Architecture** (100 lines)
   - Abstract parser interface
   - Parser registry pattern
   - Dataset-specific parser selection
   - Code traceability: annotate_base_metadata.py lines 635-700

2. **COCO Cache Optimization** (80 lines)
   - Cache initialization sequence diagram
   - Memory vs speed analysis
   - 100x speedup measurements
   - Implementation details

3. **Dataset-Specific Parsers** (180 lines)
   - parse_diqa_labels() - sequence diagram + code
   - parse_live_labels() - sequence diagram + code
   - parse_doclaynet_labels() - COCO annotation handling
   - parse_tablebank_labels() - COCO table extraction
   - parse_funsd_labels() - Form field parsing
   - parse_signatr_labels() - Writer ID extraction
   - 3 additional parsers (brief descriptions)
   - Code traceability: annotate_base_metadata.py lines 635-852

4. **45-Dimensional IQA Vector** (90 lines)
   - Vector structure table (indices 0-44)
   - Group mappings (Blur, Noise, Geometric, Illumination, Compression, Physical, Text, Scanner)
   - Construction algorithm
   - Code traceability: build_training_labels.py lines 60-137

**Acceptance Criteria**:

- ≥450 lines total
- Include 5-7 sequence diagrams (one per major parser)
- COCO cache optimization explained with diagrams
- All 9 parsers documented
- Code references to specific line numbers

---

### Deliverable 3: data-preparation-swimlane.puml

**Location**: `docs/architecture/diagrams/level-3/data-preparation/data-preparation-swimlane.puml`

**Required Content**:

**4 Swimlanes**:

1. Dataset Collection
2. Layer 1: Immutable
3. Layer 2: Enrichment
4. Layer 3: Training

**Annotations**: All 8 scripts with LOC from FILE_INVENTORY:

- download_all_datasets.py (470 lines)
- download_iqa_datasets.py (79 lines)
- download_phase3_datasets.py (290 lines)
- download_table_datasets.py (569 lines)
- download_omnidocbench.py (404 lines)
- validate_datasets.py (429 lines)
- annotate_base_metadata.py (1,235 lines) - split between Layer 1 & 2
- build_training_labels.py (590 lines)

**Legend**: Total 4,066 lines ✅ (matches LOC extraction)

**Example Annotation Format**:

```plantuml
:Build training labels;
note right
  **Script:**
  - scripts/build_training_labels.py (590 lines)

  **Total Step LOC**: 590 lines

  **Process:**
  - Construct 45-dim IQA vector
  - Calculate anchor scores
  - Apply weights

  **Documentation:**
  [[level-3/data-preparation/label-parsing-generation.md]]
end note
```

**Acceptance Criteria**:

- All 8 files annotated with LOC
- Total in legend matches 4,066
- Color-coded by layer
- Generates valid SVG

---

### Deliverable 4: Traceability Table (Level 2)

**Location**: Add section to `docs/architecture/diagrams/level-2/data-preparation/index.md`

**Required Content** (before "Related Documentation" section):

```markdown
## Source File Traceability

| Workflow Step | Source Files | LOC | Total |
|---------------|--------------|-----|-------|
| Dataset Collection | download_all_datasets.py, download_iqa_datasets.py, download_phase3_datasets.py, download_table_datasets.py, download_omnidocbench.py | 470, 79, 290, 569, 404 | 1,812 |
| Dataset Validation | validate_datasets.py | 429 | 429 |
| Layer 1: Immutable Metadata | annotate_base_metadata.py (lines 64-362) | ~600 | 600 |
| Layer 2: Enrichment | annotate_base_metadata.py (lines 363-523) | ~635 | 635 |
| Layer 3: Training Labels | build_training_labels.py | 590 | 590 |

**Workstream Total**: 4,066 lines ✅ (matches LOC extraction)

**Validation**: All files listed in traceability table match FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md
```

---

## 🤖 Agent 2: Production Runtime Level 3

**Agent Type**: documentation-writer
**Estimated Time**: 31 hours
**Priority**: High (unanimous consensus)

### Task Assignment

Create complete Level 3 documentation for Production Runtime workstream including:

1. **pipeline-state-machine.md** (12 hours, 550+ lines)
2. **device-orchestrator.md** (10 hours, 450+ lines)
3. **production-runtime-swimlane.puml** (8 hours)
4. **Traceability table** in Level 2 index.md (1 hour)

### Context Documents

**Must Read**:

- FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md - All 44 Production Runtime files with LOC
- LEVEL_3_IMPLEMENTATION_ROADMAP.md - Detailed outlines for Issues 4.3 and 4.4
- level-2/production-runtime/index.md - Existing comprehensive documentation (717 lines with state machine, error handling, device orchestration)
- SWIMLANE_TRACEABILITY_PROPOSAL.md - Swimlane examples

**Source Code** (16,910 lines total):

- src/image_preprocessing_detector/ingestion/ (8 files, 2,235 lines)
- src/image_preprocessing_detector/classification/ (4 files, 472 lines)
- src/image_preprocessing_detector/detection/ (15 files, 9,917 lines)
- src/image_preprocessing_detector/correction/ (2 files, 1,284 lines)
- src/image_preprocessing_detector/metrics/ (2 files, 1,418 lines)
- src/image_preprocessing_detector/routing/ (2 files, 150 lines)
- src/image_preprocessing_detector/output/ (2 files, 503 lines)
- src/image_preprocessing_detector/workers/ (3 files, 748 lines)
- src/image_preprocessing_detector/utils/ (1 file, 183 lines)

### Deliverables (See LEVEL_3_IMPLEMENTATION_ROADMAP.md for detailed outlines)

**pipeline-state-machine.md**: 13-state diagram, error recovery, edge cases
**device-orchestrator.md**: Device selection, budget enforcement, circuit breaker
**production-runtime-swimlane.puml**: 4 swimlanes with all 44 files annotated

---

## 🤖 Agent 3: Monitoring & Drift Level 3

**Agent Type**: documentation-writer
**Estimated Time**: 19 hours
**Priority**: High (user approved)

### Task Assignment

Create complete Level 3 documentation for Monitoring & Drift workstream including:

1. **end-to-end-lifecycle.md** (10 hours, 450+ lines)
2. **monitoring-drift-swimlane.puml** (4 hours)
3. **Traceability table** in Level 2 index.md (1 hour)
4. **Enhanced LOC validation** (4 hours)

### Context Documents

**Must Read**:

- FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md - All 7 Monitoring files with LOC
- LEVEL_3_IMPLEMENTATION_ROADMAP.md - Detailed outline for Issue 4.5
- level-2/monitoring-drift/index.md - Comprehensive 6-component architecture (890 lines)
- SWIMLANE_TRACEABILITY_PROPOSAL.md

**Source Code** (5,348 lines total):

- src/image_preprocessing_detector/drift/**init**.py (985 lines - drift detection)
- src/image_preprocessing_detector/drift/performance.py (1,027 lines - monitoring)
- src/image_preprocessing_detector/drift/alerting.py (1,061 lines - multi-channel alerts)
- src/image_preprocessing_detector/drift/active_learning.py (842 lines - sample harvesting)
- src/image_preprocessing_detector/drift/privacy_review.py (695 lines - GDPR/CCPA)
- src/image_preprocessing_detector/drift/retraining.py (743 lines - orchestration)

### Deliverables

**end-to-end-lifecycle.md**: Complete lifecycle sequence, state machines, compliance workflows
**monitoring-drift-swimlane.puml**: 6 swimlanes (one per component) with all 7 files annotated
**Enhanced validation**: Add `--validate-tables` and `--validate-swimlane` to extract_workstream_loc.sh

---

## 🤖 Agent 4: Model Training Swimlane + Remaining Tables

**Agent Type**: documentation-writer
**Estimated Time**: 7.5 hours
**Priority**: Medium

### Task Assignment

Create Model Training swimlane and complete remaining traceability tables:

1. **model-training-swimlane.puml** (4 hours)
2. **Traceability tables** for 5 remaining workstreams (3.5 hours)

### Context Documents

**Must Read**:

- FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md - Complete mappings
- level-2/model-training/index.md - Already comprehensive (755 lines)
- SWIMLANE_TRACEABILITY_PROPOSAL.md

**Source Code** (7,058 lines):

- modal/train_phase2_iqa.py (707 lines)
- modal/train_student_distillation.py (779 lines)
- modal/export_phase7_onnx.py (347 lines)
- src/.../training/ (6 files, 1,938 lines)
- src/.../models/ (7 files, 3,287 lines)

### Deliverables

**Swimlane**: 4 swimlanes (Data Pipeline, Teacher, Distillation, Export) with all 16 files
**Tables**: Add to pseudo-labeling, labeling-benchmarking, model-arena, synthetic-generation, remaining index.md files

---

## 📝 Task Invocation Commands

### Agent 1: Data Preparation

```
Invoke documentation-writer agent:

Create Level 3 documentation for Data Preparation workstream (WS3):

**Deliverables**:
1. docs/architecture/diagrams/level-3/data-preparation/metadata-schema-versioning.md (500+ lines)
   - Three-layer architecture ER diagrams
   - OriginalFileMetadata, OriginalLabels, EnrichmentData, TrainingLabels class diagrams
   - Anchor score priority algorithm (decision tree)
   - Versioning strategy
   - Code references to annotate_base_metadata.py specific lines

2. docs/architecture/diagrams/level-3/data-preparation/label-parsing-generation.md (450+ lines)
   - 9 dataset-specific parser sequence diagrams
   - COCO cache optimization flow
   - 45-dimensional IQA vector construction
   - Training label builder algorithm
   - Code references to build_training_labels.py

3. docs/architecture/diagrams/level-3/data-preparation/data-preparation-swimlane.puml
   - 4 swimlanes: Dataset Collection, Layer 1 (Immutable), Layer 2 (Enrichment), Layer 3 (Training)
   - Annotate ALL 8 scripts with LOC from FILE_INVENTORY
   - Legend showing total = 4,066 lines
   - Follow format from SWIMLANE_TRACEABILITY_PROPOSAL.md

4. Add Source File Traceability table to level-2/data-preparation/index.md
   - 5 workflow steps with file mappings and LOC
   - Total validates to 4,066 lines

**Reference Documents** (Read these first):
- docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md (WS3 section)
- docs/architecture/LEVEL_3_IMPLEMENTATION_ROADMAP.md (detailed outlines)
- docs/architecture/diagrams/level-2/data-preparation/index.md
- docs/architecture/SWIMLANE_TRACEABILITY_PROPOSAL.md

**Source Code to Analyze**:
- scripts/annotate_base_metadata.py (1,235 lines)
- scripts/build_training_labels.py (590 lines)

**Standards**:
- Follow LEVEL_2_DOCUMENTATION_TEMPLATE.md for markdown structure
- Include PlantUML diagrams (class diagrams, sequence diagrams, decision trees)
- All code references must include specific line numbers
- Validate against FILE_INVENTORY totals

**Estimated Time**: 27 hours
```

---

### Agent 2: Production Runtime

```
Invoke documentation-writer agent:

Create Level 3 documentation for Production Runtime workstream (WS1):

**Deliverables**:
1. docs/architecture/diagrams/level-3/production-runtime/pipeline-state-machine.md (550+ lines)
   - Full 13-state PlantUML state diagram
   - State transition tables (happy path, error paths, fallback paths)
   - Error recovery flows (4 categories with code examples)
   - Timeout escalation logic
   - Edge case handling (partial failures, circuit breaker, budget exhaustion)

2. docs/architecture/diagrams/level-3/production-runtime/device-orchestrator.md (450+ lines)
   - Device selection algorithm (decision tree PlantUML)
   - Budget enforcement (3-tier implementation)
   - Circuit breaker state machine (CLOSED → OPEN → HALF_OPEN)
   - Performance by device (comparison tables)
   - Integration with iqa_ml.py

3. docs/architecture/diagrams/level-3/production-runtime/production-runtime-swimlane.puml
   - 4 swimlanes: Ingestion & Preflight, Classification & Routing, Quality Analysis, Correction & Scoring
   - Annotate ALL 44 files with LOC from FILE_INVENTORY
   - Detection swimlane subdivided: Text Gate + Classical IQA + ML IQA + Layout-Lite
   - Legend showing total = 16,910 lines

4. Add Source File Traceability table to level-2/production-runtime/index.md
   - 11 workflow steps with file mappings and LOC
   - Total validates to 16,910 lines

**Reference Documents**:
- docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md (WS1 section - 44 files)
- docs/architecture/LEVEL_3_IMPLEMENTATION_ROADMAP.md (Issues 4.3, 4.4 outlines)
- docs/architecture/diagrams/level-2/production-runtime/index.md (already has state machine + error handling content - leverage this)
- docs/architecture/SWIMLANE_TRACEABILITY_PROPOSAL.md (swimlane example)

**Source Code** (16,910 lines across 44 files):
- Primary focus: detection/iqa_ml.py, utils/device_probe.py, workers/tasks.py
- Review all files in FILE_INVENTORY WS1 section

**Standards**:
- State diagram must show all 13 states
- Device selection must include decision tree PlantUML
- Swimlane must annotate all 44 files with LOC
- Total must validate to 16,910 lines

**Estimated Time**: 31 hours
```

---

### Agent 3: Monitoring & Drift

```
Invoke documentation-writer agent:

Create Level 3 documentation for Monitoring & Drift Detection workstream (WS7):

**Deliverables**:
1. docs/architecture/diagrams/level-3/monitoring-drift/end-to-end-lifecycle.md (450+ lines)
   - Complete lifecycle sequence diagram (drift → alert → harvest → privacy → retrain → arena → deploy)
   - RetrainingJob state machine (6 states: PENDING → PREPARING → TRAINING → VALIDATING → COMPLETED/FAILED/CANCELLED)
   - PrivacyReview workflow state machine (4 states: PENDING → REQUIRES_REVIEW → APPROVED/REJECTED)
   - Cross-component integration (how 6 components interact)
   - Compliance workflows (GDPR 30-day retention, CCPA opt-out)
   - Deployment gates (Arena PLCC validation before re-deploy)

2. docs/architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.puml
   - 6 swimlanes (one per component): Drift Detection, Performance Monitoring, Alerting, Active Learning, Privacy Review, Retraining
   - Annotate ALL 7 files with LOC from FILE_INVENTORY
   - Show data flow between components
   - Legend showing total = 5,348 lines

3. Add Source File Traceability table to level-2/monitoring-drift/index.md
   - 6 workflow steps (one per component) with file mappings
   - Total validates to 5,348 lines

4. Enhance scripts/extract_workstream_loc.sh with validation modes
   - Add `--validate-tables <workstream>` option
   - Add `--validate-swimlane <workstream>` option
   - Output discrepancy reports

**Reference Documents**:
- docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md (WS7 section)
- docs/architecture/LEVEL_3_IMPLEMENTATION_ROADMAP.md (Issue 4.5 outline)
- docs/architecture/diagrams/level-2/monitoring-drift/index.md (comprehensive 6-component doc - 890 lines)
- scripts/extract_workstream_loc.sh (enhance this script)

**Source Code** (5,348 lines across 7 files):
- drift/__init__.py (985 lines - drift detection, KL/PSI)
- drift/performance.py (1,027 lines - evaluation jobs)
- drift/alerting.py (1,061 lines - multi-channel dispatch)
- drift/active_learning.py (842 lines - harvesting)
- drift/privacy_review.py (695 lines - GDPR/CCPA workflows)
- drift/retraining.py (743 lines - orchestration)

**Estimated Time**: 19 hours
```

---

### Agent 4: Model Training + Remaining Tables

```
Invoke documentation-writer agent:

Create Model Training swimlane and complete all remaining traceability tables:

**Deliverables**:
1. docs/architecture/diagrams/level-3/model-training/model-training-swimlane.puml
   - 4 swimlanes: Data Preparation, Teacher Training, Student Distillation, Model Export
   - Annotate ALL 16 files with LOC from FILE_INVENTORY
   - Legend showing total = 7,058 lines

2. Add Source File Traceability tables to 5 remaining Level 2 docs:
   - level-2/model-training/index.md (4 workflow steps)
   - level-2/pseudo-labeling/index.md (5 workflow steps)
   - level-2/labeling-benchmarking/index.md (3 workflow steps)
   - level-2/model-arena/index.md (7 workflow steps)
   - level-2/synthetic-generation/index.md (3 workflow steps)

**Reference Documents**:
- docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md (all workstream sections)
- docs/architecture/diagrams/level-2/model-training/index.md (755 lines - already comprehensive)
- Other Level 2 docs for context

**Source Code**:
- Model Training: 16 files, 7,058 lines (see FILE_INVENTORY WS2 section)

**Estimated Time**: 7.5 hours
```

---

## 🔗 Dependency Chain

### Execution Order

**Week 3**: Agent 1 (Data Prep) + Agent 4 (Tables)

- Can run **fully in parallel**
- No dependencies between them

**Week 4**: Agent 2 (Production Runtime)

- Can start immediately (no dependencies)
- Reference Agent 1's swimlane format

**Week 5**: Agent 4 (Model Training swimlane)

- Can start immediately
- Quick task (4 hours)

**Week 6**: Agent 3 (Monitoring)

- Can start immediately
- Includes validation enhancement (benefits from all prior work)

### Critical Path

```
Week 3: Agents 1 + 4 (parallel) ────────────────────┐
Week 4: Agent 2 ─────────────────────────────────── │
Week 5: Agent 4 (quick) ────────────────────────────┤→ All complete
Week 6: Agent 3 (includes validation) ──────────────┘
```

**Calendar Time**: 4-6 weeks (depending on agent availability)
**Total Effort**: 84.5 hours (can parallelize to reduce wall time)

---

## ✅ Validation Checklist

### After Agent 1 (Data Prep)

- [ ] metadata-schema-versioning.md includes ≥3 class diagrams
- [ ] label-parsing-generation.md includes ≥5 sequence diagrams
- [ ] Swimlane total = 4,066 lines
- [ ] Traceability table total = 4,066 lines
- [ ] All code references include line numbers
- [ ] Markdown linting passing
- [ ] SVG generated from swimlane PUML

### After Agent 2 (Production Runtime)

- [ ] pipeline-state-machine.md includes 13-state diagram
- [ ] device-orchestrator.md includes decision tree diagram
- [ ] Swimlane total = 16,910 lines
- [ ] Traceability table total = 16,910 lines
- [ ] All 44 files annotated in swimlane
- [ ] Variance ≤2% between table, swimlane, and LOC script

### After Agent 3 (Monitoring)

- [ ] end-to-end-lifecycle.md includes lifecycle sequence diagram
- [ ] State machines for RetrainingJob and PrivacyReview
- [ ] Swimlane total = 5,348 lines
- [ ] `--validate-tables` and `--validate-swimlane` operational
- [ ] Validation reports generated for all workstreams

### After Agent 4 (Model Training + Tables)

- [ ] Model Training swimlane total = 7,058 lines
- [ ] All 8 workstreams have traceability tables
- [ ] All table totals match LOC extraction ±2%

---

## 📊 Success Metrics

### Completion Criteria

- ✅ **5 Level 3 docs** created (Data Prep × 2, Production Runtime × 2, Monitoring × 1)
- ✅ **4 swimlane diagrams** created (Data Prep, Production Runtime, Model Training, Monitoring)
- ✅ **8 traceability tables** added to Level 2 docs
- ✅ **Enhanced validation** operational with both modes
- ✅ **All totals validated** within ±2% of LOC extraction

### Quality Gates

- [ ] All diagrams render to valid SVG
- [ ] All markdown passes linting
- [ ] All code references are accurate (line numbers correct)
- [ ] All totals validated against LOC script
- [ ] No files missing from traceability (validated by enhanced script)

---

## 🚀 How to Execute

### Step 1: Invoke Agent 1 (Data Prep)

```bash
# Use Task tool to invoke documentation-writer agent
# Provide task description from "Agent 1: Data Preparation" section above
# Reference documents: FILE_INVENTORY, LEVEL_3_IMPLEMENTATION_ROADMAP, etc.
```

### Step 2: Invoke Agent 4 (Tables) in Parallel

```bash
# Can run simultaneously with Agent 1
# Quick task (8 hours total)
# Completes all traceability tables
```

### Step 3: Invoke Agent 2 (Production Runtime)

```bash
# After Agent 1 completes (to reference swimlane format)
# Or can start in parallel (no hard dependency)
```

### Step 4: Invoke Agent 3 (Monitoring + Validation)

```bash
# Can start anytime
# Includes validation enhancement (benefits from having tables/swimlanes to test)
```

---

## 📁 Expected Final Structure

```
docs/architecture/diagrams/
├── level-0/
│   └── index.md (existing)
├── level-1/
│   └── index.md (existing, updated)
├── level-2/
│   ├── production-runtime/
│   │   └── index.md (✅ enriched + traceability table added)
│   ├── model-training/
│   │   └── index.md (✅ enriched + traceability table added)
│   ├── data-preparation/
│   │   └── index.md (existing + traceability table added)
│   ├── pseudo-labeling/
│   │   └── index.md (✅ dependencies + traceability table added)
│   ├── labeling-benchmarking/
│   │   └── index.md (✅ created + traceability table added)
│   ├── model-arena/
│   │   └── index.md (existing + traceability table added)
│   ├── monitoring-drift/
│   │   └── index.md (existing + traceability table added)
│   └── synthetic-generation/
│       └── index.md (existing + traceability table added)
└── level-3/ (NEW)
    ├── data-preparation/
    │   ├── metadata-schema-versioning.md (NEW - Issue 4.1)
    │   ├── label-parsing-generation.md (NEW - Issue 4.2)
    │   └── data-preparation-swimlane.puml (NEW - Issue 6.1)
    ├── production-runtime/
    │   ├── pipeline-state-machine.md (NEW - Issue 4.3)
    │   ├── device-orchestrator.md (NEW - Issue 4.4)
    │   └── production-runtime-swimlane.puml (NEW - Issue 6.1)
    ├── model-training/
    │   └── model-training-swimlane.puml (NEW - Issue 6.1)
    └── monitoring-drift/
        ├── end-to-end-lifecycle.md (NEW - Issue 4.5)
        └── monitoring-drift-swimlane.puml (NEW - Issue 6.1)
```

**Total New Files**: 10 (5 Level 3 docs + 4 swimlanes + enhanced script)
**Total Modified Files**: 8 (Level 2 docs with traceability tables)

---

*Agent assignments ready for execution*
*Invoke agents sequentially or in parallel as capacity allows*
