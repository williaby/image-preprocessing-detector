# Layer 2 Metadata Audit Tracking Index

> **Version**: 1.0.0
> **Last Updated**: 2026-02-12
> **Purpose**: Central dashboard for tracking Layer 2 metadata audit progress across all datasets
> **Related Documentation**:
>
> - [Layer 2 Audit Methodology](../prompts/layer2_audit_prompt.md)
> - [Audit Execution Template](../audit/AUDIT_EXECUTION_TEMPLATE.md)
> - [Audit Report Template](../audit/AUDIT_REPORT_TEMPLATE.md)
> - [Cross-Dataset Known Issues](../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json)

---

## Summary Statistics

| Metric | Count | Percentage | Progress Bar |
|--------|-------|------------|--------------|
| **Total Datasets** | 51 | 100% | ████████████████████ 100% |
| **Audits Complete** | 3 | 5.9% | █░░░░░░░░░░░░░░░░░░░ 6% |
| **Audits In Progress** | 0 | 0% | ░░░░░░░░░░░░░░░░░░░░ 0% |
| **Not Started** | 48 | 94.1% | ░░░░░░░░░░░░░░░░░░░░ 0% |
| **Audit Config Registered** | 12 | 23.5% | █████░░░░░░░░░░░░░░░ 24% |

**Key Insights**:

- Early-stage coverage: Only 3 datasets fully audited (DIQA-5000, JSSODa, MLT19)
- 7 cross-dataset known issues (KI-001 to KI-007) documented from audits so far
- 12 datasets have audit configurations ready (can run immediately)
- 39 datasets need audit configuration setup before auditing

---

## Scorecard Summary Table

<!-- SCORECARD_TABLE_START -->

| Dataset | Score | Grade | Coverage | Validity | Doc | Defects | Agreement | VLM | Updated |
|---------|-------|-------|----------|----------|-----|---------|-----------|-----|---------|
| realdae | 88.9 | B | 99 | 93 | 64 | 91 | - | - | 2026-02-12 |

<!-- SCORECARD_TABLE_END -->

**Note**: Scores will be populated by running:

```bash
python scripts/audit/compute_scorecard.py --all-datasets --update-index
```

**Current Status**: Defect catalogs exist but automated scorecard computation not yet run.

---

## Full Dataset Audit Status

### Tier 1: Training-Critical Datasets

Datasets directly used for SigLIP 2 / MobileNetV4 / YOLOv10-doc training.

| Dataset | Status | Last Audit | Samples | Config Registered | Top Issue / Note |
|---------|--------|------------|---------|-------------------|------------------|
| **diqa-5000** | ✅ Complete | 2026-02-10 | 5,500 | Yes | 18 defects found, mostly pipeline bugs (bbox format, script_family enum) |
| **jssoda** | ✅ Complete | 2026-02-11 | 2,000 | Yes | 12 defects, 9 resolved via integration script, VLM-verified content flags |
| **mlt19** | ✅ Complete | 2026-02-12 | 19,657 | Yes | 13 defects, 10 resolved via v3 integration, VLM contact sheet script analysis |
| **ohr-bench** | ❌ Not Started | - | 8,561 | Yes | IQA training dataset, high priority |
| **doclaynet** | ❌ Not Started | - | 81,471 | Yes | Layout detection primary dataset |
| **pubtabnet** | ❌ Not Started | - | 519,030 | Yes | Table structure dataset (large) |
| **tablebank** | ❌ Not Started | - | 278,582 | ❌ No | Table detection dataset, needs config |
| **fintabnet** | ❌ Not Started | - | 97,475 | Yes | Financial table dataset |
| **synth-multiscript-250k** | ❌ Not Started | - | 250,000 (generating) | ❌ No | Synthetic script detection dataset, generation in progress |
| **realdae** | ❌ Not Started | - | 1,200 | ❌ No | IQA before/after pairs |
| **hiertext** | ❌ Not Started | - | 11,641 | Yes | Handwriting legibility gold standard |

---

### Tier 2: Validation & Supplementary Datasets

Secondary datasets providing diversity, validation, or augmentation.

