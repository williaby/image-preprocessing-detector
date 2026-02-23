# Head Adequacy Review: presence_reg (SIG-G4-4)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: E — Handwriting
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G4-4 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | presence_reg (also written as handwriting_presence_score) |
| Task Type | Regression — 0-1 continuous (area ratio: fraction of page that is handwritten) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P1 |
| Performance Target | SRCC ≥ 0.70 vs pixel-level annotation (HierText gold standard) |
| Primary L2 Field | `handwriting_assessment.presence_score` (float 0-1) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5); SIG-G4-1 (presence_cls is the discretized version of this score) |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.presence_score` _(float 0.0–1.0; area ratio of handwriting pixels per page)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact preferred (HierText pixel-level polygons); tier_1_annotation acceptable (model-derived from area ratio); heuristic midpoint mapping for datasets without pixel annotations

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Label Derivation Hierarchy

| Method | Datasets | Precision | Confidence |
| --- | --- | --- | --- |
| Pixel-level polygon area ratio (gold standard) | HierText | High (~1% granularity) | tier_0_exact |
| Polygon bounding-box area ratio | COCO-Text, FUNSD | Medium (~5% granularity) | tier_1_annotation |
| Corpus-level presence class midpoint | IAM, NIST-SD2 (→1.0), DocLayNet (→0.0) | Low (fixed value) | tier_2_heuristic |
| VLM-estimated area ratio | Muharaf, PUCIT-OHUL | Medium (±0.10) | tier_2_heuristic |

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| HierText | 8,281 | _(analysis required — pixel-level gold standard)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| COCO-Text | 63,686 | _(analysis required — bounding box area proxy)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| IAM | _(analysis required)_ | _(fixed: ~0.95 by design — all handwritten)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Muharaf | _(analysis required — GCS-only locally)_ | _(analysis required — VLM labeling required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| PUCIT-OHUL | _(analysis required — GCS-only locally)_ | _(analysis required — VLM labeling required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Nepali Handwritten | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| NIST SD-19 | _(analysis required)_ | _(fixed: ~1.0 by design — all handwritten)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| FUNSD | _(analysis required)_ | _(analysis required — form fill-in area ratio)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| DocLayNet (negatives) | 81,000 | _(fixed: 0.0 by design — all printed)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| TableBank (negatives) | 278,000 | _(fixed: 0.0 by design — all printed)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 102,000+ images (shared with all G4 heads)
- **Gap**: Continuous score range 0.01–0.30 (SPARSE to MODERATE) is undercovered — most datasets are bimodal (0.0 from negatives; 0.8–1.0 from pure handwriting corpora)

### VLM Validation Sampling Tier

_(analysis required — mid-range scores 0.10–0.60 likely require Tier 2/3 VLM validation; HierText gold standard can serve as calibration reference for VLM accuracy)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-04-A | Training data is bimodal (0.0 from negatives, ~1.0 from pure corpora) — sparse mid-range coverage | HIGH — SRCC target of 0.70 may not be achievable without dedicated mid-range examples |
| KI-G4-04-B | HierText polygon-level area ratio is the only true gold standard (8,281 images) — small relative to 102K target | MEDIUM — gold standard images will be weighted differently than heuristic-labeled images |
| KI-G4-04-C | Gaussian NLL head requires per-sample uncertainty estimates — not all label derivation methods provide these | MEDIUM — uncertainty must be set from label confidence tier: tier_0→low uncertainty, tier_2→high uncertainty |
| KI-G4-04-D | COCO-Text bounding box area ratio overestimates actual handwriting pixels (box includes background) | MEDIUM — systematic upward bias; correction factor needed |

### Remediation Path

_(analysis required — initial steps: 1) compute HierText pixel-ratio labels, 2) audit mid-range score coverage, 3) define uncertainty assignment per confidence tier)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 102,000+ images (shared with all G4 heads) |
| Assembly Status | ⏳ Not started |
| Current Count | _(analysis required)_ |
| Gold Standard | HierText — 8,281 images with pixel-level handwriting polygon annotations |
| Score Derivation | presence_score = pixel-ratio of handwriting per page (HierText); midpoint mapping for other datasets |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Score Distribution Requirements

| Score Range | Corresponding Class | Target Coverage | Primary Source | Risk |
| --- | --- | --- | --- | --- |
| 0.00 | NONE | ≥ 20% (capped) | Printed negatives | LOW — over-represented |
| 0.001–0.099 | SPARSE | ≥ 10% | FUNSD, COCO-Text | HIGH — undercovered |
| 0.10–0.299 | MODERATE | ≥ 15% | HierText, COCO-Text | HIGH — undercovered |
| 0.30–0.599 | SUBSTANTIAL | ≥ 20% | HierText, Muharaf | MEDIUM |
| 0.60–1.00 | DOMINANT | ≥ 25% | IAM, NIST-SD2, Muharaf | LOW — well-covered |

**Blockers**:

- handwriting subcommand of `prepare_multitask_datasets.py` not yet implemented
- HierText pixel-level area ratio computation script not yet created
- Uncertainty assignment strategy for non-gold-standard labels not defined
- COCO-Text bounding box bias correction factor not quantified

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL | ≥ 3 methods (born_digital, scanner, camera) | unknown | TBD |
| domain | `domain.level1` | HIGH | ≥ 5 domains | unknown | TBD |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes (color, grayscale) | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM | All 3 ages (modern, aged, historical) | unknown | TBD |
| script_code | `language.script_code` | HIGH | ≥ 4 scripts (LATN, ARAB, DEVA, JPAN) | unknown | TBD |
| resolution | `resolution.category` | MEDIUM | ≥ 3 tiers | unknown | TBD |
| layout_type | `structure.layout_type` | LOW | ≥ 3 types | unknown | TBD |
| degradation | `quality.degradations` | MEDIUM | ≥ 3 types | unknown | TBD |
| presence_score_range | `handwriting_assessment.presence_score` | CRITICAL | Full 0–1 range with density in 0.01–0.60 | unknown | TBD |
| annotation_method | _(L2 confidence field)_ | HIGH | Mix of tier_0, tier_1, tier_2 in known proportions | unknown | TBD |
| page_layout_complexity | `structure.layout_type` | MEDIUM | Forms, free-form pages, notebooks | unknown | TBD |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | unknown | TBD |
| mixed_content | `handwriting_assessment.is_mixed` | HIGH | Mixed pages stress mid-range score precision | unknown | TBD |
| background_complexity | `image_properties.background` | LOW | Plain and complex | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Sparse handwriting mixed with dense printed forms | `handwriting_assessment.is_mixed` | ⏳ | analysis required — critical for mid-range scores |
| Faint / low-opacity handwriting (pencil, light ink) | `quality.degradations` | ⏳ | analysis required — affects pixel-ratio ground truth |
| Camera-captured partial handwriting (some pages) | `capture_method.method` = camera_smartphone | ⏳ | analysis required |
| Historical partially-handwritten documents | `image_properties.document_age` = historical | ⏳ | analysis required |
| Non-Latin handwriting area estimation | `language.script_code` | ⏳ | analysis required |
| Stamp / signature on otherwise printed page (score ~0.02–0.05) | `handwriting_assessment.presence_score` | ⏳ | analysis required — edge of SPARSE class |
| Handwritten annotations in document margins | `structure.layout_type` | ⏳ | analysis required |
| Fully handwritten page with degraded background | `quality.degradations` | ⏳ | analysis required |
| Page with only handwritten title block and printed body | `handwriting_assessment.is_mixed` | ⏳ | analysis required — score ~0.05–0.15 |
| Near-zero handwriting presence (single word or line) | `handwriting_assessment.presence_score` | ⏳ | analysis required — SPARSE lower bound |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | presence_score ≈ 0.8–1.0, script=Arab, text_direction=rtl | SigLIP 2 | Full-page Arabic cursive; presence_score at high end |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc if access denied) | presence_score ≈ 0.7–1.0, script=HANS/HANT | SigLIP 2 | 2–4 week access request for CASIA |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | presence_score ≈ 0.7–1.0, script=Deva | SigLIP 2 | Tests regression on non-Latin full-page handwriting |
| 5d. Specialized content handwriting | 50 | Internal collection / TBD | presence_score ≈ 0.3–0.8, content_type=specialized | SigLIP 2 | Math/engineering may have mixed handwriting and diagram density |

### Additional Regression-Specific OOD Notes

OOD-Handwriting sub-sources are heavily weighted toward DOMINANT presence (score 0.7–1.0). For SIG-G4-4, mid-range score evaluation (0.10–0.60) is underrepresented in OOD. Consider augmenting with partial-handwriting documents if SRCC evaluation is insufficient.

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 5, P0)

### Missing OOD Sub-sources

- Mid-range presence score (0.10–0.50) OOD examples — current sources skew DOMINANT
- KHATT and CASIA pixel-level area ratio labels required for reliable SRCC computation against gold standard

### OOD Leakage Risk

**Level**: MEDIUM

Same as all G4 heads. Additional regression-specific risk: if OOD presence_score labels are computed from bounding boxes (not pixel level), SRCC measurement will be noisy. Recommend pixel-level annotation for OOD gold standard where feasible.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-1 (presence_cls) | presence_cls is the discretized version of presence_reg score | Class boundaries must be applied consistently: NONE 0.0–0.01, SPARSE 0.01–0.10, MODERATE 0.10–0.30, SUBSTANTIAL 0.30–0.60, DOMINANT 0.60–1.00. Same image must have logically consistent presence_score and presence class. |
| SIG-G4-5 (legibility_reg) | Shares training dataset | Gaussian NLL head architecture is shared between presence_reg and legibility_reg; output calibration must be done independently per head |
| SIG-G4-2 (legibility_cls) | Legibility is meaningless if presence_score = 0.0 | Images with presence_score = 0.0 must have legibility set to N/A; enforced by label dependency rule |

### Split Leakage Risk

**Level**: MEDIUM

Same as all G4 heads — global split registry required. Additional risk: HierText is the gold standard for SRCC validation. If HierText images appear in both presence_reg training and test splits, SRCC will be overestimated. HierText test split must be held out completely if used as the primary evaluation benchmark.

### Label Convention

presence_score is a float in [0.0, 1.0] representing the fraction of the page image area that is covered by handwriting pixels. Computed from polygon area for HierText (gold standard). Midpoint mapping for corpus-level labels: IAM → 0.95, NIST-SD2 → 1.0, printed negatives → 0.0. Bounding-box proxy from COCO-Text is a known overestimate — must document systematic bias in evaluation.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G4PR-G01 | — | handwriting subcommand of prepare_multitask_datasets.py not implemented | Phase 3 dataset prep deprioritized | Implement subcommand (shared blocker with all G4 heads) | 2 days (shared) |
| G4PR-G02 | — | HierText pixel-level area ratio computation script not yet created | Gold standard label extraction not implemented | Write script to compute handwriting pixel area ratio from HierText polygon annotations | 1 day |
| G4PR-G03 | — | Mid-range score (0.01–0.60) severely undercovered — training data is bimodal | Pure corpora are either all-handwritten or all-printed | Identify or synthesize documents with partial handwriting coverage; evaluate FUNSD and COCO-Text mid-range coverage | 1 day analysis + TBD sourcing |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G4PR-G04 | Uncertainty assignment for non-gold-standard labels not defined — Gaussian NLL training requires sigma_sq targets | Label uncertainty not modeled during harmonization | Define per-confidence-tier sigma_sq values: tier_0 → 0.01, tier_1 → 0.05, tier_2 → 0.15 | 0.5 days |
| G4PR-G05 | COCO-Text bounding box area ratio overestimates handwriting coverage — systematic bias | Bounding boxes include background whitespace | Compute correction factor from HierText (where both polygon and bbox are available); apply to COCO-Text labels | 1 day |
| G4PR-G06 | HierText test split not explicitly held out for regression SRCC evaluation | Split registry not yet implemented | Register HierText splits in global split registry before assembly; hold out test split for evaluation only | 0.5 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G4PR-G07 | OOD mid-range score coverage (0.10–0.50) insufficient for comprehensive SRCC evaluation | Source partial-handwriting documents (annotated forms with fill-ins) for OOD pool |
| G4PR-G08 | Gaussian NLL calibration not planned — sigma_sq may be miscalibrated | Add calibration step post-training: measure actual vs predicted uncertainty on val set |

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
