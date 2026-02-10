# Layer 2 Enrichment Audit Report: {DATASET_NAME}

> **Audited**: {AUDIT_DATE}
> **Schema Version**: {SCHEMA_VERSION} (`layer2_enrichment_v2.schema.json`)
> **Auditor**: {AUDITOR_NAME}
> **Methodology**: [scripts/audit/README.md](../README.md)

---

## 1. Dataset Overview

| Property | Value |
|----------|-------|
| Dataset | {DATASET_NAME} |
| Total Samples | {TOTAL_SAMPLES} |
| Samples Audited | {AUDITED_SAMPLES} |
| Enrichment Date | {ENRICHMENT_DATE} |
| Enrichment Script | {ENRICHMENT_SCRIPT} |
| Metadata JSON Path | `{METADATA_JSON_PATH}` |
| Image Base Path | `{IMAGE_BASE_PATH}` |

### Enrichment Sources Used

| Source | Path | Records |
|--------|------|---------|
| Base metadata | `{METADATA_JSON_PATH}` | {BASE_RECORDS} |
| LLM enrichment | `{LLM_ENRICHMENT_PATH}` | {LLM_RECORDS} |
| Language enrichment | `{LANGUAGE_ENRICHMENT_PATH}` | {LANG_RECORDS} |
| Docling layout | `{DOCLING_LAYOUT_PATH}` | {LAYOUT_RECORDS} |
| Docling OCR | `{DOCLING_OCR_PATH}` | {OCR_RECORDS} |

---

## 2. Executive Summary

| Metric | Value |
|--------|-------|
| Overall Compliance Rate | {COMPLIANCE_RATE}% |
| Fields with 100% Coverage | {FULL_COVERAGE_FIELDS} / {TOTAL_FIELDS} |
| Fields with 100% Validity | {FULL_VALIDITY_FIELDS} / {TOTAL_FIELDS} |
| Total Defects Found | {TOTAL_DEFECTS} |
| Consistency Defects | {CONSISTENCY_DEFECTS} |
| Samples with Zero Defects | {CLEAN_SAMPLES} / {AUDITED_SAMPLES} |

### Defect Severity Distribution

| Severity | Count | % of Total |
|----------|-------|-----------|
| Critical (wrong_value, missing_value) | {CRITICAL_COUNT} | {CRITICAL_PCT}% |
| High (wrong_format, wrong_enum) | {HIGH_COUNT} | {HIGH_PCT}% |
| Medium (inconsistent) | {MEDIUM_COUNT} | {MEDIUM_PCT}% |
| Low (not_populated) | {LOW_COUNT} | {LOW_PCT}% |

---

## 3. Defect Catalog

<!-- Sort by affected_count descending -->

| # | Field | Defect Type | Affected Count | Root Cause | Fix Category |
|---|-------|-------------|---------------|------------|--------------|
| 1 | {FIELD_1} | {DEFECT_TYPE_1} | {COUNT_1} | {ROOT_CAUSE_1} | {FIX_CAT_1} |
| 2 | {FIELD_2} | {DEFECT_TYPE_2} | {COUNT_2} | {ROOT_CAUSE_2} | {FIX_CAT_2} |

### Defect Types Reference

| Code | Description | Typical Root Cause |
|------|-------------|-------------------|
| `wrong_value` | Value exists but is factually incorrect | Model mislabel, stale heuristic |
| `missing_value` | Required field is absent (null/missing key) | Parser gap, script bug |
| `wrong_format` | Value present but wrong type or structure | Type coercion error, schema drift |
| `wrong_enum` | Value not in allowed enum set | Unmapped label, typo |
| `inconsistent` | Cross-field contradiction (e.g. layout vs flag) | Pipeline ordering, partial update |
| `not_populated` | Optional field not populated (coverage gap) | Feature not yet implemented |

### Fix Categories

| Category | Description |
|----------|-------------|
| `parser_fix` | Fix in annotation parser (`src/.../parsers/`) |
| `enrichment_fix` | Fix in enrichment script (`scripts/annotate_*.py`) |
| `schema_fix` | Schema definition needs updating |
| `backfill` | Rerun enrichment with corrected logic |
| `manual_review` | Requires human review of individual samples |
| `deferred` | Low priority, acceptable for current phase |

---

## 4. Source Comparison Matrix

<!-- For each audited sample, compare values from different enrichment sources.
     Fill one row per sample, one column per source. -->

| Sample ID | Field | Base Metadata | LLM Enrichment | Language Enrichment | Docling Layout | Visual Inspection | Verdict |
|-----------|-------|---------------|----------------|---------------------|----------------|-------------------|---------|
| {SID_1} | capture_method | {BASE_CM_1} | {LLM_CM_1} | -- | -- | {VISUAL_CM_1} | {VERDICT_1} |
| {SID_1} | domain_level1 | {BASE_DM_1} | {LLM_DM_1} | -- | -- | {VISUAL_DM_1} | {VERDICT_2} |

### Verdict Legend

- **CORRECT**: All sources agree and match visual inspection.
- **WRONG_SOURCE**: Base metadata is wrong; another source is correct.
- **ALL_WRONG**: No source matches ground truth.
- **AMBIGUOUS**: Reasonable disagreement; needs expert adjudication.

---

## 5. Per-Field Accuracy Analysis

### Coverage and Validity Summary

