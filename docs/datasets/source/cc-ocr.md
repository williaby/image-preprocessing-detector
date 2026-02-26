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
| **Total Images** | 7,058 (6,533 available; 525 referenced in annotations but not included in public download) |
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

##### Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | Benchmark annotators |
| **Quality Assurance** | Multi-task benchmark annotation with professional review |
| **GT Label Coverage** | 100% (all 7K images with multi-task annotations) |

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
| **Images** | `01_base_data/language/cc-ocr/` | ✅ Available | 6,533 JPG/PNG files (Note: 525 images referenced in annotations but not included in public download) |
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

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: D (79.2/100) | **Auditor**: claude-opus-4-6
> **Grade Cap**: C -> D (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 79.8 | 33% |  |
| Field Validity | 96.4 | 33% |  |
| Doc Completeness | 45.5 | 20% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 85.0 | 13% |  |
| **Overall** | **79.2** | | **Grade D** |

**Grade Cap Applied**:
> Grade capped from C to D: Critical fields below 75%: domain_level1=0%. Language, script, and domain are critical training stratification fields. Datasets with <75% coverage on any of these fields cannot reliably support diversity-aware training splits or balanced sampling. A contact sheet VLM review or enrichment pipeline must bring these fields above 75% before the dataset can advance beyond Grade D.

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/cc-ocr/](../../scripts/audit/results/cc-ocr/)

---

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

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | 0 | — | Benchmark evaluation set only; no orientation augmentation in source |
| MNV4-H2 | skew_reg | ➖ | 0 | — | Images are clean/benchmark-prepared; no skew distribution |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~3,000 | Pseudo-label via pipeline | Mixed DPI (41% real-world scene + 59% synthetic renders); useful for mid-quality range |
| SIG-G1-1 | blur_score | 🟡 | ~2,700 | Pseudo-label via pipeline | Real-world subset (41%) provides natural blur variation; synthetic is uniformly clean |
| SIG-G1-2 | noise_score | 🟡 | ~2,700 | Pseudo-label via pipeline | Real scene images contribute noise diversity; synthetic component adds clean negatives |
| SIG-G1-3 | contrast_score | 🟡 | ~2,700 | Pseudo-label via pipeline | Scene/document mix provides contrast range; synthetic has uniform high contrast |
| SIG-G1-4 | skew_score | ➖ | 0 | — | Benchmark set; images are pre-aligned and standardized |
| SIG-G1-5 | compression_score | 🟡 | ~2,700 | Pseudo-label via pipeline | JPEG artifacts present in real-world subset; PNG synthetic is lossless |
| SIG-G1-6 | overall_quality | 🟡 | ~2,700 | Pseudo-label via pipeline | Mixed quality real-world subset adds useful mid-tier IQA samples |
| SIG-G2-1 | script_cls | ✅ | ~6,500 | Ground truth (ISO 15924) | Hans script label confirmed; 4 tracks cover Chinese + multilingual; CJK-only but high volume |
| SIG-G3-1 | orientation_cls (post) | ➖ | 0 | — | Pre-aligned benchmark; no orientation variation to exploit |
| SIG-G3-2 | skew_reg (post) | ➖ | 0 | — | Pre-aligned benchmark; no skew variation |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~6,500 | Derived from content_type=printed | 100% printed text confirmed by metadata; clean NONE-class samples |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | — | No handwriting present |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | — | No handwriting present |
| SIG-G4-4 | presence_reg | ✅ | ~6,500 | Derived (0.0 score) | All printed; contributes 0.0 anchor values to presence regression |
| SIG-G4-5 | legibility_reg | ❌ | 0 | — | No handwriting; not applicable |
| SIG-G5-1 | capture_method_cls | ➖ | 0 | — | capture_method=unknown in metadata; cannot assert real-capture class confidently |
| SIG-G5-2 | shadow_reg | ➖ | 0 | — | No shadow annotations; synthetic portion has no shadow by design |
| SIG-G5-3 | warping_reg | ➖ | 0 | — | No warping annotations; benchmark images are flat/corrected |
| SIG-G5-4 | code_cls | 🟡 | ~500 | Derived from OCR text | Some images contain code-like formatting (LaTeX formulas preserved in annotations); minority |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~3,000 | Pseudo-label via pipeline | Same as MNV4-H3; mixed real/synthetic provides mid-quality range |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | CJK only (Hans=100% per metadata); multilingual track includes English but not separately labeled in L2 metadata |
| 2 | Capture method | 🟡 | 41% real-world (scene photos + scanned docs) + 59% synthetic renders; capture_method field = unknown in metadata |
| 3 | Document domain | ❌ | domain_level1=UNK for all 6,284 samples; benchmark covers business/academic/scene but unstratified |
| 4 | Layout type | 🟡 | 4 tracks cover scene text, structured documents (KIE), and document parsing; layout_types field unpopulated |
| 5 | Text density | 🟡 | text_scope=mixed for all samples; range from sparse scene text to dense document pages |
| 6 | Degradation types | 🟡 | Real-world 41% subset has natural degradation (compression, noise, perspective); degradation_types field unpopulated |
| 7 | Resolution/DPI range | 🟡 | Real-world images vary widely; synthetic renders are consistent; no DPI metadata available |
| 8 | Document age | ❌ | Modern content only; no historical or aged document representation |
| 9 | Text scope | ✅ | text_scope=mixed confirmed; covers word-level (multi-scene), line-level, and page-level text |
| 10 | Content flags | 🟡 | has_table=15% (942/6,284); no other content flags in metadata |
| 11 | Binarization status | ❌ | No binarized images; all color or grayscale originals |
| 12 | Artifact types | 🟡 | JPEG compression artifacts in real-world subset; otherwise minimal; no artifact labels |
| 13 | Color mode | 🟡 | Mixed; real-world images are color/grayscale; synthetic renders are color; no explicit color_mode field |
| 14 | Font variety | ✅ | Strong CJK font variety across 39 subsets; Chinese Simplified + Traditional + Latin fonts represented |

### 13.3 Corpus Role & Constraints

CC-OCR is a **primary contributor for CJK script detection (SIG-G2-1)** and a **secondary IQA contributor** via its 41% real-world subset. The MIT license removes all commercial-use barriers, making it the preferred CJK benchmark alternative to research-licensed M6Doc. The dataset's L2 metadata has domain_level1=UNK for all samples (Grade D audit), so it cannot be used for domain-stratified sampling until enrichment is complete; for script training, Hans=100% ground truth is reliable.
