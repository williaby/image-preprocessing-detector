# Head Adequacy Review: capture_cls (SIG-G5-1)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: F — Page Attributes
> **Adequacy**: ⏳ TBD

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
| Performance Target | Accuracy ≥ 85% |
| Primary L2 Field | `capture_method.method` (7-class enum) |
| Shared-Data Heads | None (dedicated capture-method dataset) |
| Training Phase | Phase 5 — Page Attributes |

### 7 Canonical Classes

| Class | Description |
| --- | --- |
| BORN_DIGITAL | PDF/vector document rendered directly to image |
| SCANNER_FLATBED | Flatbed scanner acquisition |
| SCANNER_ADF | Automatic Document Feeder scanner |
| CAMERA_PROFESSIONAL | DSLR or mirrorless camera |
| CAMERA_SMARTPHONE | Smartphone or tablet camera |
| FAX | Fax transmission artifact pattern |
| SYNTHETIC | Computationally generated (Augraphy, synth pipelines) |

### L2 capture_method Known Values

| Dataset | L2 Value | Maps To |
| --- | --- | --- |
| rvl_cdip | `"scanner"` (bare, not `scanner_flatbed`) | SCANNER_FLATBED |
| doclaynet | `"born_digital"` | BORN_DIGITAL |
| midv500, realdae, smartdoc-qa, sd7k, wsrd | `"camera_smartphone"` | CAMERA_SMARTPHONE |

Note: `L2_TO_SOURCE_CLASS` mapping in prepare script handles bare `"scanner"` → SCANNER_FLATBED and all known variants.

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `capture_method.method` _(7-class enum string)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact (dataset origin is ground truth for most sources; scanner origin known from dataset metadata)

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for RVL-CDIP and DocLayNet capture method labeling)_

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| RVL-CDIP | 400,000 | ⚠️ Partial (heuristic mapping from `"scanner"`) | ~100% (via L2_TO_SOURCE_CLASS) | _(analysis required)_ | _(check audit)_ | _(analysis required)_ |
| DocLayNet | _(analysis required)_ | ✅ `"born_digital"` | ~100% | _(analysis required)_ | — | _(analysis required)_ |
| PubTabNet | _(analysis required)_ | _(analysis required)_ | — | — | — | — |
| Tobacco800 | _(analysis required)_ | _(analysis required)_ | — | — | — | — |
| NIST SD-2 | _(analysis required)_ | _(analysis required)_ | — | — | — | — |
| MIDV500 | _(analysis required)_ | ✅ `"camera_smartphone"` | ~100% | _(analysis required)_ | — | _(analysis required)_ |
| SmartDoc-QA | _(analysis required)_ | ✅ `"camera_smartphone"` | ~100% | _(analysis required)_ | — | _(analysis required)_ |
| SROIE | _(analysis required)_ | _(analysis required)_ | — | — | — | — |
| RealDAE | _(analysis required)_ | ✅ `"camera_smartphone"` | ~100% | _(analysis required)_ | — | _(analysis required)_ |
| DocSynth300K | _(analysis required)_ | _(analysis required)_ | — | — | — | — |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required — dry-run result: `source` subcommand: 39,893 records — camera:19,893 / born_digital:10K / scanned:10K)_
- **Training target**: 130,000+ images
- **Gap**: _(analysis required — FAX and CAMERA_PROFESSIONAL classes likely severely underrepresented)_

### VLM Validation Sampling Tier

_(analysis required — capture method is primarily heuristic/provenance-based; VLM validation applies to borderline cases where L2 field is missing or ambiguous)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G5-1-01 | RVL-CDIP uses bare `"scanner"` in L2 metadata — not `"scanner_flatbed"` or `"scanner_adf"`. Cannot distinguish flatbed vs ADF from L2 field alone. | MEDIUM — SCANNER_ADF class may be severely underrepresented in training; requires heuristic or manual labeling to split |
| KI-G5-1-02 | FAX class: no known dataset with FAX-labeled documents at scale — class may need synthetic generation via Augraphy fax simulation | HIGH — class accuracy at risk without dedicated FAX training examples |
| KI-G5-1-03 | CAMERA_PROFESSIONAL class: limited dataset sources; distinction from CAMERA_SMARTPHONE is subtle at high resolution | MEDIUM — may require dedicated photography session or licensed stock images |
| KI-G5-1-04 | `source` subcommand dry-run achieved 39,893 records but is well below 130K target — significant gap in camera and born_digital classes | HIGH — additional dataset sourcing required |

### Remediation Path

_(analysis required — enumerate steps: 1) quantify per-class gap from 39,893 baseline, 2) source FAX samples via Augraphy simulation, 3) determine ADF split strategy for RVL-CDIP, 4) identify CAMERA_PROFESSIONAL sources)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 130,000+ images |
| Assembly Status | ⏳ Not started (source subcommand dry-run: 39,893 records — camera:19,893 / born_digital:10K / scanned:10K) |
| Distribution Gaps | FAX: ~0 images (no source identified); SCANNER_ADF: ~0 labeled (mixed with SCANNER_FLATBED in RVL-CDIP); CAMERA_PROFESSIONAL: unknown |
| Source Mapping | L2_TO_SOURCE_CLASS handles known variants; bare `"scanner"` → SCANNER_FLATBED confirmed working |
| Assembly Script | `scripts/prepare_multitask_datasets.py source` |

