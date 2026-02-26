---
l4_category: training-dataset
l4_dataset: capture-method
l4_workstream: WS3
l4_source_datasets:
  - doclaynet
  - rvl-cdip
  - smartdoc-qa
  - midv500
  - synth-multiscript-v3
  - realdae
l4_generation_script: scripts/prepare_multitask_datasets.py
l4_image_count: 50000
l4_status: planned
---

# Capture-Method Training Dataset

> **Quick Stats**: 50,000 images (target) | 7-class capture method classification | L2 `capture_method.method` enum
>
> **Status**: ❌ Blocked (3 classes at ~0 examples) | **HAR Score**: 59.1/100 | **P0 Gaps**: 4

---

## HAR Assessment (5-Model Consensus Review, 2026-02-21)

HAR Score: 59/100 — Needs Work
Status: ❌ BLOCKED — 3 of 7 classes have near-zero examples

---

## P0 Gaps

| Gap | Class Affected | Description | Path to Resolution |
|-----|---------------|-------------|-------------------|
| CAP-P0-1 | CAMERA_PROFESSIONAL | No source dataset contains camera images labeled as professional camera (DSLR/mirrorless) | Either acquire labeled data or merge with CAMERA_SMARTPHONE → CAMERA (see recommendation) |
| CAP-P0-2 | FAX | FAX transmission artifacts require synthesis; no real FAX datasets in inventory | Synthesize using half-tone moiré + vertical scanning artifacts; ~2K samples |
| CAP-P0-3 | SCANNER_ADF | L2 metadata has no field distinguishing ADF from flatbed scanners; rvl_cdip uses bare "scanner" | ADF heuristic: look for paper curl at edges + streaking artifacts; or heuristic label from document type |
| CAP-P0-4 | ALL | Modern CIS flatbed scanners (post-2010) have zero representation in training data | Source: acquire ≥1,500 samples from modern flatbed scanners |

---

## Class Reduction Recommendation (P1 Decision)

4-model consensus recommends reducing from 7 classes to 6 classes:

- Merge CAMERA_PROFESSIONAL + CAMERA_SMARTPHONE → **CAMERA**

**Rationale**:

- CAMERA_PROFESSIONAL has no source dataset
- In practice, the distinction between professional and smartphone cameras is not
  reliably determinable from document image quality alone
- 6-class model is more trainable with available data

**Tradeoff**: Loses granularity for professional camera use cases (uncommon in practice)

**Status**: Design decision pending. Training must not start until this is resolved.

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `capture-method` |
| **Head(s) Fed** | SIG-G5-1 `capture_cls` (also written `capture_method_cls`) |
| **Model(s)** | SigLIP 2 NAFlex |
| **Task Type** | Classification — 7 classes, softmax output |
| **Primary L2 Field(s)** | `capture_method.method` (7-class enum string) |
| **Training Phase** | Phase 5 — Page Attributes |
| **Target Size** | 50,000 images |
| **Image Size** | 384px (standard SigLIP 2 NAFlex input) |
| **Storage Location** | `E:\image_detection\03_training_datasets\capture-method\` |
| **GCS Path** | `gs://image_detection_b/capture-method_training/` |
| **Assembly Script** | `scripts/prepare_multitask_datasets.py source` |
| **HAR File(s)** | [har/sig-g5-capture-cls.md](../../planning/har/sig-g5-capture-cls.md) |
| **DDR File** | [diversity_reports/capture_method_ddr.md](../diversity_reports/capture_method_ddr.md) |

### 7 Canonical Classes

| Class | Description |
|-------|-------------|
| `BORN_DIGITAL` | PDF/vector document rendered directly to image — no physical capture step |
| `SCANNER_FLATBED` | Flatbed scanner acquisition via CCD or CIS sensor |
| `SCANNER_ADF` | Automatic Document Feeder scanner (distinctive roller artifacts) |
| `CAMERA_PROFESSIONAL` | DSLR or mirrorless camera during a dedicated photography session |
| `CAMERA_SMARTPHONE` | Smartphone or tablet camera (includes handheld and document scanner apps) |
| `FAX` | Fax transmission artifact pattern — halftone screening, 1D horizontal banding, effective resolution typically below 150 DPI, high noise |
| `SYNTHETIC` | Computationally generated images with no physical paper form (DocSynth300K, synth-multiscript pipeline, Augraphy outputs) |

### L2 Capture Method Value Mapping

The L2 `capture_method.method` field currently stores 3-class granularity. The assembly script maps
these known values to training classes:

| Dataset | L2 Raw Value | Maps To | Granularity Gap |
|---------|-------------|---------|-----------------|
| doclaynet | `"born_digital"` | `BORN_DIGITAL` | None |
| rvl_cdip | `"scanner"` (bare) | `SCANNER_FLATBED` (default) | Cannot distinguish FLATBED vs ADF without additional heuristic labeling |
| midv500, realdae, smartdoc-qa, sd7k, wsrd | `"camera_smartphone"` | `CAMERA_SMARTPHONE` | Cannot distinguish from `CAMERA_PROFESSIONAL` without metadata |
| docsynth300k, synth-multiscript-v3 | not populated | `SYNTHETIC` (via override pattern KI-005) | Must be set by assembly script based on source dataset identity |

