# Head Adequacy Review: shadow_reg (SIG-G5-2)

> **Status**: ✅ Complete
> **Version**: 2.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: F — Page Attributes
> **Adequacy**: ❌ Blocked (Score: 28.0 / 100 | P0 blockers present — assembly cannot start)

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G5-2 |
| Model | SigLIP 2 NAFlex |
| Group | G5 — Page Attributes |
| Head Name | shadow_reg (also written as shadow_score) |
| Task Type | Regression 0-1 (shadow severity score) |
| Output Format | Linear output [0-1] |
| Priority | P2 |
| Performance Target | MAE < 0.08 |
| Primary L2 Field | `physical_degradation.shadow_severity` (float 0-1) |
| Shared-Data Heads | SIG-G5-3 (warping_reg shares doc3d source dataset) |
| Training Phase | Phase 5 — Page Attributes |

### Severity Scale Definition

| Range | Bucket | Meaning |
| --- | --- | --- |
| 0.0 | NONE | No shadow present (not "measurement failed") |
| 0.0–0.25 | mild | Faint gradient, minimal OCR impact |
| 0.25–0.60 | moderate | Visible shadow, text partially obscured |
| > 0.60 | severe | Strong shadow, significant text degradation |

> **Convention**: `shadow_severity = 0.0` means NO shadow is present. This convention must be
> consistent throughout the labeling script. Sentinel values or boolean flags must be used for
> images where shadow is present but unmeasurable (e.g., binarized 1-bit documents).

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `physical_degradation.shadow_severity` _(float 0-1)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**:

- tier_0_exact for sd7k / wsrd (derived from paired pixel difference: `mean_opacity_in_shadow_mask`)
- tier_0_exact for v3 synthetic views (Augraphy severity parameter IS the label)
- tier_1_annotation for realdae (VLM or classical measurement with confidence filter)

> **NOTE on severity formula**: SSIM is explicitly BANNED for shadow labeling (per
> DATASET_DIVERSITY_REQUIREMENTS §8.2 — SSIM measures blur/noise/compression equally, not shadow
> severity). The correct formula for sd7k/wsrd paired images is:
> `severity = mean(abs(shadow_img - clean_img)[shadow_mask]) / 255.0`
> where `shadow_mask` is the per-pixel shadow presence mask included in the sd7k/wsrd dataset.

### CRITICAL STATUS — L2 Field Not Populated

`physical_degradation.shadow_severity` is NOT present in current L2 metadata for any dataset.
The Stream 4C dry-run shadow subcommand returned 0 real records and triggered a mixing cap warning,
confirming the total L2 gap. Script `label_shadow_severity.py` does not yet exist.

### Candidate Source Datasets

| Dataset | Total Images | Paired GT | Field Populated | Usable Now | Block Reason |
| --- | --- | --- | --- | --- | --- |
| sd7k | 7,239 | YES (shadow/clean + mask) | ❌ Not in L2 | 0 | label_shadow_severity.py missing |
| wsrd | 4,500 | YES (shadow/clean pairs) | ❌ Not in L2 | 0 | label_shadow_severity.py missing |
| realdae | ~1,200 | PARTIAL | ❌ Not in L2 | 0 | label_shadow_severity.py missing |
| synth-multiscript-v3 shadow views | 8,000 | YES (Augraphy param = label) | ❌ Not in L2 | 0 | severity not written to L2 sidecars |
| SmartDoc-QA clean frames | 2,000 | N/A (NONE class, 0.0) | ❌ Not in L2 | 0 | shadow_severity=0.0 must be written |
| MIDV500 flat captures | 1,000 | N/A (NONE class, 0.0) | ❌ Not in L2 | 0 | shadow_severity=0.0 must be written |
| doc3d | 102,000 | YES (3D geometry → shadow maps) | ❌ Not in L2 | 0 | DEFERRED P3 (209GB extraction effort) |

### CRITICAL STRUCTURAL PROBLEM — NONE Class

**sd7k and wsrd are shadow removal datasets. They contain ONLY shadowed images** (paired with
clean references). The 40% NONE class target (6,000 images) cannot be sourced from sd7k/wsrd.
However, the paired clean reference images FROM sd7k/wsrd can and should serve as the primary
NONE-class source — this is the most domain-correct approach (same camera, lighting, and
document type as the positive examples). Additional NONE-class sources for diversity:

| NONE-Class Source | Count | Domain Match | Rationale |
| --- | --- | --- | --- |
| sd7k/wsrd clean reference images | ~3,500–5,000 | BEST — same camera domain | Avoids dataset-identity confound |
| SmartDoc-QA clean frames | 2,000 | HIGH — same camera domain as sd7k | Flat lit, smartphone capture |
| MIDV500 flat captures | 1,000 | MEDIUM | Camera captures, no shadow |
| v3 clean (zero Augraphy shadow) | 500 | LOW — synthetic domain | Script diversity only |
| **Total NONE estimate** | **~7,000–8,500** | | Exceeds 6,000 target |

> **Gemini 3 Pro warning (9/10 confidence)**: Constructing the NONE class from entirely different
> datasets (e.g., DocLayNet born-digital) vs. shadowed datasets (camera captures) risks "domain
> shift cheating" — the model learns camera fingerprint or noise profile rather than shadow
> presence. Using sd7k/wsrd clean reference pairs as the primary NONE source is the correct
> approach and eliminates this risk.

### Usable Pool Summary (Post-P0 Remediation)

| Severity Bucket | Target | Available After Labeling | Gap |
| --- | --- | --- | --- |
| NONE (0.0) | 6,000 | ~7,000–8,500 (clean refs + SmartDoc-QA + MIDV500) | 0 |
| mild (0.0–0.25) | 3,000 | ~4,000 (sd7k/wsrd mild subset + v3 mild) | 0 |
| moderate (0.25–0.60) | 3,000 | ~7,000 (sd7k/wsrd moderate + v3 moderate) | 0 |
| severe (> 0.60) | 3,000 | ~3,000 (sd7k/wsrd severe subset; may be skewed) | 0–1,000 |
| **Total** | **15,000** | **~21,000–22,500** | **0 (numerically sufficient)** |

> **Distribution risk**: sd7k and wsrd are shadow REMOVAL datasets — they were curated for visible,
> challenging shadows. This means they likely over-represent moderate-to-severe cases and under-
> represent mild shadows. After labeling, verify the mild bucket meets the 3,000 target. If
> deficient, increase the v3 synthetic mild component.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| G5-2-DEF-01 | sd7k | `physical_degradation.shadow_severity` | Paired GT exists (shadow/clean + mask) but NOT extracted to L2 — requires label_shadow_severity.py | ❌ Blocking |
| G5-2-DEF-02 | wsrd | `physical_degradation.shadow_severity` | Same as DEF-01 — GT available but not extracted | ❌ Blocking |
| G5-2-DEF-03 | synth-multiscript-v3 shadow views | `physical_degradation.shadow_severity` | generate_v3_shadow_view.py creates 8K images but does NOT write shadow_severity to L2 sidecars | ❌ Blocking |
| G5-2-DEF-04 | All NONE-class sources | `physical_degradation.shadow_severity` | shadow_severity=0.0 not written to L2 for SmartDoc-QA clean frames, MIDV500 flat captures | ❌ Blocking |

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 15,000 images |
| Assembly Status | ❌ BLOCKED — label_shadow_severity.py does not exist; L2 field unpopulated for all datasets |
| Distribution Target | 40% NONE (0.0) / 20% mild (0.0–0.25) / 20% moderate (0.25–0.60) / 20% severe (> 0.60) |
| Real Data Requirement | ≥ 50% real (sd7k + wsrd + camera negatives) per DATASET_DIVERSITY_REQUIREMENTS §8 |
| Synthetic Cap | ≤ 50% synthetic (v3 shadow views) |
| Assembly Script | `scripts/prepare_multitask_datasets.py shadow` |

### NONE-Class Construction Path (P0 GAP — Undefined)

The assembly plan must explicitly define the NONE-class construction as a three-step process:

1. Extract clean reference images from sd7k/wsrd paired datasets (same camera domain)
2. Supplement with SmartDoc-QA clean frames + MIDV500 flat captures (2,000 + 1,000)
3. Add v3 clean views (500) for script diversity

This path is NOT currently documented in the assembly script. The `prepare_multitask_datasets.py
shadow` subcommand must be updated to explicitly handle the NONE class construction.

