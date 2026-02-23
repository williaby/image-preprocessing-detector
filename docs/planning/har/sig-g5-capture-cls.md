# Head Adequacy Review: capture_cls (SIG-G5-1)

> **Status**: ✅ Complete
> **Version**: 2.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: F — Page Attributes
> **Adequacy**: ⚠️ Needs Work (Score: 59.1 / 100 | P0 blockers present)

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G5-1 |
| Model | SigLIP 2 NAFlex |
| Group | G5 — Page Attributes |
| Head Name | capture_cls (also written as capture_method_cls) |
| Task Type | Classification — 7 classes |
| Output Format | Softmax over 7 capture methods |
| Priority | P2 |
| Performance Target | Accuracy ≥ 85%, Macro F1 ≥ 0.80 |
| Primary L2 Field | `capture_method.method` (7-class enum) |
| Shared-Data Heads | None (dedicated capture-method dataset) |
| Training Phase | Phase 5 — Page Attributes |

### 7 Canonical Classes

| Class | Description |
| --- | --- |
| BORN_DIGITAL | PDF/vector document rendered directly to image |
| SCANNER_FLATBED | Flatbed scanner acquisition (CCD or CIS sensor) |
| SCANNER_ADF | Automatic Document Feeder scanner |
| CAMERA_PROFESSIONAL | DSLR or mirrorless camera (dedicated photography session) |
| CAMERA_SMARTPHONE | Smartphone or tablet camera |
| FAX | Fax transmission artifact pattern (halftone + banding + low SNR) |
| SYNTHETIC | Computationally generated (Augraphy, synth pipelines, DocSynth300K) |

### L2 capture_method Known Values

| Dataset | L2 Value | Maps To | Granularity Gap |
| --- | --- | --- | --- |
| rvl_cdip | `"scanner"` (bare) | SCANNER_FLATBED (default) | Cannot distinguish FLATBED vs ADF |
| doclaynet | `"born_digital"` | BORN_DIGITAL | None |
| midv500, realdae, smartdoc-qa, sd7k, wsrd | `"camera_smartphone"` | CAMERA_SMARTPHONE | Cannot distinguish from CAMERA_PROFESSIONAL |
| docsynth300k, synth-multiscript-v3 | not populated | SYNTHETIC (derivable) | Must be set via override pattern |

**Critical Infrastructure Gap**: The L2 `capture_method.method` field currently stores 3-class granularity
(`born_digital`, `scanner`, `camera_*`) but the head requires 7-class granularity. Four classes
(SCANNER_ADF, CAMERA_PROFESSIONAL, FAX, SYNTHETIC) cannot be derived from existing L2 field values
without additional labeling work — either heuristic, manual, or synthetic.

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `capture_method.method` (7-class enum string)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better; tier_3_heuristic acceptable with
manual validation for ADF/FAX classes given no alternative)

**Label Provenance**: tier_0_exact for born_digital and synthetic (derivable from dataset origin);
tier_3_heuristic for scanner sub-type splits (ADF vs flatbed); tier_2_model_assisted or
tier_3_heuristic for FAX (Augraphy simulation)

### Per-Class Source Analysis

**BORN_DIGITAL** — Target: 15,000 (30%)

Primary sources: DocLayNet (80K images, 100% born_digital L2 label, Audit A/96),
PubTabNet (519K, born-digital), FinTabNet (97K, born-digital).

Current usable: ~80K+ available after downsampling. Well-covered. No labeling work required.
Diversity concern: DocLayNet is 98.5% Latin script — needs supplementation with non-Latin
born-digital documents for script diversity within class.

**SCANNER_FLATBED** — Target: 12,500 (25%)

Primary sources: RVL-CDIP (400K images, all labeled bare `"scanner"`, Audit B/87),
Tobacco800 (1,290, Audit A/91), NIST SD-2 (5,590, Audit B/82), NIST SD-6 (5,595, Audit B/83),
MDIW13 (290K script-diverse scanner scans, Audit D/87).

Current usable after default mapping: ~10,000 from dry-run. With MDIW13 added: up to 30K+ available.
Risk: All RVL-CDIP and NIST sources are 1990s CCD technology. Modern CIS flatbeds (2010+) have
different noise profiles (lower grain, better color) not represented in training. Minimum 1,500
modern CIS examples needed (source: MIDV-2020 or equivalent). See Gap CAP-G08.

