---
owner: docs-team
purpose: Guide for integrating three-tier dataset documentation structure
schema_type: common
status: active
tags:
- datasets
- integration
- usage-guide
title: Dataset Documentation Integration Guide
---

> **Purpose**: Explains how to use the three-tier dataset documentation structure
> **Audience**: Claude Code and development team
> **Integration**: Add this section to project CLAUDE.md

---

## Modular Dataset Documentation Structure

We use a **token-optimized modular structure** with individual dataset files and task-based indices:

```
Tier 1: DATASET_QUICK_REFERENCE.md     (~800 lines, ~8K tokens)
   ↓
Tier 2: DATASET_PROCESSING_STATUS.md   (~500 lines, ~5K tokens)
   ↓
Tier 3: DATASET_NAMING_STANDARD.md     (~600 lines, ~6K tokens)
   ↓
Tier 4: Individual dataset files in source/ (51 files, 100-500 lines each)
   ↓
Tier 5: Task-based indices in indices/ (7 files for different training tasks)
```

### When to Use Each File

| Task | Use This File | Why |
|------|---------------|-----|
| **"Which datasets do I have for IQA training?"** | DATASET_QUICK_REFERENCE.md | Optimized for task-based lookup |
| **"How many images are ready for layout detection?"** | DATASET_QUICK_REFERENCE.md | Quick stats and training recipes |
| **"What's the current status of ohr-bench conversion?"** | DATASET_PROCESSING_STATUS.md | Operational status tracking |
| **"Which datasets need format conversion?"** | DATASET_PROCESSING_STATUS.md | Blockers and next steps |
| **"Is nist-sd2 the same as nist_db2?"** | DATASET_NAMING_STANDARD.md | Canonical names and aliases |
| **"What are the IQA sensitivity characteristics of TableBank?"** | Individual dataset files in datasets/source/ | Deep technical details |
| **"What's the license for PubTabNet?"** | Individual dataset files in datasets/source/ | Comprehensive dataset documentation |

---

## Usage Patterns for Claude Code

### Pattern 1: Training Planning Discussion

**User**: "I need to train the IQA student model. What datasets should I use?"

**Claude Code Flow**:

1. ✅ Read [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) → "IQA Training" section
2. ✅ Identify: ohr-bench (6,849 train), diqa-5000 (4,400 train), realdae (600 pairs), ocr-quality (1,000)
3. ✅ Check "Never Train On" table → reserve val/test splits
4. ⚠️ Check [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) → ohr-bench is 🔄 converting
5. ✅ Recommend: "Use diqa-5000 train + realdae + ocr-quality now, add ohr-bench when conversion completes"
6. ❌ Don't read Individual dataset files in datasets/source/ unless user asks for deep details

**Token Usage**: ~8K (Quick Ref) + ~5K (Status) = **13K tokens** vs 45K for full catalog

---

### Pattern 2: Dataset Availability Check

**User**: "Do we have multilingual text detection datasets ready?"

**Claude Code Flow**:

1. ✅ Read [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) → "Text Detection & Script Classification" section
2. ✅ Identify: mlt19 (10K train), mdiw13 (232K train), arabic-docs (10K), cc-ocr (6.5K)
3. ✅ Check "By Category" table → 524K total images
4. ⚠️ Check [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) → 2 converting (cocotext, iam)
5. ✅ Answer: "Yes, 12 datasets with 480K training images ready. Cocotext (64K) and iam (115K) converting."

**Token Usage**: **13K tokens** vs 45K for full catalog

---

### Pattern 3: Format Conversion Blockers

**User**: "Why can't I use ohr-bench yet?"

**Claude Code Flow**:

1. ✅ Read [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) → "In Progress" section
2. ✅ Find: ohr-bench (8,561 images, Parquet→PNG, blocker: 2.1GB parquet)
3. ✅ Check priority: P0 (IQA Training)
4. ✅ Answer: "ohr-bench needs parquet→PNG conversion (2.1GB, ~4GB output). Priority P0, ETA Week 1."

**Token Usage**: **5K tokens** vs 45K for full catalog

---

### Pattern 4: Naming Confusion Resolution

**User**: "Is nist_db2 the same as nist-sd2?"

**Claude Code Flow**:

1. ✅ Read [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md) → "Canonical Name Registry"
2. ✅ Find: `nist-sd2` (canonical) with aliases `[nist_db2, nist_sd2, nist_sd_2, nist-db2]`
3. ✅ Answer: "Yes, nist_db2 is an alias for canonical name nist-sd2. Use nist-sd2 in all new code."

