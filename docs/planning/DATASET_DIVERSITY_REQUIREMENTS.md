# Training Dataset Diversity Requirements for MobileNetV4 + SigLIP 2

## Context

The approved model requirements plan ([SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md)) specifies two models needing training datasets: **MobileNetV4-Conv-S** (3 heads, fast pre-correction) and **SigLIP 2 NAFlex** (19 heads across 5 groups). This document defines the **diversity characteristics** each training dataset must exhibit to ensure robust generalization to unseen production documents.

**Related**: [TRAINING_OPTIMIZATION_PLAN.md](TRAINING_OPTIMIZATION_PLAN.md) -- Training optimization strategy (ILP allocation, multi-task loss balancing, phased head training, active learning)

Production will encounter documents from any domain, any script, any capture method, any degradation level. Models trained on narrow data distributions will fail silently on underrepresented categories. This plan specifies target distributions, stratification strategies, quality thresholds, and verification metrics for every training dataset.

### Available Diversity Dimensions (Layer 2 Enrichment Schema)

From [layer2_enrichment_v6.schema.json](docs/schema/layer2_enrichment_v6.schema.json) (v6, 132 fields — updated 2026-02):

| # | Dimension | Values | Relevance |
|---|-----------|--------|-----------|
| 1 | capture_method | born_digital, scanner_flatbed, scanner_adf, camera_professional, camera_smartphone, fax, synthetic | How the image was captured affects noise, perspective, shadows |
| 2 | domain | TAX, LEG, FIN, TEC, SCI, ADM, MED, EDU, PER, UNK | Document industry/purpose |
| 3 | script_code | 33 ISO 15924 codes -> 19 ML classes | Writing system |
| 4 | script_family | latin, cjk, arabic, indic, cyrillic, other | High-level script grouping |
| 5 | resolution | low_<150, medium_150-299, standard_300, high_>300 | Image quality baseline |
| 6 | text_density | sparse, moderate, dense | Amount of text content |
| 7 | layout_type | single_column, multi_column, complex, form_based, tabular | Page structure |
| 8 | content_flags | has_table, has_formula, has_handwriting, has_signature, has_figure | Content presence |
| 9 | degradation | blur, noise, skew, contrast, compression, bleed_through (severity 0-1) | Image quality issues |
| 10 | content_type | printed, handwritten, mixed, scene_text, synthetic | Text rendering method |
| 11 | handwriting | presence (5 levels), legibility (6 levels), content_type (7 types) | Handwriting assessment |
| 12 | paper_size | A4, Letter, Legal, etc. | Physical document size |
| 13 | **color_mode** | binarized, grayscale, color | **NEW (consensus)**: Binary images lack texture cues CNNs/ViTs rely on |
| 14 | document_age | modern, aged, historical | **NEW (consensus)**: Affects degradation patterns and paper quality |

### Current Metadata Coverage Reality

> **Updated**: 2026-02-21 (post-audit sprint, 58 datasets scored)

| Dimension | Datasets with Data | Key Gap |
|-----------|-------------------|---------|
| capture_method | 57/58 aggregates | 8 D-capped datasets need domain enrichment (GPU) |
| domain | 50/58 (8 capped at 0-65% domain_level1) | mdiw13, arabic-docs-ocr, siw13, cc-ocr, omnidocbench, muharaf, jssoda, docalign12k need GPU enrichment |
| script_code | 45/58 (via script_family) | CJK, Cyrillic weak in IQA datasets; synth-multiscript generating |
| quality/degradation | 12/58 (IQA-specific datasets) | Shadow/warping now have dedicated datasets (sd7k, wsrd, warpdoc) |
| content_flags | 51/58 (VLM inspection complete) | KI-002, KI-003, KI-006 require manual verification |

**Audit completion**: 58/58 datasets scored (100%) | Mean score: 84.1 | 43 at B+ (74%) | 8 D-capped (domain gap) | 1 F-grade (iam needs base metadata)

---

## 1. Orientation Dataset (50K) -- REBUILDING (Stream 4C)

**Model**: MobileNetV4 Head 1 + SigLIP Group 3
**Task**: 4-class classification (0/90/180/270)
**Status**: REBUILDING as hybrid (Stream 4C, 2026-02). Old 50K dataset at `E:\03_training_datasets\orientation\`
lacked multi-script diversity. New 50K hybrid: ≥60% real (DocLayNet + RVL-CDIP rotated) + ≤40% v3 synthetic
(non-Latin scripts). Scripts: `build_orientation_real_component.py` + `derive_v3_orientation_view.py`.

**Real/Synthetic Mixing**: ≥60% real documents (30K+), ≤40% v3 synthetic (≤20K, non-LATN scripts only).
**Provenance field values**: `real_born_digital`, `real_scan`, `synthetic_v3`.

### 1.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Orientation class** | CRITICAL | 25% each (0/90/180/270) | 12,500 each |
| **Capture method** | IMPORTANT | 45% born_digital, 25% scanner, 20% camera, 10% synthetic | 1,250 each |
| **Script family** | IMPORTANT | 50% Latin, 12% Arabic, 8% CJK, 6% Devanagari, 8% Japanese vertical, 16% mixed | 375 per script |
| **Domain** | NICE-TO-HAVE | 16% SCI, 12% FIN, 12% forms, 8% receipts, 12% tables, 8% legal, 8% handwritten, 24% mixed | 500 per domain |
| **Layout complexity** | IMPORTANT | 40% single_col, 30% multi_col, 15% form/tabular, 15% complex | 900 per type |
| **Resolution** | NICE-TO-HAVE | 30% standard_300, 30% medium, 20% high, 20% low | 600 per bin |
| **Degradation** | IMPORTANT | 50% clean, 35% light, 15% moderate | 1,875 moderate |

### 1.2 Stratification

- **Split**: 70/15/15 by SOURCE DOCUMENT ID before rotation (prevents leakage)
- **Primary axes**: document_type (11 categories), source_dataset, script_family
- **Rare handling**: Japanese vertical (1,050 sources), Devanagari (700 sources) -- small but adequate
- **Labels**: tier_0_exact (ground truth by construction via rotation)

### 1.2.1 Symmetric and Ambiguous Document Handling (Gaps 2 + 13 — P0)

**Symmetric documents** (visually identical at 0° and 180°) and **blank/figure-only pages** (no
orientation cues) are an epistemic impossibility for a pure 4-class classifier: the signal
required to resolve orientation is absent from the image. These must be explicitly labeled and
handled, not ignored.

**Required sub-categories (~5% of dataset, ~2,500 samples)**:

| Sub-category | Target Count | Label | Source |
|-------------|-------------|-------|--------|
| Blank pages (no text) | ~750 (1.5%) | `orientation_ambiguous` | DocLayNet blank separator pages; blank PDFs |
| Figure/chart-only pages | ~500 (1%) | `orientation_ambiguous` | DocLayNet picture-dominant pages |
| Symmetric content (centered title, palindromic table, numeric-only) | ~750 (1.5%) | `orientation_ambiguous` | Curated from DocLayNet + RVL-CDIP |
| Very sparse text (< 5 words, no paragraph structure) | ~500 (1%) | `orientation_ambiguous` | Curated with confidence_flag |

**Handling rules**:

1. The orientation head outputs `confidence_flag: ambiguous` when symmetric/blank inputs are detected
2. Default prediction for ambiguous inputs: `orientation_class=0` with `confidence < 0.4`
3. The two-stage pipeline (MobileNetV4 ambiguity detection → SigLIP 2 if unambiguous) handles this at inference
4. Integration with script detection: if `script=UNKNOWN` AND orientation requested, apply confidence dampening
5. Do NOT fold ambiguous documents into the primary 4-class training loss — use a separate binary head or confidence-suppression target

**Evaluation requirement**: Accuracy metrics reported SEPARATELY for standard (non-ambiguous) vs.
ambiguous documents. Do not include ambiguous documents in the primary orientation accuracy metric —
they inflate noise. Instead, report ambiguous-class abstention rate (target: ≥85% of ambiguous
inputs flagged as low-confidence).

### 1.3 Source Composition (Hybrid Rebuild — Stream 4C)

| Component | Count | Source | Labels | Provenance |
|-----------|-------|--------|--------|------------|
| Real (DocLayNet PDFs, rotated) | ~32K | `gs://image_detection_b/01_base_data/document_understanding/doclaynet/` (PDFs) | tier_0_exact (rotation by construction) | `real_born_digital` |
| Real (RVL-CDIP scans, rotated) | ~12K | `gs://image_detection_b/01_base_data/document_understanding/rvlcdip/` | tier_0_exact (rotation by construction) | `real_scan` |
| Synthetic (v3 non-LATN) | ~20K | `gs://image_detection_b/synth_multiscript_v3/` — 19 non-Latin scripts | tier_0_exact (orientation_class from v3 sidecar) | `synthetic_v3` |
| **Total** | **~50K** | | | |

Source mix: ~88% real / ~12% real-rotated / ≤40% synthetic. Domain-cap per real source (50% max).
Script coverage: 19 non-Latin scripts via v3 component. Resize all images to 224px (INTER_AREA).

**Status**: IN PROGRESS (Stream 4C scripts written, execution pending data transfer).

---

## 2. Skew Regression Dataset (90K) -- COMPLETE

