# Head Adequacy Review: resolution_quality_reg (SIG-G5-5)

> **Status**: 🔄 Analysis Complete — Consensus Recorded
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
| Head ID | SIG-G5-5 |
| Model | SigLIP 2 NAFlex |
| Group | G5 — Page Attributes |
| Head Name | resolution_quality_reg |
| Task Type | Regression 0-1 (char-height-aware quality score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P2 (validation head — provides teacher signal to MNV4-H3 + single-pass CPU fallback) |
| Performance Target | SRCC >= 0.70; validated against MNV4-H3 predictions |
| Primary L2 Field | `resolution.resolution_quality_score` (shared with MNV4-H3) |
| Shared-Data Heads | MNV4-H3 (shares exact training dataset) |
| Training Phase | Phase 5 — Page Attributes (trains AFTER MNV4-H3 is deployed) |

### Role Distinction from MNV4-H3

| Attribute | MNV4-H3 | SIG-G5-5 |
| --- | --- | --- |
| Input image | RAW (pre-correction) | CORRECTED (post deskew/CLAHE/sharpening) |
| Input resolution | Fixed 224x224 | NAFlex variable resolution |
| Output | Linear regression 0-1 | Gaussian NLL (mu, sigma_sq) |
| Latency | ~3ms GPU | ~50ms GPU (co-runs with 18 other heads) |
| Role | Pre-correction FAST gate; triggers upscaling | Teacher/validation; cross-checks MNV4-H3 drift; CPU fallback |
| Training order | Phase 4 (trains first) | Phase 5 (trains second; MNV4-H3 predictions available as weak labels) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `resolution.resolution_quality_score` _(float 0-1, char-height-aware; identical field to MNV4-H3)_

**Confidence Threshold**: >= 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact (PaddleOCR DBNet + CC analysis pipeline — same measurement source as MNV4-H3)

**Corrected-Image Distinction**: SIG-G5-5 trains on CORRECTED images. This means the labeling pipeline
must be applied AFTER the correction pipeline has run (deskew, CLAHE, sharpening). If training images
are raw-labeled (as in MNV4-H3), the labels will be misaligned with the actual input distribution.
This is a distinct dataset design requirement not present in the MNV4-H3 review.

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf >= 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | Complete | 99.9% (5,499 labeled, 1 error) | 99.9% (tier_3_heuristic, IQR=9px) | Coarse buckets validated (KW H=141.6) | ~5,499 |
| OHR-Bench | 8,500 | Not populated | 0% | — | Not run | 0 (RQ-SIG-G01) |
| RealDAE | 1,200 | Not populated | 0% | — | Not run | 0 (RQ-SIG-G02) |
| DocLayNet (multi-DPI renders) | TBD | Not populated | 0% | — | — | 0 (needs rendering pipeline) |
| RVL-CDIP (multi-DPI renders) | TBD | Not populated | 0% | — | — | 0 (needs rendering pipeline) |

### Corrected-Image Pipeline Requirement

The labeling pipeline for SIG-G5-5 has an additional stage not present in MNV4-H3:

1. For each source image, the full correction pipeline must be applied (deskew, CLAHE, sharpening)
2. The corrected image is the training input; the RQ label is measured on the corrected image
3. This means the label may differ slightly from MNV4-H3's label for the same source image:
   - CLAHE enhances local contrast; char-height measurement is unaffected but apparent sharpness changes
   - Deskew introduces blank margins at image edges; char-height regions near edges may yield 0px measurements
   - If MNV4-H3 triggered upscaling before SIG-G5-5 runs, SIG-G5-5 sees a post-upscale image

In practice, char-height (the primary label signal) is not materially changed by CLAHE or sharpening.
Deskew introduces at most 2-5% blank margin on extreme skew cases. The label values can be shared
with MNV4-H3 in the majority of cases, with the training image being the corrected version.
Gap RQ-SIG-G03 tracks the need to implement the corrected-image assembly path.

### Usable Pool Summary

- **Total usable before enrichment**: ~5,499 (DIQA-5000 only — same as MNV4-H3)
- **Training target**: 30,000 images (same dataset target as MNV4-H3)
- **Gap**: ~24,501 images — inherits all MNV4-H3 blockers (H3-G01, H3-G02, H3-G03)
- **Additional SIG-G5-5 gap**: corrected-image assembly path not yet implemented (RQ-SIG-G03)

### VLM Validation Sampling Tier

The RQ labeling pipeline is fully automated (PaddleOCR DBNet + CC analysis). VLM validation is not
used for resolution_quality labels. The same sampling tier logic as MNV4-H3 applies: audit validation
uses the 36-image hand-verified DIQA-5000 audit subset. Post-V2 precision target is IQR <= 3-4px
(current V1 IQR = 9.0px; V2 strategy documented in RESOLUTION_QUALITY_V2_STRATEGY.md).

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| RQ-SIG-G01 | OHR-Bench | `resolution.resolution_quality_score` | Field not populated; labeling pipeline not run | Open — inherits from MNV4-H3 H3-G01 |
| RQ-SIG-G02 | RealDAE | `resolution.resolution_quality_score` | Field not populated; labeling pipeline not run | Open — inherits from MNV4-H3 H3-G03 |
| RQ-SIG-G03 | All sources | Training image assembly | No corrected-image assembly path exists; training currently uses raw images only | Open — SIG-G5-5-specific |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-RQ-01 | PaddleOCR v2 ONLY (paddleocr>=2.7,<3.0) — v3 API incompatible; shared with MNV4-H3 | HIGH — inherited |
| KI-RQ-02 | SIGILL on Intel Broadwell CPUs; labeling must run on GPU VM | MEDIUM — inherited |
| KI-RQ-03 | V1 precision: median IQR 9.0px; coarse buckets validated (KW H=141.6, Cohen's d=0.91) | MEDIUM — inherited; V2 strategy planned |
| KI-RQ-04 | Born-digital low-DPI paradox: large fonts at 72 DPI yield high char_height despite low effective resolution | MEDIUM — inherited; OOD-Resolution 6a tests this |
| KI-G5-5-01 | CLAHE over-enhancement creates distribution shift: corrected images may appear higher quality to the model than raw images; if CLAHE settings change in production, SIG-G5-5 will silently drift | HIGH — SIG-G5-5-specific |
| KI-G5-5-02 | Post-upscale artifacts: if MNV4-H3 triggers upscaling, SIG-G5-5 sees the upscaled image; bicubic upscale creates interpolation artifacts not in training data unless training explicitly includes upscaled examples | MEDIUM — SIG-G5-5-specific |
| KI-G5-5-03 | Scheduling risk: P2 priority — SIG-G5-5 may be deferred or dropped from Phase 5 if compute is constrained; dependency on MNV4-H3 deployment completion | LOW — scheduling only |

### Remediation Path

1. **Inherit MNV4-H3 data blockers**: Resolve H3-G01 (OHR-Bench labeling), H3-G02 (multi-DPI rendering pipeline), H3-G03 (RealDAE labeling) — same remediation steps
2. **Implement corrected-image assembly path** (RQ-SIG-G03): Apply correction pipeline to assembled images before writing training manifests; re-measure RQ labels on corrected versions where necessary
3. **Implement MNV4-H3 weak label augmentation**: Once MNV4-H3 is trained, use its predictions on unlabeled images as supplementary soft labels for SIG-G5-5 training
4. **Validate CLAHE/correction pipeline consistency**: Pin correction pipeline version in training manifest metadata; alert if production correction settings deviate

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 30,000 images (same dataset as MNV4-H3) |
| Assembly Status | Not started (0/30,000 corrected-image assemblies complete) |
| Role | SIG-G5-5 is the validation head — predicts quality of the CORRECTED image delivered to OCR |
| Labels | Same char-height-aware pipeline as MNV4-H3; applied to corrected image versions |
| Distribution Target | ~49% needs_light_upscale / ~37% optimal / ~11% good / ~3% needs_major_upscale (same as MNV4-H3; distribution may shift slightly after correction) |
| Real Data Ratio | 100% real documents (no synthetic generation) |
| Split Convention | Global split registry (SHA256-keyed) — byte-identical splits with MNV4-H3 mandatory |
| MNV4-H3 Weak Labels | After MNV4-H3 is trained, its predictions on the 30K dataset serve as additional soft labels (tier_2_model) for SIG-G5-5 training; label weight: `label_confidence * (1 / max(quality_score_std, 0.01))` |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (resolution subcommand not yet implemented; must include corrected-image assembly step) |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: TBD — computed after assembly; note that the corrected-image distinction changes
the effective dimension values for degradation and resolution dimensions compared to MNV4-H3.

| Dimension | L2 Field | Relevance | Target | Current | Score | SIG-G5-5 Note |
| --- | --- | --- | --- | --- | --- | --- |
| resolution | `resolution.category` | CRITICAL — core signal; DPI tier must span full range | All 8 DPI tiers (72/100/150/200/250/300/400/600) | DIQA-5000 only (natural distribution, median 31px char_height) | TBD | After correction, DPI distribution may shift upward; multi-DPI renders critical |
| capture_method | `capture_method.method` | HIGH — scanner/camera/born-digital yield different char_height/DPI relationships | >= 3 methods (born_digital, scanner, camera_smartphone) | Unknown (DIQA-5000 composition not fully characterized) | TBD | Same analysis as MNV4-H3; born-digital low-DPI paradox inherited |
| script_code | `language.script_code` | HIGH — CJK chars are larger; char_height measurement differs by script; NaFlex advantage allows per-script char measurement at native resolution | >= 3 script families (LATN, HANS/HANT, ARAB) | Unknown | TBD | NaFlex is an advantage: higher resolution input means more accurate per-script char segmentation |
| color_mode | `image_properties.color_mode` | HIGH — CLAHE post-correction changes color_mode distribution: binarized docs are unaffected by CLAHE; color docs have enhanced contrast | >= 2 modes (color/grayscale + binarized) | Unknown | TBD | Correction pipeline does not apply CLAHE to binarized docs; color_mode distribution change is training-relevant |
| degradation | `quality.degradations` | HIGH — correction pipeline removes some degradations (blur, skew); SIG-G5-5 sees reduced degradation vs MNV4-H3; training data must reflect post-correction degradation levels | >= 3 degradation types at post-correction severity | Unknown | TBD | Post-correction images have systematically lower degradation; DIQA-5000 V1 labels were measured on raw images — re-labeling on corrected versions needed |
| domain | `domain.level1` | MEDIUM — document density affects char_height measurement reliability | >= 5 domains | Unknown | TBD | Same analysis as MNV4-H3 |
| layout_type | `structure.layout_type` | MEDIUM — dense formula/table layouts confound char_height detection; NaFlex may handle dense layout better | >= 3 types | Unknown | TBD | NaFlex higher resolution helps on dense formula/table regions |
| document_age | `image_properties.document_age` | MEDIUM — aged docs have ink spread; CLAHE may amplify historical artifacts | >= 2 age classes | Unknown | TBD | CLAHE interaction with aged docs is a distinct concern for SIG-G5-5 |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: TBD — computed after analysis

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Born-digital PDF at low DPI (large fonts → high char_height paradox) | `capture_method.method` = born_digital + `resolution.dpi` < 150 | Open | Shared with MNV4-H3 — OOD-Resolution 6a covers this; training data may lack born-digital low-DPI corrected-image examples |
| Bicubic-upscaled raster (no real resolution gain) | `resolution.upscale_factor` | Open | Shared with MNV4-H3 — OOD-Resolution 6b covers this; SIG-G5-5 additional risk: if MNV4-H3 triggers upscaling, SIG-G5-5 sees the upscaled image, which is NOT in training data |
| CLAHE over-enhancement on already-sharp images | Post-correction image properties | Open | SIG-G5-5-specific: CLAHE applied to high-contrast images may create artificial sharpness signal not corresponding to actual char resolution; OOD sub-source 6c needed |
| Post-deskew blank margins (char_height measurement at edges fails) | Image geometry post-deskew | Open | SIG-G5-5-specific: deskew on severely skewed documents introduces blank triangular margins at corners; PaddleOCR may detect zero characters in these regions; RQ score underestimation possible |
| Post-upscale interpolation artifacts (bicubic ringing) | `resolution.upscale_factor` > 1 | Open | SIG-G5-5-specific: bicubic upscaling introduces ringing artifacts at text edges; model trained without upscaled images will misjudge these as noise degradation |
| MNV4-H3 vs SIG-G5-5 divergence on ambiguous images | Inter-model comparison metric | Open | Key stress test unique to SIG-G5-5: cases where the two heads diverge by > 0.2 signal potential labeling errors or model overfitting; no OOD sub-source for this yet |
| CJK documents (larger char_height baseline) | `language.script_code` in {HANS, HANT, JPAN, KORE} | Open | Shared with MNV4-H3; NaFlex advantage expected to mitigate — needs validation |
| Documents with no text (image-only pages) | `structure.has_text` = false | Open | Shared with MNV4-H3; PaddleOCR pipeline fails gracefully with DPI-based fallback |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Resolution (Phase 6, P0, 500 total images — shared with MNV4-H3)

### OOD Sub-Sources (Shared with MNV4-H3)

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 6a. Vector PDF at 3 DPIs | 300 | DocLayNet born-digital PDFs rendered at 72/150/300 DPI (100 images each) | resolution_quality_score (measured on rendered image) | mobilenetv4 + siglip2 | Tests born-digital low-DPI paradox. SHA256+pHash dedup against training manifests required. For SIG-G5-5: images are passed through correction pipeline before scoring. |
| 6b. Upscaled rasters | 200 | OHR-Bench test set OR RealDAE subset (NOT DIQA-5000). 2x and 4x bicubic upscaling. | resolution_quality_score (measured on ORIGINAL before upscaling) + upscale_factor | mobilenetv4 + siglip2 | Tests upscale-artifact detection. SIG-G5-5 divergence from MNV4-H3 on this sub-source flags upscale-artifact sensitivity. |

### Additional OOD Sub-Sources Required for SIG-G5-5

The shared OOD-Resolution 500-image set covers the born-digital paradox and upscale artifacts but does
not cover correction pipeline artifacts that are unique to SIG-G5-5. Three additional sub-sources are
needed and tracked as Gap RQ-SIG-G04.

| Sub-Source | Images | Source | Labels Required | Purpose |
| --- | --- | --- | --- | --- |
| 6c. CLAHE over-enhanced images | 100 | Training-excluded documents with CLAHE applied at 3 clip_limit levels (1.0, 2.0, 4.0) | resolution_quality_score (pre-correction) + clahe_clip_limit | Tests whether SIG-G5-5 inflates quality score due to CLAHE-enhanced apparent contrast |
| 6d. Severely deskewed with blank margins | 100 | Training-excluded documents with >= 15 degree skew, after deskew correction | resolution_quality_score + skew_angle + blank_margin_fraction | Tests whether deskew blank margins cause underestimation of char-height near image edges |
| 6e. MNV4-H3 / SIG-G5-5 divergence cases | 100 | Sampled from DIQA-5000 val set after both models are trained; select top-50 divergence cases by \|MNV4-H3 - SIG-G5-5\| | resolution_quality_score (human-verified ground truth) | Directly tests the divergence signal; identifies whether divergence predicts labeling error or genuine model disagreement |

### OOD Evaluation Role

SIG-G5-5 is evaluated on OOD-Resolution to:

1. Cross-validate MNV4-H3 predictions — consistent agreement confirms both heads are calibrated
2. Detect correction pipeline sensitivity — sub-sources 6c/6d reveal CLAHE and deskew artifacts
3. Establish divergence threshold — sub-source 6e calibrates what |SIG-G5-5 - MNV4-H3| > delta means in practice

### OOD Acquisition Status

**Status**: Not started (Phase 6, P0 — shared with MNV4-H3); additional sub-sources 6c/6d/6e pending gap resolution RQ-SIG-G04.

### OOD Leakage Risk

Same as MNV4-H3: DIQA-5000 in training; OHR-Bench test split withheld; DocLayNet OOD renders must
use pages not in any training split. Global split registry required. Additional risk for SIG-G5-5:
correction pipeline version must be documented for every OOD image to enable future re-evaluation
if correction settings change.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| MNV4-H3 (resolution_quality) | Shares exact 30K training dataset; identical L2 label field; teacher-student relationship | Label convention must be bit-for-bit identical: both heads read the same `resolution.resolution_quality_score` from the same L2 sidecar. Training images differ (raw vs corrected). Split registry must be shared. Divergence metric `\|SIG-G5-5 - MNV4-H3\|` must be computed and monitored at inference. MNV4-H3 predictions (after Phase 4) serve as weak labels for SIG-G5-5 Phase 5 training. |
| SIG-G5-1 (capture_cls) | Different head, different dataset; born-digital capture interacts with resolution | Born-digital low-DPI paradox: capture_method=born_digital + low DPI may produce misleading resolution_quality score. Both heads must not contradict each other in downstream routing — if SIG-G5-1 predicts born_digital and SIG-G5-5 predicts high quality at 72 DPI, routing logic must handle this consistently. |
| Other G5 heads (shadow, warping, code) | Co-trained in Phase 5; share SigLIP 2 backbone | Gradient conflicts possible but resolution_quality shares low-level feature representations with IQA heads (G1 group), which is complementary. Resolution quality may compete with shadow/warping heads during gradient aggregation (PCGrad should handle this). |
| SIG-G1-6 (overall_quality) | Different construct (perceptual quality vs char-height resolution) | SIG-G5-5 measures geometric resolution; SIG-G1-6 measures perceptual quality. They are complementary, not redundant. High resolution_quality + low overall_quality indicates sharp but otherwise degraded document. Routing logic must treat these independently. |

### Ensemble Conflict Resolution Policy

When SIG-G5-5 and MNV4-H3 predictions diverge, the following policy applies at inference time:

| Scenario | Action |
| --- | --- |
| `\|SIG-G5-5_mu - MNV4-H3\|` <= 0.1 | Agreement — use SIG-G5-5_mu as final (more accurate due to NaFlex + corrected-image position) |
| `\|SIG-G5-5_mu - MNV4-H3\|` > 0.1 AND SIG-G5-5_sigma_sq < 0.05 | SIG-G5-5 is confident — override MNV4-H3 with SIG-G5-5_mu |
| `\|SIG-G5-5_mu - MNV4-H3\|` > 0.1 AND SIG-G5-5_sigma_sq >= 0.05 | Uncertainty — use conservative (lower) of the two scores; flag for quality escalation review |
| `\|SIG-G5-5_mu - MNV4-H3\|` > 0.25 (any sigma_sq) | Major divergence — flag for human review; apply safe default (needs_light_upscale treatment) |
| SIG-G5-5 unavailable (CPU-only fallback, SigLIP not loaded) | Fall back to MNV4-H3 prediction only |

The divergence threshold of 0.1 is a placeholder pending empirical calibration via OOD sub-source 6e.

### Split Leakage Risk

**Level**: MEDIUM (same as MNV4-H3)

Critical requirement: train/val/test splits must be byte-identical between MNV4-H3 and SIG-G5-5.
This is enforced by using the same global split registry entries for the shared 30K dataset.
Additional risk for SIG-G5-5: if corrected images are regenerated with different correction parameters,
SHA256 hashes will change — registry must key on source document ID, not corrected image hash.

### Label Convention

Identical to MNV4-H3: `resolution_quality_score` from L2 field `resolution.resolution_quality_score`,
log-normalized [0,1], where 0.0 = needs_major_upscale and ~0.65 = optimal (32-48px char_height range).
Any convention change applied to MNV4-H3 must be applied simultaneously to SIG-G5-5. The two heads
must never be trained on different versions of the label schema.

The Gaussian NLL output of SIG-G5-5 adds sigma_sq on top of the shared mu convention — sigma_sq
represents the model's confidence in its own prediction, not a change to the label scale.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| RQ-SIG-G01 | MNV4-H3 H3-G01 (inherited) | `resolution.resolution_quality_score` not populated in OHR-Bench L2 metadata | Labeling pipeline not yet run on OHR-Bench | Run `label_resolution_quality.py` + `integrate_resolution_quality.py` on OHR-Bench (8,500 images) on Vultr A100 VM (~11 min at 12.1 img/s) | 0.5 days (shared with MNV4-H3) |
| RQ-SIG-G02 | MNV4-H3 H3-G03 (inherited) | `resolution.resolution_quality_score` not populated in RealDAE L2 metadata | Labeling pipeline not applied to RealDAE (1,200 images) | Run labeling pipeline on RealDAE | 0.5 days (shared with MNV4-H3) |
| RQ-SIG-G03 | — | Multi-DPI rendering pipeline for DocLayNet/RVL-CDIP not yet implemented | `prepare_multitask_datasets.py resolution` subcommand not yet created | Implement resolution subcommand: render source PDFs at 8 DPI tiers, run correction pipeline on renders, run labeling pipeline, build manifest | 2-3 days (shared with MNV4-H3 H3-G02 but adds corrected-image step) |
| RQ-SIG-G04 | — | Corrected-image assembly path not implemented | SIG-G5-5 requires training on corrected images; no pipeline exists to apply correction and re-measure labels | Implement corrected-image assembly: (1) apply correction pipeline to each training image, (2) re-run RQ labeling on corrected versions where skew > 5 degrees or CLAHE is applied aggressively | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| RQ-SIG-G05 | Ensemble conflict resolution policy not formally specified or calibrated | Divergence threshold (0.1/0.25) is a placeholder; sigma_sq thresholds not yet empirically validated | After both heads are trained, run inference comparison on full DIQA-5000 val set; calibrate thresholds from divergence distribution; implement divergence logging in inference pipeline | 0.5 days (policy) + 0.5 days (inference instrumentation) |
| RQ-SIG-G06 | V2 labeling strategy not yet implemented (target ~3-4px IQR vs V1 9.0px); affects label quality for both heads | V2 plan documented but not built | Implement Phase A of V2 strategy (Sauvola binarization + morphological closing) per RESOLUTION_QUALITY_V2_STRATEGY.md | 1-2 days (shared with MNV4-H3 H3-G04) |
| RQ-SIG-G07 | OOD sub-sources 6c/6d/6e for correction pipeline artifacts not yet acquired | Correction pipeline OOD design not yet documented in OOD_DATASET_CATALOG.md | Define and acquire: (a) CLAHE over-enhanced images, (b) post-deskew blank margin images, (c) MNV4-H3/SIG-G5-5 divergence cases from val set | 1 day design + 1 day acquisition (after models are trained) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| RQ-SIG-G08 | MNV4-H3 weak label integration not yet designed; training order dependency not tracked | After MNV4-H3 Phase 4 training, generate predictions on the 30K dataset; integrate as tier_2_model soft labels for SIG-G5-5 Phase 5 training using uncertainty-weighted MSE loss |
| RQ-SIG-G09 | NaFlex token budget not configured for resolution quality task | High-resolution documents may be internally downscaled by NaFlex beyond the point where char-height discrimination is precise; configure NaFlex minimum resolution to preserve >= 32px per char-height |
| RQ-SIG-G10 | DIQA-5000 script composition not characterized | Unknown whether DIQA-5000 has sufficient CJK/Arabic coverage; if predominantly Latin, CJK quality estimation will be undertrained; audit DIQA-5000 script distribution |

---

## Section 9 — Multi-Model Consensus

**Status**: Consensus complete (2026-02-23)

**Adequacy Rating (pre-consensus)**: Needs Work — ~38/100 weighted score (source pool 30/100,
14-dimension coverage 40/100, wild conditions 35/100, OOD design 55/100)

**Analyst Summary**: SIG-G5-5 is architecturally well-positioned — the corrected-image input is an
advantage (OCR sees the corrected image, so quality scored on the corrected image is the correct
construct), and NAFlex variable resolution provides meaningfully more accurate char-height estimation
than MNV4-H3's fixed 224x224 input. However, three blockers prevent training: (1) the 24.5K training
data gap inherited from MNV4-H3, (2) the corrected-image assembly path does not exist, and (3) the
ensemble conflict resolution policy is undefined. The OOD-Resolution 500-image shared set is
adequate for the shared scenarios but does not cover CLAHE over-enhancement, deskew blank margins,
or post-upscale artifacts — correction pipeline failure modes that MNV4-H3 never encounters.

**Consensus Prompt**: Five questions on (Q1) raw vs corrected image training design,
(Q2) NAFlex resolution advantage, (Q3) ensemble conflict resolution policy,
(Q4) OOD adequacy for correction pipeline artifacts, (Q5) overall adequacy rating.

**Models Consulted**:

- google/gemini-2.5-pro (neutral, 9/10 confidence)
- google/gemini-3-pro-preview (neutral — response drifted to handwriting head; not usable for this review)

**Consensus Summary**:

Gemini 2.5 Pro (9/10 confidence) provided detailed, on-topic analysis across all five questions:

**Q1 — Raw vs corrected training**: Training on corrected images is a clear ADVANTAGE. The corrected
image is what the OCR engine actually processes, so quality scored on the corrected image reflects
actual OCR input quality. Distribution shift risk exists if correction pipeline settings change at
inference time, but this is manageable through pipeline version pinning. Paired (raw, corrected)
images are not required in the training set — corrected-only is sufficient. However, having pairs
available aids failure analysis.

**Q2 — NAFlex variable resolution**: Confirmed as a SIGNIFICANT ADVANTAGE. NAFlex processes images
at resolutions that preserve fine character details. The critical benefit is in discriminating the
boundary between "needs_light_upscale" (score ~0.5) and "optimal" (score ~0.65), corresponding to
char heights around 24-32px. At fixed 224px input, a 28px character occupies ~12% of image height
and is difficult to discriminate precisely. NaFlex at higher resolution represents that same
character at a higher fraction of total image height, enabling finer-grained quality estimation.
Risk: NaFlex may internally downscale extremely high-resolution inputs; NaFlex token budget must be
configured to preserve a minimum pixel count per character.

**Q3 — Ensemble conflict resolution**: The sigma_sq Gaussian NLL output is the primary arbiter.
Policy (confirmed as correct by consensus): (a) when SIG-G5-5 sigma_sq is low (high confidence),
SIG-G5-5 overrides MNV4-H3 regardless; (b) when both models are confident and diverge, use the
more conservative (lower) quality score to minimize OCR failure risk; (c) when SIG-G5-5 sigma_sq
is high (uncertain), fall back to MNV4-H3 or auto-trigger upscale as a safe default; (d) major
divergence (> 0.25) escalates to human review or quality escalation workflow.

**Q4 — OOD adequacy**: Current 500-image OOD-Resolution set is INADEQUATE for SIG-G5-5's specific
position. Additional sub-sources are needed for CLAHE over-enhancement, deskew blank margin effects,
and post-upscale artifacts. These are failure modes specific to SIG-G5-5 that MNV4-H3 never
encounters. The recommendation to add sub-sources 6c/6d/6e (tracked as RQ-SIG-G07) is confirmed.

**Q5 — Overall adequacy rating**: NEEDS WORK (not Blocked). Architecture is sound and the design
decisions are correct. The head is not ready for training due to the data gap and missing corrected-
image assembly path, but these are standard implementation tasks rather than architectural problems
requiring redesign. The Gaussian NLL head output is a meaningful upgrade over MNV4-H3's linear
regression for the teacher/validation role.

**Final Rating**: Needs Work

**Top Recommendations**:

1. **Resolve training data gap**: Run RQ labeling pipeline on OHR-Bench (8.5K) and RealDAE (1.2K)
   on GPU VM; implement multi-DPI rendering pipeline for DocLayNet/RVL-CDIP to reach 30K target
2. **Implement corrected-image assembly path**: Apply correction pipeline before writing training
   manifests; re-measure RQ labels on corrected versions for high-skew images; pin correction
   pipeline version in manifest metadata
3. **Define ensemble conflict resolution policy**: Formally specify sigma_sq thresholds for
   override/fallback/escalation; implement divergence logging at inference; add OOD sub-sources
   6c/6d/6e for correction pipeline artifacts after both models are trained

### Scoring Summary

| Component | Weight | Score | Weighted | Notes |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 28/100 | 9.8 | 5.5K/30K (18% complete); corrected-image assembly path missing |
| 14-Dimension Coverage | 25% | 40/100 | 10.0 | 6/8 dimensions unknown; CLAHE/correction effects on dimensions not yet characterized |
| Wild Condition Coverage | 20% | 38/100 | 7.6 | 3 inherited conditions from MNV4-H3 + 3 SIG-G5-5-specific correction artifact conditions all open |
| OOD Design Quality | 20% | 58/100 | 11.6 | Shared OOD-Resolution 500 images adequate for shared scenarios; 3 SIG-G5-5-specific sub-sources missing (6c/6d/6e) |
| **Overall** | 100% | — | **39.0** | — |

**Grade**: Needs Work (39/100)

**Comparison to MNV4-H3**: SIG-G5-5 scores slightly lower than the equivalent MNV4-H3 review would
score because it has all of MNV4-H3's gaps PLUS the corrected-image assembly gap (RQ-SIG-G04) and
the OOD correction-artifact gap (RQ-SIG-G07). Resolving MNV4-H3's P0 blockers automatically
resolves RQ-SIG-G01/G02/G03 for SIG-G5-5, but RQ-SIG-G04 and RQ-SIG-G07 require additional work.