**Token Usage**: **3K tokens** vs 45K for full catalog

---

### Pattern 5: Deep Technical Details (Rare)

**User**: "What are the IQA sensitivity characteristics of TableBank for blur and compression?"

**Claude Code Flow**:

1. ❌ Skip [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) → too high-level
2. ❌ Skip [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) → not relevant
3. ✅ Read [Individual dataset files in datasets/source/](Individual dataset files in datasets/source/) → TableBank section → "IQA Profile"
4. ✅ Find: Blur Sensitivity: HIGH, Compression Sensitivity: HIGH
5. ✅ Answer: "TableBank has HIGH blur sensitivity (grid lines sensitive) and HIGH compression sensitivity (JPEG artifacts destroy thin table lines)."

**Token Usage**: **45K tokens** (justified for deep technical query)

---

## Decision Tree for File Selection

```
START
  ↓
Is this about TRAINING TASK SELECTION or QUICK STATS?
  ├─ YES → Read DATASET_QUICK_REFERENCE.md
  │         ↓
  │         Found answer?
  │         ├─ YES → DONE (8K tokens)
  │         └─ NO → Check if STATUS question (proceed below)
  │
  └─ NO → Is this about CURRENT STATE, BLOCKERS, or FORMAT CONVERSION?
           ├─ YES → Read DATASET_PROCESSING_STATUS.md
           │         ↓
           │         Found answer?
           │         ├─ YES → DONE (5K tokens)
           │         └─ NO → Check if NAMING question (proceed below)
           │
           └─ NO → Is this about NAMING CONFUSION or ALIASES?
                    ├─ YES → Read DATASET_NAMING_STANDARD.md
                    │         ↓
                    │         DONE (3K tokens)
                    │
                    └─ NO → Deep technical details needed
                             ↓
                             Read Individual dataset files in datasets/source/ (45K tokens)
```

---

## File Characteristics Summary

### DATASET_QUICK_REFERENCE.md

- **Size**: ~800 lines, ~8K tokens
- **Purpose**: Training task selection, quick stats
- **Update Frequency**: Weekly (as datasets become training-ready)
- **Optimized For**: "Which datasets for X task?" queries
- **Contains**:
  - Datasets grouped by training purpose (IQA, Layout, Text Detection, etc.)
  - Label type index (COCO boxes, quality scores, OCR text, etc.)
  - Training recipes by phase
  - Critical filters (benchmark-reserved, license restrictions)
  - Quick lookup tables by image count and category

### DATASET_PROCESSING_STATUS.md

- **Size**: ~500 lines, ~5K tokens
- **Purpose**: Operational status tracking
- **Update Frequency**: Daily (during active conversion work)
- **Optimized For**: "What's blocking dataset X?" queries
- **Contains**:
  - Format conversion status (✅ ✓ ❌)
  - Label extraction progress
  - Blockers and next steps
  - Processing priorities and ETAs
  - Storage requirements

### DATASET_NAMING_STANDARD.md

- **Size**: ~600 lines, ~6K tokens
- **Purpose**: Canonical names and alias resolution
- **Update Frequency**: On-demand (when adding new datasets)
- **Optimized For**: "Is X the same as Y?" queries
- **Contains**:
  - Canonical name registry (all 50 datasets)
  - Alias mappings
  - Migration guide
  - Naming conventions and validation

### Individual dataset files in datasets/source/

- **Size**: ~4,300 lines, ~45K tokens
- **Purpose**: Comprehensive technical documentation
- **Update Frequency**: Monthly (major updates only)
- **Optimized For**: Deep technical queries
- **Contains**:
  - Detailed dataset documentation (per-dataset sections)
  - IQA sensitivity matrices
  - License details
  - Paper references
  - Benchmark performance metrics

---

## Integration with CLAUDE.md

Add this section to your project's CLAUDE.md:

```markdown
## Dataset Inventory

> **Token Optimized**: Use tiered documentation for efficient LLM context usage

**Quick Reference** (Start Here): [datasets/DATASET_QUICK_REFERENCE.md](datasets/DATASET_QUICK_REFERENCE.md)
- Training task selection ("Which datasets for IQA training?")
- Quick stats and image counts
- Training recipes by phase
- ~800 lines, ~8K tokens

**Processing Status**: [datasets/DATASET_PROCESSING_STATUS.md](datasets/DATASET_PROCESSING_STATUS.md)
- Current conversion/extraction status
- Blockers and next steps
- Processing priorities
- ~500 lines, ~5K tokens

**Naming Standard**: [datasets/DATASET_NAMING_STANDARD.md](datasets/DATASET_NAMING_STANDARD.md)
- Canonical names and aliases
- Resolve naming confusion
- Migration guide
- ~600 lines, ~6K tokens

**Full Catalog**: [docs/Individual dataset files in datasets/source/](docs/Individual dataset files in datasets/source/)
- Comprehensive technical documentation
- Deep details (IQA sensitivity, licenses, papers)
- Only use when Quick Reference insufficient
- ~4,300 lines, ~45K tokens

### Usage Guidelines for Claude Code

**Always start with DATASET_QUICK_REFERENCE.md** for:
- Training planning discussions
- Dataset selection by task
- Quick availability checks
- Label type filtering

**Use DATASET_PROCESSING_STATUS.md** for:
- Current state queries ("Is X ready?")
- Blocker identification
- Conversion progress tracking

**Use DATASET_NAMING_STANDARD.md** for:
- Resolving name conflicts
- Checking canonical names
- Understanding aliases

**Use Individual dataset files in datasets/source/** (last resort) for:
- Deep technical characteristics
- IQA sensitivity details
- License specifics
- Academic references

### Token Efficiency Examples

| Query Type | Files Read | Token Cost | Savings |
|------------|------------|------------|---------|
| "Datasets for IQA training?" | Quick Ref only | 8K | 83% (vs 45K) |
| "Is ohr-bench ready?" | Quick Ref + Status | 13K | 71% |
| "Is nist_db2 same as nist-sd2?" | Naming only | 6K | 87% |
| "TableBank blur sensitivity?" | Full Catalog | 45K | 0% (justified) |

**Expected Token Savings**: 70-85% for typical dataset queries
```

---

## Maintenance Workflow

### Weekly Updates (During Active Development)

**DATASET_QUICK_REFERENCE.md**:

- Update "Training-Ready" count when datasets complete conversion
- Add new datasets to appropriate "Training Purpose" tables
- Update "By Image Count" table
- Refresh "Training Recipes" if datasets change

**DATASET_PROCESSING_STATUS.md**:

- Move datasets from "In Progress" → "Training-Ready" when conversion completes
- Update priority order and ETAs
- Mark blockers as resolved
- Update storage tracking

**DATASET_NAMING_STANDARD.md**:

- Add new dataset canonical names
- Document any naming conflicts encountered
- Update migration checklist progress

### Monthly Reviews

**Individual dataset files in datasets/source/**:

- Add new per-dataset documentation sections
- Update IQA sensitivity matrix (if new datasets tested)
- Refresh license information
- Add new paper references

### On-Demand Updates

**All Files**:

- Add new datasets immediately when acquired
- Update when datasets move between tiers (benchmark → training)
- Refresh when major schema changes occur

---

## Testing the Integration

### Validation Checklist

Before committing documentation updates:

- [ ] **Quick Reference** has all training-ready datasets
- [ ] **Processing Status** reflects current conversion state
- [ ] **Naming Standard** includes all canonical names and aliases
- [ ] **Full Catalog** has detailed sections for all 50 datasets
- [ ] Cross-references between files are accurate
- [ ] Token counts are approximately correct (~8K, ~5K, ~6K, ~45K)
- [ ] No conflicting information between files
- [ ] All dataset counts match across files

### Spot Check Queries

Test these queries to validate integration:

```python
# Query 1: Training task selection
"Which datasets should I use for IQA training?"
# Expected: Quick Reference only (~8K tokens)

# Query 2: Current status
"What's the status of parquet conversions?"
# Expected: Processing Status (~5K tokens)

# Query 3: Naming resolution
"Are there multiple names for the NIST datasets?"
# Expected: Naming Standard (~6K tokens)

# Query 4: Deep technical
"What are the detailed IQA characteristics of all table datasets?"
# Expected: Full Catalog (~45K tokens)
```

---

## Related Documentation

- **Project Plan**: [docs/planning/PROJECT_PLAN.md](../planning/PROJECT_PLAN.md) - Phased implementation
- **Schema Specification**: [docs/schema/LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) - Label mappings
- **Training Methodology**: [docs/planning/PHASE7v4_TRAINING_DEEP_DIVE.md](../planning/PHASE7v4_TRAINING_DEEP_DIVE.md) - Training details

---

**Last Updated**: 2026-01-31
**Maintained By**: Data team
**Questions**: Create issue or contact data team lead
