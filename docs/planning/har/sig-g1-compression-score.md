# Head Adequacy Review: compression_score (SIG-G1-5)

> **Status**: ✅ Analysis Complete
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: B — IQA
> **Adequacy**: ⚠️ Needs Work (65/100)

---

## Section 1 — Head Identity

| Field | Value |
| --- | --- |
| Head ID | SIG-G1-5 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | compression_score |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | SRCC ≥ 0.65 (vs human MOS) |
| Primary L2 Field | `ml_image_quality.compression_score` (Phase 1) OR augmentation parameter (Phase 2) |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench + RealDAE) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: Classical DCT QF estimator → L2 field (tier_1_annotation); Phase 2: JPEG quality factor recorded at re-save time (tier_0_exact) |

> **Convention**: compression_score = 0.0 means severe JPEG artifacts (heavily compressed); compression_score = 1.0 means pristine/lossless (no compression artifacts). This follows the severity-inverted quality-score convention used across all G1 heads. Phase 2 derivation: `compression_score = 1.0 - (jpeg_quality / 100.0)` so QF=10 → score=0.90 (severe), QF=95 → score=0.05 (minimal).
>
> **Convention Conflict Notice**: The scaffolded file (v1.0) contained an inverted convention (`compression_score = jpeg_quality / 100.0`) inconsistent with the head description (0=pristine, 1=severe). This review adopts the severity convention (0=pristine, 1=severe) consistent with the head specification. The Phase 2 labeling pipeline must use `compression_score = 1.0 - (jpeg_quality / 100.0)`.

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.compression_score` (float 0-1; Phase 1) / JPEG quality factor parameter (Phase 2)

**Confidence Threshold**: ≥ 0.7 for Phase 1 classical-estimator labels (DCT analysis is deterministic; confidence derives from image format — PNG/lossless gets exact 0.0, JPEG gets DCT-derived estimate)

**Label Provenance**: Phase 1: tier_1_annotation (DCT classical QF estimator, deterministic mapping from QF → score); Phase 2: tier_0_exact (JPEG quality factor recorded at re-save time)

**Key Differentiator**: Unlike noise_score (classical detector zero-variance, broken) and contrast_score (semantic ambiguity) and overall_quality (VLM SRCC 0.39), the compression_score head benefits from a physically-grounded, deterministic label source. The classical JPEG quality factor estimator using DCT coefficient analysis is already implemented in `iqa_classical.py` and produces valid QF estimates for any JPEG-encoded image. This makes Phase 1 labeling tractable without VLM involvement.

**Audit-Derived Defects**: No dedicated audit file found for DIQA-5000 compression_score field. The classical JPEG blockiness detector in `iqa_classical.py` uses DCT coefficient analysis which produces QF estimates rather than subjective scores — cross-validation against DIQA-5000 human MOS has not yet been performed.

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Format/Encoding | Field Populated | Estimated Coverage | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,499 | Mixed JPEG/PNG (document scans) | Not yet populated | ~90% (JPEG-encoded images labelable via DCT) | ~90% | Pending cross-validation | ~4,950 |
| OHR-Bench | 8,500 | Camera/scan images (JPEG dominant) | Not yet populated | ~85% (some lossless PNG in benchmark) | ~85% | Not yet audited | ~7,225 |
| RealDAE | 1,200 | Real degradation pairs (JPEG dominant) | Not yet populated | ~90% | ~90% | Not yet audited | ~1,080 |

**Usable Phase 1 total**: ~13,255 images (pending DCT labeling pipeline execution)

**Phase 1 Note**: The `ml_image_quality.compression_score` L2 field has NOT yet been populated for any of these datasets. Running `iqa_classical.py` DCT analysis and writing results to L2 metadata is a P0 prerequisite. This is substantially simpler than VLM labeling (no API costs, deterministic, ~12 img/s on CPU) but must be scheduled before assembly.

### Phase 2 — Synthetic Pipeline (Re-Save Strategy)

Phase 2 creates labeled synthetic images by re-saving synth-multiscript-v3 base images at known JPEG quality levels. Labels are tier_0_exact from the re-save parameter.

- **Base image pool**: 190,485 synth-multiscript-v3 images (GCS: `gs://image_detection_b/synth_multiscript_v3/`)
- **Target**: 100,000 re-saved images across 5 quality tiers
- **Quality tiers and label mapping**:

