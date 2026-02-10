# Training Dataset Diversity Requirements for MobileNetV4 + SigLIP 2

## Context

The approved model requirements plan ([SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md)) specifies two models needing training datasets: **MobileNetV4-Conv-S** (3 heads, fast pre-correction) and **SigLIP 2 NAFlex** (16 heads across 5 groups). This document defines the **diversity characteristics** each training dataset must exhibit to ensure robust generalization to unseen production documents.

**Related**: [TRAINING_OPTIMIZATION_PLAN.md](TRAINING_OPTIMIZATION_PLAN.md) -- Training optimization strategy (ILP allocation, multi-task loss balancing, phased head training, active learning)

Production will encounter documents from any domain, any script, any capture method, any degradation level. Models trained on narrow data distributions will fail silently on underrepresented categories. This plan specifies target distributions, stratification strategies, quality thresholds, and verification metrics for every training dataset.

### Available Diversity Dimensions (Layer 2 Enrichment Schema)

From [layer2_enrichment_v2.schema.json](docs/schema/layer2_enrichment_v2.schema.json):

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

| Dimension | Datasets with Data | Key Gap |
|-----------|-------------------|---------|
| capture_method | 13/25 aggregates | 33% unknown; camera severely underrepresented |
| domain | 3/25 (22 are 100% UNK) | 80% unknown - cannot assess industry diversity |
| script_code | 7/25 (via script_family) | CJK, Cyrillic weak |
| quality/degradation | 0/25 | Zero coverage in aggregates |
| content_flags | 7/25 | Tables/figures/formulas sparse |

---

## 1. Orientation Dataset (50K) -- READY

**Model**: MobileNetV4 Head 1 + SigLIP Group 3
**Task**: 4-class classification (0/90/180/270)
**Status**: Generated at `E:\image_detection\03_training_datasets\orientation\`

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

### 1.3 Source Composition

Already specified in MOBILECLIP2_S4_S0_DATASET_DESIGN.md: 12,500 unique sources from DocLayNet (5,500), FUNSD/NIST (1,500), SROIE (1,000), TableBank/PubTabNet (1,500), NIST SD-19 (1,000), Arabic Docs (1,500), Nepal Devanagari (700), MLT+synthetic Japanese (1,050).

**Status**: READY. No additional design work needed.

---

## 2. Skew Regression Dataset (40K) -- NEEDS GENERATION

**Model**: MobileNetV4 Head 2 + SigLIP Group 3
**Task**: Continuous regression (±10°, target <0.5° residual)

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

### 2.2 Angle Distribution (CRITICAL)

```
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

### 2.4 Source Composition

| Component | Count | Source | Labels | Status |
|-----------|-------|--------|--------|--------|
| Clean docs + synthetic rotation | 25,000 | Same 12,500 orientation sources x 2 random angles | tier_0_exact angle | Need generation |
| Naturally skewed scans | 5,000 | RVL-CDIP (sample from 16K), Tobacco800 (1,290) | Hough-derived (tier_2_model, conf >= 0.7) | Need labeling |
| Synthetic + degradation | 10,000 | Clean sources + scanner/camera simulation + random rotation | tier_0_exact angle + degradation | Need generation |

### 2.5 Quality Thresholds

- **Synthetic labels**: tier_0_exact, confidence 1.0
- **Natural scan labels**: tier_2_model, accept only if Hough AND line-based agree within 0.5°
- **Disagreement handling**: Store as soft labels with uncertainty; use GaussianNLL loss
- **Loss function**: SmoothL1 on angle + optional GaussianNLL for uncertainty

---

## 3. Resolution Quality Dataset (30K) -- NEEDS GENERATION

**Model**: MobileNetV4 Head 3 + SigLIP Group 5
**Task**: Regression (0-1, character-height-aware)

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

