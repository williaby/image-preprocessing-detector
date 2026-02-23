# Head Adequacy Review: skew_reg (SIG-G3-2)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: A — Geometry
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G3-2 |
| Model | SigLIP 2 NAFlex |
| Group | G3 — Orientation + Skew |
| Head Name | skew_reg |
| Task Type | Regression ±10° (skew angle in degrees) |
| Output Format | SmoothL1 (continuous angle) |
| Priority | P1 |
| Performance Target | MAE < 0.3°, 90% within 0.5° |
| Primary L2 Field | `geometric.skew_angle_degrees` |
| Shared-Data Heads | MNV4-H2 (shares training dataset); SIG-G3-1 (same training group) |
| Training Phase | Phase 4 — Orientation + Skew Group (trained jointly with SIG-G3-1) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `geometric.skew_angle_degrees` _float, degrees_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact or tier_1_annotation preferred

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — | — | — |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 90,000 images (same dataset as MNV4-H2)
- **Gap**: _(analysis required)_

### VLM Validation Sampling Tier

_(analysis required — assign Tier 1/2/3 after pool analysis)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| _(analysis required)_ | — | — |

### Remediation Path

_(analysis required — enumerate steps after pool gap is quantified)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 90,000 images (same dataset as MNV4-H2) |
| Assembly Status | ✅ Complete (dataset ready — 71,498 synthetic + 18,914 natural) |
| Distribution | Same as MNV4-H2. SIG-G3-2 targets tighter MAE (< 0.3°) vs MNV4-H2 (< 0.5°) due to larger model capacity. |
| Real Data Ratio | 21% natural (18.9K of 90K) — meets ≥ 20% floor |
| Assembly Script | Same skew pipeline as MNV4-H2 |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | _(analysis required)_ | — | — | TBD |
| domain | `domain.level1` | _(analysis required)_ | — | — | TBD |
| color_mode | `image_properties.color_mode` | _(analysis required)_ | — | — | TBD |
| document_age | `image_properties.document_age` | _(analysis required)_ | — | — | TBD |
| script_code | `language.script_code` | _(analysis required)_ | — | — | TBD |
| resolution | `resolution.category` | _(analysis required)_ | — | — | TBD |
| layout_type | `structure.layout_type` | _(analysis required)_ | — | — | TBD |
| degradation | `quality.degradations` | _(analysis required)_ | — | — | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| _(analysis required)_ | — | ⏳ | — |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Geometry (Phase 2, P0, 500 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Notes |
| --- | --- | --- | --- | --- |
| 2b. Extreme perspective | 100 | Internal photography at > 30° tilt | skew_angle_degrees (measured), warping_type=perspective, capture_method=camera_smartphone | Same sub-source as MNV4-H2. |
| OOD-Capture 3b. ADF scanner with curl artifacts | 150 | Internal ADF scans | warping_type=page_curl AND skew_angle_degrees | Same sub-source as MNV4-H2. |
| OOD-Mixed cascade failures | — | Various | — | SigLIP must correct MNV4-H2 errors on difficult cases — these are the hard negatives for this head. |

### Role in the Two-Model Pipeline

SIG-G3-2 faces the hardest OOD scenarios: ambiguous cases where MNV4-H2 already failed. The OOD evaluation for this head should explicitly include documents where MNV4-H2's prediction error exceeds 1.0° to quantify the correction benefit.

### OOD Leakage Risk

Same as MNV4-H2 — skew dataset uses 13 source datasets for natural scans. SHA256-keyed global split registry required. OOD-Mixed cross-category use of OOD-Geometry images is intentional.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| MNV4-H2 (skew_reg) | Shares training dataset | SIG-G3-2 is the precision correction layer over MNV4-H2's faster estimate. Must use same L2 label field (`geometric.skew_angle_degrees`) with identical conventions. Split registry ensures no test leakage between MNV4 and SigLIP evaluation. |
| SIG-G3-1 (orientation_cls) | Trained jointly in Phase 4 | Orientation must be canonicalized before skew is computed. Joint training schedule must order orientation warmup before skew regression phases. |

### Split Leakage Risk

**Level**: MEDIUM

Same as MNV4-H2 — 13 source datasets shared with other training sets. Global split registry required (SHA256-keyed by image).

### Label Convention

Skew angle in degrees, positive = clockwise tilt. Range: ±10° for synthetic training data; natural scans at inference time may present up to ±45°. This convention must be identical in both MNV4-H2 and SIG-G3-2 training datasets. No convention drift permitted between the two shared-data heads.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — | — |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| _(analysis required)_ | — | — |

---

## Section 9 — Multi-Model Consensus

**Status**: ⏳ Pending execution

**Adequacy Rating (pre-consensus)**: ⏳ TBD (analysis required)

**Analyst Summary**: _(To be written after Sections 2–8 analysis is complete)_

**Consensus Prompt**: _(To be written after Section 8 gap registry is complete)_

**Models**: google/gemini-2.5-pro, google/gemini-3-pro-preview, openai/gpt-5.2,
deepseek/deepseek-r1-0528, x-ai/grok-4 (all neutral)

**Consensus Summary**: _(Pending)_

**Final Rating**: _(Pending)_

**Top Recommendations**: _(Pending)_

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | TBD | TBD |
| 14-Dimension Coverage | 25% | TBD | TBD |
| Wild Condition Coverage | 20% | TBD | TBD |
| OOD Design Quality | 20% | TBD | TBD |
| **Overall** | 100% | — | TBD |

**Grade**: ⏳ TBD
