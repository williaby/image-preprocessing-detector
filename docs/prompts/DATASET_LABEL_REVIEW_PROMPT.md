---
title: Dataset Source Label Review - Comprehensive Validation
purpose: Review source labels, parsers, and Layer 2 schema mapping for all datasets
owner: data-team
status: ready
priority: P0-CRITICAL
total_datasets: 46
---

# Task: Comprehensive Dataset Source Label Review

## Objective

For each dataset in the inventory, validate that:

1. **Source labels are properly documented** (what labels exist, in what format)
2. **Parser correctly extracts labels** (implementation status and correctness)
3. **Labels map to Layer 2 schema fields** (field mappings are documented)
4. **Label flow is documented** (from source → parser → Layer 2 → training)

## Context

Project A uses a three-layer metadata architecture:

- **Layer 1 (Immutable)**: Original source labels preserved exactly as-is
- **Layer 2 (Enrichment)**: Derived annotations from ML models + analysis
- **Layer 3 (Training)**: Training-ready labels computed on-demand

**Current Issues**:

- 20/46 datasets have Layer 2 metadata, but completeness varies
- Source label documentation may be incomplete
- Parser implementations may not extract all available labels
- Label flow not fully documented for all datasets

---

## Review Checklist (Per Dataset)

For each assigned dataset, complete this review:

### 1. Source Label Discovery

**Investigate**:

- [ ] What label files exist in the source dataset? (JSON, XML, CSV, TXT, etc.)
- [ ] What label formats are used? (COCO JSON, Pascal VOC, custom format, etc.)
- [ ] What information is available? (Bounding boxes, quality scores, OCR text, classifications, etc.)
- [ ] Are labels at image-level, word-level, character-level, or document-level?
- [ ] Are there train/val/test split files?

**Document in**: `docs/datasets/source_labels/{dataset_name}_source_labels.md`

**Template**:

```markdown
## {Dataset Name} - Source Labels

**Dataset**: {canonical-name}
**Source**: {GitHub/HuggingFace/Paper URL}
**License**: {License}

### Label Files Structure

```

dataset_root/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── annotations/
    ├── train.json              ← COCO format
    ├── val.json
    └── test.json

```

### Label Format

**Format Type**: COCO JSON / Pascal VOC XML / Custom CSV / etc.

**Fields Available**:
- Bounding boxes: Yes/No (format: COCO [x,y,w,h] or XYXY or XYWH)
- Class labels: Yes/No (classes: Caption, Table, Text, etc.)
- OCR text: Yes/No (word-level / line-level / page-level)
- Quality scores: Yes/No (MOS 1-5 / normalized 0-1 / custom)
- Script/Language: Yes/No (ISO codes / custom labels)
- Degradation types: Yes/No (blur, noise, skew, etc.)

**Example Label**:
```json
{example from actual dataset annotation file}
```

### Split Information

- Train: {count} images
- Val: {count} images (RESERVED for evaluation)
- Test: {count} images (RESERVED for evaluation)
- Total: {count} images

### License & Usage Restrictions

- Commercial use: Yes/No
- Research only: Yes/No
- Attribution required: Yes/No

```

---

### 2. Parser Implementation Review

**Investigate**:
- [ ] Does a parser exist for this dataset?
- [ ] Where is it located? (`src/image_preprocessing_detector/annotation/parsers/{name}.py`)
- [ ] What labels does the parser extract?
- [ ] Does the parser extract ALL available source labels or only a subset?
- [ ] Are there any labels being ignored?
- [ ] Is the parser registered in the parser registry?

**Check Files**:
- `src/image_preprocessing_detector/annotation/parsers/`
- `src/image_preprocessing_detector/annotation/parsers/__init__.py` (registry)

**Document findings** in review report.