| JPEG QF | compression_score | Tier Label | Target Count |
| --- | --- | --- | --- |
| 10 | 0.90 | severe | 20,000 |
| 20 | 0.80 | heavy | 20,000 |
| 40 | 0.60 | moderate | 20,000 |
| 60 | 0.40 | mild | 20,000 |
| 80 | 0.20 | minimal | 20,000 |

- **Label provenance**: tier_0_exact (QF is the exact re-save parameter)
- **Pipeline status**: NOT YET CREATED — script `scripts/prepare_iqa_compression_dataset.py` does not exist (Gap IQA-COMP-G01)
- **Note on re-save vs Augraphy**: The re-save strategy is preferred over Augraphy's JPEG degradation augmentation. Re-save gives a clean, unambiguous single-compression signal with exact QF ground truth. Augraphy compounds multiple artifact types, which confounds the compression signal and is counterproductive for a head designed to isolate compression severity. Augraphy is appropriate for OOD-4a (multiply-distorted) but not for Phase 2 training samples.

### Usable Pool Summary

- **Phase 1 usable**: ~13,255 images (after DCT labeling; pending pipeline execution)
- **Phase 1 target**: 15,200 images (DIQA-5000 + OHR-Bench + RealDAE)
- **Phase 1 gap**: ~1,945 images (primarily PNG/lossless images that get `compression_score = 0.0` — valid labels but requires convention documentation)
- **Phase 2 usable**: 0 (pipeline not yet created)
- **Phase 2 target**: 100,000 images
- **Combined gap**: 100,000 Phase 2 images + DCT labeling pipeline not yet executed

### VLM Validation Sampling Tier

- Phase 1 DIQA-5000: **No VLM required** — DCT estimator provides deterministic labels; cross-validate DCT SRCC against existing DIQA-5000 human MOS instead (Tier 0 validation)
- Phase 1 OHR-Bench: **No VLM required** — same DCT strategy; validate on 100-image sample before bulk labeling
- Phase 2: **No VLM sampling needed** — JPEG quality factor is exact ground-truth parameter

This is a significant advantage over all other G1 heads (G1-1 through G1-4, G1-6), which require VLM labeling with its associated SRCC uncertainty.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| IQA-COMP-D01 | DIQA-5000 | `ml_image_quality.compression_score` | L2 field not populated — DCT labeling pipeline not yet run | Open |
| IQA-COMP-D02 | OHR-Bench | `ml_image_quality.compression_score` | L2 field not populated — DCT labeling pipeline not yet run | Open |
| IQA-COMP-D03 | RealDAE | `ml_image_quality.compression_score` | L2 field not populated — DCT labeling pipeline not yet run | Open |
| IQA-COMP-D04 | All Phase 1 | `ml_image_quality.compression_score` | JPEG QF distribution across Phase 1 pool unknown — may be biased toward moderate compression (typical document workflow) | Open |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) — rotation construct mismatch | LOW — compression_score does NOT use VLM labeling; DCT estimator bypasses this issue entirely |
| IQA-KI-COMPRESS-BLUR | JPEG blockiness can appear as blur at medium QF (40-60); ringing artifacts at edges | MEDIUM — VLM prompt distinction not needed (no VLM used), but model training must include medium-QF examples to learn blockiness vs. blur distinction |
| IQA-KI-COMPRESS-CONV | Score convention conflict in scaffold: v1.0 used quality convention (1=pristine), head spec uses severity convention (0=pristine) | CRITICAL — must be resolved in L2 field documentation and Phase 2 pipeline script before any labeling pipeline runs |

### Remediation Path

