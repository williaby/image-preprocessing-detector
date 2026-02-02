#### CVSI-2015 (Competition on Video Script Identification)

> **Quick Stats**: 10,715 images | 10 scripts | Video frames | Indic scripts
>
> **License**: Research | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | ICDAR 2015 Competition on Video Script Identification |
| **Version** | 1.0 |
| **Release Date** | 2015 |
| **Competition** | ICDAR 2015 |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/cvsi/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 10,715 |
| **Training Set** | 6,412 images |
| **Validation Set** | 1,069 images |
| **Testing Set** | 3,234 images |
| **Total Size** | 43 MB |
| **File Format** | JPG |

##### Script Classes (10)

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

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Video frame captures |
| **Quality** | Variable (motion blur, low resolution) |
| **Key Value** | **Strong Indic script coverage** (8 Indic scripts) |
| **Robustness** | Trains model for degraded quality inputs |

##### Project Usage

- **Path**: `01_base_data/language/cvsi/` ✅ Extracted
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Indic script differentiation (Devanagari confusers)
- **Files**: 10,715 files, 43 MB
- **Note**: Excellent for training Devanagari vs Bengali vs Gurmukhi
- **Parser**: ✅ `parse_cvsi_labels` (extracts script class, split, ISO language/script codes)

---
