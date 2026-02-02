#### Arabic Documents OCR Dataset

> **Quick Stats**: 10,045 images | 12 categories | Arabic documents | Script detection
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes (with attribution)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Arabic Documents OCR Dataset |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Kaggle** | [mehdihasan/arabic-documents-ocr-dataset](https://www.kaggle.com/datasets/mehdihasan/arabic-documents-ocr-dataset) |
| **License** | CC-BY-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/arabic_docs_ocr/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 10,045 |
| **Annotations** | 10,046 JSON files |
| **Categories** | 12 document types |
| **Total Size** | 8.9 GB |
| **File Format** | JPG/PNG |

##### Document Categories (12)

| Category | Images | Description |
|----------|--------|-------------|
| **Administrative form** | ~841 | Government/official forms |
| **Book** | ~840 | Book pages |
| **Business card** | ~820 | Contact cards |
| **Comics** | ~840 | Arabic comic strips |
| **Handwritten text** | ~840 | Handwritten documents |
| **Invoice** | ~840 | Financial invoices |
| **Label** | ~810 | Product labels |
| **Magazine** | ~840 | Magazine pages |
| **Map** | ~840 | Arabic maps |
| **Newspaper** | ~853 | Newspaper articles |
| **Official document** | ~842 | Certificates, contracts |
| **Receipt** | ~839 | Purchase receipts |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real-world scanned documents |
| **Script** | Arabic (right-to-left) |
| **Quality Variation** | High (mixed scanning quality) |
| **Key Value** | **Diverse Arabic document types** for script detection |
| **Annotation** | JSON with text regions and transcriptions |

##### Project Usage

- **Path**: `01_base_data/language/arabic_docs_ocr/` ✅ Extracted (20,091 files, 9.3 GB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training
- **Note**: Excellent variety of real-world Arabic documents
- **Parser**: ✅ `parse_arabic_docs_labels` (extracts category, language_code from folder structure)

---
