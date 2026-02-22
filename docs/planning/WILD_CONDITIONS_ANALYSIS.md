# Wild Conditions Analysis — Per Model Head

> **Status**: ✅ Active | Research Artifact
> **Version**: 2.0.0
> **Created**: 2026-02-21
> **Updated**: 2026-02-22
> **Purpose**: Catalog all real-world scanning conditions that impact each model head,
> identifying training coverage gaps, metric thresholds, correction boundaries,
> and conditions that are impractical to address through preprocessing.

## Context

The SigLIP 2 + MobileNetV4 two-model pipeline contains 19 output heads across 5 SigLIP 2 groups
and 3 MobileNetV4 heads. This document enumerates real-world conditions ("wild conditions") that
each head must handle, along with current training coverage and gap severity.

**Research Basis**: This analysis is grounded in three research documents:

- `tmp_cleanup/ocr_preprocessing_research/ocr_research_1.md` — Root-cause taxonomy and prioritization framework (9 categories)
- `tmp_cleanup/ocr_preprocessing_research/ocr_research_2.md` — Deterministic preprocessing diagnostics and decision logic
- `tmp_cleanup/ocr_preprocessing_research/ocr_research_3.md` — Quantitative evaluation logic and calibration

**Coverage Key:**

- ✅ Covered: >5% of relevant training samples demonstrate this condition
- ⚠️ Partial: <5% coverage, or indirect/proxy coverage
- ❌ Missing: 0 examples of this condition in training data

**Gap Severity:**

- Critical: Expected metric drop >10% on real-world data; blocks production deployment
- High: Expected metric drop 5-10%; significant reliability risk
- Med: Expected metric drop 2-5%; tolerable but should remediate
- Low: Minor or edge-case impact; monitor but may not need immediate action

---

## Degradation Classification Framework

Research consistently identifies three distinct categories of OCR degradation. Project A's
preprocessing system targets only the first category. The other two require model-level or
engineering-level solutions.

### Category 1: Deterministic Degradations (Project A Scope)

These are physically caused, directly measurable, and correctable through signal processing.
Project A detects, quantifies, and corrects these before handoff to Project B.

| Degradation | Detect Method | Correct Method | Implementation |
| --- | --- | --- | --- |
| Coarse orientation | MobileNetV4 4-class | Rotation | `correction/corrections.py` |
| Fine skew | Hough transform + MobileNetV4 | Affine rotation (bicubic) | `correction/corrections.py` |
| Perspective distortion | Edge analysis / MobileNetV4 | 4-point projective transform | `correction/perspective_correction.py` |
| Low resolution | Character-height measurement | OpenCV upscaling (5 algorithms) | `ingestion/pdf_upscaler.py` |
| Non-uniform illumination | Gradient magnitude analysis | Background estimation + CLAHE | `correction/corrections.py` |
| Gaussian blur | Laplacian variance | Mild unsharp masking (or flag for reject) | `detection/iqa_classical.py` |
| Salt-and-pepper noise | Extreme pixel count | Median filter (3x3) | `detection/iqa_classical.py` |
| Low contrast | Histogram spread | CLAHE (luminance channel only) | `correction/corrections.py` |
| Shadow gradient | Shadow severity regression | Correction escalation routing | `detection/shadow_detector.py` |
| Page warping | Warp severity regression | Correction escalation routing | `detection/warping_detector.py` |
| Scanner border artifacts | Edge detection | Border removal | `correction/border_removal.py` |
| JPEG blocking artifacts | DCT coefficient analysis | Deblocking (conditional) | `detection/iqa_classical.py` |

### Category 2: Statistical / Model-Level Degradations (Monitoring Scope)

These arise from the relationship between model training distribution and production data.
Preprocessing cannot resolve these — they require model-level intervention or routing.
Project A's monitoring layer (`drift/`) detects these conditions and escalates.

