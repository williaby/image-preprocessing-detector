#### SIW-13 (Script Identification in the Wild)

> **Quick Stats**: 16,291 images | 13 scripts | Scene text | Tibetan + Hebrew coverage
>
> **License**: Research | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Script Identification in the Wild - 13 Classes |
| **Version** | 1.0 |
| **Release Date** | 2015 |
| **Paper** | [Automatic Script Identification in the Wild](https://arxiv.org/abs/1505.02982) (ICDAR 2015) |
| **Authors** | Baoguang Shi, Cong Yao, Chengquan Zhang, Xiang Bai et al. |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/siw13/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 16,291 |
| **Training Set** | 12,992 images |
| **Testing Set** | 3,299 images |
| **Total Size** | 104 MB |
| **File Format** | JPG |

##### Multi-Level Hierarchy

| Level | Count | Notes |
|-------|-------|-------|
| **Documents** | 10,908 | Unique document IDs extracted from filenames |
| **Lines** | 16,291 | Line-level cropped images |
| **Avg Lines/Doc** | 1.49 | Varies by script (1.01-2.10) |

**Naming Pattern**: `{script}_{document_id}_{line_id}.jpg`

- Document IDs are unique per script
- Line IDs restart for each document
- No word-level segmentation available

**Per-Split Breakdown**:

- Training: 8,055 documents → 12,992 lines (1.61 lines/doc avg)
- Testing: 2,853 documents → 3,299 lines (1.16 lines/doc avg)

##### Script Classes (13)

| Script | Training | Testing | Total | Notes |
|--------|----------|---------|-------|-------|
| **Arabic** | 802 | 200 | 1,002 | RTL cursive |
| **Cambodian** | 866 | 217 | 1,083 | Khmer script |
| **Chinese** | 998 | 300 | 1,298 | Han logograms |
| **English** | 976 | 245 | 1,221 | Latin script |
| **Greek** | 815 | 203 | 1,018 | Greek alphabet |
| **Hebrew** | 993 | 249 | 1,242 | **Critical for Phase 10B** |
| **Japanese** | 972 | 243 | 1,215 | Mixed Kanji/Kana |
| **Kannada** | 823 | 206 | 1,029 | South Indian |
| **Korean** | 1,249 | 312 | 1,561 | Hangul blocks |
| **Mongolian** | 953 | 239 | 1,192 | Vertical script |
| **Russian** | 825 | 206 | 1,031 | Cyrillic |
| **Thai** | 1,778 | 444 | 2,222 | Continuous script |
| **Tibetan** | 942 | 235 | 1,177 | **Critical for Phase 10B** |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Capture Method** | Camera (Google Street View) |
| **Source Type** | Scene text (outdoor signage, storefronts) |
| **Quality** | Variable (real-world lighting, perspective) |
| **Key Value** | **Only source for Tibetan & Hebrew scene text** |
| **Domain Gap** | Street signs vs documents - requires augmentation |

##### Project Usage

- **Path**: `01_base_data/language/siw13/` ✅ Extracted
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Tibetan, Hebrew, Cyrillic, Thai training data
- **Files**: 16,291 files, 104 MB
- **Note**: Critical gap-filler for low-resource scripts
- **Parser**: ✅ `parse_siw13_labels` (extracts script class, split from folder structure)

---