**SCANNER_ADF** — Target: 2,500 (5%)

Primary sources: RVL-CDIP (must be subset-labeled from existing scanner images via heuristic).

Current usable: ~0 (no ADF-distinct label in any L2 sidecar).

ADF visual heuristics per DATASET_DIVERSITY_REQUIREMENTS §7.3:

- Edge-parallel dark bands (2-5px near page margins from roller mechanism)
- Systematic micro-skew pattern (consistent 0.2-0.8° skew in same direction per batch)
- Paper-feed direction artifacts (horizontal streaks from roller dust/contamination)
- Multi-page separator marks (single-pixel horizontal lines)

**Critical constraint**: RVL-CDIP images are largely low-resolution, binarized, and cropped in
preprocessing. Many ADF-characteristic artifacts are destroyed in the preprocessing pipeline. The
fraction of RVL-CDIP images where these heuristics are reliable is estimated at 20-40% (not the
full 400K). Usable pool after heuristic: estimated 5,000-15,000 candidate images, of which
~2,500 will meet confidence threshold after 100-sample manual validation.

VLM labeling feasibility: A VLM (Claude Opus 4.6 with vision) can reliably identify ADF-specific
artifacts — particularly edge bands and horizontal roller streaks — when they are visible. VLM
validation at 10% sample rate (250 images) is recommended before propagating labels to the
full candidate pool. VLM cannot distinguish when artifacts are absent (high-quality ADF scan).
Estimated VLM precision on ADF-positive examples: ~70-75%.

**CAMERA_PROFESSIONAL** — Target: 5,000 (10%)

Primary sources: None identified. MIDV500 and SmartDoc-QA are explicitly smartphone/tablet captures.
DATASET_DIVERSITY_REQUIREMENTS §7.1 lists MIDV500 and SmartDoc-QA as sources for this class —
this is a plan error. These datasets contain no professional DSLR captures.

Current usable: ~0 from existing L2 metadata (near-zero actual DSLRs in source pool).

Estimation of available external data: Would require a new dedicated collection effort (studio
photography session) or licensing professional photography datasets. This is outside the current
source pool scope. Estimated sourcing effort: 1-2 weeks, not compatible with the 5-day P0
resolution threshold.

**Consensus assessment**: Both Gemini 2.5 Pro and Gemini 3 Pro rate this class as effectively
blocked or invalid. The visual distinction between a high-end smartphone and a DSLR for flat document
photography is often negligible. Recommend merging CAMERA_PROFESSIONAL into CAMERA_SMARTPHONE as a
single CAMERA class (6-class schema reduction).

**CAMERA_SMARTPHONE** — Target: 5,000 (10%)

Primary sources: MIDV500 (15K, Audit B/82), SmartDoc-QA (4,280, Audit A/92), RealDAE (1,200,
Audit B/84), sd7k (7,239, Audit B/87), wsrd (4,500, Audit A/95).

Current usable: ~19,893 from dry-run (exceeds 5K target). If CAMERA_PROFESSIONAL is merged into
this class, the combined CAMERA target would be ~10,000 (still covered by existing pool of ~19,893).

**FAX** — Target: 2,500 (5%)

Primary sources: None with explicit FAX labels. RVL-CDIP includes fax document types in its 16-class
taxonomy but no per-image FAX acquisition label.

Path 1 (heuristic + synthesis): Manual labeling of ~500 RVL-CDIP images using FAX visual markers
(halftone screening, 1D horizontal banding, effective resolution typically < 150 DPI, binarized
output, high noise) followed by Augraphy `Faxify` simulation to extend to ~2,500-5,000 images.
Estimated effort: 1 day labeling + 0.5 day generation.

Path 2 (validation problem): Training on synthetic FAX images but having zero real FAX images for
test set means validation F1 is meaningless for real-world deployment. Tobacco800 contains some
fax-adjacent historical document types (halftone, aged paper) but not explicit FAX captures.

Consensus assessment: FAX via Augraphy is technically feasible for training data generation but
validation remains blocked without real FAX examples. Both models flag this as a sim-to-real
deployment risk, not a training blocker.

**SYNTHETIC** — Target: 7,500 (15%)

Primary sources: DocSynth300K (300K, derivable), synth-multiscript-v3 (190K on GCS, derivable).