| Condition | Detection Signal | Response |
| --- | --- | --- |
| Unseen script / font family | Script class confidence drop | Route to specialized OCR engine |
| Historical typography | Low script detection confidence | Human-in-the-loop queue |
| Domain distribution shift | PSI > 0.2 across any IQA head | Trigger active learning / retraining |
| OCR confidence calibration drift | ECE (Expected Calibration Error) increase | Trigger model recalibration |
| Language model mismatch | Dictionary hit rate collapse | Route to language-appropriate engine |

**Monitoring thresholds (research-validated):**

- PSI > 0.20: significant drift; trigger investigation
- PSI > 0.25: critical drift; trigger emergency response
- KS-test p-value < 0.05: statistically significant distribution shift
- ECE > 0.10: confidence calibration requires attention

### Category 3: Systemic / Pipeline Integration Issues (Engineering Scope)

These are entirely preventable through engineering discipline. They are not properties of
documents or models.

| Issue | Prevention | Detection |
| --- | --- | --- |
| Double JPEG compression | Lossless internal format mandate | Compression history log; JPEG quality extraction |
| Incorrect preprocessing order (scale after binarize) | DAG-enforced module ordering | Integration tests; canary documents |
| Wrong DPI metadata used for gating | Character-height measurement, not EXIF | Invariant checks at each stage |
| Non-idempotent pipeline | Pure-function module design | SHA256 content-addressable caching |
| Binarization before rotation | Stage ordering contract | Automated pipeline tests |

**Engineering reference**: Research shows that removing binarization or scaling from a
well-ordered pipeline causes 40% and 28% performance drops respectively — pipeline
ordering is not arbitrary.

---

## Preprocessing Decision Boundaries

### Pre-OCR Hard Gates (Reject → Request Re-Capture)

These conditions are not correctable through preprocessing. The system should produce
structured rejection metadata with a specific reason code.

| Condition | Threshold | Reason |
| --- | --- | --- |
| Severe motion blur | Laplacian variance < 50 (calibrate per domain) | Information physically lost; deblurring introduces ringing worse than blur |
| Extreme focus blur | Laplacian variance < threshold/2 | Sub-Nyquist sampling: hallucinates detail rather than recovering it |
| Very low resolution | cap-height < 8px OR effective DPI < 100 | Below recovery threshold for standard engines |
| Dense specular glare | Glare coverage > 5% of text area | Sensor clipping: information mathematically unrecoverable |
| Complete text occlusion | Text confidence = 0 over >50% of page | No information to recover |

### Soft Gates (Apply Remediation)

| Condition | Trigger | Intervention |
| --- | --- | --- |
| Mild blur | Laplacian variance 50–150 | Mild unsharp masking; flag if not improving |
| Low resolution (recoverable) | cap-height 10–20px OR DPI 100–150 | Bicubic upscaling to 300 DPI; effective from ~150 DPI |
| Skew > 0.5° and ≤ 7° | Hough transform | Affine rotation with bicubic interpolation |
| Skew > 7° | Hough transform | Apply deskew AND flag as likely capture fault |
| Non-uniform illumination | Regional mean std dev > threshold | Background estimation and division normalization |
| Salt-and-pepper noise | Extreme pixel count > threshold | Median filter (3×3 or 5×5) |
| Gaussian noise | Local variance analysis | Bilateral filter (edge-preserving) |
| Low contrast (recoverable) | Michelson contrast < 0.3 | CLAHE on L channel (clip limit 2.0–4.0, 8×8 grid) |
| JPEG quality 50–80 | Quantization table analysis or EXIF | Convert to lossless working format; apply deblocking if blockiness detected |
| Perspective distortion | Edge analysis / MobileNetV4 | Four-point perspective transform (not affine) |

### Key Metric Thresholds (Research-Validated)

