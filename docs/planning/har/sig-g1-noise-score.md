# Head Adequacy Review: noise_score (SIG-G1-2)

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
| Head ID | SIG-G1-2 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | noise_score |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | SRCC ≥ 0.65 with classical noise estimation or human annotations |
| Primary L2 Field | `ml_image_quality.noise_score` (Phase 1) OR augmentation parameter (Phase 2) |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench + RealDAE) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: VLM scores → L2 field (classical path blocked); Phase 2: Gaussian noise sigma parameter → tier_0_exact label |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.noise_score` (float 0-1; Phase 1) / Gaussian noise sigma augmentation parameter (Phase 2)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better) for Phase 1 VLM labels

**Label Provenance**: Phase 1: tier_1_annotation (VLM) — classical path BLOCKED by zero-variance defect; Phase 2: tier_0_exact (augmentation sigma is ground truth by construction)

**Label Convention**: noise_score is 0-1 where 1.0 = clean (sigma = 0), 0.0 = severe noise (sigma ≥ max_sigma = 30.0). This is the INVERSE of noise severity: `score = 1.0 - clamp(sigma / 30.0, 0, 1)`.

**Classical Noise Detector Analysis**: The `NoiseDetector` in `iqa_classical.py` uses wavelet-based MAD (Median Absolute Deviation) on the HH (diagonal detail) subband of a level-1 Daubechies (`db1`) wavelet decomposition. The formula is `sigma = MAD / 0.6745` (consistency constant for Gaussian distribution). The code implementation is **technically correct**. However, the VLM pilot study confirmed "zero variance" in detector output on DIQA-5000. The root cause is dataset-level: DIQA-5000 consists predominantly of clean/low-noise scanned documents, causing the MAD estimator to output near-constant low-sigma values with near-zero cross-image variance. This is not a code bug — it is a signal property of the target population. The detector works correctly on synthetically-noisy images; it cannot discriminate mild real-world scan noise against a baseline of clean scans.

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | Not populated | 0% | Unknown | C — classical path blocked | Blocked (VLM labeling required) |
| OHR-Bench | 8,561 | Not populated | 0% | Unknown | Not assessed | Blocked (VLM labeling required) |
| RealDAE | 1,200 | Not populated | 0% | Unknown | Not assessed | Blocked (VLM labeling required) |
| **Total Phase 1** | **15,261** | **0** | **0%** | — | — | **0 usable until VLM labeling completes** |

**DIQA-5000 note**: SigLIP 2 was pre-trained on DIQA-5000 achieving VQualA 0.886. The dataset contains human MOS for overall, sharpness, and color — but NOT a separate noise dimension. VLM scoring is the only available path to populate `ml_image_quality.noise_score` for Phase 1 images.

**OHR-Bench note**: Contains page-level quality scores 0-100 across 7 domains. Does not contain a noise-specific sub-score. VLM labeling required.

### Phase 2 — Synthetic Pipeline (Self-Labeling)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are generated from augmentation parameters at creation time. The Gaussian noise standard deviation (sigma) applied during augmentation is the ground-truth label, normalized to [0,1].

- **Target**: 100,000 synthetic images via Augraphy/augmentation pipeline applied to synth-multiscript-v3 base
- **Label provenance**: tier_0_exact (Gaussian noise sigma recorded at generation time)
- **Normalization**: `noise_score = 1.0 - clamp(noise_sigma / 30.0, 0, 1)` (max_sigma=30.0 aligns with classical detector)
- **Noise types to cover**: Gaussian (primary), salt-and-pepper (secondary), scan speckle (tertiary)
- **Pipeline status**: Not yet created (0/100,000 images)
- **Augraphy support**: `OneOf([GaussianNoise, SaltAndPepperNoise])` is supported; sigma range 0-25 maps to score range 0.17-1.0

### Usable Pool Summary

- **Phase 1 usable**: 0 images (VLM labeling not yet run; classical path blocked)
- **Phase 1 target**: 15,261 images (all usable once VLM labeling completes)
- **Phase 2 usable**: 0 (pipeline not yet created)
- **Phase 2 target**: 100,000 images
- **Combined gap**: 15,261 Phase 1 images awaiting VLM labeling + 100,000 Phase 2 images not yet built

### VLM Validation Sampling Tier

- Phase 1 DIQA-5000: **Tier 1 REQUIRED** — noise-specific VLM SRCC must be measured before bulk labeling. Target: run targeted VLM pilot on 200 images covering full noise severity range (inject synthetic noise at known sigma to validate VLM can estimate sigma from visual features). Accept if SRCC ≥ 0.55 (lower threshold acceptable if Phase 2 provides primary training signal).
- Phase 1 OHR-Bench: **Tier 2** — bulk VLM labeling after pilot validates SRCC.
- Phase 2: No VLM sampling needed (augmentation parameters are ground truth).

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| IQA-NOISE-DEF-01 | DIQA-5000, OHR-Bench, RealDAE | `ml_image_quality.noise_score` | L2 field not populated for any Phase 1 dataset | OPEN — blocks Phase 1 assembly |
| IQA-NOISE-DEF-02 | DIQA-5000 | `classical_noise_sigma` | Classical noise detector (wavelet MAD) produces near-constant near-zero output on clean document population — zero variance on DIQA-5000 test population | OPEN — structural dataset property, not code bug; classical path unusable as Phase 1 label source |
| IQA-NOISE-DEF-03 | All | Phase 2 pipeline | Gaussian noise augmentation pipeline does not exist | OPEN — 0/100K images generated |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) for overall_quality — noise-specific VLM SRCC unmeasured | HIGH — noise-specific SRCC may differ; pilot required before bulk labeling |
| IQA-KI-NOISE-CLASS | Classical noise detector has near-zero variance on clean document population (DIQA-5000) — cannot be used for Phase 1 labeling or Phase 1/OOD cross-validation | CRITICAL — sole classical labeling path is blocked |
| IQA-KI-NOISE-SIM | Gaussian/S&P augmentation (Phase 2) does not capture real-world scanner speckle, photocopier artifacts, or JPEG high-frequency noise patterns — different spectral properties from true sensor noise | MEDIUM — sim-to-real gap risk for production documents |

### Remediation Path

1. Immediate P0: Run VLM noise-specific pilot on 200 DIQA-5000 images (inject known sigma, measure SRCC of VLM noise score vs. known sigma). Validates whether VLM can perceive noise severity independently of rotation/clarity conflation.
2. Immediate P0: Build Phase 2 augmentation pipeline (inject Gaussian + S&P noise into synth-multiscript-v3 images at parameterized sigma, record sigma as label, normalize to noise_score).
3. Once pilot SRCC ≥ 0.55: Run bulk VLM labeling on DIQA-5000 + OHR-Bench + RealDAE; populate `ml_image_quality.noise_score`.
4. Expand Phase 2 beyond Gaussian/S&P: Add scan speckle simulation (structured noise), JPEG high-frequency ringing as a third noise subtype, to reduce sim-to-real gap.

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: ❌ Not started (Phase 1: 0/15,261 labeled; Phase 2: 0/100,000 created)

**Target Count**: 15,261 (Phase 1) + 100,000 (Phase 2 synthetic) = 115,261 total

**Current Count**: 0 labeled images (Phase 1 VLM not run; Phase 2 pipeline not built)

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 1 total images | 15,261 | 0 labeled | ❌ VLM labeling not run |
| Phase 2 total images | 100,000 | 0 | ❌ Pipeline not created |
| Phase 1 label tier | ≥80% tier_1_annotation | 0% | ❌ Not started |
| Phase 2 label source | Augmentation params (noise sigma) | Not applicable — self-labeling | ✅ No L2 dependency once pipeline exists |
| DIQA-5000 coverage | 5,500 images | 5,500 available (0 labeled) | ⚠️ Images available, labels missing |
| OHR-Bench coverage | 8,561 images | 8,561 available (0 labeled) | ⚠️ Images available, labels missing |
| RealDAE coverage | 1,200 images | 1,200 available (0 labeled) | ⚠️ Images available, labels missing |

**Blockers**:

- VLM labeling SRCC for noise_score not yet measured independently.
- Classical noise detector has near-zero variance on clean document population — cannot serve as Phase 1 label source.
- OHR-Bench, DIQA-5000, RealDAE L2 `ml_image_quality.noise_score` fields not populated.
- Phase 2 Augraphy/augmentation pipeline not yet created.

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` — IQA sub-command not yet implemented. Must record noise_sigma per image at generation time for Phase 2.

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 0.0/100 (DDR automated score — L2 metadata not populated on assembled datasets; all dimensions report "Not measured")

