# Data Availability Report

> Generated: 2026-02-06 | Datasets: 50

## Executive Summary

| Dimension | Available | Partial | Missing | Coverage |
|-----------|-----------|---------|---------|----------|
| **Images on E Drive** | 48 | 0 | 2 (text corpora) | 100% (of image datasets) |
| **Docling OCR Text** | 7 | 0 | 43 | 14% |
| **DocLayout-YOLO Labels** | 7 | 0 | 43 | 14% |
| **GCS Documented** | 50 | 0 | 0 | 100% |

**Total images on disk**: ~2,064,000+
**GCS Bucket**: `gs://image_detection_b/image-preprocessing-detector/datasets/`

---

## Q1: Image Availability (E Drive)

### All 50 Datasets

| Dataset | Images | E Drive Path | Status |
|---------|-------:|--------------|--------|
| arabic-docs | 10,045 | `01_base_data/language/arabic_docs_ocr` | OK |
| bhutan-afs | 135 | `01_base_data/documents/bhutan_financial` | OK |
| cc-ocr | 6,533 | `01_base_data/language/cc-ocr` | OK |
| coco-text | 123,287 | `01_base_data/text_detection/cocotext` | OK |
| cvsi | 10,715 | `01_base_data/language/cvsi` | OK |
| dibco | 212 | `02_benchmark_only/dibco` | OK |
| diqa-5000 | 5,500 | `02_benchmark_only/diqa-5000` | OK |
| doc3d | 102,064 | `01_base_data/camera_captured/doc3d/data/doc3d/img/` | OK |
| doclaynet | 81,471 | `01_base_data/documents/doclaynet` | OK |
| docsynth | 300,000 | `01_base_data/layout/docsynth300k` | OK |
| dzongkha-digits | 62 | `01_base_data/language/multilingual_scripts/dzongkha_digits` | OK |
| financebench | 54,121 | `02_benchmark_only/financebench` | OK |
| fintabnet | 97,475 | `01_base_data/tables/fintabnet` | OK |
| funsd | 348 | `01_base_data/forms/funsd` | OK |
| funsd-plus | 1,139 | `01_base_data/forms/funsd_plus` | OK |
| hasy | 168,233 | `01_base_data/handwriting/hasy` | OK |
| hiertext | 11,641 | `01_base_data/text_detection/hiertext` | OK |
| hindi-synth | 80,009 | `01_base_data/language/hindi_ocr_synthetic` | OK |
| iam | 130,212 | `01_base_data/handwriting/iam_handwriting` | OK |
| im2latex | 10,000 | `01_base_data/formulas/im2latex` | OK |
| invoices-kg | 1,414 | `01_base_data/forms/invoices_kaggle` | OK |
| jssoda | 2,000 | `01_base_data/language/multilingual_scripts/jssoda` | OK |
| mathverse | 6,940 | `02_benchmark_only/mathverse` | OK |
| mdiw13 | 290,213 | `01_base_data/language/mdiw13` | OK |
| midv500 | 3,612 | `01_base_data/documents/midv500` | OK |
| mle2e | 1,816 | `01_base_data/language/mle2e` | OK |
| mlt19 | 19,993 | `01_base_data/language/mlt19` | OK |
| multimodal-textbook | 1,113 | `01_base_data/educational/multimodal_textbook` | OK |
| muharaf | 25,711 | `01_base_data/handwriting/muharaf` | OK |
| nepali-handwritten | 958 | `01_base_data/language/nepali_handwritten` | OK |
| nist-sd19 | 3,669 | `01_base_data/handwriting/nist-sd19` | OK |
| nist-sd2 | 5,590 | `01_base_data/forms/nist-sd2` | OK |
| nist-sd6 | 5,595 | `01_base_data/forms/nist_sd6` | OK |
| ocr-quality | 1,000 | `01_base_data/ocr_quality` | OK |
| ohr-bench | 16,091 | `02_benchmark_only/ohr-bench` | OK |
| omnidocbench | 1,358 | `02_benchmark_only/omnidocbench` | OK |
| openlid-v2 | N/A | N/A | TEXT CORPUS |
| pucit-ohul | 7,401 | `01_base_data/language/pucit-ohul` | OK |
| pubtabnet | 519,030 | `01_base_data/tables/pubtabnet` | OK |
| realdae | 1,200 | `01_base_data/camera_captured/realdae` | OK |
| rvl-cdip | 16,000 | `01_base_data/documents/rvl_cdip` | OK |
| signatr6k | 12,514 | `01_base_data/handwriting/signatr6k` | OK |
| siw13 | 16,291 | `01_base_data/language/siw13` | OK |
| smartdoc-qa | 4,280 | `02_benchmark_only/smartdoc-qa` | OK |
| sroie | 973 | `01_base_data/forms/sroie_icdar2019` | OK |
| tablebank | 260,025 | `01_base_data/tables/tablebank` | OK |
| tibhcr | 141,698 | `01_base_data/language/huggingface_downloads/TibHCR` | OK |
| tobacco800 | 1,290 | `01_base_data/degraded/tobacco800` | OK |
| wili-2018 | N/A | `01_base_data/language/wili_2018` | TEXT CORPUS |
| yarmouk | 15,062 | `01_base_data/language/yarmouk` | OK |

