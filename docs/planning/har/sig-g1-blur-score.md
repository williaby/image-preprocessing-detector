# Head Adequacy Review: blur_score (SIG-G1-1)

> **Status**: ✅ Complete
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: B — IQA
> **Adequacy**: ⚠️ Needs Work (45/100)

---

## Section 1 — Head Identity

| Field | Value |
| --- | --- |
| Head ID | SIG-G1-1 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | blur_score |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | SRCC ≥ 0.65 with human blur annotations or classical Laplacian ground truth |
| Primary L2 Field | `ml_image_quality.blur_score` (Phase 1 supplementary) OR augmentation parameter (Phase 2 primary) |
| Shared-Data Heads | All G1 heads share Phase 1 curated pool (DIQA-5000 + OHR-Bench + RealDAE); Phase 2 is shared synthetic base (synth-multiscript-v3) |
| Training Phase | Phase 1 warmup (IQA + Script jointly), then Phase 2 pre-training of degradation heads |
| Label Strategy | Phase 2 PRIMARY: Gaussian blur sigma augmentation parameter → blur_score (tier_0_exact); Phase 1 SUPPLEMENTARY: classical Laplacian labeling of DIQA-5000/OHR-Bench → `ml_image_quality.blur_score` L2 field (needed for real-world domain transfer) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.blur_score` (float 0-1; Phase 1 supplementary) / Gaussian blur sigma augmentation parameter (Phase 2 primary)

**Critical Architecture Clarification**: TRAINING_DATASET_QUICK_REFERENCE.md confirms that SIG-G1-1 through G1-5 are trained **primarily on Phase 2 synthetic data** (augmentation parameters as tier_0_exact labels). Phase 1 curated (16K from DIQA-5000/OHR-Bench) **feeds only G1-6 (overall_quality) as the primary head**. However, multi-model consensus concludes that Phase 1 Laplacian-labeled data is needed as a real-world domain transfer supplement to prevent the Phase 2 Gaussian-only model from learning filter statistics rather than perceptual blur.

**Confidence Threshold**: Phase 2 tier_0_exact (confidence=1.0); Phase 1 classical Laplacian ≥ 0.7 (SRCC ~0.7 with human blur perception, confirmed in project memory)

**Label Provenance**: Phase 2: tier_0_exact (augmentation parameter is ground truth); Phase 1 supplementary: tier_1_classical (Laplacian variance score, normalized to 0-1)

### Phase 1 — Curated Source Pool (Supplementary)

Phase 1 datasets are the primary source for G1-6 (overall_quality) but provide real-world domain diversity for blur_score if classical Laplacian labels are run.

| Dataset | Total Images | `blur_score` Field Populated | Coverage % | Label Method | Usable |
| --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | NOT populated | 0% | Classical Laplacian labeling not yet run | Candidate — run `label_blur_classical.py` |
| OHR-Bench | 8,500 | NOT populated | 0% | Classical Laplacian labeling not yet run | Candidate — run after DIQA-5000 |
| RealDAE | 1,200 | NOT populated | 0% | Classical Laplacian labeling not yet run | Candidate |
| **Total Phase 1 candidate** | **~15,200** | 0 | 0% | | 0 usable today |

**VLM suitability for Phase 1**: NOT recommended. VLM IQA pilot showed SRCC=0.39 overall, 0.53 non-rotated — insufficient even for overall_quality. Blur-specific VLM SRCC not yet measured. Classical Laplacian detector (iqa_classical.py) has ~0.7 SRCC with human blur perception — strongly preferred over VLM for blur-specific labeling.

### Phase 2 — Synthetic Pipeline (Primary)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are generated from augmentation parameters at creation time. The Gaussian blur sigma applied during augmentation is the ground-truth label, normalized to [0,1].

| Source | Target | Current | Status | Label Type |
| --- | --- | --- | --- | --- |
| synth-multiscript-v3 derived view | 100,000 images | 0 (pipeline not created) | 📋 Planned | tier_0_exact (Gaussian blur sigma → blur_score) |

**synth-multiscript-v3 base availability**: 350,012 images on GCS (confirmed 2026-02-21). Pristine base with diverse composition:

- Color modes: 60% color, 30% grayscale, 10% binarized
- Document age: 80% modern, 15% aged, 5% historical
- Scripts: 27 ISO 15924 scripts, 198 languages
- Skew range: ±22°

**Phase 2 augmentation plan (required additions)**:

- Gaussian blur (planned): kernel sigma 0.5–8.0, maps directly to blur_score 1.0→0.0
- Motion blur (MISSING — P0 gap): linear kernel 0–20px, direction 0°–180°
- Defocus blur (MISSING — P1 gap): lens-out-of-focus simulation via disk kernel
- Combined blur+noise (MISSING — P1 gap): compound augmentation for realistic scenarios

**Normalization convention**: `blur_score = 1.0 − clamp(sigma / sigma_max, 0, 1)` where sigma_max chosen to cover full degradation range. Score of 1.0 = no blur (sharp), 0.0 = maximum blur (unreadable).

### Usable Pool Summary

| Source | Target | Current Usable | Gap | Priority |
| --- | --- | --- | --- | --- |
| Phase 2 synthetic (primary) | 100,000 | 0 | 100,000 | P0 — build pipeline |
| Phase 1 classical supplement | ~15,000 | 0 | ~15,000 | P0 — run Laplacian labeling |
| **Combined target** | **116,000** | **0** | **116,000** | |

### VLM Validation Sampling Tier

- Phase 1 supplementary (classical Laplacian): Tier 1 (max(10, 3%) spot-check against human blur perception). Classical Laplacian has ~0.7 SRCC — VLM spot-check to confirm no systematic bias, not to replace labels.
- Phase 2 synthetic: Tier 0 (no VLM needed — augmentation parameters are ground truth)

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| IQA-BLUR-DEF-01 | DIQA-5000, OHR-Bench, RealDAE | `ml_image_quality.blur_score` | Field not populated — classical Laplacian labeling script not yet run on any Phase 1 dataset | Open — remediation: run `iqa_classical.py` Laplacian pipeline on all three datasets |
| IQA-BLUR-DEF-02 | iqa-synthetic manifest | augmentation_type | Phase 2 pipeline creates Gaussian blur only — motion blur and defocus blur kernel types absent | Open — remediation: add motion and defocus blur augmentation generators |
| IQA-BLUR-DEF-03 | iqa-synthetic, iqa-curated | 14-dim L2 | DDR 14-dim score = 0.0/100 (metadata not loaded, `samples_loaded=0`). Not confirmed poor diversity, but not measurable. | Open — remediation: load assembled manifests into DDR tool |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-BLUR-KI-001 | Phase 2 covers only Gaussian blur — Gaussian kernel trains on specific filter statistics rather than the general perceptual concept of blur. Will not generalize to motion blur (camera shake, fast document capture) or defocus blur (lens out-of-focus). | HIGH — model will pass Gaussian-based validation but fail on real-world motion blur documents |
| IQA-BLUR-KI-002 | Resolution-induced apparent blur (low DPI) can appear identical to optical blur in pixel statistics. The blur_score must be disentangled from resolution_quality_score (SIG-G5-5) to avoid label correlation. | MEDIUM — low-DPI images may receive spuriously high blur_score regardless of actual optical clarity |
| IQA-BLUR-KI-003 | JPEG compression artifacts (blocking, ringing) can visually mimic blur at block boundaries, especially at quality factors ≤ 50. Risk of label correlation between blur_score (G1-1) and compression_score (G1-5). | MEDIUM — augmentation pipeline must expose both blur and compression independently and measure their independence (Pearson r < 0.4 target) |

### Remediation Path

1. **Immediate (before Phase 2 pipeline build)**: Run classical Laplacian blur detector from `iqa_classical.py` on DIQA-5000, OHR-Bench, RealDAE. Store as `ml_image_quality.blur_score` in L2 metadata. This provides real-world domain transfer signal. Effort: ~2 engineer-days.
2. **Phase 2 pipeline (P0)**: Build `prepare_multitask_datasets.py iqa --head blur` sub-command. Include Gaussian (primary) + motion blur (linear kernel) augmentation types. Record augmentation type and parameter per image. Effort: ~3 engineer-days.
3. **Phase 2 pipeline (P1)**: Add defocus blur (disk kernel) and compound blur+noise augmentation types. Effort: ~1 additional engineer-day.
4. **Validation**: After Phase 2 assembly, verify independence from resolution (Pearson |r| < 0.4 between blur_score and resolution_quality_score labels), and from compression (|r| < 0.4 with compression_score labels).

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: 🔄 Phase 1 supplementary not labeled (0/~15K); Phase 2 primary not assembled (0/100K)

**Target Count**: ~15,000 (Phase 1 Laplacian-labeled supplementary) + 100,000 (Phase 2 synthetic primary) = ~115,000 total

**Current Count**: 0

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 2 total images | 100,000 | 0 | ❌ Pipeline not created |
| Phase 2 blur type diversity | ≥2 types (Gaussian + motion) | 0 | ❌ P0 gap |
| Phase 1 supplementary images | ~15,000 | 0 | ❌ Laplacian labeling not run |
| Phase 1 label quality | SRCC ≥ 0.65 vs human blur | ~0.7 expected (classical Laplacian) | ✅ Classical Laplacian is reliable if run |
| Phase 2 label source | Augmentation params (tier_0_exact) | N/A (self-labeling once built) | ✅ No L2 dependency |

**Blockers**:

- Phase 2 synthetic pipeline not yet created (`prepare_multitask_datasets.py iqa` not implemented)
- Classical Laplacian blur labeling not run on Phase 1 curated datasets
- Phase 2 covers Gaussian blur only — motion blur augmentation absent

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` _(not yet implemented)_

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 0.0/100 automated (DDR tool: `samples_loaded=0` — metadata not yet ingested into DDR tool; not a confirmed diversity failure)