**Template**:
```markdown
### Parser Implementation

**Parser Location**: `src/image_preprocessing_detector/annotation/parsers/{name}.py`
**Registration Status**: ✅ Registered / ❌ Not registered / ⚠️ Needs update

**Labels Extracted**:
- [x] Bounding boxes → `original_labels.{dataset}_annotations.boxes`
- [x] Class labels → `original_labels.{dataset}_annotations.classes`
- [ ] OCR text → **NOT EXTRACTED** (available but parser ignores)
- [ ] Quality scores → **NOT IMPLEMENTED** (parser doesn't support)

**Missing Extractions**:
- OCR text available in source but parser doesn't extract it
- Recommended: Update parser to extract all source labels

**Parser Code Quality**:
- Type hints: Yes/No
- Error handling: Adequate/Needs improvement
- Test coverage: {percentage}%
- Documentation: Complete/Partial/Missing
```

---

### 3. Layer 2 Schema Mapping

**Investigate**:

- [ ] Which Layer 2 schema fields does this dataset populate?
- [ ] Are there source labels that COULD populate additional Layer 2 fields?
- [ ] Are the field mappings documented?
- [ ] Is the mapping logic correct?

**Check**:

- `docs/schema/LABEL_MAPPING_SPECIFICATION.md` - Should document mapping
- Layer 2 metadata file: `/mnt/e/image_detection/metadata_registry/json/{dataset}_metadata.json`

**Document findings**:

```markdown
### Layer 2 Schema Mapping

**Populated Fields** (from source labels):
- [x] `capture_method` ← Dataset configuration (Tier 0)
- [x] `domain.level1` ← Inferred from dataset type
- [x] `content_flags.has_table` ← Parsed from COCO annotations (class="Table")
- [x] `layout_detections` ← COCO bounding boxes

**Unpopulated Fields** (could be populated from source):
- [ ] `quality.overall_score` ← **Available in source** as MOS scores
- [ ] `language.script_code` ← **Available in source** as language labels
- [ ] `text_scope.scope` ← Could infer from annotation granularity

**Missing Mappings**:
- Source has MOS scores in `annotations/quality.csv` but parser doesn't extract
- Recommended: Update parser to map MOS → `quality.overall_score`
```

---

### 4. Documentation Validation

**Check**:

- [ ] Is dataset documented in DATASET_CATALOG.md?
- [ ] Is label format documented in LABEL_MAPPING_SPECIFICATION.md?
- [ ] Is parser documented in architecture diagrams?
- [ ] Are example labels shown in documentation?

**Update**:

- [ ] DATASET_CATALOG.md - Add/update dataset section
- [ ] LABEL_MAPPING_SPECIFICATION.md - Document label mappings
- [ ] Create source_labels documentation file (Step 1 output)

---

## Datasets to Review (46 total)

### Batch 1: High-Priority IQA Datasets (5 datasets)

**Assignment**: Review these datasets first (critical for IQA training)

| Dataset | Images | Source Labels Expected | Priority |
|---------|--------|----------------------|----------|
| ohr-bench | 8,561 | Quality scores (0-100), OCR text | P0 |
| diqa-5000 | 5,500 | Human MOS (1-5), image paths | P0 |
| realdae | 1,200 | Before/after pairs, quality metrics | P0 |
| ocr-quality | 1,000 | Human quality scores, multilingual | P1 |
| iqa_phase7_165k | 165,000 | Synthetic quality labels (8 dimensions) | P1 |

### Batch 2: Layout Detection Datasets (8 datasets)

| Dataset | Images | Source Labels Expected | Priority |
|---------|--------|----------------------|----------|
| doclaynet | 81,471 | COCO boxes, 11 DocLayNet classes | P0 |
| pubtabnet | 568,000 | COCO boxes, table structure, HTML | P0 |
| tablebank | 278,582 | COCO boxes, table regions | P0 |
| fintabnet | 97,475 | COCO boxes, table structure | P1 |
| funsd | 398 | COCO boxes, OCR text, form entities | P1 |
| funsd_plus | 1,139 | COCO boxes, OCR text, extended annotations | P1 |
| sroie | 2,043 | COCO boxes, OCR text, key-value pairs | P1 |
| omnidocbench | Metadata | Multi-task labels, benchmark framework | P2 |

### Batch 3: Multilingual/Script Detection (13 datasets)