| Dataset | Status | Last Audit | Samples | Config Registered | Top Issue / Note |
|---------|--------|------------|---------|-------------------|------------------|
| **funsd** | ❌ Not Started | - | 199 | Yes | Forms dataset, small sample |
| **funsd-plus** | ❌ Not Started | - | 1,139 | ❌ No | Extended FUNSD |
| **sroie** | ❌ Not Started | - | 973 | Yes | Malaysian receipts |
| **cc-ocr** | ❌ Not Started | - | 6,533 | Yes | CJK mixed scripts |
| **arabic-docs-ocr** | ❌ Not Started | - | 10,045 | Yes | Arabic documents |
| **mdiw13** | ❌ Not Started | - | 290,213 | ❌ No | Multi-script word-level dataset |
| **siw13** | ❌ Not Started | - | 16,291 | ❌ No | Script identification dataset |
| **cvsi** | ❌ Not Started | - | 10,715 | ❌ No | Video scene text |
| **mle2e** | ❌ Not Started | - | 1,816 | ❌ No | Korean/Hangul focus |
| **hindi-synth** | ❌ Not Started | - | 80,009 | ❌ No | Synthetic Devanagari |
| **pucit-ohul** | ❌ Not Started | - | 7,401 | ❌ No | Urdu handwriting |
| **yarmouk** | ❌ Not Started | - | 15,062 | ❌ No | Arabic OCR |
| **tibhcr** | ❌ Not Started | - | 141,698 | ❌ No | Tibetan handwriting |
| **dzongkha-digits** | ❌ Not Started | - | 62 | ❌ No | Tibetan digits |
| **nepali-handwritten** | ❌ Not Started | - | 958 | ❌ No | Devanagari handwriting |
| **muharaf** | ❌ Not Started | - | 25,711 | ❌ No | Arabic cursive historical |
| **iam** | ❌ Not Started | - | 130,212 | ❌ No | English handwriting corpus |
| **cocotext** | ❌ Not Started | - | 63,686 | ❌ No | Scene text with legibility labels |
| **hasy** | ❌ Not Started | - | 168,233 | ❌ No | Math symbols handwritten |

---

### Tier 3: Specialized / Low Priority Datasets

Niche, small-sample, or lower-priority datasets.

| Dataset | Status | Last Audit | Samples | Config Registered | Top Issue / Note |
|---------|--------|------------|---------|-------------------|------------------|
| **tobacco800** | ❌ Not Started | - | 1,290 | ❌ No | Archival degradation |
| **rvl-cdip** | ❌ Not Started | - | 16,000 | ❌ No | Document classification |
| **midv500** | ❌ Not Started | - | 3,612 | ❌ No | ID documents mobile capture |
| **smartdoc-qa** | ❌ Not Started | - | 4,280 | ❌ No | Mobile capture QA |
| **nist-sd2** | ❌ Not Started | - | 5,590 | ❌ No | Tax forms synthetic |
| **nist-sd6** | ❌ Not Started | - | 5,595 | ❌ No | Tax forms + handprint |
| **nist-sd19** | ❌ Not Started | - | 3,669 | ❌ No | Handwriting digits |
| **dibco** | ❌ Not Started | - | 212 | ❌ No | Binarization benchmark |
| **signatr6k** | ❌ Not Started | - | 12,514 | ❌ No | Signature detection |
| **financebench** | ❌ Not Started | - | 54,121 | ❌ No | Financial PDFs RAG QA |
| **bhutan-afs** | ❌ Not Started | - | 135 | ❌ No | Bhutan annual reports |
| **invoices-kg** | ❌ Not Started | - | 1,414 | ❌ No | Invoice images |
| **omnidocbench** | ❌ Not Started | - | 1,358 | ❌ No | Multi-task benchmark |
| **multimodal-textbook** | ❌ Not Started | - | 1,113 | ❌ No | STEM textbook pages |
| **im2latex** | ❌ Not Started | - | 10,000 | ❌ No | Math formula extraction |
| **mathverse** | ❌ Not Started | - | 6,940 | ❌ No | Math problems |
| **doc3d** | ❌ Not Started | - | 102,064 | ❌ No | Document dewarping 3D geometry |
| **docsynth** | ❌ Not Started | - | 300,000 | ❌ No | Synthetic layout dataset |
| **ocr-quality** | ❌ Not Started | - | 1,000 | ❌ No | Quality scores multilingual |

---

## Cross-Dataset Defect Summary