Current usable: ~7,500+ available immediately after applying SYNTHETIC label override (KI-005
pattern: `capture_method=synthetic` for all synth pipeline outputs). No additional labeling work
required; provenance is self-evident.

Semantic definition concern: SYNTHETIC should be defined as "programmatically generated document
images with no physical capture step" — not generative AI fakes. Born-digital PDFs that went
through a physical scanner would be SCANNER_FLATBED, not SYNTHETIC. A computer-generated invoice
rendered as a PDF and exported as PNG would be BORN_DIGITAL if it represents a real document.
SYNTHETIC is reserved for images that never had a paper form (DocSynth, synth-multiscript pipeline).

### Usable Pool Summary

| Class | Target | Current Usable | Gap | Risk |
| --- | --- | --- | --- | --- |
| BORN_DIGITAL | 15,000 | ~80,000 available | 0 (downsample) | LOW |
| SCANNER_FLATBED | 12,500 | ~30,000 (RVL-CDIP + MDIW13) | 0 (modern CIS gap) | MEDIUM |
| SCANNER_ADF | 2,500 | ~0 (needs heuristic labeling) | 2,500 | HIGH |
| CAMERA_PROFESSIONAL | 5,000 | ~0 (no DSLR dataset) | 5,000 | BLOCKED |
| CAMERA_SMARTPHONE | 5,000 | ~19,893 | 0 (exceeds target) | LOW |
| FAX | 2,500 | ~0 (needs synthesis) | 2,500 | HIGH |
| SYNTHETIC | 7,500 | ~50,000 available | 0 (downsample) | LOW |
| **Total** | **50,000** | **~130,000** (3-class) | **10,000+** (7-class) | |

**Net assessment**: Total pool is technically sufficient if schema is reduced. Under the 7-class
schema as defined, CAMERA_PROFESSIONAL (5,000) and SCANNER_ADF (2,500) are the hard blockers.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| KI-005 | docsynth, synth-multiscript-v3, jssoda | capture_method | LLM cannot detect synthetic capture method; requires override | Override pattern in assembly script |
| KI-004 | capture_method via L2 inference | capture_method | Born-digital images misclassified as scanner when rendered from PDF then cropped | Validate via spot-check of scanner-labeled DocLayNet pages |
| KI-009 | cc-ocr (D-grade) | domain | Domain coverage gap means 0.3× weight in assembly | Apply weight in assembly script |

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 50,000 images |
| Assembly Status | ⏳ Not started (source subcommand dry-run: 39,893 records — 3-class granularity only) |
| Distribution Gaps | FAX: ~0; SCANNER_ADF: ~0; CAMERA_PROFESSIONAL: ~0 |
| Source Mapping | L2_TO_SOURCE_CLASS handles known variants; bare `"scanner"` → SCANNER_FLATBED confirmed working |
| Assembly Script | `scripts/prepare_multitask_datasets.py source` (needs 7-class upgrade) |
| Labeling Script | `scripts/label_capture_method.py` — ADF/FAX heuristic classifier on RVL-CDIP (pending) |

### Class Distribution Targets

| Class | Target Images | Current Estimate | Risk |
| --- | --- | --- | --- |
| BORN_DIGITAL | 15,000 | ~80K available (downsample) | LOW |
| SCANNER_FLATBED | 12,500 | ~10K (dry-run), ~30K with MDIW13 | MEDIUM (modern CIS gap) |
| SCANNER_ADF | 2,500 | ~0 (heuristic labeling needed) | HIGH |
| CAMERA_PROFESSIONAL | 5,000 | ~0 (no identified DSLR source) | BLOCKED |
| CAMERA_SMARTPHONE | 5,000 | ~19,893 (dry-run) | LOW |
| FAX | 2,500 | ~0 (Augraphy synthesis needed) | HIGH |
| SYNTHETIC | 7,500 | ~50K+ available (downsample) | LOW |

### Recommended Schema Reduction (from consensus)

If CAMERA_PROFESSIONAL cannot be sourced within Phase 5 timeline, adopt 6-class schema:

| Revised Class | Maps From | Target |
| --- | --- | --- |
| BORN_DIGITAL | BORN_DIGITAL | 15,000 |
| SCANNER_FLATBED | SCANNER_FLATBED | 14,000 |
| SCANNER_ADF | SCANNER_ADF | 3,000 |
| CAMERA | CAMERA_PROFESSIONAL + CAMERA_SMARTPHONE | 8,000 |
| FAX | FAX | 3,000 |
| SYNTHETIC | SYNTHETIC | 7,000 |

