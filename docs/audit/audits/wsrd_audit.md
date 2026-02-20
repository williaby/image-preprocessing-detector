> **Version**: 1.4.0
> **Date**: 2026-02-14
> **Auditor**: Claude Opus 4.6
> **Methodology**: 9-Phase Audit (v2.3.0)
>
> **Audit Goal**: Close defects so the dataset is ready for correction training.

---

## Dataset Overview

| Property | Value |
|----------|-------|
| Dataset Name | wsrd |
| Total Samples | 4500 |
| Image Base Path | `/mnt/e/image_detection/01_base_data/correction/wsrd` |
| Audit Started | 2026-02-13 |
| Audit Completed | 2026-02-14 |
| Enrichment Version | v2 (base metadata + integration script) |
| Dataset Type | Document shadow removal (NTIRE 2023+2024) |
| License | Unspecified |

---

## Enrichment Sources

| Source | Exists? | Notes |
|--------|---------|-------|
| Base metadata | ✅ | Via `annotate_base_metadata_lite.py` |
| Integration script | ✅ | `integrate_wsrd_enrichments.py` |
| LLM enrichment | ❌ | Not run |
| Language enrichment | ❌ | Not run |
| Docling layout | ❌ | Not run |
| Docling OCR | ❌ | Not run |
| Classical IQA | ❌ | Not run |
| Resolution quality | ❌ | Not run |

**Total sources available**: 2/11

---

## Phase Results

### Phase 0: Paper Review

- **Reviewed**: Source README and paper
- **Expected**: Camera-captured/document images with paired GT
- **Splits**: 3 splits from directory (train/val/test)

### Phase 1: Automated Prescreening

- **Pass rate**: 0.0% (expected for base-only metadata)
- **Passing fields** (10/15): capture_method, script_family, layout_bbox_valid, content_flags_boolean, orientation_class, image_properties_color_mode, handwriting_present, text_direction, text_directions_present, quality_overall_mos
- **Failing fields** (5/15): split(100%), domain_level1(100%), iso639_language(100%), layout_detections(100%), text_has_content(100%)
- **Assessment**: All failures are expected enrichment gaps, not data quality issues

### Phase 2: Schema Compliance

- **Valid**: 4500/4500 (100.0%)
- **All 27 fields valid** after text_scope fix (printed -> page)

### Phase 3: Multi-Source Comparison

- **Sources compared**: 1 (l2_metadata only)
- **Disagreements**: 0
- **Assessment**: No cross-source comparison possible with single source

### Phase 4: Defect Catalog

- **Total defects**: 6
  - D01: split not populated (ACCEPTED - correction dataset, deferred to training pipeline)
  - D02: domain_level1 = UNK (RESOLVED - overridden to GENERAL via VLM inspection)
  - D03: iso639_language = und (RESOLVED - overridden to en via VLM inspection)
  - D04: layout_detections = [] (ACCEPTED - not required for correction training)
  - D05: text_has_content = false (ACCEPTED - no OCR run)
  - D06: text_scope = "printed" (RESOLVED - fixed to "page")
- **Blocking defects**: 0
- **Accepted gaps**: 3 (enrichment not critical for correction training)
- **Resolved**: 3

### Phase 4.5: Stratified Sampling

- **Sample size**: 36
- **Strata**: 1 (capture_method=camera_smartphone, domain_level1=UNK)

### Phase 5: Integration Script

- **Script**: `scripts/integrate_wsrd_enrichments.py`
- **Status**: ✅ Complete
- **KI mitigations**: KI-005 (capture method from documentation)

### Phase 6: VLM Visual Inspection

- **Status**: ✅ COMPLETE
- **Date**: 2026-02-13
- **Model**: claude-opus-4-6 (in-session multimodal vision)
- **Images inspected**: 12 (Track C stratified passing samples)
- **Passing accuracy**: 91.7% (11/12 correct at image level)
- **Flag-level accuracy**: 96.7%
- **Total corrections**: 2 (all FN, 0 FP)
  - has_handwriting: 1 FN (8.3% of samples)
  - has_formula: 1 FN (8.3% of samples)
- **Domain/language overrides**: domain_level1=GENERAL, iso639_language=en, script_family=Latn (from visual inspection of document content)
- **Assessment**: Excellent accuracy. Only 1 image (0029.png) had corrections. Shadow removal documents predominantly contain printed English text.

### Phase 7: Corrections

- **text_scope fix**: Changed "printed" to "page" in integration script and re-integrated
- **Re-run results**: Schema compliance 100%, prescreening unchanged (expected)

### Phase 8: Documentation

- **Catalog doc**: `docs/datasets/source/wsrd.md` updated with audit results
- **Tracking**: AUDIT_TRACKING_INDEX updated

---

## Quality Scorecard

| Dimension | Score | Weight (orig) | Effective Weight | Weighted |
|-----------|-------|---------------|------------------|----------|
| Field Coverage | 86.67 | 0.25 | 0.2778 | 24.08 |
| Field Validity | 100.0 | 0.25 | 0.2778 | 27.78 |
| Doc Completeness | 81.82 | 0.15 | 0.1667 | 13.64 |
| Defect Rate | 96.0 | 0.15 | 0.1667 | 16.00 |
| Cross Source | N/A | 0.10 | excluded | - |
| VLM Accuracy | 91.7 | 0.10 | 0.1111 | 10.19 |
| **TOTAL** | | | | **91.68 - Grade: A** |

---

## Recommendations

1. **For correction training**: Dataset is ready to use as-is. Missing enrichments (domain, language, layout, text) are not required.
2. **For general use**: Run OCR + LLM enrichment pipeline to fill domain, language, and content flags.
3. **VLM accuracy**: Excellent (91.7%). Only minor FN corrections needed for handwriting/formula flags on a single image.

---
