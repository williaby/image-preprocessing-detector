#### Hindi OCR Synthetic Dataset

> **Quick Stats**: 80,000 line images | Devanagari script | Synthetic text lines
>
> **License**: CC0 (Public Domain) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Hindi OCR Synthetic Line Image Text Pair |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Kaggle** | [prathmeshzade/hindi-ocr-synthetic-line-image-text-pair](https://www.kaggle.com/datasets/prathmeshzade/hindi-ocr-synthetic-line-image-text-pair) |
| **License** | CC0 (Public Domain) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/hindi_ocr_synthetic/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 80,009 |
| **CSV Labels** | 1 (data.csv) |
| **Total Size** | 735 MB |
| **File Format** | PNG/JPG |

##### Dataset Structure

| Folder | Contents |
|--------|----------|
| **output_images/** | 80,000 synthetic line images |
| **TestSamples/** | 9 sample images |
| **data.csv** | Image-text pairs mapping |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthetically generated |
| **Script** | Devanagari (Hindi) |
| **Quality** | Clean (synthetic) |
| **Key Value** | **Large-scale Devanagari training data** |
| **Generation** | Programmatic text rendering |

##### Project Usage

- **Path**: `01_base_data/language/hindi_ocr_synthetic/` ✅ Extracted (80,010 files, 920 MB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Devanagari script class training (primary source)
- **Note**: Synthetic data - excellent for training, needs real-world augmentation
- **Parser**: ✅ `parse_hindi_synthetic_labels` (extracts transcription from .txt pairs, hi/Deva metadata)

---

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/hindi_ocr_synthetic/` | ✅ Available | 80,009 PNG files |
| **Text/GT** | Native annotations | ✅ Available | CSV/TXT: Paired image-text files (Devanagari line transcriptions) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/hindi-synth/` | ✅ Available | Docling GPU: 161 layout batches, 80,009 images |
| **Layer 2 Metadata** | `metadata_registry/json/hindi_ocr_synthetic_metadata.json` | ✅ Complete | 80,008 samples (2026-02-09) |