| Metric | Minimum | Optimal | Measurement |
| --- | --- | --- | --- |
| Effective DPI | 200 (absolute gate) | 300–400 | Pixel count / physical dimension |
| cap-height (pixels) | 20 | 30–33 (LSTM optimal) | CC analysis or MSER |
| x-height (pixels) | 10 (absolute min) | 20–30 | MSER or CC analysis |
| Laplacian variance | ~100 (general) | >150 (OCR-specific) | `cv2.Laplacian(gray, cv2.CV_64F).var()` |
| JPEG quality | 80 | 95+ (lossless preferred) | Quantization table analysis |
| PSNR | 25 dB | 30–50 dB | Reference-based |
| Michelson contrast | 0.3 | >0.5 | (Imax − Imin) / (Imax + Imin) |
| Skew correction trigger | 0.5° | < 0.5° | Hough transform |
| CJK character minimum | 30×30 px | 40×40 px+ | Character patch analysis |

**Resolution note from research**: The "300 DPI rule" is a practical guideline, not a
universal law. The correct gate is measured character pixel height, not declared DPI —
declared DPI from EXIF can be wrong or absent. Project A's `resolution_quality.py`
correctly implements character-height-aware scoring via PaddleOCR + KDE mode.

---

## SigLIP 2 — Group 1: IQA Heads

**Heads**: blur, noise, contrast, skew_severity, compression, overall_quality

| Wild Condition | Freq | Training Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Multiply-distorted (blur+skew+noise simultaneously) | High | ❌ Missing | Critical — LIVE benchmark shows 15–25% metric drop | Deterministic |
| Mobile phone motion blur + defocus combined | High | ⚠️ Partial | Critical — only single-type blur in DIQA-5000 | Deterministic |
| Book gutter shadow gradient + curvature | High | ❌ Missing | Critical — sd7k covers flat-doc shadows only | Deterministic |
| Aged/historical (yellowing + foxing + ink fading) | Med | ❌ Missing | High — 0 human MOS labels for ink/paper degradation | Deterministic |
| Fax artifacts (halftone + banding + noise) | Med | ❌ Missing | High — no fax examples in IQA set | Deterministic |
| Screen recapture (RGB aliasing + moiré) | Med | ❌ Missing | High — unique artifact class (Moran z-ratio metric needed) | Deterministic |
| Receipt thermal fade + bleed-through | Med | ❌ Missing | High — bleed-through has 0 human MOS labels | Deterministic |
| JPEG quality < 50 (visible blocking artifacts) | High | ⚠️ Partial | High — not explicitly in training; DIQA-5000 underrepresents | Deterministic |
| Nth-generation photocopy (copies-of-copies) | Low | ❌ Missing | Med — cumulative degradation not modeled | Deterministic |
| Mixed-region quality (sharp header, blurry body) | Low | ❌ Missing | Med — per-region quality not in IQA datasets | Deterministic |
| Ink bleed-through from reverse side | Med | ❌ Missing | Med — bimodal background detection not trained | Deterministic |
| Specular glare (glossy paper sensor saturation) | Med | ❌ Missing | Med — HSV saturation analysis not labeled | Deterministic |

**Coverage Score**: 0/12 fully covered (0%) — Critical remediation required

**Key diagnostic metrics for this group:**

- Laplacian variance (blur): gate at 100–150; calibrate per document type
- Block-boundary gradient discontinuity at 8px intervals (JPEG artifact detection)
- Local contrast variance across 64×64 windows (mixed-region quality)
- Bimodal background intensity histogram (bleed-through detection)
- Regional illumination gradient standard deviation (shadow/glare)

---

## SigLIP 2 — Group 2: Script Detection

**Heads**: script_class (19–27 classes)

| Wild Condition | Freq | Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Mixed-script documents (Latin header + Arabic body) | High | ⚠️ Partial | High — 55% multi-script in training may over-represent | Deterministic |
| RTL+LTR embedded (Arabic + English numerals) | High | ✅ Covered | Low | — |
| Historical/archaic script variants (Fraktur, Ottoman Arabic) | Low | ❌ Missing | Med — fall outside standard training distributions | Statistical |
| Long-s and archaic orthographic variants | Low | ❌ Missing | Med — systematic substitution to 'f' or 'l' | Statistical |
| Mongolian vertical script | Low | ❌ Missing | Critical — 0 samples in training (OOD candidate) | Statistical |
| Script degraded near-illegibly | Med | ⚠️ Partial | Med — pristine base images, degradation varies | Deterministic |
| Very small font CJK (<8pt at standard DPI) | Med | ⚠️ Partial | Med — 7 DPI tiers help but CJK 8pt at 150 DPI fails | Deterministic |
| Decorative/display fonts deviating from standard | Low | ❌ Missing | Med — font diversity sparse for Tier 3–4 scripts | Statistical |
| Mathematical notation within text (formulae) | Med | ❌ Missing | Med — requires specialized equation recognition | Statistical |