```
char_height < 16px:    quality = 0.00-0.15  (needs major upscaling)
char_height 16-24px:   quality = 0.15-0.35  (needs light upscaling)
char_height 24-32px:   quality = 0.35-0.55  (acceptable)
char_height 32-48px:   quality = 0.55-0.75  (optimal OCR range)
char_height 48-64px:   quality = 0.75-0.85  (good, slightly oversized)
char_height 64-96px:   quality = 0.85-0.95  (oversized)
char_height > 96px:    quality = 0.95-1.00  (definitely oversized)
```

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
| Synthetic variable-res | 5,000 | synth-multiscript-250K (sample) | Render at controlled DPI with known char heights |

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
| Camera-captured IQA: only RealDAE (583 samples) | Camera has different quality characteristics than scanner | HIGH |
| Script diversity: 0% script metadata on IQA datasets | Cannot verify script-fairness | HIGH |
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
**Task**: 19-class classification (from `config/script_ml_classes.yaml`)

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
| TIBT | 4% | 4,000 | ~142K chars + ~200 real docs + ~3.8K synth | Quantity via TibHCR; page-level concern |
| HEBR | 3% | 3,000 | ~5K | synth-multiscript | Tight |
| GREK | 2% | 2,000 | ~3K | synth-multiscript | Tight |
| BENG | 3% | 3,000 | ~8K | MDIW13, synth-multiscript | OK |
| TAML | 2% | 2,000 | ~5K | MDIW13, synth-multiscript | OK |
| TELU | 2% | 2,000 | ~5K | MDIW13, synth-multiscript | OK |
| INDIC_OTHER | 3% | 3,000 | ~10K | MDIW13, synth-multiscript | OK |
| SE_ASIAN_OTHER | 2% | 2,000 | ~3K | synth-multiscript | Tight |
| OTHER | 3% | 3,000 | ~5K | synth-multiscript | OK |
| UNKNOWN | 2% | 2,000 | Derive from no-text pages | DocLayNet figure-only, blank pages | Need curation |

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
3. **Hebrew, Greek, Thai, SE_ASIAN_OTHER**: All depend heavily on synth-multiscript-250K

### 5.4 Stratification

- **Split**: 70/15/15 by source identity
- **Primary axes**: ml_class (19), text_scope (char/word/line/page), content_type (printed/handwritten/scene)
- **Leakage prevention**: MDIW13 doc/line/word from same source -> same split; COCO-Text by COCO image ID
- **Benchmarks reserved**: MLT19 val/test, COCO-Text val/test (never in training)
- **Rare class handling**: Tibetan 5-fold CV on ~200 real samples; Hebrew/Greek accept up to 80% synthetic; class weights from script_ml_classes.yaml (TIBT=2.0, SE_ASIAN_OTHER=1.8, GREK=1.5)

### 5.5 Source Composition

| Source | Samples Used | Scripts | Selection Strategy |
|--------|-------------|---------|-------------------|
| synth-multiscript-250K | ~60K | 27 scripts | Stratified sample matching target class distribution |
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
| Nepali Handwritten | 958 | Devanagari handwriting |
| NIST SD-19 | ~2K | US census handwriting forms |
| FUNSD | 199 | Mixed print+handwriting forms |
| DocLayNet (negatives) | ~15K | Printed-only (NONE class) |
| PubTabNet (negatives) | ~5K | Table-only (NONE class) |
| **Total** | **~60K** | |

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
| SYNTHETIC | 15% | 7,500 | DocSynth300K, synth-multiscript-250K | Ready (downsample) |

### 7.2 Diversity Requirements (beyond capture class)

| Dimension | Criticality | Target | Min/Category |
|-----------|-------------|--------|--------------|
| **Domain** | IMPORTANT | >= 5 domains per capture class | 200 per (capture, domain) cell |
| **Script family** | IMPORTANT | Latin 50%, >= 3 others at >= 5% | 500 per non-Latin per capture class |
| **Quality range** | IMPORTANT | Full 0-1 per capture class | 200 per quality quintile per class |

### 7.3 Critical Gaps

1. **SCANNER_ADF vs FLATBED**: No metadata distinguishes these. Need heuristic (edge feed marks, skew patterns)
2. **FAX**: RVL-CDIP has doc type labels but no explicit fax label. Need manual labeling ~500 + propagation
3. **Camera smartphone**: ~11K total; may need synthetic camera simulation on born-digital docs

---

## 8. Shadow Regression Dataset (~15K)

**Model**: SigLIP Group 5
**Task**: Regression (0-1 severity)

### 8.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Shadow severity** | CRITICAL | 40% none, 20% mild (0.1-0.3), 20% moderate (0.3-0.6), 20% severe (0.6-1.0) | 1,500 per non-none |
| **Shadow type** | IMPORTANT | 40% none, 25% hard (finger/object), 20% soft (lighting gradient), 15% mixed | 1,000 per type |
| **Capture method** | CRITICAL | 60% camera, 20% scanner, 20% born_digital (negatives) | 1,500 scanner |