**Analyst note**: The DDR 0.0/100 reflects missing L2 enrichment on the iqa-curated and iqa-synthetic manifests, NOT confirmed poor diversity. DIQA-5000 source documents span multiple scan conditions; OHR-Bench spans 7 domains. However, until L2 enrichment is run on the assembled manifest, no dimension can be formally scored. The per-dimension assessments below reflect analyst estimates from source dataset documentation.

**Critical noise-specific dimension interactions**: Noise characteristics vary dramatically by capture method (scanner CCD horizontal banding vs. camera sensor ISO grain), resolution (noise appears larger at lower DPI), and color mode (grayscale noise is perceptually more visible than color; binarized images have noise transformed to pixel-flip errors). These three dimensions are jointly important for this head.

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| degradation | `quality.degradations` | CRITICAL — noise is the core target degradation; training set must span 0-1 range with verified real examples at each severity level | ≥4 noise severity levels (clean/mild/moderate/severe); noise must cover full score range | Unknown — DIQA-5000 predominantly clean documents; Phase 2 will add full range via augmentation params | ⚠️ 30/100 — Phase 1 likely skewed toward clean; Phase 2 will address range gap |
| capture_method | `capture_method.method` | HIGH — scanner CCD noise (horizontal banding, structured) vs. camera ISO noise (random, orientation-invariant) vs. born-digital (no inherent noise) have fundamentally different spectral characteristics | ≥3 capture methods; ≥20% scanner, ≥20% camera, ≥20% born-digital | Estimated: DIQA-5000 scanner-dominant; OHR-Bench mixed; RealDAE camera-included; Phase 2 synth-multiscript-v3 covers born-digital + synthetic | ⚠️ 45/100 — scanner and born-digital likely adequate; camera coverage uncertain |
| color_mode | `image_properties.color_mode` | HIGH — grayscale noise is more perceptually prominent than color noise (chroma masking effect); binarized images convert noise to pixel-flip errors that look different from continuous noise | ≥2 modes (color + grayscale ≥10% each); binarized as edge case | Estimated: DIQA-5000 mixed; synth-multiscript-v3 base: 60% color, 30% grayscale, 10% binarized — adequate once Phase 2 pipeline applies noise augmentation across all color modes | ✅ 60/100 — synth-multiscript-v3 base provides good color_mode spread |
| resolution | `resolution.category` | HIGH — noise-to-signal ratio varies with resolution; same sigma noise at 72 DPI has larger relative impact than at 300 DPI; noise score must account for DPI when interpreting sigma | ≥3 resolution tiers (low/standard/high) | Estimated: DIQA-5000 standardized at 300 DPI; Phase 2 can span multiple DPI tiers using synth-multiscript-v3 multi-DPI rendering | ⚠️ 40/100 — Phase 1 likely single-DPI; Phase 2 needs explicit multi-DPI noise injection |
| document_age | `image_properties.document_age` | MEDIUM — aged documents exhibit grain, foxing, and organic speckle patterns that resemble but differ from sensor noise; label ambiguity risk | ≥2 age classes (modern ≥80%, aged ≥5%) | Estimated: synth-multiscript-v3 base: 80% modern, 15% aged, 5% historical — adequate | ✅ 65/100 — synth-multiscript-v3 base covers aged/historical adequately |
| domain | `domain.level1` | MEDIUM — background complexity affects noise perception and wavelet-based estimation; dense text pages have different noise profiles from blank forms | ≥5 domains represented | Estimated: OHR-Bench spans 7 domains; DIQA-5000 spans mixed document types; adequate | ✅ 60/100 — estimated adequate via source dataset breadth |
| script_code | `language.script_code` | MEDIUM — CJK fine strokes (hairlines) are more susceptible to noise than Latin strokes; noise-to-stroke-width ratio matters for OCR impact | ≥3 script families | Estimated: DIQA-5000 likely Latin-dominant; synth-multiscript-v3 provides 27 scripts; adequate for Phase 2 | ⚠️ 50/100 — Phase 1 likely imbalanced; Phase 2 adequate |
| layout_type | `structure.layout_type` | LOW — layout type is not a primary driver of noise characteristics; uniform backgrounds may show noise more prominently | ≥3 types | Estimated: diverse across source datasets | ⚠️ 50/100 — estimated adequate but unmeasured |

