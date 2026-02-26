# OOD Coverage Gap Report

Generated: 2026-02-25 | Registry: 7535 images | Target: 12000 | Progress: 62.8%

## Head Coverage Summary

| Head | Images acquired | Min (50) | Target (100) | Status |
|------|-----------------|----------|--------------|--------|
| skew_score | 0 | ✗ | ✗ | ⚠ AT_RISK |
| open_set | 0 | ✗ | ✗ | ⚠ AT_RISK |
| handwriting_legibility | 0 | ✗ | ✗ | ⚠ AT_RISK |
| handwriting_legibility_score | 0 | ✗ | ✗ | ⚠ AT_RISK |
| resolution_quality | 0 | ✗ | ✗ | ⚠ AT_RISK |
| code_confidence | 76 | ✓ | ✗ | ▲ LOW |
| warping_severity | 100 | ✓ | ✓ | ✓ OK |
| watermark_severity | 100 | ✓ | ✓ | ✓ OK |
| document_age | 110 | ✓ | ✓ | ✓ OK |
| handwriting_content_type | 300 | ✓ | ✓ | ✓ OK |
| warping_type | 300 | ✓ | ✓ | ✓ OK |
| text_direction | 350 | ✓ | ✓ | ✓ OK |
| shadow_severity | 580 | ✓ | ✓ | ✓ OK |
| shadow_type | 620 | ✓ | ✓ | ✓ OK |
| script | 649 | ✓ | ✓ | ✓ OK |
| contrast_score | 700 | ✓ | ✓ | ✓ OK |
| overall_quality | 700 | ✓ | ✓ | ✓ OK |
| handwriting_presence_score | 700 | ✓ | ✓ | ✓ OK |
| skew_angle_degrees | 740 | ✓ | ✓ | ✓ OK |
| orientation | 811 | ✓ | ✓ | ✓ OK |
| handwriting_presence | 1100 | ✓ | ✓ | ✓ OK |
| blur_score | 1200 | ✓ | ✓ | ✓ OK |
| noise_score | 1200 | ✓ | ✓ | ✓ OK |
| compression_score | 1250 | ✓ | ✓ | ✓ OK |
| color_mode | 1665 | ✓ | ✓ | ✓ OK |
| capture_method | 7535 | ✓ | ✓ | ✓ OK |

## At-Risk Heads (< 50 labeled images)

The following heads have insufficient labeled coverage for statistically valid evaluation:

- **handwriting_legibility**: 0 images acquired
- **handwriting_legibility_score**: 0 images acquired
- **open_set**: 0 images acquired
- **resolution_quality**: 0 images acquired
- **skew_score**: 0 images acquired

## Per-Category Progress

| Category | Acquired | Notes |
|----------|----------|-------|
| ood_script | 775 | |
| ood_geometry | 1740 | |
| ood_capture | 2500 | |
| ood_degradation | 2630 | |
| ood_handwriting | 1640 | |
| ood_resolution | 365 | |
| ood_domain | 859 | |
| ood_code | 76 | |
| ood_mixed | 338 | |

## Unresolved Data Gaps

### `handwriting_legibility` — 0 images labeled

Requires human annotation. Legibility cannot be reliably inferred automatically. Assign annotators to rate: legible=True/False + legibility_score (0–1). Handwriting legibility labels are needed for images registered via harvest-train-splits (hiertext, arabic-docs, casia-hwdb2-line).

### `handwriting_legibility_score` — 0 images labeled

Same as handwriting_legibility — requires human annotation. Score is a continuous 0–1 estimate of legibility.

### `open_set` — 0 images labeled

Requires script-detection model inference. open_set=True means the script is outside the model's training vocabulary (Mongolian, Tibetan, Syriac, etc.). Populate from the script field: scripts not in the 9-class training set should be flagged open_set=True. Currently only 99 images have script labels (ood_domain arXiv pages).

### `resolution_quality` — 0 images labeled

Requires the resolution_quality labeling pipeline (`scripts/label_resolution_quality.py`). 365 ood_resolution images are registered but unlabeled. Run the PaddleOCR char-height pipeline over these images.

### `skew_score` — 0 images labeled