6-class target: 50,000. All classes feasible with existing source pool + ADF heuristic + FAX Augraphy.

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 61.6 / 100 (computed)

This head is unique among all SigLIP 2 heads: capture_method IS the label, so within-class diversity
is more important than cross-class diversity. Each capture class must internally represent the full
range of real-world conditions it would encounter in production.

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL — the label; must have ≥ 500 per class | All 7 classes, ≥ 500 each | 3 classes at target; 4 classes at ~0 | 43% |
| domain | `domain.level1` | IMPORTANT — born_digital should span TAX/FIN/SCI/MED | ≥ 5 domains per capture class | DocLayNet spans FIN/TEC/SCI; RVL-CDIP spans ADM/LEG/SCI | 70% |
| degradation | `quality.degradations` | HIGH — capture-specific artifacts (ADF roller, FAX banding, camera lens) | Per-class degradation patterns | Scanner artifacts in RVL-CDIP; camera in smartdoc; none for FAX | 65% |
| color_mode | `image_properties.color_mode` | HIGH — FAX/ADF produce binarized; born_digital is color | All 3 modes per relevant class | Born-digital: color; Scanner: grayscale/binarized; FAX missing | 60% |
| document_age | `image_properties.document_age` | MEDIUM — RVL-CDIP has aged documents; born_digital is modern | ≥ 2 age classes per scanner class | RVL-CDIP/Tobacco800 have aged; modern CIS gap | 60% |
| resolution | `resolution.category` | MEDIUM — scanner DPI varies 150-600; FAX typically < 150 effective | ≥ 3 resolution tiers per class | Multi-tier in scanner sources; FAX has characteristic low DPI | 70% |
| script_code | `language.script_code` | MEDIUM — DocLayNet/RVL-CDIP are 95%+ Latin; camera datasets have more diversity | ≥ 3 script families per capture class | Camera (MIDV500/SmartDoc): Latn-dominant; MDIW13 for scanner diversity | 55% |
| layout_type | `structure.layout_type` | LOW — layout should not drive capture prediction | ≥ 3 types per class | Covered by DocLayNet variety | 70% |

### Cross-Class Confusability Analysis

| Class Pair | Confusability | Visual Separator | Training Mitigation |
| --- | --- | --- | --- |
| SCANNER_FLATBED vs SCANNER_ADF | HIGH — clean ADF scan ≡ flatbed | ADF: edge bands, consistent micro-skew | Heuristic labels require manual validation (100-sample spot-check) |
| SCANNER_FLATBED vs BORN_DIGITAL | MEDIUM — born-digital at 150 DPI resembles low-res scan | Flatbed: grain texture, margin shadows | Include both in training; eFax edge case |
| FAX vs SCANNER_FLATBED (binarized) | HIGH — fax output and binarized scan overlap visually | FAX: 1D horizontal banding, halftone, < 150 DPI effective | FAX needs characteristic training examples with clear banding |
| CAMERA_SMARTPHONE vs CAMERA_PROFESSIONAL | HIGH — virtually indistinguishable for flat document shots | Professional: DoF blur, RAW-quality noise profile | Schema reduction recommended (merge into CAMERA) |
| SYNTHETIC vs BORN_DIGITAL | MEDIUM — DocSynth300K PDFs resemble born-digital | Synthetic: programmatic artifacts, perfect kerning, no scan noise | Strict definition: SYNTHETIC = no paper form; BORN_DIGITAL = real document |

### Domain Diversity within BORN_DIGITAL Class

DocLayNet (80K) spans: FIN 32%, TEC 29%, SCI 17%, LAW 5%, MAN 5% — strong but missing ADM,
MED, EDU domains. Supplementation with FinTabNet (FIN), PubTabNet (SCI), multimodal-textbook
(EDU) provides broader coverage.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 33.3% (2 partial + 0 full out of 6 conditions)

