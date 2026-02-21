> **Version**: 2.3.0
> **Date**: 2026-02-14
> **Auditor**: claude-opus-4-6
> **Methodology**: 9-Phase Audit (v2.3.0)
> **Status**: COMPLETE
> **Grade**: B (85.1/100)

---

## Dataset Overview

| Property | Value |
|----------|-------|
| Dataset Name | ohr-bench |
| Total Samples | 8,303 (Layer 2) / 8,561 (HuggingFace) |
| Image Base Path | /mnt/e/image_detection/02_benchmark_only/ohr-bench/ |
| Audit Started | 2026-02-13 |
| Audit Completed | 2026-02-14 |
| Enrichment Version | integrated_v2 |

---

## Pre-Flight Checklist

### Dataset Registration

- [x] Dataset registered in `scripts/audit/audit_config.py`
- [x] Metadata JSON exists at `/mnt/e/image_detection/metadata_registry/json/ohr-bench_metadata.json`
- [x] Dataset source doc exists at `docs/datasets/source/ohr-bench.md`

### Enrichment Source Inventory

| Source | Path | Exists? | Notes |
|--------|------|---------|-------|
| Base metadata | `json/ohr-bench_metadata.json` | ✅ | 8,303 samples |
| LLM enrichment | N/A | ⏭️ | Not run for this dataset |
| Language enrichment | `json/ohr-bench_language_enrichment.json` | ✅ | Truncated: 1,000/8,259 records |
| HF GT language | `json/ohr-bench_hf_language_enrichment.json` | ✅ | 8,561 records (fallback) |
| Docling layout | `extracted/ohr-bench/` (7 batch files) | ✅ | 136,555 annotations, 14 categories |
| Docling OCR | `extracted/ohr-bench/` (7 batch files) | ✅ | 1,261 records |
| Classical IQA | N/A | ⏭️ | Not applicable (born-digital) |
| Resolution quality | N/A | ⏭️ | Not run |

**Total sources available**: 5/11

### Known Issues Applied

| Issue | Title | Applies? | Action |
|-------|-------|----------|--------|
| KI-001 | Docling layout label casing | ✅ Yes | Applied title_case normalization |
| KI-005 | Capture method detection | ✅ Yes | Hardcoded BORN_DIGITAL from paper |
| KI-008 | Script family re-derivation | ✅ Yes | Re-derived via `get_script_family()` |

### Dataset Characteristics

| Property | Value | Source |
|----------|-------|--------|
| Is synthetic? | No | Born-digital PDF extraction |
| Primary language(s) | English (94.2%), Chinese (1.8%) | OpenLID + HF GT analysis |
| Primary script(s) | Latin (94.4%), CJK (1.9%) | Derived from language |
| Capture method | BORN_DIGITAL | Paper (PDF extraction @ 300 DPI) |
| Expected splits | Single split (all "train") | HuggingFace dataset |
| Total samples | 8,561 pages from 488 documents | HuggingFace parquet |
| Has ground truth files? | Yes (gt_text column) | HuggingFace parquet |
| Multi-column documents? | Yes (multi-domain) | Layout extraction |

---

## Phase 1: Automated Prescreening

**Final Pass Rate**: 94.7% (7,863/8,303)

| # | Field | Pass Rate | Status | Notes |
|---|-------|-----------|--------|-------|
| 1 | `split` | 100% | ✅ | All "train" (single split) |
| 2 | `capture_method` | 100% | ✅ | All BORN_DIGITAL |
| 3 | `domain_level1` | 100% | ✅ | 5 codes: GOV, FIN, TEC, EDU, MED |
| 4 | `iso639_language` | 96.34% | ⚠️ | 304 undetermined (minimal text) |
| 5 | `script_family` | 100% | ✅ | latin, cjk, other |
| 6 | `content_flags` | 100% | ✅ | Docling layout extraction |
| 7 | `layout_detections` | 97.65% | ⚠️ | 195 pages missing layout |
| 8 | `layout_bbox_valid` | 99.14% | ⚠️ | 71 pages malformed bboxes |
| 9 | `orientation` | 100% | ✅ | All portrait |
| 10 | `color_mode` | 100% | ✅ | All RGB |
| 11 | `handwriting` | 100% | ✅ | All false (born-digital) |
| 12 | `text_has_content` | 99.87% | ✅ | 11 pages minimal text |
| 13 | `text_direction` | 100% | ✅ | 96.3% LTR |
| 14 | `text_directions_present` | 100% | ✅ | All populated |
| 15 | `quality_overall_mos` | 100% | ✅ | N/A (no MOS) |

---

## Phase 2: Schema Compliance

**Result**: 100% validity across all fields present. Many fields at 0% coverage (expected -- not all enrichments run).

---

## Phase 3: Multi-Source Comparison

**Sources Discovered**: 3 (docling_layout, l2_metadata, language_enrichment)
**Audit Samples**: 18,351

---

## Phase 4: Defect Catalog

7 defects identified:

| ID | Severity | Description | Resolution |
|----|----------|-------------|------------|
| D01 | CRITICAL | All splits "unknown" | **FIXED**: Hardcoded "train" (HF has no split column) |
| D02 | CRITICAL | Language enrichment truncated (1,000/8,259) | **MITIGATED**: HF GT character script fallback |
| D03 | HIGH | 195 pages missing layout (2.35%) | **ACCEPTED**: Docling GPU extraction gap |
| D04 | HIGH | 71 invalid bboxes (0.86%) | **ACCEPTED**: Layout parsing edge cases |
| D05 | MEDIUM | 11 pages no text content (0.13%) | **ACCEPTED**: Minimal text pages |
| D06 | MEDIUM | Layout batch ID collision across COCO files | **FIXED**: Per-batch processing |
| D07 | LOW | Domain mapping used wrong subdirectory names | **FIXED**: Updated mapping |