**Model**: MobileNetV4 Head 2 + SigLIP Group 3
**Task**: Continuous regression (±10°, target <0.5° residual)
**Status**: Ready at `gs://image_detection_b/skew_training/` and `E:\03_training_datasets\skew\` (2.2GB)
**Actual size**: 90,412 images (71,498 synthetic + 18,914 natural scans)
**Split**: Train=70,763 / Val=9,025 / Test=10,624
**Best model result**: MobileNetV4-Conv-S @ 224px, 50 epochs: val MAE=0.837, test MAE=0.956, SRCC=0.936, orient_acc=99.5%, CPU 17.5ms

### 2.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Skew angle** | CRITICAL | Near-uniform over [-10°, +10°]; see bins below | 400 per 0.5° bin |
| **Skew source** | CRITICAL | 62.5% synthetic rotation (25K), 12.5% natural scan (5K), 25% synthetic+degraded (10K) | 5,000 natural |
| **Capture method** | IMPORTANT | 50% scanner (natural skew source), 30% born_digital+rotation, 20% camera | 2,000 camera |
| **Script family** | IMPORTANT | 50% Latin, 15% CJK/Arabic/Indic, 20% mixed | 300 per non-Latin |
| **Text density** | IMPORTANT | 30% sparse, 40% moderate, 30% dense | 3,000 per bin |
| **Degradation** | IMPORTANT | 50% clean, 25% light, 25% moderate-heavy | 2,500 moderate+ |
| **Resolution** | NICE-TO-HAVE | 30% low, 40% standard, 30% high | 3,000 per bin |
| **Layout type** | **IMPORTANT** | ≥20% multi-column, 40% single-col, 20% form/tabular, 20% complex | **18,000 multi-column** |

> **Gap 7 note**: Multi-column documents are a RAG-pipeline-critical case. Global skew deskewing
> on a multi-column layout shears text lines along column gutters — this is an active quality
> REDUCTION, not a neutral preprocessing step. The skew model must learn layout-aware estimation
> or correctly abstain for multi-column inputs. Elevating layout_type to IMPORTANT and requiring
> ≥20% multi-column samples is the minimum data-side remediation. See Section 2.3 for the
> cross-detector agreement gate.

### 2.2 Angle Distribution (CRITICAL)

```text
Bin [-10, -5]:    5,000 (12.5%) -- extreme negative
Bin (-5, -2]:     8,000 (20%)   -- moderate negative
Bin (-2, -0.5]:   7,000 (17.5%) -- mild negative (correction-critical range)
Bin (-0.5, 0.5]:  5,000 (12.5%) -- near-zero (hardest to distinguish)
Bin (0.5, 2]:     7,000 (17.5%) -- mild positive (correction-critical range)
Bin (2, 5]:       5,000 (12.5%) -- moderate positive
Bin (5, 10]:      3,000 (7.5%)  -- extreme positive
```

More samples in the mild range (±0.5-2°) because that's where sub-0.5° accuracy matters most for correction quality.

### 2.3 Stratification

- **Split**: 70/15/15 by source document ID
- **Primary axes**: skew_angle_bin (7 bins), skew_source (synthetic/natural/degraded), script_family
- **Leakage prevention**: Same source document at different angles must be in SAME split
- **Natural scan labels**: Hough-derived + line-based cross-validation; accept only if both agree within 0.5°
- **Multi-column label quality gate (Gap 7 — MANDATORY)**: For multi-column layout documents, Hough + projection-profile cross-detector agreement within 0.5° is REQUIRED before accepting the label. Global projection profiles fail on multi-column layouts (column gutters create false optima). Reject multi-column samples with cross-detector disagreement > 0.5° rather than accepting with uncertainty. Do NOT apply uncertainty-based soft labels to multi-column disagreement — the measurement itself is invalid.
- **Multi-column evaluation metric**: Report skew MAE separately for single-column vs. multi-column documents. Acceptable: multi-column MAE ≤ 1.5× single-column MAE. If multi-column MAE > 2.0× single-column, trigger alert and investigate layout-aware estimation approach.

### 2.4 Source Composition (ACTUAL)

| Component | Count | Source | Labels | Status |
|-----------|-------|--------|--------|--------|
| Clean docs + synthetic rotation | 71,498 | DocLayNet, FUNSD, SROIE, Arabic, MDIW13, MLT19, JSSoDa and others | tier_0_exact angle | ✅ Complete |
| Naturally skewed scans | 18,914 | 13 real-scan datasets; classical ensemble labeling, conf >= 0.7 | Hough-derived (tier_2_model) | ✅ Complete |
| **Total** | **90,412** | 384x384 JPEG q90, ProcessPoolExecutor 4 workers, 11.4 img/s | | ✅ Complete |

### 2.5 Quality Thresholds

- **Synthetic labels**: tier_0_exact, confidence 1.0
- **Natural scan labels**: tier_2_model, accept only if Hough AND line-based agree within 0.5°
- **Disagreement handling**: Store as soft labels with uncertainty; use GaussianNLL loss
- **Loss function**: SmoothL1 on angle + optional GaussianNLL for uncertainty

---

## 3. Resolution Quality Dataset (30K) -- IN PROGRESS (5.5K done)

**Model**: MobileNetV4 Head 3 + SigLIP Group 5
**Task**: Regression (0-1, character-height-aware)
**Status**: 5,499 images labeled from DIQA-5000 via PaddleOCR DBNet + CC pipeline. Expanding to OHR-Bench (8.5K) and RealDAE (1.2K) next.
**V1 precision note**: Median IQR 9.0px (target 2-3px); V2 strategy (Sauvola + projection profiles) underway. See [RESOLUTION_QUALITY_V2_STRATEGY.md](RESOLUTION_QUALITY_V2_STRATEGY.md).

### 3.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Resolution quality score** | CRITICAL | Uniform bins 0.0-1.0 (10 bins, 3K each) | 3,000 per 0.1 bin |
| **DPI level** | CRITICAL | 15% each: 72, 100, 150, 200, 300; 10% each: 400, 600; 5% >600 | 1,500 per level |
| **Capture method** | IMPORTANT | 40% born_digital (PDF renders), 30% scanner, 20% camera, 10% synthetic | 1,500 camera |
| **Script family** | IMPORTANT | 50% Latin, 15% CJK, 10% Arabic, 10% Indic, 15% mixed | 1,500 CJK |
| **Text density** | CRITICAL | 25% sparse, 35% moderate, 25% dense, 15% very_dense | 1,500 very_dense |
| **Content flags** | NICE-TO-HAVE | >=15% has_formula, >=10% has_table | 1,000 with formula |

### 3.2 Character Height -> Quality Score Mapping

```text
char_height < 16px:    quality = 0.00-0.15  (needs major upscaling)
char_height 16-24px:   quality = 0.15-0.35  (needs light upscaling)
char_height 24-32px:   quality = 0.35-0.55  (acceptable for Latin; INSUFFICIENT for CJK — see below)
char_height 32-48px:   quality = 0.55-0.75  (optimal OCR range)
char_height 48-64px:   quality = 0.75-0.85  (good, slightly oversized)
char_height 64-96px:   quality = 0.85-0.95  (oversized)
char_height > 96px:    quality = 0.95-1.00  (definitely oversized)
```

**Critical limitations of this mapping (Gaps 3 + 4)**:

1. **Script-specific minimums (Gap 4)**: CJK requires ≥30px (optimal 40+px) for glyph-component
   legibility. At 24-30px, CJK is illegible while Latin at the same height is marginal-acceptable.
   The table above is calibrated for Latin — apply script-aware adjustment at inference:
   - CJK (HANS/HANT/JPAN/KORE): char_height < 30px → quality_score × 0.55 before returning
   - Devanagari/Arabic/Tibetan: char_height < 24px → quality_score × 0.65
   - These adjustments live in the inference logic layer; they do NOT require model retraining

2. **Confound cases — char_height measurement is INVALID (Gap 3)**:
   - **Pre-upscaled rasters**: Bicubic upscaling inflates CC bounding boxes — measured char_height
     reads artificially high (e.g., 48px appears OK) but the image has low information density
     (blurry, low-sharpness at the measured height). See Section 3.4 confound sub-dataset.
   - **Vector PDFs**: Vector text renders correctly at any DPI. char_height measurement looks fine
     at low output DPI, but OCR on the rasterized image fails because the effective resolution is
     below threshold. These must be labeled by `effective_render_dpi`, not char_height alone.

3. **Raw physical metric output (Gap 4 fix)**: The resolution head MUST output raw physical metrics
   alongside quality_score: `pixel_height`, `stroke_width`, `contrast_ratio`. These raw values
   enable script-aware and confound-aware threshold updates in the inference logic layer without
   model retraining. The quality_score composite is a convenience output; raw metrics are the
   authoritative measurement.

### 3.3 Stratification

- **Split**: 70/15/15 by source document ID
- **Primary axes**: dpi_level, text_density, script_family
- **Leakage prevention**: doc_A at 72 DPI and doc_A at 300 DPI must be in SAME split
- **Character height measurement**: Connected component analysis + text line detection (existing `iqa_classical.py`)

### 3.4 Source Composition

| Component | Count | Source | Process |
|-----------|-------|--------|---------|
| Multi-DPI renders | 20,000 | DocLayNet (5K) + FUNSD/SROIE/NIST (2K) + MDIW13 (3K) | Render at 72/100/150/200/300/400/600 DPI |
| Camera capture (real) | 5,000 | SmartDoc-QA (4.3K) + RealDAE (1.2K) + MIDV500 (3.6K) | Already at various resolutions; label by measured char height |
| Synthetic variable-res | 5,000 | synth-multiscript-v3 (sample) | Render at controlled DPI with known char heights |
| **Confound sub-dataset (Gap 3 — REQUIRED)** | **~2,000** | Upscaled rasters + vector PDF effective DPI | See below |

**Confound sub-dataset details**:

| Confound Type | Count | Generation | Labels |
|--------------|-------|-----------|--------|
| Pre-upscaled rasters | ~1,000 | Take 72/100 DPI images → bicubic 2×-4× upscale → measure inflated char_height vs. true sharpness | `upscale_factor`, `true_dpi`, `artificially_upscaled=True`, `measured_char_height`, `actual_quality` |
| Vector PDF at low effective DPI | ~500 | Render same PDF source at 72 DPI and 300 DPI; label by `effective_render_dpi` | `effective_render_dpi`, `source_type=vector_pdf`, `quality_score_by_dpi` |
| Mixed confound | ~500 | Upscale a scanned image (stacked: both confounds) | Both labels set |

These confound samples teach the model to distinguish between "large char_height → high quality"
(valid) and "large char_height from upscaling → low actual quality" (confound). The confound
sub-dataset is mandatory before resolution head training.

### 3.5 Quality Thresholds

- **Synthetic DPI labels**: tier_0_exact, confidence 1.0
- **Character height labels**: tier_3_heuristic (connected component estimation), accept if confidence >= 0.6
- **OCR-validated**: Cross-validate resolution quality against OCR accuracy where available (SmartDoc-QA)

---

## 4. IQA Dataset (~16K hard labels + up to 100K pseudo-labeled)

**Model**: SigLIP Group 1
**Task**: 6 regression heads (blur, noise, contrast, skew_severity, compression, overall)

### 4.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Quality score range** | CRITICAL | Full 0-1 range; avoid midrange clustering | 500 per 0.1 bin |
| **Degradation type** | CRITICAL | All 6 types with severity > 0.3 | 500 per type |
| **Capture method** | CRITICAL | 30% born_digital, 30% scanner, 25% camera, 15% mixed | 1,000 camera |
| **Script family** | IMPORTANT | 60% Latin, 15% CJK, 10% Arabic, 15% other | 500 non-Latin |
| **Domain** | IMPORTANT | >= 5 domains with >= 5% each | 300 per domain |
| **Text density** | IMPORTANT | 30% sparse, 40% moderate, 30% dense | 1,000 per bin |

### 4.2 Coverage Gaps (CRITICAL)

| Gap | Impact | Severity |
|-----|--------|----------|
| **Compound/multi-degradation samples: NONE** | **15-25% expected metric drop on real-world data; blur+skew+noise compound is fundamentally harder than any single degradation — signals overlap and disentanglement fails** | **CRITICAL (Gap 1)** |
| Camera-captured IQA: ~~only RealDAE (583)~~ ✅ Fixed (8,475 camera samples) | Camera has different quality characteristics than scanner | ~~HIGH~~ ✅ Resolved (added SmartDoc-QA + MIDV500) |
| Script diversity: 0% script metadata on IQA datasets | Cannot verify script-fairness; CJK and Arabic IQA likely systematically mislabeled | HIGH |
| Domain diversity: 100% UNK in DIQA-5000 and OHR-Bench | Cannot assess industry bias | MEDIUM |

### 4.3 Source Composition

**Phase 1 (16K, hard labels)**:

| Dataset | Train | Val | Test | Labels | Provenance |
|---------|-------|-----|------|--------|------------|
| DIQA-5000 | 4,400 | 550 | 550 | 3-dim MOS (1-5) | tier_1_annotation |
| OHR-Bench | 6,849 | 856 | 856 | Quality 0-100 | tier_1_annotation |
| RealDAE | 480 | 60 | 60 | Before/after pairs | tier_1_annotation |
| SmartDoc-QA | 3,424 | 428 | 428 | Camera quality (heuristic) | tier_3_heuristic |
| MIDV500 | 2,890 | 361 | 361 | Camera quality (heuristic) | tier_3_heuristic |
| OCR-Quality | 800 | 100 | 100 | Human quality 1-4 | tier_1_annotation |
| **Total** | **20,123** | **2,515** | **2,515** | | |

**CONSENSUS UPDATE**: Added SmartDoc-QA (4,280) and MIDV500 (3,612) to Phase 1 hard labels to address the critical camera-captured IQA gap (was 583 samples, now ~8,475 camera). These provide smartphone/professional camera diversity with natural shadows, perspective, and lighting variation. Labels derived from paired/heuristic quality assessment at tier_3_heuristic with training weight 0.5.

**Phase 1B (~3K-5K, compound distortion sub-split — REQUIRED, Gap 1 remediation)**:

A compound distortion sub-split is mandatory before training the IQA head. Real-world documents
have simultaneous degradations; models trained only on single-condition samples fail on compound
inputs with 15-25% expected metric drop.

| Component | Count | Stacked Degradations | Base Images |
|-----------|-------|---------------------|-------------|
| blur + JPEG compression | 1,000-1,500 | Gaussian/motion blur → JPEG Q=30-50 | DIQA-5000/OHR-Bench clean samples (quality ≥ 0.6) |
| blur + noise | 800-1,000 | Gaussian blur → add Gaussian noise | DIQA-5000/OHR-Bench |
| noise + contrast reduction + JPEG | 600-800 | Noise → contrast degradation → JPEG | OHR-Bench clean samples |
| shadow + blur (camera domain) | 600-800 | Shadow overlay → motion blur | SmartDoc-QA / RealDAE base |
| blur + skew + noise (three-way) | 400-600 | Rotation → blur → noise | DIQA-5000 clean |

- **Pipeline**: Albumentations stacked transforms; severity for each component sampled independently
- **Labels**: Per-component severity fields (`blur_severity`, `noise_severity`, etc.); NO single compound score
- **Training weight**: 1.0 (full weight — compound conditions require full signal, not soft labels)
- **Held-out evaluation**: A SEPARATE compound distortion test split (not in training) is MANDATORY for IQA head evaluation. This is in addition to the standard val/test splits.
- **Important**: Compound samples must be Phase 1B (hard labels), NOT folded into Phase 2 pseudo-labels.

**Phase 2 (up to 100K, pseudo-labels via DocIQ-Replica)**:

- Source from DocLayNet, RVL-CDIP, Tobacco800, SmartDoc-QA (provides capture/script diversity)
- Only include pseudo-labeled samples with confidence >= 0.7
- Training weight = 0.5 * confidence (soft labels)

### 4.4 Quality Thresholds

- **Hard labels**: tier_1_annotation, confidence >= 0.9, full training weight (1.0)
- **Pseudo-labels**: tier_2_model, confidence >= 0.7, training weight = 0.5 * confidence
- **Reject**: Any sample with prediction confidence < 0.5

---

## 5. Script Detection Dataset (~108K from ~583K available)

**Model**: SigLIP Group 2
**Task**: Multi-class classification targeting full OpenLID coverage. Phase 1 launches with 19
initial ML classes (`config/script_ml_classes.yaml`); the previously deferred "Phase 2" OpenLID
expansion (~60+ scripts) is **merged into Phase 1** and committed as a single deployment scope.
Three scripts are permanently excluded from training and reserved exclusively for OOD holdout evaluation:

> **RESERVED SCRIPTS — NEVER IN TRAINING**: Mongolian (Mong), Syriac (Syrc), Georgian (Geor).
> These are the TTB/RTL/LTR OOD anchor scripts. They must not appear in any training manifest
> even after Phase 2 OpenLID expansion. The `_validate_no_reserved_scripts()` guard in
> `prepare_multitask_datasets.py` enforces this at manifest generation time.
> See [OOD Dataset Design](OOD_DATASET_DESIGN.md#script-reservation-policy).

### 5.1 Script Class Targets

| ML Class | Target % | Target Count | Available | Primary Sources | Gap Status |
|----------|----------|-------------|-----------|-----------------|------------|
| LATN | 30% | 30,000 | >100K | DocLayNet, COCO-Text, MDIW13, synth-multiscript | Oversupplied; downsample |
| ARAB | 10% | 10,000 | ~35K | Arabic Docs, Muharaf, Yarmouk, MDIW13 | OK |
| DEVA | 7% | 7,000 | ~85K | MDIW13, Hindi-synth, Nepal handwritten | OK |
| HANS | 6% | 6,000 | ~15K | synth-multiscript, COCO-Text CJK | Tight |
| HANT | 3% | 3,000 | ~5K | synth-multiscript | Tight |
| JPAN | 6% | 6,000 | ~10K | synth-multiscript, JSSODA, MLT19 | OK |
| KORE | 4% | 4,000 | ~8K | synth-multiscript, MLE2E | OK |
| CYRL | 5% | 5,000 | ~10K | MDIW13, synth-multiscript | OK |
| THAI | 3% | 3,000 | ~5K | synth-multiscript | Tight |
| TIBT | 4% | 4,000 | ~145K total (TibHCR chars + bhutan-afs + synth) | TibHCR (chars), bhutan-afs (B 83.5), synth-multiscript | Tight (P1) |
| HEBR | 3% | 3,000 | ~5K | synth-multiscript | Tight |
| GREK | 2% | 2,000 | ~3K | synth-multiscript | Tight |
| BENG | 3% | 3,000 | ~8K | MDIW13, synth-multiscript | OK |
| TAML | 2% | 2,000 | ~5K | MDIW13, synth-multiscript | OK |
| TELU | 2% | 2,000 | ~5K | MDIW13, synth-multiscript | OK |
| INDIC_OTHER | 3% | 3,000 | ~10K | MDIW13, synth-multiscript | OK |
| SE_ASIAN_OTHER | 2% | 2,000 | ~3K | synth-multiscript | Tight |
| OTHER | 3% | 3,000 | ~5K | synth-multiscript | OK |
| UNKNOWN | 2% | 2,000 | Derive from no-text pages | DocLayNet figure-only, blank pages | Need curation |

> **Note on absent scripts**: Mongolian (Mong), Syriac (Syrc), and Georgian (Geor) are
> intentionally absent from this table. These 3 scripts are OOD-reserved (see section header
> above) and must not be added to training even if sources become available or Phase 2
> OpenLID expansion includes them.

### 5.2 Diversity Requirements (beyond script class)

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Capture method** | IMPORTANT | 30% scanner, 25% camera, 30% synthetic, 15% born_digital | 10,000 camera |
| **Text scope** | CRITICAL | 20% character, 25% word, 20% line, 35% page/document | 5,000 character |
| **Content type** | IMPORTANT | 40% printed, 30% handwritten, 20% scene_text, 10% synthetic | 10,000 handwritten |
| **Resolution** | IMPORTANT | 30% low, 40% standard, 30% high | 10,000 low-res |
| **Degradation** | NICE-TO-HAVE | 60% clean, 25% light, 15% moderate | 5,000 moderate |

### 5.3 Critical Gaps

1. **Tibetan page-level**: TibHCR has 141K character images but ~0 full-page documents. Only ~200 real Bhutan docs + ~3.8K synthetic page-level from synth-multiscript. **CONSENSUS: Elevated to P1 priority** -- 200 real samples insufficient for production robustness; pursue partnerships with digital library projects (e.g., BDRC, Tibetan Buddhist Resource Center) for real page scans
2. **HANS/HANT distinction**: Requires curated data; synth-multiscript is primary source. **CONSENSUS**: Consider a dedicated HANS/HANT binary classifier as a second-stage gate after CJK detection, since visual distinction is subtle and error-prone with single-pass classification
3. **Hebrew, Greek, Thai, SE_ASIAN_OTHER**: All depend heavily on synth-multiscript-v3 (v2 at 250K DELETED; v3 at 190,485 actual — ⚠️ imbalanced; Hebrew/Greek/Thai may be under-represented)
4. **OpenLID expansion (Phase 1 commitment)**: The initial 19 ML classes are the first batch.
   Full OpenLID coverage (~60+ ISO 15924 scripts) is **committed as Phase 1 scope** — there is
   no separate "Phase 2" for script expansion. Script class config (`config/script_ml_classes.yaml`)
   is updated incrementally as new script training data is assembled. After each batch is added,
   OOD-Script must be re-evaluated: scripts transitioning from open-set to in-training lose their
   OOD-Script status (they may still appear in other OOD categories). Reserved scripts
   (Mong/Syrc/Geor) are excluded from ALL expansion batches.

   **Coverage strategy for scripts not yet in training**: Confidence abstention routes to the
   classical OpenLID language → script mapping when a script is not yet in the training set.
   This is a production safety mechanism only — it does NOT substitute for actual training data.
   Each OpenLID expansion batch requires real training data sourcing before that batch trains.
   Abstention thresholds apply per Section 17.3.
5. **Font variation coverage**: The 19 Phase 1 classes cover standard font representations. Highly
   decorative or non-standard fonts within trained scripts (e.g., ornamental Latin, CJK brush
   style) are underrepresented. These are covered by OOD-Script font variation sub-set rather
   than in training data, but future training phases should include curated decorative font
   samples to improve production robustness. See
   [OOD Dataset Design — Font Variation](OOD_DATASET_DESIGN.md#font-variation-ood-strategy).

### 5.4 Stratification

- **Split**: 70/15/15 by source identity
- **Primary axes**: ml_class (19), text_scope (char/word/line/page), content_type (printed/handwritten/scene)
- **Leakage prevention**: MDIW13 doc/line/word from same source -> same split; COCO-Text by COCO image ID
- **Benchmarks reserved**: MLT19 val/test, COCO-Text val/test (never in training)
- **OOD reserved**: Mong/Syrc/Geor scripts never in training (see reserved script guard)
- **OOD leakage check**: `_check_ood_leakage()` runs on every manifest before write; SHA256 + pHash (Hamming ≤ 5) against `metadata_registry/ood_registry.jsonl`
- **Rare class handling**: Tibetan 5-fold CV on ~200 real samples; Hebrew/Greek accept up to 80% synthetic; class weights from script_ml_classes.yaml (TIBT=2.0, SE_ASIAN_OTHER=1.8, GREK=1.5)
- **Holdout evaluation**: See [OOD Dataset Design](OOD_DATASET_DESIGN.md) for the ~4,700-image holdout set (9 categories) used for final production evaluation, including open-set rejection metrics for scripts not in training

### 5.5 Source Composition

| Source | Samples Used | Scripts | Selection Strategy |
|--------|-------------|---------|-------------------|
| synth-multiscript-v3 | ~60K | 27 scripts | Stratified sample matching target class distribution (⚠️ rebalance before use) |
| MDIW13 train | ~30K (from 232K) | 13 scripts | Stratified by script; real handwritten diversity |
| COCO-Text train | ~5K (from 43K) | Mixed | Select non-Latin preferentially; scene text domain |
| Arabic Docs OCR | ~3K | Arabic | Stratified across 12 doc types |
| SIW13 | ~3K | 13 scripts | Supplement rare scripts |
| CVSI | ~2K | 10 scripts | Video scene text domain |
| TibHCR (composites) | ~2K | Tibetan | Create pseudo-page images from character composites |
| Hindi-synth | ~2K | Devanagari | Printed Devanagari diversity |
| MLE2E | ~1K | 4 scripts (incl. Korean) | Pre-segmented crops |

### 5.6 Quality Thresholds

| Source Type | Provenance | Min Confidence | Training Weight |
|-------------|-----------|----------------|-----------------|
| Ground truth script labels (MDIW13, SIW13) | tier_1_annotation | >= 0.9 | 1.0 |
| Synthetic script labels (synth-multiscript) | tier_0_exact | 1.0 | 1.0 |
| OpenLID-derived labels (COCO-Text) | tier_2_model | >= 0.8 | 0.8 |
| Scene text labels (CVSI) | tier_1_annotation | >= 0.9 | 1.0 |
| TibHCR character composites | tier_3_heuristic | N/A | 0.7 |

---

## 6. Handwriting Assessment Dataset (~60K)

**Model**: SigLIP Group 4
**Task**: 3 classification heads (presence 5-class, legibility 6-class, content_type 7-class) + 2 regression (presence_score, legibility_score)

### 6.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Presence class** | CRITICAL | NONE 35%, SPARSE 15%, MODERATE 20%, SUBSTANTIAL 15%, DOMINANT 15% | 3,000 per non-NONE |
| **Legibility class** | CRITICAL | NOT_APPLICABLE 35%, EXCELLENT 15%, GOOD 20%, FAIR 15%, POOR 10%, ILLEGIBLE 5% | 1,000 ILLEGIBLE |
| **Content type** | CRITICAL | not_applicable 35%, signatures 10%, numeric 10%, alphanumeric 15%, prose 20%, mixed 8%, specialized 2% | 500 specialized |
| **Script family** | IMPORTANT | 40% Latin, 15% Arabic, 10% Devanagari, 10% CJK, 25% other | 2,000 Arabic |
| **Capture method** | IMPORTANT | 40% scanner, 30% born_digital (negatives), 20% camera, 10% mixed | 3,000 camera |
| **Degradation** | NICE-TO-HAVE | 60% clean, 25% light, 15% moderate | 2,000 moderate |

### 6.2 Negative Sampling (NONE class = ~35%)

~22K printed-only pages required for class balance:

- DocLayNet train: sample 15K (80K available, printed-only)
- PubTabNet train: sample 5K (500K available, tables-only)
- FinTabNet: sample 2K (97K available, financial tables)

### 6.3 Label Harmonization (CRITICAL prerequisite)

| Source | Raw Labels | -> Presence | -> Legibility | -> Content Type |
|--------|-----------|-------------|---------------|-----------------|
| HierText | `handwritten: bool`, `legible: bool` (word-level) | Area ratio of handwritten words per page | 2-level from `legible` bool; extend via recognition confidence | From transcription patterns |
| COCO-Text | `class: machine/handwritten`, `legibility: legible/illegible` | Area ratio of handwritten words | 2-level from `legibility` field | From word length/content |
| IAM | All handwritten lines, 657 writers | DOMINANT (all handwritten) | Derive from transcription error rates per writer | From transcription: numeric/alpha/prose |
| Muharaf | Arabic handwritten manuscripts | DOMINANT | FAIR-ILLEGIBLE (based on manuscript age/condition) | prose/specialized |
| PUCIT-OHUL | Urdu handwritten lines | SUBSTANTIAL-DOMINANT | Derive from OCR confidence | alphanumeric/prose |
| FUNSD | Mixed print + handwriting forms | SPARSE-MODERATE | Derive from field annotations | alphanumeric/numeric |

### 6.4 Stratification

- **Split**: 70/15/15
- **Primary axes**: presence_class, legibility_class, script_family
- **Leakage prevention**: IAM split by WRITER ID (657 writers); HierText by image ID; COCO-Text by COCO image ID; Muharaf by manuscript ID
- **Rare handling**: ILLEGIBLE from Muharaf damaged manuscripts + COCO-Text illegible; specialized from HASYv2 math symbols

### 6.5 Source Composition

| Source | Train Samples | Contribution |
|--------|--------------|-------------|
| HierText train | 8,281 | GOLD STANDARD: word-level handwritten + legible |
| COCO-Text train | ~15K | Word-level class + legibility |
| IAM | ~5K | Line transcriptions, 657 writers |
| Muharaf | ~5K | Arabic cursive, variable quality |
| PUCIT-OHUL | ~3K | Urdu handwriting |
| **KHATT** | **~4K** | **Arabic cursive handwriting (word/line-level); distinct from Muharaf manuscript style; Gap 6 P0** |
| **CASIA-HWDB** | **~4K** | **CJK offline handwriting (character/page-level); covers Simplified Chinese; Gap 6 P0** |
| **IIIT-INDIC** | **~3K** | **Devanagari + Indic handwriting (scene text + document); Gap 6 P0** |
| **HKR** | **~2K** | **Cyrillic/Russian handwriting; 200 writers, diversity of styles; Gap 6 P0** |
| Nepali Handwritten | 958 | Devanagari handwriting |
| NIST SD-19 | ~2K | US census handwriting forms |
| FUNSD | 199 | Mixed print+handwriting forms |
| DocLayNet (negatives) | ~15K | Printed-only (NONE class) |
| PubTabNet (negatives) | ~5K | Table-only (NONE class) |
| **Total** | **~73K** | **+13K non-Latin handwriting (Gap 6 P0 remediation)** |

> **Gap 6 note**: Without KHATT, CASIA-HWDB, IIIT-INDIC, and HKR, the handwriting presence/legibility/
> content_type heads cannot reliably classify Arabic cursive, CJK, Devanagari, or Cyrillic handwriting.
> These four datasets are P0 prerequisites for handwriting head training — they are not supplementary.

### 6.6 Quality Thresholds

| Label Type | Provenance | Training Weight |
|-----------|-----------|-----------------|
| HierText handwritten bool | tier_1_annotation | 1.0 |
| COCO-Text binary class | tier_1_annotation | 0.9 |
| IAM (all handwritten) | tier_1_annotation | 1.0 |
| Harmonized legibility scores | tier_3_heuristic | 0.4-0.5 |
| Negative samples (known printed-only) | tier_0_exact | 1.0 |
| Content type derivation | tier_3_heuristic | 0.4 |

**CONSENSUS UPDATE**: Reduced tier_3_heuristic weights for OCR-derived legibility from 0.7 to 0.4-0.5 and content type from 0.6 to 0.4 (recommended by Gemini 3, DeepSeek). OCR confidence is a weak proxy for human-perceived legibility -- recognition failures may reflect vocabulary/language model limitations rather than actual illegibility. Human-in-the-loop calibration recommended: sample 200-300 images per legibility level, have 2+ annotators rate, then calibrate heuristic weights to match human agreement rate.

---

## 7. Capture Method Dataset (~50K)

**Model**: SigLIP Group 5
**Task**: 7-class classification

### 7.1 Class Targets

| Class | Target % | Count | Primary Sources | Status |
|-------|----------|-------|-----------------|--------|
| BORN_DIGITAL | 30% | 15,000 | DocLayNet, PubTabNet, FinTabNet | Ready (downsample from >600K) |
| SCANNER_FLATBED | 25% | 12,500 | RVL-CDIP, Tobacco800, NIST SD-2/SD-6, MDIW13 | Ready (confirm metadata) |
| SCANNER_ADF | 5% | 2,500 | RVL-CDIP (ADF artifacts subset) | NEEDS LABELING (heuristic) |
| CAMERA_PROFESSIONAL | 10% | 5,000 | MIDV500 (15K), SmartDoc-QA | Ready |
| CAMERA_SMARTPHONE | 10% | 5,000 | SROIE, RealDAE, MLT19 camera subset | Tight (~11K available) |
| FAX | 5% | 2,500 | RVL-CDIP (fax subset) | NEEDS LABELING |
| SYNTHETIC | 15% | 7,500 | DocSynth300K, synth-multiscript-v3 (350,012) | Ready (downsample) |

### 7.2 Diversity Requirements (beyond capture class)

| Dimension | Criticality | Target | Min/Category |
|-----------|-------------|--------|--------------|
| **Domain** | IMPORTANT | >= 5 domains per capture class | 200 per (capture, domain) cell |
| **Script family** | IMPORTANT | Latin 50%, >= 3 others at >= 5% | 500 per non-Latin per capture class |
| **Quality range** | IMPORTANT | Full 0-1 per capture class | 200 per quality quintile per class |

### 7.3 Critical Gaps

1. **SCANNER_ADF vs FLATBED**: No metadata distinguishes these. Concrete ADF identification
   heuristic (Gap 9 remediation):
   - Edge-parallel dark bands (thin, 2-5px near page margins from roller mechanism)
   - Systematic micro-skew pattern (consistent 0.2-0.8° skew in same direction per batch)
   - Paper-feed direction artifacts (horizontal streaks from roller dust/contamination)
   - Multi-page separator marks (single-pixel horizontal lines from ADF separator)

   Validation criterion: Manual verification of 100 ADF-labeled samples before propagation to
   full RVL-CDIP corpus. Do NOT propagate heuristic labels without this spot-check.

2. **SCANNER_FLATBED — Modern CIS sensor gap (Gap 8 remediation)**: RVL-CDIP, Tobacco800, NIST
   SD-2/SD-6 are 1990s CCD technology. Modern CIS flatbeds (2010+) produce different noise
   profiles, color rendition, and artifact patterns than 1990s CCD scanners. A model trained
   only on 1990s scans will systematically misclassify modern scanner captures.
   - Source MIDV-2020 or equivalent recent flatbed scan dataset for CIS sensor examples
   - Annotate temporal gap: SCANNER_FLATBED_CCD (pre-2010) vs SCANNER_FLATBED_CIS (2010+)
   - Minimum target: ≥1,500 modern CIS scanner samples within the SCANNER_FLATBED class

3. **FAX**: RVL-CDIP has doc type labels but no explicit fax label. Fax-specific markers:
   halftone screening, 1D banding, low SNR (typically < 150 DPI effective). Need manual labeling
   of ~500 samples + propagation via these markers.

4. **Camera smartphone**: ~11K total; may need synthetic camera simulation on born-digital docs.

5. **Screen recapture / Moiré (Gap 10 — P1)**: Phone-photographing-a-monitor is a common
   production scenario (web page screenshots, presentation slides captured on camera). Screen
   recapture has a distinct artifact class (RGB aliasing + moiré from LCD subpixel grid) not
   present in any other capture method.
   - Add CAMERA_SMARTPHONE_SCREEN as a sub-class or annotation field
   - Generate ~500-1K screen recapture samples (photograph monitor displaying document content
     at various angles and distances)
   - Add Moran z-ratio metric to IQA verification for moiré artifact detection
   - Priority: P1 (after core camera classes are complete)

---

## 8. Shadow Regression Dataset (~18K)

**Model**: SigLIP Group 5
**Task**: Regression (0-1 severity)

> **Stream 4C Update (2026-02-21)**: SSIM-based severity labeling **ABANDONED** (5-model consensus, 4/4 substantive
> models agree). SSIM is invalid for shadow: measures blur/noise/compression equally, not shadow severity.
> Replaced with: (a) v3 synthetic views with Augraphy-applied, controlled-severity labels (Tier 0 exact), and
> (b) L2 metadata `shadow_severity` fields from real paired datasets.

**Real/Synthetic Mixing Cap**: ≥50% real (sd7k + wsrd + camera negatives), ≤50% v3 synthetic.
**Provenance field values**: `real_paired`, `synthetic_v3`.

### 8.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Shadow severity** | CRITICAL | 40% none (0.0), 20% mild (0.1-0.3), 20% moderate (0.3-0.6), 20% severe (0.6-1.0) | 1,500 per non-none |
| **Shadow type** | IMPORTANT | 40% none, 25% edge shadow, 20% cast shadow, 15% spotlight | 1,000 per type |
| **Capture method** | CRITICAL | 55%+ camera (real pairs), 20% scanner, 20% born_digital (negatives) | 1,500 scanner |
| **Provenance** | REQUIRED | Each sample carries `provenance` field | `real_paired` or `synthetic_v3` |

### 8.2 Source Composition (Stream 4C)

**Tier A — v3 Synthetic View (~8K, Augraphy Tier 0 labels)**

Generated by `scripts/generate_v3_shadow_view.py` from v3 pristine base images. Shadow applied via OpenCV
with controllable severity parameter. 4 shadow types: edge, cast, spotlight, scanner_lid.

- `severity` field = Augraphy severity parameter (Tier 0 exact, confidence 1.0)
- Cap at ≤50% of total dataset (≤9K)
- Script diversity: all 27 v3 scripts represented

**Tier B — Real Paired Datasets (~7-10K, L2 metadata labels)**

| Source | Samples | Audit | Labels | Status |
|--------|---------|-------|--------|--------|
| **sd7k** | 7,239 | **B** 87 | Paired GT (shadow/shadow-free) | Read `shadow_severity` from L2 JSON; skip `shadow_confidence < 0.5` |
| **wsrd** | 4,500 | **A** 95 | Paired GT (shadow/shadow-free) | Read `shadow_severity` from L2 JSON; skip `shadow_confidence < 0.5` |
| Doc3D | ~15K | -- | Shadow maps from 3D geometry (tier_0_exact) | DEFERRED (209GB, P3) |

**Shadow Negatives (~3.5K, camera-domain matched)**

Negatives must come from the same camera domain as positives to avoid domain confound:

| Source | Count | Severity | Rationale |
|--------|-------|----------|-----------|
| SmartDoc-QA clean frames | 2,000 | 0.0 | Flat lit, same camera domain as sd7k/wsrd |
| MIDV500 flat captures | 1,000 | 0.0 | Flat document captures, no shadow |
| v3 clean (zero shadow) | 500 | 0.0 | Generated with no shadow applied |

**Total target composition**: ~8K v3 synthetic + ~7-10K real (sd7k/wsrd) + ~3.5K negatives = **~18.5-21.5K**

Real data (sd7k + wsrd + camera negatives) ≥55% of total — exceeds the 50% real minimum.

**Book Gutter / Spine Shadow (Gap 5 — P1)**:

sd7k is flat-document only — it does not capture book gutter or curved-page shadow patterns.
Book spine shadows (gradient curves from physical binding) are a distinct artifact class that a
model trained only on flat-document shadows will systematically mislabel as "moderate edge shadow."

| Option | Feasibility | Priority |
|--------|------------|---------|
| Synthetic Blender-rendered bent-document shadows (Python → Blender bridge) | Medium | P1 |
| Doc3D shadow maps (209GB, ground-truth shadow geometry) | High quality, high effort | P2 |
| DocScan-type dataset with book scanning artifacts | Requires sourcing | P1 |

Target: ≥1,000 book-gutter shadow samples once a source is available. Add as a named sub-category
to this section when sourced. Do NOT mark shadow training complete until this gap is addressed.

**Stacked Degradation Sub-Split (Gap 11 — P1)**:

Real camera-captured documents frequently have simultaneous shadow + warping (e.g., book page
with spine shadow and page curl). Training on single-degradation examples produces overconfident
predictions on the dominant signal while ignoring secondary conditions.

- Generate ~500-800 samples: warp the v3 base image (page_curl type), THEN apply shadow overlay
- Labels carry BOTH `shadow_severity` AND `warping_severity` fields
- Weight these at 0.8× (slightly down-weighted as synthetic compound) to avoid domain shift
- Cap at ≤5% of total shadow dataset
- Modify `generate_v3_shadow_view.py` to accept a `--pre-warp` flag that applies page_curl before shadow

**Previous note on SSIM**: `severity = 1 - SSIM(shadow_img, clean_img)` was the original labeling method.
This is INVALID: SSIM measures pixel-level similarity and penalizes blur/noise/compression equally, so it
cannot isolate shadow severity. Do NOT use SSIM for shadow labels in any new scripts.

**Note on staindoc**: Stain removal (15K paired) is related but distinct from shadow removal. May provide
negative diversity and extreme degradation examples in a later phase; excluded from Stream 4C target.

---

## 9. Warping Regression Dataset (~24K)

**Model**: SigLIP Group 5
**Task**: Regression (0-1 severity)

> **Stream 4C Update (2026-02-21)**: SSIM-based severity labeling **ABANDONED** (same rationale as shadow —
> SSIM measures structural similarity, not warping severity). Replaced with: (a) v3 synthetic views with
> Augraphy/perspective transforms and controlled-severity labels (Tier 0 exact), and (b) L2 metadata
> `warping_severity` fields from real paired datasets. ALL 12,000 docalign12k pairs are now used (was 4K subset).

**Real/Synthetic Mixing Cap**: ≥70% real (all four real paired datasets), ≤30% v3 synthetic.
**Provenance field values**: `real_paired`, `synthetic_v3`.

### 9.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Warping severity** | CRITICAL | 30% none, 25% mild, 25% moderate, 20% severe | 2,000 per non-none |
| **Warping type** | IMPORTANT | 30% none, 25% page curl, 20% fold/crease, 15% perspective, 10% complex | 1,000 per type |
| **Capture method** | CRITICAL | 50% camera, 30% scanner (book spine curl), 20% born_digital (negatives) | 2,000 scanner |
| **Provenance** | REQUIRED | Each sample carries `provenance` field | `real_paired` or `synthetic_v3` |

### 9.2 Source Composition (Stream 4C)

**Tier A — v3 Synthetic View (~5K, Augraphy/perspective Tier 0 labels, capped at ≤30%)**

Generated by `scripts/generate_v3_warping_view.py` from v3 pristine base images. Three warp types:

- `perspective` (4-corner homography, severity from corner displacement ratio)
- `page_curl` (cylindrical warp, severity from bend angle)
- `fold` (reflection/shear fold, severity from fold depth)

`severity` field = normalized warp parameter (Tier 0 exact, confidence 1.0). Script diversity from v3.

**Tier B — Real Paired Datasets (~14-19.5K, L2 metadata labels)**

| Source | Samples | Audit | Labels | Status |
|--------|---------|-------|--------|--------|
| **anyphotodoc6300** | 6,306 | **A** 92 | Paired GT (corrected/distorted), AGPL-3.0 | Read `warping_severity` from L2 JSON |
| **warpdoc** | 1,020 | **B** 85 | Paired GT (warped/flat), 6 distortion types | Read `warping_severity` + `warping_type` from L2 |
| **docreal** | 200 | **B** 88 | Paired GT (distorted/scanned), MIT | Read `warping_severity` from L2 JSON |
| **docalign12k** | ~12,000 | D 76 | Paired GT (aligned/unaligned) | Use ALL 12K pairs (was 4K); 0.3x weight (D-capped) |
| **drccbi** | 325 | -- | Paired GT (warped/flat) | Read `warping_severity` from L2 JSON |
| Doc3D | ~15K | -- | Warping from 3D mesh (tier_0_exact) | DEFERRED (209GB, P3) |

**Warping Negatives (~5K, camera-domain matched)**

| Source | Count | Severity | Rationale |
|--------|-------|----------|-----------|
| SmartDoc-QA flat frames | 3,000 | 0.0 | Flat lit, camera domain; BENCHMARK-ONLY for warping eval — use only labeled negatives |
| MIDV500 flat captures | 2,000 | 0.0 | Flat document captures, no warping |

> **⚠️ SmartDoc-QA**: BENCHMARK-ONLY per audit policy for warping correction evaluation.
> Use ONLY for training negatives (flat camera captures with severity=0.0), never for warp-positive training.

**Total target**: ~5K v3 synthetic + ~14-19.5K real pairs + ~5K negatives = **~24-29.5K**.
Real data (real pairs + camera negatives) ≥70% of total — exceeds the 70% real minimum.

**docalign12k weight note**: Grade D (76) due to language gap (iso639=0%). Apply 0.3x training weight until
domain enrichment completes. Contributes ~12K pairs at reduced weight; still valuable for warping geometry.

**Stacked Degradation Sub-Split (Gap 11 — P1)**:

Real book-scan documents have simultaneous warping + skew (from page curl misalignment) + blur
(from depth-of-field at page edges). Training on isolated warping produces models that ignore
secondary signals and misestimate compound conditions.

- Modify `generate_v3_warping_view.py` to pre-apply slight skew rotation (±2-5°) BEFORE warping,
  then apply blur post-processing — this matches the real physical capture sequence
- Labels carry BOTH `warping_severity` AND `skew_angle` fields (multi-label)
- Target: ≥500 stacked samples at ≤5% of total warping dataset
- Training weight: 0.8× (compound synthetic down-weight)

**Previous note on SSIM**: `severity = 1 - SSIM(distorted, flat)` was the original labeling method.
This is INVALID for the same reasons as shadow. Do NOT use SSIM for warping labels in any new scripts.

---

## 10. Code Detection Dataset (~10K)

**Model**: SigLIP Group 5
**Task**: Regression (0-1 code confidence)

### 10.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Code confidence** | CRITICAL | 40% none (0.0), 20% possible (0.1-0.4), 20% likely (0.4-0.7), 20% definite (0.7-1.0) | 1,000 per non-zero |
| **Code language** | IMPORTANT | Python 25%, JavaScript 15%, Java 10%, C/C++ 10%, SQL 5%, other 15%, mixed 20% | 500 per language |
| **Rendering style** | IMPORTANT | 40% syntax-highlighted, 30% plain monospace, 20% inline, 10% handwritten | 500 handwritten |

### 10.2 Source Composition

| Source | Samples | Status |
|--------|---------|--------|
| GitHub rendered code screenshots | ~4,000 | Need generation (Playwright/carbon-now-cli for realistic renders) |
| Technical docs with code | ~2,000 | From multimodal-textbook, mathverse |
| Born-digital without code (negatives) | ~3,000 | DocLayNet, FinTabNet |
| Synthetic code pages | ~1,000 | Render code at various DPI/fonts |

**Gap**: No existing dataset has code block annotations. Requires new generation.

**CONSENSUS UPDATE**: Use Playwright or carbon-now-cli for GitHub code screenshot generation (recommended by Gemini 3). These produce realistic syntax-highlighted renders with proper fonts, themes (dark/light), and line numbers -- far more representative of production code images than simple monospace rendering.

---

## 11. Cross-Dataset Overlap Matrix

Source images shared across training datasets (same image, different labels per task):

| Source Set | Orient. | Skew | Res. | IQA | Script | Handwriting | Capture | Shadow | Warp |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| DocLayNet | X | X | X | | | X (neg) | X | | |
| FUNSD/NIST | X | X | X | | | X | X | | |
| SROIE | X | X | X | | | | X | | |
| RVL-CDIP | | X | | | | | X | | |
| MDIW13 | | | X | | X | | | | |
| synth-multiscript | | | X | | X | | | | |
| DIQA-5000 | | | | X | | | | | |
| OHR-Bench | | | | X | | | | | |
| RealDAE | | | | X | | | X | X | |
| HierText | | | | | | X | | | |
| COCO-Text | | | | | X | X | | | |
| SmartDoc-QA | | | | | | | X | X | X |
| MIDV500 | | | | | | | X | X | X |
| Doc3D | | | | | | | | X | X |

### Global Split Consistency Rule

**CRITICAL**: If an image appears in multiple training datasets, it MUST be in the SAME split (train/val/test) across ALL datasets. Implement a **global split registry** keyed by SHA256 hash.

---

## 12. Verification Framework

### 12.1 Pre-Training Assembly QA

| Check | Method | Threshold | Red Flag |
|-------|--------|-----------|----------|
| Class balance | Chi-square vs target distribution | p > 0.01 | Any class < 50% of target |
| Split leakage | Set intersection on source doc IDs | 0 overlap | ANY overlap |
| Label confidence | Histogram of confidence scores | >= 80% above 0.7 | > 20% below 0.5 |
| Capture coverage | Count per type | >= min threshold | Any type at 0 |
| Script coverage | Count per ML class | >= min threshold | Any class < 100 samples |
| Resolution spread | KS test for uniformity | p > 0.05 | Clustered at single DPI |
| Image integrity | PIL.Image.verify() | 0 corrupt | Any corrupt |
| Duplicate detection | pHash dedup | < 1% near-duplicates | > 5% duplicates |
| **Script × degradation cross-tabulation** | **Count (script_family × degradation_type) cells** | **≥100 samples per cell at severity > 0.3** | **ANY cell at 0 (HALT training)** |

### 12.1.1 Script × Degradation Cross-Tabulation (P0 Mandatory Requirement)

For each cell in the (script_family × degradation_type) matrix, REQUIRE ≥100 training samples
with severity > 0.3. This check is mandatory before training any head that uses both script and
quality/degradation signals (IQA Group 1, Resolution Quality MobileNet Head 3). Different scripts
have fundamentally different tolerance profiles for each degradation type (e.g., Arabic is more
sensitive to stroke blur than Latin; CJK is more sensitive to low-contrast than Devanagari).

| script_family | blur | noise | contrast | compression | shadow | warping |
|---|---|---|---|---|---|---|
| Latin | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 |
| Arabic | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 |
| CJK | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 |
| Devanagari | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 |
| Cyrillic | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 | verify ≥100 |

Add cross-tabulation verification to `scripts/verify_dataset_diversity.py`. Fail and HALT if any
cell is 0 after dataset assembly. Report as a table in the pre-training QA report.

### 12.2 Cross-Dataset Checks

| Check | Method | Red Flag |
|-------|--------|----------|
| Global split consistency | SHA256 -> split lookup across all datasets | Same image in train (task A) + test (task B) |
| Source overlap accounting | Matrix of shared source images | Undocumented overlap |
| Combined class distribution | Weighted merge | Single dataset > 50% of any class |
| Per-source contribution cap | Count per source dataset per class | Any single source > 40% of any class (consensus) |
| Cross-dimension interaction | Chi-square on (capture_method × script_family) cells | Any cell with 0 samples where both marginals > 0 (consensus) |
| Docling layout label casing | `scripts/standardize_layout_labels.py` (KI-001) | Raw Docling labels before normalization |
| Benchmark split contamination | Reserved split registry vs training manifests | smartdoc-qa, q-doc, diqa-5000 val/test in training |

### 12.2.1 Known Cross-Dataset Issues (Audit-Derived)

The Layer 2 audit identified 9 systemic quality issues affecting multiple datasets. These MUST be checked before training:

| Issue | Severity | Datasets | Fix |
|-------|----------|----------|-----|
| **KI-001**: Docling layout label casing mismatch | CRITICAL | All 52 Docling-processed datasets | `scripts/standardize_layout_labels.py` (automated) |
| **KI-002**: Docling Table detection unreliable on multi-column text | HIGH | Synthetic + multi-column | Manual VLM verification required |
| **KI-003**: Docling Picture detection unreliable on dense text | MEDIUM | Synthetic + dense text | Manual VLM verification required |
| **KI-004**: LLM handwriting detection unreliable on synthetic | HIGH | All synthetic datasets | Override pattern (set has_handwriting=False) |
| **KI-005**: LLM cannot detect synthetic capture method | HIGH | jssoda, synth-multiscript, docsynth | Override pattern (set capture_method=synthetic) |
| **KI-006**: LLM formula detection over-flags scientific text | MEDIUM | All LLM-enriched datasets | Manual VLM verification required |
| **KI-007**: LLM domain classification high UNK rate on generic content | LOW | Generic/narrative datasets | Accepted (taxonomy limitation) |
| **KI-008**: Nepali handwritten label noise (character variants) | LOW | nepali-handwritten | Dataset-specific mitigation |
| **KI-009**: Latin language conflation (fr/de/it mapped to en) | MEDIUM | mlt19, cocotext | ✅ Mitigated (LLM refinement resolves 1,731/2,671 samples) |

### 12.3 Training Monitoring

| Metric | Frequency | Threshold | Action |
|--------|-----------|-----------|--------|
| Per-class val accuracy | Every epoch | No class drops > 5% from peak | Increase class weight |
| Rare script accuracy (Tibetan, Hebrew) | Every epoch | >= 70% | Add more synthetic data |
| Synthetic vs real accuracy gap | Every 5 epochs | < 10% gap | Reduce synthetic weight |
| Per-capture-method accuracy | Every epoch | No type > 5% below average | Investigate failures |
| Gradient norm per task group | Every batch | No task > 5x average | Check PCGrad |

### 12.4 Red Flags That Halt Training

1. **Split leakage detected** -- HALT immediately
2. **Class collapse** -- Any class < 50% accuracy for 5 consecutive epochs
3. **Label noise > 5%** -- > 5% of samples flagged as likely mislabeled
4. **Synthetic-real gap > 15%** -- For classes with > 50% synthetic data
5. **Missing critical dimension** -- 0 samples for any critical category
6. **Confidence floor violation** -- > 30% of labels with confidence < 0.5

---

## 13. Dimension Sufficiency Summary

> **Updated**: 2026-02-21 based on audit completion and dataset assembly progress.

| Dataset | Capture | Script | Domain | Quality | Resolution | Content | Overall | Progress |
|---------|:-------:|:------:|:------:|:-------:|:----------:|:-------:|:-------:|:-------:|
| Orientation (50K) | OK | OK | OK | OK | OK | OK | **READY** | ✅ 100% |
| Skew (90K) | OK | OK | OK | OK | OK | N/A | **COMPLETE** | ✅ 100% |
| Resolution (30K) | TIGHT | OK | TIGHT | N/A | OK | TIGHT | **IN PROGRESS** | 🔄 18% |
| IQA (16K) | **INSUFF** | **INSUFF** | **INSUFF** | OK | TIGHT | TIGHT | **GAPS** | 🔄 40% |
| Script (108K) | TIGHT | TIGHT* | INSUFF | N/A | OK | OK | **GENERATING** | 🔄 11% |
| Handwriting (60K) | TIGHT | TIGHT | INSUFF | N/A | OK | OK | **NEEDS HARMONIZE** | ❌ 0% |
| Capture (50K) | OK | TIGHT | TIGHT | N/A | OK | N/A | **NEEDS LABELING** | ❌ 0% |
| Shadow (~18K) | TIGHT | OK | N/A | N/A | OK | N/A | **SCRIPTS DONE (Stream 4C)** | 🔄 Scripts ready |
| Warping (~24K) | TIGHT | OK | N/A | N/A | OK | N/A | **SCRIPTS DONE (Stream 4C)** | 🔄 Scripts ready |
| Code (10K) | OK | N/A | N/A | N/A | OK | N/A | **NEEDS CURATION** | ❌ 0% |

*Tibetan, Hebrew, Greek are tight; depend on synth-multiscript-v3 (350,012, GCS-complete — ⚠️ imbalanced; rebalancing needed before training)

**Shadow/Warping note (Stream 4C 2026-02-21)**: SSIM labeling abandoned (5-model consensus). Generation scripts
complete: `generate_v3_shadow_view.py` (Augraphy Tier 0), `generate_v3_warping_view.py` (perspective/curl/fold Tier 0),
`prepare_multitask_datasets.py shadow/warping` sub-commands (reads L2 `shadow_severity`/`warping_severity`).
Execution pending: data must be generated on GPU VM, L2 annotation run on sd7k/wsrd/anyphotodoc/warpdoc, then
manifests assembled and uploaded to `gs://image_detection_b/datasets/{shadow,warping}_training/`.

