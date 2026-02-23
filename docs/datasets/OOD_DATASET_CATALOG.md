# OOD Dataset Catalog

> **Status**: ✅ Active | Dataset Inventory
> **Version**: 2.0.0
> **Created**: 2026-02-21
> **Updated**: 2026-02-21
> **Purpose**: Per-category acquisition plans and progress tracking for the OOD holdout dataset.
> All registered OOD images have entries in `metadata_registry/ood_registry.jsonl`.

## Overview

| Category | Target | Acquired | Status |
| --- | --- | --- | --- |
| OOD-Script | 600 | 0 | ⏳ Pending acquisition |
| OOD-Capture | 600 | 0 | ⏳ Pending acquisition |
| OOD-Degradation | 800 | 0 | ⏳ Pending acquisition |
| OOD-Handwriting | 500 | 0 | ⏳ Pending acquisition |
| OOD-Geometry | 500 | 0 | ⏳ Pending acquisition |
| OOD-Resolution | 500 | 0 | ⏳ Pending acquisition |
| OOD-Domain | 500 | 0 | ⏳ Pending acquisition |
| OOD-Code | 200 | 0 | ⏳ Pending acquisition |
| OOD-Mixed | 500 | 0 | ⏳ Pending acquisition |
| **Total** | **4,700** | **0** | ⏳ Pending acquisition |

## Registry Location

All OOD images are registered in `metadata_registry/ood_registry.jsonl`.
See [OOD Dataset Design](../planning/OOD_DATASET_DESIGN.md) for the complete registry schema
including the full ground-truth field set (19 heads, L2-aligned).

