# Head Adequacy Review: contrast_score (SIG-G1-3)

> **Status**: ✅ Complete
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: B — IQA
> **Adequacy**: ⚠️ Needs Work (49/100)

---

## Section 1 — Head Identity

| Field | Value |
| --- | --- |
| Head ID | SIG-G1-3 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | contrast_score |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | SRCC ≥ 0.65 with classical histogram contrast or human annotations |
| Primary L2 Field | `ml_image_quality.contrast_score` (Phase 1) OR augmentation parameter (Phase 2) |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: edge-aware classical metric or VLM scores → L2 field; Phase 2: CLAHE clip limit / brightness adjustment factor recorded at generation time |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.contrast_score` (float 0-1; Phase 1) / CLAHE or brightness adjustment factor augmentation parameter (Phase 2)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better) for Phase 1 classical or VLM labels

**Label Provenance**: Phase 1: tier_1_classical (edge-aware contrast metric) or tier_1_annotation (VLM, contingent on SRCC > 0.60 gate); Phase 2: tier_0_exact (augmentation parameter is ground truth)

**Semantic Definition (CRITICAL — must be resolved before labeling begins)**: Multi-model consensus is unanimous: `contrast_score` MUST be defined as **text-background separation** (local text-foreground vs. paper-background contrast), NOT global histogram spread. Global histogram spread produces misleading labels for documents on colored paper, documents with large dark regions, and documents with mixed content. The OCR and document intelligence use case requires legibility-affecting contrast. The `iqa_classical.py` histogram contrast detector measures global spread and will need to be replaced or supplemented with an edge-aware local contrast metric (e.g., Michelson contrast at Canny edge locations, or sliding-window min/max on text regions) before Phase 1 labeling can achieve SRCC ≥ 0.65.

**Binarized Document Convention**: 1-bit binarized images have technically maximum binary contrast. Convention: label as `contrast_score = 1.0` (maximum), relying on other heads (noise_score, compression_score) to capture any binarization quality issues. This anchors the upper regression bound and avoids conflicting gradients during training.

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,499 labeled | ❌ NOT populated | 0% | N/A | Pending labeling | Pending — needs edge-aware classical labeling |
| OHR-Bench | ~8,500 | ❌ NOT populated | 0% | N/A | Pending labeling | Pending — needs edge-aware classical labeling |
| RealDAE | ~1,200 | ❌ NOT populated | 0% | N/A | Pending labeling | Pending |
| **Phase 1 total** | **~15,200** | — | **0%** | — | — | **0 usable today** |

**Note on Phase 1 feasibility**: DIQA-5000 has 5,499 images processed with resolution quality labels already (PaddleOCR pipeline). The same text-region detection output can feed an edge-aware contrast metric at low marginal cost. OHR-Bench and RealDAE require a separate labeling pass.

### Phase 2 — Synthetic Pipeline (Self-Labeling)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are generated from augmentation parameters at creation time. The contrast_factor parameter (CLAHE clip limit or linear brightness/gamma adjustment) applied during derivation from synth-multiscript-v3 is the ground-truth label.

- **Base dataset**: synth-multiscript-v3 (350K images on GCS `gs://image_detection_b/synth_multiscript_v3/`); color mode: 60% color / 30% grayscale / 10% binarized; document age: 80% modern / 15% aged / 5% historical
- **Target**: 100,000 derived images from synth-multiscript-v3 subset
- **Label provenance**: tier_0_exact (contrast augmentation parameter recorded at generation time)
- **Normalization**: `contrast_score = clamp(1.0 - contrast_reduction_factor, 0, 1)` where contrast_reduction_factor=0 → pristine (score=1.0), contrast_reduction_factor=1 → fully washed out (score=0.0)
- **Required augmentations**: (1) global CLAHE/gamma modulation for washed-out / over-bright conditions; (2) spatial illumination gradient simulation (needed for gutter shadow and uneven camera lighting cases — confirmed by both consensus models); (3) ink fade + paper yellowing composite for aged document contrast simulation; (4) colorful background overlay for text-background separation stress
- **Pipeline status**: NOT YET CREATED. `prepare_multitask_datasets.py iqa` sub-command not yet implemented

### Usable Pool Summary

- **Phase 1 usable**: 0 images (field unpopulated; semantic definition under-specified for classical labeling)
- **Phase 1 target**: ~15,200 images (trains `overall_quality` head SIG-G1-6; contrast labels derived from same images)
- **Phase 2 usable**: 0 (pipeline not yet created)
- **Phase 2 target**: 100,000 images (primary label source for SIG-G1-3)
- **Combined gap**: 100,000 Phase 2 images + Phase 1 labeling pass required