**Analyst note on diversity gaps**: The most critical dimension gap is `degradation` coverage at the severe noise end (scores < 0.3). Phase 1 DIQA-5000 is a predominantly clean-document dataset; it will not provide training signal for the high-noise range. Phase 2 synthetic augmentation is essential to cover the full 0-1 range. The `capture_method` dimension is also important: scanner CCD noise profiles must be represented to handle real-world scan artifacts.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 8.3/100 (DDR automated score for iqa-curated; 0.0/100 for iqa-synthetic)

**Analyst note**: The DDR scores reflect that 5 of 6 curated wild conditions are MISSING and all synthetic wild conditions are MISSING. These gaps are material for a noise_score head because several critical real-world noise sources cannot be replicated by simple Gaussian/S&P augmentation.

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Sensor noise — camera ISO grain (high-frequency, random spatial, orientation-invariant) | `capture_method = camera_smartphone` + `quality.noise_sigma` | ⚠️ Partial | RealDAE provides some camera-captured documents. Phase 1 pool may lack high-ISO noise examples at scale. Camera grain has spectral properties distinct from scanner noise; training on scanner-noise-only images may cause underfitting on camera captures. |
| Scanner CCD noise — horizontal banding (structured, anisotropic) | `capture_method = scanner_flatbed` + `quality.noise_subtype` | ❌ Missing from Phase 2 | Phase 2 augmentation uses isotropic Gaussian noise. Real scanner banding is anisotropic (horizontal streaks from CCD read noise). This structured pattern has different frequency content than Gaussian noise. The model must learn to score anisotropic structured noise, but Phase 2 does not include this subtype. |
| JPEG compression high-frequency artifacts (DCT block ringing, false noise perception) | `quality.compression_score` | ⚠️ Indirect | JPEG compression creates high-frequency block boundaries that the wavelet MAD detector misclassifies as noise (confirmed: the classical detector conflates JPEG artifacts with noise). Phase 1 includes JPEG-compressed images; training on both clean and JPEG-compressed images with distinct noise_score labels is required to avoid conflation. OOD-Degradation 4a (multiply-distorted) will include JPEG compression. |
| Photocopier speckle (random black specks from toner/platen contamination) | `capture_method.method` | ⚠️ Partial | Photocopier speckle differs from Gaussian noise: sparse discrete black specks on a white background. Salt-and-pepper noise in Phase 2 is a reasonable approximation. OOD-Capture 3c (4th-generation photocopies) will stress-test this. |
| Aged document grain and foxing (organic, brown-yellow, non-uniform) | `image_properties.document_age` | ⚠️ Partial | Aged documents exhibit foxing (orange-brown irregular spots) and grain (fine texture from paper degradation). These do not resemble Gaussian noise but will be scored by the noise_score head. Label ambiguity: is foxing "noise" or "texture"? Requires explicit labeling convention. synth-multiscript-v3 aged/historical profile covers some degradation but not foxing patterns. |
| Binarized documents — noise signal transformed to pixel-flip errors | `image_properties.color_mode = binarized` | ❌ Not in Phase 1 training | OOD-4d specifically tests binarized color_mode. Binarized documents have no continuous noise — quality degrades via pixel errors. The noise_score convention for binarized documents is undefined: should a clean binarized document score 1.0 (clean) or score as undefined? Labeling convention must be established before training. |
| Combined noise + blur (sensor noise in dark/low-light captures) | `quality.blur_score + quality.noise_sigma` | ❌ Missing | Low-light camera captures produce both defocus blur AND high-ISO sensor noise simultaneously. The noise_score head must learn to estimate noise severity even when blur co-occurs. Phase 2 adds noise to clean/sharp images only; it does not simulate the noise+blur interaction. |
| Screen recapture moiré and RGB aliasing (appears as structured noise) | `capture_method = screen_recapture` | ❌ Missing | Screen recapture creates moiré patterns from pixel grid aliasing. These high-frequency structured patterns will be scored as high noise by any spectral estimator. No training or OOD coverage — OOD-Capture 3a tests this but does not have training analog. |