### Post-Labeling Distribution Validation Gate

After label_shadow_severity.py is run, BEFORE assembly proceeds:

1. Verify each bucket meets minimum threshold (NONE ≥ 6,000; mild ≥ 3,000; moderate ≥ 3,000;
   severe ≥ 3,000)
2. If severe bucket is deficient (expected risk — sd7k/wsrd may skew toward moderate),
   increase v3 synthetic severe component
3. If mild bucket is deficient (sd7k/wsrd curated for challenging shadows), increase v3 mild
   component via lower Augraphy severity parameters

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 20 / 100 (estimated — assembly blocked, most dimensions unmeasured)

The automated DDR scored this dataset at 46.1/100 overall, but with 3.6/100 on the
14-dimension diversity component (only 1 of 14 dimensions measurable on 7,239 sd7k images
with no L2 metadata populated). The scores below reflect the expected state after P0 remediation.

| Dimension | L2 Field | Relevance | Target | Post-P0 Estimate | Score |
| --- | --- | --- | --- | --- | --- |
| degradation (shadow severity) | `physical_degradation.shadow_severity` | CRITICAL — this IS the label; distribution must hit 40/20/20/20 across all 4 buckets | All 4 buckets at minimum 20% | sd7k/wsrd skewed toward moderate/severe; mild may be deficient | 50 |
| capture_method | `capture_method.method` | CRITICAL — shadow appearance differs fundamentally between camera (directional, gradient) vs. scanner (lid-open, edge shadow) vs. born-digital (impossible) | ≥ 3 methods; camera dominant (≥ 55%) | sd7k/wsrd + SmartDoc-QA are `camera_smartphone`; v3 is synthetic; scanner_lid type from v3 | 55 |
| color_mode | `image_properties.color_mode` | HIGH — binarized documents lose shadow gradient entirely; model must correctly output 0.0 (undetectable) or use sentinel | ≥ 2 modes; binarized edge case defined | Currently no binarized shadow examples; edge case not defined | 10 |
| document_age | `image_properties.document_age` | MEDIUM — aged documents have yellowing that produces gradients mimicking shadow; false positive risk | ≥ 2 age classes | SmartDoc-QA/MIDV500 are modern; aged documents absent | 25 |
| domain | `domain.level1` | MEDIUM — glossy paper (photography books) reflects differently from matte; office vs. book shadows differ | ≥ 5 domains | sd7k/wsrd are camera-captured mixed domains; domain distribution unverified | 30 |
| layout_type | `structure.layout_type` | MEDIUM — shadow over dense text vs. margins has different OCR impact; model may correlate shadow with text density | ≥ 3 types | sd7k/wsrd layout distribution unknown | 25 |
| script_code | `language.script_code` | LOW — shadow detection is script-independent | ≥ 2 script families | v3 covers 27 scripts; sd7k/wsrd are predominantly Latin documents | 40 |
| resolution | `resolution.category` | LOW — shadow severity detection not resolution-dependent at typical document DPIs | ≥ 2 resolution tiers | sd7k/wsrd have known DPI; distribution not verified | 30 |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 15 / 100 (1 partially covered via OOD; training coverage near zero)

| Wild Condition | Status | Training Coverage | OOD Coverage | Gap |
| --- | --- | --- | --- | --- |
| Book gutter shadow (hard gradient at page crease from physical binding) | ❌ Not in training | None — sd7k/wsrd are flat-document only | OOD-Degradation 4c: 100 images (internal photography of bound books) | Book gutter shadow has a DISTINCT gradient curve from flat-document shadows. sd7k/wsrd samples are photographed flat. This is a known training gap — the model will systematically underestimate book gutter severity as "moderate edge shadow." |
| Scanner lid open shadow (gradual edge darkening) | ⚠️ Partial | v3 generates scanner_lid type (8K synthetic); but severity not labeled | No dedicated OOD entry | scanner_lid type coverage depends on v3 synthetic component. Real scanner-lid examples absent from sd7k/wsrd (camera datasets). |
| Spotlight / circular shadow (camera flash off-center or overhead light) | ⚠️ Partial | v3 generates spotlight type; coverage in sd7k unknown | No dedicated OOD entry | v3 Augraphy spotlight type provides partial coverage synthetically. |
| Cast shadow from hand/object held over document | ⚠️ Partial | sd7k/wsrd likely include hand-cast shadows from smartphone photography | No dedicated OOD entry | Most likely to be covered in sd7k/wsrd — these datasets target smartphone shadow removal. Verification needed post-labeling. |
| Shadow on binarized document (no gradient signal, false positive risk) | ❌ Not covered | No binarized shadow or binarized NONE examples | OOD-Degradation 4d: 100 binarized images | Shadow detectors can hallucinate shadows on high-contrast 1-bit text. Model must be trained to output 0.0 (or sentinel) for binarized inputs, not moderate scores from text edges. |
| Compound shadow + warping (bound book page with both shadow and curl) | ❌ Not covered | No compound examples in any source | OOD-Mixed: some compound coverage (4a with ≥5 distortions) | Camera-captured bound books naturally produce both gutter shadow and page curl simultaneously. Training on single-degradation examples produces overconfident predictions. Gap: DATASET_DIVERSITY_REQUIREMENTS §8.2 "Stacked Degradation Sub-Split" (Gap 11 P1). |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images — shared with IQA heads)