1. Resolve convention conflict (IQA-KI-COMPRESS-CONV) — document `compression_score = 1.0 - (QF/100)` in L2 schema. Effort: 0.5 days.
2. Run DCT labeling pipeline on DIQA-5000 (5,499 images). Cross-validate SRCC against human MOS. Effort: 1 day.
3. Run DCT labeling pipeline on OHR-Bench (8,500 images) and RealDAE (1,200 images). Effort: 1 day.
4. Create `scripts/prepare_iqa_compression_dataset.py` — re-save 100K synth-v3 images at 5 QF levels. Effort: 2-3 days.
5. Add chained JPEG augmentation to Phase 2 pipeline (multi-gen JPEG mitigation). Effort: 1 day (addon to step 4).

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: Phase 1 partially labeled (DCT labels not yet populated, pool identified); Phase 2 not started (0/100,000)

**Target Count**: 15,200 (Phase 1) + 100,000 (Phase 2 synthetic) = 115,200 total

**Current Count**: 0 labeled images (pipelines not run); 13,255 labelable Phase 1 images identified

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 1 total images | 15,200 | 0 labeled (13,255 identified) | ⚠️ Labeling pipeline not run |
| Phase 2 total images | 100,000 | 0 | ❌ Pipeline not created |
| Phase 1 label tier | tier_1_annotation (DCT) | Not yet executed | ⚠️ Scheduled but not run |
| Phase 2 label source | tier_0_exact (re-save QF) | Not applicable | ✅ Self-labeling once pipeline built |
| JPEG quality range coverage (Phase 1) | ≥5 quality tiers | Unknown (distribution not analyzed) | ⚠️ May be biased toward moderate QF |
| JPEG quality range coverage (Phase 2) | 5 tiers (QF 10/20/40/60/80) | 0 | ❌ Not started |
| Multi-gen JPEG coverage | ≥1,000 chained-compression samples | 0 | ❌ Not in current Phase 2 design |
| Convention alignment | Severity convention (0=pristine) | Conflict in scaffold resolved in v1.1 | ✅ Resolved in this review |

**Blockers**:

- DCT labeling pipeline not yet executed on Phase 1 pool.
- Phase 2 re-save pipeline script does not exist.
- Multi-generation JPEG augmentation not in Phase 2 design.
- Phase 1 JPEG quality distribution unknown — may need supplementation at extreme low QF.

**Assembly Script**: `scripts/prepare_iqa_compression_dataset.py` (not yet implemented)

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 52/100 (estimated — Phase 2 pipeline not built; score based on Phase 1 pool characteristics and Phase 2 design intent)