### VLM Validation Sampling Tier

- Phase 1 DIQA-5000: Tier 1 (max(10, 3%) per quality bucket) — VLM pilot ran 200 images for overall_quality (SRCC 0.39 overall, 0.53 non-rotated); contrast-specific SRCC not yet measured. NOTE: VLM pilot result (SRCC 0.39) is below the 0.60 gate required for VLM-based labeling. Classical edge-aware metric is recommended as primary Phase 1 label source.
- Phase 1 OHR-Bench: Tier 2 (max(15, 10%)) — labeling not yet started
- Phase 2: No VLM sampling needed (augmentation parameters are ground truth)

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| IQA-CONTRAST-DEF-01 | All Phase 1 datasets | `ml_image_quality.contrast_score` | Field not populated in L2 metadata for any dataset | Open — remediation: run edge-aware classical labeling pipeline on DIQA-5000, OHR-Bench, RealDAE |
| IQA-CONTRAST-DEF-02 | Phase 2 pipeline | N/A | IQA synthetic derivation pipeline (`prepare_multitask_datasets.py iqa`) not yet implemented | Open — remediation: implement sub-command; record contrast_factor at generation time |
| IQA-CONTRAST-DEF-03 | iqa_classical.py | `contrast_score` measurement | Current classical detector uses global histogram spread which is insufficient for text-background separation (confirmed by 2-model consensus) | Open — remediation: implement edge-aware local contrast metric (Michelson at Canny edges) |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) — rotation construct mismatch affects all G1 VLM labels | HIGH — contrast-specific VLM SRCC not yet measured; classical metric preferred for Phase 1 if edge-aware implementation is completed |
| IQA-KI-CONTRAST-01 | Semantic definition ambiguity: global histogram spread vs. text-background separation produce different label values for the same image (e.g., dark paper + dark text = narrow histogram but low separation) | CRITICAL P0 — must resolve before ANY labeling begins; consensus unanimous: use text-background separation |
| IQA-KI-CONTRAST-02 | Watermarked documents (OOD-4b) cause contrast ambiguity — watermark reduces effective text contrast even when global histogram appears normal | MEDIUM — contrast_score and watermark_severity must be independently labeled; watermark does not invalidate contrast_score measurement |
| IQA-KI-CONTRAST-03 | Phase 2 CLAHE/brightness augmentations are global operations; gutter shadow and illumination gradient conditions require spatial (local) contrast degradation simulation | HIGH — without spatial degradation in Phase 2, the model will fail on non-uniform contrast conditions (confirmed by both consensus models) |

### Remediation Path

1. **Resolve semantic definition** (0.5 day): Document `contrast_score = text-background separation` in L2 schema spec and training data design doc. Update VLM prompt to explicitly score legibility-affecting contrast (not global histogram)
2. **Implement edge-aware classical labeling** (3 days): Build `label_contrast_classical.py` using Michelson contrast at Canny edge locations or local sliding-window min/max on text regions. Apply to DIQA-5000 first; validate SRCC against any available human annotations or resolution quality labels as proxy
3. **Implement Phase 2 derivation pipeline** (3-5 days): Add `iqa` sub-command to `prepare_multitask_datasets.py`; include CLAHE, gamma, spatial gradient, ink fade, and colored-background augmentations; record all parameters per image
4. **Apply Phase 1 labeling** (2 days after script): Run on DIQA-5000 (5.5K), OHR-Bench (8.5K), RealDAE (1.2K); integrate into L2 metadata via `integrate_contrast_quality.py`

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: ❌ Phase 1 not started (0/15,200 labeled); Phase 2 not started (0/100,000)

**Target Count**: 15,200 (Phase 1) + 100,000 (Phase 2 synthetic) = 115,200 total

**Current Count**: 0 labeled images for contrast_score specifically

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 1 total images | ~15,200 | 0 labeled | ❌ Labeling pipeline not run |
| Phase 2 total images | 100,000 | 0 | ❌ Pipeline not created |
| Phase 1 label tier | ≥80% tier_1_classical (edge-aware) | 0 | ❌ Script not built |
| Phase 2 label source | Augmentation params (contrast factor) | N/A | ❌ Pipeline not built |
| Semantic definition | Documented + validated | Not documented | ❌ P0 blocker |
| SRCC validation | SRCC ≥ 0.65 vs. human MOS | Not measured | ❌ Cannot measure until Phase 1 labeled |

**Blockers**:

- Semantic definition must be documented and agreed before labeling begins (P0)
- Edge-aware classical labeling script not yet built (P0 — needed for Phase 1)
- Phase 2 synthetic pipeline not yet created (P0)
- iqa_classical.py global histogram metric unsuitable for chosen definition (P1 — replace with local metric)

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` — not yet implemented

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 0.0/100 (DDR automated score — reflects that the iqa datasets have 0 samples loaded into DDR tool, not actual poor diversity; the base synth-multiscript-v3 dataset that will generate Phase 2 labels has known distribution)

**Note**: The DDR automated score of 0.0/100 is entirely a consequence of 0 samples being loaded into the DDR tool for iqa-curated and iqa-synthetic (datasets not yet assembled). The underlying source pool and Phase 2 base (synth-multiscript-v3) have well-characterized diversity. The analyst scores below are based on source composition and planned derivation pipeline, not DDR tool measurements.

**Analyst consensus (Gemini 2.5 Pro: 60/100; Gemini 3 Pro Preview: 70-85/100; analyst estimate: 60/100)** reflecting strong latent diversity in synth-multiscript-v3 base, not yet realized in assembled dataset.

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| color_mode | `image_properties.color_mode` | CRITICAL — binarized docs have maximum binary contrast and require a fixed label convention (1.0); grayscale and color docs exhibit full contrast variation range. Color mode fundamentally changes the histogram shape used in any contrast measurement. | ≥10% binarized, ≥30% grayscale | Phase 2 base (synth-multiscript-v3): 60% color / 30% grayscale / 10% binarized — strong distribution. Phase 1: unmeasured. | ✅ 75/100 for Phase 2 (base distribution confirmed); ⚠️ 0 for Phase 1 (unmeasured) |
| document_age | `image_properties.document_age` | CRITICAL — historical/aged documents exhibit faded ink (reduced text-foreground density) and yellowed paper (elevated background brightness), reducing text-background separation. The primary real-world source of progressive contrast degradation. | ≥15% aged + historical | Phase 2 base: 80% modern / 15% aged / 5% historical — good distribution. Phase 1: DIQA-5000 has minimal aged content. | ✅ 70/100 for Phase 2; ⚠️ 30/100 for Phase 1 |
| capture_method | `capture_method.method` | HIGH — born-digital has perfect, printer-set contrast; flatbed scanner can introduce gamma bias and platen reflections; camera capture adds illumination gradients and uneven exposure. These three categories produce systematically different contrast distributions. | ≥3 capture methods, ≥20% camera | Phase 1: DIQA-5000 mix of camera+scanner+born-digital (proportions unmeasured). Phase 2: synth-multiscript-v3 is synthetic/born-digital; camera capture underrepresented. | ⚠️ 50/100 — camera underrepresented in Phase 2; Phase 1 unmeasured |
| degradation | `quality.degradations` | HIGH — contrast reduction is the primary degradation dimension for this head. Must include: washed-out overexposed, underexposed dark, ink fading, colorful background. Phase 2 augmentations directly model these. | ≥4 contrast severity levels across [0.0, 1.0] range | Phase 2: CLAHE + gamma + spatial gradient planned but not yet implemented. Phase 1: DIQA-5000 has real degradation of unknown distribution. | ⚠️ 40/100 — levels confirmed in plan but spatial degradation not yet implemented |
| domain | `domain.level1` | MEDIUM — financial/technical/legal docs tend to dense small text with high contrast requirements. Handwritten docs, receipts, and aged government forms tend lower contrast. Domain breadth ensures contrast scoring generalizes across use cases. | ≥5 domains | Phase 1 base: DIQA-5000 + OHR-Bench cover FIN, SCI, forms, natural images. Phase 2 base (synth-multiscript-v3): diverse layouts and domains. | ✅ 65/100 — domain breadth adequate from source composition |
| script_code | `language.script_code` | MEDIUM — CJK stroke-density differs from Latin; Arabic script has different stroke-width patterns; both affect local contrast measurement. Edge-aware contrast metrics may behave differently across scripts. | ≥3 script families | Phase 2 base: synth-multiscript-v3 covers 27 scripts (198 languages) — excellent script diversity. Phase 1: DIQA-5000 primarily Latin-script images. | ✅ 80/100 for Phase 2; ⚠️ 30/100 for Phase 1 |
| resolution | `resolution.category` | MEDIUM — low-DPI images have thicker, softer strokes with lower apparent contrast from anti-aliasing. 72 DPI documents appear lower-contrast than 300 DPI versions of the same document even when text-background separation is identical. Resolution affects the local-edge-based metric quality. | ≥3 DPI tiers | Phase 2 base: synth-multiscript-v3 generated at 7 DPI tiers (72/100/150/200/300/400/600). Phase 1: DIQA-5000/OHR-Bench scanned at 300 DPI primarily. | ✅ 70/100 for Phase 2 — strong DPI diversity from synth-multiscript-v3 |
| layout_type | `structure.layout_type` | LOW-MEDIUM — multi-column documents have interspersed white space that affects global histogram; single-column dense text has different local contrast texture. Minor effect on text-background separation specifically. | ≥3 layout types | Phase 2 base: synth-multiscript-v3 includes varied layout types. Phase 1: DIQA-5000/OHR-Bench include mixed layouts. | ✅ 60/100 — adequately diverse through source composition |

**Analyst note on 14-Dim overall**: The planned Phase 2 dataset (100K derived from synth-multiscript-v3) will have strong diversity across color_mode, document_age, script_code, and resolution by inheritance from the base dataset design. The primary gap is (1) Phase 1 dimensions entirely unmeasured and (2) camera-capture contrast patterns absent from Phase 2. The aggregate analyst score is 60/100, reflecting high potential not yet realized.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 8.3/100 (DDR automated score for iqa-curated — reflects 0 samples loaded, not actual coverage; 1 partial condition from DDR on mobile blur which partially overlaps with contrast)

**Analyst Score (based on planned coverage and gap analysis)**: 45/100

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Aged/historical document yellowing (low contrast from organic degradation) | `image_properties.document_age = aged / historical` | ⚠️ Partial | Phase 2 base has 20% aged/historical, but contrast degradation (ink fading + paper yellowing composite) must be EXPLICITLY simulated in the augmentation pipeline — synth-multiscript-v3 base images are clean; degradation applied at derivation time. DIQA-5000/OHR-Bench Phase 1 pool includes some aged documents but proportion unknown and unlabeled. |
| Scanner platen contamination / brightness inhomogeneity | `capture_method = scanner_flatbed` + spatial brightness variation | ❌ Missing | Not explicitly modeled in Phase 2 augmentations. Platen contamination creates bright spots and uneven gamma that reduce apparent contrast in affected regions. Partially covered by Phase 1 real scans if any contaminated documents present. |
| Fluorescent / colored paper background (text-background separation degraded by non-white substrate) | `image_properties.colorful_background = true` | ⚠️ Partial | Phase 2 can explicitly model this via background color overlay augmentation (confirmed needed by both consensus models). Not yet in augmentation specification. Phase 1 real pool may contain some colored-background docs. |
| Heavy watermark overlay (reduces effective text contrast without changing global histogram) | `physical_degradation.watermark_severity` | ⚠️ Partial | OOD-4b watermarked documents directly test this. Training data may lack watermarked examples for Phase 2 (watermark augmentation not in current plan). Must be added to Phase 2 augmentation stack. |
| Illumination gradient from camera capture (one side bright, other dark — spatially non-uniform contrast) | `capture_method = camera_smartphone / camera_professional` | ⚠️ Partial | Phase 1 real pool (DIQA-5000/OHR-Bench) likely contains some camera captures with illumination gradients. Phase 2 requires EXPLICIT spatial gradient simulation (confirmed P1 gap by both consensus models — pure CLAHE insufficient). |
| Binarized document (contrast artificially maximized — maximum separation, but binarization artifacts may reduce legibility) | `image_properties.color_mode = binarized` | ⚠️ Partial | OOD-4d binarized documents test this. Phase 2 base has 10% binarized; label convention must apply `contrast_score = 1.0` for cleanly binarized documents. Binarization-with-erosion (artifact) case needs explicit handling. |
| Overexposed document (washed-out, global histogram clipped at high end) | `quality.degradations (contrast subtype: overexposed)` | ⚠️ Partial | CLAHE augmentation in Phase 2 can simulate this. DIQA-5000 likely contains overexposed documents. Needs explicit label in L2. |
| Multiply-distorted (≥5 simultaneous types including contrast reduction) | OOD-4a (500 images) | ❌ Missing from training | OOD-4a explicitly evaluates this. Training data does not include ≥5 simultaneous distortion types with contrast as one component. Model must generalize to this from single-distortion training. |
| Screen recapture (RGB aliasing / moiré — reduces apparent contrast in affected regions) | `capture_method = screen_recapture` (indirect) | ❌ Missing | Moiré patterns reduce local contrast in the frequency domain. Not present in Phase 1 or Phase 2 planned augmentations. Partially covered by OOD-Capture category. |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types) | 500 | ✅ Direct | Contrast reduction combined with blur, noise, and JPEG in compound stacks — contrast_score must be evaluated amid compound degradation where the IQA detectors interact. Primary stress test for training/OOD distribution shift. |
| 4b. Watermarked documents | 100 | ✅ Direct | Watermarks directly reduce effective text-background contrast by partially obscuring text strokes. Primary test of whether contrast_score correctly penalizes watermark-induced contrast reduction. |
| 4c. Book gutter shadow | 100 | ✅ Direct | Hard shadow gradient creates spatially non-uniform contrast — bright half vs. dark half of the same page. Tests the model's spatial contrast estimation vs. a global metric. This sub-source specifically probes the gap between global and local contrast definitions. |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | Binarized docs have maximum binary contrast (label should be 1.0). Tests whether the model can correctly identify high contrast in 1-bit images and whether the label convention is consistent. |
| OOD-Mixed cascade | 500 | ⚠️ Indirect | Includes "binarized + extreme compression" (75 images) and "CJK HW + gutter shadow" (100 images) — both involve contrast-affecting conditions in cascade scenarios. |

**OOD Acquisition Status**: ⏳ Not started (Phase 4 — all 4,700 OOD images pending acquisition). Both consensus models rated the OOD design highly (Gemini 2.5 Pro: 90/100; Gemini 3 Pro Preview: 85-90/100).

**Missing OOD Sub-sources**:

- Compound distortion labeling for contrast_score in OOD-4a requires human annotation (classical histogram contrast detector insufficient for compound distortion; edge-aware metric may also struggle with ≥5 simultaneous distortions)
- Spatial contrast gradient sub-source for camera illumination gradient (not a separate sub-source; covered by gutter shadow in 4c and illumination by multiply-distorted in 4a)

**OOD Leakage Risk**: DIQA-5000 is in training. OOD-Degradation must use non-DIQA-5000 sources only. OHR-Bench test split must be withheld from Phase 1 training. SHA256 + pHash (Hamming ≤ 5) dedup required before OOD acquisition is registered.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench + RealDAE (~15,200 images); Phase 2: 100K derived from synth-multiscript-v3

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independent per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| All other G1 heads (G1-1, G1-2, G1-4, G1-5, G1-6) | DIQA-5000 + OHR-Bench | Multi-label independence required; labels must not be derived from each other | ✅ Each head's label is independently computed from edge-aware classical metric / augmentation params / MOS |
| SIG-G1-2 (noise_score) | Same dataset | Low contrast + high noise interact; risk of label correlation in degraded images (a noisy document appears low-contrast and vice versa) | ⚠️ Edge-aware contrast metric must be measured independently of noise; VLM prompts must score contrast and noise in separate scoring passes |
| SIG-G5-2 (shadow_reg) | Different datasets; OOD-4c overlap | Book gutter shadow (OOD-4c) tests both contrast_score and shadow_reg; shadow reduces local contrast. Risk of label cross-contamination if shadow and contrast labels are not independently generated | ✅ Different L2 fields (`ml_image_quality.contrast_score` vs. `physical_degradation.shadow_severity`); measured independently; shadow presence does not force contrast to be low (a well-lit shadow may have adequate local contrast) |
| SIG-G1-6 (overall_quality) | Same dataset | overall_quality may use weighted average of other G1 scores including contrast_score as a cross-check; risk of circular dependency if G1-6 labels derived from G1-3 labels | ⚠️ Phase 1 overall_quality from human MOS (independent ground truth); Phase 2 overall_quality from combined degradation params; ensure contrast_score is not a derived input to overall_quality label |
| SIG-G1-4 (skew_score) | Same dataset | skew_score measures geometric distortion severity (not contrast); no direct label interaction | ✅ Different constructs; no label interaction risk |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits well-defined. MEDIUM (Phase 2) — synthetic images must be SHA256-deduped against all other training sets via the global split registry. synth-multiscript-v3 uses SHA256-keyed JSONL split registry to prevent cross-dataset leakage.

**Label Convention**: All G1 scores are 0-1 floats where 1.0 = perfect quality (optimal contrast) and 0.0 = severe degradation (complete contrast loss / fully washed out). Binarized documents: `contrast_score = 1.0` by convention (maximum binary separation). Documents with colored text on colored background where text-background separation is poor should score low (0.1-0.3), even if global histogram appears bimodal.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| IQA-CONTRAST-G01 | IQA-KI-CONTRAST-01 | **Semantic definition not documented.** `contrast_score` is ambiguous between global histogram spread and text-background separation. No labeling (Phase 1 classical, Phase 1 VLM, or Phase 2 augmentation design) can be finalized without a documented, agreed definition. Multi-model consensus is unanimous: use text-background separation. | No formal definition exists in L2 schema spec or training data design doc | Document `contrast_score = text-background separation (local Michelson contrast at text edge locations)` in L2 schema annotation guide and training data design. Propagate to VLM prompt v2.0 and Phase 2 augmentation spec. | Low — 0.5 day (decision + documentation) |
| IQA-CONTRAST-G02 | IQA-CONTRAST-DEF-03 | **`iqa_classical.py` contrast detector measures global histogram spread, which is insufficient for the text-background separation definition.** Global histogram spread fails on dark-paper documents, mixed-content pages, and watermarked documents. SRCC ≥ 0.65 against human MOS will not be achievable with a global metric on challenging documents. | Classical detector was built for Phase 1C using the original (now superseded) global contrast definition | Implement `label_contrast_classical.py` using edge-aware local contrast: (1) run Canny edge detection on the page image to locate text boundary pixels, (2) measure Michelson contrast `(L_max - L_min) / (L_max + L_min)` in local patches centered on detected edges, (3) compute weighted average as the `contrast_score` for the page. Validate SRCC against DIQA-5000 subset where any human MOS or VLM labels exist. | Medium — 3 days (implementation + validation) |
| IQA-CONTRAST-G03 | IQA-CONTRAST-DEF-02 | **Phase 2 Augraphy/augmentation pipeline not yet created.** The 100K synthetic images that provide the primary tier_0_exact training signal for SIG-G1-3 (and SIG-G1-1, G1-2, G1-4, G1-5) do not yet exist. GCS base (synth-multiscript-v3, 350K images) is available and ready. | `prepare_multitask_datasets.py iqa` sub-command not implemented | Implement `iqa` sub-command: (a) select 100K subset from synth-multiscript-v3 GCS, (b) apply contrast augmentations (CLAHE clip limit variation, gamma adjustment, spatial illumination gradient), (c) record contrast_factor per image in manifest, (d) normalize to [0,1] `contrast_score`. Include spatial gradient simulation (not just global CLAHE) per consensus recommendation. | Medium — 3-5 days (script implementation + GCS derivation run) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| IQA-CONTRAST-G04 | **Phase 2 augmentations limited to global CLAHE/gamma — spatial contrast degradation not modeled.** Book gutter shadow (OOD-4c), camera illumination gradients, and uneven scanner gamma are spatially non-uniform. A model trained only on globally degraded synthetic images will fail on these conditions. Both consensus models confirmed this gap (Gemini 2.5 Pro: "planned augmentations are too generic"; Gemini 3 Pro Preview: "must include spatial/local contrast degradation"). | Phase 2 plan specifies CLAHE and brightness adjustment only, which are global operations | Extend Phase 2 augmentation stack to include: (1) linear illumination gradient overlays (simulate camera capture angle), (2) radial vignetting (simulate lens falloff), (3) localized shadow patches (using Augraphy shadow pipeline parameters). Record spatial contrast variation in metadata. | Medium — 2 days (augmentation script extension) |
| IQA-CONTRAST-G05 | **Phase 1 `ml_image_quality.contrast_score` field unpopulated for all three source datasets.** DIQA-5000, OHR-Bench, and RealDAE have 0 contrast labels. Phase 1 provides the real-document anchor for the training distribution. Without Phase 1 labels, the model is trained entirely on synthetic data, risking domain gap. | Edge-aware classical labeling script not yet built | Run `label_contrast_classical.py` (after IQA-CONTRAST-G02) on DIQA-5000 (5.5K), OHR-Bench (8.5K), RealDAE (1.2K). Integrate into L2 via `integrate_contrast_quality.py`. | Medium — 2 days after G02 script complete |
| IQA-CONTRAST-G06 | **Contrast-specific VLM SRCC not measured independently.** VLM pilot measured overall_quality SRCC (0.39 overall, 0.53 non-rotated). Contrast-specific SRCC may differ. If contrast-specific VLM SRCC exceeds 0.60 with a revised prompt (v2.0), VLM labels could supplement classical labels for challenging cases. | VLM pilot focused on overall_quality; contrast not measured separately | Run targeted VLM validation on 100-200 images using contrast-specific prompt. Measure SRCC against any available ground truth (e.g., correlate with edge-aware classical scores on DIQA-5000 subset). Use as VLM label quality gate. | Low — 1 day (in-session VLM run) |
| IQA-CONTRAST-G07 | **Binarized document label convention not yet documented or enforced in training pipeline.** Without a formal convention (contrast_score = 1.0 for clean binarized), training will encounter conflicting gradients — binarized images have technically maximum contrast but may be scored inconsistently by human annotators if asked about "quality." | Convention was noted as undefined in scaffold; not resolved before review | Document convention: `contrast_score = 1.0` for `color_mode = binarized` if binarization appears clean; `contrast_score = 0.3-0.5` if binarization artifacts (over-eroded text, broken characters) are visible. Add conditional label assignment in assembly script. | Low — 0.5 day (convention + code) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| IQA-CONTRAST-G08 | **Contrast subtype labels (overexposed/underexposed/ink-faded/background-colored/spatial-gradient) not captured.** A scalar `contrast_score` cannot distinguish between a uniformly washed-out image (global defect) and a locally shadowed image (spatial defect). Subtype information would enable more targeted correction. | Add `contrast_degradation_type` enum field to Phase 2 generation metadata; record which augmentation type was applied. Use during OOD analysis to understand where the model fails by subtype. |
| IQA-CONTRAST-G09 | **Spatial non-uniformity of contrast not captured by global score.** A book gutter shadow creates high contrast on the illuminated side and low contrast on the shadowed side; the global score is the average, losing spatial information. | Note this limitation in model card; consider adding a `contrast_uniformity_score` companion field in future iterations. For now, the global score is the production contract. |
| IQA-CONTRAST-G10 | **Colorful background documents underrepresented in Phase 1.** DIQA-5000 and OHR-Bench may contain few examples of documents with colored paper substrates (purple, green, yellow), which are common in forms and marketing materials and significantly reduce text-background separation. | Ensure Phase 2 colorful-background overlay augmentation generates sufficient examples (≥10% of Phase 2 images). Verify with `image_properties.colorful_background` L2 field distribution in assembled manifest. |

---

## Section 9 — Multi-Model Consensus

**Status**: ✅ Complete (2026-02-23)

**Adequacy Rating (pre-consensus)**: ⚠️ Needs Work

**Analyst Summary**: SIG-G1-3 (contrast_score) is a P0 head that faces two structural problems before training can proceed: (1) a semantic definition ambiguity that must be resolved before any labeling is valid, and (2) zero labeled data in both Phase 1 and Phase 2 pipelines. The good news is that the underlying data infrastructure is sound — synth-multiscript-v3 (350K images, known distributions) provides an excellent base for 100K Phase 2 derivations, and the DIQA-5000/OHR-Bench real image pool provides solid Phase 1 coverage once the edge-aware labeling pipeline is built. The OOD design (800 images across 4 directly relevant sub-sources) is well-specified. The technical path is clear and all blockers are tractable (5-10 engineer-days total). The head is not "Blocked" in the sense that no path forward exists; it is "Needs Work" with clearly defined remediation steps. The critical insight from consensus: CLAHE-only augmentation in Phase 2 will fail to teach spatial contrast estimation — the augmentation stack must include illumination gradients, shadow simulation, and ink-fade composites.

**Consensus Prompt**: "Evaluate the training dataset design for the SigLIP 2 NAFlex `contrast_score` head (SIG-G1-3). P0 regression head, SRCC ≥ 0.65 target. Dual-path strategy: Phase 1 16K real documents (DIQA-5000, OHR-Bench, RealDAE) — field unpopulated; Phase 2 100K synthetic from synth-multiscript-v3 — pipeline not created. Key ambiguity: contrast_score can mean (a) global histogram spread or (b) text-background separation. Classical iqa_classical.py uses global histogram. VLM pilot SRCC = 0.39 (below 0.60 gate). OOD: 800 images (4a-4d sub-sources), not yet acquired. Questions: (1) definition choice, (2) Phase 1 classical sufficiency, (3) Phase 2 synthetic viability, (4) OOD adequacy, (5) overall rating."

**Models consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

---

### Consensus Summary

**Unanimous rating: NEEDS WORK** (both models, confidence 8-9/10).

**Q1 — Should contrast_score be global histogram or text-background separation?**

Both models agree unanimously: **text-background separation is the only viable definition for a document intelligence model**. Global histogram spread fails on common document scenarios: dark paper with white text appears as a narrow histogram (low global contrast) but has high text-background separation; mixed-content pages (image + text) have complex histograms that misrepresent text legibility; documents on colored paper substrates (yellow, green, purple forms) may have adequate text-background separation but abnormal global histograms. Gemini 2.5 Pro cites ISO document print quality standards (ink density vs. substrate density). Gemini 3 Pro Preview notes that industry-standard local contrast metrics (Weber, Michelson) are defined at text edge locations. Both recommend implementing an edge-aware metric (Michelson or Weber contrast at Canny edge locations) for Phase 1 classical labeling.

**Q2 — Is classical histogram contrast sufficient for Phase 1 labels?**

Both models: **No, insufficient for the text-background separation definition.** Global standard deviation or histogram spread (what iqa_classical.py currently implements) cannot achieve SRCC ≥ 0.65 for legibility-affecting contrast assessment on complex documents. An edge-aware local contrast metric is required. Gemini 3 Pro Preview: "If the classical metric is global standard deviation, it is insufficient — replace with local_contrast_metric before populating Phase 1." VLM labeling (SRCC 0.39) is also below the 0.60 gate, though contrast-specific SRCC has not yet been measured independently (the overall_quality pilot result may not reflect contrast-specific performance).

**Q3 — Is Phase 2 synthetic augmentation sufficient as primary label source?**

Both models: **Yes, if augmentation stack is enhanced with spatial/local contrast degradation.** Phase 2 tier_0_exact labels (augmentation parameters as ground truth) are the strongest available signal. The synth-multiscript-v3 base has excellent diversity (color modes, document age, scripts, DPI tiers). However, pure CLAHE and global brightness adjustment will fail to teach the model to handle spatially non-uniform contrast (gutter shadows, illumination gradients, localized watermarks). Both models recommend adding spatial gradient augmentation, shadow simulation, and ink-fade composites to the Phase 2 stack. With these additions, 100K Phase 2 images are sufficient as the primary training signal.

**Q4 — Is the OOD-Degradation design adequate?**

Both models rate the OOD design highly (Gemini 2.5 Pro: 90/100; Gemini 3 Pro Preview: 85-90/100). The four sub-sources (4a multiply-distorted 500, 4b watermarked 100, 4c book gutter shadow 100, 4d binarized 100) directly target the most challenging contrast scenarios. Gemini 3 Pro Preview notes that 800 images is statistically thin for regression evaluation (recommends ~2,000 for robust SRCC calculation) but this is a P2 recommendation, not a blocker. The OOD acquisition must be prioritized once label definition is finalized.

**Q5 — Most critical gaps:**

Both models identify the same primary gap: **semantic definition ambiguity is the P0 blocker** — without resolving whether to use global or local contrast, all labeling produces inconsistent data. Secondary gaps (equal priority, both P0): Phase 2 pipeline not created; Phase 1 edge-aware classical metric not implemented. Gemini 3 Pro Preview adds: "Spatial/local contrast degradation in Phase 2 augmentations is critical — simple global CLAHE will fail on gutter shadows and illumination gradients."

**Final Rating**: ⚠️ NEEDS WORK

**Top Recommendations** (priority order):

1. Document `contrast_score = text-background separation` as the formal definition — mandatory before any labeling or augmentation design is finalized (0.5 day)
2. Implement `label_contrast_classical.py` using edge-aware Michelson contrast at Canny edge locations — replace global histogram metric for Phase 1 labeling (3 days)
3. Build Phase 2 IQA derivation pipeline with spatial contrast augmentation (gradient overlays, shadow simulation, ink-fade composites in addition to CLAHE) — mandatory for primary training signal (3-5 days)
4. Apply Phase 1 labeling to DIQA-5000, OHR-Bench, RealDAE; integrate into L2 metadata (2 days, after step 2)
5. Establish binarized document label convention (contrast_score = 1.0) and enforce in assembly script (0.5 day)

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 25 | 8.75 |
| 14-Dimension Coverage | 25% | 60 | 15.00 |
| Wild Condition Coverage | 20% | 45 | 9.00 |
| OOD Design Quality | 20% | 80 | 16.00 |
| **Overall** | 100% | — | **48.75** |

**Grade**: ⚠️ Needs Work (49/100)

**Score rationale**:

- Source Pool Adequacy (25): Both Phase 1 and Phase 2 have zero labeled data today. Score is not zero because the raw source images exist (DIQA-5000 5.5K processed, OHR-Bench 8.5K available, synth-multiscript-v3 350K on GCS), the technical path is clear, and Phase 2 uses tier_0_exact augmentation labels (highest confidence). Score capped by zero current coverage and the semantic definition blocker.
- 14-Dimension Coverage (60): synth-multiscript-v3 base has strong latent diversity (color mode, document age, script, DPI) that will flow into Phase 2. Analyst score reflects high potential, not yet realized. Score capped by camera-capture underrepresentation in Phase 2 and completely unmeasured Phase 1 dimensions.
- Wild Condition Coverage (45): Eight wild conditions identified; most are "partial" — identifiable in sources but not yet in assembled training data. Score reflects that the key conditions (aged documents, gutter shadow, colored background) are either in source pool (Phase 1 real docs) or plannable in Phase 2 augmentations, but spatial gradient simulation is confirmed missing from current augmentation specification.
- OOD Design Quality (80): The OOD-Degradation category design is well-specified with four directly relevant sub-sources. Score docked 20 points for (1) zero acquisition progress and (2) OOD labeling for contrast_score in compound distortion scenarios (4a) requiring human annotation, which introduces execution risk.
