# OOD Coverage Gap Report

Generated: 2026-02-25 | Registry: 9,155 images | Target: 12,000 | Progress: 76.3%

## Head Coverage Summary

| Head | Images acquired | Min (50) | Target (100) | Status |
|------|-----------------|----------|--------------|--------|
| skew_score | 0 | ✗ | ✗ | ⚠ AT_RISK |
| handwriting_legibility | 0 | ✗ | ✗ | ⚠ AT_RISK |
| handwriting_legibility_score | 0 | ✗ | ✗ | ⚠ AT_RISK |
| resolution_quality | 0 | ✗ | ✗ | ⚠ AT_RISK |
| code_confidence | 0 | ✗ | ✗ | ⚠ AT_RISK |
| warping_severity | 100 | ✓ | ✓ | ✓ OK |
| watermark_severity | 100 | ✓ | ✓ | ✓ OK |
| document_age | 110 | ✓ | ✓ | ✓ OK |
| warping_type | 300 | ✓ | ✓ | ✓ OK |
| handwriting_content_type | 550 | ✓ | ✓ | ✓ OK |
| text_direction | 550 | ✓ | ✓ | ✓ OK |
| shadow_severity | 580 | ✓ | ✓ | ✓ OK |
| shadow_type | 620 | ✓ | ✓ | ✓ OK |
| contrast_score | 700 | ✓ | ✓ | ✓ OK |
| overall_quality | 700 | ✓ | ✓ | ✓ OK |
| skew_angle_degrees | 740 | ✓ | ✓ | ✓ OK |
| open_set | 1,095 | ✓ | ✓ | ✓ OK |
| script | 1,095 | ✓ | ✓ | ✓ OK |
| orientation | 1,111 | ✓ | ✓ | ✓ OK |
| blur_score | 1,500 | ✓ | ✓ | ✓ OK |
| noise_score | 1,500 | ✓ | ✓ | ✓ OK |
| compression_score | 1,550 | ✓ | ✓ | ✓ OK |
| handwriting_presence_score | 1,596 | ✓ | ✓ | ✓ OK |
| color_mode | 1,965 | ✓ | ✓ | ✓ OK |
| handwriting_presence | 2,120 | ✓ | ✓ | ✓ OK |
| capture_method | 9,155 | ✓ | ✓ | ✓ OK |

## At-Risk Heads (< 50 labeled images)

The following heads have insufficient labeled coverage for statistically valid evaluation:

- **skew_score**: 0 images acquired
- **handwriting_legibility**: 0 images acquired
- **handwriting_legibility_score**: 0 images acquired
- **resolution_quality**: 0 images acquired
- **code_confidence**: 0 images acquired (model-internal confidence score, no GT field)

## Per-Category Progress

| Category | Acquired | Notes |
|----------|----------|-------|
| ood_script | 1,221 | +446 since last report (CC-OCR: Hang 147, Cyrl 149, Arab 100, Jpan 50 added) |
| ood_geometry | 1,740 | |
| ood_capture | 2,800 | +300 screen-recapture added |
| ood_degradation | 2,930 | |
| ood_handwriting | 1,990 | |
| ood_resolution | 365 | |
| ood_domain | 959 | +100 CC-OCR document_text added |
| ood_code | 500 | +424 code screenshots added |
| ood_mixed | 338 | |

## Script Coverage

| Script | ISO | Count | Status |
|--------|-----|-------|--------|
| Hans (Simplified Chinese) | Hans | 300 | ✓ |
| Latin | Latn | 207 | ✓ |
| Cyrillic | Cyrl | 149 | ✓ NEW |
| Hangul (Korean) | Hang | 147 | ✓ NEW |
| Arabic | Arab | 106 | ✓ |
| Japanese | Jpan | 65 | ✓ |
| Malayalam | Mlym | 24 | ✓ |
| Gurmukhi (Punjabi) | Guru | 21 | ✓ |
| Kannada | Knda | 18 | ✓ |
| Thai | Thai | 12 | ✓ |
| Bengali | Beng | 11 | ✓ |
| Telugu | Telu | 9 | ✓ |
| Devanagari | Deva | 8 | ✓ |
| Oriya | Orya | 8 | ✓ |
| Tamil | Taml | 6 | ✓ |
| Gujarati | Gujr | 4 | ✓ |

## Domain Enrichment

All 9,155 records have been enriched with `enrichment.domain_level1` labels.

| Domain | Count | % | Description |
|--------|-------|---|-------------|
| EDU | 2,724 | 29.8% | Educational / linguistic corpora, handwriting, scripts |
| UNK | 2,070 | 22.6% | DocSynth300K-derived (no category metadata), SD7K manga |
| GOV | 1,264 | 13.8% | Government forms, ID documents, tenders |
| TEC | 975 | 10.6% | Code screenshots, terminals, patents, manuals |
| SCI | 747 | 8.2% | arXiv papers, academic documents |
| FIN | 640 | 7.0% | Financial reports, corporate documents |
| SCN | 500 | 5.5% | Natural scene text (HierText street photos) |
| LGL | 235 | 2.6% | Laws, regulations (DocLayNet) |
| MED | 0 | 0.0% | Not yet acquired |
| REL | 0 | 0.0% | Not yet acquired |

**Inference method breakdown** (deterministic):