Summary of known issues affecting multiple datasets. See [CROSS_DATASET_KNOWN_ISSUES.json](../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json) for full details.

| Issue ID | Title | Severity | Datasets Affected | Status |
|----------|-------|----------|-------------------|--------|
| **KI-001** | Docling layout label casing mismatch | CRITICAL | All 51 datasets using Docling | ✅ Automated fix available |
| **KI-002** | Docling Table detection unreliable on multi-column text | HIGH | Synthetic + multi-column datasets | ⚠️ Manual VLM verification required |
| **KI-003** | Docling Picture detection unreliable on dense text | MEDIUM | Synthetic + dense text datasets | ⚠️ Manual VLM verification required |
| **KI-004** | LLM handwriting detection unreliable on synthetic | HIGH | All synthetic datasets | ✅ Pattern established (override) |
| **KI-005** | LLM cannot detect synthetic capture method | HIGH | jssoda, synth-multiscript-250k, docsynth300k | ✅ Pattern established (override) |
| **KI-006** | LLM formula detection over-flags scientific text | MEDIUM | All datasets with LLM enrichment | ⚠️ Manual VLM verification required |
| **KI-007** | LLM domain classification high UNK rate on generic content | LOW | Generic/narrative content datasets | ✅ Accepted (taxonomy limitation) |

**Fix Availability**:

- ✅ **Automated**: `scripts/standardize_layout_labels.py` (KI-001)
- ✅ **Pattern**: Integration script override pattern documented (KI-004, KI-005, KI-007)
- ⚠️ **Manual**: Requires per-dataset VLM inspection (KI-002, KI-003, KI-006)

---

## Audit Methodology Reference

### Process Overview

```text
1. Pre-Audit Setup
   ├─ Register dataset in scripts/audit/audit_config.py
   ├─ Run scripts/audit/select_audit_samples.py (stratified 36 samples)
   └─ Create results/<dataset>/ directory

2. Automated Screening
   ├─ Run scripts/audit/run_prescreening.py
   ├─ Identify fields with <100% pass rate
   └─ Generate baseline defect list

3. VLM Visual Inspection
   ├─ Inspect failing samples (category-based)
   ├─ Inspect passing samples (validation)
   ├─ Document corrections in vlm_corrections.json
   └─ Record findings in defect_catalog.json

4. Integration Script Development
   ├─ Fix defects via scripts/integrate_<dataset>_enrichments.py
   ├─ Apply KI-001 to KI-007 mitigations
   ├─ Re-run prescreening to verify fixes
   └─ Update defect_catalog.json with resolution status

5. Final Audit Report
   ├─ Generate comparison_report.json (before/after)
   ├─ Compute scorecard via compute_scorecard.py
   └─ Update AUDIT_TRACKING_INDEX.md
```

### Key Documents

| Document | Purpose | Location |
|----------|---------|----------|
| **Audit Prompt** | Full methodology, criteria, scoring rubric | [docs/prompts/layer2_audit_prompt.md](../prompts/layer2_audit_prompt.md) |
| **Execution Template** | Per-dataset checklist | [docs/audit/AUDIT_EXECUTION_TEMPLATE.md](../audit/AUDIT_EXECUTION_TEMPLATE.md) |
| **Report Template** | Final report format | [docs/audit/AUDIT_REPORT_TEMPLATE.md](../audit/AUDIT_REPORT_TEMPLATE.md) |
| **Scorecard Config** | Automated scoring rubric | [config/audit_scorecard.yaml](../../config/audit_scorecard.yaml) |
| **Integration Template** | Integration script skeleton | [scripts/audit/integration_script_template.py](../../scripts/audit/integration_script_template.py) |

### Key Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **select_audit_samples.py** | Stratified sampling (36 samples) | `python scripts/audit/select_audit_samples.py --dataset diqa-5000` |
| **run_prescreening.py** | Automated field validation | `python scripts/audit/run_prescreening.py --dataset diqa-5000` |
| **standardize_layout_labels.py** | Fix KI-001 layout casing | `python scripts/standardize_layout_labels.py --dataset <name>` |
| **compute_scorecard.py** | Generate audit scorecard | `python scripts/audit/compute_scorecard.py --all-datasets --update-index` |
| **integrate_<dataset>_enrichments.py** | Fix defects via integration | `python scripts/integrate_jssoda_enrichments.py` |

