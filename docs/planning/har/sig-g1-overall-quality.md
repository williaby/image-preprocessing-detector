# Head Adequacy Review: overall_quality (SIG-G1-6)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: B — IQA
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Identity

| Field | Value |
| --- | --- |
| Head ID | SIG-G1-6 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | overall_quality |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | VQualA ≥ 0.92 (SRCC with human MOS) |
| Primary L2 Field | `ml_image_quality.overall_score` OR `llm_scores.predicted_normalized` |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: DIQA-5000 uses human MOS (`ml_image_quality.overall_score`); VLM pilot path uses `llm_scores.predicted_normalized`; Phase 2: weighted average of individual G1 head scores computed at generation time |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.overall_score` (float 0-1; human MOS path) OR `llm_scores.predicted_normalized` (float 0-1; VLM path)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better) for Phase 1 VLM labels

**Label Provenance**: Phase 1: tier_0_exact (human MOS for DIQA-5000) or tier_1_annotation (VLM for OHR-Bench); Phase 2: tier_0_exact (weighted average of per-degradation augmentation parameters)

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/diqa-5000_audit.md; this head has the most empirical pilot data of all G1 heads)_

**KEY CONTEXT — VLM Pilot Results**: A 200-image VLM pilot was completed on DIQA-5000 using Opus 4.6 vision:

- SRCC overall (all 200 images): 0.39 — below 0.65 target
- SRCC overall (non-rotated 104 images): 0.53 — closer to target
- Root cause: 48% of Q5 (highest MOS) images are rotated 90°. VLM penalizes rotation (scores 2.2-2.8); DIQA MOS does not. Rotation construct mismatch causes systematic label noise.
- Score compression: Only 11 unique overall values, max 3.5, 83% in 2.5-3.2 range (pre-normalization)
- Decision: Proceed with revised VLM prompt v2.0 (orientation-independent scoring + finer granularity)

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 (human MOS) | 5,500 | 5,499 (overall_score) | ~99.9% | High (human ground truth) | _(check audit)_ | 5,499 (pending rotation mismatch resolution) |
| DIQA-5000 (VLM pilot) | 200 | 200 labeled | 100% of pilot | SRCC=0.39 (all), 0.53 (non-rotated) | ⚠️ Below target | Partial — prompt v2.0 needed |
| OHR-Bench | 10,800 | _(analysis required)_ | — | — | — | — |

### Phase 2 — Synthetic Pipeline (Self-Labeling)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are computed as a weighted average of the individual degradation parameters applied during Augraphy generation.

- **Target**: 100,000 synthetic images via Augraphy/augmentation pipeline
- **Label provenance**: tier_0_exact (weighted average of recorded augmentation parameters: blur_sigma, noise_std, contrast_factor, skew_angle, jpeg_quality)
- **Aggregation**: overall_quality = weighted_mean(blur_score, noise_score, contrast_score, skew_score, compression_score) using domain-calibrated weights
- **Risk**: Weighted average may not align with human MOS perceptual weighting; calibration against Phase 1 human MOS required
- **Pipeline status**: _(analysis required — check if Phase 2 pipeline script exists)_

### Usable Pool Summary

- **Phase 1 usable**: 5,499 (DIQA-5000 human MOS) + OHR-Bench (analysis required)
- **Phase 1 target**: 16,300 images
- **Phase 2 usable**: 0 (pipeline not yet created)
- **Phase 2 target**: 100,000 images
- **Combined gap**: 100,000 Phase 2 images + OHR-Bench label population

### VLM Validation Sampling Tier

- Phase 1 DIQA-5000: Tier 1 (max(10, 3%) per quality bucket) — 200-image VLM pilot complete (SRCC=0.39); prompt v2.0 needed before full labeling
- Phase 1 OHR-Bench: Tier 2 (max(15, 10%)) — VLM labeling not yet started; depends on prompt v2.0 validation
- Phase 2: No VLM sampling needed (augmentation parameter weighted average is ground truth, calibrated against Phase 1 MOS)

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| IQA-PILOT-ROTATION | DIQA-5000 | `ml_image_quality.overall_score` (VLM path) | VLM penalizes rotated images; 48% of high-MOS images are 90° rotated; causes SRCC=0.39 overall | OPEN — prompt v2.0 in development |
| IQA-PILOT-COMPRESSION | DIQA-5000 | `llm_scores.predicted_normalized` | Score compression: 83% of VLM scores fall in 2.5-3.2 range; only 11 unique values pre-normalization | OPEN — finer granularity in prompt v2.0 |
| _(analysis required — review diqa-5000_audit.md for additional codes)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) — rotation construct mismatch | CRITICAL — this head's primary label path is VLM; SRCC must reach 0.65 before scaling |
| IQA-KI-COMPRESS-PILOT | Score compression in VLM output — insufficient granularity for regression training | HIGH — revised prompt v2.0 must produce uniform distribution across full 0-1 range |
| IQA-KI-CIRCULAR | overall_quality may reference individual G1 scores — risk of circular dependency | MEDIUM — Phase 2 aggregation approach must be validated against Phase 1 MOS |
| _(check audit for additional KI codes)_ | — | — |

### Remediation Path

_(analysis required after reviewing DIQA-5000 audit; critical path: validate prompt v2.0 with 30-50 images → SRCC must exceed 0.65 → then scale to full Phase 1 pool)_

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: 🔄 Phase 1 partial (5,499 images with human MOS; OHR-Bench pending); Phase 2 not started (0/100,000)

**Target Count**: 16,300 (Phase 1) + 100,000 (Phase 2 synthetic) = 116,300 total

**Current Count**: 5,499 Phase 1 DIQA-5000 with human MOS; OHR-Bench not yet labeled; Phase 2 pipeline not yet created

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 1 total images | 16,300 | 5,499 (DIQA-5000 MOS only) | ❌ 10,801 images gap (OHR-Bench labels missing) |
| Phase 2 total images | 100,000 | 0 | ❌ Not started |
| Phase 1 label tier | ≥80% tier_1 | DIQA-5000: tier_0_exact (human MOS) ✅; OHR-Bench: pending | ⚠️ OHR-Bench must reach tier_1 via prompt v2.0 VLM |
| Phase 1 VLM SRCC | ≥ 0.65 | 0.53 (non-rotated), 0.39 (all) | ❌ Below target — prompt v2.0 required |
| Phase 2 label source | Weighted avg of augmentation params | Not applicable (not yet created) | ✅ No external L2 dependency |
| Phase 2 calibration | Aligned with Phase 1 MOS | Not validated | ⚠️ Calibration study required before Phase 2 assembly |
| DIQA-5000 coverage | 5,500 images | 5,499 labeled | ✅ Met |
| OHR-Bench coverage | 10,800 images | 0 labeled | ❌ Not started |

**Blockers**:

- VLM SRCC at 0.39 (all) / 0.53 (non-rotated) — below 0.65 target. Prompt v2.0 in development. Must validate on 30-50 images before scaling.
- OHR-Bench L2 `ml_image_quality.overall_score` field not yet populated.
- Phase 2 Augraphy synthetic pipeline not yet created.
- Phase 2 weighted-average aggregation formula not yet calibrated against Phase 1 human MOS.

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` _(not yet implemented)_

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| degradation | `quality.degradations` | HIGH — overall_quality aggregates all IQA degradation signals; must cover full degradation space | ≥6 degradation types represented across training set | unknown | TBD |
| capture_method | `capture_method.method` | HIGH — MOS perception differs by capture method; camera images are judged differently than scans | ≥3 capture methods represented | unknown | TBD |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs have different quality dimensions; grayscale vs color affects VLM perception | ≥2 modes (color + grayscale; binarized as edge case) | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM — aged documents have holistic quality perception different from modern degraded docs | ≥2 age classes (modern + aged) | unknown | TBD |
| domain | `domain.level1` | MEDIUM — quality tolerance varies by domain (financial requires high; social media tolerates low) | ≥5 domains | unknown | TBD |
| script_code | `language.script_code` | MEDIUM — VLM quality perception may differ by script due to training data bias | ≥3 script families | unknown | TBD |
| resolution | `resolution.category` | MEDIUM — resolution affects perceived overall quality; must be disentangled from degradation | ≥3 resolution tiers | unknown | TBD |
| layout_type | `structure.layout_type` | LOW — layout type not a primary driver of overall quality signal | ≥3 types | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Rotated document with otherwise good quality | `geometric.orientation_class` (90/180/270) + high MOS | ❌ KNOWN FAILURE | VLM pilot shows SRCC=0.39; VLM penalizes rotation, human MOS does not; prompt v2.0 required |
| Compound multi-degradation (≥5 simultaneous types) | `quality.degradations` | ⏳ | OOD-4a covers this; training may underrepresent extreme compound cases |
| High-quality aged document (historical but preserved) | `image_properties.document_age` + high MOS | ⚠️ | Model may incorrectly penalize aged appearance; must include well-preserved historical docs |
| Binarized document (quality perception ambiguous) | `image_properties.color_mode` | ⚠️ | OOD-4d tests; binarized documents are perceptually distinct from degraded color docs |
| Watermarked otherwise-good document | `physical_degradation.watermark_severity` | ⚠️ | OOD-4b tests; human MOS may score watermarked docs high if text is still legible |
| VLM-hallucinated low quality on clear rotated doc | `geometric.orientation_class` | ❌ KNOWN FAILURE | Root cause of rotation mismatch issue; systematic bias in Phase 1 VLM labels |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types) | 500 | ✅ Direct | Compound distortions not in training distribution; gutter-shadow + page_curl + defocus blur + noise + JPEG — overall_quality must integrate all signals; human annotation required |
| 4b. Watermarked documents | 100 | ✅ Direct | Watermarks directly affect overall perceived quality; tests whether overall_quality is appropriately reduced or whether watermark_severity is incorrectly dominant |
| 4c. Book gutter shadow | 100 | ✅ Direct | Hard shadow gradient tests whether overall_quality responds appropriately to spatially localized but severe degradation |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | Binarized docs absent from Phase 1 training; color_mode=binarized requires special overall_quality convention |
| OOD-Mixed cascade | TBD | ✅ Direct | Multi-distortion cascade scenarios test overall_quality as an aggregated signal |