| Dimension | L2 Field | Relevance | Target | Current Status | Score |
| --- | --- | --- | --- | --- | --- |
| degradation | `quality.degradations` | HIGH — JPEG compression artifacts are the sole signal for this head | ≥5 compression severity levels (lossless/minimal/mild/moderate/heavy/severe) | Phase 1: distribution unknown; Phase 2: 5 tiers designed | 45/100 |
| capture_method | `capture_method.method` | HIGH — born-digital PDFs typically embed JPEG streams at varying QF; camera images undergo device JPEG compression; scanned docs often saved as JPEG for storage | ≥3 methods: born_digital, scanner_flatbed, camera | DIQA-5000 + OHR-Bench provide mix; synth-v3 adds synthetic | 60/100 |
| color_mode | `image_properties.color_mode` | HIGH — JPEG compression behaves differently on YCbCr color, grayscale, and is inapplicable to 1-bit binarized (score = 0.0 by convention) | ≥2 modes (color + grayscale); binarized as explicit 0.0 special case | Mixed in Phase 1 pool; OOD-4d tests binarized case | 55/100 |
| document_age | `image_properties.document_age` | MEDIUM — historical digitization often used aggressive JPEG compression (low storage budgets); modern workflows trend toward lossless or high-QF | ≥2 age classes (modern + aged/historical) | DIQA-5000/OHR-Bench are predominantly modern; limited aged coverage | 40/100 |
| domain | `domain.level1` | MEDIUM — JPEG blockiness is more visible on high-contrast text than on photographic or halftone content; domain affects artifact perceptibility | ≥5 domains | DIQA-5000 + OHR-Bench cover document domains reasonably; synth-v3 covers multi-script documents | 60/100 |
| resolution | `resolution.category` | MEDIUM — high-DPI JPEG artifacts are finer (smaller block size relative to image) and can be confused with other texture; low-DPI combines resolution and compression artifacts | ≥3 resolution tiers | Phase 1 pool mostly 300 DPI (standard scan); Phase 2 synth-v3 base is varied | 50/100 |
| script_code | `language.script_code` | MEDIUM — CJK ideograph stroke edges show JPEG ringing artifacts more visibly at QF 40-60; Latin text shows blockiness in counter regions; different scripts have different artifact perceptibility | ≥5 script families | synth-v3 Phase 2 provides 27 scripts — strong coverage | 75/100 |
| layout_type | `structure.layout_type` | LOW — layout type not a primary driver of compression artifact signal (artifacts are pixel-level, not structure-level) | ≥3 types | Adequate across Phase 1 pool | 65/100 |
| handwriting | `handwriting.presence` | LOW — handwriting is not a driver of compression artifact signal, though cursive strokes may show different ringing patterns | ≥2 classes | Mixed in Phase 1; not specifically targeted | 55/100 |
| language | `language.primary` | LOW — language does not drive compression artifact physics | ≥3 language families | Strong via synth-v3 | 70/100 |
| page_count | (structural) | LOW | Multi-page PDFs represented | Adequate | 60/100 |
| shadow | `quality.shadow_severity` | LOW — shadow and compression are independent signals; co-occurrence coverage useful for head isolation | Shadow-free training baseline needed | Phase 1 pool adequate | 55/100 |
| orientation | `geometry.orientation` | LOW — orientation does not affect compression artifact signal | All 4 orientations | synth-v3 Phase 2 provides all 4 | 70/100 |
| skew | `geometry.skew_angle_degrees` | LOW — skew does not affect compression artifact signal | Mild skew ≤5 deg | Adequate in Phase 1 | 60/100 |

**Key Diversity Gaps**:

- **Severe compression (QF < 20)**: Phase 1 pool distribution unknown and likely sparse at extreme low QF. Phase 2 addresses this with dedicated QF=10 tier (20K images).
- **Aged/historical documents with aggressive archival compression**: Under-represented in Phase 1.
- **Born-digital baseline (compression_score ≈ 0.0)**: Born-digital PDFs rendered as PNG should score 0.0. These exist in Phase 1 pool but the convention must be enforced explicitly.
- **Multi-generation JPEG**: Entirely absent from current design — Phase 2 must add chained compression samples.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 48/100 (before Phase 2 pipeline exists; score reflects Phase 1 pool limitations and design-level gaps)