---

## Audit Workflow Example

**Step-by-step example using JSSODa audit**:

```bash
# 1. Register dataset config (if not already done)
# Edit scripts/audit/audit_config.py to add jssoda entry

# 2. Select audit samples (stratified 36)
python scripts/audit/select_audit_samples.py --dataset jssoda

# 3. Run automated prescreening
python scripts/audit/run_prescreening.py --dataset jssoda
# Output: scripts/audit/results/jssoda/automated_screening.json

# 4. VLM visual inspection
# - Inspect failing samples (capture_method, domain, content_flags)
# - Inspect passing samples (validation)
# - Document in scripts/audit/results/jssoda/vlm_corrections.json

# 5. Fix KI-001 layout casing issue
python scripts/standardize_layout_labels.py --dataset jssoda

# 6. Develop integration script
# - Create scripts/integrate_jssoda_enrichments.py
# - Apply KI-002 to KI-007 mitigations
# - Merge LLM enrichment, language enrichment, Docling layout
# - Override capture_method, has_handwriting, has_table, etc.

# 7. Run integration script
python scripts/integrate_jssoda_enrichments.py

# 8. Re-run prescreening to verify fixes
python scripts/audit/run_prescreening.py --dataset jssoda
# Expect: 10/13 fields at 100% pass (up from 0/13)

# 9. Create defect catalog
# scripts/audit/results/jssoda/defect_catalog.json
# Document all 12 defects with fix status, root cause, extrapolation risk

# 10. Compute scorecard (once implemented)
python scripts/audit/compute_scorecard.py --dataset jssoda --update-index

# 11. Update this tracking index
# Edit AUDIT_TRACKING_INDEX.md with audit results
```

---

## Next Steps & Priorities

### Immediate Actions (This Sprint)

1. **Complete Tier 1 Audits**: Prioritize ohr-bench, doclaynet (critical for training)
2. **Implement Scorecard Automation**: Build `scripts/audit/compute_scorecard.py` to auto-populate scorecard table
3. **Create Audit Configs**: Register remaining 39 datasets in `audit_config.py`

### Short-Term (Next 2 Sprints)

1. **Audit High-Value Datasets**: pubtabnet, tablebank, fintabnet, hiertext
2. **Automate KI-002/KI-003 Detection**: Build VLM batch inspection for Docling Table/Picture FPs
3. **Document Integration Patterns**: Create integration script cookbook with KI-mitigation examples

### Long-Term (Phase 7 Complete)

1. **Full Tier 1 Coverage**: All 11 Tier 1 datasets audited before training
2. **Tier 2 Selective Audits**: Audit high-diversity Tier 2 datasets (mdiw13, cocotext, iam)
3. **Cross-Dataset Analysis**: Compute aggregate defect statistics, identify new KI patterns

---

## Version History

| Version | Date | Changes | Audits Added |
|---------|------|---------|--------------|
| 1.0.0 | 2026-02-12 | Initial creation with 3 audited datasets | DIQA-5000, JSSODa, MLT19 |

---

## Scorecard Legend (Planned)

**When scorecard automation is implemented**:

| Metric | Description | Range | Interpretation |
|--------|-------------|-------|----------------|
| **Overall** | Weighted composite score | 0-100 | ≥90 Excellent, 80-89 Good, 70-79 Fair, <70 Needs Work |
| **Grade** | Letter grade | A+ to F | Based on overall score thresholds |
| **Coverage** | % of required fields populated | 0-100 | Target: ≥95% |
| **Validity** | % of populated fields passing validation | 0-100 | Target: ≥98% |
| **Doc** | Documentation completeness | 0-100 | Required fields in source dataset docs |
| **Defects** | Total defects found | N/A | Lower is better |
| **Agreement** | Human-VLM agreement rate | 0-100 | Target: ≥90% |
| **VLM** | VLM inspection sample count | N/A | Minimum 36 samples |

---

**Maintenance Notes**:

- Update this index after EVERY audit completion
- Run `compute_scorecard.py --all-datasets --update-index` to auto-update scorecard table
- Add new datasets to appropriate tier when discovered
- Document new cross-dataset issues in CROSS_DATASET_KNOWN_ISSUES.json
- Keep audit methodology references current with latest process improvements