**Reserved scripts** (never in training): Mongolian (Mong), Syriac (Syrc), Georgian (Geor).
See [Script Reservation Policy](../planning/OOD_DATASET_DESIGN.md#script-reservation-policy).

---

## Training Dataset Dependencies

Each OOD category evaluates robustness in conditions not represented in its corresponding training dataset. The canonical three-way mapping (Head ↔ Training Dataset ↔ OOD Category) lives in [TRAINING_DATASET_QUICK_REFERENCE.md — Head ↔ Dataset ↔ OOD Cross-Reference](TRAINING_DATASET_QUICK_REFERENCE.md#head--dataset--ood-cross-reference). The table below summarises at the category level for acquisition planning.

| OOD Category | Training Dataset(s) | # | Heads Evaluated | Gap / Stress Scenario |
|---|---|---|---|---|
| **OOD-Script** | script-detection | 5 | SIG-G2-1 | Reserved scripts (Mong/Syrc/Geor) never seen; open-set rejection; Phase 2 preview scripts (Grek/Armn/Ethi) |
| **OOD-Geometry** | orientation, skew | 1, 2 | MNV4-H1, MNV4-H2, SIG-G3-1, SIG-G3-2 | 0°/180° disambiguation on symmetric docs; extreme perspective; Japanese TTB convention (labeled 0°, not 270°) |
| **OOD-Capture** | capture-method, warping | 7, 9 | SIG-G5-1, SIG-G5-3 | Screen recapture moiré/aliasing (no training analog); ADF curl artifacts; 4th-gen photocopy degradation |
| **OOD-Degradation** | iqa, shadow | 4, 8 | SIG-G1-1, SIG-G1-2, SIG-G1-3, SIG-G1-4, SIG-G1-5, SIG-G1-6, SIG-G5-2 | ≥5 simultaneous distortion types; book gutter shadow gradient not in sd7k; binarized `color_mode` absent |
| **OOD-Handwriting** | handwriting | 6 | SIG-G4-1, SIG-G4-2, SIG-G4-3, SIG-G4-4, SIG-G4-5 | ILLEGIBLE class absent from training; non-Latin handwriting (Arab/CJK/Deva); `specialized` content type |
| **OOD-Resolution** | resolution-quality | 3 | MNV4-H3, SIG-G5-5 | Born-digital low-DPI paradox (large font → high char-height at 72 DPI); 2×/4× upscale artifact detection |
| **OOD-Domain** | script-detection (secondary) | 5 | All 22 heads (robustness) | Novel domain combos: government forms, religious texts, thermal receipts — cross-domain generalization |
| **OOD-Code** | code-detection | 10 | SIG-G5-4 | IDE screenshots, mixed prose+code (arXiv/Jupyter), terminal output — outside generation-script distribution |
| **OOD-Mixed** | orientation, skew, iqa, shadow, warping | 1, 2, 4, 8, 9 | MNV4-H1, MNV4-H2, SIG-G1-1, SIG-G1-2, SIG-G1-3, SIG-G1-4, SIG-G1-5, SIG-G1-6, SIG-G3-1, SIG-G3-2, SIG-G5-2, SIG-G5-3 | Cascade failures: Mongolian TTB + aged + perspective; CJK HW + gutter shadow; binarized + extreme compression |

> **Note**: OOD-Domain tests all 22 heads for general robustness. Its secondary link to #5 (script-detection) reflects the Fraktur/Ottoman Arabic sub-sources in Phase 1 of acquisition.

---

## Acquisition Roadmap

### Phase 1: Script OOD (OOD-Script) — P0

**Target: 600 images total across 8 sub-sources**

#### 1a. Mongolian real (MTHv2) — target: 100 images

- Source: Mongolian Traditional Heritage dataset (MTHv2)
- Acquisition: Download from public repository
- Labels required: `script=Mong`, `open_set=true`, `orientation=0`, `text_direction=ttb`,
  `capture_method=scanner_flatbed`, `document_age=modern`
- Cross-category: OOD-Geometry (TTB vertical orientation stress)
- Dedup required: Against all training datasets (SHA256 + pHash, Hamming ≤ 5)
- Status: ⏳ Pending

#### 1b. Mongolian synth-v3 extract — target: 50 images

- Source: Extract from `gs://image_detection_b/synth_multiscript_v3/` — Mongolian subset
- **Critical**: Must verify Mongolian images exist in v3; if so, mark `split_type="ood"` BEFORE
  any training manifest is generated. These images may not be used in training.
- Labels required: `script=Mong`, `open_set=true`, `orientation` (from sidecar),
  `text_direction=ttb`, `capture_method=synthetic`
- Cross-category: OOD-Geometry
- Status: ⏳ Pending — requires v3 pool audit for Mongolian presence

#### 1c. Syriac manuscripts — target: 120 images

- Source: SANA corpus ([ufal.mff.cuni.cz/sana](https://ufal.mff.cuni.cz/sana)), OpenITI Syriac subset
- Acquisition: Download + sample 120 pages
- Labels required: `script=Syrc`, `open_set=true`, `orientation`, `text_direction=rtl`,
  `capture_method=scanner_flatbed`, `document_age=historical`
- Cross-category: OOD-Geometry (RTL orientation disambiguation)
- Dedup required: Against Arabic training datasets (similar script family)
- Status: ⏳ Pending

#### 1d. Georgian archives — target: 100 images

- Source: National Parliamentary Library of Georgia (nplib.ge), Wikimedia Commons
- Acquisition: Download + curate 100 pages
- Labels required: `script=Geor`, `open_set=true`, `orientation=0`, `text_direction=ltr`,
  `document_age=modern` or `historical`
- Status: ⏳ Pending

#### 1e. Historical Fraktur — target: 50 images

- Source: Project Gutenberg + Wikimedia Commons (public domain German texts pre-1900)
- Acquisition: Manual curation + dedup against RVL-CDIP (critical — overlap risk)
- Labels required: `script=Latn`, `open_set=false`, `capture_method=scanner_flatbed`,
  `document_age=historical`
- Cross-category: OOD-Domain
- **Warning**: Must run SHA256 + pHash dedup against RVL-CDIP before registration
- Status: ⏳ Pending

#### 1f. Ottoman Arabic — target: 30 images

- Source: Public domain Ottoman archives (Library of Congress, open collections)
- Acquisition: Manual curation + dedup against Arabic training datasets
- Labels required: `script=Arab`, `open_set=false`, `capture_method=scanner_flatbed`,
  `document_age=historical`, `text_direction=rtl`
- Cross-category: OOD-Domain
- Status: ⏳ Pending

#### 1g. Phase 2 preview scripts — target: 75 images (~25 each: Greek, Armenian, Ethiopic)

- Purpose: Evaluate open-set rejection behavior before Phase 2 training expands to these scripts
- Source: Unicode consortium samples, national digital libraries, linguistic archives
- Labels required: `script=Grek/Armn/Ethi`, `open_set=true`, `orientation`
- Note: Once Phase 2 training includes these scripts, move to OOD-Domain or retire
- Status: ⏳ Pending

#### 1h. Font variation (decorative fonts in trained scripts) — target: 75 images

- Purpose: Test whether script head overfits to specific font shapes vs. true script features
- Sources:

  - Ornamental/calligraphic Latin fonts rendered on standard document templates
  - Gothic/Blackletter English digital typefaces (modern rendering, not historical scans)
  - CJK brush-style digital fonts (e.g., FZShuTi, HanziPen)
  - Devanagari ornate display fonts

- Labels required: `script=Latn/Hans/Jpan/Deva` (as appropriate), `open_set=false`,
  `capture_method=born_digital`
- Acquisition: Render via Python (Pillow + curated font files) at standard DPIs
- Status: ⏳ Pending

---

### Phase 2: Geometry OOD (OOD-Geometry) — P0

**Target: 500 images total**

#### 2a. Symmetric documents — target: 300 images

- Source: Wikipedia article screenshots, government form templates, non-DocLayNet cover pages
- **IMPORTANT**: Must NOT use DocLayNet directly — it is a training source. Use a fresh crawl
  or Wikipedia screenshots that pass dedup against DocLayNet.
- Acquisition: Automated screenshot pipeline + human verification of visual symmetry
- Labels required: `orientation` (human-verified), `script=Latn`,
  `capture_method=born_digital`
- Purpose: Test 0°/180° disambiguation when document has no strong orientation cue
- Cross-category: OOD-Mixed (with TTB Mongolian for cascade failure coverage)
- Dedup required: Against DocLayNet (high overlap risk for cover/title pages)
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]` (cascade failure test)
- Status: ⏳ Pending

#### 2b. Extreme perspective — target: 100 images

- Source: Internal photography (document photographed at >30° tilt)
- Acquisition: Physical collection — photograph documents at steep angles (3 tilt axes)
- Labels required: `skew_angle_degrees` (measured), `orientation`, `warping_type=perspective`,
  `capture_method=camera_smartphone`
- Status: ⏳ Pending

#### 2c. Japanese vertical text — target: 100 images

- Source: NDL Digital Collection (National Diet Library Japan), public domain Japanese archives
- Purpose: Japanese vertical text is labeled as `orientation=0` in training (non-standard
  convention). OOD coverage verifies the model handles this correctly without confusing TTB
  with rotated documents.
- Labels required: `script=Jpan`, `orientation=0`, `text_direction=ttb`,
  `capture_method=scanner_flatbed`
- Dedup required: Against synth-multiscript-v3 (Jpan samples present in training)
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]`
- Status: ⏳ Pending

---

### Phase 3: Capture OOD (OOD-Capture) — P0

**Target: 600 images total**

#### 3a. Screen recaptures — target: 200 images

- Source: Internal generation — photograph LCD/OLED/E-ink screen displaying documents
- Acquisition: Physical collection (3 device types × 3 angles × 20+ documents)
- Labels required: `capture_method=camera_smartphone`, IQA labels (blur, noise, contrast),
  `color_mode=color`
- Purpose: Unique moiré/RGB aliasing artifacts not in any training dataset
- Cross-category: OOD-Mixed (screen recapture + RTL document)
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]` (cascade: moiré degrades SigLIP)
- Status: ⏳ Pending

#### 3b. ADF scanner with curl artifacts — target: 150 images

- Source: Internal scanning with Fujitsu ScanSnap or equivalent ADF scanner
- Acquisition: Scan documents with intentional page curl, skew, and edge feed artifacts
- Labels required: `capture_method=scanner_adf`, `warping_type=page_curl`,
  `warping_severity`, `skew_angle_degrees`
- Status: ⏳ Pending

#### 3c. 4th-generation photocopies — target: 150 images

- Source: Iterative photocopy simulation via Augraphy (`photocopy` augmentation, 4 passes)
- Acquisition: Script generation from training-excluded source documents
- Labels required: `capture_method=scanner_flatbed`, IQA labels (noise, contrast, compression),
  `document_age=aged`
- Status: ⏳ Pending

#### 3d. High-speed production scanner — target: 100 images

- Source: Internal scanning on production-grade document scanner (Kodak, Canon DR series)
- Acquisition: Scan at 300+ ppm with high-speed feed settings
- Labels required: `capture_method=scanner_flatbed`, IQA labels, `color_mode`
- Status: ⏳ Pending

---

### Phase 4: Degradation OOD (OOD-Degradation) — P0

**Target: 800 images total**

#### 4a. Multiply-distorted (≥5 simultaneous types) — target: 500 images

- Source: Augraphy with ≥5 simultaneous distortion types applied to training-excluded documents
- Distortion stack: gutter-shadow + page_curl + defocus blur + noise + JPEG compression
- Labels required: All IQA head labels (`blur_score`, `noise_score`, `contrast_score`,
  `shadow_severity`, `warping_severity`, `compression_score`, `overall_quality`),
  `shadow_type`, `warping_type`
- IQA labels require human annotation (classical detectors insufficient for compound distortion)
- Status: ⏳ Pending

#### 4b. Watermarked documents — target: 100 images

- Source: Public government forms with official watermarks + synthetic watermark overlay
- Labels required: `watermark_severity` (0.0–1.0, human-labeled)
- Status: ⏳ Pending

#### 4c. Book gutter shadow (hard shadow gradient) — target: 100 images

- Source: Internal photography of bound books photographed open-flat
- Purpose: sd7k training data covers flat-document shadows only; gutter shadows have a
  distinct gradient curve not present in training data
- Labels required: `shadow_severity`, `shadow_type=hard`, `warping_type=page_curl`
- Cross-category: OOD-Mixed
- Status: ⏳ Pending

#### 4d. Binarized (1-bit) documents — target: 100 images

- Source: Archival 1-bit TIFF scans from public domain collections + Sauvola binarization
  applied to training-excluded grayscale images
- Labels required: `color_mode=binarized`, IQA labels, `capture_method`
- Purpose: `image_properties.color_mode=binarized` not present in current IQA training data
- Status: ⏳ Pending

---

### Phase 5: Handwriting OOD (OOD-Handwriting) — P0

**Target: 500 images total**

#### 5a. KHATT Arabic cursive — target: 200 images

- Source: KHATT dataset ([khatt.ideas2serve.net](https://khatt.ideas2serve.net/))
- Acquisition: Download + sample 200 pages not in training split
- Labels required: `handwriting_presence=SUBSTANTIAL`, `handwriting_presence_score`,
  `handwriting_legibility` (including FAIR/POOR/ILLEGIBLE cases), `handwriting_content_type=prose`,
  `handwriting_script=Arab` (L2 field), `text_direction=rtl`
- **ILLEGIBLE coverage**: Select 20+ pages with `handwriting_legibility=ILLEGIBLE` to cover
  this class that is absent from training data
- Dedup required: Against any Arabic handwriting training data
- Status: ⏳ Pending

#### 5b. CASIA-HWDB CJK handwritten — target: 150 images

- Source: NLPR CASIA database (request form required at [nlpr.ia.ac.cn/databases](http://nlpr.ia.ac.cn/databases/))
- Fallback if access denied: SCUT-HCCDoc dataset (open access Chinese handwritten documents)
- Acquisition: Download + sample 150 pages not in training split
- Labels required: `handwriting_presence=SUBSTANTIAL`, `handwriting_presence_score`,
  `handwriting_legibility`, `handwriting_content_type`
- Status: ⏳ Pending — access request may require 2–4 weeks

#### 5c. IIIT-INDIC Devanagari handwritten — target: 100 images

- Source: IIIT-INDIC dataset (public access)
- Acquisition: Download + sample 100 pages
- Labels required: `handwriting_presence=SUBSTANTIAL`, `script=Deva`, `text_direction=ltr`
- Status: ⏳ Pending

#### 5d. Specialized content handwriting — target: 50 images

- Source: Mathematical hand-notation (formula notebooks, engineering drawings) from public
  domain archives
- Purpose: `handwriting_content_type=specialized` class not covered in any training HW dataset
- Labels required: `handwriting_content_type=specialized`, `handwriting_presence`
- Status: ⏳ Pending

---

### Phase 6: Resolution OOD (OOD-Resolution) — P0

**Target: 500 images total**

#### 6a. Vector PDF at 3 DPIs — target: 300 images

- Source: DocLayNet born-digital PDFs (already available locally)
- **Note**: DocLayNet IS used in training. Must run SHA256 + pHash dedup of rendered images
  against training manifests. Use pages/documents not in training split.
- Acquisition: Render each at 72 DPI, 150 DPI, 300 DPI using PyMuPDF (100 pages × 3 DPIs)
- Labels required: `capture_method=born_digital`, `resolution_quality` (measured char height),
  `color_mode`
- Purpose: Vector PDFs rendered at low DPI create a misleading resolution signal (high char
  height possible at 72 DPI from large fonts, but low effective resolution)
- Status: ⏳ Pending

#### 6b. Upscaled rasters — target: 200 images

- Source: OHR-Bench test set or RealDAE subset — NOT DIQA-5000 (DIQA-5000 is in training)
- Acquisition: Apply 2× and 4× bicubic upscaling (100 images × 2 upscale factors)
- Labels required: `resolution_quality` (measured on original before upscaling),
  `capture_method` (as original), `color_mode`
- Labels: Include `upscale_factor` (2 or 4) as a custom field for analysis
- **Source restriction**: DIQA-5000 must not be used — it is in training. Confirm OHR-Bench
  test split is not included in any training manifest before use.
- Status: ⏳ Pending

---

### Phase 7: Domain OOD (OOD-Domain) — P1

**Target: 500 images total**

#### 7a. Non-English government forms — target: 250 images

- Source: Public domain government forms in non-English jurisdictions (EU, India, Japan, etc.)
- Acquisition: Curate 250 images across domain types and languages
- Labels required: All applicable heads; `document_age=modern`
- PII considerations: Government forms often contain PII. Use blank/template forms or
  officially released blank versions only. If real filled forms are used, must be explicitly
  de-identified. Alternatively, use synthetic facsimiles generated from templates.
- Status: ⏳ Pending

#### 7b. Religious texts — target: 150 images

- Source: Public domain religious manuscripts, Bible societies open digitization projects,
  Buddhist canon digital archives
- Labels required: All applicable heads; `document_age` (modern/historical varies)
- Status: ⏳ Pending

#### 7c. Technical manuals and receipts — target: 100 images

- Source: Open-source hardware manuals, thermal receipt facsimiles
- Labels required: All applicable heads; `capture_method`, IQA labels
- Purpose: Receipt thermal fade and bleed-through artifacts not in training IQA data
- Status: ⏳ Pending

---

### Phase 8: Code OOD (OOD-Code) — P0

**Target: 200 images total**

Purpose: The SigLIP `code_confidence` head (Group 5) has zero OOD coverage in the original
design. This category provides dedicated code document evaluation.

#### 8a. Source code screenshots — target: 100 images

- Source: GitHub repository screenshots, VS Code window captures, IDE screenshots
- Acquisition: Automated screenshot pipeline across 5+ programming languages
- Labels required: `code_confidence=1.0` (human-labeled), `capture_method=born_digital` or
  `camera_smartphone`, `color_mode=color`, IQA labels
- Status: ⏳ Pending

#### 8b. Mixed prose + code documents — target: 60 images

- Source: arXiv technical papers with large code blocks, Jupyter notebook exports
- Acquisition: Render PDF pages containing both prose and code sections
- Labels required: `code_confidence` (0.3–0.7 range, human-labeled), `capture_method=born_digital`
- Status: ⏳ Pending

#### 8c. Terminal/console output — target: 40 images

- Source: Terminal session screenshots, log file renders
- Acquisition: Automated screenshot pipeline (monospace-only, no prose context)
- Labels required: `code_confidence=1.0`, `capture_method=camera_smartphone` or
  `born_digital`, `color_mode=color`
- Status: ⏳ Pending

---

### Phase 9: Mixed OOD (OOD-Mixed) — P1

**Target: 500 images total**

Cross-category combinations from images acquired in Phases 1–8 that satisfy ≥2 OOD
categories simultaneously. Select after other phases are complete.

#### Examples of target combinations

| Combination | Count | Source phases |
| --- | --- | --- |
| Mongolian TTB + aged + extreme perspective | 100 | Phase 1a + Phase 2b |
| CJK handwriting + book gutter shadow | 100 | Phase 5b + Phase 4c |
| Screen recapture + RTL document | 100 | Phase 3a (RTL content) |
| Syriac RTL + ILLEGIBLE handwriting | 75 | Phase 1c + Phase 5a |
| Binarized + extreme compression distortion | 75 | Phase 4d + Phase 4a |
| Font variation (decorative) + aged paper | 50 | Phase 1h + Phase 4a |

Labels required: All applicable heads for each combination; `ood_categories` array must
include all relevant category strings.

---

## Per-Image Entry Template

Once images are acquired, add entries to `metadata_registry/ood_registry.jsonl` using the
full schema. See [OOD Dataset Design — Schema](../planning/OOD_DATASET_DESIGN.md#schema)
for the complete field reference.

Minimal required fields for every entry:

```json
{
  "sha256": "abc123...",
  "phash": "def456...",
  "phash_hamming_threshold": 5,
  "source_path": "/mnt/e/image_detection/ood/{category}/{filename}",
  "ood_categories": ["ood_script"],
  "reason": "Mongolian (Mong) TTB reserved script — never in training",
  "registered_date": "2026-02-21",
  "acquisition_method": "MTHv2 dataset download",
  "license": "Academic use only",
  "dedup_verified": true,
  "dedup_date": "2026-02-21",
  "evaluation_pipeline_stage": ["mobilenetv4", "siglip2"],
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
    "skew_angle_degrees": 0.0,
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
  },
  "open_set_evaluation": {
    "expected_behavior": "high_entropy_rejection",
    "reject_threshold": 0.50,
    "min_entropy_threshold": 0.70,
    "notes": "Model must not assign >50% confidence to any in-training script class"
  }
}
```

---

## Notes

- All OOD images must be stored on E: drive under `/mnt/e/image_detection/ood/`
- Subdirectory per category: `ood_script/`, `ood_capture/`, `ood_degradation/`,
  `ood_handwriting/`, `ood_geometry/`, `ood_resolution/`, `ood_domain/`, `ood_code/`, `ood_mixed/`
- No OOD images may be uploaded to GCS training buckets
- Cross-category images are stored once in the primary category directory; `ood_categories`
  array references all applicable categories
- Acquisition progress updated monthly or after each acquisition phase
- After any new training dataset is added, re-run dedup protocol
  (see [Dedup Re-run Protocol](../planning/OOD_DATASET_DESIGN.md#dedup-re-run-protocol))
