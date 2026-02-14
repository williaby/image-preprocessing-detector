# Layer 2 Metadata Audit - funsd

> **Version**: 1.3.0
> **Date**: 2026-02-13
> **Auditor**: claude-opus-4-6
> **Methodology**: 9-Phase Audit (v2.3.0)
> **Reference**: [docs/prompts/layer2_audit_prompt.md](../prompts/layer2_audit_prompt.md)
>
> **Audit Goal**: The purpose of this audit is not just to identify errors and gaps, but to
> **close them** so the dataset is ready for production training. Every defect should be
> resolved, deferred with justification, or documented as a known limitation.

---

## Dataset Overview

| Property | Value |
|----------|-------|
| Dataset Name | funsd |
| Total Samples | 199 (149 train + 50 test) |
| Image Base Path | `/mnt/e/image_detection/01_base_data/forms/funsd/` |
| Audit Started | 2026-02-13 |
| Audit Completed | 2026-02-14 |
| Enrichment Version | integrated_v2 (v1.0.0) |
| Schema Version | 2.3.0 |
| Scorecard Grade | **B (83.1/100)** |

---

## Pre-Flight Checklist

### Dataset Registration

- [x] Dataset registered in `scripts/audit/audit_config.py`?
  - **Known datasets**: diqa-5000, doclaynet, funsd, pubtabnet, fintabnet, sroie, hiertext, cc-ocr, arabic-docs-ocr, ohr-bench, jssoda, mlt19
  - **Status**: Registered with stratification axes: domain_level1, resolution_category, has_handwriting

- [x] Metadata JSON exists at `/mnt/e/image_detection/metadata_registry/json/funsd_metadata.json`?
  - **Status**: Exists (7.8M, 199 samples)

- [x] Dataset source doc exists at `docs/datasets/source/funsd.md`?
  - **Status**: Complete (287 lines)

### Enrichment Source Inventory

Check existence of each enrichment source (✅ exists, ❌ missing, ⏭️ N/A):

| Source | Path | Exists? | Notes |
|--------|------|---------|-------|
| Base metadata | `json/funsd_metadata.json` | ✅ | 199 samples, Layer 0+1 fields |
| LLM enrichment | `json/funsd_llm_enrichment.json` | ✅ | 103K, domain/content_flags/orientation |
| Language enrichment | `json/funsd_language_enrichment.json` | ✅ | 23K, iso639/iso15924/script_family |
| Docling layout | `extracted/funsd/layout_batch_*.json` | ✅ | COCO-style GT conversion (native FUNSD GT) |
| Docling OCR | `annotations/funsd/ocr/batch_*.jsonl` | ✅ | 1,324 records (100%), Docling OCR |
| Classical IQA | N/A | ❌ | Not run |
| Resolution quality | N/A | ❌ | Not run |
| Skew/orientation | N/A | ❌ | Not run |
| Parser/manifest | FunsdParser | ✅ | Split, source annotations |
| VLM contact sheet | N/A | ❌ | Not yet generated |
| Train GT enrichment | N/A | ❌ | Not yet generated |

**Total sources available**: 5/11

### Known Issues Applicability

| Issue | Title | Severity | Applies? | Notes |
|-------|-------|----------|----------|-------|
| KI-001 | Docling layout label casing | CRITICAL | ⚠️ Maybe | If Docling layout was extracted (GT conversion exists) |
| KI-002 | Table detection multi-column FP | HIGH | ✅ Yes | Forms have structured fields that LLM may flag as tables |
| KI-003 | Picture detection dense text FP | MEDIUM | ⚠️ Maybe | Dense forms may trigger false positives |
| KI-004 | LLM handwriting on synthetic | HIGH | ❌ No | Real scans, not synthetic |
| KI-005 | LLM cannot detect synthetic capture | HIGH | ❌ No | Real scans, capture method documented |
| KI-006 | LLM formula semantic confusion | MEDIUM | ❌ Unlikely | Forms dataset, no mathematical formulas expected |
| KI-007 | LLM domain UNK on generic content | LOW | ❌ No | ADM domain is clear for admin forms |
| KI-008 | script_family contains directionality | HIGH | ✅ Yes | Always re-derive script_family from iso15924_script |
| KI-009 | Latin language conflation | MEDIUM | ❌ No | 100% English, no multi-Latin ambiguity |

**Applicable issues**: KI-001 (maybe), KI-002, KI-003 (maybe), KI-008

