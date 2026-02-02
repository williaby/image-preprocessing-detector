#### CVSI-2015 (Competition on Video Script Identification)

> **Quick Stats**: 10,715 images | 10 scripts | Video frames | Indic scripts
>
> **License**: Research | **Commercial Use**: Research only

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | ICDAR 2015 Competition on Video Script Identification |
| **Version** | 1.0 |
| **Release Date** | 2015 |
| **Competition** | ICDAR 2015 |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/cvsi/` |
| **Documentation Status** | Partial |

##### 2. Source Data Inventory

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Video frame captures with scene text |
| **Annotations** | Implicit (folder structure) | Script label from parent directory name |
| **Metadata** | None | No explicit metadata files |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `cvsi/Training/{Script}/` | Implicit (folder name) | 6,412 | ✅ |
| **Validation** | `cvsi/Validation/{Script}/` | Implicit (folder name) | 1,069 | ✅ |
| **Test** | `cvsi/Testing/{Script}/` | Implicit (folder name) | 3,234 | ✅ |

**Split Organization Pattern**: `by_folder` (script label determined by parent directory)

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Script Class** | Folder structure | Image-level | Script determined by parent directory (10 scripts) |

> **Note**: No bounding boxes, text transcriptions, or quality scores provided in source dataset.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Kaggle README | Competition context, script list |
| **Image-level** | Filename | Potentially encoded in filename |

###### 2.5 Annotation Schema Details

> **Format**: Implicit annotation via directory structure

```text
cvsi/
├── Training/
│   ├── Arabic/*.jpg
│   ├── Bengali/*.jpg
│   ├── English/*.jpg
│   └── ... (7 more scripts)
├── Testing/
│   └── {Script}/*.jpg
└── Validation/
    └── {Script}/*.jpg

# Script label extracted from parent directory name
# No separate annotation files
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `parent_dir` | str | Yes | Script class name (Arabic, Bengali, etc.) |
| `split_dir` | str | Yes | Training, Testing, Validation |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Script class | `language.script_iso15924` | High | Folder structure → ISO 15924 code |
| ✅ Split | `provenance.split` | Medium | Training/Testing/Validation |
| ✅ Language code | `language.language_code` | High | ISO 639 code derived from script |
| ❌ Bounding boxes | - | N/A | Not provided in source |
| ❌ Text GT | - | N/A | Not provided in source |
| ❌ Quality scores | - | N/A | Not provided in source |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 3. Project Usage

###### 3a. Storage Locations

- **Path**: `01_base_data/language/cvsi/` ✅ Extracted
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Indic script differentiation (Devanagari confusers)
- **Files**: 10,715 files, 43 MB
- **Note**: Excellent for training Devanagari vs Bengali vs Gurmukhi

###### 3b. Parser & Metadata Integration

- **Parser**: ✅ `parse_cvsi_labels` (extracts script class, split, ISO language/script codes)
- **Layer 2 Integration**: Populates `language.script_iso15924`, `language.language_code`, `provenance.split`

###### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/cvsi/` | ✅ Available | 10,715 JPG files |
| **Images (GCS)** | `gs://image_detection_b/image-preprocessing-detector/datasets/cvsi/` | ✅ Available | Cloud backup |
| **Text/OCR GT** | - | ❌ None | Scene text images, no transcription GT |
| **Text/OCR Extracted** | `annotations/cvsi/ocr/` | ❌ Not extracted | OCR not yet run |
| **Layout GT** | - | ❌ None | No bounding box annotations in source |
| **Layout Extracted** | `annotations/cvsi/layout/` | ❌ Not extracted | Layout detection not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/cvsi_layer2.json` | ⚠️ Unknown | Check if enrichment completed |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete

##### 4. Dataset Statistics

###### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 6,412 | [NEEDS_VERIFICATION] | ? | ⚠️ Needs check |
| **Validation** | 1,069 | [NEEDS_VERIFICATION] | ? | ⚠️ Needs check |
| **Test** | 3,234 | [NEEDS_VERIFICATION] | ? | ⚠️ Needs check |
| **Total** | 10,715 | [NEEDS_VERIFICATION] | ? | ⚠️ Needs check |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: Layer 2 metadata counts need verification. If Layer 2 enrichment not yet run,
> run: `uv run python scripts/annotate_base_metadata.py --dataset cvsi`

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 10,715 |
| **Training Split** | 6,412 (59.8%) |
| **Validation Split** | 1,069 (10.0%) |
| **Testing Split** | 3,234 (30.2%) |
| **Image Dimensions** | [NEEDS_PROFILING] (variable, video frames) |
| **Resolution (DPI)** | N/A (video frames, no DPI metadata) |
| **File Format(s)** | JPG |
| **Color Space** | RGB |
| **Total Size on Disk** | 43 MB [Official] |
| **Annotation Format** | Implicit (folder structure) |

##### 5. Content Composition

###### 5.1 Script Classes (10)

| Script | Description |
|--------|-------------|
| **Arabic** | Arabic script |
| **Bengali** | Bengali/Bangla script |
| **English** | Latin script |
| **Gujrathi** | Gujarati script |
| **Hindi** | Devanagari script |
| **Kannada** | Kannada script |
| **Oriya** | Odia script |
| **Punjabi** | Gurmukhi script |
| **Tamil** | Tamil script |
| **Telegu** | Telugu script |

###### 5.2 Class/Category Definitions

> **Purpose**: Define the taxonomy of classes/categories used in the dataset annotations.
> **Applicability**: Script identification dataset with 10 script classes.

| Class/Category | ID | ISO 15924 | ISO 639 | Description | Script Family |
|----------------|-----|-----------|---------|-------------|---------------|
| Arabic | 1 | Arab | ar | Arabic script | Abjad |
| Bengali | 2 | Beng | bn | Bengali/Bangla script | Brahmic (Indic) |
| English | 3 | Latn | en | Latin script | Alphabetic |
| Gujrathi | 4 | Gujr | gu | Gujarati script | Brahmic (Indic) |
| Hindi | 5 | Deva | hi | Devanagari script | Brahmic (Indic) |
| Kannada | 6 | Knda | kn | Kannada script | Brahmic (Indic) |
| Oriya | 7 | Orya | or | Odia script | Brahmic (Indic) |
| Punjabi | 8 | Guru | pa | Gurmukhi script | Brahmic (Indic) |
| Tamil | 9 | Taml | ta | Tamil script | Brahmic (Indic) |
| Telegu | 10 | Telu | te | Telugu script | Brahmic (Indic) |

> **Notes**:
>
> - 8 of 10 scripts are Indic scripts from Brahmic family (excellent for Devanagari confusable training)
> - Parser maps folder names to ISO 15924 script codes and ISO 639 language codes
> - Competition focused on video frame captures from Indian media

###### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.
> **Applicability**: Script detection dataset with 10 scripts across 3 script families.

| Script/Language | ISO Script | ISO Language | Samples | Coverage | Script Family | Notes |
|-----------------|------------|--------------|---------|----------|---------------|-------|
| Arabic | Arab | ar | [NEEDS_PROFILING] | ~10% | Abjad | Right-to-left |
| Bengali | Beng | bn | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | Devanagari confusable |
| English | Latn | en | [NEEDS_PROFILING] | ~10% | Alphabetic | Latin script |
| Gujarati | Gujr | gu | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | Devanagari-related |
| Hindi | Deva | hi | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | Primary Devanagari script |
| Kannada | Knda | kn | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | South Indian script |
| Odia | Orya | or | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | Eastern India script |
| Punjabi | Guru | pa | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | Gurmukhi script |
| Tamil | Taml | ta | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | South Indian script |
| Telugu | Telu | te | [NEEDS_PROFILING] | ~10% | Brahmic (Indic) | South Indian script |

**Script Families Present**: Abjad (1), Alphabetic (1), Brahmic/Indic (8)

**Key Characteristics**:
- **Indic Script Heavy**: 8 of 10 scripts are Indic (Brahmic family)
- **Devanagari Confusables**: Bengali, Gujarati, Gurmukhi share similar shapes with Devanagari
- **Video Frame Quality**: Variable quality due to motion blur, compression artifacts

> **Notes**:
>
> - Use ISO 15924 codes for scripts, ISO 639-1/3 for languages
> - Exact sample distribution per script requires Layer 2 metadata analysis
> - Recommended for training Devanagari-family script differentiation

##### 6. IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Video frame captures |
| **Quality** | Variable (motion blur, low resolution) |
| **Key Value** | **Strong Indic script coverage** (8 Indic scripts) |
| **Robustness** | Trains model for degraded quality inputs |

##### 10. Dataset-Specific Notes

> **Purpose**: Capture unique characteristics, caveats, and implementation details specific to this dataset that don't fit standard template sections.

###### 10.1 Competition Context

- **ICDAR 2015 Competition**: Part of ICDAR 2015 Robust Reading Competition
- **Task**: Video Script Identification (VSI) - identify script in video frames with scene text
- **Challenge**: Variable quality due to motion blur, low resolution, compression artifacts
- **Domain**: Indian video media (TV, movies, advertisements)

###### 10.2 Video Frame Specifics

- **Source**: Extracted from video clips (not static documents)
- **Quality Issues**:
  - Motion blur from camera/subject movement
  - Compression artifacts from video encoding
  - Variable lighting conditions
  - Perspective distortion
  - Low resolution compared to document scans
- **Training Value**: Builds robustness to real-world degradation

###### 10.3 Indic Script Focus

- **Key Differentiator**: Strong coverage of Indic scripts (8 of 10 total)
- **Devanagari Confusables**: Excellent for training models to distinguish:
  - Devanagari (Hindi) vs Bengali
  - Devanagari vs Gujarati
  - Devanagari vs Gurmukhi (Punjabi)
- **Script Family**: All Indic scripts belong to Brahmic family, share similar shapes

###### 10.4 Implementation Notes

- **Parser**: Extracts script class from folder structure (no separate annotation files)
- **ISO Code Mapping**: Hardcoded in parser (`parse_cvsi_labels`)
- **Split Detection**: Training/Testing/Validation determined from parent directory
- **No Bounding Boxes**: Dataset provides image-level labels only (no word/line boxes)
- **No Text Transcriptions**: Scene text images, but no ground truth text provided

---