**Analyst Estimated Score**: ~55/100 based on source dataset composition analysis (synth-multiscript-v3 base diversity is strong; key gaps are capture_method camera coverage and motion blur augmentation)

**Note on DDR scores**: Both iqa-curated (0.0/100 14-dim) and iqa-synthetic (0.0/100 14-dim) reflect the DDR tool failing to load any samples, not genuine poor diversity. The synth-multiscript-v3 base (which provides Phase 2 images) has known strong diversity. Scores below are analyst estimates based on source dataset composition.

| Dimension | L2 Field | Relevance | Target | Estimated Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL — camera captures produce motion blur and defocus; scanners produce uniform blur or none; born-digital have zero optical blur. Blur signature differs fundamentally by capture origin. | ≥ 20% camera, ≥ 30% scanner, ≥ 30% born-digital | Phase 2 synth: all synthetic (no real camera blur). Phase 1 supplement: DIQA-5000 (mixed camera+scanner), OHR-Bench (scanner+born-digital), RealDAE (before/after pairs) | ⚠️ 35/100 — Phase 2 has no camera-origin blur at all |
| degradation | `quality.degradations` | HIGH — blur is the primary degradation signal for this head. Requires diverse blur severity levels and types. | ≥4 blur severity levels (none/mild/moderate/severe), ≥2 blur types (Gaussian + motion) | Phase 2 plans Gaussian only. Phase 1 supplement provides real-world blur variety (degraded scans, camera captures). | ⚠️ 30/100 — single blur type in Phase 2; real-world variety only from Phase 1 supplement |
| resolution | `resolution.category` | HIGH — blur appears more severe at low resolution (small text features become indistinguishable from optical blur). Resolution and blur must be disentangled in labels. | ≥3 DPI tiers (low/standard/high) | synth-multiscript-v3 was rendered at multiple DPI tiers (72/100/150/200/300/400/600 planned). Phase 1 supplement: DIQA-5000 varied DPI. | ✅ 70/100 — synth-multiscript-v3 explicitly has 7 DPI tiers |
| color_mode | `image_properties.color_mode` | MEDIUM — blur in binarized (1-bit) documents is effectively absent post-binarization (edges are binary regardless of capture blur). Grayscale blur signal is different from color. | ≥2 modes (color + grayscale); binarized as edge case (expected blur_score ≈ 1.0) | synth-multiscript-v3: 60% color, 30% grayscale, 10% binarized | ✅ 75/100 — good color mode distribution from base dataset |
| document_age | `image_properties.document_age` | MEDIUM — aged documents may have organic blur from paper degradation (foxing, yellowing reduces edge sharpness). Different blur profile from optical blur. | ≥2 age classes (modern + aged) | synth-multiscript-v3: 80% modern, 15% aged, 5% historical | ✅ 70/100 — aged examples present in synth base |
| domain | `domain.level1` | MEDIUM — text-heavy documents have different blur tolerance than figure-heavy. High-frequency content (tables, math) has more diagnostic blur signal. | ≥4 domains | synth-multiscript-v3: diverse document types across 27 scripts; DIQA-5000: mixed academic/business | ✅ 65/100 — adequate domain variety through script/source diversity |
| script_code | `language.script_code` | MEDIUM — CJK character sharpness (complex strokes) is more diagnostic of blur than simple Latin letters. Blur threshold for unreadability differs by script. | ≥3 script families | synth-multiscript-v3: 27 scripts, 198 languages | ✅ 80/100 — excellent script diversity from synth base |
| layout_type | `structure.layout_type` | LOW — layout type is not a primary driver of blur signal | ≥3 types | Varied via source dataset diversity | ⚠️ 40/100 — not measured; estimated adequate |

