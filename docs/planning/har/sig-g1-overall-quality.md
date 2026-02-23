# Head Adequacy Review: overall_quality (SIG-G1-6)

> **Status**: ✅ Complete
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: B — IQA
> **Adequacy**: ❌ Blocked (37/100)

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
| Performance Target | SRCC ≥ 0.65 with human MOS on DIQA-5000 held-out set |
| Primary L2 Field | `ml_image_quality.overall_score` OR `llm_scores.predicted_normalized` |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench + RealDAE) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: DIQA-5000 uses human MOS (`ml_image_quality.overall_score`); VLM pilot path uses `llm_scores.predicted_normalized`; Phase 2: weighted average of individual G1 head scores computed at generation time |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.overall_score` (float 0-1; human MOS path) OR `llm_scores.predicted_normalized` (float 0-1; VLM path)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better) for Phase 1 VLM labels

**Label Provenance**: Phase 1: tier_0_exact (human MOS for DIQA-5000) or tier_1_annotation (VLM for OHR-Bench); Phase 2: tier_0_exact (weighted average of recorded augmentation parameters)

**Note on pre-correction context**: SigLIP 2 operates on images that have already been orientation- and skew-corrected by MobileNetV4. This means VLM labels for training data MUST be generated on pre-corrected (properly oriented) images, or the VLM must score images in an orientation-independent manner. The rotation construct mismatch in the pilot is therefore a label methodology issue, not a model architecture issue.

**KEY CONTEXT — VLM Pilot Results**: A 200-image VLM pilot was completed on DIQA-5000 using Claude Opus 4.6 vision (prompt v1.0):

- SRCC overall (all 200 images): 0.39 — below 0.65 target
- SRCC overall (non-rotated 104 images): 0.53 — closer but still below target
- Root cause: 48% of Q5 (highest MOS) images are rotated 90°. VLM penalizes rotation (scores 2.2-2.8); DIQA MOS does not. Rotation construct mismatch causes systematic label noise.
- Score compression: Only 11 unique overall values, max 3.5, 83% in 2.5-3.2 range (pre-normalization)
- SRCC sharpness: 0.58 (closer to target, demonstrating VLM can approach threshold for specific IQA dimensions)
- Independence check: PASSED (all non-overall pairs r < 0.8)
- Decision: Proceed with revised VLM prompt v2.0 (orientation-independent scoring + finer granularity); validate on 30-50 images; require SRCC > 0.60 before scaling to full Phase 1 pool

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Human MOS Available | VLM Path Status | Conf ≥ 0.7 | Usable (Today) | Usable (After Remediation) |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 (human MOS) | 5,500 | 5,499 (`overall_score` populated) | Pilot at SRCC=0.39 (all), 0.53 (non-rotated) | High — human ground truth | **5,499** | 5,499 |
| OHR-Bench | 8,500 | Quality scores (0-100) available natively — requires normalization + L2 population | VLM labeling not started; depends on prompt v2.0 validation | Not yet populated in L2 | **0** | ~8,500 (after L2 population) |
| RealDAE | 1,200 | Distorted/clean pairs; overall quality derivable from distortion type + severity | Not started | Not yet measured | **0** | ~1,200 (after derivation) |
| iqa_phase7_165k | EXCLUDED | EXCLUDED — dataset flawed | EXCLUDED | EXCLUDED | **0** | **0** |
| **Phase 1 total** | **15,200** | | | | **5,499** | **15,199** |

**Effective usable today**: 5,499 images (DIQA-5000 human MOS only). 34% of Phase 1 target.

### Phase 2 — Synthetic Pipeline (Self-Labeling)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are computed as a weighted average of the individual degradation parameters applied during Augraphy generation.

- **Base dataset**: synth-multiscript-v3 (350K images on GCS, 27 scripts, 60% color/30% grayscale/10% binarized, 80% modern/15% aged/5% historical)
- **Target**: 100,000 images derived from synth-multiscript-v3 with Augraphy degradation
- **Label provenance**: tier_0_exact (weighted average of recorded augmentation parameters: blur_sigma, noise_std, contrast_factor, skew_angle, jpeg_quality)
- **Aggregation formula**: overall_quality = weighted_mean(blur_score, noise_score, contrast_score, skew_score, compression_score) using domain-calibrated weights
- **Pipeline status**: NOT YET CREATED. Base dataset (synth-multiscript-v3) is ready on GCS.
- **Assembly gap**: Assembly script `prepare_multitask_datasets.py iqa` not yet implemented
- **Risk**: Weighted average may not align with human MOS perceptual weighting; calibration against Phase 1 human MOS required after Phase 1 assembly

### Usable Pool Summary

| Pool Component | Target | Current Usable | Gap |
| --- | --- | --- | --- |
| Phase 1 curated | 16,000 | 5,499 (DIQA-5000 MOS only) | 10,501 (OHR-Bench + RealDAE label population) |
| Phase 2 synthetic | 100,000 | 0 (pipeline not created) | 100,000 |
| **Combined** | **116,000** | **5,499** | **110,501** |

### VLM Validation Sampling Tier

- DIQA-5000: Tier 1 (max(10, 3%) per quality bucket) — 200-image pilot complete (SRCC=0.39 all, 0.53 non-rotated). Prompt v2.0 required. Gate: SRCC > 0.60 on 30-50 image validation before scaling to full dataset.
- OHR-Bench: Tier 2 (max(15, 10%)) — VLM labeling not started. Depends on prompt v2.0 passing DIQA-5000 gate first.
- RealDAE: Tier 3 (spot check only) — derivable from distortion metadata; VLM validation recommended on 50-image sample.
- Phase 2 synthetic: No VLM sampling needed — augmentation parameters are tier_0_exact ground truth.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| IQA-PILOT-ROTATION | DIQA-5000 | `llm_scores.predicted_normalized` | VLM penalizes rotated images; 48% of Q5 (highest MOS) images are 90° rotated; causes SRCC=0.39 all-image overall | OPEN — prompt v2.0 in development |
| IQA-PILOT-COMPRESSION | DIQA-5000 | `llm_scores.predicted_normalized` | Score compression: 83% of VLM scores fall in 2.5-3.2 range; only 11 unique values pre-normalization; insufficient granularity for regression training | OPEN — finer granularity and scale anchoring required in prompt v2.0 |
| IQA-OHRB-UNPOPULATED | OHR-Bench | `ml_image_quality.overall_score` | L2 field not populated; quality scores available (0-100 native format) but not written to L2 metadata | OPEN — requires L2 enrichment pass after prompt v2.0 validated |
| IQA-REALDAE-UNPOPULATED | RealDAE | `ml_image_quality.overall_score` | L2 field not populated; overall quality derivable from distortion type + severity parameters | OPEN — requires derivation logic and L2 enrichment pass |
| IQA-PHASE2-MISSING | synth-multiscript-v3 derived | N/A — label computed at generation time | Phase 2 pipeline script not yet created; 100K synthetic images not assembled | OPEN — blocking Phase 2 training path |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) — rotation construct mismatch: VLM penalizes rotation but human MOS is orientation-agnostic | CRITICAL — this head's VLM labeling path is blocked until prompt v2.0 achieves SRCC > 0.65 |
| IQA-KI-002 | Score compression in VLM output — 83% of pilot scores in 2.5-3.2 range (normalized: 0.50-0.64); insufficient dynamic range for Gaussian NLL regression training | HIGH — compressed labels will cause the model to learn near-constant output; prompt v2.0 must produce uniform score distribution |
| IQA-KI-003 | Phase 2 weighted-average aggregation formula not calibrated against human MOS | HIGH — if Phase 2 labels disagree with human perception weighting, the head will learn a different construct than intended by SRCC target |
| IQA-KI-004 | overall_quality Phase 2 labels are computed from individual G1 head augmentation parameters — risk of circular dependency if the training order allows G1-6 weights to influence G1-1 through G1-5 | MEDIUM — Phase 2 aggregation uses FIXED formula (not learned), mitigating circular dependency risk; formula must be explicitly documented and frozen before assembly |
| IQA-KI-005 | Binarized document (1-bit) label convention for overall_quality is undefined — 1-bit images have technically maximum contrast but may not represent "good" quality for OCR; human MOS for binarized images is unknown | MEDIUM — affects training on the 10% binarized fraction of synth-multiscript-v3; convention must be defined before Phase 2 assembly |

### Remediation Path

**Critical path sequence**:

1. Develop VLM prompt v2.0 (orientation-independent + fine-grained scale with anchoring examples) — 2 days
2. Validate prompt v2.0 on 30-50 DIQA-5000 images — gate: SRCC > 0.60; if failed, iterate before proceeding — 1 day
3. Scale VLM labeling to DIQA-5000 test split and OHR-Bench (gated on step 2) — 2-3 days
4. Populate RealDAE overall_quality via distortion-parameter derivation logic — 1 day
5. Implement Phase 2 assembly script (`prepare_multitask_datasets.py iqa`) with weighted-average aggregation formula — 3-4 days
6. Calibrate Phase 2 weighted-average formula against Phase 1 human MOS on DIQA-5000 validation split — 1-2 days
7. Run L2 enrichment on assembled manifests; re-run DDR to validate 14-dim coverage

**Total critical path estimate**: 10-13 days

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: Phase 1 partial (5,499 images with human MOS; 10,700 images have label sources but not yet populated in L2); Phase 2 not started (0/100,000)

**Target Count**: 16,000 (Phase 1) + 100,000 (Phase 2 synthetic) = 116,000 total

**Current Count**: 5,499 Phase 1 DIQA-5000 with human MOS; OHR-Bench + RealDAE not yet labeled in L2; Phase 2 pipeline not yet created

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 1 total images | 16,000 | 5,499 (DIQA-5000 MOS only) | ❌ 10,501 images gap (OHR-Bench labels missing, RealDAE labels missing) |
| Phase 2 total images | 100,000 | 0 | ❌ Not started |
| Phase 1 label tier | ≥80% tier_1 | DIQA-5000: tier_0_exact (human MOS) ✅; OHR-Bench: pending prompt v2.0 | ⚠️ OHR-Bench must reach tier_1 via prompt v2.0 VLM |
| Phase 1 VLM SRCC | ≥ 0.65 | 0.53 (non-rotated), 0.39 (all) | ❌ Below target — prompt v2.0 required |
| Phase 2 label source | Weighted avg of augmentation params | Not applicable (not yet created) | ✅ No external L2 dependency; but formula not yet calibrated |
| Phase 2 calibration | Aligned with Phase 1 MOS | Not validated | ⚠️ Calibration study required after Phase 1 assembly |
| DIQA-5000 coverage | 5,500 images | 5,499 labeled | ✅ Met |
| OHR-Bench coverage | 8,500 images | 0 labeled in L2 | ❌ Not started |
| RealDAE coverage | 1,200 images | 0 labeled | ❌ Not started |

**Blockers**:

1. VLM SRCC at 0.39 (all) / 0.53 (non-rotated) — below 0.65 target. Prompt v2.0 in development. Must validate on 30-50 images before scaling.
2. OHR-Bench L2 `ml_image_quality.overall_score` field not yet populated (native scores available but not written to L2).
3. RealDAE overall_quality derivation logic not yet implemented.
4. Phase 2 Augraphy synthetic pipeline not yet created.
5. Phase 2 weighted-average aggregation formula not yet calibrated against Phase 1 human MOS.

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` — not yet implemented

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall DDR Score**: 0.0/100 (automated — all dimensions show "Not measured"; this reflects metadata not loaded into DDR tool, NOT confirmed poor diversity)