### Class Distribution Targets

| Class | Target Images | Current Estimate | Risk |
| --- | --- | --- | --- |
| BORN_DIGITAL | _(analysis required)_ | ~10K (dry-run) | LOW — DocLayNet well-populated |
| SCANNER_FLATBED | _(analysis required)_ | ~10K (dry-run, all RVL-CDIP labeled as flatbed) | MEDIUM — ADF not separated |
| SCANNER_ADF | _(analysis required)_ | ~0 (not distinguishable from L2 alone) | HIGH |
| CAMERA_PROFESSIONAL | _(analysis required)_ | ~0 (no identified source) | HIGH |
| CAMERA_SMARTPHONE | _(analysis required)_ | ~19,893 (dry-run) | MEDIUM — target may be met |
| FAX | _(analysis required)_ | ~0 (no source identified) | HIGH |
| SYNTHETIC | _(analysis required)_ | _(analysis required)_ | MEDIUM |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL — this IS the label; all 7 classes must be represented | All 7 classes with ≥ 500 samples minimum | 3 classes identified in dry-run | TBD |
| domain | `domain.level1` | HIGH — business docs vs scientific vs handwritten have different capture distributions | ≥ 5 domains per capture class | unknown | TBD |
| degradation | `quality.degradations` | HIGH — scanner artifacts, moiré, ADF curl are capture-specific degradations | Capture-specific degradations represented per class | unknown | TBD |
| color_mode | `image_properties.color_mode` | HIGH — FAX and older scanners produce binarized output; camera produces color | All 3 modes (color/grayscale/binarized) per relevant class | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM — aged documents disproportionately scanner-acquired | ≥ 2 age classes | unknown | TBD |
| resolution | `resolution.category` | MEDIUM — scanner DPI varies widely; camera resolution differs from scanner | ≥ 3 resolution tiers per capture class | unknown | TBD |
| script_code | `language.script_code` | MEDIUM — non-Latin documents may be captured by different methods | ≥ 3 script families | unknown | TBD |
| layout_type | `structure.layout_type` | LOW — layout type should not drive capture method prediction | ≥ 3 types | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Screen recapture (camera photographing monitor — moiré + RGB aliasing) | `capture_method.method` = camera_smartphone | ⚠️ | OOD-Capture 3a tests this; NOT in training — unique distortion type not represented in any current source |
| ADF scanner with curl artifacts (page_curl warping from ADF feed) | `capture_method.method` = scanner_adf | ⚠️ | OOD-Capture 3b; ADF class itself not in training — compounded risk |
| 4th-generation photocopies (Augraphy-simulated multi-pass degradation) | `image_properties.document_age` = aged | ⏳ | OOD-Capture 3c; copier artifacts not common in training datasets |
| High-speed production scanner (motion artifacts at speed) | `capture_method.method` = scanner_flatbed | ⏳ | OOD-Capture 3d; production scanner characteristics differ from desktop flatbed |
| FAX artifacts (halftone + compression + transmission noise combined) | `quality.degradations` | ⚠️ | FAX class has no training examples — model will fail on FAX documents without sourcing |
| Dual-camera smartphone (depth blur + HDR processing artifacts) | `capture_method.method` = camera_smartphone | ⏳ | Modern smartphones produce processing-heavy output not in SmartDoc-QA era training |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Capture (Phase 3, P0, 600 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 3a. Screen recaptures | 200 | Internal photography of monitor displaying documents (NOT from any training dataset) | capture_method=camera_smartphone, warping_type=perspective (from viewing angle), moiré presence flag | siglip2 | Unique distortion: moiré patterns + RGB subpixel aliasing from screen. Cross-categorizes with OOD-Mixed. Must be from sources with no training analog. |
| 3b. ADF scanner with curl artifacts | 150 | Internal ADF scans with deliberate page curl | capture_method=scanner_adf, warping_type=page_curl, warping_severity | siglip2 | ADF-specific artifacts not well-represented in training (RVL-CDIP does not distinguish ADF vs flatbed). Cross-categorizes with OOD-Degradation for warping_reg. |
| 3c. 4th-generation photocopies | 150 | Augraphy simulation (4 passes of copy degradation) on internal document photos | capture_method=scanner_flatbed, document_age=aged, degradation_count ≥ 4 | siglip2 | Simulates multi-generational photocopy degradation. Augraphy parameters: `PaperFactory` + `DirtyRollers` + `Letterpress` chained 4× |
| 3d. High-speed production scanner | 100 | Internal production scanner acquisition | capture_method=scanner_flatbed, scanner_speed=high | siglip2 | Production-grade scanner characteristics (motion blur at speed, edge distortion). Distinct from desktop flatbed in training. |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 3, P0)

### OOD Leakage Risk

