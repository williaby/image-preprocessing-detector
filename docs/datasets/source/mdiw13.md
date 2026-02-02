#### MDIW-13 (Foundational Script Identification Dataset)

> **Quick Stats**: 290,213 images (1,135 docs, 13,979 lines, 86,655 words) | 13 scripts | Printed + Handwritten
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multi-lingual Database for Script Identification |
| **Version** | February 2025 |
| **Source** | [Zenodo](https://zenodo.org/records/6376096) |
| **Paper** | [Cognitive Computation 2023](https://link.springer.com/article/10.1007/s12559-023-10193-w) |
| **License** | Academic/Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mdiw13/` |

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
| **Main** | `SIW_MultiscriptDatabase/{script}/` | Directory structure | 101,814 | ✅ |
| **Competition Train** | `TrainCompetition_WITHGroundTruth/{script}/` | Directory structure | 232,170* | ✅ |
| **Competition Test** | `TestCompetition_WITHOUTGroundTruth/` | TestCompetitionGroundtruth.txt | 58,043 | ✅ RESERVED |

*Note: Train count may include main database (overlapping or distinct - needs verification)

**Split Organization Pattern**: `by_folder` + `single_dir_with_manifest` (test set)

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

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Documents** | 1,135 |
| **Total Lines** | 13,979 |
| **Total Words** | 86,655 |
| **File Format** | PNG |
| **Archive Size** | 226 MB |

#### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Main** | 101,814 | ❓ Check | ❓ | ⚠️ Needs verification |
| **Competition Train** | 232,170* | ❓ Check | ❓ | ⚠️ Needs verification |
| **Competition Test** | 58,043 | ❓ Check | ❓ | 🚫 RESERVED - Do not train |
| **Total** | 290,213 | ❓ Check | ❓ | ⚠️ Verify all splits |

*Note: Competition train count may overlap with main database - needs verification

**Split Status Legend**:

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Needs verification - Split coverage not yet confirmed
- ❌ Missing - Split not included in Layer 2 metadata
- 🚫 RESERVED - Competition test set, never train on this

> **Note**: Competition test set (58,043 images) is RESERVED for benchmark evaluation only.
> Use `split` field in sample source metadata to track which split each sample belongs to.

##### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.

| Script/Language | ISO 15924 | ISO 639 | Samples | Coverage | Notes |
|-----------------|-----------|---------|---------|----------|-------|
| Arabic | Arab | ar | ~22,325 | 7.7% | RTL script |
| Bengali/Bangla | Beng | bn | ~22,325 | 7.7% | Indic script |
| Gujarati | Gujr | gu | ~22,325 | 7.7% | Indic script |
| Gurmukhi | Guru | pa | ~22,325 | 7.7% | Punjabi script |
| Devanagari/Hindi | Deva | hi | ~22,325 | 7.7% | Hindi/Marathi/Nepali |
| Japanese | Jpan | ja | ~22,325 | 7.7% | Mixed Kanji + Kana |
| Kannada | Knda | kn | ~22,325 | 7.7% | South Indian script |
| Malayalam | Mlym | ml | ~22,325 | 7.7% | South Indian script |
| Oriya | Orya | or | ~22,325 | 7.7% | Eastern Indian script |
| Roman/Latin | Latn | en | ~22,325 | 7.7% | English default |
| Tamil | Taml | ta | ~22,325 | 7.7% | South Indian script |
| Telugu | Telu | te | ~22,325 | 7.7% | South Indian script |
| Thai | Thai | th | ~22,325 | 7.7% | Southeast Asian |

**Script Families Present**: Latin, Arabic, Indic (8 scripts), CJK (Japanese), Thai

**Estimated samples per script**: 290,213 total / 13 scripts ≈ 22,325 per script (assumes balanced)

> **Notes**:
>
> - Sample counts are estimates assuming balanced distribution (needs verification)
> - Japanese uses mixed script (Kanji + Hiragana + Katakana)
> - Devanagari used for Hindi primarily, also Marathi and Nepali
> - All 13 scripts have ISO 15924 and ISO 639 codes mapped in parser

##### 6.1 IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned newspapers + handwritten letters |
| **Key Value** | **Only multi-script DOCUMENT dataset** (not scene text) |
| **Segmentation** | Document → Line → Word level |
| **Handwriting** | Included (critical for robustness) |

##### 6.2 Degradation Sensitivity

> **Status**: [NEEDS_PROFILING] - Requires empirical analysis on 1000-sample subset

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | [NEEDS_PROFILING] | Likely HIGH (newspaper print + handwriting) |
| **Noise** | [NEEDS_PROFILING] | Likely MEDIUM-HIGH (scanned documents) |
| **Skew** | [NEEDS_PROFILING] | Likely MEDIUM (document rotation common) |
| **Contrast** | [NEEDS_PROFILING] | Likely MEDIUM (varied print quality) |
| **Compression** | [NEEDS_PROFILING] | PNG format (lossless) |

**Profiling Command**:

```bash
python scripts/profile_dataset.py \
  --input /mnt/e/image_detection/01_base_data/language/mdiw13/ \
  --sample-size 1000 \
  --output docs/datasets/mdiw13_profile.json
```

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
| **Complementary Datasets** | Combine with mlt19 (10 languages), synth-multiscript-250k (27 scripts - see TRAINING_DATASET_CATALOG.md) |
| **Benchmark Suitability** | MEDIUM-HIGH - Competition test set (58K) reserved for evaluation |
| **Known Limitations** | No text transcriptions, no bounding boxes, script balance not verified |

**Key Training Applications**:

1. **Script detection/classification** (primary use case)
2. **Multi-granularity segmentation** (document → line → word)
3. **Handwriting robustness** (mixed print + handwriting)
4. **Script-specific IQA models** (13-class quality assessment)

##### 3a. Project Usage

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
| Directory: Document/Line/Word | `text_scope.scope` | ⚠️ Could infer | Segmentation level → scope |
| Ground truth numeric | `raw_labels.numeric_label` | ✅ Mapped | Test set only |

**Gap**: Tier 0 config fields (capture_method, domain) not populated by parser

> **Parser Reference**: See [LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) for field mappings

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/mdiw13/` | ✅ Available | Primary image files (290K) |
| **Images (GCS)** | `gs://image_detection_b/.../mdiw13/` | ✅ Available | Backup storage |
| **Text/OCR GT** | - | ❌ None | Dataset does not provide text transcriptions |
| **Text/OCR Extracted** | `annotations/mdiw13/ocr/` | ❌ Not extracted | Could extract via Tesseract/DocTR |
| **Layout GT** | - | ❌ None | No layout annotations provided |
| **Layout Extracted** | `annotations/mdiw13/layout/` | ❌ Not extracted | Could extract via DocLayout-YOLO |
| **Layer 2 Metadata** | `metadata_registry/json/mdiw13_layer2.json` | ❓ Check | Enrichment metadata |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- ❓ Check - Existence needs verification

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
- [MLT-19](mlt19.md) - Multi-lingual text dataset (10 languages)
- [synth-multiscript-250k](synth-multiscript-250k.md) - Synthetic multi-script (27 scripts)

##### Competition

- **ICDAR SIW Competition**: Test set (58,043 images) is from official competition
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

##### 10.3 External Resources

- **Competition context**: Part of ICDAR Script Identification Workshop competition
- **Requires Zenodo download**: Dataset available via Zenodo repository (registration required)
- **Archive format**: ZIP file (226 MB compressed)

##### 10.4 Training Considerations

- **Competition test set**: 58,043 images RESERVED - never train on these samples
- **Script balance**: Assume ~22K samples per script (needs verification)
- **Multi-granularity**: Can train separate models for document/line/word levels
- **Handwriting inclusion**: Mixed print + handwriting provides robustness
- **Script confusability**: Japanese (Kanji) may confuse with Chinese scripts

---