**Analyst gap summary**: Phase 2 synthetic augmentation (Gaussian + S&P) addresses random isotropic noise but misses: (1) structured anisotropic scanner banding, (2) JPEG artifact-noise conflation, (3) aged document organic grain, (4) combined noise+blur, and (5) screen recapture moiré. These represent 5 of the 8 real-world noise wild conditions and collectively constitute a significant sim-to-real gap that Phase 1 real-world data (once labeled) would partially close.

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types) | 500 | ✅ Direct | Compound distortions include noise; noise_score must be evaluated amid blur, compression, shadow, and gutter curl co-occurring. IQA labels require human annotation (classical detector cannot be used for OOD ground truth — zero variance defect extends to OOD). |
| 4b. Watermarked documents | 100 | ⚠️ Indirect | Watermark texture may be misidentified as noise in fine-texture regions. Noise_score should remain high (near 1.0) for a cleanly watermarked document — but wavelet-based noise estimation may confuse repetitive watermark patterns with noise energy. |
| 4c. Book gutter shadow | 100 | ⚠️ Indirect | Shadow regions may exhibit apparent noise from low-signal areas; secondary effect. Tests robustness of noise scoring in non-uniform illumination. |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | color_mode=binarized absent from Phase 1 training. Noise signal is fundamentally transformed post-binarization (continuous noise → pixel-flip errors). Label convention must be established before OOD acquisition. |
| OOD-Capture 3c (4th-gen photocopies) | 150 | ✅ Direct (cross-category) | Iterative photocopy speckle; most authentic real-world noisy document scenario. This is the best real-world noise stress test available in the OOD catalog. |
| OOD-Mixed cascade | 500 | ⚠️ Indirect | Multi-distortion compounds including noise-inducing degradations. |