### Head-Specific OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 4a. Multiply-distorted (≥ 5 types, shadow as one) | 500 | Augraphy compound augmentation on training-excluded documents; distortion stack: gutter-shadow + page_curl + defocus blur + noise + JPEG compression | `shadow_severity` + `warping_severity` + `blur_score` + `noise_score` + `compression_score` + `overall_quality`, all IQA heads | siglip2 | Shadow must be scored independently of the other 4+ distortion types. Source docs must be drawn from doc3d test split + internal photography ONLY (sd7k/wsrd are training sources). IQA labels require human annotation — classical detectors insufficient for compound distortion. |
| 4c. Book gutter shadow (hard gradient at page crease) | 100 | Internal photography of bound books photographed open-flat | `shadow_severity`, `shadow_type=hard`, `warping_type=page_curl` | siglip2 | sd7k and wsrd cover flat-document shadows only. Gutter shadows have a distinct parabolic gradient curve absent from training data. Paired with page_curl warping — both G5-2 and G5-3 are stressed simultaneously. This 100-image sub-source is the ONLY shadow-specific OOD coverage. |

### OOD Adequacy Assessment

The 100-image book-gutter-shadow sub-source (4c) provides targeted qualitative coverage of the
most important known failure mode. However, two concerns apply:

1. **Statistical power**: 100 images is insufficient for a stable MAE estimate on a regression
   head. MAE confidence intervals at n=100 are wide. Gemini 3 Pro recommends expanding 4c to
   250-500 images for statistically meaningful results.

2. **Coverage breadth**: The OOD set tests exactly one known failure mode (book gutter). It does
   not test binarized-document false positives, scanner-lid shadow, or spotlight shadow. These
   failure modes would require additional OOD sub-sources to evaluate.

### OOD Leakage Risk

**Level**: LOW. sd7k and wsrd are training sources; OOD must use doc3d test split plus internally
acquired documents only. Book gutter shadow (4c) uses internal photography of bound books — no
training analog exists. Compound distortion (4a) must draw exclusively from doc3d test split
images not used in training, combined with Augraphy-generated distortions. Dedup required:
SHA256 + pHash (Hamming ≤ 5) against training manifests before registration.

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 4, P0)

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G5-3 (warping_reg) | Both use doc3d as a potential source; shadow and warping co-occur in bound-book images (gutter shadow + page curl) | Labels must be recorded independently: `shadow_severity` and `warping_severity` are separate L2 fields. Images where both distortions co-occur must have both fields populated. Risk: model learning shadow → warping spurious correlation (both appear together in bound-book training data). Mitigation: ensure NONE-shadow training images also include warped documents (SmartDoc-QA has page curl but minimal shadow). Global split registry (SHA256-keyed) prevents a doc3d image appearing in both shadow_reg training AND warping_reg test split. |
| SIG-G1-1 (blur_score) | Shadow gradients cause localized blur in the gradient transition zone; strong shadow also reduces local contrast | IQA heads may develop spurious correlations with shadow_reg predictions. OOD-4a compound set specifically stresses this interaction — shadow must be scored independently of co-occurring blur. Training must include shadow-only examples where blur_score = 0.0 to teach the model these are orthogonal. |
| SIG-G5-1 (capture_cls) | Shadow primarily occurs in camera-captured documents; scanner-lid-open is a distinct capture method variant | Consistent labels across capture_method and shadow_reg: camera_smartphone images with shadows must have BOTH fields populated. The NONE class from SmartDoc-QA and MIDV500 must also have capture_method labels to preserve this co-labeling requirement. |