**Critical infrastructure gap**: Four classes (`SCANNER_ADF`, `CAMERA_PROFESSIONAL`, `FAX`,
`SYNTHETIC`) cannot be derived from existing L2 field values without additional labeling work.
`CAMERA_PROFESSIONAL` has no identified source dataset. This gap drives the BLOCKED status.

---

## Section 2 — Status

| Metric | Value |
|--------|-------|
| **Assembly Status** | ❌ Blocked — 3 classes at ~0 examples (SCANNER_ADF, CAMERA_PROFESSIONAL, FAX) |
| **Current Count** | 0 / 50,000 assembled (dry-run: 39,893 records, 3-class granularity only) |
| **HAR Adequacy Score** | 59.1/100 — ⚠️ Needs Work (P0 blockers present) |
| **P0 Gap Count** | 4 (CAP-G01 through CAP-G04) |
| **Primary Blocker** | `scripts/label_capture_method.py` not created; CAMERA_PROFESSIONAL has no source data; FAX class requires Augraphy synthesis; L2 upgrade script missing |
| **Estimated Unblock Effort** | 4–6 days under 6-class schema (recommended); 2+ weeks under 7-class schema |
| **Last HAR Updated** | 2026-02-23 |

### Recommended Schema Reduction

The multi-model HAR consensus (Gemini 2.5 Pro + Gemini 3 Pro) recommends reducing from 7 to 6
classes by merging `CAMERA_PROFESSIONAL` into `CAMERA_SMARTPHONE`, creating a unified `CAMERA`
class. The visual distinction between high-end smartphone and DSLR for flat document photography is
negligible in practice, and no DSLR document photography dataset exists in the source pool.

Under the 6-class schema all P0 gaps are resolvable within 5 days:

| Revised Class | Maps From | Target |
|---------------|-----------|--------|
| `BORN_DIGITAL` | `BORN_DIGITAL` | 15,000 |
| `SCANNER_FLATBED` | `SCANNER_FLATBED` | 14,000 |
| `SCANNER_ADF` | `SCANNER_ADF` | 3,000 |
| `CAMERA` | `CAMERA_PROFESSIONAL` + `CAMERA_SMARTPHONE` | 8,000 |
| `FAX` | `FAX` | 3,000 |
| `SYNTHETIC` | `SYNTHETIC` | 7,000 |

Until the schema decision is finalised, this document uses the 7-class definition from the HAR.

---

## Section 3 — Source Pool Analysis

> Derived from HAR § Section 2. Identifies which source datasets contribute to the assembled
> training dataset and how much of each is usable given the required L2 field coverage.

**Required L2 Field**: `capture_method.method` (7-class enum string)
**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better; tier_3_heuristic acceptable for
ADF/FAX classes given no alternative, with mandatory 100-sample manual validation before propagation)
**Label Provenance**: tier_0_exact for born_digital and synthetic (provenance self-evident from
dataset origin); tier_3_heuristic for scanner sub-type splits (ADF vs flatbed); tier_2_model_assisted
or tier_3_heuristic for FAX (Augraphy simulation)

### Candidate Source Datasets by Class

**BORN_DIGITAL** — Target: 15,000

| Source Dataset | Total Images | Usable | Notes |
|----------------|-------------|--------|-------|
| doclaynet | ~80,000 | ~80,000 | 100% born_digital L2 label; well-covered; needs script diversity supplementation (98.5% Latin) |
| pubtabnet | ~519,000 | subset | Born-digital scientific tables; supplement for SCI domain coverage |
| fintabnet | ~97,000 | subset | Born-digital financial tables; supplement for FIN domain coverage |

Current usable: ~80,000+ available; target met by downsampling. No labeling work required.

**SCANNER_FLATBED** — Target: 12,500

| Source Dataset | Total Images | Usable | Notes |
|----------------|-------------|--------|-------|
| rvl-cdip | ~400,000 | ~10,000 (dry-run) | Bare `"scanner"` L2 value; 1990s CCD technology — modern CIS gap |
| mdiw13 | ~290,000 | ~20,000+ | Script-diverse scanner scans; adds non-Latin coverage |
| tobacco800 | ~1,290 | ~1,290 | Audit A/91; historical flatbed quality |
| nist-sd2 | ~5,590 | ~5,590 | Audit B/82; 1990s CCD flatbed |
| nist-sd6 | ~5,595 | ~5,595 | Audit B/83; 1990s CCD flatbed |

Current usable: ~10,000 (dry-run from rvl-cdip alone); ~30,000+ with MDIW13 added. Modern CIS
flatbed scanners (2010+) not represented — minimum 1,500 modern CIS examples needed (Gap CAP-G06).

**SCANNER_ADF** — Target: 2,500

| Source Dataset | Total Images | Usable | Notes |
|----------------|-------------|--------|-------|
| rvl-cdip | ~400,000 | ~0 now; est. 2,500 after heuristic | ADF-distinct label absent from all L2 sidecars; requires heuristic classifier |