**Estimated Actual Coverage** (analyst assessment based on known dataset composition):

| Dimension | L2 Field | Relevance | Target | Estimated Current | Estimated Score |
| --- | --- | --- | --- | --- | --- |
| degradation | `quality.degradations` | CRITICAL — overall_quality must integrate all IQA degradation signals; comprehensive degradation space is the core task | ≥6 degradation types across training set | DIQA-5000: diverse real degradations (blur, noise, contrast, JPEG); OHR-Bench: structured document degradations; Phase 2: augmentation-controlled. Overall: broad | 65/100 — real degradation diversity via DIQA + OHR-Bench is strong once labeled |
| capture_method | `capture_method.method` | HIGH — human MOS perception differs by capture method; camera documents are judged differently than flatbed scans; overall_quality must generalize across capture types | ≥3 capture methods represented | DIQA-5000: primarily scanned documents; OHR-Bench: mixed scan + camera; RealDAE: real degraded docs. Estimated: scanner-dominant | ⚠️ 45/100 — camera capture under-represented in Phase 1; Phase 2 synth-multiscript-v3 is born-digital |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs have different quality dimensions than color/grayscale; VLM quality perception differs significantly by color mode | ≥2 modes (color + grayscale; binarized as labeled edge case) | DIQA-5000: primarily grayscale/color; synth-multiscript-v3 Phase 2: 60% color/30% gray/10% binarized | ⚠️ 55/100 — not yet measured; Phase 2 will provide strong color_mode diversity |
| document_age | `image_properties.document_age` | HIGH — aged documents have holistic quality perception distinct from modern degraded docs; VLM may conflate aging artifacts with poor quality | ≥2 age classes (modern + aged) | synth-multiscript-v3: 80% modern/15% aged/5% historical; DIQA-5000: primarily modern scans | ⚠️ 50/100 — Phase 2 will provide aged/historical coverage; Phase 1 is modern-dominant |
| domain | `domain.level1` | MEDIUM — quality tolerance perception varies by domain (financial documents have different quality expectations than social media content) | ≥5 domains | DIQA-5000: varied document types (scientific, financial, general); OHR-Bench: multi-domain by design | 55/100 — moderate domain breadth via DIQA + OHR-Bench; unmeasured |
| script_code | `language.script_code` | MEDIUM-LOW — VLM quality perception should be largely script-agnostic; some risk of VLM bias toward Latin script documents | ≥3 script families | DIQA-5000: primarily Latin-script documents; Phase 2 synth-multiscript-v3: 27 scripts | ⚠️ 40/100 — Phase 1 is Latin-dominant; Phase 2 will add non-Latin coverage |
| resolution | `resolution.category` | MEDIUM — resolution affects perceived overall quality; model must disentangle resolution from degradation | ≥3 resolution tiers | DIQA-5000: varied DPI (target for resolution quality dataset); Phase 2: synth-multiscript-v3 covers 72-600 DPI tiers | 55/100 — expected adequate after Phase 2 assembly; unmeasured in Phase 1 |
| layout_type | `structure.layout_type` | LOW — layout type is not a primary driver of overall quality signal; quality is content-agnostic | ≥3 types | DIQA-5000: diverse document layouts; OHR-Bench: structured academic/government documents | 50/100 — moderate variety expected |