| Dataset | Images | Source Labels Expected | Priority |
|---------|--------|----------------------|----------|
| synth-multiscript-250k | 250,000 | Script labels (27 scripts), quality labels | P0 |
| mdiw13 | 290,213 | Script labels (13 scripts), word boxes | P0 |
| mlt19 | 20,000 | Language labels (10), word boxes | P0 |
| cc_ocr | 6,533 | CJK text, word boxes | P1 |
| arabic_docs_ocr | 10,045 | Arabic OCR text, word/page level | P1 |
| hindi_ocr_synthetic | 80,009 | Hindi OCR text, synthetic | P1 |
| multilingual_scripts | 3,279 | 27 script labels, synthetic | P2 |
| yarmouk_ocr | 15,062 | Arabic OCR text | P2 |
| cocotext | 63,686 | Scene text, word boxes, language | P1 |
| siw13 | 16,291 | Script labels (13 scripts) | P2 |
| cvsi | 10,715 | Video scene text | P2 |
| nepali_handwritten | 958 | Devanagari handwriting | P2 |
| pucit_ohul_urdu | 7,401 | Urdu handwriting | P2 |

### Batch 4: Degradation/Quality Datasets (7 datasets)

| Dataset | Images | Source Labels Expected | Priority |
|---------|--------|----------------------|----------|
| dibco | 343 | Ground truth binary images, degradation types | P0 |
| tobacco800 | 1,290 | Document class labels, degradation | P1 |
| historical_degraded | 1,356 | Degradation labels, archival scans | P1 |
| rvl_cdip | 16,000 | Document class (16 classes) | P1 |
| midv500 | 3,612 | Mobile capture metadata, 50 countries | P2 |
| midv500_data | 15,050 | Extended mobile capture metadata | P2 |
| smartdoc-qa | 4,280 | Quality assessment, mobile capture | P1 |

### Batch 5: Handwriting Datasets (5 datasets)

| Dataset | Images | Source Labels Expected | Priority |
|---------|--------|----------------------|----------|
| hasyv2 | 168,233 | Symbol labels, handwriting | P1 |
| nist_sd19 | 3,669 | Character labels, handwriting | P1 |
| nist_sd2 | 5,590 | Form labels, tax forms | P2 |
| nist_sd6 | 5,595 | Form + handwriting labels | P2 |
| im2latex | 10,000 | LaTeX formulas, math symbols | P2 |

### Batch 6: Specialized/Financial (8 datasets)

| Dataset | Images | Source Labels Expected | Priority |
|---------|--------|----------------------|----------|
| financebench | 54,121 | Financial tables, QA pairs | P1 |
| bhutan_financial | 135 | Annual report structure | P2 |
| invoices_kaggle | 1,414 | Invoice fields, key-value pairs | P2 |
| mathverse | 6,940 | Math problems, multi-modal | P2 |
| multimodal_textbook | 1,113 | STEM diagrams, equations | P2 |
| signatr6k | 12,514 | Text segmentation, signatures | P2 |
| mle2e | 1,816 | Multi-lingual end-to-end | P2 |
| synthetic_iqa | 9 | Test samples, quality labels | P2 |

### Batch 7: Text Corpora (2 datasets)

| Dataset | Samples | Source Labels Expected | Priority |
|---------|---------|----------------------|----------|
| openlid-v2 | 116M+ | Language ID labels (201 languages) | P1 |
| wili_2018 | 235,000 | Wikipedia language ID | P2 |

---

## Review Template (Per Dataset)

Create a report for each dataset: `docs/datasets/reviews/{dataset_name}_review.md`