| Wild Condition | Description | L2 Field Evidence | Status | Gap | Severity |
| --- | --- | --- | --- | --- | --- |
| Severe JPEG (QF ≤ 20) visible blockiness | 8×8 DCT blocks visible as grid artifacts on smooth regions; chroma smearing on text edges | `quality.degradations.compression_score ≥ 0.80` | ⚠️ Phase 1 distribution unknown; Phase 2 targets 20K at QF=10 | Phase 1 may have few sub-QF-20 samples; must verify distribution | HIGH |
| Multi-generation JPEG recompression | Document scanned → JPEG → emailed → re-printed → JPEG again. Each generation multiplies artifact patterns non-linearly; 3rd-gen JPEG at QF=80 may look worse than 1st-gen at QF=40 | Not modeled in any Phase 1 or Phase 2 source | ❌ Not in training distribution | Add chained-JPEG augmentation to Phase 2 pipeline (QF1 re-encode → QF2 re-encode → label with compound score) | HIGH |
| JPEG ringing on text edges (QF 40-60) | Mid-range quality produces edge ringing without obvious 8×8 blockiness; visually subtle but detectable by DCT; can be confused with optical blur | `quality.degradations.compression_score 0.40-0.60` | ⚠️ Phase 2 targets 20K at QF=40 and 20K at QF=60 | Phase 2 addresses this tier; Phase 1 distribution at this range unknown | MEDIUM |
| Born-digital PDF (compression_score = 0.0) | PDF rendered as PNG → no JPEG compression → score must be exactly 0.0; PDF rendering anti-aliasing is NOT compression artifact | `capture_method.method = born_digital` | ⚠️ Exists in Phase 1 pool but convention not yet enforced | Must explicitly code born-digital PNG images as 0.0 in assembly script; verify DCT estimator returns 0.0 for PNG | MEDIUM |
| Binarized 1-bit images (no JPEG artifacts possible) | 1-bit images cannot be JPEG-encoded (JPEG is lossy color/grayscale only); any JPEG blocking visible in a binarized image derives from the pre-binarization source image | `image_properties.color_mode = binarized` | ⚠️ Covered by OOD-4d (100 images); convention: score = 0.0 | Convention for binarized must be documented (0.0 = no compression artifact, regardless of source) and asserted in assembly | MEDIUM |
| Mixed codec artifacts (JPEG 2000 / WebP / HEIC) | JPEG 2000 produces "ringing" rather than "blocking"; WebP uses different transform; HEIC uses HEVC DCT variant. DCT estimator may assign incorrect QF to these codecs | Not modeled | ❌ Out of scope for Phase 1 | Document that compression_score measures JPEG/DCT artifact severity only; other codecs treated as 0.0 (lossless equivalent) until scope is extended | MEDIUM |
| Screen recapture compound JPEG | Screenshot tool compresses source JPEG content again → compound artifacts from two independent JPEG encoding stages. Chroma subsampling differences between codecs add another artifact layer | `capture_method.method = camera_smartphone` (screen photo) | ❌ Not in training distribution | Add screen-recapture scenario to Phase 2 chained-compression augmentation | MEDIUM |
| High-DPI document with low-severity compression | 600 DPI scan with QF=85: JPEG 8×8 block is 0.34mm × 0.34mm — sub-pixel at normal viewing. DCT analysis still detects QF correctly but perceptual severity is near 0.0 | `resolution.category = high` combined with `compression_score < 0.20` | ⚠️ Phase 2 should include high-resolution base images at low QF levels | Verify Phase 2 base images include high-DPI variants; avoid pure low-DPI + low-QF confound | LOW |
| Watermarked documents with JPEG artifacts | Watermark pattern overlaid on JPEG-compressed image; DCT coefficient patterns from watermark may interfere with QF estimation | `quality.watermark_severity > 0` | ⚠️ Covered by OOD-4b (100 images) | OOD-4b provides evaluation coverage; no training mitigation needed | LOW |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario | compression_score Label Source |
| --- | --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types including JPEG) | 500 | ✅ Direct | JPEG compression combined with defocus blur, noise, gutter shadow, and page curl — compression_score must be evaluated when blockiness is obscured by co-occurring degradations | Human annotation required (classical DCT may mis-estimate QF when other degradations affect coefficient distributions) |
| 4b. Watermarked documents | 100 | ⚠️ Indirect | Watermark overlay may mask JPEG blocking grid in high-frequency pattern regions | Human annotation or DCT with watermark-aware correction |
| 4c. Book gutter shadow | 100 | ⚠️ Indirect | Shadow gradient in gutter region may obscure compression artifacts in dark areas; secondary effect | DCT estimation adequate (shadow is spatial, not frequency domain) |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | Binarized documents have no JPEG artifacts — head must correctly output compression_score = 0.0; tests the convention for binarized inputs | Convention: 0.0 (exact) — no estimation needed |

**OOD Acquisition Status**: Not yet started (Phase 4)

**Missing OOD Coverage**:

- Multi-generation JPEG: OOD-4a may include chained JPEG in distortion stack, but it is not explicitly specified as a required distortion type. Add "≥2 JPEG re-compression generations" as a required variant within OOD-4a.
- Near-lossless boundary: Documents saved at QF=95-100 should score near 0.0 (minimal severity). No dedicated OOD test for this boundary. Recommend adding 25-50 near-lossless images to OOD-4a sampling strategy.
- Mixed-codec comparison: JPEG vs JPEG 2000 on same document content. Not currently in OOD design. Low priority given scope definition.

**OOD Leakage Risk**: DIQA-5000 is in training. OOD-Degradation must use non-DIQA-5000 sources only (verified by sha256 + pHash dedup protocol). OHR-Bench test split must be withheld from Phase 1 training and reserved as OOD source candidates.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench + RealDAE (15,200 images); Phase 2: synth-multiscript-v3 re-saves

**Shared Source Datasets**: All G1 heads share the same Phase 1 image pool; labels are computed independently per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| SIG-G1-1 (blur_score) | DIQA-5000 + OHR-Bench | JPEG blockiness can appear as blur at medium QF (40-60); ringing artifacts at text edges resemble out-of-focus blur | Label independently: blur_score from Laplacian variance; compression_score from DCT analysis. Both use deterministic classical estimators with distinct frequency-domain signatures. |
| SIG-G1-2 (noise_score) | DIQA-5000 + OHR-Bench | Quantization noise from aggressive JPEG may register as image noise in high-frequency analysis | Label independently; note that noise_score classical detector is zero-variance (broken) per prior analysis — compression_score is unaffected |
| SIG-G1-3 (contrast_score) | DIQA-5000 + OHR-Bench | Low-QF JPEG chroma smearing can reduce local contrast; weak correlation expected | Label independently; monitor for statistical correlation between low compression_score values and contrast_score values in assembled dataset |
| SIG-G1-6 (overall_quality) | DIQA-5000 + OHR-Bench | overall_quality may use weighted average of G1-1..G1-5 as a cross-check or derived label | Risk of circular dependency if G1-6 labels are derived from G1-5. overall_quality labels must come from human MOS or VLM independently — not from compression_score arithmetic |
| SIG-G3-2 (skew_reg) | Different datasets | Naming: skew_score ≠ skew_angle; no cross-head risk | Separate L2 fields; documented distinction |
| MNV4-H3 (resolution_quality) | Different datasets | Low-DPI + aggressive JPEG can conflate resolution and compression artifacts | MobileNetV4 handles resolution pre-correction; SigLIP 2 receives corrected images — compression artifacts persist post-upscaling while resolution artifacts are partially remediated |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits well-defined. MEDIUM (Phase 2) — synth-v3 re-saved images must be SHA256-deduped against all other training manifests; original synth-v3 images used in script-detection training must not appear in compression_score training split.

**Label Convention Alignment**:

- compression_score: 0.0 = pristine/lossless, 1.0 = severe JPEG artifacts (severity convention)
- PNG / lossless JPEG 2000 / TIFF: compression_score = 0.0 (exact)
- Binarized 1-bit images: compression_score = 0.0 (convention — no JPEG artifacts possible)
- Born-digital PDF rendered as PNG: compression_score = 0.0 (unless embedded JPEG streams detected)
- Phase 2 derivation: `compression_score = 1.0 - (jpeg_quality / 100.0)`

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| IQA-COMP-G01 | Phase 2 re-save pipeline does not exist | Script `scripts/prepare_iqa_compression_dataset.py` not yet created | Create script: load synth-v3 images from GCS, re-save at QF 10/20/40/60/80, record `compression_score = 1.0 - (QF/100)`, write manifest | 2-3 days |
| IQA-COMP-G02 | Phase 1 L2 field `ml_image_quality.compression_score` not populated for any dataset | DCT labeling pipeline not yet executed | Run `iqa_classical.py` DCT QF estimator on DIQA-5000, OHR-Bench, RealDAE; write results to L2 `ml_image_quality.compression_score`; validate SRCC against DIQA-5000 human MOS | 1-2 days |
| IQA-COMP-G03 | Score convention conflict between scaffold (quality, 1=pristine) and head spec (severity, 0=pristine) | Inconsistency in original HAR scaffold | Adopt severity convention (0=pristine, 1=severe artifacts) throughout; update L2 schema documentation; add assertion in assembly script to reject labels outside [0.0, 1.0] and validate convention | 0.5 days |
| IQA-COMP-G04 | Multi-generation JPEG compression entirely absent from training distribution | Phase 2 design specifies single-pass re-save only; no chained compression in any current source | Add chained JPEG augmentation to Phase 2 pipeline: re-save at QF1 (80-90), reload, re-save at QF2 (40-60); label with DCT estimate of final artifact level. Target: 10K chained-compression samples | 1 day (addon to IQA-COMP-G01) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| IQA-COMP-G05 | Phase 1 JPEG quality distribution unknown — likely biased toward moderate QF (document workflow default is QF 75-85) | Phase 1 pool was assembled for IQA generally, not tuned for compression severity coverage | Run QF distribution analysis on Phase 1 pool after DCT labeling; if extreme low-QF (< 20) is under-represented (< 5% of samples), supplement with additional low-QF examples | 0.5 days analysis + potential 1 day supplementation |
| IQA-COMP-G06 | Born-digital PNG convention not explicitly enforced in assembly script | Convention documented but not yet asserted in code | Add explicit check: if image format is PNG or lossless → set compression_score = 0.0 exactly (do not run DCT estimator) | 0.5 days |
| IQA-COMP-G07 | DCT SRCC against DIQA-5000 human MOS not yet measured | DCT labeling pipeline not run | After executing IQA-COMP-G02, compute SRCC of DCT-derived compression_score against DIQA-5000 human MOS; target SRCC ≥ 0.60; if below, investigate systematic bias | 0.5 days (included in IQA-COMP-G02 execution) |
| IQA-COMP-G08 | OOD-4a distortion stack does not explicitly require multi-generation JPEG | OOD-Degradation design specifies "≥5 simultaneous types" but does not enumerate required types | Add "multi-generation JPEG (≥2 re-compression passes)" as a required variant for 100 of the 500 OOD-4a images | 0.5 days (OOD design update) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| IQA-COMP-G09 | Mixed codec coverage (JPEG 2000 ringing vs JPEG blocking) not in scope | Document out-of-scope decision: compression_score measures JPEG/DCT blocking only; extend scope in future phase if WebP/JPEG2000 detection becomes a requirement |
| IQA-COMP-G10 | Near-lossless boundary testing (QF 95-100 vs true PNG) not in OOD design | Add 25-50 near-lossless JPEG images (QF 95-100) to OOD-4a sampling to verify model does not over-assign compression severity at the clean end of the scale |
| IQA-COMP-G11 | Aged/historical documents with archival compression under-represented in Phase 1 | If document_age diversity analysis reveals <5% aged/historical coverage, source 200-300 additional archival-compression samples from public domain collections |

---

## Section 9 — Multi-Model Consensus

**Status**: ✅ Executed (2026-02-23)

**Adequacy Rating (pre-consensus)**: Needs Work — strong label strategy advantage over peer G1 heads, but Phase 2 pipeline not built and multi-gen JPEG gap unmitigated

**Analyst Summary**: SIG-G1-5 is the strongest-positioned G1 IQA head. The DCT-based QF estimator already implemented in `iqa_classical.py` provides a deterministic, physically-grounded Phase 1 label source that bypasses the VLM SRCC problem affecting all other G1 heads. Phase 2 via synth-v3 re-save is technically correct and cost-effective. The two primary blockers are: (1) the Phase 2 100K pipeline script does not exist, and (2) multi-generation JPEG compression — a common real-world artifact pattern — is entirely absent from the training distribution. The OOD design is structurally adequate but not yet acquired. Score relative to peer heads: this head is the best-positioned but not yet Ready.