**Resolved**: 4/7 | **Accepted**: 3/7 | **Deferred**: 0/7

---

## Phase 5: Integration Script

**Script**: `scripts/integrate_ohr_bench_enrichments.py` (1,206 lines)

### Iteration History

| Iteration | Pass Rate | Key Fix |
|-----------|-----------|---------|
| 1 | 0% | Initial run -- layout matched 0 (batch ID collision) |
| 2 | ~60% | Fixed per-batch processing, DUDE single-page files |
| 3 | ~87% | Fixed domain mapping, split to "train" |
| 4 | 94.7% | Added HF GT language fallback for truncated OpenLID |

### Critical Bug: COCO Batch ID Collision

All 7 Docling layout batch files use overlapping `image_id` ranges (0-199). Loading into a single dict caused batch_6 (61 docs) to overwrite all previous batches. Fix: process each batch independently with per-batch `batch_id_to_docname` mapping.

---

## Phase 6: VLM Inspection

**Status**: COMPLETE
**Method**: Contact sheet batch review (4 sheets x 9 images, 3x3 grid @ 500px) + individual image deep inspection (28/36 read individually)
**Inspector**: claude-opus-4-6
**Date**: 2026-02-13

### VLM Accuracy: 94.4% (34/36 fully correct)

| Field | Correct | Incorrect | Accuracy |
|-------|---------|-----------|----------|
| `iso639_language` | 36 | 0 | 100% |
| `script_family` | 36 | 0 | 100% |
| `domain_level1` | 36 | 0 | 100% |
| `orientation` | 36 | 0 | 100% |
| `capture_method` | 34 | 2 flagged | 94.4% |
| `has_handwriting` | 34 | 2 | 94.4% |

### Corrections Applied

| ID | File | Field | Old | New | Confidence |
|----|------|-------|-----|-----|------------|
| C01 | GNHK_eng_EU_115.png | has_handwriting | false | true | High |
| C02 | GNHK_eng_EU_283.png | has_handwriting | false | true | High |

### Content Flag Distribution (36 samples)

| Flag | Count | Pct |
|------|-------|-----|
| has_table | 10 | 27.8% |
| has_figure | 7 | 19.4% |
| has_formula | 1 | 2.8% |
| has_handwriting | 2 | 5.6% |
| has_code | 0 | 0.0% |

### Key Observations

- **No Chinese text** in 36-sample set (dataset is 94.2% English; Chinese 5.8% not represented in domain-stratified sample)
- **2 GNHK samples** are photographed handwritten cards embedded in PDFs (capture_method flagged but not corrected since PDF container is born_digital)
- **2 additional samples** appear to contain scanned typewritten content (1986 memo, old index) but are embedded in born-digital PDFs
- All domain assignments match OHR-Bench subdirectory mapping; 3 borderline cases noted but accepted

**Grade cap removed**: VLM accuracy 94.4% exceeds 90% threshold.

---

## Phase 7: Corrections & Iteration

All corrections applied during Phase 5 iteration. Final state:

- Split: 100% "train"
- Domain: 5 standardized codes, 0% UNK
- Language: 96.3% detected (OpenLID + HF GT fallback)
- Layout: 97.7% coverage
- Enrichment version: integrated_v2

---

## Phase 8: Documentation

Source doc rewritten from 4/12 sections to 12/12 (all template sections).
Scorecard doc_completeness: 100% (11/11 keywords matched).

---

## Phase 9: Scorecard

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Field Coverage | 99.5 | 0.25 | 24.88 |
| Field Validity | 91.5 | 0.25 | 22.89 |
| Doc Completeness | 100.0 | 0.15 | 15.00 |
| Defect Rate | 86.0 | 0.15 | 12.90 |
| Cross Source Agreement | 0.0 | 0.10 | 0.00 |
| VLM Accuracy | 94.4 | 0.10 | 9.44 |
| **Total** | **85.1** | **1.00** | **85.11** |

**Grade**: B (85.1/100) -- VLM inspection completed, cap removed

---

## Phase 10: Lessons Learned

### Key Findings

1. **COCO batch ID collision**: Multiple COCO JSON files from Docling GPU extraction use overlapping `image_id` ranges. Must process each batch independently. This is a potential cross-dataset issue for any dataset with multi-batch Docling extraction.

2. **Language enrichment truncation**: The OpenLID language enrichment file was truncated to 1,000/8,259 records. Root cause unknown. Mitigated with HF ground truth character script analysis as fallback.

3. **HF dataset split claims unreliable**: Documentation claimed train/val/test splits existed but HuggingFace `datasets` library confirmed all 8,561 pages are in a single "train" split with no split column. Always verify split claims programmatically.

4. **Domain mapping fragility**: Documentation domain names ("government", "newspaper") didn't match actual path subdirectories ("administration", "news"). Verify mappings against actual data paths.

5. **Single-page document ID format**: 515 DUDE-format files use `DUDE_{hash}.png` without `_pNNN` suffix. Integration scripts must handle both formats.

### Process Improvements

- Consider adding a KI-010 for COCO batch ID collision risk
- Language enrichment pipeline should validate record counts match metadata counts
- Scorecard doc_completeness keyword matching requires content between heading and sub-heading -- add brief description after every `####` heading

### v2.3.0 Field Coverage

| Field | Populated | Notes |
|-------|-----------|-------|
| `text_direction` | 96.3% (ltr) | Populated for pages with detected language |
| `text_directions_present` | 100% | Populated for all pages |
| `character_height_rendered_px` | N/A | Synthetic-only field |
| `output_size_px` | N/A | Derived view field |
