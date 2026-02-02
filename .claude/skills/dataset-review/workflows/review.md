# Dataset Review Workflow

Step-by-step workflow for reviewing and validating a dataset catalog entry.

## Authoritative References

Before starting, ensure familiarity with:

- **Template**: docs/DATASET_TEMPLATE.md (v1.2.0) - Defines required entry format
- **Gaps Report**: docs/planning/DATASET_GAPS_REPORT.md - Known issues and priorities
- **Layer 2 Schema**: docs/schema/layer2_enrichment.schema.json - Schema definition

---

## Phase 0: Pre-flight Verification

### Checklist

```markdown
- [ ] Template version check (v1.2.0 or later)
- [ ] Dataset directory exists
- [ ] Canonical name validated
- [ ] Template file accessible
- [ ] Layer 2 schema accessible
```

### Commands

```bash
# GATE 0.1: Verify template version (MUST be v1.2.0+)
grep -m1 "^| 1\." docs/DATASET_TEMPLATE.md | head -1
# Expected: v1.2.0 or higher

# Check dataset directory (try both locations)
ls -la /mnt/e/image_detection/01_base_data/{category}/{dataset}/ 2>/dev/null || \
ls -la /mnt/e/image_detection/02_benchmark_only/{dataset}/

# Verify canonical name exists in naming standard
grep -n "{dataset}" docs/datasets/DATASET_NAMING_STANDARD.md
```

### Decision

- **All checks pass** → Proceed to Phase 1
- **Template version < 1.2.0** → STOP, update template first
- **Any other check fails** → Document blocker, STOP

---

## Phase 1: Current State Analysis

### Read Template

```bash
# Review template structure
head -100 docs/DATASET_TEMPLATE.md
```

### Find Current Entry

```bash
# Search for dataset section in catalog
grep -n "### \[{dataset}\]" docs/datasets/source/{dataset}.md
grep -n "### {dataset}" docs/datasets/source/{dataset}.md
```

### Create Gap Analysis

Create `tmp_cleanup/.tmp-{dataset}-gap-analysis.md` with:

```markdown
# Gap Analysis: {dataset}

**Date**: {YYYY-MM-DD}
**Reviewer**: dataset-catalog-agent
**Template Version**: 1.2.0

## Template Section Comparison

| Section | Present | Complete | Notes |
|---------|---------|----------|-------|
| Quick Stats | | | |
| Overview Table | | | |
| Source Data Inventory | | | |
| Dataset Split Locations | | | |
| Provided Labels | | | |
| Project Usage | | | |
| Parser & Metadata | | | |
| Data Locations | | | |
| Dataset Statistics | | | |
| Text Statistics | | | |
| Content Composition | | | |
| IQA Profile | | | |
| Known Issues | | | |
| Dataset-Specific Notes | | | |

## Missing Information

1.
2.
3.

## Research Required

- [ ] Paper lookup
- [ ] Repository check
- [ ] File structure verification
```

---

## Phase 2: Research & Information Gathering

### 2a. Paper Lookup

Search order:

1. [arXiv](https://arxiv.org/search/)
2. [Papers With Code](https://paperswithcode.com)
3. Google Scholar
4. Dataset official website

Extract:

- Release date and version
- Maintainer organization
- License (CRITICAL: cannot be inferred)
- BibTeX citation
- Official statistics (image counts, splits)

### 2b. Source Repository

Check locations:

- GitHub repository
- HuggingFace datasets
- University/organization page

Document:

- Download instructions
- README content
- Known issues from maintainers
- File format specifications
- **Split organization pattern** (by_folder / by_file_list / single_dir_with_manifest)

### 2c. File Structure Verification (Split-Aware)

**CRITICAL**: Datasets use THREE different split organization patterns. Check ALL patterns.

```bash
# Step 1: Determine split organization pattern
DATASET_DIR="/mnt/e/image_detection/01_base_data/{category}/{dataset}"

# Pattern 1: by_folder (train/val/test directories)
if [ -d "$DATASET_DIR/train" ] || [ -d "$DATASET_DIR/val" ] || [ -d "$DATASET_DIR/test" ]; then
    echo "Pattern: by_folder"
    find "$DATASET_DIR/train" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.tif" \) 2>/dev/null | wc -l
    find "$DATASET_DIR/val" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.tif" \) 2>/dev/null | wc -l
    find "$DATASET_DIR/test" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.tif" \) 2>/dev/null | wc -l
fi

# Pattern 2: by_file_list (train.txt, val.txt, test.txt manifests)
if [ -f "$DATASET_DIR/train.txt" ] || [ -f "$DATASET_DIR/val.txt" ] || [ -f "$DATASET_DIR/test.txt" ]; then
    echo "Pattern: by_file_list"
    wc -l "$DATASET_DIR/train.txt" 2>/dev/null
    wc -l "$DATASET_DIR/val.txt" 2>/dev/null
    wc -l "$DATASET_DIR/test.txt" 2>/dev/null
fi

# Pattern 3: single_dir_with_manifest (split defined in JSON/CSV)
if [ -f "$DATASET_DIR/manifest.json" ] || [ -f "$DATASET_DIR/splits.json" ] || [ -f "$DATASET_DIR/metadata.csv" ]; then
    echo "Pattern: single_dir_with_manifest"
    # Check manifest structure
    head -20 "$DATASET_DIR/manifest.json" 2>/dev/null || head -20 "$DATASET_DIR/splits.json" 2>/dev/null
fi

# Fallback: Count all images if no split structure detected
find "$DATASET_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.tif" \) | wc -l

# Check annotation formats
ls -la "$DATASET_DIR"/*.json "$DATASET_DIR"/*.txt "$DATASET_DIR"/*.xml 2>/dev/null
```

### 2d. Cross-Reference Validation

**IMPORTANT**: Filesystem counts are OBSERVATIONAL, not authoritative.

Create discrepancy table:

| Source | Stated Count | Split Pattern | Notes |
|--------|--------------|---------------|-------|
| Paper/Official Docs | | | **Authoritative for splits** |
| Repository README | | | |
| Manifest/File List | | | **Authoritative if present** |
| Actual Files | | | Observational only |

**Discrepancy Handling**:

- If manifest exists → manifest count is authoritative
- If paper differs from files → flag for investigation, DO NOT assume files are correct
- If duplicates/extras possible → note in catalog, investigate before training

---

## Phase 3: Catalog Entry Update

### Restructure Process

1. Copy current entry to working file
2. Map content to template sections
3. Fill missing sections from research
4. Move orphaned content to "Dataset-Specific Notes"
5. Apply documentation status markers

### Documentation Status Markers

- `[Official]` - From paper/documentation
- `[Empirically Derived]` - Computed from samples
- `[Inferred]` - Reasoned from evidence
- `[NEEDS_PROFILING]` - Requires analysis
- `[NEEDS_VERIFICATION]` - Needs confirmation

### GATE 3: Validation After Catalog Update (MANDATORY)

```bash
# Run structure validation
uv run python scripts/validate_datasets.py --dataset {dataset_name}

# Run completeness check
uv run python scripts/metadata_completeness_report.py --dataset {dataset_name}
```

**Gate Criteria**:

- `validate_datasets.py` exits 0
- No CRITICAL issues in completeness report
- All template sections exist (even if marked incomplete)

**If Gate Fails**: Document issues, DO NOT proceed to Phase 4

---

## Phase 4: Parser Audit

### Locate Parser

```bash
# Find parser file
ls -la src/image_preprocessing_detector/annotation/parsers/*/{dataset}*.py

# Check registry
grep -n "{dataset}" src/image_preprocessing_detector/annotation/parsers/registry.py
```

### Create Comparison Matrix (Schema-Derived)

**Core Fields** (from layer2_enrichment.schema.json):

| Source Field | Layer 2 Target | Parser Handles | Priority | Notes |
|--------------|----------------|----------------|----------|-------|
| Bounding boxes (XYXY) | layout_detections.bbox | | High | COCO format |
| Bounding boxes (polygon) | layout_detections.polygon | | High | If available |
| Bounding boxes (quad) | layout_detections.quad | | Medium | Rotated text |
| Segmentation masks | layout_detections.mask | | Medium | If available |
| Text transcription | text_content.full_text | | High | GT or OCR |
| Text source type | text_content.source_type | | High | Enum value |
| Quality scores | quality.overall_score | | Medium | 0-1 normalized |
| Language/script | language.language_code | | Medium | ISO codes |
| Class labels | layout_detections.class_name | | High | Taxonomy mapped |
| Class taxonomy | layout_detections.class_id | | High | Canonical IDs |
| Split info | provenance.split | | Medium | train/val/test |
| Hierarchy (page→block→line) | layout_detections.hierarchy | | Low | If structured |
| Key-value pairs | entities.key_value | | Medium | Forms/NER |
| Reading order | layout_detections.reading_order | | Low | If available |
| DPI/resolution | image_metadata.dpi | | Low | If available |

### GATE 4: Parser Validation (MANDATORY)

```bash
# Validate parser output against schema
uv run python scripts/validate_annotation_output.py --dataset {dataset_name}
```

**Gate Criteria**:

- Script exits 0
- Output matches layer2_enrichment.schema.json
- No type errors or missing required fields

**If No Parser Exists**:

- Document as parser_status = "Not Implemented"
- Note in catalog entry Section 3b
- Skip validation gate, proceed to Phase 5

---

## Phase 5: Text Content Integration

### Decision Tree

```text
Source provides text?
├── YES → source_type = "ground_truth"
│         Check parser populates text_content.full_text
│         Verify text_statistics computation
│
└── NO → annotations/{dataset}/ocr/ exists?
         ├── YES → source_type = "ocr_*"
         │         Check parser reads OCR output
         │
         └── NO → Document blocker
                  Add to Processing Status
```

### Layer 2 Required Fields

```json
{
  "text_content": {
    "full_text": "required string",
    "source_type": "required enum",
    "source_file": "optional",
    "extraction_method": "optional"
  }
}
```

### GATE 5: Text Statistics Validation (MANDATORY if text present)

```bash
# Calculate text statistics to verify population
uv run python scripts/calculate_text_statistics.py --input /mnt/e/image_detection/metadata_registry/json/{dataset}_layer2.json

# Enrich language metadata
uv run python scripts/enrich_language.py --dataset {dataset_name}
```

**Gate Criteria**:

- `text_statistics` object populated
- `char_count > 0` for samples with text
- Language detection completed

---

## Phase 6: Cross-File Synchronization

### CHECKPOINT: Create Rollback State

**Before making ANY cross-file changes**, create a checkpoint:

```bash
# Create checkpoint directory
mkdir -p tmp_cleanup/.checkpoint-{dataset}-$(date +%Y%m%d%H%M%S)
CHECKPOINT_DIR="tmp_cleanup/.checkpoint-{dataset}-$(date +%Y%m%d%H%M%S)"

# Backup all files that will be modified
cp docs/datasets/source/{dataset}.md "$CHECKPOINT_DIR/"
cp docs/datasets/DATASET_QUICK_REFERENCE.md "$CHECKPOINT_DIR/"
cp docs/datasets/DATASET_PROCESSING_STATUS.md "$CHECKPOINT_DIR/"
cp docs/datasets/DATASET_NAMING_STANDARD.md "$CHECKPOINT_DIR/"

echo "Checkpoint created: $CHECKPOINT_DIR"
```

### Update Quick Reference

Add/update row in appropriate table:

- Image count
- Capture method icon
- Label types available
- Metadata coverage rating

### Update Processing Status

Move to correct section:

- ✅ Training-Ready
- 🔄 In Progress
- ❌ Blocked
- 📚 Text Corpus

Document blockers with priority (P0-P3)

### Verify Naming Standard

Confirm canonical name entry exists with aliases

### GATE 6: Cross-File Consistency Validation

**All counts and statuses MUST match across files.**

```bash
# Extract counts from each file and compare
echo "=== Catalog Count ==="
grep -A5 "### \[{dataset}\]" docs/datasets/source/{dataset}.md | grep -i "total\|images"

echo "=== Quick Reference Count ==="
grep "{dataset}" docs/datasets/DATASET_QUICK_REFERENCE.md

echo "=== Processing Status ==="
grep "{dataset}" docs/datasets/DATASET_PROCESSING_STATUS.md
```

**If Gate Fails (counts don't match)**:

```bash
# ROLLBACK: Restore from checkpoint
cp "$CHECKPOINT_DIR"/* docs/
echo "Rolled back to checkpoint"
```

---

## Phase 7: Completion Validation

### GATE 7: Final Validation Suite (MANDATORY)

```bash
# Run full validation suite
uv run python scripts/validate_datasets.py
uv run python scripts/metadata_completeness_report.py

# Verify parser output if parser exists
uv run python scripts/validate_annotation_output.py --dataset {dataset_name} 2>/dev/null || echo "No parser"
```

### Final Checklist

```markdown
- [ ] Catalog entry follows template v1.2.0
- [ ] Canonical name used everywhere
- [ ] All template sections populated or marked
- [ ] Parser audit complete with schema-derived matrix
- [ ] Parser validation passed (Gate 4) OR no parser documented
- [ ] Text content handled OR blocker documented
- [ ] Text statistics validated (Gate 5) if applicable
- [ ] Quick Reference updated
- [ ] Processing Status updated
- [ ] Counts match across files (Gate 6 passed)
- [ ] Final validation suite passed (Gate 7)
- [ ] Checkpoint can be deleted (success) OR restored (failure)
```

### Quality Rating

- **Complete**: All gates passed, all sections filled, parser validated, text handled, files synced
- **Partial**: Core gates passed, some markers remain, blockers documented
- **Stub**: Basic structure only, gates not run, significant work needed

### Completion Report

```markdown
# Dataset Review Completion: {dataset}

**Date**: {YYYY-MM-DD}
**Quality Rating**: Complete/Partial/Stub
**Template Version**: 1.2.0

## Gate Results

| Gate | Script | Exit Code | Status |
|------|--------|-----------|--------|
| Gate 0 | Template version check | | PASS/FAIL |
| Gate 3 | validate_datasets.py | | PASS/FAIL/SKIP |
| Gate 4 | validate_annotation_output.py | | PASS/FAIL/SKIP |
| Gate 5 | calculate_text_statistics.py | | PASS/FAIL/SKIP |
| Gate 6 | Cross-file consistency | | PASS/FAIL |
| Gate 7 | Full validation suite | | PASS/FAIL |

## Phase Results

| Phase | Status | Notes |
|-------|--------|-------|
| 0: Pre-flight | PASS/FAIL | |
| 1: Analysis | PASS/FAIL | |
| 2: Research | PASS/FAIL | Split pattern: by_folder/by_file_list/manifest |
| 3: Catalog Update | PASS/FAIL | Gate 3: {status} |
| 4: Parser Audit | PASS/FAIL | Gate 4: {status} |
| 5: Text Integration | PASS/FAIL | Gate 5: {status} |
| 6: Synchronization | PASS/FAIL | Gate 6: {status} |
| 7: Validation | PASS/FAIL | Gate 7: {status} |

## Files Modified

- docs/datasets/source/{dataset}.md
- docs/datasets/DATASET_QUICK_REFERENCE.md
- docs/datasets/DATASET_PROCESSING_STATUS.md

## Checkpoint Status

- [ ] Checkpoint created: {checkpoint_dir}
- [ ] Checkpoint deleted (success) / Checkpoint restored (failure)

## Blockers (if any)

1.

## Next Actions

1.
```

---

## Operational Scripts

Run these scripts when needed during the review process:

### After Parser Updates

```bash
# Validate parser output against schema
uv run python scripts/validate_annotation_output.py --dataset {dataset_name}
```

### After Text Content Changes

```bash
# Calculate text statistics
uv run python scripts/calculate_text_statistics.py --input {layer2_json_path}

# Enrich language metadata
uv run python scripts/enrich_language.py --dataset {dataset_name}
```

### After Metadata Changes

```bash
# Regenerate Layer 2 metadata
uv run python scripts/annotate_base_metadata_incremental.py --dataset {dataset_name}

# Aggregate statistics
uv run python scripts/aggregate_layer2_metadata.py --dataset {dataset_name}
```

### Completeness Check

```bash
# Check metadata completeness
uv run python scripts/metadata_completeness_report.py
```

### Rollback (Emergency)

```bash
# List available checkpoints
ls -la tmp_cleanup/.checkpoint-{dataset}-*

# Restore from specific checkpoint
cp tmp_cleanup/.checkpoint-{dataset}-{timestamp}/* docs/
```