**OOD Acquisition Status**: Not started (Phase 4). 0/800 images acquired.

**Critical OOD labeling constraint**: Classical noise detector CANNOT be used for OOD ground truth labels (zero-variance defect on clean-to-moderate noise range). OOD-Degradation (4a) multiply-distorted images require human annotation for noise_score labels. This extends the P0 blocker: OOD evaluation cannot begin until a validated labeling method (VLM or human MOS) exists for real-world images.

**OOD Leakage Risk**: DIQA-5000 and OHR-Bench are in training. OOD-Degradation must use non-DIQA-5000 sources only. RealDAE test split must be withheld from Phase 1 training. Cross-category OOD-Capture 3c (photocopies) uses training-excluded source documents.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench + RealDAE (15,261 images); Phase 2: synthetic augmentation of synth-multiscript-v3

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independent per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| All other G1 heads (G1-1, G1-3 to G1-6) | DIQA-5000 + OHR-Bench + RealDAE | Multi-label independence required; labels must not be derived from each other | ✅ Each head's label is independently computed from MOS/VLM/augmentation params |
| SIG-G1-1 (blur_score) | Same dataset | Gaussian blur applied during augmentation changes frequency content; wavelet detector may conflate blur and noise. In training, noise+blur compound augmentation must be labeled separately for each head. | ⚠️ Phase 2 must apply noise and blur augmentations independently; combined images must have separate noise_score and blur_score labels |
| SIG-G1-3 (contrast_score) | Same dataset | Low contrast images (faded scans) may have elevated noise perception; label correlation risk in faded + noisy images | ⚠️ VLM prompt must score noise and contrast independently on same images; validate independence of Phase 1 labels |
| SIG-G1-6 (overall_quality) | Same dataset | overall_quality may use weighted average of other G1 scores — risk of circular dependency if G1-6 labels derived from G1-2 labels | ⚠️ Ensure G1-6 labels are independent human MOS, not derived from G1-2 predictions |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits are defined. MEDIUM (Phase 2) — synthetic images must be SHA256-deduped against all other training sets (synth-multiscript-v3 is also used for script-detection training).

**Label Convention**: noise_score is 0-1 float where 1.0 = perfect quality (no noise), 0.0 = severe degradation (maximum noise). This is **INVERSE of noise sigma** (sigma=0 → score=1.0; sigma≥30 → score=0.0). The `normalize_noise_score()` function in `iqa_classical.py` implements this correctly with `max_sigma=30.0`.