Current usable: ~0. ADF visual heuristics (edge-parallel dark bands 2–5 px, systematic micro-skew
0.2–0.8° per batch, paper-feed horizontal streaks, multi-page separator marks) must be applied to
RVL-CDIP images via `scripts/label_capture_method.py`. Many ADF artifacts are destroyed in
RVL-CDIP preprocessing; usable pool estimated at 20–40% of total, yielding ~5,000–15,000 candidates
before confidence filtering. Target 2,500 at confidence ≥ 0.7.

> **ADF/Flatbed Indistinguishability (P0 data quality gap)**: rvl_cdip uses the bare `"scanner"`
> label in L2 metadata with no ADF/flatbed field. Cannot distinguish ADF from flatbed without:
> (a) manual annotation of paper curl/streak artifacts, or (b) a heuristic based on document
> appearance. This is a P0 data quality gap. The `scripts/label_capture_method.py` script
> (which does not yet exist) must implement this heuristic and write `"scanner_adf"` explicitly
> into L2 sidecars before any ADF-class records can be assembled.

**CAMERA_PROFESSIONAL** — Target: 5,000

| Source Dataset | Total Images | Usable | Notes |
|----------------|-------------|--------|-------|
| (none identified) | — | ~0 | No DSLR document photography dataset exists in source pool; MIDV500 and SmartDoc-QA are smartphone captures — the original plan listing them here was an error |

Current usable: ~0. This class is effectively blocked under the 7-class schema. The HAR consensus
recommendation is to merge `CAMERA_PROFESSIONAL` into `CAMERA_SMARTPHONE` (6-class schema reduction).

**CAMERA_SMARTPHONE** — Target: 5,000

| Source Dataset | Total Images | Usable | Notes |
|----------------|-------------|--------|-------|
| midv500 | ~15,000 | ~15,000 | Audit B/82; smartphone/tablet capture of identity documents |
| smartdoc-qa | ~4,280 | ~4,280 | Audit A/92; smartphone document photography |
| realdae | ~1,200 | ~1,200 | Audit B/84; camera capture |
| sd7k | ~7,239 | ~7,239 | Audit B/87; smartphone shadows |
| wsrd | ~4,500 | ~4,500 | Audit A/95; smartphone warping |

Current usable: ~19,893 (dry-run). Exceeds 5,000 target; downsample for balance. Under 6-class
schema (merged with CAMERA_PROFESSIONAL), combined target is 8,000 — still well-covered.

**FAX** — Target: 2,500

| Source Dataset | Total Images | Usable | Notes |
|----------------|-------------|--------|-------|
| rvl-cdip (fax subset) | ~400,000 | ~0 now; ~500 after manual label | RVL-CDIP includes fax doc types in 16-class taxonomy but no per-image FAX acquisition label |
| Augraphy `Faxify` (synthetic) | unlimited | ~2,000–4,500 | Halftone + 1D banding + low SNR simulation; sim-to-real gap is accepted risk |

Current usable: ~0. Requires: (1) manual labeling of ~500 RVL-CDIP images using FAX heuristics
(halftone screening, 1D horizontal banding, effective resolution below 150 DPI, binarized output,
high noise), then (2) Augraphy `Faxify` synthesis to reach 2,500. Estimated effort: 1.5 days.
Validation is blocked without real FAX test images — training F1 on synthetic FAX is not
meaningful for real-world deployment (Gap CAP-G07).

**SYNTHETIC** — Target: 7,500

| Source Dataset | Total Images | Usable | Notes |
|----------------|-------------|--------|-------|
| docsynth300k | ~300,000 | ~7,500 (downsample) | `capture_method=SYNTHETIC` via KI-005 override pattern |
| synth-multiscript-v3 | ~190,485 (GCS) | ~15,000 subset | `capture_method=SYNTHETIC` via override; 190K on GCS |

Current usable: ~50,000+ available immediately after applying SYNTHETIC label override. No
additional labeling work required; provenance is self-evident from dataset identity.

**Semantic definition note**: SYNTHETIC = images with no physical paper form (pipeline-generated).
A born-digital PDF exported as PNG is `BORN_DIGITAL`, not SYNTHETIC. A scanned document is
`SCANNER_FLATBED` regardless of whether the source was born-digital. This distinction must be
documented in `config/siglip2_multitask.yaml` (Gap CAP-G09).

### Pool Summary

| Metric | Value |
|--------|-------|
| **Total usable (current, 3-class)** | ~39,893 images (dry-run confirmed) |
| **Total usable (post-P0, 6-class schema)** | ~50,000+ projected |
| **Total usable (post-P0, 7-class schema)** | ~45,000 (CAMERA_PROFESSIONAL remains blocked) |
| **Training target** | 50,000 images |
| **Pool surplus/deficit (3-class)** | -10,107 images from target; 3 classes at ~0 |
| **Real vs. synthetic ratio (target)** | ~85% real / ~15% synthetic (SYNTHETIC class) |

---

## Section 4 — Label Schema

> The exact fields, types, and value conventions that training records must carry.

**Primary L2 Field**: `capture_method.method`
**Type**: str
**Range / Enum**: `BORN_DIGITAL` | `SCANNER_FLATBED` | `SCANNER_ADF` | `CAMERA_PROFESSIONAL` | `CAMERA_SMARTPHONE` | `FAX` | `SYNTHETIC`
**Provenance Tier**:

- `tier_0_exact` for sources where capture provenance is unambiguous from dataset documentation:
  doclaynet (born_digital), rvl-cdip (scanner, default FLATBED), docsynth300k / synth-multiscript-v3
  (SYNTHETIC)
- `tier_1_annotation` for camera sources where the capture device is documented in dataset metadata:
  midv500, smartdoc-qa, realdae, sd7k, wsrd (all `camera_smartphone`)
- `tier_3_heuristic` for ADF vs flatbed sub-type labeling via visual artifact heuristics on
  RVL-CDIP; must be validated at 100-sample manual spot-check before propagation
- `tier_2_model_assisted` or `tier_3_heuristic` for FAX class via Augraphy synthesis

**Derivation Formula**: L2 raw value → canonical class via `L2_TO_SOURCE_CLASS` mapping in
`scripts/prepare_multitask_datasets.py`. Bare `"scanner"` maps to `SCANNER_FLATBED` by default;
ADF labeling script must write `"scanner_adf"` explicitly into L2 sidecars.

### Training Manifest Record Schema

```json
{
  "image_path": "source/images/{filename}.jpg",
  "source_dataset": "{doclaynet|rvl_cdip|smartdoc_qa|...}",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0,
  "capture_method": "BORN_DIGITAL",
  "capture_method_raw_l2": "born_digital"
}
```

The `capture_method_raw_l2` field is optional but recommended for audit traceability — it preserves
the original L2 value before mapping to the canonical training class.

### Label Statistics (target)

| Metric | Value |
|--------|-------|
| **Classes** | 7 (or 6 under recommended schema reduction) |
| **Target class balance** | 7,143 images per class (perfectly balanced 50K / 7) |
| **Achievable without schema change** | 5 classes only; CAMERA_PROFESSIONAL and SCANNER_ADF/FAX at ~0 |
| **Class imbalance mitigation** | Class-weighted cross-entropy or balanced batch sampler; target effective class ratio ≤ 6:1 (Gap CAP-G11) |

---

## Section 5 — Composition and Splits

> Target count, class distribution, split ratios, and leakage prevention strategy.

### Target Class Distribution (7-class schema)

| Class | Target Images | Current Estimate | Risk |
|-------|--------------|-----------------|------|
| `BORN_DIGITAL` | 15,000 | ~80,000 available (downsample) | LOW |
| `SCANNER_FLATBED` | 12,500 | ~10,000 (dry-run); ~30,000 with MDIW13 | MEDIUM (modern CIS gap) |
| `SCANNER_ADF` | 2,500 | ~0 (heuristic labeling needed) | HIGH |
| `CAMERA_PROFESSIONAL` | 5,000 | ~0 (no identified DSLR source) | BLOCKED |
| `CAMERA_SMARTPHONE` | 5,000 | ~19,893 (dry-run; exceeds target) | LOW |
| `FAX` | 2,500 | ~0 (Augraphy synthesis needed) | HIGH |
| `SYNTHETIC` | 7,500 | ~50,000+ available (downsample) | LOW |
| **Total** | **50,000** | **~130,000 (3-class pool)** | — |

**Note on BORN_DIGITAL weighting**: The HAR sets a 30% target (15,000) for BORN_DIGITAL because
DocLayNet is the dominant source and must be downsampled to prevent it from dominating the class
distribution. Even within BORN_DIGITAL, deliberate domain sub-balancing is needed: DocLayNet spans
FIN/TEC/SCI but is absent in ADM, MED, and EDU domains.

### Split Strategy

| Split | Images | Percentage |
|-------|-------:|------------|
| Train | 35,000 | 70% |
| Val | 7,500 | 15% |
| Test | 7,500 | 15% |
| **Total** | **50,000** | **100%** |

**Split Method**: Stratified by class label and source dataset to ensure each class is represented
in all three splits.
**Random Seed**: 42
**Leakage Prevention**: Source dataset test splits reserved for OOD; global split registry enforces
SHA256 deduplication. RVL-CDIP is shared with the natural-scan skew and orientation datasets — the
global split registry prevents the same RVL-CDIP image from appearing in capture-method training
and the test split of any other dataset drawing from RVL-CDIP. DocLayNet is similarly shared
(capture-method BORN_DIGITAL class + orientation real component + IQA curated dataset).

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audit**: [capture_method_ddr.md](../diversity_reports/capture_method_ddr.md)
> **HAR Section 4 Reference**: [sig-g5-capture-cls.md § Section 4](../../planning/har/sig-g5-capture-cls.md)
> **Overall Diversity Score**: 61.6/100 (HAR pre-assembly estimate) | DDR score: 20.0/100 (0 samples assembled)

**Characteristic of this head**: Capture method IS the label, so within-class diversity is more
important than cross-class diversity. Each capture class must internally represent the full range of
real-world conditions it would encounter in production — a SCANNER_FLATBED example should span
old CCD scanners through modern CIS scanners, not just 1990s RVL-CDIP images.