```markdown
# {Dataset Name} - Source Label Review

**Review Date**: 2025-01-30
**Reviewer**: {Agent/Person Name}
**Dataset Canonical Name**: {canonical-name}
**Status**: ✅ Complete / ⚠️ Issues Found / ❌ Major Problems

---

## 1. Source Label Discovery

### Label Files Located

**Path**: `/mnt/e/image_detection/01_base_data/{dataset}/annotations/`

**Files**:
- `train_annotations.json` (COCO format, 150MB)
- `val_annotations.json` (COCO format, 15MB)
- `test_annotations.json` (COCO format, 15MB)
- `quality_scores.csv` (MOS scores, 500KB)

### Label Format Analysis

**Primary Format**: COCO JSON

**Fields Present**:
```json
{
  "images": [...],
  "annotations": [
    {
      "id": 12345,
      "image_id": 67890,
      "category_id": 5,
      "bbox": [x, y, width, height],
      "area": 45000,
      "iscrowd": 0
    }
  ],
  "categories": [
    {"id": 1, "name": "Caption"},
    {"id": 2, "name": "Footnote"},
    ...
  ]
}
```

**Additional Labels**:

- Quality scores in separate CSV: `image_id, mos_score, annotator_id`
- OCR text in TXT files: `{image_id}.txt`

### Label Granularity

- Bounding boxes: **Element-level** (tables, figures, text blocks)
- Quality scores: **Image-level** (one MOS per image)
- OCR text: **Page-level** (full page transcription)
- Script labels: **Word-level** (per-word language codes)

---

## 2. Parser Implementation Status

### Parser Location

**File**: `src/image_preprocessing_detector/annotation/parsers/{dataset_name}.py`
**Exists**: ✅ Yes / ❌ No / ⚠️ Incomplete

### Parser Analysis

**Class**: `{DatasetName}Parser(DatasetParser)`

**Methods Implemented**:

- [x] `parse_original_labels(image_path)` - Extracts COCO boxes
- [x] `get_split(image_path)` - Returns train/val/test
- [ ] `parse_quality_scores(image_path)` - **NOT IMPLEMENTED** (CSV available)
- [ ] `parse_ocr_text(image_path)` - **NOT IMPLEMENTED** (TXT files available)

**Labels Extracted vs Available**:

| Label Type | Available in Source | Extracted by Parser | Status |
|------------|-------------------|-------------------|--------|
| COCO bounding boxes | ✅ Yes | ✅ Extracted | ✅ Complete |
| Quality scores (MOS) | ✅ Yes (CSV) | ❌ **Not extracted** | ⚠️ Missing |
| OCR text | ✅ Yes (TXT) | ❌ **Not extracted** | ⚠️ Missing |
| Script labels | ❌ No | N/A | N/A |

**Issues Found**:

1. Parser only extracts COCO boxes, ignores quality scores in CSV
2. OCR text files exist but are not parsed
3. No error handling for missing annotation files

**Recommendations**:

- Add `_parse_quality_csv()` method to extract MOS scores
- Add `_parse_ocr_text()` method to extract text transcriptions
- Add try/except for missing files

---

## 3. Layer 2 Schema Mapping

### Field Mapping Table

| Source Label | Parser Extraction | Layer 2 Field | Mapping Logic | Status |
|--------------|------------------|---------------|---------------|--------|
| `annotations[].bbox` | ✅ `parse_original_labels()` | `layout_detections[].bbox` | Direct COCO format | ✅ Mapped |
| `annotations[].category_id` | ✅ `parse_original_labels()` | `layout_detections[].class_name` | ID→name via categories | ✅ Mapped |
| `quality_scores.csv:mos_score` | ❌ Not extracted | `quality.overall_score` | Normalize MOS 1-5 → 0-1 | ❌ **MISSING** |
| `{image_id}.txt` | ❌ Not extracted | `text_scope.estimated_chars` | Count chars in text | ❌ **MISSING** |
| Dataset config | ✅ Hardcoded | `capture_method.method` | "born_digital" | ✅ Mapped |
| Dataset config | ✅ Hardcoded | `domain.level1` | "SCI" | ✅ Mapped |

### Layer 2 Field Coverage

**Populated Fields**:

- [x] `capture_method` (Tier 0 - dataset config)
- [x] `resolution` (from image file metadata)
- [x] `domain` (Tier 0 - dataset config)
- [x] `content_flags.has_table` (Tier 2 - YOLO inference OR Tier 1 - COCO labels)
- [x] `layout_detections` (Tier 1 - COCO annotations)

**Unpopulated Fields** (with available source data):

- [ ] `quality.overall_score` ← **CSV has MOS scores**
- [ ] `quality.degradations` ← Could analyze images
- [ ] `text_scope.estimated_chars` ← **TXT files have text**
- [ ] `structure.text_density` ← Could compute from layout
- [ ] `structure.layout_type` ← Could infer from layout_detections

**Unpopulated Fields** (no source data):

- [ ] `language.script_code` ← Needs script detection model
- [ ] `llm_scores` ← Needs SigLIP inference

---

## 4. Label Flow Documentation

### Current Flow

```
Source Labels              Parser                    Layer 2 Schema
─────────────              ──────                    ──────────────
train.json            →    {Dataset}Parser.    →    layout_detections[]
├── annotations           parse_original_labels()    (COCO boxes)
└── categories                  ↓
                          original_labels.          content_flags.has_table
