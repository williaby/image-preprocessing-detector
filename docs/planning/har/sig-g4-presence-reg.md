# Head Adequacy Review: presence_reg (SIG-G4-4)

> **Status**: Reviewed — Blocked
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: E — Handwriting
> **Adequacy**: Blocked

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G4-4 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | presence_reg (also written as handwriting_presence_score) |
| Task Type | Regression — 0-1 continuous (area ratio: fraction of page that is handwritten) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P1 |
| Performance Target | Pearson r ≥ 0.80 on OOD holdout (HierText gold standard) |
| Primary L2 Field | `handwriting_assessment.presence_score` (float 0-1) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5); SIG-G4-1 (presence_cls) is the discretized version of this head's output |
| Training Phase | Phase 4 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.presence_score` (float 0.0–1.0; area ratio of
handwriting pixels per page)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact from HierText pixel-level polygons; tier_2_heuristic from
corpus-level midpoint mapping (IAM→0.95, DocLayNet→0.0); tier_1_annotation from bounding-box
proxy after bias correction (COCO-Text); VLM-estimated for Muharaf/PUCIT-OHUL.

### Label Derivation Hierarchy

| Method | Datasets | Precision | Confidence Tier |
| --- | --- | --- | --- |
| Pixel-level polygon area ratio (gold standard) | HierText (8,281 images) | High (~1% granularity) | tier_0_exact |
| Bounding-box area ratio (proxy — overestimates) | COCO-Text (~63K) | Medium (~5-15% upward bias) | tier_1_annotation (after correction) |
| Corpus-level midpoint mapping (fixed value) | IAM→0.95, NIST-SD2→1.0, DocLayNet→0.0 | Low (no within-class variance) | tier_2_heuristic |
| VLM-estimated area ratio | Muharaf (~20K), PUCIT-OHUL (~7K) | Medium (±0.10) | tier_2_heuristic |

**Critical Note on Midpoint Mapping**: Assigning a fixed value (e.g., IAM→0.95) does not
yield regression labels — it yields quantized targets clustered at discrete anchors. When the
Gaussian NLL loss trains against sigma_sq on these targets, it will drive sigma_sq toward
zero to match the hard quantization points, defeating the purpose of uncertainty modeling.
Midpoint-mapped datasets are not true regression training data; they are classification data
forced into a continuous label format.

### Candidate Source Datasets

| Dataset | Total Images | Pixel-Ratio Viable | Expected Score Range | Score Distribution | Usable |
| --- | --- | --- | --- | --- | --- |
| HierText | 8,281 | Yes — polygon areas available | 0.0–0.50 (scene text, partial HW) | Non-bimodal; mixed scene content provides mid-range coverage | Yes — gold standard |
| COCO-Text | 63,686 | Partial — bounding boxes only | 0.0–0.30 (mostly scene text with minimal HW) | Skewed low; most pages have little handwriting | Partial — after bias correction |
| IAM | ~13,000 pages | No — corpus-level only | Fixed: ~0.95 (pure handwriting pages) | Spike at 0.95 — not true regression | Restricted — DOMINANT anchor only |
| Muharaf | ~20,000 pages | No — VLM required | Fixed: ~0.90–1.0 (full Arabic HW pages) | Spike at ~0.95 — not true regression | Restricted — DOMINANT anchor only |
| PUCIT-OHUL | ~7,000 pages | No — VLM required | Fixed: ~0.85–1.0 (Urdu HW pages) | Spike near 1.0 — not true regression | Restricted — DOMINANT anchor only |
| NIST-SD2 | ~5,590 pages | No — corpus-level only | Fixed: ~1.0 (all handwritten forms) | Spike at 1.0 — not true regression | Restricted — DOMINANT anchor only |
| FUNSD | ~200 forms | Partial — form annotations | 0.05–0.40 (fill-in area vs. printed form) | Mid-range potential; too small for meaningful count | Minor contributor |
| DocLayNet | 81,000 pages | No — corpus-level only | Fixed: 0.0 (born-digital, no HW) | Spike at 0.0 — not true regression | Yes — NONE anchor (capped) |
| TableBank | ~260K pages | No — corpus-level only | Fixed: 0.0 (born-digital) | Spike at 0.0 — not true regression | Yes — NONE anchor (capped) |
| RVL-CDIP | ~16,000 (sample) | No — corpus-level only | 0.0–0.05 (mostly printed, some typed forms) | Near 0.0; marginal HW possible | Minor contributor |

### Distribution Concern: Structural Bimodality

The training pool will produce a heavily bimodal distribution:

- **Spike at 0.0**: DocLayNet, TableBank, RVL-CDIP — capped at ~12,000 examples but trivially
  abundant
- **Spike at ~0.95**: IAM, NIST-SD2, Muharaf, PUCIT-OHUL — ~50,000 available after GCS access;
  capped at ~20,000 for balance
- **Mid-range (0.05–0.85)**: HierText (~8K, partial coverage), COCO-Text (proxy only), FUNSD
  (~200). Together: well under 10,000 images with any mid-range signal, and most of that is in
  the 0.0–0.20 range from scene text.
- **Score range 0.20–0.70**: Estimated < 3,000 images from all sources combined. No large-scale
  natural source for this critical regression interval exists in the current dataset inventory.

### Calibration Concern: Pixel Ratio vs. Perceptual Presence

Pixel-ratio of annotation area does not equal perceptual handwriting presence. Examples:

- A single red-ink signature on a dense printed page → pixel ratio ~0.01–0.02, but perceptually
  the document is "signed" and requires handwriting-aware processing
- A faint pencil note in white space → pixel ratio ~0.04, but handwriting clearly present
- Large block-letter handwriting spanning half the page → pixel ratio ~0.35, which accurately
  reflects scale

This construct validity gap is real but accepted for a document processing pipeline whose
downstream purpose is routing (not human perception judgement). The routing logic cares about
"how much of the page is handwritten" as a structural proxy, not a quality judgement.
Consensus: treat as P2, not P0.

### Usable Pool Summary

| Score Range | Primary Source | Estimated Count | Quality |
| --- | --- | --- | --- |
| 0.0 (exact) | DocLayNet, TableBank, RVL-CDIP | 350,000+ available; cap at ~12,000 | tier_2_heuristic |
| 0.01–0.19 | HierText (polygon), COCO-Text (proxy) | ~5,000–8,000 | tier_0 to tier_1 |
| 0.20–0.69 | HierText (sparse), FUNSD | <3,000 | tier_0 to tier_1 |
| 0.70–0.89 | VLM-labeled Muharaf/PUCIT-OHUL outliers | ~1,000–2,000 | tier_2_heuristic |
| 0.90–1.00 | IAM, NIST-SD2, Muharaf, PUCIT-OHUL (corpus) | ~50,000 available; cap at ~20,000 | tier_2_heuristic |

- **Total true regression-quality labels** (tier_0 or tier_1): ~8,000–11,000 (HierText + COCO-Text corrected)
- **Training target**: 60,000 images (shared with all G4 heads)
- **Gap to target**: ~49,000 images — the remainder will carry tier_2_heuristic labels that
  produce quantized (not continuous) regression targets
- **Mid-range gap (0.20–0.70)**: approximately 57,000 images short of any reasonable density

### VLM Validation Sampling Tier

- Score range 0.0 and ~1.0 (corpus-level): Tier 2 sampling only (validate 2% spot-check)
- Score range 0.05–0.50 (HierText polygon, COCO-Text proxy): Tier 1 targeted (validate 15%
  of mid-range images; polygon-derived scores that fall near 0.10 or 0.50 benefit from
  VLM confirmation)
- VLM area estimation for Muharaf/PUCIT-OHUL mid-range outliers: Tier 1 full pass

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| HW-PRES-REG-D01 | All G4 datasets | `handwriting_assessment.presence_score` | L2 field unpopulated for all datasets | Open — blocks all assembly |
| HW-PRES-REG-D02 | HierText | `handwriting_assessment.presence_score` | Pixel-level polygon area ratio not yet computed | Open |
| HW-PRES-REG-D03 | COCO-Text | `handwriting_assessment.presence_score` | Bounding-box area proxy overestimates presence; bias correction factor not quantified | Open |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-04-A | Training distribution is structurally bimodal (0.0 from negatives, ~0.95 from HW corpora) — mid-range (0.20–0.70) severely underrepresented | CRITICAL — regression model will learn a near-step function; mid-range predictions will be interpolated with no training signal |
| KI-G4-04-B | Corpus-level midpoint mapping (IAM→0.95, DocLayNet→0.0) produces quantized targets, not continuous regression labels | HIGH — Gaussian NLL head will drive sigma_sq→0 at quantized points, producing overconfident predictions |
| KI-G4-04-C | Pearson r ≥ 0.80 is achievable spuriously on a bimodal test set without any mid-range precision — metric is misleading | HIGH — Pearson r at 0.80 on a bimodal test does not indicate useful regression capability |
| KI-G4-04-D | COCO-Text bounding box area ratio overestimates handwriting pixels (box includes background) by ~5-15% | MEDIUM — systematic upward bias; correction factor requires empirical measurement against HierText ground truth |
| KI-G4-04-E | Gaussian NLL head requires per-sample sigma_sq targets — no principled derivation path for sigma_sq from heuristic labels | MEDIUM — tier assignment (tier_0→sigma=0.01, tier_2→sigma=0.15) is an engineering approximation, not ground truth uncertainty |

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 60,000 images (shared with all G4 heads) |
| Assembly Status | Blocked — L2 field unpopulated; pixel-ratio script not implemented; assembly pipeline subcommand not implemented |
| Current Count | 0 images with valid `handwriting_assessment.presence_score` labels |
| Gold Standard | HierText — 8,281 images with pixel-level handwriting polygon annotations (only source of true continuous labels) |
| Score Derivation | presence_score = pixel-ratio of handwriting per page (HierText); midpoint mapping for corpus datasets; bounding-box proxy for COCO-Text after bias correction |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Score Distribution Requirements

| Score Range | Label Method | Target Coverage | Primary Source | Risk |
| --- | --- | --- | --- | --- |
| 0.00 (exact) | Corpus-level (all_printed) | ~15–20% (capped) | DocLayNet, TableBank | LOW — vastly over-available; cap required |
| 0.01–0.19 | Pixel-ratio (HierText) + BB proxy (COCO-Text) | ≥ 15% | HierText, COCO-Text | HIGH — estimated ~8K available; only partially real mid-range |
| 0.20–0.69 | Pixel-ratio (HierText sparse) | ≥ 25% | HierText, FUNSD | CRITICAL — <3K available; no large-scale source identified |
| 0.70–0.89 | VLM-estimated outliers | ≥ 10% | Muharaf/PUCIT-OHUL outliers | HIGH — VLM labeling required; coverage uncertain |
| 0.90–1.00 | Corpus-level (all_handwritten) | ~20–25% (capped) | IAM, NIST-SD2, Muharaf | LOW — ~50K available; cap required |

**Active Blockers**:

- `handwriting_assessment.presence_score` L2 field unpopulated for all datasets (P0)
- HierText pixel-level area ratio computation script not created (P0)
- handwriting subcommand of `prepare_multitask_datasets.py` not implemented (P0)
- Score range 0.20–0.70 has no large-scale natural source (P0)
- Uncertainty (sigma_sq) assignment strategy per confidence tier not defined (P1)

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: Estimated 18/100 (pre-assembly projection)

The dominant failure is the score distribution dimension: the regression target is not
uniformly or even reasonably distributed across 0–1. Secondary failures are script diversity
(only Latin/Arabic/Urdu), capture method coverage, and near-total absence of mid-range mixed
documents that would train nuanced intermediate predictions.

| Dimension | L2 Field | Relevance | Target | Current Estimate | Score |
| --- | --- | --- | --- | --- | --- |
| score_distribution | `handwriting_assessment.presence_score` | CRITICAL | Reasonably uniform density 0–1; critical mass in 0.20–0.70 | Bimodal: spike at 0.0, spike at ~0.95; 0.20–0.70 near-empty | 5/100 |
| mixed_content | `handwriting_assessment.is_mixed` | CRITICAL | ≥ 30% mixed pages (printed + handwriting in varying ratios) | Near zero — mixed pages with mid-range scores not available at scale | 5/100 |
| script_diversity | `language.script_code` | HIGH | ≥ 4 scripts (LATN, ARAB, DEVA, HANS) | LATN (IAM, HierText, COCO-Text), ARAB (Muharaf), URDU (PUCIT-OHUL); CJK/Deva absent | 25/100 |
| capture_method | `capture_method.method` | HIGH | ≥ 3 methods (born_digital, scanner, camera) | Scanner (IAM, NIST-SD2), born_digital (DocLayNet negatives), camera (COCO-Text, HierText); reasonable coverage at extremes | 35/100 |
| annotation_method | _(label confidence tier)_ | HIGH | Mix of tier_0, tier_1, tier_2 in known proportions | All tier_2_heuristic except HierText (tier_0); quantized targets dominate | 20/100 |
| document_age | `image_properties.document_age` | MEDIUM | All 3 ages (modern, aged, historical) | Mostly modern; aged/historical virtually absent | 15/100 |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes (color, grayscale) | Grayscale dominant (IAM, NIST-SD2); some color in scene text datasets | 40/100 |
| degradation | `quality.degradations` | MEDIUM | ≥ 3 degradation types | IAM/NIST-SD2 are clean scans; degraded HW scarce | 20/100 |
| domain | `domain.level1` | MEDIUM | ≥ 5 domains | Academic (IAM), financial (NIST-SD2), natural scene (HierText); limited spread | 30/100 |
| resolution | `resolution.category` | MEDIUM | ≥ 3 tiers | Scanner sources ~300 DPI; HierText variable; limited range | 35/100 |
| layout_type | `structure.layout_type` | MEDIUM | Pure HW, mixed, born-digital structured | Pure manuscript (DOMINANT); born-digital structured (NONE); mixed layouts absent | 20/100 |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | Letters/notes (IAM), forms (NIST-SD2), scene images (HierText) | 25/100 |
| handwriting_style | `handwriting_assessment.content_type` | LOW | Multiple styles (cursive, print, mixed) | Cursive/print from IAM; limited variation | 30/100 |
| background_complexity | `image_properties.background` | LOW | Plain and complex | Plain dominant; complex backgrounds in scene text only | 30/100 |

**Key Dimension Findings**:

- **Score distribution is the dominant failure**. A regression head trained on a bimodal
  distribution will learn a near-step function — predicting 0.0 or ~0.95 with no nuanced
  intermediate capability. Without mid-range training examples, the Pearson r metric is
  misleading (it can hit 0.80 spuriously on a bimodal test set without any useful mid-range
  regression).
- **Mixed content deficit directly causes the score distribution gap**. Documents with
  partial handwriting (exam sheets, annotated printouts, signed forms) are the natural
  source of mid-range scores. None exist at scale in the current dataset inventory.
- **Script diversity is structurally limited** to Latin/Arabic/Urdu. The OOD set (KHATT,
  CASIA-HWDB, IIIT-INDIC) will encounter scripts entirely absent from training.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 15/100 (pre-assembly projection)

| Wild Condition | L2 Field Evidence | Status | Severity |
| --- | --- | --- | --- |
| Microscopic handwriting annotations (single signature, corner page number) — presence ~0.01–0.05 | `handwriting_assessment.presence_score` | Absent | CRITICAL — SPARSERANGE lower bound; no dedicated source |
| Exam answer sheets: ~50% HW / 50% printed grid — presence ~0.40–0.60 | `handwriting_assessment.is_mixed` | Absent | CRITICAL — defining example of mid-range score; no dataset provides this |
| Signed forms (printed body + handwritten signature block) — presence ~0.02–0.08 | `handwriting_assessment.is_mixed` | Absent | CRITICAL — common in real document processing; not in any training source |
| Historical documents with heavy marginalia — presence ~0.35–0.65 | `image_properties.document_age` = historical | Absent | HIGH — mid-range; historical HW absent from all training sources |
| Calligraphic typed Arabic (Naskh typeface resembles HW visually) — false positive risk | `language.script_code` = Arab | Absent | HIGH — model may predict presence_score > 0.0 for printed Arabic with cursive fonts |
| Camera-captured notebook pages: HW on printed grid background — presence ~0.70–0.85 | `capture_method.method` = camera | Partial (HierText scene text) | HIGH — needs HW-specific camera examples |
| Multi-page document: cover 0.0, body pages 1.0 — per-page vs. doc-level ambiguity | _(pipeline design)_ | Unresolved | HIGH — pipeline must specify whether score is per-page or per-document |
| Faint pencil annotations on dense printed text — presence ~0.03–0.10 | `quality.degradations` | Absent | MEDIUM — pencil HW poorly detected by pixel-ratio from binary annotations |
| Born-digital document with embedded HW image scan — presence 0.0 by design | `capture_method.method` = born_digital | Absent | MEDIUM — presence_score should be 0.0 (no actual HW pixel content) |
| CJK handwritten documents (CASIA-HWDB style) — presence ~0.90–1.0 | `language.script_code` = Hans | OOD only | MEDIUM — absent from training; tested in OOD-Handwriting 5b |

**Key Finding**: The four most critical wild conditions (microscopic annotations, exam sheets,
signed forms, and historical marginalia) all define the mid-range of the regression scale
(0.02–0.65). Their absence is not a diversity gap in the traditional sense — they are the
score range the regression head needs to learn, and that score range is entirely absent from
training data. This is equivalent to the MARGINAL/PARTIAL/SUBSTANTIAL class gap in SIG-G4-1,
expressed in continuous terms.

**Wild Condition Tally**: 0 fully covered, 1 partial (camera HW via HierText scene text),
9 absent.

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | `handwriting_presence_score` (pixel-level preferred) ≈ 0.70–1.0, `script=Arab`, `text_direction=rtl` | SigLIP 2 | Full-page Arabic cursive; presence_score at DOMINANT end; pixel-level polygon labels required for SRCC computation |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc) | `handwriting_presence_score` ≈ 0.70–1.0, `script=Hans/Hant` | SigLIP 2 | 2–4 week access request for CASIA; CJK absent from training |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | `handwriting_presence_score` ≈ 0.70–1.0, `script=Deva` | SigLIP 2 | Tests regression on Devanagari full-page handwriting; absent from training |
| 5d. Specialized content handwriting | 50 | Mathematical/engineering notebooks, public domain archives | `handwriting_presence_score` ≈ 0.30–0.80, `content_type=specialized` | SigLIP 2 | Mixed math notation + printed content; potential mid-range OOD examples |

### Regression-Specific OOD Assessment

The OOD-Handwriting set is heavily weighted toward DOMINANT presence (0.70–1.00). For
presence_reg specifically, this means:

- **OOD Pearson r is effectively an endpoint test**. If the model predicts correctly at
  ~0.90–1.0 for OOD samples, it achieves high Pearson r without demonstrating any mid-range
  capability. This is the same metric misinterpretation risk that applies to the training set.
- **Sub-source 5d (50 images with mixed math content)** is the only OOD sub-source with
  potential mid-range score representation. 50 images is insufficient for a statistically
  meaningful SRCC/Pearson r estimate at that score range.
- **Pixel-level polygon labels are required** for KHATT and CASIA-HWDB OOD images if Pearson r
  against gold standard is the evaluation target. Bounding-box labels will produce systematic
  overestimate bias in the OOD labels themselves, corrupting the evaluation.

### OOD Acquisition Status

**Status**: Not started (Phase 5, P0)

### Missing OOD Sub-sources for Regression Evaluation

- Mid-range presence score (0.10–0.60) OOD examples are entirely absent. The current OOD
  design cannot evaluate the regression head's mid-range precision — only its DOMINANT endpoint.
- Consider augmenting with 50–100 annotated form fill-in examples (FUNSD-style) if the goal
  is genuine Pearson r measurement rather than endpoint Pearson r.

### OOD Leakage Risk

**Level**: MEDIUM — Same as all G4 heads. Additional regression-specific risk: if OOD
presence_score labels are computed from bounding boxes (not pixel level), the evaluation
Pearson r will be biased upward for the OOD set, giving a falsely optimistic result. Pixel-
level polygon annotation for OOD labels is strongly recommended.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-1 (presence_cls) | presence_cls is the discretized version of presence_reg output | Class boundaries must align: NONE 0.0–0.01, MARGINAL 0.01–0.10, PARTIAL 0.10–0.50, SUBSTANTIAL 0.50–0.90, DOMINANT 0.90–1.00. The same image must have logically consistent presence_score and presence class. Derived from same pixel-ratio computation. |
| SIG-G4-5 (legibility_reg) | Shares Gaussian NLL head architecture; trained on same dataset | Calibration must be done independently per head. The sigma_sq uncertainty outputs are not semantically comparable between presence_reg and legibility_reg. |
| SIG-G4-2 (legibility_cls) | Legibility is meaningless when presence_score = 0.0 | Images with presence_score = 0.0 must have legibility set to N_A; enforced by label dependency rule during assembly. |
| SIG-G4-3 (content_type_cls) | content_type is not applicable when presence_score = 0.0 | Same dependency as legibility — presence_score is the gate for all other G4 secondary heads. |

### Split Leakage Risk

**Level**: MEDIUM — All five G4 heads share the same training dataset. Global split registry
(SHA256-keyed) required. Additional regression-specific risk: HierText serves as the primary
gold standard for Pearson r evaluation. If HierText images appear in both training and test
splits, the Pearson r measurement will be overestimated. HierText test split must be
registered as held-out before any training manifests are assembled.

### Label Convention

`presence_score` is a float in [0.0, 1.0] representing the fraction of the page image area
covered by handwriting pixels. Convention:

- 0.0: No handwriting pixels (printed, born-digital, blank) — unambiguous; does NOT mean
  "handwriting is so bad it scores zero"
- 1.0: Entire page area is handwriting pixels (pure manuscript page)
- Intermediate values: computed from polygon area for HierText (gold standard); midpoint
  mapping for corpus-level datasets (IAM→0.95, DocLayNet→0.0)
- COCO-Text bounding box proxy is a known overestimate — must document systematic bias in
  evaluation reporting

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-PRES-REG-G01 | `handwriting_assessment.presence_score` L2 field unpopulated for all datasets — no label source exists | Labels were never derived during dataset processing | Run pixel-ratio computation script on HierText; run VLM estimation on Muharaf/PUCIT-OHUL; derive heuristic labels for remaining sources | 2–3 days |
| HW-PRES-REG-G02 | HierText pixel-level area ratio computation script not yet created | Gold standard label extraction not implemented | Write script to compute handwriting pixel area ratio from HierText polygon annotations; validate against a 50-image manual spot-check | 1 day |
| HW-PRES-REG-G03 | Score range 0.20–0.70 severely underrepresented — bimodal distribution at 0.0 and ~0.95 with <3,000 mid-range examples | No large-scale dataset provides mixed printed+handwriting pages at moderate density | Audit HierText mid-range yield; evaluate FUNSD/COCO-Text mid-range potential; if insufficient, implement synthetic mixed-document composition (overlay HW crops onto printed pages at varying coverage %) | 2–4 days (analysis) + TBD (synthesis if needed) |
| HW-PRES-REG-G04 | handwriting subcommand of `prepare_multitask_datasets.py` not implemented | Phase 3 dataset prep deprioritized; other subcommands implemented first | Implement following the established subcommand pattern; enforce NONE class cap (12,000), DOMINANT cap (20,000), mid-range over-sampling | 2 days (shared with all G4 heads) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-PRES-REG-G05 | Pearson r ≥ 0.80 target is misleading on a bimodal training and test distribution — endpoint accuracy produces high Pearson r without mid-range capability | Metric selection made before distribution analysis; bimodal data inflates Pearson r spuriously | Add MAE (Mean Absolute Error) and SRCC (Spearman Rank Correlation Coefficient) as co-primary metrics; weight evaluation toward mid-range samples (0.10–0.80) for a meaningful capability test | 0.5 days — governance decision |
| HW-PRES-REG-G06 | sigma_sq assignment from confidence tier is an engineering approximation — tier_0→0.01, tier_1→0.05, tier_2→0.15 — not derived from true label variance | Gaussian NLL training requires per-sample uncertainty ground truth; none available from any source | Define and document tier-based sigma_sq mapping in assembly spec; note in model card that sigma_sq encodes label source type, not epistemic uncertainty | 0.5 days |
| HW-PRES-REG-G07 | COCO-Text bounding box area ratio overestimates handwriting coverage — systematic upward bias uncorrected | Bounding boxes include background whitespace; no correction factor implemented | Compute correction factor from HierText images (where both pixel-level and bounding-box annotations exist); apply factor to COCO-Text labels before training | 1 day |
| HW-PRES-REG-G08 | HierText test split not explicitly held out for regression Pearson r evaluation — split registry not yet implemented | Global split registry not yet deployed | Register HierText splits in global split registry before any assembly begins; hold out test split for evaluation-only | 0.5 days |
| HW-PRES-REG-G09 | False precision risk: midpoint-mapped labels (IAM→0.95, DocLayNet→0.0) produce quantized regression targets, not true continuous labels — Gaussian NLL head will overfit to quantization | No continuous label generation path for pure-HW and pure-printed corpus datasets | Document this as a known limitation in model card; consider assigning uniform distribution sigma_sq=0.05 for tier_2 sources to prevent overconfident predictions at quantized anchors | 0.5 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| HW-PRES-REG-G10 | Construct validity study: pixel-ratio vs. perceptual presence not formally validated | Design a 50-image pairwise human annotation study to measure correlation between pixel-ratio scores and human "presence strength" ratings |
| HW-PRES-REG-G11 | OOD mid-range coverage insufficient — 50 images from sub-source 5d cannot support meaningful SRCC in 0.10–0.60 range | Add 50–100 annotated form fill-in examples (FUNSD-style signed forms) to OOD-Handwriting |
| HW-PRES-REG-G12 | Per-page vs. per-document aggregation strategy undefined for multi-page inputs | Define pipeline specification: presence_score is computed per-page and reported per-page; document-level aggregation is a downstream consumer responsibility |
| HW-PRES-REG-G13 | Gaussian NLL post-training calibration not planned | Add calibration step post-training: measure actual vs. predicted uncertainty on validation set; apply temperature scaling if sigma_sq is systematically overconfident at quantized anchors |

### Deprioritization Recommendation (Consensus-Derived)

Both external models (Gemini 2.5 Pro and Gemini 3 Pro Preview) independently recommended
considering an alternative to training a standalone regression head:

**Option A — Deprioritize and derive from SIG-G4-1 logits**: Compute
`presence_score = P(NONE)*0.005 + P(MARGINAL)*0.055 + P(PARTIAL)*0.30 + P(SUBSTANTIAL)*0.70 + P(DOMINANT)*0.95`
as a weighted sum of classification probabilities. This reuses SIG-G4-1 training effort and
eliminates the regression P0 blockers. Drawback: no uncertainty output (no sigma_sq).

**Option B — Proceed as planned but add MAE/SRCC metrics and mid-range data sourcing**:
Accept the bimodal data constraint; invest in synthetic mixed-document composition to generate
mid-range examples; replace Pearson r target with MAE ≤ 0.10 on mid-range holdout.

The HAR does not make a final architecture decision — both options are valid. The decision
should be made jointly with the G4 training lead after SIG-G4-1 assembly planning is complete.
Gap HW-PRES-REG-G03 (mid-range sourcing) is the critical path item that determines which
option is viable.

---

## Section 9 — Multi-Model Consensus

**Consensus Run Date**: 2026-02-23
**Models Consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)
**Consensus Confidence**: 9/10 (unanimous across both models on core findings)

### Analyst Pre-Consensus Summary

SIG-G4-4 (presence_reg) shares all infrastructure P0 blockers with SIG-G4-1 (presence_cls):
L2 field unpopulated, pixel-ratio script missing, handwriting subcommand not implemented. The
regression head has a structural advantage over the classification head — pixel-ratio directly
yields a continuous label without discretization — but faces an additional critical problem
specific to regression: the training distribution is structurally bimodal, and bimodal data
produces misleading Pearson r results even when the metric target appears to be met.

The Gaussian NLL head design is sound in principle but requires per-sample uncertainty ground
truth (sigma_sq) that does not exist in any source dataset and cannot be principally derived
from corpus-level heuristic labels. This is an additional complexity layer on top of all the
data gaps inherited from SIG-G4-1.

### Consensus Questions and Findings

**Q1: Is pixel-ratio a valid proxy for presence_score?**

Both models: Conditionally valid for document routing purposes (acceptable P2 construct
validity gap), but not valid as a perceptual presence measure. A small but salient annotation
(signature, marginal note) produces a low pixel-ratio score (~0.01–0.03) that underrepresents
its routing significance. For a pipeline whose goal is OCR routing, not human perception,
this gap is acceptable at P2. The construct validity study (HW-PRES-REG-G10) should be
completed before production deployment but does not block training.

**Q2: Is the bimodal distribution a solvable problem?**

Both models: FUNDAMENTAL FLAW under the current data strategy, not a solvable problem.

Gemini 2.5 Pro: "The bimodal distribution is a fundamental flaw, not a solvable problem
with the current data strategy. Trying to achieve Pearson r ≥ 0.80 is unrealistic if the
test set contains any meaningful number of mid-range samples."

Gemini 3 Pro Preview: "Training a regression head on discrete, quantized targets effectively
forces the model to learn a classification task disguised as regression. Without label
smoothing or soft targets, the Gaussian NLL loss will drive sigma_sq toward zero to match
the hard quantization points, defeating the purpose of uncertainty modeling."

Synthesis: Achievable Pearson r ≥ 0.80 on a similarly bimodal OOD set proves nothing about
mid-range regression capability. A model predicting only 0.0 and 0.95 achieves Pearson r
~0.95 on a bimodal test set. The metric must be supplemented with MAE on mid-range holdout
(0.10–0.80) or SRCC on the full continuous range.

**Q3: Does the regression head add unique value over SIG-G4-1?**

Gemini 2.5 Pro: "The regression head offers negligible value over the SIG-G4-1 classifier
given the data. Recommend deriving a continuous score from SIG-G4-1 logits as a weighted
sum of class probabilities."

Gemini 3 Pro Preview: Agreed on principle; additionally recommended ordinal regression as
an alternative if a continuous head is required for architectural reasons.

Synthesis: The regression head adds value via: (a) uncertainty output (sigma_sq) for
downstream confidence-aware routing; (b) smooth gradient signal to the shared backbone
during training; (c) enabling downstream consumers to use continuous thresholds without
requiring class boundary knowledge. However, all three benefits require solving the mid-range
data gap first. If HW-PRES-REG-G03 is not resolved, the unique value is negligible in practice.

**Q4: What risks are missing from the gap registry?**

Additional gaps identified by both models and incorporated into Section 8 above:

- Pearson r metric misinterpretation on bimodal test sets (added as HW-PRES-REG-G05, P1)
- False precision from midpoint-mapped quantized targets defeating Gaussian NLL purpose
  (added as HW-PRES-REG-G09, P1)
- sigma_sq calibration failure — model will encode label source type rather than true
  epistemic uncertainty (incorporated into HW-PRES-REG-G06, P1)

**Q5: Overall rating**

Both models: **Blocked**. Unanimous at 9/10 confidence.

Blocking factors in order of severity:

1. L2 field unpopulated: no labels exist for any dataset (P0)
2. Score range 0.20–0.70 has no large-scale source — bimodal training produces a misleading
   step-function regressor (P0)
3. Assembly pipeline not implemented (P0)
4. Pixel-ratio computation script not created (P0)
5. Pearson r target is misleading on bimodal data — must add MAE/SRCC co-metrics (P1)

### Consensus Summary

| Question | Gemini 2.5 Pro | Gemini 3 Pro Preview | Consensus |
| --- | --- | --- | --- |
| Pixel-ratio construct validity | P2 — acceptable for routing purposes | P2 — valid proxy; construct gap real but not P0 | P2 — not a blocker; document in model card |
| Bimodal distribution | Fundamental flaw — not solvable | Fundamental flaw — quantized targets undermine Gaussian NLL | Fundamental flaw; P0-C is the most critical gap |
| Unique value vs. SIG-G4-1 | Negligible; derive from logits | Negligible; prefer ordinal regression or derive from logits | Minimal until mid-range data gap (G03) resolved |
| Missing risks | Pearson r misinterpretation; sigma_sq calibration failure | False precision from quantized targets; sigma_sq calibration | Both risks added as P1 gaps |
| Overall rating | Blocked | Blocked | Blocked |

### Scoring Summary

| Component | Weight | Score | Weighted Score | Rationale |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 20/100 | 7.0 | Endpoint pools (0.0 and ~0.95) adequate; HierText gold standard present but tiny (8K); mid-range (0.20–0.70) near-empty; corpus-level labels are quantized anchors not true regression data |
| 14-Dimension Coverage | 25% | 18/100 | 4.5 | Score distribution dimension: 5/100; mixed content: 5/100; other dimensions limited but not zero; script diversity low |
| Wild Condition Coverage | 20% | 15/100 | 3.0 | 0 fully covered; 1 partial; 9 absent; all critical mid-range wild conditions (signatures, exam sheets, annotated forms) absent from training |
| OOD Design Quality | 20% | 55/100 | 11.0 | Structurally correct shared G4 OOD design; KHATT/CASIA/IIIT-INDIC are appropriate; 500 images is adequate for robustness auditing; regression-specific gap: pixel-level OOD labels required for Pearson r evaluation; mid-range OOD (sub-source 5d) too small at 50 images |
| **Overall** | 100% | — | **25.5** | — |

**Overall Score**: 25.5/100

**Grade**: F — Blocked

**Final Rating**: Blocked

### Top Recommendations (Consensus-Derived)

1. **Immediate P0**: Implement HierText pixel-level area ratio computation script. This is
   the only source of true continuous regression labels. 8,281 images is small but real.
   Effort: 1 day.

2. **Immediate P0**: Audit HierText mid-range yield. After running the pixel-ratio script,
   determine how many images fall in the 0.10–0.70 range. If fewer than 3,000, proceed
   immediately to synthetic mixed-document composition to generate mid-range training
   examples. Without mid-range data, the regression head cannot train meaningfully.
   Effort: 0.5 days audit + TBD composition.

3. **P1 governance decision**: Replace Pearson r ≥ 0.80 as the sole performance target.
   Add MAE ≤ 0.10 on mid-range holdout (0.10–0.80) as a co-primary metric. Pearson r
   ≥ 0.80 should be retained as a secondary metric with the understanding that it will be
   spuriously achievable on bimodal data and is not sufficient evidence of mid-range
   regression capability. Effort: 0 days — governance decision.

4. **Architecture decision**: After SIG-G4-1 assembly planning is complete, evaluate whether
   to proceed with SIG-G4-4 as a standalone regression head vs. deriving presence_score
   from SIG-G4-1 classifier logits (weighted sum). The logit-derived approach eliminates
   all P0 regression blockers at the cost of losing sigma_sq uncertainty output.

5. **Shared P0**: Implement handwriting subcommand in `prepare_multitask_datasets.py`. This
   unblocks all five G4 heads simultaneously. Effort: 2 days (shared with SIG-G4-1 through
   SIG-G4-5).