| Dimension | L2 Field | Relevance | Target | Current | Status |
|-----------|----------|-----------|--------|---------|--------|
| capture_method | `capture_method.method` | CRITICAL — the label; ≥ 500 examples per class required | All 7 classes at ≥ 500 | 3 classes at target; 4 classes at ~0 | ❌ 43% |
| domain | `domain.level1` | IMPORTANT — born_digital should span TAX/FIN/SCI/MED; scanner docs tend to be business/administrative | ≥ 5 domains per capture class | DocLayNet: FIN/TEC/SCI strong; ADM/MED/EDU weak; RVL-CDIP: ADM/LEG/SCI | ⚠️ 70% |
| degradation | `quality.degradations` | HIGH — capture-specific artifacts required (ADF roller bands, FAX halftone banding, camera lens distortion) | Per-class degradation patterns | Scanner artifacts in RVL-CDIP; camera in smartdoc; FAX artifacts absent | ⚠️ 65% |
| color_mode | `image_properties.color_mode` | HIGH — FAX/ADF produce binarized; born_digital is color; camera is color | All 3 modes (color/grayscale/binarized) per relevant class | Born-digital: color; scanner: grayscale/binarized; FAX missing | ⚠️ 60% |
| document_age | `image_properties.document_age` | MEDIUM — RVL-CDIP/Tobacco800 have aged documents; born_digital is modern | ≥ 2 age classes per scanner class | RVL-CDIP/Tobacco800 have aged examples; modern CIS gap for SCANNER_FLATBED | ⚠️ 60% |
| resolution | `resolution.category` | MEDIUM — scanner DPI varies 150–600; FAX typically below 150 effective DPI | ≥ 3 resolution tiers per class | Multi-tier in scanner sources; FAX characteristic low DPI not yet represented | ⚠️ 70% |
| script_code | `language.script_code` | MEDIUM — DocLayNet/RVL-CDIP are 95%+ Latin; camera datasets have more geographic diversity | ≥ 3 script families per capture class | Camera (MIDV500/SmartDoc): Latin-dominant; MDIW13 adds script diversity for scanner | ⚠️ 55% |
| layout_type | `structure.layout_type` | LOW — layout should not drive capture method prediction | ≥ 3 layout types per class | Covered by DocLayNet variety within BORN_DIGITAL | ✅ 70% |

### Cross-Class Confusability Analysis

The highest-risk class pairs where the model is expected to confuse labels:

| Class Pair | Confusability | Visual Separator | Training Mitigation |
|------------|--------------|-----------------|---------------------|
| SCANNER_FLATBED vs SCANNER_ADF | HIGH — clean ADF scan is visually indistinguishable from flatbed | ADF: edge-parallel dark bands, consistent micro-skew, horizontal roller streaks | Heuristic labels require 100-sample manual validation before propagation |
| FAX vs SCANNER_FLATBED (binarized) | HIGH — fax output and binarized flatbed scan overlap visually | FAX: 1D horizontal banding, halftone screening, effective resolution below 150 DPI | FAX must have characteristic training examples with clear banding artifacts |
| CAMERA_SMARTPHONE vs CAMERA_PROFESSIONAL | HIGH — virtually indistinguishable for flat document photography | Professional: shallow DoF blur, RAW noise profile | Schema reduction recommended (merge into CAMERA) |
| SCANNER_FLATBED vs BORN_DIGITAL | MEDIUM — born-digital at 150 DPI resembles low-resolution scan | Flatbed: grain texture, margin shadow, page curl at edges | Include low-DPI born-digital examples alongside scanner in training |
| SYNTHETIC vs BORN_DIGITAL | MEDIUM — DocSynth300K PDFs resemble born-digital documents | Synthetic: programmatic artifacts, perfect kerning, no scan noise | Strict definition enforced: SYNTHETIC = no physical paper form |

### Key Diversity Gaps

- Four capture classes have near-zero training examples: SCANNER_ADF (~0), CAMERA_PROFESSIONAL (~0),
  FAX (~0). All three are critical for 7-class accuracy targets.
- SCANNER_FLATBED examples are almost entirely 1990s CCD technology (RVL-CDIP, NIST). Modern CIS
  flatbed scanners (2010+) have lower grain and better color — not represented.
- BORN_DIGITAL is domain-skewed toward FIN/TEC/SCI (DocLayNet composition). ADM, MED, and EDU
  domains require supplementation.
- Screen recapture (phone photographing a monitor) has no training analog in any source dataset and
  produces moiré + RGB subpixel aliasing not present in standard CAMERA_SMARTPHONE examples.

---

## Section 7 — Wild Condition Coverage

> **HAR Section 5 Reference**: [sig-g5-capture-cls.md § Section 5](../../planning/har/sig-g5-capture-cls.md)
> **Overall Wild Condition Score**: 33.3% (2 partial + 0 full out of 6 conditions)

