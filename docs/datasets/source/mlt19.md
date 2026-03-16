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
| **Total Images** | 19,657 (local; paper cites ~20,000; 336 source images unavailable) |
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

> **Audit Date**: 2026-02-15 | **Grade**: B (89.7/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 90.9 | 15% |  |
| Field Validity | 95.5 | 15% |  |
| Doc Completeness | 100.0 | 5% |  |
| Defect Rate | 81.2 | 10% |  |
| Cross-Source Agreement | 83.8 | 15% |  |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **89.7** | | **Grade B** |

##### 11.2 Key Defects

> **Total**: 17 defects (9 resolved, 4 accepted, 3 deferred, 1 partial)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| VR-001 | iso639_language | critical | ACCEPTED |  |
| VR-002 | iso639_language | medium | ACCEPTED |  |
| VR-003 | iso639_language | low | ACCEPTED |  |
| VR-004 | iso639_language | low | ACCEPTED |  |
| D01 | split | medium | RESOLVED | Split derived from source.split field. |
| D02 | domain_level1 | medium | PARTIALLY_RESOLVED | SCN blanket override + LLM enrichment. 80.7% remain UNK (expected for scene text per KI-007). |
| D03 | script_family | medium | RESOLVED | Derived from iso15924_script via get_script_family(). |
| D04 | orientation_class | low | RESOLVED | Default 0 (upright) with confidence 0.5 for scene text. |
| D05 | image_properties_color_mode | low | RESOLVED | All color (camera-captured natural images). |
| D06 | handwriting_present | medium | RESOLVED | Populated from has_handwriting with VLM corrections (3 true positives). |
| D07 | iso639_language | medium | RESOLVED | Multi-script per-image language detection integrated. |
| D08 | text_has_content (text_statistics) | medium | DEFERRED | Text extraction not yet run for scene text images. |
| D09 | layout_detections[*].class_name | medium | RESOLVED | Layout labels standardized to DocLayNet taxonomy via standardize_layout_labels.py. |
| D10 | has_figure | medium | RESOLVED | Verified via VLM inspection; false positives corrected. |
| D11 | iso15924_script | medium | RESOLVED | Derived from multi-script detection. |
| D12 | quality_overall | low | DEFERRED | Quality scoring not yet implemented for scene text. |
| D13 | layout_detections (empty) | medium | DEFERRED | 2,492 samples (12.7%) with empty layout detections. |

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

##### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/mlt19/](../../scripts/audit/results/mlt19/)

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

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 19,657 | **Avg Min Confidence**: 0.411

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 822 | 4.2% |
| active_learning | 5,948 | 30.3% |
| unreliable | 12,887 | 65.6% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `layout_detections` | 99.3% | 0.411 |
| 2 | `has_table` | 0.7% | 0.800 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~10,000 | VLM-derived (train only; test ~33% error) | Scene text signs appear at various angles; train-split orientation labels (D04 resolved) are usable but not primary orientation source; test split VLM labels have ~33% error (VR-001) and should be excluded |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | No document skew labels; camera perspective distortion is not equivalent to document page skew |
| MNV4-H3 | resolution_quality_reg | ➖ | 0 | N/A | No resolution quality labels computed; PaddleOCR pipeline not run |
| SIG-G1-1 | blur_score | ➖ | 0 | N/A | No IQA blur labels; scene blur from camera distance/motion is present but unlabeled |
| SIG-G1-2 | noise_score | ➖ | 0 | N/A | No IQA noise labels; outdoor high-ISO noise present but unlabeled |
| SIG-G1-3 | contrast_score | ➖ | 0 | N/A | No IQA contrast labels; outdoor lighting variance present but unlabeled |
| SIG-G1-4 | skew_score | ➖ | 0 | N/A | No skew score labels; camera perspective != document skew metric |
| SIG-G1-5 | compression_score | ➖ | 0 | N/A | No IQA compression labels; JPEG artifacts present but unlabeled |
| SIG-G1-6 | overall_quality | ➖ | 0 | N/A | No IQA overall quality labels |
| SIG-G2-1 | script_cls | ✅ Primary | ~19,657 | Human GT (train 10K) + VLM-derived (test 9.6K, lower accuracy) | 7 ISO 15924 classes: Latn(54.5%), Deva(10.4%), Hang(6.0%), Arab(5.2%), Hans(5.1%), Jpan(4.8%), Beng(4.6%); train GT is 96.6% accurate; test VLM accuracy ~67% overall (arabic 28%, japanese 56%; see VR-001); use train split preferentially for high-confidence script labels |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~10,000 | VLM-derived (train only) | Scene-captured text signs appear rotated; post-correction orientation signal available from train split with ~96% language accuracy; test split excluded due to VR-001 |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | N/A | Camera perspective distortion is not post-correction document skew; no applicable labels |
| SIG-G4-1 | handwriting_presence_cls | ❌ | ~3 | N/A | content_flags has_handwriting = 0.0% (only 3 of 19,657 samples); essentially all printed scene text; not a useful handwriting source |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | N/A | No handwriting content; no legibility labels |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | N/A | No handwriting content; no content type labels |
| SIG-G4-4 | presence_reg | ❌ | 0 | N/A | Effectively 0.0 presence score for all samples; not useful for regression training |
| SIG-G4-5 | legibility_reg | ❌ | 0 | N/A | No handwriting; no legibility regression labels |
| SIG-G5-1 | capture_method_cls | ✅ Primary | ~19,657 | Derived from dataset capture method (100% camera_smartphone) | 100% real labels; pure "camera" class contribution; 19,657 samples for the camera/smartphone stratum of the 7-class capture_method head; all real (no synthetic mixing) |
| SIG-G5-2 | shadow_reg | ➖ | 0 | N/A | Natural scene shadows present but no shadow severity labels; would require dedicated shadow labeling pipeline |
| SIG-G5-3 | warping_reg | ➖ | 0 | N/A | Camera perspective present but no warping severity labels; no warping annotation pipeline run |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | Scene text (street signs, billboards); no code/programming content present |
| SIG-G5-5 | resolution_quality_reg | ➖ | 0 | N/A | No resolution quality labels computed; variable camera resolution but unlabeled |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ Well-covered | 6 families: Latin (54.5%), CJK (16.7% — Han/Hangul/Jpan), Indic (15.0% — Deva+Beng), Arabic (5.2%), Other/symbols (8.6%), Cyrillic (0.0%); 11 distinct ISO 15924 codes; complements mdiw13 with camera-captured scene text perspective |
| 2 | Capture method | 🟡 Partial | 100% camera_smartphone; excellent camera representation; no scanner or born_digital diversity; ideal complement to mdiw13 (scanner) for capture_method head |
| 3 | Document domain | ✅ Well-covered | domain_level1 = SCN (scene text) for 100%; broad scene diversity: street signs, billboards, menus, shop fronts, traffic signs across 10 countries |
| 4 | Layout type | ❌ Not present | No layout_type labels; DocLayout-YOLO returns 12.7% empty detections on scene text (KI-003); scene text is not document-layout structured |
| 5 | Text density | 🟡 Partial | text_scope=phrase for 100% (word/phrase level); scene images have variable text density but density is not directly labeled |
| 6 | Degradation types | ❌ Not present | No degradation type labels; degradation_types dict empty in aggregates; natural scene degradation (blur, lighting, compression) present but unlabeled |
| 7 | Resolution/DPI range | ✅ Well-covered | Variable camera resolution (consumer smartphones to DSLRs); scene photos span low to high pixel density; text size varies 8-72pt on signage at varying distances |
| 8 | Document age | ❌ Not present | No document_age labels; scene photography from 2019 (modern); historical content absent |
| 9 | Text scope | 🟡 Partial | 100% phrase-level text scope; word/phrase crops from scene images; no full-page or document-level scope |
| 10 | Content flags | 🟡 Partial | has_table=0.1% (12 samples), has_handwriting=0.0% (3 samples); no formula/code flags; largely print-only scene text |
| 11 | Binarization status | ❌ Not present | All color RGB images (D05 resolved); no binarized samples; no binarization status labels |
| 12 | Artifact types | 🟡 Partial | JPEG compression artifacts present (variable quality); motion blur common; no artifact type labels; natural real-world imaging conditions cover broad artifact space |
| 13 | Color mode | 🟡 Partial | 100% color RGB (camera_smartphone); no grayscale or binarized variety; good color diversity from real-world scene photography |
| 14 | Font variety | ✅ Well-covered | Extremely high font diversity — commercial signage across 10 countries uses varied display, serif, sans-serif, handwritten-style, and custom fonts; multilingual typography across 7 script families |

### 13.3 Corpus Role & Constraints

MLT19 is a primary contributor to SIG-G2-1 `script_cls` for the camera-captured scene text distribution, providing 10,000 human-GT-labeled train images (96.6% language accuracy) and 9,657 VLM-labeled test images (67% accuracy; test split should be downweighted or excluded for high-precision script heads). It is the sole 100%-camera dataset for SIG-G5-1 `capture_method_cls`, contributing all 19,657 images to the camera/smartphone stratum. The Latin language conflation (KI-009: all European Latin-script languages mapped to "en" for train split, partially resolved via LLM refinement in v5) means Latin-script subclass precision is reduced; this does not affect the script-family level classification but limits language-level training signal.