RVL-CDIP is a training source. OOD-Capture must use internally acquired or independently photographed/scanned documents with no overlap with any training dataset. Screen recaptures (3a), ADF scans (3b), Augraphy photocopies (3c), and production scanner outputs (3d) all represent acquisition methods not present in training datasets — no dedup required against training splits, but images must be confirmed as not previously digitized into any known dataset.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G5-3 (warping_reg) | OOD-Capture sub-source 3b (ADF curl) is shared — same 150 images require both capture_method and warping_severity labels | Both heads must label the shared OOD images consistently. `capture_method=scanner_adf` AND `warping_severity` must be populated for the same image set. Labeling must be coordinated — a single annotation pass should populate both L2 fields. |
| SIG-G5-5 (resolution_quality_reg) | Born-digital capture at low DPI creates interaction — capture_cls labels the method; resolution_quality_reg scores the visual quality | A document labeled BORN_DIGITAL by capture_cls may receive high resolution_quality despite low DPI (large font paradox). Downstream routing must account for this interaction: born-digital low-DPI does not require upscaling in the same way scanned low-DPI does. |
| SIG-G3-1 (orientation_cls) | Screen recaptures (OOD-3a) create unusual orientations from viewing angle | No shared training data, but OOD-3a images may also stress orientation heads. Labels should include orientation_class for cross-head OOD analysis. |

### Split Leakage Risk

**Level**: MEDIUM

RVL-CDIP (400K images) is shared across capture_cls training and other training datasets (skew natural scans, orientation base images). Global split registry required to ensure images in capture_cls training set are not in test splits of other datasets that draw from RVL-CDIP. DocLayNet is similarly shared.

### Label Convention

7 canonical classes per L2 schema. Bare `"scanner"` from rvl_cdip is mapped to SCANNER_FLATBED (not SCANNER_ADF) by default. Any future labeling effort that distinguishes ADF from flatbed within RVL-CDIP must update L2 sidecars to `"scanner_adf"` or `"scanner_flatbed"` explicitly. The `source` subcommand dry-run result (39,893 records with confirmed class mapping) validates the L2_TO_SOURCE_CLASS mapping is working correctly.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G5-1-G01 | — | FAX class: ~0 training examples identified in any source dataset | No FAX-labeled dataset available; FAX is rare in modern document collections | Generate FAX-simulated images using Augraphy `Faxify` augmentation on RVL-CDIP or DocLayNet images; target 3,000–5,000 samples | 1 day |
| G5-1-G02 | — | SCANNER_ADF class: not separable from SCANNER_FLATBED in RVL-CDIP L2 metadata (both use bare `"scanner"`) | L2 metadata does not capture scanner subtype | Design heuristic (page curl presence, edge curvature) or manual annotation to split RVL-CDIP scanner images into flatbed vs ADF; or source new ADF dataset | 2-3 days |
| G5-1-G03 | — | CAMERA_PROFESSIONAL class: no identified large-scale source dataset | Professional camera document photography not common in public datasets | Source licensed professional photography datasets or conduct internal photography session; target 3,000–5,000 samples | 1-2 days sourcing |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G5-1-G04 | RVL-CDIP capture_method labeling needs validation beyond heuristic mapping | Bare `"scanner"` → SCANNER_FLATBED assumption not verified on sample of images | Manual spot-check of 100 RVL-CDIP images to validate flatbed assignment; check for ADF artifacts (page curl, edge distortion) | 0.5 days |
| G5-1-G05 | Total assembly gap: 39,893 (dry-run) vs 130K target — 90K+ additional images needed | Insufficient source datasets identified so far | Audit remaining candidate datasets (PubTabNet, Tobacco800, NIST SD-2, DocSynth300K) for capture_method field population | 1 day |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G5-1-G06 | SYNTHETIC class training coverage not assessed — DocSynth300K and synth-multiscript-v3 could contribute | Audit L2 metadata for SYNTHETIC capture_method field population across synthetic generation datasets |
| G5-1-G07 | Per-class accuracy target (≥ 85% overall) may mask low-accuracy minority classes (FAX, ADF) | After training, compute per-class accuracy; set per-class floor of ≥ 70% for all 7 classes |

---

## Section 9 — Multi-Model Consensus

**Status**: ⏳ Pending execution

**Adequacy Rating (pre-consensus)**: ⏳ TBD (analysis required)

**Analyst Summary**: _(To be written after Sections 2–8 analysis is complete)_

**Consensus Prompt**: _(To be written after Section 8 gap registry is complete)_

**Models**: google/gemini-2.5-pro, google/gemini-3-pro-preview, openai/gpt-5.2,
deepseek/deepseek-r1-0528, x-ai/grok-4 (all neutral)

**Consensus Summary**: _(Pending)_

**Final Rating**: _(Pending)_

**Top Recommendations**: _(Pending)_

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | TBD | TBD |
| 14-Dimension Coverage | 25% | TBD | TBD |
| Wild Condition Coverage | 20% | TBD | TBD |
| OOD Design Quality | 20% | TBD | TBD |
| **Overall** | 100% | — | TBD |

**Grade**: ⏳ TBD