**OOD Acquisition Status**: ⏳ Not started (Phase 4)

**Missing OOD Sub-sources**: Compound distortion labeling for overall_quality requires human annotation for all 500 OOD-4a images (all IQA head labels needed simultaneously for each compound image).

**OOD Leakage Risk**: DIQA-5000 is in training. OOD-Degradation must use non-DIQA-5000 sources only. OHR-Bench test split must be withheld from Phase 1 training. Additionally, any OHR-Bench images used in OOD must be from the withheld test split only.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench (16,300 images); Phase 2: synthetic augmentation

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independent per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| SIG-G1-1 (blur_score) | DIQA-5000 + OHR-Bench | overall_quality may use blur_score as one component; must not create circular dependency | ✅ Phase 1 labels are independently sourced (MOS/VLM); Phase 2 aggregation is explicit weighted average |
| SIG-G1-2 (noise_score) | DIQA-5000 + OHR-Bench | Same circular dependency risk as blur_score | ✅ Same mitigation; Phase 2 formula must be fixed (not learned from other heads) |
| SIG-G1-3 (contrast_score) | DIQA-5000 + OHR-Bench | Same circular dependency risk | ✅ Same mitigation |
| SIG-G1-4 (skew_score) | DIQA-5000 + OHR-Bench | Same circular dependency risk | ✅ Same mitigation |
| SIG-G1-5 (compression_score) | DIQA-5000 + OHR-Bench | Same circular dependency risk | ✅ Same mitigation |
| SIG-G3-2 (skew_reg) | Different datasets | Naming clarity: overall_quality is unrelated to skew_reg | ✅ No shared data; different head group |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits well-defined. MEDIUM (Phase 2) — synthetic images must be SHA256-deduped against all other training sets. MEDIUM (VLM labels) — VLM pilot images (200) from DIQA-5000 must remain in training split, not OOD.