**Binarized image convention**: Undefined. Must be resolved before training: Option A — label as 1.0 (binarization removes continuous noise); Option B — exclude from training and flag as OOD-edge-case; Option C — label based on pixel error density. Recommendation: Option A (label = 1.0) with `color_mode=binarized` flag in manifest, rely on other G1 heads for binarization quality signals.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| IQA-NOISE-G01 | IQA-NOISE-DEF-02 | **Classical noise detector has near-zero variance on clean document population — blocks ALL Phase 1 labeling and OOD ground truth.** The wavelet MAD detector correctly measures sigma but DIQA-5000's predominantly clean document population produces near-constant near-zero sigma, yielding zero cross-image variance. This is a dataset-level property, not a code bug. It prevents using classical detection as Phase 1 label source or as cross-validation signal. The same defect propagates to OOD: OOD-Degradation labels also cannot use the classical detector. | DIQA-5000 is a clean-document quality benchmark; its images have naturally low noise. The wavelet MAD estimator is correct for the images it was designed for, but has zero discriminative power on a low-noise population. | (a) Run targeted VLM noise-specific pilot (200 images with injected synthetic noise at known sigma; measure VLM SRCC vs. known sigma). If SRCC ≥ 0.55, proceed with bulk VLM labeling as Phase 1 label source. (b) Alternative: use DIQA-5000 human MOS "sharpness" dimension as proxy (sharpness correlates with low noise); map to noise_score with validated linear regression. For OOD labeling: human annotation required (VLM or expert). | Medium — 3-5 engineer-days for VLM pilot + bulk labeling + OOD annotation design |
| IQA-NOISE-G02 | IQA-NOISE-DEF-01 | **Phase 1 L2 field `ml_image_quality.noise_score` not populated for any source dataset.** DIQA-5000, OHR-Bench, and RealDAE all have zero records with this field populated. Phase 1 assembly script requires this field. | VLM labeling pipeline has not been run against these datasets for the noise_score dimension. DIQA-5000 VLM pilot focused on overall_quality; noise-specific VLM scoring has not been validated. | Run VLM labeling pipeline on DIQA-5000 + OHR-Bench + RealDAE after validating noise-specific SRCC ≥ 0.55. Estimated: 16K images × VLM batch rate. | Medium — 2-3 engineer-days (plus VLM compute cost) |
| IQA-NOISE-G03 | IQA-NOISE-DEF-03 | **Phase 2 Augraphy synthetic pipeline does not exist** — 0/100,000 images generated. The Phase 2 label strategy (tier_0_exact from noise sigma) is well-designed but requires implementation. | IQA sub-command in `prepare_multitask_datasets.py` not implemented. Augraphy noise augmentation parameters and normalization scheme are defined but no generation script exists. | Implement `scripts/prepare_multitask_datasets.py iqa` sub-command: iterate synth-multiscript-v3 images, apply `OneOf([GaussianNoise(sigma=u), SaltAndPepperNoise(amount=v)])` with u sampled from [0, 28] and v from [0, 0.05]; record sigma (or amount) as noise_score ground truth. Include all DPI tiers and color_modes from synth-multiscript-v3. | Medium — 2-3 engineer-days for augmentation script + 3-5 hours GPU generation time |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| IQA-NOISE-G04 | **Noise-specific VLM SRCC has not been measured independently.** The VLM pilot measured overall_quality SRCC (0.39 all / 0.53 non-rotated). Noise-specific scoring may behave differently — noise is a more concrete perceptual attribute than overall quality, which may yield better SRCC. Until measured, the viability of VLM as Phase 1 label source is uncertain. | VLM pilot was designed for overall_quality, not dimension-specific scoring. | Run targeted VLM pilot: 200 DIQA-5000 images with injected Gaussian noise at sigma ∈ {0, 3, 6, 10, 15, 20, 25}. Ask VLM to score noise severity specifically. Compare VLM output vs. known sigma (SRCC). Report noise-specific SRCC separately from overall SRCC. | Low — 1-2 engineer-days (VLM pilot execution + analysis) |
| IQA-NOISE-G05 | **Scanner banding (anisotropic structured noise) absent from Phase 2 augmentation.** Phase 2 augmentation uses isotropic Gaussian noise and S&P noise. Real scanner CCD banding is anisotropic: horizontal streaks from CCD read noise, column-correlated noise from ADC. These have distinct spectral properties from Gaussian noise. | Augraphy does not natively include horizontal banding noise; requires custom augmentation. | Add horizontal banding simulation to Phase 2 pipeline: generate additive noise with correlation length = image width (horizontal) and vary band amplitude to create sigma-equivalent score. Target: 15-20% of Phase 2 images include banding subtype. | Low — 1 engineer-day for custom augmentation function |
| IQA-NOISE-G06 | **Binarized image noise_score label convention is undefined.** Color_mode=binarized images represent 1-bit documents where continuous noise is transformed to pixel-flip errors. Labeling convention is unresolved: score=1.0 (no continuous noise), or score based on pixel error density, or exclude from training. Without a policy, training will receive conflicting gradients for binarized images. | Convention not established during head specification. | Establish binarized image policy: Recommend score=1.0 for binarized images where binarization quality is good (few pixel errors), add `color_mode=binarized` flag to manifest for loss masking option. OOD-4d tests this scenario. | Low — 0.5 engineer-days (policy decision + manifest flag implementation) |
| IQA-NOISE-G07 | **Phase 2 noise augmentation does not cover noise+blur compound condition.** Low-light camera captures produce simultaneous blur + noise. Phase 2 applies noise augmentation to clean/sharp images only, creating a training distribution that lacks this co-occurring condition. | Augmentation pipeline designed for single-degradation labeling; compound labeling requires multi-head simultaneous application. | Extend Phase 2 augmentation to include 10-15% compound noise+blur samples: apply both GaussianNoise and DefocusBlur simultaneously; record independent noise_score and blur_score labels. Requires updating both G1-1 (blur) and G1-2 (noise) assembly scripts to handle compound samples. | Medium — 2 engineer-days for compound augmentation script + G1-1/G1-2 label coordination |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| IQA-NOISE-G08 | Noise subtype labels (Gaussian/salt-pepper/scanner-banding/organic-grain) not captured in Phase 2 manifest | Add `noise_subtype` field to Phase 2 generation manifest; use during OOD analysis to identify model performance by noise type |
| IQA-NOISE-G09 | Aged document organic grain (foxing, paper grain) not in Phase 2 augmentation | Source historical document scans with known degradation; add foxing simulation (orange-brown spot overlay) to aged/historical augmentation profiles |
| IQA-NOISE-G10 | JPEG high-frequency artifact-noise conflation not addressed in training | Add JPEG compression (Q=20-40) as a noise co-augmentation subtype; label images with both compression_score and noise_score to train the model to distinguish JPEG artifacts from sensor noise |

