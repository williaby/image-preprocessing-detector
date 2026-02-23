# Head Adequacy Review: resolution_quality (MNV4-H3)

> **Status**: Needs Work
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: D — Resolution
> **Adequacy**: Needs Work

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | MNV4-H3 |
| Model | MobileNetV4-Conv-S |
| Group | Pre-Correction Stage Gate |
| Head Name | resolution_quality |
| Task Type | Regression 0-1 (char-height-aware quality score) |
| Output Format | Linear output [0-1] |
| Priority | P0 |
| Performance Target | SRCC ≥ 0.70 with human MOS or OCR degradation metric; MAE < 0.1 on held-out validation set |
| Primary L2 Field | `resolution.resolution_quality_score` (0-1) |
| Shared-Data Heads | SIG-G5-5 (resolution_quality_reg — uses same 30K training dataset; SigLIP 2 validation head) |
| Training Phase | Phase 4 — Pre-Correction Gate (trained before SigLIP 2) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `resolution.resolution_quality_score` _(float 0-1, char-height-aware)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_3_heuristic (V1: PaddleOCR DBNet text detection + CC analysis pipeline).
V2 will upgrade to tier_2_model (Sauvola + ensemble + calibration) once implemented.

**Audit-Derived Defects**: V1 IQR precision = 9.0px (target 2-3px); 54% cross-bucket rate. Coarse
bucket classification validated (KW H=141.6, p=1.7e-30, Cohen's d=0.91, 3% anomaly rate). Continuous
regression scores are noisy but directionally correct.

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | Yes (V1 complete) | 99.9% (5,499 labeled, 1 error) | ~80% estimated (V1 precision degrades confidence near bucket boundaries) | V1 coarse buckets validated; regression precision suboptimal | 5,499 |
| OHR-Bench | 8,500 | No | 0% | — | Labeling pipeline validated, not yet run | 0 (ready to label) |
| RealDAE | 1,200 | No | 0% | — | Labeling pipeline validated, not yet run | 0 (ready to label) |
| DocLayNet (multi-DPI renders) | 81,000 source pages (subset to render) | No | 0% | — | Needs multi-DPI rendering pipeline | 0 (needs 2-3d implementation) |
| synth-multiscript-v3 | 190,485 | No | 0% | — | Known DPI at generation; char_height measurable via generator metadata | 0 (feasible via sidecar metadata) |

### Usable Pool Summary

- **Total usable now**: 5,499 (DIQA-5000 V1 labels only — 18% of target)
- **Training target**: 30,000 images
- **Gap**: ~24,501 images
- **Fastest path to close gap**: Run labeling pipeline on OHR-Bench (8,500; ~11 min on A100) + RealDAE
  (1,200; ~2 min) → reaches ~15,200 (51% of target). Multi-DPI rendering pipeline for DocLayNet
  fills the remainder.

### VLM Validation Sampling Tier

Not applicable for this head. Resolution quality labels are derived from automated char-height
measurement (PaddleOCR DBNet + CC analysis), not VLM annotation. Audit validation uses a 36-image
audit sample and a 300-500 image gold standard set (per V2 strategy Phase C). No VLM sampling tier
is required.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| RQ-MNV4-D01 | DIQA-5000 | `resolution.char_height_px` | V1 median IQR = 9.0px vs. 2-3px target; 54% cross-bucket rate near boundary values | Open — V2 strategy planned |
| RQ-MNV4-D02 | DIQA-5000 | `resolution.resolution_quality_score` | Score range compression: 83% of images fall in 2.5-3.2 MOS range after bucket normalization, limiting regression gradient signal | Open — V2 score distribution review needed |
| RQ-MNV4-D03 | DIQA-5000 | `resolution.char_height_px` | CJK radical fragmentation: disconnected strokes fragment into short CCs, deflating median char_height for CJK documents | Open — V2 Phase A morphological closing addresses this |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-RQ-01 | PaddleOCR v2 ONLY (`paddleocr>=2.7,<3.0`) — v3 API completely incompatible; labeling pipeline will silently fail on v3 | HIGH — version pin must be enforced in requirements |
| KI-RQ-02 | SIGILL on Intel Broadwell CPUs: PaddlePaddle CPU path hits illegal instruction (no AVX-512) | MEDIUM — labeling must run on GPU VM (Vultr A100 or equivalent) |
| KI-RQ-03 | V1 precision: median IQR 9.0px (target 2-3px), 54% cross-bucket rate; coarse label quality sufficient for training bootstrap but not production | MEDIUM — V2 strategy planned; bootstrap OK, production requires V2 |
| KI-RQ-04 | Born-digital low-DPI paradox: large fonts at 72 DPI yield high char_height despite low effective resolution — the label is correct (high char_height IS OCR-optimal), but training set must include these examples explicitly to prevent model overfitting to scanner noise as proxy for quality | MEDIUM — see OOD-Resolution 6a and RQ-MNV4-G05 |

### Remediation Path

1. Run `scripts/label_resolution_quality.py` + `scripts/integrate_resolution_quality.py` on
   OHR-Bench (8,500 images) on Vultr A100 VM (~11 min at 12.1 img/s) — Gap IDs: RQ-MNV4-G01
2. Run same labeling pipeline on RealDAE (1,200 images) — Gap ID: RQ-MNV4-G02
3. Implement `prepare_multitask_datasets.py resolution` subcommand: render source PDFs at 8 DPI
   tiers (72/100/150/200/250/300/400/600), run labeling pipeline, build manifest — Gap ID: RQ-MNV4-G03
4. Implement V2 precision improvements (Phase A: Sauvola + morphological closing + KDE mode) —
   Gap ID: RQ-MNV4-G04
5. Validate bucket distribution matches target (~49% needs_light_upscale / ~37% optimal /
   ~11% good / ~3% needs_major_upscale) across assembled pool

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 30,000 images |
| Assembly Status | In progress — 5,499/30,000 (18%) |
| Current Labeled | DIQA-5000 complete (5,499 images, median char_height=31px, median score=0.525) |
| Distribution Target | ~49% needs_light_upscale \| ~37% optimal \| ~11% good \| ~3% needs_major_upscale |
| Multi-DPI Rendering | Source docs rendered at 72/100/150/200/250/300/400/600 DPI to populate lower-resolution training examples |
| Real Data Ratio | 100% real documents (no synthetic generation — labels derived from actual image measurements) |
| Label Source | Character-height-aware pipeline: PaddleOCR DBNet text detection + CC analysis (two-stage) |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (resolution subcommand not yet implemented) |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall DDR Score**: 20.0/100 (DDR audit run 2026-02-21 — see
`docs/datasets/diversity_reports/resolution_quality_ddr.md`)

**DDR Audit Status**: The automated DDR scores 0.0/100 for wild condition coverage and
14-dimension diversity because the training manifest has not yet been assembled (L2 metadata not
linked to the 5,499 DIQA-5000 images in the diversity evaluation pipeline). Label quality scores
50.0/100. The scores below reflect human analysis of DIQA-5000 characteristics and the known
composition of planned source datasets.

| Dimension | L2 Field | Relevance | Target | Current (DIQA-5000) | Score |
| --- | --- | --- | --- | --- | --- |
| resolution_dpi | `resolution.category` | CRITICAL — core signal for this head; DPI tier coverage must span full range | All 8 DPI tiers (72/100/150/200/250/300/400/600) represented | Natural distribution of scanned documents; no controlled DPI coverage; 72-150 DPI tier likely underrepresented | 2/5 |
| capture_method | `capture_method.method` | HIGH — scanner, camera, and born-digital yield different char_height/DPI relationships; model must not learn scanner noise as proxy for quality | ≥ 3 methods (born_digital, scanner, camera_smartphone); ≥ 20% born_digital required | DIQA-5000 is predominantly scanned documents; born_digital fraction unknown but likely low | 2/5 |
| script_code | `language.script_code` | HIGH — CJK characters are naturally larger (approx. 1.5x Latin height); char_height measurement differs by script; CJK radical fragmentation degrades V1 precision | ≥ 3 script families (LATN, HANS/HANT, ARAB); ≥ 15% CJK | DIQA-5000 is predominantly Latin; CJK fraction unknown | 2/5 |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs lose fine character structure; CC-based measurement behavior changes; Sauvola binarization handles this differently from Gaussian adaptive | ≥ 2 modes (color/grayscale + binarized) | Predominantly grayscale/color; binarized fraction unknown | 2/5 |
| domain | `domain.level1` | MEDIUM — document density affects char_height measurement reliability; dense legal/scientific documents have different char_height distributions | ≥ 5 domains | DIQA-5000 covers varied document types but domain balance unknown | 3/5 |
| layout_type | `structure.layout_type` | MEDIUM — dense formula/table layouts confound char_height detection; single-column vs. multi-column affects measurement regions | ≥ 3 types | DIQA-5000 includes mixed layout documents | 3/5 |
| document_age | `image_properties.document_age` | MEDIUM — aged docs have ink spread affecting apparent char boundaries; V2 Sauvola handles this better than V1 Gaussian | ≥ 2 age classes (modern + aged) | Mostly modern documents | 2/5 |
| degradation | `quality.degradations` | MEDIUM — blur/noise reduce effective char_height measurement accuracy; training must include degraded-but-readable documents to learn the distinction | ≥ 3 degradation types; blur at multiple severity levels | DIQA-5000 includes blur, noise, contrast degradation types | 3/5 |

**Critical Coverage Gaps**:

- Born-digital low-DPI examples are almost certainly absent from DIQA-5000 (all scanned). This is
  the most critical gap: without these examples, the model may learn "scanner texture = high quality"
  as a spurious feature.
- Low-DPI tier (72-150 DPI) coverage is likely underrepresented in DIQA-5000 (scanned docs are
  typically ≥ 200 DPI).
- CJK and non-Latin script coverage in DIQA-5000 is unknown but presumed low.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 1/6 conditions covered or partially covered (DDR Section 1 reports 0.0/100 —
no conditions formally covered with current unlinked manifest)

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Born-digital PDF at low DPI (large fonts → high char_height despite low effective pixel density) | `capture_method.method` = born_digital + `resolution.dpi` < 150 | Not covered | Critical: DIQA-5000 is scan-dominated; born-digital low-DPI examples absent. Char-height scoring handles this CORRECTLY (high char_height at 72 DPI IS OCR-optimal), but model must see examples to avoid spurious feature learning. OOD-Resolution 6a tests this; training distribution must include it. Gap ID: RQ-MNV4-G05 |
| Bicubic-upscaled raster (2x/4x interpolation artifacts; no new information despite higher DPI) | `resolution.upscale_factor` | Not covered | Model must learn that bicubic-upscaled images have artificially crisp edges but reduced effective OCR quality. Labels derived from pre-upscale originals. OOD-Resolution 6b tests this; training requires examples. Gap ID: RQ-MNV4-G06 |
| High-DPI scan with optical blur (300+ DPI but illegible due to camera motion or defocus) | `quality.degradations` includes blur | Partial | DIQA-5000 includes blur examples at natural severity; high-DPI-with-severe-blur combination may be underrepresented. Gemini 3 Pro raised this as an OOD gap: pixel count alone does not predict readability. Gap ID: RQ-MNV4-G07 |
| CJK documents with large naturally-sized characters | `language.script_code` in {HANS, HANT, JPAN, KORE} | Not covered | CJK chars are ~1.5x Latin height; char_height measurement via V1 CC pipeline is degraded by radical fragmentation (KI-RQ-03). Score may overestimate quality. V2 Phase A morphological closing addresses measurement; training data gap remains. |
| Image-only pages (no text; PaddleOCR detects nothing) | `structure.has_text` = false | Partial | Label falls back to DPI-based heuristic (fallback path exists in labeling script). Label quality for text-absent pages is lower (DPI heuristic, not char-height measurement). Gap ID: RQ-MNV4-G07 |
| Mixed-resolution spreads (high-DPI cover page + low-DPI body in same PDF) | No dedicated L2 field | Not covered | Page-level scoring cannot represent mixed-DPI within a document. Score reflects overall page char_height distribution. Low priority — page-level model scope is appropriate. |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Resolution (Phase 6, P0, 500 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 6a. Vector PDF at 3 DPIs | 300 | DocLayNet born-digital PDFs rendered at 72/150/300 DPI (100 pages × 3 DPIs) | `resolution_quality_score` (measured on rendered image), `capture_method=born_digital`, `color_mode` | mobilenetv4 + siglip2 | Tests born-digital low-DPI paradox: large fonts at 72 DPI → high char_height despite low effective resolution. Must SHA256+pHash dedup against training manifests. Use pages NOT overlapping with DocLayNet training images. |
| 6b. Upscaled rasters | 200 | OHR-Bench test set or RealDAE subset (NOT DIQA-5000 — in training). 2× and 4× bicubic upscaling (100 images × 2 factors). | `resolution_quality_score` (measured on ORIGINAL before upscaling), `capture_method` (as original), `color_mode`, `upscale_factor` (2 or 4) | mobilenetv4 + siglip2 | Labels derived from pre-upscale originals. Tests whether head correctly predicts quality of underlying document, not the interpolated image. DIQA-5000 must NOT be used — it is in training. |

### OOD Coverage Gaps (Identified by Consensus)

Two gaps were raised by both Gemini models:

1. **High-DPI-but-blurry optical degradation** (P1): A 300 DPI scan with camera motion blur or
   defocus has high pixel count but low effective readability. Neither current sub-source covers this
   combination. Recommended: add 100-image sub-source (6c) from OHR-Bench degraded scans or
   artificially blurred high-DPI rasters. Gap ID: RQ-MNV4-G08
2. **JPEG compression artifacts at varied DPI** (P2): Aggressive JPEG compression (quality 10-30)
   reduces apparent character resolution via DCT blocking. Affects both born-digital and scanned
   documents. Recommended for future OOD expansion. Gap ID: RQ-MNV4-G09

### OOD Acquisition Status

**Status**: Not started (Phase 6, P0)

### OOD Leakage Risk

DIQA-5000 is in training. OHR-Bench test split must be withheld from training labels — only the
OHR-Bench test split is eligible for OOD-Resolution 6b. DocLayNet OOD images for 6a must use pages
NOT overlapping with DocLayNet images used in any other training dataset (global split registry
required). All OOD images require SHA256 + pHash dedup (Hamming ≤ 5) against all training manifests
before registration.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G5-5 (resolution_quality_reg) | Shares exact same 30,000 image training dataset; SigLIP 2 validation head | Must use global split registry (SHA256-keyed). MNV4-H3 is the fast pre-correction gate (~3ms); SIG-G5-5 is the SigLIP validation head (~50ms). Both read the same L2 field. MNV4-H3 trains first (Phase 4); its predictions can serve as weak labels for SIG-G5-5 (Phase 5). |
| MNV4-H1 (orientation) | Same model, different head | Resolution quality inference occurs after orientation/skew correction in the pipeline — pipeline ordering must be respected. Training images should be orientation-corrected before resolution labeling to reflect the actual corrected-document quality the model will see at inference time. |
| MNV4-H2 (skew_reg) | Same model, different head | Same pipeline ordering dependency as MNV4-H1. Skew-distorted images have reduced effective resolution; labels should reflect corrected document quality. |

### Split Leakage Risk

**Level**: MEDIUM

DIQA-5000 is fully in training. OHR-Bench test split withheld from training. DocLayNet OOD renders
(6a) must use pages not appearing in any other training split. Global split registry (SHA256-keyed)
required for all DocLayNet and RVL-CDIP derived images across all training datasets. Synth-multiscript-v3
images used in OOD must be tagged `split_type=ood` before any training manifest is generated.

### Label Convention

`resolution_quality_score` uses a log-normalized scale: 0.0 = needs_major_upscale (char_height
< 8px, document unreadable for OCR), ~0.3-0.4 = needs_light_upscale (char_height 8-24px), ~0.5-0.65
= optimal range (char_height 32-48px — ideal for OCR), ~0.7+ = good to high resolution beyond optimal
(char_height > 48px). This convention must be identical between MNV4-H3 and SIG-G5-5 — both heads
read the same L2 field `resolution.resolution_quality_score`.

### Cascade Dependency Warning

MNV4-H3 is the earliest quality gate in the pipeline. An incorrect resolution quality prediction
propagates downstream:

- If MNV4-H3 mislabels a low-quality document as acceptable → SigLIP 2 receives blurry/low-res
  input → all 19 SigLIP 2 heads degrade in accuracy.
- If MNV4-H3 mislabels a high-quality document as needing upscaling → unnecessary upscaling pass
  adds latency and may introduce interpolation artifacts.

This cascade dependency makes MNV4-H3 a P0 blocker for the overall pipeline quality.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| RQ-MNV4-G01 | `resolution.resolution_quality_score` not populated in OHR-Bench L2 metadata | Labeling pipeline not yet run on OHR-Bench (8,500 images) | Run `scripts/label_resolution_quality.py` + `scripts/integrate_resolution_quality.py` on OHR-Bench on Vultr A100 VM (~11 min at 12.1 img/s). Adds ~8,500 images to pool. | 0.5 days |
| RQ-MNV4-G02 | `resolution.resolution_quality_score` not populated in RealDAE L2 metadata | Labeling pipeline not yet run on RealDAE (1,200 images) | Run labeling pipeline on RealDAE. Adds ~1,200 images to pool. | 0.25 days |
| RQ-MNV4-G03 | Multi-DPI rendering pipeline for DocLayNet not yet implemented; 72/100/150 DPI tier underrepresented in pool | `prepare_multitask_datasets.py resolution` subcommand not yet created | Implement resolution subcommand: render DocLayNet source PDFs at 8 DPI tiers (72/100/150/200/250/300/400/600), run labeling pipeline on rendered images, build manifest. Adds ~15,000 images to pool. | 2-3 days |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| RQ-MNV4-G04 | V2 labeling precision not yet implemented: V1 IQR = 9.0px vs. target 4-5px; 54% cross-bucket rate | V2 plan documented but not built (Sauvola + morphological closing + KDE mode + projection profiles) | Implement V2 Phase A (Sauvola binarization + morphological closing + KDE mode) in `src/image_preprocessing_detector/schema_utils/resolution_quality.py`. Estimated improvement: IQR 9px → 6-7px. Then Phase B (ensemble + DBSCAN): IQR → 4-5px. | Phase A: 1-2 days; Phase B: 3-4 days |
| RQ-MNV4-G05 | Born-digital low-DPI examples absent from training distribution (DIQA-5000 is scan-dominated) | Multi-DPI rendering pipeline not yet built; all current labels are from scanned documents | Include born-digital low-DPI renders explicitly in training pipeline via DocLayNet rendering at 72/100 DPI (part of RQ-MNV4-G03). Must ensure ≥ 10% of training pool is born-digital, ≥ 5% is born-digital at < 150 DPI. | Part of RQ-MNV4-G03 |
| RQ-MNV4-G06 | Upscaling artifact examples absent from training distribution | No upscaling simulation in current labeling pipeline | Add 2x/4x bicubic upscaling augmentation to `prepare_multitask_datasets.py resolution` pipeline. Labels derived from pre-upscale originals. | 0.5 days (part of RQ-MNV4-G03) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| RQ-MNV4-G07 | CJK char_height calibration not validated (CJK chars naturally ~1.5x Latin height; score may overestimate quality if CJK is underrepresented in training) | Add CJK-stratified validation during resolution labeling; audit DIQA-5000 CJK subset; ensure ≥ 10% CJK scripts in final 30K pool |
| RQ-MNV4-G08 | High-DPI-but-blurry optical degradation not covered in OOD (pixel count high but content unreadable) | Add OOD-Resolution 6c sub-source: 100 high-DPI scans with controlled optical blur applied. Source from OHR-Bench degraded subset or artificially blurred RealDAE images. |
| RQ-MNV4-G09 | JPEG compression artifacts not covered in OOD (aggressive DCT blocking reduces apparent char resolution) | Add OOD-Resolution 6d sub-source (future): 50 images with JPEG quality 10-30 applied to varied-DPI source documents |
| RQ-MNV4-G10 | Image-only pages (no text) rely on DPI heuristic fallback — fallback formula not formally documented | Define and document DPI-only fallback label formula for text-absent pages in labeling script docstring and L2 schema notes |

---

## Section 9 — Multi-Model Consensus

**Status**: Complete (2026-02-23)

**Adequacy Rating**: Needs Work

**Analyst Summary**: MNV4-H3 is architecturally sound with a clear remediation path. The labeling
script exists, has been validated on DIQA-5000, and runs at 12.1 img/s on an A100. The char-height-
aware scoring strategy is the correct approach — it directly models OCR readability rather than
relying on DPI metadata that frequently misrepresents effective document quality. The core blocker is
data volume (5,499/30,000 labeled, 18%) and V1 label precision (IQR 9px vs. 4-5px target). The path
to 30K is clear: run OHR-Bench + RealDAE labeling (adds ~9,700), implement multi-DPI rendering
pipeline for DocLayNet (adds ~15,000). V2 precision improvements should be parallelized with data
collection. The head is NOT blocked — bootstrap training can begin immediately with V1 data to
validate the architecture and identify which data subsets need priority re-labeling.

**Consensus Prompt Summary**: Five questions evaluated — (1) bootstrap with V1 data vs. wait for
V2, (2) char-height vs. DPI scoring strategy, (3) born-digital paradox handling, (4) OOD design
adequacy, (5) overall rating.

**Models Consulted**: google/gemini-2.5-pro (neutral, 8/10), google/gemini-3-pro-preview (neutral, 9/10)

**Consensus Continuation ID**: 67208f6f-df4b-42ac-9396-57444d708ef2

### Consensus Findings

#### Points of Agreement (2/2 models)

| Question | Finding | Confidence |
| --- | --- | --- |
| Q1: Bootstrap with V1 data? | V1 labels are acceptable for bootstrapping and pipeline validation. Do not block on V2 precision before starting training. V2 precision is required for production deployment but not for architecture validation. | 8-9/10 |
| Q2: Char-height vs. DPI? | Char-height-aware scoring is unambiguously correct. DPI is metadata, frequently inaccurate, and decoupled from OCR readability. Char-height directly models the downstream success criterion. | 8-9/10 |
| Q3: Born-digital paradox? | Char-height scoring mathematically resolves the paradox. However, the training distribution must explicitly include born-digital examples. Without them, the model may overfit to scanner noise/texture as a proxy for "high quality." The scoring logic solves it; the training distribution must enforce it. | 8-9/10 |
| Q4: OOD design gaps? | Both models identified high-DPI-but-blurry optical degradation as a missing OOD sub-source. The current 2 sub-sources are a good start but leave this failure mode untested. | 8-9/10 |
| Q5: Overall rating? | Needs Work. Not Blocked. Recommended strategy: start bootstrap training now with V1 data; parallelize V2 labeling and dataset expansion campaigns. | 8-9/10 |

#### Points of Divergence

| Topic | Gemini 2.5 Pro | Gemini 3 Pro Preview |
| --- | --- | --- |
| Priority of V2 precision | V2 is a mandatory prerequisite for production; do not deploy on V1 labels alone | V2 is important but bootstrap now; "waiting for V2 before training is a strategic error" |
| Bootstrap timing | Acceptable for baseline but V2 must follow before production | Start immediately; use V1 results to guide which data subsets to prioritize for V2 re-labeling |

Both positions are compatible. The resolution: begin bootstrap training with V1 data in parallel
with V2 label precision improvements. Do not deploy to production until V2 labels cover ≥ 80% of
training pool.

### Consensus Recommendations

1. **Start bootstrap training immediately** with current 5,499 V1 labels. Use results to validate
   architecture convergence and identify high-error data subsets for priority V2 re-labeling. Do not
   block training on data completion.

2. **Run OHR-Bench and RealDAE labeling pipelines** before next training iteration. This is a
   0.75-day effort that adds ~9,700 images (reaching 51% of target) and captures different document
   degradation profiles than DIQA-5000.

3. **Ensure born-digital examples are explicitly included in training distribution**. Multi-DPI
   DocLayNet renders (RQ-MNV4-G03) must target ≥ 10% born-digital at < 150 DPI to prevent the model
   from learning scanner texture as a quality proxy.

4. **Implement V2 Phase A** (Sauvola binarization + morphological closing + KDE mode) before final
   production training run. This is a 1-2 day effort that reduces IQR from 9px to ~6-7px. Phase B
   (ensemble + DBSCAN) for 4-5px precision should follow.

5. **Add OOD-Resolution 6c** (high-DPI-but-blurry, 100 images) to cover optical degradation at
   high pixel count — a failure mode distinct from the two current sub-sources.

### Scoring Summary

| Component | Weight | Score | Weighted | Rationale |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 2/10 | 0.70 | 5,499/30,000 (18%); labeling script validated; path to 30K clear; V1 precision suboptimal but usable for bootstrap |
| 14-Dimension Coverage | 25% | 2/10 | 0.50 | DDR formal score 0.0/100 (manifest not linked); human analysis: born-digital/low-DPI/CJK dimensions critically underrepresented in DIQA-5000 |
| Wild Condition Coverage | 20% | 2/10 | 0.40 | Born-digital paradox not covered in training; upscaling artifacts absent; high-DPI-blur gap in OOD; char-height scoring handles paradox correctly but training distribution does not yet reflect it |
| OOD Design Quality | 20% | 5/10 | 1.00 | Design is well-specified (2 targeted sub-sources testing the two primary failure modes); acquisition not started; high-DPI-blur gap identified by both consensus models |
| **Overall** | 100% | — | **2.60/10** | Weighted sum |

**Normalised Grade**: 26/100

**Grade**: Needs Work

**Interpretation**: The conceptual and technical design is sound. Every major design decision
(char-height scoring, DPI safety rails, cascade gate position) is validated by consensus. The low
score reflects execution gaps in data volume and coverage — both of which are on a clear remediation
path. The head is not blocked. Re-score expected to reach ≥ 6.0/10 after OHR-Bench + RealDAE
labeling + multi-DPI rendering pipeline.