**14-Dimension Estimated Score**: 52/100 (analyst estimate across measured dimensions, weighted by relevance)

**Important caveat**: The DDR automated score of 0.0/100 will resolve to a meaningful number once the IQA manifest is populated and L2 metadata is loaded. The underlying source datasets (DIQA-5000, OHR-Bench, synth-multiscript-v3) have genuine diversity, but this cannot be confirmed by the automated tool until assembly is complete. Use estimated score (52/100) for HAR scoring; validate with DDR re-run after assembly.

---

## Section 5 — Wild Condition Coverage

**Overall DDR Score (curated)**: 8.3/100 (0 covered / 1 partial / 5 missing out of 6 conditions)

**Overall DDR Score (synthetic)**: 0.0/100 (dataset not assembled; 2 conditions defined, 0 covered)

| Wild Condition | L2 Field Evidence | Status | Gap | Phase 2 Coverage |
| --- | --- | --- | --- | --- |
| Multiply-distorted (≥5 simultaneous types) | `quality.degradations` with ≥5 entries | ❌ Missing | Neither DIQA-5000 nor OHR-Bench systematically covers extreme compound distortions — these are typically excluded from controlled MOS studies to maintain rating validity. The overall_quality model must generalize to compound distortions it was not trained on. | Phase 2 can PARTIALLY address: Augraphy allows ≥5 simultaneous augmentations. OOD-4a (500 images) provides evaluation. |
| Mobile phone motion blur + defocus combined | `quality.blur_type` = motion AND defocus | ⚠️ Partial | DIQA-5000 includes some motion blur cases but systematic coverage of the combined motion+defocus condition typical of handheld smartphone camera capture is limited. VLM pilot SRCC 0.58 on sharpness dimension suggests partial coverage. | Phase 2 Augraphy: motion blur + defocus can be applied; depends on implementation of synthetic augmentation script. |
| Book gutter shadow + page curvature combined | `geometric.warping_type` + `quality.shadow_severity` | ❌ Missing | Combination of spatially localized shadow gradient (hard gutter shadow) with page curl warping is absent from DIQA-5000 and OHR-Bench training data. OOD-4c specifically targets this scenario. | Phase 2: difficult to reproduce realistically with Augraphy synthetic approach; Augraphy shadow is flat, not gutter-gradient. |
| Aged/historical documents (yellowing, foxing, ink fading) | `image_properties.document_age` = aged/historical | ❌ Missing | DIQA-5000 is primarily modern scanned documents. OHR-Bench focuses on academic/government scans, not historical degradation. The perception of "quality" for aged documents differs from modern degraded docs (yellowing may not affect legibility). | Phase 2: synth-multiscript-v3 15% aged + 5% historical provides PARTIAL coverage; document_age profiles added to synth base. |
| Fax artifacts (halftone + noise cascade + dynamic range collapse) | `quality.degradations` with fax-characteristic profile | ❌ Missing | Neither Phase 1 dataset contains fax-generated documents. Fax has a distinct artifact profile (halftone moiré + noise cascade + dynamic range collapse to 1-2 gray levels) that is qualitatively different from standard compression noise. | Phase 2: Augraphy has fax-simulation capability; depends on whether this is included in the generation script. |
| Screen recapture (RGB aliasing + moiré pattern from LCD) | `capture_method` = camera_smartphone + display_artifact | ❌ Missing | Screen recapture introduces RGB sub-pixel aliasing and moiré from the camera-display interaction — not present in any IQA training dataset. OOD-Capture (3a, 200 images) provides evaluation but not training. | Phase 2: Augraphy cannot easily reproduce screen capture moiré; this wild condition will remain absent from training. |

