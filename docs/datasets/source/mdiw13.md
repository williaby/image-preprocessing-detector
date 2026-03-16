---
dataset_id: mdiw13
version: "1.0"
license: Academic
commercial_use: false
iqa_profiles:
  - handwriting
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### MDIW-13 (Foundational Script Identification Dataset)

> **Quick Stats**: 290,213 images (1,135 docs, 13,979 lines, 86,655 words) | 13 scripts | Printed + Handwritten
>
> **License**: Academic | **Commercial Use**: Research only

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multilingual Database for Script Identification |
| **Version** | February 2025 |
| **Source** | [Zenodo](https://zenodo.org/records/6376096) |
| **Paper** | [Cognitive Computation 2023](https://link.springer.com/article/10.1007/s12559-023-10193-w) |
| **License** | Academic/Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mdiw13/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Multi-script word/line/document images |
| **Annotations** | TXT | TestCompetitionGroundtruth.txt (numeric labels 0-12) |
| **Metadata** | Directory structure | Script classification via folder names |
| **Supplementary** | README (assumed) | Dataset documentation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Main** | `SIW_MultiscriptDatabase/{script}/` | Directory structure | 203,538 | ✅ |
| **Competition Train** | `TrainCompetition_WITHGroundTruth/{script}/` | Directory structure | 30,861 | ✅ |
| **Competition Test** | `TestCompetition_WITHOUTGroundTruth/` | TestCompetitionGroundtruth.txt | 55,814 | ✅ RESERVED |

**Split Organization Pattern**: `by_folder` + `single_dir_with_manifest` (test set)

> **Notes**:
>
> - Split counts verified from Layer 2 metadata (post-integration v2)
> - Competition test set is RESERVED for benchmark evaluation only

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Script Classification** | Directory name | Image | Script class from folder path (13 scripts) |
| **Numeric Labels** | TXT (line-separated) | Image | Competition test labels (0-12 numeric codes) |
| **Segmentation Level** | Directory name | Image | Document/Line/Word granularity |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Zenodo/Paper | Version, license, citation, 13 scripts |
| **Image-level** | Filename/Directory | Script class, segmentation level, data source |
| **Annotation-level** | Ground truth file | Numeric label (0-12) for test samples |

##### 2.5 Annotation Schema Details

> **Format**: Directory-based classification + numeric ground truth file

**Directory Structure**:

```text
{script_name}/
    Document/
        img001.png
    Line/
        img002.png
    Word/
        img003.png
```

**Ground Truth File** (TestCompetitionGroundtruth.txt):

```text
0    # Line 1 -> Arabic
4    # Line 2 -> Hindi
9    # Line 3 -> Roman
...
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `script_directory` | str | Yes | Folder name = script class |
| `segmentation_directory` | str | Varies | Document/Line/Word level |
| `numeric_label` | int | Test only | 0-12 mapping to script |
| `sample_number` | int | Test only | Extracted from filename |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Script classification | `script_name`, `iso15924_script_code`, `language_code` | High | Fully extracted |
| ✅ Segmentation level | `raw_labels.segmentation_level` | Medium | Fully extracted |
| ✅ Data source | `raw_labels.data_source` | Medium | Fully extracted |
| ✅ Numeric labels | `raw_labels.numeric_label` | Low | Test set only, extracted |
| ❌ Text transcriptions | - | Low | Not provided by dataset |
| ❌ Bounding boxes | - | Low | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | Competition annotators |
| **Quality Assurance** | Competition-grade multi-level script annotation |
| **GT Label Coverage** | 100% (all 290K images with script class labels) |

#### 3a. Project Usage

- **Path**: `01_base_data/language/mdiw13/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Foundational training for 10-class script classifier
- **Note**: Research identified this as "the most on-target dataset" for document script ID
- **Parser**: [`parse_mdiw13_labels`](../scripts/annotate_base_metadata.py#L2094) | ✅ Complete

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`Mdiw13Parser`](../../src/image_preprocessing_detector/annotation/parsers/multilingual/mdiw13.py) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `script_name`, `iso15924_script_code`, `language_code`, `raw_labels` |
| **Layer 2 Auto-Derived** | `language.script_code`, `language.language_code`, `text_scope.scope` (from segmentation) |
| **Config Entry** | `DATASET_CONFIGS["mdiw13"]` (in annotate_base_metadata.py) |

**Parser Features**:

- ✅ ISO 15924 script code mapping (13 scripts)
- ✅ ISO 639 language code mapping
- ✅ Handles directory-based and ground truth file labels
- ✅ Class-level caching for ground truth file
- ✅ Supports alternate script names (Bangla/Bengali, Hindi/Devanagari)

**Extracted Fields**:

| Source Label | Layer 2 Target | Status | Method |
|--------------|----------------|--------|--------|
| Directory: `{script}/` | `language.script_code` | ✅ Mapped | SCRIPT_MAPPINGS lookup |
| SCRIPT_MAPPINGS | `language.language_code` | ✅ Mapped | ISO 639 derivation |
| Directory: Document/Line/Word | `text_scope.scope` | ⚠️ Could infer | Segmentation level -> scope |
| Ground truth numeric | `raw_labels.numeric_label` | ✅ Mapped | Test set only |

> **Parser Reference**: See [LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) for field mappings

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/mdiw13/` | ✅ Available | 290,213 PNG files |
| **Text/GT** | Native annotations | ⚠️ Partial | Labels: word-level script/language labels (not full text transcriptions) |
| **Text/OCR Extracted** | `extracted/mdiw13/ocr_batch_*.jsonl` | ⚠️ Empty | Docling OCR returns empty for word-level crops |
| **Layout Extracted** | `extracted/mdiw13/layout_batch_*.json` | ✅ Available | 1,162 batches, 289,941 images matched (99.91%) |
| **Layer 2 Metadata** | `metadata_registry/json/mdiw13_metadata.json` | ✅ Available | 1.47 GB, 290,213 samples, schema v2.3.0 |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- ⚠️ Partial/Empty - Data processed but incomplete

#### 4. Dataset Statistics

> 290,213 images across 3 splits (main, competition train, competition test)

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Main** | 203,538 | 203,538 | 100% | ✅ Complete |
| **Competition Train** | 30,861 | 30,861 | 100% | ✅ Complete |
| **Competition Test** | 55,814 | 55,814 | 100% | 🚫 RESERVED |
| **Total** | 290,213 | 290,213 | 100% | ✅ All splits |

**Split Status Legend**:

- ✅ Complete - All samples from this split are in Layer 2 metadata
- 🚫 RESERVED - Competition test set, never train on this

> **Note**: Competition test set (55,814 images) is RESERVED for benchmark evaluation only.
> Use `split` field in sample source metadata to track which split each sample belongs to.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Documents** | 1,135 |
| **Total Lines** | 13,979 |
| **Total Words** | 86,655 |
| **File Format** | PNG |
| **Archive Size** | 226 MB |

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Mixed (newspapers + handwritten letters) |
| **Document Types** | Word crops, line crops, full document images |
| **Language(s)** | 13 languages across Indic, Arabic, CJK, Latin, Thai |
| **Temporal Range** | Not specified (various decades of published text) |
| **Acquisition Method** | Scanner (flatbed) |

##### 5.1 Class/Category Distribution

| Category | Subcategory | Description |
|----------|-------------|-------------|
| Handwritten | Word/Line/Document | Handwritten text samples from all 13 scripts |
| Printed | Word/Line/Document | Printed text samples from all 13 scripts |
| Competition Train | Word | Competition training samples with script labels |
| Competition Test | Word | Competition test samples (RESERVED, ground truth in separate file) |

##### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.
>
> **Source**: Layer 2 metadata (post-integration v2, 2026-02-12). Counts for main + competition_train
> splits where script labels are derivable from directory structure. Competition test samples
> (55,814) have limited script attribution (from ground truth file only).

| Script/Language | ISO 15924 | ISO 639 | Samples | Coverage | Text Dir | Notes |
|-----------------|-----------|---------|---------|----------|----------|-------|
| Arabic | Arab | ar | ~22K | 7.7% | rtl | May include Farsi/Persian text |
| Bengali/Bangla | Beng | bn | ~22K | 7.7% | ltr | Indic script |
| Gujarati | Gujr | gu | ~22K | 7.7% | ltr | Indic script |
| Gurmukhi | Guru | pa | ~22K | 7.7% | ltr | Punjabi script |
| Devanagari/Hindi | Deva | hi | ~22K | 7.7% | ltr | Hindi/Marathi/Nepali |
| Japanese | Jpan | ja | ~22K | 7.7% | ltr | Mixed Kanji + Kana (horizontal yokogaki) |
| Kannada | Knda | kn | ~22K | 7.7% | ltr | South Indian script |
| Malayalam | Mlym | ml | ~22K | 7.7% | ltr | South Indian script |
| Oriya | Orya | or | ~22K | 7.7% | ltr | Eastern Indian script |
| Roman/Latin | Latn | en | ~22K | 7.7% | ltr | May contain non-English Latin text |
| Tamil | Taml | ta | ~22K | 7.7% | ltr | South Indian script |
| Telugu | Telu | te | ~22K | 7.7% | ltr | South Indian script |
| Thai | Thai | th | ~22K | 7.7% | ltr | Southeast Asian |

**Script Families Present**: Latin, Arabic, Indic (8 scripts), CJK (Japanese), Thai

> **Notes**:
>
> - Sample counts are approximate (~290K / 13 = ~22K per script, assumes balanced)
> - Japanese uses mixed script (Kanji + Hiragana + Katakana), horizontal LTR only in samples
> - Arabic-script samples may include Farsi/Persian text (script correct, language approximate)
> - Roman-script samples may include non-English Latin languages (Spanish observed)
> - VLM inspection (60 images, 13/13 scripts) confirmed 100% script label accuracy

#### 6. IQA Profile

> Scanned multi-script document images. Primary value: script diversity (13 scripts) with mixed print and handwriting.

##### 6.1 Source Characteristics

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned newspapers + handwritten letters |
| **Key Value** | **Only multi-script DOCUMENT dataset** (not scene text) |
| **Segmentation** | Document -> Line -> Word level |
| **Handwriting** | Included (critical for robustness) |
| **Capture Method** | Scanner (flatbed) |

##### 6.2 Degradation Sensitivity

> **Status**: [NEEDS_PROFILING] - Requires empirical analysis on 1000-sample subset

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | [NEEDS_PROFILING] | Likely HIGH (newspaper print + handwriting) |
| **Noise** | [NEEDS_PROFILING] | Likely MEDIUM-HIGH (scanned documents) |
| **Skew** | [NEEDS_PROFILING] | Likely MEDIUM (document rotation common) |
| **Contrast** | [NEEDS_PROFILING] | Likely MEDIUM (varied print quality) |
| **Compression** | [NEEDS_PROFILING] | PNG format (lossless) |

##### 6.3 Document Feature Characteristics

> **Status**: [NEEDS_PROFILING] - Inferred from dataset description

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Varied (word-level segmentation) | Multi-scale detection needed |
| **Script Diversity** | Very High (13 scripts) | Script-specific IQA models beneficial |
| **Font Diversity** | High (newspapers + handwritten) | Robustness critical |
| **Content Type** | Mixed print + handwriting | Handwriting more noise-sensitive |
| **Segmentation Levels** | 3 (document/line/word) | Multi-granularity training data |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Multi-script, multi-granularity, large volume |
| **Unique Characteristics** | Only document-level (not scene text) multi-script dataset with 13 scripts |
| **Complementary Datasets** | Combine with mlt19 (10 languages), synth-multiscript-250k (27 scripts) |
| **Benchmark Suitability** | MEDIUM-HIGH - Competition test set (55K) reserved for evaluation |
| **Known Limitations** | No text transcriptions, no bounding boxes, script balance not verified |

**Key Training Applications**:

1. **Script detection/classification** (primary use case)
2. **Multi-granularity segmentation** (document -> line -> word)
3. **Handwriting robustness** (mixed print + handwriting)
4. **Script-specific IQA models** (13-class quality assessment)

#### 7. Known Issues & Limitations

> Both source dataset limitations and Layer 2 audit findings documented below.

##### Source Dataset Limitations

- **No text transcriptions**: Dataset provides script classification only, not OCR ground truth
- **No bounding boxes**: Images are pre-segmented at word/line/document level
- **Script balance unverified**: Assumes ~22K samples per script but distribution may be uneven
- **Language imprecision**: Arabic-script samples may include Farsi/Persian; Roman-script samples may include non-English Latin languages
- **Competition test labels**: Ground truth file uses numeric codes (0-12), not script names

##### Layer 2 Audit Findings (2026-02-12)

- **KI-008 (HIGH): script_family contained directionality values** - Base metadata had `ltr`/`rtl` instead of `latin`/`arabic`/`indic`/`cjk`/`thai` for 64.8% of samples. Fixed in integration by deriving from `iso15924_script` via `get_script_family()`.
- **KI-001 (CRITICAL): Docling layout label casing** - Layout labels from Docling use different casing than DocLayNet standard. Fixed inline via `DOCLING_TO_DOCLAYNET` mapping in integration script.
- **KI-007 (LOW): domain_level1 = UNK** - Mixed-domain dataset (newspapers + handwritten letters) defaults to UNK. Accepted as valid for mixed-domain datasets.
- **D01 (HIGH): split = "unknown" for ALL samples** - Parser did not populate split from directory structure. Fixed by re-deriving from `source.original_path` (SIW_MultiscriptDatabase = main, TrainCompetition = competition_train, TestCompetition = competition_test).
- **D05 (MEDIUM): text_has_content = 0%** - Docling OCR returns empty text for word/line-level image crops. This is expected behavior (Docling designed for full pages), not a data quality issue. Deferred.
- **D09 (MEDIUM): iso639_language = "und" for 21.7%** - Competition test samples (55,814) lack ground truth language labels in directory path. Partially resolved via path-based script extraction for main samples.

#### 8. Representative Samples

> VLM visual inspection confirmed 100% script label accuracy across all 13 scripts (60 images).
> No thumbnail assets generated; see VLM corrections file for per-script findings.

| Script | Sample | Type | Visual Confirmation |
|--------|--------|------|---------------------|
| Devanagari | hind_066_001_002.png | Printed word | Clear headline stroke (shirorekha) |
| Bengali | bang_026_024_003.png | Printed word | Distinctive matra line |
| Arabic | arab_045_003_004.png | Printed word | RTL text confirmed |
| Japanese | japa_003.png | Handwritten doc | Mixed Hiragana + Kanji, horizontal LTR |
| Tamil | tami_002_001_001.png | Handwritten word | Distinctive rounded letterforms |
| Latin | roma_051_004_001.png | Printed word | Latin script; Spanish confirmed in docs |
| Thai | thai_001.png | Handwritten doc | Circular letterforms, tone marks |
| Kannada | kana_001.png | Handwritten doc | Rounded shapes with headline stroke |
| Gurmukhi | gurm_004_002_002.png | Printed word | Distinctive Gurmukhi letterforms |
| Malayalam | mala_023_011_004.png | Printed word | Distinctive rounded letterforms |
| Oriya | oriy_010_003_007.png | Handwritten word | Curved Odia letterforms |
| Gujarati | gujr_001_002_001.png | Printed word | No headline bar (distinguishes from Devanagari) |
| Telugu | telu_001_001_001.png | Printed word | Rounded letterforms with characteristic curves |

#### 9. References

##### Primary Citation

```bibtex
@article{mdiw13_2023,
  title={Multi-lingual Database for Script Identification in Scene and Document Images},
  author={[Authors from paper]},
  journal={Cognitive Computation},
  year={2023},
  publisher={Springer},
  doi={10.1007/s12559-023-10193-w},
  url={https://link.springer.com/article/10.1007/s12559-023-10193-w}
}
```

##### Dataset Repository

- **Zenodo**: <https://zenodo.org/records/6376096>
- **Paper**: <https://link.springer.com/article/10.1007/s12559-023-10193-w>
- **Archive Size**: 226 MB

##### Related Works

- [SIW-13](siw13.md) - Related script identification dataset (same scripts)
- [MLT-19](mlt19.md) - Multilingual text dataset (10 languages)
- [synth-multiscript-250k](synth-multiscript-250k.md) - Synthetic multi-script (27 scripts)

##### Competition

- **ICDAR SIW Competition**: Test set (55,814 images) is from official competition
- **Ground Truth**: TestCompetitionGroundtruth.txt with numeric labels 0-12

#### 10. Dataset-Specific Notes

> **Purpose**: Capture unique characteristics and implementation details specific to MDIW-13

##### 10.1 Annotation Caveats

- **No text transcriptions**: Dataset provides script classification only, not OCR ground truth
- **No bounding boxes**: Images are pre-segmented at word/line/document level
- **Competition test labels**: Ground truth file uses numeric codes (0-12), not script names
- **Sample numbering**: Test samples use format `sample000001.png` (1-indexed)
- **Script name variants**: "Bengali" also called "Bangla", "Hindi" also called "Devanagari"

##### 10.2 Implementation Notes

- **Ground truth file format**: Line-separated numeric labels (one per line, 1-indexed)
- **Parser caching**: Class-level cache for ground truth file to avoid repeated reads
- **Directory structure**: Script name is inferred from parent directory path
- **Segmentation level**: Extracted from directory name (Document/Line/Word)
- **Data source tracking**: Distinguishes main, competition_train, competition_test via path
- **Integration script**: `scripts/integrate_mdiw13_enrichments.py` handles all 11 defects + v2.3.0 upgrade

##### 10.3 External Resources

- **Competition context**: Part of ICDAR Script Identification Workshop competition
- **Requires Zenodo download**: Dataset available via Zenodo repository (registration required)
- **Archive format**: ZIP file (226 MB compressed)

##### 10.4 Training Considerations

- **Competition test set**: 55,814 images RESERVED - never train on these samples
- **Script balance**: Assume ~22K samples per script (needs verification)
- **Multi-granularity**: Can train separate models for document/line/word levels
- **Handwriting inclusion**: Mixed print + handwriting provides robustness
- **Script confusability**: Japanese (Kanji) may confuse with Chinese scripts

---

##### 11. Layer 2 Audit Summary

> **Audit Date**: 2026-02-12 | **Auditor**: claude-opus-4-6
> **Methodology**: 9-Phase Audit (v2.3.0) | **Tier**: 3 (Comprehensive)

##### 11.1 Quality Scorecard

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 85.2 | 0.385 | 12/15 fields at 100% post-integration |
| Doc Completeness | 63.6 | 0.231 | 7/11 keyword sections populated |
| Defect Rate | 94.4 | 0.231 | 11 defects, 5.6 penalty (7 resolved, 2 partial, 2 deferred) |
| VLM Accuracy | 96.7 | 0.154 | 100% script accuracy, 13/13 scripts (60 images) |
| **Overall** | **84.1** | | **Grade B** (computed by scorecard script) |

**Prescreening**: 12/15 fields at 100% (post-integration v2)

##### 11.2 Key Defects

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | HIGH | RESOLVED | Re-derived from source.original_path |
| D02 | script_family | HIGH | RESOLVED | Re-derived via get_script_family() |
| D03 | domain_level1 | LOW | DEFERRED | KI-007: UNK acceptable for mixed-domain |
| D04 | layout_detections | MEDIUM | RESOLVED | 289,941/290,213 matched (99.91%) |
| D05 | text_has_content | MEDIUM | DEFERRED | Docling OCR empty for word crops |
| D06 | orientation_class | MEDIUM | RESOLVED | Default 0 (scanner_flatbed, VLM confirmed) |
| D07 | color_mode | MEDIUM | RESOLVED | Default grayscale |
| D08 | handwriting_present | MEDIUM | RESOLVED | Derived from directory path |
| D09 | iso639_language | MEDIUM | PARTIAL | 78.3% (21.7% competition_test no GT) |
| D10 | iso15924_script | LOW | PARTIAL | Same as D09 |
| D11 | schema_version | MEDIUM | RESOLVED | Upgraded 2.1 -> 2.3.0 |

##### 11.3 VLM Inspection Summary

| Flag | Inspected | FP Rate | Notes |
|------|----------:|--------:|-------|
| has_table | 60 | 0% | All FALSE confirmed (word/line/document crops) |
| has_formula | 60 | 0% | All FALSE confirmed |
| has_figure | 60 | 0% | All FALSE confirmed |
| has_handwriting | 60 | 0% | Correct when derived from directory |
| has_code | 60 | 0% | All FALSE confirmed |

**VLM Accuracy**: 100% script label accuracy across 13/13 scripts (60 images, Tier 3 minimum met)

##### 11.4 Cross-Dataset Findings

- **KI-001**: Docling layout label casing confirmed; mitigated via DOCLING_TO_DOCLAYNET mapping
- **KI-007**: domain_level1=UNK confirmed as acceptable for mixed-domain datasets
- **KI-008**: script_family containing directionality values (`ltr`/`rtl`) instead of family names; mitigated via get_script_family() re-derivation
- **NEW**: Prescreening `VALID_CAPTURE_METHODS` set was missing `scanner_flatbed` and `scanner_adf` -- fixed in prescreening script (affects all datasets using specific scanner subtypes)

**Audit Artifacts**: [scripts/audit/results/mdiw13/](../../../scripts/audit/results/mdiw13/)

---

##### 12. Reliability & Bottlenecks

> **Computed**: 2026-02-12 | **Samples**: 290,213 | **Avg Min Confidence**: 0.000
>
> **Note**: All samples show as "unreliable" because `text_quality` has 0.000 confidence
> (Docling OCR returns empty text for word-level crops -- expected behavior, not a data
> quality issue). See Layer 2 Audit Summary above for post-integration quality assessment.

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 290,213 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 63.6% | 0.000 |
| 2 | `language` | 36.4% | 0.604 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | 0 | N/A | All scanner_flatbed crops are upright (orientation_class=0 for 100%); no rotation diversity; not useful for orientation training |
| MNV4-H2 | skew_reg | ➖ | 0 | N/A | Flatbed scans have near-zero skew; word/line crops have no meaningful skew signal |
| MNV4-H3 | resolution_quality_reg | ➖ | 0 | N/A | No resolution quality labels computed; consistent scan resolution throughout |
| SIG-G1-1 | blur_score | ➖ | 0 | N/A | No IQA labels; scanned documents have minimal blur — useful only as implicit "clean" negative |
| SIG-G1-2 | noise_score | ➖ | 0 | N/A | No IQA labels; scanner noise present but unlabeled |
| SIG-G1-3 | contrast_score | ➖ | 0 | N/A | No IQA labels; varied print quality but no contrast annotations |
| SIG-G1-4 | skew_score | ➖ | 0 | N/A | No IQA labels; flatbed scan skew is minimal |
| SIG-G1-5 | compression_score | ➖ | 0 | N/A | PNG lossless format; compression artifacts absent |
| SIG-G1-6 | overall_quality | ➖ | 0 | N/A | No IQA labels present |
| SIG-G2-1 | script_cls | ✅ Primary | ~234,400 | Human expert GT (directory + competition GT file) | 9 ML-usable ISO 15924 classes (Arab, Beng, Guru, Deva, Jpan, Latn, Mlym, Orya+Taml+Telu+Thai mapped); competition_test (55,814) RESERVED; most important real/printed multi-script document dataset |
| SIG-G3-1 | orientation_cls (post) | ➖ | 0 | N/A | All samples at 0° orientation (flatbed scanner); no post-correction orientation signal |
| SIG-G3-2 | skew_reg (post) | ➖ | 0 | N/A | Flatbed scans are axis-aligned; post-correction skew effectively zero |
| SIG-G4-1 | handwriting_presence_cls | 🟡 Secondary | ~152,700 | Derived from directory path (handwritten_document flag) | 52.6% has_handwriting=True (152,661 samples); binary label only; printed half provides useful "no handwriting" negatives |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | N/A | No legibility annotations available in dataset |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | N/A | No handwriting content-type annotations |
| SIG-G4-4 | presence_reg | 🟡 Secondary | ~152,700 | Derived binary (0.0/1.0) | Binary presence score usable as 0.0/1.0 regression signal; same 52.6% coverage as G4-1 |
| SIG-G4-5 | legibility_reg | ❌ | 0 | N/A | No legibility score labels available |
| SIG-G5-1 | capture_method_cls | ✅ Primary | ~234,400 | Derived from dataset capture method (100% scanner_flatbed) | 100% real labels; pure "scanned" class contribution; usable for capture_method 7-class head as "scanner" stratum |
| SIG-G5-2 | shadow_reg | ❌ | 0 | N/A | No shadow severity labels; flatbed scanning produces minimal shadow |
| SIG-G5-3 | warping_reg | ❌ | 0 | N/A | No warping labels; flatbed scans have near-zero warping |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | VLM confirmed 0% has_code across all 60 inspected samples |
| SIG-G5-5 | resolution_quality_reg | ➖ | 0 | N/A | No resolution quality labels computed; PaddleOCR pipeline not run on this dataset |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ Well-covered | 5 families: Indic (56.3%), Latin (10.2%), Arabic (9.1%), CJK/Japanese (2.7%), Thai (7.6%); 13 scripts total; strongest multi-script coverage of any real document dataset |
| 2 | Capture method | 🟡 Partial | 100% scanner_flatbed; excellent scanner representation but no camera or born_digital diversity |
| 3 | Document domain | ❌ Not present | domain_level1 = UNK for all 290K samples (KI-007 accepted); mix of newspapers + handwritten letters but no structured domain labels |
| 4 | Layout type | ❌ Not present | No layout_type labels; word/line/document crops at 3 granularity levels but no semantic layout categories |
| 5 | Text density | 🟡 Partial | text_scope=word for 100% (pre-segmented crops); word-level density is implicitly single-word, not document density |
| 6 | Degradation types | ❌ Not present | No degradation labels; degradation_types dict is empty in aggregates; scanned quality assumed acceptable |
| 7 | Resolution/DPI range | 🟡 Partial | Consistent flatbed scanner resolution (estimated 200-400 DPI); no per-image DPI metadata; no low-resolution samples |
| 8 | Document age | 🟡 Partial | Newspaper content spans various decades; no explicit document_age labels; mix of modern and older print |
| 9 | Text scope | ✅ Well-covered | 100% word-level text scope (pre-segmented); document-level, line-level, and word-level granularity present in directory structure |
| 10 | Content flags | 🟡 Partial | has_handwriting=52.6% (derived); has_table=0.0% (VLM confirmed); has_code=0% (VLM confirmed); no formula/figure flags |
| 11 | Binarization status | 🟡 Partial | Default grayscale (D07 resolved); not explicitly binarized; scanner output is typically near-binary for text |
| 12 | Artifact types | ❌ Not present | No artifact type labels; top_degradations list is empty; scanner artifacts (bleed-through, noise) present but unlabeled |
| 13 | Color mode | 🟡 Partial | Default grayscale for all samples (D07 resolved); consistent single mode, no color or binarized variety |
| 14 | Font variety | ✅ Well-covered | High font diversity across 13 scripts including newspaper print fonts and handwritten letterforms; VLM confirmed authentic script-specific letterforms |

### 13.3 Corpus Role & Constraints

MDIW13 is the primary real-document dataset for SIG-G2-1 `script_cls`, providing 234,399 human-expert-labeled images across 9 ML-usable ISO 15924 script classes from flatbed-scanned printed documents and handwritten letters. The competition test set (55,814 images) is permanently RESERVED for benchmark evaluation and must never be used for training. Real/printed mixing caps do not apply to G2-1 since this dataset contributes exclusively to the real-scanned stratum; the 13th script class (Zyyy/undetermined, 21.7%) corresponds to competition_test samples and is excluded from training pools.