quality_scores.csv         {dataset}_annotations    (inferred from boxes)
(NOT PARSED)                                   ×→  (NOT MAPPED - parser gap)

{image_id}.txt
(NOT PARSED)                                   ×→  text_scope.estimated_chars
                                                    (NOT MAPPED - parser gap)
```

### Documented Flow

**File**: `docs/schema/LABEL_MAPPING_SPECIFICATION.md`

**Section**: Should have detailed mapping for this dataset

**Status**: ✅ Documented / ⚠️ Partial / ❌ Missing

**Recommendations**:

- Document quality score CSV → Layer 2 mapping
- Document OCR text extraction → text_scope mapping
- Add flow diagram to LABEL_MAPPING_SPECIFICATION.md

---

## 5. Recommendations & Action Items

### Parser Updates Needed

- [ ] **Add quality score extraction**: Parse `quality_scores.csv` → `quality.overall_score`
- [ ] **Add OCR text extraction**: Parse `{image_id}.txt` → `text_scope.estimated_chars/words`
- [ ] **Add error handling**: Handle missing annotation files gracefully
- [ ] **Add tests**: Unit tests for parser with sample data

### Documentation Updates Needed

- [ ] **LABEL_MAPPING_SPECIFICATION.md**: Add detailed mapping for this dataset
- [ ] **Source labels doc**: Create `docs/datasets/source_labels/{dataset}_source_labels.md`
- [ ] **Parser docstrings**: Add comprehensive docstrings to parser class
- [ ] **DATASET_CATALOG.md**: Update with label format details

### Enrichment Pipeline Updates

- [ ] **Run missing enrichment providers**: Language, Degradation, Structure (if applicable)
- [ ] **Re-aggregate metadata**: After parser updates and enrichment

---

## Summary

**Overall Status**: ✅ Good / ⚠️ Needs Work / ❌ Major Issues

**Key Findings**:

- {Summary of what's working well}
- {Summary of gaps and issues}
- {Recommendations for improvement}

**Estimated Effort to Complete**:

- Parser updates: {X} hours
- Documentation updates: {Y} hours
- Testing: {Z} hours
- **Total**: {X+Y+Z} hours

```

---

## Deliverables (Per Dataset)

1. **Source Label Documentation**: `docs/datasets/source_labels/{dataset_name}_source_labels.md`
2. **Review Report**: `docs/datasets/reviews/{dataset_name}_review.md`
3. **Parser Issues List**: Documented in review report
4. **Mapping Gaps**: Documented in review report
5. **Action Items**: Prioritized list of updates needed

---

## Consolidated Report (After All Reviews)

After reviewing all datasets, create: `docs/datasets/CONSOLIDATED_LABEL_REVIEW_REPORT.md`

**Contents**:
- Summary statistics (how many datasets have complete parsers, etc.)
- Common parser patterns and gaps
- Systematic mapping issues across datasets
- Prioritized action plan for parser updates
- Documentation gaps summary