### Split Leakage Risk

**Level**: MEDIUM. doc3d (102K images, DEFERRED to P3) feeds potential shadow, warping, and IQA
training. Global split registry (SHA256-keyed) is required to prevent a doc3d image appearing in
both shadow_reg training and warping_reg test split. Within shadow_reg, sd7k and wsrd are
exclusive to this head — cross-head leakage from these sources is absent, but the clean reference
images from sd7k/wsrd used as NONE-class training must NOT appear in the test split of any other
dataset that drew from these sources.

### Label Convention

`shadow_severity = 0.0` means NO shadow present, not "unable to measure" or "measurement
failed." This distinction is critical. Images where shadow gradient is present but physically
unmeasurable (e.g., 1-bit binarized documents where gradient information is lost in thresholding)
must use a sentinel value or separate boolean flag (`shadow_unmeasurable=true`), NOT 0.0.
This convention must be documented and enforced in label_shadow_severity.py before any labels are
generated. Overloading 0.0 with both meanings would corrupt the regression target for binarized
inputs.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| SHADOW-G01 | `label_shadow_severity.py` does not exist — sd7k and wsrd paired GT labels cannot be extracted to L2; v3 shadow views cannot be labeled; NONE class cannot be written | Script not yet created | Create script: (1) define severity formula (mean opacity in shadow mask for paired datasets); (2) extract sd7k/wsrd labels using shadow mask files; (3) derive v3 synthetic labels from Augraphy severity parameter; (4) write shadow_severity=0.0 for NONE-class sources; (5) write all values to L2 sidecars; document convention for binarized sentinel | 3–4 days |
| SHADOW-G02 | L2 `physical_degradation.shadow_severity` field unpopulated for all 6 source datasets | SHADOW-G01 not yet executed | Execute label_shadow_severity.py after SHADOW-G01 is complete; validate output distribution per dataset; confirm sd7k audit grade B/87 and wsrd audit grade A/95 labels pass confidence threshold ≥ 0.7 | 1–2 days (dependent on SHADOW-G01) |
| SHADOW-G03 | NONE-class construction path not defined in assembly script; `prepare_multitask_datasets.py shadow` subcommand does not have a documented NONE-class source | Shadow removal datasets (sd7k/wsrd) contain only shadowed images; no NONE-class source was planned when scripts were written | Update assembly script: (1) include sd7k/wsrd clean reference images as primary NONE source; (2) add SmartDoc-QA clean frames (2,000) and MIDV500 flat captures (1,000) as secondary; (3) add v3 clean views (500) for script diversity; (4) document domain-match rationale to prevent dataset-identity confound | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| SHADOW-G04 | Book gutter shadow absent from training data — sd7k/wsrd cover flat-document shadows only; model will systematically underestimate gutter shadows | Dataset curation gap — shadow removal datasets target flat documents | Option A (recommended): Add Augraphy gutter-shadow augmentation to `generate_v3_shadow_view.py` via `--pre-warp page_curl` flag (per DATASET_DIVERSITY_REQUIREMENTS §8.2 "Stacked Degradation Sub-Split"); target ~1,000 compound examples. Option B (P2): Doc3D shadow maps from 3D geometry. Cap compound examples at ≤ 5% of total shadow dataset | 1 day |
| SHADOW-G05 | Binarized document handling not defined — shadow gradient information is lost in 1-bit images; shadow_severity = 0.0 convention would be incorrect | Label convention gap | (1) Define binarized sentinel handling in SHADOW-G01 script; (2) add ~500 binarized clean images to NONE class (sourced from OOD-Degradation 4d or archival 1-bit scans) to train the model that binarized inputs have zero detectable shadow | 0.5 days |
| SHADOW-G06 | Compound shadow + warping not in training data — camera-captured bound books naturally produce both conditions simultaneously | Single-degradation training assumption | Add 500–800 compound examples: warp v3 base image (page_curl type) THEN apply shadow overlay; set `shadow_severity` AND `warping_severity` labels; weight at 0.8× (slightly down-weighted synthetic compound); cap at ≤ 5% of total shadow dataset | 1 day |
| SHADOW-G07 | OOD-Degradation 4c (book gutter shadow) has only 100 images — statistically insufficient for stable MAE regression evaluation | OOD design was established before full gap analysis | Expand OOD-4c from 100 to ≥ 250 images (photograph 10+ additional bound books from diverse domains: scientific, financial, literary, technical manuals) | 0.5 days (additional photography) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| SHADOW-G08 | Shadow type sub-label (hard/cast/spotlight/scanner_lid) not verified for training distribution — severity may correlate with type | After labeling, verify shadow type distribution within each severity bucket; ensure no type dominates a single severity tier |
| SHADOW-G09 | doc3d (102K images) DEFERRED to P3 — 3D geometry-based shadow maps would provide highest-quality labels for severe shadow cases | After P0/P1 resolved, assess severity bucket shortfalls; if severe bucket remains deficient, implement doc3d extraction pipeline (209GB, 2–3 weeks effort) |
| SHADOW-G10 | Domain diversity within camera class not verified — sd7k/wsrd may be concentrated on specific document types (e.g., form-style documents) | Post-labeling, audit domain distribution within sd7k/wsrd via L2 domain field; if concentrated, supplement with domain-diverse camera-captured documents |