| Wild Condition | L2 Field Evidence | Training Coverage | OOD Coverage | Status |
| --- | --- | --- | --- | --- |
| Screen recapture (camera photographing monitor — moiré + RGB aliasing) | No training analog in any source dataset | None | OOD-Capture 3a (200 images) | ⚠️ Partial — OOD only |
| ADF scanner with curl artifacts (page feed introduces page_curl warping) | No ADF-labeled training examples | None | OOD-Capture 3b (150 images) — cross-category with warping_reg | ⚠️ Partial — OOD only |
| 4th-generation photocopies (multi-pass Augraphy degradation) | Not represented in training scanner class | None | OOD-Capture 3c (150 images, Augraphy 4-pass) | ⚠️ Partial — OOD only |
| High-speed production scanner (motion artifacts at >200 ppm speed) | RVL-CDIP/Tobacco800 are desktop scanners, not production units | None | OOD-Capture 3d (100 images, internal acquisition) | ⚠️ Partial — OOD only |
| FAX transmission artifacts on real fax machine output | No training examples (FAX class currently 0 images) | None | No dedicated OOD entry | ❌ Not covered |
| eFax / digital fax (born-digital document transmitted as fax) | Born-digital that acquires FAX artifacts during transmission | None | No OOD entry; semantic boundary unclear | ❌ Not covered |

**Missing OOD entry**: The OOD-Capture design covers scanner and camera stress scenarios well but has
no dedicated sub-source for real FAX machine output. Without real FAX validation data, the FAX class
accuracy cannot be measured in production conditions. Recommend adding OOD-Capture 3e: real fax
output (50 images, sourced from legal/government archives with physical fax machine provenance).

**Cropped vs uncropped scanner OOD (Gemini 3 Pro recommendation)**: Scanner ADF vs flatbed
distinction relies partly on border artifacts. OOD should include ~50 images where border artifacts
are deliberately cropped out, to test whether the model learned robust features vs border shortcuts.
Add as OOD-Capture 3d-extension (no acquisition effort — synthetic crop on existing 3d images).

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Capture (Phase 3, P0, 600 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 3a. Screen recaptures | 200 | Internal photography of monitor displaying documents (LCD/OLED/E-ink, 3 device types × 3 angles × 20+ documents) | `capture_method=camera_smartphone`, `warping_type=perspective`, moiré presence flag, IQA labels | siglip2 | Unique distortion: moiré patterns + RGB subpixel aliasing from screen. Cross-categorizes with OOD-Mixed. Must be from sources with no training analog. |
| 3b. ADF scanner with curl artifacts | 150 | Internal ADF scans (Fujitsu ScanSnap or equivalent) with deliberate page curl | `capture_method=scanner_adf`, `warping_type=page_curl`, `warping_severity`, `skew_angle_degrees` | siglip2 | ADF-specific artifacts not well-represented in training. Cross-categorizes with OOD-Degradation/warping_reg. Labels for both capture_cls AND warping_reg must be populated. |
| 3c. 4th-generation photocopies | 150 | Augraphy simulation (4 passes of `PaperFactory` + `DirtyRollers` + `Letterpress`) on training-excluded source documents | `capture_method=scanner_flatbed`, `document_age=aged`, `degradation_count` ≥ 4, IQA labels | siglip2 | Simulates multi-generational photocopy degradation. Distinct from single-pass scanner examples in training. |
| 3d. High-speed production scanner | 100 | Internal production scanner acquisition (Kodak, Canon DR series) at 300+ ppm | `capture_method=scanner_flatbed`, IQA labels, `color_mode` | siglip2 | Production-grade scanner characteristics (motion blur at speed, edge distortion). Distinct from desktop flatbed in training. Extension: include 50-image border-cropped variants (all images) to test border-artifact dependency. |

### Recommended OOD Additions

| Proposed Sub-Source | Target | Purpose | Acquisition Method |
| --- | --- | --- | --- |
| 3e. Real fax machine output | 50 images | Validate FAX class accuracy on real (not synthetic) fax images | Source from legal/government archives, law firms, or internal fax machine scan |
| 3d-ext. Border-cropped scanner variants | ~50 | Test whether ADF vs flatbed detection degrades when border artifacts removed | Apply aggressive center-crop to existing 3d images (no new acquisition) |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 3, P0)

### OOD Leakage Risk