**Label Convention**: overall_quality is 0-1 where 1.0 = perfect overall quality, 0.0 = unusable quality. Phase 1 MOS is normalized from [0, 5] DIQA scale to [0, 1]. Phase 2 weighted average uses fixed weights (not learned). Label conventions for rotated, binarized, and watermarked images must be documented before assembly. Specifically: rotation does NOT reduce overall_quality if geometric correction is applied downstream (prompt v2.0 must reflect this).

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G1-6-G01 | IQA-PILOT-ROTATION | VLM prompt v1.0 SRCC below 0.65 target — rotation mismatch causes systematic label noise | VLM penalizes document rotation; human MOS is orientation-agnostic | Develop and validate VLM prompt v2.0 (orientation-independent scoring); test on 30-50 images; require SRCC ≥ 0.65 before scaling | 2-3 days |
| G1-6-G02 | — | OHR-Bench `ml_image_quality.overall_score` not populated | L2 enrichment pipeline not yet run on OHR-Bench | Run VLM labeling pipeline on OHR-Bench using validated prompt v2.0; populate `ml_image_quality.overall_score` | _(analysis required after G01 resolved)_ |
| G1-6-G03 | — | Phase 2 Augraphy synthetic pipeline not yet created | Script `prepare_multitask_datasets.py iqa` not implemented | Implement IQA sub-command; compute overall_quality as weighted average of individual degradation scores at generation time | _(analysis required)_ |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G1-6-G04 | IQA-PILOT-COMPRESSION: VLM score compression — 83% of scores in 2.5-3.2 pre-normalization | VLM prompt v1.0 not calibrated for fine-grained IQA scoring | Prompt v2.0 must include anchoring examples and explicit scale instructions to spread scores across full [0,5] range | 1-2 days (within prompt v2.0 work) |
| G1-6-G05 | Phase 2 weighted-average formula not calibrated against Phase 1 human MOS | Aggregation weights are assumed, not empirically derived | After Phase 1 assembly, compute correlation between weighted-average formula and human MOS on DIQA-5000 validation split; adjust weights | _(analysis required)_ |
| G1-6-G06 | Binarized document label convention for overall_quality undefined | 1-bit images have ambiguous overall quality under continuous 0-1 scoring | Document convention: overall_quality for binarized = f(legibility, contrast) only — compression and noise dimensions not applicable; add handling in assembly script | _(analysis required)_ |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G1-6-G07 | Per-degradation weight in Phase 2 overall_quality aggregation is fixed; domain-specific weights not explored | After training, analyze which degradation weights best predict human MOS per domain; use as calibration signal |
| G1-6-G08 | VLM inter-rater reliability not measured (single model used for all labels) | Run labeling with two VLM models; compute agreement; flag divergent labels for human review |

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