### Notes

| Dataset | Note |
|---------|------|
| doc3d | 102,064 images extracted (448x448 RGBA). Albedo/BM zips retained unextracted. |
| openlid-v2 | Text corpus (language identification). No images expected. |
| wili-2018 | Text corpus (Wikipedia language identification). No images expected. |

---

## Q2: Text Availability (Docling OCR Extraction)

OCR text has been extracted using Docling for **7 datasets** at `annotations/{dataset}/ocr/`.
An additional dataset (funsd) has 1,324 OCR records in the `ocr/` subdirectory with `batch_*.jsonl` naming.

| Dataset | OCR Records | JSONL Files | Pattern | Match to Images |
|---------|------------:|------------:|---------|-----------------|
| diqa-5000 | 5,500 | 28 | `ocr_batch_*.jsonl` | 100% (5,500 images) |
| funsd | 1,324 | 14 | `batch_*.jsonl` | ~100% (348 train+test images, multi-page?) |
| invoices-kg | 1,414 | 8 | `ocr_batch_*.jsonl` | 100% (1,414 images) |
| nist-sd2 | 5,590 | 28 | `ocr_batch_*.jsonl` | 100% (5,590 images) |
| nist-sd6 | 5,595 | 28 | `ocr_batch_*.jsonl` | 100% (5,595 images) |
| rvl-cdip | 16,000 | 80 | `ocr_batch_*.jsonl` | 100% (16,000 images) |
| smartdoc-qa | 3,000 | 15 | `ocr_batch_*.jsonl` | 70% (4,280 images) |

**Mirror at `extracted_text/`**: Same 8 datasets also appear under `/mnt/e/image_detection/extracted_text/` (including mobile-receipts-voxel51 which is not in our 50).

### Gap: 43 datasets have NO Docling OCR extraction

Note: Some datasets have ground truth text as part of their native annotations (e.g., sroie has receipt text, im2latex has LaTeX, funsd has form text labels, mlt19 has text annotations). These are NOT the same as Docling OCR extraction but could serve as text sources for language detection.

---

## Q3: DocLayout-YOLO Layout Labels

Layout annotations using DocLayout-YOLO (COCO format, 11 DocLayNet classes) exist for **7 datasets** at `annotations/{dataset}/layout/`.

| Dataset | Layout Records | JSON Files | Format |
|---------|---------------:|------------:|--------|
| diqa-5000 | 5,411 | 28 | COCO (11-class DocLayNet) |
| invoices-kg | 1,414 | 8 | COCO (11-class DocLayNet) |
| nist-sd2 | 5,590 | 28 | COCO (11-class DocLayNet) |
| nist-sd6 | 5,593 | 28 | COCO (11-class DocLayNet) |
| rvl-cdip | 15,733 | 80 | COCO (11-class DocLayNet) |
| smartdoc-qa | 2,203 | 15 | COCO (11-class DocLayNet) |
| mobile-receipts-voxel51 | 709 | 4 | COCO (11-class DocLayNet) |