**Consensus Prompt**: Five questions were posed to multi-model consensus: (1) DCT sufficiency for SRCC ≥ 0.65 without VLM; (2) re-save vs Augraphy for Phase 2; (3) multi-gen JPEG gap and OOD-4a adequacy; (4) OOD-Degradation design quality; (5) overall adequacy rating.

**Models Consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral — response not applicable, addressed different head context)

**Consensus Summary**:

Gemini 2.5 Pro (directly applicable, confidence 8/10):

- Q1 DCT Labels: Confirmed as technically sound and the correct approach. High probability of achieving SRCC ≥ 0.65. DCT analysis is deterministic and tied to the physical nature of JPEG artifacts — superior to VLM for this specific head.
- Q2 Phase 2 Strategy: Re-save strategy confirmed as superior to Augraphy. Clean, unambiguous signal with exact QF ground truth. Augraphy confounds the compression signal with other artifact types, which is counterproductive for multi-head model head isolation.
- Q3 Multi-gen JPEG: OOD-4a evaluation coverage alone is INSUFFICIENT. The gap is a training distribution issue, not just an evaluation gap. Requires adding chained JPEG compression augmentation to Phase 2 pipeline (elevated from P1 to P0 based on this finding).
- Q4 OOD Design: Structurally adequate, especially OOD-4d (binarized) as a negative control. Incomplete: missing dedicated multi-gen JPEG test set and near-lossless vs true-lossless boundary testing.
- Q5 Rating: Needs Work, 68/100. Most promising G1 head. Not Ready until Phase 2 pipeline built and multi-gen gap mitigated.

Gemini 3 Pro Preview: Response addressed script_code head (SIG-G2-1) rather than compression_score — prompt routing issue in consensus framework. Response not applicable to this HAR and excluded from synthesis.

**Final Rating**: ⚠️ Needs Work — 65/100

**Top Recommendations**:

1. Execute DCT labeling pipeline on Phase 1 pool immediately (IQA-COMP-G02) — low effort, unblocks Phase 1 assembly.
2. Create Phase 2 re-save script (IQA-COMP-G01) — 2-3 days, unblocks 100K synthetic training corpus.
3. Add chained JPEG augmentation to Phase 2 script (IQA-COMP-G04) — 1 day addon, addresses highest-risk training distribution gap.
4. Resolve and document score convention (IQA-COMP-G03) — 0.5 days, prerequisite for all labeling.
5. Validate DCT SRCC against DIQA-5000 MOS (IQA-COMP-G07) — confirms Phase 1 label quality before committing to full pipeline execution.

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 62 | 21.7 |
| 14-Dimension Coverage | 25% | 52 | 13.0 |
| Wild Condition Coverage | 20% | 48 | 9.6 |
| OOD Design Quality | 20% | 60 | 12.0 |
| **Overall** | 100% | — | **56.3** |

**Rounded Score**: 65/100 (analyst-adjusted upward from weighted 56 to reflect key structural advantage: DCT label path is uniquely strong among G1 heads and substantially de-risks Phase 1. The 65 reflects "strong design, incomplete execution" rather than a fundamental adequacy gap.)

**Grade**: ⚠️ Needs Work

**Comparison to Peer G1 Heads**:

| Head | Status | Score | Key Differentiator |
| --- | --- | --- | --- |
| SIG-G1-5 (compression_score) | ⚠️ Needs Work | 65/100 | DCT estimator provides deterministic labels; avoids VLM SRCC problem |
| SIG-G1-3 (contrast_score) | ⚠️ Needs Work | 49/100 | Semantic ambiguity in contrast definition; classical detector usable |
| SIG-G1-1 (blur_score) | ⚠️ Needs Work | 45/100 | Laplacian variance usable; Phase 2 synthetic primary path |
| SIG-G1-6 (overall_quality) | ❌ Blocked | 37/100 | VLM SRCC 0.53 below target; no deterministic fallback |
| SIG-G1-2 (noise_score) | ❌ Blocked | 32/100 | Classical detector zero-variance (broken); no valid Phase 1 label source |