**Analyst summary on diversity**: The synth-multiscript-v3 base provides genuinely strong diversity across color mode, document age, script, and DPI levels. The critical gap is **capture_method** — Phase 2 is entirely synthetic (born_digital category), with no camera-origin motion blur or defocus. This is the single most important diversity gap because it directly limits the model's ability to handle real-world document photography blur.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 8.3/100 automated (iqa-curated DDR: 0 covered, 1 partial, 5 missing — note this DDR was generated with 0 samples loaded; the 8.3 reflects the overall IQA dataset not blur-specific coverage)

**Analyst-assessed blur-specific wild condition coverage**: ~25/100

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Motion blur (camera shake during document capture) | `quality.degradations` (blur subtype = motion) | ❌ Missing | Completely absent from Phase 2 synthetic augmentation plan. Linear kernel (0–20px, direction 0–180°) is the standard motion blur simulation. This is the most common real-world blur type for mobile-captured documents. No training examples means the head will fail to recognize motion blur patterns which have directional structure unlike Gaussian. P0 gap. |
| Defocus blur (lens out-of-focus, autofocus failure) | `quality.degradations` (blur subtype = defocus) | ❌ Missing | Absent from Phase 2 plan. Disk kernel (radius 1–10px) simulates lens defocus. Common for camera-origin captures. Circular point-spread function is visually distinct from Gaussian (sharper cutoff vs Gaussian tail). P1 gap. |
| Resolution-induced apparent blur (low DPI, < 150 DPI) | `resolution.resolution_quality_score` | ⚠️ Partial | Low-DPI images appear blurry but are optically sharp — blur_score should be low (good optical quality) while resolution_quality_score is low. Risk of training on low-DPI images as "blurry" unless DPI is controlled as a covariate. synth-multiscript-v3 7-DPI-tier structure partially addresses this if labels are DPI-aware. |
| Partial blur (one region sharp, one blurry) | `quality.degradations` (spatial extent) | ❌ Missing | Phase 1 images scored globally — MOS and classical Laplacian produce a single global score. Spatially non-uniform blur (one text column sharp, adjacent column blurry from uneven scanner pressure) is not captured. Model will produce a global average that may be misleading for partial blur. No dedicated training signal. |
| Combined blur + noise (low-light camera capture) | `quality.degradations` | ❌ Missing | Low-light camera captures often produce both motion blur (long exposure) and high ISO noise simultaneously. The combined degradation signal is not independently representable as a linear combination of blur and noise scores. DDR iqa-curated "Mobile phone motion blur + defocus combined" = ⚠️ Partial (the only partial in the DDR). Phase 1 supplement (DIQA-5000/RealDAE real images) provides some coverage. |
| JPEG compression mimicking blur (quality factor ≤ 50) | `quality.degradations` | ⚠️ Partial | JPEG blockiness produces ring artifacts at edges that can superficially resemble blur. Phase 2 will include compression_score augmentation separately; must verify that low JPEG quality images do not receive high blur_score. Risk of label conflation between G1-1 (blur) and G1-5 (compression). Phase 1 supplement covers this if compression_score labels are computed independently. |
| Binarized documents (blur signal effectively absent) | `image_properties.color_mode` | ⚠️ Partial | After binarization, blur in the original image is lost — binary pixels are either 0 or 1 regardless of optical sharpness. Phase 2 includes 10% binarized images (from synth-multiscript-v3). Label convention must be: binarized images → blur_score ≈ 1.0 (cannot assess optical blur post-binarization). Convention not yet defined. |
| Multiply-distorted (≥5 simultaneous types including blur) | `quality.degradations` | ❌ Missing (training) / ✅ OOD-4a | Completely absent from training data. OOD-4a (500 images, multiply-distorted with ≥5 simultaneous types) tests this. Training on single-degradation images may cause the head to underestimate blur when co-occurring with noise, shadows, and JPEG compression. This is the most likely OOD failure mode. |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types simultaneously) | 500 | ✅ Direct — critical | Compound distortions: gutter-shadow + page_curl + defocus blur + noise + JPEG. Blur must be scored amid 4+ co-occurring degradations. This is the primary stress test for real-world deployment. Requires human annotation (classical detectors insufficient for compound distortion). |
| 4b. Watermarked documents | 100 | ⚠️ Indirect | Watermark texture may create low-frequency overlay resembling blur at fine text regions. Secondary effect — blur_score should remain high if underlying text is sharp. |
| 4c. Book gutter shadow | 100 | ⚠️ Indirect | Hard shadow gradient causes local contrast reduction that can lower apparent sharpness in gradient zones. Not true optical blur, but shadow regions may score lower on Laplacian-based metrics. |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | `color_mode=binarized` absent from Phase 1 training as labeled data. Post-binarization blur assessment is undefined — model must handle gracefully (expected: blur_score ≈ 1.0 since binarization erases blur information). |

