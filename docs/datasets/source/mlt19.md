---
dataset_id: mlt19
version: "1.0"
license: MIT
commercial_use: false
iqa_profiles:
  - scene_text
  - multi_script
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: complete
---

### MLT-19 (ICDAR 2019 Multilingual Text)

> **Quick Stats**: ~14 GB | 10 languages | Scene text | Script detection

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | ICDAR 2019 Multilingual Text Detection Dataset |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Competition** | ICDAR 2019 Robust Reading Competition |
| **Kaggle** | [zubairalibhutto/mlt-19-ocr-dataset](https://www.kaggle.com/datasets/zubairalibhutto/mlt-19-ocr-dataset) |
| **Official** | [rrc.cvc.uab.es](https://rrc.cvc.uab.es/?ch=15) |
| **License** | MIT |
| **Commercial Use** | Research only |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mlt19/` |
| **Documentation Status** | Complete |

##### 1.1 License & Commercial Use

- **License**: MIT
- **Commercial Use**: Research only (competition terms)
- **Citation Required**: Yes (see Section 9)
- **Redistribution**: Permitted under MIT terms; competition data may have additional restrictions from ICDAR 2019 organizers

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Scene text images (camera-captured) |
| **Annotations** | TXT | Per-word bounding boxes + language labels |
| **Metadata** | Inline | Per-image language distribution via GT files |

##### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `TrainImages/` | `TrainGT/*.txt` | 10,000 | ✅ |
| **Test** | `TestImages/` | - | 9,735+ | ⚠️ No public GT |

**Split Organization Pattern**: `by_folder`

> **Notes**:
>
> - Test images use `ts_img_NNNNN` prefix, train uses `tr_img_NNNNN`
> - Test GT never publicly released (standard ICDAR competition practice)
> - Train GT provides per-word language annotations

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Polygons** | TXT (8 coordinates) | Word | Quadrilateral bounding boxes per word |
| **Language Class** | TXT (per line) | Word | Language label per annotation |

> **Note**: Train split only. Test split requires visual detection.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Image-level** | Derived from GT files | Language distribution per image |
| **Annotation-level** | TXT files | Per-word language class |

##### 2.5 Annotation Schema Details

> **Format**: Custom TXT format - one line per text instance

```text
# Format: x1,y1,x2,y2,x3,y3,x4,y4,language_code
Example: 10,20,100,20,100,40,10,40,Latin
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `coordinates` | 8 integers | Yes | Polygon format (x,y for 4 corners) |
| `language` | str | Yes | 10 classes: Latin, Arabic, Chinese, Japanese, Korean, Bangla, Hindi, Symbols, Mixed, None |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Word polygons | `layout_annotations` | High | Convert to COCO format |
| ✅ Language labels | `language`, `script_family` | High | 10-class script detection |
| ❌ Text transcriptions | - | N/A | Not provided |
| ❌ Quality scores | - | N/A | Scene text dataset |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | ICDAR 2019 competition annotators |
| **Quality Assurance** | Competition-grade annotation with multi-language expert review |
| **GT Label Coverage** | 100% (train only; test GT not publicly released) |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 10A (Script Detection) |
| **Purpose** | Multi-script training for 10-class classification |
| **Local Path** | `01_base_data/language/mlt19/` |
| **Subset Used** | Full dataset (train + test) |
| **Preprocessing** | GT format conversion, test split VLM labeling |
| **Files** | 30,000 files, 14 GB |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`parse_mlt19_labels`](../../scripts/annotate_base_metadata.py#L2457) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `language_code`, `raw_labels.languages`, `bounding_boxes` |
| **Layer 2 Auto-Derived** | `script_family`, `iso639_language`, `text_direction`, `text_directions_present` |
| **Config Entry** | `DATASET_CONFIGS["mlt19"]` |

> **Parser Reference**: See [LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) for field mappings.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/mlt19/` | ✅ Available | 19,993 JPG files |
| **Text/OCR GT** | `TrainGT/*.txt` | ✅ Available (train only) | Per-word text with language labels |
| **Text/GT Converted** | `metadata_registry/extracted/mlt19/` | ✅ Converted | GT conversion: 10,000 images, 111,996 annotations, 540K chars |
| **Layout GT Converted** | `metadata_registry/extracted/mlt19/layout_batch_*.json` | ✅ Converted | COCO-style word-level layout with script class labels |
| **Layer 2 Metadata** | `metadata_registry/json/mlt19_metadata.json` | ✅ Available | Enrichment metadata v5 |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete

#### 4. Dataset Statistics

Coverage and distribution statistics for the MLT-19 dataset across train/test splits.

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 10,000 | 10,000 | 100% | ✅ Complete |
| **Test** | 9,657 | 9,657 | 100% | ✅ Complete |
| **Total** | 19,657 | 19,657 | 100% | ✅ All splits |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: Train (50.9%) has parser GT, Test (49.1%) has VLM-derived labels from contact sheet analysis.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 19,657 |
| **Training Split** | 10,000 (50.9%) |
| **Test Split** | 9,657 (49.1%) |
| **Image Dimensions** | Variable (scene photos) |
| **Resolution (DPI)** | Variable (camera-captured) |
| **File Format(s)** | JPG |
| **Color Space** | RGB |
| **Total Size on Disk** | ~14.3 GB |
| **Annotation Format** | TXT (train), VLM-derived (test) |

##### 4.3 Text Statistics (if ground truth text available)

> **Source**: Computed from ground truth text labels
> **Availability**: ✅ Available (train only)

**Ground Truth Conversion Stats (Train Split)**:

- **Images**: 10,000
- **Annotations**: 111,996 word-level instances
- **Total Characters**: 540K
- **Script Categories**: 10 classes

> **Note**: Text statistics are from word-level bounding box annotations with language labels,
> not full transcriptions. Test split requires Docling OCR pipeline for text statistics.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Scene text (natural images with text) |
| **Document Types** | Street signs, shop fronts, billboards, menus, traffic signs |
| **Language(s)** | 10 languages across 7 script families |
| **Temporal Range** | 2019 (competition dataset) |
| **Capture Method** | Camera/smartphone photography |

##### 5.1 Class/Category Distribution

**Script Classes (Train GT, 10,000 images)**:

| Category | Count (Approx) | Notes |
|----------|----------------|-------|
| Latin | ~2,671 | Conflates en/fr/de/it |
| Hindi (Devanagari) | ~1,800 | |
| Chinese (Hans) | ~1,500 | |
| Korean (Hangul) | ~1,200 | |
| Bangla (Bengali) | ~900 | |
| Arabic | ~800 | |
| Japanese | ~600 | |
| Symbols | varies | Non-script markers |
| Mixed | varies | Multi-script images |
| None | varies | No text detected |

##### 5.2 Class/Category Definitions

> **Purpose**: Define the 10 MLT19 script classes with ISO mappings.

| Class/Category | ID | Description | ISO Script | ISO Language |
|----------------|-----|-------------|------------|--------------|
| Latin | 1 | European languages (conflated) | Latn | en (used for all) |
| Arabic | 2 | Arabic script | Arab | ar |
| Chinese | 3 | Simplified/Traditional Chinese | Hans/Hant | zh |
| Japanese | 4 | Japanese (Han + Kana) | Jpan | ja |
| Korean | 5 | Hangul script | Hang | ko |
| Bangla | 6 | Bengali/Bangla script | Beng | bn |
| Hindi | 7 | Devanagari script | Deva | hi |
| Symbols | 8 | Non-linguistic symbols | Zsym | und |
| Mixed | 9 | Multiple scripts in same image | - | mul |
| None | 10 | No text detected | - | und |

> **Notes**:
>
> - Latin class includes English, French, German, Italian (KI-009: Latin language conflation)
> - Parser maps all Latin-script European languages to "en" (affects ~2,671 train samples, 13.6%)
> - **v5 refinement**: LLM enrichment resolves 1,731 Latin samples to specific European languages (fr/de/it)

##### 5.3 Language & Script Coverage

**Train Split (Layer 2 v5, 9,922 images)**:

| Language | ISO Code | Count | Coverage | Notes |
|----------|----------|------:|----------|-------|
| English | en | 2,251 | 22.7% | Confirmed English (parser + LLM agree) |
| Hindi | hi | 955 | 9.6% | Devanagari script |
| Korean | ko | 1,047 | 10.6% | Hangul script |
| Chinese | zh | 1,000 | 10.1% | Hans/Hant script |
| Bengali | bn | 994 | 10.0% | Beng script |
| Arabic | ar | 986 | 9.9% | Arab script |
| Japanese | ja | 937 | 9.4% | Jpan script |
| French | fr | 734 | 7.4% | Refined from Latin via LLM (v5) |
| German | de | 548 | 5.5% | Refined from Latin via LLM (v5) |
| Italian | it | 424 | 4.3% | Refined from Latin via LLM (v5) |
| Other European | es/pt/da/nl/etc. | 16 | 0.2% | Refined from Latin via LLM (v5) |
| Undetermined | und | 30 | 0.3% | 29 unclear test + 1 train |

**Test Split (VLM Contact Sheet, 9,735 images)**:

| Script | Count | Pct | ISO 639 |
|--------|------:|----:|---------|
| Latin | 8,046 | 82.7% | en |
| Devanagari | 1,102 | 11.3% | hi |
| Hangul | 193 | 2.0% | ko |
| Han (Chinese) | 164 | 1.7% | zh |
| Bengali | 124 | 1.3% | bn |
| Arabic | 41 | 0.4% | ar |
| Han (Japanese) | 36 | 0.4% | ja |
| Unclear | 29 | 0.3% | und |

**Script Families Present**: Latin, Arabic, Indic (Devanagari, Bengali), CJK (Han, Hangul, Japanese)

**Text Directions (v2.3.0)**:

- LTR (left-to-right): Latin, Devanagari, Bengali, CJK
- RTL (right-to-left): Arabic

#### 6. IQA Profile

Scene text captured via camera/smartphone with variable real-world lighting, perspective, and compression artifacts.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Scene text (camera-captured natural images) |
| **Capture Device** | Camera/smartphone (consumer-grade) |
| **Original Quality** | Variable (real-world photography) |
| **Compression** | JPEG (quality varies) |
| **Known Artifacts** | Natural lighting variance, perspective distortion, motion blur |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Small text on distant signs extremely sensitive |
| **Noise** | MEDIUM | Outdoor lighting + high ISO can introduce noise |
| **Skew** | LOW | Camera perspective expected (not document degradation) |
| **Contrast** | MEDIUM | Outdoor lighting varies (shadows, backlighting) |
| **Compression** | MEDIUM | JPEG artifacts on small text |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | 8-72pt (signs vary) | Small distant text sensitive to blur |
| **Line/Grid Density** | N/A | Scene text, not tabular |
| **Font Diversity** | HIGH | Commercial signage uses varied fonts |
| **Mathematical Notation** | Rare | Occasional scientific signs |
| **Color Usage** | HIGH | Multi-color signs common |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large-scale multi-script scene text for script detection |
| **Unique Characteristics** | 10-class script detection, scene text diversity |
| **Complementary Datasets** | Combine with synth-multiscript-250k, mdiw13 for multilingual training |
| **Benchmark Suitability** | HIGH - ICDAR 2019 competition dataset |
| **Known Limitations** | Scene text != document quality; Latin language conflation |

##### 6.5 Benchmark Results

> **Purpose**: ICDAR 2019 Robust Reading Competition results

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| Various | Multi-lingual Text Detection | F1 / Recall | Competition results | [ICDAR 2019 RRC](https://rrc.cvc.uab.es/?ch=15) |

**Competition Results**:

| Competition | Year | Winning Score | Winner |
|-------------|------|---------------|--------|
| ICDAR 2019 RRC-MLT | 2019 | Varies by task | Various teams |

> **Notes**:
>
> - Official competition leaderboard available at RRC website
> - Test GT never released publicly (standard competition practice)

#### 7. Known Issues & Limitations

**Known Limitations**:

1. **Latin language conflation (KI-009)**: Parser maps all Latin-script European languages (French, German, Italian) to "en" (English). Affects ~2,671 train samples (13.6%). Root cause: MLT19 GT uses "Latin" as a language class, not individual European languages.

2. **Test split GT holdout**: Test GT never publicly released (standard ICDAR competition practice). Test images (9,735) require visual detection via VLM contact sheets.

3. **Test split language accuracy (VR-001)**: VLM contact-sheet method at 50-per-sheet thumbnail resolution has ~33% language error rate on test split. Arabic test (72% error), Japanese test (44% error). CJK script confusion and cross-family contamination are primary error modes. Train split parser GT is 96.6% accurate by comparison.

4. **DocLayout-YOLO scene text (KI-003)**: 12.7% empty detections expected. Model trained on documents, not scene signs/banners. "figure" class maps to entire scene photos (100% FP for has_figure).

**Layer 2 Audit Findings**:

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| VR-001 | iso639_language | critical | OPEN | Test split VLM language labels ~33% error rate (ar_test 72%, ja_test 44%) |
| D02 | domain_level1 | low | DEFERRED | 80.7% UNK - acceptable for scene text (KI-007) |
| D08 | text_statistics | medium | DEFERRED | Requires Docling OCR pipeline |
| D12 | quality_overall | medium | DEFERRED | Requires IQA pipeline |
| D13 | layout_detections | low | DEFERRED | 12.7% empty - expected for scene text |

#### 8. Representative Samples

> Representative sample thumbnails not yet generated. See VLM contact sheets at `scripts/audit/results/mlt19/`.

**VLM Contact Sheet Analysis**: 195 sheets covering 9,735 test images with visual script identification.

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{nayef2019icdar2019,
  title={ICDAR2019 Robust Reading Challenge on Multi-lingual Scene Text Detection and Recognition -- RRC-MLT-2019},
  author={Nayef, Nibal and others},
  booktitle={ICDAR},
  year={2019}
}
```

##### Related Works

- [synth-multiscript-250k](synth-multiscript-250k.md) - Complementary synthetic multilingual dataset
- [mdiw13](mdiw13.md) - Multi-script document dataset
- [cocotext](cocotext.md) - English scene text dataset

##### Leaderboards

- [ICDAR 2019 Robust Reading Competition](https://rrc.cvc.uab.es/?ch=15)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Polygon format**: GT uses 8-coordinate polygon format (x,y for 4 corners), not COCO bounding boxes [x,y,w,h]. Conversion required for LayoutParser integration.
- **Language class "Latin"**: Encompasses en/fr/de/it without distinguishing individual languages. All mapped to "en" by parser.
- **Test split**: No public GT available. VLM contact sheet analysis (v3) resolved 9,706/9,735 test images. Only 29 "unclear" + 1 error remain.

##### 10.2 Processing & Implementation Notes

- **Filename prefixes**: Test images use `ts_img_NNNNN` prefix, train uses `tr_img_NNNNN`.
- **Metadata image_id**: Uses UUID-based image_id, not filename stem.
- **GT file format**: One line per text instance - `x1,y1,x2,y2,x3,y3,x4,y4,language_code`
- **Split derivation**: Layer 2 metadata `split` field derived from `source.split` (automatic).

##### 10.3 External Resources

- **Kaggle mirror**: [zubairalibhutto/mlt-19-ocr-dataset](https://www.kaggle.com/datasets/zubairalibhutto/mlt-19-ocr-dataset)
- **Download instructions**:

  ```bash
  pip install kaggle
  kaggle datasets download -d zubairalibhutto/mlt-19-ocr-dataset
  unzip mlt-19-ocr-dataset.zip -d /mnt/e/image_detection/01_base_data/language/mlt19/
  ```

- **Official competition**: [rrc.cvc.uab.es/?ch=15](https://rrc.cvc.uab.es/?ch=15)

---

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-13 | **Grade**: B (84.22/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 87.10 | 0.25 | 15-field v2.3.0 prescreening |
| Field Validity | 96.77 | 0.25 | Excellent where data exists |
| Doc Completeness | 100.00 | 0.15 | 11/11 sections per template v1.4.0 |
| Defect Rate | 45.80 | 0.15 | 3 deferred defects |
| Cross-Source Agreement | 83.80 | 0.10 | KI-009 Latin refinement improved agreement |
| VLM Accuracy | 80.00 | 0.10 | 4/5 passing samples correct |
| **Overall** | **84.22** | | **Grade B** |

**Enrichment Sources**:

| Source | Coverage | Used For |
|--------|----------|----------|
| Parser ground truth | 9,922 (50.5%, train only) | language, script (primary) |
| Train GT enrichment | 134 (0.7%, train low-conf) | language, script from GT files |
| VLM contact sheet | 9,706 (49.4%, test only) | language, script (visual identification) |
| LLM enrichment (text-only) | 9,989 (50.8%, train only) | domain, language, script, content_type |
| Language enrichment (OpenLID) | 1,000 (5.1%, train only) | language, script (fallback) |
| DocLayout-YOLO v1 | 17,165 (87.3%) | layout_detections, content flags |

**Prescreening Results** (post v4 integration, 15-field v2.3.0):

| Field | Pass Rate | Notes |
|-------|-----------|-------|
| split | 100% | Derived from source.split |
| capture_method | 100% | Hardcoded camera_smartphone (confidence 1.0) |
| script_family | 100% | Derived from iso15924_script |
| layout_bbox_valid | 100% | All bboxes valid where present |
| content_flags_boolean | 100% | VLM-corrected (34 images inspected) |
| orientation_class | 100% | Default 0 (upright), confidence 0.5 |
| image_properties_color_mode | 100% | All color (camera-captured) |
| handwriting_present | 100% | VLM-verified (3 true positives found) |
| quality_overall_mos | 100% | Present from v1 base annotation |
| text_direction | 100% | Derived from iso15924_script (v2.3.0) |
| text_directions_present | 100% | Aggregated from script + raw_labels (v2.3.0) |
| **iso639_language** | **99.85%** | Only 30 unclear samples remain (was 50.5% in v2) |
| **domain_level1** | **19.3%** | 80.7% UNK - expected for scene text (KI-007) |
| **layout_detections** | **87.3%** | 12.7% empty - expected for scene text |
| **text_has_content** | **0%** | DEFERRED - requires Docling OCR |

**Fields at 100%**: 11/15 | **Overall pass (all 15)**: 0% (driven by text_has_content)

##### 11.2 Key Defects

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D02 | domain_level1 | low | DEFERRED | 80.7% UNK - acceptable for scene text (KI-007) |
| D08 | text_statistics | medium | DEFERRED | Requires Docling OCR pipeline |
| D12 | quality_overall | medium | DEFERRED | Requires IQA pipeline |
| D13 | layout_detections | low | DEFERRED | 12.7% empty - expected for scene text |

##### 11.3 VLM Inspection Summary

**Content Flag Verification**:

| Flag | Flagged by Model | VLM True Positives | FP Rate |
|------|------------------|-------------------|---------|
| has_table | 14 | 12 | 14.3% |
| has_formula | 6 | 0 | 100% |
| has_figure | 13,009 | 0 | 100% (scene photo ≠ embedded figure) |
| has_handwriting | 0 (model) | 3 (VLM-discovered) | N/A |

**VLM Failing Sample Inspection**:

| Failure Category | Inspected | Finding |
|------------------|-----------|---------|
| Domain UNK (train) | 3 | All CORRECT - generic scene text (road/street signs) |
| Domain non-UNK | 3 | 2 correct, 1 questionable (restaurant menu as FIN) |
| Language und (test) | 3 | All KNOWN_GAP - visually identifiable but no source data |
| Empty layout | 3 | All EXPECTED - DocLayout-YOLO not designed for scene text |
| Passing samples | 5 | Domain mostly correct; Latin-script language mapping issue |

**Track C Passing Accuracy**: 80% (4/5 correct domain, 40% language correct due to Latin conflation)

**Language/Script Contact Sheet Validation** (v5, 2026-02-13):

20 contact sheets generated with 476 images sampled across all language categories (seed=42).
Visual inspection of tiled 5x5 grids (384x384 thumbnails) with overlaid metadata labels.

| Category | Method | Pool | Inspected | Correct | Accuracy | Notes |
|----------|--------|-----:|----------:|--------:|---------:|-------|
| en_train | parser_gt | 2,270 | 25 | 22 | 88% | ~3 KI-009 residual (LLM also said "en") |
| en_test | vlm_contact | 981 | 25 | 17 | 68% | Hindi/Korean/Arabic contamination |
| hi_train | parser_gt | 701 | 25 | 25 | 100% | Perfect Devanagari identification |
| hi_test | vlm_contact | 301 | 25 | 21 | 84% | French/Arabic misclassified |
| ko_train | parser_gt | 1,000 | 25 | 23 | 92% | ~2 Japanese/Korean CJK confusion |
| ko_test | vlm_contact | 500 | 25 | 18 | 72% | Bengali/Hindi/Chinese contamination |
| zh_train | parser_gt | 1,000 | 25 | 25 | 100% | Perfect Chinese identification |
| zh_test | vlm_contact | 500 | 25 | 20 | 80% | Korean/Bengali/Japanese confusion |
| bn_train | parser_gt | 701 | 25 | 25 | 100% | Perfect Bengali identification |
| bn_test | vlm_contact | 301 | 25 | 20 | 80% | Chinese/Hindi contamination |
| ar_train | parser_gt | 886 | 25 | 24 | 96% | 1 borderline bilingual sign |
| ar_test | vlm_contact | 41 | 25 | 7 | **28%** | SEVERE: Chinese/Korean/Bengali contamination |
| ja_train | parser_gt | 937 | 25 | 25 | 100% | Perfect Japanese identification |
| ja_test | vlm_contact | 360 | 25 | 14 | **56%** | Korean/French/Arabic contamination |
| fr_refined | gt+llm | 734 | 25 | 25 | 100% | KI-009 refinement validated |
| de_refined | gt+llm | 548 | 25 | 23 | 92% | ~2 international brand names |
| it_refined | gt+llm | 424 | 25 | 25 | 100% | KI-009 refinement validated |
| und_all | mixed | 30 | 25 | 20 | 80% | ~5 have readable text |
| low_conf | openlid | 1 | 1 | 0 | 0% | tt/Cyrl likely Arabic (trivial) |
| minor_eu | gt+llm | 25 | 25 | 21 | 84% | Brand name ambiguity |

**Summary by method**:

| Method | Sheets | Inspected | Correct | Accuracy |
|--------|-------:|----------:|--------:|---------:|
| parser_gt (train) | 7 | 175 | 169 | **96.6%** |
| parser_gt+llm_refined | 4 | 100 | 94 | **94.0%** |
| vlm_contact_sheet (test) | 7 | 175 | 117 | **66.9%** |

**Critical finding (VR-001)**: Test split language labels from VLM contact-sheet method have ~33%
error rate overall. Arabic test (72% wrong) and Japanese test (44% wrong) are most affected.
Primary error modes: CJK script confusion and cross-script-family contamination at thumbnail resolution.

**Validation artifacts**: `scripts/audit/results/mlt19/validation_sheets/` (20 sheets + manifest + report)

##### 11.4 Cross-Dataset Findings

> List any Known Issues (KI-NNN) discovered or confirmed during this audit.

- **KI-001**: DocLayout-YOLO class casing confirmed
- **KI-003**: Scene photo -> "figure" FP confirmed (universal for scene text datasets)
- **KI-007**: UNK domain validated for scene text (80.7% acceptable)
- **KI-009**: Latin language conflation (fr/de/it -> en) - NEW finding, affects 13.6% of train samples

**Audit Artifacts**: [scripts/audit/results/mlt19/](../../scripts/audit/results/mlt19/)

---

#### 12. Reliability & Bottlenecks

> **Purpose**: Auto-generated composite reliability summary identifying the weakest enrichment fields per dataset. Populated by `materialize_reliability_summary.py`.
>
> **Methodology**: Each enrichment field is assigned a confidence score (0.0-1.0). Missing/unrun fields get confidence=0.0. The composite min_confidence across all fields determines each sample's overall reliability category.

##### 12.1 Composite Category Distribution

> **Computed**: 2026-02-12 (post-audit) | **Samples**: 19,657

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 19,627 | 99.8% |
| active_learning | 0 | 0.0% |
| unreliable | 30 | 0.2% |

**Category Thresholds**: hard_label >= 0.9, soft_label >= 0.7, active_learning >= 0.5, unreliable < 0.5

##### 12.2 Top Bottleneck Fields

> The fields most frequently responsible for the lowest per-sample confidence.

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `domain` | 80.7% | 0.300 |
| 2 | `layout_detections` | 12.7% | 0.600 |
| 3 | `language` | 0.15% (train) / 33% (test) | 0.950 (train) / 0.67 (test VLM, validated) |

> **Improving Reliability**: Run the corresponding backfill script for the top bottleneck:
>
> - `domain` -> Expected for scene text (KI-007), update dataset config if needed
> - `layout_detections` -> Expected 12.7% empty rate for scene text (KI-003)
> - `language` -> Re-run VLM contact sheet or OpenLID for low-confidence samples

**Deferred Items**:

| Item | Prerequisite | Impact |
|------|--------------|--------|
| text_has_content / text_statistics | Docling OCR pipeline | Would enable text density analysis |
| quality_overall (IQA) | VLM IQA or classical IQA run | Would enable quality stratification |
| resolution_quality_score | PaddleOCR GPU session | Character-height-based quality |

---

#### Version History

| Version | Date | Changes |
|---------|------|---------|
| v5.1 (validation) | 2026-02-13 | Contact sheet validation (20 sheets, 476 images). Train 96.6%, test 66.9% accuracy. VR-001 critical defect: test split VLM labels ~33% error |
| v5 (integrated_v5) | 2026-02-13 | KI-009 Latin language refinement (1,731 samples: fr/de/it from LLM), doc restructure complete, grade B (84.22) |
| v4 (integrated_v4) | 2026-02-13 | Added v2.3.0 text_direction/text_directions_present fields, scorecard recomputation |
| v3 (integrated_v3) | 2026-02-12 | VLM contact sheet enrichment (9,735 test), train GT enrichment (134), DocLayout-YOLO standardization |
| v2 | 2026-02-12 | LLM enrichment + OpenLID language enrichment integration |
| v1 | 2026-02-10 | Initial base metadata + Docling layout enrichment |