**Template**:
```markdown
# Consolidated Dataset Label Review Report

**Review Period**: 2025-01-30
**Datasets Reviewed**: 46/46
**Reviewers**: {List of agents/people}

## Summary Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Datasets with parsers | 30 | 65% |
| Datasets without parsers | 16 | 35% |
| Parsers extracting ALL source labels | 12 | 26% |
| Parsers with missing extractions | 18 | 39% |
| Datasets with complete Layer 2 mapping docs | 8 | 17% |

## Common Issues

### Issue 1: Quality Scores Not Extracted (15 datasets)

**Datasets Affected**: ohr-bench, diqa-5000, ...

**Problem**: Source has MOS/quality scores in CSV/JSON but parsers don't extract

**Recommendation**: Create shared `QualityScoreParser` mixin

### Issue 2: OCR Text Ignored (12 datasets)

**Datasets Affected**: {list}

**Problem**: OCR ground truth exists but parsers skip it

**Recommendation**: Add `text_scope.estimated_chars` population from OCR

## Prioritized Action Plan

**Phase 1** (Week 1): Update P0 parsers
- [ ] ohr-bench: Add quality score extraction
- [ ] diqa-5000: Add MOS extraction
- [ ] synth-multiscript-250k: Verify script label extraction

**Phase 2** (Week 2): Update P1 parsers
- [ ] mdiw13: Add script label extraction
- [ ] mlt19: Add language label extraction
- [ ] Layout datasets: Verify COCO extraction complete

**Phase 3** (Week 3): Documentation
- [ ] LABEL_MAPPING_SPECIFICATION.md: Document all mappings
- [ ] Create source_labels docs for all datasets
- [ ] Update DATASET_CATALOG.md
```

---

## Execution Instructions

### For LLM Agent

**You will be assigned a batch of datasets** (e.g., Batch 1: High-Priority IQA Datasets).

**For each dataset in your batch**:

1. **Locate source dataset**:

   ```bash
   ls -lh /mnt/e/image_detection/01_base_data/{dataset_name}/
   ls -lh /mnt/e/image_detection/02_benchmark_only/{dataset_name}/
   ```

2. **Find annotation files**:

   ```bash
   find /mnt/e/.../01_base_data/{dataset} -name "*.json" -o -name "*.xml" -o -name "*.csv"
   ```

3. **Examine label format**:

   ```bash
   # Check COCO JSON structure
   cat annotations/train.json | jq '.annotations[0]'

   # Check CSV format
   head -5 quality_scores.csv
   ```

4. **Check parser implementation**:

   ```bash
   cat src/image_preprocessing_detector/annotation/parsers/{dataset}.py
   ```

5. **Review Layer 2 metadata**:

   ```bash
   cat /mnt/e/.../metadata_registry/json/{dataset}_metadata.json | jq '.samples[0].enrichments.versions[0].data | keys'
   ```

6. **Create source labels documentation**
7. **Create review report**
8. **List action items**

---

## Tools Available

- **Read** tool: Read source files, parsers, metadata
- **Grep** tool: Search for label references in code
- **Bash** tool: List files, check formats, run validation
- **Write** tool: Create documentation files

---

## Success Criteria

Your review is complete when:

- [x] Source labels fully documented (formats, fields, examples)
- [x] Parser status assessed (exists, complete, gaps identified)
- [x] Layer 2 mapping documented (what maps to what)
- [x] Label flow diagram created (source → parser → Layer 2)
- [x] Action items prioritized (parser updates, documentation, enrichment)
- [x] Review report written for each dataset

---

## References

- **Layer 2 Schema**: `/home/byron/dev/image_detection/docs/schema/layer2_enrichment.schema.json`
- **Parser Base Class**: `/home/byron/dev/image_detection/src/image_preprocessing_detector/annotation/parsers/base.py`
- **Existing Documentation**: `/home/byron/dev/image_detection/docs/schema/LABEL_MAPPING_SPECIFICATION.md`
- **Dataset Catalog**: `/home/byron/dev/image_detection/docs/DATASET_CATALOG.md`

---

**Estimated Total Effort**: 46 datasets × 30 minutes = 23 hours (can be parallelized across 5 batches)