### 8.2 Source Composition

| Source | Samples | Labels | Status |
|--------|---------|--------|--------|
| RealDAE | 583 pairs | Derive severity = 1 - SSIM(shadowed, clean) | Ready (need computation) |
| Doc3D | ~15K | Shadow maps from 3D geometry (tier_0_exact) | DEFERRED (209GB, P3) |
| SmartDoc-QA | 4,280 | Natural shadows (tier_3_heuristic) | Need severity annotation |
| MIDV500 | 3,612 | Variable lighting (tier_3_heuristic) | Need severity annotation |
| Synthetic shadow | ~5K | Born-digital + shadow overlay (tier_0_exact) | Need generation |

**Without Doc3D**: ~14K feasible (583 RealDAE + 4.3K SmartDoc + 3.6K MIDV + 5K synthetic)

---

## 9. Warping Regression Dataset (~20K)

**Model**: SigLIP Group 5
**Task**: Regression (0-1 severity)

### 9.1 Diversity Requirements

| Dimension | Criticality | Target Distribution | Min/Category |
|-----------|-------------|---------------------|--------------|
| **Warping severity** | CRITICAL | 30% none, 25% mild, 25% moderate, 20% severe | 2,000 per non-none |
| **Warping type** | IMPORTANT | 30% none, 25% page curl, 20% fold/crease, 15% perspective, 10% complex | 1,000 per type |
| **Capture method** | CRITICAL | 50% camera, 30% scanner (book spine curl), 20% born_digital (negatives) | 2,000 scanner |

### 9.2 Source Composition

| Source | Samples | Labels | Status |
|--------|---------|--------|--------|
| Doc3D | ~15K | Warping from 3D mesh (tier_0_exact) | DEFERRED (209GB, P3) |
| SmartDoc-QA | 4,280 | Perspective distortion | Need warping annotation |
| MIDV500 | 3,612 | Variable perspective | Need warping annotation |
| Synthetic TPS warping | ~5K | Born-digital + thin-plate-spline | Need generation |

**Without Doc3D**: ~13K feasible (4.3K SmartDoc + 3.6K MIDV + 5K synthetic)

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

### 12.2 Cross-Dataset Checks

| Check | Method | Red Flag |
|-------|--------|----------|
| Global split consistency | SHA256 -> split lookup across all datasets | Same image in train (task A) + test (task B) |
| Source overlap accounting | Matrix of shared source images | Undocumented overlap |
| Combined class distribution | Weighted merge | Single dataset > 50% of any class |
| Per-source contribution cap | Count per source dataset per class | Any single source > 40% of any class (consensus) |
| Cross-dimension interaction | Chi-square on (capture_method × script_family) cells | Any cell with 0 samples where both marginals > 0 (consensus) |

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

| Dataset | Capture | Script | Domain | Quality | Resolution | Content | Overall |
|---------|:-------:|:------:|:------:|:-------:|:----------:|:-------:|:-------:|
| Orientation (50K) | OK | OK | OK | OK | OK | OK | **READY** |
| Skew (40K) | TIGHT | OK | TIGHT | OK | OK | N/A | **NEEDS GEN** |
| Resolution (30K) | TIGHT | OK | TIGHT | N/A | OK | TIGHT | **NEEDS GEN** |
| IQA (16K) | **INSUFF** | **INSUFF** | **INSUFF** | OK | TIGHT | TIGHT | **GAPS** |
| Script (108K) | TIGHT | TIGHT* | INSUFF | N/A | OK | OK | **MOSTLY READY** |
| Handwriting (60K) | TIGHT | TIGHT | INSUFF | N/A | OK | OK | **NEEDS HARMONIZE** |
| Capture (50K) | OK | TIGHT | TIGHT | N/A | OK | N/A | **NEEDS LABELING** |
| Shadow (15K) | TIGHT | OK | N/A | N/A | OK | N/A | **NEEDS DOC3D** |
| Warping (20K) | TIGHT | OK | N/A | N/A | OK | N/A | **NEEDS DOC3D** |
| Code (10K) | OK | N/A | N/A | N/A | OK | N/A | **NEEDS CURATION** |