**Note**: funsd has layout batch files in `gcs_ocr/` subdirectory but they contain 0 image records (empty `images` arrays). The 7th annotated dataset (mobile-receipts-voxel51) is not in our canonical 50.

### Datasets with native layout annotations (NOT DocLayout-YOLO)

- **doclaynet**: 81,471 images with native DocLayNet annotations (11-class COCO format) - most comprehensive
- **pubtabnet**: 519K images with table structure annotations
- **tablebank**: 260K images with table detection annotations
- **fintabnet**: 97K images with table structure annotations
- **docsynth**: 300K synthetic document images with layout annotations

### Gap: 43 datasets have NO DocLayout-YOLO annotations

---

## Q4: GCS Availability

All 50 datasets have documented GCS paths in their source documentation files. The standard pattern is:

```
gs://image_detection_b/image-preprocessing-detector/datasets/{dataset_name}/
```

Exceptions:

- **doc3d**: Intentionally excluded from GCS due to ~209 GB size
- **coco-text**: `gs://image_detection_b/01_base_data/text_detection/cocotext/` (different path pattern)
- **hiertext**: `gs://image_detection_b/01_base_data/text_detection/hiertext/` (different path pattern)
- **openlid-v2**: `gs://image_detection_b/datasets/synthetic-corpus/` (corpus-specific path)

**Note**: `gsutil` is not available in the current environment. GCS contents cannot be verified programmatically. The documented paths may not all have actual data uploaded.

---

## Priority Actions

### ~~P0: Extract doc3d archives~~ DONE

- ✅ 102,064 PNG images extracted (448x448 RGBA, 24 GB)
- Albedo/backward mapping zips retained unextracted (~107 GB)

### P1: Extend Docling OCR to remaining 42 image datasets

Currently only 7/48 image datasets have OCR extraction. Priority order:

1. **High-value document datasets**: doclaynet (81K), tobacco800 (1.3K), financebench (54K), sroie (973), funsd-plus (1.1K)
2. **Table datasets**: pubtabnet (519K), tablebank (260K), fintabnet (97K)
3. **Handwriting**: iam (130K), muharaf (25K), nepali-handwritten (958), pucit-ohul (7.4K), tibhcr (142K)
4. **Script/language**: mlt19 (20K), mle2e (1.8K), cc-ocr (6.5K), cvsi (10.7K), hindi-synth (80K)
5. **Others**: midv500 (3.6K), realdae (1.2K), ocr-quality (1K), ohr-bench (16K)

### P2: Extend DocLayout-YOLO to remaining 42 image datasets

Same priority as P1 - run layout detection pipeline in parallel with OCR.

### P3: Verify GCS uploads

Install `gsutil` or use `gcloud storage` to verify actual GCS contents match documented paths.

---

## Annotation Pipeline Status

### Current Annotation Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| Docling OCR | `annotations/{dataset}/ocr/ocr_batch_*.jsonl` | 7 datasets processed |
| DocLayout-YOLO | `annotations/{dataset}/layout/layout_batch_*.json` | 7 datasets processed |
| Ground Truth | `annotations/{dataset}/ground_truth/` | Directories exist but empty for all 8 annotated datasets |
| Extracted Text | `extracted_text/{dataset}/` | Mirror of OCR annotations |
| Layer 2 Parquet | `metadata_registry/samples.parquet` | 41 datasets, 10 samples each (pilot) |

### Annotated vs Total Coverage

```
Images with OCR:    38,423 / ~2,064,000  (1.9%)
Images with Layout: 36,944 / ~2,064,000  (1.8%)
Datasets with OCR:  7 / 48 image datasets (14.6%)
Datasets with Layout: 6 / 48 image datasets (12.5%)
```
