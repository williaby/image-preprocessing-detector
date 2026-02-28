# OOD Dataset Design

> **Status**: ✅ Active | Planning Specification
> **Version**: 2.1.0
> **Created**: 2026-02-21
> **Updated**: 2026-02-21
> **Purpose**: Formal specification for the out-of-distribution holdout dataset used for
> final evaluation of the SigLIP 2 + MobileNetV4 training pipeline.

## Design Principles

1. **Never-train**: No OOD image may appear in any training or validation (hyperparameter
   tuning) manifest. OOD is exclusively for final hold-out evaluation.
2. **Maximally out-of-distribution**: Each OOD image must differ from the training distribution
   in at least one clearly defined, documented dimension.
3. **Labeled**: All OOD images must have complete ground-truth labels for all applicable heads
   using the L2-aligned schema (see [Schema](#schema)).
4. **Diverse internally**: OOD set must cover all 9 OOD categories below.
5. **Deduplicated**: All OOD images must pass SHA256 + pHash deduplication (Hamming
   distance ≤ 5) against all training datasets before registration.
6. **Registered**: Every OOD image is registered in `metadata_registry/ood_registry.jsonl`
   before any training manifest is generated.
7. **Reserved scripts enforced**: Three scripts are permanently excluded from training and
   reserved exclusively as OOD anchors (see [Script Reservation Policy](#script-reservation-policy)).
8. **Sources segregated**: OOD-Geometry and OOD-Resolution sources must not overlap with
   training datasets. DocLayNet and DIQA-5000 are training sources and **must not be used
   as OOD sources** — pHash dedup cannot reliably detect cross-DPI semantic duplicates, so
   the same DocLayNet document rendered at a different DPI would pass the dedup check but
   still leak in-distribution semantic content. OOD-Resolution must use exclusively
   non-training sources (e.g., FUNSD, XFUND, WikiTableSet).
9. **Dedup re-run on training updates**: Any time a new dataset is added to training, the
   OOD registry must be re-deduped against the new dataset before the next training run.
10. **Augmentation engine independence**: OOD-Degradation images must be produced using a
    different augmentation engine than the training degradation pipeline. If training uses
    Augraphy for shadow/warping simulation, OOD-Degradation images must originate from real
    degraded documents or use an independent tool (e.g., DocDegradation, physical scanning)
    to avoid correlation between training augmentation artifacts and OOD test conditions.

---

## Script Reservation Policy

Five scripts are permanently excluded from training data and reserved exclusively for OOD
evaluation. The original three direction anchors cover all major text direction axes; two
additional scripts were added from SALAMI (5 samples each — too few for meaningful training
contribution, ideal as OOD anchors for historical manuscript evaluation).

| Reserved Script | ISO 15924 | Direction | Source Strategy |
| --- | --- | --- | --- |
| Armenian | Armn | LTR (unique alphabet) | SALAMI historical manuscripts (5 images) |
| Georgian | Geor | Left-to-right (LTR, unique letterforms) | SALAMI (5 images) + National Parliamentary Library of Georgia archives |
| Gothic | Goth | LTR (historical, extinct script) | SALAMI historical manuscripts (5 images) |
| Mongolian Traditional | Mong | Top-to-bottom (TTB) | MTHv2 dataset + synth-v3 extract |
| Syriac | Syrc | Right-to-left (RTL) | SANA / OpenITI Syriac manuscripts |

**Enforcement**: Any training manifest containing images with ISO 15924 script in
`{"Armn", "Geor", "Goth", "Mong", "Syrc"}` must be rejected at training time (see
[Reserved Script Guard](#reserved-script-guard)). Enforced by `OOD_RESERVED_SCRIPTS` in
`scripts/prepare_multitask_datasets.py` and `OOD_ONLY_SCRIPTS` in
`scripts/generate_base_dataset_v3.py`.

**Important**: These 5 scripts are training-exclusion *anchors*. OOD may freely include
additional scripts beyond these 5. Conversely, any script in the OpenLID-expanded training set
(see [Training Scope](#training-scope-and-openlid-coverage)) is only truly OOD for the script
head if it is one of these 5 reserved scripts or belongs to a font variation category.

---

## Font Variation OOD Strategy

For the script detection head, font variation within *trained* scripts constitutes a valid OOD
dimension. The model may have learned script-specific visual patterns tied to specific font
styles rather than the underlying script structure.

**Font variation OOD cases (included in OOD-Script):**

| Case | Description | Script in Training? | OOD Dimension |
| --- | --- | --- | --- |
| Ornamental Latin | Decorative calligraphic or highly stylized Latin fonts | Yes (Latn) | Font style outside training distribution |
| Gothic/Blackletter | Old English, Fraktur style (modern typefaces, not historical scans) | Yes (Latn) | Distinct glyphic style not in training fonts |
| CJK brush-style | Traditional ink brush Chinese/Japanese (digital typeface) | Yes (Hans, Jpan) | Organic variation not in synth generator |
| Devanagari decorative | Ornate Devanagari poster/display fonts | Yes (Deva) | Non-standard display rendering |

**Note**: Historical Fraktur scans and Ottoman Arabic scans are *historical variants* (different
from modern decorative fonts) and are listed under [OOD-Script historical variants](#ood-script-historical-variants).

---

## Training Scope and OpenLID Coverage

The SigLIP 2 script detection head (Group 2) will ultimately cover **all scripts in OpenLID**
(~107 languages, ~60+ scripts), not just the 10-class Phase 1 set (Latn, Hans, Jpan, Kore,
Tibt, Arab, Deva, Cyrl, Thai, Hebr).

**Implications for OOD design:**

1. Scripts added in Phase 2+ (e.g., Greek, Ethiopic, Tamil, Burmese) become
   in-training scripts and are no longer truly OOD for the script head. They may still
   provide OOD coverage for other heads (handwriting, geometry, capture method).
   Note: Armenian (Armn) is now permanently reserved for OOD (moved from Phase 2+ candidate
   to reserved anchor due to insufficient training data — only 5 SALAMI samples).
2. The 5 reserved scripts (Armn, Geor, Goth, Mong, Syrc) remain OOD **regardless** of OpenLID coverage.
3. OOD-Script must include a Phase 2 preview sub-set (scripts that will enter training in
   Phase 2 but are not yet in Phase 1): these evaluate open-set rejection behavior.
4. After each training phase expansion, OOD-Script should be re-evaluated: any script that
   transitions from open-set to in-distribution must move to a new OOD category (e.g.,
   OOD-Domain) or be retained only for non-script-head evaluation.

---

## Phase 2 OOD Evolution Protocol

As the training scope expands to Phase 2 (OpenLID ~60+ scripts), the OOD registry must
evolve without invalidating historical evaluation comparisons.

### Lifecycle States

Each OOD registry entry carries an `ood_status` field with these values:

| Status | Meaning |
| --- | --- |
| `active` | Currently used in OOD benchmark evaluation |
| `retired` | Moved to training; replaced in OOD by a different source |
| `under_review` | Flagged for reclassification pending Phase 2 expansion decision |

### Reclassification Rules

When a Phase 2 preview script enters the training set:

1. All OOD images with `ood_categories = ["ood_script"]` for that script change
   `ood_status` → `"under_review"`.
2. Evaluate whether the image still provides OOD coverage for other heads
   (e.g., handwriting, geometry, domain). If yes, update `ood_categories` to reflect the
   remaining non-script OOD dimensions and set `ood_status → "active"`.
3. If no non-script OOD value remains, set `ood_status → "retired"`, populate
   `retired_reason`, and register a replacement source in `replacement_registered`.
4. Log all reclassifications in `metadata_registry/ood_phase_log.jsonl`.

### Registry Fields for Phase 2 Tracking

The following fields are added to every registry entry (see [Schema](#schema)):

```json
{
  "ood_status": "active",
  "training_phase_added": null,
  "retired_reason": null,
  "replacement_registered": null
}
```

- `ood_status`: `"active"` | `"retired"` | `"under_review"` (required, default `"active"`)
- `training_phase_added`: `null` for permanent OOD anchors; `int` (1, 2, …) if the script
  entered training in that phase (triggers reclassification review)
- `retired_reason`: string explaining why retired (e.g., `"Script entered Phase 2 training"`)
- `replacement_registered`: SHA256 of the replacement OOD image; `null` if no replacement yet

---

## OOD Categories and Target Composition (~5,400 images total)

| Category | Target | Source Strategy | Dimensions Tested |
| --- | --- | --- | --- |
| **OOD-Script** | 600 images | Reserved scripts (Mong/Syrc/Geor) + historical variants + font variations + Phase 2 previews | Script detection head; orientation (TTB/RTL cases) |
| **OOD-Capture** | 600 images | Screen recaptures, ADF scanner with curl, 4th-gen photocopies, high-speed production scanner | Capture method head (7-class), IQA heads |
| **OOD-Degradation** | 800 images | Multiply-distorted (≥5 simultaneous types): gutter-shadow + warp + blur + noise + compression; watermarked; binarized docs | All IQA heads; shadow/warping sub-types |
| **OOD-Handwriting** | ~1,000 images | Arabic cursive (KHATT), CJK handwritten (CASIA-HWDB), Devanagari (IIIT-INDIC); includes ILLEGIBLE and specialized content_type; grid-sampled across {script × legibility} pairs | Handwriting heads (5 sub-heads) |
| **OOD-Geometry** | 500 images | Symmetric docs from non-training sources; extreme perspective (>30° tilt); Japanese vertical text; boundary skew sub-set (±8°, ±9°, ±10°, ±11°) | Orientation head; skew head; cascade failure |
| **OOD-Resolution** | 500 images | Vector PDFs at 72/150/300 DPI from FUNSD/XFUND/WikiTableSet; upscaled rasters from non-training sources (2x/4x bicubic) | Resolution quality head (MobileNetV4 + SigLIP) |
| **OOD-Domain** | 500 images | Government forms (EU CERFA, German Bundesministerium, UN multilingual, Japanese NTA); religious texts; receipts; technical manuals | All heads (unseen domain type) |
| **OOD-Code** | 400 images | Source code screenshots; terminal output; markdown rendered; mixed prose+code; license-cleared, no PII | code_confidence head (SigLIP Group 5) |
| **OOD-Mixed** | 500 images | Cross-category combinations spanning ≥3 OOD dimensions each: Mong+aged+perspective, CJK HW+gutter shadow, screen recapture+RTL | All heads (compound failure detection) |

**Total target**: ~5,400 images

**Cross-category note**: A single OOD image may satisfy multiple categories. For example,
a Mongolian document photographed at a steep angle contributes to both OOD-Script (reserved
script) and OOD-Geometry (extreme perspective). These images are registered once in
`ood_registry.jsonl` with multiple entries in the `ood_categories` array.

---

## OOD-Script Justification

### Reserved Script Anchors

The three reserved scripts provide directional coverage that cannot be tested with in-training
scripts:

**Mongolian (Mong — Top-to-Bottom):**

- Explicitly excluded from synth-multiscript-v3 training data.
- Unique vertical writing direction stresses both the script head and the orientation head.
- **v3 contradiction resolution**: If Mongolian images are found in synth-multiscript-v3,
  they must be extracted and marked `split_type="ood"` before any training manifest is
  generated. They may not be used in training even if they exist in the v3 pool.
- Sources: MTHv2 (real), synth-v3 Mongolian extract (if present, mark ood only).

**Syriac (Syrc — Right-to-Left):**

- RTL script with cursive letterforms distinct from Arabic training data.
- Tests RTL orientation disambiguation that Arabic already partially covers (but with
  different visual features).
- Sources: SANA corpus, OpenITI digitized Syriac manuscripts (public domain).

**Georgian (Geor — Left-to-Right):**

- LTR script with completely unique letterforms not seen in any training script.
- Tests whether the script head rejects with high entropy rather than hallucinating a
  known-class prediction.
- Sources: National Parliamentary Library of Georgia (nplib.ge), Wikimedia Commons.

### OOD-Script Allocation (~600 images)

| Sub-source | Count | Cross-category |
| --- | --- | --- |
| Mongolian real (MTHv2) | 100 | OOD-Script + OOD-Geometry (TTB orientation) |
| Mongolian synth-v3 extract (ood split only) | 50 | OOD-Script + OOD-Geometry |
| Syriac manuscripts (real) | 120 | OOD-Script + OOD-Geometry (RTL) |
| Georgian archives (real) | 100 | OOD-Script |
| Historical Fraktur (real scans, public domain) | 50 | OOD-Script + OOD-Domain |
| Ottoman Arabic (real scans, public domain) | 30 | OOD-Script + OOD-Domain |
| Phase 2 preview scripts (~25 each: Greek/Armenian/Ethiopic) | 75 | OOD-Script (open-set behavior) |
| Font variation (ornamental Latin/CJK/Deva decorative fonts) | 75 | OOD-Script (font style OOD) |
| **Total** | **600** | |

### Historical Variants {#ood-script-historical-variants}

- **Historical Fraktur**: Project Gutenberg + Wikimedia Commons, German texts pre-1900.
  MUST dedup against RVL-CDIP (critical — Wikimedia/RVL-CDIP overlap risk).
  Labels: `script=Latn`, `document_age=historical`, `source=scanner_flatbed`.

  ```bash
  python scripts/check_ood_leakage.py \
      --ood-candidates /mnt/e/image_detection/ood/ood_script/fraktur/ \
      --training-index /mnt/e/image_detection/01_base_data/rvl_cdip/ \
      --hamming-threshold 5 \
      --report fraktur_rvlcdip_dedup_report.json
  ```

- **Ottoman Arabic**: Public domain Ottoman archives (Library of Congress, open collections).
  MUST dedup against all Arabic training datasets.
  Labels: `script=Arab`, `document_age=historical`, `source=scanner_flatbed`.

---

## OOD Acquisition Plan

| OOD Category | Acquisition Method | Est. Effort |
| --- | --- | --- |
| Mongolian real (MTHv2) | Dataset download | 1 day |
| Mongolian synth-v3 extract | Filter splits.jsonl for Mong, mark split_type="ood" | 0.5 days |
| Syriac manuscripts | SANA/OpenITI download | 0.5 days |
| Georgian archives | nplib.ge + Wikimedia Commons | 0.5 days |
| Historical Fraktur/Ottoman | Wikimedia + public domain + dedup vs RVL-CDIP | 2 days |
| Font variation (decorative) | Render known scripts with curated ornamental fonts | 1 day |
| Phase 2 preview scripts | Source from linguistic archives (Unicode consortium samples) | 1 day |
| Screen recaptures | Internal generation: photograph LCD/OLED/E-ink at varied angles | 1 day |
| ADF scanner with curl | Internal: scan with Fujitsu ScanSnap or equivalent | 0.5 days |
| 4th-gen photocopies | Iterative photocopy simulation script (Augraphy) | 0.5 days |
| Multiply-distorted (≥5 types) | Augraphy extended pipeline | 1 day |
| Watermarked documents | Source from public government forms + synthesize watermarks | 0.5 days |
| Binarized documents | 1-bit TIFF from archives + Sauvola binarization of existing data | 0.5 days |
| KHATT Arabic cursive | Dataset download (khatt.ideas2serve.net) — 300 pages | 1 day |
| CASIA-HWDB CJK | NLPR request form + download (fallback: SCUT-HCCDoc); map CRA writer-level labels to L2 legibility tiers (EXCELLENT/GOOD/FAIR/POOR/ILLEGIBLE) | 2 days |
| IIIT-INDIC Devanagari HW | Dataset download | 0.5 days |
| ILLEGIBLE handwriting | Curate from KHATT (worst-legibility subset) | 0.5 days |
| Symmetric docs (non-training) | Wikipedia screenshots + form images (non-DocLayNet) | 0.5 days |
| Japanese vertical text | NDL Digital Collection samples | 0.5 days |
| Extreme perspective | Internal photography: document at >30° tilt | 0.5 days |
| Vector PDF at 3 DPIs | FUNSD / XFUND / WikiTableSet: non-training born-digital forms at 72/150/300 DPI (DocLayNet banned — semantic content in training distribution) | 1 day |
| Upscaled rasters (2x/4x) | FUNSD test set + non-DocLayNet sources; bicubic 2x and 4x upscaling (confirm SHA256 not in any training manifest) | 0.5 days |
| Government/religious forms | EU CERFA forms (French); German Bundesministerium official docs; UN multilingual official documents; Japanese NTA tax forms; non-English religious texts (public domain) | 2 days |
| Source code screenshots | GitHub screenshot tool + terminal captures (400+ target); all images must be license-cleared (MIT/Apache/CC) and PII-scrubbed | 0.5 days |
| Code mixed with prose | Research papers with large code blocks (arXiv CC-licensed); confirm no PII in terminal captures | 0.5 days |
| Cross-category (OOD-Mixed) | Combine collected OOD samples; each image must span ≥3 OOD dimensions (e.g., reserved script + aged + perspective tilt) | 0.5 days |

---

## Acceptance Thresholds

Each OOD evaluation run must meet these thresholds to pass. Failing a threshold triggers
investigation and potential training data remediation. Thresholds are split by pipeline
stage because MobileNetV4 (pre-correction, raw input) and SigLIP 2 (post-correction) have
distinct failure modes. See also [Oracle Mode](#oracle-mode) for isolating Stage 2 failures.

### MobileNetV4 Thresholds (Pre-Correction Stage, Raw Input)

Images are fed raw (uncorrected) to MobileNetV4 only. Evaluated on OOD images with
`evaluation_pipeline_stage` containing `"mobilenetv4"`.

| Head | Type | Metric | Go Threshold | Warn Threshold |
| --- | --- | --- | --- | --- |
| orientation_class | Classification | Accuracy | ≥ 0.95 | ≥ 0.90 |
| skew_angle | Regression | MAE (degrees) | ≤ 1.5° | ≤ 2.5° |
| resolution_quality (pre) | Regression | SRCC vs human GT | ≥ 0.72 | ≥ 0.62 |

**Note on resolution_quality head**: MobileNetV4 receives the raw image at its native
resolution (no pre-resize to 224px for this head). The resolution quality head must observe
the actual pixel density to produce meaningful scores. Only the classification/skew heads
use the standard 224px crop.

### SigLIP 2 Thresholds (Post-Correction Stage)

Images are passed through MobileNetV4 correction, then fed to SigLIP. Evaluated on OOD
images with `evaluation_pipeline_stage` containing `"siglip2"`.

| Head | Type | Metric | Go Threshold | Warn Threshold |
| --- | --- | --- | --- | --- |
| blur_score | Regression | SRCC vs human GT | ≥ 0.75 | ≥ 0.65 |
| noise_score | Regression | SRCC vs human GT | ≥ 0.75 | ≥ 0.65 |
| contrast_score | Regression | SRCC vs human GT | ≥ 0.75 | ≥ 0.65 |
| compression_score | Regression | SRCC vs human GT | ≥ 0.70 | ≥ 0.60 |
| skew_score | Regression | SRCC vs human GT | ≥ 0.75 | ≥ 0.65 |
| overall_quality | Regression | SRCC vs human GT | ≥ 0.70 | ≥ 0.60 |
| script_class (in-dist) | Classification | Top-1 Accuracy | ≥ 0.90 | ≥ 0.85 |
| script_class (open-set) | Open-set rejection | Avg H_norm = H(x)/ln(N) | ≥ 0.70 | ≥ 0.60 |
| orientation_class (val) | Classification | Accuracy | ≥ 0.95 | ≥ 0.90 |
| skew_angle (val) | Regression | MAE (degrees) | ≤ 1.5° | ≤ 2.5° |
| handwriting_presence | Classification | F1 (NONE vs rest) | ≥ 0.85 | ≥ 0.78 |
| handwriting_legibility | Regression | SRCC vs human GT | ≥ 0.72 | ≥ 0.62 |
| handwriting_content_type | Classification | F1 macro | ≥ 0.80 | ≥ 0.72 |
| capture_method | Classification | F1 macro (7-class) | ≥ 0.80 | ≥ 0.72 |
| shadow_severity | Regression | SRCC vs human GT | ≥ 0.75 | ≥ 0.65 |
| warping_severity | Regression | SRCC vs human GT | ≥ 0.75 | ≥ 0.65 |
| watermark_severity | Regression | SRCC vs human GT | ≥ 0.70 | ≥ 0.60 |
| code_confidence | Regression | SRCC vs human GT | ≥ 0.80 | ≥ 0.70 |
| resolution_quality (val) | Regression | SRCC vs human GT | ≥ 0.75 | ≥ 0.65 |

**Open-set rejection criterion**: For reserved scripts (Mong, Syrc, Geor) and Phase 2
preview scripts, the model must not assign > 0.5 confidence to any single in-training
class. **Normalized logit entropy** H_norm = H(x) / ln(N_current_classes) must be ≥ 0.70,
where N is the number of in-training classes at evaluation time (Phase 1: N=10, Phase 2:
N=60+). Normalization ensures the threshold is mathematically stable across phase expansions:
H_norm=0.70 always means ≥70% of maximum possible uncertainty regardless of N.

---

## Ground Truth Labeling — IAA Protocol

For all subjectively labeled OOD fields, inter-annotator agreement (IAA) must be measured
and reported before accepting ground truth labels into the registry.

### Applicable Fields

| Field | IAA Metric | Minimum Acceptable | Notes |
| --- | --- | --- | --- |
| handwriting_presence | Cohen's Kappa (κ) | ≥ 0.70 | 2+ annotators |
| handwriting_legibility | Cohen's Kappa (κ) | ≥ 0.70 | 2+ annotators |
| handwriting_content_type | Cohen's Kappa (κ) | ≥ 0.70 | 5-class categorical |
| watermark_severity | Krippendorff's Alpha | ≥ 0.65 | Ordinal 0.0–1.0 |
| shadow_severity | Krippendorff's Alpha | ≥ 0.65 | Ordinal 0.0–1.0 |
| overall_quality | Krippendorff's Alpha | ≥ 0.65 | Regression target |

### Protocol

1. **Minimum 2 independent annotators** per image for each subjective field.
2. Compute IAA on a **calibration set of 30 images** before full annotation begins.
3. If IAA < minimum: conduct alignment session, revise guidelines, re-annotate calibration set.
4. After calibration passes, proceed with full annotation. Record final κ / α in
   `metadata_registry/iaa_report.json`.
5. Ground truth is the **majority vote** (categorical) or **mean** (regression) across
   annotators when IAA ≥ minimum.
6. Images with IAA < minimum after two rounds must use **expert adjudication** (single
   designated expert breaks tie) with a note in `reason` field.

---

## Schema

### OOD Registry Format (`metadata_registry/ood_registry.jsonl`)

One JSON object per line. Field names align to `layer2_enrichment_v2.schema.json` v2.3.0.

```json
{
  "sha256": "abc123...",
  "phash": "def456...",
  "phash_hamming_threshold": 5,
  "source_path": "/mnt/e/image_detection/ood/{category}/{filename}",
  "ood_categories": ["ood_script", "ood_geometry"],
  "reason": "Mongolian (Mong) TTB reserved script — not in training; vertical orientation stress",
  "registered_date": "2026-02-21",
  "acquisition_method": "MTHv2 dataset download",
  "license": "Academic use only",
  "dedup_verified": true,
  "dedup_date": "2026-02-21",
  "evaluation_pipeline_stage": ["mobilenetv4", "siglip2"],
  "ood_status": "active",
  "training_phase_added": null,
  "retired_reason": null,
  "replacement_registered": null,
  "ground_truth": {
    "blur_score": null,
    "noise_score": null,
    "contrast_score": null,
    "compression_score": null,
    "skew_score": null,
    "overall_quality": null,
    "script": "Mong",
    "open_set": true,
    "orientation": 0,
    "skew_angle_degrees": 0.5,
    "handwriting_presence": "NONE",
    "handwriting_presence_score": 0.0,
    "handwriting_legibility": "NOT_APPLICABLE",
    "handwriting_legibility_score": 0.0,
    "handwriting_content_type": "not_applicable",
    "capture_method": "scanner_flatbed",
    "shadow_severity": 0.0,
    "shadow_type": "none",
    "warping_severity": 0.0,
    "warping_type": "none",
    "watermark_severity": 0.0,
    "code_confidence": 0.0,
    "resolution_quality": null,
    "color_mode": "grayscale",
    "document_age": "modern",
    "text_direction": "ttb"
  }
}
```

**Field reference** (L2 schema alignment):

| GT Field | L2 Object | L2 Field | Values |
| --- | --- | --- | --- |
| blur_score | ml_image_quality | blur_score | 0.0–1.0; null if not assessed |
| noise_score | ml_image_quality | noise_score | 0.0–1.0 |
| contrast_score | ml_image_quality | contrast_score | 0.0–1.0 |
| compression_score | ml_image_quality | compression_score | 0.0–1.0 |
| skew_score | ml_image_quality | skew_score | 0.0–1.0 |
| overall_quality | ml_image_quality | overall_score | 0.0–1.0 |
| script | language | — | ISO 15924 title case (Mong, Syrc, Geor, Latn…) |
| open_set | — | — | true if script NOT in current training set |
| orientation | geometric | orientation_class | int: 0, 90, 180, 270 |
| skew_angle_degrees | geometric | skew_angle_degrees | float, signed |
| handwriting_presence | handwriting_assessment | presence | NONE\|SPARSE\|MODERATE\|SUBSTANTIAL\|DOMINANT |
| handwriting_presence_score | handwriting_assessment | presence_score | 0.0–1.0 |
| handwriting_legibility | handwriting_assessment | legibility | NOT_APPLICABLE\|EXCELLENT\|GOOD\|FAIR\|POOR\|ILLEGIBLE |
| handwriting_legibility_score | handwriting_assessment | legibility_score | 0.0–1.0 |
| handwriting_content_type | handwriting_assessment | content_type | not_applicable\|signatures_marks\|numeric\|alphanumeric\|prose\|mixed\|specialized |
| capture_method | capture_method | method | born_digital\|scanner_flatbed\|scanner_adf\|camera_professional\|camera_smartphone\|fax\|synthetic |
| shadow_severity | physical_degradation | shadow_severity | 0.0–1.0 |
| shadow_type | physical_degradation | shadow_type | none\|hard\|soft\|mixed |
| warping_severity | physical_degradation | warping_severity | 0.0–1.0 |
| warping_type | physical_degradation | warping_type | none\|page_curl\|fold\|perspective\|barrel\|pincushion\|wave\|complex |
| watermark_severity | physical_degradation | watermark_severity | 0.0–1.0 |
| code_confidence | — | — | 0.0–1.0 (human-labeled) |
| resolution_quality | resolution | — | 0.0–1.0 regression target |
| color_mode | image_properties | color_mode | color\|grayscale\|binarized |
| document_age | image_properties | document_age | modern\|aged\|historical |
| text_direction | language | text_direction | ltr\|rtl\|ttb |

### Open-Set Evaluation Sub-Object

For images with `open_set == true`, add the following sub-object to the registry entry:

```json
{
  "open_set_evaluation": {
    "expected_behavior": "high_entropy_rejection",
    "reject_threshold": 0.50,
    "min_entropy_threshold": 0.70,
    "entropy_formula": "H_norm = H(x) / ln(N_current_classes)",
    "entropy_note": "Threshold is normalized: 0.70 = 70% of max possible entropy. N_current_classes is the number of in-training script classes at evaluation time (Phase 1: 10, Phase 2: 60+). This ensures threshold is invariant to phase expansion.",
    "notes": "Model must not assign >50% confidence to any in-training class"
  }
}
```

### evaluation_pipeline_stage

Specifies which pipeline stage(s) the image is intended to evaluate:

- `"mobilenetv4"` — image evaluated in raw (pre-correction) state: orientation, skew, resolution quality
- `"siglip2"` — image evaluated after correction: all 16 SigLIP heads
- Both `"mobilenetv4"` and `"siglip2"` — for cascade failure coverage (raw image → correction → post-correction)

Array of strings. Most OOD images specify both. OOD-Geometry symmetric-document cases
**must** specify both to capture cascade failures.

### Registry Versioning (`metadata_registry/ood_registry_meta.json`)

A companion metadata file tracks the schema version and state of the OOD registry. This
enables reproducible evaluation comparisons across training phases.

```json
{
  "schema_version": "2.1.0",
  "registry_path": "metadata_registry/ood_registry.jsonl",
  "last_dedup_date": "2026-02-21",
  "total_entries": 0,
  "active_entries": 0,
  "retired_entries": 0,
  "phase_dedup_log": "metadata_registry/dedup_log.jsonl",
  "phase_change_log": "metadata_registry/ood_phase_log.jsonl",
  "checksum_entries": "sha256 of ood_registry.jsonl at last update"
}
```

Update `ood_registry_meta.json` after every dedup run, phase expansion, or registry entry
addition/retirement.

### Manifest Item Schema Extension

OOD images use a separate benchmark pipeline and are NEVER included in training or validation
manifests. Training manifest items include `split_type` as a required field:

```json
{
  "image_path": "shadow/images/example.jpg",
  "script": "LATN",
  "source": "scanned",
  "orientation": 0,
  "shadow": 0.0,
  "warping": 0.0,
  "split_type": "train"
}
```

`split_type` values: `"train"` | `"val"` | `"test"` | `"ood"` (REQUIRED, no default)

The OOD benchmark manifest (`ood_eval.jsonl`) uses the full registry schema above with all
ground truth fields. It is generated by `prepare_benchmark_dataset.py` and consumed
exclusively by `evaluate_ood_performance.py`.

---

## Enforcement

### OOD Leakage Check (`prepare_multitask_datasets.py`)

Applied at the end of every sub-command before writing manifest files:

```python
def _check_ood_leakage(
    samples: list[dict],
    ood_registry_path: Path,
    phash_hamming_threshold: int = 5,
) -> None:
    """Halt if any sample SHA256 or pHash matches OOD registry.

    Args:
        samples: Training manifest samples.
        ood_registry_path: Path to ood_registry.jsonl.
        phash_hamming_threshold: Max Hamming distance for near-duplicate detection.
    """
    ood_registry = load_ood_registry(ood_registry_path)
    ood_sha256s = {entry["sha256"] for entry in ood_registry}
    ood_phashes = [entry["phash"] for entry in ood_registry]
    leakage_sha256 = [
        s for s in samples if compute_sha256(s["image_path"]) in ood_sha256s
    ]
    leakage_phash = [
        s for s in samples
        if any(
            hamming_distance(compute_phash(s["image_path"]), op) <= phash_hamming_threshold
            for op in ood_phashes
        )
    ]
    leakage = list({s["image_path"] for s in leakage_sha256 + leakage_phash})
    if leakage:
        raise ValueError(
            f"OOD LEAKAGE DETECTED: {len(leakage)} OOD images in training manifest\n"
            f"First 5: {leakage[:5]}"
        )
```

### Reserved Script Guard {#reserved-script-guard}

Applied in `prepare_multitask_datasets.py` on every sub-command writing a training manifest:

```python
RESERVED_OOD_SCRIPTS: frozenset[str] = frozenset({"Mong", "Syrc", "Geor"})

def _validate_no_reserved_scripts(
    samples: list[dict],
    reserved: frozenset[str] = RESERVED_OOD_SCRIPTS,
) -> None:
    """Halt if any training sample uses a reserved OOD-only script.

    Args:
        samples: Training manifest samples.
        reserved: ISO 15924 script codes reserved for OOD evaluation only.

    Raises:
        ValueError: If any sample's script field matches a reserved script.
    """
    violations = [s for s in samples if s.get("script") in reserved]
    if violations:
        raise ValueError(
            f"RESERVED SCRIPT VIOLATION: {len(violations)} training samples "
            f"use OOD-reserved scripts {set(reserved)}.\n"
            f"Reserved scripts must never appear in training data.\n"
            f"First 3 violations: {[v['image_path'] for v in violations[:3]]}"
        )
```

### Training Script Guard (`modal/train_siglip2_multitask.py`)

```python
def _validate_manifest(samples: list[dict]) -> None:
    """Reject manifest items with split_type == 'ood' or reserved scripts."""
    ood_items = [s for s in samples if s.get("split_type") == "ood"]
    if ood_items:
        raise ValueError(
            f"MANIFEST VALIDATION FAILED: {len(ood_items)} items have split_type='ood'. "
            f"OOD images must never be used for training or validation."
        )
    _validate_no_reserved_scripts(samples)
```

### Dedup Re-run Protocol {#dedup-re-run-protocol}

When any new dataset is added to the training pool:

1. Add new dataset images to the dedup index (SHA256 + pHash all images).
2. Run dedup against `metadata_registry/ood_registry.jsonl`:

   ```bash
   python scripts/check_ood_leakage.py \
       --ood-registry metadata_registry/ood_registry.jsonl \
       --new-training-dir /mnt/e/image_detection/{new_dataset}/ \
       --hamming-threshold 5
   ```

3. If any OOD image is flagged: remove from OOD registry, find a replacement source, re-register.
4. Update `dedup_date` field in the registry entry.
5. Log the dedup run result in `metadata_registry/dedup_log.jsonl`.

**ORB feature matching for OOD-Geometry augmented images**: pHash is rotation-sensitive
and may fail to detect near-duplicates that differ only by perspective or geometric
augmentation. For OOD-Geometry images, supplement pHash with ORB (Oriented FAST and
Rotated BRIEF) feature matching: any training image sharing ≥80% ORB keypoint matches
with an OOD-Geometry image must be flagged for manual review, regardless of pHash
Hamming distance.

---

## Benchmark Pipeline (Separate from Training)

OOD evaluation uses a dedicated pipeline, never touching training code paths:

```text
prepare_benchmark_dataset.py
    ↓ (reads ood_registry.jsonl, copies/renders images to benchmark dir)
ood_eval.jsonl (one entry per OOD image, with ground truth labels)
    ↓
evaluate_ood_performance.py
    ↓ (runs model inference on each image at correct pipeline stage)
ood_benchmark_results.json (per-head metrics broken down by OOD category)
```

`evaluate_ood_performance.py` respects `evaluation_pipeline_stage`:

- `mobilenetv4`: Feeds raw (uncorrected) image to MobileNetV4 only.
- `siglip2`: Applies MobileNetV4 corrections, then feeds corrected image to SigLIP.
- Both: Runs both stages and reports per-stage metrics separately.

### Oracle Mode {#oracle-mode}

Oracle Mode is a diagnostic evaluation pass that isolates Stage 2 (SigLIP) failures from
Stage 1 (MobileNetV4) correction errors:

```text
Oracle Mode:
    ↓ (skip MobileNetV4 entirely)
    ↓ (feed PERFECTLY-CORRECTED OOD images directly to SigLIP)
    ↓ (correct orientation = 0, skew = 0.0, no compression artifacts)
ood_benchmark_results_oracle.json
```

**Interpretation**: If SigLIP fails under Oracle Mode (when given perfect corrections), the
failure is a genuine Stage 2 weakness. If SigLIP passes Oracle Mode but fails in standard
mode, the failure is a Stage 1 correction cascade error that must be addressed in
MobileNetV4 training.

Oracle Mode must be run after every SigLIP training update where any SigLIP head fails its
Go threshold in the standard cascade evaluation.

---

## Cascade Failure Coverage

The two-stage pipeline (MobileNetV4 raw → corrections → SigLIP corrected) introduces cascade
failure modes not present in single-model evaluation:

| Cascade Failure Mode | OOD Coverage | Category |
| --- | --- | --- |
| MobileNetV4 misclassifies symmetric doc orientation → SigLIP receives wrong-orientation image | Symmetric docs (non-training source) | OOD-Geometry |
| MobileNetV4 aggressive deskew on TTB Mongolian → SigLIP receives distorted image | Mongolian TTB images | OOD-Script + OOD-Geometry |
| MobileNetV4 correct orientation, SigLIP receives extreme moiré from screen recapture → degraded IQA/script | Screen recaptures | OOD-Capture |
| MobileNetV4 correct for clean high-res, SigLIP receives upscaled raster → wrong resolution quality | Upscaled rasters | OOD-Resolution |

All cascade failure images must specify `evaluation_pipeline_stage: ["mobilenetv4", "siglip2"]`
so both stages are evaluated and the compound failure can be measured.

---

## Related Documents

- [Wild Conditions Analysis](WILD_CONDITIONS_ANALYSIS.md)
- [OOD Dataset Catalog](../datasets/OOD_DATASET_CATALOG.md) (per-image acquisition plans)
- [Dataset Diversity Requirements](DATASET_DIVERSITY_REQUIREMENTS.md)
- [SigLIP 2 Multitask Requirements](SIGLIP2_MULTITASK_REQUIREMENTS.md)
- [Layer 2 Enrichment Schema](../../docs/schema/layer2_enrichment_v2.schema.json)