**Wild Condition Coverage Score**: 8.3/100 (from DDR, curated dataset)

**Key gap for overall_quality**: The multiply-distorted condition (OOD-4a, 500 images) is the most critical stress test. A model trained primarily on single-type or light compound distortions may assign near-average overall_quality to cases where multiple severe distortions compound in non-linear ways (e.g., combining heavy blur + heavy JPEG + gutter shadow simultaneously).

**Phase 2 partial mitigation**: Augraphy can generate compound distortion synthetic images. The Phase 2 assembly script must explicitly sample from ≥5 simultaneous augmentation combinations at higher severity to address the multiply-distorted gap.

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**SIG-G1-6 Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 simultaneous types) | 500 | ✅ Direct — highest priority | Compound distortions (gutter-shadow + page_curl + defocus blur + noise + JPEG compression) test overall_quality as an integrating signal; human annotation required for all IQA head labels simultaneously; failure mode: overall_quality under/over-weights compound interactions |
| 4b. Watermarked documents | 100 | ✅ Direct | Watermarks affect overall perceived quality in context-dependent ways (government watermark on otherwise-clear document); tests whether overall_quality appropriately weights watermark severity vs. other quality dimensions |
| 4c. Book gutter shadow (hard shadow gradient) | 100 | ✅ Direct | Hard shadow gradient tests whether overall_quality responds appropriately to spatially localized but severe degradation; gutter shadow has a distinct gradient profile not in sd7k training data |
| 4d. Binarized (1-bit) documents | 100 | ✅ Direct | Binarized docs are absent from Phase 1 training; perceptual quality convention for 1-bit images (maximum contrast but no grayscale texture) must be defined and consistent between training (Phase 2) and OOD labels |
| OOD-Mixed (cascade failures) | ~200 (from 500 OOD-Mixed pool) | ✅ Indirect | Multi-distortion cascade scenarios including CJK handwriting + gutter shadow, binarized + extreme JPEG — test overall_quality under correlated multi-source degradation |