RVL-CDIP is a training source. OOD-Capture must use internally acquired or independently
photographed/scanned documents. Screen recaptures (3a), ADF internal scans (3b), Augraphy
photocopies (3c, from excluded source docs), and production scanner outputs (3d) all represent
acquisition scenarios not present in training datasets. Dedup required against training manifests:
SHA256 + pHash (Hamming ≤ 5). Fax OOD (3e) must be confirmed as not previously digitized into
any known training dataset.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G5-3 (warping_reg) | OOD-Capture sub-source 3b (ADF curl) is shared — same 150 images require both `capture_method=scanner_adf` AND `warping_severity` labels | Single annotation pass must populate both L2 fields. Warping_reg team lead and capture_cls team lead must coordinate 3b acquisition and labeling. |
| SIG-G5-5 (resolution_quality_reg) | Born-digital capture at low DPI creates interaction: capture_cls labels the method; resolution_quality_reg scores the visual quality | A document labeled BORN_DIGITAL may receive high resolution_quality despite low DPI (large-font paradox documented in OOD-Resolution 6a). Downstream routing must account: born-digital low-DPI does not require upscaling the same way scanned low-DPI does. |
| SIG-G3-1 (orientation_cls) | Screen recaptures (OOD-3a) introduce unusual orientations from viewing angle | OOD-3a images should also include `orientation_class` labels for cross-head OOD analysis. Moiré degradation may stress orientation head performance as a secondary effect. |
| SIG-G1-1 through SIG-G1-6 (IQA heads) | FAX class has characteristic IQA signature (low contrast, binarized, high noise) | FAX training examples must have IQA labels populated alongside capture_method labels. The IQA heads and capture_cls head should produce consistent joint predictions on FAX images (low contrast + low resolution + capture_method=FAX). |

### Split Leakage Risk

**Level**: MEDIUM

RVL-CDIP (400K images) is shared across capture_cls training and natural-scan skew training and
the orientation dataset. Global split registry enforces that images in capture_cls training
are not in test splits of other datasets drawing from RVL-CDIP. DocLayNet is similarly shared
(capture_cls BORN_DIGITAL + orientation real component + IQA curated dataset).

### Label Convention

7 canonical classes per L2 schema. Bare `"scanner"` from rvl_cdip maps to SCANNER_FLATBED by
default. Any ADF labeling script must update L2 sidecars to `"scanner_adf"` explicitly and record
labeling confidence in the sidecar. SYNTHETIC class requires override pattern per KI-005
(LLM cannot detect synthetic origin — provenance must be set by assembly script based on source
dataset identity, not inference).