**Coverage Score**: 1/9 fully covered (11%) — High remediation required

**Note**: Historical typography, archaic glyphs, and mathematical notation are
**Statistical** degradations — they cannot be resolved through image preprocessing
and require specialized model routing (see Out-of-Scope section).

---

## SigLIP 2 — Group 3: Orientation + Skew

**Heads**: orientation_class (4-class), skew_angle (regression)

| Wild Condition | Freq | Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Symmetric documents (identical at 180°) | High | ❌ Missing | Critical — whitespace-based disambiguation unavailable | Deterministic |
| Non-Latin orientation cues (RTL whitespace absent) | High | ⚠️ Partial | Critical — Arabic only ~500/50K samples (1%) | Deterministic |
| Camera perspective vs. pure rotation (skew >30°) | Med | ⚠️ Partial | High — conf≥0.7 filter removes hardest skew cases | Deterministic |
| Combined skew + warping (non-flat page) | Med | ❌ Missing | High — skew dataset assumes flat documents | Deterministic |
| Near-zero skew (70–80% of production scans <2°) | High | ⚠️ Partial | Med — distribution head-heavy, label noise floor matters | Deterministic |
| Partial/cropped page (scanner edge visible) | Med | ❌ Missing | Med — orientation ambiguous without full context | Deterministic |
| Multi-column layout breaking global skew estimate | Med | ❌ Missing | Med — projection profile fails across column gutters | Deterministic |
| Completely blank page (no text orientation cues) | Low | ❌ Missing | Med — orientation undefined, classifier may hallucinate | Deterministic |

**Coverage Score**: 0/8 fully covered (0%) — Critical remediation required

**Research note**: For multi-column documents, a single global Hough/projection-profile skew
estimate is unreliable. Research recommends running two independent skew detectors from different
families (e.g., Hough + projection profile) and accepting the estimate only when they agree
within 0.5°. Disagreement should be classified as "layout complexity" rather than pure skew.

---

## SigLIP 2 — Group 4: Handwriting

**Heads**: handwriting_presence (binary), handwriting_legibility (regression),
handwriting_script (3-class), handwriting_content_type (2-class), handwriting_density (regression)

| Wild Condition | Freq | Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Arabic cursive handwriting | High | ❌ Missing | Critical — KHATT dataset not yet added | Statistical |
| Chinese character (CJK) handwriting | High | ❌ Missing | Critical — CASIA-HWDB not yet added | Statistical |
| Devanagari handwriting (Shirorekha varies) | Med | ❌ Missing | Critical — IIIT-INDIC not yet added | Statistical |
| Cyrillic handwriting | Med | ❌ Missing | High — HKR dataset not yet added | Statistical |
| Form fill-in (handwriting within printed fields) | High | ❌ Missing | High — FUNSD has 199 images only | Deterministic |
| Signatures overlapping printed text | High | ⚠️ Partial | High — IAM doesn't include signatures | Deterministic |
| Marginalia/annotations alongside print | Med | ❌ Missing | Med — no annotation-specific training data | Deterministic |
| Multiple writers on same page | Low | ❌ Missing | Low — rare production scenario | Deterministic |
| Typewriter text (semi-mechanical, historical) | Low | ❌ Missing | Low — falls between print and handwriting | Statistical |

**Coverage Score**: 0/9 fully covered (0%) — Critical remediation required

**Important**: Non-Latin handwriting recognition is a **Statistical** degradation beyond the
scope of Project A's preprocessing. Project A's role is to **detect and classify** handwriting
presence, legibility, and density so that Project B can route to the appropriate specialized
HWR model. Preprocessing cannot make Arabic cursive recognizable to a Latin-trained model.