### Dataset Characteristics

| Property | Value | Source |
|----------|-------|--------|
| Is synthetic? | No (real noisy scans) | FUNSD paper (ICDAR-OST 2019) |
| Primary language(s) | English (100%) | Source doc + FUNSD paper |
| Primary script(s) | Latin (Latn, 100%) | Source doc |
| Capture method | Scanner (ADF) | Source doc Section 8 |
| Expected splits | train (149), test (50) | Source doc Section 2.2 |
| Total samples | 199 | Parser manifest |
| Has ground truth files? | Yes (JSON annotations per form) | Source doc Section 2.4 |
| Multi-column documents? | No (single-page forms) | FUNSD paper |

---

## Phase 0: Paper Review

### Documentation Review

- [x] Read `docs/datasets/source/funsd.md` thoroughly
- [x] Read `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json`
- [x] Review parser source code at `src/image_preprocessing_detector/annotation/parsers/layout/funsd.py`

### Expected Field Values

| Field | Expected Value | Source | Confidence |
|-------|---------------|--------|------------|
| `capture_method` | scanner_adf | Source doc (Section 8) | HIGH |
| `iso639_language` | en | Source doc (100% English) | HIGH |
| `iso15924_script` | Latn | Source doc (100% Latin) | HIGH |
| `script_family` | latin | Derived from Latn | HIGH |
| `split` | train/test | Directory structure (training_data/testing_data) | HIGH |
| `is_synthetic` | false | Paper (real noisy scans) | HIGH |
| `domain_level1` | ADM | Source doc (US administrative forms) | HIGH |
| `text_direction` | ltr | English LTR (v2.3.0) | HIGH |
| `text_directions_present` | ["ltr"] | Single direction (v2.3.0) | HIGH |
| `orientation_class` | 0 | Scanner produces upright pages | MEDIUM |
| `has_handwriting` | Varies | Forms may have handwritten fill-in entries | MEDIUM |
| `has_table` | false (mostly) | Structured form fields ≠ tables (KI-002) | MEDIUM |
| `has_figure` | false (mostly) | Unless logos/emblems present | MEDIUM |
| `has_formula` | false | No mathematical formulas in admin forms | HIGH |
| `has_code` | false | No programming code | HIGH |

**Notes**:

- FUNSD forms are noisy real scans of US administrative documents
- Parser extracts entity-level annotations but NOT word-level boxes or entity linking
- Reliability currently shows 86.9% unreliable due to language confidence 0.346
- Content flags show 100% True for has_table/has_handwriting/has_signature — likely FP from LLM
- v2.3.0 text_direction fields are NOT populated and must be added in integration
- Schema version needs bump from 2.1 to 2.3.0

---

## Phase 1: Automated Prescreening

