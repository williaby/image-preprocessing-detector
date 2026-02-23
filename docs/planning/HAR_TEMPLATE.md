# Head Adequacy Review (HAR) Template

> **Status**: Template v1.0
> **Usage**: Copy this file to `docs/planning/har/{head-id}-{head-name}.md` and fill in each section.
> **Methodology**: See `docs/planning/HAR_MASTER_INDEX.md` for the HAR methodology overview.
> **Scoring**: Source Pool (35%) + 14-Dimension (25%) + Wild Condition (20%) + OOD Quality (20%)

---

## Section 1 — Head Identity

| Field | Value |
| --- | --- |
| Head ID | _e.g., SIG-G5-2_ |
| Model | _SigLIP 2 NAFlex or MobileNetV4-Conv-S_ |
| Group | _e.g., G5 — Page Attributes_ |
| Head Name | _e.g., shadow_reg_ |
| Task Type | _e.g., Regression (0-1 continuous severity score)_ |
| Output Format | _e.g., scalar float via Gaussian NLL head (mu, sigma_sq)_ |
| Priority | _P0 / P1 / P2_ |
| Performance Target | _e.g., MAE < 0.08 on OOD-Degradation shadow sub-set_ |
| Primary L2 Field | _e.g., `physical_degradation.shadow_severity`_ |
| Shared-Data Heads | _e.g., SIG-G5-3 (warping_reg shares physical_degradation)_ |
| Training Phase | _e.g., Phase 5 (Page Attributes)_ |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `_field.path_` _(type)_
**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)
**Label Provenance**: tier_0_exact or tier_1_annotation preferred
**Audit-Derived Defects**: _List any D-codes from dataset audits that affect this field_

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| _dataset-name_ | _N_ | _n_ | __%_ | __%_ | _A/B/C/D/F_ | _✅/⚠️/❌ N_ |

### Usable Pool Summary

- **Total usable before enrichment**: _N images_
- **Training target**: _N images_
- **Gap**: _Describe gap if any_

### VLM Validation Sampling Tier

- Tier 1 (Standard — max(10, 3%)): _applied to: dataset-a, dataset-b_
- Tier 2 (Enhanced — max(15, 10%)): _applied to: dataset-c (higher uncertainty)_
- Tier 3 (Deep — max(25, 15%)): _applied to: dataset-d (significant uncertainty or coverage issues)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(none yet)_ | — | — | _No audits run yet_ | OPEN |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| _(none identified)_ | — | — |

### Remediation Path

1. _Step 1: Describe remediation action_
2. _Step 2: Additional steps if needed_

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: ⏳ Not started / 🔄 In progress / ✅ Complete
**Target Count**: _N images_
**Current Count**: _N assembled / N usable in pool_

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Total images | _N_ | _N_ | _✅/⚠️/❌_ |
| Label tier | ≥80% tier_1 | _N/A_ | — |
| _Class/bucket name_ | _%_ | _unknown_ | _⚠️_ |
| Real data ratio | ≥50% | __%_ | _✅/❌_ |

**Blockers**:

- _List any blockers that prevent assembly_

**Assembly Script**: `scripts/prepare_multitask_datasets.py {subcommand}`

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _XX/100_ (computed after assembly)

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL/HIGH/MEDIUM/LOW | _≥N classes_ | _unknown_ | _⚠️/✅/❌ N_ |
| domain | `domain.level1` | HIGH | _≥N domains_ | _unknown_ | _⚠️/✅/❌ N_ |
| color_mode | `image_properties.color_mode` | HIGH | _≥2 modes_ | _unknown_ | _⚠️/✅/❌ N_ |
| document_age | `image_properties.document_age` | MEDIUM | _All 3 ages_ | _unknown_ | _⚠️/✅/❌ N_ |
| script_code | `language.script_code` | MEDIUM | _≥N scripts_ | _unknown_ | _⚠️/✅/❌ N_ |
| resolution | `resolution.category` | LOW | _Standard OK_ | _unknown_ | _⚠️/✅/❌ N_ |
| layout_type | `structure.layout_type` | LOW | _≥N types_ | _unknown_ | _⚠️/✅/❌ N_ |
| degradation | `quality.degradations` | LOW | _≥2 types_ | _unknown_ | _⚠️/✅/❌ N_ |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _XX/100_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| _Condition name_ | `field.path` | _✅/⚠️/❌_ | _Description of gap_ |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: _OOD-Category (Phase N, Priority, N total images)_
**Head-Specific Sub-source**: _"Sub-source name" (N images, acquisition method)_

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| _Sub-source name_ | _N_ | _✅/⚠️/❌_ | _Stress scenario description_ |

**OOD Acquisition Status**: ⏳ Not started (Phase N)
**Missing OOD Sub-sources**: _List any missing sub-sources specific to this head_
**OOD Leakage Risk**: _Describe leakage risk and mitigations_

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: _dataset-name; other-head also uses same dataset_
**Shared Source Datasets**: _List source datasets shared with other heads_

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| _Head-ID (head-name)_ | _dataset-name_ | _Risk description_ | _✅/⚠️ Mitigation_ |

**Split Leakage Risk**: LOW/MEDIUM/HIGH — _reason_
**Label Convention**: _Any shared label conventions that must be consistent_

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| _HEAD-G01_ | — | _Gap description_ | _Root cause_ | _Remediation action_ | _N days_ |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| _HEAD-G02_ | _Gap description_ | _Root cause_ | _Remediation action_ | _N days_ |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| _HEAD-G03_ | _Gap description_ | _Remediation action_ |

---

## Section 9 — Multi-Model Consensus

**Status**: ⏳ Pending execution
**Adequacy Rating (pre-consensus)**: ❌ Blocked / ⚠️ Needs Work / ✅ Ready

**Analyst Summary** (fill before running consensus):

_1-paragraph summary of findings from Sections 2–8, covering usable pool size, P0 blockers,
OOD design quality, and the most significant wild condition gaps._

**Consensus Prompt**:

```
Evaluate the training dataset design and OOD coverage for the SigLIP2/MobileNetV4 `{head_name}` head.
This head is a {task_type} predicting {description}.
Primary L2 field: `{l2_field}`.
Source pool: {pool_description}.
Target: {target_count} training images {distribution_if_applicable}.
OOD: {ood_description}.
Performance target: {performance_target}.
P0 gaps: {p0_gap_list}.
P1 gaps: {p1_gap_list}.

Evaluate: (1) Is the source pool sufficient to meet the training target once P0 gaps are resolved?
(2) Are the P0 blockers correctly identified and prioritized?
(3) Does the OOD design adequately stress this head's realistic failure modes?
(4) What risks are missing from the gap registry?
(5) Overall rating: Ready / Needs Work / Blocked — with 1-paragraph justification.
```

**Models**: google/gemini-2.5-pro, google/gemini-3-pro-preview, openai/gpt-5.2,
deepseek/deepseek-r1-0528, x-ai/grok-4 (all neutral)

**Consensus Summary**: _[append after execution]_
**Final Rating**: _[Ready / Needs Work / Blocked]_
**Top Recommendations**: _[bullet list from synthesis]_

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | _/100_ | _/35_ |
| 14-Dimension Coverage | 25% | _/100_ | _/25_ |
| Wild Condition Coverage | 20% | _/100_ | _/20_ |
| OOD Design Quality | 20% | _/100_ | _/20_ |
| **Overall** | 100% | — | _/100_ |

**Grade**: ❌ Blocked / ⚠️ Needs Work / ✅ Ready