Requires skew classification model inference. Run the trained MobileNetV4 skew head over all registered images. ~40 geometric images have skew_angle_degrees set; skew_score is the binned classification equivalent and needs the trained model.

### Dataset gaps still requiring acquisition

The following planned sources were not downloaded during Phase 3 (no local copy available):

| Sub-source | Dataset | Target images | License | Download URL |
|---|---|---|---|---|
| 2c Japanese vertical | NDL Digital Collection | 100 | Public Domain | dl.ndl.go.jp |
| 3a Screen recaptures | DLC-2021 | 100 | Academic | zenodo.org/record/7467028 |
| 4c Book gutter shadow | Internet Archive + IUPR | 90 | CC0 / Academic | archive.org / L3i lab |
| 4c Historical incunabula | Zaguan/University of Zaragoza | 30 | Public Domain | zaguan.unizar.es |
| 5b CJK handwriting | SCUT-HCCDoc | 100 | Open | github.com/HCIILAB/SCUT-HCCDoc (email <eelwjin@scut.edu.cn>) |
| 5b CJK handwriting | CASIA-HWDB | 50 | Academic | nlpr.ia.ac.cn |
| 7a Gov forms | EUR-Lex API | 240 | Public Domain | eur-lex.europa.eu |
| 7b Religious texts | CBETA / Wikimedia | 150 | CC0 / Open | cbeta.org |
| 7c Technical manuals | CORD receipts | 100 | CC-BY-4.0 | github.com/clovaai/cord |
| 1b-1g Script OOD | KhmerST + AMADI_LontarSet + SANA + Georgian | 425 | Academic | L3i lab / ufal.mff.cuni.cz |

**Acquired since plan**: KHATT (1,633 images, benhachem/KHATT on HuggingFace); IIIT-INDIC (95,430 images, c3rl/IIIT-INDIC-HW-WORDS-Hindi on HuggingFace).

**Total unacquired**: ~1,385 images from remaining planned Phase 3 sources.

## License Constraints

- Academic/Research only: 1930 entries
- Commercial-OK: 5605 entries

**Commercial deployment blocker**: 1,280 academic-license entries cannot be used in production without data refresh. Primary academic sources: WarpDoc (170), RVL-CDIP (100), docalign12k (130), RealDAE (40). Muharaf removed (NC license).
**Replacement strategy**: Albumentations MoirePattern (3a), synthetic generation (3b/3d), CC0 Internet Archive (4c).

## Recommended Next Steps

### P0 — Label at-risk heads (no new data needed)

- Run `scripts/label_resolution_quality.py` over ood_resolution/ (365 images)
- Run contrast_score IQA detector over all registered images
- Run trained MobileNetV4 skew head for skew_score inference
- Assign human annotators to handwriting_legibility (hiertext + arabic-docs HW images from harvest-train-splits)
- Populate open_set flag from script field for all 99 labeled-script images

### P1 — Fill high-priority dataset gaps (Week 1)

- Download SCUT-HCCDoc (open access, github.com/HCIILAB/SCUT-HCCDoc): 100 CJK HW images
- Send KHATT license request (khatt.ideas2serve.net): 200 Arabic cursive images
- Download IIIT-INDIC Devanagari (cvit.iiit.ac.in): 100 Devanagari HW images
- Request DLC-2021 (zenodo.org/record/7467028): 100 screen recapture images

### P2 — Scale toward 12,000 target (Week 2+)

- EUR-Lex API: ~240 government form images (public domain)
- NDL Digital Collection: ~100 Japanese vertical-text images
- Internet Archive: ~60 book gutter shadow images (CC0)
- CORD receipts: ~50 non-English camera receipt images (CC-BY-4.0)
- CASIA-HWDB: 50 CJK handwriting images (after NLPR access approval)
- KhmerST + AMADI_LontarSet: ~100 script OOD images (L3i lab)
- derive-mixed-compounds: ~210 additional OOD-Mixed compound images

**Current acquisition**: 7,535 / 12,000 (62.8%) — minimum viable P0 gate passed. Directional evaluation feasible; statistically rigorous evaluation requires ~12,000 images.
