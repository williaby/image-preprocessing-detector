# Head Adequacy Review: orientation_cls (SIG-G3-1)

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
| Head ID | SIG-G3-1 |
| Model | SigLIP 2 NAFlex |
| Group | G3 — Orientation + Skew |
| Head Name | orientation_cls |
| Task Type | Classification — 4 classes (0 / 90 / 180 / 270) |
| Output Format | Softmax over 4 orientations |
| Priority | P1 |
| Performance Target | Accuracy ≥ 98% |
| Primary L2 Field | `geometric.orientation_class` |
| Shared-Data Heads | MNV4-H1 (shares training dataset); SIG-G3-2 (same dataset group) |
| Training Phase | Phase 4 — Orientation + Skew Group (trained jointly with SIG-G3-2) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `geometric.orientation_class` _string enum: 0, 90, 180, 270_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact or tier_1_annotation preferred

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — | — | — |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 50,000 images (same dataset as MNV4-H1)
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
| Target Count | 50,000 images (same dataset as MNV4-H1) |
| Assembly Status | ✅ Complete (dataset ready at E:\image_detection\03_training_datasets\orientation\\) |
| Distribution | Same as MNV4-H1 — balanced 4-class (12,500 docs × 4 rotations). Japanese vertical text labeled at 0°. |
| Real Data Ratio | ≥ 50% required |
| Accuracy Note | SIG-G3-1 targets higher accuracy (≥ 98%) than MNV4-H1 (≥ 95%) due to larger model capacity. |
| Assembly Script | `scripts/prepare_multitask_datasets.py orientation` |

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

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 2a. Symmetric documents | 300 | Wikipedia / gov-form screenshots NOT from DocLayNet | orientation_class | mobilenetv4 + siglip2 | Tests 0°/180° disambiguation on visually symmetric pages. Must dedup against DocLayNet. |
| 2b. Extreme perspective | 100 | Internal photography at > 30° tilt | skew_angle_degrees (measured), warping_type=perspective, capture_method=camera_smartphone | mobilenetv4 + siglip2 | — |
| 2c. Japanese vertical text | 100 | NDL Digital Collection | script=Jpan, orientation=0, text_direction=ttb | mobilenetv4 + siglip2 | Must dedup against synth-multiscript-v3 Jpan samples. |

### Additional Coverage

OOD-Mixed sub-sources that include orientation cascade failures (Mongolian TTB + aged + perspective) test whether SigLIP 2 can correct MNV4 failures on ambiguous documents.

### OOD Leakage Risk

Same as MNV4-H1 — training set is closed, OOD uses different sources. OOD-Mixed cross-category may re-use OOD-Geometry images combined with other distortions; this is intentional and does not constitute leakage.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| MNV4-H1 (orientation) | Shares exact same 50K training dataset | Must use global split registry (SHA256-keyed) to avoid test contamination. SigLIP 2 serves as correction/validation layer over MNV4-H1 predictions. |
| SIG-G3-2 (skew_reg) | Trained jointly in Phase 4 | Skew and orientation interact — misoriented docs appear skewed. Labels must be computed after canonical orientation is established. |

### Split Leakage Risk

**Level**: LOW

Same reasoning as MNV4-H1 — training set is closed (12,500 unique docs × 4 rotations). OOD uses different sources.

### Label Convention

`orientation=0` for Japanese TTB text — same convention must be enforced in both MNV4-H1 and SIG-G3-1 training datasets. Any future dataset additions must apply this convention before assembly to maintain consistency across the two heads sharing this dataset.

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