| Wild Condition | L2 Evidence | Training Coverage | Status | Gap |
|----------------|-------------|------------------|--------|-----|
| Screen recapture (camera photographing monitor — moiré + RGB subpixel aliasing) | No training analog in any source dataset | None | ❌ Missing | No source dataset contains screen-captured documents. Covered in OOD-Capture 3a (200 images) only. Model will not have seen this pattern at train time. |
| ADF scanner with page curl artifacts (feed mechanism introduces curl warping) | No ADF-labeled training examples exist | None | ⚠️ Partial — OOD only | OOD-Capture 3b covers this (150 images). If ADF heuristic labeling (CAP-G01) is completed, training coverage improves to partial for ADF artifacts excluding curl. |
| 4th-generation photocopies (multi-pass Augraphy degradation cascade) | Not represented in training scanner class | None | ⚠️ Partial — OOD only | OOD-Capture 3c (150 images, Augraphy 4-pass). Training uses only single-pass scan examples. |
| High-speed production scanner (motion artifacts at above 200 ppm) | RVL-CDIP/Tobacco800 are desktop scanners, not production units | None | ⚠️ Partial — OOD only | OOD-Capture 3d (100 images, internal acquisition required). |
| FAX transmission artifacts on real fax machine output | No training examples (FAX class currently at ~0 images) | None | ❌ Not covered | No dedicated OOD entry for real FAX output. Without real FAX validation data, FAX class accuracy cannot be measured in production conditions. Proposed: OOD-Capture 3e (50 images, legal/government archives). |
| eFax / digital fax (born-digital document transmitted as fax — acquires FAX artifacts) | Semantic boundary between BORN_DIGITAL and FAX is unclear for this case | None | ❌ Not covered | Semantic ambiguity: a born-digital invoice transmitted via fax should be classified as FAX (acquisition method), not BORN_DIGITAL (origin). This boundary must be defined in `config/siglip2_multitask.yaml` (Gap CAP-G09). |

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
> **HAR Section 6 Reference**: [sig-g5-capture-cls.md § Section 6](../../planning/har/sig-g5-capture-cls.md)

| Field | Value |
|-------|-------|
| **Primary OOD Category** | OOD-Capture |
| **OOD Target Images (this head)** | 600 images (current design); ≥ 900 recommended |
| **OOD Acquisition Status** | ⏳ Not started (Phase 3, P0) |

| OOD Sub-source | Images | Relevance | Stress Scenario |
|----------------|-------:|-----------|-----------------|
| 3a. Screen recaptures | 200 | ✅ Direct | Camera photographs monitor displaying documents (LCD/OLED/E-ink, 3 device types × 3 angles × 20+ documents). Unique distortion: moiré patterns + RGB subpixel aliasing. No training analog. Labels: `capture_method=camera_smartphone`, `warping_type=perspective`, moiré presence flag. Cross-categorizes with OOD-Mixed. |
| 3b. ADF scanner with curl artifacts | 150 | ✅ Direct | Internal ADF scans (Fujitsu ScanSnap or equivalent) with deliberate page curl. Tests ADF-specific features not well-represented in training. Labels: `capture_method=scanner_adf`, `warping_type=page_curl`, `warping_severity`, `skew_angle_degrees`. Cross-categorizes with OOD-Degradation/warping_reg — joint labeling required. |
| 3c. 4th-generation photocopies | 150 | ✅ Direct | Augraphy simulation (4 passes of `PaperFactory` + `DirtyRollers` + `Letterpress`) on training-excluded source documents. Tests multi-generational degradation distinct from single-pass scanner training examples. Labels: `capture_method=scanner_flatbed`, `document_age=aged`, `degradation_count` ≥ 4, IQA labels. |
| 3d. High-speed production scanner | 100 | ✅ Direct | Internal production scanner acquisition (Kodak or Canon DR series) at 300+ ppm. Tests motion blur at speed and edge distortion not present in desktop flatbed training. Extension: 50-image border-cropped variants (3d-ext) to test whether ADF vs flatbed detection depends on border artifacts. |
| 3e. Real fax machine output (proposed) | 50 | ✅ Direct | Source from legal/government archives or law firms with physical fax machine provenance. Required to make FAX class validation meaningful; without it, FAX F1 score is computed only against synthetic Augraphy images. |
| 3d-ext. Border-cropped scanner variants (proposed) | ~50 | ⚠️ Indirect | Center-crop applied to existing 3d images — no new acquisition. Tests whether ADF vs flatbed classification degrades when border artifacts (roller bands) are removed from frame. |

**OOD Leakage Risk**: RVL-CDIP is a training source. OOD-Capture must use internally acquired or
independently photographed/scanned documents. Screen recaptures (3a), ADF internal scans (3b),
Augraphy photocopies on excluded source documents (3c), and production scanner outputs (3d) all
represent acquisition scenarios not present in training. Deduplication required against training
manifests: SHA256 + pHash (Hamming ≤ 5). Fax OOD (3e) must be confirmed as not previously
digitized into any known training dataset.

**Cross-head OOD note**: OOD sub-source 3a (screen recaptures) should also include
`orientation_class` labels for cross-head analysis with SIG-G3-1. OOD sub-source 3b (ADF curl)
must have `warping_severity` populated for cross-head analysis with SIG-G5-3 `warping_reg`. Both
annotation passes must be coordinated with the respective head teams.

---

## Section 9 — Assembly Pipeline

**Status**: ❌ Blocked — `source` subcommand dry-run works (39,893 records, 3-class output) but
3 classes remain at ~0 examples; upgrade to 7-class schema not yet implemented.

### Assembly Commands