---

## Section 9 — Multi-Model Consensus

**Status**: ✅ Complete (2026-02-23)

**Adequacy Rating (pre-consensus)**: ❌ Blocked

**Analyst Summary**: SIG-G1-2 (noise_score) faces a two-layer blocking problem. The primary P0 blocker is that the classical noise detector (wavelet MAD), while technically correct, has near-zero discriminative variance on the clean-document Phase 1 population (DIQA-5000, OHR-Bench) — making it unusable as a Phase 1 label source or cross-validation signal. This leaves VLM as the sole Phase 1 labeling path, but noise-specific VLM SRCC has not been measured (only overall_quality SRCC was piloted: 0.39-0.53). The secondary P0 blocker is that the Phase 2 synthetic pipeline (100K images, tier_0_exact from noise sigma) does not yet exist. The architecture for Phase 2 is well-designed and tractable; this is a procedural gap, not a design problem. Phase 2 alone cannot meet the SRCC ≥ 0.65 target on real documents due to the sim-to-real gap between isotropic Gaussian noise and real-world scanner speckle / JPEG artifacts / aged organic grain. The head is not fundamentally broken: the Gaussian NLL architecture is appropriate, the dual-path label strategy is sound, and Phase 2 synthetic will provide strong training signal for the noise concept. But both Phase 1 labeling (VLM SRCC validation) and Phase 2 pipeline construction must complete before assembly can begin.

**Consensus Models**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

---

### Consensus Summary

**Ratings**: Gemini 2.5 Pro — BLOCKED (confidence 9/10); Gemini 3 Pro Preview — NEEDS WORK / Blocked (confidence 8-9/10).

**Q1 — Is the classical noise detector zero-variance issue a P0 blocker?**

Both models agree: Yes, this is a P0 blocker for Phase 1 labeling. The classical detector's failure to discriminate on the clean document population eliminates it as a label source and as a cross-validation signal for Phase 1. The path forward requires either (a) validated VLM noise-specific scoring or (b) human MOS annotation on a 1-2K seed set. Gemini 2.5 Pro rates this as a fundamental architectural blocker (BLOCKED status); Gemini 3 Pro Preview notes that Phase 2 synthetic is a tractable alternative primary signal, which downweights severity to NEEDS WORK. Synthesis: Both are correct from different vantage points. Phase 2 synthetic CAN provide the primary training signal, but Phase 1 real-document data is required for domain calibration (the sim-to-real gap is too large for a production model trained on synthetic Gaussian/S&P noise alone). The blocker is procedural, not architectural.

**Q2 — Can Phase 2 synthetic labels alone produce a production-useful noise_score head?**

Both models: No. A model trained exclusively on Gaussian and salt-and-pepper noise augmentation will not generalize to real-world scanner speckle, JPEG high-frequency artifacts, aged document organic grain, or photocopier toner noise. The sim-to-real gap is confirmed by the distinct spectral properties of real-world noise vs. synthetic Gaussian noise. The SRCC ≥ 0.65 target on real documents requires domain adaptation from at least some real labeled examples (Phase 1). However, Phase 2 provides an excellent foundation for the noise concept that Phase 1 fine-tunes.

**Q3 — What is the minimum Phase 1 curated data volume for calibration?**

Consensus recommendation: 2,000-5,000 real-document images with validated noise labels (VLM-scored, SRCC ≥ 0.55 confirmed) are sufficient for domain adaptation when combined with 100K Phase 2 synthetic. The full 15K Phase 1 pool is available; the question is label quality, not volume. A VLM pilot of 200 images (injected noise at known sigma) would validate whether VLM can serve as label source before committing to bulk labeling.

**Q4 — Is the OOD-Degradation design adequate?**

Both models: Yes, the 800-image design (4a-4d sub-sources) is well-targeted and adequate in design. Key strength: 4a multiply-distorted (500) directly tests compound-noise scenarios; 4c book gutter shadow tests non-uniform illumination with apparent noise; 4d binarized tests the edge case. Gap: OOD labeling ALSO cannot use the classical noise detector — human annotation or validated VLM is required for OOD noise_score ground truth. This extends the labeling blocker to evaluation.