**OOD Acquisition Status**: Not started (Phase 4)

**OOD Design Quality Assessment**: The 4-sub-source design is well-specified and directly targets the key stress scenarios for overall_quality. The 500-image 4a multiply-distorted set is the most important — it specifically evaluates the compound distortion generalization gap. The design is adequate for its purpose.

**Critical OOD label requirement**: All 800 OOD-Degradation images require human annotation for `overall_quality` — classical detectors are insufficient for compound distortions. This represents a significant annotation effort that must be planned for.

**OOD Leakage Risk**: DIQA-5000 is in training (Phase 1). OOD-Degradation must use non-DIQA-5000 sources only. OHR-Bench test split must be withheld from Phase 1 training. Upscaled OOD (OOD-Resolution 6b) must use OHR-Bench test split or RealDAE, NOT DIQA-5000.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench + RealDAE (16,000 images); Phase 2: synthetic augmentation from synth-multiscript-v3

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independent per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| SIG-G1-1 (blur_score) | DIQA-5000 + OHR-Bench (Phase 1) + synth-multiscript-v3 (Phase 2) | overall_quality Phase 2 label uses blur_score as one component; must not create circular dependency if heads are trained jointly | ✅ Phase 1 labels are independently sourced (human MOS); Phase 2 aggregation formula is fixed (not learned); joint training uses per-head loss terms, not cross-head dependencies |
| SIG-G1-2 (noise_score) | Same pool | Same circular dependency risk | ✅ Same mitigation as G1-1 |
| SIG-G1-3 (contrast_score) | Same pool | Same circular dependency risk | ✅ Same mitigation |
| SIG-G1-4 (skew_score) | Same pool | Naming clarity: `skew_score` (G1) is a degradation severity metric 0-1; `skew_reg` (G3) is actual angle in degrees. These are entirely different constructs sharing similar name. | ✅ Label fields are distinct (`quality.skew_severity` vs `geometric.skew_angle_degrees`); training data is separate (IQA pool vs. skew dataset) |
| SIG-G1-5 (compression_score) | Same pool | Same circular dependency risk | ✅ Same mitigation |
| SIG-G3-2 (skew_reg) | Different datasets | No dependency; naming confusion documented above | ✅ No shared data; different head group |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits are well-defined. MEDIUM (Phase 2) — synthetic images must be SHA256-deduped against all other training sets via global split registry. MEDIUM (VLM labels) — VLM pilot images (200) from DIQA-5000 must remain in training split, not leaked to OOD or test sets.

**Label Convention**: overall_quality is 0-1 where 1.0 = perfect overall quality, 0.0 = unusable quality. Phase 1 human MOS is normalized from [1, 5] DIQA scale to [0, 1] using: `(MOS - 1) / 4`. Phase 2 weighted average uses fixed weights (not learned). Label conventions for the following edge cases MUST be documented before assembly:

1. **Rotation**: Rotation does NOT reduce overall_quality if geometric correction is applied downstream. VLM prompt v2.0 must explicitly score images as if already correctly oriented.
2. **Binarization**: 1-bit images — convention TBD (see IQA-KI-005). Recommended: label based on legibility (text sharpness, contrast) only; compression and noise dimensions not applicable.
3. **Watermarks**: Watermark presence reduces overall_quality in proportion to legibility impact; a subtle corner watermark on an otherwise-clear document should not reduce score below 0.7.
4. **Aged appearance**: Yellowing and foxing are historical artifact, not degradation in the legibility sense; aged docs with clear text should score 0.6-0.8, not 0.2.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| IQA-OVERALL-G01 | IQA-PILOT-ROTATION | **VLM prompt v1.0 SRCC below 0.65 target — rotation construct mismatch causes systematic label noise on 48% of high-MOS DIQA-5000 images.** SRCC=0.39 (all images), 0.53 (non-rotated). The VLM penalizes rotation as a quality flaw; human MOS does not. Since SigLIP 2 operates on pre-corrected images, training labels must score images in an orientation-independent manner. | VLM conflates geometric orientation with perceptual quality; human MOS raters ignore rotation when evaluating image quality; pilot used raw DIQA-5000 images without orientation-normalization. | Develop VLM prompt v2.0: (a) Explicit orientation-independence instruction ("Score as if the image is already correctly oriented"), (b) Scale anchoring with labeled examples at each 0.5-unit interval, (c) Domain-specific anchors (scan quality vs. camera quality). Validate on 30-50 DIQA-5000 images; require SRCC > 0.65 (gate) before scaling to full Phase 1 pool. | 3-4 days |
| IQA-OVERALL-G02 | IQA-OHRB-UNPOPULATED | **OHR-Bench `ml_image_quality.overall_score` L2 field not populated.** OHR-Bench provides 8,500 images with native quality 0-100 scores available but not written to L2 metadata. Without this field, 56% of the Phase 1 target pool is inaccessible to the assembly script. | L2 enrichment pipeline has not been run on OHR-Bench for the overall_score field; native quality scores exist but require normalization (0-100 → 0-1) and L2 field population. | (a) Normalize OHR-Bench native quality scores: `overall_score = raw_score / 100`; (b) Write to L2 metadata field `ml_image_quality.overall_score`; (c) Validate normalization preserves relative ordering (monotonicity check). This can proceed in parallel with IQA-OVERALL-G01, as it uses native scores not VLM. | 1-2 days |
| IQA-OVERALL-G03 | IQA-PHASE2-MISSING | **Phase 2 Augraphy synthetic pipeline not created.** 100,000 synthetic images with overall_quality pseudo-labels from augmentation parameters represent 86% of the total training target. Assembly script not implemented. | Data engineering effort deferred; base dataset (synth-multiscript-v3) is ready but the derivation pipeline for IQA augmented views has not been built. | Implement `prepare_multitask_datasets.py iqa` sub-command: (a) Sample 100K images from synth-multiscript-v3, (b) Apply Augraphy augmentation stack with recorded parameters (blur, noise, contrast, JPEG, skew), (c) Compute overall_quality = weighted_mean(blur_score, noise_score, contrast_score, skew_score, compression_score) using calibrated weights, (d) Write to manifest with `split_type` field and SHA256 dedup against global registry. Include ≥5 simultaneous augmentation combinations to address multiply-distorted wild condition gap. | 5-7 days |

### P1 Improvements (resolve before training evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| IQA-OVERALL-G04 | IQA-PILOT-COMPRESSION: VLM score compression — 83% of pilot scores in 2.5-3.2 range (pre-normalization); only 11 unique values; insufficient dynamic range for Gaussian NLL regression | Prompt v1.0 lacks calibration anchors; VLM defaults to conservative mid-range scores without examples to anchor the extremes | Include explicit scale anchors in prompt v2.0: examples of 0-0.5 quality (unusable), 0.5-0.75 (low quality, usable with caveats), 0.75-0.9 (good), 0.9-1.0 (excellent). Require the VLM to use the full scale and penalize compressed output distributions during validation. | 1-2 days (within prompt v2.0 work; included in G01 timeline) |
| IQA-OVERALL-G05 | Phase 2 weighted-average aggregation formula not yet calibrated against Phase 1 human MOS | Aggregation weights are assumed from literature, not empirically derived from this dataset | After Phase 1 assembly, compute Pearson correlation between weighted-average formula and human MOS on DIQA-5000 validation split; adjust weights by minimizing (formula_prediction - human_MOS)² on calibration set. Document final weights in assembly script as frozen constants. | 2-3 days |
| IQA-OVERALL-G06 | Label convention for binarized documents (1-bit) undefined | 1-bit images are perceptually distinct — maximum contrast but no texture, and binarization itself is an irreversible quality transformation | Define convention: `overall_quality` for 1-bit images = legibility score (text sharpness, binary edge quality, thresholding artifacts) in range [0.4, 1.0]; map augmentation severity to this range; document in assembly script and model card. Score 1.0 = clean binarization with sharp edges; 0.4 = heavily dithered or misthresholded. | 1 day |
| IQA-OVERALL-G07 | RealDAE overall_quality derivation logic not implemented | RealDAE provides distorted/clean pairs; overall quality must be derived from distortion type and severity rather than direct MOS | Implement derivation logic: `overall_quality = 1 - aggregate_distortion_severity`, where aggregate severity is weighted sum of detected distortion types from RealDAE distortion metadata. Validate against DIQA-5000 human MOS on matched distortion types. | 1-2 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| IQA-OVERALL-G08 | VLM inter-rater reliability not measured — single VLM model used for all labels | Run labeling on 100 images with two VLM configurations (different temperature or model variant); compute agreement; flag divergent labels for human review or exclusion |
| IQA-OVERALL-G09 | Domain-specific overall_quality weighting not explored — quality tolerance differs by document domain (financial: high bar; social media: tolerates low) | After training, analyze SRCC by domain; if per-domain calibration improves SRCC > 0.03, explore domain-conditioned quality head variant |
| IQA-OVERALL-G10 | Screen recapture wild condition will remain absent from training — Phase 2 Augraphy cannot reproduce RGB sub-pixel moiré | Document as known OOD gap; monitor model performance on OOD-Capture sub-source 3a (200 screen recapture images) |