**OOD Acquisition Status**: ⏳ Not started (Phase 4, all 800 images pending)

**Missing OOD Sub-sources for blur_score specifically**:

- Camera-captured documents with motion blur — 4a stress tests blur within compound distortion but does not isolate motion blur specifically. A dedicated motion-blur sub-source (50–100 images) would directly validate the P0 gap.
- Low-DPI vs. optical blur disambiguation examples (DPI-controlled pairs) — would validate that the model correctly scores a sharp low-DPI image higher than a blurry high-DPI image.

**OOD Leakage Risk**: DIQA-5000 and OHR-Bench are in Phase 1 training pool. OOD-Degradation must use non-overlapping sources. All OOD images must be verified via SHA256 + pHash (Hamming ≤ 5) against all training manifests before registration.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1 curated (DIQA-5000 + OHR-Bench + RealDAE): shared across all G1 heads. Phase 2 synthetic (synth-multiscript-v3 derived): shared base, independent augmentation per head.

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independently computed per head.

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| SIG-G1-5 (compression_score) | Same Phase 2 base | JPEG blockiness at quality ≤ 50 can visually mimic blur (blurring block boundaries). Risk: label correlation between blur_score (Gaussian/motion sigma) and compression_score (JPEG quality). | ✅ Labels derived from independent augmentation parameters. Measure Pearson r between blur and compression labels after assembly; target r < 0.4. Flag and investigate if exceeded. |
| SIG-G1-6 (overall_quality) | Phase 1 curated | overall_quality uses VLM/human MOS; blur_score uses classical Laplacian supplement. If blur is the dominant quality issue in an image, the two scores should be correlated — this is expected and acceptable, not a consistency error. | ✅ Different label methods ensure independence for non-blurry images. |
| SIG-G1-2 (noise_score) | Same Phase 2 base | Blur and noise are often co-occurring (low-light capture). Risk: model cannot distinguish independent blur from blur+noise without separate training signal. | ⚠️ P1 improvement: add compound blur+noise augmentation to Phase 2 with explicit per-degradation labels. |
| SIG-G5-5 (resolution_quality_reg) | Different dataset (resolution-quality #3) | Low-DPI images appear blurry. blur_score should remain low (good optical quality) for a sharp low-DPI image. Labels must not conflate resolution artifacts with optical blur. | ⚠️ P1: Validate after assembly that blur_score and resolution_quality_score labels have r < 0.5 at the image level. |

**Split Leakage Risk**: MEDIUM — synth-multiscript-v3 is the shared base for all derived IQA views. Global split registry (SHA256-keyed) must be applied to ensure the same base image does not appear in blur_score training AND resolution_quality training AND validation simultaneously.

**Label Convention**: All G1 scores are 0-1 floats where 1.0 = perfect quality (no blur), 0.0 = severe degradation (severe blur). This is INVERSE of degradation severity (which uses 0=none, 1=severe). Convention must be consistent across all G1 heads and documented in the assembly script.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before training can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| IQA-BLUR-G01 | IQA-BLUR-DEF-02 | **Phase 2 synthetic pipeline not yet created.** 100K target images, 0 assembled. This is the PRIMARY label source for blur_score — no pipeline means no training data. | `prepare_multitask_datasets.py iqa` sub-command not implemented | Implement `prepare_multitask_datasets.py iqa --head blur_score` sub-command. Select 100K images from synth-multiscript-v3 base. Apply Gaussian blur (sigma 0.5–8.0) augmentation. Record sigma per image. Normalize to blur_score = 1.0 − clamp(sigma/sigma_max). | Medium — 3 engineer-days including testing |
| IQA-BLUR-G02 | IQA-BLUR-KI-001 | **Motion blur absent from Phase 2 augmentation (Gaussian-only).** A model trained exclusively on Gaussian blur learns filter statistics, not perceptual blur concept. Consensus (Gemini 2.5 Pro: 9/10 confidence): motion blur absence will cause the model to fail on camera-captured documents. Phase 4a OOD (multiply-distorted) will immediately expose this weakness. | Phase 2 plan specifies only Gaussian blur sigma. No motion blur (linear kernel) or direction parameters. | Add motion blur augmentation to Phase 2 pipeline: linear kernel (kernel_size 0–20px, direction 0–180°). Record `blur_type` (gaussian/motion) and parameters per image. Normalize to common blur_score scale. Target: ≥30% of Phase 2 samples with motion blur. | Low — 1 engineer-day to add motion blur generator to Phase 2 pipeline |
| IQA-BLUR-G03 | IQA-BLUR-DEF-01 | **Phase 1 classical Laplacian labeling not run on any dataset.** `ml_image_quality.blur_score` field unpopulated for DIQA-5000, OHR-Bench, RealDAE. Without Phase 1 supplement, Phase 2 Gaussian+motion blur training has no real-world domain transfer anchor. Consensus: Phase 1 Laplacian labeling is a MANDATORY MINIMUM for production-quality generalization. | Classical Laplacian blur labeling script has not been run on IQA datasets (resolution quality pipeline ran separately for resolution_quality_score). | Run existing `iqa_classical.py` Laplacian detector on DIQA-5000, OHR-Bench, RealDAE. Normalize Laplacian variance scores to 0-1 blur_score range. Store in L2 `ml_image_quality.blur_score`. Expected SRCC ~0.7 with human blur perception (validated in project memory). | Low — 2 engineer-days including normalization calibration |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| IQA-BLUR-G04 | **Defocus blur (lens out-of-focus) absent from Phase 2.** Disk kernel blur has a visually distinct profile from Gaussian (sharper cutoff) and motion blur (directional). Without defocus examples, model may over-generalize Gaussian patterns to all blur types. | Phase 2 plan does not include disk/defocus kernel augmentation. | Add defocus blur (disk kernel, radius 1–10px) to Phase 2 augmentation pipeline as third blur type. Target: ≥15% of Phase 2 samples with defocus blur. | Low — 0.5 engineer-days (add disk kernel generator) |
| IQA-BLUR-G05 | **Resolution-induced apparent blur not disentangled from optical blur.** Low-DPI images appear blurry due to sampling limitations, not optical degradation. Risk: model learns to assign high blur_score to low-DPI sharp images. | Labels generated from augmentation sigma without DPI covariate. | Add DPI as a covariate in Phase 2 generation. For low-DPI images (< 150 DPI), ensure blur_score reflects OPTICAL blur only (i.e., sigma=0 → blur_score=1.0 regardless of DPI). Validate post-assembly: blur_score and resolution_quality_score labels must have Pearson r < 0.5. | Low — 0.5 engineer-days in generation script |
| IQA-BLUR-G06 | **Binarized document blur convention undefined.** Post-binarization, all blur information is lost — binary pixels are 0 or 1 regardless of optical sharpness. 10% of Phase 2 images (from synth-multiscript-v3) are binarized. Without a defined convention, these images will receive random blur_score labels based on Gaussian sigma (which has no effect on a binarized image). | No explicit handling for `color_mode=binarized` in augmentation pipeline. | Define convention: For binarized images, set `blur_score = 1.0` (cannot assess optical blur post-binarization, treat as maximally sharp). Mask Gaussian blur augmentation loss for binarized images in training (or exclude from Phase 2 blur_score subset). | Low — 0.5 engineer-days policy definition + code |
| IQA-BLUR-G07 | **Blur-compression independence not verified.** JPEG blockiness at quality ≤ 50 mimics blur visually. If blur_score and compression_score labels are correlated (r > 0.4), the head will receive ambiguous gradients. | Phase 2 applies degradations independently, but statistical correlation in the augmented image space is not verified. | After Phase 2 assembly, run independence check: compute Pearson r between blur_score and compression_score labels for all Phase 2 images. If r > 0.4, add explicit "blur-only" and "compression-only" training examples at the severity boundary. | Low — 0.5 engineer-days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| IQA-BLUR-G08 | **Partial blur (spatially non-uniform) not representable.** Global MOS and Laplacian scores produce a single global value; spatially non-uniform blur (one region sharp, adjacent region blurry) is averaged away. | Add `blur_spatial_uniformity` field to Phase 2 generation metadata. Source partial-blur training examples from camera-captured documents with selective focus (depth-of-field effects). Effort: 2 engineer-days. |
| IQA-BLUR-G09 | **Combined blur + noise sub-condition not explicitly trained.** Low-light capture produces simultaneous motion blur + high ISO noise; the compound signal is not a linear combination of independent degradations. | Add compound augmentation (simultaneous Gaussian/motion blur + Gaussian noise) to Phase 2 pipeline. Record both parameters. Add `compound_degradation=True` flag to identify these examples in analysis. Effort: 1 engineer-day. |
| IQA-BLUR-G10 | **Blur-specific VLM SRCC not measured independently.** VLM pilot measured SRCC on overall_quality only (SRCC=0.53 non-rotated). Blur-specific VLM SRCC may differ significantly given that blur is more classically measurable than overall quality. | Run targeted VLM validation on 100–200 DIQA-5000 images using blur-specific prompt (orientation-independent, focused on text sharpness). Compare against Laplacian classical labels. If VLM SRCC > 0.65, use as Phase 1 label quality gate rather than classical only. Effort: 2–4 hours in-session. |

---

## Section 9 — Multi-Model Consensus

**Status**: ✅ Complete (2026-02-23)

**Adequacy Rating (pre-consensus)**: ⚠️ Needs Work

**Analyst Summary**: SIG-G1-1 (blur_score) faces a fundamentally different challenge from the overall_quality head (SIG-G1-6): blur is classically measurable with ~0.7 SRCC (Laplacian variance), making Phase 1 labeling tractable without VLM. The critical gap is that the Phase 2 primary pipeline does not yet exist, and when built, its plan calls for Gaussian blur only. Gaussian-only training teaches the model to recognize Gaussian filter statistics rather than the general perceptual concept of blur — a well-known failure mode in IQA literature. Motion blur from camera captures (a primary real-world blur source for documents) will be completely absent from training. The Phase 1 classical supplement provides real-world anchor but is not yet labeled. The OOD design (800 images across 4 sub-sources) is sound and well-targeted; all are pending acquisition. The synth-multiscript-v3 base diversity is strong. The path to ✅ Ready is clear and bounded: build Phase 2 pipeline with Gaussian + motion blur, run Laplacian labeling on Phase 1 datasets, and handle binarized image convention.

**Consensus Prompt**: "Evaluate the training dataset design for SigLIP 2 NAFlex blur_score head (SIG-G1-1). P0 regression head. Phase 2 primary (100K planned, not built): Gaussian blur sigma → tier_0_exact labels from synth-multiscript-v3. Phase 1 supplement (16K, not labeled): classical Laplacian on DIQA-5000/OHR-Bench. Questions: (1) Is Gaussian-only Phase 2 sufficient, or is motion blur a P0 requirement? (2) Is Phase 1 Laplacian labeling mandatory or optional? (3) Is 100K adequate given single blur type? (4) OOD-Degradation adequacy? (5) Overall rating."

**Models consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

---

### Consensus Summary

**Ratings**: Gemini 2.5 Pro — BLOCKED (9/10 confidence); Gemini 3 Pro Preview — NEEDS WORK (8/10 confidence)

**Synthesized rating: NEEDS WORK** (downgraded from BLOCKED because all gaps are solvable within 1 week and the pipeline architecture is sound)

---

**Q1 — Is Gaussian blur sufficient as the primary Phase 2 label source?**

Both models: NO. A model trained exclusively on Gaussian blur learns to recognize the statistical patterns of that specific filter, not the perceptual concept of blur. Gaussian blur has a spatially symmetric, monotonically decreasing PSF (point spread function). Motion blur has a directional linear PSF. Defocus blur has a disk-shaped PSF with a sharp cutoff. These produce different frequency-domain signatures. A model trained only on Gaussian will fail to recognize motion blur patterns as "blurry" — it will produce near-neutral blur_score outputs for camera-captured documents with horizontal or vertical motion blur, exactly the use case the head is designed for.

Gemini 2.5 Pro specifically notes: "This narrow training approach directly undermines the feature's potential value and risks delivering a model that performs poorly on user-provided content. The 500 multiply-distorted test images in Phase 4a will likely highlight this weakness immediately."

**Q2 — Is Phase 1 Laplacian labeling mandatory or optional?**

Both models: MANDATORY MINIMUM for production-quality generalization. Phase 2 provides exact labels but only for synthetic images. Without Phase 1 real-world supplement, the model has no anchor for real document blur characteristics — organic blur from aging paper, scanner pressure variations, and camera defocus from actual document photography. The classical Laplacian detector (already in `iqa_classical.py`) has ~0.7 SRCC with human blur perception — significantly better than the VLM pilot (SRCC=0.39). Running it on Phase 1 datasets is low effort (~2 engineer-days) and constitutes a minimum requirement.

**Q3 — Is 100K adequate given single blur type?**

Both models: Volume is adequate; diversity is the problem. 100K of diverse blur types (Gaussian + motion + defocus) is adequate for a regression head. 100K of Gaussian only is NOT adequate for production deployment. The fix is to diversify augmentation types (add motion blur to Phase 2), not to increase volume.

**Q4 — OOD-Degradation adequacy (4a multiply-distorted as primary stress test)?**

Both models: OOD design is sound and well-targeted. Phase 4a (500 multiply-distorted images) correctly identifies the primary OOD stress scenario for blur_score: blur co-occurring with 4+ other degradations. However, 800 images total is thin for a regression head — both models note this. OOD-4a requires human annotation (classical Laplacian has SRCC < 0.28 on compound distortions per VLM pilot study — insufficient for OOD ground truth). The OOD acquisition pending status is expected at this phase.

Additional OOD gap noted: no dedicated camera-captured motion blur sub-source. This would directly validate the P0 gap identified for Phase 2.

**Q5 — Overall adequacy rating:**

Gemini 2.5 Pro: BLOCKED — primary concern is that proceeding without motion blur in Phase 2 will produce a model that fails in production.

Gemini 3 Pro Preview: NEEDS WORK — Phase 2 synthetic is the strongest signal path if augmentation is diversified; classical Laplacian provides viable Phase 1 supplement; pipeline gap is solvable.

**Synthesis**: NEEDS WORK. The disagreement between BLOCKED and NEEDS WORK resolves on the remediation timeline: all P0 gaps (build Phase 2 pipeline with motion blur, run Laplacian labeling) are solvable within ~1 week. The pipeline architecture (synth-multiscript-v3 base + augmentation derivation) is sound. This is not structurally blocked like SIG-G3-2's label noise ceiling — the path forward is clear and bounded.

**Final Rating**: ⚠️ NEEDS WORK

**Top Recommendations** (priority order):

1. Build Phase 2 pipeline (`prepare_multitask_datasets.py iqa --head blur_score`) with BOTH Gaussian and motion blur augmentation types. Target: ≥30% motion blur in 100K samples. Without motion blur, the head will fail on camera-captured document images in production. (P0, ~3 engineer-days combined)
2. Run classical Laplacian blur detector (`iqa_classical.py`) on DIQA-5000, OHR-Bench, and RealDAE. Store as `ml_image_quality.blur_score` in L2 metadata. This provides real-world domain transfer anchor that Phase 2 synthetic cannot provide. (P0, ~2 engineer-days)
3. Define binarized image blur convention: `blur_score = 1.0` for `color_mode=binarized` images (post-binarization blur information is lost; treat as maximally sharp). Apply as a training mask in Phase 2. (P1, 0.5 engineer-days)
4. Add defocus blur (disk kernel, radius 1–10px) as third blur type in Phase 2 pipeline to cover lens autofocus failure scenarios. (P1, 0.5 engineer-days)
5. Validate independence after assembly: Pearson |r| between blur_score and compression_score labels must be < 0.4, and between blur_score and resolution_quality_score must be < 0.5. Investigate if exceeded.

---

### Scoring Summary

| Component | Weight | Score | Weighted | Rationale |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 35 | 12.25 | Phase 2 pipeline not built (0 images), Phase 1 Laplacian labels not run (0 populated). synth-multiscript-v3 base is available and diverse — architecture is sound, execution is not started. Score reflects zero current usable data, not structural infeasibility. |
| 14-Dimension Coverage | 25% | 55 | 13.75 | DDR automated score is 0.0/100 due to metadata load failure (not genuine poor diversity). Analyst estimate: synth-multiscript-v3 base provides strong diversity across color mode, script, DPI, document age. Critical gap: capture_method (Phase 2 entirely synthetic, no camera-origin blur). Score capped by unmeasured dimensions and absent camera coverage. |
| Wild Condition Coverage | 20% | 25 | 5.00 | DDR wild condition 8.3/100 (for full IQA dataset). Blur-specific: 2 conditions partial (combined blur+noise, JPEG mimicking blur), 3 conditions missing (motion blur, defocus blur, partial spatial blur), 2 conditions partially addressed (binarized convention undefined, resolution-apparent blur risk). Motion blur absence is the most critical miss. |
| OOD Design Quality | 20% | 70 | 14.00 | OOD-Degradation design (4a–4d) is well-targeted for IQA heads. 4a (500 multiply-distorted) is the correct primary stress test. Design is sound; all pending acquisition is normal at this phase. Score capped by thin overall volume (800 images for regression head), lack of isolated motion blur sub-source, and OOD annotation method (human annotation required but not planned). |
| **Overall** | 100% | — | **45.00** | |

**Grade**: ⚠️ Needs Work (45/100)

**Score rationale note**: The 45/100 score reflects a genuine pipeline execution gap — no training data currently exists for this head — but not a structural infeasibility. All gaps are resolvable in ~1 week of engineering. After completion of the three P0 gaps (Phase 2 pipeline with Gaussian+motion, Phase 1 Laplacian labeling, binarized convention), the expected score would rise to approximately 72/100 — approaching the ✅ Ready threshold. The primary residual gap after P0 remediation is the 14-dim DDR load failure and wild condition coverage (defocus blur, partial blur), which are P1 improvements.