**Audit quality note**: 8 datasets capped at Grade D due to domain_level1 <75% (mdiw13, arabic-docs-ocr, siw13, cc-ocr, omnidocbench, muharaf, jssoda, docalign12k). Training weights may need reduction for these sources until domain enrichment is complete.

**IAM risk**: Grade F (36.4) -- no base metadata. If IAM is used for handwriting training, run DocLayout-YOLO to generate layout metadata first (GPU required).

---

## 14. Synth-Multiscript Assessment: Adjust, Not Redesign

> **GCS Audit (2026-02-21, corrected)**: `gs://image_detection_b/synth_multiscript_v3/` — **350,012 images**
> across 27 script folders (COMPLETE). The 190,485 figure was an erroneous intermediate count; live jpg-only
> gsutil count confirms 350,012. Target (350,012) was met; however, generation has a **distribution imbalance
> bug** — Arab has 49,169 images (3.8× target), 17 scripts below 12,963 target. Rebalancing required before
> training, not regeneration. v3 adds: orientation labels in sidecar JSON (`data.geometric.orientation_class`),
> all 27 ISO 15924 scripts, `splits.jsonl` for deterministic train/val/test assignment.

### Current Design Strengths

The existing `MultiScriptDocumentGenerator` ([generator.py](src/image_preprocessing_detector/synthetic/generator.py)) and its config ([config.py](src/image_preprocessing_detector/synthetic/config.py)) provide a robust foundation:

| Capability | Implementation | Quality |
|-----------|---------------|---------|
| **Script coverage** | 27 scripts, 198 OpenLID-v2 languages | Excellent |
| **Font diversity** | 5 tiers (SYSTEM 40%, REGIONAL 25%, STYLISTIC 15%, HANDWRITING 15%, ADVERSARIAL 5%) | Excellent |
| **Layout variety** | 11 layout types → Layer 2 mapping | Good |
| **Text density** | 5 levels (MINIMAL→DENSE) → Layer 2 mapping | Good |
| **Quality tiers** | 5 levels (PRISTINE 10%→DEGRADED 10%), independent of script | Good |
| **IQA labels** | 8 dimensions (blur, noise, compression, ink, paper, geometric, bleed_through, overall) | Good |
| **Multi-script docs** | 35% single, 45% two-script, 12% three, 3% four+ | Good |
| **Confusability pairs** | kas_Arab/kas_Deva, ace_Arab/ace_Latn, etc. | Excellent |
| **Mimicry fonts** | Latin fonts mimicking Arabic/Greek/Hebrew/CJK/Cyrillic | Excellent |
| **DPI-aware rendering** | Tier-based renderers (72/150/300 DPI) with proper A4 sizing | Good |
| **Layer 2 metadata** | Full schema_adapter.py with degradation mapping | Good |
| **Parser** | Implemented at `parsers/multilingual/synth_multiscript.py` | Done |