---

## SigLIP 2 — Group 5: Page Attributes

### Capture Method (7-class)

| Wild Condition | Freq | Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Modern color flatbed scanner (2020+, CIS sensor) | High | ❌ Missing | Critical — RVL-CDIP is 1990s CCD only | Deterministic |
| ADF scanner (edge-feed, curl artifacts) | High | ❌ Missing | High — no ADF-specific training data | Deterministic |
| Screen recapture (phone photographing monitor) | Med | ❌ Missing | High — distinct moiré artifact class | Deterministic |
| 4th-generation photocopy | Low | ❌ Missing | Med | Deterministic |
| High-speed production scanner | Med | ❌ Missing | Med | Deterministic |
| Born-digital PDF with embedded raster images | High | ⚠️ Partial | Med — mixed vector/raster not well-represented | Deterministic |

**Coverage Score**: 0/6 fully covered (0%)

**Born-digital PDF note**: Research highlights that for born-digital PDFs, the correct
preprocessing action is to **bypass optical preprocessing entirely** and extract the native
text layer for 100% character fidelity. The `pdf_type_classifier.py` supports this routing,
but it must be validated that born_digital pages with native text layers are correctly
identified and routed before pixel preprocessing is applied.

### Shadow (regression)

| Wild Condition | Freq | Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Book gutter/spine shadow (gradient curve) | High | ❌ Missing | Critical — sd7k is flat-doc only | Deterministic |
| Finger-cast shadows (document held by hand) | High | ⚠️ Partial | High | Deterministic |
| Scanner lid not fully closed (partial illumination) | Med | ⚠️ Partial | Med | Deterministic |
| Multiple overlapping shadows | Low | ❌ Missing | Low | Deterministic |
| Specular glare adjacent to shadow (mixed) | Low | ❌ Missing | Low — requires separate glare mask | Deterministic |

**Coverage Score**: 0/5 fully covered (0%)

**Detection method**: Homomorphic filtering in log-space separates illumination (low-frequency)
from reflectance (high-frequency) for shadow removal. Background estimation + division
normalization handles gradient shadows. Glare detection uses HSV saturation-channel analysis:
regions where V > 250 and S < 20.

### Warping (regression)

| Wild Condition | Freq | Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Book spine cylindrical distortion | High | ⚠️ Partial | High — warpdoc limited | Deterministic |
| Page curl from humidity | Med | ✅ Covered | Low | Deterministic |
| Crumpled/creased pages | Low | ❌ Missing | Med | Deterministic |
| Combined warp + skew + blur | Med | ❌ Missing | High | Deterministic |
| Folded document (sharp crease, two-plane) | Low | ❌ Missing | Med | Deterministic |

**Coverage Score**: 1/5 fully covered (20%)

**Correction boundary**: DocUNet and DewarpNet-class learning-based unwarping is appropriate
for camera-captured book pages. Current `perspective_correction.py` handles keystoning.
Complex cylindrical distortion (deep book spine) may require a specialized dewarping model —
this is tracked as a potential Phase 5 extension.

### Resolution Quality (regression)

| Wild Condition | Freq | Coverage | Gap Severity | Research Category |
| --- | --- | --- | --- | --- |
| Vector PDF rendered at low effective DPI | High | ❌ Missing | Critical — misleading resolution signal | Deterministic |
| Upscaled raster (bicubic 2×–4×) | High | ❌ Missing | Critical — artificially inflates char height | Deterministic |
| Mixed raster/vector document | Med | ❌ Missing | High | Deterministic |
| DPI gradient within document | Low | ❌ Missing | Med | Deterministic |
| Sub-pixel ClearType rendering | Med | ❌ Missing | Med | Deterministic |
| Very low DPI (< 100 DPI, unrecoverable) | Med | ❌ Missing | Critical — below recovery boundary | Deterministic (reject) |

**Coverage Score**: 0/6 fully covered (0%)

