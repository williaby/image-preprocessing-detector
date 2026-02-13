#### CC-OCR (CJK Mixed Benchmark)

> **Quick Stats**: 7,058 images | 39 subsets | 4 tracks | MIT license
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | CC-OCR: Comprehensive OCR Benchmark |
| **Version** | 1.0 |
| **HuggingFace** | [wulipc/CC-OCR](https://huggingface.co/datasets/wulipc/CC-OCR) |
| **License** | MIT |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/cc_ocr/` |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 7,058 |
| **Subsets** | 39 |
| **Real-world Images** | 41% |
| **Total Size** | 2.1 GB |
| **File Format** | PNG/JPG |

##### Tracks

| Track | Description |
|-------|-------------|
| **Multi-Scene Text** | Various text in natural scenes |
| **Multilingual Text** | Chinese, English, mixed |
| **Document Parsing** | Structured document understanding |
| **Key Information Extraction** | Form field extraction |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mixed (41% real-world, 59% synthetic) |
| **Key Value** | **MIT-licensed CJK benchmark** (alternative to M6Doc) |
| **Languages** | Chinese (Simplified + Traditional), English, Multilingual |
| **Quality** | Professional annotation |

##### Project Usage

- **Path**: `01_base_data/language/huggingface_downloads/CC-OCR/`
- **Images Path**: `01_base_data/language/huggingface_downloads/CC-OCR/extracted_images/` ✅ 7,058 images
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: CJK Mixed script class training
- **Note**: Selected as MIT alternative to research-licensed M6Doc
- **Parser**: [`parse_cc_ocr_labels`](../scripts/annotate_base_metadata.py#L2157) | ✅ Complete
- **Conversion**: ✅ Extracted from TSV files (base64-encoded images) → `extracted_images/` via `scripts/convert_datasets_to_images.py --dataset cc-ocr`

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/cc-ocr/` | ✅ Available | 6,533 JPG/PNG files |
| **Text/GT** | Native annotations | ✅ Available | TSV: Full OCR text in `answer` field (doc_parsing, kie TSVs) |
| **Text/OCR Extracted** | `metadata_registry/extracted/cc-ocr/` | ✅ Available | Docling GPU: 33 OCR batches, 6,533 records |
| **Layout Extracted** | `metadata_registry/extracted/cc-ocr/` | ✅ Available | Docling GPU: 33 layout batches, 6,533 images |

##### Text Labels

CC-OCR includes OCR ground truth text in TSV annotation files:

| Attribute | Value |
|-----------|-------|
| **Location** | `doc_parsing/`, `kie/`, `multi_lan_ocr/`, `multi_scene_ocr/` subdirs |
| **File Count** | 39 TSV files |
| **Format** | TSV with columns: `index`, `image`, `image_name`, `question`, `answer`, `category`, `l2-category`, `split` |
| **Text Column** | `answer` - contains full OCR ground truth text |

**Sample text labels**:

- Chinese documents: `非本协议另有规定或双方另有其它书面约定，租金...`
- English documents: `\section*{English First Paper} Subject code: 107...`
- LaTeX formatting preserved for formulas and structured content

---

#### Nepal Devanagari Documents

> **Quick Stats**: 717 pages | Book + Newspaper | Real-world Devanagari
>
> **License**: Public Domain (assumed) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Nepal Devanagari Documents (Atharva Veda) |
| **Source** | Vedic Reserve, Maharishi International University |
| **Download** | [Atharva Veda PDF](http://vedicreserve.miu.edu/atharva_veda/atharva_veda.pdf) (713 pages) |
| **Conversion Date** | 2025-01-25 |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Nepal 1 (Book)** | 713 pages |
| **Nepal 2 (Newspaper)** | 4 pages |
| **Total Pages** | 717 |
| **Resolution** | 300 DPI |
| **File Format** | PNG (converted from PDF) |

##### Content

| Source | Description |
|--------|-------------|
| **Nepal 1** | Multi-page book, single-column Devanagari text |
| **Nepal 2** | 4-page newspaper, multi-column layout |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/nepal_devanagari/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Real-world Devanagari document samples
- **Parser**: [`parse_multilingual_scripts_labels`](../scripts/annotate_base_metadata.py#L1548) | ⚠️ Partial (unlabeled)

---

#### Downloaded Script Detection Datasets (Phase 10B)

The following datasets have been downloaded for 10-class script detection training:

| Dataset | Scripts | Size | Path | Status |
|---------|---------|------|------|--------|
| **MDIW-13** | 13 scripts (Arabic, Devanagari, Japanese, Thai, Latin + 8 Indic) | 226 MB | `language/mdiw13/` | ✅ Downloaded |
| **MIDV-500** | Latin, Cyrillic (50 countries ID docs) | 48 GB | `language/midv500_data/` | ✅ Downloaded |
| **TibHCR** | Tibetan (141,698 character samples) | 4.5 GB | `language/huggingface_downloads/TibHCR/` | ✅ Downloaded |
| **CC-OCR** | CJK Mixed (7,058 images, MIT) | 2.1 GB | `language/huggingface_downloads/CC-OCR/` | ✅ Downloaded |
| **MLT-19** | 10 languages (scene text) | 14.3 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Arabic Docs OCR** | Arabic (10,000 images) | 9.5 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Yarmouk OCR** | Arabic (8,994 images) | 2.2 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Hindi OCR Synthetic** | Devanagari (80,000 lines) | 735 MB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Nepali Handwritten** | Devanagari (1,000 images) | 1.3 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **PUCIT-OHUL Urdu** | Arabic-derived (7,309 lines) | 568 MB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Nepal PDFs** | Devanagari (717 pages) | - | `language/multilingual_scripts/nepal_devanagari/` | ✅ Converted |

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 6,284 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 6,284 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `has_table` | 100.0% | 0.000 |