| Field | Coverage | Validity | Defect Types | Notes |
|-------|----------|----------|-------------|-------|
| `capture_method` | {CM_COVERAGE}% | {CM_VALIDITY}% | {CM_DEFECTS} | |
| `capture_confidence` | {CC_COVERAGE}% | {CC_VALIDITY}% | {CC_DEFECTS} | |
| `resolution_category` | {RC_COVERAGE}% | {RC_VALIDITY}% | {RC_DEFECTS} | |
| `resolution_pixels` | {RP_COVERAGE}% | {RP_VALIDITY}% | {RP_DEFECTS} | |
| `domain_level1` | {DL_COVERAGE}% | {DL_VALIDITY}% | {DL_DEFECTS} | |
| `domain_confidence` | {DC_COVERAGE}% | {DC_VALIDITY}% | {DC_DEFECTS} | |
| `iso639_language` | {LANG_COVERAGE}% | {LANG_VALIDITY}% | {LANG_DEFECTS} | |
| `iso15924_script` | {SCRIPT_COVERAGE}% | {SCRIPT_VALIDITY}% | {SCRIPT_DEFECTS} | |
| `script_family` | {SF_COVERAGE}% | {SF_VALIDITY}% | {SF_DEFECTS} | |
| `text_scope` | {TS_COVERAGE}% | {TS_VALIDITY}% | {TS_DEFECTS} | |
| `content_flags.has_table` | {HT_COVERAGE}% | {HT_VALIDITY}% | {HT_DEFECTS} | |
| `content_flags.has_formula` | {HF_COVERAGE}% | {HF_VALIDITY}% | {HF_DEFECTS} | |
| `content_flags.has_handwriting` | {HH_COVERAGE}% | {HH_VALIDITY}% | {HH_DEFECTS} | |
| `content_flags.has_figure` | {HFG_COVERAGE}% | {HFG_VALIDITY}% | {HFG_DEFECTS} | |
| `layout_detections` | {LD_COVERAGE}% | {LD_VALIDITY}% | {LD_DEFECTS} | |
| `quality_overall_score` | {QOS_COVERAGE}% | {QOS_VALIDITY}% | {QOS_DEFECTS} | |
| `llm_scores.predicted_mos` | {MOS_COVERAGE}% | {MOS_VALIDITY}% | {MOS_DEFECTS} | |
| `sample_reliability_summary` | {SRS_COVERAGE}% | {SRS_VALIDITY}% | {SRS_DEFECTS} | |

### Detailed Field Notes

<!-- Add field-specific observations here. Delete rows that are not applicable. -->

**capture_method**: {CAPTURE_METHOD_NOTES}

**domain_level1**: {DOMAIN_NOTES}

**layout_detections**: {LAYOUT_NOTES}

**content_flags**: {CONTENT_FLAGS_NOTES}

---

## 6. Pipeline Fix Recommendations

<!-- Prioritize by impact (affected_count * severity). -->

### Priority 1 (Critical)

| # | Fix Description | Affected Samples | Fix Location | Estimated Effort |
|---|----------------|-----------------|--------------|-----------------|
| 1 | {FIX_DESC_1} | {FIX_COUNT_1} | `{FIX_LOCATION_1}` | {FIX_EFFORT_1} |

### Priority 2 (High)

| # | Fix Description | Affected Samples | Fix Location | Estimated Effort |
|---|----------------|-----------------|--------------|-----------------|
| 1 | {FIX_DESC_2} | {FIX_COUNT_2} | `{FIX_LOCATION_2}` | {FIX_EFFORT_2} |

### Priority 3 (Medium/Low)

| # | Fix Description | Affected Samples | Fix Location | Estimated Effort |
|---|----------------|-----------------|--------------|-----------------|
| 1 | {FIX_DESC_3} | {FIX_COUNT_3} | `{FIX_LOCATION_3}` | {FIX_EFFORT_3} |

---

## 7. Cross-Dataset Extrapolation Notes

### Applicability to Other Datasets

<!-- Which findings from this audit are likely to affect other datasets?
     This section enables efficient auditing of subsequent datasets. -->

| Finding | Likely Affects | Reason |
|---------|---------------|--------|
| {FINDING_1} | {DATASETS_1} | {REASON_1} |
| {FINDING_2} | {DATASETS_2} | {REASON_2} |

### Known Shared Pipeline Components

| Component | Datasets Using It | Defect Risk |
|-----------|------------------|-------------|
| `annotate_base_metadata.py` | All 51 datasets | {RISK_1} |
| `enrich_language.py` | Datasets with language enrichment | {RISK_2} |
| `enrich_metadata_from_llm.py` | Datasets with LLM enrichment | {RISK_3} |
| `standardize_layout_labels.py` | Datasets with layout detections | {RISK_4} |

### Datasets Recommended for Next Audit

<!-- Based on findings, which datasets should be audited next? -->

1. **{NEXT_DATASET_1}** -- {NEXT_REASON_1}
2. **{NEXT_DATASET_2}** -- {NEXT_REASON_2}

---

## 8. Appendix

### A. Audit Sample Selection

| Sample ID | Stratification Bucket | Image Path |
|-----------|----------------------|------------|
| {ASID_1} | {BUCKET_1} | `{AIMG_1}` |

### B. Raw Compliance Report

Full JSON report: `{REPORT_JSON_PATH}`

Generated by `scripts/audit/audit_schema_compliance.py`.

### C. Schema Reference

Schema: `docs/schema/layer2_enrichment_v2.schema.json` (v2.1.0)

Documentation: `docs/schema/layer2_enrichment_schema.md`