If schema reduction is adopted (6-class), CAMERA_PROFESSIONAL images labeled in any external
source should be remapped to CAMERA_SMARTPHONE in the assembly script via the
`L2_TO_SOURCE_CLASS` mapping update.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| CAP-G01 | SCANNER_ADF not separable from SCANNER_FLATBED in any L2 metadata (all RVL-CDIP uses bare `"scanner"`) | L2 metadata design did not capture scanner sub-type | Implement `scripts/label_capture_method.py` ADF heuristic: edge bands + micro-skew pattern + horizontal streaks on RVL-CDIP images; validate on 100-sample manual spot-check before propagation; estimated 2,500 usable ADF images after filtering | 2-3 days |
| CAP-G02 | CAMERA_PROFESSIONAL class: near-zero usable data across all source datasets | MIDV500/SmartDoc-QA are smartphone captures; no DSLR document photography datasets exist in source pool | Option A: Source dedicated DSLR photography session (~2 weeks effort). Option B: Schema reduction — merge CAMERA_PROFESSIONAL into CAMERA_SMARTPHONE, adopt 6-class schema. Option B is recommended by consensus | 1-2 weeks (Option A) or 1 day (Option B schema change) |
| CAP-G03 | FAX class: zero labeled training examples; no real FAX validation data | FAX documents rare in modern public datasets; RVL-CDIP has FAX doc types but no per-image FAX acquisition label | Step 1: Manual label ~500 RVL-CDIP images using FAX heuristics (halftone, 1D banding, < 150 DPI effective). Step 2: Augraphy `Faxify` to generate 2,000-4,500 additional synthetic examples. Step 3: Source ≥50 real FAX images for OOD validation (legal/government archives) | 1 day labeling + 0.5 day generation + 1-2 days sourcing real FAX |
| CAP-G04 | No upgrade script exists to map existing 3-class L2 metadata (`born_digital`, `scanner`, `camera_*`) to 7-class schema | Assembly script (`prepare_multitask_datasets.py source`) was designed for 3-class output | Extend `scripts/label_capture_method.py` to write 7-class `capture_method.method` into L2 sidecars; update `L2_TO_SOURCE_CLASS` mapping in prepare script; test with dry-run validation | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| CAP-G05 | ADF heuristic label validation required: do NOT propagate heuristic ADF labels without 100-sample manual spot-check | Risk of systematic label noise that cap model accuracy below 85% target | Manual review of 100 ADF-candidate images by domain expert; measure heuristic precision; reject propagation if precision < 70% | 0.5 days |
| CAP-G06 | Modern CIS scanner gap: RVL-CDIP and NIST datasets are 1990s CCD technology; production documents frequently come from modern CIS flatbeds with different noise profiles | Source dataset temporal gap | Source MIDV-2020 or equivalent CIS scanner dataset; target ≥ 1,500 modern CIS examples within SCANNER_FLATBED class | 1-2 days sourcing |
| CAP-G07 | FAX sim-to-real validation: zero real FAX examples means training/eval F1 is unmeasurable for real-world deployment | FAX class trained entirely on Augraphy synthetic data | Source ≥ 50 real FAX images for OOD sub-source 3e; compare model confidence on real vs synthetic FAX | 1-2 days sourcing |
| CAP-G08 | OOD-Capture set size (600 images) is insufficient for statistically robust per-class evaluation | OOD design preceded full gap analysis | Expand OOD-Capture from 600 to ≥ 900 total: add 3e (real FAX, 50), 3d-ext (border-crop, 50), increase 3a/3b/3c each by ~50 | 0 new acquisition for border-crop; 1-2 days for 3e |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| CAP-G09 | SYNTHETIC class semantic definition needs documentation in schema | Add explicit definition to `config/siglip2_multitask.yaml`: SYNTHETIC = images with no physical paper form (pipeline-generated); BORN_DIGITAL = real document digitized as PDF; clarify eFax boundary |
| CAP-G10 | Per-class accuracy target: overall ≥ 85% may mask low-accuracy minority classes | After training, compute per-class accuracy; set per-class floor ≥ 70% for all 7 classes; report in training evaluation |
| CAP-G11 | Class imbalance mitigation not specified in assembly plan | Apply class-weighted cross-entropy or balanced batch sampler in `config/siglip2_multitask.yaml`; target effective class ratio ≤ 6:1 (richest to rarest class) |

---

## Section 9 — Multi-Model Consensus

**Models**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

**Analyst Pre-Consensus Summary**: The 7-class capture method head has clear blockers in
CAMERA_PROFESSIONAL (no data path) and SCANNER_ADF/FAX (labeling work required). Schema reduction
to 6 classes is the pragmatic resolution. OOD design is conceptually sound but undersized.

### Consensus Results

**Gemini 2.5 Pro (8/10 confidence)**: Rates overall as NEEDS WORK.

- ADF heuristics are technically feasible bootstrap with noisy labels — pragmatic but risks
  learning artifact shortcuts rather than capture method semantics.
- CAMERA_PROFESSIONAL is blocked (near-zero data, marginal user value).
- FAX via Augraphy feasible for training; sim-to-real gap is an accepted risk for rare classes.
- OOD design conceptually strong but 600 images statistically insufficient.
- Missing risks: class imbalance impact on Macro F1, sim-to-real FAX gap, flatbed vs
  born-digital inter-class confusion.
- Recommendation: Merge CAMERA_PROFESSIONAL + CAMERA_SMARTPHONE; defer FAX to 5-class model
  pending synthetic-to-real validation.

**Gemini 3 Pro (9/10 confidence)**: Rates overall as BLOCKED (stronger assessment).

- ADF heuristics not tractable on binarized, low-res RVL-CDIP images where roller artifacts
  are destroyed in preprocessing. Labels will reflect heuristic shortcuts, not capture method.
- CAMERA_PROFESSIONAL is semantically invalid in modern context (iPhone 15 Pro vs DSLR
  distinction negligible for flat document photography).
- FAX validation blocked without real test examples — training F1 is meaningless.
- OOD set has one gap: no cropped vs uncropped scanner variants to test border-artifact dependency.
- Missing risks: eFax semantic ambiguity (born-digital document transmitted over fax),
  SYNTHETIC class overfit to Augraphy generation patterns.