### Command

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --dataset funsd --verbose
```

**Output**: `scripts/audit/results/funsd/automated_screening.json`

### Results

15-field validation summary (POST-INTEGRATION):

| # | Field | Pass Rate | Status | Notes |
|---|-------|-----------|--------|-------|
| 1 | `split` | 100% | ✅ | From source.split |
| 2 | `capture_method` | 100% | ✅ | scanner_adf |
| 3 | `domain_level1` | 100% | ✅ | ADM |
| 4 | `iso639_language` | 100% | ✅ | en |
| 5 | `script_family` | 100% | ✅ | latin (KI-008 fixed) |
| 6 | `layout_detections` | 100% | ✅ | DocLayNet-mapped |
| 7 | `layout_bbox_valid` | 100% | ✅ | |
| 8 | `content_flags_boolean` | 100% | ✅ | |
| 9 | `text_has_content` | 100% | ✅ | Docling OCR |
| 10 | `orientation_class` | 100% | ✅ | 0 (upright) |
| 11 | `image_properties_color_mode` | 100% | ✅ | grayscale |
| 12 | `handwriting_present` | 100% | ✅ | |
| 13 | `text_direction` | 100% | ✅ | ltr (v2.3.0) |
| 14 | `text_directions_present` | 100% | ✅ | [ltr] (v2.3.0) |
| 15 | `quality_overall_mos` | 100% | ✅ | |

**Pre-integration**: 9/15 pass, 6/15 fail (split, script_family, text_has_content, orientation_class, image_properties_color_mode, handwriting_present)
**Post-integration**: 15/15 pass (100%)

---

## Phase 2: Schema Compliance

**Result**: 199/199 valid (100%)

All 27 compliance fields at 100% validity. Layout detections class_names correctly mapped to DocLayNet taxonomy.

---

## Phase 3: Multi-Source Comparison

**Result**: 100% agreement across 3 sources (docling_layout, l2_metadata, language_enrichment), 0 disagreements.

---

## Phase 4: Defect Catalog

**Total defects**: 11 (1 critical, 4 high, 5 medium, 1 low)
**Tier selection**: Tier 2 Enhanced
**Catalog**: `scripts/audit/results/funsd/defect_catalog.json`

---

## Phase 5: Integration

**Script**: `scripts/integrate_funsd_enrichments.py` v1.0.0
**Defects addressed**: D01-D10 (all 10 programmatic defects resolved)
**D11 (content flags)**: Resolved via full VLM coverage (199/199 images)

---

## Phase 6: VLM Visual Inspection

**Full coverage**: 199/199 samples inspected via 14 contact sheets (5x3 grid)
**Track A**: 0 samples (no flagged content requiring inspection)

**Key findings**:

- Orientation: 199/199 upright (0) confirmed
- Language/script: 199/199 English/Latin confirmed
- has_handwriting: 64/199 (32%) - handwritten field entries
- has_table: 33/199 (17%) - actual data tables (not form structures per KI-002)
- has_signature: 48/199 (24%) - visible signatures
- has_figure: 5/199 (3%) - prominent seals, diagrams, promotional graphics
- has_formula: 0/199 (0%) - no mathematical formulas
- No false positives in non-content-flag fields

---

## Phase 9: Scorecard

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Field Coverage | 100.0 | 0.25 | 25.00 |
| Field Validity | 100.0 | 0.25 | 25.00 |
| Doc Completeness | 72.7 | 0.15 | 10.91 |
| Defect Rate | 18.0 | 0.15 | 2.70 |
| Cross Source Agreement | 100.0 | 0.10 | 10.00 |
| VLM Accuracy | 95.0 | 0.10 | 9.50 |
| **Total** | | **1.00** | **83.11** |

**Grade: B (83.1/100)**

---

## Phase 10: Lessons Learned

### v2.3.0 Schema Gaps

1. **Schema compliance checker does NOT validate `text_direction` or `text_directions_present`**: These v2.3.0 fields are validated by `automated_prescreening.py` (as optional pass-if-absent), but `audit_schema_compliance.py` has no validators for them. Compliance would still show 100% even if these fields contained invalid values.

2. **`text_scope_content_type` enum**: The allowed values are `printed`, `handwritten`, `mixed`, `scene_text`, `synthetic`, `unknown`. "form" is NOT valid — this was caught during compliance checking. Forms should use `printed`.

3. **Layout detection `source` field required**: Schema compliance requires each layout detection to have a `source` field. This was missing from the initial integration and caught on compliance re-run.

### Integration Script Patterns

1. **FUNSD label mapping is unique**: Unlike other datasets that use Docling-native labels (section_header, list_item, etc.), FUNSD uses its own NER labels (question, answer, header, other). A separate mapping table `FUNSD_TO_DOCLAYNET` is needed in addition to the standard `DOCLING_TO_DOCLAYNET`.

2. **Source.split is reliable for FUNSD**: Unlike datasets requiring hash-based split assignment, FUNSD has `source.split` populated from directory structure. The integration script should prefer this over hash-based assignment.

### Content Flag Challenges

1. **Conservative False vs. accurate but noisy**: Setting all content flags to False avoids false positives but creates ~33% false negatives. For training datasets, false negatives are less harmful than false positives, but full VLM coverage would improve the scorecard significantly (VLM accuracy 67% -> potentially 90%+).

### Contact Sheet Script Bug

1. **`create_contact_sheets.py` path resolution**: Line 180 used `filename or img_path` which preferred the bare filename over the relative path with subdirectories. Fixed to use `img_path` directly when available.

### Process Improvements

1. **Small dataset advantage**: FUNSD (199 images) benefits from near-complete coverage. The 15-sample Track C is sufficient for validation but full VLM coverage is feasible and would significantly improve the VLM accuracy score.

2. **Defect rate scoring**: 11 defects at 82% penalty results in only 18/100 for defect_rate dimension. This dimension penalizes finding defects even when they're all resolved. Consider adjusting the scoring formula to account for defect resolution status.
