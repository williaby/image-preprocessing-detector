#### Yarmouk OCR Dataset

> **Quick Stats**: 6,039 PDFs | Arabic documents | University research dataset
>
> **License**: Research (University of Yarmouk) | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Yarmouk University Arabic OCR Dataset |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Institution** | Yarmouk University, Jordan |
| **Kaggle** | [eyadwin/yarmouk-ocr-dataset](https://www.kaggle.com/datasets/eyadwin/yarmouk-ocr-dataset) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/yarmouk_ocr/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Scanned PDFs** | 6,039 |
| **HTML Annotations** | 6,061 |
| **Text Transcriptions** | 4,633 |
| **Total Size** | 2.2 GB |
| **File Format** | PDF (scanned documents) |

##### Dataset Structure

| Split | Description |
|-------|-------------|
| **Scanned/** | Original scanned PDF documents |
| **HTML/** | Annotated HTML versions |
| **OCR/** | OCR output text files |
| **testing sample/** | Test set samples |
| **training sample/** | Training set samples |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned academic/official documents |
| **Script** | Arabic |
| **Quality** | Variable (real-world scanning artifacts) |
| **Key Value** | **Academic Arabic documents** with OCR annotations |
| **Note** | PDFs require conversion to images for training |

##### Project Usage

- **Path**: `01_base_data/language/yarmouk_ocr/` ✅ Extracted (16,734 files, 2.8 GB)
- **Images Path**: `01_base_data/language/yarmouk_ocr_images/` ✅ 6,039 PNG images (pre-extracted from PDFs)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training (supplementary)
- **Parser**: ✅ `parse_yarmouk_labels` (extracts split from folder structure)
- **Conversion**: ⚠️ Required PDF→PNG conversion at 300 DPI (6,039 scanned PDFs → PNG images)

---