---

## Section 9 — Multi-Model Consensus

**Status**: Complete (2026-02-23)

**Adequacy Rating (pre-consensus)**: Blocked — Phase 1 VLM labels blocked (SRCC below target), Phase 2 pipeline not assembled, wild condition coverage critically low

**Analyst Summary**: SIG-G1-6 (overall_quality) is the most empirically grounded head in the G1 group — the 200-image VLM pilot provides quantitative evidence about label quality that other G1 heads lack. The core challenge is not architectural (SigLIP 2 with Gaussian NLL is well-suited to the task) but data-quality: (1) the VLM labeling path for OHR-Bench is blocked by SRCC 0.39-0.53 (below 0.65 target), with a clear root cause (rotation construct mismatch) and a concrete remediation path (prompt v2.0 with orientation-independence + scale anchors); (2) Phase 2 100K synthetic pipeline does not exist; (3) wild condition coverage is critically low (8.3/100 curated). The positive signals are: DIQA-5000 provides 5,499 high-quality human MOS labels (tier_0_exact), the Phase 2 base dataset (synth-multiscript-v3) is ready on GCS, and the OOD design is well-specified. The head is blocked for production training but unblocked for baseline model development using DIQA-5000 human MOS alone (sufficient for a 5K-image baseline that validates the Gaussian NLL head architecture).

**Consensus Prompt (Summary)**: "Evaluate the training dataset design and label strategy adequacy for SIG-G1-6 (overall_quality). Key questions: (1) Is dual-path label strategy adequate — can DIQA-5000 human MOS (5,499 images) serve as primary training signal if OHR-Bench VLM labeling is delayed? (2) Is VLM SRCC gap (0.53 vs. 0.65) a P0 blocker or P1, given SigLIP sees pre-corrected images? (3) Can Phase 2 synthetic augmentation-parameter-derived labels compensate for Phase 1 label quality issues? (4) Is OOD-Degradation design (800 images, 4 sub-sources) adequate? (5) Overall rating: Ready / Needs Work / Blocked?"

**Models consulted**: google/gemini-2.5-pro (neutral, confidence 9/10), google/gemini-3-pro-preview (neutral, confidence 9/10)

---

### Consensus Summary

**Unanimous rating: BLOCKED / NEEDS WORK** (both models, confidence 9/10)

**Q1 — Can DIQA-5000 human MOS alone serve as primary training signal?**

Both models agree: DIQA-5000 5,499 human MOS labels are the project's most reliable asset and CAN serve as the primary training signal for a baseline model. This enables a "DIQA-First" development track that de-risks the project from VLM labeling delays. However, 5,499 images is insufficient for the full production model — OHR-Bench population is required to reach the 16K Phase 1 target and achieve adequate diversity.

Gemini 2.5 Pro specifically recommends the DIQA-First approach: train an initial model on DIQA-5000 + RealDAE to establish baseline performance, then scale to full Phase 1 after VLM labeling is validated.

**Q2 — Is VLM SRCC gap (0.53 vs. 0.65) a P0 blocker or P1?**

Both models: **P0 blocker for the VLM labeling path to OHR-Bench**, but NOT a blocker for training on DIQA-5000 human MOS (which is independent of VLM). The distinction is important:

- VLM labels for OHR-Bench are blocked until SRCC ≥ 0.65 is demonstrated on prompt v2.0
- DIQA-5000 human MOS labels are already available and can train the head immediately
- The rotation construct mismatch is a label-generation problem, not a model-architecture problem; SigLIP seeing pre-corrected images actually reduces the risk once labels are correctly generated

Gemini 3 Pro flags an additional concern: VLM score compression (83% in 2.5-3.2 range) makes the Phase 1 VLM labels nearly useless for regression training even if SRCC improves — the dynamic range of training labels must cover the full 0-1 scale.

**Q3 — Can Phase 2 synthetic labels compensate for Phase 1 label quality issues?**

Both models: **Partially yes, with significant caveats**. Phase 2 tier_0_exact labels (exact augmentation parameters) are the highest-confidence label path for the individual degradation heads (G1-1 through G1-5). For overall_quality specifically:

- The weighted-average aggregation formula assumes perceptual weights that may not match human MOS — empirical calibration against DIQA-5000 human MOS is required before Phase 2 labels are used
- Gemini 3 Pro flags that the strict Phase 1 / Phase 2 data separation may be a strategic error — Phase 1 curated data should potentially contribute silver labels (classical IQA detectors) to the individual degradation heads, bridging the sim-to-real gap
- Phase 2 cannot address wild conditions that Augraphy does not model (screen recapture moiré, gutter shadow gradient, fax artifacts)

**Q4 — OOD-Degradation design adequacy**