---

## Section 9 — Multi-Model Consensus

**Models consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

> **Note**: deepseek/deepseek-r1-0528 and x-ai/grok-4 both conflated this prompt with the
> code_reg head (SIG-G5-4) and their responses were not applicable to shadow_reg. Consensus
> is based on the two Gemini models (both 9/10 confidence) plus independent analyst findings.

### Analyst Pre-Consensus Summary

The shadow_reg head has a numerically viable source pool once P0 gaps are resolved: sd7k (7.2K
paired GT), wsrd (4.5K paired GT), and v3 shadow views (8K synthetic) provide ~20K shadowed
examples against a 15K target. The fundamental problem is that assembly is fully blocked by the
non-existence of the labeling script. Additionally, the NONE class construction path has a
critical structural flaw: sd7k/wsrd contain only shadowed images, so the clean reference images
from these datasets must be used as NONE-class training data to avoid domain-identity confound.
The OOD design correctly identifies book gutter shadow as the primary failure mode but is
statistically thin at 100 images and does not test binarized false positives or compound
degradation. The automated DDR score (46.1/100 overall, 3.6/100 on 14-dimension diversity) is
consistent with a dataset in a planning-only state.

### Consensus Results

**Gemini 2.5 Pro (9/10 confidence)**: BLOCKED.

The proposal is an untestable plan, not an actionable dataset design. The absence of the
labeling mechanism means no training data can be generated, rendering all details theoretical.
Confirms: (1) P0 prioritization is correct; (2) source pool numerically sufficient post-P0;
(3) OOD design too narrow — only book-gutter tested, missing binarized and unusual shadow
types; (4) NONE class construction from external datasets risks domain-specific bias — model
may learn dataset identity (camera noise, compression) rather than shadow presence.
Recommendation: redirect all effort to the labeling pipeline before any further design work.

**Gemini 3 Pro Preview (9/10 confidence)**: BLOCKED.

Adds critical precision on the NONE class risk, calling it "domain shift cheating": if Shadow
= Dataset_A camera artifacts and No-Shadow = Dataset_B, the model learns to classify dataset
fingerprints. The correction: use the clean reference images included in sd7k/wsrd as the
primary NONE-class source — these are the same camera, same lighting setup, same documents,
just without the shadow overlay. Also raises: (1) severity formula must be defined
mathematically FIRST (RMSE, mean opacity in mask) before coding the script; (2) OOD at 100
images is statistically thin for regression MAE — 250-500 recommended; (3) add ~500 binarized
clean images to NONE class to prevent false positive hallucination on 1-bit text edges.

### Points of Agreement (2/2 models)

1. The head is BLOCKED — labeling script absence is an absolute prerequisite, not a deferrable item.
2. Source pool is numerically sufficient once P0 gaps are resolved (~20K available vs. 15K target).
3. P0 prioritization (labeling script → L2 population → NONE class definition) is correct.
4. NONE class construction from unrelated external datasets risks domain confound.
5. OOD design is too narrow to provide meaningful regression evaluation of failure modes.