- Recommendation: Collapse to 4-5 classes immediately; require human-in-the-loop for ADF.

### Points of Agreement

1. CAMERA_PROFESSIONAL is blocked — no usable data, marginal downstream value.
2. FAX via Augraphy is trainable but requires real FAX examples for meaningful validation.
3. ADF heuristic labeling requires manual validation before propagation to avoid systematic noise.
4. OOD design is conceptually strong; size needs expansion.
5. Class imbalance is a missing risk that will affect Macro F1 on minority classes.

### Points of Disagreement

- ADF heuristic feasibility: Gemini 2.5 Pro considers it a pragmatic bootstrap; Gemini 3 Pro
  considers the preprocessing destruction of artifacts a fundamental barrier on RVL-CDIP.
  Resolution: Both are partially correct — a subset of RVL-CDIP images will retain artifacts; the
  heuristic should be applied with confidence scoring and the low-confidence fraction excluded.
- Severity: Gemini 2.5 Pro rates Needs Work; Gemini 3 Pro rates Blocked. The difference is
  whether CAMERA_PROFESSIONAL can be resolved by schema change (yes, ≤1 day) or data collection
  (≥2 weeks). Schema change resolves it within the P0 threshold.

### Final Consensus Rating

**NEEDS WORK** — with schema reduction (merge CAMERA_PROFESSIONAL → CAMERA_SMARTPHONE, adopt
6-class schema) as the mandatory P0 action. Under the reduced schema:

- SCANNER_ADF heuristic labeling: 2-3 days (P0)
- FAX Augraphy generation: 1.5 days (P0)
- Upgrade script for L2 metadata: 1 day (P0)

All P0 gaps are resolvable within the 5-day threshold under the reduced schema.

### Scoring Summary

| Component | Weight | Rationale | Raw Score | Weighted |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | Usable images / (7,143 × 7 classes). BORN_DIGITAL 1.0, SCANNER_FLATBED 0.8, SCANNER_ADF 0.0, CAMERA_PROFESSIONAL 0.0, CAMERA_SMARTPHONE 1.0, FAX 0.0, SYNTHETIC 1.0. Sum: 4.8/7 = 68.6% | 68.6 | 24.0 |
| 14-Dimension Coverage | 25% | Average across 8 assessed dimensions: capture_method class coverage (43%), domain (70%), degradation (65%), color_mode (60%), document_age (60%), resolution (70%), script_code (55%), layout_type (70%) | 61.6 | 15.4 |
| Wild Condition Coverage | 20% | (0 full + 4 partial × 0.5) / 6 total conditions = 33.3% | 33.3 | 6.7 |
| OOD Design Quality | 20% | Strong conceptual design (4 sub-sources targeting real failure modes). Deducted: volume too small (600 vs ≥900), missing 3e real FAX, missing border-crop variant | 65.0 | 13.0 |
| **Overall** | 100% | — | — | **59.1** |

**Grade**: ⚠️ Needs Work (59.1 / 100 | P0 blockers present; all P0 resolvable ≤5 days under 6-class schema)

### Top Recommendations (from consensus)

1. Reduce schema from 7 to 6 classes immediately: merge CAMERA_PROFESSIONAL into
   CAMERA_SMARTPHONE, creating a unified CAMERA class. Update `config/siglip2_multitask.yaml`,
   `L2_TO_SOURCE_CLASS`, and all HAR documentation. This converts CAP-G02 from a weeks-long
   data collection effort to a 1-day schema change.

2. Implement `scripts/label_capture_method.py` ADF heuristic with confidence scoring. Apply
   to RVL-CDIP. Set confidence threshold ≥ 0.7 for inclusion. Manually validate 100 samples
   before propagation. Target: 2,500 ADF-labeled images at confidence ≥ 0.7.

3. Generate FAX training data via Augraphy `Faxify` (2,500 images from RVL-CDIP + 500 manually
   labeled). Source ≥ 50 real FAX images for OOD sub-source 3e to enable meaningful validation.

4. Expand OOD-Capture from 600 to ≥ 900 images: add 3e (real FAX, 50), 3d-ext (border-cropped
   scanner variants, 50), increase 3a/3b/3c each by ~66 images.

5. Add class-weighted cross-entropy or balanced batch sampler to training config. Target effective
   class ratio ≤ 6:1. FAX and SCANNER_ADF will be minority classes requiring upweighting.