Both models: **Design is adequate and well-targeted**. The 4 sub-sources (4a multiply-distorted 500, 4b watermarked 100, 4c gutter shadow 100, 4d binarized 100) cover the most important stress scenarios for overall_quality. The 500-image 4a multiply-distorted set is the most critical and correctly prioritized. Two caveats:

- All 800 OOD-Degradation images require human annotation for overall_quality labels — classical detectors are insufficient for compound distortions; this annotation effort must be planned
- 800 images is minimally sufficient for statistical validity of SRCC measurement; Gemini 3 Pro recommends scaling to ~2,000 for more robust regression evaluation

**Q5 — Overall adequacy rating**

Unanimous: **BLOCKED** on production training path; **NEEDS WORK** on baseline development path.

- Production training (target SRCC ≥ 0.65): BLOCKED — VLM labeling path SRCC below target, Phase 2 not assembled, wild condition coverage critically low
- Baseline development (DIQA-5000 only): UNBLOCKED — 5,499 human MOS labels can train a baseline head; useful for validating Gaussian NLL architecture and establishing lower-bound performance

**Final Rating**: ❌ BLOCKED (production) / ⚠️ NEEDS WORK (baseline track available)

**Top Recommendations** (priority order):

1. **Develop VLM prompt v2.0** (orientation-independent + fine-grained scale with anchors) — 3-4 days. Gate: SRCC > 0.65 on 30-50 DIQA-5000 images before scaling. This is the single most important action to unblock Phase 1 OHR-Bench labeling.
2. **Populate OHR-Bench L2 field** using native quality scores (normalize 0-100 → 0-1) — 1-2 days. This can proceed in parallel with prompt v2.0 development since it uses native scores, not VLM.
3. **DIQA-First baseline model** — train on 5,499 DIQA-5000 + 1,200 RealDAE (after derivation logic) to validate architecture and establish performance baseline while VLM path is being fixed — 1 day setup.
4. **Implement Phase 2 assembly script** (`prepare_multitask_datasets.py iqa`) with weighted-average aggregation and Augraphy augmentation stack including ≥5 simultaneous augmentation combinations — 5-7 days.
5. **Calibrate Phase 2 weighted-average formula** against DIQA-5000 human MOS after Phase 1 baseline training — 2-3 days.

---

### Scoring Summary

| Component | Weight | Raw Score | Rationale | Weighted |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 48 | Phase 1 usable today = 5,499/16,000 (34%), high-quality human MOS. OHR-Bench has native scores available but not in L2. VLM SRCC below target blocks OHR-Bench labeling path. Phase 2 not assembled. Score reflects strong DIQA-5000 anchor (high quality) offset by massive count gap (Phase 2 absent = 86% of total missing). | 16.8 |
| 14-Dimension Coverage | 25% | 25 | DDR automated = 0/100 (metadata not loaded). Analyst estimate 52/100 for actual diversity based on known dataset composition, but using conservative midpoint (25) to reflect uncertainty and unverified status. Phase 2 assembly will add synth-multiscript-v3 diversity (scripts, color modes, document ages). | 6.25 |
| Wild Condition Coverage | 20% | 8 | DDR curated = 8.3/100 (0 covered / 1 partial / 5 missing). Synthetic DDR = 0/100 (not assembled). Using DDR value directly as this is the most reliable measurement available. Phase 2 Augraphy partially addresses multiply-distorted and motion blur; screen recapture and fax remain unaddressed. | 1.60 |
| OOD Design Quality | 20% | 60 | 4 sub-sources with 800 total target images. Design is well-specified and directly relevant. Score capped from 100 because: (a) 0 images acquired; (b) all 800 OOD images require human annotation (not planned); (c) 800 images is minimally sufficient for SRCC reliability. | 12.00 |
| **Overall** | 100% | — | — | **36.65** |

**Grade**: ❌ Blocked (37/100)

**Score rationale**:

- Source Pool Adequacy (48): DIQA-5000 human MOS (5,499 images at tier_0_exact quality) is a strong foundation, but represents only 5% of the combined 116K target. OHR-Bench and RealDAE have label sources but require population effort. Phase 2 100K is entirely absent. Score reflects the asymmetry between label quality (high for what exists) and label completeness (very low overall).
- 14-Dimension Coverage (25): The automated DDR score is 0 due to metadata loading failure, not confirmed poor diversity. Conservative midpoint score reflects genuine uncertainty. Actual underlying diversity (DIQA-5000, OHR-Bench, synth-multiscript-v3 base) is estimated at 52/100 by analyst but unvalidated.
- Wild Condition Coverage (8): DDR score taken at face value. The curated Phase 1 pool has severe wild condition gaps — 5 of 6 defined conditions are missing. This is the most concerning dimension for production reliability.
- OOD Design Quality (60): Well-designed category with directly relevant sub-sources. Significantly penalized because 0 of 800 target images are acquired and human annotation for compound distortions is unplanned. OOD-Mixed provides additional evaluation scenarios.
