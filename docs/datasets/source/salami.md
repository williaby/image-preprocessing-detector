---
dataset_id: salami
version: "1.0"
license: CC-BY-4.0
commercial_use: true
iqa_profiles:
  - legibility_calibration
  - multi_script
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: complete
---

#### SALAMI (Statistical Analysis of Legibility Assessment Maps and Images)

> **Quick Stats**: 250 manuscript images | Scanner (flatbed) | 8 scripts | 20 expert annotators | 4,811 region-level assessments | CC-BY-4.0
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Statistical Analysis of Legibility Assessment Maps and Images |
| **Version** | 1.0 |
| **Release Date** | 2020-11-11 |
| **Maintainer** | Vlad Atanasiu et al. |
| **Paper** | [SALAMI: Statistical Analysis of Legibility Assessment Maps and Images](https://zenodo.org/records/4270352) |
| **Repository** | [Zenodo: 10.5281/zenodo.4270352](https://zenodo.org/records/4270352) |
| **License** | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Commercial Use** | Yes |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Input Images** | PNG | 250 historical manuscript page images |
| **Mean Score Maps** | PNG | 250 pixel-level mean legibility maps |
| **Std Maps** | PNG | 250 pixel-level uncertainty (std) maps |
| **Assessments** | JSON | 4,811 region-level legibility annotations |
| **Image Metadata** | JSON | 250 image records (language, batch) |
| **User Profiles** | JSON | 20 expert assessor profiles |

##### 2.2 Dataset Split Locations

> **Split Organization**: No official train/test/val splits. All 250 images organized by batch.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **All** | `salami_1.0/images/input/*.png` | `salami_1.0/src/assessments.json` | 250 | ✅ Available |

**Split Organization Pattern**: `single_dir_with_manifest` (images in one directory, shared JSON annotations)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Legibility Ratings** | JSON | Region-level | 5-level scale: 0-20%, 20-40%, 40-60%, 60-80%, 80-100% readable |
| **Legibility Maps** | PNG | Pixel-level | Mean score per pixel (pre-computed from 20 experts) |
| **Uncertainty Maps** | PNG | Pixel-level | Standard deviation of expert scores per pixel |
| **Language Labels** | JSON | Image-level | 8 scripts: Armenian, Georgian, German, Gothic, Greek, Latin, Ottoman, Slavonic |
| **Expert Profiles** | JSON | Assessor-level | Academic level, environment, language expertise, MSI experience |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Zenodo record | Version, license, citation |
| **Image-level** | `images.json` | Image ID, language, batch assignment |
| **Assessor-level** | `users.json` | 20 expert profiles with language expertise ratings |
| **Assessment-level** | `assessments.json` | Region bounding boxes, ratings, assessor ID |

##### 2.5 Annotation Schema Details

**assessments.json** (4,811 region-level entries):

```json
{
  "img_id": "00_00",
  "user_id": "05",
  "annotations": [
    {
      "x": 100,
      "y": 200,
      "width": 300,
      "height": 150,
      "rating": "60-80% readable"
    }
  ]
}
```

**images.json** (250 entries):

```json
{
  "id": "00_00",
  "lang": "Greek",
  "batch": "00"
}
```

**users.json** (20 entries):

```json
{
  "id": "05",
  "academic_level": 2,
  "environment": "online",
  "lang_Greek": 3,
  "lang_Latin": 2,
  "msi_experience": 3
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `img_id` | string | Yes | Matches image filename stem (`{batch}_{idx}`) |
| `lang` | string | Yes | Language name (maps to ISO 15924 script) |
| `rating` | string | Yes | 5-level legibility scale |
| `user_id` | string | Yes | Links to expert profile |
| `x`, `y`, `width`, `height` | int | Yes | Region bounding box (COCO-like) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Legibility ratings | `legibility_score` | **High** | 5-level scale, multi-expert consensus |
| ✅ Language/script | `iso15924_script_code` | **High** | 8 scripts mapped to ISO 15924 codes |
| ✅ Region bounding boxes | `layout_detections` | **Medium** | COCO-like x,y,w,h format |
| ✅ Expert agreement | `assessment_count`, `expert_count` | **Medium** | Multi-expert calibration data |
| ✅ Pixel-level legibility maps | `legibility_map_path` | **Medium** | Pre-computed mean + std maps |
| ⚠️ Expert profiles | `expert_metadata` | **Low** | Language expertise levels, academic background |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert (20 trained assessors) |
| **Provenance Tier** | Tier 0 (Exact) - multi-expert consensus with computed agreement |
| **Annotator Details** | 20 experts: academic levels 1-4, lab + online environments |
| **Inter-Annotator Agreement** | Captured via std_maps (pixel-level standard deviation across 20 experts) |
| **Quality Assurance** | Pre-computed mean and std maps from 20 independent expert assessments |
| **GT Label Coverage** | 100% (every image has multiple expert assessments) |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | SigLIP 2 multi-task training (legibility calibration) |
| **Purpose** | Gold-standard calibration anchor for handwriting legibility heads |
| **Local Path** | `01_base_data/handwriting/salami/` |
| **Subset Used** | Full dataset (250 images) |
| **Preprocessing** | None required (PNG images + JSON annotations) |

##### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`SalamiParser`](../../../src/image_preprocessing_detector/annotation/parsers/handwriting/salami.py) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `legibility_score`, `language`, `iso15924_script_code`, `assessment_count` |
| **Layer 2 Auto-Derived** | `has_handwriting=True`, per-image script from `images.json` |
| **Config Entry** | `DATASET_CONFIGS["salami"]` |

##### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Input Images** | `01_base_data/handwriting/salami/salami_1.0/images/input/` | ✅ Available | 250 PNG manuscript images |
| **Mean Score Maps** | `01_base_data/handwriting/salami/salami_1.0/images/mean_score_maps/` | ✅ Available | 250 pixel-level legibility maps |
| **Std Maps** | `01_base_data/handwriting/salami/salami_1.0/images/std_maps/` | ✅ Available | 250 uncertainty maps |
| **Annotations** | `01_base_data/handwriting/salami/salami_1.0/src/` | ✅ Available | assessments.json, images.json, users.json |
| **Layer 2 Metadata** | - | ❌ Not generated | Pending Layer 2 annotation pipeline |

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **Note**: No official train/test/val splits. All 250 images used as calibration anchor.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **All** | 250 | 0 | 0% | ❌ Pending Layer 2 |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 250 (input) + 250 (mean maps) + 250 (std maps) |
| **Assessments** | 4,811 region-level entries |
| **Expert Assessors** | 20 |
| **Languages** | 8 (Armenian, Georgian, German, Gothic, Greek, Latin, Ottoman, Slavonic) |
| **Batches** | Multiple (organized by `{batch}_{idx}`) |
| **File Format(s)** | PNG (images/maps), JSON (annotations) |
| **Total Size on Disk** | 83 MB (archive) |

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Historical manuscripts (multi-language, multi-century) |
| **Document Types** | Manuscript page images |
| **Language(s)** | 8 languages across 7 script families |
| **Temporal Range** | Historical (multi-century) |
| **Acquisition Method** | Archival scanning (flatbed) |

##### 5.3 Language & Script Coverage

| Script/Language | ISO 15924 | Samples | Notes |
|-----------------|-----------|---------|-------|
| Armenian | Armn | [NEEDS_PROFILING] | Armenian manuscript pages |
| Georgian | Geor | [NEEDS_PROFILING] | Georgian manuscript pages |
| German | Latn | [NEEDS_PROFILING] | Latin script, German language |
| Gothic | Goth | [NEEDS_PROFILING] | Gothic script manuscripts |
| Greek | Grek | [NEEDS_PROFILING] | Greek manuscript pages |
| Latin | Latn | [NEEDS_PROFILING] | Latin script, Latin language |
| Ottoman | Arab | [NEEDS_PROFILING] | Arabic script, Ottoman Turkish |
| Slavonic | Cyrl | [NEEDS_PROFILING] | Cyrillic script, Church Slavonic |

**Script Families Present**: Armenian, Georgian, Latin, Gothic, Greek, Arabic, Cyrillic (7 families)

> **Note**: Exact per-language counts available from `images.json` but not yet profiled.

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Scanned historical manuscripts (archival quality) |
| **Capture Device** | Archival flatbed scanner |
| **Original Quality** | Variable (clean to illegible, as measured by 20 experts) |
| **Compression** | PNG (lossless) |
| **Known Artifacts** | Aging, ink degradation, bleed-through, fading |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Historical manuscripts with fine text strokes |
| **Noise** | MEDIUM | Aging artifacts on historical paper |
| **Contrast** | HIGH | Ink fading is directly measured by legibility assessments |
| **Compression** | LOW | Stored as PNG (lossless) |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | CRITICAL - Gold-standard legibility calibration with 20-expert pixel-level consensus |
| **Unique Characteristics** | Multi-expert agreement maps, 5-level legibility scale, 8 scripts, uncertainty quantification |
| **Complementary Datasets** | Muharaf (Arabic legibility), GNHK (illegible handwriting), HierText |
| **Benchmark Suitability** | HIGH - Multi-expert consensus provides reliable ground truth |
| **Known Limitations** | Small dataset (250 images), no text transcriptions, historical only |

#### 7. Known Issues & Limitations

- **Small Size**: Only 250 images (designed as calibration anchor, not primary training data)
- **No Text Transcriptions**: Only legibility ratings, not character-level OCR ground truth
- **Historical Only**: All manuscripts are historical; no modern handwriting
- **Multi-Script Complexity**: 8 different scripts require per-image script detection

#### 9. References

##### Primary Citation

```bibtex
@misc{atanasiu2020salami,
  title={SALAMI: Statistical Analysis of Legibility Assessment Maps and Images},
  author={Atanasiu, Vlad and others},
  year={2020},
  doi={10.5281/zenodo.4270352},
  publisher={Zenodo}
}
```

##### Related Works

- [Muharaf](muharaf.md) - Arabic historical handwriting (legibility variation)
- [GNHK](gnhk.md) - Illegible handwriting seed data

#### 10. Dataset-Specific Notes

##### 10.1 Legibility Rating Scale

The 5-level rating scale maps to numeric midpoint scores:

| Rating | Description | Numeric Score |
|--------|-------------|---------------|
| 0-20% readable | Very illegible | 0.1 |
| 20-40% readable | Mostly illegible | 0.3 |
| 40-60% readable | Partially readable | 0.5 |
| 60-80% readable | Mostly readable | 0.7 |
| 80-100% readable | Clearly readable | 0.9 |

##### 10.2 Expert Profiles

20 assessors with documented expertise:

- **Academic Levels**: 1-4 (undergraduate to professor)
- **Environments**: Lab (controlled) and Online (remote)
- **Language Expertise**: Self-reported 0-3 proficiency per language
- **MSI Experience**: 1-3 (manuscript image experience level)

##### 10.3 Gap Closure

SALAMI closes the legibility calibration gap (SIG-G4-2, SIG-G4-5):

- **Before**: No multi-expert legibility ground truth for handwriting quality assessment
- **After**: 250 images with 20-expert pixel-level consensus maps + 4,811 region ratings
- **Role**: Gold-standard calibration anchor for legibility model training
- **Heads Served**: SIG-G4-2 (legibility_cls), SIG-G4-5 (legibility_reg)

##### 10.4 Pre-Computed Maps

Mean score maps and std maps are pre-computed from all 20 expert assessments:

- **Mean map**: Per-pixel average legibility score across all assessors
- **Std map**: Per-pixel standard deviation (uncertainty/disagreement measure)
- **Usage**: Can be used directly as regression targets for pixel-level legibility prediction

---

#### 13. Training Head Coverage

##### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ | -- | N/A | No orientation labels |
| MNV4-H2 | skew_reg | ❌ | -- | N/A | No skew angle labels |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~250 | tier_3_heuristic | Scanner-captured; quality varies by manuscript age |
| SIG-G1-1 | blur_score | 🟡 | ~250 | tier_3_heuristic | Legibility correlates with blur; indirect signal |
| SIG-G1-2 | noise_score | 🟡 | ~250 | tier_3_heuristic | Aging artifacts provide noise diversity |
| SIG-G1-3 | contrast_score | 🟡 | ~250 | tier_3_heuristic | Ink fading varies contrast; legibility captures this |
| SIG-G1-4 | skew_score | ❌ | -- | N/A | No skew quality labels |
| SIG-G1-5 | compression_score | ❌ | -- | N/A | PNG (lossless) |
| SIG-G1-6 | overall_quality | 🟡 | ~250 | tier_2_model | Legibility maps provide quality proxy |
| SIG-G2-1 | script_cls | ✅ | ~250 | tier_1_annotation | 7 script families from images.json (Armn, Geor, Latn, Goth, Grek, Arab, Cyrl) |
| SIG-G3-1 | orientation_cls (post) | ❌ | -- | N/A | No orientation labels |
| SIG-G3-2 | skew_reg (post) | ❌ | -- | N/A | No skew labels |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~250 | tier_1_annotation | 100% handwritten manuscripts |
| SIG-G4-2 | handwriting_legibility_cls | ✅ | ~250 | tier_0_exact | 20-expert consensus; 5-level scale; GOLD STANDARD calibration |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | ~250 | tier_1_annotation | Historical manuscript handwriting; CURSIVE class |
| SIG-G4-4 | presence_reg | ✅ | ~250 | derived | Full-page manuscripts; area ratio = 1.0 |
| SIG-G4-5 | legibility_reg | ✅ | ~250 | tier_0_exact | Pre-computed mean score maps from 20 experts; GOLD STANDARD |
| SIG-G5-1 | capture_method_cls | ✅ | ~250 | tier_1_annotation | 100% archival scanner; SCANNER class |
| SIG-G5-2 | shadow_reg | ❌ | -- | N/A | Controlled archival scanning |
| SIG-G5-3 | warping_reg | ❌ | -- | N/A | Flat archival scans |
| SIG-G5-4 | code_cls | ❌ | -- | N/A | Historical manuscripts; no code |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~250 | tier_3_heuristic | Archival scanner; pending IQA pipeline |

##### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 7 families: Armn, Geor, Latn, Goth, Grek, Arab, Cyrl |
| 2 | Capture method | ✅ | Archival scanner (100%) |
| 3 | Document domain | 🟡 | Historical manuscripts only |
| 4 | Layout type | 🟡 | Full manuscript pages; no multi-column or tabular |
| 5 | Text density | 🟡 | Variable (historical manuscript text density) |
| 6 | Degradation types | ✅ | Aging, ink fading, bleed-through — with quantified legibility |
| 7 | Resolution/DPI range | 🟡 | Archival scanner; unquantified |
| 8 | Document age | ✅ | Historical manuscripts (multi-century) |
| 9 | Text scope | 🟡 | Page-level only |
| 10 | Content flags | ✅ | has_handwriting=100% |
| 11 | Binarization status | 🟡 | Color/grayscale PNG (not binarized) |
| 12 | Artifact types | ✅ | Aging, ink degradation, bleed-through, fading — quantified by expert consensus |
| 13 | Color mode | 🟡 | Color scans |
| 14 | Font variety | ❌ | Handwriting only; multi-script historical styles |

##### 13.3 Corpus Role & Constraints

SALAMI is the gold-standard calibration anchor for handwriting legibility assessment heads
(SIG-G4-2, SIG-G4-5), providing the only multi-expert pixel-level legibility ground truth
in the corpus. With 20 expert assessors providing 4,811 region-level ratings across 250
manuscripts in 7 script families, it enables reliable calibration of legibility regression
and classification models. Despite its small size (250 images), it serves an outsized role
as the confidence anchor — all other legibility scores in the corpus can be calibrated
against SALAMI's expert consensus. CC-BY-4.0 permits commercial training without restriction.