```bash
# Prerequisites — run in order before full assembly:
#
# Step 1: Implement ADF heuristic labeling script (creates L2 sidecar updates for RVL-CDIP)
#   scripts/label_capture_method.py --dataset rvl-cdip --class ADF --confidence-threshold 0.7
#   Then manually validate 100-sample spot-check before propagation (Gap CAP-G05)
#
# Step 2: Generate FAX training data via Augraphy
#   scripts/label_capture_method.py --dataset rvl-cdip --class FAX --heuristic fax
#   python -c "... Augraphy Faxify generation for 2000-4500 images ..."
#
# Step 3: Apply SYNTHETIC override to synth-multiscript-v3 and docsynth300k
#   (handled inside assembly script via KI-005 override pattern — no separate script needed)

# Dry run (validates without writing — confirmed working as of 2026-02-21)
uv run python scripts/prepare_multitask_datasets.py source --dry-run

# Full assembly (requires P0 gaps resolved)
uv run python scripts/prepare_multitask_datasets.py source
```

**Dry-run result (2026-02-21)**: 39,893 records assembled at 3-class granularity:
`camera: 19,893` / `born_digital: 10,000` / `scanned: 10,000`. FAX, SCANNER_ADF, and
CAMERA_PROFESSIONAL all returned 0 records as expected. Mixing cap warning generated for
under-represented classes.

### Dependencies

| Dependency | Status | Required For |
|------------|--------|-------------|
| `scripts/label_capture_method.py` | ❌ Not created | ADF heuristic labeling of RVL-CDIP; FAX heuristic + Augraphy generation |
| `L2_TO_SOURCE_CLASS` 7-class upgrade | ❌ Pending | Mapping bare `"scanner"` + sub-types to 7-class schema in assembly script |
| `rvl-cdip` L2 metadata with ADF labels | ❌ Pending | SCANNER_ADF source pool |
| `rvl-cdip` L2 metadata with FAX labels | ❌ Pending | FAX source pool |
| `doclaynet_metadata.json` | ✅ Ready | BORN_DIGITAL source pool |
| `rvl_cdip_metadata.json` | ✅ Ready | SCANNER_FLATBED + (future) SCANNER_ADF + FAX source pools |
| `synth-multiscript-v3` GCS splits.jsonl | ✅ Ready | SYNTHETIC source pool via KI-005 override |
| `midv500_metadata.json`, `smartdoc-qa_metadata.json`, `realdae_metadata.json` | ✅ Ready | CAMERA_SMARTPHONE source pool |
| `sd7k_metadata.json`, `wsrd_metadata.json` | ✅ Ready | CAMERA_SMARTPHONE supplementary pool |
| Global split registry | ✅ Operational | Cross-dataset train/test leakage prevention |

### Generated Outputs

| File | Description |
|------|-------------|
| `train_manifest.json` | Flat JSON list of training records (70% of 50,000) |
| `val_manifest.json` | Flat JSON list of validation records (15% of 50,000) |
| `test_manifest.json` | Flat JSON list of test records (15% of 50,000; kept separate from OOD) |
| `source/images/` | Dataset images (symlinked or copied from source datasets; or GCS path) |

---

## Section 10 — Gap Registry