- DocLayNet COCO annotation lookup: 1,712 records (FIN/SCI/LGL/TEC/GOV per image)
- Source dataset rule: 3,150 records
- Reason prefix rule: 1,490 records
- Code screenshot generator: 424 records → TEC
- OHR-Bench academic benchmark: 353 records → EDU
- Fixed per-method: 690 records
- DocSynth300K (no category): 650 records → UNK
- Composite shadow chain: 80 records → UNK (DocLayNet through 4a_compound chain)

**UNK breakdown** (1,970 records — requires manual annotation or DocSynth300K enrichment):

- SD7K shadow photos: 1,000 (predominantly Japanese manga/comics, no matching domain)
- albumentations_compound (DocSynth300K): 500
- augraphy_photocopy_4x (DocSynth300K): 200
- pil_watermark (DocSynth300K): 100
- synthetic_composite_shadow: 80
- sauvola_binarize (DocSynth300K): 50
- RealDAE shadow (mixed real documents): 40

## Unresolved Data Gaps

### `handwriting_legibility` — 0 images labeled

Requires human annotation. Legibility cannot be reliably inferred automatically. Assign annotators
to rate: legible=True/False + legibility_score (0–1). Handwriting legibility labels are needed for
images registered via local_dataset_copy (IIIT-INDIC 500, KHATT 400, CASIA-HWDB2 50 images).

### `handwriting_legibility_score` — 0 images labeled

Same as handwriting_legibility — requires human annotation. Score is a continuous 0–1 estimate of legibility.

### `resolution_quality` — 0 images labeled

Requires the resolution_quality labeling pipeline (`scripts/label_resolution_quality.py`).
365 ood_resolution images are registered but unlabeled. Run the PaddleOCR char-height pipeline
over these images on the Vultr A100 VM (207.246.124.234). PaddleOCR v2 only (`paddleocr>=2.7,<3.0`).

### `skew_score` — 0 images labeled

Requires skew classification model inference. Run the trained MobileNetV4 skew head over all
registered images. ~740 geometric images have skew_angle_degrees set; skew_score is the binned
classification equivalent and needs the trained model.

### `code_confidence` — 0 images labeled

This is a model-internal confidence output (not a GT label). No acquisition needed — populated
at inference time.

### Dataset gaps still requiring acquisition

The following planned sources were not downloaded during Phase 3 (no local copy available):

| Sub-source | Dataset | Target images | License | Download URL |
|---|---|---|---|---|
| 2c Japanese vertical | NDL Digital Collection | 100 | Public Domain | dl.ndl.go.jp |
| 3a Screen recaptures | DLC-2021 | 100 | Academic | zenodo.org/record/7467028 |
| 4c Book gutter shadow | Internet Archive + IUPR | 90 | CC0 / Academic | archive.org / L3i lab |
| 4c Historical incunabula | Zaguan/University of Zaragoza | 30 | Public Domain | zaguan.unizar.es |
| 5b CJK handwriting | SCUT-HCCDoc | 100 | Open | github.com/HCIILAB/SCUT-HCCDoc |
| 7a Gov forms | EUR-Lex API | 240 | Public Domain | eur-lex.europa.eu |
| 7b Religious texts | CBETA / Wikimedia | 150 | CC0 / Open | cbeta.org |
| 7c Technical manuals | CORD receipts | 100 | CC-BY-4.0 | github.com/clovaai/cord |
| 1b-1g Script OOD | KhmerST + AMADI_LontarSet + SANA + Georgian | 425 | Academic | L3i lab / ufal.mff.cuni.cz |

**Acquired since plan**: KHATT (400 registered), IIIT-INDIC (500 registered), CC-OCR (546 registered).
**Total unacquired**: ~1,335 images from remaining planned Phase 3 sources.

## License Constraints

- Academic/Research only: ~2,200 entries
- Commercial-OK: ~6,955 entries

**Commercial deployment blocker**: Academic-license entries cannot be used in production without
data refresh. Primary academic sources: WarpDoc (170), RVL-CDIP (100), docalign12k (130), RealDAE (40).

## Recommended Next Steps

### P0 — Label at-risk heads (no new data needed)

- Run `scripts/label_resolution_quality.py` on Vultr A100 VM over ood_resolution/ (365 images)
- Run trained MobileNetV4 skew head for skew_score inference over all 9,155 registered images
- Assign human annotators to handwriting_legibility for IIIT-INDIC/KHATT/CASIA-HWDB2 images
- Populate open_set flag: ✅ DONE (1,095 records set to open_set=False)

### P1 — Fill script head gaps (next session)

- SCUT-HCCDoc CJK handwriting: download from github.com/HCIILAB/SCUT-HCCDoc (~100 images)
- EUR-Lex API government forms: ~240 public domain government documents
- NDL Digital Collection: ~100 Japanese vertical-text images (public domain)

### P2 — Scale toward 12,000 target

- CBETA religious texts: ~150 images (CC0)
- CORD receipts: ~50 non-English camera receipt images (CC-BY-4.0)
- derive-mixed-compounds: ~210 additional OOD-Mixed compound images
- Internet Archive: ~60 book gutter shadow images (CC0)

### P3 — Resolve domain UNK (22.6%)

- Annotate DocSynth300K-derived records (750) with domain labels via contact sheet review
  (sheets saved at `/tmp/ood_domain_review/`)
- Map SD7K records (1,000 manga/comics) to a new ENT (entertainment) domain if added to taxonomy
- Review 40 RealDAE shadow images manually (contact sheet available)

**Current acquisition**: 9,155 / 12,000 (76.3%) — well above P0 gate (7,000). Statistically
rigorous evaluation requires ~12,000 images across all head categories.