**Resolution detection note**: EXIF/metadata DPI cannot be trusted as the primary gate.
The correct measurement is character pixel height via CC analysis or MSER detection,
which is what `resolution_quality.py` implements. The specific failure mode for pre-upscaled
rasters is that the measured pixel height is artificially inflated — the system must
cross-validate with actual OCR quality probes for these cases.

---

## MobileNetV4 — Pre-Correction Heads

### Orientation (4-class)

Same conditions as SigLIP 2 Group 3 orientation — see above.
MobileNetV4 is the pre-correction fast pass; SigLIP 2 provides the refined post-correction
result. The pre-correction gate runs on the **uncorrected, potentially distorted** image,
making its wild condition exposure identical to Group 3 but with greater severity since
all analysis for Stage 2 depends on Stage 1 getting orientation and resolution right.

### Skew (regression)

Same conditions as SigLIP 2 Group 3 skew — see above. The confidence≥0.7 filter applied
during dataset construction removes the hardest cases (>15° combined skew+perspective),
which are precisely the cases that most need correction.

### Resolution Quality (0–1 regression)

Same conditions as SigLIP 2 Group 5 resolution quality — see above.

---

## Conditions Out of Scope (Impractical for Preprocessing)

The following conditions cannot be resolved through image preprocessing. Project A's role
is to **detect, classify, and route** documents exhibiting these conditions — not to correct
them. Where noted, the system should produce rejection metadata or escalate to human review.

### 1. Irrecoverable Physical Damage

| Condition | Why Irrecoverable | Correct Action |
| --- | --- | --- |
| Physical tears through character bodies | Information physically absent | Reject; flag for re-scan from another copy |
| Complete text occlusion by opaque stains | No signal beneath stain | Reject; flag for physical restoration or manual transcription |
| Severe ink dissolution (text fully dissolved) | Sub-Nyquist: no frequency content to reconstruct | Reject; flag for archival intervention |
| Catastrophic water damage obliterating geometry | All structural information lost | Reject |

### 2. Irrecoverable Capture Failures

| Condition | Why Irrecoverable | Correct Action |
| --- | --- | --- |
| Severe motion blur (Laplacian variance < 50) | Deconvolution introduces ringing worse than blur | Reject; request re-capture |
| Extreme out-of-focus capture | Spatial frequencies permanently attenuated | Reject; request re-capture |
| Dense specular glare > 5% text area | Sensor clipping: 8-bit maximum — no information | Reject; request re-capture with corrected lighting |
| Effective DPI < 100 with standard fonts | Below upscaling recovery threshold | Reject; request re-scan at ≥ 300 DPI |

### 3. Statistical / Model-Level Problems (Not Pixel Problems)

These require model routing, domain adaptation, or retraining — not preprocessing.

| Condition | Why Preprocessing Cannot Help | Correct Routing |
| --- | --- | --- |
| Unseen script family (Mongolian, Syriac, Georgian) | Model learned boundaries don't exist for these | OOD detection → human review queue |
| Historical typography (archaic glyph sets) | Feature extractor can't map to correct latent space | Route to specialized historical OCR (Kraken + ByT5) |
| Calligraphic / decorative fonts not in training | Visual representation outside training distribution | Route to vision-language model with OCR post-correction |
| Mathematical equation recognition | Requires specialized equation model (MathPix-class) | Route to specialized equation OCR |
| Handwriting in unsupported script | Training data absent; preprocessing doesn't change model weights | Route to appropriate HWR model based on script detection |
| Real-word OCR substitutions (59% of OCR errors) | Valid words substituted; undetectable via image preprocessing | Post-OCR correction with language model (Project C) |
| Model confidence calibration drift | Statistical property of model, not of image | Trigger ECE-based model recalibration in `drift/` |

### 4. Semantic / Layout Problems Requiring Model-Level Solutions

| Condition | Why Preprocessing Cannot Help | Correct Routing |
| --- | --- | --- |
| Ambiguous reading order in complex layouts | Semantic problem: visual preprocessing cannot infer intent | Layout model with directed graph reading order (Project B) |
| Table cell merging across OCR output | Structural extraction failure after correct recognition | Table structure model (Project B) |
| Multi-column text flow coordination | Global document understanding required | Layout-aware OCR mode (Project B) |
| Footnote / endnote association | Discourse-level, not pixel-level | NLP model (Project C) |