*Tibetan, Hebrew, Greek are tight; depend on synth-multiscript-250K

---

## 14. Synth-Multiscript-250K Assessment: Adjust, Not Redesign

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

With Tier A+B adjustments, synth-multiscript-250K becomes reusable across:

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

**Before**: Generate 250K images once → use only for script detection
**After**: Generate 250K base images → derive multiple training views via post-processing

```
synth-multiscript-250K (base)
├── Script labels (tier_0_exact) → Script Detection Dataset
├── + skew rotation → Skew Regression Dataset (10K subset)
├── + DPI re-rendering → Resolution Quality Dataset (5K subset)
├── + color mode conversion → Color mode diversity for all tasks
├── + orientation rotation → Additional orientation sources
├── IQA labels (tier_0_exact) → IQA Phase 2 pseudo-label pool
└── Capture method = "synthetic" → Capture Method Dataset
```

**Key principle**: Generate the base images ONCE, then apply task-specific transformations as post-processing steps. This avoids regenerating 250K images and maximizes reuse.

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

| Priority | Item | Effort | Blocks |
|----------|------|--------|--------|
| P0 | Skew dataset generation (40K) | 3-5 days | MobileNetV4 + SigLIP Group 3 |
| P0 | Resolution quality dataset (30K) | 3-4 days | MobileNetV4 + SigLIP Group 5 |
| P0 | Handwriting label harmonization | 3 days | SigLIP Group 4 |
| P1 | Capture method labeling (RVL-CDIP) | 2-3 days | SigLIP Group 5 |
| P1 | Code detection dataset curation (10K) | 3-4 days | SigLIP Group 5 |
| P2 | Doc3D extraction (209GB) | 1-2 days | Shadow + Warping |
| P2 | Shadow severity computation | 1 day | Shadow training |
| P2 | Warping severity annotation | 2 days | Warping training |
| P1 | Tibetan real page-level collection | 2-4 weeks | Script accuracy (elevated from P3 per consensus) |
| P3 | ADF vs flatbed distinction | 2 days | Capture method |
| P3 | Fax identification in RVL-CDIP | 1-2 days | Capture method |

---

## 15. Critical Files

| File | Purpose |
|------|---------|
| `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md` | Model architecture consuming these datasets |
| `docs/schema/layer2_enrichment_v2.schema.json` | Schema defining all diversity dimensions |
| `config/script_ml_classes.yaml` | 19 ML script classes with weights |
| `scripts/generate_orientation_dataset.py` | Template for dataset generation scripts |
| `src/image_preprocessing_detector/annotation/config/datasets.py` | Dataset registry with per-dataset metadata |
| `src/image_preprocessing_detector/annotation/schemas/enrichment.py` | Pydantic models for Layer 2 enrichment |

---

## 16. Implementation: Dataset Assembly Scripts

For each dataset that needs generation, create a script following the `generate_orientation_dataset.py` pattern:

| Script | Dataset | Key Logic |
|--------|---------|-----------|
| `scripts/generate_skew_dataset.py` | Skew (40K) | Random rotation ±10° on orientation sources; Hough labeling for natural scans |
| `scripts/generate_resolution_dataset.py` | Resolution (30K) | Multi-DPI rendering; char height measurement via connected components |
| `scripts/generate_handwriting_labels.py` | Handwriting (60K) | Harmonize HierText/COCO-Text/IAM labels to unified presence/legibility/content_type |
| `scripts/generate_code_dataset.py` | Code (10K) | Render GitHub code screenshots; label with syntax detection |
| `scripts/label_capture_method.py` | Capture (50K) | Heuristic classifier for ADF/fax on RVL-CDIP |
| `scripts/compute_shadow_severity.py` | Shadow (15K) | SSIM-based severity from RealDAE pairs; synthetic overlay |
| `scripts/compute_warping_severity.py` | Warping (20K) | TPS-based synthetic warping; perspective measurement |
| `scripts/verify_dataset_diversity.py` | ALL | Chi-square tests, coverage reports, split leakage checks |

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

```
training_weight = tier_base_weight * min(confidence, 1.0)
```

Where `tier_base_weight` is: tier_0_exact=1.0, tier_1_annotation=1.0, tier_2_model=0.8, tier_3_heuristic=0.5

This creates a smooth gradient that naturally down-weights uncertain labels without hard cutoffs.

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