> **Source**: [sig-g5-capture-cls.md § Section 8](../../planning/har/sig-g5-capture-cls.md)
> **HAR Adequacy Score**: 59.1/100 — ⚠️ Needs Work (P0 blockers present; all P0 resolvable ≤ 5 days under 6-class schema)

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
|--------|-------------|------------|-------------|--------|
| CAP-G01 | SCANNER_ADF not separable from SCANNER_FLATBED in any L2 metadata (all RVL-CDIP uses bare `"scanner"`) | L2 metadata design did not capture scanner sub-type | Implement `scripts/label_capture_method.py` ADF heuristic: edge bands + micro-skew pattern + horizontal streaks on RVL-CDIP images; validate on 100-sample manual spot-check before propagation; estimated 2,500 usable ADF images after confidence filtering at ≥ 0.7 | 2–3 days |
| CAP-G02 | CAMERA_PROFESSIONAL class: near-zero usable data across all source datasets | MIDV500/SmartDoc-QA are smartphone captures; no DSLR document photography dataset exists in source pool | Option A: Source dedicated DSLR photography session (~2 weeks effort). Option B (recommended): Schema reduction — merge CAMERA_PROFESSIONAL into CAMERA_SMARTPHONE, adopt 6-class schema. Option B is the consensus recommendation. | 1–2 weeks (Option A) or 1 day (Option B schema change) |
| CAP-G03 | FAX class: zero labeled training examples; no real FAX validation data | FAX documents rare in modern public datasets; RVL-CDIP has FAX doc types in its 16-class taxonomy but no per-image FAX acquisition label | Step 1: Manually label ~500 RVL-CDIP images using FAX visual markers (halftone, 1D banding, effective resolution below 150 DPI). Step 2: Augraphy `Faxify` to extend to ~2,500–5,000 images. Step 3: Source ≥ 50 real FAX images for OOD-Capture 3e validation (legal/government archives). | 1 day labeling + 0.5 day generation + 1–2 days sourcing real FAX |
| CAP-G04 | No upgrade script to map existing 3-class L2 metadata (`born_digital`, `scanner`, `camera_*`) to 7-class schema | Assembly script `prepare_multitask_datasets.py source` was designed for 3-class output | Extend `scripts/label_capture_method.py` to write 7-class `capture_method.method` values into L2 sidecars; update `L2_TO_SOURCE_CLASS` mapping in prepare script; test with dry-run validation confirming all 7 classes appear in output | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Remediation | Effort |
|--------|-------------|-------------|--------|
| CAP-G05 | ADF heuristic label validation required: do NOT propagate heuristic ADF labels without 100-sample manual spot-check | Manual review of 100 ADF-candidate images by domain expert; measure heuristic precision; reject propagation if precision below 70%; document precision metric in L2 sidecar `label_confidence` field | 0.5 days |
| CAP-G06 | Modern CIS scanner gap: RVL-CDIP and NIST datasets are 1990s CCD technology; production documents frequently come from modern CIS flatbeds with different noise profiles (lower grain, better color) | Source dataset temporal gap | Source MIDV-2020 or equivalent CIS scanner dataset; target ≥ 1,500 modern CIS examples within SCANNER_FLATBED class | 1–2 days sourcing |
| CAP-G07 | FAX sim-to-real validation: zero real FAX examples means training/eval F1 is unmeasurable for real-world deployment | FAX class trained entirely on Augraphy synthetic data | Source ≥ 50 real FAX images for OOD sub-source 3e; compare model confidence on real vs synthetic FAX to quantify sim-to-real gap | 1–2 days sourcing |
| CAP-G08 | OOD-Capture set size (600 images) is insufficient for statistically robust per-class evaluation | OOD design preceded full gap analysis | Expand OOD-Capture from 600 to ≥ 900 total: add 3e (real FAX, 50 images), 3d-ext (border-cropped variants, 50 images), increase 3a/3b/3c each by ~50 images | 0 new acquisition for border-crop; 1–2 days for 3e acquisition |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
|--------|-------------|-------------|
| CAP-G09 | SYNTHETIC class semantic definition not documented — creates ambiguity for eFax edge cases (born-digital document transmitted via fax) | Add explicit SYNTHETIC definition to `config/siglip2_multitask.yaml`: SYNTHETIC = images with no physical paper form (pipeline-generated); BORN_DIGITAL = real document digitized as PDF; FAX = acquisition method, not document origin; clarify that eFax receives FAX classification regardless of born-digital origin |
| CAP-G10 | Per-class accuracy target: overall ≥ 85% accuracy may mask low accuracy on minority classes (SCANNER_ADF, FAX) | After training, compute per-class accuracy; set per-class floor ≥ 70% for all classes; report in training evaluation alongside aggregate metrics |
| CAP-G11 | Class imbalance mitigation not specified in assembly plan | Apply class-weighted cross-entropy or balanced batch sampler in `config/siglip2_multitask.yaml`; target effective class ratio ≤ 6:1 (richest to rarest class); FAX and SCANNER_ADF will be minority classes requiring upweighting |

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

| Head ID | Head Name | Task | Target Metric | Target Value | Test Set |
|---------|-----------|------|--------------|-------------|----------|
| SIG-G5-1 | `capture_cls` | 7-class softmax classification | Overall accuracy | ≥ 88% | OOD-Capture (600+ images) |
| SIG-G5-1 | `capture_cls` | 7-class softmax classification | Macro F1 | ≥ 0.80 | OOD-Capture |
| SIG-G5-1 | `capture_cls` | 7-class softmax classification | Per-class accuracy floor | ≥ 75% all classes | OOD-Capture per class |

**Note**: The HAR head specification lists the accuracy target as ≥ 85% overall / Macro F1 ≥ 0.80.
The task brief for this dataset document raises the accuracy target to ≥ 88% to align with the
tighter production routing requirement — `capture_method = CAMERA_*` drives adjusted correction
thresholds in the pipeline. Whichever target is formally adopted should be reflected in
`config/siglip2_multitask.yaml` and the training evaluation report.

**Per-class accuracy floor** (Gap CAP-G10): After training, per-class accuracy must be ≥ 75% for
all 7 classes. The aggregate accuracy target alone is insufficient because SCANNER_ADF and FAX are
operationally important minority classes — misclassifying an ADF scan as SCANNER_FLATBED suppresses
the ADF-specific correction pathway.

### Achieved Results

| Head | Val Accuracy | Test Accuracy | Val Macro F1 | Status |
|------|-------------|--------------|-------------|--------|
| `capture_cls` | — | — | — | ❌ Not trained |

---

## Related Documents

- **HAR File**: [sig-g5-capture-cls.md](../../planning/har/sig-g5-capture-cls.md)
- **DDR**: [capture_method_ddr.md](../diversity_reports/capture_method_ddr.md)
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-02-23 | Added HAR Assessment section, P0 Gaps summary table, Class Reduction Recommendation section, ADF/flatbed indistinguishability callout in SCANNER_ADF source pool |
| 1.0.0 | 2026-02-23 | Initial creation from HAR sig-g5-capture-cls.md and DDR capture_method_ddr.md |