### 5. Prevention-Only Problems (Engineering Discipline)

| Condition | Prevention Method | Why Not Correctable After |
| --- | --- | --- |
| Double JPEG compression (quality degradation accumulates) | Mandate lossless internal format (PNG/TIFF) | Information is already lost; deblocking smears strokes |
| Pipeline ordering errors (scale after binarize) | DAG-enforced module ordering | Aliasing and stroke distortion from binarized rotation |
| Wrong DPI metadata propagation | Character-height measurement at each stage | Cannot retroactively know true DPI if metadata was wrong |

---

## Coverage Summary

| Head Group | Heads | Wild Conditions | Fully Covered | Coverage % | Priority |
| --- | --- | --- | --- | --- | --- |
| IQA (SigLIP G1) | 6 | 12 | 0 | 0% | P0 Critical |
| Script (SigLIP G2) | 1 | 9 | 1 | 11% | P0 High |
| Orientation+Skew (SigLIP G3) | 2 | 8 | 0 | 0% | P0 Critical |
| Handwriting (SigLIP G4) | 5 | 9 | 0 | 0% | P0 Critical |
| Capture (SigLIP G5) | 1 | 6 | 0 | 0% | P0 Critical |
| Shadow (SigLIP G5) | 1 | 5 | 0 | 0% | P1 High |
| Warping (SigLIP G5) | 1 | 5 | 1 | 20% | P1 High |
| Resolution (SigLIP G5) | 1 | 6 | 0 | 0% | P0 Critical |

**Overall**: 2/60 wild conditions fully covered (3%)

---

## Remediation Priority

**P0 — Must fix before production deployment:**

1. Multiply-distorted IQA samples (blur+skew+noise simultaneously) — generate compound
   distortion dataset from DIQA-5000 / OHR-Bench using augmentation pipeline
2. JPEG quality detection at intake — add JPEG quality gate to ingestion; flag quality < 80
3. Mongolian vertical script (complete OOD gap) — already designated OOD; confirm detection
4. Symmetric document orientation (near-identical 0°/180°) — add content-aware disambiguation
5. All non-Latin handwriting classification (Arabic, CJK, Devanagari, Cyrillic) — add KHATT,
   CASIA-HWDB, IIIT-INDIC, HKR datasets
6. Modern scanner capture method (2020+ CIS flatbed, ADF) — source dedicated capture examples
7. Vector PDF / upscaled raster resolution quality confounds — synthetic confound dataset

**P1 — Fix before scaling deployment:**

1. Book gutter shadow gradient (flat-doc-only training) — need bent-document shadow dataset
2. Mobile motion blur + defocus combination — multi-distortion augmentation
3. Arabic/Hebrew orientation representation (<1% of 50K orientation set)
4. FUNSD form fill-in expansion — add IAM-OnDB, RIMES, ESPOSALLES datasets
5. Multi-column skew detection validation — cross-detector agreement check

**P2 — Monitor and improve incrementally:**

1. Screen recapture moiré detection — add Moran z-ratio metric to IQA
2. Crumpled/creased page warping — extend warpdoc with physical crumple augmentation
3. Born-digital bypass path validation — confirm pdf_type_classifier correctly gates
4. Historical typography detection — add confidence-based routing to specialized models

---

## Related Documents

- [OOD Dataset Design](OOD_DATASET_DESIGN.md)
- [Dataset Diversity Requirements](DATASET_DIVERSITY_REQUIREMENTS.md)
- [Diversity Remediation Plan](DIVERSITY_REMEDIATION_PLAN.md)
- [Stream 4C Dataset Handoff](STREAM_4C_DATASET_HANDOFF.md)
- [SigLIP 2 Multitask Requirements](SIGLIP2_MULTITASK_REQUIREMENTS.md)
- Research basis: `tmp_cleanup/ocr_preprocessing_research/`