**Verdict**: The core pipeline is well-engineered. A full redesign would waste substantial existing work. Instead, targeted adjustments expand its utility across ALL training tasks.

### Gaps vs. Multi-Task Training Requirements

| Training Task | Current Support | Gap | Severity |
|--------------|----------------|-----|----------|
| **Script Detection** | Primary purpose, excellent coverage | Single-script ratio too low (35% vs 45-50% needed) | LOW |
| **Resolution Quality** | 3 DPI tiers (72, 150, 300) | Missing 100, 200, 400, 600 DPI; no char-height labels | MEDIUM |
| **Skew Regression** | geometric_distortion (broad) | No controlled skew angle labels for regression | HIGH |
| **Orientation** | No rotation variation | No 0/90/180/270 rotation augmentation | MEDIUM |
| **IQA** | 8 IQA dimensions | All synthetic; useful as supplement only | LOW |
| **Capture Method** | All "synthetic" | No scanner/camera simulation | MEDIUM |
| **Handwriting** | Font-based (15% handwriting fonts) | Not real handwriting; useful for negatives only | LOW |
| **Shadow/Warping** | Not simulated | No shadow/perspective/warping | N/A (use real datasets) |
| **Code Detection** | No code content | Not applicable (separate pipeline) | N/A |

### Missing Diversity Dimensions