**Q5 — Overall adequacy rating?**

Gemini 2.5 Pro: BLOCKED — the labeling strategy for real-world images is invalid until a replacement is found and validated.
Gemini 3 Pro Preview: NEEDS WORK / Blocked — Phase 2 synthetic is tractable; Phase 1 requires validated VLM or human MOS; both paths exist but require 5-10 days of engineering work before assembly begins.
Synthesis: BLOCKED with a clear remediation path. The core design (Gaussian NLL head, dual-path strategy, augmentation-as-label for Phase 2) is sound. Two P0 procedural gaps (VLM noise SRCC validation + Phase 2 pipeline construction) must resolve before assembly begins. Neither requires architectural rework.

**Final Rating**: ❌ BLOCKED (37/100)

**Top Recommendations** (priority order):

1. Run VLM noise-specific pilot immediately: 200 DIQA-5000 images with injected Gaussian noise at known sigma ∈ {0, 3, 6, 10, 15, 20, 25}; measure VLM noise score SRCC vs. injected sigma. If SRCC ≥ 0.55, proceed with bulk VLM labeling as Phase 1 source (2-3 engineer-days to validate and run).
2. Build Phase 2 augmentation pipeline: Implement `iqa` sub-command in `prepare_multitask_datasets.py`; apply `OneOf([GaussianNoise, SaltAndPepperNoise])` to synth-multiscript-v3 images; record sigma as tier_0_exact label (2-3 engineer-days + 3-5 hours GPU generation).
3. Populate Phase 1 L2 fields: After VLM pilot validates SRCC, run bulk VLM labeling on DIQA-5000 + OHR-Bench + RealDAE; populate `ml_image_quality.noise_score`.
4. Establish binarized image convention: Define score=1.0 policy for binarized color_mode images; add manifest flag for loss masking (0.5 engineer-days).
5. Add scanner banding augmentation to Phase 2: Implement anisotropic horizontal banding noise subtype to reduce sim-to-real gap for scanner document noise (1 engineer-day).
6. Acquire OOD-Degradation images: 800 images across 4a-4d sub-sources; use human annotation or validated VLM for noise_score ground truth (NOT classical detector).

### Scoring Summary

| Component | Weight | Score | Weighted | Rationale |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 30 | 10.5 | Phase 2 design is sound but 0/100K built. Phase 1 labels blocked by classical zero-variance defect; VLM SRCC unmeasured for noise specifically. Image pool exists (15K) but 0 labeled. |
| 14-Dimension Coverage | 25% | 20 | 5.0 | DDR 0.0/100 due to L2 metadata not populated. Estimated real diversity moderate (diverse source datasets) but capture_method scanner banding and resolution DPI spread are unverified gaps. |
| Wild Condition Coverage | 20% | 15 | 3.0 | DDR 8.3/100 curated, 0.0/100 synthetic. 5 of 8 noise-specific wild conditions missing. Critical gaps: scanner banding, JPEG artifact conflation, noise+blur compound, screen recapture. |
| OOD Design Quality | 20% | 65 | 13.0 | OOD-Degradation design (4a-4d) is well-targeted and adequate. Score reduced by: 0/800 acquired, and OOD labels ALSO cannot use classical detector (human annotation required for OOD ground truth). |
| **Overall** | 100% | — | **31.5** | |

**Grade**: ❌ Blocked (32/100 rounded)

**Score rationale**:

- Source Pool Adequacy (30): Image pool size is adequate (15K Phase 1 + 100K Phase 2 planned). Both paths are blocked by absent labels. Score reflects that the design is sound and the blockers are procedural, not architectural — higher than a structurally broken design would receive.
- 14-Dimension Coverage (20): Severely depressed by missing L2 enrichment on manifests (0.0/100 DDR). Estimated actual diversity is moderate (diverse source datasets) but three dimensions with direct noise relevance — capture_method scanner profiles, resolution DPI spread, and color_mode binarized convention — are unverified or unresolved.
- Wild Condition Coverage (15): Below DDR's already-low score of 8.3/100 because 5 of the 8 noise-specific wild conditions (scanner banding, JPEG conflation, noise+blur, aged grain, screen recapture) are not covered even in design. Phase 2 adds only isotropic Gaussian/S&P noise.
- OOD Design Quality (65): Design is appropriate and well-targeted. Partial credit because: design exists (4 sub-sources cover the right stress scenarios), but all acquisition is pending and OOD labeling faces the same classical detector blocker as Phase 1.