### Points of Additional Insight from Models

- **Severity formula definition**: Must be mathematically specified before coding (not after).
  Formula: `mean(abs(shadow_img - clean_img)[shadow_mask]) / 255.0` using sd7k/wsrd shadow masks.
- **NONE class**: sd7k/wsrd clean reference images are the correct primary NONE source — same
  camera, same document, eliminates domain fingerprint risk.
- **OOD statistical adequacy**: 100 images (4c) is insufficient for stable MAE on regression.
  Expand to ≥ 250 images for a meaningful evaluation.
- **Binarized false positive risk**: Shadow detectors hallucinate on high-contrast 1-bit text
  edges. Requires dedicated binarized NONE-class training examples (SHADOW-G05).

### Final Consensus Rating

**BLOCKED** — The shadow_reg head cannot proceed to assembly until three P0 blockers are
resolved: (1) `label_shadow_severity.py` must be created with a mathematically precise severity
formula; (2) all 6 source datasets must have the L2 field populated; (3) the NONE-class
construction path must be formally defined using sd7k/wsrd clean reference pairs as primary
source. All P0 blockers are resolvable within an estimated 5-7 days of focused effort.
Under the 6-class (P1-remediated) state, the head would be upgraded to NEEDS WORK.

### Scoring Summary

| Component | Weight | Rationale | Raw Score | Weighted |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | Currently 0/15K usable (full block). After P0 remediation ~21K available, exceeding target. Blocked score applied: 10/100 (recognizes viable path exists but current state is 0). | 10 | 3.5 |
| 14-Dimension Coverage | 25% | DDR measured 3.6/100 automated. Post-remediation estimate: capture_method (55), color_mode (10), document_age (25), domain (30), layout_type (25), script_code (40), degradation/severity (50), resolution (30). Average: ~33/100. Heavily penalized by color_mode gap (binarized undefined) and document_age absence. | 33 | 8.3 |
| Wild Condition Coverage | 20% | 0 conditions fully covered in training; 3 of 6 partially covered via v3 synthetic types; 1 partially covered via OOD (book gutter). Score: (0 full + 3 partial × 0.5) / 6 = 25% | 25 | 5.0 |
| OOD Design Quality | 20% | 2 sub-sources (4a compound + 4c book gutter) from a shared OOD category. 4c specifically targets the primary failure mode. Deductions: only 1 shadow-specific sub-source (not 4); 100-image 4c is statistically thin; binarized failure mode absent from OOD. | 57 | 11.4 |
| **Overall** | 100% | — | — | **28.2** |

**Grade**: ❌ Blocked (28.2 / 100 | Assembly blocked on P0 gaps; all P0 resolvable in ≤ 7 days)

### Top Recommendations (from consensus)

1. Create `label_shadow_severity.py` immediately with mathematically precise severity formula:
   `mean(abs(shadow_img - clean_img)[shadow_mask]) / 255.0` for sd7k/wsrd paired datasets;
   Augraphy severity parameter for v3 synthetic views; explicit 0.0 writes for NONE-class
   sources. Document the binarized sentinel convention before coding.

2. Use sd7k/wsrd clean reference images as the primary NONE-class source. Do NOT construct
   the NONE class from DocLayNet or other born-digital sources — domain fingerprint contamination
   will cause the model to learn camera noise, not shadow absence.

3. Expand OOD-Degradation 4c from 100 to ≥ 250 book-gutter-shadow images. Photograph at
   least 10 additional bound books (diverse domains: scientific manuals, financial reports,
   literary books, legal texts) to provide statistically meaningful MAE regression evaluation.

4. Add ~500 binarized clean images to the NONE class (from archival 1-bit TIFF sources or
   Sauvola binarization of clean documents) to prevent false positive hallucination on 1-bit
   text edges. Define the shadow_severity sentinel convention for binarized inputs.

5. Implement compound shadow + warping training examples (SHADOW-G06): apply page_curl warp
   to v3 base images THEN apply shadow overlay; record both `shadow_severity` and
   `warping_severity` labels; target 500–800 compound examples capped at ≤ 5% of dataset.
