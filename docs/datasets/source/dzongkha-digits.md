#### Dzongkha Digits (Tibetan Script)

> **Quick Stats**: 1,000 images | Handwritten digits | Tibetan-derived script
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes (with attribution required)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Dzongkha Handwritten Digit Dataset |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | Tawmo, Prottay Kumar Adhikary et al. |
| **HuggingFace** | [proadhikary/dzongkha-digits](https://huggingface.co/datasets/proadhikary/dzongkha-digits) |
| **Zenodo** | [10.5281/zenodo.6271560](https://doi.org/10.5281/zenodo.6271560) |
| **License** | CC-BY-4.0 (Creative Commons Attribution 4.0 International) |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | 1,000 handwritten Dzongkha digit images |
| **Annotations** | Implicit (HuggingFace dataset field) | Class labels 0-9 in `label` field |
| **Metadata** | JSON (Croissant ML Commons 1.1) | Dataset-level metadata |
| **Supplementary** | - | None provided |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | HuggingFace `train` split | Embedded in dataset (label field) | 1,000 | ✅ |
| **Validation** | - | - | 0 | ℹ️ Not provided |
| **Test** | - | - | 0 | ℹ️ Not provided |
| **Total** | HuggingFace dataset | - | 1,000 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (HuggingFace format)

> **Notes**:
>
> - Dataset has NO official train/val/test split - users must create their own
> - All 1,000 images are in single "train" split
> - HuggingFace provides Parquet files (79.7 MB) auto-converted from JPG (184 MB)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Class Labels** | Integer (0-9) | Image-level | Digit classification (0-9) |
| **Text Transcriptions** | Implicit (requires mapping) | Character-level | Tibetan digit Unicode (༠-༩) |

> **Note**: Text transcriptions not explicitly provided - must map class label to Tibetan Unicode character.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace card + Zenodo | License (CC-BY-4.0), citation, DOI, collection method |
| **Image-level** | HuggingFace dataset fields | Class label (0-9), image dimensions |
| **Annotation-level** | - | None |
| **Document-level** | - | Not applicable (single digits) |

##### 2.5 Annotation Schema Details

> **Format**: HuggingFace Datasets format with Croissant ML Commons 1.1 metadata

```python
# HuggingFace Dataset Schema
{
  "features": {
    "image": Image(),         # PIL Image object (JPG)
    "label": ClassLabel(      # Integer class label
      names=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    )
  }
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image` | PIL Image | Yes | JPG format, variable resolution (1.65k-7.41k px) |
| `label` | int | Yes | Range 0-9, maps to Tibetan digit Unicode |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Class labels | `class_label` (0-9) | High | Direct extraction from HuggingFace |
| ✅ Text GT (derived) | `ground_truth_text` (༠-༩) | High | Requires Unicode mapping table |
| ✅ Script metadata | `script_family` (Tibetan) | High | Path-based detection |
| ✅ Language metadata | `iso639_language` (dz) | High | Path-based detection |
| ⚠️ Writer ID | - | Low | Not in public release (100 writers mentioned) |
| ❌ Bounding boxes | - | N/A | Digit is entire image |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,000 |
| **Classes** | 10 (digits 0-9: ༠–༩) |
| **Participants** | 100 writers |
| **File Format** | JPG |
| **Collection Method** | Google Jamboard |

##### 5. Content Composition

##### 5.1 Class/Category Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Class 0 (༠) | ~100 | 10% |
| Class 1 (༡) | ~100 | 10% |
| Class 2 (༢) | ~100 | 10% |
| Class 3 (༣) | ~100 | 10% |
| Class 4 (༤) | ~100 | 10% |
| Class 5 (༥) | ~100 | 10% |
| Class 6 (༦) | ~100 | 10% |
| Class 7 (༧) | ~100 | 10% |
| Class 8 (༨) | ~100 | 10% |
| Class 9 (༩) | ~100 | 10% |

> **Note**: Exact class distribution not documented. Assumed balanced (~100 images per digit) based on 1,000 total images and 100 writers.

##### 5.2 Class/Category Definitions

> **Purpose**: Define the taxonomy of classes/categories used in the dataset annotations.

| Class/Category | ID | Tibetan Character | Unicode | Description |
|----------------|-----|-------------------|---------|-------------|
| Zero | 0 | ༠ | U+0F20 | Tibetan Digit Zero |
| One | 1 | ༡ | U+0F21 | Tibetan Digit One |
| Two | 2 | ༢ | U+0F22 | Tibetan Digit Two |
| Three | 3 | ༣ | U+0F23 | Tibetan Digit Three |
| Four | 4 | ༤ | U+0F24 | Tibetan Digit Four |
| Five | 5 | ༥ | U+0F25 | Tibetan Digit Five |
| Six | 6 | ༦ | U+0F26 | Tibetan Digit Six |
| Seven | 7 | ༧ | U+0F27 | Tibetan Digit Seven |
| Eight | 8 | ༨ | U+0F28 | Tibetan Digit Eight |
| Nine | 9 | ༩ | U+0F29 | Tibetan Digit Nine |

> **Notes**:
>
> - Dzongkha uses Tibetan script numerals (not Arabic numerals)
> - Unicode range: U+0F20 to U+0F29 (Tibetan Digit Zero through Nine)
> - Classes are mutually exclusive (single digit per image)
> - No hierarchical taxonomy (flat 10-class classification)

##### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Tibetan / Dzongkha | Tibt / dz | 1,000 | 100% | National language of Bhutan |

**Script Families Present**: Tibetan (Tibt)

**ISO Codes**:

- **Script**: ISO 15924 code `Tibt` (Tibetan)
- **Language**: ISO 639-1 code `dz` (Dzongkha)

> **Notes**:
>
> - Dzongkha is the national language of Bhutan
> - Dzongkha uses Tibetan script with minor variations
> - Monolingual dataset (single script, single language)
> - Digits are universal across Tibetan script variants

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Handwritten digits |
| **Script** | Tibetan (Dzongkha is Tibetan-derived) |
| **Language** | Dzongkha (Bhutan national language) |
| **Key Value** | Tibetan script class for 10-class detection |

##### References

```bibtex
@dataset{tawmo_2022_6271560,
  author = {Tawmo and Prottay Kumar Adhikary and Pankaj Dadure and Partha Pakray},
  title = {Dzongkha Handwritten Digit Dataset},
  year = {2022},
  doi = {10.5281/zenodo.6271560}
}
```

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/dzongkha_digits/`
- **Phase(s)**: Phase 10A (Script Detection)
- **Purpose**: Tibetan script class training
- **Parser**: [`parse_multilingual_scripts_labels`](../scripts/annotate_base_metadata.py#L1548) | ✅ Complete

---
