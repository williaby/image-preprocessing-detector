# Head Adequacy Review: skew_reg (MNV4-H2)

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
| Head ID | MNV4-H2 |
| Model | MobileNetV4-Conv-S |
| Group | Pre-Correction Stage Gate |
| Head Name | skew_reg |
| Task Type | Regression ±10° (skew angle in degrees) |
| Output Format | Linear output (angle degrees) — hybrid bins (42 classes) + residual regression |
| Priority | P0 |
| Performance Target | MAE < 0.5° |
| Primary L2 Field | `geometric.skew_angle_degrees` |
| Shared-Data Heads | SIG-G3-2 (skew_reg uses same training dataset) |
| Training Phase | Phase 4 — Pre-Correction Gate |

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
- **Training target**: 90,000 images
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
| Target Count | 90,000 images (90,412 actual — dataset COMPLETE) |
| Assembly Status | ✅ Complete (71,498 synthetic + 18,914 natural scans at E:\03_training_datasets\skew\\) |
| Distribution | 71K synthetic (ProcessPoolExecutor, 384×384 JPEG q90) + 19K natural scans from 13 source datasets; conf ≥ 0.7 classical ensemble filter; split: 70,763 train / 9,025 val / 10,624 test |
| Real Data Ratio | 21% natural (18.9K of 90K) — meets ≥ 20% floor |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (skew pipeline complete, no further work needed) |

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

### OOD Sub-Sources Relevant to skew_reg

| Sub-Source | Images | Source | Labels Required | Notes |
| --- | --- | --- | --- | --- |
| 2b. Extreme perspective | 100 | Internal photography at > 30° tilt | skew_angle_degrees (measured), warping_type=perspective, capture_method=camera_smartphone | Tests interaction of perspective warping with skew estimation. |
| OOD-Capture 3b. ADF scanner with curl artifacts | 150 | Internal ADF scans | warping_type=page_curl AND skew_angle_degrees | Tests whether page curl degrades skew estimation accuracy. |
| OOD-Mixed cascade failures | — | Various | — | Scenarios where skew is compounded with other distortions. |

### Key Stress Test

Documents where skew estimation is confounded by page curl, perspective, or shadow — these are the highest-risk failure modes for this head in production.

### OOD Leakage Risk

Skew dataset uses 13 source datasets for natural scans. Must verify OOD-Geometry documents are not present in any training split. SHA256-keyed global split registry is required.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G3-2 (skew_reg) | Shares exact same 90K training dataset | Must use global split registry (SHA256-keyed). Both use `geometric.skew_angle_degrees` with identical label conventions. |
| MNV4-H1 (orientation) | Same model, different task | Skew and orientation interact. Training pipeline applies orientation correction BEFORE skew estimation. Skew dataset was built from already-orientation-corrected images. |
| SIG-G1-4 (skew_score) | Related but distinct concept | skew_score is a 0–1 IQA severity metric (how badly skewed is the document?). skew_reg is the actual angle in degrees. Different fields, different semantics — must not conflate. |

### Split Leakage Risk

**Level**: MEDIUM

13 source datasets are shared with other training sets. Global split registry is required (SHA256-keyed by image) to prevent test leakage between MNV4 and SigLIP evaluation sets.

### Label Convention

Skew angle in degrees, positive = clockwise tilt. Range: ±10° for synthetic training data; natural scans at inference time may present up to ±45°. This convention must be identical in both MNV4-H2 and SIG-G3-2 training datasets.

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