| Dimension | Status | Fix |
|-----------|--------|-----|
| color_mode | Not tracked | Add binarization (15%) + grayscale (25%) post-process |
| document_age | Not tracked | Add aged paper effects to augmentation pipeline |
| DPI levels | Only 72, 150, 300 | Add 100, 200, 400, 600 to RESOLUTION_TIERS |
| UNKNOWN class | Not generated | Add blank/figure-only pages (2-3% of samples) |
| character_height | Not measured | Add CC analysis + store in metadata |
| skew_angle | Not controlled | Add exact angle rotation with tier_0_exact label |

### Recommended Adjustments (3 Tiers)

**Tier A: Config-Only Changes (No code changes, 1-2 hours)**

1. **Expand RESOLUTION_TIERS** in `config.py`:

   ```python
   RESOLUTION_TIERS = {
       "VERY_LOW": {"width_range": (400, 500), "target_dpi": 72},
       "LOW": {"width_range": (500, 700), "target_dpi": 100},
       "MEDIUM_LOW": {"width_range": (700, 850), "target_dpi": 150},
       "MEDIUM": {"width_range": (850, 1000), "target_dpi": 200},
       "STANDARD": {"width_range": (1000, 1200), "target_dpi": 300},
       "HIGH": {"width_range": (1200, 1400), "target_dpi": 400},
       "VERY_HIGH": {"width_range": (1400, 1700), "target_dpi": 600},
   }
   ```

2. **Adjust DOCUMENT_COMPOSITION_WEIGHTS**:

   ```python
   DOCUMENT_COMPOSITION_WEIGHTS = {
       "single": 0.45,     # 35% → 45% (more single-script for cleaner labels)
       "two": 0.38,        # 45% → 38%
       "three": 0.10,      # 12% → 10%
       "four_plus": 0.02,  # 3% → 2%
       "priority_pairs": 0.05,
   }
   ```

3. **Update RESOLUTION_TIER_WEIGHTS** to match 7-tier DPI:

   ```python
   RESOLUTION_TIER_WEIGHTS = {
       "VERY_LOW": 0.08, "LOW": 0.12, "MEDIUM_LOW": 0.15,
       "MEDIUM": 0.20, "STANDARD": 0.25, "HIGH": 0.12, "VERY_HIGH": 0.08,
   }
   ```

**Tier B: Minor Code Changes (4-6 hours)**

1. **Color mode post-processing** in `generator.py`:
   - After rendering + augmentation, randomly convert:
     - 15% to binarized (Otsu threshold or adaptive)
     - 25% to grayscale (PIL .convert("L") then back to RGB for model input)
     - 60% keep RGB
   - Store `color_mode` in metadata

2. **Character height measurement** in `schema_adapter.py`:
   - After rendering, measure character height via connected component analysis
   - Store `char_height_px` and `char_height_quality_score` in metadata
   - Uses existing `iqa_classical.py` connected component logic

3. **Skew augmentation mode** in `generator.py`:
   - New config flag: `skew_augmentation: bool = False`
   - When enabled, apply random rotation ±10° with exact angle stored
   - Labels: `skew_angle_degrees` (float, tier_0_exact)
   - Separate from degradation pipeline (applied AFTER augmentation)

4. **Orientation augmentation mode** in `generator.py`:
   - New config flag: `orientation_augmentation: bool = False`
   - When enabled, apply 0/90/180/270 rotation with class label
   - Labels: `orientation_class` (int, tier_0_exact)

5. **Document age simulation** in `augmentation_hybrid.py`:
   - Add `AGED` and `HISTORICAL` profiles alongside existing LIGHT/MODERATE/HEAVY
   - AGED: yellowing (mild), foxing spots, slight contrast reduction
   - HISTORICAL: heavy yellowing, foxing, staining, ink fading
   - Store `document_age` in metadata (modern/aged/historical)

**Tier C: New Capabilities (Deferred, 8-12 hours)**

1. **Scanner simulation** augmentation:
   - Scan noise profiles (Gaussian + salt-pepper)
   - ADF edge feed marks (thin dark lines at page edges)
   - Flatbed artifacts (shadow along spine for book scans)
   - Store `simulated_capture_method` in metadata

2. **Camera simulation** augmentation:
    - Perspective transform (mild keystone)
    - Non-uniform illumination (vignette + directional gradient)
    - Finger shadow occlusion (edge region darkening)
    - Slight motion blur (directional)
    - Store `simulated_capture_method: "camera_smartphone"` in metadata

3. **Domain templates**:
    - Invoice template (header, table, footer)
    - Receipt template (narrow, list items, total)
    - Scientific template (abstract, two-column body, references)
    - Legal template (numbered paragraphs, citations)
    - Form template (fields with labels + values in different scripts)
    - Store `domain` in metadata

4. **Structured content injection**:
    - Table generation (rows × cols with cell text)
    - Mathematical formulas (LaTeX rendering)
    - Figure placeholders (colored rectangles with caption)
    - Set content_flags accordingly

### Impact on Dataset Plan

With Tier A+B adjustments, synth-multiscript-v3 (350,012 images) becomes reusable across:

| Training Task | Synth-Multiscript Role | Samples Used | Replaces |
|--------------|----------------------|-------------|----------|
| Script Detection | PRIMARY source | ~60K (stratified by ML class) | N/A |
| Resolution Quality | SUPPLEMENTARY (multi-DPI) | ~5K (render at 7 DPI levels) | Part of "Synthetic variable-res" in Sec 3.4 |
| Skew Regression | SOURCE DOCUMENTS (apply rotation) | ~10K (clean sources × random angles) | Part of "Clean docs + synthetic rotation" in Sec 2.4 |
| Orientation | SOURCE DOCUMENTS (apply rotation) | Already using real docs | N/A |
| IQA (Phase 2) | PSEUDO-LABEL SUPPLEMENTARY | Up to ~20K (confidence >= 0.7) | Adds to Phase 2 pseudo-label pool |
| Capture Method | SYNTHETIC CLASS | ~7.5K | Already accounted for |
| Handwriting | NEGATIVE SAMPLES | ~5K printed-only | Supplements DocLayNet/PubTabNet negatives |

### Generation Strategy Change

**Before**: Generate base images once → use only for script detection
**After**: Generate base images once (v3: 350,012) → derive multiple training views via post-processing

```text
synth-multiscript-v3 (base, 350,012 images)
├── Script labels (tier_0_exact) → Script Detection Dataset
├── + skew rotation → Skew Regression Dataset (10K subset)
├── + DPI re-rendering → Resolution Quality Dataset (5K subset)
├── + color mode conversion → Color mode diversity for all tasks
├── + orientation rotation → Additional orientation sources
├── IQA labels (tier_0_exact) → IQA Phase 2 pseudo-label pool
└── Capture method = "synthetic" → Capture Method Dataset
```

**Key principle**: Generate the base images ONCE, then apply task-specific transformations as post-processing steps. This avoids regenerating 350K images (v3) and maximizes reuse.

### Implementation Priority

| Priority | Adjustment | Effort | Unblocks |
|----------|-----------|--------|----------|
| P0 | Tier A: Config changes (resolution tiers, composition weights) | 1-2h | Resolution quality diversity |
| P0 | Tier B.6: Skew augmentation mode | 2-3h | Skew regression from synthetic sources |
| P1 | Tier B.4: Color mode post-processing | 1-2h | Color mode diversity (consensus) |
| P1 | Tier B.5: Character height measurement | 2h | Resolution quality labels |
| P1 | Tier B.8: Document age simulation | 2h | Document age diversity (consensus) |
| P2 | Tier B.7: Orientation augmentation mode | 1h | Supplementary orientation data |
| P3 | Tier C.9-10: Scanner/camera simulation | 4-6h | Capture method diversity |
| P3 | Tier C.11-12: Domain templates + structured content | 4-6h | Domain + content flag diversity |

### Critical Files to Modify

| File | Changes |
|------|---------|
| `src/image_preprocessing_detector/synthetic/config.py` | RESOLUTION_TIERS (7 levels), RESOLUTION_TIER_WEIGHTS, DOCUMENT_COMPOSITION_WEIGHTS |
| `src/image_preprocessing_detector/synthetic/generator.py` | Add color_mode, skew, orientation post-processing; char height measurement |
| `src/image_preprocessing_detector/synthetic/schema_adapter.py` | Add color_mode, skew_angle, orientation_class, char_height to metadata |
| `src/image_preprocessing_detector/synthetic/augmentation_hybrid.py` | Add AGED, HISTORICAL profiles |
| `src/image_preprocessing_detector/synthetic/cli.py` | Add --skew, --orientation, --color-mode flags |

---

## 15. Generation Priority

> **Updated**: 2026-02-21. Skew is COMPLETE. Shadow/Warping feasibility improved via audit discoveries.

| Priority | Item | Effort | Blocks | Status |
|----------|------|--------|--------|--------|
| ~~P0~~ | ~~Skew dataset generation (40K)~~ | ~~3-5 days~~ | ~~MobileNetV4 + SigLIP Group 3~~ | ✅ **DONE (90K)** |
| ~~P1~~ | ~~Stream 4C: shadow/warping v3 view generation scripts~~ | ~~2 days~~ | ~~Shadow + Warping training~~ | ✅ **DONE** (`generate_v3_shadow_view.py`, `generate_v3_warping_view.py`) |
| ~~P1~~ | ~~Stream 4C: orientation hybrid rebuild scripts~~ | ~~1 day~~ | ~~Orientation training~~ | ✅ **DONE** (`build_orientation_real_component.py`, `derive_v3_orientation_view.py`) |
| ~~P1~~ | ~~Stream 4C: `prepare_multitask_datasets.py` (5 sub-commands)~~ | ~~2 days~~ | ~~SigLIP 2 training~~ | ✅ **DONE** (script, orientation, source, shadow, warping, merge) |
| P0 | Stream 4C: execute shadow/warping/orientation generation (data transfer) | 1-2 days | Shadow/Warping/Orientation training | ❌ Pending (needs GPU VM + GCS) |
| P0 | Resolution quality dataset V2 pipeline (Sauvola + projection) | 6-9 days | MobileNetV4 + SigLIP Group 5 | 🔄 In progress |
| P0 | Handwriting label harmonization | 3 days | SigLIP Group 4 | ❌ Not started |
| P0 | Domain enrichment: 8 D-capped datasets (GPU) | 2-5 days | Script/Handwriting training quality | ❌ Not started |
| P1 | Shadow severity: run L2 annotation on sd7k + wsrd (replaces SSIM) | 1 day | Shadow training | ❌ Not started |
| P1 | Warping severity: run L2 annotation on anyphotodoc + warpdoc + docalign12k | 2 days | Warping training | ❌ Not started |
| P1 | Capture method labeling (RVL-CDIP ADF/fax heuristic) | 2-3 days | SigLIP Group 5 | ❌ Not started |
| P1 | Code detection dataset curation (10K) | 3-4 days | SigLIP Group 5 | ❌ Not started |
| P1 | Tibetan real page-level collection | 2-4 weeks | Script accuracy (elevated from P3) | ❌ Not started |
| P2 | IAM base metadata generation (DocLayout-YOLO, GPU) | 1-2 days | Handwriting training (IAM Grade F rescue) | ❌ Not started |
| P3 | Doc3D extraction (209GB) | 1-2 days | Shadow + Warping augmentation | Deferred (feasible without) |
| P3 | ADF vs flatbed distinction | 2 days | Capture method | ❌ Not started |

---

## 16. Critical Files

| File | Purpose |
|------|---------|
| `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md` | Model architecture consuming these datasets |
| `docs/schema/layer2_enrichment_v2.schema.json` | Schema defining all diversity dimensions |
| `config/script_ml_classes.yaml` | 19 ML script classes with weights |
| `config/siglip2_multitask.yaml` | SigLIP2 multi-task training config (NEW - from Phase 10) |
| `scripts/generate_orientation_dataset.py` | Template for dataset generation scripts |
| `scripts/generate_multitask_labels.py` | Teacher pseudo-labeling pipeline (NEW - Phase 10 Stream 7) |
| `modal/train_siglip2_multitask.py` | SigLIP2 multi-task training script (NEW - Phase 10 Stream 4) |
| `src/image_preprocessing_detector/annotation/config/datasets.py` | Dataset registry with per-dataset metadata |
| `src/image_preprocessing_detector/annotation/schemas/enrichment.py` | Pydantic models for Layer 2 enrichment |
| `docs/datasets/AUDIT_TRACKING_INDEX.md` | Audit scores and quality signals for all 58 source datasets |
| `docs/datasets/DATASET_QUICK_REFERENCE.md` | Source dataset inventory (59 datasets, 3.35M images) |
| `docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md` | Assembled training dataset status and specs |

---

## 16. Implementation: Dataset Assembly Scripts

For each dataset that needs generation, create a script following the `generate_orientation_dataset.py` pattern:

| Script | Dataset | Key Logic | Status |
|--------|---------|-----------|--------|
| `scripts/generate_skew_dataset.py` | Skew (90K) | Random rotation ±10° on orientation sources; Hough labeling for natural scans | ✅ Done |
| `scripts/generate_v3_shadow_view.py` | Shadow synthetic (~8K) | v3 pool via splits.jsonl → Augraphy shadow (4 types) → Tier 0 severity labels | ✅ Done |
| `scripts/generate_v3_warping_view.py` | Warping synthetic (~5K) | v3 pool via splits.jsonl → perspective/curl/fold → Tier 0 severity labels | ✅ Done |
| `scripts/build_orientation_real_component.py` | Orientation real (~30K) | Download DocLayNet/RVL-CDIP PDFs → render → 4 rotations per page | ✅ Done |
| `scripts/derive_v3_orientation_view.py` | Orientation synthetic (~20K) | v3 sidecar fetch for `orientation_class` → balanced sample across 4 classes | ✅ Done |
| `scripts/prepare_multitask_datasets.py` | ALL (5 sub-commands) | script / orientation / source / shadow / warping / merge → GCS upload | ✅ Done |
| `scripts/generate_resolution_dataset.py` | Resolution (30K) | Multi-DPI rendering; char height measurement via connected components | ❌ Pending |
| `scripts/generate_handwriting_labels.py` | Handwriting (60K) | Harmonize HierText/COCO-Text/IAM labels to unified presence/legibility/content_type | ❌ Pending |
| `scripts/generate_code_dataset.py` | Code (10K) | Render GitHub code screenshots; label with syntax detection | ❌ Pending |
| `scripts/label_capture_method.py` | Capture (50K) | Heuristic classifier for ADF/fax on RVL-CDIP | ❌ Pending |
| `scripts/label_shadow_severity.py` | Shadow real (sd7k+wsrd) | L2 metadata annotation for `shadow_severity`; skip if `shadow_confidence < 0.5` | ❌ Pending |
| `scripts/label_warping_severity.py` | Warping real (4 datasets) | L2 metadata annotation for `warping_severity`; preserve `warping_type` from warpdoc | ❌ Pending |
| `scripts/verify_dataset_diversity.py` | ALL | Chi-square tests, coverage reports, split leakage checks | ❌ Pending |

---

## 17. Production Safeguards

### Confidence-Based Classical Fallback

**CONSENSUS UPDATE** (DeepSeek, Grok): When SigLIP 2 or MobileNetV4 predictions fall below confidence thresholds, the system should gracefully degrade to classical methods rather than serving low-confidence results:

| Head/Group | Confidence Threshold | Fallback Strategy |
|-----------|---------------------|-------------------|
| Orientation (MobileNet) | < 0.7 | Use Hough line-based orientation detection |
| Skew (MobileNet) | < 0.6 | Use classical Hough skew estimation |
| Resolution Quality (MobileNet) | < 0.5 | Use DPI metadata + connected component char height |
| IQA (SigLIP Group 1) | < 0.5 per dimension | Fall back to classical IQA detectors (iqa_classical.py) |
| Script Detection (SigLIP Group 2) | < 0.6 | Use OpenLID language -> script mapping |
| Handwriting (SigLIP Group 4) | < 0.5 | Use connected component stroke analysis |

This ensures production robustness during the early deployment phase when models may encounter out-of-distribution documents.

### Confidence-Based Label Weighting Within Tiers

**CONSENSUS UPDATE** (DeepSeek): Within each provenance tier, apply continuous confidence-based weighting rather than binary accept/reject:

```python
training_weight = tier_base_weight * min(confidence, 1.0)
```

Where `tier_base_weight` is: tier_0_exact=1.0, tier_1_annotation=1.0, tier_2_model=0.8, tier_3_heuristic=0.5

This creates a smooth gradient that naturally down-weights uncertain labels without hard cutoffs.

### 17.3 OOD Generalization Strategy (Non-Script Heads)

**CRITICAL DESIGN PRINCIPLE — OOD abstention is a safety mechanism, not a coverage substitute.**
If a condition is known to occur in production (per
[WILD_CONDITIONS_ANALYSIS.md](WILD_CONDITIONS_ANALYSIS.md)), the solution is adding training data
for that condition. Abstention handles genuinely unseen inputs; it cannot correct for gaps in
training coverage because the model produces high-confidence wrong predictions — not low-confidence
ones — on conditions it has been exposed to in a distorted way.

**What OOD abstention does**: When model confidence falls below the threshold, the system degrades
to classical methods (Section 17.1) rather than serving a low-confidence ML prediction.

**What OOD abstention does NOT do**: Cover conditions omitted from training data. A model that has
never seen compound blur+warping will produce wrong predictions on those images with high
confidence — it does not know to abstain.

**Abstention thresholds by head**:

| Head | Abstention Threshold | Post-Abstention Action |
|------|---------------------|----------------------|
| Orientation (MobileNet) | confidence < 0.5 | Classical Hough; flag `low_confidence` |
| Skew (MobileNet) | confidence < 0.5 | Classical Hough skew; flag `low_confidence` |
| Resolution Quality (MobileNet) | confidence < 0.45 | DPI metadata + CC char height |
| IQA (SigLIP Group 1) | any dimension confidence < 0.45 | Classical IQA detectors (iqa_classical.py) |
| Script Detection (SigLIP Group 2) | < 0.55 | OpenLID language → script mapping |
| Handwriting (SigLIP Group 4) | < 0.45 | CC stroke analysis |

**Non-training scripts (pending OpenLID expansion batches)**: When a script is not yet in the
training set, the OpenLID language → script classical fallback maps it to the nearest trained
class with reduced confidence. This is automatic — there is no human review queue in the
production pipeline. The system continues processing with clearly flagged reduced confidence.

**Required monitoring**: Track per-head abstention rates in production telemetry. If abstention
rate for any condition exceeds 10% of documents, treat as a signal to add training data for that
condition rather than tuning the abstention threshold.

---

## 18. Multi-Model Consensus Review Summary

**Review Date**: 2026-02-09
**Models Consulted**: 5 (4 substantive responses)
**Average Confidence**: 8.25/10

| Model | Stance | Score | Key Contribution |
|-------|--------|-------|------------------|
| google/gemini-2.5-pro | For | 9/10 | Validated architecture; flagged camera IQA gap |
| google/gemini-3-pro-preview | Against | 8/10 | Color space dimension; lower heuristic weights; Playwright for code gen |
| openai/gpt-5.2 | Neutral | -- | Empty response (no verdict returned) |
| deepseek/deepseek-r1-0528 | Neutral | 8/10 | Cross-dimension tests; per-source caps; HANS/HANT classifier; Tibetan elevation |
| x-ai/grok-4 | Against | 8/10 | Classical fallback safeguards; production robustness concerns |

### Unanimous Findings (All 4 Models)

1. **Global split registry** -- Exemplary design, essential for multi-task training
2. **4-tier provenance system** -- Best practice for mixed-quality labels
3. **Verification framework** -- Comprehensive and actionable
4. **Camera IQA gap** -- Critical risk (583 samples insufficient)

### Changes Incorporated

| Finding | Action | Section |
|---------|--------|---------|
| Camera IQA gap (583 -> 8,475) | Added SmartDoc-QA + MIDV500 to IQA Phase 1 | 4.3 |
| Color space dimension missing | Added as dimension 13 (binarized/grayscale/color) | Context |
| Document age dimension missing | Added as dimension 14 (modern/aged/historical) | Context |
| tier_3_heuristic weights too high | Reduced legibility 0.7->0.4-0.5, content_type 0.6->0.4 | 6.6 |
| Tibetan priority too low | Elevated from P3 to P1 | 5.3, 14 |
| HANS/HANT needs dedicated classifier | Added second-stage gate recommendation | 5.3 |
| Missing cross-dimension interaction tests | Added to verification framework | 12.2 |
| Missing per-source contribution caps | Added 40% cap per source per class | 12.2 |
| Code screenshot generation approach | Added Playwright/carbon-now-cli recommendation | 10.2 |
| Production confidence fallback | Added classical method fallback table | 17 |
| Confidence-based label weighting | Added continuous weighting formula | 17 |

### Findings Not Incorporated (Deferred)

| Finding | Reason | Status |
|---------|--------|--------|
| Human-in-the-loop legibility calibration | Requires funded annotation effort; documented as recommendation in 6.6 | Noted |
| Document age metadata enrichment | Requires new enrichment pipeline; schema dimension added but no dataset targets yet | Deferred |
| Color mode metadata enrichment | Requires new enrichment pipeline; schema dimension added but no dataset targets yet | Deferred |

### Post-Consensus Audit Update (2026-02-14)

A full Layer 2 metadata audit completed 2026-02-14 across all 58 source datasets (Version 4.0.0).
Key findings that affect diversity planning:

| Finding | Impact | Action |
|---------|--------|--------|
| 8 datasets capped at Grade D (domain_level1 <75%) | Training weight reliability reduced for mdiw13, arabic-docs-ocr, siw13, cc-ocr, omnidocbench, muharaf, jssoda, docalign12k | Apply 0.3× weight cap until domain enrichment complete (GPU-LLM required) |
| IAM at Grade F (base metadata absent) | Handwriting dataset has no reliable domain/quality metadata | Requires rescue pipeline; Tier 3 heuristic labels only until fixed |
| 9 cross-dataset Known Issues (KI-001 to KI-009) | Systemic label inconsistency, split contamination, and schema gaps across multiple datasets | See Section 12.2.1 for KI table and verification checks |
| SmartDoc-QA is BENCHMARK-ONLY | Phase 10/11 plan incorrectly listed it as a warping training source | Removed from Section 9 training composition; benchmark wall must hold |
| Shadow dataset unblocked | sd7k (Grade B 87) + wsrd (Grade A 95) provide 11.7K purpose-built shadow pairs | ~18K target achievable via Augraphy Tier 0 synthetic (≤50%) + real pairs via L2 labels |
| Warping dataset unblocked | anyphotodoc6300 (Grade A 92) + warpdoc (Grade B 85) + all 12K docalign12k | ~24K target achievable; Augraphy synthetic ≤30%; docalign12k at 0.3x weight (D-capped) |

---

## 19. Stream 4C Implementation Update (2026-02-21)

This section documents the decisions made during Stream 4C dataset preparation (Phase 10) and their impact
on the diversity requirements above.

### 19.1 Provenance Field (Cross-Cutting Requirement)

**Every sample in every training manifest MUST carry a `provenance` field.** This field enables post-hoc analysis
of real/synthetic generalization gaps and is enforced by `prepare_multitask_datasets.py`.

| Provenance Value | Meaning | Used In |
|-----------------|---------|---------|
| `real_scan` | Physical document scanned by flatbed or ADF | Orientation (real), Source (scanned) |
| `real_camera` | Physical document photographed by camera | Source (camera), Shadow/Warping negatives |
| `real_born_digital` | Born-digital PDF rendered to image | Orientation (real), Source (born_digital) |
| `real_paired` | Real document from paired shadow/warping dataset | Shadow, Warping (sd7k, wsrd, anyphotodoc, etc.) |
| `synthetic_v3` | Generated by synth-multiscript-v3 pipeline | Orientation (v3), Shadow (Augraphy), Warping (Augraphy), Script |

### 19.2 L2 `capture_method` Expansion for Source Dataset

The document source dataset was expanded from 3 hardcoded datasets to any L2-enriched dataset with confirmed
capture method. The L2 `capture_method` field maps to 3 training classes:

```python
L2_TO_SOURCE_CLASS = {
    "born_digital":         "born_digital",
    "scanner_flatbed":      "scanned",
    "scanner_adf":          "scanned",
    "fax":                  "scanned",
    "camera_smartphone":    "camera",
    "camera_professional":  "camera",
    "synthetic":            None,   # Excluded
    "unknown":              None,   # Excluded
}
```

Camera class expansion queries ALL L2-enriched datasets for camera images:

| Dataset | Camera Images | Method |
|---------|--------------|--------|
| SmartDoc-QA | ~4,300 | `camera_professional` from L2 metadata |
| RealDAE | ~1,200 | `camera_smartphone` from L2 metadata |
| MIDV500 | ~3,600 | `camera_professional` from L2 metadata |
| Others | Variable | L2 enrichment query |

Target: ≥12,000 camera images before splitting. `born_digital` underscore spelling validated by assertion
at write time (hard validation). Domain stratification for scanned (RVL-CDIP) via L2 `domain_level1` field.

### 19.3 Synth-Multiscript-v3 GCS Audit Findings

Audit of `gs://image_detection_b/synth_multiscript_v3/` (2026-02-21):

- **Total images**: 350,012 (confirmed by live jpg-only gsutil count 2026-02-21; earlier 190,485 figure was an erroneous intermediate count)
- **Scripts**: 27 ISO 15924 folders confirmed (Arab, Cyrl, Deva, Hans, Hant, Hebr, Jpan, etc.)
- **Orientation labels**: Available in per-image sidecar JSON at `data.geometric.orientation_class` (0/90/180/270)
- **Split registry**: `splits.jsonl` at GCS prefix root — use for deterministic split assignment
- **Latin exclusion**: `Latn` folder excluded from orientation and shadow/warping synthetic components
  (Latin orientation coverage provided by real documents)

### 19.4 SSIM Labeling Abandonment (Shadow + Warping)

5-model AI consensus (4/4 substantive models, 2026-02-21) rejected SSIM as a shadow/warping severity metric:

> **SSIM measures structural similarity, not shadow/warping severity.** A blurred image has low SSIM vs. its
> clean counterpart for the same reason a shadowed image does. SSIM cannot distinguish between blur, noise,
> compression artifacts, and actual degradation of interest.

**Replacement methodology**:

1. **Synthetic labels (Tier 0 exact)**: Augraphy severity parameter directly recorded as label. No post-hoc
   measurement needed — the severity is known because we set it.
2. **Real labels (Tier 1/2)**: L2 metadata `shadow_severity` / `warping_severity` fields from dedicated
   annotation pipeline (to be run on sd7k, wsrd, anyphotodoc6300, warpdoc, docalign12k).

Scripts implementing the new methodology:

- `generate_v3_shadow_view.py` — Augraphy-based synthetic shadow, Tier 0
- `generate_v3_warping_view.py` — perspective/curl/fold synthetic warp, Tier 0
- `prepare_multitask_datasets.py shadow` — reads L2 `shadow_severity`, enforces ≥50% real
- `prepare_multitask_datasets.py warping` — reads L2 `warping_severity`, enforces ≥70% real

Scripts pending implementation for real data labeling:

- `label_shadow_severity.py` — L2 annotation for sd7k + wsrd
- `label_warping_severity.py` — L2 annotation for anyphotodoc + warpdoc + docalign12k + docreal

---

## 20. Audit-Derived Quality Signals

**Audit Version**: 4.0.0 (2026-02-14)
**Coverage**: 58/58 source datasets scored | Mean 84.1 | Median 88.8

This section translates Layer 2 audit results into actionable training guidance. Each assembled
training dataset carries risk proportional to the grade distribution of its source datasets.

### 19.1 Source Dataset Audit Grades by Training Task

| Training Dataset | Key Source Datasets | Audit Grade | Score | Risk Level |
|-----------------|---------------------|-------------|-------|------------|
| **Orientation (50K)** | DocLayNet PDFs + RVL-CDIP (real, rotated) + synth-multiscript-v3 (non-LATN) | B, B, Deferred | 87, 88, -- | LOW (≥60% real; v3 synthetic ≤40%) |
| **Skew (90K)** ✅ DONE | synth (71K) + 13 natural scan datasets | Mixed B-C | 80-90 | LOW (synthetic 79%, labels T0/T2) |
| **Resolution Quality (30K)** | diqa-5000, ohr-bench, realdae | B, B, B | 84, 87, 84 | LOW-MEDIUM |
| **IQA Curated (16K)** | diqa-5000, ohr-bench, realdae | B, B, B | 84, 87, 84 | LOW-MEDIUM |
| **IQA Synthetic (100K)** | synth-multiscript-v3 | Deferred (pre-audit) | -- | LOW (synthetic by construction) |
| **Script (108K)** | mdiw13, synth-multiscript-v3, mlt19 | **D**, Deferred, C | 74, --, 80 | **HIGH** (mdiw13 domain cap) |
| **Handwriting (60K)** | iam, gnhk, nist-sd19, cvl | **F**, B, B, C | 45, 85, 88, 78 | **CRITICAL** (IAM Grade F) |
| **Capture Method (50K)** | doclaynet, ohr-bench, midv500, smartdoc-qa* | B, B, B, A | 87, 87, 92, 93 | LOW-MEDIUM |
| **Shadow (~18K)** | sd7k, wsrd + v3 synthetic (Augraphy Tier 0) | B, A, -- | 87, 95, -- | LOW (Augraphy synthetic = self-labeled) |
| **Warping (~24K)** | anyphotodoc6300, warpdoc, docalign12k (ALL 12K) + v3 synthetic | A, B, **D**, -- | 92, 85, 76, -- | MEDIUM (docalign12k domain cap, 0.3x weight) |

> \* SmartDoc-QA is used ONLY for Capture Method training (source type labels), never for warping/perspective
> correction training. Benchmark integrity maintained.

### 19.2 D-Capped Dataset Training Weight Policy

Eight datasets cannot provide reliable domain-level diversity signals until domain_level1 coverage
reaches >75%. Applies to: **mdiw13, arabic-docs-ocr, siw13, cc-ocr, omnidocbench, muharaf,
jssoda, docalign12k**.

```text
Normal weight:     tier_base_weight * min(confidence, 1.0)
D-capped weight:   tier_base_weight * min(confidence, 1.0) * 0.3
Trigger:           audit.domain_level1_coverage < 0.75 OR audit.grade == "D"
Unblock condition: GPU-LLM domain enrichment pipeline (P0 in Section 15)
```

**Practical impact by training task:**

| Training Dataset | D-Capped Sources | Sample Count Affected | Effective Weight |
|-----------------|------------------|-----------------------|-----------------|
| Script (108K) | mdiw13 (290K source) | ~25K script training images | 0.3× |
| Warping (20K) | docalign12k (~12K source) | ~3K warping images | 0.3× |
| Capture Method (50K) | cc-ocr (6.5K source) | ~2K capture images | 0.3× |

**Until domain enrichment completes**, these datasets contribute at 0.3× weight. The assembly
scripts (`scripts/generate_multitask_labels.py`) should read the audit grade from
`docs/datasets/AUDIT_TRACKING_INDEX.md` and apply the weight cap automatically.

### 19.3 IAM Grade F Rescue Path

IAM (`iam`) received **Grade F (score: 45)** due to absent base metadata fields. The 60K
handwriting training dataset cannot safely use IAM until the following rescue pipeline runs:

| Step | Action | Priority | Estimated Effort |
|------|--------|----------|-----------------|
| 1 | Add base metadata (paper format, script, language) from IAM official docs | P1 | 2h |
| 2 | Run capture method inference (scanner-based, high confidence) | P1 | 30m |
| 3 | Run domain enrichment (English academic/institutional) | P1 | 1h |
| 4 | Re-run audit scoring; target Grade B (≥80) | P1 | 30m |
| 5 | Promote from Tier 3 heuristic to Tier 1 annotation for metadata | P1 | -- |

**Until IAM is rescued**, the handwriting training dataset relies on:

- gnhk (Grade B 85): ~15K handwriting samples
- nist-sd19 (Grade B 88): ~10K historical handwriting
- cvl (Grade C 78): ~8K historical handwriting

This leaves the 60K target short (~33K available vs. 60K needed). IAM rescue is a prerequisite
for reaching full handwriting dataset size.

### 19.4 Known Issue Application Checklist for Dataset Assembly

Before running any assembly script for a training dataset, verify these KI checks pass:

| KI | Issue | Affected Training Datasets | Check Command |
|----|-------|---------------------------|---------------|
| KI-001 | Orientation label inconsistency (0°/360° boundary) | Orientation, Skew | `verify_dataset_diversity.py --check ki001` |
| KI-002 | Script label granularity mismatch (ISO vs. ML classes) | Script, IQA Synthetic | `verify_dataset_diversity.py --check ki002` |
| KI-003 | Benchmark split contamination risk | All datasets using doclaynet, pubtabnet, ohr-bench | `verify_dataset_diversity.py --check ki003` |
| KI-004 | Capture method label inflation (born-digital misclassified) | Capture Method | `verify_dataset_diversity.py --check ki004` |
| KI-005 | Bounding box coordinate system inconsistency (COCO vs. VOC) | Layout-adjacent tasks | `verify_dataset_diversity.py --check ki005` |
| KI-006 | Resolution quality label drift (V1 vs. V2 method) | Resolution Quality | `verify_dataset_diversity.py --check ki006` |
| KI-007 | Cross-dataset image duplication (same source, different splits) | All | `verify_dataset_diversity.py --check ki007` |
| KI-008 | IAM metadata absence propagation | Handwriting | `verify_dataset_diversity.py --check ki008` |
| KI-009 | Domain label coverage gap in D-capped datasets | Script, Warping, Capture Method | `verify_dataset_diversity.py --check ki009` |

> **Note**: `verify_dataset_diversity.py` KI checks are planned functions; implement alongside
> dataset assembly scripts in Phase 10 Stream 7.

### 19.5 Grade Distribution Summary for Training Portfolio

| Grade | Count | Source Datasets | Training Risk |
|-------|-------|-----------------|---------------|
| A (95-100) | 6 | wsrd, anyphotodoc6300, midv500, smartdoc-qa, synthdog, docvqa | Ideal — use at full weight |
| B (80-94) | 31 | ohr-bench, doclaynet, sd7k, gnhk, nist-sd19, realdae, warpdoc, … | Standard — use at full weight |
| C (70-79) | 13 | cvl, staindoc, mlt19, mlt17, bhutan-afs, … | Acceptable — verify label accuracy |
| D (<70) | 8 | mdiw13, arabic-docs-ocr, siw13, cc-ocr, omnidocbench, muharaf, jssoda, docalign12k | Restricted — apply 0.3× weight cap |
| F | 1 | iam | Rescue required before use |
| Deferred | 3 | doc3d, docsynth300k, synth-multiscript-v3 | Self-evaluated at generation time (v3 complete on GCS; formal audit pending) |

**Portfolio health**: 37/54 scored datasets (69%) are Grade B or above and can be used at full
training weight. The 8 D-capped datasets require domain enrichment (P0 action); IAM requires
metadata rescue (P1 action) before the handwriting dataset can reach its 60K target.

---

## 21. Wild Conditions Gap Remediation Update (2026-02-22)

**Reference**: [WILD_CONDITIONS_ANALYSIS.md](WILD_CONDITIONS_ANALYSIS.md) — 60 documented wild conditions
**Consensus review**: 5-model review (4/4 substantive responses, avg confidence 8.5/10, 2026-02-22)
**Full analysis**: `tmp_cleanup/.tmp-wild-conditions-vs-ddr-analysis-20260222.md`

### 21.1 Gap Remediation Status

| Gap | Description | Priority | DDR Section Updated | Status |
|-----|-------------|----------|---------------------|--------|
| Gap 1 | Compound/multi-distorted IQA samples | P0 | Section 4.2, 4.3 Phase 1B | ✅ Added |
| Gap 2 | Symmetric document orientation (epistemic impossibility) | P0 | Section 1.2.1 | ✅ Added |
| Gap 3 | Resolution confounds (upscaled raster / vector PDF) | P0 | Section 3.2, 3.4 | ✅ Added |
| Gap 4 | Script-specific quality thresholds (CJK vs Latin minimum) | P0 | Section 3.2 | ✅ Added |
| Gap 5 | Book gutter shadow (sd7k is flat-doc only) | P1 | Section 8.2 | ✅ Noted |
| Gap 6 | Non-Latin handwriting (KHATT, CASIA-HWDB, IIIT-INDIC, HKR absent) | P0 | Section 6.5 | ✅ Added |
| Gap 7 | Multi-column skew — global deskewing is a RAG quality REDUCTION | P0 | Section 2.1, 2.3 | ✅ Added |
| Gap 8 | Modern CIS scanner (2020+) absent; RVL-CDIP is 1990s CCD only | P1 | Section 7.3 | ✅ Added |
| Gap 9 | ADF identification heuristic undefined | P1 | Section 7.3 | ✅ Added |
| Gap 10 | Screen recapture / moiré — unique artifact class | P1 | Section 7.3 | ✅ Added |
| Gap 11 | Compound warp+shadow+skew (single-degradation training inadequate) | P1 | Sections 8.2, 9 | ✅ Added |
| Gap 12 | Document age dataset targets (aged/historical) — was "deferred" | P1 | Section 4.3 note | ✅ Activated |
| Gap 13 | Blank/figure-only orientation (hallucination risk) | P0 | Section 1.2.1 (merged with Gap 2) | ✅ Added |
| Gap 14 | Per-script IQA adequacy (~500 non-Latin total is insufficient) | P1 | Section 4.1 min raised | ✅ Noted |

### 21.2 Policy Clarifications (Applied in This Update)

Three DDR policies clarified following the 2026-02-22 consensus review:

**Policy 1 — OOD abstention scope** (Section 17.3): OOD confidence abstention is enforced at
production inference but is NOT a substitute for training data coverage. Known production
conditions must have training data representation. Abstention handles genuinely unseen
out-of-distribution inputs — not gaps in planned training coverage where the model will
produce high-confidence wrong predictions.

**Policy 2 — OpenLID expansion commitment** (Section 5): The previously deferred "Phase 2"
OpenLID script expansion (~60+ ISO 15924 scripts) is merged into Phase 1 scope. The 19 initial
ML classes are the first training batch. Each subsequent batch (per OpenLID language group) is
committed as Phase 1 work. No "Phase 2" for script expansion exists.

**Policy 3 — No human review routing** (Section 17.3): OOD inputs in production do NOT route to
a human review queue. The production safeguards use confidence-based classical method fallbacks
throughout. Human annotation workflows exist for training data preparation only, not for
production document routing.

### 21.3 Updated Wild Condition Coverage Estimate

| Coverage State | Before This Update | After P0 Gaps Addressed | After P0+P1 Gaps Addressed |
|----------------|--------------------|--------------------------|-----------------------------|
| Fully covered | 2/60 (3%) | ~8/60 (13%) | ~16/60 (27%) |
| Partially covered | 5/60 (8%) | ~12/60 (20%) | ~20/60 (33%) |
| Not covered | 53/60 (88%) | ~40/60 (67%) | ~24/60 (40%) |

Target deployment threshold: ≥20% fully covered (12/60 conditions). P0 remediation achieves
this. Full coverage (60/60) is not a realistic target at any viable data budget — the goal is
highest-frequency × highest-impact coverage, not completeness.

### 21.4 Training Prerequisites (Updated Blocking Dependencies)

| Head Group | BEFORE training can start | New Prerequisites Added |
|-----------|--------------------------|------------------------|
| Orientation | Symmetric/ambiguous sub-dataset assembled | Section 1.2.1 (~2,500 samples) |
| Skew | ≥20% multi-column + cross-detector gate validated | Section 2.1, 2.3 |
| Resolution Quality | Confound sub-dataset assembled; raw metric output implemented | Section 3.4 (~2,000 samples) |
| IQA | Compound distortion Phase 1B assembled | Section 4.3 (~3K-5K samples) |
| Script Detection | KHATT + CASIA-HWDB + IIIT-INDIC + HKR licensed and integrated | Section 6.5 (+13K samples) |
| Handwriting | Same non-Latin datasets as Script; harmonize_handwriting_labels updated | Section 6.5 |
| Capture Method | Modern CIS scanner examples sourced; ADF heuristic validated on 100 samples | Section 7.3 |
| Shadow | Book gutter gap acknowledged; stacked degradation sub-split generated | Section 8.2 |
| Warping | Stacked degradation sub-split generated | Section 9 |
